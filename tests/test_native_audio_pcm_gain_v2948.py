from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "workspace/public/src/native-init/a90_audio.c"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2948_badapple_pcm_gain.py"


class TestNativeAudioPcmGainV2948(unittest.TestCase):
    def test_pcm_gain_is_attenuation_only(self) -> None:
        text = AUDIO.read_text(encoding="utf-8")
        self.assertIn("#define AUDIO_PCM_GAIN_MILLI_DEFAULT 1000", text)
        self.assertIn("#define AUDIO_PCM_GAIN_MILLI_MAX 1000", text)
        self.assertIn("static void audio_pcm_apply_gain", text)
        self.assertIn("pcm_gain_milli >= AUDIO_PCM_GAIN_MILLI_DEFAULT", text)
        self.assertIn("audio.play.refused=pcm-gain-out-of-range", text)
        self.assertNotIn("AUDIO_PCM_GAIN_MILLI_MAX 2000", text)

    def test_pcm_file_peak_validation_uses_scaled_peak(self) -> None:
        text = AUDIO.read_text(encoding="utf-8")
        self.assertIn("audio.play.pcm_file.pcm_gain_milli=%d", text)
        self.assertIn("audio.play.pcm_file.scaled_peak_abs=%d", text)
        self.assertIn("scaled_peak_abs <= peak_limit", text)
        self.assertIn("if (scaled_peak_abs > peak_limit)", text)

    def test_audio_play_exposes_pcm_gain_cli_and_status(self) -> None:
        text = AUDIO.read_text(encoding="utf-8")
        self.assertIn("--pcm-gain-milli", text)
        self.assertIn("audio.play.pcm_gain_milli=%d", text)
        self.assertIn("audio.play.pcm_gain.attenuation_only=1", text)
        self.assertIn("audio.play.execute.plan.pcm_gain_milli=%d", text)
        self.assertIn("audio.play.execute.pcm_gain_milli=%d", text)
        self.assertIn("audio.play.worker.pcm_gain_milli=%d", text)

    def test_v2948_builder_requires_pcm_gain_markers(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2948"', text)
        self.assertIn('INIT_VERSION = "0.10.50"', text)
        self.assertIn('INIT_BUILD = "v2948-badapple-pcm-gain"', text)
        self.assertIn('boot_linux_v2948_badapple_pcm_gain.img', text)
        self.assertIn('"recommended_pcm_gain_milli": 840', text)
        self.assertIn('pending-v2949', text)
        self.assertIn('audio.play.pcm_file.scaled_peak_abs=%d', text)


if __name__ == "__main__":
    unittest.main()
