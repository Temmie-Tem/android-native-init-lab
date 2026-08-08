"""Static closure tests for the A90 one-shot automatic handoff capability."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
NATIVE = REPO_ROOT / "workspace/public/src/native-init"
# The current generation, not a historical one. Pinned to phase3-minimal-h
# this test kept asserting H4's image, hash and latch, so the focused suite
# could pass without ever validating the generation actually being built.
MANIFEST = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder"
    / "versions/phase3-minimal-h7/manifest.toml"
)


class A90AutoHandoffSourceV1Tests(unittest.TestCase):
    def test_evidence_run_fsyncs_file_and_parent_directory(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        publish = source[
            source.index("static int a90_auto_handoff_publish_evidence_run("):
            source.index("static int a90_auto_handoff_replay_ondevice_evidence(")
        ]
        self.assertIn("static int a90_auto_handoff_fsync_evidence_dir(void)", source)
        self.assertIn("O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW", source)
        self.assertIn("return a90_auto_handoff_fsync_evidence_dir();", publish)

    def test_h7_display_cleanup_and_host_budget_share_a_bounded_owner_count(self) -> None:
        native = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        orchestrator = (
            REPO_ROOT
            / "workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("#define A90_D_HANDOFF_DRM_OWNER_MAX 16U", native)
        self.assertIn("#define A90_D_HANDOFF_PROC_ENTRY_MAX 8192U", native)
        self.assertIn(
            "#define A90_D_HANDOFF_DISPLAY_TOTAL_TIMEOUT_MS 127000",
            native,
        )
        cleanup = native[
            native.index("static int d_handoff_stop_display_owners_mode("):
            native.index("static int d_handoff_stop_display_owners(")
        ]
        self.assertIn(
            "if (owner_attempts >= A90_D_HANDOFF_DRM_OWNER_MAX)",
            cleanup,
        )
        self.assertIn("owner_limit=%u attempted=%u stop=refused", cleanup)
        self.assertIn("process_limit=%u scanned=%u stop=refused", cleanup)
        self.assertIn("long display_deadline =", cleanup)
        self.assertIn("d_handoff_pid_has_drm_fd_until(", cleanup)
        self.assertIn("display_deadline", cleanup)
        self.assertIn("F1_HANDOFF_DISPLAY_OWNER_BOUND_COUNT = 16", orchestrator)
        self.assertIn(
            "F1_HANDOFF_DISPLAY_PROC_ENTRY_BOUND_COUNT = 8192",
            orchestrator,
        )
        self.assertIn("F1_HANDOFF_DISPLAY_TOTAL_BOUND_SEC = 127", orchestrator)
        self.assertIn("+ F1_HANDOFF_DISPLAY_BOUND_SEC", orchestrator)

    def test_h7_evidence_bind_is_private_without_einval_bypass(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        bind = source[
            source.index("static int d3_bind_evidence_dir("):
            source.index("static int d3_move_mount_one(")
        ]
        self.assertIn(
            "mount(A90_D3_EVIDENCE_DIR,\n"
            "              A90_D3_EVIDENCE_DIR,",
            bind,
        )
        self.assertIn(
            "mount(NULL, A90_D3_EVIDENCE_DIR, NULL, MS_PRIVATE, NULL)",
            bind,
        )
        self.assertNotIn("errno != EINVAL", bind)
        self.assertLess(bind.index("MS_PRIVATE"), bind.index("dst, NULL, MS_BIND"))
        self.assertIn("umount2(A90_D3_EVIDENCE_DIR, MNT_DETACH)", bind)

    def test_h7_hash_and_loop_attach_share_one_open_source_identity(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        handoff = source[
            source.index("int a90_server_distro_switch_root_cmd("):
            source.index("int a90_server_distro_userdata_preflight_cmd(")
        ]
        attach = source[
            source.index("static int d3_attach_loop("):
            source.index("static int d3_detach_loop(")
        ]
        self.assertIn("d3_open_source(image, &source)", handoff)
        self.assertGreaterEqual(
            handoff.count("d3_verify_source_sha_fd(&source"),
            2,
        )
        self.assertIn("d3_attach_loop(image, &source, &loop_attached)", handoff)
        self.assertIn("ioctl(loop_fd, LOOP_SET_FD, source->fd)", attach)
        self.assertIn("ioctl(loop_fd, LOOP_GET_STATUS64, &observed)", attach)
        self.assertIn("observed.lo_device != (uint64_t)source->dev", attach)
        self.assertIn("observed.lo_inode != (uint64_t)source->ino", attach)
        self.assertNotIn('"losetup"', attach)

    def test_h7_read_only_root_refuses_unmounted_dev_fallback(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        move = source[
            source.index("static int d3_move_core_mounts("):
            source.index("static void d3_restore_core_mounts(")
        ]
        self.assertIn(
            "dev_mountpoint=0 refused=read-only-root-requires-mounted-dev",
            move,
        )
        self.assertNotIn("d3_prepare_new_dev", move)
        self.assertIn("return -ENODEV;", move)

    def test_ondevice_evidence_tail_keeps_preceding_and_final_bytes(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        replay = source[
            source.index("static int a90_auto_handoff_replay_ondevice_evidence("):
            source.index("int a90_auto_handoff_run_once(void)")
        ]
        self.assertIn(
            "buffer[A90_ONDEV_EVIDENCE_TAIL_MAX + 2U]",
            replay,
        )
        self.assertIn(
            "size_t read_limit = A90_ONDEV_EVIDENCE_TAIL_MAX;",
            replay,
        )
        self.assertEqual(replay.count("read_limit += 1U;"), 1)
        self.assertIn("while (consumed < read_limit)", replay)
        self.assertIn("read_limit - consumed", replay)
        self.assertIn(
            "records[records_seen % A90_ONDEV_EVIDENCE_LINES_MAX] = marker",
            replay,
        )
        self.assertIn("unsigned first = records_seen - emitted;", replay)
        self.assertNotIn(
            "while (*cursor != '\\0' && emitted < A90_ONDEV_EVIDENCE_LINES_MAX)",
            replay,
        )

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
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260807-05.img",
            manifest,
        )
        self.assertIn(
            "b92a5437d3854b0f01e4b2acc4a241ad9c8ad8f0b17d7cc36e246d2fbb01d10a",
            manifest,
        )
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h7.enable", manifest)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h7.done", manifest)
        self.assertIn('-DINIT_VERSION="0.11.175"', manifest)

    def test_manifest_pins_the_read_only_source_and_evidence_strings(self) -> None:
        """The builder verifies pinned strings against the built init.

        So pinning them here is what makes "the mechanism is compiled in" a
        checked fact rather than an assumption about the source tree.
        """
        manifest = MANIFEST.read_text(encoding="utf-8")
        for pinned in (
            "writable_set=verified root=read-only count=%u",
            "writable_set=mounted count=%u",
            "replayed lines=%d path=%s",
            "run published intent_sha256=%s path=%s",
            "handoff_display owner_limit=%u attempted=%u stop=refused",
            "handoff_display process_limit=%u scanned=%u stop=refused",
            "evidence_bind=source-private",
            "dev_mountpoint=0 refused=read-only-root-requires-mounted-dev",
        ):
            self.assertIn(pinned, manifest)


if __name__ == "__main__":
    unittest.main()
