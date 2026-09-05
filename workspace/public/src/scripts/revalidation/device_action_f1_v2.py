#!/usr/bin/env python3
"""Host-only core for reusable boot-only Device Action Process v2.

The CLI validates profiles, manifests, and regular-path artifacts, renders the
future live plan, and simulates durable state transitions. It has no connected
or live mode and never invokes ADB, USB, or Odin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import device_action_f1_evidence_v2 as typed_evidence
import device_action_cdc_acm_observer_v1 as cdc_acm_observer
import s22plus_fyg8_p286_candidate_intent as candidate_intent
from s22plus_boot_only_f1_transport import (
    BOOT_MEMBER,
    F1TransportError,
    pin_boot_only_ap,
    pin_regular_file,
    read_boot_only_member,
)


RUNNER_VERSION = "device-action-f1-v2-host-core-3"
PROFILE_SCHEMA = "device_action_target_profile_v2"
MANIFEST_SCHEMA = "device_action_f1_candidate_v2"
TARGET_EVIDENCE_SCHEMA = "device_action_target_evidence_v2"
JOURNAL_SCHEMA = "device_action_f1_journal_record_v2"
JOURNAL_HEAD_SCHEMA = "device_action_f1_journal_head_v2"
RESULT_SCHEMA = "device_action_f1_result_v2"
DEFAULT_MANIFEST = Path(
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_r4w1c_process_v2_draft.json"
)
DEFAULT_RUN_ROOT = Path("workspace/private/runs/device-action-f1-v2")
HASH_RE = re.compile(r"[0-9a-f]{64}")
ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,95}")
MAX_JSON = 1024 * 1024
P317_OVERLAY_INTENT_MAX_BYTES = 2 * 1024 * 1024
MAX_RECORD = 32 * 1024
MAX_RESULT_RECORD = 64 * 1024

STATES = (
    "PREFLIGHT",
    "APPROVED",
    "DOWNLOAD_IDENTIFIED",
    "CANDIDATE_FLASHED",
    "OBSERVED",
    "RECOVERY_DOWNLOAD",
    "ROLLBACK_FLASHED",
    "HEALTH_VERIFIED",
    "CLOSED",
    "ABORTED",
)
NEXT_STATES: dict[str | None, set[str]] = {
    None: {"PREFLIGHT"},
    "PREFLIGHT": {"APPROVED", "ABORTED"},
    # A durable Download-request cut may enter recovery without first
    # fabricating a candidate endpoint/claim/attempt.  The live adapter uses
    # this direct recovery edge only for its passive recovery-only branch;
    # ordinary candidate execution still follows the existing path below.
    "APPROVED": {"DOWNLOAD_IDENTIFIED", "RECOVERY_DOWNLOAD", "ABORTED"},
    "DOWNLOAD_IDENTIFIED": {"CANDIDATE_FLASHED", "RECOVERY_DOWNLOAD", "ABORTED"},
    "CANDIDATE_FLASHED": {"OBSERVED", "ABORTED"},
    "OBSERVED": {"RECOVERY_DOWNLOAD", "ABORTED"},
    "RECOVERY_DOWNLOAD": {"ROLLBACK_FLASHED", "ABORTED"},
    "ROLLBACK_FLASHED": {"HEALTH_VERIFIED", "ABORTED"},
    "HEALTH_VERIFIED": {"CLOSED", "ABORTED"},
    "CLOSED": set(),
    "ABORTED": set(),
}
STATE_ACTION = {
    "PREFLIGHT": "preflight_validated",
    "APPROVED": "approval_bound",
    "DOWNLOAD_IDENTIFIED": "download_identified",
    "CANDIDATE_FLASHED": "candidate_flashed",
    "OBSERVED": "candidate_observed",
    "RECOVERY_DOWNLOAD": "recovery_download_identified",
    "ROLLBACK_FLASHED": "rollback_flashed",
    "HEALTH_VERIFIED": "final_health_verified",
    "CLOSED": "run_closed",
    "ABORTED": "run_aborted",
}
TIMELINE = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
# A request-cut recovery has no candidate event to report.  It still retains
# the session-start event from the approved journal, then follows a separate
# rollback-only suffix.  Keeping the prefix explicit lets the journal reopen
# without fabricating a candidate event or transfer attempt.
RECOVERY_TIMELINE = (
    "live_session_start",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
RECOVERY_EVENT_STATES = {
    "RECOVERY_DOWNLOAD",
    "ROLLBACK_FLASHED",
    "HEALTH_VERIFIED",
}
EVENT_STATE = {
    "live_session_start": "PREFLIGHT",
    "candidate_flash_start": "DOWNLOAD_IDENTIFIED",
    "candidate_flash_done": "CANDIDATE_FLASHED",
    "candidate_boot_ready": "OBSERVED",
    "rollback_flash_start": "RECOVERY_DOWNLOAD",
    "rollback_flash_done": "ROLLBACK_FLASHED",
    "rollback_boot_ready": "HEALTH_VERIFIED",
    "live_session_end": "HEALTH_VERIFIED",
}
CHECKPOINT_STATE = {
    "candidate_transfer_attempt": "DOWNLOAD_IDENTIFIED",
    "rollback_transfer_attempt": "RECOVERY_DOWNLOAD",
    "download_request_revalidation": "RECOVERY_DOWNLOAD",
}
MAX_TRANSFER_ATTEMPTS = 2


class F1V2Error(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise F1V2Error("value is not canonical JSON") from exc


def json_sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _stable_read(path: Path, label: str, maximum: int = MAX_JSON) -> tuple[bytes, dict[str, Any]]:
    direct = path.absolute()
    if str(direct).startswith("/proc/"):
        raise F1V2Error(f"{label} cannot use /proc")
    try:
        entry = os.lstat(direct)
    except OSError as exc:
        raise F1V2Error(f"{label} is unavailable: {direct}") from exc
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode):
        raise F1V2Error(f"{label} is not a direct regular file")
    if direct.resolve(strict=True) != direct:
        raise F1V2Error(f"{label} has an indirect path component")
    descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        payload = bytearray()
        while chunk := os.read(descriptor, 1024 * 1024):
            payload.extend(chunk)
            if len(payload) > maximum:
                raise F1V2Error(f"{label} exceeds its size bound")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(direct)
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise F1V2Error(f"{label} changed while reading")
    data = bytes(payload)
    return data, {
        "path": str(direct),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _execution_source_maximum(
    name: str, userspace_overlay_contract_id: str | None
) -> int:
    if (
        name == "p317_overlay_intent"
        and userspace_overlay_contract_id
        == typed_evidence.P317_MAX77705_OVERLAY_CONTRACT_ID
    ):
        return P317_OVERLAY_INTENT_MAX_BYTES
    return MAX_JSON


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise F1V2Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, receipt = _stable_read(path, label)
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise F1V2Error(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise F1V2Error(f"{label} must be an object")
    return value, receipt


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise F1V2Error(f"{label} keys do not match the v2 schema")
    return value


def _text(value: Any, label: str, maximum: int = 1024) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        raise F1V2Error(f"{label} must be a bounded string")
    return value


def _digest(value: Any, label: str) -> str:
    text = _text(value, label, 64)
    if HASH_RE.fullmatch(text) is None:
        raise F1V2Error(f"{label} is not a lowercase SHA256")
    return text


def _artifact(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"path", "size", "sha256"}, label)
    _text(item["path"], f"{label}.path")
    if isinstance(item["size"], bool) or not isinstance(item["size"], int) or not 1 <= item["size"] <= 2**40:
        raise F1V2Error(f"{label}.size is invalid")
    _digest(item["sha256"], f"{label}.sha256")
    return item


def _health(value: Any, label: str) -> None:
    item = _exact(
        value,
        {
            "android_boot_completed",
            "boot_animation_stopped",
            "verified_boot_state",
            "root_required",
            "boot_sha256",
            "supporting_partition_sha256",
            "odin_endpoint_absent",
        },
        label,
    )
    for key in ("android_boot_completed", "boot_animation_stopped", "root_required", "odin_endpoint_absent"):
        if item[key] is not True:
            raise F1V2Error(f"{label}.{key} must be true")
    if item["verified_boot_state"] != "orange":
        raise F1V2Error(f"{label}.verified_boot_state must be orange")
    _digest(item["boot_sha256"], f"{label}.boot_sha256")
    parts = _exact(item["supporting_partition_sha256"], {"vendor_boot", "dtbo", "recovery"}, f"{label}.parts")
    for name, value in parts.items():
        _digest(value, f"{label}.{name}")


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    _exact(
        profile,
        {"schema", "profile_id", "health_profile_id", "target", "transport", "rollback", "start_health", "final_health", "recovery"},
        "target profile",
    )
    if profile["schema"] != PROFILE_SCHEMA:
        raise F1V2Error("target profile schema mismatch")
    for key in ("profile_id", "health_profile_id"):
        if not isinstance(profile[key], str) or ID_RE.fullmatch(profile[key]) is None:
            raise F1V2Error(f"{key} is not canonical")
    target = _exact(profile["target"], {"model", "device", "firmware_incremental", "android_transport", "download"}, "target")
    for key in ("model", "device", "firmware_incremental"):
        _text(target[key], f"target.{key}", 128)
    if target["android_transport"] != "adb":
        raise F1V2Error("target Android transport must be adb")
    download = _exact(target["download"], {"usb_vendor_id", "usb_product_id", "product", "manufacturer", "serial_policy"}, "target.download")
    if (
        download["usb_vendor_id"],
        download["usb_product_id"],
        download["product"],
        download["manufacturer"],
        download["serial_policy"],
    ) != ("04e8", "685d", "SAMSUNG USB", "Samsung", "absent"):
        raise F1V2Error("target Download identity is not measured Samsung Download")
    transfer = _exact(profile["transport"], {"kind", "allowed_partition", "allowed_member", "odin"}, "transport")
    if (transfer["kind"], transfer["allowed_partition"], transfer["allowed_member"]) != ("odin4_boot_only", "boot", BOOT_MEMBER):
        raise F1V2Error("transport is not boot-only Odin")
    _artifact(transfer["odin"], "transport.odin")
    rollback = _exact(profile["rollback"], {"kind", "ap"}, "rollback")
    if rollback["kind"] != "magisk_boot_only":
        raise F1V2Error("rollback is not Magisk boot-only")
    _artifact(rollback["ap"], "rollback.ap")
    _health(profile["start_health"], "start_health")
    _health(profile["final_health"], "final_health")
    recovery = _exact(profile["recovery"], {"operator_attended", "physical_download_required", "rollback_preapproved"}, "recovery")
    if any(value is not True for value in recovery.values()):
        raise F1V2Error("recovery requirements must all be true")
    return profile


def validate_manifest(manifest: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    _exact(
        manifest,
        {"schema", "manifest_id", "run_id", "status", "target_profile", "candidate_ap", "rollback_ap", "allowed_member", "observation", "final_health_profile", "runner_version"},
        "candidate manifest",
    )
    if manifest["schema"] != MANIFEST_SCHEMA or manifest["status"] not in {
        "draft-host-only",
        "ready-for-f1-approval",
    }:
        raise F1V2Error("manifest has an invalid Process v2 readiness state")
    for key in ("manifest_id", "run_id"):
        if not isinstance(manifest[key], str) or ID_RE.fullmatch(manifest[key]) is None:
            raise F1V2Error(f"{key} is not canonical")
    _text(manifest["target_profile"], "target_profile")
    candidate = _artifact(manifest["candidate_ap"], "candidate_ap")
    rollback = _artifact(manifest["rollback_ap"], "rollback_ap")
    if rollback != profile["rollback"]["ap"] or rollback["sha256"] == candidate["sha256"]:
        raise F1V2Error("manifest rollback identity is invalid")
    if manifest["allowed_member"] != profile["transport"]["allowed_member"]:
        raise F1V2Error("manifest member differs from the profile")
    observation = manifest["observation"]
    if not isinstance(observation, dict) or frozenset(observation) not in {
        frozenset({"timeout_sec", "acceptance"}),
        frozenset({"timeout_sec", "acceptance", "candidate_observer"}),
        frozenset(
            {
                "timeout_sec",
                "acceptance",
                "candidate_observer",
                typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY,
            }
        ),
        frozenset(
            {
                "timeout_sec",
                "acceptance",
                typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY,
            }
        ),
    }:
        raise F1V2Error("observation shape mismatch")
    if isinstance(observation["timeout_sec"], bool) or not isinstance(observation["timeout_sec"], int) or not 1 <= observation["timeout_sec"] <= 600:
        raise F1V2Error("observation timeout is invalid")
    try:
        typed_evidence.validate_acceptance(observation["acceptance"])
    except typed_evidence.EvidenceError as exc:
        raise F1V2Error(str(exc)) from exc
    if "candidate_observer" in observation:
        if observation.get(typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY) not in (
            typed_evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
        ):
            try:
                cdc_acm_observer.validate_spec(observation["candidate_observer"])
            except cdc_acm_observer.ObserverError as exc:
                raise F1V2Error(str(exc)) from exc
    acceptance = observation["acceptance"]
    try:
        typed_evidence.validate_candidate_arrival_proof_role(
            observation.get(typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY),
            observation.get("candidate_observer"),
            expected_run_id=acceptance.get("run_id"),
        )
    except typed_evidence.EvidenceError as exc:
        raise F1V2Error(str(exc)) from exc
    role = observation.get(typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY)
    if role is not None:
        identity = (
            acceptance.get("userspace_overlay_contract_id"),
            acceptance.get("run_id"),
        )
        if identity not in {
            (
                typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P323_RUN_ID,
            ),
            (
                typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P324_RUN_ID,
            ),
            (
                typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P325_RUN_ID,
            ),
            (
                typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P326_RUN_ID,
            ),
            (
                typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P327_RUN_ID,
            ),
            (
                typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P328_RUN_ID,
            ),
            (
                typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P329_RUN_ID,
            ),
            (
                typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P330_RUN_ID,
            ),
            (
                typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P331_RUN_ID,
            ),
            (
                typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P332_RUN_ID,
            ),
            (
                typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P333_RUN_ID,
            ),
            (
                typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P334_RUN_ID,
            ),
            (
                typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P335_RUN_ID,
            ),
            (
                typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P336_RUN_ID,
            ),
            (
                typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P337_RUN_ID,
            ),
            (
                typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P338_RUN_ID,
            ),
            (
                typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P339_RUN_ID,
            ),
            (
                typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P340_RUN_ID,
            ),
            (
                typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P341_RUN_ID,
            ),
            (
                typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P342_RUN_ID,
            ),
            (
                typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P343_RUN_ID,
            ),
        }:
            raise F1V2Error(
                "candidate arrival proof role requires the exact versioned stock binding"
            )
    if manifest["final_health_profile"] != profile["health_profile_id"] or manifest["runner_version"] != RUNNER_VERSION:
        raise F1V2Error("manifest health profile or runner version mismatch")
    return manifest


def verify_p303_campaign_binding(
    acceptance: dict[str, Any],
    verification: dict[str, Any],
    *,
    manifest_id: str,
    live_run_id: str,
) -> None:
    """Keep the one stock baseline pair bound to its exact P3.03 run."""
    if acceptance.get("userspace_overlay_contract_id") not in {
        typed_evidence.P303_OVERLAY_CONTRACT_ID,
        typed_evidence.P304_OVERLAY_CONTRACT_ID,
        typed_evidence.P305_OVERLAY_CONTRACT_ID,
    }:
        return
    baseline = verification.get("p303_stock_baseline")
    stock_keys = {"stock_baseline_raw", "stock_baseline_result"}
    contract = acceptance.get("contract")
    if not isinstance(contract, dict):
        raise F1V2Error("P3.03 acceptance contract is invalid")
    supplied = stock_keys & set(contract)
    if not supplied:
        if baseline is not None:
            raise F1V2Error("P3.03 unbound stock baseline is present")
        return
    if supplied != stock_keys:
        raise F1V2Error("P3.03 stock baseline binding is incomplete")
    expected = {"manifest_id": manifest_id, "live_run_id": live_run_id}
    if not isinstance(baseline, dict) or baseline.get("campaign_binding") != expected:
        raise F1V2Error("P3.03 stock baseline belongs to a different campaign")


def _repo_path(root: Path, value: str, label: str) -> Path:
    path = Path(_text(value, label))
    if path.is_absolute() or ".." in path.parts:
        raise F1V2Error(f"{label} must be repository-relative")
    return (root / path).absolute()


def _artifact_path(root: Path, item: dict[str, Any], label: str) -> Path:
    path = Path(item["path"])
    if ".." in path.parts:
        raise F1V2Error(f"{label}.path contains traversal")
    return path.absolute() if path.is_absolute() else (root / path).absolute()


@dataclass(frozen=True)
class Bundle:
    profile: dict[str, Any]
    manifest: dict[str, Any]
    receipt: dict[str, Any]
    sha256: str


def _selected_candidate_source_contract(
    source_contract_id: str, profile: str
):
    if source_contract_id == typed_evidence.P310_SOURCE_CONTRACT_ID:
        import s22plus_fyg8_p310_candidate_intent as p310_intent

        try:
            return p310_intent.selected_source_contract_for_candidate(
                source_contract_id, profile
            )
        except p310_intent.IntentError as exc:
            raise F1V2Error(str(exc)) from exc
    if source_contract_id == typed_evidence.P300_SOURCE_CONTRACT_ID:
        import s22plus_fyg8_p300_candidate_intent as p300_intent

        try:
            return p300_intent.selected_source_contract_for_candidate(
                source_contract_id, profile
            )
        except p300_intent.IntentError as exc:
            raise F1V2Error(str(exc)) from exc
    try:
        return candidate_intent.selected_source_contract(
            source_contract_id, profile
        )
    except candidate_intent.IntentError as exc:
        raise F1V2Error(str(exc)) from exc


def _overridden_candidate_sources(
    userspace_overlay_contract_id: str | None,
) -> frozenset[str]:
    if userspace_overlay_contract_id in {
        typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P319_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.MAX77705_OVERLAY_CONTRACT_ID,
        typed_evidence.P317_MAX77705_OVERLAY_CONTRACT_ID,
        typed_evidence.P318_MAX77705_OVERLAY_CONTRACT_ID,
        typed_evidence.P311_OVERLAY_CONTRACT_ID,
        typed_evidence.P312_OVERLAY_CONTRACT_ID,
        typed_evidence.P313_OVERLAY_CONTRACT_ID,
        typed_evidence.P314_OVERLAY_CONTRACT_ID,
        typed_evidence.P315_OVERLAY_CONTRACT_ID,
    }:
        return frozenset({"p310_telemetry_decoder"})
    return frozenset()


def execution_critical_source_receipts(
    acceptance: dict[str, Any],
    *,
    candidate_arrival_proof_role: str | None = None,
    bind_private_inputs: bool = True,
) -> dict[str, dict[str, Any]]:
    if type(bind_private_inputs) is not bool:
        raise F1V2Error("private-input binding flag is invalid")
    receipts = {
        "runner": _stable_read(Path(__file__).resolve(), "F1 v2 runner")[1],
        "cdc_acm_observer": _stable_read(
            Path(cdc_acm_observer.__file__).resolve(),
            "CDC ACM observer",
        )[1],
        "typed_evidence": _stable_read(
            Path(typed_evidence.__file__).resolve(), "typed evidence runner"
        )[1],
        "checkpoint_decoder": _stable_read(
            Path(typed_evidence.checkpoint.__file__).resolve(),
            "checkpoint decoder",
        )[1],
        "regular_path_transport": _stable_read(
            Path(__file__).with_name("s22plus_boot_only_f1_transport.py").resolve(),
            "regular-path transport",
        )[1],
    }
    if acceptance.get("kind") == typed_evidence.SAME_RING_KIND:
        same_ring_sources = {
            "same_ring_decoder": Path(typed_evidence.same_ring.__file__),
            "same_ring_static_checker": Path(__file__).with_name(
                "s22plus_fyg8_p219_same_ring_contract.py"
            ),
            "same_ring_design_model": Path(__file__).with_name(
                "s22plus_fyg8_p218_same_ring_discriminator.py"
            ),
            "same_ring_base_checker": Path(__file__).with_name(
                "s22plus_fyg8_r4w1b_patch_check.py"
            ),
        }
        for name, path in same_ring_sources.items():
            receipts[name] = _stable_read(path.resolve(), name.replace("_", " "))[1]
    if acceptance.get("kind") == typed_evidence.SAME_RING_MULTIBOOT_KIND:
        same_ring_multiboot_sources = {
            "same_ring_multiboot_decoder": Path(
                typed_evidence.same_ring_multiboot.__file__
            ),
            "same_ring_record_decoder": Path(typed_evidence.same_ring.__file__),
            "same_ring_static_checker": Path(__file__).with_name(
                "s22plus_fyg8_p219_same_ring_contract.py"
            ),
            "same_ring_design_model": Path(__file__).with_name(
                "s22plus_fyg8_p218_same_ring_discriminator.py"
            ),
            "same_ring_base_checker": Path(__file__).with_name(
                "s22plus_fyg8_r4w1b_patch_check.py"
            ),
        }
        for name, path in same_ring_multiboot_sources.items():
            receipts[name] = _stable_read(path.resolve(), name.replace("_", " "))[1]
    if acceptance.get("kind") == typed_evidence.E1_LATEST_STAGE_KIND:
        profile = acceptance.get("profile")
        source_contract_id = acceptance.get("source_contract_id")
        userspace_overlay_contract_id = acceptance.get(
            "userspace_overlay_contract_id"
        )
        try:
            selected_decoder = typed_evidence._latest_stage_observation_decoder(
                source_contract_id,
                profile,
                userspace_overlay_contract_id,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        e1_latest_stage_sources = {
            "e1_latest_stage_decoder": Path(
                selected_decoder.__file__
            ),
            "e1_latest_stage_design_model": Path(
                selected_decoder.model.__file__
            ),
            "candidate_intent": Path(candidate_intent.__file__),
        }
        if source_contract_id is not None:
            try:
                selected = _selected_candidate_source_contract(
                    source_contract_id, profile
                )
                source_data = selected.source_bytes(candidate_intent.repo_root())
            except (
                candidate_intent.p233.CheckError,
                F1V2Error,
                OSError,
            ) as exc:
                raise F1V2Error(
                    "versioned execution-critical source closure failed"
                ) from exc
            overridden_sources = _overridden_candidate_sources(
                userspace_overlay_contract_id
            )
            if not overridden_sources <= set(source_data):
                raise F1V2Error("userspace overlay source override differs")
            for name, data in source_data.items():
                if name in overridden_sources:
                    continue
                receipts[f"candidate_source_{name}"] = {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            root = candidate_intent.repo_root()
            if userspace_overlay_contract_id in {
                typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
            }:
                # Stock adapters retain the P310 carrier closure while their
                # adapter/observer bytes are bound separately below.
                stock_adapter = typed_evidence.STOCK_ADAPTERS[
                    userspace_overlay_contract_id
                ]
                prefix = (
                    "p343"
                    if userspace_overlay_contract_id
                    == typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p342"
                    if userspace_overlay_contract_id
                    == typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p341"
                    if userspace_overlay_contract_id
                    == typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p340"
                    if userspace_overlay_contract_id
                    == typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p339"
                    if userspace_overlay_contract_id
                    == typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p338"
                    if userspace_overlay_contract_id
                    == typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p337"
                    if userspace_overlay_contract_id
                    == typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p336"
                    if userspace_overlay_contract_id
                    == typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p335"
                    if userspace_overlay_contract_id
                    == typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID
                    else "p334"
                    if userspace_overlay_contract_id
                    == typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID
                    else "p333"
                    if userspace_overlay_contract_id
                    == typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID
                    else "p332"
                    if userspace_overlay_contract_id
                    == typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID
                    else "p331"
                    if userspace_overlay_contract_id
                    == typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p330"
                    if userspace_overlay_contract_id
                    == typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID
                    else "p329"
                    if userspace_overlay_contract_id
                    == typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID
                    else "p328"
                    if userspace_overlay_contract_id
                    == typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID
                    else "p327"
                    if userspace_overlay_contract_id
                    == typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID
                    else "p326"
                    if userspace_overlay_contract_id
                    == typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID
                    else "p325"
                    if userspace_overlay_contract_id
                    == typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID
                    else
                    "p324"
                    if userspace_overlay_contract_id
                    == typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID
                    else "p323"
                    if userspace_overlay_contract_id
                    == typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID
                    else "p322"
                    if userspace_overlay_contract_id
                    == typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID
                    else (
                        "p321"
                        if userspace_overlay_contract_id
                        == typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID
                        else "p320"
                    )
                )
                label = {
                    "p343": "P3.43",
                    "p342": "P3.42",
                    "p341": "P3.41",
                    "p340": "P3.40",
                    "p339": "P3.39",
                    "p338": "P3.38",
                    "p337": "P3.37",
                    "p336": "P3.36",
                    "p335": "P3.35",
                    "p334": "P3.34",
                    "p333": "P3.33",
                    "p332": "P3.32",
                    "p331": "P3.31",
                    "p330": "P3.30",
                    "p329": "P3.29",
                    "p328": "P3.28",
                    "p327": "P3.27",
                    "p326": "P3.26",
                    "p325": "P3.25",
                    "p324": "P3.24",
                    "p323": "P3.23",
                    "p322": "P3.22",
                    "p321": "P3.21",
                    "p320": "P3.20",
                }[prefix]
                try:
                    adapter_sources = stock_adapter.source_bytes(root)
                except (stock_adapter.DecodeError, OSError) as exc:
                    raise F1V2Error(f"{label} stock adapter source closure failed") from exc
                if set(adapter_sources) != stock_adapter.SOURCE_KEYS:
                    raise F1V2Error(f"{label} stock adapter source set differs")
                for name, data in adapter_sources.items():
                    receipts[f"{prefix}_adapter_source_{name}"] = {
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                e1_latest_stage_sources[f"{prefix}_stock_adapter"] = Path(
                    stock_adapter.__file__
                )
                e1_latest_stage_sources[f"{prefix}_carrier_model"] = Path(
                    stock_adapter.model.__file__
                )
                e1_latest_stage_sources[f"{prefix}_telemetry_spec"] = Path(
                    stock_adapter.spec.__file__
                )
                observer_source = getattr(stock_adapter, "P320_OBSERVER_SOURCE", None)
                if observer_source is not None:
                    e1_latest_stage_sources[f"{prefix}_observer_contract"] = Path(
                        observer_source
                    )
                if prefix == "p323":
                    e1_latest_stage_sources["p323_predecessor_baseline"] = Path(
                        typed_evidence.p323_predecessor_baseline.__file__
                    )
                if prefix == "p324":
                    e1_latest_stage_sources["p324_typec_lane_binding"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_typec_lane_binding.py")
                    e1_latest_stage_sources["p324_cdc_acm_observer"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_cdc_acm_observer.py")
                if prefix == "p325":
                    e1_latest_stage_sources["p324_typec_lane_binding"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_typec_lane_binding.py")
                    e1_latest_stage_sources["p324_cdc_acm_observer"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_cdc_acm_observer.py")
                    e1_latest_stage_sources["p325_cdc_acm_guard_adapter"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p325_cdc_acm_guard_adapter.py")
                if prefix == "p326":
                    e1_latest_stage_sources["p324_typec_lane_binding"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_typec_lane_binding.py")
                    e1_latest_stage_sources["p324_cdc_acm_observer"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_cdc_acm_observer.py")
                    e1_latest_stage_sources["p325_cdc_acm_guard_adapter"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p325_cdc_acm_guard_adapter.py")
                    e1_latest_stage_sources["p326_bidirectional_acm_observer"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p326_bidirectional_acm_observer.py")
                if prefix in {"p328", "p329", "p330", "p331", "p332", "p333", "p334", "p335", "p336", "p337", "p338", "p339", "p340", "p341", "p342", "p343"}:
                    if bind_private_inputs:
                        try:
                            key_identity = (
                                typed_evidence.p343_artifact_identity.auth_key_identity()
                                if prefix == "p343"
                                else
                                typed_evidence.p342_artifact_identity.auth_key_identity()
                                if prefix == "p342"
                                else
                                typed_evidence.p341_artifact_identity.auth_key_identity()
                                if prefix == "p341"
                                else
                                typed_evidence.p340_artifact_identity.auth_key_identity()
                                if prefix == "p340"
                                else
                                typed_evidence.p339_artifact_identity.auth_key_identity()
                                if prefix == "p339"
                                else typed_evidence.p338_artifact_identity.auth_key_identity()
                                if prefix == "p338"
                                else
                                typed_evidence.p337_artifact_identity.auth_key_identity()
                                if prefix == "p337"
                                else
                                typed_evidence.p336_artifact_identity.auth_key_identity()
                                if prefix == "p336"
                                else
                                typed_evidence.p335_artifact_identity.auth_key_identity()
                                if prefix == "p335"
                                else typed_evidence.p334_artifact_identity.auth_key_identity()
                                if prefix == "p334"
                                else typed_evidence.p333_artifact_identity.auth_key_identity()
                                if prefix == "p333"
                                else typed_evidence.p332_artifact_identity.auth_key_identity()
                                if prefix == "p332"
                                else typed_evidence.p331_artifact_identity.auth_key_identity()
                                if prefix == "p331"
                                else
                                typed_evidence.p330_artifact_identity.auth_key_identity()
                                if prefix == "p330"
                                else typed_evidence.p329_artifact_identity.auth_key_identity()
                                if prefix == "p329"
                                else typed_evidence.p328_artifact_identity.auth_key_identity()
                            )
                        except Exception as exc:
                            raise F1V2Error(
                                f"{label} fixed auth key identity is unavailable"
                            ) from exc
                    else:
                        key_identity = dict(
                            typed_evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY
                        )
                    expected_key = (
                        typed_evidence.P343_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p343"
                        else
                        typed_evidence.P342_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p342"
                        else
                        typed_evidence.P341_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p341"
                        else
                        typed_evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p340"
                        else
                        typed_evidence.P339_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p339"
                        else
                        typed_evidence.P338_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p338"
                        else
                        typed_evidence.P337_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p337"
                        else
                        typed_evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p336"
                        else
                        typed_evidence.P335_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p335"
                        else typed_evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p334"
                        else typed_evidence.P333_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p333"
                        else typed_evidence.P332_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p332"
                        else typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p331"
                        else
                        typed_evidence.P330_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p330"
                        else typed_evidence.P329_AUTH_EXEC_AUTH_KEY_IDENTITY
                        if prefix == "p329"
                        else typed_evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY
                    )
                    if key_identity != expected_key:
                        raise F1V2Error(f"{label} fixed auth key identity differs")
                    receipts[f"{prefix}_auth_key"] = dict(key_identity)
                    if prefix == "p341":
                        e1_latest_stage_sources["p341_open_read_branch_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p341_open_read_branch_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p341_open_read_branch_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p341_open_read_branch_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p341_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p341_artifact_identity.py"
                            )
                        )
                        e1_latest_stage_sources["p341_host_first_open"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_host_first_open.py"
                            )
                        )
                        e1_latest_stage_sources["p341_open_failure_capture"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_open_failure_capture.py"
                            )
                        )
                        e1_latest_stage_sources["p341_stock_candidate_build"] = (
                            Path(__file__).resolve().parent.parent
                            / "analysis/s22plus_fyg8_p341_stock_candidate_build.py"
                        )
                        e1_latest_stage_sources["p341_stock_process_v2_adapter"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p341_stock_process_v2_adapter.py"
                            )
                        )
                    elif prefix == "p343":
                        e1_latest_stage_sources["p343_open_read_branch_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p343_open_read_branch_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p343_open_read_branch_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p343_open_read_branch_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p343_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p343_artifact_identity.py"
                            )
                        )
                        e1_latest_stage_sources["p343_host_first_open"] = (
                            Path(__file__).with_name("s22plus_fyg8_host_first_open.py")
                        )
                        e1_latest_stage_sources["p343_open_failure_capture"] = (
                            Path(__file__).with_name("s22plus_fyg8_open_failure_capture.py")
                        )
                        e1_latest_stage_sources["p343_idle_reuse_probe"] = (
                            Path(__file__).with_name("s22plus_fyg8_idle_reuse_probe.py")
                        )
                        e1_latest_stage_sources["p343_stock_candidate_build"] = (
                            Path(__file__).resolve().parent.parent
                            / "analysis/s22plus_fyg8_p343_stock_candidate_build.py"
                        )
                        e1_latest_stage_sources["p343_stock_process_v2_adapter"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p343_stock_process_v2_adapter.py"
                            )
                        )
                        e1_latest_stage_sources["p343_exploration_session"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p343_exploration_session.py"
                            )
                        )
                        e1_latest_stage_sources["p343_exploration_action"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p343_exploration_action.py"
                            )
                        )
                        e1_latest_stage_sources["p343_readonly_exploration"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_readonly_exploration.py"
                            )
                        )
                        e1_latest_stage_sources["p335_resident_session"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p335_resident_session.py"
                            )
                        )
                        e1_latest_stage_sources["p335_resident_action"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p335_resident_action.py"
                            )
                        )
                    elif prefix == "p342":
                        e1_latest_stage_sources["p342_open_read_branch_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p342_open_read_branch_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p342_open_read_branch_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p342_open_read_branch_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p342_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p342_artifact_identity.py"
                            )
                        )
                        e1_latest_stage_sources["p342_host_first_open"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_host_first_open.py"
                            )
                        )
                        e1_latest_stage_sources["p342_open_failure_capture"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_open_failure_capture.py"
                            )
                        )
                        e1_latest_stage_sources["p342_idle_reuse_probe"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_idle_reuse_probe.py"
                            )
                        )
                        e1_latest_stage_sources["p342_stock_candidate_build"] = (
                            Path(__file__).resolve().parent.parent
                            / "analysis/s22plus_fyg8_p342_stock_candidate_build.py"
                        )
                        e1_latest_stage_sources["p342_stock_process_v2_adapter"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p342_stock_process_v2_adapter.py"
                            )
                        )
                    elif prefix == "p340":
                        e1_latest_stage_sources["p340_open_read_branch_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p340_open_read_branch_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p340_open_read_branch_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p340_open_read_branch_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p340_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p340_artifact_identity.py"
                            )
                        )
                        e1_latest_stage_sources["p340_open_failure_capture"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_open_failure_capture.py"
                            )
                        )
                    elif prefix == "p339":
                        e1_latest_stage_sources["p339_open_read_branch_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p339_open_read_branch_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p339_open_read_branch_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p339_open_read_branch_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p339_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p339_artifact_identity.py"
                            )
                        )
                    elif prefix == "p338":
                        e1_latest_stage_sources["p338_open_read_branch_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p338_open_read_branch_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p338_open_read_branch_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p338_open_read_branch_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p338_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p338_artifact_identity.py"
                            )
                        )
                    elif prefix == "p337":
                        e1_latest_stage_sources["p337_open_read_diag_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p337_open_read_diag_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p337_open_read_diag_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p337_open_read_diag_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p337_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p337_artifact_identity.py"
                            )
                        )
                    elif prefix == "p336":
                        e1_latest_stage_sources["p336_long_idle_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p336_long_idle_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p336_long_idle_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p336_long_idle_runtime.py"
                            )
                        )
                        e1_latest_stage_sources["p336_artifact_identity"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p336_artifact_identity.py"
                            )
                        )
                        e1_latest_stage_sources["p336_long_idle_action"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p336_long_idle_action.py"
                            )
                        )
                        e1_latest_stage_sources["p336_long_idle_action_activation"] = (
                            Path(__file__).resolve().parents[2]
                            / "device-action/bindings/s22plus_fyg8_p336_long_idle_action_v1.json"
                        )
                    elif prefix == "p335":
                        e1_latest_stage_sources[
                            "p335_retained_listener_acm_observer"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p335_retained_listener_acm_observer.py"
                        )
                        e1_latest_stage_sources[
                            "p335_retained_listener_runtime"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p335_retained_listener_runtime.py"
                        )
                    elif prefix == "p334":
                        e1_latest_stage_sources[
                            "p334_first_read_rc_acm_observer"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p334_first_read_rc_acm_observer.py"
                        )
                        e1_latest_stage_sources[
                            "p334_first_read_rc_runtime"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p334_first_read_rc_runtime.py"
                        )
                    elif prefix == "p333":
                        e1_latest_stage_sources[
                            "p333_open_entry_diag_acm_observer"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p333_open_entry_diag_acm_observer.py"
                        )
                        e1_latest_stage_sources[
                            "p333_open_entry_diag_runtime"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p333_open_entry_diag_runtime.py"
                        )
                    elif prefix == "p332":
                        e1_latest_stage_sources[
                            "p332_logical_resident_acm_observer"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p332_logical_resident_acm_observer.py"
                        )
                        e1_latest_stage_sources[
                            "p332_logical_resident_exec_runtime"
                        ] = Path(__file__).with_name(
                            "s22plus_fyg8_p332_logical_resident_exec_runtime.py"
                        )
                    elif prefix == "p331":
                        e1_latest_stage_sources["p331_resident_acm_observer"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p331_resident_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources["p331_resident_exec_runtime"] = (
                            Path(__file__).with_name(
                                "s22plus_fyg8_p331_resident_exec_runtime.py"
                            )
                        )
                    else:
                        e1_latest_stage_sources[f"{prefix}_authenticated_acm_observer"] = (
                            Path(__file__).with_name(
                                f"s22plus_fyg8_{prefix}_auth_acm_observer.py"
                            )
                        )
                        e1_latest_stage_sources[f"{prefix}_authenticated_exec_runtime"] = (
                            Path(__file__).with_name(
                                f"s22plus_fyg8_{prefix}_auth_exec_runtime.py"
                            )
                        )
                    e1_latest_stage_sources[f"{prefix}_artifact_identity"] = (
                        Path(__file__).with_name(
                            "s22plus_fyg8_p343_artifact_identity.py"
                            if prefix == "p343"
                            else "s22plus_fyg8_p342_artifact_identity.py"
                            if prefix == "p342"
                            else "s22plus_fyg8_p341_artifact_identity.py"
                            if prefix == "p341"
                            else "s22plus_fyg8_p340_artifact_identity.py"
                            if prefix == "p340"
                            else "s22plus_fyg8_p339_artifact_identity.py"
                            if prefix == "p339"
                            else "s22plus_fyg8_p338_artifact_identity.py"
                            if prefix == "p338"
                            else "s22plus_fyg8_p337_artifact_identity.py"
                            if prefix == "p337"
                            else "s22plus_fyg8_p336_artifact_identity.py"
                            if prefix == "p336"
                            else "s22plus_fyg8_p335_artifact_identity.py"
                            if prefix == "p335"
                            else "s22plus_fyg8_p334_artifact_identity.py"
                            if prefix == "p334"
                            else "s22plus_fyg8_p333_artifact_identity.py"
                            if prefix == "p333"
                            else "s22plus_fyg8_p332_artifact_identity.py"
                            if prefix == "p332"
                            else "s22plus_fyg8_p331_artifact_identity.py"
                            if prefix == "p331"
                            else f"s22plus_fyg8_{prefix}_artifact_identity.py"
                        )
                    )
                if prefix == "p327":
                    e1_latest_stage_sources["p324_typec_lane_binding"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_typec_lane_binding.py")
                    e1_latest_stage_sources["p324_cdc_acm_observer"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p324_cdc_acm_observer.py")
                    e1_latest_stage_sources["p325_cdc_acm_guard_adapter"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p325_cdc_acm_guard_adapter.py")
                    e1_latest_stage_sources["p327_framed_acm_observer"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p327_framed_acm_observer.py")
                    e1_latest_stage_sources["p327_framed_exec_runtime"] = Path(
                        __file__
                    ).with_name("s22plus_fyg8_p327_framed_exec_runtime.py")
            elif userspace_overlay_contract_id == (
                typed_evidence.P319_STOCK_OVERLAY_CONTRACT_ID
            ):
                # P319 is a stock-witness overlay over the P310 carrier.  Its
                # adapter source closure is explicit and has no overlay
                # DEFAULT_INTENT/verify_intent path.
                try:
                    adapter_sources = typed_evidence.p319_stock_adapter.source_bytes(
                        root
                    )
                except (typed_evidence.p319_stock_adapter.DecodeError, OSError) as exc:
                    raise F1V2Error(
                        "P3.19 stock adapter source closure failed"
                    ) from exc
                if set(adapter_sources) != typed_evidence.p319_stock_adapter.SOURCE_KEYS:
                    raise F1V2Error("P3.19 stock adapter source set differs")
                for name, data in adapter_sources.items():
                    receipts[f"p319_adapter_source_{name}"] = {
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                e1_latest_stage_sources["p319_stock_adapter"] = Path(
                    typed_evidence.p319_stock_adapter.__file__
                )
                e1_latest_stage_sources["p319_carrier_model"] = Path(
                    typed_evidence.p319_stock_adapter.model.__file__
                )
                e1_latest_stage_sources["p319_telemetry_spec"] = Path(
                    typed_evidence.p319_stock_adapter.spec.__file__
                )
            elif userspace_overlay_contract_id in (
                typed_evidence.P301_TELEMETRY_OVERLAY_IDS
            ):
                root = candidate_intent.repo_root()
                if (
                    userspace_overlay_contract_id
                    == typed_evidence.P318_MAX77705_OVERLAY_CONTRACT_ID
                ):
                    import s22plus_fyg8_p318_overlay_contract as overlay_module

                    overlay_label = "P3.18"
                    prefix = "p318"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P317_MAX77705_OVERLAY_CONTRACT_ID
                ):
                    import s22plus_fyg8_p317_overlay_contract as overlay_module

                    overlay_label = "P3.17"
                    prefix = "p317"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.MAX77705_OVERLAY_CONTRACT_ID
                ):
                    import s22plus_fyg8_p316_overlay_contract as overlay_module

                    overlay_label = "P3.16"
                    prefix = "p316"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P315_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p315_overlay
                    overlay_label = "P3.15"
                    prefix = "p315"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P314_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p314_overlay
                    overlay_label = "P3.14"
                    prefix = "p314"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P313_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p313_overlay
                    overlay_label = "P3.13"
                    prefix = "p313"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P312_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p312_overlay
                    overlay_label = "P3.12"
                    prefix = "p312"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P311_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p311_overlay
                    overlay_label = "P3.11"
                    prefix = "p311"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P308_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p308_overlay
                    overlay_label = "P3.08"
                    prefix = "p308"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P307_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p307_overlay
                    overlay_label = "P3.07"
                    prefix = "p307"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P306_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p306_overlay
                    overlay_label = "P3.06"
                    prefix = "p306"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P305_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p305_overlay
                    overlay_label = "P3.05"
                    prefix = "p305"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P304_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p304_overlay
                    overlay_label = "P3.04"
                    prefix = "p304"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P303_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p303_overlay
                    overlay_label = "P3.03"
                    prefix = "p303"
                elif (
                    userspace_overlay_contract_id
                    == typed_evidence.P302_OVERLAY_CONTRACT_ID
                ):
                    overlay_module = typed_evidence.p302_overlay
                    overlay_label = "P3.02"
                    prefix = "p302"
                else:
                    overlay_module = typed_evidence.p301_overlay
                    overlay_label = "P3.01"
                    prefix = "p301"
                try:
                    overlay_contract = overlay_module.verify_intent(
                        root,
                        root / overlay_module.DEFAULT_INTENT,
                    )
                    if overlay_module in {
                        typed_evidence.p304_overlay,
                        typed_evidence.p305_overlay,
                        typed_evidence.p306_overlay,
                        typed_evidence.p307_overlay,
                        typed_evidence.p308_overlay,
                        typed_evidence.p311_overlay,
                        typed_evidence.p312_overlay,
                        typed_evidence.p313_overlay,
                        typed_evidence.p314_overlay,
                        typed_evidence.p315_overlay,
                    } or prefix in {"p316", "p317", "p318"}:
                        overlay_sources = {
                            name: overlay_module._read_regular(  # noqa: SLF001
                                root / path, f"{overlay_label} SOURCE_KEY {name}"
                            )
                            for name, path in sorted(
                                overlay_module.SOURCE_PATHS.items()
                            )
                        }
                    else:
                        overlay_sources = overlay_module.source_bytes(root)
                    if overlay_module is typed_evidence.p311_overlay:
                        replacement = overlay_sources.get(
                            "p310_telemetry_decoder_replacement"
                        )
                        if replacement != source_data.get(
                            "p310_telemetry_decoder"
                        ):
                            raise F1V2Error(
                                "P3.11 P3.10 decoder replacement differs"
                            )
                    if overlay_module is typed_evidence.p312_overlay:
                        replacement = overlay_sources.get(
                            "p310_telemetry_decoder"
                        )
                        if replacement != source_data.get(
                            "p310_telemetry_decoder"
                        ):
                            raise F1V2Error(
                                "P3.12 P3.10 decoder replacement differs"
                            )
                    if overlay_module is typed_evidence.p313_overlay:
                        replacement = overlay_sources.get(
                            "p310_telemetry_decoder"
                        )
                        if replacement != source_data.get(
                            "p310_telemetry_decoder"
                        ):
                            raise F1V2Error(
                                "P3.13 P3.10 decoder replacement differs"
                            )
                    if overlay_module is typed_evidence.p314_overlay:
                        replacement = overlay_sources.get(
                            "p310_telemetry_decoder"
                        )
                        if replacement != source_data.get(
                            "p310_telemetry_decoder"
                        ):
                            raise F1V2Error(
                                "P3.14 P3.10 decoder replacement differs"
                            )
                    if overlay_module is typed_evidence.p315_overlay:
                        replacement = overlay_sources.get(
                            "p310_telemetry_decoder"
                        )
                        if replacement != source_data.get(
                            "p310_telemetry_decoder"
                        ):
                            raise F1V2Error(
                                "P3.15 P3.10 decoder replacement differs"
                            )
                except (
                    overlay_module.OverlayContractError,
                    OSError,
                ) as exc:
                    raise F1V2Error(
                        f"{overlay_label} execution overlay closure failed"
                    ) from exc
                if (
                    overlay_contract.get("userspace_overlay_contract_id")
                    != userspace_overlay_contract_id
                    or overlay_contract.get("source_contract_id")
                    != source_contract_id
                ):
                    raise F1V2Error(
                        f"{overlay_label} execution overlay identity differs"
                    )
                for name, data in overlay_sources.items():
                    receipts[f"{prefix}_overlay_source_{name}"] = {
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                e1_latest_stage_sources[f"{prefix}_overlay_intent"] = (
                    root / overlay_module.DEFAULT_INTENT
                )
                if (
                    userspace_overlay_contract_id
                    in {
                        typed_evidence.P303_OVERLAY_CONTRACT_ID,
                        typed_evidence.P304_OVERLAY_CONTRACT_ID,
                        typed_evidence.P305_OVERLAY_CONTRACT_ID,
                    }
                ):
                    e1_latest_stage_sources["p303_stock_baseline_binding"] = Path(
                        typed_evidence.p303_stock_binding.__file__
                    )
                    e1_latest_stage_sources["p303_stock_log_d0"] = (
                        root / typed_evidence.p303_stock_binding.PRODUCER_PATH
                    )
                if (
                    userspace_overlay_contract_id
                    in {
                        typed_evidence.P302_OVERLAY_CONTRACT_ID,
                        typed_evidence.P303_OVERLAY_CONTRACT_ID,
                        typed_evidence.P304_OVERLAY_CONTRACT_ID,
                        typed_evidence.P305_OVERLAY_CONTRACT_ID,
                        typed_evidence.P306_OVERLAY_CONTRACT_ID,
                        typed_evidence.P307_OVERLAY_CONTRACT_ID,
                        typed_evidence.P308_OVERLAY_CONTRACT_ID,
                    }
                ):
                    parent_sources = typed_evidence.p301_overlay.source_bytes(root)
                    for name, data in parent_sources.items():
                        receipts[f"p301_overlay_source_{name}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
                    e1_latest_stage_sources["p301_overlay_intent"] = (
                        root / typed_evidence.p301_overlay.DEFAULT_INTENT
                    )
                if (
                    userspace_overlay_contract_id
                    in {
                        typed_evidence.P304_OVERLAY_CONTRACT_ID,
                        typed_evidence.P305_OVERLAY_CONTRACT_ID,
                        typed_evidence.P306_OVERLAY_CONTRACT_ID,
                        typed_evidence.P307_OVERLAY_CONTRACT_ID,
                        typed_evidence.P308_OVERLAY_CONTRACT_ID,
                    }
                ):
                    e1_latest_stage_sources["p304_e2_stock_closure"] = Path(
                        typed_evidence.p304_e2_closure.__file__
                    )
                    parent_sources = typed_evidence.p303_overlay.source_bytes(root)
                    for name, data in parent_sources.items():
                        receipts[f"p303_overlay_source_{name}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
                    e1_latest_stage_sources["p303_overlay_intent"] = (
                        root / typed_evidence.p303_overlay.DEFAULT_INTENT
                    )
                    if userspace_overlay_contract_id in {
                        typed_evidence.P305_OVERLAY_CONTRACT_ID,
                        typed_evidence.P306_OVERLAY_CONTRACT_ID,
                        typed_evidence.P307_OVERLAY_CONTRACT_ID,
                        typed_evidence.P308_OVERLAY_CONTRACT_ID,
                    }:
                        parent_sources = {
                            name: typed_evidence.p304_overlay._read_regular(  # noqa: SLF001
                                root / path, f"P3.04 SOURCE_KEY {name}"
                            )
                            for name, path in sorted(
                                typed_evidence.p304_overlay.SOURCE_PATHS.items()
                            )
                        }
                        for name, data in parent_sources.items():
                            receipts[f"p304_overlay_source_{name}"] = {
                                "size": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(),
                            }
                        e1_latest_stage_sources["p304_overlay_intent"] = (
                            root / typed_evidence.p304_overlay.DEFAULT_INTENT
                        )
                    if userspace_overlay_contract_id in {
                        typed_evidence.P306_OVERLAY_CONTRACT_ID,
                        typed_evidence.P307_OVERLAY_CONTRACT_ID,
                        typed_evidence.P308_OVERLAY_CONTRACT_ID,
                    }:
                        parent_sources = {
                            name: typed_evidence.p305_overlay._read_regular(  # noqa: SLF001
                                root / path, f"P3.05 SOURCE_KEY {name}"
                            )
                            for name, path in sorted(
                                typed_evidence.p305_overlay.SOURCE_PATHS.items()
                            )
                        }
                        for name, data in parent_sources.items():
                            receipts[f"p305_overlay_source_{name}"] = {
                                "size": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(),
                            }
                        e1_latest_stage_sources["p305_overlay_intent"] = (
                            root / typed_evidence.p305_overlay.DEFAULT_INTENT
                        )
                    if (
                        userspace_overlay_contract_id
                        == typed_evidence.P308_OVERLAY_CONTRACT_ID
                    ):
                        parent_sources = {
                            name: typed_evidence.p307_overlay._read_regular(  # noqa: SLF001
                                root / path, f"P3.07 SOURCE_KEY {name}"
                            )
                            for name, path in sorted(
                                typed_evidence.p307_overlay.SOURCE_PATHS.items()
                            )
                        }
                        for name, data in parent_sources.items():
                            receipts[f"p307_overlay_source_{name}"] = {
                                "size": len(data),
                                "sha256": hashlib.sha256(data).hexdigest(),
                            }
                        e1_latest_stage_sources["p307_overlay_intent"] = (
                            root / typed_evidence.p307_overlay.DEFAULT_INTENT
                        )
            e1_latest_stage_sources["source_contract_selector"] = Path(
                candidate_intent.source_contracts.__file__
            )
            if source_contract_id == candidate_intent.p286.CONTRACT_ID:
                import s22plus_fyg8_p286_change_freeze as p286_freeze

                for name, path in p286_freeze.NON_IDENTITY_SUPPORT_PATHS.items():
                    e1_latest_stage_sources[f"p286_support_{name}"] = (
                        candidate_intent.repo_root() / path
                    )
            elif source_contract_id == typed_evidence.P288_SOURCE_CONTRACT_ID:
                import s22plus_fyg8_p288_change_freeze as p288_freeze

                for name, path in p288_freeze.NON_IDENTITY_SUPPORT_PATHS.items():
                    e1_latest_stage_sources[f"p288_support_{name}"] = (
                        candidate_intent.repo_root() / path
                    )
            elif source_contract_id == typed_evidence.P290_SOURCE_CONTRACT_ID:
                import s22plus_fyg8_p290_change_freeze as p290_freeze

                for name, path in p290_freeze.NON_IDENTITY_SUPPORT_PATHS.items():
                    e1_latest_stage_sources[f"p290_support_{name}"] = (
                        candidate_intent.repo_root() / path
                    )
            elif source_contract_id in {
                typed_evidence.P300_SOURCE_CONTRACT_ID,
                typed_evidence.P310_SOURCE_CONTRACT_ID,
            }:
                import s22plus_fyg8_p300_identity_tiers as p300_identity

                try:
                    tier2 = p300_identity.tier2_materials(
                        candidate_intent.repo_root()
                    )
                    tier3 = p300_identity.tier3_materials(
                        candidate_intent.repo_root()
                    )
                except (p300_identity.IdentityTierError, OSError) as exc:
                    raise F1V2Error(
                        "P3.00 Stage C receipt closure failed"
                    ) from exc
                for tier, materials in (("tier2", tier2), ("tier3", tier3)):
                    for name, data in materials.items():
                        key = name.replace(":", "_")
                        receipts[f"p300_{tier}_{key}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
            elif source_contract_id == typed_evidence.P298_SOURCE_CONTRACT_ID:
                import s22plus_fyg8_p298_identity_tiers as p298_identity

                try:
                    tier2 = p298_identity.tier2_materials(
                        candidate_intent.repo_root()
                    )
                    tier3 = p298_identity.tier3_materials(
                        candidate_intent.repo_root()
                    )
                except (p298_identity.IdentityTierError, OSError) as exc:
                    raise F1V2Error(
                        "P2.98 Stage C receipt closure failed"
                    ) from exc
                for tier, materials in (("tier2", tier2), ("tier3", tier3)):
                    for name, data in materials.items():
                        key = name.replace(":", "_")
                        receipts[f"p298_{tier}_{key}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
            elif source_contract_id == typed_evidence.P296_SOURCE_CONTRACT_ID:
                import s22plus_fyg8_p296_identity_tiers as p296_identity

                try:
                    tier2 = p296_identity.tier2_materials(
                        candidate_intent.repo_root()
                    )
                    tier3 = p296_identity.tier3_materials(
                        candidate_intent.repo_root()
                    )
                except (p296_identity.IdentityTierError, OSError) as exc:
                    raise F1V2Error(
                        "P2.96 Stage C receipt closure failed"
                    ) from exc
                for tier, materials in (("tier2", tier2), ("tier3", tier3)):
                    for name, data in materials.items():
                        key = name.replace(":", "_")
                        receipts[f"p296_{tier}_{key}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
            elif source_contract_id == typed_evidence.P294_SOURCE_CONTRACT_ID:
                import s22plus_fyg8_p294_identity_tiers as p294_identity

                try:
                    tier2 = p294_identity.tier2_materials(
                        candidate_intent.repo_root()
                    )
                    tier3 = p294_identity.tier3_materials(
                        candidate_intent.repo_root()
                    )
                except (p294_identity.IdentityTierError, OSError) as exc:
                    raise F1V2Error(
                        "P2.94 Stage C receipt closure failed"
                    ) from exc
                for tier, materials in (("tier2", tier2), ("tier3", tier3)):
                    for name, data in materials.items():
                        key = name.replace(":", "_")
                        receipts[f"p294_{tier}_{key}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
            elif source_contract_id == typed_evidence.P292_SOURCE_CONTRACT_ID:
                import s22plus_fyg8_p292_identity_tiers as p292_identity

                try:
                    tier2 = p292_identity.tier2_materials(
                        candidate_intent.repo_root()
                    )
                    tier3 = p292_identity.tier3_materials(
                        candidate_intent.repo_root()
                    )
                except (p292_identity.IdentityTierError, OSError) as exc:
                    raise F1V2Error(
                        "P2.92 Stage C receipt closure failed"
                    ) from exc
                for tier, materials in (("tier2", tier2), ("tier3", tier3)):
                    for name, data in materials.items():
                        key = name.replace(":", "_")
                        receipts[f"p292_{tier}_{key}"] = {
                            "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(),
                        }
        elif profile in candidate_intent.SUPPORTED_PROFILES:
            for name, path in candidate_intent.source_paths_for_profile(
                profile
            ).items():
                e1_latest_stage_sources[f"candidate_source_{name}"] = (
                    candidate_intent.resolve(candidate_intent.repo_root(), path)
                )
        if profile == "E2":
            e1_latest_stage_sources.update(
                {
                    "e2_boot_verify": Path(
                        typed_evidence.e2_closure.boot_verify.__file__
                    ),
                    "e2_legacy_static_elf": Path(
                        typed_evidence.e2_closure.e1_static.__file__
                    ),
                }
            )
        for name, path in e1_latest_stage_sources.items():
            receipts[name] = _stable_read(
                path.resolve(),
                name.replace("_", " "),
                maximum=_execution_source_maximum(
                    name, userspace_overlay_contract_id
                ),
            )[1]
    if candidate_arrival_proof_role is not None:
        if candidate_arrival_proof_role not in {
            typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE,
            typed_evidence.CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE,
            typed_evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
            typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
        }:
            raise F1V2Error("candidate arrival proof role is not allowlisted")
        overlay = acceptance.get("userspace_overlay_contract_id")
        if candidate_arrival_proof_role == typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE:
            logical = {
                typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID: (
                    "p343", "P3.43",
                    "s22plus_fyg8_p343_open_read_branch_acm_observer.py",
                    "s22plus_fyg8_p343_open_read_branch_runtime.py",
                    "s22plus_fyg8_p343_artifact_identity.py",
                    typed_evidence.p343_artifact_identity,
                    typed_evidence.P343_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID: (
                    "p342", "P3.42",
                    "s22plus_fyg8_p342_open_read_branch_acm_observer.py",
                    "s22plus_fyg8_p342_open_read_branch_runtime.py",
                    "s22plus_fyg8_p342_artifact_identity.py",
                    typed_evidence.p342_artifact_identity,
                    typed_evidence.P342_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID: (
                    "p341", "P3.41",
                    "s22plus_fyg8_p341_open_read_branch_acm_observer.py",
                    "s22plus_fyg8_p341_open_read_branch_runtime.py",
                    "s22plus_fyg8_p341_artifact_identity.py",
                    typed_evidence.p341_artifact_identity,
                    typed_evidence.P341_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID: (
                    "p340", "P3.40",
                    "s22plus_fyg8_p340_open_read_branch_acm_observer.py",
                    "s22plus_fyg8_p340_open_read_branch_runtime.py",
                    "s22plus_fyg8_p340_artifact_identity.py",
                    typed_evidence.p340_artifact_identity,
                    typed_evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID: (
                    "p339", "P3.39",
                    "s22plus_fyg8_p339_open_read_branch_acm_observer.py",
                    "s22plus_fyg8_p339_open_read_branch_runtime.py",
                    "s22plus_fyg8_p339_artifact_identity.py",
                    typed_evidence.p339_artifact_identity,
                    typed_evidence.P339_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID: (
                    "p338", "P3.38",
                    "s22plus_fyg8_p338_open_read_branch_acm_observer.py",
                    "s22plus_fyg8_p338_open_read_branch_runtime.py",
                    "s22plus_fyg8_p338_artifact_identity.py",
                    typed_evidence.p338_artifact_identity,
                    typed_evidence.P338_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID: (
                    "p337", "P3.37",
                    "s22plus_fyg8_p337_open_read_diag_acm_observer.py",
                    "s22plus_fyg8_p337_open_read_diag_runtime.py",
                    "s22plus_fyg8_p337_artifact_identity.py",
                    typed_evidence.p337_artifact_identity,
                    typed_evidence.P337_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID: (
                    "p336", "P3.36",
                    "s22plus_fyg8_p336_long_idle_acm_observer.py",
                    "s22plus_fyg8_p336_long_idle_runtime.py",
                    "s22plus_fyg8_p336_artifact_identity.py",
                    typed_evidence.p336_artifact_identity,
                    typed_evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID: (
                    "p335", "P3.35",
                    "s22plus_fyg8_p335_retained_listener_acm_observer.py",
                    "s22plus_fyg8_p335_retained_listener_runtime.py",
                    "s22plus_fyg8_p335_artifact_identity.py",
                    typed_evidence.p335_artifact_identity,
                    typed_evidence.P335_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID: (
                    "p332", "P3.32",
                    "s22plus_fyg8_p332_logical_resident_acm_observer.py",
                    "s22plus_fyg8_p332_logical_resident_exec_runtime.py",
                    "s22plus_fyg8_p332_artifact_identity.py",
                    typed_evidence.p332_artifact_identity,
                    typed_evidence.P332_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID: (
                    "p333", "P3.33",
                    "s22plus_fyg8_p333_open_entry_diag_acm_observer.py",
                    "s22plus_fyg8_p333_open_entry_diag_runtime.py",
                    "s22plus_fyg8_p333_artifact_identity.py",
                    typed_evidence.p333_artifact_identity,
                    typed_evidence.P333_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
                typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID: (
                    "p334", "P3.34",
                    "s22plus_fyg8_p334_first_read_rc_acm_observer.py",
                    "s22plus_fyg8_p334_first_read_rc_runtime.py",
                    "s22plus_fyg8_p334_artifact_identity.py",
                    typed_evidence.p334_artifact_identity,
                    typed_evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY,
                ),
            }.get(overlay)
            if logical is None:
                raise F1V2Error("logical resident role requires its exact overlay")
            prefix, label, observer_name, runtime_name, artifact_name, artifact_module, expected_key = logical
            observer_key = (
                "p343_open_read_branch_acm_observer"
                if prefix == "p343"
                else
                "p341_open_read_branch_acm_observer"
                if prefix == "p341"
                else
                "p340_open_read_branch_acm_observer"
                if prefix == "p340"
                else
                "p339_open_read_branch_acm_observer"
                if prefix == "p339"
                else "p338_open_read_branch_acm_observer"
                if prefix == "p338"
                else
                "p337_open_read_diag_acm_observer"
                if prefix == "p337"
                else
                "p336_long_idle_acm_observer"
                if prefix == "p336"
                else
                "p335_retained_listener_acm_observer"
                if prefix == "p335"
                else "p334_first_read_rc_acm_observer"
                if prefix == "p334"
                else "p333_open_entry_diag_acm_observer"
                if prefix == "p333"
                else "p332_logical_resident_acm_observer"
            )
            runtime_key = (
                "p343_open_read_branch_runtime"
                if prefix == "p343"
                else
                "p341_open_read_branch_runtime"
                if prefix == "p341"
                else
                "p340_open_read_branch_runtime"
                if prefix == "p340"
                else
                "p339_open_read_branch_runtime"
                if prefix == "p339"
                else "p338_open_read_branch_runtime"
                if prefix == "p338"
                else
                "p337_open_read_diag_runtime"
                if prefix == "p337"
                else
                "p336_long_idle_runtime"
                if prefix == "p336"
                else
                "p335_retained_listener_runtime"
                if prefix == "p335"
                else "p334_first_read_rc_runtime"
                if prefix == "p334"
                else "p333_open_entry_diag_runtime"
                if prefix == "p333"
                else "p332_logical_resident_exec_runtime"
            )
            for name, filename in (
                (observer_key, observer_name),
                (runtime_key, runtime_name),
                (f"{prefix}_artifact_identity", artifact_name),
            ):
                receipts[name] = _stable_read(
                    Path(__file__).with_name(filename).resolve(),
                    f"{label} {name}",
                )[1]
            if prefix == "p336":
                for name, filename in (
                    (
                        "p336_long_idle_action",
                        "s22plus_fyg8_p336_long_idle_action.py",
                    ),
                    (
                        "p336_long_idle_action_activation",
                        "../device-action/bindings/s22plus_fyg8_p336_long_idle_action_v1.json",
                    ),
                ):
                    path = (
                        Path(__file__).with_name(filename).resolve()
                        if not filename.startswith("../")
                        else Path(__file__).resolve().parents[2]
                        / filename.removeprefix("../")
                    )
                    receipts[name] = _stable_read(path, f"P3.36 {name}")[1]
            if prefix == "p343":
                for name, filename in (
                    ("p343_exploration_session", "s22plus_fyg8_p343_exploration_session.py"),
                    ("p343_exploration_action", "s22plus_fyg8_p343_exploration_action.py"),
                    ("p343_readonly_exploration", "s22plus_fyg8_readonly_exploration.py"),
                    ("p335_resident_session", "s22plus_fyg8_p335_resident_session.py"),
                    ("p335_resident_action", "s22plus_fyg8_p335_resident_action.py"),
                ):
                    receipts[name] = _stable_read(
                        Path(__file__).with_name(filename).resolve(), f"P3.43 {name}"
                    )[1]
            if bind_private_inputs:
                try:
                    key_identity = artifact_module.auth_key_identity()
                except Exception as exc:
                    raise F1V2Error(f"{label} fixed auth key identity is unavailable") from exc
            else:
                key_identity = dict(expected_key)
            if key_identity != expected_key:
                raise F1V2Error(f"{label} fixed auth key identity differs")
            receipts[f"{prefix}_auth_key"] = dict(key_identity)
        elif candidate_arrival_proof_role == typed_evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE:
            if overlay != typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID:
                raise F1V2Error("P3.31 resident role requires the P3.31 overlay")
            for name, filename in (
                (
                    "p331_resident_acm_observer",
                    "s22plus_fyg8_p331_resident_acm_observer.py",
                ),
                (
                    "p331_resident_exec_runtime",
                    "s22plus_fyg8_p331_resident_exec_runtime.py",
                ),
                ("p331_artifact_identity", "s22plus_fyg8_p331_artifact_identity.py"),
            ):
                receipts[name] = _stable_read(
                    Path(__file__).with_name(filename).resolve(),
                    f"P3.31 {name}",
                )[1]
            if bind_private_inputs:
                try:
                    key_identity = typed_evidence.p331_artifact_identity.auth_key_identity()
                except Exception as exc:
                    raise F1V2Error("P3.31 fixed auth key identity is unavailable") from exc
            else:
                key_identity = dict(typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY)
            if key_identity != typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise F1V2Error("P3.31 fixed auth key identity differs")
            receipts["p331_auth_key"] = dict(key_identity)
        elif candidate_arrival_proof_role == typed_evidence.CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE:
            if overlay != typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID:
                raise F1V2Error("P3.30 diagnostic exec role requires the P3.30 overlay")
            for name, filename in (
                ("p330_authenticated_acm_observer", "s22plus_fyg8_p330_auth_acm_observer.py"),
                ("p330_authenticated_exec_runtime", "s22plus_fyg8_p330_auth_exec_runtime.py"),
                ("p330_artifact_identity", "s22plus_fyg8_p330_artifact_identity.py"),
            ):
                receipts[name] = _stable_read(
                    Path(__file__).with_name(filename).resolve(), f"P3.30 {name}"
                )[1]
            key_identity = (
                typed_evidence.p330_artifact_identity.auth_key_identity()
                if bind_private_inputs
                else dict(typed_evidence.P330_AUTH_EXEC_AUTH_KEY_IDENTITY)
            )
            if key_identity != typed_evidence.P330_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise F1V2Error("P3.30 fixed auth key identity differs")
            receipts["p330_auth_key"] = dict(key_identity)
        elif candidate_arrival_proof_role == typed_evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE:
            if overlay != typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID:
                raise F1V2Error("P3.29 settled exec role requires the P3.29 overlay")
            for name, filename in (
                ("p329_authenticated_acm_observer", "s22plus_fyg8_p329_auth_acm_observer.py"),
                ("p329_authenticated_exec_runtime", "s22plus_fyg8_p329_auth_exec_runtime.py"),
                ("p329_artifact_identity", "s22plus_fyg8_p329_artifact_identity.py"),
            ):
                receipts[name] = _stable_read(
                    Path(__file__).with_name(filename).resolve(), f"P3.29 {name}"
                )[1]
            key_identity = (
                typed_evidence.p329_artifact_identity.auth_key_identity()
                if bind_private_inputs
                else dict(typed_evidence.P329_AUTH_EXEC_AUTH_KEY_IDENTITY)
            )
            if key_identity != typed_evidence.P329_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise F1V2Error("P3.29 fixed auth key identity differs")
            receipts["p329_auth_key"] = dict(key_identity)
        elif candidate_arrival_proof_role == typed_evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE:
            if overlay != typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID:
                raise F1V2Error("P3.28 authenticated exec role requires the P3.28 overlay")
            for name, filename in (
                (
                    "p328_authenticated_acm_observer",
                    "s22plus_fyg8_p328_auth_acm_observer.py",
                ),
                (
                    "p328_authenticated_exec_runtime",
                    "s22plus_fyg8_p328_auth_exec_runtime.py",
                ),
                (
                    "p328_artifact_identity",
                    "s22plus_fyg8_p328_artifact_identity.py",
                ),
            ):
                receipts[name] = _stable_read(
                    Path(__file__).with_name(filename).resolve(),
                    f"P3.28 {name}",
                )[1]
            if bind_private_inputs:
                try:
                    key_identity = typed_evidence.p328_artifact_identity.auth_key_identity()
                except Exception as exc:
                    raise F1V2Error("P3.28 fixed auth key identity is unavailable") from exc
            else:
                key_identity = dict(typed_evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY)
            if key_identity != typed_evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY:
                raise F1V2Error("P3.28 fixed auth key identity differs")
            receipts["p328_auth_key"] = dict(key_identity)
        elif candidate_arrival_proof_role == typed_evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE:
            if overlay != typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID:
                raise F1V2Error("P3.27 framed command role requires the P3.27 overlay")
            for name, filename in (
                ("p327_framed_acm_observer", "s22plus_fyg8_p327_framed_acm_observer.py"),
                ("p327_framed_exec_runtime", "s22plus_fyg8_p327_framed_exec_runtime.py"),
            ):
                receipts[name] = _stable_read(
                    Path(__file__).with_name(filename).resolve(),
                    f"P3.27 {name}",
                )[1]
        elif candidate_arrival_proof_role == typed_evidence.CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE:
            if overlay != typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID:
                raise F1V2Error("P3.26 console role requires the P3.26 overlay")
            runtime_path = Path(__file__).with_name(
                "s22plus_fyg8_p326_bidirectional_console_runtime.py"
            )
            receipts["p326_bidirectional_console_runtime"] = _stable_read(
                runtime_path.resolve(), "P3.26 bidirectional console runtime"
            )[1]
        elif overlay == typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID:
            prefix = "p324"
            label = "P3.24 retained ACM-primary runtime for P3.25"
        else:
            p324 = overlay == typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID
            prefix = "p324" if p324 else "p323"
            label = f"P3.{24 if p324 else 23} ACM-primary runtime"
        if candidate_arrival_proof_role == typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE:
            runtime_path = Path(__file__).with_name(
                f"s22plus_fyg8_{prefix}_acm_primary_runtime.py"
            )
            receipts[f"{prefix}_acm_primary_runtime"] = _stable_read(
                runtime_path.resolve(), label
            )[1]
    return receipts


def verify_candidate_source_binding(
    acceptance: dict[str, Any],
    verification: dict[str, Any],
    execution_sources: dict[str, dict[str, Any]],
) -> None:
    if acceptance.get("kind") != typed_evidence.E1_LATEST_STAGE_KIND:
        return
    expected_sources = verification.get("candidate_source_receipts")
    source_contract_id = acceptance.get("source_contract_id")
    userspace_overlay_contract_id = acceptance.get(
        "userspace_overlay_contract_id"
    )
    if verification.get("source_contract_id") != source_contract_id:
        raise F1V2Error("candidate source contract selector changed")
    if source_contract_id is not None:
        expected_keys = _selected_candidate_source_contract(
            source_contract_id, acceptance.get("profile")
        ).source_keys
    else:
        expected_keys = typed_evidence.E1_LATEST_STAGE_SOURCE_KEYS.get(
            acceptance.get("profile")
        )
    if (
        expected_keys is None
        or not isinstance(expected_sources, dict)
        or set(expected_sources) != expected_keys
    ):
        raise F1V2Error("candidate source preimage is incomplete")
    overridden_sources = _overridden_candidate_sources(
        userspace_overlay_contract_id
    )
    if not overridden_sources <= set(expected_sources):
        raise F1V2Error("candidate source override preimage differs")
    for name, source_receipt in expected_sources.items():
        if name in overridden_sources:
            continue
        actual = execution_sources.get(f"candidate_source_{name}")
        if (
            not isinstance(actual, dict)
            or {key: actual.get(key) for key in ("size", "sha256")}
            != source_receipt
        ):
            raise F1V2Error(
                "candidate source preimage differs from execution-critical sources"
            )
    if userspace_overlay_contract_id in {
        typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
    }:
        if verification.get("userspace_overlay_contract_id") != userspace_overlay_contract_id:
            raise F1V2Error("stock overlay selector changed")
        adapter = typed_evidence.STOCK_ADAPTERS[userspace_overlay_contract_id]
        prefix = (
            "p343"
            if userspace_overlay_contract_id
            == typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID
            else
            "p342"
            if userspace_overlay_contract_id
            == typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID
            else
            "p341"
            if userspace_overlay_contract_id
            == typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID
            else
            "p340"
            if userspace_overlay_contract_id
            == typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID
            else
            "p339"
            if userspace_overlay_contract_id
            == typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID
            else
            "p338"
            if userspace_overlay_contract_id
            == typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID
            else
            "p337"
            if userspace_overlay_contract_id
            == typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID
            else "p336"
            if userspace_overlay_contract_id
            == typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID
            else "p335"
            if userspace_overlay_contract_id
            == typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID
            else "p334"
            if userspace_overlay_contract_id
            == typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID
            else "p333"
            if userspace_overlay_contract_id
            == typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID
            else "p332"
            if userspace_overlay_contract_id
            == typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID
            else "p331"
            if userspace_overlay_contract_id
            == typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID
            else
            "p330"
            if userspace_overlay_contract_id
            == typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID
            else "p329"
            if userspace_overlay_contract_id
            == typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID
            else "p328"
            if userspace_overlay_contract_id
            == typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID
            else "p327"
            if userspace_overlay_contract_id
            == typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID
            else "p326"
            if userspace_overlay_contract_id
            == typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID
            else "p325"
            if userspace_overlay_contract_id
            == typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID
            else
            "p324"
            if userspace_overlay_contract_id
            == typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID
            else "p323"
            if userspace_overlay_contract_id
            == typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID
            else "p322"
            if userspace_overlay_contract_id
            == typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID
            else "p321"
            if userspace_overlay_contract_id
            == typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID
            else "p320"
        )
        expected_adapter = verification.get(f"{prefix}_adapter_source_receipts")
        if (
            not isinstance(expected_adapter, dict)
            or set(expected_adapter) != adapter.SOURCE_KEYS
        ):
            raise F1V2Error(f"{prefix} stock adapter source binding is incomplete")
        for name, source_receipt in expected_adapter.items():
            actual = execution_sources.get(f"{prefix}_adapter_source_{name}")
            if (
                not isinstance(actual, dict)
                or {key: actual.get(key) for key in ("size", "sha256")}
                != source_receipt
            ):
                raise F1V2Error(f"{prefix} stock adapter source differs from execution-critical sources")
        if prefix == "p325":
            expected_guard = verification.get("p325_guard_adapter_source")
            actual_guard = execution_sources.get("p325_cdc_acm_guard_adapter")
            if (
                not isinstance(expected_guard, dict)
                or not isinstance(actual_guard, dict)
                or {key: actual_guard.get(key) for key in ("size", "sha256")}
                != expected_guard
            ):
                raise F1V2Error(
                    "p325 CDC ACM guard adapter differs from execution-critical sources"
                )
        if prefix in {"p328", "p329", "p330", "p331", "p332", "p333", "p334", "p335", "p336", "p337", "p338", "p339", "p340", "p341", "p342", "p343"}:
            version = (
                "P3.43"
                if prefix == "p343"
                else
                "P3.42"
                if prefix == "p342"
                else
                "P3.41"
                if prefix == "p341"
                else
                "P3.40"
                if prefix == "p340"
                else
                "P3.39"
                if prefix == "p339"
                else "P3.38"
                if prefix == "p338"
                else
                "P3.37"
                if prefix == "p337"
                else "P3.36"
                if prefix == "p336"
                else "P3.35"
                if prefix == "p335"
                else "P3.34"
                if prefix == "p334"
                else "P3.33"
                if prefix == "p333"
                else "P3.32"
                if prefix == "p332"
                else "P3.31"
                if prefix == "p331"
                else
                "P3.30"
                if prefix == "p330"
                else "P3.29"
                if prefix == "p329"
                else "P3.28"
            )
            expected_observer = verification.get("p328_authenticated_observer_source")
            if prefix == "p343":
                expected_observer = verification.get(
                    "p343_open_read_branch_acm_observer_source"
                )
            elif prefix == "p342":
                expected_observer = verification.get(
                    "p342_open_read_branch_acm_observer_source"
                )
            elif prefix == "p341":
                expected_observer = verification.get(
                    "p341_open_read_branch_acm_observer_source"
                )
            elif prefix == "p340":
                expected_observer = verification.get(
                    "p340_open_read_branch_acm_observer_source"
                )
            elif prefix == "p339":
                expected_observer = verification.get(
                    "p339_open_read_branch_acm_observer_source"
                )
            elif prefix == "p338":
                expected_observer = verification.get(
                    "p338_open_read_branch_acm_observer_source"
                )
            elif prefix == "p337":
                expected_observer = verification.get(
                    "p337_open_read_diag_acm_observer_source"
                )
            elif prefix == "p336":
                expected_observer = verification.get(
                    "p336_long_idle_acm_observer_source"
                )
            elif prefix == "p335":
                expected_observer = verification.get(
                    "p335_retained_listener_observer_source"
                )
            elif prefix == "p334":
                expected_observer = verification.get(
                    "p334_first_read_rc_observer_source",
                    verification.get("p334_authenticated_observer_source"),
                )
            elif prefix == "p333":
                expected_observer = verification.get(
                    "p333_open_entry_diag_observer_source",
                    verification.get("p333_authenticated_observer_source"),
                )
            elif prefix == "p332":
                expected_observer = verification.get(
                    "p332_logical_resident_observer_source",
                    verification.get("p332_authenticated_observer_source"),
                )
            elif prefix == "p331":
                expected_observer = verification.get(
                    "p331_resident_observer_source",
                    verification.get("p331_authenticated_observer_source"),
                )
            elif prefix in {"p329", "p330"}:
                expected_observer = verification.get("p329_authenticated_observer_source")
            if prefix == "p330":
                expected_observer = verification.get("p330_authenticated_observer_source")
            actual_observer = execution_sources.get(
                "p343_open_read_branch_acm_observer"
                if prefix == "p343"
                else "p342_open_read_branch_acm_observer"
                if prefix == "p342"
                else "p341_open_read_branch_acm_observer"
                if prefix == "p341"
                else "p340_open_read_branch_acm_observer"
                if prefix == "p340"
                else "p339_open_read_branch_acm_observer"
                if prefix == "p339"
                else "p338_open_read_branch_acm_observer"
                if prefix == "p338"
                else
                "p337_open_read_diag_acm_observer"
                if prefix == "p337"
                else "p336_long_idle_acm_observer"
                if prefix == "p336"
                else "p335_retained_listener_acm_observer"
                if prefix == "p335"
                else "p334_first_read_rc_acm_observer"
                if prefix == "p334"
                else "p333_open_entry_diag_acm_observer"
                if prefix == "p333"
                else "p332_logical_resident_acm_observer"
                if prefix == "p332"
                else "p331_resident_acm_observer"
                if prefix == "p331"
                else f"{prefix}_authenticated_acm_observer"
            )
            if (
                not isinstance(expected_observer, dict)
                or not isinstance(actual_observer, dict)
                or {key: actual_observer.get(key) for key in ("size", "sha256")}
                != expected_observer
            ):
                raise F1V2Error(
                    f"{version} authenticated observer differs from execution-critical sources"
                )
            expected_runtime = verification.get(
                f"{prefix}_authenticated_runtime_source"
            )
            if prefix == "p343":
                expected_runtime = verification.get(
                    "p343_open_read_branch_runtime_source"
                )
            elif prefix == "p342":
                expected_runtime = verification.get(
                    "p342_open_read_branch_runtime_source"
                )
            elif prefix == "p341":
                expected_runtime = verification.get(
                    "p341_open_read_branch_runtime_source"
                )
            elif prefix == "p340":
                expected_runtime = verification.get(
                    "p340_open_read_branch_runtime_source"
                )
            elif prefix == "p339":
                expected_runtime = verification.get(
                    "p339_open_read_branch_runtime_source"
                )
            elif prefix == "p338":
                expected_runtime = verification.get(
                    "p338_open_read_branch_runtime_source"
                )
            elif prefix == "p337":
                expected_runtime = verification.get(
                    "p337_open_read_diag_runtime_source"
                )
            elif prefix == "p336":
                expected_runtime = verification.get(
                    "p336_long_idle_runtime_source"
                )
            elif prefix == "p335":
                expected_runtime = verification.get(
                    "p335_retained_listener_runtime_source"
                )
            elif prefix == "p334":
                expected_runtime = verification.get(
                    "p334_first_read_rc_runtime_source",
                    verification.get("p334_authenticated_runtime_source"),
                )
            elif prefix == "p333":
                expected_runtime = verification.get(
                    "p333_open_entry_diag_runtime_source",
                    verification.get("p333_authenticated_runtime_source"),
                )
            elif prefix == "p332":
                expected_runtime = verification.get(
                    "p332_logical_resident_runtime_source",
                    verification.get("p332_authenticated_runtime_source"),
                )
            elif prefix == "p331":
                expected_runtime = verification.get(
                    "p331_resident_runtime_source",
                    verification.get("p331_authenticated_runtime_source"),
                )
            actual_runtime = execution_sources.get(
                "p343_open_read_branch_runtime"
                if prefix == "p343"
                else "p342_open_read_branch_runtime"
                if prefix == "p342"
                else "p341_open_read_branch_runtime"
                if prefix == "p341"
                else "p340_open_read_branch_runtime"
                if prefix == "p340"
                else "p339_open_read_branch_runtime"
                if prefix == "p339"
                else "p338_open_read_branch_runtime"
                if prefix == "p338"
                else
                "p337_open_read_diag_runtime"
                if prefix == "p337"
                else "p336_long_idle_runtime"
                if prefix == "p336"
                else "p335_retained_listener_runtime"
                if prefix == "p335"
                else "p334_first_read_rc_runtime"
                if prefix == "p334"
                else "p333_open_entry_diag_runtime"
                if prefix == "p333"
                else "p332_logical_resident_exec_runtime"
                if prefix == "p332"
                else "p331_resident_exec_runtime"
                if prefix == "p331"
                else f"{prefix}_authenticated_exec_runtime"
            )
            if (
                not isinstance(expected_runtime, dict)
                or not isinstance(actual_runtime, dict)
                or {key: actual_runtime.get(key) for key in ("size", "sha256")}
                != expected_runtime
            ):
                raise F1V2Error(
                    f"{version} authenticated runtime differs from execution-critical sources"
            )
            expected_artifact = verification.get(f"{prefix}_artifact_identity_source")
            if prefix == "p343":
                expected_artifact = verification.get(
                    "p343_artifact_identity_source"
                )
            elif prefix == "p342":
                expected_artifact = verification.get(
                    "p342_artifact_identity_source"
                )
            elif prefix == "p341":
                expected_artifact = verification.get(
                    "p341_artifact_identity_source"
                )
            elif prefix == "p331":
                expected_artifact = verification.get(
                    "p331_artifact_identity_source"
                )
            actual_artifact = execution_sources.get(f"{prefix}_artifact_identity")
            if (
                not isinstance(expected_artifact, dict)
                or not isinstance(actual_artifact, dict)
                or {key: actual_artifact.get(key) for key in ("size", "sha256")}
                != expected_artifact
            ):
                raise F1V2Error(
                    f"{version} artifact identity differs from execution-critical sources"
                )
            if prefix == "p343":
                expected_idle = verification.get("p343_idle_reuse_probe_source")
                actual_idle = execution_sources.get("p343_idle_reuse_probe")
                if (
                    not isinstance(expected_idle, dict)
                    or not isinstance(actual_idle, dict)
                    or {key: actual_idle.get(key) for key in ("size", "sha256")}
                    != {key: expected_idle.get(key) for key in ("size", "sha256")}
                ):
                    raise F1V2Error(
                        "P3.43 idle-reuse probe differs from execution-critical sources"
                    )
            elif prefix == "p342":
                expected_idle = verification.get("p342_idle_reuse_probe_source")
                actual_idle = execution_sources.get("p342_idle_reuse_probe")
                if (
                    not isinstance(expected_idle, dict)
                    or not isinstance(actual_idle, dict)
                    or {key: actual_idle.get(key) for key in ("size", "sha256")}
                    != {key: expected_idle.get(key) for key in ("size", "sha256")}
                ):
                    raise F1V2Error(
                        "P3.42 idle-reuse probe differs from execution-critical sources"
                    )
            if prefix == "p336":
                for expected_name, actual_name in (
                    ("p336_long_idle_action_source", "p336_long_idle_action"),
                    (
                        "p336_long_idle_action_activation",
                        "p336_long_idle_action_activation",
                    ),
                ):
                    expected_action = verification.get(expected_name)
                    actual_action = execution_sources.get(actual_name)
                    if (
                        not isinstance(expected_action, dict)
                        or not isinstance(actual_action, dict)
                        or {key: actual_action.get(key) for key in ("size", "sha256")}
                        != {key: expected_action.get(key) for key in ("size", "sha256")}
                    ):
                        raise F1V2Error(
                            f"P3.36 {expected_name} differs from execution-critical sources"
                        )
            expected_key = verification.get(f"{prefix}_auth_key")
            actual_key = execution_sources.get(f"{prefix}_auth_key")
            if (
                not isinstance(expected_key, dict)
                or set(expected_key) != {"size", "sha256"}
                or expected_key
                != (
                    typed_evidence.P343_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p343"
                    else
                    typed_evidence.P342_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p342"
                    else
                    typed_evidence.P341_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p341"
                    else
                    typed_evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p340"
                    else
                    typed_evidence.P339_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p339"
                    else typed_evidence.P338_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p338"
                    else
                    typed_evidence.P337_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p337"
                    else typed_evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p336"
                    else typed_evidence.P335_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p335"
                    else typed_evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p334"
                    else typed_evidence.P333_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p333"
                    else typed_evidence.P332_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p332"
                    else typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p331"
                    else
                    typed_evidence.P329_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p329"
                    else typed_evidence.P330_AUTH_EXEC_AUTH_KEY_IDENTITY
                    if prefix == "p330"
                    else typed_evidence.P328_AUTH_EXEC_AUTH_KEY_IDENTITY
                )
                or actual_key != expected_key
            ):
                raise F1V2Error(
                    f"{version} auth key identity differs from execution-critical sources"
                )
            if prefix == "p343":
                for expected_name, actual_name in (
                    ("p343_exploration_session_source", "p343_exploration_session"),
                    ("p343_exploration_action_source", "p343_exploration_action"),
                    ("p343_readonly_exploration_source", "p343_readonly_exploration"),
                    ("p335_resident_session_source", "p335_resident_session"),
                    ("p335_resident_action_source", "p335_resident_action"),
                ):
                    expected_extra = verification.get(expected_name)
                    actual_extra = execution_sources.get(actual_name)
                    if (
                        not isinstance(expected_extra, dict)
                        or not isinstance(actual_extra, dict)
                        or {key: actual_extra.get(key) for key in ("size", "sha256")}
                        != {key: expected_extra.get(key) for key in ("size", "sha256")}
                    ):
                        raise F1V2Error(
                            f"P3.43 {expected_name} differs from execution-critical sources"
                        )
        elif prefix == "p327":
            expected_observer = verification.get("p327_framed_observer_source")
            actual_observer = execution_sources.get("p327_framed_acm_observer")
            if (
                not isinstance(expected_observer, dict)
                or not isinstance(actual_observer, dict)
                or {key: actual_observer.get(key) for key in ("size", "sha256")}
                != expected_observer
            ):
                raise F1V2Error(
                    "p327 framed observer differs from execution-critical sources"
                )
            expected_runtime = verification.get("p327_framed_runtime_source")
            actual_runtime = execution_sources.get("p327_framed_exec_runtime")
            if (
                not isinstance(expected_runtime, dict)
                or not isinstance(actual_runtime, dict)
                or {key: actual_runtime.get(key) for key in ("size", "sha256")}
                != expected_runtime
            ):
                raise F1V2Error(
                    "p327 framed runtime differs from execution-critical sources"
                )
        elif prefix == "p326":
            expected_observer = verification.get("p326_observer_source")
            actual_observer = execution_sources.get("p326_bidirectional_acm_observer")
            if (
                not isinstance(expected_observer, dict)
                or not isinstance(actual_observer, dict)
                or {key: actual_observer.get(key) for key in ("size", "sha256")}
                != expected_observer
            ):
                raise F1V2Error(
                    "p326 bidirectional observer differs from execution-critical sources"
                )
            expected_runtime = verification.get("p326_console_runtime_source")
            actual_runtime = execution_sources.get("p326_bidirectional_console_runtime")
            if (
                not isinstance(expected_runtime, dict)
                or not isinstance(actual_runtime, dict)
                or {key: actual_runtime.get(key) for key in ("size", "sha256")}
                != expected_runtime
            ):
                raise F1V2Error(
                    "p326 console runtime differs from execution-critical sources"
                )
    elif userspace_overlay_contract_id == typed_evidence.P319_STOCK_OVERLAY_CONTRACT_ID:
        if verification.get("userspace_overlay_contract_id") != userspace_overlay_contract_id:
            raise F1V2Error("P3.19 stock overlay selector changed")
        expected_adapter = verification.get("p319_adapter_source_receipts")
        if (
            not isinstance(expected_adapter, dict)
            or set(expected_adapter) != typed_evidence.p319_stock_adapter.SOURCE_KEYS
        ):
            raise F1V2Error("P3.19 stock adapter source binding is incomplete")
        for name, source_receipt in expected_adapter.items():
            actual = execution_sources.get(f"p319_adapter_source_{name}")
            if (
                not isinstance(actual, dict)
                or {key: actual.get(key) for key in ("size", "sha256")}
                != source_receipt
            ):
                raise F1V2Error("P3.19 stock adapter source differs from execution-critical sources")
    elif userspace_overlay_contract_id is not None:
        if (
            userspace_overlay_contract_id
            not in typed_evidence.P301_TELEMETRY_OVERLAY_IDS
            or verification.get("userspace_overlay_contract_id")
            != userspace_overlay_contract_id
        ):
            raise F1V2Error("candidate userspace overlay selector changed")
        if (
            userspace_overlay_contract_id
            == typed_evidence.P318_MAX77705_OVERLAY_CONTRACT_ID
        ):
            import s22plus_fyg8_p318_overlay_contract as p318_overlay

            required_overlays = [("p318", p318_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.P317_MAX77705_OVERLAY_CONTRACT_ID
        ):
            import s22plus_fyg8_p317_overlay_contract as p317_overlay

            required_overlays = [("p317", p317_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.MAX77705_OVERLAY_CONTRACT_ID
        ):
            import s22plus_fyg8_p316_overlay_contract as p316_overlay

            required_overlays = [("p316", p316_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.P315_OVERLAY_CONTRACT_ID
        ):
            required_overlays = [("p315", typed_evidence.p315_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.P314_OVERLAY_CONTRACT_ID
        ):
            required_overlays = [("p314", typed_evidence.p314_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.P313_OVERLAY_CONTRACT_ID
        ):
            required_overlays = [("p313", typed_evidence.p313_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.P312_OVERLAY_CONTRACT_ID
        ):
            required_overlays = [("p312", typed_evidence.p312_overlay)]
        elif (
            userspace_overlay_contract_id
            == typed_evidence.P311_OVERLAY_CONTRACT_ID
        ):
            required_overlays = [("p311", typed_evidence.p311_overlay)]
        else:
            required_overlays = [("p301", typed_evidence.p301_overlay)]
        if (
            userspace_overlay_contract_id
            == typed_evidence.P302_OVERLAY_CONTRACT_ID
        ):
            required_overlays.append(("p302", typed_evidence.p302_overlay))
        if (
            userspace_overlay_contract_id
            == typed_evidence.P303_OVERLAY_CONTRACT_ID
        ):
            required_overlays.append(("p303", typed_evidence.p303_overlay))
        if (
            userspace_overlay_contract_id
            == typed_evidence.P304_OVERLAY_CONTRACT_ID
        ):
            required_overlays.extend(
                (
                    ("p303", typed_evidence.p303_overlay),
                    ("p304", typed_evidence.p304_overlay),
                )
            )
        if (
            userspace_overlay_contract_id
            == typed_evidence.P305_OVERLAY_CONTRACT_ID
        ):
            required_overlays.extend(
                (
                    ("p303", typed_evidence.p303_overlay),
                    ("p304", typed_evidence.p304_overlay),
                    ("p305", typed_evidence.p305_overlay),
                )
            )
        if (
            userspace_overlay_contract_id
            == typed_evidence.P306_OVERLAY_CONTRACT_ID
        ):
            required_overlays.extend(
                (
                    ("p303", typed_evidence.p303_overlay),
                    ("p304", typed_evidence.p304_overlay),
                    ("p305", typed_evidence.p305_overlay),
                    ("p306", typed_evidence.p306_overlay),
                )
            )
        if (
            userspace_overlay_contract_id
            == typed_evidence.P307_OVERLAY_CONTRACT_ID
        ):
            required_overlays.extend(
                (
                    ("p303", typed_evidence.p303_overlay),
                    ("p304", typed_evidence.p304_overlay),
                    ("p305", typed_evidence.p305_overlay),
                    ("p307", typed_evidence.p307_overlay),
                )
            )
        if (
            userspace_overlay_contract_id
            == typed_evidence.P308_OVERLAY_CONTRACT_ID
        ):
            required_overlays.extend(
                (
                    ("p303", typed_evidence.p303_overlay),
                    ("p304", typed_evidence.p304_overlay),
                    ("p305", typed_evidence.p305_overlay),
                    ("p307", typed_evidence.p307_overlay),
                    ("p308", typed_evidence.p308_overlay),
                )
            )
        for prefix, overlay_module in required_overlays:
            expected_overlay = verification.get(
                f"{prefix}_overlay_source_receipts"
            )
            if (
                not isinstance(expected_overlay, dict)
                or set(expected_overlay) != overlay_module.SOURCE_KEYS
            ):
                raise F1V2Error(
                    f"{prefix.upper()} overlay source binding is incomplete"
                )
            for name, source_receipt in expected_overlay.items():
                actual = execution_sources.get(
                    f"{prefix}_overlay_source_{name}"
                )
                if (
                    not isinstance(actual, dict)
                    or {key: actual.get(key) for key in ("size", "sha256")}
                    != source_receipt
                ):
                    raise F1V2Error(
                        f"{prefix.upper()} overlay source differs from "
                        "execution-critical sources"
                    )
    if source_contract_id == typed_evidence.P298_SOURCE_CONTRACT_ID:
        import s22plus_fyg8_p298_identity_tiers as p298_identity

        expected_repair = verification.get("tier2_repair_files")
        repair_paths = {
            p298_identity.TIER2_DIRECT_PATHS[name].as_posix(): name
            for name in typed_evidence.P298_REPAIR_TIER2_KEYS
        }
        if not isinstance(expected_repair, dict) or set(expected_repair) != set(
            repair_paths
        ):
            raise F1V2Error("P2.98 Tier-2 repair binding is incomplete")
        for path, name in repair_paths.items():
            actual = execution_sources.get(f"p298_tier2_direct_{name}")
            if (
                not isinstance(actual, dict)
                or {key: actual.get(key) for key in ("size", "sha256")}
                != expected_repair[path]
            ):
                raise F1V2Error(
                    "P2.98 Tier-2 repair differs from execution-critical sources"
                )


def verify_candidate_observer_binding(
    acceptance: dict[str, Any],
    observer: dict[str, Any] | None,
) -> None:
    source_contract_id = acceptance.get("source_contract_id")
    profile = acceptance.get("profile")
    stock_overlay = acceptance.get("userspace_overlay_contract_id") in {
        typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P319_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P321_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P322_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P323_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P324_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P325_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
    }
    if source_contract_id is None:
        if observer is not None:
            raise F1V2Error("candidate observer has no versioned source contract")
        return
    selected = _selected_candidate_source_contract(source_contract_id, profile)
    derive = getattr(selected.module, "candidate_observer", None)
    if derive is None:
        if observer is not None:
            raise F1V2Error("source contract does not define a candidate observer")
        return
    if observer is None and not stock_overlay:
        raise F1V2Error("source contract requires a candidate observer")
    if observer is None:
        if (
            acceptance.get("userspace_overlay_contract_id")
            in {
                typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
            }
        ):
            raise F1V2Error("P3.31-P3.40 resident observer is required")
        if (
            acceptance.get("userspace_overlay_contract_id")
            in {
                typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
                typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
            }
        ):
            raise F1V2Error("framed command observer is required")
        return
    run_id_hex = acceptance.get("run_id")
    if not isinstance(run_id_hex, str) or re.fullmatch(r"[0-9a-f]{32}", run_id_hex) is None:
        raise F1V2Error("candidate observer run ID is invalid")
    if acceptance.get("userspace_overlay_contract_id") in {
        typed_evidence.P343_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P342_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P341_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P340_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P339_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P338_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P337_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P335_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P332_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P333_STOCK_OVERLAY_CONTRACT_ID,
        typed_evidence.P334_STOCK_OVERLAY_CONTRACT_ID,
    }:
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    if (
        acceptance.get("userspace_overlay_contract_id")
        == typed_evidence.P331_STOCK_OVERLAY_CONTRACT_ID
    ):
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    if (
        acceptance.get("userspace_overlay_contract_id")
        == typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID
    ):
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    if (
        acceptance.get("userspace_overlay_contract_id")
        == typed_evidence.P329_STOCK_OVERLAY_CONTRACT_ID
    ):
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    if (
        acceptance.get("userspace_overlay_contract_id")
        == typed_evidence.P328_STOCK_OVERLAY_CONTRACT_ID
    ):
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    if (
        acceptance.get("userspace_overlay_contract_id")
        == typed_evidence.P327_STOCK_OVERLAY_CONTRACT_ID
    ):
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    if (
        acceptance.get("userspace_overlay_contract_id")
        == typed_evidence.P326_STOCK_OVERLAY_CONTRACT_ID
    ):
        try:
            typed_evidence.validate_candidate_arrival_proof_role(
                typed_evidence.CANDIDATE_BIDIRECTIONAL_CONSOLE_ROLE,
                observer,
                expected_run_id=run_id_hex,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        return
    try:
        expected = derive(bytes.fromhex(run_id_hex))
    except (TypeError, ValueError) as exc:
        raise F1V2Error("candidate observer derivation failed") from exc
    if observer != expected:
        raise F1V2Error("candidate observer differs from the source contract")


def verify_bundle(
    root: Path,
    manifest_path: Path,
    *,
    runtime_bound: bool = False,
) -> Bundle:
    root = root.resolve()
    manifest_file = manifest_path if manifest_path.is_absolute() else root / manifest_path
    manifest_raw, manifest_receipt = load_json(manifest_file, "candidate manifest")
    profile_file = _repo_path(root, manifest_raw.get("target_profile", ""), "target_profile")
    profile_raw, profile_receipt = load_json(profile_file, "target profile")
    profile = validate_profile(profile_raw)
    manifest = validate_manifest(manifest_raw, profile)
    receipts: dict[str, Any] = {}
    candidate_ap_frame: bytes | None = None
    for label, item in (("candidate_ap", manifest["candidate_ap"]), ("rollback_ap", manifest["rollback_ap"])):
        with pin_boot_only_ap(
            _artifact_path(root, item, label),
            label=label,
            expected_size=item["size"],
            expected_sha256=item["sha256"],
            require_deterministic_metadata=label == "candidate_ap",
        ) as pinned:
            receipts[label] = pinned.receipt()
            if label == "candidate_ap":
                candidate_ap_frame = read_boot_only_member(pinned, label=label)
                receipts[label]["member"] = {
                    "name": BOOT_MEMBER,
                    "size": len(candidate_ap_frame),
                    "sha256": hashlib.sha256(candidate_ap_frame).hexdigest(),
                }
    acceptance = manifest["observation"]["acceptance"]
    candidate_arrival_proof_role = manifest["observation"].get(
        typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY
    )
    verify_candidate_observer_binding(
        acceptance, manifest["observation"].get("candidate_observer")
    )
    execution_sources = execution_critical_source_receipts(
        acceptance,
        candidate_arrival_proof_role=candidate_arrival_proof_role,
        bind_private_inputs=not runtime_bound,
    )
    try:
        contract_items = typed_evidence.contract_artifacts(acceptance)
    except typed_evidence.EvidenceError as exc:
        raise F1V2Error(str(exc)) from exc
    if contract_items:
        contract_payloads: dict[str, bytes] = {}
        contract_receipts: dict[str, dict[str, Any]] = {}
        for name, item in contract_items.items():
            with pin_regular_file(
                _artifact_path(root, item, f"observation contract {name}"),
                label=f"observation contract {name}",
                expected_size=item["size"],
                expected_sha256=item["sha256"],
            ) as pinned:
                os.lseek(pinned.descriptor, 0, os.SEEK_SET)
                chunks: list[bytes] = []
                remaining = pinned.size + 1
                while remaining:
                    chunk = os.read(pinned.descriptor, remaining)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                payload = b"".join(chunks)
                os.lseek(pinned.descriptor, 0, os.SEEK_SET)
                if len(payload) != pinned.size:
                    raise F1V2Error(f"observation contract {name} read is short")
                contract_payloads[name] = payload
                contract_receipts[name] = pinned.receipt()
        try:
            verification = typed_evidence.verify_offline_contract(
                acceptance,
                payloads=contract_payloads,
                receipts=contract_receipts,
                candidate_ap=receipts["candidate_ap"],
                runtime_bound=runtime_bound,
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        verify_p303_campaign_binding(
            acceptance,
            verification,
            manifest_id=manifest["manifest_id"],
            live_run_id=manifest["run_id"],
        )
        receipts["observation_contract"] = {
            "artifacts": contract_receipts,
            "verification": verification,
        }
        verify_candidate_source_binding(
            acceptance, verification, execution_sources
        )
        if acceptance.get("profile") == "E2":
            if candidate_ap_frame is None:
                raise F1V2Error("candidate AP boot member was not retained for E2 audit")
            try:
                typed_evidence.validate_e2_ap_payload(
                    candidate_ap_frame, verification.get("ap_payload_closure")
                )
            except typed_evidence.EvidenceError as exc:
                raise F1V2Error(str(exc)) from exc
    odin = profile["transport"]["odin"]
    with pin_regular_file(
        _artifact_path(root, odin, "odin"),
        label="Odin4",
        expected_size=odin["size"],
        expected_sha256=odin["sha256"],
    ) as pinned:
        if not os.access(pinned.path, os.X_OK):
            raise F1V2Error("pinned Odin4 is not executable")
        receipts["odin"] = pinned.receipt()
    receipt = {
        "schema": "device_action_f1_validated_bundle_v2",
        "runner_version": RUNNER_VERSION,
        "profile": profile_receipt,
        "manifest": manifest_receipt,
        **receipts,
        "execution_critical_sources": execution_sources,
        "device_contact": False,
        "odin_invoked": False,
        "live_authorized": False,
    }
    return Bundle(profile, manifest, receipt, json_sha256(receipt))


def validate_target_evidence(profile: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    _exact(evidence, {"schema", "targets", "odin_endpoint_absent"}, "target evidence")
    if evidence["schema"] != TARGET_EVIDENCE_SCHEMA or evidence["odin_endpoint_absent"] is not True:
        raise F1V2Error("target evidence header is invalid")
    if not isinstance(evidence["targets"], list) or len(evidence["targets"]) != 1:
        raise F1V2Error("target evidence must contain exactly one target")
    target = _exact(evidence["targets"][0], {"model", "device", "firmware_incremental", "android_transport", "adb_serial_sha256", "usb_topology_sha256"}, "target evidence target")
    for key in ("model", "device", "firmware_incremental", "android_transport"):
        if target[key] != profile["target"][key]:
            raise F1V2Error(f"target evidence mismatch: {key}")
    _digest(target["adb_serial_sha256"], "adb serial digest")
    _digest(target["usb_topology_sha256"], "USB topology digest")
    return evidence


def approval_binding(bundle: Bundle, evidence: dict[str, Any]) -> tuple[dict[str, Any], str]:
    validate_target_evidence(bundle.profile, evidence)
    value = {
        "schema": "device_action_f1_approval_binding_v2",
        "runner_version": RUNNER_VERSION,
        "profile_id": bundle.profile["profile_id"],
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "target_evidence_sha256": json_sha256(evidence),
        "candidate_ap_sha256": bundle.manifest["candidate_ap"]["sha256"],
        "rollback_ap_sha256": bundle.manifest["rollback_ap"]["sha256"],
        "observation": bundle.manifest["observation"],
        "rollback_preapproved": True,
    }
    role = bundle.manifest["observation"].get(
        typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY
    )
    if role is not None:
        value[typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY] = role
    return value, json_sha256(value)


def classify_odin_output(returncode: int, stdout: bytes, stderr: bytes) -> str:
    output = stdout + b"\n" + stderr
    session_markers = (
        b"Setup Connection",
        b"initializeConnection",
        b"Receive PIT Info",
        b"Upload Binaries",
        b"Close Connection",
    )
    if b"Fail parse" in output and not any(marker in output for marker in session_markers):
        return "odin_local_parse_failure"
    completed_markers = (
        b"Setup Connection",
        b"Upload Binaries",
        b"boot.img.lz4",
        b"100%",
        b"Close Connection",
    )
    if returncode == 0 and all(marker in output for marker in completed_markers):
        return "odin_transfer_completed"
    return "odin_device_session_failure_or_unknown"


def _write_exclusive_bounded(path: Path, value: Any, limit: int) -> None:
    if type(limit) is not int or limit not in {MAX_RECORD, MAX_RESULT_RECORD}:
        raise F1V2Error("durable record bound is invalid")
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(payload) > limit:
        raise F1V2Error("durable record exceeds its bound")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        if os.write(descriptor, payload) != len(payload):
            raise F1V2Error("short durable record write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


def _write_exclusive(path: Path, value: Any) -> None:
    _write_exclusive_bounded(path, value, MAX_RECORD)


def _write_atomic_bounded(path: Path, value: Any, limit: int) -> None:
    if path.is_symlink():
        raise F1V2Error("durable head cannot be a symlink")
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    _write_exclusive_bounded(temporary, value, limit)
    os.replace(temporary, path)
    _fsync_dir(path.parent)


def _write_atomic(path: Path, value: Any) -> None:
    _write_atomic_bounded(path, value, MAX_RECORD)


def _write_live_result(path: Path, value: Any) -> None:
    """Publish only the canonical terminal result under the 64 KiB bound."""
    if path.name != "live-result.json":
        raise F1V2Error("extended durable bound is limited to live-result.json")
    _write_atomic_bounded(path, value, MAX_RESULT_RECORD)


def _record_hash(record: dict[str, Any]) -> str:
    unsigned = dict(record)
    unsigned.pop("record_sha256", None)
    return json_sha256(unsigned)


def _validate_checkpoint(
    action: str,
    outcome: str,
    details: dict[str, Any],
    attempts: dict[str, int],
) -> None:
    if action == "download_request_revalidation":
        item = _exact(
            details,
            {"reason", "error_type", "error_sha256"},
            "Download request revalidation checkpoint details",
        )
        if (
            outcome != "parked"
            or attempts.get(action, 0) != 0
            or not isinstance(item["reason"], str)
            or not item["reason"]
            or not isinstance(item["error_type"], str)
            or not item["error_type"]
            or not isinstance(item["error_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", item["error_sha256"]) is None
        ):
            raise F1V2Error("Download request revalidation checkpoint is invalid")
        attempts[action] = 1
        return
    if outcome != "attempt_started":
        raise F1V2Error("journal checkpoint outcome is invalid")
    item = _exact(details, {"attempt", "start"}, "journal checkpoint details")
    attempt = item["attempt"]
    expected = attempts.get(action, 0) + 1
    if (
        isinstance(attempt, bool)
        or not isinstance(attempt, int)
        or attempt != expected
        or attempt > MAX_TRANSFER_ATTEMPTS
    ):
        raise F1V2Error("journal checkpoint attempt sequence is invalid")
    _artifact(item["start"], "journal checkpoint start")
    attempts[action] = attempt


class Journal:
    def __init__(self, run_dir: Path, binding_sha256: str):
        self.run_dir = run_dir.absolute()
        self.directory = self.run_dir / "journal"
        self.head_path = self.run_dir / "journal-head.json"
        self.binding_sha256 = _digest(binding_sha256, "journal binding")

    @classmethod
    def create(
        cls,
        run_dir: Path,
        binding_sha256: str,
        preflight_details: dict[str, Any] | None = None,
    ) -> "Journal":
        journal = cls(run_dir, binding_sha256)
        if journal.run_dir.exists() or journal.run_dir.is_symlink():
            raise F1V2Error("run directory already exists")
        journal.directory.mkdir(parents=True, mode=0o700)
        _fsync_dir(journal.run_dir.parent)
        journal.transition(
            "PREFLIGHT",
            "ok",
            preflight_details or {"host_only": True},
        )
        return journal

    @classmethod
    def reopen(cls, run_dir: Path, binding_sha256: str) -> "Journal":
        journal = cls(run_dir, binding_sha256)
        if journal.run_dir.is_symlink() or not journal.directory.is_dir():
            raise F1V2Error("journal directory is unavailable")
        records = journal.records()
        if records:
            journal._write_head(records[-1])
        return journal

    def _head_count(self, records: list[dict[str, Any]]) -> int:
        if not records:
            if self.head_path.exists() or self.head_path.is_symlink():
                raise F1V2Error("journal head exists without records")
            return 0
        if not self.head_path.exists() or self.head_path.is_symlink():
            raise F1V2Error("journal head is missing or indirect")
        head, _receipt = load_json(self.head_path, "journal head")
        _exact(
            head,
            {
                "schema",
                "binding_sha256",
                "record_count",
                "last_sequence",
                "last_record_sha256",
            },
            "journal head",
        )
        count = head["record_count"]
        if (
            head["schema"] != JOURNAL_HEAD_SCHEMA
            or head["binding_sha256"] != self.binding_sha256
            or isinstance(count, bool)
            or not isinstance(count, int)
            or not 1 <= count <= len(records)
            or head["last_sequence"] != count - 1
            or head["last_record_sha256"] != records[count - 1]["record_sha256"]
        ):
            raise F1V2Error("journal head does not match the durable chain")
        return count

    def _write_head(self, record: dict[str, Any]) -> None:
        _write_atomic(
            self.head_path,
            {
                "schema": JOURNAL_HEAD_SCHEMA,
                "binding_sha256": self.binding_sha256,
                "record_count": record["sequence"] + 1,
                "last_sequence": record["sequence"],
                "last_record_sha256": record["record_sha256"],
            },
        )

    def records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        state: str | None = None
        previous = "0" * 64
        events: list[str] = []
        checkpoint_attempts: dict[str, int] = {}
        paths = sorted(self.directory.glob("*.json"))
        for sequence, path in enumerate(paths):
            value, _receipt = load_json(path, f"journal record {sequence}")
            _exact(value, {"schema", "sequence", "timestamp_utc", "kind", "state", "action", "outcome", "details", "binding_sha256", "previous_record_sha256", "record_sha256"}, f"journal record {sequence}")
            prefix = f"{sequence:04d}-"
            if not path.name.startswith(prefix) or value["schema"] != JOURNAL_SCHEMA or value["sequence"] != sequence:
                raise F1V2Error(f"journal record {sequence} identity mismatch")
            if value["binding_sha256"] != self.binding_sha256 or value["previous_record_sha256"] != previous or value["record_sha256"] != _record_hash(value):
                raise F1V2Error(f"journal record {sequence} chain mismatch")
            if value["kind"] == "transition":
                if value["state"] not in NEXT_STATES[state] or value["action"] != STATE_ACTION[value["state"]]:
                    raise F1V2Error(f"journal transition {sequence} is invalid")
                state = value["state"]
            elif value["kind"] == "event":
                if value["state"] != state or EVENT_STATE.get(value["action"]) != state:
                    raise F1V2Error(f"journal event {sequence} is invalid")
                order = (
                    RECOVERY_TIMELINE
                    if state in RECOVERY_EVENT_STATES
                    and "candidate_flash_start" not in events
                    else TIMELINE
                )
                if len(events) >= len(order) or order[len(events)] != value["action"]:
                    raise F1V2Error(f"journal timeline {sequence} is out of order")
                events.append(value["action"])
            elif value["kind"] == "checkpoint":
                if (
                    value["state"] != state
                    or CHECKPOINT_STATE.get(value["action"]) != state
                ):
                    raise F1V2Error(f"journal checkpoint {sequence} is invalid")
                _validate_checkpoint(
                    value["action"],
                    value["outcome"],
                    value["details"],
                    checkpoint_attempts,
                )
            else:
                raise F1V2Error(f"journal record {sequence} kind is invalid")
            previous = value["record_sha256"]
            records.append(value)
        self._head_count(records)
        return records

    def state(self) -> str | None:
        transitions = [r["state"] for r in self.records() if r["kind"] == "transition"]
        return transitions[-1] if transitions else None

    def _append(self, kind: str, state: str, action: str, outcome: str, details: dict[str, Any]) -> None:
        records = self.records()
        current = next((r["state"] for r in reversed(records) if r["kind"] == "transition"), None)
        events = [r["action"] for r in records if r["kind"] == "event"]
        checkpoint_attempts: dict[str, int] = {}
        for record in records:
            if record["kind"] == "checkpoint":
                checkpoint_attempts[record["action"]] = (
                    1
                    if record["action"] == "download_request_revalidation"
                    else record["details"]["attempt"]
                )
        if kind == "transition":
            if state not in NEXT_STATES[current] or action != STATE_ACTION[state]:
                raise F1V2Error(f"invalid transition: {current} -> {state}")
        elif kind == "event":
            order = (
                RECOVERY_TIMELINE
                if current in RECOVERY_EVENT_STATES
                and "candidate_flash_start" not in events
                else TIMELINE
            )
            if (
                len(events) >= len(order)
                or state != current
                or EVENT_STATE.get(action) != state
                or order[len(events)] != action
            ):
                raise F1V2Error(f"invalid timeline event: {action}")
        elif kind == "checkpoint":
            if state != current or CHECKPOINT_STATE.get(action) != state:
                raise F1V2Error(f"invalid journal checkpoint: {action}")
            _validate_checkpoint(action, outcome, details, checkpoint_attempts)
        else:
            raise F1V2Error("invalid journal record kind")
        previous = records[-1]["record_sha256"] if records else "0" * 64
        record = {
            "schema": JOURNAL_SCHEMA,
            "sequence": len(records),
            "timestamp_utc": utc_now(),
            "kind": kind,
            "state": state,
            "action": action,
            "outcome": _text(outcome, "journal outcome", 96),
            "details": details,
            "binding_sha256": self.binding_sha256,
            "previous_record_sha256": previous,
        }
        record["record_sha256"] = _record_hash(record)
        filename = f"{len(records):04d}-{kind}-{action}.json"
        _write_exclusive(self.directory / filename, record)
        self._write_head(record)

    def transition(self, state: str, outcome: str, details: dict[str, Any]) -> None:
        self._append("transition", state, STATE_ACTION[state], outcome, details)

    def event(self, name: str, details: dict[str, Any] | None = None) -> None:
        state = self.state()
        if state is None:
            raise F1V2Error("journal has no state")
        self._append("event", state, name, "recorded", details or {})

    def checkpoint(
        self, name: str, outcome: str, details: dict[str, Any] | None = None
    ) -> None:
        state = self.state()
        if state is None:
            raise F1V2Error("journal has no state")
        self._append("checkpoint", state, name, outcome, details or {})

    def receipt(self) -> dict[str, Any]:
        records = self.records()
        return {
            "path": str(self.directory),
            "head_path": str(self.head_path),
            "record_count": len(records),
            "last_record_sha256": records[-1]["record_sha256"] if records else "0" * 64,
        }


def timeline(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "events": [
            {"name": record["action"], "timestamp_utc": record["timestamp_utc"]}
            for record in records
            if record["kind"] == "event"
        ]
    }


def _simulated_evidence(bundle: Bundle) -> dict[str, Any]:
    target = bundle.profile["target"]
    return {
        "schema": TARGET_EVIDENCE_SCHEMA,
        "targets": [{
            "model": target["model"],
            "device": target["device"],
            "firmware_incremental": target["firmware_incremental"],
            "android_transport": target["android_transport"],
            "adb_serial_sha256": hashlib.sha256(b"simulation-adb").hexdigest(),
            "usb_topology_sha256": hashlib.sha256(b"simulation-usb").hexdigest(),
        }],
        "odin_endpoint_absent": True,
    }


def _result(bundle: Bundle, journal: Journal, scenario: str, verdict: str, outcome: str, resumed: bool = False) -> dict[str, Any]:
    result = {
        "schema": RESULT_SCHEMA,
        "runner_version": RUNNER_VERSION,
        "mode": "host-only-simulation",
        "scenario": scenario,
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "approval_binding_sha256": journal.binding_sha256,
        "journal": journal.receipt(),
        "current_state": journal.state(),
        "timeline": timeline(journal.records()),
        "verdict": verdict,
        "outcome_class": outcome,
        "resumed": resumed,
        "device_contact": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "live_authorized": False,
    }
    _write_exclusive(journal.run_dir / "result.json", result)
    return result


def simulate(bundle: Bundle, scenario: str, run_dir: Path) -> dict[str, Any]:
    if scenario not in {"happy-path", "local-parse-failure", "candidate-timeout", "interrupted-result"}:
        raise F1V2Error("unknown simulation scenario")
    approval, approval_hash = approval_binding(bundle, _simulated_evidence(bundle))
    journal = Journal.create(run_dir, approval_hash)
    journal.event("live_session_start", {"simulation": True})
    journal.transition("APPROVED", "simulated", {"approval_binding_sha256": approval_hash, "rollback_preapproved": approval["rollback_preapproved"]})
    journal.transition("DOWNLOAD_IDENTIFIED", "simulated", {"target_count": 1})
    journal.event("candidate_flash_start", {"simulation": True})
    if scenario == "local-parse-failure":
        outcome = classify_odin_output(1, b"Fail parse /tmp/AP.tar.md5\n", b"")
        journal.transition("ABORTED", outcome, {"device_session_started": False, "partition_transfer": False})
        return _result(bundle, journal, scenario, "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION", outcome)
    journal.transition("CANDIDATE_FLASHED", "simulated", {"transfer": "not-executed"})
    journal.event("candidate_flash_done", {"simulation": True})
    timed_out = scenario == "candidate-timeout"
    journal.transition("OBSERVED", "candidate_timeout" if timed_out else "simulated", {"timed_out": timed_out})
    journal.event("candidate_boot_ready", {"proof": not timed_out, "simulated": True})
    journal.transition("RECOVERY_DOWNLOAD", "simulated", {"physical_entry": "simulated"})
    journal.event("rollback_flash_start", {"simulation": True})
    journal.transition("ROLLBACK_FLASHED", "simulated", {"transfer": "not-executed"})
    journal.event("rollback_flash_done", {"simulation": True})
    journal.transition("HEALTH_VERIFIED", "simulated", {"healthy": True})
    journal.event("rollback_boot_ready", {"simulation": True})
    journal.event("live_session_end", {"simulation": True})
    resumed = scenario == "interrupted-result"
    if resumed:
        journal = Journal.reopen(run_dir, approval_hash)
        if journal.state() != "HEALTH_VERIFIED":
            raise F1V2Error("resume state mismatch")
    journal.transition("CLOSED", "simulated", {"resumed": resumed})
    if timed_out:
        return _result(bundle, journal, scenario, "NO_PROOF_F1_V2_CANDIDATE_TIMEOUT_ROLLED_BACK", "candidate_timeout_rolled_back")
    return _result(bundle, journal, scenario, "PASS_F1_V2_HOST_ONLY_SIMULATION", "simulated_complete", resumed)


def render_plan(bundle: Bundle) -> dict[str, Any]:
    return {
        "schema": "device_action_f1_plan_v2",
        "runner_version": RUNNER_VERSION,
        "manifest_id": bundle.manifest["manifest_id"],
        "status": bundle.manifest["status"],
        "bundle_sha256": bundle.sha256,
        "target_profile": bundle.profile["profile_id"],
        "candidate_ap": bundle.receipt["candidate_ap"],
        "rollback_ap": bundle.receipt["rollback_ap"],
        "odin": bundle.receipt["odin"],
        "state_machine": list(STATES),
        "approval_required": True,
        "rollback_preapproved_by_f1_approval": True,
        "target_evidence_required": True,
        "regular_path_inputs": True,
        "device_contact": False,
        "odin_invoked": False,
        "live_authorized": False,
    }


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    base.mkdir(parents=True, exist_ok=True)
    path = requested or base / f"simulation-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    path = path if path.is_absolute() else root / path
    path = path.resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise F1V2Error("run directory is outside the private v2 root") from exc
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--simulate", choices=("happy-path", "local-parse-failure", "candidate-timeout", "interrupted-result"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--run-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        bundle = verify_bundle(root, args.manifest)
        if args.validate:
            result = {
                "schema": "device_action_f1_host_preflight_v2",
                "runner_version": RUNNER_VERSION,
                "bundle": bundle.receipt,
                "bundle_sha256": bundle.sha256,
                "verdict": "PASS_DEVICE_ACTION_F1_V2_HOST_PREFLIGHT",
                "device_contact": False,
                "odin_invoked": False,
                "live_authorized": False,
            }
        elif args.render_plan:
            result = render_plan(bundle)
        else:
            result = simulate(bundle, args.simulate, allocate_run_dir(root, args.run_dir))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (F1V2Error, F1TransportError, OSError) as exc:
        print(f"Device Action F1 v2 error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
