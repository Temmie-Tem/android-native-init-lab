from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/server-distro/run_wsta216_default_drop_hardening_policy.py"
)


class ServerDistroWsta216DefaultDropHardeningPolicyTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def operator_status(self) -> dict:
        return {
            "decision": "wsta108-operator-server-status-source-pass",
            "checks": {
                "packet_filter_loopback_live_proven": True,
                "packet_filter_control_plane_live_proven": True,
                "preferred_hardening_lever_legacy_iptables": True,
            },
            "server_status": {
                "exposure": {
                    "public_state": "PUBLIC_OFF",
                    "default_public_off": True,
                },
                "packet_filter": {
                    "state": "READY",
                    "ready": True,
                },
                "hardening": {
                    "packet_filter_proof": {
                        "state": "PACKET_FILTER_LOOPBACK_AND_CONTROL_PLANE_LIVE_PROVEN",
                        "backend": "legacy-iptables",
                        "policy": "loopback-default-drop",
                        "loopback_live_proven": True,
                        "restore_exact": True,
                        "final_selftest_fail_zero": True,
                        "control_proof": {
                            "control_plane_live_proven": True,
                            "control_session_after_apply": True,
                            "cleanup_ok": True,
                        },
                    },
                    "apparmor_feasibility": {
                        "state": "APPARMOR_NOT_AVAILABLE_UNDER_CURRENT_EVIDENCE",
                        "apparmor_unavailable_under_current_evidence": True,
                        "profile_load_allowed": False,
                        "preferred_current_hardening_lever": "legacy-iptables-loopback-default-drop",
                    },
                },
                "operator_next_actions": [
                    "keep-public-exposure-default-off",
                    "use-explicit-wsta88-live-gate-only-when-attended",
                    "continue-containment-hardening-with-legacy-iptables-default-drop",
                    "move-to-legacy-iptables-default-drop-hardening",
                ],
            },
        }

    def wsta94_proof(self) -> dict:
        return {
            "decision": "wsta94-packet-filter-loopback-live-pass",
            "checks": {
                "packet_filter_preflight_pass": True,
                "packet_filter_apply_pass": True,
                "packet_filter_default_drop_observed": True,
                "loopback_before_ok": True,
                "loopback_after_ok": True,
                "packet_filter_restore_pass": True,
                "packet_filter_restore_exact": True,
                "chroot_cleanup_ok": True,
                "final_selftest_fail_zero": True,
                "public_url_value_logged": False,
                "secret_values_logged": 0,
            },
            "packet_filter_probe": {
                "stdout": "\n".join([
                    "packet_filter_backend=legacy-iptables",
                    "packet_filter_policy_class=loopback-default-drop",
                    "-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
                ]),
                "parsed": {
                    "preflight_pass": True,
                    "apply_pass": True,
                    "loopback_before_ok": True,
                    "loopback_after_ok": True,
                    "v4_input_drop": True,
                    "v4_forward_drop": True,
                    "v6_input_drop": True,
                    "v4_loopback_accept": True,
                    "v6_loopback_accept": True,
                    "restore_exact_v4": True,
                    "restore_exact_v6": True,
                    "restore_pass": True,
                },
            },
        }

    def control_summary(self) -> dict:
        return {
            "packet_filter_preflight_rc": 0,
            "packet_filter_preflight_parsed": {
                "packet_filter_backend": "legacy-iptables",
                "packet_filter_policy_class": "loopback-default-drop",
                "packet_filter_apply_autostart": "0",
                "packet_filter_secret_values_logged": "0",
            },
            "packet_filter_apply_loopback_default_drop_rc": 0,
            "packet_filter_apply_loopback_default_drop_parsed": {
                "packet_filter_decision": "packet-filter-loopback-default-drop-applied",
                "packet_filter_backend": "legacy-iptables",
                "packet_filter_policy_class": "loopback-default-drop",
                "packet_filter_saved_before": "1",
                "packet_filter_loopback_accept": "1",
                "packet_filter_input_default": "DROP",
                "packet_filter_forward_default": "DROP",
                "packet_filter_output_default": "ACCEPT",
                "packet_filter_control_ssh_accept": "1",
                "packet_filter_secret_values_logged": "0",
            },
            "packet_filter_restore_rc": 0,
            "packet_filter_restore_ok": True,
            "ssh_before_marker": True,
            "ssh_after_apply_marker": True,
            "post_mount_absent": True,
            "post_loop_absent": True,
            "post_dropbear_absent": True,
        }

    def run_valid_policy(self):
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            proof_path = root / "inputs" / "wsta94_result.json"
            control_path = root / "inputs" / "packet_filter_control_summary.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(proof_path, self.wsta94_proof())
            self.write_json(control_path, self.control_summary())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta216"),
                "--wsta215-operator-status-json",
                str(status_path),
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
                "--packet-filter-control-summary-json",
                str(control_path),
                "--emit-default-drop-hardening-policy",
            ]))
            policy = json.loads((root / "wsta216" / runner.POLICY_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta216" / runner.MARKDOWN_NAME).read_text(encoding="utf-8")
        return result, policy, markdown

    def test_valid_evidence_emits_default_drop_hardening_policy(self) -> None:
        result, policy, markdown = self.run_valid_policy()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(policy["schema"], runner.POLICY_SCHEMA)
        self.assertEqual(policy["state"], runner.POLICY_STATE)
        self.assertEqual(policy["backend"], "legacy-iptables")
        self.assertEqual(policy["policy"], "loopback-default-drop")
        self.assertEqual(policy["activation"], "explicit-operator-gated")
        self.assertFalse(policy["live_execution_requested"])
        self.assertFalse(result["safety"]["packet_filter_mutation"])
        self.assertTrue(policy["rules_contract"]["control_plane_accept"])
        self.assertIn("apply-loopback-default-drop-before-public-exposure", policy["lifecycle"]["required_sequence"])
        self.assertTrue(result["checks"]["operator_status_required_next_actions_present"])
        self.assertTrue(result["checks"]["source_wiring_wsta79_accepts_contract"])
        self.assertIn("Hardening lever: `legacy-iptables-loopback-default-drop`", markdown)
        self.assertIn("Packet-filter mutation: `false`", markdown)

    def test_gate_blocks_without_explicit_flag_or_private_inputs(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            proof_path = root / "inputs" / "wsta94_result.json"
            control_path = root / "inputs" / "packet_filter_control_summary.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(proof_path, self.wsta94_proof())
            self.write_json(control_path, self.control_summary())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta216"),
                "--wsta215-operator-status-json",
                str(status_path),
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
                "--packet-filter-control-summary-json",
                str(control_path),
            ]))
        self.assertEqual(result["decision"], "wsta216-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "wsta108_operator_server_status.json"
            proof_path = root / "wsta94_result.json"
            control_path = root / "packet_filter_control_summary.json"
            self.write_json(status_path, self.operator_status())
            self.write_json(proof_path, self.wsta94_proof())
            self.write_json(control_path, self.control_summary())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta216"),
                "--wsta215-operator-status-json",
                str(status_path),
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
                "--packet-filter-control-summary-json",
                str(control_path),
                "--emit-default-drop-hardening-policy",
            ]))
        self.assertEqual(result["decision"], "wsta216-blocked-nonprivate-run-dir")

    def test_source_evidence_must_prove_control_plane_survives_apply(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            status = self.operator_status()
            proof = self.wsta94_proof()
            control = self.control_summary()
            control["ssh_after_apply_marker"] = False
            status_path = root / "inputs" / "wsta108_operator_server_status.json"
            proof_path = root / "inputs" / "wsta94_result.json"
            control_path = root / "inputs" / "packet_filter_control_summary.json"
            self.write_json(status_path, status)
            self.write_json(proof_path, proof)
            self.write_json(control_path, control)
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta216"),
                "--wsta215-operator-status-json",
                str(status_path),
                "--wsta94-packet-filter-proof-json",
                str(proof_path),
                "--packet-filter-control-summary-json",
                str(control_path),
                "--emit-default-drop-hardening-policy",
            ]))
        self.assertEqual(result["decision"], "wsta216-blocked-source-evidence-incomplete")
        self.assertFalse(result["checks"]["control_summary_ssh_before_after_apply"])

    def test_policy_validation_catches_live_execution_regression(self) -> None:
        _result, policy, _markdown = self.run_valid_policy()
        self.assertTrue(runner.validate_policy(policy)["no_live_execution"])
        policy["live_execution_requested"] = True
        self.assertFalse(runner.validate_policy(policy)["no_live_execution"])


if __name__ == "__main__":
    unittest.main()
