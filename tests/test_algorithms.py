"""Behavioral regressions for the public shortest-path API."""

from dataclasses import FrozenInstanceError
from math import inf
import unittest

from dijkstra_toolkit import (
    Arc,
    dijkstra,
    make_graph,
    multi_source_dijkstra,
    recover,
    require_int,
    reverse_graph,
    verify_distances,
)


def ag_graph():
    """Thirteen undirected links from the manuscript, not inferred paths."""
    links = [
        (0, 1, 2), (0, 2, 4), (0, 3, 5),
        (1, 3, 2), (1, 4, 4), (1, 6, 7),
        (2, 5, 3), (2, 6, 5),
        (3, 4, 1), (3, 5, 5), (3, 6, 5),
        (4, 6, 2), (5, 6, 1),
    ]
    arcs = []
    for u, v, weight in links:
        arcs.append(Arc(len(arcs), u, v, weight))
        arcs.append(Arc(len(arcs), v, u, weight))
    return make_graph(7, arcs, version="manuscript-A-G", weight_unit="cost-unit")


class AlgorithmTests(unittest.TestCase):
    def test_ag_distances_route_parents_and_trace(self):
        graph = ag_graph()
        events = []
        result = dijkstra(graph, 0, observer=events.append)
        self.assertEqual(result.distance, (0, 2, 4, 4, 5, 7, 7))
        self.assertEqual(result.sources, (0,))
        self.assertTrue(result.complete)
        self.assertEqual(result.settled, (True,) * 7)
        self.assertEqual([e.vertex for e in events], list(range(7)))
        self.assertEqual([e.rank for e in events], list(range(1, 8)))
        self.assertEqual([e.distance for e in events], [0, 2, 4, 4, 5, 7, 7])
        route = recover(result, graph, 6)
        self.assertIsNotNone(route)
        self.assertEqual([0] + [e.head for e in route], [0, 1, 3, 4, 6])
        self.assertEqual(sum(e.weight for e in route), 7)
        parents = tuple(
            None if edge_id is None else graph.edge_by_id[edge_id].tail
            for edge_id in result.parent_edge
        )
        self.assertEqual(parents, (None, 0, 0, 1, 3, 2, 4))
        self.assertEqual(len(graph.arcs), 26)
        self.assertTrue(verify_distances(graph, result))

    def test_ag_complete_distance_matrix(self):
        expected = (
            (0, 2, 4, 4, 5, 7, 7),
            (2, 0, 6, 2, 3, 6, 5),
            (4, 6, 0, 7, 6, 3, 4),
            (4, 2, 7, 0, 1, 4, 3),
            (5, 3, 6, 1, 0, 3, 2),
            (7, 6, 3, 4, 3, 0, 1),
            (7, 5, 4, 3, 2, 1, 0),
        )
        graph = ag_graph()
        self.assertEqual(tuple(dijkstra(graph, s).distance for s in range(7)), expected)

    def test_target_is_settled_not_merely_discovered(self):
        graph = make_graph(3, [Arc(0, 0, 2, 10), Arc(1, 0, 1, 1), Arc(2, 1, 2, 1)])
        result = dijkstra(graph, 0, 2)
        self.assertEqual(result.distance[2], 2)
        self.assertEqual(tuple(e.edge_id for e in recover(result, graph, 2)), (1, 2))
        self.assertTrue(result.settled[2])
        self.assertFalse(result.complete)

    def test_early_exit_does_not_certify_other_tentative_labels(self):
        graph = make_graph(3, [Arc(0, 0, 1, 1), Arc(1, 0, 2, 10), Arc(2, 1, 2, 2)])
        events = []
        early = dijkstra(graph, 0, 1, observer=events.append)
        self.assertEqual(early.distance[2], 10)
        self.assertEqual(early.settled, (True, True, False))
        self.assertEqual([e.vertex for e in events], [0, 1])
        self.assertFalse(early.complete)
        self.assertEqual(early.diagnostics.scanned_edges, 2)
        self.assertFalse(verify_distances(graph, early))
        with self.assertRaises((ValueError, RuntimeError)):
            recover(early, graph, 2)
        self.assertEqual(dijkstra(graph, 0).distance[2], 3)

    def test_source_equals_target(self):
        singleton = make_graph(1, [Arc(0, 0, 0, 0)])
        result = dijkstra(singleton, 0, 0)
        self.assertTrue(result.complete)
        self.assertEqual(result.distance, (0,))
        self.assertEqual(recover(result, singleton, 0), ())
        graph = make_graph(2, [Arc(0, 0, 1, 2)])
        partial = dijkstra(graph, 0, 0)
        self.assertFalse(partial.complete)
        self.assertEqual(partial.distance, (0, inf))
        self.assertEqual(recover(partial, graph, 0), ())
        self.assertEqual(partial.diagnostics.scanned_edges, 0)

    def test_disconnected_and_directed_graph(self):
        graph = make_graph(3, [Arc(0, 0, 1, 2)])
        result = dijkstra(graph, 1, 0)
        self.assertTrue(result.complete)
        self.assertEqual(result.distance, (inf, 0, inf))
        self.assertIsNone(recover(result, graph, 0))
        self.assertIsNone(recover(result, graph, 2))
        self.assertTrue(verify_distances(graph, result))

    def test_zero_cost_cycle_and_self_loop_do_not_change_root(self):
        graph = make_graph(4, [
            Arc(0, 0, 0, 0), Arc(1, 0, 1, 0), Arc(2, 1, 2, 0),
            Arc(3, 2, 0, 0), Arc(4, 2, 1, 0), Arc(5, 2, 3, 1),
        ])
        result = dijkstra(graph, 0)
        self.assertEqual(result.distance, (0, 0, 0, 1))
        self.assertIsNone(result.parent_edge[0])
        self.assertEqual(result.diagnostics.live_pops, 4)
        self.assertEqual(result.diagnostics.improvements, 3)
        self.assertEqual([e.edge_id for e in recover(result, graph, 3)], [1, 2, 5])
        self.assertTrue(verify_distances(graph, result))

    def test_parallel_edges_and_equal_ties_are_reproducible(self):
        arcs = [Arc(9, 0, 1, 5), Arc(3, 0, 1, 1), Arc(1, 0, 1, 1),
                Arc(7, 0, 2, 1), Arc(4, 1, 3, 1), Arc(8, 2, 3, 1)]
        first = make_graph(4, arcs)
        second = make_graph(4, reversed(arcs))
        r1, r2 = dijkstra(first, 0), dijkstra(second, 0)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(r1.parent_edge, r2.parent_edge)
        self.assertEqual(r1.distance, (0, 1, 1, 2))
        self.assertEqual([e.edge_id for e in recover(r1, first, 3)], [1, 4])

    def test_stale_heap_entry_and_counter_identities(self):
        graph = make_graph(4, [Arc(0, 0, 1, 10), Arc(1, 0, 2, 1),
                               Arc(2, 2, 1, 1), Arc(3, 1, 3, 1)])
        events = []
        result = dijkstra(graph, 0, observer=events.append)
        d = result.diagnostics
        self.assertEqual(result.distance, (0, 2, 1, 3))
        self.assertEqual((d.live_pops, d.stale_pops, d.scanned_edges, d.improvements), (4, 1, 4, 4))
        self.assertEqual(d.peak_queue, 2)
        self.assertEqual(d.live_pops + d.stale_pops, d.improvements + 1)
        self.assertEqual(len(events), d.live_pops)

    def test_arbitrarily_large_integer_costs_remain_exact(self):
        large = 10 ** 400
        graph = make_graph(3, [Arc(0, 0, 1, large), Arc(1, 1, 2, large + 1),
                               Arc(2, 0, 2, 3 * large)])
        result = dijkstra(graph, 0)
        self.assertEqual(result.distance, (0, large, 2 * large + 1))
        self.assertIs(type(result.distance[2]), int)
        self.assertEqual(sum(e.weight for e in recover(result, graph, 2)), 2 * large + 1)
        self.assertTrue(verify_distances(graph, result))

    def test_costs_beyond_python_decimal_conversion_limit(self):
        # Hashing and validation must not accidentally stringify exact integers
        # through Python's default 4,300-digit decimal conversion boundary.
        large = 10 ** 5000
        graph = make_graph(3, [Arc(0, 0, 1, large), Arc(1, 1, 2, large)])
        result = dijkstra(graph, 0)
        self.assertTrue(result.distance[2] == 2 * large)
        self.assertTrue(sum(e.weight for e in recover(result, graph, 2)) == 2 * large)
        self.assertTrue(verify_distances(graph, result))

    def test_multi_source_normalization_and_roots(self):
        graph = make_graph(4, [Arc(0, 0, 1, 0), Arc(1, 1, 0, 0),
                               Arc(2, 0, 2, 5), Arc(3, 1, 2, 2), Arc(4, 2, 3, 1)])
        result = multi_source_dijkstra(graph, [1, 0, 1])
        self.assertEqual(result.sources, (0, 1))
        self.assertEqual(result.distance, (0, 0, 2, 3))
        self.assertEqual(result.parent_edge[:2], (None, None))
        self.assertEqual([e.edge_id for e in recover(result, graph, 3)], [3, 4])
        self.assertEqual(recover(result, graph, 1), ())
        self.assertTrue(result.complete)
        self.assertTrue(verify_distances(graph, result))
        d = result.diagnostics
        self.assertEqual(d.live_pops + d.stale_pops, d.improvements + len(result.sources))

    def test_reverse_preserves_edge_identity_and_reverses_reachability(self):
        graph = make_graph(3, [Arc(7, 0, 1, 2), Arc(8, 1, 2, 3)])
        backward = reverse_graph(graph)
        self.assertEqual(backward.edge_by_id[7], Arc(7, 1, 0, 2))
        self.assertEqual(backward.edge_by_id[8], Arc(8, 2, 1, 3))
        self.assertEqual(dijkstra(backward, 2).distance, (5, 3, 0))
        self.assertEqual(backward.weight_unit, graph.weight_unit)

    def test_observer_exceptions_propagate(self):
        def fail(_event):
            raise RuntimeError("observer failure")

        with self.assertRaisesRegex(RuntimeError, "observer failure"):
            dijkstra(make_graph(1, []), 0, observer=fail)

    def test_observer_events_are_immutable(self):
        events = []
        dijkstra(make_graph(1, []), 0, observer=events.append)
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            events[0].vertex = 7
        with self.assertRaises(TypeError):
            dijkstra(make_graph(1, []), 0, observer="not callable")


class ValidationTests(unittest.TestCase):
    def test_integer_validation_does_not_coerce(self):
        for value in [True, False, 1.0, "1", None, inf, float("nan")]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    require_int(value, "example")
                with self.assertRaises((TypeError, ValueError)):
                    make_graph(value, [])
                for position in range(4):
                    args = [0, 0, 1, 1]
                    args[position] = value
                    with self.assertRaises((TypeError, ValueError)):
                        make_graph(2, [Arc(*args)])
        self.assertEqual(require_int(10 ** 400, "large"), 10 ** 400)

    def test_query_vertices_must_be_valid_integers(self):
        graph = make_graph(2, [])
        for value in [True, False, 0.0, "0", None, -1, 2]:
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    dijkstra(graph, value)
                if value is not None:
                    with self.assertRaises((TypeError, ValueError)):
                        dijkstra(graph, 0, value)
                with self.assertRaises((TypeError, ValueError)):
                    multi_source_dijkstra(graph, [value])
        with self.assertRaises((TypeError, ValueError)):
            multi_source_dijkstra(graph, [])
        with self.assertRaises((TypeError, ValueError)):
            dijkstra(make_graph(0, []), 0)

    def test_graph_structure_and_metadata_validation(self):
        for rows in [
            [(0, 0, 1, -1)],
            [(0, -1, 1, 1)],
            [(0, 0, 2, 1)],
            [(0, 0, 1, 1), (0, 1, 0, 1)],
        ]:
            with self.subTest(rows=rows):
                with self.assertRaises((TypeError, ValueError)):
                    make_graph(2, (Arc(*row) for row in rows))
        with self.assertRaises((TypeError, ValueError)):
            make_graph(-1, [])
        for keyword in ["version", "weight_unit"]:
            for value in ["", None, 7]:
                with self.subTest(keyword=keyword, value=value):
                    with self.assertRaises((TypeError, ValueError)):
                        make_graph(1, [], **{keyword: value})

    def test_graph_and_nested_records_are_immutable(self):
        arc = Arc(0, 0, 1, 3)
        graph = make_graph(2, [arc])
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            graph.version = "changed"
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            arc.weight = 0
        with self.assertRaises(TypeError):
            graph.edge_by_id[0] = Arc(0, 0, 1, 0)
        self.assertIsInstance(graph.outgoing, tuple)
        self.assertTrue(all(isinstance(bucket, tuple) for bucket in graph.outgoing))
        self.assertIsInstance(graph.arcs, tuple)


if __name__ == "__main__":
    unittest.main()
