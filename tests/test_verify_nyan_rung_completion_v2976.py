"""Static tests for the V2976 Nyan rung completion verifier."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/verify_nyan_rung_completion_v2976.py"


class TestVerifyNyanRungCompletionV2976(unittest.TestCase):
    def setUp(self) -> None:
        self.text = SCRIPT.read_text(encoding="utf-8")

    def test_checks_both_compact_format_and_live_playback(self) -> None:
        self.assertIn('EXPECTED_FORMAT = "pal8-rle"', self.text)
        self.assertIn('MAX_COMPRESSION_RATIO_MILLI = 200', self.text)
        self.assertIn('MIN_RAW_XBGR_REDUCTION_X100 = 3000', self.text)
        self.assertIn('def audit_asset', self.text)
        self.assertIn('def audit_live', self.text)
        self.assertIn('asset_audit["pass"] and live_audit["pass"]', self.text)

    def test_rejects_weak_live_evidence(self) -> None:
        required = [
            'decision_ok',
            'rollback_selftest_fail0',
            'presented_all',
            'dropped_zero',
            'setcrtc_path',
            'pal8_pixel_format',
            'sync_pass',
            'audio_pcm_file_validated',
        ]
        for token in required:
            self.assertIn(token, self.text)

    def test_report_is_metadata_only(self) -> None:
        self.assertIn('Raw media payloads and private run logs remain under `workspace/private/` and are not committed.', self.text)
        self.assertNotIn('frames.a90vstr".read_bytes', self.text)
        self.assertNotIn('audio.s16le".read_bytes', self.text)


if __name__ == "__main__":
    unittest.main()
