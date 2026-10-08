"""Independent route feasibility and full shortest-distance certificates."""

from __future__ import annotations

import math
from typing import Iterable

from .algorithms import ShortestPathResult, _validate_result_shape
from .graph import Graph, _require_vertex, require_int


def verify_route(
    graph: Graph,
    source: int,
    target: int,
    edge_ids: Iterable[int],
    claimed_cost: int,
    *,
    graph_digest: str | None = None,
) -> bool:
    """Check snapshot, continuity and exact cost, without proving optimality.

    Invalid query endpoints raise; malformed certificates return ``False``.
    Walks may revisit vertices and arcs, and an empty walk costs zero.
    """
    _require_vertex(graph, source, "source")
    _require_vertex(graph, target, "target")
    if graph_digest is not None and graph_digest != graph.digest:
        return False
    try:
        require_int(claimed_cost, "claimed_cost")
        if claimed_cost < 0:
            return False
        vertex = source
        cost = 0
        for edge_id in edge_ids:
            require_int(edge_id, "edge_id")
            arc = graph.edge_by_id.get(edge_id)
            if arc is None or arc.tail != vertex:
                return False
            cost += arc.weight
            if cost > claimed_cost:
                return False
            vertex = arc.head
        return vertex == target and cost == claimed_cost
    except (TypeError, ValueError, OverflowError):
        return False


def verify_distances(graph: Graph, result: ShortestPathResult) -> bool:
    """Verify a full result in O(V + E), independently of the search.

    Edge inequalities certify a lower bound on every route; rooted, tight
    parent witnesses attain each finite label. Reachability closure certifies
    infinity labels. Parent cycles, including zero-cost cycles, are rejected.
    """
    if not isinstance(graph, Graph):
        return False
    try:
        _validate_result_shape(graph, result)
    except (TypeError, ValueError, AttributeError):
        return False
    if not result.complete:
        return False

    n = graph.vertex_count
    sources = frozenset(result.sources)
    parent_vertex: list[int | None] = [None] * n
    for vertex in range(n):
        label = result.distance[vertex]
        if label == math.inf:
            if result.settled[vertex] or result.parent_edge[vertex] is not None:
                return False
        else:
            if not result.settled[vertex]:
                return False
            if vertex in sources:
                continue
            edge_id = result.parent_edge[vertex]
            arc = graph.edge_by_id.get(edge_id) if edge_id is not None else None
            if arc is None or arc.head != vertex:
                return False
            predecessor = result.distance[arc.tail]
            if predecessor == math.inf or predecessor + arc.weight != label:
                return False
            parent_vertex[vertex] = arc.tail

    for arc in graph.arcs:
        tail_distance = result.distance[arc.tail]
        if tail_distance != math.inf:
            head_distance = result.distance[arc.head]
            if head_distance == math.inf or head_distance > tail_distance + arc.weight:
                return False

    # Each vertex enters the trail once. Marking resolved trails prevents the
    # quadratic cost of independently following every parent chain.
    state = bytearray(n)  # 0 unseen, 1 on current trail, 2 reaches a source
    for source in sources:
        state[source] = 2
    for start in range(n):
        if result.distance[start] == math.inf or state[start] == 2:
            continue
        trail: list[int] = []
        vertex = start
        while state[vertex] == 0:
            state[vertex] = 1
            trail.append(vertex)
            predecessor = parent_vertex[vertex]
            if predecessor is None:
                return False
            vertex = predecessor
        if state[vertex] == 1:
            return False
        for vertex in trail:
            state[vertex] = 2
    return True
