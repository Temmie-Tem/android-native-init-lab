"""Regression tests for native_kernel_perf_regs_frame_sample_ring_v2214."""

import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2214 = load_revalidation("native_kernel_perf_regs_frame_sample_ring_v2214")


class ParseAndSymbolHelpers(unittest.TestCase):
    def test_parse_int_accepts_decimal_and_hex(self):
        self.assertEqual(v2214.parse_int("42"), 42)
        self.assertEqual(v2214.parse_int("0x2a"), 42)
        self.assertEqual(v2214.parse_int("0X2A"), 42)

    def test_parse_helper_stdout_extracts_stats_meta_offsets_and_samples(self):
        stdout = (
            "result=v2214-perf-regs-frame-sample-ring-complete\n"
            "offsets ctx_fp=0xe8 ctx_lr=0xf0 ctx_sp=0xf8 ctx_pc=0x100\n"
            "stats count=0x4 read_errors=1 sample_capacity=4\n"
            "samples occupied=0x2 capacity=4 printed=2\n"
            "sample idx=0 pid=100 tgid=100 comm=worker ctx_pc=0xffffff8008010000 "
            "ctx_lr=0xffffff8008020000 fp_slot_next=0xffffffc000001000 "
            "fp_slot_raw_lr=0xffffff8008030000 fp2_slot_next=0 fp2_slot_raw_lr=0\n"
            "sample idx=1 pid=101 tgid=101 comm=idle ctx_pc=0xffffffc000003000 "
            "ctx_lr=0xffffffc000004000 fp_slot_next=0 fp_slot_raw_lr=0xffffffc000005000 "
            "fp2_slot_next=0xffffffc000006000 fp2_slot_raw_lr=0xffffff8008040000\n"
        )

        parsed = v2214.parse_helper_stdout(stdout)

        self.assertEqual(parsed["offsets"], {"ctx_fp": 0xE8, "ctx_lr": 0xF0, "ctx_sp": 0xF8, "ctx_pc": 0x100})
        self.assertEqual(parsed["stats"], {"count": 4, "read_errors": 1, "sample_capacity": 4})
        self.assertEqual(parsed["sample_meta"], {"occupied": 2, "capacity": 4, "printed": 2})
        self.assertEqual(len(parsed["samples"]), 2)
        self.assertEqual(parsed["samples"][0]["comm"], "worker")
        self.assertEqual(parsed["samples"][0]["ctx_pc"], 0xFFFFFF8008010000)
        self.assertEqual(parsed["samples"][1]["fp2_slot_raw_lr"], 0xFFFFFF8008040000)

    def test_classify_addr_and_load_text_symbols(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "ffffff8008001000 T alpha\n"
                "ffffff8008002000 D data_ignored\n"
                "nothex T ignored\n"
                "ffffff8008003000 W beta\n"
                "ffffff9000000000 T outside\n",
                encoding="utf-8",
            )

            symbols = v2214.load_text_symbols(path)

        self.assertEqual(symbols, [(0xFFFFFF8008001000, "alpha"), (0xFFFFFF8008003000, "beta")])
        text = v2214.classify_addr(0xFFFFFF8008001020)
        self.assertTrue(text["kernel_text"])
        self.assertTrue(text["aligned_4"])
        self.assertTrue(text["aligned_16"])
        self.assertFalse(v2214.classify_addr(0)["kernel_va"])

    def test_nearest_symbol_and_symbolize_counter(self):
        symbols = [
            (0xFFFFFF8008001000, "alpha"),
            (0xFFFFFF8008002000, "beta"),
        ]
        counter = Counter({
            0xFFFFFF8008001010: 2,
            0xFFFFFF8008002500: 1,
            0xFFFFFF8007FFFF00: 3,
        })

        nearest = v2214.nearest_symbol(0xFFFFFF8008001010, symbols)
        summarized = v2214.symbolize_counter(counter, symbols, limit=2)

        self.assertEqual(nearest["symbol"], "alpha")
        self.assertEqual(nearest["offset"], 0x10)
        self.assertIsNone(v2214.nearest_symbol(0xFFFFFF8007FFFF00, symbols))
        self.assertEqual(summarized["total"], 6)
        self.assertEqual(summarized["direct_hits"], 3)
        self.assertAlmostEqual(summarized["direct_hit_fraction"], 0.5)
        self.assertEqual(summarized["top"][0]["addr"], "0xffffff8007ffff00")
        self.assertIsNone(summarized["top"][0]["symbol"])


class ProbeAnalysis(unittest.TestCase):
    def test_analyze_probe_counts_regs_slots_uniques_and_symbolization(self):
        stock_symbols = [
            (v2214.KERNEL_TEXT_MIN + 0x100, "pc_func"),
            (v2214.KERNEL_TEXT_MIN + 0x200, "lr_func"),
            (v2214.KERNEL_TEXT_MIN + 0x300, "raw_func"),
        ]
        probe = {
            "stats": {"count": 4, "sample_capacity": 4},
            "sample_meta": {"occupied": 4},
            "samples": [
                {
                    "pid": 100,
                    "comm": "worker",
                    "ctx_pc": v2214.KERNEL_TEXT_MIN + 0x100,
                    "ctx_lr": v2214.KERNEL_TEXT_MIN + 0x200,
                    "fp_slot_next": 0xFFFFFFC000001000,
                    "fp_slot_raw_lr": v2214.KERNEL_TEXT_MIN + 0x300,
                    "fp2_slot_next": 0,
                    "fp2_slot_raw_lr": 0,
                },
                {
                    "pid": 101,
                    "comm": "idle",
                    "ctx_pc": 0xFFFFFFC000003000,
                    "ctx_lr": 0xFFFFFFC000004000,
                    "fp_slot_next": 0,
                    "fp_slot_raw_lr": 0xFFFFFFC000005000,
                    "fp2_slot_next": 0xFFFFFFC000006000,
                    "fp2_slot_raw_lr": v2214.KERNEL_TEXT_MIN + 0x300,
                },
                {
                    "pid": 100,
                    "comm": "worker",
                    "ctx_pc": v2214.KERNEL_TEXT_MIN + 0x100,
                    "ctx_lr": 0,
                    "fp_slot_next": 0,
                    "fp_slot_raw_lr": 0,
                    "fp2_slot_next": 0,
                    "fp2_slot_raw_lr": 0,
                },
            ],
        }

        with mock.patch.object(v2214, "load_text_symbols", return_value=stock_symbols):
            analysis = v2214.analyze_probe(probe)

        self.assertEqual(analysis["counts"]["printed_samples"], 3)
        self.assertEqual(analysis["counts"]["walkable_fp_next"], 1)
        self.assertEqual(analysis["counts"]["walkable_fp2_next"], 1)
        self.assertEqual(analysis["counts"]["raw_lr_nonzero"], 2)
        self.assertEqual(analysis["counts"]["raw_lr_kernel_text"], 1)
        self.assertEqual(analysis["counts"]["raw_lr_kernel_va_nontext"], 1)
        self.assertEqual(analysis["counts"]["ctx_pc_kernel_text"], 2)
        self.assertEqual(analysis["counts"]["ctx_lr_nonzero"], 2)
        self.assertEqual(analysis["counts"]["ctx_lr_kernel_text"], 1)
        self.assertEqual(analysis["counts"]["ctx_lr_kernel_va_nontext"], 1)
        self.assertEqual(analysis["unique_counts"]["ctx_pc"], 2)
        self.assertEqual(analysis["unique_counts"]["ctx_lr"], 2)
        self.assertEqual(analysis["unique_comms"], ["idle", "worker"])
        self.assertEqual(analysis["unique_pid_count"], 2)
        self.assertTrue(analysis["sample_ring_saturated"])
        self.assertEqual(analysis["symbolization"]["text_symbol_count"], 3)
        self.assertEqual(analysis["symbolization"]["ctx_pc"]["direct_hits"], 2)
        self.assertEqual(analysis["symbolization"]["ctx_lr"]["direct_hits"], 1)

    def test_analyze_probe_not_saturated_when_capacity_exceeds_occupied(self):
        with mock.patch.object(v2214, "load_text_symbols", return_value=[]):
            analysis = v2214.analyze_probe({
                "stats": {"sample_capacity": 8},
                "sample_meta": {"occupied": 2},
                "samples": [],
            })

        self.assertFalse(analysis["sample_ring_saturated"])
        self.assertEqual(analysis["capacity"], 8)
        self.assertEqual(analysis["occupied_samples"], 2)
        self.assertIn("longer duration", analysis["convergence_hint"])


class ReportRendering(unittest.TestCase):
    def test_render_report_includes_perf_metrics_symbols_safety_and_evidence(self):
        summary = {
            "decision": "v2214-perf-regs-frame-sample-ring-captured",
            "pass": True,
            "selftest_fail0": True,
            "phase_timer_contract": "phase-v1",
            "residual_state_contract": "clean",
            "out_dir": "workspace/private/runs/kernel/v2214-test",
            "build": {"helper_sha256": "feedface"},
            "probe": {"stats": {"count": 4}},
            "analysis": {
                "counts": {
                    "printed_samples": 2,
                    "walkable_fp_next": 1,
                    "walkable_fp2_next": 0,
                    "raw_lr_nonzero": 2,
                    "raw_lr_kernel_text": 1,
                    "raw_lr_kernel_va_nontext": 1,
                    "ctx_pc_kernel_text": 2,
                    "ctx_lr_nonzero": 2,
                    "ctx_lr_kernel_text": 1,
                    "ctx_lr_kernel_va_nontext": 1,
                },
                "unique_counts": {
                    "ctx_pc": 2,
                    "fp_slot_raw_lr": 2,
                    "fp_slot_next": 1,
                    "fp2_slot_raw_lr": 1,
                    "ctx_lr": 2,
                },
                "unique_preview": {
                    "ctx_pc": ["0xffffff8008010000"],
                    "fp_slot_raw_lr": ["0xffffff8008020000"],
                    "fp_slot_next": [],
                    "fp2_slot_raw_lr": [],
                    "ctx_lr": ["0xffffff8008030000"],
                },
                "unique_comm_count": 2,
                "unique_pid_count": 2,
                "occupied_samples": 2,
                "capacity": 4,
                "sample_ring_saturated": False,
                "convergence_hint": "ring not saturated; longer duration can still add information",
                "symbolization": {
                    "stock_map": "workspace/private/runs/kernel/v2197-stock-kallsyms/System.map",
                    "text_symbol_count": 10,
                    "ctx_pc": {
                        "direct_hits": 2,
                        "total": 2,
                        "top": [
                            {
                                "count": 2,
                                "addr": "0xffffff8008010000",
                                "symbol": "pc_func",
                                "offset": 4,
                            }
                        ],
                    },
                    "ctx_lr": {
                        "direct_hits": 1,
                        "total": 2,
                        "top": [
                            {
                                "count": 1,
                                "addr": "0xffffff8008030000",
                                "symbol": "lr_func",
                                "offset": 8,
                            }
                        ],
                    },
                },
            },
            "safety": {
                "read_only_bpf": True,
                "probe_write_user_executed": False,
                "flash_reboot": False,
            },
        }

        report = v2214.render_report(summary)

        self.assertIn("# Native Init V2214 Perf Regs Frame Sample Ring", report)
        self.assertIn("- Decision: `v2214-perf-regs-frame-sample-ring-captured`", report)
        self.assertIn("- Live ctx PC in kernel text: `2`", report)
        self.assertIn("- Direct stock-map ctx PC hits: `2` / `2`", report)
        self.assertIn("| `ctx_pc` | 2 | 0xffffff8008010000 |", report)
        self.assertIn("| `ctx_pc` | 2 | `0xffffff8008010000` | `pc_func` | `4` |", report)
        self.assertIn("- read_only_bpf: `true`", report)
        self.assertIn("- Helper SHA-256: `feedface`", report)


if __name__ == "__main__":
    unittest.main()
