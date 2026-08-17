#!/usr/bin/env python3
"""Raw-first S22+ P3.19 Max77705 attribute-name Stage A D0 observer."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any

import device_action_d0_v2 as d0
import device_action_f1_v2 as f1
import device_action_raw_capture_v1 as raw_capture
import s22plus_fyg8_max77705_sysfs_d0 as prior


VERSION = "s22plus-fyg8-p319-max77705-attribute-stage-a-v2"
SCHEMA = "s22plus_fyg8_max77705_attribute_stage_a_d0_v2"
STOP_SCHEMA = "s22plus_fyg8_max77705_attribute_stage_a_d0_stop_v2"
VERDICT = "PASS_S22PLUS_FYG8_MAX77705_ATTRIBUTE_STAGE_A_D0"
STOP_VERDICT = "STOP_S22PLUS_FYG8_MAX77705_ATTRIBUTE_STAGE_A_D0"
DEFAULT_RUN_ROOT = Path(
    "workspace/private/runs/s22plus-fyg8-max77705-attribute-stage-a-d0"
)
MAX_STAGE_A_BYTES = 32 * 1024
ASCII_DECIMAL_RE = re.compile(r"[0-9]+")
ENTRY_NAME_RE = re.compile(r"[A-Za-z0-9._:+-]+")
ENTRY_KINDS = {"symlink", "directory", "regular", "other"}

STAGE_A_SCRIPT = r"""set -eu
platform=/sys/bus/platform/devices/994000.i2c
[ -d "$platform" ] || exit 20
adapter_count=0
adapter=
for candidate in "$platform"/i2c-*; do
    [ -d "$candidate" ] || continue
    name=${candidate##*/}
    suffix=${name#i2c-}
    [ "$suffix" != "$name" ] || continue
    case "$suffix" in ''|*[!0-9]*) continue ;; esac
    adapter_count=$((adapter_count + 1))
    adapter=$candidate
done
[ "$adapter_count" -eq 1 ] || exit 21
client_count=0
client=
for candidate in "$adapter"/*-0066; do
    [ -d "$candidate" ] || continue
    name=${candidate##*/}
    prefix=${name%-0066}
    [ "$prefix" != "$name" ] || continue
    case "$prefix" in ''|*[!0-9]*) continue ;; esac
    client_count=$((client_count + 1))
    client=$candidate
done
[ "$client_count" -eq 1 ] || exit 22
printf 'adapter\t%s\n' "${adapter##*/}"
printf 'client\t%s\n' "${client##*/}"
entry_count=0
regmap_count=0
regmap_kind=absent
for entry in "$client"/* "$client"/.[!.]* "$client"/..?*; do
    [ -e "$entry" ] || [ -L "$entry" ] || continue
    name=${entry##*/}
    case "$name" in ''|*[!A-Za-z0-9._:+-]*) exit 23 ;; esac
    if [ -L "$entry" ]; then
        kind=symlink
    elif [ -d "$entry" ]; then
        kind=directory
    elif [ -f "$entry" ]; then
        kind=regular
    else
        kind=other
    fi
    entry_count=$((entry_count + 1))
    if [ "$name" = regmap ]; then
        regmap_count=$((regmap_count + 1))
        regmap_kind=$kind
    fi
    printf 'entry\t%s\t%s\n' "$name" "$kind"
done
printf 'entry_count\t%s\n' "$entry_count"
printf 'regmap_count\t%s\n' "$regmap_count"
printf 'regmap_kind\t%s\n' "$regmap_kind"
"""


class StageAError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _identity(root: Path, path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    try:
        rendered = path.relative_to(root).as_posix()
    except ValueError:
        rendered = str(path)
    return {
        "path": rendered,
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _render_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _strict_uint(value: str, label: str) -> int:
    if ASCII_DECIMAL_RE.fullmatch(value) is None:
        raise StageAError(f"Stage A {label} is not canonical ASCII decimal")
    parsed = int(value)
    if str(parsed) != value or parsed > 4096:
        raise StageAError(f"Stage A {label} is outside its canonical bound")
    return parsed


def parse_stage_a(handle: raw_capture.RawCaptureHandle) -> dict[str, Any]:
    """Parse only a finalized durable raw handle, never a live byte stream."""

    try:
        payload = raw_capture.read_stdout(handle, maximum=MAX_STAGE_A_BYTES)
        raw_capture.require_success(handle)
    except raw_capture.RawCaptureError as exc:
        raise StageAError(f"Stage A acquisition did not complete: {exc}") from exc
    if not payload:
        raise StageAError("Stage A stdout is empty")
    try:
        text = payload.decode("ascii", "strict")
    except UnicodeDecodeError as exc:
        raise StageAError("Stage A stdout is not ASCII") from exc
    if not text.endswith("\n"):
        raise StageAError("Stage A stdout lacks its final line delimiter")

    adapter_rows: list[str] = []
    client_rows: list[str] = []
    entries: list[dict[str, str]] = []
    entry_count_rows: list[int] = []
    regmap_count_rows: list[int] = []
    regmap_kind_rows: list[str] = []
    for index, line in enumerate(text.splitlines()):
        fields = line.split("\t")
        if len(fields) == 2 and fields[0] == "adapter":
            adapter_rows.append(fields[1])
        elif len(fields) == 2 and fields[0] == "client":
            client_rows.append(fields[1])
        elif len(fields) == 3 and fields[0] == "entry":
            name, kind = fields[1:]
            if ENTRY_NAME_RE.fullmatch(name) is None:
                raise StageAError(f"Stage A entry[{index}] name is invalid")
            if kind not in ENTRY_KINDS:
                raise StageAError(f"Stage A entry[{index}] kind is invalid")
            entries.append({"name": name, "kind": kind})
        elif len(fields) == 2 and fields[0] == "entry_count":
            entry_count_rows.append(_strict_uint(fields[1], "entry_count"))
        elif len(fields) == 2 and fields[0] == "regmap_count":
            regmap_count_rows.append(_strict_uint(fields[1], "regmap_count"))
        elif len(fields) == 2 and fields[0] == "regmap_kind":
            regmap_kind_rows.append(fields[1])
        else:
            raise StageAError(f"Stage A row {index} is malformed")

    if len(adapter_rows) != 1:
        raise StageAError("Stage A adapter row cardinality is not one")
    if re.fullmatch(r"i2c-[0-9]+", adapter_rows[0]) is None:
        raise StageAError("Stage A adapter name is not canonical")
    if len(client_rows) != 1:
        raise StageAError("Stage A client row cardinality is not one")
    if re.fullmatch(r"[0-9]+-0066", client_rows[0]) is None:
        raise StageAError("Stage A client name is not canonical")
    if len(entry_count_rows) != 1:
        raise StageAError("Stage A entry_count row cardinality is not one")
    if not entries:
        raise StageAError("Stage A entry inventory is empty")
    if len(entries) != entry_count_rows[0]:
        raise StageAError("Stage A entry_count differs from emitted entries")
    names = [row["name"] for row in entries]
    if len(set(names)) != len(names):
        raise StageAError("Stage A entry inventory contains duplicate names")
    if len(regmap_count_rows) != 1:
        raise StageAError("Stage A regmap_count row cardinality is not one")
    if regmap_count_rows[0] not in {0, 1}:
        raise StageAError("Stage A regmap_count is not zero or one")
    if len(regmap_kind_rows) != 1:
        raise StageAError("Stage A regmap_kind row cardinality is not one")
    regmap_rows = [row for row in entries if row["name"] == "regmap"]
    if len(regmap_rows) != regmap_count_rows[0]:
        raise StageAError("Stage A regmap_count differs from exact-name rows")
    if not regmap_rows and regmap_kind_rows[0] != "absent":
        raise StageAError("Stage A absent regmap has a non-absent kind")
    if regmap_rows and regmap_kind_rows[0] != regmap_rows[0]["kind"]:
        raise StageAError("Stage A regmap kind differs from its inode type")

    entries.sort(key=lambda row: row["name"])
    return {
        "adapter_name": adapter_rows[0],
        "client_name": client_rows[0],
        "entry_count": len(entries),
        "entries": entries,
        "regmap_exact_entry_count": len(regmap_rows),
        "regmap_exact_entry_kind": regmap_kind_rows[0],
        "regmap_named_entries": [
            row for row in entries if "regmap" in row["name"].lower()
        ],
        "raw_capture_receipt": _identity(repo_root(), handle.receipt_path),
        "raw_stdout": {
            "path": _render_path(repo_root(), handle.stdout_path),
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        },
    }


def stage_a_safety_contract(script: str = STAGE_A_SCRIPT) -> dict[str, Any]:
    forbidden = (
        "cat ",
        " od ",
        " dd ",
        " hexdump ",
        " xxd ",
        "<",
        ">",
        "/sys/kernel/debug",
        "/dev/i2c",
        "regmap/",
        "data=",
        " modprobe",
        " insmod",
        " rmmod",
        " reboot",
        " setprop",
    )
    required = (
        "/sys/bus/platform/devices/994000.i2c",
        '"$platform"/i2c-*',
        '"$adapter"/*-0066',
        'if [ -L "$entry" ]',
        'elif [ -d "$entry" ]',
        'elif [ -f "$entry" ]',
        "printf 'entry\\t%s\\t%s\\n'",
    )
    passed = not any(token in script for token in forbidden) and all(
        token in script for token in required
    )
    return {
        "result": "pass" if passed else "fail",
        "script_size": len(script.encode("ascii")),
        "script_sha256": hashlib.sha256(script.encode("ascii")).hexdigest(),
        "attribute_body_open_count": 0,
        "attribute_body_read_count": 0,
        "i2c_device_access_count": 0,
        "debugfs_access_count": 0,
        "sysfs_write_count": 0,
        "reboot_count": 0,
        "module_action_count": 0,
        "only_directory_glob_inode_test_and_printf": True,
    }


def _inventory_handle(
    adb: Path,
    capture_dir: Path,
    name: str,
) -> tuple[raw_capture.RawCaptureHandle, str, prior.Selection]:
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "devices", "-l"],
            capture_dir,
            name,
            timeout=10,
            stdout_maximum=d0.MAX_TEXT_OUTPUT,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
        text = raw_capture.decode_success_stdout(
            handle, maximum=d0.MAX_TEXT_OUTPUT, strip=False
        )
    except raw_capture.RawCaptureError as exc:
        raise StageAError(f"Stage A ADB inventory failed: {exc}") from exc
    return handle, text, prior.select_exact_s22(text)


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).absolute()
    base.mkdir(parents=True, exist_ok=True)
    if base.is_symlink() or base.resolve(strict=True) != base:
        raise StageAError("Stage A run root is indirect")
    candidate = requested or base / (
        "d0-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{time.time_ns()}"
    )
    candidate = candidate if candidate.is_absolute() else root / candidate
    direct = candidate.absolute()
    if direct.parent != base or direct.exists() or direct.is_symlink():
        raise StageAError("Stage A run directory is not a new direct child")
    direct.mkdir(mode=0o700)
    if direct.resolve(strict=True) != direct:
        raise StageAError("Stage A run directory became indirect")
    d0._fsync_dir(direct.parent)
    return direct


def collect(
    root: Path,
    profile_path: Path,
    adb_path: Path,
    run_dir: Path,
) -> dict[str, Any]:
    safety = stage_a_safety_contract()
    if safety["result"] != "pass":
        raise StageAError("Stage A directory-only command contract failed")
    profile, _payload = f1.load_json(profile_path, "S22+ FYG8 target profile")
    f1.validate_profile(profile)
    if profile.get("profile_id") != "s22plus-fyg8":
        raise StageAError("Stage A profile differs")
    adb = adb_path.resolve(strict=True)
    client = d0.AdbReadOnlyClient(
        adb,
        expected_model=prior.EXPECTED_MODEL,
        expected_device=prior.EXPECTED_DEVICE,
    )
    client.bind_raw_capture_dir(run_dir)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-stage-a")
    host_tool = client.receipt()
    initial_usb = d0.usb_snapshot(
        d0.DEFAULT_USB_ROOT, profile["target"]["download"]
    )
    if (
        not initial_usb["enumerated_devices"]
        or initial_usb["download_endpoint_count"] != 0
    ):
        raise StageAError("Stage A initial USB state is not Android-only")
    _initial_handle, initial_text, selection = _inventory_handle(
        adb, capture_dir, "0000-adb-inventory-initial"
    )
    serial = selection.serial
    topology = client.topology(serial)
    properties = client.properties(serial)
    prior._exact_identity(properties)
    root_health = client.root_health(serial)
    health = d0.validate_health(prior._ProfileView(profile), properties, root_health, True)

    try:
        stage_handle = raw_capture.acquire_command(
            [str(adb), "-s", serial, "exec-out", "su", "-c", STAGE_A_SCRIPT],
            capture_dir,
            "0001-stage-a-directory-inventory",
            timeout=20,
            stdout_maximum=MAX_STAGE_A_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
    except raw_capture.RawCaptureError as exc:
        raise StageAError(f"Stage A raw acquisition failed: {exc}") from exc
    observation = parse_stage_a(stage_handle)

    _final_handle, final_text, final_selection = _inventory_handle(
        adb, capture_dir, "0002-adb-inventory-final"
    )
    final_topology = client.topology(final_selection.serial)
    final_properties = client.properties(final_selection.serial)
    final_usb = d0.usb_snapshot(
        d0.DEFAULT_USB_ROOT, profile["target"]["download"]
    )
    if (
        final_selection.serial_sha256 != selection.serial_sha256
        or final_selection.other_serial_sha256 != selection.other_serial_sha256
        or final_text != initial_text
        or final_topology != topology
        or final_properties != properties
        or final_usb != initial_usb
    ):
        raise StageAError("Stage A target, health, inventory, or USB state changed")

    regmap_ready = (
        observation["regmap_exact_entry_count"] == 1
        and observation["regmap_exact_entry_kind"] == "regular"
    )
    stage_b_target = (
        "/sys/bus/platform/devices/994000.i2c/"
        f"{observation['adapter_name']}/{observation['client_name']}/regmap"
        if regmap_ready
        else None
    )
    kernfs_dir = root / (
        "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
        "kernel_platform/common/fs/kernfs/dir.c"
    )
    sysfs_file = root / (
        "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
        "kernel_platform/common/fs/sysfs/file.c"
    )
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "verdict": VERDICT,
        "captured_at_utc": _utc_now(),
        "target": prior.TARGET,
        "target_evidence": {
            "adb_serial_sha256": selection.serial_sha256,
            "adb_topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
            "inventory_row_count": len(selection.rows),
            "other_target_count": len(selection.other_serial_sha256),
            "other_serial_sha256": list(selection.other_serial_sha256),
            "other_target_command_count": 0,
            "identity": {
                "model": properties["model"],
                "device": properties["device"],
                "incremental": properties["incremental"],
            },
        },
        "health": health,
        "host_tool": host_tool,
        "usb": {"initial": initial_usb, "final": final_usb},
        "command_contract": safety,
        "transaction_proof": {
            "derived_stage_a_i2c_transaction_count": 0,
            "global_background_i2c_activity_measured": False,
            "kernfs_dir_source": _identity(root, kernfs_dir),
            "sysfs_file_source": _identity(root, sysfs_file),
            "basis": (
                "The exact command performs only kernfs directory enumeration, "
                "inode type tests, shell integer/string operations, and stdout "
                "printf; sysfs show is reached only from an attribute-file read."
            ),
        },
        "observation": observation,
        "stage_b": {
            "single_attribute_candidate_count": 1 if regmap_ready else 0,
            "single_attribute_target": stage_b_target,
            "status": (
                "SINGLE_REGMAP_ATTRIBUTE_READY"
                if regmap_ready
                else (
                    "REGMAP_ENTRY_ABSENT"
                    if observation["regmap_exact_entry_count"] == 0
                    else "REGMAP_ENTRY_NOT_A_REGULAR_ATTRIBUTE"
                )
            ),
            "stage_b_executed": False,
        },
        "device_contact": True,
        "device_writes": False,
        "candidate_used": False,
        "reboot_requested": False,
        "module_action": False,
        "service_action": False,
        "partition_transfer": False,
        "adb_target_command_count": 6,
        "other_target_command_count": 0,
        "d1_authorized": False,
        "f1_authorized": False,
    }
    d0.durable_create(run_dir / "result.json", result)
    return result


def _stop_value(reason: str, raw_receipt: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "schema": STOP_SCHEMA,
        "version": VERSION,
        "verdict": STOP_VERDICT,
        "captured_at_utc": _utc_now(),
        "reason": reason,
        "last_raw_capture": raw_receipt,
        "device_writes": False,
        "candidate_used": False,
        "reboot_requested": False,
        "partition_transfer": False,
        "retry_permitted_by_result": False,
        "f1_authorized": False,
    }


def _last_capture(root: Path, run_dir: Path) -> dict[str, Any] | None:
    paths = sorted(run_dir.glob("**/*.capture.json"))
    return _identity(root, paths[-1]) if paths else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--collect", action="store_true")
    parser.add_argument("--profile", type=Path, default=prior.DEFAULT_PROFILE)
    parser.add_argument("--adb", type=Path, default=prior.DEFAULT_ADB)
    parser.add_argument("--run-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.validate:
        value = {
            "schema": SCHEMA,
            "version": VERSION,
            "verdict": "PASS_S22PLUS_FYG8_MAX77705_ATTRIBUTE_STAGE_A_H0_READY",
            "safety": stage_a_safety_contract(),
            "device_contact": False,
            "live_authorized": False,
        }
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if value["safety"]["result"] == "pass" else 2
    root = repo_root()
    run_dir = allocate_run_dir(root, args.run_dir)
    try:
        result = collect(
            root,
            _resolve(root, args.profile),
            _resolve(root, args.adb),
            run_dir,
        )
    except (
        StageAError,
        prior.InventoryError,
        d0.D0Error,
        f1.F1V2Error,
        raw_capture.RawCaptureError,
        OSError,
    ) as exc:
        reason = str(exc)
        stop = _stop_value(reason, _last_capture(root, run_dir))
        try:
            d0.durable_create(run_dir / "result.json", stop)
        except (d0.D0Error, OSError):
            pass
        print(f"P3.19 Stage A D0 error: {reason}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
