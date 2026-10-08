# Graph and result formats

## A single JSON graph

Save the following as `my-graph.json`, then run
`python -m dijkstra_toolkit route my-graph.json 0 2`.

```json
{
  "schema": "dijkstra-toolkit-v1",
  "vertex_count": 3,
  "graph_version": "example-v1",
  "weight_unit": "minutes",
  "labels": ["Origin", "Transfer", "Destination"],
  "edges": [
    {"edge_id": 0, "tail": 0, "head": 1, "weight": 2},
    {"edge_id": 1, "tail": 1, "head": 2, "weight": 3},
    {"edge_id": 2, "tail": 0, "head": 2, "weight": 9}
  ]
}
```

The route has cost 5 and edge IDs `[0, 1]`. `labels` is the only optional field;
if supplied, it must contain one unique string per vertex. Labels are used for
DOT display, while API and CLI endpoints remain numeric IDs. The graph version
and unit must be nonempty strings. Edge IDs must be unique integers. All
endpoints must exist, and weights must be nonnegative integers.

The loader rejects unknown fields, duplicate JSON keys, unsupported schemas,
missing fields, Boolean numeric values, and nonstandard NaN/Infinity literals.
JSON numbers such as `2.0` or `2e0` are floats and are rejected as weights.
If you have capacities, restrictions, or timestamps, preprocess them into the
declared graph instead of adding unsupported fields to an edge record.

Python's normal decimal integer conversion limit applies to JSON input/output
(usually 4,300 digits). The in-memory Python API handles larger integers without
changing that process setting. Interoperability also depends on the consumer:
JavaScript number parsing, for example, cannot exactly represent all large
integers. Use a consumer with arbitrary-precision integer support for huge costs.

## Checksum-protected NDJSON edges

For edge-per-line data, use `weighted-digraph-v1` metadata with the same
vertex count, version, unit, and optional labels. Replace `edges` with:

| Field | Meaning |
| --- | --- |
| `edge_file` | Relative path from the metadata file to an NDJSON edge file. |
| `sha256_base64` | Canonical base64 encoding of the 32-byte SHA-256 file digest. |

Every nonblank edge line has the same four fields as the JSON example. Blank
lines are ignored. The file checksum covers the exact bytes, including blank
lines and line endings. Changing Windows/Unix line endings changes it.

`data/ndjson/metadata.json` and `data/ndjson/edges.ndjson` form a complete
working example. Run:

```sh
python -m dijkstra_toolkit validate data/ndjson/metadata.json
python -m dijkstra_toolkit route data/ndjson/metadata.json 0 6
```

Generate a digest for your own edge file in Python:

```python
from pathlib import Path
import base64
import hashlib

raw = Path("edges.ndjson").read_bytes()
print(base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii"))
```

Insert that value in the metadata after checking the intended data. The loader
verifies and parses the same byte buffer. It still builds the whole graph in
memory; NDJSON support does not imply streaming-memory graph construction.

The edge-file checksum and the graph content digest have different purposes.
The first identifies input bytes. The second identifies validated numeric
content and metadata, independent of edge order and whitespace. See
`make_graph`'s docstring for its canonical digest encoding.

## Query files

Batch queries are UTF-8 NDJSON. Each nonblank line is a separate query:

```jsonl
{"query_id":"delivery-001","source":0,"target":2}
{"query_id":"delivery-002","source":2,"target":0}
```

`query_id` is optional and must be a string when present. IDs do not have to be
unique; output `query_line` identifies the input line unambiguously. `source`
and `target` are required integers; unknown query fields are rejected. Blank
lines are skipped and do not produce records.

```sh
python -m dijkstra_toolkit batch data/disconnected.json data/queries-with-errors.ndjson --output batch-results.ndjson
```

This deliberate mixed example writes one reachable answer, one unreachable
answer, and one error record. It finishes the output but exits with status 1.
The normal `data/queries.ndjson` file is designed for `data/a-g.json` and has
only valid queries.

## Results and errors

Route JSON includes `schema: "dijkstra-result-v1"`, `algorithm`,
`implementation_version`, `graph_version`, `graph_digest`, `weight_unit`,
`sources`, `source`, `target`, `complete`, and `diagnostics`.

| Outcome | `status` | `distance` | `edge_ids` | `vertices` |
| --- | --- | --- | --- | --- |
| Reachable target | `reachable` | Exact integer | Array of edge IDs | Source through target |
| Source equals target | `reachable` | 0 | `[]` | `[source]` |
| Unreachable target | `unreachable` | `null` | `null` | `null` |
| Invalid batch query | `error` | Absent | Absent | Absent |

Reachable CLI routes are independently rescored before publication;
`certificate_status` is `feasible_cost_verified`. For unreachable answers it
is `not_applicable`. This field is a feasibility/cost check, not an independent
optimality proof. Use `verify_distances` on a full library result for that proof.

The `complete` field refers to full-source completeness, not whether the
requested route is ready. A reachable point result is final even when
`complete` is false. Full `distances` and `nearest` output uses `distances`,
`parent_edge`, and `settled` arrays, with null distances for unreachable vertices.
Route output does not expose provisional non-target labels.

`--trace` adds live settlement records with vertex, distance, one-based rank,
and queue size. It is a settlement trace, not every relaxation or stale pop.

Batch records add `query_line` and the supplied `query_id`. A malformed query
adds a contextual `error` message and the graph identity. Graph loading fails
before the output is created. Standard output contains a batch summary, while
individual records go to the requested file.

| Process exit status | Meaning |
| --- | --- |
| 0 | Success, including unreachable routes. |
| 1 | Batch output completed, but one or more query rows failed. |
| 2 | Usage, graph validation, or file error. |

Batch output is written to an adjacent temporary file, flushed, and published
with a no-overwrite hard link. Existing files are preserved even if created
concurrently. The output parent folder must exist and its filesystem must
support hard links; otherwise the command fails without publishing the final
output. Temporary files are removed on normal error handling. A forced process
termination can leave a hidden temporary file, which is not a completed result.

## Included data

| File | Purpose |
| --- | --- |
| `a-g.json` | Seven-vertex bidirectional network from the manuscript. |
| `a-g.expected.json` | Expected distances, route, and all-pairs matrix; a fixture, not graph input. |
| `disconnected.json` | Directed reachability and an isolated vertex. |
| `zero-and-parallel.json` | Equal-cost alternatives, parallel arcs, and a zero-cost cycle. |
| `queries.ndjson` | Three valid queries for A–G. |
| `queries-with-errors.ndjson` | Mixed outcomes for the disconnected graph. |
| `ndjson/metadata.json` | Checksum-protected alternative representation of A–G. |
