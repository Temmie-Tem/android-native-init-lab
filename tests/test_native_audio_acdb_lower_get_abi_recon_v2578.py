"""Tests for V2578 ACDB lower-get ABI recon helpers."""

from __future__ import annotations

import unittest

from _loader import load_revalidation

v2578 = load_revalidation("native_audio_acdb_lower_get_abi_recon_v2578")


class NativeAudioAcdbLowerGetAbiReconV2578(unittest.TestCase):
    def test_parse_readelf_symbols_extracts_target_exports(self) -> None:
        text = """
   107: 0000e26d   104 FUNC    GLOBAL DEFAULT   14 acdb_loader_get_calibration
   115: 00009d31   876 FUNC    GLOBAL DEFAULT   14 acdb_loader_send_audio_cal_v5
   999: 00000000     0 NOTYPE  GLOBAL DEFAULT  UND ignored_symbol
"""
        symbols = v2578.parse_readelf_symbols(text, ["acdb_loader_get_calibration", "acdb_loader_send_audio_cal_v5"])

        self.assertEqual(symbols["acdb_loader_get_calibration"]["value_hex"], "0x0000e26d")
        self.assertEqual(symbols["acdb_loader_get_calibration"]["size"], 104)
        self.assertEqual(symbols["acdb_loader_send_audio_cal_v5"]["type"], "FUNC")

    def test_extract_matching_lines_returns_context(self) -> None:
        text = "\n".join([
            "0: push {r4, lr}",
            "1: movs r0, #39",
            "2: bl #28626",
            "3: movs r0, #0",
        ])

        snippets = v2578.extract_matching_lines(text, [r"movs\s+r0,\s*#39"], context=1)

        self.assertEqual(snippets[0]["line"], 2)
        context = snippets[0]["context"]
        self.assertIn("push", context[0]["text"])
        self.assertIn("bl", context[-1]["text"])

    def test_render_report_is_host_only_and_rejects_live_rerun(self) -> None:
        manifest = {
            "decision": "v2578-lower-get-abi-host-recon-complete",
            "manifest_path": "workspace/private/runs/audio/v2578/meta.json",
            "inputs": {
                "libacdbloader": {"sha256": "a" * 64},
                "libaudcal": {"sha256": "b" * 64},
            },
            "symbols": {
                "acdb_loader_send_common_custom_topology": {"value_hex": "0x8cf1", "size": 2620, "type": "FUNC"},
                "acdb_loader_send_audio_cal_v5": {"value_hex": "0x9d31", "size": 876, "type": "FUNC"},
                "acdb_loader_get_calibration": {"value_hex": "0x0000e26d", "size": 104, "type": "FUNC"},
                "acdb_loader_adsp_get_audio_cal": {"value_hex": "0xe8f5", "size": 352, "type": "FUNC"},
                "acdb_loader_get_audio_cal_v2": {"value_hex": "0xea55", "size": 136, "type": "FUNC"},
                "acdb_loader_store_get_audio_cal": {"value_hex": "0xe715", "size": 480, "type": "FUNC"},
            },
            "disassembly": {},
        }

        report = v2578.render_report(manifest)

        self.assertIn("Host-only ABI reconnaissance", report)
        self.assertIn("Do not rerun the V2572/V2577", report)
        self.assertIn("requested length\n  alone is not success", report)
        self.assertNotIn("/data/local/tmp", report)


if __name__ == "__main__":
    unittest.main()
