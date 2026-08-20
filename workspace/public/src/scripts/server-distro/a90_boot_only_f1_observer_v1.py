#!/usr/bin/env python3
"""Exact A90 native-resident preflight/final-health observation contract.

Receipt validation stays pure.  ``probe_bridge_identity`` is the read-only
host producer for the bridge identity receipt; it is not called by an H0 CLI
path.  The live owner remains disabled until the owner-controlled bridge and
command producers are completed and independently reviewed.
"""

from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_boot_only_f1_contract_v1 import (
    ContractError,
    canonical_json,
    require_int,
    require_object,
    require_sha,
    require_string,
    sha256_bytes,
)


OBSERVER_SCHEMA = "a90-boot-only-f1-observer-input-v1"
FIXED_BRIDGE_DEVICE = (
    "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
)
BRIDGE_KEYS = frozenset(
    {
        "selectedDevice",
        "selectedRealpath",
        "usbVendor",
        "usbProduct",
        "bridgeProcessPid",
        "bridgeProcessStartTicks",
        "listenerSocketInode",
        "otherTargetsPresent",
        "receiptSha256",
    }
)
COMMAND_KEYS = frozenset({"command", "rc", "status", "text", "receiptSha256"})
INPUT_KEYS = frozenset({"schema", "bridge", "version", "selftest", "status", "bootId"})
TTY_RE = re.compile(r"^/dev/ttyACM[0-9]+$")
BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
VERSION_RE = re.compile(r"^version: (?P<version>\S+) build=(?P<build>\S+)$")
SELFTEST_RE = re.compile(
    r"^selftest: pass=(?P<pass>[0-9]+) warn=(?P<warn>[0-9]+) "
    r"fail=0 duration=(?P<duration>[0-9]+)ms entries=(?P<entries>[1-9][0-9]*)$"
)
REPO_ROOT = Path(__file__).resolve().parents[5]
BRIDGE_SCRIPT = (
    REPO_ROOT / "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py"
)
PYTHON_EXECUTABLE = Path("/usr/bin/python3.14")


@dataclass(frozen=True)
class ObservedHealth:
    target_evidence_sha256: str
    boot_id: str
    version: str
    build: str
    boot_identity_sha256: str
    device_safety_state: str
    recovery_available: bool
    other_targets_untouched: bool
    receipt_sha256: str


def _receipt_sha(value: dict[str, Any]) -> str:
    return sha256_bytes(
        canonical_json({key: value[key] for key in sorted(value) if key != "receiptSha256"})
    )


def command_receipt(command: list[str], result: Any) -> dict[str, Any]:
    if (
        type(command) is not list
        or not command
        or any(type(item) is not str or not item for item in command)
    ):
        raise ContractError("observer command is not one fixed argv")
    value = {
        "command": command,
        "rc": getattr(result, "rc", None),
        "status": getattr(result, "status", None),
        "text": getattr(result, "text", None),
    }
    value["receiptSha256"] = _receipt_sha(value)
    return value


def _validate_command(
    value: Any, expected_command: list[str], label: str
) -> dict[str, Any]:
    receipt = require_object(value, COMMAND_KEYS, label)
    if (
        receipt["command"] != expected_command
        or receipt["rc"] != 0
        or type(receipt["rc"]) is not int
        or receipt["status"] != "ok"
        or type(receipt["text"]) is not str
        or not receipt["text"]
        or receipt["receiptSha256"] != _receipt_sha(receipt)
    ):
        raise ContractError(f"{label} is not one exact successful cmdv1 receipt")
    return receipt


def _validate_bridge(value: Any) -> dict[str, Any]:
    bridge = require_object(value, BRIDGE_KEYS, "observer bridge")
    if (
        bridge["selectedDevice"] != FIXED_BRIDGE_DEVICE
        or type(bridge["selectedRealpath"]) is not str
        or TTY_RE.fullmatch(bridge["selectedRealpath"]) is None
        or bridge["usbVendor"] != "04e8"
        or bridge["usbProduct"] != "6861"
        or bridge["otherTargetsPresent"] != 0
        or type(bridge["otherTargetsPresent"]) is not int
        or bridge["receiptSha256"] != _receipt_sha(bridge)
    ):
        raise ContractError("observer bridge identity mismatch")
    require_int(
        bridge["bridgeProcessPid"],
        "observer bridge process PID",
        minimum=1,
        maximum=(1 << 31) - 1,
    )
    require_int(
        bridge["bridgeProcessStartTicks"],
        "observer bridge process start ticks",
        minimum=1,
        maximum=(1 << 63) - 1,
    )
    require_int(
        bridge["listenerSocketInode"],
        "observer listener socket inode",
        minimum=1,
        maximum=(1 << 63) - 1,
    )
    return bridge


def _read_ascii(path: Path) -> str:
    try:
        return path.read_text(encoding="ascii", errors="strict").strip()
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"observer cannot read {path}") from exc


def _usb_parent(path: Path) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ContractError("observer tty sysfs path is absent") from exc
    for candidate in (resolved, *resolved.parents):
        if (candidate / "idVendor").is_file() and (candidate / "idProduct").is_file():
            return candidate
    raise ContractError("observer tty has no USB device parent")


def _process_start_ticks(stat_text: str) -> int:
    end = stat_text.rfind(")")
    fields = stat_text[end + 2 :].split() if end >= 0 else []
    if len(fields) < 20:
        raise ContractError("observer bridge process stat is malformed")
    try:
        return int(fields[19], 10)
    except ValueError as exc:
        raise ContractError("observer bridge process start ticks are malformed") from exc


def _listener_inodes(proc_net_tcp: Path) -> list[int]:
    matches: list[int] = []
    for line in _read_ascii(proc_net_tcp).splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 10 and fields[1] == "0100007F:D431" and fields[3] == "0A":
            try:
                matches.append(int(fields[9], 10))
            except ValueError as exc:
                raise ContractError("observer listener inode is malformed") from exc
    if any(inode <= 0 for inode in matches):
        raise ContractError("observer listener inode is invalid")
    return matches


def _listener_inode(proc_net_tcp: Path) -> int:
    matches = _listener_inodes(proc_net_tcp)
    if len(matches) != 1:
        raise ContractError("observer requires one exact loopback listener")
    return matches[0]


def prove_listener_absent(proc_root: Path = Path("/proc")) -> None:
    if _listener_inodes(proc_root / "net/tcp"):
        raise ContractError("A90 bridge listener already exists")


def probe_endpoint_identity(
    *,
    serial_root: Path = Path("/dev/serial/by-id"),
    sys_class_tty: Path = Path("/sys/class/tty"),
    sys_usb_devices: Path = Path("/sys/bus/usb/devices"),
) -> dict[str, Any]:
    """Bind the sole A90 ACM endpoint before an owner starts its bridge.

    The function is read-only.  It is not called by any H0 CLI path.
    """

    selected = serial_root / Path(FIXED_BRIDGE_DEVICE).name
    try:
        link_metadata = selected.lstat()
        realpath = selected.resolve(strict=True)
        tty_metadata = realpath.stat()
    except OSError as exc:
        raise ContractError("fixed A90 bridge endpoint is absent") from exc
    if (
        not stat.S_ISLNK(link_metadata.st_mode)
        or TTY_RE.fullmatch(str(realpath)) is None
        or not stat.S_ISCHR(tty_metadata.st_mode)
    ):
        raise ContractError("fixed A90 bridge endpoint identity mismatch")
    usb_parent = _usb_parent(sys_class_tty / realpath.name / "device")
    vendor = _read_ascii(usb_parent / "idVendor").lower()
    product = _read_ascii(usb_parent / "idProduct").lower()
    if (vendor, product) != ("04e8", "6861"):
        raise ContractError("fixed A90 USB identity mismatch")

    serial_entries = list(serial_root.iterdir())
    other_serial = sum(entry.name != selected.name for entry in serial_entries)
    samsung_parents: set[Path] = set()
    for entry in sys_usb_devices.iterdir():
        if (entry / "idVendor").is_file() and _read_ascii(entry / "idVendor").lower() == "04e8":
            samsung_parents.add(entry.resolve(strict=True))
    other_usb = sum(parent != usb_parent for parent in samsung_parents)
    other_targets = other_serial + other_usb
    if other_targets != 0:
        raise ContractError("observer endpoint inventory is ambiguous")
    return {
        "selectedDevice": FIXED_BRIDGE_DEVICE,
        "selectedRealpath": str(realpath),
        "usbVendor": vendor,
        "usbProduct": product,
        "otherTargetsPresent": other_targets,
    }


def _fd_holders(proc_root: Path, targets: set[str]) -> dict[str, set[int]]:
    holders = {target: set() for target in targets}
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            descriptors = list((entry / "fd").iterdir())
        except OSError:
            continue
        for descriptor in descriptors:
            try:
                target = os.readlink(descriptor)
            except OSError:
                continue
            if target in holders:
                holders[target].add(int(entry.name, 10))
    return holders


def probe_bridge_identity(
    endpoint: Any,
    *,
    expected_pid: int,
    expected_command: tuple[str, ...],
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    """Bind an owner-created exact-FD bridge process after it becomes ready."""

    require_int(
        expected_pid,
        "expected bridge PID",
        minimum=1,
        maximum=(1 << 31) - 1,
    )
    if (
        type(endpoint) is not dict
        or set(endpoint)
        != {
            "selectedDevice",
            "selectedRealpath",
            "usbVendor",
            "usbProduct",
            "otherTargetsPresent",
        }
        or type(expected_command) is not tuple
        or not expected_command
        or any(type(part) is not str or not part for part in expected_command)
    ):
        raise ContractError("owned bridge probe inputs are malformed")
    if endpoint["otherTargetsPresent"] != 0 or type(endpoint["otherTargetsPresent"]) is not int:
        raise ContractError("owned bridge endpoint is ambiguous")

    entry = proc_root / str(expected_pid)
    try:
        raw_cmdline = (entry / "cmdline").read_bytes()
        if not raw_cmdline.endswith(b"\0"):
            raise ContractError("owned bridge cmdline framing mismatch")
        command = tuple(
            part.decode("ascii") for part in raw_cmdline.split(b"\0") if part
        )
        executable = (entry / "exe").resolve(strict=True)
        start_ticks = _process_start_ticks(_read_ascii(entry / "stat"))
    except (OSError, UnicodeError) as exc:
        raise ContractError("owned bridge process identity is unavailable") from exc
    if command != expected_command or executable != PYTHON_EXECUTABLE:
        raise ContractError("owned bridge process execution identity mismatch")

    listener_inode = _listener_inode(proc_root / "net/tcp")
    socket_target = f"socket:[{listener_inode}]"
    tty_target = endpoint["selectedRealpath"]
    holders = _fd_holders(proc_root, {socket_target, tty_target})
    if holders != {socket_target: {expected_pid}, tty_target: {expected_pid}}:
        raise ContractError("owned bridge listener or TTY ownership mismatch")
    value = {
        **endpoint,
        "bridgeProcessPid": expected_pid,
        "bridgeProcessStartTicks": start_ticks,
        "listenerSocketInode": listener_inode,
    }
    value["receiptSha256"] = _receipt_sha(value)
    return _validate_bridge(value)


def prove_bridge_absent(
    *,
    pid: int,
    listener_inode: int,
    selected_realpath: str,
    proc_root: Path = Path("/proc"),
) -> None:
    """Require process, listener, and TTY ownership to be absent after reap."""

    require_int(pid, "retired bridge PID", minimum=1, maximum=(1 << 31) - 1)
    require_int(
        listener_inode,
        "retired bridge listener inode",
        minimum=1,
        maximum=(1 << 63) - 1,
    )
    if (proc_root / str(pid)).exists():
        raise ContractError("owned bridge process survived reap")
    if listener_inode in _listener_inodes(proc_root / "net/tcp"):
        raise ContractError("owned bridge listener survived reap")
    targets = {f"socket:[{listener_inode}]", selected_realpath}
    if any(_fd_holders(proc_root, targets).values()):
        raise ContractError("owned bridge FD survived reap")


def _unique_matching_line(text: str, pattern: re.Pattern[str], label: str) -> re.Match[str]:
    matches = [pattern.fullmatch(line.strip()) for line in text.replace("\r", "").splitlines()]
    exact = [match for match in matches if match is not None]
    if len(exact) != 1:
        raise ContractError(f"{label} fact is not unique")
    return exact[0]


def _identity_binding_sha256(expected: Any) -> str:
    if type(expected) is not dict:
        raise ContractError("observer expected identity is not an object")
    require_string(expected.get("version"), "observer expected version")
    require_string(expected.get("build"), "observer expected build")
    candidates = [
        expected.get("residentQualificationSha256"),
        expected.get("sha256"),
    ]
    present = [value for value in candidates if value is not None]
    if len(present) != 1:
        raise ContractError("observer expected identity binding is ambiguous")
    return require_sha(present[0], "observer expected identity binding SHA256")


def validate_observation_input(
    value: Any,
    expected: dict[str, Any],
    *,
    recovery_available: bool,
) -> ObservedHealth:
    identity_binding_sha256 = _identity_binding_sha256(expected)
    observed = require_object(value, INPUT_KEYS, "observer input")
    if observed["schema"] != OBSERVER_SCHEMA:
        raise ContractError("observer schema mismatch")
    bridge = _validate_bridge(observed["bridge"])
    version = _validate_command(observed["version"], ["version"], "version receipt")
    selftest = _validate_command(observed["selftest"], ["selftest"], "selftest receipt")
    status = _validate_command(observed["status"], ["status"], "status receipt")
    boot_id_receipt = _validate_command(
        observed["bootId"],
        ["cat", "/proc/sys/kernel/random/boot_id"],
        "boot ID receipt",
    )
    version_match = _unique_matching_line(version["text"], VERSION_RE, "version")
    selftest_match = _unique_matching_line(selftest["text"], SELFTEST_RE, "selftest")
    if (
        (version_match.group("version"), version_match.group("build"))
        != (expected["version"], expected["build"])
        or int(selftest_match.group("entries"), 10) < 1
    ):
        raise ContractError("observed resident identity or selftest mismatch")
    pstore_lines = [
        line.strip()
        for line in status["text"].replace("\r", "").splitlines()
        if line.strip().startswith("pstore=")
    ]
    if (
        len(pstore_lines) != 1
        or pstore_lines[0].split().count("entries=0") != 1
        or any(
            token.startswith("entries=") and token != "entries=0"
            for token in pstore_lines[0].split()
        )
    ):
        raise ContractError("observed pstore health is not exact zero")
    boot_ids = [
        line.strip()
        for line in boot_id_receipt["text"].replace("\r", "").splitlines()
        if BOOT_ID_RE.fullmatch(line.strip()) is not None
    ]
    if len(boot_ids) != 1:
        raise ContractError("current native boot ID is not unique")
    if recovery_available is not True:
        raise ContractError("physical recovery qualification is absent")
    receipt_hashes = {
        name: observed[name]["receiptSha256"]
        for name in ("version", "selftest", "status", "bootId")
    }
    target_evidence = {
        "bridgeReceiptSha256": bridge["receiptSha256"],
        "bootIdSha256": sha256_bytes(boot_ids[0].encode("ascii")),
        "commandReceiptSha256": receipt_hashes,
    }
    boot_identity = {
        "version": expected["version"],
        "build": expected["build"],
        "bootIdSha256": target_evidence["bootIdSha256"],
    }
    complete = {
        "schema": OBSERVER_SCHEMA,
        "targetEvidence": target_evidence,
        "bootIdentity": boot_identity,
        "identityBindingSha256": identity_binding_sha256,
        "deviceSafetyState": "RESIDENT_HEALTHY",
        "recoveryAvailable": True,
        "otherTargetsUntouched": True,
    }
    return ObservedHealth(
        target_evidence_sha256=sha256_bytes(canonical_json(target_evidence)),
        boot_id=boot_ids[0],
        version=expected["version"],
        build=expected["build"],
        boot_identity_sha256=sha256_bytes(canonical_json(boot_identity)),
        device_safety_state="RESIDENT_HEALTHY",
        recovery_available=True,
        other_targets_untouched=True,
        receipt_sha256=sha256_bytes(canonical_json(complete)),
    )
