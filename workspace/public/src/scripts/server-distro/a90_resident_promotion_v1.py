#!/usr/bin/env python3
"""A90-only resident install/promotion tail over the reviewed F1 orchestrator.

The base orchestrator remains the sole owner of staging, candidate transfer,
journal publication, and rollback recovery.  This module validates the extra
promotion evidence and supplies either the legacy second-boot health tail or
the resident-install terminal after first candidate health.  Inspection is the
default; live modes still require a final manifest and fresh exact approval.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_v3403_absent_only_staging as staging  # noqa: E402
import a90_v3403_f1_orchestrator as base  # noqa: E402


MODE = "a90-resident-promotion-v1"
RESULT_SCHEMA = "a90_resident_boot_promotion_v1_result"
INSTALL_MODE = "a90-resident-install-v2"
INSTALL_RESULT_SCHEMA = "a90_resident_install_v2_result"
INSTALL_STATUS = "PASS_A90_RESIDENT_INSTALLED"
INSTALL_TERMINAL_STATE = "RESIDENT_INSTALLED_CLOSED"
INSTALL_EVENTS = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "live_session_end",
)
INSTALL_SUCCESS_ACTIONS = (
    "preflight",
    "approved",
    "staging-started",
    "rootfs-staged",
    "rootfs-candidate-preflight",
    "resident-promotion-guard-armed",
    "candidate-transfer-started",
    "candidate-flashed",
    "candidate-boot-ready",
    "candidate-health-verified",
    "closed",
)
INSTALL_SUCCESS_STATES = (
    "PREFLIGHT",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "APPROVED",
    "CANDIDATE_FLASHED",
    "CANDIDATE_FLASHED",
    "CANDIDATE_HEALTH_VERIFIED",
    INSTALL_TERMINAL_STATE,
)
REBOOT_COMMAND = ("reboot",)
MAX_PRIOR_JOURNAL_RECORDS = 64
GUARD_CRASH_CLEANUP_WAIT_SEC = 5.0
GUARD_CRASH_CLEANUP_POLL_SEC = 0.1
QUALIFICATION_HELPER_PATH = SCRIPT_DIR / "a90_resident_fast_handoff_v1.py"
PROMOTED_RESULT_KEYS = {
    "schema",
    "run_id",
    "status",
    "manifest_sha256",
    "candidate_sha256",
    "candidate_transfer_count",
    "candidate_replay",
    "resident_reboot_count",
    "candidate_health_check_count",
    "rollback_transfer_count",
    "rollback_required",
    "first_health",
    "second_health",
    "timeline_events",
}
INSTALLED_RESULT_KEYS = {
    "schema",
    "run_id",
    "status",
    "manifest_sha256",
    "candidate_sha256",
    "candidate_transfer_count",
    "candidate_replay",
    "resident_reboot_count",
    "candidate_health_check_count",
    "rollback_transfer_count",
    "rollback_required",
    "device_safety_state",
    "first_health",
    "timeline_events",
}


class ContractError(base.ContractError):
    """Raised when the resident-promotion extension is not exact."""


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _load_bound_json(value: Any, label: str) -> tuple[staging.BoundFile, dict[str, Any]]:
    try:
        bound = base.private_bound_file(value, label)
    except (base.ContractError, OSError) as exc:
        raise ContractError(f"{label} binding is unavailable") from exc
    staging.require_regular_file(
        bound.path,
        expected_size=bound.size,
        expected_sha256=bound.sha256,
    )
    try:
        parsed = json.loads(bound.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not valid JSON") from exc
    return bound, _dict(parsed, label)


def _validate_runner_binding(value: Any) -> dict[str, Any]:
    item = _dict(value, "resident_promotion.runner")
    if set(item) != {"path", "size", "sha256"}:
        raise ContractError("resident promotion runner binding keys are not exact")
    path_value = item.get("path")
    size_value = item.get("size")
    sha_value = item.get("sha256")
    if not isinstance(path_value, str) or type(size_value) is not int:
        raise ContractError("resident promotion runner binding is incomplete")
    try:
        selected = Path(path_value).resolve(strict=True)
    except FileNotFoundError as exc:
        raise ContractError("resident promotion runner is absent") from exc
    expected = Path(__file__).resolve()
    info = selected.lstat()
    if (
        not Path(path_value).is_absolute()
        or selected != expected
        or not stat.S_ISREG(info.st_mode)
        or selected.is_symlink()
        or size_value != info.st_size
        or sha_value != base.sha256_file(selected)
    ):
        raise ContractError("resident promotion runner binding changed")
    return {"path": str(selected), "size": size_value, "sha256": sha_value}


def _validate_qualification_binding(value: Any) -> dict[str, Any]:
    item = _dict(value, "resident_promotion.qualification_helper")
    if set(item) != {"path", "size", "sha256"}:
        raise ContractError("qualification helper binding keys are not exact")
    path_value = item.get("path")
    size_value = item.get("size")
    sha_value = item.get("sha256")
    if not isinstance(path_value, str) or type(size_value) is not int:
        raise ContractError("qualification helper binding is incomplete")
    try:
        selected = Path(path_value).resolve(strict=True)
        expected = QUALIFICATION_HELPER_PATH.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ContractError("qualification helper is absent") from exc
    info = selected.lstat()
    if (
        not Path(path_value).is_absolute()
        or selected != expected
        or not stat.S_ISREG(info.st_mode)
        or selected.is_symlink()
        or size_value != info.st_size
        or sha_value != base.sha256_file(selected)
    ):
        raise ContractError("qualification helper binding changed")
    return {"path": str(selected), "size": size_value, "sha256": sha_value}


def _validate_prior_run(
    spec: base.F1Spec,
    value: Any,
) -> dict[str, Any]:
    item = _dict(value, "resident_promotion.prior_closed_run")
    if set(item) != {
        "run_id",
        "manifest",
        "approval_prepared",
        "result",
        "timeline",
        "journal",
    }:
        raise ContractError("prior closed-run binding keys are not exact")
    prior_run_id = item.get("run_id")
    if not isinstance(prior_run_id, str) or not prior_run_id:
        raise ContractError("prior closed-run id is missing")
    manifest_bound, prior_manifest = _load_bound_json(
        item.get("manifest"),
        "resident_promotion.prior_closed_run.manifest",
    )
    approval_bound, approval = _load_bound_json(
        item.get("approval_prepared"),
        "resident_promotion.prior_closed_run.approval_prepared",
    )
    result_bound, result = _load_bound_json(
        item.get("result"),
        "resident_promotion.prior_closed_run.result",
    )
    timeline_bound, timeline = _load_bound_json(
        item.get("timeline"),
        "resident_promotion.prior_closed_run.timeline",
    )
    journal_value = item.get("journal")
    if (
        not isinstance(journal_value, list)
        or not journal_value
        or len(journal_value) > MAX_PRIOR_JOURNAL_RECORDS
    ):
        raise ContractError("prior journal record count is not bounded")

    records: list[dict[str, Any]] = []
    journal_sha256: list[str] = []
    state_by_action = {
        "preflight": "PREFLIGHT",
        "approved": "APPROVED",
        "staging-started": "APPROVED",
        "rootfs-staged": "APPROVED",
        "rootfs-candidate-preflight": "APPROVED",
        "candidate-transfer-started": "APPROVED",
        "candidate-flashed": "CANDIDATE_FLASHED",
        "attended-window-open": "CANDIDATE_FLASHED",
        "attended-pre-handoff-attempt": "CANDIDATE_FLASHED",
        "attended-pre-handoff-failed": "CANDIDATE_FLASHED",
        "candidate-boot-ready": "CANDIDATE_FLASHED",
        "attended-pre-handoff-ready": "CANDIDATE_FLASHED",
        "attended-handoff-started": "CANDIDATE_FLASHED",
        "observation-proven": "OBSERVED",
        "observation-no-proof": "OBSERVED",
        "rollback-transfer-started": "RECOVERY_ROLLBACK",
        "rollback-flashed": "ROLLBACK_FLASHED",
        "rollback-boot-ready": "ROLLBACK_FLASHED",
        "health-verified": "HEALTH_VERIFIED",
        "closed": "CLOSED",
    }
    for sequence, entry in enumerate(journal_value):
        bound, record = _load_bound_json(
            entry,
            f"resident_promotion.prior_closed_run.journal[{sequence}]",
        )
        action = record.get("action")
        if (
            record.get("schema") != base.JOURNAL_SCHEMA
            or record.get("sequence") != sequence
            or record.get("run_id") != prior_run_id
            or record.get("manifest_sha256") != manifest_bound.sha256
            or record.get("state") != state_by_action.get(action)
            or not base.is_canonical_utc_timestamp(record.get("timestamp_utc"))
            or bound.path.name
            != f"{sequence:04d}-{action}.json"
        ):
            raise ContractError("prior journal is not contiguous and exact")
        records.append(record)
        journal_sha256.append(bound.sha256)

    actions = [record.get("action") for record in records]
    if actions[:7] != [
        "preflight",
        "approved",
        "staging-started",
        "rootfs-staged",
        "rootfs-candidate-preflight",
        "candidate-transfer-started",
        "candidate-flashed",
    ] or actions[-5:] != [
        "rollback-transfer-started",
        "rollback-flashed",
        "rollback-boot-ready",
        "health-verified",
        "closed",
    ]:
        raise ContractError("prior journal state order is not exact")
    exact_counts = {
        "candidate-transfer-started": 1,
        "candidate-flashed": 1,
        "candidate-boot-ready": 1,
        "rollback-transfer-started": 1,
        "rollback-flashed": 1,
        "rollback-boot-ready": 1,
        "health-verified": 1,
        "closed": 1,
    }
    if any(actions.count(action) != count for action, count in exact_counts.items()):
        raise ContractError("prior run lacks one candidate and one rollback closure")
    if any(
        action in actions
        for action in ("candidate-host-rejected", "aborted-before-candidate")
    ):
        raise ContractError("prior run did not execute the exact candidate")

    candidate_start = records[actions.index("candidate-transfer-started")]
    candidate_flash = records[actions.index("candidate-flashed")]
    candidate_health = records[actions.index("candidate-boot-ready")]
    rollback_start = records[actions.index("rollback-transfer-started")]
    rollback_flash = records[actions.index("rollback-flashed")]
    rollback_health = records[actions.index("rollback-boot-ready")]
    final_health = records[actions.index("health-verified")]
    approved = records[actions.index("approved")]
    closed = records[actions.index("closed")]
    prior_native_exact = _require_exact_native_health(
        spec,
        _dict(candidate_health.get("health"), "prior candidate native health"),
    )
    prior_rollback_native_exact = _require_exact_native_health(
        SimpleNamespace(
            candidate_version=spec.rollback_version,
            candidate_build=spec.rollback_build,
            stage=spec.stage,
        ),
        {
            "exact_bridge": final_health.get("exact_bridge"),
            "selected_realpath": final_health.get("selected_realpath"),
            "version": _dict(
                final_health.get("baseline"),
                "prior final baseline",
            ).get("version"),
            "selftest": _dict(
                final_health.get("baseline"),
                "prior final baseline",
            ).get("selftest"),
        },
    )
    approval_binding = _dict(
        approval.get("approval_binding"),
        "prior approval binding",
    )
    target = _dict(prior_manifest.get("target"), "prior target")
    connected_d0 = _dict(
        target.get("connected_d0_result"),
        "prior connected D0",
    )
    connected_paths = _dict(
        target.get("connected_path_preflight"),
        "prior connected path preflight",
    )
    orchestrator = _dict(
        prior_manifest.get("f1_orchestrator"),
        "prior F1 orchestrator",
    )
    rootfs_staging = _dict(
        prior_manifest.get("rootfs_staging"),
        "prior rootfs staging",
    )
    staging_adapter = _dict(
        rootfs_staging.get("adapter"),
        "prior staging adapter",
    )
    transport = _dict(prior_manifest.get("transport"), "prior transport")
    debian_rootfs = _dict(
        prior_manifest.get("debian_rootfs"),
        "prior Debian rootfs",
    )
    keyed_source = _dict(
        debian_rootfs.get("keyed_source"),
        "prior keyed source",
    )
    observation = _dict(
        prior_manifest.get("observation"),
        "prior observation",
    )
    expected_approval_binding = staging.canonical_f1_approval_binding(
        run_id=prior_run_id,
        manifest_sha256=manifest_bound.sha256,
        orchestrator_sha256=orchestrator.get("sha256"),
        staging_adapter_sha256=staging_adapter.get("sha256"),
        flash_runner_sha256=transport.get("runner_sha256"),
        candidate_boot_sha256=spec.candidate.sha256,
        rollback_boot_sha256=spec.rollback.sha256,
        rootfs_sha256=keyed_source.get("sha256"),
        connected_d0_sha256=connected_d0.get("sha256"),
        connected_path_preflight_sha256=connected_paths.get("sha256"),
        recovery_adb_serial_sha256=target.get("recovery_adb_serial_sha256"),
        observation_mode=observation.get("mode"),
        attended_window_sec=observation.get("attended_window_sec"),
        pre_handoff_attempt_limit=observation.get("pre_handoff_attempt_limit"),
        handoff_attempt_limit=observation.get("handoff_attempt_limit"),
    )
    approval_binding_sha = base.json_sha256(approval_binding)
    approval_token = base.APPROVAL_PREFIX + approval_binding_sha
    approval_token_sha = hashlib.sha256(approval_token.encode("utf-8")).hexdigest()
    if (
        candidate_start.get("candidate_sha256") != spec.candidate.sha256
        or candidate_flash.get("candidate_sha256") != spec.candidate.sha256
        or candidate_flash.get("candidate_transfer_count") != 1
        or candidate_flash.get("candidate_replay") is not False
        or candidate_health.get("candidate_version") != spec.candidate_version
        or candidate_health.get("candidate_build") != spec.candidate_build
        or candidate_health.get("selftest_fail_zero") is not True
        or rollback_start.get("rollback_sha256") != spec.rollback.sha256
        or rollback_flash.get("rollback_sha256") != spec.rollback.sha256
        or rollback_flash.get("rollback_transfer_count") != 1
        or rollback_flash.get("candidate_replay") is not False
        or rollback_health.get("rollback_version") != spec.rollback_version
        or rollback_health.get("rollback_build") != spec.rollback_build
        or rollback_health.get("selftest_fail_zero") is not True
        or final_health.get("version") != spec.rollback_version
        or final_health.get("build") != spec.rollback_build
        or final_health.get("selftest_fail_zero") is not True
        or final_health.get("pstore_entries_zero") is not True
        or final_health.get("exact_bridge") is not True
        or not isinstance(final_health.get("baseline"), dict)
    ):
        raise ContractError("prior run artifact identity or health is not exact")

    candidate_manifest = _dict(prior_manifest.get("candidate_boot"), "prior candidate_boot")
    rollback_manifest = _dict(prior_manifest.get("rollback_boot"), "prior rollback_boot")
    allowed_status = {
        "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
        "PASS_F1_V2_DEBIAN_PID1_PROVEN_AND_ROLLED_BACK",
        "PASS_F1_V2_DISPLAY_ACQUISITION_PROVEN_AND_ROLLED_BACK",
    }
    result_keys = {
        "schema",
        "run_id",
        "status",
        "manifest_sha256",
        "candidate_transfer_count",
        "candidate_transfer_uncertain",
        "candidate_replay",
        "debian_pid1_proven",
        "display_acquisition_proven",
        "rollback_transfer_count",
        "final_health_restored",
        "timeline_events",
    }
    closed_payload = {
        key: closed.get(key)
        for key in result_keys
    }
    closed_payload["schema"] = base.ORCHESTRATOR_SCHEMA
    events = timeline.get("events")
    timeline_names = (
        [event.get("name") for event in events]
        if isinstance(events, list)
        and all(
            isinstance(event, dict)
            and set(event) == {"name", "timestamp_utc"}
            and base.is_canonical_utc_timestamp(event.get("timestamp_utc"))
            for event in events
        )
        else None
    )
    timeline_timestamps = (
        [event["timestamp_utc"] for event in events]
        if isinstance(events, list)
        else None
    )
    status_facts = {
        "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK": (False, False),
        "PASS_F1_V2_DEBIAN_PID1_PROVEN_AND_ROLLED_BACK": (True, False),
        "PASS_F1_V2_DISPLAY_ACQUISITION_PROVEN_AND_ROLLED_BACK": (True, True),
    }
    approval_keys = {
        "schema",
        "created_utc",
        "run_id",
        "manifest_sha256",
        "approval_binding",
        "approval_binding_sha256",
        "approval_token",
        "device_contact",
        "device_write",
        "f1_authorized",
        "live_authorized",
    }
    if (
        prior_manifest.get("schema")
        not in {
            staging.FINAL_MANIFEST_SCHEMA,
            staging.PHASE2_DISPLAY_MANIFEST_SCHEMA,
        }
        or prior_manifest.get("status") != staging.FINAL_MANIFEST_STATUS
        or prior_manifest.get("run_id") != prior_run_id
        or target.get("profile") != staging.TARGET_PROFILE
        or target.get("bridge_selected_exact") is not True
        or target.get("bridge_device") != spec.stage.bridge_device
        or target.get("bridge_selected_realpath") != spec.stage.bridge_realpath
        or target.get("recovery_adb_serial_sha256")
        != spec.recovery_serial_sha256
        or set(connected_d0) != {"outcome", "path", "size", "sha256"}
        or set(connected_paths)
        != {
            "handoff_work_path_absent",
            "keyed_source_path_absent",
            "path",
            "run_stage_path_absent",
            "sha256",
            "size",
        }
        or any(
            connected_paths.get(name) is not True
            for name in (
                "handoff_work_path_absent",
                "keyed_source_path_absent",
                "run_stage_path_absent",
            )
        )
        or orchestrator.get("candidate_attempt_limit") != 1
        or orchestrator.get("rollback_attempt_limit") != 1
        or orchestrator.get("candidate_route_in_recovery") is not False
        or transport.get("only_partition_payload") != "boot"
        or transport.get("forbidden_partition_writes") is not True
        or approval_binding != expected_approval_binding
        or candidate_manifest.get("sha256") != spec.candidate.sha256
        or rollback_manifest.get("sha256") != spec.rollback.sha256
        or approval.get("schema") != base.APPROVAL_PREPARED_SCHEMA
        or set(approval) != approval_keys
        or not base.is_canonical_utc_timestamp(approval.get("created_utc"))
        or approval.get("run_id") != prior_run_id
        or approval.get("manifest_sha256") != manifest_bound.sha256
        or approval.get("approval_binding_sha256") != approval_binding_sha
        or approval.get("approval_token") != approval_token
        or any(
            approval.get(name) is not False
            for name in ("device_contact", "device_write", "f1_authorized", "live_authorized")
        )
        or approval_binding.get("manifest_sha256") != manifest_bound.sha256
        or approval_binding.get("candidate_boot_sha256") != spec.candidate.sha256
        or approval_binding.get("rollback_boot_sha256") != spec.rollback.sha256
        or approved.get("approval_consumed") is not True
        or approved.get("rollback_pre_authorized") is not True
        or approved.get("approval_binding_sha256") != approval_binding_sha
        or approved.get("approval_token_sha256") != approval_token_sha
        or result.get("run_id") != prior_run_id
        or set(result) != result_keys
        or result.get("schema") != base.ORCHESTRATOR_SCHEMA
        or result.get("status") not in allowed_status
        or result.get("manifest_sha256") != manifest_bound.sha256
        or result.get("candidate_transfer_count") != 1
        or result.get("candidate_transfer_uncertain") is not False
        or result.get("candidate_replay") is not False
        or result.get("rollback_transfer_count") != 1
        or result.get("final_health_restored") is not True
        or (
            result.get("debian_pid1_proven"),
            result.get("display_acquisition_proven"),
        )
        != status_facts.get(result.get("status"))
        or closed_payload != result
        or timeline_names != list(base.CANONICAL_EVENTS)
        or timeline_timestamps != sorted(timeline_timestamps or [])
        or result.get("timeline_events") != timeline_names
    ):
        raise ContractError("prior closed result does not prove exact rollback health")
    return {
        "run_id": prior_run_id,
        "manifest_sha256": manifest_bound.sha256,
        "approval_prepared_sha256": approval_bound.sha256,
        "result_sha256": result_bound.sha256,
        "timeline_sha256": timeline_bound.sha256,
        "journal_sha256": journal_sha256,
        "candidate_transfer_count": 1,
        "rollback_transfer_count": 1,
        "candidate_health_verified": True,
        "candidate_native_exact": prior_native_exact,
        "final_v2321_health_verified": True,
        "rollback_native_exact": prior_rollback_native_exact,
    }


def _validate_debian_receipt(
    spec: base.F1Spec,
    value: Any,
    qualification_helper: dict[str, Any],
) -> dict[str, Any]:
    bound = base.private_bound_file(
        value,
        "resident_promotion.debian_ab_receipt",
    )
    staging.require_regular_file(
        bound.path,
        expected_size=bound.size,
        expected_sha256=bound.sha256,
    )
    try:
        fast = importlib.import_module("a90_resident_fast_handoff_v1")
        module_path = Path(str(fast.__file__)).resolve(strict=True)
        if module_path != Path(qualification_helper["path"]):
            raise ContractError("qualification helper module identity changed")
        debian_ab = fast.validate_ab_receipt(bound.path)
    except (ContractError, ImportError, OSError, RuntimeError) as exc:
        raise ContractError("Debian A/B receipt is not exact") from exc
    rootfs = _dict(spec.manifest.get("debian_rootfs"), "debian_rootfs")
    keyed_source = _dict(
        rootfs.get("keyed_source"),
        "debian_rootfs.keyed_source",
    )
    materialization_label = "debian_rootfs.keyed_source.materialization"
    manifest_materialization = base.private_bound_file(
        keyed_source.get("materialization"),
        materialization_label,
    )
    closure_materialization = base.bound_by_label(
        spec.stage,
        materialization_label,
    )
    if manifest_materialization != closure_materialization:
        raise ContractError("keyed rootfs materialization left the bound closure")
    if (
        keyed_source.get("size") != spec.stage.local_size
        or keyed_source.get("sha256") != spec.stage.local_sha256
        or spec.stage.local_size != fast.EXPECTED_IMAGE_BYTES
        or spec.stage.local_sha256 == fast.EXPECTED_IMAGE_SHA256
    ):
        raise ContractError("resident promotion requires a fresh keyed rootfs")
    slots = _dict(debian_ab.get("slots"), "debian_ab_receipt.slots")
    for slot_name in ("A", "B"):
        slot = _dict(slots.get(slot_name), f"debian_ab_receipt slot {slot_name}")
        image = _dict(slot.get("image"), f"debian_ab_receipt slot {slot_name} image")
        if (
            image.get("bytes") != fast.EXPECTED_IMAGE_BYTES
            or image.get("sha256") != fast.EXPECTED_IMAGE_SHA256
        ):
            raise ContractError("Debian A/B receipt rootfs identity changed")
    if (
        debian_ab.get("image_byte_identical") is not True
        or debian_ab.get("presenter_byte_identical") is not True
        or debian_ab.get("source_unchanged") is not True
        or debian_ab.get("base_unchanged") is not True
    ):
        raise ContractError("Debian A/B receipt lacks deterministic closure")
    if base.sha256_file(module_path) != qualification_helper["sha256"]:
        raise ContractError("qualification helper changed during validation")
    return {
        "path": str(bound.path),
        "sha256": bound.sha256,
        "clean_rootfs_sha256": fast.EXPECTED_IMAGE_SHA256,
        "rootfs_sha256": spec.stage.local_sha256,
        "keyed_materialization_sha256": closure_materialization.sha256,
        "deterministic_ab": True,
    }


def validate_promotion_manifest(
    spec: base.F1Spec,
    *,
    recovery: bool = False,
) -> dict[str, Any]:
    value = _dict(spec.manifest.get("resident_promotion"), "resident_promotion")
    common_keys = {
        "mode",
        "runner",
        "qualification_helper",
        "rootfs_preflight_disposition",
        "candidate_health_checks",
        "rollback_on_post_attempt_failure",
        "prior_closed_run",
        "debian_ab_receipt",
    }
    mode = value.get("mode")
    if mode == MODE:
        expected_keys = common_keys | {
            "resident_reboot_command",
            "resident_reboot_timeout_sec",
        }
        expected_schema = staging.RESIDENT_PROMOTION_MANIFEST_SCHEMA
        expected_health_checks = 2
    elif mode == INSTALL_MODE:
        expected_keys = common_keys | {"success_terminal"}
        expected_schema = staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        expected_health_checks = 1
    else:
        raise ContractError("resident promotion mode is not supported")
    if set(value) != expected_keys:
        raise ContractError("resident promotion manifest key set is not exact")
    if (
        spec.manifest.get("schema") != expected_schema
        or value.get("rootfs_preflight_disposition") != "absent"
        or value.get("candidate_health_checks") != expected_health_checks
        or value.get("rollback_on_post_attempt_failure") is not True
        or spec.observation_mode != base.UNATTENDED_OBSERVATION_MODE
        or spec.display_required
    ):
        raise ContractError("resident promotion execution contract is not exact")
    if mode == MODE:
        reboot_command = value.get("resident_reboot_command")
        reboot_timeout = value.get("resident_reboot_timeout_sec")
        if (
            not isinstance(reboot_command, list)
            or tuple(reboot_command) != REBOOT_COMMAND
            or type(reboot_timeout) is not int
            or reboot_timeout != spec.candidate_return_timeout
            or not 30 <= reboot_timeout <= 600
        ):
            raise ContractError("resident promotion reboot contract is not exact")
    elif value.get("success_terminal") != INSTALL_STATUS:
        raise ContractError("resident install terminal is not exact")
    result = {
        "mode": mode,
        "runner": _validate_runner_binding(value.get("runner")),
        "rootfs_preflight_disposition": "absent",
        "candidate_health_checks": expected_health_checks,
        "rollback_on_post_attempt_failure": True,
    }
    if mode == MODE:
        result.update(
            resident_reboot_command=list(REBOOT_COMMAND),
            resident_reboot_timeout_sec=reboot_timeout,
        )
    else:
        result["success_terminal"] = INSTALL_STATUS
    if recovery:
        _dict(
            value.get("qualification_helper"),
            "resident_promotion.qualification_helper",
        )
        _dict(value.get("prior_closed_run"), "resident_promotion.prior_closed_run")
        _dict(value.get("debian_ab_receipt"), "resident_promotion.debian_ab_receipt")
        result["auxiliary_evidence_reopened"] = False
    else:
        qualification_helper = _validate_qualification_binding(
            value.get("qualification_helper")
        )
        result["qualification_helper"] = qualification_helper
        result["prior_closed_run"] = _validate_prior_run(
            spec,
            value.get("prior_closed_run"),
        )
        result["debian_ab_receipt"] = _validate_debian_receipt(
            spec,
            value.get("debian_ab_receipt"),
            qualification_helper,
        )
    return result


def load_spec(
    manifest_path: Path,
    expected_manifest_sha256: str,
    *,
    allow_draft: bool,
    recovery: bool = False,
) -> tuple[base.F1Spec, dict[str, Any], list[str]]:
    spec, issues = base.load_spec(
        manifest_path,
        expected_manifest_sha256,
        allow_draft=allow_draft,
    )
    try:
        promotion = validate_promotion_manifest(spec, recovery=recovery)
    except (ContractError, base.ContractError, staging.ContractError, OSError) as exc:
        if not allow_draft:
            raise ContractError(str(exc)) from exc
        promotion = {}
        issues.append(f"resident promotion is not final: {exc}")
    return spec, promotion, issues


def _promotion_health(
    spec: base.F1Spec,
    args: argparse.Namespace,
    native_health: dict[str, Any],
) -> dict[str, Any]:
    return {
        "native": native_health,
        "pstore": base.require_clean_pstore_before_handoff(args),
        "rootfs": base.remote_source_preflight(spec, args),
        "ncm": base.rebind_host_ncm_after_reenumeration(spec, args),
    }


def _require_exact_native_health(
    spec: base.F1Spec,
    native_health: dict[str, Any],
) -> dict[str, str]:
    health = _dict(native_health, "candidate native health")
    version = _dict(health.get("version"), "candidate version response")
    selftest = _dict(health.get("selftest"), "candidate selftest response")
    version_lines = str(version.get("text") or "").splitlines()
    selftest_lines = str(selftest.get("text") or "").splitlines()
    expected_version = (
        f"version: {spec.candidate_version} build={spec.candidate_build}"
    )
    version_facts = [
        line for line in version_lines if line.startswith("version: ")
    ]
    selftest_facts = [
        line for line in selftest_lines if line.startswith("selftest: ")
    ]
    if (
        health.get("exact_bridge") is not True
        or health.get("selected_realpath") != spec.stage.bridge_realpath
        or type(version.get("rc")) is not int
        or version.get("rc") != 0
        or version.get("status") != "ok"
        or version.get("command") != ["version"]
        or version_facts != [expected_version]
        or type(selftest.get("rc")) is not int
        or selftest.get("rc") != 0
        or selftest.get("status") != "ok"
        or selftest.get("command") != ["selftest"]
        or len(selftest_facts) != 1
        or re.fullmatch(
            r"selftest: pass=[0-9]+ warn=[0-9]+ fail=0 "
            r"duration=[0-9]+ms entries=[1-9][0-9]*",
            selftest_facts[0] if selftest_facts else "",
        )
        is None
    ):
        raise ContractError("candidate native health is not exact")
    return {
        "version_line": expected_version,
        "selftest_line": selftest_facts[0],
    }


def _require_exact_command_receipt(
    value: Any,
    command: list[str],
    label: str,
) -> dict[str, Any]:
    receipt = _dict(value, label)
    if (
        set(receipt) != {"command", "rc", "status", "trust", "begin", "end", "text"}
        or receipt.get("command") != command
        or type(receipt.get("rc")) is not int
        or receipt.get("rc") != 0
        or receipt.get("status") != "ok"
        or not isinstance(receipt.get("text"), str)
    ):
        raise ContractError(f"{label} is not an exact successful receipt")
    return receipt


def _validate_installed_health(
    spec: base.F1Spec,
    value: Any,
) -> dict[str, Any]:
    health = _dict(value, "resident-install first health")
    if set(health) != {"native", "pstore", "rootfs", "ncm"}:
        raise ContractError("resident-install first health keys are not exact")
    _require_exact_native_health(spec, health.get("native"))

    pstore = _dict(health.get("pstore"), "resident-install pstore health")
    if (
        set(pstore)
        != {"mounted_read_only", "entries", "mount", "listing", "summary", "unmount"}
        or pstore.get("mounted_read_only") is not True
        or pstore.get("entries") != []
    ):
        raise ContractError("resident-install pstore health is not exact")
    _require_exact_command_receipt(
        pstore.get("mount"),
        ["mountfs", "pstore", base.PSTORE_MOUNT_PATH, "pstore", "ro"],
        "resident-install pstore mount",
    )
    listing = _require_exact_command_receipt(
        pstore.get("listing"),
        ["ls", base.PSTORE_MOUNT_PATH],
        "resident-install pstore listing",
    )
    if base._pstore_entry_names(listing["text"]):  # noqa: SLF001
        raise ContractError("resident-install pstore listing is not empty")
    _require_exact_command_receipt(
        pstore.get("summary"),
        ["pstore", "full"],
        "resident-install pstore summary",
    )
    _require_exact_command_receipt(
        pstore.get("unmount"),
        ["umount", base.PSTORE_MOUNT_PATH],
        "resident-install pstore unmount",
    )

    rootfs = _dict(health.get("rootfs"), "resident-install rootfs health")
    expected_rootfs_command = [
        "sh",
        "-c",
        base.remote_source_preflight_script(spec),
    ]
    if (
        type(rootfs.get("rc")) is not int
        or rootfs.get("rc") != 0
        or rootfs.get("status") != "ok"
        or rootfs.get("command") != expected_rootfs_command
        or not isinstance(rootfs.get("text"), str)
        or rootfs["text"].count(
            "A90F1_SOURCE_PRECHECK exact=1 work_absent=1"
        ) != 1
    ):
        raise ContractError("resident-install rootfs health is not exact")

    ncm = _dict(health.get("ncm"), "resident-install NCM health")
    common_ncm = {
        "same_current_acm_usb_parent",
        "exact_interface_count",
        "profile_bound",
        "mutated",
        "profile_check",
        "active_before",
        "ready",
    }
    expected_ncm = common_ncm | (
        {"modify", "activate", "active_after"}
        if ncm.get("mutated") is True
        else set()
    )
    ready = _dict(ncm.get("ready"), "resident-install NCM readiness")
    profile_name = getattr(spec, "observer_host_ncm_profile", None)
    profile_check = _dict(
        ncm.get("profile_check"),
        "resident-install NCM profile check",
    )
    active_before = _dict(
        ncm.get("active_before"),
        "resident-install NCM active-before check",
    )
    host_receipt_keys = {"command", "returncode", "stdout", "stderr"}
    if (
        set(ncm) != expected_ncm
        or ncm.get("same_current_acm_usb_parent") is not True
        or type(ncm.get("exact_interface_count")) is not int
        or ncm.get("exact_interface_count") != 1
        or ncm.get("profile_bound") is not True
        or type(ncm.get("mutated")) is not bool
        or not isinstance(profile_name, str)
        or not profile_name
        or set(profile_check) != host_receipt_keys
        or type(profile_check.get("returncode")) is not int
        or profile_check.get("returncode") != 0
        or str(profile_check.get("stdout") or "").strip()
        != base.HOST_NCM_CONNECTION_TYPE
        or set(active_before) != host_receipt_keys
        or ready
        != {
            "verified_a90_ncm": True,
            "direct_route": True,
            "host_cidr_present": True,
            "device_ping": True,
        }
    ):
        raise ContractError("resident-install NCM health is not exact")
    selected_receipt = active_before
    if ncm["mutated"]:
        for label in ("modify", "activate"):
            receipt = _dict(ncm.get(label), f"resident-install NCM {label}")
            if (
                set(receipt) != host_receipt_keys
                or type(receipt.get("returncode")) is not int
                or receipt.get("returncode") != 0
            ):
                raise ContractError(f"resident-install NCM {label} failed")
        selected_receipt = _dict(
            ncm.get("active_after"),
            "resident-install NCM active-after check",
        )
        if set(selected_receipt) != host_receipt_keys:
            raise ContractError("resident-install NCM active-after check is not exact")
    if (
        type(selected_receipt.get("returncode")) is not int
        or selected_receipt.get("returncode") != 0
        or str(selected_receipt.get("stdout") or "").splitlines()[:1]
        != [profile_name]
    ):
        raise ContractError("resident-install NCM selected profile is not exact")
    return health


def _dispatch_resident_reboot(
    spec: base.F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    marker = "reboot: syncing and restarting"
    line = base.a90ctl.encode_cmdv1_line(list(REBOOT_COMMAND))
    text = base.a90ctl.bridge_exchange(
        args.bridge_host,
        args.bridge_port,
        line,
        min(float(spec.candidate_return_timeout), 30.0),
        markers=(marker.encode("ascii"),),
        input_mode=base.F1_SERIAL_INPUT_MODE,
        input_char_delay_sec=base.F1_SERIAL_INPUT_CHAR_DELAY_SEC,
        require_prompt_after_end=False,
        post_marker_drain_sec=0.0,
    )
    if text.count(marker) != 1:
        raise ContractError("resident reboot acceptance marker is not exact")
    return {"command": list(REBOOT_COMMAND), "accepted": True, "marker": marker}


def _validate_promoted_result(
    spec: base.F1Spec,
    result: dict[str, Any],
) -> dict[str, Any]:
    if (
        set(result) != PROMOTED_RESULT_KEYS
        or result.get("schema") != RESULT_SCHEMA
        or result.get("run_id") != spec.stage.run_id
        or result.get("status") != "PASS_A90_F1_RP_RESIDENT_PROMOTED"
        or result.get("manifest_sha256") != spec.stage.manifest_sha256
        or result.get("candidate_sha256") != spec.candidate.sha256
        or result.get("candidate_transfer_count") != 1
        or result.get("candidate_replay") is not False
        or result.get("resident_reboot_count") != 1
        or result.get("candidate_health_check_count") != 2
        or result.get("rollback_transfer_count") != 0
        or result.get("rollback_required") is not False
        or not isinstance(result.get("first_health"), dict)
        or not isinstance(result.get("second_health"), dict)
        or result.get("timeline_events") != list(base.PROMOTION_EVENTS)
    ):
        raise ContractError("promoted result is not exact")
    return result


def _publish_exact_promoted_result(
    spec: base.F1Spec,
    transaction_dir: Path,
    result: dict[str, Any],
) -> None:
    exact = _validate_promoted_result(spec, result)
    path = transaction_dir / "result.json"
    if path.exists():
        base.require_private_regular(path)
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("existing promoted result is invalid") from exc
        if existing != exact:
            raise ContractError("existing promoted result changed")
        return
    base.write_private_json_exclusive(path, exact)


def _promoted_result_from_terminal(
    spec: base.F1Spec,
    record: dict[str, Any],
) -> dict[str, Any]:
    common = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    payload = PROMOTED_RESULT_KEYS - {"schema", "run_id", "manifest_sha256"}
    if (
        set(record) != common | payload
        or record.get("schema") != base.JOURNAL_SCHEMA
        or record.get("state") != "PROMOTED_CLOSED"
        or record.get("action") != "closed"
    ):
        raise ContractError("promoted terminal journal is not exact")
    result = {key: record.get(key) for key in PROMOTED_RESULT_KEYS}
    result["schema"] = RESULT_SCHEMA
    return _validate_promoted_result(spec, result)


def repair_promoted_result(
    spec: base.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if not records or records[-1].get("action") != "closed":
        raise ContractError("promotion result repair requires terminal journal")
    result = _promoted_result_from_terminal(spec, records[-1])
    _publish_exact_promoted_result(spec, transaction_dir, result)
    return result


def _validate_installed_result(
    spec: base.F1Spec,
    result: dict[str, Any],
) -> dict[str, Any]:
    if (
        set(result) != INSTALLED_RESULT_KEYS
        or spec.manifest.get("schema") != staging.RESIDENT_INSTALL_MANIFEST_SCHEMA
        or _dict(
            spec.manifest.get("resident_promotion"),
            "resident_promotion",
        ).get("mode") != INSTALL_MODE
        or result.get("schema") != INSTALL_RESULT_SCHEMA
        or result.get("run_id") != spec.stage.run_id
        or result.get("status") != INSTALL_STATUS
        or result.get("manifest_sha256") != spec.stage.manifest_sha256
        or result.get("candidate_sha256") != spec.candidate.sha256
        or type(result.get("candidate_transfer_count")) is not int
        or result.get("candidate_transfer_count") != 1
        or result.get("candidate_replay") is not False
        or type(result.get("resident_reboot_count")) is not int
        or result.get("resident_reboot_count") != 0
        or type(result.get("candidate_health_check_count")) is not int
        or result.get("candidate_health_check_count") != 1
        or type(result.get("rollback_transfer_count")) is not int
        or result.get("rollback_transfer_count") != 0
        or result.get("rollback_required") is not False
        or result.get("device_safety_state") != "RESIDENT_HEALTHY"
        or not isinstance(result.get("first_health"), dict)
        or tuple(result.get("timeline_events") or ()) != INSTALL_EVENTS
    ):
        raise ContractError("resident-install result is not exact")
    _validate_installed_health(spec, result.get("first_health"))
    return result


def _publish_exact_installed_result(
    spec: base.F1Spec,
    transaction_dir: Path,
    result: dict[str, Any],
) -> None:
    exact = _validate_installed_result(spec, result)
    path = transaction_dir / "result.json"
    if path.exists():
        base.require_private_regular(path)
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("existing resident-install result is invalid") from exc
        if existing != exact:
            raise ContractError("existing resident-install result changed")
        return
    base.write_private_json_exclusive(path, exact)


def _installed_result_from_terminal(
    spec: base.F1Spec,
    record: dict[str, Any],
) -> dict[str, Any]:
    common = {
        "schema",
        "sequence",
        "timestamp_utc",
        "run_id",
        "manifest_sha256",
        "state",
        "action",
    }
    payload = INSTALLED_RESULT_KEYS - {"schema", "run_id", "manifest_sha256"}
    if (
        set(record) != common | payload
        or record.get("schema") != base.JOURNAL_SCHEMA
        or record.get("state") != INSTALL_TERMINAL_STATE
        or record.get("action") != "closed"
    ):
        raise ContractError("resident-install terminal journal is not exact")
    result = {key: record.get(key) for key in INSTALLED_RESULT_KEYS}
    result["schema"] = INSTALL_RESULT_SCHEMA
    return _validate_installed_result(spec, result)


def repair_installed_result(
    spec: base.F1Spec,
    transaction_dir: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if not records or records[-1].get("action") != "closed":
        raise ContractError("resident-install result repair requires terminal journal")
    if (
        tuple(record.get("action") for record in records)
        != INSTALL_SUCCESS_ACTIONS
        or tuple(record.get("state") for record in records)
        != INSTALL_SUCCESS_STATES
    ):
        raise ContractError("resident-install journal success sequence is not exact")
    by_action = {str(record["action"]): record for record in records}
    started = by_action["candidate-transfer-started"]
    flashed = by_action["candidate-flashed"]
    boot_ready = by_action["candidate-boot-ready"]
    health_verified = by_action["candidate-health-verified"]
    if (
        started.get("candidate_sha256") != spec.candidate.sha256
        or type(started.get("candidate_transfer_count_max")) is not int
        or started.get("candidate_transfer_count_max") != 1
        or started.get("candidate_replay") is not False
        or started.get("rollback_required") is not True
        or flashed.get("candidate_sha256") != spec.candidate.sha256
        or type(flashed.get("candidate_transfer_count")) is not int
        or flashed.get("candidate_transfer_count") != 1
        or flashed.get("candidate_replay") is not False
        or flashed.get("rollback_required") is not True
        or boot_ready.get("candidate_version") != spec.candidate_version
        or boot_ready.get("candidate_build") != spec.candidate_build
        or boot_ready.get("selftest_fail_zero") is not True
        or type(health_verified.get("candidate_health_check_count")) is not int
        or health_verified.get("candidate_health_check_count") != 1
    ):
        raise ContractError("resident-install journal candidate proof is not exact")
    native_exact = _require_exact_native_health(spec, boot_ready.get("health"))
    if health_verified.get("native_exact") != native_exact:
        raise ContractError("resident-install journal native proof changed")
    first_health = _validate_installed_health(
        spec,
        health_verified.get("health"),
    )
    result = _installed_result_from_terminal(spec, records[-1])
    if result.get("first_health") != first_health:
        raise ContractError("resident-install terminal health changed")
    _publish_exact_installed_result(spec, transaction_dir, result)
    return result


def close_installed_transaction(
    spec: base.F1Spec,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    *,
    first_health: dict[str, Any],
) -> dict[str, Any]:
    base.ensure_event(
        transaction_dir,
        events,
        "live_session_end",
        allow_promotion=True,
    )
    names = [event["name"] for event in events]
    if tuple(names) != INSTALL_EVENTS:
        raise ContractError("resident-install success lacks the canonical timeline")
    result = {
        "schema": INSTALL_RESULT_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": INSTALL_STATUS,
        "manifest_sha256": spec.stage.manifest_sha256,
        "candidate_sha256": spec.candidate.sha256,
        "candidate_transfer_count": 1,
        "candidate_replay": False,
        "resident_reboot_count": 0,
        "candidate_health_check_count": 1,
        "rollback_transfer_count": 0,
        "rollback_required": False,
        "device_safety_state": "RESIDENT_HEALTHY",
        "first_health": first_health,
        "timeline_events": names,
    }
    base.append_record(
        journal_dir,
        INSTALL_TERMINAL_STATE,
        "closed",
        result,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    _publish_exact_installed_result(spec, transaction_dir, result)
    return result


def close_promoted_transaction(
    spec: base.F1Spec,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    *,
    first_health: dict[str, Any],
    second_health: dict[str, Any],
) -> dict[str, Any]:
    base.ensure_event(
        transaction_dir,
        events,
        "live_session_end",
        allow_promotion=True,
    )
    names = [event["name"] for event in events]
    if tuple(names) != base.PROMOTION_EVENTS:
        raise ContractError("promotion success lacks the canonical timeline")
    result = {
        "schema": RESULT_SCHEMA,
        "run_id": spec.stage.run_id,
        "status": "PASS_A90_F1_RP_RESIDENT_PROMOTED",
        "manifest_sha256": spec.stage.manifest_sha256,
        "candidate_sha256": spec.candidate.sha256,
        "candidate_transfer_count": 1,
        "candidate_replay": False,
        "resident_reboot_count": 1,
        "candidate_health_check_count": 2,
        "rollback_transfer_count": 0,
        "rollback_required": False,
        "first_health": first_health,
        "second_health": second_health,
        "timeline_events": names,
    }
    base.append_record(
        journal_dir,
        "PROMOTED_CLOSED",
        "closed",
        result,
        manifest_sha256=spec.stage.manifest_sha256,
        run_id=spec.stage.run_id,
    )
    _publish_exact_promoted_result(spec, transaction_dir, result)
    return result


def promotion_tail(
    spec: base.F1Spec,
    args: argparse.Namespace,
    transaction_dir: Path,
    journal_dir: Path,
    events: list[dict[str, str]],
    candidate_health: dict[str, Any],
    guard: base.cdc_guard.ModemManagerGuard,
) -> dict[str, Any]:
    guard_released = False
    try:
        first_native_exact = _require_exact_native_health(spec, candidate_health)
        first_health = _promotion_health(spec, args, candidate_health)
        base.append_record(
            journal_dir,
            "CANDIDATE_HEALTH_VERIFIED",
            "candidate-health-verified",
            {
                "candidate_health_check_count": 1,
                "native_exact": first_native_exact,
                "health": first_health,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        mode = _dict(
            spec.manifest.get("resident_promotion"),
            "resident_promotion",
        ).get("mode")
        if mode == INSTALL_MODE:
            if not guard.healthy(recheck=True):
                raise ContractError("resident-install ModemManager guard was lost")
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor="resident-promotion",
            )
            guard_released = True
            if release.get("released") is not True:
                raise ContractError("resident-install ModemManager guard did not release")
            return close_installed_transaction(
                spec,
                transaction_dir,
                journal_dir,
                events,
                first_health=first_health,
            )
        if mode != MODE:
            raise ContractError("resident promotion mode changed after validation")
        channel = base.settle_observation_channel(args, phase="before-resident-reboot")
        candidate_epoch = base.capture_bridge_serial_epoch(spec, args)
        if not guard.healthy(recheck=True):
            raise ContractError("resident reboot ModemManager guard was lost")
        base.append_record(
            journal_dir,
            "RESIDENT_REBOOT_INTENT",
            "resident-reboot-intent",
            {
                "resident_reboot_count_max": 1,
                "command": list(REBOOT_COMMAND),
                "candidate_epoch": candidate_epoch,
                "channel": channel,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        base.ensure_event(
            transaction_dir,
            events,
            "resident_reboot_start",
            allow_promotion=True,
        )
        if not guard.healthy(recheck=True):
            raise ContractError("resident reboot guard was lost before dispatch")
        dispatch = _dispatch_resident_reboot(spec, args)
        base.append_record(
            journal_dir,
            "RESIDENT_REBOOT_INTENT",
            "resident-reboot-dispatched",
            {"resident_reboot_count": 1, "dispatch": dispatch},
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        returned_native = base._verify_candidate_after_return_epoch_once(  # noqa: SLF001
            spec,
            args,
            candidate_epoch,
            phase="resident-reboot-return",
            return_guard=guard,
        )
        base.append_record(
            journal_dir,
            "RESIDENT_REBOOTED",
            "resident-rebooted",
            {"resident_reboot_count": 1, "return": returned_native},
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        base.ensure_event(
            transaction_dir,
            events,
            "resident_reboot_ready",
            allow_promotion=True,
        )
        second_health = _promotion_health(spec, args, returned_native)
        if not guard.healthy(recheck=True):
            raise ContractError("resident reboot guard was lost after health checks")
        second_guard = base.require_returned_modemmanager_guard(
            spec,
            returned_native["return_epoch"],
            guard,
        )
        if not guard.healthy(recheck=True):
            raise ContractError("resident reboot guard was lost before health intent")
        base.append_record(
            journal_dir,
            "RESIDENT_HEALTH_VERIFIED",
            "resident-health-verified",
            {
                "candidate_health_check_count": 2,
                "usb_generations_distinct": True,
                "candidate_return_modemmanager_guard": second_guard,
                "health": second_health,
            },
            manifest_sha256=spec.stage.manifest_sha256,
            run_id=spec.stage.run_id,
        )
        base.ensure_event(
            transaction_dir,
            events,
            "promotion_health_verified",
            allow_promotion=True,
        )
        release = base.release_candidate_return_modemmanager_guard(
            guard,
            transaction_dir,
            corridor="resident-promotion",
        )
        guard_released = True
        if release.get("released") is not True:
            raise ContractError("resident reboot ModemManager guard did not release")
        return close_promoted_transaction(
            spec,
            transaction_dir,
            journal_dir,
            events,
            first_health=first_health,
            second_health=second_health,
        )
    finally:
        if not guard_released:
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor="resident-promotion",
            )
            if release.get("released") is not True:
                raise ContractError("resident promotion guard did not release")


def _consumed_rollback_guard_attempt(
    transaction_dir: Path,
    corridor: str,
) -> bool:
    arm_path = transaction_dir / f"{corridor}-modemmanager-guard-arm.json"
    release_path = (
        transaction_dir / f"{corridor}-modemmanager-guard-release.json"
    )
    failure_path = (
        transaction_dir / f"{corridor}-modemmanager-guard-release-failed.json"
    )
    arm_exists = os.path.lexists(arm_path)
    release_exists = os.path.lexists(release_path)
    failure_exists = os.path.lexists(failure_path)
    if not arm_exists and not release_exists and not failure_exists:
        return False
    if not arm_exists:
        raise ContractError("rollback recovery guard release lacks its arm")
    if release_exists and failure_exists:
        raise ContractError("rollback recovery guard has conflicting releases")
    base.require_private_regular(arm_path)
    try:
        arm = json.loads(arm_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("rollback recovery guard evidence is invalid") from exc
    receipt = arm.get("receipt") if isinstance(arm, dict) else None
    guard_spec = arm.get("guard_spec") if isinstance(arm, dict) else None
    topology = arm.get("topology") if isinstance(arm, dict) else None
    instance = receipt.get("instance_sha256") if isinstance(receipt, dict) else None
    try:
        receipt = base.require_exact_modemmanager_guard_receipt(
            receipt,
            guard_spec,
            topology,
        )
    except base.ContractError as exc:
        raise ContractError("rollback recovery guard receipt is invalid") from exc
    if (
        not isinstance(arm, dict)
        or set(arm)
        != {
            "schema",
            "corridor",
            "max_sec",
            "child_pid",
            "guard_spec",
            "topology",
            "receipt",
        }
        or arm.get("schema") != base.MODEMMANAGER_GUARD_ARM_SCHEMA
        or arm.get("corridor") != corridor
        or type(arm.get("max_sec")) is not int
        or not (
            base.cdc_guard.GUARD_DEFAULT_MAX_SEC
            <= arm.get("max_sec")
            <= base.cdc_guard.GUARD_MAX_SEC_LIMIT
        )
        or type(arm.get("child_pid")) is not int
        or arm.get("child_pid") <= 0
    ):
        raise ContractError("rollback recovery guard evidence lost its binding")
    if failure_exists:
        base.require_private_regular(failure_path)
        try:
            failure = json.loads(failure_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ContractError("rollback recovery guard failure is invalid") from exc
        failure_returncode = (
            failure.get("returncode") if isinstance(failure, dict) else None
        )
        expected_status = (
            "guard-expired"
            if failure_returncode == base.cdc_guard.GUARD_EXPIRED_EXIT
            else (
                "guard-exited-uncommanded"
                if failure_returncode
                in {0, base.cdc_guard.GUARD_UNCOMMANDED_EXIT}
                else "release-failed"
            )
        )
        returncode_shape = (
            isinstance(failure, dict)
            and set(failure)
            == {
                "schema",
                "status",
                "instance_sha256",
                "returncode",
                "released",
            }
            and type(failure_returncode) is int
            and failure.get("status") == expected_status
        )
        error_shape = (
            set(failure)
            == {
                "schema",
                "status",
                "instance_sha256",
                "error_type",
                "released",
            }
            and failure.get("status") == "release-failed"
            and isinstance(failure.get("error_type"), str)
            and base.cdc_guard.ERROR_TYPE_RE.fullmatch(failure["error_type"])
            is not None
        ) if isinstance(failure, dict) else False
        if (
            not isinstance(failure, dict)
            or failure.get("schema") != base.cdc_guard.GUARD_SCHEMA
            or failure.get("instance_sha256") != instance
            or failure.get("released") is not False
            or not (returncode_shape or error_shape)
        ):
            raise ContractError(
                "rollback recovery guard failure lost its binding"
            )
    if not release_exists:
        if (Path("/proc") / str(arm["child_pid"])).exists():
            raise ContractError("rollback recovery guard attempt is still active")
        deadline = time.monotonic() + GUARD_CRASH_CLEANUP_WAIT_SEC
        while os.path.lexists(base.cdc_guard.GUARD_RUNTIME_RULE_PATH):
            if time.monotonic() >= deadline:
                raise ContractError(
                    "interrupted rollback recovery guard rule is still present"
                )
            time.sleep(GUARD_CRASH_CLEANUP_POLL_SEC)
        return True
    base.require_private_regular(release_path)
    try:
        release = json.loads(release_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("rollback recovery guard release is invalid") from exc
    if (
        not isinstance(release, dict)
        or set(release)
        != {
            "schema",
            "status",
            "instance_sha256",
            "returncode",
            "released",
        }
        or release.get("schema") != base.cdc_guard.GUARD_SCHEMA
        or release.get("status") != "released"
        or release.get("released") is not True
        or release.get("returncode") != 0
        or release.get("instance_sha256") != instance
    ):
        raise ContractError("rollback recovery guard evidence lost its binding")
    return True


def _next_rollback_guard_corridor(transaction_dir: Path) -> str:
    first = _consumed_rollback_guard_attempt(
        transaction_dir,
        "rollback-recovery-1",
    )
    second = _consumed_rollback_guard_attempt(
        transaction_dir,
        "rollback-recovery-2",
    )
    if not first and not second:
        return "rollback-recovery-1"
    if first and not second:
        return "rollback-recovery-2"
    raise ContractError("rollback recovery guard attempts are not exact or exhausted")


def recover_promotion_or_rollback(
    spec: base.F1Spec,
    args: argparse.Namespace,
) -> dict[str, Any]:
    transaction_dir = base.exact_transaction_dir(spec, args.transaction_dir)
    records = base.read_journal(spec, transaction_dir)
    actions = [record.get("action") for record in records]
    if (
        records
        and records[-1].get("state") == INSTALL_TERMINAL_STATE
        and records[-1].get("action") == "closed"
    ):
        approval = base.approved_bindings(spec, args, recovery=True)
        base.verify_local_closure(spec)
        base.require_consumed_approval(records, approval)
        return repair_installed_result(spec, transaction_dir, records)
    if (
        records
        and records[-1].get("state") == "PROMOTED_CLOSED"
        and records[-1].get("action") == "closed"
    ):
        approval = base.approved_bindings(spec, args, recovery=True)
        base.verify_local_closure(spec)
        base.require_consumed_approval(records, approval)
        return repair_promoted_result(spec, transaction_dir, records)
    if "candidate-transfer-started" not in actions:
        raise ContractError("promotion recovery lacks durable candidate intent")
    if "closed" in actions:
        raise ContractError("promotion recovery transaction is already closed")
    current_state = records[-1].get("state")
    if not isinstance(current_state, str) or not current_state:
        raise ContractError("promotion recovery journal state is not exact")
    approval = base.approved_bindings(spec, args, recovery=True)
    base.verify_local_closure(spec)
    base.require_consumed_approval(records, approval)
    corridor: str | None = None
    guard: base.cdc_guard.ModemManagerGuard | None = None
    try:
        corridor = _next_rollback_guard_corridor(transaction_dir)
        prepared_inputs = base.resident_promotion_guard_inputs(
            transaction_dir,
            records,
        )
        guard = base.arm_candidate_return_modemmanager_guard(
            spec,
            args,
            transaction_dir,
            corridor=corridor,
            prepared_inputs=prepared_inputs,
        )
        base.modemmanager_guard_arm_evidence(
            transaction_dir,
            corridor,
            guard,
        )
    except Exception:
        if guard is not None and corridor is not None:
            try:
                base.release_candidate_return_modemmanager_guard(
                    guard,
                    transaction_dir,
                    corridor=corridor,
                )
            # Observer cleanup cannot revoke the pre-authorized exact rollback.
            except Exception:  # noqa: BLE001 - rollback authority is stronger
                pass
        return base.recover_approved_rollback(spec, args)
    release_attempted = False

    def release_before_close() -> None:
        nonlocal release_attempted
        release_attempted = True
        assert guard is not None
        assert corridor is not None
        release = base.release_candidate_return_modemmanager_guard(
            guard,
            transaction_dir,
            corridor=corridor,
        )
        if release.get("released") is not True:
            raise ContractError("rollback recovery guard did not release")

    try:
        assert corridor is not None
        return base.recover_approved_rollback(
            spec,
            args,
            return_guard=guard,
            before_close=release_before_close,
        )
    finally:
        if not release_attempted:
            release = base.release_candidate_return_modemmanager_guard(
                guard,
                transaction_dir,
                corridor=corridor,
            )
            if release.get("released") is not True:
                raise ContractError("rollback recovery guard did not release")


def inspect_manifest(
    spec: base.F1Spec,
    promotion: dict[str, Any],
    issues: list[str],
) -> dict[str, Any]:
    result = base.inspect_manifest(spec, issues)
    result["resident_promotion"] = promotion
    result["resident_promotion_ready_for_approval"] = not issues
    result["live_authority"] = False
    result["device_contact"] = False
    result["device_write"] = False
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = base.build_parser()
    parser.description = __doc__
    parser.add_argument("--execute-approved-promotion", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    forbidden = (
        args.execute_approved_f1,
        args.continue_attended_f1,
        args.confirm_visible_display,
    )
    if any(forbidden):
        raise ContractError("promotion runner refuses ordinary/attended F1 modes")
    selected = sum(
        bool(value)
        for value in (
            args.prepare_approval,
            args.execute_approved_promotion,
            args.recover_approved_rollback,
        )
    )
    if selected > 1:
        raise ContractError("promotion runner modes are mutually exclusive")
    final_only = selected == 1
    spec, promotion, issues = load_spec(
        args.manifest,
        args.expect_manifest_sha256,
        allow_draft=not final_only,
        recovery=args.recover_approved_rollback,
    )
    if not final_only:
        result = inspect_manifest(spec, promotion, issues)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not issues else 2
    if args.prepare_approval:
        if any(
            value is not None
            for value in (
                args.approval,
                args.attended_approval,
                args.visible_approval,
                args.transaction_dir,
                args.recovery_path,
            )
        ):
            raise ContractError("approval preparation accepts no live arguments")
        result = base.prepare_approval(spec)
    elif args.execute_approved_promotion:
        if args.transaction_dir is None or args.approval is None:
            raise ContractError("promotion execution requires transaction and approval")
        if any(
            value is not None
            for value in (
                args.attended_approval,
                args.visible_approval,
                args.recovery_path,
            )
        ):
            raise ContractError("promotion execution accepts no continuation/recovery input")
        result = base.execute_approved_f1(
            spec,
            args,
            promotion_tail=promotion_tail,
        )
    else:
        if args.transaction_dir is None:
            raise ContractError("rollback recovery requires transaction directory")
        if any(
            value is not None
            for value in (
                args.approval,
                args.attended_approval,
                args.visible_approval,
            )
        ):
            raise ContractError("rollback recovery accepts no new approval")
        result = recover_promotion_or_rollback(spec, args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001 - concise fail-closed CLI
        print(f"a90-resident-promotion-v1: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
