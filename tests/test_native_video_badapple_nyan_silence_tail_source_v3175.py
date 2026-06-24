from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
STATUS_HUD = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
MENU_APPS = ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c"
AUDIO = ROOT / "workspace/public/src/native-init/a90_audio.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3175_badapple_nyan_silence_tail.py"
)


class NativeVideoBadappleNyanSilenceTailSourceV3175Tests(unittest.TestCase):
    def test_v3175_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3175")
        self.assertEqual(runner.INIT_VERSION, "0.11.18")
        self.assertEqual(runner.INIT_BUILD, "v3175-badapple-nyan-silence-tail")

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.18", required)
        self.assertIn(b"v3175-badapple-nyan-silence-tail", required)
        self.assertIn(b"video.status.stream_readahead=%s", required)
        self.assertIn(b"sequential-only-window-off", required)
        self.assertIn(b"video.status.stream_readahead.window_enabled=%d", required)
        self.assertIn(b"video.status.menu_av_tail_wait=audio-expected-duration", required)
        self.assertIn(b"video.stream.readahead.deadline_skips=%u", required)
        self.assertIn(b"video.stream.audio_sync.tail_wait_target=%s", required)
        self.assertIn(b"menu.demo.badapple.audio_duration_ms=232800", required)
        self.assertIn(b"menu.demo.badapple.audio_tail_pad_ms=707", required)
        self.assertIn(b"menu.demo.badapple.audio_duration_source=pcm-file-size-plus-silence-tail", required)
        self.assertIn(b"menu.demo.badapple.pcm_duration_wait=expected-duration", required)
        self.assertIn(b"menu.demo.nyan.audio_duration_ms=11000", required)
        self.assertIn(b"menu.demo.nyan.audio_tail_pad_ms=1000", required)
        self.assertIn(b"menu.demo.nyan.audio_duration_source=pcm-file-size-plus-silence-tail", required)
        self.assertIn(b"menu.demo.nyan.pcm_duration_wait=expected-duration", required)
        self.assertIn(b"audio.play.pcm_file.short_file_zero_pad_allowed=1", required)
        self.assertIn(b"audio.play.execute.pcm_file_zero_pad_tail=%d", required)
        self.assertIn(b"audio.play.execute.file_tail_zero_chunks=%d", required)
        self.assertNotIn(b"video.status.stream_readahead=sequential-window", required)
        self.assertNotIn(b"video.stream.readahead.policy=sequential-window", required)

    def test_periodic_window_readahead_is_disabled_and_guarded_if_reenabled(self) -> None:
        source = STATUS_HUD.read_text(encoding="utf-8")
        play_start = source.index("static int video_stream_play(")
        play_end = source.index("static const char *video_cache_preset_sha256", play_start)
        play = source[play_start:play_end]

        self.assertIn("#define VIDEO_STREAM_READAHEAD_WINDOW_ENABLED 0", source)
        self.assertIn("#define VIDEO_STREAM_READAHEAD_DEADLINE_GUARD_NS 25000000ULL", source)
        self.assertIn("video.status.stream_readahead=%s", source)
        self.assertIn('"sequential-only-window-off"', source)
        self.assertIn("video.stream.readahead.window_enabled=%d", play)
        self.assertIn("video.stream.readahead.deadline_guard_ns=%llu", play)
        self.assertIn("#if VIDEO_STREAM_READAHEAD_WINDOW_ENABLED", play)
        self.assertIn("deadline_ns - now_ns >= VIDEO_STREAM_READAHEAD_DEADLINE_GUARD_NS", play)
        self.assertIn("++readahead_deadline_skips;", play)
        self.assertIn("video.stream.readahead.deadline_skips=%u", play)

    def test_full_demo_tail_wait_targets_audio_expected_duration(self) -> None:
        source = STATUS_HUD.read_text(encoding="utf-8")
        play_start = source.index("static int video_stream_play(")
        play_end = source.index("static const char *video_cache_preset_sha256", play_start)
        play = source[play_start:play_end]

        self.assertIn('const char *audio_tail_wait_target = "none";', play)
        self.assertIn('audio_tail_wait_target = "video";', play)
        self.assertIn("limit_frames == manifest->frame_count", play)
        self.assertIn("audio_sync->listen_begin_ns + audio_sync->expected_duration_ns", play)
        self.assertIn('audio_tail_wait_target = "audio";', play)
        self.assertIn("video.stream.audio_sync.tail_wait_target=%s", play)

    def test_badapple_and_nyan_menu_use_silence_tail_durations(self) -> None:
        source = MENU_APPS.read_text(encoding="utf-8")
        badapple_start = source.index("case SCREEN_MENU_DEMO_BADAPPLE")
        nyan_start = source.index("case SCREEN_MENU_DEMO_NYAN")
        doom_start = source.index("case SCREEN_MENU_DEMO_DOOM")
        badapple = source[badapple_start:nyan_start]
        nyan = source[nyan_start:doom_start]

        self.assertIn('"--duration-ms", "232800"', badapple)
        self.assertIn("menu.demo.badapple.audio_duration_ms=232800", badapple)
        self.assertIn("menu.demo.badapple.audio_tail_pad_ms=707", badapple)
        self.assertIn("menu.demo.badapple.audio_duration_source=pcm-file-size-plus-silence-tail", badapple)
        self.assertIn("menu.demo.badapple.pcm_duration_wait=expected-duration", badapple)
        self.assertNotIn("audio_duration_ms=232093", badapple)
        self.assertIn('"--duration-ms", "11000"', nyan)
        self.assertIn("menu.demo.nyan.audio_duration_ms=11000", nyan)
        self.assertIn("menu.demo.nyan.audio_tail_pad_ms=1000", nyan)
        self.assertIn("menu.demo.nyan.audio_duration_source=pcm-file-size-plus-silence-tail", nyan)
        self.assertIn("menu.demo.nyan.pcm_duration_wait=expected-duration", nyan)
        self.assertNotIn("audio_duration_ms=10000", nyan)
        self.assertIn('"--present", "setcrtc"', badapple)
        self.assertIn('"--present", "setcrtc"', nyan)
        self.assertIn("menu.demo.badapple.video_late_drop=setcrtc-cadence-no-drop", badapple)
        self.assertIn("menu.demo.nyan.video_late_drop=setcrtc-cadence-no-drop", nyan)

    def test_audio_allows_short_tail_only_for_approved_demo_pcm(self) -> None:
        source = AUDIO.read_text(encoding="utf-8")
        file_open_start = source.index("static int audio_pcm_file_open_validated(")
        file_open_end = source.index("static int audio_pcm_stream_open_validated", file_open_start)
        file_open = source[file_open_start:file_open_end]
        execute_start = source.index("static int audio_play_execute_pcm(")
        execute_end = source.index("static void audio_play_print_execute_plan", execute_start)
        execute = source[execute_start:execute_end]

        self.assertIn("#define AUDIO_BADAPPLE_FULL_PCM_SILENCE_TAIL_MAX_MS 1200", source)
        self.assertIn("#define AUDIO_NYAN_PREVIEW_PCM_SILENCE_TAIL_MAX_MS 1500", source)
        self.assertIn("static int audio_pcm_file_silence_tail_max_ms", source)
        self.assertIn("audio_pcm_file_is_badapple_full_song(path)", source)
        self.assertIn("audio_pcm_file_is_nyan_preview(path)", source)
        self.assertIn("tail_max_ms <= 0", file_open)
        self.assertIn("audio.play.pcm_file.error=short-file", file_open)
        self.assertIn("audio.play.pcm_file.short_file_zero_pad_allowed=1", file_open)
        self.assertIn("audio_read_file_tail_or_silence_fd", execute)
        self.assertIn("audio.play.execute.pcm_file_zero_pad_tail=%d", execute)
        self.assertIn("audio.play.execute.file_tail_zero_chunks=%d", execute)

    def test_manifest_metadata_records_new_readahead_and_tail_policy(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('"source_baseline": "v3173-badapple-nyan-pcm-duration"', source)
        self.assertIn('"badapple_audio_duration_ms": 232800', source)
        self.assertIn('"badapple_silence_tail_pad_ms": 707', source)
        self.assertIn('"badapple_pcm_size_bytes": 44561952', source)
        self.assertIn('"nyan_audio_duration_ms": 11000', source)
        self.assertIn('"nyan_silence_tail_pad_ms": 1000', source)
        self.assertIn('"nyan_pcm_size_bytes": 1920000', source)
        self.assertIn('"short_file_zero_pad_policy": "approved-demo-pcm-only"', source)
        self.assertIn('"stream_readahead": "sequential-only-window-off"', source)
        self.assertIn('"window_readahead_default_enabled": False', source)
        self.assertIn('"window_readahead_deadline_guard_ns": 25000000', source)
        self.assertIn('"silence_tail_wait": "expected-duration-for-full-demo"', source)
        self.assertIn("periodic-stutter-check", source)
        self.assertIn("silence-tail-clean-menu-return", source)


if __name__ == "__main__":
    unittest.main()
