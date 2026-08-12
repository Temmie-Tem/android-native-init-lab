#!/usr/bin/env python3
"""Attended one-shot S20+ Magisk bootstrap and mandatory stock rollback F1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time
from typing import Any, Callable

import device_action_f1_v2 as f1_core
import s20plus_g986n_d0_inventory as base
import s20plus_g986n_routine_d0 as routine
import s22plus_boot_only_f1_transport as transport


VERSION = "s20plus-g986n-magisk-bootstrap-f1-v1"
F1_ACTIVE = True
ROOT = Path(__file__).resolve().parents[5]
RUN_ROOT = Path("workspace/private/runs/s20plus-g986n-magisk-bootstrap-f1")
EXPECTED_MODEL = "SM-G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"
EXPECTED_TOPOLOGY_SHA256 = "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1"
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "73e8800248796a542c4d9d63acbfb641302dc12fe79b14d30b23771b6bbfb23b"
ODIN = Path("/usr/bin/odin4")
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
CANDIDATE = ROOT / "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1/candidate/AP.tar.md5"
CANDIDATE_SIZE = 25_835_561
CANDIDATE_SHA256 = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
ROLLBACK = ROOT / "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1/rollback/AP.tar.md5"
ROLLBACK_SIZE = 25_671_721
ROLLBACK_SHA256 = "48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b"
TRANSITION_RESULT = ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/enter-download-20260812T171215Z-1786554735803424083/result.json"
TRANSITION_RESULT_SIZE = 1_783
TRANSITION_RESULT_SHA256 = "0f62006aa71e5d1a76e87f994d2c465fa47a8d550f2fe0e3fe99c5ab18418e84"
TRANSITION_RESOLUTION = ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/enter-download-20260812T171215Z-1786554735803424083/resolution.json"
TRANSITION_RESOLUTION_SIZE = 264
TRANSITION_RESOLUTION_SHA256 = "8f2567e14f13d85722675666347cff777c7d1d4c8f56a73da25d62b145ecf27b"
ADB = base.DEFAULT_ADB
DOWNLOAD_USB = {
    "idVendor": "04e8",
    "idProduct": "685d",
    "product": "SAMSUNG USB",
    "manufacturer": "Samsung",
}
APPROVAL_PREFIX = "S20PLUS-G986N-MAGISK-BOOTSTRAP-F1-APPROVE:"
USBFS_RE = re.compile(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})")
MAX_OUTPUT = 8 * 1024 * 1024
ODIN_TIMEOUT = 300
ANDROID_TIMEOUT = 420
DOWNLOAD_TIMEOUT = 600
CLOSURE_FILES = {
    "inventory": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py",
        21_474,
        "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    ),
    "routine": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_routine_d0.py",
        12_649,
        "2377e463e1ec4869fd9ba7a5155aeb6c792bdb5b5b969c902a2b0e5a00fda77c",
    ),
    "transport": (
        ROOT / "workspace/public/src/scripts/revalidation/s22plus_boot_only_f1_transport.py",
        9_923,
        "7cf81759bc1d01e596f86129952227c3da3c778073ae78ad07ad9318e625c52f",
    ),
    "f1_core": (
        ROOT / "workspace/public/src/scripts/revalidation/device_action_f1_v2.py",
        80_200,
        "f143274b990cc8e2dfe3913539065e09b74bfb153d807652c0ea3c46571f4383",
    ),
}


class BootstrapError(RuntimeError):
    pass


Command = Callable[[list[str], float, int], tuple[int, bytes, bytes]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file(path: Path, size: int, digest: str, label: str) -> None:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BootstrapError(f"{label} is not an exact regular file")
    if metadata.st_size != size or sha256_file(path) != digest:
        raise BootstrapError(f"{label} identity mismatch")
    if path.resolve(strict=True) != path.absolute():
        raise BootstrapError(f"{label} path is indirect")


def bounded_command(argv: list[str], timeout: float, maximum: int) -> tuple[int, bytes, bytes]:
    if not argv or not 0 < timeout <= 600 or not 0 < maximum <= MAX_OUTPUT:
        raise BootstrapError("invalid command bound")
    return streaming_command(argv, timeout, maximum)


def streaming_command(argv: list[str], timeout: float, maximum: int) -> tuple[int, bytes, bytes]:
    if not argv or not 0 < timeout <= 600 or not 0 < maximum <= MAX_OUTPUT:
        raise BootstrapError("invalid command bound")
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    output = {"stdout": bytearray(), "stderr": bytearray()}
    for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            events = selector.select(min(remaining, 0.25))
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output[key.data].extend(chunk)
                if len(output["stdout"]) + len(output["stderr"]) > maximum:
                    raise BootstrapError("command output exceeded bound while running")
        returncode = process.wait(timeout=max(0.1, deadline - time.monotonic()))
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return returncode, bytes(output["stdout"]), bytes(output["stderr"])


def decode(result: tuple[int, bytes, bytes], label: str, *, stderr_ok: bool = False) -> tuple[str, str]:
    rc, stdout, stderr = result
    if rc != 0 or (stderr and not stderr_ok):
        raise BootstrapError(f"{label} failed")
    try:
        return stdout.decode("utf-8", "strict").strip(), stderr.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise BootstrapError(f"{label} output is not UTF-8") from exc


def durable_create(path: Path, value: Any) -> None:
    base.durable_write(path, value)


def fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_bytes(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_OUTPUT:
        raise BootstrapError("raw evidence exceeded its bound")
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
                raise BootstrapError("short raw evidence write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    fsync_dir(path.parent)


def closure_receipts() -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for label, (path, size, digest) in CLOSURE_FILES.items():
        require_file(path, size, digest, f"closure {label}")
        receipts[label] = {"path": str(path), "size": size, "sha256": digest}
    self_path = Path(__file__).resolve(strict=True)
    self_meta = self_path.lstat()
    if self_path.is_symlink() or not stat.S_ISREG(self_meta.st_mode):
        raise BootstrapError("runner is not a direct regular file")
    source = self_path.read_bytes()
    pattern = rb'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "[0-9a-f]{64}"'
    normalized, count = re.subn(
        pattern,
        b'EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        source,
    )
    normalized_sha256 = hashlib.sha256(normalized).hexdigest()
    if count != 1 or normalized_sha256 != EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256:
        raise BootstrapError("runner bytes do not match the reviewed normalized identity")
    receipts["runner"] = {
        "path": str(self_path),
        "size": self_meta.st_size,
        "sha256": sha256_file(self_path),
        "normalized_sha256": normalized_sha256,
    }
    receipts["adb"] = base.tool_receipt(ADB)
    return receipts


def event(run_dir: Path, ordinal: int, name: str, value: dict[str, Any]) -> Path:
    path = run_dir / "events" / f"{ordinal:02d}-{name}.json"
    path.parent.mkdir(mode=0o700, exist_ok=True)
    durable_create(path, {"schema": "s20plus_g986n_f1_event_v1", "version": VERSION, "ordinal": ordinal, "name": name, "at": utc_now(), **value})
    return path


def parse_devices(output: str) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or any(USBFS_RE.fullmatch(line) is None for line in lines):
        raise BootstrapError("Odin enumeration output is malformed")
    devices = sorted(set(lines))
    if len(devices) != 1 or len(lines) != 1:
        raise BootstrapError("Odin endpoint is absent or ambiguous")
    return devices


def read_small(path: Path) -> str | None:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return None
    if len(payload) > 512:
        raise BootstrapError("Download sysfs value is oversized")
    return payload.decode("utf-8", "strict").strip()


def endpoint_stat(path: str) -> tuple[int, int, int, int]:
    metadata = os.stat(path, follow_symlinks=False)
    if not stat.S_ISCHR(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("Odin endpoint is not a direct character device")
    return metadata.st_dev, metadata.st_ino, metadata.st_rdev, metadata.st_ctime_ns


def identify_download(
    command: Command = bounded_command,
    *,
    sys_root: Path = Path("/sys/bus/usb/devices"),
    stat_reader: Callable[[str], tuple[int, int, int, int]] = endpoint_stat,
) -> dict[str, Any]:
    stdout, _ = decode(command([str(ODIN), "-l"], 10, 64 * 1024), "Odin enumeration")
    device = parse_devices(stdout)[0]
    identity = stat_reader(device)
    coordinates = USBFS_RE.fullmatch(device)
    assert coordinates is not None
    bus, dev = str(int(coordinates.group(1))), str(int(coordinates.group(2)))
    matches: list[tuple[Path, dict[str, str | None]]] = []
    for node in sorted(sys_root.glob("[0-9]*-[0-9]*")):
        values = {name: read_small(node / name) for name in ("busnum", "devnum", *DOWNLOAD_USB, "serial")}
        if values["busnum"] == bus and values["devnum"] == dev:
            matches.append((node, values))
    if len(matches) != 1:
        raise BootstrapError("Download sysfs topology is absent or ambiguous")
    node, values = matches[0]
    repeated = {name: read_small(node / name) for name in values}
    if values != repeated or any(values[key] != value for key, value in DOWNLOAD_USB.items()) or values["serial"] not in (None, ""):
        raise BootstrapError("Download USB identity mismatch")
    topology = f"usb:{node.name}"
    if hashlib.sha256(topology.encode()).hexdigest() != EXPECTED_TOPOLOGY_SHA256:
        raise BootstrapError("Download topology differs from the exact Android target")
    if stat_reader(device) != identity:
        raise BootstrapError("Download endpoint changed during identity read")
    return {
        "device": device,
        "endpoint_identity": list(identity),
        "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": EXPECTED_TOPOLOGY_SHA256,
        "usb": {**DOWNLOAD_USB, "serial_absent": True},
    }


def validate_transition_evidence() -> dict[str, Any]:
    require_file(TRANSITION_RESULT, TRANSITION_RESULT_SIZE, TRANSITION_RESULT_SHA256, "Download dispatch result")
    require_file(TRANSITION_RESOLUTION, TRANSITION_RESOLUTION_SIZE, TRANSITION_RESOLUTION_SHA256, "Download observation resolution")
    dispatch = json.loads(TRANSITION_RESULT.read_text())
    resolution = json.loads(TRANSITION_RESOLUTION.read_text())
    if (
        dispatch.get("schema") != "s20plus_g986n_routine_action_result_v1"
        or dispatch.get("version") != "s20plus-g986n-routine-actions-v1"
        or dispatch.get("action") != "enter-download"
        or dispatch.get("verdict") != "DISPATCHED_S20PLUS_G986N_DOWNLOAD_ENTRY_PENDING"
        or dispatch.get("effect_command_count") != 1
        or dispatch.get("other_target_command_count") != 0
        or dispatch.get("s22plus_command_count") != 0
        or dispatch.get("a90_command_count") != 0
        or dispatch.get("target", {}).get("model") != EXPECTED_MODEL
        or dispatch.get("target", {}).get("device") != EXPECTED_DEVICE
        or dispatch.get("target", {}).get("product") != EXPECTED_PRODUCT
        or dispatch.get("target", {}).get("incremental") != EXPECTED_INCREMENTAL
        or dispatch.get("target", {}).get("usb_topology_sha256") != EXPECTED_TOPOLOGY_SHA256
        or dispatch.get("verification", {}).get("replay_permitted") is not False
        or resolution.get("schema") != "s20plus_g986n_control_resolution_v1"
        or resolution.get("version") != "s20plus-g986n-routine-actions-v1"
        or resolution.get("action") != "enter-download"
        or resolution.get("resolution") != "download-observed"
    ):
        raise BootstrapError("Download transition evidence is not exact")
    return {"dispatch_sha256": TRANSITION_RESULT_SHA256, "resolution_sha256": TRANSITION_RESOLUTION_SHA256}


def validate_artifacts() -> dict[str, Any]:
    require_file(ODIN, ODIN_SIZE, ODIN_SHA256, "Odin4")
    require_file(CANDIDATE, CANDIDATE_SIZE, CANDIDATE_SHA256, "candidate AP")
    require_file(ROLLBACK, ROLLBACK_SIZE, ROLLBACK_SHA256, "rollback AP")
    with transport.pin_boot_only_ap(CANDIDATE, label="candidate", expected_size=CANDIDATE_SIZE, expected_sha256=CANDIDATE_SHA256) as item:
        candidate_member = transport.boot_only_member_receipt(item, label="candidate")
    with transport.pin_boot_only_ap(ROLLBACK, label="rollback", expected_size=ROLLBACK_SIZE, expected_sha256=ROLLBACK_SHA256) as item:
        rollback_member = transport.boot_only_member_receipt(item, label="rollback")
    return {
        "candidate": {"path": str(CANDIDATE), "size": CANDIDATE_SIZE, "sha256": CANDIDATE_SHA256, "member": candidate_member},
        "rollback": {"path": str(ROLLBACK), "size": ROLLBACK_SIZE, "sha256": ROLLBACK_SHA256, "member": rollback_member},
        "odin": {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256},
    }


def binding_payload(run_dir: Path, artifacts: dict[str, Any], transition: dict[str, Any], endpoint: dict[str, Any], closure: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_magisk_bootstrap_binding_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "target": {"model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL, "topology_sha256": EXPECTED_TOPOLOGY_SHA256},
        "artifacts": artifacts,
        "transition": transition,
        "endpoint": endpoint,
        "closure": closure,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "rollback_mandatory": True,
        "candidate_replay": False,
        "root_persistence_authorized": False,
    }


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def guard_path() -> Path:
    # Share the routine-action lock name so routine D1/D0 retrieval and F1
    # cannot race even though their run evidence lives under separate roots.
    return ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"


def allocate_run_dir(requested: Path | None) -> Path:
    direct_root = ROOT / RUN_ROOT
    root = direct_root.resolve(strict=True)
    if direct_root.absolute() != root or direct_root.is_symlink() or not direct_root.is_dir():
        raise BootstrapError("private F1 root is indirect")
    candidate = requested or root / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{time.time_ns()}")
    candidate = candidate if candidate.is_absolute() else ROOT / candidate
    resolved = candidate.resolve()
    resolved.relative_to(root)
    resolved.mkdir(mode=0o700)
    fsync_dir(resolved.parent)
    return resolved


def read_guard(run_dir: Path) -> dict[str, Any]:
    path = guard_path()
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("F1 guard is not an exact regular file")
    value = json.loads(path.read_text())
    if value != {
        "schema": "s20plus_g986n_magisk_bootstrap_guard_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "unresolved": True,
    }:
        raise BootstrapError("F1 guard does not match this run")
    return value


def release_guard(run_dir: Path) -> None:
    read_guard(run_dir)
    guard_path().unlink()
    fsync_dir(guard_path().parent)


def validate_run_dir(run_dir: Path) -> Path:
    direct_root = ROOT / RUN_ROOT
    private_root = direct_root.resolve(strict=True)
    if direct_root.absolute() != private_root or direct_root.is_symlink():
        raise BootstrapError("private F1 root is indirect")
    resolved = run_dir.resolve(strict=True)
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise BootstrapError("run directory is outside the private F1 root") from exc
    metadata = run_dir.lstat()
    if resolved != run_dir.absolute() or not stat.S_ISDIR(metadata.st_mode) or run_dir.is_symlink():
        raise BootstrapError("run directory is indirect or not a directory")
    return resolved


def prepare(requested: Path | None, command: Command = bounded_command) -> Path:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    if os.path.lexists(guard_path()):
        raise BootstrapError("routine action remains unresolved")
    artifacts = validate_artifacts()
    transition = validate_transition_evidence()
    closure = closure_receipts()
    run_dir = allocate_run_dir(requested)
    guard_parent = guard_path().parent
    if guard_parent.resolve(strict=True) != guard_parent.absolute() or guard_parent.is_symlink() or not guard_parent.is_dir():
        raise BootstrapError("shared S20+ action-guard directory is indirect")
    fsync_dir(guard_path().parent.parent)
    durable_create(guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": VERSION, "run_dir": str(run_dir), "unresolved": True})
    try:
        endpoint = identify_download(command)
        binding = binding_payload(run_dir, artifacts, transition, endpoint, closure)
        binding_sha = canonical_sha(binding)
        prepared = {"schema": "s20plus_g986n_magisk_bootstrap_prepared_v1", "version": VERSION, "binding": binding, "binding_sha256": binding_sha, "approval_token": APPROVAL_PREFIX + binding_sha, "prepared_at": utc_now()}
        durable_create(run_dir / "prepared.json", prepared)
        event(run_dir, 0, "prepared", {"binding_sha256": binding_sha})
        return run_dir
    except Exception:
        if guard_path().exists():
            release_guard(run_dir)
        raise


def read_prepared(run_dir: Path) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    prepared_path = run_dir / "prepared.json"
    metadata = prepared_path.lstat()
    if prepared_path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("prepared binding is not an exact regular file")
    prepared = json.loads(prepared_path.read_text())
    if prepared.get("schema") != "s20plus_g986n_magisk_bootstrap_prepared_v1" or prepared.get("version") != VERSION:
        raise BootstrapError("prepared binding is malformed")
    if prepared.get("binding_sha256") != canonical_sha(prepared.get("binding")) or prepared.get("approval_token") != APPROVAL_PREFIX + prepared["binding_sha256"]:
        raise BootstrapError("prepared binding hash mismatch")
    if prepared["binding"].get("run_dir") != str(run_dir):
        raise BootstrapError("prepared run directory mismatch")
    if prepared["binding"].get("closure") != closure_receipts():
        raise BootstrapError("execution closure changed after preparation")
    binding = prepared["binding"]
    if binding.get("target") != {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        "topology_sha256": EXPECTED_TOPOLOGY_SHA256,
    }:
        raise BootstrapError("prepared target binding mismatch")
    if binding.get("candidate_attempts") != 1 or binding.get("rollback_attempts") != 1:
        raise BootstrapError("prepared attempt bounds mismatch")
    if binding.get("rollback_mandatory") is not True or binding.get("candidate_replay") is not False:
        raise BootstrapError("prepared recovery binding mismatch")
    return prepared


def persist_transfer(run_dir: Path, kind: str, binding_sha256: str, endpoint: dict[str, Any], outcome: tuple[dict[str, object], bytes, bytes]) -> str:
    receipt, stdout, stderr = outcome
    durable_bytes(run_dir / f"{kind}.stdout", stdout)
    durable_bytes(run_dir / f"{kind}.stderr", stderr)
    classification = f1_core.classify_odin_output(int(receipt["returncode"]), stdout, stderr)
    if receipt.get("endpoint_post_state") == "changed":
        classification = "odin_device_session_failure_or_unknown"
    durable_create(run_dir / f"{kind}-result.json", {"schema": "s20plus_g986n_f1_transfer_v1", "version": VERSION, "kind": kind, "binding_sha256": binding_sha256, "endpoint": {"device": endpoint["device"], "identity": endpoint["endpoint_identity"]}, "classification": classification, "receipt": receipt, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest()})
    return classification


def read_transfer_intent(run_dir: Path, kind: str, binding_sha256: str) -> dict[str, Any]:
    path = run_dir / f"{kind}-intent.json"
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise BootstrapError(f"{kind} intent is missing") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError(f"{kind} intent is not an exact regular file")
    value = json.loads(path.read_text())
    digest = CANDIDATE_SHA256 if kind == "candidate" else ROLLBACK_SHA256
    if (
        set(value) != {"schema", "version", "kind", "binding_sha256", "ap_sha256", "endpoint", "attempt", "no_replay", "at"}
        or value.get("schema") != "s20plus_g986n_f1_transfer_intent_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("ap_sha256") != digest
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or set(value.get("endpoint", {})) != {"device", "identity"}
        or USBFS_RE.fullmatch(value["endpoint"]["device"]) is None
        or not isinstance(value["endpoint"]["identity"], list)
        or len(value["endpoint"]["identity"]) != 4
    ):
        raise BootstrapError(f"{kind} intent is malformed or mismatched")
    return value


def read_raw_evidence(path: Path, expected_size: Any, expected_sha256: Any) -> bytes:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise BootstrapError("raw transfer evidence is missing") from exc
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("raw transfer evidence is not an exact regular file")
    if not isinstance(expected_size, int) or not 0 <= expected_size <= MAX_OUTPUT or metadata.st_size != expected_size:
        raise BootstrapError("raw transfer evidence size mismatch")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise BootstrapError("raw transfer evidence hash mismatch")
    return payload


def completed_transfer_result(run_dir: Path, kind: str, binding_sha256: str) -> dict[str, Any]:
    intent = read_transfer_intent(run_dir, kind, binding_sha256)
    path = run_dir / f"{kind}-result.json"
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError(f"{kind} result is not an exact regular file")
    value = json.loads(path.read_text())
    digest = CANDIDATE_SHA256 if kind == "candidate" else ROLLBACK_SHA256
    receipt = value.get("receipt", {})
    stdout = read_raw_evidence(run_dir / f"{kind}.stdout", receipt.get("stdout_bytes"), value.get("stdout_sha256"))
    stderr = read_raw_evidence(run_dir / f"{kind}.stderr", receipt.get("stderr_bytes"), value.get("stderr_sha256"))
    if (
        value.get("schema") != "s20plus_g986n_f1_transfer_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("endpoint") != intent.get("endpoint")
        or value.get("classification") != "odin_transfer_completed"
        or f1_core.classify_odin_output(receipt.get("returncode"), stdout, stderr) != "odin_transfer_completed"
        or receipt.get("label") != kind
        or receipt.get("returncode") != 0
        or receipt.get("command_shape") != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or receipt.get("regular_path_inputs") is not True
        or receipt.get("anonymous_proc_fd_inputs") is not False
        or receipt.get("ap", {}).get("sha256") != digest
        or receipt.get("odin", {}).get("sha256") != ODIN_SHA256
        or receipt.get("endpoint_pre_identity") != intent["endpoint"]["identity"]
        or receipt.get("endpoint_post_state") not in ("same", "absent")
    ):
        raise BootstrapError(f"{kind} completion evidence is malformed or mismatched")
    return value


def record_pending_health(run_dir: Path, final: dict[str, Any]) -> None:
    path = run_dir / f"health-observation-{time.time_ns()}.json"
    durable_create(path, {"schema": "s20plus_g986n_f1_health_observation_v1", "version": VERSION, "terminal": False, "final_health": final})


def execute_odin_exact(path: Path, size: int, digest: str, kind: str, endpoint: dict[str, Any]) -> tuple[dict[str, object], bytes, bytes]:
    expected_identity = tuple(endpoint["endpoint_identity"])
    with transport.pin_regular_file(ODIN, label="Odin4", expected_size=ODIN_SIZE, expected_sha256=ODIN_SHA256) as odin, transport.pin_boot_only_ap(path, label=kind, expected_size=size, expected_sha256=digest) as ap:
        command = transport.build_odin_boot_only_command(odin.path, ap.path, endpoint["device"])
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(ap)
        pre_identity = endpoint_stat(endpoint["device"])
        if pre_identity != expected_identity:
            raise BootstrapError("Download endpoint changed before Odin dispatch")
        returncode, stdout, stderr = streaming_command(command, ODIN_TIMEOUT, MAX_OUTPUT)
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(ap)
        try:
            post_identity = endpoint_stat(endpoint["device"])
            post_state = "same" if post_identity == expected_identity else "changed"
        except FileNotFoundError:
            post_identity = None
            post_state = "absent"
        receipt: dict[str, object] = {
            "label": kind,
            "returncode": returncode,
            "command_shape": ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"],
            "regular_path_inputs": True,
            "anonymous_proc_fd_inputs": False,
            "odin": odin.receipt(),
            "ap": ap.receipt(),
            "endpoint_path_sha256": hashlib.sha256(endpoint["device"].encode()).hexdigest(),
            "endpoint_pre_identity": list(pre_identity),
            "endpoint_post_identity": None if post_identity is None else list(post_identity),
            "endpoint_post_state": post_state,
            "stdout_bytes": len(stdout),
            "stderr_bytes": len(stderr),
        }
        return receipt, stdout, stderr


def transfer_once(run_dir: Path, kind: str, endpoint: dict[str, Any], ordinal: int, binding_sha256: str) -> str:
    if kind == "candidate":
        path, size, digest = CANDIDATE, CANDIDATE_SIZE, CANDIDATE_SHA256
    elif kind == "rollback":
        path, size, digest = ROLLBACK, ROLLBACK_SIZE, ROLLBACK_SHA256
    else:
        raise BootstrapError("unknown transfer kind")
    intent = run_dir / f"{kind}-intent.json"
    durable_create(intent, {"schema": "s20plus_g986n_f1_transfer_intent_v1", "version": VERSION, "kind": kind, "binding_sha256": binding_sha256, "ap_sha256": digest, "endpoint": {"device": endpoint["device"], "identity": endpoint["endpoint_identity"]}, "attempt": 1, "no_replay": True, "at": utc_now()})
    event(run_dir, ordinal, f"{kind}-transfer-started", {"ap_sha256": digest})
    try:
        outcome = execute_odin_exact(path, size, digest, kind, endpoint)
    except Exception as exc:
        durable_create(run_dir / f"{kind}-result.json", {"schema": "s20plus_g986n_f1_transfer_failure_v1", "kind": kind, "classification": "odin_device_session_failure_or_unknown", "error_class": type(exc).__name__, "possible_partition_effect": True})
        return "odin_device_session_failure_or_unknown"
    return persist_transfer(run_dir, kind, binding_sha256, endpoint, outcome)


def adb_rows(command: Command, adb: str) -> list[dict[str, Any]]:
    text, _ = decode(command([adb, "devices", "-l"], 10, 64 * 1024), "ADB inventory")
    return base.parse_inventory(text)


def android_health_once(command: Command, adb: str) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    first_rows = adb_rows(command, adb)
    selected = routine.select_exact_target(first_rows)
    serial = selected["serial"]
    devpath, _ = decode(command([adb, "-s", serial, "get-devpath"], 10, 64 * 1024), "Android devpath")
    if base.DEVPATH_RE.fullmatch(devpath) is None or base.sha256_text(devpath) != EXPECTED_TOPOLOGY_SHA256:
        raise BootstrapError("Android target topology mismatch")
    snapshot_text, _ = decode(command([adb, "-s", serial, "exec-out", "sh", "-c", base.REMOTE_SNAPSHOT], 20, 64 * 1024), "Android health")
    values = base.parse_snapshot(snapshot_text)
    base.validate_snapshot_binding(values, selected)
    final_rows = adb_rows(command, adb)
    final_selected = routine.select_exact_target(final_rows)
    if serial != final_selected["serial"] or base.sanitized_inventory(first_rows) != base.sanitized_inventory(final_rows):
        raise BootstrapError("Android inventory changed during exact health read")
    expected = {"model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product_name": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL, "boot_completed": "1", "bootanim": "stopped", "selinux": "Enforcing", "verified_boot_state": "orange"}
    if not all(values.get(key) == value for key, value in expected.items()):
        raise BootstrapError("Android health does not match exact target")
    identity = {"serial_sha256": base.sha256_text(serial), "topology_sha256": base.sha256_text(devpath), "boot_id_sha256": base.sha256_text(values["boot_id"])}
    return selected, values, identity


def wait_android(command: Command, adb: str, timeout: float) -> tuple[dict[str, Any], dict[str, str], dict[str, str]] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return android_health_once(command, adb)
        except Exception:
            time.sleep(2)
    return None


def root_observation(command: Command, adb: str, expected_identity: dict[str, str], timeout: float = 90) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            selected, _values, current_identity = android_health_once(command, adb)
        except Exception:
            time.sleep(3)
            continue
        if current_identity != expected_identity:
            return {"root_verified": False, "attempts": attempts, "identity_drift": True}
        serial = selected["serial"]
        try:
            rc, stdout, stderr = command([adb, "-s", serial, "shell", "su", "-c", "id"], 20, 64 * 1024)
        except Exception as exc:
            return {"root_verified": False, "attempts": attempts, "observer_uncertain": True, "failure_class": type(exc).__name__}
        text = (stdout + b"\n" + stderr).decode("utf-8", "replace")
        if rc == 0 and "uid=0(root)" in text:
            return {"root_verified": True, "attempts": attempts, "output_sha256": hashlib.sha256(text.encode()).hexdigest()}
        time.sleep(3)
    return {"root_verified": False, "attempts": attempts}


def request_rollback_download(run_dir: Path, command: Command, adb: str, binding_sha256: str, expected_identity: dict[str, str]) -> bool:
    try:
        selected, _values, current_identity = android_health_once(command, adb)
    except Exception as exc:
        durable_create(run_dir / "rollback-mode-preflight.json", {"schema": "s20plus_g986n_f1_rollback_mode_preflight_v1", "version": VERSION, "dispatch_attempted": False, "failure_class": type(exc).__name__})
        return False
    if current_identity != expected_identity:
        durable_create(run_dir / "rollback-mode-preflight.json", {"schema": "s20plus_g986n_f1_rollback_mode_preflight_v1", "version": VERSION, "dispatch_attempted": False, "identity_drift": True})
        return False
    serial = selected["serial"]
    durable_create(run_dir / "rollback-mode-intent.json", {"schema": "s20plus_g986n_f1_rollback_mode_intent_v1", "version": VERSION, "binding_sha256": binding_sha256, "action": "enter-download-for-stock-rollback", "ordinal": 1, "serial_sha256": expected_identity["serial_sha256"], "topology_sha256": expected_identity["topology_sha256"], "boot_id_sha256": expected_identity["boot_id_sha256"], "no_replay": True, "at": utc_now()})
    try:
        rc, stdout, stderr = command([adb, "-s", serial, "reboot", "download"], 20, 64 * 1024)
        durable_create(run_dir / "rollback-mode-result.json", {"schema": "s20plus_g986n_f1_rollback_mode_result_v1", "version": VERSION, "binding_sha256": binding_sha256, "returncode": rc, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(), "outcome": "dispatched" if rc == 0 and not stderr else "uncertain", "replay_permitted": False})
        return rc == 0 and not stderr
    except Exception as exc:
        durable_create(run_dir / "rollback-mode-result.json", {"schema": "s20plus_g986n_f1_rollback_mode_result_v1", "version": VERSION, "binding_sha256": binding_sha256, "outcome": "uncertain", "failure_class": type(exc).__name__, "replay_permitted": False})
        return False


def wait_download(command: Command, timeout: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return identify_download(command)
        except Exception:
            time.sleep(2)
    return None


def final_stock_health(command: Command, adb: str, prior_boot_id_sha256: str | None = None) -> dict[str, Any]:
    android = wait_android(command, adb, ANDROID_TIMEOUT)
    if android is None:
        return {"healthy": False, "reason": "android-not-returned"}
    selected, values, identity = android
    serial = selected["serial"]
    rc, stdout, stderr = command([adb, "-s", serial, "shell", "su", "-c", "id"], 20, 64 * 1024)
    if len(stdout) + len(stderr) > 64 * 1024:
        return {"healthy": False, "reason": "root-absence-output-oversized"}
    try:
        stdout_text = stdout.decode("utf-8", "strict").strip()
        stderr_text = stderr.decode("utf-8", "strict").strip()
    except UnicodeError:
        return {"healthy": False, "reason": "root-absence-output-malformed"}
    root_text = stdout_text + ("\n" if stdout_text and stderr_text else "") + stderr_text
    root_present = "uid=0(root)" in root_text
    absence_re = re.compile(r"(?:/system/bin/sh: )?su: (?:not found|inaccessible|permission denied|no such file)", re.IGNORECASE)
    expected_absence = rc == 127 and stdout_text == "" and absence_re.fullmatch(stderr_text) is not None
    if root_present:
        return {"healthy": False, "root_absent": False, "reason": "root-still-present", "root_probe_rc": rc, "root_probe_sha256": hashlib.sha256(root_text.encode()).hexdigest()}
    if not expected_absence:
        return {"healthy": False, "root_absent": None, "reason": "root-absence-observer-uncertain", "root_probe_rc": rc, "root_probe_sha256": hashlib.sha256(root_text.encode()).hexdigest()}
    try:
        _confirmed_selected, confirmed_values, confirmed_identity = android_health_once(command, adb)
    except Exception:
        return {"healthy": False, "root_absent": None, "reason": "post-root-probe-identity-uncertain"}
    if confirmed_identity != identity:
        return {"healthy": False, "root_absent": None, "reason": "post-root-probe-identity-drift"}
    boot_id_sha256 = base.sha256_text(values["boot_id"])
    boot_changed = prior_boot_id_sha256 is None or boot_id_sha256 != prior_boot_id_sha256
    return {"healthy": boot_changed, "root_absent": True, "boot_changed": boot_changed, "boot_id_sha256": boot_id_sha256, "confirmed_boot_id_sha256": base.sha256_text(confirmed_values["boot_id"]), "root_probe_rc": rc, "root_probe_sha256": hashlib.sha256(root_text.encode()).hexdigest(), "target": {"model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL}}


def execute(run_dir: Path, approval: str, command: Command = bounded_command) -> dict[str, Any]:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    prepared = read_prepared(run_dir)
    if approval != prepared["approval_token"]:
        raise BootstrapError("exact F1 approval token mismatch")
    if (run_dir / "candidate-intent.json").exists():
        raise BootstrapError("candidate attempt already exists; replay forbidden")
    validate_artifacts()
    adb = base.tool_receipt(ADB)["path"]
    endpoint = identify_download(command)
    if endpoint["endpoint_identity"] != prepared["binding"]["endpoint"]["endpoint_identity"]:
        raise BootstrapError("prepared Download endpoint changed")
    binding_sha256 = prepared["binding_sha256"]
    classification = transfer_once(run_dir, "candidate", endpoint, 1, binding_sha256)
    event(run_dir, 2, "candidate-transfer-finished", {"classification": classification})
    candidate_android = wait_android(command, adb, ANDROID_TIMEOUT) if classification == "odin_transfer_completed" else None
    root = {"root_verified": False, "attempts": 0}
    if candidate_android is not None:
        root = root_observation(command, adb, candidate_android[2])
    candidate_boot_id_sha256 = candidate_android[2]["boot_id_sha256"] if candidate_android is not None else None
    durable_create(run_dir / "candidate-observation.json", {"schema": "s20plus_g986n_f1_candidate_observation_v1", "classification": classification, "android_returned": candidate_android is not None, "boot_id_sha256": candidate_boot_id_sha256, **root})
    event(run_dir, 3, "candidate-observation-closed", {"root_verified": root["root_verified"]})
    if candidate_android is not None:
        request_rollback_download(run_dir, command, adb, binding_sha256, candidate_android[2])
    rollback_endpoint = wait_download(command, DOWNLOAD_TIMEOUT)
    if rollback_endpoint is None:
        result = {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED", "candidate_root_verified": root["root_verified"], "candidate_replay_permitted": False, "rollback_preapproved": True}
        durable_create(run_dir / "result.json", result)
        return result
    rollback_class = transfer_once(run_dir, "rollback", rollback_endpoint, 4, binding_sha256)
    event(run_dir, 5, "rollback-transfer-finished", {"classification": rollback_class})
    if rollback_class != "odin_transfer_completed":
        result = {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_UNCERTAIN", "candidate_root_verified": root["root_verified"], "candidate_replay_permitted": False, "rollback_replay_permitted": False}
        durable_create(run_dir / "result.json", result)
        return result
    completed_transfer_result(run_dir, "rollback", binding_sha256)
    final = final_stock_health(command, adb, candidate_boot_id_sha256)
    verdict = ("PASS_S20PLUS_G986N_MAGISK_ROOT_PROVEN_STOCK_ROLLBACK_HEALTHY" if root["root_verified"] and final["healthy"] else "NO_PROOF_S20PLUS_G986N_CANDIDATE_STOCK_ROLLBACK_HEALTHY" if final["healthy"] else "RECOVERY_PENDING_S20PLUS_G986N_FINAL_HEALTH")
    result = {"schema": "s20plus_g986n_magisk_bootstrap_f1_result_v1", "version": VERSION, "verdict": verdict, "candidate_transfer": classification, "candidate_root_verified": root["root_verified"], "rollback_transfer": rollback_class, "final_health": final, "candidate_replay_permitted": False, "rollback_replay_permitted": False, "other_target_command_count": 0, "s22plus_command_count": 0, "a90_command_count": 0}
    durable_create(run_dir / "result.json", result)
    if final["healthy"]:
        release_guard(run_dir)
    return result


def recover(run_dir: Path, command: Command = bounded_command) -> dict[str, Any]:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    prepared = read_prepared(run_dir)
    candidate_intent = read_transfer_intent(run_dir, "candidate", prepared["binding_sha256"])
    if candidate_intent["endpoint"] != {"device": prepared["binding"]["endpoint"]["device"], "identity": prepared["binding"]["endpoint"]["endpoint_identity"]}:
        raise BootstrapError("candidate intent does not match prepared endpoint")
    adb = base.tool_receipt(ADB)["path"]
    prior_boot_id_sha256 = None
    observation_path = run_dir / "candidate-observation.json"
    if observation_path.exists():
        observation = json.loads(observation_path.read_text())
        prior_boot_id_sha256 = observation.get("boot_id_sha256")
    if (run_dir / "rollback-intent.json").exists():
        result_path = run_dir / "rollback-result.json"
        if not result_path.exists():
            return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_OUTCOME_UNKNOWN", "rollback_replay_permitted": False}
        try:
            completed_transfer_result(run_dir, "rollback", prepared["binding_sha256"])
        except BootstrapError:
            return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_UNCERTAIN", "rollback_replay_permitted": False}
        final = final_stock_health(command, adb, prior_boot_id_sha256)
        result = {"verdict": "RECOVERED_S20PLUS_G986N_STOCK_ROLLBACK_HEALTHY" if final["healthy"] else "RECOVERY_PENDING_S20PLUS_G986N_FINAL_HEALTH", "final_health": final, "candidate_replay_permitted": False, "rollback_replay_permitted": False}
        if final["healthy"]:
            durable_create(run_dir / "recovery-result.json", result)
            release_guard(run_dir)
        else:
            record_pending_health(run_dir, final)
        return result
    endpoint = wait_download(command, DOWNLOAD_TIMEOUT)
    if endpoint is None:
        return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED"}
    rollback_class = transfer_once(run_dir, "rollback", endpoint, 4, prepared["binding_sha256"])
    if rollback_class != "odin_transfer_completed":
        return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_UNCERTAIN"}
    final = final_stock_health(command, adb, prior_boot_id_sha256)
    result = {"verdict": "RECOVERED_S20PLUS_G986N_STOCK_ROLLBACK_HEALTHY" if final["healthy"] else "RECOVERY_PENDING_S20PLUS_G986N_FINAL_HEALTH", "final_health": final, "candidate_replay_permitted": False, "rollback_replay_permitted": False}
    if final["healthy"]:
        durable_create(run_dir / "recovery-result.json", result)
        release_guard(run_dir)
    else:
        record_pending_health(run_dir, final)
    return result


def render_plan() -> dict[str, Any]:
    return {"schema": "s20plus_g986n_magisk_bootstrap_f1_plan_v1", "version": VERSION, "active": F1_ACTIVE, "target": f"{EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_INCREMENTAL}", "candidate": {"size": CANDIDATE_SIZE, "sha256": CANDIDATE_SHA256, "member": "boot.img.lz4"}, "rollback": {"size": ROLLBACK_SIZE, "sha256": ROLLBACK_SHA256, "member": "boot.img.lz4", "mandatory": True}, "candidate_attempts": 1, "rollback_attempts": 1, "candidate_replay": False, "root_persistence_authorized": False, "live_flash_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--recover", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    args = parser.parse_args()
    if args.render_plan:
        print(json.dumps(render_plan(), indent=2, sort_keys=True))
        return 0
    if args.prepare:
        try:
            run_dir = prepare(args.run_dir)
            prepared = read_prepared(run_dir)
        except Exception:
            print("FAIL_S20PLUS_G986N_F1_PREPARE_CLOSED")
            return 1
        print("PASS_S20PLUS_G986N_F1_PREPARED")
        print(f"run_dir={run_dir}")
        print(f"approval={prepared['approval_token']}")
        return 0
    if args.run_dir is None:
        print("FAIL_S20PLUS_G986N_F1_RUN_DIR_REQUIRED")
        return 1
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    try:
        result = execute(run_dir, args.approval or "") if args.execute else recover(run_dir)
    except Exception:
        print("FAIL_S20PLUS_G986N_F1_CLOSED")
        return 1
    print(result["verdict"])
    print(f"result={run_dir / ('result.json' if args.execute else 'recovery-result.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
