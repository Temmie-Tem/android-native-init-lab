from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta114_syscall_trace_chroot_profile.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta114_syscall_trace_chroot_profile.py")


class ServerDistroWsta114SyscallTraceChrootProfileTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            execute_syscall_trace_chroot_live=False,
            allow_syscall_trace_live=False,
            ack_private_trace_artifact=False,
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta114-blocked-syscall-trace-chroot-live-required"),
        )

        args.execute_syscall_trace_chroot_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta114-blocked-syscall-trace-live-allow-required"),
        )

        args.allow_syscall_trace_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta114-blocked-private-trace-artifact-ack-required"),
        )

        args.ack_private_trace_artifact = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta114"),
            ]))
            saved = json.loads((root / "wsta114" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta114-blocked-syscall-trace-chroot-live-required")
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
        ):
            self.assertFalse(result["safety"][key])

    def test_syscall_trace_marker_stage_script_merges_wsta113_markers(self) -> None:
        script = runner.syscall_trace_marker_stage_script()

        self.assertIn("A90WSTA114_SYSCALL_TRACE_MARKER_STAGE_BEGIN", script)
        self.assertIn("syscall-trace-tool=/usr/bin/strace", script)
        self.assertIn("syscall-trace-target=dpublic-smoke-httpd", script)
        self.assertIn("syscall-trace-profile-source=deferred-WSTA114", script)
        self.assertIn("syscall-trace-public-default=off", script)
        self.assertIn("grep -v -E", script)
        self.assertIn("A90WSTA114_SYSCALL_TRACE_MARKER_STAGE_DONE", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_trace_probe_script_runs_strace_around_smoke_service(self) -> None:
        script = runner.trace_probe_script()

        self.assertIn("A90WSTA114_TRACE_BEGIN", script)
        self.assertIn("cloudflared-quick-enable", script)
        self.assertIn("A90WSTA114_PUBLIC_ENABLE_ABSENT=1", script)
        self.assertIn("command -v strace", script)
        self.assertIn("-o \"$TRACE\" \"$LAUNCHER\" dpublic-smoke-httpd \"$SMOKE\" 127.0.0.1 8080", script)
        self.assertIn("A90WSTA114_LOOPBACK_GET_OK=1", script)
        self.assertIn("A90WSTA114_SMOKE_NO_NEW_PRIVS=", script)
        self.assertIn("A90WSTA114_SMOKE_CAP_EFF=", script)
        self.assertIn("A90WSTA114_SYSCALL_HAS_EXECVE=1", script)
        self.assertIn("A90WSTA114_SYSCALL_HAS_SOCKET=1", script)
        self.assertIn("A90WSTA114_SYSCALL_HAS_BIND=1", script)
        self.assertIn("A90WSTA114_SYSCALL_HAS_LISTEN=1", script)
        self.assertIn("A90WSTA114_SYSCALL_LIST_BEGIN", script)
        self.assertIn("A90WSTA114_TRACE_DONE", script)
        self.assertNotIn("cloudflared tunnel", script)
        self.assertNotIn("iptables -A", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_parse_trace_probe_requires_public_off_loopback_and_core_syscalls(self) -> None:
        stdout = "\n".join([
            "A90WSTA114_TRACE_BEGIN",
            "A90WSTA114_PROC_MOUNTED=1",
            "A90WSTA114_PUBLIC_ENABLE_ABSENT=1",
            "A90WSTA114_LAUNCHER_PRESENT=1",
            "A90WSTA114_POLICY_PRESENT=1",
            "A90WSTA114_SMOKE_PRESENT=1",
            "A90WSTA114_HTTP_GET_PRESENT=1",
            "A90WSTA114_SETPRIV_PRESENT=1",
            "A90WSTA114_STRACE_PRESENT=1",
            "A90WSTA114_TRACE_PROCESS_STARTED=1",
            "A90WSTA114_SMOKE_PID_FOUND=1",
            "A90WSTA114_SMOKE_NO_NEW_PRIVS=1",
            "A90WSTA114_SMOKE_CAP_EFF=0000000000000000",
            "A90WSTA114_LOOPBACK_GET_OK=1",
            "A90WSTA114_LAUNCHER_EXEC_LOGGED=1",
            "A90WSTA114_TRACE_FILE_NONEMPTY=1",
            "A90WSTA114_SYSCALL_PROFILE_NONEMPTY=1",
            "A90WSTA114_SYSCALL_HAS_EXECVE=1",
            "A90WSTA114_SYSCALL_HAS_SOCKET=1",
            "A90WSTA114_SYSCALL_HAS_BIND=1",
            "A90WSTA114_SYSCALL_HAS_LISTEN=1",
            "A90WSTA114_SYSCALL_LIST_BEGIN",
            "bind",
            "close",
            "execve",
            "listen",
            "socket",
            "A90WSTA114_SYSCALL_LIST_END",
            "A90WSTA114_PROC_UNMOUNTED=1",
            "A90WSTA114_TRACE_DONE",
        ])

        parsed = runner.parse_trace_probe({"stdout": stdout})

        self.assertTrue(parsed["proof_done"])
        self.assertTrue(parsed["public_enable_absent"])
        self.assertTrue(parsed["strace_present"])
        self.assertTrue(parsed["loopback_get_ok"])
        self.assertTrue(parsed["smoke_no_new_privs"])
        self.assertTrue(parsed["smoke_cap_eff_zero"])
        self.assertTrue(parsed["core_syscalls_observed"])
        self.assertEqual(parsed["syscall_names"], ["bind", "close", "execve", "listen", "socket"])
        self.assertEqual(parsed["syscall_count"], 5)

        missing_bind = runner.parse_trace_probe({"stdout": stdout.replace("bind\n", "")})
        self.assertFalse(missing_bind["core_syscalls_observed"])

    def test_syscall_profile_is_private_smoke_service_only(self) -> None:
        parsed = {
            "public_enable_absent": True,
            "loopback_get_ok": True,
            "smoke_no_new_privs": True,
            "smoke_cap_eff_zero": True,
            "core_syscalls_observed": True,
            "syscall_count": 4,
            "syscall_names": ["bind", "execve", "listen", "socket"],
        }

        profile = runner.syscall_profile(parsed, {"all_saved": True})

        self.assertEqual(profile["schema"], "a90-wsta114-syscall-profile-v1")
        self.assertEqual(profile["service"], "dpublic-smoke-httpd")
        self.assertEqual(profile["scope"], "smoke-service-only")
        self.assertTrue(profile["public_default_off"])
        self.assertTrue(profile["loopback_get_ok"])
        self.assertTrue(profile["core_syscalls_observed"])
        self.assertEqual(profile["trace_artifacts"], {"all_saved": True})
        self.assertFalse(profile["public_url_value_logged"])
        self.assertEqual(profile["secret_values_logged"], 0)

    def test_fetch_remote_file_saves_private_artifact_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            local = run_dir / "trace.out"
            args = SimpleNamespace(ssh_port=2222, ssh_connect_timeout=1, device_ip="192.0.2.2")
            completed = SimpleNamespace(
                returncode=0,
                stdout=b"execve(...)\n",
                stderr=b"",
            )
            with mock.patch.object(runner.subprocess, "run", return_value=completed) as run_call:
                record = runner.fetch_remote_file(
                    args,
                    run_dir,
                    "/tmp/a90-wsta114-syscall-trace/smoke.strace",
                    local,
                    timeout=5.0,
                )
                self.assertTrue(local.is_file())

        remote_script = run_call.call_args.args[0][-1]
        self.assertTrue(record["saved"])
        self.assertEqual(record["size_bytes"], len(b"execve(...)\n"))
        self.assertIn("/bin/cat /tmp/a90-wsta114-syscall-trace/smoke.strace", remote_script)
        self.assertEqual(record["secret_values_logged"], 0)

    def test_classify_requires_trace_profile_and_cleanup(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "local_image_present": True,
            "dpublic_helpers_built": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "remote_image_ready": True,
            "chroot_mount_ready": True,
            "dropbear_started": True,
            "debian_ssh_marker": True,
            "service_hardening_assets_staged": True,
            "dpublic_helpers_staged": True,
            "syscall_trace_marker_staged": True,
            "public_default_off": True,
            "strace_present": True,
            "smoke_binaries_present": True,
            "trace_started": True,
            "loopback_get_ok": True,
            "trace_file_nonempty": True,
            "syscall_profile_nonempty": True,
            "syscall_core_observed": True,
            "trace_artifact_saved": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta114-blocked-explicit-live-gate"),
            ("strace_present", "wsta114-blocked-strace-missing"),
            ("loopback_get_ok", "wsta114-blocked-loopback-get"),
            ("syscall_core_observed", "wsta114-blocked-core-syscalls-missing"),
            ("trace_artifact_saved", "wsta114-blocked-trace-artifact-save"),
            ("chroot_cleanup_ok", "wsta114-blocked-chroot-cleanup"),
            ("final_selftest_fail_zero", "wsta114-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)

    def test_source_preserves_wsta_live_safety_boundaries(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('"boot_flash": False', source)
        self.assertIn('"wifi_connect": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn("build_dpublic_helpers", source)
        self.assertIn("stage_loopback_binaries", source)
        self.assertIn("stage_service_hardening_assets", source)
        self.assertIn("wsta94_mount_script", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("iptables -A", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
