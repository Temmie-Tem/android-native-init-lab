#!/usr/bin/env python3
"""Focused P3.15 runtime, proof-gate, and Process-v2 tests."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

import build_s22plus_fyg8_p315_candidate as candidate_builder
import device_action_f1_evidence_v2 as evidence
import device_action_f1_v2 as process_v2
import prepare_s22plus_fyg8_p315_process_v2 as promotion
import prepare_s22plus_fyg8_p315_ready_manifest as ready_manifest
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_e2_stock_closure as stock_closure
import s22plus_fyg8_p315_overlay_contract as overlay
import s22plus_fyg8_p315_packaging_wiring_audit as wiring
import s22plus_fyg8_p315_telemetry_decoder as decoder
import s22plus_fyg8_p315_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[1]


class P315ProcessV2Tests(unittest.TestCase):
    def test_complete_source_key_inventory_exists(self) -> None:
        missing = [
            key
            for key, relative in overlay.SOURCE_PATHS.items()
            if not (ROOT / relative).is_file()
        ]
        self.assertEqual(missing, [])

    def test_matrix_and_reserved_semantics_are_exact(self) -> None:
        self.assertEqual(spec.matrix_cell_count(), 251_450)
        self.assertEqual(len(spec.a_outputs()), 126)
        self.assertEqual(len(spec.b_outputs()), 2_222)
        self.assertEqual(len(spec.matrix_b_values()), 2_223)
        self.assertEqual(
            spec.P315_RESERVED_NAMES,
            {
                0x6721: "profile-only-nested-hit",
                0x6722: "gadget-start-zero-without-run-on",
                0x6723: "run-on-provenance-contradiction",
            },
        )

    def test_evidence_adapter_selects_exact_p315_decoder(self) -> None:
        selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(selected, decoder)

    def test_packaging_gate_executes_before_parent_packager(self) -> None:
        proof = wiring.audit(ROOT)
        self.assertTrue(proof["call_graph"]["validator_precedes_packager"])
        self.assertTrue(proof["call_graph"]["validator_return_is_bound"])
        self.assertEqual(proof["negative_fixture"]["parent_packager_call_count"], 0)
        self.assertEqual(proof["negative_fixture"]["package_output_count"], 0)

    def test_builder_calls_root_bound_validator_exactly_once(self) -> None:
        path = ROOT / overlay.SOURCE_PATHS["p315_candidate_builder"]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "validate_successor_artifact"
        ]
        self.assertEqual(len(calls), 1)
        keywords = {keyword.arg for keyword in calls[0].keywords}
        self.assertEqual(keywords, {"root"})

    def test_process_v2_uses_exact_p315_stock_closure(self) -> None:
        self.assertIs(promotion.e2_closure_selector, stock_closure)
        sentinel = {"verified": True}
        self.assertIs(
            evidence._generic_rootfs_module_closure(  # noqa: SLF001
                evidence.P310_SOURCE_CONTRACT_ID,
                stock_closure,
                sentinel,
            ),
            sentinel,
        )
        with self.assertRaisesRegex(
            evidence.EvidenceError, "P3.15 exact init authority is unavailable"
        ):
            evidence._p315_e2_authority_context(  # noqa: SLF001
                stock_closure, [], {}
            )

    def test_execution_source_override_includes_p315(self) -> None:
        self.assertEqual(
            process_v2._overridden_candidate_sources(overlay.CONTRACT_ID),  # noqa: SLF001
            frozenset({"p310_telemetry_decoder"}),
        )

    def test_ready_manifest_wrapper_is_exact(self) -> None:
        self.assertEqual(
            ready_manifest.USERSPACE_OVERLAY_CONTRACT_ID, overlay.CONTRACT_ID
        )
        self.assertEqual(
            ready_manifest.SOURCE_CONTRACT_ID, overlay.PARENT_SOURCE_CONTRACT_ID
        )
        self.assertEqual(ready_manifest.DEFAULT_TIMEOUT_SEC, 300)

    def test_final_qualification_spec_matches_design(self) -> None:
        specification = design.FINAL_QUALIFICATION_ARTIFACT_SPECS[
            "reproducible_package_and_ready_rehearsal"
        ]
        self.assertEqual(specification["schema"], design.QUALIFICATION_SCHEMA)
        self.assertEqual(specification["verdict"], design.QUALIFICATION_VERDICT)

    def test_candidate_builder_uses_fixed_image_without_full_lto(self) -> None:
        self.assertEqual(candidate_builder.DEFAULT_IMAGE, overlay.PARENT_IMAGE)
        self.assertFalse(design.requirements()["artifacts"]["full_lto_required"])

    def test_userspace_result_preserves_inherited_descriptor_identity(self) -> None:
        source = (
            ROOT / overlay.SOURCE_PATHS["p315_userspace_build"]
        ).read_text(encoding="utf-8")
        self.assertEqual(
            source.count('"callsite_descriptor_a_b_identical": True'), 1
        )


if __name__ == "__main__":
    unittest.main()
