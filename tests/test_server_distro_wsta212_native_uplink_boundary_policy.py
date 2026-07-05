from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script(
    "workspace/public/src/scripts/server-distro/run_wsta212_native_uplink_boundary_policy.py"
)


class ServerDistroWsta212NativeUplinkBoundaryPolicyTests(unittest.TestCase):
    def private_tmp(self):
        runner.DEFAULT_RUN_BASE.mkdir(parents=True, exist_ok=True)
        return tempfile.TemporaryDirectory(dir=runner.DEFAULT_RUN_BASE)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def manifest_result(self) -> dict:
        return {
            "decision": "wsta90-service-hardening-manifest-source-pass",
            "manifest": {
                "global_policy": {
                    "default_public_off": True,
                },
                "services": [
                    {
                        "name": "wsta-native-uplink-helper",
                        "target_user": "root-native-boundary",
                        "target_group": "root-native-boundary",
                        "network_intent": "native-owned-wifi-control-only",
                        "seccomp_profile": "native-uplink-boundary",
                        "status": "boundary-preserve",
                        "ambient_capabilities": [],
                        "bounding_capabilities": [],
                        "proof_gaps": [
                            "keep credential handling in native-owned service boundary",
                        ],
                    },
                ],
            },
        }

    def wsta22_result(self) -> dict:
        return {
            "decision": "wsta22-native-wifi-service-client-pass",
            "checks": {
                "helper_status_pass": True,
                "helper_scan_pass": True,
                "service_start_pass": True,
                "service_stop_pass": True,
                "final_selftest_fail_zero": True,
            },
            "helper_status": {
                "parsed": {
                    "op": "status",
                    "owner": "native-init",
                    "decision": "wifi-service-status-pass",
                    "native_wifi_service_client_decision": "native-wifi-service-client-pass",
                    "native_wifi_service_client_secret_values_logged": "0",
                    "credentials": "0",
                    "dhcp_routing": "0",
                    "public_tunnel": "0",
                },
            },
            "helper_scan": {
                "parsed": {
                    "op": "scan",
                    "owner": "native-init",
                    "decision": "wifi-scan-pass",
                    "native_wifi_service_client_decision": "native-wifi-service-client-pass",
                    "native_wifi_service_client_secret_values_logged": "0",
                    "credentials": "0",
                    "connect": "0",
                    "dhcp_routing": "0",
                    "public_tunnel": "0",
                    "raw_results_redacted": "1",
                },
            },
            "safety": {
                "service_supported_ops": ["status", "scan"],
                "wifi_association": False,
                "dhcp": False,
                "ping": False,
                "public_tunnel": False,
                "userdata_touch": False,
                "switch_root": False,
            },
        }

    def wsta154_model(self) -> dict:
        return {
            "schema": "a90-wsta154-seccomp-launcher-gate-model-v1",
            "state": "SECCOMP_LAUNCHER_DRY_RUN_GATE_MODEL_SOURCE_DEFINED",
            "enforcement_state": "MODEL_ONLY_NOT_ENFORCED",
            "excluded_boundaries": [
                {
                    "name": "wsta-native-uplink-helper",
                    "launchable_under_debian_service_seccomp": False,
                    "reason": "native Wi-Fi boundary",
                },
                {
                    "name": "native-dpublic-hud-presenter",
                    "launchable_under_debian_service_seccomp": False,
                    "reason": "native KMS owner",
                },
            ],
        }

    def run_valid_policy(self):
        with self.private_tmp() as tmp:
            root = Path(tmp)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            wsta22_path = root / "inputs" / "wsta22_result.json"
            model_path = root / "inputs" / "wsta154_seccomp_launcher_gate_model.json"
            self.write_json(manifest_path, self.manifest_result())
            self.write_json(wsta22_path, self.wsta22_result())
            self.write_json(model_path, self.wsta154_model())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta212"),
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta22-native-wifi-service-client-json",
                str(wsta22_path),
                "--wsta154-seccomp-launcher-gate-model-json",
                str(model_path),
                "--emit-native-uplink-boundary-policy",
            ]))
            policy = json.loads((root / "wsta212" / runner.POLICY_NAME).read_text(encoding="utf-8"))
            markdown = (root / "wsta212" / runner.MARKDOWN_NAME).read_text(encoding="utf-8")
        return result, policy, markdown

    def test_valid_evidence_emits_native_uplink_boundary_policy(self) -> None:
        result, policy, markdown = self.run_valid_policy()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertEqual(policy["schema"], runner.POLICY_SCHEMA)
        self.assertEqual(policy["state"], runner.POLICY_STATE)
        self.assertEqual(policy["service"], "wsta-native-uplink-helper")
        self.assertEqual(policy["classification"], "native-owned-root-boundary")
        boundary = policy["boundary_contract"]
        self.assertEqual(boundary["debian_allowed_ops"], ["status", "scan"])
        self.assertIn("connect", boundary["debian_denied_ops"])
        self.assertIn("public-tunnel", boundary["debian_denied_ops"])
        self.assertFalse(boundary["debian_may_start_association"])
        self.assertFalse(boundary["debian_may_run_dhcp"])
        self.assertFalse(boundary["debian_may_start_public_tunnel"])
        self.assertFalse(boundary["debian_may_read_wifi_credentials"])
        self.assertFalse(policy["launcher_policy"]["launchable_under_debian_service_launcher"])
        self.assertFalse(policy["launcher_policy"]["launchable_under_debian_service_seccomp"])
        self.assertTrue(result["checks"]["wsta22_live_status_no_credentials_or_public"])
        self.assertTrue(result["checks"]["helper_source_denies_before_request_write"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertIn("Allowed ops: `status, scan`", markdown)
        self.assertIn("Debian service launcher allowed: `false`", markdown)

    def test_gate_blocks_without_explicit_flag_or_private_inputs(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
            wsta22_path = root / "inputs" / "wsta22_result.json"
            model_path = root / "inputs" / "wsta154_seccomp_launcher_gate_model.json"
            self.write_json(manifest_path, self.manifest_result())
            self.write_json(wsta22_path, self.wsta22_result())
            self.write_json(model_path, self.wsta154_model())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta212"),
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta22-native-wifi-service-client-json",
                str(wsta22_path),
                "--wsta154-seccomp-launcher-gate-model-json",
                str(model_path),
            ]))
        self.assertEqual(result["decision"], "wsta212-blocked-explicit-gate-required")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "wsta90_service_hardening_manifest.json"
            wsta22_path = root / "wsta22_result.json"
            model_path = root / "wsta154_seccomp_launcher_gate_model.json"
            self.write_json(manifest_path, self.manifest_result())
            self.write_json(wsta22_path, self.wsta22_result())
            self.write_json(model_path, self.wsta154_model())
            result = runner.run(runner.build_arg_parser().parse_args([
                "--run-dir",
                str(root / "wsta212"),
                "--wsta90-service-hardening-manifest-json",
                str(manifest_path),
                "--wsta22-native-wifi-service-client-json",
                str(wsta22_path),
                "--wsta154-seccomp-launcher-gate-model-json",
                str(model_path),
                "--emit-native-uplink-boundary-policy",
            ]))
        self.assertEqual(result["decision"], "wsta212-blocked-nonprivate-run-dir")

    def test_source_evidence_must_prove_native_owned_status_scan_boundary(self) -> None:
        cases = []

        def manifest_not_boundary(manifest: dict, _wsta22: dict, _model: dict) -> None:
            manifest["manifest"]["services"][0]["status"] = "regular-service"

        def scan_not_redacted(_manifest: dict, wsta22: dict, _model: dict) -> None:
            wsta22["helper_scan"]["parsed"]["raw_results_redacted"] = "0"

        def public_tunnel_started(_manifest: dict, wsta22: dict, _model: dict) -> None:
            wsta22["helper_status"]["parsed"]["public_tunnel"] = "1"

        def uplink_not_excluded(_manifest: dict, _wsta22: dict, model: dict) -> None:
            model["excluded_boundaries"][0]["launchable_under_debian_service_seccomp"] = True

        cases.extend([manifest_not_boundary, scan_not_redacted, public_tunnel_started, uplink_not_excluded])
        for mutate in cases:
            with self.subTest(mutation=mutate.__name__), self.private_tmp() as tmp:
                root = Path(tmp)
                manifest = self.manifest_result()
                wsta22 = self.wsta22_result()
                model = self.wsta154_model()
                mutate(manifest, wsta22, model)
                manifest_path = root / "inputs" / "wsta90_service_hardening_manifest.json"
                wsta22_path = root / "inputs" / "wsta22_result.json"
                model_path = root / "inputs" / "wsta154_seccomp_launcher_gate_model.json"
                self.write_json(manifest_path, manifest)
                self.write_json(wsta22_path, wsta22)
                self.write_json(model_path, model)
                result = runner.run(runner.build_arg_parser().parse_args([
                    "--run-dir",
                    str(root / "wsta212"),
                    "--wsta90-service-hardening-manifest-json",
                    str(manifest_path),
                    "--wsta22-native-wifi-service-client-json",
                    str(wsta22_path),
                    "--wsta154-seccomp-launcher-gate-model-json",
                    str(model_path),
                    "--emit-native-uplink-boundary-policy",
                ]))
            self.assertEqual(result["decision"], "wsta212-blocked-source-evidence-incomplete")

    def test_policy_validation_catches_debian_connectivity_regression(self) -> None:
        _, policy, _ = self.run_valid_policy()
        self.assertTrue(runner.validate_policy(policy)["debian_cannot_start_connectivity"])
        policy["boundary_contract"]["debian_may_run_dhcp"] = True
        self.assertFalse(runner.validate_policy(policy)["debian_cannot_start_connectivity"])


if __name__ == "__main__":
    unittest.main()
