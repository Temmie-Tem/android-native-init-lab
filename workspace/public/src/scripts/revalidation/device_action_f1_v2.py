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
from s22plus_boot_only_f1_transport import (
    BOOT_MEMBER,
    F1TransportError,
    pin_boot_only_ap,
    pin_regular_file,
)


RUNNER_VERSION = "device-action-f1-v2-host-core-1"
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
MAX_RECORD = 32 * 1024

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
    "APPROVED": {"DOWNLOAD_IDENTIFIED", "ABORTED"},
    "DOWNLOAD_IDENTIFIED": {"CANDIDATE_FLASHED", "ABORTED"},
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
    observation = _exact(manifest["observation"], {"timeout_sec", "acceptance"}, "observation")
    if isinstance(observation["timeout_sec"], bool) or not isinstance(observation["timeout_sec"], int) or not 1 <= observation["timeout_sec"] <= 600:
        raise F1V2Error("observation timeout is invalid")
    try:
        typed_evidence.validate_acceptance(observation["acceptance"])
    except typed_evidence.EvidenceError as exc:
        raise F1V2Error(str(exc)) from exc
    if manifest["final_health_profile"] != profile["health_profile_id"] or manifest["runner_version"] != RUNNER_VERSION:
        raise F1V2Error("manifest health profile or runner version mismatch")
    return manifest


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


def verify_bundle(root: Path, manifest_path: Path) -> Bundle:
    root = root.resolve()
    manifest_file = manifest_path if manifest_path.is_absolute() else root / manifest_path
    manifest_raw, manifest_receipt = load_json(manifest_file, "candidate manifest")
    profile_file = _repo_path(root, manifest_raw.get("target_profile", ""), "target_profile")
    profile_raw, profile_receipt = load_json(profile_file, "target profile")
    profile = validate_profile(profile_raw)
    manifest = validate_manifest(manifest_raw, profile)
    receipts: dict[str, Any] = {}
    for label, item in (("candidate_ap", manifest["candidate_ap"]), ("rollback_ap", manifest["rollback_ap"])):
        with pin_boot_only_ap(
            _artifact_path(root, item, label),
            label=label,
            expected_size=item["size"],
            expected_sha256=item["sha256"],
        ) as pinned:
            receipts[label] = pinned.receipt()
    acceptance = manifest["observation"]["acceptance"]
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
            )
        except typed_evidence.EvidenceError as exc:
            raise F1V2Error(str(exc)) from exc
        receipts["observation_contract"] = {
            "artifacts": contract_receipts,
            "verification": verification,
        }
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
    runner_receipt = _stable_read(Path(__file__).resolve(), "F1 v2 runner")[1]
    evidence_receipt = _stable_read(
        Path(typed_evidence.__file__).resolve(), "typed evidence runner"
    )[1]
    checkpoint_receipt = _stable_read(
        Path(typed_evidence.checkpoint.__file__).resolve(), "checkpoint decoder"
    )[1]
    transport_receipt = _stable_read(
        Path(__file__).with_name("s22plus_boot_only_f1_transport.py").resolve(),
        "regular-path transport",
    )[1]
    receipt = {
        "schema": "device_action_f1_validated_bundle_v2",
        "runner_version": RUNNER_VERSION,
        "profile": profile_receipt,
        "manifest": manifest_receipt,
        **receipts,
        "execution_critical_sources": {
            "runner": runner_receipt,
            "typed_evidence": evidence_receipt,
            "checkpoint_decoder": checkpoint_receipt,
            "regular_path_transport": transport_receipt,
        },
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


def _write_exclusive(path: Path, value: Any) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(payload) > MAX_RECORD:
        raise F1V2Error("durable record exceeds its bound")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        if os.write(descriptor, payload) != len(payload):
            raise F1V2Error("short durable record write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


def _write_atomic(path: Path, value: Any) -> None:
    if path.is_symlink():
        raise F1V2Error("durable head cannot be a symlink")
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    _write_exclusive(temporary, value)
    os.replace(temporary, path)
    _fsync_dir(path.parent)


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
                if len(events) >= len(TIMELINE) or TIMELINE[len(events)] != value["action"]:
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
                checkpoint_attempts[record["action"]] = record["details"]["attempt"]
        if kind == "transition":
            if state not in NEXT_STATES[current] or action != STATE_ACTION[state]:
                raise F1V2Error(f"invalid transition: {current} -> {state}")
        elif kind == "event":
            if (
                len(events) >= len(TIMELINE)
                or state != current
                or EVENT_STATE.get(action) != state
                or TIMELINE[len(events)] != action
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
