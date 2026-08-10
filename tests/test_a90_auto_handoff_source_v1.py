"""Static closure tests for the A90 one-shot automatic handoff capability."""

from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from _loader import load_script


REPO_ROOT = Path(__file__).resolve().parents[1]
NATIVE = REPO_ROOT / "workspace/public/src/native-init"
# The current generation, not a historical one.
MANIFEST = (
    REPO_ROOT
    / "workspace/public/src/scripts/revalidation/a90_flat_builder"
    / "versions/phase3-minimal-h13/manifest.toml"
)
H12_MANIFEST = MANIFEST.parents[1] / "phase3-minimal-h12/manifest.toml"
H11_MANIFEST = MANIFEST.parents[1] / "phase3-minimal-h11/manifest.toml"
H10_MANIFEST = MANIFEST.parents[1] / "phase3-minimal-h10/manifest.toml"
H9_MANIFEST = MANIFEST.parents[1] / "phase3-minimal-h9/manifest.toml"
H8_MANIFEST = MANIFEST.parents[1] / "phase3-minimal-h8/manifest.toml"
FLAT_BUILDER = load_script(
    "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py"
)


class A90AutoHandoffSourceV1Tests(unittest.TestCase):
    def test_h13_build_binding_includes_receipt_while_h8_stays_v1(self) -> None:
        with MANIFEST.open("rb") as stream:
            h13 = FLAT_BUILDER.normalized_auto_handoff_binding(
                tomllib.load(stream)
            )
        with H8_MANIFEST.open("rb") as stream:
            h8 = FLAT_BUILDER.normalized_auto_handoff_binding(
                tomllib.load(stream)
            )
        self.assertEqual(h13["schema"], "a90-compiled-auto-handoff-binding-v2")
        self.assertEqual(
            h13["receipt_path"],
            "/cache/a90-source-receipt-phase3-minimal-h13",
        )
        self.assertEqual(h8["schema"], "a90-compiled-auto-handoff-binding-v1")
        self.assertNotIn("receipt_path", h8)

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

    def test_h9_fast_receipt_binds_full_source_metadata_and_is_durable(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        identity = source[
            source.index("struct d3_source_identity {"):
            source.index("static int d3_open_source(")
        ]
        verify = source[
            source.index("static int d3_verify_source_receipt_open("):
            source.index("static int d3_write_source_receipt(")
        ]
        publish_at = source.index("static int d3_write_source_receipt(")
        publish = source[
            publish_at:
            source.index("static int d3_path_is_mounted(", publish_at)
        ]
        for field in (
            "dev", "ino", "size", "mode", "uid", "gid", "nlink",
            "mtime", "ctime",
        ):
            self.assertIn(field, identity)
        self.assertIn("d3_source_fd_matches(source)", verify)
        self.assertIn("d3_source_path_matches(image, source)", verify)
        self.assertIn("memcmp(observed, expected", verify)
        self.assertIn("O_RDONLY | O_CLOEXEC | O_NOFOLLOW", verify)
        self.assertIn("O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW", publish)
        self.assertIn("fsync(fd)", publish)
        self.assertIn("rename(temporary, A90_D3_SOURCE_RECEIPT_PATH)", publish)
        self.assertIn("d3_fsync_cache_dir()", publish)

    def test_h9_arm_qualifies_once_and_boot_only_verifies_before_latch(self) -> None:
        source = (NATIVE / "a90_auto_handoff.c").read_text(encoding="utf-8")
        arm = source[
            source.index("int a90_auto_handoff_arm_cmd("):
            source.index("static int a90_auto_handoff_mkdir_evidence_dir(")
        ]
        run = source[
            source.index("int a90_auto_handoff_run_once(void)"):
            source.index("\n#else\n\nint a90_auto_handoff_status_cmd", source.index("int a90_auto_handoff_run_once(void)"))
        ]
        self.assertLess(
            arm.index("a90_server_distro_source_receipt_ensure("),
            arm.index("a90_auto_handoff_create_enable("),
        )
        self.assertLess(
            run.index("a90_server_distro_source_receipt_preflight("),
            run.index("a90_auto_handoff_create_latch("),
        )
        self.assertNotIn("a90_server_distro_source_receipt_ensure(", run)

    def test_h9_routine_handoff_skips_full_sha_but_revalidates_same_fd(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        handoff = source[
            source.index("int a90_server_distro_switch_root_cmd("):
            source.index("#define A90_D4_TAG")
        ]
        self.assertIn("source_receipt_fast = d3_source_receipt_enabled() != 0", handoff)
        self.assertIn("? d3_verify_source_receipt_open(image, expected_sha, &source)", handoff)
        self.assertIn("? d3_source_fd_matches(&source)", handoff)
        self.assertIn("d3_source_path_matches(image, &source)", handoff)
        self.assertIn('"source_receipt_initial_done"', handoff)
        self.assertIn('"source_identity_post_display_done"', handoff)

    def test_read_only_root_mounts_private_dev_tmpfs_before_node_creation(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        prepare = source[
            source.index("static int d3_prepare_new_dev("):
            source.index("static int d3_restore_mount_one(")
        ]
        move = source[
            source.index("static int d3_move_core_mounts("):
            source.index("static int d3_restore_core_mounts(")
        ]
        self.assertIn('lstat(dev_dir, &st)', prepare)
        self.assertNotIn("d3_mkdir_p(dev_dir", prepare)
        self.assertLess(
            prepare.index('mount("tmpfs", dev_dir, "tmpfs"'),
            prepare.index('d3_prepare_dev_node("dev/console"'),
        )
        self.assertIn("dev_tmpfs=mounted image_write=0", prepare)
        self.assertIn("umount2(dev_dir, MNT_DETACH)", prepare)
        self.assertIn("d3_prepare_new_dev(mounted_devpts)", move)
        self.assertNotIn("read-only-root-requires-mounted-dev", move)

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
        branch = source[source.index("int direct_dispatch_state;") :]
        cache_guard = branch.index("if (!a90_cache_ready) {")
        refused = branch.index("durable /cache unavailable")
        dispatch = branch.index("a90_auto_handoff_run_once();")
        self.assertLess(cache_guard, dispatch)
        self.assertLess(cache_guard, refused)
        self.assertLess(refused, dispatch)
        self.assertIn("staying native; no replay", source)

    def test_handoff_stage_markers_are_ordered(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        stages = (
            "handoff_begin",
            "source_receipt_initial_done",
            "display_release_done",
            "source_identity_post_display_done",
            "loop_attached",
            "root_mounted",
            "writable_set_ready",
            "distro_init_verified",
            "display_marker_ready",
            "mount_moves_done",
            "switch_root_exec",
        )
        positions = [source.index(f'"{stage}"') for stage in stages]
        self.assertEqual(positions, sorted(positions))

    def test_manifest_binds_profile_specific_latch_and_exact_rootfs(self) -> None:
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn("candidate_authority = false", manifest)
        self.assertIn("-DA90_AUTO_HANDOFF_BENCHMARK_V1=1", manifest)
        self.assertIn(
            "/mnt/sdext/a90/runtime/"
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260810-08.img",
            manifest,
        )
        self.assertIn(
            "8a87cd547cfd7cfee7ec4af7ee266fd4da0b91e508099950df50a272ab19952e",
            manifest,
        )
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h13.enable", manifest)
        self.assertIn("/cache/a90-auto-handoff-phase3-minimal-h13.done", manifest)
        self.assertIn("/cache/a90-source-receipt-phase3-minimal-h13", manifest)
        self.assertIn('-DINIT_VERSION="0.11.181"', manifest)
        self.assertIn("-DA90_AUTO_HANDOFF_DIRECT_DEBIAN_BOOT=1", manifest)
        self.assertIn("-DA90_WIFI_PERSISTENT_HANDOFF_V1=1", manifest)
        self.assertIn("-DA90_WIFI_AUTOCONNECT_PRIVATE_MOUNT_NS=1", manifest)

    def test_superseded_h12_manifest_keeps_its_original_identity(self) -> None:
        manifest = H12_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('-DINIT_VERSION="0.11.180"', manifest)
        self.assertIn(
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260810-07.img",
            manifest,
        )

    def test_superseded_h11_manifest_keeps_its_original_identity(self) -> None:
        manifest = H11_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('-DINIT_VERSION="0.11.179"', manifest)
        self.assertIn(
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260810-03.img",
            manifest,
        )
        self.assertIn(
            "9e9b11aa80e2c83f54990e9b286dcdd89535438d6f0a248fe89557c75a763931",
            manifest,
        )
        self.assertIn("/cache/a90-source-receipt-phase3-minimal-h11", manifest)
        self.assertNotIn("A90_WIFI_PERSISTENT_HANDOFF_V1", manifest)

    def test_superseded_h10_manifest_keeps_its_original_identity(self) -> None:
        manifest = H10_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('-DINIT_VERSION="0.11.178"', manifest)
        self.assertIn(
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-03.img",
            manifest,
        )
        self.assertIn(
            "38d9ce41503483996d14a18fb51275fbbe47e898ce51aee37f9f88b61295018e",
            manifest,
        )
        self.assertIn("/cache/a90-source-receipt-phase3-minimal-h10", manifest)
        self.assertNotIn("A90_AUTO_HANDOFF_DIRECT_DEBIAN_BOOT", manifest)

    def test_direct_boot_prepares_only_minimal_network_before_handoff(self) -> None:
        source = (NATIVE / "v724/90_main.inc.c").read_text(encoding="utf-8")
        marker = source.index(
            "A90DIRECT_BOOT mode=min-network-wifi hud=skipped "
            "native_aux=wifi-companion+ncm"
        )
        branch_end = source.index("        if (a90_reloaded) {", marker)
        direct = source[marker:branch_end]
        self.assertIn('a90_benchmark_emit("native_direct_handoff_ready")', direct)
        self.assertIn("a90_auto_handoff_run_once()", direct)
        self.assertNotIn("start_auto_hud", direct)
        self.assertNotIn("a90_netservice_start", direct)
        self.assertIn("a90_netservice_prepare_handoff", direct)
        self.assertIn("a90_wifi_start_boot_autoconnect_once", direct)
        self.assertNotIn("a90_audio_boot_chime_start_once", direct)
        self.assertIn("v726_start_wifi_lifecycle_modem_owner_once", direct)
        self.assertIn("v1393_run_wifi_test_boot_once", direct)
        self.assertIn("v1393_require_persistent_handoff_started", direct)
        self.assertLess(
            direct.index("v1393_require_persistent_handoff_started"),
            direct.index("a90_auto_handoff_run_once"),
        )
        self.assertNotIn("v1393_wait_persistent_handoff_ready", direct)
        self.assertIn("native_wifi_companion_async_started", direct)
        self.assertIn(
            "#if defined(A90_WIFI_LIFECYCLE_MODEM_OWNER) && "
            "!A90_WIFI_PERSISTENT_HANDOFF_V1",
            direct,
        )
        fallback = source[branch_end:source.index(
            "            v724_run_qrtr_servloc_boot_once();",
            branch_end,
        )]
        self.assertIn("v726_start_wifi_lifecycle_modem_owner_once", fallback)
        self.assertIn(
            "#if defined(A90_WIFI_LIFECYCLE_MODEM_OWNER) && "
            "!A90_WIFI_PERSISTENT_HANDOFF_V1",
            fallback,
        )
        self.assertIn("v1393_run_wifi_test_boot_once", fallback)
        self.assertIn(
            "#if A90_AUTO_HANDOFF_BENCHMARK_V1 && "
            "!A90_AUTO_HANDOFF_DIRECT_DEBIAN_BOOT",
            source,
        )

    def test_wifi_handoff_bind_exposes_only_redacted_read_only_surface(self) -> None:
        source = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        bind = source[
            source.index("static int d3_bind_wifi_handoff_dir("):
            source.index("static int d3_move_mount_one(")
        ]
        self.assertIn('#define A90_D3_WIFI_HANDOFF_DIR "/cache/a90-wifi-handoff"', source)
        self.assertNotIn('"/cache/a90-wifi"', bind)
        self.assertIn("MS_REMOUNT | MS_BIND | MS_RDONLY", bind)
        self.assertIn("MS_NOSUID | MS_NODEV | MS_NOEXEC", bind)
        self.assertIn("wifi_handoff_bind=ok", bind)

    def test_persistent_wifi_companion_is_fail_closed_and_observed(self) -> None:
        helper = (NATIVE / "helpers/a90_android_execns_probe.c").read_text(
            encoding="utf-8"
        )
        wifi = (NATIVE / "a90_wifi.c").read_text(encoding="utf-8")
        direct = (NATIVE / "v724/90_main.inc.c").read_text(encoding="utf-8")
        server = (NATIVE / "a90_server_distro.c").read_text(encoding="utf-8")
        self.assertIn('strcmp(argv[i], "--persistent-handoff")', helper)
        self.assertIn(
            "--persistent-handoff requires "
            "wifi-companion-wlan-pd-service-object-visible-trigger-start-only mode",
            helper,
        )
        self.assertIn("persistent_handoff_children_ready", helper)
        self.assertIn("persistent_handoff.reason=required-child-exited", helper)
        self.assertIn("persistent_handoff.reason=wlan0-disappeared", helper)
        self.assertIn("write_persistent_handoff_ready_output_file", helper)
        self.assertIn("persistent_handoff.reason=fast-readiness-incomplete", helper)
        self.assertIn("persistent_handoff.reason=fast-wlan0-not-ready", helper)
        self.assertIn("persistent_handoff.fast_wlan0=ready", helper)
        self.assertLess(
            helper.index("persistent_handoff.reason=fast-readiness-incomplete"),
            helper.index("usleep(8000000)"),
        )
        self.assertIn("persistent_handoff_modem_holder_ready", helper)
        self.assertIn("persistent_handoff_health_publish", helper)
        self.assertIn("a90-wifi-companion-health-v1", helper)
        self.assertIn(
            '#define A90_PERSISTENT_HANDOFF_HEALTH_DIR "/cache/a90-wifi-handoff"',
            helper,
        )
        self.assertIn(
            'A90_PERSISTENT_HANDOFF_HEALTH_DIR "/companion"',
            helper,
        )
        self.assertIn("--handoff-ready-output-path", helper)
        self.assertIn("schema=a90-execns-persistent-handoff-ready-v1", helper)
        self.assertIn("write_result_output_file(cfg->result_output_path", helper)
        self.assertIn("#if !A90_WIFI_PERSISTENT_HANDOFF_V1", direct)
        self.assertIn("unshare(CLONE_NEWNS)", wifi)
        self.assertIn("MS_REC | MS_PRIVATE", wifi)
        self.assertIn("poll(&pfd, 1, 2000)", wifi)
        self.assertIn("/cache/a90-wifi-handoff", wifi)
        self.assertIn(
            'A90_WIFI_RUNTIME_ROOT "/handoff-status.tmp"',
            wifi,
        )
        self.assertIn("wifi_reset_handoff_export", wifi)
        self.assertNotIn(
            '#define A90_WIFI_HANDOFF_ROOT "/cache/a90-wifi"',
            wifi,
        )
        self.assertIn("d3_validate_wifi_handoff_members", server)
        self.assertIn('strcmp(entry->d_name, "companion")', server)

        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn(
            '"-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_WAIT_MS=5000"',
            manifest,
        )
        self.assertIn(
            '"-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_POLL_MS=50"',
            manifest,
        )
        self.assertIn("wifi_handoff_bind=unexpected-member", server)

    def test_superseded_h9_manifest_keeps_its_original_identity(self) -> None:
        manifest = H9_MANIFEST.read_text(encoding="utf-8")
        self.assertIn('-DINIT_VERSION="0.11.177"', manifest)
        self.assertIn(
            "debian-bookworm-arm64-phase2-display-v3406-keyed-20260809-02.img",
            manifest,
        )
        self.assertIn(
            "e2028b021cd67ebf16ad3cb917e9b548e1fcc434d5e42f10117854f202d01b24",
            manifest,
        )
        self.assertIn("/cache/a90-source-receipt-phase3-minimal-h9", manifest)

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
            "dev_mountpoint=0 dev_tmpfs=mounted image_write=0",
            "source_receipt=qualified path=%s metadata=exact full_sha=verified",
            "source_receipt=verified path=%s metadata=exact full_sha=skipped",
        ):
            self.assertIn(pinned, manifest)


if __name__ == "__main__":
    unittest.main()
