from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta151_dropbear_admin_syscall_trace.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta151_dropbear_admin_syscall_trace.py")


def args(**overrides) -> argparse.Namespace:
    defaults = {
        "execute_dropbear_admin_syscall_trace_live": False,
        "allow_dropbear_admin_trace_live": False,
        "ack_admin_key_material": False,
        "ack_root_login_negative_test": False,
        "ack_private_trace_artifact": False,
        "ack_runtime_cleanup": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class ServerDistroWsta151DropbearAdminSyscallTraceTests(unittest.TestCase):
    def test_explicit_live_gate_requires_all_acknowledgements(self) -> None:
        self.assertEqual(
            runner.explicit_live_gate(args()),
            (False, "wsta151-blocked-dropbear-admin-syscall-trace-live-required"),
        )
        self.assertEqual(
            runner.explicit_live_gate(args(execute_dropbear_admin_syscall_trace_live=True)),
            (False, "wsta151-blocked-dropbear-admin-trace-live-allow-required"),
        )
        self.assertEqual(
            runner.explicit_live_gate(args(
                execute_dropbear_admin_syscall_trace_live=True,
                allow_dropbear_admin_trace_live=True,
            )),
            (False, "wsta151-blocked-admin-key-material-ack-required"),
        )
        self.assertEqual(
            runner.explicit_live_gate(args(
                execute_dropbear_admin_syscall_trace_live=True,
                allow_dropbear_admin_trace_live=True,
                ack_admin_key_material=True,
            )),
            (False, "wsta151-blocked-root-login-negative-test-ack-required"),
        )
        self.assertEqual(
            runner.explicit_live_gate(args(
                execute_dropbear_admin_syscall_trace_live=True,
                allow_dropbear_admin_trace_live=True,
                ack_admin_key_material=True,
                ack_root_login_negative_test=True,
            )),
            (False, "wsta151-blocked-private-trace-artifact-ack-required"),
        )
        self.assertEqual(
            runner.explicit_live_gate(args(
                execute_dropbear_admin_syscall_trace_live=True,
                allow_dropbear_admin_trace_live=True,
                ack_admin_key_material=True,
                ack_root_login_negative_test=True,
                ack_private_trace_artifact=True,
            )),
            (False, "wsta151-blocked-runtime-cleanup-ack-required"),
        )
        self.assertEqual(
            runner.explicit_live_gate(args(
                execute_dropbear_admin_syscall_trace_live=True,
                allow_dropbear_admin_trace_live=True,
                ack_admin_key_material=True,
                ack_root_login_negative_test=True,
                ack_private_trace_artifact=True,
                ack_runtime_cleanup=True,
            )),
            (True, "ok"),
        )

    def test_safety_is_inert_until_live_gate(self) -> None:
        inert = runner.safety(False)
        live = runner.safety(True)

        self.assertFalse(inert["device_action"])
        self.assertFalse(inert["boot_flash"])
        self.assertFalse(inert["public_tunnel"])
        self.assertFalse(inert["admin_key_material"])
        self.assertEqual(inert["secret_values_logged"], 0)
        self.assertTrue(live["device_action"])
        self.assertFalse(live["boot_flash"])
        self.assertEqual(live["syscall_trace_capture"], "explicit-live-gated-private-artifact")
        self.assertTrue(live["root_login_negative_test"])

    def test_admin_trace_stage_script_wraps_safe_dropbear_in_strace(self) -> None:
        script = runner.admin_trace_stage_and_start_script(
            "/mnt/a90",
            "ssh-ed25519 AAAATEST operator@example",
            "192.168.7.2",
            2222,
        )

        self.assertIn("A90WSTA151_ADMIN_TRACE_STAGE_BEGIN", script)
        self.assertIn("A90WSTA151_ADMIN_TRACE_STAGE_DONE", script)
        self.assertIn("a90admin:x:3903:3903:A90 admin a90admin:/home/a90admin:/bin/sh", script)
        self.assertIn("/home/a90admin/.ssh/authorized_keys", script)
        self.assertIn("/root/.ssh/authorized_keys", script)
        self.assertIn("A90WSTA151_ROOT_AUTHORIZED_KEYS_ABSENT=1", script)
        self.assertIn("/usr/bin/strace -qq -f -s 96 -o", script)
        self.assertIn("/usr/sbin/dropbear -F -E", script)
        self.assertIn("-s -w -j -k", script)
        self.assertIn("A90WSTA151_STRACE_PRESENT=1", script)
        self.assertIn("A90WSTA151_TRACE_ALIVE=1", script)
        self.assertNotIn("$M/root/.ssh/authorized_keys\" > ", script)

    def test_parse_stage_requires_strace_root_denied_and_safe_dropbear(self) -> None:
        record = {
            "text": "\n".join([
                "A90WSTA151_ADMIN_TRACE_STAGE_BEGIN",
                "A90WSTA151_ROOT_AUTHORIZED_KEYS_ABSENT=1",
                "A90WSTA151_ADMIN_PASSWD_LINE=1",
                "A90WSTA151_ADMIN_GROUP_LINE=1",
                "A90WSTA151_ADMIN_SHADOW_LINE=1",
                "A90WSTA151_ADMIN_AUTHORIZED_KEYS=1",
                "A90WSTA151_DROPBEAR_PRESENT=1",
                "A90WSTA151_STRACE_PRESENT=1",
                "A90WSTA151_HOSTKEY_TYPE=ed25519",
                "A90WSTA151_DROPBEAR_COMMAND=/usr/sbin/dropbear -F -E -r /tmp/a90_dropbear_admin_hostkey -p 192.168.7.2:2222 -P /tmp/a90_dropbear_admin.pid -s -w -j -k",
                "A90WSTA151_TRACE_ALIVE=1",
                "A90WSTA151_DROPBEAR_LISTEN=1",
                "A90WSTA151_ADMIN_TRACE_STAGE_DONE",
            ])
        }
        parsed = runner.parse_stage(record)
        no_strace = runner.parse_stage({"text": str(record["text"]).replace(
            "A90WSTA151_STRACE_PRESENT=1",
            "A90WSTA151_STRACE_PRESENT=0",
        )})

        self.assertTrue(parsed["stage_done"])
        self.assertTrue(parsed["root_authorized_keys_absent"])
        self.assertTrue(parsed["strace_present"])
        self.assertTrue(parsed["dropbear_command_safe"])
        self.assertTrue(parsed["trace_alive"])
        self.assertFalse(no_strace["strace_present"])

    def test_parse_snapshot_requires_core_and_accept_syscalls(self) -> None:
        snapshot_script = runner.snapshot_trace_script("/mnt/a90")
        self.assertIn("/bin/busybox awk", snapshot_script)
        self.assertIn("/bin/busybox sort", snapshot_script)
        self.assertIn("A90WSTA151_TRACE_SNAPSHOT_FILE_NONEMPTY=1", snapshot_script)
        self.assertIn("dropbear-admin.snapshot.strace", snapshot_script)
        self.assertNotIn("/usr/bin/awk", snapshot_script)
        self.assertIn("Password auth succeeded", snapshot_script)
        self.assertNotIn("Password auth succeeded\\\\|root login", snapshot_script)

        record = {
            "text": "\n".join([
                "A90WSTA151_TRACE_SNAPSHOT_BEGIN",
                "A90WSTA151_TRACE_FILE_NONEMPTY=1",
                "A90WSTA151_TRACE_SNAPSHOT_FILE_NONEMPTY=1",
                "A90WSTA151_SYSCALL_PROFILE_NONEMPTY=1",
                "A90WSTA151_SYSCALL_COUNT=6",
                "A90WSTA151_DROPBEAR_LOG_POLICY_CLEAN=1",
                "A90WSTA151_SYSCALL_LIST_BEGIN",
                "accept",
                "bind",
                "close",
                "execve",
                "listen",
                "socket",
                "A90WSTA151_SYSCALL_LIST_END",
                "A90WSTA151_TRACE_SNAPSHOT_DONE",
            ])
        }
        parsed = runner.parse_snapshot(record)
        missing_accept = runner.parse_snapshot({"text": str(record["text"]).replace("accept\n", "")})

        self.assertTrue(parsed["snapshot_done"])
        self.assertTrue(parsed["trace_file_nonempty"])
        self.assertTrue(parsed["trace_snapshot_file_nonempty"])
        self.assertTrue(parsed["core_syscalls_observed"])
        self.assertTrue(parsed["accept_observed"])
        self.assertEqual(parsed["syscall_count"], 6)
        self.assertFalse(missing_accept["accept_observed"])

    def test_parse_snapshot_accepts_marker_proof_when_list_is_not_printed(self) -> None:
        parsed = runner.parse_snapshot({
            "text": "\n".join([
                "A90WSTA151_TRACE_SNAPSHOT_BEGIN",
                "A90WSTA151_TRACE_FILE_NONEMPTY=1",
                "A90WSTA151_TRACE_SNAPSHOT_FILE_NONEMPTY=1",
                "A90WSTA151_SYSCALL_PROFILE_NONEMPTY=1",
                "A90WSTA151_SYSCALL_COUNT=53",
                "A90WSTA151_SYSCALL_HAS_execve=1",
                "A90WSTA151_SYSCALL_HAS_socket=1",
                "A90WSTA151_SYSCALL_HAS_bind=1",
                "A90WSTA151_SYSCALL_HAS_listen=1",
                "A90WSTA151_SYSCALL_HAS_ACCEPT=1",
                "A90WSTA151_DROPBEAR_LOG_POLICY_CLEAN=1",
            ])
        })

        self.assertTrue(parsed["core_syscalls_observed"])
        self.assertTrue(parsed["accept_observed"])
        self.assertTrue(parsed["dropbear_log_policy_clean"])

    def test_syscall_profile_records_admin_boundary_without_public_values(self) -> None:
        profile = runner.syscall_profile(
            {
                "core_syscalls_observed": True,
                "accept_observed": True,
                "syscall_count": 5,
                "syscall_names": ["accept4", "bind", "execve", "listen", "socket"],
            },
            admin_ok=True,
            root_rejected=True,
            bind="192.168.7.2:2222",
            trace_artifacts={"all_saved": True},
        )

        self.assertEqual(profile["schema"], "a90-wsta151-dropbear-admin-syscall-profile-v1")
        self.assertEqual(profile["service"], "dropbear-admin-usb")
        self.assertEqual(profile["daemon_privilege_model"], "root-boundary-auth-daemon")
        self.assertEqual(profile["bind"], "192.168.7.2:2222")
        self.assertEqual(profile["network_scope"], "usb-ncm-admin-only")
        self.assertTrue(profile["admin_login_uid_gid_proven"])
        self.assertTrue(profile["root_ssh_rejected"])
        self.assertTrue(profile["core_syscalls_observed"])
        self.assertTrue(profile["accept_observed"])
        self.assertFalse(profile["public_url_value_logged"])
        self.assertEqual(profile["secret_values_logged"], 0)

    def test_trace_cleanup_parse_and_classify_order(self) -> None:
        parsed = runner.parse_trace_cleanup({
            "text": "\n".join([
                "A90WSTA151_TRACE_CLEANUP_BEGIN",
                "A90WSTA151 admin_keys_absent=1",
                "A90WSTA151 dropbear_absent=1",
                "A90WSTA151 trace_dir_absent=1",
                "A90WSTA151_TRACE_CLEANUP_DONE",
            ])
        })
        result = {"trace_cleanup_parse": parsed}
        checks = {
            "explicit_live_gate": True,
            "local_image_present": True,
            "local_image_sha_ok": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "remote_image_ready": True,
            "admin_trace_stage_script_uploaded": True,
            "chroot_mount_ready": True,
            "admin_trace_stage_pass": True,
            "admin_ssh_pass": True,
            "root_ssh_rejected": True,
            "trace_snapshot_pass": True,
            "trace_file_nonempty": True,
            "trace_snapshot_file_nonempty": True,
            "syscall_profile_nonempty": True,
            "syscall_core_observed": True,
            "syscall_accept_observed": False,
            "dropbear_log_policy_clean": True,
            "trace_artifact_saved": False,
            "trace_cleanup_ok": False,
            "chroot_cleanup_ok": False,
            "final_selftest_fail_zero": False,
        }

        self.assertTrue(runner.trace_cleanup_ok(result))
        self.assertEqual(
            runner.classify({"checks": checks}),
            "wsta151-blocked-accept-syscall-missing",
        )

    def test_default_gate_blocks_without_device_action(self) -> None:
        with tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE) as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "run"),
            ]))

        self.assertEqual(result["decision"], "wsta151-blocked-dropbear-admin-syscall-trace-live-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])

    def test_source_is_bounded_and_uses_wsta120_admin_model(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("run_wsta120_dropbear_admin_live_gate", source)
        self.assertIn("run_wsta119_dropbear_admin_model", source)
        self.assertIn("ack_private_trace_artifact", source)
        self.assertIn("root_ssh_rejected", source)
        self.assertIn("dropbear-admin-usb-daemon", source)
        self.assertIn("WSTA115_STRACE_IMAGE", source)
        self.assertNotIn("native_init_flash.py", source)


if __name__ == "__main__":
    unittest.main()
