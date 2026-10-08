# Dijkstra Toolkit

Find shortest routes, inspect how Dijkstra's algorithm works, and verify the
answers on your own weighted networks. This repository provides a reusable
Python library and command-line tools with no runtime dependencies.

It also accompanies **Understanding Dijkstra's Algorithm — Theory, Proof,
Implementation, and Shortest-Path Engineering** by Adeel Javaid. Everything
needed to use the software is documented here; the book is optional. Files are
organized by capability, with no chapter sequence to follow.

## Start in one minute

Install **Python 3.12 or newer**, extract the ZIP, and open a terminal inside
the `dijkstra-toolkit` folder. These commands work directly from the source:

```sh
python -m dijkstra_toolkit route data/a-g.json 0 6
python -m dijkstra_toolkit distances data/a-g.json 0
python -m unittest discover -s tests -v
```

Use `python3` if that is your Python command. On Windows, `py -3.12` is another
option when that version is installed. No installation or network connection
is needed to run the toolkit once Python is available.

The first command finds **A → B → D → E → G**, with total cost **7**. Vertex
IDs 0–6 correspond to A–G. The full distance vector is
`[0, 2, 4, 4, 5, 7, 7]`. Output is JSON so scripts can use it directly.

For installation, Windows instructions, troubleshooting, and publishing this
folder as your own repository, see [INSTRUCTIONS.md](INSTRUCTIONS.md).

## What you can do

| Task | Entry point |
| --- | --- |
| Find one shortest route | `route GRAPH SOURCE TARGET` |
| Find distances from one vertex | `distances GRAPH SOURCE` |
| Find the closest of several starting points | `nearest GRAPH SOURCES...` |
| Inspect settlement order | `route GRAPH SOURCE TARGET --trace` |
| Validate graph data | `validate GRAPH` |
| Run a query file | `batch GRAPH QUERIES --output results.ndjson` |
| Draw a graph with optional route highlighting | `dot GRAPH --source S --target T` |
| Integrate shortest paths into Python | `dijkstra_toolkit` public API |

Prefix commands with `python -m dijkstra_toolkit`. Run
`python -m dijkstra_toolkit --help` for help, or add `--help` after a command.

## Use the library

```python
from dijkstra_toolkit import Arc, make_graph, dijkstra, recover, verify_route

graph = make_graph(
    3,
    [Arc(0, 0, 1, 2), Arc(1, 1, 2, 3), Arc(2, 0, 2, 9)],
    version="my-network-v1",
    weight_unit="minutes",
)
result = dijkstra(graph, 0, target=2)
route = recover(result, graph, 2)
assert route is not None
assert result.distance[2] == 5
assert [edge.edge_id for edge in route] == [0, 1]
assert verify_route(graph, 0, 2, [0, 1], 5, graph_digest=result.graph_digest)
```

Distances and edge weights use exact, nonnegative Python integers. Directed
edges, parallel edges, zero weights, isolated vertices, and self-loops are
supported. Use scaled units such as milliseconds or cents for fractional
measurements. Invalid data is rejected rather than silently converted.

## Explore working examples

Run these from the repository root:

```sh
python -m examples.basic_routes
python -m examples.nearest_facility
python -m examples.capacity_routes
python -m examples.replacement_paths
python -m examples.turn_penalties
python -m examples.snapshot_change
```

Each example explains its model and checks its expected result. The examples
cover route recovery and first hops, multi-source search, directed travel to
facilities, capacity filters, closures, turn costs, and changes to a network.

## Repository guide

```text
dijkstra_toolkit/   Reusable graph, solver, verifier, loader, and CLI
data/              Small graphs, query files, and expected results
examples/          Independent applications you can run or adapt
tests/             Regressions, independent oracle, and CLI tests
benchmarks/        Seeded experiment with raw timings and environment data
docs/              API, data formats, concepts, and verification guides
.github/workflows/ Automated tests for a future GitHub repository
```

- [API guide](docs/API.md) — contracts and examples for developers.
- [Data formats](docs/DATA_FORMATS.md) — bring your own network and queries.
- [Concepts](docs/CONCEPTS.md) — correctness, modeling, ties, and complexity.
- [Verification and benchmarks](docs/VERIFICATION.md) — test and measure changes.
- [Book connection](docs/BOOK_NOTES.md) — thematic correspondence and scope.
- [Contributing](CONTRIBUTING.md) — change and review the code.

## Guarantees and boundaries

A route result includes its graph version and content digest. Recovery checks
snapshot identity, direction, continuity, and cost. Target searches stop only
when the target is settled; other provisional labels cannot be recovered as
final routes. Full results can also be checked by an independent optimality
verifier. A route's feasibility check alone does **not** prove optimality.

Tie handling is deterministic for the same vertex and edge IDs, regardless of
input record order. It selects one shortest route, without promising the
fewest hops or a lexicographically smallest path.

This release focuses on static graphs with nonnegative integer costs. It does
not implement negative-weight algorithms, A*, bidirectional search, schedules,
ECMP, dynamic repair, or large-network acceleration. It is a reference toolkit
and experiment starting point, without service deadlines or memory admission
controls. See the guides before adapting it to those workloads.

## License

The repository code and its original documentation are provided under the
[MIT License](LICENSE). The book manuscript is not included and its publishing
rights are separate. Version: **0.1.0**.
