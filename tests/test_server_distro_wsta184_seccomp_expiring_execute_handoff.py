from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta184_seccomp_expiring_execute_handoff.py")


class ServerDistroWsta184SeccompExpiringExecuteHandoffTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_bundle(self, root: Path) -> tuple[Path, Path]:
        bundle_json = root / "wsta180_operator_handoff.json"
        bundle_sh = root / "wsta180_operator_handoff_commands.sh"
        self.write_json(bundle_json, {"schema": "a90-wsta180-seccomp-live-handoff-bundle-v1"})
        bundle_sh.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        return bundle_json, bundle_sh

    def command_payload(self, root: Path) -> tuple[Path, Path, dict]:
        command = runner.wsta182.execution_command(
            root / "fresh-wsta183-readiness" / "fresh-wsta182-readiness-status",
            root / "wsta180_operator_handoff.json",
            root / "wsta180_operator_handoff_commands.sh",
            1800.0,
            1800.0,
        )
        payload = runner.wsta182.command_payload(command)
        command_json = root / "fresh-wsta183-readiness" / "fresh-wsta182-readiness-status" / runner.wsta182.COMMAND_JSON_NAME
        command_sh = root / "fresh-wsta183-readiness" / "fresh-wsta182-readiness-status" / runner.wsta182.COMMAND_SH_NAME
        self.write_json(command_json, payload)
        command_sh.parent.mkdir(parents=True, exist_ok=True)
        command_sh.write_text("#!/bin/sh\nexec " + " ".join(command) + "\n", encoding="utf-8")
        return command_json, command_sh, payload

    def write_readiness_result(self, path: Path, command_json: Path, command_sh: Path, *, ended_utc: str) -> None:
        self.write_json(path, {
            "decision": runner.wsta182.PASS_DECISION,
            "ended_utc": ended_utc,
            "checks": {
                "source_gate_valid": True,
                "execution_command_valid": True,
            },
            "status": {
                "state": "READY_FOR_EXPLICIT_OPERATOR_APPROVAL",
                "blocking_condition": "explicit-wsta181-operator-approval-required",
            },
            "command": {
                "state": "READY_TO_RUN_NOT_EXECUTED",
                "executed": False,
                "command_json": runner.rel(command_json),
                "command_script": runner.rel(command_sh),
            },
            "safety": {
                "live_command_executed": False,
                "wsta181_execute_command_executed": False,
                "wsta178_execute_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        })

    def valid_fresh_result(self, args, bundle_json: Path, bundle_sh: Path, *, old: bool = False) -> dict:
        now = dt.datetime.now(dt.timezone.utc)
        ended = now - dt.timedelta(seconds=1200 if old else 0)
        ended_s = runner.format_utc(ended)
        readiness_dir = args.run_dir / "fresh-wsta182-readiness-status"
        command_json, command_sh, _payload = self.command_payload(args.run_dir.parent)
        readiness_result = readiness_dir / runner.wsta182.SUMMARY_NAME
        self.write_readiness_result(readiness_result, command_json, command_sh, ended_utc=ended_s)
        result = {
            "decision": runner.wsta183.PASS_DECISION,
            "ended_utc": ended_s,
            "wsta180_bundle_json": runner.rel(bundle_json),
            "wsta180_bundle_sh": runner.rel(bundle_sh),
            "checks": {
                "fresh_source_gate_valid": True,
                "readiness_valid": True,
            },
            "readiness": {
                "state": "READY_FOR_EXPLICIT_OPERATOR_APPROVAL",
                "result_json": runner.rel(readiness_result),
                "command_json": runner.rel(command_json),
                "command_script": runner.rel(command_sh),
            },
            "safety": {
                "live_command_executed": False,
                "wsta181_execute_command_executed": False,
                "wsta178_execute_command_executed": False,
                "seccomp_filter_loaded": False,
                "seccomp_enforced": False,
                "correct_wsta161_token_supplied": False,
            },
        }
        self.write_json(args.run_dir / runner.wsta183.SUMMARY_NAME, result)
        return result

    def args(self, root: Path, bundle_json: Path, bundle_sh: Path, *extra: str) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta184"),
            "--wsta180-bundle-json",
            str(bundle_json),
            "--wsta180-bundle-sh",
            str(bundle_sh),
            *extra,
        ]

    def test_expiring_handoff_wraps_fresh_readiness_command_without_execution(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh = self.write_bundle(root)

            def fake_wsta183(args):
                return self.valid_fresh_result(args, bundle_json, bundle_sh)

            old_wsta183 = runner.wsta183.run
            runner.wsta183.run = fake_wsta183
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.args(root, bundle_json, bundle_sh, "--emit-expiring-handoff")
                ))
            finally:
                runner.wsta183.run = old_wsta183

            handoff = json.loads((root / "wsta184" / runner.HANDOFF_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["fresh_readiness_valid"])
        self.assertTrue(result["checks"]["freshness_valid"])
        self.assertTrue(result["checks"]["readiness_valid"])
        self.assertTrue(result["checks"]["command_valid"])
        self.assertTrue(result["safety"]["handoff_generated"])
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertEqual(handoff["schema"], "a90-wsta184-expiring-wsta181-execute-handoff-v1")
        self.assertEqual(handoff["state"], "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY")
        self.assertFalse(handoff["executed"])
        self.assertIn("workspace/public/src/scripts/server-distro/run_wsta181_seccomp_handoff_execute_audit_gate.py", handoff["command"])

    def test_missing_handoff_gate_blocks_before_fresh_readiness(self) -> None:
        def fail(*_args, **_kwargs):
            raise AssertionError("fresh readiness should not run")

        old_wsta183 = runner.wsta183.run
        runner.wsta183.run = fail
        try:
            with self.private_tmp() as tmp:
                root = Path(tmp)
                bundle_json, bundle_sh = self.write_bundle(root)
                result = runner.run(runner.build_arg_parser().parse_args(self.args(root, bundle_json, bundle_sh)))
        finally:
            runner.wsta183.run = old_wsta183

        self.assertEqual(result["decision"], "wsta184-blocked-explicit-handoff-gate-required")

    def test_invalid_fresh_readiness_blocks_handoff(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh = self.write_bundle(root)

            def bad_wsta183(args):
                result = self.valid_fresh_result(args, bundle_json, bundle_sh)
                result["decision"] = "bad"
                runner.write_json(args.run_dir / runner.wsta183.SUMMARY_NAME, result)
                return result

            old_wsta183 = runner.wsta183.run
            runner.wsta183.run = bad_wsta183
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.args(root, bundle_json, bundle_sh, "--emit-expiring-handoff")
                ))
            finally:
                runner.wsta183.run = old_wsta183

        self.assertEqual(result["decision"], "wsta184-blocked-fresh-readiness-invalid")
        self.assertFalse((root / "wsta184" / runner.HANDOFF_NAME).exists())

    def test_stale_readiness_blocks_handoff(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            bundle_json, bundle_sh = self.write_bundle(root)

            def old_wsta183_result(args):
                return self.valid_fresh_result(args, bundle_json, bundle_sh, old=True)

            old_wsta183 = runner.wsta183.run
            runner.wsta183.run = old_wsta183_result
            try:
                result = runner.run(runner.build_arg_parser().parse_args(
                    self.args(root, bundle_json, bundle_sh, "--emit-expiring-handoff", "--max-age-sec", "60")
                ))
            finally:
                runner.wsta183.run = old_wsta183

        self.assertEqual(result["decision"], "wsta184-blocked-handoff-invalid")
        self.assertFalse(result["freshness_checks"]["within_max_age"])
        self.assertFalse((root / "wsta184" / runner.HANDOFF_NAME).exists())


if __name__ == "__main__":
    unittest.main()
