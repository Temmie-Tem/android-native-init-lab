#!/usr/bin/env python3
"""Typed observation contracts for Device Action Process v2."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint


MARKER_KIND = "retained_marker_after_rollback"
CHECKPOINT_KIND = "retained_checkpoint_after_rollback"
CHECKPOINT_DECODER = "s22plus_fyg8_r4w1e_checkpoint_v1"
CHECKPOINT_SOURCE = "/proc/last_kmsg"
OUTCOME_NAMES = {
    checkpoint.OUTCOME_PROGRESS: "progress",
    checkpoint.OUTCOME_SUCCESS: "success",
    checkpoint.OUTCOME_FAILURE: "failure",
}
HEX32_RE = re.compile(r"[0-9a-f]{32}")
HASH_RE = re.compile(r"[0-9a-f]{64}")


class EvidenceError(ValueError):
    pass


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise EvidenceError(f"{label} keys do not match the evidence schema")
    return value


def _artifact(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"path", "size", "sha256"}, label)
    if (
        not isinstance(item["path"], str)
        or not item["path"]
        or isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 1024 * 1024
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _bounded_text(value: Any, label: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or "\x00" in value
    ):
        raise EvidenceError(f"{label} must be a bounded string")
    return value


def validate_acceptance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError("acceptance must be an object")
    kind = value.get("kind")
    if kind == MARKER_KIND:
        item = _exact(
            value,
            {"kind", "source", "marker", "family", "exact_count"},
            "marker acceptance",
        )
        if item["source"] != CHECKPOINT_SOURCE or item["exact_count"] != 1:
            raise EvidenceError("marker acceptance source or count is invalid")
        _bounded_text(item["marker"], "acceptance.marker", 512)
        _bounded_text(item["family"], "acceptance.family", 128)
        return item
    if kind != CHECKPOINT_KIND:
        raise EvidenceError("acceptance kind is not allowlisted")

    item = _exact(
        value,
        {
            "kind",
            "source",
            "marker",
            "family",
            "exact_count",
            "decoder",
            "profile",
            "run_id",
            "terminal_stage",
            "terminal_outcome",
            "require_two_valid_slots",
            "contract",
        },
        "checkpoint acceptance",
    )
    if (
        item["source"] != CHECKPOINT_SOURCE
        or item["marker"] != checkpoint.ENTRY_PROOF.decode("ascii")
        or item["family"] != checkpoint.ENTRY_FAMILY.decode("ascii")
        or item["exact_count"] != 1
        or item["decoder"] != CHECKPOINT_DECODER
        or item["profile"] != "E1"
        or item["terminal_stage"] != checkpoint.PROFILE_TERMINAL_STAGE["E1"]
        or item["terminal_outcome"] != "success"
        or item["require_two_valid_slots"] is not True
        or not isinstance(item["run_id"], str)
        or HEX32_RE.fullmatch(item["run_id"]) is None
        or item["run_id"] == "0" * 32
        or item["run_id"]
        == checkpoint.MODEL_RUN_IDS["E1"].hex()
    ):
        raise EvidenceError("checkpoint acceptance identity is invalid")
    contract = _exact(
        item["contract"], {"run_manifest", "static_check"}, "checkpoint contract"
    )
    _artifact(contract["run_manifest"], "checkpoint contract run_manifest")
    _artifact(contract["static_check"], "checkpoint contract static_check")
    return item


def contract_artifacts(acceptance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        return {}
    return {
        name: dict(value)
        for name, value in item["contract"].items()
    }


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError(f"duplicate evidence JSON key: {key}")
        value[key] = item
    return value


def _json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} is not an object")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise EvidenceError("run manifest is not canonical ASCII JSON") from exc


def verify_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("offline checkpoint contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline checkpoint contract artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline checkpoint contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    run_id = canonical_sha256[:32]
    if (
        run_manifest.get("schema")
        != "s22plus_fyg8_r4w1e_e1_run_manifest_v1"
        or run_manifest.get("target") != checkpoint.TARGET
        or run_manifest.get("profile") != item["profile"]
        or run_manifest.get("checkpoint_carrier_sha256")
        != checkpoint.CARRIER_SHA256
        or run_manifest.get("checkpoint_patch_sha256") != checkpoint.PATCH_SHA256
        or run_id != item["run_id"]
    ):
        raise EvidenceError("run manifest does not bind the checkpoint acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e_e1_candidate_static_checker_v1"
        or static_result.get("target") != checkpoint.TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E_E1_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["run_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fresh_non_model_id") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or artifacts.get("ap", {}).get("size") != candidate_ap.get("size")
        or artifacts.get("ap", {}).get("sha256") != candidate_ap.get("sha256")
        or artifacts.get("run_manifest", {}).get("size")
        != receipts["run_manifest"].get("size")
        or artifacts.get("run_manifest", {}).get("sha256")
        != receipts["run_manifest"].get("sha256")
        or candidate.get("boot_only_ap") is not True
        or not isinstance(safety, dict)
        or safety.get("host_only") is not True
        or any(
            safety.get(key) is not False
            for key in (
                "device_contact",
                "device_write",
                "odin_invoked",
                "odin_transfer",
                "flash",
                "partition_write",
                "live_authorized",
            )
        )
    ):
        raise EvidenceError("static checker result does not bind the candidate")
    return {
        "schema": "device_action_f1_checkpoint_offline_contract_v2",
        "decoder": item["decoder"],
        "profile": item["profile"],
        "run_id": item["run_id"],
        "terminal_stage": item["terminal_stage"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "verified": True,
    }


def _base_classification(
    *,
    classification: str,
    exact_count: int,
    family_count: int,
    integrity_issue: bool,
) -> dict[str, Any]:
    return {
        "classification": classification,
        "exact_count": exact_count,
        "exact_record_count": exact_count,
        "family_count": family_count,
        "foreign_count": max(0, family_count - exact_count),
        "foreign_records_hex": [],
        "unterminated_offsets": [],
        "delimiter_mismatch_count": 0,
        "partial_at_head": False,
        "partial_at_tail": False,
        "historical_family_count": 0,
        "integrity_issue": integrity_issue,
        "baseline_absent": family_count == 0 and exact_count == 0,
        "acceptance_present": False,
        "accepted": False,
        "checkpoint": None,
    }


def classify_checkpoint(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != CHECKPOINT_KIND:
        raise EvidenceError("checkpoint classifier received another evidence kind")
    marker = checkpoint.ENTRY_PROOF
    family = checkpoint.ENTRY_FAMILY
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    prefix_counts = [payload.count(prefix) for prefix in checkpoint.ENTRY_PREFIXES]
    partial_head = any(
        payload.startswith(marker[-length:])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if not any(prefix_counts) and exact_count == 0 and not partial_head and not partial_tail:
        return _base_classification(
            classification="CHECKPOINT_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    if (
        exact_count != item["exact_count"]
        or family_count != item["exact_count"]
        or any(count != item["exact_count"] for count in prefix_counts)
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="CHECKPOINT_FAMILY_INTEGRITY_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
        return result

    position = payload.index(marker)
    region = payload[position : position + checkpoint.REGION_SIZE]
    try:
        decoded = checkpoint.decode_region(
            region,
            item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except checkpoint.CheckError as exc:
        result = _base_classification(
            classification="CHECKPOINT_DECODE_FAILURE",
            exact_count=exact_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["checkpoint"] = {"error": str(exc), "observer_offset": position}
        return result

    active = decoded["active"]
    outcome_name = OUTCOME_NAMES.get(active["outcome"], "unknown")
    two_slots = len(decoded["valid_slots"]) == 2
    accepted = (
        decoded["terminal"] is True
        and active["stage"] == item["terminal_stage"]
        and outcome_name == item["terminal_outcome"]
        and (two_slots or item["require_two_valid_slots"] is not True)
    )
    if accepted:
        classification = "CHECKPOINT_TERMINAL_SUCCESS"
    elif decoded["terminal"] and outcome_name == "failure":
        classification = "CHECKPOINT_TERMINAL_FAILURE"
    elif decoded["terminal"]:
        classification = "CHECKPOINT_TERMINAL_MISMATCH"
    else:
        classification = "CHECKPOINT_PROGRESS_ONLY"
    result = _base_classification(
        classification=classification,
        exact_count=exact_count,
        family_count=family_count,
        integrity_issue=False,
    )
    result["acceptance_present"] = accepted
    result["accepted"] = accepted
    result["checkpoint"] = {
        **decoded,
        "observer_offset": position,
        "outcome_name": outcome_name,
        "two_valid_slots": two_slots,
        "boot_identity_self_consistent": two_slots,
    }
    return result
