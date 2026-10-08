# Shortest paths and modeling

## What the solver minimizes

A route is a sequence of directed edges. Its cost is the sum of their weights.
Dijkstra finds a minimum-cost route from a source when all weights are
nonnegative. A minimum additive cost may represent distance, time, price, or
a carefully defined combination; the graph model decides which question is
being answered.

Capacity is usually a bottleneck constraint, not an additive cost. Reliability
probabilities do not add. Turn costs depend on how a location was entered.
Filter infeasible edges or expand the state space before searching. The
capacity and turn examples demonstrate both approaches.

## Why settlement is safe

Each tentative label is the cost of a route already discovered. Relaxing an
edge from `u` to `v` replaces the label for `v` only when
`distance[u] + weight(u, v)` is strictly smaller. The queue returns the least
current proposal. Because extending a path with a nonnegative edge cannot
decrease its cost, no unseen continuation can later improve a settled vertex.

The implementation pushes a new heap record after an improvement. Old records
remain until popped; a record whose key no longer matches the current label
is stale and is skipped. Equal proposals do not replace parents, so zero-cost
cycles cannot create parent cycles through equality updates.

Consider edges `s→t:10`, `s→a:1`, and `a→t:1`. Discovering `t` gives cost 10;
settling `a` improves it to 2. A target search must stop on settlement, not on
insertion into the queue.

## Meaningful identities and ties

Vertices use dense numeric IDs, with optional labels for display. Every edge
has its own identity, so parallel roads or network links remain distinguishable.
An undirected link is represented by two directed arcs. Removing only one of
them closes only that direction.

Adjacency is sorted by head and edge ID, then heap ties use the smaller vertex ID.
Strict relaxation keeps the first equal-cost witness. This is reproducible
for fixed IDs and data, independent of file record ordering. Renumbering
vertices may choose a different optimal route. Determinism does not imply a
secondary objective such as fewest turns or fewest hops; model that objective
explicitly if it matters.

This toolkit returns one route. A network of all tight edges can contain
cycles when zero weights exist, so it is not always a directed acyclic graph.
Counting all shortest simple paths and building loop-free equal-cost forwarding
require additional algorithms.

## Numeric policy

All finite costs are Python integers. They do not overflow at a fixed 32- or
64-bit boundary. Large integers still consume memory and increase arithmetic
cost. Infinity is only an internal sentinel and is never added to a finite
path cost. JSON output uses `null` for unreachable distances.

Do not round measurements independently at each relaxation. Choose a fixed
unit at ingestion, such as microseconds, and record it with the graph. This
release rejects negative weights, floats, strings, NaN, infinity, and Boolean
values as weights. It does not silently turn a malformed value into zero.

## Complexity and scale

For `n` vertices and `m` directed edges, graph construction sorts adjacency and
edge records, costs up to `O(m log(m + 1) + n)`, and stores `O(n + m)` data.
Single-source lazy-heap search costs `O(n + (m_r + 1) log(m_r + 2))` in the
worst case, where `m_r` is the number of scanned edges; initialization and
result materialization cost `O(n)`. The queue can retain `O(m_r + 1)` records.
Multi-source search adds initial source records. These bounds count arithmetic
as constant-time; very large integer bit lengths increase costs.

The graph is kept in memory. NDJSON avoids a giant array in the file format,
but the loader retains its edge bytes for digest-consistent parsing and builds
an in-memory graph. This is not an external-memory engine. Trace collection
also adds memory and callback overhead. Measure representative workloads before
choosing a more specialized queue or representation.

## Choosing another algorithm

| Situation | Suitable direction |
| --- | --- |
| Every edge has the same cost | Breadth-first search can be simpler. |
| Static, nonnegative additive costs | This toolkit's Dijkstra implementation. |
| Negative edges | Bellman–Ford or a valid reweighting method; reject negative cycles where relevant. |
| A useful consistent target heuristic | A* can reduce exploration. |
| Many large-network route queries | Preprocessing and specialized data structures may help. |
| Schedules or departure-dependent costs | A time-dependent model with an appropriate FIFO/waiting contract. |
| Resource consumption accumulates along a route | Expanded resource state or a constrained-path algorithm. |

Only Dijkstra and its multi-source form are implemented here. Reverse-graph
search is a modeling transformation, not bidirectional search. A snapshot
change requires a new query; retaining a feasible old route does not establish
that it remains optimal.
