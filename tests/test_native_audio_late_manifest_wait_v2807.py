from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIO_C = ROOT / "workspace/public/src/native-init/a90_audio.c"
BUILD_SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2807_audio_late_manifest_wait.py"


class NativeAudioLateManifestWaitV2807Test(unittest.TestCase):
    def test_worker_waits_for_manifest_before_setcal_verify(self) -> None:
        text = AUDIO_C.read_text(encoding="utf-8")
        self.assertIn("AUDIO_PLAY_MANIFEST_WAIT_TIMEOUT_MS 90000", text)
        self.assertIn("audio_wait_for_manifest_ready", text)
        self.assertIn("audio.play.worker.manifest_wait_started=1", text)
        self.assertIn("audio.play.worker.manifest_ready=1", text)
        self.assertIn("manifest_wait,setcal_hold", text)
        self.assertLess(
            text.index("audio_wait_for_manifest_ready(manifest_path)"),
            text.index("audio_setcal_verify_manifest(profile, manifest_path"),
        )

    def test_builder_uses_v2807_identity_and_default_manifest_contract(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2807"', text)
        self.assertIn('INIT_VERSION = "0.9.315"', text)
        self.assertIn('INIT_BUILD = "v2807-audio-late-manifest-wait"', text)
        self.assertIn('NATIVE_INIT_V2807_AUDIO_LATE_MANIFEST_WAIT_SOURCE_BUILD_2026-06-19.md', text)
        self.assertIn('"manifest_wait"', text)
        self.assertIn('/cache/a90-runtime/pkg/manifests/audio-setcal-internal-speaker-safe.manifest', text)


if __name__ == "__main__":
    unittest.main()
