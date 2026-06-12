"""Regression tests for a90_kernel_v2203_timer_row_source_matcher."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from _loader import load_revalidation

matcher = load_revalidation("a90_kernel_v2203_timer_row_source_matcher")


def write_timer_source(root: Path) -> Path:
    path = root / "drivers" / "timer_demo.c"
    path.parent.mkdir(parents=True)
    path.write_text(
        "\n".join(
            [
                "static void timer_cb(unsigned long data) {}",
                "static void ignored_cb(unsigned long data) {}",
                "void init_timer_demo(struct demo *dev) {",
                "  setup_timer(&dev->timer, timer_cb, 0);",
                "  setup_timer(&dev->ignored, ignored_cb, 0);",
                "  mod_timer(&dev->timer, jiffies + 1);",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


class ScalarAndSignatureHelpers(unittest.TestCase):
    def test_parse_int_accepts_int_decimal_and_hex_strings(self):
        self.assertEqual(matcher.parse_int(7), 7)
        self.assertEqual(matcher.parse_int("17"), 17)
        self.assertEqual(matcher.parse_int("0x11"), 17)
        self.assertEqual(matcher.parse_int("0X11"), 17)

    def test_row_signature_extracts_stability_and_shape_flags(self):
        row = {
            "comm": "rcu_preempt",
            "count": 5,
            "timeout_min": 1,
            "timeout_max": 100,
            "timeout_avg": 10000,
            "obj_data_delta": -128,
            "obj_expires_match": 5,
            "obj_function_match": 5,
        }

        signature = matcher.row_signature(row)

        self.assertEqual(signature["comm"], "rcu_preempt")
        self.assertEqual(signature["count"], 5)
        self.assertEqual(
            signature["signature"],
            [
                "rcu_comm",
                "has_jiffies_1",
                "long_timeout",
                "embedded_timer_data_delta",
                "expires_stable",
                "function_stable",
            ],
        )


class SourceXrefExtraction(unittest.TestCase):
    def test_fast_extract_timer_xrefs_filters_targets_and_attaches_arm_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_path = write_timer_source(root)

            xrefs = matcher.fast_extract_timer_xrefs([root], {"timer_cb", "missing_cb"})

            self.assertEqual(set(xrefs), {"timer_cb"})
            xref = xrefs["timer_cb"]
            self.assertEqual(len(xref.timer_uses), 1)
            self.assertEqual(xref.timer_uses[0].api, "setup_timer")
            self.assertEqual(xref.timer_uses[0].timer_expr, "dev->timer")
            self.assertEqual(xref.timer_uses[0].timer_leaf, "timer")
            self.assertEqual(xref.timer_uses[0].path, str(source_path))
            self.assertEqual(len(xref.arm_refs), 1)
            self.assertEqual(xref.arm_refs[0].api, "mod_timer")
            self.assertEqual(xref.arm_refs[0].timer_leaf, "timer")
            self.assertEqual(xref.arm_refs[0].interval_class, "jiffies_plus_1")


class RowMappingScoring(unittest.TestCase):
    def test_score_row_mapping_rewards_matching_rcu_jiffies_and_embedded_timer(self):
        row = {
            "comm": "rcu_preempt",
            "count": 5,
            "timeout_min": 1,
            "timeout_max": 1,
            "timeout_avg": 1,
            "obj_data_delta": -64,
            "obj_expires_match": 5,
            "obj_function_match": 5,
            "obj_read_errors": 0,
        }
        symbol = {"symbol": "rcu_nocb_timer", "offset": 0}
        xref_score = {
            "score": 80,
            "timer_leaves": ["nocb_timer"],
            "best_interval_class": "jiffies_plus_1",
            "notes": ["struct-field timer object"],
            "api_kinds": ["setup_timer"],
        }

        score, notes = matcher.score_row_mapping(row, symbol, xref_score)

        self.assertGreater(score, 300)
        self.assertIn("entry offset", notes)
        self.assertIn("rcu row matches rcu/nocb source pattern", notes)
        self.assertIn("jiffies+1 cadence match", notes)
        self.assertIn("embedded data delta matches struct-field timer", notes)

    def test_score_row_mapping_penalizes_missing_symbol_and_conflicting_rows(self):
        missing_score, missing_notes = matcher.score_row_mapping({}, None, {})
        self.assertEqual(missing_score, -200)
        self.assertEqual(missing_notes, ["no symbol mapping"])

        row = {
            "comm": "rcu_preempt",
            "count": 3,
            "timeout_min": 100,
            "timeout_max": 200,
            "timeout_avg": 20000,
            "obj_data_delta": 0,
            "obj_expires_match": 3,
            "obj_function_match": 3,
            "obj_read_errors": 0,
        }
        score, notes = matcher.score_row_mapping(
            row,
            {"symbol": "generic_timer", "offset": 0},
            {"score": 50, "best_interval_class": "jiffies_plus_1", "timer_leaves": [], "notes": []},
        )

        self.assertLess(score, 0)
        self.assertIn("rcu row maps to non-rcu source pattern", notes)
        self.assertIn("long-timeout row conflicts with jiffies+1 source", notes)


class SourceRootsAndRendering(unittest.TestCase):
    def test_candidate_source_roots_prefers_explicit_and_resolves_relative_inputs(self):
        explicit = [Path("/explicit/source")]
        self.assertEqual(matcher.candidate_source_roots({"inputs": {"source_roots": ["ignored"]}}, explicit), explicit)

        roots = matcher.candidate_source_roots(
            {"inputs": {"source_roots": ["relative/source", "/absolute/source"]}},
            [],
        )

        self.assertEqual(roots[0], matcher.REPO_ROOT / "relative/source")
        self.assertEqual(roots[1], Path("/absolute/source"))

    def test_render_markdown_includes_candidate_and_row_notes(self):
        text = matcher.render_markdown(
            {
                "decision": "v2203-row-matcher-provisional-lead",
                "reason": "source-backed",
                "row_count": 1,
                "source_files_scanned": 2,
                "xref_count": 1,
                "interpretation": "ranking only",
                "top_candidates": [
                    {
                        "slide_hex": "0x0",
                        "weighted_score": 42,
                        "hard_conflicts": 0,
                        "top_row_score": 42,
                        "rcu_row_score": None,
                        "rows": [
                            {
                                "rank": 0,
                                "runtime_function": "0x1000",
                                "comm": "worker",
                                "count": 5,
                                "symbol": "timer_cb",
                                "symbol_offset": 0,
                                "row_score": 42,
                                "notes": ["entry offset", "source xref score 7"],
                            }
                        ],
                    }
                ],
            }
        )

        self.assertIn("- Decision: `v2203-row-matcher-provisional-lead`", text)
        self.assertIn("- slide `0x0`: weighted=42", text)
        self.assertIn("row0 `0x1000` comm=worker count=5 -> `timer_cb`+0", text)
        self.assertIn("ranking only", text)


class AnalyzeMinimalFixture(unittest.TestCase):
    def test_analyze_ranks_single_source_backed_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "src"
            write_timer_source(source_root)
            v2198_json = root / "v2198.json"
            v2202_summary = root / "v2202.json"
            system_map = root / "System.map"
            v2198_json.write_text(
                json.dumps({"top_timer_candidates": [{"slide": 0, "slide_hex": "0x0"}]}),
                encoding="utf-8",
            )
            v2202_summary.write_text(
                json.dumps(
                    {
                        "histogram": {
                            "rows": [
                                {
                                    "rank": 0,
                                    "function": "0x1000",
                                    "count": 5,
                                    "comm": "worker",
                                    "timeout_min": 1,
                                    "timeout_max": 1,
                                    "timeout_avg": 1,
                                    "obj_data_delta": -64,
                                    "obj_expires_match": 5,
                                    "obj_function_match": 5,
                                    "obj_read_errors": 0,
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            system_map.write_text(
                "0000000000001000 T timer_cb\n"
                "0000000000001100 T next_symbol\n",
                encoding="utf-8",
            )
            args = SimpleNamespace(
                v2198_json=v2198_json,
                v2202_summary=v2202_summary,
                system_map=system_map,
                source_root=[source_root],
                row_limit=8,
                count_cap=200,
                top_candidates=4,
            )

            result = matcher.analyze(args)

            self.assertEqual(result["decision"], "v2203-row-matcher-provisional-lead")
            self.assertEqual(result["row_count"], 1)
            self.assertEqual(result["xref_count"], 1)
            top = result["top_candidates"][0]
            self.assertEqual(top["slide_hex"], "0x0")
            self.assertEqual(top["hard_conflicts"], 0)
            self.assertGreater(top["weighted_score"], 0)
            self.assertEqual(top["rows"][0]["symbol"], "timer_cb")
            self.assertEqual(top["rows"][0]["symbol_offset"], 0)


if __name__ == "__main__":
    unittest.main()
