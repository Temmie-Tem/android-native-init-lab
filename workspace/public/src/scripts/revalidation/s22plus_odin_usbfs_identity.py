#!/usr/bin/env python3
"""Measured usbfs endpoint identity for Odin enumeration gates.

This module distinguishes replacement-sensitive node identity from the three
timestamps that an observed ``odin4 -l`` invocation may update.  It owns no
target, live authorization, transfer command, artifact, or proof verdict.
Callers must opt in explicitly and must persist the returned transition
evidence through their transaction harness.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


EVIDENCE_SCHEMA = "s22plus_odin_usbfs_node_transition_v1"
ENUMERATION_EVIDENCE_SCHEMA = "s22plus_odin_usbfs_enumeration_transition_v1"
IDENTITY_PREFIX = "usbfs-immutable-v1:"
USBFS_ROOT = Path("/dev/bus/usb")
STAT_BINARY = Path("/usr/bin/stat")
USBFS_PATH_RE = re.compile(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})")
MAX_INVENTORY_ENTRIES = 4096
MAX_BIRTH_OUTPUT_BYTES = 1024

MUTABLE_METADATA_FIELDS = (
    "st_atime_ns",
    "st_ctime_ns",
    "st_mtime_ns",
)
IMMUTABLE_IDENTITY_FIELDS = (
    "path",
    "st_dev",
    "st_ino",
    "st_rdev",
    "st_nlink",
    "st_file_type",
    "st_mode",
    "st_uid",
    "st_gid",
    "birth_time_ns",
    "device_major",
    "device_minor",
)
ALL_NODE_FIELDS = IMMUTABLE_IDENTITY_FIELDS + MUTABLE_METADATA_FIELDS


class UsbfsIdentityError(RuntimeError):
    pass


class UsbfsInventoryArrival(UsbfsIdentityError):
    """One new usbfs node appeared while all baseline nodes stayed stable."""

    def __init__(self, path: str):
        super().__init__(f"usbfs node arrived during enumeration: {path}")
        self.path = path


@dataclass(frozen=True)
class UsbfsNodeSnapshot:
    path: str
    st_dev: int
    st_ino: int
    st_rdev: int
    st_nlink: int
    st_file_type: int
    st_mode: int
    st_uid: int
    st_gid: int
    birth_time_ns: int
    device_major: int
    device_minor: int
    st_atime_ns: int
    st_ctime_ns: int
    st_mtime_ns: int


NodeSnapshotter = Callable[[str], UsbfsNodeSnapshot]
InventoryReader = Callable[[], dict[str, UsbfsNodeSnapshot]]


def _canonical_json_bytes(value: Any) -> bytes:
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


def _validated_usbfs_coordinates(path: str) -> tuple[int, int]:
    match = USBFS_PATH_RE.fullmatch(path)
    if match is None:
        raise UsbfsIdentityError(f"invalid usbfs endpoint path: {path}")
    bus, device = (int(value) for value in match.groups())
    if bus <= 0 or device <= 0:
        raise UsbfsIdentityError(f"invalid usbfs endpoint coordinates: {path}")
    return bus, device


def _validate_snapshot(snapshot: UsbfsNodeSnapshot) -> None:
    if not isinstance(snapshot, UsbfsNodeSnapshot):
        raise UsbfsIdentityError("usbfs snapshot has an invalid type")
    bus, device = _validated_usbfs_coordinates(snapshot.path)
    values = asdict(snapshot)
    for name, value in values.items():
        if name == "path" or name == "birth_time_ns":
            continue
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise UsbfsIdentityError(f"usbfs snapshot field is invalid: {name}")
    if (
        not isinstance(snapshot.birth_time_ns, int)
        or isinstance(snapshot.birth_time_ns, bool)
        or snapshot.birth_time_ns < 0
    ):
        raise UsbfsIdentityError("usbfs birth time is invalid")
    expected_minor = (bus - 1) * 128 + device - 1
    if (
        snapshot.st_file_type != stat.S_IFCHR
        or snapshot.device_major != 189
        or snapshot.device_minor != expected_minor
        or os.major(snapshot.st_rdev) != snapshot.device_major
        or os.minor(snapshot.st_rdev) != snapshot.device_minor
        or snapshot.st_nlink != 1
    ):
        raise UsbfsIdentityError("usbfs snapshot device relation is invalid")


def parse_birth_time_ns(value: str) -> int | None:
    if value == "-":
        return None
    match = re.fullmatch(
        r"(20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})"
        r"\.([0-9]{1,9}) ([+-][0-9]{4})",
        value,
    )
    if match is None:
        raise UsbfsIdentityError("usbfs birth-time output is malformed")
    base, fraction, offset = match.groups()
    try:
        instant = datetime.strptime(f"{base} {offset}", "%Y-%m-%d %H:%M:%S %z")
    except ValueError as exc:
        raise UsbfsIdentityError("usbfs birth-time output is malformed") from exc
    return int(instant.timestamp()) * 1_000_000_000 + int(fraction.ljust(9, "0"))


def read_birth_time_ns(path: str) -> int | None:
    _validated_usbfs_coordinates(path)
    try:
        resolved_stat = STAT_BINARY.resolve(strict=True)
        descriptor = os.open(
            resolved_stat,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
        )
    except OSError as exc:
        raise UsbfsIdentityError("birth-time reader executable is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise UsbfsIdentityError("birth-time reader is not a regular file")
        try:
            result = subprocess.run(
                ["stat", "--printf=%w", "--", path],
                executable=f"/proc/self/fd/{descriptor}",
                pass_fds=(descriptor,),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UsbfsIdentityError(f"usbfs birth-time read failed: {path}") from exc
        after = os.fstat(descriptor)
        if _stat_identity_for_executable(before) != _stat_identity_for_executable(after):
            raise UsbfsIdentityError("birth-time reader changed during execution")
    finally:
        os.close(descriptor)
    if (
        result.returncode != 0
        or result.stderr
        or len(result.stdout) > MAX_BIRTH_OUTPUT_BYTES
    ):
        raise UsbfsIdentityError(f"usbfs birth-time read failed: {path}")
    try:
        value = result.stdout.decode("ascii")
    except UnicodeDecodeError as exc:
        raise UsbfsIdentityError("usbfs birth-time output is not ASCII") from exc
    return parse_birth_time_ns(value)


def _stat_identity_for_executable(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _stat_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_rdev,
        metadata.st_nlink,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_atime_ns,
        metadata.st_ctime_ns,
        metadata.st_mtime_ns,
    )


def snapshot_node(
    path: str,
    *,
    birth_reader: Callable[[str], int | None] = read_birth_time_ns,
) -> UsbfsNodeSnapshot:
    _validated_usbfs_coordinates(path)
    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISCHR(before.st_mode) or before.st_nlink != 1:
        raise UsbfsIdentityError(f"usbfs endpoint is not a direct character device: {path}")
    birth_time = birth_reader(path)
    if birth_time is None:
        raise UsbfsIdentityError(f"usbfs endpoint has no birth time: {path}")
    after = os.stat(path, follow_symlinks=False)
    if _stat_identity(before) != _stat_identity(after):
        raise UsbfsIdentityError(f"usbfs endpoint changed during snapshot: {path}")
    snapshot = UsbfsNodeSnapshot(
        path=path,
        st_dev=after.st_dev,
        st_ino=after.st_ino,
        st_rdev=after.st_rdev,
        st_nlink=after.st_nlink,
        st_file_type=stat.S_IFMT(after.st_mode),
        st_mode=stat.S_IMODE(after.st_mode),
        st_uid=after.st_uid,
        st_gid=after.st_gid,
        birth_time_ns=birth_time,
        device_major=os.major(after.st_rdev),
        device_minor=os.minor(after.st_rdev),
        st_atime_ns=after.st_atime_ns,
        st_ctime_ns=after.st_ctime_ns,
        st_mtime_ns=after.st_mtime_ns,
    )
    _validate_snapshot(snapshot)
    return snapshot


def capture_inventory(
    *,
    root: Path = USBFS_ROOT,
    snapshotter: NodeSnapshotter = snapshot_node,
) -> dict[str, UsbfsNodeSnapshot]:
    if not root.is_dir():
        return {}
    try:
        paths = sorted(root.glob("[0-9][0-9][0-9]/[0-9][0-9][0-9]"))
    except OSError as exc:
        raise UsbfsIdentityError("usbfs inventory failed") from exc
    inventory: dict[str, UsbfsNodeSnapshot] = {}
    for path in paths:
        encoded = str(USBFS_ROOT / path.relative_to(root))
        if USBFS_PATH_RE.fullmatch(encoded) is None:
            continue
        try:
            snapshot = snapshotter(encoded)
        except (OSError, UsbfsIdentityError) as exc:
            raise UsbfsIdentityError(f"usbfs inventory is incomplete: {encoded}") from exc
        _validate_snapshot(snapshot)
        if snapshot.path != encoded:
            raise UsbfsIdentityError("usbfs inventory path/snapshot mismatch")
        inventory[encoded] = snapshot
        if len(inventory) > MAX_INVENTORY_ENTRIES:
            raise UsbfsIdentityError("usbfs inventory exceeds bound")
    return inventory


def immutable_identity(snapshot: UsbfsNodeSnapshot) -> str:
    _validate_snapshot(snapshot)
    value = asdict(snapshot)
    identity = {name: value[name] for name in IMMUTABLE_IDENTITY_FIELDS}
    return IDENTITY_PREFIX + hashlib.sha256(_canonical_json_bytes(identity)).hexdigest()


def transition_evidence(
    before: UsbfsNodeSnapshot,
    after: UsbfsNodeSnapshot,
) -> dict[str, Any]:
    _validate_snapshot(before)
    _validate_snapshot(after)
    if before.path != after.path:
        raise UsbfsIdentityError("usbfs transition path changed")
    left = asdict(before)
    right = asdict(after)
    immutable_changes = tuple(
        name for name in IMMUTABLE_IDENTITY_FIELDS if left[name] != right[name]
    )
    metadata_changes = tuple(
        name for name in MUTABLE_METADATA_FIELDS if left[name] != right[name]
    )
    if immutable_changes:
        raise UsbfsIdentityError(
            "usbfs immutable endpoint identity changed: " + ",".join(immutable_changes)
        )
    identity_before = immutable_identity(before)
    identity_after = immutable_identity(after)
    if identity_before != identity_after:
        raise UsbfsIdentityError("usbfs immutable identity digest changed")
    evidence = {
        "schema": EVIDENCE_SCHEMA,
        "path": before.path,
        "identity": identity_before,
        "before": left,
        "after": right,
        "immutable_changes": list(immutable_changes),
        "metadata_changes": list(metadata_changes),
        "allowed_metadata_fields": list(MUTABLE_METADATA_FIELDS),
    }
    validate_transition_evidence(evidence)
    return evidence


def validate_transition_evidence(evidence: Any) -> None:
    expected_keys = {
        "schema",
        "path",
        "identity",
        "before",
        "after",
        "immutable_changes",
        "metadata_changes",
        "allowed_metadata_fields",
    }
    if not isinstance(evidence, dict) or set(evidence) != expected_keys:
        raise UsbfsIdentityError("usbfs transition evidence shape is invalid")
    if (
        evidence["schema"] != EVIDENCE_SCHEMA
        or not isinstance(evidence["identity"], str)
        or not evidence["identity"].startswith(IDENTITY_PREFIX)
        or evidence["allowed_metadata_fields"] != list(MUTABLE_METADATA_FIELDS)
        or evidence["immutable_changes"] != []
    ):
        raise UsbfsIdentityError("usbfs transition evidence policy is invalid")
    before = evidence["before"]
    after = evidence["after"]
    if (
        not isinstance(before, dict)
        or not isinstance(after, dict)
        or set(before) != set(ALL_NODE_FIELDS)
        or set(after) != set(ALL_NODE_FIELDS)
        or evidence["path"] != before.get("path")
        or evidence["path"] != after.get("path")
    ):
        raise UsbfsIdentityError("usbfs transition snapshots are invalid")
    changed = [
        name for name in MUTABLE_METADATA_FIELDS if before[name] != after[name]
    ]
    if evidence["metadata_changes"] != changed:
        raise UsbfsIdentityError("usbfs transition metadata diff is invalid")
    if any(before[name] != after[name] for name in IMMUTABLE_IDENTITY_FIELDS):
        raise UsbfsIdentityError("usbfs transition immutable fields changed")
    try:
        before_snapshot = UsbfsNodeSnapshot(**before)
        after_snapshot = UsbfsNodeSnapshot(**after)
    except TypeError as exc:
        raise UsbfsIdentityError("usbfs transition snapshot shape is invalid") from exc
    _validate_snapshot(before_snapshot)
    _validate_snapshot(after_snapshot)
    if (
        immutable_identity(before_snapshot) != evidence["identity"]
        or immutable_identity(after_snapshot) != evidence["identity"]
    ):
        raise UsbfsIdentityError("usbfs transition identity digest is invalid")


def revalidate_transition_evidence(
    evidence: dict[str, Any],
    *,
    snapshotter: NodeSnapshotter = snapshot_node,
) -> str:
    """Recheck immutable identity after a transition receipt is published."""

    validate_transition_evidence(evidence)
    previous = UsbfsNodeSnapshot(**evidence["after"])
    current = snapshotter(evidence["path"])
    follow_up = transition_evidence(previous, current)
    if follow_up["identity"] != evidence["identity"]:
        raise UsbfsIdentityError("usbfs post-receipt identity changed")
    return follow_up["identity"]


def enumeration_evidence(
    before: dict[str, UsbfsNodeSnapshot],
    after: dict[str, UsbfsNodeSnapshot],
    live_devices: tuple[str, ...],
) -> dict[str, Any]:
    if (
        not isinstance(before, dict)
        or not isinstance(after, dict)
        or len(before) > MAX_INVENTORY_ENTRIES
        or len(after) > MAX_INVENTORY_ENTRIES
    ):
        raise UsbfsIdentityError("usbfs enumeration inventory is invalid")
    before_paths = tuple(sorted(before))
    after_paths = tuple(sorted(after))
    if before_paths != after_paths:
        raise UsbfsIdentityError("usbfs inventory membership changed during enumeration")
    if tuple(sorted(set(live_devices))) != live_devices or not set(live_devices) <= set(
        before_paths
    ):
        raise UsbfsIdentityError("usbfs live-device inventory binding is invalid")
    transitions: list[dict[str, Any]] = []
    for path in before_paths:
        if before[path].path != path or after[path].path != path:
            raise UsbfsIdentityError("usbfs inventory path/snapshot mismatch")
        transitions.append(transition_evidence(before[path], after[path]))
    evidence = {
        "schema": ENUMERATION_EVIDENCE_SCHEMA,
        "inventory_paths": list(before_paths),
        "live_devices": list(live_devices),
        "node_transitions": transitions,
    }
    validate_enumeration_evidence(evidence)
    return evidence


def validate_enumeration_evidence(evidence: Any) -> None:
    if not isinstance(evidence, dict) or set(evidence) != {
        "schema",
        "inventory_paths",
        "live_devices",
        "node_transitions",
    }:
        raise UsbfsIdentityError("usbfs enumeration evidence shape is invalid")
    inventory_paths = evidence["inventory_paths"]
    live_devices = evidence["live_devices"]
    transitions = evidence["node_transitions"]
    if (
        evidence["schema"] != ENUMERATION_EVIDENCE_SCHEMA
        or not isinstance(inventory_paths, list)
        or not isinstance(live_devices, list)
        or not isinstance(transitions, list)
        or len(inventory_paths) > MAX_INVENTORY_ENTRIES
        or inventory_paths != sorted(set(inventory_paths))
        or live_devices != sorted(set(live_devices))
        or not set(live_devices) <= set(inventory_paths)
        or len(transitions) != len(inventory_paths)
        or any(not isinstance(value, dict) for value in transitions)
    ):
        raise UsbfsIdentityError("usbfs enumeration evidence is invalid")
    for path in inventory_paths:
        _validated_usbfs_coordinates(path)
    for transition in transitions:
        validate_transition_evidence(transition)
    if [value["path"] for value in transitions] != inventory_paths:
        raise UsbfsIdentityError("usbfs enumeration transition order is invalid")


def _exact_single_arrival_path(
    before: dict[str, UsbfsNodeSnapshot],
    after: dict[str, UsbfsNodeSnapshot],
) -> str | None:
    before_paths = set(before)
    after_paths = set(after)
    arrivals = after_paths - before_paths
    if len(arrivals) != 1 or before_paths != after_paths - arrivals:
        return None
    for path in sorted(before_paths):
        transition_evidence(before[path], after[path])
    arrival = next(iter(arrivals))
    _validate_snapshot(after[arrival])
    if after[arrival].path != arrival:
        raise UsbfsIdentityError("usbfs arrival path/snapshot mismatch")
    return arrival


class MeasuredUsbfsIdentityObserver:
    """Stateful adapter for one bounded Odin enumeration invocation."""

    def __init__(
        self,
        *,
        inventory_reader: InventoryReader = capture_inventory,
    ) -> None:
        self._inventory_reader = inventory_reader
        self._baseline: dict[str, UsbfsNodeSnapshot] | None = None
        self._after: dict[str, UsbfsNodeSnapshot] | None = None

    def inventory(self) -> dict[str, str]:
        if self._baseline is not None:
            raise UsbfsIdentityError("usbfs observer cannot be reused across enumerations")
        baseline = self._inventory_reader()
        if not isinstance(baseline, dict) or len(baseline) > MAX_INVENTORY_ENTRIES:
            raise UsbfsIdentityError("usbfs observer inventory is invalid")
        identities: dict[str, str] = {}
        for path, snapshot in sorted(baseline.items()):
            _validate_snapshot(snapshot)
            if path != snapshot.path:
                raise UsbfsIdentityError("usbfs observer inventory path mismatch")
            identities[path] = immutable_identity(snapshot)
        self._baseline = dict(baseline)
        return identities

    def _after_inventory(
        self, *, allow_membership_change: bool = False
    ) -> dict[str, UsbfsNodeSnapshot]:
        if self._baseline is None:
            raise UsbfsIdentityError("usbfs observer inventory was not captured")
        if self._after is None:
            after = self._inventory_reader()
            if not isinstance(after, dict) or len(after) > MAX_INVENTORY_ENTRIES:
                raise UsbfsIdentityError("usbfs observer inventory is invalid")
            for path, snapshot in sorted(after.items()):
                _validate_snapshot(snapshot)
                if path != snapshot.path:
                    raise UsbfsIdentityError("usbfs observer inventory path mismatch")
            if not allow_membership_change:
                arrival = _exact_single_arrival_path(self._baseline, after)
                if arrival is not None:
                    raise UsbfsInventoryArrival(arrival)
                enumeration_evidence(self._baseline, after, ())
            self._after = dict(after)
        return self._after

    def identity(self, path: str) -> str | None:
        current = self._after_inventory().get(path)
        return None if current is None else immutable_identity(current)

    def evidence(self, live_devices: tuple[str, ...]) -> dict[str, Any]:
        if self._baseline is None:
            raise UsbfsIdentityError("usbfs observer inventory was not captured")
        return enumeration_evidence(
            self._baseline,
            self._after_inventory(),
            live_devices,
        )

    def identity_or_exact_departure(self, path: str) -> str | None:
        """Return identity or accept removal of only the named baseline node."""

        _validated_usbfs_coordinates(path)
        if self._baseline is None or path not in self._baseline:
            raise UsbfsIdentityError("usbfs departure baseline is invalid")
        after = self._after_inventory(allow_membership_change=True)
        current = after.get(path)
        if current is not None:
            return immutable_identity(current)
        expected = {
            current_path: snapshot
            for current_path, snapshot in self._baseline.items()
            if current_path != path
        }
        if tuple(sorted(after)) != tuple(sorted(expected)):
            raise UsbfsIdentityError(
                "usbfs inventory is not an exact during-enumeration departure"
            )
        enumeration_evidence(expected, after, ())
        return None

    def evidence_after_exact_departure(self, path: str) -> dict[str, Any]:
        """Describe the already-validated inventory after one exact removal."""

        _validated_usbfs_coordinates(path)
        if self._baseline is None or path not in self._baseline:
            raise UsbfsIdentityError("usbfs departure baseline is invalid")
        after = self._after_inventory(allow_membership_change=True)
        if path in after:
            raise UsbfsIdentityError("usbfs departed endpoint is still present")
        expected_paths = tuple(sorted(set(self._baseline) - {path}))
        if tuple(sorted(after)) != expected_paths:
            raise UsbfsIdentityError("usbfs exact departure evidence changed")
        return enumeration_evidence(after, after, ())

    def revalidate(self, evidence: dict[str, Any]) -> None:
        validate_enumeration_evidence(evidence)
        current = self._inventory_reader()
        expected = {
            value["path"]: UsbfsNodeSnapshot(**value["after"])
            for value in evidence["node_transitions"]
        }
        enumeration_evidence(
            expected,
            current,
            tuple(evidence["live_devices"]),
        )

    def revalidate_or_departure(self, evidence: dict[str, Any]) -> None:
        """Allow an unchanged inventory or exact removal of all live Odin nodes."""

        validate_enumeration_evidence(evidence)
        live_devices = tuple(evidence["live_devices"])
        if not live_devices:
            raise UsbfsIdentityError("usbfs departure evidence has no live endpoint")
        expected_full = {
            value["path"]: UsbfsNodeSnapshot(**value["after"])
            for value in evidence["node_transitions"]
        }
        expected_departed = {
            value["path"]: UsbfsNodeSnapshot(**value["after"])
            for value in evidence["node_transitions"]
            if value["path"] not in live_devices
        }
        current = self._inventory_reader()
        current_paths = tuple(sorted(current))
        if current_paths == tuple(sorted(expected_full)):
            enumeration_evidence(expected_full, current, live_devices)
        elif current_paths == tuple(sorted(expected_departed)):
            enumeration_evidence(expected_departed, current, ())
        else:
            raise UsbfsIdentityError(
                "usbfs inventory is neither unchanged nor an exact live departure"
            )
