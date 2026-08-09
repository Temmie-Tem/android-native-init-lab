#!/usr/bin/env python3
"""Focused P3.14 runtime, Carrier, packaging, and Process-v2 tests."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

import build_s22plus_fyg8_p314_candidate as candidate_builder
import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p314_carrier_model as model
import s22plus_fyg8_p314_design_contract as design
import s22plus_fyg8_p314_e2_stock_closure as stock_closure
import s22plus_fyg8_p314_matrix_fixture as matrix
import s22plus_fyg8_p314_overlay_contract as overlay
import s22plus_fyg8_p314_qualification_closure as qualification
import s22plus_fyg8_p314_telemetry_decoder as decoder
import s22plus_fyg8_p314_telemetry_spec as spec


ROOT = Path(__file__).resolve().parents[1]


class P314ProcessV2Tests(unittest.TestCase):
    def test_complete_source_key_inventory_exists(self) -> None:
        missing = [
            key for key, relative in overlay.SOURCE_PATHS.items()
            if not (ROOT / relative).is_file()
        ]
        self.assertEqual(missing, [])

    def test_matrix_arithmetic_and_position_authority(self) -> None:
        self.assertEqual(spec.matrix_cell_count(), 251_450)
        self.assertEqual(len(spec.a_outputs()), 126)
        self.assertEqual(len(spec.b_outputs()), 2_222)
        self.assertEqual(len(spec.matrix_b_values()), 2_223)
        self.assertEqual(
            sum(
                spec.matrix_expected_acceptance(family="a", generation=generation)
                for generation in range(1, 108)
            ),
            1,
        )
        self.assertTrue(
            all(
                spec.matrix_expected_acceptance(family="b", generation=generation)
                for generation in range(1, 108)
            )
        )

    def test_legacy_detail_is_decode_only(self) -> None:
        run_id = bytes.fromhex("31403140314031403140314031403140")
        initial = model.initialize_record(spec.PROFILE, run_id)
        position = spec.position_for_generation(1)
        request = model.encode_request(
            spec.PROFILE,
            position.stage,
            run_id=run_id,
            outcome=model.OUTCOME_FAILURE,
            item_index=position.item_index,
            detail=spec.LEGACY_GENERIC_MULTIPLICITY_DETAIL,
        )
        with self.assertRaises(model.DesignError):
            model.apply_request(initial, request)
        historical = matrix._force_apply(  # noqa: SLF001
            initial,
            run_id=run_id,
            generation=1,
            outcome=model.OUTCOME_FAILURE,
            detail=spec.LEGACY_GENERIC_MULTIPLICITY_DETAIL,
        )
        result = evidence.classify_e1_latest_stage(
            historical, matrix._acceptance(run_id)  # noqa: SLF001
        )
        persisted = json.loads(json.dumps(result, sort_keys=True, allow_nan=False))
        self.assertEqual(persisted["failure_count"], 1)
        self.assertEqual(
            persisted["records"][0]["active_semantics"]["detail_kind"],
            "p314-observer-contradiction",
        )

    def test_pair_mask_at_intermediate_generation_is_noncausal(self) -> None:
        run_id = bytes.fromhex("31403140314031403140314031403140")
        prefixes = matrix._prefixes(run_id)  # noqa: SLF001
        payload = matrix._force_apply(  # noqa: SLF001
            prefixes[96],
            run_id=run_id,
            generation=97,
            outcome=model.OUTCOME_FAILURE,
            detail=spec.encode_pair_mask(3),
        )
        result = decoder.decode_record(payload, expected_run_id=run_id)
        semantics = result["active_semantics"]["telemetry"]
        self.assertEqual(semantics["pairs"], ["start_off", "start_on"])
        self.assertFalse(semantics["cycle_causal_claim"])

    def test_packaging_gate_is_before_parent_packager(self) -> None:
        call_graph = qualification._builder_call_graph(ROOT)  # noqa: SLF001
        negative = qualification._negative_packaging_fixture(ROOT)  # noqa: SLF001
        self.assertTrue(call_graph["validator_precedes_package"])
        self.assertEqual(negative["parent_packager_call_count"], 0)
        self.assertEqual(negative["package_output_count"], 0)

    def test_two_phase_design_contract_is_not_circular(self) -> None:
        requirements = design.requirements()["packaging_wiring"]
        self.assertTrue(requirements["two_phase_validation_required"])
        self.assertIn(
            "validator_called_before_packaging",
            requirements["prepackaging_required_proofs"],
        )
        self.assertIn(
            "validated_artifact_receipted_by_qualification",
            requirements["final_required_proofs"],
        )

    def test_evidence_adapter_selects_exact_p314_decoder(self) -> None:
        selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(selected, decoder)

    def test_stock_closure_uses_p314_intent_authority(self) -> None:
        self.assertIs(stock_closure.overlay, overlay)
        self.assertIs(
            stock_closure.select(overlay.PARENT_SOURCE_CONTRACT_ID),
            stock_closure,
        )
        self.assertEqual(stock_closure.INCIDENTAL_PATH_OFFSET, 0x47E1)
        self.assertEqual(stock_closure.INCIDENTAL_INSTRUCTION_WINDOW_OFFSET, 0x47E0)

    def test_candidate_builder_exposes_inherited_packager_contract(self) -> None:
        self.assertEqual(
            candidate_builder.packager.SCHEMA,
            candidate_builder.parent.parent.base.packager.SCHEMA,
        )


if __name__ == "__main__":
    unittest.main()
