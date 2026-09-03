#!/usr/bin/env python3
"""One-use attended volatile TWRP-fastbootd census for exact SM-G986N T2."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time
from typing import Any, Callable

import s20plus_g986n_d0_inventory as base
import s20plus_g986n_fastboot_getvar_census as classic
import s20plus_g986n_twrp_boot_identity_d0 as twrp_d0
import s20plus_g986n_twrp_t2_profile_h0 as t2_profile


VERSION = "s20plus-g986n-twrp-fastbootd-census-v1"
SCHEMA = "s20plus_g986n_twrp_fastbootd_census_result_v1"
PENDING_VERDICT = "PASS_S20PLUS_G986N_TWRP_FASTBOOTD_CENSUS_RETURN_PENDING"
FINAL_PASS = "PASS_S20PLUS_G986N_TWRP_FASTBOOTD_CENSUS_RETURN_HEALTHY"
FINAL_NO_PROOF = "NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_RETURNED_HEALTHY"

# Rotated only after independent review of the exact dormant closure.
LIVE_ACTIVE = True
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "7ea137f132f00f6fa208b647b9374d0e844560f0010174b6445d0a9d48bdd7be"

GETVARS = (
    "is-userspace",
    "product",
    "version-bootloader",
    "max-download-size",
)
EXPECTED_USB = {
    "vid": "18d1",
    "pid": "4ee0",
    "bcd_device": "0100",
    "manufacturer": "samsung",
    "product": "SM-G986N",
}
EXPECTED_INTERFACE = {"class": "ff", "subclass": "42", "protocol": "03"}
EXPECTED_CONTROLLER = "a600000.dwc3"
EXPECTED_RECOVERY_USB = "mtp,adb"

RUN_ROOT_REL = Path("workspace/private/runs/s20plus-g986n-twrp-fastbootd-census")
SHARED_GUARD_REL = Path(
    "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
)
CONSUMED_NAME = "consumed-enable-intent.json"
MAX_COMMAND_BYTES = 32 * 1024
MAX_FASTBOOT_WAIT_SECONDS = 30.0
SHA256_RE = re.compile(r"[0-9a-f]{64}")

SOURCE_SPECS = {
    "s20plus_g986n_twrp_boot_identity_d0.py": {
        "size": 29_863,
        "sha256": "a71db531a25778b2dbd38c0b05b897dac33a7cc2f7eef51ba59edd899f9ecec6",
    },
    "s20plus_g986n_twrp_t2_profile_h0.py": {
        "size": 12_847,
        "sha256": "c02b78f2a1215a1fc2104a4634264609d2060d610bc628a068b318cb1cf55fb7",
    },
    "s20plus_g986n_fastboot_getvar_census.py": {
        "size": 38_587,
        "sha256": "80ab93f7e2091a5db0cedfd8d46fb2df9afaf36ceab9ca70bca6b762f535d39e",
    },
    "device_action_raw_capture_v1.py": {
        "size": 25_006,
        "sha256": "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4",
    },
    "s20plus_g986n_d0_inventory.py": {
        "size": 21_474,
        "sha256": "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    },
    "s20plus_g986n_routine_d0.py": {
        "size": 12_649,
        "sha256": "2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c",
    },
}

PREFLIGHT_SCRIPT = r"""set -eu
g=/config/usb_gadget/g1
controller=$(/system/bin/getprop sys.usb.controller)
service=$(/system/bin/getprop init.svc.fastbootd)
if [ -d "$g/functions/ffs.adb" ]; then ffs_adb=present; else ffs_adb=absent; fi
if [ -e "$g/functions/ffs.fastboot" ] || [ -L "$g/functions/ffs.fastboot" ]; then ffs_fastboot=present; else ffs_fastboot=absent; fi
if [ -d /dev/usb-ffs/fastboot ] && [ ! -L /dev/usb-ffs/fastboot ]; then fastboot_functionfs_dir=present; else fastboot_functionfs_dir=absent; fi
if /system/bin/grep -q ' /dev/usb-ffs/fastboot ' /proc/mounts; then
    if /system/bin/grep -q ' /dev/usb-ffs/fastboot functionfs ' /proc/mounts; then fastboot_functionfs=mounted; else fastboot_functionfs=other; fi
else
    fastboot_functionfs=absent
fi
active_target=$(/system/bin/readlink -f "$g/configs/b.1/f1" 2>/dev/null || true)
case "$active_target" in
    "$g/functions/ffs.adb") active_function=adb ;;
    "$g/functions/ffs.fastboot") active_function=fastboot ;;
    "") active_function=absent ;;
    *) active_function=other ;;
esac
if [ -e "$g/configs/b.1/f2" ] || [ -L "$g/configs/b.1/f2" ]; then secondary_function=present; else secondary_function=absent; fi
bound_udc=$(/system/bin/cat "$g/UDC" 2>/dev/null || true)
usb_vid=$(/system/bin/cat "$g/idVendor" 2>/dev/null || true); usb_vid=${usb_vid#0x}
usb_pid=$(/system/bin/cat "$g/idProduct" 2>/dev/null || true); usb_pid=${usb_pid#0x}
usb_bcd=$(/system/bin/cat "$g/bcdUSB" 2>/dev/null || true); usb_bcd=${usb_bcd#0x}
usb_device=$(/system/bin/cat "$g/bcdDevice" 2>/dev/null || true); usb_device=${usb_device#0x}
printf '%s\n' \
    "controller=$controller" \
    "bound_udc=$bound_udc" \
    "fastboot_service=$service" \
    "ffs_adb=$ffs_adb" \
    "ffs_fastboot=$ffs_fastboot" \
    "fastboot_functionfs_dir=$fastboot_functionfs_dir" \
    "fastboot_functionfs=$fastboot_functionfs" \
    "active_function=$active_function" \
    "secondary_function=$secondary_function" \
    "usb_vid=$usb_vid" \
    "usb_pid=$usb_pid" \
    "usb_bcd_usb=$usb_bcd" \
    "usb_bcd_device=$usb_device"
"""

INNER_ENABLE_SCRIPT = r"""set -eu
/system/bin/sleep 1
g=/config/usb_gadget/g1
controller=$(/system/bin/getprop sys.usb.controller)
[ "$controller" = "a600000.dwc3" ] || exit 111
[ "$(/system/bin/getprop init.svc.fastbootd)" = "stopped" ] || exit 112
[ ! -e "$g/functions/ffs.fastboot" ] && [ ! -L "$g/functions/ffs.fastboot" ] || exit 113
[ "$(/system/bin/readlink -f "$g/configs/b.1/f1")" = "$g/functions/ffs.adb" ] || exit 114
[ ! -e "$g/configs/b.1/f2" ] && [ ! -L "$g/configs/b.1/f2" ] || exit 115
[ "$(/system/bin/cat "$g/UDC")" = "$controller" ] || exit 116
[ "$(/system/bin/cat "$g/bcdUSB")" = "0x0320" ] || exit 117
[ "$(/system/bin/cat "$g/bcdDevice")" = "0x0419" ] || exit 118
[ -d /dev/usb-ffs/fastboot ] && [ ! -L /dev/usb-ffs/fastboot ] || exit 119
! /system/bin/grep -q ' /dev/usb-ffs/fastboot ' /proc/mounts || exit 120
/system/bin/mount -t functionfs -o rmode=0770,fmode=0660,uid=1000,gid=1000 fastboot /dev/usb-ffs/fastboot
/system/bin/grep -q ' /dev/usb-ffs/fastboot functionfs ' /proc/mounts || exit 121
/system/bin/mkdir "$g/functions/ffs.fastboot"
[ -d "$g/functions/ffs.fastboot" ] || exit 122
/system/bin/setprop ctl.start fastbootd
i=0
while [ "$i" -lt 100 ]; do
    if [ "$(/system/bin/getprop init.svc.fastbootd)" = "running" ] && \
       [ -e /dev/usb-ffs/fastboot/ep0 ] && \
       [ -e /dev/usb-ffs/fastboot/ep1 ] && \
       [ -e /dev/usb-ffs/fastboot/ep2 ]; then
        break
    fi
    i=$((i + 1))
    /system/bin/sleep 0.1
done
[ "$i" -lt 100 ] || exit 120
[ "$(/system/bin/readlink -f "$g/configs/b.1/f1")" = "$g/functions/ffs.adb" ] || exit 121
[ ! -e "$g/configs/b.1/f2" ] && [ ! -L "$g/configs/b.1/f2" ] || exit 122
[ "$(/system/bin/cat "$g/UDC")" = "$controller" ] || exit 123
printf '%s' none > "$g/UDC"
/system/bin/rm "$g/configs/b.1/f1"
/system/bin/ln -s "$g/functions/ffs.fastboot" "$g/configs/b.1/f1"
printf '%s' 0x18D1 > "$g/idVendor"
printf '%s' 0x4EE0 > "$g/idProduct"
printf '%s' 0x0100 > "$g/bcdDevice"
printf '%s' samsung > "$g/strings/0x409/manufacturer"
printf '%s' SM-G986N > "$g/strings/0x409/product"
printf '%s' fastboot > "$g/configs/b.1/strings/0x409/configuration"
printf '%s' "$controller" > "$g/UDC"
printf '%s\n' enabled > /tmp/s20plus_g986n_fastbootd_enabled_v1
"""

LAUNCH_SCRIPT = (
    "set -eu\n"
    "[ \"$(/system/bin/id -u)\" = \"0\" ] || exit 121\n"
    f"[ \"$(/system/bin/getprop ro.twrp.version)\" = \"{t2_profile.TWRP_VERSION}\" ] || exit 122\n"
    f"[ \"$(/system/bin/getprop ro.build.version.incremental)\" = \"{t2_profile.TWRP_INCREMENTAL}\" ] || exit 123\n"
    f"[ \"$(/system/bin/getprop sys.usb.config)\" = \"{EXPECTED_RECOVERY_USB}\" ] || exit 124\n"
    f"marker=$(/system/bin/sha256sum {t2_profile.MARKER_PATH})\n"
    "set -- $marker\n"
    f"[ \"$#\" -eq 2 ] && [ \"$1\" = \"{t2_profile.MARKER_SHA256}\" ] && [ \"$2\" = \"{t2_profile.MARKER_PATH}\" ] || exit 125\n"
    "/system/bin/nohup /system/bin/setsid /system/bin/sh -c "
    + shlex.quote(INNER_ENABLE_SCRIPT)
    + " </dev/null >/tmp/s20plus_g986n_fastbootd_enable_v1.log 2>&1 &\n"
    "printf 'armed\\n'\n"
)

PREFLIGHT_KEYS = (
    "controller",
    "bound_udc",
    "fastboot_service",
    "ffs_adb",
    "ffs_fastboot",
    "fastboot_functionfs_dir",
    "fastboot_functionfs",
    "active_function",
    "secondary_function",
    "usb_vid",
    "usb_pid",
    "usb_bcd_usb",
    "usb_bcd_device",
)
PREFLIGHT_EXPECTED = {
    "controller": EXPECTED_CONTROLLER,
    "bound_udc": EXPECTED_CONTROLLER,
    "fastboot_service": "stopped",
    "ffs_adb": "present",
    "ffs_fastboot": "absent",
    "fastboot_functionfs_dir": "present",
    "fastboot_functionfs": "absent",
    "active_function": "adb",
    "secondary_function": "absent",
    "usb_vid": "04e8",
    "usb_pid": "6860",
    "usb_bcd_usb": "0320",
    "usb_bcd_device": "0419",
}


class FastbootdCensusError(RuntimeError):
    pass


class ReturnRequiredError(FastbootdCensusError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]
UsbInventory = Callable[[], tuple[dict[str, Any], ...]]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_root(root: Path) -> Path:
    return root / RUN_ROOT_REL


def lexists(path: Path) -> bool:
    """Return true for every directory entry, including a broken symlink."""

    return os.path.lexists(path)


def guard_path(root: Path) -> Path:
    return root / SHARED_GUARD_REL


def consumed_path(root: Path) -> Path:
    return run_root(root) / CONSUMED_NAME


def file_receipt(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise FastbootdCensusError(f"{label} is unavailable") from exc
    if (
        path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size != size
        or classic.sha256_file(path) != digest
    ):
        raise FastbootdCensusError(f"{label} identity differs")
    return {"path": str(path), "size": size, "sha256": digest}


def normalized_self_sha256() -> str:
    path = Path(__file__).resolve()
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise FastbootdCensusError("current fastbootd runner is indirect")
    payload = path.read_bytes()
    payload, active_count = re.subn(
        rb"^LIVE_ACTIVE = (?:False|True)$",
        b"LIVE_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        payload,
        count=1,
        flags=re.MULTILINE,
    )
    payload, reviewed_count = re.subn(
        rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = ".*"$',
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "<REVIEWED_NORMALIZED_SHA256>"',
        payload,
        count=1,
        flags=re.MULTILINE,
    )
    if active_count != 1 or reviewed_count != 1:
        raise FastbootdCensusError("fastbootd runner activation normalization differs")
    return hashlib.sha256(payload).hexdigest()


def require_support(root: Path) -> dict[str, Any]:
    directory = Path(__file__).resolve().parent
    sources = {
        name: file_receipt(directory / name, spec["size"], spec["sha256"], name)
        for name, spec in SOURCE_SPECS.items()
    }
    normalized = normalized_self_sha256()
    if normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise FastbootdCensusError("fastbootd runner normalized identity is not reviewed")
    return {
        "sources": sources,
        "runner": {
            "size": Path(__file__).stat().st_size,
            "sha256": classic.sha256_file(Path(__file__).resolve()),
            "normalized_sha256": normalized,
        },
        "adb": base.tool_receipt(base.DEFAULT_ADB),
        "fastboot": classic.require_fastboot(root),
        "preflight_script": {
            "size": len(PREFLIGHT_SCRIPT.encode()),
            "sha256": hashlib.sha256(PREFLIGHT_SCRIPT.encode()).hexdigest(),
        },
        "launch_script": {
            "size": len(LAUNCH_SCRIPT.encode()),
            "sha256": hashlib.sha256(LAUNCH_SCRIPT.encode()).hexdigest(),
        },
        "inner_enable_script": {
            "size": len(INNER_ENABLE_SCRIPT.encode()),
            "sha256": hashlib.sha256(INNER_ENABLE_SCRIPT.encode()).hexdigest(),
        },
    }


def allocate_run_dir(root: Path) -> Path:
    parent = run_root(root)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = parent / (
        "run-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{time.time_ns()}"
    )
    path.mkdir(mode=0o700)
    classic._fsync_dir(parent)
    return path


def acquire_guard(root: Path, run_dir: Path) -> None:
    path = guard_path(root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        base.durable_write(
            path,
            {
                "schema": "s20plus_g986n_twrp_fastbootd_guard_v1",
                "version": VERSION,
                "action": "attended-t2-volatile-fastbootd-census",
                "run_dir": str(run_dir),
                "unresolved": True,
                "at": now(),
            },
        )
    except FileExistsError as exc:
        raise FastbootdCensusError("an unresolved shared S20+ action exists") from exc


def check_guard(root: Path, run_dir: Path) -> None:
    value = classic.load_json(guard_path(root), "shared action guard")
    if (
        set(value)
        != {"schema", "version", "action", "run_dir", "unresolved", "at"}
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_guard_v1"
        or value.get("version") != VERSION
        or value.get("action") != "attended-t2-volatile-fastbootd-census"
        or value.get("run_dir") != str(run_dir)
        or value.get("unresolved") is not True
        or not isinstance(value.get("at"), str)
        or not value.get("at")
    ):
        raise FastbootdCensusError("shared action guard binding differs")


def release_guard(root: Path, run_dir: Path) -> None:
    check_guard(root, run_dir)
    path = guard_path(root)
    path.unlink()
    classic._fsync_dir(path.parent)


def parse_preflight(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    returncode, stdout, stderr = result
    if returncode != 0 or stderr or len(stdout) > 4096:
        raise FastbootdCensusError("volatile fastbootd preflight failed")
    try:
        text = stdout.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise FastbootdCensusError("volatile fastbootd preflight is not UTF-8") from exc
    if "\r" in text or "\x00" in text or not text.endswith("\n"):
        raise FastbootdCensusError("volatile fastbootd preflight framing differs")
    lines = text.splitlines()
    if len(lines) != len(PREFLIGHT_KEYS):
        raise FastbootdCensusError("volatile fastbootd preflight field count differs")
    values: dict[str, str] = {}
    for expected, line in zip(PREFLIGHT_KEYS, lines, strict=True):
        key, separator, value = line.partition("=")
        if separator != "=" or key != expected or not value or key in values:
            raise FastbootdCensusError("volatile fastbootd preflight grammar differs")
        values[key] = value
    if values != PREFLIGHT_EXPECTED:
        raise FastbootdCensusError("volatile fastbootd preflight values differ")
    return values


def recovery_snapshot(
    command: Command,
    predecessor: dict[str, Any],
    *,
    expected_other: list[str] | None = None,
) -> dict[str, Any]:
    adb = str(base.DEFAULT_ADB)
    first_rows = twrp_d0.inventory_from_result(
        command([adb, "devices", "-l"], 10, MAX_COMMAND_BYTES),
        "initial recovery ADB inventory",
    )
    selected = twrp_d0.select_recovery_row(first_rows, predecessor["serial_sha256"])
    serial = selected["serial"]
    devpath = twrp_d0.parse_devpath(
        command([adb, "-s", serial, "get-devpath"], 10, MAX_COMMAND_BYTES)
    )
    if base.sha256_text(devpath) != predecessor["topology_sha256"]:
        raise FastbootdCensusError("current T2 recovery topology differs")
    identity = twrp_d0.parse_recovery_identity(
        command(
            [adb, "-s", serial, "exec-out", "sh", "-c", t2_profile.RECOVERY_SHELL_ARGUMENT],
            30,
            MAX_COMMAND_BYTES,
        )
    )
    preflight = parse_preflight(
        command(
            [adb, "-s", serial, "exec-out", "sh", "-c", PREFLIGHT_SCRIPT],
            20,
            MAX_COMMAND_BYTES,
        )
    )
    final_rows = twrp_d0.inventory_from_result(
        command([adb, "devices", "-l"], 10, MAX_COMMAND_BYTES),
        "final recovery ADB inventory",
    )
    final = twrp_d0.select_recovery_row(final_rows, predecessor["serial_sha256"])
    if final["serial"] != serial:
        raise FastbootdCensusError("current T2 recovery selection changed")
    other = sorted(base.sha256_text(row["serial"]) for row in first_rows if row["serial"] != serial)
    final_other = sorted(base.sha256_text(row["serial"]) for row in final_rows if row["serial"] != serial)
    if other != final_other or (expected_other is not None and other != expected_other):
        raise FastbootdCensusError("other ADB inventory changed")
    return {
        "serial": serial,
        "node": devpath.removeprefix("usb:"),
        "serial_sha256": predecessor["serial_sha256"],
        "topology_sha256": predecessor["topology_sha256"],
        "boot_id_sha256": base.sha256_text(identity["boot_id"]),
        "other_serial_sha256": other,
        "identity": {key: value for key, value in identity.items() if key != "boot_id"},
        "preflight": preflight,
    }


def _is_fastboot_interface(interface: dict[str, Any]) -> bool:
    return all(interface.get(key) == value for key, value in EXPECTED_INTERFACE.items())


def validate_fastbootd_usb(
    rows: tuple[dict[str, Any], ...], node: str, serial: str
) -> dict[str, Any] | None:
    matches = [
        row
        for row in rows
        if any(_is_fastboot_interface(item) for item in row.get("interfaces", ()))
    ]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("node") != node:
        raise FastbootdCensusError("fastbootd endpoint is foreign or ambiguous")
    row = matches[0]
    if (
        row.get("vid") != EXPECTED_USB["vid"]
        or row.get("pid") != EXPECTED_USB["pid"]
        or row.get("bcd_device") != EXPECTED_USB["bcd_device"]
        or str(row.get("manufacturer", "")).casefold() != EXPECTED_USB["manufacturer"]
        or row.get("product") != EXPECTED_USB["product"]
        or row.get("serial") != serial
    ):
        raise FastbootdCensusError("fastbootd USB identity differs")
    interfaces = row.get("interfaces", ())
    if len(interfaces) != 1 or not _is_fastboot_interface(interfaces[0]):
        raise FastbootdCensusError("fastbootd interface count differs")
    endpoints = interfaces[0].get("endpoints", ())
    if len(endpoints) != 2:
        raise FastbootdCensusError("fastbootd endpoint count differs")
    directions = set()
    for endpoint in endpoints:
        if endpoint.get("type") != "Bulk" or endpoint.get("max_packet_size") not in {"0200", "0400"}:
            raise FastbootdCensusError("fastbootd bulk endpoint differs")
        directions.add(endpoint.get("direction"))
    if directions != {"in", "out"}:
        raise FastbootdCensusError("fastbootd endpoint directions differ")
    return row


def wait_fastbootd(
    usb_inventory: UsbInventory,
    node: str,
    serial: str,
    *,
    timeout: float = MAX_FASTBOOT_WAIT_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not 0.1 <= timeout <= MAX_FASTBOOT_WAIT_SECONDS:
        raise FastbootdCensusError("fastbootd wait bound differs")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        endpoint = validate_fastbootd_usb(usb_inventory(), node, serial)
        if endpoint is not None:
            return endpoint
        sleep(0.1)
    raise ReturnRequiredError("exact volatile fastbootd endpoint did not arrive")


def create_enable_intent(root: Path, run_dir: Path, prepared: dict[str, Any]) -> None:
    intent = {
        "schema": "s20plus_g986n_twrp_fastbootd_enable_intent_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "prepared_sha256": classic.object_sha256(prepared),
        "attempt": 1,
        "volatile_only": True,
        "persistent_writes": 0,
        "partition_operations": 0,
        "replay_permitted": False,
        "at": now(),
    }
    base.durable_write(run_dir / "enable-intent.json", intent)
    base.durable_write(consumed_path(root), intent)


def validate_enable_intent(
    run_dir: Path,
    intent: dict[str, Any],
    prepared: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        set(intent)
        != {
            "schema",
            "version",
            "run_dir",
            "prepared_sha256",
            "attempt",
            "volatile_only",
            "persistent_writes",
            "partition_operations",
            "replay_permitted",
            "at",
        }
        or intent.get("schema")
        != "s20plus_g986n_twrp_fastbootd_enable_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("run_dir") != str(run_dir)
        or not _is_sha256(intent.get("prepared_sha256"))
        or type(intent.get("attempt")) is not int
        or intent.get("attempt") != 1
        or intent.get("volatile_only") is not True
        or type(intent.get("persistent_writes")) is not int
        or intent.get("persistent_writes") != 0
        or type(intent.get("partition_operations")) is not int
        or intent.get("partition_operations") != 0
        or intent.get("replay_permitted") is not False
        or not isinstance(intent.get("at"), str)
    ):
        raise FastbootdCensusError("fastbootd enable intent differs")
    if prepared is not None and intent.get("prepared_sha256") != classic.object_sha256(
        prepared
    ):
        raise FastbootdCensusError("fastbootd enable intent prepared binding differs")
    return intent


def _validate_run_dir(root: Path, run_dir: Path) -> Path:
    parent = run_root(root).resolve(strict=True)
    try:
        metadata = run_dir.lstat()
    except OSError as exc:
        raise FastbootdCensusError("consumed run directory is unavailable") from exc
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISDIR(metadata.st_mode)
        or run_dir.parent.resolve(strict=True) != parent
    ):
        raise FastbootdCensusError("consumed run directory is indirect")
    return run_dir


def resolve_consumed_run(root: Path) -> Path:
    path = consumed_path(root)
    if lexists(path):
        intent = classic.load_json(path, "consumed fastbootd enable intent")
        raw = intent.get("run_dir")
        if not isinstance(raw, str):
            raise FastbootdCensusError("consumed fastbootd enable intent differs")
        run_dir = _validate_run_dir(root, Path(raw))
        prepared = classic.load_json(run_dir / "prepared.json", "prepared fastbootd census")
        validate_prepared(run_dir, prepared)
        validate_enable_intent(run_dir, intent, prepared)
    else:
        guard = classic.load_json(guard_path(root), "shared action guard")
        raw = guard.get("run_dir")
        if not isinstance(raw, str):
            raise FastbootdCensusError("shared action guard run differs")
        run_dir = _validate_run_dir(root, Path(raw))
        prepared = classic.load_json(run_dir / "prepared.json", "prepared fastbootd census")
        validate_prepared(run_dir, prepared)
        intent = classic.load_json(run_dir / "enable-intent.json", "local fastbootd enable intent")
        validate_enable_intent(run_dir, intent, prepared)
        base.durable_write(path, intent)
    return run_dir


def enable_is_consumed(root: Path, run_dir: Path) -> bool:
    return lexists(consumed_path(root)) or lexists(run_dir / "enable-intent.json")


def connected_census(
    root: Path,
    run_dir: Path,
    command: Command,
    usb_inventory: UsbInventory = classic.real_usb_inventory,
) -> dict[str, Any]:
    if not LIVE_ACTIVE:
        raise FastbootdCensusError("live TWRP fastbootd census is not active")
    if lexists(consumed_path(root)):
        raise FastbootdCensusError("the one-use volatile fastbootd enable is consumed")
    support = require_support(root)
    predecessor = twrp_d0.validate_t2_predecessor()
    acquire_guard(root, run_dir)
    recovery = recovery_snapshot(command, predecessor)
    target = {
        "model": "SM-G986N",
        "device": "y2q",
        "product": "y2qksx",
        "incremental": "G986NKSS8IYC2",
        "serial_sha256": recovery["serial_sha256"],
        "topology_sha256": recovery["topology_sha256"],
        "recovery_boot_id_sha256": recovery["boot_id_sha256"],
        "other_serial_sha256": recovery["other_serial_sha256"],
    }
    prepared = {
        "schema": "s20plus_g986n_twrp_fastbootd_prepared_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "target": target,
        "t2_predecessor": predecessor,
        "t2_identity": recovery["identity"],
        "volatile_preflight": recovery["preflight"],
        "support_sha256": classic.object_sha256(support),
        "fixed_getvars": list(GETVARS),
        "fastboot_tool": support["fastboot"],
        "persistent_writes": 0,
        "partition_operations": 0,
        "at": now(),
    }
    base.durable_write(run_dir / "prepared.json", prepared)
    if require_support(root) != support:
        raise FastbootdCensusError("fastbootd support closure changed before enable")
    create_enable_intent(root, run_dir, prepared)
    acquisition_error: str | None = None
    try:
        raw_result = command(
            [str(base.DEFAULT_ADB), "-s", recovery["serial"], "exec-out", "sh", "-c", LAUNCH_SCRIPT],
            15,
            MAX_COMMAND_BYTES,
        )
    except Exception as exc:
        raw_result = None
        acquisition_error = hashlib.sha256(
            f"{type(exc).__name__}:{exc}".encode()
        ).hexdigest()
    armed = raw_result == (0, b"armed\n", b"")
    base.durable_write(
        run_dir / "enable-result.json",
        {
            "schema": "s20plus_g986n_twrp_fastbootd_enable_result_v1",
            "version": VERSION,
            "armed": armed,
            "returncode": None if raw_result is None else raw_result[0],
            "stdout_sha256": None if raw_result is None else hashlib.sha256(raw_result[1]).hexdigest(),
            "stderr_sha256": None if raw_result is None else hashlib.sha256(raw_result[2]).hexdigest(),
            "acquisition_error_sha256": acquisition_error,
            "replay_permitted": False,
            "at": now(),
        },
    )
    if require_support(root) != support:
        raise ReturnRequiredError("fastbootd support closure changed after enable")
    endpoint = wait_fastbootd(usb_inventory, recovery["node"], recovery["serial"])
    base.durable_write(
        run_dir / "entry-observed.json",
        {
            "schema": "s20plus_g986n_twrp_fastbootd_entry_observed_v1",
            "version": VERSION,
            "serial_sha256": recovery["serial_sha256"],
            "topology_sha256": recovery["topology_sha256"],
            "vid": endpoint["vid"],
            "pid": endpoint["pid"],
            "bcd_device": endpoint["bcd_device"],
            "interface": dict(EXPECTED_INTERFACE),
            "at": now(),
        },
    )
    post_rows = twrp_d0.inventory_from_result(
        command([str(base.DEFAULT_ADB), "devices", "-l"], 10, MAX_COMMAND_BYTES),
        "post-fastbootd ADB inventory",
    )
    if any(base.sha256_text(row["serial"]) == recovery["serial_sha256"] for row in post_rows):
        raise ReturnRequiredError("T2 target remains in ADB after fastbootd arrival")
    other = sorted(base.sha256_text(row["serial"]) for row in post_rows)
    if other != recovery["other_serial_sha256"]:
        raise ReturnRequiredError("other ADB inventory changed during fastbootd entry")
    observations: list[dict[str, Any]] = []
    private_values = (recovery["serial"], recovery["node"])
    for ordinal, variable in enumerate(GETVARS, start=1):
        if classic.require_fastboot(root) != support["fastboot"]:
            raise ReturnRequiredError("fastboot tool changed during census")
        if validate_fastbootd_usb(usb_inventory(), recovery["node"], recovery["serial"]) is None:
            raise ReturnRequiredError("fastbootd endpoint disappeared during census")
        intent = {
            "schema": "s20plus_g986n_twrp_fastbootd_getvar_intent_v1",
            "version": VERSION,
            "ordinal": ordinal,
            "variable": variable,
            "attempt": 1,
            "replay_permitted": False,
            "at": now(),
        }
        base.durable_write(run_dir / f"query-{ordinal:02d}-intent.json", intent)
        observation = classic.classify_getvar(
            variable,
            command(
                [support["fastboot"]["path"], "-s", recovery["serial"], "getvar", variable],
                10,
                MAX_COMMAND_BYTES,
            ),
            private_values,
        )
        observation["intent_sha256"] = classic.object_sha256(intent)
        observation["ordinal"] = ordinal
        validate_query_result(intent, ordinal, variable, observation)
        base.durable_write(run_dir / f"query-{ordinal:02d}-result.json", observation)
        observations.append(observation)
        if ordinal == 1 and not (
            observation.get("status") == "VALUE"
            and str(observation.get("value", "")).casefold() == "yes"
        ):
            raise ReturnRequiredError("endpoint did not prove userspace fastbootd")
        if observation.get("status") == "FAILURE_STOP":
            raise ReturnRequiredError("unrecognized fastbootd getvar failure")
    if classic.require_fastboot(root) != support["fastboot"]:
        raise ReturnRequiredError("fastboot tool changed after census")
    if validate_fastbootd_usb(usb_inventory(), recovery["node"], recovery["serial"]) is None:
        raise ReturnRequiredError("fastbootd endpoint disappeared after census")
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "target": target,
        "getvar_order": list(GETVARS),
        "getvars": observations,
        "is_userspace_yes": True,
        "volatile_enable_attempts": 1,
        "recovery_adb_selected_command_count": 3,
        "fastboot_command_count": len(GETVARS),
        "selected_s20plus_command_attempt_count": 4 + len(GETVARS),
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "other_target_command_count": 0,
        "fastboot_download_phase": False,
        "getvar_all_sent": False,
        "boot_command_sent": False,
        "flash_command_sent": False,
        "erase_command_sent": False,
        "set_active_sent": False,
        "persistent_writes": 0,
        "partition_operations": 0,
        "return_health_pending": True,
        "replay_permitted": False,
        "verdict": PENDING_VERDICT,
        "at": now(),
    }
    base.durable_write(run_dir / "probe-result.json", result)
    return result


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def validate_prepared(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    if set(prepared) != {
        "schema",
        "version",
        "run_dir",
        "target",
        "t2_predecessor",
        "t2_identity",
        "volatile_preflight",
        "support_sha256",
        "fixed_getvars",
        "fastboot_tool",
        "persistent_writes",
        "partition_operations",
        "at",
    }:
        raise FastbootdCensusError("prepared fastbootd field set differs")
    target = prepared.get("target")
    other = target.get("other_serial_sha256") if isinstance(target, dict) else None
    if (
        prepared.get("schema") != "s20plus_g986n_twrp_fastbootd_prepared_v1"
        or prepared.get("version") != VERSION
        or prepared.get("run_dir") != str(run_dir)
        or prepared.get("fixed_getvars") != list(GETVARS)
        or type(prepared.get("persistent_writes")) is not int
        or prepared.get("persistent_writes") != 0
        or type(prepared.get("partition_operations")) is not int
        or prepared.get("partition_operations") != 0
        or not _is_sha256(prepared.get("support_sha256"))
        or not isinstance(target, dict)
        or set(target) != {
            "model",
            "device",
            "product",
            "incremental",
            "serial_sha256",
            "topology_sha256",
            "recovery_boot_id_sha256",
            "other_serial_sha256",
        }
        or target.get("model") != "SM-G986N"
        or target.get("device") != "y2q"
        or target.get("product") != "y2qksx"
        or target.get("incremental") != "G986NKSS8IYC2"
        or any(
            not _is_sha256(target.get(key))
            for key in ("serial_sha256", "topology_sha256", "recovery_boot_id_sha256")
        )
        or not isinstance(other, list)
        or any(not _is_sha256(value) for value in other)
        or len(other) != len(set(other))
        or not isinstance(prepared.get("t2_predecessor"), dict)
        or not isinstance(prepared.get("t2_identity"), dict)
        or prepared.get("volatile_preflight") != PREFLIGHT_EXPECTED
        or not isinstance(prepared.get("fastboot_tool"), dict)
        or prepared.get("fastboot_tool", {}).get("path") is None
        or not isinstance(prepared.get("at"), str)
    ):
        raise FastbootdCensusError("prepared fastbootd binding differs")
    return target


def validate_enable_result(run_dir: Path) -> bool:
    path = run_dir / "enable-result.json"
    if not lexists(path):
        return False
    result = classic.load_json(path, "volatile fastbootd enable result")
    if set(result) != {
        "schema",
        "version",
        "armed",
        "returncode",
        "stdout_sha256",
        "stderr_sha256",
        "acquisition_error_sha256",
        "replay_permitted",
        "at",
    }:
        raise FastbootdCensusError("volatile fastbootd enable result fields differ")
    error = result.get("acquisition_error_sha256")
    command_fields = (
        result.get("returncode"),
        result.get("stdout_sha256"),
        result.get("stderr_sha256"),
    )
    command_result = (
        isinstance(command_fields[0], int)
        and not isinstance(command_fields[0], bool)
        and _is_sha256(command_fields[1])
        and _is_sha256(command_fields[2])
        and error is None
    )
    acquisition_failure = all(value is None for value in command_fields) and _is_sha256(error)
    armed_exact = (
        result.get("returncode") == 0
        and result.get("stdout_sha256") == hashlib.sha256(b"armed\n").hexdigest()
        and result.get("stderr_sha256") == hashlib.sha256(b"").hexdigest()
    )
    if (
        result.get("schema") != "s20plus_g986n_twrp_fastbootd_enable_result_v1"
        or result.get("version") != VERSION
        or not isinstance(result.get("armed"), bool)
        or result.get("replay_permitted") is not False
        or not isinstance(result.get("at"), str)
        or not (command_result or acquisition_failure)
        or (acquisition_failure and result.get("armed") is not False)
        or (result.get("armed") is True and not armed_exact)
    ):
        raise FastbootdCensusError("volatile fastbootd enable result differs")
    return True


def validate_entry_observation(run_dir: Path, target: dict[str, Any]) -> bool:
    path = run_dir / "entry-observed.json"
    if not lexists(path):
        return False
    value = classic.load_json(path, "fastbootd entry observation")
    if (
        set(value)
        != {
            "schema",
            "version",
            "serial_sha256",
            "topology_sha256",
            "vid",
            "pid",
            "bcd_device",
            "interface",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_entry_observed_v1"
        or value.get("version") != VERSION
        or value.get("serial_sha256") != target.get("serial_sha256")
        or value.get("topology_sha256") != target.get("topology_sha256")
        or value.get("vid") != EXPECTED_USB["vid"]
        or value.get("pid") != EXPECTED_USB["pid"]
        or value.get("bcd_device") != EXPECTED_USB["bcd_device"]
        or value.get("interface") != EXPECTED_INTERFACE
        or not isinstance(value.get("at"), str)
    ):
        raise FastbootdCensusError("fastbootd entry observation differs")
    return True


def validate_query_result(
    intent: dict[str, Any], ordinal: int, variable: str, result: dict[str, Any]
) -> dict[str, Any]:
    if (
        set(result)
        != {
            "schema",
            "version",
            "variable",
            "status",
            "value",
            "returncode",
            "output_sha256",
            "output",
            "captured_before_parse",
            "at",
            "intent_sha256",
            "ordinal",
        }
        or result.get("schema")
        != "s20plus_g986n_fastboot_getvar_observation_v1"
        or result.get("version") != classic.VERSION
        or result.get("ordinal") != ordinal
        or result.get("variable") != variable
        or result.get("intent_sha256") != classic.object_sha256(intent)
        or result.get("status") not in {"VALUE", "UNSUPPORTED", "FAILURE_STOP"}
        or not (isinstance(result.get("value"), str) or result.get("value") is None)
        or type(result.get("returncode")) is not int
        or not isinstance(result.get("output"), str)
        or not _is_sha256(result.get("output_sha256"))
        or result.get("captured_before_parse") is not True
        or not isinstance(result.get("at"), str)
    ):
        raise FastbootdCensusError("fastbootd query result differs")
    try:
        output = result["output"].encode("utf-8", "strict")
    except UnicodeError as exc:
        raise FastbootdCensusError("fastbootd query output encoding differs") from exc
    if len(output) > MAX_COMMAND_BYTES:
        raise FastbootdCensusError("fastbootd query output exceeds its bound")
    derived = classic.classify_getvar(
        variable,
        (result["returncode"], output, b""),
        (),
    )
    for key in ("status", "value", "returncode", "output_sha256", "output"):
        if result.get(key) != derived.get(key):
            raise FastbootdCensusError("fastbootd query result cannot be rederived")
    return result


def validate_query_prefix(run_dir: Path, entry_present: bool) -> int:
    allowed_intents = {
        run_dir / f"query-{ordinal:02d}-intent.json"
        for ordinal in range(1, len(GETVARS) + 1)
    }
    allowed_results = {
        run_dir / f"query-{ordinal:02d}-result.json"
        for ordinal in range(1, len(GETVARS) + 1)
    }
    if set(run_dir.glob("query-*-intent.json")) - allowed_intents or set(
        run_dir.glob("query-*-result.json")
    ) - allowed_results:
        raise FastbootdCensusError("unexpected fastbootd query evidence exists")
    count = 0
    missing_seen = False
    first_userspace_yes = False
    for ordinal, variable in enumerate(GETVARS, start=1):
        intent_path = run_dir / f"query-{ordinal:02d}-intent.json"
        result_path = run_dir / f"query-{ordinal:02d}-result.json"
        if not lexists(intent_path):
            if lexists(result_path):
                raise FastbootdCensusError("fastbootd result lacks its intent")
            missing_seen = True
            continue
        if missing_seen or not entry_present:
            raise FastbootdCensusError("fastbootd query intent lacks its entry")
        intent = classic.load_json(intent_path, f"query {ordinal} intent")
        if (
            set(intent)
            != {
                "schema",
                "version",
                "ordinal",
                "variable",
                "attempt",
                "replay_permitted",
                "at",
            }
            or intent.get("schema") != "s20plus_g986n_twrp_fastbootd_getvar_intent_v1"
            or intent.get("version") != VERSION
            or intent.get("ordinal") != ordinal
            or intent.get("variable") != variable
            or type(intent.get("attempt")) is not int
            or intent.get("attempt") != 1
            or intent.get("replay_permitted") is not False
            or not isinstance(intent.get("at"), str)
        ):
            raise FastbootdCensusError("fastbootd query intent differs")
        count += 1
        if not lexists(result_path):
            missing_seen = True
            continue
        result = classic.load_json(result_path, f"query {ordinal} result")
        validate_query_result(intent, ordinal, variable, result)
        if ordinal == 1:
            first_userspace_yes = (
                result.get("status") == "VALUE"
                and str(result.get("value", "")).casefold() == "yes"
            )
            if not first_userspace_yes:
                missing_seen = True
        elif not first_userspace_yes:
            raise FastbootdCensusError("later fastbootd query lacks userspace proof")
        if result.get("status") == "FAILURE_STOP":
            missing_seen = True
    return count


def validate_journal(
    root: Path, run_dir: Path, prepared: dict[str, Any]
) -> tuple[int, bool]:
    target = validate_prepared(run_dir, prepared)
    local = classic.load_json(run_dir / "enable-intent.json", "local fastbootd enable intent")
    consumed = classic.load_json(consumed_path(root), "consumed fastbootd enable intent")
    validate_enable_intent(run_dir, local, prepared)
    validate_enable_intent(run_dir, consumed, prepared)
    if local != consumed:
        raise FastbootdCensusError("fastbootd enable intent chain differs")
    enable_result = validate_enable_result(run_dir)
    entry_present = validate_entry_observation(run_dir, target)
    count = validate_query_prefix(run_dir, entry_present)
    if entry_present and not enable_result:
        raise FastbootdCensusError("fastbootd entry lacks enable result")
    probe_present = lexists(run_dir / "probe-result.json")
    if probe_present and (not entry_present or count != len(GETVARS)):
        raise FastbootdCensusError("fastbootd probe lacks complete predecessor evidence")
    if probe_present and classic.load_json(
        run_dir / "probe-result.json", "fastbootd probe result target"
    ).get("target") != target:
        raise FastbootdCensusError("fastbootd probe target differs")
    proved = probe_is_complete(run_dir) if probe_present else False
    return count, proved


def probe_is_complete(run_dir: Path) -> bool:
    path = run_dir / "probe-result.json"
    if not lexists(path):
        return False
    probe = classic.load_json(path, "fastbootd probe result")
    observations = probe.get("getvars")
    if (
        set(probe)
        != {
            "schema",
            "version",
            "target",
            "getvar_order",
            "getvars",
            "is_userspace_yes",
            "volatile_enable_attempts",
            "recovery_adb_selected_command_count",
            "fastboot_command_count",
            "selected_s20plus_command_attempt_count",
            "s22plus_command_count",
            "a90_command_count",
            "other_target_command_count",
            "fastboot_download_phase",
            "getvar_all_sent",
            "boot_command_sent",
            "flash_command_sent",
            "erase_command_sent",
            "set_active_sent",
            "persistent_writes",
            "partition_operations",
            "return_health_pending",
            "replay_permitted",
            "verdict",
            "at",
        }
        or probe.get("schema") != SCHEMA
        or probe.get("version") != VERSION
        or probe.get("verdict") != PENDING_VERDICT
        or probe.get("getvar_order") != list(GETVARS)
        or type(probe.get("volatile_enable_attempts")) is not int
        or probe.get("volatile_enable_attempts") != 1
        or type(probe.get("fastboot_command_count")) is not int
        or probe.get("fastboot_command_count") != len(GETVARS)
        or type(probe.get("recovery_adb_selected_command_count")) is not int
        or probe.get("recovery_adb_selected_command_count") != 3
        or type(probe.get("selected_s20plus_command_attempt_count")) is not int
        or probe.get("selected_s20plus_command_attempt_count") != 4 + len(GETVARS)
        or any(
            type(probe.get(key)) is not int or probe.get(key) != 0
            for key in (
                "s22plus_command_count",
                "a90_command_count",
                "other_target_command_count",
                "persistent_writes",
                "partition_operations",
            )
        )
        or any(
            probe.get(key) is not False
            for key in (
                "fastboot_download_phase",
                "getvar_all_sent",
                "boot_command_sent",
                "flash_command_sent",
                "erase_command_sent",
                "set_active_sent",
            )
        )
        or probe.get("is_userspace_yes") is not True
        or probe.get("return_health_pending") is not True
        or probe.get("replay_permitted") is not False
        or not isinstance(probe.get("at"), str)
        or not isinstance(observations, list)
        or len(observations) != len(GETVARS)
    ):
        raise FastbootdCensusError("fastbootd probe result differs")
    for ordinal, variable in enumerate(GETVARS, start=1):
        intent = classic.load_json(
            run_dir / f"query-{ordinal:02d}-intent.json", f"query {ordinal} intent"
        )
        result = classic.load_json(
            run_dir / f"query-{ordinal:02d}-result.json", f"query {ordinal} result"
        )
        validate_query_result(intent, ordinal, variable, result)
        if (
            intent.get("ordinal") != ordinal
            or intent.get("variable") != variable
            or intent.get("replay_permitted") is not False
            or result.get("ordinal") != ordinal
            or result.get("variable") != variable
            or result.get("intent_sha256") != classic.object_sha256(intent)
            or result.get("status") not in {"VALUE", "UNSUPPORTED"}
            or observations[ordinal - 1] != result
        ):
            raise FastbootdCensusError("fastbootd query evidence differs")
    first = observations[0]
    if first.get("status") != "VALUE" or str(first.get("value", "")).casefold() != "yes":
        raise FastbootdCensusError("fastbootd userspace proof differs")
    return True


def validate_final_result(
    run_dir: Path,
    prepared: dict[str, Any],
    count: int,
    proved: bool,
    result: dict[str, Any],
) -> dict[str, Any]:
    target = validate_prepared(run_dir, prepared)
    returned = result.get("returned_android")
    health = returned.get("health") if isinstance(returned, dict) else None
    expected_health = {
        "model": "SM-G986N",
        "device": "y2q",
        "product_name": "y2qksx",
        "incremental": "G986NKSS8IYC2",
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    if (
        set(result)
        != {
            "schema",
            "version",
            "target",
            "returned_android",
            "fastboot_query_intent_count",
            "is_userspace_yes_proved",
            "volatile_enable_attempts",
            "selected_s20plus_command_attempt_count",
            "persistent_writes",
            "partition_operations",
            "fastboot_mutation_commands",
            "s22plus_command_count",
            "a90_command_count",
            "other_target_command_count",
            "replay_permitted",
            "verdict",
            "at",
        }
        or result.get("schema") != "s20plus_g986n_twrp_fastbootd_final_result_v1"
        or result.get("version") != VERSION
        or result.get("target") != target
        or not isinstance(returned, dict)
        or set(returned) != {"boot_id_sha256", "health"}
        or not _is_sha256(returned.get("boot_id_sha256"))
        or returned.get("boot_id_sha256") == target.get("recovery_boot_id_sha256")
        or health != expected_health
        or type(result.get("fastboot_query_intent_count")) is not int
        or result.get("fastboot_query_intent_count") != count
        or type(result.get("is_userspace_yes_proved")) is not bool
        or result.get("is_userspace_yes_proved") is not proved
        or type(result.get("volatile_enable_attempts")) is not int
        or result.get("volatile_enable_attempts") != 1
        or type(result.get("selected_s20plus_command_attempt_count")) is not int
        or result.get("selected_s20plus_command_attempt_count") != 7 + count
        or type(result.get("persistent_writes")) is not int
        or result.get("persistent_writes") != 0
        or type(result.get("partition_operations")) is not int
        or result.get("partition_operations") != 0
        or type(result.get("fastboot_mutation_commands")) is not int
        or result.get("fastboot_mutation_commands") != 0
        or type(result.get("s22plus_command_count")) is not int
        or result.get("s22plus_command_count") != 0
        or type(result.get("a90_command_count")) is not int
        or result.get("a90_command_count") != 0
        or type(result.get("other_target_command_count")) is not int
        or result.get("other_target_command_count") != 0
        or result.get("replay_permitted") is not False
        or result.get("verdict") != (FINAL_PASS if proved else FINAL_NO_PROOF)
        or not isinstance(result.get("at"), str)
    ):
        raise FastbootdCensusError("final fastbootd result differs")
    return result


def abort_pre_effect(root: Path) -> dict[str, Any]:
    guard = classic.load_json(guard_path(root), "shared action guard")
    raw = guard.get("run_dir")
    if not isinstance(raw, str):
        raise FastbootdCensusError("shared action guard run differs")
    run_dir = _validate_run_dir(root, Path(raw))
    check_guard(root, run_dir)
    if enable_is_consumed(root, run_dir):
        raise FastbootdCensusError("volatile enable intent exists; pre-effect abort is unavailable")
    forbidden = (
        "enable-result.json",
        "entry-observed.json",
        "probe-result.json",
        "final-result.json",
    )
    if any(lexists(run_dir / name) for name in forbidden) or any(
        run_dir.glob("query-*.json")
    ):
        raise FastbootdCensusError("effect evidence exists; pre-effect abort is unavailable")
    prepared_path = run_dir / "prepared.json"
    prepared_sha256 = None
    if lexists(prepared_path):
        prepared = classic.load_json(prepared_path, "prepared fastbootd census")
        validate_prepared(run_dir, prepared)
        prepared_sha256 = classic.object_sha256(prepared)
    result: dict[str, Any] = {
        "schema": "s20plus_g986n_twrp_fastbootd_pre_effect_abort_v1",
        "version": VERSION,
        "prepared_sha256": prepared_sha256,
        "device_effects": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "verdict": "ABORTED_S20PLUS_G986N_TWRP_FASTBOOTD_BEFORE_EFFECT",
        "at": now(),
    }
    abort_path = run_dir / "pre-effect-abort.json"
    if lexists(abort_path):
        result = classic.load_json(abort_path, "pre-effect abort result")
        if (
            set(result)
            != {
                "schema",
                "version",
                "prepared_sha256",
                "device_effects",
                "persistent_writes",
                "partition_operations",
                "verdict",
                "at",
            }
            or result.get("schema")
            != "s20plus_g986n_twrp_fastbootd_pre_effect_abort_v1"
            or result.get("version") != VERSION
            or result.get("prepared_sha256") != prepared_sha256
            or any(
                type(result.get(key)) is not int or result.get(key) != 0
                for key in (
                    "device_effects",
                    "persistent_writes",
                    "partition_operations",
                )
            )
            or result.get("verdict")
            != "ABORTED_S20PLUS_G986N_TWRP_FASTBOOTD_BEFORE_EFFECT"
            or not isinstance(result.get("at"), str)
        ):
            raise FastbootdCensusError("pre-effect abort result differs")
    else:
        base.durable_write(abort_path, result)
    release_guard(root, run_dir)
    return result


def finalize(
    root: Path,
    command: Command,
    usb_inventory: UsbInventory = classic.real_usb_inventory,
) -> dict[str, Any]:
    run_dir = resolve_consumed_run(root)
    final_path = run_dir / "final-result.json"
    if lexists(final_path):
        result = classic.load_json(final_path, "final fastbootd result")
        prepared = classic.load_json(run_dir / "prepared.json", "prepared fastbootd census")
        count, proved = validate_journal(root, run_dir, prepared)
        validate_final_result(run_dir, prepared, count, proved, result)
        if lexists(guard_path(root)):
            release_guard(root, run_dir)
        return result
    check_guard(root, run_dir)
    prepared = classic.load_json(run_dir / "prepared.json", "prepared fastbootd census")
    intent = classic.load_json(consumed_path(root), "consumed fastbootd enable intent")
    if intent.get("prepared_sha256") != classic.object_sha256(prepared):
        raise FastbootdCensusError("prepared fastbootd evidence differs")
    count, proved = validate_journal(root, run_dir, prepared)
    target = validate_prepared(run_dir, prepared)
    if any(
        _is_fastboot_interface(interface)
        for row in usb_inventory()
        for interface in row.get("interfaces", ())
    ):
        raise ReturnRequiredError("phone remains in fastbootd")
    support = require_support(root)
    if classic.object_sha256(support) != prepared.get("support_sha256"):
        raise FastbootdCensusError("fastbootd support closure changed before return")
    returned = classic.collect_android_health(command, usb_inventory)
    if (
        returned["serial_sha256"] != target.get("serial_sha256")
        or returned["topology_sha256"] != target.get("topology_sha256")
        or returned["other_serial_sha256"] != target.get("other_serial_sha256")
        or returned["boot_id_sha256"] == target.get("recovery_boot_id_sha256")
    ):
        raise FastbootdCensusError("returned Android identity or boot differs")
    if require_support(root) != support:
        raise FastbootdCensusError("fastbootd support closure changed after return")
    result = {
        "schema": "s20plus_g986n_twrp_fastbootd_final_result_v1",
        "version": VERSION,
        "target": target,
        "returned_android": {
            "boot_id_sha256": returned["boot_id_sha256"],
            "health": returned["health"],
        },
        "fastboot_query_intent_count": count,
        "is_userspace_yes_proved": proved,
        "volatile_enable_attempts": 1,
        "selected_s20plus_command_attempt_count": 7 + count,
        "persistent_writes": 0,
        "partition_operations": 0,
        "fastboot_mutation_commands": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "other_target_command_count": 0,
        "replay_permitted": False,
        "verdict": FINAL_PASS if proved else FINAL_NO_PROOF,
        "at": now(),
    }
    validate_final_result(run_dir, prepared, count, proved, result)
    base.durable_write(final_path, result)
    release_guard(root, run_dir)
    return result


def plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_twrp_fastbootd_plan_v1",
        "version": VERSION,
        "target": "SM-G986N/y2q/y2qksx/G986NKSS8IYC2",
        "start": "exact retained T2 recovery ADB",
        "volatile_control": "start existing fastbootd and rebind only recovery configfs",
        "expected_fastboot_usb": "18d1:4ee0 ff/42/03",
        "getvars": list(GETVARS),
        "getvar_all": False,
        "fastboot_mutation_commands": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "physical_android_return": True,
        "live_active": LIVE_ACTIVE,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--connected", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    modes.add_argument("--abort-pre-effect", action="store_true")
    parser.add_argument("--operator-attended", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    if args.render_plan:
        print(json.dumps(plan(), indent=2, sort_keys=True))
        return 0
    if not LIVE_ACTIVE:
        print("STOP_S20PLUS_TWRP_FASTBOOTD: reviewed activation is absent")
        return 2
    if args.abort_pre_effect:
        try:
            result = abort_pre_effect(root)
        except Exception:
            print("FAIL_S20PLUS_TWRP_FASTBOOTD_PRE_EFFECT_ABORT_CLOSED")
            return 1
        print(result["verdict"])
        return 0
    if not args.operator_attended:
        print("STOP_S20PLUS_TWRP_FASTBOOTD: operator attendance is required")
        return 2
    if args.connected:
        run_dir = allocate_run_dir(root)
        command = classic.RawCommand(run_dir, "connected")
        try:
            result = connected_census(root, run_dir, command)
        except ReturnRequiredError as exc:
            base.durable_write(
                run_dir / "failure.json",
                {
                    "schema": "s20plus_g986n_twrp_fastbootd_failure_v1",
                    "version": VERSION,
                    "failure_sha256": hashlib.sha256(
                        f"{type(exc).__name__}:{exc}".encode()
                    ).hexdigest(),
                    "return_required": True,
                    "replay_permitted": False,
                    "persistent_writes": 0,
                    "partition_operations": 0,
                    "at": now(),
                },
            )
            print("RECOVERY_PENDING_S20PLUS_TWRP_FASTBOOTD_PHYSICAL_REBOOT")
            return 1
        except Exception as exc:
            consumed = enable_is_consumed(root, run_dir)
            base.durable_write(
                run_dir / "failure.json",
                {
                    "schema": "s20plus_g986n_twrp_fastbootd_failure_v1",
                    "version": VERSION,
                    "failure_sha256": hashlib.sha256(
                        f"{type(exc).__name__}:{exc}".encode()
                    ).hexdigest(),
                    "return_required": consumed,
                    "replay_permitted": False,
                    "persistent_writes": 0,
                    "partition_operations": 0,
                    "at": now(),
                },
            )
            if not consumed and lexists(guard_path(root)):
                try:
                    release_guard(root, run_dir)
                except Exception:
                    pass
            print(
                "RECOVERY_PENDING_S20PLUS_TWRP_FASTBOOTD_PHYSICAL_REBOOT"
                if consumed
                else "FAIL_S20PLUS_TWRP_FASTBOOTD_PRE_EFFECT_CLOSED"
            )
            return 1
        print(result["verdict"])
        print("OPERATOR_ACTION_REQUIRED: use TWRP UI or physical keys to reboot System")
        return 0
    try:
        run_dir = resolve_consumed_run(root)
        if lexists(run_dir / "final-result.json"):
            def no_command(*_args: Any) -> tuple[int, bytes, bytes]:
                raise FastbootdCensusError("terminal re-emission cannot contact the device")
            command = no_command
        else:
            command = classic.RawCommand(
                run_dir,
                "finalize",
                capture_dir=classic.allocate_finalize_capture_dir(run_dir),
            )
        result = finalize(root, command)
    except ReturnRequiredError:
        print("RETURN_REQUIRED_S20PLUS_TWRP_FASTBOOTD: reboot System physically")
        return 1
    except Exception:
        print("FAIL_S20PLUS_TWRP_FASTBOOTD_FINALIZE_CLOSED")
        return 1
    print(result["verdict"])
    print(f"result={run_dir / 'final-result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
