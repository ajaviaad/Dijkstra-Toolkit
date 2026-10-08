"""Immutable directed multigraphs with exact, nonnegative integer weights."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
from typing import Iterable, Mapping


def require_int(value: object, name: str) -> int:
    """Return an integer without coercion; booleans are not integers here."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer (not bool)")
    return value


@dataclass(frozen=True, slots=True)
class Arc:
    """An identified directed arc; parallel arcs and self-loops are allowed."""

    edge_id: int
    tail: int
    head: int
    weight: int

    def __post_init__(self) -> None:
        for name in ("edge_id", "tail", "head", "weight"):
            require_int(getattr(self, name), name)
        if self.tail < 0 or self.head < 0:
            raise ValueError("arc endpoints must be nonnegative")
        if self.weight < 0:
            raise ValueError("arc weight must be nonnegative")


@dataclass(frozen=True, slots=True, init=False)
class Graph:
    """A validated immutable snapshot. Construct with :func:`make_graph`."""

    vertex_count: int
    outgoing: tuple[tuple[Arc, ...], ...]
    arcs: tuple[Arc, ...]
    version: str
    weight_unit: str
    digest: str
    edge_by_id: Mapping[int, Arc]

    def __init__(self) -> None:
        raise TypeError("use make_graph() to construct a Graph")


def make_graph(
    vertex_count: int,
    arcs: Iterable[Arc],
    version: str = "local",
    weight_unit: str = "cost-unit",
) -> Graph:
    """Validate and freeze a graph; its digest includes metadata and all arcs.

    Arc order in the input does not affect the snapshot. Canonical arcs are
    ordered by edge ID, and outgoing arcs by ``(head, edge_id)``.

    The SHA-256 input is ASCII JSON with sorted keys, compact separators, and
    ``ensure_ascii=True``. Its keys are ``vertex_count`` (``hex(n)``),
    ``graph_version``, ``weight_unit``, and ``edges``. Each edge is a four-item
    array of Python ``hex()`` strings in ID/tail/head/weight order. Encoding
    integers this way avoids the interpreter limit on decimal conversion and
    preserves arbitrary-size exact integers without changing global settings.
    """
    require_int(vertex_count, "vertex_count")
    if vertex_count < 0:
        raise ValueError("vertex_count must be nonnegative")
    for name, value in (("version", version), ("weight_unit", weight_unit)):
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must be nonempty")

    by_id: dict[int, Arc] = {}
    for position, arc in enumerate(arcs):
        if not isinstance(arc, Arc):
            raise TypeError(f"arcs[{position}] must be an Arc")
        # Revalidate at the snapshot boundary, including Arc subclasses.
        for name in ("edge_id", "tail", "head", "weight"):
            require_int(getattr(arc, name), f"arcs[{position}].{name}")
        if arc.weight < 0:
            raise ValueError(f"arcs[{position}].weight must be nonnegative")
        if not 0 <= arc.tail < vertex_count or not 0 <= arc.head < vertex_count:
            raise ValueError(f"arcs[{position}] has an endpoint outside the graph")
        if arc.edge_id in by_id:
            raise ValueError(f"duplicate edge_id {arc.edge_id}")
        # Copy into the exact immutable public type; caller-owned subclasses
        # cannot later change a graph through mutable overridden attributes.
        by_id[arc.edge_id] = Arc(arc.edge_id, arc.tail, arc.head, arc.weight)

    canonical = tuple(by_id[key] for key in sorted(by_id))
    adjacency: list[list[Arc]] = [[] for _ in range(vertex_count)]
    for arc in canonical:
        adjacency[arc.tail].append(arc)
    outgoing = tuple(tuple(sorted(row, key=lambda a: (a.head, a.edge_id))) for row in adjacency)
    payload = {
        "vertex_count": hex(vertex_count),
        "graph_version": version,
        "weight_unit": weight_unit,
        "edges": [[hex(a.edge_id), hex(a.tail), hex(a.head), hex(a.weight)] for a in canonical],
    }
    canonical_bytes = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")
    graph = object.__new__(Graph)
    for name, value in (
        ("vertex_count", vertex_count),
        ("outgoing", outgoing),
        ("arcs", canonical),
        ("version", version),
        ("weight_unit", weight_unit),
        ("digest", hashlib.sha256(canonical_bytes).hexdigest()),
        ("edge_by_id", MappingProxyType({a.edge_id: a for a in canonical})),
    ):
        object.__setattr__(graph, name, value)
    return graph


def _require_vertex(graph: Graph, vertex: object, name: str) -> int:
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    value = require_int(vertex, name)
    if not 0 <= value < graph.vertex_count:
        raise ValueError(f"{name} must be in [0, {graph.vertex_count})")
    return value


def reverse_graph(graph: Graph) -> Graph:
    """Reverse all arcs, retaining IDs/unit and appending ':reversed' to version."""
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    return make_graph(
        graph.vertex_count,
        (Arc(a.edge_id, a.head, a.tail, a.weight) for a in graph.arcs),
        version=f"{graph.version}:reversed",
        weight_unit=graph.weight_unit,
    )
