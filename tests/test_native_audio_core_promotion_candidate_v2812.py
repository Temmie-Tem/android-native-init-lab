from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2812_audio_core_promotion_candidate.py"
)


class NativeAudioCorePromotionCandidateV2812Test(unittest.TestCase):
    def test_builder_rolls_audio_core_candidate_to_0100(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2812"', text)
        self.assertIn('INIT_VERSION = "0.10.0"', text)
        self.assertIn('INIT_BUILD = "v2812-audio-core-promotion-candidate"', text)
        self.assertIn("boot_linux_v2812_audio_core_promotion_candidate.img", text)
        self.assertIn("NATIVE_INIT_V2812_AUDIO_CORE_PROMOTION_CANDIDATE_SOURCE_BUILD_2026-06-19.md", text)

    def test_builder_reuses_v2807_late_manifest_core_but_does_not_claim_adoption(self) -> None:
        text = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("build_native_init_boot_v2807_audio_late_manifest_wait", text)
        self.assertIn("pending-live-validation", text)
        self.assertIn("promotion-candidate", text)
        self.assertIn("Rollback target remains `v2321-usb-clean-identity-rodata`", text)
        self.assertIn("validated_by_prior_live_run", text)


if __name__ == "__main__":
    unittest.main()
