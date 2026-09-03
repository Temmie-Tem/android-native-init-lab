#!/usr/bin/env python3
"""Attended one-use T2 fastbootd preparation probe without USB role switch."""

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
from typing import Any, Callable

import s20plus_g986n_d0_inventory as base
import s20plus_g986n_fastboot_getvar_census as classic
import s20plus_g986n_twrp_boot_identity_d0 as twrp_d0
import s20plus_g986n_twrp_fastbootd_census as predecessor
import s20plus_g986n_twrp_t2_profile_h0 as t2_profile


VERSION = "s20plus-g986n-twrp-fastbootd-prep-probe-v1"
PENDING = "PASS_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_READY_RETURN_PENDING"
FINAL_PASS = "PASS_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_RETURNED_HEALTHY"
FINAL_NO_PROOF = "NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_RETURNED_HEALTHY"

LIVE_ACTIVE = True
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "8c52caa352779509d17e675fd544089e4e3b6ccb22cde1a6aab878e39a225b26"

RUN_ROOT_REL = Path("workspace/private/runs/s20plus-g986n-twrp-fastbootd-prep-probe")
SHARED_GUARD_REL = Path(
    "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
)
CONSUMED_NAME = "consumed-prep-intent.json"
OLD_FINAL_REL = Path(
    "workspace/private/runs/s20plus-g986n-twrp-fastbootd-census/"
    "run-20260902T181904Z-1788373144962486779/final-result.json"
)
OLD_FINAL_SIZE = 1_456
OLD_FINAL_SHA256 = "8979538332be37879700b2f455e77eb9e12c1ed4ccc3efbdb5d7d49bde90b0a4"
OLD_CONSUMED_REL = Path(
    "workspace/private/runs/s20plus-g986n-twrp-fastbootd-census/"
    "consumed-enable-intent.json"
)
OLD_CONSUMED_SIZE = 534
OLD_CONSUMED_SHA256 = "df486135a3619871e76b891a4b4a0f8f90d1693d0b43a9cc4629c52c3f947153"
OLD_RUNNER_SIZE = 60_738
OLD_RUNNER_SHA256 = "9e89e9fd56630d571270faa2ee9410049c4fb8b5bd9ae8800f9a9bf840ac6225"
MAX_BYTES = 32 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}")

PREPARE_SCRIPT = r"""set -eu
g=/config/usb_gadget/g1
controller=$(/system/bin/getprop sys.usb.controller)
[ "$controller" = "a600000.dwc3" ] || exit 201
[ "$(/system/bin/getprop init.svc.fastbootd)" = "stopped" ] || exit 202
[ -d /dev/usb-ffs/fastboot ] && [ ! -L /dev/usb-ffs/fastboot ] || exit 203
! /system/bin/grep -q ' /dev/usb-ffs/fastboot ' /proc/mounts || exit 204
[ ! -e "$g/functions/ffs.fastboot" ] && [ ! -L "$g/functions/ffs.fastboot" ] || exit 205
[ "$(/system/bin/readlink -f "$g/configs/b.1/f1")" = "$g/functions/ffs.adb" ] || exit 206
[ ! -e "$g/configs/b.1/f2" ] && [ ! -L "$g/configs/b.1/f2" ] || exit 207
[ "$(/system/bin/cat "$g/UDC")" = "$controller" ] || exit 208
[ "$(/system/bin/cat "$g/bcdUSB")" = "0x0320" ] || exit 209
[ "$(/system/bin/cat "$g/bcdDevice")" = "0x0419" ] || exit 210
/system/bin/mount -t functionfs -o rmode=0770,fmode=0660,uid=1000,gid=1000 fastboot /dev/usb-ffs/fastboot
/system/bin/grep -q ' /dev/usb-ffs/fastboot functionfs ' /proc/mounts || exit 211
printf '%s\n' stage=functionfs-mounted
/system/bin/mkdir "$g/functions/ffs.fastboot"
[ -d "$g/functions/ffs.fastboot" ] && [ ! -L "$g/functions/ffs.fastboot" ] || exit 212
printf '%s\n' stage=configfs-function-created
/system/bin/setprop ctl.start fastbootd
i=0
while [ "$i" -lt 100 ]; do
    [ "$(/system/bin/getprop init.svc.fastbootd)" = "running" ] && break
    i=$((i + 1))
    /system/bin/sleep 0.1
done
[ "$i" -lt 100 ] || exit 213
printf '%s\n' stage=service-running
i=0
while [ "$i" -lt 100 ]; do
    if [ -e /dev/usb-ffs/fastboot/ep0 ] && \
       [ -e /dev/usb-ffs/fastboot/ep1 ] && \
       [ -e /dev/usb-ffs/fastboot/ep2 ]; then
        break
    fi
    i=$((i + 1))
    /system/bin/sleep 0.1
done
[ "$i" -lt 100 ] || exit 214
[ "$(/system/bin/readlink -f "$g/configs/b.1/f1")" = "$g/functions/ffs.adb" ] || exit 215
[ ! -e "$g/configs/b.1/f2" ] && [ ! -L "$g/configs/b.1/f2" ] || exit 216
[ "$(/system/bin/cat "$g/UDC")" = "$controller" ] || exit 217
printf '%s\n' stage=endpoints-ready
"""

POST_SCRIPT = r"""set -eu
g=/config/usb_gadget/g1
controller=$(/system/bin/getprop sys.usb.controller)
[ "$controller" = "a600000.dwc3" ] || exit 221
[ "$(/system/bin/getprop init.svc.fastbootd)" = "running" ] || exit 222
[ -d /dev/usb-ffs/fastboot ] && [ ! -L /dev/usb-ffs/fastboot ] || exit 223
/system/bin/grep -q ' /dev/usb-ffs/fastboot functionfs ' /proc/mounts || exit 224
[ -d "$g/functions/ffs.fastboot" ] && [ ! -L "$g/functions/ffs.fastboot" ] || exit 225
[ -e /dev/usb-ffs/fastboot/ep0 ] || exit 226
[ -e /dev/usb-ffs/fastboot/ep1 ] || exit 227
[ -e /dev/usb-ffs/fastboot/ep2 ] || exit 228
[ "$(/system/bin/readlink -f "$g/configs/b.1/f1")" = "$g/functions/ffs.adb" ] || exit 229
[ ! -e "$g/configs/b.1/f2" ] && [ ! -L "$g/configs/b.1/f2" ] || exit 230
[ "$(/system/bin/cat "$g/UDC")" = "$controller" ] || exit 231
[ "$(/system/bin/getprop sys.usb.config)" = "mtp,adb" ] || exit 232
[ "$(/system/bin/getprop init.svc.adbd)" = "running" ] || exit 233
printf '%s\n' prep_state=ready-adb-retained
"""

SUCCESS_OUTPUT = (
    b"stage=functionfs-mounted\n"
    b"stage=configfs-function-created\n"
    b"stage=service-running\n"
    b"stage=endpoints-ready\n"
)
POST_OUTPUT = b"prep_state=ready-adb-retained\n"
STAGES = (
    "none",
    "functionfs-mounted",
    "configfs-function-created",
    "service-running",
    "endpoints-ready",
)


class PrepProbeError(RuntimeError):
    pass


class ReturnRequiredError(PrepProbeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def lexists(path: Path) -> bool:
    return os.path.lexists(path)


def run_root(root: Path) -> Path:
    return root / RUN_ROOT_REL


def consumed_path(root: Path) -> Path:
    return run_root(root) / CONSUMED_NAME


def guard_path(root: Path) -> Path:
    return root / SHARED_GUARD_REL


def sha256_file(path: Path) -> str:
    return classic.sha256_file(path)


def pin_file(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    try:
        state = path.lstat()
    except OSError as exc:
        raise PrepProbeError(f"{label} is unavailable") from exc
    if (
        stat.S_ISLNK(state.st_mode)
        or not stat.S_ISREG(state.st_mode)
        or state.st_nlink != 1
        or state.st_size != size
        or sha256_file(path) != digest
    ):
        raise PrepProbeError(f"{label} identity differs")
    return {"path": str(path), "size": size, "sha256": digest}


def normalized_self_sha256() -> str:
    path = Path(__file__).resolve()
    state = path.lstat()
    if stat.S_ISLNK(state.st_mode) or not stat.S_ISREG(state.st_mode) or state.st_nlink != 1:
        raise PrepProbeError("prep probe source is indirect")
    payload = path.read_bytes()
    payload, active_count = re.subn(
        rb"^LIVE_ACTIVE = (?:False|True)$",
        b"LIVE_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        payload,
        count=1,
        flags=re.MULTILINE,
    )
    payload, digest_count = re.subn(
        rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = ".*"$',
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "<REVIEWED_NORMALIZED_SHA256>"',
        payload,
        count=1,
        flags=re.MULTILINE,
    )
    if active_count != 1 or digest_count != 1:
        raise PrepProbeError("prep probe normalization differs")
    return hashlib.sha256(payload).hexdigest()


def require_support(root: Path) -> dict[str, Any]:
    old_path = Path(predecessor.__file__).resolve()
    old_source = pin_file(old_path, OLD_RUNNER_SIZE, OLD_RUNNER_SHA256, "old census runner")
    normalized = normalized_self_sha256()
    if normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise PrepProbeError("prep probe normalized identity is not reviewed")
    return {
        "old_source": old_source,
        "old_support_sha256": classic.object_sha256(predecessor.require_support(root)),
        "adb": base.tool_receipt(base.DEFAULT_ADB),
        "runner": {
            "size": Path(__file__).stat().st_size,
            "sha256": sha256_file(Path(__file__).resolve()),
            "normalized_sha256": normalized,
        },
        "prepare_script": {
            "size": len(PREPARE_SCRIPT.encode()),
            "sha256": hashlib.sha256(PREPARE_SCRIPT.encode()).hexdigest(),
        },
        "post_script": {
            "size": len(POST_SCRIPT.encode()),
            "sha256": hashlib.sha256(POST_SCRIPT.encode()).hexdigest(),
        },
    }


def no_device_command(*_args: Any) -> tuple[int, bytes, bytes]:
    raise PrepProbeError("predecessor validation attempted device contact")


def validate_predecessor(root: Path) -> dict[str, Any]:
    pin_file(root / OLD_FINAL_REL, OLD_FINAL_SIZE, OLD_FINAL_SHA256, "old census terminal")
    pin_file(
        root / OLD_CONSUMED_REL,
        OLD_CONSUMED_SIZE,
        OLD_CONSUMED_SHA256,
        "old census consumed marker",
    )
    if lexists(guard_path(root)):
        raise PrepProbeError("shared S20+ guard is not empty")
    value = predecessor.finalize(root, no_device_command, lambda: ())
    if (
        value.get("verdict")
        != "NO_PROOF_S20PLUS_G986N_TWRP_FASTBOOTD_RETURNED_HEALTHY"
        or value.get("replay_permitted") is not False
        or value.get("fastboot_query_intent_count") != 0
        or value.get("is_userspace_yes_proved") is not False
        or value.get("persistent_writes") != 0
        or value.get("partition_operations") != 0
        or value.get("fastboot_mutation_commands") != 0
    ):
        raise PrepProbeError("old census terminal differs")
    return value


def allocate_run_dir(root: Path) -> Path:
    parent = run_root(root)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = parent / (
        "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{time.time_ns()}"
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
                "schema": "s20plus_g986n_twrp_fastbootd_prep_guard_v1",
                "version": VERSION,
                "action": "attended-t2-fastbootd-prep-probe",
                "run_dir": str(run_dir),
                "unresolved": True,
                "at": now(),
            },
        )
    except FileExistsError as exc:
        raise PrepProbeError("an unresolved shared S20+ action exists") from exc


def check_guard(root: Path, run_dir: Path) -> None:
    value = classic.load_json(guard_path(root), "prep probe guard")
    if (
        set(value) != {"schema", "version", "action", "run_dir", "unresolved", "at"}
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_prep_guard_v1"
        or value.get("version") != VERSION
        or value.get("action") != "attended-t2-fastbootd-prep-probe"
        or value.get("run_dir") != str(run_dir)
        or value.get("unresolved") is not True
        or not isinstance(value.get("at"), str)
        or not value.get("at")
    ):
        raise PrepProbeError("prep probe guard differs")


def release_guard(root: Path, run_dir: Path) -> None:
    check_guard(root, run_dir)
    path = guard_path(root)
    path.unlink()
    classic._fsync_dir(path.parent)


def create_intent(root: Path, run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    intent = {
        "schema": "s20plus_g986n_twrp_fastbootd_prep_intent_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "prepared_sha256": classic.object_sha256(prepared),
        "attempt": 1,
        "volatile_functionfs_mount_attempts": 1,
        "volatile_service_start_attempts": 1,
        "usb_role_switch_attempts": 0,
        "fastboot_commands": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "replay_permitted": False,
        "at": now(),
    }
    base.durable_write(run_dir / "prep-intent.json", intent)
    base.durable_write(consumed_path(root), intent)
    return intent


def classify_prepare(result: tuple[int, bytes, bytes]) -> dict[str, Any]:
    returncode, stdout, stderr = result
    prefixes = [b""]
    offset = 0
    for line in SUCCESS_OUTPUT.splitlines(keepends=True):
        offset += len(line)
        prefixes.append(SUCCESS_OUTPUT[:offset])
    last_stage = STAGES[prefixes.index(stdout)] if stdout in prefixes else "invalid-output"
    success = returncode == 0 and stderr == b"" and stdout == SUCCESS_OUTPUT
    return {
        "schema": "s20plus_g986n_twrp_fastbootd_prep_command_result_v1",
        "version": VERSION,
        "success": success,
        "last_stage": last_stage,
        "returncode": returncode,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "stdout_size": len(stdout),
        "stderr_size": len(stderr),
        "usb_role_switched": False,
        "fastboot_commands": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "replay_permitted": False,
        "at": now(),
    }


def final_recovery_check(
    command: Command, recovery: dict[str, Any]
) -> dict[str, Any]:
    adb = str(base.DEFAULT_ADB)
    serial = recovery["serial"]
    post_raw = command(
        [adb, "-s", serial, "exec-out", "sh", "-c", POST_SCRIPT], 20, MAX_BYTES
    )
    if post_raw != (0, POST_OUTPUT, b""):
        raise ReturnRequiredError("post-prepare T2 state differs")
    identity = twrp_d0.parse_recovery_identity(
        command(
            [adb, "-s", serial, "exec-out", "sh", "-c", t2_profile.RECOVERY_SHELL_ARGUMENT],
            30,
            MAX_BYTES,
        )
    )
    if base.sha256_text(identity["boot_id"]) != recovery["boot_id_sha256"]:
        raise ReturnRequiredError("recovery boot changed during preparation probe")
    devpath = twrp_d0.parse_devpath(
        command([adb, "-s", serial, "get-devpath"], 10, MAX_BYTES)
    )
    if base.sha256_text(devpath) != recovery["topology_sha256"]:
        raise ReturnRequiredError("recovery topology changed during preparation probe")
    rows = twrp_d0.inventory_from_result(
        command([adb, "devices", "-l"], 10, MAX_BYTES), "post-prepare ADB inventory"
    )
    selected = twrp_d0.select_recovery_row(rows, recovery["serial_sha256"])
    if selected["serial"] != serial:
        raise ReturnRequiredError("recovery selection changed during preparation probe")
    other = sorted(base.sha256_text(row["serial"]) for row in rows if row["serial"] != serial)
    if other != recovery["other_serial_sha256"]:
        raise ReturnRequiredError("other ADB inventory changed during preparation probe")
    return {key: value for key, value in identity.items() if key != "boot_id"}


def connected_probe(root: Path, run_dir: Path, command: Command) -> dict[str, Any]:
    if not LIVE_ACTIVE:
        raise PrepProbeError("live preparation probe is not active")
    if lexists(consumed_path(root)):
        raise PrepProbeError("the one-use preparation probe is consumed")
    support = require_support(root)
    validate_predecessor(root)
    t2 = twrp_d0.validate_t2_predecessor()
    acquire_guard(root, run_dir)
    recovery = predecessor.recovery_snapshot(command, t2)
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
        "schema": "s20plus_g986n_twrp_fastbootd_prep_prepared_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "target": target,
        "old_terminal_sha256": OLD_FINAL_SHA256,
        "old_consumed_sha256": OLD_CONSUMED_SHA256,
        "support_sha256": classic.object_sha256(support),
        "t2_predecessor_sha256": classic.object_sha256(t2),
        "starting_identity": recovery["identity"],
        "starting_preflight": recovery["preflight"],
        "usb_role_switch_attempts": 0,
        "fastboot_commands": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "at": now(),
    }
    base.durable_write(run_dir / "prepared.json", prepared)
    if require_support(root) != support:
        raise PrepProbeError("preparation probe support changed before intent")
    intent = create_intent(root, run_dir, prepared)
    command_result = classify_prepare(
        command(
            [str(base.DEFAULT_ADB), "-s", recovery["serial"], "exec-out", "sh", "-c", PREPARE_SCRIPT],
            30,
            MAX_BYTES,
        )
    )
    command_result["intent_sha256"] = classic.object_sha256(intent)
    base.durable_write(run_dir / "prep-command-result.json", command_result)
    if not command_result["success"]:
        raise ReturnRequiredError("fastbootd preparation did not reach endpoints-ready")
    post_identity = final_recovery_check(command, recovery)
    if post_identity != recovery["identity"]:
        raise ReturnRequiredError("recovery identity changed during preparation probe")
    if require_support(root) != support:
        raise ReturnRequiredError("preparation probe support changed after effect")
    result = {
        "schema": "s20plus_g986n_twrp_fastbootd_prep_probe_result_v1",
        "version": VERSION,
        "target": target,
        "last_stage": "endpoints-ready",
        "functionfs_mounted": True,
        "configfs_function_created": True,
        "fastbootd_service_running": True,
        "fastboot_endpoints_ready": True,
        "adb_retained": True,
        "post_identity": post_identity,
        "volatile_functionfs_mount_attempts": 1,
        "volatile_service_start_attempts": 1,
        "usb_role_switch_attempts": 0,
        "fastboot_commands": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "return_health_pending": True,
        "replay_permitted": False,
        "verdict": PENDING,
        "at": now(),
    }
    validate_probe(run_dir, prepared, result)
    base.durable_write(run_dir / "probe-result.json", result)
    return result


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def validate_run_dir(root: Path, run_dir: Path) -> Path:
    try:
        parent = run_root(root).resolve(strict=True)
        state = run_dir.lstat()
    except OSError as exc:
        raise PrepProbeError("prep run is unavailable") from exc
    if (
        stat.S_ISLNK(state.st_mode)
        or not stat.S_ISDIR(state.st_mode)
        or run_dir.parent.resolve(strict=True) != parent
    ):
        raise PrepProbeError("prep run is indirect or outside its root")
    return run_dir


def validate_prepared(run_dir: Path, value: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema",
        "version",
        "run_dir",
        "target",
        "old_terminal_sha256",
        "old_consumed_sha256",
        "support_sha256",
        "t2_predecessor_sha256",
        "starting_identity",
        "starting_preflight",
        "usb_role_switch_attempts",
        "fastboot_commands",
        "persistent_writes",
        "partition_operations",
        "at",
    }
    target = value.get("target")
    other = target.get("other_serial_sha256") if isinstance(target, dict) else None
    if (
        set(value) != expected
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_prep_prepared_v1"
        or value.get("version") != VERSION
        or value.get("run_dir") != str(run_dir)
        or value.get("old_terminal_sha256") != OLD_FINAL_SHA256
        or value.get("old_consumed_sha256") != OLD_CONSUMED_SHA256
        or not _is_sha256(value.get("support_sha256"))
        or not _is_sha256(value.get("t2_predecessor_sha256"))
        or not isinstance(target, dict)
        or set(target)
        != {
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
        or any(not _is_sha256(item) for item in other)
        or len(other) != len(set(other))
        or not isinstance(value.get("starting_identity"), dict)
        or value.get("starting_preflight") != predecessor.PREFLIGHT_EXPECTED
        or any(
            type(value.get(key)) is not int or value.get(key) != 0
            for key in (
                "usb_role_switch_attempts",
                "fastboot_commands",
                "persistent_writes",
                "partition_operations",
            )
        )
        or not isinstance(value.get("at"), str)
    ):
        raise PrepProbeError("prep prepared binding differs")
    return target


def validate_intent(
    run_dir: Path, prepared: dict[str, Any], value: dict[str, Any]
) -> dict[str, Any]:
    if (
        set(value)
        != {
            "schema",
            "version",
            "run_dir",
            "prepared_sha256",
            "attempt",
            "volatile_functionfs_mount_attempts",
            "volatile_service_start_attempts",
            "usb_role_switch_attempts",
            "fastboot_commands",
            "persistent_writes",
            "partition_operations",
            "replay_permitted",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_prep_intent_v1"
        or value.get("version") != VERSION
        or value.get("run_dir") != str(run_dir)
        or value.get("prepared_sha256") != classic.object_sha256(prepared)
        or any(
            type(value.get(key)) is not int or value.get(key) != expected
            for key, expected in (
                ("attempt", 1),
                ("volatile_functionfs_mount_attempts", 1),
                ("volatile_service_start_attempts", 1),
                ("usb_role_switch_attempts", 0),
                ("fastboot_commands", 0),
                ("persistent_writes", 0),
                ("partition_operations", 0),
            )
        )
        or value.get("replay_permitted") is not False
        or not isinstance(value.get("at"), str)
    ):
        raise PrepProbeError("prep intent differs")
    return value


def raw_result(run_dir: Path, name: str) -> tuple[int, bytes, bytes]:
    receipt = run_dir / "raw-captures" / f"{name}.capture.json"
    try:
        handle = classic.raw_capture.load_handle(receipt)
    except (OSError, classic.raw_capture.RawCaptureError) as exc:
        raise PrepProbeError(f"raw capture {name} is unavailable") from exc
    if (
        handle.name != name
        or handle.returncode is None
        or handle.timed_out
        or handle.output_exceeded
        or handle.producer_error_type is not None
    ):
        raise PrepProbeError(f"raw capture {name} differs")
    return (
        handle.returncode,
        classic.raw_capture.read_stdout(handle, maximum=MAX_BYTES),
        classic.raw_capture.read_stderr(handle, maximum=MAX_BYTES),
    )


def validate_command_result(
    run_dir: Path, intent: dict[str, Any], value: dict[str, Any]
) -> bool:
    if set(value) != {
        "schema",
        "version",
        "success",
        "last_stage",
        "returncode",
        "stdout_sha256",
        "stderr_sha256",
        "stdout_size",
        "stderr_size",
        "usb_role_switched",
        "fastboot_commands",
        "persistent_writes",
        "partition_operations",
        "replay_permitted",
        "at",
        "intent_sha256",
    }:
        raise PrepProbeError("prep command result fields differ")
    derived = classify_prepare(raw_result(run_dir, "connected-06"))
    if (
        value.get("schema") != derived["schema"]
        or value.get("version") != VERSION
        or value.get("intent_sha256") != classic.object_sha256(intent)
        or any(value.get(key) != derived.get(key) for key in derived if key != "at")
        or not isinstance(value.get("at"), str)
    ):
        raise PrepProbeError("prep command result cannot be rederived")
    return value.get("success") is True


def validate_post_raw(run_dir: Path, prepared: dict[str, Any]) -> None:
    target = validate_prepared(run_dir, prepared)
    if raw_result(run_dir, "connected-07") != (0, POST_OUTPUT, b""):
        raise PrepProbeError("post-prepare raw state differs")
    identity = twrp_d0.parse_recovery_identity(raw_result(run_dir, "connected-08"))
    if (
        base.sha256_text(identity["boot_id"]) != target["recovery_boot_id_sha256"]
        or {key: item for key, item in identity.items() if key != "boot_id"}
        != prepared["starting_identity"]
    ):
        raise PrepProbeError("post-prepare raw identity differs")
    devpath = twrp_d0.parse_devpath(raw_result(run_dir, "connected-09"))
    if base.sha256_text(devpath) != target["topology_sha256"]:
        raise PrepProbeError("post-prepare raw topology differs")
    rows = twrp_d0.inventory_from_result(
        raw_result(run_dir, "connected-10"), "stored post-prepare inventory"
    )
    selected = twrp_d0.select_recovery_row(rows, target["serial_sha256"])
    if base.sha256_text(selected["serial"]) != target["serial_sha256"]:
        raise PrepProbeError("stored post-prepare selection differs")
    other = sorted(
        base.sha256_text(row["serial"])
        for row in rows
        if row["serial"] != selected["serial"]
    )
    if other != target["other_serial_sha256"]:
        raise PrepProbeError("stored other ADB inventory differs")


def validate_probe(
    run_dir: Path, prepared: dict[str, Any], value: dict[str, Any]
) -> None:
    if (
        set(value)
        != {
            "schema",
            "version",
            "target",
            "last_stage",
            "functionfs_mounted",
            "configfs_function_created",
            "fastbootd_service_running",
            "fastboot_endpoints_ready",
            "adb_retained",
            "post_identity",
            "volatile_functionfs_mount_attempts",
            "volatile_service_start_attempts",
            "usb_role_switch_attempts",
            "fastboot_commands",
            "persistent_writes",
            "partition_operations",
            "return_health_pending",
            "replay_permitted",
            "verdict",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_prep_probe_result_v1"
        or value.get("version") != VERSION
        or value.get("target") != validate_prepared(run_dir, prepared)
        or value.get("last_stage") != "endpoints-ready"
        or any(
            value.get(key) is not True
            for key in (
                "functionfs_mounted",
                "configfs_function_created",
                "fastbootd_service_running",
                "fastboot_endpoints_ready",
                "adb_retained",
                "return_health_pending",
            )
        )
        or value.get("post_identity") != prepared["starting_identity"]
        or any(
            type(value.get(key)) is not int or value.get(key) != expected
            for key, expected in (
                ("volatile_functionfs_mount_attempts", 1),
                ("volatile_service_start_attempts", 1),
                ("usb_role_switch_attempts", 0),
                ("fastboot_commands", 0),
                ("persistent_writes", 0),
                ("partition_operations", 0),
            )
        )
        or value.get("replay_permitted") is not False
        or value.get("verdict") != PENDING
        or not isinstance(value.get("at"), str)
    ):
        raise PrepProbeError("prep probe result differs")
    validate_post_raw(run_dir, prepared)


def resolve_run(root: Path) -> Path:
    global_path = consumed_path(root)
    if lexists(global_path):
        intent = classic.load_json(global_path, "consumed prep intent")
        raw = intent.get("run_dir")
        if not isinstance(raw, str):
            raise PrepProbeError("consumed prep run differs")
        run_dir = Path(raw)
    else:
        guard = classic.load_json(guard_path(root), "prep probe guard")
        raw = guard.get("run_dir")
        if not isinstance(raw, str):
            raise PrepProbeError("prep probe guard run differs")
        run_dir = Path(raw)
    validate_run_dir(root, run_dir)
    if not lexists(global_path):
        check_guard(root, run_dir)
        prepared = classic.load_json(run_dir / "prepared.json", "prep prepared")
        validate_prepared(run_dir, prepared)
        intent = classic.load_json(run_dir / "prep-intent.json", "local prep intent")
        validate_intent(run_dir, prepared, intent)
        base.durable_write(global_path, intent)
    return run_dir


def validate_journal(root: Path, run_dir: Path) -> tuple[dict[str, Any], bool]:
    prepared = classic.load_json(run_dir / "prepared.json", "prep prepared")
    validate_prepared(run_dir, prepared)
    local = classic.load_json(run_dir / "prep-intent.json", "local prep intent")
    consumed = classic.load_json(consumed_path(root), "consumed prep intent")
    validate_intent(run_dir, prepared, local)
    validate_intent(run_dir, prepared, consumed)
    if local != consumed:
        raise PrepProbeError("prep intent chain differs")
    command_path = run_dir / "prep-command-result.json"
    probe_path = run_dir / "probe-result.json"
    if not lexists(command_path):
        if lexists(probe_path):
            raise PrepProbeError("prep probe lacks its command result")
        return prepared, False
    command_result = classic.load_json(command_path, "prep command result")
    success = validate_command_result(run_dir, local, command_result)
    if lexists(probe_path):
        probe = classic.load_json(probe_path, "prep probe result")
        if not success:
            raise PrepProbeError("prep probe lacks successful command result")
        validate_probe(run_dir, prepared, probe)
        proved = True
    else:
        proved = False
    return prepared, proved


def validate_final_result(
    run_dir: Path, prepared: dict[str, Any], proved: bool, value: dict[str, Any]
) -> dict[str, Any]:
    target = validate_prepared(run_dir, prepared)
    returned = value.get("returned_android")
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
        set(value)
        != {
            "schema",
            "version",
            "target",
            "returned_android",
            "prep_proved",
            "usb_role_switch_attempts",
            "fastboot_commands",
            "persistent_writes",
            "partition_operations",
            "replay_permitted",
            "verdict",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_twrp_fastbootd_prep_final_result_v1"
        or value.get("version") != VERSION
        or value.get("target") != target
        or not isinstance(returned, dict)
        or set(returned) != {"boot_id_sha256", "health"}
        or not _is_sha256(returned.get("boot_id_sha256"))
        or returned.get("boot_id_sha256") == target["recovery_boot_id_sha256"]
        or returned.get("health") != expected_health
        or value.get("prep_proved") is not proved
        or any(
            type(value.get(key)) is not int or value.get(key) != 0
            for key in (
                "usb_role_switch_attempts",
                "fastboot_commands",
                "persistent_writes",
                "partition_operations",
            )
        )
        or value.get("replay_permitted") is not False
        or value.get("verdict") != (FINAL_PASS if proved else FINAL_NO_PROOF)
        or not isinstance(value.get("at"), str)
    ):
        raise PrepProbeError("prep final result differs")
    return value


def finalize(root: Path, command: Command) -> dict[str, Any]:
    run_dir = resolve_run(root)
    final_path = run_dir / "final-result.json"
    prepared, proved = validate_journal(root, run_dir)
    if lexists(final_path):
        result = classic.load_json(final_path, "prep final result")
        validate_final_result(run_dir, prepared, proved, result)
        if lexists(guard_path(root)):
            release_guard(root, run_dir)
        return result
    check_guard(root, run_dir)
    support = require_support(root)
    if classic.object_sha256(support) != prepared["support_sha256"]:
        raise PrepProbeError("prep support changed before Android return")
    returned = classic.collect_android_health(command, classic.real_usb_inventory)
    target = prepared["target"]
    if (
        returned["serial_sha256"] != target["serial_sha256"]
        or returned["topology_sha256"] != target["topology_sha256"]
        or returned["other_serial_sha256"] != target["other_serial_sha256"]
        or returned["boot_id_sha256"] == target["recovery_boot_id_sha256"]
    ):
        raise PrepProbeError("returned Android identity or boot differs")
    result = {
        "schema": "s20plus_g986n_twrp_fastbootd_prep_final_result_v1",
        "version": VERSION,
        "target": target,
        "returned_android": {
            "boot_id_sha256": returned["boot_id_sha256"],
            "health": returned["health"],
        },
        "prep_proved": proved,
        "usb_role_switch_attempts": 0,
        "fastboot_commands": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "replay_permitted": False,
        "verdict": FINAL_PASS if proved else FINAL_NO_PROOF,
        "at": now(),
    }
    if require_support(root) != support:
        raise PrepProbeError("prep support changed after Android return")
    validate_final_result(run_dir, prepared, proved, result)
    base.durable_write(final_path, result)
    release_guard(root, run_dir)
    return result


def abort_pre_effect(root: Path) -> dict[str, Any]:
    guard = classic.load_json(guard_path(root), "prep probe guard")
    raw = guard.get("run_dir")
    if not isinstance(raw, str):
        raise PrepProbeError("prep probe guard run differs")
    run_dir = validate_run_dir(root, Path(raw))
    check_guard(root, run_dir)
    if lexists(consumed_path(root)) or lexists(run_dir / "prep-intent.json"):
        raise PrepProbeError("prep intent exists; abort is unavailable")
    if any(
        lexists(run_dir / name)
        for name in (
            "prep-command-result.json",
            "probe-result.json",
            "failure.json",
            "final-result.json",
        )
    ):
        raise PrepProbeError("prep effect evidence exists; abort is unavailable")
    result = {
        "schema": "s20plus_g986n_twrp_fastbootd_prep_abort_v1",
        "version": VERSION,
        "device_effects": 0,
        "persistent_writes": 0,
        "partition_operations": 0,
        "verdict": "ABORTED_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_BEFORE_EFFECT",
        "at": now(),
    }
    path = run_dir / "pre-effect-abort.json"
    if lexists(path):
        current = classic.load_json(path, "prep pre-effect abort")
        if (
            set(current)
            != {
                "schema",
                "version",
                "device_effects",
                "persistent_writes",
                "partition_operations",
                "verdict",
                "at",
            }
            or current.get("schema") != "s20plus_g986n_twrp_fastbootd_prep_abort_v1"
            or current.get("version") != VERSION
            or any(
                type(current.get(key)) is not int or current.get(key) != 0
                for key in ("device_effects", "persistent_writes", "partition_operations")
            )
            or current.get("verdict")
            != "ABORTED_S20PLUS_G986N_TWRP_FASTBOOTD_PREP_BEFORE_EFFECT"
            or not isinstance(current.get("at"), str)
        ):
            raise PrepProbeError("prep pre-effect abort differs")
        result = current
    else:
        base.durable_write(path, result)
    release_guard(root, run_dir)
    return result


def plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_twrp_fastbootd_prep_plan_v1",
        "version": VERSION,
        "target": "SM-G986N/y2q/y2qksx/G986NKSS8IYC2",
        "functionfs_mount_attempts": 1,
        "service_start_attempts": 1,
        "configfs_function_creations": 1,
        "usb_role_switch_attempts": 0,
        "fastboot_commands": 0,
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
        print("STOP_S20PLUS_TWRP_FASTBOOTD_PREP: reviewed activation is absent")
        return 2
    if args.abort_pre_effect:
        try:
            print(abort_pre_effect(root)["verdict"])
            return 0
        except Exception:
            print("FAIL_S20PLUS_TWRP_FASTBOOTD_PREP_ABORT_CLOSED")
            return 1
    if not args.operator_attended:
        print("STOP_S20PLUS_TWRP_FASTBOOTD_PREP: attendance is required")
        return 2
    if args.connected:
        run_dir = allocate_run_dir(root)
        command = classic.RawCommand(run_dir, "connected")
        try:
            result = connected_probe(root, run_dir, command)
        except ReturnRequiredError as exc:
            base.durable_write(
                run_dir / "failure.json",
                {
                    "schema": "s20plus_g986n_twrp_fastbootd_prep_failure_v1",
                    "version": VERSION,
                    "failure_sha256": hashlib.sha256(
                        f"{type(exc).__name__}:{exc}".encode()
                    ).hexdigest(),
                    "return_required": True,
                    "replay_permitted": False,
                    "at": now(),
                },
            )
            print("RECOVERY_PENDING_S20PLUS_TWRP_FASTBOOTD_PREP_PHYSICAL_REBOOT")
            return 1
        except Exception as exc:
            consumed = lexists(consumed_path(root)) or lexists(run_dir / "prep-intent.json")
            base.durable_write(
                run_dir / "failure.json",
                {
                    "schema": "s20plus_g986n_twrp_fastbootd_prep_failure_v1",
                    "version": VERSION,
                    "failure_sha256": hashlib.sha256(
                        f"{type(exc).__name__}:{exc}".encode()
                    ).hexdigest(),
                    "return_required": consumed,
                    "replay_permitted": False,
                    "at": now(),
                },
            )
            if not consumed and lexists(guard_path(root)):
                try:
                    release_guard(root, run_dir)
                except Exception:
                    pass
            print(
                "RECOVERY_PENDING_S20PLUS_TWRP_FASTBOOTD_PREP_PHYSICAL_REBOOT"
                if consumed
                else "FAIL_S20PLUS_TWRP_FASTBOOTD_PREP_PRE_EFFECT_CLOSED"
            )
            return 1
        print(result["verdict"])
        print("OPERATOR_ACTION_REQUIRED: use TWRP UI to reboot System")
        return 0
    try:
        run_dir = resolve_run(root)
        if lexists(run_dir / "final-result.json"):
            command = no_device_command
        else:
            command = classic.RawCommand(
                run_dir,
                "finalize",
                capture_dir=classic.allocate_finalize_capture_dir(run_dir),
            )
        result = finalize(root, command)
    except Exception:
        print("FAIL_S20PLUS_TWRP_FASTBOOTD_PREP_FINALIZE_CLOSED")
        return 1
    print(result["verdict"])
    print(f"result={run_dir / 'final-result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
