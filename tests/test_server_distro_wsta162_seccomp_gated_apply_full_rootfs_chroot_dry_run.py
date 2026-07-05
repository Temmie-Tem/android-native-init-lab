from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta162_seccomp_gated_apply_full_rootfs_chroot_dry_run.py")


class ServerDistroWsta162SeccompGatedApplyFullRootfsChrootDryRunTests(unittest.TestCase):
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
            "default_action": "ERRNO(EPERM)",
            "allowlist": allowlist,
            "allowlist_count": len(allowlist),
            "deny_by_default": True,
            "enforcement": {
                "enabled": False,
                "reason": "source-only fixture",
            },
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
                {"name": "wsta-native-uplink-helper"},
                {"name": "native-dpublic-hud-presenter"},
            ],
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def write_filter_artifact(self, root: Path) -> tuple[Path, Path]:
        object_path = root / "inputs" / "wsta156_seccomp_filters.o"
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_bytes(b"fake-wsta162-object")
        object_sha = hashlib.sha256(object_path.read_bytes()).hexdigest()
        manifest = {
            "schema": "a90-wsta156-seccomp-nonloaded-filter-artifact-v1",
            "state": "SECCOMP_FILTER_ARTIFACT_COMPILED_NOT_LOADED",
            "source_policy_schema": "a90-wsta153-seccomp-policy-source-v1",
            "source_policy_enforcement_state": "SOURCE_ONLY_NOT_ENFORCED",
            "service_count": 4,
            "loaded": False,
            "enforced": False,
            "artifact_sha256": {"object": object_sha},
            "services": [
                {"service": "dpublic-smoke-httpd", "instruction_count": 9, "missing_syscalls": []},
                {"service": "cloudflared-quick-tunnel", "instruction_count": 11, "missing_syscalls": []},
                {"service": "dropbear-admin-usb", "instruction_count": 13, "missing_syscalls": []},
                {"service": "dpublic-hud-intent", "instruction_count": 15, "missing_syscalls": []},
            ],
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }
        manifest_path = root / "inputs" / "wsta156_seccomp_filter_manifest.json"
        self.write_json(manifest_path, manifest)
        return manifest_path, object_path

    def write_wsta161_helper(self, root: Path) -> tuple[Path, Path]:
        helper = root / "inputs" / "a90-seccomp-loader-gated-apply"
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_bytes(b"fake-wsta161-helper")
        helper_sha = hashlib.sha256(helper.read_bytes()).hexdigest()
        manifest = {
            "schema": "a90-wsta161-seccomp-loader-gated-apply-helper-v1",
            "state": "SECCOMP_LOADER_GATED_APPLY_COMPILED_NOT_LOADED",
            "helper_sha256": helper_sha,
            "helper_file": "ELF 64-bit LSB executable, ARM aarch64, statically linked",
            "default_mode": "check-only",
            "apply_code_compiled": True,
            "default_load_enabled": False,
            "loaded": False,
            "enforced": False,
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }
        manifest_path = root / "inputs" / "wsta161_seccomp_loader_helper_manifest.json"
        self.write_json(manifest_path, manifest)
        return manifest_path, helper

    def test_valid_inputs_stage_wsta161_helper_and_prove_chroot_markers(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_rootfs = root / "source-rootfs"
            source_rootfs.mkdir()
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            filter_manifest, filter_object = self.write_filter_artifact(root)
            helper_manifest, helper_binary = self.write_wsta161_helper(root)
            dry_stdout = "\n".join([
                "A90WSTA159_SECCOMP_HELPER_PRESENT=1",
                "a90_service_launcher_decision=exec",
                "fake_setpriv_args=--no-new-privs --reuid a90hud --regid a90hud --init-groups -- /bin/true",
                "",
            ])
            enforce_stdout = "\n".join([
                "A90WSTA159_SECCOMP_HELPER_PRESENT=1",
                "A90WSTA161_LOADER_GATED_APPLY=1",
                "A90WSTA161_SECCOMP_LOAD=0",
                "A90WSTA161_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=seccomp-dpublic-hud-intent-observed-v1 len=49",
                "a90_seccomp_loader_decision=check-only",
                "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY_OK=1",
                "a90_service_launcher_decision=blocked-seccomp-enforce-unimplemented",
                "",
            ])
            with (
                mock.patch.object(runner.wsta3.d4c, "verify_rootfs", return_value=None),
                mock.patch.object(
                    runner.wsta160,
                    "run_chroot_launcher",
                    side_effect=[
                        {"returncode": 0, "stdout": dry_stdout, "stderr": ""},
                        {"returncode": 65, "stdout": enforce_stdout, "stderr": ""},
                    ],
                ),
            ):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "wsta162"),
                    "--source-rootfs",
                    str(source_rootfs),
                    "--wsta153-seccomp-policy-json",
                    str(policy_path),
                    "--wsta156-filter-manifest-json",
                    str(filter_manifest),
                    "--wsta156-filter-object",
                    str(filter_object),
                    "--wsta161-loader-helper-manifest-json",
                    str(helper_manifest),
                    "--wsta161-loader-helper",
                    str(helper_binary),
                    "--execute-gated-apply-full-rootfs-chroot-dry-run",
                ]))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["helper_schema_is_wsta161"])
        self.assertTrue(result["checks"]["helper_apply_code_compiled"])
        self.assertEqual(
            result["proof"]["helper_schema"],
            "a90-wsta161-seccomp-loader-gated-apply-helper-v1",
        )
        self.assertFalse(result["proof"]["filter_load_enabled"])
        self.assertFalse(result["proof"]["seccomp_enforced"])
        self.assertTrue(result["proof_checks"]["enforce_no_load_attempt"])

    def test_gate_blocks_without_explicit_flag_or_private_helper(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_rootfs = root / "source-rootfs"
            source_rootfs.mkdir()
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            filter_manifest, filter_object = self.write_filter_artifact(root)
            helper_manifest, helper_binary = self.write_wsta161_helper(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta162"),
                "--source-rootfs",
                str(source_rootfs),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--wsta156-filter-manifest-json",
                str(filter_manifest),
                "--wsta156-filter-object",
                str(filter_object),
                "--wsta161-loader-helper-manifest-json",
                str(helper_manifest),
                "--wsta161-loader-helper",
                str(helper_binary),
            ]))
        self.assertEqual(result["decision"], "wsta162-blocked-explicit-gate-required")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            outside_root = Path(outside)
            source_rootfs = root / "source-rootfs"
            source_rootfs.mkdir()
            policy_path = root / "inputs" / "wsta153_seccomp_policy.json"
            self.write_json(policy_path, self.source_policy())
            filter_manifest, filter_object = self.write_filter_artifact(root)
            helper_manifest, helper_binary = self.write_wsta161_helper(outside_root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta162"),
                "--source-rootfs",
                str(source_rootfs),
                "--wsta153-seccomp-policy-json",
                str(policy_path),
                "--wsta156-filter-manifest-json",
                str(filter_manifest),
                "--wsta156-filter-object",
                str(filter_object),
                "--wsta161-loader-helper-manifest-json",
                str(helper_manifest),
                "--wsta161-loader-helper",
                str(helper_binary),
                "--execute-gated-apply-full-rootfs-chroot-dry-run",
            ]))
        self.assertEqual(result["decision"], "wsta162-blocked-helper-manifest-nonprivate")


if __name__ == "__main__":
    unittest.main()
