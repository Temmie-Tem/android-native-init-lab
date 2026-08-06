"""Static closure tests for the A90 one-shot automatic handoff capability."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
NATIVE = REPO_ROOT / "workspace/public/src/native-init"
MANIFEST = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h/manifest.toml"
)


class A90AutoHandoffSourceV1Tests(unittest.TestCase):
    def test_capability_is_disabled_by_default(self) -> None:
        config = (NATIVE / "a90_config.h").read_text(encoding="utf-8")
        self.assertIn("#define A90_AUTO_HANDOFF_BENCHMARK_V1 0", config)

    def test_durable_enable_and_latch_precede_single_dispatch_and_are_retained(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        run_at = source.index("int a90_auto_handoff_run_once(void)")
        enable_at = source.index("a90_auto_handoff_read_enable(", run_at)
        create_at = source.index("rc = a90_auto_handoff_create_latch(", run_at)
        dispatch_at = source.index("a90_server_distro_switch_root_cmd(argv, 4)", run_at)
        returned_at = source.index("state=handoff-returned-no-replay", run_at)
        self.assertLess(enable_at, create_at)
        self.assertLess(create_at, dispatch_at)
        self.assertLess(dispatch_at, returned_at)
        self.assertIn("O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW", source)
        self.assertIn("fsync(fd)", source)
        self.assertIn("a90_auto_handoff_fsync_cache_dir", source)
        returned_tail = source[returned_at:]
        self.assertNotIn("unlink(A90_AUTO_HANDOFF_LATCH_PATH)", returned_tail)

    def test_first_boot_stays_native_until_explicit_durable_arm(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        run_at = source.index("int a90_auto_handoff_run_once(void)")
        unarmed_at = source.index("state=unarmed-stay-native", run_at)
        dispatch_at = source.index("state=dispatch-once", run_at)
        self.assertLess(unarmed_at, dispatch_at)
        self.assertIn("AUTO-HANDOFF-BENCHMARK-V1-ARM", source)
        self.assertIn("armed-after-native-health", source)
        self.assertIn('"A90AUTO state=unarmed-stay-native"', source)
        self.assertIn("return 2;", source[unarmed_at:dispatch_at])

    def test_main_refuses_auto_dispatch_without_durable_cache(self) -> None:
        source = (NATIVE / "v724/90_main.inc.c").read_text(encoding="utf-8")
        cache_guard = source.index("if (a90_cache_ready) {")
        dispatch = source.index("a90_auto_handoff_run_once();")
        refused = source.index("durable /cache unavailable")
        self.assertLess(cache_guard, dispatch)
        self.assertLess(dispatch, refused)
        self.assertIn("staying native; no replay", source)

    def test_handoff_stage_markers_are_ordered(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        stages = (
            "handoff_begin",
            "source_sha_initial_done",
            "display_release_done",
            "source_sha_post_display_done",
            "loop_attached",
            "root_mounted",
            "writable_set_ready",
            "distro_init_verified",
            "display_marker_ready",
            "mount_moves_done",
            "switch_root_exec",
        )
        positions = [source.index(f'("{stage}")') for stage in stages]
        self.assertEqual(positions, sorted(positions))

    def test_manifest_binds_profile_specific_latch_and_exact_rootfs(self) -> None:
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("candidate_authority = false", manifest)
        self.assertIn("-DA90_AUTO_HANDOFF_BENCHMARK_V1=1", manifest)
        self.assertIn(
            "/mnt/sdext/a90/runtime/debian-bookworm-arm64-phase2-display-v3406-keyed-20260805-11.img",
            manifest,
        )
        self.assertIn(
            "8b4bfd99a9324c0a32e76c837e33282afa79739fa32645e3303861e8928a33fa",
            manifest,
        )
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h4.enable", manifest)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h4.done", manifest)


if __name__ == "__main__":
    unittest.main()
