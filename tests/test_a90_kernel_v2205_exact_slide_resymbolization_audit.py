"""Regression tests for a90_kernel_v2205_exact_slide_resymbolization_audit."""

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2205 = load_revalidation("a90_kernel_v2205_exact_slide_resymbolization_audit")


class SymbolAndMappingHelpers(unittest.TestCase):
    def test_signed_hex_formats_positive_zero_and_negative(self):
        self.assertEqual(v2205.signed_hex(0), "0x0")
        self.assertEqual(v2205.signed_hex(0x123), "0x123")
        self.assertEqual(v2205.signed_hex(-0x123), "-0x123")

    def test_parse_system_map_sorts_valid_symbols_and_skips_bad_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "not-hex T ignored\n"
                "0000000000003000 T schedule_tail\n"
                "0000000000001000 D null_fops\n"
                "short\n",
                encoding="utf-8",
            )

            symbols = v2205.parse_system_map(path)

        self.assertEqual(
            [(symbol.address, symbol.kind, symbol.name) for symbol in symbols],
            [(0x1000, "D", "null_fops"), (0x3000, "T", "schedule_tail")],
        )

    def test_nearest_symbol_reports_offset_and_next_delta(self):
        symbols = [
            v2205.Symbol(0x1000, "T", "alpha"),
            v2205.Symbol(0x1100, "T", "beta"),
        ]
        addresses = [symbol.address for symbol in symbols]

        self.assertIsNone(v2205.nearest_symbol(symbols, addresses, 0x0FFF))
        mapping = v2205.nearest_symbol(symbols, addresses, 0x1080)

        self.assertEqual(mapping["symbol"], "alpha")
        self.assertEqual(mapping["kind"], "T")
        self.assertEqual(mapping["symbol_address"], "0x0000000000001000")
        self.assertEqual(mapping["offset"], 0x80)
        self.assertEqual(mapping["next_delta"], 0x80)

    def test_symbolize_runtime_applies_slide_and_marks_unmapped(self):
        symbols = [v2205.Symbol(0x1000, "T", "schedule")]
        addresses = [symbol.address for symbol in symbols]

        mapped = v2205.symbolize_runtime(0xFFFF000000001020, 0xFFFF000000000000, symbols, addresses)
        unmapped = v2205.symbolize_runtime(0xFFFF000000000800, 0xFFFF000000000000, symbols, addresses)

        self.assertEqual(mapped["static"], "0x0000000000001020")
        self.assertTrue(mapped["mapped"])
        self.assertEqual(mapped["symbol"], "schedule")
        self.assertFalse(unmapped["mapped"])


class InputParsers(unittest.TestCase):
    def test_parse_stack_ips_accepts_ranked_and_plain_rows_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stack.md"
            path.write_text(
                "stack_ip rank=1 index=0 value=0xffffff8000001000\n"
                "stack_ip index=1 value=0xffffff8000002000\n"
                "stack_ip index=1 value=0xffffff8000002000\n",
                encoding="utf-8",
            )

            rows = v2205.parse_stack_ips(path)

        self.assertEqual(
            rows,
            [
                {"index": 0, "runtime": 0xFFFFFF8000001000},
                {"index": 1, "runtime": 0xFFFFFF8000002000},
            ],
        )

    def test_load_exact_slide_requires_best_slide_and_preserves_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text(
                json.dumps({"analysis": {"best_slide": -0x10, "best_sources": ["fd0:null"]}}),
                encoding="utf-8",
            )
            missing = Path(tmp) / "missing.json"
            missing.write_text(json.dumps({"analysis": {}}), encoding="utf-8")

            exact = v2205.load_exact_slide(path)
            with self.assertRaises(ValueError):
                v2205.load_exact_slide(missing)

        self.assertEqual(exact["slide"], -0x10)
        self.assertEqual(exact["slide_hex"], "-0x10")
        self.assertEqual(exact["sources"], ["fd0:null"])


class CrossRunMapping(unittest.TestCase):
    def test_map_v2195_stack_adds_schedule_hints(self):
        symbols = [
            v2205.Symbol(0x1000, "T", "schedule"),
            v2205.Symbol(0x2000, "T", "random_fn"),
        ]
        addresses = [symbol.address for symbol in symbols]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stack.md"
            path.write_text(
                "stack_ip index=0 value=0xffff000000001004\n"
                "stack_ip index=1 value=0xffff000000002004\n",
                encoding="utf-8",
            )

            rows = v2205.map_v2195_stack(path, 0xFFFF000000000000, symbols, addresses)

        self.assertEqual([row["symbol"] for row in rows], ["schedule", "random_fn"])
        self.assertEqual([row["schedule_hint"] for row in rows], [True, False])

    def test_map_v2202_rows_maps_function_stack_ips_and_timer_hints(self):
        symbols = [
            v2205.Symbol(0x1000, "T", "timer_expire_entry"),
            v2205.Symbol(0x2000, "T", "worker_fn"),
        ]
        addresses = [symbol.address for symbol in symbols]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text(
                json.dumps(
                    {
                        "histogram": {
                            "rows": [
                                {
                                    "rank": 1,
                                    "comm": "swapper",
                                    "count": 7,
                                    "timeout_min": 1,
                                    "timeout_max": 3,
                                    "timeout_avg": 2,
                                    "obj_data_delta": 16,
                                    "function": "0xffff000000001008",
                                    "stack_ips": [{"index": 2, "value": "0xffff000000002004"}],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            rows = v2205.map_v2202_rows(path, 0xFFFF000000000000, symbols, addresses)

        self.assertEqual(rows[0]["rank"], 1)
        self.assertEqual(rows[0]["mapped_function"]["symbol"], "timer_expire_entry")
        self.assertTrue(rows[0]["timer_hint"])
        self.assertEqual(rows[0]["mapped_stack_ips"][0]["symbol"], "worker_fn")
        self.assertEqual(rows[0]["mapped_stack_ips"][0]["index"], 2)

    def test_load_legacy_context_extracts_deltas_and_v2203_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            v2197 = Path(tmp) / "symbolization.json"
            v2197.write_text(
                json.dumps(
                    {
                        "top_slide_candidates": [
                            {
                                "slide": 0x1000,
                                "slide_hex": "0x1000",
                                "source": "stack",
                                "stack_score": 3,
                                "stack_total": 6,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            v2203 = Path(tmp) / "result.json"
            v2203.write_text(
                json.dumps(
                    {
                        "decision": "v2203-done",
                        "reason": "ranked",
                        "top_candidates": [{"symbol": "timer_fn"}],
                    }
                ),
                encoding="utf-8",
            )

            context = v2205.load_legacy_context(v2197, v2203, 0x1800)
            empty = v2205.load_legacy_context(Path(tmp) / "absent-a", Path(tmp) / "absent-b", 0)

        self.assertEqual(context["exact_minus_v2197_top"], 0x800)
        self.assertEqual(context["exact_minus_v2197_top_hex"], "0x800")
        self.assertEqual(context["v2203_decision"], "v2203-done")
        self.assertEqual(context["v2203_top_candidate"], {"symbol": "timer_fn"})
        self.assertEqual(empty, {})


class ClassificationAndReport(unittest.TestCase):
    def test_classify_result_separates_implausible_from_review_needed(self):
        blocked = v2205.classify_result(
            [{"schedule_hint": False}],
            [{"mapped_function": {"symbol": "random_fn"}, "timer_hint": False}],
        )
        review = v2205.classify_result(
            [{"schedule_hint": True}],
            [{"mapped_function": {"symbol": "timer_tick"}, "timer_hint": True}],
        )

        self.assertEqual(blocked[0], "v2205-fops-slide-not-universal-text-slide")
        self.assertIn("semantically implausible", blocked[1])
        self.assertEqual(review[0], "v2205-fops-slide-text-audit-needs-review")
        self.assertIn("schedule-like", review[1])

    def test_render_markdown_includes_decision_tables_next_steps_and_evidence(self):
        report = v2205.render_markdown(
            {
                "decision": "v2205-fops-slide-not-universal-text-slide",
                "reason": "not universal",
                "v2204_exact_slide": {"slide_hex": "0x1000", "sources": ["fd0", "fd1"]},
                "v2195_stack_exact_slide": [
                    {
                        "index": 0,
                        "runtime": "0xffff000000001000",
                        "static": "0x0000000000000000",
                        "symbol": "random",
                        "offset": 4,
                        "schedule_hint": False,
                    }
                ],
                "v2202_timer_rows_exact_slide": [
                    {
                        "rank": 1,
                        "comm": "swapper",
                        "count": 5,
                        "runtime_function": "0xffff000000002000",
                        "mapped_function": {"symbol": "random_timer", "offset": 8},
                        "timer_hint": True,
                    }
                ],
                "legacy_context": {
                    "exact_minus_v2197_top_hex": "0x800",
                    "v2203_decision": "v2203-done",
                    "v2203_reason": "done",
                },
                "inputs": {"system_map": "System.map"},
            }
        )

        self.assertIn("# Native Init V2205 Exact-Slide Resymbolization Audit", report)
        self.assertIn("- Decision: `v2205-fops-slide-not-universal-text-slide`", report)
        self.assertIn("| 0 | `0xffff000000001000` | `0x0000000000000000` | `random` | `4` | `false` |", report)
        self.assertIn("| 1 | `swapper` | 5 | `0xffff000000002000` | `random_timer` | `8` | `true` |", report)
        self.assertIn("- system_map: `System.map`", report)


if __name__ == "__main__":
    unittest.main()
