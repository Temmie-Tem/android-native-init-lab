"""Tests for the V2843 bundled SET-cal boot-image builder."""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

v2843 = importlib.import_module("build_native_init_boot_v2843_audio_bundled_setcal")


class BuildNativeInitBootV2843AudioBundledSetcalTest(unittest.TestCase):
    def test_source_allows_bundled_prefix_and_default_manifest_override(self) -> None:
        audio = (REPO / "workspace/public/src/native-init/a90_audio.c").read_text(encoding="utf-8")
        stage = (REPO / "workspace/public/src/native-init/a90_audio_stage.h").read_text(encoding="utf-8")

        self.assertIn('#define AUDIO_SETCAL_BUNDLED_PREFIX "/a90/audio"', audio)
        self.assertIn("audio_setcal_path_has_prefix(path, AUDIO_SETCAL_BUNDLED_PREFIX)", audio)
        self.assertIn("#ifndef AUDIO_SETCAL_DEFAULT_MANIFEST_PATH", stage)
        self.assertIn('/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest', stage)

    def test_builder_targets_fresh_bundled_candidate(self) -> None:
        self.assertEqual(v2843.CYCLE, "V2843")
        self.assertEqual(v2843.INIT_VERSION, "0.10.12")
        self.assertEqual(v2843.INIT_BUILD, "v2843-audio-bundled-setcal")
        self.assertIn("boot_linux_v2843_audio_bundled_setcal.img", str(v2843.BOOT_IMAGE))
        self.assertEqual(v2843.BUNDLED_PREFIX, "/a90/audio")
        self.assertEqual(
            v2843.BUNDLED_REMOTE_MANIFEST,
            "/a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest",
        )

    def test_remote_remap_moves_only_legacy_cache_paths(self) -> None:
        self.assertEqual(
            v2843.remap_remote_path("/cache/a90-acdb-setcal-replay-v2725/00-arg.bin"),
            "/a90/audio/setcal/internal-speaker-safe/00-arg.bin",
        )
        self.assertEqual(v2843.remap_remote_path("/vendor/keep"), "/vendor/keep")

    def test_bundled_relative_path_rejects_non_bundled_paths(self) -> None:
        self.assertEqual(
            v2843.bundled_relative_path("/a90/audio/setcal/internal-speaker-safe/a.bin"),
            "a90/audio/setcal/internal-speaker-safe/a.bin",
        )
        with self.assertRaises(ValueError):
            v2843.bundled_relative_path("/cache/a.bin")

    def test_report_names_private_payload_boundary(self) -> None:
        report = v2843.render_report(
            {
                "decision": "v2843-test",
                "boot_image": "workspace/private/inputs/boot_images/test.img",
                "boot_sha256": "d" * 64,
                "init_version": "0.10.12",
                "init_build": "v2843-audio-bundled-setcal",
                "audio_bundled_setcal": {
                    "artifact_count": 15,
                    "replay_entry_count": 11,
                    "native_manifest_sha256": "e" * 64,
                },
            },
            ("helper",),
            ("flag",),
        )

        self.assertIn("Bundled SET-cal", report)
        self.assertIn("/a90/audio", report)
        self.assertIn("Raw SET-cal bytes remain private", report)
        self.assertIn("without host artifact deployment", report)


if __name__ == "__main__":
    unittest.main()
