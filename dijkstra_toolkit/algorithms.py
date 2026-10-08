"""Deterministic lazy-heap Dijkstra with explicit finality and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
from typing import Callable, Iterable

from .graph import Arc, Graph, _require_vertex


@dataclass(frozen=True, slots=True)
class Diagnostics:
    """Counters for heap extraction, edge scans, and strict improvements."""

    live_pops: int
    stale_pops: int
    scanned_edges: int
    improvements: int
    peak_queue: int


@dataclass(frozen=True, slots=True)
class SettledEvent:
    """A final vertex label, emitted after popping and before scanning arcs."""

    vertex: int
    distance: int
    rank: int
    queue_size: int


@dataclass(frozen=True, slots=True)
class ShortestPathResult:
    """Frozen labels and witnesses bound to a particular graph snapshot.

    Unreachable labels are ``math.inf``. In a partial target search, labels for
    other vertices can be tentative; use :func:`recover` for safe route access.
    """

    sources: tuple[int, ...]
    target: int | None
    distance: tuple[int | float, ...]
    parent_edge: tuple[int | None, ...]
    settled: tuple[bool, ...]
    complete: bool
    graph_version: str
    graph_digest: str
    diagnostics: Diagnostics


Observer = Callable[[SettledEvent], None]


def dijkstra(
    graph: Graph,
    source: int,
    target: int | None = None,
    *,
    observer: Observer | None = None,
) -> ShortestPathResult:
    """Find shortest paths, optionally stopping when the target is settled.

    Equal distances are resolved by vertex index, with outgoing arcs visited in
    canonical order. Parent witnesses change only on strict improvement.
    """
    _require_vertex(graph, source, "source")
    if target is not None:
        _require_vertex(graph, target, "target")
    return _run(graph, (source,), target, observer)


def multi_source_dijkstra(
    graph: Graph, sources: Iterable[int], *, observer: Observer | None = None
) -> ShortestPathResult:
    """Return full distances to the nearest of the unique supplied sources."""
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    roots = tuple(sorted({_require_vertex(graph, s, "source") for s in sources}))
    if not roots:
        raise ValueError("sources must be nonempty")
    return _run(graph, roots, None, observer)


def _run(
    graph: Graph, sources: tuple[int, ...], target: int | None, observer: Observer | None
) -> ShortestPathResult:
    if observer is not None and not callable(observer):
        raise TypeError("observer must be callable or None")
    n = graph.vertex_count
    distance: list[int | float] = [math.inf] * n
    parent: list[int | None] = [None] * n
    settled = [False] * n
    queue: list[tuple[int, int]] = []
    for source in sources:
        distance[source] = 0
        queue.append((0, source))
    heapq.heapify(queue)
    roots = frozenset(sources)
    live_pops = stale_pops = scanned_edges = improvements = 0
    peak_queue = len(queue)
    complete = True
    while queue:
        cost, vertex = heapq.heappop(queue)
        if settled[vertex] or cost != distance[vertex]:
            stale_pops += 1
            continue
        settled[vertex] = True
        live_pops += 1
        if observer is not None:
            observer(SettledEvent(vertex, cost, live_pops, len(queue)))
        if vertex == target:
            # With one vertex there are no other labels left to establish.
            complete = n == 1
            break
        for arc in graph.outgoing[vertex]:
            scanned_edges += 1
            candidate = cost + arc.weight
            if arc.head not in roots and candidate < distance[arc.head]:
                distance[arc.head] = candidate
                parent[arc.head] = arc.edge_id
                heapq.heappush(queue, (candidate, arc.head))
                improvements += 1
                peak_queue = max(peak_queue, len(queue))
    return ShortestPathResult(
        sources=sources,
        target=target,
        distance=tuple(distance),
        parent_edge=tuple(parent),
        settled=tuple(settled),
        complete=complete,
        graph_version=graph.version,
        graph_digest=graph.digest,
        diagnostics=Diagnostics(live_pops, stale_pops, scanned_edges, improvements, peak_queue),
    )


def _is_distance(value: object) -> bool:
    return (isinstance(value, int) and not isinstance(value, bool) and value >= 0) or (
        isinstance(value, float) and value == math.inf
    )


def _validate_result_shape(graph: Graph, result: ShortestPathResult) -> None:
    """Shared structural checks; no claim of shortest-path optimality."""
    if not isinstance(result, ShortestPathResult):
        raise TypeError("result must be a ShortestPathResult")
    if result.graph_version != graph.version or result.graph_digest != graph.digest:
        raise ValueError("result belongs to a different graph snapshot")
    if type(result.complete) is not bool:
        raise ValueError("result.complete must be a boolean")
    if not isinstance(result.sources, tuple) or not result.sources:
        raise ValueError("result.sources must be a nonempty tuple")
    for source in result.sources:
        _require_vertex(graph, source, "result source")
    if any(left >= right for left, right in zip(result.sources, result.sources[1:])):
        raise ValueError("result sources must be unique and sorted")
    if result.target is not None:
        _require_vertex(graph, result.target, "result target")
    n = graph.vertex_count
    for name in ("distance", "parent_edge", "settled"):
        values = getattr(result, name)
        if not isinstance(values, tuple) or len(values) != n:
            raise ValueError(f"result.{name} must be a tuple of length vertex_count")
    if any(not _is_distance(value) for value in result.distance):
        raise ValueError("result contains an invalid distance")
    if any(type(value) is not bool for value in result.settled):
        raise ValueError("result contains a non-boolean settled flag")
    if any(value is not None and (isinstance(value, bool) or not isinstance(value, int)) for value in result.parent_edge):
        raise ValueError("result contains an invalid parent edge ID")
    for vertex, label in enumerate(result.distance):
        if label == math.inf:
            if result.settled[vertex] or result.parent_edge[vertex] is not None:
                raise ValueError("unreachable labels must be unsettled and have no parent")
        elif result.complete and not result.settled[vertex]:
            raise ValueError("complete results must settle every finite label")
    for source in result.sources:
        if result.distance[source] != 0 or result.parent_edge[source] is not None:
            raise ValueError("result source must have distance zero and no parent")
        if not result.settled[source]:
            raise ValueError("result sources must be settled")


def recover(result: ShortestPathResult, graph: Graph, target: int) -> tuple[Arc, ...] | None:
    """Recover a final route, rejecting stale snapshots or malformed witnesses.

    Return ``None`` for an unreachable target, or an empty tuple for a source.
    Partial results may only be recovered for their requested, settled target.
    This checks the route witness; use ``verify_distances`` for optimality.
    """
    _require_vertex(graph, target, "target")
    _validate_result_shape(graph, result)
    if not result.complete and (target != result.target or not result.settled[target]):
        raise ValueError("partial result can only recover its settled requested target")
    if result.distance[target] == math.inf:
        if not result.complete or result.settled[target] or result.parent_edge[target] is not None:
            raise ValueError("inconsistent unreachable target")
        return None
    if not result.settled[target]:
        raise ValueError("target distance has not been finalized")

    sources = frozenset(result.sources)
    route: list[Arc] = []
    visited: set[int] = set()
    vertex = target
    total = 0
    while vertex not in sources:
        if vertex in visited:
            raise ValueError("parent witnesses contain a cycle")
        visited.add(vertex)
        if not result.settled[vertex]:
            raise ValueError("parent witness passes through an unsettled vertex")
        edge_id = result.parent_edge[vertex]
        arc = graph.edge_by_id.get(edge_id) if edge_id is not None else None
        if arc is None or arc.head != vertex:
            raise ValueError("missing or incorrectly oriented parent edge")
        if result.distance[arc.tail] == math.inf or result.distance[arc.tail] + arc.weight != result.distance[vertex]:
            raise ValueError("parent edge does not witness the claimed distance")
        route.append(arc)
        total += arc.weight
        vertex = arc.tail
    if not result.settled[vertex]:
        raise ValueError("route source has not been finalized")
    if total != result.distance[target]:
        raise ValueError("route cost differs from the target label")
    route.reverse()
    return tuple(route)
