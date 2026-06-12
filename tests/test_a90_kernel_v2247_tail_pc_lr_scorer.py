"""Regression tests for a90_kernel_v2247_tail_pc_lr_scorer."""

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2247 = load_revalidation("a90_kernel_v2247_tail_pc_lr_scorer")


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def sample_summary(slide="0x1000", accepted=True, samples=None):
    return {
        "analysis": {
            "codeword": {
                "accepted_exact_codeword_slide": accepted,
                "accepted_near_exact_codeword_slide": False,
                "accepted_symbolization_slide": False,
                "acceptance_reason": "unit",
                "best": {
                    "slide": slide,
                    "slide_hex": slide,
                    "pc_match": 4,
                    "pc_readable": 5,
                    "lr_prev_match": 3,
                    "lr_prev_readable": 4,
                    "lr_match": 2,
                    "lr_readable": 4,
                    "weighted_score": 10,
                },
            }
        },
        "probe": {
            "samples": samples or [],
        },
    }


def target_summary(rows=None):
    return {
        "rows": rows
        if rows is not None
        else [
            {
                "symbol": "request_firmware",
                "stock_address_hex": "0xffffff8008100000",
                "stack_reported_size_hex": "0x40",
                "source": {"found": True, "path": "drivers/base/firmware_class.c"},
            },
            {
                "symbol": "qdf_file_read",
                "stock_address_hex": "0xffffff8008100100",
                "stack_reported_size_hex": "0x20",
                "source": {"found": True, "path": "qdf_file.c"},
            },
        ]
    }


class BasicLoaders(unittest.TestCase):
    def test_parse_int_accepts_int_decimal_hex_empty_and_invalid(self):
        self.assertEqual(v2247.parse_int(7), 7)
        self.assertEqual(v2247.parse_int("15"), 15)
        self.assertEqual(v2247.parse_int("0x10"), 16)
        self.assertIsNone(v2247.parse_int(""))
        self.assertIsNone(v2247.parse_int(None))
        with self.assertRaises(ValueError):
            v2247.parse_int("bad")

    def test_load_exact_slide_preserves_acceptance_metrics(self):
        loaded = v2247.load_exact_slide(sample_summary(slide="0x2000", accepted=True))

        self.assertTrue(loaded["available"])
        self.assertTrue(loaded["accepted_exact_codeword_slide"])
        self.assertTrue(loaded["accepted_symbolization_slide"])
        self.assertEqual(loaded["slide"], 0x2000)
        self.assertEqual(loaded["weighted_score"], 10)

    def test_load_exact_slide_can_report_unavailable(self):
        loaded = v2247.load_exact_slide(sample_summary(slide=None, accepted=False))

        self.assertFalse(loaded["available"])
        self.assertIsNone(loaded["slide"])
        self.assertFalse(loaded["accepted_symbolization_slide"])

    def test_load_targets_filters_incomplete_rows_and_sorts_by_start(self):
        rows = [
            {"symbol": "bad", "stock_address_hex": None, "stack_reported_size_hex": "0x10"},
            {"symbol": "later", "stock_address_hex": "0x3000", "stack_reported_size_hex": "0x20"},
            {"symbol": "first", "stock_address_hex": "0x2000", "stack_reported_size_hex": "0x10"},
        ]

        targets = v2247.load_targets(target_summary(rows))

        self.assertEqual([target["symbol"] for target in targets], ["first", "later"])
        self.assertEqual(targets[0]["start"], 0x2000)
        self.assertEqual(targets[0]["end"], 0x2010)
        self.assertEqual(targets[0]["size_hex"], "0x10")


class Scoring(unittest.TestCase):
    def test_target_for_static_uses_half_open_ranges(self):
        targets = v2247.load_targets(target_summary())

        self.assertEqual(v2247.target_for_static(0xFFFFFF8008100000, targets)["symbol"], "request_firmware")
        self.assertEqual(v2247.target_for_static(0xFFFFFF800810003F, targets)["symbol"], "request_firmware")
        self.assertIsNone(v2247.target_for_static(0xFFFFFF8008100040, targets))

    def test_sample_addresses_includes_pc_lr_and_lr_minus4_only_when_nonzero(self):
        addresses = v2247.sample_addresses({"ctx_pc": "0x1100", "ctx_lr": "0x1204"})

        self.assertEqual(addresses, {"ctx_pc": 0x1100, "ctx_lr": 0x1204, "ctx_lr_minus4": 0x1200})
        self.assertEqual(v2247.sample_addresses({"ctx_pc": 0, "ctx_lr": ""}), {})

    def test_score_samples_maps_runtime_addresses_to_static_targets(self):
        slide = 0x1000
        static_request = 0xFFFFFF8008100008
        static_qdf = 0xFFFFFF8008100104
        samples = [
            {
                "ctx_pc": f"0x{static_request + slide:x}",
                "ctx_lr": f"0x{static_qdf + 4 + slide:x}",
                "comm": "kworker",
                "pid": 101,
            },
            {
                "ctx_pc": "0x1234",
                "ctx_lr": None,
                "comm": "idle",
                "pid": 0,
            },
        ]

        scoring = v2247.score_samples(sample_summary(samples=samples), v2247.load_targets(target_summary()), slide)

        self.assertEqual(scoring["sample_count"], 2)
        self.assertEqual(scoring["hit_count"], 3)
        self.assertEqual(scoring["source_hit_counts"], {"ctx_lr": 1, "ctx_lr_minus4": 1, "ctx_pc": 1})
        self.assertEqual(scoring["symbol_hit_counts"], {"qdf_file_read": 2, "request_firmware": 1})
        self.assertEqual(scoring["comm_hit_counts"], {"kworker": 3})
        self.assertEqual(scoring["hits"][0]["symbol_offset_hex"], "0x8")


class SummaryBuilder(unittest.TestCase):
    def make_args(self, root: Path, sample_payload, target_payload):
        sample_path = root / "sample.json"
        target_path = root / "target.json"
        write_json(sample_path, sample_payload)
        write_json(target_path, target_payload)
        return argparse.Namespace(
            label="unit",
            sample_summary=sample_path,
            target_summary=target_path,
        )

    def test_build_summary_passes_with_usable_slide_and_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            static_request = 0xFFFFFF8008100010
            args = self.make_args(
                root,
                sample_summary(samples=[{"ctx_pc": f"0x{static_request + 0x1000:x}", "comm": "kworker"}]),
                target_summary(),
            )
            out_dir = root / "out"
            out_dir.mkdir()

            summary = v2247.build_summary(args, out_dir)
            private_score = json.loads(Path(summary["private_score"]["path"]).read_text(encoding="utf-8"))

        self.assertTrue(summary["pass"])
        self.assertEqual(summary["decision"], "v2247-tail-pc-lr-scorer-pass")
        self.assertEqual(summary["target_count"], 2)
        self.assertEqual(summary["scoring"]["hit_count"], 1)
        self.assertFalse(summary["private_score"]["contains_raw_runtime_addresses"])
        self.assertTrue(summary["private_score"]["contains_per_sample_symbol_hits"])
        self.assertEqual(private_score["scoring"]["hits"][0]["symbol"], "request_firmware")

    def test_build_summary_reports_no_usable_slide_before_no_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.make_args(root, sample_summary(slide=None, accepted=False), target_summary(rows=[]))
            out_dir = root / "out"
            out_dir.mkdir()

            summary = v2247.build_summary(args, out_dir)

        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "v2247-tail-pc-lr-scorer-no-usable-slide")
        self.assertEqual(summary["scoring"]["hit_count"], 0)

    def test_build_summary_reports_no_targets_when_slide_is_usable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = self.make_args(root, sample_summary(), target_summary(rows=[]))
            out_dir = root / "out"
            out_dir.mkdir()

            summary = v2247.build_summary(args, out_dir)

        self.assertFalse(summary["pass"])
        self.assertEqual(summary["decision"], "v2247-tail-pc-lr-scorer-no-targets")


if __name__ == "__main__":
    unittest.main()
