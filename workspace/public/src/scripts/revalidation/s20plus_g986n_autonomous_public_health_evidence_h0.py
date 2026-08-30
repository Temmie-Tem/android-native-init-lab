#!/usr/bin/env python3
"""Permanent H0 model for S20+ autonomous public-health evidence/accounting.

The current coordinator has no serializing public-health lease/completion
nodes.  This module is therefore permanently non-activatable: it exposes pure
parsers and protocol validators, but no private-filesystem writer, command
producer, callback, transport, or execution backend.  A later coordinator and
execution integration require a new reviewed implementation.
"""

from __future__ import annotations

import argparse
import ast
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
STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_EVIDENCE_PASS_GO_NOT_ACTIVE"
EVIDENCE_ACTIVE = False
LIVE_AUTHORITY = False
MECHANICALLY_ACTIVATABLE = False
COORDINATOR_INTEGRATED = False
PERMANENT_H0_ONLY = True

ACCOUNTING_OPENING_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_accounting_opening_v1"
)
READ_INTENT_SCHEMA = "s20plus_g986n_autonomous_public_health_read_intent_v1"
COMMAND_EVIDENCE_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_command_evidence_v1"
)
READ_RESULT_SCHEMA = "s20plus_g986n_autonomous_public_health_read_result_v1"
COORDINATOR_LEASE_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_read_lease_v1"
)
COORDINATOR_COMPLETE_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_read_complete_v1"
)
PLAN_SCHEMA = "s20plus_g986n_autonomous_public_health_evidence_plan_v1"

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

FIXED_ROOT = (
    ROOT
    / "workspace/private/runs/"
    "s20plus-g986n-autonomous-public-health-evidence"
)
FIXED_LEDGER_LAYOUT = (
    "campaigns/campaign-<sha256(campaign_id)>/sessions/"
    "session-<sha256(session_id)>"
)

READ_RESERVATION_BYTES = 512 * 1024
RAW_PAIR_MAX_BYTES = 64 * 1024
COMMAND_RECEIPT_MAX_BYTES = 8 * 1024
HEALTH_RESULT_MAX_BYTES = 64 * 1024
RAW_SET_PROOF_MAX_BYTES = 6 * RAW_PAIR_MAX_BYTES
RECEIPT_SET_PROOF_MAX_BYTES = 6 * COMMAND_RECEIPT_MAX_BYTES
TOTAL_EVIDENCE_PROOF_MAX_BYTES = (
    RAW_SET_PROOF_MAX_BYTES
    + RECEIPT_SET_PROOF_MAX_BYTES
    + HEALTH_RESULT_MAX_BYTES
)
if TOTAL_EVIDENCE_PROOF_MAX_BYTES != 507_904:
    raise RuntimeError("public-health byte proof differs")
if TOTAL_EVIDENCE_PROOF_MAX_BYTES >= READ_RESERVATION_BYTES:
    raise RuntimeError("public-health evidence does not fit its reservation")

CHILD_LIMITS = {
    "read_operations_max": 64,
    "private_evidence_bytes_max": 32 * 1024 * 1024,
}
CAMPAIGN_LIMITS = {
    "read_operations_max": 256,
    "private_evidence_bytes_max": 128 * 1024 * 1024,
}
COUNTER_KEYS = {
    "read_operations",
    "private_evidence_bytes_consumed",
    "private_evidence_bytes_reserved",
}
CONTROL_COUNTER_KEYS = {
    "control_transactions",
    "component_effects_consumed",
    "component_effects_reserved",
    "normal_reboots",
    "download_roundtrips",
    "roundtrip_entries",
    "roundtrip_returns",
}
CONTROL_CHILD_LIMITS = {
    "control_transactions_max": 16,
    "component_effects_max": 24,
    "normal_reboots_max": 8,
    "download_roundtrips_max": 8,
}
CONTROL_CAMPAIGN_LIMITS = {
    "control_transactions_max": 64,
    "component_effects_max": 96,
    "normal_reboots_max": 32,
    "download_roundtrips_max": 32,
}
COORDINATOR_CAMPAIGN_DURATION_SECONDS = 24 * 60 * 60
COORDINATOR_SESSION_DURATION_SECONDS = 4 * 60 * 60
COORDINATOR_BINDING_SHA256 = (
    "0299b3a3ddbd0e496f46092b0f547ce24064e66636b90274a574d86007b9be82"
)
MAX_LEDGER_CHILDREN = 256
MAX_READ_ORDINAL = 999_999
MAX_JSON_BYTES = 1024 * 1024
ZERO_HASH = "0" * 64
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
DEVPATH_RE = re.compile(r"usb:[0-9]+-[0-9]+(?:\.[0-9]+)*\Z")
SAFE_VALUE_RE = re.compile(r"[^\x00\r\n]{0,4096}\Z")
SHELL_ID_RE = re.compile(
    r"uid=2000\(shell\) gid=2000\(shell\)(?: [^\x00\r\n]+)?\Z"
)
CAMPAIGN_DIRECTORY_RE = re.compile(r"campaign-[0-9a-f]{64}\Z")
SESSION_DIRECTORY_RE = re.compile(r"session-[0-9a-f]{64}\Z")

SOURCE_SPECS = MappingProxyType({
    "coordinator": MappingProxyType({
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_autonomous_research_coordinator_h0.py",
        "size": 105_904,
        "sha256": "87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd",
    }),
    "health": MappingProxyType({
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_autonomous_health_h0.py",
        "size": 13_908,
        "sha256": "03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b",
    }),
    "inventory": MappingProxyType({
        "path": ROOT
        / "workspace/public/src/scripts/revalidation/"
        "s20plus_g986n_d0_inventory.py",
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    }),
})


class EvidenceH0Error(RuntimeError):
    """Malformed sources, retained returns, leases, or counters fail closed."""


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
        raise EvidenceH0Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def parse_canonical_json(payload: bytes, label: str) -> Any:
    if type(payload) is not bytes or len(payload) > MAX_JSON_BYTES:
        raise EvidenceH0Error(f"{label} is oversized or not bytes")
    try:
        result = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise EvidenceH0Error(f"{label} is not strict JSON") from exc
    if canonical_bytes(result) != payload:
        raise EvidenceH0Error(f"{label} is not canonical JSON")
    return result


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


def _make_fixed_source_reader(
    fixed_specs: Mapping[str, Mapping[str, Any]],
):
    def read_fixed_source(label: str) -> tuple[bytes, dict[str, Any]]:
        if label not in fixed_specs:
            raise EvidenceH0Error("source label is outside the fixed closure")
        spec = fixed_specs[label]
        path = Path(spec["path"])
        descriptor = -1
        try:
            descriptor = _open(path, _O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
            before = _fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_size != spec["size"]
            ):
                raise EvidenceH0Error(f"{label} source identity differs")
            data = bytearray()
            while len(data) < before.st_size:
                chunk = _read(
                    descriptor, min(1024 * 1024, before.st_size - len(data))
                )
                if not chunk:
                    break
                data.extend(chunk)
            if len(data) != before.st_size or _read(descriptor, 1):
                raise EvidenceH0Error(f"{label} source length differs")
            after = _fstat(descriptor)
        except OSError as exc:
            raise EvidenceH0Error(f"{label} source is unavailable") from exc
        finally:
            if descriptor >= 0:
                _close(descriptor)
        current = _stat(path, follow_symlinks=False)
        if _metadata(before) != _metadata(after) or _metadata(after) != _metadata(current):
            raise EvidenceH0Error(f"{label} source changed while read")
        payload = bytes(data)
        if sha256_bytes(payload) != spec["sha256"]:
            raise EvidenceH0Error(f"{label} source bytes differ")
        return payload, {
            "path": str(path),
            "size": len(payload),
            "sha256": sha256_bytes(payload),
        }

    return read_fixed_source


_read_fixed_source = _make_fixed_source_reader(SOURCE_SPECS)
del _make_fixed_source_reader


def _literal_assignment(payload: bytes, name: str) -> Any:
    tree = ast.parse(payload.decode("utf-8", "strict"))
    matches: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                matches.append(node.value)
    if len(matches) != 1:
        raise EvidenceH0Error(f"source assignment {name} is missing or ambiguous")
    try:
        return ast.literal_eval(matches[0])
    except (ValueError, TypeError) as exc:
        raise EvidenceH0Error(f"source assignment {name} is not literal") from exc


_COORDINATOR_SOURCE, _COORDINATOR_RECEIPT = _read_fixed_source("coordinator")
_HEALTH_SOURCE, _HEALTH_RECEIPT = _read_fixed_source("health")
_INVENTORY_SOURCE, _INVENTORY_RECEIPT = _read_fixed_source("inventory")

PROPERTY_KEYS = tuple(_literal_assignment(_INVENTORY_SOURCE, "PROPERTY_KEYS"))
REMOTE_SNAPSHOT = _literal_assignment(_INVENTORY_SOURCE, "REMOTE_SNAPSHOT")
INVENTORY_SCHEMA = _literal_assignment(_INVENTORY_SOURCE, "SCHEMA")
INVENTORY_VERSION = _literal_assignment(_INVENTORY_SOURCE, "VERSION")
INVENTORY_VERDICT = _literal_assignment(_INVENTORY_SOURCE, "VERDICT")
EXPECTED_ADB_SHA256 = _literal_assignment(_INVENTORY_SOURCE, "EXPECTED_ADB_SHA256")
FIXED_TRANSCRIPT = tuple(_literal_assignment(_HEALTH_SOURCE, "FIXED_TRANSCRIPT"))
CONTEXT_KEYS = tuple(_literal_assignment(_COORDINATOR_SOURCE, "_CONTEXT_BINDING_KEYS"))
COORDINATOR_SCHEMA = _literal_assignment(_COORDINATOR_SOURCE, "SCHEMA")
COORDINATOR_NORMALIZED_SHA256 = _literal_assignment(
    _COORDINATOR_SOURCE, "EXPECTED_COORDINATOR_NORMALIZED_SHA256"
)

if (
    _literal_assignment(_INVENTORY_SOURCE, "EXPECTED_MODEL") != TARGET["model"]
    or _literal_assignment(_HEALTH_SOURCE, "TARGET") != TARGET
    or _literal_assignment(_COORDINATOR_SOURCE, "TARGET") != TARGET
    or len(FIXED_TRANSCRIPT) != 6
    or any(
        item["ordinal"] != ordinal or item["max_bytes"] != RAW_PAIR_MAX_BYTES
        for ordinal, item in enumerate(FIXED_TRANSCRIPT, 1)
    )
):
    raise EvidenceH0Error("source literals differ from the fixed target/transcript")

EVIDENCE_NAMES = tuple(
    sorted(
        [
            f"cmd-{ordinal:02d}.{suffix}"
            for ordinal in range(1, 7)
            for suffix in ("stdout.bin", "stderr.bin", "receipt.json")
        ]
        + ["health.json"]
    )
)
RETURN_NAMES = tuple(name for name in EVIDENCE_NAMES if name != "health.json")


def _self_bytes() -> tuple[bytes, dict[str, Any]]:
    path = Path(__file__).resolve(strict=True)
    descriptor = _open(path, _O_RDONLY | _O_CLOEXEC | _O_NOFOLLOW)
    try:
        before = _fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > 2 * 1024 * 1024
        ):
            raise EvidenceH0Error("owner source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = _read(descriptor, min(1024 * 1024, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or _read(descriptor, 1):
            raise EvidenceH0Error("owner source length differs")
        after = _fstat(descriptor)
    finally:
        _close(descriptor)
    current = _stat(path, follow_symlinks=False)
    if _metadata(before) != _metadata(after) or _metadata(after) != _metadata(current):
        raise EvidenceH0Error("owner source changed while read")
    payload = bytes(data)
    return payload, {
        "path": str(path),
        "size": len(payload),
        "sha256": sha256_bytes(payload),
    }


def normalized_self_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise EvidenceH0Error("self normalization requires exact bytes")
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
            raise EvidenceH0Error("self activation normalization is ambiguous")
    return sha256_bytes(normalized)


def self_receipt() -> dict[str, Any]:
    payload, receipt = _self_bytes()
    return {**receipt, "normalized_sha256": normalized_self_sha256(payload)}


def source_receipts() -> dict[str, Any]:
    current = {
        label: _read_fixed_source(label)[1]
        for label in ("coordinator", "health", "inventory")
    }
    return {"owner": self_receipt(), **current}


def _require_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise EvidenceH0Error(f"{label} is not a bounded integer")
    return value


def _require_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise EvidenceH0Error(f"{label} is not lowercase SHA-256")
    return value


def _require_id(value: Any, label: str) -> str:
    if type(value) is not str or ID_RE.fullmatch(value) is None:
        raise EvidenceH0Error(f"{label} is not a fixed identifier")
    return value


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise EvidenceH0Error(f"{label} keys differ")


def zero_counters() -> dict[str, int]:
    return {key: 0 for key in sorted(COUNTER_KEYS)}


def validate_counters(value: Any, limits: Mapping[str, int], label: str) -> dict[str, int]:
    _exact_keys(value, COUNTER_KEYS, label)
    result = {key: _require_int(value[key], f"{label}.{key}") for key in COUNTER_KEYS}
    if result["read_operations"] > limits["read_operations_max"]:
        raise EvidenceH0Error(f"{label} read limit exceeded")
    if (
        result["private_evidence_bytes_consumed"]
        + result["private_evidence_bytes_reserved"]
        > limits["private_evidence_bytes_max"]
    ):
        raise EvidenceH0Error(f"{label} byte limit exceeded")
    if result["private_evidence_bytes_reserved"] not in (0, READ_RESERVATION_BYTES):
        raise EvidenceH0Error(f"{label} reservation differs")
    completed_reads = result["read_operations"] - (
        1 if result["private_evidence_bytes_reserved"] else 0
    )
    if completed_reads < 0 or result["private_evidence_bytes_consumed"] > (
        completed_reads * TOTAL_EVIDENCE_PROOF_MAX_BYTES
    ):
        raise EvidenceH0Error(f"{label} consumed bytes exceed completed reads")
    return result


def reserve_counters(value: Any, limits: Mapping[str, int], label: str) -> dict[str, int]:
    result = validate_counters(value, limits, label)
    if result["private_evidence_bytes_reserved"] != 0:
        raise EvidenceH0Error(f"{label} has an unresolved reservation")
    result["read_operations"] += 1
    result["private_evidence_bytes_reserved"] = READ_RESERVATION_BYTES
    return validate_counters(result, limits, label)


def settle_counters(
    value: Any, actual: int, limits: Mapping[str, int], label: str
) -> dict[str, int]:
    result = validate_counters(value, limits, label)
    measured = _require_int(actual, "actual evidence bytes")
    if (
        result["private_evidence_bytes_reserved"] != READ_RESERVATION_BYTES
        or measured > TOTAL_EVIDENCE_PROOF_MAX_BYTES
    ):
        raise EvidenceH0Error("settlement lacks or exceeds reservation")
    result["private_evidence_bytes_reserved"] = 0
    result["private_evidence_bytes_consumed"] += measured
    return validate_counters(result, limits, label)


def validate_scope_relation(
    child: Mapping[str, int], campaign: Mapping[str, int], label: str
) -> None:
    if any(campaign[key] != child[key] for key in COUNTER_KEYS):
        raise EvidenceH0Error(f"{label} child/campaign accounting differs")


def validate_control_counters(
    value: Any, limits: Mapping[str, int], label: str
) -> dict[str, int]:
    _exact_keys(value, CONTROL_COUNTER_KEYS, label)
    result = {key: _require_int(value[key], f"{label}.{key}") for key in value}
    unresolved = result["roundtrip_entries"] - result["roundtrip_returns"]
    total_effects = (
        result["component_effects_consumed"]
        + result["component_effects_reserved"]
    )
    if (
        result["download_roundtrips"] != result["roundtrip_entries"]
        or unresolved not in (0, 1)
        or result["component_effects_reserved"] != unresolved
        or result["control_transactions"]
        != result["normal_reboots"] + result["download_roundtrips"]
        or result["component_effects_consumed"]
        != result["normal_reboots"]
        + result["roundtrip_entries"]
        + result["roundtrip_returns"]
        or result["control_transactions"] > limits["control_transactions_max"]
        or total_effects > limits["component_effects_max"]
        or result["normal_reboots"] > limits["normal_reboots_max"]
        or result["download_roundtrips"] > limits["download_roundtrips_max"]
    ):
        raise EvidenceH0Error(f"{label} relationships differ")
    return result


def validate_control_scope_relation(
    child: Mapping[str, int], campaign: Mapping[str, int], label: str
) -> None:
    monotonic = (
        "control_transactions",
        "component_effects_consumed",
        "normal_reboots",
        "download_roundtrips",
        "roundtrip_entries",
        "roundtrip_returns",
    )
    if (
        any(campaign[key] < child[key] for key in monotonic)
        or campaign["component_effects_reserved"]
        != child["component_effects_reserved"]
    ):
        raise EvidenceH0Error(f"{label} control scopes differ")


def validate_source_identity(value: Any, label: str) -> dict[str, Any]:
    keys = {
        "target",
        "serial_sha256",
        "topology_sha256",
        "boot_id_sha256",
        "healthy_android",
        "foreign_guard_present",
    }
    _exact_keys(value, keys, label)
    if value["target"] != TARGET:
        raise EvidenceH0Error(f"{label} target differs")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        _require_hex(value[key], f"{label}.{key}")
    if value["healthy_android"] is not True or value["foreign_guard_present"] is not False:
        raise EvidenceH0Error(f"{label} is not exact healthy Android")
    return dict(value)


def validate_context(value: Any, campaign_id: str, session_id: str) -> dict[str, Any]:
    _exact_keys(value, set(CONTEXT_KEYS), "coordinator context")
    if (
        value["campaign_id"] != campaign_id
        or value["session_id"] != session_id
        or value["phase"] != "healthy-normal"
        or value["expired"] is not False
        or value["session_expired"] is not False
        or value["endpoint"] is not None
        or value["terminal"] is not None
        or value["pending_intent_issued_at"] is not None
        or value["f1_intent"] is not False
        or value["approval_consumed"] is not False
        or value["partition_transfer"] is not False
        or value["no_replay"] is not True
    ):
        raise EvidenceH0Error("coordinator context is not healthy and unblocked")
    current = _require_int(value["current_time"], "context current_time")
    campaign_expiry = _require_int(value["campaign_expires_at"], "campaign expiry")
    session_expiry = _require_int(value["session_expires_at"], "session expiry")
    if current >= campaign_expiry or current >= session_expiry:
        raise EvidenceH0Error("coordinator context is expired")
    if session_expiry > campaign_expiry:
        raise EvidenceH0Error("coordinator session expiry exceeds campaign expiry")
    ordinal = _require_int(value["current_ordinal"], "context ordinal")
    _require_hex(value["predecessor_sha256"], "context head")
    validate_source_identity(value["source_identity"], "context source")
    child = validate_control_counters(
        value["child_counters"],
        CONTROL_CHILD_LIMITS,
        "context child control counters",
    )
    campaign = validate_control_counters(
        value["campaign_counters"],
        CONTROL_CAMPAIGN_LIMITS,
        "context campaign control counters",
    )
    if ordinal != campaign["download_roundtrips"]:
        raise EvidenceH0Error("context action ordinal differs from campaign chain")
    validate_control_scope_relation(child, campaign, "coordinator context")
    if child["component_effects_reserved"] or campaign["component_effects_reserved"]:
        raise EvidenceH0Error("healthy context retains a control reservation")
    return dict(value)


COORDINATOR_OPENING_KEYS = {
    "schema",
    "kind",
    "campaign_id",
    "session_id",
    "target",
    "policy_binding_sha256",
    "coordinator_normalized_sha256",
    "source_identity",
    "opened_at",
    "expires_at",
    "campaign_counters",
    "child_counters",
    "predecessor_sha256",
    "attended_opening",
    "no_replay",
    "f1_intent",
    "approval_consumed",
    "partition_transfer",
}
COORDINATOR_SESSION_KEYS = {
    "schema",
    "kind",
    "campaign_id",
    "session_id",
    "target",
    "policy_binding_sha256",
    "coordinator_normalized_sha256",
    "source_identity",
    "opened_at",
    "expires_at",
    "campaign_counters",
    "child_counters",
    "predecessor_sha256",
    "no_replay",
}
COORDINATOR_GUARD_KEYS = {
    "schema",
    "kind",
    "phase",
    "campaign_id",
    "session_id",
    "target",
    "policy_binding_sha256",
    "coordinator_normalized_sha256",
    "source_identity",
    "opened_at",
    "expires_at",
    "opening_sha256",
    "session_opening_sha256",
    "opening",
    "session",
    "campaign_counters",
    "child_counters",
    "no_replay",
    "f1_intent",
    "approval_consumed",
    "partition_transfer",
}
ALLOCATION_KEYS = {
    "campaign_id",
    "session_id",
    "target",
    "guard",
    "guard_raw",
    "opening",
    "opening_raw",
    "session",
    "session_raw",
}
ACCOUNTING_OPENING_KEYS = {
    "schema",
    "kind",
    "recorded_at",
    "campaign_id",
    "session_id",
    "target",
    "allocation_source_identity",
    "source_identity",
    "sources",
    "coordinator_guard",
    "coordinator_opening",
    "coordinator_session",
    "coordinator_guard_sha256",
    "coordinator_opening_sha256",
    "coordinator_session_sha256",
    "first_current_context",
    "first_current_context_sha256",
    "first_coordinator_head",
    "first_coordinator_head_sha256",
    "child_counters",
    "campaign_counters",
    "attended_opening",
    "no_replay",
    "command_execution_backend",
}


def _zero_control_counters() -> dict[str, int]:
    return {key: 0 for key in sorted(CONTROL_COUNTER_KEYS)}


def _validated_raw_node(
    node: Any, raw: Any, keys: set[str], label: str
) -> tuple[dict[str, Any], bytes]:
    _exact_keys(node, keys, label)
    if (
        type(raw) is not bytes
        or len(raw) > MAX_JSON_BYTES
        or canonical_bytes(node) != raw
        or parse_canonical_json(raw, label) != node
    ):
        raise EvidenceH0Error(f"{label} raw bytes are not exact canonical bytes")
    return dict(node), raw


def _validated_current_head(node: Any, raw: bytes, label: str) -> dict[str, Any]:
    if type(node) is not dict or not node:
        raise EvidenceH0Error(f"{label} is not a coordinator node")
    if (
        type(raw) is not bytes
        or len(raw) > MAX_JSON_BYTES
        or canonical_bytes(node) != raw
        or parse_canonical_json(raw, label) != node
    ):
        raise EvidenceH0Error(f"{label} bytes are not exact canonical bytes")
    return dict(node)


def _validate_current_head_semantics(
    head: Mapping[str, Any],
    context: Mapping[str, Any],
    label: str,
    *,
    exact_session: Mapping[str, Any],
) -> None:
    if head != exact_session:
        raise EvidenceH0Error(f"{label} is not the exact allocation session")
    child = validate_control_counters(
        head["child_counters"], CONTROL_CHILD_LIMITS, f"{label} child"
    )
    campaign = validate_control_counters(
        head["campaign_counters"],
        CONTROL_CAMPAIGN_LIMITS,
        f"{label} campaign",
    )
    validate_control_scope_relation(child, campaign, label)
    if (
        head["source_identity"] != context["source_identity"]
        or child != context["child_counters"]
        or campaign != context["campaign_counters"]
    ):
        raise EvidenceH0Error(f"{label} session/context differs")


def _validate_coordinator_allocation(
    allocation: Any,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _exact_keys(allocation, ALLOCATION_KEYS, "coordinator allocation")
    campaign_id = _require_id(allocation["campaign_id"], "campaign id")
    session_id = _require_id(allocation["session_id"], "session id")
    if allocation["target"] != TARGET:
        raise EvidenceH0Error("allocation target differs")
    opening, opening_raw = _validated_raw_node(
        allocation["opening"],
        allocation["opening_raw"],
        COORDINATOR_OPENING_KEYS,
        "coordinator campaign opening",
    )
    session, session_raw = _validated_raw_node(
        allocation["session"],
        allocation["session_raw"],
        COORDINATOR_SESSION_KEYS,
        "coordinator session opening",
    )
    guard, _ = _validated_raw_node(
        allocation["guard"],
        allocation["guard_raw"],
        COORDINATOR_GUARD_KEYS,
        "coordinator campaign guard",
    )
    source = validate_source_identity(opening["source_identity"], "opening source")
    opened = _require_int(opening["opened_at"], "opening opened_at")
    campaign_expiry = _require_int(opening["expires_at"], "opening expiry")
    session_opened = _require_int(session["opened_at"], "session opened_at")
    session_expiry = _require_int(session["expires_at"], "session expiry")
    opening_child = validate_control_counters(
        opening["child_counters"], CONTROL_CHILD_LIMITS, "opening child counters"
    )
    opening_campaign = validate_control_counters(
        opening["campaign_counters"],
        CONTROL_CAMPAIGN_LIMITS,
        "opening campaign counters",
    )
    session_child = validate_control_counters(
        session["child_counters"], CONTROL_CHILD_LIMITS, "session child counters"
    )
    session_campaign = validate_control_counters(
        session["campaign_counters"],
        CONTROL_CAMPAIGN_LIMITS,
        "session campaign counters",
    )
    guard_child = validate_control_counters(
        guard["child_counters"], CONTROL_CHILD_LIMITS, "guard child counters"
    )
    guard_campaign = validate_control_counters(
        guard["campaign_counters"],
        CONTROL_CAMPAIGN_LIMITS,
        "guard campaign counters",
    )
    policy_binding = _require_hex(
        opening["policy_binding_sha256"], "opening policy binding"
    )
    coordinator_binding = _require_hex(
        opening["coordinator_normalized_sha256"], "opening coordinator binding"
    )
    if (
        opening["schema"] != COORDINATOR_SCHEMA
        or opening["kind"] != "campaign-opening"
        or opening["campaign_id"] != campaign_id
        or opening["session_id"] != session_id
        or opening["target"] != TARGET
        or policy_binding != COORDINATOR_BINDING_SHA256
        or coordinator_binding != COORDINATOR_NORMALIZED_SHA256
        or opening["predecessor_sha256"] != ZERO_HASH
        or opening["attended_opening"] is not True
        or opening["no_replay"] is not True
        or any(
            opening[key] is not False
            for key in ("f1_intent", "approval_consumed", "partition_transfer")
        )
        or campaign_expiry - opened != COORDINATOR_CAMPAIGN_DURATION_SECONDS
        or opening_child != _zero_control_counters()
        or opening_campaign != _zero_control_counters()
    ):
        raise EvidenceH0Error("coordinator campaign opening semantics differ")
    if (
        session["schema"] != COORDINATOR_SCHEMA
        or session["kind"] != "session-opening"
        or session["campaign_id"] != campaign_id
        or session["session_id"] != session_id
        or session["target"] != TARGET
        or session["policy_binding_sha256"] != policy_binding
        or session["coordinator_normalized_sha256"] != coordinator_binding
        or session["source_identity"] != source
        or session_opened != opened
        or session_expiry - session_opened != COORDINATOR_SESSION_DURATION_SECONDS
        or session_expiry > campaign_expiry
        or session["predecessor_sha256"] != sha256_bytes(opening_raw)
        or session["no_replay"] is not True
        or session_child != opening_child
        or session_campaign != opening_campaign
    ):
        raise EvidenceH0Error("coordinator session opening semantics differ")
    if (
        guard["schema"] != COORDINATOR_SCHEMA
        or guard["kind"] != "campaign-guard"
        or guard["phase"] != "allocation-claimed"
        or guard["campaign_id"] != campaign_id
        or guard["session_id"] != session_id
        or guard["target"] != TARGET
        or guard["policy_binding_sha256"] != policy_binding
        or guard["coordinator_normalized_sha256"] != coordinator_binding
        or guard["source_identity"] != source
        or guard["opened_at"] != opened
        or guard["expires_at"] != campaign_expiry
        or guard["opening_sha256"] != sha256_bytes(opening_raw)
        or guard["session_opening_sha256"] != sha256_bytes(session_raw)
        or guard["opening"] != opening
        or guard["session"] != session
        or guard_child != opening_child
        or guard_campaign != opening_campaign
        or guard["no_replay"] is not True
        or any(
            guard[key] is not False
            for key in ("f1_intent", "approval_consumed", "partition_transfer")
        )
    ):
        raise EvidenceH0Error("coordinator campaign guard semantics differ")
    return guard, opening, session


def model_accounting_opening(
    allocation: Any,
    current_context: Any,
    current_context_raw: bytes,
    current_head: Any,
    current_head_raw: bytes,
    recorded_at: int,
) -> dict[str, Any]:
    """Pure model only; it cannot read or publish either private root."""

    guard, coordinator_opening, coordinator_session = (
        _validate_coordinator_allocation(allocation)
    )
    campaign_id = allocation["campaign_id"]
    session_id = allocation["session_id"]
    context = validate_context(current_context, campaign_id, session_id)
    if type(current_context_raw) is not bytes or canonical_bytes(context) != current_context_raw:
        raise EvidenceH0Error("current coordinator context bytes are not canonical")
    head = _validated_current_head(
        current_head, current_head_raw, "current coordinator head"
    )
    if sha256_bytes(current_head_raw) != context["predecessor_sha256"]:
        raise EvidenceH0Error("current coordinator head/context predecessor differs")
    _validate_current_head_semantics(
        head,
        context,
        "current coordinator head",
        exact_session=coordinator_session,
    )
    source = validate_source_identity(context["source_identity"], "current source")
    allocation_source = validate_source_identity(
        coordinator_opening["source_identity"], "allocation source"
    )
    opened = coordinator_opening["opened_at"]
    campaign_expiry = coordinator_opening["expires_at"]
    session_expiry = coordinator_session["expires_at"]
    if (
        opened > context["current_time"]
        or campaign_expiry != context["campaign_expires_at"]
        or session_expiry != context["session_expires_at"]
    ):
        raise EvidenceH0Error("allocation/current context time differs")
    recorded = _require_int(recorded_at, "accounting recorded_at")
    if (
        recorded != context["current_time"]
        or recorded >= campaign_expiry
        or recorded >= session_expiry
    ):
        raise EvidenceH0Error("accounting opening is outside the current lease window")
    child_read = zero_counters()
    campaign_read = zero_counters()
    return {
        "schema": ACCOUNTING_OPENING_SCHEMA,
        "kind": "accounting-opening",
        "recorded_at": recorded,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": TARGET,
        "allocation_source_identity": allocation_source,
        "source_identity": source,
        "sources": source_receipts(),
        "coordinator_guard": guard,
        "coordinator_opening": coordinator_opening,
        "coordinator_session": coordinator_session,
        "coordinator_guard_sha256": sha256_bytes(allocation["guard_raw"]),
        "coordinator_opening_sha256": sha256_bytes(allocation["opening_raw"]),
        "coordinator_session_sha256": sha256_bytes(allocation["session_raw"]),
        "first_current_context": context,
        "first_current_context_sha256": sha256_bytes(current_context_raw),
        "first_coordinator_head": head,
        "first_coordinator_head_sha256": sha256_bytes(current_head_raw),
        "child_counters": child_read,
        "campaign_counters": campaign_read,
        "attended_opening": True,
        "no_replay": True,
        "command_execution_backend": False,
    }


def validate_accounting_opening(
    opening: Any, opening_raw: bytes
) -> dict[str, Any]:
    _exact_keys(opening, ACCOUNTING_OPENING_KEYS, "accounting opening")
    if type(opening_raw) is not bytes or canonical_bytes(opening) != opening_raw:
        raise EvidenceH0Error("accounting opening bytes are not exact canonical bytes")
    campaign_id = _require_id(opening["campaign_id"], "accounting campaign id")
    session_id = _require_id(opening["session_id"], "accounting session id")
    allocation_source = validate_source_identity(
        opening["allocation_source_identity"], "accounting allocation source"
    )
    current_source = validate_source_identity(
        opening["source_identity"], "accounting current source"
    )
    reconstructed_allocation = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": opening["target"],
        "guard": opening["coordinator_guard"],
        "guard_raw": canonical_bytes(opening["coordinator_guard"]),
        "opening": opening["coordinator_opening"],
        "opening_raw": canonical_bytes(opening["coordinator_opening"]),
        "session": opening["coordinator_session"],
        "session_raw": canonical_bytes(opening["coordinator_session"]),
    }
    guard, coordinator_opening, coordinator_session = (
        _validate_coordinator_allocation(reconstructed_allocation)
    )
    context = validate_context(
        opening["first_current_context"], campaign_id, session_id
    )
    first_head_raw = canonical_bytes(opening["first_coordinator_head"])
    _validated_current_head(
        opening["first_coordinator_head"],
        first_head_raw,
        "accounting first coordinator head",
    )
    _validate_current_head_semantics(
        opening["first_coordinator_head"],
        context,
        "accounting first coordinator head",
        exact_session=coordinator_session,
    )
    recorded = _require_int(opening["recorded_at"], "accounting recorded_at")
    for key in (
        "coordinator_guard_sha256",
        "coordinator_opening_sha256",
        "coordinator_session_sha256",
        "first_current_context_sha256",
        "first_coordinator_head_sha256",
    ):
        _require_hex(opening[key], f"accounting {key}")
    if (
        opening["schema"] != ACCOUNTING_OPENING_SCHEMA
        or opening["kind"] != "accounting-opening"
        or opening["target"] != TARGET
        or opening["attended_opening"] is not True
        or opening["no_replay"] is not True
        or opening["command_execution_backend"] is not False
        or opening["sources"] != source_receipts()
        or opening["coordinator_guard_sha256"]
        != sha256_bytes(canonical_bytes(guard))
        or opening["coordinator_opening_sha256"]
        != sha256_bytes(canonical_bytes(coordinator_opening))
        or opening["coordinator_session_sha256"]
        != sha256_bytes(canonical_bytes(coordinator_session))
        or allocation_source != coordinator_opening["source_identity"]
        or context["source_identity"] != current_source
        or opening["first_current_context_sha256"]
        != sha256_bytes(canonical_bytes(context))
        or opening["first_coordinator_head_sha256"]
        != sha256_bytes(first_head_raw)
        or opening["first_coordinator_head_sha256"]
        != context["predecessor_sha256"]
        or recorded != context["current_time"]
        or recorded >= context["campaign_expires_at"]
        or recorded >= context["session_expires_at"]
    ):
        raise EvidenceH0Error("accounting opening schema differs")
    child = validate_counters(
        opening["child_counters"], CHILD_LIMITS, "opening child read counters"
    )
    campaign = validate_counters(
        opening["campaign_counters"],
        CAMPAIGN_LIMITS,
        "opening campaign read counters",
    )
    if child["read_operations"] != 0 or child["private_evidence_bytes_reserved"]:
        raise EvidenceH0Error("accounting opening child state is not fresh")
    validate_scope_relation(child, campaign, "accounting opening")
    if campaign != zero_counters():
        raise EvidenceH0Error("initial attended session campaign read state is not fresh")
    return dict(opening)


def initial_protocol_state(
    opening: Mapping[str, Any], opening_raw: bytes
) -> dict[str, Any]:
    opening = validate_accounting_opening(opening, opening_raw)
    child = opening["child_counters"]
    campaign = opening["campaign_counters"]
    return {
        "read_ordinal": 0,
        "previous_evidence_result_sha256": ZERO_HASH,
        "previous_coordinator_complete_sha256": ZERO_HASH,
        "child_counters": child,
        "campaign_counters": campaign,
        "campaign_parked": False,
    }


LEASE_KEYS = {
    "schema",
    "kind",
    "issued_at",
    "campaign_id",
    "session_id",
    "target",
    "action",
    "read_ordinal",
    "accounting_opening_sha256",
    "coordinator_context",
    "coordinator_context_sha256",
    "coordinator_head",
    "coordinator_head_sha256",
    "source_identity",
    "previous_evidence_result_sha256",
    "previous_coordinator_complete_sha256",
    "previous_child_counters",
    "previous_campaign_counters",
    "child_counters",
    "campaign_counters",
    "reservation_bytes",
    "expected_host_tool",
    "attempt_consumed",
    "replay_authorized",
    "controls_blocked",
    "terminal_blocked",
    "completion_required",
}
PROTOCOL_STATE_KEYS = {
    "read_ordinal",
    "previous_evidence_result_sha256",
    "previous_coordinator_complete_sha256",
    "child_counters",
    "campaign_counters",
    "campaign_parked",
}


def expected_host_tool() -> dict[str, Any]:
    return {
        "path": "/usr/lib/android-sdk/platform-tools/adb",
        "size": 716_968,
        "sha256": EXPECTED_ADB_SHA256,
    }


def validate_protocol_state(value: Any) -> dict[str, Any]:
    _exact_keys(value, PROTOCOL_STATE_KEYS, "protocol state")
    ordinal = _require_int(value["read_ordinal"], "protocol read ordinal")
    if ordinal > CHILD_LIMITS["read_operations_max"]:
        raise EvidenceH0Error("protocol read ordinal exceeds child limit")
    _require_hex(
        value["previous_evidence_result_sha256"],
        "protocol previous evidence result",
    )
    _require_hex(
        value["previous_coordinator_complete_sha256"],
        "protocol previous coordinator completion",
    )
    child = validate_counters(
        value["child_counters"], CHILD_LIMITS, "protocol child counters"
    )
    campaign = validate_counters(
        value["campaign_counters"], CAMPAIGN_LIMITS, "protocol campaign counters"
    )
    if type(value["campaign_parked"]) is not bool:
        raise EvidenceH0Error("protocol parked state is not boolean")
    validate_scope_relation(child, campaign, "protocol state")
    fresh = (
        ordinal == 0
        and value["campaign_parked"] is False
        and value["previous_evidence_result_sha256"] == ZERO_HASH
        and value["previous_coordinator_complete_sha256"] == ZERO_HASH
        and child == zero_counters()
        and campaign == zero_counters()
    )
    terminal = (
        ordinal == 1
        and value["campaign_parked"] is True
        and value["previous_evidence_result_sha256"] != ZERO_HASH
        and value["previous_coordinator_complete_sha256"] != ZERO_HASH
        and child["read_operations"] == 1
        and child["private_evidence_bytes_reserved"] == 0
        and 0 < child["private_evidence_bytes_consumed"]
        <= TOTAL_EVIDENCE_PROOF_MAX_BYTES
    )
    if not (fresh or terminal):
        raise EvidenceH0Error("protocol state is not exact fresh or parked terminal")
    return {
        **dict(value),
        "child_counters": child,
        "campaign_counters": campaign,
    }


def validate_future_lease(
    lease: Any,
    lease_raw: bytes,
    opening: Mapping[str, Any],
    opening_raw: bytes,
    state: Mapping[str, Any],
    observed_at: int,
) -> dict[str, Any]:
    _exact_keys(lease, LEASE_KEYS, "future coordinator lease")
    if type(lease_raw) is not bytes or canonical_bytes(lease) != lease_raw:
        raise EvidenceH0Error("future coordinator lease is noncanonical")
    state = validate_protocol_state(state)
    if state["campaign_parked"] is not False:
        raise EvidenceH0Error("parked campaign cannot issue another read lease")
    if state["read_ordinal"] != 0:
        raise EvidenceH0Error("this permanent H0 models only the first session read")
    opening = validate_accounting_opening(opening, opening_raw)
    ordinal = _require_int(lease["read_ordinal"], "lease ordinal", 1)
    if ordinal > MAX_READ_ORDINAL or ordinal != state["read_ordinal"] + 1:
        raise EvidenceH0Error("lease ordinal is not the next evidence ordinal")
    campaign_id = opening["campaign_id"]
    session_id = opening["session_id"]
    context = validate_context(lease["coordinator_context"], campaign_id, session_id)
    head_raw = canonical_bytes(lease["coordinator_head"])
    _validated_current_head(
        lease["coordinator_head"], head_raw, "lease coordinator head"
    )
    _validate_current_head_semantics(
        lease["coordinator_head"],
        context,
        "lease coordinator head",
        exact_session=opening["coordinator_session"],
    )
    issued = _require_int(lease["issued_at"], "lease issued_at")
    observed = _require_int(observed_at, "lease observed_at")
    if (
        issued > observed
        or issued != context["current_time"]
        or issued >= context["campaign_expires_at"]
        or issued >= context["session_expires_at"]
    ):
        raise EvidenceH0Error("lease was not issued from a current pre-expiry head")
    previous_child = validate_counters(
        lease["previous_child_counters"], CHILD_LIMITS, "lease previous child"
    )
    previous_campaign = validate_counters(
        lease["previous_campaign_counters"], CAMPAIGN_LIMITS, "lease previous campaign"
    )
    expected_child = reserve_counters(previous_child, CHILD_LIMITS, "lease child")
    expected_campaign = reserve_counters(
        previous_campaign, CAMPAIGN_LIMITS, "lease campaign"
    )
    validate_scope_relation(previous_child, previous_campaign, "lease predecessor")
    validate_scope_relation(expected_child, expected_campaign, "lease debit")
    if (
        lease["schema"] != COORDINATOR_LEASE_SCHEMA
        or lease["kind"] != "public-health-read-lease"
        or lease["campaign_id"] != campaign_id
        or lease["session_id"] != session_id
        or lease["target"] != TARGET
        or lease["action"] != "public-health"
        or lease["accounting_opening_sha256"]
        != sha256_bytes(canonical_bytes(opening))
        or lease["coordinator_context_sha256"]
        != sha256_bytes(canonical_bytes(context))
        or lease["coordinator_head_sha256"] != sha256_bytes(head_raw)
        or lease["coordinator_head_sha256"] != context["predecessor_sha256"]
        or lease["source_identity"] != context["source_identity"]
        or lease["source_identity"] != opening["source_identity"]
        or lease["previous_evidence_result_sha256"]
        != state["previous_evidence_result_sha256"]
        or lease["previous_coordinator_complete_sha256"]
        != state["previous_coordinator_complete_sha256"]
        or previous_child != state["child_counters"]
        or previous_campaign != state["campaign_counters"]
        or lease["child_counters"] != expected_child
        or lease["campaign_counters"] != expected_campaign
        or lease["reservation_bytes"] != READ_RESERVATION_BYTES
        or lease["expected_host_tool"] != expected_host_tool()
        or lease["attempt_consumed"] is not True
        or lease["replay_authorized"] is not False
        or lease["controls_blocked"] is not True
        or lease["terminal_blocked"] is not True
        or lease["completion_required"] is not True
    ):
        raise EvidenceH0Error("future coordinator lease binding/debit differs")
    if (
        previous_child["read_operations"] != ordinal - 1
        or expected_child["read_operations"] != ordinal
        or expected_campaign["read_operations"]
        != previous_campaign["read_operations"] + 1
    ):
        raise EvidenceH0Error("future lease read ordinals/counters differ")
    return dict(lease)


def mirror_read_intent(
    lease: Mapping[str, Any],
    lease_raw: bytes,
    opening: Mapping[str, Any],
    opening_raw: bytes,
    mirrored_at: int,
) -> dict[str, Any]:
    _exact_keys(lease, LEASE_KEYS, "future coordinator lease")
    if type(lease_raw) is not bytes or canonical_bytes(lease) != lease_raw:
        raise EvidenceH0Error("intent mirror lease bytes differ")
    opening = validate_accounting_opening(opening, opening_raw)
    timestamp = _require_int(mirrored_at, "intent mirror timestamp")
    if timestamp < lease["issued_at"]:
        raise EvidenceH0Error("intent mirror predates coordinator lease")
    return {
        "schema": READ_INTENT_SCHEMA,
        "kind": "read-intent-mirror",
        "mirrored_at": timestamp,
        "campaign_id": opening["campaign_id"],
        "session_id": opening["session_id"],
        "target": TARGET,
        "action": "public-health",
        "read_ordinal": lease["read_ordinal"],
        "coordinator_lease_sha256": sha256_bytes(lease_raw),
        "lease_issued_at": lease["issued_at"],
        "lease_observed_at": timestamp,
        "campaign_expires_at": lease["coordinator_context"][
            "campaign_expires_at"
        ],
        "session_expires_at": lease["coordinator_context"]["session_expires_at"],
        "coordinator_head_sha256": lease["coordinator_head_sha256"],
        "source_identity": lease["source_identity"],
        "previous_evidence_result_sha256": lease[
            "previous_evidence_result_sha256"
        ],
        "previous_coordinator_complete_sha256": lease[
            "previous_coordinator_complete_sha256"
        ],
        "child_counters": lease["child_counters"],
        "campaign_counters": lease["campaign_counters"],
        "reservation_bytes": READ_RESERVATION_BYTES,
        "expected_evidence_names": list(EVIDENCE_NAMES),
        "attempt_consumed": True,
        "uncertain_if_incomplete": True,
        "replay_authorized": False,
        "next_action_before_coordinator_complete": False,
        "command_execution_backend": False,
    }


INTENT_KEYS = {
    "schema",
    "kind",
    "mirrored_at",
    "campaign_id",
    "session_id",
    "target",
    "action",
    "read_ordinal",
    "coordinator_lease_sha256",
    "lease_issued_at",
    "lease_observed_at",
    "campaign_expires_at",
    "session_expires_at",
    "coordinator_head_sha256",
    "source_identity",
    "previous_evidence_result_sha256",
    "previous_coordinator_complete_sha256",
    "child_counters",
    "campaign_counters",
    "reservation_bytes",
    "expected_evidence_names",
    "attempt_consumed",
    "uncertain_if_incomplete",
    "replay_authorized",
    "next_action_before_coordinator_complete",
    "command_execution_backend",
}


def validate_intent_shape(intent: Any, intent_raw: bytes) -> dict[str, Any]:
    _exact_keys(intent, INTENT_KEYS, "read intent")
    if type(intent_raw) is not bytes or canonical_bytes(intent) != intent_raw:
        raise EvidenceH0Error("read intent bytes are not exact canonical bytes")
    ordinal = _require_int(intent["read_ordinal"], "intent ordinal", 1)
    if ordinal > CHILD_LIMITS["read_operations_max"]:
        raise EvidenceH0Error("intent ordinal exceeds child limit")
    _require_id(intent["campaign_id"], "intent campaign id")
    _require_id(intent["session_id"], "intent session id")
    for key in (
        "coordinator_lease_sha256",
        "coordinator_head_sha256",
        "previous_evidence_result_sha256",
        "previous_coordinator_complete_sha256",
    ):
        _require_hex(intent[key], f"intent {key}")
    _require_int(intent["mirrored_at"], "intent mirrored_at")
    lease_issued = _require_int(intent["lease_issued_at"], "intent lease issued_at")
    lease_observed = _require_int(
        intent["lease_observed_at"], "intent lease observed_at"
    )
    campaign_expiry = _require_int(
        intent["campaign_expires_at"], "intent campaign expiry"
    )
    session_expiry = _require_int(
        intent["session_expires_at"], "intent session expiry"
    )
    validate_source_identity(intent["source_identity"], "intent source")
    child = validate_counters(intent["child_counters"], CHILD_LIMITS, "intent child")
    campaign = validate_counters(
        intent["campaign_counters"], CAMPAIGN_LIMITS, "intent campaign"
    )
    if (
        intent["schema"] != READ_INTENT_SCHEMA
        or intent["kind"] != "read-intent-mirror"
        or intent["target"] != TARGET
        or intent["action"] != "public-health"
        or intent["reservation_bytes"] != READ_RESERVATION_BYTES
        or intent["mirrored_at"] != lease_observed
        or lease_issued > lease_observed
        or lease_issued >= campaign_expiry
        or lease_issued >= session_expiry
        or session_expiry > campaign_expiry
        or intent["expected_evidence_names"] != list(EVIDENCE_NAMES)
        or intent["attempt_consumed"] is not True
        or intent["uncertain_if_incomplete"] is not True
        or intent["replay_authorized"] is not False
        or intent["next_action_before_coordinator_complete"] is not False
        or intent["command_execution_backend"] is not False
        or child["read_operations"] != ordinal
        or child["private_evidence_bytes_reserved"] != READ_RESERVATION_BYTES
        or campaign["private_evidence_bytes_reserved"] != READ_RESERVATION_BYTES
    ):
        raise EvidenceH0Error("read intent semantics differ")
    validate_scope_relation(child, campaign, "read intent")
    return dict(intent)


def validate_mirrored_intent(
    intent: Any,
    intent_raw: bytes,
    lease: Mapping[str, Any],
    lease_raw: bytes,
    opening: Mapping[str, Any],
    opening_raw: bytes,
) -> dict[str, Any]:
    actual = validate_intent_shape(intent, intent_raw)
    expected = mirror_read_intent(
        lease, lease_raw, opening, opening_raw, actual["mirrored_at"]
    )
    if actual != expected:
        raise EvidenceH0Error("read intent is not an exact lease mirror")
    return actual


def _base_tool(value: Any, label: str) -> dict[str, Any]:
    keys = {"path", "device", "inode", "mtime_ns", "size", "sha256"}
    _exact_keys(value, keys, label)
    for key in ("device", "inode", "mtime_ns", "size"):
        _require_int(value[key], f"{label}.{key}")
    if (
        value["path"] != expected_host_tool()["path"]
        or value["size"] != expected_host_tool()["size"]
        or value["sha256"] != expected_host_tool()["sha256"]
    ):
        raise EvidenceH0Error(f"{label} differs from fixed ADB")
    return dict(value)


def _decode(result: tuple[int, bytes, bytes], label: str) -> str:
    returncode, stdout, stderr = result
    if type(returncode) is not int or type(returncode) is bool or returncode != 0:
        raise EvidenceH0Error(f"{label} return code differs")
    if type(stdout) is not bytes or type(stderr) is not bytes or stderr:
        raise EvidenceH0Error(f"{label} streams differ")
    try:
        return stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise EvidenceH0Error(f"{label} is not UTF-8") from exc


def parse_inventory(text: str) -> tuple[dict[str, Any], ...]:
    if type(text) is not str:
        raise EvidenceH0Error("inventory is not text")
    rows: list[dict[str, Any]] = []
    serials: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2 or SERIAL_RE.fullmatch(fields[0]) is None:
            raise EvidenceH0Error("inventory row is malformed")
        if fields[0] in serials:
            raise EvidenceH0Error("inventory serial is duplicated")
        serials.add(fields[0])
        metadata = frozenset(fields[2:])
        for prefix in ("model:", "device:", "product:"):
            if len([item for item in metadata if item.startswith(prefix)]) > 1:
                raise EvidenceH0Error("inventory metadata conflicts")
        rows.append({"serial": fields[0], "state": fields[1], "metadata": metadata})
    return tuple(rows)


def select_target(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    matches = [row for row in rows if "model:SM_G986N" in row["metadata"]]
    if len(matches) != 1 or matches[0]["state"] != "device":
        raise EvidenceH0Error("inventory lacks one authorized exact model")
    selected = matches[0]
    for prefix in ("model:", "device:", "product:"):
        if len([item for item in selected["metadata"] if item.startswith(prefix)]) != 1:
            raise EvidenceH0Error("selected inventory metadata is incomplete")
    return selected


def _sanitized_inventory(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "serial_sha256": hashlib.sha256(row["serial"].encode()).hexdigest(),
            "state": row["state"],
            "metadata": sorted(row["metadata"]),
        }
        for row in rows
    )


def parse_snapshot(text: str) -> dict[str, str]:
    if type(text) is not str:
        raise EvidenceH0Error("snapshot is not text")
    values: dict[str, str] = {}
    allowed = set(PROPERTY_KEYS)
    for line in text.splitlines():
        if "=" not in line:
            raise EvidenceH0Error("snapshot line is malformed")
        key, value = line.split("=", 1)
        if key not in allowed or key in values or SAFE_VALUE_RE.fullmatch(value) is None:
            raise EvidenceH0Error("snapshot field differs")
        values[key] = value
    if set(values) != allowed:
        raise EvidenceH0Error("snapshot fields are incomplete")
    if (
        values["model"] != TARGET["model"]
        or values["device"] != TARGET["device"]
        or values["product_name"] != TARGET["product"]
        or values["incremental"] != TARGET["build"]
        or values["boot_completed"] != "1"
        or values["bootanim"] != "stopped"
        or values["selinux"] != "Enforcing"
        or BOOT_ID_RE.fullmatch(values["boot_id"]) is None
    ):
        raise EvidenceH0Error("snapshot target/build/health differs")
    return values


def _actual_argvs(records: Sequence[Mapping[str, Any]]) -> list[list[str]]:
    if len(records) != 6:
        raise EvidenceH0Error("retained set is not six commands")
    initial = _decode(
        (
            records[1]["returncode"],
            records[1]["stdout"],
            records[1]["stderr"],
        ),
        "initial inventory",
    )
    serial = select_target(parse_inventory(initial))["serial"]
    adb = expected_host_tool()["path"]
    return [
        [adb, "version"],
        [adb, "devices", "-l"],
        [adb, "-s", serial, "get-devpath"],
        [adb, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
        [adb, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
        [adb, "devices", "-l"],
    ]


def build_command_receipts(
    intent_raw: bytes, records: Sequence[Mapping[str, Any]]
) -> tuple[tuple[dict[str, Any], bytes], ...]:
    """Pure provenance builder; it cannot retain or execute caller records."""

    intent = parse_canonical_json(intent_raw, "read intent")
    validate_intent_shape(intent, intent_raw)
    if type(records) not in (tuple, list) or len(records) != 6:
        raise EvidenceH0Error("retained set is not six records")
    common_tool: dict[str, Any] | None = None
    previous_published = intent["mirrored_at"]
    for record, template in zip(records, FIXED_TRANSCRIPT, strict=True):
        _exact_keys(
            record,
            {
                "ordinal",
                "argv",
                "timeout_sec",
                "max_bytes",
                "returncode",
                "stdout",
                "stderr",
                "host_tool_before",
                "host_tool_after",
                "execution_started_at",
                "execution_completed_at",
                "return_retained_at",
                "receipt_published_at",
            },
            "retained command record",
        )
        if (
            type(record["returncode"]) is not int
            or type(record["returncode"]) is bool
            or type(record["ordinal"]) is not int
            or type(record["ordinal"]) is bool
            or type(record["timeout_sec"]) is not int
            or type(record["timeout_sec"]) is bool
            or type(record["max_bytes"]) is not int
            or type(record["max_bytes"]) is bool
            or type(record["argv"]) is not list
            or any(type(item) is not str for item in record["argv"])
            or type(record["stdout"]) is not bytes
            or type(record["stderr"]) is not bytes
        ):
            raise EvidenceH0Error("retained command record types differ")
        started = _require_int(
            record["execution_started_at"], "command execution_started_at"
        )
        completed = _require_int(
            record["execution_completed_at"], "command execution_completed_at"
        )
        retained = _require_int(
            record["return_retained_at"], "command return_retained_at"
        )
        published = _require_int(
            record["receipt_published_at"], "command receipt_published_at"
        )
        if (
            started < previous_published
            or completed < started
            or completed - started > template["timeout_sec"]
            or retained < completed
            or published < retained
            or published >= intent["campaign_expires_at"]
            or published >= intent["session_expires_at"]
            or len(record["stdout"]) + len(record["stderr"])
            > record["max_bytes"]
            or record["max_bytes"] != template["max_bytes"]
        ):
            raise EvidenceH0Error("retained command timing/output bound differs")
        previous_published = published
        before = _base_tool(record["host_tool_before"], "host_tool_before")
        after = _base_tool(record["host_tool_after"], "host_tool_after")
        if before != after:
            raise EvidenceH0Error("ADB tool changed around a command")
        if common_tool is None:
            common_tool = before
        elif common_tool != before:
            raise EvidenceH0Error("ADB tool changed across commands")
    argvs = _actual_argvs(records)
    predecessor = sha256_bytes(intent_raw)
    receipts: list[tuple[dict[str, Any], bytes]] = []
    for ordinal, (record, argv, template) in enumerate(
        zip(records, argvs, FIXED_TRANSCRIPT, strict=True), 1
    ):
        if (
            record["ordinal"] != ordinal
            or record["argv"] != argv
            or record["timeout_sec"] != template["timeout_sec"]
            or record["max_bytes"] != template["max_bytes"]
        ):
            raise EvidenceH0Error("retained execution identity differs from fixed command")
        stdout = record["stdout"]
        stderr = record["stderr"]
        if len(stdout) + len(stderr) > template["max_bytes"]:
            raise EvidenceH0Error("retained raw pair exceeds 64 KiB")
        receipt = {
            "schema": COMMAND_EVIDENCE_SCHEMA,
            "read_ordinal": intent["read_ordinal"],
            "ordinal": ordinal,
            "predecessor_sha256": predecessor,
            "argv_template_sha256": sha256_bytes(canonical_bytes(template["argv"])),
            "argv_sha256": sha256_bytes(canonical_bytes(argv)),
            "timeout_sec": template["timeout_sec"],
            "max_bytes": template["max_bytes"],
            "returncode": record["returncode"],
            "execution_started_at": record["execution_started_at"],
            "execution_completed_at": record["execution_completed_at"],
            "return_retained_at": record["return_retained_at"],
            "receipt_published_at": record["receipt_published_at"],
            "stdout_size": len(stdout),
            "stdout_sha256": sha256_bytes(stdout),
            "stderr_size": len(stderr),
            "stderr_sha256": sha256_bytes(stderr),
            "host_tool_before": record["host_tool_before"],
            "host_tool_after": record["host_tool_after"],
        }
        raw = canonical_bytes(receipt)
        if len(raw) > COMMAND_RECEIPT_MAX_BYTES:
            raise EvidenceH0Error("canonical command receipt exceeds 8 KiB")
        receipts.append((receipt, raw))
        predecessor = sha256_bytes(raw)
    return tuple(receipts)


def derive_health_result(
    intent: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    receipt_pairs: Sequence[tuple[Mapping[str, Any], bytes]],
) -> dict[str, Any]:
    """Pure retained-return parser; it never reads a current tool or device."""

    expected = build_command_receipts(canonical_bytes(intent), records)
    if type(receipt_pairs) not in (tuple, list) or len(receipt_pairs) != 6:
        raise EvidenceH0Error("retained receipt set is incomplete")
    for actual, wanted in zip(receipt_pairs, expected, strict=True):
        if (
            type(actual) not in (tuple, list)
            or len(actual) != 2
            or type(actual[0]) is not dict
            or type(actual[1]) is not bytes
            or canonical_bytes(actual[0]) != actual[1]
        ):
            raise EvidenceH0Error("retained receipt pair is malformed")
        if actual[0] != wanted[0] or actual[1] != wanted[1]:
            raise EvidenceH0Error("retained receipt/raw predecessor chain differs")
    triples = [
        (record["returncode"], record["stdout"], record["stderr"])
        for record in records
    ]
    version = _decode(triples[0], "ADB version")
    first_rows = parse_inventory(_decode(triples[1], "initial inventory"))
    selected = select_target(first_rows)
    serial = selected["serial"]
    devpath = _decode(triples[2], "selected devpath")
    if DEVPATH_RE.fullmatch(devpath) is None:
        raise EvidenceH0Error("selected devpath differs")
    first_snapshot = parse_snapshot(_decode(triples[3], "first snapshot"))
    second_snapshot = parse_snapshot(_decode(triples[4], "second snapshot"))
    if first_snapshot != second_snapshot:
        raise EvidenceH0Error("public-health snapshots differ")
    expected_metadata = {
        "model:SM_G986N",
        f"device:{TARGET['device']}",
        f"product:{TARGET['product']}",
    }
    if not expected_metadata <= selected["metadata"]:
        raise EvidenceH0Error("snapshot conflicts with selected inventory row")
    final_rows = parse_inventory(_decode(triples[5], "final inventory"))
    final_selected = select_target(final_rows)
    if (
        final_selected["serial"] != serial
        or _sanitized_inventory(final_rows) != _sanitized_inventory(first_rows)
    ):
        raise EvidenceH0Error("target or inventory changed across retained read")
    properties = dict(first_snapshot)
    boot_id = properties.pop("boot_id")
    common_tool = _base_tool(records[0]["host_tool_before"], "retained host tool")
    result = {
        "schema": INVENTORY_SCHEMA,
        "version": INVENTORY_VERSION,
        "mode": "connected-read-only",
        "target": {
            "model": TARGET["model"],
            "adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
            "usb_topology_sha256": hashlib.sha256(devpath.encode()).hexdigest(),
            "other_serial_sha256": sorted(
                hashlib.sha256(row["serial"].encode()).hexdigest()
                for row in first_rows
                if row["serial"] != serial
            ),
            "inventory_sha256": hashlib.sha256(
                json.dumps(_sanitized_inventory(first_rows), sort_keys=True).encode()
            ).hexdigest(),
        },
        "properties": properties,
        "boot_id_sha256": hashlib.sha256(boot_id.encode()).hexdigest(),
        "usb_debugging_verified": True,
        "adb_authorization_state": "device",
        "host_tool": {
            **common_tool,
            "version_output_sha256": hashlib.sha256(version.encode()).hexdigest(),
        },
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "verdict": INVENTORY_VERDICT,
    }
    source = validate_source_identity(intent["source_identity"], "intent source")
    if (
        result["target"]["adb_serial_sha256"] != source["serial_sha256"]
        or result["target"]["usb_topology_sha256"] != source["topology_sha256"]
        or result["boot_id_sha256"] != source["boot_id_sha256"]
        or result["properties"]["build_product"] != TARGET["device"]
        or f"/{TARGET['product']}/{TARGET['device']}:"
        not in result["properties"]["fingerprint"]
        or not result["properties"]["fingerprint"].endswith(":user/release-keys")
        or SHELL_ID_RE.fullmatch(result["properties"]["shell_identity"]) is None
    ):
        raise EvidenceH0Error("derived health differs from coordinator lease source")
    encoded = canonical_bytes(result)
    if len(encoded) > HEALTH_RESULT_MAX_BYTES:
        raise EvidenceH0Error("canonical health result exceeds 64 KiB")
    return result


def evidence_payloads(
    intent: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    receipt_pairs: Sequence[tuple[Mapping[str, Any], bytes]],
) -> dict[str, bytes]:
    health = derive_health_result(intent, records, receipt_pairs)
    payloads: dict[str, bytes] = {"health.json": canonical_bytes(health)}
    for ordinal, (record, receipt_pair) in enumerate(
        zip(records, receipt_pairs, strict=True), 1
    ):
        payloads[f"cmd-{ordinal:02d}.stdout.bin"] = record["stdout"]
        payloads[f"cmd-{ordinal:02d}.stderr.bin"] = record["stderr"]
        payloads[f"cmd-{ordinal:02d}.receipt.json"] = receipt_pair[1]
    if set(payloads) != set(EVIDENCE_NAMES):
        raise EvidenceH0Error("evidence payload names differ")
    return payloads


READ_RESULT_KEYS = {
    "schema",
    "kind",
    "completed_at",
    "campaign_id",
    "session_id",
    "target",
    "source_identity",
    "action",
    "read_ordinal",
    "intent_sha256",
    "coordinator_lease_sha256",
    "last_receipt_sha256",
    "health_sha256",
    "evidence_files",
    "evidence_set_sha256",
    "actual_evidence_bytes",
    "child_counters",
    "campaign_counters",
    "outcome_proven",
    "reporting_after_expiry_or_drift",
    "reporting_cut_at",
    "replay_authorized",
    "coordinator_complete_required",
    "device_command_count_by_owner",
    "device_effect_count",
}


def model_validated_read_result(
    opening: Mapping[str, Any],
    opening_raw: bytes,
    state: Mapping[str, Any],
    lease: Mapping[str, Any],
    lease_raw: bytes,
    lease_observed_at: int,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    records: Sequence[Mapping[str, Any]],
    receipt_pairs: Sequence[tuple[Mapping[str, Any], bytes]],
    completed_at: int,
    reporting_cut_at: int | None,
) -> dict[str, Any]:
    """Model a result only from the exact lease, mirror, returns, and receipts."""

    validate_future_lease(
        lease, lease_raw, opening, opening_raw, state, lease_observed_at
    )
    validate_mirrored_intent(
        intent, intent_raw, lease, lease_raw, opening, opening_raw
    )
    payloads = evidence_payloads(intent, records, receipt_pairs)
    completed = _require_int(completed_at, "read result completed_at")
    if (
        completed < intent["mirrored_at"]
        or completed < lease["issued_at"]
        or completed < lease_observed_at
        or completed < records[-1]["receipt_published_at"]
        or lease_observed_at != intent["lease_observed_at"]
    ):
        raise EvidenceH0Error("read result predates its lease or mirror")
    if reporting_cut_at is not None:
        cut = _require_int(reporting_cut_at, "reporting drift cut")
        if cut < records[-1]["receipt_published_at"] or cut > completed:
            raise EvidenceH0Error("reporting cut does not follow the complete transcript")
    else:
        cut = None
    reporting_after_expiry_or_drift = (
        cut is not None
        or completed >= lease["coordinator_context"]["campaign_expires_at"]
        or completed >= lease["coordinator_context"]["session_expires_at"]
    )
    if set(payloads) != set(EVIDENCE_NAMES):
        raise EvidenceH0Error("read result lacks exact 19-file evidence set")
    manifest: list[dict[str, Any]] = []
    raw_total = 0
    receipt_total = 0
    for name in sorted(payloads):
        payload = payloads[name]
        if type(payload) is not bytes:
            raise EvidenceH0Error("evidence payload is not bytes")
        if name.endswith(".bin"):
            raw_total += len(payload)
        elif name.endswith(".receipt.json"):
            if len(payload) > COMMAND_RECEIPT_MAX_BYTES:
                raise EvidenceH0Error("receipt exceeds 8 KiB")
            receipt_total += len(payload)
        elif name == "health.json" and len(payload) > HEALTH_RESULT_MAX_BYTES:
            raise EvidenceH0Error("health JSON exceeds 64 KiB")
        manifest.append({"name": name, "size": len(payload), "sha256": sha256_bytes(payload)})
    if raw_total > RAW_SET_PROOF_MAX_BYTES or receipt_total > RECEIPT_SET_PROOF_MAX_BYTES:
        raise EvidenceH0Error("raw or receipt aggregate exceeds proof bound")
    actual = sum(item["size"] for item in manifest)
    if actual > TOTAL_EVIDENCE_PROOF_MAX_BYTES or actual > READ_RESERVATION_BYTES:
        raise EvidenceH0Error("actual evidence exceeds reservation")
    last_receipt = payloads["cmd-06.receipt.json"]
    health_raw = payloads["health.json"]
    result = {
        "schema": READ_RESULT_SCHEMA,
        "kind": "read-result",
        "completed_at": completed,
        "campaign_id": opening["campaign_id"],
        "session_id": opening["session_id"],
        "target": TARGET,
        "source_identity": intent["source_identity"],
        "action": "public-health",
        "read_ordinal": intent["read_ordinal"],
        "intent_sha256": sha256_bytes(intent_raw),
        "coordinator_lease_sha256": intent["coordinator_lease_sha256"],
        "last_receipt_sha256": sha256_bytes(last_receipt),
        "health_sha256": sha256_bytes(health_raw),
        "evidence_files": manifest,
        "evidence_set_sha256": sha256_bytes(canonical_bytes(manifest)),
        "actual_evidence_bytes": actual,
        "child_counters": settle_counters(
            intent["child_counters"], actual, CHILD_LIMITS, "result child"
        ),
        "campaign_counters": settle_counters(
            intent["campaign_counters"], actual, CAMPAIGN_LIMITS, "result campaign"
        ),
        "outcome_proven": True,
        "reporting_after_expiry_or_drift": reporting_after_expiry_or_drift,
        "reporting_cut_at": cut,
        "replay_authorized": False,
        "coordinator_complete_required": True,
        "device_command_count_by_owner": 0,
        "device_effect_count": 0,
    }
    if len(canonical_bytes(result)) > MAX_JSON_BYTES:
        raise EvidenceH0Error("read result model exceeds its JSON bound")
    return result


COMPLETE_KEYS = {
    "schema",
    "kind",
    "completed_at",
    "campaign_id",
    "session_id",
    "target",
    "action",
    "read_ordinal",
    "coordinator_lease_sha256",
    "evidence_result_sha256",
    "child_counters",
    "campaign_counters",
    "completion_mode",
    "evidence_outcome_proven",
    "replay_authorized",
    "controls_unblocked",
    "terminal_unblocked",
    "campaign_parked",
}


def validate_read_result_model(result: Any, result_raw: bytes) -> dict[str, Any]:
    _exact_keys(result, READ_RESULT_KEYS, "read result")
    if type(result_raw) is not bytes or canonical_bytes(result) != result_raw:
        raise EvidenceH0Error("read result bytes are not exact canonical bytes")
    completed = _require_int(result["completed_at"], "read result completed_at")
    del completed
    _require_id(result["campaign_id"], "read result campaign id")
    _require_id(result["session_id"], "read result session id")
    ordinal = _require_int(result["read_ordinal"], "read result ordinal", 1)
    if ordinal > CHILD_LIMITS["read_operations_max"]:
        raise EvidenceH0Error("read result ordinal exceeds child limit")
    for key in (
        "intent_sha256",
        "coordinator_lease_sha256",
        "last_receipt_sha256",
        "health_sha256",
        "evidence_set_sha256",
    ):
        _require_hex(result[key], f"read result {key}")
    validate_source_identity(result["source_identity"], "read result source")
    if type(result["evidence_files"]) is not list:
        raise EvidenceH0Error("read result manifest is not a list")
    manifest: list[dict[str, Any]] = []
    raw_total = 0
    receipt_total = 0
    for index, item in enumerate(result["evidence_files"]):
        _exact_keys(item, {"name", "size", "sha256"}, f"manifest item {index}")
        name = item["name"]
        if type(name) is not str:
            raise EvidenceH0Error("manifest name is not text")
        size = _require_int(item["size"], f"manifest {name} size")
        _require_hex(item["sha256"], f"manifest {name} hash")
        if name.endswith(".bin"):
            raw_total += size
        elif name.endswith(".receipt.json"):
            if size > COMMAND_RECEIPT_MAX_BYTES:
                raise EvidenceH0Error("manifest receipt exceeds 8 KiB")
            receipt_total += size
        elif name == "health.json":
            if size > HEALTH_RESULT_MAX_BYTES:
                raise EvidenceH0Error("manifest health exceeds 64 KiB")
        else:
            raise EvidenceH0Error("manifest name is outside the evidence grammar")
        manifest.append(dict(item))
    if [item["name"] for item in manifest] != list(EVIDENCE_NAMES):
        raise EvidenceH0Error("read result manifest names/order differ")
    by_name = {item["name"]: item for item in manifest}
    for command_ordinal in range(1, 7):
        if (
            by_name[f"cmd-{command_ordinal:02d}.stdout.bin"]["size"]
            + by_name[f"cmd-{command_ordinal:02d}.stderr.bin"]["size"]
            > RAW_PAIR_MAX_BYTES
        ):
            raise EvidenceH0Error("manifest raw pair exceeds 64 KiB")
    actual = _require_int(result["actual_evidence_bytes"], "actual evidence bytes")
    if (
        raw_total > RAW_SET_PROOF_MAX_BYTES
        or receipt_total > RECEIPT_SET_PROOF_MAX_BYTES
        or actual != sum(item["size"] for item in manifest)
        or actual > TOTAL_EVIDENCE_PROOF_MAX_BYTES
        or result["evidence_set_sha256"] != sha256_bytes(canonical_bytes(manifest))
        or result["last_receipt_sha256"]
        != manifest[list(EVIDENCE_NAMES).index("cmd-06.receipt.json")]["sha256"]
        or result["health_sha256"]
        != manifest[list(EVIDENCE_NAMES).index("health.json")]["sha256"]
    ):
        raise EvidenceH0Error("read result manifest accounting differs")
    child = validate_counters(
        result["child_counters"], CHILD_LIMITS, "result child counters"
    )
    campaign = validate_counters(
        result["campaign_counters"], CAMPAIGN_LIMITS, "result campaign counters"
    )
    cut = result["reporting_cut_at"]
    if cut is not None:
        cut = _require_int(cut, "read result reporting cut")
        if cut > result["completed_at"]:
            raise EvidenceH0Error("read result reporting cut is from the future")
    if (
        result["schema"] != READ_RESULT_SCHEMA
        or result["kind"] != "read-result"
        or result["target"] != TARGET
        or result["action"] != "public-health"
        or child["read_operations"] != ordinal
        or child["private_evidence_bytes_reserved"] != 0
        or campaign["private_evidence_bytes_reserved"] != 0
        or result["outcome_proven"] is not True
        or type(result["reporting_after_expiry_or_drift"]) is not bool
        or (cut is not None and result["reporting_after_expiry_or_drift"] is not True)
        or result["replay_authorized"] is not False
        or result["coordinator_complete_required"] is not True
        or type(result["device_command_count_by_owner"]) is not int
        or result["device_command_count_by_owner"] != 0
        or type(result["device_effect_count"]) is not int
        or result["device_effect_count"] != 0
    ):
        raise EvidenceH0Error("read result semantics differ")
    validate_scope_relation(child, campaign, "read result")
    return dict(result)


def model_future_completion(
    result: Mapping[str, Any], result_raw: bytes, completed_at: int
) -> dict[str, Any]:
    """Model settlement only; this permanent H0 can never unblock controls."""

    result = validate_read_result_model(result, result_raw)
    completed = _require_int(completed_at, "completion completed_at")
    if completed < result["completed_at"]:
        raise EvidenceH0Error("completion predates its evidence result")
    return {
        "schema": COORDINATOR_COMPLETE_SCHEMA,
        "kind": "public-health-read-complete",
        "completed_at": completed,
        "campaign_id": result["campaign_id"],
        "session_id": result["session_id"],
        "target": TARGET,
        "action": "public-health",
        "read_ordinal": result["read_ordinal"],
        "coordinator_lease_sha256": result["coordinator_lease_sha256"],
        "evidence_result_sha256": sha256_bytes(result_raw),
        "child_counters": result["child_counters"],
        "campaign_counters": result["campaign_counters"],
        "completion_mode": "permanent-h0-parked",
        "evidence_outcome_proven": True,
        "replay_authorized": False,
        "controls_unblocked": False,
        "terminal_unblocked": False,
        "campaign_parked": True,
    }


def validate_future_completion(
    completion: Any,
    completion_raw: bytes,
    result: Mapping[str, Any],
    result_raw: bytes,
    lease: Mapping[str, Any],
    lease_raw: bytes,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    opening: Mapping[str, Any],
    opening_raw: bytes,
    state: Mapping[str, Any],
    lease_observed_at: int,
    records: Sequence[Mapping[str, Any]],
    receipt_pairs: Sequence[tuple[Mapping[str, Any], bytes]],
) -> dict[str, Any]:
    _exact_keys(completion, COMPLETE_KEYS, "future coordinator completion")
    if type(completion_raw) is not bytes or canonical_bytes(completion) != completion_raw:
        raise EvidenceH0Error("future coordinator completion is noncanonical")
    result = validate_read_result_model(result, result_raw)
    expected_result = model_validated_read_result(
        opening,
        opening_raw,
        state,
        lease,
        lease_raw,
        lease_observed_at,
        intent,
        intent_raw,
        records,
        receipt_pairs,
        result["completed_at"],
        result["reporting_cut_at"],
    )
    if result != expected_result:
        raise EvidenceH0Error("read result differs from retained evidence")
    expected_completion = model_future_completion(
        result, result_raw, completion["completed_at"]
    )
    if completion != expected_completion:
        raise EvidenceH0Error("completion mode or flags differ from its cut state")
    intent = validate_mirrored_intent(
        intent, intent_raw, lease, lease_raw, opening, opening_raw
    )
    actual = result["actual_evidence_bytes"]
    expected_child = settle_counters(
        intent["child_counters"], actual, CHILD_LIMITS, "completion child"
    )
    expected_campaign = settle_counters(
        intent["campaign_counters"], actual, CAMPAIGN_LIMITS, "completion campaign"
    )
    if (
        lease["schema"] != COORDINATOR_LEASE_SCHEMA
        or lease["kind"] != "public-health-read-lease"
        or intent["coordinator_lease_sha256"] != sha256_bytes(lease_raw)
        or result["intent_sha256"] != sha256_bytes(intent_raw)
        or result["coordinator_lease_sha256"] != sha256_bytes(lease_raw)
        or result["campaign_id"] != intent["campaign_id"]
        or result["session_id"] != intent["session_id"]
        or result["read_ordinal"] != intent["read_ordinal"]
        or result["source_identity"] != intent["source_identity"]
        or result["child_counters"] != expected_child
        or result["campaign_counters"] != expected_campaign
        or result["completed_at"] < intent["mirrored_at"]
        or result["completed_at"] < lease["issued_at"]
    ):
        raise EvidenceH0Error("read result does not settle its exact lease/intent")
    park = True
    completed = _require_int(completion["completed_at"], "completion completed_at")
    if any(
        type(completion[key]) is not bool
        for key in (
            "evidence_outcome_proven",
            "replay_authorized",
            "controls_unblocked",
            "terminal_unblocked",
            "campaign_parked",
        )
    ):
        raise EvidenceH0Error("completion flags are not strict booleans")
    if (
        completion["schema"] != COORDINATOR_COMPLETE_SCHEMA
        or completion["kind"] != "public-health-read-complete"
        or completed < result["completed_at"]
        or completion["campaign_id"] != result["campaign_id"]
        or completion["session_id"] != result["session_id"]
        or completion["target"] != TARGET
        or completion["action"] != "public-health"
        or completion["read_ordinal"] != result["read_ordinal"]
        or completion["coordinator_lease_sha256"]
        != result["coordinator_lease_sha256"]
        or completion["evidence_result_sha256"] != sha256_bytes(result_raw)
        or completion["child_counters"] != result["child_counters"]
        or completion["campaign_counters"] != result["campaign_counters"]
        or completion["completion_mode"]
        != "permanent-h0-parked"
        or completion["evidence_outcome_proven"] is not True
        or completion["replay_authorized"] is not False
        or completion["controls_unblocked"] is not (not park)
        or completion["terminal_unblocked"] is not (not park)
        or completion["campaign_parked"] is not park
    ):
        raise EvidenceH0Error("future coordinator completion/result settlement differs")
    return dict(completion)


def advance_protocol_state(
    state: Mapping[str, Any],
    result: Mapping[str, Any],
    result_raw: bytes,
    completion: Mapping[str, Any],
    completion_raw: bytes,
    lease: Mapping[str, Any],
    lease_raw: bytes,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    opening: Mapping[str, Any],
    opening_raw: bytes,
    lease_observed_at: int,
    records: Sequence[Mapping[str, Any]],
    receipt_pairs: Sequence[tuple[Mapping[str, Any], bytes]],
) -> dict[str, Any]:
    state = validate_protocol_state(state)
    validate_future_completion(
        completion,
        completion_raw,
        result,
        result_raw,
        lease,
        lease_raw,
        intent,
        intent_raw,
        opening,
        opening_raw,
        state,
        lease_observed_at,
        records,
        receipt_pairs,
    )
    if result["read_ordinal"] != state["read_ordinal"] + 1:
        raise EvidenceH0Error("completion would settle counters twice or skip an ordinal")
    return {
        "read_ordinal": result["read_ordinal"],
        "previous_evidence_result_sha256": sha256_bytes(result_raw),
        "previous_coordinator_complete_sha256": sha256_bytes(completion_raw),
        "child_counters": result["child_counters"],
        "campaign_counters": result["campaign_counters"],
        "campaign_parked": completion["campaign_parked"],
    }


def ledger_relative_names(campaign_id: str, session_id: str, read_count: int) -> dict[str, Any]:
    campaign = "campaign-" + hashlib.sha256(_require_id(campaign_id, "campaign id").encode()).hexdigest()
    session = "session-" + hashlib.sha256(_require_id(session_id, "session id").encode()).hexdigest()
    count = _require_int(read_count, "read count")
    if count > 1:
        raise EvidenceH0Error("permanent H0 ledger models only initial ordinal one")
    children = ["accounting-opening.json"]
    for ordinal in range(1, count + 1):
        children.extend(
            [
                f"read-intent-{ordinal:06d}.json",
                f"read-{ordinal:06d}",
                f"read-result-{ordinal:06d}.json",
            ]
        )
    return {
        "root_children": ["campaigns"],
        "campaign": campaign,
        "campaign_children": ["sessions"],
        "session": session,
        "session_children": children,
        "read_children": list(EVIDENCE_NAMES),
    }


def validate_ledger_namespace(
    *,
    campaign_id: str,
    session_id: str,
    read_count: int,
    root_children: Sequence[str],
    campaign_directories: Sequence[str],
    campaign_children: Sequence[str],
    session_directories: Sequence[str],
    session_children: Sequence[str],
    read_children_by_ordinal: Mapping[int, Sequence[str]],
) -> dict[str, Any]:
    """Pure closed-grammar check; this function performs no filesystem access."""

    expected = ledger_relative_names(campaign_id, session_id, read_count)
    groups = {
        "root": root_children,
        "campaign directories": campaign_directories,
        "campaign": campaign_children,
        "session directories": session_directories,
        "session": session_children,
    }
    for label, values in groups.items():
        if type(values) not in (list, tuple) or any(type(item) is not str for item in values):
            raise EvidenceH0Error(f"{label} namespace is not a string sequence")
        if len(values) != len(set(values)):
            raise EvidenceH0Error(f"{label} namespace contains duplicates")
    if (
        list(root_children) != expected["root_children"]
        or list(campaign_children) != expected["campaign_children"]
        or list(session_children) != expected["session_children"]
    ):
        raise EvidenceH0Error("fixed ledger namespace differs")
    if (
        not 1 <= len(campaign_directories) <= MAX_LEDGER_CHILDREN
        or any(CAMPAIGN_DIRECTORY_RE.fullmatch(name) is None for name in campaign_directories)
        or expected["campaign"] not in campaign_directories
        or not 1 <= len(session_directories) <= MAX_LEDGER_CHILDREN
        or any(SESSION_DIRECTORY_RE.fullmatch(name) is None for name in session_directories)
        or expected["session"] not in session_directories
    ):
        raise EvidenceH0Error("campaign/session directory namespace differs")
    count = _require_int(read_count, "read namespace count")
    if type(read_children_by_ordinal) is not dict or set(read_children_by_ordinal) != set(
        range(1, count + 1)
    ):
        raise EvidenceH0Error("read directory ordinals contain a gap or extra entry")
    for ordinal, names in read_children_by_ordinal.items():
        if type(ordinal) is not int or type(names) not in (list, tuple):
            raise EvidenceH0Error("read directory namespace types differ")
        if list(names) != list(EVIDENCE_NAMES):
            raise EvidenceH0Error("read directory lacks the exact 19 evidence files")
    return expected


def classify_reporting_cut(
    *,
    lease_present: bool,
    intent_present: bool,
    published_evidence_names: Sequence[str],
    result_present: bool,
    coordinator_complete_present: bool,
    expired_or_drifted: bool,
) -> dict[str, Any]:
    flags = {
        "lease_present": lease_present,
        "intent_present": intent_present,
        "result_present": result_present,
        "coordinator_complete_present": coordinator_complete_present,
        "expired_or_drifted": expired_or_drifted,
    }
    if any(type(value) is not bool for value in flags.values()):
        raise EvidenceH0Error("reporting cut flags are not strict booleans")
    if type(published_evidence_names) not in (list, tuple) or any(
        type(name) is not str for name in published_evidence_names
    ):
        raise EvidenceH0Error("reporting cut evidence names are not a string sequence")
    names = set(published_evidence_names)
    if not names <= set(EVIDENCE_NAMES) or len(names) != len(published_evidence_names):
        raise EvidenceH0Error("reporting cut evidence names are foreign or duplicated")
    if not lease_present and (
        intent_present or names or result_present or coordinator_complete_present
    ):
        raise EvidenceH0Error("reporting cut has a descendant without a lease")
    if not intent_present and (names or result_present or coordinator_complete_present):
        raise EvidenceH0Error("reporting cut has evidence without an intent mirror")
    if result_present and names != set(EVIDENCE_NAMES):
        raise EvidenceH0Error("reporting cut has a result without the exact evidence set")
    if coordinator_complete_present and not result_present:
        raise EvidenceH0Error("reporting cut has a completion without an evidence result")
    if not lease_present:
        return {
            "status": "NO_LEASE_NO_AUTHORITY",
            "zero_command_resume": False,
            "reservation_retained": False,
            "settled_consumed": False,
            "completion_must_be_revalidated_before_settlement": False,
            "replay_authorized": False,
            "next_action_authorized": False,
        }
    if not intent_present:
        status = "LEASE_MIRROR_ZERO_COMMAND_RESUMABLE"
        resumable = True
    elif names in (set(RETURN_NAMES), set(EVIDENCE_NAMES)) and not result_present:
        status = "COMPLETE_RETURNS_RESULT_ZERO_COMMAND_RESUMABLE"
        resumable = True
    elif result_present and names == set(EVIDENCE_NAMES) and not coordinator_complete_present:
        status = "AWAITING_COORDINATOR_COMPLETE"
        resumable = True
    elif coordinator_complete_present and result_present and names == set(EVIDENCE_NAMES):
        status = "COMPLETE_REVALIDATION_REQUIRED_PARKED"
        resumable = True
    else:
        status = "UNCERTAIN_CONSUMED"
        resumable = False
    return {
        "status": status,
        "zero_command_resume": resumable,
        "reservation_retained": lease_present,
        "settled_consumed": False,
        "completion_must_be_revalidated_before_settlement": coordinator_complete_present,
        "replay_authorized": False,
        "next_action_authorized": False,
    }


def begin_live_read() -> None:
    raise EvidenceH0Error("live begin requires a new coordinator implementation")


def record_live_return() -> None:
    raise EvidenceH0Error("live return recording is absent from this H0 model")


def complete_live_read() -> None:
    raise EvidenceH0Error("live completion requires a new coordinator implementation")


def render_plan() -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "evidence_active": EVIDENCE_ACTIVE,
        "live_authority": LIVE_AUTHORITY,
        "mechanically_activatable": MECHANICALLY_ACTIVATABLE,
        "coordinator_integrated": COORDINATOR_INTEGRATED,
        "permanent_h0_only": PERMANENT_H0_ONLY,
        "cli": ["--render-plan"],
        "target": TARGET,
        "sources": source_receipts(),
        "fixed_root": str(FIXED_ROOT),
        "ledger_layout": FIXED_LEDGER_LAYOUT,
        "counter_keys": sorted(COUNTER_KEYS),
        "child_limits": CHILD_LIMITS,
        "campaign_limits": CAMPAIGN_LIMITS,
        "read_reservation_bytes": READ_RESERVATION_BYTES,
        "byte_proof": {
            "raw_pairs_max": RAW_SET_PROOF_MAX_BYTES,
            "command_receipts_max": RECEIPT_SET_PROOF_MAX_BYTES,
            "health_json_max": HEALTH_RESULT_MAX_BYTES,
            "total_max": TOTAL_EVIDENCE_PROOF_MAX_BYTES,
        },
        "fixed_transcript": list(FIXED_TRANSCRIPT),
        "fixed_evidence_names": list(EVIDENCE_NAMES),
        "coordinator_nodes_required": [
            "public-health-read-lease-%06d",
            "public-health-read-complete-%06d",
        ],
        "current_coordinator_has_required_nodes": False,
        "modeled_session_scope": "initial-attended-session-only",
        "cross_session_counter_carry_implemented": False,
        "interleaved_control_heads_supported": False,
        "completion_can_unblock_controls": False,
        "next_read_after_completion_modeled": False,
        "timestamp_provenance": "numeric-model-only",
        "durable_publication_order_proven": False,
        "command_execution_backend": False,
        "private_filesystem_writer": False,
        "device_commands": [],
        "device_effects": [],
        "root_commands": [],
        "control_actions": [],
        "partition_transfers": [],
        "partial_state": {
            "status": "UNCERTAIN_CONSUMED",
            "reservation_retained": True,
            "replay_authorized": False,
            "next_action_authorized": False,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--render-plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan exists in this permanent H0 model")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
