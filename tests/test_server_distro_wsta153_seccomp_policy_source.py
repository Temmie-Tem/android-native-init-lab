from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta153_seccomp_policy_source.py")


class ServerDistroWsta153SeccompPolicySourceTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def source_status(self) -> dict:
        return {
            "decision": runner.wsta108.PASS_DECISION,
            "server_status": {
                "state": "SERVER_PROFILE_READY_DEFAULT_OFF",
                "hardening": {
                    "global_policy": {
                        "seccomp_ready_for_profile_source": True,
                    },
                    "syscall_trace_proof": {
                        "state": "SMOKE_SERVICE_SYSCALL_TRACE_LIVE_PROVEN",
                        "proof_run_dir": "workspace/private/runs/server-distro/wsta114-test",
                        "service": "dpublic-smoke-httpd",
                        "smoke_syscall_trace_live_proven": True,
                        "syscall_count": 5,
                        "syscall_names": ["write", "execve", "socket", "bind", "listen"],
                        "remaining_profiles": [],
                        "no_new_privs": True,
                        "cap_eff_zero": True,
                        "trace_artifacts_saved": True,
                    },
                    "cloudflared_runtime": {
                        "state": "CLOUDFLARED_RUNTIME_LIVE_PROVEN",
                        "proof_run_dir": "workspace/private/runs/server-distro/wsta125-test",
                        "service": "cloudflared-quick-tunnel",
                        "cloudflared_live_proven": True,
                        "user": "a90tunnel",
                        "uid": 3902,
                        "gid": 3902,
                        "syscall_count": 4,
                        "syscall_names": ["connect", "execve", "socket", "write"],
                        "no_new_privs": True,
                        "cap_eff_zero": True,
                        "trace_artifacts_saved": True,
                    },
                    "dropbear_admin_syscall_trace_proof": {
                        "state": "DROPBEAR_ADMIN_SYSCALL_TRACE_LIVE_PROVEN",
                        "proof_run_dir": "workspace/private/runs/server-distro/wsta151-test",
                        "service": "dropbear-admin-usb",
                        "dropbear_admin_syscall_trace_live_proven": True,
                        "daemon_privilege_model": "root-boundary-auth-daemon",
                        "network_scope": "usb-ncm-admin-only",
                        "uid": 3903,
                        "gid": 3903,
                        "syscall_count": 5,
                        "syscall_names": ["accept", "execve", "socket", "bind", "listen"],
                        "trace_artifacts_saved": True,
                    },
                    "hud_presenter_model": {
                        "intent_syscall_trace_proof": {
                            "state": "DPUBLIC_HUD_INTENT_SYSCALL_TRACE_LIVE_PROVEN",
                            "proof_run_dir": "workspace/private/runs/server-distro/wsta149-test",
                            "service": "dpublic-hud",
                            "hud_intent_syscall_trace_live_proven": True,
                            "uid": 3904,
                            "gid": 3904,
                            "syscall_count": 5,
                            "syscall_names": ["renameat", "fsync", "execve", "openat", "write"],
                            "no_new_privs": True,
                            "cap_eff_zero": True,
                            "trace_artifacts_saved": True,
                        },
                    },
                },
            },
        }

    def test_valid_status_emits_source_only_default_deny_policy(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            self.write_json(status_path, self.source_status())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta153"),
                "--wsta108-operator-status-json",
                str(status_path),
                "--emit-seccomp-policy-source",
            ]))
            policy = json.loads((root / "wsta153" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(policy["schema"], "a90-wsta153-seccomp-policy-source-v1")
        self.assertEqual(policy["state"], "SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES")
        self.assertEqual(policy["enforcement_state"], "SOURCE_ONLY_NOT_ENFORCED")
        self.assertEqual(policy["service_count"], 4)
        services = {item["service"]: item for item in policy["services"]}
        self.assertEqual(set(services), {
            "dpublic-smoke-httpd",
            "cloudflared-quick-tunnel",
            "dropbear-admin-usb",
            "dpublic-hud-intent",
        })
        self.assertTrue(all(item["deny_by_default"] for item in services.values()))
        self.assertTrue(all(item["enforcement"]["enabled"] is False for item in services.values()))
        self.assertEqual(services["dpublic-smoke-httpd"]["allowlist"], sorted(services["dpublic-smoke-httpd"]["allowlist"]))
        self.assertIn("connect", services["cloudflared-quick-tunnel"]["allowlist"])
        self.assertIn("accept", services["dropbear-admin-usb"]["allowlist"])
        self.assertIn("renameat", services["dpublic-hud-intent"]["allowlist"])
        self.assertIn("wsta-native-uplink-helper", json.dumps(policy["excluded_boundaries"], sort_keys=True))
        self.assertFalse(result["safety"]["seccomp_enforced"])
        self.assertTrue(result["checks"]["policy_all_allowlists_nonempty"])

    def test_status_must_have_all_profiles_and_empty_remaining_list(self) -> None:
        status = self.source_status()
        status["server_status"]["hardening"]["syscall_trace_proof"]["remaining_profiles"] = ["dropbear-admin-usb"]
        self.assertFalse(runner.validate_status(status)["remaining_syscall_profiles_retired"])

        status = self.source_status()
        status["server_status"]["hardening"]["cloudflared_runtime"]["syscall_names"] = []
        self.assertFalse(runner.validate_status(status)["all_sources_have_full_syscall_lists"])

    def test_default_nonprivate_and_not_ready_status_block(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            self.write_json(status_path, self.source_status())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta153"),
                "--wsta108-operator-status-json",
                str(status_path),
            ]))
        self.assertEqual(result["decision"], "wsta153-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "wsta108_operator_server_status.json"
            self.write_json(status_path, self.source_status())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta153"),
                "--wsta108-operator-status-json",
                str(status_path),
                "--emit-seccomp-policy-source",
            ]))
        self.assertEqual(result["decision"], "wsta153-blocked-nonprivate-run-dir")

        with self.private_tmp() as tmp:
            root = Path(tmp)
            status = self.source_status()
            status["server_status"]["hardening"]["global_policy"]["seccomp_ready_for_profile_source"] = False
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            self.write_json(status_path, status)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta153"),
                "--wsta108-operator-status-json",
                str(status_path),
                "--emit-seccomp-policy-source",
            ]))
        self.assertEqual(result["decision"], "wsta153-blocked-status-not-ready-for-seccomp-policy")


if __name__ == "__main__":
    unittest.main()
