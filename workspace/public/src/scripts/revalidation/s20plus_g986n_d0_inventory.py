#!/usr/bin/env python3
"""Bounded unprivileged D0 onboarding inventory for one exact SM-G986N."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Callable


VERSION = "s20plus-g986n-d0-inventory-v1"
SCHEMA = "s20plus_g986n_d0_inventory_result_v1"
VERDICT = "PASS_S20PLUS_G986N_D0_ONBOARDING_READ_ONLY"
EXPECTED_MODEL = "SM-G986N"
EXPECTED_ADB_MODEL = "model:SM_G986N"
DEFAULT_ADB = Path("/usr/bin/adb")
EXPECTED_ADB_REALPATH = Path("/usr/lib/android-sdk/platform-tools/adb")
EXPECTED_ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s20plus-g986n-d0-inventory")
ACTIVE_INTENT_NAME = "active-intent.json"
MAX_TEXT_BYTES = 64 * 1024
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
DEVPATH_RE = re.compile(r"usb:[0-9]+-[0-9]+(?:\.[0-9]+)*")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SAFE_VALUE_RE = re.compile(r"[^\x00\r\n]{0,4096}")

PROPERTY_KEYS = (
    "model",
    "device",
    "product_name",
    "build_product",
    "fingerprint",
    "incremental",
    "build_id",
    "android_release",
    "sdk",
    "security_patch",
    "build_type",
    "build_tags",
    "build_characteristics",
    "bootloader",
    "boot_bootloader",
    "verified_boot_state",
    "flash_locked",
    "vbmeta_device_state",
    "warranty_bit",
    "boot_mode",
    "slot_suffix",
    "hardware",
    "board_platform",
    "soc_manufacturer",
    "soc_model",
    "cpu_abilist",
    "first_api_level",
    "boot_completed",
    "bootanim",
    "kernel_release",
    "machine",
    "selinux",
    "shell_identity",
    "boot_id",
)

REMOTE_SNAPSHOT = """set -eu
emit_prop() {
    printf '%s=' "$1"
    getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop build_product ro.build.product
emit_prop fingerprint ro.build.fingerprint
emit_prop incremental ro.build.version.incremental
emit_prop build_id ro.build.id
emit_prop android_release ro.build.version.release
emit_prop sdk ro.build.version.sdk
emit_prop security_patch ro.build.version.security_patch
emit_prop build_type ro.build.type
emit_prop build_tags ro.build.tags
emit_prop build_characteristics ro.build.characteristics
emit_prop bootloader ro.bootloader
emit_prop boot_bootloader ro.boot.bootloader
emit_prop verified_boot_state ro.boot.verifiedbootstate
emit_prop flash_locked ro.boot.flash.locked
emit_prop vbmeta_device_state ro.boot.vbmeta.device_state
emit_prop warranty_bit ro.boot.warranty_bit
emit_prop boot_mode ro.bootmode
emit_prop slot_suffix ro.boot.slot_suffix
emit_prop hardware ro.hardware
emit_prop board_platform ro.board.platform
emit_prop soc_manufacturer ro.soc.manufacturer
emit_prop soc_model ro.soc.model
emit_prop cpu_abilist ro.product.cpu.abilist
emit_prop first_api_level ro.product.first_api_level
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'kernel_release='; uname -r
printf 'machine='; uname -m
printf 'selinux='; getenforce
printf 'shell_identity='; id
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
"""


class InventoryError(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


class CommandRecorder:
    def __init__(self, command: Command):
        self.command = command
        self.host_command_count = 0
        self.inventory_command_count = 0
        self.selected_target_command_count = 0

    def run(
        self, argv: list[str], timeout: float, maximum: int
    ) -> tuple[int, bytes, bytes]:
        self.host_command_count += 1
        if len(argv) >= 3 and argv[-2:] == ["devices", "-l"]:
            self.inventory_command_count += 1
        if "-s" in argv:
            self.selected_target_command_count += 1
        return self.command(argv, timeout, maximum)

    def evidence(self) -> dict[str, int]:
        return {
            "host_command_count": self.host_command_count,
            "inventory_command_count": self.inventory_command_count,
            "selected_target_command_count": self.selected_target_command_count,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def bounded_command(argv: list[str], timeout: float, maximum: int) -> tuple[int, bytes, bytes]:
    if not argv or not 0.1 <= timeout <= 60 or not 1 <= maximum <= MAX_TEXT_BYTES:
        raise InventoryError("invalid host command bound")
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=error,
            close_fds=True,
        )
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if output.tell() + error.tell() > maximum:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                raise InventoryError("host command output exceeded its bound")
            if time.monotonic() >= deadline:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
                raise InventoryError("host command timed out")
            time.sleep(0.02)
        output.seek(0)
        error.seek(0)
        stdout = output.read(maximum + 1)
        stderr = error.read(maximum + 1)
    if len(stdout) + len(stderr) > maximum:
        raise InventoryError("host command output exceeded its bound")
    return process.returncode, stdout, stderr


def decode_command(
    result: tuple[int, bytes, bytes], label: str, *, permit_stderr: bool = False
) -> str:
    returncode, stdout, stderr = result
    if returncode != 0:
        raise InventoryError(f"{label} failed with rc={returncode}")
    if stderr and not permit_stderr:
        raise InventoryError(f"{label} produced stderr")
    try:
        return stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{label} is not UTF-8") from exc


def parse_inventory(text: str) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    serials: set[str] = set()
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2 or SERIAL_RE.fullmatch(fields[0]) is None:
            raise InventoryError("ADB inventory contains a malformed row")
        if fields[0] in serials:
            raise InventoryError("ADB inventory contains a duplicate serial row")
        serials.add(fields[0])
        metadata = frozenset(fields[2:])
        for prefix in ("model:", "device:", "product:"):
            if len([value for value in metadata if value.startswith(prefix)]) > 1:
                raise InventoryError(
                    f"ADB inventory contains conflicting {prefix[:-1]} metadata"
                )
        rows.append(
            {
                "serial": fields[0],
                "state": fields[1],
                "metadata": metadata,
            }
        )
    return tuple(rows)


def select_target(rows: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    matches = [row for row in rows if EXPECTED_ADB_MODEL in row["metadata"]]
    if len(matches) != 1 or matches[0]["state"] != "device":
        raise InventoryError(
            f"expected exactly one authorized {EXPECTED_MODEL}, found {len(matches)} exact rows"
        )
    selected = matches[0]
    for prefix in ("model:", "device:", "product:"):
        if len([value for value in selected["metadata"] if value.startswith(prefix)]) != 1:
            raise InventoryError(f"selected ADB row lacks exact {prefix[:-1]} metadata")
    return selected


def sanitized_inventory(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "serial_sha256": sha256_text(row["serial"]),
            "state": row["state"],
            "metadata": sorted(row["metadata"]),
        }
        for row in rows
    )


def parse_snapshot(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    allowed = set(PROPERTY_KEYS)
    for line in text.splitlines():
        if "=" not in line:
            raise InventoryError("property snapshot contains a malformed line")
        key, value = line.split("=", 1)
        if key not in allowed or key in values or SAFE_VALUE_RE.fullmatch(value) is None:
            raise InventoryError(f"property snapshot contains an invalid field: {key}")
        values[key] = value
    if set(values) != allowed:
        raise InventoryError("property snapshot fields are incomplete")
    if values["model"] != EXPECTED_MODEL:
        raise InventoryError("selected target property model mismatch")
    if not values["device"] or not values["incremental"] or not values["fingerprint"]:
        raise InventoryError("selected target public identity is incomplete")
    if values["boot_completed"] != "1" or values["bootanim"] != "stopped":
        raise InventoryError("selected target Android boot is not stable")
    if BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise InventoryError("selected target boot ID is malformed")
    return values


def tool_receipt(adb: Path) -> dict[str, Any]:
    resolved = adb.resolve(strict=True)
    digest = hashlib.sha256()
    size = 0
    descriptor = os.open(resolved, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111:
            raise InventoryError("ADB tool is not an executable regular file")
        while chunk := os.read(descriptor, 1024 * 1024):
            size += len(chunk)
            if size > 128 * 1024 * 1024:
                raise InventoryError("ADB tool exceeds its receipt bound")
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.stat(resolved, follow_symlinks=False)
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise InventoryError("ADB tool changed while its identity was read")
    receipt = {
        "path": str(resolved),
        "device": after.st_dev,
        "inode": after.st_ino,
        "mtime_ns": after.st_mtime_ns,
        "size": size,
        "sha256": digest.hexdigest(),
    }
    if resolved != EXPECTED_ADB_REALPATH or receipt["sha256"] != EXPECTED_ADB_SHA256:
        raise InventoryError("ADB tool does not match the reviewed canonical identity")
    return receipt


def _adb_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._]", "_", value)


def validate_snapshot_binding(snapshot: dict[str, str], selected: dict[str, Any]) -> None:
    expected = {
        f"model:{_adb_token(snapshot['model'])}",
        f"device:{_adb_token(snapshot['device'])}",
        f"product:{_adb_token(snapshot['product_name'])}",
    }
    if not expected <= selected["metadata"]:
        raise InventoryError("selected target snapshot conflicts with ADB metadata")


def collect(
    command: Command = bounded_command,
    *,
    recorder: CommandRecorder | None = None,
) -> dict[str, Any]:
    recorder = recorder or CommandRecorder(command)
    run_command = recorder.run
    receipt = tool_receipt(DEFAULT_ADB)
    exact_adb = receipt["path"]
    version = decode_command(run_command([exact_adb, "version"], 10, MAX_TEXT_BYTES), "adb version")

    first_text = decode_command(
        run_command([exact_adb, "devices", "-l"], 10, MAX_TEXT_BYTES),
        "initial ADB inventory",
    )
    first_rows = parse_inventory(first_text)
    selected = select_target(first_rows)
    serial = selected["serial"]

    devpath = decode_command(
        run_command([exact_adb, "-s", serial, "get-devpath"], 10, MAX_TEXT_BYTES),
        "selected target devpath",
    )
    if DEVPATH_RE.fullmatch(devpath) is None:
        raise InventoryError("selected target USB topology is malformed")

    first_snapshot = parse_snapshot(
        decode_command(
            run_command(
                [exact_adb, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
                20,
                MAX_TEXT_BYTES,
            ),
            "first selected target snapshot",
        )
    )
    second_snapshot = parse_snapshot(
        decode_command(
            run_command(
                [exact_adb, "-s", serial, "exec-out", "sh", "-c", REMOTE_SNAPSHOT],
                20,
                MAX_TEXT_BYTES,
            ),
            "second selected target snapshot",
        )
    )
    if first_snapshot != second_snapshot:
        raise InventoryError("selected target snapshot changed during collection")
    validate_snapshot_binding(first_snapshot, selected)

    final_text = decode_command(
        run_command([exact_adb, "devices", "-l"], 10, MAX_TEXT_BYTES),
        "final ADB inventory",
    )
    final_rows = parse_inventory(final_text)
    final_selected = select_target(final_rows)
    if serial != final_selected["serial"] or sanitized_inventory(first_rows) != sanitized_inventory(final_rows):
        raise InventoryError("selected target or ADB inventory changed during collection")
    if tool_receipt(Path(exact_adb)) != receipt:
        raise InventoryError("ADB tool changed during collection")
    counts = recorder.evidence()
    if counts != {
        "host_command_count": 6,
        "inventory_command_count": 2,
        "selected_target_command_count": 3,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }:
        raise InventoryError("D0 command counts do not match the fixed plan")

    public_properties = dict(first_snapshot)
    boot_id = public_properties.pop("boot_id")
    selected_hash = sha256_text(serial)
    other_hashes = sorted(
        sha256_text(row["serial"]) for row in first_rows if row["serial"] != serial
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "connected-read-only",
        "target": {
            "model": EXPECTED_MODEL,
            "adb_serial_sha256": selected_hash,
            "usb_topology_sha256": sha256_text(devpath),
            "other_serial_sha256": other_hashes,
            "inventory_sha256": sha256_text(
                json.dumps(sanitized_inventory(first_rows), sort_keys=True)
            ),
        },
        "properties": public_properties,
        "boot_id_sha256": sha256_text(boot_id),
        "usb_debugging_verified": True,
        "adb_authorization_state": "device",
        "host_tool": {
            **receipt,
            "version_output_sha256": sha256_text(version),
        },
        **counts,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "verdict": VERDICT,
    }


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    base.mkdir(parents=True, exist_ok=True)
    candidate = requested or base / (
        "d0-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{time.time_ns()}"
    )
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise InventoryError("run directory is outside the private S20+ D0 root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def durable_write(path: Path, result: dict[str, Any]) -> None:
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise InventoryError("short durable result write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


def failure_result(
    recorder: CommandRecorder,
    exc: Exception,
    intent_sha256: str | None = None,
) -> dict[str, Any]:
    signature = f"{type(exc).__name__}:{exc}"
    return {
        "schema": "s20plus_g986n_d0_inventory_failure_v1",
        "version": VERSION,
        "mode": "connected-read-only-failed",
        "failure_class": type(exc).__name__,
        "failure_signature_sha256": sha256_text(signature),
        "intent_sha256": intent_sha256,
        **recorder.evidence(),
        "device_contact_started": recorder.inventory_command_count > 0,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "verdict": "FAIL_S20PLUS_G986N_D0_STOP_NO_RETRY",
    }


def arm_intent(root: Path, run_dir: Path, adb_receipt: dict[str, Any]) -> tuple[Path, str]:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    guard = base / ACTIVE_INTENT_NAME
    intent = {
        "schema": "s20plus_g986n_d0_inventory_intent_v1",
        "version": VERSION,
        "expected_model": EXPECTED_MODEL,
        "run_dir": str(run_dir.relative_to(base)),
        "adb": adb_receipt,
        "planned_host_command_count": 6,
        "planned_inventory_command_count": 2,
        "planned_selected_target_command_count": 3,
        "planned_other_target_command_count": 0,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
    }
    durable_write(run_dir / "intent.json", intent)
    try:
        durable_write(guard, intent)
    except FileExistsError as exc:
        raise InventoryError(
            "an S20+ D0 intent already exists; connected replay is refused"
        ) from exc
    intent_sha256 = hashlib.sha256(
        json.dumps(intent, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    ).hexdigest()
    return guard, intent_sha256


def dry_run_plan(adb: Path) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_d0_inventory_plan_v1",
        "version": VERSION,
        "mode": "dry-run-device-hidden",
        "expected_model": EXPECTED_MODEL,
        "adb_path": str(adb),
        "target_commands": 3,
        "other_target_commands": 0,
        "device_writes": False,
        "root_used": False,
        "reboot_requested": False,
        "mode_transition_requested": False,
        "payload_transfer": False,
        "partition_access": False,
        "live_authorized": False,
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connected", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    if not args.connected:
        print(json.dumps(dry_run_plan(DEFAULT_ADB), indent=2, sort_keys=True))
        return 0
    run_dir = allocate_run_dir(root, args.run_dir)
    recorder = CommandRecorder(bounded_command)
    intent_sha256: str | None = None
    try:
        _guard, intent_sha256 = arm_intent(
            root, run_dir, tool_receipt(DEFAULT_ADB)
        )
        result = collect(recorder=recorder)
        result["intent_sha256"] = intent_sha256
        durable_write(run_dir / "result.json", result)
    except Exception as exc:
        try:
            durable_write(
                run_dir / "failure.json",
                failure_result(recorder, exc, intent_sha256),
            )
        except Exception:
            print("FAIL_S20PLUS_G986N_D0_EVIDENCE_WRITE")
            return 1
        print("FAIL_S20PLUS_G986N_D0_STOP_NO_RETRY")
        print(f"failure={run_dir / 'failure.json'}")
        return 1
    print(VERDICT)
    print(f"result={run_dir / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
