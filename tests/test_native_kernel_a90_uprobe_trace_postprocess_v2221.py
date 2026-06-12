"""Regression tests for native_kernel_a90_uprobe_trace_postprocess_v2221.

Pins the small pure JSON helpers used to bridge V2219 collector output into the
V2220 parser without running the collector, parser, bridge, or device.
"""

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

postprocess = load_revalidation("native_kernel_a90_uprobe_trace_postprocess_v2221")


class ParseStdoutJson(unittest.TestCase):
    def test_empty_stdout_returns_empty_dict(self):
        self.assertEqual(postprocess.parse_stdout_json(""), {})
        self.assertEqual(postprocess.parse_stdout_json("  \n\t"), {})

    def test_parses_clean_json_object(self):
        self.assertEqual(
            postprocess.parse_stdout_json('{"pass": true, "count": 3}'),
            {"pass": True, "count": 3},
        )

    def test_extracts_json_object_from_noisy_stdout(self):
        stdout = (
            "collector starting\n"
            "debug: bridge ready\n"
            '{"decision": "ok", "nested": {"hits": [1, 2]}}\n'
            "collector done\n"
        )

        self.assertEqual(
            postprocess.parse_stdout_json(stdout),
            {"decision": "ok", "nested": {"hits": [1, 2]}},
        )

    def test_raises_json_decode_error_when_no_json_object_exists(self):
        with self.assertRaises(postprocess.json.JSONDecodeError):
            postprocess.parse_stdout_json("collector produced no structured output")

    def test_raises_json_decode_error_for_malformed_embedded_json(self):
        with self.assertRaises(postprocess.json.JSONDecodeError):
            postprocess.parse_stdout_json("prefix {not-json: true} suffix")


class LoadJson(unittest.TestCase):
    def test_load_json_reads_object_from_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text('{"decision": "done", "pass": false}\n')

            self.assertEqual(
                postprocess.load_json(path),
                {"decision": "done", "pass": False},
            )

    def test_load_json_propagates_decode_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("not-json")

            with self.assertRaises(postprocess.json.JSONDecodeError):
                postprocess.load_json(path)

    def test_load_json_propagates_missing_file_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.json"

            with self.assertRaises(FileNotFoundError):
                postprocess.load_json(path)


if __name__ == "__main__":
    unittest.main()
