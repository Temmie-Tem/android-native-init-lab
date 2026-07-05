from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta160_seccomp_full_rootfs_chroot_dry_run.py")


class ServerDistroWsta160SeccompFullRootfsChrootDryRunTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_file(self, path: Path, data: bytes = b"x") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def test_valid_inputs_prepare_and_chroot_proof_pass(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_rootfs = root / "source-rootfs"
            source_rootfs.mkdir()
            policy = root / "inputs" / "wsta153_seccomp_policy.json"
            filter_manifest = root / "inputs" / "wsta156_seccomp_filter_manifest.json"
            filter_object = root / "inputs" / "wsta156_seccomp_filters.o"
            helper_manifest = root / "inputs" / "wsta158_seccomp_loader_helper_manifest.json"
            helper_binary = root / "inputs" / "a90-seccomp-loader-checkonly"
            for path in (policy, filter_manifest, filter_object, helper_manifest, helper_binary):
                self.write_file(path, b"{}")
            dry_stdout = "\n".join([
                "A90WSTA159_SECCOMP_HELPER_PRESENT=1",
                "a90_service_launcher_decision=exec",
                "fake_setpriv_args=--no-new-privs --reuid a90hud --regid a90hud --init-groups -- /bin/true",
                "",
            ])
            enforce_stdout = "\n".join([
                "A90WSTA159_SECCOMP_HELPER_PRESENT=1",
                "A90WSTA158_LOADER_CHECK_ONLY=1",
                "A90WSTA158_SECCOMP_LOAD=0",
                "A90WSTA158_PROFILE service=dpublic-hud policy_service=dpublic-hud-intent profile=x len=49",
                "A90WSTA159_SECCOMP_HELPER_CHECK_ONLY_OK=1",
                "a90_service_launcher_decision=blocked-seccomp-enforce-unimplemented",
                "",
            ])
            def fake_stage(rootfs: Path, *_args) -> dict:
                helper = rootfs / runner.wsta3.TARGET_SECCOMP_LOADER_HELPER
                helper.parent.mkdir(parents=True, exist_ok=True)
                helper.write_bytes(b"helper")
                return {
                    "service_launcher": {"seccomp_helper_check_call_present": True},
                    "seccomp_loader_helper": {"staged": True},
                }

            with (
                mock.patch.object(runner.wsta3.d4c, "verify_rootfs", return_value=None),
                mock.patch.object(runner, "stage_full_rootfs", side_effect=fake_stage),
                mock.patch.object(
                    runner,
                    "run_chroot_launcher",
                    side_effect=[
                        {"returncode": 0, "stdout": dry_stdout, "stderr": ""},
                        {"returncode": 65, "stdout": enforce_stdout, "stderr": ""},
                    ],
                ),
            ):
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "wsta160"),
                    "--source-rootfs",
                    str(source_rootfs),
                    "--wsta153-seccomp-policy-json",
                    str(policy),
                    "--wsta156-filter-manifest-json",
                    str(filter_manifest),
                    "--wsta156-filter-object",
                    str(filter_object),
                    "--wsta158-loader-helper-manifest-json",
                    str(helper_manifest),
                    "--wsta158-loader-helper",
                    str(helper_binary),
                    "--execute-full-rootfs-chroot-dry-run",
                ]))
            summary = json.loads((root / "wsta160" / runner.SUMMARY_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(summary["gate_decision"], "ok")
        self.assertTrue(result["checks"]["rootfs_copy_staged"])
        self.assertTrue(result["checks"]["service_launcher_staged"])
        self.assertTrue(result["checks"]["helper_default_path_staged"])
        self.assertEqual(
            result["proof"]["default_helper_path_inside_chroot"],
            "/usr/lib/a90-dpublic/seccomp/a90-seccomp-loader-checkonly",
        )
        self.assertFalse(result["proof"]["filter_load_enabled"])
        self.assertFalse(result["proof"]["seccomp_enforced"])
        self.assertTrue(result["proof_checks"]["enforce_blocks_before_exec"])

    def test_gate_blocks_without_explicit_flag_or_private_source(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            source_rootfs = root / "source-rootfs"
            source_rootfs.mkdir()
            policy = root / "inputs" / "wsta153_seccomp_policy.json"
            filter_manifest = root / "inputs" / "wsta156_seccomp_filter_manifest.json"
            filter_object = root / "inputs" / "wsta156_seccomp_filters.o"
            helper_manifest = root / "inputs" / "wsta158_seccomp_loader_helper_manifest.json"
            helper_binary = root / "inputs" / "a90-seccomp-loader-checkonly"
            for path in (policy, filter_manifest, filter_object, helper_manifest, helper_binary):
                self.write_file(path, b"{}")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta160"),
                "--source-rootfs",
                str(source_rootfs),
                "--wsta153-seccomp-policy-json",
                str(policy),
                "--wsta156-filter-manifest-json",
                str(filter_manifest),
                "--wsta156-filter-object",
                str(filter_object),
                "--wsta158-loader-helper-manifest-json",
                str(helper_manifest),
                "--wsta158-loader-helper",
                str(helper_binary),
            ]))
        self.assertEqual(result["decision"], "wsta160-blocked-explicit-gate-required")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            outside_source = Path(outside) / "source-rootfs"
            outside_source.mkdir()
            policy = root / "inputs" / "wsta153_seccomp_policy.json"
            filter_manifest = root / "inputs" / "wsta156_seccomp_filter_manifest.json"
            filter_object = root / "inputs" / "wsta156_seccomp_filters.o"
            helper_manifest = root / "inputs" / "wsta158_seccomp_loader_helper_manifest.json"
            helper_binary = root / "inputs" / "a90-seccomp-loader-checkonly"
            for path in (policy, filter_manifest, filter_object, helper_manifest, helper_binary):
                self.write_file(path, b"{}")
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta160"),
                "--source-rootfs",
                str(outside_source),
                "--wsta153-seccomp-policy-json",
                str(policy),
                "--wsta156-filter-manifest-json",
                str(filter_manifest),
                "--wsta156-filter-object",
                str(filter_object),
                "--wsta158-loader-helper-manifest-json",
                str(helper_manifest),
                "--wsta158-loader-helper",
                str(helper_binary),
                "--execute-full-rootfs-chroot-dry-run",
            ]))
        self.assertEqual(result["decision"], "wsta160-blocked-source-rootfs-nonprivate")


if __name__ == "__main__":
    unittest.main()
