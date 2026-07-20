#!/usr/bin/env python3
"""Reusable connected read-only qualification for Device Action Process v2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import device_action_f1_v2 as f1


D0_VERSION = "device-action-d0-v2-1"
D0_RESULT_SCHEMA = "device_action_d0_result_v2"
D0_VERDICT = "PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/device-action-d0-v2")
DEFAULT_USB_ROOT = Path("/sys/bus/usb/devices")
MAX_TEXT_OUTPUT = 64 * 1024
MAX_OBSERVER_BYTES = 64 * 1024 * 1024
SERIAL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
DEVPATH_RE = re.compile(r"usb:[0-9]+-[0-9]+(?:\.[0-9]+)*")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
REMOTE_PATH_RE = re.compile(r"/(?:proc|sys)/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+")


class D0Error(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def _terminate(process: subprocess.Popen[Any]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)


def bounded_command(
    argv: list[str], *, timeout: float, maximum: int = MAX_TEXT_OUTPUT
) -> CommandResult:
    """Run one argv-only host command with bounded time and captured bytes."""

    if not argv or not 0.1 <= timeout <= 300 or not 1 <= maximum <= 128 * 1024 * 1024:
        raise D0Error("invalid command bound")
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as error:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=error,
            close_fds=True,
        )
        deadline = time.monotonic() + timeout
        exceeded = False
        timed_out = False
        while process.poll() is None:
            if os.fstat(output.fileno()).st_size + os.fstat(error.fileno()).st_size > maximum:
                exceeded = True
                _terminate(process)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _terminate(process)
                break
            time.sleep(0.02)
        output.seek(0)
        error.seek(0)
        stdout = output.read(maximum + 1)
        stderr = error.read(maximum + 1)
    if timed_out:
        raise D0Error(f"command timed out: {Path(argv[0]).name}")
    if exceeded or len(stdout) + len(stderr) > maximum:
        raise D0Error(f"command output exceeded bound: {Path(argv[0]).name}")
    return CommandResult(process.returncode, stdout, stderr)


def _decode(result: CommandResult, label: str) -> str:
    if result.returncode != 0:
        raise D0Error(f"{label} failed with rc={result.returncode}")
    if result.stderr:
        raise D0Error(f"{label} produced stderr")
    try:
        return result.stdout.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise D0Error(f"{label} output is not UTF-8") from exc


def _hash_regular_file(path: Path, maximum: int = 128 * 1024 * 1024) -> dict[str, Any]:
    direct = path.resolve(strict=True)
    entry = os.stat(direct, follow_symlinks=False)
    if not stat.S_ISREG(entry.st_mode):
        raise D0Error(f"host tool is not regular: {direct}")
    digest = hashlib.sha256()
    total = 0
    with direct.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(chunk)
            if total > maximum:
                raise D0Error(f"host tool exceeds bound: {direct}")
            digest.update(chunk)
    return {"path": str(direct), "size": total, "sha256": digest.hexdigest()}


def _read_stable(path: Path, maximum: int) -> bytes:
    if path.is_symlink():
        raise D0Error("observer output is indirect")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise D0Error("observer output is not regular")
        payload = bytearray()
        while chunk := os.read(descriptor, 1024 * 1024):
            payload.extend(chunk)
            if len(payload) > maximum:
                raise D0Error("observer output exceeds its read bound")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(path)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise D0Error("observer output changed while reading")
    return bytes(payload)


def _parse_key_values(text: str, required: set[str], label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            raise D0Error(f"{label} contains a malformed line")
        key, value = line.split("=", 1)
        if key in values or key not in required or not value or len(value) > 4096:
            raise D0Error(f"{label} contains an invalid field: {key}")
        values[key] = value
    if set(values) != required:
        raise D0Error(f"{label} fields are incomplete")
    return values


class ReadOnlyClient(Protocol):
    def receipt(self) -> dict[str, Any]: ...
    def one_serial(self) -> str: ...
    def topology(self, serial: str) -> str: ...
    def properties(self, serial: str) -> dict[str, str]: ...
    def root_health(self, serial: str) -> dict[str, str]: ...
    def capture(self, serial: str, source: str, destination: Path) -> dict[str, Any]: ...


class AdbReadOnlyClient:
    PROPERTY_FIELDS = {
        "model",
        "device",
        "bootloader",
        "incremental",
        "boot_completed",
        "bootanim",
        "verified_boot_state",
        "boot_id",
        "kernel_release",
    }

    def __init__(self, adb: Path):
        resolved = adb.resolve(strict=True)
        if not os.access(resolved, os.X_OK):
            raise D0Error("ADB is not executable")
        self.adb = resolved
        self._receipt = _hash_regular_file(resolved)

    def _run(self, arguments: list[str], label: str, timeout: float = 20) -> str:
        return _decode(
            bounded_command([str(self.adb), *arguments], timeout=timeout), label
        )

    def receipt(self) -> dict[str, Any]:
        version = self._run(["version"], "adb version", 10)
        return {
            **self._receipt,
            "version_output_sha256": hashlib.sha256(version.encode()).hexdigest(),
        }

    def one_serial(self) -> str:
        text = self._run(["devices", "-l"], "adb devices", 10)
        rows: list[tuple[str, str]] = []
        for line in text.splitlines():
            if not line or line.startswith("List of devices attached"):
                continue
            fields = line.split()
            if len(fields) < 2:
                raise D0Error("adb inventory contains a malformed row")
            rows.append((fields[0], fields[1]))
        if len(rows) != 1 or rows[0][1] != "device":
            raise D0Error(f"expected exactly one authorized ADB target, found {len(rows)}")
        serial = rows[0][0]
        if SERIAL_RE.fullmatch(serial) is None:
            raise D0Error("ADB serial has an unsafe shape")
        return serial

    def topology(self, serial: str) -> str:
        value = self._run(["-s", serial, "get-devpath"], "adb get-devpath", 10)
        if DEVPATH_RE.fullmatch(value) is None:
            raise D0Error("ADB USB topology is malformed")
        return value

    def _shell(self, serial: str, command: str, *, root: bool, timeout: float) -> str:
        remote = f"su -c {shlex.quote(command)}" if root else f"sh -c {shlex.quote(command)}"
        return self._run(["-s", serial, "shell", remote], "adb read-only shell", timeout)

    def properties(self, serial: str) -> dict[str, str]:
        command = """printf 'model='; getprop ro.product.model
printf 'device='; getprop ro.product.device
printf 'bootloader='; getprop ro.boot.bootloader
printf 'incremental='; getprop ro.build.version.incremental
printf 'boot_completed='; getprop sys.boot_completed
printf 'bootanim='; getprop init.svc.bootanim
printf 'verified_boot_state='; getprop ro.boot.verifiedbootstate
printf 'boot_id='; cat /proc/sys/kernel/random/boot_id
printf 'kernel_release='; uname -r"""
        return _parse_key_values(
            self._shell(serial, command, root=False, timeout=20),
            self.PROPERTY_FIELDS,
            "Android properties",
        )

    def root_health(self, serial: str) -> dict[str, str]:
        command = """printf 'root='; id
printf 'boot='; sha256sum /dev/block/by-name/boot | cut -d' ' -f1
printf 'vendor_boot='; sha256sum /dev/block/by-name/vendor_boot | cut -d' ' -f1
printf 'dtbo='; sha256sum /dev/block/by-name/dtbo | cut -d' ' -f1
printf 'recovery='; sha256sum /dev/block/by-name/recovery | cut -d' ' -f1"""
        return _parse_key_values(
            self._shell(serial, command, root=True, timeout=180),
            {"root", "boot", "vendor_boot", "dtbo", "recovery"},
            "root health",
        )

    def capture(self, serial: str, source: str, destination: Path) -> dict[str, Any]:
        if REMOTE_PATH_RE.fullmatch(source) is None or ".." in Path(source).parts:
            raise D0Error("observer source is not a bounded procfs/sysfs path")
        remote = f"su -c {shlex.quote('cat ' + shlex.quote(source))}"
        stderr_path = destination.with_suffix(destination.suffix + ".stderr")
        started = time.monotonic()
        with destination.open("xb") as output, stderr_path.open("xb") as error:
            process = subprocess.Popen(
                [str(self.adb), "-s", serial, "exec-out", remote],
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=error,
                close_fds=True,
            )
            deadline = started + 180
            while process.poll() is None:
                if output.tell() > MAX_OBSERVER_BYTES or error.tell() > MAX_TEXT_OUTPUT:
                    _terminate(process)
                    raise D0Error("observer output exceeded its bound")
                if time.monotonic() >= deadline:
                    _terminate(process)
                    raise D0Error("observer timed out before EOF")
                time.sleep(0.05)
            output.flush()
            error.flush()
            os.fsync(output.fileno())
            os.fsync(error.fileno())
            returncode = process.returncode
        _fsync_dir(destination.parent)
        if returncode != 0 or stderr_path.stat().st_size:
            raise D0Error("observer capture failed or produced stderr")
        payload = _read_stable(destination, MAX_OBSERVER_BYTES)
        if not payload or len(payload) > MAX_OBSERVER_BYTES:
            raise D0Error("observer output is empty or oversized")
        return {
            "path": str(destination),
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "read_to_eof": True,
            "stderr_bytes": 0,
            "elapsed_sec": round(time.monotonic() - started, 6),
        }


def _read_small(path: Path) -> str | None:
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    if len(payload) > 512:
        raise D0Error(f"USB sysfs value exceeds bound: {path.name}")
    try:
        return payload.decode("utf-8", "strict").strip()
    except UnicodeDecodeError as exc:
        raise D0Error(f"USB sysfs value is not UTF-8: {path.name}") from exc


def usb_snapshot(root: Path, download: dict[str, str]) -> dict[str, Any]:
    if not root.is_dir():
        raise D0Error("USB sysfs root is unavailable")
    entries: list[dict[str, str]] = []
    download_count = 0
    for child in sorted(root.iterdir(), key=lambda value: value.name):
        vendor = _read_small(child / "idVendor")
        product_id = _read_small(child / "idProduct")
        if vendor is None or product_id is None:
            continue
        record = {"node": child.name, "vendor": vendor, "product_id": product_id}
        if (vendor, product_id) == (
            download["usb_vendor_id"],
            download["usb_product_id"],
        ):
            download_count += 1
            record["product"] = _read_small(child / "product") or ""
            record["manufacturer"] = _read_small(child / "manufacturer") or ""
        entries.append(record)
    return {
        "enumerated_devices": len(entries),
        "download_endpoint_count": download_count,
        "snapshot_sha256": f1.json_sha256(entries),
    }


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_create(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        if os.write(descriptor, payload) != len(payload):
            raise D0Error("short D0 result write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_dir(path.parent)


def allocate_run_dir(root: Path, requested: Path | None) -> Path:
    base = (root / DEFAULT_RUN_ROOT).resolve()
    base.mkdir(parents=True, exist_ok=True)
    candidate = requested or base / f"d0-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{time.time_ns()}"
    candidate = candidate if candidate.is_absolute() else root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise D0Error("D0 run directory is outside the private run root") from exc
    resolved.mkdir(mode=0o700)
    _fsync_dir(resolved.parent)
    return resolved


def _validate_health(
    bundle: f1.Bundle,
    properties: dict[str, str],
    root_health: dict[str, str],
    no_odin: bool,
) -> dict[str, Any]:
    target = bundle.profile["target"]
    expected = bundle.profile["start_health"]
    identity = {
        "model": target["model"],
        "device": target["device"],
        "incremental": target["firmware_incremental"],
    }
    for key, value in identity.items():
        if properties[key] != value:
            raise D0Error(f"connected target identity mismatch: {key}")
    if properties["boot_completed"] != "1" or properties["bootanim"] != "stopped":
        raise D0Error("Android boot is not complete and stable")
    if properties["verified_boot_state"] != expected["verified_boot_state"]:
        raise D0Error("verified-boot state mismatch")
    if BOOT_ID_RE.fullmatch(properties["boot_id"]) is None:
        raise D0Error("Android boot_id is malformed")
    if not root_health["root"].startswith("uid=0(root)"):
        raise D0Error("required Magisk root is unavailable")
    expected_hashes = {
        "boot": expected["boot_sha256"],
        **expected["supporting_partition_sha256"],
    }
    for name, digest in expected_hashes.items():
        if re.fullmatch(r"[0-9a-f]{64}", root_health[name]) is None:
            raise D0Error(f"malformed target hash: {name}")
        if root_health[name] != digest:
            raise D0Error(f"target partition identity mismatch: {name}")
    if not no_odin or expected["odin_endpoint_absent"] is not True:
        raise D0Error("normal Android has a Download endpoint")
    return {
        "android_boot_completed": True,
        "boot_animation_stopped": True,
        "verified_boot_state": properties["verified_boot_state"],
        "root_verified": True,
        "boot_sha256": root_health["boot"],
        "supporting_partition_sha256": {
            name: root_health[name] for name in ("vendor_boot", "dtbo", "recovery")
        },
        "odin_endpoint_absent": True,
        "kernel_release": properties["kernel_release"],
        "boot_id_sha256": hashlib.sha256(properties["boot_id"].encode()).hexdigest(),
    }


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise D0Error(f"{label} keys do not match the D0 schema")
    return value


def validate_result(
    result: dict[str, Any], bundle: f1.Bundle, run_dir: Path
) -> dict[str, Any]:
    _exact(
        result,
        {
            "schema",
            "version",
            "mode",
            "profile_id",
            "manifest_id",
            "bundle_sha256",
            "target_evidence",
            "health",
            "observer",
            "usb",
            "host_tool",
            "verdict",
            "device_contact",
            "device_writes",
            "reboot_requested",
            "download_transition_requested",
            "odin_invoked",
            "partition_transfer",
            "f1_authorized",
            "live_authorized",
        },
        "D0 result",
    )
    expected_header = {
        "schema": D0_RESULT_SCHEMA,
        "version": D0_VERSION,
        "mode": "connected-read-only",
        "profile_id": bundle.profile["profile_id"],
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "verdict": D0_VERDICT,
    }
    for key, expected in expected_header.items():
        if result[key] != expected:
            raise D0Error(f"D0 result header mismatch: {key}")
    if result["device_contact"] is not True:
        raise D0Error("D0 result does not prove connected collection")
    for key in (
        "device_writes",
        "reboot_requested",
        "download_transition_requested",
        "odin_invoked",
        "partition_transfer",
        "f1_authorized",
        "live_authorized",
    ):
        if result[key] is not False:
            raise D0Error(f"D0 result contains forbidden authority: {key}")
    f1.validate_target_evidence(bundle.profile, result["target_evidence"])
    health = _exact(
        result["health"],
        {
            "android_boot_completed",
            "boot_animation_stopped",
            "verified_boot_state",
            "root_verified",
            "boot_sha256",
            "supporting_partition_sha256",
            "odin_endpoint_absent",
            "kernel_release",
            "boot_id_sha256",
        },
        "D0 health",
    )
    expected_health = bundle.profile["start_health"]
    for key in (
        "android_boot_completed",
        "boot_animation_stopped",
        "root_verified",
        "odin_endpoint_absent",
    ):
        if health[key] is not True:
            raise D0Error(f"D0 health is false: {key}")
    if (
        health["verified_boot_state"] != expected_health["verified_boot_state"]
        or health["boot_sha256"] != expected_health["boot_sha256"]
        or health["supporting_partition_sha256"]
        != expected_health["supporting_partition_sha256"]
        or re.fullmatch(r"[0-9a-f]{64}", health["boot_id_sha256"]) is None
        or not isinstance(health["kernel_release"], str)
        or not health["kernel_release"]
    ):
        raise D0Error("D0 health identity is invalid")
    observer = result["observer"]
    required_observer = {
        "path",
        "bytes",
        "sha256",
        "read_to_eof",
        "stderr_bytes",
        "elapsed_sec",
        "source",
        "marker_family_count",
        "exact_marker_count",
        "baseline_clean",
    }
    _exact(observer, required_observer, "D0 observer")
    if (
        observer["source"] != bundle.manifest["observation"]["acceptance"]["source"]
        or not isinstance(observer["bytes"], int)
        or isinstance(observer["bytes"], bool)
        or not 1 <= observer["bytes"] <= MAX_OBSERVER_BYTES
        or re.fullmatch(r"[0-9a-f]{64}", observer["sha256"]) is None
        or observer["read_to_eof"] is not True
        or observer["stderr_bytes"] != 0
        or not isinstance(observer["elapsed_sec"], (int, float))
        or isinstance(observer["elapsed_sec"], bool)
        or not 0 < observer["elapsed_sec"] <= 185
        or observer["marker_family_count"] != 0
        or observer["exact_marker_count"] != 0
        or observer["baseline_clean"] is not True
    ):
        raise D0Error("D0 observer evidence is invalid")
    observer_path = Path(observer["path"])
    expected_observer_path = (run_dir / "baseline-observer.bin").absolute()
    if not observer_path.is_absolute() or observer_path != expected_observer_path:
        raise D0Error("D0 observer path is outside its run directory")
    observer_payload = _read_stable(observer_path, MAX_OBSERVER_BYTES)
    if (
        len(observer_payload) != observer["bytes"]
        or hashlib.sha256(observer_payload).hexdigest() != observer["sha256"]
    ):
        raise D0Error("D0 observer raw evidence does not match its receipt")
    try:
        stderr_payload = _read_stable(
            observer_path.with_suffix(observer_path.suffix + ".stderr"),
            MAX_TEXT_OUTPUT,
        )
    except OSError as exc:
        raise D0Error("D0 observer stderr evidence is unavailable") from exc
    if stderr_payload:
        raise D0Error("D0 observer stderr evidence is not empty")
    usb = _exact(result["usb"], {"initial", "final"}, "D0 USB evidence")
    for name in ("initial", "final"):
        snapshot = _exact(
            usb[name],
            {"enumerated_devices", "download_endpoint_count", "snapshot_sha256"},
            f"D0 USB {name}",
        )
        if (
            not isinstance(snapshot["enumerated_devices"], int)
            or isinstance(snapshot["enumerated_devices"], bool)
            or snapshot["enumerated_devices"] <= 0
            or snapshot["download_endpoint_count"] != 0
            or re.fullmatch(r"[0-9a-f]{64}", snapshot["snapshot_sha256"]) is None
        ):
            raise D0Error(f"D0 USB {name} evidence is invalid")
    host_tool = _exact(
        result["host_tool"],
        {"path", "size", "sha256", "version_output_sha256"},
        "D0 host-tool receipt",
    )
    if (
        not isinstance(host_tool["path"], str)
        or not host_tool["path"]
        or not isinstance(host_tool["size"], int)
        or isinstance(host_tool["size"], bool)
        or host_tool["size"] <= 0
        or re.fullmatch(r"[0-9a-f]{64}", host_tool["sha256"]) is None
        or re.fullmatch(r"[0-9a-f]{64}", host_tool["version_output_sha256"])
        is None
    ):
        raise D0Error("D0 host-tool receipt is invalid")
    return result


def collect_connected(
    bundle: f1.Bundle,
    run_dir: Path,
    client: ReadOnlyClient,
    usb_root: Path,
) -> dict[str, Any]:
    host_tool = client.receipt()
    download = bundle.profile["target"]["download"]
    initial_usb = usb_snapshot(usb_root, download)
    if not initial_usb["enumerated_devices"]:
        raise D0Error("host USB inventory is unexpectedly empty")
    if initial_usb["download_endpoint_count"]:
        raise D0Error("Download endpoint is present before Android collection")
    serial = client.one_serial()
    topology = client.topology(serial)
    first = client.properties(serial)
    root_health = client.root_health(serial)
    health = _validate_health(bundle, first, root_health, True)
    acceptance = bundle.manifest["observation"]["acceptance"]
    source = acceptance["source"]
    if REMOTE_PATH_RE.fullmatch(source) is None or ".." in Path(source).parts:
        raise D0Error("observer source is not a bounded procfs/sysfs path")
    receipt = client.capture(serial, source, run_dir / "baseline-observer.bin")
    payload = _read_stable(run_dir / "baseline-observer.bin", MAX_OBSERVER_BYTES)
    family = acceptance["family"].encode()
    marker = acceptance["marker"].encode()
    family_count = payload.count(family)
    exact_count = payload.count(marker)
    if family_count or exact_count:
        raise D0Error("baseline observer contains the candidate marker family")
    final_serial = client.one_serial()
    final_topology = client.topology(final_serial)
    final = client.properties(final_serial)
    final_usb = usb_snapshot(usb_root, download)
    if not final_usb["enumerated_devices"]:
        raise D0Error("final host USB inventory is unexpectedly empty")
    if final_usb["download_endpoint_count"]:
        raise D0Error("Download endpoint appeared during Android collection")
    if final_serial != serial or final_topology != topology or final != first:
        raise D0Error("connected target changed during D0 collection")
    target_evidence = {
        "schema": f1.TARGET_EVIDENCE_SCHEMA,
        "targets": [
            {
                "model": first["model"],
                "device": first["device"],
                "firmware_incremental": first["incremental"],
                "android_transport": "adb",
                "adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
                "usb_topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
            }
        ],
        "odin_endpoint_absent": True,
    }
    f1.validate_target_evidence(bundle.profile, target_evidence)
    result = {
        "schema": D0_RESULT_SCHEMA,
        "version": D0_VERSION,
        "mode": "connected-read-only",
        "profile_id": bundle.profile["profile_id"],
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "target_evidence": target_evidence,
        "health": health,
        "observer": {
            **receipt,
            "source": source,
            "marker_family_count": family_count,
            "exact_marker_count": exact_count,
            "baseline_clean": True,
        },
        "usb": {"initial": initial_usb, "final": final_usb},
        "host_tool": host_tool,
        "verdict": D0_VERDICT,
        "device_contact": True,
        "device_writes": False,
        "reboot_requested": False,
        "download_transition_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    validate_result(result, bundle, run_dir)
    durable_create(run_dir / "result.json", result)
    return result


def render_plan(bundle: f1.Bundle, adb: Path) -> dict[str, Any]:
    return {
        "schema": "device_action_d0_plan_v2",
        "version": D0_VERSION,
        "profile_id": bundle.profile["profile_id"],
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "adb": _hash_regular_file(adb.resolve(strict=True)),
        "reads": [
            "adb inventory and USB topology",
            "Android properties and boot_id",
            "root id and boot/vendor_boot/dtbo/recovery SHA256",
            bundle.manifest["observation"]["acceptance"]["source"],
            "host USB sysfs Download-endpoint absence",
        ],
        "device_contact": False,
        "device_writes": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def default_adb() -> Path:
    value = shutil.which("adb")
    if value is None:
        raise D0Error("adb is unavailable")
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--connected-read-only", action="store_true")
    parser.add_argument("--manifest", type=Path, default=f1.DEFAULT_MANIFEST)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--adb", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        bundle = f1.verify_bundle(root, args.manifest)
        adb = args.adb or default_adb()
        plan = render_plan(bundle, adb)
        if args.validate:
            result = {
                **plan,
                "schema": "device_action_d0_offline_check_v2",
                "verdict": "PASS_DEVICE_ACTION_D0_V2_OFFLINE_READY",
            }
        elif args.render_plan:
            result = plan
        else:
            run_dir = allocate_run_dir(root, args.run_dir)
            result = collect_connected(
                bundle,
                run_dir,
                AdbReadOnlyClient(adb),
                DEFAULT_USB_ROOT,
            )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (D0Error, f1.F1V2Error, f1.F1TransportError, OSError) as exc:
        print(f"Device Action D0 v2 error: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
