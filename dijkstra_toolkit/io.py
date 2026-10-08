"""Strict graph readers for portable JSON and checksummed NDJSON files."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from pathlib import Path
from typing import Any

from .graph import Arc, Graph, make_graph


class GraphFormatError(ValueError):
    """A graph file does not satisfy its declared input schema."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _bad_constant(value: str) -> None:
    raise ValueError(f"nonstandard JSON number {value!r} is not allowed")


def parse_json(text: str | bytes, context: str = "JSON input") -> Any:
    """Parse standard JSON, rejecting duplicate keys, NaN, and Infinity."""
    try:
        return json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=_bad_constant)
    except (ValueError, UnicodeError) as exc:
        raise GraphFormatError(f"{context}: {exc}") from exc


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GraphFormatError(f"{context}: expected a JSON object")
    return value


def _fields(obj: dict[str, Any], required: set[str], optional: set[str],
            context: str) -> None:
    missing = sorted(required - obj.keys())
    unknown = sorted(obj.keys() - required - optional)
    if missing:
        raise GraphFormatError(f"{context}: missing field(s): {', '.join(missing)}")
    if unknown:
        raise GraphFormatError(f"{context}: unknown field(s): {', '.join(unknown)}")


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise GraphFormatError(f"{path}: {exc.strerror or exc}") from exc


def _arc(value: Any, context: str) -> Arc:
    obj = _object(value, context)
    _fields(obj, {"edge_id", "tail", "head", "weight"}, set(), context)
    try:
        return Arc(obj["edge_id"], obj["tail"], obj["head"], obj["weight"])
    except (ValueError, TypeError) as exc:
        raise GraphFormatError(f"{context}: {exc}") from exc


def load_graph_with_labels(path: str | Path) -> tuple[Graph, tuple[str, ...] | None]:
    """Read a graph and optional display labels; vertex IDs always remain integers.

    The NDJSON variant hashes and parses the same byte buffer, so a file change
    between separate reads cannot bypass checksum verification.
    """
    graph_path = Path(path)
    context = str(graph_path)
    obj = _object(parse_json(_read(graph_path), context), context)
    schema = obj.get("schema")
    common = {"schema", "vertex_count", "graph_version", "weight_unit"}
    if schema == "dijkstra-toolkit-v1":
        _fields(obj, common | {"edges"}, {"labels"}, context)
        if not isinstance(obj["edges"], list):
            raise GraphFormatError(f"{context}: edges must be an array")
        arcs = [_arc(value, f"{context}: edges[{index}]")
                for index, value in enumerate(obj["edges"])]
    elif schema == "weighted-digraph-v1":
        _fields(obj, common | {"edge_file", "sha256_base64"}, {"labels"}, context)
        filename = obj["edge_file"]
        if not isinstance(filename, str) or not filename.strip():
            raise GraphFormatError(f"{context}: edge_file must be a nonempty relative path")
        if Path(filename).is_absolute():
            raise GraphFormatError(f"{context}: edge_file must be a relative path")
        expected = obj["sha256_base64"]
        try:
            if not isinstance(expected, str):
                raise ValueError("expected a string")
            decoded = base64.b64decode(expected, validate=True)
            if len(decoded) != 32 or base64.b64encode(decoded).decode("ascii") != expected:
                raise ValueError("expected a canonical base64-encoded SHA-256 digest")
        except (ValueError, binascii.Error) as exc:
            raise GraphFormatError(f"{context}: invalid sha256_base64: {exc}") from exc
        edge_path = graph_path.parent / filename
        raw = _read(edge_path)
        if hashlib.sha256(raw).digest() != decoded:
            raise GraphFormatError(f"{edge_path}: SHA-256 checksum mismatch")
        arcs = []
        for lineno, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            line_context = f"{edge_path}: line {lineno}"
            arcs.append(_arc(parse_json(line, line_context), line_context))
    else:
        raise GraphFormatError(f"{context}: unsupported schema {schema!r}")
    try:
        graph = make_graph(obj["vertex_count"], arcs,
                           version=obj["graph_version"], weight_unit=obj["weight_unit"])
    except (ValueError, TypeError) as exc:
        raise GraphFormatError(f"{context}: {exc}") from exc
    labels = obj.get("labels")
    if "labels" in obj:
        if (not isinstance(labels, list) or len(labels) != graph.vertex_count
                or any(not isinstance(label, str) for label in labels)):
            raise GraphFormatError(f"{context}: labels must contain one string per vertex")
        if len(set(labels)) != len(labels):
            raise GraphFormatError(f"{context}: labels must be unique")
    return graph, tuple(labels) if labels is not None else None


def load_graph(path: str | Path) -> Graph:
    """Read and validate either supported graph schema, returning an immutable graph."""
    return load_graph_with_labels(path)[0]
