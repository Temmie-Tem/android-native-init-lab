"""Static and parser tests for the A90 H17 persistent Debian server lane."""

from __future__ import annotations

import base64
from pathlib import Path
import shutil
import tempfile
import unittest

from _loader import load_script


REPO = Path(__file__).resolve().parents[1]
NATIVE = REPO / "workspace/public/src/native-init/a90_server_distro.c"
FIRSTBOOT = REPO / "workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh"
H16 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h16/manifest.toml"
H17 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h17/manifest.toml"
H18 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h18/manifest.toml"
H19 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h19/manifest.toml"
H20 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h20/manifest.toml"
H21 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h21/manifest.toml"
H22 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h22/manifest.toml"
H23 = REPO / "workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h23/manifest.toml"
BUILDER = load_script(
    "workspace/public/src/scripts/revalidation/a90_flat_builder/build.py"
)
BUILDLIB = load_script(
    "workspace/public/src/scripts/revalidation/a90_flat_builder/buildlib.py"
)
OBSERVER = load_script(
    "workspace/public/src/scripts/server-distro/a90_h17_persistent_server_observer_v1.py"
)


def canonical_test_public_key() -> bytes:
    blob = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + b"\x11" * 32
    return b"ssh-ed25519 " + base64.b64encode(blob) + b"\n"


def passing_transcript() -> str:
    facts = {
        "pid1_comm": "init",
        "pid1_exe": "/usr/sbin/init",
        "root_mount": "/dev/block/a90-userdata|ext4|ro,nosuid,nodev,norecovery",
        "auth_mount": "a90-h17-observer-auth|tmpfs|rw,nosuid,nodev,noexec",
        "auth_key_meta": "regular file|600|0|0|1|81",
        "firstboot_mount": "rootfs|rootfs|ro,nosuid,nodev",
        "hud_run_mount": "a90-dpublic-hud|tmpfs|rw,nosuid,nodev",
        "dropbear_pid": "201",
        "dropbear_exe": "/usr/sbin/dropbear",
        "listener_count": "1",
        "listener_owner": "1",
        "hud_pid": "177",
        "hud_exe": "/init (deleted)",
        "hud_drm_fd_count": "1",
        "hud_status_state": "running",
        "hud_present_rc": "0",
        "hud_last_sequence": "1",
        "marker_autoreboot_sec": "disabled",
        "marker_dropbear_started": "1",
        "marker_hud_intent_written": "1",
        "marker_hud_presenter_pid_valid": "1",
        "marker_hud_presenter_started": "1",
        "marker_hud_started": "1",
        "marker_wifi_sta_decision": "wifi-sta-pass",
        "wlan0_operstate": "up",
        "wlan0_carrier": "1",
    }
    body = "\n".join(f"{key}={facts[key]}" for key in sorted(facts))
    return f"notice\n{OBSERVER.BEGIN}\n{body}\n{OBSERVER.END}\n"


class H17ManifestTests(unittest.TestCase):
    def test_h17_is_a_depth_two_child_with_exact_v5_binding(self) -> None:
        resolution = BUILDLIB.resolve_manifest(H17)
        self.assertEqual(
            [path.parent.name for path in resolution.lineage],
            ["phase3-minimal-h17", "phase3-minimal-h16", "v3404-effective"],
        )
        binding = BUILDER.normalized_auto_handoff_binding(resolution.data)
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v5")
        self.assertEqual(binding["candidate_version"], "0.11.185")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h17-ufs-ro-observer-auth-persistent-hud",
        )
        self.assertEqual(binding["observer_auth"], "boot-private-tmpfs-v1")
        self.assertEqual(binding["display_owner"], "native-handoff-hud-v1")
        self.assertEqual(binding["root_kind"], "userdata-ext4-ro-noload")

    def test_manifest_lineage_still_rejects_a_third_extension(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            versions = Path(raw) / "versions"
            for source in (H17, H16, H16.parents[1] / "v3404-effective/manifest.toml"):
                destination = versions / source.parent.name / "manifest.toml"
                destination.parent.mkdir(parents=True)
                shutil.copyfile(source, destination)
            h18 = versions / "phase3-minimal-h18" / "manifest.toml"
            h18.parent.mkdir()
            h18.write_text(
                'schema = "a90-flat-builder-v1"\n'
                'extends = "phase3-minimal-h17"\n'
                'profile = "depth-three-must-fail"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(BUILDLIB.ManifestError, "depth exceeds 2"):
                BUILDLIB.resolve_manifest(h18)

    def test_h18_diagnostic_successor_keeps_its_historical_identity_and_pin(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H18).data
        self.assertEqual(manifest["profile"], "phase3-minimal-h18-post-root-failure-attribution")
        binding = BUILDER.normalized_auto_handoff_binding(manifest)
        self.assertEqual(binding["candidate_version"], "0.11.186")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h18-post-root-failure-attribution",
        )
        self.assertEqual(
            binding["enable_path"],
            "/cache/a90-auto-handoff-phase3-minimal-h18.enable",
        )
        self.assertEqual(
            binding["latch_path"],
            "/cache/a90-auto-handoff-phase3-minimal-h18.done",
        )
        self.assertEqual(
            manifest["init"]["closure_sha256"],
            "714c17971e357466dbccd69853d2c52b6ccf1b16648df4c2436900989e37009b",
        )

    def test_h19_identity_remains_historical_after_display_assumption_refutation(self) -> None:
        resolution = BUILDLIB.resolve_manifest(H19)
        self.assertEqual(
            [path.parent.name for path in resolution.lineage],
            ["phase3-minimal-h19", "phase3-minimal-h16", "v3404-effective"],
        )
        manifest = resolution.data
        binding = BUILDER.normalized_auto_handoff_binding(manifest)
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v6")
        self.assertEqual(binding["candidate_version"], "0.11.187")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h19-ufs-auth-debian-display",
        )
        self.assertEqual(binding["observer_auth"], "boot-private-tmpfs-v1")
        self.assertEqual(binding["display_owner"], "debian-existing-firstboot-v1")
        self.assertEqual(binding["firstboot_source"], "ufs-existing-immutable-v1")
        self.assertEqual(binding["persistent_native_hud"], "disabled")
        self.assertNotIn("-DA90_UFS_PERSISTENT_NATIVE_HUD_V1=1", manifest["init"]["cflags"])
        self.assertEqual(
            manifest["init"]["closure_sha256"],
            "4623c9cc1d6aa08b305a5151312355f3f2eff56abc4413c6ca013aa47ecf28e2",
        )

    def test_h20_keeps_native_hud_but_retires_only_firstboot_overlay(self) -> None:
        resolution = BUILDLIB.resolve_manifest(H20)
        self.assertEqual(
            [path.parent.name for path in resolution.lineage],
            ["phase3-minimal-h20", "phase3-minimal-h16", "v3404-effective"],
        )
        manifest = resolution.data
        binding = BUILDER.normalized_auto_handoff_binding(manifest)
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v7")
        self.assertEqual(binding["candidate_version"], "0.11.188")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h20-ufs-auth-native-hud-no-firstboot-overlay",
        )
        self.assertEqual(binding["observer_auth"], "boot-private-tmpfs-v1")
        self.assertEqual(binding["display_owner"], "native-handoff-hud-v1")
        self.assertEqual(binding["firstboot_source"], "ufs-existing-immutable-v1")
        self.assertEqual(binding["firstboot_overlay"], "disabled")
        self.assertEqual(binding["persistent_native_hud"], "enabled")
        self.assertEqual(BUILDER.h17_runtime_features(manifest), (True, False, True))
        self.assertNotIn("firstboot_overlay=ready", "\n".join(manifest["validation"]["init_strings"]))
        self.assertEqual(
            manifest["init"]["closure_globs"],
            [
                "a90*.c",
                "a90*.h",
                "v319/*.inc.c",
                "v319/a90*.h",
                "v724/*.inc.c",
                "helpers/a90_android_execns_probe.c",
            ],
        )
        root = REPO / manifest["init"]["source_root"]
        closure = BUILDLIB.expanded_closure(
            root,
            manifest["init"]["sources"],
            manifest["init"]["closure_globs"],
        )
        self.assertFalse(any(path.startswith("s22plus") for path in closure))
        self.assertNotEqual(
            BUILDLIB.closure_sha256(root, closure),
            manifest["init"]["closure_sha256"],
        )

    def test_h21_defers_native_hud_drm_until_the_ufs_intent(self) -> None:
        resolution = BUILDLIB.resolve_manifest(H21)
        self.assertEqual(
            [path.parent.name for path in resolution.lineage],
            ["phase3-minimal-h21", "phase3-minimal-h16", "v3404-effective"],
        )
        manifest = resolution.data
        binding = BUILDER.normalized_auto_handoff_binding(manifest)
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v8")
        self.assertEqual(binding["candidate_version"], "0.11.189")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h21-ufs-auth-native-hud-delayed-drm",
        )
        self.assertEqual(binding["firstboot_overlay"], "disabled")
        self.assertEqual(binding["persistent_native_hud"], "enabled")
        self.assertEqual(
            binding["hud_drm_acquisition"],
            "deferred-until-ufs-intent-v1",
        )
        self.assertEqual(
            binding["ufs_firstboot_cleanup_compatibility"],
            "no-pre-intent-drm-fd-v1",
        )
        self.assertTrue(BUILDER.h21_delayed_hud_drm_mode(manifest))
        root = REPO / manifest["init"]["source_root"]
        closure = BUILDLIB.expanded_closure(
            root,
            manifest["init"]["sources"],
            manifest["init"]["closure_globs"],
        )
        self.assertNotEqual(
            BUILDLIB.closure_sha256(root, closure),
            manifest["init"]["closure_sha256"],
        )

    def test_h22_identity_is_historical_and_its_native_closure_is_retired(self) -> None:
        resolution = BUILDLIB.resolve_manifest(H22)
        self.assertEqual(
            [path.parent.name for path in resolution.lineage],
            ["phase3-minimal-h22", "phase3-minimal-h16", "v3404-effective"],
        )
        manifest = resolution.data
        binding = BUILDER.normalized_auto_handoff_binding(manifest)
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v9")
        self.assertEqual(binding["candidate_version"], "0.11.190")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h22-ufs-auth-native-hud-preserved-dev-dir",
        )
        self.assertEqual(
            binding["hud_drm_acquisition"],
            "deferred-until-ufs-intent-v2",
        )
        self.assertEqual(
            binding["hud_drm_device_access"],
            "preopened-dev-dir-fd-openat-card0-v1",
        )
        self.assertEqual(
            binding["ufs_firstboot_cleanup_compatibility"],
            "no-pre-intent-drm-card-fd-v2",
        )
        self.assertTrue(BUILDER.h21_delayed_hud_drm_mode(manifest))
        self.assertTrue(BUILDER.h22_preserved_dev_dir_mode(manifest))
        root = REPO / manifest["init"]["source_root"]
        closure = BUILDLIB.expanded_closure(
            root,
            manifest["init"]["sources"],
            manifest["init"]["closure_globs"],
        )
        self.assertNotEqual(
            BUILDLIB.closure_sha256(root, closure),
            manifest["init"]["closure_sha256"],
        )

    def test_h23_uses_an_exact_private_card_root_binding(self) -> None:
        resolution = BUILDLIB.resolve_manifest(H23)
        self.assertEqual(
            [path.parent.name for path in resolution.lineage],
            ["phase3-minimal-h23", "phase3-minimal-h16", "v3404-effective"],
        )
        manifest = resolution.data
        binding = BUILDER.normalized_auto_handoff_binding(manifest)
        self.assertEqual(binding["schema"], "a90-compiled-auto-handoff-binding-v10")
        self.assertEqual(binding["candidate_version"], "0.11.191")
        self.assertEqual(
            binding["candidate_build"],
            "phase3-minimal-h23-ufs-auth-native-hud-private-card-root",
        )
        self.assertEqual(
            binding["hud_drm_acquisition"],
            "deferred-until-ufs-intent-v3",
        )
        self.assertEqual(
            binding["hud_drm_device_access"],
            "private-pivot-root-card0-bind-v1",
        )
        self.assertEqual(
            binding["hud_mount_namespace"],
            "private-minimal-card-root-v1",
        )
        self.assertEqual(
            binding["debian_device_exposure"],
            "card0-only-no-userdata-v1",
        )
        self.assertTrue(BUILDER.h21_delayed_hud_drm_mode(manifest))
        self.assertFalse(BUILDER.h22_preserved_dev_dir_mode(manifest))
        self.assertTrue(BUILDER.h23_private_card_root_mode(manifest))
        root = REPO / manifest["init"]["source_root"]
        closure = BUILDLIB.expanded_closure(
            root,
            manifest["init"]["sources"],
            manifest["init"]["closure_globs"],
        )
        self.assertFalse(any(path.startswith("s22plus") for path in closure))
        self.assertEqual(len(closure), 142)
        self.assertEqual(
            BUILDLIB.closure_sha256(root, closure),
            manifest["init"]["closure_sha256"],
        )

    def test_private_key_is_required_only_for_h17_and_never_enters_manifest(self) -> None:
        h17 = BUILDLIB.resolve_manifest(H17).data
        h16 = BUILDLIB.resolve_manifest(H16).data
        with self.assertRaisesRegex(RuntimeError, "requires"):
            BUILDER.validate_observer_authorized_key(REPO, h17, None)
        private = REPO / "workspace/private"
        with tempfile.TemporaryDirectory(dir=private) as raw:
            key = Path(raw) / "observer.pub"
            key.write_bytes(canonical_test_public_key())
            bound = BUILDER.validate_observer_authorized_key(REPO, h17, key)
            assert bound is not None
            self.assertEqual(bound["bytes"], key.stat().st_size)
            self.assertNotIn(key.read_text(), H17.read_text())
            key.write_bytes(b"ssh-ed25519 AAAA\n")
            with self.assertRaisesRegex(RuntimeError, "metadata|canonical"):
                BUILDER.validate_observer_authorized_key(REPO, h17, key)
            key.write_bytes(canonical_test_public_key())
            with self.assertRaisesRegex(RuntimeError, "non-H17"):
                BUILDER.validate_observer_authorized_key(REPO, h16, key)

    def test_auth_only_is_allowed_but_hud_without_auth_is_rejected(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H17).data
        manifest["init"]["cflags"].remove("-DA90_UFS_PERSISTENT_NATIVE_HUD_V1=1")
        self.assertEqual(BUILDER.h17_runtime_features(manifest), (True, False, False))
        self.assertTrue(BUILDER.h17_private_runtime_mode(manifest))
        self.assertFalse(BUILDER.h17_firstboot_overlay_mode(manifest))
        self.assertFalse(BUILDER.h17_persistent_hud_mode(manifest))
        manifest["init"]["cflags"].remove("-DA90_UFS_OBSERVER_AUTH_OVERLAY_V1=1")
        manifest["init"]["cflags"].append("-DA90_UFS_PERSISTENT_NATIVE_HUD_V1=1")
        with self.assertRaisesRegex(RuntimeError, "requires observer-auth"):
            BUILDER.h17_runtime_features(manifest)

    def test_delayed_hud_drm_rejects_firstboot_overlay_or_missing_hud(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H21).data
        manifest["init"]["cflags"].remove("-DA90_UFS_FIRSTBOOT_OVERLAY_V1=0")
        manifest["init"]["cflags"].append("-DA90_UFS_FIRSTBOOT_OVERLAY_V1=1")
        with self.assertRaisesRegex(RuntimeError, "without firstboot overlay"):
            BUILDER.h21_delayed_hud_drm_mode(manifest)
        manifest = BUILDLIB.resolve_manifest(H21).data
        manifest["init"]["cflags"].remove("-DA90_UFS_PERSISTENT_NATIVE_HUD_V1=1")
        with self.assertRaisesRegex(RuntimeError, "requires auth and HUD"):
            BUILDER.h21_delayed_hud_drm_mode(manifest)

    def test_preserved_dev_dir_requires_delayed_hud_drm(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H22).data
        manifest["init"]["cflags"].remove(
            "-DA90_UFS_PERSISTENT_NATIVE_HUD_DELAYED_DRM_V1=1"
        )
        with self.assertRaisesRegex(RuntimeError, "requires delayed HUD DRM"):
            BUILDER.h22_preserved_dev_dir_mode(manifest)

    def test_private_card_root_rejects_missing_delay_or_preserved_dev(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H23).data
        manifest["init"]["cflags"].remove(
            "-DA90_UFS_PERSISTENT_NATIVE_HUD_DELAYED_DRM_V1=1"
        )
        with self.assertRaisesRegex(RuntimeError, "requires delayed HUD DRM"):
            BUILDER.h23_private_card_root_mode(manifest)

        manifest = BUILDLIB.resolve_manifest(H23).data
        manifest["init"]["cflags"].append(
            "-DA90_UFS_PERSISTENT_NATIVE_HUD_PRESERVED_DEV_DIR_V1=1"
        )
        with self.assertRaisesRegex(RuntimeError, "without preserved dev FD"):
            BUILDER.h23_private_card_root_mode(manifest)


class H17NativeSourceTests(unittest.TestCase):
    def test_post_root_failure_stage_and_errno_are_retained_before_cleanup(self) -> None:
        source = NATIVE.read_text()
        handoff = source[
            source.index("int a90_server_distro_switch_root_userdata_ro(") :
            source.index("static int d4_dpublic_hud_bind_target(")
        ]
        stage_calls = [
            ("root-content", "d4_userdata_ro_check_root(expected_marker,"),
            ("writable-set-mount", "d3_mount_writable_set(&writable_mounted)"),
            ("writable-set-verify", "d3_verify_writable_set()"),
            ("observer-auth-overlay", "h17_mount_observer_auth("),
            ("firstboot-overlay", "h17_bind_firstboot(&h17_firstboot_bound)"),
            ("persistent-hud", "h17_start_persistent_hud("),
            ("evidence-bind", "d3_bind_evidence_dir(&evidence_bound)"),
            ("wifi-handoff-bind", "d3_bind_wifi_handoff_dir(&wifi_handoff_bound)"),
        ]
        positions = []
        for index, (stage, call) in enumerate(stage_calls):
            stage_token = f'failure_stage = "{stage}";'
            start = handoff.index(stage_token)
            end = (
                handoff.index(f'failure_stage = "{stage_calls[index + 1][0]}";')
                if index + 1 < len(stage_calls)
                else handoff.index('failure_stage = "distro-init";')
            )
            block = handoff[start:end]
            self.assertLess(block.index(stage_token), block.index(call))
            self.assertLess(block.index(call), block.index("if (rc < 0)"))
            self.assertIn("goto fail_before_move;", block)
            positions.append(start)
        self.assertEqual(positions, sorted(positions))
        failure = handoff[handoff.index("fail_before_move:") :]
        diagnostic = failure.index("d4_record_handoff_failure(")
        cleanup = failure.index("h17_stop_persistent_hud(")
        self.assertLess(diagnostic, cleanup)
        self.assertIn("failure_stage", failure[:cleanup])
        self.assertIn("failure_recorded", failure[:cleanup])

        move = handoff[
            handoff.index('failure_stage = "core-mount-move";') :
            handoff.index("#if A90_AUTO_HANDOFF_BENCHMARK_V1", handoff.index('failure_stage = "core-mount-move";'))
        ]
        self.assertLess(move.index("d3_move_core_mounts(true,"), move.index("if (rc < 0)"))
        self.assertLess(move.index("if (rc < 0)"), move.index("d4_record_handoff_failure("))
        self.assertLess(move.index("d4_record_handoff_failure("), move.index("d3_restore_core_mounts("))

        switch_exec = handoff[handoff.index('failure_stage = "switch-root-exec";') : handoff.index("fail_before_move:")]
        self.assertLess(switch_exec.index("execve(A90_D3_BUSYBOX"), switch_exec.index("rc = -errno;"))
        self.assertLess(switch_exec.index("rc = -errno;"), switch_exec.index("d4_record_handoff_failure("))
        self.assertLess(switch_exec.index("d4_record_handoff_failure("), switch_exec.index("d3_restore_core_mounts("))
        self.assertEqual(handoff.count("failure_recorded = true;"), 2)

    def test_handoff_overlays_follow_content_validation_and_precede_switch_root(self) -> None:
        source = NATIVE.read_text()
        handoff = source[
            source.index("int a90_server_distro_switch_root_userdata_ro(") :
            source.index("static int d4_dpublic_hud_bind_target(")
        ]
        ordered = [
            "d4_userdata_ro_check_root(expected_marker,",
            "d3_mount_writable_set(&writable_mounted)",
            "h17_mount_observer_auth(&h17_observer_auth_mounted)",
            "h17_bind_firstboot(&h17_firstboot_bound)",
            "h17_start_persistent_hud(",
            "d3_move_core_mounts(true,",
            "execve(A90_D3_BUSYBOX, switch_argv, newenv)",
        ]
        positions = [handoff.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("h17_stop_persistent_hud", handoff)
        self.assertIn("h17_unbind_firstboot", handoff)
        self.assertIn("h17_unmount_observer_auth", handoff)
        self.assertIn("cleanup_clean = false", handoff)
        self.assertIn("ufs_write=0", source)

    def test_h20_firstboot_and_native_hud_calls_have_independent_guards(self) -> None:
        source = NATIVE.read_text()
        handoff = source[
            source.index("int a90_server_distro_switch_root_userdata_ro(") :
            source.index("static int d4_dpublic_hud_bind_target(")
        ]
        auth_start = handoff.index("#if A90_UFS_OBSERVER_AUTH_OVERLAY_V1")
        firstboot_guard = handoff.index(
            "#if A90_UFS_FIRSTBOOT_OVERLAY_V1",
            auth_start,
        )
        firstboot_call = handoff.index(
            "h17_bind_firstboot(&h17_firstboot_bound)",
            firstboot_guard,
        )
        firstboot_end = handoff.index("#endif", firstboot_call)
        hud_guard = handoff.index(
            "#if A90_UFS_PERSISTENT_NATIVE_HUD_V1",
            firstboot_end,
        )
        hud_call = handoff.index("h17_start_persistent_hud(", hud_guard)
        hud_end = handoff.index("#endif", hud_call)
        self.assertLess(firstboot_guard, firstboot_call)
        self.assertLess(firstboot_call, firstboot_end)
        self.assertLess(firstboot_end, hud_guard)
        self.assertLess(hud_guard, hud_call)
        self.assertLess(hud_call, hud_end)
        self.assertIn(
            "firstboot=ufs-existing firstboot_overlay=disabled",
            handoff,
        )
        self.assertIn("persistent_native_hud=enabled", handoff)

    def test_h21_starts_the_hud_without_drm_and_requires_no_preintent_drm_fd(self) -> None:
        source = NATIVE.read_text()
        start = source[
            source.index("static int h17_start_persistent_hud(") :
            source.index("static int h17_stop_persistent_hud(")
        ]
        self.assertIn("#if A90_UFS_PERSISTENT_NATIVE_HUD_DELAYED_DRM_V1", start)
        self.assertIn("opts.preopen_drm = false", start)
        self.assertIn("hud_has_drm))", start)
        self.assertIn("drm_fd=deferred", start)
        self.assertIn("drm_trigger=ufs-intent", start)

    def test_h23_sanitizes_fds_and_pivots_to_a_card0_only_root(self) -> None:
        source = NATIVE.read_text()
        start = source[
            source.index("static int h17_start_persistent_hud(") :
            source.index("static int h17_stop_persistent_hud(")
        ]
        private = source[
            source.index("static int dpublic_hud_service_sanitize_fds(") :
            source.index("static int dpublic_hud_service_child_loop(")
        ]
        child = source[
            source.index("static int dpublic_hud_service_child_loop(") :
            source.index("static bool dpublic_hud_service_pid_is_default(")
        ]
        self.assertIn('open("/dev/null", O_RDWR | O_CLOEXEC | O_NOFOLLOW)', private)
        self.assertIn("S_ISFIFO(ready_st.st_mode)", private)
        self.assertIn("null_st.st_rdev != makedev(1, 3)", private)
        self.assertIn("dup2(null_fd, fd)", private)
        self.assertIn('opendir("/proc/self/fd")', private)
        self.assertIn("fd == ready_fd || fd == scan_fd", private)
        exact_tree = source[
            source.index("static int h23_dir_has_only(") :
            source.index("static int h23_require_absent(")
        ]
        self.assertLess(exact_tree.index("errno = 0;"), exact_tree.index("readdir(dir)"))
        self.assertIn("if (errno != 0)", exact_tree)
        ordered = [
            "dpublic_hud_service_sanitize_fds(ready_fd)",
            "unshare(CLONE_NEWNS)",
            "MS_REC | MS_PRIVATE",
            'mount("a90-hud-private-root"',
            "mount(card_source, card_target, NULL, MS_BIND, NULL)",
            "mount(A90_DPUBLIC_HUD_RUN_DIR, run_target, NULL, MS_BIND, NULL)",
            'syscall(SYS_pivot_root, ".", "old-root")',
            "umount2(A90_DPUBLIC_HUD_PRIVATE_OLD_ROOT, MNT_DETACH)",
            'lstat("/dev/block/a90-userdata", &forbidden)',
            'lstat("/proc", &forbidden)',
            'lstat("/sys", &forbidden)',
        ]
        positions = [private.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("opts.private_card_root = true", start)
        self.assertIn("d_handoff_pid_has_drm_fd_until(hud_pid, 0", start)
        self.assertIn("h23_validate_private_card_root(hud_pid)", start)
        self.assertIn("drm_access=private-pivot-root-card0-bind", start)
        self.assertIn("old_root=detached userdata_exposed=0", start)
        self.assertLess(
            child.index("a90_console_silence_child()"),
            child.index("dpublic_hud_service_enter_private_card_root(ready_fd)"),
        )
        self.assertLess(
            child.index("dpublic_hud_parse_intent("),
            child.index("a90_kms_begin_frame(0x061018)"),
        )
        self.assertNotIn("a90_kms_begin_frame_from_dev_dir", source)
        self.assertNotIn("h22_open_preserved_dev_dir", source)

    def test_auth_overlay_is_tmpfs_and_key_bytes_are_never_logged(self) -> None:
        source = NATIVE.read_text()
        auth = source[
            source.index("static int h17_authorized_key_bytes_valid(") :
            source.index("static int d3_check_distro_init(")
        ]
        self.assertIn('mount("a90-h17-observer-auth"', auth)
        self.assertIn("MS_NOSUID | MS_NODEV | MS_NOEXEC", auth)
        self.assertIn('"mode=0700,uid=0,gid=0,size=64k"', auth)
        self.assertIn("O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW", auth)
        self.assertIn("fchmod(target_fd, 0600)", auth)
        self.assertNotIn("%s", auth[auth.index("observer_auth=ready") :])

    def test_firstboot_preserves_only_the_bound_native_hud_pid(self) -> None:
        script = FIRSTBOOT.read_text()
        self.assertIn("native_hud_pid=$(cat /run/a90-dpublic/hud-presenter.pid", script)
        self.assertIn("native_hud_pid_valid=0", script)
        self.assertIn('/init|"/init (deleted)")', script)
        self.assertIn('[ "$native_hud_pid_valid" = "1" ] || native_hud_pid=', script)
        self.assertIn('[ "$pid" = "$native_hud_pid" ] && continue', script)
        self.assertIn("hud_presenter_pid_valid=$native_hud_pid_valid", script)
        self.assertIn("hud_presenter_started=$hud_presenter_started", script)
        self.assertIn("hud_started=$hud_presenter_started", script)

    def test_firstboot_bind_is_read_only_and_hud_requires_exact_drm_owner(self) -> None:
        source = NATIVE.read_text()
        firstboot = source[
            source.index("static int h17_bind_firstboot(") :
            source.index("static int h17_start_persistent_hud(")
        ]
        hud = source[
            source.index("static int h17_start_persistent_hud(") :
            source.index("int a90_server_distro_userdata_ro_qualify(")
        ]
        self.assertIn(
            "MS_REMOUNT | MS_BIND | MS_RDONLY | MS_NOSUID | MS_NODEV",
            firstboot,
        )
        self.assertIn("(target_fs.f_flag & ST_RDONLY) == 0", firstboot)
        self.assertIn("dpublic_hud_service_pid_is_default(hud_pid)", hud)
        self.assertIn("d_handoff_pid_has_drm_fd_until(hud_pid, 0", hud)
        self.assertIn("hud_pid != *pid_out", hud)
        self.assertIn("d_handoff_stop_drm_owner(A90_DPUBLIC_HUD_SERVICE_TAG, *pid)", hud)

    def test_unpublished_hud_child_cleanup_is_bounded_and_tracked(self) -> None:
        source = NATIVE.read_text()
        start = source[
            source.index("static int dpublic_hud_service_start(") :
            source.index("static int dpublic_hud_service_status(")
        ]
        self.assertIn("pid_t *child_pid_out", start)
        self.assertEqual(
            start.count("d_handoff_stop_drm_owner("),
            2,
        )
        self.assertIn("return cleanup_rc < 0 ? cleanup_rc : rc;", start)
        self.assertNotIn("(void)kill(pid, SIGTERM)", start)

    def test_shared_hud_run_mount_and_bind_are_fail_closed(self) -> None:
        source = NATIVE.read_text()
        verifier = source[
            source.index("static int dpublic_hud_service_verify_shared_run_mount(") :
            source.index("static int dpublic_hud_service_mount_shared_run_dir(")
        ]
        bind = source[
            source.index("static int d4_bind_dpublic_hud_run_dir(bool *bound_out) {") :
            source.index("static int d4_move_mount_one(")
        ]
        self.assertIn('strcmp(source, A90_DPUBLIC_HUD_RUN_SOURCE) == 0', verifier)
        self.assertIn('strcmp(fstype, "tmpfs") == 0', verifier)
        self.assertIn('dpublic_hud_mount_option_present(options, "nosuid")', verifier)
        self.assertIn('dpublic_hud_mount_option_present(options, "nodev")', verifier)
        self.assertIn("matches != 1U", verifier)
        self.assertIn("(fs.f_flag & ST_NOSUID) == 0", verifier)
        self.assertIn("MS_REMOUNT | MS_BIND | MS_NOSUID | MS_NODEV", bind)
        self.assertIn("src_st.st_dev != dst_st.st_dev", bind)
        self.assertIn("src_st.st_ino != dst_st.st_ino", bind)
        self.assertIn("dst_st.st_gid != A90_DPUBLIC_HUD_GROUP_GID", bind)
        self.assertIn("goto fail_bound", bind)


class H17ObserverTests(unittest.TestCase):
    def test_passing_transcript_requires_visible_hud_and_stays_health_pending(self) -> None:
        result = OBSERVER.classify(passing_transcript(), 0, True)
        self.assertTrue(result["proof"])
        self.assertEqual(result["status"], "PASS_A90_H17_PERSISTENT_SERVER_LIVE")
        self.assertEqual(result["device_safety"], "HEALTH_PENDING_PERSISTENT_DEBIAN")
        self.assertFalse(result["new_device_effect_authority"])
        self.assertFalse(result["automatic_native_return_expected"])

        no_visible = OBSERVER.classify(passing_transcript(), 0, False)
        self.assertFalse(no_visible["proof"])

    def test_observer_rejects_duplicate_or_missing_facts(self) -> None:
        transcript = passing_transcript()
        duplicate = transcript.replace(
            OBSERVER.END,
            "pid1_comm=init\n" + OBSERVER.END,
        )
        with self.assertRaisesRegex(OBSERVER.ObserverError, "not exact"):
            OBSERVER.classify(duplicate, 0, True)
        missing = transcript.replace("wlan0_carrier=1\n", "")
        with self.assertRaisesRegex(OBSERVER.ObserverError, "not exact"):
            OBSERVER.classify(missing, 0, True)

    def test_observer_rejects_wrong_mount_identity_or_hud_pid(self) -> None:
        wrong_auth = passing_transcript().replace(
            "auth_mount=a90-h17-observer-auth|",
            "auth_mount=other-tmpfs|",
        )
        self.assertFalse(OBSERVER.classify(wrong_auth, 0, True)["proof"])
        writable_firstboot = passing_transcript().replace(
            "firstboot_mount=rootfs|rootfs|ro,nosuid,nodev",
            "firstboot_mount=rootfs|rootfs|rw,nosuid,nodev",
        )
        self.assertFalse(OBSERVER.classify(writable_firstboot, 0, True)["proof"])
        stale_hud = passing_transcript().replace(
            "marker_hud_presenter_pid_valid=1",
            "marker_hud_presenter_pid_valid=0",
        )
        self.assertFalse(OBSERVER.classify(stale_hud, 0, True)["proof"])
        wrong_hud_run = passing_transcript().replace(
            "hud_run_mount=a90-dpublic-hud|tmpfs|rw,nosuid,nodev",
            "hud_run_mount=other|tmpfs|rw,nosuid,nodev",
        )
        self.assertFalse(OBSERVER.classify(wrong_hud_run, 0, True)["proof"])
        missing_no_replay = passing_transcript().replace(
            ",norecovery",
            "",
        )
        self.assertFalse(OBSERVER.classify(missing_no_replay, 0, True)["proof"])

    def test_ssh_command_is_fixed_key_only_usb_ncm(self) -> None:
        command = OBSERVER.ssh_command(Path("/private/observer"), 5.0)
        self.assertIn("root@192.168.7.2", command)
        self.assertIn("PasswordAuthentication=no", command)
        self.assertIn("KbdInteractiveAuthentication=no", command)
        self.assertIn("IdentitiesOnly=yes", command)
        remote = command[-1]
        self.assertEqual(remote.count("if (count == 1) print value"), 2)
        self.assertIn("__invalid_count_", remote)
        for forbidden in (" reboot ", " mount ", " umount ", " rm ", " chmod ", " chown "):
            self.assertNotIn(forbidden, f" {remote} ")


if __name__ == "__main__":
    unittest.main()
