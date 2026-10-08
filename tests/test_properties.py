"""Seeded differential checks use an independent matrix relaxation schedule."""

from math import inf
import random
import unittest

from dijkstra_toolkit import (Arc, dijkstra, make_graph, multi_source_dijkstra,
                             recover, reverse_graph, verify_distances, verify_route)


def matrix_oracle(vertex_count, rows):
    """Floyd–Warshall built from original records, not solver adjacency."""
    matrix = [[inf] * vertex_count for _ in range(vertex_count)]
    for v in range(vertex_count):
        matrix[v][v] = 0
    for _edge_id, tail, head, weight in rows:
        matrix[tail][head] = min(matrix[tail][head], weight)
    for k in range(vertex_count):
        for i in range(vertex_count):
            if matrix[i][k] == inf:
                continue
            for j in range(vertex_count):
                if matrix[k][j] == inf:
                    continue
                candidate = matrix[i][k] + matrix[k][j]
                if candidate < matrix[i][j]:
                    matrix[i][j] = candidate
    return matrix


def generated_rows(seed, vertex_count):
    rng = random.Random(seed)
    rows = []
    for u in range(vertex_count):
        for v in range(vertex_count):
            if rng.random() < 0.27:
                rows.append((len(rows), u, v, rng.choice([0, 0, 1, 1, 2, 3, 8])))
                if rng.random() < 0.12:
                    rows.append((len(rows), u, v, rng.choice([0, 1, 4, 9])))
    return rows


def build(vertex_count, rows):
    return make_graph(vertex_count, (Arc(*row) for row in rows))


class DifferentialTests(unittest.TestCase):
    def test_one_hundred_seeded_graphs_all_sources_and_targets(self):
        for seed in range(100):
            n = 1 + seed % 8
            rows = generated_rows(seed, n)
            graph = build(n, rows)
            expected = matrix_oracle(n, rows)
            authoritative = {row[0]: row for row in rows}
            for source in range(n):
                with self.subTest(seed=seed, source=source):
                    actual = dijkstra(graph, source)
                    self.assertEqual(actual.distance, tuple(expected[source]))
                    self.assertTrue(verify_distances(graph, actual))
                    self.assertLessEqual(actual.diagnostics.live_pops, n)
                    self.assertEqual(actual.diagnostics.live_pops + actual.diagnostics.stale_pops,
                                     actual.diagnostics.improvements + 1)
                    reachable = {v for v, cost in enumerate(expected[source]) if cost != inf}
                    self.assertEqual(actual.diagnostics.scanned_edges,
                                     sum(1 for _id, u, _v, _w in rows if u in reachable))
                    for target in range(n):
                        route = recover(actual, graph, target)
                        early = dijkstra(graph, source, target)
                        self.assertEqual(early.distance[target], expected[source][target])
                        early_route = recover(early, graph, target)
                        if expected[source][target] == inf:
                            self.assertIsNone(route)
                            self.assertIsNone(early_route)
                            continue
                        self.assertIsNotNone(route)
                        self.assertIsNotNone(early_route)
                        for witness in (route, early_route):
                            cursor, cost = source, 0
                            for arc in witness:
                                _id, tail, head, weight = authoritative[arc.edge_id]
                                self.assertEqual(cursor, tail)
                                cursor, cost = head, cost + weight
                            self.assertEqual(cursor, target)
                            self.assertEqual(cost, expected[source][target])
                            self.assertTrue(verify_route(graph, source, target,
                                                         [a.edge_id for a in witness], cost))

    def test_multi_source_and_reverse_agree_with_matrix(self):
        for seed in range(30):
            n = 2 + seed % 7
            rows = generated_rows(1000 + seed, n)
            expected = matrix_oracle(n, rows)
            graph = build(n, rows)
            sources = [0, n - 1]
            nearest = multi_source_dijkstra(graph, reversed(sources))
            self.assertEqual(nearest.distance,
                             tuple(min(expected[s][v] for s in sources) for v in range(n)))
            self.assertTrue(verify_distances(graph, nearest))
            reversed_graph = reverse_graph(graph)
            for source in range(n):
                self.assertEqual(dijkstra(reversed_graph, source).distance,
                                 tuple(expected[v][source] for v in range(n)))


class MetamorphicTests(unittest.TestCase):
    def test_scaling_renaming_reordering_and_isolated_vertices(self):
        for seed in range(25):
            n = 2 + seed % 6
            rows = generated_rows(2000 + seed, n)
            baseline_graph = build(n, rows)
            rng = random.Random(seed)
            permutation = list(range(n))
            rng.shuffle(permutation)
            renamed = build(n, [(eid, permutation[u], permutation[v], w) for eid, u, v, w in rows])
            scaled = build(n, [(eid, u, v, w * 7) for eid, u, v, w in rows])
            isolated = build(n + 2, rows)
            reordered_rows = list(rows)
            rng.shuffle(reordered_rows)
            reordered = build(n, reordered_rows)
            self.assertEqual(baseline_graph.digest, reordered.digest)
            for source in range(n):
                with self.subTest(seed=seed, source=source):
                    baseline = dijkstra(baseline_graph, source)
                    mapped = dijkstra(renamed, permutation[source])
                    self.assertEqual(tuple(mapped.distance[permutation[v]] for v in range(n)), baseline.distance)
                    self.assertEqual(dijkstra(scaled, source).distance,
                                     tuple(inf if d == inf else d * 7 for d in baseline.distance))
                    self.assertEqual(dijkstra(isolated, source).distance, baseline.distance + (inf, inf))
                    repeated = dijkstra(reordered, source)
                    self.assertEqual(repeated.distance, baseline.distance)
                    self.assertEqual(repeated.parent_edge, baseline.parent_edge)

    def test_heavier_parallel_edge_and_single_incoming_sink(self):
        for seed in range(20):
            n = 3 + seed % 5
            rows = generated_rows(3000 + seed, n)
            baseline = build(n, rows)
            added = list(rows)
            if rows:
                _eid, u, v, w = rows[0]
                added.append((len(added), u, v, w + 100))
            parallel = build(n, added)
            sink_rows = rows + [(len(rows), n - 1, n, 4)]
            sink = build(n + 1, sink_rows)
            for source in range(n):
                original = dijkstra(baseline, source).distance
                self.assertEqual(dijkstra(parallel, source).distance, original)
                result = dijkstra(sink, source).distance
                self.assertEqual(result[:n], original)
                self.assertEqual(result[n], inf if original[n - 1] == inf else original[n - 1] + 4)

    def test_adding_a_constant_is_not_a_valid_scaling_property(self):
        rows = [(0, 0, 2, 5), (1, 0, 1, 2), (2, 1, 2, 2)]
        original, shifted = build(3, rows), build(3, [(e, u, v, w + 2) for e, u, v, w in rows])
        self.assertEqual([e.edge_id for e in recover(dijkstra(original, 0), original, 2)], [1, 2])
        self.assertEqual([e.edge_id for e in recover(dijkstra(shifted, 0), shifted, 2)], [0])


if __name__ == "__main__":
    unittest.main()
