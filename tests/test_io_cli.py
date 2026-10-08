"""Input boundaries and user-facing command behavior, using isolated files."""

from __future__ import annotations

import base64
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dijkstra_toolkit.cli import _batch, _route
from dijkstra_toolkit.io import GraphFormatError, load_graph, load_graph_with_labels


ROOT = Path(__file__).resolve().parents[1]


class InputAndCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.graph_path = self.directory / "graph.json"
        self.document = {
            "schema": "dijkstra-toolkit-v1", "vertex_count": 5,
            "graph_version": "example-v1", "weight_unit": "minutes",
            "labels": ['A "quoted"', "B\\slash", "C\nline", "D", "isolated"],
            "edges": [
                {"edge_id": 5, "tail": 0, "head": 1, "weight": 8},
                {"edge_id": 7, "tail": 0, "head": 1, "weight": 2},
                {"edge_id": 8, "tail": 1, "head": 2, "weight": 3},
                {"edge_id": 2, "tail": 0, "head": 2, "weight": 9},
                {"edge_id": 9, "tail": 2, "head": 3, "weight": 0},
            ],
        }
        self.save()

    def save(self):
        self.graph_path.write_text(json.dumps(self.document), encoding="utf-8")

    def command(self, *args, expected=0):
        completed = subprocess.run([sys.executable, "-m", "dijkstra_toolkit", *map(str, args)],
                                   cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, expected, completed.stderr or completed.stdout)
        self.assertNotIn("Traceback", completed.stderr)
        return completed

    def test_load_graph_and_display_labels(self):
        graph, labels = load_graph_with_labels(self.graph_path)
        self.assertEqual(graph.vertex_count, 5)
        self.assertEqual(graph.weight_unit, "minutes")
        self.assertEqual(labels, tuple(self.document["labels"]))
        self.assertEqual(load_graph(self.graph_path).digest, graph.digest)

    def test_reject_duplicate_json_keys(self):
        self.graph_path.write_text('{"schema":"dijkstra-toolkit-v1","schema":"other"}')
        with self.assertRaisesRegex(GraphFormatError, "duplicate JSON key"):
            load_graph(self.graph_path)

    def test_reject_nonstandard_constants(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                self.graph_path.write_text('{"schema":' + value + '}')
                with self.assertRaisesRegex(GraphFormatError, "nonstandard JSON number"):
                    load_graph(self.graph_path)

    def test_reject_coerced_integer_fields(self):
        for field in ("edge_id", "tail", "head", "weight"):
            original = self.document["edges"][0][field]
            for bad in (True, 2.0, "2"):
                with self.subTest(field=field, bad=bad):
                    self.document["edges"][0][field] = bad
                    self.save()
                    with self.assertRaises(GraphFormatError):
                        load_graph(self.graph_path)
            self.document["edges"][0][field] = original

    def test_reject_negative_weight_duplicate_id_and_bounds(self):
        for field, bad in (("weight", -1), ("head", 5), ("edge_id", 7)):
            with self.subTest(field=field):
                original = self.document["edges"][0][field]
                self.document["edges"][0][field] = bad
                self.save()
                with self.assertRaises(GraphFormatError):
                    load_graph(self.graph_path)
                self.document["edges"][0][field] = original

    def test_reject_bad_labels(self):
        for labels in (None, ["A"], ["A"] * 5, [0, 1, 2, 3, 4]):
            with self.subTest(labels=labels):
                self.document["labels"] = labels
                self.save()
                with self.assertRaises(GraphFormatError):
                    load_graph(self.graph_path)

    def test_reject_wrong_schema_missing_and_unknown_fields(self):
        for document in ({"schema": "future-v99"},
                         {"schema": "dijkstra-toolkit-v1"},
                         {**self.document, "vertex_cont": 5}):
            with self.subTest(document=document):
                self.graph_path.write_text(json.dumps(document))
                with self.assertRaises(GraphFormatError):
                    load_graph(self.graph_path)

    def ndjson_metadata(self, raw=None):
        if raw is None:
            raw = ("\n".join(json.dumps(edge) for edge in self.document["edges"]) + "\n").encode()
        edge_path = self.directory / "arcs.ndjson"
        edge_path.write_bytes(raw)
        metadata = {key: value for key, value in self.document.items() if key != "edges"}
        metadata.update(schema="weighted-digraph-v1", edge_file="arcs.ndjson",
                        sha256_base64=base64.b64encode(hashlib.sha256(raw).digest()).decode())
        self.graph_path.write_text(json.dumps(metadata))
        return edge_path, metadata

    def test_verified_ndjson_matches_inline_graph(self):
        digest = load_graph(self.graph_path).digest
        self.ndjson_metadata()
        self.assertEqual(load_graph(self.graph_path).digest, digest)

    def test_checksum_covers_exact_bytes(self):
        edge_path, _ = self.ndjson_metadata()
        edge_path.write_bytes(edge_path.read_bytes() + b"\n")
        with self.assertRaisesRegex(GraphFormatError, "checksum mismatch"):
            load_graph(self.graph_path)

    def test_ndjson_reports_line_number(self):
        self.ndjson_metadata(b'\n{"edge_id":0,"tail":0,"head":1,"weight":1,"weight":2}\n')
        with self.assertRaisesRegex(GraphFormatError, "line 2.*duplicate"):
            load_graph(self.graph_path)

    def test_bad_checksum_and_absolute_edge_path(self):
        _, metadata = self.ndjson_metadata()
        for update in ({"sha256_base64": "not base64"},
                       {"sha256_base64": base64.b64encode(b"too short").decode()},
                       {"edge_file": str(self.directory / "arcs.ndjson")}):
            with self.subTest(update=update):
                self.graph_path.write_text(json.dumps({**metadata, **update}))
                with self.assertRaises(GraphFormatError):
                    load_graph(self.graph_path)

    def test_validate_command_reports_identity(self):
        result = json.loads(self.command("validate", self.graph_path).stdout)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["schema"], "dijkstra-result-v1")
        self.assertEqual(result["graph_digest"], load_graph(self.graph_path).digest)
        self.assertEqual(result["edge_count"], 5)

    def test_route_and_trace(self):
        result = json.loads(self.command("route", self.graph_path, 0, 3, "--trace").stdout)
        self.assertEqual(result["distance"], 5)
        self.assertEqual(result["edge_ids"], [7, 8, 9])
        self.assertEqual(result["vertices"], [0, 1, 2, 3])
        self.assertEqual(result["status"], "reachable")
        self.assertEqual(result["certificate_status"], "feasible_cost_verified")
        self.assertEqual([event["rank"] for event in result["trace"]], [1, 2, 3, 4])
        self.assertEqual(result["trace"][-1]["vertex"], 3)

    def test_unreachable_route_uses_null(self):
        completed = self.command("route", self.graph_path, 0, 4)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "unreachable")
        self.assertEqual(result["certificate_status"], "not_applicable")
        self.assertIsNone(result["distance"])
        self.assertIsNone(result["edge_ids"])
        self.assertNotIn("Infinity", completed.stdout)

    def test_source_to_itself(self):
        result = json.loads(self.command("route", self.graph_path, 2, 2).stdout)
        self.assertEqual(result["distance"], 0)
        self.assertEqual(result["edge_ids"], [])
        self.assertEqual(result["vertices"], [2])

    def test_route_verifier_failure_prevents_success_output(self):
        with patch("dijkstra_toolkit.cli.verify_route", return_value=False) as verifier:
            with self.assertRaisesRegex(ValueError, "feasibility and cost verification"):
                _route(load_graph(self.graph_path), 0, 3)
        verifier.assert_called_once()

    def test_full_and_multi_source_distances(self):
        result = json.loads(self.command("distances", self.graph_path, 0).stdout)
        self.assertEqual(result["distances"], [0, 2, 5, 5, None])
        self.assertTrue(result["complete"])
        nearest = json.loads(self.command("nearest", self.graph_path, 4, 0, 4).stdout)
        self.assertEqual(nearest["distances"], [0, 2, 5, 5, 0])
        self.assertEqual(nearest["sources"], [0, 4])

    def test_large_integer_distances_are_exact(self):
        huge = 10**400
        self.document["edges"] = [{"edge_id": 0, "tail": 0, "head": 1, "weight": huge}]
        self.save()
        route = json.loads(self.command("route", self.graph_path, 0, 1).stdout)
        self.assertEqual(route["distance"], huge)
        distances = json.loads(self.command("distances", self.graph_path, 0).stdout)
        self.assertEqual(distances["distances"], [0, huge, None, None, None])

    def test_argument_errors_have_no_traceback(self):
        self.command("route", self.graph_path, "0.5", 1, expected=2)
        self.command("route", self.graph_path, 0, 99, expected=2)
        self.command("validate", self.directory / "missing.json", expected=2)
        self.command("dot", self.graph_path, "--source", 0, expected=2)

    def test_dot_escapes_labels_and_highlights_route(self):
        dot = self.command("dot", self.graph_path, "--source", 0, "--target", 3).stdout
        self.assertIn('label="A \\"quoted\\""', dot)
        self.assertIn('label="B\\\\slash"', dot)
        self.assertIn('label="C\\nline"', dot)
        self.assertEqual(dot.count('penwidth="3"'), 3)

    def test_batch_records_failures_and_unreachable_success(self):
        queries = self.directory / "queries.ndjson"
        queries.write_text('\n'.join([
            '{"query_id":"route","source":0,"target":3}',
            '{"query_id":"unreachable","source":0,"target":4}',
            '{"query_id":"bad","source":true,"target":1}',
            '{"source":0,"source":1,"target":2}',
            '{malformed',
            '{"source":0,"target":0}',
        ]) + '\n')
        output = self.directory / "results.ndjson"
        summary = json.loads(self.command("batch", self.graph_path, queries,
                                          "--output", output, expected=1).stdout)
        self.assertEqual((summary["processed"], summary["failed"]), (6, 3))
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        self.assertEqual([row["status"] for row in rows],
                         ["reachable", "unreachable", "error", "error", "error", "reachable"])
        self.assertEqual(rows[2]["query_id"], "bad")
        self.assertIn("line 3", rows[2]["error"])
        self.assertEqual(rows[5]["query_line"], 6)
        self.assertEqual(list(self.directory.glob(".*.tmp")), [])

    def test_batch_refuses_overwrite_and_same_input(self):
        queries = self.directory / "queries.ndjson"
        queries.write_text('{"source":0,"target":3}\n')
        output = self.directory / "results.ndjson"
        output.write_text("preserve me")
        self.command("batch", self.graph_path, queries, "--output", output, expected=2)
        self.assertEqual(output.read_text(), "preserve me")
        self.command("batch", self.graph_path, queries, "--output", queries, expected=2)
        self.assertEqual(queries.read_text(), '{"source":0,"target":3}\n')

    def test_batch_publishes_successful_results(self):
        queries = self.directory / "queries.ndjson"
        queries.write_text('\n{"source":0,"target":3}\n\n')
        output = self.directory / "results.ndjson"
        summary = json.loads(self.command("batch", self.graph_path, queries, "--output", output).stdout)
        self.assertEqual((summary["processed"], summary["failed"]), (1, 0))
        self.assertEqual(json.loads(output.read_text())["query_line"], 2)

    def test_batch_publication_race_preserves_other_writer(self):
        queries = self.directory / "queries.ndjson"
        queries.write_text('{"source":0,"target":3}\n')
        output = self.directory / "results.ndjson"

        def competing_writer(source, destination):
            Path(destination).write_text("other writer")
            raise FileExistsError("destination appeared during processing")

        with patch("dijkstra_toolkit.cli.os.link", side_effect=competing_writer):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(FileExistsError):
                    _batch(load_graph(self.graph_path), self.graph_path, queries, output)
        self.assertEqual(output.read_text(), "other writer")
        self.assertEqual(list(self.directory.glob(".*.tmp")), [])

    def test_batch_missing_input_does_not_publish(self):
        output = self.directory / "results.ndjson"
        self.command("batch", self.graph_path, self.directory / "missing.ndjson",
                     "--output", output, expected=2)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
