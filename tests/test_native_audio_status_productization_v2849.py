"""Tests for V2849 audio productization status markers."""

from __future__ import annotations

from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
AUDIO_C = REPO / "workspace/public/src/native-init/a90_audio.c"
AUDIO_APP_C = REPO / "workspace/public/src/native-init/a90_app_audio.c"
AUDIO_PROFILE_H = REPO / "workspace/public/src/native-init/a90_audio_profile.h"


class NativeAudioStatusProductizationV2849Test(unittest.TestCase):
    def test_profile_header_pins_latest_productization_evidence(self) -> None:
        header = AUDIO_PROFILE_H.read_text(encoding="utf-8")

        for marker in [
            '#define AUDIO_PRODUCTIZATION_LATEST_RUN "V2852"',
            '#define AUDIO_PRODUCTIZATION_LATEST_VERSION "0.10.16"',
            '#define AUDIO_PRODUCTIZATION_LATEST_TAG "v2851-audio-changelog-productization"',
            '#define AUDIO_BOOT_CHIME_VALIDATION_RUN "V2846"',
            '#define AUDIO_STOP_EXECUTE_VALIDATION_RUN "V2848"',
            '#define AUDIO_STOP_EXECUTE_SCOPE "core-route-reset"',
            '#define AUDIO_CHANGELOG_VALIDATION_RUN "V2852"',
            '#define AUDIO_CHANGELOG_SCREENAPP_COUNT 2',
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, header)

    def test_audio_status_exports_chime_and_stop_execute_capabilities(self) -> None:
        source = AUDIO_C.read_text(encoding="utf-8")

        for marker in [
            "audio.status.productization.version=1",
            "audio.status.productization.latest_run=%s",
            "AUDIO_PRODUCTIZATION_LATEST_RUN",
            "audio.status.productization.latest_version=%s",
            "AUDIO_PRODUCTIZATION_LATEST_VERSION",
            "audio.status.productization.latest_tag=%s",
            "AUDIO_PRODUCTIZATION_LATEST_TAG",
            "audio.status.feature.chime=1",
            "audio.status.feature.boot_chime=1",
            "audio.status.feature.boot_chime.enabled=%d",
            "audio.status.feature.boot_chime.best_effort=1",
            "audio.status.feature.boot_chime.blocks_boot=0",
            "audio.status.feature.boot_chime.validation_run=%s",
            "audio.status.feature.stop_execute=1",
            "audio.status.feature.stop_execute.scope=%s",
            "audio.status.feature.stop_execute.validation_run=%s",
            "audio.status.feature.changelog=1",
            "audio.status.feature.changelog.validation_run=%s",
            "audio.status.feature.changelog.screenapp_count=%d",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_screen_status_summarizes_latest_productization(self) -> None:
        source = AUDIO_APP_C.read_text(encoding="utf-8")

        for marker in [
            "LATEST %s %s",
            "AUDIO_PRODUCTIZATION_LATEST_VERSION",
            "AUDIO_PRODUCTIZATION_LATEST_RUN",
            "CHIME BOOT %s  STOP %s  ABOUT %s",
            "AUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT ? \"ON\" : \"OFF\"",
            "AUDIO_STOP_EXECUTE_SCOPE",
            "AUDIO_CHANGELOG_VALIDATION_RUN",
            "DISPLAY ONLY - NO AUDIO WRITE",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
        self.assertNotIn("SNDRV_CTL_IOCTL_ELEM_WRITE", source)
        self.assertNotIn("audio_route_write", source)


if __name__ == "__main__":
    unittest.main()
