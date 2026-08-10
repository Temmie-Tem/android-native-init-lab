#!/usr/bin/env python3
"""Machine-enforced design contract for the P3.15 snapshot repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p314_design_contract as predecessor


SCHEMA = "s22plus_fyg8_p315_design_requirements_v1"
ARTIFACT_SCHEMA = "s22plus_fyg8_p315_prepackaging_closure_v1"
STATUS = "registered-not-satisfied"
VERDICT = "PASS_P315_LIVE_SNAPSHOT_REPAIR_PREPACKAGING_HOST_ONLY"

INCIDENT_PATH = Path(
    "docs/reports/"
    "S22PLUS_FYG8_P314_LIVE_PROFILE_SNAPSHOT_INCIDENT_2026-08-10.md"
)
INCIDENT_RECEIPT = {
    "size": 4868,
    "sha256": "067febb9c20d20a3d86777d4c2ad628a841988a42e75c1c1490acd8f1a041101",
}
PREDECESSOR_REQUIREMENTS_SHA256 = (
    "b5d2b520c6866faf85e4c2b9d936f8cfefb8a4a6c0905af08e93acccb7077e3e"
)

PAIR_NAMES = (
    "start_off",
    "start_on",
    "child_suspend",
    "child_resume",
    "phy_suspend_off",
    "phy_suspend_on",
    "power_off",
    "power_on",
    "phy_init",
    "notify_connect",
)
STOP_EXPECTED_COUNTS = {
    "start_off": 1,
    "start_on": 0,
    "child_suspend": 1,
    "child_resume": 0,
    "phy_suspend_off": 2,
    "phy_suspend_on": 0,
    "power_off": 1,
    "power_on": 0,
    "phy_init": 0,
    "notify_connect": 0,
}
RESTART_EXPECTED_COUNTS = {
    "start_off": 1,
    "start_on": 1,
    "child_suspend": 1,
    "child_resume": 1,
    "phy_suspend_off": 2,
    "phy_suspend_on": 2,
    "power_off": 1,
    "power_on": 1,
    "phy_init": 1,
    "notify_connect": 1,
}
FINAL_EXPECTED_COUNTS = {
    "start_off": 1,
    "start_on": 1,
    "child_suspend": 1,
    "child_resume": 1,
    "phy_suspend_off": 2,
    "phy_suspend_on": 2,
    "power_off": 1,
    "power_on": 1,
    "phy_init": 1,
    "notify_connect": 1,
}

SNAPSHOT_FAILURE_DETAIL = 0x6704
UNKNOWN_PHASE_DETAIL = 0x6707
STOP_CLEAN_RECORDS = 14
RESTART_CLEAN_RECORDS = 41
FINAL_CLEAN_RECORDS = 41
FINAL_DRIFT_RECORDS = 49
RECORD_CAPACITY = 64

SNAPSHOT_SITES = (
    {
        "site": "role",
        "caller": "p282_phase_role",
        "profile_required": False,
        "disposition": "trace-read-error-normalized-to-role-source-contradiction",
    },
    {
        "site": "legacy-cycle-refresh",
        "caller": "p282_cycle_refresh",
        "profile_required": False,
        "disposition": "trace-read-error-normalized-to-trace-incomplete-warning",
    },
    {
        "site": "bind",
        "caller": "p282_phase_bind",
        "profile_required": False,
        "disposition": "bind-event-count-no-file-read",
    },
    {
        "site": "direct",
        "caller": "p313_run/direct-initial",
        "profile_required": False,
        "disposition": "bind-event-count-no-file-read",
    },
    {
        "site": "stop",
        "caller": "p313_run/stop",
        "profile_required": True,
        "disposition": "p315-live-snapshot-helper",
    },
    {
        "site": "restart",
        "caller": "p313_run/restart",
        "profile_required": True,
        "disposition": "p315-live-snapshot-helper",
    },
)

SEAM_CALLER_PAIRS = (
    ("p282_trace_read_snapshot", "p315_read_live_snapshot"),
    ("p314_parse_live_snapshot", "p315_read_live_snapshot"),
    ("p313_cycle_profile_relations", "p314_parse_live_snapshot"),
    ("p300_ring_stats_clean", "p314_parse_live_snapshot"),
    ("p315_read_live_snapshot", "p313_run/stop"),
    ("p315_read_live_snapshot", "p313_run/restart"),
    ("p313_cycle_profile_relations", "p313_cycle_finish"),
    ("p313_cycle_profile_relations", "p313_cycle_close_partial"),
)

PROFILE_INVARIANT_IMPLEMENTATIONS = (
    "stop-and-restart-via-p315-helper",
    "final-inline-disable-read-profile-parse-compare-ring",
    "partial-inline-disable-read-profile-parse-compare-ring",
)

VOID_FUNCTION_SWEEP = {
    "p314-runtime-fixture": {
        "must_execute": [
            "p313_cycle_profile_relations",
            "profile_from_result",
        ],
        "compile_only": {},
    },
    "p313-stop-multiplicity-audit": {
        "must_execute": [],
        "compile_only": {
            "p313_cycle_profile_relations": "pair-geometry-only-audit",
            "profile_from_result": "pair-geometry-only-audit",
            "fill_clean": "custom-stop-vector-replaces-inherited-clean-vector",
            "append_bounded_drift": "bounded-drift-outside-localization-scope",
            "check_a": "carrier-A-outside-localization-scope",
            "check_b": "carrier-B-outside-localization-scope",
            "check_values": "carrier-values-outside-localization-scope",
            "p313_a_outputs": "carrier-A-outside-localization-scope",
            "p313_b_outputs": "carrier-B-outside-localization-scope",
        },
    },
}


class P315DesignError(ValueError):
    pass


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise P315DesignError(f"{label} differs")


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise P315DesignError(f"{label} keys differ")


def verify_historical_authority(root: Path) -> dict[str, Any]:
    path = root / INCIDENT_PATH
    payload = path.read_bytes()
    receipt = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
    _require_equal(receipt, INCIDENT_RECEIPT, "P3.14 incident receipt")
    _require_equal(
        predecessor.requirements_sha256(),
        PREDECESSOR_REQUIREMENTS_SHA256,
        "P3.14 design requirements receipt",
    )
    return {
        "incident": {"path": INCIDENT_PATH.as_posix(), **receipt},
        "predecessor_requirements_sha256": PREDECESSOR_REQUIREMENTS_SHA256,
        "verified": True,
    }


def requirements() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "historical_authority": {
            "incident_path": INCIDENT_PATH.as_posix(),
            "incident_receipt": INCIDENT_RECEIPT,
            "predecessor_requirements_sha256": PREDECESSOR_REQUIREMENTS_SHA256,
            "historical_contracts_unchanged": True,
        },
        "phase_geometry": {
            "pair_names": list(PAIR_NAMES),
            "stop_expected_counts": STOP_EXPECTED_COUNTS,
            "restart_expected_counts": RESTART_EXPECTED_COUNTS,
            "final_expected_counts": FINAL_EXPECTED_COUNTS,
            "stop_clean_records": STOP_CLEAN_RECORDS,
            "restart_clean_records": RESTART_CLEAN_RECORDS,
            "final_clean_records": FINAL_CLEAN_RECORDS,
            "final_drift_records": FINAL_DRIFT_RECORDS,
            "record_capacity": RECORD_CAPACITY,
            "explicit_phase_switch_required": True,
            "unknown_phase_fail_closed_detail": UNKNOWN_PHASE_DETAIL,
            "missing_pair_rejected": True,
            "excess_pair_uses_existing_mask": True,
        },
        "live_snapshot": {
            "helper": "p315_read_live_snapshot",
            "stop_and_restart_require_profile": True,
            "trace_or_profile_read_failure_detail": SNAPSHOT_FAILURE_DETAIL,
            "parse_only_after_successful_snapshot": True,
            "profile_relation_only_after_parse": True,
            "ring_stats_only_after_profile_relation": True,
            "profile_hits_relation": "profile_hits>=record_hits",
            "raw_errno_terminal_forbidden": True,
            "final_partial_behavior_unchanged": True,
        },
        "coverage": {
            "snapshot_sites": list(SNAPSHOT_SITES),
            "seam_caller_pairs": [list(pair) for pair in SEAM_CALLER_PAIRS],
            "profile_invariant_implementations": list(
                PROFILE_INVARIANT_IMPLEMENTATIONS
            ),
            "void_function_sweep": VOID_FUNCTION_SWEEP,
            "changed_function_immediate_caller_unverified_difference": 0,
        },
        "time_budget": {
            "candidate_window_seconds": 300,
            "bounded_wait_seconds": 160,
            "nominal_nonwait_remainder_seconds": 140,
            "new_waits": 0,
            "added_profile_reads": 2,
            "profile_buffer_capacity_bytes": 65536,
            "maximum_added_read_extent_bytes": 131072,
            "materialized_nonwait_overhead_must_be_recalculated": True,
            "subtraction_alone_is_not_proof": True,
            "guard_lifetime_unchanged": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "trace_descriptor_unchanged": True,
            "module_plan_unchanged": True,
            "checkpoint_positions_unchanged": True,
            "carrier_layout_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_required": False,
            "userspace_rebuild_and_repackage_required": True,
            "changed_closure_independent_review_required": True,
        },
        "packaging": {
            "requirements_hash_in_source_closure": True,
            "validator_called_before_packaging": True,
            "missing_or_failed_artifact_blocks_packaging": True,
            "validated_artifact_receipted_by_qualification": True,
        },
    }


def requirements_sha256() -> str:
    payload = json.dumps(
        requirements(), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def validate_successor_artifact(value: dict[str, Any]) -> dict[str, Any]:
    """Reject a future P3.15 package closure missing a design obligation."""

    _require_exact_keys(
        value,
        {
            "schema",
            "verdict",
            "requirements_sha256",
            "historical_authority",
            "phase_geometry",
            "live_snapshot",
            "coverage",
            "time_budget",
            "artifacts",
            "packaging",
            "verified",
        },
        "P3.15 closure",
    )
    _require_equal(value.get("schema"), ARTIFACT_SCHEMA, "closure schema")
    _require_equal(value.get("verdict"), VERDICT, "closure verdict")
    _require_equal(
        value.get("requirements_sha256"), requirements_sha256(), "requirements receipt"
    )
    expected = requirements()
    for section in (
        "historical_authority",
        "phase_geometry",
        "live_snapshot",
        "coverage",
        "time_budget",
        "artifacts",
        "packaging",
    ):
        proof = value.get(section)
        if not isinstance(proof, dict):
            raise P315DesignError(f"{section} proof missing")
        for key, required in expected[section].items():
            _require_equal(proof.get(key), required, f"{section} {key}")
        _require_equal(proof.get("verified"), True, f"{section} verified")
    _require_equal(value.get("verified"), True, "closure verified")
    return {
        "verdict": VERDICT,
        "requirements_sha256": requirements_sha256(),
        "restart_expected_counts": RESTART_EXPECTED_COUNTS,
        "snapshot_failure_detail": SNAPSHOT_FAILURE_DETAIL,
        "unknown_phase_detail": UNKNOWN_PHASE_DETAIL,
        "verified": True,
    }
