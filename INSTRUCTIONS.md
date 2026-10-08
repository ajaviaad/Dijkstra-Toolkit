# Setup and usage instructions

## 1. Extract and check Python

Extract the ZIP into a normal folder. Open a terminal in `dijkstra-toolkit`,
where `README.md` and `pyproject.toml` are located.

```sh
python --version
python -m dijkstra_toolkit --help
```

Python must be version 3.12 or newer. If the command is unavailable, try
`python3` on macOS/Linux or `py -3.12` on Windows. Substitute that command in
the examples below. The standard-library source mode needs no package download.

## 2. Run a complete workflow

```sh
python -m dijkstra_toolkit validate data/a-g.json
python -m dijkstra_toolkit route data/a-g.json 0 6 --trace
python -m dijkstra_toolkit distances data/a-g.json 0
python -m dijkstra_toolkit nearest data/a-g.json 0 5
python -m dijkstra_toolkit batch data/a-g.json data/queries.ndjson --output my-results.ndjson
python -m unittest discover -s tests -v
```

The batch command refuses an existing output file. Choose a new name when
repeating an experiment. It emits one result per query and returns a nonzero
exit status if any query is invalid. Unreachable routes are valid answers.

To export a graph with the A–G route highlighted:

```sh
python -m dijkstra_toolkit dot data/a-g.json --source 0 --target 6 > route.dot
```

The resulting file is Graphviz DOT source. If Graphviz is separately installed,
`dot -Tsvg route.dot -o route.svg` renders it. Graphviz is optional and is not
required for solving routes or running tests.

## 3. Install for use outside this folder

Installation is optional. Create an isolated environment and install this
local folder in editable mode. The initial package installation may download
the setuptools build dependency; runtime and tests use no third-party packages.

macOS / Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/dijkstra-toolkit route data/a-g.json 0 6
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\dijkstra-toolkit.exe route data/a-g.json 0 6
```

These commands call the environment directly, so activation and shell policy
changes are unnecessary. In that environment, you can import `dijkstra_toolkit`
from your own program regardless of its folder.

## 4. Add your network

Copy `data/disconnected.json` as a small starting point. Set `vertex_count`,
`graph_version`, `weight_unit`, and your directed edge records. Vertex IDs
must be consecutive integers from 0 to `vertex_count - 1`; edge IDs must be
unique integers. Optional `labels` are for display; commands take numeric IDs.

For a road usable in both directions, add two records with different edge IDs.
Costs may differ by direction. For travel times such as 1.25 seconds, use 1250
milliseconds consistently. Do not mix units or use Boolean values as numbers.

Validate the graph, run a known route, and check it against your source data
before running batches. See [Data formats](docs/DATA_FORMATS.md) for full
examples and the checksum-protected NDJSON format.

## 5. Create a Git repository

The ZIP is a complete repository folder without Git history. Git is optional
for use. To start tracking it locally, run these commands inside the folder:

```sh
git init
git add .
git commit -m "Add standalone Dijkstra toolkit"
```

If Git requests your name and email, configure your own identity. To publish,
create an empty repository in your chosen hosting service and follow its
instructions to add the remote and push. This archive has not been published
to GitHub or PyPI and does not depend on a particular remote URL.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| `No module named dijkstra_toolkit` | Run from the extracted root or install it in the Python environment being used. |
| Python version error | Use Python 3.12 or newer. |
| Unknown vertex | Use a numeric ID in the graph's declared range, not a label such as A. |
| Invalid weight | Use an integer at least zero. Strings, floats, Boolean values, and negative values are rejected. |
| Checksum mismatch | The NDJSON bytes changed. Validate the intended data and update its metadata checksum deliberately. |
| Existing output error | Choose a fresh batch output path. |
| Snapshot mismatch | Recompute after changing the graph; do not reconstruct old results against new data. |
| Incomplete result | Use `distances` or `dijkstra(graph, source)` when you need a full tree. |

For environment details, see the official [Python virtual environment guide](https://docs.python.org/3/library/venv.html)
and [Python packaging guide](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
