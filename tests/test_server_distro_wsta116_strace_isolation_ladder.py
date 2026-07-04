from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta116_strace_isolation_ladder.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta116_strace_isolation_ladder.py")


class ServerDistroWsta116StraceIsolationLadderTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            execute_strace_isolation_live=False,
            allow_strace_isolation_live=False,
            ack_private_trace_artifact=False,
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta116-blocked-strace-isolation-live-required"),
        )

        args.execute_strace_isolation_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta116-blocked-strace-isolation-live-allow-required"),
        )

        args.allow_strace_isolation_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta116-blocked-private-trace-artifact-ack-required"),
        )

        args.ack_private_trace_artifact = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta116"),
            ]))
            saved = json.loads((root / "wsta116" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta116-blocked-strace-isolation-live-required")
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

    def test_isolation_probe_script_contains_three_ordered_strace_probes(self) -> None:
        script = runner.isolation_probe_script()

        self.assertIn("A90WSTA116_ISOLATION_BEGIN", script)
        self.assertIn("cloudflared-quick-enable", script)
        self.assertIn("A90WSTA116_PUBLIC_ENABLE_ABSENT=1", script)
        self.assertIn("A90WSTA116_PROC_UNMOUNT_DEFERRED=1", script)
        self.assertIn("command -v strace", script)
        self.assertIn('"$STRACE" -qq -f -s 96 -o "$DIRECT_TRACE" /bin/true', script)
        self.assertIn('"$STRACE" -qq -f -s 96 -o "$LAUNCHER_TRACE" "$LAUNCHER" dpublic-smoke-httpd /bin/true', script)
        self.assertIn('"$STRACE" -qq -f -s 96 -o "$SMOKE_TRACE" "$LAUNCHER" dpublic-smoke-httpd /bin/sh "$RUN_DIR/service-child.sh"', script)
        self.assertIn(': > "$RUN_DIR/smoke-server.log"', script)
        self.assertIn('/bin/chmod 0666 "$RUN_DIR/smoke-server.log"', script)
        self.assertIn("A90WSTA116_SMOKE_BG_SPAWNED=1", script)
        self.assertIn("A90WSTA116_SMOKE_BG_LOOPBACK_GET_OK=1", script)
        self.assertIn('echo "A90WSTA116_${name}_SYSCALL_LIST_BEGIN"', script)
        self.assertIn('emit_syscall_list DIRECT_TRUE "$DIRECT_SYSCALLS"', script)
        self.assertIn('emit_syscall_list LAUNCHER_TRUE "$LAUNCHER_SYSCALLS"', script)
        self.assertIn('emit_syscall_list SMOKE_BG "$SMOKE_SYSCALLS"', script)
        self.assertIn("A90WSTA116_ISOLATION_DONE", script)
        self.assertNotIn("cloudflared tunnel", script)
        self.assertNotIn("iptables -A", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_parse_isolation_probe_records_each_ladder_step(self) -> None:
        stdout = "\n".join([
            "A90WSTA116_ISOLATION_BEGIN",
            "A90WSTA116_PROC_MOUNTED=1",
            "A90WSTA116_PUBLIC_ENABLE_ABSENT=1",
            "A90WSTA116_LAUNCHER_PRESENT=1",
            "A90WSTA116_POLICY_PRESENT=1",
            "A90WSTA116_SMOKE_PRESENT=1",
            "A90WSTA116_HTTP_GET_PRESENT=1",
            "A90WSTA116_SETPRIV_PRESENT=1",
            "A90WSTA116_STRACE_PRESENT=1",
            "A90WSTA116_DIRECT_TRUE_RC=0",
            "A90WSTA116_DIRECT_TRUE_TRACE_NONEMPTY=1",
            "A90WSTA116_DIRECT_TRUE_HAS_EXECVE=1",
            "A90WSTA116_DIRECT_TRUE_SYSCALL_LIST_BEGIN",
            "execve",
            "exit_group",
            "A90WSTA116_DIRECT_TRUE_SYSCALL_LIST_END",
            "A90WSTA116_LAUNCHER_TRUE_RC=0",
            "A90WSTA116_LAUNCHER_TRUE_EXEC_LOGGED=1",
            "A90WSTA116_LAUNCHER_TRUE_TRACE_NONEMPTY=1",
            "A90WSTA116_LAUNCHER_TRUE_HAS_EXECVE=1",
            "A90WSTA116_LAUNCHER_TRUE_SYSCALL_LIST_BEGIN",
            "execve",
            "setresuid",
            "A90WSTA116_LAUNCHER_TRUE_SYSCALL_LIST_END",
            "A90WSTA116_SMOKE_BG_SPAWNED=1",
            "A90WSTA116_SMOKE_BG_DONE=1",
            "A90WSTA116_SMOKE_BG_LOOPBACK_GET_OK=1",
            "A90WSTA116_SMOKE_BG_EXEC_LOGGED=1",
            "A90WSTA116_SMOKE_BG_TRACE_NONEMPTY=1",
            "A90WSTA116_SMOKE_NO_NEW_PRIVS=1",
            "A90WSTA116_SMOKE_CAP_EFF=0000000000000000",
            "A90WSTA116_SMOKE_BG_SYSCALL_LIST_BEGIN",
            "bind",
            "execve",
            "listen",
            "socket",
            "A90WSTA116_SMOKE_BG_SYSCALL_LIST_END",
            "A90WSTA116_PROC_UNMOUNTED=1",
            "A90WSTA116_ISOLATION_DONE",
        ])

        parsed = runner.parse_isolation_probe({"stdout": stdout})

        self.assertTrue(parsed["proof_done"])
        self.assertTrue(parsed["direct_true_rc_zero"])
        self.assertTrue(parsed["launcher_true_exec_logged"])
        self.assertTrue(parsed["smoke_bg_loopback_get_ok"])
        self.assertTrue(parsed["smoke_core_syscalls_observed"])
        self.assertEqual(parsed["direct_true_syscalls"], ["execve", "exit_group"])
        self.assertEqual(parsed["launcher_true_syscalls"], ["execve", "setresuid"])
        self.assertEqual(parsed["smoke_bg_syscalls"], ["bind", "execve", "listen", "socket"])

        missing_socket = runner.parse_isolation_probe({"stdout": stdout.replace("socket\n", "")})
        self.assertFalse(missing_socket["smoke_core_syscalls_observed"])

    def test_run_isolation_probe_records_timeout_as_blocked_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            args = SimpleNamespace(
                ssh_port=2222,
                ssh_connect_timeout=1,
                device_ip="192.0.2.2",
                isolation_timeout=5.0,
            )
            timeout = runner.subprocess.TimeoutExpired(
                cmd=["ssh"],
                timeout=5.0,
                output=b"A90WSTA116_ISOLATION_BEGIN\n",
                stderr=b"timeout\n",
            )
            with mock.patch.object(runner.subprocess, "run", side_effect=timeout):
                record = runner.run_isolation_probe(args, run_dir)

        self.assertTrue(record["timed_out"])
        self.assertIsNone(record["returncode"])
        self.assertEqual(record["timeout_sec"], 5.0)
        self.assertIn("A90WSTA116_ISOLATION_BEGIN", record["stdout"])
        self.assertTrue(record["parsed"]["proof_begin"])
        self.assertFalse(record["parsed"]["proof_done"])

    def test_isolation_summary_is_private_diagnostic_not_public_profile(self) -> None:
        parsed = {
            "direct_true_rc_zero": True,
            "direct_true_trace_nonempty": True,
            "direct_true_has_execve": True,
            "direct_true_syscalls": ["execve"],
            "launcher_true_rc_zero": True,
            "launcher_true_exec_logged": True,
            "launcher_true_trace_nonempty": True,
            "launcher_true_has_execve": True,
            "launcher_true_syscalls": ["execve"],
            "smoke_bg_spawned": True,
            "smoke_bg_done": True,
            "smoke_bg_loopback_get_ok": True,
            "smoke_bg_exec_logged": True,
            "smoke_bg_trace_nonempty": True,
            "smoke_no_new_privs": True,
            "smoke_cap_eff_zero": True,
            "smoke_core_syscalls_observed": True,
            "smoke_bg_syscalls": ["bind", "execve", "listen", "socket"],
        }

        summary = runner.isolation_summary(parsed, {"all_required_saved": True})

        self.assertEqual(summary["schema"], "a90-wsta116-strace-isolation-v1")
        self.assertEqual(summary["scope"], "smoke-service-strace-timeout-isolation")
        self.assertTrue(summary["direct_true"]["rc_zero"])
        self.assertTrue(summary["launcher_true"]["exec_logged"])
        self.assertTrue(summary["smoke_background"]["core_syscalls_observed"])
        self.assertEqual(summary["trace_artifacts"], {"all_required_saved": True})
        self.assertFalse(summary["public_url_value_logged"])
        self.assertEqual(summary["secret_values_logged"], 0)

    def test_classify_orders_the_three_isolation_failures(self) -> None:
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
            "isolation_probe_completed": True,
            "public_default_off": True,
            "strace_present": True,
            "smoke_binaries_present": True,
            "direct_true_pass": True,
            "launcher_true_pass": True,
            "smoke_background_pass": True,
            "trace_artifacts_saved": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)

        for key, decision in (
            ("explicit_live_gate", "wsta116-blocked-explicit-live-gate"),
            ("isolation_probe_completed", "wsta116-blocked-isolation-timeout"),
            ("strace_present", "wsta116-blocked-strace-missing"),
            ("direct_true_pass", "wsta116-blocked-direct-true-strace"),
            ("launcher_true_pass", "wsta116-blocked-launcher-true-strace"),
            ("smoke_background_pass", "wsta116-blocked-smoke-background-strace"),
            ("trace_artifacts_saved", "wsta116-blocked-trace-artifact-save"),
            ("chroot_cleanup_ok", "wsta116-blocked-chroot-cleanup"),
            ("final_selftest_fail_zero", "wsta116-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)

    def test_source_preserves_wsta_live_safety_boundaries(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn('"boot_flash": False', source)
        self.assertIn('"wifi_connect": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"packet_filter_mutation": False', source)
        self.assertIn("stage_service_hardening_assets", source)
        self.assertIn("stage_loopback_binaries", source)
        self.assertIn("wsta94_mount_script", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("iptables -A", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())


if __name__ == "__main__":
    unittest.main()
