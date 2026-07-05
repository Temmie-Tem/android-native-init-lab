from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta206_wsta201_fresh_transaction_preparer.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta206_wsta201_fresh_transaction_preparer.py")
TOKEN_LITERAL = "WSTA161-" + "EXPLICIT-ALLOW-SECCOMP-LOAD"


class ServerDistroWsta206Wsta201FreshTransactionPreparerTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta201_status_chain(self, root: Path) -> Path:
        from tests.test_server_distro_wsta202_wsta201_live_preflight import (
            ServerDistroWsta202Wsta201LivePreflightTests,
        )

        fixture = ServerDistroWsta202Wsta201LivePreflightTests()
        return fixture.write_status_chain(root)

    def args(self, root: Path, status: Path, *, emit: bool = True) -> list[str]:
        args = [
            "--run-dir",
            str(root / "wsta206"),
            "--wsta201-status-json",
            str(status),
        ]
        if emit:
            args.append("--emit-wsta206-fresh-transaction-preparer")
        return args

    def test_replays_wsta202_to_wsta205_and_emits_preparer_but_requires_token(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))
            preparer = json.loads((root / "wsta206" / runner.PREPARER_JSON_NAME).read_text(encoding="utf-8"))
            shell = root / "wsta206" / runner.PREPARER_SH_NAME
            shell_text = shell.read_text(encoding="utf-8")
            shell_exists = shell.exists()
            shell_executable = bool(shell.stat().st_mode & 0o100)
            markdown = (root / "wsta206" / runner.PREPARER_MD_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(preparer["fresh_transaction_preparer"]["state"], "FRESH_TRANSACTION_PREPARER_READY_TOKEN_REQUIRED_DEFAULT_OFF")
        self.assertTrue(preparer["fresh_transaction_preparer"]["ready_for_fresh_prepare"])
        self.assertFalse(preparer["fresh_transaction_preparer"]["ready_for_immediate_live_execute"])
        self.assertFalse(preparer["fresh_transaction_preparer"]["private_token_env_present"])
        self.assertTrue(shell_exists)
        self.assertTrue(shell_executable)
        self.assertIn("run_wsta206_wsta201_fresh_transaction_preparer.py", shell_text)
        self.assertIn("fresh_wsta205_transaction_script", shell_text)
        self.assertTrue(result["safety"]["wsta202_replay_executed"])
        self.assertTrue(result["safety"]["wsta203_replay_executed"])
        self.assertTrue(result["safety"]["wsta204_replay_executed"])
        self.assertTrue(result["safety"]["wsta205_replay_executed"])
        self.assertTrue(result["safety"]["wsta206_prepare_script_generated"])
        self.assertFalse(result["safety"]["wsta206_prepare_script_executed"])
        self.assertFalse(result["safety"]["wsta205_transaction_script_executed"])
        self.assertFalse(result["safety"]["wsta200_handoff_shell_executed"])
        self.assertIn("does not run the WSTA205 transaction script", markdown)

    def test_replays_token_ready_state_without_supplying_it(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            with mock.patch.dict(runner.os.environ, {
                runner.wsta193.PRIVATE_TOKEN_ENV: runner.wsta161.LOAD_TOKEN
            }):
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))

        preparer = result["fresh_transaction_preparer"]
        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(preparer["state"], "FRESH_TRANSACTION_PREPARER_READY_TOKEN_READY_DEFAULT_OFF")
        self.assertTrue(preparer["ready_for_immediate_live_execute"])
        self.assertTrue(preparer["private_token_env_present"])
        self.assertTrue(preparer["private_token_matches_wsta161"])
        self.assertFalse(result["safety"]["correct_wsta161_token_supplied"])
        self.assertFalse(result["safety"]["device_action"])

    def test_blocks_without_explicit_emit_gate(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path, emit=False)))

        self.assertEqual(result["decision"], "wsta206-blocked-explicit-emit-gate-required")
        self.assertFalse(result["safety"]["wsta202_replay_executed"])
        self.assertFalse(result["safety"]["live_command_executed"])

    def test_blocks_invalid_or_nonprivate_wsta201_status(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            payload["handoff_status"]["handoff_match"] = False
            self.write_json(status_path, payload)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))
        self.assertEqual(result["decision"], "wsta206-blocked-wsta201-status-invalid")
        self.assertFalse(result["wsta201_status_checks"]["handoff_match"])

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            outside_status = Path(outside) / runner.wsta202.wsta201.STATUS_JSON_NAME
            outside_status.write_text(status_path.read_text(encoding="utf-8"), encoding="utf-8")
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, outside_status)))
        self.assertEqual(result["decision"], "wsta206-blocked-wsta201-status-nonprivate")

    def test_rejects_replay_drift_when_wsta202_fails(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            with mock.patch.object(runner.wsta202, "run", return_value={
                "decision": "not-pass",
                "checks": {"status_valid": False},
                "safety": runner.safety_flags(),
            }):
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))

        self.assertEqual(result["decision"], "wsta206-blocked-wsta202-replay-invalid")
        self.assertTrue(result["safety"]["wsta202_replay_executed"])
        self.assertFalse(result["safety"]["wsta203_replay_executed"])

    def test_print_template_and_public_surfaces_are_redacted(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = self.write_wsta201_status_chain(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, status_path)))
            summary_text = json.dumps(runner.public_summary(result), sort_keys=True)
            preparer_text = (root / "wsta206" / runner.PREPARER_JSON_NAME).read_text(encoding="utf-8")
            source_text = SOURCE.read_text(encoding="utf-8")

        with mock.patch.object(runner, "run", side_effect=AssertionError("unexpected run")):
            with mock.patch("builtins.print") as printed:
                rc = runner.main_with_args(["--print-template"])

        self.assertEqual(rc, 0)
        for text in (summary_text, preparer_text, source_text, printed.call_args.args[0]):
            self.assertNotIn(TOKEN_LITERAL, text)
            self.assertNotIn("try" + "cloudflare.com", text.lower())
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())
            self.assertNotIn("native_init_flash.py", text)
        self.assertIn("wsta206-wsta201-fresh-transaction-preparer-pass", source_text)
        self.assertIn("FRESH_TRANSACTION_PREPARER_READY_TOKEN_REQUIRED_DEFAULT_OFF", source_text)
        self.assertIn('"boot_flash": False', source_text)
        self.assertIn('"correct_wsta161_token_in_artifact": False', source_text)


if __name__ == "__main__":
    unittest.main()
