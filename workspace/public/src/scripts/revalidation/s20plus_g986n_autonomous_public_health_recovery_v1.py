#!/usr/bin/env python3
"""Permanent-inactive recovery-v1 core for S20+ public-health research.

This source is intentionally self-contained.  It never imports, opens, or
executes a repository oracle at runtime.  It embeds the qualified protocol
schemas and retained-return parser needed to inspect a future private copy.
The current unit defines only the commandless store/manifest/scanner H0 model;
all fixed-root writer/scanner/finalizer entrypoints remain mechanically unreachable.
"""

from __future__ import annotations

import argparse
import ast
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from typing import Any, Mapping, Sequence


STATUS = "H0_PUBLIC_HEALTH_RECOVERY_V1_STORE_SCANNER_PASS_GO_NOT_ACTIVE"
EXPECTED_RECOVERY_NORMALIZED_SHA256 = "1b769167018a2a08e71e67adc00c20148eb4e0a11a6c428bf8fc82b517533b5d"
RECOVERY_V1_QUALIFIED = False
RECOVERY_SCANNER_ACTIVE = False
RECOVERY_WRITER_ACTIVE = False
RECOVERY_FINALIZER_ACTIVE = False
RECOVERY_REEMIT_ACTIVE = False
RECOVERY_MANIFEST_ACTIVE = False
RECOVERY_CONTRACT_ACTIVE = False
LIVE_AUTHORITY = False
SELF_CONTAINED_FINALIZER_IMPLEMENTED = False
PERMANENT_H0_ONLY = True

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "build": "G986NKSS8IYC2",
}

PLAN_SCHEMA = "s20plus_g986n_autonomous_public_health_recovery_v1_plan"
MANIFEST_SCHEMA = "s20plus_g986n_autonomous_public_health_recovery_v1_manifest"
RUNNER_BINDING_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_recovery_v1_runner_binding"
)
BASE_SCHEMA = "s20plus_g986n_autonomous_research_coordinator_h0_v1"
HEALTH_SCHEMA = "s20plus_g986n_d0_inventory_result_v1"
HEALTH_VERSION = "s20plus-g986n-d0-inventory-v1"
HEALTH_VERDICT = "PASS_S20PLUS_G986N_D0_ONBOARDING_READ_ONLY"
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

ORACLE_IDENTITIES = MappingProxyType(
    {
        "base_coordinator": MappingProxyType(
            {
                "size": 105_904,
                "sha256": "87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd",
            }
        ),
        "health": MappingProxyType(
            {
                "size": 13_908,
                "sha256": "03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b",
            }
        ),
        "inventory": MappingProxyType(
            {
                "size": 21_474,
                "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
            }
        ),
        "evidence_owner": MappingProxyType(
            {
                "size": 96_626,
                "sha256": "1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4",
                "normalized_sha256": "79d2fb339ce6c972790e28675ec407d2dbbd2f8e6f1b1e87008f332cbb708db1",
            }
        ),
        "read_leaf": MappingProxyType(
            {
                "size": 53_200,
                "sha256": "e2952245bf4433044fae12ff8114ee9ff4239cbacd173a83cdc5a3dfcfa3d2c6",
            }
        ),
    }
)
EXPECTED_RETAINED_SOURCE_RECEIPTS = MappingProxyType(
    {
        "owner": MappingProxyType(
            {
                "path": "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_evidence_h0.py",
                "size": 96_626,
                "sha256": "1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4",
                "normalized_sha256": "79d2fb339ce6c972790e28675ec407d2dbbd2f8e6f1b1e87008f332cbb708db1",
            }
        ),
        "coordinator": MappingProxyType(
            {
                "path": "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_research_coordinator_h0.py",
                "size": 105_904,
                "sha256": "87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd",
            }
        ),
        "health": MappingProxyType(
            {
                "path": "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_health_h0.py",
                "size": 13_908,
                "sha256": "03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b",
            }
        ),
        "inventory": MappingProxyType(
            {
                "path": "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py",
                "size": 21_474,
                "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
            }
        ),
    }
)

FIXED_ROOTS = MappingProxyType(
    {
        "base": Path(
            "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
            "s20plus-g986n-autonomous-research"
        ),
        "evidence": Path(
            "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
            "s20plus-g986n-autonomous-public-health-evidence"
        ),
        "leaf": Path(
            "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
            "s20plus-g986n-autonomous-public-health-read-leaf"
        ),
    }
)

LOCK_NAME = "coordinator.lock"
RECOVERY_DIRECTORY = "recovery-v1"
RECOVERY_CORE_NAME = "recovery-core.py"
RECOVERY_MANIFEST_NAME = "manifest.json"
OPENING_DIRECTORY = "opening-v1"
CAMPAIGN_BINDING_NAME = "campaign-binding.json"
RECOVERY_CORE_MAX_BYTES = 256 * 1024
RECOVERY_MANIFEST_MAX_BYTES = 32 * 1024
RECOVERY_BUNDLE_MAX_BYTES = 288 * 1024
RECOVERY_OPENING_MAX_BYTES = 544 * 1024
CAMPAIGN_BINDING_MAX_BYTES = 16 * 1024
STRUCTURAL_MAX_BYTES = 48 * 1024
EVIDENCE_RESERVATION_BYTES = 512 * 1024
EVIDENCE_PROOF_MAX_BYTES = 507_904
COMPLETED_TOTAL_MAX_BYTES = 1_441_792
COMPLETED_TOTAL_FILE_COUNT = 52
RECOVERY_OPENING_FILE_COUNT = 21
if (
    RECOVERY_BUNDLE_MAX_BYTES
    + RECOVERY_OPENING_MAX_BYTES
    + CAMPAIGN_BINDING_MAX_BYTES
    + STRUCTURAL_MAX_BYTES
    + EVIDENCE_RESERVATION_BYTES
    != COMPLETED_TOTAL_MAX_BYTES
    or 2 + RECOVERY_OPENING_FILE_COUNT + 1 + 8 + 19 + 1
    != COMPLETED_TOTAL_FILE_COUNT
):
    raise RuntimeError("recovery completed-closure accounting differs")

STRUCTURAL_CAPS = MappingProxyType(
    {
        "active-campaign.json": 8 * 1024,
        "opening.json": 4 * 1024,
        "session-opening.json": 4 * 1024,
        "accounting-opening.json": 16 * 1024,
        "public-health-read-lease-000001.json": 8 * 1024,
        "read-intent-000001.json": 4 * 1024,
        "read-result-000001.json": 8 * 1024,
        "public-health-read-complete-000001.json": 4 * 1024,
    }
)

PROPERTY_KEYS = (
    "model",
    "device",
    "product_name",
    "build_product",
    "fingerprint",
    "incremental",
    "build_id",
    "android_release",
    "sdk",
    "security_patch",
    "build_type",
    "build_tags",
    "build_characteristics",
    "bootloader",
    "boot_bootloader",
    "verified_boot_state",
    "flash_locked",
    "vbmeta_device_state",
    "warranty_bit",
    "boot_mode",
    "slot_suffix",
    "hardware",
    "board_platform",
    "soc_manufacturer",
    "soc_model",
    "cpu_abilist",
    "first_api_level",
    "boot_completed",
    "bootanim",
    "kernel_release",
    "machine",
    "selinux",
    "shell_identity",
    "boot_id",
)

REMOTE_SNAPSHOT = """set -eu
emit_prop() {
    printf '%s=' "$1"
    getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop build_product ro.build.product
emit_prop fingerprint ro.build.fingerprint
emit_prop incremental ro.build.version.incremental
emit_prop build_id ro.build.id
emit_prop android_release ro.build.version.release
emit_prop sdk ro.build.version.sdk
emit_prop security_patch ro.build.version.security_patch
emit_prop build_type ro.build.type
emit_prop build_tags ro.build.tags
emit_prop build_characteristics ro.build.characteristics
emit_prop bootloader ro.bootloader
emit_prop boot_bootloader ro.boot.bootloader
emit_prop verified_boot_state ro.boot.verifiedbootstate
emit_prop flash_locked ro.boot.flash.locked
emit_prop vbmeta_device_state ro.boot.vbmeta.device_state
emit_prop warranty_bit ro.boot.warranty_bit
emit_prop boot_mode ro.bootmode
emit_prop slot_suffix ro.boot.slot_suffix
emit_prop hardware ro.hardware
emit_prop board_platform ro.board.platform
emit_prop soc_manufacturer ro.soc.manufacturer
emit_prop soc_model ro.soc.model
emit_prop cpu_abilist ro.product.cpu.abilist
emit_prop first_api_level ro.product.first_api_level
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'kernel_release='; uname -r
printf 'machine='; uname -m
printf 'selinux='; getenforce
printf 'shell_identity='; id
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
"""

FIXED_TRANSCRIPT = (
    {
        "ordinal": 1,
        "argv": ["ADB", "version"],
        "timeout_sec": 10,
        "max_bytes": 65_536,
    },
    {
        "ordinal": 2,
        "argv": ["ADB", "devices", "-l"],
        "timeout_sec": 10,
        "max_bytes": 65_536,
    },
    {
        "ordinal": 3,
        "argv": ["ADB", "-s", "BOUND_SERIAL", "get-devpath"],
        "timeout_sec": 10,
        "max_bytes": 65_536,
    },
    {
        "ordinal": 4,
        "argv": [
            "ADB",
            "-s",
            "BOUND_SERIAL",
            "exec-out",
            "sh",
            "-c",
            "FIXED_PUBLIC_SNAPSHOT",
        ],
        "timeout_sec": 20,
        "max_bytes": 65_536,
    },
    {
        "ordinal": 5,
        "argv": [
            "ADB",
            "-s",
            "BOUND_SERIAL",
            "exec-out",
            "sh",
            "-c",
            "FIXED_PUBLIC_SNAPSHOT",
        ],
        "timeout_sec": 20,
        "max_bytes": 65_536,
    },
    {
        "ordinal": 6,
        "argv": ["ADB", "devices", "-l"],
        "timeout_sec": 10,
        "max_bytes": 65_536,
    },
)

ADB_PATH = "/usr/lib/android-sdk/platform-tools/adb"
ADB_SIZE = 716_968
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
ZERO_HASH = "0" * 64
FUTURE_RUNNER_BINDING_JSON = b'{"binding_complete":false,"normalized_sha256":"0000000000000000000000000000000000000000000000000000000000000000","schema":"s20plus_g986n_autonomous_public_health_recovery_v1_runner_binding","status":"UNBOUND_PLACEHOLDER"}\n'
FUTURE_RUNNER_BINDING = MappingProxyType(
    json.loads(FUTURE_RUNNER_BINDING_JSON.decode("ascii"))
)

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
PUBLICATION_ORDER = tuple(
    name
    for ordinal in range(1, 7)
    for name in (
        f"cmd-{ordinal:02d}.stdout.bin",
        f"cmd-{ordinal:02d}.stderr.bin",
        f"cmd-{ordinal:02d}.receipt.json",
    )
) + ("health.json",)
FUTURE_OPENING_NAMES = (
    "opening-intent.json",
    *PUBLICATION_ORDER,
    "opening-result.json",
)
if len(FUTURE_OPENING_NAMES) != RECOVERY_OPENING_FILE_COUNT:
    raise RuntimeError("future opening namespace count differs")

HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
DEVPATH_RE = re.compile(r"usb:[0-9]+-[0-9]+(?:\.[0-9]+)*\Z")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
SAFE_VALUE_RE = re.compile(r"[^\x00\r\n]{0,4096}\Z")
SHELL_ID_RE = re.compile(
    r"uid=2000\(shell\) gid=2000\(shell\)(?: [^\x00\r\n]+)?\Z"
)
MAX_JSON_BYTES = 1024 * 1024


class RecoveryV1Error(RuntimeError):
    """Malformed state or an inactive entrypoint fails closed."""


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
        raise RecoveryV1Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise RecoveryV1Error("digest input is not bytes")
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> Any:
    raise ValueError(f"non-finite JSON constant {value}")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def parse_canonical_json(payload: bytes, label: str, maximum: int = MAX_JSON_BYTES) -> Any:
    if (
        type(payload) is not bytes
        or not payload
        or type(maximum) is not int
        or type(maximum) is bool
        or maximum < 1
        or len(payload) > maximum
    ):
        raise RecoveryV1Error(f"{label} is empty, oversized, or not bytes")
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RecoveryV1Error(f"{label} is not strict JSON") from exc
    if canonical_bytes(value) != payload:
        raise RecoveryV1Error(f"{label} is not exact canonical JSON")
    return value


def _exact_keys(value: Any, keys: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise RecoveryV1Error(f"{label} keys differ")


def _exact_equal(left: Any, right: Any) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def _require_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or type(value) is bool or value < minimum:
        raise RecoveryV1Error(f"{label} is not a strict bounded integer")
    return value


def _require_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise RecoveryV1Error(f"{label} is not lowercase SHA-256")
    return value


def _require_id(value: Any, label: str) -> str:
    if type(value) is not str or ID_RE.fullmatch(value) is None:
        raise RecoveryV1Error(f"{label} is not an exact identifier")
    return value


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
        raise RecoveryV1Error(f"{label} target differs")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        _require_hex(value[key], f"{label}.{key}")
    if value["healthy_android"] is not True or value["foreign_guard_present"] is not False:
        raise RecoveryV1Error(f"{label} is not exact healthy Android")
    return dict(value)


READ_COUNTER_KEYS = {
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


def zero_read_counters() -> dict[str, int]:
    return {key: 0 for key in sorted(READ_COUNTER_KEYS)}


def reserved_read_counters() -> dict[str, int]:
    return {
        "private_evidence_bytes_consumed": 0,
        "private_evidence_bytes_reserved": EVIDENCE_RESERVATION_BYTES,
        "read_operations": 1,
    }


def settled_read_counters(actual: int) -> dict[str, int]:
    measured = _require_int(actual, "actual evidence bytes")
    if measured > EVIDENCE_PROOF_MAX_BYTES:
        raise RecoveryV1Error("actual evidence exceeds proof maximum")
    return {
        "private_evidence_bytes_consumed": measured,
        "private_evidence_bytes_reserved": 0,
        "read_operations": 1,
    }


def validate_read_counters(value: Any, expected: Mapping[str, int], label: str) -> dict[str, int]:
    _exact_keys(value, READ_COUNTER_KEYS, label)
    result = {key: _require_int(value[key], f"{label}.{key}") for key in value}
    if result != dict(expected):
        raise RecoveryV1Error(f"{label} differs from exact one-read state")
    return result


def validate_zero_control_counters(value: Any, label: str) -> dict[str, int]:
    _exact_keys(value, CONTROL_COUNTER_KEYS, label)
    result = {key: _require_int(value[key], f"{label}.{key}") for key in value}
    if any(result.values()):
        raise RecoveryV1Error(f"{label} is not zero-control")
    return result


def parse_inventory(text: str) -> tuple[dict[str, Any], ...]:
    if type(text) is not str:
        raise RecoveryV1Error("inventory is not text")
    rows: list[dict[str, Any]] = []
    serials: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2 or SERIAL_RE.fullmatch(fields[0]) is None:
            raise RecoveryV1Error("inventory row is malformed")
        if fields[0] in serials:
            raise RecoveryV1Error("inventory serial is duplicated")
        serials.add(fields[0])
        metadata = frozenset(fields[2:])
        for prefix in ("model:", "device:", "product:"):
            if len([item for item in metadata if item.startswith(prefix)]) > 1:
                raise RecoveryV1Error("inventory metadata conflicts")
        rows.append({"serial": fields[0], "state": fields[1], "metadata": metadata})
    return tuple(rows)


def select_target(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    if type(rows) is not tuple:
        raise RecoveryV1Error("inventory rows are not immutable")
    matches = [row for row in rows if "model:SM_G986N" in row["metadata"]]
    if len(matches) != 1 or matches[0]["state"] != "device":
        raise RecoveryV1Error("inventory lacks one authorized exact model")
    selected = matches[0]
    for prefix in ("model:", "device:", "product:"):
        if len([item for item in selected["metadata"] if item.startswith(prefix)]) != 1:
            raise RecoveryV1Error("selected inventory metadata is incomplete")
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
        raise RecoveryV1Error("snapshot is not text")
    values: dict[str, str] = {}
    allowed = set(PROPERTY_KEYS)
    for line in text.splitlines():
        if "=" not in line:
            raise RecoveryV1Error("snapshot line is malformed")
        key, value = line.split("=", 1)
        if key not in allowed or key in values or SAFE_VALUE_RE.fullmatch(value) is None:
            raise RecoveryV1Error("snapshot field differs")
        values[key] = value
    if set(values) != allowed:
        raise RecoveryV1Error("snapshot fields are incomplete")
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
        raise RecoveryV1Error("snapshot target/build/health differs")
    return values


def _decode_return(returncode: Any, stdout: Any, stderr: Any, label: str) -> str:
    if type(returncode) is not int or type(returncode) is bool or returncode != 0:
        raise RecoveryV1Error(f"{label} return code differs")
    if type(stdout) is not bytes or type(stderr) is not bytes or stderr:
        raise RecoveryV1Error(f"{label} streams differ")
    try:
        return stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise RecoveryV1Error(f"{label} is not UTF-8") from exc


def _validate_tool(value: Any, label: str) -> dict[str, Any]:
    keys = {"path", "device", "inode", "mtime_ns", "size", "sha256"}
    _exact_keys(value, keys, label)
    for key in ("device", "inode", "mtime_ns", "size"):
        _require_int(value[key], f"{label}.{key}")
    if (
        value["path"] != ADB_PATH
        or value["size"] != ADB_SIZE
        or value["sha256"] != ADB_SHA256
    ):
        raise RecoveryV1Error(f"{label} differs from frozen host tool")
    return dict(value)


def _validate_expected_host_tool(value: Any, label: str) -> dict[str, Any]:
    _exact_keys(value, {"path", "size", "sha256"}, label)
    _require_int(value["size"], f"{label}.size")
    _require_hex(value["sha256"], f"{label}.sha256")
    expected = {"path": ADB_PATH, "size": ADB_SIZE, "sha256": ADB_SHA256}
    if not _exact_equal(value, expected):
        raise RecoveryV1Error(f"{label} differs from exact expected host tool")
    return dict(value)


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


def _validate_intent_shape(intent: Any, intent_raw: bytes) -> dict[str, Any]:
    _exact_keys(intent, INTENT_KEYS, "read intent")
    if type(intent_raw) is not bytes or canonical_bytes(intent) != intent_raw:
        raise RecoveryV1Error("read intent bytes differ")
    mirrored = _require_int(intent["mirrored_at"], "intent mirrored_at")
    lease_issued = _require_int(intent["lease_issued_at"], "intent lease issued_at")
    lease_observed = _require_int(
        intent["lease_observed_at"], "intent lease observed_at"
    )
    campaign_expiry = _require_int(intent["campaign_expires_at"], "campaign expiry")
    session_expiry = _require_int(intent["session_expires_at"], "session expiry")
    reservation = _require_int(intent["reservation_bytes"], "intent reservation")
    _require_id(intent["campaign_id"], "intent campaign id")
    _require_id(intent["session_id"], "intent session id")
    _require_hex(intent["coordinator_lease_sha256"], "intent lease hash")
    _require_hex(intent["coordinator_head_sha256"], "intent head hash")
    _require_hex(intent["previous_evidence_result_sha256"], "prior result hash")
    _require_hex(intent["previous_coordinator_complete_sha256"], "prior complete hash")
    validate_source_identity(intent["source_identity"], "intent source")
    validate_read_counters(intent["child_counters"], reserved_read_counters(), "intent child")
    validate_read_counters(
        intent["campaign_counters"], reserved_read_counters(), "intent campaign"
    )
    if (
        intent["schema"] != READ_INTENT_SCHEMA
        or intent["kind"] != "read-intent-mirror"
        or intent["target"] != TARGET
        or intent["action"] != "public-health"
        or type(intent["read_ordinal"]) is not int
        or intent["read_ordinal"] != 1
        or reservation != EVIDENCE_RESERVATION_BYTES
        or mirrored != lease_observed
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
        or intent["previous_evidence_result_sha256"] != ZERO_HASH
        or intent["previous_coordinator_complete_sha256"] != ZERO_HASH
    ):
        raise RecoveryV1Error("read intent semantics differ")
    return dict(intent)


def model_exact_intent_mirror(
    lease: Mapping[str, Any],
    lease_raw: bytes,
    accounting: Mapping[str, Any],
    mirrored_at: int,
) -> dict[str, Any]:
    timestamp = _require_int(mirrored_at, "intent mirror timestamp")
    if timestamp < _require_int(lease["issued_at"], "lease issued_at"):
        raise RecoveryV1Error("intent mirror predates validated lease")
    return {
        "schema": READ_INTENT_SCHEMA,
        "kind": "read-intent-mirror",
        "mirrored_at": timestamp,
        "campaign_id": accounting["campaign_id"],
        "session_id": accounting["session_id"],
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
        "reservation_bytes": EVIDENCE_RESERVATION_BYTES,
        "expected_evidence_names": list(EVIDENCE_NAMES),
        "attempt_consumed": True,
        "uncertain_if_incomplete": True,
        "replay_authorized": False,
        "next_action_before_coordinator_complete": False,
        "command_execution_backend": False,
    }


def validate_intent(
    intent: Any,
    intent_raw: bytes,
    lease: Mapping[str, Any],
    lease_raw: bytes,
    accounting: Mapping[str, Any],
    accounting_raw: bytes,
    guard_raw: bytes,
    opening_raw: bytes,
    session_raw: bytes,
) -> dict[str, Any]:
    """Validate an intent against the entire exact retained opening/lease chain."""
    guard = parse_canonical_json(
        guard_raw, "base guard", STRUCTURAL_CAPS["active-campaign.json"]
    )
    opening = parse_canonical_json(
        opening_raw, "base opening", STRUCTURAL_CAPS["opening.json"]
    )
    session = parse_canonical_json(
        session_raw,
        "base session opening",
        STRUCTURAL_CAPS["session-opening.json"],
    )
    allocation = validate_base_allocation(
        guard, guard_raw, opening, opening_raw, session, session_raw
    )
    validated_accounting = validate_accounting_opening(
        accounting,
        accounting_raw,
        allocation,
        guard_raw,
        opening_raw,
        session_raw,
    )
    validated_lease = validate_lease(
        lease,
        lease_raw,
        validated_accounting,
        accounting_raw,
        session,
        session_raw,
    )
    actual = _validate_intent_shape(intent, intent_raw)
    expected = model_exact_intent_mirror(
        validated_lease, lease_raw, validated_accounting, actual["mirrored_at"]
    )
    if not _exact_equal(actual, expected):
        raise RecoveryV1Error("read intent is not the exact validated lease mirror")
    return actual


RECEIPT_KEYS = {
    "schema",
    "read_ordinal",
    "ordinal",
    "predecessor_sha256",
    "argv_template_sha256",
    "argv_sha256",
    "timeout_sec",
    "max_bytes",
    "returncode",
    "execution_started_at",
    "execution_completed_at",
    "return_retained_at",
    "receipt_published_at",
    "stdout_size",
    "stdout_sha256",
    "stderr_size",
    "stderr_sha256",
    "host_tool_before",
    "host_tool_after",
}


def _expected_actual_argvs(serial: str) -> tuple[list[str], ...]:
    if type(serial) is not str or SERIAL_RE.fullmatch(serial) is None:
        raise RecoveryV1Error("selected serial grammar differs")
    return (
        [ADB_PATH, "version"],
        [ADB_PATH, "devices", "-l"],
        [ADB_PATH, "-s", serial, "get-devpath"],
        [ADB_PATH, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
        [ADB_PATH, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
        [ADB_PATH, "devices", "-l"],
    )


def validate_return_receipts(
    intent: Mapping[str, Any],
    intent_raw: bytes,
    evidence_files: Mapping[str, bytes],
) -> tuple[dict[str, Any], ...]:
    # Presence-only retained-return parsing validates the strict intent shape.
    # Settlement callers must first use validate_intent() with the full chain.
    intent = _validate_intent_shape(intent, intent_raw)
    if type(evidence_files) is not dict or not set(RETURN_NAMES) <= set(evidence_files):
        raise RecoveryV1Error("retained return set is incomplete")
    inventory_text = _decode_return(
        0,
        evidence_files["cmd-02.stdout.bin"],
        evidence_files["cmd-02.stderr.bin"],
        "initial inventory",
    )
    serial = select_target(parse_inventory(inventory_text))["serial"]
    argvs = _expected_actual_argvs(serial)
    predecessor = sha256_bytes(intent_raw)
    common_tool: dict[str, Any] | None = None
    previous_published = intent["mirrored_at"]
    receipts: list[dict[str, Any]] = []
    for ordinal, (template, argv) in enumerate(
        zip(FIXED_TRANSCRIPT, argvs, strict=True), 1
    ):
        stdout_name = f"cmd-{ordinal:02d}.stdout.bin"
        stderr_name = f"cmd-{ordinal:02d}.stderr.bin"
        receipt_name = f"cmd-{ordinal:02d}.receipt.json"
        stdout = evidence_files[stdout_name]
        stderr = evidence_files[stderr_name]
        raw = evidence_files[receipt_name]
        if type(stdout) is not bytes or type(stderr) is not bytes:
            raise RecoveryV1Error("retained raw stream is not bytes")
        if len(stdout) + len(stderr) > template["max_bytes"]:
            raise RecoveryV1Error("retained raw pair exceeds bound")
        receipt = parse_canonical_json(raw, receipt_name, 8 * 1024)
        _exact_keys(receipt, RECEIPT_KEYS, receipt_name)
        started = _require_int(receipt["execution_started_at"], "execution start")
        completed = _require_int(receipt["execution_completed_at"], "execution complete")
        retained = _require_int(receipt["return_retained_at"], "return retained")
        published = _require_int(receipt["receipt_published_at"], "receipt published")
        before = _validate_tool(receipt["host_tool_before"], "host tool before")
        after = _validate_tool(receipt["host_tool_after"], "host tool after")
        if common_tool is None:
            common_tool = before
        if (
            receipt["schema"] != COMMAND_EVIDENCE_SCHEMA
            or type(receipt["read_ordinal"]) is not int
            or receipt["read_ordinal"] != 1
            or type(receipt["ordinal"]) is not int
            or receipt["ordinal"] != ordinal
            or receipt["predecessor_sha256"] != predecessor
            or receipt["argv_template_sha256"]
            != sha256_bytes(canonical_bytes(template["argv"]))
            or receipt["argv_sha256"] != sha256_bytes(canonical_bytes(argv))
            or type(receipt["timeout_sec"]) is not int
            or receipt["timeout_sec"] != template["timeout_sec"]
            or type(receipt["max_bytes"]) is not int
            or receipt["max_bytes"] != template["max_bytes"]
            or type(receipt["returncode"]) is not int
            or type(receipt["returncode"]) is bool
            or receipt["returncode"] != 0
            or started < previous_published
            or completed < started
            or completed - started > template["timeout_sec"]
            or retained < completed
            or published < retained
            or published >= intent["campaign_expires_at"]
            or published >= intent["session_expires_at"]
            or receipt["stdout_size"] != len(stdout)
            or receipt["stdout_sha256"] != sha256_bytes(stdout)
            or receipt["stderr_size"] != len(stderr)
            or receipt["stderr_sha256"] != sha256_bytes(stderr)
            or before != after
            or (common_tool is not None and before != common_tool)
        ):
            raise RecoveryV1Error("retained receipt chain differs")
        for key in ("stdout_size", "stderr_size"):
            _require_int(receipt[key], f"receipt {key}")
        for key in (
            "predecessor_sha256",
            "argv_template_sha256",
            "argv_sha256",
            "stdout_sha256",
            "stderr_sha256",
        ):
            _require_hex(receipt[key], f"receipt {key}")
        receipts.append(receipt)
        predecessor = sha256_bytes(raw)
        previous_published = published
    return tuple(receipts)


def validate_health_result(value: Any) -> dict[str, Any]:
    required = {
        "schema",
        "version",
        "mode",
        "target",
        "properties",
        "boot_id_sha256",
        "usb_debugging_verified",
        "adb_authorization_state",
        "host_tool",
        "host_command_count",
        "inventory_command_count",
        "selected_target_command_count",
        "other_target_command_count",
        "s22plus_command_count",
        "a90_command_count",
        "device_writes",
        "root_used",
        "reboot_requested",
        "mode_transition_requested",
        "payload_transfer",
        "partition_access",
        "d1_authorized",
        "f1_authorized",
        "verdict",
    }
    _exact_keys(value, required, "health result")
    if (
        value["schema"] != HEALTH_SCHEMA
        or value["version"] != HEALTH_VERSION
        or value["mode"] != "connected-read-only"
        or value["verdict"] != HEALTH_VERDICT
    ):
        raise RecoveryV1Error("health schema differs")
    target = value["target"]
    _exact_keys(
        target,
        {
            "model",
            "adb_serial_sha256",
            "usb_topology_sha256",
            "other_serial_sha256",
            "inventory_sha256",
        },
        "health target",
    )
    if target["model"] != TARGET["model"]:
        raise RecoveryV1Error("health target differs")
    for key in ("adb_serial_sha256", "usb_topology_sha256", "inventory_sha256"):
        _require_hex(target[key], f"health target {key}")
    if type(target["other_serial_sha256"]) is not list:
        raise RecoveryV1Error("other serial receipt is not a list")
    for item in target["other_serial_sha256"]:
        _require_hex(item, "other serial hash")
    properties = value["properties"]
    expected_properties = set(PROPERTY_KEYS) - {"boot_id"}
    _exact_keys(properties, expected_properties, "health properties")
    fixed = {
        "model": TARGET["model"],
        "device": TARGET["device"],
        "product_name": TARGET["product"],
        "build_product": TARGET["device"],
        "incremental": TARGET["build"],
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    if any(properties[key] != expected for key, expected in fixed.items()):
        raise RecoveryV1Error("health properties differ")
    if (
        f"/{TARGET['product']}/{TARGET['device']}:" not in properties["fingerprint"]
        or not properties["fingerprint"].endswith(":user/release-keys")
        or SHELL_ID_RE.fullmatch(properties["shell_identity"]) is None
    ):
        raise RecoveryV1Error("health fingerprint or shell differs")
    _require_hex(value["boot_id_sha256"], "health boot id")
    counts = {
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }
    if any(type(value[key]) is not int or value[key] != expected for key, expected in counts.items()):
        raise RecoveryV1Error("health command counts differ")
    if value["usb_debugging_verified"] is not True or value["adb_authorization_state"] != "device":
        raise RecoveryV1Error("health ADB state differs")
    for key in (
        "device_writes",
        "root_used",
        "reboot_requested",
        "mode_transition_requested",
        "payload_transfer",
        "partition_access",
        "d1_authorized",
        "f1_authorized",
    ):
        if value[key] is not False:
            raise RecoveryV1Error("health crosses read-only boundary")
    tool = value["host_tool"]
    _exact_keys(
        tool,
        {"path", "device", "inode", "mtime_ns", "size", "sha256", "version_output_sha256"},
        "health tool",
    )
    _validate_tool({key: tool[key] for key in ("path", "device", "inode", "mtime_ns", "size", "sha256")}, "health tool")
    _require_hex(tool["version_output_sha256"], "health tool version hash")
    return dict(value)


def derive_health_from_retained(
    intent: Mapping[str, Any], intent_raw: bytes, evidence_files: Mapping[str, bytes]
) -> dict[str, Any]:
    receipts = validate_return_receipts(intent, intent_raw, evidence_files)
    triples = [
        (
            receipts[ordinal - 1]["returncode"],
            evidence_files[f"cmd-{ordinal:02d}.stdout.bin"],
            evidence_files[f"cmd-{ordinal:02d}.stderr.bin"],
        )
        for ordinal in range(1, 7)
    ]
    version = _decode_return(*triples[0], "ADB version")
    first_rows = parse_inventory(_decode_return(*triples[1], "initial inventory"))
    selected = select_target(first_rows)
    serial = selected["serial"]
    devpath = _decode_return(*triples[2], "selected devpath")
    if DEVPATH_RE.fullmatch(devpath) is None:
        raise RecoveryV1Error("selected devpath differs")
    first_snapshot = parse_snapshot(_decode_return(*triples[3], "first snapshot"))
    second_snapshot = parse_snapshot(_decode_return(*triples[4], "second snapshot"))
    if first_snapshot != second_snapshot:
        raise RecoveryV1Error("public snapshots differ")
    expected_metadata = {
        "model:SM_G986N",
        f"device:{TARGET['device']}",
        f"product:{TARGET['product']}",
    }
    if not expected_metadata <= selected["metadata"]:
        raise RecoveryV1Error("selected inventory conflicts with snapshot")
    final_rows = parse_inventory(_decode_return(*triples[5], "final inventory"))
    final_selected = select_target(final_rows)
    if (
        final_selected["serial"] != serial
        or _sanitized_inventory(final_rows) != _sanitized_inventory(first_rows)
    ):
        raise RecoveryV1Error("target or inventory drifted")
    properties = dict(first_snapshot)
    boot_id = properties.pop("boot_id")
    common_tool = _validate_tool(receipts[0]["host_tool_before"], "retained host tool")
    result = {
        "schema": HEALTH_SCHEMA,
        "version": HEALTH_VERSION,
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
        "verdict": HEALTH_VERDICT,
    }
    source = validate_source_identity(intent["source_identity"], "intent source")
    if (
        result["target"]["adb_serial_sha256"] != source["serial_sha256"]
        or result["target"]["usb_topology_sha256"] != source["topology_sha256"]
        or result["boot_id_sha256"] != source["boot_id_sha256"]
    ):
        raise RecoveryV1Error("derived health differs from intent source")
    validate_health_result(result)
    if len(canonical_bytes(result)) > 64 * 1024:
        raise RecoveryV1Error("derived health exceeds 64 KiB")
    return result


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


def evidence_manifest(evidence_files: Mapping[str, bytes]) -> tuple[list[dict[str, Any]], int]:
    if type(evidence_files) is not dict or set(evidence_files) != set(EVIDENCE_NAMES):
        raise RecoveryV1Error("evidence set is not exact 19-file closure")
    manifest: list[dict[str, Any]] = []
    raw_total = 0
    receipt_total = 0
    for name in EVIDENCE_NAMES:
        payload = evidence_files[name]
        if type(payload) is not bytes:
            raise RecoveryV1Error("evidence payload is not bytes")
        if name.endswith(".bin"):
            raw_total += len(payload)
        elif name.endswith(".receipt.json"):
            if len(payload) > 8 * 1024:
                raise RecoveryV1Error("receipt exceeds 8 KiB")
            receipt_total += len(payload)
        elif name == "health.json" and len(payload) > 64 * 1024:
            raise RecoveryV1Error("health exceeds 64 KiB")
        manifest.append({"name": name, "size": len(payload), "sha256": sha256_bytes(payload)})
    for ordinal in range(1, 7):
        if (
            len(evidence_files[f"cmd-{ordinal:02d}.stdout.bin"])
            + len(evidence_files[f"cmd-{ordinal:02d}.stderr.bin"])
            > 64 * 1024
        ):
            raise RecoveryV1Error("raw pair exceeds 64 KiB")
    actual = sum(item["size"] for item in manifest)
    if raw_total > 393_216 or receipt_total > 49_152 or actual > EVIDENCE_PROOF_MAX_BYTES:
        raise RecoveryV1Error("evidence aggregate exceeds bound")
    return manifest, actual


def validate_read_result(
    result: Any,
    result_raw: bytes,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    lease: Mapping[str, Any],
    lease_raw: bytes,
    accounting: Mapping[str, Any],
    accounting_raw: bytes,
    guard_raw: bytes,
    opening_raw: bytes,
    session_raw: bytes,
    evidence_files: Mapping[str, bytes],
) -> dict[str, Any]:
    _exact_keys(result, READ_RESULT_KEYS, "read result")
    if canonical_bytes(result) != result_raw:
        raise RecoveryV1Error("read result bytes differ")
    validate_intent(
        intent,
        intent_raw,
        lease,
        lease_raw,
        accounting,
        accounting_raw,
        guard_raw,
        opening_raw,
        session_raw,
    )
    derived_health = derive_health_from_retained(intent, intent_raw, evidence_files)
    if evidence_files.get("health.json") != canonical_bytes(derived_health):
        raise RecoveryV1Error("health file differs from retained derivation")
    manifest, actual = evidence_manifest(evidence_files)
    reported_actual = _require_int(
        result["actual_evidence_bytes"], "result actual evidence bytes"
    )
    completed = _require_int(result["completed_at"], "result completed_at")
    last_receipt = parse_canonical_json(
        evidence_files["cmd-06.receipt.json"],
        "last command receipt",
        8 * 1024,
    )
    last_published = _require_int(
        last_receipt["receipt_published_at"], "last receipt published_at"
    )
    cut = result["reporting_cut_at"]
    if cut is not None:
        cut = _require_int(cut, "result reporting cut")
    expected_after = (
        cut is not None
        or completed >= intent["campaign_expires_at"]
        or completed >= intent["session_expires_at"]
    )
    expected_counters = settled_read_counters(actual)
    for key in (
        "intent_sha256",
        "coordinator_lease_sha256",
        "last_receipt_sha256",
        "health_sha256",
        "evidence_set_sha256",
    ):
        _require_hex(result[key], f"result {key}")
    validate_source_identity(result["source_identity"], "result source")
    validate_read_counters(result["child_counters"], expected_counters, "result child")
    validate_read_counters(result["campaign_counters"], expected_counters, "result campaign")
    if (
        result["schema"] != READ_RESULT_SCHEMA
        or result["kind"] != "read-result"
        or result["campaign_id"] != intent["campaign_id"]
        or result["session_id"] != intent["session_id"]
        or result["target"] != TARGET
        or not _exact_equal(result["source_identity"], intent["source_identity"])
        or result["action"] != "public-health"
        or type(result["read_ordinal"]) is not int
        or result["read_ordinal"] != 1
        or result["intent_sha256"] != sha256_bytes(intent_raw)
        or result["coordinator_lease_sha256"] != sha256_bytes(lease_raw)
        or result["last_receipt_sha256"]
        != sha256_bytes(evidence_files["cmd-06.receipt.json"])
        or result["health_sha256"] != sha256_bytes(evidence_files["health.json"])
        or not _exact_equal(result["evidence_files"], manifest)
        or result["evidence_set_sha256"] != sha256_bytes(canonical_bytes(manifest))
        or reported_actual != actual
        or completed < intent["mirrored_at"]
        or completed < last_published
        or (cut is not None and (cut < last_published or cut > completed))
        or result["outcome_proven"] is not True
        or type(result["reporting_after_expiry_or_drift"]) is not bool
        or result["reporting_after_expiry_or_drift"] is not expected_after
        or result["replay_authorized"] is not False
        or result["coordinator_complete_required"] is not True
        or type(result["device_command_count_by_owner"]) is not int
        or result["device_command_count_by_owner"] != 0
        or type(result["device_effect_count"]) is not int
        or result["device_effect_count"] != 0
    ):
        raise RecoveryV1Error("read result semantics differ")
    return dict(result)


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


def model_parked_completion(result: Mapping[str, Any], result_raw: bytes, completed_at: int) -> dict[str, Any]:
    timestamp = _require_int(completed_at, "completion completed_at")
    if timestamp < _require_int(result["completed_at"], "result completed_at"):
        raise RecoveryV1Error("completion predates result")
    return {
        "schema": COORDINATOR_COMPLETE_SCHEMA,
        "kind": "public-health-read-complete",
        "completed_at": timestamp,
        "campaign_id": result["campaign_id"],
        "session_id": result["session_id"],
        "target": TARGET,
        "action": "public-health",
        "read_ordinal": 1,
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


def validate_parked_completion(
    completion: Any,
    completion_raw: bytes,
    result: Mapping[str, Any],
    result_raw: bytes,
) -> dict[str, Any]:
    _exact_keys(completion, COMPLETE_KEYS, "parked completion")
    if canonical_bytes(completion) != completion_raw:
        raise RecoveryV1Error("completion bytes differ")
    expected = model_parked_completion(result, result_raw, completion["completed_at"])
    if not _exact_equal(completion, expected):
        raise RecoveryV1Error("completion differs from exact parked model")
    return dict(completion)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _runner_binding_from_core(core_bytes: bytes) -> dict[str, Any]:
    if type(core_bytes) is not bytes:
        raise RecoveryV1Error("recovery core is not bytes")
    try:
        tree = ast.parse(core_bytes.decode("utf-8", "strict"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise RecoveryV1Error("recovery core source is not exact Python") from exc
    matches: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                isinstance(target, ast.Name)
                and target.id == "FUTURE_RUNNER_BINDING_JSON"
                for target in targets
            ):
                matches.append(node.value)
    if len(matches) != 1:
        raise RecoveryV1Error("future runner binding source field is ambiguous")
    try:
        raw = ast.literal_eval(matches[0])
    except (TypeError, ValueError) as exc:
        raise RecoveryV1Error("future runner binding source field is not literal") from exc
    binding = parse_canonical_json(raw, "embedded future runner binding", 4 * 1024)
    _exact_keys(
        binding,
        {"schema", "status", "normalized_sha256", "binding_complete"},
        "embedded future runner binding",
    )
    if (
        binding["schema"] != RUNNER_BINDING_SCHEMA
        or type(binding["status"]) is not str
        or type(binding["binding_complete"]) is not bool
    ):
        raise RecoveryV1Error("embedded future runner binding semantics differ")
    _require_hex(binding["normalized_sha256"], "embedded runner normalized hash")
    return binding


def validate_core_identity(core_bytes: bytes) -> dict[str, Any]:
    if type(core_bytes) is not bytes or not core_bytes or len(core_bytes) > RECOVERY_CORE_MAX_BYTES:
        raise RecoveryV1Error("recovery core bytes exceed 256 KiB")
    normalized = normalized_self_sha256(core_bytes)
    if (
        EXPECTED_RECOVERY_NORMALIZED_SHA256 == ZERO_HASH
        or normalized != EXPECTED_RECOVERY_NORMALIZED_SHA256
    ):
        raise RecoveryV1Error("recovery core normalized identity is not qualified")
    return {
        "size": len(core_bytes),
        "sha256": sha256_bytes(core_bytes),
        "normalized_sha256": normalized,
        "runner_binding": _runner_binding_from_core(core_bytes),
    }


def build_manifest(core_bytes: bytes) -> dict[str, Any]:
    core_identity = validate_core_identity(core_bytes)
    binding = core_identity["runner_binding"]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "H0_PRIVATE_RECOVERY_COPY_NOT_ACTIVE",
        "target": TARGET,
        "core": {
            "name": RECOVERY_CORE_NAME,
            "size": len(core_bytes),
            "sha256": sha256_bytes(core_bytes),
            "normalized_sha256": core_identity["normalized_sha256"],
            "normalized_sha256_expected": EXPECTED_RECOVERY_NORMALIZED_SHA256,
            "runner_binding_is_activation_normalized": True,
            "mode": "0400",
        },
        "future_runner_binding": binding,
        "future_runner_binding_sha256": sha256_bytes(canonical_bytes(binding)),
        "oracles": _plain(ORACLE_IDENTITIES),
        "retained_source_receipts": _plain(EXPECTED_RETAINED_SOURCE_RECEIPTS),
        "fixed_roots": {key: str(value) for key, value in FIXED_ROOTS.items()},
        "schemas": {
            "base": BASE_SCHEMA,
            "health": HEALTH_SCHEMA,
            "accounting_opening": ACCOUNTING_OPENING_SCHEMA,
            "read_intent": READ_INTENT_SCHEMA,
            "command_evidence": COMMAND_EVIDENCE_SCHEMA,
            "read_result": READ_RESULT_SCHEMA,
            "coordinator_lease": COORDINATOR_LEASE_SCHEMA,
            "coordinator_complete": COORDINATOR_COMPLETE_SCHEMA,
        },
        "caps": {
            "core_max_bytes": RECOVERY_CORE_MAX_BYTES,
            "manifest_max_bytes": RECOVERY_MANIFEST_MAX_BYTES,
            "recovery_bundle_max_bytes": RECOVERY_BUNDLE_MAX_BYTES,
            "recovery_opening_max_bytes": RECOVERY_OPENING_MAX_BYTES,
            "campaign_binding_max_bytes": CAMPAIGN_BINDING_MAX_BYTES,
            "structural_max_bytes": STRUCTURAL_MAX_BYTES,
            "evidence_reservation_bytes": EVIDENCE_RESERVATION_BYTES,
            "evidence_proof_max_bytes": EVIDENCE_PROOF_MAX_BYTES,
            "completed_total_max_bytes": COMPLETED_TOTAL_MAX_BYTES,
            "completed_total_file_count": COMPLETED_TOTAL_FILE_COUNT,
            "recovery_opening_file_count": RECOVERY_OPENING_FILE_COUNT,
        },
        "structural_node_caps": dict(STRUCTURAL_CAPS),
        "evidence_names": list(EVIDENCE_NAMES),
        "evidence_publication_order": list(PUBLICATION_ORDER),
        "future_leaf_namespace": {
            "lock": LOCK_NAME,
            "recovery_directory": RECOVERY_DIRECTORY,
            "opening_directory": OPENING_DIRECTORY,
            "opening_names": list(FUTURE_OPENING_NAMES),
            "campaign_binding": CAMPAIGN_BINDING_NAME,
            "lease": "public-health-read-lease-000001.json",
            "completion": "public-health-read-complete-000001.json",
            "current_scanner_accepts_opening_or_campaign_binding": False,
        },
        "property_keys": list(PROPERTY_KEYS),
        "remote_snapshot_sha256": sha256_bytes(REMOTE_SNAPSHOT.encode()),
        "fixed_transcript": _plain(FIXED_TRANSCRIPT),
        "entrypoints": {
            "scan_fixed_state": "zero-command-gated-inactive",
            "classify_cut": "pure-presence-only-no-settlement",
            "finalize_zero_command": "not-implemented-gated-inactive",
            "reemit_terminal": "not-implemented-gated-inactive",
        },
        "manifest_published_last": True,
        "direct_path_execution_authoritative": False,
        "private_core_requires_nofollow_manifest_verified_loader": True,
        "same_module_verifier_is_loader_authority": False,
        "independent_loader_runner_identity_cross_check_implemented": False,
        "replay_authorized": False,
        "refund_authorized": False,
        "next_action_authorized": False,
        "live_authority": False,
    }
    raw = canonical_bytes(manifest)
    if len(raw) > RECOVERY_MANIFEST_MAX_BYTES or len(core_bytes) + len(raw) > RECOVERY_BUNDLE_MAX_BYTES:
        raise RecoveryV1Error("recovery manifest/bundle exceeds bound")
    return manifest


def validate_manifest(manifest: Any, manifest_raw: bytes, core_bytes: bytes) -> dict[str, Any]:
    expected = build_manifest(core_bytes)
    if (
        type(manifest_raw) is not bytes
        or canonical_bytes(manifest) != manifest_raw
        or not _exact_equal(manifest, expected)
    ):
        raise RecoveryV1Error("recovery manifest differs from frozen core binding")
    return dict(manifest)


BASE_OPENING_KEYS = {
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
BASE_SESSION_KEYS = {
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
BASE_GUARD_KEYS = {
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
CONTEXT_KEYS = {
    "campaign_id",
    "session_id",
    "phase",
    "expired",
    "session_expired",
    "current_time",
    "campaign_expires_at",
    "session_expires_at",
    "current_ordinal",
    "source_identity",
    "endpoint",
    "predecessor_sha256",
    "child_counters",
    "campaign_counters",
    "terminal",
    "f1_intent",
    "approval_consumed",
    "partition_transfer",
    "no_replay",
    "pending_intent_issued_at",
}
POLICY_BINDING_SHA256 = (
    "0299b3a3ddbd0e496f46092b0f547ce24064e66636b90274a574d86007b9be82"
)
BASE_NORMALIZED_SHA256 = (
    "8d28f370f16d1f0d86eaa456fae09c01160d9fd8445529184643223934f4aea1"
)


def validate_base_allocation(
    guard: Any,
    guard_raw: bytes,
    opening: Any,
    opening_raw: bytes,
    session: Any,
    session_raw: bytes,
) -> dict[str, Any]:
    _exact_keys(guard, BASE_GUARD_KEYS, "base guard")
    _exact_keys(opening, BASE_OPENING_KEYS, "base opening")
    _exact_keys(session, BASE_SESSION_KEYS, "base session")
    if (
        canonical_bytes(guard) != guard_raw
        or canonical_bytes(opening) != opening_raw
        or canonical_bytes(session) != session_raw
    ):
        raise RecoveryV1Error("base allocation raw bytes differ")
    campaign_id = _require_id(opening["campaign_id"], "base campaign id")
    session_id = _require_id(opening["session_id"], "base session id")
    source = validate_source_identity(opening["source_identity"], "base source")
    session_source = validate_source_identity(
        session["source_identity"], "base session source"
    )
    guard_source = validate_source_identity(guard["source_identity"], "base guard source")
    opened = _require_int(opening["opened_at"], "base opened_at")
    campaign_expiry = _require_int(opening["expires_at"], "base campaign expiry")
    session_opened = _require_int(session["opened_at"], "session opened_at")
    session_expiry = _require_int(session["expires_at"], "session expiry")
    guard_opened = _require_int(guard["opened_at"], "guard opened_at")
    guard_expiry = _require_int(guard["expires_at"], "guard expiry")
    for value, label in (
        (opening["child_counters"], "opening child controls"),
        (opening["campaign_counters"], "opening campaign controls"),
        (session["child_counters"], "session child controls"),
        (session["campaign_counters"], "session campaign controls"),
        (guard["child_counters"], "guard child controls"),
        (guard["campaign_counters"], "guard campaign controls"),
    ):
        validate_zero_control_counters(value, label)
    if (
        opening["schema"] != BASE_SCHEMA
        or opening["kind"] != "campaign-opening"
        or opening["target"] != TARGET
        or opening["policy_binding_sha256"] != POLICY_BINDING_SHA256
        or opening["coordinator_normalized_sha256"] != BASE_NORMALIZED_SHA256
        or opening["predecessor_sha256"] != ZERO_HASH
        or opening["attended_opening"] is not True
        or opening["no_replay"] is not True
        or any(
            opening[key] is not False
            for key in ("f1_intent", "approval_consumed", "partition_transfer")
        )
        or campaign_expiry != opened + 24 * 60 * 60
        or session["schema"] != BASE_SCHEMA
        or session["kind"] != "session-opening"
        or session["campaign_id"] != campaign_id
        or session["session_id"] != session_id
        or session["target"] != TARGET
        or session["policy_binding_sha256"] != POLICY_BINDING_SHA256
        or session["coordinator_normalized_sha256"] != BASE_NORMALIZED_SHA256
        or not _exact_equal(session_source, source)
        or session_opened != opened
        or session_expiry != opened + 4 * 60 * 60
        or session_expiry > campaign_expiry
        or session["predecessor_sha256"] != sha256_bytes(opening_raw)
        or session["no_replay"] is not True
        or guard["schema"] != BASE_SCHEMA
        or guard["kind"] != "campaign-guard"
        or guard["phase"] != "allocation-claimed"
        or guard["campaign_id"] != campaign_id
        or guard["session_id"] != session_id
        or guard["target"] != TARGET
        or guard["policy_binding_sha256"] != POLICY_BINDING_SHA256
        or guard["coordinator_normalized_sha256"] != BASE_NORMALIZED_SHA256
        or not _exact_equal(guard_source, source)
        or guard_opened != opened
        or guard_expiry != campaign_expiry
        or guard["opening_sha256"] != sha256_bytes(opening_raw)
        or guard["session_opening_sha256"] != sha256_bytes(session_raw)
        or canonical_bytes(guard["opening"]) != opening_raw
        or canonical_bytes(guard["session"]) != session_raw
        or guard["no_replay"] is not True
        or any(
            guard[key] is not False
            for key in ("f1_intent", "approval_consumed", "partition_transfer")
        )
    ):
        raise RecoveryV1Error("base allocation semantics differ")
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_identity": source,
        "opened_at": opened,
        "campaign_expires_at": campaign_expiry,
        "session_expires_at": session_expiry,
    }


def _validate_retained_source_receipts(value: Any) -> None:
    _exact_keys(
        value,
        {"owner", "coordinator", "health", "inventory"},
        "source receipts",
    )
    if not _exact_equal(value, _plain(EXPECTED_RETAINED_SOURCE_RECEIPTS)):
        raise RecoveryV1Error("retained source receipts are not exact frozen content")


def validate_accounting_opening(
    value: Any,
    raw: bytes,
    allocation: Mapping[str, Any],
    guard_raw: bytes,
    opening_raw: bytes,
    session_raw: bytes,
) -> dict[str, Any]:
    _exact_keys(value, ACCOUNTING_OPENING_KEYS, "accounting opening")
    if canonical_bytes(value) != raw:
        raise RecoveryV1Error("accounting opening raw bytes differ")
    campaign_id = allocation["campaign_id"]
    session_id = allocation["session_id"]
    source = allocation["source_identity"]
    allocation_source = validate_source_identity(
        value["allocation_source_identity"], "accounting allocation source"
    )
    current_source = validate_source_identity(
        value["source_identity"], "accounting current source"
    )
    recorded = _require_int(value["recorded_at"], "accounting recorded_at")
    context = value["first_current_context"]
    _exact_keys(context, CONTEXT_KEYS, "accounting current context")
    current = _require_int(context["current_time"], "context time")
    context_campaign_expiry = _require_int(
        context["campaign_expires_at"], "context campaign expiry"
    )
    context_session_expiry = _require_int(
        context["session_expires_at"], "context session expiry"
    )
    context_source = validate_source_identity(
        context["source_identity"], "accounting context source"
    )
    validate_zero_control_counters(context["child_counters"], "context child controls")
    validate_zero_control_counters(
        context["campaign_counters"], "context campaign controls"
    )
    _validate_retained_source_receipts(value["sources"])
    validate_read_counters(value["child_counters"], zero_read_counters(), "opening child")
    validate_read_counters(
        value["campaign_counters"], zero_read_counters(), "opening campaign"
    )
    if (
        value["schema"] != ACCOUNTING_OPENING_SCHEMA
        or value["kind"] != "accounting-opening"
        or value["campaign_id"] != campaign_id
        or value["session_id"] != session_id
        or value["target"] != TARGET
        or not _exact_equal(allocation_source, source)
        or not _exact_equal(current_source, source)
        or canonical_bytes(value["coordinator_guard"]) != guard_raw
        or canonical_bytes(value["coordinator_opening"]) != opening_raw
        or canonical_bytes(value["coordinator_session"]) != session_raw
        or value["coordinator_guard_sha256"] != sha256_bytes(guard_raw)
        or value["coordinator_opening_sha256"] != sha256_bytes(opening_raw)
        or value["coordinator_session_sha256"] != sha256_bytes(session_raw)
        or value["first_current_context_sha256"] != sha256_bytes(canonical_bytes(context))
        or canonical_bytes(value["first_coordinator_head"]) != session_raw
        or value["first_coordinator_head_sha256"] != sha256_bytes(session_raw)
        or value["attended_opening"] is not True
        or value["no_replay"] is not True
        or value["command_execution_backend"] is not False
        or context["campaign_id"] != campaign_id
        or context["session_id"] != session_id
        or context["phase"] != "healthy-normal"
        or context["expired"] is not False
        or context["session_expired"] is not False
        or recorded < allocation["opened_at"]
        or current != recorded
        or current >= allocation["campaign_expires_at"]
        or current >= allocation["session_expires_at"]
        or context_campaign_expiry != allocation["campaign_expires_at"]
        or context_session_expiry != allocation["session_expires_at"]
        or type(context["current_ordinal"]) is not int
        or context["current_ordinal"] != 0
        or not _exact_equal(context_source, source)
        or context["endpoint"] is not None
        or context["predecessor_sha256"] != sha256_bytes(session_raw)
        or context["terminal"] is not None
        or context["f1_intent"] is not False
        or context["approval_consumed"] is not False
        or context["partition_transfer"] is not False
        or context["no_replay"] is not True
        or context["pending_intent_issued_at"] is not None
    ):
        raise RecoveryV1Error("accounting opening semantics differ")
    return dict(value)


def validate_lease(
    lease: Any,
    lease_raw: bytes,
    accounting: Mapping[str, Any],
    accounting_raw: bytes,
    session: Mapping[str, Any],
    session_raw: bytes,
) -> dict[str, Any]:
    _exact_keys(lease, LEASE_KEYS, "read lease")
    if canonical_bytes(lease) != lease_raw:
        raise RecoveryV1Error("lease raw bytes differ")
    context = lease["coordinator_context"]
    _exact_keys(context, CONTEXT_KEYS, "lease context")
    issued = _require_int(lease["issued_at"], "lease issued_at")
    _require_int(context["current_time"], "lease context time")
    _require_int(context["campaign_expires_at"], "lease context campaign expiry")
    _require_int(context["session_expires_at"], "lease context session expiry")
    reservation = _require_int(lease["reservation_bytes"], "lease reservation")
    lease_source = validate_source_identity(lease["source_identity"], "lease source")
    context_source = validate_source_identity(
        context["source_identity"], "lease context source"
    )
    validate_zero_control_counters(context["child_counters"], "lease child controls")
    validate_zero_control_counters(
        context["campaign_counters"], "lease campaign controls"
    )
    validate_read_counters(
        lease["previous_child_counters"], zero_read_counters(), "lease prior child"
    )
    validate_read_counters(
        lease["previous_campaign_counters"],
        zero_read_counters(),
        "lease prior campaign",
    )
    validate_read_counters(lease["child_counters"], reserved_read_counters(), "lease child")
    validate_read_counters(
        lease["campaign_counters"], reserved_read_counters(), "lease campaign"
    )
    _validate_expected_host_tool(lease["expected_host_tool"], "lease expected host tool")
    opening_context = accounting["first_current_context"]
    context_without_time = {
        key: value for key, value in context.items() if key != "current_time"
    }
    opening_without_time = {
        key: value for key, value in opening_context.items() if key != "current_time"
    }
    if (
        lease["schema"] != COORDINATOR_LEASE_SCHEMA
        or lease["kind"] != "public-health-read-lease"
        or lease["campaign_id"] != accounting["campaign_id"]
        or lease["session_id"] != accounting["session_id"]
        or lease["target"] != TARGET
        or lease["action"] != "public-health"
        or type(lease["read_ordinal"]) is not int
        or lease["read_ordinal"] != 1
        or lease["accounting_opening_sha256"] != sha256_bytes(accounting_raw)
        or lease["coordinator_context_sha256"] != sha256_bytes(canonical_bytes(context))
        or canonical_bytes(lease["coordinator_head"]) != session_raw
        or lease["coordinator_head_sha256"] != sha256_bytes(session_raw)
        or not _exact_equal(lease_source, accounting["source_identity"])
        or lease["previous_evidence_result_sha256"] != ZERO_HASH
        or lease["previous_coordinator_complete_sha256"] != ZERO_HASH
        or reservation != EVIDENCE_RESERVATION_BYTES
        or lease["attempt_consumed"] is not True
        or lease["replay_authorized"] is not False
        or lease["controls_blocked"] is not True
        or lease["terminal_blocked"] is not True
        or lease["completion_required"] is not True
        or context["campaign_id"] != accounting["campaign_id"]
        or context["session_id"] != accounting["session_id"]
        or context["phase"] != "healthy-normal"
        or context["expired"] is not False
        or context["session_expired"] is not False
        or context["current_time"] != issued
        or issued < accounting["recorded_at"]
        or not _exact_equal(context_without_time, opening_without_time)
        or type(context["current_ordinal"]) is not int
        or context["current_ordinal"] != 0
        or issued >= context["campaign_expires_at"]
        or issued >= context["session_expires_at"]
        or not _exact_equal(context_source, lease_source)
        or context["endpoint"] is not None
        or context["predecessor_sha256"] != sha256_bytes(session_raw)
        or context["terminal"] is not None
        or context["f1_intent"] is not False
        or context["approval_consumed"] is not False
        or context["partition_transfer"] is not False
        or context["no_replay"] is not True
        or context["pending_intent_issued_at"] is not None
    ):
        raise RecoveryV1Error("read lease semantics differ")
    return dict(lease)


def validate_structural_raws(raws: Mapping[str, bytes]) -> dict[str, Any]:
    if type(raws) is not dict or not set(raws) <= set(STRUCTURAL_CAPS):
        raise RecoveryV1Error("structural node names differ")
    total = 0
    receipts: dict[str, Any] = {}
    for name, payload in raws.items():
        cap = STRUCTURAL_CAPS[name]
        parse_canonical_json(payload, name, cap)
        total += len(payload)
        receipts[name] = {"size": len(payload), "sha256": sha256_bytes(payload)}
    if total > STRUCTURAL_MAX_BYTES:
        raise RecoveryV1Error("structural aggregate exceeds 48 KiB")
    if "public-health-read-complete-000001.json" in raws and len(raws) != 8:
        raise RecoveryV1Error("completed structural closure is not eight nodes")
    return {"node_count": len(raws), "actual_bytes": total, "nodes": receipts}


def _metadata(value: os.stat_result) -> tuple[int, ...]:
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


def _validate_directory_info(value: os.stat_result, label: str) -> None:
    if (
        not stat.S_ISDIR(value.st_mode)
        or stat.S_IMODE(value.st_mode) != 0o700
        or value.st_uid != os.geteuid()
        or value.st_gid != os.getegid()
    ):
        raise RecoveryV1Error(f"{label} directory identity differs")


def _open_absolute_directory(path: Path, label: str) -> int:
    path = Path(path)
    if not path.is_absolute() or any(part in ("", ".", "..") for part in path.parts[1:]):
        raise RecoveryV1Error(f"{label} path is not fixed absolute")
    descriptor = os.open(
        "/",
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_CLOEXEC
        | os.O_NOFOLLOW
        | os.O_NONBLOCK,
    )
    try:
        for component in path.parts[1:]:
            try:
                child = os.open(
                    component,
                    os.O_RDONLY
                    | os.O_DIRECTORY
                    | os.O_CLOEXEC
                    | os.O_NOFOLLOW
                    | os.O_NONBLOCK,
                    dir_fd=descriptor,
                )
            except OSError as exc:
                raise RecoveryV1Error(f"{label} path component is indirect") from exc
            os.close(descriptor)
            descriptor = child
        _validate_directory_info(os.fstat(descriptor), label)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_fixed_root(label: str) -> int:
    if label not in FIXED_ROOTS:
        raise RecoveryV1Error("root label is outside fixed closure")
    try:
        return _open_absolute_directory(FIXED_ROOTS[label], f"{label} root")
    except OSError as exc:
        raise RecoveryV1Error(f"{label} root is unavailable") from exc


def _safe_component(name: str, label: str) -> str:
    if (
        type(name) is not str
        or not name
        or name in (".", "..")
        or "/" in name
        or "\x00" in name
    ):
        raise RecoveryV1Error(f"{label} component differs")
    return name


def _open_child_directory(parent: int, name: str, label: str) -> int:
    _safe_component(name, label)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | os.O_DIRECTORY
            | os.O_CLOEXEC
            | os.O_NOFOLLOW
            | os.O_NONBLOCK,
            dir_fd=parent,
        )
    except OSError as exc:
        raise RecoveryV1Error(f"{label} directory is unavailable") from exc
    try:
        _validate_directory_info(os.fstat(descriptor), label)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_or_create_recovery_directory(leaf_fd: int) -> int:
    try:
        os.mkdir(RECOVERY_DIRECTORY, 0o700, dir_fd=leaf_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise RecoveryV1Error("recovery directory creation failed") from exc
    initial = -1
    reopened = -1
    try:
        initial = _open_child_directory(leaf_fd, RECOVERY_DIRECTORY, "recovery-v1")
        # Also closes a prior uncertain mkdir/parent-fsync cut on retry.  The
        # final-name directory is opened on both sides of that durability point.
        os.fsync(leaf_fd)
        reopened = _open_child_directory(
            leaf_fd, RECOVERY_DIRECTORY, "reopened recovery-v1"
        )
        if (os.fstat(initial).st_dev, os.fstat(initial).st_ino) != (
            os.fstat(reopened).st_dev,
            os.fstat(reopened).st_ino,
        ):
            raise RecoveryV1Error("recovery directory changed across parent fsync")
        os.close(initial)
        initial = -1
        result = reopened
        reopened = -1
        return result
    except OSError as exc:
        raise RecoveryV1Error("recovery directory durability check failed") from exc
    finally:
        if initial >= 0:
            try:
                os.close(initial)
            except OSError:
                pass
        if reopened >= 0:
            try:
                os.close(reopened)
            except OSError:
                pass


def _directory_names(
    descriptor: int, label: str, maximum_entries: int
) -> tuple[str, ...]:
    limit = _require_int(maximum_entries, f"{label} maximum entries")
    before = os.fstat(descriptor)
    try:
        collected: list[str] = []
        with os.scandir(descriptor) as entries:
            for entry in entries:
                if len(collected) >= limit:
                    raise RecoveryV1Error(f"{label} exceeds bounded entry count")
                collected.append(entry.name)
        names = tuple(sorted(collected))
    except OSError as exc:
        raise RecoveryV1Error(f"{label} enumeration failed") from exc
    after = os.fstat(descriptor)
    if _metadata(before) != _metadata(after) or len(names) != len(set(names)):
        raise RecoveryV1Error(f"{label} changed or contains duplicates")
    return names


def _require_names(
    descriptor: int,
    expected: set[str],
    label: str,
) -> tuple[str, ...]:
    names = _directory_names(descriptor, label, len(expected))
    if set(names) != expected:
        raise RecoveryV1Error(f"{label} namespace differs")
    return names


def _read_regular_at(
    parent: int,
    name: str,
    label: str,
    maximum: int,
    mode: int = 0o400,
) -> bytes:
    _safe_component(name, label)
    limit = _require_int(maximum, f"{label} maximum", 1)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent,
        )
    except OSError as exc:
        raise RecoveryV1Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_IMODE(before.st_mode) != mode
            or before.st_nlink != 1
            or before.st_uid != os.geteuid()
            or before.st_gid != os.getegid()
            or before.st_size > limit
        ):
            raise RecoveryV1Error(f"{label} file identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = os.read(descriptor, min(65_536, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or os.read(descriptor, 1):
            raise RecoveryV1Error(f"{label} length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise RecoveryV1Error(f"{label} changed while read")
        return bytes(data)
    finally:
        os.close(descriptor)


def _read_optional_at(
    parent: int, name: str, label: str, maximum: int, mode: int = 0o400
) -> bytes | None:
    try:
        return _read_regular_at(parent, name, label, maximum, mode)
    except RecoveryV1Error as exc:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return None
        except OSError:
            pass
        raise exc


class _ExclusiveCoordinatorLock:
    def __init__(self, leaf_fd: int, create: bool):
        self.leaf_fd = leaf_fd
        self.create = create
        self.descriptor = -1

    def __enter__(self) -> int:
        flags = os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        created = False
        try:
            if self.create:
                try:
                    self.descriptor = os.open(
                        LOCK_NAME,
                        flags | os.O_CREAT | os.O_EXCL,
                        0o600,
                        dir_fd=self.leaf_fd,
                    )
                    created = True
                except FileExistsError:
                    self.descriptor = os.open(
                        LOCK_NAME, flags, 0o600, dir_fd=self.leaf_fd
                    )
            else:
                self.descriptor = os.open(
                    LOCK_NAME, flags, 0o600, dir_fd=self.leaf_fd
                )
            if created:
                os.fchmod(self.descriptor, 0o600)
            info = os.fstat(self.descriptor)
            if (
                not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1
                or info.st_uid != os.geteuid()
                or info.st_gid != os.getegid()
                or info.st_size != 0
            ):
                raise RecoveryV1Error("coordinator lock identity differs")
            # Always flush both the lock and its final-name parent.  This makes
            # retry after an O_EXCL-success/parent-fsync cut converge instead
            # of silently trusting an existing but not yet proven lock name.
            os.fsync(self.descriptor)
            os.fsync(self.leaf_fd)
            after = os.fstat(self.descriptor)
            named = os.stat(LOCK_NAME, dir_fd=self.leaf_fd, follow_symlinks=False)
            if (
                _metadata(info) != _metadata(after)
                or not stat.S_ISREG(named.st_mode)
                or stat.S_IMODE(named.st_mode) != 0o600
                or named.st_nlink != 1
                or named.st_uid != os.geteuid()
                or named.st_gid != os.getegid()
                or named.st_size != 0
                or (named.st_dev, named.st_ino) != (after.st_dev, after.st_ino)
            ):
                raise RecoveryV1Error("coordinator lock changed across durability check")
            fcntl.flock(
                self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB
            )
            return self.descriptor
        except BlockingIOError as exc:
            self._close()
            raise RecoveryV1Error("coordinator lock is already held") from exc
        except OSError as exc:
            self._close()
            raise RecoveryV1Error("coordinator lock durability or open failed") from exc
        except BaseException:
            self._close()
            raise

    def _close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.descriptor >= 0:
            try:
                fcntl.flock(self.descriptor, fcntl.LOCK_UN)
            finally:
                self._close()


_LIBC = ctypes.CDLL(None, use_errno=True)
_LINKAT = _LIBC.linkat
_LINKAT.argtypes = [
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
]
_LINKAT.restype = ctypes.c_int
_AT_EMPTY_PATH = 0x1000


def _link_anonymous_tmpfile(source_fd: int, parent_fd: int, name: str) -> None:
    _safe_component(name, "publication name")
    if _LINKAT(source_fd, b"", parent_fd, name.encode(), _AT_EMPTY_PATH) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), name)


PUBLISH_CAPS = MappingProxyType(
    {
        RECOVERY_CORE_NAME: RECOVERY_CORE_MAX_BYTES,
        RECOVERY_MANIFEST_NAME: RECOVERY_MANIFEST_MAX_BYTES,
    }
)


def _write_complete(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        count = os.write(descriptor, payload[offset:])
        if type(count) is not int or type(count) is bool or count <= 0:
            raise RecoveryV1Error("anonymous file write did not progress")
        offset += count
    if offset != len(payload):
        raise RecoveryV1Error("anonymous file write was incomplete")


def _existing_exact(parent: int, name: str, payload: bytes) -> bool:
    try:
        existing = _read_regular_at(
            parent, name, f"existing {name}", PUBLISH_CAPS[name], 0o400
        )
    except RecoveryV1Error:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return False
        raise
    if existing != payload:
        raise RecoveryV1Error("existing final bytes differ")
    return True


def _atomic_publish_at(parent: int, name: str, payload: bytes) -> str:
    if name not in PUBLISH_CAPS or type(payload) is not bytes or not payload:
        raise RecoveryV1Error("publication request is outside recovery bundle")
    if len(payload) > PUBLISH_CAPS[name]:
        raise RecoveryV1Error("publication payload exceeds fixed cap")
    if _existing_exact(parent, name, payload):
        os.fsync(parent)
        if not _existing_exact(parent, name, payload):
            raise RecoveryV1Error("existing final changed across directory fsync")
        return "EXACT_ALREADY_PRESENT"
    flags = os.O_WRONLY | os.O_CLOEXEC | getattr(os, "O_TMPFILE", 0)
    if not getattr(os, "O_TMPFILE", 0):
        raise RecoveryV1Error("O_TMPFILE is unavailable")
    descriptor = -1
    try:
        descriptor = os.open(".", flags, 0o400, dir_fd=parent)
        os.fchmod(descriptor, 0o400)
        _write_complete(descriptor, payload)
        os.fsync(descriptor)
        anonymous_info = os.fstat(descriptor)
        try:
            _link_anonymous_tmpfile(descriptor, parent, name)
        except OSError as exc:
            if exc.errno != errno.EEXIST or not _existing_exact(parent, name, payload):
                raise RecoveryV1Error("anonymous no-replace link failed") from exc
            os.fsync(parent)
            if not _existing_exact(parent, name, payload):
                raise RecoveryV1Error("racing exact final changed across fsync")
            return "EXACT_RACE_PRESENT"
        os.fsync(parent)
        final_fd = os.open(
            name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=parent,
        )
        try:
            final_info = os.fstat(final_fd)
            if (
                not stat.S_ISREG(final_info.st_mode)
                or stat.S_IMODE(final_info.st_mode) != 0o400
                or final_info.st_nlink != 1
                or final_info.st_uid != os.geteuid()
                or final_info.st_gid != os.getegid()
                or (final_info.st_dev, final_info.st_ino)
                != (anonymous_info.st_dev, anonymous_info.st_ino)
                or final_info.st_size != len(payload)
            ):
                raise RecoveryV1Error("linked final inode identity differs")
            data = bytearray()
            while len(data) < final_info.st_size:
                chunk = os.read(
                    final_fd, min(65_536, final_info.st_size - len(data))
                )
                if not chunk:
                    break
                data.extend(chunk)
            if (
                len(data) != final_info.st_size
                or os.read(final_fd, 1)
                or bytes(data) != payload
                or _metadata(final_info) != _metadata(os.fstat(final_fd))
            ):
                raise RecoveryV1Error("published final bytes differ on reopen")
        finally:
            os.close(final_fd)
        return "PUBLISHED"
    except OSError as exc:
        raise RecoveryV1Error("atomic anonymous publication failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_self_bytes() -> bytes:
    path = Path(__file__)
    if not path.is_absolute():
        raise RecoveryV1Error("recovery core source path is not absolute")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > RECOVERY_CORE_MAX_BYTES
        ):
            raise RecoveryV1Error("recovery core source identity differs")
        data = bytearray()
        while len(data) < before.st_size:
            chunk = os.read(descriptor, min(65_536, before.st_size - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != before.st_size or os.read(descriptor, 1):
            raise RecoveryV1Error("recovery core source length differs")
        after = os.fstat(descriptor)
        if _metadata(before) != _metadata(after):
            raise RecoveryV1Error("recovery core source changed while read")
        return bytes(data)
    finally:
        os.close(descriptor)


def _require_preopening_campaign_root(descriptor: int, label: str) -> None:
    names = set(_directory_names(descriptor, f"pre-opening {label} root", 1))
    if not names <= {"campaigns"}:
        raise RecoveryV1Error(f"pre-opening {label} root namespace differs")
    if "campaigns" in names:
        campaigns = _open_child_directory(
            descriptor, "campaigns", f"pre-opening {label} campaigns"
        )
        try:
            _require_names(campaigns, set(), f"pre-opening {label} campaigns")
        finally:
            os.close(campaigns)


def _require_lock_identity(leaf_fd: int) -> None:
    try:
        info = os.stat(LOCK_NAME, dir_fd=leaf_fd, follow_symlinks=False)
    except OSError as exc:
        raise RecoveryV1Error("existing coordinator lock is unavailable") from exc
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or info.st_uid != os.geteuid()
        or info.st_gid != os.getegid()
        or info.st_size != 0
    ):
        raise RecoveryV1Error("existing coordinator lock identity differs")


def _require_preinstall_leaf(
    leaf_fd: int,
    core: bytes,
    manifest_raw: bytes,
) -> None:
    names = set(_directory_names(leaf_fd, "preinstall read-leaf root", 2))
    if not names <= {LOCK_NAME, RECOVERY_DIRECTORY}:
        raise RecoveryV1Error("recovery install sees a campaign or foreign leaf node")
    if LOCK_NAME in names:
        _require_lock_identity(leaf_fd)
    if RECOVERY_DIRECTORY not in names:
        return
    recovery_fd = _open_child_directory(
        leaf_fd, RECOVERY_DIRECTORY, "preinstall recovery-v1"
    )
    try:
        recovery_names = set(
            _directory_names(recovery_fd, "preinstall recovery bundle", 2)
        )
        if not recovery_names <= {RECOVERY_CORE_NAME, RECOVERY_MANIFEST_NAME}:
            raise RecoveryV1Error("preinstall recovery bundle namespace differs")
        if RECOVERY_MANIFEST_NAME in recovery_names and RECOVERY_CORE_NAME not in recovery_names:
            raise RecoveryV1Error("manifest exists without recovery core")
        if RECOVERY_CORE_NAME in recovery_names:
            existing_core = _read_regular_at(
                recovery_fd,
                RECOVERY_CORE_NAME,
                "preinstall recovery core",
                RECOVERY_CORE_MAX_BYTES,
            )
            if existing_core != core:
                raise RecoveryV1Error("preinstall recovery core bytes differ")
        if RECOVERY_MANIFEST_NAME in recovery_names:
            existing_manifest = _read_regular_at(
                recovery_fd,
                RECOVERY_MANIFEST_NAME,
                "preinstall recovery manifest",
                RECOVERY_MANIFEST_MAX_BYTES,
            )
            if existing_manifest != manifest_raw:
                raise RecoveryV1Error("preinstall recovery manifest bytes differ")
            manifest = parse_canonical_json(
                existing_manifest,
                "preinstall recovery manifest",
                RECOVERY_MANIFEST_MAX_BYTES,
            )
            validate_manifest(manifest, existing_manifest, core)
    finally:
        os.close(recovery_fd)


def _require_reopened_fixed_root(label: str, held: int) -> None:
    reopened = _open_fixed_root(label)
    try:
        held_info = os.fstat(held)
        reopened_info = os.fstat(reopened)
        if (held_info.st_dev, held_info.st_ino) != (
            reopened_info.st_dev,
            reopened_info.st_ino,
        ):
            raise RecoveryV1Error(f"{label} root was replaced during install")
    finally:
        os.close(reopened)


def _require_bound_future_runner(core_bytes: bytes) -> dict[str, Any]:
    identity = validate_core_identity(core_bytes)
    binding = identity["runner_binding"]
    if (
        binding["status"] != "BOUND"
        or binding["binding_complete"] is not True
        or binding["normalized_sha256"] == ZERO_HASH
    ):
        raise RecoveryV1Error("future recovery runner remains unbound")
    return {"core_bytes": core_bytes, "core_identity": identity}


def _install_recovery_bundle_impl() -> dict[str, Any]:
    gate = _require_gate("writer")
    core = gate["core_bytes"]
    manifest_raw = canonical_bytes(build_manifest(core))
    leaf_fd = _open_fixed_root("leaf")
    base_fd = -1
    evidence_fd = -1
    try:
        base_fd = _open_fixed_root("base")
        evidence_fd = _open_fixed_root("evidence")
        # Reject every known invalid pre-opening state before creating a lock,
        # directory, or final file.  Same-UID concurrent writers remain outside
        # the threat model, so the exact checks are repeated once the lock is held.
        _require_preinstall_leaf(leaf_fd, core, manifest_raw)
        _require_preopening_campaign_root(base_fd, "base")
        _require_preopening_campaign_root(evidence_fd, "evidence")
        with _ExclusiveCoordinatorLock(leaf_fd, create=True):
            _require_preinstall_leaf(leaf_fd, core, manifest_raw)
            _require_preopening_campaign_root(base_fd, "base")
            _require_preopening_campaign_root(evidence_fd, "evidence")
            recovery_fd = _open_or_create_recovery_directory(leaf_fd)
            try:
                names = set(_directory_names(recovery_fd, "recovery bundle", 2))
                if not names <= {RECOVERY_CORE_NAME, RECOVERY_MANIFEST_NAME}:
                    raise RecoveryV1Error("recovery bundle namespace differs")
                if RECOVERY_MANIFEST_NAME in names and RECOVERY_CORE_NAME not in names:
                    raise RecoveryV1Error("manifest exists without recovery core")
                core_status = _atomic_publish_at(recovery_fd, RECOVERY_CORE_NAME, core)
                manifest_status = _atomic_publish_at(
                    recovery_fd, RECOVERY_MANIFEST_NAME, manifest_raw
                )
                _require_names(
                    recovery_fd,
                    {RECOVERY_CORE_NAME, RECOVERY_MANIFEST_NAME},
                    "completed recovery bundle",
                )
                check_core = _read_regular_at(
                    recovery_fd,
                    RECOVERY_CORE_NAME,
                    "recovery core",
                    RECOVERY_CORE_MAX_BYTES,
                )
                check_manifest_raw = _read_regular_at(
                    recovery_fd,
                    RECOVERY_MANIFEST_NAME,
                    "recovery manifest",
                    RECOVERY_MANIFEST_MAX_BYTES,
                )
                check_manifest = parse_canonical_json(
                    check_manifest_raw,
                    "recovery manifest",
                    RECOVERY_MANIFEST_MAX_BYTES,
                )
                validate_manifest(check_manifest, check_manifest_raw, check_core)
                _require_reopened_fixed_root("base", base_fd)
                _require_reopened_fixed_root("evidence", evidence_fd)
                reopened_leaf = _open_fixed_root("leaf")
                try:
                    if (
                        os.fstat(reopened_leaf).st_dev,
                        os.fstat(reopened_leaf).st_ino,
                    ) != (os.fstat(leaf_fd).st_dev, os.fstat(leaf_fd).st_ino):
                        raise RecoveryV1Error("leaf root was replaced during install")
                    reopened_recovery = _open_child_directory(
                        reopened_leaf, RECOVERY_DIRECTORY, "reopened recovery-v1"
                    )
                    try:
                        if (
                            os.fstat(reopened_recovery).st_dev,
                            os.fstat(reopened_recovery).st_ino,
                        ) != (
                            os.fstat(recovery_fd).st_dev,
                            os.fstat(recovery_fd).st_ino,
                        ):
                            raise RecoveryV1Error(
                                "recovery directory was replaced during install"
                            )
                    finally:
                        os.close(reopened_recovery)
                finally:
                    os.close(reopened_leaf)
                return {
                    "status": "H0_RECOVERY_BUNDLE_MODELED",
                    "core_publication": core_status,
                    "manifest_publication": manifest_status,
                    "manifest_published_last": True,
                    "live_authority": False,
                }
            finally:
                os.close(recovery_fd)
    finally:
        if evidence_fd >= 0:
            os.close(evidence_fd)
        if base_fd >= 0:
            os.close(base_fd)
        os.close(leaf_fd)


def _model_verify_private_core_bytes(recovery_fd: int) -> bytes:
    """H0 same-module model only; not the required independent private loader."""
    _require_names(
        recovery_fd,
        {RECOVERY_CORE_NAME, RECOVERY_MANIFEST_NAME},
        "recovery bundle",
    )
    core = _read_regular_at(
        recovery_fd, RECOVERY_CORE_NAME, "recovery core", RECOVERY_CORE_MAX_BYTES
    )
    manifest_raw = _read_regular_at(
        recovery_fd,
        RECOVERY_MANIFEST_NAME,
        "recovery manifest",
        RECOVERY_MANIFEST_MAX_BYTES,
    )
    manifest = parse_canonical_json(
        manifest_raw, "recovery manifest", RECOVERY_MANIFEST_MAX_BYTES
    )
    validate_manifest(manifest, manifest_raw, core)
    _require_bound_future_runner(core)
    return core


def classify_cut(
    *,
    opening_present: bool,
    core_present: bool,
    manifest_present: bool,
    lease_present: bool,
    intent_present: bool,
    evidence_names: Sequence[str],
    result_present: bool,
    completion_present: bool,
) -> dict[str, Any]:
    flags = (
        opening_present,
        core_present,
        manifest_present,
        lease_present,
        intent_present,
        result_present,
        completion_present,
    )
    if any(type(value) is not bool for value in flags):
        raise RecoveryV1Error("cut presence flags are not strict booleans")
    if type(evidence_names) not in (list, tuple) or any(
        type(name) is not str for name in evidence_names
    ):
        raise RecoveryV1Error("cut evidence names are not a string sequence")
    names = tuple(evidence_names)
    if len(names) != len(set(names)) or not set(names) <= set(EVIDENCE_NAMES):
        raise RecoveryV1Error("cut evidence names are foreign or duplicated")
    if set(names) != set(PUBLICATION_ORDER[: len(names)]):
        raise RecoveryV1Error("cut evidence publication has a gap or reorder")
    if manifest_present and not core_present:
        raise RecoveryV1Error("manifest cannot exist without core")
    if not opening_present:
        if lease_present or intent_present or names or result_present or completion_present:
            raise RecoveryV1Error("campaign descendant exists before opening")
        partial = core_present is not manifest_present
        return {
            "status": (
                "PRE_OPENING_PARTIAL_BUNDLE_REPAIR_ONLY"
                if partial
                else "PRE_OPENING_NO_CAMPAIGN"
            ),
            "bundle_repair_eligible": partial,
            "modeled_candidate_operation": (
                "repair-exact-bundle" if partial else None
            ),
            "settlement_validated": False,
            "replay_authorized": False,
            "refund_authorized": False,
            "next_action_authorized": False,
            "zero_command_finalization_authorized": False,
            "campaign_parked": False,
        }
    if not core_present or not manifest_present:
        return {
            "status": "OPENING_WITH_INCOMPLETE_RECOVERY_BUNDLE_PARKED",
            "bundle_repair_eligible": False,
            "modeled_candidate_operation": None,
            "settlement_validated": False,
            "replay_authorized": False,
            "refund_authorized": False,
            "next_action_authorized": False,
            "zero_command_finalization_authorized": False,
            "campaign_parked": True,
        }
    if not lease_present and (intent_present or names or result_present or completion_present):
        raise RecoveryV1Error("read descendant exists without lease")
    if not intent_present and (names or result_present or completion_present):
        raise RecoveryV1Error("evidence exists without intent")
    if result_present and set(names) != set(EVIDENCE_NAMES):
        raise RecoveryV1Error("result exists without exact 19-file evidence")
    if completion_present and not result_present:
        raise RecoveryV1Error("completion exists without result")
    if not lease_present:
        status = "OPENING_NO_LEASE_NO_AUTONOMOUS_AUTHORITY"
        candidate = None
    elif not intent_present:
        status = "LEASE_WITHOUT_MIRROR_PARKED"
        candidate = "publish-exact-mirror-only"
    elif set(names) == set(RETURN_NAMES) and not result_present:
        status = "COMPLETE_RETURNS_DERIVATION_CANDIDATE_UNPROVED"
        candidate = "derive-health-and-result-from-retained-only"
    elif set(names) == set(EVIDENCE_NAMES) and not result_present:
        status = "HEALTH_PRESENT_RESULT_CANDIDATE_UNPROVED"
        candidate = "derive-result-from-retained-only"
    elif not result_present:
        status = "INCOMPLETE_RETURNS_UNCERTAIN_CONSUMED_PARKED"
        candidate = None
    elif result_present and not completion_present:
        status = "RESULT_PRESENT_COMPLETION_CANDIDATE_UNPROVED"
        candidate = "publish-exact-parked-completion"
    else:
        status = "COMPLETION_PRESENT_REEMIT_CANDIDATE_UNPROVED"
        candidate = "reemit-only-after-full-revalidation"
    return {
        "status": status,
        "bundle_repair_eligible": False,
        "modeled_candidate_operation": candidate,
        "settlement_validated": False,
        "replay_authorized": False,
        "refund_authorized": False,
        "next_action_authorized": False,
        "zero_command_finalization_authorized": False,
        "campaign_parked": lease_present,
    }


def _read_json_at(parent: int, name: str, label: str, maximum: int) -> tuple[dict[str, Any], bytes]:
    raw = _read_regular_at(parent, name, label, maximum, 0o400)
    value = parse_canonical_json(raw, label, maximum)
    if type(value) is not dict:
        raise RecoveryV1Error(f"{label} is not an object")
    return value, raw


def _open_evidence_session(
    evidence_root: int, campaign_id: str, session_id: str
) -> tuple[int, list[int]]:
    held: list[int] = []
    try:
        campaigns = _open_child_directory(
            evidence_root, "campaigns", "evidence campaigns"
        )
        held.append(campaigns)
        campaign_name = "campaign-" + hashlib.sha256(campaign_id.encode()).hexdigest()
        _require_names(campaigns, {campaign_name}, "evidence campaigns")
        campaign = _open_child_directory(
            campaigns, campaign_name, "evidence campaign"
        )
        held.append(campaign)
        _require_names(campaign, {"sessions"}, "evidence campaign")
        sessions = _open_child_directory(campaign, "sessions", "evidence sessions")
        held.append(sessions)
        session_name = "session-" + hashlib.sha256(session_id.encode()).hexdigest()
        _require_names(sessions, {session_name}, "evidence sessions")
        session = _open_child_directory(sessions, session_name, "evidence session")
        held.append(session)
        return session, held
    except BaseException:
        for descriptor in reversed(held):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise


def _read_evidence_directory(session_fd: int) -> tuple[dict[str, bytes], tuple[str, ...]]:
    names = set(_directory_names(session_fd, "evidence session", 4))
    allowed_session = {
        "accounting-opening.json",
        "read-intent-000001.json",
        "read-000001",
        "read-result-000001.json",
    }
    if not names <= allowed_session:
        raise RecoveryV1Error("evidence session namespace contains an extra node")
    if "read-result-000001.json" in names and "read-000001" not in names:
        raise RecoveryV1Error("evidence result exists without read directory")
    if "read-000001" not in names:
        return {}, ()
    read_fd = _open_child_directory(session_fd, "read-000001", "evidence read")
    try:
        read_names = _directory_names(read_fd, "evidence read", len(EVIDENCE_NAMES))
        if not set(read_names) <= set(EVIDENCE_NAMES):
            raise RecoveryV1Error("evidence read namespace contains an extra file")
        if set(read_names) != set(PUBLICATION_ORDER[: len(read_names)]):
            raise RecoveryV1Error("evidence read namespace has a gap")
        payloads: dict[str, bytes] = {}
        for name in read_names:
            if name.endswith(".bin"):
                maximum = 65_536
            elif name.endswith(".receipt.json"):
                maximum = 8 * 1024
            elif name == "health.json":
                maximum = 64 * 1024
            else:
                raise RecoveryV1Error("evidence read filename differs")
            payload = _read_regular_at(read_fd, name, name, maximum, 0o400)
            if name.endswith(".receipt.json") or name == "health.json":
                parse_canonical_json(payload, name, maximum)
            payloads[name] = payload
        for ordinal in range(1, 7):
            stdout = payloads.get(f"cmd-{ordinal:02d}.stdout.bin")
            stderr = payloads.get(f"cmd-{ordinal:02d}.stderr.bin")
            if stdout is not None and stderr is not None and len(stdout) + len(stderr) > 65_536:
                raise RecoveryV1Error("partial raw pair exceeds 64 KiB")
        return payloads, tuple(PUBLICATION_ORDER[: len(read_names)])
    finally:
        os.close(read_fd)


def _scan_fixed_state_impl() -> dict[str, Any]:
    gate = _require_gate("scanner")
    leaf_fd = _open_fixed_root("leaf")
    base_fd = -1
    evidence_fd = -1
    held: list[int] = []
    try:
        with _ExclusiveCoordinatorLock(leaf_fd, create=False):
            leaf_names = set(_directory_names(leaf_fd, "read-leaf root", 4))
            leaf_allowed = {
                LOCK_NAME,
                RECOVERY_DIRECTORY,
                "public-health-read-lease-000001.json",
                "public-health-read-complete-000001.json",
            }
            if not leaf_names <= leaf_allowed or LOCK_NAME not in leaf_names:
                raise RecoveryV1Error("read-leaf root namespace differs")

            core_present = False
            manifest_present = False
            core_bytes: bytes | None = None
            if RECOVERY_DIRECTORY in leaf_names:
                recovery_fd = _open_child_directory(
                    leaf_fd, RECOVERY_DIRECTORY, "recovery-v1"
                )
                try:
                    recovery_names = set(
                        _directory_names(recovery_fd, "recovery bundle", 2)
                    )
                    if not recovery_names <= {
                        RECOVERY_CORE_NAME,
                        RECOVERY_MANIFEST_NAME,
                    }:
                        raise RecoveryV1Error("recovery bundle namespace differs")
                    core_present = RECOVERY_CORE_NAME in recovery_names
                    manifest_present = RECOVERY_MANIFEST_NAME in recovery_names
                    if manifest_present and not core_present:
                        raise RecoveryV1Error("manifest exists without core")
                    if core_present:
                        core_bytes = _read_regular_at(
                            recovery_fd,
                            RECOVERY_CORE_NAME,
                            "recovery core",
                            RECOVERY_CORE_MAX_BYTES,
                        )
                        if core_bytes != gate["core_bytes"]:
                            raise RecoveryV1Error(
                                "executing recovery core differs from retained copy"
                            )
                    if manifest_present:
                        _model_verify_private_core_bytes(recovery_fd)
                finally:
                    os.close(recovery_fd)

            base_fd = _open_fixed_root("base")
            base_names = set(_directory_names(base_fd, "base root", 2))
            if not base_names <= {"active-campaign.json", "campaigns"}:
                raise RecoveryV1Error("base root namespace differs")
            opening_present = "active-campaign.json" in base_names
            lease_present = "public-health-read-lease-000001.json" in leaf_names
            completion_present = (
                "public-health-read-complete-000001.json" in leaf_names
            )
            if not opening_present:
                if lease_present or completion_present:
                    raise RecoveryV1Error("leaf descendant exists before base opening")
                if "campaigns" in base_names:
                    empty_campaigns = _open_child_directory(
                        base_fd, "campaigns", "pre-opening base campaigns"
                    )
                    try:
                        _require_names(
                            empty_campaigns, set(), "pre-opening base campaigns"
                        )
                    finally:
                        os.close(empty_campaigns)
                evidence_fd = _open_fixed_root("evidence")
                evidence_names = set(
                    _directory_names(evidence_fd, "pre-opening evidence root", 1)
                )
                if not evidence_names <= {"campaigns"}:
                    raise RecoveryV1Error("pre-opening evidence root differs")
                if "campaigns" in evidence_names:
                    empty_evidence = _open_child_directory(
                        evidence_fd, "campaigns", "pre-opening evidence campaigns"
                    )
                    try:
                        _require_names(
                            empty_evidence,
                            set(),
                            "pre-opening evidence campaigns",
                        )
                    finally:
                        os.close(empty_evidence)
                return {
                    "schema": PLAN_SCHEMA,
                    "target": TARGET,
                    "cut": classify_cut(
                        opening_present=False,
                        core_present=core_present,
                        manifest_present=manifest_present,
                        lease_present=False,
                        intent_present=False,
                        evidence_names=(),
                        result_present=False,
                        completion_present=False,
                    ),
                    "structural": {"node_count": 0, "actual_bytes": 0},
                    "manifest_verified": manifest_present,
                    "device_commands": 0,
                    "live_authority": False,
                }

            if base_names != {"active-campaign.json", "campaigns"}:
                raise RecoveryV1Error("base opening lacks campaigns directory")
            guard, guard_raw = _read_json_at(
                base_fd,
                "active-campaign.json",
                "base guard",
                STRUCTURAL_CAPS["active-campaign.json"],
            )
            campaign_id = _require_id(guard.get("campaign_id"), "guard campaign id")
            session_id = _require_id(guard.get("session_id"), "guard session id")
            campaigns_fd = _open_child_directory(base_fd, "campaigns", "base campaigns")
            held.append(campaigns_fd)
            _require_names(campaigns_fd, {campaign_id}, "base campaigns")
            campaign_fd = _open_child_directory(
                campaigns_fd, campaign_id, "base campaign"
            )
            held.append(campaign_fd)
            _require_names(campaign_fd, {"session"}, "base campaign")
            base_session_fd = _open_child_directory(
                campaign_fd, "session", "base session"
            )
            held.append(base_session_fd)
            _require_names(
                base_session_fd,
                {"opening.json", "session-opening.json"},
                "base initial session",
            )
            opening, opening_raw = _read_json_at(
                base_session_fd,
                "opening.json",
                "base opening",
                STRUCTURAL_CAPS["opening.json"],
            )
            session, session_raw = _read_json_at(
                base_session_fd,
                "session-opening.json",
                "base session opening",
                STRUCTURAL_CAPS["session-opening.json"],
            )
            allocation = validate_base_allocation(
                guard, guard_raw, opening, opening_raw, session, session_raw
            )

            evidence_fd = _open_fixed_root("evidence")
            evidence_root_names = set(
                _directory_names(evidence_fd, "evidence root", 1)
            )
            if evidence_root_names != {"campaigns"}:
                raise RecoveryV1Error("evidence root namespace differs")
            evidence_session_fd, evidence_held = _open_evidence_session(
                evidence_fd, campaign_id, session_id
            )
            held.extend(evidence_held)
            evidence_session_names = set(
                _directory_names(evidence_session_fd, "evidence session", 4)
            )
            accounting_present = "accounting-opening.json" in evidence_session_names
            intent_present = "read-intent-000001.json" in evidence_session_names
            read_directory_present = "read-000001" in evidence_session_names
            result_present = "read-result-000001.json" in evidence_session_names
            if lease_present and not accounting_present:
                raise RecoveryV1Error("lease exists without accounting opening")
            if intent_present and not lease_present:
                raise RecoveryV1Error("intent exists without leaf lease")
            if read_directory_present and not intent_present:
                raise RecoveryV1Error("read directory exists before durable intent")

            structural_raws: dict[str, bytes] = {
                "active-campaign.json": guard_raw,
                "opening.json": opening_raw,
                "session-opening.json": session_raw,
            }
            accounting: dict[str, Any] | None = None
            accounting_raw: bytes | None = None
            if accounting_present:
                accounting, accounting_raw = _read_json_at(
                    evidence_session_fd,
                    "accounting-opening.json",
                    "accounting opening",
                    STRUCTURAL_CAPS["accounting-opening.json"],
                )
                validate_accounting_opening(
                    accounting,
                    accounting_raw,
                    allocation,
                    guard_raw,
                    opening_raw,
                    session_raw,
                )
                structural_raws["accounting-opening.json"] = accounting_raw

            lease: dict[str, Any] | None = None
            lease_raw: bytes | None = None
            if lease_present:
                if accounting is None or accounting_raw is None:
                    raise RecoveryV1Error("lease lacks validated accounting opening")
                lease, lease_raw = _read_json_at(
                    leaf_fd,
                    "public-health-read-lease-000001.json",
                    "read lease",
                    STRUCTURAL_CAPS["public-health-read-lease-000001.json"],
                )
                validate_lease(
                    lease,
                    lease_raw,
                    accounting,
                    accounting_raw,
                    session,
                    session_raw,
                )
                structural_raws["public-health-read-lease-000001.json"] = lease_raw

            intent: dict[str, Any] | None = None
            intent_raw: bytes | None = None
            if intent_present:
                if (
                    lease is None
                    or lease_raw is None
                    or accounting is None
                    or accounting_raw is None
                ):
                    raise RecoveryV1Error("intent lacks validated lease/accounting chain")
                intent, intent_raw = _read_json_at(
                    evidence_session_fd,
                    "read-intent-000001.json",
                    "read intent",
                    STRUCTURAL_CAPS["read-intent-000001.json"],
                )
                validate_intent(
                    intent,
                    intent_raw,
                    lease,
                    lease_raw,
                    accounting,
                    accounting_raw,
                    guard_raw,
                    opening_raw,
                    session_raw,
                )
                structural_raws["read-intent-000001.json"] = intent_raw

            evidence_files, evidence_names = _read_evidence_directory(
                evidence_session_fd
            )
            if evidence_files and intent is None:
                raise RecoveryV1Error("retained returns exist without intent")
            derived_health: dict[str, Any] | None = None
            if set(RETURN_NAMES) <= set(evidence_files):
                if intent is None or intent_raw is None:
                    raise RecoveryV1Error("retained returns lack validated intent")
                derived_health = derive_health_from_retained(
                    intent, intent_raw, evidence_files
                )
                if "health.json" in evidence_files and evidence_files[
                    "health.json"
                ] != canonical_bytes(derived_health):
                    raise RecoveryV1Error("retained health differs from derivation")

            result: dict[str, Any] | None = None
            result_raw: bytes | None = None
            if result_present:
                if (
                    intent is None
                    or intent_raw is None
                    or lease_raw is None
                    or set(evidence_files) != set(EVIDENCE_NAMES)
                ):
                    raise RecoveryV1Error("result prerequisites are incomplete")
                result, result_raw = _read_json_at(
                    evidence_session_fd,
                    "read-result-000001.json",
                    "read result",
                    STRUCTURAL_CAPS["read-result-000001.json"],
                )
                validate_read_result(
                    result,
                    result_raw,
                    intent,
                    intent_raw,
                    lease,
                    lease_raw,
                    accounting,
                    accounting_raw,
                    guard_raw,
                    opening_raw,
                    session_raw,
                    evidence_files,
                )
                structural_raws["read-result-000001.json"] = result_raw

            if completion_present:
                if result is None or result_raw is None:
                    raise RecoveryV1Error("completion exists without validated result")
                completion, completion_raw = _read_json_at(
                    leaf_fd,
                    "public-health-read-complete-000001.json",
                    "parked completion",
                    STRUCTURAL_CAPS[
                        "public-health-read-complete-000001.json"
                    ],
                )
                validate_parked_completion(
                    completion, completion_raw, result, result_raw
                )
                structural_raws[
                    "public-health-read-complete-000001.json"
                ] = completion_raw

            structural = validate_structural_raws(structural_raws)
            cut = classify_cut(
                opening_present=True,
                core_present=core_present,
                manifest_present=manifest_present,
                lease_present=lease_present,
                intent_present=intent_present,
                evidence_names=evidence_names,
                result_present=result_present,
                completion_present=completion_present,
            )
            return {
                "schema": PLAN_SCHEMA,
                "target": TARGET,
                "campaign_id_sha256": sha256_bytes(campaign_id.encode()),
                "session_id_sha256": sha256_bytes(session_id.encode()),
                "source_identity": allocation["source_identity"],
                "cut": cut,
                "structural": structural,
                "evidence_file_count": len(evidence_files),
                "evidence_bytes": sum(len(value) for value in evidence_files.values()),
                "derived_health_validated": derived_health is not None,
                "result_validated": result is not None,
                "completion_validated": completion_present,
                "manifest_verified": manifest_present,
                "device_commands": 0,
                "live_authority": False,
            }
    finally:
        for descriptor in reversed(held):
            try:
                os.close(descriptor)
            except OSError:
                pass
        if evidence_fd >= 0:
            os.close(evidence_fd)
        if base_fd >= 0:
            os.close(base_fd)
        os.close(leaf_fd)


def _require_gate(kind: str) -> dict[str, Any]:
    common = (
        RECOVERY_V1_QUALIFIED is True
        and RECOVERY_CONTRACT_ACTIVE is True
        and RECOVERY_MANIFEST_ACTIVE is True
        and LIVE_AUTHORITY is False
    )
    selected = {
        "scanner": RECOVERY_SCANNER_ACTIVE,
        "writer": RECOVERY_WRITER_ACTIVE,
        "finalizer": RECOVERY_FINALIZER_ACTIVE,
        "reemit": RECOVERY_REEMIT_ACTIVE,
    }
    if kind not in selected or not common or selected[kind] is not True:
        raise RecoveryV1Error(f"{kind} entrypoint is inactive")
    gate = _require_bound_future_runner(_read_self_bytes())
    if not _exact_equal(
        gate["core_identity"]["runner_binding"],
        _plain(FUTURE_RUNNER_BINDING),
    ):
        raise RecoveryV1Error("executing core and runner binding differ")
    return gate


def scan_fixed_state() -> dict[str, Any]:
    return _scan_fixed_state_impl()


def install_recovery_bundle() -> dict[str, Any]:
    return _install_recovery_bundle_impl()


def finalize_zero_command() -> None:
    _require_gate("finalizer")
    if SELF_CONTAINED_FINALIZER_IMPLEMENTED is not True:
        raise RecoveryV1Error("zero-command finalizer is not implemented")
    raise RecoveryV1Error("zero-command finalizer has no implementation")


def reemit_terminal() -> None:
    _require_gate("reemit")
    if SELF_CONTAINED_FINALIZER_IMPLEMENTED is not True:
        raise RecoveryV1Error("terminal reemit is not implemented")
    raise RecoveryV1Error("terminal reemit has no implementation")


def normalized_self_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise RecoveryV1Error("self normalization requires bytes")
    normalized = payload
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        normalized,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_RECOVERY_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_RECOVERY_NORMALIZED_SHA256 = "<REVIEWED_RECOVERY_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    normalized, runner_count = re.subn(
        rb"^FUTURE_RUNNER_BINDING_JSON = b'[^\r\n]*\\n'$",
        b"FUTURE_RUNNER_BINDING_JSON = b'<REVIEWED_FUTURE_RUNNER_BINDING>\\\\n'",
        normalized,
        flags=re.MULTILINE,
    )
    if (status_count, anchor_count, runner_count) != (1, 1, 1):
        raise RecoveryV1Error("identity/runner normalization is ambiguous")
    for name in (
        "RECOVERY_V1_QUALIFIED",
        "RECOVERY_SCANNER_ACTIVE",
        "RECOVERY_WRITER_ACTIVE",
        "RECOVERY_FINALIZER_ACTIVE",
        "RECOVERY_REEMIT_ACTIVE",
        "RECOVERY_MANIFEST_ACTIVE",
        "RECOVERY_CONTRACT_ACTIVE",
        "LIVE_AUTHORITY",
    ):
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode(),
            f"{name} = <REVIEWED_BOOLEAN>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RecoveryV1Error("activation normalization is ambiguous")
    return sha256_bytes(normalized)


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "target": TARGET,
        "recovery_v1_qualified": RECOVERY_V1_QUALIFIED,
        "scanner_active": RECOVERY_SCANNER_ACTIVE,
        "writer_active": RECOVERY_WRITER_ACTIVE,
        "finalizer_active": RECOVERY_FINALIZER_ACTIVE,
        "reemit_active": RECOVERY_REEMIT_ACTIVE,
        "manifest_active": RECOVERY_MANIFEST_ACTIVE,
        "contract_active": RECOVERY_CONTRACT_ACTIVE,
        "live_authority": LIVE_AUTHORITY,
        "self_contained_finalizer_implemented": SELF_CONTAINED_FINALIZER_IMPLEMENTED,
        "permanent_h0_only": PERMANENT_H0_ONLY,
        "cli": ["--render-plan"],
        "self": {
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_self_sha256(source),
        },
        "oracle_hashes_embedded_not_reopened": _plain(ORACLE_IDENTITIES),
        "fixed_roots": {key: str(value) for key, value in FIXED_ROOTS.items()},
        "recovery_namespace": {
            "lock": {"name": LOCK_NAME, "mode": "0600"},
            "directory": RECOVERY_DIRECTORY,
            "core": {"name": RECOVERY_CORE_NAME, "max_bytes": RECOVERY_CORE_MAX_BYTES},
            "manifest": {
                "name": RECOVERY_MANIFEST_NAME,
                "max_bytes": RECOVERY_MANIFEST_MAX_BYTES,
                "published_last": True,
            },
            "bundle_max_bytes": RECOVERY_BUNDLE_MAX_BYTES,
        },
        "completed_closure": {
            "max_bytes": COMPLETED_TOTAL_MAX_BYTES,
            "file_count": COMPLETED_TOTAL_FILE_COUNT,
            "recovery_bundle_max_bytes": RECOVERY_BUNDLE_MAX_BYTES,
            "opening_max_bytes": RECOVERY_OPENING_MAX_BYTES,
            "campaign_binding_max_bytes": CAMPAIGN_BINDING_MAX_BYTES,
            "structural_max_bytes": STRUCTURAL_MAX_BYTES,
            "evidence_reservation_bytes": EVIDENCE_RESERVATION_BYTES,
        },
        "manifest_model": build_manifest(source),
        "private_loader_requirement": (
            "open-nofollow-verify-manifest-then-compile-bytes; "
            "direct-path-exec-is-not-provenance"
        ),
        "same_module_private_verifier_authoritative": False,
        "ancestor_consistency_boundary": {
            "all_absolute_components_opened_nofollow": True,
            "managed_roots_and_descendants_require_current_uid_gid_mode_0700": True,
            "host_ancestors_above_managed_roots_require_nofollow_but_not_mode_0700": True,
            "all_three_fixed_roots_and_recovery_directory_reopened_after_install": True,
            "same_uid_concurrent_replacement_closed": False,
        },
        "implemented_subset": [
            "self-contained-retained-return-parser",
            "manifest-model",
            "three-root-held-dirfd-legacy-journal-scanner-model",
            "anonymous-no-replace-store-primitive",
            "presence-only-cut-classifier",
        ],
        "unresolved_gates": [
            "future-runner-normalized-identity",
            "independent-private-loader-and-trusted-runner-cross-check",
            "private-manifest-install-activation",
            "attended-opening-v1-and-campaign-binding-schemas",
            "scanner-grammar-rotation-for-opening-v1-and-campaign-binding",
            "scanner-activation",
            "zero-command-finalizer-implementation",
            "terminal-reemit-implementation",
            "contract-activation",
            "combined-independent-review",
        ],
        "device_commands": [],
        "device_effects": [],
        "root_commands": [],
        "control_actions": [],
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
        parser.error("only --render-plan exists in recovery-v1 H0")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
