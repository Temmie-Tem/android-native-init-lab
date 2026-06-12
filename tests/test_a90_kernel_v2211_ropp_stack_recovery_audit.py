"""Regression tests for a90_kernel_v2211_ropp_stack_recovery_audit."""

import argparse
import json
import struct
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2211 = load_revalidation("a90_kernel_v2211_ropp_stack_recovery_audit")


def encode_bl(pc: int, target: int) -> int:
    imm26 = ((target - pc) >> 2) & 0x03FFFFFF
    return 0x94000000 | imm26


class ScalarSymbolAndImageHelpers(unittest.TestCase):
    def test_parse_int_and_hex_formatters(self):
        self.assertEqual(v2211.parse_int(7), 7)
        self.assertEqual(v2211.parse_int("42"), 42)
        self.assertEqual(v2211.parse_int("0x2a"), 42)
        self.assertEqual(v2211.hex64(-1), "0xffffffffffffffff")
        self.assertEqual(v2211.hex_signed(-0x20), "-0x20")
        self.assertEqual(v2211.hex_signed(0x20), "0x20")

    def test_parse_system_map_build_index_and_nearest_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "not-hex T ignored\n"
                "ffffff8008003000 T beta\n"
                "ffffff8008001000 T alpha\n"
                "ffffff8008002000 W alpha\n",
                encoding="utf-8",
            )

            symbols = v2211.parse_system_map(path)
            index = v2211.build_symbol_index(symbols)
            addresses = [symbol.address for symbol in symbols]
            nearest = v2211.nearest_symbol(symbols, addresses, 0xFFFFFF8008002100)

        self.assertEqual([symbol.address for symbol in symbols], [0xFFFFFF8008001000, 0xFFFFFF8008002000, 0xFFFFFF8008003000])
        self.assertEqual(index["alpha"], 0xFFFFFF8008001000)
        self.assertEqual(nearest["symbol"], "alpha")
        self.assertEqual(nearest["kind"], "W")
        self.assertEqual(nearest["offset_hex"], "0x100")
        self.assertIsNone(v2211.nearest_symbol(symbols, addresses, 0xFFFFFF8008000FFF))

    def test_load_kernel_raw_config_and_read_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "raw"
            raw_path.write_bytes(b"\x00\x01\x02\x03kernel")
            wrapped = root / "wrapped"
            wrapped.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 6) + b"kernel")
            truncated = root / "truncated"
            truncated.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 10) + b"short")
            meta = root / "stock.json"
            meta.write_text(json.dumps({"synthetic_base": "0xffffff8008000000"}), encoding="utf-8")
            config = root / "autoconf.h"
            config.write_text(
                '#define CONFIG_RKP_CFP 1\n#define CONFIG_RKP_CFP_ROPP_SYSREGKEY "y"\n',
                encoding="utf-8",
            )

            self.assertEqual(v2211.load_kernel_raw(raw_path), b"\x00\x01\x02\x03kernel")
            self.assertEqual(v2211.load_kernel_raw(wrapped), b"kernel")
            with self.assertRaises(ValueError):
                v2211.load_kernel_raw(truncated)
            self.assertEqual(v2211.load_synthetic_base(meta), 0xFFFFFF8008000000)
            self.assertEqual(v2211.parse_config_symbols(config)["CONFIG_RKP_CFP_ROPP_SYSREGKEY"], "y")
            self.assertEqual(v2211.read_u32(raw_path.read_bytes(), 0xFFFFFF8008000000, 0xFFFFFF8008000000), 0x03020100)
            self.assertIsNone(v2211.read_u32(raw_path.read_bytes(), 0xFFFFFF8008000000, 0xFFFFFF8007FFFFFC))

    def test_bl_helpers_decode_positive_and_negative_targets(self):
        pc = 0xFFFFFF8008001000
        forward = pc + 0x40
        backward = pc - 0x40
        forward_insn = encode_bl(pc, forward)
        backward_insn = encode_bl(pc, backward)

        self.assertTrue(v2211.is_bl(forward_insn))
        self.assertFalse(v2211.is_bl(0xD65F03C0))
        self.assertEqual(v2211.decode_bl_target(forward_insn, pc), forward)
        self.assertEqual(v2211.decode_bl_target(backward_insn, pc), backward)


class CallsiteAndStackHelpers(unittest.TestCase):
    def build_callsite_fixture(self):
        synthetic_base = v2211.KERNEL_VA_MIN
        raw = bytearray(0x1000)
        direct_call = synthetic_base + 0x100
        spring_call = synthetic_base + 0x180
        target = synthetic_base + 0x300
        springboard = synthetic_base + 0x400
        struct.pack_into("<I", raw, direct_call - synthetic_base, encode_bl(direct_call, target))
        struct.pack_into("<I", raw, spring_call - synthetic_base, encode_bl(spring_call, springboard))
        symbols = [
            v2211.Symbol(synthetic_base, "T", "_stext"),
            v2211.Symbol(synthetic_base, "T", "_text"),
            v2211.Symbol(target, "T", "target_func"),
            v2211.Symbol(springboard, "T", "jopp_springboard_blr_x0"),
            v2211.Symbol(synthetic_base + 0x800, "T", "_etext"),
        ]
        symbols.sort(key=lambda symbol: symbol.address)
        symbol_index = v2211.build_symbol_index(symbols)
        callsites = v2211.build_callsite_map(bytes(raw), synthetic_base, symbols, symbol_index)
        return synthetic_base, bytes(raw), symbols, callsites, direct_call + 4, spring_call + 4

    def test_build_callsite_map_classifies_direct_and_springboard_returns(self):
        _base, _raw, _symbols, callsites, direct_return, spring_return = self.build_callsite_fixture()

        self.assertIn(direct_return, callsites)
        self.assertIn(spring_return, callsites)
        self.assertEqual(callsites[direct_return][0].kind, "direct")
        self.assertEqual(callsites[direct_return][0].target_symbol, "target_func")
        self.assertEqual(callsites[spring_return][0].kind, "springboard")
        self.assertEqual(callsites[spring_return][0].target_symbol, "jopp_springboard_blr_x0")

    def test_candidate_slides_stack_rows_and_joint_key_solver(self):
        _base, _raw, symbols, callsites, direct_return, spring_return = self.build_callsite_fixture()
        addresses = [symbol.address for symbol in symbols]
        slide = 0x80000
        stack_ips = [direct_return + slide, spring_return + slide, v2211.KERNEL_VA_MIN + 0x700]
        rows = v2211.stack_rows_for_slide(stack_ips, slide, callsites, symbols, addresses)
        key = 0x12345678
        encoded_stack = [(direct_return + slide) ^ key, (spring_return + slide) ^ key]
        joint = v2211.solve_joint_keys(encoded_stack, slide, [direct_return, spring_return], callsites)
        slides = v2211.candidate_slides(
            {"top_slide_candidates": [{"slide": "0x1000"}]},
            {
                "top_timer_candidates": [{"slide": "0x2000"}],
                "stack_candidate_cross_check": [{"slide": "0x3000"}],
            },
        )

        self.assertTrue(rows[0]["direct_callsite"])
        self.assertTrue(rows[1]["springboard_callsite"])
        self.assertFalse(rows[2]["direct_callsite"])
        self.assertEqual(joint[0]["key"], v2211.hex64(key))
        self.assertEqual(joint[0]["distinct_frame_count"], 2)
        self.assertEqual(slides, [0x1000, 0x2000, 0x3000, 0x80000])

    def test_source_evidence_detects_ropp_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stacktrace = root / "stacktrace.c"
            instrument = root / "instrument.py"
            stacktrace.write_text(
                "if (frame->pc < 0xffffff8008000000) ropp_enable_backtrace();\n"
                "if (((frame->pc & 0x3) != 0)) ropp_enable_backtrace();\n",
                encoding="utf-8",
            )
            instrument.write_text(
                "eor RRX, x30, RRK\nstp x29, RRX\nldp x29, RRX\n"
                "eor x30, RRX, RRK\n",
                encoding="utf-8",
            )

            evidence = v2211.source_evidence(stacktrace, instrument)

        self.assertTrue(evidence["stacktrace_decode_outside_kernel_range"])
        self.assertTrue(evidence["stacktrace_decode_misaligned_kernel_range"])
        self.assertTrue(evidence["instrument_eor_lr_key"])
        self.assertTrue(evidence["instrument_stp_encoded_lr"])
        self.assertTrue(evidence["instrument_ldp_decode"])


class AnalyzeAndReport(unittest.TestCase):
    def write_inputs(self, root: Path) -> argparse.Namespace:
        synthetic_base = v2211.KERNEL_VA_MIN
        raw = bytearray(0x2000)
        calls = [
            (synthetic_base + 0x100, synthetic_base + 0x900),
            (synthetic_base + 0x180, synthetic_base + 0xA00),
            (synthetic_base + 0x200, synthetic_base + 0xB00),
        ]
        for call, target in calls:
            struct.pack_into("<I", raw, call - synthetic_base, encode_bl(call, target))
        kernel_raw = root / "kernel.raw"
        kernel_raw.write_bytes(raw)
        stock_meta = root / "stock.json"
        stock_meta.write_text(json.dumps({"synthetic_base": synthetic_base}), encoding="utf-8")
        system_map = root / "System.map"
        system_map.write_text(
            "\n".join(
                [
                    f"{synthetic_base:016x} T _text",
                    f"{synthetic_base:016x} T _stext",
                    f"{synthetic_base + 0x900:016x} T one",
                    f"{synthetic_base + 0xA00:016x} T jopp_springboard_blr_x1",
                    f"{synthetic_base + 0xB00:016x} T three",
                    f"{synthetic_base + 0x1000:016x} T _etext",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        slide = 0x80000
        v2197 = root / "symbolization.json"
        v2197.write_text(
            json.dumps(
                {
                    "raw_stack_ips": [v2211.hex64(call + 4 + slide) for call, _target in calls],
                    "top_slide_candidates": [{"slide": v2211.hex_signed(slide)}],
                }
            ),
            encoding="utf-8",
        )
        v2198 = root / "v2198.json"
        v2198.write_text(
            json.dumps(
                {
                    "top_timer_candidates": [{"slide": v2211.hex_signed(slide)}],
                    "stack_candidate_cross_check": [],
                }
            ),
            encoding="utf-8",
        )
        autoconf = root / "autoconf.h"
        autoconf.write_text(
            "#define CONFIG_RKP_CFP 1\n"
            "#define CONFIG_RKP_CFP_JOPP 1\n"
            "#define CONFIG_RKP_CFP_ROPP 1\n"
            "#define CONFIG_RKP_CFP_ROPP_SYSREGKEY 1\n",
            encoding="utf-8",
        )
        stacktrace = root / "stacktrace.c"
        stacktrace.write_text(
            "if (frame->pc < 0xffffff8008000000) ropp_enable_backtrace();\n"
            "if (((frame->pc & 0x3) != 0)) ropp_enable_backtrace();\n",
            encoding="utf-8",
        )
        instrument = root / "instrument.py"
        instrument.write_text("eor RRX, x30, RRK\nstp x29, RRX\neor x30, RRX, RRK\n", encoding="utf-8")
        return argparse.Namespace(
            system_map=system_map,
            kernel_raw=kernel_raw,
            stock_meta=stock_meta,
            v2197_symbolization=v2197,
            v2198_result=v2198,
            stacktrace_c=stacktrace,
            rkp_instrument=instrument,
            autoconf=autoconf,
            enable_joint_key_exhaustive=True,
            max_joint_callsites=100,
        )

    def test_analyze_accepts_strong_stack_callsite_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = v2211.analyze(self.write_inputs(Path(tmp)))

        self.assertEqual(result["decision"], "v2211-stack-callsite-slide-candidate")
        self.assertEqual(result["stack"]["count"], 3)
        self.assertTrue(result["stack"]["all_canonical_aligned"])
        self.assertEqual(result["top_slide_rows"][0]["callsite_hits"], 3)
        self.assertEqual(result["top_slide_rows"][0]["unique_callsite_runtime_hits"], 3)
        self.assertEqual(result["callsites"]["record_count"], 3)
        self.assertTrue(result["source_evidence"]["stacktrace_decode_outside_kernel_range"])
        self.assertEqual(result["config"]["CONFIG_RKP_CFP_ROPP_SYSREGKEY"], "1")
        self.assertTrue(result["safety"]["host_only"])

    def test_render_table_and_markdown_include_recovery_decision(self):
        table = v2211.render_table(["A"], [["x|y"]])
        self.assertIn("x\\|y", table)

        result = {
            "decision": "v2211-ropp-stack-recovery-blocked-by-canonical-pass-through",
            "reason": "blocked",
            "stack": {"count": 1, "all_canonical_aligned": True},
            "slide_candidate_count": 1,
            "source_evidence": {"stacktrace_c": "stacktrace.c", "instrument_py": "instrument.py"},
            "callsites": {
                "scan_range": {"start": "0x1", "end": "0x2"},
                "return_address_count": 1,
                "record_count": 1,
                "springboard_record_count": 0,
            },
            "joint_key_quality": {
                "search_enabled": False,
                "strong_joint_key_slide_count": 0,
                "accepted": False,
                "rejection_reason": "skipped",
            },
            "top_slide_rows": [
                {
                    "slide_hex": "0x80000",
                    "callsite_hits": 0,
                    "unique_callsite_runtime_hits": 0,
                    "direct_callsite_hits": 0,
                    "springboard_callsite_hits": 0,
                    "best_joint_key_distinct_frames": 0,
                    "best_joint_key": None,
                    "rows": [
                        {
                            "index": 0,
                            "runtime": "0xffffff8009a42334",
                            "static": "0xffffff80099c2334",
                            "nearest_symbol": {"symbol": "__schedule", "offset_hex": "0x10"},
                            "direct_callsite": False,
                            "springboard_callsite": False,
                        }
                    ],
                }
            ],
            "safety": {"host_only": True, "live_device_access": False},
            "inputs": {
                "v2197_symbolization": "symbolization.json",
                "v2198_result": "v2198.json",
                "kernel_raw": "kernel.raw",
            },
        }
        report = v2211.render_markdown(result)

        self.assertIn("# Native Init V2211 ROPP Stack Recovery Audit", report)
        self.assertIn("- Decision: `v2211-ropp-stack-recovery-blocked-by-canonical-pass-through`", report)
        self.assertIn("| `0x80000` | 0 | 0 | 0 | 0 | 0 | - |", report)
        self.assertIn("| 0 | `0xffffff8009a42334` | `0xffffff80099c2334` | `__schedule`0x10 | false | false |", report)
        self.assertIn("- host_only: `true`", report)


if __name__ == "__main__":
    unittest.main()
