#!/usr/bin/env python3
"""Focused P3.17 runtime, packaging, and Process-v2 wiring tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import build_s22plus_fyg8_p317_candidate as candidate_builder
import device_action_f1_evidence_v2 as evidence
import device_action_f1_live_v2 as live
import device_action_f1_v2 as process_v2
import prepare_s22plus_fyg8_p317_process_v2 as promotion
import prepare_s22plus_fyg8_p317_ready_manifest as ready_manifest
import s22plus_fyg8_p317_candidate_static_checker as static_checker
import s22plus_fyg8_p317_e2_stock_closure as stock_closure
import s22plus_fyg8_p317_lifecycle_audit as lifecycle
import s22plus_fyg8_p317_max77705_envelope_fixture as envelope_fixture
import s22plus_fyg8_p317_max77705_telemetry_decoder as decoder
import s22plus_fyg8_p317_overlay_contract as overlay
import s22plus_fyg8_p317_process_v2_adapter_fixture as adapter_fixture
import s22plus_fyg8_p317_qualification_closure as qualification
import s22plus_fyg8_p317_runtime_fixture as runtime_fixture


class P317ProcessV2Tests(unittest.TestCase):
    def test_complete_source_key_inventory_exists(self) -> None:
        missing = [
            key for key, relative in overlay.SOURCE_PATHS.items()
            if not (ROOT / relative).is_file()
        ]
        self.assertEqual(missing, [])
        self.assertEqual(
            overlay.SOURCE_PATHS["process_v2_runner"],
            overlay.PREFIX / "device_action_f1_v2.py",
        )

    def test_reviewed_gate_receipts_are_registered(self) -> None:
        gates = overlay._executability_gates(ROOT)  # noqa: SLF001
        self.assertEqual(
            gates["fixed_point"]["value"]["module_delta"]["added_early_module_count"],
            5,
        )
        self.assertEqual(
            gates["fixed_point"]["value"]["module_delta"]["successor_early_count"],
            69,
        )
        self.assertEqual(
            gates["fixed_point"]["value"]["module_delta"]["successor_effective_total_count"],
            70,
        )

    def test_intent_value_is_json_round_trip_stable(self) -> None:
        value = overlay.create_intent_value(ROOT)
        self.assertEqual(value, json.loads(json.dumps(value)))

    def test_runtime_fixture_executes_materialized_witnesses(self) -> None:
        value = runtime_fixture.audit(ROOT)
        self.assertEqual(value["provider_count"], 3)
        self.assertEqual(value["settle_sleep_count"], 49)
        self.assertTrue(value["actual_materialized_waiting_state_executed"])

    def test_lifecycle_inheritance_and_immediate_callers(self) -> None:
        value = lifecycle.audit(ROOT)
        self.assertTrue(value["inherited_helper_definitions_byte_identical"])
        self.assertEqual(value["p317_runtime_observer_callers"], 7)
        self.assertEqual(value["p317_wrapper_observer_callers"], 2)

    def test_native_envelope_and_real_adapter_are_complete(self) -> None:
        envelope = envelope_fixture.audit(ROOT)
        adapter = adapter_fixture.audit()
        self.assertEqual(envelope["row_count"], 105)
        self.assertEqual(envelope["observer_site_error_rows"], 84)
        self.assertTrue(envelope["byte_exact_python_authority"])
        self.assertTrue(adapter["verified"])

    def test_evidence_adapter_selects_exact_p317_decoder(self) -> None:
        selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
            overlay.PARENT_SOURCE_CONTRACT_ID, overlay.PROFILE, overlay.CONTRACT_ID
        )
        self.assertIs(selected, decoder)

    def test_process_v2_uses_exact_69_module_closure(self) -> None:
        self.assertIs(promotion.e2_closure_selector, stock_closure)
        self.assertEqual(stock_closure.EXPECTED_MODULE_COUNT, 69)
        self.assertEqual(len(stock_closure.ADDED_MODULES), 8)
        self.assertIs(
            evidence._select_e2_closure(  # noqa: SLF001
                evidence.P310_SOURCE_CONTRACT_ID, overlay.CONTRACT_ID
            ),
            stock_closure,
        )

    def test_evidence_uses_p317_stock_authority_for_p317_overlay(self) -> None:
        source = (
            ROOT / "workspace/public/src/scripts/revalidation/device_action_f1_evidence_v2.py"
        ).read_text(encoding="utf-8")
        branch = source.index(
            "if userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:",
            source.index("generic_module_closure = _generic_rootfs_module_closure"),
        )
        generic = source.index(
            "elif userspace_overlay_contract_id in MAX77705_OVERLAY_CONTRACT_IDS:",
            branch,
        )
        selected = source[branch:generic]
        self.assertIn("_p317_e2_authority_context", selected)
        self.assertNotIn("_p316_e2_authority_context", selected)

    def test_predecessor_order_is_preserved_by_insertion(self) -> None:
        names = tuple(name for name, _runtime in stock_closure.ADDED_MODULES)
        self.assertEqual(
            names,
            (
                "spmi-pmic-arb.ko", "pinctrl-spmi-gpio.ko",
                "qti-regmap-debugfs.ko", "regmap-spmi.ko",
                "qcom-spmi-pmic.ko", "msm-geni-se.ko", "gpi.ko",
                "i2c-msm-geni.ko",
            ),
        )

    def test_candidate_builder_calls_prepackaging_gate(self) -> None:
        tree = ast.parse(
            (ROOT / overlay.SOURCE_PATHS["p317_candidate_builder"]).read_text(
                encoding="utf-8"
            )
        )
        source = (ROOT / overlay.SOURCE_PATHS["p317_candidate_builder"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("base.build_candidate(args)", source)
        self.assertIn("qualification", source)
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == "artifact_safety" for node in ast.walk(tree)))

    def test_candidate_safety_uses_explicit_frozen_base_callback(self) -> None:
        source = (ROOT / overlay.SOURCE_PATHS["p317_candidate_builder"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("p310_builder._BASE_ARTIFACT_SAFETY", source)

    def test_diagnostic_is_late_only(self) -> None:
        self.assertEqual(
            candidate_builder.DIAGNOSTIC_RAMDISK_PATH,
            "lib/modules/s22plus_max77705_mux_diag.ko",
        )
        value = overlay.create_intent_value(ROOT)
        requirements = value["packaging_requirements"]
        self.assertEqual(requirements["early_stock_module_count"], 69)
        self.assertEqual(requirements["total_effective_module_count"], 70)
        self.assertTrue(requirements["diagnostic_absent_from_early_plan"])

    def test_candidate_static_exception_is_scoped_to_max77705(self) -> None:
        oversized = {
            "path": "candidate-static.json",
            "size": evidence.DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES + 1,
            "sha256": "0" * 64,
        }
        with self.assertRaises(evidence.EvidenceError):
            evidence._artifact(oversized, "ordinary")  # noqa: SLF001
        self.assertIs(
            evidence._artifact(  # noqa: SLF001
                oversized, "P3.17 static",
                maximum=evidence.P317_CANDIDATE_STATIC_MAX_BYTES,
            ),
            oversized,
        )
        p317_only = {
            **oversized,
            "size": evidence.P316_CANDIDATE_STATIC_MAX_BYTES + 1,
        }
        with self.assertRaises(evidence.EvidenceError):
            evidence._artifact(  # noqa: SLF001
                p317_only,
                "P3.16 static",
                maximum=evidence.P316_CANDIDATE_STATIC_MAX_BYTES,
            )
        self.assertIs(
            evidence._artifact(  # noqa: SLF001
                p317_only,
                "P3.17 static",
                maximum=evidence.P317_CANDIDATE_STATIC_MAX_BYTES,
            ),
            p317_only,
        )

    def test_guard_lifetime_applies_to_p317(self) -> None:
        bundle = SimpleNamespace(manifest={"observation": {"acceptance": {
            "userspace_overlay_contract_id": overlay.CONTRACT_ID
        }}})
        self.assertTrue(live._p313_bundle(bundle))  # noqa: SLF001

    def test_ready_manifest_wrapper_is_exact(self) -> None:
        self.assertEqual(ready_manifest.USERSPACE_OVERLAY_CONTRACT_ID, overlay.CONTRACT_ID)
        self.assertEqual(ready_manifest.SOURCE_CONTRACT_ID, overlay.PARENT_SOURCE_CONTRACT_ID)
        self.assertEqual(ready_manifest.DEFAULT_TIMEOUT_SEC, 300)

    def test_evidence_requires_p317_lifecycle_receipt(self) -> None:
        source = (
            ROOT / "workspace/public/src/scripts/revalidation/device_action_f1_evidence_v2.py"
        ).read_text(encoding="utf-8")
        start = source.index(
            "elif userspace_overlay_contract_id == P317_MAX77705_OVERLAY_CONTRACT_ID:"
        )
        end = source.index(
            "elif userspace_overlay_contract_id == MAX77705_OVERLAY_CONTRACT_ID:",
            start,
        )
        branch = source[start:end]
        self.assertIn("PASS_P317_LATE_LOADER_LIFECYCLE_HOST_ONLY", branch)
        self.assertNotIn("PASS_P316_LATE_LOADER_LIFECYCLE_HOST_ONLY", branch)

    def test_execution_sources_replace_parent_decoder(self) -> None:
        self.assertEqual(
            process_v2._overridden_candidate_sources(overlay.CONTRACT_ID),  # noqa: SLF001
            frozenset({"p310_telemetry_decoder"}),
        )

    def test_p317_overlay_intent_size_exception_is_name_and_overlay_scoped(self) -> None:
        self.assertEqual(
            process_v2._execution_source_maximum(  # noqa: SLF001
                "p317_overlay_intent", overlay.CONTRACT_ID
            ),
            2 * 1024 * 1024,
        )
        self.assertEqual(
            process_v2._execution_source_maximum(  # noqa: SLF001
                "ordinary_source", overlay.CONTRACT_ID
            ),
            process_v2.MAX_JSON,
        )
        self.assertEqual(
            process_v2._execution_source_maximum(  # noqa: SLF001
                "p317_overlay_intent", evidence.MAX77705_OVERLAY_CONTRACT_ID
            ),
            process_v2.MAX_JSON,
        )

    def test_qualification_has_distinct_prepackaging_schema(self) -> None:
        self.assertNotEqual(qualification.PREPACKAGING_SCHEMA, qualification.FINAL_SCHEMA)
        self.assertEqual(qualification.EXPECTED_MODULE_PLAN_COUNT, 69)

    def test_static_checker_emits_all_p317_proof_keys(self) -> None:
        source = (ROOT / overlay.SOURCE_PATHS["p317_static_checker"]).read_text(
            encoding="utf-8"
        )
        self.assertIn('result["p317_envelope_fixture"]', source)
        self.assertIn('result["p317_executability_fixed_point"]', source)
        self.assertEqual(static_checker.RESULT_PREFIX, "p317")


if __name__ == "__main__":
    unittest.main()
