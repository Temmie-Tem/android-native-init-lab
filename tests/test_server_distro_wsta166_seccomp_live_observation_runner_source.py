from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta166_seccomp_live_observation_runner_source.py")


class ServerDistroWsta166SeccompLiveObservationRunnerSourceTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def plan(self) -> dict:
        return runner.wsta165.observation_plan()

    def test_source_proof_emits_no_load_remote_script_and_contract(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            plan_path = root / "inputs" / "wsta165_live_observation_plan.json"
            self.write_json(plan_path, self.plan())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta166"),
                "--wsta165-plan-json",
                str(plan_path),
                "--emit-seccomp-live-runner-source-proof",
            ]))
            script_path = root / "wsta166" / runner.REMOTE_SCRIPT_NAME
            contract_path = root / "wsta166" / runner.CONTRACT_NAME
            script_text = script_path.read_text(encoding="utf-8")
            contract = json.loads(contract_path.read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["plan_checks"]["three_scenarios"])
        self.assertTrue(result["source_checks"]["script_has_all_scenarios"])
        self.assertTrue(result["source_checks"]["script_correct_token_literal_absent"])
        self.assertTrue(result["source_checks"]["contract_correct_token_false"])
        self.assertIn("run_scenario no-load-env-gate", script_text)
        self.assertIn("run_scenario load-env-gate-missing-token", script_text)
        self.assertIn("run_scenario load-env-gate-wrong-token", script_text)
        self.assertIn("intentionally-wrong-token", script_text)
        self.assertNotIn(runner.CORRECT_WSTA161_TOKEN, script_text)
        self.assertEqual(contract["scenario_names"], [
            "no-load-env-gate",
            "load-env-gate-missing-token",
            "load-env-gate-wrong-token",
        ])
        self.assertFalse(contract["correct_wsta161_token_included"])
        self.assertFalse(contract["seccomp_filter_load_expected"])
        self.assertFalse(contract["seccomp_enforcement_expected"])

    def test_gate_blocks_without_explicit_flag_or_private_plan(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            plan_path = root / "inputs" / "wsta165_live_observation_plan.json"
            self.write_json(plan_path, self.plan())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta166"),
                "--wsta165-plan-json",
                str(plan_path),
            ]))
        self.assertEqual(result["decision"], "wsta166-blocked-explicit-gate-required")

        with self.private_tmp() as tmp, tempfile.TemporaryDirectory() as outside:
            root = Path(tmp)
            plan_path = Path(outside) / "wsta165_live_observation_plan.json"
            self.write_json(plan_path, self.plan())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta166"),
                "--wsta165-plan-json",
                str(plan_path),
                "--emit-seccomp-live-runner-source-proof",
            ]))
        self.assertEqual(result["decision"], "wsta166-blocked-wsta165-plan-nonprivate")

    def test_plan_with_correct_token_literal_blocks_source_proof(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            plan = self.plan()
            plan["scenarios"][2]["env"]["A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN"] = runner.CORRECT_WSTA161_TOKEN
            plan_path = root / "inputs" / "wsta165_live_observation_plan.json"
            self.write_json(plan_path, plan)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta166"),
                "--wsta165-plan-json",
                str(plan_path),
                "--emit-seccomp-live-runner-source-proof",
            ]))
        self.assertEqual(result["decision"], "wsta166-blocked-source-invalid")
        self.assertFalse(result["plan_checks"]["correct_token_literal_absent"])
        self.assertFalse(result["source_checks"]["script_correct_token_literal_absent"])


if __name__ == "__main__":
    unittest.main()
