"""Tests for V2579 ACDB direct-GET layout extraction helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2579 = load_revalidation("native_audio_acdb_direct_get_layout_extractor_v2579")


class NativeAudioAcdbDirectGetLayoutExtractorV2579(unittest.TestCase):
    def test_command_value_addends(self) -> None:
        self.assertEqual(v2579.command_value(0x13091, 466), "0x13263")
        self.assertEqual(v2579.command_value(0x13091, 468), "0x13265")
        self.assertEqual(v2579.command_value(0x13091, 474), "0x1326b")
        self.assertEqual(v2579.command_value(0x11399), "0x11399")

    def test_pattern_hits_and_validation(self) -> None:
        text = """
 e752: e8 69                         ldr r0, [r5, #28]
 e754: 25 28                         cmp r0, #37
 e758: 01 28                         cmp r0, #1
 e75c: 00 28                         cmp r0, #0
 e786: 29 6a                         ldr r1, [r5, #32]
 e794: aa 6a                         ldrne r2, [r5, #40]
 e788: 43 f2 91 00                   movw r0, #12433
 e81c: 41 f2 99 30                   movw r0, #5017
 e872: 00 f5 e9 70                   add.w r0, r0, #466
 e7a0: 00 f5 ea 70                   add.w r0, r0, #468
 e8c6: 00 f5 ed 70                   add.w r0, r0, #474
 e7b6: 00 91                         str r0, [sp]
"""
        hits = v2579.pattern_hits(text, v2579.REQUIRED_STORE_PATTERNS)
        validation = v2579.validate_required_hits(hits)

        self.assertTrue(validation["ok"], validation)
        self.assertEqual(validation["missing"], [])
        self.assertEqual(hits["selector_offset_28"][0]["line"], 2)

    def test_render_report_selects_build_only_next_unit(self) -> None:
        manifest = {
            "decision": "v2579-direct-get-layout-host-extracted",
            "manifest_path": "workspace/private/runs/audio/v2579/layout.json",
            "inputs": {"libacdbloader": {"sha256": "a" * 64}},
            "validation": {
                "store_get_audio_cal": {"ok": True, "missing": []},
                "adsp_get_audio_cal": {"ok": True, "missing": []},
                "computed_command_checks": {
                    "0x13091_plus_466": "0x13263",
                    "0x13091_plus_468": "0x13265",
                    "0x13091_plus_474": "0x1326b",
                    "0x11399": "0x11399",
                },
            },
        }

        report = v2579.render_report(manifest)

        self.assertIn("Host-only static extraction", report)
        self.assertIn("V2580 should be build-only", report)
        self.assertIn("no `AUDIO_SET_CALIBRATION`", report)
        self.assertNotIn("/data/local/tmp", report)

    def test_missing_dump_returns_error(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2579-missing-"))
        args = v2579.parse_args(["--v2578-dump-dir", str(root)])

        with self.assertRaises(FileNotFoundError):
            v2579.build_manifest(args)


if __name__ == "__main__":
    unittest.main()
