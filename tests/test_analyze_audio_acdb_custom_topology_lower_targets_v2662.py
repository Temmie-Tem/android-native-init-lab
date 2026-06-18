"""Tests for V2662 libacdbloader lower-target reconnaissance."""

from __future__ import annotations

import struct
import unittest

from _loader import load_revalidation

v2662 = load_revalidation("analyze_audio_acdb_custom_topology_lower_targets_v2662")


class AnalyzeCustomTopologyLowerTargetsV2662(unittest.TestCase):
    def test_parse_symbol_table_reads_values_and_version_base(self) -> None:
        text = """
          10: 0000e43d   592 FUNC    GLOBAL DEFAULT   14 acdb_loader_adsp_set_audio_cal
          11: 00000000     0 FUNC    GLOBAL DEFAULT  UND calloc@LIBC (2)
        """

        symbols = v2662.parse_symbol_table(text)

        self.assertEqual(symbols["acdb_loader_adsp_set_audio_cal"]["value_hex"], "0x0000e43d")
        self.assertEqual(symbols["calloc"]["name"], "calloc@LIBC")

    def test_elf32_sections_finds_gnu_debugdata(self) -> None:
        data = bytearray(0x300)
        data[:4] = b"\x7fELF"
        data[4] = 1
        data[5] = 1
        shoff = 0x80
        shentsize = 40
        shnum = 3
        shstrndx = 2
        struct.pack_into("<I", data, 0x20, shoff)
        struct.pack_into("<H", data, 0x2E, shentsize)
        struct.pack_into("<H", data, 0x30, shnum)
        struct.pack_into("<H", data, 0x32, shstrndx)
        names = b"\0.gnu_debugdata\0.shstrtab\0"
        data[0x200:0x200 + len(names)] = names
        # section 1 .gnu_debugdata name offset 1, offset 0x240, size 0x20
        struct.pack_into("<IIIIIIIIII", data, shoff + shentsize, 1, 1, 0, 0, 0x240, 0x20, 0, 0, 1, 0)
        # section 2 .shstrtab name offset after .gnu_debugdata\0
        struct.pack_into("<IIIIIIIIII", data, shoff + shentsize * 2, 16, 3, 0, 0, 0x200, len(names), 0, 0, 1, 0)

        sections = v2662.elf32_sections(bytes(data))

        self.assertEqual(sections[".gnu_debugdata"]["offset"], 0x240)
        self.assertEqual(sections[".gnu_debugdata"]["size"], 0x20)

    def test_render_report_states_no_direct_dlsym_when_custom_symbols_absent(self) -> None:
        summary = {
            "decision": "v2662-lower-set-exports-present-custom-symbols-hidden-host-recon",
            "ok": True,
            "lib_path": "workspace/private/libacdbloader.so",
            "lib_sha256": "0" * 64,
            "lower_set_exports_ready": True,
            "direct_custom_symbols_ready": False,
            "exported_required": {name: {"value_hex": "0x1", "size": 4} for name in v2662.EXPORTED_REQUIRED},
            "custom_topology_strings": {name: True for name in v2662.CUSTOM_SEND_NAMES + v2662.CUSTOM_LOG_STRINGS},
            "custom_topology_dynamic_symbols": {name: None for name in v2662.CUSTOM_SEND_NAMES},
            "custom_topology_debug_symbols": {name: None for name in v2662.CUSTOM_SEND_NAMES},
        }

        report = v2662.render_report(summary)

        self.assertIn("cannot simply `dlsym()`", report)
        self.assertIn("acdb_loader_adsp_set_audio_cal", report)


if __name__ == "__main__":
    unittest.main()
