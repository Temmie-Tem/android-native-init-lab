#!/usr/bin/env python3
"""Inactive H0 terminal-continuity adapter for the S20+ opening model.

The fixture model in this file adds a terminal continuity field to each of the
six Phase-A opening receipts.  It then derives a sanitized recovery-input
envelope from retained intent and evidence bytes only.  It is not an opening
result, a campaign binding, a recovery-loader integration, or live authority.

The public CLI is render-only.  Model helpers load and hash/normalization-check
the exact Phase-A and runtime sources before using their validators.  Recovery
loader/core/manifest identities are declarative pins only: this adapter neither
opens them nor proves their installed bytes.  These H0 fixtures authorize no
command, path, clock, serial, USB operation, or device access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import MappingProxyType, ModuleType, SimpleNamespace
from typing import Any, Mapping, Sequence


STATUS = "H0_AUTONOMOUS_PUBLIC_HEALTH_TERMINAL_CONTINUITY_V1_MODEL_PASS_GO_NOT_ACTIVE"
EXPECTED_SELF_NORMALIZED_SHA256 = "bba10951e24e798c57d4db103f9d591a09d495c753f106ca144b3b90d923095a"

# Operational and integration gates.  This source is reviewed and activated,
# if ever, only as a new exact-byte unit; changing these booleans is not an
# activation procedure.
TERMINAL_CONTINUITY_V1_QUALIFIED = False
PHASE_A_EXACT_BOUND = False
RUNTIME_EXACT_BOUND = False
RECOVERY_BUNDLE_EXACT_BOUND = False
RECEIPT_ADAPTER_INTEGRATED = False
OPENING_RESULT_INTEGRATED = False
CAMPAIGN_BINDING_INTEGRATED = False
RECOVERY_LOADER_INTEGRATED = False
EXECUTOR_IMPLEMENTED = False
TARGET_COORDINATION_ACTIVE = False
CROSS_CODE_COORDINATION_ACTIVE = False
CONTRACT_ACTIVE = False
MECHANICAL_ACTIVATION = False
LIVE_AUTHORITY = False

GATE_NAMES = (
    "TERMINAL_CONTINUITY_V1_QUALIFIED",
    "PHASE_A_EXACT_BOUND",
    "RUNTIME_EXACT_BOUND",
    "RECOVERY_BUNDLE_EXACT_BOUND",
    "RECEIPT_ADAPTER_INTEGRATED",
    "OPENING_RESULT_INTEGRATED",
    "CAMPAIGN_BINDING_INTEGRATED",
    "RECOVERY_LOADER_INTEGRATED",
    "EXECUTOR_IMPLEMENTED",
    "TARGET_COORDINATION_ACTIVE",
    "CROSS_CODE_COORDINATION_ACTIVE",
    "CONTRACT_ACTIVE",
    "MECHANICAL_ACTIVATION",
    "LIVE_AUTHORITY",
)

TARGET = MappingProxyType(
    {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "build": "G986NKSS8IYC2",
    }
)

PLAN_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_terminal_continuity_v1_h0_plan"
)
RECOVERY_INPUT_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_terminal_continuity_recovery_input_v1"
)
TERMINAL_CONTINUITY_SCHEMA = (
    "s20plus_g986n_autonomous_public_health_terminal_continuity_v1"
)

SOURCE_ROOT = Path(
    "/home/temmie/dev/android-native-init-lab/workspace/public/src/scripts/"
    "revalidation"
)
PHASE_A_PATH = SOURCE_ROOT / "s20plus_g986n_autonomous_public_health_campaign_v1.py"
RUNTIME_PATH = SOURCE_ROOT / "s20plus_g986n_autonomous_public_health_runtime_v1_h0.py"
RECOVERY_LOADER_PATH = (
    SOURCE_ROOT / "s20plus_g986n_autonomous_public_health_recovery_loader_v1_h0.py"
)

PINNED_IDENTITIES = MappingProxyType(
    {
        "phase_a": MappingProxyType(
            {
                "name": PHASE_A_PATH.name,
                "size": 92_607,
                "sha256": (
                    "43edcfc5bf2c69f96bcef015f305d38be9c310dd92371a2a942e075261dfa8e2"
                ),
                "normalized_sha256": (
                    "be1f73de763b7fcce8e1b74da23cb662244b7b1de9bcbb862ffa59c5c296e773"
                ),
            }
        ),
        "runtime": MappingProxyType(
            {
                "name": RUNTIME_PATH.name,
                "size": 85_645,
                "sha256": (
                    "f6644edc1f8eee80e6f9fc5e7623c96b8e58de23312e71607e51a4658d67652f"
                ),
                "normalized_sha256": (
                    "12b993c199a104c2c0f1bdb9706c179005292971428ef26317442e600eb89ac2"
                ),
            }
        ),
        "recovery_loader": MappingProxyType(
            {
                "name": RECOVERY_LOADER_PATH.name,
                "size": 35_315,
                "sha256": (
                    "a210944447dc33b7593b42ba5c46cde9561c9449e8981523b468a4121c4284cc"
                ),
                "normalized_sha256": (
                    "8df4dc534a1d4e9ac1a73867151e4bfcf2450a52283a281c7091d9c47e1e09cc"
                ),
            }
        ),
        "recovery_core": MappingProxyType(
            {
                "name": "recovery-core.py",
                "size": 162_875,
                "sha256": (
                    "94f6022aebcdc63bcad08757f493349d2e4b198610a367e72181a65694321f0b"
                ),
                "normalized_sha256": (
                    "38cb154e526e8a1a3ad38f8c857f03668f92fedced786745f5e8e85d91e21dac"
                ),
            }
        ),
        "recovery_manifest": MappingProxyType(
            {
                "name": "manifest.json",
                "size": 7_669,
                "sha256": (
                    "51931dd9a084e1c7ae8d674681d34be7bd2f50b32d8c0b84b2842d51749df593"
                ),
            }
        ),
    }
)

SELF_MAX_BYTES = 128 * 1024
PHASE_A_MAX_BYTES = 128 * 1024
RUNTIME_MAX_BYTES = 128 * 1024
EXTENDED_RECEIPT_MAX_BYTES = 8 * 1024
RECOVERY_INPUT_MAX_BYTES = 32 * 1024
HEX64_RE = re.compile(r"[0-9a-f]{64}\Z")

TERMINAL_CONTINUITY_KEYS = {
    "schema",
    "clock_sample",
    "adb_server_after",
    "usb_generation",
    "observed_after_return_retained",
}


class TerminalContinuityV1Error(RuntimeError):
    """Any drift, ambiguity, injected input, or inactive operation stops."""


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
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise TerminalContinuityV1Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise TerminalContinuityV1Error("digest input is not bytes")
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
        raise TerminalContinuityV1Error(f"{label} bytes differ or exceed cap")
    try:
        value = json.loads(
            payload.decode("ascii", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise TerminalContinuityV1Error(f"{label} is not strict JSON") from exc
    if canonical_bytes(value) != payload:
        raise TerminalContinuityV1Error(f"{label} is not exact canonical JSON")
    return value


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != expected:
        raise TerminalContinuityV1Error(f"{label} keys differ")


def _exact_equal(left: Any, right: Any) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


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


def _read_exact_file(path: Path, identity: Mapping[str, Any], maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise TerminalContinuityV1Error(f"cannot open exact source {identity['name']}") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != identity["size"]
            or before.st_size < 1
            or before.st_size > maximum
        ):
            raise TerminalContinuityV1Error(f"exact source metadata differs: {identity['name']}")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise TerminalContinuityV1Error(f"exact source length differs: {identity['name']}")
        after = os.fstat(descriptor)
        raw = bytes(payload)
        if _metadata(before) != _metadata(after) or sha256_bytes(raw) != identity["sha256"]:
            raise TerminalContinuityV1Error(f"exact source identity differs: {identity['name']}")
        return raw
    finally:
        os.close(descriptor)


def _load_phase_a() -> SimpleNamespace:
    identity = PINNED_IDENTITIES["phase_a"]
    raw = _read_exact_file(PHASE_A_PATH, identity, PHASE_A_MAX_BYTES)
    namespace: dict[str, Any] = {
        "__name__": "_exact_s20plus_public_health_phase_a",
        "__file__": str(PHASE_A_PATH),
        "__package__": None,
    }
    try:
        exec(compile(raw, str(PHASE_A_PATH), "exec"), namespace)
    except BaseException as exc:
        raise TerminalContinuityV1Error("exact Phase-A source did not load") from exc
    required = (
        "canonical_bytes",
        "sha256_bytes",
        "parse_canonical_json",
        "validate_opening_intent",
        "expected_actual_argvs",
        "parse_inventory",
        "select_target",
        "_decode_success",
        "validate_opening_command_receipt",
        "validate_health",
        "_derive_health_from_validated_returns",
        "validate_clock_sample",
        "validate_adb_server_receipt",
        "normalized_source_sha256",
    )
    if any(not callable(namespace.get(name)) for name in required):
        raise TerminalContinuityV1Error("exact Phase-A validator surface differs")
    if (
        namespace.get("EXPECTED_SELF_NORMALIZED_SHA256")
        != identity["normalized_sha256"]
        or namespace["normalized_source_sha256"](raw)
        != identity["normalized_sha256"]
        or dict(namespace.get("TARGET", {})) != dict(TARGET)
        or namespace.get("OPENING_RECEIPT_MAX_BYTES") != EXTENDED_RECEIPT_MAX_BYTES
        or namespace.get("EXPECTED_LOADER_NAME")
        != PINNED_IDENTITIES["recovery_loader"]["name"]
        or namespace.get("EXPECTED_LOADER_SIZE")
        != PINNED_IDENTITIES["recovery_loader"]["size"]
        or namespace.get("EXPECTED_LOADER_SHA256")
        != PINNED_IDENTITIES["recovery_loader"]["sha256"]
        or namespace.get("EXPECTED_LOADER_NORMALIZED_SHA256")
        != PINNED_IDENTITIES["recovery_loader"]["normalized_sha256"]
        or namespace.get("EXPECTED_CORE_NAME")
        != PINNED_IDENTITIES["recovery_core"]["name"]
        or namespace.get("EXPECTED_CORE_SIZE")
        != PINNED_IDENTITIES["recovery_core"]["size"]
        or namespace.get("EXPECTED_CORE_SHA256")
        != PINNED_IDENTITIES["recovery_core"]["sha256"]
        or namespace.get("EXPECTED_CORE_NORMALIZED_SHA256")
        != PINNED_IDENTITIES["recovery_core"]["normalized_sha256"]
        or namespace.get("EXPECTED_MANIFEST_NAME")
        != PINNED_IDENTITIES["recovery_manifest"]["name"]
        or namespace.get("EXPECTED_MANIFEST_SIZE")
        != PINNED_IDENTITIES["recovery_manifest"]["size"]
        or namespace.get("EXPECTED_MANIFEST_SHA256")
        != PINNED_IDENTITIES["recovery_manifest"]["sha256"]
    ):
        raise TerminalContinuityV1Error("exact Phase-A or recovery pins differ")
    return SimpleNamespace(**namespace)


def _load_runtime() -> ModuleType:
    identity = PINNED_IDENTITIES["runtime"]
    raw = _read_exact_file(RUNTIME_PATH, identity, RUNTIME_MAX_BYTES)
    module_name = "_exact_s20plus_public_health_runtime"
    module = ModuleType(module_name)
    module.__file__ = str(RUNTIME_PATH)
    module.__package__ = None
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(compile(raw, str(RUNTIME_PATH), "exec"), module.__dict__)
    except BaseException as exc:
        raise TerminalContinuityV1Error("exact runtime source did not load") from exc
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous
    required = ("normalized_source_sha256", "_expected_usbfs_rdev")
    if any(not callable(getattr(module, name, None)) for name in required):
        raise TerminalContinuityV1Error("exact runtime validator surface differs")
    try:
        normalized = module.normalized_source_sha256(raw)
        probe_rdev = module._expected_usbfs_rdev(1, 2)
    except BaseException as exc:
        raise TerminalContinuityV1Error("exact runtime validators rejected their pin") from exc
    if (
        getattr(module, "EXPECTED_SELF_NORMALIZED_SHA256", None)
        != identity["normalized_sha256"]
        or normalized != identity["normalized_sha256"]
        or dict(getattr(module, "TARGET", {})) != dict(TARGET)
        or getattr(module, "USBFS_MAJOR", None) != 189
        or getattr(module, "USBFS_DEVICES_PER_BUS", None) != 128
        or getattr(module, "USBFS_MAX_DEVICE_NUMBER", None) != 127
        or probe_rdev != os.makedev(189, 1)
    ):
        raise TerminalContinuityV1Error("exact runtime USB mapping or identity differs")
    return module


def _snapshot_evidence(phase_a: SimpleNamespace, evidence: Mapping[str, bytes]) -> dict[str, bytes]:
    if type(evidence) is not dict or set(evidence) != set(phase_a.OPENING_EVIDENCE_NAMES):
        raise TerminalContinuityV1Error("evidence is not the exact 19-file set")
    retained: dict[str, bytes] = {}
    for name in phase_a.OPENING_EVIDENCE_NAMES:
        value = evidence[name]
        if type(value) is not bytes:
            raise TerminalContinuityV1Error(f"retained evidence is not bytes: {name}")
        retained[name] = value
    return retained


def _selected_serial_from_cmd02(phase_a: SimpleNamespace, evidence: Mapping[str, bytes]) -> str:
    try:
        text = phase_a._decode_success(
            evidence["cmd-02.stdout.bin"],
            evidence["cmd-02.stderr.bin"],
            "retained cmd02 inventory",
        )
        selected = phase_a.select_target(phase_a.parse_inventory(text))
    except phase_a.CampaignV1Error as exc:
        raise TerminalContinuityV1Error("cmd02 does not select one exact target") from exc
    serial = selected.get("serial")
    if type(serial) is not str:
        raise TerminalContinuityV1Error("cmd02 selected serial differs")
    return serial


def _derived_health_identity(
    phase_a: SimpleNamespace, health: Mapping[str, Any]
) -> dict[str, Any]:
    identity = {
        "target": dict(TARGET),
        "serial_sha256": health["target"]["adb_serial_sha256"],
        "topology_sha256": health["target"]["usb_topology_sha256"],
        "boot_id_sha256": health["boot_id_sha256"],
        "health_verdict": health["verdict"],
    }
    _exact_keys(
        identity,
        {
            "target",
            "serial_sha256",
            "topology_sha256",
            "boot_id_sha256",
            "health_verdict",
        },
        "derived health identity",
    )
    if identity["target"] != dict(TARGET):
        raise TerminalContinuityV1Error("derived health target differs")
    for key in ("serial_sha256", "topology_sha256", "boot_id_sha256"):
        if type(identity[key]) is not str or HEX64_RE.fullmatch(identity[key]) is None:
            raise TerminalContinuityV1Error("derived health hash differs")
    if identity["health_verdict"] != phase_a.HEALTH_VERDICT:
        raise TerminalContinuityV1Error("derived health verdict differs")
    return identity


def _validate_usb_generation(
    phase_a: SimpleNamespace,
    runtime: ModuleType,
    value: Any,
    derived_health_identity: Mapping[str, Any],
) -> dict[str, Any]:
    keys = {
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
    }
    _exact_keys(value, keys, "USB generation")
    for key in (
        "sysfs_device",
        "sysfs_inode",
        "busnum",
        "devnum",
        "usbfs_device",
        "usbfs_inode",
        "usbfs_rdev",
    ):
        if type(value[key]) is not int or type(value[key]) is bool or value[key] < 0:
            raise TerminalContinuityV1Error(f"USB generation.{key} is malformed")
    if not 1 <= value["busnum"] <= 999 or not 1 <= value["devnum"] <= 127:
        raise TerminalContinuityV1Error("USB bus/device number is outside reviewed mapping")
    expected_rdev = os.makedev(
        189, (value["busnum"] - 1) * 128 + (value["devnum"] - 1)
    )
    try:
        runtime_rdev = runtime._expected_usbfs_rdev(value["busnum"], value["devnum"])
    except BaseException as exc:
        raise TerminalContinuityV1Error("exact runtime rejected USB mapping") from exc
    if (
        value["schema"] != phase_a.USB_GENERATION_SCHEMA
        or type(value["topology_sha256"]) is not str
        or HEX64_RE.fullmatch(value["topology_sha256"]) is None
        or value["topology_sha256"] != derived_health_identity["topology_sha256"]
        or value["usbfs_rdev"] != expected_rdev
        or runtime_rdev != expected_rdev
        or value["held_descriptors"] is not True
        or value["event_monitor_overflow"] is not False
        or value["generation_continuous"] is not True
    ):
        raise TerminalContinuityV1Error("USB generation is not exact runtime-mapped evidence")
    return dict(value)


def _validate_terminal_continuity(
    phase_a: SimpleNamespace,
    runtime: ModuleType,
    continuity: Any,
    intent: Mapping[str, Any],
    derived_health_identity: Mapping[str, Any],
    terminal_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    _exact_keys(continuity, TERMINAL_CONTINUITY_KEYS, "terminal continuity")
    if continuity["schema"] != TERMINAL_CONTINUITY_SCHEMA:
        raise TerminalContinuityV1Error("terminal continuity schema differs")
    if continuity["observed_after_return_retained"] is not True:
        raise TerminalContinuityV1Error("terminal continuity was not retained after return")
    try:
        clock = phase_a.validate_clock_sample(
            intent["clock_binding"], continuity["clock_sample"]
        )
        server = phase_a.validate_adb_server_receipt(continuity["adb_server_after"])
    except phase_a.CampaignV1Error as exc:
        raise TerminalContinuityV1Error("terminal clock/server proof differs") from exc
    usb = _validate_usb_generation(
        phase_a,
        runtime,
        continuity["usb_generation"],
        derived_health_identity,
    )
    if (
        not _exact_equal(server, intent["adb_server"])
        or clock["logical_sec"] != terminal_receipt["receipt_published_at"]
        or clock["logical_sec"] < terminal_receipt["return_retained_at"]
    ):
        raise TerminalContinuityV1Error(
            "terminal continuity is not the exact post-return server/clock generation"
        )
    return {
        "schema": TERMINAL_CONTINUITY_SCHEMA,
        "clock_sample": clock,
        "adb_server_after": server,
        "usb_generation": usb,
        "observed_after_return_retained": True,
    }


def _validate_evidence_inner(
    phase_a: SimpleNamespace,
    runtime: ModuleType,
    intent_raw: bytes,
    evidence: Mapping[str, bytes],
) -> dict[str, Any]:
    retained = _snapshot_evidence(phase_a, evidence)
    try:
        intent_value = phase_a.parse_canonical_json(
            intent_raw, "opening intent", phase_a.OPENING_INTENT_MAX_BYTES
        )
        intent = phase_a.validate_opening_intent(intent_value, intent_raw)
    except phase_a.CampaignV1Error as exc:
        raise TerminalContinuityV1Error("opening intent is not exact Phase-A bytes") from exc

    selected_serial = _selected_serial_from_cmd02(phase_a, retained)
    argvs = phase_a.expected_actual_argvs(selected_serial)
    predecessor = sha256_bytes(intent_raw)
    previous_time = intent["created_at"]
    deadline = intent["created_at"] + phase_a.OPENING_RECEIPT_CHAIN_MAX_SEC
    stripped_receipts: list[dict[str, Any]] = []
    extended_receipts: list[dict[str, Any]] = []
    proof_bytes = 0

    for ordinal, (template, argv) in enumerate(
        zip(phase_a.FIXED_TRANSCRIPT, argvs, strict=True), 1
    ):
        stdout = retained[f"cmd-{ordinal:02d}.stdout.bin"]
        stderr = retained[f"cmd-{ordinal:02d}.stderr.bin"]
        receipt_raw = retained[f"cmd-{ordinal:02d}.receipt.json"]
        if len(stdout) + len(stderr) > template["max_bytes"]:
            raise TerminalContinuityV1Error("opening raw pair exceeds its fixed cap")
        receipt = parse_canonical_json(
            receipt_raw, "extended opening receipt", EXTENDED_RECEIPT_MAX_BYTES
        )
        _exact_keys(
            receipt,
            set(phase_a.OPENING_RECEIPT_KEYS) | {"terminal_continuity"},
            "extended opening receipt",
        )
        base = dict(receipt)
        continuity = base.pop("terminal_continuity")
        base_raw = phase_a.canonical_bytes(base)
        try:
            phase_a.validate_opening_command_receipt(base, base_raw, template, argv)
        except phase_a.CampaignV1Error as exc:
            raise TerminalContinuityV1Error("stripped Phase-A receipt differs") from exc
        if ordinal < 6:
            if continuity is not None:
                raise TerminalContinuityV1Error("ordinals 1-5 continuity must be null")
        elif type(continuity) is not dict:
            raise TerminalContinuityV1Error("ordinal 6 continuity object is absent")
        if (
            base["predecessor_sha256"] != predecessor
            or base["execution_started_at"] < previous_time
            or base["execution_started_at"] > deadline
            or base["execution_completed_at"] > deadline
            or base["return_retained_at"] > deadline
            or base["receipt_published_at"] > deadline
            or base["stdout_size"] != len(stdout)
            or base["stdout_sha256"] != sha256_bytes(stdout)
            or base["stderr_size"] != len(stderr)
            or base["stderr_sha256"] != sha256_bytes(stderr)
            or base["clock_binding_sha256"]
            != sha256_bytes(phase_a.canonical_bytes(intent["clock_binding"]))
            or base["adb_server_sha256"]
            != sha256_bytes(phase_a.canonical_bytes(intent["adb_server"]))
        ):
            raise TerminalContinuityV1Error(
                "extended receipt predecessor, raw, clock, or server binding differs"
            )
        stripped_receipts.append(base)
        extended_receipts.append(receipt)
        predecessor = sha256_bytes(receipt_raw)
        previous_time = base["receipt_published_at"]
        proof_bytes += len(stdout) + len(stderr) + len(receipt_raw)

    try:
        health = phase_a.parse_canonical_json(
            retained["health.json"], "opening health", phase_a.OPENING_HEALTH_MAX_BYTES
        )
        phase_a.validate_health(health)
        derived_health = phase_a._derive_health_from_validated_returns(
            retained, stripped_receipts, selected_serial
        )
    except phase_a.CampaignV1Error as exc:
        raise TerminalContinuityV1Error("retained raw returns or health differ") from exc
    if (
        not _exact_equal(health, derived_health)
        or health["target"]["adb_serial_sha256"]
        != sha256_bytes(selected_serial.encode("utf-8"))
        or not _exact_equal(
            {
                key: health["host_tool"][key]
                for key in ("path", "device", "inode", "mtime_ns", "size", "sha256")
            },
            intent["adb_client"],
        )
    ):
        raise TerminalContinuityV1Error("health is not derived from retained opening bytes")
    proof_bytes += len(retained["health.json"])
    if proof_bytes > phase_a.OPENING_EVIDENCE_PROOF_MAX_BYTES:
        raise TerminalContinuityV1Error("opening evidence exceeds the fixed proof cap")

    identity = _derived_health_identity(phase_a, health)
    terminal = _validate_terminal_continuity(
        phase_a,
        runtime,
        extended_receipts[-1]["terminal_continuity"],
        intent,
        identity,
        stripped_receipts[-1],
    )
    manifest = [
        {"name": name, "size": len(retained[name]), "sha256": sha256_bytes(retained[name])}
        for name in phase_a.OPENING_EVIDENCE_NAMES
    ]
    return {
        "intent": intent,
        "selected_serial": selected_serial,
        "selected_serial_sha256": sha256_bytes(selected_serial.encode("utf-8")),
        "derived_health_identity": identity,
        "health": health,
        "terminal_continuity": terminal,
        "receipts": extended_receipts,
        "manifest": manifest,
        "actual_bytes": proof_bytes,
        "health_sha256": sha256_bytes(retained["health.json"]),
        "terminal_receipt_sha256": sha256_bytes(
            retained["cmd-06.receipt.json"]
        ),
    }


def validate_terminal_continuity_evidence(
    *, intent_raw: bytes, evidence: Mapping[str, bytes]
) -> dict[str, Any]:
    """Authenticate retained extended evidence without returning the raw serial."""

    phase_a = _load_phase_a()
    runtime = _load_runtime()
    validated = _validate_evidence_inner(phase_a, runtime, intent_raw, evidence)
    return {
        "selected_serial_sha256": validated["selected_serial_sha256"],
        "derived_health_identity": validated["derived_health_identity"],
        "foreign_guard_absence_authenticated": False,
        "source_identity_usable": False,
        "runtime_owner_observation_verified": False,
        "health_sha256": validated["health_sha256"],
        "terminal_continuity": validated["terminal_continuity"],
        "manifest": validated["manifest"],
        "actual_bytes": validated["actual_bytes"],
    }


def model_terminal_continuity_evidence(
    *,
    intent_raw: bytes,
    base_evidence: Mapping[str, bytes],
    clock_sample: Mapping[str, Any],
    adb_server_after: Mapping[str, Any],
    usb_generation: Mapping[str, Any],
) -> dict[str, bytes]:
    """Create H0 fixture bytes by adapting one exact Phase-A evidence set."""

    phase_a = _load_phase_a()
    runtime = _load_runtime()
    retained = _snapshot_evidence(phase_a, base_evidence)
    try:
        intent_value = phase_a.parse_canonical_json(
            intent_raw, "opening intent", phase_a.OPENING_INTENT_MAX_BYTES
        )
        intent = phase_a.validate_opening_intent(intent_value, intent_raw)
        selected_serial = _selected_serial_from_cmd02(phase_a, retained)
        validated_base = phase_a.validate_opening_evidence(
            intent=intent,
            intent_raw=intent_raw,
            evidence=retained,
            selected_serial=selected_serial,
        )
    except phase_a.CampaignV1Error as exc:
        raise TerminalContinuityV1Error("base evidence is not exact Phase-A evidence") from exc
    identity = _derived_health_identity(phase_a, validated_base["health"])
    terminal = _validate_terminal_continuity(
        phase_a,
        runtime,
        {
            "schema": TERMINAL_CONTINUITY_SCHEMA,
            "clock_sample": _plain(clock_sample),
            "adb_server_after": _plain(adb_server_after),
            "usb_generation": _plain(usb_generation),
            "observed_after_return_retained": True,
        },
        intent,
        identity,
        validated_base["receipts"][-1],
    )

    adapted = dict(retained)
    predecessor = sha256_bytes(intent_raw)
    argvs = phase_a.expected_actual_argvs(selected_serial)
    for ordinal, (template, argv) in enumerate(
        zip(phase_a.FIXED_TRANSCRIPT, argvs, strict=True), 1
    ):
        base = dict(validated_base["receipts"][ordinal - 1])
        base["predecessor_sha256"] = predecessor
        try:
            phase_a.validate_opening_command_receipt(
                base, phase_a.canonical_bytes(base), template, argv
            )
        except phase_a.CampaignV1Error as exc:
            raise TerminalContinuityV1Error("adapted stripped Phase-A receipt differs") from exc
        extended = dict(base)
        extended["terminal_continuity"] = terminal if ordinal == 6 else None
        raw = canonical_bytes(extended)
        if len(raw) > EXTENDED_RECEIPT_MAX_BYTES:
            raise TerminalContinuityV1Error("extended opening receipt exceeds 8 KiB")
        adapted[f"cmd-{ordinal:02d}.receipt.json"] = raw
        predecessor = sha256_bytes(raw)

    _validate_evidence_inner(phase_a, runtime, intent_raw, adapted)
    return adapted


def _derive_recovery_input_value(
    *, intent_raw: bytes, evidence: Mapping[str, bytes]
) -> dict[str, Any]:
    phase_a = _load_phase_a()
    runtime = _load_runtime()
    validated = _validate_evidence_inner(phase_a, runtime, intent_raw, evidence)
    intent = validated["intent"]
    terminal = validated["terminal_continuity"]
    retained = {
        "schema": terminal["schema"],
        "clock_sample": terminal["clock_sample"],
        "clock_sample_sha256": sha256_bytes(canonical_bytes(terminal["clock_sample"])),
        "adb_server_after": terminal["adb_server_after"],
        "adb_server_after_sha256": sha256_bytes(
            canonical_bytes(terminal["adb_server_after"])
        ),
        "usb_generation": terminal["usb_generation"],
        "usb_generation_sha256": sha256_bytes(
            canonical_bytes(terminal["usb_generation"])
        ),
        "observed_after_return_retained": True,
    }
    identity = validated["derived_health_identity"]
    manifest = validated["manifest"]
    value = {
        "schema": RECOVERY_INPUT_SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "campaign_id": intent["campaign_id"],
        "session_id": intent["session_id"],
        "opening_intent_sha256": sha256_bytes(intent_raw),
        "evidence_set_sha256": sha256_bytes(canonical_bytes(manifest)),
        "terminal_receipt_sha256": validated["terminal_receipt_sha256"],
        "health_sha256": validated["health_sha256"],
        "selected_serial_sha256": validated["selected_serial_sha256"],
        "derived_health_identity": identity,
        "derived_health_identity_sha256": sha256_bytes(canonical_bytes(identity)),
        "retained_terminal_continuity": retained,
        "foreign_guard_absence_authenticated": False,
        "source_identity_usable": False,
        "runtime_owner_observation_verified": False,
        "opening_result_integration": False,
        "campaign_binding_integration": False,
        "recovery_loader_integration": False,
        "caller_serial_accepted": False,
        "caller_clock_accepted": False,
        "caller_usb_accepted": False,
        "caller_time_accepted": False,
        "caller_path_accepted": False,
        "device_commands_authorized": False,
        "live_authority": False,
    }
    if len(canonical_bytes(value)) > RECOVERY_INPUT_MAX_BYTES:
        raise TerminalContinuityV1Error("recovery-input envelope exceeds fixed cap")
    return value


def model_recovery_input_envelope(
    *, intent_raw: bytes, evidence: Mapping[str, bytes]
) -> dict[str, Any]:
    """Derive the deterministic sanitized envelope from exactly two inputs."""

    return _derive_recovery_input_value(intent_raw=intent_raw, evidence=evidence)


def validate_recovery_input_envelope(
    value: Any,
    raw: bytes,
    *,
    intent_raw: bytes,
    evidence: Mapping[str, bytes],
) -> dict[str, Any]:
    if type(raw) is not bytes:
        raise TerminalContinuityV1Error("recovery-input envelope raw is not bytes")
    expected = _derive_recovery_input_value(intent_raw=intent_raw, evidence=evidence)
    if (
        type(value) is not dict
        or canonical_bytes(value) != raw
        or len(raw) > RECOVERY_INPUT_MAX_BYTES
        or not _exact_equal(value, expected)
    ):
        raise TerminalContinuityV1Error("recovery-input envelope bytes differ")
    return dict(value)


def _operational_gates() -> dict[str, bool]:
    return {
        "terminal_continuity_v1_qualified": TERMINAL_CONTINUITY_V1_QUALIFIED,
        "phase_a_exact_bound": PHASE_A_EXACT_BOUND,
        "runtime_exact_bound": RUNTIME_EXACT_BOUND,
        "recovery_bundle_exact_bound": RECOVERY_BUNDLE_EXACT_BOUND,
        "receipt_adapter_integrated": RECEIPT_ADAPTER_INTEGRATED,
        "opening_result_integrated": OPENING_RESULT_INTEGRATED,
        "campaign_binding_integrated": CAMPAIGN_BINDING_INTEGRATED,
        "recovery_loader_integrated": RECOVERY_LOADER_INTEGRATED,
        "executor_implemented": EXECUTOR_IMPLEMENTED,
        "target_coordination_active": TARGET_COORDINATION_ACTIVE,
        "cross_code_coordination_active": CROSS_CODE_COORDINATION_ACTIVE,
        "contract_active": CONTRACT_ACTIVE,
        "mechanical_activation": MECHANICAL_ACTIVATION,
        "live_authority": LIVE_AUTHORITY,
    }


def _require_operational_gate() -> None:
    # Pure gate: no source, path, clock, process, USB, or device observation.
    if not all(value is True for value in _operational_gates().values()):
        raise TerminalContinuityV1Error("terminal continuity adapter is inactive")


def run_terminal_continuity_adapter() -> None:
    """Future no-input entrypoint; this H0 source has no operational owner."""

    _require_operational_gate()
    raise TerminalContinuityV1Error("terminal continuity operational owner is not implemented")


def normalized_source_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise TerminalContinuityV1Error("source normalization requires bytes")
    normalized = payload
    normalized, status_count = re.subn(
        rb'^STATUS = "[A-Z0-9_]+"$',
        b'STATUS = "<REVIEWED_STATUS>"',
        normalized,
        flags=re.MULTILINE,
    )
    normalized, anchor_count = re.subn(
        rb'^EXPECTED_SELF_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_SELF_NORMALIZED_SHA256 = "<REVIEWED_SELF_ANCHOR>"',
        normalized,
        flags=re.MULTILINE,
    )
    if (status_count, anchor_count) != (1, 1):
        raise TerminalContinuityV1Error("source identity normalization is ambiguous")
    for name in GATE_NAMES:
        normalized, count = re.subn(
            rf"^{name} = (?:False|True)$".encode("ascii"),
            f"{name} = <REVIEWED_BOOLEAN>".encode("ascii"),
            normalized,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise TerminalContinuityV1Error("source gate normalization is ambiguous")
    return sha256_bytes(normalized)


def _read_self_bytes() -> bytes:
    path = Path(__file__)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > SELF_MAX_BYTES
        ):
            raise TerminalContinuityV1Error("terminal continuity source metadata differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, before.st_size - len(payload))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise TerminalContinuityV1Error("terminal continuity source length differs")
        if _metadata(before) != _metadata(os.fstat(descriptor)):
            raise TerminalContinuityV1Error("terminal continuity source changed while read")
        return bytes(payload)
    finally:
        os.close(descriptor)


def render_plan() -> dict[str, Any]:
    source = _read_self_bytes()
    normalized_sha256 = normalized_source_sha256(source)
    if normalized_sha256 != EXPECTED_SELF_NORMALIZED_SHA256:
        raise TerminalContinuityV1Error("terminal continuity normalized source differs")
    gates = _operational_gates()
    if any(gates.values()):
        raise TerminalContinuityV1Error("H0 render found an active gate")
    return {
        "schema": PLAN_SCHEMA,
        "status": STATUS,
        "target": dict(TARGET),
        "tier": "H0",
        "gates": gates,
        "self": {
            "size": len(source),
            "sha256": sha256_bytes(source),
            "normalized_sha256": normalized_sha256,
            "normalized_sha256_expected": EXPECTED_SELF_NORMALIZED_SHA256,
        },
        "pins": {name: dict(value) for name, value in PINNED_IDENTITIES.items()},
        "pin_verification_boundary": {
            "actual_source_hash_and_normalized_load_on_model_call": [
                "phase_a",
                "runtime",
            ],
            "declarative_only_not_opened_by_adapter": [
                "recovery_loader",
                "recovery_core",
                "recovery_manifest",
            ],
            "declarative_recovery_pins_prove_installed_bytes": False,
        },
        "receipt_extension": {
            "top_level_field": "terminal_continuity",
            "ordinals_1_through_5": None,
            "ordinal_6_exact_keys": sorted(TERMINAL_CONTINUITY_KEYS),
            "ordinal_6_schema": TERMINAL_CONTINUITY_SCHEMA,
            "maximum_bytes": EXTENDED_RECEIPT_MAX_BYTES,
            "predecessor_hashes_extended_raw": True,
            "stripped_base_uses_exact_phase_a_validator": True,
            "usb_runtime_mapping": {
                "busnum_min": 1,
                "busnum_max": 999,
                "devnum_min": 1,
                "devnum_max": 127,
                "usbfs_rdev": "os.makedev(189,(busnum-1)*128+(devnum-1))",
            },
        },
        "recovery_input": {
            "inputs": ["intent_raw", "evidence"],
            "serial_source": "retained-cmd-02-inventory-only",
            "raw_serial_retained": False,
            "raw_devpath_retained": False,
            "raw_boot_id_retained": False,
            "caller_serial_clock_usb_time_path": False,
            "foreign_guard_absence_authenticated": False,
            "source_identity_usable": False,
            "runtime_owner_observation_verified": False,
            "opening_result_integration": False,
            "campaign_binding_integration": False,
            "recovery_loader_integration": False,
        },
        "authority": {
            "render_only": True,
            "fixture_model_is_authority": False,
            "device_contact": False,
            "device_commands_authorized": False,
            "live_authority": False,
        },
        "cli": ["--render-plan"],
        "device_commands": [],
        "device_writes": [],
        "subprocesses": [],
        "sockets": [],
        "root_commands": [],
        "odin_invocations": [],
        "partition_transfers": [],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args(argv)
    if not args.render_plan:
        parser.error("only --render-plan is available while inactive")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
