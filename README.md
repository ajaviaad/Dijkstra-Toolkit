# Dijkstra Toolkit

**Exact shortest paths, verifiable routes, and reproducible graph experiments in Python.**

Dijkstra Toolkit provides a reusable library and command-line interface for working
with directed graphs whose edge weights are nonnegative integers. Find shortest
routes, inspect settlement order, compare multiple starting points, and check
results against the graph that produced them.

Use it for independent study, teaching, and shortest-path engineering. The examples
and documentation are self-contained. Readers of **Understanding Dijkstra's
Algorithm — Theory, Proof, Implementation, and Shortest-Path Engineering** by
Adeel Javaid can also use the toolkit while studying the book.

**Requires Python 3.12 or newer. No third-party runtime dependencies.**

## Install from this repository

### 1. Clone the repository

Install Git and Python 3.12 or newer. Copy this repository's HTTPS or SSH clone URL
from its **Code** menu, then replace `REPOSITORY_URL` below with that URL:

```sh
git clone REPOSITORY_URL dijkstra-toolkit
cd dijkstra-toolkit
```

Run the following setup commands from this folder, where `pyproject.toml` is located.
Installation uses the checked-out source and does not require a PyPI release.

### 2. Create an environment and install

**macOS / Linux**

```sh
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

**Windows PowerShell**

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
```

Use an installed Python version of at least 3.12 when creating the environment.
If PowerShell blocks activation, run
`.\.venv\Scripts\python.exe -m pip install .` directly, then use
`.\.venv\Scripts\dijkstra-toolkit.exe` for the commands below. No execution-policy
change is needed.

The initial installation may download the setuptools build dependency. The
installed toolkit and its tests use Python's standard library at runtime.

### 3. Run your first route

With the environment active and the terminal at the repository root:

```sh
dijkstra-toolkit --version
dijkstra-toolkit validate data/a-g.json
dijkstra-toolkit route data/a-g.json 0 6
dijkstra-toolkit distances data/a-g.json 0
```

The included seven-vertex graph uses numeric IDs `0`–`6` for labels A–G. The route
command returns **A → B → D → E → G**, with total cost **7**:

```text
Vertices:   [0, 1, 3, 4, 6]
Edge IDs:   [0, 6, 16, 22]
Distance:   7
```

The full distance vector from A is `[0, 2, 4, 4, 5, 7, 7]`.

You can also invoke every command through the active Python interpreter:

```sh
python -m dijkstra_toolkit route data/a-g.json 0 6
```

Keep the clone to use its sample data, examples, tests, and benchmarks. Installing
the package makes the library and command available in the environment; it does
not copy the repository's sample files into your current directory. Use paths to
your own graph files when running elsewhere.

## Command-line workflows

| Task | Command |
| --- | --- |
| Validate a graph | `dijkstra-toolkit validate data/a-g.json` |
| Find one shortest route | `dijkstra-toolkit route data/a-g.json 0 6` |
| Inspect settlement order | `dijkstra-toolkit route data/a-g.json 0 6 --trace` |
| Find all distances from one source | `dijkstra-toolkit distances data/a-g.json 0` |
| Find distances from the nearest listed source | `dijkstra-toolkit nearest data/a-g.json 0 5` |
| Process a query file | `dijkstra-toolkit batch data/a-g.json data/queries.ndjson --output results.ndjson` |
| Export a graph with a highlighted route | `dijkstra-toolkit dot data/a-g.json --source 0 --target 6 > route.dot` |

Run `dijkstra-toolkit --help` for the command list or add `--help` after a subcommand.
Graph queries return JSON for use in scripts. The `dot` command writes Graphviz
DOT source; rendering it as an image requires a separate Graphviz installation.

Batch output must use a new filename and an existing parent directory. An
unreachable route is a valid result. Invalid queries produce error records and a
nonzero batch exit status. See [data formats](docs/DATA_FORMATS.md) for the result
schema and exit codes.

On a directed graph, `nearest` measures travel **from** the supplied sources. To
model travel **to** facilities, reverse the graph; the nearest-facility example
demonstrates both directions.

## Use the Python library

```python
from dijkstra_toolkit import Arc, dijkstra, make_graph, recover, verify_route

graph = make_graph(
    3,
    [
        Arc(edge_id=0, tail=0, head=1, weight=2),
        Arc(edge_id=1, tail=1, head=2, weight=3),
        Arc(edge_id=2, tail=0, head=2, weight=9),
    ],
    version="my-network-v1",
    weight_unit="minutes",
)

result = dijkstra(graph, 0, target=2)
route = recover(result, graph, 2)
assert route is not None

edge_ids = [edge.edge_id for edge in route]
assert result.distance[2] == 5
assert edge_ids == [0, 1]
assert verify_route(
    graph,
    0,
    2,
    edge_ids,
    5,
    graph_digest=result.graph_digest,
)

print({"distance": result.distance[2], "edge_ids": edge_ids})
```

The public API also includes `multi_source_dijkstra`, `reverse_graph`, and
`verify_distances`. See the [API guide](docs/API.md) for their contracts and examples.

Edge weights and finite distances use exact Python integers. Unreachable distances
are `math.inf` in Python results and `null` in CLI JSON. Parallel edges, zero weights,
isolated vertices, and self-loops are supported.

## Bring your own graph

Start with an included graph in `data/`, or use the complete JSON example in
[data formats](docs/DATA_FORMATS.md). Each directed edge has an ID, a tail vertex,
a head vertex, and a nonnegative integer weight.

- Number vertices from `0` to `vertex_count - 1`; commands use IDs, not labels.
- Give every edge a unique integer ID.
- Represent a connection usable in both directions with two directed edges.
- Use consistent scaled units, such as milliseconds, when measurements have fractions.
- Validate input before querying it. Floats, negative weights, Boolean numeric
  values, and unknown graph fields are rejected.

Both JSON graphs and checksum-protected NDJSON edge files are supported. Both
formats are loaded into an in-memory graph.

## Explore working examples

Run these from the repository root with the environment active:

```sh
python -m examples.basic_routes
python -m examples.nearest_facility
python -m examples.capacity_routes
python -m examples.replacement_paths
python -m examples.turn_penalties
python -m examples.snapshot_change
```

The examples cover route recovery and first hops, multiple starting points,
directed facility routing, capacity filters, closures, turn costs, and graph
changes. Each checks its expected result and can be adapted independently.

## Development, tests, and benchmarks

For development, install the clone in editable mode so changes to its Python
source are reflected without reinstalling:

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

The tests cover graph validation, route certificates, edge cases, CLI behavior,
and comparisons against an independent shortest-path oracle. The included GitHub
Actions workflow configures additional Python and operating-system checks.

Run a small reproducible benchmark with a fresh output directory:

```sh
python -m benchmarks.run --vertices 20 --edges 60 --seed 42 --repeats 2 --output results/smoke-001
```

This is a functional smoke run. Use more repetitions for performance analysis.
The benchmark saves its generated graph, raw observations, environment details,
summary, and file checksums. See [verification and benchmarks](docs/VERIFICATION.md)
for measurement methods and interpretation.

## Repository guide

```text
dijkstra_toolkit/   Graph types, solvers, verifiers, loaders, and CLI
data/              Sample graphs, query files, and expected results
examples/          Independent applications to run or adapt
tests/             Regression, oracle, property, and CLI tests
benchmarks/        Seeded experiments and measurement output
docs/              API, formats, concepts, and verification guides
.github/workflows/ Automated test configuration
pyproject.toml     Package metadata and installation settings
```

| Guide | Purpose |
| --- | --- |
| [API](docs/API.md) | Integrate the library and understand result contracts |
| [Data formats](docs/DATA_FORMATS.md) | Create graphs and query files; interpret output |
| [Concepts](docs/CONCEPTS.md) | Understand correctness, modeling, ties, and complexity |
| [Verification and benchmarks](docs/VERIFICATION.md) | Test changes and measure performance |
| [Contributing](CONTRIBUTING.md) | Develop and review improvements |

## Correctness and scope

Results carry a graph version and content digest. Route recovery checks the graph
snapshot, edge direction, continuity, and cost. A target search stops only when
the target is settled and may leave the full-source result incomplete; recover
the requested target or run a full search when other destinations are needed.

`verify_route` checks feasibility and claimed cost. It does **not** independently
prove that a route is shortest. `verify_distances` checks optimality for a complete
result using graph-wide conditions and parent witnesses.

Tie handling is deterministic for the same graph and vertex/edge IDs, regardless
of input record order. It selects one shortest route without promising the fewest
hops or a lexicographically smallest path.

This release handles static graphs with nonnegative integer costs. Negative-weight
algorithms, A*, bidirectional search, schedules, ECMP, dynamic repair, and
large-network acceleration are outside its implemented scope. The toolkit does
not impose service deadlines or memory admission limits.

## Troubleshooting

| Problem | Resolution |
| --- | --- |
| `dijkstra-toolkit` is not found | Activate the environment used for installation, or use its Python executable with `-m dijkstra_toolkit`. |
| `No module named dijkstra_toolkit` | Install with the same interpreter that runs your program: `python -m pip install .` from the repository root. |
| Python version is unsupported | Create the environment with Python 3.12 or newer. |
| A sample file cannot be found | Run from the repository root or supply the file's full path. |
| A weight or vertex is rejected | Use nonnegative integer weights and vertex IDs in the declared range. |
| Batch or benchmark output already exists | Choose a new output filename or directory. |
| A graph snapshot does not match | Recompute the result after changing the graph. |

## License

Code and original repository documentation are provided under the
[MIT License](LICENSE).

Current package version: **0.1.0**.
