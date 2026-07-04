from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta129_dpublic_hud_live_gate.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta129_dpublic_hud_live_gate.py")


class ServerDistroWsta129DpublicHudLiveGateTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def test_explicit_live_gate_requires_all_acks(self) -> None:
        args = SimpleNamespace(
            execute_hud_live=False,
            allow_hud_live=False,
            ack_drm_control=False,
            ack_private_trace_artifact=False,
            ack_runtime_cleanup=False,
        )
        self.assertEqual(runner.explicit_live_gate(args), (False, "wsta129-blocked-hud-live-required"))

        args.execute_hud_live = True
        self.assertEqual(runner.explicit_live_gate(args), (False, "wsta129-blocked-hud-live-allow-required"))

        args.allow_hud_live = True
        self.assertEqual(runner.explicit_live_gate(args), (False, "wsta129-blocked-drm-control-ack-required"))

        args.ack_drm_control = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta129-blocked-private-trace-artifact-ack-required"),
        )

        args.ack_private_trace_artifact = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta129-blocked-runtime-cleanup-ack-required"),
        )

        args.ack_runtime_cleanup = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta129"),
            ]))
            saved = json.loads((root / "wsta129" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta129-blocked-hud-live-required")
        self.assertEqual(saved["decision"], result["decision"])
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "public_smoke",
            "external_ping",
            "packet_filter_mutation",
            "userdata_touch",
            "switch_root",
            "drm_open",
            "kms_setcrtc",
        ):
            self.assertFalse(result["safety"][key])

    def test_stage_hud_binary_uploads_to_service_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hud = root / "a90-dpublic-hud"
            hud.write_bytes(b"hud")
            args = SimpleNamespace(hud=hud, hud_stage_timeout=3.0)
            with mock.patch.object(
                runner.wsta42,
                "ssh_write_file",
                return_value={"staged": True, "returncode": 0},
            ) as write_file:
                record = runner.stage_hud_binary(args, root)

        write_file.assert_called_once()
        self.assertEqual(write_file.call_args.args[2], hud)
        self.assertEqual(write_file.call_args.args[3], runner.REMOTE_HUD)
        self.assertTrue(record["staged"])
        self.assertEqual(record["service"], "dpublic-hud")
        self.assertEqual(record["secret_values_logged"], 0)

    def test_hud_probe_script_is_drm_only_and_private_trace(self) -> None:
        script = runner.hud_probe_script(5)

        self.assertIn("A90WSTA129_HUD_PROBE_BEGIN", script)
        self.assertIn("A90WSTA129_SYS_MOUNTED=1", script)
        self.assertIn("A90WSTA129_SYS_UNMOUNTED=1", script)
        self.assertIn("cloudflared-quick-enable", script)
        self.assertIn("A90WSTA129_PUBLIC_ENABLE_ABSENT=1", script)
        self.assertIn("command -v strace", script)
        self.assertIn("/dev/dri/card0", script)
        self.assertIn("A90WSTA129_DRM_SYSFS_PRESENT=1", script)
        self.assertIn("A90WSTA129_DRM_NODE_POLICY_APPLIED=1", script)
        self.assertIn("dpublic-hud", script)
        self.assertIn("a90-dpublic-hud", script)
        self.assertIn("A90WSTA129_SOCKET_FD_ABSENT=1", script)
        self.assertIn("A90WSTA129_DRM_FD_PRESENT=1", script)
        self.assertIn("A90WSTA129_HUD_SETCRTC_PERMISSION_DENIED=1", script)
        self.assertIn("A90WSTA129_HUD_PROBE_BLOCKED", script)
        self.assertIn("A90WSTA129_SYSCALL_HAS_IOCTL=1", script)
        self.assertIn("A90WSTA129_SYSCALL_NETWORK_ABSENT=1", script)
        self.assertIn("A90WSTA129_SYSCALL_LIST_BEGIN", script)
        self.assertIn("A90WSTA129_DRM_NODE_RESTORED=1", script)
        self.assertIn("A90WSTA129_HUD_PROBE_DONE", script)
        self.assertNotIn("cloudflared tunnel", script)
        self.assertNotIn("iptables -A", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_parse_hud_probe_requires_nonroot_no_network_drm_and_core_syscalls(self) -> None:
        stdout = "\n".join([
            "A90WSTA129_HUD_PROBE_BEGIN",
            "A90WSTA129_PROC_MOUNTED=1",
            "A90WSTA129_SYS_MOUNTED=1",
            "A90WSTA129_PUBLIC_ENABLE_ABSENT=1",
            "A90WSTA129_LAUNCHER_PRESENT=1",
            "A90WSTA129_POLICY_PRESENT=1",
            "A90WSTA129_HUD_BINARY_PRESENT=1",
            "A90WSTA129_SETPRIV_PRESENT=1",
            "A90WSTA129_STRACE_PRESENT=1",
            "A90WSTA129_DRM_SYSFS_PRESENT=1",
            "A90WSTA129_DRM_NODE_PRESENT=1",
            "A90WSTA129_DRM_NODE_POLICY_APPLIED=1",
            "A90WSTA129_TRACE_PROCESS_STARTED=1",
            "A90WSTA129_HUD_PID_FOUND=1",
            "A90WSTA129_HUD_UID_REAL=3904",
            "A90WSTA129_HUD_UID_EFFECTIVE=3904",
            "A90WSTA129_HUD_GID_REAL=3904",
            "A90WSTA129_HUD_GID_EFFECTIVE=3904",
            "A90WSTA129_HUD_NO_NEW_PRIVS=1",
            "A90WSTA129_HUD_CAP_EFF=0000000000000000",
            "A90WSTA129_SOCKET_FD_COUNT=0",
            "A90WSTA129_SOCKET_FD_ABSENT=1",
            "A90WSTA129_DRM_FD_PRESENT=1",
            "A90WSTA129_LAUNCHER_EXEC_LOGGED=1",
            "A90WSTA129_LAUNCHER_SERVICE_LOGGED=1",
            "A90WSTA129_LAUNCHER_USER_LOGGED=1",
            "A90WSTA129_TRACE_FILE_NONEMPTY=1",
            "A90WSTA129_SYSCALL_PROFILE_NONEMPTY=1",
            "A90WSTA129_SYSCALL_NETWORK_ABSENT=1",
            "A90WSTA129_DRM_NODE_RESTORED=1",
            "A90WSTA129_SYSCALL_LIST_BEGIN",
            "close",
            "execve",
            "ioctl",
            "mmap",
            "munmap",
            "openat",
            "read",
            "A90WSTA129_SYSCALL_LIST_END",
            "A90WSTA129_SYS_UNMOUNTED=1",
            "A90WSTA129_PROC_UNMOUNTED=1",
            "A90WSTA129_HUD_PROBE_DONE",
        ])

        parsed = runner.parse_hud_probe({"stdout": stdout})

        self.assertTrue(parsed["proof_done"])
        self.assertTrue(parsed["sys_mounted"])
        self.assertTrue(parsed["sys_unmounted"])
        self.assertTrue(parsed["public_enable_absent"])
        self.assertTrue(parsed["drm_node_policy_applied"])
        self.assertTrue(parsed["drm_node_restored"])
        self.assertTrue(parsed["hud_uid_real"])
        self.assertTrue(parsed["hud_uid_effective"])
        self.assertTrue(parsed["hud_gid_real"])
        self.assertTrue(parsed["hud_gid_effective"])
        self.assertTrue(parsed["hud_no_new_privs"])
        self.assertTrue(parsed["hud_cap_eff_zero"])
        self.assertTrue(parsed["hud_socket_fd_absent"])
        self.assertTrue(parsed["hud_drm_fd_present"])
        self.assertTrue(parsed["network_syscalls_absent"])
        self.assertTrue(parsed["core_syscalls_observed"])
        self.assertEqual(parsed["syscall_names"], ["close", "execve", "ioctl", "mmap", "munmap", "openat", "read"])

        with_socket = runner.parse_hud_probe({"stdout": stdout.replace("read\n", "read\nsocket\n")})
        self.assertFalse(with_socket["network_syscalls_absent"])

        missing_ioctl = runner.parse_hud_probe({"stdout": stdout.replace("ioctl\n", "")})
        self.assertFalse(missing_ioctl["core_syscalls_observed"])

    def test_hud_runtime_profile_is_no_network_drm_runtime_only(self) -> None:
        parsed = {
            "public_enable_absent": True,
            "hud_uid_real": True,
            "hud_uid_effective": True,
            "hud_gid_real": True,
            "hud_gid_effective": True,
            "hud_no_new_privs": True,
            "hud_cap_eff_zero": True,
            "hud_socket_fd_absent": True,
            "network_syscalls_absent": True,
            "drm_node_policy_applied": True,
            "drm_node_restored": True,
            "hud_drm_fd_present": True,
            "core_syscalls_observed": True,
            "syscall_count": 5,
            "syscall_names": ["execve", "ioctl", "mmap", "munmap", "openat"],
        }

        profile = runner.hud_runtime_profile(parsed, {"all_saved": True})

        self.assertEqual(profile["schema"], "a90-wsta129-dpublic-hud-runtime-profile-v1")
        self.assertEqual(profile["service"], "dpublic-hud")
        self.assertEqual(profile["scope"], "hud-drm-runtime-only")
        self.assertTrue(profile["uid_gid_3904"])
        self.assertTrue(profile["no_socket_fd"])
        self.assertTrue(profile["no_network_syscalls"])
        self.assertTrue(profile["drm_fd_present"])
        self.assertEqual(profile["trace_artifacts"], {"all_saved": True})
        self.assertFalse(profile["public_url_value_logged"])
        self.assertEqual(profile["secret_values_logged"], 0)

    def test_parse_hud_probe_preserves_setcrtc_permission_boundary(self) -> None:
        stdout = "\n".join([
            "A90WSTA129_HUD_PROBE_BEGIN",
            "A90WSTA129_PROC_MOUNTED=1",
            "A90WSTA129_SYS_MOUNTED=1",
            "A90WSTA129_PUBLIC_ENABLE_ABSENT=1",
            "A90WSTA129_LAUNCHER_PRESENT=1",
            "A90WSTA129_POLICY_PRESENT=1",
            "A90WSTA129_HUD_BINARY_PRESENT=1",
            "A90WSTA129_SETPRIV_PRESENT=1",
            "A90WSTA129_STRACE_PRESENT=1",
            "A90WSTA129_DRM_SYSFS_PRESENT=1",
            "A90WSTA129_DRM_NODE_PRESENT=1",
            "A90WSTA129_DRM_NODE_POLICY_APPLIED=1",
            "A90WSTA129_TRACE_PROCESS_STARTED=1",
            "A90WSTA129_HUD_EXITED_EARLY=1",
            "a90_service_launcher_decision=exec",
            "a90_service_launcher_service=dpublic-hud",
            "a90_service_launcher_user=a90hud",
            "setcrtc: Permission denied",
            "A90WSTA129_LAUNCHER_EXEC_LOGGED=1",
            "A90WSTA129_LAUNCHER_SERVICE_LOGGED=1",
            "A90WSTA129_LAUNCHER_USER_LOGGED=1",
            "A90WSTA129_HUD_SETCRTC_PERMISSION_DENIED=1",
            "A90WSTA129_TRACE_FILE_NONEMPTY=1",
            "A90WSTA129_SYSCALL_PROFILE_NONEMPTY=1",
            "A90WSTA129_SYSCALL_NETWORK_ABSENT=1",
            "A90WSTA129_SYSCALL_LIST_BEGIN",
            "execve",
            "ioctl",
            "mmap",
            "munmap",
            "openat",
            "A90WSTA129_SYSCALL_LIST_END",
            "A90WSTA129_DRM_NODE_RESTORED=1",
            "A90WSTA129_SYS_UNMOUNTED=1",
            "A90WSTA129_PROC_UNMOUNTED=1",
            "A90WSTA129_HUD_PROBE_BLOCKED",
        ])

        parsed = runner.parse_hud_probe({"stdout": stdout})
        self.assertTrue(parsed["hud_exited_early"])
        self.assertTrue(parsed["hud_setcrtc_permission_denied"])
        self.assertTrue(parsed["proof_blocked"])
        self.assertTrue(parsed["launcher_exec_logged"])
        self.assertTrue(parsed["trace_file_nonempty"])
        self.assertTrue(parsed["syscall_profile_nonempty"])
        self.assertTrue(parsed["core_syscalls_observed"])

    def test_classify_requires_hud_runtime_proof_and_cleanup(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "local_image_present": True,
            "hud_binary_present_local": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "remote_image_ready": True,
            "chroot_mount_ready": True,
            "dropbear_started": True,
            "debian_ssh_marker": True,
            "service_hardening_assets_staged": True,
            "hud_binary_staged": True,
            "hud_probe_completed": True,
            "public_default_off": True,
            "strace_present": True,
            "drm_node_policy_applied": True,
            "trace_started": True,
            "hud_setcrtc_permission_ok": True,
            "hud_uid_gid_pass": True,
            "hud_no_new_privs_pass": True,
            "hud_cap_eff_zero_pass": True,
            "hud_no_network_pass": True,
            "hud_drm_node_observed": True,
            "trace_file_nonempty": True,
            "syscall_profile_nonempty": True,
            "syscall_core_observed": True,
            "trace_artifact_saved": True,
            "runtime_cleanup_ok": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta129-blocked-explicit-live-gate"),
            ("hud_binary_present_local", "wsta129-blocked-hud-binary-missing"),
            ("hud_probe_completed", "wsta129-blocked-hud-probe"),
            ("hud_setcrtc_permission_ok", "wsta129-blocked-hud-setcrtc-permission"),
            ("hud_no_network_pass", "wsta129-blocked-hud-network"),
            ("hud_drm_node_observed", "wsta129-blocked-hud-drm-node"),
            ("trace_artifact_saved", "wsta129-blocked-trace-artifact-save"),
            ("runtime_cleanup_ok", "wsta129-blocked-runtime-cleanup"),
            ("final_selftest_fail_zero", "wsta129-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)

    def test_source_preserves_hud_live_safety_boundaries(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--execute-hud-live", template["command"])
        self.assertIn("--ack-drm-control", template["command"])
        self.assertIn("--ack-private-trace-artifact", template["command"])
        self.assertIn("--ack-runtime-cleanup", template["command"])
        self.assertFalse(template["boot_flash"])
        self.assertFalse(template["native_reboot"])
        self.assertFalse(template["public_tunnel"])
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"wifi_connect": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn("stage_service_hardening_assets", source)
        self.assertIn("stage_hud_binary", source)
        self.assertIn("wsta94_mount_script", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("iptables -A", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
