#!/usr/bin/env python3
"""Permanent-H0 read leaf for the S20+ autonomous public-health model.

This file is deliberately not a live coordinator.  It models one and only one
public-health lease from the exact initial attended allocation of the frozen
base coordinator, then accepts only the frozen evidence owner's fully
revalidated parked completion.  It has no writer, clock, command producer,
transport, device backend, callback, or activation path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from os import O_CLOEXEC as _O_CLOEXEC
from os import O_NOFOLLOW as _O_NOFOLLOW
from os import O_RDONLY as _O_RDONLY
from os import close as _close
from os import fstat as _fstat
from os import open as _open
from os import read as _read
from os import stat as _stat
from os import stat_result as _stat_result
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[5]
STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_READ_LEAF_PASS_GO_NOT_ACTIVE"

READ_LEAF_ACTIVE = False
LIVE_AUTHORITY = False
MECHANICALLY_ACTIVATABLE = False
COORDINATOR_INTEGRATED = False
PRIVATE_FILESYSTEM_WRITER = False
EXECUTION_INTEGRATED = False
TRUSTED_CLOCK_PROVEN = False
DURABLE_PUBLICATION_PROVEN = False
PERMANENT_H0_ONLY = True

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

PLAN_SCHEMA = "s20plus_g986n_autonomous_public_health_read_leaf_plan_v1"
STATE_SCHEMA = "s20plus_g986n_autonomous_public_health_read_leaf_state_v1"

BASE_COORDINATOR_SHA256 = (
    "87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd"
)
BASE_COORDINATOR_SIZE = 105_904
EVIDENCE_OWNER_SHA256 = (
    "1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4"
)
EVIDENCE_OWNER_NORMALIZED_SHA256 = (
    "79d2fb339ce6c972790e28675ec407d2dbbd2f8e6f1b1e87008f332cbb708db1"
)
EVIDENCE_OWNER_SIZE = 96_626

SOURCE_SPECS = MappingProxyType(
    {
        "base_coordinator": MappingProxyType(
            {
                "path": ROOT
                / "workspace/public/src/scripts/revalidation/"
                "s20plus_g986n_autonomous_research_coordinator_h0.py",
                "size": BASE_COORDINATOR_SIZE,
                "sha256": BASE_COORDINATOR_SHA256,
            }
        ),
        "evidence_owner": MappingProxyType(
            {
                "path": ROOT
                / "workspace/public/src/scripts/revalidation/"
                "s20plus_g986n_autonomous_public_health_evidence_h0.py",
                "size": EVIDENCE_OWNER_SIZE,
                "sha256": EVIDENCE_OWNER_SHA256,
            }
        ),
    }
)

BASE_COORDINATOR_ROOT = (
    ROOT / "workspace/private/runs/s20plus-g986n-autonomous-research"
)
EVIDENCE_ROOT = (
    ROOT
    / "workspace/private/runs/"
    "s20plus-g986n-autonomous-public-health-evidence"
)
FIXED_ROOT = (
    ROOT
    / "workspace/private/runs/"
    "s20plus-g986n-autonomous-public-health-read-leaf"
)

# These are the only names the old coordinator may retain for the initial
# session.  Lease/completion nodes belong to the separate leaf root.
BASE_INITIAL_SESSION_NAMES = ("opening.json", "session-opening.json")
LEAF_PENDING_NAMES = ("public-health-read-lease-000001.json",)
LEAF_PARKED_NAMES = (
    "public-health-read-lease-000001.json",
    "public-health-read-complete-000001.json",
)

READ_RESERVATION_BYTES = 524_288
EVIDENCE_PROOF_MAX_BYTES = 507_904

# The evidence reservation deliberately excludes these retained canonical JSON
# nodes.  This leaf closes that omission with a separate structural budget.  A
# future writer must enforce the same limits before durable publication.
STRUCTURAL_NODE_LAYOUT = MappingProxyType(
    {
        "base/active-campaign.json": MappingProxyType(
            {
                "root": str(BASE_COORDINATOR_ROOT),
                "actual_name": "active-campaign.json",
                "relative_location": "active-campaign.json",
                "max_bytes": 8 * 1024,
            }
        ),
        "base/opening.json": MappingProxyType(
            {
                "root": str(BASE_COORDINATOR_ROOT),
                "actual_name": "opening.json",
                "relative_location": "campaigns/<campaign_id>/session/opening.json",
                "max_bytes": 4 * 1024,
            }
        ),
        "base/session-opening.json": MappingProxyType(
            {
                "root": str(BASE_COORDINATOR_ROOT),
                "actual_name": "session-opening.json",
                "relative_location": (
                    "campaigns/<campaign_id>/session/session-opening.json"
                ),
                "max_bytes": 4 * 1024,
            }
        ),
        "evidence/accounting-opening.json": MappingProxyType(
            {
                "root": str(EVIDENCE_ROOT),
                "actual_name": "accounting-opening.json",
                "relative_location": (
                    "campaigns/campaign-<sha256(campaign_id)>/sessions/"
                    "session-<sha256(session_id)>/accounting-opening.json"
                ),
                "max_bytes": 16 * 1024,
            }
        ),
        "leaf/public-health-read-lease-000001.json": MappingProxyType(
            {
                "root": str(FIXED_ROOT),
                "actual_name": "public-health-read-lease-000001.json",
                "relative_location": "public-health-read-lease-000001.json",
                "max_bytes": 8 * 1024,
            }
        ),
        "evidence/read-intent-000001.json": MappingProxyType(
            {
                "root": str(EVIDENCE_ROOT),
                "actual_name": "read-intent-000001.json",
                "relative_location": (
                    "campaigns/campaign-<sha256(campaign_id)>/sessions/"
                    "session-<sha256(session_id)>/read-intent-000001.json"
                ),
                "max_bytes": 4 * 1024,
            }
        ),
        "evidence/read-result-000001.json": MappingProxyType(
            {
                "root": str(EVIDENCE_ROOT),
                "actual_name": "read-result-000001.json",
                "relative_location": (
                    "campaigns/campaign-<sha256(campaign_id)>/sessions/"
                    "session-<sha256(session_id)>/read-result-000001.json"
                ),
                "max_bytes": 8 * 1024,
            }
        ),
        "leaf/public-health-read-complete-000001.json": MappingProxyType(
            {
                "root": str(FIXED_ROOT),
                "actual_name": "public-health-read-complete-000001.json",
                "relative_location": "public-health-read-complete-000001.json",
                "max_bytes": 4 * 1024,
            }
        ),
    }
)
STRUCTURAL_NODE_CAPS = MappingProxyType(
    {key: value["max_bytes"] for key, value in STRUCTURAL_NODE_LAYOUT.items()}
)
STRUCTURAL_NODE_COUNT = 8
STRUCTURAL_CHILD_JOURNAL_MAX_BYTES = 48 * 1024
STRUCTURAL_CAMPAIGN_JOURNAL_MAX_BYTES = 48 * 1024
TRANSIENT_CURRENT_CONTEXT_MAX_BYTES = 4 * 1024
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024

INITIAL_STRUCTURAL_NAMES = (
    "base/active-campaign.json",
    "base/opening.json",
    "base/session-opening.json",
    "evidence/accounting-opening.json",
)
PENDING_STRUCTURAL_NAMES = INITIAL_STRUCTURAL_NAMES + (
    "leaf/public-health-read-lease-000001.json",
    "evidence/read-intent-000001.json",
)
FINAL_STRUCTURAL_NAMES = tuple(STRUCTURAL_NODE_LAYOUT)
STRUCTURAL_STAGE_NAMES = MappingProxyType(
    {
        "base-allocation": FINAL_STRUCTURAL_NAMES[:3],
        "accounting-opening": FINAL_STRUCTURAL_NAMES[:4],
        "lease": FINAL_STRUCTURAL_NAMES[:5],
        "intent": FINAL_STRUCTURAL_NAMES[:6],
        "result": FINAL_STRUCTURAL_NAMES[:7],
        "completion": FINAL_STRUCTURAL_NAMES[:8],
    }
)

ALLOWED_SUCCESSOR = MappingProxyType(
    {
        "initial": "public-health-read-lease",
        "pending": "public-health-read-complete",
        "parked": None,
    }
)


class ReadLeafH0Error(RuntimeError):
    """Any drift, ambiguity, extra successor, or unproved settlement stops."""


def canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ReadLeafH0Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ReadLeafH0Error("digest input is not bytes")
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_canonical_json(payload: bytes, label: str) -> Any:
    if type(payload) is not bytes or not payload or len(payload) > MAX_JSON_BYTES:
        raise ReadLeafH0Error(f"{label} is empty, oversized, or not bytes")
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReadLeafH0Error(f"{label} is not strict JSON") from exc
    if canonical_bytes(value) != payload:
        raise ReadLeafH0Error(f"{label} is not exact canonical JSON")
    return value


def _metadata(value: _stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _verify_source_payload(label: str, payload: bytes) -> dict[str, Any]:
    if label not in SOURCE_SPECS or type(payload) is not bytes:
        raise ReadLeafH0Error("source is outside the frozen closure")
    spec = SOURCE_SPECS[label]
    if len(payload) != spec["size"] or sha256_bytes(payload) != spec["sha256"]:
        raise ReadLeafH0Error(f"{label} source bytes differ")
    if label == "evidence_owner":
        normalized = payload
        for name in (
            "EVIDENCE_ACTIVE",
            "LIVE_AUTHORITY",
            "MECHANICALLY_ACTIVATABLE",
            "COORDINATOR_INTEGRATED",
        ):
            normalized, count = re.subn(
                rf"^{name} = (?:False|True)$".encode(),
                f"{name} = <REVIEWED_BOOLEAN>".encode(),
                normalized,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ReadLeafH0Error("evidence activation normalization is ambiguous")
        if sha256_bytes(normalized) != EVIDENCE_OWNER_NORMALIZED_SHA256:
            raise ReadLeafH0Error("evidence normalized identity differs")
    return {
        "path": str(spec["path"]),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def _read_exact_source(label: str) -> tuple[bytes, dict[str, Any]]:
    if label not in SOURCE_SPECS:
        raise ReadLeafH0Error("source label is outside the frozen closure")
    spec = SOURCE_SPECS[label]
    path = Path(spec["path"])
    descriptor = -1
    try:
        descriptor = _open(path, _O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
        before = _fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != spec["size"]
            or before.st_size > MAX_SOURCE_BYTES
        ):
            raise ReadLeafH0Error(f"{label} source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = _read(descriptor, min(1024 * 1024, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or _read(descriptor, 1):
            raise ReadLeafH0Error(f"{label} source length differs")
        after = _fstat(descriptor)
    finally:
        if descriptor >= 0:
            _close(descriptor)
    current = _stat(path, follow_symlinks=False)
    if _metadata(before) != _metadata(after) or _metadata(after) != _metadata(current):
        raise ReadLeafH0Error(f"{label} source changed while read")
    payload = bytes(data)
    return payload, _verify_source_payload(label, payload)


def _self_bytes() -> tuple[bytes, dict[str, Any]]:
    path = Path(__file__).resolve(strict=True)
    descriptor = _open(path, _O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
    try:
        before = _fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > MAX_SOURCE_BYTES
        ):
            raise ReadLeafH0Error("leaf source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = _read(descriptor, min(1024 * 1024, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or _read(descriptor, 1):
            raise ReadLeafH0Error("leaf source length differs")
        after = _fstat(descriptor)
    finally:
        _close(descriptor)
    current = _stat(path, follow_symlinks=False)
    if _metadata(before) != _metadata(after) or _metadata(after) != _metadata(current):
        raise ReadLeafH0Error("leaf source changed while read")
    payload = bytes(data)
    return payload, {
        "path": str(path),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def normalized_self_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ReadLeafH0Error("self normalization requires bytes")
    normalized = payload
    for name in (
        "READ_LEAF_ACTIVE",
        "LIVE_AUTHORITY",
        "MECHANICALLY_ACTIVATABLE",
        "COORDINATOR_INTEGRATED",
        "PRIVATE_FILESYSTEM_WRITER",
        "EXECUTION_INTEGRATED",
        "TRUSTED_CLOCK_PROVEN",
        "DURABLE_PUBLICATION_PROVEN",
    ):
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode(),
            f"{name} = <REVIEWED_BOOLEAN>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ReadLeafH0Error("leaf activation normalization is ambiguous")
    return sha256_bytes(normalized)


def self_receipt() -> dict[str, Any]:
    payload, receipt = _self_bytes()
    return {**receipt, "normalized_sha256": normalized_self_sha256(payload)}


def _load_exact_evidence_api() -> Mapping[str, Any]:
    """Execute only the already hash-verified commandless evidence bytes.

    The frozen base coordinator is never imported or executed.  The selected
    evidence functions are reused so a parked completion cannot weaken the
    already-qualified retained-return validation.
    """

    payload, receipt = _read_exact_source("evidence_owner")
    namespace: dict[str, Any] = {
        "__file__": receipt["path"],
        "__name__": "_s20plus_exact_commandless_evidence_owner",
    }
    code = compile(payload, receipt["path"], "exec", dont_inherit=True)
    exec(code, namespace, namespace)
    if (
        namespace.get("TARGET") != TARGET
        or namespace.get("STATUS")
        != "H0_AUTONOMOUS_PUBLIC_HEALTH_EVIDENCE_PASS_GO_NOT_ACTIVE"
        or namespace.get("EVIDENCE_ACTIVE") is not False
        or namespace.get("LIVE_AUTHORITY") is not False
        or namespace.get("MECHANICALLY_ACTIVATABLE") is not False
        or namespace.get("COORDINATOR_INTEGRATED") is not False
        or namespace.get("READ_RESERVATION_BYTES") != READ_RESERVATION_BYTES
        or namespace.get("TOTAL_EVIDENCE_PROOF_MAX_BYTES")
        != EVIDENCE_PROOF_MAX_BYTES
    ):
        raise ReadLeafH0Error("frozen evidence owner boundary differs")
    selected = (
        "canonical_bytes",
        "sha256_bytes",
        "source_receipts",
        "model_accounting_opening",
        "validate_accounting_opening",
        "initial_protocol_state",
        "validate_protocol_state",
        "validate_source_identity",
        "validate_counters",
        "validate_scope_relation",
        "reserve_counters",
        "expected_host_tool",
        "validate_future_lease",
        "mirror_read_intent",
        "validate_mirrored_intent",
        "validate_future_completion",
        "advance_protocol_state",
        "COORDINATOR_LEASE_SCHEMA",
        "COORDINATOR_COMPLETE_SCHEMA",
        "CHILD_LIMITS",
        "CAMPAIGN_LIMITS",
        "ZERO_HASH",
    )
    if any(name not in namespace for name in selected):
        raise ReadLeafH0Error("frozen evidence API is incomplete")
    return MappingProxyType({name: namespace[name] for name in selected})


_BASE_SOURCE, _BASE_RECEIPT = _read_exact_source("base_coordinator")
_EVIDENCE_SOURCE, _EVIDENCE_RECEIPT = _read_exact_source("evidence_owner")
# MappingProxyType narrows the reused API but is not a Python isolation
# boundary: selected functions still have inspectable module globals.  Those
# globals are non-authoritative in this permanently commandless H0 model and
# must not be treated as a provenance mechanism by a future live integration.
_EVIDENCE = _load_exact_evidence_api()


def source_receipts() -> dict[str, Any]:
    base_payload, base = _read_exact_source("base_coordinator")
    evidence_payload, evidence = _read_exact_source("evidence_owner")
    del base_payload, evidence_payload
    transitive = _EVIDENCE["source_receipts"]()
    owner = transitive.get("owner")
    coordinator = transitive.get("coordinator")
    if (
        type(owner) is not dict
        or owner.get("size") != EVIDENCE_OWNER_SIZE
        or owner.get("sha256") != EVIDENCE_OWNER_SHA256
        or owner.get("normalized_sha256") != EVIDENCE_OWNER_NORMALIZED_SHA256
        or type(coordinator) is not dict
        or coordinator.get("size") != BASE_COORDINATOR_SIZE
        or coordinator.get("sha256") != BASE_COORDINATOR_SHA256
    ):
        raise ReadLeafH0Error("transitive evidence source closure differs")
    return {
        "read_leaf": self_receipt(),
        "base_coordinator": base,
        "evidence_owner": evidence,
        "evidence_transitive": transitive,
    }


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise ReadLeafH0Error(f"{label} keys differ")


def _require_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ReadLeafH0Error(f"{label} is not a strict bounded integer")
    return value


def _strict_string_sequence(value: Any, label: str) -> tuple[str, ...]:
    if type(value) not in (list, tuple) or any(type(item) is not str for item in value):
        raise ReadLeafH0Error(f"{label} is not a string sequence")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise ReadLeafH0Error(f"{label} contains duplicate names")
    return result


def validate_transient_current_context(payload: bytes) -> dict[str, Any]:
    if type(payload) is not bytes or len(payload) > TRANSIENT_CURRENT_CONTEXT_MAX_BYTES:
        raise ReadLeafH0Error("transient current context exceeds 4 KiB")
    value = parse_canonical_json(payload, "transient current context")
    if type(value) is not dict:
        raise ReadLeafH0Error("transient current context is not an object")
    return {
        "standalone_node_retained": False,
        "standalone_node_separately_charged": False,
        "canonical_value_lease_embedding_required": True,
        "embedded_bytes_must_be_charged_with_lease_structural_cap": True,
        "size": len(payload),
        "sha256": sha256_bytes(payload),
        "max_bytes": TRANSIENT_CURRENT_CONTEXT_MAX_BYTES,
    }


def _validate_structural_subset(
    raw_nodes: Any, expected_names: Sequence[str]
) -> dict[str, Any]:
    expected = tuple(expected_names)
    if type(raw_nodes) is not dict or tuple(raw_nodes) != expected:
        raise ReadLeafH0Error("structural journal names/order differ")
    per_node: dict[str, Any] = {}
    total = 0
    for name in expected:
        payload = raw_nodes[name]
        if type(payload) is not bytes:
            raise ReadLeafH0Error(f"{name} structural node is not bytes")
        cap = STRUCTURAL_NODE_CAPS[name]
        if len(payload) > cap:
            raise ReadLeafH0Error(f"{name} exceeds its structural cap")
        parse_canonical_json(payload, name)
        per_node[name] = {
            "size": len(payload),
            "sha256": sha256_bytes(payload),
            "max_bytes": cap,
        }
        total += len(payload)
    if (
        total > STRUCTURAL_CHILD_JOURNAL_MAX_BYTES
        or total > STRUCTURAL_CAMPAIGN_JOURNAL_MAX_BYTES
    ):
        raise ReadLeafH0Error("structural aggregate exceeds child/campaign cap")
    return {
        "node_count": len(expected),
        "per_node": per_node,
        "actual_bytes": total,
        "child_journal_bytes": total,
        "campaign_journal_bytes": total,
        "child_journal_max_bytes": STRUCTURAL_CHILD_JOURNAL_MAX_BYTES,
        "campaign_journal_max_bytes": STRUCTURAL_CAMPAIGN_JOURNAL_MAX_BYTES,
        "evidence_reservation_bytes": READ_RESERVATION_BYTES,
        "evidence_proof_max_bytes": EVIDENCE_PROOF_MAX_BYTES,
        "separate_from_evidence_reservation": True,
        "writer_enforced": False,
    }


def validate_structural_journal(raw_nodes: Any) -> dict[str, Any]:
    proof = _validate_structural_subset(raw_nodes, FINAL_STRUCTURAL_NAMES)
    if proof["node_count"] != STRUCTURAL_NODE_COUNT:
        raise ReadLeafH0Error("structural journal node count differs")
    progression: dict[str, Any] = {}
    expected_count = 3
    previous_bytes = 0
    for stage, names in STRUCTURAL_STAGE_NAMES.items():
        stage_nodes = {name: raw_nodes[name] for name in names}
        stage_proof = _validate_structural_subset(stage_nodes, names)
        if (
            stage_proof["node_count"] != expected_count
            or stage_proof["actual_bytes"] <= previous_bytes
        ):
            raise ReadLeafH0Error("structural journal progression differs")
        progression[stage] = {
            "node_count": stage_proof["node_count"],
            "actual_bytes": stage_proof["actual_bytes"],
        }
        expected_count += 1
        previous_bytes = stage_proof["actual_bytes"]
    if expected_count != STRUCTURAL_NODE_COUNT + 1 or previous_bytes != proof["actual_bytes"]:
        raise ReadLeafH0Error("structural final progression differs")
    proof["progression"] = progression
    return proof


def validate_separate_namespaces(
    phase: str,
    base_session_names: Sequence[str],
    leaf_names: Sequence[str],
) -> dict[str, Any]:
    if type(phase) is not str or phase not in ALLOWED_SUCCESSOR:
        raise ReadLeafH0Error("leaf phase differs")
    base = _strict_string_sequence(base_session_names, "base session namespace")
    leaf = _strict_string_sequence(leaf_names, "read-leaf namespace")
    expected_leaf = {
        "initial": (),
        "pending": LEAF_PENDING_NAMES,
        "parked": LEAF_PARKED_NAMES,
    }[phase]
    if base != BASE_INITIAL_SESSION_NAMES:
        raise ReadLeafH0Error("old coordinator namespace was augmented or changed")
    if leaf != expected_leaf:
        raise ReadLeafH0Error("read-leaf namespace contains a sibling or gap")
    if set(base) & set(leaf):
        raise ReadLeafH0Error("old coordinator and read-leaf namespaces overlap")
    return {
        "phase": phase,
        "base_session_names": list(base),
        "read_leaf_names": list(leaf),
        "separate_root": True,
    }


def validate_successor(phase: str, successor_kind: str) -> str:
    if type(phase) is not str or phase not in ALLOWED_SUCCESSOR:
        raise ReadLeafH0Error("successor phase differs")
    if type(successor_kind) is not str:
        raise ReadLeafH0Error("successor kind is not a string")
    expected = ALLOWED_SUCCESSOR[phase]
    if expected is None or successor_kind != expected:
        raise ReadLeafH0Error("control, terminal, F1, sibling, or replay successor denied")
    return successor_kind


def _zero_control_counters(value: Any, label: str) -> dict[str, int]:
    keys = {
        "control_transactions",
        "component_effects_consumed",
        "component_effects_reserved",
        "normal_reboots",
        "download_roundtrips",
        "roundtrip_entries",
        "roundtrip_returns",
    }
    _exact_keys(value, keys, label)
    result = {key: _require_int(value[key], f"{label}.{key}") for key in keys}
    if any(result.values()):
        raise ReadLeafH0Error(f"{label} is not the exact zero-control state")
    return result


def _initial_model(
    allocation: Mapping[str, Any],
    current_context: Mapping[str, Any],
    current_context_raw: bytes,
    current_head: Mapping[str, Any],
    current_head_raw: bytes,
    observed_at: int,
) -> tuple[dict[str, Any], bytes, dict[str, Any], dict[str, Any]]:
    # Reopen every frozen source before relying on the evidence validator.
    source_receipts()
    transient = validate_transient_current_context(current_context_raw)
    if canonical_bytes(current_context) != current_context_raw:
        raise ReadLeafH0Error("current context raw bytes differ")
    if type(allocation) is not dict:
        raise ReadLeafH0Error("allocation is not a strict object")
    for raw_name in ("guard_raw", "opening_raw", "session_raw"):
        if type(allocation.get(raw_name)) is not bytes:
            raise ReadLeafH0Error("base allocation lacks exact raw bytes")
    if current_head != allocation.get("session") or current_head_raw != allocation.get(
        "session_raw"
    ):
        raise ReadLeafH0Error("current head is not byte-identical session opening")
    timestamp = _require_int(observed_at, "observed_at")
    if current_context.get("current_time") != timestamp:
        raise ReadLeafH0Error("observed time differs from current context")

    try:
        opening = _EVIDENCE["model_accounting_opening"](
            allocation,
            current_context,
            current_context_raw,
            current_head,
            current_head_raw,
            timestamp,
        )
        opening_raw = _EVIDENCE["canonical_bytes"](opening)
        protocol = _EVIDENCE["initial_protocol_state"](opening, opening_raw)
    except Exception as exc:
        raise ReadLeafH0Error("frozen initial coordinator/evidence model rejected") from exc

    if (
        opening["target"] != TARGET
        or opening["attended_opening"] is not True
        or opening["command_execution_backend"] is not False
        or protocol["read_ordinal"] != 0
        or protocol["campaign_parked"] is not False
        or any(protocol["child_counters"].values())
        or any(protocol["campaign_counters"].values())
    ):
        raise ReadLeafH0Error("initial read state is not fresh attended zero state")
    _zero_control_counters(current_context["child_counters"], "child controls")
    _zero_control_counters(current_context["campaign_counters"], "campaign controls")

    raw_nodes = {
        "base/active-campaign.json": allocation["guard_raw"],
        "base/opening.json": allocation["opening_raw"],
        "base/session-opening.json": allocation["session_raw"],
        "evidence/accounting-opening.json": opening_raw,
    }
    structural = _validate_structural_subset(raw_nodes, INITIAL_STRUCTURAL_NAMES)
    return opening, opening_raw, protocol, {
        "transient_context": transient,
        "structural": structural,
    }


PENDING_BUNDLE_KEYS = {
    "allocation",
    "current_context",
    "current_context_raw",
    "current_head",
    "current_head_raw",
    "observed_at",
    "base_session_names",
    "initial_leaf_names",
    "accounting_opening",
    "accounting_opening_raw",
    "protocol_state",
    "lease",
    "lease_raw",
    "intent",
    "intent_raw",
    "state",
}

STATE_KEYS = {
    "schema",
    "phase",
    "campaign_id",
    "session_id",
    "target",
    "read_ordinal",
    "source_identity",
    "base_guard_sha256",
    "base_opening_sha256",
    "base_session_sha256",
    "transient_context_sha256",
    "accounting_opening_sha256",
    "admission_head_sha256",
    "current_head_sha256",
    "lease_sha256",
    "intent_sha256",
    "evidence_result_sha256",
    "completion_sha256",
    "child_counters",
    "campaign_counters",
    "structural_node_count",
    "structural_journal_bytes",
    "pending_effect",
    "campaign_parked",
    "controls_authorized",
    "terminal_authorized",
    "f1_authorized",
    "second_lease_authorized",
    "reporting_device_command_count",
    "reporting_device_effect_count",
    "writer_enforced",
    "clock_proven",
    "durability_proven",
}


def _model_state(
    *,
    phase: str,
    opening: Mapping[str, Any],
    allocation: Mapping[str, Any],
    context_raw: bytes,
    current_head_raw: bytes,
    lease_raw: bytes,
    intent_raw: bytes,
    result_raw: bytes | None,
    completion_raw: bytes | None,
    counters: Mapping[str, Any],
    structural: Mapping[str, Any],
) -> dict[str, Any]:
    if phase not in ("pending", "parked"):
        raise ReadLeafH0Error("modeled leaf state phase differs")
    return {
        "schema": STATE_SCHEMA,
        "phase": phase,
        "campaign_id": opening["campaign_id"],
        "session_id": opening["session_id"],
        "target": TARGET,
        "read_ordinal": 1,
        "source_identity": opening["source_identity"],
        "base_guard_sha256": sha256_bytes(allocation["guard_raw"]),
        "base_opening_sha256": sha256_bytes(allocation["opening_raw"]),
        "base_session_sha256": sha256_bytes(allocation["session_raw"]),
        "transient_context_sha256": sha256_bytes(context_raw),
        "accounting_opening_sha256": sha256_bytes(canonical_bytes(opening)),
        "admission_head_sha256": sha256_bytes(current_head_raw),
        "current_head_sha256": (
            sha256_bytes(lease_raw)
            if phase == "pending"
            else sha256_bytes(completion_raw)
        ),
        "lease_sha256": sha256_bytes(lease_raw),
        "intent_sha256": sha256_bytes(intent_raw),
        "evidence_result_sha256": (
            None if result_raw is None else sha256_bytes(result_raw)
        ),
        "completion_sha256": (
            None if completion_raw is None else sha256_bytes(completion_raw)
        ),
        "child_counters": counters["child_counters"],
        "campaign_counters": counters["campaign_counters"],
        "structural_node_count": structural["node_count"],
        "structural_journal_bytes": structural["actual_bytes"],
        "pending_effect": phase == "pending",
        "campaign_parked": True,
        "controls_authorized": False,
        "terminal_authorized": False,
        "f1_authorized": False,
        "second_lease_authorized": False,
        "reporting_device_command_count": 0,
        "reporting_device_effect_count": 0,
        "writer_enforced": False,
        "clock_proven": False,
        "durability_proven": False,
    }


def validate_state(value: Any) -> dict[str, Any]:
    _exact_keys(value, STATE_KEYS, "read-leaf state")
    phase = value["phase"]
    if phase not in ("pending", "parked"):
        raise ReadLeafH0Error("read-leaf state phase differs")
    if (
        value["schema"] != STATE_SCHEMA
        or value["target"] != TARGET
        or type(value["read_ordinal"]) is not int
        or value["read_ordinal"] != 1
        or type(value["campaign_id"]) is not str
        or re.fullmatch(r"[0-9a-f]{32}", value["campaign_id"]) is None
        or type(value["session_id"]) is not str
        or re.fullmatch(r"[0-9a-f]{32}", value["session_id"]) is None
        or type(value["source_identity"]) is not dict
    ):
        raise ReadLeafH0Error("read-leaf state identity differs")
    for key in (
        "base_guard_sha256",
        "base_opening_sha256",
        "base_session_sha256",
        "transient_context_sha256",
        "accounting_opening_sha256",
        "admission_head_sha256",
        "current_head_sha256",
        "lease_sha256",
        "intent_sha256",
    ):
        if type(value[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            raise ReadLeafH0Error(f"state {key} differs")
    for key in ("evidence_result_sha256", "completion_sha256"):
        if value[key] is not None and (
            type(value[key]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None
        ):
            raise ReadLeafH0Error(f"state {key} differs")
    _require_int(value["structural_node_count"], "structural node count")
    _require_int(value["structural_journal_bytes"], "structural journal bytes")
    if (
        value["structural_journal_bytes"] == 0
        or value["structural_journal_bytes"] > STRUCTURAL_CHILD_JOURNAL_MAX_BYTES
        or value["admission_head_sha256"] != value["base_session_sha256"]
    ):
        raise ReadLeafH0Error("state structural journal exceeds cap")
    try:
        source = _EVIDENCE["validate_source_identity"](
            value["source_identity"], "read-leaf state source"
        )
        child = _EVIDENCE["validate_counters"](
            value["child_counters"], _EVIDENCE["CHILD_LIMITS"], "state child"
        )
        campaign = _EVIDENCE["validate_counters"](
            value["campaign_counters"],
            _EVIDENCE["CAMPAIGN_LIMITS"],
            "state campaign",
        )
        _EVIDENCE["validate_scope_relation"](child, campaign, "read-leaf state")
    except Exception as exc:
        raise ReadLeafH0Error("state source or counter semantics differ") from exc
    if source["target"] != TARGET:
        raise ReadLeafH0Error("state source target differs")
    strict_bools = (
        "pending_effect",
        "campaign_parked",
        "controls_authorized",
        "terminal_authorized",
        "f1_authorized",
        "second_lease_authorized",
        "writer_enforced",
        "clock_proven",
        "durability_proven",
    )
    if any(type(value[key]) is not bool for key in strict_bools):
        raise ReadLeafH0Error("state flags are not strict booleans")
    if (
        value["campaign_parked"] is not True
        or any(
            value[key] is not False
            for key in (
                "controls_authorized",
                "terminal_authorized",
                "f1_authorized",
                "second_lease_authorized",
                "writer_enforced",
                "clock_proven",
                "durability_proven",
            )
        )
        or value["pending_effect"] is not (phase == "pending")
        or type(value["reporting_device_command_count"]) is not int
        or value["reporting_device_command_count"] != 0
        or type(value["reporting_device_effect_count"]) is not int
        or value["reporting_device_effect_count"] != 0
    ):
        raise ReadLeafH0Error("read-leaf state grants an effect or successor")
    if phase == "pending":
        expected = {
            "read_operations": 1,
            "private_evidence_bytes_consumed": 0,
            "private_evidence_bytes_reserved": READ_RESERVATION_BYTES,
        }
        if (
            value["evidence_result_sha256"] is not None
            or value["completion_sha256"] is not None
            or value["structural_node_count"] != len(PENDING_STRUCTURAL_NAMES)
            or child != expected
            or campaign != expected
            or value["current_head_sha256"] != value["lease_sha256"]
        ):
            raise ReadLeafH0Error("pending state contains a completion")
    else:
        if (
            value["evidence_result_sha256"] is None
            or value["completion_sha256"] is None
            or value["structural_node_count"] != STRUCTURAL_NODE_COUNT
            or child["read_operations"] != 1
            or child["private_evidence_bytes_reserved"] != 0
            or not 0
            < child["private_evidence_bytes_consumed"]
            <= EVIDENCE_PROOF_MAX_BYTES
            or campaign != child
            or value["current_head_sha256"] != value["completion_sha256"]
        ):
            raise ReadLeafH0Error("parked state lacks exact completion")
    return dict(value)


def _construct_exact_lease(
    opening: Mapping[str, Any],
    opening_raw: bytes,
    protocol: Mapping[str, Any],
    current_context: Mapping[str, Any],
    current_head: Mapping[str, Any],
    observed_at: int,
) -> dict[str, Any]:
    child_previous = protocol["child_counters"]
    campaign_previous = protocol["campaign_counters"]
    return {
        "schema": _EVIDENCE["COORDINATOR_LEASE_SCHEMA"],
        "kind": "public-health-read-lease",
        "issued_at": observed_at,
        "campaign_id": opening["campaign_id"],
        "session_id": opening["session_id"],
        "target": TARGET,
        "action": "public-health",
        "read_ordinal": 1,
        "accounting_opening_sha256": sha256_bytes(opening_raw),
        "coordinator_context": dict(current_context),
        "coordinator_context_sha256": sha256_bytes(canonical_bytes(current_context)),
        "coordinator_head": dict(current_head),
        "coordinator_head_sha256": sha256_bytes(canonical_bytes(current_head)),
        "source_identity": opening["source_identity"],
        "previous_evidence_result_sha256": _EVIDENCE["ZERO_HASH"],
        "previous_coordinator_complete_sha256": _EVIDENCE["ZERO_HASH"],
        "previous_child_counters": child_previous,
        "previous_campaign_counters": campaign_previous,
        "child_counters": _EVIDENCE["reserve_counters"](
            child_previous, _EVIDENCE["CHILD_LIMITS"], "leaf child"
        ),
        "campaign_counters": _EVIDENCE["reserve_counters"](
            campaign_previous, _EVIDENCE["CAMPAIGN_LIMITS"], "leaf campaign"
        ),
        "reservation_bytes": READ_RESERVATION_BYTES,
        "expected_host_tool": _EVIDENCE["expected_host_tool"](),
        "attempt_consumed": True,
        "replay_authorized": False,
        "controls_blocked": True,
        "terminal_blocked": True,
        "completion_required": True,
    }


def model_ordinal_one_pending(
    allocation: Mapping[str, Any],
    current_context: Mapping[str, Any],
    current_context_raw: bytes,
    current_head: Mapping[str, Any],
    current_head_raw: bytes,
    observed_at: int,
    *,
    base_session_names: Sequence[str],
    leaf_names: Sequence[str],
) -> dict[str, Any]:
    validate_successor("initial", "public-health-read-lease")
    namespace = validate_separate_namespaces(
        "initial", base_session_names, leaf_names
    )
    opening, opening_raw, protocol, base_proofs = _initial_model(
        allocation,
        current_context,
        current_context_raw,
        current_head,
        current_head_raw,
        observed_at,
    )
    lease = _construct_exact_lease(
        opening,
        opening_raw,
        protocol,
        current_context,
        current_head,
        observed_at,
    )
    lease_raw = canonical_bytes(lease)
    try:
        _EVIDENCE["validate_future_lease"](
            lease, lease_raw, opening, opening_raw, protocol, observed_at
        )
        intent = _EVIDENCE["mirror_read_intent"](
            lease, lease_raw, opening, opening_raw, observed_at
        )
        intent_raw = _EVIDENCE["canonical_bytes"](intent)
        _EVIDENCE["validate_mirrored_intent"](
            intent, intent_raw, lease, lease_raw, opening, opening_raw
        )
    except Exception as exc:
        raise ReadLeafH0Error("frozen evidence lease/intent model rejected") from exc
    raw_nodes = {
        "base/active-campaign.json": allocation["guard_raw"],
        "base/opening.json": allocation["opening_raw"],
        "base/session-opening.json": allocation["session_raw"],
        "evidence/accounting-opening.json": opening_raw,
        "leaf/public-health-read-lease-000001.json": lease_raw,
        "evidence/read-intent-000001.json": intent_raw,
    }
    structural = _validate_structural_subset(raw_nodes, PENDING_STRUCTURAL_NAMES)
    state = _model_state(
        phase="pending",
        opening=opening,
        allocation=allocation,
        context_raw=current_context_raw,
        current_head_raw=current_head_raw,
        lease_raw=lease_raw,
        intent_raw=intent_raw,
        result_raw=None,
        completion_raw=None,
        counters=lease,
        structural=structural,
    )
    validate_state(state)
    validate_separate_namespaces(
        "pending", namespace["base_session_names"], LEAF_PENDING_NAMES
    )
    return {
        "allocation": allocation,
        "current_context": current_context,
        "current_context_raw": current_context_raw,
        "current_head": current_head,
        "current_head_raw": current_head_raw,
        "observed_at": observed_at,
        "base_session_names": namespace["base_session_names"],
        "initial_leaf_names": namespace["read_leaf_names"],
        "accounting_opening": opening,
        "accounting_opening_raw": opening_raw,
        "protocol_state": protocol,
        "lease": lease,
        "lease_raw": lease_raw,
        "intent": intent,
        "intent_raw": intent_raw,
        "state": state,
    }


def validate_pending_bundle(value: Any) -> dict[str, Any]:
    _exact_keys(value, PENDING_BUNDLE_KEYS, "pending bundle")
    expected = model_ordinal_one_pending(
        value["allocation"],
        value["current_context"],
        value["current_context_raw"],
        value["current_head"],
        value["current_head_raw"],
        value["observed_at"],
        base_session_names=value["base_session_names"],
        leaf_names=value["initial_leaf_names"],
    )
    if value != expected:
        raise ReadLeafH0Error("pending bundle differs from exact ordinal-one model")
    return dict(value)


def complete_pending_parked(
    pending: Mapping[str, Any],
    result: Mapping[str, Any],
    result_raw: bytes,
    completion: Mapping[str, Any],
    completion_raw: bytes,
    records: Sequence[Mapping[str, Any]],
    receipt_pairs: Sequence[tuple[Mapping[str, Any], bytes]],
    *,
    base_session_names: Sequence[str],
    leaf_names: Sequence[str],
) -> dict[str, Any]:
    validate_successor("pending", "public-health-read-complete")
    pending = validate_pending_bundle(pending)
    validate_separate_namespaces("pending", base_session_names, leaf_names)
    if tuple(base_session_names) != tuple(pending["base_session_names"]):
        raise ReadLeafH0Error("completion base namespace differs from admitted lease")
    if type(result_raw) is not bytes or type(completion_raw) is not bytes:
        raise ReadLeafH0Error("result/completion raw values are not bytes")
    try:
        checked = _EVIDENCE["validate_future_completion"](
            completion,
            completion_raw,
            result,
            result_raw,
            pending["lease"],
            pending["lease_raw"],
            pending["intent"],
            pending["intent_raw"],
            pending["accounting_opening"],
            pending["accounting_opening_raw"],
            pending["protocol_state"],
            pending["observed_at"],
            records,
            receipt_pairs,
        )
        advanced = _EVIDENCE["advance_protocol_state"](
            pending["protocol_state"],
            result,
            result_raw,
            completion,
            completion_raw,
            pending["lease"],
            pending["lease_raw"],
            pending["intent"],
            pending["intent_raw"],
            pending["accounting_opening"],
            pending["accounting_opening_raw"],
            pending["observed_at"],
            records,
            receipt_pairs,
        )
    except Exception as exc:
        raise ReadLeafH0Error("full frozen evidence revalidation rejected completion") from exc
    if (
        checked != completion
        or advanced["campaign_parked"] is not True
        or completion.get("completion_mode") != "permanent-h0-parked"
        or completion.get("controls_unblocked") is not False
        or completion.get("terminal_unblocked") is not False
        or completion.get("campaign_parked") is not True
        or type(result.get("device_command_count_by_owner")) is not int
        or result.get("device_command_count_by_owner") != 0
        or type(result.get("device_effect_count")) is not int
        or result.get("device_effect_count") != 0
    ):
        raise ReadLeafH0Error("completion is not exact zero-command parked settlement")
    raw_nodes = {
        "base/active-campaign.json": pending["allocation"]["guard_raw"],
        "base/opening.json": pending["allocation"]["opening_raw"],
        "base/session-opening.json": pending["allocation"]["session_raw"],
        "evidence/accounting-opening.json": pending["accounting_opening_raw"],
        "leaf/public-health-read-lease-000001.json": pending["lease_raw"],
        "evidence/read-intent-000001.json": pending["intent_raw"],
        "evidence/read-result-000001.json": result_raw,
        "leaf/public-health-read-complete-000001.json": completion_raw,
    }
    structural = validate_structural_journal(raw_nodes)
    state = _model_state(
        phase="parked",
        opening=pending["accounting_opening"],
        allocation=pending["allocation"],
        context_raw=pending["current_context_raw"],
        current_head_raw=pending["current_head_raw"],
        lease_raw=pending["lease_raw"],
        intent_raw=pending["intent_raw"],
        result_raw=result_raw,
        completion_raw=completion_raw,
        counters=result,
        structural=structural,
    )
    validate_state(state)
    validate_separate_namespaces("parked", BASE_INITIAL_SESSION_NAMES, LEAF_PARKED_NAMES)
    return {
        "state": state,
        "validated_settlement": {
            "status": "FULLY_REVALIDATED_SETTLEMENT_PARKED",
            "settlement_validated": True,
            "reservation_state": "SETTLED",
            "replay_authorized": False,
            "next_action_authorized": False,
            "campaign_parked": True,
        },
        "structural_accounting": structural,
        "transient_current_context": validate_transient_current_context(
            pending["current_context_raw"]
        ),
        "evidence_protocol_state": advanced,
        "result": result,
        "result_raw": result_raw,
        "completion": completion,
        "completion_raw": completion_raw,
    }


def reject_any_successor_from_parked(state: Mapping[str, Any], successor_kind: str) -> None:
    checked = validate_state(state)
    if checked["phase"] != "parked":
        raise ReadLeafH0Error("successor rejection requires parked state")
    validate_successor("parked", successor_kind)


def classify_cut(
    *,
    lease_present: bool,
    intent_present: bool,
    result_present: bool,
    completion_present: bool,
) -> dict[str, Any]:
    flags = {
        "lease_present": lease_present,
        "intent_present": intent_present,
        "result_present": result_present,
        "completion_present": completion_present,
    }
    if any(type(value) is not bool for value in flags.values()):
        raise ReadLeafH0Error("cut flags are not strict booleans")
    if intent_present and not lease_present:
        raise ReadLeafH0Error("intent cannot exist without a lease")
    if result_present and not intent_present:
        raise ReadLeafH0Error("result cannot exist without an intent")
    if completion_present and not result_present:
        raise ReadLeafH0Error("completion cannot exist without a result")
    if not lease_present:
        status = "NO_LEASE_NO_AUTHORITY"
        reservation = "ABSENT"
    elif not intent_present:
        status = "LEASE_PRESENT_MIRROR_UNPROVED_PARKED"
        reservation = "RETAINED"
    elif not result_present:
        status = "PENDING_EVIDENCE_UNCERTAIN_CONSUMED_PARKED"
        reservation = "RETAINED"
    elif not completion_present:
        status = "RESULT_PRESENT_COMPLETION_UNPROVED_PARKED"
        reservation = "RETAINED"
    else:
        status = "COMPLETION_PRESENT_SETTLEMENT_UNPROVED_PARKED"
        reservation = "RETAINED_OR_UNPROVED"
    return {
        "status": status,
        "reservation_state": reservation,
        "settlement_validated": False,
        "zero_command_revalidation_only": lease_present,
        "replay_authorized": False,
        "refund_authorized": False,
        "next_read_authorized": False,
        "control_authorized": False,
        "terminal_authorized": False,
        "f1_authorized": False,
        "campaign_parked": lease_present,
    }


def begin_live_read() -> None:
    raise ReadLeafH0Error("live read is absent from this permanent H0 leaf")


def publish_live_lease() -> None:
    raise ReadLeafH0Error("private writer is absent from this permanent H0 leaf")


def execute_live_return() -> None:
    raise ReadLeafH0Error("executor/transport is absent from this permanent H0 leaf")


def complete_live_read() -> None:
    raise ReadLeafH0Error("live completion is absent from this permanent H0 leaf")


def render_plan() -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "target": TARGET,
        "read_leaf_active": READ_LEAF_ACTIVE,
        "live_authority": LIVE_AUTHORITY,
        "mechanically_activatable": MECHANICALLY_ACTIVATABLE,
        "coordinator_integrated": COORDINATOR_INTEGRATED,
        "private_filesystem_writer": PRIVATE_FILESYSTEM_WRITER,
        "execution_integrated": EXECUTION_INTEGRATED,
        "trusted_clock_proven": TRUSTED_CLOCK_PROVEN,
        "durable_publication_proven": DURABLE_PUBLICATION_PROVEN,
        "permanent_h0_only": PERMANENT_H0_ONLY,
        "cli": ["--render-plan"],
        "sources": source_receipts(),
        "fixed_roots": {
            "base_coordinator": str(BASE_COORDINATOR_ROOT),
            "evidence_owner": str(EVIDENCE_ROOT),
            "read_leaf": str(FIXED_ROOT),
        },
        "base_coordinator_imported_or_executed": False,
        "evidence_owner_reused_only_after_exact_hash_verification": True,
        "selected_evidence_callable_globals_are_non_authoritative": True,
        "modeled_read_ordinals": [1],
        "state_machine": {
            "initial_successor": "public-health-read-lease",
            "pending_successor": "public-health-read-complete",
            "completion": "permanent-h0-parked",
            "parked_successors": [],
        },
        "base_initial_session_names": list(BASE_INITIAL_SESSION_NAMES),
        "leaf_pending_names": list(LEAF_PENDING_NAMES),
        "leaf_parked_names": list(LEAF_PARKED_NAMES),
        "evidence_accounting": {
            "reservation_bytes": READ_RESERVATION_BYTES,
            "proof_max_bytes": EVIDENCE_PROOF_MAX_BYTES,
        },
        "structural_journal": {
            "retained_node_count": STRUCTURAL_NODE_COUNT,
            "progression_node_counts": [3, 4, 5, 6, 7, 8],
            "node_layout": {
                key: dict(value) for key, value in STRUCTURAL_NODE_LAYOUT.items()
            },
            "node_caps": dict(STRUCTURAL_NODE_CAPS),
            "fixed_root_count": 3,
            "child_max_bytes": STRUCTURAL_CHILD_JOURNAL_MAX_BYTES,
            "campaign_max_bytes": STRUCTURAL_CAMPAIGN_JOURNAL_MAX_BYTES,
            "transient_current_context_max_bytes": TRANSIENT_CURRENT_CONTEXT_MAX_BYTES,
            "current_context_standalone_node_retained": False,
            "current_context_standalone_node_separately_charged": False,
            "current_context_canonical_value_embedded_in_lease": True,
            "current_context_embedded_bytes_charged_with_lease": True,
            "future_writer_enforcement_required": True,
        },
        "durable_order_proven": False,
        "clock_provenance": "unproved-numeric-model-only",
        "same_uid_concurrent_writer": "outside-threat-model-stop-no-live-authority",
        "device_commands": [],
        "device_effects": [],
        "control_actions": [],
        "terminal_actions": [],
        "f1_actions": [],
        "partition_transfers": [],
        "callbacks": [],
        "backends": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--render-plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan exists in this permanent H0 leaf")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
