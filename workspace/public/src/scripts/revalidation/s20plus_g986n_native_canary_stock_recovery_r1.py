#!/usr/bin/env python3
"""Dormant stock-boot recovery owner for the S20+ N1 root-data transaction.

The runner consumes only the exact durable handoff written by
``s20plus_g986n_native_canary_r1.py``.  It has no candidate path and can send
only the already-qualified single-member stock ``boot.img.lz4`` AP once.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable

import s20plus_g986n_magisk_bootstrap_f1 as bootstrap
import s20plus_g986n_native_canary_r1 as root_data


VERSION = "s20plus-g986n-native-canary-stock-recovery-r1-v1"
NATIVE_CANARY_STOCK_RECOVERY_ACTIVE = False
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "9849416b63064406afa5c7c235c6b7b1e79e490ceda9af2417b6ddd77dc6b8bb"
SCRIPT = Path(__file__).resolve()

PHYSICAL_ARM = "S20PLUS-G986N-NATIVE-CANARY-R1-STOCK-RECOVERY-ARM"
PHYSICAL_CONFIRM = "S20PLUS-G986N-NATIVE-CANARY-R1-STOCK-RECOVERY-CONFIRM"
ARM_ARRIVAL_WINDOW_SEC = 300

Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]

STOCK_ARM_FILES = {
    "stock-recovery-handoff.json",
    "stock-recovery-arm.json",
    "stock-recovery-arrival.json",
}
STOCK_DISPATCH_FILES = STOCK_ARM_FILES | {
    "stock-recovery-confirmation.json",
    "rollback-intent.json",
    "events/90-rollback-transfer-started.json",
}
STOCK_COMPLETION_FILES = STOCK_DISPATCH_FILES | {
    "rollback.stdout",
    "rollback.stderr",
    "rollback-result.json",
}
STOCK_PENDING_FILE = "stock-recovery-result.json"
STOCK_HEALTH_FILE = "stock-final-health.json"
STOCK_KNOWN_FILES = STOCK_COMPLETION_FILES | {
    STOCK_PENDING_FILE,
    STOCK_HEALTH_FILE,
    "terminal-input.json",
    "terminal-result.json",
}
STOCK_TRANSFER_FILES = {"rollback.stdout", "rollback.stderr", "rollback-result.json"}
STOCK_TRANSFER_STATES = {
    "odin_transfer_completed",
    "odin_device_session_failure_or_unknown",
    "odin_local_parse_failure",
    "odin_effect_outcome_unproved_after_intent",
}

ROOT_ABSENCE_RAW_RE = re.compile(
    rb"(?:/system/bin/sh: )?su: "
    rb"(?:not found|inaccessible or not found|no such file)\n?",
    re.IGNORECASE,
)


class StockRecoveryError(RuntimeError):
    pass


def exact_root_absence_text(stdout: bytes, stderr: bytes) -> str:
    if stdout != b"" or ROOT_ABSENCE_RAW_RE.fullmatch(stderr) is None:
        raise StockRecoveryError("N1 stock root-absence raw transcript is not exact")
    body = stderr[:-1] if stderr.endswith(b"\n") else stderr
    try:
        return body.decode("ascii", "strict")
    except UnicodeError as exc:
        raise StockRecoveryError("N1 stock root-absence transcript is not ASCII") from exc


def normalized_self_sha256() -> str:
    payload = SCRIPT.read_bytes()
    pattern = rb'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"'
    normalized, count = re.subn(
        pattern,
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        payload,
    )
    if count != 1:
        raise StockRecoveryError("N1 stock-recovery normalized identity is ambiguous")
    return hashlib.sha256(normalized).hexdigest()


def self_receipt() -> dict[str, Any]:
    metadata = SCRIPT.lstat()
    normalized = normalized_self_sha256()
    if (
        SCRIPT.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256
    ):
        raise StockRecoveryError("N1 stock-recovery runner does not match review")
    return {
        "path": str(SCRIPT),
        "size": metadata.st_size,
        "sha256": bootstrap.sha256_file(SCRIPT),
        "normalized_sha256": normalized,
    }


def require_active() -> None:
    if not NATIVE_CANARY_STOCK_RECOVERY_ACTIVE or not root_data.NATIVE_CANARY_R1_ACTIVE:
        raise StockRecoveryError("S20+ N1 stock recovery is not active")


def read_handoff(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / "stock-recovery-handoff.json", "N1 stock-recovery handoff"
    )
    expected_runner = prepared["binding"]["closure"]["stock_recovery_runner"]
    current = self_receipt()
    if not root_data.exact_typed_equal(current, expected_runner):
        raise StockRecoveryError("N1 recovery runner differs from the approved binding")
    if not root_data.exact_typed_equal(value, {
        "schema": "s20plus_g986n_native_canary_r1_stock_handoff_v1",
        "version": root_data.VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "run_dir": str(run_dir),
        "stock_boot": prepared["binding"]["artifacts"]["stock_boot"],
        "recovery_runner": expected_runner,
        "operator_confirmed": True,
        "operator_asserted_rooted_recovery_unavailable": True,
        "confirmation": root_data.STOCK_HANDOFF_CONFIRM,
        "attempt": 1,
        "replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }) or type(value.get("attempt")) is not int or not isinstance(value.get("at"), str):
        raise StockRecoveryError("N1 stock-recovery handoff is malformed or mismatched")
    return value


def validate_stock_journal(
    run_dir: Path,
    prepared: dict[str, Any],
    allowed: set[str],
    required: set[str],
) -> set[str]:
    seen = root_data.validate_recovery_journal(
        run_dir,
        prepared,
        allowed,
        allow_uncertain_commands=True,
    )
    root_data.assert_stock_handoff_eligible_journal(run_dir, seen)
    if seen.intersection(STOCK_KNOWN_FILES) != allowed:
        raise StockRecoveryError("N1 stock-recovery journal is in the wrong state")
    if not required.issubset(seen):
        raise StockRecoveryError("N1 stock-recovery journal is incomplete")
    if "events/90-rollback-transfer-started.json" in seen:
        validate_rollback_event(run_dir, prepared)
    return seen


def validate_rollback_event(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / "events/90-rollback-transfer-started.json",
        "N1 rollback transfer event",
    )
    if not root_data.exact_typed_equal(value, {
        "schema": "s20plus_g986n_f1_event_v1",
        "version": bootstrap.VERSION,
        "ordinal": 90,
        "name": "rollback-transfer-started",
        "at": value.get("at") if isinstance(value, dict) else None,
        "ap_sha256": bootstrap.ROLLBACK_SHA256,
    }) or type(value.get("ordinal")) is not int or not isinstance(value.get("at"), str):
        raise StockRecoveryError("N1 rollback transfer event is malformed")
    validate_rollback_intent(run_dir, prepared)
    return value


def validate_rollback_intent(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / "rollback-intent.json", "N1 rollback transfer intent"
    )
    endpoint = value.get("endpoint") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "kind", "binding_sha256", "ap_sha256",
            "endpoint", "attempt", "no_replay", "at",
        }
        or value.get("schema") != "s20plus_g986n_f1_transfer_intent_v1"
        or value.get("version") != bootstrap.VERSION
        or value.get("kind") != "rollback"
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("ap_sha256") != bootstrap.ROLLBACK_SHA256
        or type(value.get("attempt")) is not int
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value.get("at")
        or not isinstance(endpoint, dict)
        or set(endpoint) != {"device", "identity"}
        or not isinstance(endpoint.get("device"), str)
        or bootstrap.USBFS_RE.fullmatch(endpoint.get("device")) is None
        or not isinstance(endpoint.get("identity"), list)
        or len(endpoint.get("identity", [])) != 4
        or any(type(item) is not int for item in endpoint.get("identity", []))
    ):
        raise StockRecoveryError("N1 rollback transfer intent is malformed")
    return value


def validate_rollback_outcome(
    run_dir: Path,
    prepared: dict[str, Any],
    expected_classification: str,
) -> dict[str, Any]:
    binding_sha256 = prepared["binding_sha256"]
    intent = validate_rollback_intent(run_dir, prepared)
    result = root_data.read_exact_json(
        run_dir / "rollback-result.json", "N1 rollback transfer result"
    )
    if result.get("schema") == "s20plus_g986n_f1_transfer_failure_v1":
        if (
            not root_data.exact_typed_equal(result, {
                "schema": "s20plus_g986n_f1_transfer_failure_v1",
                "kind": "rollback",
                "classification": "odin_device_session_failure_or_unknown",
                "error_class": result.get("error_class"),
                "possible_partition_effect": True,
            })
            or not isinstance(result.get("error_class"), str)
            or re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_.]{0,127}", result.get("error_class")
            )
            is None
            or expected_classification != "odin_device_session_failure_or_unknown"
            or os.path.lexists(run_dir / "rollback.stdout")
            or os.path.lexists(run_dir / "rollback.stderr")
        ):
            raise StockRecoveryError("N1 rollback failure evidence is malformed")
        return result
    receipt = result.get("receipt") if isinstance(result, dict) else None
    if (
        not isinstance(result, dict)
        or set(result) != {
            "schema", "version", "kind", "binding_sha256", "endpoint",
            "classification", "receipt", "stdout_sha256", "stderr_sha256",
        }
        or result.get("schema") != "s20plus_g986n_f1_transfer_v1"
        or result.get("version") != bootstrap.VERSION
        or result.get("kind") != "rollback"
        or result.get("binding_sha256") != binding_sha256
        or not root_data.exact_typed_equal(
            result.get("endpoint"), intent.get("endpoint")
        )
        or result.get("classification") != expected_classification
        or expected_classification not in {
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
            "odin_local_parse_failure",
        }
        or not isinstance(receipt, dict)
    ):
        raise StockRecoveryError("N1 rollback transfer evidence is malformed")
    stdout = root_data.read_exact_blob(
        run_dir / "rollback.stdout", "N1 rollback stdout", bootstrap.MAX_OUTPUT
    )
    stderr = root_data.read_exact_blob(
        run_dir / "rollback.stderr", "N1 rollback stderr", bootstrap.MAX_OUTPUT
    )
    expected_receipt_keys = {
        "label", "returncode", "command_shape", "regular_path_inputs",
        "anonymous_proc_fd_inputs", "odin", "ap", "endpoint_path_sha256",
        "endpoint_pre_identity", "endpoint_post_identity", "endpoint_post_state",
        "stdout_bytes", "stderr_bytes",
    }
    post_state = receipt.get("endpoint_post_state")
    post_identity = receipt.get("endpoint_post_identity")
    if (
        set(receipt) != expected_receipt_keys
        or receipt.get("label") != "rollback"
        or type(receipt.get("returncode")) is not int
        or receipt.get("command_shape")
        != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or receipt.get("regular_path_inputs") is not True
        or receipt.get("anonymous_proc_fd_inputs") is not False
        or type(receipt.get("stdout_bytes")) is not int
        or receipt.get("stdout_bytes") != len(stdout)
        or type(receipt.get("stderr_bytes")) is not int
        or receipt.get("stderr_bytes") != len(stderr)
        or not isinstance(result.get("stdout_sha256"), str)
        or result.get("stdout_sha256") != hashlib.sha256(stdout).hexdigest()
        or not isinstance(result.get("stderr_sha256"), str)
        or result.get("stderr_sha256") != hashlib.sha256(stderr).hexdigest()
        or not root_data.exact_typed_equal(receipt.get("ap"), {
            "path": str(bootstrap.ROLLBACK),
            "size": bootstrap.ROLLBACK_SIZE,
            "sha256": bootstrap.ROLLBACK_SHA256,
        })
        or not root_data.exact_typed_equal(receipt.get("odin"), {
            "path": str(bootstrap.ODIN),
            "size": bootstrap.ODIN_SIZE,
            "sha256": bootstrap.ODIN_SHA256,
        })
        or receipt.get("endpoint_path_sha256")
        != hashlib.sha256(intent["endpoint"]["device"].encode()).hexdigest()
        or not root_data.exact_typed_equal(
            receipt.get("endpoint_pre_identity"), intent["endpoint"]["identity"]
        )
        or post_state not in {"same", "absent", "changed"}
        or (
            post_state == "same"
            and not root_data.exact_typed_equal(
                post_identity, intent["endpoint"]["identity"]
            )
        )
        or (post_state == "absent" and post_identity is not None)
        or (
            post_state == "changed"
            and (
                not isinstance(post_identity, list)
                or len(post_identity) != 4
                or any(type(item) is not int for item in post_identity)
                or post_identity == intent["endpoint"]["identity"]
            )
        )
        or bootstrap.persisted_transfer_classification(receipt, stdout, stderr)
        != expected_classification
    ):
        raise StockRecoveryError("N1 rollback transfer receipt is malformed")
    return result


def validate_stock_transfer_state(
    run_dir: Path,
    prepared: dict[str, Any],
) -> tuple[str, set[str], bool]:
    """Classify a consumed stock intent without ever dispatching Odin again."""
    seen = root_data.validate_recovery_journal(
        run_dir,
        prepared,
        STOCK_KNOWN_FILES,
        allow_uncertain_commands=True,
    )
    stock_seen = seen.intersection(STOCK_KNOWN_FILES)
    required_prefix = STOCK_ARM_FILES | {
        "stock-recovery-confirmation.json",
        "rollback-intent.json",
    }
    if not required_prefix.issubset(stock_seen):
        raise StockRecoveryError("N1 stock transfer observation lacks its durable intent")
    arm_record = validate_arm(run_dir, prepared)
    intent = validate_rollback_intent(run_dir, prepared)
    confirmation = root_data.read_exact_json(
        run_dir / "stock-recovery-confirmation.json",
        "N1 stock confirmation",
    )
    endpoint = confirmation.get("endpoint") if isinstance(confirmation, dict) else None
    validate_confirmation(run_dir, prepared, endpoint)
    if (
        not root_data.exact_typed_equal(endpoint, arm_record["arrival_endpoint"])
        or not root_data.exact_typed_equal(intent.get("endpoint"), {
            "device": endpoint.get("device") if isinstance(endpoint, dict) else None,
            "identity": endpoint.get("endpoint_identity") if isinstance(endpoint, dict) else None,
        })
    ):
        raise StockRecoveryError("N1 stock transfer prefix endpoint is mismatched")

    outcome_files = stock_seen.intersection(STOCK_TRANSFER_FILES)
    event_name = "events/90-rollback-transfer-started.json"
    event_present = event_name in stock_seen
    if not event_present and outcome_files:
        raise StockRecoveryError("N1 stock transfer evidence has no started event")
    if event_present:
        validate_rollback_event(run_dir, prepared)
    if "rollback.stderr" in outcome_files and "rollback.stdout" not in outcome_files:
        raise StockRecoveryError("N1 stock transfer raw evidence is out of order")
    transfer_files = required_prefix | ({event_name} if event_present else set()) | outcome_files
    if "rollback-result.json" not in outcome_files:
        for name in sorted(outcome_files):
            root_data.read_exact_blob(
                run_dir / name,
                f"N1 partial stock transfer {name}",
                bootstrap.MAX_OUTPUT,
            )
        return "odin_effect_outcome_unproved_after_intent", transfer_files, False

    result = root_data.read_exact_json(
        run_dir / "rollback-result.json", "N1 rollback transfer result"
    )
    if result.get("schema") == "s20plus_g986n_f1_transfer_failure_v1":
        if outcome_files != {"rollback-result.json"}:
            raise StockRecoveryError("N1 stock failure result has unexpected raw evidence")
        validate_rollback_outcome(
            run_dir,
            prepared,
            "odin_device_session_failure_or_unknown",
        )
        return "odin_device_session_failure_or_unknown", transfer_files, True

    if outcome_files != STOCK_TRANSFER_FILES:
        raise StockRecoveryError("N1 stock transfer result lacks both raw streams")
    classification = result.get("classification") if isinstance(result, dict) else None
    if classification not in STOCK_TRANSFER_STATES - {
        "odin_effect_outcome_unproved_after_intent"
    }:
        raise StockRecoveryError("N1 stock transfer result classification is invalid")
    validate_rollback_outcome(run_dir, prepared, classification)
    return classification, transfer_files, True


def validate_stock_download_baseline(value: Any) -> dict[str, Any]:
    baseline = bootstrap.validate_download_baseline(value)
    if (
        not isinstance(baseline.get("listing_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", baseline["listing_sha256"]) is None
        or not isinstance(baseline.get("at"), str)
        or not baseline["at"]
    ):
        raise StockRecoveryError("N1 stock Download baseline is not exactly typed")
    try:
        observed_at = datetime.fromisoformat(baseline["at"])
    except ValueError as exc:
        raise StockRecoveryError("N1 stock Download baseline time is malformed") from exc
    if observed_at.tzinfo is None or observed_at.utcoffset() != timedelta(0):
        raise StockRecoveryError("N1 stock Download baseline time is not UTC")
    return baseline


def validate_stock_download_endpoint(value: Any, label: str) -> dict[str, Any]:
    endpoint = bootstrap.validate_download_endpoint_record(value, label)
    if not root_data.exact_typed_equal(
        endpoint.get("usb"),
        {**bootstrap.DOWNLOAD_USB, "serial_absent": True},
    ):
        raise StockRecoveryError(f"{label} USB profile is not exactly typed")
    return endpoint


def validate_arm_intent(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    arm = root_data.read_exact_json(run_dir / "stock-recovery-arm.json", "N1 stock arm")
    baseline = validate_stock_download_baseline(
        arm.get("baseline") if isinstance(arm, dict) else None
    )
    if not root_data.exact_typed_equal(arm, {
        "schema": "s20plus_g986n_native_canary_stock_recovery_arm_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "baseline": baseline,
        "baseline_sha256": root_data.canonical_sha(baseline),
        "operator_confirmed": True,
        "physical_action": "operator-physical-download-entry",
        "arrival_deadline": arm.get("arrival_deadline") if isinstance(arm, dict) else None,
        "confirmation_required": PHYSICAL_CONFIRM,
        "attempt": 1,
        "replay_permitted": False,
        "at": arm.get("at") if isinstance(arm, dict) else None,
    }) or type(arm.get("attempt")) is not int or not isinstance(arm.get("at"), str):
        raise StockRecoveryError("N1 stock-recovery arm intent is malformed or mismatched")
    try:
        baseline_at = datetime.fromisoformat(baseline["at"])
        armed_at = datetime.fromisoformat(arm["at"])
        deadline = datetime.fromisoformat(arm["arrival_deadline"])
    except (TypeError, ValueError) as exc:
        raise StockRecoveryError("N1 stock-recovery arm window is malformed") from exc
    if (
        armed_at.tzinfo is None
        or baseline_at.tzinfo is None
        or baseline_at.utcoffset() != timedelta(0)
        or deadline.tzinfo is None
        or armed_at.utcoffset() != timedelta(0)
        or deadline.utcoffset() != timedelta(0)
        or baseline_at > armed_at
        or deadline - armed_at != timedelta(seconds=ARM_ARRIVAL_WINDOW_SEC)
    ):
        raise StockRecoveryError("N1 stock-recovery arm arrival window is malformed")
    return arm


def validate_arm_arrival(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / "stock-recovery-arrival.json", "N1 stock Download arrival"
    )
    endpoint = validate_stock_download_endpoint(
        value.get("arrival_endpoint") if isinstance(value, dict) else None,
        "N1 stock arrived Download endpoint",
    )
    arrival = value.get("arrival") if isinstance(value, dict) else None
    if not root_data.exact_typed_equal(value, {
        "schema": "s20plus_g986n_native_canary_stock_recovery_arrival_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "arm_sha256": root_data.canonical_sha(arm),
        "arrival_endpoint": endpoint,
        "arrival": arrival,
        "physical_action_consumed": True,
        "replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }) or (
        not isinstance(value.get("at"), str)
        or not isinstance(arrival, dict)
        or set(arrival) != {
            "baseline_listing_sha256", "arrival_listing_sha256", "arrival_endpoint"
        }
        or arrival.get("baseline_listing_sha256") != arm["baseline"]["listing_sha256"]
        or not isinstance(arrival.get("arrival_listing_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", arrival.get("arrival_listing_sha256")) is None
        or arrival.get("arrival_listing_sha256") == arm["baseline"]["listing_sha256"]
        or arrival.get("arrival_endpoint") != endpoint["device"]
    ):
        raise StockRecoveryError("N1 stock Download arrival is malformed or mismatched")
    return value


def validate_arm(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    arm = validate_arm_intent(run_dir, prepared)
    return validate_arm_arrival(run_dir, prepared, arm)


def arm(
    run_dir: Path,
    confirmation: str,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    prepared = root_data.read_prepared(run_dir, input_scope="stock-recovery")
    root_data.read_guard(run_dir)
    read_handoff(run_dir, prepared)
    if confirmation != PHYSICAL_ARM:
        raise StockRecoveryError("N1 stock-recovery arm confirmation mismatch")
    arm_path = run_dir / "stock-recovery-arm.json"
    arrival_path = run_dir / "stock-recovery-arrival.json"
    if os.path.lexists(run_dir / "stock-recovery-baseline.json"):
        raise StockRecoveryError("N1 legacy baseline-only arm state is not resumable")
    if any(os.path.lexists(run_dir / name) for name in (
        "stock-recovery-confirmation.json",
        "rollback-intent.json", "rollback-result.json", "stock-recovery-result.json",
        "terminal-result.json",
    )):
        raise StockRecoveryError("N1 stock-recovery arm is duplicated or inconsistent")
    if os.path.lexists(arm_path):
        expected = set(STOCK_ARM_FILES)
        if not os.path.lexists(arrival_path):
            expected.remove("stock-recovery-arrival.json")
        validate_stock_journal(
            run_dir,
            prepared,
            expected,
            expected,
        )
        arm_record = validate_arm_intent(run_dir, prepared)
        if not os.path.lexists(arrival_path):
            # The durable intent means the physical action is consumed.  This
            # resume path only observes the current endpoint once.
            devices, listing_sha256 = bootstrap.enumerate_download(command)
            if len(devices) != 1:
                raise StockRecoveryError(
                    "N1 armed stock Download arrival is absent or ambiguous"
                )
            endpoint = bootstrap.identify_download(command)
            if endpoint["device"] != devices[0]:
                raise StockRecoveryError("N1 armed stock Download endpoint changed")
            arrival = {
                "baseline_listing_sha256": arm_record["baseline"]["listing_sha256"],
                "arrival_listing_sha256": listing_sha256,
                "arrival_endpoint": endpoint["device"],
            }
            root_data.read_guard(run_dir)
            root_data.durable_create(arrival_path, {
                "schema": "s20plus_g986n_native_canary_stock_recovery_arrival_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "arm_sha256": root_data.canonical_sha(arm_record),
                "arrival_endpoint": endpoint,
                "arrival": arrival,
                "physical_action_consumed": True,
                "replay_permitted": False,
                "at": root_data.utc_now(),
            })
        validate_arm(run_dir, prepared)
        return {
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_PHYSICAL_DOWNLOAD_CONFIRMATION",
            "confirmation_required": PHYSICAL_CONFIRM,
        }
    validate_stock_journal(
        run_dir,
        prepared,
        {"stock-recovery-handoff.json"},
        {"stock-recovery-handoff.json"},
    )
    baseline = validate_stock_download_baseline(bootstrap.download_baseline(command))
    root_data.read_guard(run_dir)
    armed_at = datetime.now(timezone.utc)
    arm_record = {
        "schema": "s20plus_g986n_native_canary_stock_recovery_arm_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "baseline": baseline,
        "baseline_sha256": root_data.canonical_sha(baseline),
        "operator_confirmed": True,
        "physical_action": "operator-physical-download-entry",
        "arrival_deadline": (
            armed_at + timedelta(seconds=ARM_ARRIVAL_WINDOW_SEC)
        ).isoformat(),
        "confirmation_required": PHYSICAL_CONFIRM,
        "attempt": 1,
        "replay_permitted": False,
        "at": armed_at.isoformat(),
    }
    root_data.durable_create(arm_path, arm_record)
    # Only after the intent is durable may the attended physical transition be
    # performed and observed.
    observed = bootstrap.wait_download_after_baseline(
        command,
        baseline,
        ARM_ARRIVAL_WINDOW_SEC,
    )
    if observed is None:
        raise StockRecoveryError("N1 stock Download arrival was not observed after baseline")
    endpoint, arrival = observed
    validate_stock_download_endpoint(endpoint, "N1 stock arrived endpoint")
    root_data.read_guard(run_dir)
    root_data.durable_create(arrival_path, {
        "schema": "s20plus_g986n_native_canary_stock_recovery_arrival_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "arm_sha256": root_data.canonical_sha(arm_record),
        "arrival_endpoint": endpoint,
        "arrival": arrival,
        "physical_action_consumed": True,
        "replay_permitted": False,
        "at": root_data.utc_now(),
    })
    return {
        "verdict": "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_PHYSICAL_DOWNLOAD_CONFIRMATION",
        "confirmation_required": PHYSICAL_CONFIRM,
    }


def validate_confirmation(
    run_dir: Path,
    prepared: dict[str, Any],
    endpoint: dict[str, Any],
) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / "stock-recovery-confirmation.json", "N1 stock confirmation"
    )
    if not root_data.exact_typed_equal(value, {
        "schema": "s20plus_g986n_native_canary_stock_recovery_confirmation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "endpoint": endpoint,
        "operator_confirmed": True,
        "confirmation": PHYSICAL_CONFIRM,
        "attempt": 1,
        "replay_permitted": False,
        "at": value.get("at") if isinstance(value, dict) else None,
    }) or type(value.get("attempt")) is not int or not isinstance(value.get("at"), str):
        raise StockRecoveryError("N1 stock confirmation is malformed or mismatched")
    validate_stock_download_endpoint(endpoint, "N1 stock endpoint")
    return value


def pending_result(
    run_dir: Path,
    prepared: dict[str, Any],
    verdict: str,
    classification: str,
    final_health: dict[str, Any] | None,
) -> dict[str, Any]:
    result = {
        "schema": "s20plus_g986n_native_canary_stock_recovery_result_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "stock_transfer": classification,
        "final_health": final_health,
        "install_replay_permitted": False,
        "stock_recovery_replay_permitted": False,
    }
    root_data.durable_create(run_dir / "stock-recovery-result.json", result)
    return result


def normalize_pending_final_health(final: Any) -> Any:
    """Name the exact same-boot stock observation instead of overclaiming reset need."""
    if (
        isinstance(final, dict)
        and set(final) == {
            "healthy", "root_absent", "boot_changed", "boot_id_sha256",
            "confirmed_boot_id_sha256", "root_probe_rc", "root_probe_sha256",
            "target",
        }
        and final.get("healthy") is False
        and final.get("root_absent") is True
        and final.get("boot_changed") is False
        and type(final.get("root_probe_rc")) is int
        and final.get("root_probe_rc") == 127
        and all(
            isinstance(final.get(key), str)
            and re.fullmatch(r"[0-9a-f]{64}", final.get(key)) is not None
            for key in (
                "boot_id_sha256", "confirmed_boot_id_sha256", "root_probe_sha256"
            )
        )
        and final.get("boot_id_sha256") == final.get("confirmed_boot_id_sha256")
        and root_data.exact_typed_equal(final.get("target"), {
            "model": bootstrap.EXPECTED_MODEL,
            "device": bootstrap.EXPECTED_DEVICE,
            "product": bootstrap.EXPECTED_PRODUCT,
            "incremental": bootstrap.EXPECTED_INCREMENTAL,
        })
    ):
        return {**final, "reason": "boot-identity-not-changed"}
    return final


def pending_verdict(final: Any, classification: str = "odin_transfer_completed") -> str:
    if classification not in STOCK_TRANSFER_STATES:
        raise StockRecoveryError("N1 pending stock transfer state is invalid")
    if classification != "odin_transfer_completed":
        return "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_TRANSFER_UNCERTAIN"
    if (
        isinstance(final, dict)
        and final.get("reason") == "boot-identity-not-changed"
    ):
        return "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_BOOT_IDENTITY_UNCHANGED"
    return "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_FACTORY_RESET_REQUIRED"


def validate_healthy_final(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {
            "healthy", "root_absent", "boot_changed", "boot_id_sha256",
            "confirmed_boot_id_sha256", "root_probe_rc", "root_probe_sha256",
            "target",
        }
        or value.get("healthy") is not True
        or value.get("root_absent") is not True
        or value.get("boot_changed") is not True
        or type(value.get("root_probe_rc")) is not int
        or value.get("root_probe_rc") != 127
        or any(
            not isinstance(value.get(key), str)
            or re.fullmatch(r"[0-9a-f]{64}", value.get(key)) is None
            for key in (
                "boot_id_sha256", "confirmed_boot_id_sha256", "root_probe_sha256"
            )
        )
        or value.get("boot_id_sha256") != value.get("confirmed_boot_id_sha256")
        or value.get("target") != {
            "model": bootstrap.EXPECTED_MODEL,
            "device": bootstrap.EXPECTED_DEVICE,
            "product": bootstrap.EXPECTED_PRODUCT,
            "incremental": bootstrap.EXPECTED_INCREMENTAL,
        }
    ):
        raise StockRecoveryError("N1 stock final-health observation is malformed")
    return value


def validate_root_absence_record(absence: Any) -> dict[str, Any]:
    if (
        not isinstance(absence, dict)
        or set(absence) != {
            "returncode", "stdout_bytes", "stderr_bytes", "stdout_sha256",
            "stderr_sha256", "stdout_hex", "stderr_hex", "normalized_sha256",
            "root_absent", "identity_confirmed",
        }
        or type(absence.get("returncode")) is not int
        or absence.get("returncode") != 127
        or type(absence.get("stdout_bytes")) is not int
        or type(absence.get("stderr_bytes")) is not int
        or absence.get("stdout_bytes", -1) < 0
        or absence.get("stderr_bytes", -1) < 0
        or absence.get("stdout_bytes", 0) + absence.get("stderr_bytes", 0)
        > 64 * 1024
        or not isinstance(absence.get("stdout_hex"), str)
        or not isinstance(absence.get("stderr_hex"), str)
        or re.fullmatch(r"(?:[0-9a-f]{2})*", absence.get("stdout_hex", "")) is None
        or re.fullmatch(r"(?:[0-9a-f]{2})*", absence.get("stderr_hex", "")) is None
        or absence.get("root_absent") is not True
        or absence.get("identity_confirmed") is not True
        or any(
            not isinstance(absence.get(key), str)
            or re.fullmatch(r"[0-9a-f]{64}", absence.get(key)) is None
            for key in ("stdout_sha256", "stderr_sha256", "normalized_sha256")
        )
    ):
        raise StockRecoveryError("N1 stock root-absence record is malformed")
    stdout = bytes.fromhex(absence["stdout_hex"])
    stderr = bytes.fromhex(absence["stderr_hex"])
    normalized = exact_root_absence_text(stdout, stderr)
    if (
        len(stdout) != absence["stdout_bytes"]
        or len(stderr) != absence["stderr_bytes"]
        or hashlib.sha256(stdout).hexdigest() != absence["stdout_sha256"]
        or hashlib.sha256(stderr).hexdigest() != absence["stderr_sha256"]
        or hashlib.sha256(normalized.encode()).hexdigest()
        != absence["normalized_sha256"]
    ):
        raise StockRecoveryError("N1 stock root-absence transcript is not exact")
    return absence


def validate_stock_health_evidence(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / STOCK_HEALTH_FILE, "N1 durable stock final health"
    )
    identity = value.get("android_identity") if isinstance(value, dict) else None
    absence = value.get("root_absence") if isinstance(value, dict) else None
    final = value.get("final_health") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "final_health",
            "android_identity", "root_absence", "at",
        }
        or value.get("schema")
        != "s20plus_g986n_native_canary_stock_final_health_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or not isinstance(value.get("at"), str)
        or not isinstance(identity, dict)
        or not isinstance(absence, dict)
        or set(absence) != {
            "returncode", "stdout_bytes", "stderr_bytes", "stdout_sha256",
            "stderr_sha256", "stdout_hex", "stderr_hex", "normalized_sha256",
            "root_absent", "identity_confirmed",
        }
        or type(absence.get("returncode")) is not int
        or absence.get("returncode") != 127
        or type(absence.get("stdout_bytes")) is not int
        or type(absence.get("stderr_bytes")) is not int
        or absence.get("stdout_bytes", -1) < 0
        or absence.get("stderr_bytes", -1) < 0
        or absence.get("stdout_bytes", 0) + absence.get("stderr_bytes", 0)
        > 64 * 1024
        or not isinstance(absence.get("stdout_hex"), str)
        or not isinstance(absence.get("stderr_hex"), str)
        or re.fullmatch(r"(?:[0-9a-f]{2})*", absence.get("stdout_hex", "")) is None
        or re.fullmatch(r"(?:[0-9a-f]{2})*", absence.get("stderr_hex", "")) is None
        or absence.get("root_absent") is not True
        or absence.get("identity_confirmed") is not True
        or any(
            not isinstance(absence.get(key), str)
            or re.fullmatch(r"[0-9a-f]{64}", absence.get(key)) is None
            for key in ("stdout_sha256", "stderr_sha256", "normalized_sha256")
        )
    ):
        raise StockRecoveryError("N1 durable stock final health is malformed")
    validate_root_absence_record(absence)
    root_data.require_returned_target(prepared, identity, "N1 stock recovery target")
    if identity["boot_id_sha256"] in root_data.known_boot_ids_before_observation(
        run_dir,
        prepared,
        "stock",
    ):
        raise StockRecoveryError("N1 stock final health reuses an earlier boot identity")
    healthy = validate_healthy_final(final)
    if (
        identity["boot_id_sha256"] != healthy["boot_id_sha256"]
        or identity["boot_id_sha256"]
        == prepared["binding"]["target"]["boot_id_sha256"]
        or healthy["root_probe_rc"] != absence["returncode"]
        or healthy["root_probe_sha256"] != absence["normalized_sha256"]
    ):
        raise StockRecoveryError("N1 stock final-health identity is mismatched")
    return value


def exact_root_absence_evidence(
    command: Command,
    adb: str,
    selected: dict[str, Any],
    expected_identity: dict[str, str],
) -> dict[str, Any]:
    rc, stdout, stderr = command(
        [adb, "-s", selected["serial"], "shell", "su", "-c", "id"],
        20,
        64 * 1024,
    )
    if (
        type(rc) is not int
        or not isinstance(stdout, bytes)
        or not isinstance(stderr, bytes)
        or len(stdout) + len(stderr) > 64 * 1024
    ):
        raise StockRecoveryError("N1 stock root-absence receipt is malformed")
    if rc != 127:
        raise StockRecoveryError("N1 stock root absence is not exact")
    normalized = exact_root_absence_text(stdout, stderr)
    _selected, _values, confirmed_identity = bootstrap.android_health_once(command, adb)
    if confirmed_identity != expected_identity:
        raise StockRecoveryError("N1 stock identity changed during root-absence proof")
    return {
        "returncode": rc,
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_hex": stdout.hex(),
        "stderr_hex": stderr.hex(),
        "normalized_sha256": hashlib.sha256(normalized.encode()).hexdigest(),
        "root_absent": True,
        "identity_confirmed": True,
    }


def finish_healthy(
    run_dir: Path,
    prepared: dict[str, Any],
    command: Command,
    final: dict[str, Any],
    stock_transfer_state: str,
) -> dict[str, Any]:
    if stock_transfer_state not in STOCK_TRANSFER_STATES:
        raise StockRecoveryError("N1 stock transfer state is invalid")
    semantics = root_data.stock_terminal_semantics(stock_transfer_state)
    health_path = run_dir / STOCK_HEALTH_FILE
    if os.path.lexists(health_path):
        evidence = validate_stock_health_evidence(run_dir, prepared)
        identity = evidence["android_identity"]
    else:
        healthy = validate_healthy_final(final)
        adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
        selected, _values, identity = bootstrap.android_health_once(command, adb)
        root_data.require_returned_target(prepared, identity, "N1 stock recovery target")
        if identity["boot_id_sha256"] in root_data.known_boot_ids_before_observation(
            run_dir,
            prepared,
            "stock",
        ):
            raise StockRecoveryError(
                "N1 stock final health reuses an earlier boot identity"
            )
        absence = exact_root_absence_evidence(command, adb, selected, identity)
        if identity["boot_id_sha256"] != healthy["boot_id_sha256"]:
            raise StockRecoveryError("N1 stock final-health boot identity changed")
        healthy = {
            **healthy,
            "root_probe_rc": absence["returncode"],
            "root_probe_sha256": absence["normalized_sha256"],
        }
        root_data.durable_create(health_path, {
            "schema": "s20plus_g986n_native_canary_stock_final_health_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "final_health": healthy,
            "android_identity": identity,
            "root_absence": absence,
            "at": root_data.utc_now(),
        })
        evidence = validate_stock_health_evidence(run_dir, prepared)
    # A durable pre-terminal health receipt is resumable evidence, not a
    # standing health lease.  Re-read the exact target and root absence before
    # every terminal publication attempt; cleanup itself remains no-replay.
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    selected, _values, current_identity = bootstrap.android_health_once(command, adb)
    root_data.require_returned_target(prepared, current_identity, "N1 stock terminal target")
    if current_identity != identity:
        raise StockRecoveryError("N1 stock identity changed before terminal publication")
    terminal_absence = exact_root_absence_evidence(
        command,
        adb,
        selected,
        current_identity,
    )
    health_sha256 = hashlib.sha256(
        root_data.read_exact_blob(
            health_path,
            "N1 durable stock final health",
            1024 * 1024,
        )
    ).hexdigest()
    root_data.write_stock_terminal_input(
        run_dir,
        prepared,
        semantics["verdict"],
        current_identity,
        stock_transfer_state=stock_transfer_state,
        stock_final_health_sha256=health_sha256,
        stock_root_absence_sha256=root_data.canonical_sha(terminal_absence),
    )
    root_data.settle_cleanup_without_replay(
        run_dir,
        prepared,
        selected,
        command,
    )
    staged_absence = root_data.stage_absence_evidence(command, adb, selected)
    selected, _values, post_cleanup_identity = bootstrap.android_health_once(command, adb)
    root_data.require_returned_target(
        prepared,
        post_cleanup_identity,
        "N1 stock post-cleanup terminal target",
    )
    if post_cleanup_identity != current_identity:
        raise StockRecoveryError("N1 stock identity changed after staged-input cleanup")
    post_cleanup_absence = exact_root_absence_evidence(
        command,
        adb,
        selected,
        post_cleanup_identity,
    )
    return root_data.write_terminal(
        run_dir,
        prepared,
        semantics["verdict"],
        post_cleanup_identity,
        None,
        recovery=semantics["recovery"],
        canary_state_class=semantics["canary_state_class"],
        stock_final_health_sha256=health_sha256,
        stock_transfer_state=stock_transfer_state,
        stock_precleanup_root_absence_sha256=root_data.canonical_sha(terminal_absence),
        stock_root_absent=evidence["root_absence"]["root_absent"],
        stock_terminal_root_absence=post_cleanup_absence,
        staged_input_absence=staged_absence,
    )


def transfer_stock_once(
    run_dir: Path,
    endpoint: dict[str, Any],
    binding_sha256: str,
) -> str:
    """Send the fixed stock boot once with R1 atomic no-clobber evidence."""
    intent = {
        "schema": "s20plus_g986n_f1_transfer_intent_v1",
        "version": bootstrap.VERSION,
        "kind": "rollback",
        "binding_sha256": binding_sha256,
        "ap_sha256": bootstrap.ROLLBACK_SHA256,
        "endpoint": {
            "device": endpoint["device"],
            "identity": endpoint["endpoint_identity"],
        },
        "attempt": 1,
        "no_replay": True,
        "at": root_data.utc_now(),
    }
    root_data.durable_create(run_dir / "rollback-intent.json", intent)
    root_data.durable_create(
        run_dir / "events/90-rollback-transfer-started.json",
        {
            "schema": "s20plus_g986n_f1_event_v1",
            "version": bootstrap.VERSION,
            "ordinal": 90,
            "name": "rollback-transfer-started",
            "at": root_data.utc_now(),
            "ap_sha256": bootstrap.ROLLBACK_SHA256,
        },
    )
    try:
        receipt, stdout, stderr = bootstrap.execute_odin_exact(
            bootstrap.ROLLBACK,
            bootstrap.ROLLBACK_SIZE,
            bootstrap.ROLLBACK_SHA256,
            "rollback",
            endpoint,
        )
    except Exception as exc:
        root_data.durable_create(
            run_dir / "rollback-result.json",
            {
                "schema": "s20plus_g986n_f1_transfer_failure_v1",
                "kind": "rollback",
                "classification": "odin_device_session_failure_or_unknown",
                "error_class": type(exc).__name__,
                "possible_partition_effect": True,
            },
        )
        return "odin_device_session_failure_or_unknown"
    root_data.durable_blob(run_dir / "rollback.stdout", stdout)
    root_data.durable_blob(run_dir / "rollback.stderr", stderr)
    classification = bootstrap.persisted_transfer_classification(
        receipt,
        stdout,
        stderr,
    )
    root_data.durable_create(
        run_dir / "rollback-result.json",
        {
            "schema": "s20plus_g986n_f1_transfer_v1",
            "version": bootstrap.VERSION,
            "kind": "rollback",
            "binding_sha256": binding_sha256,
            "endpoint": intent["endpoint"],
            "classification": classification,
            "receipt": receipt,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        },
    )
    return classification


def confirm(
    run_dir: Path,
    confirmation: str,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    prepared = root_data.read_prepared(run_dir, input_scope="stock-recovery")
    root_data.read_guard(run_dir)
    read_handoff(run_dir, prepared)
    if confirmation != PHYSICAL_CONFIRM:
        raise StockRecoveryError("N1 stock-recovery confirmation mismatch")
    arm_record = validate_arm(run_dir, prepared)
    if any(os.path.lexists(run_dir / name) for name in (
        "rollback-intent.json", "rollback-result.json", "stock-recovery-result.json",
        "terminal-result.json",
    )):
        raise StockRecoveryError("N1 stock recovery already attempted; replay forbidden")
    confirmation_path = run_dir / "stock-recovery-confirmation.json"
    confirmation_present = os.path.lexists(confirmation_path)
    allowed = STOCK_ARM_FILES | (
        {"stock-recovery-confirmation.json"} if confirmation_present else set()
    )
    validate_stock_journal(run_dir, prepared, allowed, allowed)
    endpoint = bootstrap.identify_download(command)
    if not root_data.exact_typed_equal(endpoint, arm_record["arrival_endpoint"]):
        raise StockRecoveryError("N1 stock Download endpoint is not the armed arrival session")
    if not confirmation_present:
        root_data.durable_create(confirmation_path, {
            "schema": "s20plus_g986n_native_canary_stock_recovery_confirmation_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "endpoint": endpoint,
            "operator_confirmed": True,
            "confirmation": PHYSICAL_CONFIRM,
            "attempt": 1,
            "replay_permitted": False,
            "at": root_data.utc_now(),
        })
    validate_confirmation(run_dir, prepared, endpoint)
    root_data.read_guard(run_dir)
    validate_stock_journal(
        run_dir,
        prepared,
        STOCK_ARM_FILES | {"stock-recovery-confirmation.json"},
        STOCK_ARM_FILES | {"stock-recovery-confirmation.json"},
    )
    classification = transfer_stock_once(run_dir, endpoint, prepared["binding_sha256"])
    outcome = validate_rollback_outcome(run_dir, prepared, classification)
    if classification == "odin_transfer_completed":
        validate_stock_journal(
            run_dir,
            prepared,
            STOCK_COMPLETION_FILES,
            STOCK_COMPLETION_FILES,
        )
    else:
        outcome_files = (
            STOCK_DISPATCH_FILES | {"rollback-result.json"}
            if outcome.get("schema") == "s20plus_g986n_f1_transfer_failure_v1"
            else STOCK_COMPLETION_FILES
        )
        validate_stock_journal(run_dir, prepared, outcome_files, outcome_files)
        return pending_result(
            run_dir,
            prepared,
            "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_TRANSFER_UNCERTAIN",
            classification,
            None,
        )
    adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
    final = bootstrap.final_stock_health(
        command,
        adb,
        prepared["binding"]["target"]["boot_id_sha256"],
    )
    if final.get("healthy") is True:
        return finish_healthy(run_dir, prepared, command, final, classification)
    normalized_final = normalize_pending_final_health(final)
    return pending_result(
        run_dir,
        prepared,
        pending_verdict(normalized_final),
        classification,
        normalized_final,
    )


def validate_pending(
    run_dir: Path,
    prepared: dict[str, Any],
    expected_transfer: str | None = None,
) -> dict[str, Any]:
    value = root_data.read_exact_json(
        run_dir / "stock-recovery-result.json", "N1 pending stock result"
    )
    final_health = value.get("final_health") if isinstance(value, dict) else None
    simple_reasons = {
        "android-not-returned",
        "root-absence-output-oversized",
        "root-absence-output-malformed",
    }
    uncertain_reasons = {
        "post-root-probe-identity-uncertain",
        "post-root-probe-identity-drift",
    }
    root_reasons = {"root-still-present", "root-absence-observer-uncertain"}
    same_boot_exact = (
        isinstance(final_health, dict)
        and set(final_health) == {
            "healthy", "root_absent", "boot_changed", "boot_id_sha256",
            "confirmed_boot_id_sha256", "root_probe_rc", "root_probe_sha256",
            "target", "reason",
        }
        and final_health.get("healthy") is False
        and final_health.get("root_absent") is True
        and final_health.get("boot_changed") is False
        and final_health.get("reason") == "boot-identity-not-changed"
        and type(final_health.get("root_probe_rc")) is int
        and final_health.get("root_probe_rc") == 127
        and all(
            isinstance(final_health.get(key), str)
            and re.fullmatch(r"[0-9a-f]{64}", final_health.get(key)) is not None
            for key in (
                "boot_id_sha256", "confirmed_boot_id_sha256", "root_probe_sha256"
            )
        )
        and final_health.get("boot_id_sha256")
        == final_health.get("confirmed_boot_id_sha256")
        and root_data.exact_typed_equal(final_health.get("target"), {
            "model": bootstrap.EXPECTED_MODEL,
            "device": bootstrap.EXPECTED_DEVICE,
            "product": bootstrap.EXPECTED_PRODUCT,
            "incremental": bootstrap.EXPECTED_INCREMENTAL,
        })
    )
    final_health_exact = (
        final_health is None
        or isinstance(final_health, dict)
        and final_health.get("healthy") is False
        and (
            (set(final_health) == {"healthy", "reason"} and final_health.get("reason") in simple_reasons)
            or (
                set(final_health) == {"healthy", "root_absent", "reason"}
                and final_health.get("reason") in uncertain_reasons
                and final_health.get("root_absent") is None
            )
            or (
                set(final_health) == {
                    "healthy", "root_absent", "reason", "root_probe_rc", "root_probe_sha256"
                }
                and final_health.get("reason") in root_reasons
                and (
                    final_health.get("root_absent") is False
                    or final_health.get("root_absent") is None
                )
                and isinstance(final_health.get("root_probe_rc"), int)
                and not isinstance(final_health.get("root_probe_rc"), bool)
                and isinstance(final_health.get("root_probe_sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", final_health.get("root_probe_sha256")) is not None
            )
            or same_boot_exact
        )
    )
    stock_transfer = value.get("stock_transfer") if isinstance(value, dict) else None
    expected_verdict = pending_verdict(final_health, stock_transfer) \
        if stock_transfer in STOCK_TRANSFER_STATES else None
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "verdict", "stock_transfer",
            "final_health", "install_replay_permitted", "stock_recovery_replay_permitted",
        }
        or value.get("schema") != "s20plus_g986n_native_canary_stock_recovery_result_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("verdict") != expected_verdict
        or stock_transfer not in STOCK_TRANSFER_STATES
        or (expected_transfer is not None and stock_transfer != expected_transfer)
        or (stock_transfer == "odin_transfer_completed" and final_health is None)
        or not final_health_exact
        or value.get("install_replay_permitted") is not False
        or value.get("stock_recovery_replay_permitted") is not False
    ):
        raise StockRecoveryError("N1 pending stock result is malformed or ineligible")
    return value


def finalize_stock(
    run_dir: Path,
    command: Command = bootstrap.bounded_command,
) -> dict[str, Any]:
    require_active()
    terminal_present = os.path.lexists(run_dir / "terminal-result.json")
    prepared = root_data.read_prepared(
        run_dir,
        input_scope="stock-terminal-release" if terminal_present else "stock-finalize",
        allow_released_terminal=terminal_present,
    )
    read_handoff(run_dir, prepared)
    transfer_classification, transfer_files, _transfer_complete = (
        validate_stock_transfer_state(run_dir, prepared)
    )
    pending_present = os.path.lexists(run_dir / STOCK_PENDING_FILE)
    health_present = os.path.lexists(run_dir / STOCK_HEALTH_FILE)
    terminal_input_present = os.path.lexists(run_dir / "terminal-input.json")
    allowed = set(transfer_files)
    if pending_present:
        validate_pending(run_dir, prepared, transfer_classification)
        allowed.add(STOCK_PENDING_FILE)
    if health_present:
        validate_stock_health_evidence(run_dir, prepared)
        allowed.add(STOCK_HEALTH_FILE)
    if terminal_input_present:
        root_data.read_stock_terminal_input(run_dir, prepared)
        allowed.add("terminal-input.json")
    if terminal_present:
        allowed.add("terminal-result.json")
    validate_stock_journal(
        run_dir,
        prepared,
        allowed,
        allowed,
    )
    if terminal_present:
        if not health_present:
            raise StockRecoveryError("N1 stock terminal has no durable health evidence")
        evidence = validate_stock_health_evidence(run_dir, prepared)
        terminal_input = root_data.read_stock_terminal_input(run_dir, prepared)
        if terminal_input["stock_transfer_state"] != transfer_classification:
            raise StockRecoveryError(
                "N1 stock terminal transfer state contradicts the durable Odin journal"
            )
        terminal = root_data.read_exact_json(
            run_dir / "terminal-result.json", "N1 stock terminal result"
        )
        if (
            not isinstance(terminal, dict)
            or not root_data.exact_typed_equal(
                terminal_input.get("target_identity"),
                evidence["android_identity"],
            )
            or not root_data.exact_typed_equal(
                terminal.get("target_identity"),
                evidence["android_identity"],
            )
        ):
            raise StockRecoveryError(
                "N1 stock terminal target differs from durable final health"
            )
        terminal_absence = validate_root_absence_record(
            terminal.get("stock_terminal_root_absence")
            if isinstance(terminal, dict) else None
        )
        semantics = root_data.stock_terminal_semantics(
            terminal_input["stock_transfer_state"]
        )
        return root_data.write_terminal(
            run_dir,
            prepared,
            semantics["verdict"],
            terminal.get("target_identity"),
            None,
            recovery=semantics["recovery"],
            canary_state_class=semantics["canary_state_class"],
            stock_final_health_sha256=hashlib.sha256(
                root_data.read_exact_blob(
                    run_dir / STOCK_HEALTH_FILE,
                    "N1 durable stock final health",
                    1024 * 1024,
                )
            ).hexdigest(),
            stock_transfer_state=terminal_input["stock_transfer_state"],
            stock_precleanup_root_absence_sha256=terminal_input[
                "stock_root_absence_sha256"
            ],
            stock_root_absent=evidence["root_absence"]["root_absent"],
            stock_terminal_root_absence=terminal_absence,
            staged_input_absence=terminal.get("staged_input_absence_evidence"),
        )
    if health_present:
        final = validate_stock_health_evidence(run_dir, prepared)["final_health"]
    else:
        adb = prepared["binding"]["closure"]["bootstrap"]["adb"]["path"]
        final = bootstrap.final_stock_health(
            command,
            adb,
            prepared["binding"]["target"]["boot_id_sha256"],
        )
        if final.get("healthy") is not True:
            if not pending_present:
                normalized_final = normalize_pending_final_health(final)
                verdict = (
                    "RECOVERY_PENDING_S20PLUS_G986N_NATIVE_CANARY_STOCK_TRANSFER_UNCERTAIN"
                    if transfer_classification != "odin_transfer_completed"
                    else pending_verdict(normalized_final)
                )
                return pending_result(
                    run_dir,
                    prepared,
                    verdict,
                    transfer_classification,
                    normalized_final,
                )
            raise StockRecoveryError("N1 stock Android is not yet healthy")
    return finish_healthy(
        run_dir,
        prepared,
        command,
        final,
        transfer_classification,
    )


def render_plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_native_canary_stock_recovery_plan_v1",
        "version": VERSION,
        "active": NATIVE_CANARY_STOCK_RECOVERY_ACTIVE,
        "owner": root_data.VERSION,
        "target": f"{bootstrap.EXPECTED_MODEL}/{bootstrap.EXPECTED_DEVICE}/{bootstrap.EXPECTED_INCREMENTAL}",
        "artifact": {
            "path": str(bootstrap.ROLLBACK),
            "size": bootstrap.ROLLBACK_SIZE,
            "sha256": bootstrap.ROLLBACK_SHA256,
        },
        "attempts": 1,
        "candidate_path": False,
        "partition_payload": "boot-only-stock-recovery",
        "live_authority": NATIVE_CANARY_STOCK_RECOVERY_ACTIVE,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    parser.add_argument("--arm", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--finalize-stock", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--confirmation")
    args = parser.parse_args()
    if sum((args.render_plan, args.arm, args.confirm, args.finalize_stock)) != 1:
        parser.error("choose exactly one N1 stock-recovery mode")
    if args.render_plan:
        if args.run_id is not None or args.confirmation is not None:
            parser.error("--render-plan accepts no run or confirmation input")
        print(json.dumps(render_plan(), sort_keys=True))
        return 0
    require_active()
    if args.run_id is None:
        parser.error("--run-id is required")
    run_dir = root_data.resolve_run_id(args.run_id)
    if args.arm:
        if args.confirmation is None:
            parser.error("--confirmation is required")
        result = arm(run_dir, args.confirmation)
    elif args.confirm:
        if args.confirmation is None:
            parser.error("--confirmation is required")
        result = confirm(run_dir, args.confirmation)
    else:
        if args.confirmation is not None:
            parser.error("--finalize-stock accepts only --run-id")
        result = finalize_stock(run_dir)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
