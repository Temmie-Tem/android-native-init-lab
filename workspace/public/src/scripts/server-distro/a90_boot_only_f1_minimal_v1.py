#!/usr/bin/env python3
"""Minimal reusable A90 boot-only F1 transaction.

This module intentionally contains no production device backend.  Its H0 state
machine fixes the only reusable decisions: exact target, exact candidate and
rollback bytes, one candidate attempt, one rollback attempt, no replay, and
bounded final health.  A reviewed adapter may later implement the Backend
protocol with the existing native_init_flash.py and Native serial tools.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


CAPABILITY = "A90_BOOT_ONLY_F1_MINIMAL_V1"
MANIFEST_SCHEMA = "a90-boot-only-f1-minimal-manifest-v1"
QUALIFICATION_SCHEMA = "a90-boot-only-f1-minimal-qualification-v1"
QUALIFICATION_REVIEW_SCHEMA = "a90-boot-only-f1-minimal-independent-review-v1"
PREPARED_SCHEMA = "a90-boot-only-f1-minimal-prepared-v1"
RECORD_SCHEMA = "a90-boot-only-f1-minimal-record-v1"
RESULT_SCHEMA = "a90-boot-only-f1-minimal-result-v1"
TARGET_PROFILE = "SAMSUNG_A90_5G"
V2321_ROLLBACK_PATH = (
    "/home/temmie/dev/android-native-init-lab/workspace/private/inputs/boot_images/"
    "boot_linux_v2321_usb_clean_identity_rodata.img"
)
V2321_ROLLBACK_SIZE = 60_882_944
V2321_ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
V2321_ROLLBACK_VERSION = "0.9.285"
V2321_ROLLBACK_BUILD = "v2321-usb-clean-identity-rodata"
REPO_ROOT = Path(__file__).resolve().parents[5]
RUN_ROOT = REPO_ROOT / "workspace/private/runs/a90-boot-only-f1-minimal-v1"
EXECUTION_SOURCE_RELS = (
    "workspace/public/src/scripts/revalidation/_workspace_bootstrap.py",
    "workspace/public/src/scripts/revalidation/a90_bridge.py",
    "workspace/public/src/scripts/revalidation/a90_observation_pipeline.py",
    "workspace/public/src/scripts/revalidation/a90_serial_lock.py",
    "workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py",
    "workspace/public/src/scripts/revalidation/a90ctl.py",
    "workspace/public/src/scripts/revalidation/native_init_flash.py",
    "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py",
    "workspace/public/src/scripts/server-distro/a90_boot_only_f1_adapter_v1.py",
    "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py",
)
APPROVAL_PREFIX = "A90-F1-MINIMAL-V1-APPROVE:"
LIVE_EXECUTION_ENABLED = True
_MODULE_SENTINEL = object()
MAX_JSON_BYTES = 1 << 20
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")

RECORDS = (
    "00-prepared.json",
    "10-approved.json",
    "20-candidate-intent.json",
    "21-candidate-launched.json",
    "22-candidate-result.json",
    "30-rollback-intent.json",
    "31-rollback-launched.json",
    "32-rollback-result.json",
    "40-terminal.json",
)

RECORD_KINDS = {
    "00-prepared.json": "PREPARED",
    "10-approved.json": "APPROVED",
    "20-candidate-intent.json": "CANDIDATE_INTENT",
    "21-candidate-launched.json": "CANDIDATE_LAUNCHED",
    "22-candidate-result.json": "CANDIDATE_RESULT",
    "30-rollback-intent.json": "ROLLBACK_INTENT",
    "31-rollback-launched.json": "ROLLBACK_LAUNCHED",
    "32-rollback-result.json": "ROLLBACK_RESULT",
    "40-terminal.json": "TERMINAL",
}

SUCCESS_PATH = (
    "00-prepared.json",
    "10-approved.json",
    "20-candidate-intent.json",
    "21-candidate-launched.json",
    "22-candidate-result.json",
    "40-terminal.json",
)

ROLLBACK_PATH = (
    "00-prepared.json",
    "10-approved.json",
    "20-candidate-intent.json",
    "21-candidate-launched.json",
    "22-candidate-result.json",
    "30-rollback-intent.json",
    "31-rollback-launched.json",
    "32-rollback-result.json",
    "40-terminal.json",
)


class ContractError(RuntimeError):
    """Raised before an effect or on an unprovable transition."""


def _reject_constant(_value: str) -> None:
    raise ContractError("non-finite JSON number")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON key")
        result[key] = value
    return result


def canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise ContractError("value is not canonical JSON") from exc


def parse_canonical(raw: bytes, label: str) -> Any:
    if not raw or len(raw) > MAX_JSON_BYTES or raw.endswith(b"\n"):
        raise ContractError(f"{label} byte envelope is invalid")
    try:
        value = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"{label} is not strict JSON") from exc
    if canonical_json(value) != raw:
        raise ContractError(f"{label} is not canonical JSON")
    return value


def _object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ContractError(f"{label} fields mismatch")
    return value


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value or len(value) > 256:
        raise ContractError(f"{label} is invalid")
    return value


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not canonical SHA256")
    return value


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _artifact(value: Any, label: str) -> dict[str, Any]:
    item = _object(
        value,
        {"path", "size", "sha256", "version", "build"},
        label,
    )
    path = Path(_text(item["path"], f"{label}.path"))
    if not path.is_absolute() or "/../" in f"{path}/":
        raise ContractError(f"{label}.path is not stable absolute")
    if type(item["size"]) is not int or not 1 <= item["size"] <= 128 * 1024 * 1024:
        raise ContractError(f"{label}.size is invalid")
    _sha(item["sha256"], f"{label}.sha256")
    _text(item["version"], f"{label}.version")
    _text(item["build"], f"{label}.build")
    return item


def _input(value: Any, label: str) -> dict[str, Any]:
    item = _object(value, {"path", "size", "sha256"}, label)
    path = Path(_text(item["path"], f"{label}.path"))
    if not path.is_absolute() or "/../" in f"{path}/":
        raise ContractError(f"{label}.path is not stable absolute")
    if type(item["size"]) is not int or not 1 <= item["size"] <= MAX_JSON_BYTES:
        raise ContractError(f"{label}.size is invalid")
    _sha(item["sha256"], f"{label}.sha256")
    return item


def _read_bounded_regular(path: Path, label: str, maximum: int) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != os.getuid()
        or before.st_gid != os.getgid()
        or before.st_mode & 0o022
        or not 1 <= before.st_size <= maximum
    ):
        raise ContractError(f"{label} path identity mismatch")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        current = os.fstat(descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
            or current.st_size != before.st_size
        ):
            raise ContractError(f"{label} changed before read")
        raw = bytearray()
        while len(raw) < current.st_size:
            chunk = os.pread(descriptor, current.st_size - len(raw), len(raw))
            if not chunk:
                raise ContractError(f"{label} ended during read")
            raw.extend(chunk)
        if os.pread(descriptor, 1, current.st_size):
            raise ContractError(f"{label} grew during read")
        return bytes(raw)
    finally:
        os.close(descriptor)


def validate_manifest(value: Any) -> dict[str, Any]:
    manifest = _object(
        value,
        {
            "schema",
            "capability",
            "targetProfile",
            "partition",
            "runId",
            "expectedStart",
            "candidate",
            "rollback",
            "qualification",
            "timeouts",
        },
        "manifest",
    )
    if (
        manifest["schema"] != MANIFEST_SCHEMA
        or manifest["capability"] != CAPABILITY
        or manifest["targetProfile"] != TARGET_PROFILE
        or manifest["partition"] != "boot"
    ):
        raise ContractError("manifest selected another capability or partition")
    if type(manifest["runId"]) is not str or ID_RE.fullmatch(manifest["runId"]) is None:
        raise ContractError("manifest run ID is invalid")
    expected = _object(manifest["expectedStart"], {"version", "build"}, "expectedStart")
    _text(expected["version"], "expectedStart.version")
    _text(expected["build"], "expectedStart.build")
    candidate = _artifact(manifest["candidate"], "candidate")
    rollback = _artifact(manifest["rollback"], "rollback")
    if rollback != {
        "path": V2321_ROLLBACK_PATH,
        "size": V2321_ROLLBACK_SIZE,
        "sha256": V2321_ROLLBACK_SHA256,
        "version": V2321_ROLLBACK_VERSION,
        "build": V2321_ROLLBACK_BUILD,
    }:
        raise ContractError("rollback is not the exact V2321 artifact")
    if candidate["sha256"] == rollback["sha256"] or candidate["path"] == rollback["path"]:
        raise ContractError("candidate and rollback are not distinct")
    qualification = _object(
        manifest["qualification"],
        {
            "schema",
            "candidateSha256",
            "rollbackSha256",
            "recovery",
            "hazard",
            "freshState",
            "review",
        },
        "qualification",
    )
    if qualification["schema"] != QUALIFICATION_SCHEMA:
        raise ContractError("qualification schema is invalid")
    if (
        _sha(qualification["candidateSha256"], "qualified candidate")
        != candidate["sha256"]
        or _sha(qualification["rollbackSha256"], "qualified rollback")
        != rollback["sha256"]
    ):
        raise ContractError("qualification does not bind the selected artifacts")
    recovery = _object(
        qualification["recovery"],
        {"profile", "method", "demonstrated"},
        "qualification.recovery",
    )
    if (
        recovery["profile"] != "A90_ATTENDED_PHYSICAL_RECOVERY_V1"
        or recovery["method"]
        != "NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1"
        or type(recovery["demonstrated"]) is not bool
        or recovery["demonstrated"] is not True
    ):
        raise ContractError("physical recovery qualification is not exact")
    hazard = _object(
        qualification["hazard"],
        {"id", "statementSha256", "accepted"},
        "qualification.hazard",
    )
    _text(hazard["id"], "hazard ID")
    _sha(hazard["statementSha256"], "hazard statement")
    if type(hazard["accepted"]) is not bool or hazard["accepted"] is not True:
        raise ContractError("candidate hazard was not accepted")
    fresh_state = _object(
        qualification["freshState"], {"enablePath", "latchPath"}, "fresh state"
    )
    if any(type(fresh_state[key]) is not str for key in fresh_state):
        raise ContractError("fresh state paths are not strings")
    marker_base = r"/cache/a90-auto-handoff-(phase3-minimal-[a-z0-9-]{1,48})"
    enable = re.fullmatch(marker_base + r"\.enable", fresh_state["enablePath"])
    latch = re.fullmatch(marker_base + r"\.done", fresh_state["latchPath"])
    if enable is None or latch is None or enable.group(1) != latch.group(1):
        raise ContractError("fresh state paths do not bind one enable/latch generation")
    _input(qualification["review"], "qualification review")
    timeouts = _object(manifest["timeouts"], {"flashSec", "healthSec"}, "timeouts")
    for key in ("flashSec", "healthSec"):
        if type(timeouts[key]) is not int or not 1 <= timeouts[key] <= 900:
            raise ContractError(f"timeouts.{key} is invalid")
    return manifest


def load_manifest(path: Path) -> tuple[bytes, dict[str, Any]]:
    if not path.is_absolute():
        raise ContractError("manifest path is not absolute")
    raw = _read_bounded_regular(path, "manifest", MAX_JSON_BYTES)
    return raw, validate_manifest(parse_canonical(raw, "manifest"))


def _require_manifest_pair(raw: bytes, value: dict[str, Any]) -> dict[str, Any]:
    parsed = validate_manifest(parse_canonical(raw, "manifest"))
    if canonical_json(value) != raw or value != parsed:
        raise ContractError("manifest bytes and execution object differ")
    return parsed


@dataclass
class BoundArtifact:
    path: Path
    fd: int
    receipt: dict[str, Any]

    @classmethod
    def open(cls, value: dict[str, Any], role: str) -> "BoundArtifact":
        path = Path(value["path"])
        try:
            path_metadata = path.lstat()
        except OSError as exc:
            raise ContractError(f"{role} cannot be inspected") from exc
        if (
            not stat.S_ISREG(path_metadata.st_mode)
            or path_metadata.st_nlink != 1
            or path_metadata.st_uid != os.getuid()
            or path_metadata.st_gid != os.getgid()
            or path_metadata.st_mode & 0o022
            or path_metadata.st_size != value["size"]
        ):
            raise ContractError(f"{role} path identity mismatch")
        try:
            descriptor = os.open(
                path,
                os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
            )
        except OSError as exc:
            raise ContractError(f"{role} cannot be opened") from exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or not stat.S_ISREG(path_metadata.st_mode)
                or metadata.st_nlink != 1
                or path_metadata.st_nlink != 1
                or metadata.st_uid != os.getuid()
                or metadata.st_gid != os.getgid()
                or metadata.st_mode & 0o022
                or (metadata.st_dev, metadata.st_ino)
                != (path_metadata.st_dev, path_metadata.st_ino)
                or metadata.st_size != value["size"]
            ):
                raise ContractError(f"{role} file identity mismatch")
            digest = _hash_fd(descriptor, metadata.st_size)
            if digest != value["sha256"]:
                raise ContractError(f"{role} digest mismatch")
            receipt = {
                "role": role,
                "path": str(path),
                "dev": metadata.st_dev,
                "ino": metadata.st_ino,
                "mode": metadata.st_mode,
                "uid": metadata.st_uid,
                "gid": metadata.st_gid,
                "nlink": metadata.st_nlink,
                "size": metadata.st_size,
                "sha256": digest,
            }
            return cls(path, descriptor, receipt)
        except BaseException:
            os.close(descriptor)
            raise

    def checkpoint(self) -> dict[str, Any]:
        metadata = os.fstat(self.fd)
        path_metadata = self.path.lstat()
        if (
            metadata.st_size != self.receipt["size"]
            or metadata.st_size > 128 * 1024 * 1024
        ):
            raise ContractError(f"{self.receipt['role']} size changed after binding")
        current = {
            "role": self.receipt["role"],
            "path": str(self.path),
            "dev": metadata.st_dev,
            "ino": metadata.st_ino,
            "mode": metadata.st_mode,
            "uid": metadata.st_uid,
            "gid": metadata.st_gid,
            "nlink": metadata.st_nlink,
            "size": metadata.st_size,
            "sha256": _hash_fd(self.fd, metadata.st_size),
        }
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not stat.S_ISREG(path_metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
            or current != self.receipt
        ):
            raise ContractError(f"{self.receipt['role']} changed after binding")
        return current

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def _hash_fd(descriptor: int, size: int) -> str:
    digest = hashlib.sha256()
    offset = 0
    while offset < size:
        chunk = os.pread(descriptor, min(1 << 20, size - offset), offset)
        if not chunk:
            raise ContractError("artifact ended during hash")
        digest.update(chunk)
        offset += len(chunk)
    if os.pread(descriptor, 1, size):
        raise ContractError("artifact exceeds declared size")
    return digest.hexdigest()


def _verify_input(value: dict[str, Any], label: str) -> bytes:
    item = _input(value, label)
    path = Path(item["path"])
    try:
        path_metadata = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(path_metadata.st_mode)
        or path_metadata.st_nlink != 1
        or path_metadata.st_uid != os.getuid()
        or path_metadata.st_gid != os.getgid()
        or path_metadata.st_mode & 0o022
        or path_metadata.st_size != item["size"]
    ):
        raise ContractError(f"{label} path identity mismatch")
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
    )
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
            or metadata.st_uid != os.getuid()
            or metadata.st_gid != os.getgid()
            or metadata.st_mode & 0o022
            or metadata.st_size != item["size"]
        ):
            raise ContractError(f"{label} input identity mismatch")
        raw = bytearray()
        while len(raw) < metadata.st_size:
            chunk = os.pread(
                descriptor,
                min(1 << 20, metadata.st_size - len(raw)),
                len(raw),
            )
            if not chunk:
                raise ContractError(f"{label} ended during read")
            raw.extend(chunk)
        if (
            os.pread(descriptor, 1, metadata.st_size)
            or hashlib.sha256(raw).hexdigest() != item["sha256"]
        ):
            raise ContractError(f"{label} bytes mismatch")
        return bytes(raw)
    finally:
        os.close(descriptor)


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    for relative in sorted(EXECUTION_SOURCE_RELS):
        raw = (REPO_ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_qualification_review(value: Any, manifest: dict[str, Any]) -> None:
    review = _object(
        value,
        {
            "schema", "capability", "verdict", "scope", "targetProfile",
            "executionClosureSha256", "candidateSha256", "rollbackSha256",
            "recovery", "hazard", "freshState", "findings", "contacts", "reviewer",
            "reviewDate", "liveAuthority",
        },
        "qualification review",
    )
    if (
        review["schema"] != QUALIFICATION_REVIEW_SCHEMA
        or review["capability"] != CAPABILITY
        or review["verdict"] != "PASS_GO"
        or review["scope"] != "A90_MINIMAL_BOOT_ONLY_F1_EXECUTION_AND_H27_HAZARD"
        or review["targetProfile"] != TARGET_PROFILE
        or review["executionClosureSha256"] != execution_closure_sha256()
        or review["candidateSha256"] != manifest["candidate"]["sha256"]
        or review["rollbackSha256"] != manifest["rollback"]["sha256"]
        or review["liveAuthority"] is not False
        or type(review["reviewer"]) is not str
        or not review["reviewer"]
        or type(review["reviewDate"]) is not str
        or re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", review["reviewDate"]) is None
    ):
        raise ContractError("qualification review identity or verdict is invalid")
    recovery = _object(review["recovery"], {"profile", "method", "demonstrated"}, "review recovery")
    hazard = _object(review["hazard"], {"id", "statementSha256", "accepted"}, "review hazard")
    if recovery != manifest["qualification"]["recovery"] or hazard != manifest["qualification"]["hazard"]:
        raise ContractError("qualification review does not bind recovery and hazard")
    fresh_state = _object(
        review["freshState"], {"enablePath", "latchPath"}, "review fresh state"
    )
    if fresh_state != manifest["qualification"]["freshState"]:
        raise ContractError("qualification review does not bind fresh state")
    findings = _object(review["findings"], {"high", "medium", "low"}, "review findings")
    if any(type(findings[key]) is not list or findings[key] for key in findings):
        raise ContractError("qualification review contains a material finding")
    contacts = _object(
        review["contacts"],
        {"device", "dev", "usb", "network", "workspacePrivate", "otherTargets", "writes"},
        "review contacts",
    )
    if any(type(value) is not int or value != 0 for value in contacts.values()):
        raise ContractError("qualification review contact boundary is invalid")


def _verify_qualification_inputs(manifest: dict[str, Any]) -> None:
    raw = _verify_input(manifest["qualification"]["review"], "qualification review")
    _validate_qualification_review(parse_canonical(raw, "qualification review"), manifest)


@dataclass(frozen=True)
class Snapshot:
    target_evidence_sha256: str
    boot_id: str
    version: str
    build: str
    healthy: bool
    recovery_available: bool
    recovery_evidence_sha256: str
    fresh_state_absent: bool
    other_targets_untouched: bool
    receipt_sha256: str

    def validate(self) -> None:
        _sha(self.target_evidence_sha256, "target evidence")
        _sha(self.receipt_sha256, "snapshot receipt")
        _sha(self.recovery_evidence_sha256, "snapshot recovery evidence")
        _text(self.boot_id, "boot ID")
        _text(self.version, "snapshot version")
        _text(self.build, "snapshot build")
        for value, label in (
            (self.healthy, "healthy"),
            (self.recovery_available, "recovery available"),
            (self.fresh_state_absent, "fresh state absent"),
            (self.other_targets_untouched, "other targets untouched"),
        ):
            if type(value) is not bool:
                raise ContractError(f"snapshot {label} is not boolean")

    def payload(self) -> dict[str, Any]:
        return {
            "targetEvidenceSha256": self.target_evidence_sha256,
            "bootId": self.boot_id,
            "version": self.version,
            "build": self.build,
            "healthy": self.healthy,
            "recoveryAvailable": self.recovery_available,
            "recoveryEvidenceSha256": self.recovery_evidence_sha256,
            "freshStateAbsent": self.fresh_state_absent,
            "otherTargetsUntouched": self.other_targets_untouched,
            "receiptSha256": self.receipt_sha256,
        }

    def stable_binding(self) -> dict[str, Any]:
        """Fields that must remain identical across fresh preflight reads."""
        return {
            "targetEvidenceSha256": self.target_evidence_sha256,
            "bootId": self.boot_id,
            "version": self.version,
            "build": self.build,
            "healthy": self.healthy,
            "recoveryAvailable": self.recovery_available,
            "recoveryEvidenceSha256": self.recovery_evidence_sha256,
            "freshStateAbsent": self.fresh_state_absent,
            "otherTargetsUntouched": self.other_targets_untouched,
        }


@dataclass(frozen=True)
class EffectResult:
    returncode: int
    completed: bool
    quiescent: bool
    receipt_sha256: str

    def validate(self) -> None:
        if type(self.returncode) is not int:
            raise ContractError("effect return code is invalid")
        if type(self.completed) is not bool or type(self.quiescent) is not bool:
            raise ContractError("effect flags are invalid")
        _sha(self.receipt_sha256, "effect receipt")

    def payload(self) -> dict[str, Any]:
        return {
            "returncode": self.returncode,
            "completed": self.completed,
            "quiescent": self.quiescent,
            "receiptSha256": self.receipt_sha256,
        }


class Backend(Protocol):
    def preflight(self, manifest: dict[str, Any]) -> Snapshot: ...
    def flash(self, artifact: dict[str, Any], *, rollback: bool, timeout_sec: int) -> EffectResult: ...
    def observe(
        self,
        expected: dict[str, Any],
        fresh_state: dict[str, Any],
        *,
        require_fresh_state: bool,
        timeout_sec: int,
    ) -> Snapshot: ...


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_record(run_directory: Path, name: str, value: dict[str, Any]) -> None:
    if name not in RECORDS:
        raise ContractError("record name is not allowlisted")
    raw = canonical_json(value)
    path = run_directory / name
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o600,
    )
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(descriptor, raw[offset:])
            if written <= 0:
                raise ContractError("record short write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(run_directory)


def _require_run_path(run_directory: Path, run_id: str) -> None:
    root = RUN_ROOT
    metadata = root.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o077
        or run_directory != root / run_id
    ):
        raise ContractError("run path is not the fixed private A90 namespace")


def _candidate_guard(manifest: dict[str, Any]) -> tuple[Path, bytes]:
    path = RUN_ROOT / f"candidate-{manifest['candidate']['sha256']}.guard"
    raw = canonical_json({
        "schema": "a90-boot-only-f1-candidate-guard-v1",
        "candidateSha256": manifest["candidate"]["sha256"],
        "manifestSha256": sha256_bytes(canonical_json(manifest)),
        "runId": manifest["runId"],
    })
    return path, raw


def _publish_candidate_guard(manifest: dict[str, Any]) -> None:
    path, raw = _candidate_guard(manifest)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
    except FileExistsError as exc:
        raise ContractError("candidate was already reserved or consumed") from exc
    try:
        if os.write(descriptor, raw) != len(raw):
            raise ContractError("candidate guard short write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(RUN_ROOT)


def _active_guard(manifest: dict[str, Any]) -> tuple[Path, bytes]:
    return RUN_ROOT / "active-run.guard", canonical_json({
        "schema": "a90-boot-only-f1-active-run-v1",
        "candidateSha256": manifest["candidate"]["sha256"],
        "manifestSha256": sha256_bytes(canonical_json(manifest)),
        "runId": manifest["runId"],
    })


def _publish_active_guard(manifest: dict[str, Any]) -> None:
    path, raw = _active_guard(manifest)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
    except FileExistsError as exc:
        raise ContractError("another A90 F1 transaction is active") from exc
    try:
        if os.write(descriptor, raw) != len(raw):
            raise ContractError("active guard short write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(RUN_ROOT)


def _require_active_guard(manifest: dict[str, Any]) -> None:
    path, expected = _active_guard(manifest)
    actual = _verify_input(
        {"path": str(path), "size": len(expected), "sha256": sha256_bytes(expected)},
        "active run guard",
    )
    if actual != expected:
        raise ContractError("active run guard identity mismatch")


def _release_active_guard(manifest: dict[str, Any]) -> None:
    _require_active_guard(manifest)
    path, _expected = _active_guard(manifest)
    os.unlink(path)
    _fsync_directory(RUN_ROOT)


def _require_candidate_guard(manifest: dict[str, Any]) -> None:
    path, expected = _candidate_guard(manifest)
    actual = _verify_input(
        {"path": str(path), "size": len(expected), "sha256": sha256_bytes(expected)},
        "candidate guard",
    )
    if actual != expected:
        raise ContractError("candidate guard identity mismatch")


def read_records(run_directory: Path) -> dict[str, dict[str, Any]]:
    if not run_directory.is_dir() or run_directory.is_symlink():
        raise ContractError("run directory is not direct")
    names = {entry.name for entry in run_directory.iterdir()}
    if not names.issubset(RECORDS):
        raise ContractError("run directory contains an unknown record")
    ordered_names = tuple(name for name in RECORDS if name in names)
    if not ordered_names or not any(
        ordered_names == path[: len(ordered_names)]
        for path in (SUCCESS_PATH, ROLLBACK_PATH)
    ):
        raise ContractError("journal is not an allowlisted transaction prefix")
    result: dict[str, dict[str, Any]] = {}
    manifest_sha256: str | None = None
    for name in RECORDS:
        path = run_directory / name
        if name not in names:
            continue
        value = parse_canonical(
            _read_bounded_regular(path, name, MAX_JSON_BYTES), name
        )
        item = _object(
            value,
            {"schema", "kind", "manifestSha256", "payload"},
            name,
        )
        if (
            item["schema"] != RECORD_SCHEMA
            or item["kind"] != RECORD_KINDS[name]
            or type(item["payload"]) is not dict
        ):
            raise ContractError("journal record envelope mismatch")
        current_manifest = _sha(item["manifestSha256"], "journal manifest")
        if manifest_sha256 is None:
            manifest_sha256 = current_manifest
        elif current_manifest != manifest_sha256:
            raise ContractError("journal mixes manifest identities")
        result[name] = value
    return result


def _record(kind: str, manifest_sha256: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": RECORD_SCHEMA,
        "kind": kind,
        "manifestSha256": manifest_sha256,
        "payload": payload,
    }


def approval_token(manifest_sha256: str, snapshot: Snapshot, run_id: str) -> str:
    binding = canonical_json(
        {
            "capability": CAPABILITY,
            "manifestSha256": manifest_sha256,
            "targetEvidenceSha256": snapshot.target_evidence_sha256,
            "bootId": snapshot.boot_id,
            "runId": run_id,
        }
    )
    return APPROVAL_PREFIX + sha256_bytes(binding)


def _require_start(snapshot: Snapshot, manifest: dict[str, Any]) -> None:
    snapshot.validate()
    expected = manifest["expectedStart"]
    if (
        not snapshot.healthy
        or not snapshot.recovery_available
        or not snapshot.fresh_state_absent
        or not snapshot.other_targets_untouched
        or snapshot.recovery_evidence_sha256
        != manifest["qualification"]["review"]["sha256"]
        or (snapshot.version, snapshot.build)
        != (expected["version"], expected["build"])
    ):
        raise ContractError("starting A90 is not exact, healthy, and recoverable")


def prepare(
    manifest_raw: bytes,
    manifest: dict[str, Any],
    run_directory: Path,
    backend: Backend,
) -> str:
    manifest = _require_manifest_pair(manifest_raw, manifest)
    _verify_qualification_inputs(manifest)
    _require_run_path(run_directory, manifest["runId"])
    if run_directory.exists():
        raise ContractError("run directory already exists")
    candidate = BoundArtifact.open(manifest["candidate"], "candidate")
    rollback = BoundArtifact.open(manifest["rollback"], "rollback")
    try:
        snapshot = backend.preflight(manifest)
        _require_start(snapshot, manifest)
        run_directory.mkdir(mode=0o700, parents=False)
        _fsync_directory(run_directory.parent)
        try:
            _publish_active_guard(manifest)
        except BaseException:
            run_directory.rmdir()
            _fsync_directory(run_directory.parent)
            raise
        try:
            _publish_candidate_guard(manifest)
        except BaseException:
            _release_active_guard(manifest)
            run_directory.rmdir()
            _fsync_directory(run_directory.parent)
            raise
        manifest_sha256 = sha256_bytes(manifest_raw)
        payload = {
            "schema": PREPARED_SCHEMA,
            "runId": manifest["runId"],
            "candidate": candidate.checkpoint(),
            "rollback": rollback.checkpoint(),
            "snapshot": snapshot.payload(),
        }
        publish_record(
            run_directory,
            "00-prepared.json",
            _record("PREPARED", manifest_sha256, payload),
        )
        return approval_token(manifest_sha256, snapshot, manifest["runId"])
    finally:
        candidate.close()
        rollback.close()


def _load_prepared(
    records: dict[str, dict[str, Any]], manifest_sha256: str, run_id: str
) -> dict[str, Any]:
    prepared = records.get("00-prepared.json")
    if (
        prepared is None
        or prepared.get("schema") != RECORD_SCHEMA
        or prepared.get("kind") != "PREPARED"
        or prepared.get("manifestSha256") != manifest_sha256
        or type(prepared.get("payload")) is not dict
    ):
        raise ContractError("prepared record mismatch")
    payload = _object(
        prepared["payload"],
        {"schema", "runId", "candidate", "rollback", "snapshot"},
        "prepared payload",
    )
    if payload["schema"] != PREPARED_SCHEMA or payload["runId"] != run_id:
        raise ContractError("prepared payload identity mismatch")
    return payload


def _prepared_snapshot_binding(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = _object(
        payload,
        {
            "targetEvidenceSha256",
            "bootId",
            "version",
            "build",
            "healthy",
            "recoveryAvailable",
            "recoveryEvidenceSha256",
            "freshStateAbsent",
            "otherTargetsUntouched",
            "receiptSha256",
        },
        "prepared snapshot",
    )
    _sha(snapshot["receiptSha256"], "prepared snapshot receipt")
    return {key: value for key, value in snapshot.items() if key != "receiptSha256"}


def _terminal(
    run_directory: Path,
    manifest_sha256: str,
    terminal: str,
    snapshot: Snapshot | None,
    reason: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    qualification = manifest["qualification"]
    payload = {
        "schema": RESULT_SCHEMA,
        "terminal": terminal,
        "reason": reason,
        "snapshot": None if snapshot is None else snapshot.payload(),
        "candidateReplay": False,
        "qualification": {
            "recoveryEvidenceSha256": qualification["review"]["sha256"],
            "hazardId": qualification["hazard"]["id"],
            "hazardAccepted": qualification["hazard"]["accepted"],
        },
    }
    publish_record(
        run_directory,
        "40-terminal.json",
        _record("TERMINAL", manifest_sha256, payload),
    )
    if terminal in {"PASS_A90_RESIDENT_INSTALLED", "NO_PROOF_ROLLED_BACK"}:
        _release_active_guard(manifest)
    return payload


def execute(
    manifest_raw: bytes,
    manifest: dict[str, Any],
    run_directory: Path,
    supplied_approval: str,
    backend: Backend,
) -> dict[str, Any]:
    manifest = _require_manifest_pair(manifest_raw, manifest)
    _verify_qualification_inputs(manifest)
    _require_run_path(run_directory, manifest["runId"])
    _require_candidate_guard(manifest)
    _require_active_guard(manifest)
    records = read_records(run_directory)
    if set(records) != {"00-prepared.json"}:
        raise ContractError("execute requires one fresh prepared run")
    manifest_sha256 = sha256_bytes(manifest_raw)
    prepared = _load_prepared(records, manifest_sha256, manifest["runId"])
    candidate = BoundArtifact.open(manifest["candidate"], "candidate")
    rollback = BoundArtifact.open(manifest["rollback"], "rollback")
    try:
        snapshot = backend.preflight(manifest)
        _require_start(snapshot, manifest)
        if snapshot.stable_binding() != _prepared_snapshot_binding(prepared["snapshot"]):
            raise ContractError("prepared target or boot changed")
        if (
            candidate.checkpoint() != prepared["candidate"]
            or rollback.checkpoint() != prepared["rollback"]
        ):
            raise ContractError("prepared artifact changed")
        _verify_qualification_inputs(manifest)
        expected_approval = approval_token(
            manifest_sha256, snapshot, manifest["runId"]
        )
        if supplied_approval != expected_approval:
            raise ContractError("approval does not bind this target, boot, and manifest")
        publish_record(
            run_directory,
            "10-approved.json",
            _record(
                "APPROVED",
                manifest_sha256,
                {"approvalSha256": sha256_bytes(supplied_approval.encode("ascii"))},
            ),
        )
        publish_record(
            run_directory,
            "20-candidate-intent.json",
            _record(
                "CANDIDATE_INTENT",
                manifest_sha256,
                {"sha256": manifest["candidate"]["sha256"]},
            ),
        )
        candidate.checkpoint()
        publish_record(
            run_directory,
            "21-candidate-launched.json",
            _record("CANDIDATE_LAUNCHED", manifest_sha256, {"attempt": 1}),
        )
        candidate_result = backend.flash(
            manifest["candidate"],
            rollback=False,
            timeout_sec=manifest["timeouts"]["flashSec"],
        )
        candidate_result.validate()
        candidate.checkpoint()
        publish_record(
            run_directory,
            "22-candidate-result.json",
            _record("CANDIDATE_RESULT", manifest_sha256, candidate_result.payload()),
        )
        if not candidate_result.quiescent:
            return _terminal(
                run_directory,
                manifest_sha256,
                "RECOVERY_REQUIRED",
                None,
                "CANDIDATE_HELPER_NOT_QUIESCENT",
                manifest,
            )
        try:
            observed = backend.observe(
                manifest["candidate"],
                manifest["qualification"]["freshState"],
                require_fresh_state=True,
                timeout_sec=manifest["timeouts"]["healthSec"],
            )
            observed.validate()
        except Exception:
            observed = None
        if (
            observed is not None
            and candidate_result.completed
            and candidate_result.returncode == 0
            and observed.healthy
            and observed.recovery_available
            and observed.fresh_state_absent
            and observed.other_targets_untouched
            and (observed.version, observed.build)
            == (manifest["candidate"]["version"], manifest["candidate"]["build"])
        ):
            return _terminal(
                run_directory,
                manifest_sha256,
                "PASS_A90_RESIDENT_INSTALLED",
                observed,
                "CANDIDATE_HEALTHY",
                manifest,
            )

        publish_record(
            run_directory,
            "30-rollback-intent.json",
            _record("ROLLBACK_INTENT", manifest_sha256, {"sha256": manifest["rollback"]["sha256"]}),
        )
        rollback.checkpoint()
        publish_record(
            run_directory,
            "31-rollback-launched.json",
            _record("ROLLBACK_LAUNCHED", manifest_sha256, {"attempt": 1}),
        )
        rollback_result = backend.flash(
            manifest["rollback"],
            rollback=True,
            timeout_sec=manifest["timeouts"]["flashSec"],
        )
        rollback_result.validate()
        rollback.checkpoint()
        publish_record(
            run_directory,
            "32-rollback-result.json",
            _record("ROLLBACK_RESULT", manifest_sha256, rollback_result.payload()),
        )
        if not rollback_result.quiescent:
            return _terminal(
                run_directory,
                manifest_sha256,
                "RECOVERY_REQUIRED",
                None,
                "ROLLBACK_HELPER_NOT_QUIESCENT",
                manifest,
            )
        try:
            recovered = backend.observe(
                manifest["rollback"],
                manifest["qualification"]["freshState"],
                require_fresh_state=False,
                timeout_sec=manifest["timeouts"]["healthSec"],
            )
            recovered.validate()
        except Exception:
            recovered = None
        if (
            recovered is not None
            and rollback_result.completed
            and rollback_result.returncode == 0
            and recovered.healthy
            and recovered.recovery_available
            and recovered.other_targets_untouched
            and (recovered.version, recovered.build)
            == (manifest["rollback"]["version"], manifest["rollback"]["build"])
        ):
            return _terminal(
                run_directory,
                manifest_sha256,
                "NO_PROOF_ROLLED_BACK",
                recovered,
                "ROLLBACK_HEALTHY",
                manifest,
            )
        return _terminal(
            run_directory,
            manifest_sha256,
            "RECOVERY_REQUIRED",
            recovered,
            "ROLLBACK_HEALTH_UNPROVED",
            manifest,
        )
    finally:
        candidate.close()
        rollback.close()


def recovery_decision(run_directory: Path) -> str:
    records = read_records(run_directory)
    names = set(records)
    if "40-terminal.json" in names:
        return "TERMINAL_COMPLETE"
    if "31-rollback-launched.json" in names:
        return "PARK_ROLLBACK_NO_REPLAY"
    if "30-rollback-intent.json" in names:
        return "SAME_ROLLBACK_MAY_LAUNCH_ONCE"
    if "20-candidate-intent.json" in names:
        return "CANDIDATE_CONSUMED_ROLLBACK_ONLY"
    if names.issubset({"00-prepared.json", "10-approved.json"}):
        return "PRE_EFFECT_NO_DEVICE_EFFECT"
    raise ContractError("journal prefix is not recoverable")


def ensure_run_root() -> None:
    if not RUN_ROOT.exists():
        RUN_ROOT.mkdir(mode=0o700, parents=False)
        _fsync_directory(RUN_ROOT.parent)
    metadata = RUN_ROOT.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o077
    ):
        raise ContractError("fixed A90 run root is not private and direct")


def _live_backend(manifest: dict[str, Any], phase: str) -> Backend:
    if LIVE_EXECUTION_ENABLED is not True:
        raise ContractError("minimal F1 execution is disabled")
    canonical_name = "a90_boot_only_f1_minimal_v1"
    current_module = sys.modules.get(__name__)
    if (
        current_module is None
        or current_module.__dict__.get("_MODULE_SENTINEL") is not _MODULE_SENTINEL
    ):
        raise ContractError("running minimal F1 module identity is not canonical")
    canonical_module = sys.modules.get(canonical_name)
    if canonical_module is not None and canonical_module is not current_module:
        raise ContractError("another minimal F1 module identity is already loaded")
    sys.modules[canonical_name] = current_module
    adapter_name = "a90_boot_only_f1_adapter_v1"
    adapter_path = Path(__file__).resolve().with_name(f"{adapter_name}.py")
    adapter = sys.modules.get(adapter_name)
    if adapter is None:
        specification = importlib.util.spec_from_file_location(adapter_name, adapter_path)
        if specification is None or specification.loader is None:
            raise ContractError("minimal F1 adapter import specification failed")
        adapter = importlib.util.module_from_spec(specification)
        sys.modules[adapter_name] = adapter
        try:
            specification.loader.exec_module(adapter)
        except BaseException:
            sys.modules.pop(adapter_name, None)
            raise
    if (
        Path(getattr(adapter, "__file__", "")).resolve() != adapter_path
        or getattr(adapter, "MINIMAL_MODULE_SENTINEL", None) is not _MODULE_SENTINEL
        or adapter.ContractError is not ContractError
        or adapter.Snapshot is not Snapshot
        or adapter.EffectResult is not EffectResult
    ):
        raise ContractError("loaded minimal F1 adapter identity is not exact")
    if adapter.LIVE_ADAPTER_ENABLED is not True:
        raise ContractError("minimal F1 adapter is disabled")
    prefix = f"{manifest['runId']}-{phase}-"
    pattern = re.compile(re.escape(prefix) + r"([1-9][0-9]*)-logs")
    ordinals = [
        int(match.group(1))
        for entry in RUN_ROOT.iterdir()
        if (match := pattern.fullmatch(entry.name)) is not None
    ]
    ordinal = max(ordinals, default=0) + 1
    for _attempt in range(8):
        log_directory = RUN_ROOT / f"{prefix}{ordinal}-logs"
        try:
            runner = adapter.HostRunner(log_directory)
            return adapter.FixedA90Adapter(
                runner, qualification=manifest["qualification"]
            )
        except ContractError as exc:
            if "already exists" not in str(exc):
                raise
            ordinal += 1
    raise ContractError("could not reserve a unique adapter log ordinal")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="action", required=True)
    validate = subparsers.add_parser("validate-manifest")
    validate.add_argument("manifest", type=Path)
    audit = subparsers.add_parser("audit")
    audit.add_argument("run_id")
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("manifest", type=Path)
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("manifest", type=Path)
    execute_parser.add_argument("--approval", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.action == "validate-manifest":
        raw, manifest = load_manifest(args.manifest)
        print(
            json.dumps(
                {
                    "status": "VALID_H0_MINIMAL_MANIFEST",
                    "manifestSha256": sha256_bytes(raw),
                    "runId": manifest["runId"],
                    "liveExecutionEnabled": LIVE_EXECUTION_ENABLED,
                },
                sort_keys=True,
            )
        )
        return 0
    if args.action == "audit":
        if ID_RE.fullmatch(args.run_id) is None:
            raise ContractError("audit run ID is invalid")
        ensure_run_root()
        print(json.dumps({"decision": recovery_decision(RUN_ROOT / args.run_id)}, sort_keys=True))
        return 0
    if args.action in {"prepare", "execute"}:
        raw, manifest = load_manifest(args.manifest)
        ensure_run_root()
        run_directory = RUN_ROOT / manifest["runId"]
        backend = _live_backend(manifest, args.action)
        if args.action == "prepare":
            token = prepare(raw, manifest, run_directory, backend)
            print(json.dumps({"approval": token, "runId": manifest["runId"]}, sort_keys=True))
            return 0
        result = execute(
            raw, manifest, run_directory, args.approval, backend
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    raise ContractError("unknown action")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"A90_BOOT_ONLY_F1_MINIMAL_V1 NO_GO: {exc}", file=os.sys.stderr)
        raise SystemExit(2) from exc
