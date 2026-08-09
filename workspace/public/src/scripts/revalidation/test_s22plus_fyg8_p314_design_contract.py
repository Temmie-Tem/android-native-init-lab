#!/usr/bin/env python3
"""Regression tests for the P3.14 detailed design contract."""

from __future__ import annotations

from copy import deepcopy
import json
import unittest

import s22plus_fyg8_p313_successor_hazard_contract as predecessor
import s22plus_fyg8_p314_design_contract as design
import test_s22plus_fyg8_p313_successor_hazard_contract as predecessor_test


def compliant_prepackaging_fixture() -> dict[str, object]:
    return {
        "schema": design.PREPACKAGING_ARTIFACT_SCHEMA,
        "design_requirements_sha256": design.requirements_sha256(),
        "successor_hazard_closure": predecessor_test.compliant_fixture(),
        "runtime": {
            "stop_expected_counts": predecessor.STOP_EXPECTED_COUNTS,
            "final_expected_counts": predecessor.FINAL_EXPECTED_COUNTS,
            "stop_clean_records": 14,
            "final_clean_records": 41,
            "final_drift_records": 49,
            "record_capacity": 64,
            "overflow_fixture_records": 65,
            "generated_from_materialized_source": True,
            "all_complete_pair_returns_validated": True,
            "expected_counts_normalized_before_excess": True,
            "nonzero_excess_pair_mask_terminal": True,
            "legacy_0x6712_emit_sites_zero": True,
            "pair_mask_requires_integrity_clean_counts": True,
            "pair_mask_does_not_claim_exclusive_drift": True,
            "diagnostic_continue_enabled": False,
            "unclassified_contradiction_stops": True,
            "stop_drift_checked_before_restart": True,
            "trace_event_inventory_unchanged": True,
            "checkpoint_positions_unchanged": True,
            "verified": True,
        },
        "carrier": {
            "a_outputs": 126,
            "successor_b_outputs": 2_222,
            "matrix_b_values": 2_223,
            "progress_zero_outputs": 1,
            "positions": 107,
            "matrix_cells": 251_450,
            "pair_mask_detail_min": 0x6C01,
            "pair_mask_detail_max": 0x6FFF,
            "generated_from_actual_encoders": True,
            "accept_reject_from_runtime_emit_sites": True,
            "real_process_v2_adapter_round_trip": True,
            "persistence_round_trip": True,
            "legacy_0x6712_decode_only": True,
            "verified": True,
        },
        "packaging_wiring": {
            **{key: True for key in design.PREPACKAGING_WIRING_PROOFS},
            "verified": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "module_plan_unchanged": True,
            "carrier_size_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_performed": False,
            "verified": True,
        },
        "verified": True,
    }


def compliant_fixture() -> dict[str, object]:
    return {
        "schema": design.ARTIFACT_SCHEMA,
        "design_requirements_sha256": design.requirements_sha256(),
        "prepackaging_closure": compliant_prepackaging_fixture(),
        "packaging_wiring": {
            **{key: True for key in design.FINAL_QUALIFICATION_PROOFS},
            "verified": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "module_plan_unchanged": True,
            "carrier_size_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_performed": False,
            "userspace_builds_reproducible": True,
            "packages_reproducible": True,
            "verified": True,
        },
        "verified": True,
    }


class P314DesignContractTests(unittest.TestCase):
    def test_design_binds_registered_predecessor_requirements(self) -> None:
        value = design.requirements()
        self.assertEqual(value["status"], design.STATUS)
        self.assertEqual(
            value["predecessor_requirements_sha256"],
            predecessor.requirements_sha256(),
        )
        self.assertEqual(
            value["packaging_wiring"]["status"], "required-not-satisfied"
        )
        self.assertEqual(
            tuple(value["packaging_wiring"]["prepackaging_required_proofs"]),
            design.PREPACKAGING_WIRING_PROOFS,
        )
        self.assertEqual(
            tuple(value["packaging_wiring"]["final_required_proofs"]),
            design.FINAL_QUALIFICATION_PROOFS,
        )
        self.assertTrue(value["packaging_wiring"]["two_phase_validation_required"])
        self.assertEqual(len(design.requirements_sha256()), 64)
        json.dumps(value, sort_keys=True, allow_nan=False)

    def test_design_is_stricter_than_optional_diagnostic_continuation(self) -> None:
        runtime = design.requirements()["runtime"]
        self.assertFalse(runtime["diagnostic_continue_enabled"])
        self.assertTrue(runtime["all_genuine_contradictions_stop"])
        self.assertEqual(runtime["stop_clean_records"], 14)
        self.assertEqual(runtime["final_clean_records"], 41)
        self.assertEqual(runtime["final_drift_records"], 49)

    def test_carrier_matrix_and_pair_mask_arithmetic(self) -> None:
        carrier = design.requirements()["carrier"]
        self.assertEqual(carrier["successor_b_outputs"], 2_222)
        self.assertEqual(carrier["matrix_b_values"], 2_223)
        self.assertEqual(carrier["matrix_cells"], 251_450)
        self.assertEqual(carrier["pair_mask_detail_min"], 0x6C01)
        self.assertEqual(carrier["pair_mask_detail_max"], 0x6FFF)

    def test_compliant_future_qualification_passes_structural_gate(self) -> None:
        prepackaging = design.validate_prepackaging_artifact(
            compliant_prepackaging_fixture()
        )
        self.assertTrue(prepackaging["verified"])
        result = design.validate_qualification_artifact(compliant_fixture())
        self.assertTrue(result["verified"])
        self.assertFalse(result["diagnostic_continue_enabled"])
        self.assertEqual(result["matrix_cells"], 251_450)

    def test_future_packaging_wiring_is_not_self_attesting(self) -> None:
        for key in design.PREPACKAGING_WIRING_PROOFS:
            with self.subTest(key=key):
                value = deepcopy(compliant_prepackaging_fixture())
                value["packaging_wiring"][key] = False  # type: ignore[index]
                with self.assertRaises(design.P314DesignError):
                    design.validate_prepackaging_artifact(value)
        for key in design.FINAL_QUALIFICATION_PROOFS:
            with self.subTest(key=key):
                value = deepcopy(compliant_fixture())
                value["packaging_wiring"][key] = False  # type: ignore[index]
                with self.assertRaises(design.P314DesignError):
                    design.validate_qualification_artifact(value)

    def test_missing_or_mutated_load_bearing_proof_fails_closed(self) -> None:
        mutations = (
            ("runtime", "final_clean_records", 37),
            ("runtime", "legacy_0x6712_emit_sites_zero", False),
            ("runtime", "pair_mask_requires_integrity_clean_counts", False),
            ("runtime", "diagnostic_continue_enabled", True),
            ("runtime", "stop_drift_checked_before_restart", False),
            ("carrier", "matrix_cells", 109_461),
            ("carrier", "legacy_0x6712_decode_only", False),
            ("artifacts", "full_lto_performed", True),
        )
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key):
                value = deepcopy(compliant_prepackaging_fixture())
                value[section][key] = replacement  # type: ignore[index]
                with self.assertRaises(design.P314DesignError):
                    design.validate_prepackaging_artifact(value)

        value = deepcopy(compliant_prepackaging_fixture())
        del value["successor_hazard_closure"]["hazards"][  # type: ignore[index]
            "qualification_wiring"
        ]
        with self.assertRaises(design.P314DesignError):
            design.validate_prepackaging_artifact(value)

        value = deepcopy(compliant_fixture())
        value["artifacts"]["packages_reproducible"] = False  # type: ignore[index]
        with self.assertRaises(design.P314DesignError):
            design.validate_qualification_artifact(value)


if __name__ == "__main__":
    unittest.main()
