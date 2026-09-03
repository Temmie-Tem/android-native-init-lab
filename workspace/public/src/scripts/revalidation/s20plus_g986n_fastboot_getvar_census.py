#!/usr/bin/env python3
"""One-use attended classic-fastboot read-only census for exact SM-G986N."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable

import device_action_raw_capture_v1 as raw_capture
import s20plus_g986n_d0_inventory as base
import s20plus_g986n_routine_d0 as routine


VERSION = "s20plus-g986n-fastboot-getvar-census-v1"
SCHEMA = "s20plus_g986n_fastboot_getvar_census_result_v1"
RETURN_PENDING = "PASS_S20PLUS_G986N_FASTBOOT_GETVAR_CENSUS_RETURN_PENDING"
FINAL_PASS = "PASS_S20PLUS_G986N_FASTBOOT_GETVAR_CENSUS_RETURN_HEALTHY"
FINAL_NO_PROOF = "NO_PROOF_S20PLUS_G986N_FASTBOOT_CENSUS_RETURNED_HEALTHY"

# Rotated only after independent review of the exact final bytes.
CAPABILITY_ORDINAL = 2
LIVE_ACTIVE = True

EXPECTED_MODEL = "SM-G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"

FASTBOOT_REL = Path(
    "workspace/private/tools/android-platform-tools/37.0.1-15733141/"
    "platform-tools/fastboot"
)
FASTBOOT_SIZE = 3_333_552
FASTBOOT_SHA256 = "a686e2c7e8dc9cf4cba0cb8a2eef05f7b2bd682c925abd032fe203215d80b618"
FASTBOOT_VERSION = "37.0.1-15733141"
GETVARS = (
    "product",
    "is-userspace",
    "version-bootloader",
    "max-download-size",
)

EXPECTED_FASTBOOT_USB = {
    "vid": "18d1",
    "pid": "d00d",
    "bcd_device": "0100",
    "manufacturer": "Google",
    "product": "Android",
}
EXPECTED_INTERFACE = {"class": "ff", "subclass": "42", "protocol": "03"}
EXPECTED_ENDPOINTS = (
    {"direction": "out", "type": "Bulk", "max_packet_size": "0400"},
    {"direction": "in", "type": "Bulk", "max_packet_size": "0400"},
)

DEFAULT_RUN_ROOT = Path("workspace/private/runs/s20plus-g986n-fastboot-getvar-census")
SHARED_GUARD_REL = Path(
    "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
)
CONSUMED_NAME = "consumed-entry-intent-v2.json"
PREDECESSOR_CONSUMED_NAME = "consumed-entry-intent.json"
PREDECESSOR_ENTRY_SIZE = 562
PREDECESSOR_ENTRY_SHA256 = "75bc5e7d1cb4c7fb15a9e17144ac01dd2bafaef3fb79a6ce42d078c78b7b45fd"
PREDECESSOR_FINAL_SIZE = 1_511
PREDECESSOR_FINAL_SHA256 = "80d075c54a65c75f0a820eb3147dbc872c9640be68b4eaf343531fd87e139f8d"
MAX_TEXT_BYTES = 32 * 1024
MAX_WAIT_SECONDS = 180.0
USB_NODE_RE = re.compile(r"[0-9]+-[0-9]+(?:\.[0-9]+)*")
USB_HEX_RE = re.compile(r"[0-9a-f]{4}")
USB_SERIAL_RE = re.compile(r"[^\x00\r\n]{1,128}")


class FastbootCensusError(RuntimeError):
    pass


class ReturnRequiredError(FastbootCensusError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]
Acquire = Callable[..., raw_capture.RawCaptureHandle]
UsbInventory = Callable[[], tuple[dict[str, Any], ...]]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def object_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise FastbootCensusError(f"{label} is not a direct regular file")
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FastbootCensusError(f"{label} is unreadable") from exc
    if not isinstance(value, dict):
        raise FastbootCensusError(f"{label} is not an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_fastboot(root: Path) -> dict[str, Any]:
    path = (root / FASTBOOT_REL).absolute()
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise FastbootCensusError("bound fastboot executable is unavailable") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or path.resolve(strict=True) != path:
        raise FastbootCensusError("bound fastboot executable is indirect")
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
        raise FastbootCensusError("bound fastboot executable ownership or mode differs")
    if metadata.st_size != FASTBOOT_SIZE or sha256_file(path) != FASTBOOT_SHA256:
        raise FastbootCensusError("bound fastboot executable identity differs")
    if not os.access(path, os.X_OK):
        raise FastbootCensusError("bound fastboot executable is not executable")
    return {
        "path": str(path),
        "size": FASTBOOT_SIZE,
        "sha256": FASTBOOT_SHA256,
        "version": FASTBOOT_VERSION,
    }


class RawCommand:
    """Return command bytes only after the common raw receipt is durable."""

    def __init__(
        self,
        run_dir: Path,
        prefix: str,
        *,
        acquire: Acquire = raw_capture.acquire_command,
        capture_dir: Path | None = None,
    ) -> None:
        self.capture_dir = capture_dir or raw_capture.prepare_capture_dir(run_dir)
        self.prefix = prefix
        self.acquire = acquire
        self.ordinal = 0

    def __call__(
        self, argv: list[str], timeout: float, maximum: int
    ) -> tuple[int, bytes, bytes]:
        self.ordinal += 1
        handle = self.acquire(
            argv,
            self.capture_dir,
            f"{self.prefix}-{self.ordinal:02d}",
            timeout=timeout,
            stdout_maximum=maximum,
            stderr_maximum=maximum,
        )
        current = raw_capture.load_handle(handle.receipt_path)
        if (
            current != handle
            or handle.producer_error_type is not None
            or handle.timed_out
            or handle.output_exceeded
            or handle.returncode is None
        ):
            raise FastbootCensusError("raw command acquisition did not complete")
        return (
            handle.returncode,
            raw_capture.read_stdout(handle, maximum=maximum),
            raw_capture.read_stderr(handle, maximum=maximum),
        )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="strict").strip()
    except (OSError, UnicodeError):
        return ""


def real_usb_inventory() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for raw in sorted(glob.glob("/sys/bus/usb/devices/*")):
        device = Path(raw)
        if USB_NODE_RE.fullmatch(device.name) is None:
            continue
        vid = _read_text(device / "idVendor").lower()
        pid = _read_text(device / "idProduct").lower()
        if USB_HEX_RE.fullmatch(vid) is None or USB_HEX_RE.fullmatch(pid) is None:
            continue
        interfaces: list[dict[str, Any]] = []
        for raw_interface in sorted(glob.glob(f"{raw}:*")):
            interface = Path(raw_interface)
            endpoints = tuple(
                {
                    "direction": _read_text(Path(raw_endpoint) / "direction"),
                    "type": _read_text(Path(raw_endpoint) / "type"),
                    "max_packet_size": _read_text(
                        Path(raw_endpoint) / "wMaxPacketSize"
                    ).lower(),
                }
                for raw_endpoint in sorted(glob.glob(f"{raw_interface}/ep_*"))
            )
            interfaces.append(
                {
                    "class": _read_text(interface / "bInterfaceClass").lower(),
                    "subclass": _read_text(interface / "bInterfaceSubClass").lower(),
                    "protocol": _read_text(interface / "bInterfaceProtocol").lower(),
                    "endpoints": endpoints,
                }
            )
        rows.append(
            {
                "node": device.name,
                "vid": vid,
                "pid": pid,
                "bcd_device": _read_text(device / "bcdDevice").lower(),
                "manufacturer": _read_text(device / "manufacturer"),
                "product": _read_text(device / "product"),
                "serial": _read_text(device / "serial"),
                "interfaces": tuple(interfaces),
            }
        )
    return tuple(rows)


def _is_fastboot(interface: dict[str, Any]) -> bool:
    return all(interface.get(key) == value for key, value in EXPECTED_INTERFACE.items())


def validate_android_usb(
    rows: tuple[dict[str, Any], ...], node: str, serial: str
) -> None:
    matches = [row for row in rows if row.get("node") == node]
    if len(matches) != 1:
        raise FastbootCensusError("Android USB topology is absent or ambiguous")
    row = matches[0]
    if (
        row.get("vid") != "04e8"
        or row.get("pid") != "6860"
        or row.get("serial") != serial
        or any(_is_fastboot(item) for item in row.get("interfaces", ()))
    ):
        raise FastbootCensusError("prepared topology is not the exact Android role")


def validate_fastboot_usb(
    rows: tuple[dict[str, Any], ...], node: str, serial: str
) -> dict[str, Any] | None:
    matches = [
        row
        for row in rows
        if any(_is_fastboot(item) for item in row.get("interfaces", ()))
    ]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("node") != node:
        raise FastbootCensusError("fastboot endpoint is foreign or ambiguous")
    row = matches[0]
    if any(row.get(key) != value for key, value in EXPECTED_FASTBOOT_USB.items()):
        raise FastbootCensusError("fastboot USB identity differs")
    interfaces = row.get("interfaces", ())
    if (
        len(interfaces) != 1
        or not _is_fastboot(interfaces[0])
        or tuple(interfaces[0].get("endpoints", ())) != EXPECTED_ENDPOINTS
    ):
        raise FastbootCensusError("fastboot interface or endpoints differ")
    if (
        USB_SERIAL_RE.fullmatch(str(row.get("serial", ""))) is None
        or row.get("serial") != serial
    ):
        raise FastbootCensusError("fastboot serial does not continue the target")
    return row


def wait_for_fastboot(
    usb_inventory: UsbInventory,
    node: str,
    serial: str,
    *,
    timeout: float,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not 0.1 <= timeout <= MAX_WAIT_SECONDS:
        raise FastbootCensusError("fastboot wait bound differs")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        endpoint = validate_fastboot_usb(usb_inventory(), node, serial)
        if endpoint is not None:
            return endpoint
        sleep(0.1)
    raise FastbootCensusError("exact fastboot endpoint did not arrive")


def collect_android_health(
    command: Command,
    usb_inventory: UsbInventory,
) -> dict[str, Any]:
    adb_receipt = base.tool_receipt(base.DEFAULT_ADB)
    adb = adb_receipt["path"]
    first_rows = base.parse_inventory(
        base.decode_command(command([adb, "devices", "-l"], 10, MAX_TEXT_BYTES), "ADB inventory")
    )
    selected = routine.select_exact_target(first_rows)
    serial = selected["serial"]
    devpath = base.decode_command(
        command([adb, "-s", serial, "get-devpath"], 10, MAX_TEXT_BYTES),
        "target devpath",
    )
    if base.DEVPATH_RE.fullmatch(devpath) is None:
        raise FastbootCensusError("target USB topology is malformed")
    snapshots = []
    for _ in range(2):
        text = base.decode_command(
            command(
                [adb, "-s", serial, "exec-out", "sh", "-c", base.REMOTE_SNAPSHOT],
                20,
                MAX_TEXT_BYTES,
            ),
            "target health",
        )
        snapshots.append(base.parse_snapshot(text))
    if snapshots[0] != snapshots[1]:
        raise FastbootCensusError("target health changed during collection")
    values = snapshots[0]
    base.validate_snapshot_binding(values, selected)
    if values["incremental"] != EXPECTED_INCREMENTAL or values["selinux"] != "Enforcing":
        raise FastbootCensusError("target build or SELinux health differs")
    final_rows = base.parse_inventory(
        base.decode_command(
            command([adb, "devices", "-l"], 10, MAX_TEXT_BYTES),
            "final ADB inventory",
        )
    )
    final_selected = routine.select_exact_target(final_rows)
    if (
        final_selected["serial"] != serial
        or routine.sanitized_inventory(final_rows)
        != routine.sanitized_inventory(first_rows)
    ):
        raise FastbootCensusError("ADB inventory changed during health collection")
    validate_android_usb(usb_inventory(), devpath.removeprefix("usb:"), serial)
    if base.tool_receipt(base.DEFAULT_ADB) != adb_receipt:
        raise FastbootCensusError("ADB tool changed during health collection")
    return {
        "serial": serial,
        "devpath": devpath,
        "node": devpath.removeprefix("usb:"),
        "serial_sha256": base.sha256_text(serial),
        "topology_sha256": base.sha256_text(devpath),
        "boot_id_sha256": base.sha256_text(values["boot_id"]),
        "other_serial_sha256": sorted(
            base.sha256_text(row["serial"])
            for row in first_rows
            if row["serial"] != serial
        ),
        "health": {
            "model": values["model"],
            "device": values["device"],
            "product_name": values["product_name"],
            "incremental": values["incremental"],
            "boot_completed": values["boot_completed"],
            "bootanim": values["bootanim"],
            "selinux": values["selinux"],
        },
        "adb": adb_receipt,
    }


def classify_getvar(
    variable: str,
    result: tuple[int, bytes, bytes],
    private_values: tuple[str, ...],
) -> dict[str, Any]:
    returncode, stdout, stderr = result
    try:
        output = (stdout + stderr).decode("utf-8", "strict")
    except UnicodeError as exc:
        raise FastbootCensusError("fastboot output is not UTF-8") from exc
    for value in private_values:
        if value:
            output = output.replace(value, "<PRIVATE_REDACTED>")
    output = output.strip()
    lowered = output.lower()
    unsupported = (
        returncode == 1
        and "failed (remote:" in lowered
        and any(
            marker in lowered
            for marker in ("unknown variable", "variable not found", "not implemented")
        )
    )
    if returncode == 0 and "failed (" not in lowered and "fastboot: error" not in lowered:
        status = "VALUE"
    elif unsupported:
        status = "UNSUPPORTED"
    else:
        status = "FAILURE_STOP"
    value: str | None = None
    for line in output.splitlines():
        candidate = line.strip()
        for prefix in (f"(bootloader) {variable}:", f"{variable}:"):
            if candidate.startswith(prefix):
                value = candidate[len(prefix) :].strip()
                break
        if value is not None:
            break
    if status == "VALUE" and value is None:
        status = "FAILURE_STOP"
    return {
        "schema": "s20plus_g986n_fastboot_getvar_observation_v1",
        "version": VERSION,
        "variable": variable,
        "status": status,
        "value": value,
        "returncode": returncode,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "output": output,
        "captured_before_parse": True,
        "at": now(),
    }


def run_root(root: Path) -> Path:
    return (root / DEFAULT_RUN_ROOT).absolute()


def guard_path(root: Path) -> Path:
    return (root / SHARED_GUARD_REL).absolute()


def consumed_path(root: Path) -> Path:
    return run_root(root) / CONSUMED_NAME


def predecessor_consumed_path(root: Path) -> Path:
    return run_root(root) / PREDECESSOR_CONSUMED_NAME


def _bound_run_dir(root: Path, entry: dict[str, Any], label: str) -> Path:
    raw = entry.get("run_dir")
    if not isinstance(raw, str):
        raise FastbootCensusError(f"{label} has no run directory")
    candidate = Path(raw)
    if not candidate.is_absolute():
        raise FastbootCensusError(f"{label} run directory is not absolute")
    try:
        candidate.relative_to(run_root(root))
    except ValueError as exc:
        raise FastbootCensusError(f"{label} run directory is outside the census root") from exc
    if candidate.is_symlink() or not candidate.is_dir() or candidate.resolve() != candidate:
        raise FastbootCensusError(f"{label} run directory is unavailable or indirect")
    return candidate


def require_zero_query_predecessor(root: Path) -> dict[str, Any]:
    if guard_path(root).exists() or guard_path(root).is_symlink():
        raise FastbootCensusError("predecessor shared guard remains unresolved")
    entry_path = predecessor_consumed_path(root)
    metadata = entry_path.lstat()
    if (
        entry_path.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or metadata.st_size != PREDECESSOR_ENTRY_SIZE
        or sha256_file(entry_path) != PREDECESSOR_ENTRY_SHA256
    ):
        raise FastbootCensusError("predecessor entry identity differs")
    entry = load_json(entry_path, "predecessor consumed entry")
    predecessor_run = _bound_run_dir(root, entry, "predecessor")
    terminal_path = predecessor_run / "final-result.json"
    terminal_metadata = terminal_path.lstat()
    if (
        terminal_path.is_symlink()
        or not stat.S_ISREG(terminal_metadata.st_mode)
        or stat.S_IMODE(terminal_metadata.st_mode) != 0o400
        or terminal_metadata.st_size != PREDECESSOR_FINAL_SIZE
        or sha256_file(terminal_path) != PREDECESSOR_FINAL_SHA256
    ):
        raise FastbootCensusError("predecessor terminal identity differs")
    terminal = load_json(terminal_path, "predecessor terminal")
    if (
        terminal.get("verdict") != FINAL_NO_PROOF
        or terminal.get("fastboot_query_intent_count") != 0
        or terminal.get("all_four_queries_completed") is not False
        or terminal.get("fastboot_endpoint_absent_before_health") is not True
        or terminal.get("replay_permitted") is not False
        or (predecessor_run / "entry-observed.json").exists()
        or (predecessor_run / "probe-result.json").exists()
        or list(predecessor_run.glob("query-*-intent.json"))
        or list(predecessor_run.glob("query-*-result.json"))
    ):
        raise FastbootCensusError("predecessor is not the exact zero-query healthy terminal")
    return {
        "ordinal": 1,
        "entry_sha256": PREDECESSOR_ENTRY_SHA256,
        "terminal_sha256": PREDECESSOR_FINAL_SHA256,
        "run_dir_sha256": base.sha256_text(str(predecessor_run)),
        "verdict": FINAL_NO_PROOF,
        "fastboot_query_intent_count": 0,
    }


def allocate_run_dir(root: Path) -> Path:
    parent = run_root(root)
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    run_dir = parent / (
        "census-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + f"-{time.time_ns()}"
    )
    run_dir.mkdir(mode=0o700)
    _fsync_dir(parent)
    return run_dir


def allocate_finalize_capture_dir(run_dir: Path) -> Path:
    for ordinal in range(1, 1000):
        path = run_dir / f"finalize-raw-{ordinal:03d}"
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            continue
        _fsync_dir(run_dir)
        return raw_capture.prepare_capture_dir(run_dir, path.name)
    raise FastbootCensusError("finalize raw-attempt namespace is exhausted")


def consumed_run_dir(root: Path) -> Path:
    value = load_json(consumed_path(root), "consumed entry intent")
    return _bound_run_dir(root, value, "consumed entry intent")


def acquire_guard(root: Path, run_dir: Path) -> None:
    path = guard_path(root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        base.durable_write(
            path,
            {
                "schema": "s20plus_g986n_fastboot_getvar_guard_v1",
                "version": VERSION,
                "capability_ordinal": CAPABILITY_ORDINAL,
                "action": "attended-classic-fastboot-read-only-census",
                "run_dir": str(run_dir),
                "unresolved": True,
                "at": now(),
            },
        )
    except FileExistsError as exc:
        raise FastbootCensusError("an unresolved shared S20+ action exists") from exc


def check_guard(root: Path, run_dir: Path) -> None:
    value = load_json(guard_path(root), "shared action guard")
    if (
        value.get("schema") != "s20plus_g986n_fastboot_getvar_guard_v1"
        or value.get("version") != VERSION
        or value.get("capability_ordinal") != CAPABILITY_ORDINAL
        or value.get("run_dir") != str(run_dir)
        or value.get("unresolved") is not True
    ):
        raise FastbootCensusError("shared action guard binding differs")


def release_guard(root: Path, run_dir: Path) -> None:
    check_guard(root, run_dir)
    path = guard_path(root)
    path.unlink()
    _fsync_dir(path.parent)


def create_entry_intent(root: Path, run_dir: Path, prepared: dict[str, Any]) -> None:
    base.durable_write(
        consumed_path(root),
        {
            "schema": "s20plus_g986n_fastboot_getvar_entry_intent_v2",
            "version": VERSION,
            "capability_ordinal": CAPABILITY_ORDINAL,
            "run_dir": str(run_dir),
            "prepared_sha256": object_sha256(prepared),
            "operator_action": "select Magisk bootloader reboot",
            "host_transition_command": None,
            "attempt": 1,
            "no_replay": True,
            "consumed": True,
            "at": now(),
        },
    )


def check_entry_intent(root: Path, run_dir: Path, prepared: dict[str, Any]) -> None:
    value = load_json(consumed_path(root), "consumed entry intent")
    if (
        value.get("schema") != "s20plus_g986n_fastboot_getvar_entry_intent_v2"
        or value.get("version") != VERSION
        or value.get("capability_ordinal") != CAPABILITY_ORDINAL
        or value.get("run_dir") != str(run_dir)
        or value.get("prepared_sha256") != object_sha256(prepared)
        or value.get("host_transition_command") is not None
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or value.get("consumed") is not True
    ):
        raise FastbootCensusError("consumed entry intent binding differs")


def connected_census(
    *,
    root: Path,
    run_dir: Path,
    command: Command,
    usb_inventory: UsbInventory = real_usb_inventory,
    ready: Callable[[], None] | None = None,
    timeout: float = MAX_WAIT_SECONDS,
) -> dict[str, Any]:
    if not LIVE_ACTIVE:
        raise FastbootCensusError("live fastboot census is not active")
    predecessor = require_zero_query_predecessor(root)
    if consumed_path(root).exists() or consumed_path(root).is_symlink():
        raise FastbootCensusError("the one-use fastboot census is already consumed")
    acquire_guard(root, run_dir)
    health = collect_android_health(command, usb_inventory)
    fastboot_receipt = require_fastboot(root)
    prepared = {
        "schema": "s20plus_g986n_fastboot_getvar_prepared_v1",
        "version": VERSION,
        "capability_ordinal": CAPABILITY_ORDINAL,
        "predecessor": predecessor,
        "target": {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product_name": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            "serial_sha256": health["serial_sha256"],
            "topology_sha256": health["topology_sha256"],
            "boot_id_sha256": health["boot_id_sha256"],
            "other_serial_sha256": health["other_serial_sha256"],
        },
        "health": health["health"],
        "host_tools": {"adb": health["adb"], "fastboot": fastboot_receipt},
        "fixed_getvars": list(GETVARS),
        "device_writes": False,
        "at": now(),
    }
    base.durable_write(run_dir / "prepared.json", prepared)
    create_entry_intent(root, run_dir, prepared)
    if ready is not None:
        ready()

    endpoint = wait_for_fastboot(
        usb_inventory,
        health["node"],
        health["serial"],
        timeout=timeout,
    )
    base.durable_write(
        run_dir / "entry-observed.json",
        {
            "schema": "s20plus_g986n_fastboot_entry_observed_v1",
            "version": VERSION,
            "capability_ordinal": CAPABILITY_ORDINAL,
            "prepared_sha256": object_sha256(prepared),
            "serial_sha256": base.sha256_text(endpoint["serial"]),
            "topology_sha256": health["topology_sha256"],
            "at": now(),
        },
    )

    post_rows = base.parse_inventory(
        base.decode_command(
            command([health["adb"]["path"], "devices", "-l"], 10, MAX_TEXT_BYTES),
            "post-entry ADB inventory",
        )
    )
    if any(row["serial"] == health["serial"] for row in post_rows):
        raise ReturnRequiredError("prepared target remains in ADB after fastboot arrival")
    if sorted(base.sha256_text(row["serial"]) for row in post_rows) != health[
        "other_serial_sha256"
    ]:
        raise ReturnRequiredError("other ADB inventory changed during fastboot entry")

    observations: list[dict[str, Any]] = []
    private_values = (health["serial"], health["devpath"], health["node"])
    for ordinal, variable in enumerate(GETVARS, start=1):
        if require_fastboot(root) != fastboot_receipt:
            raise ReturnRequiredError("fastboot tool changed during census")
        if validate_fastboot_usb(
            usb_inventory(), health["node"], health["serial"]
        ) is None:
            raise ReturnRequiredError("fastboot endpoint disappeared during census")
        intent = {
            "schema": "s20plus_g986n_fastboot_getvar_query_intent_v1",
            "version": VERSION,
            "capability_ordinal": CAPABILITY_ORDINAL,
            "prepared_sha256": object_sha256(prepared),
            "ordinal": ordinal,
            "variable": variable,
            "attempt": 1,
            "no_replay": True,
            "at": now(),
        }
        base.durable_write(run_dir / f"query-{ordinal:02d}-intent.json", intent)
        observation = classify_getvar(
            variable,
            command(
                [
                    fastboot_receipt["path"],
                    "-s",
                    health["serial"],
                    "getvar",
                    variable,
                ],
                10,
                MAX_TEXT_BYTES,
            ),
            private_values,
        )
        observation["intent_sha256"] = object_sha256(intent)
        observation["capability_ordinal"] = CAPABILITY_ORDINAL
        base.durable_write(
            run_dir / f"query-{ordinal:02d}-result.json", observation
        )
        observations.append(observation)
        if observation["status"] == "FAILURE_STOP":
            raise ReturnRequiredError("unrecognized fastboot query failure")

    if validate_fastboot_usb(
        usb_inventory(), health["node"], health["serial"]
    ) is None:
        raise ReturnRequiredError("fastboot endpoint disappeared after census")
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "capability_ordinal": CAPABILITY_ORDINAL,
        "target": prepared["target"],
        "getvars": observations,
        "getvar_order": list(GETVARS),
        "prepare_adb_command_count": 5,
        "post_entry_adb_command_count": 1,
        "fastboot_command_count": len(observations),
        "s22plus_command_count": 0,
        "a90_command_count": 0,
        "other_target_command_count": 0,
        "device_writes": False,
        "reboot_command_sent": False,
        "payload_transfer": False,
        "partition_access": False,
        "fastboot_download_phase": False,
        "boot_command_sent": False,
        "flash_command_sent": False,
        "erase_command_sent": False,
        "unlock_command_sent": False,
        "return_health_pending": True,
        "replay_permitted": False,
        "verdict": RETURN_PENDING,
        "at": now(),
    }
    base.durable_write(run_dir / "probe-result.json", result)
    return result


def failure_result(exc: Exception, return_required: bool) -> dict[str, Any]:
    signature = f"{type(exc).__name__}:{exc}"
    return {
        "schema": "s20plus_g986n_fastboot_getvar_failure_v1",
        "version": VERSION,
        "capability_ordinal": CAPABILITY_ORDINAL,
        "failure_class": type(exc).__name__,
        "failure_signature_sha256": hashlib.sha256(signature.encode()).hexdigest(),
        "return_required": return_required,
        "remaining_queries_forbidden": return_required,
        "device_writes": False,
        "payload_transfer": False,
        "partition_access": False,
        "replay_permitted": False,
        "verdict": (
            "RECOVERY_PENDING_S20PLUS_G986N_FASTBOOT_CENSUS_PHYSICAL_START"
            if return_required
            else "FAIL_S20PLUS_G986N_FASTBOOT_CENSUS_PRE_ENTRY_CLOSED"
        ),
        "at": now(),
    }


def query_intent_count(run_dir: Path) -> int:
    count = 0
    for ordinal, variable in enumerate(GETVARS, start=1):
        path = run_dir / f"query-{ordinal:02d}-intent.json"
        if not path.exists():
            break
        value = load_json(path, f"query {ordinal} intent")
        if (
            value.get("ordinal") != ordinal
            or value.get("variable") != variable
            or value.get("capability_ordinal") != CAPABILITY_ORDINAL
            or value.get("no_replay") is not True
        ):
            raise FastbootCensusError("query intent sequence differs")
        count += 1
    if any(
        (run_dir / f"query-{ordinal:02d}-intent.json").exists()
        for ordinal in range(count + 2, len(GETVARS) + 1)
    ):
        raise FastbootCensusError("query intent sequence has a gap")
    return count


def probe_is_complete(run_dir: Path) -> bool:
    path = run_dir / "probe-result.json"
    if not path.exists():
        return False
    probe = load_json(path, "probe result")
    if (
        probe.get("schema") != SCHEMA
        or probe.get("version") != VERSION
        or probe.get("capability_ordinal") != CAPABILITY_ORDINAL
        or probe.get("verdict") != RETURN_PENDING
        or probe.get("getvar_order") != list(GETVARS)
        or probe.get("fastboot_command_count") != len(GETVARS)
    ):
        raise FastbootCensusError("probe result differs")
    observations = probe.get("getvars")
    if not isinstance(observations, list) or len(observations) != len(GETVARS):
        raise FastbootCensusError("probe observation count differs")
    for ordinal, variable in enumerate(GETVARS, start=1):
        intent = load_json(
            run_dir / f"query-{ordinal:02d}-intent.json",
            f"query {ordinal} intent",
        )
        result = load_json(
            run_dir / f"query-{ordinal:02d}-result.json",
            f"query {ordinal} result",
        )
        if (
            intent.get("ordinal") != ordinal
            or intent.get("variable") != variable
            or intent.get("capability_ordinal") != CAPABILITY_ORDINAL
            or intent.get("no_replay") is not True
            or result.get("variable") != variable
            or result.get("capability_ordinal") != CAPABILITY_ORDINAL
            or result.get("status") not in {"VALUE", "UNSUPPORTED"}
            or result.get("intent_sha256") != object_sha256(intent)
            or observations[ordinal - 1] != result
        ):
            raise FastbootCensusError("probe query evidence differs")
    return True


def finalize_return(
    *,
    root: Path,
    run_dir: Path,
    command: Command,
    usb_inventory: UsbInventory = real_usb_inventory,
) -> dict[str, Any]:
    terminal_path = run_dir / "final-result.json"
    if terminal_path.exists():
        terminal = load_json(terminal_path, "final result")
        if (
            terminal.get("verdict") not in {FINAL_PASS, FINAL_NO_PROOF}
            or terminal.get("capability_ordinal") != CAPABILITY_ORDINAL
        ):
            raise FastbootCensusError("final result differs")
        if guard_path(root).exists():
            release_guard(root, run_dir)
        return terminal
    check_guard(root, run_dir)
    prepared = load_json(run_dir / "prepared.json", "prepared census")
    check_entry_intent(root, run_dir, prepared)
    if any(
        _is_fastboot(interface)
        for row in usb_inventory()
        for interface in row.get("interfaces", ())
    ):
        raise ReturnRequiredError("phone remains in fastboot")
    returned = collect_android_health(command, usb_inventory)
    target = prepared.get("target", {})
    if (
        returned["serial_sha256"] != target.get("serial_sha256")
        or returned["topology_sha256"] != target.get("topology_sha256")
        or returned["other_serial_sha256"] != target.get("other_serial_sha256")
    ):
        raise FastbootCensusError("returned Android identity differs")
    count = query_intent_count(run_dir)
    complete = probe_is_complete(run_dir)
    if returned["boot_id_sha256"] == target.get("boot_id_sha256"):
        raise FastbootCensusError("consumed entry intent has no fresh returned boot")
    terminal = {
        "schema": "s20plus_g986n_fastboot_getvar_final_result_v1",
        "version": VERSION,
        "capability_ordinal": CAPABILITY_ORDINAL,
        "target": target,
        "returned_android": {
            "serial_sha256": returned["serial_sha256"],
            "topology_sha256": returned["topology_sha256"],
            "boot_id_sha256": returned["boot_id_sha256"],
            "health": returned["health"],
        },
        "fastboot_query_intent_count": count,
        "all_four_queries_completed": complete,
        "fastboot_endpoint_absent_before_health": True,
        "device_writes": False,
        "payload_transfer": False,
        "partition_access": False,
        "replay_permitted": False,
        "verdict": FINAL_PASS if complete else FINAL_NO_PROOF,
        "at": now(),
    }
    base.durable_write(terminal_path, terminal)
    release_guard(root, run_dir)
    return terminal


def dry_run_plan() -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_fastboot_getvar_plan_v1",
        "version": VERSION,
        "capability_ordinal": CAPABILITY_ORDINAL,
        "required_predecessor_terminal_sha256": PREDECESSOR_FINAL_SHA256,
        "expected_target": f"{EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_INCREMENTAL}",
        "expected_usb": "18d1:d00d ff/42/03",
        "getvars": list(GETVARS),
        "raw_capture_before_parse": True,
        "one_use_entry_intent": True,
        "physical_start_and_final_health": True,
        "device_writes": False,
        "payload_transfer": False,
        "partition_access": False,
        "boot_command_sent": False,
        "live_active": LIVE_ACTIVE,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--connected", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    parser.add_argument("--operator-attended", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    if args.render_plan:
        print(json.dumps(dry_run_plan(), indent=2, sort_keys=True))
        return 0
    if not args.operator_attended:
        print("STOP_S20PLUS_FASTBOOT_CENSUS: operator attendance is required")
        return 2
    if not LIVE_ACTIVE:
        print("STOP_S20PLUS_FASTBOOT_CENSUS: reviewed activation is absent")
        return 2

    if args.connected:
        run_dir = allocate_run_dir(root)
        command = RawCommand(run_dir, "connected")
        try:
            result = connected_census(
                root=root,
                run_dir=run_dir,
                command=command,
                ready=lambda: print(
                    "READY_FOR_OPERATOR_MAGISK_BOOTLOADER_ENTRY", flush=True
                ),
            )
        except Exception as exc:
            return_required = consumed_path(root).exists()
            base.durable_write(
                run_dir / "failure.json",
                failure_result(exc, return_required),
            )
            if not return_required and guard_path(root).exists():
                try:
                    check_guard(root, run_dir)
                except FastbootCensusError:
                    pass
                else:
                    release_guard(root, run_dir)
            print(
                "RECOVERY_PENDING_S20PLUS_G986N_FASTBOOT_CENSUS_PHYSICAL_START"
                if return_required
                else "FAIL_S20PLUS_G986N_FASTBOOT_CENSUS_PRE_ENTRY_CLOSED"
            )
            print(f"run_dir={run_dir}")
            return 1
        print(result["verdict"])
        print("OPERATOR_ACTION_REQUIRED: select START with physical keys")
        print(f"run_dir={run_dir}")
        return 0

    run_dir = consumed_run_dir(root)
    if (run_dir / "final-result.json").exists():
        def command(*_args: Any) -> tuple[int, bytes, bytes]:
            raise FastbootCensusError("terminal re-emission cannot contact the device")
    else:
        command = RawCommand(
            run_dir,
            "read",
            capture_dir=allocate_finalize_capture_dir(run_dir),
        )
    try:
        result = finalize_return(
            root=root,
            run_dir=run_dir,
            command=command,
        )
    except ReturnRequiredError:
        print("RETURN_REQUIRED_S20PLUS_G986N_FASTBOOT_CENSUS: select physical START")
        return 1
    except Exception:
        print("FAIL_S20PLUS_G986N_FASTBOOT_CENSUS_FINALIZE_CLOSED")
        return 1
    print(result["verdict"])
    print(f"result={run_dir / 'final-result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
