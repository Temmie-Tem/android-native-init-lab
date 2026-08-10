#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p314_telemetry_spec as inherited_telemetry


STATIC_SECTIONS = (
    "historical_authority",
    "phase_geometry",
    "restart_source_geometry",
    "restart_completion",
    "restart_result_classification",
    "live_snapshot",
    "coverage",
    "time_budget",
    "host_observer",
    "artifacts",
    "packaging",
)


def _sha256_fixture(index: int) -> str:
    return f"{index:064x}"


def compliant_fixture() -> dict[str, object]:
    """Build registration-shape data, not a qualification proof."""

    requirements = design.requirements()
    value: dict[str, object] = {
        "schema": design.ARTIFACT_SCHEMA,
        "verdict": design.VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "verified": True,
    }
    for section in STATIC_SECTIONS:
        proof = deepcopy(requirements[section])
        proof["verified"] = True
        value[section] = proof
    proof_artifacts: dict[str, object] = {}
    for index, (name, specification) in enumerate(
        design.PROOF_ARTIFACT_SPECS.items(), start=1
    ):
        proof_artifacts[name] = {
            "schema": specification["schema"],
            "verdict": specification["verdict"],
            "requirements_sha256": design.requirements_sha256(),
            "artifact_sha256": _sha256_fixture(index),
            "producer": specification["producer"],
            "producer_sha256": _sha256_fixture(index + 100),
            "verified": True,
        }
    value["proof_artifacts"] = proof_artifacts
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

    def test_exact_predecessor_sources_are_receipted(self) -> None:
        root = Path(__file__).resolve().parents[5]
        result = design.verify_source_authority(root)
        self.assertTrue(result["verified"])
        self.assertEqual(result["receipts"], design.PREDECESSOR_SOURCE_RECEIPTS)

    def test_restart_geometry_is_full_and_source_registered(self) -> None:
        requirements = design.requirements()
        geometry = requirements["phase_geometry"]
        source = requirements["restart_source_geometry"]
        self.assertEqual(geometry["stop_expected_counts"], design.STOP_EXPECTED_COUNTS)
        self.assertEqual(
            geometry["restart_expected_counts"], design.RESTART_EXPECTED_COUNTS
        )
        self.assertEqual(geometry["final_expected_counts"], design.FINAL_EXPECTED_COUNTS)
        self.assertEqual(design.RESTART_EXPECTED_COUNTS, design.FINAL_EXPECTED_COUNTS)
        self.assertIsNot(design.RESTART_EXPECTED_COUNTS, design.FINAL_EXPECTED_COUNTS)

        derivation = source["pair_source_derivation"]
        self.assertEqual(set(derivation), set(design.PAIR_NAMES))
        self.assertEqual(
            {name: row["expected"] for name, row in derivation.items()},
            design.RESTART_EXPECTED_COUNTS,
        )
        self.assertTrue(all(row["chain"] for row in derivation.values()))
        self.assertEqual(sum(design.RESTART_EXPECTED_COUNTS.values()) * 2, 24)

        auxiliary = source["auxiliary_geometry"]
        auxiliary_records = (
            auxiliary["outer_pair_records"]
            + auxiliary["run_pair_records"]
            + auxiliary["gadget_start_pair_records"]
            + auxiliary["singleton_records"]
        )
        self.assertEqual(auxiliary_records, 17)
        self.assertEqual(auxiliary["functional_pair_records"] + auxiliary_records, 41)
        self.assertEqual(auxiliary["total_records"], 41)
        self.assertTrue(source["fixture_copy_is_not_source_proof"])

    def test_restart_completion_closes_async_work_race(self) -> None:
        completion = design.requirements()["restart_completion"]
        self.assertIn(
            "mode_store-returns-before-new-sm_work-completes",
            completion["asynchronous_chain"],
        )
        self.assertTrue(completion["pm_active_readbacks_are_not_completion_witness"])
        self.assertTrue(completion["readiness_is_control_flow_only"])
        self.assertTrue(completion["readiness_requires_complete_start_on_pair"])
        self.assertTrue(completion["readiness_requires_start_on_nested_in_outer_pair"])
        self.assertEqual(completion["readiness_requires_quiescent_outer_pairs"], 4)
        self.assertEqual(completion["four_outer_pairs_without_start_on_detail"], 0x6707)
        forbidden = set(completion["readiness_forbidden_dependencies"])
        self.assertTrue(
            {
                "gadget_start",
                "run_on",
                "qscratch",
                "state",
                "config",
                "total_record_count",
            }.issubset(forbidden)
        )
        self.assertNotIn("readiness_requires_exact_source_minimums", completion)
        self.assertNotIn("readiness_accepts_bounded_record_range", completion)
        self.assertEqual(completion["timeout_or_attempt_exhaustion_detail"], 0x6718)
        self.assertEqual(
            completion["outer_worker_or_start_on_never_completes_detail"],
            0x6718,
        )
        self.assertIn(
            "outer-worker-never-completes-0x6718",
            completion["runtime_fixture_cases"],
        )
        self.assertEqual(completion["trace_read_failure_detail"], 0x6704)
        self.assertTrue(completion["authoritative_profile_snapshot_follows_readiness"])

    def test_missing_nested_run_stop_is_a_result_not_a_readiness_timeout(self) -> None:
        classification = design.requirements()["restart_result_classification"]
        self.assertEqual(
            classification["required_nested_pairs_for_strict_geometry"],
            list(design.RESTART_REQUIRED_NESTED_PAIRS),
        )
        self.assertEqual(
            classification["resume_precondition_absence_pairs"],
            ["gadget_start", "run_on"],
        )
        self.assertTrue(
            classification["resume_precondition_requires_both_pair_records_zero"]
        )
        self.assertNotIn(
            "resume_precondition_requires_both_pair_profile_hits_zero",
            classification,
        )
        self.assertEqual(
            classification["profile_counter_granularity"],
            "trace-event-not-decoded-argument",
        )
        self.assertEqual(
            classification["run_off_and_run_on_share_profile_indices"], [19, 20]
        )
        self.assertEqual(
            classification["gadget_start_profile_indices"], [21, 22]
        )
        self.assertTrue(
            classification["absence_requires_no_relevant_profile_excess"]
        )
        self.assertTrue(
            classification[
                "gadget_start_absence_requires_profile_equals_record_equals_zero"
            ]
        )
        self.assertTrue(
            classification[
                "run_on_absence_requires_profile_equals_total_run_event_records"
            ]
        )
        self.assertTrue(classification["run_on_absolute_profile_zero_forbidden"])
        self.assertEqual(classification["resume_precondition_detail"], 0x671D)
        retained = classification["retained_branch_details"]
        self.assertEqual(
            retained,
            {
                "profile_only_nested_hit": 0x6721,
                "gadget_start_zero_without_run_on": 0x6722,
                "run_on_provenance_contradiction": 0x6723,
            },
        )
        self.assertEqual(len(set(retained.values())), 3)
        self.assertTrue(all(0x6701 <= detail <= 0x673F for detail in retained.values()))
        self.assertEqual(classification["profile_hit_without_record_detail"], 0x6721)
        self.assertEqual(classification["incomplete_pair_detail"], 0x6713)
        self.assertTrue(
            classification[
                "gadget_start_negative_without_run_on_uses_controller_detail"
            ]
        )
        self.assertEqual(
            classification["gadget_start_positive_detail"], 0x6714
        )
        self.assertEqual(
            classification["gadget_start_zero_without_run_on_detail"], 0x6722
        )
        self.assertTrue(
            classification["gadget_start_zero_branch_requires_rc_equal_zero"]
        )
        self.assertTrue(
            classification["gadget_start_nonnegative_fallthrough_forbidden"]
        )
        self.assertEqual(
            classification["run_on_without_gadget_start_detail"], 0x6723
        )
        self.assertEqual(
            classification["run_on_after_negative_gadget_start_detail"], 0x6723
        )
        self.assertTrue(
            classification["run_on_negative_requires_valid_zero_gadget_start"]
        )
        self.assertTrue(
            classification[
                "run_on_absent_after_gadget_start_is_not_resume_precondition"
            ]
        )
        self.assertTrue(
            classification["strict_restart_geometry_only_after_required_pairs_present"]
        )
        self.assertTrue(
            classification["resume_precondition_is_terminal_information_result"]
        )
        self.assertTrue(
            classification["resume_precondition_does_not_continue_to_final"]
        )
        self.assertIn(
            "gadget-start-zero-run-on-absent-0x6722",
            classification["runtime_fixture_cases"],
        )
        self.assertIn(
            "gadget-start-negative-run-on-absent-controller-detail",
            classification["runtime_fixture_cases"],
        )
        self.assertIn(
            "run-on-negative-controller-detail",
            classification["runtime_fixture_cases"],
        )
        self.assertIn(
            "gadget-start-positive-run-on-present-0x6714",
            classification["runtime_fixture_cases"],
        )
        self.assertIn(
            "both-gadget-start-and-run-on-absent-with-run-off-profile-baseline-0x671d",
            classification["runtime_fixture_cases"],
        )
        self.assertIn(
            "run-event-profile-excess-over-run-off-record-baseline-0x6721",
            classification["runtime_fixture_cases"],
        )
        precedence = classification["classification_precedence"]
        self.assertLess(
            precedence.index("gadget-start-positive-0x6714"),
            precedence.index("gadget-start-zero-run-on-absent-0x6722"),
        )

    def test_new_branch_meanings_reuse_existing_reserved_b_outputs(self) -> None:
        inherited_outputs = set(inherited_telemetry.b_outputs())
        details = set(design.RETAINED_RESTART_BRANCH_DETAILS.values())
        self.assertTrue(details.issubset(inherited_outputs))
        self.assertEqual(len(inherited_outputs | details), len(inherited_outputs))
        for detail in sorted(details):
            decoded = inherited_telemetry.decode_b(detail)
            self.assertEqual(decoded["kind"], "observer-contradiction")
            self.assertTrue(decoded["name"].startswith("reserved-observer-"))
        self.assertEqual(
            design.requirements()["artifacts"][
                "new_details_within_inherited_terminal_gate"
            ],
            [0x6721, 0x6722, 0x6723],
        )

    def test_snapshot_inventory_names_readiness_as_profile_free(self) -> None:
        sites = design.requirements()["coverage"]["snapshot_sites"]
        false_sites = [row["site"] for row in sites if not row["profile_required"]]
        true_sites = [row["site"] for row in sites if row["profile_required"]]
        self.assertEqual(
            false_sites,
            ["role", "legacy-cycle-refresh", "bind", "direct", "restart-readiness"],
        )
        self.assertEqual(true_sites, ["stop", "restart"])
        readiness = next(row for row in sites if row["site"] == "restart-readiness")
        self.assertEqual(
            readiness["disposition"], "bounded-prefix-only-no-profile-relation"
        )

    def test_existing_profile_invariant_implementations_remain_visible(self) -> None:
        implementations = design.requirements()["coverage"][
            "profile_invariant_implementations"
        ]
        self.assertEqual(len(implementations), 3)
        self.assertIn("stop-and-restart-via-p315-helper", implementations)
        self.assertIn(
            "final-inline-disable-read-profile-parse-compare-ring", implementations
        )
        self.assertIn(
            "partial-inline-disable-read-profile-parse-compare-ring", implementations
        )

    def test_void_sweep_distinguishes_execution_from_compile_only(self) -> None:
        sweep = design.requirements()["coverage"]["void_function_sweep"]
        self.assertEqual(
            sweep["p314-runtime-fixture"]["must_execute"],
            ["p313_cycle_profile_relations", "profile_from_result"],
        )
        compile_only = sweep["p313-stop-multiplicity-audit"]["compile_only"]
        self.assertEqual(len(compile_only), 9)
        self.assertTrue(
            all(isinstance(reason, str) and reason for reason in compile_only.values())
        )

    def test_time_budget_bounds_polling_and_profile_reads(self) -> None:
        budget = design.requirements()["time_budget"]
        expected_snapshots = (
            design.RESTART_DEADLINE_SECONDS * 1000 // design.POLL_INTERVAL_MSEC + 1
        )
        self.assertEqual(expected_snapshots, 301)
        self.assertEqual(budget["restart_completion_maximum_snapshots"], 301)
        self.assertEqual(budget["new_wait_points"], 1)
        self.assertEqual(budget["new_independent_wait_seconds"], 0)
        self.assertTrue(budget["restart_completion_reuses_existing_deadline"])
        self.assertEqual(
            budget["restart_readiness_maximum_read_extent_bytes"], 301 * 65536
        )
        self.assertEqual(budget["added_profile_reads"], 2)
        self.assertEqual(budget["profile_maximum_added_read_extent_bytes"], 2 * 65536)
        self.assertEqual(
            budget["maximum_added_read_extent_bytes"],
            301 * 65536 + 2 * 65536,
        )
        self.assertTrue(budget["materialized_nonwait_overhead_must_be_recalculated"])
        self.assertTrue(budget["subtraction_alone_is_not_proof"])

    def test_host_observer_contract_covers_real_dispatch_and_persistence(self) -> None:
        observer = design.requirements()["host_observer"]
        self.assertEqual(observer["required_cases"], list(design.HOST_OBSERVER_CASES))
        self.assertEqual(observer["matrix_cells_minimum"], 251450)
        self.assertTrue(observer["p315_overlay_selected_by_real_process_v2"])
        self.assertTrue(observer["carrier_v2_semantics_selected_before_decode"])
        self.assertTrue(observer["json_persistence_round_trip_required"])
        self.assertEqual(observer["foreign_count_must_equal"], 0)
        self.assertEqual(observer["reviewed_guard_seconds"], 1200)
        self.assertEqual(
            observer["retained_branch_details"],
            design.RETAINED_RESTART_BRANCH_DETAILS,
        )
        self.assertTrue(observer["p315_decoder_overrides_reserved_branch_names"])
        self.assertTrue(observer["inherited_b_output_count_unchanged"])
        hazards = observer["hazard_closure"]
        self.assertEqual(hazards, design.HOST_OBSERVER_HAZARD_CLOSURE)
        self.assertTrue(
            all(
                row["proof"] in design.PROOF_ARTIFACT_SPECS
                for row in hazards.values()
            )
        )

    def test_registration_shape_is_explicitly_not_execution_authority(self) -> None:
        result = design.validate_successor_artifact(compliant_fixture())
        self.assertTrue(result["design_shape_valid"])
        self.assertFalse(result["execution_authority"])
        self.assertEqual(result["snapshot_failure_detail"], 0x6704)
        self.assertEqual(result["unknown_phase_detail"], 0x6707)
        self.assertTrue(
            design.requirements()["packaging"][
                "registration_shape_test_is_not_execution_proof"
            ]
        )
        packaging = design.requirements()["packaging"]
        self.assertEqual(
            set(packaging["prepackaging_proof_artifact_specs"]),
            set(design.PROOF_ARTIFACT_SPECS),
        )
        self.assertEqual(
            set(packaging["final_qualification_artifact_specs"]),
            set(design.FINAL_QUALIFICATION_ARTIFACT_SPECS),
        )
        self.assertTrue(packaging["two_phase_validation_required"])

    def test_missing_or_weakened_obligation_fails_closed(self) -> None:
        mutations = (
            ("phase_geometry", "restart_expected_counts", design.STOP_EXPECTED_COUNTS),
            ("phase_geometry", "explicit_phase_switch_required", False),
            ("restart_source_geometry", "fixture_copy_is_not_source_proof", False),
            ("restart_completion", "pm_active_readbacks_are_not_completion_witness", False),
            ("restart_completion", "readiness_is_control_flow_only", False),
            ("restart_completion", "maximum_snapshots", 0),
            ("restart_result_classification", "resume_precondition_detail", -1),
            (
                "restart_result_classification",
                "run_on_absent_after_gadget_start_is_not_resume_precondition",
                False,
            ),
            (
                "restart_result_classification",
                "gadget_start_zero_branch_requires_rc_equal_zero",
                False,
            ),
            (
                "restart_result_classification",
                "run_on_absolute_profile_zero_forbidden",
                False,
            ),
            (
                "restart_result_classification",
                "resume_precondition_does_not_continue_to_final",
                False,
            ),
            ("live_snapshot", "stop_and_restart_require_profile", False),
            ("live_snapshot", "trace_or_profile_read_failure_detail", -5),
            ("coverage", "changed_function_immediate_caller_unverified_difference", 1),
            ("time_budget", "restart_completion_maximum_snapshots", 0),
            ("time_budget", "materialized_nonwait_overhead_must_be_recalculated", False),
            ("host_observer", "json_persistence_round_trip_required", False),
            ("artifacts", "full_lto_required", True),
            ("packaging", "prepackaging_validator_called_before_parent_packager", False),
        )
        for section, key, replacement in mutations:
            with self.subTest(section=section, key=key):
                value = compliant_fixture()
                value[section][key] = replacement  # type: ignore[index]
                with self.assertRaises(design.P315DesignError):
                    design.validate_successor_artifact(value)

        value = compliant_fixture()
        del value["proof_artifacts"]["runtime_wrapper_fixture"]  # type: ignore[index]
        with self.assertRaises(design.P315DesignError):
            design.validate_successor_artifact(value)

        value = compliant_fixture()
        value["proof_artifacts"]["process_v2_adapter_fixture"][  # type: ignore[index]
            "artifact_sha256"
        ] = "not-a-sha256"
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
