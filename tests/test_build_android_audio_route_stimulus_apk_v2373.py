"""Host-only tests for the V2373 APK-style Android AudioTrack stimulus builder."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation


v2373 = load_revalidation("build_android_audio_route_stimulus_apk_v2373")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "dry_run": True,
        "android_sdk": None,
        "java_home": None,
        "javac": None,
        "keystore": None,
        "out_dir": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AndroidAudioRouteStimulusApkBuilder(unittest.TestCase):
    def test_dry_run_reports_missing_tools_without_building(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(v2373.shutil, "which", return_value=None):
            empty_sdk = Path(temp_dir) / "sdk"
            result = v2373.build(args(dry_run=True, android_sdk=empty_sdk, java_home=Path(temp_dir) / "jdk"))

        self.assertFalse(result["built"])
        self.assertIn("android_jar", result["missing"])
        self.assertIn("aapt", result["missing"])
        self.assertIn("apksigner", result["missing"])

    def test_can_build_state_when_required_tools_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sdk = root / "sdk"
            java_home = root / "jdk"
            for path in (
                java_home / "bin/javac",
                java_home / "bin/java",
                java_home / "bin/keytool",
                sdk / "platforms/android-31/android.jar",
                sdk / "build-tools/35.0.0/aapt",
                sdk / "build-tools/35.0.0/d8",
                sdk / "build-tools/35.0.0/zipalign",
                sdk / "build-tools/35.0.0/apksigner",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("tool")
            state = v2373.discover_state(args(android_sdk=sdk, java_home=java_home))

        self.assertTrue(state["manifest_exists"])
        self.assertGreater(state["java_source_count"], 0)
        self.assertTrue(state["can_build"])
        self.assertEqual(state["android_sdk"], str(sdk))

    def test_manifest_source_and_builder_keep_native_audio_paths_out(self) -> None:
        manifest = v2373.MANIFEST.read_text()
        sources = "\n".join(path.read_text() for path in sorted(v2373.JAVA_SRC_ROOT.glob("**/*.java")))
        builder = Path(v2373.__file__).read_text()

        self.assertIn('package="com.a90.nativeinit.audio"', manifest)
        self.assertIn('android:minSdkVersion="23"', manifest)
        self.assertIn('android:targetSdkVersion="31"', manifest)
        self.assertIn('android:exported="true"', manifest)
        self.assertIn("PLAY_ROUTE_STIMULUS", manifest)
        self.assertIn("AudioTrack", sources)
        self.assertIn("setSpeakerphoneOn", sources)
        self.assertIn("A90_AUDIO_STIMULUS_BEGIN", sources)
        for text in (manifest, sources, builder):
            self.assertNotIn("/dev/snd", text)
            self.assertNotIn("tinyplay", text)
            self.assertNotIn("tinymix set", text)


if __name__ == "__main__":
    unittest.main()
