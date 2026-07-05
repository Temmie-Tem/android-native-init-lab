from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta161_seccomp_loader_gated_apply_helper.py")


class ServerDistroWsta161SeccompLoaderGatedApplyHelperTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def fake_filter_source(self) -> str:
        return """#include <linux/filter.h>

const unsigned int a90_wsta156_service_count = 4U;
const unsigned int a90_wsta156_audit_arch_aarch64 = 3221225655U;

struct sock_filter a90_wsta156_dpublic_smoke_httpd_filter[] = {{0, 0, 0, 0}};
const unsigned short a90_wsta156_dpublic_smoke_httpd_filter_len = 1U;
struct sock_filter a90_wsta156_cloudflared_quick_tunnel_filter[] = {{0, 0, 0, 0}};
const unsigned short a90_wsta156_cloudflared_quick_tunnel_filter_len = 1U;
struct sock_filter a90_wsta156_dropbear_admin_usb_filter[] = {{0, 0, 0, 0}};
const unsigned short a90_wsta156_dropbear_admin_usb_filter_len = 1U;
struct sock_filter a90_wsta156_dpublic_hud_intent_filter[] = {{0, 0, 0, 0}};
const unsigned short a90_wsta156_dpublic_hud_intent_filter_len = 1U;
"""

    def compile_fake_filter_object(self, root: Path) -> Path:
        source = root / "inputs" / "fake_wsta156_filters.c"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(self.fake_filter_source(), encoding="utf-8")
        object_path = root / "inputs" / "wsta156_seccomp_filters.o"
        completed = subprocess.run(
            ["aarch64-linux-gnu-gcc", "-Wall", "-Wextra", "-Werror", "-c", str(source), "-o", str(object_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30.0,
        )
        if completed.returncode != 0:
            self.fail(completed.stderr)
        return object_path

    def write_filter_artifact(self, root: Path) -> tuple[Path, Path]:
        object_path = self.compile_fake_filter_object(root)
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
                {
                    "service": "dpublic-smoke-httpd",
                    "profile_name": "seccomp-dpublic-smoke-httpd-observed-v1",
                    "instruction_count": 1,
                    "missing_syscalls": [],
                },
                {
                    "service": "cloudflared-quick-tunnel",
                    "profile_name": "seccomp-cloudflared-quick-tunnel-observed-v1",
                    "instruction_count": 1,
                    "missing_syscalls": [],
                },
                {
                    "service": "dropbear-admin-usb",
                    "profile_name": "seccomp-dropbear-admin-usb-observed-v1",
                    "instruction_count": 1,
                    "missing_syscalls": [],
                },
                {
                    "service": "dpublic-hud-intent",
                    "profile_name": "seccomp-dpublic-hud-intent-observed-v1",
                    "instruction_count": 1,
                    "missing_syscalls": [],
                },
            ],
            "redaction": {
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }
        manifest_path = root / "inputs" / "wsta156_seccomp_filter_manifest.json"
        self.write_json(manifest_path, manifest)
        return manifest_path, object_path

    def test_valid_filter_artifact_builds_gated_apply_helper_and_blocks_load(self) -> None:
        self.assertIsNotNone(shutil.which("aarch64-linux-gnu-gcc"))
        self.assertIsNotNone(shutil.which("aarch64-linux-gnu-nm"))
        self.assertIsNotNone(shutil.which("qemu-aarch64"))
        with self.private_tmp() as tmp:
            root = Path(tmp)
            manifest_path, object_path = self.write_filter_artifact(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta161"),
                "--wsta156-filter-manifest-json",
                str(manifest_path),
                "--wsta156-filter-object",
                str(object_path),
                "--emit-seccomp-loader-gated-apply-helper",
            ]))
            manifest = json.loads((root / "wsta161" / runner.MANIFEST_NAME).read_text(encoding="utf-8"))
            helper_source = (root / "wsta161" / runner.HELPER_SOURCE_NAME).read_text(encoding="utf-8")
            service_stdout = (root / "wsta161" / runner.SERVICE_STDOUT_NAME).read_text(encoding="utf-8")
            apply_stdout = (root / "wsta161" / runner.APPLY_STDOUT_NAME).read_text(encoding="utf-8")
            wrong_stdout = (root / "wsta161" / runner.WRONG_TOKEN_STDOUT_NAME).read_text(encoding="utf-8")
            nm_output = (root / "wsta161" / runner.NM_OUTPUT_NAME).read_text(encoding="utf-8")
            binary_exists = (root / "wsta161" / runner.HELPER_BINARY_NAME).is_file()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(binary_exists)
        self.assertEqual(manifest["state"], "SECCOMP_LOADER_GATED_APPLY_COMPILED_NOT_LOADED")
        self.assertTrue(manifest["apply_code_compiled"])
        self.assertFalse(manifest["default_load_enabled"])
        self.assertFalse(manifest["loaded"])
        self.assertFalse(manifest["enforced"])
        self.assertIn("PR_SET_NO_NEW_PRIVS", helper_source)
        self.assertIn("PR_SET_SECCOMP", helper_source)
        self.assertIn("A90WSTA161_ALLOW_LOAD", helper_source)
        self.assertIn("A90WSTA161_LOAD_TOKEN", helper_source)
        self.assertIn("a90_wsta161_load_profile", nm_output)
        self.assertIn("service=dpublic-hud policy_service=dpublic-hud-intent", service_stdout)
        self.assertIn("A90WSTA161_SECCOMP_LOAD=0", apply_stdout)
        self.assertIn("blocked-load-gate-required", apply_stdout)
        self.assertNotIn("A90WSTA161_SECCOMP_LOAD_ATTEMPT=1", apply_stdout)
        self.assertIn("blocked-load-token-required", wrong_stdout)
        self.assertNotIn("A90WSTA161_SECCOMP_LOAD_ATTEMPT=1", wrong_stdout)
        self.assertFalse(result["safety"]["seccomp_filter_loaded"])
        self.assertFalse(result["safety"]["seccomp_enforced"])

    def test_gate_blocks_without_explicit_flag_or_private_artifacts(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            manifest_path, object_path = self.write_filter_artifact(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta161"),
                "--wsta156-filter-manifest-json",
                str(manifest_path),
                "--wsta156-filter-object",
                str(object_path),
            ]))
        self.assertEqual(result["decision"], "wsta161-blocked-explicit-gate-required")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            outside_root = Path(outside)
            manifest_path, object_path = self.write_filter_artifact(outside_root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta161"),
                "--wsta156-filter-manifest-json",
                str(manifest_path),
                "--wsta156-filter-object",
                str(object_path),
                "--emit-seccomp-loader-gated-apply-helper",
            ]))
        self.assertEqual(result["decision"], "wsta161-blocked-filter-manifest-nonprivate")

    def test_invalid_filter_object_sha_blocks(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            manifest_path, object_path = self.write_filter_artifact(root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["object"] = "0" * 64
            self.write_json(manifest_path, manifest)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta161"),
                "--wsta156-filter-manifest-json",
                str(manifest_path),
                "--wsta156-filter-object",
                str(object_path),
                "--emit-seccomp-loader-gated-apply-helper",
            ]))
        self.assertEqual(result["decision"], "wsta161-blocked-filter-artifact-invalid")


if __name__ == "__main__":
    unittest.main()
