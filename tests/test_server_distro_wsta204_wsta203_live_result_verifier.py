from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta204_wsta203_live_result_verifier.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta204_wsta203_live_result_verifier.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta204Wsta203LiveResultVerifierTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_audit_chain(self, root: Path) -> Path:
        from tests.test_server_distro_wsta203_wsta202_wrapper_manifest_audit import (
            ServerDistroWsta203Wsta202WrapperManifestAuditTests,
        )

        fixture = ServerDistroWsta203Wsta202WrapperManifestAuditTests()
        preflight_path = fixture.write_preflight_chain(root)
        wsta203_dir = root / "wsta203"
        runner.wsta203.run(runner.wsta203.build_arg_parser().parse_args([
            "--run-dir",
            str(wsta203_dir),
            "--wsta202-preflight-json",
            str(preflight_path),
            "--audit-wsta203-wrapper-manifest",
        ]))
        return wsta203_dir / runner.wsta203.AUDIT_JSON_NAME

    def args(self, root: Path, audit: Path, *, emit: bool = True) -> list[str]:
        args = [
            "--run-dir",
            str(root / "wsta204"),
            "--source-wsta203-audit-json",
            str(audit),
        ]
        if emit:
            args.append("--emit-wsta204-live-result-verifier")
        return args

    def verify_args(self, root: Path, audit: Path, live_result: Path) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta204-verify"),
            "--source-wsta203-audit-json",
            str(audit),
            "--wsta198-live-result-json",
            str(live_result),
            "--verify-wsta204-live-result",
        ]

    def synthetic_live_result(self, audit_path: Path, live_result: Path) -> dict:
        audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))
        audit = audit_payload["wrapper_manifest_audit"]
        checks = {key: True for key in runner.REQUIRED_LIVE_CHECKS}
        safety = {key: True for key in runner.REQUIRED_LIVE_SAFETY_TRUE}
        safety.update({key: False for key in runner.REQUIRED_LIVE_SAFETY_FALSE})
        safety.update({
            "device_action": "single-service-seccomp-load-canary-over-ssh-chroot",
            "secret_values_logged": 0,
        })
        canary = {key: True for key in runner.REQUIRED_CANARY_MARKERS}
        payload = {
            "scope": "WSTA198 SSH/chroot adapter for WSTA196 seccomp-load canary",
            "decision": runner.wsta198.LIVE_PASS_DECISION,
            "run_dir": runner.rel(live_result.parent),
            "checks": checks,
            "safety": safety,
            "canary_parse": canary,
            "execution": {
                "returncode": 0,
                "input_redacted": True,
                "stdout": "A90WSTA198_REMOTE_CANARY_BEGIN\nA90WSTA198_LAUNCHER_PRESENT=1\n",
                "stderr": "",
            },
            "fresh_health": {"checks": {"version": True, "status": True, "selftest": True}},
            "post_health": {"checks": {"version": True, "status": True, "selftest": True}},
            "adapter": {
                "selected_transport": audit["selected_transport"],
                "canary_service": audit["canary_service"],
                "live_execution_requested": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
            },
        }
        self.write_json(live_result, payload)
        return payload

    def test_emits_post_live_verifier_but_requires_token(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, audit_path)))
            verifier = json.loads((root / "wsta204" / runner.VERIFIER_JSON_NAME).read_text(encoding="utf-8"))
            shell = root / "wsta204" / runner.VERIFIER_SH_NAME
            shell_exists = shell.exists()
            shell_executable = bool(shell.stat().st_mode & 0o100)
            markdown = (root / "wsta204" / runner.VERIFIER_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.SOURCE_PASS_DECISION)
        self.assertEqual(verifier["live_result_verifier"]["state"], "POST_LIVE_RESULT_VERIFIER_READY_TOKEN_REQUIRED_DEFAULT_OFF")
        self.assertTrue(verifier["live_result_verifier"]["ready_for_post_live_verification"])
        self.assertFalse(verifier["live_result_verifier"]["ready_for_immediate_live_execute"])
        self.assertFalse(verifier["live_result_verifier"]["private_token_env_present"])
        self.assertTrue(shell_exists)
        self.assertTrue(shell_executable)
        self.assertTrue(result["safety"]["wsta203_recheck_executed"])
        self.assertFalse(result["safety"]["wsta200_handoff_shell_executed"])
        self.assertFalse(result["safety"]["wsta198_live_command_executed"])
        self.assertIn("WSTA204 emits and runs only host-side verification logic", markdown)

    def test_emits_token_ready_state_without_supplying_it(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            with mock.patch.dict(runner.os.environ, {
                runner.wsta193.PRIVATE_TOKEN_ENV: runner.wsta161.LOAD_TOKEN
            }):
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, audit_path)))

        verifier = result["live_result_verifier"]
        self.assertEqual(result["decision"], runner.SOURCE_PASS_DECISION)
        self.assertEqual(verifier["state"], "POST_LIVE_RESULT_VERIFIER_READY_TOKEN_READY_DEFAULT_OFF")
        self.assertTrue(verifier["ready_for_immediate_live_execute"])
        self.assertTrue(verifier["private_token_env_present"])
        self.assertTrue(verifier["private_token_matches_wsta161"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["device_action"])

    def test_blocks_without_explicit_emit_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, audit_path, emit=False)))

        self.assertEqual(result["decision"], "wsta204-blocked-explicit-emit-gate-required")
        self.assertFalse(result["safety"]["wsta203_recheck_executed"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_blocks_audit_drift_after_recheck(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            payload = json.loads(audit_path.read_text(encoding="utf-8"))
            payload["wrapper_manifest_audit"]["operator_preflight_checks"].append("stale-extra")
            self.write_json(audit_path, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, audit_path)))

        self.assertEqual(result["decision"], "wsta204-blocked-audit-drift")
        self.assertTrue(result["checks"]["wsta203_recheck_valid"])
        self.assertFalse(result["checks"]["audit_stable_view_match"])
        self.assertFalse(result["safety"]["wsta200_handoff_shell_executed"])

    def test_verifies_synthetic_live_result_acceptance(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            live_result = root / "wsta198-live" / runner.wsta198.SUMMARY_NAME
            self.synthetic_live_result(audit_path, live_result)
            result = runner.run(runner.build_arg_parser().parse_args(self.verify_args(root, audit_path, live_result)))

        self.assertEqual(result["decision"], runner.VERIFY_PASS_DECISION)
        verification = result["live_result_verification"]
        self.assertEqual(verification["state"], "WSTA198_LIVE_RESULT_ACCEPTED")
        self.assertTrue(verification["seccomp_filter_loaded"])
        self.assertTrue(verification["seccomp_enforced"])
        self.assertTrue(verification["post_run_cleanup_checked"])

    def test_rejects_synthetic_live_result_missing_marker(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            live_result = root / "wsta198-live" / runner.wsta198.SUMMARY_NAME
            payload = self.synthetic_live_result(audit_path, live_result)
            payload["canary_parse"]["loaded_marker"] = False
            self.write_json(live_result, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.verify_args(root, audit_path, live_result)))

        self.assertEqual(result["decision"], "wsta204-blocked-live-result-invalid")
        self.assertFalse(result["live_result_checks"]["required_canary_markers"])

    def test_print_template_and_public_surfaces_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            audit_path = self.write_audit_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, audit_path)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            verifier_text = (root / "wsta204" / runner.VERIFIER_JSON_NAME).read_text(encoding="utf-8")
            source_text = SOURCE.read_text(encoding="utf-8")

        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        for text in (summary_text, verifier_text, source_text, printed.call_args.args[0]):
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta204-wsta203-live-result-verifier-source-pass", source_text)
        self.assertIn("POST_LIVE_RESULT_VERIFIER_READY_TOKEN_REQUIRED_DEFAULT_OFF", source_text)
        self.assertIn('"boot_flash": False', source_text)
        self.assertIn('"correct_wsta161_token_in_artifact": False', source_text)


if __name__ == "__main__":
    unittest.main()
