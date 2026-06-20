from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "workspace/public/src/native-init/a90_audio.c"
PROFILE = ROOT / "workspace/public/src/native-init/a90_audio_profile.c"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_native_init_boot_v2945_badapple_fullsong_pcm64.py"


class TestNativeAudioBadAppleFullsongPcm64V2945(unittest.TestCase):
    def test_profile_default_duration_cap_stays_short(self) -> None:
        text = PROFILE.read_text(encoding="utf-8")
        self.assertIn(".duration_cap_ms = 10000", text)
        self.assertIn(".amplitude_cap_milli = 200", text)

    def test_only_badapple_fullsong_paths_get_long_duration_policy(self) -> None:
        text = AUDIO.read_text(encoding="utf-8")
        self.assertIn('#define AUDIO_BADAPPLE_FULL_PCM_PATH "/cache/a90-runtime/pkg/av/v2903/audio/audio.s16le"', text)
        self.assertIn('#define AUDIO_BADAPPLE_LEGACY_FULL_PCM_PATH "/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le"', text)
        self.assertIn("#define AUDIO_BADAPPLE_FULL_PCM_DURATION_CAP_MS 240000", text)
        self.assertIn("static bool audio_pcm_file_is_badapple_full_song", text)
        self.assertIn("static int audio_play_effective_duration_cap_ms", text)
        self.assertIn("return AUDIO_BADAPPLE_FULL_PCM_DURATION_CAP_MS;", text)
        self.assertIn('return "badapple-fullsong-pcm";', text)
        self.assertIn("return profile->duration_cap_ms;", text)

    def test_audio_play_uses_effective_duration_cap_for_safety_gate(self) -> None:
        text = AUDIO.read_text(encoding="utf-8")
        self.assertIn("audio.play.cap.effective_duration_ms=%d", text)
        self.assertIn("audio.play.cap.duration_policy=%s", text)
        self.assertIn("audio.play.cap.badapple_fullsong_ms=%d", text)
        self.assertRegex(
            text,
            re.compile(r"duration_ms <= effective_duration_cap_ms \? 1 : 0", re.MULTILINE),
        )
        self.assertIn("duration_ms > effective_duration_cap_ms", text)
        self.assertNotIn("duration_ms > profile->duration_cap_ms ||", text)

    def test_fullsong_frame_geometry_uses_64_bit_arithmetic(self) -> None:
        text = AUDIO.read_text(encoding="utf-8")
        self.assertIn(
            "total_frames = ((long long)profile->sample_rate * (long long)duration_ms) / 1000LL;",
            text,
        )
        self.assertIn("audio.play.execute.total_frames=%lld", text)
        self.assertIn("audio.play.worker.total_frames=%lld", text)
        self.assertNotIn("total_frames = (profile->sample_rate * duration_ms) / 1000;", text)

    def test_v2945_builder_requires_fullsong_pcm64_markers(self) -> None:
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('CYCLE = "V2945"', text)
        self.assertIn('INIT_VERSION = "0.10.49"', text)
        self.assertIn('INIT_BUILD = "v2945-badapple-fullsong-pcm64"', text)
        self.assertIn('boot_linux_v2945_badapple_fullsong_pcm64.img', text)
        self.assertIn('audio.play.cap.effective_duration_ms=%d', text)
        self.assertIn('badapple-fullsong-pcm', text)
        self.assertIn('recommended_duration_ms', text)
        self.assertIn('pending-v2946', text)


if __name__ == "__main__":
    unittest.main()
