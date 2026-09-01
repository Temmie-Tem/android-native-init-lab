#!/usr/bin/env python3
"""Exact attended read-only S20+ TWRP boot-partition identity audit.

The connected lane is dormant until a reviewed target-contract activation.
It reads only fixed symlink, inode, and sysfs metadata.  It never opens the
boot block, reads partition bytes, stages a payload, writes, or reboots.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable, Sequence

import s20plus_g986n_d0_inventory as base
import s20plus_g986n_twrp_t2_f2 as t2


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
VERSION = "s20plus-g986n-twrp-boot-identity-d0-v1"
SCHEMA = "s20plus_g986n_twrp_boot_identity_d0_result_v1"
PLAN_SCHEMA = "s20plus_g986n_twrp_boot_identity_d0_plan_v1"
ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE = True
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "abd40c644e5bbbac8da743bee8e94e427730dca252bfadcbf39f6beb71b7bdfb"

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

ADB = base.EXPECTED_ADB_REALPATH
ADB_SIZE = 716_968
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-twrp-boot-identity-d0"
T2_RUN = (
    ROOT
    / "workspace/private/runs/s20plus-g986n-twrp-t2-f2/"
    "run-1788244623738402681"
)
T2_TERMINAL = T2_RUN / "terminal.json"
T2_TERMINAL_SIZE = 1_911
T2_TERMINAL_SHA256 = (
    "da24acd3b33c78f4ed41565858e5314bb2c3a1acaf020ac06fb83fd99ab84d05"
)

SOURCE_CLOSURE = {
    "d0_inventory": {
        "path": Path(base.__file__).resolve(),
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    },
    "t2_owner": {
        "path": Path(t2.__file__).resolve(),
        "size": 167_684,
        "sha256": "7f5519ef76091f491165a0be5ce81733f0343318057d02f7577954db1d1a0d11",
    },
    "t2_profile": {
        "path": Path(t2.h0.__file__).resolve(),
        "size": 12_847,
        "sha256": "c02b78f2a1215a1fc2104a4634264609d2060d610bc628a068b318cb1cf55fb7",
    },
}

BOOT_LINK = "/dev/block/bootdevice/by-name/boot"
EXPECTED_BOOT_SIZE = 67_108_864
EXPECTED_SECTORS_512 = EXPECTED_BOOT_SIZE // 512
MAX_COMMAND_BYTES = 16 * 1024
COMMAND_TIMEOUT_SECONDS = 30
HEX64_RE = re.compile(r"[0-9a-f]{64}")
DIRECT_PATH_RE = re.compile(r"/dev/block/[A-Za-z0-9._-]{1,64}")
DEVNAME_RE = re.compile(r"[A-Za-z0-9._-]{1,64}")
DECIMAL_RE = re.compile(r"0|[1-9][0-9]{0,15}")
RUN_NAME_RE = re.compile(r"run-[0-9]{19}")

BOOT_METADATA_KEYS = (
    "boot_link",
    "direct_path",
    "rdev_major",
    "rdev_minor",
    "sysfs_dev",
    "devname",
    "devtype",
    "partname",
    "partition_number",
    "sectors_512",
    "size_bytes",
    "node_is_block",
    "block_device_open_count",
    "partition_content_bytes_read",
)

BOOT_METADATA_SCRIPT = r"""set -eu
boot_link=/dev/block/bootdevice/by-name/boot
[ -L "$boot_link" ] || exit 91
direct_path=$(/system/bin/readlink -f "$boot_link")
case "$direct_path" in
    /dev/block/*) ;;
    *) exit 92 ;;
esac
[ -b "$direct_path" ] || exit 93
major_hex=$(/system/bin/stat -c %t "$direct_path")
minor_hex=$(/system/bin/stat -c %T "$direct_path")
major=$((0x$major_hex))
minor=$((0x$minor_hex))
sysdev=/sys/dev/block/$major:$minor
[ -L "$sysdev" ] || exit 94
[ -f "$sysdev/uevent" ] || exit 95
[ -f "$sysdev/dev" ] || exit 96
[ -f "$sysdev/partition" ] || exit 97
[ -f "$sysdev/size" ] || exit 98
uevent_value() {
    /system/bin/awk -F= -v wanted="$1" '
        $1 == wanted { count += 1; value = $2 }
        END { if (count != 1 || value == "") exit 1; print value }
    ' "$sysdev/uevent"
}
uevent_major=$(uevent_value MAJOR)
uevent_minor=$(uevent_value MINOR)
devname=$(uevent_value DEVNAME)
devtype=$(uevent_value DEVTYPE)
partname=$(uevent_value PARTNAME)
uevent_partn=$(uevent_value PARTN)
sysfs_dev=$(/system/bin/cat "$sysdev/dev")
partition_number=$(/system/bin/cat "$sysdev/partition")
sectors_512=$(/system/bin/cat "$sysdev/size")
size_bytes=$((sectors_512 * 512))
[ "$uevent_major" = "$major" ] || exit 99
[ "$uevent_minor" = "$minor" ] || exit 100
[ "$sysfs_dev" = "$major:$minor" ] || exit 101
[ "$devname" = "${direct_path##*/}" ] || exit 102
[ "$devtype" = partition ] || exit 103
[ "$partname" = boot ] || exit 104
[ "$uevent_partn" = "$partition_number" ] || exit 105
printf '%s\n' \
    "boot_link=$boot_link" \
    "direct_path=$direct_path" \
    "rdev_major=$major" \
    "rdev_minor=$minor" \
    "sysfs_dev=$sysfs_dev" \
    "devname=$devname" \
    "devtype=$devtype" \
    "partname=$partname" \
    "partition_number=$partition_number" \
    "sectors_512=$sectors_512" \
    "size_bytes=$size_bytes" \
    "node_is_block=1" \
    "block_device_open_count=0" \
    "partition_content_bytes_read=0"
"""


class AuditError(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256_bytes(canonical(value))


def read_exact_regular(
    path: Path,
    *,
    expected_size: int | None,
    expected_sha256: str | None,
    maximum: int,
    label: str,
) -> bytes:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > maximum
            or (expected_size is not None and before.st_size != expected_size)
        ):
            raise AuditError(f"{label} identity differs")
        payload = bytearray()
        while len(payload) < before.st_size:
            chunk = os.read(descriptor, min(1024 * 1024, before.st_size - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) != before.st_size or os.read(descriptor, 1):
            raise AuditError(f"{label} length differs")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ) != (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ):
        raise AuditError(f"{label} changed while read")
    data = bytes(payload)
    if expected_sha256 is not None and sha256_bytes(data) != expected_sha256:
        raise AuditError(f"{label} hash differs")
    return data


def file_receipt(
    path: Path,
    *,
    expected_size: int | None = None,
    expected_sha256: str | None = None,
    maximum: int = 1024 * 1024,
    label: str,
) -> dict[str, Any]:
    data = read_exact_regular(
        path,
        expected_size=expected_size,
        expected_sha256=expected_sha256,
        maximum=maximum,
        label=label,
    )
    return {"path": str(path), "size": len(data), "sha256": sha256_bytes(data)}


def normalized_self_sha256() -> str:
    source = read_exact_regular(
        SCRIPT,
        expected_size=None,
        expected_sha256=None,
        maximum=128 * 1024,
        label="TWRP boot identity D0 runner",
    )
    source, active_count = re.subn(
        rb"^ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE = (?:False|True)$",
        b"ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        source,
        count=1,
        flags=re.MULTILINE,
    )
    source, reviewed_count = re.subn(
        rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = ".*"$',
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "<REVIEWED_NORMALIZED_SHA256>"',
        source,
        count=1,
        flags=re.MULTILINE,
    )
    if active_count != 1 or reviewed_count != 1:
        raise AuditError("runner activation normalization differs")
    return sha256_bytes(source)


def validate_t2_predecessor() -> dict[str, Any]:
    if os.path.lexists(t2.SHARED_GUARD):
        raise AuditError("shared S20+ action guard is held")
    try:
        t2.source_closure(enforce_self=True)
        run_dir = t2.resolve_run(T2_RUN.name)
        prepared = t2.read_prepared(
            run_dir, require_unexpired=False, require_current_guard=False
        )
        actual = t2.validate_journal(run_dir, prepared)
        terminal = t2._validate_terminal(run_dir, prepared, actual)
        current_host = t2.validate_host_closure(
            enforce_self=True,
            expected_serial_sha256=terminal["recovery_observation"]["serial_sha256"],
        )
    except Exception as exc:
        raise AuditError("retained T2 predecessor validation failed") from exc
    terminal_receipt = file_receipt(
        T2_TERMINAL,
        expected_size=T2_TERMINAL_SIZE,
        expected_sha256=T2_TERMINAL_SHA256,
        maximum=4 * 1024,
        label="retained T2 terminal",
    )
    observation = terminal.get("recovery_observation")
    if (
        terminal.get("verdict") != "PROVED_T2_RECOVERY_RETAINED"
        or terminal.get("candidate_replay_permitted") is not False
        or terminal.get("candidate_retained") is not True
        or type(observation) is not dict
        or observation.get("claim_verdict") != "PROVED"
    ):
        raise AuditError("retained T2 predecessor semantics differ")
    serial_sha256 = observation.get("serial_sha256")
    topology_sha256 = observation.get("topology_sha256")
    boot_id_sha256 = observation.get("boot_id_sha256")
    if any(
        type(value) is not str or HEX64_RE.fullmatch(value) is None
        for value in (serial_sha256, topology_sha256, boot_id_sha256)
    ):
        raise AuditError("retained T2 predecessor identity differs")
    if os.path.lexists(t2.SHARED_GUARD):
        raise AuditError("shared S20+ action guard appeared during validation")
    return {
        "terminal": terminal_receipt,
        "serial_sha256": serial_sha256,
        "topology_sha256": topology_sha256,
        "boot_id_sha256": boot_id_sha256,
        "journal_node_count": len(actual),
        "host_closure_sha256": digest(current_host),
        "candidate_consumed": True,
        "t2_transfer_authority_inherited": False,
    }


def validate_host_closure(*, enforce_self: bool) -> dict[str, Any]:
    sources: dict[str, Any] = {}
    for name, expected in SOURCE_CLOSURE.items():
        sources[name] = file_receipt(
            expected["path"],
            expected_size=expected["size"],
            expected_sha256=expected["sha256"],
            label=f"{name} source",
        )
    adb = base.tool_receipt(base.DEFAULT_ADB)
    if (
        adb.get("path") != str(ADB)
        or adb.get("size") != ADB_SIZE
        or adb.get("sha256") != ADB_SHA256
    ):
        raise AuditError("ADB tool identity differs")
    normalized = normalized_self_sha256()
    if enforce_self and normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise AuditError("runner normalized identity is not reviewed")
    return {
        "sources": sources,
        "adb": adb,
        "runner": file_receipt(SCRIPT, label="current D0 runner", maximum=128 * 1024),
        "runner_normalized_sha256": normalized,
        "remote_scripts": {
            "t2_identity": {
                "size": len(t2.h0.RECOVERY_SHELL_ARGUMENT.encode()),
                "sha256": sha256_text(t2.h0.RECOVERY_SHELL_ARGUMENT),
            },
            "boot_metadata": {
                "size": len(BOOT_METADATA_SCRIPT.encode()),
                "sha256": sha256_text(BOOT_METADATA_SCRIPT),
            },
        },
        "t2_predecessor": validate_t2_predecessor(),
    }


def decode_output(
    result: tuple[int, bytes, bytes], label: str, *, single_framed: bool
) -> str:
    if type(result) is not tuple or len(result) != 3:
        raise AuditError(f"{label} command envelope differs")
    returncode, stdout, stderr = result
    if (
        type(returncode) is not int
        or type(stdout) is not bytes
        or type(stderr) is not bytes
        or len(stdout) + len(stderr) > MAX_COMMAND_BYTES
        or returncode != 0
        or stderr
    ):
        raise AuditError(f"{label} command failed or exceeded bounds")
    try:
        text = stdout.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise AuditError(f"{label} output is not UTF-8") from exc
    if "\r" in text or "\x00" in text:
        raise AuditError(f"{label} output framing differs")
    if single_framed and (not text.endswith("\n") or text.endswith("\n\n")):
        raise AuditError(f"{label} output framing differs")
    return text


def inventory_from_result(result: tuple[int, bytes, bytes], label: str) -> tuple[dict[str, Any], ...]:
    text = decode_output(result, label, single_framed=False)
    try:
        return base.parse_inventory(text.strip())
    except Exception as exc:
        raise AuditError(f"{label} is malformed") from exc


def select_recovery_row(
    rows: tuple[dict[str, Any], ...], expected_serial_sha256: str
) -> dict[str, Any]:
    matches = tuple(
        row
        for row in rows
        if sha256_text(row["serial"]) == expected_serial_sha256
    )
    model_rows = tuple(
        row for row in rows if t2.b0.EXPECTED_ADB_MODEL in row["metadata"]
    )
    if len(matches) != 1 or any(row is not matches[0] for row in model_rows):
        raise AuditError("exact retained S20+ recovery row is absent or ambiguous")
    selected = matches[0]
    if selected["state"] != "recovery":
        raise AuditError("exact retained S20+ row is not in recovery state")
    return selected


def parse_devpath(result: tuple[int, bytes, bytes]) -> str:
    text = decode_output(result, "selected recovery devpath", single_framed=True)
    if text.count("\n") != 1:
        raise AuditError("selected recovery devpath framing differs")
    value = text[:-1]
    if base.DEVPATH_RE.fullmatch(value) is None:
        raise AuditError("selected recovery devpath grammar differs")
    return value


def parse_recovery_identity(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    try:
        return t2.h0.parse_recovery_observation(result)
    except Exception as exc:
        raise AuditError("exact T2 recovery identity differs") from exc


def decimal(value: str, label: str, maximum: int) -> int:
    if DECIMAL_RE.fullmatch(value) is None:
        raise AuditError(f"{label} is malformed")
    parsed = int(value)
    if parsed > maximum:
        raise AuditError(f"{label} exceeds its bound")
    return parsed


def parse_boot_metadata(result: tuple[int, bytes, bytes]) -> dict[str, Any]:
    text = decode_output(result, "boot metadata", single_framed=True)
    lines = text.splitlines()
    if len(lines) != len(BOOT_METADATA_KEYS):
        raise AuditError("boot metadata field count differs")
    values: dict[str, str] = {}
    for key, line in zip(BOOT_METADATA_KEYS, lines, strict=True):
        actual, separator, value = line.partition("=")
        if separator != "=" or actual != key or key in values or not value:
            raise AuditError("boot metadata grammar differs")
        values[key] = value
    direct_path = values["direct_path"]
    devname = values["devname"]
    if (
        values["boot_link"] != BOOT_LINK
        or DIRECT_PATH_RE.fullmatch(direct_path) is None
        or DEVNAME_RE.fullmatch(devname) is None
        or direct_path.rsplit("/", 1)[-1] != devname
        or values["devtype"] != "partition"
        or values["partname"] != "boot"
        or values["node_is_block"] != "1"
        or values["block_device_open_count"] != "0"
        or values["partition_content_bytes_read"] != "0"
    ):
        raise AuditError("boot metadata fixed fields differ")
    major = decimal(values["rdev_major"], "boot rdev major", 1_048_575)
    minor = decimal(values["rdev_minor"], "boot rdev minor", 1_048_575)
    partition = decimal(values["partition_number"], "boot partition number", 4_095)
    sectors = decimal(values["sectors_512"], "boot sector count", 2_097_152)
    size = decimal(values["size_bytes"], "boot size", 1024 * 1024 * 1024)
    if (
        major == 0
        or partition == 0
        or values["sysfs_dev"] != f"{major}:{minor}"
        or sectors != EXPECTED_SECTORS_512
        or size != sectors * 512
        or size != EXPECTED_BOOT_SIZE
    ):
        raise AuditError("boot metadata cross-check differs")
    return {
        "boot_link": BOOT_LINK,
        "direct_path": direct_path,
        "rdev_major": major,
        "rdev_minor": minor,
        "sysfs_dev": values["sysfs_dev"],
        "devname": devname,
        "devtype": "partition",
        "partname": "boot",
        "partition_number": partition,
        "sectors_512": sectors,
        "size_bytes": size,
        "node_is_block": True,
        "block_device_open_count": 0,
        "partition_content_bytes_read": 0,
    }


class CommandRecorder:
    def __init__(self, command: Command):
        self.command = command
        self.argv: list[list[str]] = []

    def run(self, argv: list[str], timeout: float, maximum: int) -> tuple[int, bytes, bytes]:
        self.argv.append(list(argv))
        return self.command(argv, timeout, maximum)

    def counts(self) -> dict[str, int]:
        inventories = sum(argv[1:] == ["devices", "-l"] for argv in self.argv)
        selected = sum(len(argv) >= 3 and argv[1] == "-s" for argv in self.argv)
        return {
            "host_command_count": len(self.argv),
            "inventory_command_count": inventories,
            "selected_target_command_count": selected,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }


def collect(
    command: Command = base.bounded_command,
    *,
    predecessor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    predecessor = predecessor or validate_t2_predecessor()
    recorder = CommandRecorder(command)
    run = recorder.run
    expected_serial_sha256 = predecessor["serial_sha256"]
    expected_topology_sha256 = predecessor["topology_sha256"]

    first_rows = inventory_from_result(
        run([str(ADB), "devices", "-l"], 10, MAX_COMMAND_BYTES),
        "initial ADB inventory",
    )
    selected = select_recovery_row(first_rows, expected_serial_sha256)
    serial = selected["serial"]
    devpath_before = parse_devpath(
        run([str(ADB), "-s", serial, "get-devpath"], 10, MAX_COMMAND_BYTES)
    )
    if sha256_text(devpath_before) != expected_topology_sha256:
        raise AuditError("selected recovery topology differs from retained T2")
    identity_before_raw = run(
        [str(ADB), "-s", serial, "exec-out", "sh", "-c", t2.h0.RECOVERY_SHELL_ARGUMENT],
        COMMAND_TIMEOUT_SECONDS,
        MAX_COMMAND_BYTES,
    )
    identity_before = parse_recovery_identity(identity_before_raw)
    metadata_raw = run(
        [str(ADB), "-s", serial, "exec-out", "sh", "-c", BOOT_METADATA_SCRIPT],
        COMMAND_TIMEOUT_SECONDS,
        MAX_COMMAND_BYTES,
    )
    metadata = parse_boot_metadata(metadata_raw)
    identity_after_raw = run(
        [str(ADB), "-s", serial, "exec-out", "sh", "-c", t2.h0.RECOVERY_SHELL_ARGUMENT],
        COMMAND_TIMEOUT_SECONDS,
        MAX_COMMAND_BYTES,
    )
    identity_after = parse_recovery_identity(identity_after_raw)
    if identity_after != identity_before:
        raise AuditError("T2 recovery identity changed during metadata read")
    devpath_after = parse_devpath(
        run([str(ADB), "-s", serial, "get-devpath"], 10, MAX_COMMAND_BYTES)
    )
    if devpath_after != devpath_before:
        raise AuditError("selected recovery topology changed during metadata read")
    final_rows = inventory_from_result(
        run([str(ADB), "devices", "-l"], 10, MAX_COMMAND_BYTES),
        "final ADB inventory",
    )
    final_selected = select_recovery_row(final_rows, expected_serial_sha256)
    if (
        final_selected["serial"] != serial
        or base.sanitized_inventory(final_rows) != base.sanitized_inventory(first_rows)
    ):
        raise AuditError("ADB inventory changed during metadata read")
    counts = recorder.counts()
    if counts != {
        "host_command_count": 7,
        "inventory_command_count": 2,
        "selected_target_command_count": 5,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }:
        raise AuditError("D0 command counts differ")
    current_boot_id_sha256 = sha256_text(identity_before["boot_id"])
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "tier": "D0",
        "mode": "connected-read-only",
        "verdict": "PROVED_S20PLUS_G986N_TWRP_BOOT_IDENTITY_METADATA",
        "target": dict(TARGET),
        "recovery": {
            "serial_sha256": expected_serial_sha256,
            "topology_sha256": expected_topology_sha256,
            "predecessor_boot_id_sha256": predecessor["boot_id_sha256"],
            "current_boot_id_sha256": current_boot_id_sha256,
            "same_retained_recovery_boot": (
                current_boot_id_sha256 == predecessor["boot_id_sha256"]
            ),
            "t2_identity_without_boot_id": {
                key: value for key, value in identity_before.items() if key != "boot_id"
            },
        },
        "boot_partition": metadata,
        "evidence": {
            "initial_inventory_sha256": digest(base.sanitized_inventory(first_rows)),
            "identity_before_stdout_sha256": sha256_bytes(identity_before_raw[1]),
            "metadata_stdout_sha256": sha256_bytes(metadata_raw[1]),
            "identity_after_stdout_sha256": sha256_bytes(identity_after_raw[1]),
            "final_inventory_sha256": digest(base.sanitized_inventory(final_rows)),
        },
        **counts,
        "recovery_root_adbd_observed": True,
        "su_invocations": 0,
        "block_device_open_count": 0,
        "partition_content_bytes_read": 0,
        "device_writes": 0,
        "staged_payloads": 0,
        "reboots": 0,
        "mode_transitions": 0,
        "odin_invocations": 0,
        "partition_transfers": 0,
        "f1_authorized": False,
        "direct_block_write_authorized": False,
    }


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def allocate_run_dir() -> Path:
    parent = RUN_ROOT.parent
    if parent.resolve(strict=True) != parent.absolute() or parent.is_symlink():
        raise AuditError("private run parent is indirect")
    if not RUN_ROOT.exists():
        RUN_ROOT.mkdir(mode=0o700)
        fsync_directory(parent)
    root_info = RUN_ROOT.lstat()
    if (
        RUN_ROOT.is_symlink()
        or not stat.S_ISDIR(root_info.st_mode)
        or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute()
    ):
        raise AuditError("private run root is indirect")
    for _ in range(32):
        path = RUN_ROOT / f"run-{time.time_ns()}"
        if RUN_NAME_RE.fullmatch(path.name) is None:
            continue
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            continue
        fsync_directory(RUN_ROOT)
        return path
    raise AuditError("unable to allocate D0 run directory")


def durable_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("utf-8") + b"\n"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            amount = os.write(descriptor, payload[offset:])
            if amount <= 0:
                raise AuditError("short D0 result write")
            offset += amount
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_directory(path.parent)


def failure_result(recorder: CommandRecorder | None, exc: Exception) -> dict[str, Any]:
    counts = (
        recorder.counts()
        if recorder is not None
        else {
            "host_command_count": 0,
            "inventory_command_count": 0,
            "selected_target_command_count": 0,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }
    )
    return {
        "schema": "s20plus_g986n_twrp_boot_identity_d0_failure_v1",
        "version": VERSION,
        "tier": "D0",
        "verdict": "STOP_S20PLUS_G986N_TWRP_BOOT_IDENTITY_D0_NO_RETRY",
        "failure_class": type(exc).__name__,
        "failure_signature_sha256": sha256_text(f"{type(exc).__name__}:{exc}"),
        **counts,
        "device_writes": 0,
        "block_device_open_count": 0,
        "partition_content_bytes_read": 0,
        "staged_payloads": 0,
        "reboots": 0,
        "mode_transitions": 0,
        "odin_invocations": 0,
        "partition_transfers": 0,
        "f1_authorized": False,
        "direct_block_write_authorized": False,
    }


def require_active() -> None:
    if ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE is not True:
        raise AuditError("TWRP boot identity D0 is dormant")
    validate_host_closure(enforce_self=True)


def run_connected() -> dict[str, Any]:
    require_active()
    closure_before = validate_host_closure(enforce_self=True)
    run_dir = allocate_run_dir()
    recorder = CommandRecorder(base.bounded_command)
    try:
        result = collect(
            command=recorder.run,
            predecessor=closure_before["t2_predecessor"],
        )
        if recorder.counts() != {
            key: result[key]
            for key in (
                "host_command_count",
                "inventory_command_count",
                "selected_target_command_count",
                "other_target_command_count",
                "s22plus_command_count",
                "a90_command_count",
            )
        }:
            raise AuditError("outer D0 command recorder differs")
        closure_after = validate_host_closure(enforce_self=True)
        if closure_after != closure_before:
            raise AuditError("host or T2 predecessor closure changed during D0")
        result["host_closure_sha256"] = digest(closure_before)
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        durable_json(run_dir / "result.json", result)
    except Exception as exc:
        failure = failure_result(recorder, exc)
        failure["completed_at"] = datetime.now(timezone.utc).isoformat()
        durable_json(run_dir / "failure.json", failure)
        return {**failure, "run_dir": str(run_dir)}
    return {**result, "run_dir": str(run_dir)}


def render_plan() -> dict[str, Any]:
    closure = validate_host_closure(enforce_self=False)
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": (
            "BINDING_ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE"
            if ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE
            else "H0_REVIEW_PENDING_NOT_ACTIVE"
        ),
        "active": ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE,
        "live_authority": ATTENDED_TWRP_BOOT_IDENTITY_D0_ACTIVE,
        "target": dict(TARGET),
        "closure_sha256": digest(closure),
        "runner_normalized_sha256": closure["runner_normalized_sha256"],
        "connected_commands": [
            "global-adb-inventory",
            "selected-retained-recovery-get-devpath",
            "selected-exact-t2-identity-before",
            "selected-fixed-boot-metadata",
            "selected-exact-t2-identity-after",
            "selected-retained-recovery-get-devpath-after",
            "global-adb-inventory-after",
        ],
        "metadata_fields": list(BOOT_METADATA_KEYS),
        "limits": {
            "host_commands": 7,
            "selected_target_commands": 5,
            "other_target_commands": 0,
            "block_device_opens": 0,
            "partition_content_bytes_read": 0,
            "device_writes": 0,
            "reboots": 0,
            "mode_transitions": 0,
            "odin_invocations": 0,
            "partition_transfers": 0,
        },
        "grants_f1": False,
        "grants_direct_block_write": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--connected", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), indent=2, sort_keys=True, allow_nan=False))
        return 0
    try:
        result = run_connected()
    except AuditError as exc:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": "STOP_S20PLUS_G986N_TWRP_BOOT_IDENTITY_D0",
                    "error_sha256": sha256_text(str(exc)),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0 if result["verdict"].startswith("PROVED_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
