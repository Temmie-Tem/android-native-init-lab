#!/usr/bin/env python3
"""Machine-enforced design contract for the P3.15 snapshot repair."""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p314_design_contract as predecessor


SCHEMA = "s22plus_fyg8_p315_design_requirements_v3"
ARTIFACT_SCHEMA = "s22plus_fyg8_p315_prepackaging_closure_v3"
QUALIFICATION_SCHEMA = "s22plus_fyg8_p315_final_qualification_closure_v1"
STATUS = "registered-not-satisfied"
VERDICT = "PASS_P315_RESTART_COMPLETE_SNAPSHOT_PREPACKAGING_HOST_ONLY"
QUALIFICATION_VERDICT = (
    "PASS_P315_FINAL_QUALIFICATION_AND_READY_REHEARSAL_HOST_ONLY"
)

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

KERNEL_SOURCE_ROOT = Path(
    "workspace/private/work/p310-v6-dev/workspace/private/work/"
    "s22plus_fyg8_kernel_build_p290_2ec2bbae/kernel_platform"
)
PREDECESSOR_SOURCE_RECEIPTS = {
    "dwc3_msm_wrapper": {
        "path": (
            KERNEL_SOURCE_ROOT
            / "msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c"
        ).as_posix(),
        "size": 204659,
        "sha256": "1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021",
    },
    "dwc3_core": {
        "path": (
            KERNEL_SOURCE_ROOT / "msm-kernel/drivers/usb/dwc3/core.c"
        ).as_posix(),
        "size": 51625,
        "sha256": "77db45ab1091f37dd935fcd827309b898bb3866b4e09e3f9751cdfaa542dd4e3",
    },
    "hs_phy": {
        "path": (
            KERNEL_SOURCE_ROOT
            / "msm-kernel/drivers/usb/phy/phy-msm-snps-hs.c"
        ).as_posix(),
        "size": 50240,
        "sha256": "7823f9efd310b350169d84ba824e715b31ef3065e6a280ffc502dac6985124eb",
    },
    "p314_materialized_runtime": {
        "path": (
            "workspace/private/outputs/s22plus_fyg8_p314/intent/"
            "materialized-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
        ),
        "size": 234791,
        "sha256": "37db3603a32726f2dec1ce78e13591ffe25a479439faeaee9128bbdba738c2e6",
    },
    "p314_materialized_descriptor": {
        "path": (
            "workspace/private/outputs/s22plus_fyg8_p314/intent/"
            "materialized-sources/s22plus_fyg8_p286_trace_descriptor.h"
        ),
        "size": 27172,
        "sha256": "3e233e3eeee6ac8c522f2ae7352bce1ed736de35c85d6869b0f3e68573b6f735",
    },
}

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

# These are reviewed call chains in the exact source receipts above.  The
# successor audit must derive each count from those functions; copying this
# table into a fixture is not proof.
RESTART_PAIR_SOURCE_DERIVATION = {
    "start_off": {
        "expected": 1,
        "chain": [
            "mode:none->dwc3_msm_set_role",
            "dwc3_ext_event_notify->sm_work",
            "DRD_STATE_PERIPHERAL->dwc3_otg_start_peripheral(0)",
        ],
    },
    "start_on": {
        "expected": 1,
        "chain": [
            "mode:peripheral->dwc3_msm_set_role",
            "dwc3_ext_event_notify->sm_work",
            "DRD_STATE_IDLE+B_SESS_VLD->dwc3_otg_start_peripheral(1)",
        ],
    },
    "child_suspend": {
        "expected": 1,
        "chain": [
            "dwc3_otg_start_peripheral(0)->pm_runtime_put_sync(child)",
            "dwc3_runtime_suspend->dwc3_suspend_common",
        ],
    },
    "child_resume": {
        "expected": 1,
        "chain": [
            "dwc3_otg_start_peripheral(1)->pm_runtime_get_sync(child)",
            "dwc3_runtime_resume->dwc3_resume_common",
        ],
    },
    "phy_suspend_off": {
        "expected": 2,
        "chain": [
            "child:dwc3_core_exit->usb_phy_set_suspend(usb2_phy,1)",
            "parent:dwc3_msm_suspend->usb_phy_set_suspend(hs_phy,1)",
            "child-usb2_phy==parent-hs_phy",
        ],
    },
    "phy_suspend_on": {
        "expected": 2,
        "chain": [
            "parent:dwc3_msm_resume->usb_phy_set_suspend(hs_phy,0)",
            "child:dwc3_core_init->usb_phy_set_suspend(usb2_phy,0)",
            "child-usb2_phy==parent-hs_phy",
        ],
    },
    "power_off": {
        "expected": 1,
        "chain": [
            "first-msm_hsphy_set_suspend(1)->msm_hsphy_enable_power(false)",
            "second-msm_hsphy_set_suspend(1)->already-suspended-return",
        ],
    },
    "power_on": {
        "expected": 1,
        "chain": [
            "child:dwc3_core_init->usb_phy_init",
            "msm_hsphy_init->msm_hsphy_enable_power(true)",
        ],
    },
    "phy_init": {
        "expected": 1,
        "chain": [
            "child:dwc3_resume_common->dwc3_core_init_for_resume",
            "dwc3_core_init->usb_phy_init(usb2_phy)",
        ],
    },
    "notify_connect": {
        "expected": 1,
        "chain": [
            "dwc3_otg_start_peripheral(1)",
            "usb_phy_notify_connect(hs_phy,USB_SPEED_HIGH)",
        ],
    },
}

RESTART_AUXILIARY_GEOMETRY = {
    "outer_pairs": 4,
    "outer_pair_chain": [
        "none-state-transition-work",
        "none-state-stabilization-work",
        "peripheral-state-transition-work",
        "peripheral-state-stabilization-work",
    ],
    "pullup_pairs": 0,
    "run_pairs": 2,
    "gadget_start_pairs": 1,
    "qscratch_hits": 1,
    "state_hits": 1,
    "config_hits": 1,
    "functional_pair_records": 24,
    "outer_pair_records": 8,
    "run_pair_records": 4,
    "gadget_start_pair_records": 2,
    "singleton_records": 3,
    "total_records": 41,
}

SNAPSHOT_FAILURE_DETAIL = 0x6704
RECORD_FORMAT_CONTRADICTION_DETAIL = 0x6707
UNKNOWN_PHASE_DETAIL = RECORD_FORMAT_CONTRADICTION_DETAIL
PAIRING_CONTRADICTION_DETAIL = 0x6713
POSITIVE_RETURN_DETAIL = 0x6714
QSCRATCH_CONTRADICTION_DETAIL = 0x6715
SNAPSHOT_CONTRADICTION_DETAIL = 0x6716
STOP_CLEAN_RECORDS = 14
RESTART_CLEAN_RECORDS = 41
FINAL_CLEAN_RECORDS = 41
FINAL_DRIFT_RECORDS = 49
RECORD_CAPACITY = 64

RESTART_COMPLETION_HELPER = "p315_wait_restart_completion"
RESTART_COMPLETION_MAX_SNAPSHOTS = 301
RESTART_COMPLETION_TIMEOUT_DETAIL = 0x6718
RESTART_RESUME_PRECONDITION_DETAIL = 0x671D
PROFILE_ONLY_NESTED_HIT_DETAIL = 0x6721
GADGET_START_ZERO_WITHOUT_RUN_ON_DETAIL = 0x6722
RUN_ON_PROVENANCE_CONTRADICTION_DETAIL = 0x6723
POLL_INTERVAL_MSEC = 100
RESTART_DEADLINE_SECONDS = 30
TRACE_BUFFER_CAPACITY_BYTES = 65536
RESTART_READINESS_MAX_READ_EXTENT_BYTES = (
    RESTART_COMPLETION_MAX_SNAPSHOTS * TRACE_BUFFER_CAPACITY_BYTES
)
PROFILE_READ_COUNT = 2
PROFILE_BUFFER_CAPACITY_BYTES = 65536
PROFILE_MAX_READ_EXTENT_BYTES = PROFILE_READ_COUNT * PROFILE_BUFFER_CAPACITY_BYTES
TOTAL_MAX_ADDED_READ_EXTENT_BYTES = (
    RESTART_READINESS_MAX_READ_EXTENT_BYTES + PROFILE_MAX_READ_EXTENT_BYTES
)

RESTART_REQUIRED_NESTED_PAIRS = (
    "child_resume",
    "phy_init",
    "power_on",
    "gadget_start",
    "run_on",
)

RETAINED_RESTART_BRANCH_DETAILS = {
    "profile_only_nested_hit": PROFILE_ONLY_NESTED_HIT_DETAIL,
    "gadget_start_zero_without_run_on": (
        GADGET_START_ZERO_WITHOUT_RUN_ON_DETAIL
    ),
    "run_on_provenance_contradiction": (
        RUN_ON_PROVENANCE_CONTRADICTION_DETAIL
    ),
}

HOST_OBSERVER_CASES = (
    "clean-normal-adjacent-pair",
    "stop-0x6704-at-actual-generation",
    "restart-0x6704-at-actual-generation",
    "profile-deficit-0x6705",
    "unknown-phase-0x6707",
    "completed-outer-with-missing-resume-pair-0x671d",
    "profile-only-nested-hit-0x6721",
    "gadget-start-zero-without-run-on-0x6722",
    "run-on-provenance-contradiction-0x6723",
    "all-inherited-a-b-and-pair-mask-position-cells",
    "unknown-overlay-fail-closed",
)

HOST_OBSERVER_HAZARD_CLOSURE = {
    "runtime-authority-and-position-drift": {
        "historical_units": ["P3.01", "P3.04", "P3.08"],
        "proof": "restart_source_geometry",
    },
    "live-caller-input-validity": {
        "historical_units": ["P3.14"],
        "proof": "runtime_wrapper_fixture",
    },
    "profile-versus-record-semantics": {
        "historical_units": ["P3.11", "P3.14"],
        "proof": "runtime_wrapper_fixture",
    },
    "carrier-decoder-persistence-and-overlay-dispatch": {
        "historical_units": ["P3.10", "P3.13", "P3.14-ready"],
        "proof": "process_v2_adapter_fixture",
    },
    "prepackaging-declaration-versus-wiring": {
        "historical_units": ["P3.11", "P3.14"],
        "proof": "packaging_wiring_audit",
    },
}

PROOF_ARTIFACT_SPECS = {
    "restart_source_geometry": {
        "schema": "s22plus_fyg8_p315_restart_source_geometry_audit_v1",
        "verdict": "PASS_P315_RESTART_SOURCE_GEOMETRY_HOST_ONLY",
        "producer": "s22plus_fyg8_p315_restart_source_geometry_audit.py",
    },
    "runtime_wrapper_fixture": {
        "schema": "s22plus_fyg8_p315_runtime_wrapper_fixture_v1",
        "verdict": "PASS_P315_RUNTIME_WRAPPER_FIXTURE_HOST_ONLY",
        "producer": "s22plus_fyg8_p315_runtime_fixture.py",
    },
    "process_v2_adapter_fixture": {
        "schema": "s22plus_fyg8_p315_process_v2_adapter_fixture_v1",
        "verdict": "PASS_P315_PROCESS_V2_ADAPTER_PERSISTENCE_HOST_ONLY",
        "producer": "s22plus_fyg8_p315_process_v2_adapter_fixture.py",
    },
    "packaging_wiring_audit": {
        "schema": "s22plus_fyg8_p315_packaging_wiring_audit_v1",
        "verdict": "PASS_P315_PREPACKAGING_WIRING_HOST_ONLY",
        "producer": "s22plus_fyg8_p315_packaging_wiring_audit.py",
    },
}

FINAL_QUALIFICATION_ARTIFACT_SPECS = {
    "reproducible_package_and_ready_rehearsal": {
        "schema": "s22plus_fyg8_p315_final_qualification_closure_v1",
        "verdict": "PASS_P315_FINAL_QUALIFICATION_AND_READY_REHEARSAL_HOST_ONLY",
        "producer": "s22plus_fyg8_p315_qualification_closure.py",
    },
}

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
        "site": "restart-readiness",
        "caller": "p313_run/restart-completion",
        "profile_required": False,
        "disposition": "bounded-prefix-only-no-profile-relation",
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
    ("p282_trace_read_snapshot", "p315_wait_restart_completion"),
    ("p315_parse_restart_prefix", "p315_wait_restart_completion"),
    ("p315_wait_restart_completion", "p313_run/restart"),
    ("p315_parse_restart_snapshot", "p315_read_live_snapshot"),
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


def _require_sha256(value: Any, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise P315DesignError(f"{label} is not a sha256")


def _proof_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def artifact_receipt(value: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("ascii") + b"\n"
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def proof_receipt(
    root: Path, name: str, result: dict[str, Any]
) -> dict[str, Any]:
    specification = PROOF_ARTIFACT_SPECS.get(name)
    if specification is None:
        raise P315DesignError(f"unknown proof artifact: {name}")
    producer = root / "workspace/public/src/scripts/revalidation" / specification[
        "producer"
    ]
    payload = producer.read_bytes()
    return {
        "schema": specification["schema"],
        "verdict": specification["verdict"],
        "requirements_sha256": requirements_sha256(),
        "artifact_sha256": _proof_sha256(result),
        "producer": specification["producer"],
        "producer_sha256": hashlib.sha256(payload).hexdigest(),
        "verified": True,
    }


def _recompute_proof_artifacts(root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for name, specification in PROOF_ARTIFACT_SPECS.items():
        module_name = Path(specification["producer"]).stem
        module = importlib.import_module(module_name)
        result = module.audit(root)
        if not isinstance(result, dict):
            raise P315DesignError(f"{name} proof result differs")
        _require_equal(result.get("schema"), specification["schema"], f"{name} schema")
        _require_equal(
            result.get("verdict"), specification["verdict"], f"{name} verdict"
        )
        _require_equal(
            result.get("requirements_sha256"),
            requirements_sha256(),
            f"{name} requirements receipt",
        )
        _require_equal(result.get("verified"), True, f"{name} verified")
        rows[name] = proof_receipt(root, name, result)
    return rows


def verify_source_authority(root: Path) -> dict[str, Any]:
    receipts: dict[str, dict[str, Any]] = {}
    for name, expected in PREDECESSOR_SOURCE_RECEIPTS.items():
        path = root / expected["path"]
        payload = path.read_bytes()
        actual = {
            "path": expected["path"],
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        _require_equal(actual, expected, f"{name} source receipt")
        receipts[name] = actual
    return {"receipts": receipts, "verified": True}


def _validate_proof_receipts(value: Any) -> None:
    if not isinstance(value, dict):
        raise P315DesignError("proof artifact receipts missing")
    _require_exact_keys(value, set(PROOF_ARTIFACT_SPECS), "proof artifacts")
    for name, specification in PROOF_ARTIFACT_SPECS.items():
        proof = value.get(name)
        if not isinstance(proof, dict):
            raise P315DesignError(f"{name} proof receipt missing")
        _require_exact_keys(
            proof,
            {
                "schema",
                "verdict",
                "requirements_sha256",
                "artifact_sha256",
                "producer",
                "producer_sha256",
                "verified",
            },
            f"{name} proof receipt",
        )
        _require_equal(proof.get("schema"), specification["schema"], f"{name} schema")
        _require_equal(
            proof.get("verdict"), specification["verdict"], f"{name} verdict"
        )
        _require_equal(
            proof.get("requirements_sha256"),
            requirements_sha256(),
            f"{name} requirements receipt",
        )
        _require_equal(
            proof.get("producer"), specification["producer"], f"{name} producer"
        )
        _require_sha256(proof.get("artifact_sha256"), f"{name} artifact")
        _require_sha256(proof.get("producer_sha256"), f"{name} producer")
        _require_equal(proof.get("verified"), True, f"{name} verified")


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
            "predecessor_source_receipts": PREDECESSOR_SOURCE_RECEIPTS,
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
        "restart_source_geometry": {
            "pair_source_derivation": RESTART_PAIR_SOURCE_DERIVATION,
            "auxiliary_geometry": RESTART_AUXILIARY_GEOMETRY,
            "all_ten_pair_counts_derived_from_exact_source": True,
            "all_seventeen_auxiliary_records_derived_from_exact_source": True,
            "fixture_copy_is_not_source_proof": True,
            "source_audit_spec": PROOF_ARTIFACT_SPECS[
                "restart_source_geometry"
            ],
        },
        "restart_completion": {
            "asynchronous_chain": [
                "mode_store->dwc3_msm_set_role",
                "dwc3_ext_event_notify-flushes-old-work",
                "dwc3_ext_event_notify-queues-new-sm_work",
                "mode_store-returns-before-new-sm_work-completes",
            ],
            "pm_active_readbacks_are_not_completion_witness": True,
            "helper": RESTART_COMPLETION_HELPER,
            "prefix_parser": "p315_parse_restart_prefix",
            "readiness_is_control_flow_only": True,
            "readiness_requires_complete_start_on_pair": True,
            "readiness_requires_start_on_nested_in_outer_pair": True,
            "readiness_requires_quiescent_outer_pairs": 4,
            "readiness_forbidden_dependencies": [
                "child_resume",
                "phy_init",
                "power_on",
                "gadget_start",
                "run_on",
                "qscratch",
                "state",
                "config",
                "total_record_count",
            ],
            "four_outer_pairs_without_start_on_detail": UNKNOWN_PHASE_DETAIL,
            "inflight_outer_or_start_pair_is_not_yet_ready": True,
            "completed_malformed_prefix_fails_closed": True,
            "readiness_cannot_make_controller_or_cycle_claim": True,
            "authoritative_profile_snapshot_follows_readiness": True,
            "deadline_seconds": RESTART_DEADLINE_SECONDS,
            "poll_interval_msec": POLL_INTERVAL_MSEC,
            "maximum_snapshots": RESTART_COMPLETION_MAX_SNAPSHOTS,
            "timeout_or_attempt_exhaustion_detail": (
                RESTART_COMPLETION_TIMEOUT_DETAIL
            ),
            "outer_worker_or_start_on_never_completes_detail": (
                RESTART_COMPLETION_TIMEOUT_DETAIL
            ),
            "runtime_fixture_cases": [
                "outer-pair-inflight-not-ready",
                "start-on-pair-inflight-not-ready",
                "four-outer-pairs-without-start-on-0x6707",
                "outer-worker-never-completes-0x6718",
                "control-flow-ready-without-gadget-start-or-run-on",
            ],
            "trace_read_failure_detail": SNAPSHOT_FAILURE_DETAIL,
            "new_raw_errno_terminal_forbidden": True,
        },
        "restart_result_classification": {
            "parser": "p315_parse_restart_snapshot",
            "structural_parse_precedes_presence_classification": True,
            "profile_and_ring_integrity_precede_absence_claim": True,
            "required_nested_pairs_for_strict_geometry": list(
                RESTART_REQUIRED_NESTED_PAIRS
            ),
            "resume_precondition_absence_pairs": ["gadget_start", "run_on"],
            "resume_precondition_requires_both_pair_records_zero": True,
            "profile_counter_granularity": "trace-event-not-decoded-argument",
            "run_off_and_run_on_share_profile_indices": [19, 20],
            "gadget_start_profile_indices": [21, 22],
            "absence_requires_no_relevant_profile_excess": True,
            "gadget_start_absence_requires_profile_equals_record_equals_zero": (
                True
            ),
            "run_on_absence_requires_decoded_pair_records_zero": True,
            "run_on_absence_requires_profile_equals_total_run_event_records": (
                True
            ),
            "run_on_absolute_profile_zero_forbidden": True,
            "resume_precondition_detail": RESTART_RESUME_PRECONDITION_DETAIL,
            "retained_branch_details": RETAINED_RESTART_BRANCH_DETAILS,
            "retained_branch_details_are_pairwise_distinct": True,
            "retained_branch_details_use_inherited_reserved_slots": True,
            "gadget_start_or_run_on_incomplete_detail": (
                PAIRING_CONTRADICTION_DETAIL
            ),
            "profile_hit_without_record_detail": (
                PROFILE_ONLY_NESTED_HIT_DETAIL
            ),
            "profile_only_is_attribution_not_ring_loss": True,
            "incomplete_pair_detail": PAIRING_CONTRADICTION_DETAIL,
            "negative_return_uses_existing_controller_detail": True,
            "gadget_start_negative_without_run_on_uses_controller_detail": True,
            "gadget_start_positive_detail": POSITIVE_RETURN_DETAIL,
            "gadget_start_zero_branch_requires_rc_equal_zero": True,
            "gadget_start_nonnegative_fallthrough_forbidden": True,
            "gadget_start_zero_without_run_on_detail": (
                GADGET_START_ZERO_WITHOUT_RUN_ON_DETAIL
            ),
            "run_on_without_gadget_start_detail": (
                RUN_ON_PROVENANCE_CONTRADICTION_DETAIL
            ),
            "run_on_after_negative_gadget_start_detail": (
                RUN_ON_PROVENANCE_CONTRADICTION_DETAIL
            ),
            "run_on_negative_uses_existing_controller_detail": True,
            "run_on_negative_requires_valid_zero_gadget_start": True,
            "run_on_absent_after_gadget_start_is_not_resume_precondition": True,
            "precursor_absent_while_gate_pair_present_detail": (
                UNKNOWN_PHASE_DETAIL
            ),
            "run_on_without_qscratch_detail": QSCRATCH_CONTRADICTION_DETAIL,
            "run_on_without_state_or_config_detail": (
                SNAPSHOT_CONTRADICTION_DETAIL
            ),
            "strict_restart_geometry_only_after_required_pairs_present": True,
            "strict_restart_geometry_records": RESTART_CLEAN_RECORDS,
            "bounded_drift_records": FINAL_DRIFT_RECORDS,
            "resume_precondition_is_terminal_information_result": True,
            "resume_precondition_does_not_continue_to_final": True,
            "no_new_detail_family": True,
            "classification_precedence": [
                "profile-only-nested-hit-0x6721",
                "incomplete-entry-return-0x6713",
                "gadget-start-and-run-on-both-absent-0x671d",
                "run-on-provenance-contradiction-0x6723",
                "gadget-start-negative-run-on-absent-controller-detail",
                "gadget-start-positive-0x6714",
                "gadget-start-zero-run-on-absent-0x6722",
                "run-on-negative-controller-detail",
                "strict-restart-geometry",
            ],
            "runtime_fixture_cases": [
                "both-gadget-start-and-run-on-absent-with-run-off-profile-baseline-0x671d",
                "run-event-profile-excess-over-run-off-record-baseline-0x6721",
                "absolute-zero-run-profile-is-not-an-absence-contract",
                "incomplete-nested-pair-0x6713",
                "gadget-start-negative-run-on-absent-controller-detail",
                "gadget-start-zero-run-on-absent-0x6722",
                "gadget-start-positive-run-on-absent-0x6714",
                "gadget-start-positive-run-on-present-0x6714",
                "run-on-without-gadget-start-0x6723",
                "run-on-after-negative-gadget-start-0x6723",
                "run-on-negative-controller-detail",
                "full-clean-strict-restart-geometry",
            ],
        },
        "live_snapshot": {
            "helper": "p315_read_live_snapshot",
            "stop_and_restart_require_profile": True,
            "trace_or_profile_read_failure_detail": SNAPSHOT_FAILURE_DETAIL,
            "parse_only_after_successful_snapshot": True,
            "profile_relation_only_after_parse": True,
            "ring_stats_only_after_profile_relation": True,
            "profile_hits_relation": "profile_hits>=record_hits",
            "absence_claim_requires_no_relevant_profile_excess": True,
            "pair_specific_zero_uses_decoded_records_not_profile_counters": True,
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
            "new_wait_points": 1,
            "new_independent_wait_seconds": 0,
            "restart_completion_reuses_existing_deadline": True,
            "restart_completion_maximum_snapshots": (
                RESTART_COMPLETION_MAX_SNAPSHOTS
            ),
            "restart_readiness_maximum_read_extent_bytes": (
                RESTART_READINESS_MAX_READ_EXTENT_BYTES
            ),
            "added_profile_reads": PROFILE_READ_COUNT,
            "profile_buffer_capacity_bytes": PROFILE_BUFFER_CAPACITY_BYTES,
            "profile_maximum_added_read_extent_bytes": (
                PROFILE_MAX_READ_EXTENT_BYTES
            ),
            "maximum_added_read_extent_bytes": (
                TOTAL_MAX_ADDED_READ_EXTENT_BYTES
            ),
            "materialized_nonwait_overhead_must_be_recalculated": True,
            "subtraction_alone_is_not_proof": True,
            "guard_lifetime_unchanged": True,
        },
        "host_observer": {
            "required_cases": list(HOST_OBSERVER_CASES),
            "hazard_closure": HOST_OBSERVER_HAZARD_CLOSURE,
            "matrix_cells_minimum": 251450,
            "actual_runtime_emit_sites_define_acceptance": True,
            "actual_generation_positions_required": True,
            "p315_overlay_selected_by_real_process_v2": True,
            "carrier_v2_semantics_selected_before_decode": True,
            "json_persistence_round_trip_required": True,
            "foreign_count_must_equal": 0,
            "unknown_or_mixed_overlay_fails_closed": True,
            "p315_decoder_overrides_reserved_branch_names": True,
            "historical_decoder_meanings_unchanged": True,
            "retained_branch_details": RETAINED_RESTART_BRANCH_DETAILS,
            "inherited_b_output_count_unchanged": True,
            "ready_manifest_rehearsal_required": True,
            "reviewed_guard_seconds": 1200,
            "common_guard_lifecycle_regression_required": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "trace_descriptor_unchanged": True,
            "module_plan_unchanged": True,
            "checkpoint_positions_unchanged": True,
            "carrier_layout_unchanged": True,
            "new_details_within_inherited_terminal_gate": [
                0x6721,
                0x6722,
                0x6723,
            ],
            "rollback_unchanged": True,
            "full_lto_required": False,
            "userspace_rebuild_and_repackage_required": True,
            "changed_closure_independent_review_required": True,
        },
        "packaging": {
            "status": "required-not-satisfied",
            "prepackaging_proof_artifact_specs": PROOF_ARTIFACT_SPECS,
            "final_qualification_artifact_specs": (
                FINAL_QUALIFICATION_ARTIFACT_SPECS
            ),
            "two_phase_validation_required": True,
            "requirements_hash_in_source_closure": True,
            "prepackaging_validator_called_before_parent_packager": True,
            "validator_return_controls_package_creation": True,
            "missing_or_failed_artifact_blocks_packaging": True,
            "negative_fixture_parent_packager_calls": 0,
            "negative_fixture_package_outputs": 0,
            "validated_artifact_receipted_by_qualification": True,
            "ready_manifest_rehearsal_after_reproducible_packaging": True,
            "registration_shape_test_is_not_execution_proof": True,
            "actual_builder_call_graph_review_required": True,
        },
    }


def requirements_sha256() -> str:
    payload = json.dumps(
        requirements(), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def validate_successor_artifact(
    value: dict[str, Any], *, root: Path | None = None
) -> dict[str, Any]:
    """Validate shape, and when root-bound, execute every registered proof."""

    _require_exact_keys(
        value,
        {
            "schema",
            "verdict",
            "requirements_sha256",
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
            "proof_artifacts",
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
        "restart_source_geometry",
        "restart_completion",
        "restart_result_classification",
        "live_snapshot",
        "coverage",
        "time_budget",
        "host_observer",
        "artifacts",
        "packaging",
    ):
        proof = value.get(section)
        if not isinstance(proof, dict):
            raise P315DesignError(f"{section} proof missing")
        for key, required in expected[section].items():
            _require_equal(proof.get(key), required, f"{section} {key}")
        _require_equal(proof.get("verified"), True, f"{section} verified")
    _validate_proof_receipts(value.get("proof_artifacts"))
    if root is not None:
        root = root.resolve()
        verify_historical_authority(root)
        verify_source_authority(root)
        _require_equal(
            value.get("proof_artifacts"),
            _recompute_proof_artifacts(root),
            "executed proof artifact receipts",
        )
    _require_equal(value.get("verified"), True, "closure verified")
    return {
        "verdict": VERDICT,
        "requirements_sha256": requirements_sha256(),
        "restart_expected_counts": RESTART_EXPECTED_COUNTS,
        "restart_clean_records": RESTART_CLEAN_RECORDS,
        "restart_completion_max_snapshots": RESTART_COMPLETION_MAX_SNAPSHOTS,
        "restart_resume_precondition_detail": (
            RESTART_RESUME_PRECONDITION_DETAIL
        ),
        "snapshot_failure_detail": SNAPSHOT_FAILURE_DETAIL,
        "unknown_phase_detail": UNKNOWN_PHASE_DETAIL,
        "design_shape_valid": True,
        "execution_authority": root is not None,
        "verified": True,
    }


def validate_qualification_artifact(
    value: dict[str, Any], *, root: Path, candidate_tree: dict[str, Any]
) -> dict[str, Any]:
    """Bind the executed prepackaging proofs to reproducible package bytes."""

    _require_exact_keys(
        value,
        {
            "schema",
            "verdict",
            "requirements_sha256",
            "prepackaging_closure",
            "prepackaging_receipt",
            "packaging_wiring",
            "artifacts",
            "verified",
        },
        "P3.15 qualification closure",
    )
    _require_equal(value.get("schema"), QUALIFICATION_SCHEMA, "qualification schema")
    _require_equal(
        value.get("verdict"), QUALIFICATION_VERDICT, "qualification verdict"
    )
    _require_equal(
        value.get("requirements_sha256"),
        requirements_sha256(),
        "qualification requirements receipt",
    )
    closure = value.get("prepackaging_closure")
    if not isinstance(closure, dict):
        raise P315DesignError("qualification prepackaging closure missing")
    proof = validate_successor_artifact(closure, root=root)
    _require_equal(
        value.get("prepackaging_receipt"),
        artifact_receipt(closure),
        "qualification prepackaging receipt",
    )
    wiring = value.get("packaging_wiring")
    if not isinstance(wiring, dict):
        raise P315DesignError("qualification packaging wiring missing")
    _require_exact_keys(
        wiring,
        {
            "validated_artifact_receipted_by_qualification",
            "receipt_binds_requirements_and_artifact_sha256",
            "ready_manifest_rehearsal_after_reproducible_packaging",
            "ready_manifest_rehearsal",
            "verified",
        },
        "qualification packaging wiring",
    )
    for key in (
        "validated_artifact_receipted_by_qualification",
        "receipt_binds_requirements_and_artifact_sha256",
        "ready_manifest_rehearsal_after_reproducible_packaging",
        "verified",
    ):
        _require_equal(wiring.get(key), True, f"qualification wiring {key}")
    rehearsal = wiring.get("ready_manifest_rehearsal")
    if not isinstance(rehearsal, dict) or rehearsal.get("verified") is not True:
        raise P315DesignError("ready-manifest rehearsal proof missing")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict):
        raise P315DesignError("qualification artifact identity missing")
    _require_exact_keys(
        artifacts,
        {
            "fixed_image_unchanged",
            "kernel_hooks_unchanged",
            "trace_descriptor_unchanged",
            "module_plan_unchanged",
            "carrier_layout_unchanged",
            "rollback_unchanged",
            "full_lto_performed",
            "userspace_builds_reproducible",
            "packages_reproducible",
            "candidate_tree",
            "verified",
        },
        "qualification artifact identity",
    )
    for key, expected in (
        ("fixed_image_unchanged", True),
        ("kernel_hooks_unchanged", True),
        ("trace_descriptor_unchanged", True),
        ("module_plan_unchanged", True),
        ("carrier_layout_unchanged", True),
        ("rollback_unchanged", True),
        ("full_lto_performed", False),
        ("userspace_builds_reproducible", True),
        ("packages_reproducible", True),
        ("verified", True),
    ):
        _require_equal(artifacts.get(key), expected, f"qualification artifact {key}")
    _require_equal(
        artifacts.get("candidate_tree"), candidate_tree, "qualification tree receipt"
    )
    _require_equal(value.get("verified"), True, "qualification verified")
    return {
        "schema": QUALIFICATION_SCHEMA,
        "requirements_sha256": requirements_sha256(),
        "prepackaging_requirements_sha256": proof["requirements_sha256"],
        "prepackaging_execution_authority": proof["execution_authority"],
        "packages_reproducible": True,
        "ready_manifest_rehearsed": True,
        "verified": True,
    }
