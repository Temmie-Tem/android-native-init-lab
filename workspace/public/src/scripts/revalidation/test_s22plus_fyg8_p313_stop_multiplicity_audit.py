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


if __name__ == "__main__":
    unittest.main()
