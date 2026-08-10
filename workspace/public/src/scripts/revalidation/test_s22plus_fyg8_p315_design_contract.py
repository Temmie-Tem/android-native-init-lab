#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

import s22plus_fyg8_p315_design_contract as design


def compliant_fixture() -> dict[str, object]:
    requirements = design.requirements()
    value: dict[str, object] = {
        "schema": design.ARTIFACT_SCHEMA,
        "verdict": design.VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "verified": True,
    }
    for section in (
        "historical_authority",
        "phase_geometry",
        "live_snapshot",
        "coverage",
        "time_budget",
        "artifacts",
        "packaging",
    ):
        proof = deepcopy(requirements[section])
        proof["verified"] = True
        value[section] = proof
    return value


class P315DesignContractTests(unittest.TestCase):
    def test_historical_authority_is_exact_and_append_only(self) -> None:
        root = Path(__file__).resolve().parents[5]
        result = design.verify_historical_authority(root)
        self.assertTrue(result["verified"])
        self.assertEqual(
            result["predecessor_requirements_sha256"],
            design.PREDECESSOR_REQUIREMENTS_SHA256,
        )

    def test_phase_geometry_is_explicit_for_all_three_phases(self) -> None:
        geometry = design.requirements()["phase_geometry"]
        self.assertEqual(geometry["stop_expected_counts"], design.STOP_EXPECTED_COUNTS)
        self.assertEqual(
            geometry["restart_expected_counts"], design.RESTART_EXPECTED_COUNTS
        )
        self.assertEqual(
            geometry["final_expected_counts"], design.FINAL_EXPECTED_COUNTS
        )
        self.assertEqual(
            design.RESTART_EXPECTED_COUNTS, design.FINAL_EXPECTED_COUNTS
        )
        self.assertIsNot(
            design.RESTART_EXPECTED_COUNTS, design.FINAL_EXPECTED_COUNTS
        )
        self.assertEqual(geometry["restart_clean_records"], 41)
        self.assertEqual(geometry["unknown_phase_fail_closed_detail"], 0x6707)

    def test_snapshot_inventory_has_only_four_profile_false_sites(self) -> None:
        sites = design.requirements()["coverage"]["snapshot_sites"]
        false_sites = [row["site"] for row in sites if not row["profile_required"]]
        true_sites = [row["site"] for row in sites if row["profile_required"]]
        self.assertEqual(
            false_sites, ["role", "legacy-cycle-refresh", "bind", "direct"]
        )
        self.assertEqual(true_sites, ["stop", "restart"])
        self.assertEqual(
            [row["disposition"] for row in sites if row["site"] in true_sites],
            ["p315-live-snapshot-helper", "p315-live-snapshot-helper"],
        )

    def test_existing_profile_invariant_implementations_remain_visible(self) -> None:
        implementations = design.requirements()["coverage"][
            "profile_invariant_implementations"
        ]
        self.assertEqual(len(implementations), 3)
        self.assertIn("stop-and-restart-via-p315-helper", implementations)
        self.assertIn(
            "final-inline-disable-read-profile-parse-compare-ring",
            implementations,
        )
        self.assertIn(
            "partial-inline-disable-read-profile-parse-compare-ring",
            implementations,
        )

    def test_void_sweep_distinguishes_execution_from_compile_only(self) -> None:
        sweep = design.requirements()["coverage"]["void_function_sweep"]
        self.assertEqual(
            sweep["p314-runtime-fixture"]["must_execute"],
            ["p313_cycle_profile_relations", "profile_from_result"],
        )
        compile_only = sweep["p313-stop-multiplicity-audit"]["compile_only"]
        self.assertEqual(len(compile_only), 9)
        self.assertTrue(all(isinstance(reason, str) and reason for reason in compile_only.values()))

    def test_time_budget_accounts_for_two_bounded_profile_reads(self) -> None:
        budget = design.requirements()["time_budget"]
        self.assertEqual(budget["bounded_wait_seconds"], 160)
        self.assertEqual(budget["nominal_nonwait_remainder_seconds"], 140)
        self.assertEqual(budget["added_profile_reads"], 2)
        self.assertEqual(budget["maximum_added_read_extent_bytes"], 2 * 65536)
        self.assertTrue(budget["materialized_nonwait_overhead_must_be_recalculated"])
        self.assertTrue(budget["subtraction_alone_is_not_proof"])

    def test_future_compliant_closure_passes(self) -> None:
        result = design.validate_successor_artifact(compliant_fixture())
        self.assertTrue(result["verified"])
        self.assertEqual(result["snapshot_failure_detail"], 0x6704)
        self.assertEqual(result["unknown_phase_detail"], 0x6707)

    def test_missing_or_weakened_proof_fails_closed(self) -> None:
        mutations = (
            ("phase_geometry", "restart_expected_counts", design.STOP_EXPECTED_COUNTS),
            ("phase_geometry", "explicit_phase_switch_required", False),
            ("phase_geometry", "unknown_phase_fail_closed_detail", -1),
            ("live_snapshot", "stop_and_restart_require_profile", False),
            ("live_snapshot", "trace_or_profile_read_failure_detail", -5),
            ("live_snapshot", "raw_errno_terminal_forbidden", False),
            ("coverage", "changed_function_immediate_caller_unverified_difference", 1),
            ("time_budget", "added_profile_reads", 0),
            ("time_budget", "materialized_nonwait_overhead_must_be_recalculated", False),
            ("artifacts", "full_lto_required", True),
            ("packaging", "validator_called_before_packaging", False),
        )
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key):
                value = compliant_fixture()
                value[section][key] = replacement  # type: ignore[index]
                with self.assertRaises(design.P315DesignError):
                    design.validate_successor_artifact(value)

        value = compliant_fixture()
        del value["coverage"]["snapshot_sites"]  # type: ignore[index]
        with self.assertRaises(design.P315DesignError):
            design.validate_successor_artifact(value)

    def test_requirements_are_json_stable(self) -> None:
        payload = json.dumps(
            design.requirements(), sort_keys=True, separators=(",", ":")
        )
        self.assertEqual(len(design.requirements_sha256()), 64)
        self.assertIn(design.SCHEMA, payload)


if __name__ == "__main__":
    unittest.main()
