# Connection to the book

This toolkit accompanies **Understanding Dijkstra's Algorithm — Theory, Proof,
Implementation, and Shortest-Path Engineering** by Adeel Javaid (2026 manuscript).
It is independently usable and arranged around practical tasks. The code is
an integrated implementation with additional validation and snapshot binding;
it is not a literal assembly of every listing in the manuscript. This release
uses vertex-ID heap tie keys; the manuscript reference uses insertion serials.
Both retain strict improvement and deterministic behavior, but can choose
different witnesses when several routes have the same minimum cost.

| Theme | Repository material |
| --- | --- |
| Graphs that preserve direction, identity, and cost meaning | `graph.py`, data format guide, capacity and turn examples |
| Label setting, relaxation, and priority queues | `algorithms.py`, settlement traces, regression tests |
| Route recovery and certificates | `certificates.py`, `verify_route`, `verify_distances` |
| Numeric and result contracts | Integer validation, snapshot digests, partial-result restrictions |
| Multiple starting points and destination searches | Multi-source solver and nearest-facility example |
| Network changes and cached answers | Replacement-path and snapshot-change examples |
| Reproducible algorithm engineering | Seeded tests, batch input, benchmark manifest and raw timings |

## The A–G network

`data/a-g.json` contains these 13 undirected links, each stored as two arcs:

```text
A–B 2    A–C 4    A–D 5    B–D 2    B–E 4
B–G 7    C–F 3    C–G 5    D–E 1    D–F 5
D–G 5    E–G 2    F–G 1
```

From A, the distances to A–G are `0, 2, 4, 4, 5, 7, 7`.
The selected route to G is `A–B–D–E–G`, with cost `2+2+1+2 = 7`.
The links D–F and D–G retain weight 5; after D improves to 4, their candidates
are 9. `data/a-g.expected.json` records the all-pairs distance matrix and the
selected route for regression use.

The capacity and replacement-path examples use small networks drawn from the
manuscript's applications. Other examples are original demonstrations of the
same modeling principles. None require reading a particular chapter first.

## Deliberate scope

The book discusses more than this release implements. A*, bidirectional
search, Bellman–Ford, Johnson reweighting, time-dependent schedules, ECMP,
specialized priority queues, CSR, contraction hierarchies, and dynamic repair
are topics for further implementations, not hidden features of this package.
The concept guide helps identify when they would be relevant.

The repository ships its own source, fixtures, tests, and documentation. It
does not include the manuscript text or figures. Its MIT license applies to
the repository; it does not relicense the book.
