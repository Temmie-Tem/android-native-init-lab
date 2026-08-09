#!/usr/bin/env python3
"""Regression tests for P3.13 stop-side multiplicity localization."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import s22plus_fyg8_p313_stop_multiplicity_audit as audit


class P313StopMultiplicityAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = audit.audit(Path.cwd())

    def test_source_forces_two_stop_suspend_pairs_on_the_shared_phy(self) -> None:
        source = self.result["kernel_source_contract"]
        self.assertTrue(source["shared_hs_phy_from_child_usb_phy_phandle_zero"])
        self.assertEqual(
            source["stop_suspend_callers"],
            ["dwc3_core_exit", "dwc3_msm_suspend"],
        )
        self.assertEqual(source["source_forced_stop_pair"], "phy_suspend_off")
        self.assertEqual(source["source_forced_stop_pair_count"], 2)
        self.assertTrue(source["second_suspend_is_idempotent_early_return"])
        self.assertEqual(source["source_forced_restart_pair"], "phy_suspend_on")
        self.assertEqual(source["source_forced_restart_pair_count"], 2)

    def test_materialized_parser_reproduces_0x6712_from_that_pair(self) -> None:
        runtime = self.result["runtime_localization"]
        self.assertEqual(
            runtime["materialized_fixture"],
            "stop-detail=0x6712 records=14 phy-suspend-off-pairs=2",
        )
        self.assertTrue(runtime["source_forced_trigger_localized"])
        self.assertFalse(runtime["raw_pair_vector_recovered"])
        self.assertFalse(runtime["exclusive_pair_identity_proved"])
        self.assertEqual(runtime["source_derived_successor_clean_records"], 41)
        self.assertEqual(runtime["source_derived_successor_drift_records"], 49)
        self.assertEqual(runtime["successor_clean_headroom"], 23)
        self.assertEqual(runtime["successor_drift_headroom"], 15)

    def test_every_contradiction_detail_round_trips_at_every_generation(self) -> None:
        cross = self.result["carrier_value_generation_cross_product"]
        self.assertEqual(cross["generation_count"], 107)
        self.assertEqual(cross["contradiction_detail_count"], 63)
        self.assertEqual(cross["failure_round_trips"], 6_741)
        self.assertEqual(cross["progress_outcome_rejections"], 6_741)
        self.assertIn(
            "real Process-v2 adapter",
            self.result["carrier_cross_product_scope"],
        )
        json.dumps(self.result, sort_keys=True, allow_nan=False)

    def test_pair_specific_detail_costs_no_trace_records_and_fits_fixed_gates(
        self,
    ) -> None:
        detail = self.result["pair_specific_multiplicity_detail"]
        self.assertEqual(detail["output_count"], 1_023)
        self.assertEqual(detail["detail_min"], 0x6C01)
        self.assertEqual(detail["detail_max"], 0x6FFF)
        self.assertEqual(detail["trace_record_cost"], 0)
        self.assertTrue(detail["historical_p311_range_disjoint"])
        self.assertFalse(detail["current_runtime_guard_accepts"])
        self.assertTrue(detail["successor_runtime_guard_change_required"])
        self.assertEqual(
            detail["checkpoint_value_position_acceptances"], 109_461
        )
        self.assertEqual(
            detail["fixed_image_value_position_acceptances"], 109_461
        )
        self.assertFalse(detail["full_lto_required"])

    def test_successor_hazards_are_registered_but_not_claimed_complete(self) -> None:
        registration = self.result["successor_hazard_registration"]
        self.assertEqual(
            registration["qualification_status"], "registered-not-satisfied"
        )
        self.assertEqual(len(registration["requirements_sha256"]), 64)
        self.assertEqual(
            set(registration["requirements"]["hazards"]),
            {
                "source_derived_pair_geometry",
                "continuation_partition",
                "carrier_value_position_matrix",
                "pair_specific_multiplicity_detail",
                "qualification_wiring",
            },
        )


if __name__ == "__main__":
    unittest.main()
