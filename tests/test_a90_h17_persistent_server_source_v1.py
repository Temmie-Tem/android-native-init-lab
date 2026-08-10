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

    def test_h17_native_closure_pin_is_current(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H17).data
        root = REPO / manifest["init"]["source_root"]
        closure = BUILDLIB.expanded_closure(
            root,
            manifest["init"]["sources"],
            manifest["init"]["closure_globs"],
        )
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

    def test_feature_macros_are_all_or_nothing(self) -> None:
        manifest = BUILDLIB.resolve_manifest(H17).data
        manifest["init"]["cflags"].remove("-DA90_UFS_PERSISTENT_NATIVE_HUD_V1=1")
        with self.assertRaisesRegex(RuntimeError, "must be paired"):
            BUILDER.h17_private_runtime_mode(manifest)


class H17NativeSourceTests(unittest.TestCase):
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
        self.assertIn("d_handoff_pid_has_drm_fd(hud_pid)", hud)
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
