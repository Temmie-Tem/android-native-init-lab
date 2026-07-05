from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py")


class ServerDistroWsta167SeccompLiveObservationTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def write_contract_and_script(self, root: Path) -> tuple[Path, Path]:
        plan = runner.wsta166.wsta165.observation_plan()
        script = runner.wsta166.remote_script(plan)
        script_path = root / "inputs" / "wsta166_remote_seccomp_observation.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script, encoding="utf-8")
        script_path.chmod(0o755)
        contract = runner.wsta166.live_runner_contract(plan, script_path)
        contract_path = root / "inputs" / "wsta166_live_runner_contract.json"
        self.write_json(contract_path, contract)
        return contract_path, script_path

    def test_explicit_live_gate_requires_all_acknowledgements(self) -> None:
        args = SimpleNamespace(
            execute_seccomp_live_observation=False,
            allow_seccomp_live_observation=False,
            ack_no_correct_wsta161_token=False,
            ack_no_seccomp_load=False,
            ack_cleanup_required=False,
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta167-blocked-seccomp-live-observation-required"),
        )
        args.execute_seccomp_live_observation = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta167-blocked-seccomp-live-observation-allow-required"),
        )
        args.allow_seccomp_live_observation = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta167-blocked-no-correct-token-ack-required"),
        )
        args.ack_no_correct_wsta161_token = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta167-blocked-no-seccomp-load-ack-required"),
        )
        args.ack_no_seccomp_load = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta167-blocked-cleanup-ack-required"),
        )
        args.ack_cleanup_required = True
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_default_run_is_device_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            contract, script = self.write_contract_and_script(root)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta167"),
                "--wsta166-contract-json",
                str(contract),
                "--wsta166-remote-script",
                str(script),
            ]))
            saved = json.loads((root / "wsta167" / runner.RESULT_NAME).read_text(encoding="utf-8"))

        self.assertEqual(result["decision"], "wsta167-blocked-seccomp-live-observation-required")
        self.assertEqual(saved["decision"], result["decision"])
        self.assertTrue(result["checks"]["contract_valid"])
        for key in (
            "device_action",
            "boot_flash",
            "native_reboot",
            "wifi_connect",
            "dhcp",
            "public_tunnel",
            "packet_filter_mutation",
            "userdata_touch",
            "switch_root",
            "seccomp_filter_loaded",
            "seccomp_enforced",
        ):
            self.assertFalse(result["safety"][key])

    def test_validate_contract_rejects_correct_token_literal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract, script = self.write_contract_and_script(root)
            payload = json.loads(contract.read_text(encoding="utf-8"))
            script_text = script.read_text(encoding="utf-8")
            checks = runner.validate_contract(payload, script_text)
            self.assertTrue(all(checks.values()))

            bad = script_text + "\n" + runner.wsta166.CORRECT_WSTA161_TOKEN + "\n"
            bad_checks = runner.validate_contract(payload, bad)
            self.assertFalse(bad_checks["correct_token_literal_absent"])

    def test_parse_observation_requires_all_no_load_blocks(self) -> None:
        contract = {
            "scenario_names": [
                "no-load-env-gate",
                "load-env-gate-missing-token",
                "load-env-gate-wrong-token",
            ],
            "expected_scenario_returncode": 65,
        }
        stdout = "\n".join([
            "A90WSTA166_REMOTE_BEGIN",
            "A90WSTA166_SCENARIO_BEGIN name=no-load-env-gate",
            "a90_seccomp_loader_decision=blocked-load-gate-required",
            "A90WSTA166_SCENARIO_RC name=no-load-env-gate rc=65",
            "A90WSTA166_SCENARIO_END name=no-load-env-gate",
            "A90WSTA166_SCENARIO_BEGIN name=load-env-gate-missing-token",
            "a90_service_launcher_decision=blocked-seccomp-helper-load-token-required",
            "A90WSTA166_SCENARIO_RC name=load-env-gate-missing-token rc=65",
            "A90WSTA166_SCENARIO_END name=load-env-gate-missing-token",
            "A90WSTA166_SCENARIO_BEGIN name=load-env-gate-wrong-token",
            "a90_seccomp_loader_decision=blocked-load-token-required",
            "A90WSTA166_SCENARIO_RC name=load-env-gate-wrong-token rc=65",
            "A90WSTA166_SCENARIO_END name=load-env-gate-wrong-token",
            "A90WSTA166_REMOTE_DONE",
        ])
        parsed = runner.parse_observation(stdout, contract)
        self.assertTrue(all(parsed.values()))

        bad = runner.parse_observation(stdout + "\nA90WSTA161_SECCOMP_LOAD_ATTEMPT=1\n", contract)
        self.assertFalse(bad["load_attempt_absent"])

    def test_classify_orders_live_observation_requirements(self) -> None:
        checks = {
            "explicit_live_gate": True,
            "contract_valid": True,
            "local_inputs_present": True,
            "baseline_selftest_fail_zero": True,
            "native_stale_cleanup_ok": True,
            "remote_image_ready": True,
            "chroot_mount_ready": True,
            "dropbear_started": True,
            "debian_ssh_marker": True,
            "seccomp_assets_staged": True,
            "observation_pass": True,
            "chroot_cleanup_ok": True,
            "final_selftest_fail_zero": True,
        }
        self.assertEqual(runner.classify({"checks": checks}), runner.PASS_DECISION)
        for key, decision in (
            ("explicit_live_gate", "wsta167-blocked-explicit-live-gate"),
            ("contract_valid", "wsta167-blocked-contract-invalid"),
            ("seccomp_assets_staged", "wsta167-blocked-seccomp-assets-stage"),
            ("observation_pass", "wsta167-blocked-observation"),
            ("final_selftest_fail_zero", "wsta167-blocked-final-selftest"),
        ):
            self.assertEqual(runner.classify({"checks": {**checks, key: False}}), decision)


if __name__ == "__main__":
    unittest.main()
