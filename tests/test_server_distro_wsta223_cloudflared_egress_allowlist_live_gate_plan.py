from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/server-distro/run_wsta223_cloudflared_egress_allowlist_live_gate_plan.py"
)


class ServerDistroWsta223CloudflaredEgressAllowlistLiveGatePlanTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def operator_status(self) -> dict:
        return {
            "decision": runner.WSTA108_PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta222-test",
            "checks": {
                "wsta221_cloudflared_egress_allowlist_policy_supplied": True,
                "cloudflared_egress_allowlist_policy_defined": True,
                "cloudflared_egress_allowlist_no_live_execution": True,
                "cloudflared_egress_allowlist_no_mutation_here": True,
                "cloudflared_egress_allowlist_owner_match_fail_closed": True,
                "cloudflared_egress_allowlist_preserves_default_drop": True,
            },
            "server_status": {
                "exposure": {
                    "public_state": "PUBLIC_OFF",
                    "default_public_off": True,
                },
                "operator_next_actions": [
                    "keep-public-exposure-default-off",
                    "use-explicit-wsta88-live-gate-only-when-attended",
                    "prepare-attended-cloudflared-egress-allowlist-live-gate",
                    "move-to-cloudflared-egress-allowlist-live-gate",
                ],
                "hardening": {
                    "cloudflared_egress_allowlist_policy": {
                        "decision": runner.wsta221.PASS_DECISION,
                        "state": runner.wsta221.POLICY_STATE,
                        "cloudflared_egress_allowlist_policy_defined": True,
                        "hardening_lever": runner.wsta221.HARDENING_LEVER,
                        "service": runner.wsta221.SERVICE,
                        "target_user": runner.wsta221.SERVICE_USER,
                        "target_uid": runner.wsta221.SERVICE_UID,
                        "default_public_off": True,
                        "live_execution_requested": False,
                        "packet_filter_mutation_by_wsta221": False,
                        "owner_match_fail_closed": True,
                        "preserve_existing_default_drop": True,
                        "restore_exact_required": True,
                        "control_plane_must_survive_apply": True,
                        "public_url_value_logged": False,
                        "secret_values_logged": 0,
                    },
                },
            },
        }

    def wsta221_policy(self) -> dict:
        policy = {
            "schema": runner.wsta221.POLICY_SCHEMA,
            "state": runner.wsta221.POLICY_STATE,
            "hardening_lever": runner.wsta221.HARDENING_LEVER,
            "service": runner.wsta221.SERVICE,
            "backend": "legacy-iptables",
            "policy": "cloudflared-egress-allowlist",
            "activation": "explicit-operator-gated-after-default-drop",
            "default_public_off": True,
            "live_execution_requested": False,
            "packet_filter_mutation_by_wsta221": False,
            "target_identity": {
                "user": runner.wsta221.SERVICE_USER,
                "uid": runner.wsta221.SERVICE_UID,
                "gid": runner.wsta221.SERVICE_GID,
            },
            "policy_contract": {
                "preserve_existing_input_default_drop": True,
                "apply_after_loopback_default_drop": True,
                "save_existing_rules_before_mutation": True,
                "restore_exact_rules_before_public_off_success": True,
                "control_plane_must_survive_apply": True,
                "fail_closed_if_owner_match_unavailable": True,
                "fail_closed_if_dns_or_tls_route_unresolved": True,
                "forbid_public_url_logging": True,
                "forbid_secret_logging": True,
            },
            "candidate_rule_shape": {
                "chain": "OUTPUT",
                "owner_match": {
                    "uid_owner": runner.wsta221.SERVICE_UID,
                    "user": runner.wsta221.SERVICE_USER,
                },
                "allow_loopback": True,
                "allow_established_related": True,
                "allow_dns": "route-resolved-live-preflight-required",
                "allow_tls": "route-resolved-live-preflight-required",
                "default_for_service": "REJECT-or-DROP-after-live-preflight",
                "global_output_default": "unchanged-until-live-proof",
            },
            "next_live_gate_requirements": list(runner.REQUIRED_POLICY_REQUIREMENTS),
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        return {
            "decision": runner.wsta221.PASS_DECISION,
            "run_dir": "workspace/private/runs/server-distro/wsta221-test",
            "policy": policy,
            "checks": {
                "operator_status_ready": True,
                "cloudflared_model_ready": True,
                "cloudflared_runtime_ready": True,
                "policy_ready": True,
            },
            "safety": {
                "device_action": False,
                "packet_filter_mutation": False,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
        }

    def run_valid_plan(self):
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            policy_path = root / "inputs" / "wsta221_result.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(policy_path, self.wsta221_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta223"),
                "--emit-live-gate-plan",
                "--wsta222-operator-status-json",
                str(status_path),
                "--wsta221-policy-json",
                str(policy_path),
            ]))
            plan = json.loads((root / "wsta223" / runner.PLAN_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta223" / runner.MARKDOWN_NAME).read_text(encoding="utf-8")
        return result, plan, markdown

    def test_valid_status_and_policy_emit_live_gate_plan(self) -> None:
        result, plan, markdown = self.run_valid_plan()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(result["checks"]["operator_status_ready"])
        self.assertTrue(result["checks"]["wsta221_policy_ready"])
        self.assertTrue(result["checks"]["plan_ready"])
        self.assertEqual(plan["schema"], runner.PLAN_SCHEMA)
        self.assertEqual(plan["state"], runner.PLAN_STATE)
        self.assertEqual(plan["service"], runner.wsta221.SERVICE)
        self.assertFalse(plan["live_execution_requested"])
        self.assertFalse(plan["packet_filter_mutation_by_wsta223"])
        self.assertTrue(plan["blocked_until_source_exists"])
        self.assertIn("apply-cloudflared-egress-allowlist", plan["required_helper_ops"])
        self.assertIn("--force-cloudflared-egress-allowlist-proof", plan["required_operator_acknowledgements"])
        self.assertEqual(plan["candidate_rule_shape"]["owner_match"]["uid_owner"], runner.wsta221.SERVICE_UID)
        self.assertIn("State: `CLOUDFLARED_EGRESS_ALLOWLIST_LIVE_GATE_PLANNED`", markdown)

    def test_gate_blocks_without_explicit_flag_or_private_inputs(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            policy_path = root / "inputs" / "wsta221_result.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(policy_path, self.wsta221_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta223"),
                "--wsta222-operator-status-json",
                str(status_path),
                "--wsta221-policy-json",
                str(policy_path),
            ]))
        self.assertEqual(result["decision"], "wsta223-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "wsta108_operator_server_status.json"
            policy_path = root / "wsta221_result.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(policy_path, self.wsta221_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta223"),
                "--emit-live-gate-plan",
                "--wsta222-operator-status-json",
                str(status_path),
                "--wsta221-policy-json",
                str(policy_path),
            ]))
        self.assertEqual(result["decision"], "wsta223-blocked-nonprivate-run-dir")

    def test_status_must_have_concrete_egress_allowlist_next_action(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status = self.operator_status()
            status["server_status"]["operator_next_actions"] = [
                "keep-public-exposure-default-off",
                "move-to-next-hardening-layer-after-attended-default-drop-live",
            ]
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            policy_path = root / "inputs" / "wsta221_result.json"
            self.write_json(status_path, status)
            self.write_json(policy_path, self.wsta221_policy())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta223"),
                "--emit-live-gate-plan",
                "--wsta222-operator-status-json",
                str(status_path),
                "--wsta221-policy-json",
                str(policy_path),
            ]))

        self.assertEqual(result["decision"], "wsta223-blocked-operator-status-incomplete")
        self.assertFalse(result["checks"]["operator_required_actions_present"])
        self.assertFalse(result["checks"]["operator_abstract_next_action_retired"])

    def test_policy_must_stay_no_mutation_and_owner_scoped(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            policy = self.wsta221_policy()
            policy["policy"]["packet_filter_mutation_by_wsta221"] = True
            policy["policy"]["candidate_rule_shape"]["owner_match"]["uid_owner"] = 0
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            policy_path = root / "inputs" / "wsta221_result.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(policy_path, policy)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta223"),
                "--emit-live-gate-plan",
                "--wsta222-operator-status-json",
                str(status_path),
                "--wsta221-policy-json",
                str(policy_path),
            ]))

        self.assertEqual(result["decision"], "wsta223-blocked-wsta221-policy-incomplete")
        self.assertFalse(result["checks"]["policy_no_packet_filter_mutation_in_policy"])
        self.assertFalse(result["checks"]["policy_target_uid_owner_ok"])

    def test_plan_validation_catches_helper_or_ack_regression(self) -> None:
        _result, plan, _markdown = self.run_valid_plan()
        self.assertTrue(runner.validate_plan(plan)["helper_ops_complete"])
        self.assertTrue(runner.validate_plan(plan)["operator_acks_complete"])
        plan["required_helper_ops"].remove("restore")
        plan["required_operator_acknowledgements"].remove("--force-control-plane-proof")
        checks = runner.validate_plan(plan)
        self.assertFalse(checks["helper_ops_complete"])
        self.assertFalse(checks["operator_acks_complete"])


if __name__ == "__main__":
    unittest.main()
