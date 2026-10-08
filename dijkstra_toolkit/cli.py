"""Portable command-line tools for inspecting and querying weighted digraphs."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

from . import __version__
from .algorithms import dijkstra, multi_source_dijkstra, recover
from .certificates import verify_route
from .graph import Graph, require_int
from .io import GraphFormatError, load_graph_with_labels, parse_json


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _metadata(graph: Graph, algorithm: str = "dijkstra") -> dict[str, Any]:
    return {"schema": "dijkstra-result-v1", "algorithm": algorithm,
            "implementation_version": __version__, "graph_version": graph.version,
            "graph_digest": graph.digest, "weight_unit": graph.weight_unit}


def _result_metadata(graph: Graph, result: Any,
                     algorithm: str = "dijkstra") -> dict[str, Any]:
    record = _metadata(graph, algorithm)
    record.update(sources=list(result.sources), target=result.target,
                  complete=result.complete,
                  diagnostics={key: getattr(result.diagnostics, key) for key in
                               ("live_pops", "stale_pops", "scanned_edges", "improvements", "peak_queue")})
    return record


def _route(graph: Graph, source: int, target: int, trace: bool = False) -> dict[str, Any]:
    events: list[dict[str, int]] = []

    def observe(event: Any) -> None:
        events.append({key: getattr(event, key) for key in
                       ("vertex", "distance", "rank", "queue_size")})

    result = dijkstra(graph, source, target, observer=observe if trace else None)
    arcs = recover(result, graph, target)
    edge_ids = None if arcs is None else [arc.edge_id for arc in arcs]
    if arcs is not None and not verify_route(
            graph, source, target, edge_ids, result.distance[target],
            graph_digest=result.graph_digest):
        raise ValueError("computed route failed feasibility and cost verification")
    record = _result_metadata(graph, result)
    record.update(source=source,
                  status="unreachable" if arcs is None else "reachable",
                  certificate_status="not_applicable" if arcs is None else "feasible_cost_verified",
                  distance=None if arcs is None else result.distance[target],
                  edge_ids=edge_ids,
                  vertices=None if arcs is None else [source] + [arc.head for arc in arcs])
    if trace:
        record["trace"] = events
    return record


def _distances(graph: Graph, sources: list[int], multi: bool = False) -> dict[str, Any]:
    result = multi_source_dijkstra(graph, sources) if multi else dijkstra(graph, sources[0])
    record = _result_metadata(graph, result, "multi-source-dijkstra" if multi else "dijkstra")
    record.update(status="complete", distances=[None if distance == math.inf else distance
                                               for distance in result.distance],
                  parent_edge=list(result.parent_edge), settled=list(result.settled))
    return record


def render_dot(graph: Graph, labels: tuple[str, ...] | None = None,
               source: int | None = None, target: int | None = None) -> str:
    """Build safely quoted Graphviz DOT; optional route highlighting uses edge IDs."""
    if (source is None) != (target is None):
        raise ValueError("DOT route highlighting requires both source and target")
    highlighted: set[int] = set()
    if source is not None and target is not None:
        result = dijkstra(graph, source, target)
        route = recover(result, graph, target)
        if route is not None:
            ids = [arc.edge_id for arc in route]
            if not verify_route(graph, source, target, ids, result.distance[target],
                                graph_digest=graph.digest):
                raise ValueError("route verification failed")
            highlighted.update(ids)
    lines = ["digraph shortest_paths {", '  rankdir="LR";', '  node [shape="circle"];']
    for vertex in range(graph.vertex_count):
        label = labels[vertex] if labels is not None else str(vertex)
        attrs = [f"label={_json(label)}"]
        if vertex == source:
            attrs.extend(['style="filled"', 'fillcolor="#dbeafe"'])
        if vertex == target:
            attrs.append('peripheries="2"')
        lines.append(f"  v{vertex} [{', '.join(attrs)}];")
    for arc in graph.arcs:
        attrs = [f"label={_json(f'e{arc.edge_id}: {arc.weight}')}"]
        if arc.edge_id in highlighted:
            attrs.extend(['color="#2563eb"', 'penwidth="3"'])
        lines.append(f"  v{arc.tail} -> v{arc.head} [{', '.join(attrs)}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _query(value: Any, context: str) -> tuple[str | None, int, int]:
    if not isinstance(value, dict):
        raise GraphFormatError(f"{context}: query must be a JSON object")
    if set(value) - {"query_id", "source", "target"}:
        raise GraphFormatError(f"{context}: unknown query field(s): "
                               + ", ".join(sorted(set(value) - {"query_id", "source", "target"})))
    if "source" not in value or "target" not in value:
        raise GraphFormatError(f"{context}: query requires source and target")
    query_id = value.get("query_id")
    if "query_id" in value and not isinstance(query_id, str):
        raise GraphFormatError(f"{context}: query_id must be a string")
    source = require_int(value["source"], "source")
    target = require_int(value["target"], "target")
    return query_id, source, target


def _batch(graph: Graph, graph_path: Path, queries: Path, output: Path) -> int:
    # Linking an adjacent temporary file publishes atomically without replacing an
    # existing destination, including one created while the queries are running.
    if output.resolve() in (graph_path.resolve(), queries.resolve()):
        raise ValueError("batch output must differ from the graph and query input paths")
    if output.exists() or output.is_symlink():
        raise ValueError(f"{output}: output already exists; choose a new output path")
    failed = processed = 0
    temporary: Path | None = None
    try:
        with queries.open("rb") as input_file:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                             dir=output.parent, prefix=f".{output.name}.",
                                             suffix=".tmp", delete=False) as output_file:
                temporary = Path(output_file.name)
                for lineno, line in enumerate(input_file, 1):
                    if not line.strip():
                        continue
                    context = f"{queries}: line {lineno}"
                    value: Any = None
                    try:
                        value = parse_json(line, context)
                        query_id, source, target = _query(value, context)
                        record = _route(graph, source, target)
                        if query_id is not None:
                            record["query_id"] = query_id
                    except (ValueError, TypeError) as exc:
                        failed += 1
                        message = str(exc)
                        if not message.startswith(context):
                            message = f"{context}: {message}"
                        record = _metadata(graph)
                        record.update(status="error", error=message)
                        if isinstance(value, dict) and isinstance(value.get("query_id"), str):
                            record["query_id"] = value["query_id"]
                    record["query_line"] = lineno
                    output_file.write(_json(record) + "\n")
                    processed += 1
                output_file.flush()
                os.fsync(output_file.fileno())
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    summary = _metadata(graph, "batch")
    summary.update(status="complete" if failed == 0 else "completed_with_errors",
                   output=str(output), processed=processed, failed=failed)
    print(_json(summary))
    return 1 if failed else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dijkstra-toolkit",
        description="Exact integer shortest paths on directed, nonnegative-weight graphs.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate a graph and report its identity")
    validate.add_argument("graph", type=Path)
    route = commands.add_parser("route", help="find one source-to-target shortest route")
    route.add_argument("graph", type=Path)
    route.add_argument("source", type=int)
    route.add_argument("target", type=int)
    route.add_argument("--trace", action="store_true", help="include live extraction events")
    distances = commands.add_parser("distances", help="compute all distances from one source")
    distances.add_argument("graph", type=Path)
    distances.add_argument("source", type=int)
    nearest = commands.add_parser("nearest", help="compute distance from the nearest listed source")
    nearest.add_argument("graph", type=Path)
    nearest.add_argument("sources", type=int, nargs="+")
    batch = commands.add_parser("batch", help="stream NDJSON queries to a new output file")
    batch.add_argument("graph", type=Path)
    batch.add_argument("queries", type=Path)
    batch.add_argument("--output", type=Path, required=True)
    dot = commands.add_parser("dot", help="export Graphviz DOT, optionally highlighting a route")
    dot.add_argument("graph", type=Path)
    dot.add_argument("--source", type=int)
    dot.add_argument("--target", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 on success, 1 on failed batch rows, and 2 on input/usage errors."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "dot" and (args.source is None) != (args.target is None):
        parser.error("dot route highlighting requires both --source and --target")
    try:
        graph, labels = load_graph_with_labels(args.graph)
        if args.command == "validate":
            record = _metadata(graph, "validation")
            record.update(status="valid", vertex_count=graph.vertex_count, edge_count=len(graph.arcs))
            print(_json(record))
        elif args.command == "route":
            print(_json(_route(graph, args.source, args.target, args.trace)))
        elif args.command == "distances":
            print(_json(_distances(graph, [args.source])))
        elif args.command == "nearest":
            print(_json(_distances(graph, args.sources, multi=True)))
        elif args.command == "batch":
            return _batch(graph, args.graph, args.queries, args.output)
        elif args.command == "dot":
            print(render_dot(graph, labels, args.source, args.target), end="")
    except (OSError, ValueError, TypeError) as exc:
        print(f"dijkstra-toolkit: error: {exc}", file=sys.stderr)
        return 2
    return 0
