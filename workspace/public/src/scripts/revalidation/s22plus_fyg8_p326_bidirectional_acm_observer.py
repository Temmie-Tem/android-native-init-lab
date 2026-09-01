#!/usr/bin/env python3
"""P3.26 exact-lane CDC ACM observer with two fixed host-to-device writes."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
import select
import stat
import termios
import time
from typing import Any, Iterator

import device_action_cdc_acm_observer_v1 as observer
import s22plus_fyg8_p325_cdc_acm_guard_adapter as p325
import s22plus_fyg8_p326_bidirectional_console_runtime as runtime


SCHEMA = "s22plus_fyg8_p326_bidirectional_acm_receipt_v1"
CONTRACT_ID = "s22plus-fyg8-p326-bidirectional-acm-v1"
TARGET = runtime.TARGET
RECEIPT_NAME = "p326-candidate-observer-roundtrip.json"
TRAILING_QUIET_SEC = 0.05
MAX_TRAILING_CAPTURE = 1
P325_SOURCE = Path(p325.__file__).resolve()
P325_SOURCE_IDENTITY = {
    "size": 6_295,
    "sha256": "13d4ba6ee935d5b7a73d06f0e4e7ef34b5ac567fbed89813113205f87f34a648",
}


class P326ObserverError(ValueError):
    """The P3.26 transcript, exact tty, or inherited observer differs."""


def _identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _file_receipt(path: Path, label: str) -> dict[str, Any]:
    direct = path.absolute()
    try:
        before = direct.lstat()
        payload = direct.read_bytes()
        after = direct.lstat()
    except OSError as exc:
        raise P326ObserverError(f"{label} is unavailable") from exc
    inode = lambda value: (  # noqa: E731
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or stat.S_IMODE(before.st_mode) != 0o400
        or inode(before) != inode(after)
    ):
        raise P326ObserverError(f"{label} changed")
    return {"path": str(direct), **_identity(payload)}


def _validate_base() -> None:
    try:
        payload = P325_SOURCE.read_bytes()
    except OSError as exc:
        raise P326ObserverError("P325 observer adapter is unavailable") from exc
    if _identity(payload) != P325_SOURCE_IDENTITY:
        raise P326ObserverError("P325 observer adapter identity differs")
    if p325.CONTRACT_ID != "s22plus-fyg8-p325-cdc-acm-guard-tty-node-v1":
        raise P326ObserverError("P325 observer contract differs")


@dataclass
class RoundTripAudit:
    tx: bytearray = field(default_factory=bytearray)
    trailing_rx: bytearray = field(default_factory=bytearray)
    banner_seen: bool = False
    pong_seen: bool = False
    shell_ok_seen: bool = False
    endpoint_identity_sha256: str | None = None


def _read_segment(
    descriptor: int,
    expected: bytes,
    deadline: float,
    writer: Any,
) -> bool:
    payload = bytearray()
    while len(payload) < len(expected) and time.monotonic() < deadline:
        readable, _, _ = select.select(
            [descriptor], [], [], min(0.1, max(0.0, deadline - time.monotonic()))
        )
        if not readable:
            continue
        try:
            chunk = os.read(descriptor, len(expected) - len(payload))
        except BlockingIOError:
            continue
        if not chunk:
            continue
        payload.extend(chunk)
        writer.write_stdout(chunk)
    return bytes(payload) == expected


def _write_segment(
    descriptor: int,
    payload: bytes,
    deadline: float,
    audit: RoundTripAudit,
) -> bool:
    written = 0
    while written < len(payload) and time.monotonic() < deadline:
        _, writable, _ = select.select(
            [], [descriptor], [], min(0.1, max(0.0, deadline - time.monotonic()))
        )
        if not writable:
            continue
        try:
            amount = os.write(descriptor, payload[written:])
        except BlockingIOError:
            continue
        if amount <= 0 or amount > len(payload) - written:
            return False
        audit.tx.extend(payload[written : written + amount])
        written += amount
    return written == len(payload)


def _reject_trailing(
    descriptor: int,
    deadline: float,
    writer: Any,
    audit: RoundTripAudit,
) -> bool:
    quiet_deadline = min(deadline, time.monotonic() + TRAILING_QUIET_SEC)
    while time.monotonic() < quiet_deadline:
        readable, _, _ = select.select(
            [descriptor],
            [],
            [],
            min(0.01, max(0.0, quiet_deadline - time.monotonic())),
        )
        if not readable:
            continue
        try:
            chunk = os.read(descriptor, MAX_TRAILING_CAPTURE)
        except BlockingIOError:
            continue
        if not chunk:
            return True
        writer.write_stdout(chunk)
        audit.trailing_rx.extend(chunk)
        return False
    return True


def _exchange(
    descriptor: int,
    deadline: float,
    writer: Any,
    audit: RoundTripAudit,
) -> bool:
    audit.banner_seen = _read_segment(
        descriptor, runtime.DEVICE_BANNER, deadline, writer
    )
    if not audit.banner_seen:
        return False
    if not _write_segment(descriptor, runtime.HOST_PING, deadline, audit):
        return False
    audit.pong_seen = _read_segment(
        descriptor, runtime.DEVICE_PONG, deadline, writer
    )
    if not audit.pong_seen:
        return False
    if not _write_segment(descriptor, runtime.HOST_SHELL, deadline, audit):
        return False
    audit.shell_ok_seen = _read_segment(
        descriptor, runtime.DEVICE_SHELL_OK, deadline, writer
    )
    return audit.shell_ok_seen and _reject_trailing(
        descriptor, deadline, writer, audit
    )


@contextlib.contextmanager
def _adapt(base: observer.ObserverSession) -> Iterator[RoundTripAudit]:
    original_read = base._read_endpoint
    audit = RoundTripAudit()

    def read_endpoint(
        endpoint: observer.Endpoint,
        deadline: float,
        writer: Any,
    ) -> str:
        path = base.dev_root / endpoint.tty_name
        if not base.guard.healthy(recheck=True):
            return "guard-lost"
        # P325 proved that the two ModemManager properties live on tty_class.
        if not base.guard.matches_node(endpoint.tty_class):
            return "identity-mismatch"
        try:
            info = path.stat()
            if (
                not stat.S_ISCHR(info.st_mode)
                or os.major(info.st_rdev) != endpoint.major
                or os.minor(info.st_rdev) != endpoint.minor
            ):
                return "identity-mismatch"
            descriptor = os.open(
                path,
                os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK | os.O_CLOEXEC,
            )
        except OSError:
            return "open-failed"
        try:
            try:
                fcntl.ioctl(descriptor, termios.TIOCEXCL)
            except OSError:
                return "exclusive-failed"
            if not base.guard.healthy(recheck=True):
                return "guard-lost"
            try:
                base._raw_tty(descriptor)
            except (OSError, termios.error):
                return "open-failed"

            if not _exchange(descriptor, deadline, writer, audit):
                return "captured"

            guard_healthy = base.guard.healthy(recheck=True)
            guard_matches = (
                base.guard.matches_node(endpoint.tty_class)
                if guard_healthy
                else False
            )
            identity, repeated = observer._resolve_endpoint(endpoint.tty_class)  # noqa: SLF001
            topology = observer.TOPOLOGY_RE.fullmatch(base.topology)
            assert topology is not None
            if (
                repeated.identity_sha256 != endpoint.identity_sha256
                or not observer._matches(base.spec, topology.group(1), identity, repeated)  # noqa: SLF001
                or os.fstat(descriptor).st_rdev != info.st_rdev
            ):
                return "captured-identity-mismatch"
            if not guard_healthy:
                return "captured-guard-lost"
            if not guard_matches:
                return "captured-identity-mismatch"
            audit.endpoint_identity_sha256 = endpoint.identity_sha256
            return "captured"
        finally:
            os.close(descriptor)

    base._read_endpoint = read_endpoint  # type: ignore[method-assign]
    try:
        yield audit
    finally:
        base._read_endpoint = original_read  # type: ignore[method-assign]


@dataclass
class P326ObserverSession:
    delegate: Any
    base: observer.ObserverSession
    run_dir: Path
    audit: RoundTripAudit

    def observe(
        self, *, timeout_sec: int, download_departure: dict[str, Any]
    ) -> dict[str, Any]:
        result = self.delegate.observe(
            timeout_sec=timeout_sec, download_departure=download_departure
        )
        tx = bytes(self.audit.tx)
        accepted = (
            result.get("accepted") is True
            and self.audit.banner_seen
            and self.audit.pong_seen
            and self.audit.shell_ok_seen
            and not self.audit.trailing_rx
            and tx == runtime.HOST_TRANSCRIPT
            and self.audit.endpoint_identity_sha256
            == result.get("endpoint_identity_sha256")
        )
        receipt = {
            "schema": SCHEMA,
            "contract_id": CONTRACT_ID,
            "target": TARGET,
            "base_observer": _file_receipt(
                self.run_dir / "candidate-observer.json",
                "P326 base observer receipt",
            ),
            "tx_hex": tx.hex(),
            "tx": _identity(tx),
            "rx": _identity(runtime.DEVICE_TRANSCRIPT),
            "trailing_rx": _identity(bytes(self.audit.trailing_rx)),
            "trailing_bytes_seen": len(self.audit.trailing_rx),
            "banner_seen": self.audit.banner_seen,
            "pid1_pong_seen": self.audit.pong_seen,
            "busybox_shell_ok_seen": self.audit.shell_ok_seen,
            "endpoint_identity_sha256": self.audit.endpoint_identity_sha256,
            "accepted": accepted,
            "host_usb_write_count": 2,
            "host_usb_write_bytes": len(tx),
            "fixed_candidate_channel_only": True,
            "adb_commands": 0,
            "odin_invocations": 0,
        }
        observer.persist_json(self.run_dir / RECEIPT_NAME, receipt)
        projected = dict(result)
        projected["accepted"] = accepted
        projected["exact"] = accepted
        if not accepted and result.get("accepted") is True:
            projected["classification"] = "byte-mismatch"
        return projected

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


@contextlib.contextmanager
def observer_session(
    spec: dict[str, str],
    source_topology: str,
    run_dir: Path,
    binding: dict[str, str],
    lane_binding: dict[str, Any],
    lane_binding_receipt: dict[str, Any],
    **kwargs: Any,
) -> Iterator[P326ObserverSession]:
    _validate_base()
    if observer.expected_banner(spec) != runtime.DEVICE_TRANSCRIPT:
        raise P326ObserverError("P326 expected transcript differs")
    with p325.observer_session(
        spec,
        source_topology,
        run_dir,
        binding,
        lane_binding,
        lane_binding_receipt,
        **kwargs,
    ) as inherited:
        base = inherited.delegate.delegate
        if not isinstance(base, observer.ObserverSession):
            raise P326ObserverError("P326 base observer shape differs")
        with _adapt(base) as audit:
            yield P326ObserverSession(inherited, base, run_dir, audit)


def _strict_json(path: Path) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise P326ObserverError("P326 receipt has duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise P326ObserverError("P326 receipt is unreadable") from exc
    if not isinstance(value, dict):
        raise P326ObserverError("P326 receipt is not an object")
    return value


def validate_receipt(
    run_dir: Path,
    *,
    spec: dict[str, str],
    binding: dict[str, str],
    source_topology: str,
    lane_binding: dict[str, Any],
    lane_binding_receipt: dict[str, Any],
) -> dict[str, Any]:
    try:
        base = p325.validate_receipt(
            run_dir,
            spec=spec,
            binding=binding,
            source_topology=source_topology,
            lane_binding=lane_binding,
            lane_binding_receipt=lane_binding_receipt,
        )
    except Exception as exc:
        raise P326ObserverError(str(exc)) from exc
    value = _strict_json(run_dir / RECEIPT_NAME)
    expected_keys = {
        "schema", "contract_id", "target", "base_observer", "tx_hex", "tx",
        "rx", "trailing_rx", "trailing_bytes_seen", "banner_seen",
        "pid1_pong_seen", "busybox_shell_ok_seen",
        "endpoint_identity_sha256", "accepted", "host_usb_write_count",
        "host_usb_write_bytes", "fixed_candidate_channel_only", "adb_commands",
        "odin_invocations",
    }
    try:
        tx = bytes.fromhex(value.get("tx_hex", ""))
    except (TypeError, ValueError) as exc:
        raise P326ObserverError("P326 tx encoding differs") from exc
    base_receipt = _file_receipt(
        run_dir / "candidate-observer.json", "P326 base observer receipt"
    )
    if (
        set(value) != expected_keys
        or value["schema"] != SCHEMA
        or value["contract_id"] != CONTRACT_ID
        or value["target"] != TARGET
        or value["base_observer"] != base_receipt
        or value["tx"] != _identity(tx)
        or tx != runtime.HOST_TRANSCRIPT
        or value["rx"] != _identity(runtime.DEVICE_TRANSCRIPT)
        or value["trailing_rx"] != _identity(b"")
        or value["trailing_bytes_seen"] != 0
        or value["banner_seen"] is not True
        or value["pid1_pong_seen"] is not True
        or value["busybox_shell_ok_seen"] is not True
        or value["endpoint_identity_sha256"] != base.get("endpoint_identity_sha256")
        or value["accepted"] is not True
        or value["host_usb_write_count"] != 2
        or value["host_usb_write_bytes"] != len(runtime.HOST_TRANSCRIPT)
        or value["fixed_candidate_channel_only"] is not True
        or value["adb_commands"] != 0
        or value["odin_invocations"] != 0
        or base.get("accepted") is not True
    ):
        raise P326ObserverError("P326 round-trip receipt differs")
    return dict(base) | {
        "p326_roundtrip": value,
        "pid1_bidirectional_proof": True,
        "busybox_shell_roundtrip_proof": True,
    }


__all__ = [
    "CONTRACT_ID",
    "P326ObserverError",
    "P326ObserverSession",
    "P325_SOURCE_IDENTITY",
    "RECEIPT_NAME",
    "RoundTripAudit",
    "SCHEMA",
    "TARGET",
    "observer_session",
    "validate_receipt",
]
