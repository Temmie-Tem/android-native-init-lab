#!/usr/bin/env python3
"""Guarded S22+ V3440 RDX USB viability gate.

The live path is zero-flash.  It triggers one policy-authorized Android SysRq
panic, observes the resulting USB identity, and, only for Samsung 04e8:685d,
sends the two read-only S-Boot discovery commands PrEaMbLe and PrObE.  It never
requests a memory transfer, partition operation, reboot, or Qualcomm Firehose
session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA = "s22plus_v3440_rdx_usb_viability_v1"
TIMELINE_SCHEMA = "events:[{name,timestamp_utc}]"
SCRIPT_RELATIVE = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3440_rdx_usb_viability_gate.py"
)
POLICY_DRAFT = Path(
    "docs/operations/"
    "S22PLUS_V3440_RDX_USB_VIABILITY_AGENTS_EXCEPTION_DRAFT_2026-07-11.md"
)
POLICY_MARKER = "S22+ V3440 RDX USB viability live gate"
ACTIVE_SENTINEL = "S22PLUS_V3440_RDX_USB_POLICY_STATE=ACTIVE"
PANIC_ACK_TOKEN = "S22PLUS-V3440-RDX-ONE-SYSRQ-PANIC"
PROBE_ACK_TOKEN = "S22PLUS-V3440-RDX-TWO-COMMAND-USB-PROBE"

SBOOT_DUMP_COMMIT = "8c9f6eb79ffbe702152ca7810f6382bf5e1bfd58"
QDL_COMMIT = "a00d81bc639908875862582f0d3cb0775d92e269"
PYUSB_VERSION = "1.2.1"
PYUSB_WHEEL_SHA256 = (
    "2b4c7cb86dbadf044dfb9d3a4ff69fd217013dbe78a792177a3feb172449ea36"
)
PYUSB_PRIVATE = Path("workspace/private/tools/s22plus-rdx-pyusb")
PYUSB_WHEEL = Path("workspace/private/tools/wheels/pyusb-1.2.1-py3-none-any.whl")
SAMSUNG_RDX_ID = (0x04E8, 0x685D)
QUALCOMM_SAHARA_ID = (0x05C6, 0x900E)
ANDROID_MTP_ID = (0x04E8, 0x6860)
ALLOWED_SBOOT_COMMANDS = (b"PrEaMbLe\0", b"PrObE\0")
POSITIVE_ACK = b"AcKnOwLeDgMeNt\x00"
NEGATIVE_ACK = b"NeGaTiVeAcKmNt\x00"
MAX_PROBE_BYTES = 0x8000
MAX_TABLE_ENTRIES = 256
DEFAULT_OBSERVE_SEC = 120
DEFAULT_RECOVERY_SEC = 300

EXPECTED_MODEL = "SM-S906N"
EXPECTED_DEVICE = "g0q"
EXPECTED_BOOTLOADER = "S906NKSS7FYG8"
EXPECTED_BOOT_SHA256 = (
    "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
)
EXPECTED_STOCK_DTBO_SHA256 = (
    "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
)

TIMELINE_REQUIRED = (
    "live_session_start",
    "candidate_flash_start",
    "candidate_flash_done",
    "candidate_boot_ready",
    "rollback_flash_start",
    "rollback_flash_done",
    "rollback_boot_ready",
    "live_session_end",
)
TIMELINE_SEMANTIC = (
    "no_candidate_flash_panic_arm_start",
    "no_candidate_flash_sysrq_triggered",
    "rdx_usb_observation_complete",
    "no_rollback_flash_rdx_exit_wait_start",
    "no_rollback_flash_android_returned",
)
TIMELINE_ALLOWED = TIMELINE_REQUIRED + TIMELINE_SEMANTIC

SERIAL_RE = re.compile(r"\b[A-Z0-9]{10,16}\b")
SAFE_TEXT_RE = re.compile(r"[^A-Za-z0-9._+ -]")


class GateError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def redact(text: str) -> str:
    return SERIAL_RE.sub("<SERIAL_REDACTED>", text)


def durable_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def durable_write_json(path: Path, value: Any) -> None:
    durable_write_bytes(
        path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    command: list[str], *, timeout: float = 30.0, check: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise GateError(f"command failed rc={result.returncode}: {command[0]}")
    return result


@dataclass
class Timeline:
    path: Path
    events: list[dict[str, str]]

    @classmethod
    def create(cls, path: Path) -> "Timeline":
        result = cls(path, [])
        result.flush()
        return result

    def append(self, name: str) -> None:
        if name not in TIMELINE_ALLOWED:
            raise GateError(f"unknown timeline event: {name}")
        if name in {item["name"] for item in self.events}:
            raise GateError(f"duplicate timeline event: {name}")
        self.events.append({"name": name, "timestamp_utc": utc_now()})
        self.flush()

    def flush(self) -> None:
        durable_write_json(self.path, {"events": self.events})


def agents_policy_active(root: Path) -> bool:
    text = (root / "AGENTS.md").read_text(encoding="utf-8")
    source_sha256 = sha256_file(root / SCRIPT_RELATIVE)
    required = (
        POLICY_MARKER,
        ACTIVE_SENTINEL,
        str(SCRIPT_RELATIVE),
        source_sha256,
        PANIC_ACK_TOKEN,
        PROBE_ACK_TOKEN,
        EXPECTED_BOOT_SHA256,
        EXPECTED_STOCK_DTBO_SHA256,
        SBOOT_DUMP_COMMIT,
        QDL_COMMIT,
    )
    return all(item in text for item in required)


def verify_policy_draft(root: Path) -> dict[str, Any]:
    draft = root / POLICY_DRAFT
    if not draft.is_file():
        raise GateError(f"missing policy draft: {POLICY_DRAFT}")
    text = draft.read_text(encoding="utf-8")
    source = root / SCRIPT_RELATIVE
    source_sha256 = sha256_file(source)
    required = (
        POLICY_MARKER,
        str(SCRIPT_RELATIVE),
        source_sha256,
        PANIC_ACK_TOKEN,
        PROBE_ACK_TOKEN,
        EXPECTED_BOOT_SHA256,
        EXPECTED_STOCK_DTBO_SHA256,
        SBOOT_DUMP_COMMIT,
        QDL_COMMIT,
        PYUSB_WHEEL_SHA256,
        "DRAFT_INACTIVE",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise GateError(f"policy draft missing pins: {missing}")
    return {
        "path": str(POLICY_DRAFT),
        "sha256": sha256_file(draft),
        "source_sha256": source_sha256,
        "active": agents_policy_active(root),
    }


def verify_pyusb_runtime(root: Path) -> dict[str, Any]:
    wheel = root / PYUSB_WHEEL
    package_root = root / PYUSB_PRIVATE
    if not wheel.is_file() or sha256_file(wheel) != PYUSB_WHEEL_SHA256:
        raise GateError("pinned private PyUSB wheel is missing or mismatched")
    if not package_root.is_dir():
        raise GateError("private PyUSB runtime directory is missing")
    package_text = str(package_root)
    if package_text not in sys.path:
        sys.path.insert(0, package_text)
    try:
        import usb  # type: ignore[import-not-found]
        import usb.backend.libusb1  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:
        raise GateError("private PyUSB runtime import failed") from error
    if usb.__version__ != PYUSB_VERSION:
        raise GateError(f"PyUSB version mismatch: {usb.__version__}")
    if usb.backend.libusb1.get_backend() is None:
        raise GateError("libusb-1.0 backend is unavailable")
    return {
        "version": usb.__version__,
        "wheel_sha256": PYUSB_WHEEL_SHA256,
        "libusb_backend": True,
    }


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="ascii", errors="replace").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def usb_snapshot() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    usb_root = Path("/sys/bus/usb/devices")
    if not usb_root.is_dir():
        return devices
    for path in sorted(usb_root.iterdir(), key=lambda item: item.name):
        vendor = read_text(path / "idVendor")
        product = read_text(path / "idProduct")
        if vendor is None or product is None:
            continue
        interfaces: list[dict[str, str | None]] = []
        for interface in sorted(usb_root.glob(path.name + ":*")):
            driver = None
            try:
                driver = (interface / "driver").resolve(strict=True).name
            except (FileNotFoundError, OSError):
                pass
            interfaces.append(
                {
                    "name": interface.name,
                    "class": read_text(interface / "bInterfaceClass"),
                    "subclass": read_text(interface / "bInterfaceSubClass"),
                    "protocol": read_text(interface / "bInterfaceProtocol"),
                    "driver": driver,
                }
            )
        devices.append(
            {
                "sysfs_name": path.name,
                "vid": vendor.lower(),
                "pid": product.lower(),
                "manufacturer": redact(read_text(path / "manufacturer") or ""),
                "product": redact(read_text(path / "product") or ""),
                "device_class": read_text(path / "bDeviceClass"),
                "speed": read_text(path / "speed"),
                "interfaces": interfaces,
            }
        )
    return devices


def usb_ids(snapshot: list[dict[str, Any]]) -> set[tuple[int, int]]:
    return {(int(item["vid"], 16), int(item["pid"], 16)) for item in snapshot}


def classify_snapshot(snapshot: list[dict[str, Any]]) -> str:
    ids = usb_ids(snapshot)
    if SAMSUNG_RDX_ID in ids:
        return "SAMSUNG_SBOOT_RDX_04E8_685D"
    if QUALCOMM_SAHARA_ID in ids:
        return "QUALCOMM_SAHARA_CRASHDUMP_05C6_900E"
    return "NO_SUPPORTED_RDX_ENDPOINT"


def safe_name(raw: bytes) -> str:
    return SAFE_TEXT_RE.sub("?", raw.decode("utf-8", errors="replace"))[:80]


def parse_probe_table(data: bytes) -> dict[str, Any]:
    if len(data) < 16 or b"\0" not in data[:16]:
        raise GateError("probe response missing bounded device-name header")
    raw_name = data.split(b"\0", 1)[0]
    mode = 64 if raw_name.startswith(b"+") else 32
    raw_name = raw_name[1:] if mode == 64 else raw_name
    entry_size = 0x28 if mode == 64 else 0x1C
    entries: list[dict[str, Any]] = []
    offset = 0x10
    while offset + entry_size <= len(data) and len(entries) < MAX_TABLE_ENTRIES:
        chunk = data[offset : offset + entry_size]
        if mode == 64:
            area_type = struct.unpack_from("<I", chunk, 0)[0]
            name = chunk[4:24].split(b"\0", 1)[0]
            start, end = struct.unpack_from("<QQ", chunk, 24)
        else:
            area_type = struct.unpack_from("<I", chunk, 0)[0]
            name = chunk[4:20].split(b"\0", 1)[0]
            start, end = struct.unpack_from("<II", chunk, 20)
        if start == 0 and end == 0:
            break
        if start < 20 or end < start:
            raise GateError("probe response contains malformed range")
        entries.append(
            {
                "type": area_type,
                "name": safe_name(name),
                "start": start,
                "end": end,
                "length": end - start + 1,
            }
        )
        offset += entry_size
    if not entries:
        raise GateError("probe response contains no valid memory areas")
    return {"mode": mode, "device_name": safe_name(raw_name), "areas": entries}


def validate_sboot_command(command: bytes) -> None:
    if command not in ALLOWED_SBOOT_COMMANDS:
        raise GateError(f"forbidden S-Boot command: {command!r}")


def validate_preamble_ack(data: bytes) -> None:
    if data == NEGATIVE_ACK:
        raise GateError("S-Boot returned NegativeAck; probe not sent")
    if data != POSITIVE_ACK:
        raise GateError(f"unexpected S-Boot preamble response length={len(data)}")


def _write_chunks(endpoint: Any, payload: bytes) -> None:
    validate_sboot_command(payload)
    packet_size = int(endpoint.wMaxPacketSize)
    for offset in range(0, len(payload), packet_size):
        written = endpoint.write(payload[offset : offset + packet_size], timeout=1000)
        if written <= 0:
            raise GateError("S-Boot USB OUT returned no progress")


def _read_bounded(endpoint: Any, maximum: int, *, first_only: bool = False) -> bytes:
    result = bytearray()
    packet_size = int(endpoint.wMaxPacketSize)
    while len(result) < maximum:
        request = min(packet_size, maximum - len(result))
        try:
            chunk = bytes(endpoint.read(request, timeout=1000))
        except Exception as error:  # PyUSB exposes backend-specific timeout types.
            if "timed out" in str(error).lower() and result:
                break
            raise GateError(f"S-Boot USB IN failed: {type(error).__name__}") from error
        result.extend(chunk)
        if first_only or len(chunk) < request:
            break
    return bytes(result)


def sboot_two_command_probe(run_dir: Path) -> dict[str, Any]:
    try:
        import usb.core  # type: ignore[import-not-found]
        import usb.util  # type: ignore[import-not-found]
    except ModuleNotFoundError as error:
        raise GateError("PyUSB is required only for the active S-Boot probe") from error

    devices = list(
        usb.core.find(
            find_all=True,
            idVendor=SAMSUNG_RDX_ID[0],
            idProduct=SAMSUNG_RDX_ID[1],
        )
    )
    if not devices:
        raise GateError("exact Samsung RDX USB device disappeared before probe")
    if len(devices) != 1:
        raise GateError(f"expected one Samsung RDX USB device, found {len(devices)}")
    device = devices[0]
    configuration = device.get_active_configuration()
    candidates = [item for item in configuration if int(item.bInterfaceClass) == 0x0A]
    if len(candidates) != 1:
        raise GateError(f"expected one CDC-data interface, found {len(candidates)}")
    interface = candidates[0]
    interface_number = int(interface.bInterfaceNumber)
    out_endpoint = usb.util.find_descriptor(
        interface,
        custom_match=lambda item: usb.util.endpoint_direction(item.bEndpointAddress)
        == usb.util.ENDPOINT_OUT,
    )
    in_endpoint = usb.util.find_descriptor(
        interface,
        custom_match=lambda item: usb.util.endpoint_direction(item.bEndpointAddress)
        == usb.util.ENDPOINT_IN,
    )
    if out_endpoint is None or in_endpoint is None:
        raise GateError("RDX CDC-data interface lacks one IN and one OUT endpoint")

    detached = False
    claimed = False
    try:
        try:
            if device.is_kernel_driver_active(interface_number):
                device.detach_kernel_driver(interface_number)
                detached = True
        except (NotImplementedError, AttributeError):
            pass
        usb.util.claim_interface(device, interface_number)
        claimed = True
        _write_chunks(out_endpoint, ALLOWED_SBOOT_COMMANDS[0])
        ack = _read_bounded(in_endpoint, int(in_endpoint.wMaxPacketSize), first_only=True)
        durable_write_bytes(run_dir / "sboot_preamble_response.bin", ack)
        validate_preamble_ack(ack)

        _write_chunks(out_endpoint, ALLOWED_SBOOT_COMMANDS[1])
        raw_probe = _read_bounded(in_endpoint, MAX_PROBE_BYTES)
        durable_write_bytes(run_dir / "sboot_probe_response.bin", raw_probe)
        parsed = parse_probe_table(raw_probe)
        durable_write_json(run_dir / "sboot_probe_table.json", parsed)
        return {
            "verdict": "SBOOT_PROBE_TABLE_READ",
            "response_bytes": len(raw_probe),
            "mode": parsed["mode"],
            "device_name": parsed["device_name"],
            "area_count": len(parsed["areas"]),
            "commands_sent": [item.rstrip(b"\0").decode("ascii") for item in ALLOWED_SBOOT_COMMANDS],
            "memory_transfer_requested": False,
        }
    finally:
        if claimed:
            try:
                usb.util.release_interface(device, interface_number)
            except Exception:
                pass
        if detached:
            try:
                device.attach_kernel_driver(interface_number)
            except Exception:
                pass
        usb.util.dispose_resources(device)


def adb_serial() -> str:
    output = run(["adb", "devices"], check=True).stdout.splitlines()[1:]
    serials = [line.split()[0] for line in output if line.strip().endswith("\tdevice")]
    if len(serials) != 1:
        raise GateError(f"expected one authorized Android device, found {len(serials)}")
    return serials[0]


def adb_shell(serial: str, command: str, *, timeout: float = 30.0) -> str:
    return run(["adb", "-s", serial, "shell", command], timeout=timeout, check=True).stdout.strip()


def root_shell(serial: str, command: str, *, timeout: float = 30.0) -> str:
    return adb_shell(serial, f"su -c {json.dumps(command)}", timeout=timeout)


def android_preflight() -> tuple[str, dict[str, str]]:
    serial = adb_serial()
    props = {
        "model": adb_shell(serial, "getprop ro.product.model"),
        "device": adb_shell(serial, "getprop ro.product.device"),
        "bootloader": adb_shell(serial, "getprop ro.boot.bootloader"),
        "boot_completed": adb_shell(serial, "getprop sys.boot_completed"),
        "root_id": root_shell(serial, "id"),
        "boot_sha256": root_shell(serial, "sha256sum /dev/block/by-name/boot").split()[0],
        "dtbo_sha256": root_shell(serial, "sha256sum /dev/block/by-name/dtbo").split()[0],
    }
    expected = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "bootloader": EXPECTED_BOOTLOADER,
        "boot_completed": "1",
        "boot_sha256": EXPECTED_BOOT_SHA256,
        "dtbo_sha256": EXPECTED_STOCK_DTBO_SHA256,
    }
    for key, value in expected.items():
        if props[key] != value:
            raise GateError(f"Android preflight mismatch: {key}")
    if "uid=0(root)" not in props["root_id"]:
        raise GateError("Magisk root preflight failed")
    props["root_id"] = "uid=0(root)"
    return serial, props


def trigger_one_sysrq_panic(serial: str, run_id: str) -> None:
    command = (
        "set -eu; "
        f"printf '%s\\n' 'S22_V3440_RDX_BEGIN run={run_id}' > /dev/kmsg; "
        "printf 1 > /proc/sys/kernel/sysrq; "
        "printf c > /proc/sysrq-trigger"
    )
    timed_out = False
    try:
        result = run(
            ["adb", "-s", serial, "shell", f"su -c {shlex.quote(command)}"],
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        result = None
    # A working panic normally tears down ADB before it can return a clean rc.
    if result is not None and result.returncode == 0:
        raise GateError("sysrq command returned cleanly; panic transport was not lost")
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            state = run(["adb", "-s", serial, "get-state"], timeout=3, check=False)
        except subprocess.TimeoutExpired:
            return
        if state.returncode != 0 or state.stdout.strip() != "device":
            return
        time.sleep(0.25)
    suffix = " after command timeout" if timed_out else ""
    raise GateError(f"ADB remained connected{suffix}; panic not proven")


def wait_for_rdx_endpoint(
    run_dir: Path, timeout_sec: int, sampler: Callable[[], list[dict[str, Any]]] = usb_snapshot
) -> tuple[str, list[dict[str, Any]]]:
    deadline = time.monotonic() + timeout_sec
    samples: list[dict[str, Any]] = []
    previous_signature: str | None = None
    while time.monotonic() < deadline:
        snapshot = sampler()
        classification = classify_snapshot(snapshot)
        signature = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if signature != previous_signature:
            samples.append(
                {
                    "timestamp_utc": utc_now(),
                    "classification": classification,
                    "devices": snapshot,
                }
            )
            durable_write_json(run_dir / "usb_samples.json", samples)
            previous_signature = signature
        if classification != "NO_SUPPORTED_RDX_ENDPOINT":
            return classification, snapshot
        time.sleep(0.25)
    return "NO_SUPPORTED_RDX_ENDPOINT", samples[-1]["devices"] if samples else []


def wait_for_android(timeout_sec: int) -> tuple[str, dict[str, str]]:
    deadline = time.monotonic() + timeout_sec
    last_error = ""
    while time.monotonic() < deadline:
        try:
            serial, props = android_preflight()
            return serial, props
        except (GateError, subprocess.SubprocessError) as error:
            last_error = str(error)
            time.sleep(2)
    raise GateError(f"Android baseline did not return: {last_error}")


def offline_check(root: Path) -> dict[str, Any]:
    draft = verify_policy_draft(root)
    runtime = verify_pyusb_runtime(root)
    return {
        "schema": SCHEMA,
        "verdict": "HOST_SOURCE_READY_NO_LIVE_AUTHORIZATION",
        "policy": draft,
        "pins": {
            "sboot_dump_commit": SBOOT_DUMP_COMMIT,
            "qdl_commit": QDL_COMMIT,
            "boot_sha256": EXPECTED_BOOT_SHA256,
            "stock_dtbo_sha256": EXPECTED_STOCK_DTBO_SHA256,
        },
        "allowed_sboot_commands": [
            item.rstrip(b"\0").decode("ascii") for item in ALLOWED_SBOOT_COMMANDS
        ],
        "max_probe_bytes": MAX_PROBE_BYTES,
        "memory_transfer": False,
        "device_contact": False,
        "policy_active": agents_policy_active(root),
        "private_pyusb_runtime": runtime,
    }


def live_run(root: Path, args: argparse.Namespace) -> int:
    if not agents_policy_active(root):
        raise GateError("V3440 RDX USB policy is inactive")
    if args.panic_ack != PANIC_ACK_TOKEN:
        raise GateError("panic acknowledgement token mismatch")
    if args.probe_ack != PROBE_ACK_TOKEN:
        raise GateError("USB probe acknowledgement token mismatch")

    run_dir = root / "workspace/private/runs" / f"s22plus_v3440_rdx_{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    timeline = Timeline.create(run_dir / "timeline.json")
    timeline.append("live_session_start")
    pyusb_runtime = verify_pyusb_runtime(root)
    serial, preflight = android_preflight()
    baseline_usb = usb_snapshot()
    run_id = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": run_id,
        "candidate_flash": False,
        "rollback_flash": False,
        "preflight": preflight,
        "pyusb_runtime": pyusb_runtime,
        "baseline_usb": baseline_usb,
        "panic_attempted": False,
        "timeline_semantics": {
            "candidate_flash_start": "panic_arm_start_no_candidate_flash",
            "candidate_flash_done": "sysrq_triggered_no_candidate_flash",
            "candidate_boot_ready": "rdx_usb_observation_complete",
            "rollback_flash_start": "rdx_exit_wait_start_no_rollback_flash",
            "rollback_flash_done": "android_returned_no_rollback_flash",
            "rollback_boot_ready": "stock_android_hashes_reverified",
        },
        "verdict": "INCOMPLETE",
    }
    durable_write_json(run_dir / "result.json", result)

    timeline.append("candidate_flash_start")
    timeline.append("no_candidate_flash_panic_arm_start")
    result["panic_attempted"] = True
    durable_write_json(run_dir / "result.json", result)
    trigger_one_sysrq_panic(serial, run_id)
    timeline.append("candidate_flash_done")
    timeline.append("no_candidate_flash_sysrq_triggered")

    try:
        classification, endpoint_snapshot = wait_for_rdx_endpoint(
            run_dir, args.observe_sec
        )
        result["rdx_classification"] = classification
        result["rdx_endpoint_snapshot"] = endpoint_snapshot
        if classification == "SAMSUNG_SBOOT_RDX_04E8_685D":
            result["probe"] = sboot_two_command_probe(run_dir)
            result["verdict"] = "PASS_SBOOT_READONLY_PROBE"
        elif classification == "QUALCOMM_SAHARA_CRASHDUMP_05C6_900E":
            result["probe"] = {
                "verdict": "SAHARA_ENDPOINT_PRESENT_NOT_COLLECTED",
                "qdl_commit": QDL_COMMIT,
                "qdl_invoked": False,
            }
            result["verdict"] = "PASS_SAHARA_ENDPOINT_DISCOVERY"
        else:
            result["probe"] = {"verdict": "NO_SUPPORTED_ENDPOINT"}
            result["verdict"] = "NO_PROOF_NO_RDX_USB_ENDPOINT"
    except Exception as error:
        error_text = str(error) if isinstance(error, GateError) else type(error).__name__
        result["probe"] = {
            "verdict": "FAIL_CLOSED_PROBE_ERROR",
            "error": error_text,
        }
        result["verdict"] = "FAIL_CLOSED_RDX_PROBE"
    durable_write_json(run_dir / "result.json", result)
    timeline.append("candidate_boot_ready")
    timeline.append("rdx_usb_observation_complete")

    print("RDX observation complete. Operator: use the physical RDX EXIT action now.", flush=True)
    timeline.append("rollback_flash_start")
    timeline.append("no_rollback_flash_rdx_exit_wait_start")
    _, recovered = wait_for_android(args.recovery_sec)
    timeline.append("rollback_flash_done")
    timeline.append("no_rollback_flash_android_returned")
    result["recovered_android"] = recovered
    timeline.append("rollback_boot_ready")
    timeline.append("live_session_end")
    durable_write_json(run_dir / "result.json", result)
    print(json.dumps({"run_dir": str(run_dir), "verdict": result["verdict"]}, indent=2))
    return 0 if result["verdict"].startswith("PASS_") else 10


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--offline-check", action="store_true")
    modes.add_argument("--print-plan", action="store_true")
    modes.add_argument("--snapshot", action="store_true")
    modes.add_argument("--live", action="store_true")
    parser.add_argument("--panic-ack")
    parser.add_argument("--probe-ack")
    parser.add_argument("--observe-sec", type=int, default=DEFAULT_OBSERVE_SEC)
    parser.add_argument("--recovery-sec", type=int, default=DEFAULT_RECOVERY_SEC)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    try:
        if args.offline_check:
            print(json.dumps(offline_check(root), indent=2, sort_keys=True))
            return 0
        if args.print_plan:
            print(
                "stock Android preflight -> one SysRq panic -> RDX USB classify -> "
                "04e8:685d PrEaMbLe+PrObE only OR 05c6:900e classify only -> "
                "operator RDX exit -> stock Android hash recheck"
            )
            return 0
        if args.snapshot:
            snapshot = usb_snapshot()
            print(json.dumps({"classification": classify_snapshot(snapshot), "devices": snapshot}, indent=2))
            return 0
        if not 5 <= args.observe_sec <= 300:
            raise GateError("observe-sec must be in [5, 300]")
        if not 30 <= args.recovery_sec <= 600:
            raise GateError("recovery-sec must be in [30, 600]")
        return live_run(root, args)
    except (GateError, subprocess.SubprocessError) as error:
        print(f"V3440 gate error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
