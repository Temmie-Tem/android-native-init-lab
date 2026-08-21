#!/usr/bin/env python3
"""Host-only validator for the fixed A90 H30 pre-write failure.

This is deliberately a receipt validator, not a recovery or retry owner.  It
accepts no caller-selected path or run, contacts no device, publishes no
journal record, and never removes either retained guard.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import a90_boot_only_f1_minimal_v1 as owner
import a90_boot_only_f1_adapter_v1 as adapter


SCHEMA = "a90-h30-prewrite-reconciliation-v1"
DECISION = "PREWRITE_ABORTED_NO_BOOT_WRITE"
RUN_ID = "a90-h30-f1-20260821-01"
RUN_DIRECTORY = owner.RUN_ROOT / RUN_ID
LOG_DIRECTORY = owner.RUN_ROOT / f"{RUN_ID}-execute-1-logs"
MANIFEST_SHA256 = "2a14c8be2486f0da4cd8cf364529c5b5ce84d5ca7085d929a4c61db97263a81d"
RECORD_HASHES = {
    "00-prepared.json": "2ced1331453483c56e8cb728da10da12e49615f1574d56183f1ca4ea0adbf6ab",
    "10-approved.json": "52ae4a9fe15b017f52afbe7fdbedc01c5b2253895caf6246ac54ee0ce4133589",
    "20-candidate-intent.json": "7fd8a00b2e3d43097a7833f6d51b9a41526ad3cb053ee1fd1ec9de42336e8393",
    "21-candidate-launched.json": "0b3f71ec97c9fb9eb1103b83ceab5f9836448223e1d95535b98c6317c988a00d",
    "22-candidate-result.json": "42c41b678821958e2e5aed10d854c939b58d8db53b3dafe7119eb39b6821cfaf",
    "30-rollback-intent.json": "70b58e8d725ad4df97f3b169e1f1729f89a9e9377cfc17fa1437a137240a675e",
    "31-rollback-launched.json": "12a9e8091c523f5cd11ed3614ab6dda33f1654d2c8ad20e2e0be983b3ddb6f80",
    "32-rollback-result.json": "dadb495602e6c49f494d23f0d21199bf1135fcf8865a4cb44948bbc226ac50b3",
    "40-terminal.json": "6591783fbd0b950e7c59f8d32a149d3bfe1a8b26df0c83e47744521a715c9a63",
}
EFFECT_LOG_HASHES = {
    "010-flash-candidate.stdout": "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24",
    "010-flash-candidate.stderr": "1d6ce416b5b47c1e3c03d71bfebe8cd09ad88f2e0696150b38f80b32e9c22366",
    "020-flash-rollback.stdout": "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24",
    "020-flash-rollback.stderr": "0658003a67cad391ba0396494ce8f0dc9a0a7a3f9778fa3b53b959eee17ce78b",
}
RECOVERY_RECORD_HASH = "b4d01a63c316b3f767dc8e76fab9a38dd4e6afbf14b52b8ad44579942d0070a4"
CURRENT_RECOVERY_REVIEW_SHA256 = (
    "660c7e8522343029449a739da233e8c516e20c876a9d4caa3d7a41371685f369"
)
FORBIDDEN_STAGES = (
    "sealed local image copy:",
    "phase.native_init_flash.adb_push.",
    "phase.native_init_flash.remote_sha256.",
    "phase.native_init_flash.flash_boot_image.",
    "phase.native_init_flash.boot_dd_write.",
    "phase.native_init_flash.boot_readback_sha256.",
    "remote image sha256:",
    "boot block prefix sha256:",
    "requesting system boot through TWRP",
)


class ContractError(RuntimeError):
    pass


def _read(path: Path, label: str, maximum: int = adapter.MAX_OUTPUT_BYTES) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o022
        or metadata.st_size > maximum
    ):
        raise ContractError(f"{label} identity is not exact")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        current = os.fstat(descriptor)
        if (
            (current.st_dev, current.st_ino, current.st_size)
            != (metadata.st_dev, metadata.st_ino, metadata.st_size)
        ):
            raise ContractError(f"{label} changed before read")
        raw = os.pread(descriptor, current.st_size, 0)
        if len(raw) != current.st_size or os.pread(descriptor, 1, current.st_size):
            raise ContractError(f"{label} changed during read")
        return raw
    finally:
        os.close(descriptor)


def _sha(raw: bytes) -> str:
    return owner.sha256_bytes(raw)


def _require_records() -> tuple[dict[str, dict[str, Any]], bool]:
    try:
        records = owner.read_records(RUN_DIRECTORY)
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    closed = tuple(records) == owner.POSTROLLBACK_RECOVERY_PATH
    if tuple(records) not in (owner.ROLLBACK_PATH, owner.POSTROLLBACK_RECOVERY_PATH):
        raise ContractError("H30 journal is not the fixed rollback or recovery prefix")
    for name, expected in RECORD_HASHES.items():
        record = records.get(name)
        if (
            type(record) is not dict
            or _sha(owner.canonical_json(record)) != expected
            or record.get("manifestSha256") != MANIFEST_SHA256
        ):
            raise ContractError(f"fixed H30 record changed: {name}")
    if records["20-candidate-intent.json"]["payload"] != {
        "sha256": "d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe"
    }:
        raise ContractError("H30 candidate intent changed")
    if records["30-rollback-intent.json"]["payload"] != {
        "sha256": owner.V2321_ROLLBACK_SHA256
    }:
        raise ContractError("H30 rollback intent changed")
    for name in ("22-candidate-result.json", "32-rollback-result.json"):
        if records[name]["payload"] != {
            "completed": False,
            "outcome": "PRE_WRITE_FAILURE",
            "quiescent": True,
            "returncode": 1,
            "receiptSha256": (
                "dd79dd85df5018246ed3e91d55a0d407470e5beee4e54f30cae617b323832001"
                if name.startswith("22")
                else "ec14176932058746a582b5c528cf2e08f7f3a61922459d10117d05e27f66736d"
            ),
        }:
            raise ContractError(f"{name} is not the fixed PRE_WRITE_FAILURE")
    terminal = records["40-terminal.json"]["payload"]
    if (
        terminal.get("terminal") != "RECOVERY_REQUIRED"
        or terminal.get("reason") != "ROLLBACK_HEALTH_UNPROVED"
        or terminal.get("candidateReplay") is not False
    ):
        raise ContractError("H30 terminal changed")
    if closed:
        recovery = records["41-recovery-closed.json"]
        if _sha(owner.canonical_json(recovery)) != RECOVERY_RECORD_HASH:
            raise ContractError("H30 recovery closure changed")
        payload = recovery["payload"]
        snapshot = payload.get("recoveredSnapshot")
        if (
            payload.get("schema") != "a90-f1-postrollback-recovery-v1"
            or payload.get("decision")
            != "V2321_HEALTHY_EXTERNAL_ROLLBACK_OUTCOME_UNPROVED"
            or payload.get("candidateReplay") is not False
            or payload.get("rollbackReplay") is not False
            or payload.get("rollbackOutcome") != "UNPROVED_EXTERNAL_CONTINUATION"
            or payload.get("currentReviewSha256") != CURRENT_RECOVERY_REVIEW_SHA256
            or type(snapshot) is not dict
            or snapshot.get("version") != owner.V2321_ROLLBACK_VERSION
            or snapshot.get("build") != owner.V2321_ROLLBACK_BUILD
            or snapshot.get("healthy") is not True
            or snapshot.get("otherTargetsUntouched") is not True
            or snapshot.get("freshStateObserved") is not False
            or snapshot.get("freshStateAbsent") is not False
            or payload.get("recoveredSnapshotSha256")
            != _sha(owner.canonical_json(snapshot))
        ):
            raise ContractError("H30 recovery closure is not exact")
    return records, closed


def _require_effect_logs() -> None:
    for name, expected in EFFECT_LOG_HASHES.items():
        raw = _read(LOG_DIRECTORY / name, name)
        if _sha(raw) != expected:
            raise ContractError(f"fixed H30 effect log changed: {name}")
        if name.endswith(".stdout"):
            try:
                value = adapter._json(raw, name)
            except adapter.ContractError as exc:
                raise ContractError(str(exc)) from exc
            if adapter._parse_owner_effect_receipt(raw) != "PRE_WRITE_FAILURE":
                raise ContractError(f"{name} is not the fixed owner receipt")
            if value.get("writeStarted") is not False or value.get(
                "bootWrittenReadbackExact"
            ) is not False:
                raise ContractError(f"{name} contains a write stage")
        else:
            text = raw.decode("utf-8")
            if "local image size:" not in text or "local image sha256:" not in text:
                raise ContractError(f"{name} lacks fixed local inspection")
            if "phase.native_init_flash.inspect_local_image." not in text:
                raise ContractError(f"{name} lacks local inspection phase")
            if any(stage in text for stage in FORBIDDEN_STAGES):
                raise ContractError(f"{name} contains a transfer stage")


def reconcile() -> dict[str, Any]:
    _records, closed = _require_records()
    _require_effect_logs()
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "candidateReplay": False,
        "rollbackReplay": False,
        "candidateWriteCount": 0,
        "rollbackWriteCount": 0,
        "guards": (
            "candidate-retained-active-released" if closed else "retained"
        ),
        "deviceContact": False,
        "durableJournalPublication": closed,
        "reviewRequiredBeforeClosure": not closed,
    }


def main() -> int:
    print(json.dumps(reconcile(), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, owner.ContractError, adapter.ContractError) as exc:
        print(f"A90_H30_PREWRITE_RECONCILE_V1 NO_GO: {exc}", file=os.sys.stderr)
        raise SystemExit(2) from exc
