from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta156_seccomp_nonloaded_filter_artifact.py")


class ServerDistroWsta156SeccompNonloadedFilterArtifactTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def service(self, name: str, allowlist: list[str]) -> dict:
        return {
            "service": name,
            "profile_name": f"seccomp-{name}-observed-v1",
            "source_state": f"{name}-live-proven",
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
                "reason": "source-only fixture",
            },
            "identity": {
                "user": "a90svc",
                "uid": 3901,
                "gid": 3901,
            },
            "network_scope": "test-scope",
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def source_policy(self) -> dict:
        return {
            "schema": "a90-wsta153-seccomp-policy-source-v1",
            "state": "SECCOMP_POLICY_DRAFT_FROM_LIVE_BASELINES",
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
                    "reason": "native Wi-Fi boundary",
                },
                {
                    "name": "native-dpublic-hud-presenter",
                    "reason": "native KMS boundary",
                },
            ],
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def test_valid_policy_compiles_nonloaded_aarch64_filter_artifact(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta156"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-nonloaded-filter-artifact",
            ]))
            manifest = json.loads((root / "wsta156" / runner.MANIFEST_NAME).read_text(encoding="utf-8"))
            c_source = (root / "wsta156" / runner.C_SOURCE_NAME).read_text(encoding="utf-8")
            object_exists = (root / "wsta156" / runner.OBJECT_NAME).is_file()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(object_exists)
        self.assertEqual(manifest["state"], "SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED")
        self.assertFalse(manifest["loaded"])
        self.assertFalse(manifest["enforced"])
        self.assertEqual(manifest["audit_arch"]["value"], runner.AUDIT_ARCH_AARCH64)
        services = {item["service"]: item for item in manifest["services"]}
        self.assertEqual(services["dpublic-hud-intent"]["resolved_count"], 5)
        self.assertEqual(services["dpublic-hud-intent"]["instruction_count"], 13)
        self.assertIn("allow openat", c_source)
        self.assertIn("BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)", c_source)
        self.assertIn("A90_SECCOMP_ERRNO_EPERM", c_source)
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])
        self.assertFalse(result["safety"]["seccomp_enforced"])

    def test_gate_blocks_without_explicit_flag_or_private_paths(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta156"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
            ]))
        self.assertEqual(result["decision"], "wsta156-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy_path = root / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta156"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-nonloaded-filter-artifact",
            ]))
        self.assertEqual(result["decision"], "wsta156-blocked-nonprivate-run-dir")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            policy_path = Path(outside) / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta156"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-nonloaded-filter-artifact",
            ]))
        self.assertEqual(result["decision"], "wsta156-blocked-policy-json-nonprivate")

    def test_unresolved_syscall_blocks_filter_artifact(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            policy = self.source_policy()
            policy["services"][0]["allowlist"].append("definitely_not_a_syscall")
            policy["services"][0]["allowlist_count"] = len(policy["services"][0]["allowlist"])
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, policy)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta156"),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--emit-seccomp-nonloaded-filter-artifact",
            ]))
        self.assertEqual(result["decision"], "wsta156-blocked-syscall-resolution-failed")


if __name__ == "__main__":
    unittest.main()
