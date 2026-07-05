from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta180_seccomp_live_handoff_bundle.py")


class ServerDistroWsta180SeccompLiveHandoffBundleTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_wsta168_command(self, root: Path) -> tuple[Path, Path]:
        command_json = root / "wsta168_live_command.json"
        command_sh = root / "wsta168_live_command.sh"
        self.write_json(command_json, {
            "schema": "a90-wsta168-seccomp-live-observation-command-v1",
            "state": "READY_TO_RUN_NOT_EXECUTED",
            "command": ["python3", "workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py"],
            "required_ack_flags": [],
            "expected_outcome": {},
            "executed": False,
            "secret_values_logged": 0,
        })
        command_sh.write_text("#!/bin/sh\nexec true\n", encoding="utf-8")
        return command_json, command_sh

    def write_wsta178_command(self, root: Path, *, bad_script: bool = False) -> tuple[Path, Path, Path]:
        command_json, command_sh = self.write_wsta168_command(root)
        command = runner.wsta179.wsta178.execution_command(
            root / "wsta178-preflight",
            command_json,
            command_sh,
            20.0,
            1800.0,
            900,
        )
        payload = runner.wsta179.wsta178.command_payload(command)
        packet_json = root / "wsta178-preflight" / runner.wsta179.wsta178.COMMAND_JSON_NAME
        packet_sh = root / "wsta178-preflight" / runner.wsta179.wsta178.COMMAND_SH_NAME
        self.write_json(packet_json, payload)
        script = "#!/bin/sh\nset -eu\nexec " + " ".join(command) + "\n"
        if bad_script:
            script += "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD\n"
        packet_sh.parent.mkdir(parents=True, exist_ok=True)
        packet_sh.write_text(script, encoding="utf-8")
        result_path = runner.wsta179.inferred_wsta177_result_path(payload)
        assert result_path is not None
        return packet_json, packet_sh, result_path

    def args(self, root: Path, packet_json: Path, packet_sh: Path, *extra: str) -> list[str]:
        return [
            "--run-dir",
            str(root / "wsta180"),
            "--wsta178-command-json",
            str(packet_json),
            "--wsta178-command-sh",
            str(packet_sh),
            *extra,
        ]

    def test_handoff_bundle_emits_execution_and_audit_surfaces_without_executing(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, result_path = self.write_wsta178_command(root)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, packet_json, packet_sh, "--emit-wsta180-handoff-bundle")
            ))
            bundle = json.loads((root / "wsta180" / runner.BUNDLE_JSON_NAME).read_text(encoding="utf-8"))
            commands_script = (root / "wsta180" / runner.BUNDLE_SH_NAME).read_text(encoding="utf-8")

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["pre_run_audit_missing_result"])
        self.assertTrue(result["checks"]["execution_packet_valid"])
        self.assertTrue(result["checks"]["post_run_audit_command_valid"])
        self.assertTrue(result["checks"]["bundle_valid"])
        self.assertTrue(result["safety"]["handoff_bundle_generated"])
        self.assertFalse(result["safety"]["live_command_executed"])
        self.assertEqual(bundle["state"], "READY_FOR_OPERATOR_APPROVAL_NOT_EXECUTED")
        self.assertEqual(bundle["execute_packet"]["command_script"], runner.rel(packet_sh))
        self.assertEqual(bundle["expected_result"]["wsta177_result_json"], runner.rel(result_path))
        self.assertFalse(bundle["executed"])
        self.assertIn("run_wsta179_seccomp_one_shot_result_audit.py", commands_script)
        self.assertNotIn("--execute-wsta177-one-shot", commands_script)
        self.assertNotIn("WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD", commands_script)

    def test_missing_bundle_gate_blocks_before_audit(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, _result_path = self.write_wsta178_command(root)
            result = runner.run(runner.build_arg_parser().parse_args(self.args(root, packet_json, packet_sh)))

        self.assertEqual(result["decision"], "wsta180-blocked-explicit-bundle-gate-required")
        self.assertFalse((root / "wsta180" / runner.BUNDLE_JSON_NAME).exists())

    def test_existing_result_blocks_pre_run_bundle(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, result_path = self.write_wsta178_command(root)
            self.write_json(result_path, {"decision": "unexpected-existing-result"})
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, packet_json, packet_sh, "--emit-wsta180-handoff-bundle")
            ))

        self.assertEqual(result["decision"], "wsta180-blocked-pre-run-audit-not-ready")
        self.assertFalse(result["checks"]["pre_run_audit_missing_result"])
        self.assertFalse((root / "wsta180" / runner.BUNDLE_JSON_NAME).exists())

    def test_bad_command_packet_blocks_bundle(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            packet_json, packet_sh, _result_path = self.write_wsta178_command(root, bad_script=True)
            result = runner.run(runner.build_arg_parser().parse_args(
                self.args(root, packet_json, packet_sh, "--emit-wsta180-handoff-bundle")
            ))

        self.assertEqual(result["decision"], "wsta180-blocked-pre-run-audit-not-ready")
        self.assertFalse(result["checks"]["pre_run_command_packet_valid"])
        self.assertFalse((root / "wsta180" / runner.BUNDLE_JSON_NAME).exists())


if __name__ == "__main__":
    unittest.main()
