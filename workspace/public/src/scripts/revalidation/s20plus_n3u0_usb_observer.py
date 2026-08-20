#!/usr/bin/env python3
"""Dormant, bounded host observer for the S20+ N3-U0 ACM witness."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import select
import stat
import termios
import time
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


SCHEMA = "s20plus_g986n_n3u0_usb_observer_v1"
BASELINE_SCHEMA = "s20plus_g986n_n3u0_usb_baseline_v1"
RECEIPT_SCHEMA = "s20plus_g986n_n3u0_usb_receipt_v1"
OBSERVER_ACTIVE = False

USB_VENDOR = "04e8"
USB_PRODUCT = "6861"
USB_MANUFACTURER = "Samsung"
USB_PRODUCT_STRING = "S20Plus-N3U0"
USB_DRIVER = "cdc_acm"
USB_INTERFACE = "00"
BANNER = b"S20PLUS_N3U0_ACM_V1\n"

ARRIVAL_TIMEOUT_SEC = 180
BANNER_TIMEOUT_SEC = 12
POLL_INTERVAL_SEC = 0.05
USB_ROOT = Path("/sys/bus/usb/devices")
TTY_ROOT = Path("/sys/class/tty")
DEV_ROOT = Path("/dev")

USB_NODE_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
TTY_RE = re.compile(r"ttyACM[0-9]+")
DIGEST_RE = re.compile(r"[0-9a-f]{64}")


class ObserverError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _read_attr(path: Path, label: str, maximum: int = 128) -> str:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise ObserverError(f"N3-U0 sysfs attribute is unavailable: {label}") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ObserverError(f"N3-U0 sysfs attribute is indirect: {label}")
        payload = os.read(descriptor, maximum + 1)
        if len(payload) > maximum or os.read(descriptor, 1):
            raise ObserverError(f"N3-U0 sysfs attribute is oversized: {label}")
    finally:
        os.close(descriptor)
    if payload.endswith(b"\n"):
        payload = payload[:-1]
    if not payload or any(byte < 0x20 or byte > 0x7E for byte in payload):
        raise ObserverError(f"N3-U0 sysfs attribute is malformed: {label}")
    try:
        return payload.decode("ascii", "strict")
    except UnicodeError as exc:
        raise ObserverError(f"N3-U0 sysfs attribute is not ASCII: {label}") from exc


def _optional_attr(path: Path, label: str) -> str | None:
    try:
        return _read_attr(path, label)
    except ObserverError as exc:
        if isinstance(exc.__cause__, FileNotFoundError):
            return None
        raise


@dataclass(frozen=True)
class Candidate:
    usb_node: str
    usb_path: Path
    tty_name: str
    tty_class: Path
    interface_path: Path
    major: int
    minor: int
    identity_sha256: str


@dataclass(frozen=True)
class Inventory:
    exact: tuple[Candidate, ...]
    pending_identity_sha256: tuple[str, ...]
    conflicting_identity_sha256: tuple[str, ...]


def _usb_device_nodes(usb_root: Path) -> list[tuple[str, Path]]:
    try:
        entries = sorted(usb_root.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        raise ObserverError("N3-U0 USB inventory is unavailable") from exc
    values: list[tuple[str, Path]] = []
    for entry in entries:
        if USB_NODE_RE.fullmatch(entry.name) is None:
            continue
        try:
            resolved = entry.resolve(strict=True)
        except OSError as exc:
            raise ObserverError("N3-U0 USB device link is invalid") from exc
        if not resolved.is_dir():
            raise ObserverError("N3-U0 USB device node is not a directory")
        values.append((entry.name, resolved))
    return values


def _tty_for_usb(
    usb_node: str,
    usb_path: Path,
    tty_root: Path,
) -> list[Candidate]:
    try:
        entries = sorted(tty_root.glob("ttyACM*"), key=lambda path: path.name)
    except OSError as exc:
        raise ObserverError("N3-U0 TTY inventory is unavailable") from exc
    values: list[Candidate] = []
    for entry in entries:
        if TTY_RE.fullmatch(entry.name) is None:
            continue
        try:
            device_path = (entry / "device").resolve(strict=True)
        except OSError:
            continue
        interface_path: Path | None = None
        for parent in (device_path, *device_path.parents):
            if ":" in parent.name and (parent / "bInterfaceNumber").exists():
                interface_path = parent
                break
            if parent == usb_path:
                break
        if interface_path is None:
            continue
        try:
            if interface_path.parent.resolve(strict=True) != usb_path:
                continue
            interface = _read_attr(
                interface_path / "bInterfaceNumber", "bInterfaceNumber"
            )
            driver = (interface_path / "driver").resolve(strict=True).name
            dev_value = _read_attr(entry / "dev", "tty dev")
        except (OSError, ObserverError):
            continue
        match = re.fullmatch(r"([0-9]+):([0-9]+)", dev_value)
        if match is None or interface != USB_INTERFACE or driver != USB_DRIVER:
            continue
        identity = {
            "usb_node": usb_node,
            "vendor": USB_VENDOR,
            "product": USB_PRODUCT,
            "manufacturer": USB_MANUFACTURER,
            "product_string": USB_PRODUCT_STRING,
            "serial_absent": True,
            "driver": driver,
            "interface": interface,
            "tty_name": entry.name,
            "dev": dev_value,
        }
        values.append(
            Candidate(
                usb_node=usb_node,
                usb_path=usb_path,
                tty_name=entry.name,
                tty_class=entry,
                interface_path=interface_path,
                major=int(match.group(1)),
                minor=int(match.group(2)),
                identity_sha256=_digest(identity),
            )
        )
    return values


def scan_inventory(
    *,
    usb_root: Path = USB_ROOT,
    tty_root: Path = TTY_ROOT,
) -> Inventory:
    exact: list[Candidate] = []
    pending: list[str] = []
    conflicts: list[str] = []
    for usb_node, usb_path in _usb_device_nodes(usb_root):
        try:
            vendor = _read_attr(usb_path / "idVendor", "idVendor")
            product = _read_attr(usb_path / "idProduct", "idProduct")
        except ObserverError:
            continue
        if vendor != USB_VENDOR or product != USB_PRODUCT:
            continue
        manufacturer = _optional_attr(usb_path / "manufacturer", "manufacturer")
        product_string = _optional_attr(usb_path / "product", "product")
        serial = _optional_attr(usb_path / "serial", "serial")
        candidate_named = product_string == USB_PRODUCT_STRING
        if not candidate_named:
            continue
        base_identity = {
            "usb_node": usb_node,
            "vendor": vendor,
            "product": product,
            "manufacturer": manufacturer,
            "product_string": product_string,
            "serial": serial,
        }
        if manufacturer != USB_MANUFACTURER or serial is not None:
            conflicts.append(_digest(base_identity))
            continue
        ttys = _tty_for_usb(usb_node, usb_path, tty_root)
        if not ttys:
            pending.append(_digest({**base_identity, "tty_count": 0}))
            continue
        if len(ttys) != 1:
            conflicts.append(_digest({**base_identity, "tty_count": len(ttys)}))
            continue
        exact.append(ttys[0])
    return Inventory(
        exact=tuple(exact),
        pending_identity_sha256=tuple(sorted(pending)),
        conflicting_identity_sha256=tuple(sorted(conflicts)),
    )


def capture_baseline(
    expected_usb_node: str,
    *,
    usb_root: Path = USB_ROOT,
    tty_root: Path = TTY_ROOT,
) -> dict[str, Any]:
    if USB_NODE_RE.fullmatch(expected_usb_node) is None:
        raise ObserverError("N3-U0 expected USB topology is invalid")
    inventory = scan_inventory(usb_root=usb_root, tty_root=tty_root)
    if (
        inventory.exact
        or inventory.pending_identity_sha256
        or inventory.conflicting_identity_sha256
    ):
        raise ObserverError("N3-U0 candidate identity is not absent at baseline")
    return {
        "schema": BASELINE_SCHEMA,
        "observer_schema": SCHEMA,
        "expected_topology_sha256": _hash_text(expected_usb_node),
        "candidate_absent": True,
        "exact_identity_sha256": [],
        "pending_identity_sha256": [],
        "conflicting_identity_sha256": [],
    }


def validate_baseline(value: Any, expected_usb_node: str) -> dict[str, Any]:
    expected = {
        "schema": BASELINE_SCHEMA,
        "observer_schema": SCHEMA,
        "expected_topology_sha256": _hash_text(expected_usb_node),
        "candidate_absent": True,
        "exact_identity_sha256": [],
        "pending_identity_sha256": [],
        "conflicting_identity_sha256": [],
    }
    if value != expected or any(type(value.get(name)) is not bool for name in ("candidate_absent",)):
        raise ObserverError("N3-U0 baseline is malformed")
    return value


def select_arrival(
    baseline: dict[str, Any],
    expected_usb_node: str,
    *,
    usb_root: Path = USB_ROOT,
    tty_root: Path = TTY_ROOT,
) -> Candidate:
    validate_baseline(baseline, expected_usb_node)
    inventory = scan_inventory(usb_root=usb_root, tty_root=tty_root)
    if inventory.conflicting_identity_sha256:
        raise ObserverError("N3-U0 candidate identity is conflicting")
    if inventory.pending_identity_sha256:
        if inventory.exact:
            raise ObserverError("N3-U0 candidate endpoint is ambiguous")
        raise ObserverError("N3-U0 candidate endpoint is pending")
    if len(inventory.exact) != 1:
        label = "absent" if not inventory.exact else "ambiguous"
        raise ObserverError(f"N3-U0 candidate endpoint is {label}")
    candidate = inventory.exact[0]
    if candidate.usb_node != expected_usb_node:
        raise ObserverError("N3-U0 candidate arrived on a foreign topology")
    return candidate


def _verify_descriptor(candidate: Candidate, descriptor: int) -> None:
    info = os.fstat(descriptor)
    if (
        not stat.S_ISCHR(info.st_mode)
        or os.major(info.st_rdev) != candidate.major
        or os.minor(info.st_rdev) != candidate.minor
    ):
        raise ObserverError("N3-U0 TTY descriptor identity changed")


def read_exact_banner(
    descriptor: int,
    *,
    timeout_sec: int = BANNER_TIMEOUT_SEC,
    monotonic: Callable[[], float] = time.monotonic,
) -> bytes:
    if type(timeout_sec) is not int or timeout_sec != BANNER_TIMEOUT_SEC:
        raise ObserverError("N3-U0 banner timeout is not the reviewed bound")
    try:
        fcntl.ioctl(descriptor, termios.TIOCEXCL)
        tty.setraw(descriptor, termios.TCSANOW)
    except (OSError, termios.error) as exc:
        raise ObserverError("N3-U0 TTY could not be exclusively opened") from exc
    deadline = monotonic() + timeout_sec
    payload = bytearray()
    while len(payload) < len(BANNER):
        remaining_time = deadline - monotonic()
        if remaining_time <= 0:
            raise ObserverError("N3-U0 banner timed out")
        readable, _, _ = select.select(
            [descriptor], [], [], min(0.1, remaining_time)
        )
        if not readable:
            continue
        try:
            chunk = os.read(descriptor, len(BANNER) - len(payload))
        except BlockingIOError:
            continue
        if not chunk:
            continue
        payload.extend(chunk)
        if not BANNER.startswith(payload):
            raise ObserverError("N3-U0 banner bytes differ")
    if bytes(payload) != BANNER:
        raise ObserverError("N3-U0 banner bytes differ")
    return bytes(payload)


def observe_selected(
    baseline: dict[str, Any],
    expected_usb_node: str,
    candidate: Candidate,
    descriptor: int,
    *,
    usb_root: Path,
    tty_root: Path,
) -> dict[str, Any]:
    validate_baseline(baseline, expected_usb_node)
    if candidate.usb_node != expected_usb_node:
        raise ObserverError("N3-U0 selected endpoint topology changed")
    _verify_descriptor(candidate, descriptor)
    payload = read_exact_banner(descriptor)
    _verify_descriptor(candidate, descriptor)
    repeated = select_arrival(
        baseline,
        expected_usb_node,
        usb_root=usb_root,
        tty_root=tty_root,
    )
    if repeated.identity_sha256 != candidate.identity_sha256:
        raise ObserverError("N3-U0 endpoint changed after banner")
    return {
        "schema": RECEIPT_SCHEMA,
        "observer_schema": SCHEMA,
        "baseline_sha256": _digest(baseline),
        "expected_topology_sha256": _hash_text(expected_usb_node),
        "endpoint_identity_sha256": candidate.identity_sha256,
        "banner_sha256": hashlib.sha256(payload).hexdigest(),
        "banner_size": len(payload),
        "tty_number_stable": False,
        "exact": True,
        "accepted": True,
    }


def _open_live(candidate: Candidate, dev_root: Path = DEV_ROOT) -> int:
    path = dev_root / candidate.tty_name
    try:
        before = path.lstat()
    except OSError as exc:
        raise ObserverError("N3-U0 TTY node is unavailable") from exc
    if (
        not stat.S_ISCHR(before.st_mode)
        or os.major(before.st_rdev) != candidate.major
        or os.minor(before.st_rdev) != candidate.minor
    ):
        raise ObserverError("N3-U0 TTY node identity differs")
    try:
        descriptor = os.open(
            path,
            os.O_RDWR
            | os.O_NOCTTY
            | os.O_NONBLOCK
            | os.O_CLOEXEC
            | os.O_NOFOLLOW,
        )
    except OSError as exc:
        raise ObserverError("N3-U0 TTY open failed") from exc
    try:
        _verify_descriptor(candidate, descriptor)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def require_active() -> None:
    if OBSERVER_ACTIVE is not True:
        raise ObserverError("N3-U0 USB observer is dormant")


def observe_attended(
    baseline: dict[str, Any],
    expected_usb_node: str,
) -> dict[str, Any]:
    """Observe once for a future reviewed owner; currently always dormant."""
    require_active()
    validate_baseline(baseline, expected_usb_node)
    deadline = time.monotonic() + ARRIVAL_TIMEOUT_SEC
    candidate: Candidate | None = None
    while time.monotonic() < deadline:
        try:
            candidate = select_arrival(baseline, expected_usb_node)
            break
        except ObserverError as exc:
            if str(exc) not in {
                "N3-U0 candidate endpoint is absent",
                "N3-U0 candidate endpoint is pending",
            }:
                raise
        time.sleep(POLL_INTERVAL_SEC)
    if candidate is None:
        raise ObserverError("N3-U0 candidate arrival timed out")
    descriptor = _open_live(candidate)
    try:
        return observe_selected(
            baseline,
            expected_usb_node,
            candidate,
            descriptor,
            usb_root=USB_ROOT,
            tty_root=TTY_ROOT,
        )
    finally:
        os.close(descriptor)


def render_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "active": OBSERVER_ACTIVE,
        "live_authority": False,
        "target": {
            "model": "SM-G986N",
            "device": "y2q",
            "product": "y2qksx",
            "build": "G986NKSS8IYC2",
        },
        "usb": {
            "vendor": USB_VENDOR,
            "product": USB_PRODUCT,
            "manufacturer": USB_MANUFACTURER,
            "product_string": USB_PRODUCT_STRING,
            "serial_absent": True,
            "driver": USB_DRIVER,
            "interface": USB_INTERFACE,
        },
        "banner_hex": BANNER.hex(),
        "arrival_timeout_sec": ARRIVAL_TIMEOUT_SEC,
        "banner_timeout_sec": BANNER_TIMEOUT_SEC,
        "tty_number_stable": False,
        "device_commands": [],
        "device_writes": [],
        "partition_transfers": [],
        "status": "REVIEW_PENDING_NOT_ACTIVE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if not args.render_plan:
        parser.error("only --render-plan is available while dormant")
    print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
