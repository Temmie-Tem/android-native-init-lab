"""Tests for V2941 Bad Apple Player HUD BEAT FLASH wiring."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUD = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
TABLE = ROOT / "workspace/public/src/native-init/v319/a90_badapple_beat_table.h"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2941_badapple_beat_flash.py"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestNativeVideoBadAppleBeatFlashV2941(unittest.TestCase):
    def test_generated_table_is_sorted_and_has_real_source_metadata(self) -> None:
        text = _text(TABLE)
        array_body = text.split("static const uint32_t A90_BADAPPLE_BEAT_MS[] = {", 1)[1].split("};", 1)[0]
        values = [int(value) for value in re.findall(r"(\d+)U", array_body)]
        self.assertGreaterEqual(len(values), 300)
        self.assertEqual(values, sorted(values))
        self.assertGreater(values[0], 0)
        self.assertGreater(values[-1], 180_000)
        self.assertIn('A90_BADAPPLE_BEAT_SOURCE_ID "badapple-v2903-energy-onsets-v2941"', text)
        self.assertIn('A90_BADAPPLE_BEAT_WINDOW_MS 70U', text)
        self.assertIn('b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75', text)

    def test_player_hud_uses_audio_clock_onset_table_not_pending_placeholder(self) -> None:
        text = _text(HUD)
        self.assertIn('#include "a90_badapple_beat_table.h"', text)
        self.assertIn("video_badapple_beat_flash_active(audio_ms", text)
        self.assertIn("border_color = beat_flash_active ? 0xFFFFFF : lamp_color", text)
        self.assertIn("BEAT FLASH %s  audio-clock onsets=%u nearest=%ums", text)
        self.assertNotIn("host onset table pending", text)

    def test_stream_reports_beat_flash_telemetry(self) -> None:
        text = _text(HUD)
        for marker in (
            "video.stream.beat_flash.enabled=1",
            "video.stream.beat_flash.source=%s",
            "video.stream.beat_flash.audio_sha256=%s",
            "video.stream.beat_flash.table_count=%u",
            "video.stream.beat_flash.active_frames=%u",
        ):
            self.assertIn(marker, text)

    def test_v2941_builder_requires_beat_flash_markers(self) -> None:
        text = _text(BUILDER)
        self.assertIn('INIT_VERSION = "0.10.47"', text)
        self.assertIn('INIT_BUILD = "v2941-badapple-beat-flash"', text)
        self.assertIn('BEAT FLASH %s  audio-clock onsets=%u nearest=%ums', text)
        self.assertIn('badapple-v2903-energy-onsets-v2941', text)
        self.assertIn('video.stream.beat_flash.active_frames=%u', text)
        self.assertIn('pending-v2942', text)


if __name__ == "__main__":
    unittest.main()
