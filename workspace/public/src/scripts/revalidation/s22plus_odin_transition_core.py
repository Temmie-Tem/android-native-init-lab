#!/usr/bin/env python3
"""Durable Odin endpoint-generation evidence for future S22+ live gates.

This module owns no target, artifact, policy, or proof verdict. It converts
bounded ``odin4 -l`` snapshots into immutable receipts and generation-bound
tickets. Target helpers retain all authorization and transfer decisions.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import s22plus_boot_only_live_core as live_core


SNAPSHOT_SCHEMA = "s22plus_odin_endpoint_snapshot_v1"
INDEX_SCHEMA = "s22plus_odin_transaction_index_v1"
PHASE_SCHEMA = "s22plus_odin_phase_receipt_v1"
ODIN_DEVICE_RE = re.compile(r"/dev/bus/usb/\d+/\d+")
RECEIPT_NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
TRANSACTION_PHASES = (
    "prepared",
    "candidate_transfer_started",
    "candidate_transfer_finished",
    "candidate_observation_closed",
    "rollback_endpoint_observed",
    "rollback_confirmed",
    "rollback_transfer_finished",
    "rollback_android_ready",
    "first_rollback_observer_captured",
    "classified",
)
MAX_ENUM_OUTPUT_BYTES = 64 * 1024
MAX_INDEX_RECORD_BYTES = 64 * 1024
MAX_INDEX_BYTES = 16 * 1024 * 1024
INDEX_RESUME_RE = re.compile(r"transaction-resume-(\d{6})\.jsonl")


class OdinTransitionError(RuntimeError):
    pass


class RunResult(Protocol):
    returncode: int
    stdout: str | bytes | None
    stderr: str | bytes | None


Runner = Callable[[list[str], float], RunResult]
DeviceIdentity = Callable[[str], str | None]


@dataclass(frozen=True)
class OdinSnapshot:
    timestamp_utc: str
    returncode: int
    raw_devices: tuple[str, ...]
    live_devices: tuple[str, ...]
    stale_devices: tuple[str, ...]
    live_device_identities: tuple[tuple[str, str], ...]
    stdout: str
    stderr: str


@dataclass(frozen=True)
class EndpointTicket:
    device: str
    device_identity: str
    generation: int
    snapshot_sequence: int
    snapshot_receipt: str
    snapshot_receipt_sha256: str


@dataclass(frozen=True)
class WaitResult:
    ticket: EndpointTicket | None
    next_sequence: int
    timed_out: bool


@dataclass(frozen=True)
class AbsenceResult:
    absent: bool
    next_sequence: int
    timed_out: bool


class EndpointGenerationTracker:
    """Assign a new generation after every observed absent-to-live transition."""

    def __init__(self) -> None:
        self._previous_live: tuple[str, ...] = ()
        self._generation = 0

    def observe(self, live_devices: tuple[str, ...]) -> int | None:
        if len(live_devices) > 1:
            raise OdinTransitionError(
                f"ambiguous live Odin endpoints: {list(live_devices)}"
            )
        if live_devices != self._previous_live:
            if live_devices:
                self._generation += 1
            self._previous_live = live_devices
        return self._generation if live_devices else None


def _default_runner(argv: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _default_device_identity(path: str) -> str | None:
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if not stat.S_ISCHR(metadata.st_mode):
        raise OdinTransitionError(f"Odin endpoint is not a character device: {path}")
    return ":".join(
        str(value)
        for value in (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_rdev,
            metadata.st_ctime_ns,
        )
    )


def enumerate_odin(
    odin: Path,
    *,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    timeout_sec: float = 10.0,
    timestamp: Callable[[], str] = live_core.utc_now,
) -> OdinSnapshot:
    """Return one bounded snapshot; stale paths are evidence, not live devices."""

    if timeout_sec <= 0:
        raise OdinTransitionError("Odin enumeration timeout must be positive")
    try:
        result = runner([str(odin), "-l"], timeout_sec)
    except (OSError, subprocess.SubprocessError) as exc:
        raise OdinTransitionError("Odin enumeration did not complete") from exc
    stdout = _as_text(result.stdout)
    stderr = _as_text(result.stderr)
    if len(stdout.encode("utf-8")) + len(stderr.encode("utf-8")) > MAX_ENUM_OUTPUT_BYTES:
        raise OdinTransitionError("Odin enumeration output exceeds bound")
    if result.returncode != 0:
        raise OdinTransitionError(
            f"Odin enumeration failed rc={result.returncode}"
        )
    raw_devices = tuple(sorted(set(ODIN_DEVICE_RE.findall(stdout + stderr))))
    identities = tuple(
        (device, identity)
        for device in raw_devices
        if (identity := device_identity(device)) is not None
    )
    live_devices = tuple(device for device, _identity in identities)
    stale_devices = tuple(device for device in raw_devices if device not in live_devices)
    return OdinSnapshot(
        timestamp_utc=timestamp(),
        returncode=result.returncode,
        raw_devices=raw_devices,
        live_devices=live_devices,
        stale_devices=stale_devices,
        live_device_identities=identities,
        stdout=stdout,
        stderr=stderr,
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_append_jsonl(path: Path, value: dict[str, Any]) -> None:
    """Append one bounded record; immutable receipts remain the trust root."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(payload) > MAX_INDEX_RECORD_BYTES:
        raise OdinTransitionError("transaction index record exceeds bound")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise OdinTransitionError(f"cannot open transaction index: {path}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OdinTransitionError(f"transaction index is not a regular file: {path}")
        if metadata.st_size + len(payload) > MAX_INDEX_BYTES:
            raise OdinTransitionError(
                f"transaction index exceeds bound: {metadata.st_size + len(payload)}"
            )
        written = os.write(descriptor, payload)
        if written != len(payload):
            raise OdinTransitionError(
                f"short transaction index append: {written} != {len(payload)}"
            )
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def read_transaction_index(path: Path) -> dict[str, Any]:
    """Parse complete records and report, but do not trust, a partial tail."""

    payload = live_core.read_stable_file(path, maximum=MAX_INDEX_BYTES)
    complete = payload.endswith(b"\n") or not payload
    chunks = payload.split(b"\n")
    if complete:
        chunks = chunks[:-1]
        partial_tail = b""
    else:
        partial_tail = chunks.pop()
    records: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        if not chunk:
            raise OdinTransitionError(f"empty transaction index record: {index}")
        try:
            record = json.loads(chunk)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OdinTransitionError(
                f"malformed transaction index record: {index}"
            ) from exc
        if not isinstance(record, dict) or record.get("schema") != INDEX_SCHEMA:
            raise OdinTransitionError(f"invalid transaction index record: {index}")
        records.append(record)
    return {
        "records": records,
        "complete": complete,
        "partial_tail_bytes": len(partial_tail),
        "partial_tail_sha256": live_core.sha256_bytes(partial_tail),
    }


def _transaction_index_paths(run_dir: Path) -> list[Path]:
    base = run_dir / "transaction.jsonl"
    paths = [base] if base.exists() else []
    resumes: list[tuple[int, Path]] = []
    for path in run_dir.glob("transaction-resume-*.jsonl"):
        match = INDEX_RESUME_RE.fullmatch(path.name)
        if match is None:
            raise OdinTransitionError(f"invalid transaction index segment: {path}")
        resumes.append((int(match.group(1)), path))
    if resumes and not paths:
        raise OdinTransitionError("transaction index resume exists without base segment")
    resumes.sort()
    numbers = [number for number, _path in resumes]
    if numbers != list(range(1, len(numbers) + 1)):
        raise OdinTransitionError(
            f"transaction index resume segments are not contiguous: {numbers}"
        )
    paths.extend(path for _number, path in resumes)
    return paths


def read_transaction_segments(run_dir: Path) -> dict[str, Any]:
    segments = []
    records: list[dict[str, Any]] = []
    for path in _transaction_index_paths(run_dir):
        parsed = read_transaction_index(path)
        segments.append(
            {
                "path": str(path),
                "complete": parsed["complete"],
                "partial_tail_bytes": parsed["partial_tail_bytes"],
                "partial_tail_sha256": parsed["partial_tail_sha256"],
                "record_count": len(parsed["records"]),
            }
        )
        records.extend(parsed["records"])
    return {"segments": segments, "records": records}


def append_transaction_record(run_dir: Path, value: dict[str, Any]) -> Path:
    """Append to the latest clean segment, or start a new one after a partial tail."""

    paths = _transaction_index_paths(run_dir)
    if not paths:
        target = run_dir / "transaction.jsonl"
    else:
        latest = paths[-1]
        parsed = read_transaction_index(latest)
        if parsed["complete"]:
            target = latest
        else:
            target = run_dir / f"transaction-resume-{len(paths):06d}.jsonl"
            if target.exists() or target.is_symlink():
                raise OdinTransitionError(
                    f"transaction index resume segment already exists: {target}"
                )
    durable_append_jsonl(target, value)
    return target


def _receipt_payload(snapshot: OdinSnapshot, sequence: int) -> dict[str, Any]:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "sequence": sequence,
        **asdict(snapshot),
    }


def persist_snapshot(run_dir: Path, sequence: int, snapshot: OdinSnapshot) -> dict[str, Any]:
    if sequence < 0:
        raise OdinTransitionError("snapshot sequence must be non-negative")
    receipt_path = run_dir / "receipts" / f"odin-snapshot-{sequence:06d}.json"
    live_core.durable_create_json(receipt_path, _receipt_payload(snapshot, sequence))
    identity = live_core.hash_stable_file(receipt_path)
    record = {
        "schema": INDEX_SCHEMA,
        "record": "odin_snapshot",
        "timestamp_utc": snapshot.timestamp_utc,
        "sequence": sequence,
        "receipt": str(receipt_path),
        "receipt_size": identity["size"],
        "receipt_sha256": identity["sha256"],
        "live_devices": list(snapshot.live_devices),
        "stale_devices": list(snapshot.stale_devices),
    }
    append_transaction_record(run_dir, record)
    return record


def create_phase_receipt(
    run_dir: Path, phase: str, payload: dict[str, Any]
) -> dict[str, Any]:
    if not RECEIPT_NAME_RE.fullmatch(phase):
        raise OdinTransitionError(f"invalid phase receipt name: {phase!r}")
    if phase not in TRANSACTION_PHASES:
        raise OdinTransitionError(f"unknown transaction phase: {phase}")
    existing_set: set[str] = set()
    for path in sorted((run_dir / "receipts").glob("phase-*.json")):
        value = json.loads(live_core.read_stable_file(path, maximum=MAX_INDEX_RECORD_BYTES))
        if not isinstance(value, dict) or value.get("schema") != PHASE_SCHEMA:
            raise OdinTransitionError(f"invalid phase receipt schema: {path}")
        existing_phase = value.get("phase")
        if existing_phase not in TRANSACTION_PHASES or existing_phase in existing_set:
            raise OdinTransitionError(f"invalid or duplicate phase receipt: {path}")
        if path.name != f"phase-{existing_phase}.json":
            raise OdinTransitionError(f"phase receipt path/payload mismatch: {path}")
        existing_set.add(existing_phase)
    existing = [value for value in TRANSACTION_PHASES if value in existing_set]
    expected = list(TRANSACTION_PHASES[: len(existing)])
    if existing != expected:
        raise OdinTransitionError(
            f"transaction phase receipts are not a valid prefix: {existing}"
        )
    if len(existing) >= len(TRANSACTION_PHASES) or phase != TRANSACTION_PHASES[len(existing)]:
        next_phase = (
            TRANSACTION_PHASES[len(existing)]
            if len(existing) < len(TRANSACTION_PHASES)
            else None
        )
        raise OdinTransitionError(
            f"out-of-order transaction phase: {phase}; expected {next_phase}"
        )
    receipt_path = run_dir / "receipts" / f"phase-{phase}.json"
    value = {
        "schema": PHASE_SCHEMA,
        "phase": phase,
        "timestamp_utc": live_core.utc_now(),
        "payload": payload,
    }
    live_core.durable_create_json(receipt_path, value)
    identity = live_core.hash_stable_file(receipt_path)
    record = {
        "schema": INDEX_SCHEMA,
        "record": "phase_receipt",
        "timestamp_utc": value["timestamp_utc"],
        "phase": phase,
        "receipt": str(receipt_path),
        "receipt_size": identity["size"],
        "receipt_sha256": identity["sha256"],
    }
    append_transaction_record(run_dir, record)
    return record


def list_snapshot_receipts(run_dir: Path) -> list[dict[str, Any]]:
    """Recover load-bearing snapshots even if the JSONL index ended early."""

    records: list[dict[str, Any]] = []
    for path in sorted((run_dir / "receipts").glob("odin-snapshot-*.json")):
        payload = json.loads(live_core.read_stable_file(path, maximum=MAX_INDEX_RECORD_BYTES))
        if not isinstance(payload, dict) or payload.get("schema") != SNAPSHOT_SCHEMA:
            raise OdinTransitionError(f"invalid snapshot receipt schema: {path}")
        sequence = payload.get("sequence")
        if not isinstance(sequence, int) or path.name != f"odin-snapshot-{sequence:06d}.json":
            raise OdinTransitionError(f"snapshot receipt path/payload mismatch: {path}")
        identity = live_core.hash_stable_file(path)
        records.append(
            {
                "path": str(path),
                "sequence": sequence,
                "size": identity["size"],
                "sha256": identity["sha256"],
                "live_devices": payload.get("live_devices"),
                "stale_devices": payload.get("stale_devices"),
            }
        )
    sequences = [record["sequence"] for record in records]
    if sequences != sorted(set(sequences)):
        raise OdinTransitionError("snapshot receipt sequence is invalid")
    return records


def _resume_tracker(
    run_dir: Path, sequence_start: int
) -> EndpointGenerationTracker:
    receipts = list_snapshot_receipts(run_dir)
    sequences = [record["sequence"] for record in receipts]
    if sequences != list(range(len(sequences))):
        raise OdinTransitionError(
            f"snapshot receipts are not contiguous from zero: {sequences}"
        )
    if sequence_start != len(receipts):
        raise OdinTransitionError(
            f"snapshot sequence resume mismatch: expected {len(receipts)}, "
            f"received {sequence_start}"
        )
    tracker = EndpointGenerationTracker()
    for record in receipts:
        live_devices = record.get("live_devices")
        if not isinstance(live_devices, list) or any(
            not isinstance(device, str) for device in live_devices
        ):
            raise OdinTransitionError(
                f"snapshot receipt has invalid live devices: {record['path']}"
            )
        tracker.observe(tuple(live_devices))
    return tracker


def _snapshot_and_record(
    odin: Path,
    run_dir: Path,
    sequence: int,
    *,
    runner: Runner,
    device_identity: DeviceIdentity,
    timestamp: Callable[[], str],
) -> tuple[OdinSnapshot, dict[str, Any]]:
    snapshot = enumerate_odin(
        odin,
        runner=runner,
        device_identity=device_identity,
        timestamp=timestamp,
    )
    return snapshot, persist_snapshot(run_dir, sequence, snapshot)


def wait_for_single_live_endpoint(
    odin: Path,
    run_dir: Path,
    *,
    timeout_sec: float,
    sequence_start: int = 0,
    poll_sec: float = 1.0,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    timestamp: Callable[[], str] = live_core.utc_now,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> WaitResult:
    if timeout_sec < 0 or poll_sec < 0:
        raise OdinTransitionError("endpoint wait bounds must be non-negative")
    deadline = monotonic() + timeout_sec
    sequence = sequence_start
    tracker = _resume_tracker(run_dir, sequence_start)
    while True:
        snapshot, record = _snapshot_and_record(
            odin,
            run_dir,
            sequence,
            runner=runner,
            device_identity=device_identity,
            timestamp=timestamp,
        )
        generation = tracker.observe(snapshot.live_devices)
        sequence += 1
        if generation is not None:
            return WaitResult(
                ticket=EndpointTicket(
                    device=snapshot.live_devices[0],
                    device_identity=snapshot.live_device_identities[0][1],
                    generation=generation,
                    snapshot_sequence=sequence - 1,
                    snapshot_receipt=record["receipt"],
                    snapshot_receipt_sha256=record["receipt_sha256"],
                ),
                next_sequence=sequence,
                timed_out=False,
            )
        if monotonic() >= deadline:
            return WaitResult(ticket=None, next_sequence=sequence, timed_out=True)
        sleep(poll_sec)


def wait_for_no_live_endpoint(
    odin: Path,
    run_dir: Path,
    *,
    timeout_sec: float,
    sequence_start: int = 0,
    poll_sec: float = 1.0,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    timestamp: Callable[[], str] = live_core.utc_now,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> AbsenceResult:
    if timeout_sec < 0 or poll_sec < 0:
        raise OdinTransitionError("disconnect wait bounds must be non-negative")
    deadline = monotonic() + timeout_sec
    sequence = sequence_start
    _resume_tracker(run_dir, sequence_start)
    while True:
        snapshot, _ = _snapshot_and_record(
            odin,
            run_dir,
            sequence,
            runner=runner,
            device_identity=device_identity,
            timestamp=timestamp,
        )
        sequence += 1
        if len(snapshot.live_devices) > 1:
            raise OdinTransitionError(
                f"ambiguous live Odin endpoints: {list(snapshot.live_devices)}"
            )
        if not snapshot.live_devices:
            return AbsenceResult(absent=True, next_sequence=sequence, timed_out=False)
        if monotonic() >= deadline:
            return AbsenceResult(absent=False, next_sequence=sequence, timed_out=True)
        sleep(poll_sec)


def revalidate_endpoint_ticket(
    odin: Path,
    run_dir: Path,
    ticket: EndpointTicket,
    *,
    sequence: int,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    timestamp: Callable[[], str] = live_core.utc_now,
) -> dict[str, Any]:
    _resume_tracker(run_dir, sequence)
    snapshot, record = _snapshot_and_record(
        odin,
        run_dir,
        sequence,
        runner=runner,
        device_identity=device_identity,
        timestamp=timestamp,
    )
    observed_identity = (
        snapshot.live_device_identities[0][1]
        if len(snapshot.live_device_identities) == 1
        else None
    )
    if (
        snapshot.live_devices != (ticket.device,)
        or observed_identity != ticket.device_identity
    ):
        raise OdinTransitionError(
            "Odin endpoint generation changed before transfer: "
            f"expected {ticket.device}/{ticket.device_identity}, observed "
            f"{list(snapshot.live_devices)}/{observed_identity}"
        )
    return {
        "device": ticket.device,
        "device_identity": ticket.device_identity,
        "generation": ticket.generation,
        "original_snapshot_sequence": ticket.snapshot_sequence,
        "revalidation_snapshot_sequence": sequence,
        "revalidation_receipt": record["receipt"],
        "revalidation_receipt_sha256": record["receipt_sha256"],
    }
