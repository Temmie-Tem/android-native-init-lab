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
            'video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache]',
            'video cache preset [badapple|badapple-scale] play [--trust-cache]',
            'video.status.next_demo=video demo [badapple|badapple-scale] [status|verify|play] [--trust-cache]',
            'video.cache.version=1',
            'video.cache.stream_size_match=%d',
            'video.cache.verify.sha256_match=%d',
            'video.cache.play.trust_cache=1',
            'video.cache.play.trust_cache=0',
            'video.cache.play.requested_present=%s',
            'video.cache.play.requested_layout=%s',
            'video.cache.preset=%s',
            'video.cache.preset.asset_id=%s',
            'video.cache.preset.sha256=%s',
            'video.demo.storage=sd-sha-cache',
            'video.demo.boot_asset_policy=boot-image-carries-player-not-frames',
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

    def test_cache_play_default_verifies_sha_then_reuses_stream_player(self):
        verify_index = self.status.index('rc = video_cache_verify_hash(&manifest')
        trust_zero_index = self.status.index('video.cache.play.trust_cache=0', verify_index)
        play_index = self.status.index('return video_stream_play(&manifest, requested_frames, present_mode, layout, &audio_sync);', trust_zero_index)
        self.assertLess(verify_index, play_index)
        self.assertIn('strcmp(subcommand, "cache") == 0', self.status)
        self.assertIn('return cmd_video_cache(argv, argc);', self.status)

    def test_cache_play_trust_cache_is_explicit_and_skips_full_sha(self):
        self.assertIn('strcmp(argv[index], "--trust-cache") == 0', self.status)
        trust_index = self.status.index('video.cache.play.trust_cache=1')
        else_index = self.status.index('} else {', trust_index)
        trusted_block = self.status[trust_index:else_index]
        self.assertIn('video.cache.play.trust_cache=1', trusted_block)
        self.assertIn('video.cache.verify.actual_sha256=trust-cache-not-checked', trusted_block)
        self.assertIn('video.cache.verify.sha256_checked=0', trusted_block)
        self.assertIn('video.cache.verify.sha256_match=0', trusted_block)
        self.assertNotIn('video_cache_verify_hash(&manifest', trusted_block)

    def test_cache_play_trust_cache_still_requires_ready_stream(self):
        stat_index = self.status.index('rc = video_cache_stat_stream(&manifest, &stream_exists, &stream_size, &stream_size_match);')
        trust_index = self.status.index('if (trust_cache) {', stat_index)
        ready_block = self.status[stat_index:trust_index]
        self.assertIn('video.cache.play.error=stream-not-ready', ready_block)
        self.assertIn('!stream_exists || !stream_size_match', ready_block)
        self.assertIn('return -EINVAL;', ready_block)

    def test_badapple_scale_preset_maps_to_sd_cache_sha(self):
        expected_sha = '878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890'
        self.assertIn('#define VIDEO_CACHE_PRESET_BADAPPLE_SCALE_NAME "badapple-scale"', self.status)
        self.assertIn('#define VIDEO_CACHE_PRESET_BADAPPLE_SCALE_ASSET_ID "v2874-synthetic-mono1-checker-6501f"', self.status)
        self.assertIn(f'#define VIDEO_CACHE_PRESET_BADAPPLE_SCALE_SHA256 "{expected_sha}"', self.status)
        self.assertIn('video_cache_preset_sha256', self.status)
        self.assertIn('preset_sha256 = video_cache_preset_sha256(preset_name);', self.status)
        self.assertIn('sha256 = preset_sha256;', self.status)

    def test_badapple_real_preset_uses_player_hud_layout(self):
        expected_sha = '9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0'
        self.assertIn('#define VIDEO_CACHE_PRESET_BADAPPLE_NAME "badapple"', self.status)
        self.assertIn('#define VIDEO_CACHE_PRESET_BADAPPLE_ASSET_ID "badapple-480x360-full-v2903"', self.status)
        self.assertIn(f'#define VIDEO_CACHE_PRESET_BADAPPLE_SHA256 "{expected_sha}"', self.status)
        self.assertIn('VIDEO_STREAM_LAYOUT_PLAYER_HUD', self.status)
        self.assertIn('video_cache_preset_default_layout', self.status)
        self.assertIn('return VIDEO_STREAM_LAYOUT_PLAYER_HUD;', self.status)
        self.assertIn('video_render_player_hud', self.status)
        self.assertIn('--layout full|player-hud', self.status)

    def test_unknown_preset_is_rejected_before_cache_lookup(self):
        preset_branch = self.status[self.status.index('if (strcmp(argv[2], "preset") == 0) {'):self.status.index('} else {', self.status.index('if (strcmp(argv[2], "preset") == 0) {'))]
        self.assertIn('video.cache.preset.error=unknown', preset_branch)
        self.assertIn('return -EINVAL;', preset_branch)

    def test_demo_badapple_scale_wraps_cache_preset(self):
        self.assertIn('static int cmd_video_demo', self.status)
        demo_block = self.status[self.status.index('static int cmd_video_demo'):self.status.index('static int cmd_video_stream')]
        self.assertIn('strcmp(argv[2], VIDEO_CACHE_PRESET_BADAPPLE_NAME) == 0', demo_block)
        self.assertIn('strcmp(argv[2], VIDEO_CACHE_PRESET_BADAPPLE_SCALE_NAME) == 0', demo_block)
        self.assertIn('cache_argv[cache_argc++] = "cache";', demo_block)
        self.assertIn('cache_argv[cache_argc++] = "preset";', demo_block)
        self.assertIn('cache_argv[cache_argc++] = argc >= 4 ? argv[3] : "status";', demo_block)
        self.assertIn('return cmd_video_cache(cache_argv, cache_argc);', demo_block)
        self.assertIn('return cmd_video_frame(argv, argc);', demo_block)

    def test_help_and_cmdmeta_include_cache_surface(self):
        self.assertIn('video [status|frame|demo badapple|anim|blitbench|stream --manifest PATH --video-only|cache [status|verify|play] SHA256 [--trust-cache] [--layout full|player-hud]|cache preset [badapple|badapple-scale] [status|verify|play]]', self.help)
        self.assertIn('video [status|frame|demo|anim|blitbench|flipprobe|stream|cache]', self.help)
        self.assertIn('demo [badapple|badapple-scale|frame-pattern]', self.dispatch)
        self.assertIn('|cache [status|verify|play] SHA256 [--trust-cache] [--layout full|player-hud]|cache preset [badapple|badapple-scale] [status|verify|play]]', self.dispatch)


if __name__ == "__main__":
    unittest.main()
