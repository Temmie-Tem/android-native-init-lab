"""Regression tests for a90_kernel_v2217_exact_slide_resymbolization_audit."""

import json
import struct
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2217 = load_revalidation("a90_kernel_v2217_exact_slide_resymbolization_audit")

BASE = v2217.KERNEL_TEXT_MIN


def encode_bl(pc: int, target: int) -> int:
    imm26 = ((target - pc) >> 2) & 0x03FFFFFF
    return 0x94000000 | imm26


class ScalarMapAndInstructionHelpers(unittest.TestCase):
    def test_parse_int_hex_and_exact_slide_extraction(self):
        self.assertEqual(v2217.parse_int(7), 7)
        self.assertEqual(v2217.parse_int("42"), 42)
        self.assertEqual(v2217.parse_int("0x2a"), 42)
        self.assertEqual(v2217.hex64(-1), "0xffffffffffffffff")
        self.assertEqual(v2217.hex_signed(-0x20), "-0x20")
        self.assertEqual(v2217.hex_signed(0x20), "0x20")
        summary = {"analysis": {"codeword": {"accepted_exact_codeword_slide": True, "best": {"slide": "0x84ef4"}}}}
        self.assertEqual(v2217.extract_exact_slide(summary), 0x84EF4)
        with self.assertRaises(ValueError):
            v2217.extract_exact_slide({"analysis": {"codeword": {"accepted_exact_codeword_slide": False}}})

    def test_parse_system_map_index_and_nearest_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "nothex T ignored\n"
                f"{BASE + 0x3000:016x} T beta\n"
                f"{BASE + 0x1000:016x} T alpha\n"
                f"{BASE + 0x2000:016x} W alpha\n",
                encoding="utf-8",
            )
            symbols = v2217.parse_system_map(path)
            index = v2217.build_symbol_index(symbols)
            addresses = [symbol.address for symbol in symbols]
            nearest = v2217.nearest_symbol(symbols, addresses, BASE + 0x2100)

        self.assertEqual([symbol.address for symbol in symbols], [BASE + 0x1000, BASE + 0x2000, BASE + 0x3000])
        self.assertEqual(index["alpha"], BASE + 0x1000)
        self.assertEqual(nearest["symbol"], "alpha")
        self.assertEqual(nearest["kind"], "W")
        self.assertEqual(nearest["offset"], 0x100)
        self.assertEqual(nearest["offset_hex"], "0x100")
        self.assertIsNone(v2217.nearest_symbol(symbols, addresses, BASE + 0x0FFF))

    def test_load_raw_meta_read_u32_and_instruction_kinds(self):
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

            self.assertEqual(v2217.load_kernel_raw(raw_path), b"\x11\x22\x33\x44payload")
            self.assertEqual(v2217.load_kernel_raw(wrapped), b"payload")
            with self.assertRaises(ValueError):
                v2217.load_kernel_raw(truncated)
            self.assertEqual(v2217.load_synthetic_base(meta), BASE)
            self.assertEqual(v2217.read_u32(raw_path.read_bytes(), BASE, BASE), 0x44332211)
            self.assertIsNone(v2217.read_u32(raw_path.read_bytes(), BASE, BASE - 4))

        bl = encode_bl(BASE + 0x100, BASE + 0x200)
        self.assertTrue(v2217.is_bl(bl))
        self.assertEqual(v2217.decode_bl_target(bl, BASE + 0x100), BASE + 0x200)
        self.assertEqual(v2217.decode_insn_kind(None), "out-of-range")
        self.assertEqual(v2217.decode_insn_kind(bl), "bl")
        self.assertEqual(v2217.decode_insn_kind(0x14000000), "b")
        self.assertEqual(v2217.decode_insn_kind(0xD63F0000), "blr_x0")
        self.assertEqual(v2217.decode_insn_kind(0xD61F0000), "br_x0")
        self.assertEqual(v2217.decode_insn_kind(0xD65F03C0), "ret")
        self.assertEqual(v2217.decode_insn_kind(0xCA1103D0), "ropp_eor_x16_x30_x17")
        self.assertEqual(v2217.decode_insn_kind(0x00BE7BAD), "jopp_magic")
        self.assertEqual(v2217.decode_insn_kind(0xD503201F), "other")


class SymbolizationAndRoppAudit(unittest.TestCase):
    def build_fixture(self):
        raw = bytearray(0x2000)
        direct_call = BASE + 0x100
        spring_call = BASE + 0x180
        direct_target = BASE + 0x900
        spring_target = BASE + 0xA00
        struct.pack_into("<I", raw, direct_call - BASE, encode_bl(direct_call, direct_target))
        struct.pack_into("<I", raw, spring_call - BASE, encode_bl(spring_call, spring_target))
        symbols = [
            v2217.Symbol(BASE, "T", "_text"),
            v2217.Symbol(BASE, "T", "_stext"),
            v2217.Symbol(direct_call, "T", "caller"),
            v2217.Symbol(spring_call, "T", "spring_caller"),
            v2217.Symbol(direct_target, "T", "target_func"),
            v2217.Symbol(spring_target, "T", "jopp_springboard_blr_x0"),
            v2217.Symbol(BASE + 0x1000, "T", "_etext"),
        ]
        symbols.sort(key=lambda symbol: symbol.address)
        addresses = [symbol.address for symbol in symbols]
        index = v2217.build_symbol_index(symbols)
        ranges = v2217.build_function_ranges(symbols, BASE, BASE + 0x1000)
        starts = [item.start for item in ranges]
        callsites = v2217.build_callsite_map(bytes(raw), BASE, symbols, addresses, index)
        return bytes(raw), ranges, starts, callsites, direct_call + 4, spring_call + 4

    def test_function_ranges_lookup_and_callsite_map(self):
        _raw, ranges, starts, callsites, direct_return, spring_return = self.build_fixture()

        self.assertEqual(v2217.function_lookup(ranges, starts, BASE + 0x110).name, "caller")
        self.assertIsNone(v2217.function_lookup(ranges, starts, BASE + 0x2000))
        self.assertEqual(callsites[direct_return][0].kind, "direct")
        self.assertEqual(callsites[direct_return][0].target_symbol, "target_func")
        self.assertEqual(callsites[spring_return][0].kind, "springboard")
        self.assertEqual(callsites[spring_return][0].target_symbol, "jopp_springboard_blr_x0")

    def test_resymbolize_live_regs_counts_symbols_callsites_and_insn_kind(self):
        raw, ranges, starts, callsites, direct_return, spring_return = self.build_fixture()
        slide = 0x80000
        samples = [
            {
                "pid": 100,
                "comm": "worker",
                "ctx_pc": BASE + 0x110 + slide,
                "ctx_pc_insn": 0,
                "ctx_lr": direct_return + slide,
                "ctx_lr_prev_insn": encode_bl(BASE + 0x100, BASE + 0x900),
                "fp_slot_raw_lr": 0,
                "fp2_slot_raw_lr": 0,
            },
            {
                "pid": 101,
                "comm": "spring",
                "ctx_pc": BASE + 0x190 + slide,
                "ctx_pc_insn": 0,
                "ctx_lr": spring_return + slide,
                "ctx_lr_prev_insn": encode_bl(BASE + 0x180, BASE + 0xA00),
                "fp_slot_raw_lr": 0,
                "fp2_slot_raw_lr": 0,
            },
            {
                "pid": 102,
                "comm": "outside",
                "ctx_pc": BASE + 0x3000 + slide,
                "ctx_pc_insn": 0,
                "ctx_lr": 0xFFFFFFC000001000,
                "ctx_lr_prev_insn": 0,
                "fp_slot_raw_lr": 0,
                "fp2_slot_raw_lr": 0,
            },
        ]

        live = v2217.resymbolize_live_regs(samples, slide, ranges, starts, callsites, raw, BASE)

        self.assertEqual(live["sample_count"], 3)
        self.assertEqual(live["pc_resolved"], 2)
        self.assertEqual(live["lr_resolved"], 2)
        self.assertEqual(live["lr_callsite"], 2)
        self.assertEqual(live["lr_user_or_nontext"], 1)
        self.assertIn(("caller", 1), live["pc_top_symbols"])
        self.assertEqual(live["preview"][0]["ctx_pc_symbol"], "caller")
        self.assertEqual(live["preview"][0]["ctx_lr_symbol"], "caller")
        self.assertTrue(live["preview"][0]["ctx_lr_callsite"])
        self.assertEqual(live["preview"][0]["ctx_lr_prev_insn_kind"], "bl")
        self.assertEqual(live["preview"][1]["ctx_lr_callsite_kind"], ["springboard"])

    def test_ropp_decode_attempt_reports_unique_and_reduced_context(self):
        raw, ranges, starts, callsites, direct_return, _spring_return = self.build_fixture()
        callsites = {direct_return: callsites[direct_return]}
        slide = 0x80000
        runtime_return = direct_return + slide
        key = 0x123456789ABCDEF0
        samples = [
            {
                "pid": 100,
                "comm": "worker",
                "ctx_pc": BASE + 0x110 + slide,
                "fp_slot_raw_lr": runtime_return ^ key,
                "fp2_slot_raw_lr": runtime_return ^ key,
            },
            {
                "pid": 101,
                "comm": "miss",
                "ctx_pc": BASE + 0x110 + slide,
                "fp_slot_raw_lr": runtime_return ^ key,
                "fp2_slot_raw_lr": (runtime_return ^ key) ^ 0x40,
            },
            {
                "pid": 102,
                "comm": "skip",
                "ctx_pc": BASE + 0x110 + slide,
                "fp_slot_raw_lr": 0,
                "fp2_slot_raw_lr": runtime_return ^ key,
            },
        ]

        ropp = v2217.ropp_decode_attempt(samples, slide, callsites, raw, BASE, ranges, starts)

        self.assertEqual(ropp["tested_samples"], 2)
        self.assertEqual(ropp["unique_samples"], 1)
        self.assertEqual(ropp["no_match_samples"], 1)
        self.assertEqual(ropp["ambiguous_samples"], 0)
        self.assertEqual(ropp["same_function_context_unique_samples"], 1)
        self.assertFalse(ropp["accepted_exact_unwind"])
        self.assertEqual(ropp["candidate_count_min"], 0)
        self.assertEqual(ropp["candidate_count_max"], 1)
        self.assertEqual(ropp["preview"][0]["examples"][0]["key"], v2217.hex64(key))
        self.assertEqual(ropp["preview"][0]["examples"][0]["decoded_1_symbol"], "caller")


class ReportRendering(unittest.TestCase):
    def test_render_report_includes_live_and_ropp_sections(self):
        result = {
            "decision": "v2217-live-resymbolized-ropp-still-ambiguous",
            "exact_slide_hex": "0x84ef4",
            "out_dir": "workspace/private/runs/kernel/v2217-test",
            "inputs": {
                "v2216_summary": "summary.json",
                "system_map": "System.map",
                "kernel_raw": "kernel.raw",
            },
            "live_resymbolization": {
                "sample_count": 1,
                "pc_resolved": 1,
                "lr_resolved": 1,
                "lr_callsite": 1,
                "pc_top_symbols": [("caller", 1)],
                "lr_top_symbols": [("caller", 1)],
                "preview": [
                    {
                        "index": 0,
                        "pid": 100,
                        "comm": "worker",
                        "ctx_pc_symbol": "caller",
                        "ctx_pc_offset": 16,
                        "ctx_lr_symbol": "caller",
                        "ctx_lr_offset": 4,
                        "ctx_lr_callsite": True,
                        "ctx_lr_prev_insn_kind": "bl",
                    }
                ],
            },
            "ropp_decode": {
                "accepted_exact_unwind": False,
                "tested_samples": 1,
                "unique_samples": 0,
                "ambiguous_samples": 1,
                "no_match_samples": 0,
                "same_function_context_unique_samples": 0,
                "candidate_count_min": 2,
                "candidate_count_median": 2,
                "candidate_count_max": 2,
                "reduced_count_min": 0,
                "reduced_count_median": 0,
                "reduced_count_max": 0,
                "reason": "ambiguous",
                "preview": [
                    {
                        "index": 0,
                        "pid": 100,
                        "comm": "worker",
                        "ctx_pc_function": "caller",
                        "candidate_count": 2,
                        "same_function_reduced_count": 0,
                        "encoded_1": "0x1",
                        "encoded_2": "0x2",
                    }
                ],
            },
            "safety": {"host_only": True, "live_device_access": False, "flash_reboot": False},
        }

        report = v2217.render_report(result)

        self.assertIn("# Native Init V2217 Exact Slide Resymbolization Audit", report)
        self.assertIn("- Decision: `v2217-live-resymbolized-ropp-still-ambiguous`", report)
        self.assertIn("- Exact slide: `0x84ef4`", report)
        self.assertIn("| `ctx_pc` | caller:1 |", report)
        self.assertIn("| 0 | 100 | `worker` | `caller` | `16` | `caller` | `4` | `true` | `bl` |", report)
        self.assertIn("| 0 | 100 | `worker` | `caller` | 2 | 0 | `0x1` | `0x2` |", report)
        self.assertIn("- host_only: `true`", report)


if __name__ == "__main__":
    unittest.main()
