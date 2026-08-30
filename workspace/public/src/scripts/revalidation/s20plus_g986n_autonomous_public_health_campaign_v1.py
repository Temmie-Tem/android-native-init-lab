#!/usr/bin/env python3
"""Inactive S20+ attended-opening and ordinal-1 public-health campaign.

This file is the self-contained Phase-A artifact model for one future
exact-target opening followed by one fixed six-command public-health read.  It
deliberately provides neither a connected implementation nor the required
unforgeable same-process opening-to-read handoff while the ADB server,
USB-generation, trusted-clock, cross-code coordination, recovery grammar,
contract, and mechanical gates remain false.

The public CLI is render-only.  In particular, the model functions below are
not authority: they construct and validate canonical bytes for hostile H0
fixtures, while :func:`attended_open_and_read` checks every operational gate
before it can inspect a path, clock, process, socket, USB node, or device.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence


STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_CAMPAIGN_V1_MODEL_PASS_GO_NOT_ACTIVE"
EXPECTED_SELF_NORMALIZED_SHA256 = "be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773"

# These are operational gates, not descriptive capability claims.  Phase A
# intentionally leaves every one false.  A future activation is a separate,
# combined exact-byte review and contract transition.
CAMPAIGN_V1_QUALIFIED = False
OPENING_ACTIVE = False
READ_PRODUCER_ACTIVE = False
RECOVERY_BUNDLE_BOUND = False
RECOVERY_SCANNER_ROTATED = False
RECOVERY_FINALIZER_ROTATED = False
ADB_CLIENT_EXEC_ACTIVE = False
EXECUTOR_IMPLEMENTED = False
SAME_PROCESS_HANDOFF_IMPLEMENTED = False
ADB_SERVER_PROVENANCE_PROVEN = False
USB_GENERATION_PROVEN = False
TRUSTED_CLOCK_PROVEN = False
TARGET_COORDINATION_ACTIVE = False
CROSS_CODE_COORDINATION_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

LIVE_CAPABLE_DESIGN = False
PHASE_A_MODEL_ONLY = True
OPENING_RAW_DERIVATION_MODEL_IMPLEMENTED = True

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)

PLAN_SCHEMA = "s20plus_g986n_autonomous_public_health_campaign_v1_plan"
OPENING_INTENT_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_attended_opening_intent_v1"
)
OPENING_COMMAND_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_opening_command_evidence_v1"
)
OPENING_RESULT_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_attended_opening_result_v1"
)
CAMPAIGN_BINDING_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_campaign_binding_v1"
)
CLOCK_BINDING_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_host_clock_binding_v1"
)
CLOCK_SAMPLE_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_host_clock_sample_v1"
)
ADB_SERVER_RECEIPT_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_adb_server_receipt_v1"
)
USB_GENERATION_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_usb_generation_v1"
)
HEALTH_SCHEMA = "s20plus_g986n_d0_inventory_result_v1"
HEALTH_VERSION = "s20plus-g986n-d0-inventory-v1"
HEALTH_VERDICT = "PASS_S20PLUS_G986N_D0_ONBOARDING_READ_ONLY"

BASE_SCHEMA = "s20plus_g986n_autonomous_research_coordinator_h0_v1"
ACCOUNTING_OPENING_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_accounting_opening_v1"
)
READ_INTENT_SCHEMA = "s20plus_g986n_autonomous_public_health_read_intent_v1"
READ_COMMAND_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_command_evidence_v1"
)
READ_RESULT_SCHEMA = "s20plus_g986n_autonomous_public_health_read_result_v1"
COORDINATOR_LEASE_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_read_lease_v1"
)
COORDINATOR_COMPLETE_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_read_complete_v1"
)

POLICY_BINDING_SHA256 = (
    "0299b3a3ddbd0e496f46092b0f547ce24064e66636b90274a574d86007b9be82"
)
BASE_COORDINATOR_NORMALIZED_SHA256 = (
    "8d28f370f16d1f0d86eaa456fae09c01160d9fd8445529184643223934f4aea1"
)

ADB_PATH = "/usr/lib/android-sdk/platform-tools/adb"
ADB_SIZE = 716_968
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
ADB_SERVER_SOCKET = "tcp:127.0.0.1:5037"
EXPECTED_LOADER_NAME = (
    "s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py"
)
EXPECTED_LOADER_SIZE = 35_315
EXPECTED_LOADER_SHA256 = (
    "a210944447dc33b7593b42ba5c46cde9561c9449e8981523b468a4121c4284cc"
)
EXPECTED_LOADER_NORMALIZED_SHA256 = (
    "8df4dc534a1d4e9ac1a73867151e4bfcf2450a52283a281c7091d9c47e1e09cc"
)
EXPECTED_CORE_NAME = "recovery-core.py"
EXPECTED_CORE_SIZE = 162_875
EXPECTED_CORE_SHA256 = (
    "94f6022aebcdc63bcad08757f493349d2e4b198610a367e72181a65694321f0b"
)
EXPECTED_CORE_NORMALIZED_SHA256 = (
    "38cb154e526e8a1a3ad38f8c857f03668f92fedced786745f5e8e85d91e21dac"
)
EXPECTED_MANIFEST_NAME = "manifest.json"
EXPECTED_MANIFEST_SIZE = 7_669
EXPECTED_MANIFEST_SHA256 = (
    "51931dd9a084e1c7ae8d674681d34be7bd2f50b32d8c0b84b2842d51749df593"
)

ZERO_HASH = "0" * 64
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")
ID_RE = re.compile(r"[0-9a-f]{32}\Z")
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
DEVPATH_RE = re.compile(r"usb:[0-9]+-[0-9]+(?:\.[0-9]+)*\Z")
SAFE_VALUE_RE = re.compile(r"[^\x00\r\n]{0,4096}\Z")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
SHELL_ID_RE = re.compile(
    r"uid=2000\(shell\) gid=2000\(shell\)(?: [^\x00\r\n]+)?\Z"
)

FIXED_BASE_ROOT = (
    "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
    "s20plus-g986n-autonomous-research"
)
FIXED_EVIDENCE_ROOT = (
    "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
    "s20plus-g986n-autonomous-public-health-evidence"
)
FIXED_LEAF_ROOT = (
    "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
    "s20plus-g986n-autonomous-public-health-read-leaf"
)
SHARED_ACTIVE_ACTION_PATH = (
    "/home/temmie/dev/android-native-init-lab/workspace/private/runs/"
    "s20plus-g986n-routine-actions/active-action.json"
)

RECOVERY_CORE_MAX_BYTES = 256 * 1024
RECOVERY_MANIFEST_MAX_BYTES = 32 * 1024
RECOVERY_BUNDLE_MAX_BYTES = 288 * 1024
OPENING_INTENT_MAX_BYTES = 16 * 1024
OPENING_RESULT_MAX_BYTES = 16 * 1024
OPENING_RECEIPT_CHAIN_MAX_SEC = 5 * 60
OPENING_RAW_PAIR_MAX_BYTES = 64 * 1024
OPENING_RECEIPT_MAX_BYTES = 8 * 1024
OPENING_HEALTH_MAX_BYTES = 64 * 1024
OPENING_EVIDENCE_PROOF_MAX_BYTES = (
    6 * OPENING_RAW_PAIR_MAX_BYTES
    + 6 * OPENING_RECEIPT_MAX_BYTES
    + OPENING_HEALTH_MAX_BYTES
)
OPENING_EVIDENCE_RESERVATION_BYTES = 512 * 1024
OPENING_DIRECTORY_MAX_BYTES = 544 * 1024
CAMPAIGN_BINDING_MAX_BYTES = 16 * 1024
STRUCTURAL_MAX_BYTES = 48 * 1024
READ_EVIDENCE_PROOF_MAX_BYTES = 507_904
READ_EVIDENCE_RESERVATION_BYTES = 512 * 1024
COMPLETED_TOTAL_MAX_BYTES = 1_441_792
COMPLETED_TOTAL_FILE_COUNT = 52
OPENING_DIRECTORY_FILE_COUNT = 21

if (
    OPENING_EVIDENCE_PROOF_MAX_BYTES != 507_904
    or OPENING_EVIDENCE_PROOF_MAX_BYTES >= OPENING_EVIDENCE_RESERVATION_BYTES
    or OPENING_INTENT_MAX_BYTES
    + OPENING_RESULT_MAX_BYTES
    + OPENING_EVIDENCE_RESERVATION_BYTES
    != OPENING_DIRECTORY_MAX_BYTES
    or RECOVERY_BUNDLE_MAX_BYTES
    + OPENING_DIRECTORY_MAX_BYTES
    + CAMPAIGN_BINDING_MAX_BYTES
    + STRUCTURAL_MAX_BYTES
    + READ_EVIDENCE_RESERVATION_BYTES
    != COMPLETED_TOTAL_MAX_BYTES
):
    raise RuntimeError("campaign-v1 byte accounting differs")

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
    {"ordinal": 1, "argv": ["ADB", "version"], "timeout_sec": 10, "max_bytes": 65_536},
    {"ordinal": 2, "argv": ["ADB", "devices", "-l"], "timeout_sec": 10, "max_bytes": 65_536},
    {"ordinal": 3, "argv": ["ADB", "-s", "BOUND_SERIAL", "get-devpath"], "timeout_sec": 10, "max_bytes": 65_536},
    {
        "ordinal": 4,
        "argv": ["ADB", "-s", "BOUND_SERIAL", "exec-out", "sh", "-c", "FIXED_PUBLIC_SNAPSHOT"],
        "timeout_sec": 20,
        "max_bytes": 65_536,
    },
    {
        "ordinal": 5,
        "argv": ["ADB", "-s", "BOUND_SERIAL", "exec-out", "sh", "-c", "FIXED_PUBLIC_SNAPSHOT"],
        "timeout_sec": 20,
        "max_bytes": 65_536,
    },
    {"ordinal": 6, "argv": ["ADB", "devices", "-l"], "timeout_sec": 10, "max_bytes": 65_536},
)

OPENING_RETURN_NAMES = tuple(
    name
    for ordinal in range(1, 7)
    for name in (
        f"cmd-{ordinal:02d}.stdout.bin",
        f"cmd-{ordinal:02d}.stderr.bin",
        f"cmd-{ordinal:02d}.receipt.json",
    )
)
OPENING_EVIDENCE_NAMES = OPENING_RETURN_NAMES + ("health.json",)
READ_RETURN_NAMES = OPENING_RETURN_NAMES
READ_EVIDENCE_NAMES = READ_RETURN_NAMES + ("health.json",)

FROZEN_SOURCE_RECEIPTS = MappingProxyType(
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


class CampaignV1Error(RuntimeError):
    """Any ambiguity, drift, reorder, replay, or inactive operation stops."""


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
        raise CampaignV1Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise CampaignV1Error("digest input is not bytes")
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


def parse_canonical_json(payload: bytes, label: str, maximum: int) -> Any:
    if (
        type(payload) is not bytes
        or not payload
        or type(maximum) is not int
        or type(maximum) is bool
        or maximum < 1
        or len(payload) > maximum
    ):
        raise CampaignV1Error(f"{label} is empty, oversized, or not bytes")
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CampaignV1Error(f"{label} is not strict JSON") from exc
    if canonical_bytes(value) != payload:
        raise CampaignV1Error(f"{label} is not exact canonical JSON")
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != expected:
        raise CampaignV1Error(f"{label} keys differ")


def _require_int(value: Any, label: str, minimum: int = 0) -> int:
    if type(value) is not int or type(value) is bool or value < minimum:
        raise CampaignV1Error(f"{label} is not a strict bounded integer")
    return value


def _require_hex(value: Any, label: str) -> str:
    if type(value) is not str or HEX64_RE.fullmatch(value) is None:
        raise CampaignV1Error(f"{label} is not lowercase SHA-256")
    return value


def _require_id(value: Any, label: str) -> str:
    if type(value) is not str or ID_RE.fullmatch(value) is None:
        raise CampaignV1Error(f"{label} is not an exact identifier")
    return value


def _exact_equal(left: Any, right: Any) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def validate_source_identity(value: Any, label: str = "source identity") -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "target",
            "serial_sha256",
            "topology_sha256",
            "boot_id_sha256",
            "healthy_android",
            "foreign_guard_present",
        },
        label,
    )
    if value["target"] != dict(TARGET):
        raise CampaignV1Error(f"{label} target differs")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        _require_hex(value[key], f"{label}.{key}")
    if value["healthy_android"] is not True or value["foreign_guard_present"] is not False:
        raise CampaignV1Error(f"{label} is not exact healthy Android")
    return dict(value)


def validate_tool_identity(value: Any, label: str = "ADB client") -> dict[str, Any]:
    _exact_keys(
        value,
        {"path", "device", "inode", "mtime_ns", "size", "sha256"},
        label,
    )
    for key in ("device", "inode", "mtime_ns", "size"):
        _require_int(value[key], f"{label}.{key}")
    if (
        value["path"] != ADB_PATH
        or value["size"] != ADB_SIZE
        or value["sha256"] != ADB_SHA256
    ):
        raise CampaignV1Error(f"{label} differs from the exact held client")
    return dict(value)


def validate_clock_binding(value: Any) -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "schema",
            "host_boot_id_sha256",
            "realtime_origin_ns",
            "boottime_origin_ns",
            "monotonic_origin_ns",
            "logical_origin_sec",
            "caller_supplied_time",
        },
        "clock binding",
    )
    for key in ("host_boot_id_sha256",):
        _require_hex(value[key], f"clock.{key}")
    for key in (
        "realtime_origin_ns",
        "boottime_origin_ns",
        "monotonic_origin_ns",
        "logical_origin_sec",
    ):
        _require_int(value[key], f"clock.{key}")
    if (
        value["schema"] != CLOCK_BINDING_SCHEMA
        or value["caller_supplied_time"] is not False
        or value["logical_origin_sec"] != value["realtime_origin_ns"] // 1_000_000_000
    ):
        raise CampaignV1Error("clock binding semantics differ")
    return dict(value)


def validate_clock_sample(binding: Mapping[str, Any], value: Any) -> dict[str, Any]:
    origin = validate_clock_binding(dict(binding))
    _exact_keys(
        value,
        {
            "schema",
            "host_boot_id_sha256",
            "realtime_ns",
            "boottime_ns",
            "monotonic_ns",
            "logical_sec",
            "projection_skew_ns",
            "reversed",
        },
        "clock sample",
    )
    for key in (
        "realtime_ns",
        "boottime_ns",
        "monotonic_ns",
        "logical_sec",
        "projection_skew_ns",
    ):
        _require_int(value[key], f"clock sample.{key}")
    _require_hex(value["host_boot_id_sha256"], "clock sample boot")
    boottime_delta = value["boottime_ns"] - origin["boottime_origin_ns"]
    monotonic_delta = value["monotonic_ns"] - origin["monotonic_origin_ns"]
    projected = origin["realtime_origin_ns"] + boottime_delta
    skew = abs(value["realtime_ns"] - projected)
    if (
        value["schema"] != CLOCK_SAMPLE_SCHEMA
        or value["host_boot_id_sha256"] != origin["host_boot_id_sha256"]
        or value["reversed"] is not False
        or boottime_delta < 0
        or monotonic_delta < 0
        or boottime_delta < monotonic_delta
        or value["realtime_ns"] < origin["realtime_origin_ns"]
        or value["projection_skew_ns"] != skew
        or skew > 5_000_000_000
        or value["logical_sec"]
        != origin["logical_origin_sec"] + boottime_delta // 1_000_000_000
    ):
        raise CampaignV1Error("clock sample drifted, reversed, rebooted, or is caller-derived")
    return dict(value)


def validate_adb_server_receipt(value: Any) -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "schema",
            "socket_spec",
            "socket_inode",
            "pid",
            "pid_start_ticks",
            "uid",
            "pidfd_held",
            "continuous_identity_checks",
            "executable",
            "provenance_proven",
        },
        "ADB server receipt",
    )
    for key in ("socket_inode", "pid", "pid_start_ticks", "uid"):
        _require_int(value[key], f"ADB server.{key}", 1 if key != "uid" else 0)
    executable = validate_tool_identity(value["executable"], "ADB server executable")
    if (
        value["schema"] != ADB_SERVER_RECEIPT_SCHEMA
        or value["socket_spec"] != ADB_SERVER_SOCKET
        or value["pidfd_held"] is not True
        or value["continuous_identity_checks"] is not True
        or value["provenance_proven"] is not True
        or executable["sha256"] != ADB_SHA256
    ):
        raise CampaignV1Error("ADB server provenance is not exact and continuous")
    return dict(value)


def validate_usb_generation(value: Any, source: Mapping[str, Any]) -> dict[str, Any]:
    source = validate_source_identity(dict(source))
    _exact_keys(
        value,
        {
            "schema",
            "topology_sha256",
            "sysfs_device",
            "sysfs_inode",
            "busnum",
            "devnum",
            "usbfs_device",
            "usbfs_inode",
            "usbfs_rdev",
            "held_descriptors",
            "event_monitor_overflow",
            "generation_continuous",
        },
        "USB generation",
    )
    for key in (
        "sysfs_device",
        "sysfs_inode",
        "busnum",
        "devnum",
        "usbfs_device",
        "usbfs_inode",
        "usbfs_rdev",
    ):
        _require_int(value[key], f"USB generation.{key}")
    _require_hex(value["topology_sha256"], "USB generation topology")
    if (
        value["schema"] != USB_GENERATION_SCHEMA
        or value["topology_sha256"] != source["topology_sha256"]
        or value["held_descriptors"] is not True
        or value["event_monitor_overflow"] is not False
        or value["generation_continuous"] is not True
    ):
        raise CampaignV1Error("USB transport generation is not continuously bound")
    return dict(value)


def _validate_identity_receipt(value: Any, label: str, normalized: bool) -> dict[str, Any]:
    keys = {"name", "size", "sha256"}
    if normalized:
        keys.add("normalized_sha256")
    _exact_keys(value, keys, label)
    if type(value["name"]) is not str or not value["name"]:
        raise CampaignV1Error(f"{label} name differs")
    _require_int(value["size"], f"{label}.size", 1)
    _require_hex(value["sha256"], f"{label}.sha256")
    if normalized:
        _require_hex(value["normalized_sha256"], f"{label}.normalized_sha256")
    return dict(value)


def validate_producer_binding(value: Any) -> dict[str, Any]:
    _exact_keys(
        value,
        {"schema", "status", "normalized_sha256", "binding_complete"},
        "producer binding",
    )
    _require_hex(value["normalized_sha256"], "producer normalized identity")
    if (
        value["schema"] != "s20plus_g986n_autonomous_public_health_campaign_v1_runner_binding"
        or value["status"] != "BOUND"
        or value["binding_complete"] is not True
        or EXPECTED_SELF_NORMALIZED_SHA256 == ZERO_HASH
        or value["normalized_sha256"] != EXPECTED_SELF_NORMALIZED_SHA256
    ):
        raise CampaignV1Error("producer identity is not bound")
    return dict(value)


def validate_recovery_binding(value: Any) -> dict[str, Any]:
    _exact_keys(
        value,
        {
            "schema",
            "status",
            "binding_complete",
            "phase_b_exact_binding_required",
            "loader",
            "core",
            "manifest",
        },
        "recovery binding",
    )
    loader = _validate_identity_receipt(value["loader"], "recovery loader", True)
    core = _validate_identity_receipt(value["core"], "recovery core", True)
    manifest = _validate_identity_receipt(value["manifest"], "recovery manifest", False)
    if (
        value["schema"]
        != "s20plus_g986n_autonomous_public_health_recovery_precursors_v1"
        or value["status"] != "PHASE_A_QUALIFIED_PRECURSORS_NOT_OPERATIONAL"
        or value["binding_complete"] is not False
        or value["phase_b_exact_binding_required"] is not True
        or loader
        != {
            "name": EXPECTED_LOADER_NAME,
            "size": EXPECTED_LOADER_SIZE,
            "sha256": EXPECTED_LOADER_SHA256,
            "normalized_sha256": EXPECTED_LOADER_NORMALIZED_SHA256,
        }
        or core
        != {
            "name": EXPECTED_CORE_NAME,
            "size": EXPECTED_CORE_SIZE,
            "sha256": EXPECTED_CORE_SHA256,
            "normalized_sha256": EXPECTED_CORE_NORMALIZED_SHA256,
        }
        or manifest
        != {
            "name": EXPECTED_MANIFEST_NAME,
            "size": EXPECTED_MANIFEST_SIZE,
            "sha256": EXPECTED_MANIFEST_SHA256,
        }
        or core["size"] > RECOVERY_CORE_MAX_BYTES
        or manifest["size"] > RECOVERY_MANIFEST_MAX_BYTES
        or core["size"] + manifest["size"] > RECOVERY_BUNDLE_MAX_BYTES
        or loader["size"] > 64 * 1024
    ):
        raise CampaignV1Error("recovery bundle binding differs")
    return dict(value)


OPENING_INTENT_KEYS = {
    "schema",
    "kind",
    "created_at",
    "campaign_id",
    "session_id",
    "target",
    "policy_binding_sha256",
    "activation_binding_candidate_sha256",
    "activation_binding_verified",
    "producer_binding",
    "recovery_binding",
    "clock_binding",
    "adb_client",
    "adb_server",
    "authority",
    "expected_transcript_sha256",
    "expected_evidence_names",
    "expected_command_count",
    "source_identity",
    "attempt_consumed",
    "no_replay",
    "device_effects_authorized",
    "operational_recovery_bound",
}


def model_opening_intent(
    *,
    campaign_id: str,
    session_id: str,
    created_at: int,
    activation_binding_candidate_sha256: str,
    producer_binding: Mapping[str, Any],
    recovery_binding: Mapping[str, Any],
    clock_binding: Mapping[str, Any],
    adb_client: Mapping[str, Any],
    adb_server: Mapping[str, Any],
) -> dict[str, Any]:
    _require_id(campaign_id, "campaign id")
    _require_id(session_id, "session id")
    created = _require_int(created_at, "opening created_at")
    _require_hex(activation_binding_candidate_sha256, "activation binding candidate")
    producer = validate_producer_binding(dict(producer_binding))
    recovery = validate_recovery_binding(dict(recovery_binding))
    clock = validate_clock_binding(dict(clock_binding))
    client = validate_tool_identity(dict(adb_client))
    server = validate_adb_server_receipt(dict(adb_server))
    value = {
        "schema": OPENING_INTENT_SCHEMA,
        "kind": "attended-opening-intent",
        "created_at": created,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "policy_binding_sha256": POLICY_BINDING_SHA256,
        "activation_binding_candidate_sha256": activation_binding_candidate_sha256,
        "activation_binding_verified": False,
        "producer_binding": producer,
        "recovery_binding": recovery,
        "clock_binding": clock,
        "adb_client": client,
        "adb_server": server,
        "authority": {
            "kind": "fresh-direct-attended-post-activation-request-requirement",
            "fresh_direct_attended_post_activation_required": True,
            "requirement_verified_in_phase_a": False,
            "preactivation_consent_accepted": False,
            "standing_consent_accepted": False,
            "reusable": False,
            "operational_authority": False,
        },
        "expected_transcript_sha256": sha256_bytes(canonical_bytes(list(FIXED_TRANSCRIPT))),
        "expected_evidence_names": list(OPENING_EVIDENCE_NAMES),
        "expected_command_count": 6,
        "source_identity": None,
        "attempt_consumed": True,
        "no_replay": True,
        "device_effects_authorized": False,
        "operational_recovery_bound": False,
    }
    validate_opening_intent(value, canonical_bytes(value))
    return value


def validate_opening_intent(value: Any, raw: bytes) -> dict[str, Any]:
    _exact_keys(value, OPENING_INTENT_KEYS, "opening intent")
    if canonical_bytes(value) != raw or len(raw) > OPENING_INTENT_MAX_BYTES:
        raise CampaignV1Error("opening intent bytes differ or exceed 16 KiB")
    _require_id(value["campaign_id"], "opening campaign id")
    _require_id(value["session_id"], "opening session id")
    _require_int(value["created_at"], "opening created_at")
    _require_hex(
        value["activation_binding_candidate_sha256"],
        "opening activation binding candidate",
    )
    validate_producer_binding(value["producer_binding"])
    validate_recovery_binding(value["recovery_binding"])
    clock = validate_clock_binding(value["clock_binding"])
    validate_tool_identity(value["adb_client"])
    validate_adb_server_receipt(value["adb_server"])
    authority = value["authority"]
    _exact_keys(
        authority,
        {
            "kind",
            "fresh_direct_attended_post_activation_required",
            "requirement_verified_in_phase_a",
            "preactivation_consent_accepted",
            "standing_consent_accepted",
            "reusable",
            "operational_authority",
        },
        "opening authority",
    )
    if (
        value["schema"] != OPENING_INTENT_SCHEMA
        or value["kind"] != "attended-opening-intent"
        or value["target"] != dict(TARGET)
        or value["policy_binding_sha256"] != POLICY_BINDING_SHA256
        or value["activation_binding_verified"] is not False
        or value["created_at"] != clock["logical_origin_sec"]
        or value["expected_transcript_sha256"]
        != sha256_bytes(canonical_bytes(list(FIXED_TRANSCRIPT)))
        or value["expected_evidence_names"] != list(OPENING_EVIDENCE_NAMES)
        or type(value["expected_command_count"]) is not int
        or value["expected_command_count"] != 6
        or value["source_identity"] is not None
        or value["attempt_consumed"] is not True
        or value["no_replay"] is not True
        or value["device_effects_authorized"] is not False
        or value["operational_recovery_bound"] is not False
        or authority["kind"]
        != "fresh-direct-attended-post-activation-request-requirement"
        or authority["fresh_direct_attended_post_activation_required"] is not True
        or authority["requirement_verified_in_phase_a"] is not False
        or authority["preactivation_consent_accepted"] is not False
        or authority["standing_consent_accepted"] is not False
        or authority["reusable"] is not False
        or authority["operational_authority"] is not False
    ):
        raise CampaignV1Error("opening intent semantics differ")
    return dict(value)


def expected_actual_argvs(serial: str) -> tuple[list[str], ...]:
    if type(serial) is not str or SERIAL_RE.fullmatch(serial) is None:
        raise CampaignV1Error("selected serial grammar differs")
    return (
        [ADB_PATH, "version"],
        [ADB_PATH, "devices", "-l"],
        [ADB_PATH, "-s", serial, "get-devpath"],
        [ADB_PATH, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
        [ADB_PATH, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
        [ADB_PATH, "devices", "-l"],
    )


def parse_inventory(text: str) -> tuple[dict[str, Any], ...]:
    if type(text) is not str:
        raise CampaignV1Error("inventory is not text")
    rows: list[dict[str, Any]] = []
    serials: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2 or SERIAL_RE.fullmatch(fields[0]) is None:
            raise CampaignV1Error("inventory row is malformed")
        if fields[0] in serials:
            raise CampaignV1Error("inventory serial is duplicated")
        serials.add(fields[0])
        metadata_fields = fields[2:]
        if len(metadata_fields) != len(set(metadata_fields)):
            raise CampaignV1Error("inventory metadata token is duplicated")
        metadata = frozenset(metadata_fields)
        for prefix in ("model:", "device:", "product:", "usb:"):
            if len([item for item in metadata if item.startswith(prefix)]) > 1:
                raise CampaignV1Error("inventory metadata conflicts")
        rows.append({"serial": fields[0], "state": fields[1], "metadata": metadata})
    return tuple(rows)


def select_target(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    if type(rows) is not tuple:
        raise CampaignV1Error("inventory rows are not immutable")
    matches = [row for row in rows if "model:SM_G986N" in row["metadata"]]
    if len(matches) != 1 or matches[0]["state"] != "device":
        raise CampaignV1Error("inventory lacks one authorized exact target")
    selected = matches[0]
    exact = {
        "model:SM_G986N",
        f"device:{TARGET['device']}",
        f"product:{TARGET['product']}",
    }
    if not exact <= selected["metadata"]:
        raise CampaignV1Error("selected target metadata differs")
    usb_tokens = [item for item in selected["metadata"] if item.startswith("usb:")]
    if len(usb_tokens) != 1:
        raise CampaignV1Error("selected target lacks one USB metadata token")
    return selected


def _sanitized_inventory(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "serial_sha256": sha256_bytes(row["serial"].encode()),
            "state": row["state"],
            "metadata": sorted(row["metadata"]),
        }
        for row in rows
    )


def parse_snapshot(text: str) -> dict[str, str]:
    if (
        type(text) is not str
        or not text.endswith("\n")
        or "\r" in text
        or "\x00" in text
    ):
        raise CampaignV1Error("snapshot is not exact LF-terminated text")
    values: dict[str, str] = {}
    lines = text[:-1].split("\n")
    if len(lines) != len(PROPERTY_KEYS):
        raise CampaignV1Error("snapshot line count differs")
    for expected_key, line in zip(PROPERTY_KEYS, lines, strict=True):
        if "=" not in line:
            raise CampaignV1Error("snapshot line is malformed")
        key, value = line.split("=", 1)
        if (
            key != expected_key
            or key in values
            or SAFE_VALUE_RE.fullmatch(value) is None
        ):
            raise CampaignV1Error("snapshot field differs")
        values[key] = value
    if tuple(values) != PROPERTY_KEYS:
        raise CampaignV1Error("snapshot fields are incomplete")
    if (
        values["model"] != TARGET["model"]
        or values["device"] != TARGET["device"]
        or values["product_name"] != TARGET["product"]
        or values["build_product"] != TARGET["device"]
        or values["incremental"] != TARGET["build"]
        or values["boot_completed"] != "1"
        or values["bootanim"] != "stopped"
        or values["selinux"] != "Enforcing"
        or BOOT_ID_RE.fullmatch(values["boot_id"]) is None
        or f"/{TARGET['product']}/{TARGET['device']}:" not in values["fingerprint"]
        or not values["fingerprint"].endswith(":user/release-keys")
        or SHELL_ID_RE.fullmatch(values["shell_identity"]) is None
    ):
        raise CampaignV1Error("snapshot target, build, boot, or health differs")
    return values


def _decode_success(stdout: bytes, stderr: bytes, label: str) -> str:
    if type(stdout) is not bytes or type(stderr) is not bytes or stderr:
        raise CampaignV1Error(f"{label} streams differ")
    try:
        return stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise CampaignV1Error(f"{label} is not UTF-8") from exc


def _decode_exact_stdout(stdout: bytes, stderr: bytes, label: str) -> str:
    if type(stdout) is not bytes or type(stderr) is not bytes or stderr:
        raise CampaignV1Error(f"{label} streams differ")
    try:
        return stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise CampaignV1Error(f"{label} is not UTF-8") from exc


OPENING_RECEIPT_KEYS = {
    "schema",
    "phase",
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
    "clock_binding_sha256",
    "adb_server_sha256",
}


def model_opening_command_receipt(
    *,
    intent: Mapping[str, Any],
    ordinal: int,
    serial: str,
    predecessor_sha256: str,
    stdout: bytes,
    stderr: bytes,
    started_at: int,
    completed_at: int,
    retained_at: int,
    published_at: int,
) -> dict[str, Any]:
    intent = validate_opening_intent(dict(intent), canonical_bytes(dict(intent)))
    if type(ordinal) is not int or type(ordinal) is bool or not 1 <= ordinal <= 6:
        raise CampaignV1Error("opening command ordinal differs")
    template = FIXED_TRANSCRIPT[ordinal - 1]
    argv = expected_actual_argvs(serial)[ordinal - 1]
    value = {
        "schema": OPENING_COMMAND_SCHEMA,
        "phase": "attended-opening",
        "ordinal": ordinal,
        "predecessor_sha256": _require_hex(predecessor_sha256, "command predecessor"),
        "argv_template_sha256": sha256_bytes(canonical_bytes(template["argv"])),
        "argv_sha256": sha256_bytes(canonical_bytes(argv)),
        "timeout_sec": template["timeout_sec"],
        "max_bytes": template["max_bytes"],
        "returncode": 0,
        "execution_started_at": _require_int(started_at, "execution started"),
        "execution_completed_at": _require_int(completed_at, "execution completed"),
        "return_retained_at": _require_int(retained_at, "return retained"),
        "receipt_published_at": _require_int(published_at, "receipt published"),
        "stdout_size": len(stdout),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_size": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
        "host_tool_before": intent["adb_client"],
        "host_tool_after": intent["adb_client"],
        "clock_binding_sha256": sha256_bytes(canonical_bytes(intent["clock_binding"])),
        "adb_server_sha256": sha256_bytes(canonical_bytes(intent["adb_server"])),
    }
    if len(stdout) + len(stderr) > template["max_bytes"]:
        raise CampaignV1Error("opening raw pair exceeds 64 KiB")
    validate_opening_command_receipt(value, canonical_bytes(value), template, argv)
    return value


def validate_opening_command_receipt(
    value: Any,
    raw: bytes,
    template: Mapping[str, Any],
    argv: Sequence[str],
) -> dict[str, Any]:
    _exact_keys(value, OPENING_RECEIPT_KEYS, "opening command receipt")
    if canonical_bytes(value) != raw or len(raw) > OPENING_RECEIPT_MAX_BYTES:
        raise CampaignV1Error("opening receipt bytes differ or exceed 8 KiB")
    for key in (
        "ordinal",
        "timeout_sec",
        "max_bytes",
        "returncode",
        "execution_started_at",
        "execution_completed_at",
        "return_retained_at",
        "receipt_published_at",
        "stdout_size",
        "stderr_size",
    ):
        _require_int(value[key], f"opening receipt.{key}")
    for key in (
        "predecessor_sha256",
        "argv_template_sha256",
        "argv_sha256",
        "stdout_sha256",
        "stderr_sha256",
        "clock_binding_sha256",
        "adb_server_sha256",
    ):
        _require_hex(value[key], f"opening receipt.{key}")
    before = validate_tool_identity(value["host_tool_before"])
    after = validate_tool_identity(value["host_tool_after"])
    if (
        value["schema"] != OPENING_COMMAND_SCHEMA
        or value["phase"] != "attended-opening"
        or value["ordinal"] != template["ordinal"]
        or value["argv_template_sha256"] != sha256_bytes(canonical_bytes(template["argv"]))
        or value["argv_sha256"] != sha256_bytes(canonical_bytes(list(argv)))
        or value["timeout_sec"] != template["timeout_sec"]
        or value["max_bytes"] != template["max_bytes"]
        or value["returncode"] != 0
        or value["execution_completed_at"] < value["execution_started_at"]
        or value["execution_completed_at"] - value["execution_started_at"] > template["timeout_sec"]
        or value["return_retained_at"] < value["execution_completed_at"]
        or value["receipt_published_at"] < value["return_retained_at"]
        or not _exact_equal(before, after)
    ):
        raise CampaignV1Error("opening command receipt semantics differ")
    return dict(value)


HEALTH_KEYS = {
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


def validate_health(value: Any) -> dict[str, Any]:
    _exact_keys(value, HEALTH_KEYS, "health")
    target = value["target"]
    _exact_keys(
        target,
        {"model", "adb_serial_sha256", "usb_topology_sha256", "other_serial_sha256", "inventory_sha256"},
        "health target",
    )
    for key in ("adb_serial_sha256", "usb_topology_sha256", "inventory_sha256"):
        _require_hex(target[key], f"health target.{key}")
    if type(target["other_serial_sha256"]) is not list:
        raise CampaignV1Error("other serial hashes are not a list")
    for item in target["other_serial_sha256"]:
        _require_hex(item, "other serial hash")
    properties = value["properties"]
    if type(properties) is not dict or set(properties) != set(PROPERTY_KEYS) - {"boot_id"}:
        raise CampaignV1Error("health property closure differs")
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
        raise CampaignV1Error("health target/build/state differs")
    if (
        f"/{TARGET['product']}/{TARGET['device']}:" not in properties["fingerprint"]
        or not properties["fingerprint"].endswith(":user/release-keys")
        or SHELL_ID_RE.fullmatch(properties["shell_identity"]) is None
    ):
        raise CampaignV1Error("health fingerprint or shell identity differs")
    _require_hex(value["boot_id_sha256"], "health boot hash")
    tool = value["host_tool"]
    _exact_keys(
        tool,
        {"path", "device", "inode", "mtime_ns", "size", "sha256", "version_output_sha256"},
        "health host tool",
    )
    validate_tool_identity({key: tool[key] for key in ("path", "device", "inode", "mtime_ns", "size", "sha256")})
    _require_hex(tool["version_output_sha256"], "ADB version output hash")
    expected_counts = {
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }
    if any(type(value[key]) is not int or value[key] != expected for key, expected in expected_counts.items()):
        raise CampaignV1Error("health command accounting differs")
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
            raise CampaignV1Error("health crosses the public read-only boundary")
    if (
        value["schema"] != HEALTH_SCHEMA
        or value["version"] != HEALTH_VERSION
        or value["mode"] != "connected-read-only"
        or target["model"] != TARGET["model"]
        or value["usb_debugging_verified"] is not True
        or value["adb_authorization_state"] != "device"
        or value["verdict"] != HEALTH_VERDICT
    ):
        raise CampaignV1Error("health envelope differs")
    return dict(value)


def _derive_health_from_validated_returns(
    evidence: Mapping[str, bytes],
    receipts: Sequence[Mapping[str, Any]],
    selected_serial: str,
) -> dict[str, Any]:
    if len(receipts) != 6:
        raise CampaignV1Error("opening return derivation requires six receipts")
    version = _decode_success(
        evidence["cmd-01.stdout.bin"], evidence["cmd-01.stderr.bin"], "ADB version"
    )
    first_rows = parse_inventory(
        _decode_success(
            evidence["cmd-02.stdout.bin"],
            evidence["cmd-02.stderr.bin"],
            "initial inventory",
        )
    )
    selected = select_target(first_rows)
    if selected["serial"] != selected_serial:
        raise CampaignV1Error("selected serial differs from retained inventory")
    devpath = _decode_success(
        evidence["cmd-03.stdout.bin"], evidence["cmd-03.stderr.bin"], "devpath"
    )
    if DEVPATH_RE.fullmatch(devpath) is None:
        raise CampaignV1Error("retained devpath grammar differs")
    usb_tokens = [item for item in selected["metadata"] if item.startswith("usb:")]
    if usb_tokens != [devpath]:
        raise CampaignV1Error("inventory USB token differs from get-devpath")
    first_snapshot = parse_snapshot(
        _decode_exact_stdout(
            evidence["cmd-04.stdout.bin"],
            evidence["cmd-04.stderr.bin"],
            "first snapshot",
        )
    )
    second_snapshot = parse_snapshot(
        _decode_exact_stdout(
            evidence["cmd-05.stdout.bin"],
            evidence["cmd-05.stderr.bin"],
            "second snapshot",
        )
    )
    if first_snapshot != second_snapshot:
        raise CampaignV1Error("opening snapshots differ")
    final_rows = parse_inventory(
        _decode_success(
            evidence["cmd-06.stdout.bin"],
            evidence["cmd-06.stderr.bin"],
            "final inventory",
        )
    )
    final_selected = select_target(final_rows)
    if (
        final_selected["serial"] != selected_serial
        or _sanitized_inventory(final_rows) != _sanitized_inventory(first_rows)
    ):
        raise CampaignV1Error("opening target or global inventory drifted")
    properties = dict(first_snapshot)
    boot_id = properties.pop("boot_id")
    common_tool = validate_tool_identity(receipts[0]["host_tool_before"])
    for receipt in receipts:
        if not _exact_equal(receipt["host_tool_before"], common_tool):
            raise CampaignV1Error("opening held ADB client changed")
    health = {
        "schema": HEALTH_SCHEMA,
        "version": HEALTH_VERSION,
        "mode": "connected-read-only",
        "target": {
            "model": TARGET["model"],
            "adb_serial_sha256": sha256_bytes(selected_serial.encode()),
            "usb_topology_sha256": sha256_bytes(devpath.encode()),
            "other_serial_sha256": sorted(
                sha256_bytes(row["serial"].encode())
                for row in first_rows
                if row["serial"] != selected_serial
            ),
            "inventory_sha256": sha256_bytes(
                json.dumps(_sanitized_inventory(first_rows), sort_keys=True).encode()
            ),
        },
        "properties": properties,
        "boot_id_sha256": sha256_bytes(boot_id.encode()),
        "usb_debugging_verified": True,
        "adb_authorization_state": "device",
        "host_tool": {
            **common_tool,
            "version_output_sha256": sha256_bytes(version.encode()),
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
    return validate_health(health)


def validate_opening_evidence(
    *,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    evidence: Mapping[str, bytes],
    selected_serial: str,
) -> dict[str, Any]:
    intent = validate_opening_intent(dict(intent), intent_raw)
    if type(evidence) is not dict or set(evidence) != set(OPENING_EVIDENCE_NAMES):
        raise CampaignV1Error("opening evidence is not the exact 19-file set")
    argvs = expected_actual_argvs(selected_serial)
    predecessor = sha256_bytes(intent_raw)
    previous_time = intent["created_at"]
    opening_deadline = intent["created_at"] + OPENING_RECEIPT_CHAIN_MAX_SEC
    receipts: list[dict[str, Any]] = []
    proof_bytes = 0
    for ordinal, (template, argv) in enumerate(zip(FIXED_TRANSCRIPT, argvs, strict=True), 1):
        stdout = evidence[f"cmd-{ordinal:02d}.stdout.bin"]
        stderr = evidence[f"cmd-{ordinal:02d}.stderr.bin"]
        receipt_raw = evidence[f"cmd-{ordinal:02d}.receipt.json"]
        if type(stdout) is not bytes or type(stderr) is not bytes:
            raise CampaignV1Error("opening raw stream is not bytes")
        if len(stdout) + len(stderr) > template["max_bytes"]:
            raise CampaignV1Error("opening raw pair exceeds its bound")
        receipt = parse_canonical_json(receipt_raw, "opening command receipt", OPENING_RECEIPT_MAX_BYTES)
        validate_opening_command_receipt(receipt, receipt_raw, template, argv)
        if (
            receipt["predecessor_sha256"] != predecessor
            or receipt["execution_started_at"] < previous_time
            or receipt["execution_started_at"] > opening_deadline
            or receipt["execution_completed_at"] > opening_deadline
            or receipt["return_retained_at"] > opening_deadline
            or receipt["receipt_published_at"] > opening_deadline
            or receipt["stdout_size"] != len(stdout)
            or receipt["stdout_sha256"] != sha256_bytes(stdout)
            or receipt["stderr_size"] != len(stderr)
            or receipt["stderr_sha256"] != sha256_bytes(stderr)
            or receipt["clock_binding_sha256"] != sha256_bytes(canonical_bytes(intent["clock_binding"]))
            or receipt["adb_server_sha256"] != sha256_bytes(canonical_bytes(intent["adb_server"]))
        ):
            raise CampaignV1Error("opening command predecessor, raw, clock, or server binding differs")
        receipts.append(receipt)
        predecessor = sha256_bytes(receipt_raw)
        previous_time = receipt["receipt_published_at"]
        proof_bytes += len(stdout) + len(stderr) + len(receipt_raw)
    health_raw = evidence["health.json"]
    health = parse_canonical_json(health_raw, "opening health", OPENING_HEALTH_MAX_BYTES)
    validate_health(health)
    derived_health = _derive_health_from_validated_returns(
        evidence, receipts, selected_serial
    )
    if (
        not _exact_equal(health, derived_health)
        or health["target"]["adb_serial_sha256"] != sha256_bytes(selected_serial.encode())
        or not _exact_equal(
            {key: health["host_tool"][key] for key in ("path", "device", "inode", "mtime_ns", "size", "sha256")},
            intent["adb_client"],
        )
    ):
        raise CampaignV1Error(
            "opening health is not the exact derivation of retained returns"
        )
    proof_bytes += len(health_raw)
    if proof_bytes > OPENING_EVIDENCE_PROOF_MAX_BYTES:
        raise CampaignV1Error("opening evidence proof exceeds 507904 bytes")
    return {
        "receipts": receipts,
        "health": health,
        "actual_bytes": proof_bytes,
        "manifest": [
            {"name": name, "size": len(evidence[name]), "sha256": sha256_bytes(evidence[name])}
            for name in OPENING_EVIDENCE_NAMES
        ],
    }


OPENING_RESULT_KEYS = {
    "schema",
    "kind",
    "completed_at",
    "campaign_id",
    "session_id",
    "target",
    "source_identity",
    "opening_intent_sha256",
    "last_receipt_sha256",
    "health_sha256",
    "evidence_files",
    "evidence_set_sha256",
    "actual_evidence_bytes",
    "producer_binding_sha256",
    "recovery_binding_sha256",
    "clock_binding_sha256",
    "clock_sample",
    "adb_server_sha256",
    "usb_generation",
    "usb_generation_sha256",
    "host_command_count",
    "selected_target_command_count",
    "other_target_command_count",
    "attempt_consumed",
    "replay_authorized",
    "device_effect_count",
}


def model_opening_result(
    *,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    evidence: Mapping[str, bytes],
    selected_serial: str,
    clock_sample: Mapping[str, Any],
    usb_generation: Mapping[str, Any],
) -> dict[str, Any]:
    intent = validate_opening_intent(dict(intent), intent_raw)
    validated = validate_opening_evidence(
        intent=intent,
        intent_raw=intent_raw,
        evidence=evidence,
        selected_serial=selected_serial,
    )
    health = validated["health"]
    source = {
        "target": dict(TARGET),
        "serial_sha256": health["target"]["adb_serial_sha256"],
        "topology_sha256": health["target"]["usb_topology_sha256"],
        "boot_id_sha256": health["boot_id_sha256"],
        "healthy_android": True,
        "foreign_guard_present": False,
    }
    validate_source_identity(source)
    clock = validate_clock_sample(intent["clock_binding"], dict(clock_sample))
    usb = validate_usb_generation(dict(usb_generation), source)
    manifest = validated["manifest"]
    result = {
        "schema": OPENING_RESULT_SCHEMA,
        "kind": "attended-opening-result",
        "completed_at": validated["receipts"][-1]["receipt_published_at"],
        "campaign_id": intent["campaign_id"],
        "session_id": intent["session_id"],
        "target": dict(TARGET),
        "source_identity": source,
        "opening_intent_sha256": sha256_bytes(intent_raw),
        "last_receipt_sha256": sha256_bytes(evidence["cmd-06.receipt.json"]),
        "health_sha256": sha256_bytes(evidence["health.json"]),
        "evidence_files": manifest,
        "evidence_set_sha256": sha256_bytes(canonical_bytes(manifest)),
        "actual_evidence_bytes": validated["actual_bytes"],
        "producer_binding_sha256": sha256_bytes(canonical_bytes(intent["producer_binding"])),
        "recovery_binding_sha256": sha256_bytes(canonical_bytes(intent["recovery_binding"])),
        "clock_binding_sha256": sha256_bytes(canonical_bytes(intent["clock_binding"])),
        "clock_sample": clock,
        "adb_server_sha256": sha256_bytes(canonical_bytes(intent["adb_server"])),
        "usb_generation": usb,
        "usb_generation_sha256": sha256_bytes(canonical_bytes(usb)),
        "host_command_count": 6,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "attempt_consumed": True,
        "replay_authorized": False,
        "device_effect_count": 0,
    }
    validate_opening_result(
        result,
        canonical_bytes(result),
        intent,
        intent_raw,
        evidence,
        selected_serial,
    )
    return result


def validate_opening_result(
    value: Any,
    raw: bytes,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    evidence: Mapping[str, bytes],
    selected_serial: str,
) -> dict[str, Any]:
    intent = validate_opening_intent(dict(intent), intent_raw)
    validated_evidence = validate_opening_evidence(
        intent=intent,
        intent_raw=intent_raw,
        evidence=evidence,
        selected_serial=selected_serial,
    )
    _exact_keys(value, OPENING_RESULT_KEYS, "opening result")
    if canonical_bytes(value) != raw or len(raw) > OPENING_RESULT_MAX_BYTES:
        raise CampaignV1Error("opening result bytes differ or exceed 16 KiB")
    source = validate_source_identity(value["source_identity"])
    derived_health = validated_evidence["health"]
    expected_source = {
        "target": dict(TARGET),
        "serial_sha256": derived_health["target"]["adb_serial_sha256"],
        "topology_sha256": derived_health["target"]["usb_topology_sha256"],
        "boot_id_sha256": derived_health["boot_id_sha256"],
        "healthy_android": True,
        "foreign_guard_present": False,
    }
    validate_clock_sample(intent["clock_binding"], value["clock_sample"])
    validate_usb_generation(value["usb_generation"], source)
    expected_manifest = validated_evidence["manifest"]
    if type(value["evidence_files"]) is not list:
        raise CampaignV1Error("opening result evidence manifest is not a list")
    for index, item in enumerate(value["evidence_files"]):
        _exact_keys(item, {"name", "size", "sha256"}, f"opening manifest {index}")
        if type(item["name"]) is not str or type(item["size"]) is not int or type(item["size"]) is bool:
            raise CampaignV1Error("opening result evidence manifest item differs")
        _require_hex(item["sha256"], "opening result evidence item hash")
    for key in (
        "opening_intent_sha256",
        "last_receipt_sha256",
        "health_sha256",
        "evidence_set_sha256",
        "producer_binding_sha256",
        "recovery_binding_sha256",
        "clock_binding_sha256",
        "adb_server_sha256",
        "usb_generation_sha256",
    ):
        _require_hex(value[key], f"opening result.{key}")
    _require_int(value["completed_at"], "opening completed_at")
    _require_int(value["actual_evidence_bytes"], "opening evidence bytes")
    if (
        value["schema"] != OPENING_RESULT_SCHEMA
        or value["kind"] != "attended-opening-result"
        or value["campaign_id"] != intent["campaign_id"]
        or value["session_id"] != intent["session_id"]
        or value["target"] != dict(TARGET)
        or not _exact_equal(source, expected_source)
        or value["opening_intent_sha256"] != sha256_bytes(intent_raw)
        or value["completed_at"]
        != validated_evidence["receipts"][-1]["receipt_published_at"]
        or value["clock_sample"]["logical_sec"] != value["completed_at"]
        or value["completed_at"]
        > intent["created_at"] + OPENING_RECEIPT_CHAIN_MAX_SEC
        or value["last_receipt_sha256"]
        != sha256_bytes(evidence["cmd-06.receipt.json"])
        or value["health_sha256"] != sha256_bytes(evidence["health.json"])
        or value["producer_binding_sha256"] != sha256_bytes(canonical_bytes(intent["producer_binding"]))
        or value["recovery_binding_sha256"] != sha256_bytes(canonical_bytes(intent["recovery_binding"]))
        or value["clock_binding_sha256"] != sha256_bytes(canonical_bytes(intent["clock_binding"]))
        or value["adb_server_sha256"] != sha256_bytes(canonical_bytes(intent["adb_server"]))
        or value["usb_generation_sha256"] != sha256_bytes(canonical_bytes(value["usb_generation"]))
        or value["host_command_count"] != 6
        or value["selected_target_command_count"] != 3
        or value["other_target_command_count"] != 0
        or value["attempt_consumed"] is not True
        or value["replay_authorized"] is not False
        or value["device_effect_count"] != 0
        or value["actual_evidence_bytes"] > OPENING_EVIDENCE_PROOF_MAX_BYTES
        or value["evidence_files"] != expected_manifest
        or value["actual_evidence_bytes"] != validated_evidence["actual_bytes"]
        or value["evidence_set_sha256"] != sha256_bytes(canonical_bytes(value["evidence_files"]))
    ):
        raise CampaignV1Error("opening result semantics differ")
    return dict(value)


def zero_read_counters() -> dict[str, int]:
    return {
        "private_evidence_bytes_consumed": 0,
        "private_evidence_bytes_reserved": 0,
        "read_operations": 0,
    }


def reserved_read_counters() -> dict[str, int]:
    return {
        "private_evidence_bytes_consumed": 0,
        "private_evidence_bytes_reserved": READ_EVIDENCE_RESERVATION_BYTES,
        "read_operations": 1,
    }


def zero_control_counters() -> dict[str, int]:
    return {
        "component_effects_consumed": 0,
        "component_effects_reserved": 0,
        "control_transactions": 0,
        "download_roundtrips": 0,
        "normal_reboots": 0,
        "roundtrip_entries": 0,
        "roundtrip_returns": 0,
    }


FORWARD_NODE_ORDER = (
    "active-campaign.json",
    "opening.json",
    "session-opening.json",
    "accounting-opening.json",
    "public-health-read-lease-000001.json",
    "read-intent-000001.json",
)


def model_forward_nodes(
    opening_result: Mapping[str, Any],
    opening_result_raw: bytes,
    *,
    opening_intent: Mapping[str, Any],
    opening_intent_raw: bytes,
    opening_evidence: Mapping[str, bytes],
    selected_serial: str,
) -> dict[str, bytes]:
    result = dict(opening_result)
    validate_opening_result(
        result,
        opening_result_raw,
        opening_intent,
        opening_intent_raw,
        opening_evidence,
        selected_serial,
    )
    source = validate_source_identity(result["source_identity"])
    campaign_id = _require_id(result["campaign_id"], "forward campaign id")
    session_id = _require_id(result["session_id"], "forward session id")
    opened = _require_int(result["completed_at"], "forward opened_at")
    campaign_expiry = opened + 24 * 60 * 60
    session_expiry = opened + 4 * 60 * 60
    zero_read = zero_read_counters()
    zero_control = zero_control_counters()

    opening = {
        "schema": BASE_SCHEMA,
        "kind": "campaign-opening",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "policy_binding_sha256": POLICY_BINDING_SHA256,
        "coordinator_normalized_sha256": BASE_COORDINATOR_NORMALIZED_SHA256,
        "source_identity": source,
        "opened_at": opened,
        "expires_at": campaign_expiry,
        "campaign_counters": zero_control,
        "child_counters": zero_control,
        "predecessor_sha256": ZERO_HASH,
        "attended_opening": True,
        "no_replay": True,
        "f1_intent": False,
        "approval_consumed": False,
        "partition_transfer": False,
    }
    opening_raw = canonical_bytes(opening)
    session = {
        "schema": BASE_SCHEMA,
        "kind": "session-opening",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "policy_binding_sha256": POLICY_BINDING_SHA256,
        "coordinator_normalized_sha256": BASE_COORDINATOR_NORMALIZED_SHA256,
        "source_identity": source,
        "opened_at": opened,
        "expires_at": session_expiry,
        "campaign_counters": zero_control,
        "child_counters": zero_control,
        "predecessor_sha256": sha256_bytes(opening_raw),
        "no_replay": True,
    }
    session_raw = canonical_bytes(session)
    guard = {
        "schema": BASE_SCHEMA,
        "kind": "campaign-guard",
        "phase": "allocation-claimed",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "policy_binding_sha256": POLICY_BINDING_SHA256,
        "coordinator_normalized_sha256": BASE_COORDINATOR_NORMALIZED_SHA256,
        "source_identity": source,
        "opened_at": opened,
        "expires_at": campaign_expiry,
        "opening_sha256": sha256_bytes(opening_raw),
        "session_opening_sha256": sha256_bytes(session_raw),
        "opening": opening,
        "session": session,
        "campaign_counters": zero_control,
        "child_counters": zero_control,
        "no_replay": True,
        "f1_intent": False,
        "approval_consumed": False,
        "partition_transfer": False,
    }
    guard_raw = canonical_bytes(guard)
    context = {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "phase": "healthy-normal",
        "expired": False,
        "session_expired": False,
        "current_time": opened,
        "campaign_expires_at": campaign_expiry,
        "session_expires_at": session_expiry,
        "current_ordinal": 0,
        "source_identity": source,
        "endpoint": None,
        "predecessor_sha256": sha256_bytes(session_raw),
        "child_counters": zero_control,
        "campaign_counters": zero_control,
        "terminal": None,
        "f1_intent": False,
        "approval_consumed": False,
        "partition_transfer": False,
        "no_replay": True,
        "pending_intent_issued_at": None,
    }
    accounting = {
        "schema": ACCOUNTING_OPENING_SCHEMA,
        "kind": "accounting-opening",
        "recorded_at": opened,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "allocation_source_identity": source,
        "source_identity": source,
        "sources": _plain(FROZEN_SOURCE_RECEIPTS),
        "coordinator_guard": guard,
        "coordinator_opening": opening,
        "coordinator_session": session,
        "coordinator_guard_sha256": sha256_bytes(guard_raw),
        "coordinator_opening_sha256": sha256_bytes(opening_raw),
        "coordinator_session_sha256": sha256_bytes(session_raw),
        "first_current_context": context,
        "first_current_context_sha256": sha256_bytes(canonical_bytes(context)),
        "first_coordinator_head": session,
        "first_coordinator_head_sha256": sha256_bytes(session_raw),
        "child_counters": zero_read,
        "campaign_counters": zero_read,
        "attended_opening": True,
        "no_replay": True,
        "command_execution_backend": False,
    }
    accounting_raw = canonical_bytes(accounting)
    expected_tool = {"path": ADB_PATH, "size": ADB_SIZE, "sha256": ADB_SHA256}
    lease = {
        "schema": COORDINATOR_LEASE_SCHEMA,
        "kind": "public-health-read-lease",
        "issued_at": opened,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "action": "public-health",
        "read_ordinal": 1,
        "accounting_opening_sha256": sha256_bytes(accounting_raw),
        "coordinator_context": context,
        "coordinator_context_sha256": sha256_bytes(canonical_bytes(context)),
        "coordinator_head": session,
        "coordinator_head_sha256": sha256_bytes(session_raw),
        "source_identity": source,
        "previous_evidence_result_sha256": ZERO_HASH,
        "previous_coordinator_complete_sha256": ZERO_HASH,
        "previous_child_counters": zero_read,
        "previous_campaign_counters": zero_read,
        "child_counters": reserved_read_counters(),
        "campaign_counters": reserved_read_counters(),
        "reservation_bytes": READ_EVIDENCE_RESERVATION_BYTES,
        "expected_host_tool": expected_tool,
        "attempt_consumed": True,
        "replay_authorized": False,
        "controls_blocked": True,
        "terminal_blocked": True,
        "completion_required": True,
    }
    lease_raw = canonical_bytes(lease)
    read_intent = {
        "schema": READ_INTENT_SCHEMA,
        "kind": "read-intent-mirror",
        "mirrored_at": opened,
        "campaign_id": campaign_id,
        "session_id": session_id,
        "target": dict(TARGET),
        "action": "public-health",
        "read_ordinal": 1,
        "coordinator_lease_sha256": sha256_bytes(lease_raw),
        "lease_issued_at": opened,
        "lease_observed_at": opened,
        "campaign_expires_at": campaign_expiry,
        "session_expires_at": session_expiry,
        "coordinator_head_sha256": sha256_bytes(session_raw),
        "source_identity": source,
        "previous_evidence_result_sha256": ZERO_HASH,
        "previous_coordinator_complete_sha256": ZERO_HASH,
        "child_counters": reserved_read_counters(),
        "campaign_counters": reserved_read_counters(),
        "reservation_bytes": READ_EVIDENCE_RESERVATION_BYTES,
        "expected_evidence_names": sorted(READ_EVIDENCE_NAMES),
        "attempt_consumed": True,
        "uncertain_if_incomplete": True,
        "replay_authorized": False,
        "next_action_before_coordinator_complete": False,
        "command_execution_backend": False,
    }
    nodes = {
        "active-campaign.json": guard_raw,
        "opening.json": opening_raw,
        "session-opening.json": session_raw,
        "accounting-opening.json": accounting_raw,
        "public-health-read-lease-000001.json": lease_raw,
        "read-intent-000001.json": canonical_bytes(read_intent),
    }
    if tuple(nodes) != FORWARD_NODE_ORDER:
        raise CampaignV1Error("forward publication must be guard-first")
    structural_size = 0
    for name, payload in nodes.items():
        if len(payload) > STRUCTURAL_CAPS[name]:
            raise CampaignV1Error(f"{name} exceeds its structural cap")
        structural_size += len(payload)
    if structural_size > STRUCTURAL_MAX_BYTES:
        raise CampaignV1Error("forward nodes exceed the structural aggregate")
    return nodes


CAMPAIGN_BINDING_KEYS = {
    "schema",
    "kind",
    "bound_at",
    "campaign_id",
    "session_id",
    "target",
    "source_identity",
    "opening_intent_sha256",
    "opening_result_sha256",
    "opening_evidence_set_sha256",
    "producer_binding",
    "recovery_binding",
    "clock_binding_sha256",
    "adb_server_sha256",
    "usb_generation_sha256",
    "forward_publication_order",
    "forward_commitments",
    "read_ordinal_max",
    "same_process_handoff_required",
    "same_process_handoff_implemented",
    "durable_nodes_authorize_read_commands",
    "total_opening_to_read_freshness_proven",
    "future_rotated_finalizer_only_after_cut",
    "shared_active_action_created",
    "operational_authority",
    "no_replay",
}


def model_campaign_binding(
    *,
    opening_intent: Mapping[str, Any],
    opening_intent_raw: bytes,
    opening_result: Mapping[str, Any],
    opening_result_raw: bytes,
    opening_evidence: Mapping[str, bytes],
    selected_serial: str,
    forward_nodes: Mapping[str, bytes],
) -> dict[str, Any]:
    intent = validate_opening_intent(dict(opening_intent), opening_intent_raw)
    result = validate_opening_result(
        dict(opening_result),
        opening_result_raw,
        intent,
        opening_intent_raw,
        opening_evidence,
        selected_serial,
    )
    expected_forward = model_forward_nodes(
        result,
        opening_result_raw,
        opening_intent=intent,
        opening_intent_raw=opening_intent_raw,
        opening_evidence=opening_evidence,
        selected_serial=selected_serial,
    )
    if type(forward_nodes) is not dict or tuple(forward_nodes) != FORWARD_NODE_ORDER:
        raise CampaignV1Error("campaign binding forward nodes are not guard-first")
    if any(forward_nodes[name] != expected_forward[name] for name in FORWARD_NODE_ORDER):
        raise CampaignV1Error("campaign binding forward node is not deterministic")
    commitments: dict[str, str] = {}
    for name in FORWARD_NODE_ORDER:
        payload = forward_nodes[name]
        if type(payload) is not bytes or not payload or len(payload) > STRUCTURAL_CAPS[name]:
            raise CampaignV1Error("campaign forward commitment payload differs")
        parse_canonical_json(payload, name, STRUCTURAL_CAPS[name])
        commitments[name] = sha256_bytes(payload)
    value = {
        "schema": CAMPAIGN_BINDING_SCHEMA,
        "kind": "campaign-binding",
        "bound_at": result["completed_at"],
        "campaign_id": result["campaign_id"],
        "session_id": result["session_id"],
        "target": dict(TARGET),
        "source_identity": result["source_identity"],
        "opening_intent_sha256": sha256_bytes(opening_intent_raw),
        "opening_result_sha256": sha256_bytes(opening_result_raw),
        "opening_evidence_set_sha256": result["evidence_set_sha256"],
        "producer_binding": intent["producer_binding"],
        "recovery_binding": intent["recovery_binding"],
        "clock_binding_sha256": result["clock_binding_sha256"],
        "adb_server_sha256": result["adb_server_sha256"],
        "usb_generation_sha256": result["usb_generation_sha256"],
        "forward_publication_order": list(FORWARD_NODE_ORDER),
        "forward_commitments": commitments,
        "read_ordinal_max": 1,
        "same_process_handoff_required": True,
        "same_process_handoff_implemented": False,
        "durable_nodes_authorize_read_commands": False,
        "total_opening_to_read_freshness_proven": False,
        "future_rotated_finalizer_only_after_cut": True,
        "shared_active_action_created": False,
        "operational_authority": False,
        "no_replay": True,
    }
    validate_campaign_binding(
        value,
        canonical_bytes(value),
        intent,
        opening_intent_raw,
        result,
        opening_result_raw,
        opening_evidence,
        selected_serial,
        forward_nodes,
    )
    return value


def validate_campaign_binding(
    value: Any,
    raw: bytes,
    intent: Mapping[str, Any],
    intent_raw: bytes,
    result: Mapping[str, Any],
    result_raw: bytes,
    opening_evidence: Mapping[str, bytes],
    selected_serial: str,
    forward_nodes: Mapping[str, bytes],
) -> dict[str, Any]:
    validate_opening_intent(dict(intent), intent_raw)
    validate_opening_result(
        dict(result),
        result_raw,
        intent,
        intent_raw,
        opening_evidence,
        selected_serial,
    )
    expected_forward = model_forward_nodes(
        result,
        result_raw,
        opening_intent=intent,
        opening_intent_raw=intent_raw,
        opening_evidence=opening_evidence,
        selected_serial=selected_serial,
    )
    _exact_keys(value, CAMPAIGN_BINDING_KEYS, "campaign binding")
    if canonical_bytes(value) != raw or len(raw) > CAMPAIGN_BINDING_MAX_BYTES:
        raise CampaignV1Error("campaign binding bytes differ or exceed 16 KiB")
    validate_source_identity(value["source_identity"])
    validate_producer_binding(value["producer_binding"])
    validate_recovery_binding(value["recovery_binding"])
    for key in (
        "opening_intent_sha256",
        "opening_result_sha256",
        "opening_evidence_set_sha256",
        "clock_binding_sha256",
        "adb_server_sha256",
        "usb_generation_sha256",
    ):
        _require_hex(value[key], f"campaign binding.{key}")
    expected_commitments = {
        name: sha256_bytes(forward_nodes[name]) for name in FORWARD_NODE_ORDER
    }
    if (
        value["schema"] != CAMPAIGN_BINDING_SCHEMA
        or value["kind"] != "campaign-binding"
        or value["bound_at"] != result["completed_at"]
        or value["campaign_id"] != intent["campaign_id"]
        or value["session_id"] != intent["session_id"]
        or value["target"] != dict(TARGET)
        or not _exact_equal(value["source_identity"], result["source_identity"])
        or value["opening_intent_sha256"] != sha256_bytes(intent_raw)
        or value["opening_result_sha256"] != sha256_bytes(result_raw)
        or value["opening_evidence_set_sha256"] != result["evidence_set_sha256"]
        or not _exact_equal(value["producer_binding"], intent["producer_binding"])
        or not _exact_equal(value["recovery_binding"], intent["recovery_binding"])
        or value["clock_binding_sha256"] != result["clock_binding_sha256"]
        or value["adb_server_sha256"] != result["adb_server_sha256"]
        or value["usb_generation_sha256"] != result["usb_generation_sha256"]
        or value["forward_publication_order"] != list(FORWARD_NODE_ORDER)
        or value["forward_commitments"] != expected_commitments
        or any(
            forward_nodes[name] != expected_forward[name]
            for name in FORWARD_NODE_ORDER
        )
        or type(value["read_ordinal_max"]) is not int
        or value["read_ordinal_max"] != 1
        or value["same_process_handoff_required"] is not True
        or value["same_process_handoff_implemented"] is not False
        or value["durable_nodes_authorize_read_commands"] is not False
        or value["total_opening_to_read_freshness_proven"] is not False
        or value["future_rotated_finalizer_only_after_cut"] is not True
        or value["shared_active_action_created"] is not False
        or value["operational_authority"] is not False
        or value["no_replay"] is not True
    ):
        raise CampaignV1Error("campaign binding semantics differ")
    return dict(value)


def _campaign_paths(campaign_id: str, session_id: str) -> dict[str, str]:
    _require_id(campaign_id, "path campaign id")
    _require_id(session_id, "path session id")
    campaign_hash = sha256_bytes(campaign_id.encode())
    session_hash = sha256_bytes(session_id.encode())
    base_session = f"base/campaigns/{campaign_id}/session"
    evidence_session = (
        f"evidence/campaigns/campaign-{campaign_hash}/sessions/session-{session_hash}"
    )
    return {"base_session": base_session, "evidence_session": evidence_session}


def publication_sequence(campaign_id: str, session_id: str) -> tuple[str, ...]:
    paths = _campaign_paths(campaign_id, session_id)
    opening = tuple(f"leaf/opening-v1/{name}" for name in OPENING_RETURN_NAMES)
    read = tuple(
        f"{paths['evidence_session']}/read-000001/{name}"
        for name in READ_RETURN_NAMES
    )
    sequence = (
        "leaf/coordinator.lock",
        "leaf/recovery-v1/recovery-core.py",
        "leaf/recovery-v1/manifest.json",
        "leaf/opening-v1/opening-intent.json",
        *opening,
        "leaf/opening-v1/health.json",
        "leaf/opening-v1/opening-result.json",
        "leaf/campaign-binding.json",
        "base/active-campaign.json",
        f"{paths['base_session']}/opening.json",
        f"{paths['base_session']}/session-opening.json",
        f"{paths['evidence_session']}/accounting-opening.json",
        "leaf/public-health-read-lease-000001.json",
        f"{paths['evidence_session']}/read-intent-000001.json",
        *read,
        f"{paths['evidence_session']}/read-000001/health.json",
        f"{paths['evidence_session']}/read-result-000001.json",
        "leaf/public-health-read-complete-000001.json",
    )
    if len(sequence) != COMPLETED_TOTAL_FILE_COUNT or len(set(sequence)) != len(sequence):
        raise CampaignV1Error("completed file sequence is not exactly 52 unique files")
    if sequence[25:28] != (
        "base/active-campaign.json",
        f"{paths['base_session']}/opening.json",
        f"{paths['base_session']}/session-opening.json",
    ):
        raise CampaignV1Error("base publication is not immutable guard-first")
    return sequence


def _cut_stage(prefix_length: int) -> str:
    if prefix_length < 3:
        return "PREOPENING_BUNDLE_INCOMPLETE_NO_AUTHORITY"
    if prefix_length == 3:
        return "RECOVERY_BUNDLE_PREFIX_PRESENT_PHASE_B_BINDING_REQUIRED"
    if prefix_length < 24:
        return "OPENING_ATTEMPT_CONSUMED_FUTURE_FINALIZER_ONLY_PARKED"
    if prefix_length == 24:
        return "OPENING_RESULT_PRESENT_BINDING_PENDING_FUTURE_FINALIZER_ONLY"
    if prefix_length < 31:
        return "CAMPAIGN_ALLOCATION_PREFIX_FUTURE_FINALIZER_ONLY"
    if prefix_length == 31:
        return "READ_INTENT_DURABLE_NO_COMMAND_AUTHORITY_PHASE_B_HANDOFF_REQUIRED"
    if prefix_length < 49:
        return "READ_ATTEMPT_CONSUMED_INCOMPLETE_FUTURE_FINALIZER_ONLY_PARKED"
    if prefix_length == 49:
        return "READ_RETURNS_COMPLETE_HEALTH_FUTURE_FINALIZER_CANDIDATE"
    if prefix_length == 50:
        return "READ_HEALTH_PRESENT_RESULT_FUTURE_FINALIZER_CANDIDATE"
    if prefix_length == 51:
        return "READ_RESULT_PRESENT_COMPLETION_FUTURE_FINALIZER_CANDIDATE"
    return "PARKED_COMPLETION_REEMIT_ONLY"


def classify_publication_cut(
    *,
    campaign_id: str,
    session_id: str,
    present_in_publication_order: Sequence[str],
    shared_active_action_present: bool = False,
) -> dict[str, Any]:
    if type(shared_active_action_present) is not bool:
        raise CampaignV1Error("shared active-action presence is not strict bool")
    if type(present_in_publication_order) not in (list, tuple) or any(
        type(item) is not str for item in present_in_publication_order
    ):
        raise CampaignV1Error("publication cut is not a string sequence")
    complete = publication_sequence(campaign_id, session_id)
    present = tuple(present_in_publication_order)
    if len(present) > len(complete) or present != complete[: len(present)]:
        raise CampaignV1Error("publication cut has a gap, reorder, duplicate, or foreign node")
    status = _cut_stage(len(present))
    campaign_consumed = len(present) >= 4
    if shared_active_action_present:
        status = (
            "FOREIGN_ACTIVE_ACTION_ZERO_COMMAND_YIELD"
            if not campaign_consumed
            else "FOREIGN_ACTIVE_ACTION_APPEARED_CONSUMED_ATTEMPT_PARKED"
        )
    return {
        "status": status,
        "present_count": len(present),
        "next_node": None,
        "modeled_next_node": (
            None if len(present) == len(complete) else complete[len(present)]
        ),
        "campaign_attempt_consumed": campaign_consumed,
        "opening_replay_authorized": False,
        "read_replay_authorized": False,
        "new_process_device_commands_authorized": False,
        "same_process_handoff_implemented": False,
        "durable_nodes_authorize_read_commands": False,
        "durable_content_validated": False,
        "process_capability_issued": False,
        "finalizer_only_resume": False,
        "current_finalizer_authorized": False,
        "future_finalizer_only_resume_authorized": False,
        "modeled_future_finalizer_candidate": campaign_consumed,
        "shared_active_action_created_by_campaign": False,
        "recovery_bypass_preserved": True,
        "campaign_parked": campaign_consumed,
    }


def normalized_source_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise CampaignV1Error("source normalization requires bytes")
    normalized = payload
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        normalized,
        flags=re.MULTILINE,
    )
    if status_count != 1:
        raise CampaignV1Error("source status normalization is ambiguous")
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "<REVIEWED_SELF_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    if anchor_count != 1:
        raise CampaignV1Error("source identity normalization is ambiguous")
    # Full recovery identities rotate after Phase-B grammar/binding activation.
    # Mask only those full atoms; names and reviewed logic-normalized identities
    # remain part of the producer's normalized identity.
    for name in ("EXPECTED_LOADER_SIZE", "EXPECTED_CORE_SIZE", "EXPECTED_MANIFEST_SIZE"):
        normalized, count = re.subn(
            rf"^{name} = [0-9_]+$".encode(),
            f"{name} = <REVIEWED_FULL_SIZE>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise CampaignV1Error("recovery full-size normalization is ambiguous")
    for name in (
        "EXPECTED_LOADER_SHA256",
        "EXPECTED_CORE_SHA256",
        "EXPECTED_MANIFEST_SHA256",
    ):
        normalized, count = re.subn(
            (
                rf'^({name} = \(\n    )"[0-9a-f]{{64}}"(\n\))$'
            ).encode(),
            rf'\1"<REVIEWED_FULL_SHA256>"\2'.encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise CampaignV1Error("recovery full-hash normalization is ambiguous")
    for name in (
        "CAMPAIGN_V1_QUALIFIED",
        "OPENING_ACTIVE",
        "READ_PRODUCER_ACTIVE",
        "RECOVERY_BUNDLE_BOUND",
        "RECOVERY_SCANNER_ROTATED",
        "RECOVERY_FINALIZER_ROTATED",
        "ADB_CLIENT_EXEC_ACTIVE",
        "EXECUTOR_IMPLEMENTED",
        "SAME_PROCESS_HANDOFF_IMPLEMENTED",
        "ADB_SERVER_PROVENANCE_PROVEN",
        "USB_GENERATION_PROVEN",
        "TRUSTED_CLOCK_PROVEN",
        "TARGET_COORDINATION_ACTIVE",
        "CROSS_CODE_COORDINATION_ACTIVE",
        "CONTRACT_ACTIVE",
        "MECHANICAL_ACTIVATION",
        "LIVE_AUTHORITY",
    ):
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode(),
            f"{name} = <REVIEWED_BOOLEAN>".encode(),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise CampaignV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _require_operational_gate() -> None:
    # This function contains no filesystem, process, clock, socket, USB, or
    # device access.  The connected owner must call it as its first statement.
    if not all(
        gate is True
        for gate in (
            CAMPAIGN_V1_QUALIFIED,
            OPENING_ACTIVE,
            READ_PRODUCER_ACTIVE,
            RECOVERY_BUNDLE_BOUND,
            RECOVERY_SCANNER_ROTATED,
            RECOVERY_FINALIZER_ROTATED,
            ADB_CLIENT_EXEC_ACTIVE,
            EXECUTOR_IMPLEMENTED,
            SAME_PROCESS_HANDOFF_IMPLEMENTED,
            ADB_SERVER_PROVENANCE_PROVEN,
            USB_GENERATION_PROVEN,
            TRUSTED_CLOCK_PROVEN,
            TARGET_COORDINATION_ACTIVE,
            CROSS_CODE_COORDINATION_ACTIVE,
            CONTRACT_ACTIVE,
            MECHANICAL_ACTIVATION,
        )
    ) or LIVE_AUTHORITY is not True:
        raise CampaignV1Error("campaign-v1 operational owner is inactive")


def attended_open_and_read() -> None:
    """Future no-input owner; Phase A stops before any observable operation."""

    _require_operational_gate()
    raise CampaignV1Error("campaign-v1 connected implementation is not activated")


def render_plan() -> dict[str, Any]:
    sample_campaign = "0" * 32
    sample_session = "1" * 32
    sequence = publication_sequence(sample_campaign, sample_session)
    gates = {
        "campaign_v1_qualified": CAMPAIGN_V1_QUALIFIED,
        "opening_active": OPENING_ACTIVE,
        "read_producer_active": READ_PRODUCER_ACTIVE,
        "recovery_bundle_bound": RECOVERY_BUNDLE_BOUND,
        "recovery_scanner_rotated": RECOVERY_SCANNER_ROTATED,
        "recovery_finalizer_rotated": RECOVERY_FINALIZER_ROTATED,
        "adb_client_exec_active": ADB_CLIENT_EXEC_ACTIVE,
        "executor_implemented": EXECUTOR_IMPLEMENTED,
        "same_process_handoff_implemented": SAME_PROCESS_HANDOFF_IMPLEMENTED,
        "adb_server_provenance_proven": ADB_SERVER_PROVENANCE_PROVEN,
        "usb_generation_proven": USB_GENERATION_PROVEN,
        "trusted_clock_proven": TRUSTED_CLOCK_PROVEN,
        "target_coordination_active": TARGET_COORDINATION_ACTIVE,
        "cross_code_coordination_active": CROSS_CODE_COORDINATION_ACTIVE,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
    }
    if any(gates.values()):
        raise CampaignV1Error("Phase-A render found an active operational gate")
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "live_capable_design": LIVE_CAPABLE_DESIGN,
        "phase_a_model_only": PHASE_A_MODEL_ONLY,
        "opening_raw_derivation_model_implemented": (
            OPENING_RAW_DERIVATION_MODEL_IMPLEMENTED
        ),
        "gates": gates,
        "cli": ["--render-plan"],
        "future_operational_entry": "attended_open_and_read-no-input-gated",
        "caller_inputs": [],
        "callbacks": [],
        "backends": [],
        "device_commands": [],
        "device_effects": [],
        "root_commands": [],
        "odin_commands": [],
        "partition_transfers": [],
        "fixed_roots": {
            "base": FIXED_BASE_ROOT,
            "evidence": FIXED_EVIDENCE_ROOT,
            "leaf": FIXED_LEAF_ROOT,
        },
        "coordination": {
            "cooperative_lock": "flock-on-held-leaf-root-directory-fd",
            "creates_shared_active_action": False,
            "shared_active_action_path": SHARED_ACTIVE_ACTION_PATH,
            "existing_recovery_bypasses_coordination_lock": True,
            "process_death_releases_flock": True,
            "same_uid_uncooperative_writer_closed": False,
        },
        "fixed_transcript_per_phase": list(FIXED_TRANSCRIPT),
        "phase_order": ["attended-opening", "ordinal-1-read"],
        "same_process_handoff": {
            "required_for_activation": True,
            "implemented": False,
            "proven": False,
            "durable_nodes_authorize_read_commands": False,
        },
        "planned_total_host_adb_invocations": 12,
        "planned_total_selected_target_commands": 6,
        "other_target_commands": 0,
        "same_process_12_command_closure_proven": False,
        "opening_command_executor_implemented": False,
        "ordinal1_read_executor_implemented": False,
        "publication": {
            "file_count": len(sequence),
            "guard_first": sequence[25].endswith("active-campaign.json"),
            "raw_before_receipt": True,
            "sequence": list(sequence),
        },
        "caps": {
            "recovery_bundle_max_bytes": RECOVERY_BUNDLE_MAX_BYTES,
            "opening_intent_max_bytes": OPENING_INTENT_MAX_BYTES,
            "opening_result_max_bytes": OPENING_RESULT_MAX_BYTES,
            "opening_logical_receipt_chain_max_sec": (
                OPENING_RECEIPT_CHAIN_MAX_SEC
            ),
            "total_opening_to_read_freshness_proven": False,
            "opening_19_file_reservation_bytes": OPENING_EVIDENCE_RESERVATION_BYTES,
            "opening_directory_max_bytes": OPENING_DIRECTORY_MAX_BYTES,
            "campaign_binding_max_bytes": CAMPAIGN_BINDING_MAX_BYTES,
            "structural_max_bytes": STRUCTURAL_MAX_BYTES,
            "read_reservation_bytes": READ_EVIDENCE_RESERVATION_BYTES,
            "completed_total_max_bytes": COMPLETED_TOTAL_MAX_BYTES,
            "completed_total_file_count": COMPLETED_TOTAL_FILE_COUNT,
        },
        "schemas": {
            "opening_intent": OPENING_INTENT_SCHEMA,
            "opening_command": OPENING_COMMAND_SCHEMA,
            "opening_result": OPENING_RESULT_SCHEMA,
            "campaign_binding": CAMPAIGN_BINDING_SCHEMA,
            "clock_binding": CLOCK_BINDING_SCHEMA,
            "clock_sample": CLOCK_SAMPLE_SCHEMA,
            "adb_server": ADB_SERVER_RECEIPT_SCHEMA,
            "usb_generation": USB_GENERATION_SCHEMA,
        },
        "forward_publication_order": list(FORWARD_NODE_ORDER),
        "recovery_finalizer_boundary": {
            "current_finalizer_accepts_opening_namespace": False,
            "future_rotated_finalizer_required": True,
            "phase_a_changes_current_finalizer": False,
        },
        "unresolved_activation_gates": [
            "ADB-server-provenance",
            "USB-generation-runtime-owner",
            "trusted-host-clock-runtime-owner",
            "unforgeable-same-process-opening-to-read-handoff",
            "current-recovery-scanner-opening-namespace-rotation",
            "zero-command-prelease-finalizer-extension",
            "cross-code-new-D1-F1-R1-start-coordination",
            "combined-independent-review",
            "binding-contract-and-mechanical-activation",
            "fresh-post-activation-attended-request",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--render-plan", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan exists in campaign-v1 Phase A")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
