"""Regression tests for a90_kernel_stack_symbolize.

Pins deterministic System.map parsing, log parsing, slide candidate generation,
and stack/timer slide scoring helpers with synthetic data only.
"""

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

symbolize = load_revalidation("a90_kernel_stack_symbolize")


TEXT_BASE = 0xFFFFFF8008000000


class ParsingHelpers(unittest.TestCase):
    def test_parse_int_accepts_decimal_and_hex(self):
        self.assertEqual(symbolize.parse_int("123"), 123)
        self.assertEqual(symbolize.parse_int(" 0x10 "), 16)

    def test_parse_system_map_filters_to_kernel_text_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "nothex T ignored\n"
                "0000000000001000 T low_address\n"
                f"{TEXT_BASE:016x} T _text\n"
                f"{TEXT_BASE + 0x10:016x} W weak_func\n"
                f"{TEXT_BASE + 0x20:016x} D data_symbol\n"
                f"{TEXT_BASE + 0x30:016x} t local_func\n"
            )

            symbols = symbolize.parse_system_map(path)

            self.assertEqual(
                symbols,
                [
                    symbolize.Symbol(TEXT_BASE, "T", "_text"),
                    symbolize.Symbol(TEXT_BASE + 0x10, "W", "weak_func"),
                    symbolize.Symbol(TEXT_BASE + 0x30, "t", "local_func"),
                ],
            )

    def test_parse_stack_and_timer_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stack_log = root / "stack.log"
            stack_log.write_text(
                "noise\n"
                "stack_ip index=0 value=0xffffff8008001010\n"
                "stack_ip index=1 value=0xffffff8008002020\n"
            )
            timer_log = root / "timer.log"
            timer_log.write_text(
                "value=18446744073709551617 count=2\n"
                "value=1 count=3\n"
                "value=2 count=7\n"
            )

            self.assertEqual(
                symbolize.parse_stack_log(stack_log),
                [0xffffff8008001010, 0xffffff8008002020],
            )
            self.assertEqual(
                symbolize.parse_timer_log(timer_log),
                [
                    {"address": 1, "count": 2},
                    {"address": 1, "count": 3},
                    {"address": 2, "count": 7},
                ],
            )


class SymbolAndSlideHelpers(unittest.TestCase):
    def test_nearest_symbol_reports_offsets_extent_and_next_delta(self):
        symbols = [
            symbolize.Symbol(TEXT_BASE, "T", "_text"),
            symbolize.Symbol(TEXT_BASE + 0x100, "T", "schedule"),
        ]
        addresses = [symbol.address for symbol in symbols]

        self.assertIsNone(symbolize.nearest_symbol(symbols, addresses, TEXT_BASE - 1))
        hit = symbolize.nearest_symbol(symbols, addresses, TEXT_BASE + 0x20)
        self.assertEqual(hit["symbol"], "_text")
        self.assertEqual(hit["offset"], 0x20)
        self.assertEqual(hit["next_delta"], 0xE0)
        self.assertTrue(hit["inside_known_extent"])

    def test_build_symbol_index_keeps_first_duplicate(self):
        symbols = [
            symbolize.Symbol(TEXT_BASE, "T", "dup"),
            symbolize.Symbol(TEXT_BASE + 0x10, "T", "dup"),
        ]
        self.assertEqual(symbolize.build_symbol_index(symbols)["dup"], TEXT_BASE)

    def test_candidate_slides_deduplicates_and_obeys_bounds(self):
        symbol_index = {
            "__schedule": TEXT_BASE + 0x1000,
            "schedule": TEXT_BASE + 0x2000,
        }
        stack_ips = [
            TEXT_BASE + 0x1000 + 0x1234,
            TEXT_BASE + 0x2000 + 0x1234,
            TEXT_BASE + 0x1000 + 0x9000000,
        ]

        candidates = symbolize.candidate_slides(stack_ips, symbol_index, ["__schedule", "schedule"])
        slides = sorted(candidate["slide"] for candidate in candidates)

        self.assertEqual(slides, [0x234, 0x1234, 0x2234])
        source_symbols = {candidate["slide"]: candidate["source_symbol"] for candidate in candidates}
        self.assertEqual(source_symbols[0x1234], "__schedule")


class ScoreSlide(unittest.TestCase):
    def test_score_slide_combines_stack_mapping_and_timer_anchor_scores(self):
        slide = 0x1000
        symbols = [
            symbolize.Symbol(TEXT_BASE, "T", "_text"),
            symbolize.Symbol(TEXT_BASE + 0x100, "T", "schedule"),
            symbolize.Symbol(TEXT_BASE + 0x200, "T", "timer_callback"),
            symbolize.Symbol(TEXT_BASE + 0x5000, "T", "far_func"),
        ]
        addresses = [symbol.address for symbol in symbols]
        stack_ips = [
            TEXT_BASE + 0x100 + slide,
            TEXT_BASE + 0x120 + slide,
            TEXT_BASE - 0x10 + slide,
        ]
        timer_functions = [
            {"address": TEXT_BASE + 0x200 + slide, "count": 7},
            {"address": TEXT_BASE + 0x250 + slide, "count": 3},
            {"address": TEXT_BASE - 0x20 + slide, "count": 11},
        ]

        result = symbolize.score_slide(
            symbols,
            addresses,
            slide,
            stack_ips,
            timer_functions,
            source={"source_symbol": "schedule"},
        )

        self.assertEqual(result["slide"], slide)
        self.assertEqual(result["slide_hex"], "0x1000")
        self.assertEqual(result["source"], {"source_symbol": "schedule"})
        self.assertEqual(result["stack_score"], 2)
        self.assertEqual(result["stack_total"], 3)
        self.assertEqual(result["timer_weight_total"], 21)
        self.assertEqual(result["timer_weighted_score"], 10)
        self.assertEqual(result["timer_entry_weighted_score"], 7)
        self.assertEqual(result["timer_near_entry_weighted_score"], 10)
        self.assertEqual(result["timer_name_hint_weighted_score"], 10)
        self.assertFalse(result["stack_mappings"][2]["mapped"])
        self.assertEqual(result["timer_mappings"][0]["symbol"], "timer_callback")


if __name__ == "__main__":
    unittest.main()
