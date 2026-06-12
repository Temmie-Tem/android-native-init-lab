"""Regression tests for a90_kernel_v2207_jopp_stub_mapper host helpers."""

import argparse
import json
import struct
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2207 = load_revalidation("a90_kernel_v2207_jopp_stub_mapper")


class ScalarSymbolAndImageHelpers(unittest.TestCase):
    def test_parse_int_and_hex_formatters(self):
        self.assertEqual(v2207.parse_int(7), 7)
        self.assertEqual(v2207.parse_int("42"), 42)
        self.assertEqual(v2207.parse_int("0x2a"), 42)
        self.assertEqual(v2207.hex64(-1), "0xffffffffffffffff")
        self.assertEqual(v2207.hex_signed(-0x20), "-0x20")
        self.assertEqual(v2207.hex_signed(0x20), "0x20")

    def test_parse_system_map_build_index_and_nearest_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "not-hex T ignored\n"
                "0000000000003000 T beta\n"
                "0000000000001000 T alpha\n"
                "0000000000002000 T alpha\n",
                encoding="utf-8",
            )

            symbols = v2207.parse_system_map(path)
            index = v2207.build_symbol_index(symbols)
            addresses = [symbol.address for symbol in symbols]
            nearest = v2207.nearest_symbol(symbols, addresses, 0x2100)

        self.assertEqual([symbol.name for symbol in symbols], ["alpha", "alpha", "beta"])
        self.assertEqual(index["alpha"], 0x1000)
        self.assertEqual(nearest["symbol"], "alpha")
        self.assertEqual(nearest["offset"], 0x100)
        self.assertEqual(nearest["next_delta"], 0xF00)
        self.assertIsNone(v2207.nearest_symbol(symbols, addresses, 0x0FFF))

    def test_load_kernel_accepts_raw_and_uncompressed_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw"
            raw_path.write_bytes(b"kernel")
            wrapped = Path(tmp) / "wrapped"
            wrapped.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 6) + b"kernel")
            truncated = Path(tmp) / "truncated"
            truncated.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 10) + b"short")

            self.assertEqual(v2207.load_kernel(raw_path), b"kernel")
            self.assertEqual(v2207.load_kernel(wrapped), b"kernel")
            with self.assertRaises(ValueError):
                v2207.load_kernel(truncated)

    def test_synthetic_base_raw_offsets_and_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / "stock.json"
            meta.write_text(json.dumps({"synthetic_base": "0x1000"}), encoding="utf-8")
            raw = b"\x78\x56\x34\x12" + b"\x88\x77\x66\x55\x44\x33\x22\x11"

            self.assertEqual(v2207.load_synthetic_base(meta), 0x1000)
            self.assertIsNone(v2207.raw_offset(0x1000, 0x0FFF))
            self.assertEqual(v2207.raw_offset(0x1000, 0x1004), 4)
            self.assertEqual(v2207.read_u32(raw, 0x1000, 0x1000), 0x12345678)
            self.assertEqual(v2207.read_u64(raw, 0x1000, 0x1004), 0x1122334455667788)
            self.assertIsNone(v2207.read_u64(raw, 0x1000, 0x1008))


class InstructionHelpers(unittest.TestCase):
    def test_decode_branch_target_and_instruction_classification(self):
        self.assertEqual(v2207.decode_branch_target(0x94000001, 0x1000), 0x1004)
        self.assertEqual(v2207.decode_branch_target(0x17FFFFFF, 0x1000), 0x0FFC)

        self.assertEqual(v2207.classify_insn(None)["mnemonic"], "out-of-range")
        self.assertEqual(v2207.classify_insn(v2207.JOPP_MAGIC)["mnemonic"], "jopp_magic")
        self.assertEqual(v2207.classify_insn(v2207.ROPP_EOR_X16_X30_X17)["mnemonic"], "ropp_eor_x16_x30_x17")
        self.assertEqual(v2207.classify_insn(0xD63F0000)["mnemonic"], "blr_x0")
        self.assertEqual(v2207.classify_insn(0xD61F0000)["mnemonic"], "br_x0")
        self.assertEqual(v2207.classify_insn(0xD65F03C0)["mnemonic"], "ret")

        bl = v2207.classify_insn(0x94000001, 0x1000)
        branch = v2207.classify_insn(0x14000001, 0x1000)
        self.assertEqual(bl["mnemonic"], "bl")
        self.assertEqual(bl["target"], "0x0000000000001004")
        self.assertEqual(branch["mnemonic"], "b")
        self.assertEqual(branch["target"], "0x0000000000001004")

    def test_instruction_window_and_entry_profile_detect_magic_and_ropp(self):
        synthetic_base = 0x1000
        raw = bytearray(0x80)
        struct.pack_into("<I", raw, 0x20 - 4, v2207.JOPP_MAGIC)
        struct.pack_into("<I", raw, 0x20 + 8, v2207.ROPP_EOR_X16_X30_X17)

        window = v2207.instruction_window(bytes(raw), synthetic_base, 0x1020, before=4, after=8)
        profile = v2207.entry_profile(bytes(raw), synthetic_base, 0x1020)

        self.assertEqual([row["relative_to_target"] for row in window], [-4, 0, 4, 8])
        self.assertEqual(window[0]["mnemonic"], "jopp_magic")
        self.assertEqual(profile["jopp_magic_delta_before"], 4)
        self.assertTrue(profile["jopp_magic_before_entry"])
        self.assertEqual(profile["ropp_prologue_offsets"], [8])
        self.assertTrue(profile["ropp_prologue_present"])


class MappingAndInputParsers(unittest.TestCase):
    def test_static_mapping_reports_instruction_profiles_and_text_status(self):
        synthetic_base = 0x1000
        raw = bytearray(0x100)
        struct.pack_into("<I", raw, 0x20 - 4, v2207.JOPP_MAGIC)
        struct.pack_into("<I", raw, 0x20, 0xD65F03C0)
        symbols = [v2207.Symbol(0x1020, "T", "target")]
        addresses = [symbol.address for symbol in symbols]

        mapping = v2207.static_mapping(bytes(raw), synthetic_base, symbols, addresses, 0xFFFF000000001020, 0xFFFF000000000000)
        unmapped = v2207.static_mapping(bytes(raw), synthetic_base, symbols, addresses, 0xFFFF000000000800, 0xFFFF000000000000)

        self.assertTrue(mapping["raw_in_range"])
        self.assertEqual(mapping["instruction"]["mnemonic"], "ret")
        self.assertEqual(mapping["jopp_magic_nearby"], 4)
        self.assertEqual(mapping["symbol"], "target")
        self.assertTrue(mapping["text_symbol"])
        self.assertFalse(unmapped["raw_in_range"])
        self.assertFalse(unmapped["text_symbol"])

    def test_parse_v2206_members_skips_zero_runtime_and_uses_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.json"
            path.write_text(
                json.dumps(
                    {
                        "member_analysis": {
                            "observations": [
                                {"field": "fd0_llseek", "runtime": "0xffff000000002000"},
                                {"field": "custom", "runtime": "0x3000", "expected_symbols": ["custom_fn"]},
                                {"field": "zero", "runtime": "0x0"},
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )

            summary, rows = v2207.parse_v2206_members(path)

        self.assertIn("member_analysis", summary)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["expected_symbols"], ["null_lseek"])
        self.assertEqual(rows[1]["expected_symbols"], ["custom_fn"])

    def test_parse_required_config_inspect_rkp_and_v2197_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            autoconf = Path(tmp) / "autoconf.h"
            autoconf.write_text(
                "#define CONFIG_RKP_CFP_JOPP 1\n"
                "#define CONFIG_RKP_CFP_ROPP_SYSREGKEY 1\n"
                "#define CONFIG_OTHER 1\n",
                encoding="utf-8",
            )
            rkp = Path(tmp) / "instrument.py"
            rkp.write_text(
                "jopp_springboard_blr_x{register}\n"
                "objdump.write(magic_i, objdump.JOPP_MAGIC)\n"
                "eor RRX, x30, RRK\n"
                "stp x29, RRX\n"
                "ldp x29, RRX\n"
                "eor x30, RRX, RRK\n",
                encoding="utf-8",
            )
            symbolization = Path(tmp) / "symbolization.json"
            symbolization.write_text(
                json.dumps(
                    {
                        "top_slide_candidates": [
                            {
                                "slide": 0x1000,
                                "slide_hex": "0x1000",
                                "stack_score": 5,
                                "stack_total": 6,
                                "source": {"source_symbol": "__schedule"},
                                "timer_entry_weighted_score": 9,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            config = v2207.parse_required_config(autoconf)
            source = v2207.inspect_rkp_source(rkp)
            context = v2207.load_v2197_slide_context(symbolization)
            missing_context = v2207.load_v2197_slide_context(Path(tmp) / "absent.json")

        self.assertEqual(config, {"CONFIG_RKP_CFP_JOPP": "1", "CONFIG_RKP_CFP_ROPP_SYSREGKEY": "1"})
        self.assertTrue(source["exists"])
        self.assertTrue(source["has_jopp_blr_rewrite"])
        self.assertTrue(source["has_magic_before_function"])
        self.assertTrue(source["has_ropp_eor_stp"])
        self.assertTrue(source["has_ropp_ldp_decode"])
        self.assertEqual(context[0]["source_symbol"], "__schedule")
        self.assertEqual(missing_context, [])


class AnalyzeAndReport(unittest.TestCase):
    def write_minimal_inputs(self, root: Path) -> argparse.Namespace:
        system_map = root / "System.map"
        system_map.write_text(
            "0000000000001000 D null_fops\n"
            "0000000000002000 T null_lseek\n"
            "0000000000002100 T read_null\n"
            "0000000000003000 T msm_geni_serial_console_write\n",
            encoding="utf-8",
        )
        raw = bytearray(0x3000)
        for address in (0x2000, 0x2100):
            struct.pack_into("<I", raw, address - 0x1000 - 4, v2207.JOPP_MAGIC)
            struct.pack_into("<I", raw, address - 0x1000, v2207.ROPP_EOR_X16_X30_X17)
        struct.pack_into("<I", raw, 0x3000 - 0x1000, 0xD65F03C0)
        kernel_raw = root / "kernel.raw"
        kernel_raw.write_bytes(raw)
        stock_meta = root / "stock-kallsyms.json"
        stock_meta.write_text(json.dumps({"synthetic_base": "0x1000"}), encoding="utf-8")
        v2206_summary = root / "v2206.json"
        v2206_summary.write_text(
            json.dumps(
                {
                    "object_analysis": {
                        "best_slide": 0xFFFF000000000000,
                        "exact_slide": True,
                        "best_sources": ["fd0_fop:null_fops"],
                        "observations": [
                            {
                                "field": "fd0_fop",
                                "runtime": "0xffff000000001000",
                                "expected_symbols": ["null_fops"],
                                "candidates": [
                                    {
                                        "slide": "0xffff000000000000",
                                        "static": "0x1000",
                                    }
                                ],
                            }
                        ],
                    },
                    "member_analysis": {
                        "ranked_slides": [
                            {
                                "slide": "0xffff000000100000",
                                "slide_hex": "0xffff000000100000",
                            }
                        ],
                        "observations": [
                            {
                                "field": "fd0_llseek",
                                "runtime": "0xffff000000102000",
                                "expected_symbols": ["null_lseek"],
                            },
                            {
                                "field": "fd0_read",
                                "runtime": "0xffff000000102100",
                                "expected_symbols": ["read_null"],
                            },
                        ],
                    },
                }
            ),
            encoding="utf-8",
        )
        v2197 = root / "symbolization.json"
        v2197.write_text(
            json.dumps({"top_slide_candidates": [{"slide": 0xFFFF000000000000, "slide_hex": "0xffff000000000000"}]}),
            encoding="utf-8",
        )
        rkp = root / "instrument.py"
        rkp.write_text(
            "jopp_springboard_blr_x{register}\n"
            "objdump.write(magic_i, objdump.JOPP_MAGIC)\n"
            "eor RRX, x30, RRK\n"
            "stp x29, RRX\n"
            "ldp x29, RRX\n"
            "eor x30, RRX, RRK\n",
            encoding="utf-8",
        )
        autoconf = root / "autoconf.h"
        autoconf.write_text(
            "#define CONFIG_RKP_CFP_JOPP 1\n"
            "#define CONFIG_RKP_CFP_ROPP 1\n"
            "#define CONFIG_RKP_CFP_ROPP_SYSREGKEY 1\n"
            "#define CONFIG_RKP_CFP_JOPP_MAGIC 0x00be7bad\n",
            encoding="utf-8",
        )
        return argparse.Namespace(
            system_map=system_map,
            kernel_raw=kernel_raw,
            stock_meta=stock_meta,
            v2206_summary=v2206_summary,
            v2197_symbolization=v2197,
            rkp_instrument=rkp,
            autoconf=autoconf,
        )

    def test_analyze_classifies_runtime_patched_members_and_records_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.write_minimal_inputs(Path(tmp))
            result = v2207.analyze(args)

        self.assertEqual(result["decision"], "v2207-member-targets-runtime-patched-not-direct-symbol-slide")
        self.assertTrue(result["object_layer"]["exact"])
        self.assertEqual(result["member_layer"]["object_slide_expected_hits"], 0)
        self.assertFalse(result["member_layer"]["exact_single_text_slide"])
        self.assertEqual(result["member_layer"]["single_slide_exact_hits"][0]["exact_expected_hit_count"], 2)
        self.assertTrue(result["expected_entry_profiles"]["null_lseek"]["jopp_magic_before_entry"])
        self.assertTrue(result["safety"]["host_only"])
        self.assertFalse(result["safety"]["live_device_access"])

    def test_render_table_escapes_pipes_and_markdown_includes_core_sections(self):
        table = v2207.render_table(["A", "B"], [["x|y", "z"]])
        self.assertIn("x\\|y", table)

        result = {
            "decision": "v2207-member-targets-runtime-patched-not-direct-symbol-slide",
            "reason": "blocked",
            "inputs": {"system_map": "System.map", "kernel_raw": "kernel.raw", "v2206_summary": "v2206.json"},
            "rkp_cfp": {
                "config": {
                    "CONFIG_RKP_CFP_JOPP": "1",
                    "CONFIG_RKP_CFP_ROPP": "1",
                    "CONFIG_RKP_CFP_ROPP_SYSREGKEY": "1",
                    "CONFIG_RKP_CFP_JOPP_MAGIC": "0x00be7bad",
                },
                "source": {
                    "has_jopp_blr_rewrite": True,
                    "has_magic_before_function": True,
                    "has_ropp_eor_stp": True,
                    "has_ropp_ldp_decode": True,
                },
            },
            "object_layer": {"slide_hex": "0x8179c", "sources": ["fd0"], "slots": []},
            "member_layer": {
                "object_slide_expected_hits": 0,
                "exact_single_text_slide": False,
                "single_slide_exact_hits": [{"slide_hex": "0x1", "exact_expected_hit_count": 2, "sources": ["fd0:read"]}],
                "rows": [
                    {
                        "field": "fd0_read",
                        "runtime": "0xffff",
                        "expected_symbols": ["read_null"],
                        "expected_mappings": [{"slide_to_expected_hex": "0x1", "delta_from_object_slide_hex": "-0x2"}],
                        "candidate_mappings": {
                            "object_slide": {
                                "symbol": "other",
                                "offset": 4,
                                "instruction": {"mnemonic": "ret"},
                            }
                        },
                    }
                ],
            },
            "expected_entry_profiles": {
                "read_null": {
                    "address": "0x0000000000002100",
                    "jopp_magic_before_entry": True,
                    "ropp_prologue_present": True,
                    "ropp_prologue_offsets": [0],
                }
            },
            "safety": {"host_only": True, "live_device_access": False},
        }
        report = v2207.render_markdown(result)

        self.assertIn("# Native Init V2207 JOPP Stub Mapper", report)
        self.assertIn("- Decision: `v2207-member-targets-runtime-patched-not-direct-symbol-slide`", report)
        self.assertIn("CONFIG_RKP_CFP_JOPP", report)
        self.assertIn("| `fd0_read` | `0xffff` | read_null | `0x1` | `-0x2` | `other`+4 | ret |", report)
        self.assertIn("- host_only: `true`", report)


if __name__ == "__main__":
    unittest.main()
