"""Measure verified full-source searches on a reproducible synthetic multigraph."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import tracemalloc

from dijkstra_toolkit import Arc, __version__, dijkstra, make_graph, verify_distances


def generate(vertices: int, edges: int, seed: int) -> list[Arc]:
    """A directed chain plus random arcs; zero weights and parallel arcs allowed."""
    rng = random.Random(seed)
    arcs = [Arc(i, i, i + 1, rng.randrange(21)) for i in range(vertices - 1)]
    while len(arcs) < edges:
        arcs.append(Arc(len(arcs), rng.randrange(vertices), rng.randrange(vertices),
                        rng.randrange(21)))
    return arcs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vertices", type=int, default=1000)
    parser.add_argument("--edges", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True,
                        help="new output directory; existing paths are refused")
    args = parser.parse_args()
    if args.vertices < 1 or args.edges < args.vertices - 1 or args.repeats < 1:
        parser.error("vertices and repeats must be positive; edges must be at least vertices - 1")
    if args.output.exists() or args.output.is_symlink():
        parser.error("output directory already exists; choose a new path")

    started = time.perf_counter_ns()
    arcs = generate(args.vertices, args.edges, args.seed)
    graph = make_graph(args.vertices, arcs, version=f"synthetic-chain-random-v1-seed-{args.seed}")
    build_ns = time.perf_counter_ns() - started
    warmup = dijkstra(graph, 0)
    if not verify_distances(graph, warmup):
        raise RuntimeError("warmup result failed independent optimality verification")
    observations = []
    for repetition in range(args.repeats):
        # Release the preceding result before starting the next timed run.
        started = time.perf_counter_ns()
        result = dijkstra(graph, 0)
        elapsed_ns = time.perf_counter_ns() - started
        if not verify_distances(graph, result):
            raise RuntimeError("timed result failed independent optimality verification")
        observations.append({"repetition": repetition, "elapsed_ns": elapsed_ns,
                             "diagnostics": asdict(result.diagnostics)})
        del result
    # A separate, untimed pass measures Python allocations for the query only.
    tracemalloc.start()
    memory_result = dijkstra(graph, 0)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    if not verify_distances(graph, memory_result):
        raise RuntimeError("memory-pass result failed verification")
    times = sorted(row["elapsed_ns"] for row in observations)
    summary = {
        "schema": "dijkstra-benchmark-v1", "status": "complete",
        "graph_digest": graph.digest, "implementation_version": __version__,
        "generator": "directed-chain-plus-random-arcs-v1",
        "vertices": args.vertices, "edges": args.edges, "seed": args.seed,
        "query": {"source": 0, "mode": "full-source"}, "repeats": args.repeats,
        "warmup_runs": 1, "build_ns": build_ns,
        "median_ns": statistics.median(times),
        "p95_ns": times[math.ceil(.95 * len(times)) - 1],
        "p95_definition": "nearest-rank", "query_python_peak_bytes": peak,
        "memory_definition": "separate tracemalloc run; excludes graph and process RSS",
        "verification": "independent full-result certificate after every run; outside timer",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": sys.version, "platform": platform.platform(),
                        "machine": platform.machine()},
    }
    graph_data = {"schema": "dijkstra-toolkit-v1", "vertex_count": graph.vertex_count,
                  "graph_version": graph.version, "weight_unit": graph.weight_unit,
                  "edges": [asdict(edge) for edge in graph.arcs]}
    # Output is claimed complete only after manifest.json is successfully written.
    args.output.mkdir(parents=True, exist_ok=False)
    files = {
        "graph.json": json.dumps(graph_data, indent=2) + "\n",
        "observations.ndjson": "".join(json.dumps(row) + "\n" for row in observations),
        "summary.json": json.dumps(summary, indent=2) + "\n",
    }
    for name, content in files.items():
        (args.output / name).write_text(content, encoding="utf-8")
    manifest = {"status": "complete", "sha256": {
        name: hashlib.sha256((args.output / name).read_bytes()).hexdigest() for name in files}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
