import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_HUD = ROOT / "workspace/public/src/native-init/v319/30_status_hud.inc.c"
HELP = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"


class NativeVideoCacheCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.status = STATUS_HUD.read_text()
        cls.help = HELP.read_text()
        cls.dispatch = DISPATCH.read_text()

    def test_cache_root_and_status_markers_are_exposed(self):
        expected = [
            '#define VIDEO_STREAM_CACHE_ROOT "/mnt/sdext/a90/runtime/video/cache"',
            '#define VIDEO_STREAM_CACHE_DIR_PREFIX "sha256-"',
            'video.status.next_cache=video cache [status|verify|play] SHA256',
            'video.cache.version=1',
            'video.cache.stream_size_match=%d',
            'video.cache.verify.sha256_match=%d',
            'video.cache.play.requested_present=%s',
        ]
        for marker in expected:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.status)

    def test_cache_manifest_is_content_addressed_by_sha(self):
        self.assertIn('video_cache_manifest_path_for_sha', self.status)
        self.assertIn('VIDEO_STREAM_CACHE_ROOT', self.status)
        self.assertIn('VIDEO_STREAM_CACHE_DIR_PREFIX', self.status)
        self.assertIn('video_text_is_sha256(sha256)', self.status)
        self.assertIn('video_sha256_equal_fold(manifest->sha256, sha256)', self.status)
        self.assertIn('video.cache.error=manifest-sha-mismatch', self.status)

    def test_cache_status_uses_expected_stream_size_formula(self):
        self.assertIn('video_stream_expected_total_bytes', self.status)
        self.assertIn('sizeof(struct video_stream_header_v1)', self.status)
        self.assertIn('sizeof(struct video_stream_frame_record_v1)', self.status)
        self.assertIn('manifest->frame_count', self.status)
        self.assertIn('manifest->frame_bytes', self.status)

    def test_cache_play_verifies_sha_then_reuses_stream_player(self):
        verify_index = self.status.index('rc = video_cache_verify_hash(&manifest')
        play_index = self.status.index('return video_stream_play(&manifest, requested_frames, present_mode, &audio_sync);', verify_index)
        self.assertLess(verify_index, play_index)
        self.assertIn('strcmp(subcommand, "cache") == 0', self.status)
        self.assertIn('return cmd_video_cache(argv, argc);', self.status)

    def test_help_and_cmdmeta_include_cache_surface(self):
        self.assertIn('video [status|frame|anim|blitbench|stream --manifest PATH --video-only|cache [status|verify|play] SHA256]', self.help)
        self.assertIn('video [status|frame|anim|blitbench|flipprobe|stream|cache]', self.help)
        self.assertIn('|cache [status|verify|play] SHA256]', self.dispatch)


if __name__ == "__main__":
    unittest.main()
