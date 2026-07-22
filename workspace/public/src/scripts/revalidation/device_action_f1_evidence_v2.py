#!/usr/bin/env python3
"""Typed observation contracts for Device Action Process v2."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import s22plus_fyg8_r4w1e_checkpoint_contract as checkpoint
import s22plus_fyg8_p219_same_ring_decoder as same_ring
import s22plus_fyg8_p230_same_ring_multiboot_decoder as same_ring_multiboot
import s22plus_fyg8_p233_e1_decoder as e1_latest_stage


MARKER_KIND = "retained_marker_after_rollback"
CHECKPOINT_KIND = "retained_checkpoint_after_rollback"
PID1_USERSPACE_KIND = "retained_pid1_userspace_after_rollback"
SAME_RING_KIND = "retained_pid1_same_ring_discriminator_after_rollback"
SAME_RING_MULTIBOOT_KIND = (
    "retained_pid1_same_ring_multiboot_discriminator_after_rollback"
)
E1_LATEST_STAGE_KIND = "retained_e1_latest_stage_multiboot_after_rollback"
CHECKPOINT_DECODER = "s22plus_fyg8_r4w1e_checkpoint_v1"
PID1_USERSPACE_DECODER = "s22plus_fyg8_r4w1e0_pid1_userspace_v1"
SAME_RING_DECODER = "s22plus_fyg8_p219_same_ring_v1"
SAME_RING_MULTIBOOT_DECODER = "s22plus_fyg8_p230_same_ring_multiboot_v1"
E1_LATEST_STAGE_DECODER = e1_latest_stage.DECODER_ID
CHECKPOINT_SOURCE = "/proc/last_kmsg"
PID1_USERSPACE_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PID1_USERSPACE_ENTRY = b"\n[[S22P1U|ba234c7de4105b2a23222436284605f2]]\n"
PID1_USERSPACE_PROOF = b"\n[[S22P1U|ec8d029b05288644bbe7b5f7c7af190c]]\n"
PID1_USERSPACE_FAMILY = b"[[S22P1U|"
PID1_USERSPACE_PROBE_ID = "64554e8469385878c5bf8d57c44edeea"
SAME_RING_CONTRACT_ID = same_ring.CONTRACT_ID.hex()
SAME_RING_MULTIBOOT_POLICY_ID = same_ring_multiboot.POLICY_ID.hex()
SAME_RING_RUN_MANIFEST_SCHEMA = "s22plus_fyg8_p219_run_manifest_v1"
SAME_RING_STATIC_SCHEMA = "s22plus_fyg8_p219_candidate_static_checker_v1"
SAME_RING_STATIC_VERDICT = "PASS_P219_OFFLINE_CANDIDATE_STATIC_CONTRACT"
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


def _artifact_matches(value: Any, expected: dict[str, Any]) -> bool:
    return (
        isinstance(value, dict)
        and value.get("size") == expected.get("size")
        and value.get("sha256") == expected.get("sha256")
    )


def _binary_identity(value: Any, label: str) -> dict[str, Any]:
    item = _exact(value, {"size", "sha256"}, label)
    if (
        isinstance(item["size"], bool)
        or not isinstance(item["size"], int)
        or not 1 <= item["size"] <= 2**40
        or not isinstance(item["sha256"], str)
        or HASH_RE.fullmatch(item["sha256"]) is None
    ):
        raise EvidenceError(f"{label} identity is invalid")
    return item


def _record_blob_claim(
    value: Any, label: str, artifact: dict[str, Any]
) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "label",
            "size",
            "sha256",
            "entry_count",
            "userspace_count",
            "unsat_count",
            "long_family_count",
            "unsat_family_count",
            "old_e0_entry_count",
            "old_e0_userspace_count",
            "verified",
        },
        label,
    )
    expected_counts = {
        "entry_count": 1,
        "userspace_count": 1,
        "unsat_count": 1,
        "long_family_count": 2,
        "unsat_family_count": 1,
        "old_e0_entry_count": 0,
        "old_e0_userspace_count": 0,
    }
    if (
        item["label"] != label
        or not _artifact_matches(item, artifact)
        or any(item[key] != count for key, count in expected_counts.items())
        or item["verified"] is not True
    ):
        raise EvidenceError(f"{label} record claim is invalid")
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
    if kind == SAME_RING_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "records",
                "families",
                "accepted_identity",
                "exact_count",
                "contract",
            },
            "same-ring acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"] != "USERSPACE_CALLBACK_REACHED"
            or item["exact_count"] != 1
        ):
            raise EvidenceError("same-ring acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring contract",
        )
        _artifact(contract["run_manifest"], "same-ring contract run_manifest")
        _artifact(contract["static_check"], "same-ring contract static_check")
        return item
    if kind == SAME_RING_MULTIBOOT_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "contract_id",
                "policy_id",
                "records",
                "families",
                "accepted_identity",
                "minimum_exact_count",
                "contract",
            },
            "same-ring multiboot acceptance",
        )
        expected_records = {
            "entry_hex": same_ring.ENTRY_PROOF.hex(),
            "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
            "unsat_hex": same_ring.UNSAT_PROOF.hex(),
        }
        expected_families = {
            "long_hex": same_ring.ENTRY_FAMILY.hex(),
            "unsat_hex": same_ring.UNSAT_FAMILY.hex(),
        }
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != SAME_RING_MULTIBOOT_DECODER
            or item["contract_id"] != SAME_RING_CONTRACT_ID
            or item["policy_id"] != SAME_RING_MULTIBOOT_POLICY_ID
            or item["records"] != expected_records
            or item["families"] != expected_families
            or item["accepted_identity"]
            != "USERSPACE_CALLBACK_REACHED_ONE_OR_MORE_BOOTS"
            or item["minimum_exact_count"] != 1
        ):
            raise EvidenceError("same-ring multiboot acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "same-ring multiboot contract",
        )
        _artifact(
            contract["run_manifest"],
            "same-ring multiboot contract run_manifest",
        )
        _artifact(
            contract["static_check"],
            "same-ring multiboot contract static_check",
        )
        return item
    if kind == E1_LATEST_STAGE_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "decoder",
                "policy_id",
                "profile",
                "run_id",
                "long_family_hex",
                "unsat_family_hex",
                "terminal_stage",
                "minimum_success_count",
                "clean_baseline_required",
                "contract",
            },
            "E1 latest-stage acceptance",
        )
        profile = item["profile"]
        model = e1_latest_stage.model
        model_ids = {model.model_run_id(name).hex() for name in model.PROFILE_NUMBERS}
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["decoder"] != E1_LATEST_STAGE_DECODER
            or item["policy_id"] != e1_latest_stage.POLICY_ID
            or profile not in model.PROFILE_NUMBERS
            or not isinstance(item["run_id"], str)
            or HEX32_RE.fullmatch(item["run_id"]) is None
            or item["run_id"] == "0" * 32
            or item["run_id"] in model_ids
            or item["long_family_hex"] != model.LONG_FAMILY.hex()
            or item["unsat_family_hex"] != model.UNSAT_FAMILY.hex()
            or item["terminal_stage"] != model.PROFILE_TERMINALS.get(profile)
            or item["minimum_success_count"] != 1
            or item["clean_baseline_required"] is not True
        ):
            raise EvidenceError("E1 latest-stage acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "E1 latest-stage contract",
        )
        _artifact(contract["run_manifest"], "E1 latest-stage run_manifest")
        _artifact(contract["static_check"], "E1 latest-stage static_check")
        return item
    if kind == PID1_USERSPACE_KIND:
        item = _exact(
            value,
            {
                "kind",
                "source",
                "marker",
                "family",
                "exact_count",
                "decoder",
                "probe_id",
                "entry_marker",
                "contract",
            },
            "PID1 userspace acceptance",
        )
        if (
            item["source"] != CHECKPOINT_SOURCE
            or item["marker"] != PID1_USERSPACE_PROOF.decode("ascii")
            or item["entry_marker"] != PID1_USERSPACE_ENTRY.decode("ascii")
            or item["family"] != PID1_USERSPACE_FAMILY.decode("ascii")
            or item["exact_count"] != 1
            or item["decoder"] != PID1_USERSPACE_DECODER
            or item["probe_id"] != PID1_USERSPACE_PROBE_ID
        ):
            raise EvidenceError("PID1 userspace acceptance identity is invalid")
        contract = _exact(
            item["contract"],
            {"run_manifest", "static_check"},
            "PID1 userspace contract",
        )
        _artifact(contract["run_manifest"], "PID1 userspace contract run_manifest")
        _artifact(contract["static_check"], "PID1 userspace contract static_check")
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
    if item["kind"] not in {
        CHECKPOINT_KIND,
        PID1_USERSPACE_KIND,
        SAME_RING_KIND,
        SAME_RING_MULTIBOOT_KIND,
        E1_LATEST_STAGE_KIND,
    }:
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


def _verify_checkpoint_offline_contract(
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
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
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


def _verify_pid1_userspace_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("offline PID1 userspace contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline PID1 userspace artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline PID1 userspace contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "run manifest")
    static_result = _json(payloads["static_check"], "static checker result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    observation = run_manifest.get("observation_contract")
    if (
        run_manifest.get("schema") != "s22plus_fyg8_r4w1e0_run_manifest_v1"
        or run_manifest.get("target") != PID1_USERSPACE_TARGET
        or run_manifest.get("profile") != "E0"
        or run_manifest.get("probe_id") != item["probe_id"]
        or run_manifest.get("entry_proof")
        != PID1_USERSPACE_ENTRY.decode("ascii").strip()
        or run_manifest.get("userspace_proof")
        != PID1_USERSPACE_PROOF.decode("ascii").strip()
        or observation
        != {
            "accepted_identity": "USERSPACE_CALLBACK_REACHED",
            "baseline_family_count": 0,
            "post_family_count": 1,
        }
    ):
        raise EvidenceError("run manifest does not bind PID1 userspace acceptance")

    binding = static_result.get("run_binding")
    candidate = static_result.get("candidate")
    artifacts = candidate.get("artifacts") if isinstance(candidate, dict) else None
    blockers = static_result.get("blockers")
    safety = static_result.get("safety")
    if (
        static_result.get("schema")
        != "s22plus_fyg8_r4w1e0_candidate_static_checker_v1"
        or static_result.get("target") != PID1_USERSPACE_TARGET
        or static_result.get("verdict")
        != "PASS_R4W1E0_OFFLINE_CANDIDATE_STATIC_CONTRACT"
        or blockers != []
        or not isinstance(binding, dict)
        or binding.get("run_id") != item["probe_id"]
        or binding.get("canonical_manifest_size") != len(canonical)
        or binding.get("canonical_manifest_sha256") != canonical_sha256
        or binding.get("fixed_probe_id") is not True
        or binding.get("clean_baseline_required") is not True
        or binding.get("verified") is not True
        or not isinstance(artifacts, dict)
        or not _artifact_matches(artifacts.get("ap"), candidate_ap)
        or not _artifact_matches(
            artifacts.get("run_manifest"), receipts["run_manifest"]
        )
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
        raise EvidenceError("static checker result does not bind E0 candidate")
    return {
        "schema": "device_action_f1_pid1_userspace_offline_contract_v2",
        "decoder": item["decoder"],
        "probe_id": item["probe_id"],
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "verified": True,
    }


def _same_ring_records() -> dict[str, str]:
    return {
        "entry_hex": same_ring.ENTRY_PROOF.hex(),
        "userspace_hex": same_ring.USERSPACE_PROOF.hex(),
        "unsat_hex": same_ring.UNSAT_PROOF.hex(),
    }


def _verify_same_ring_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] not in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        raise EvidenceError("offline same-ring contract is not applicable")
    if set(payloads) != {"run_manifest", "static_check"} or set(receipts) != set(
        payloads
    ):
        raise EvidenceError("offline same-ring artifacts are incomplete")
    for name, payload in payloads.items():
        pin = item["contract"][name]
        receipt = receipts[name]
        if (
            len(payload) != pin["size"]
            or hashlib.sha256(payload).hexdigest() != pin["sha256"]
            or receipt.get("size") != pin["size"]
            or receipt.get("sha256") != pin["sha256"]
        ):
            raise EvidenceError(f"offline same-ring contract {name} changed")

    run_manifest = _json(payloads["run_manifest"], "same-ring run manifest")
    static_result = _json(payloads["static_check"], "same-ring static result")
    canonical = _canonical(run_manifest)
    canonical_sha256 = hashlib.sha256(canonical).hexdigest()
    records = _same_ring_records()
    expected_observation = {
        "accepted_identity": "USERSPACE_CALLBACK_REACHED",
        "zero_classification": "ZERO_AMBIGUOUS",
        "entry_threshold": same_ring.ENTRY_SIZE,
        "unsat_threshold": same_ring.UNSAT_SIZE,
        "clean_baseline_required": True,
    }
    if (
        set(run_manifest)
        != {
            "schema",
            "target",
            "profile",
            "contract_id",
            "contract_sha256",
            "records",
            "observation_contract",
            "candidate_ap",
        }
        or run_manifest.get("schema") != SAME_RING_RUN_MANIFEST_SCHEMA
        or run_manifest.get("target") != same_ring.TARGET
        or run_manifest.get("profile") != "P219"
        or run_manifest.get("contract_id") != SAME_RING_CONTRACT_ID
        or run_manifest.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or run_manifest.get("records") != records
        or run_manifest.get("observation_contract") != expected_observation
        or not _artifact_matches(run_manifest.get("candidate_ap"), candidate_ap)
        or payloads["run_manifest"] != canonical
    ):
        raise EvidenceError("run manifest does not bind the same-ring candidate")

    if (
        set(static_result)
        != {
            "schema",
            "target",
            "verdict",
            "contract_id",
            "contract_sha256",
            "records",
            "run_binding",
            "candidate",
            "safety",
        }
        or static_result.get("schema") != SAME_RING_STATIC_SCHEMA
        or static_result.get("target") != same_ring.TARGET
        or static_result.get("verdict") != SAME_RING_STATIC_VERDICT
        or static_result.get("contract_id") != SAME_RING_CONTRACT_ID
        or static_result.get("contract_sha256") != same_ring.CONTRACT_SHA256
        or static_result.get("records") != records
        or static_result.get("run_binding")
        != {
            "canonical_manifest_size": len(canonical),
            "canonical_manifest_sha256": canonical_sha256,
            "verified": True,
        }
    ):
        raise EvidenceError("static checker header does not bind P2.19 candidate")

    candidate = _exact(
        static_result["candidate"],
        {"artifacts", "record_verification"},
        "same-ring candidate",
    )
    artifacts = _exact(
        candidate["artifacts"],
        {"ap", "run_manifest", "image", "vmlinux", "boot_image"},
        "same-ring candidate artifacts",
    )
    identities = {
        name: _binary_identity(value, f"same-ring {name}")
        for name, value in artifacts.items()
    }
    verification = _exact(
        candidate["record_verification"],
        {
            "image",
            "vmlinux",
            "boot_image",
            "boot_kernel",
            "ap_members",
            "boot_only_ap",
            "verified",
        },
        "same-ring record verification",
    )
    image_claim = _record_blob_claim(
        verification["image"], "Image", identities["image"]
    )
    _record_blob_claim(
        verification["vmlinux"], "vmlinux", identities["vmlinux"]
    )
    boot_image_claim = _binary_identity(
        verification["boot_image"], "verified boot image"
    )
    boot_kernel_claim = _exact(
        verification["boot_kernel"],
        {"size", "sha256", "equals_image"},
        "verified boot kernel",
    )
    if (
        not _artifact_matches(identities["ap"], candidate_ap)
        or not _artifact_matches(
            identities["run_manifest"], receipts["run_manifest"]
        )
        or boot_image_claim != identities["boot_image"]
        or boot_kernel_claim
        != {
            "size": image_claim["size"],
            "sha256": image_claim["sha256"],
            "equals_image": True,
        }
        or verification["ap_members"]
        != [{"name": "boot.img.lz4", "type": "regular"}]
        or verification["boot_only_ap"] is not True
        or verification["verified"] is not True
        or static_result.get("safety")
        != {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
        }
    ):
        raise EvidenceError("static checker result does not bind P2.19 candidate")
    multiboot = item["kind"] == SAME_RING_MULTIBOOT_KIND
    result = {
        "schema": (
            "device_action_f1_same_ring_multiboot_offline_contract_v1"
            if multiboot
            else "device_action_f1_same_ring_offline_contract_v2"
        ),
        "decoder": (
            SAME_RING_MULTIBOOT_DECODER if multiboot else SAME_RING_DECODER
        ),
        "contract_id": SAME_RING_CONTRACT_ID,
        "candidate_ap_sha256": candidate_ap["sha256"],
        "run_manifest_sha256": receipts["run_manifest"]["sha256"],
        "static_check_sha256": receipts["static_check"]["sha256"],
        "clean_baseline_required": True,
        "zero_is_ambiguous": True,
        "verified": True,
    }
    if multiboot:
        result["policy_id"] = SAME_RING_MULTIBOOT_POLICY_ID
        result["minimum_exact_count"] = 1
    return result


def verify_offline_contract(
    acceptance: dict[str, Any],
    *,
    payloads: dict[str, bytes],
    receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
) -> dict[str, Any]:
    if acceptance.get("kind") == E1_LATEST_STAGE_KIND:
        raise EvidenceError(
            "P2.33 E1 latest-stage evidence has no candidate-bound offline "
            "contract; source-only implementation cannot become live-ready"
        )
    if acceptance.get("kind") in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        return _verify_same_ring_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    if acceptance.get("kind") == PID1_USERSPACE_KIND:
        return _verify_pid1_userspace_offline_contract(
            acceptance,
            payloads=payloads,
            receipts=receipts,
            candidate_ap=candidate_ap,
        )
    return _verify_checkpoint_offline_contract(
        acceptance,
        payloads=payloads,
        receipts=receipts,
        candidate_ap=candidate_ap,
    )


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


def classify_pid1_userspace(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != PID1_USERSPACE_KIND:
        raise EvidenceError("PID1 userspace classifier received another evidence kind")
    entry_count = payload.count(PID1_USERSPACE_ENTRY)
    userspace_count = payload.count(PID1_USERSPACE_PROOF)
    family_count = payload.count(PID1_USERSPACE_FAMILY)
    markers = (PID1_USERSPACE_ENTRY, PID1_USERSPACE_PROOF)
    partial_head = any(
        payload.startswith(marker[-length:])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    partial_tail = any(
        payload.endswith(marker[:length])
        for marker in markers
        for length in range(len(b"[[S22P1"), len(marker))
    )
    if family_count == 0 and not partial_head and not partial_tail:
        result = _base_classification(
            classification="PID1_USERSPACE_ABSENT",
            exact_count=0,
            family_count=0,
            integrity_issue=False,
        )
    elif (
        family_count != 1
        or entry_count + userspace_count != 1
        or partial_head
        or partial_tail
    ):
        result = _base_classification(
            classification="PID1_USERSPACE_FAMILY_INTEGRITY_FAILURE",
            exact_count=userspace_count,
            family_count=family_count,
            integrity_issue=True,
        )
        result["partial_at_head"] = partial_head
        result["partial_at_tail"] = partial_tail
    elif userspace_count == 1:
        result = _base_classification(
            classification="PID1_USERSPACE_CALLBACK_REACHED",
            exact_count=1,
            family_count=1,
            integrity_issue=False,
        )
        result["acceptance_present"] = True
        result["accepted"] = True
    else:
        result = _base_classification(
            classification="PID1_ENTRY_ONLY",
            exact_count=0,
            family_count=1,
            integrity_issue=False,
        )
    result["entry_count"] = entry_count
    result["userspace_count"] = userspace_count
    result["probe_id"] = item["probe_id"]
    return result


def classify_same_ring(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_KIND:
        raise EvidenceError("same-ring classifier received another evidence kind")
    try:
        decoded = same_ring.classify_observation(payload)
    except same_ring.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    exact_record_count = (
        decoded["entry_count"]
        + decoded["userspace_count"]
        + decoded["unsat_count"]
    )
    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = max(0, family_count - exact_record_count)
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["contract_id"] = item["contract_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_same_ring_multiboot(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != SAME_RING_MULTIBOOT_KIND:
        raise EvidenceError("same-ring multiboot classifier received another kind")
    try:
        decoded = same_ring_multiboot.classify_observation(payload)
    except same_ring_multiboot.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    family_count = decoded["long_family_count"] + decoded["unsat_family_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["userspace_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = decoded["exact_record_count"]
    result["foreign_count"] = max(0, family_count - decoded["exact_record_count"])
    result["partial_at_head"] = decoded["partial_at_snapshot_edge"]
    result["partial_at_tail"] = decoded["partial_at_snapshot_edge"]
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["entry_count"] = decoded["entry_count"]
    result["userspace_count"] = decoded["userspace_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["long_family_count"] = decoded["long_family_count"]
    result["unsat_family_count"] = decoded["unsat_family_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["contract_id"] = item["contract_id"]
    result["policy_id"] = item["policy_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_e1_latest_stage(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] != E1_LATEST_STAGE_KIND:
        raise EvidenceError("E1 latest-stage classifier received another kind")
    try:
        decoded = e1_latest_stage.classify_observation(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
    except e1_latest_stage.DecodeError as exc:
        raise EvidenceError(str(exc)) from exc

    model = e1_latest_stage.model
    long_family_count = payload.count(model.LONG_FAMILY)
    unsat_family_count = payload.count(model.UNSAT_FAMILY)
    family_count = long_family_count + unsat_family_count
    exact_record_count = decoded["long_record_count"] + decoded["unsat_count"]
    result = _base_classification(
        classification=decoded["classification"],
        exact_count=decoded["success_count"],
        family_count=family_count,
        integrity_issue=decoded["integrity_issue"],
    )
    result["exact_record_count"] = exact_record_count
    result["foreign_count"] = max(0, family_count - exact_record_count)
    result["baseline_absent"] = decoded["classification"] == "ZERO_AMBIGUOUS"
    result["acceptance_present"] = decoded["accepted"]
    result["accepted"] = decoded["accepted"]
    result["long_record_count"] = decoded["long_record_count"]
    result["unsat_count"] = decoded["unsat_count"]
    result["entry_count"] = decoded["entry_count"]
    result["progress_count"] = decoded["progress_count"]
    result["failure_count"] = decoded["failure_count"]
    result["success_count"] = decoded["success_count"]
    result["fallback_record_count"] = decoded["fallback_record_count"]
    result["minimum_candidate_boots"] = decoded["minimum_candidate_boots"]
    result["records"] = decoded["records"]
    result["integrity_issues"] = decoded["integrity_issues"]
    result["policy_id"] = item["policy_id"]
    result["profile"] = item["profile"]
    result["run_id"] = item["run_id"]
    result["residual_zero_meanings"] = decoded["residual_zero_meanings"]
    return result


def classify_clean_baseline(
    payload: bytes, acceptance: dict[str, Any]
) -> dict[str, Any]:
    item = validate_acceptance(acceptance)
    if item["kind"] == E1_LATEST_STAGE_KIND:
        baseline = e1_latest_stage.classify_clean_baseline(
            payload,
            expected_profile=item["profile"],
            expected_run_id=bytes.fromhex(item["run_id"]),
        )
        return {
            "classification": baseline["classification"],
            "exact_record_count": 0,
            "family_count": 0 if baseline["baseline_clean"] else 1,
            "integrity_issue": baseline["integrity_issue"],
            "baseline_clean": baseline["baseline_clean"],
        }
    if item["kind"] in {SAME_RING_KIND, SAME_RING_MULTIBOOT_KIND}:
        result = (
            classify_same_ring_multiboot(payload, item)
            if item["kind"] == SAME_RING_MULTIBOOT_KIND
            else classify_same_ring(payload, item)
        )
        exact_count = result["exact_record_count"]
        family_count = result["family_count"]
        clean = (
            result["classification"] == "ZERO_AMBIGUOUS"
            and result["integrity_issue"] is False
            and exact_count == 0
            and family_count == 0
        )
        return {
            "classification": result["classification"],
            "exact_record_count": exact_count,
            "family_count": family_count,
            "integrity_issue": result["integrity_issue"],
            "baseline_clean": clean,
        }

    marker = item["marker"].encode("ascii")
    family = item["family"].encode("ascii")
    exact_count = payload.count(marker)
    family_count = payload.count(family)
    return {
        "classification": (
            "BASELINE_CLEAN"
            if exact_count == 0 and family_count == 0
            else "BASELINE_FAMILY_PRESENT"
        ),
        "exact_record_count": exact_count,
        "family_count": family_count,
        "integrity_issue": False,
        "baseline_clean": exact_count == 0 and family_count == 0,
    }
