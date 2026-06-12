"""Regression tests for a90_kernel_v2209_fops_clone_semantic_mapper."""

import argparse
import json
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_revalidation

v2209 = load_revalidation("a90_kernel_v2209_fops_clone_semantic_mapper")


class ScalarSymbolAndRawHelpers(unittest.TestCase):
    def test_parse_int_and_hex_formatters(self):
        self.assertEqual(v2209.parse_int(7), 7)
        self.assertEqual(v2209.parse_int("42"), 42)
        self.assertEqual(v2209.parse_int("0x2a"), 42)
        self.assertEqual(v2209.hex64(-1), "0xffffffffffffffff")
        self.assertEqual(v2209.hex_signed(-0x20), "-0x20")
        self.assertEqual(v2209.hex_signed(0x20), "0x20")

    def test_parse_system_map_build_index_and_nearest_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "System.map"
            path.write_text(
                "not-hex T ignored\n"
                "0000000000003000 T beta\n"
                "0000000000001000 T alpha\n"
                "0000000000002000 W alpha\n",
                encoding="utf-8",
            )

            symbols = v2209.parse_system_map(path)
            index = v2209.build_symbol_index(symbols)
            addresses = [symbol.address for symbol in symbols]
            nearest = v2209.nearest_symbol(symbols, addresses, 0x2100)

        self.assertEqual([symbol.address for symbol in symbols], [0x1000, 0x2000, 0x3000])
        self.assertEqual(index["alpha"], 0x1000)
        self.assertEqual(nearest["symbol"], "alpha")
        self.assertEqual(nearest["kind"], "W")
        self.assertEqual(nearest["offset_hex"], "0x100")
        self.assertIsNone(v2209.nearest_symbol(symbols, addresses, 0x0FFF))

    def test_load_kernel_raw_accepts_wrapped_and_rejects_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_path = Path(tmp) / "raw"
            raw_path.write_bytes(b"kernel")
            wrapped = Path(tmp) / "wrapped"
            wrapped.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 6) + b"kernel")
            truncated = Path(tmp) / "truncated"
            truncated.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 10) + b"short")

            self.assertEqual(v2209.load_kernel_raw(raw_path), b"kernel")
            self.assertEqual(v2209.load_kernel_raw(wrapped), b"kernel")
            with self.assertRaises(ValueError):
                v2209.load_kernel_raw(truncated)

    def test_load_synthetic_base_and_kernel_va_classifier(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / "stock.json"
            meta.write_text(json.dumps({"synthetic_base": "0xffff000000000000"}), encoding="utf-8")

            self.assertEqual(v2209.load_synthetic_base(meta), 0xFFFF000000000000)
        self.assertTrue(v2209.looks_like_kernel_va(v2209.KERNEL_VA_MIN))
        self.assertTrue(v2209.looks_like_kernel_va(v2209.KERNEL_VA_MAX))
        self.assertFalse(v2209.looks_like_kernel_va(v2209.KERNEL_VA_MIN - 1))


class RelaAndSourceParsing(unittest.TestCase):
    def test_rela_record_discovery_and_read_u32_landing_profile(self):
        synthetic_base = 0xFFFF000000000000
        raw = bytearray(4 + 2 * 24 + 0x100)
        for index, addend in enumerate([v2209.KERNEL_VA_MIN + 0x1000, v2209.KERNEL_VA_MIN + 0x2000]):
            struct.pack_into(
                "<QQQ",
                raw,
                4 + index * 24,
                v2209.KERNEL_VA_MIN + 0x8000 + index * 0x10,
                v2209.RELA_INFO_RELATIVE,
                addend,
            )
        struct.pack_into("<I", raw, 0x80 - 4, v2209.JOPP_MAGIC)
        struct.pack_into("<I", raw, 0x80 + 8, v2209.ROPP_EOR_X16_X30_X17)

        self.assertTrue(v2209.is_stock_rela_record(bytes(raw), 4))
        rela_run = v2209.discover_stock_rela(bytes(raw), synthetic_base)
        self.assertEqual(rela_run["start_offset"], 4)
        self.assertEqual(rela_run["count"], 2)
        self.assertEqual(v2209.read_u32(bytes(raw), synthetic_base, synthetic_base + 0x7C), v2209.JOPP_MAGIC)
        profile = v2209.landing_profile(bytes(raw), synthetic_base, synthetic_base + 0x80)
        self.assertEqual(profile["jopp_magic_relative_offsets"], [-4])
        self.assertEqual(profile["ropp_eor_relative_offsets"], [8])

    def test_config_stripping_file_operations_offsets_and_initializers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            autoconf = root / "autoconf.h"
            autoconf.write_text("#define CONFIG_MMU 1\n", encoding="utf-8")
            fs_h = root / "fs.h"
            fs_h.write_text(
                "struct file_operations {\n"
                "    struct module *owner;\n"
                "    loff_t (*llseek)(void);\n"
                "#ifdef CONFIG_MMU\n"
                "    int (*mmap)(void);\n"
                "#else\n"
                "    int (*mmap_compat)(void);\n"
                "#endif\n"
                "    ssize_t (*read)(void);\n"
                "};\n",
                encoding="utf-8",
            )
            mem_c = root / "mem.c"
            mem_c.write_text(
                "#define redirected read_null\n"
                "static const struct file_operations null_fops = {\n"
                "    .llseek = null_lseek,\n"
                "    .read = redirected,\n"
                "};\n"
                "static const struct file_operations zero_fops = {\n"
                "    .llseek = null_lseek,\n"
                "};\n",
                encoding="utf-8",
            )

            config = v2209.parse_config_symbols(autoconf)
            stripped = v2209.strip_inactive_config_blocks(fs_h.read_text(), config)
            offsets = v2209.parse_file_operations_offsets(fs_h, config)
            macros = v2209.parse_macros(mem_c.read_text())
            initializers = v2209.parse_fops_initializers(mem_c, {"null_fops", "zero_fops"}, config)

        self.assertEqual(config, {"CONFIG_MMU"})
        self.assertIn("mmap", stripped)
        self.assertNotIn("mmap_compat", stripped)
        self.assertEqual(offsets, {"owner": 0, "llseek": 8, "mmap": 16, "read": 24})
        self.assertEqual(macros, {"redirected": "read_null"})
        self.assertEqual(v2209.resolve_alias("redirected", macros), "read_null")
        self.assertEqual(initializers["null_fops"]["read"]["source_target"], "redirected")
        self.assertEqual(initializers["null_fops"]["read"]["resolved_target"], "read_null")

    def test_parse_elf_rela_dyn_and_live_value_and_object_bases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vmlinux = root / "vmlinux"
            payload = bytearray(0x80)
            struct.pack_into("<QQq", payload, 0x40, 0x9000, v2209.RELA_INFO_RELATIVE, -1)
            vmlinux.write_bytes(payload)
            readelf = SimpleNamespace(stdout="  [ 1] .rela.dyn RELA 0000000000004000 000040 000018 18  A  0   0  8\n")

            with mock.patch.object(v2209.subprocess, "run", return_value=readelf):
                entries = v2209.parse_elf_rela_dyn(vmlinux)

        self.assertEqual(entries[0].location, 0x4000)
        self.assertEqual(entries[0].r_addend, 0xFFFFFFFFFFFFFFFF)
        self.assertEqual(v2209.live_value({"probe": {"summary": {"fd0": "0x20"}}}, "fd0"), 0x20)
        self.assertIsNone(v2209.live_value({"probe": {"summary": {"fd0": "0x0"}}}, "fd0"))
        self.assertEqual(
            v2209.object_bases_from_v2208(
                {
                    "object_rows": [
                        {"expected_symbol": "null_fops", "static_addend": "0x1000"},
                        {"expected_symbol": "zero_fops", "static_addend": "0x2000"},
                    ]
                }
            ),
            {"null_fops": 0x1000, "zero_fops": 0x2000},
        )
        with self.assertRaises(RuntimeError):
            v2209.object_bases_from_v2208({"object_rows": [{"expected_symbol": "null_fops", "static_addend": "0x1000"}]})


class AnalyzeAndReport(unittest.TestCase):
    def write_inputs(self, root: Path) -> argparse.Namespace:
        synthetic_base = v2209.KERNEL_VA_MIN
        stock_symbols = {
            "null_fops": synthetic_base + 0x1000,
            "zero_fops": synthetic_base + 0x1100,
            "null_lseek": synthetic_base + 0x2000,
            "read_null": synthetic_base + 0x2100,
            "write_null": synthetic_base + 0x2200,
        }
        clone_bases = {
            "null_fops": synthetic_base + 0x1800,
            "zero_fops": synthetic_base + 0x1900,
        }
        landing_addends = {
            ("null_fops", "llseek"): synthetic_base + 0x3000,
            ("null_fops", "read"): synthetic_base + 0x3100,
            ("zero_fops", "llseek"): synthetic_base + 0x3000,
            ("zero_fops", "write"): synthetic_base + 0x3200,
        }
        source_targets = {
            ("null_fops", "llseek"): "null_lseek",
            ("null_fops", "read"): "read_null",
            ("zero_fops", "llseek"): "null_lseek",
            ("zero_fops", "write"): "write_null",
        }
        system_map = root / "System.map"
        system_map.write_text(
            "\n".join(f"{address:016x} T {name}" for name, address in stock_symbols.items())
            + "\n"
            + "\n".join(f"{address:016x} T landing_{index}" for index, address in enumerate(sorted(set(landing_addends.values()))))
            + "\n",
            encoding="utf-8",
        )
        rebuilt_map = root / "rebuilt.System.map"
        rebuilt_base = {
            "null_fops": 0x1000,
            "zero_fops": 0x1100,
            "null_lseek": 0x2000,
            "read_null": 0x2100,
            "write_null": 0x2200,
        }
        rebuilt_map.write_text("\n".join(f"{address:016x} T {name}" for name, address in rebuilt_base.items()) + "\n", encoding="utf-8")
        autoconf = root / "autoconf.h"
        autoconf.write_text("#define CONFIG_MMU 1\n", encoding="utf-8")
        fs_h = root / "fs.h"
        fs_h.write_text(
            "struct file_operations {\n"
            "    struct module *owner;\n"
            "    loff_t (*llseek)(void);\n"
            "    ssize_t (*read)(void);\n"
            "    ssize_t (*write)(void);\n"
            "};\n",
            encoding="utf-8",
        )
        mem_c = root / "mem.c"
        mem_c.write_text(
            "static const struct file_operations null_fops = {\n"
            "    .llseek = null_lseek,\n"
            "    .read = read_null,\n"
            "};\n"
            "static const struct file_operations zero_fops = {\n"
            "    .llseek = null_lseek,\n"
            "    .write = write_null,\n"
            "};\n",
            encoding="utf-8",
        )
        slot_entries: list[tuple[int, int]] = []
        rebuilt_entries: list[tuple[int, int]] = []
        field_offsets = {"llseek": 8, "read": 16, "write": 24}
        for key, addend in landing_addends.items():
            object_name, field = key
            slot_entries.append((clone_bases[object_name] + field_offsets[field], addend))
            target = source_targets[key]
            rebuilt_entries.append((rebuilt_base[object_name] + field_offsets[field], rebuilt_base[target]))
        raw = bytearray(4 + len(slot_entries) * 24 + 0x5000)
        for index, (slot, addend) in enumerate(slot_entries):
            struct.pack_into("<QQQ", raw, 4 + index * 24, slot, v2209.RELA_INFO_RELATIVE, addend)
        for addend in landing_addends.values():
            offset = addend - synthetic_base
            struct.pack_into("<I", raw, offset - 4, v2209.JOPP_MAGIC)
            struct.pack_into("<I", raw, offset + 8, v2209.ROPP_EOR_X16_X30_X17)
        kernel_raw = root / "kernel.raw"
        kernel_raw.write_bytes(raw)
        stock_meta = root / "stock.json"
        stock_meta.write_text(json.dumps({"synthetic_base": synthetic_base}), encoding="utf-8")
        v2208_result = root / "v2208.json"
        v2208_result.write_text(
            json.dumps(
                {
                    "slide": {"best": 0x80000},
                    "object_rows": [
                        {"expected_symbol": "null_fops", "static_addend": v2209.hex64(clone_bases["null_fops"])},
                        {"expected_symbol": "zero_fops", "static_addend": v2209.hex64(clone_bases["zero_fops"])},
                    ],
                }
            ),
            encoding="utf-8",
        )
        probe_summary = {}
        for key, addend in landing_addends.items():
            field = v2209.FOPS_FIELD_TO_V2206[key]
            probe_summary[field] = v2209.hex64(addend + 0x80000)
        v2206 = root / "v2206.json"
        v2206.write_text(json.dumps({"probe": {"summary": probe_summary}}), encoding="utf-8")
        vmlinux = root / "vmlinux"
        payload = bytearray(0x200)
        for index, (slot, addend) in enumerate(rebuilt_entries):
            struct.pack_into("<QQq", payload, 0x40 + index * 24, slot, v2209.RELA_INFO_RELATIVE, addend)
        vmlinux.write_bytes(payload)
        self.readelf_stdout = f"  [ 1] .rela.dyn RELA 0000000000004000 000040 {len(rebuilt_entries) * 24:06x} 18  A  0   0  8\n"
        return argparse.Namespace(
            system_map=system_map,
            kernel_raw=kernel_raw,
            stock_meta=stock_meta,
            v2206_summary=v2206,
            v2208_result=v2208_result,
            rebuilt_vmlinux=vmlinux,
            rebuilt_system_map=rebuilt_map,
            source_mem_c=mem_c,
            source_fs_h=fs_h,
            autoconf=autoconf,
        )

    def test_analyze_builds_slot_accurate_semantic_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self.write_inputs(Path(tmp))
            with mock.patch.object(v2209.subprocess, "run", return_value=SimpleNamespace(stdout=self.readelf_stdout)):
                result = v2209.analyze(args)

        self.assertEqual(result["decision"], "v2209-fops-clone-semantic-map-built")
        self.assertTrue(result["checks"]["stock_slot_rela_present"])
        self.assertTrue(result["checks"]["rebuilt_label_matches_source"])
        self.assertTrue(result["checks"]["v2206_live_values_match_predicted_runtime"])
        self.assertEqual(result["checks"]["row_count"], 4)
        self.assertEqual(result["clone_bases"]["null_fops"], v2209.hex64(v2209.KERNEL_VA_MIN + 0x1800))
        read_row = next(row for row in result["semantic_rows"] if row["object"] == "null_fops" and row["field"] == "read")
        self.assertEqual(read_row["semantic_target"], "read_null")
        self.assertEqual(read_row["runtime_pointer"], v2209.hex64(v2209.KERNEL_VA_MIN + 0x3100 + 0x80000))
        self.assertTrue(read_row["rebuilt_matches_expected_label"])
        self.assertTrue(read_row["observed_matches_predicted"])
        shared_runtime = v2209.hex64(v2209.KERNEL_VA_MIN + 0x3000 + 0x80000)
        self.assertEqual(
            sorted(item["object"] for item in result["runtime_semantic_map"][shared_runtime]),
            ["null_fops", "zero_fops"],
        )

    def test_semantic_targets_and_markdown_rendering(self):
        runtime_map = {
            "0x2": [{"object": "zero_fops", "field": "llseek", "semantic_target": "null_lseek"}],
            "0x1": [
                {"object": "null_fops", "field": "llseek", "semantic_target": "null_lseek"},
                {"object": "zero_fops", "field": "llseek", "semantic_target": "null_lseek"},
            ],
        }
        self.assertEqual(v2209.semantic_targets_for_runtime(runtime_map)[0][0], "`0x1`")
        table = v2209.render_table(["A"], [["x|y"]])
        self.assertIn("x\\|y", table)

        result = {
            "decision": "v2209-fops-clone-semantic-map-built",
            "reason": "built",
            "inputs": {
                "v2208_result": "v2208.json",
                "kernel_raw": "kernel.raw",
                "source_mem_c": "mem.c",
                "source_fs_h": "fs.h",
                "rebuilt_vmlinux": "vmlinux",
            },
            "slide": {"runtime_rela_slide_hex": "0x80000"},
            "checks": {
                "row_count": 1,
                "stock_slot_rela_present": True,
                "rebuilt_label_matches_source": True,
                "v2206_live_values_match_predicted_runtime": True,
            },
            "runtime_semantic_map": runtime_map,
            "semantic_rows": [
                {
                    "object": "null_fops",
                    "field": "read",
                    "field_offset_hex": "0x10",
                    "semantic_target": "read_null",
                    "clone_slot": "0x1000",
                    "stock_addend": "0x2000",
                    "runtime_pointer": "0x82000",
                    "delta_from_stock_label_hex": "0x100",
                    "nearest_stock_symbol": {"symbol": "landing", "offset_hex": "0x0"},
                    "rebuilt_matches_expected_label": True,
                    "observed_matches_predicted": True,
                }
            ],
            "clone_bases": {"null_fops": "0x1000"},
            "safety": {"host_only": True, "live_device_access": False},
        }
        report = v2209.render_markdown(result)

        self.assertIn("# Native Init V2209 Fops Clone Semantic Mapper", report)
        self.assertIn("- Decision: `v2209-fops-clone-semantic-map-built`", report)
        self.assertIn("| `null_fops.read` | `0x10` | `read_null` | `0x1000` | `0x2000` | `0x82000` | `0x100` | `landing`0x0 | true | true |", report)
        self.assertIn("- host_only: `true`", report)


if __name__ == "__main__":
    unittest.main()
