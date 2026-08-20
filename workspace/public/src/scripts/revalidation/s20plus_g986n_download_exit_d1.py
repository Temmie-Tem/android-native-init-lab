#!/usr/bin/env python3
"""Attended, no-payload return from Samsung Download mode to normal Android."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
from typing import Any, Callable

import s20plus_g986n_d0_inventory as base
import s20plus_g986n_routine_d0 as routine


VERSION = "s20plus-g986n-download-exit-d1-v1"
ROOT = Path(__file__).resolve().parents[5]
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-download-exit"
SHARED_GUARD = ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"
ODIN = Path("/usr/bin/odin4")
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
EXPECTED_MODEL = "SM-G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"
EXPECTED_ANDROID_TOPOLOGY_SHA256 = "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1"
EXPECTED_DOWNLOAD_TOPOLOGY_SHA256 = frozenset({
    EXPECTED_ANDROID_TOPOLOGY_SHA256,
    "ae90de878991480bf8aafc6e131953d185245aba4fa8d9cd8d0507810d2c96e1",
})
DOWNLOAD_USB = {
    "idVendor": "04e8",
    "idProduct": "685d",
    "product": "SM8250",
    "manufacturer": "Samsung",
}
USBFS_RE = re.compile(r"/dev/bus/usb/[0-9]{3}/[0-9]{3}\Z")
CONFIRM_TOKEN = "S20PLUS-G986N-DOWNLOAD-EXIT-CONFIRM"
MAX_OUTPUT = 64 * 1024
COMMAND_TIMEOUT = 120
ANDROID_TIMEOUT = 120


class ExitError(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_create(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o400)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(path.parent)


def durable_bytes(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_OUTPUT:
        raise ExitError("Odin output exceeded its bound")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o400)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(path.parent)


def canonical(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ExitError("exit JSON contains a duplicate key")
        value[key] = item
    return value


def reject_constant(value: str) -> Any:
    raise ExitError(f"exit JSON contains non-finite value {value}")


def file_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def read_json_payload(
    descriptor: int, metadata: os.stat_result, label: str
) -> bytes:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o400
        or not 0 < metadata.st_size <= MAX_OUTPUT
    ):
        raise ExitError(f"{label} is not an exact regular file")
    chunks: list[bytes] = []
    total = 0
    while total < metadata.st_size:
        chunk = os.read(descriptor, metadata.st_size - total)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    if total != metadata.st_size or os.read(descriptor, 1):
        raise ExitError(f"{label} length changed while reading")
    if file_identity(metadata) != file_identity(os.fstat(descriptor)):
        raise ExitError(f"{label} changed while reading")
    return b"".join(chunks)


def decode_json_payload(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ExitError(f"{label} is malformed") from exc
    if (
        not isinstance(value, dict)
        or payload
        != json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ):
        raise ExitError(f"{label} is malformed or noncanonical")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_receipt() -> dict[str, Any]:
    resolved = ODIN.resolve(strict=True)
    fd = os.open(resolved, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not before.st_mode & 0o111:
            raise ExitError("Odin is not an executable regular file")
        digest = hashlib.sha256()
        size = 0
        while chunk := os.read(fd, 1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    if (before.st_dev, before.st_ino, before.st_size, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_ctime_ns):
        raise ExitError("Odin changed while its identity was read")
    if resolved != ODIN or size != ODIN_SIZE or digest.hexdigest() != ODIN_SHA256:
        raise ExitError("Odin is not the reviewed executable")
    return {"path": str(resolved), "size": size, "sha256": digest.hexdigest()}


def bounded_command(argv: list[str], timeout: float, maximum: int) -> tuple[int, bytes, bytes]:
    if not argv or timeout <= 0 or maximum < 1 or maximum > MAX_OUTPUT:
        raise ExitError("invalid command bound")
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout_file, stderr=stderr_file, close_fds=True)
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if stdout_file.tell() + stderr_file.tell() > maximum:
                    process.terminate()
                    process.wait(timeout=2)
                    raise ExitError("command output exceeded its bound")
                if time.monotonic() >= deadline:
                    process.terminate()
                    process.wait(timeout=2)
                    raise ExitError("command timed out")
                time.sleep(0.05)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
            raise ExitError("command did not terminate")
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read(maximum + 1)
        stderr = stderr_file.read(maximum + 1)
    if len(stdout) + len(stderr) > maximum:
        raise ExitError("command output exceeded its bound")
    return process.returncode, stdout, stderr


def decode(result: tuple[int, bytes, bytes], label: str) -> str:
    rc, stdout, stderr = result
    if rc != 0:
        raise ExitError(f"{label} failed")
    if stderr:
        raise ExitError(f"{label} produced stderr")
    try:
        return stdout.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise ExitError(f"{label} output is malformed") from exc


def parse_listing(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if any(USBFS_RE.fullmatch(line) is None for line in lines):
        raise ExitError("Download listing is malformed")
    if len(set(lines)) != len(lines):
        raise ExitError("Download listing contains duplicates")
    return sorted(lines)


def endpoint_stat(path: str) -> tuple[int, int, int, int]:
    metadata = os.stat(path, follow_symlinks=False)
    if not stat.S_ISCHR(metadata.st_mode) or metadata.st_nlink != 1:
        raise ExitError("Download endpoint is not an exact character device")
    return metadata.st_dev, metadata.st_ino, metadata.st_rdev, metadata.st_ctime_ns


def read_small(path: Path) -> str | None:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return None
    if len(payload) > 512:
        raise ExitError("Download sysfs value is oversized")
    return payload.decode("utf-8", "strict").strip()


def identify_download(command: Command = bounded_command, *, sys_root: Path = Path("/sys/bus/usb/devices")) -> dict[str, Any]:
    listing = parse_listing(decode(command([str(ODIN), "-l"], 10, MAX_OUTPUT), "Odin enumeration"))
    if len(listing) != 1:
        raise ExitError("Download endpoint is absent or ambiguous")
    device = listing[0]
    identity = endpoint_stat(device)
    coordinates = USBFS_RE.fullmatch(device)
    assert coordinates is not None
    bus, dev = str(int(device.split("/")[-2])), str(int(device.split("/")[-1]))
    matches: list[tuple[Path, dict[str, str | None]]] = []
    for node in sorted(sys_root.glob("[0-9]*-[0-9]*")):
        values = {name: read_small(node / name) for name in ("busnum", "devnum", *DOWNLOAD_USB, "serial")}
        if values["busnum"] == bus and values["devnum"] == dev:
            matches.append((node, values))
    if len(matches) != 1:
        raise ExitError("Download topology is absent or ambiguous")
    node, values = matches[0]
    if values != {name: read_small(node / name) for name in values}:
        raise ExitError("Download identity changed during observation")
    if any(values[key] != value for key, value in DOWNLOAD_USB.items()) or values["serial"] not in (None, ""):
        raise ExitError("Download USB profile mismatch")
    topology = f"usb:{node.name}"
    topology_sha256 = hashlib.sha256(topology.encode()).hexdigest()
    if topology_sha256 not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256:
        raise ExitError("Download topology is not allowlisted")
    if endpoint_stat(device) != identity:
        raise ExitError("Download endpoint changed during observation")
    return {
        "device": device,
        "endpoint_identity": list(identity),
        "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": topology_sha256,
        "usb": {**DOWNLOAD_USB, "serial_absent": True},
    }


def validate_endpoint(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"device", "endpoint_identity", "endpoint_sha256", "topology_sha256", "usb"}
        or not isinstance(value.get("device"), str)
        or USBFS_RE.fullmatch(value.get("device", "")) is None
        or value.get("endpoint_sha256") != hashlib.sha256(value["device"].encode()).hexdigest()
        or not isinstance(value.get("endpoint_identity"), list)
        or len(value["endpoint_identity"]) != 4
        or any(isinstance(item, bool) or not isinstance(item, int) for item in value["endpoint_identity"])
        or value.get("topology_sha256") not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256
        or value.get("usb") != {**DOWNLOAD_USB, "serial_absent": True}
    ):
        raise ExitError("Download endpoint evidence is malformed")
    return value


def allocate_run_dir(requested: Path | None) -> Path:
    RUN_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    root = RUN_ROOT.resolve(strict=True)
    if RUN_ROOT.is_symlink() or RUN_ROOT.absolute() != root or not stat.S_ISDIR(RUN_ROOT.lstat().st_mode):
        raise ExitError("private exit root is indirect")
    candidate = requested or root / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{time.time_ns()}")
    candidate = candidate if candidate.is_absolute() else ROOT / candidate
    resolved = candidate.resolve()
    resolved.relative_to(root)
    resolved.mkdir(mode=0o700)
    fsync_dir(resolved.parent)
    return resolved


def validate_run_dir(run_dir: Path) -> Path:
    root = RUN_ROOT.resolve(strict=True)
    resolved = run_dir.resolve(strict=True)
    resolved.relative_to(root)
    metadata = run_dir.lstat()
    if run_dir.is_symlink() or not stat.S_ISDIR(metadata.st_mode) or resolved != run_dir.absolute():
        raise ExitError("exit run directory is indirect")
    return resolved


def acquire_guard(run_dir: Path) -> None:
    parent_meta = SHARED_GUARD.parent.lstat()
    if SHARED_GUARD.parent.is_symlink() or not stat.S_ISDIR(parent_meta.st_mode):
        raise ExitError("shared action guard directory is indirect")
    if os.path.lexists(SHARED_GUARD):
        raise ExitError("another S20 action is unresolved")
    durable_create(SHARED_GUARD, {
        "schema": "s20plus_g986n_download_exit_guard_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "unresolved": True,
    })


def release_guard(run_dir: Path) -> None:
    parent = open_guard_parent()
    try:
        _value, before = read_guard_at(parent, run_dir)
        _value, after = read_guard_at(parent, run_dir)
        current = os.stat(
            SHARED_GUARD.name, dir_fd=parent, follow_symlinks=False
        )
        if guard_identity(before) != guard_identity(after) or guard_identity(
            after
        ) != guard_identity(current):
            raise ExitError("shared guard changed before release")
        os.unlink(SHARED_GUARD.name, dir_fd=parent)
        os.fsync(parent)
    finally:
        os.close(parent)


def read_guard(run_dir: Path) -> dict[str, Any]:
    parent = open_guard_parent()
    try:
        value, _metadata = read_guard_at(parent, run_dir)
    finally:
        os.close(parent)
    return value


def guard_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return file_identity(metadata)


def open_guard_parent() -> int:
    parent = SHARED_GUARD.parent
    try:
        metadata = parent.lstat()
    except OSError as exc:
        raise ExitError("shared guard parent is unavailable") from exc
    if (
        parent.is_symlink()
        or not stat.S_ISDIR(metadata.st_mode)
        or parent.resolve(strict=True) != parent.absolute()
    ):
        raise ExitError("shared guard parent is indirect")
    descriptor = os.open(
        parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    opened = os.fstat(descriptor)
    if guard_identity(opened) != guard_identity(metadata):
        os.close(descriptor)
        raise ExitError("shared guard parent changed while opening")
    return descriptor


def read_guard_at(parent: int, run_dir: Path) -> tuple[dict[str, Any], os.stat_result]:
    try:
        descriptor = os.open(
            SHARED_GUARD.name,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=parent,
        )
    except OSError as exc:
        raise ExitError("shared action guard is missing or indirect") from exc
    try:
        metadata = os.fstat(descriptor)
        payload = read_json_payload(descriptor, metadata, "shared action guard")
    finally:
        os.close(descriptor)
    value = decode_json_payload(payload, "shared action guard")
    expected = {"schema": "s20plus_g986n_download_exit_guard_v1", "version": VERSION, "run_dir": str(run_dir), "unresolved": True}
    if set(value) != set(expected) or value != expected:
        raise ExitError("shared guard does not match this run")
    return value, metadata


def scan_exact_nodes(run_dir: Path, names: set[str]) -> None:
    actual: set[str] = set()
    with os.scandir(run_dir) as entries:
        for entry in entries:
            metadata = entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or entry.is_symlink():
                raise ExitError("exit journal contains a special or indirect node")
            actual.add(entry.name)
    if actual != names:
        raise ExitError("exit journal contains missing or extra evidence")


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError as exc:
        raise ExitError(f"{label} is missing or indirect") from exc
    try:
        metadata = os.fstat(descriptor)
        payload = read_json_payload(descriptor, metadata, label)
    finally:
        os.close(descriptor)
    return decode_json_payload(payload, label)


def read_bytes_exact(path: Path, label: str, expected_sha256: str) -> bytes:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise ExitError(f"{label} is not an exact regular file")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ExitError(f"{label} hash mismatch")
    return payload


def arm(run_dir: Path, command: Command = bounded_command) -> Path:
    run_dir = validate_run_dir(run_dir)
    tool = tool_receipt()
    acquire_guard(run_dir)
    try:
        listing = parse_listing(decode(command([str(ODIN), "-l"], 10, MAX_OUTPUT), "Odin baseline"))
        if listing:
            raise ExitError("Download baseline is not empty; disconnect the USB cable first")
        baseline = {"schema": "s20plus_g986n_download_exit_baseline_v1", "version": VERSION, "endpoint_count": 0, "listing_sha256": hashlib.sha256(b"\n".join(x.encode() for x in listing)).hexdigest(), "at": now()}
        durable_create(run_dir / "baseline.json", baseline)
        binding = {"schema": "s20plus_g986n_download_exit_binding_v1", "version": VERSION, "target": {"model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL}, "baseline_sha256": canonical(baseline), "odin": tool, "action": "exit-download", "no_payload": True, "attempt": 1, "no_replay": True}
        durable_create(run_dir / "arm-intent.json", {"schema": "s20plus_g986n_download_exit_arm_v1", "version": VERSION, "binding": binding, "binding_sha256": canonical(binding), "operator_confirmation_required": CONFIRM_TOKEN, "at": now(), "no_replay": True})
        return run_dir / "arm-intent.json"
    except Exception as exc:
        durable_create(run_dir / "failure.json", {"schema": "s20plus_g986n_download_exit_failure_v1", "version": VERSION, "failure_class": type(exc).__name__, "reason_sha256": hashlib.sha256(str(exc).encode()).hexdigest(), "effect_command_count": 0, "replay_permitted": False, "at": now()})
        release_guard(run_dir)
        raise


def android_health(
    command: Command = bounded_command,
    timeout: float = ANDROID_TIMEOUT,
    expected_topology_sha256: str = EXPECTED_ANDROID_TOPOLOGY_SHA256,
) -> dict[str, Any]:
    if expected_topology_sha256 not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256:
        raise ExitError("Android topology binding is not allowlisted")
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            text = decode(command([str(base.DEFAULT_ADB), "devices", "-l"], 10, MAX_OUTPUT), "ADB inventory")
            selected = routine.select_exact_target(base.parse_inventory(text))
            serial = selected["serial"]
            devpath = decode(command([str(base.DEFAULT_ADB), "-s", serial, "get-devpath"], 10, MAX_OUTPUT), "Android devpath").strip()
            if base.sha256_text(devpath) != expected_topology_sha256:
                raise ExitError("Android topology mismatch")
            snapshot = decode(command([str(base.DEFAULT_ADB), "-s", serial, "exec-out", "sh", "-c", base.REMOTE_SNAPSHOT], 20, MAX_OUTPUT), "Android health")
            values = base.parse_snapshot(snapshot)
            base.validate_snapshot_binding(values, selected)
            if values.get("incremental") != EXPECTED_INCREMENTAL or values.get("boot_completed") != "1" or values.get("bootanim") != "stopped" or values.get("selinux") != "Enforcing":
                raise ExitError("Android health is not stable")
            return {"serial_sha256": base.sha256_text(serial), "topology_sha256": base.sha256_text(devpath), "boot_id_sha256": base.sha256_text(values["boot_id"]), "model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL}
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise ExitError("Android normal health did not return") from last


def confirm(run_dir: Path, confirmation: str, command: Command = bounded_command) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    if confirmation != CONFIRM_TOKEN:
        raise ExitError("exit confirmation mismatch")
    arm_value = read_json(run_dir / "arm-intent.json", "arm intent")
    baseline = read_json(run_dir / "baseline.json", "Download baseline")
    binding = arm_value.get("binding")
    if arm_value.get("schema") != "s20plus_g986n_download_exit_arm_v1" or arm_value.get("version") != VERSION or arm_value.get("operator_confirmation_required") != CONFIRM_TOKEN or arm_value.get("no_replay") is not True or arm_value.get("binding_sha256") != canonical(binding) or not isinstance(binding, dict) or binding.get("schema") != "s20plus_g986n_download_exit_binding_v1" or binding.get("version") != VERSION or binding.get("action") != "exit-download" or binding.get("target") != {"model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL} or binding.get("no_payload") is not True or binding.get("attempt") != 1 or binding.get("no_replay") is not True:
        raise ExitError("arm evidence is malformed")
    if baseline.get("schema") != "s20plus_g986n_download_exit_baseline_v1" or baseline.get("version") != VERSION or baseline.get("endpoint_count") != 0 or binding.get("baseline_sha256") != canonical(baseline):
        raise ExitError("Download baseline is malformed")
    if os.path.lexists(run_dir / "exit-intent.json") or os.path.lexists(run_dir / "result.json"):
        raise ExitError("exit action already consumed")
    scan_exact_nodes(run_dir, {"baseline.json", "arm-intent.json"})
    try:
        endpoint = validate_endpoint(identify_download(command))
    except Exception as exc:
        durable_create(run_dir / "failure.json", {"schema": "s20plus_g986n_download_exit_failure_v1", "version": VERSION, "failure_class": type(exc).__name__, "reason_sha256": hashlib.sha256(str(exc).encode()).hexdigest(), "effect_command_count": 0, "replay_permitted": False, "at": now()})
        release_guard(run_dir)
        raise
    binding_sha = arm_value["binding_sha256"]
    if tool_receipt() != binding.get("odin"):
        raise ExitError("Odin changed after arm")
    read_guard(run_dir)
    durable_create(run_dir / "exit-intent.json", {"schema": "s20plus_g986n_download_exit_intent_v1", "version": VERSION, "binding_sha256": binding_sha, "action": "exit-download", "endpoint": endpoint, "command_shape": ["odin4", "--reboot", "-d", "USBFS"], "attempt": 1, "no_payload": True, "no_replay": True, "at": now()})
    pre = tuple(endpoint["endpoint_identity"])
    try:
        scan_exact_nodes(run_dir, {"baseline.json", "arm-intent.json", "exit-intent.json"})
        read_guard(run_dir)
        if endpoint_stat(endpoint["device"]) != pre:
            raise ExitError("Download endpoint changed before dispatch")
        rc, stdout, stderr = command([str(ODIN), "--reboot", "-d", endpoint["device"]], COMMAND_TIMEOUT, MAX_OUTPUT)
        durable_bytes(run_dir / "exit.stdout", stdout)
        durable_bytes(run_dir / "exit.stderr", stderr)
        try:
            post = endpoint_stat(endpoint["device"])
            post_state = "same" if post == pre else "changed"
        except (FileNotFoundError, ExitError):
            post = None
            post_state = "absent"
    except Exception as exc:
        durable_create(run_dir / "result.json", {"schema": "s20plus_g986n_download_exit_result_v1", "version": VERSION, "binding_sha256": binding_sha, "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_UNKNOWN", "failure_class": type(exc).__name__, "effect_command_count": 1, "no_replay": True, "replay_permitted": False, "at": now()})
        raise
    dispatched = rc == 0 and post_state == "absent"
    if not dispatched:
        result = {"schema": "s20plus_g986n_download_exit_result_v1", "version": VERSION, "binding_sha256": binding_sha, "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_UNKNOWN", "returncode": rc, "post_state": post_state, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(), "effect_command_count": 1, "no_replay": True, "replay_permitted": False, "at": now()}
        durable_create(run_dir / "result.json", result)
        return result
    result = {"schema": "s20plus_g986n_download_exit_result_v1", "version": VERSION, "binding_sha256": binding_sha, "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTH", "returncode": rc, "post_state": post_state, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(), "effect_command_count": 1, "no_replay": True, "replay_permitted": False, "at": now()}
    try:
        result["android"] = android_health(
            command,
            expected_topology_sha256=endpoint["topology_sha256"],
        )
        result["verdict"] = "PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY"
    except Exception as exc:
        result["health_failure_class"] = type(exc).__name__
        durable_create(run_dir / "result.json", result)
        return result
    durable_create(run_dir / "result.json", result)
    release_guard(run_dir)
    return result


def finalize(run_dir: Path, command: Command = bounded_command) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    arm_value = read_json(run_dir / "arm-intent.json", "arm intent")
    baseline = read_json(run_dir / "baseline.json", "Download baseline")
    intent = read_json(run_dir / "exit-intent.json", "exit intent")
    result = read_json(run_dir / "result.json", "exit result")
    arm_keys = {
        "schema",
        "version",
        "binding",
        "binding_sha256",
        "operator_confirmation_required",
        "at",
        "no_replay",
    }
    binding_keys = {
        "schema",
        "version",
        "target",
        "baseline_sha256",
        "odin",
        "action",
        "no_payload",
        "attempt",
        "no_replay",
    }
    baseline_keys = {
        "schema",
        "version",
        "endpoint_count",
        "listing_sha256",
        "at",
    }
    intent_keys = {
        "schema",
        "version",
        "binding_sha256",
        "action",
        "endpoint",
        "command_shape",
        "attempt",
        "no_payload",
        "no_replay",
        "at",
    }
    result_keys = {
        "schema",
        "version",
        "binding_sha256",
        "verdict",
        "returncode",
        "post_state",
        "stdout_sha256",
        "stderr_sha256",
        "effect_command_count",
        "no_replay",
        "replay_permitted",
        "at",
    }
    binding = arm_value.get("binding")
    if (
        set(arm_value) != arm_keys
        or not isinstance(binding, dict)
        or set(binding) != binding_keys
        or set(baseline) != baseline_keys
        or set(intent) != intent_keys
        or set(result) not in (result_keys, result_keys | {"health_failure_class"})
        or arm_value.get("schema") != "s20plus_g986n_download_exit_arm_v1"
        or arm_value.get("version") != VERSION
        or arm_value.get("operator_confirmation_required") != CONFIRM_TOKEN
        or arm_value.get("no_replay") is not True
        or not isinstance(arm_value.get("at"), str)
        or not arm_value["at"]
        or arm_value.get("binding_sha256") != canonical(binding)
        or binding.get("schema") != "s20plus_g986n_download_exit_binding_v1"
        or binding.get("version") != VERSION
        or binding.get("target")
        != {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
        }
        or binding.get("action") != "exit-download"
        or binding.get("no_payload") is not True
        or type(binding.get("attempt")) is not int
        or binding.get("attempt") != 1
        or binding.get("no_replay") is not True
        or binding.get("odin")
        != {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256}
        or baseline.get("schema") != "s20plus_g986n_download_exit_baseline_v1"
        or baseline.get("version") != VERSION
        or type(baseline.get("endpoint_count")) is not int
        or baseline.get("endpoint_count") != 0
        or baseline.get("listing_sha256") != hashlib.sha256(b"").hexdigest()
        or not isinstance(baseline.get("at"), str)
        or not baseline["at"]
        or binding.get("baseline_sha256") != canonical(baseline)
    ):
        raise ExitError("arm or baseline evidence is malformed")
    normal_pending = (
        result.get("verdict")
        == "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTH"
        and result.get("post_state") == "absent"
    )
    changed_unknown = (
        result.get("verdict")
        == "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_EXIT_UNKNOWN"
        and result.get("post_state") == "changed"
    )
    if intent.get("schema") != "s20plus_g986n_download_exit_intent_v1" or intent.get("version") != VERSION or intent.get("binding_sha256") != arm_value.get("binding_sha256") or intent.get("action") != "exit-download" or type(intent.get("attempt")) is not int or intent.get("attempt") != 1 or intent.get("no_payload") is not True or intent.get("no_replay") is not True or intent.get("command_shape") != ["odin4", "--reboot", "-d", "USBFS"] or not isinstance(intent.get("at"), str) or not intent["at"] or result.get("schema") != "s20plus_g986n_download_exit_result_v1" or result.get("version") != VERSION or result.get("binding_sha256") != arm_value.get("binding_sha256") or type(result.get("effect_command_count")) is not int or result.get("effect_command_count") != 1 or result.get("no_replay") is not True or result.get("replay_permitted") is not False or type(result.get("returncode")) is not int or result.get("returncode") != 0 or not isinstance(result.get("at"), str) or not result["at"] or ("health_failure_class" in result and (not normal_pending or not isinstance(result["health_failure_class"], str) or not result["health_failure_class"])) or normal_pending == changed_unknown or not isinstance(intent.get("endpoint"), dict):
        raise ExitError("exit evidence is malformed")
    validate_endpoint(intent["endpoint"])
    stdout_sha256 = result.get("stdout_sha256")
    stderr_sha256 = result.get("stderr_sha256")
    if not isinstance(stdout_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", stdout_sha256) or not isinstance(stderr_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", stderr_sha256):
        raise ExitError("exit output evidence is malformed")
    read_bytes_exact(run_dir / "exit.stdout", "exit stdout", stdout_sha256)
    read_bytes_exact(run_dir / "exit.stderr", "exit stderr", stderr_sha256)
    scan_exact_nodes(run_dir, {"baseline.json", "arm-intent.json", "exit-intent.json", "exit.stdout", "exit.stderr", "result.json"})
    if result.get("verdict") == "PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY":
        raise ExitError("exit result already finalized")
    result["android"] = android_health(
        command,
        expected_topology_sha256=intent["endpoint"]["topology_sha256"],
    )
    result["source_verdict"] = result["verdict"]
    result["exit_dispatch_proven"] = normal_pending
    result["verdict"] = (
        "PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY"
        if normal_pending
        else "PASS_S20PLUS_G986N_DOWNLOAD_EXIT_NORMAL_HEALTHY_AFTER_UNCERTAIN_DISPATCH"
    )
    result["finalized_at"] = now()
    read_guard(run_dir)
    durable_create(run_dir / "final-result.json", result)
    release_guard(run_dir)
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--arm", action="store_true")
    modes.add_argument("--confirm", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--confirmation")
    return p


def main() -> int:
    args = parser().parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    try:
        if args.arm:
            run_dir = allocate_run_dir(run_dir)
            path = arm(run_dir)
            print("PASS_S20PLUS_G986N_DOWNLOAD_EXIT_ARMED")
            print(f"run_dir={run_dir}")
            print(f"confirmation={CONFIRM_TOKEN}")
            return 0
        if args.confirm:
            result = confirm(run_dir, args.confirmation or "")
        else:
            result = finalize(run_dir)
    except Exception:
        print("FAIL_S20PLUS_G986N_DOWNLOAD_EXIT_CLOSED")
        return 1
    print(result["verdict"])
    print(f"result={run_dir / ('final-result.json' if args.finalize else 'result.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
