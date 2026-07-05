from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta154_seccomp_launcher_gate_model.py")


class ServerDistroWsta154SeccompLauncherGateModelTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def service(self, name: str, allowlist: list[str]) -> dict:
        profile_suffix = name.replace("_", "-")
        return {
            "service": name,
            "profile_name": f"seccomp-{profile_suffix}-observed-v1",
            "source_state": f"{name}-live-proven",
            "source_proof_run_dir": f"workspace/private/runs/server-distro/{name}-test",
            "architecture": "aarch64",
            "profile_class": "observed-live-baseline",
            "default_action": "ERRNO(EPERM)",
            "allowlist": allowlist,
            "allowlist_count": len(allowlist),
            "observed_syscall_count": len(allowlist),
            "deny_by_default": True,
            "kill_process_on_violation": False,
            "enforcement": {
                "enabled": False,
                "reason": "source policy only",
                "next_gate": "WSTA154",
            },
            "identity": {
                "user": "a90svc",
                "uid": 3901,
                "gid": 3901,
            },
            "network_scope": "test-scope",
            "no_new_privs": True,
            "cap_eff_zero": True,
            "trace_artifacts_saved": True,
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "notes": ["test fixture"],
        }

    def source_policy(self) -> dict:
        return {
            "schema": "a90-wsta153-seccomp-policy-source-v1",
            "state": "SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES",
            "source_status_json": "workspace/private/runs/server-distro/wsta153-test/wsta108.json",
            "enforcement_state": "SOURCE_ONLY_NOT_ENFORCED",
            "default_action": "ERRNO(EPERM)",
            "architecture": "aarch64",
            "services": [
                self.service("dpublic-smoke-httpd", ["bind", "execve", "listen", "write"]),
                self.service("cloudflared-quick-tunnel", ["connect", "execve", "socket", "write"]),
                self.service("dropbear-admin-usb", ["accept", "bind", "execve", "listen", "socket"]),
                self.service("dpublic-hud-intent", ["execve", "fsync", "openat", "renameat", "write"]),
            ],
            "service_count": 4,
            "excluded_boundaries": [
                {
                    "name": "wsta-native-uplink-helper",
                    "reason": "native Wi-Fi control",
                },
                {
                    "name": "native-dpublic-hud-presenter",
                    "reason": "native KMS owner",
                },
            ],
            "next_live_gate": {
                "required": True,
                "suggested_unit": "WSTA154",
                "scope": "launcher dry-run",
            },
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def run_valid_policy(self):
        with self.private_tmp() as tmp:
            root = Path(tmp)
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta154"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-launcher-gate-model",
            ]))
            model = json.loads((root / "wsta154" / runner.RESULT_NAME).read_text(encoding="utf-8"))
        return result, model

    def test_valid_policy_emits_dry_run_launcher_gate_model(self) -> None:
        result, model = self.run_valid_policy()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(model["schema"], runner.MODEL_SCHEMA)
        self.assertEqual(model["state"], runner.MODEL_STATE)
        self.assertEqual(model["enforcement_state"], runner.MODEL_ENFORCEMENT_STATE)
        self.assertFalse(model["launcher_integration"]["filter_load_enabled"])
        self.assertEqual(model["launcher_integration"]["mode"], "dry-run-before-filter-load")
        bindings = {item["launcher_service"]: item for item in model["service_bindings"]}
        self.assertEqual(set(bindings), {
            "dpublic-smoke-httpd",
            "cloudflared-quick-tunnel",
            "dropbear-admin-usb",
            "dpublic-hud",
        })
        self.assertEqual(bindings["dpublic-hud"]["policy_service"], "dpublic-hud-intent")
        self.assertTrue(all(item["filter_load"]["enabled"] is False for item in bindings.values()))
        self.assertIn("A90WSTA154_SECCOMP_DRY_RUN_ONLY=1", model["dry_run_global_markers"])
        self.assertTrue(result["checks"]["model_all_binding_dry_run_checks_pass"])
        self.assertFalse(result["safety"]["seccomp_enforced"])
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])

    def test_gate_blocks_without_explicit_flag_or_private_paths(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta154"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
            ]))
        self.assertEqual(result["decision"], "wsta154-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy_path = root / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta154"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-launcher-gate-model",
            ]))
        self.assertEqual(result["decision"], "wsta154-blocked-nonprivate-run-dir")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            policy_path = Path(outside) / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta154"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-launcher-gate-model",
            ]))
        self.assertEqual(result["decision"], "wsta154-blocked-policy-json-nonprivate")

    def test_policy_must_remain_source_only_complete_and_nonempty(self) -> None:
        mutations = []

        def enforcement_state(policy: dict) -> None:
            policy["enforcement_state"] = "ENFORCED"

        def missing_service(policy: dict) -> None:
            policy["services"] = policy["services"][:-1]
            policy["service_count"] = len(policy["services"])

        def empty_allowlist(policy: dict) -> None:
            policy["services"][0]["allowlist"] = []
            policy["services"][0]["allowlist_count"] = 0

        def profile_enforced(policy: dict) -> None:
            policy["services"][0]["enforcement"]["enabled"] = True

        mutations.extend([enforcement_state, missing_service, empty_allowlist, profile_enforced])
        for mutate in mutations:
            with self.subTest(mutation=mutate.__name__), self.private_tmp() as tmp:
                root = Path(tmp)
                policy = self.source_policy()
                mutate(policy)
                policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
                self.write_json(policy_path, policy)
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "wsta154"),
                    "--wsta153-seccomp-policy-json",
                    str(policy_path),
                    "--emit-seccomp-launcher-gate-model",
                ]))
            self.assertEqual(result["decision"], "wsta154-blocked-policy-not-ready-for-launcher-gate")

    def test_model_validation_catches_filter_load_regression(self) -> None:
        _, model = self.run_valid_policy()
        self.assertTrue(runner.validate_model(model)["filter_load_disabled"])
        model["launcher_integration"]["filter_load_enabled"] = True
        self.assertFalse(runner.validate_model(model)["filter_load_disabled"])


if __name__ == "__main__":
    unittest.main()
