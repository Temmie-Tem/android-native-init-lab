#!/usr/bin/env python3
"""Focused P3.16 packaging and Process-v2 wiring tests."""

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

import build_s22plus_fyg8_p316_candidate as candidate_builder
import device_action_f1_evidence_v2 as evidence
import device_action_f1_live_v2 as live
import device_action_f1_v2 as process_v2
import prepare_s22plus_fyg8_p316_process_v2 as promotion
import prepare_s22plus_fyg8_p316_ready_manifest as ready_manifest
import s22plus_fyg8_max77705_telemetry_decoder as decoder
import s22plus_fyg8_p316_e2_stock_closure as stock_closure
import s22plus_fyg8_p316_overlay_contract as overlay
import s22plus_fyg8_p316_qualification_closure as qualification

class P316ProcessV2Tests(unittest.TestCase):
    def test_complete_source_key_inventory_exists(self) -> None:
        missing = [
            key
            for key, relative in overlay.SOURCE_PATHS.items()
            if not (ROOT / relative).is_file()
        ]
        self.assertEqual(missing, [])
        self.assertEqual(
            overlay.SOURCE_PATHS["process_v2_runner"],
            overlay.PREFIX / "device_action_f1_v2.py",
        )

    def test_parent_authority_is_frozen_p315_not_current_source_replay(self) -> None:
        parent = overlay.verify_parent(ROOT)
        self.assertEqual(parent["contract_id"], overlay.parent.CONTRACT_ID)
        self.assertEqual(
            parent["overlay_intent"], overlay.generator.EXPECTED_P315_INTENT
        )
        source = (ROOT / overlay.SOURCE_PATHS["p316_overlay_contract"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("generator._frozen_bytes", source)
        self.assertNotIn("parent.verify_intent(root", source)

    def test_max77705_surface_gate_reads_nested_linked_validation(self) -> None:
        gate = overlay._surface_gate(ROOT)  # noqa: SLF001
        validation = gate["diagnostic_linked_build"]["validation"]
        self.assertTrue(validation["linked_build_satisfied"])
        self.assertEqual(
            (validation["module_size"], validation["module_sha256"]),
            overlay.surface.DIAG_MODULE_IDENTITY,
        )

    def test_intent_value_is_json_round_trip_stable(self) -> None:
        value = overlay.create_intent_value(ROOT)
        self.assertEqual(value, json.loads(json.dumps(value)))

    def test_evidence_adapter_selects_exact_max77705_decoder(self) -> None:
        selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(selected, decoder)

    def test_candidate_static_size_exception_is_p316_scoped(self) -> None:
        oversized_for_default = {
            "path": "candidate-static.json",
            "size": evidence.DEFAULT_CONTRACT_ARTIFACT_MAX_BYTES + 1,
            "sha256": "0" * 64,
        }
        with self.assertRaises(evidence.EvidenceError):
            evidence._artifact(  # noqa: SLF001
                oversized_for_default, "ordinary contract artifact"
            )
        self.assertIs(
            evidence._artifact(  # noqa: SLF001
                oversized_for_default,
                "P3.16 candidate static",
                maximum=evidence.P316_CANDIDATE_STATIC_MAX_BYTES,
            ),
            oversized_for_default,
        )
        too_large = dict(
            oversized_for_default,
            size=evidence.P316_CANDIDATE_STATIC_MAX_BYTES + 1,
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence._artifact(  # noqa: SLF001
                too_large,
                "P3.16 candidate static",
                maximum=evidence.P316_CANDIDATE_STATIC_MAX_BYTES,
            )

    def test_process_v2_uses_exact_64_module_closure(self) -> None:
        self.assertIs(promotion.e2_closure_selector, stock_closure)
        self.assertEqual(stock_closure.EXPECTED_MODULE_COUNT, 64)
        self.assertIs(
            evidence._select_e2_closure(  # noqa: SLF001
                evidence.P310_SOURCE_CONTRACT_ID, overlay.CONTRACT_ID
            ),
            stock_closure,
        )
        sentinel = {"verified": True}
        self.assertIs(
            evidence._generic_rootfs_module_closure(  # noqa: SLF001
                evidence.P310_SOURCE_CONTRACT_ID,
                stock_closure,
                sentinel,
            ),
            sentinel,
        )
        static = promotion.static_checker
        self.assertTrue(callable(static.repo_root))
        self.assertTrue(callable(static.resolve))
        self.assertTrue(callable(static.stable_read))
        self.assertIs(static.ARTIFACT_LIMITS, static.base.ARTIFACT_LIMITS)

    def test_stock_closure_uses_frozen_p315_candidate_parent(self) -> None:
        parent, artifact = stock_closure._frozen_parent_closure(ROOT)  # noqa: SLF001
        self.assertEqual(parent["count"], 61)
        self.assertEqual(
            parent["closure_sha256"],
            "a27191b070bbd3c3fe65f51612218d87be03eab62ac470d2c0545140adc9ccf0",
        )
        self.assertEqual(
            artifact, stock_closure.EXPECTED_P315_PARENT_ARTIFACT_RESULT
        )

    def test_p316_absolute_path_delta_is_explicit(self) -> None:
        self.assertEqual(len(stock_closure.P316_RETIRED_REQUIRED_PATH_STRINGS), 2)
        self.assertEqual(
            stock_closure.P316_DYNAMIC_PATH_SUFFIX_STRINGS,
            frozenset({"/driver", "/driver_override", "/of_node/compatible"}),
        )
        self.assertFalse(
            stock_closure.P316_RETIRED_REQUIRED_PATH_STRINGS
            & stock_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        )
        self.assertTrue(
            stock_closure.P316_DYNAMIC_PATH_SUFFIX_STRINGS
            <= stock_closure.REQUIRED_ABSOLUTE_PATH_STRINGS
        )

    def test_candidate_builder_calls_prepackaging_gate_before_packaging(self) -> None:
        tree = ast.parse(
            (ROOT / overlay.SOURCE_PATHS["p316_candidate_builder"]).read_text(
                encoding="utf-8"
            )
        )
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "validate_prepackaging_artifact"
        ]
        parent_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "build_candidate"
        ]
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(parent_calls), 1)
        self.assertLess(calls[0].lineno, parent_calls[0].lineno)

    def test_candidate_safety_uses_explicit_frozen_base_callback(self) -> None:
        source = (ROOT / overlay.SOURCE_PATHS["p316_candidate_builder"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("p310_builder._BASE_ARTIFACT_SAFETY", source)
        self.assertNotIn("parent.parent.parent._BASE_ARTIFACT_SAFETY", source)

    def test_diagnostic_is_late_only_and_boot_staged_once(self) -> None:
        self.assertEqual(candidate_builder.DIAGNOSTIC_RAMDISK_PATH,
                         "lib/modules/s22plus_max77705_mux_diag.ko")
        self.assertEqual(stock_closure.ADDED_MODULES,
                         (("msm-geni-se.ko", "msm_geni_se"),
                          ("gpi.ko", "gpi"),
                          ("i2c-msm-geni.ko", "i2c_msm_geni")))
        source = (ROOT / overlay.SOURCE_PATHS["p316_candidate_builder"]).read_text(
            encoding="utf-8"
        )
        self.assertIn('"diagnostic_staged_exactly_once": True', source)

    def test_guard_lifetime_applies_to_p316(self) -> None:
        bundle = SimpleNamespace(
            manifest={
                "observation": {
                    "acceptance": {
                        "userspace_overlay_contract_id": overlay.CONTRACT_ID
                    }
                }
            }
        )
        self.assertTrue(live._p313_bundle(bundle))  # noqa: SLF001

    def test_ready_manifest_wrapper_is_exact(self) -> None:
        self.assertEqual(
            ready_manifest.USERSPACE_OVERLAY_CONTRACT_ID, overlay.CONTRACT_ID
        )
        self.assertEqual(
            ready_manifest.SOURCE_CONTRACT_ID, overlay.PARENT_SOURCE_CONTRACT_ID
        )
        self.assertEqual(ready_manifest.DEFAULT_TIMEOUT_SEC, 300)

    def test_execution_sources_replace_parent_decoder_with_overlay(self) -> None:
        self.assertEqual(
            process_v2._overridden_candidate_sources(overlay.CONTRACT_ID),  # noqa: SLF001
            frozenset({"p310_telemetry_decoder"}),
        )

    def test_static_checker_uses_p316_rootfs_authority(self) -> None:
        source = (ROOT / overlay.SOURCE_PATHS["p316_static_checker"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("closure.exact_init_authority", source)
        self.assertNotIn("p311_static.rootfs_entrypoint_context", source)

    def test_qualification_requires_distinct_prepackaging_validation(self) -> None:
        self.assertNotEqual(
            qualification.PREPACKAGING_SCHEMA, qualification.FINAL_SCHEMA
        )
        self.assertIn(
            "prepackaging", qualification.validate_prepackaging_artifact.__name__
        )
        source = (ROOT / overlay.SOURCE_PATHS["p316_static_checker"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("intent_path=intent_path", source)


if __name__ == "__main__":
    unittest.main()
