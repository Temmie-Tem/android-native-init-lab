#!/usr/bin/env python3
"""Durable Odin endpoint-generation evidence for future S22+ live gates.

This module owns no target, artifact, policy, or proof verdict. It converts
bounded ``odin4 -l`` snapshots into exclusive-create, crash-durable receipts
and generation-bound tickets. Target helpers retain all authorization and
transfer decisions. The host run directory is trusted storage, not a defense
against a malicious owner who can rewrite repository files.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import re
import stat
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Protocol

import s22plus_boot_only_live_core as live_core
import device_action_raw_capture_v1 as raw_capture
import s22plus_odin_usbfs_identity as usbfs_identity


SNAPSHOT_SCHEMA_V1 = "s22plus_odin_endpoint_snapshot_v1"
SNAPSHOT_SCHEMA_V2 = "s22plus_odin_endpoint_snapshot_v2"
SNAPSHOT_SCHEMA = "s22plus_odin_endpoint_snapshot_v3"
INDEX_SCHEMA = "s22plus_odin_transaction_index_v1"
PHASE_SCHEMA = "s22plus_odin_phase_receipt_v1"
ODIN_DEVICE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])/dev/bus/usb/[0-9]{3}/[0-9]{3}(?![A-Za-z0-9_./-])"
)
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
MAX_INDEX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_RECEIPT_BYTES = 512 * 1024
MAX_INDEX_SEGMENTS = 64
MAX_SNAPSHOT_RECEIPTS = 4096
MAX_DIAGNOSTIC_RECEIPTS = 64
DEFAULT_ENUM_TIMEOUT_SEC = 10.0
INDEX_RESUME_RE = re.compile(r"transaction-resume-(\d{6})\.jsonl")
DIAGNOSTIC_SCHEMA = "s22plus_odin_diagnostic_failure_v1"
DIAGNOSTIC_OBSERVATION_STAGE = "enumeration-evidence-before-snapshot"
DIAGNOSTIC_FAILURE_CLASSES = {
    "inventory-membership-changed": "UsbfsInventoryMembershipChanged",
    "usbfs-identity-failed": "UsbfsIdentityError",
    "direct-io-failed": "OSError",
}


class OdinTransitionError(RuntimeError):
    pass


class OdinEndpointArrivalRace(OdinTransitionError):
    """The endpoint appeared between inventory capture and Odin enumeration."""


class OdinMeasuredEvidenceFailure(OdinTransitionError):
    """Allowlisted final-evidence failure, before any snapshot is persisted."""

    def __init__(
        self,
        failure_kind: str,
        inner_exception_class: str,
        *,
        removed: tuple[str, ...] = (),
        added: tuple[str, ...] = (),
    ):
        if (
            DIAGNOSTIC_FAILURE_CLASSES.get(failure_kind) != inner_exception_class
            or not isinstance(removed, tuple)
            or not isinstance(added, tuple)
            or any(not isinstance(path, str) for path in (*removed, *added))
            or removed != tuple(sorted(set(removed)))
            or added != tuple(sorted(set(added)))
            or set(removed) & set(added)
            or len(removed) + len(added)
            > usbfs_identity.MAX_INVENTORY_ENTRIES
            or (
                failure_kind != "inventory-membership-changed"
                and (removed or added)
            )
        ):
            raise OdinTransitionError("measured USB endpoint failure is invalid")
        for path in (*removed, *added):
            usbfs_identity._validated_usbfs_coordinates(path)
        super().__init__("measured USB endpoint evidence failed")
        self.observation_stage = DIAGNOSTIC_OBSERVATION_STAGE
        self.failure_kind = failure_kind
        self.inner_exception_class = inner_exception_class
        self.removed = removed
        self.added = added


class RunResult(Protocol):
    returncode: int
    stdout: str | bytes | None
    stderr: str | bytes | None


@dataclass(frozen=True)
class RawRunResult:
    handle: raw_capture.RawCaptureHandle


Runner = Callable[[list[str], float], RunResult | RawRunResult]
DeviceIdentity = Callable[[str], str | None]
DeviceInventory = Callable[[], dict[str, str]]


class EndpointIdentityObserver(Protocol):
    def inventory(self) -> dict[str, str]: ...

    def identity(self, path: str) -> str | None: ...

    def evidence(self, live_devices: tuple[str, ...]) -> dict[str, Any]: ...

    def identity_or_exact_departure(self, path: str) -> str | None: ...

    def evidence_after_exact_departure(self, path: str) -> dict[str, Any]: ...

    def revalidate(self, evidence: dict[str, Any]) -> None: ...

    def revalidate_or_departure(self, evidence: dict[str, Any]) -> None: ...


EndpointObserverFactory = Callable[[], EndpointIdentityObserver]


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
    endpoint_transition_evidence: dict[str, Any] | None = None
    raw_capture_receipt: dict[str, Any] | None = None


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


@dataclass(frozen=True, eq=False)
class _TransactionLease:
    run_dir: Path
    run_identity: tuple[int, int]
    owner_pid: int
    owner_thread: int


_ACTIVE_LEASES: set[_TransactionLease] = set()
_ACTIVE_LEASES_LOCK = threading.Lock()


class EndpointGenerationTracker:
    """Assign generations to observed path and character-device identities."""

    def __init__(self) -> None:
        self._previous_live: tuple[tuple[str, str], ...] = ()
        self._generation = 0

    def observe(self, live_identities: tuple[tuple[str, str], ...]) -> int | None:
        if len(live_identities) > 1:
            raise OdinTransitionError(
                f"ambiguous live Odin endpoints: {list(live_identities)}"
            )
        if live_identities != self._previous_live:
            if live_identities:
                self._generation += 1
            self._previous_live = live_identities
        return self._generation if live_identities else None

    @property
    def generation(self) -> int:
        return self._generation


class _EnumerationOutputLimit(subprocess.SubprocessError):
    pass


def _default_runner(argv: list[str], timeout: float) -> subprocess.CompletedProcess[bytes]:
    """Sentinel: production callers must replace it with a bound raw runner."""

    del argv, timeout
    raise OdinTransitionError(
        "Odin enumeration raw-first runner is not bound to a run directory"
    )


def _raw_capture_identity(handle: raw_capture.RawCaptureHandle) -> dict[str, Any]:
    payload = handle.receipt_path.read_bytes()
    return {
        "path": str(handle.receipt_path),
        "size": len(payload),
        "sha256": live_core.sha256_bytes(payload),
    }


def _next_enumeration_capture_name(run_dir: Path, sequence: int) -> tuple[Path, str]:
    capture_dir = raw_capture.prepare_capture_dir(
        run_dir, "raw-odin-enumeration"
    )
    prefix = f"sequence-{sequence:06d}-attempt-"
    used: set[int] = set()
    for path in capture_dir.iterdir():
        match = re.fullmatch(
            re.escape(prefix) + r"([0-9]{4})\.(?:stdout\.bin|stderr\.bin|capture\.json)",
            path.name,
        )
        if match is not None:
            used.add(int(match.group(1)))
    attempt = 0
    while attempt in used:
        attempt += 1
    if attempt > 9999:
        raise OdinTransitionError("Odin raw-capture attempt capacity is exhausted")
    return capture_dir, prefix + f"{attempt:04d}"


def _raw_first_runner(
    run_dir: Path,
    sequence: int,
) -> tuple[Runner, list[raw_capture.RawCaptureHandle]]:
    handles: list[raw_capture.RawCaptureHandle] = []

    def run(argv: list[str], timeout: float) -> RawRunResult:
        capture_dir, name = _next_enumeration_capture_name(run_dir, sequence)
        try:
            handle = raw_capture.acquire_command(
                argv,
                capture_dir,
                name,
                timeout=timeout,
                stdout_maximum=MAX_ENUM_OUTPUT_BYTES,
                stderr_maximum=MAX_ENUM_OUTPUT_BYTES,
            )
            handles.append(handle)
            return RawRunResult(handle)
        except raw_capture.RawCaptureError as exc:
            raise _EnumerationOutputLimit(
                f"Odin raw-first enumeration capture failed: {exc}"
            ) from exc

    return run, handles


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _monotonic_now(monotonic: Callable[[], float]) -> float:
    value = monotonic()
    try:
        finite = math.isfinite(value)
    except TypeError as exc:
        raise OdinTransitionError("monotonic clock returned a non-number") from exc
    if not finite:
        raise OdinTransitionError("monotonic clock returned a non-finite value")
    return value


def _deadline_after(start: float, duration: float) -> float:
    deadline = start + duration
    if not math.isfinite(deadline):
        raise OdinTransitionError("deadline overflowed to a non-finite value")
    return deadline


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


def _default_device_inventory() -> dict[str, str]:
    root = Path("/dev/bus/usb")
    if not root.is_dir():
        return {}
    inventory: dict[str, str] = {}
    for path in sorted(root.glob("[0-9][0-9][0-9]/[0-9][0-9][0-9]")):
        encoded = str(path)
        if ODIN_DEVICE_RE.fullmatch(encoded) is None:
            continue
        identity = _default_device_identity(encoded)
        if identity is not None:
            inventory[encoded] = identity
        if len(inventory) > MAX_SNAPSHOT_RECEIPTS:
            raise OdinTransitionError("USB device-node inventory exceeds bound")
    return inventory


def _validated_device_inventory(device_inventory: DeviceInventory) -> dict[str, str]:
    try:
        inventory = device_inventory()
    except OSError as exc:
        raise OdinTransitionError("USB device-node inventory failed") from exc
    if not isinstance(inventory, dict) or len(inventory) > MAX_SNAPSHOT_RECEIPTS:
        raise OdinTransitionError("USB device-node inventory is invalid")
    for path, identity in inventory.items():
        if (
            not isinstance(path, str)
            or ODIN_DEVICE_RE.fullmatch(path) is None
            or not isinstance(identity, str)
            or not identity
        ):
            raise OdinTransitionError("USB device-node inventory entry is invalid")
    return inventory


def measured_usbfs_observer(
    capture_dir: Path | None = None,
) -> EndpointIdentityObserver:
    """Return the opt-in R4W1-C-derived timestamp-aware identity observer."""

    return usbfs_identity.MeasuredUsbfsIdentityObserver(capture_dir=capture_dir)


def _new_endpoint_observer(
    factory: EndpointObserverFactory,
) -> EndpointIdentityObserver:
    try:
        observer = factory()
    except (OSError, TypeError, usbfs_identity.UsbfsIdentityError) as exc:
        raise OdinTransitionError("measured USB endpoint observer creation failed") from exc
    if any(
        not callable(getattr(observer, name, None))
        for name in (
            "inventory",
            "identity",
            "evidence",
            "identity_or_exact_departure",
            "evidence_after_exact_departure",
            "revalidate",
            "revalidate_or_departure",
        )
    ):
        raise OdinTransitionError("measured USB endpoint observer is invalid")
    return observer


def enumerate_odin(
    odin: Path,
    *,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    device_inventory: DeviceInventory = _default_device_inventory,
    endpoint_observer_factory: EndpointObserverFactory | None = None,
    allow_live_departure_race: bool = False,
    allow_live_arrival_race: bool = False,
    timeout_sec: float = 10.0,
    timestamp: Callable[[], str] = live_core.utc_now,
) -> OdinSnapshot:
    """Return one bounded snapshot; stale paths are evidence, not live devices."""

    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise OdinTransitionError("Odin enumeration timeout must be positive")
    observer: EndpointIdentityObserver | None = None
    if endpoint_observer_factory is not None:
        if (
            device_identity is not _default_device_identity
            or device_inventory is not _default_device_inventory
        ):
            raise OdinTransitionError(
                "measured endpoint observer cannot be combined with legacy identity callbacks"
            )
        try:
            observer = _new_endpoint_observer(endpoint_observer_factory)
            before = _validated_device_inventory(observer.inventory)
        except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
            raise OdinTransitionError("measured USB endpoint inventory failed") from exc
        active_identity = (
            observer.identity_or_exact_departure
            if allow_live_departure_race
            else observer.identity
        )
    else:
        before = _validated_device_inventory(device_inventory)
        active_identity = device_identity
    try:
        result = runner([str(odin), "-l"], timeout_sec)
    except (OSError, subprocess.SubprocessError) as exc:
        raise OdinTransitionError("Odin enumeration did not complete") from exc
    if isinstance(result, RawRunResult):
        try:
            if (
                result.handle.producer_error_type is not None
                or result.handle.timed_out
                or result.handle.output_exceeded
            ):
                raise raw_capture.RawCaptureError(
                    "Odin raw enumeration acquisition failed"
                )
            stdout = raw_capture.read_stdout(
                result.handle, maximum=MAX_ENUM_OUTPUT_BYTES
            ).decode("utf-8", "replace")
            stderr = raw_capture.read_stderr(
                result.handle, maximum=MAX_ENUM_OUTPUT_BYTES
            ).decode("utf-8", "replace")
        except (UnicodeError, raw_capture.RawCaptureError) as exc:
            raise OdinTransitionError(
                "Odin raw enumeration cannot be parsed"
            ) from exc
        returncode = result.handle.returncode
    else:
        stdout = _as_text(result.stdout)
        stderr = _as_text(result.stderr)
        returncode = result.returncode
    if len(stdout.encode("utf-8")) + len(stderr.encode("utf-8")) > MAX_ENUM_OUTPUT_BYTES:
        raise OdinTransitionError("Odin enumeration output exceeds bound")
    if returncode != 0:
        raise OdinTransitionError(
            f"Odin enumeration failed rc={returncode}"
        )
    raw_devices = tuple(
        sorted(set(ODIN_DEVICE_RE.findall(stdout)) | set(ODIN_DEVICE_RE.findall(stderr)))
    )
    identities_list: list[tuple[str, str]] = []
    arrival_list: list[str] = []
    stale_list: list[str] = []
    for device in raw_devices:
        identity_before = before.get(device)
        try:
            identity_after = active_identity(device)
        except usbfs_identity.UsbfsInventoryArrival as exc:
            if allow_live_arrival_race and raw_devices == (exc.path,):
                raise OdinEndpointArrivalRace(
                    f"Odin endpoint arrived during enumeration: {exc.path}"
                ) from exc
            raise OdinTransitionError(
                f"unexpected USB endpoint arrival during enumeration: {exc.path}"
            ) from exc
        except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
            raise OdinTransitionError(
                f"Odin endpoint identity observation failed: {device}"
            ) from exc
        if identity_before is not None and identity_after is None:
            if (
                allow_live_departure_race
                and observer is not None
                and raw_devices == (device,)
            ):
                try:
                    endpoint_evidence = observer.evidence_after_exact_departure(
                        device
                    )
                except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
                    raise OdinTransitionError(
                        f"Odin endpoint changed during enumeration: {device}"
                    ) from exc
                return OdinSnapshot(
                    timestamp_utc=timestamp(),
                    returncode=returncode,
                    raw_devices=raw_devices,
                    live_devices=(),
                    stale_devices=raw_devices,
                    live_device_identities=(),
                    stdout=stdout,
                    stderr=stderr,
                    endpoint_transition_evidence=endpoint_evidence,
                )
            raise OdinTransitionError(
                f"Odin endpoint changed during enumeration: {device}"
            )
        if identity_before is None and identity_after is None:
            stale_list.append(device)
            continue
        if identity_before is None:
            arrival_list.append(device)
            continue
        if identity_after != identity_before:
            raise OdinTransitionError(
                f"Odin endpoint changed during enumeration: {device}"
            )
        identities_list.append((device, identity_after))
    if arrival_list:
        if len(arrival_list) == 1 and not identities_list:
            raise OdinEndpointArrivalRace(
                f"Odin endpoint arrived during enumeration: {arrival_list[0]}"
            )
        raise OdinTransitionError(
            "ambiguous live Odin endpoints during enumeration"
        )
    identities = tuple(identities_list)
    live_devices = tuple(device for device, _identity in identities)
    stale_devices = tuple(stale_list)
    try:
        endpoint_evidence = observer.evidence(live_devices) if observer is not None else None
    except usbfs_identity.UsbfsInventoryArrival as exc:
        if allow_live_arrival_race and not raw_devices:
            raise OdinEndpointArrivalRace(
                f"USB endpoint arrived after empty Odin enumeration: {exc.path}"
            ) from exc
        raise OdinTransitionError(
            f"unexpected USB endpoint arrival during enumeration: {exc.path}"
        ) from exc
    except usbfs_identity.UsbfsInventoryMembershipChanged as exc:
        raise OdinMeasuredEvidenceFailure(
            "inventory-membership-changed",
            "UsbfsInventoryMembershipChanged",
            removed=exc.removed,
            added=exc.added,
        ) from exc
    except usbfs_identity.UsbfsIdentityError as exc:
        raise OdinMeasuredEvidenceFailure(
            "usbfs-identity-failed", "UsbfsIdentityError"
        ) from exc
    except OSError as exc:
        raise OdinMeasuredEvidenceFailure(
            "direct-io-failed", "OSError"
        ) from exc
    return OdinSnapshot(
        timestamp_utc=timestamp(),
        returncode=returncode,
        raw_devices=raw_devices,
        live_devices=live_devices,
        stale_devices=stale_devices,
        live_device_identities=identities,
        stdout=stdout,
        stderr=stderr,
        endpoint_transition_evidence=endpoint_evidence,
    )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _require_direct_directory(path: Path, *, create: bool = False) -> os.stat_result:
    if create and not path.exists() and not path.is_symlink():
        parent = path.parent
        if parent == path:
            raise OdinTransitionError(f"cannot create transaction directory: {path}")
        _require_direct_directory(parent, create=True)
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            _fsync_directory(parent)
        except OSError as exc:
            raise OdinTransitionError(
                f"cannot create transaction directory: {path}"
            ) from exc
        else:
            _fsync_directory(parent)
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise OdinTransitionError(f"transaction directory unavailable: {path}") from exc
    if not stat.S_ISDIR(metadata.st_mode) or path.is_symlink():
        raise OdinTransitionError(f"transaction path is not a direct directory: {path}")
    return metadata


@contextmanager
def transaction_session(run_dir: Path):
    """Hold the single-writer lease for one complete helper transaction."""

    directory = _require_direct_directory(run_dir, create=True)
    lock_path = run_dir / ".odin-transition.lock"
    flags = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise OdinTransitionError(f"cannot open transaction lock: {lock_path}") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OdinTransitionError(f"transaction lock is not regular: {lock_path}")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise OdinTransitionError("transaction already has an active writer") from exc
        lease = _TransactionLease(
            run_dir=run_dir,
            run_identity=(directory.st_dev, directory.st_ino),
            owner_pid=os.getpid(),
            owner_thread=threading.get_ident(),
        )
        with _ACTIVE_LEASES_LOCK:
            _ACTIVE_LEASES.add(lease)
        try:
            yield lease
        finally:
            with _ACTIVE_LEASES_LOCK:
                _ACTIVE_LEASES.discard(lease)
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _require_active_lease(run_dir: Path, lease: _TransactionLease) -> None:
    if not isinstance(lease, _TransactionLease):
        raise OdinTransitionError("active transaction lease is required")
    with _ACTIVE_LEASES_LOCK:
        registered = lease in _ACTIVE_LEASES
    if (
        not registered
        or lease.owner_pid != os.getpid()
        or lease.owner_thread != threading.get_ident()
        or lease.run_dir != run_dir
    ):
        raise OdinTransitionError("active transaction lease is required")
    current = _require_direct_directory(run_dir)
    if (current.st_dev, current.st_ino) != lease.run_identity:
        raise OdinTransitionError("transaction directory identity changed")


def _json_receipt_bytes(value: Any) -> bytes:
    try:
        payload = (
            json.dumps(
                value,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise OdinTransitionError("receipt payload is not bounded JSON") from exc
    if len(payload) > MAX_RECEIPT_BYTES:
        raise OdinTransitionError(
            f"receipt exceeds bound: {len(payload)} > {MAX_RECEIPT_BYTES}"
        )
    return payload


def _create_sealed_receipt(path: Path, value: Any) -> dict[str, Any]:
    expected = _json_receipt_bytes(value)
    _require_direct_directory(path.parent, create=True)
    temporary = path.with_name(f".{path.name}.sealed-tmp-{os.getpid()}")
    if path.exists() or path.is_symlink():
        raise OdinTransitionError(f"receipt already exists: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = -1
    try:
        try:
            descriptor = os.open(temporary, flags, 0o400)
        except OSError as exc:
            raise OdinTransitionError(
                f"cannot create sealed receipt temporary: {temporary}"
            ) from exc
        offset = 0
        while offset < len(expected):
            written = os.write(descriptor, expected[offset:])
            if written <= 0:
                raise OdinTransitionError(f"short receipt write: {temporary}")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size != len(expected)
        ):
            raise OdinTransitionError(f"temporary receipt is not sealed: {temporary}")
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise OdinTransitionError(f"receipt was created concurrently: {path}") from exc
        except OSError as exc:
            raise OdinTransitionError(f"cannot publish sealed receipt: {path}") from exc
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
    actual = live_core.read_stable_file(path, maximum=MAX_RECEIPT_BYTES)
    if actual != expected:
        raise OdinTransitionError(f"receipt serialization mismatch: {path}")
    return {"size": len(actual), "sha256": live_core.sha256_bytes(actual)}


def _persist_measured_evidence_diagnostic(
    run_dir: Path,
    sequence: int,
    failure: OdinMeasuredEvidenceFailure,
    *,
    timestamp: Callable[[], str],
    lease: _TransactionLease,
) -> dict[str, Any]:
    if (
        not isinstance(run_dir, Path)
        or not isinstance(sequence, int)
        or isinstance(sequence, bool)
        or sequence < 0
        or not isinstance(failure, OdinMeasuredEvidenceFailure)
    ):
        raise OdinTransitionError("diagnostic failure input is invalid")
    _require_active_lease(run_dir, lease)
    diagnostics = run_dir / "diagnostics"
    _require_direct_directory(diagnostics, create=True)
    ordinal = None
    path = None
    for candidate in range(MAX_DIAGNOSTIC_RECEIPTS):
        candidate_path = (
            diagnostics / f"odin-diagnostic-failure-{candidate:06d}.json"
        )
        if not candidate_path.exists() and not candidate_path.is_symlink():
            ordinal = candidate
            path = candidate_path
            break
    if ordinal is None or path is None:
        raise OdinTransitionError("diagnostic receipt capacity exhausted")
    payload = {
        "schema": DIAGNOSTIC_SCHEMA,
        "ordinal": ordinal,
        "timestamp_utc": timestamp(),
        "attempted_snapshot_sequence": sequence,
        "observation_stage": failure.observation_stage,
        "failure_kind": failure.failure_kind,
        "inner_exception_class": failure.inner_exception_class,
        "removed": list(failure.removed),
        "added": list(failure.added),
        "snapshot_persisted": False,
    }
    receipt = _create_sealed_receipt(path, payload)
    return {
        "path": str(path),
        "size": receipt["size"],
        "sha256": receipt["sha256"],
    }


def _read_sealed_receipt(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = live_core.read_stable_file(path, maximum=MAX_RECEIPT_BYTES)
    metadata = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o400:
        raise OdinTransitionError(f"receipt is not sealed read-only: {path}")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OdinTransitionError(f"receipt is malformed JSON: {path}") from exc
    if not isinstance(value, dict):
        raise OdinTransitionError(f"receipt is not a JSON object: {path}")
    return value, {"size": len(payload), "sha256": live_core.sha256_bytes(payload)}


def _jsonl_record_bytes(value: dict[str, Any]) -> bytes:
    try:
        payload = (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise OdinTransitionError("transaction index record is not JSON") from exc
    if len(payload) > MAX_INDEX_RECORD_BYTES:
        raise OdinTransitionError("transaction index record exceeds bound")
    return payload


def _durable_append_jsonl(path: Path, value: dict[str, Any]) -> None:
    """Append one bounded advisory record after its durable receipt exists."""

    _require_direct_directory(path.parent)
    payload = _jsonl_record_bytes(value)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW
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
    _require_direct_directory(run_dir)
    base = run_dir / "transaction.jsonl"
    if base.is_symlink():
        raise OdinTransitionError(f"transaction index must not be a symlink: {base}")
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
    if len(resumes) > MAX_INDEX_SEGMENTS - 1:
        raise OdinTransitionError(
            f"transaction index segment count exceeds {MAX_INDEX_SEGMENTS}"
        )
    numbers = [number for number, _path in resumes]
    if numbers != list(range(1, len(numbers) + 1)):
        raise OdinTransitionError(
            f"transaction index resume segments are not contiguous: {numbers}"
        )
    paths.extend(path for _number, path in resumes)
    total_bytes = 0
    for path in paths:
        metadata = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise OdinTransitionError(
                f"transaction index segment must be a direct regular file: {path}"
            )
        total_bytes += metadata.st_size
        if total_bytes > MAX_INDEX_TOTAL_BYTES:
            raise OdinTransitionError(
                f"transaction index total exceeds {MAX_INDEX_TOTAL_BYTES} bytes"
            )
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


def _append_transaction_record_unlocked(run_dir: Path, value: dict[str, Any]) -> Path:
    """Append to the latest clean segment, or start a new one after a partial tail."""

    payload_size = len(_jsonl_record_bytes(value))
    paths = _transaction_index_paths(run_dir)
    if not paths:
        target = run_dir / "transaction.jsonl"
    else:
        latest = paths[-1]
        parsed = read_transaction_index(latest)
        if parsed["complete"]:
            target = latest
        else:
            if len(paths) >= MAX_INDEX_SEGMENTS:
                raise OdinTransitionError(
                    "transaction index has no resume-segment capacity"
                )
            target = run_dir / f"transaction-resume-{len(paths):06d}.jsonl"
            if target.exists() or target.is_symlink():
                raise OdinTransitionError(
                    f"transaction index resume segment already exists: {target}"
                )
    total_size = sum(path.stat(follow_symlinks=False).st_size for path in paths)
    if total_size + payload_size > MAX_INDEX_TOTAL_BYTES:
        raise OdinTransitionError("transaction index append exceeds aggregate bound")
    _durable_append_jsonl(target, value)
    return target


def _require_index_append_capacity(run_dir: Path, required_bytes: int) -> None:
    """Reserve room for one already-serialized record before receipt publication."""

    if required_bytes <= 0 or required_bytes > MAX_INDEX_RECORD_BYTES:
        raise OdinTransitionError("transaction index record has invalid size")
    paths = _transaction_index_paths(run_dir)
    if not paths and required_bytes > MAX_INDEX_BYTES:
        raise OdinTransitionError("transaction index segment has no append capacity")
    if paths:
        latest = read_transaction_index(paths[-1])
        if not latest["complete"] and len(paths) >= MAX_INDEX_SEGMENTS:
            raise OdinTransitionError("transaction index has no resume-segment capacity")
        if latest["complete"]:
            current_size = paths[-1].stat(follow_symlinks=False).st_size
            if current_size + required_bytes > MAX_INDEX_BYTES:
                raise OdinTransitionError("transaction index segment has no append capacity")
    total_size = sum(path.stat(follow_symlinks=False).st_size for path in paths)
    if total_size + required_bytes > MAX_INDEX_TOTAL_BYTES:
        raise OdinTransitionError("transaction index has no aggregate append capacity")


def _receipt_payload(snapshot: OdinSnapshot, sequence: int) -> dict[str, Any]:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "sequence": sequence,
        **asdict(snapshot),
    }


def _validate_snapshot_for_persistence(snapshot: OdinSnapshot) -> None:
    if not isinstance(snapshot, OdinSnapshot):
        raise OdinTransitionError("snapshot has an invalid type")
    raw = snapshot.raw_devices
    live = snapshot.live_devices
    stale = snapshot.stale_devices
    identities = snapshot.live_device_identities
    evidence = snapshot.endpoint_transition_evidence
    raw_capture_receipt = snapshot.raw_capture_receipt
    if any(
        not isinstance(values, tuple)
        or any(not isinstance(value, str) for value in values)
        for values in (raw, live, stale)
    ):
        raise OdinTransitionError("snapshot device lists are invalid")
    if raw != tuple(sorted(set(raw))) or live != tuple(sorted(set(live))):
        raise OdinTransitionError("snapshot device lists are not canonical")
    if stale != tuple(sorted(set(stale))) or set(live) & set(stale):
        raise OdinTransitionError("snapshot stale devices are not canonical")
    if tuple(sorted(live + stale)) != raw:
        raise OdinTransitionError("snapshot live/stale partition is invalid")
    if (
        not isinstance(identities, tuple)
        or any(
            not isinstance(value, tuple)
            or len(value) != 2
            or any(not isinstance(field, str) or not field for field in value)
            for value in identities
        )
        or tuple(value[0] for value in identities) != live
    ):
        raise OdinTransitionError("snapshot endpoint identities are invalid")
    if evidence is not None and not isinstance(evidence, dict):
        raise OdinTransitionError("snapshot endpoint transition evidence is invalid")
    if raw_capture_receipt is not None:
        if (
            not isinstance(raw_capture_receipt, dict)
            or set(raw_capture_receipt) != {"path", "sha256", "size"}
            or not isinstance(raw_capture_receipt["path"], str)
            or not raw_capture_receipt["path"]
            or type(raw_capture_receipt["size"]) is not int
            or not 1 <= raw_capture_receipt["size"] <= 64 * 1024
            or not isinstance(raw_capture_receipt["sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", raw_capture_receipt["sha256"])
            is None
        ):
            raise OdinTransitionError("snapshot raw-capture receipt is invalid")
    try:
        if evidence is not None:
            usbfs_identity.validate_enumeration_evidence(evidence)
            if evidence["live_devices"] != list(live):
                raise OdinTransitionError(
                    "snapshot endpoint transition evidence live binding is invalid"
                )
    except (AttributeError, TypeError, usbfs_identity.UsbfsIdentityError) as exc:
        raise OdinTransitionError(
            "snapshot endpoint transition evidence is invalid"
        ) from exc
    if (
        snapshot.returncode != 0
        or not isinstance(snapshot.timestamp_utc, str)
        or not snapshot.timestamp_utc
        or not isinstance(snapshot.stdout, str)
        or not isinstance(snapshot.stderr, str)
        or len(snapshot.stdout.encode("utf-8"))
        + len(snapshot.stderr.encode("utf-8"))
        > MAX_ENUM_OUTPUT_BYTES
    ):
        raise OdinTransitionError("snapshot observation is invalid")


def _persist_snapshot_unlocked(
    run_dir: Path, sequence: int, snapshot: OdinSnapshot
) -> dict[str, Any]:
    _reconcile_receipt_index_unlocked(run_dir)
    existing = list_snapshot_receipts(run_dir)
    if len(existing) >= MAX_SNAPSHOT_RECEIPTS:
        raise OdinTransitionError("snapshot receipt capacity is exhausted")
    if sequence != len(existing):
        raise OdinTransitionError(
            f"snapshot sequence append mismatch: expected {len(existing)}, received {sequence}"
        )
    if snapshot.raw_capture_receipt is not None:
        raw_value = snapshot.raw_capture_receipt
        raw_path = Path(raw_value["path"]).absolute()
        raw_root = (run_dir / "raw-odin-enumeration").absolute()
        if raw_path.parent != raw_root:
            raise OdinTransitionError("snapshot raw capture escaped its run directory")
        try:
            handle = raw_capture.load_handle(raw_path)
        except raw_capture.RawCaptureError as exc:
            raise OdinTransitionError("snapshot raw capture cannot be reopened") from exc
        raw_bytes = raw_path.read_bytes()
        if (
            len(raw_bytes) != raw_value["size"]
            or live_core.sha256_bytes(raw_bytes) != raw_value["sha256"]
            or handle.returncode != snapshot.returncode
            or raw_capture.read_stdout(
                handle, maximum=MAX_ENUM_OUTPUT_BYTES
            ).decode("utf-8", errors="replace")
            != snapshot.stdout
            or raw_capture.read_stderr(
                handle, maximum=MAX_ENUM_OUTPUT_BYTES
            ).decode("utf-8", errors="replace")
            != snapshot.stderr
        ):
            raise OdinTransitionError("snapshot raw capture differs from parsed output")
    receipt_path = run_dir / "receipts" / f"odin-snapshot-{sequence:06d}.json"
    receipt_value = _receipt_payload(snapshot, sequence)
    receipt_bytes = _json_receipt_bytes(receipt_value)
    expected_identity = {
        "size": len(receipt_bytes),
        "sha256": live_core.sha256_bytes(receipt_bytes),
    }
    record = {
        "schema": INDEX_SCHEMA,
        "record": "odin_snapshot",
        "timestamp_utc": snapshot.timestamp_utc,
        "sequence": sequence,
        "receipt": str(receipt_path),
        "receipt_size": expected_identity["size"],
        "receipt_sha256": expected_identity["sha256"],
        "live_devices": list(snapshot.live_devices),
        "live_device_identities": [list(value) for value in snapshot.live_device_identities],
        "stale_devices": list(snapshot.stale_devices),
    }
    record_bytes = _jsonl_record_bytes(record)
    _require_index_append_capacity(run_dir, len(record_bytes))
    identity = _create_sealed_receipt(receipt_path, receipt_value)
    if identity != expected_identity:
        raise OdinTransitionError("snapshot receipt identity changed during publication")
    _append_transaction_record_unlocked(run_dir, record)
    return record


def persist_snapshot(
    run_dir: Path,
    sequence: int,
    snapshot: OdinSnapshot,
    *,
    lease: _TransactionLease,
) -> dict[str, Any]:
    if sequence < 0:
        raise OdinTransitionError("snapshot sequence must be non-negative")
    _require_active_lease(run_dir, lease)
    _validate_snapshot_for_persistence(snapshot)
    return _persist_snapshot_unlocked(run_dir, sequence, snapshot)


def _receipt_directory(run_dir: Path, *, create: bool = False) -> Path | None:
    _require_direct_directory(run_dir, create=create)
    directory = run_dir / "receipts"
    if not directory.exists() and not directory.is_symlink() and not create:
        return None
    _require_direct_directory(directory, create=create)
    return directory


def list_phase_receipts(run_dir: Path) -> list[dict[str, Any]]:
    directory = _receipt_directory(run_dir)
    if directory is None:
        return []
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted(directory.glob("phase-*.json")):
        value, identity = _read_sealed_receipt(path)
        if value.get("schema") != PHASE_SCHEMA:
            raise OdinTransitionError(f"invalid phase receipt schema: {path}")
        phase = value.get("phase")
        if phase not in TRANSACTION_PHASES or phase in seen:
            raise OdinTransitionError(f"invalid or duplicate phase receipt: {path}")
        if path.name != f"phase-{phase}.json":
            raise OdinTransitionError(f"phase receipt path/payload mismatch: {path}")
        if not isinstance(value.get("timestamp_utc"), str) or not isinstance(
            value.get("payload"), dict
        ):
            raise OdinTransitionError(f"invalid phase receipt payload: {path}")
        seen.add(phase)
        records.append(
            {
                "path": str(path),
                "phase": phase,
                "timestamp_utc": value["timestamp_utc"],
                "size": identity["size"],
                "sha256": identity["sha256"],
            }
        )
    records.sort(key=lambda record: TRANSACTION_PHASES.index(record["phase"]))
    phases = [record["phase"] for record in records]
    expected = list(TRANSACTION_PHASES[: len(phases)])
    if phases != expected:
        raise OdinTransitionError(
            f"transaction phase receipts are not a valid prefix: {phases}"
        )
    return records


def create_phase_receipt(
    run_dir: Path,
    phase: str,
    payload: dict[str, Any],
    *,
    lease: _TransactionLease,
) -> dict[str, Any]:
    if not RECEIPT_NAME_RE.fullmatch(phase):
        raise OdinTransitionError(f"invalid phase receipt name: {phase!r}")
    if phase not in TRANSACTION_PHASES:
        raise OdinTransitionError(f"unknown transaction phase: {phase}")
    _require_active_lease(run_dir, lease)
    existing = list_phase_receipts(run_dir)
    _reconcile_receipt_index_unlocked(run_dir)
    if len(existing) >= len(TRANSACTION_PHASES) or phase != TRANSACTION_PHASES[
        len(existing)
    ]:
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
    receipt_bytes = _json_receipt_bytes(value)
    expected_identity = {
        "size": len(receipt_bytes),
        "sha256": live_core.sha256_bytes(receipt_bytes),
    }
    record = {
        "schema": INDEX_SCHEMA,
        "record": "phase_receipt",
        "timestamp_utc": value["timestamp_utc"],
        "phase": phase,
        "receipt": str(receipt_path),
        "receipt_size": expected_identity["size"],
        "receipt_sha256": expected_identity["sha256"],
    }
    record_bytes = _jsonl_record_bytes(record)
    _require_index_append_capacity(run_dir, len(record_bytes))
    identity = _create_sealed_receipt(receipt_path, value)
    if identity != expected_identity:
        raise OdinTransitionError("phase receipt identity changed during publication")
    _append_transaction_record_unlocked(run_dir, record)
    return record


def list_snapshot_receipts(run_dir: Path) -> list[dict[str, Any]]:
    """Recover crash-durable snapshots from trusted host storage."""

    directory = _receipt_directory(run_dir)
    if directory is None:
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("odin-snapshot-*.json")):
        if len(records) >= MAX_SNAPSHOT_RECEIPTS:
            raise OdinTransitionError(
                f"snapshot receipt count exceeds {MAX_SNAPSHOT_RECEIPTS}"
            )
        payload, identity = _read_sealed_receipt(path)
        schema = payload.get("schema")
        if schema not in {SNAPSHOT_SCHEMA_V1, SNAPSHOT_SCHEMA_V2, SNAPSHOT_SCHEMA}:
            raise OdinTransitionError(f"invalid snapshot receipt schema: {path}")
        sequence = payload.get("sequence")
        if not isinstance(sequence, int) or path.name != f"odin-snapshot-{sequence:06d}.json":
            raise OdinTransitionError(f"snapshot receipt path/payload mismatch: {path}")
        raw = payload.get("raw_devices")
        live = payload.get("live_devices")
        stale = payload.get("stale_devices")
        identities = payload.get("live_device_identities")
        evidence = payload.get("endpoint_transition_evidence")
        raw_capture_receipt = payload.get("raw_capture_receipt")
        if any(
            not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for values in (raw, live, stale)
        ):
            raise OdinTransitionError(f"snapshot receipt device lists invalid: {path}")
        if raw != sorted(set(raw)) or live != sorted(set(live)) or stale != sorted(set(stale)):
            raise OdinTransitionError(f"snapshot receipt device lists not canonical: {path}")
        if set(live) & set(stale) or sorted(live + stale) != raw:
            raise OdinTransitionError(f"snapshot receipt live/stale partition invalid: {path}")
        if (
            not isinstance(identities, list)
            or any(
                not isinstance(value, list)
                or len(value) != 2
                or any(not isinstance(field, str) for field in value)
                for value in identities
            )
            or [value[0] for value in identities] != live
        ):
            raise OdinTransitionError(f"snapshot receipt identities invalid: {path}")
        if schema == SNAPSHOT_SCHEMA_V1 and "endpoint_transition_evidence" in payload:
            raise OdinTransitionError(
                f"legacy snapshot receipt has transition evidence: {path}"
            )
        if schema in {SNAPSHOT_SCHEMA_V1, SNAPSHOT_SCHEMA_V2} and (
            "raw_capture_receipt" in payload
        ):
            raise OdinTransitionError(
                f"legacy snapshot receipt has raw-capture evidence: {path}"
            )
        if schema == SNAPSHOT_SCHEMA and raw_capture_receipt is not None:
            if (
                not isinstance(raw_capture_receipt, dict)
                or set(raw_capture_receipt) != {"path", "sha256", "size"}
            ):
                raise OdinTransitionError(
                    f"snapshot raw-capture receipt invalid: {path}"
                )
            raw_path = Path(raw_capture_receipt.get("path", "")).absolute()
            if raw_path.parent != (run_dir / "raw-odin-enumeration").absolute():
                raise OdinTransitionError(
                    f"snapshot raw capture escaped run directory: {path}"
                )
            try:
                handle = raw_capture.load_handle(raw_path)
            except raw_capture.RawCaptureError as exc:
                raise OdinTransitionError(
                    f"snapshot raw capture cannot be reopened: {path}"
                ) from exc
            raw_bytes = raw_path.read_bytes()
            if (
                len(raw_bytes) != raw_capture_receipt.get("size")
                or live_core.sha256_bytes(raw_bytes)
                != raw_capture_receipt.get("sha256")
                or handle.returncode != payload.get("returncode")
                or raw_capture.read_stdout(
                    handle, maximum=MAX_ENUM_OUTPUT_BYTES
                ).decode("utf-8", errors="replace")
                != payload.get("stdout")
                or raw_capture.read_stderr(
                    handle, maximum=MAX_ENUM_OUTPUT_BYTES
                ).decode("utf-8", errors="replace")
                != payload.get("stderr")
            ):
                raise OdinTransitionError(
                    f"snapshot raw capture differs from receipt: {path}"
                )
        if (
            evidence is not None and not isinstance(evidence, dict)
        ):
            raise OdinTransitionError(
                f"snapshot receipt transition evidence invalid: {path}"
            )
        try:
            if evidence is not None:
                usbfs_identity.validate_enumeration_evidence(evidence)
                if evidence["live_devices"] != live:
                    raise OdinTransitionError(
                        f"snapshot receipt transition evidence binding invalid: {path}"
                    )
        except (AttributeError, TypeError, usbfs_identity.UsbfsIdentityError) as exc:
            raise OdinTransitionError(
                f"snapshot receipt transition evidence invalid: {path}"
            ) from exc
        if (
            payload.get("returncode") != 0
            or not isinstance(payload.get("timestamp_utc"), str)
            or not isinstance(payload.get("stdout"), str)
            or not isinstance(payload.get("stderr"), str)
        ):
            raise OdinTransitionError(f"snapshot receipt observation invalid: {path}")
        record = {
            "path": str(path),
            "sequence": sequence,
            "timestamp_utc": payload["timestamp_utc"],
            "size": identity["size"],
            "sha256": identity["sha256"],
            "live_devices": live,
            "live_device_identities": identities,
            "stale_devices": stale,
        }
        # Preserve the exact historical v1 summary shape so evidence collected
        # before measured endpoint support still reopens byte-for-byte.
        if schema in {SNAPSHOT_SCHEMA_V2, SNAPSHOT_SCHEMA}:
            record["endpoint_transition_evidence"] = evidence
        if schema == SNAPSHOT_SCHEMA:
            record["raw_capture_receipt"] = raw_capture_receipt
        records.append(record)
    sequences = [record["sequence"] for record in records]
    if sequences != sorted(set(sequences)):
        raise OdinTransitionError("snapshot receipt sequence is invalid")
    return records


def _audit_index_against_receipts(
    run_dir: Path,
    snapshots: list[dict[str, Any]],
    phases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate every complete advisory index reference against its receipt."""

    indexed = read_transaction_segments(run_dir)
    known = {record["path"]: record for record in snapshots + phases}
    seen_paths: set[str] = set()
    last_snapshot_sequence = -1
    last_phase_index = -1
    for record in indexed["records"]:
        kind = record.get("record")
        receipt = record.get("receipt")
        if kind not in {"odin_snapshot", "phase_receipt"} or not isinstance(
            receipt, str
        ):
            raise OdinTransitionError("transaction index has unknown record")
        if receipt in seen_paths:
            raise OdinTransitionError(f"transaction index duplicates receipt: {receipt}")
        seen_paths.add(receipt)
        current = known.get(receipt)
        if current is None:
            raise OdinTransitionError(f"transaction index receipt is missing: {receipt}")
        if (
            record.get("receipt_size") != current["size"]
            or record.get("receipt_sha256") != current["sha256"]
        ):
            raise OdinTransitionError(f"transaction index receipt hash mismatch: {receipt}")
        if kind == "odin_snapshot":
            sequence = record.get("sequence")
            if not isinstance(sequence, int) or sequence <= last_snapshot_sequence:
                raise OdinTransitionError("transaction index snapshot order is invalid")
            if sequence != current["sequence"]:
                raise OdinTransitionError("transaction index snapshot sequence mismatch")
            if (
                record.get("live_devices") != current["live_devices"]
                or record.get("live_device_identities")
                != current["live_device_identities"]
                or record.get("stale_devices") != current["stale_devices"]
            ):
                raise OdinTransitionError("transaction index snapshot summary mismatch")
            last_snapshot_sequence = sequence
        else:
            phase = record.get("phase")
            if phase not in TRANSACTION_PHASES or phase != current["phase"]:
                raise OdinTransitionError("transaction index phase mismatch")
            phase_index = TRANSACTION_PHASES.index(phase)
            if phase_index <= last_phase_index:
                raise OdinTransitionError("transaction index phase order is invalid")
            last_phase_index = phase_index
    orphans = [record for path, record in known.items() if path not in seen_paths]
    if len(orphans) > 1:
        raise OdinTransitionError(
            f"multiple unindexed receipts cannot be crash-reconciled: {len(orphans)}"
        )
    if orphans:
        orphan = orphans[0]
        if "sequence" in orphan and orphan["sequence"] != len(snapshots) - 1:
            raise OdinTransitionError("unindexed snapshot is not the latest receipt")
        if "phase" in orphan and orphan["phase"] != phases[-1]["phase"]:
            raise OdinTransitionError("unindexed phase is not the latest receipt")
    return orphans


def _index_record_from_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    common = {
        "schema": INDEX_SCHEMA,
        "timestamp_utc": receipt["timestamp_utc"],
        "receipt": receipt["path"],
        "receipt_size": receipt["size"],
        "receipt_sha256": receipt["sha256"],
    }
    if "sequence" in receipt:
        return {
            **common,
            "record": "odin_snapshot",
            "sequence": receipt["sequence"],
            "live_devices": receipt["live_devices"],
            "live_device_identities": receipt["live_device_identities"],
            "stale_devices": receipt["stale_devices"],
            "recovered_after_receipt_publish": True,
        }
    return {
        **common,
        "record": "phase_receipt",
        "phase": receipt["phase"],
        "recovered_after_receipt_publish": True,
    }


def _reconcile_receipt_index_unlocked(run_dir: Path) -> None:
    snapshots = list_snapshot_receipts(run_dir)
    phases = list_phase_receipts(run_dir)
    orphans = _audit_index_against_receipts(run_dir, snapshots, phases)
    if orphans:
        receipt_directory = Path(orphans[0]["path"]).parent
        record = _index_record_from_receipt(orphans[0])
        record_bytes = _jsonl_record_bytes(record)
        _fsync_directory(receipt_directory)
        _fsync_directory(run_dir)
        _require_index_append_capacity(run_dir, len(record_bytes))
        _append_transaction_record_unlocked(run_dir, record)
        if _audit_index_against_receipts(run_dir, snapshots, phases):
            raise OdinTransitionError("receipt index reconciliation did not converge")


def _resume_tracker(
    run_dir: Path, sequence_start: int, *, lease: _TransactionLease
) -> tuple[EndpointGenerationTracker, list[dict[str, Any]]]:
    _require_active_lease(run_dir, lease)
    _reconcile_receipt_index_unlocked(run_dir)
    receipts = list_snapshot_receipts(run_dir)
    phases = list_phase_receipts(run_dir)
    if _audit_index_against_receipts(run_dir, receipts, phases):
        raise OdinTransitionError("transaction index still has an unindexed receipt")
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
        tracker.observe(
            tuple(tuple(value) for value in record["live_device_identities"])
        )
    return tracker, receipts


def _validate_ticket_against_receipts(
    run_dir: Path,
    ticket: EndpointTicket,
    receipts: list[dict[str, Any]],
) -> None:
    if (
        ticket.generation <= 0
        or ticket.snapshot_sequence < 0
        or ticket.snapshot_sequence >= len(receipts)
    ):
        raise OdinTransitionError("Odin endpoint ticket metadata is invalid")
    original = receipts[ticket.snapshot_sequence]
    expected_path = str(
        run_dir / "receipts" / f"odin-snapshot-{ticket.snapshot_sequence:06d}.json"
    )
    if (
        ticket.snapshot_receipt != expected_path
        or original["path"] != expected_path
        or ticket.snapshot_receipt_sha256 != original["sha256"]
        or original["live_device_identities"]
        != [[ticket.device, ticket.device_identity]]
    ):
        raise OdinTransitionError("Odin endpoint ticket receipt binding is invalid")
    tracker = EndpointGenerationTracker()
    generation = None
    for record in receipts[: ticket.snapshot_sequence + 1]:
        generation = tracker.observe(
            tuple(tuple(value) for value in record["live_device_identities"])
        )
    if generation != ticket.generation:
        raise OdinTransitionError("Odin endpoint ticket generation is invalid")


def _snapshot_and_record(
    odin: Path,
    run_dir: Path,
    sequence: int,
    *,
    runner: Runner,
    device_identity: DeviceIdentity,
    device_inventory: DeviceInventory,
    endpoint_observer_factory: EndpointObserverFactory | None,
    timestamp: Callable[[], str],
    enumeration_timeout_sec: float,
    lease: _TransactionLease,
    allow_empty_post_receipt_change: bool = False,
    allow_live_departure: bool = False,
) -> tuple[OdinSnapshot, dict[str, Any]]:
    if allow_empty_post_receipt_change and allow_live_departure:
        raise OdinTransitionError("snapshot transition policy is ambiguous")
    effective_runner = runner
    effective_observer_factory = endpoint_observer_factory
    raw_handles: list[raw_capture.RawCaptureHandle] = []
    if runner is _default_runner:
        effective_runner, raw_handles = _raw_first_runner(run_dir, sequence)
    if endpoint_observer_factory is measured_usbfs_observer:
        usbfs_capture_dir = raw_capture.prepare_capture_dir(
            run_dir, f"raw-usbfs-identity-{sequence:06d}"
        )
        effective_observer_factory = lambda: measured_usbfs_observer(
            usbfs_capture_dir
        )
    try:
        snapshot = enumerate_odin(
            odin,
            runner=effective_runner,
            device_identity=device_identity,
            device_inventory=device_inventory,
            endpoint_observer_factory=effective_observer_factory,
            allow_live_departure_race=allow_live_departure,
            allow_live_arrival_race=allow_empty_post_receipt_change,
            timeout_sec=enumeration_timeout_sec,
            timestamp=timestamp,
        )
    except OdinMeasuredEvidenceFailure as failure:
        try:
            _persist_measured_evidence_diagnostic(
                run_dir,
                sequence,
                failure,
                timestamp=timestamp,
                lease=lease,
            )
        except Exception:
            pass
        raise
    if runner is _default_runner:
        if len(raw_handles) != 1:
            raise OdinTransitionError(
                "Odin enumeration did not produce one durable raw capture"
            )
        snapshot = replace(
            snapshot,
            raw_capture_receipt=_raw_capture_identity(raw_handles[0]),
        )
    record = persist_snapshot(run_dir, sequence, snapshot, lease=lease)
    if effective_observer_factory is None:
        for device, expected_identity in snapshot.live_device_identities:
            if device_identity(device) != expected_identity:
                raise OdinTransitionError(
                    f"Odin endpoint identity changed while recording snapshot: {device}"
                )
    else:
        try:
            evidence = snapshot.endpoint_transition_evidence
            if evidence is None:
                raise OdinTransitionError(
                    "measured USB endpoint evidence is absent after receipt"
                )
            # Only endpoint-arrival polling may carry an empty receipt forward.
            # Tickets and terminal absence checks remain strictly revalidated.
            revalidator = _new_endpoint_observer(effective_observer_factory)
            if snapshot.live_devices and allow_live_departure:
                revalidator.revalidate_or_departure(evidence)
            elif snapshot.live_devices or not allow_empty_post_receipt_change:
                revalidator.revalidate(evidence)
        except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
            raise OdinTransitionError(
                "measured USB endpoint changed while recording snapshot"
            ) from exc
    return snapshot, record


def wait_for_single_live_endpoint(
    odin: Path,
    run_dir: Path,
    *,
    timeout_sec: float,
    lease: _TransactionLease,
    sequence_start: int = 0,
    poll_sec: float = 1.0,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    device_inventory: DeviceInventory = _default_device_inventory,
    endpoint_observer_factory: EndpointObserverFactory | None = None,
    timestamp: Callable[[], str] = live_core.utc_now,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> WaitResult:
    if (
        not math.isfinite(timeout_sec)
        or not math.isfinite(poll_sec)
        or timeout_sec <= 0
        or poll_sec < 0
    ):
        raise OdinTransitionError("endpoint timeout must be positive and poll non-negative")
    deadline = _deadline_after(_monotonic_now(monotonic), timeout_sec)
    sequence = sequence_start
    tracker, _receipts = _resume_tracker(run_dir, sequence_start, lease=lease)
    while True:
        remaining = deadline - _monotonic_now(monotonic)
        if remaining <= 0:
            return WaitResult(ticket=None, next_sequence=sequence, timed_out=True)
        try:
            snapshot, record = _snapshot_and_record(
                odin,
                run_dir,
                sequence,
                runner=runner,
                device_identity=device_identity,
                device_inventory=device_inventory,
                endpoint_observer_factory=endpoint_observer_factory,
                timestamp=timestamp,
                enumeration_timeout_sec=min(DEFAULT_ENUM_TIMEOUT_SEC, remaining),
                lease=lease,
                allow_empty_post_receipt_change=True,
            )
        except OdinEndpointArrivalRace:
            remaining = deadline - _monotonic_now(monotonic)
            if remaining <= 0:
                return WaitResult(ticket=None, next_sequence=sequence, timed_out=True)
            sleep(min(poll_sec, remaining))
            continue
        generation = tracker.observe(snapshot.live_device_identities)
        sequence += 1
        if _monotonic_now(monotonic) >= deadline:
            return WaitResult(ticket=None, next_sequence=sequence, timed_out=True)
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
        remaining = deadline - _monotonic_now(monotonic)
        if remaining <= 0:
            return WaitResult(ticket=None, next_sequence=sequence, timed_out=True)
        sleep(min(poll_sec, remaining))


def wait_for_no_live_endpoint(
    odin: Path,
    run_dir: Path,
    *,
    timeout_sec: float,
    lease: _TransactionLease,
    sequence_start: int = 0,
    poll_sec: float = 1.0,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    device_inventory: DeviceInventory = _default_device_inventory,
    endpoint_observer_factory: EndpointObserverFactory | None = None,
    allow_live_departure: bool = False,
    timestamp: Callable[[], str] = live_core.utc_now,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> AbsenceResult:
    if (
        not math.isfinite(timeout_sec)
        or not math.isfinite(poll_sec)
        or timeout_sec <= 0
        or poll_sec < 0
    ):
        raise OdinTransitionError("disconnect timeout must be positive and poll non-negative")
    deadline = _deadline_after(_monotonic_now(monotonic), timeout_sec)
    sequence = sequence_start
    _resume_tracker(run_dir, sequence_start, lease=lease)
    while True:
        remaining = deadline - _monotonic_now(monotonic)
        if remaining <= 0:
            return AbsenceResult(absent=False, next_sequence=sequence, timed_out=True)
        snapshot, _ = _snapshot_and_record(
            odin,
            run_dir,
            sequence,
            runner=runner,
            device_identity=device_identity,
            device_inventory=device_inventory,
            endpoint_observer_factory=endpoint_observer_factory,
            timestamp=timestamp,
            enumeration_timeout_sec=min(DEFAULT_ENUM_TIMEOUT_SEC, remaining),
            lease=lease,
            allow_live_departure=allow_live_departure,
        )
        sequence += 1
        if len(snapshot.live_devices) > 1:
            raise OdinTransitionError(
                f"ambiguous live Odin endpoints: {list(snapshot.live_devices)}"
            )
        if _monotonic_now(monotonic) >= deadline:
            return AbsenceResult(absent=False, next_sequence=sequence, timed_out=True)
        if not snapshot.live_devices:
            return AbsenceResult(absent=True, next_sequence=sequence, timed_out=False)
        remaining = deadline - _monotonic_now(monotonic)
        if remaining <= 0:
            return AbsenceResult(absent=False, next_sequence=sequence, timed_out=True)
        sleep(min(poll_sec, remaining))


def revalidate_endpoint_ticket(
    odin: Path,
    run_dir: Path,
    ticket: EndpointTicket,
    *,
    sequence: int,
    lease: _TransactionLease,
    timeout_sec: float,
    runner: Runner = _default_runner,
    device_identity: DeviceIdentity = _default_device_identity,
    device_inventory: DeviceInventory = _default_device_inventory,
    endpoint_observer_factory: EndpointObserverFactory | None = None,
    timestamp: Callable[[], str] = live_core.utc_now,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise OdinTransitionError("revalidation timeout must be positive")
    deadline = _deadline_after(_monotonic_now(monotonic), timeout_sec)
    tracker, receipts = _resume_tracker(run_dir, sequence, lease=lease)
    _validate_ticket_against_receipts(run_dir, ticket, receipts)
    remaining = deadline - _monotonic_now(monotonic)
    if remaining <= 0:
        raise OdinTransitionError("Odin endpoint revalidation deadline expired")
    snapshot, record = _snapshot_and_record(
        odin,
        run_dir,
        sequence,
        runner=runner,
        device_identity=device_identity,
        device_inventory=device_inventory,
        endpoint_observer_factory=endpoint_observer_factory,
        timestamp=timestamp,
        enumeration_timeout_sec=min(DEFAULT_ENUM_TIMEOUT_SEC, remaining),
        lease=lease,
    )
    observed_identity = (
        snapshot.live_device_identities[0][1]
        if len(snapshot.live_device_identities) == 1
        else None
    )
    observed_generation = tracker.observe(snapshot.live_device_identities)
    if (
        _monotonic_now(monotonic) >= deadline
        or snapshot.live_devices != (ticket.device,)
        or observed_identity != ticket.device_identity
        or observed_generation != ticket.generation
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
