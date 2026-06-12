"""Regression tests for native_kernel_perf_regs_codeword_sample_ring_v2216."""

import json
import struct
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2216 = load_revalidation("native_kernel_perf_regs_codeword_sample_ring_v2216")

BASE = v2216.KERNEL_TEXT_MIN


class ParseAndSymbolHelpers(unittest.TestCase):
    def test_parse_int_and_helper_stdout_extracts_codeword_samples(self):
        stdout = (
            "result=v2216-perf-regs-codeword-sample-ring-complete\n"
            "offsets ctx_fp=0xe8 ctx_lr=0xf0 ctx_sp=0xf8 ctx_pc=0x100\n"
            "stats count=0x3 read_errors=1 sample_capacity=4\n"
            "samples occupied=2 capacity=4 printed=2\n"
            "sample idx=0 pid=100 tgid=100 comm=worker ctx_pc=0xffffff8008010000 "
            "ctx_pc_insn=0xd503201f ctx_lr=0xffffff8008010010 ctx_lr_prev_insn=0x94000000 "
            "ctx_lr_insn=0xd65f03c0 fp_slot_next=0xffffffc000001000 "
            "fp_slot_raw_lr=0xffffff8008020000 fp2_slot_next=0 fp2_slot_raw_lr=0\n"
            "sample idx=1 pid=101 tgid=101 comm=idle ctx_pc=0xffffffc000003000 "
            "ctx_pc_insn=0xaa0003e0 ctx_lr=0xffffffc000004000 ctx_lr_prev_insn=0x14000000 "
            "ctx_lr_insn=0xd503201f fp_slot_next=0 fp_slot_raw_lr=0xffffffc000005000 "
            "fp2_slot_next=0xffffffc000006000 fp2_slot_raw_lr=0xffffff8008040000\n"
        )

        parsed = v2216.parse_helper_stdout(stdout)

        self.assertEqual(v2216.parse_int("0x2a"), 42)
        self.assertEqual(parsed["offsets"], {"ctx_fp": 0xE8, "ctx_lr": 0xF0, "ctx_sp": 0xF8, "ctx_pc": 0x100})
        self.assertEqual(parsed["stats"], {"count": 3, "read_errors": 1, "sample_capacity": 4})
        self.assertEqual(parsed["sample_meta"], {"occupied": 2, "capacity": 4, "printed": 2})
        self.assertEqual(len(parsed["samples"]), 2)
        self.assertEqual(parsed["samples"][0]["comm"], "worker")
        self.assertEqual(parsed["samples"][0]["ctx_pc_insn"], 0xD503201F)
        self.assertEqual(parsed["samples"][1]["fp2_slot_raw_lr"], 0xFFFFFF8008040000)

    def test_classify_addr_text_symbols_symbol_index_and_nearest(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                f"{BASE + 0x1000:016x} T alpha\n"
                f"{BASE + 0x1800:016x} D ignored_data\n"
                f"{BASE + 0x2000:016x} W beta\n"
                "nothex T ignored\n"
                "ffffff9000000000 T outside\n",
                encoding="utf-8",
            )

            symbols = v2216.load_text_symbols(path)
            index = v2216.load_symbol_index(path)
            nearest = v2216.nearest_symbol(BASE + 0x1010, symbols)
            summarized = v2216.symbolize_counter(Counter({BASE + 0x1010: 2, BASE - 4: 1}), symbols)

        self.assertEqual(symbols, [(BASE + 0x1000, "alpha"), (BASE + 0x2000, "beta")])
        self.assertEqual(index["alpha"], BASE + 0x1000)
        self.assertEqual(index["ignored_data"], BASE + 0x1800)
        self.assertTrue(v2216.classify_addr(BASE + 0x1000)["kernel_text"])
        self.assertFalse(v2216.classify_addr(0)["kernel_va"])
        self.assertEqual(nearest["symbol"], "alpha")
        self.assertEqual(nearest["offset"], 0x10)
        self.assertEqual(summarized["direct_hits"], 2)
        self.assertAlmostEqual(summarized["direct_hit_fraction"], 2 / 3)
        self.assertIsNone(summarized["top"][1]["symbol"])

    def test_load_raw_meta_and_read_stock_u32(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "kernel.raw"
            raw_path.write_bytes(b"\x11\x22\x33\x44payload")
            wrapped = root / "wrapped.raw"
            wrapped.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 7) + b"payload")
            truncated = root / "truncated.raw"
            truncated.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 9) + b"short")
            meta = root / "stock.json"
            meta.write_text(json.dumps({"synthetic_base": hex(BASE)}), encoding="utf-8")

            self.assertEqual(v2216.load_kernel_raw(raw_path), b"\x11\x22\x33\x44payload")
            self.assertEqual(v2216.load_kernel_raw(wrapped), b"payload")
            with self.assertRaises(ValueError):
                v2216.load_kernel_raw(truncated)
            self.assertEqual(v2216.load_synthetic_base(meta), BASE)
            self.assertEqual(v2216.read_stock_u32(raw_path.read_bytes(), BASE, BASE), 0x44332211)
            self.assertIsNone(v2216.read_stock_u32(raw_path.read_bytes(), BASE, BASE - 4))


class CodewordAnalysis(unittest.TestCase):
    def write_codeword_fixture(self, root: Path, slide: int = 0x1000):
        raw = bytearray(0x1000)
        words = {
            BASE + 0x100: 0xD503201F,
            BASE + 0x200: 0x94000000,
            BASE + 0x204: 0xD65F03C0,
        }
        for addr, word in words.items():
            struct.pack_into("<I", raw, addr - BASE, word)
        raw_path = root / "kernel.raw"
        raw_path.write_bytes(raw)
        meta_path = root / "stock.json"
        meta_path.write_text(json.dumps({"synthetic_base": BASE}), encoding="utf-8")
        map_path = root / "System.map"
        map_path.write_text(
            f"{BASE:016x} T _text\n"
            f"{BASE:016x} T _stext\n"
            f"{BASE + 0x100:016x} T pc_func\n"
            f"{BASE + 0x200:016x} T lr_func\n"
            f"{BASE + 0x1000:016x} T _etext\n",
            encoding="utf-8",
        )
        v2215_path = root / "v2215-result.json"
        v2215_path.write_text(
            json.dumps({"p0_slide": {"best": {"slide": slide}, "top_candidates": [{"slide": slide}, {"slide": 0}]}}),
            encoding="utf-8",
        )
        sample = {
            "ctx_pc": BASE + 0x100 + slide,
            "ctx_pc_insn": words[BASE + 0x100],
            "ctx_lr": BASE + 0x204 + slide,
            "ctx_lr_prev_insn": words[BASE + 0x200],
            "ctx_lr_insn": words[BASE + 0x204],
        }
        return raw_path, meta_path, map_path, v2215_path, sample, slide

    def test_candidate_slides_and_generated_slides_from_codeword_scan(self):
        with tempfile.TemporaryDirectory(dir=v2216.REPO_ROOT) as tmp:
            raw_path, meta_path, map_path, v2215_path, sample, slide = self.write_codeword_fixture(Path(tmp))
            raw = v2216.load_kernel_raw(raw_path)
            symbol_index = {"_text": BASE, "_stext": BASE, "_etext": BASE + 0x1000}
            with mock.patch.object(v2216, "V2215_RESULT_PATH", v2215_path), \
                 mock.patch.object(v2216, "load_symbol_index", return_value=symbol_index):
                candidates = v2216.candidate_slides()
                generated = v2216.codeword_generated_slides([sample], raw, BASE)

        self.assertIn(0, candidates)
        self.assertIn(slide, candidates)
        self.assertIn(slide, generated)

    def test_codeword_match_analysis_accepts_unique_exact_slide(self):
        with tempfile.TemporaryDirectory(dir=v2216.REPO_ROOT) as tmp:
            raw_path, meta_path, map_path, v2215_path, sample, slide = self.write_codeword_fixture(Path(tmp))
            symbol_index = {"_text": BASE, "_stext": BASE, "_etext": BASE + 0x1000}
            raw = v2216.load_kernel_raw(raw_path)
            with mock.patch.object(v2216, "STOCK_RAW_PATH", raw_path), \
                 mock.patch.object(v2216, "STOCK_META_PATH", meta_path), \
                 mock.patch.object(v2216, "STOCK_MAP_PATH", map_path), \
                 mock.patch.object(v2216, "V2215_RESULT_PATH", v2215_path), \
                 mock.patch.object(v2216, "load_symbol_index", return_value=symbol_index), \
                 mock.patch.object(v2216, "load_kernel_raw", return_value=raw), \
                 mock.patch.object(v2216, "load_synthetic_base", return_value=BASE):
                analysis = v2216.codeword_match_analysis([sample])

        self.assertTrue(analysis["available"])
        self.assertTrue(analysis["accepted_exact_codeword_slide"])
        self.assertTrue(analysis["accepted_symbolization_slide"])
        self.assertEqual(analysis["acceptance_reason"], "exact_pc_lr_codeword_match")
        self.assertEqual(analysis["best"]["slide"], slide)
        self.assertEqual(analysis["best"]["pc_match"], 1)
        self.assertEqual(analysis["best"]["lr_prev_match"], 1)
        self.assertEqual(analysis["best"]["lr_match"], 1)
        self.assertGreaterEqual(analysis["best"]["weighted_score"], 7)

    def test_codeword_match_analysis_reports_missing_stock_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.raw"
            with mock.patch.object(v2216, "STOCK_RAW_PATH", missing):
                analysis = v2216.codeword_match_analysis([])

        self.assertEqual(analysis, {"available": False, "reason": "stock raw/meta missing"})


class ProbeAnalysisAndReport(unittest.TestCase):
    def test_analyze_probe_counts_codewords_symbols_and_saturation(self):
        probe = {
            "stats": {"count": 4, "sample_capacity": 2},
            "sample_meta": {"occupied": 2},
            "samples": [
                {
                    "pid": 100,
                    "comm": "worker",
                    "ctx_pc": BASE + 0x100,
                    "ctx_lr": BASE + 0x200,
                    "fp_slot_next": 0xFFFFFFC000001000,
                    "fp_slot_raw_lr": BASE + 0x300,
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
                    "fp2_slot_raw_lr": BASE + 0x400,
                },
            ],
        }
        symbols = [(BASE + 0x100, "pc_func"), (BASE + 0x200, "lr_func"), (BASE + 0x300, "raw_func")]
        codeword = {"available": True, "accepted_exact_codeword_slide": True, "best": {"slide_hex": "0x1000"}}

        with mock.patch.object(v2216, "load_text_symbols", return_value=symbols), \
             mock.patch.object(v2216, "codeword_match_analysis", return_value=codeword):
            analysis = v2216.analyze_probe(probe)

        self.assertEqual(analysis["counts"]["printed_samples"], 2)
        self.assertEqual(analysis["counts"]["walkable_fp_next"], 1)
        self.assertEqual(analysis["counts"]["walkable_fp2_next"], 1)
        self.assertEqual(analysis["counts"]["raw_lr_kernel_text"], 1)
        self.assertEqual(analysis["counts"]["raw_lr_kernel_va_nontext"], 1)
        self.assertEqual(analysis["counts"]["ctx_pc_kernel_text"], 1)
        self.assertEqual(analysis["counts"]["ctx_lr_kernel_text"], 1)
        self.assertEqual(analysis["counts"]["ctx_lr_kernel_va_nontext"], 1)
        self.assertEqual(analysis["unique_comm_count"], 2)
        self.assertEqual(analysis["unique_pid_count"], 2)
        self.assertTrue(analysis["sample_ring_saturated"])
        self.assertEqual(analysis["symbolization"]["ctx_pc"]["direct_hits"], 1)
        self.assertIs(analysis["codeword"], codeword)

    def test_render_report_includes_codeword_decision_tables_and_safety(self):
        summary = {
            "decision": "v2216-codeword-slide-exact",
            "pass": True,
            "selftest_fail0": True,
            "phase_timer_contract": "phase-v1",
            "residual_state_contract": "clean",
            "out_dir": "workspace/private/runs/kernel/v2216-test",
            "build": {"helper_sha256": "feedface"},
            "probe": {"stats": {"count": 4}},
            "analysis": {
                "counts": {
                    "printed_samples": 1,
                    "walkable_fp_next": 1,
                    "walkable_fp2_next": 0,
                    "raw_lr_nonzero": 1,
                    "raw_lr_kernel_text": 1,
                    "raw_lr_kernel_va_nontext": 0,
                    "ctx_pc_kernel_text": 1,
                    "ctx_lr_nonzero": 1,
                    "ctx_lr_kernel_text": 1,
                    "ctx_lr_kernel_va_nontext": 0,
                },
                "unique_counts": {"ctx_pc": 1, "fp_slot_raw_lr": 1, "fp_slot_next": 1, "fp2_slot_raw_lr": 0, "ctx_lr": 1},
                "unique_preview": {"ctx_pc": ["0xffffff8008010000"], "fp_slot_raw_lr": [], "fp_slot_next": [], "fp2_slot_raw_lr": [], "ctx_lr": []},
                "unique_comm_count": 1,
                "unique_pid_count": 1,
                "occupied_samples": 1,
                "capacity": 2,
                "sample_ring_saturated": False,
                "convergence_hint": "ring not saturated",
                "symbolization": {
                    "stock_map": "System.map",
                    "text_symbol_count": 3,
                    "ctx_pc": {"direct_hits": 1, "total": 1, "top": [{"count": 1, "addr": "0xffffff8008010000", "symbol": "pc_func", "offset": 0}]},
                    "ctx_lr": {"direct_hits": 1, "total": 1, "top": [{"count": 1, "addr": "0xffffff8008010004", "symbol": "lr_func", "offset": 4}]},
                },
                "codeword": {
                    "accepted_exact_codeword_slide": True,
                    "best": {"slide_hex": "0x1000"},
                    "stock_raw": "kernel.raw",
                    "candidate_source": "result.json",
                    "candidate_count": 1,
                    "top_candidates": [{"slide_hex": "0x1000", "weighted_score": 7, "pc_match": 1, "pc_readable": 1, "lr_prev_match": 1, "lr_prev_readable": 1, "lr_match": 1, "lr_readable": 1}],
                },
            },
            "safety": {"read_only_bpf": True, "probe_write_user_executed": False, "flash_reboot": False},
        }

        report = v2216.render_report(summary)

        self.assertIn("# Native Init V2216 Perf Regs Codeword Sample Ring", report)
        self.assertIn("- Decision: `v2216-codeword-slide-exact`", report)
        self.assertIn("- Codeword exact slide accepted: `true`", report)
        self.assertIn("| 1 | `0x1000` | 7 | 1/1 | 1/1 | 1/1 |", report)
        self.assertIn("| `ctx_pc` | 1 | `0xffffff8008010000` | `pc_func` | `0` |", report)
        self.assertIn("- read_only_bpf: `true`", report)
        self.assertIn("- Helper SHA-256: `feedface`", report)


if __name__ == "__main__":
    unittest.main()
