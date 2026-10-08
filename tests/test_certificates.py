"""Route feasibility and full-distance optimality are separate promises."""

from dataclasses import replace
from math import inf
import unittest

from dijkstra_toolkit import Arc, dijkstra, make_graph, recover, verify_distances, verify_route


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.graph = make_graph(4, [Arc(0, 0, 1, 5), Arc(1, 0, 2, 1),
                                    Arc(2, 2, 1, 1)], version="snapshot")
        self.result = dijkstra(self.graph, 0)

    def test_valid_route_and_source_identity(self):
        self.assertTrue(verify_route(self.graph, 0, 1, [1, 2], 2,
                                     graph_digest=self.graph.digest))
        self.assertTrue(verify_route(self.graph, 0, 0, [], 0))
        self.assertFalse(verify_route(self.graph, 0, 1, [], 0))
        self.assertTrue(verify_distances(self.graph, self.result))

    def test_feasible_suboptimal_route_does_not_prove_optimality(self):
        self.assertTrue(verify_route(self.graph, 0, 1, [0], 5))
        fabricated = replace(self.result, distance=(0, 5, 1, inf),
                             parent_edge=(None, 0, 1, None))
        self.assertFalse(verify_distances(self.graph, fabricated))

    def test_route_tampering_is_rejected(self):
        for edge_ids, claimed_cost in [([1, 2], 3), ([2, 1], 2), ([99], 2),
                                       ([1], 1), ([0, 2], 6), ([True], 5),
                                       (["1", 2], 2), ([1, 2], True),
                                       ([1, 2], 2.0), ([1, 2], -1)]:
            with self.subTest(edge_ids=edge_ids, claimed_cost=claimed_cost):
                self.assertFalse(verify_route(self.graph, 0, 1, edge_ids, claimed_cost))
        self.assertFalse(verify_route(self.graph, 0, 1, [1, 2], 2, graph_digest="wrong"))
        self.assertFalse(verify_route(self.graph, 0, 1, None, 2))
        for cost in [None, "2", inf, -inf, float("nan")]:
            with self.subTest(cost=cost):
                self.assertFalse(verify_route(self.graph, 0, 1, [1, 2], cost))

    def test_same_version_with_changed_content_is_a_different_snapshot(self):
        changed = make_graph(4, [Arc(0, 0, 1, 5), Arc(1, 0, 2, 1),
                                 Arc(2, 2, 1, 7)], version="snapshot")
        self.assertEqual(changed.version, self.graph.version)
        self.assertNotEqual(changed.digest, self.graph.digest)
        with self.assertRaises((ValueError, RuntimeError)):
            recover(self.result, changed, 1)
        self.assertFalse(verify_distances(changed, self.result))
        self.assertFalse(verify_route(changed, 0, 1, [1, 2], 2,
                                      graph_digest=self.graph.digest))

    def test_version_mismatch_is_rejected(self):
        changed = make_graph(4, self.graph.arcs, version="other-snapshot")
        with self.assertRaises((ValueError, RuntimeError)):
            recover(self.result, changed, 1)
        self.assertFalse(verify_distances(changed, self.result))

    def test_digest_covers_units_vertex_count_and_arc_identity(self):
        candidates = [
            make_graph(4, self.graph.arcs, version="snapshot", weight_unit="milliseconds"),
            make_graph(5, self.graph.arcs, version="snapshot"),
            make_graph(4, [Arc(10, 0, 1, 5), Arc(11, 0, 2, 1), Arc(12, 2, 1, 1)],
                       version="snapshot"),
        ]
        for changed in candidates:
            with self.subTest(digest=changed.digest):
                self.assertNotEqual(changed.digest, self.graph.digest)
                self.assertFalse(verify_distances(changed, self.result))
                with self.assertRaises((ValueError, RuntimeError)):
                    recover(self.result, changed, 1)

    def test_broken_parent_certificates_are_rejected(self):
        changes = [
            {"parent_edge": (None, None, 1, None)},
            {"parent_edge": (None, 99, 1, None)},
            {"parent_edge": (None, 1, 1, None)},
            {"distance": (0, 3, 1, inf)},
            {"distance": (0, 2)},
            {"parent_edge": (None, 2)},
            {"graph_digest": "not-the-snapshot"},
        ]
        for change in changes:
            with self.subTest(change=change):
                fabricated = replace(self.result, **change)
                with self.assertRaises((ValueError, RuntimeError)):
                    recover(fabricated, self.graph, 1)
                self.assertFalse(verify_distances(self.graph, fabricated))

    def test_parent_cycle_fails_even_with_zero_weights(self):
        graph = make_graph(3, [Arc(0, 0, 1, 0), Arc(1, 1, 2, 0), Arc(2, 2, 1, 0)])
        fabricated = replace(dijkstra(graph, 0), parent_edge=(None, 2, 1))
        with self.assertRaises((ValueError, RuntimeError)):
            recover(fabricated, graph, 2)
        self.assertFalse(verify_distances(graph, fabricated))

    def test_distance_certificate_rejects_malformed_labels_and_state(self):
        changes = [
            {"distance": (0, True, 1, inf)},
            {"distance": (0, 2.0, 1, inf)},
            {"distance": (0, "2", 1, inf)},
            {"distance": (0, float("nan"), 1, inf)},
            {"distance": (0, -inf, 1, inf)},
            {"distance": (1, 2, 1, inf)},
            {"distance": (0, 0, 0, inf)},
            {"distance": (0, inf, 1, inf)},
            {"distance": (0, 2, 1, 0)},
            {"sources": ()},
            {"sources": (True,)},
            {"sources": (0, 0)},
            {"sources": [0]},
            {"target": True},
            {"target": 4},
            {"distance": [0, 2, 1, inf]},
            {"settled": (True,)},
            {"settled": (True, False, True, False)},
            {"settled": (1, True, True, False)},
            {"parent_edge": (None, 2, 1, 0)},
            {"parent_edge": (None, 2, True, None)},
            {"complete": False},
            {"complete": 1},
        ]
        for change in changes:
            with self.subTest(change=change):
                self.assertFalse(verify_distances(self.graph, replace(self.result, **change)))

    def test_recovery_endpoint_validation(self):
        for target in [True, 1.0, "1", None, -1, 4]:
            with self.subTest(target=target):
                with self.assertRaises((ValueError, TypeError)):
                    recover(self.result, self.graph, target)


if __name__ == "__main__":
    unittest.main()
