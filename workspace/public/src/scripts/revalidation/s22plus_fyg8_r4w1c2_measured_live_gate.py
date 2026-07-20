#!/usr/bin/env python3
"""Inert-until-bound R4W1-C2 measured-usbfs direct-PID1 live gate.

The offline mode is host-only.  Live and recovery modes require a complete,
separately committed policy clause.  The helper reopens the historical,
immutable R4W1-C connected PASS, uses timestamp-aware immutable usbfs endpoint
receipts, consumes the candidate exception before one boot-only transfer, and
performs mandatory Magisk-first rollback before retained-marker classification.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
import re
import select
import stat
import subprocess
import sys
import tarfile
import termios
import time
from pathlib import Path
from typing import Any, Callable

import s22plus_boot_only_live_core as core
import s22plus_fyg8_r3c0_live_gate as transport
import s22plus_fyg8_r4w1c_connected_gate as connected
import s22plus_odin_transition_core as odin_core
import s22plus_odin_usbfs_identity as usbfs_identity


SCHEMA = "s22plus_fyg8_r4w1c2_measured_live_gate_v1"
TARGET = connected.TARGET
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c2_measured_live_gate.py"
)
TEST_RELATIVE = Path("tests/test_s22plus_fyg8_r4w1c2_measured_live_gate.py")
POLICY_DRAFT = Path(
    "docs/operations/S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_EXCEPTION_DRAFT_2026-07-21.md"
)
EXPECTED_POLICY_TEMPLATE_SIZE = 13_701
EXPECTED_POLICY_TEMPLATE_SHA256 = (
    "710481ab970133232570baaf2aab9bcef73d82c217fb155a06feb3cbdd4d3d45"
)
POLICY_MARKER = (
    "S22+ FYG8 R4W1-C2 measured-usbfs watchdog-carrier direct-PID1 "
    "boot-only live gate"
)
POLICY_BEGIN = "BEGIN_S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_V1"
POLICY_END = "END_S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_V1"
ACTIVE_SENTINEL = "S22PLUS_FYG8_R4W1C2_MEASURED_LIVE_POLICY_STATE=ACTIVE"
LIVE_ACK_TOKEN = (
    "S22PLUS-FYG8-R4W1C2-MEASURED-USBFS-PHYSICAL-CONTINUITY-"
    "DIRECT-PID1-LIVE"
)
ROLLBACK_ACK_TOKEN = (
    "S22PLUS-FYG8-R4W1C2-MEASURED-USBFS-PHYSICAL-CONTINUITY-"
    "MAGISK-ROLLBACK-FROM-DOWNLOAD"
)
NORMAL_DOWNLOAD_CONFIRMATION = (
    "S22PLUS-FYG8-R4W1C2-MEASURED-USBFS-PHYSICAL-CONTINUITY-"
    "NORMAL-DOWNLOAD-CONFIRMED"
)
STOCK_CLEANUP_CONFIRMATION = (
    "S22PLUS-FYG8-R4W1C2-MEASURED-USBFS-PHYSICAL-CONTINUITY-"
    "STOCK-CLEANUP-CONFIRMED"
)
AMBIGUOUS_ROLLBACK_RETRY_ACK = (
    "S22PLUS-FYG8-R4W1C2-MEASURED-USBFS-PHYSICAL-CONTINUITY-"
    "AMBIGUOUS-MAGISK-ROLLBACK-RETRY"
)

CONNECTED_HELPER_SHA256 = (
    "fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9"
)
CONNECTED_TEST_SHA256 = (
    "98938da61fc6a3f95389a31f019950fa00b3e6575687aab8d1edf5d070240251"
)
CONNECTED_CLAUSE_SHA256 = (
    "35f1d2cf8b9a4b25bac108832fb3f9ec9fd37e05c1b03f9fa34eeb5367c17ffa"
)
LIVE_CORE_SHA256 = connected.EXPECTED_LIVE_CORE_SHA256
ODIN_CORE_SIZE = 58_423
ODIN_CORE_SHA256 = (
    "c9abb179158bb45039574465e743f1f5bee18f993cbddd2f0b40e9048d1ca6b3"
)
ODIN_CORE_TEST_SIZE = 64_485
ODIN_CORE_TEST_SHA256 = (
    "39a28a8e751897c9517205f6cfe05d1193bd3fc7ce5f6c446ec26f70aa9875fd"
)
USBFS_IDENTITY_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/s22plus_odin_usbfs_identity.py"
)
USBFS_IDENTITY_SIZE = 18_998
USBFS_IDENTITY_SHA256 = (
    "2d1310e129670e89862826bcacc3886820c60f2691f342720927e8e13bddfe10"
)
USBFS_IDENTITY_TEST_RELATIVE = Path("tests/test_s22plus_odin_usbfs_identity.py")
USBFS_IDENTITY_TEST_SIZE = 15_668
USBFS_IDENTITY_TEST_SHA256 = (
    "da7e059a3d9a274d6b0d82977da805a47b6cdd7149d07476d51586b457a3cd66"
)
STAT_BINARY = Path("/usr/lib/cargo/bin/coreutils/stat")
STAT_BINARY_SIZE = 11_352_352
STAT_BINARY_SHA256 = (
    "48893b0fb21436b54619db80486e83ef39dfccaf1aefe83dfa00c02d6146e8c0"
)

RUN_ROOT = Path("workspace/private/runs")
CONSUMED_STATE = Path(
    "workspace/private/state/s22plus_fyg8_r4w1c2_measured_live_exception_consumed.json"
)
PASS_VERDICT = "PASS_R4W1C2_MEASURED_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK"
NO_PROOF_VERDICT = "NO_PROOF_R4W1C2_MEASURED_EXEC_OR_RETENTION_UNRESOLVED"
MAX_OBSERVER_BYTES = connected.MAX_OBSERVER_BYTES
DEFAULT_PARK_WAIT_SEC = 120.0
MAX_TRANSFER_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_RECOVERY_ATTEMPTS = 2
USB_TOPOLOGY_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
DOWNLOAD_USB_PRODUCT = "685d"
DOWNLOAD_USB_PRODUCT_TEXT = "SAMSUNG USB"
DOWNLOAD_USB_MANUFACTURER = "Samsung"
DOWNLOAD_USB_SERIAL_STATE = "absent"
PHYSICAL_CONTINUITY_BASIS = (
    "operator-attested-same-attended-handset-cable-hub-host-port;"
    "preflight-through-final-rollback-and-android-return;"
    "not-host-intrinsically-verifiable"
)
USBFS_CHARACTER_MAJOR = 189
USBFS_DEVICES_PER_BUS = 128
DOWNLOAD_STABLE_SAMPLE_COUNT = 3
DOWNLOAD_STABLE_POLL_SEC = 0.25
USB_SYSFS_ROOT = Path("/sys/bus/usb/devices")
STOCK_CLEANUP_INTENT_NAME = "rollback-stock-cleanup-intent.json"
UTC_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z"
)


class GateError(RuntimeError):
    pass


class OdinCommandFailed(GateError):
    """A sealed Odin process returned a definite nonzero status."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _direct_regular_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise GateError(f"{label} is missing or indirect: {path}")
    resolved = path.resolve()
    if resolved != path.absolute():
        raise GateError(f"{label} did not resolve directly: {path}")
    return resolved


def adb_usb_topology(serial: str) -> str:
    result = transport.run(["adb", "-s", serial, "get-devpath"], timeout=10)
    if result.returncode != 0:
        raise GateError("ADB USB topology query failed")
    value = result.stdout.strip()
    match = re.fullmatch(r"usb:(?P<topology>[0-9]+-[0-9]+(?:\.[0-9]+)*)", value)
    if match is None:
        raise GateError(f"ADB USB topology is not canonical: {value!r}")
    return match.group("topology")


def adb_usb_binding(serial: str) -> dict[str, str]:
    topology = adb_usb_topology(serial)
    result = transport.run(["adb", "-s", serial, "get-serialno"], timeout=10)
    if result.returncode != 0:
        raise GateError("ADB USB serial query failed")
    usb_serial = result.stdout.strip()
    if (
        re.fullmatch(r"[A-Za-z0-9._:-]{4,128}", usb_serial) is None
        or usb_serial != serial
    ):
        raise GateError("ADB USB serial does not bind the selected Android target")
    try:
        sysfs_serial = (
            Path("/sys/bus/usb/devices") / topology / "serial"
        ).read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise GateError("Android USB sysfs serial is unavailable") from exc
    if sysfs_serial != usb_serial:
        raise GateError("ADB and Android USB sysfs serials differ")
    return {
        "topology": topology,
        "serial_sha256": android_serial_sha256(usb_serial),
        "download_serial_state": DOWNLOAD_USB_SERIAL_STATE,
    }


def android_serial_sha256(serial: str) -> str:
    try:
        encoded = serial.encode("ascii")
    except UnicodeEncodeError as exc:
        raise GateError("Android serial is not ASCII") from exc
    if re.fullmatch(r"[A-Za-z0-9._:-]{4,128}", serial) is None:
        raise GateError("Android serial is not canonical")
    return core.sha256_bytes(encoded)


def endpoint_node_snapshot(device: str) -> tuple[os.stat_result, str]:
    if odin_core.ODIN_DEVICE_RE.fullmatch(device) is None:
        raise GateError("Odin endpoint path is malformed")
    metadata = os.stat(device, follow_symlinks=False)
    if not stat.S_ISCHR(metadata.st_mode):
        raise GateError("Odin endpoint is not a character device")
    identity = ":".join(
        str(value)
        for value in (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_rdev,
            metadata.st_ctime_ns,
        )
    )
    return metadata, identity


def require_usbfs_node_binding(
    device: str, metadata: os.stat_result, identity: dict[str, str]
) -> None:
    try:
        busnum = int(identity["busnum"])
        devnum = int(identity["devnum"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GateError("Download USB bus/device numbers are malformed") from exc
    expected_device = f"/dev/bus/usb/{busnum:03d}/{devnum:03d}"
    expected_minor = (busnum - 1) * USBFS_DEVICES_PER_BUS + (devnum - 1)
    if (
        device != expected_device
        or os.major(metadata.st_rdev) != USBFS_CHARACTER_MAJOR
        or os.minor(metadata.st_rdev) != expected_minor
    ):
        raise GateError("Odin endpoint is not the exact sysfs-bound usbfs node")


def require_download_serial_absent(usb_device: Path) -> str:
    serial_path = usb_device / "serial"
    try:
        os.stat(serial_path, follow_symlinks=False)
    except FileNotFoundError:
        return DOWNLOAD_USB_SERIAL_STATE
    except OSError as exc:
        raise GateError("Download USB serial state is unreadable") from exc
    raise GateError("Download USB serial is unexpectedly present")


def read_download_sysfs_identity(usb_device: Path) -> dict[str, str] | None:
    try:
        serial_state_before = require_download_serial_absent(usb_device)
        values = {
            "vendor": (usb_device / "idVendor").read_text(encoding="ascii").strip(),
            "product": (usb_device / "idProduct").read_text(encoding="ascii").strip(),
            "product_text": (usb_device / "product").read_text(encoding="ascii").strip(),
            "manufacturer": (usb_device / "manufacturer")
            .read_text(encoding="ascii")
            .strip(),
            "busnum": (usb_device / "busnum").read_text(encoding="ascii").strip(),
            "devnum": (usb_device / "devnum").read_text(encoding="ascii").strip(),
            "devpath": (usb_device / "devpath").read_text(encoding="ascii").strip(),
        }
        serial_state_after = require_download_serial_absent(usb_device)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as exc:
        raise GateError("Download USB sysfs identity is unreadable") from exc
    if serial_state_before != serial_state_after:
        raise GateError("Download USB serial state changed while reading identity")
    values["serial_state"] = serial_state_after
    return values


def validate_download_sysfs_identity(
    values: dict[str, str], expected_topology: str
) -> None:
    if USB_TOPOLOGY_RE.fullmatch(expected_topology) is None:
        raise GateError("Download USB topology is malformed")
    expected_busnum, expected_devpath = expected_topology.split("-", 1)
    if (
        values.get("vendor") != "04e8"
        or values.get("product") != DOWNLOAD_USB_PRODUCT
        or values.get("product_text") != DOWNLOAD_USB_PRODUCT_TEXT
        or values.get("manufacturer") != DOWNLOAD_USB_MANUFACTURER
        or values.get("serial_state") != DOWNLOAD_USB_SERIAL_STATE
        or re.fullmatch(r"[1-9][0-9]*", values.get("busnum", "")) is None
        or re.fullmatch(r"[1-9][0-9]*", values.get("devnum", "")) is None
        or re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", values.get("devpath", "")) is None
        or values.get("busnum") != expected_busnum
        or values.get("devpath") != expected_devpath
        or not 1 <= int(values["busnum"]) <= 999
        or not 1 <= int(values["devnum"]) <= 999
    ):
        raise GateError("Download USB identity is not exact Samsung/canonical")


def endpoint_usb_identity(device: str) -> dict[str, str]:
    metadata, _legacy_identity_before = endpoint_node_snapshot(device)
    try:
        measured_before = usbfs_identity.snapshot_node(device)
        device_identity_before = usbfs_identity.immutable_identity(measured_before)
    except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
        raise GateError("Odin endpoint measured identity is unavailable") from exc
    sysfs_link = Path("/sys/dev/char") / (
        f"{os.major(metadata.st_rdev)}:{os.minor(metadata.st_rdev)}"
    )
    try:
        sysfs_device = sysfs_link.resolve(strict=True)
    except OSError as exc:
        raise GateError("Odin endpoint lacks a resolvable sysfs device") from exc
    usb_device: Path | None = None
    for candidate in (sysfs_device, *sysfs_device.parents):
        if USB_TOPOLOGY_RE.fullmatch(candidate.name):
            usb_device = candidate
            break
    if usb_device is None:
        raise GateError("Odin endpoint lacks a canonical USB topology")
    identity_before = read_download_sysfs_identity(usb_device)
    if identity_before is None:
        raise GateError("Odin endpoint USB identity disappeared while reading")
    validate_download_sysfs_identity(identity_before, usb_device.name)
    require_usbfs_node_binding(device, metadata, identity_before)
    identity_after = read_download_sysfs_identity(usb_device)
    if identity_after is None or identity_after != identity_before:
        raise GateError("Odin endpoint USB identity changed while reading")
    metadata_after, _legacy_identity_after = endpoint_node_snapshot(device)
    require_usbfs_node_binding(device, metadata_after, identity_after)
    try:
        measured_after = usbfs_identity.snapshot_node(device)
        device_identity_after = usbfs_identity.immutable_identity(measured_after)
    except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
        raise GateError("Odin endpoint measured identity is unavailable") from exc
    if device_identity_after != device_identity_before:
        raise GateError("Odin endpoint immutable identity changed while reading USB")
    return {
        "topology": usb_device.name,
        **identity_after,
        "sysfs_device": str(usb_device),
        "device_identity": device_identity_after,
    }


def require_ticket_usb_binding(
    ticket: odin_core.EndpointTicket, expected: dict[str, str]
) -> dict[str, str]:
    expected_topology = str(expected.get("topology", ""))
    expected_serial = str(expected.get("serial_sha256", ""))
    expected_download_serial = str(expected.get("download_serial_state", ""))
    if USB_TOPOLOGY_RE.fullmatch(expected_topology) is None:
        raise GateError("expected USB topology is malformed")
    if re.fullmatch(r"[0-9a-f]{64}", expected_serial) is None:
        raise GateError("expected USB serial binding is malformed")
    if expected_download_serial != DOWNLOAD_USB_SERIAL_STATE:
        raise GateError("expected Download USB serial state is malformed")
    identity = endpoint_usb_identity(ticket.device)
    if (
        identity["topology"] != expected_topology
        or identity["serial_state"] != expected_download_serial
        or identity["product"] != DOWNLOAD_USB_PRODUCT
        or identity["device_identity"] != ticket.device_identity
    ):
        raise GateError(
            "Odin endpoint does not match the bound Samsung Download identity"
        )
    return identity


def bound_download_node_sample(
    expected: dict[str, str],
    *,
    sysfs_root: Path = USB_SYSFS_ROOT,
) -> dict[str, Any] | None:
    expected_topology = str(expected.get("topology", ""))
    expected_serial = str(expected.get("serial_sha256", ""))
    expected_download_serial = str(expected.get("download_serial_state", ""))
    if USB_TOPOLOGY_RE.fullmatch(expected_topology) is None:
        raise GateError("expected USB topology is malformed")
    if re.fullmatch(r"[0-9a-f]{64}", expected_serial) is None:
        raise GateError("expected USB serial binding is malformed")
    if expected_download_serial != DOWNLOAD_USB_SERIAL_STATE:
        raise GateError("expected Download USB serial state is malformed")

    usb_device = sysfs_root / expected_topology
    first_identity = read_download_sysfs_identity(usb_device)
    if first_identity is None:
        return None
    if first_identity["vendor"] != "04e8":
        raise GateError("bound USB topology is no longer Samsung")
    if first_identity["product"] != DOWNLOAD_USB_PRODUCT:
        return None
    validate_download_sysfs_identity(first_identity, expected_topology)

    device = (
        f"/dev/bus/usb/{int(first_identity['busnum']):03d}/"
        f"{int(first_identity['devnum']):03d}"
    )
    if odin_core.ODIN_DEVICE_RE.fullmatch(device) is None:
        raise GateError("bound Download endpoint path is malformed")
    try:
        metadata, device_identity_before = endpoint_node_snapshot(device)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise GateError("bound Download endpoint is unreadable") from exc
    require_usbfs_node_binding(device, metadata, first_identity)
    try:
        measured_before = usbfs_identity.snapshot_node(device)
        immutable_before = usbfs_identity.immutable_identity(measured_before)
    except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
        raise GateError("bound Download measured identity is unavailable") from exc
    second_identity = read_download_sysfs_identity(usb_device)
    if second_identity is None or second_identity != first_identity:
        raise GateError("bound Download USB identity changed while sampling")
    metadata_after, device_identity_after = endpoint_node_snapshot(device)
    require_usbfs_node_binding(device, metadata_after, second_identity)
    if device_identity_after != device_identity_before:
        raise GateError("bound Download endpoint changed while sampling")
    try:
        measured_after = usbfs_identity.snapshot_node(device)
        immutable_after = usbfs_identity.immutable_identity(measured_after)
    except (OSError, usbfs_identity.UsbfsIdentityError) as exc:
        raise GateError("bound Download measured identity is unavailable") from exc
    if immutable_after != immutable_before:
        raise GateError("bound Download immutable identity changed while sampling")
    return {
        "device": device,
        "topology": expected_topology,
        "serial_state": first_identity["serial_state"],
        "product": first_identity["product"],
        "product_text": first_identity["product_text"],
        "manufacturer": first_identity["manufacturer"],
        "node": {
            "st_dev": metadata.st_dev,
            "st_ino": metadata.st_ino,
            "st_rdev": metadata.st_rdev,
            "st_ctime_ns": metadata.st_ctime_ns,
            "immutable_identity": immutable_after,
        },
    }


def wait_for_stable_download_node(
    expected: dict[str, str],
    timeout_sec: float,
    *,
    sampler: Callable[[dict[str, str]], dict[str, Any] | None] = bound_download_node_sample,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise GateError("Download endpoint stabilization timeout is invalid")
    started = monotonic()
    deadline = started + timeout_sec
    stable_count = 0
    observed: dict[str, Any] | None = None
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GateError("bound Download endpoint did not stabilize in time")
        sample = sampler(expected)
        if sample is None:
            if observed is not None:
                raise GateError("bound Download endpoint disappeared while stabilizing")
            stable_count = 0
        else:
            node = sample.get("node")
            if (
                set(sample)
                != {
                    "device",
                    "topology",
                    "serial_state",
                    "product",
                    "product_text",
                    "manufacturer",
                    "node",
                }
                or not isinstance(node, dict)
                or set(node) != {"st_dev", "st_ino", "st_rdev", "st_ctime_ns"}
                or any(not isinstance(node[name], int) for name in node)
            ):
                raise GateError("bound Download endpoint sample is malformed")
            if (
                sample["topology"] != expected.get("topology")
                or sample["serial_state"] != expected.get("download_serial_state")
                or sample["product"] != DOWNLOAD_USB_PRODUCT
                or sample["product_text"] != DOWNLOAD_USB_PRODUCT_TEXT
                or sample["manufacturer"] != DOWNLOAD_USB_MANUFACTURER
                or odin_core.ODIN_DEVICE_RE.fullmatch(str(sample["device"])) is None
            ):
                raise GateError("bound Download endpoint sample does not match binding")
            if observed is None:
                observed = sample
                stable_count = 1
            else:
                prior_node = observed["node"]
                immutable = ("st_dev", "st_ino", "st_rdev")
                if sample["device"] != observed["device"] or any(
                    node[name] != prior_node[name] for name in immutable
                ):
                    raise GateError("bound Download endpoint was replaced while stabilizing")
                if sample != observed:
                    observed = sample
                    stable_count = 1
                else:
                    stable_count += 1
            if stable_count >= DOWNLOAD_STABLE_SAMPLE_COUNT:
                return {
                    **sample,
                    "stable_samples": stable_count,
                    "elapsed_sec": round(monotonic() - started, 6),
                }
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GateError("bound Download endpoint did not stabilize in time")
        sleep(min(DOWNLOAD_STABLE_POLL_SEC, remaining))


@contextlib.contextmanager
def sealed_memfd(
    path: Path,
    *,
    label: str,
    expected_size: int,
    expected_sha256: str,
    executable: bool = False,
    boot_only_ap: bool = False,
):
    source_path = _direct_regular_file(path, label)
    source_fd = os.open(
        source_path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    sealed_fd = -1
    try:
        sealed_fd = os.memfd_create(
            re.sub(r"[^A-Za-z0-9_.-]", "-", label)[:64],
            os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
        )
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(source_fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > expected_size:
                raise GateError(f"{label} exceeds its pinned size")
            digest.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(sealed_fd, view)
                if written <= 0:
                    raise GateError(f"{label} memfd copy stalled")
                view = view[written:]
        if total != expected_size or digest.hexdigest() != expected_sha256:
            raise GateError(f"{label} identity changed before transfer")
        os.fchmod(sealed_fd, 0o500 if executable else 0o400)
        fcntl.fcntl(
            sealed_fd,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_SEAL
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_WRITE,
        )
        if boot_only_ap:
            os.lseek(sealed_fd, 0, os.SEEK_SET)
            with os.fdopen(os.dup(sealed_fd), "rb") as stream, tarfile.open(
                fileobj=stream, mode="r:*"
            ) as archive:
                members = archive.getmembers()
            if (
                len(members) != 1
                or members[0].name != "boot.img.lz4"
                or not members[0].isfile()
            ):
                raise GateError(f"{label} sealed image is not exactly boot-only")
        os.lseek(sealed_fd, 0, os.SEEK_SET)
        yield sealed_fd
    finally:
        os.close(source_fd)
        if sealed_fd >= 0:
            os.close(sealed_fd)


@contextlib.contextmanager
def pinned_odin_session(path: Path):
    with sealed_memfd(
        path,
        label="Odin4-session",
        expected_size=connected.EXPECTED_ODIN_SIZE,
        expected_sha256=connected.EXPECTED_ODIN_SHA256,
        executable=True,
    ) as descriptor:
        external_path = Path(f"/proc/{os.getpid()}/fd/{descriptor}")
        if not external_path.exists():
            raise GateError("sealed Odin session path is unavailable")
        yield descriptor, external_path


def flash_sealed_exact(
    odin_fd: int,
    ap_path: Path,
    *,
    ap_size: int,
    ap_sha256: str,
    label: str,
    log_path: Path,
    revalidate: Callable[[], tuple[str, dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if odin_fd < 0:
        raise GateError("sealed Odin descriptor is invalid")
    with sealed_memfd(
        ap_path,
        label=label,
        expected_size=ap_size,
        expected_sha256=ap_sha256,
        boot_only_ap=True,
    ) as ap_fd:
        device, revalidation = revalidate()
        command = [
            f"/proc/self/fd/{odin_fd}",
            "--reboot",
            "-a",
            f"/proc/self/fd/{ap_fd}",
            "-d",
            device,
        ]
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            pass_fds=(odin_fd, ap_fd),
            timeout=240,
            check=False,
        )
    stdout = completed.stdout or b""
    stderr = completed.stderr or b""
    if len(stdout) + len(stderr) > MAX_TRANSFER_OUTPUT_BYTES:
        raise GateError(f"{label} Odin output exceeded its bound")
    transfer = {
        "label": label,
        "returncode": completed.returncode,
        "stdout_bytes": len(stdout),
        "stderr_bytes": len(stderr),
        "stdout_sha256": core.sha256_bytes(stdout),
        "stderr_sha256": core.sha256_bytes(stderr),
        "odin_sha256": connected.EXPECTED_ODIN_SHA256,
        "ap_sha256": ap_sha256,
        "sealed_inputs": True,
    }
    core.durable_create_json(log_path, transfer)
    if completed.returncode != 0:
        raise OdinCommandFailed(
            f"{label} Odin flash failed rc={completed.returncode}"
        )
    return transfer, revalidation


def helper_sha256(root: Path) -> str:
    return core.sha256_file(root / SCRIPT_RELATIVE)


def test_sha256(root: Path) -> str:
    return core.sha256_file(root / TEST_RELATIVE)


def policy_required_values(root: Path) -> tuple[str, ...]:
    return (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        helper_sha256(root),
        test_sha256(root),
        str(connected.SCRIPT_RELATIVE),
        CONNECTED_HELPER_SHA256,
        CONNECTED_TEST_SHA256,
        CONNECTED_CLAUSE_SHA256,
        LIVE_CORE_SHA256,
        ODIN_CORE_SHA256,
        USBFS_IDENTITY_SHA256,
        USBFS_IDENTITY_TEST_SHA256,
        str(STAT_BINARY),
        STAT_BINARY_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        NORMAL_DOWNLOAD_CONFIRMATION,
        STOCK_CLEANUP_CONFIRMATION,
        AMBIGUOUS_ROLLBACK_RETRY_ACK,
        str(POLICY_DRAFT),
        EXPECTED_POLICY_TEMPLATE_SHA256,
        str(connected.PASS_STATE),
        connected.EXPECTED_CANDIDATE_BOOT_SHA256,
        connected.EXPECTED_CANDIDATE_AP_SHA256,
        connected.EXPECTED_STATIC_RESULT_SHA256,
        connected.EXPECTED_MAGISK_AP_SHA256,
        connected.EXPECTED_STOCK_AP_SHA256,
        connected.EXPECTED_FULL_FIRMWARE_SHA256,
        connected.EXPECTED_VENDOR_BOOT_SHA256,
        str(CONSUMED_STATE),
    )


def extract_policy_clause(text: str) -> str:
    pattern = re.compile(
        rf"(?ms)^{re.escape(POLICY_BEGIN)}$\n.*?^{re.escape(POLICY_END)}$"
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise GateError("R4W1-C2 live policy clause count is not one")
    clause = matches[0].group(0)
    active = re.compile(rf"(?m)^`{re.escape(ACTIVE_SENTINEL)}`\.?$")
    if len(active.findall(clause)) != 1:
        raise GateError("R4W1-C2 live ACTIVE sentinel count is not one")
    if "DRAFT_INACTIVE" in clause or "POLICY_STATE=RETIRED" in clause:
        raise GateError("R4W1-C2 live policy clause is inactive or retired")
    return clause


def policy_template(root: Path) -> tuple[str, dict[str, Any]]:
    path = connected.require_direct_path(
        root, root / POLICY_DRAFT, "R4W1-C2 live policy template"
    )
    payload = core.read_stable_file(path, maximum=128 * 1024)
    identity = {"size": len(payload), "sha256": core.sha256_bytes(payload)}
    if identity != {
        "size": EXPECTED_POLICY_TEMPLATE_SIZE,
        "sha256": EXPECTED_POLICY_TEMPLATE_SHA256,
    }:
        raise GateError("R4W1-C2 live policy template identity mismatch")
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise GateError("R4W1-C2 live policy template is not UTF-8") from exc
    placeholders = (
        "LIVE_HELPER_SHA256",
        "LIVE_TEST_SHA256",
        "POLICY_TEMPLATE_SHA256",
        "CONNECTED_PASS_CREATED_AT_UTC",
        "CONNECTED_PASS_RECORD_SIZE",
        "CONNECTED_PASS_RECORD_SHA256",
        "CONNECTED_RESULT_PATH",
        "CONNECTED_RESULT_SIZE",
        "CONNECTED_RESULT_SHA256",
    )
    if "DRAFT_INACTIVE" not in text or any(
        text.count("{{" + name + "}}") != 1 for name in placeholders
    ):
        raise GateError("R4W1-C2 live policy template placeholder contract mismatch")
    extract_policy_clause(text)
    if core.read_stable_file(path, maximum=128 * 1024) != payload:
        raise GateError("R4W1-C2 live policy template changed while reopening")
    return text, {"path": str(POLICY_DRAFT), **identity}


def render_policy_clause(
    root: Path, binding: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    text, identity = policy_template(root)
    replacements = {
        "LIVE_HELPER_SHA256": helper_sha256(root),
        "LIVE_TEST_SHA256": test_sha256(root),
        "POLICY_TEMPLATE_SHA256": EXPECTED_POLICY_TEMPLATE_SHA256,
        "CONNECTED_PASS_CREATED_AT_UTC": str(binding["created_at_utc"]),
        "CONNECTED_PASS_RECORD_SIZE": str(binding["pass_size"]),
        "CONNECTED_PASS_RECORD_SHA256": str(binding["pass_sha256"]),
        "CONNECTED_RESULT_PATH": str(binding["result_path"]),
        "CONNECTED_RESULT_SIZE": str(binding["result_size"]),
        "CONNECTED_RESULT_SHA256": str(binding["result_sha256"]),
    }
    for name, value in replacements.items():
        text = text.replace("{{" + name + "}}", value)
    if "{{" in text or "}}" in text:
        raise GateError("R4W1-C2 live policy rendering left a placeholder")
    return extract_policy_clause(text), identity


def policy_clause(root: Path) -> str:
    try:
        text = core.read_stable_file(root / "AGENTS.md", maximum=2 * 1024 * 1024).decode(
            "utf-8"
        )
    except (OSError, UnicodeError) as exc:
        raise GateError("AGENTS.md is unavailable") from exc
    clause = extract_policy_clause(text)
    binding = parse_connected_binding(clause)
    expected, _ = render_policy_clause(root, binding)
    if clause != expected:
        raise GateError("R4W1-C2 live policy is not the exact reviewed rendering")
    return clause


def policy_active(root: Path) -> bool:
    try:
        policy_clause(root)
    except GateError:
        return False
    return True


def verify_policy_draft(root: Path) -> dict[str, Any]:
    _text, identity = policy_template(root)
    return {
        **identity,
        "helper_sha256": helper_sha256(root),
        "test_sha256": test_sha256(root),
        "active": policy_active(root),
    }


def parse_connected_binding(clause: str) -> dict[str, Any]:
    pattern = re.compile(
        r"The load-bearing connected PASS record is\s+"
        r"`(?P<pass_path>[^`]+)`,\s+created at `(?P<created_at>[^`]+)`, size\s+"
        r"`(?P<pass_size>[1-9][0-9]*)`, SHA256\s+"
        r"`(?P<pass_sha>[0-9a-f]{64})`\. It binds connected result\s+"
        r"`(?P<result_path>[^`]+)`, size `(?P<result_size>[1-9][0-9]*)`, SHA256\s+"
        r"`(?P<result_sha>[0-9a-f]{64})`\."
    )
    matches = list(pattern.finditer(clause))
    if len(matches) != 1:
        raise GateError("R4W1-C2 live clause lacks one exact connected binding")
    raw = matches[0].groupdict()
    if any(
        re.fullmatch(r"[A-Za-z0-9._/-]+", raw[key]) is None
        for key in ("pass_path", "result_path")
    ):
        raise GateError("R4W1-C2 connected path binding contains unsafe bytes")
    if raw["pass_path"] != str(connected.PASS_STATE):
        raise GateError("R4W1-C2 connected PASS path binding mismatch")
    if re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z",
        raw["created_at"],
    ) is None:
        raise GateError("R4W1-C2 connected timestamp binding is malformed")
    result = Path(raw["result_path"])
    if (
        result.is_absolute()
        or ".." in result.parts
        or tuple(result.parts[:3]) != ("workspace", "private", "runs")
        or result.name != "result.json"
        or str(result) != raw["result_path"]
    ):
        raise GateError("R4W1-C2 connected result path binding is not canonical")
    return {
        "pass_path": raw["pass_path"],
        "created_at_utc": raw["created_at"],
        "pass_size": int(raw["pass_size"]),
        "pass_sha256": raw["pass_sha"],
        "result_path": raw["result_path"],
        "result_size": int(raw["result_size"]),
        "result_sha256": raw["result_sha"],
    }


def verify_artifacts(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    odin = resolve(root, args.odin)
    identities = {
        "candidate_boot": connected.require_identity(
            resolve(root, args.candidate_boot),
            connected.EXPECTED_CANDIDATE_BOOT_SIZE,
            connected.EXPECTED_CANDIDATE_BOOT_SHA256,
            "candidate boot",
        ),
        "candidate_lz4": connected.require_identity(
            resolve(root, args.candidate_lz4),
            connected.EXPECTED_CANDIDATE_LZ4_SIZE,
            connected.EXPECTED_CANDIDATE_LZ4_SHA256,
            "candidate LZ4",
        ),
        "candidate_ap": connected.require_identity(
            resolve(root, args.candidate_ap),
            connected.EXPECTED_CANDIDATE_AP_SIZE,
            connected.EXPECTED_CANDIDATE_AP_SHA256,
            "candidate AP",
        ),
        "manifest": connected.require_identity(
            resolve(root, args.manifest),
            connected.EXPECTED_MANIFEST_SIZE,
            connected.EXPECTED_MANIFEST_SHA256,
            "candidate manifest",
        ),
        "static_result": connected.require_identity(
            resolve(root, args.static_result),
            connected.EXPECTED_STATIC_RESULT_SIZE,
            connected.EXPECTED_STATIC_RESULT_SHA256,
            "static result",
        ),
        "magisk_rollback_ap": connected.require_identity(
            resolve(root, args.magisk_ap),
            connected.EXPECTED_MAGISK_AP_SIZE,
            connected.EXPECTED_MAGISK_AP_SHA256,
            "Magisk rollback AP",
        ),
        "stock_cleanup_ap": connected.require_identity(
            resolve(root, args.stock_ap),
            connected.EXPECTED_STOCK_AP_SIZE,
            connected.EXPECTED_STOCK_AP_SHA256,
            "stock cleanup AP",
        ),
        "full_firmware": connected.require_identity(
            resolve(root, args.full_firmware),
            connected.EXPECTED_FULL_FIRMWARE_SIZE,
            connected.EXPECTED_FULL_FIRMWARE_SHA256,
            "full FYG8 firmware",
        ),
        "odin": connected.require_identity(
            odin,
            connected.EXPECTED_ODIN_SIZE,
            connected.EXPECTED_ODIN_SHA256,
            "Odin4",
        ),
    }
    for label, path in (
        ("candidate AP", resolve(root, args.candidate_ap)),
        ("Magisk rollback AP", resolve(root, args.magisk_ap)),
        ("stock cleanup AP", resolve(root, args.stock_ap)),
    ):
        if connected.tar_members(path) != ["boot.img.lz4"]:
            raise GateError(f"{label} is not exactly boot-only")

    try:
        resolved_stat = usbfs_identity.STAT_BINARY.resolve(strict=True)
    except OSError as exc:
        raise GateError("usbfs birth-time stat executable is unavailable") from exc
    if resolved_stat != STAT_BINARY:
        raise GateError("usbfs birth-time stat executable resolved path mismatch")

    expected_sources = {
        "static_checker": (
            connected.STATIC_CHECKER_RELATIVE,
            connected.EXPECTED_STATIC_CHECKER_SIZE,
            connected.EXPECTED_STATIC_CHECKER_SHA256,
        ),
        "static_checker_test": (
            connected.STATIC_CHECKER_TEST_RELATIVE,
            connected.EXPECTED_STATIC_CHECKER_TEST_SIZE,
            connected.EXPECTED_STATIC_CHECKER_TEST_SHA256,
        ),
        "builder": (
            connected.BUILDER_RELATIVE,
            connected.EXPECTED_BUILDER_SIZE,
            connected.EXPECTED_BUILDER_SHA256,
        ),
        "builder_test": (
            connected.BUILDER_TEST_RELATIVE,
            connected.EXPECTED_BUILDER_TEST_SIZE,
            connected.EXPECTED_BUILDER_TEST_SHA256,
        ),
        "live_core": (
            connected.LIVE_CORE_RELATIVE,
            connected.EXPECTED_LIVE_CORE_SIZE,
            LIVE_CORE_SHA256,
        ),
        "live_core_test": (
            connected.LIVE_CORE_TEST_RELATIVE,
            connected.EXPECTED_LIVE_CORE_TEST_SIZE,
            connected.EXPECTED_LIVE_CORE_TEST_SHA256,
        ),
        "odin_core": (connected.ODIN_CORE_RELATIVE, ODIN_CORE_SIZE, ODIN_CORE_SHA256),
        "odin_core_test": (
            connected.ODIN_CORE_TEST_RELATIVE,
            ODIN_CORE_TEST_SIZE,
            ODIN_CORE_TEST_SHA256,
        ),
        "usbfs_identity": (
            USBFS_IDENTITY_RELATIVE,
            USBFS_IDENTITY_SIZE,
            USBFS_IDENTITY_SHA256,
        ),
        "usbfs_identity_test": (
            USBFS_IDENTITY_TEST_RELATIVE,
            USBFS_IDENTITY_TEST_SIZE,
            USBFS_IDENTITY_TEST_SHA256,
        ),
        "transport": (
            connected.TRANSPORT_RELATIVE,
            connected.EXPECTED_TRANSPORT_SIZE,
            connected.EXPECTED_TRANSPORT_SHA256,
        ),
    }
    source_pins = {
        label: connected.require_identity(root / path, size, digest, label)
        for label, (path, size, digest) in expected_sources.items()
    }
    source_pins["stat_binary"] = connected.require_identity(
        STAT_BINARY,
        STAT_BINARY_SIZE,
        STAT_BINARY_SHA256,
        "usbfs birth-time stat executable",
    )
    return {
        "target": TARGET,
        "identities": identities,
        "source_pins": source_pins,
        "fresh_static_checker": connected.run_fresh_static_checker(root),
        "ap_members": ["boot.img.lz4"],
        "endpoint_identity_mode": "measured-usbfs-immutable-v1",
    }


def reopen_connected_evidence(
    root: Path, artifacts: dict[str, Any], clause: str
) -> dict[str, Any]:
    binding = parse_connected_binding(clause)
    pass_path = connected.require_direct_path(
        root, root / connected.PASS_STATE, "R4W1-C2 connected PASS"
    )
    pass_before = core.read_stable_file(pass_path, maximum=1024 * 1024)
    pass_identity = {
        "size": len(pass_before),
        "sha256": core.sha256_bytes(pass_before),
    }
    record = connected.validate_connected_pass(root)
    result_path = connected.require_direct_path(
        root, root / Path(str(record["result_path"])), "R4W1-C2 connected result"
    )
    result_before = core.read_stable_file(result_path, maximum=8 * 1024 * 1024)
    result_identity = {
        "size": len(result_before),
        "sha256": core.sha256_bytes(result_before),
    }
    try:
        connected_result = json.loads(result_before)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("R4W1-C connected result is invalid") from exc
    historical_artifacts = connected_result.get("artifacts", {})
    if (
        historical_artifacts.get("identities") != artifacts.get("identities")
        or historical_artifacts.get("fresh_static_checker")
        != artifacts.get("fresh_static_checker")
        or historical_artifacts.get("ap_members") != artifacts.get("ap_members")
    ):
        raise GateError("R4W1-C2 current artifacts differ from connected evidence")
    expected = {
        "pass_path": str(connected.PASS_STATE),
        "created_at_utc": record["created_at_utc"],
        "pass_size": pass_identity["size"],
        "pass_sha256": pass_identity["sha256"],
        "result_path": record["result_path"],
        "result_size": result_identity["size"],
        "result_sha256": result_identity["sha256"],
    }
    if binding != expected:
        raise GateError("R4W1-C2 live clause connected evidence mismatch")
    if (
        record.get("helper_sha256") != CONNECTED_HELPER_SHA256
        or record.get("test_sha256") != CONNECTED_TEST_SHA256
        or record.get("policy_clause_sha256") != CONNECTED_CLAUSE_SHA256
    ):
        raise GateError("R4W1-C2 connected source or clause identity mismatch")
    if (
        core.read_stable_file(pass_path, maximum=1024 * 1024) != pass_before
        or core.read_stable_file(result_path, maximum=8 * 1024 * 1024)
        != result_before
    ):
        raise GateError("R4W1-C2 connected evidence changed while reopening")
    return {"binding": binding, "record": record}


def _direct_state_parent(root: Path) -> Path:
    return connected.require_direct_path(
        root,
        root / CONSUMED_STATE.parent,
        "R4W1-C2 consumed-state directory",
        directory=True,
    )


def prepared_binding(
    root: Path, run_dir: Path, baseline: dict[str, Any]
) -> dict[str, Any]:
    phases = odin_core.list_phase_receipts(run_dir)
    if len(phases) != 1 or phases[0].get("phase") != "prepared":
        raise GateError("R4W1-C2 consumption requires exactly one prepared receipt")
    expected_payload = connected.expected_phase_payload(baseline)
    if phase_payload(root, run_dir, "prepared") != expected_payload:
        raise GateError("R4W1-C2 prepared receipt does not bind the live baseline")
    record = phases[0]
    return {
        "path": str(
            connected.require_direct_path(
                root, Path(str(record["path"])), "R4W1-C2 prepared receipt"
            ).relative_to(root)
        ),
        "size": record["size"],
        "sha256": record["sha256"],
        "payload": expected_payload,
    }


def consume_exception(
    root: Path,
    run_dir: Path,
    artifacts: dict[str, Any],
    connected_evidence: dict[str, Any],
    policy: dict[str, Any],
    clause: str,
    baseline: dict[str, Any],
    usb_binding: dict[str, str],
    live_session_start_utc: str,
) -> dict[str, Any]:
    _direct_state_parent(root)
    path = root / CONSUMED_STATE
    if path.exists() or path.is_symlink():
        raise GateError("R4W1-C2 candidate exception is already consumed")
    android_serial = str(baseline["android_serial"])
    expected_usb_binding = {
        "topology": str(usb_binding.get("topology", "")),
        "serial_sha256": android_serial_sha256(android_serial),
        "download_serial_state": DOWNLOAD_USB_SERIAL_STATE,
    }
    if (
        USB_TOPOLOGY_RE.fullmatch(expected_usb_binding["topology"]) is None
        or usb_binding != expected_usb_binding
    ):
        raise GateError("R4W1-C2 USB binding does not match the Android serial")
    prepared = prepared_binding(root, run_dir, baseline)
    record = {
        "schema": "s22plus_fyg8_r4w1c2_measured_consumed_v1",
        "target": TARGET,
        "reason": "candidate_flash_start",
        "consumed_at_utc": core.utc_now(),
        "live_session_start_utc": live_session_start_utc,
        "run_dir": str(run_dir.relative_to(root)),
        "helper_sha256": helper_sha256(root),
        "test_sha256": test_sha256(root),
        "policy_draft": {
            "path": policy["path"],
            "size": policy["size"],
            "sha256": policy["sha256"],
        },
        "policy_clause_sha256": core.sha256_bytes(clause.encode("utf-8")),
        "connected_binding": connected_evidence["binding"],
        "prepared": prepared,
        "android_serial": android_serial,
        "android_boot_id": str(baseline["boot_id"]),
        "usb_binding": usb_binding,
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
        "candidate_ap_sha256": connected.EXPECTED_CANDIDATE_AP_SHA256,
        "static_result_sha256": connected.EXPECTED_STATIC_RESULT_SHA256,
        "magisk_ap_sha256": connected.EXPECTED_MAGISK_AP_SHA256,
        "stock_ap_sha256": connected.EXPECTED_STOCK_AP_SHA256,
        "artifact_target": artifacts["target"],
    }
    core.durable_create_json(path, record)
    _direct_state_parent(root)
    return record


def require_consumed(
    root: Path,
    artifacts: dict[str, Any],
    policy: dict[str, Any],
    clause: str,
) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    _direct_state_parent(root)
    path = connected.require_direct_path(
        root, root / CONSUMED_STATE, "R4W1-C2 consumed state"
    )
    consumed_bytes = core.read_stable_file(path, maximum=1024 * 1024)
    try:
        record = json.loads(consumed_bytes)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("R4W1-C2 consumed state is invalid") from exc
    expected = {
        "schema": "s22plus_fyg8_r4w1c2_measured_consumed_v1",
        "target": TARGET,
        "reason": "candidate_flash_start",
        "helper_sha256": helper_sha256(root),
        "test_sha256": test_sha256(root),
        "candidate_ap_sha256": connected.EXPECTED_CANDIDATE_AP_SHA256,
        "static_result_sha256": connected.EXPECTED_STATIC_RESULT_SHA256,
        "magisk_ap_sha256": connected.EXPECTED_MAGISK_AP_SHA256,
        "stock_ap_sha256": connected.EXPECTED_STOCK_AP_SHA256,
        "artifact_target": TARGET,
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
        "policy_draft": {
            "path": policy["path"],
            "size": policy["size"],
            "sha256": policy["sha256"],
        },
        "policy_clause_sha256": core.sha256_bytes(clause.encode("utf-8")),
    }
    required_keys = {
        *expected,
        "consumed_at_utc",
        "live_session_start_utc",
        "run_dir",
        "connected_binding",
        "prepared",
        "android_serial",
        "android_boot_id",
        "usb_binding",
    }
    if (
        not isinstance(record, dict)
        or set(record) != required_keys
        or any(record.get(key) != value for key, value in expected.items())
        or UTC_RE.fullmatch(str(record.get("consumed_at_utc", ""))) is None
        or UTC_RE.fullmatch(str(record.get("live_session_start_utc", ""))) is None
        or not isinstance(record.get("usb_binding"), dict)
        or set(record.get("usb_binding", {}))
        != {"topology", "serial_sha256", "download_serial_state"}
        or USB_TOPOLOGY_RE.fullmatch(
            str(record.get("usb_binding", {}).get("topology", ""))
        )
        is None
        or record.get("usb_binding", {}).get("download_serial_state")
        != DOWNLOAD_USB_SERIAL_STATE
        or re.fullmatch(
            r"[0-9a-f]{64}",
            str(record.get("usb_binding", {}).get("serial_sha256", "")),
        )
        is None
        or record.get("usb_binding", {}).get("serial_sha256")
        != android_serial_sha256(str(record.get("android_serial", "")))
        or re.fullmatch(
            r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
            str(record.get("android_boot_id", "")),
        )
        is None
    ):
        raise GateError("R4W1-C2 consumed state contract mismatch")
    relative = Path(str(record.get("run_dir", "")))
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or tuple(relative.parts[:3]) != ("workspace", "private", "runs")
    ):
        raise GateError("R4W1-C2 consumed run path is not canonical")
    run_dir = connected.require_direct_path(
        root, root / relative, "R4W1-C2 consumed run directory", directory=True
    )
    connected_evidence = reopen_connected_evidence(root, artifacts, clause)
    if record["connected_binding"] != connected_evidence["binding"]:
        raise GateError("R4W1-C2 consumed connected evidence binding mismatch")
    phases = odin_core.list_phase_receipts(run_dir)
    if not phases or phases[0].get("phase") != "prepared":
        raise GateError("R4W1-C2 consumed transaction lacks prepared evidence")
    prepared = phases[0]
    prepared_path = connected.require_direct_path(
        root, Path(str(prepared["path"])), "R4W1-C2 consumed prepared receipt"
    )
    prepared_summary = {
        "path": str(prepared_path.relative_to(root)),
        "size": prepared["size"],
        "sha256": prepared["sha256"],
        "payload": phase_payload(root, run_dir, "prepared"),
    }
    if record["prepared"] != prepared_summary:
        raise GateError("R4W1-C2 consumed prepared evidence mismatch")
    prepared_payload = prepared_summary["payload"]
    if (
        prepared_payload.get("android_serial") != record["android_serial"]
        or prepared_payload.get("boot_id") != record["android_boot_id"]
    ):
        raise GateError("R4W1-C2 consumed Android baseline mismatch")
    if core.read_stable_file(path, maximum=1024 * 1024) != consumed_bytes:
        raise GateError("R4W1-C2 consumed state changed while reopening")
    return record, run_dir, connected_evidence


def _ticket_payload(ticket: odin_core.EndpointTicket) -> dict[str, Any]:
    return {
        "device": ticket.device,
        "device_identity": ticket.device_identity,
        "generation": ticket.generation,
        "snapshot_sequence": ticket.snapshot_sequence,
        "snapshot_receipt": ticket.snapshot_receipt,
        "snapshot_receipt_sha256": ticket.snapshot_receipt_sha256,
    }


def next_snapshot_sequence(run_dir: Path) -> int:
    receipts = odin_core.list_snapshot_receipts(run_dir)
    sequences = [record["sequence"] for record in receipts]
    if sequences != list(range(len(sequences))):
        raise GateError("R4W1-C2 Odin snapshot sequence is not contiguous")
    return len(sequences)


def wait_for_endpoint(
    odin: Path,
    run_dir: Path,
    *,
    timeout_sec: float,
    sequence: int,
    lease: Any,
    expected_usb_binding: dict[str, str],
) -> tuple[odin_core.EndpointTicket, int]:
    started = time.monotonic()
    stable = wait_for_stable_download_node(expected_usb_binding, timeout_sec)
    remaining = timeout_sec - (time.monotonic() - started)
    if remaining <= 0:
        raise GateError("Download endpoint stabilization exhausted the wait deadline")
    result = odin_core.wait_for_single_live_endpoint(
        odin,
        run_dir,
        timeout_sec=remaining,
        sequence_start=sequence,
        poll_sec=1.0,
        lease=lease,
        endpoint_observer_factory=odin_core.measured_usbfs_observer,
    )
    if result.ticket is None or result.timed_out:
        raise GateError("one normal Download endpoint did not appear in time")
    stable_node = stable["node"]
    stable_device_identity = str(stable_node.get("immutable_identity", ""))
    if (
        result.ticket.device != stable["device"]
        or result.ticket.device_identity != stable_device_identity
    ):
        raise GateError("ticketed Odin endpoint differs from the stabilized endpoint")
    require_ticket_usb_binding(result.ticket, expected_usb_binding)
    return result.ticket, result.next_sequence


def revalidate_ticket(
    odin: Path,
    run_dir: Path,
    ticket: odin_core.EndpointTicket,
    *,
    sequence: int,
    lease: Any,
) -> tuple[str, int, dict[str, Any]]:
    record = odin_core.revalidate_endpoint_ticket(
        odin,
        run_dir,
        ticket,
        sequence=sequence,
        timeout_sec=15.0,
        lease=lease,
        endpoint_observer_factory=odin_core.measured_usbfs_observer,
    )
    return ticket.device, sequence + 1, record


def prepare_fresh_confirmation_input() -> int:
    try:
        descriptor = sys.stdin.fileno()
    except (OSError, ValueError) as exc:
        raise GateError("normal Download confirmation input is unavailable") from exc
    if os.isatty(descriptor):
        try:
            termios.tcflush(descriptor, termios.TCIFLUSH)
        except OSError as exc:
            raise GateError("normal Download TTY input could not be flushed") from exc
    else:
        try:
            ready, _, _ = select.select([descriptor], [], [], 0)
        except (OSError, ValueError) as exc:
            raise GateError("normal Download confirmation input is unavailable") from exc
        if ready:
            raise GateError("prebuffered normal Download confirmation is not fresh")
    return descriptor


def read_fresh_confirmation(timeout_sec: float, descriptor: int) -> str:
    if not math.isfinite(timeout_sec) or timeout_sec <= 0:
        raise GateError("normal Download confirmation window is invalid")
    deadline = time.monotonic() + timeout_sec
    payload = bytearray()
    while b"\n" not in payload:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GateError("normal Download confirmation timed out")
        ready, _, _ = select.select([descriptor], [], [], remaining)
        if not ready:
            raise GateError("normal Download confirmation timed out")
        chunk = os.read(descriptor, 256)
        if not chunk:
            raise GateError("normal Download confirmation was not provided")
        payload.extend(chunk)
        if len(payload) > 256:
            raise GateError("normal Download confirmation is oversized")
    line, separator, trailing = bytes(payload).partition(b"\n")
    if separator != b"\n" or trailing:
        raise GateError("normal Download confirmation has trailing input")
    try:
        return line.removesuffix(b"\r").decode("ascii")
    except UnicodeDecodeError as exc:
        raise GateError("normal Download confirmation is not ASCII") from exc


def confirm_normal_download(timeout_sec: float) -> None:
    descriptor = prepare_fresh_confirmation_input()
    print(
        "Confirm that the original candidate handset remains on the same cable, "
        "hub, and host port and that its screen is normal Samsung Download mode. "
        "Type the exact R4W1-C2 physical-continuity temporal confirmation token "
        "to permit boot-only rollback.",
        flush=True,
    )
    if read_fresh_confirmation(timeout_sec, descriptor) != NORMAL_DOWNLOAD_CONFIRMATION:
        raise GateError("normal Download confirmation mismatch")


def confirm_stock_cleanup(timeout_sec: float) -> None:
    descriptor = prepare_fresh_confirmation_input()
    print(
        "Magisk rollback returned a definite failure. Confirm that the original "
        "candidate handset still remains on the same cable, hub, and host port "
        "in normal Samsung Download mode. Type the exact R4W1-C2 stock-cleanup "
        "physical-continuity confirmation token to permit the cleanup transfer.",
        flush=True,
    )
    if read_fresh_confirmation(timeout_sec, descriptor) != STOCK_CLEANUP_CONFIRMATION:
        raise GateError("stock cleanup confirmation mismatch")


def observe_candidate(seconds: float) -> dict[str, Any]:
    if not math.isfinite(seconds) or not 0 <= seconds <= 180:
        raise GateError("candidate observation bound is invalid")
    started = time.monotonic()
    time.sleep(seconds)
    elapsed = time.monotonic() - started
    return {
        "bounded": True,
        "requested_sec": seconds,
        "elapsed_sec": round(elapsed, 6),
        "full_window_completed": elapsed >= seconds,
        "candidate_adb_required": False,
        "host_rdx_command": False,
        "watchdog_survival_directly_proven": False,
        "meaning": "passive time window only; endpoint absence is not liveness proof",
    }


def wait_magisk_android(
    seconds: float,
    *,
    expected_serial: str,
    expected_usb_binding: dict[str, str],
) -> tuple[str, dict[str, str]]:
    if not math.isfinite(seconds) or seconds <= 0:
        raise GateError("Android wait bound is invalid")
    deadline = time.monotonic() + seconds
    last_error = "no Android observation"
    while time.monotonic() < deadline:
        try:
            serial, android = connected.current_android_exact()
            if serial != expected_serial:
                raise GateError("exact Android serial changed across rollback")
            if adb_usb_binding(serial) != expected_usb_binding:
                raise GateError("exact Android USB binding changed across rollback")
            return serial, android
        except (connected.GateError, transport.GateError, OSError, subprocess.SubprocessError) as exc:
            last_error = str(exc)
            time.sleep(2)
    raise GateError(f"exact Magisk Android did not return: {last_error}")


def collect_rollback_observer(
    root: Path, serial: str, run_dir: Path, attempt: int
) -> dict[str, Any]:
    if not 0 <= attempt <= MAX_RECOVERY_ATTEMPTS:
        raise GateError("rollback observer attempt is out of range")
    prefix = "live" if attempt == 0 else f"recovery-{attempt:02d}"
    paths = [
        run_dir / f"rollback_last_kmsg_{prefix}_1.bin",
        run_dir / f"rollback_last_kmsg_{prefix}_2.bin",
    ]
    receipts: list[dict[str, Any]] = []
    payloads: list[bytes] = []
    for path in paths:
        receipt = core.capture_adb_exec_out(
            serial,
            "cat /proc/last_kmsg",
            path,
            root=True,
            timeout=120,
            maximum=MAX_OBSERVER_BYTES,
        )
        payload = core.read_stable_file(path, maximum=MAX_OBSERVER_BYTES)
        if not payload:
            raise GateError("rollback last_kmsg is empty")
        receipts.append(receipt)
        payloads.append(payload)
        time.sleep(0.25)
    if payloads[0] != payloads[1]:
        raise GateError("rollback last_kmsg reads are not byte-identical")
    marker = connected.classify_marker(payloads[0])
    bindings = []
    for receipt, path in zip(receipts, paths):
        stderr_path = path.with_suffix(path.suffix + ".stderr")
        bindings.append(
            {
                "path": str(path.relative_to(root)),
                **core.hash_stable_file(path),
                "stderr_path": str(stderr_path.relative_to(root)),
                "stderr": core.hash_stable_file(stderr_path),
                "receipt": receipt,
            }
        )
    result = {
        "reads": receipts,
        "bindings": bindings,
        "byte_identical": True,
        "read_to_eof": all(receipt["read_to_eof"] for receipt in receipts),
        "stderr_bytes": sum(receipt["stderr_bytes"] for receipt in receipts),
        "bytes": len(payloads[0]),
        "sha256": core.sha256_bytes(payloads[0]),
        "marker": marker,
        "watchdog_survival_directly_proven": False,
        "load_bearing": True,
    }
    summary_path = run_dir / f"rollback_last_kmsg_{prefix}.json"
    core.durable_create_json(summary_path, result)
    result["summary"] = {
        "path": str(summary_path.relative_to(root)),
        **core.hash_stable_file(summary_path),
    }
    return result


def reopen_rollback_observer(
    root: Path, run_dir: Path, payload: dict[str, Any]
) -> dict[str, Any]:
    summary = payload.get("summary")
    if not isinstance(summary, dict) or set(summary) != {"path", "size", "sha256"}:
        raise GateError("rollback observer phase lacks a summary binding")
    summary_path = connected.require_direct_path(
        root, root / Path(str(summary["path"])), "R4W1-C2 rollback observer summary"
    )
    if run_dir not in summary_path.parents:
        raise GateError("rollback observer summary escaped the transaction run")
    if core.hash_stable_file(summary_path) != {
        "size": summary["size"],
        "sha256": summary["sha256"],
    }:
        raise GateError("rollback observer summary identity mismatch")
    try:
        observer = json.loads(
            core.read_stable_file(summary_path, maximum=2 * 1024 * 1024)
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError("rollback observer summary is invalid") from exc
    bindings = observer.get("bindings")
    if not isinstance(bindings, list) or len(bindings) != 2:
        raise GateError("rollback observer binding count mismatch")
    payloads: list[bytes] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            raise GateError("rollback observer binding is malformed")
        path = connected.require_direct_path(
            root, root / Path(str(binding.get("path", ""))), "rollback observer"
        )
        stderr_path = connected.require_direct_path(
            root,
            root / Path(str(binding.get("stderr_path", ""))),
            "rollback observer stderr",
        )
        if run_dir not in path.parents or run_dir not in stderr_path.parents:
            raise GateError("rollback observer binding escaped the transaction run")
        raw = core.read_stable_file(path, maximum=MAX_OBSERVER_BYTES)
        stderr = core.read_stable_file(stderr_path, maximum=1024 * 1024)
        if (
            {"size": len(raw), "sha256": core.sha256_bytes(raw)}
            != {"size": binding.get("size"), "sha256": binding.get("sha256")}
            or {"size": len(stderr), "sha256": core.sha256_bytes(stderr)}
            != binding.get("stderr")
            or stderr
        ):
            raise GateError("rollback observer raw identity mismatch")
        payloads.append(raw)
    if not payloads[0] or payloads[0] != payloads[1]:
        raise GateError("rollback observer raw reads are not stable and identical")
    expected_marker = connected.classify_marker(payloads[0])
    if (
        observer.get("marker") != expected_marker
        or observer.get("sha256") != core.sha256_bytes(payloads[0])
        or observer.get("bytes") != len(payloads[0])
        or observer.get("byte_identical") is not True
        or observer.get("read_to_eof") is not True
        or observer.get("stderr_bytes") != 0
    ):
        raise GateError("rollback observer summary semantics mismatch")
    observer["summary"] = summary
    if core.hash_stable_file(summary_path) != {
        "size": summary["size"],
        "sha256": summary["sha256"],
    }:
        raise GateError("rollback observer changed while reopening")
    return observer


def find_completed_rollback_observer(
    root: Path, run_dir: Path
) -> dict[str, Any] | None:
    candidates = [run_dir / "rollback_last_kmsg_live.json"]
    candidates.extend(
        run_dir / f"rollback_last_kmsg_recovery-{attempt:02d}.json"
        for attempt in range(1, MAX_RECOVERY_ATTEMPTS + 1)
    )
    for path in candidates:
        if not path.exists() and not path.is_symlink():
            continue
        direct = connected.require_direct_path(
            root, path, "R4W1-C2 completed rollback observer summary"
        )
        summary = {
            "path": str(direct.relative_to(root)),
            **core.hash_stable_file(direct),
        }
        return reopen_rollback_observer(root, run_dir, {"summary": summary})
    return None


def classify_verdict(
    *,
    rollback_target: str | None,
    rollback_ok: bool,
    candidate_transfer_ok: bool,
    candidate_observation: dict[str, Any] | None,
    observer: dict[str, Any] | None,
) -> tuple[str, int]:
    if rollback_target != "magisk" or not rollback_ok:
        return "FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED", 20
    if observer is None:
        return "FAIL_R4W1C2_OBSERVER_CAPTURE", 21
    marker = observer.get("marker")
    if not isinstance(marker, dict) or marker.get("integrity_issue") is True:
        return "FAIL_R4W1C2_MARKER_INTEGRITY", 22
    if not candidate_transfer_ok:
        if marker.get("acceptance_present") is True:
            return "FAIL_R4W1C2_MARKER_INTEGRITY", 23
        return "FAIL_R4W1C2_CANDIDATE_TRANSFER_AND_ROLLED_BACK", 24
    if (
        not isinstance(candidate_observation, dict)
        or candidate_observation.get("bounded") is not True
        or candidate_observation.get("requested_sec") != DEFAULT_PARK_WAIT_SEC
        or candidate_observation.get("full_window_completed") is not True
        or candidate_observation.get("odin_disconnected") is not True
        or candidate_observation.get("candidate_transfer_ok") is not True
        or not isinstance(candidate_observation.get("elapsed_sec"), (int, float))
        or candidate_observation["elapsed_sec"] < DEFAULT_PARK_WAIT_SEC
    ):
        return "FAIL_R4W1C2_CANDIDATE_OBSERVATION_REQUIRED", 25
    if marker.get("acceptance_present") is True:
        return PASS_VERDICT, 0
    return NO_PROOF_VERDICT, 32


def _phase_names(run_dir: Path) -> list[str]:
    return [record["phase"] for record in odin_core.list_phase_receipts(run_dir)]


def phase_payload(root: Path, run_dir: Path, phase: str) -> dict[str, Any] | None:
    path = run_dir / "receipts" / f"phase-{phase}.json"
    if not path.exists() and not path.is_symlink():
        return None
    path = connected.require_direct_path(
        root, path, f"R4W1-C2 phase receipt {phase}"
    )
    payload = core.read_stable_file(path, maximum=odin_core.MAX_RECEIPT_BYTES)
    try:
        value = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"R4W1-C2 phase receipt is invalid: {phase}") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != odin_core.PHASE_SCHEMA
        or value.get("phase") != phase
        or not isinstance(value.get("payload"), dict)
    ):
        raise GateError(f"R4W1-C2 phase receipt contract mismatch: {phase}")
    records = {
        record["phase"]: record for record in odin_core.list_phase_receipts(run_dir)
    }
    record = records.get(phase)
    if record is None or {
        "size": len(payload),
        "sha256": core.sha256_bytes(payload),
    } != {"size": record["size"], "sha256": record["sha256"]}:
        raise GateError(f"R4W1-C2 phase receipt identity mismatch: {phase}")
    return value["payload"]


def create_phase(
    run_dir: Path,
    phase: str,
    payload: dict[str, Any],
    *,
    lease: Any,
) -> dict[str, Any]:
    return odin_core.create_phase_receipt(run_dir, phase, payload, lease=lease)


def normalize_recovery_prefix(run_dir: Path, *, lease: Any) -> None:
    phases = _phase_names(run_dir)
    if not phases or phases[0] != "prepared":
        raise GateError("recovery requires the original prepared transaction")
    fillers = {
        "candidate_transfer_started": {
            "recovery_fill": True,
            "status": "consumed-before-transfer-intent-no-transfer-started",
        },
        "candidate_transfer_finished": {
            "recovery_fill": True,
            "status": "interrupted-transfer-result-unknown",
        },
        "candidate_observation_closed": {
            "recovery_fill": True,
            "status": "interrupted-no-candidate-observation-proof",
        },
    }
    for phase in odin_core.TRANSACTION_PHASES[1:4]:
        phases = _phase_names(run_dir)
        if phase in phases:
            continue
        if phases != list(odin_core.TRANSACTION_PHASES[: len(phases)]):
            raise GateError("recovery phase receipts are not a forward prefix")
        create_phase(run_dir, phase, fillers[phase], lease=lease)


def candidate_state(root: Path, run_dir: Path) -> dict[str, Any]:
    started = phase_payload(root, run_dir, "candidate_transfer_started")
    finished = phase_payload(root, run_dir, "candidate_transfer_finished")
    observation = phase_payload(root, run_dir, "candidate_observation_closed")
    if finished is None:
        status = "not-started" if started is None else "transfer-outcome-unknown"
        ok = False
    elif finished.get("ok") is True:
        status = "transfer-completed"
        ok = True
    elif finished.get("ok") is False:
        status = "transfer-failed"
        ok = False
    else:
        status = "transfer-outcome-unknown"
        ok = False
    return {
        "candidate_transfer_ok": ok,
        "candidate_status": status,
        "candidate_transfer_started": started,
        "candidate_transfer_finished": finished,
        "candidate_observation": observation,
    }


def create_ambiguous_retry_intent(
    root: Path,
    run_dir: Path,
    *,
    attempt: int,
    ticket: odin_core.EndpointTicket,
    topology: dict[str, str],
) -> dict[str, Any]:
    path = run_dir / "rollback-ambiguous-retry-intent.json"
    if path.exists() or path.is_symlink():
        raise GateError("ambiguous rollback retry was already consumed")
    record = {
        "schema": "s22plus_fyg8_r4w1c_ambiguous_rollback_retry_v1",
        "created_at_utc": core.utc_now(),
        "attempt": attempt,
        "ack": AMBIGUOUS_ROLLBACK_RETRY_ACK,
        "ticket": _ticket_payload(ticket),
        "usb_binding": topology,
        "target": "magisk",
        "magisk_ap_sha256": connected.EXPECTED_MAGISK_AP_SHA256,
    }
    core.durable_create_json(path, record)
    connected.require_direct_path(root, path, "ambiguous rollback retry intent")
    return record


def create_stock_cleanup_intent(
    root: Path,
    run_dir: Path,
    *,
    attempt: int,
    ticket: odin_core.EndpointTicket,
    topology: dict[str, str],
) -> dict[str, Any]:
    path = run_dir / STOCK_CLEANUP_INTENT_NAME
    if path.exists() or path.is_symlink():
        raise GateError("stock cleanup intent was already consumed")
    record = {
        "schema": "s22plus_fyg8_r4w1c_stock_cleanup_intent_v1",
        "created_at_utc": core.utc_now(),
        "attempt": attempt,
        "ack": STOCK_CLEANUP_CONFIRMATION,
        "ticket": _ticket_payload(ticket),
        "usb_binding": topology,
        "target": "stock",
        "stock_ap_sha256": connected.EXPECTED_STOCK_AP_SHA256,
        "magisk_failure": "definite-nonzero",
    }
    core.durable_create_json(path, record)
    connected.require_direct_path(root, path, "stock cleanup intent")
    return record


def stock_cleanup_tainted(run_dir: Path) -> bool:
    path = run_dir / STOCK_CLEANUP_INTENT_NAME
    return path.exists() or path.is_symlink()


def require_no_stock_cleanup_taint(run_dir: Path) -> None:
    if stock_cleanup_tainted(run_dir):
        raise GateError(
            "stock cleanup intent permanently taints this transaction; "
            "automatic recovery is forbidden"
        )


def stock_cleanup_evidence(root: Path, run_dir: Path) -> dict[str, Any] | None:
    if not stock_cleanup_tainted(run_dir):
        return None
    intent = connected.require_direct_path(
        root, run_dir / STOCK_CLEANUP_INTENT_NAME, "stock cleanup intent"
    )
    evidence: dict[str, Any] = {
        "intent": {
            "path": str(intent.relative_to(root)),
            **core.hash_stable_file(intent),
        },
        "transfer_logs": [],
    }
    logs = sorted(run_dir.glob("odin-stock-attempt-*.json"))
    if len(logs) > 1:
        raise GateError("multiple stock cleanup transfer logs are forbidden")
    for path in logs:
        if re.fullmatch(r"odin-stock-attempt-[0-9]{2}\.json", path.name) is None:
            raise GateError("stock cleanup transfer log name is malformed")
        direct = connected.require_direct_path(root, path, "stock cleanup transfer log")
        evidence["transfer_logs"].append(
            {"path": str(direct.relative_to(root)), **core.hash_stable_file(direct)}
        )
    return evidence


def transaction_evidence(root: Path, run_dir: Path) -> dict[str, Any]:
    snapshots = odin_core.list_snapshot_receipts(run_dir)
    phases = odin_core.list_phase_receipts(run_dir)
    indexed = odin_core.read_transaction_segments(run_dir)
    records = indexed.get("records")
    segments = indexed.get("segments")
    if not isinstance(records, list) or not isinstance(segments, list) or not segments:
        raise GateError("R4W1-C2 transaction index evidence is incomplete")
    receipt_summaries: list[dict[str, Any]] = []
    known: dict[str, dict[str, Any]] = {}
    for record in [*snapshots, *phases]:
        path = connected.require_direct_path(
            root, Path(str(record["path"])), "R4W1-C2 transaction receipt"
        )
        payload = core.read_stable_file(path, maximum=odin_core.MAX_RECEIPT_BYTES)
        if {"size": len(payload), "sha256": core.sha256_bytes(payload)} != {
            "size": record["size"],
            "sha256": record["sha256"],
        }:
            raise GateError("R4W1-C2 transaction receipt identity mismatch")
        absolute = str(path)
        receipt_summaries.append({**record, "path": str(path.relative_to(root))})
        known[absolute] = record
    if len(records) != len(known):
        raise GateError("R4W1-C2 transaction index record count mismatch")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise GateError("R4W1-C2 transaction index record is malformed")
        receipt = record.get("receipt")
        if not isinstance(receipt, str) or receipt in seen:
            raise GateError("R4W1-C2 transaction index receipt reference is invalid")
        expected = known.get(receipt)
        if expected is None:
            raise GateError("R4W1-C2 transaction index references an unknown receipt")
        if (
            record.get("receipt_size") != expected["size"]
            or record.get("receipt_sha256") != expected["sha256"]
        ):
            raise GateError("R4W1-C2 transaction index receipt identity mismatch")
        seen.add(receipt)
    if seen != set(known):
        raise GateError("R4W1-C2 transaction index omits a receipt")
    segment_summaries: list[dict[str, Any]] = []
    for segment in segments:
        if segment.get("complete") is not True or segment.get("partial_tail_bytes") != 0:
            raise GateError("R4W1-C2 transaction index has an incomplete segment")
        path = connected.require_direct_path(
            root, Path(str(segment["path"])), "R4W1-C2 transaction index"
        )
        segment_summaries.append(
            {**segment, **core.hash_stable_file(path), "path": str(path.relative_to(root))}
        )
    evidence = {
        "snapshots": [record for record in receipt_summaries if "sequence" in record],
        "phases": [record for record in receipt_summaries if "phase" in record],
        "index_segments": segment_summaries,
        "record_count": len(records),
        "stock_cleanup": stock_cleanup_evidence(root, run_dir),
    }
    if (
        odin_core.list_snapshot_receipts(run_dir) != snapshots
        or odin_core.list_phase_receipts(run_dir) != phases
        or odin_core.read_transaction_segments(run_dir) != indexed
    ):
        raise GateError("R4W1-C2 transaction evidence changed while reopening")
    return evidence


def append_timeline_event(
    path: Path,
    events: list[dict[str, str]],
    name: str,
    *,
    timestamp_utc: str | None = None,
) -> None:
    if name not in core.TIMELINE_NAMES:
        raise GateError(f"unknown R4W1-C2 timeline event: {name}")
    if any(event.get("name") == name for event in events):
        return
    index = core.TIMELINE_NAMES.index(name)
    if events and index <= core.TIMELINE_NAMES.index(events[-1]["name"]):
        raise GateError("R4W1-C2 timeline events are not strictly ordered")
    stamp = timestamp_utc or core.utc_now()
    if UTC_RE.fullmatch(stamp) is None:
        raise GateError("R4W1-C2 timeline timestamp is malformed")
    events.append({"name": name, "timestamp_utc": stamp})
    core.durable_write_json(path, {"events": events})


def phase_timestamp(run_dir: Path, phase: str) -> str | None:
    for record in odin_core.list_phase_receipts(run_dir):
        if record["phase"] == phase:
            return str(record["timestamp_utc"])
    return None


def recovery_timeline_seed(
    root: Path, consumed: dict[str, Any], run_dir: Path
) -> list[dict[str, str]]:
    events = [
        {
            "name": "live_session_start",
            "timestamp_utc": str(consumed["live_session_start_utc"]),
        },
        {
            "name": "candidate_flash_start",
            "timestamp_utc": str(consumed["consumed_at_utc"]),
        },
    ]
    finished = phase_payload(root, run_dir, "candidate_transfer_finished")
    if finished is not None:
        stamp = phase_timestamp(run_dir, "candidate_transfer_finished")
        if stamp is None:
            raise GateError("candidate transfer timestamp is unavailable")
        events.append({"name": "candidate_flash_done", "timestamp_utc": stamp})
    observation = phase_payload(root, run_dir, "candidate_observation_closed")
    if (
        isinstance(observation, dict)
        and observation.get("candidate_transfer_ok") is True
        and observation.get("odin_disconnected") is True
        and observation.get("full_window_completed") is True
    ):
        stamp = phase_timestamp(run_dir, "candidate_observation_closed")
        if stamp is None:
            raise GateError("candidate observation timestamp is unavailable")
        events.append({"name": "candidate_boot_ready", "timestamp_utc": stamp})
    return events


def _finish(
    root: Path,
    run_dir: Path,
    timeline_path: Path,
    timeline: list[dict[str, str]],
    result: dict[str, Any],
    *,
    verdict: str,
    rc: int,
    result_name: str,
    error: str | None = None,
) -> int:
    append_timeline_event(timeline_path, timeline, "live_session_end")
    if verdict == PASS_VERDICT and stock_cleanup_tainted(run_dir):
        verdict = "FAIL_R4W1C2_STOCK_CLEANUP_TAINTED"
        rc = 34
        error = "stock cleanup intent permanently forbids PASS"
    if verdict == PASS_VERDICT and [event["name"] for event in timeline] != list(
        core.TIMELINE_NAMES
    ):
        verdict = "FAIL_R4W1C2_PASS_TIMELINE_INCOMPLETE"
        rc = 26
        error = "PASS requires all eight exact action milestones"
    result["verdict"] = verdict
    if error is not None:
        result["error"] = error
    try:
        result["transaction_evidence"] = transaction_evidence(root, run_dir)
    except (GateError, odin_core.OdinTransitionError, OSError) as exc:
        if rc == 0:
            raise
        result["transaction_evidence"] = None
        result["transaction_evidence_error"] = str(exc)
    result["timeline"] = {"path": str(timeline_path.relative_to(root)), "events": timeline}
    result_path = run_dir / result_name
    core.durable_create_json(result_path, result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": verdict}, indent=2))
    return rc


def next_recovery_attempt(root: Path, run_dir: Path) -> tuple[int, Path, Path]:
    attempts: list[int] = []
    for path in run_dir.glob("recovery-attempt-*-timeline.json"):
        connected.require_direct_path(root, path, "R4W1-C2 recovery timeline")
        match = re.fullmatch(r"recovery-attempt-([0-9]{2})-timeline\.json", path.name)
        if match is None:
            raise GateError("R4W1-C2 recovery timeline name is malformed")
        attempts.append(int(match.group(1)))
    attempts.sort()
    if attempts != list(range(1, len(attempts) + 1)):
        raise GateError("R4W1-C2 recovery attempt sequence is not contiguous")
    attempt = len(attempts) + 1
    if attempt > MAX_RECOVERY_ATTEMPTS:
        raise GateError("R4W1-C2 recovery failed twice; automatic recovery is stopped")
    timeline = run_dir / f"recovery-attempt-{attempt:02d}-timeline.json"
    result = run_dir / f"result-recovery-attempt-{attempt:02d}.json"
    if result.exists() or result.is_symlink():
        raise GateError("R4W1-C2 recovery result already exists")
    return attempt, timeline, result


def _rollback_sequence(
    root: Path,
    args: argparse.Namespace,
    run_dir: Path,
    timeline_path: Path,
    timeline: list[dict[str, str]],
    result: dict[str, Any],
    odin: Path,
    odin_fd: int,
    *,
    sequence: int,
    lease: Any,
    attempt: int,
    result_name: str,
) -> int:
    rollback_target: str | None = None
    rollback_ok = False
    observer: dict[str, Any] | None = None
    try:
        completed_transfer = phase_payload(root, run_dir, "rollback_transfer_finished")
        rollback_intent = phase_payload(root, run_dir, "rollback_confirmed")
        if completed_transfer is None:
            inferred_android: tuple[str, dict[str, str]] | None = None
            ambiguous_retry = rollback_intent is not None
            if ambiguous_retry:
                try:
                    inferred_android = wait_magisk_android(
                        args.ambiguous_android_probe_sec,
                        expected_serial=str(result["android_serial"]),
                        expected_usb_binding=dict(result["usb_binding"]),
                    )
                except GateError:
                    inferred_android = None
            if inferred_android is not None:
                rollback_target = "magisk"
                create_phase(
                    run_dir,
                    "rollback_transfer_finished",
                    {
                        "target": "magisk",
                        "completion_evidence": "exact-magisk-android-postcondition",
                        "retransmitted": False,
                    },
                    lease=lease,
                )
                completed_transfer = phase_payload(
                    root, run_dir, "rollback_transfer_finished"
                )
            else:
                if ambiguous_retry and args.ambiguous_rollback_ack != AMBIGUOUS_ROLLBACK_RETRY_ACK:
                    raise GateError(
                        "rollback outcome is ambiguous; fresh ambiguous-retry acknowledgement required"
                    )
                ticket, sequence = wait_for_endpoint(
                    odin,
                    run_dir,
                    timeout_sec=args.rollback_endpoint_wait_sec,
                    sequence=sequence,
                    lease=lease,
                    expected_usb_binding=dict(result["usb_binding"]),
                )
                topology = require_ticket_usb_binding(
                    ticket, dict(result["usb_binding"])
                )
                if (
                    not ambiguous_retry
                    and phase_payload(root, run_dir, "rollback_endpoint_observed")
                    is None
                ):
                    create_phase(
                        run_dir,
                        "rollback_endpoint_observed",
                        {"ticket": _ticket_payload(ticket), "usb": topology},
                        lease=lease,
                    )
                confirm_normal_download(args.confirmation_wait_sec)
                if not ambiguous_retry:
                    create_phase(
                        run_dir,
                        "rollback_confirmed",
                        {
                            "temporal_confirmation": NORMAL_DOWNLOAD_CONFIRMATION,
                            "transfer_intent": "magisk",
                            "ticket": _ticket_payload(ticket),
                            "usb": topology,
                        },
                        lease=lease,
                    )
                else:
                    create_ambiguous_retry_intent(
                        root,
                        run_dir,
                        attempt=attempt,
                        ticket=ticket,
                        topology=topology,
                    )
                append_timeline_event(
                    timeline_path,
                    timeline,
                    "rollback_flash_start",
                    timestamp_utc=phase_timestamp(run_dir, "rollback_confirmed")
                    if not ambiguous_retry
                    else None,
                )

                def transfer_revalidation() -> tuple[str, dict[str, Any]]:
                    nonlocal sequence
                    device, sequence, record = revalidate_ticket(
                        odin, run_dir, ticket, sequence=sequence, lease=lease
                    )
                    return device, {
                        "endpoint": record,
                        "usb": require_ticket_usb_binding(
                            ticket, dict(result["usb_binding"])
                        ),
                    }

                try:
                    transfer, revalidation = flash_sealed_exact(
                        odin_fd,
                        resolve(root, args.magisk_ap),
                        ap_size=connected.EXPECTED_MAGISK_AP_SIZE,
                        ap_sha256=connected.EXPECTED_MAGISK_AP_SHA256,
                        label="r4w1c-magisk-rollback",
                        log_path=run_dir
                        / f"odin-magisk-attempt-{attempt:02d}.json",
                        revalidate=transfer_revalidation,
                    )
                    rollback_target = "magisk"
                except OdinCommandFailed as magisk_error:
                    confirm_stock_cleanup(args.confirmation_wait_sec)
                    create_stock_cleanup_intent(
                        root,
                        run_dir,
                        attempt=attempt,
                        ticket=ticket,
                        topology=topology,
                    )

                    def cleanup_revalidation_action() -> tuple[str, dict[str, Any]]:
                        nonlocal sequence
                        device, sequence, record = revalidate_ticket(
                            odin, run_dir, ticket, sequence=sequence, lease=lease
                        )
                        return device, {
                            "endpoint": record,
                            "usb": require_ticket_usb_binding(
                                ticket, dict(result["usb_binding"])
                            ),
                        }

                    cleanup_transfer, cleanup_revalidation = flash_sealed_exact(
                        odin_fd,
                        resolve(root, args.stock_ap),
                        ap_size=connected.EXPECTED_STOCK_AP_SIZE,
                        ap_sha256=connected.EXPECTED_STOCK_AP_SHA256,
                        label="r4w1c-stock-cleanup",
                        log_path=run_dir
                        / f"odin-stock-attempt-{attempt:02d}.json",
                        revalidate=cleanup_revalidation_action,
                    )
                    rollback_target = "stock"
                    transfer = {
                        "magisk_error": str(magisk_error),
                        "stock_cleanup": cleanup_transfer,
                    }
                    revalidation = {"stock_cleanup": cleanup_revalidation}
                create_phase(
                    run_dir,
                    "rollback_transfer_finished",
                    {
                        "target": rollback_target,
                        "revalidation": revalidation,
                        "transfer": transfer,
                        "ambiguous_retry": ambiguous_retry,
                    },
                    lease=lease,
                )
                completed_transfer = phase_payload(
                    root, run_dir, "rollback_transfer_finished"
                )
        else:
            rollback_target = completed_transfer.get("target")
            if rollback_target not in {"magisk", "stock"}:
                raise GateError("completed rollback transfer receipt is ambiguous")
        rollback_target = str(completed_transfer.get("target"))
        rollback_start_stamp = phase_timestamp(run_dir, "rollback_confirmed")
        if rollback_start_stamp is not None:
            append_timeline_event(
                timeline_path,
                timeline,
                "rollback_flash_start",
                timestamp_utc=rollback_start_stamp,
            )
        append_timeline_event(
            timeline_path,
            timeline,
            "rollback_flash_done",
            timestamp_utc=phase_timestamp(run_dir, "rollback_transfer_finished"),
        )
        if rollback_target != "magisk":
            raise GateError("stock cleanup cannot satisfy exact Magisk rollback")
        serial, final_android = (
            inferred_android
            if "inferred_android" in locals() and inferred_android is not None
            else wait_magisk_android(
                args.android_wait_sec,
                expected_serial=str(result["android_serial"]),
                expected_usb_binding=dict(result["usb_binding"]),
            )
        )
        absence = odin_core.wait_for_no_live_endpoint(
            odin,
            run_dir,
            timeout_sec=args.odin_absence_wait_sec,
            sequence_start=sequence,
            poll_sec=0.1,
            lease=lease,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
        )
        sequence = absence.next_sequence
        if not absence.absent or absence.timed_out:
            raise GateError("rollback Android retained an Odin endpoint")
        rollback_ok = True
        if "rollback_android_ready" not in _phase_names(run_dir):
            create_phase(
                run_dir,
                "rollback_android_ready",
                {"android": final_android, "no_odin_endpoint": True},
                lease=lease,
            )
        append_timeline_event(
            timeline_path,
            timeline,
            "rollback_boot_ready",
            timestamp_utc=phase_timestamp(run_dir, "rollback_android_ready"),
        )
        observer_phase = phase_payload(
            root, run_dir, "first_rollback_observer_captured"
        )
        if observer_phase is None:
            observer = find_completed_rollback_observer(root, run_dir)
            if observer is None:
                observer = collect_rollback_observer(root, serial, run_dir, attempt)
            create_phase(
                run_dir,
                "first_rollback_observer_captured",
                {
                    "bytes": observer["bytes"],
                    "sha256": observer["sha256"],
                    "byte_identical": True,
                    "summary": observer["summary"],
                },
                lease=lease,
            )
        else:
            observer = reopen_rollback_observer(root, run_dir, observer_phase)
        verdict, rc = classify_verdict(
            rollback_target=rollback_target,
            rollback_ok=rollback_ok,
            candidate_transfer_ok=bool(result.get("candidate_transfer_ok")),
            candidate_observation=result.get("candidate_observation"),
            observer=observer,
        )
        if "classified" not in _phase_names(run_dir):
            create_phase(run_dir, "classified", {"verdict": verdict}, lease=lease)
        result.update(
            {
                "rollback_target": rollback_target,
                "rollback_ok": rollback_ok,
                "final_android": final_android,
                "rollback_last_kmsg": observer,
                "final_snapshot_sequence": sequence - 1,
            }
        )
        return _finish(
            root,
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict=verdict,
            rc=rc,
            result_name=result_name,
        )
    except (
        GateError,
        connected.GateError,
        core.LiveCoreError,
        odin_core.OdinTransitionError,
        transport.GateError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        result.update(
            {
                "rollback_target": rollback_target,
                "rollback_ok": rollback_ok,
                "rollback_last_kmsg": observer,
            }
        )
        return _finish(
            root,
            run_dir,
            timeline_path,
            timeline,
            result,
            verdict="FAIL_R4W1C2_ROLLBACK_NOT_VERIFIED_RECOVERY_REQUIRED",
            rc=20,
            result_name=result_name,
            error=str(exc),
        )


def _live_run_with_odin(
    root: Path,
    args: argparse.Namespace,
    artifacts: dict[str, Any],
    policy: dict[str, Any],
    odin: Path,
    odin_fd: int,
) -> int:
    if not policy_active(root) or policy.get("active") is not True:
        raise GateError("R4W1-C2 live policy is inactive")
    if args.ack != LIVE_ACK_TOKEN:
        raise GateError("R4W1-C2 live acknowledgement mismatch")
    clause = policy_clause(root)
    connected_evidence = reopen_connected_evidence(root, artifacts, clause)
    _direct_state_parent(root)
    if (root / CONSUMED_STATE).exists() or (root / CONSUMED_STATE).is_symlink():
        raise GateError("R4W1-C2 candidate exception is already consumed")
    run_dir = core.allocate_run_dir(root, RUN_ROOT, "s22plus-r4w1c2-measured-live", args.run_dir)
    timeline_path = run_dir / "timeline-live.json"
    timeline: list[dict[str, str]] = []
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": "live",
        "target": TARGET,
        "artifacts": artifacts,
        "policy": policy,
        "connected_evidence": connected_evidence["binding"],
        "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
        "candidate_transfer_attempted": False,
        "candidate_transfer_ok": False,
        "verdict": "INCOMPLETE",
    }
    append_timeline_event(timeline_path, timeline, "live_session_start")
    with odin_core.transaction_session(run_dir) as lease:
        try:
            baseline = connected.connected_preflight(
                root,
                run_dir,
                odin,
                odin_absence_wait_sec=args.odin_absence_wait_sec,
                lease=lease,
            )
            result["baseline"] = baseline
            serial = str(baseline["android_serial"])
            result["android_serial"] = serial
            usb_binding = adb_usb_binding(serial)
            result["usb_binding"] = usb_binding
            reboot = transport.run(["adb", "-s", serial, "reboot", "download"], timeout=20)
            if reboot.returncode != 0:
                raise GateError("baseline Android failed to request Download mode")
            sequence = next_snapshot_sequence(run_dir)
            ticket, sequence = wait_for_endpoint(
                odin,
                run_dir,
                timeout_sec=args.candidate_endpoint_wait_sec,
                sequence=sequence,
                lease=lease,
                expected_usb_binding=usb_binding,
            )
            candidate_usb = require_ticket_usb_binding(ticket, usb_binding)
        except (
            GateError,
            connected.GateError,
            core.LiveCoreError,
            odin_core.OdinTransitionError,
            transport.GateError,
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            return _finish(
                root,
                run_dir,
                timeline_path,
                timeline,
                result,
                verdict="FAIL_R4W1C2_PRECONSUMPTION_NO_CANDIDATE_FLASH",
                rc=1,
                result_name="result-live.json",
                error=str(exc),
            )

        try:
            current_artifacts = verify_artifacts(root, args)
            if current_artifacts != artifacts:
                raise GateError("R4W1-C2 artifact contract changed before consumption")
            current_policy = verify_policy_draft(root)
            if current_policy != policy or policy_clause(root) != clause:
                raise GateError("R4W1-C2 live policy changed before consumption")
            current_connected = reopen_connected_evidence(root, artifacts, clause)
            if current_connected != connected_evidence:
                raise GateError("R4W1-C2 connected evidence changed before consumption")
            consumed = consume_exception(
                root,
                run_dir,
                artifacts,
                connected_evidence,
                policy,
                clause,
                baseline,
                usb_binding,
                timeline[0]["timestamp_utc"],
            )
        except (GateError, connected.GateError, core.LiveCoreError, OSError) as exc:
            return _finish(
                root,
                run_dir,
                timeline_path,
                timeline,
                result,
                verdict="FAIL_R4W1C2_PRECONSUMPTION_NO_CANDIDATE_FLASH",
                rc=1,
                result_name="result-live.json",
                error=str(exc),
            )
        append_timeline_event(
            timeline_path,
            timeline,
            "candidate_flash_start",
            timestamp_utc=consumed["consumed_at_utc"],
        )
        result["consumed_state"] = consumed
        result["candidate_transfer_attempted"] = True
        create_phase(
            run_dir,
            "candidate_transfer_started",
            {
                "ticket": _ticket_payload(ticket),
                "usb": candidate_usb,
                "candidate_ap_sha256": connected.EXPECTED_CANDIDATE_AP_SHA256,
            },
            lease=lease,
        )
        try:
            def candidate_revalidation() -> tuple[str, dict[str, Any]]:
                nonlocal sequence
                device, sequence, record = revalidate_ticket(
                    odin, run_dir, ticket, sequence=sequence, lease=lease
                )
                return device, {
                    "endpoint": record,
                    "usb": require_ticket_usb_binding(ticket, usb_binding),
                }

            transfer, revalidation = flash_sealed_exact(
                odin_fd,
                resolve(root, args.candidate_ap),
                ap_size=connected.EXPECTED_CANDIDATE_AP_SIZE,
                ap_sha256=connected.EXPECTED_CANDIDATE_AP_SHA256,
                label="r4w1c-candidate",
                log_path=run_dir / "odin-candidate.json",
                revalidate=candidate_revalidation,
            )
            result["candidate_transfer_ok"] = True
            transfer_error = None
        except (
            GateError,
            odin_core.OdinTransitionError,
            transport.GateError,
            OSError,
            subprocess.SubprocessError,
        ) as exc:
            revalidation = None
            transfer_error = str(exc)
            result["candidate_transfer_error"] = transfer_error
        create_phase(
            run_dir,
            "candidate_transfer_finished",
            {
                "ok": result["candidate_transfer_ok"],
                "error": transfer_error,
                "revalidation": revalidation,
                "transfer": transfer if transfer_error is None else None,
            },
            lease=lease,
        )
        append_timeline_event(
            timeline_path,
            timeline,
            "candidate_flash_done",
            timestamp_utc=phase_timestamp(run_dir, "candidate_transfer_finished"),
        )

        observation: dict[str, Any]
        if result["candidate_transfer_ok"]:
            try:
                absence = odin_core.wait_for_no_live_endpoint(
                    odin,
                    run_dir,
                    timeout_sec=args.disconnect_wait_sec,
                    sequence_start=sequence,
                    poll_sec=1.0,
                    lease=lease,
                    endpoint_observer_factory=odin_core.measured_usbfs_observer,
                )
                sequence = absence.next_sequence
                if not absence.absent or absence.timed_out:
                    raise GateError("candidate Odin endpoint did not disappear")
                observation = observe_candidate(args.park_wait_sec)
                observation["odin_disconnected"] = True
            except (GateError, odin_core.OdinTransitionError, OSError) as exc:
                observation = {
                    "bounded": True,
                    "odin_disconnected": False,
                    "error": str(exc),
                    "watchdog_survival_directly_proven": False,
                }
        else:
            observation = {
                "bounded": True,
                "meaning": "candidate transfer failed; no passive observation proof",
                "watchdog_survival_directly_proven": False,
            }
        observation["candidate_transfer_ok"] = result["candidate_transfer_ok"]
        result["candidate_observation"] = observation
        create_phase(
            run_dir,
            "candidate_observation_closed",
            observation,
            lease=lease,
        )
        if (
            observation.get("candidate_transfer_ok") is True
            and observation.get("odin_disconnected") is True
            and observation.get("full_window_completed") is True
        ):
            append_timeline_event(
                timeline_path,
                timeline,
                "candidate_boot_ready",
                timestamp_utc=phase_timestamp(run_dir, "candidate_observation_closed"),
            )
        core.durable_create_json(run_dir / "live-progress.json", result)
        print(
            "Candidate observation is closed. Physically leave any RDX screen and "
            "enter normal Samsung Download mode for mandatory rollback.",
            flush=True,
        )
        return _rollback_sequence(
            root,
            args,
            run_dir,
            timeline_path,
            timeline,
            result,
            odin,
            odin_fd,
            sequence=sequence,
            lease=lease,
            attempt=0,
            result_name="result-live.json",
        )


def live_run(
    root: Path,
    args: argparse.Namespace,
    artifacts: dict[str, Any],
    policy: dict[str, Any],
) -> int:
    with pinned_odin_session(resolve(root, args.odin)) as (odin_fd, odin):
        return _live_run_with_odin(
            root, args, artifacts, policy, odin, odin_fd
        )


def rollback_from_download(
    root: Path,
    args: argparse.Namespace,
    artifacts: dict[str, Any],
    policy: dict[str, Any],
) -> int:
    if args.ack != ROLLBACK_ACK_TOKEN:
        raise GateError("R4W1-C2 rollback acknowledgement mismatch")
    if not policy_active(root) or policy.get("active") is not True:
        raise GateError("R4W1-C2 recovery requires the exact ACTIVE live policy")
    clause = policy_clause(root)
    consumed, run_dir, connected_evidence = require_consumed(
        root, artifacts, policy, clause
    )
    require_no_stock_cleanup_taint(run_dir)
    if consumed["artifact_target"] != artifacts["target"]:
        raise GateError("R4W1-C2 recovery artifact target mismatch")
    if phase_payload(root, run_dir, "classified") is not None:
        raise GateError("R4W1-C2 transaction is already classified")
    with pinned_odin_session(resolve(root, args.odin)) as (
        odin_fd,
        odin,
    ), odin_core.transaction_session(run_dir) as lease:
        attempt, timeline_path, result_path = next_recovery_attempt(root, run_dir)
        timeline = recovery_timeline_seed(root, consumed, run_dir)
        core.durable_create_json(timeline_path, {"events": timeline})
        state = candidate_state(root, run_dir)
        result: dict[str, Any] = {
            "schema": SCHEMA,
            "mode": "rollback-from-download",
            "recovery_attempt": attempt,
            "target": TARGET,
            "artifacts": artifacts,
            "consumed_state": consumed,
            "connected_evidence": connected_evidence["binding"],
            "usb_binding": consumed["usb_binding"],
            "android_serial": consumed["android_serial"],
            "physical_continuity_basis": PHYSICAL_CONTINUITY_BASIS,
            **state,
            "verdict": "INCOMPLETE",
        }
        normalize_recovery_prefix(run_dir, lease=lease)
        result.update(candidate_state(root, run_dir))
        sequence = next_snapshot_sequence(run_dir)
        return _rollback_sequence(
            root,
            args,
            run_dir,
            timeline_path,
            timeline,
            result,
            odin,
            odin_fd,
            sequence=sequence,
            lease=lease,
            attempt=attempt,
            result_name=result_path.name,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--live", action="store_true")
    modes.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    parser.add_argument("--candidate-boot", type=Path, default=connected.DEFAULT_CANDIDATE_BOOT)
    parser.add_argument("--candidate-lz4", type=Path, default=connected.DEFAULT_CANDIDATE_LZ4)
    parser.add_argument("--candidate-ap", type=Path, default=connected.DEFAULT_CANDIDATE_AP)
    parser.add_argument("--manifest", type=Path, default=connected.DEFAULT_MANIFEST)
    parser.add_argument("--static-result", type=Path, default=connected.DEFAULT_STATIC_RESULT)
    parser.add_argument("--magisk-ap", type=Path, default=connected.DEFAULT_MAGISK_AP)
    parser.add_argument("--stock-ap", type=Path, default=connected.DEFAULT_STOCK_AP)
    parser.add_argument("--full-firmware", type=Path, default=connected.DEFAULT_FULL_FIRMWARE)
    parser.add_argument("--odin", type=Path, default=connected.DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--odin-absence-wait-sec", type=float, default=15.0)
    parser.add_argument("--candidate-endpoint-wait-sec", type=float, default=120.0)
    parser.add_argument("--disconnect-wait-sec", type=float, default=45.0)
    parser.add_argument("--park-wait-sec", type=float, default=DEFAULT_PARK_WAIT_SEC)
    parser.add_argument("--rollback-endpoint-wait-sec", type=float, default=180.0)
    parser.add_argument("--confirmation-wait-sec", type=float, default=120.0)
    parser.add_argument("--android-wait-sec", type=float, default=300.0)
    parser.add_argument("--ambiguous-android-probe-sec", type=float, default=45.0)
    parser.add_argument("--ambiguous-rollback-ack")
    return parser


def validate_runtime_args(args: argparse.Namespace) -> None:
    bounds = (
        ("Odin absence", args.odin_absence_wait_sec, 0.1, 30.0),
        ("candidate endpoint", args.candidate_endpoint_wait_sec, 1.0, 300.0),
        ("disconnect", args.disconnect_wait_sec, 1.0, 120.0),
        ("park", args.park_wait_sec, DEFAULT_PARK_WAIT_SEC, DEFAULT_PARK_WAIT_SEC),
        ("rollback endpoint", args.rollback_endpoint_wait_sec, 1.0, 300.0),
        ("confirmation", args.confirmation_wait_sec, 1.0, 300.0),
        ("Android", args.android_wait_sec, 1.0, 600.0),
        ("ambiguous Android probe", args.ambiguous_android_probe_sec, 5.0, 120.0),
    )
    for label, value, minimum, maximum in bounds:
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise GateError(f"{label} wait must be between {minimum} and {maximum}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        validate_runtime_args(args)
        artifacts = verify_artifacts(root, args)
        policy = verify_policy_draft(root)
        if args.offline_check:
            print(
                json.dumps(
                    {
                        "schema": SCHEMA,
                        "mode": "offline-check",
                        "target": TARGET,
                        "artifacts": artifacts,
                        "policy": policy,
                        "connected_pass_present": (root / connected.PASS_STATE).is_file(),
                        "candidate_consumed": (root / CONSUMED_STATE).exists(),
                        "device_contact": False,
                        "device_writes": False,
                        "reboot": False,
                        "download_transition": False,
                        "odin_transfer": False,
                        "flash": False,
                        "verdict": "PASS_R4W1C2_LIVE_GATE_OFFLINE_CHECK",
                    },
                    indent=2,
                )
            )
            return 0
        if args.live:
            return live_run(root, args, artifacts, policy)
        return rollback_from_download(root, args, artifacts, policy)
    except (
        GateError,
        connected.GateError,
        core.LiveCoreError,
        odin_core.OdinTransitionError,
        transport.GateError,
        OSError,
        subprocess.SubprocessError,
        tarfile.TarError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
