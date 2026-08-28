"""Small host-only checks for the dormant S22+ transient-action catalog."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs/operations/targets/S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md"
COMMON = ROOT / "AGENTS.md"
TARGET = ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md"
RISK = ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md"
PROCESS = ROOT / "docs/operations/DEVICE_ACTION_PROCESS_V2.md"


def load_policy() -> tuple[dict, str]:
    text = POLICY.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError("policy must contain one JSON declaration")
    return json.loads(blocks[0]), text


class S22PlusPreF1CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy, cls.text = load_policy()
        cls.common = COMMON.read_text(encoding="utf-8")
        cls.target = TARGET.read_text(encoding="utf-8")
        cls.risk = RISK.read_text(encoding="utf-8")
        cls.process = PROCESS.read_text(encoding="utf-8")

    def test_definition_is_exact_and_not_active(self) -> None:
        self.assertEqual(
            self.policy["schema"],
            "s22plus_fyg8_pre_f1_autonomous_action_catalog_v1",
        )
        self.assertEqual(self.policy["status"], "DEFINED_NOT_ACTIVE")
        self.assertEqual(
            self.policy["target"],
            {
                "model": "SM-S906N",
                "device": "g0q",
                "build": "S906NKSS7FYG8",
                "other_target_commands": 0,
            },
        )
        activation = self.policy["activation"]
        self.assertEqual(activation["mode"], "one_fresh_attended_session")
        self.assertEqual(activation["catalog_hash"], "required_at_activation")
        self.assertEqual(activation["effect_core_hash"], "required_at_activation")
        for key in (
            "mechanically_activated",
            "activation_manifest_present",
            "live_session_approval_present",
            "current_live_authority",
            "implicit_activation",
        ):
            self.assertIs(activation[key], False)
        required = {
            "exact_coordinator_runner",
            "versioned_catalog",
            "hostile_tests",
            "independent_pass_go",
            "activation_manifest",
            "fresh_attended_live_session_approval",
            "exact_live_target_and_topology",
        }
        self.assertTrue(required.issubset(activation["requires"]))
        self.assertIn("not a runner, coordinator", self.text)

    def test_campaign_is_finite_monotonic_and_bounded(self) -> None:
        campaign = self.policy["campaign"]
        self.assertTrue(campaign["finite"])
        self.assertTrue(campaign["monotonic"])
        self.assertFalse(campaign["renewable"])
        self.assertFalse(campaign["resettable"])
        self.assertTrue(campaign["one_open_campaign"])
        self.assertTrue(campaign["new_campaign_requires_fresh_activation"])
        self.assertTrue(campaign["f1_requires_campaign_closed"])
        self.assertEqual(campaign["d1_effect_max"], 8)
        self.assertEqual(campaign["d0_command_group_max"], 256)
        self.assertEqual(campaign["duration_seconds"], 43_200)
        self.assertTrue(campaign["journal_root"].startswith("workspace/private/"))
        self.assertNotIn("..", Path(campaign["journal_root"]).parts)

    def test_catalog_contains_only_reviewed_transient_classes(self) -> None:
        classes = self.policy["catalog"]["classes"]
        self.assertEqual(
            {entry["id"] for entry in classes},
            {
                "bounded_raw_first_read",
                "normal_android_reboot_health",
                "payload_free_download_roundtrip",
                "fixed_privileged_usb_role_or_udc_transient",
            },
        )
        by_id = {entry["id"]: entry for entry in classes}
        self.assertEqual(by_id["bounded_raw_first_read"]["tier"], "D0")
        self.assertEqual(by_id["normal_android_reboot_health"]["tier"], "D1")
        download = by_id["payload_free_download_roundtrip"]
        self.assertEqual(download["eligibility"], "automatic_return_proof_required")
        self.assertEqual(download["return_command"], "/usr/bin/odin4 --reboot -d <bound-endpoint>")
        self.assertIs(download["payload"], False)
        usb = by_id["fixed_privileged_usb_role_or_udc_transient"]
        self.assertIs(usb["privileged"], True)
        self.assertEqual(usb["descriptor"], "fixed_literal_node_and_value_bound_at_activation")
        self.assertEqual(usb["restore_or_reboot_proof"], "required")
        self.assertEqual(
            self.policy["catalog"]["recovery_entry"],
            "eligible_only_after_automatic_return_proof",
        )

    def test_accounting_and_repairs_preserve_no_replay(self) -> None:
        accounting = self.policy["effect_accounting"]
        self.assertIs(accounting["pre_intent_host_failure_consumes"], False)
        self.assertIs(accounting["intent_is_immediately_before_first_device_command"], True)
        self.assertIs(accounting["durable_effect_intent_consumes_one_ordinal"], True)
        self.assertEqual(
            accounting["post_intent_pre_command_cut"],
            "uncertain_consumed_no_replay",
        )
        self.assertIs(accounting["fresh_target_health_recheck_before_intent"], True)
        self.assertIs(accounting["uncertain_command_replay"], False)
        self.assertIs(accounting["next_effect_requires_exact_healthy_return"], True)
        self.assertEqual(
            accounting["stop_state"], "park_for_operator_return_and_passive_reads_only"
        )
        repair = self.policy["repair"]
        self.assertIs(repair["observer_parser_reporting_h0_if_effect_core_unchanged"], True)
        self.assertIs(repair["zero_new_device_command_surface"], True)
        self.assertEqual(
            repair["core_selector_state_or_recovery_drift"],
            "fresh_review_and_activation",
        )
        self.assertIs(repair["consumed_ordinal_replay"], False)
        self.assertEqual(
            self.policy["evidence"],
            {
                "one_machine_receipt_per_ordinal": True,
                "one_campaign_summary": True,
                "per_read_prose_review": False,
            },
        )

    def test_forbidden_surface_and_contract_delegation_are_explicit(self) -> None:
        forbidden = set(self.policy["forbidden"])
        self.assertTrue(
            {
                "unattended_f1",
                "kernel_module_load_or_unload",
                "panic_or_crash_injection",
                "runtime_code_payload",
                "f1_or_partition_transfer",
                "generic_root_or_su",
                "arbitrary_sysfs_configfs_path_or_value",
                "persistent_property_service_security_configuration_write",
                "package_shared_storage_userdata_write",
                "odin_payload_transfer",
            }.issubset(forbidden)
        )
        for text in (self.common, self.target, self.risk):
            self.assertIn("S22+", text)
        self.assertIn("S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md", self.common)
        self.assertIn("S22PLUS_FYG8_PREF1_AUTONOMOUS_RESEARCH_POLICY_V1.md", self.target)
        self.assertIn("DEFINED_NOT_ACTIVE", self.common)
        self.assertIn("DEFINED_NOT_ACTIVE", self.target)
        self.assertIn("pre-F1", self.risk)

    def test_policy_unit_has_no_runner_or_device_result(self) -> None:
        self.assertLessEqual(len(self.text.splitlines()), 180)
        self.assertFalse(
            (ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_pref1_autonomous_research.py").exists()
        )
        self.assertNotIn("PASS_GO", self.policy["status"])
        self.assertIn("No readiness label", self.text)
        self.assertIn("F1 remains attended", self.text)

if __name__ == "__main__":
    unittest.main()
