# Python API guide

## Build a validated snapshot

```python
from dijkstra_toolkit import Arc, make_graph

graph = make_graph(
    3,
    [Arc(10, 0, 1, 5), Arc(11, 1, 2, 0), Arc(12, 0, 2, 9)],
    version="network-v1",
    weight_unit="milliseconds",
)
```

`Arc(edge_id, tail, head, weight)` is immutable. `make_graph` validates every
edge, including edges outside the component you plan to search. It rejects
duplicate edge IDs and invalid endpoints. IDs, counts, endpoints, and weights
are integers, with Boolean values explicitly rejected. Counts and weights
are nonnegative; endpoints range from zero to `vertex_count - 1`. Edge IDs
may be any integer. An empty graph is valid but has no valid query endpoint.

`Graph` exposes `vertex_count`, `arcs`, `outgoing`, `edge_by_id`, `version`,
`weight_unit`, and `digest`. Construct graphs through `make_graph`. Adjacency
and edge records are immutable. Outgoing arcs are ordered by `(head, edge_id)`;
canonical arc records are ordered by edge ID. Duplicate parallel arcs with
distinct IDs remain distinct.

Heap records use `(distance, vertex_id)`, so the smaller numeric vertex ID is
settled first when costs tie. There is no insertion-serial tie key.

The content digest includes topology, weights, vertex count, version, and
unit. Keep cost-model changes visible in the version. Display labels are
external metadata and do not affect the graph digest. SHA-256 identifies a
snapshot; it does not authenticate its publisher.

## Search and recover

```python
from dijkstra_toolkit import dijkstra, recover

full = dijkstra(graph, 0)
point = dijkstra(graph, 0, target=2)
path = recover(point, graph, 2)
assert path is not None
assert sum(edge.weight for edge in path) == point.distance[2] == 5
```

`dijkstra(graph, source, target=None, *, observer=None)` returns an immutable
`ShortestPathResult`. Full search exhausts the queue. Target search stops
when that target is extracted with its current minimum label, before scanning
its outgoing edges. Discovery is insufficient for stopping.

| Result field | Meaning |
| --- | --- |
| `sources` | Tuple of starting vertex IDs; one for ordinary Dijkstra. |
| `target` | Requested target, or `None` for full search. |
| `distance` | Exact integer labels, or `math.inf` for currently unreached vertices. |
| `parent_edge` | Edge ID giving the chosen predecessor, or `None`. |
| `settled` | Whether each vertex's label was finalized by a live pop. |
| `complete` | Whether all labels are established as final. |
| `graph_version`, `graph_digest` | Snapshot binding. |
| `diagnostics` | Work counters defined below. |

When `complete` is false, non-target entries may be provisional, including
infinity. Recovery permits only the requested target. To request other routes,
perform a full search. Completeness is conservative: a target stop reports
false except on a one-vertex graph, even if some additional labels happen to
be final. An unreachable target leads to queue exhaustion and a complete result.

`recover(result, graph, target)` returns a tuple of authoritative `Arc` objects,
`None` for an unreachable target, or an empty tuple for a zero-edge source
route. It checks snapshot identity, dimensions, parent direction, continuity,
cycles, and total cost. It raises an error for an invalid or unproved result.
Do not infer a reachable route from the truthiness of the returned tuple:
an empty source route is valid; use `path is None` to detect disconnection.

## Several sources and reverse searches

```python
from dijkstra_toolkit import multi_source_dijkstra, reverse_graph

nearest = multi_source_dijkstra(graph, [0, 1])
assert nearest.distance[2] == 0  # source 1 has a zero-cost edge to 2
to_target = dijkstra(reverse_graph(graph), 2)
assert to_target.distance[0] == 5  # original direction: 0 to 2
```

`multi_source_dijkstra(graph, sources, *, observer=None)` accepts a nonempty
iterable, validates it, and canonicalizes it to sorted distinct IDs. It computes
the minimum distance from any source. Roots retain no parent. Recovering a path
ends at whichever source owns the selected witness. Equal-cost source selection
follows the vertex-ID queue policy; it is not a nearest-facility ranking rule.

For travel **to** a facility in a directed network, reverse the edges and start
from facilities. Reverse the recovered arc sequence to express the trip in the
original graph; the edge IDs are preserved. `reverse_graph` appends `:reversed`
to the version and returns a separate snapshot. See the runnable
`examples.nearest_facility` example for reconstruction and verification.

## Verify answers

```python
from dijkstra_toolkit import verify_route, verify_distances

assert verify_route(graph, 0, 2, [10, 11], 5, graph_digest=graph.digest)
assert verify_distances(graph, full)
```

`verify_route(graph, source, target, edge_ids, claimed_cost, *, graph_digest=None)`
checks direction, continuity, endpoints, and exact cost using graph records.
Supply the digest from a serialized response to check snapshot binding. It
returns false for invalid certificate data; invalid query endpoints may raise
`TypeError` or `ValueError`. A successful check proves feasibility and cost,
not that a cheaper route does not exist.

`verify_distances(graph, result)` independently checks a **complete** result:
source zeros, label validity, edge inequalities, witnessed parent paths, and
unreachable closure. It returns false for an incomplete or invalid result.
It does not call Dijkstra. Its full graph scan establishes optimality within
the supplied graph and cost model.

## Observe work

```python
events = []
traced = dijkstra(graph, 0, target=2, observer=events.append)
assert [event.vertex for event in events] == [0, 1, 2]
```

An observer receives immutable `SettledEvent` records with `vertex`,
`distance`, `rank` (starting at one), and `queue_size` after the live pop.
It runs synchronously, including for the target before stopping. Exceptions
propagate. Avoid slow callbacks during performance measurements.

| Counter | Definition |
| --- | --- |
| `live_pops` | Current labels extracted and settled. |
| `stale_pops` | Obsolete proposals discarded. |
| `scanned_edges` | Outgoing arcs inspected by expansions. |
| `improvements` | Strictly better labels written and pushed. |
| `peak_queue` | Maximum heap record count, including stale proposals. |

On queue exhaustion, `live_pops + stale_pops == improvements + len(sources)`.
An early target exit can leave records in the queue and does not expand the
target. On full runs, each reachable vertex is expanded exactly once.

## Load a file

```python
from dijkstra_toolkit.io import load_graph
graph = load_graph("data/a-g.json")
```

See [Data formats](DATA_FORMATS.md) for schemas. File labels are presentation
metadata; this library call returns the numeric graph snapshot.
