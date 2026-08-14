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
PRE_CANDIDATE_ABORT_ACTIVE = True
ROOT = Path(__file__).resolve().parents[5]
RUN_ROOT = Path("workspace/private/runs/s20plus-g986n-magisk-bootstrap-f1")
EXPECTED_MODEL = "SM-G986N"
EXPECTED_DEVICE = "y2q"
EXPECTED_PRODUCT = "y2qksx"
EXPECTED_INCREMENTAL = "G986NKSS8IYC2"
EXPECTED_TOPOLOGY_SHA256 = "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1"
EXPECTED_DOWNLOAD_TOPOLOGY_SHA256 = frozenset({
    "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1",
    "ae90de878991480bf8aafc6e131953d185245aba4fa8d9cd8d0507810d2c96e1",
})
EXPECTED_REVIEWED_RUNNER_NORMALIZED_SHA256 = "457c6c9c06a70b431a0c352d7707c1d421bbe89f190667eb2eab608cab49c57e"
ABANDONABLE_PREVIOUS_RUNNER_SHA256 = "d2447b21b1ab22b4def7ae309220d508e66b9de6064cc5fde702870758322976"
ABANDONABLE_PREVIOUS_NORMALIZED_SHA256 = "f85505049b899be56df0e79b95092c13afd8deaa885befce03c8e0736d1b4407"
ABANDONABLE_PREVIOUS_BINDING_SHA256 = "0e299f6f05c9846cb8584aef161c109a9bdf1007a5cf642a8c9589e46255c859"
ODIN = Path("/usr/bin/odin4")
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
CANDIDATE = ROOT / "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1/candidate/AP.tar.md5"
CANDIDATE_SIZE = 25_835_561
CANDIDATE_SHA256 = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
ROLLBACK = ROOT / "workspace/private/outputs/s20plus_g986n/magisk_boot_only_iyc2_v1/rollback/AP.tar.md5"
ROLLBACK_SIZE = 25_671_721
ROLLBACK_SHA256 = "48a11265a6730a6ab842b07f63cffe9cbdf1582a919b02abdaf1d2b9a2e0bd6b"
ADB = base.DEFAULT_ADB
DOWNLOAD_USB = {
    "idVendor": "04e8",
    "idProduct": "685d",
    "product": "SM8250",
    "manufacturer": "Samsung",
}
APPROVAL_PREFIX = "S20PLUS-G986N-MAGISK-BOOTSTRAP-F1-APPROVE:"
PHYSICAL_ROLLBACK_ARM = "S20PLUS-G986N-PHYSICAL-ROLLBACK-ARM"
PHYSICAL_ROLLBACK_CONFIRM = "S20PLUS-G986N-PHYSICAL-ROLLBACK-CONFIRM"
CANDIDATE_ENDPOINT_CONFIRM = "S20PLUS-G986N-CANDIDATE-ENDPOINT-REENUM-CONFIRM"
PRE_CANDIDATE_CLOSE_BINDING_SHA256 = "dfb6aab5ebfcc88aa516e0463b79cb5458abf26c54177a7a1f6a6fd9d3e734f4"
PRE_CANDIDATE_CLOSE_RUNNER_SHA256 = "dd039152309f093a06835df54f673811ea56be9cd5c4d78d71102decedda95cc"
PRE_CANDIDATE_CLOSE_NORMALIZED_SHA256 = "4f4b88f1851d71446e3145480523e6e40e7d68cea3d12a406febba50ace3d670"
ENDPOINT_UNCERTAIN_CLOSE_BINDING_SHA256 = "9bc9b25e4299126b239541b7808135ea5a55367543b44dc2fa5ba787a60b80d9"
ENDPOINT_UNCERTAIN_CLOSE_RUNNER_SHA256 = "41355c32876ae938b6bfa2139997d59d8f0a68ccdd568439a39710ee72edca78"
ENDPOINT_UNCERTAIN_CLOSE_NORMALIZED_SHA256 = "8b3cd4b62b5d0679907e754fb0b7e032fe182355602bb4d849ba00948913cdbc"
PRE_CANDIDATE_ABORT_COMPATIBLE_RUNNER = {
    "normalized_sha256": "6ceec9037dad1e486450a7fc1085aeb5e527b1e3d1ec7420ac6aa23f03bb823e",
    "sha256": "fe86f61166a7f719678ca74431abb0de4f1638ead514289f973601f5b47c4cda",
    "size": 105_326,
}
PRE_CANDIDATE_CONTINUATION_COMPATIBLE_RUNNER = {
    "normalized_sha256": "041a9289426d8e49f08868143004d3c7797930e4f76db20d47fd94d074814a88",
    "sha256": "5200a4bff71f0f8996530497354ddee07c5efbd9c70be5ac7c7f92c77fc4c4d5",
    "size": 126_758,
}
RECOVERY_CONTINUATION_COMPATIBLE_RUNNER = {
    "normalized_sha256": "c6de158fe6b7126441b579d2a1a025b7f9f9e4bdda294d4e499674bf6082e281",
    "sha256": "be92517849cc6ee13cc74ec987afc7cb7490e9f7b36d1e533d2006098840b953",
    "size": 134_425,
}
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
        80_851,
        "4e61a7511cc2ed103d1cac4d1afdd2c91d6edc41e30d9bc2832229286d9ee290",
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


def sha256_exact_regular_file(path: Path, label: str) -> str:
    """Hash a small journal file through one no-follow regular-file descriptor."""
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
    except FileNotFoundError as exc:
        raise BootstrapError(f"{label} is missing") from exc
    except OSError as exc:
        raise BootstrapError(f"{label} is not an exact regular file") from exc
    try:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise BootstrapError(f"{label} is not an exact regular file")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > 1024 * 1024:
                raise BootstrapError(f"{label} is oversized")
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_exact_json(path: Path, label: str) -> Any:
    """Read only a single-link regular JSON file, never following symlinks."""
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
    except FileNotFoundError as exc:
        raise BootstrapError(f"{label} is missing") from exc
    except OSError as exc:
        raise BootstrapError(f"{label} is not an exact regular file") from exc
    try:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise BootstrapError(f"{label} is not an exact regular file")
        payload = bytearray()
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > 1024 * 1024:
                raise BootstrapError(f"{label} is oversized")
        return json.loads(bytes(payload).decode("utf-8", "strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapError(f"{label} is malformed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


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


def parse_download_listing(output: str) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if any(USBFS_RE.fullmatch(line) is None for line in lines):
        raise BootstrapError("Odin enumeration output is malformed")
    devices = sorted(set(lines))
    if len(devices) != len(lines):
        raise BootstrapError("Odin enumeration contains duplicate endpoints")
    return devices


def parse_devices(output: str) -> list[str]:
    devices = parse_download_listing(output)
    if len(devices) != 1:
        raise BootstrapError("Odin endpoint is absent or ambiguous")
    return devices


def enumerate_download(command: Command = bounded_command) -> tuple[list[str], str]:
    stdout, _ = decode(command([str(ODIN), "-l"], 10, 64 * 1024), "Odin enumeration")
    return parse_download_listing(stdout), hashlib.sha256(stdout.encode()).hexdigest()


def download_baseline(command: Command = bounded_command) -> dict[str, Any]:
    devices, listing_sha256 = enumerate_download(command)
    if devices:
        raise BootstrapError("Download endpoint baseline is not empty")
    return {
        "schema": "s20plus_g986n_f1_download_baseline_v1",
        "version": VERSION,
        "endpoint_count": 0,
        "listing_sha256": listing_sha256,
        "at": utc_now(),
    }


def validate_download_baseline(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "version", "endpoint_count", "listing_sha256", "at"}
        or value.get("schema") != "s20plus_g986n_f1_download_baseline_v1"
        or value.get("version") != VERSION
        or not isinstance(value.get("endpoint_count"), int)
        or isinstance(value.get("endpoint_count"), bool)
        or value.get("endpoint_count") != 0
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("listing_sha256"))) is None
    ):
        raise BootstrapError("Download baseline is malformed")
    return value


def write_download_baseline(run_dir: Path, label: str, value: dict[str, Any]) -> Path:
    validate_download_baseline(value)
    path = run_dir / f"{label}.json"
    durable_create(path, value)
    return path


def wait_download_after_baseline(
    command: Command,
    baseline: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    validate_download_baseline(baseline)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            devices, listing_sha256 = enumerate_download(command)
            if len(devices) != 1:
                time.sleep(2)
                continue
            endpoint = identify_download(command)
            if endpoint["device"] != devices[0]:
                time.sleep(2)
                continue
            return endpoint, {
                "baseline_listing_sha256": baseline["listing_sha256"],
                "arrival_listing_sha256": listing_sha256,
                "arrival_endpoint": endpoint["device"],
            }
        except Exception:
            time.sleep(2)
    return None


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
    devices, _listing_sha256 = enumerate_download(command)
    device = parse_devices("\n".join(devices))[0]
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
    topology_sha256 = hashlib.sha256(topology.encode()).hexdigest()
    if topology_sha256 not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256:
        raise BootstrapError("Download topology differs from the exact Android target")
    if stat_reader(device) != identity:
        raise BootstrapError("Download endpoint changed during identity read")
    return {
        "device": device,
        "endpoint_identity": list(identity),
        "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": topology_sha256,
        "usb": {**DOWNLOAD_USB, "serial_absent": True},
    }


def validate_download_endpoint_record(value: Any, label: str = "Download endpoint") -> dict[str, Any]:
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
        raise BootstrapError(f"{label} is malformed or mismatched")
    return value


def endpoint_session_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Compare stable USB-session identity while excluding mutable ctime_ns."""
    validate_download_endpoint_record(left, "left Download endpoint")
    validate_download_endpoint_record(right, "right Download endpoint")
    return (
        left["device"] == right["device"]
        and left["endpoint_sha256"] == right["endpoint_sha256"]
        and left["endpoint_identity"][:3] == right["endpoint_identity"][:3]
        and left["topology_sha256"] == right["topology_sha256"]
        and left["usb"] == right["usb"]
    )


def runner_receipt_for_identity(current_closure: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    return {"path": current_closure["runner"]["path"], **identity}


def continuation_receipt_value(
    prepared: dict[str, Any],
    current_closure: dict[str, Any],
    *,
    current_runner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_f1_pre_candidate_continuation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "previous_runner": prepared["binding"]["closure"]["runner"],
        "current_runner": current_runner or current_closure["runner"],
        "candidate_intent_absent_at_rotation": True,
        "rollback_intent_absent_at_rotation": True,
        "no_replay": True,
    }


def ensure_pre_candidate_continuation(run_dir: Path, prepared: dict[str, Any]) -> None:
    current_closure = closure_receipts()
    if prepared["binding"]["closure"] == current_closure:
        return
    path = run_dir / "pre-candidate-continuation.json"
    expected = continuation_receipt_value(prepared, current_closure)
    if os.path.lexists(path):
        if read_exact_json(path, "pre-candidate continuation") != expected:
            raise BootstrapError("pre-candidate continuation evidence is malformed")
        return
    if any(os.path.lexists(run_dir / name) for name in ("candidate-intent.json", "rollback-intent.json")):
        raise BootstrapError("pre-candidate continuation was not recorded before effect intent")
    durable_create(path, expected)


def recovery_continuation_value(prepared: dict[str, Any], current_closure: dict[str, Any]) -> dict[str, Any]:
    run_dir = Path(prepared["binding"]["run_dir"])
    late_observation = run_dir / "candidate-late-observation.json"
    return {
        "schema": "s20plus_g986n_f1_recovery_continuation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "candidate_intent_sha256": sha256_exact_regular_file(run_dir / "candidate-intent.json", "candidate intent"),
        "candidate_result_sha256": sha256_exact_regular_file(run_dir / "candidate-result.json", "candidate result"),
        "candidate_observation_sha256": sha256_exact_regular_file(run_dir / "candidate-observation.json", "candidate observation"),
        "candidate_late_observation_sha256": (
            sha256_exact_regular_file(late_observation, "candidate late observation")
            if os.path.lexists(late_observation)
            else None
        ),
        "previous_runner": runner_receipt_for_identity(current_closure, RECOVERY_CONTINUATION_COMPATIBLE_RUNNER),
        "current_runner": current_closure["runner"],
        "rollback_intent_absent_at_rotation": True,
        "no_replay": True,
    }


def ensure_recovery_continuation(run_dir: Path, prepared: dict[str, Any]) -> None:
    current_closure = closure_receipts()
    if prepared["binding"]["closure"] == current_closure:
        return
    path = run_dir / "recovery-continuation.json"
    expected = recovery_continuation_value(prepared, current_closure)
    if os.path.lexists(path):
        if read_exact_json(path, "recovery continuation") != expected:
            raise BootstrapError("recovery continuation evidence is malformed")
        return
    recovery_effect_nodes = (
        "rollback-mode-intent.json", "rollback-intent.json",
        "rollback-handoff-intent.json", "rollback-handoff-confirmation.json",
    )
    if any(os.path.lexists(run_dir / name) for name in recovery_effect_nodes):
        raise BootstrapError("recovery continuation was not recorded before rollback state")
    durable_create(path, expected)


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


def validate_live_transition_binding(
    run_dir: Path,
    transition: dict[str, Any],
    endpoint: dict[str, Any],
) -> None:
    expected_transition_keys = {
        "schema",
        "version",
        "android_identity",
        "stock_root_absence",
        "baseline_sha256",
        "arrival_listing_sha256",
        "intent_sha256",
        "result_sha256",
        "observation_sha256",
        "endpoint_identity",
        "endpoint_topology_sha256",
        "replay_permitted",
    }
    identity = transition.get("android_identity", {})
    root_absence = transition.get("stock_root_absence", {})
    endpoint_identity = endpoint.get("endpoint_identity")
    endpoint_device = endpoint.get("device")
    if (
        set(transition) != expected_transition_keys
        or transition.get("schema") != "s20plus_g986n_f1_live_transition_binding_v1"
        or transition.get("version") != VERSION
        or set(identity) != {"serial_sha256", "topology_sha256", "boot_id_sha256"}
        or identity.get("topology_sha256") != EXPECTED_TOPOLOGY_SHA256
        or set(root_absence) != {"returncode", "stdout_sha256", "stderr_sha256", "identity_confirmed"}
        or not isinstance(root_absence.get("returncode"), int)
        or isinstance(root_absence.get("returncode"), bool)
        or root_absence.get("returncode") != 127
        or root_absence.get("stdout_sha256") != hashlib.sha256(b"").hexdigest()
        or re.fullmatch(r"[0-9a-f]{64}", str(root_absence.get("stderr_sha256"))) is None
        or root_absence.get("identity_confirmed") is not True
        or re.fullmatch(r"[0-9a-f]{64}", str(transition.get("baseline_sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(transition.get("arrival_listing_sha256"))) is None
        or set(endpoint) != {"device", "endpoint_identity", "endpoint_sha256", "topology_sha256", "usb"}
        or not isinstance(endpoint_device, str)
        or USBFS_RE.fullmatch(endpoint_device) is None
        or endpoint.get("endpoint_sha256") != hashlib.sha256(endpoint_device.encode()).hexdigest()
        or not isinstance(endpoint_identity, list)
        or len(endpoint_identity) != 4
        or any(not isinstance(item, int) or isinstance(item, bool) for item in endpoint_identity)
        or endpoint.get("topology_sha256") not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256
        or endpoint.get("usb") != {**DOWNLOAD_USB, "serial_absent": True}
        or transition.get("endpoint_identity") != endpoint.get("endpoint_identity")
        or transition.get("endpoint_topology_sha256") != endpoint.get("topology_sha256")
        or transition.get("replay_permitted") is not False
    ):
        raise BootstrapError("prepared live transition binding is malformed")
    paths = {
        "intent_sha256": run_dir / "initial-download-intent.json",
        "result_sha256": run_dir / "initial-download-result.json",
        "observation_sha256": run_dir / "initial-download-observation.json",
    }
    values: dict[str, Any] = {}
    for key, path in paths.items():
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise BootstrapError("live transition evidence is not an exact regular file")
        if sha256_file(path) != transition[key]:
            raise BootstrapError("live transition evidence hash mismatch")
        values[key] = json.loads(path.read_text())
    intent = values["intent_sha256"]
    result = values["result_sha256"]
    observation = values["observation_sha256"]
    expected_target = {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        **identity,
    }
    if (
        set(intent) != {"schema", "version", "action", "target", "stock_root_absence", "baseline_sha256", "attempt", "no_replay", "at"}
        or intent.get("schema") != "s20plus_g986n_f1_initial_download_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("action") != "enter-download-for-candidate-session"
        or intent.get("target") != expected_target
        or intent.get("stock_root_absence") != root_absence
        or intent.get("baseline_sha256") != transition.get("baseline_sha256")
        or isinstance(intent.get("attempt"), bool)
        or not isinstance(intent.get("attempt"), int)
        or intent.get("attempt") != 1
        or intent.get("no_replay") is not True
        or set(result) != {"schema", "version", "action", "attempt", "returncode", "stdout_sha256", "stderr_sha256", "outcome", "replay_permitted", "at"}
        or result.get("schema") != "s20plus_g986n_f1_initial_download_result_v1"
        or result.get("version") != VERSION
        or result.get("action") != intent["action"]
        or not isinstance(result.get("attempt"), int)
        or isinstance(result.get("attempt"), bool)
        or result.get("attempt") != 1
        or not isinstance(result.get("returncode"), int)
        or isinstance(result.get("returncode"), bool)
        or result.get("returncode") != 0
        or result.get("stdout_sha256") != hashlib.sha256(b"").hexdigest()
        or result.get("stderr_sha256") != hashlib.sha256(b"").hexdigest()
        or result.get("outcome") != "dispatched"
        or result.get("replay_permitted") is not False
        or set(observation) != {"schema", "version", "action", "resolution", "endpoint", "baseline_sha256", "arrival_listing_sha256", "at"}
        or observation.get("schema") != "s20plus_g986n_f1_initial_download_observation_v1"
        or observation.get("version") != VERSION
        or observation.get("action") != intent["action"]
        or observation.get("resolution") != "download-observed"
        or observation.get("baseline_sha256") != transition.get("baseline_sha256")
        or observation.get("arrival_listing_sha256") != transition.get("arrival_listing_sha256")
        or observation.get("endpoint") != endpoint
    ):
        raise BootstrapError("live transition evidence is malformed or mismatched")
    baseline_path = run_dir / "initial-download-baseline.json"
    baseline_meta = baseline_path.lstat()
    if baseline_path.is_symlink() or not stat.S_ISREG(baseline_meta.st_mode) or baseline_meta.st_nlink != 1:
        raise BootstrapError("initial Download baseline is not an exact regular file")
    baseline = validate_download_baseline(json.loads(baseline_path.read_text()))
    if canonical_sha(baseline) != transition.get("baseline_sha256"):
        raise BootstrapError("initial Download baseline hash mismatch")


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


def compatible_continuation_journal_consistent(run_dir: Path) -> bool:
    candidate_intent = os.path.lexists(run_dir / "candidate-intent.json")
    rollback_intent = os.path.lexists(run_dir / "rollback-intent.json")
    candidate_followups = (
        "candidate-result.json", "candidate.stdout", "candidate.stderr",
        "candidate-observation.json", "candidate-late-observation.json",
        "recovery-continuation.json",
    )
    rollback_followups = ("rollback-result.json", "rollback.stdout", "rollback.stderr")
    post_candidate = (
        "rollback-mode-preflight.json", "rollback-mode-baseline.json",
        "rollback-mode-intent.json", "rollback-mode-result.json",
        "rollback-mode-observation.json", "rollback-handoff-intent.json",
        "rollback-handoff-baseline.json", "rollback-handoff-confirmation.json",
    )
    if any(os.path.lexists(run_dir / name) for name in candidate_followups) and not candidate_intent:
        return False
    if rollback_intent and not candidate_intent:
        return False
    if any(os.path.lexists(run_dir / name) for name in rollback_followups) and not rollback_intent:
        return False
    if any(os.path.lexists(run_dir / name) for name in post_candidate) and not candidate_intent:
        return False
    return True


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
    closure = closure_receipts()
    run_dir = allocate_run_dir(requested)
    guard_parent = guard_path().parent
    if guard_parent.resolve(strict=True) != guard_parent.absolute() or guard_parent.is_symlink() or not guard_parent.is_dir():
        raise BootstrapError("shared S20+ action-guard directory is indirect")
    fsync_dir(guard_path().parent.parent)
    durable_create(guard_path(), {"schema": "s20plus_g986n_magisk_bootstrap_guard_v1", "version": VERSION, "run_dir": str(run_dir), "unresolved": True})
    try:
        adb = closure["adb"]["path"]
        transition, endpoint = transition_android_to_download(run_dir, command, adb)
        binding = binding_payload(run_dir, artifacts, transition, endpoint, closure)
        binding_sha = canonical_sha(binding)
        prepared = {"schema": "s20plus_g986n_magisk_bootstrap_prepared_v1", "version": VERSION, "binding": binding, "binding_sha256": binding_sha, "approval_token": APPROVAL_PREFIX + binding_sha, "prepared_at": utc_now()}
        durable_create(run_dir / "prepared.json", prepared)
        event(run_dir, 0, "prepared", {"binding_sha256": binding_sha})
        return run_dir
    except Exception:
        # Before a durable transition intent there was no device effect and the
        # run may close.  Once the intent exists the exact reboot is no-replay;
        # retain the guard for attended observation or reviewed recovery.
        if guard_path().exists() and not (run_dir / "initial-download-intent.json").exists():
            release_guard(run_dir)
        raise


def read_prepared(run_dir: Path, *, allow_pre_candidate_compatible: bool = False) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    prepared_path = run_dir / "prepared.json"
    metadata = prepared_path.lstat()
    if prepared_path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("prepared binding is not an exact regular file")
    prepared = json.loads(prepared_path.read_text())
    if (
        set(prepared) != {"schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"}
        or prepared.get("schema") != "s20plus_g986n_magisk_bootstrap_prepared_v1"
        or prepared.get("version") != VERSION
    ):
        raise BootstrapError("prepared binding is malformed")
    if prepared.get("binding_sha256") != canonical_sha(prepared.get("binding")) or prepared.get("approval_token") != APPROVAL_PREFIX + prepared["binding_sha256"]:
        raise BootstrapError("prepared binding hash mismatch")
    if prepared["binding"].get("run_dir") != str(run_dir):
        raise BootstrapError("prepared run directory mismatch")
    binding = prepared["binding"]
    if set(binding) != {
        "schema",
        "version",
        "run_dir",
        "target",
        "artifacts",
        "transition",
        "endpoint",
        "closure",
        "candidate_attempts",
        "rollback_attempts",
        "rollback_mandatory",
        "candidate_replay",
        "root_persistence_authorized",
    }:
        raise BootstrapError("prepared binding fields are not exact")
    current_closure = closure_receipts()
    prepared_closure = binding.get("closure")
    if prepared_closure != current_closure:
        previous_runner = prepared_closure.get("runner", {}) if isinstance(prepared_closure, dict) else {}
        previous_identity = {key: previous_runner.get(key) for key in ("size", "sha256", "normalized_sha256")}
        rotated_closure = dict(prepared_closure) if isinstance(prepared_closure, dict) else {}
        rotated_closure["runner"] = current_closure["runner"]
        effect_nodes = (
            "candidate-intent.json", "candidate-result.json", "candidate.stdout",
            "candidate.stderr", "candidate-observation.json", "candidate-late-observation.json",
            "recovery-continuation.json", "rollback-intent.json",
            "rollback-result.json", "rollback.stdout", "rollback.stderr",
            "rollback-mode-preflight.json", "rollback-mode-baseline.json",
            "rollback-mode-intent.json", "rollback-mode-result.json",
            "rollback-mode-observation.json", "rollback-handoff-intent.json",
            "rollback-handoff-baseline.json", "rollback-handoff-confirmation.json",
        )
        effects_present = any(os.path.lexists(run_dir / name) for name in effect_nodes)
        continuation_ok = not effects_present
        if effects_present and os.path.lexists(run_dir / "pre-candidate-continuation.json"):
            continuation_value = read_exact_json(
                run_dir / "pre-candidate-continuation.json",
                "pre-candidate continuation",
            )
            historical_runner = runner_receipt_for_identity(current_closure, RECOVERY_CONTINUATION_COMPATIBLE_RUNNER)
            historical_continuation = continuation_receipt_value(
                prepared,
                current_closure,
                current_runner=historical_runner,
            )
            # Once candidate evidence exists, this compatibility lane is only
            # valid for the exact reviewed predecessor that performed the one
            # candidate transfer.  A self-asserted current-run continuation
            # must not transfer historical effect authority.
            continuation_ok = False
            if continuation_value == historical_continuation:
                recovery_nodes = (
                    "rollback-mode-intent.json", "rollback-mode-result.json",
                    "rollback-mode-observation.json", "rollback-intent.json",
                    "rollback-result.json", "rollback-handoff-intent.json",
                    "rollback-handoff-baseline.json", "rollback-handoff-confirmation.json",
                )
                recovery_started = any(os.path.lexists(run_dir / name) for name in recovery_nodes)
                recovery_receipt_ok = not recovery_started
                if recovery_started and os.path.lexists(run_dir / "recovery-continuation.json"):
                    recovery_receipt_ok = read_exact_json(
                        run_dir / "recovery-continuation.json",
                        "recovery continuation",
                    ) == recovery_continuation_value(prepared, current_closure)
                continuation_ok = recovery_receipt_ok
        if (
            not allow_pre_candidate_compatible
            or previous_identity != PRE_CANDIDATE_CONTINUATION_COMPATIBLE_RUNNER
            or previous_runner.get("path") != current_closure["runner"]["path"]
            or rotated_closure != current_closure
            or not compatible_continuation_journal_consistent(run_dir)
            or not continuation_ok
        ):
            raise BootstrapError("execution closure changed after preparation")
    if binding.get("target") != {
        "model": EXPECTED_MODEL,
        "device": EXPECTED_DEVICE,
        "product": EXPECTED_PRODUCT,
        "incremental": EXPECTED_INCREMENTAL,
        "topology_sha256": EXPECTED_TOPOLOGY_SHA256,
    }:
        raise BootstrapError("prepared target binding mismatch")
    if binding.get("artifacts") != validate_artifacts():
        raise BootstrapError("prepared artifact binding mismatch")
    validate_live_transition_binding(run_dir, binding.get("transition", {}), binding.get("endpoint", {}))
    if (
        not isinstance(binding.get("candidate_attempts"), int)
        or isinstance(binding.get("candidate_attempts"), bool)
        or binding.get("candidate_attempts") != 1
        or not isinstance(binding.get("rollback_attempts"), int)
        or isinstance(binding.get("rollback_attempts"), bool)
        or binding.get("rollback_attempts") != 1
    ):
        raise BootstrapError("prepared attempt bounds mismatch")
    if binding.get("rollback_mandatory") is not True or binding.get("candidate_replay") is not False:
        raise BootstrapError("prepared recovery binding mismatch")
    return prepared


def read_prepared_for_pre_effect_abandon(run_dir: Path) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    prepared_path = run_dir / "prepared.json"
    metadata = prepared_path.lstat()
    if prepared_path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("prepared binding is not an exact regular file")
    prepared = json.loads(prepared_path.read_text())
    if (
        prepared.get("schema") != "s20plus_g986n_magisk_bootstrap_prepared_v1"
        or prepared.get("version") != VERSION
        or prepared.get("binding_sha256") != canonical_sha(prepared.get("binding"))
        or prepared.get("approval_token") != APPROVAL_PREFIX + prepared["binding_sha256"]
        or prepared.get("binding", {}).get("run_dir") != str(run_dir)
        or prepared.get("binding_sha256") != ABANDONABLE_PREVIOUS_BINDING_SHA256
        or prepared.get("binding", {}).get("closure", {}).get("runner", {}).get("sha256") != ABANDONABLE_PREVIOUS_RUNNER_SHA256
        or prepared.get("binding", {}).get("closure", {}).get("runner", {}).get("normalized_sha256") != ABANDONABLE_PREVIOUS_NORMALIZED_SHA256
    ):
        raise BootstrapError("previous prepared binding is not exactly abandonable")
    return prepared


def abandon_pre_effect(run_dir: Path) -> Path:
    prepared = read_prepared_for_pre_effect_abandon(run_dir)
    expected = {
        run_dir / "prepared.json": "regular",
        run_dir / "events": "directory",
        run_dir / "events" / "00-prepared.json": "regular",
    }
    actual: dict[Path, str] = {}
    pending = [run_dir]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode):
                    kind = "regular"
                elif stat.S_ISDIR(metadata.st_mode):
                    kind = "directory"
                    pending.append(path)
                else:
                    kind = "special"
                actual[path] = kind
    if actual != expected:
        raise BootstrapError("prepared run has possible effect or unexpected evidence")
    prepared_event_path = run_dir / "events" / "00-prepared.json"
    event_meta = prepared_event_path.lstat()
    if prepared_event_path.is_symlink() or not stat.S_ISREG(event_meta.st_mode) or event_meta.st_nlink != 1:
        raise BootstrapError("prepared event is not an exact regular file")
    prepared_event = json.loads(prepared_event_path.read_text())
    if (
        set(prepared_event) != {"schema", "version", "ordinal", "name", "at", "binding_sha256"}
        or prepared_event.get("schema") != "s20plus_g986n_f1_event_v1"
        or prepared_event.get("version") != VERSION
        or not isinstance(prepared_event.get("ordinal"), int)
        or isinstance(prepared_event.get("ordinal"), bool)
        or prepared_event.get("ordinal") != 0
        or prepared_event.get("name") != "prepared"
        or prepared_event.get("binding_sha256") != prepared["binding_sha256"]
    ):
        raise BootstrapError("prepared event is malformed or mismatched")
    path = run_dir / "abandoned-pre-effect.json"
    durable_create(path, {"schema": "s20plus_g986n_f1_pre_effect_abandon_v1", "version": VERSION, "binding_sha256": prepared["binding_sha256"], "candidate_intent_absent": True, "rollback_intent_absent": True, "device_effects": 0, "reason": "ephemeral-download-endpoint-session-binding", "at": utc_now()})
    release_guard(run_dir)
    return path


def read_prepared_for_pre_candidate_abort(run_dir: Path) -> dict[str, Any]:
    """Validate a current or reviewed-compatible prepared run for zero-payload abort."""
    run_dir = validate_run_dir(run_dir)
    read_guard(run_dir)
    prepared = read_exact_json(run_dir / "prepared.json", "prepared binding")
    if (
        not isinstance(prepared, dict)
        or set(prepared) != {"schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"}
        or prepared.get("schema") != "s20plus_g986n_magisk_bootstrap_prepared_v1"
        or prepared.get("version") != VERSION
        or prepared.get("binding_sha256") != canonical_sha(prepared.get("binding"))
        or prepared.get("approval_token") != APPROVAL_PREFIX + prepared["binding_sha256"]
    ):
        raise BootstrapError("prepared binding is malformed or mismatched")
    binding = prepared["binding"]
    if (
        not isinstance(binding, dict)
        or set(binding) != {
            "schema", "version", "run_dir", "target", "artifacts", "transition",
            "endpoint", "closure", "candidate_attempts", "rollback_attempts",
            "rollback_mandatory", "candidate_replay", "root_persistence_authorized",
        }
        or binding.get("schema") != "s20plus_g986n_magisk_bootstrap_binding_v1"
        or binding.get("version") != VERSION
        or binding.get("run_dir") != str(run_dir)
        or binding.get("target") != {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            "topology_sha256": EXPECTED_TOPOLOGY_SHA256,
        }
        or not isinstance(binding.get("candidate_attempts"), int)
        or isinstance(binding.get("candidate_attempts"), bool)
        or binding.get("candidate_attempts") != 1
        or not isinstance(binding.get("rollback_attempts"), int)
        or isinstance(binding.get("rollback_attempts"), bool)
        or binding.get("rollback_attempts") != 1
        or binding.get("rollback_mandatory") is not True
        or binding.get("candidate_replay") is not False
        or binding.get("root_persistence_authorized") is not False
    ):
        raise BootstrapError("pre-candidate abort binding is not exact")
    expected_artifacts = {
        "candidate": {
            "path": str(CANDIDATE),
            "size": CANDIDATE_SIZE,
            "sha256": CANDIDATE_SHA256,
            "member": {
                "name": "boot.img.lz4",
                "size": 25_833_304,
                "sha256": "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5",
            },
        },
        "rollback": {
            "path": str(ROLLBACK),
            "size": ROLLBACK_SIZE,
            "sha256": ROLLBACK_SHA256,
            "member": {
                "name": "boot.img.lz4",
                "size": 25_667_811,
                "sha256": "c2bb08fcbaf492bb0e9bd5dc119633e17b97539f7cd954d88c20c80d046ca29e",
            },
        },
        "odin": {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256},
    }
    if binding.get("artifacts") != expected_artifacts:
        raise BootstrapError("pre-candidate abort artifact binding is not exact")
    closure = binding.get("closure")
    if not isinstance(closure, dict) or set(closure) != {*CLOSURE_FILES, "runner", "adb"}:
        raise BootstrapError("pre-candidate abort closure is malformed")
    for label, (path, size, digest) in CLOSURE_FILES.items():
        if closure.get(label) != {"path": str(path), "size": size, "sha256": digest}:
            raise BootstrapError("pre-candidate abort helper closure changed")
    adb_receipt = closure.get("adb")
    if (
        not isinstance(adb_receipt, dict)
        or adb_receipt.get("path") != str(base.EXPECTED_ADB_REALPATH)
        or adb_receipt.get("size") != 716_968
        or adb_receipt.get("sha256") != base.EXPECTED_ADB_SHA256
    ):
        raise BootstrapError("pre-candidate abort ADB closure changed")
    runner = closure.get("runner")
    current_runner = closure_receipts()["runner"]
    compatible_runner = {
        "path": str(Path(__file__).resolve(strict=True)),
        **PRE_CANDIDATE_ABORT_COMPATIBLE_RUNNER,
    }
    if runner not in (current_runner, compatible_runner):
        raise BootstrapError("prepared runner is not compatible with pre-candidate abort")
    validate_download_endpoint_record(binding.get("endpoint"), "prepared Download endpoint")
    validate_live_transition_binding(run_dir, binding.get("transition", {}), binding["endpoint"])
    return prepared


def validate_pre_candidate_abort_state(run_dir: Path, prepared: dict[str, Any]) -> None:
    required = {
        "prepared.json",
        "initial-download-baseline.json",
        "initial-download-intent.json",
        "initial-download-observation.json",
        "initial-download-result.json",
        "events/00-prepared.json",
    }
    optional = {"candidate-endpoint-reenumeration.json", "result.json"}
    resume = {
        "pre-candidate-abort-intent.json",
        "pre-candidate-abort.stdout",
        "pre-candidate-abort.stderr",
        "pre-candidate-abort-result.json",
    }
    actual: set[str] = set()
    pending = [(run_dir, "")]
    while pending:
        directory, prefix = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = f"{prefix}{entry.name}"
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode) and not entry.is_symlink():
                    if relative != "events":
                        raise BootstrapError("pre-candidate abort journal contains an unexpected directory")
                    pending.append((Path(entry.path), "events/"))
                    continue
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or entry.is_symlink():
                    raise BootstrapError("pre-candidate abort journal contains an indirect or special node")
                actual.add(relative)
    if not required.issubset(actual) or not actual.issubset(required | optional | resume):
        raise BootstrapError("pre-candidate abort journal contains missing or possible-effect evidence")
    prepared_event = read_exact_json(run_dir / "events" / "00-prepared.json", "prepared event")
    if (
        not isinstance(prepared_event, dict)
        or set(prepared_event) != {"schema", "version", "ordinal", "name", "at", "binding_sha256"}
        or prepared_event.get("schema") != "s20plus_g986n_f1_event_v1"
        or prepared_event.get("version") != VERSION
        or not isinstance(prepared_event.get("ordinal"), int)
        or isinstance(prepared_event.get("ordinal"), bool)
        or prepared_event.get("ordinal") != 0
        or prepared_event.get("name") != "prepared"
        or prepared_event.get("binding_sha256") != prepared["binding_sha256"]
    ):
        raise BootstrapError("prepared event is malformed or mismatched")
    if any(name in actual for name in ("candidate-intent.json", "candidate-result.json", "candidate.stdout", "candidate.stderr", "candidate-observation.json", "candidate-endpoint-confirmation.json", "rollback-intent.json", "rollback-result.json", "rollback.stdout", "rollback.stderr")):
        raise BootstrapError("candidate or rollback effect evidence forbids pre-candidate abort")
    has_reenumeration = "candidate-endpoint-reenumeration.json" in actual
    has_result = "result.json" in actual
    if has_reenumeration != has_result:
        raise BootstrapError("pre-candidate abort pending evidence is incomplete")
    if has_reenumeration:
        validate_candidate_endpoint_reenumeration(run_dir, prepared)
        result = read_exact_json(run_dir / "result.json", "pre-candidate result")
        if (
            not isinstance(result, dict)
            or set(result) != {"schema", "version", "verdict", "candidate_replay_permitted", "rollback_replay_permitted", "candidate_endpoint_confirmation_required"}
            or result.get("schema") != "s20plus_g986n_magisk_bootstrap_f1_result_v1"
            or result.get("version") != VERSION
            or result.get("verdict") != "RECOVERY_PENDING_S20PLUS_G986N_CANDIDATE_ENDPOINT_CONFIRMATION_REQUIRED"
            or result.get("candidate_replay_permitted") is not False
            or result.get("rollback_replay_permitted") is not False
            or result.get("candidate_endpoint_confirmation_required") != CANDIDATE_ENDPOINT_CONFIRM
        ):
            raise BootstrapError("pre-candidate result is malformed or mismatched")
    abort_nodes = actual & resume
    if abort_nodes:
        if not {"pre-candidate-abort-intent.json", "pre-candidate-abort-result.json"}.issubset(abort_nodes):
            raise BootstrapError("pre-candidate abort dispatch evidence is incomplete")
        raw_nodes = abort_nodes & {"pre-candidate-abort.stdout", "pre-candidate-abort.stderr"}
        if raw_nodes and raw_nodes != {"pre-candidate-abort.stdout", "pre-candidate-abort.stderr"}:
            raise BootstrapError("pre-candidate abort raw evidence is incomplete")


def validate_pre_candidate_abort_return(
    prepared: dict[str, Any],
    identity: dict[str, str],
) -> None:
    prepared_identity = prepared["binding"]["transition"]["android_identity"]
    if (
        identity.get("serial_sha256") != prepared_identity.get("serial_sha256")
        or identity.get("topology_sha256") != prepared_identity.get("topology_sha256")
        or re.fullmatch(r"[0-9a-f]{64}", str(identity.get("boot_id_sha256"))) is None
        or identity.get("boot_id_sha256") == prepared_identity.get("boot_id_sha256")
    ):
        raise BootstrapError("normal return does not match the prepared S20+ transition")


def expected_pre_candidate_abort_endpoint(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    if os.path.lexists(run_dir / "candidate-endpoint-reenumeration.json"):
        validate_candidate_endpoint_reenumeration(run_dir, prepared)
        raise BootstrapError("re-enumerated Download endpoint is not eligible for payload-free abort dispatch")
    return validate_download_endpoint_record(prepared["binding"]["endpoint"], "prepared Download endpoint")


def validate_pre_candidate_abort_dispatch(
    run_dir: Path,
    prepared: dict[str, Any],
) -> dict[str, Any]:
    intent = read_exact_json(run_dir / "pre-candidate-abort-intent.json", "pre-candidate abort intent")
    result = read_exact_json(run_dir / "pre-candidate-abort-result.json", "pre-candidate abort result")
    endpoint = intent.get("endpoint") if isinstance(intent, dict) else None
    if (
        not isinstance(intent, dict)
        or set(intent) != {"schema", "version", "binding_sha256", "action", "endpoint", "command_shape", "attempt", "partition_payload", "no_replay", "at"}
        or intent.get("schema") != "s20plus_g986n_f1_pre_candidate_abort_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("binding_sha256") != prepared["binding_sha256"]
        or intent.get("action") != "payload-free-normal-return"
        or intent.get("command_shape") != ["odin4", "--reboot", "-d", "USBFS"]
        or isinstance(intent.get("attempt"), bool)
        or not isinstance(intent.get("attempt"), int)
        or intent.get("attempt") != 1
        or intent.get("partition_payload") is not False
        or intent.get("no_replay") is not True
    ):
        raise BootstrapError("pre-candidate abort intent is malformed")
    validate_download_endpoint_record(endpoint, "pre-candidate abort endpoint")
    expected_endpoint = expected_pre_candidate_abort_endpoint(run_dir, prepared)
    if endpoint != expected_endpoint:
        raise BootstrapError("pre-candidate abort endpoint lost exact transition continuity")
    if not isinstance(result, dict):
        raise BootstrapError("pre-candidate abort result is malformed")
    common = {
        "schema", "version", "binding_sha256", "action", "verdict",
        "effect_command_count", "partition_transfer_count", "no_replay",
        "replay_permitted", "at",
    }
    dispatched = set(result) == common | {"returncode", "post_state", "stdout_sha256", "stderr_sha256"}
    failed = set(result) == common | {"failure_class"}
    if (
        not (dispatched or failed)
        or result.get("schema") != "s20plus_g986n_f1_pre_candidate_abort_result_v1"
        or result.get("version") != VERSION
        or result.get("binding_sha256") != prepared["binding_sha256"]
        or result.get("action") != intent["action"]
        or isinstance(result.get("effect_command_count"), bool)
        or not isinstance(result.get("effect_command_count"), int)
        or isinstance(result.get("partition_transfer_count"), bool)
        or not isinstance(result.get("partition_transfer_count"), int)
        or result.get("partition_transfer_count") != 0
        or result.get("no_replay") is not True
        or result.get("replay_permitted") is not False
    ):
        raise BootstrapError("pre-candidate abort result is malformed")
    stdout_path = run_dir / "pre-candidate-abort.stdout"
    stderr_path = run_dir / "pre-candidate-abort.stderr"
    if dispatched:
        stdout_sha256 = result.get("stdout_sha256")
        stderr_sha256 = result.get("stderr_sha256")
        if (
            result.get("effect_command_count") != 1
            or isinstance(result.get("returncode"), bool)
            or not isinstance(result.get("returncode"), int)
            or result.get("returncode") != 0
            or result.get("post_state") != "absent"
            or result.get("verdict") != "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH"
            or re.fullmatch(r"[0-9a-f]{64}", str(stdout_sha256)) is None
            or re.fullmatch(r"[0-9a-f]{64}", str(stderr_sha256)) is None
        ):
            raise BootstrapError("pre-candidate abort dispatch result is not successful")
        read_raw_evidence(stdout_path, stdout_path.stat().st_size, stdout_sha256)
        read_raw_evidence(stderr_path, stderr_path.stat().st_size, stderr_sha256)
    else:
        if (
            result.get("effect_command_count") != 0
            or result.get("verdict") != "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_UNKNOWN"
            or not isinstance(result.get("failure_class"), str)
            or os.path.lexists(stdout_path)
            or os.path.lexists(stderr_path)
        ):
            raise BootstrapError("pre-candidate abort failure evidence is malformed")
    return result


def finalize_pre_candidate_abort(
    run_dir: Path,
    prepared: dict[str, Any],
    command: Command,
    adb: str,
    *,
    payload_free_reboot_dispatched: bool,
    observed_android: tuple[dict[str, Any], dict[str, str], dict[str, str]] | None = None,
) -> dict[str, Any]:
    android = observed_android or wait_android(command, adb, ANDROID_TIMEOUT)
    if android is None:
        return {
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH",
            "candidate_replay_permitted": False,
            "partition_transfer_count": 0,
        }
    _selected, _values, identity = android
    validate_pre_candidate_abort_return(prepared, identity)
    receipt = {
        "schema": "s20plus_g986n_f1_pre_candidate_abort_final_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "PASS_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTHY",
        "pre_candidate": True,
        "candidate_intent_absent": True,
        "rollback_intent_absent": True,
        "partition_transfer_count": 0,
        "payload_free_reboot_dispatched": payload_free_reboot_dispatched,
        "android_identity": identity,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "at": utc_now(),
    }
    durable_create(run_dir / "pre-candidate-abort-final.json", receipt)
    release_guard(run_dir)
    return receipt


def abort_pre_candidate(
    run_dir: Path,
    command: Command = bounded_command,
) -> dict[str, Any]:
    """Abort a zero-partition-effect F1 run and return it to normal Android."""
    if not F1_ACTIVE or not PRE_CANDIDATE_ABORT_ACTIVE:
        raise BootstrapError("S20+ pre-candidate abort is not active")
    prepared = read_prepared_for_pre_candidate_abort(run_dir)
    validate_pre_candidate_abort_state(run_dir, prepared)
    adb = base.tool_receipt(ADB)["path"]
    if os.path.lexists(run_dir / "pre-candidate-abort-final.json"):
        raise BootstrapError("pre-candidate abort is already closed")
    if os.path.lexists(run_dir / "pre-candidate-abort-intent.json"):
        dispatch = validate_pre_candidate_abort_dispatch(run_dir, prepared)
        return finalize_pre_candidate_abort(run_dir, prepared, command, adb, payload_free_reboot_dispatched=dispatch["effect_command_count"] == 1)
    try:
        observed_android = android_health_once(command, adb)
        _selected, _values, identity = observed_android
    except Exception:
        observed_android = None
        identity = None
    if identity is not None:
        validate_pre_candidate_abort_return(prepared, identity)
        return finalize_pre_candidate_abort(run_dir, prepared, command, adb, payload_free_reboot_dispatched=False, observed_android=observed_android)
    if adb_rows(command, adb):
        raise BootstrapError("ADB rows remain while exact Android health is unavailable")
    require_file(ODIN, ODIN_SIZE, ODIN_SHA256, "Odin4")
    endpoint = identify_download(command)
    expected_endpoint = expected_pre_candidate_abort_endpoint(run_dir, prepared)
    if endpoint != expected_endpoint:
        raise BootstrapError("Download endpoint lost exact transition continuity")
    intent = {
        "schema": "s20plus_g986n_f1_pre_candidate_abort_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "action": "payload-free-normal-return",
        "endpoint": endpoint,
        "command_shape": ["odin4", "--reboot", "-d", "USBFS"],
        "attempt": 1,
        "partition_payload": False,
        "no_replay": True,
        "at": utc_now(),
    }
    durable_create(run_dir / "pre-candidate-abort-intent.json", intent)
    read_guard(run_dir)
    expected_identity = tuple(endpoint["endpoint_identity"])
    effect_command_count = 0
    try:
        if endpoint_stat(endpoint["device"]) != expected_identity:
            raise BootstrapError("Download endpoint changed before payload-free return")
        effect_command_count = 1
        rc, stdout, stderr = command([str(ODIN), "--reboot", "-d", endpoint["device"]], 120, 64 * 1024)
        durable_bytes(run_dir / "pre-candidate-abort.stdout", stdout)
        durable_bytes(run_dir / "pre-candidate-abort.stderr", stderr)
        try:
            post_identity = endpoint_stat(endpoint["device"])
            post_state = "same" if post_identity == expected_identity else "changed"
        except FileNotFoundError:
            post_state = "absent"
        dispatched = rc == 0 and post_state == "absent"
        result = {
            "schema": "s20plus_g986n_f1_pre_candidate_abort_result_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "action": intent["action"],
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTH" if dispatched else "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_UNKNOWN",
            "returncode": rc,
            "post_state": post_state,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "effect_command_count": effect_command_count,
            "partition_transfer_count": 0,
            "no_replay": True,
            "replay_permitted": False,
            "at": utc_now(),
        }
    except Exception as exc:
        result = {
            "schema": "s20plus_g986n_f1_pre_candidate_abort_result_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "action": intent["action"],
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PRE_CANDIDATE_ABORT_UNKNOWN",
            "failure_class": type(exc).__name__,
            "effect_command_count": effect_command_count,
            "partition_transfer_count": 0,
            "no_replay": True,
            "replay_permitted": False,
            "at": utc_now(),
        }
        durable_create(run_dir / "pre-candidate-abort-result.json", result)
        raise
    durable_create(run_dir / "pre-candidate-abort-result.json", result)
    if not dispatched:
        return result
    return finalize_pre_candidate_abort(run_dir, prepared, command, adb, payload_free_reboot_dispatched=True)


def close_pre_candidate_transition(
    run_dir: Path,
    command: Command = bounded_command,
) -> Path:
    """Close the named prepare run after its initial transition only."""
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    run_dir = validate_run_dir(run_dir)
    guard = read_guard(run_dir)
    prepared_path = run_dir / "prepared.json"
    metadata = prepared_path.lstat()
    if prepared_path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("prepared binding is not an exact regular file")
    prepared = json.loads(prepared_path.read_text())
    if (
        set(prepared) != {"schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"}
        or prepared.get("schema") != "s20plus_g986n_magisk_bootstrap_prepared_v1"
        or prepared.get("version") != VERSION
        or prepared.get("binding_sha256") != PRE_CANDIDATE_CLOSE_BINDING_SHA256
        or prepared.get("approval_token") != APPROVAL_PREFIX + PRE_CANDIDATE_CLOSE_BINDING_SHA256
        or prepared.get("binding", {}).get("run_dir") != str(run_dir)
        or prepared.get("binding_sha256") != canonical_sha(prepared.get("binding"))
    ):
        raise BootstrapError("prepared run is not the exact named pre-candidate close target")
    binding = prepared["binding"]
    closure_runner = binding.get("closure", {}).get("runner", {})
    if (
        closure_runner.get("sha256") != PRE_CANDIDATE_CLOSE_RUNNER_SHA256
        or closure_runner.get("normalized_sha256") != PRE_CANDIDATE_CLOSE_NORMALIZED_SHA256
        or binding.get("target") != {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            "topology_sha256": EXPECTED_TOPOLOGY_SHA256,
        }
        or not isinstance(binding.get("candidate_attempts"), int)
        or isinstance(binding.get("candidate_attempts"), bool)
        or binding.get("candidate_attempts") != 1
        or not isinstance(binding.get("rollback_attempts"), int)
        or isinstance(binding.get("rollback_attempts"), bool)
        or binding.get("rollback_attempts") != 1
        or binding.get("rollback_mandatory") is not True
        or binding.get("candidate_replay") is not False
    ):
        raise BootstrapError("pre-candidate close binding is not exact")
    if guard.get("run_dir") != str(run_dir) or guard.get("unresolved") is not True:
        raise BootstrapError("shared guard is not bound to this run")
    if os.path.lexists(run_dir / "pre-candidate-transition-closed.json"):
        raise BootstrapError("pre-candidate transition close already consumed")
    allowed_files = {
        run_dir / "prepared.json",
        run_dir / "initial-download-baseline.json",
        run_dir / "initial-download-intent.json",
        run_dir / "initial-download-observation.json",
        run_dir / "initial-download-result.json",
        run_dir / "events" / "00-prepared.json",
    }
    actual: dict[Path, str] = {}
    pending = [run_dir]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                    actual[path] = "regular"
                elif stat.S_ISDIR(metadata.st_mode) and metadata.st_nlink >= 2:
                    actual[path] = "directory"
                    pending.append(path)
                else:
                    actual[path] = "unexpected"
    expected = {path: "regular" for path in allowed_files if path != run_dir / "events"}
    expected[run_dir / "events"] = "directory"
    if actual != expected:
        raise BootstrapError("pre-candidate run has possible effect or unexpected evidence")
    validate_live_transition_binding(run_dir, binding["transition"], binding["endpoint"])
    adb = base.tool_receipt(ADB)["path"]
    selected, _values, identity = android_health_once(command, adb)
    prepared_identity = binding["transition"]["android_identity"]
    if (
        identity.get("serial_sha256") != prepared_identity.get("serial_sha256")
        or identity.get("topology_sha256") != prepared_identity.get("topology_sha256")
        or not re.fullmatch(r"[0-9a-f]{64}", str(identity.get("boot_id_sha256")))
        or identity.get("boot_id_sha256") == prepared_identity.get("boot_id_sha256")
    ):
        raise BootstrapError("current Android target or boot transition does not match the prepared run")
    root_absence = exact_root_absence_once(command, adb, selected, identity)
    receipt = {
        "schema": "s20plus_g986n_f1_pre_candidate_transition_close_v1",
        "version": VERSION,
        "binding_sha256": PRE_CANDIDATE_CLOSE_BINDING_SHA256,
        "run_dir": str(run_dir),
        "candidate_intent_absent": True,
        "rollback_intent_absent": True,
        "transfer_evidence_absent": True,
        "initial_transition_completed": True,
        "prepared_android_identity": prepared_identity,
        "current_android_identity": identity,
        "boot_id_changed_after_transition": True,
        "root_absence": root_absence,
        "device_effects_after_initial_transition": 0,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "reason": "initial-download-transition-complete-candidate-never-started",
        "at": utc_now(),
    }
    path = run_dir / "pre-candidate-transition-closed.json"
    durable_create(path, receipt)
    release_guard(run_dir)
    return path


def close_endpoint_uncertain_transition(
    run_dir: Path,
    command: Command = bounded_command,
) -> Path:
    """Close the named current run after endpoint uncertainty, pre-transfer."""
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    run_dir = validate_run_dir(run_dir)
    guard = read_guard(run_dir)
    prepared_path = run_dir / "prepared.json"
    metadata = prepared_path.lstat()
    if prepared_path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("prepared binding is not an exact regular file")
    prepared = json.loads(prepared_path.read_text())
    binding = prepared.get("binding")
    closure_runner = binding.get("closure", {}).get("runner", {}) if isinstance(binding, dict) else {}
    if (
        set(prepared) != {"schema", "version", "binding", "binding_sha256", "approval_token", "prepared_at"}
        or prepared.get("schema") != "s20plus_g986n_magisk_bootstrap_prepared_v1"
        or prepared.get("version") != VERSION
        or prepared.get("binding_sha256") != ENDPOINT_UNCERTAIN_CLOSE_BINDING_SHA256
        or prepared.get("approval_token") != APPROVAL_PREFIX + ENDPOINT_UNCERTAIN_CLOSE_BINDING_SHA256
        or prepared.get("binding", {}).get("run_dir") != str(run_dir)
        or prepared.get("binding_sha256") != canonical_sha(binding)
        or closure_runner.get("sha256") != ENDPOINT_UNCERTAIN_CLOSE_RUNNER_SHA256
        or closure_runner.get("normalized_sha256") != ENDPOINT_UNCERTAIN_CLOSE_NORMALIZED_SHA256
        or binding.get("target") != {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            "topology_sha256": EXPECTED_TOPOLOGY_SHA256,
        }
        or not isinstance(binding.get("candidate_attempts"), int)
        or isinstance(binding.get("candidate_attempts"), bool)
        or binding.get("candidate_attempts") != 1
        or not isinstance(binding.get("rollback_attempts"), int)
        or isinstance(binding.get("rollback_attempts"), bool)
        or binding.get("rollback_attempts") != 1
        or binding.get("rollback_mandatory") is not True
        or binding.get("candidate_replay") is not False
    ):
        raise BootstrapError("prepared run is not the exact endpoint-uncertain close target")
    if guard.get("run_dir") != str(run_dir) or guard.get("unresolved") is not True:
        raise BootstrapError("shared guard is not bound to this run")
    if os.path.lexists(run_dir / "endpoint-uncertain-transition-closed.json"):
        raise BootstrapError("endpoint-uncertain close already consumed")
    allowed_files = {
        run_dir / "prepared.json",
        run_dir / "initial-download-baseline.json",
        run_dir / "initial-download-intent.json",
        run_dir / "initial-download-observation.json",
        run_dir / "initial-download-result.json",
        run_dir / "result.json",
        run_dir / "events" / "00-prepared.json",
    }
    actual: dict[Path, str] = {}
    pending = [run_dir]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                    actual[path] = "regular"
                elif stat.S_ISDIR(metadata.st_mode) and metadata.st_nlink >= 2:
                    actual[path] = "directory"
                    pending.append(path)
                else:
                    actual[path] = "unexpected"
    expected = {path: "regular" for path in allowed_files if path != run_dir / "events"}
    expected[run_dir / "events"] = "directory"
    if actual != expected:
        raise BootstrapError("endpoint-uncertain run has possible effect or unexpected evidence")
    result_meta = (run_dir / "result.json").lstat()
    result = json.loads((run_dir / "result.json").read_text())
    if (
        (run_dir / "result.json").is_symlink()
        or not stat.S_ISREG(result_meta.st_mode)
        or result_meta.st_nlink != 1
        or set(result) != {"schema", "version", "verdict", "failure_class", "candidate_replay_permitted", "rollback_replay_permitted"}
        or result.get("schema") != "s20plus_g986n_magisk_bootstrap_f1_result_v1"
        or result.get("version") != VERSION
        or result.get("verdict") != "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_ENDPOINT_UNCERTAIN"
        or not isinstance(result.get("failure_class"), str)
        or result.get("candidate_replay_permitted") is not False
        or result.get("rollback_replay_permitted") is not False
        or os.path.lexists(run_dir / "candidate-intent.json")
        or os.path.lexists(run_dir / "candidate-result.json")
        or os.path.lexists(run_dir / "rollback-intent.json")
        or os.path.lexists(run_dir / "rollback-result.json")
    ):
        raise BootstrapError("endpoint-uncertain result or effect evidence is malformed")
    validate_live_transition_binding(run_dir, binding["transition"], binding["endpoint"])
    adb = base.tool_receipt(ADB)["path"]
    selected, _values, identity = android_health_once(command, adb)
    prepared_identity = binding["transition"]["android_identity"]
    if (
        identity.get("serial_sha256") != prepared_identity.get("serial_sha256")
        or identity.get("topology_sha256") != prepared_identity.get("topology_sha256")
        or not re.fullmatch(r"[0-9a-f]{64}", str(identity.get("boot_id_sha256")))
        or identity.get("boot_id_sha256") == prepared_identity.get("boot_id_sha256")
    ):
        raise BootstrapError("current Android target or boot transition does not match the endpoint-uncertain run")
    root_absence = exact_root_absence_once(command, adb, selected, identity)
    receipt = {
        "schema": "s20plus_g986n_f1_endpoint_uncertain_close_v1",
        "version": VERSION,
        "binding_sha256": ENDPOINT_UNCERTAIN_CLOSE_BINDING_SHA256,
        "run_dir": str(run_dir),
        "candidate_intent_absent": True,
        "rollback_intent_absent": True,
        "transfer_evidence_absent": True,
        "endpoint_observation_uncertain": True,
        "prepared_android_identity": prepared_identity,
        "current_android_identity": identity,
        "boot_id_changed_after_transition": True,
        "root_absence": root_absence,
        "device_effects_after_initial_transition": 0,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "reason": "download-endpoint-unavailable-before-candidate-intent",
        "at": utc_now(),
    }
    path = run_dir / "endpoint-uncertain-transition-closed.json"
    durable_create(path, receipt)
    release_guard(run_dir)
    return path


def endpoint_identity_ctime_only_change(receipt: dict[str, object]) -> bool:
    pre = receipt.get("endpoint_pre_identity")
    post = receipt.get("endpoint_post_identity")
    return (
        receipt.get("endpoint_post_state") == "changed"
        and isinstance(pre, list)
        and isinstance(post, list)
        and len(pre) == 4
        and len(post) == 4
        and all(isinstance(value, int) and not isinstance(value, bool) for value in pre + post)
        and pre[:3] == post[:3]
        and pre[3] != post[3]
    )


def persisted_transfer_classification(receipt: dict[str, object], stdout: bytes, stderr: bytes) -> str:
    classification = f1_core.classify_odin_output(int(receipt["returncode"]), stdout, stderr)
    if receipt.get("endpoint_post_state") == "changed" and not endpoint_identity_ctime_only_change(receipt):
        return "odin_device_session_failure_or_unknown"
    return classification


def persist_transfer(run_dir: Path, kind: str, binding_sha256: str, endpoint: dict[str, Any], outcome: tuple[dict[str, object], bytes, bytes]) -> str:
    receipt, stdout, stderr = outcome
    durable_bytes(run_dir / f"{kind}.stdout", stdout)
    durable_bytes(run_dir / f"{kind}.stderr", stderr)
    classification = persisted_transfer_classification(receipt, stdout, stderr)
    durable_create(run_dir / f"{kind}-result.json", {"schema": "s20plus_g986n_f1_transfer_v1", "version": VERSION, "kind": kind, "binding_sha256": binding_sha256, "endpoint": {"device": endpoint["device"], "identity": endpoint["endpoint_identity"]}, "classification": classification, "receipt": receipt, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest()})
    return classification


def read_transfer_intent(run_dir: Path, kind: str, binding_sha256: str) -> dict[str, Any]:
    path = run_dir / f"{kind}-intent.json"
    value = read_exact_json(path, f"{kind} intent")
    digest = CANDIDATE_SHA256 if kind == "candidate" else ROLLBACK_SHA256
    if (
        set(value) != {"schema", "version", "kind", "binding_sha256", "ap_sha256", "endpoint", "attempt", "no_replay", "at"}
        or value.get("schema") != "s20plus_g986n_f1_transfer_intent_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("ap_sha256") != digest
        or not isinstance(value.get("attempt"), int)
        or isinstance(value.get("attempt"), bool)
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or set(value.get("endpoint", {})) != {"device", "identity"}
        or not isinstance(value["endpoint"].get("device"), str)
        or USBFS_RE.fullmatch(value["endpoint"]["device"]) is None
        or not isinstance(value["endpoint"]["identity"], list)
        or len(value["endpoint"]["identity"]) != 4
        or any(not isinstance(item, int) or isinstance(item, bool) for item in value["endpoint"]["identity"])
        or not isinstance(value.get("at"), str)
        or not value.get("at")
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
    if not isinstance(expected_size, int) or isinstance(expected_size, bool) or not 0 <= expected_size <= MAX_OUTPUT or metadata.st_size != expected_size:
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
        set(value) != {"schema", "version", "kind", "binding_sha256", "endpoint", "classification", "receipt", "stdout_sha256", "stderr_sha256"}
        or set(receipt) != {
            "label", "returncode", "command_shape", "regular_path_inputs",
            "anonymous_proc_fd_inputs", "odin", "ap", "endpoint_path_sha256",
            "endpoint_pre_identity", "endpoint_post_identity", "endpoint_post_state",
            "stdout_bytes", "stderr_bytes",
        }
        or value.get("schema") != "s20plus_g986n_f1_transfer_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("endpoint") != intent.get("endpoint")
        or value.get("classification") != "odin_transfer_completed"
        or f1_core.classify_odin_output(receipt.get("returncode"), stdout, stderr) != "odin_transfer_completed"
        or receipt.get("label") != kind
        or not isinstance(receipt.get("returncode"), int)
        or isinstance(receipt.get("returncode"), bool)
        or receipt.get("returncode") != 0
        or receipt.get("command_shape") != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or receipt.get("regular_path_inputs") is not True
        or receipt.get("anonymous_proc_fd_inputs") is not False
        or receipt.get("ap") != {
            "path": str(CANDIDATE if kind == "candidate" else ROLLBACK),
            "size": CANDIDATE_SIZE if kind == "candidate" else ROLLBACK_SIZE,
            "sha256": digest,
        }
        or receipt.get("odin") != {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256}
        or receipt.get("endpoint_path_sha256") != hashlib.sha256(intent["endpoint"]["device"].encode()).hexdigest()
        or receipt.get("endpoint_pre_identity") != intent["endpoint"]["identity"]
        or (
            receipt.get("endpoint_post_state") == "same"
            and receipt.get("endpoint_post_identity") != intent["endpoint"]["identity"]
        )
        or (
            receipt.get("endpoint_post_state") == "absent"
            and receipt.get("endpoint_post_identity") is not None
        )
        or (
            receipt.get("endpoint_post_state") not in ("same", "absent")
            and not endpoint_identity_ctime_only_change(receipt)
        )
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
    expected = {"model": EXPECTED_MODEL, "device": EXPECTED_DEVICE, "product_name": EXPECTED_PRODUCT, "incremental": EXPECTED_INCREMENTAL, "boot_completed": "1", "bootanim": "stopped", "selinux": "Enforcing", "verified_boot_state": "orange", "flash_locked": "0", "vbmeta_device_state": "unlocked"}
    if not all(values.get(key) == value for key, value in expected.items()):
        raise BootstrapError("Android health does not match exact target")
    identity = {"serial_sha256": base.sha256_text(serial), "topology_sha256": base.sha256_text(devpath), "boot_id_sha256": base.sha256_text(values["boot_id"])}
    return selected, values, identity


def exact_root_absence_once(
    command: Command,
    adb: str,
    selected: dict[str, Any],
    expected_identity: dict[str, str],
) -> dict[str, Any]:
    rc, stdout, stderr = command(
        [adb, "-s", selected["serial"], "shell", "su", "-c", "id"],
        20,
        64 * 1024,
    )
    if len(stdout) + len(stderr) > 64 * 1024:
        raise BootstrapError("initial root-absence output is oversized")
    try:
        stdout_text = stdout.decode("utf-8", "strict").strip()
        stderr_text = stderr.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise BootstrapError("initial root-absence output is malformed") from exc
    combined = stdout_text + ("\n" if stdout_text and stderr_text else "") + stderr_text
    absence_re = re.compile(
        r"(?:/system/bin/sh: )?su: (?:not found|inaccessible(?: or not found)?|permission denied|no such file)",
        re.IGNORECASE,
    )
    if "uid=0(root)" in combined or rc != 127 or stdout_text != "" or absence_re.fullmatch(stderr_text) is None:
        raise BootstrapError("initial stock root absence is not exact")
    _confirmed_selected, _confirmed_values, confirmed_identity = android_health_once(command, adb)
    if confirmed_identity != expected_identity:
        raise BootstrapError("Android identity changed during initial root-absence proof")
    return {
        "returncode": rc,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "identity_confirmed": True,
    }


def transition_android_to_download(
    run_dir: Path,
    command: Command,
    adb: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected, _values, identity = android_health_once(command, adb)
    if identity["topology_sha256"] != EXPECTED_TOPOLOGY_SHA256:
        raise BootstrapError("initial Android topology is not exact")
    serial = selected["serial"]
    root_absence = exact_root_absence_once(command, adb, selected, identity)
    baseline = download_baseline(command)
    baseline_path = write_download_baseline(run_dir, "initial-download-baseline", baseline)
    baseline_sha256 = canonical_sha(baseline)
    intent = {
        "schema": "s20plus_g986n_f1_initial_download_intent_v1",
        "version": VERSION,
        "action": "enter-download-for-candidate-session",
        "target": {
            "model": EXPECTED_MODEL,
            "device": EXPECTED_DEVICE,
            "product": EXPECTED_PRODUCT,
            "incremental": EXPECTED_INCREMENTAL,
            **identity,
        },
        "stock_root_absence": root_absence,
        "baseline_sha256": baseline_sha256,
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    intent_path = run_dir / "initial-download-intent.json"
    durable_create(intent_path, intent)
    try:
        rc, stdout, stderr = command(
            [adb, "-s", serial, "reboot", "download"],
            20,
            64 * 1024,
        )
        outcome = "dispatched" if rc == 0 and not stderr else "uncertain"
        result = {
            "schema": "s20plus_g986n_f1_initial_download_result_v1",
            "version": VERSION,
            "action": intent["action"],
            "attempt": 1,
            "returncode": rc,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "outcome": outcome,
            "replay_permitted": False,
            "at": utc_now(),
        }
    except Exception as exc:
        result = {
            "schema": "s20plus_g986n_f1_initial_download_result_v1",
            "version": VERSION,
            "action": intent["action"],
            "attempt": 1,
            "outcome": "uncertain",
            "failure_class": type(exc).__name__,
            "replay_permitted": False,
            "at": utc_now(),
        }
    result_path = run_dir / "initial-download-result.json"
    durable_create(result_path, result)
    if result["outcome"] != "dispatched":
        raise BootstrapError("initial Download dispatch is uncertain; replay forbidden")
    observed_result = wait_download_after_baseline(command, baseline, DOWNLOAD_TIMEOUT)
    if observed_result is None:
        raise BootstrapError("initial Download endpoint was not observed; replay forbidden")
    endpoint, arrival = observed_result
    observed = {
        "schema": "s20plus_g986n_f1_initial_download_observation_v1",
        "version": VERSION,
        "action": intent["action"],
        "resolution": "download-observed",
        "endpoint": endpoint,
        "baseline_sha256": baseline_sha256,
        "arrival_listing_sha256": arrival["arrival_listing_sha256"],
        "at": utc_now(),
    }
    observed_path = run_dir / "initial-download-observation.json"
    durable_create(observed_path, observed)
    transition = {
        "schema": "s20plus_g986n_f1_live_transition_binding_v1",
        "version": VERSION,
        "android_identity": identity,
        "stock_root_absence": root_absence,
        "baseline_sha256": baseline_sha256,
        "arrival_listing_sha256": arrival["arrival_listing_sha256"],
        "intent_sha256": sha256_file(intent_path),
        "result_sha256": sha256_file(result_path),
        "observation_sha256": sha256_file(observed_path),
        "endpoint_identity": endpoint["endpoint_identity"],
        "endpoint_topology_sha256": endpoint["topology_sha256"],
        "replay_permitted": False,
    }
    return transition, endpoint


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
    try:
        baseline = download_baseline(command)
        write_download_baseline(run_dir, "rollback-mode-baseline", baseline)
    except Exception as exc:
        durable_create(run_dir / "rollback-mode-preflight.json", {"schema": "s20plus_g986n_f1_rollback_mode_preflight_v1", "version": VERSION, "dispatch_attempted": False, "baseline_failure_class": type(exc).__name__})
        return False
    baseline_sha256 = canonical_sha(baseline)
    serial = selected["serial"]
    durable_create(run_dir / "rollback-mode-intent.json", {"schema": "s20plus_g986n_f1_rollback_mode_intent_v1", "version": VERSION, "binding_sha256": binding_sha256, "action": "enter-download-for-stock-rollback", "ordinal": 1, "serial_sha256": expected_identity["serial_sha256"], "topology_sha256": expected_identity["topology_sha256"], "boot_id_sha256": expected_identity["boot_id_sha256"], "baseline_sha256": baseline_sha256, "no_replay": True, "at": utc_now()})
    try:
        rc, stdout, stderr = command([adb, "-s", serial, "reboot", "download"], 20, 64 * 1024)
        durable_create(run_dir / "rollback-mode-result.json", {"schema": "s20plus_g986n_f1_rollback_mode_result_v1", "version": VERSION, "binding_sha256": binding_sha256, "returncode": rc, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest(), "outcome": "dispatched" if rc == 0 and not stderr else "uncertain", "replay_permitted": False})
        return rc == 0 and not stderr
    except Exception as exc:
        durable_create(run_dir / "rollback-mode-result.json", {"schema": "s20plus_g986n_f1_rollback_mode_result_v1", "version": VERSION, "binding_sha256": binding_sha256, "outcome": "uncertain", "failure_class": type(exc).__name__, "replay_permitted": False})
        return False


def validate_rollback_mode_transition(run_dir: Path, binding_sha256: str, expected_identity: dict[str, str]) -> dict[str, Any]:
    intent_path = run_dir / "rollback-mode-intent.json"
    result_path = run_dir / "rollback-mode-result.json"
    baseline_path = run_dir / "rollback-mode-baseline.json"
    values: dict[str, Any] = {}
    for label, path in (("rollback mode intent", intent_path), ("rollback mode result", result_path), ("rollback mode baseline", baseline_path)):
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise BootstrapError(f"{label} is not an exact regular file")
        values[label] = json.loads(path.read_text())
    intent = values["rollback mode intent"]
    result = values["rollback mode result"]
    baseline = validate_download_baseline(values["rollback mode baseline"])
    baseline_sha256 = canonical_sha(baseline)
    if (
        set(intent) != {"schema", "version", "binding_sha256", "action", "ordinal", "serial_sha256", "topology_sha256", "boot_id_sha256", "baseline_sha256", "no_replay", "at"}
        or intent.get("schema") != "s20plus_g986n_f1_rollback_mode_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("binding_sha256") != binding_sha256
        or intent.get("action") != "enter-download-for-stock-rollback"
        or not isinstance(intent.get("ordinal"), int)
        or isinstance(intent.get("ordinal"), bool)
        or intent.get("ordinal") != 1
        or intent.get("serial_sha256") != expected_identity["serial_sha256"]
        or intent.get("topology_sha256") != expected_identity["topology_sha256"]
        or intent.get("boot_id_sha256") != expected_identity["boot_id_sha256"]
        or intent.get("baseline_sha256") != baseline_sha256
        or intent.get("no_replay") is not True
        or set(result) != {"schema", "version", "binding_sha256", "returncode", "stdout_sha256", "stderr_sha256", "outcome", "replay_permitted"}
        or result.get("schema") != "s20plus_g986n_f1_rollback_mode_result_v1"
        or result.get("version") != VERSION
        or result.get("binding_sha256") != binding_sha256
        or not isinstance(result.get("returncode"), int)
        or isinstance(result.get("returncode"), bool)
        or result.get("returncode") != 0
        or result.get("stdout_sha256") != hashlib.sha256(b"").hexdigest()
        or result.get("stderr_sha256") != hashlib.sha256(b"").hexdigest()
        or result.get("outcome") != "dispatched"
        or result.get("replay_permitted") is not False
    ):
        raise BootstrapError("rollback mode transition evidence is malformed or mismatched")
    return baseline


def read_rollback_mode_observation(
    run_dir: Path,
    binding_sha256: str,
    baseline: dict[str, Any],
) -> dict[str, Any]:
    value = read_exact_json(run_dir / "rollback-mode-observation.json", "rollback mode observation")
    endpoint = value.get("endpoint") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "baseline_sha256",
            "baseline_listing_sha256", "arrival_listing_sha256", "arrival_endpoint",
            "endpoint", "replay_permitted", "at",
        }
        or value.get("schema") != "s20plus_g986n_f1_rollback_mode_observation_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("baseline_sha256") != canonical_sha(baseline)
        or value.get("baseline_listing_sha256") != baseline["listing_sha256"]
        or re.fullmatch(r"[0-9a-f]{64}", str(value.get("arrival_listing_sha256"))) is None
        or not isinstance(endpoint, dict)
        or value.get("arrival_endpoint") != endpoint.get("device")
        or value.get("replay_permitted") is not False
    ):
        raise BootstrapError("rollback mode observation is malformed or mismatched")
    return validate_download_endpoint_record(endpoint, "rollback Download endpoint")


def wait_download(command: Command, timeout: float) -> dict[str, Any] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return identify_download(command)
        except Exception:
            time.sleep(2)
    return None


def validate_candidate_for_physical_handoff(run_dir: Path, binding_sha256: str) -> dict[str, Any]:
    intent = read_transfer_intent(run_dir, "candidate", binding_sha256)
    path = run_dir / "candidate-result.json"
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise BootstrapError("candidate result is not an exact regular file")
    value = json.loads(path.read_text())
    if (
        set(value) != {"schema", "version", "kind", "binding_sha256", "endpoint", "classification", "receipt", "stdout_sha256", "stderr_sha256"}
        or value.get("schema") != "s20plus_g986n_f1_transfer_v1"
        or value.get("version") != VERSION
        or value.get("kind") != "candidate"
        or value.get("binding_sha256") != binding_sha256
        or value.get("endpoint") != intent.get("endpoint")
        or value.get("classification") not in {"odin_transfer_completed", "odin_device_session_failure_or_unknown", "odin_local_parse_failure"}
    ):
        raise BootstrapError("candidate transfer evidence is malformed or mismatched")
    receipt = value["receipt"]
    stdout = read_raw_evidence(run_dir / "candidate.stdout", receipt.get("stdout_bytes"), value.get("stdout_sha256"))
    stderr = read_raw_evidence(run_dir / "candidate.stderr", receipt.get("stderr_bytes"), value.get("stderr_sha256"))
    expected_receipt_keys = {
        "label", "returncode", "command_shape", "regular_path_inputs",
        "anonymous_proc_fd_inputs", "odin", "ap", "endpoint_path_sha256",
        "endpoint_pre_identity", "endpoint_post_identity", "endpoint_post_state",
        "stdout_bytes", "stderr_bytes",
    }
    post_state = receipt.get("endpoint_post_state")
    post_identity = receipt.get("endpoint_post_identity")
    if (
        not isinstance(receipt, dict)
        or set(receipt) != expected_receipt_keys
        or receipt.get("label") != "candidate"
        or not isinstance(receipt.get("returncode"), int)
        or isinstance(receipt.get("returncode"), bool)
        or receipt.get("command_shape") != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or receipt.get("regular_path_inputs") is not True
        or receipt.get("anonymous_proc_fd_inputs") is not False
        or receipt.get("ap") != {"path": str(CANDIDATE), "size": CANDIDATE_SIZE, "sha256": CANDIDATE_SHA256}
        or receipt.get("odin") != {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256}
        or receipt.get("endpoint_path_sha256") != hashlib.sha256(intent["endpoint"]["device"].encode()).hexdigest()
        or receipt.get("endpoint_pre_identity") != intent["endpoint"]["identity"]
        or post_state not in {"same", "absent", "changed"}
        or (post_state == "same" and post_identity != intent["endpoint"]["identity"])
        or (post_state == "absent" and post_identity is not None)
        or (
            post_state == "changed"
            and (
                not isinstance(post_identity, list)
                or len(post_identity) != 4
                or any(not isinstance(item, int) or isinstance(item, bool) for item in post_identity)
                or post_identity == intent["endpoint"]["identity"]
            )
        )
    ):
        raise BootstrapError("candidate transfer receipt is malformed or mismatched")
    current_classification = persisted_transfer_classification(receipt, stdout, stderr)
    compatible_ctime_classification = (
        value["classification"] == "odin_device_session_failure_or_unknown"
        and current_classification == "odin_transfer_completed"
        and endpoint_identity_ctime_only_change(receipt)
    )
    if current_classification != value["classification"] and not compatible_ctime_classification:
        raise BootstrapError("candidate transfer classification mismatch")
    if value["classification"] == "odin_transfer_completed":
        return completed_transfer_result(run_dir, "candidate", binding_sha256)
    return value


def validate_late_candidate_completion(
    run_dir: Path,
    prepared: dict[str, Any],
    candidate_result: dict[str, Any],
    candidate_observation: dict[str, Any],
) -> None:
    """Accept only the reviewed historical ctime-only post-Odin ambiguity."""
    receipt = candidate_result.get("receipt", {})
    intent = read_transfer_intent(run_dir, "candidate", prepared["binding_sha256"])
    stdout = read_raw_evidence(
        run_dir / "candidate.stdout",
        receipt.get("stdout_bytes"),
        candidate_result.get("stdout_sha256"),
    )
    stderr = read_raw_evidence(
        run_dir / "candidate.stderr",
        receipt.get("stderr_bytes"),
        candidate_result.get("stderr_sha256"),
    )
    expected_receipt_keys = {
        "label", "returncode", "command_shape", "regular_path_inputs",
        "anonymous_proc_fd_inputs", "odin", "ap", "endpoint_path_sha256",
        "endpoint_pre_identity", "endpoint_post_identity", "endpoint_post_state",
        "stdout_bytes", "stderr_bytes",
    }
    if (
        candidate_result.get("classification") != "odin_device_session_failure_or_unknown"
        or set(receipt) != expected_receipt_keys
        or f1_core.classify_odin_output(receipt.get("returncode"), stdout, stderr) != "odin_transfer_completed"
        or not endpoint_identity_ctime_only_change(receipt)
        or receipt.get("label") != "candidate"
        or not isinstance(receipt.get("returncode"), int)
        or isinstance(receipt.get("returncode"), bool)
        or receipt.get("returncode") != 0
        or receipt.get("command_shape") != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
        or receipt.get("regular_path_inputs") is not True
        or receipt.get("anonymous_proc_fd_inputs") is not False
        or receipt.get("ap") != {"path": str(CANDIDATE), "size": CANDIDATE_SIZE, "sha256": CANDIDATE_SHA256}
        or receipt.get("odin") != {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256}
        or receipt.get("endpoint_path_sha256") != hashlib.sha256(intent["endpoint"]["device"].encode()).hexdigest()
        or receipt.get("endpoint_pre_identity") != intent["endpoint"]["identity"]
        or candidate_observation != {
            "schema": "s20plus_g986n_f1_candidate_observation_v1",
            "version": VERSION,
            "classification": "odin_device_session_failure_or_unknown",
            "android_returned": False,
            "boot_id_sha256": None,
            "root_verified": False,
            "attempts": 0,
        }
    ):
        raise BootstrapError("candidate late-observation eligibility is not exact")


def observe_late_candidate_android(
    run_dir: Path,
    prepared: dict[str, Any],
    command: Command,
    adb: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    path = run_dir / "candidate-late-observation.json"
    if os.path.lexists(path):
        value = read_exact_json(path, "candidate late observation")
        identity = value.get("android_identity") if isinstance(value, dict) else None
        root = value.get("root_observation") if isinstance(value, dict) else None
    else:
        _selected, _values, identity = android_health_once(command, adb)
        prepared_identity = prepared["binding"]["transition"]["android_identity"]
        if (
            identity.get("serial_sha256") != prepared_identity.get("serial_sha256")
            or identity.get("topology_sha256") != prepared_identity.get("topology_sha256")
            or identity.get("boot_id_sha256") == prepared_identity.get("boot_id_sha256")
        ):
            raise BootstrapError("late candidate Android identity does not match the prepared transition")
        root = root_observation(command, adb, identity)
        value = {
            "schema": "s20plus_g986n_f1_candidate_late_observation_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "candidate_result_sha256": sha256_exact_regular_file(run_dir / "candidate-result.json", "candidate result"),
            "candidate_observation_sha256": sha256_exact_regular_file(run_dir / "candidate-observation.json", "candidate observation"),
            "android_identity": identity,
            "root_observation": root,
            "candidate_replay_permitted": False,
            "at": utc_now(),
        }
        durable_create(path, value)
    if (
        not isinstance(value, dict)
        or set(value) != {
            "schema", "version", "binding_sha256", "candidate_result_sha256",
            "candidate_observation_sha256", "android_identity", "root_observation",
            "candidate_replay_permitted", "at",
        }
        or value.get("schema") != "s20plus_g986n_f1_candidate_late_observation_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("candidate_result_sha256") != sha256_exact_regular_file(run_dir / "candidate-result.json", "candidate result")
        or value.get("candidate_observation_sha256") != sha256_exact_regular_file(run_dir / "candidate-observation.json", "candidate observation")
        or value.get("candidate_replay_permitted") is not False
        or not isinstance(identity, dict)
        or set(identity) != {"serial_sha256", "topology_sha256", "boot_id_sha256"}
        or any(re.fullmatch(r"[0-9a-f]{64}", str(identity.get(key))) is None for key in identity)
        or not isinstance(root, dict)
        or not isinstance(root.get("root_verified"), bool)
        or not isinstance(root.get("attempts"), int)
        or isinstance(root.get("attempts"), bool)
        or set(root) not in (
            {"root_verified", "attempts"},
            {"root_verified", "attempts", "output_sha256"},
            {"root_verified", "attempts", "identity_drift"},
            {"root_verified", "attempts", "observer_uncertain", "failure_class"},
        )
        or root.get("attempts") < 1
        or root.get("attempts") > 30
        or (root.get("root_verified") is True and "output_sha256" not in root)
        or ("output_sha256" in root and root.get("root_verified") is not True)
        or ("output_sha256" in root and re.fullmatch(r"[0-9a-f]{64}", str(root.get("output_sha256"))) is None)
        or ("identity_drift" in root and (root.get("identity_drift") is not True or root.get("root_verified") is not False))
        or ("observer_uncertain" in root and (root.get("observer_uncertain") is not True or root.get("root_verified") is not False))
        or ("failure_class" in root and not isinstance(root.get("failure_class"), str))
    ):
        raise BootstrapError("candidate late observation is malformed or mismatched")
    prepared_identity = prepared["binding"]["transition"]["android_identity"]
    if (
        identity["serial_sha256"] != prepared_identity["serial_sha256"]
        or identity["topology_sha256"] != prepared_identity["topology_sha256"]
        or identity["boot_id_sha256"] == prepared_identity["boot_id_sha256"]
    ):
        raise BootstrapError("candidate late observation lost target continuity")
    return identity, root


def validate_candidate_observation_for_physical_handoff(
    run_dir: Path,
    candidate_result: dict[str, Any] | None,
) -> dict[str, Any]:
    value = read_exact_json(run_dir / "candidate-observation.json", "candidate observation")
    required = {
        "schema",
        "version",
        "classification",
        "android_returned",
        "boot_id_sha256",
        "root_verified",
        "attempts",
    }
    extras = set(value) - required if isinstance(value, dict) else set()
    allowed_extras = (
        set(),
        {"output_sha256"},
        {"identity_drift"},
        {"observer_uncertain", "failure_class"},
    )
    if (
        not isinstance(value, dict)
        or set(value) < required
        or extras not in allowed_extras
        or value.get("schema") != "s20plus_g986n_f1_candidate_observation_v1"
        or value.get("version") != VERSION
        or value.get("classification") not in {
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
            "odin_local_parse_failure",
        }
        or not isinstance(value.get("android_returned"), bool)
        or not isinstance(value.get("root_verified"), bool)
        or not isinstance(value.get("attempts"), int)
        or isinstance(value.get("attempts"), bool)
        or not 0 <= value.get("attempts") <= 90
        or (value.get("boot_id_sha256") is not None and re.fullmatch(r"[0-9a-f]{64}", str(value.get("boot_id_sha256"))) is None)
        or (value.get("android_returned") is True and re.fullmatch(r"[0-9a-f]{64}", str(value.get("boot_id_sha256"))) is None)
        or (value.get("android_returned") is True and value.get("attempts") < 1)
        or (value.get("classification") != "odin_transfer_completed" and value.get("android_returned") is True)
        or (value.get("android_returned") is False and (value.get("boot_id_sha256") is not None or value.get("root_verified") or value.get("attempts") != 0))
        or (value.get("root_verified") and value.get("android_returned") is not True)
        or (value.get("root_verified") is True and "output_sha256" not in value)
        or ("output_sha256" in value and value.get("root_verified") is not True)
        or ("output_sha256" in value and re.fullmatch(r"[0-9a-f]{64}", str(value.get("output_sha256"))) is None)
        or ("identity_drift" in value and (value.get("identity_drift") is not True or value.get("root_verified") is not False))
        or ("observer_uncertain" in value and (value.get("observer_uncertain") is not True or value.get("root_verified") is not False))
        or ("failure_class" in value and not isinstance(value.get("failure_class"), str))
    ):
        raise BootstrapError("candidate observation is malformed or mismatched")
    if candidate_result is not None and value.get("classification") != candidate_result.get("classification"):
        raise BootstrapError("candidate observation classification mismatch")
    return value


def validate_rollback_mode_state_for_physical_handoff(
    run_dir: Path,
    binding_sha256: str,
    candidate_observation: dict[str, Any],
) -> None:
    intent_path = run_dir / "rollback-mode-intent.json"
    result_path = run_dir / "rollback-mode-result.json"
    intent_exists = os.path.lexists(intent_path)
    result_exists = os.path.lexists(result_path)
    if not intent_exists and not result_exists:
        if candidate_observation["android_returned"]:
            # A returned candidate Android with no rollback journal is only
            # valid when the rollback preflight failed before dispatch.
            preflight = run_dir / "rollback-mode-preflight.json"
            preflight_value = read_exact_json(preflight, "rollback mode preflight")
            if (
                set(preflight_value) != {"schema", "version", "dispatch_attempted", "identity_drift"}
                and set(preflight_value) != {"schema", "version", "dispatch_attempted", "failure_class"}
                and set(preflight_value) != {"schema", "version", "dispatch_attempted", "baseline_failure_class"}
            ):
                raise BootstrapError("rollback mode preflight is malformed")
            if preflight_value.get("schema") != "s20plus_g986n_f1_rollback_mode_preflight_v1" or preflight_value.get("version") != VERSION or preflight_value.get("dispatch_attempted") is not False:
                raise BootstrapError("rollback mode preflight is mismatched")
        return
    if not intent_exists or not result_exists:
        raise BootstrapError("rollback mode journal is incomplete")
    intent = read_exact_json(intent_path, "rollback mode intent")
    result = read_exact_json(result_path, "rollback mode result")
    baseline_path = run_dir / "rollback-mode-baseline.json"
    baseline = validate_download_baseline(read_exact_json(baseline_path, "rollback mode baseline"))
    expected_intent = {
        "schema", "version", "binding_sha256", "action", "ordinal", "serial_sha256",
        "topology_sha256", "boot_id_sha256", "baseline_sha256", "no_replay", "at",
    }
    if (
        set(intent) != expected_intent
        or intent.get("schema") != "s20plus_g986n_f1_rollback_mode_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("binding_sha256") != binding_sha256
        or intent.get("action") != "enter-download-for-stock-rollback"
        or not isinstance(intent.get("ordinal"), int)
        or isinstance(intent.get("ordinal"), bool)
        or intent.get("ordinal") != 1
        or re.fullmatch(r"[0-9a-f]{64}", str(intent.get("serial_sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(intent.get("topology_sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(intent.get("boot_id_sha256"))) is None
        or intent.get("baseline_sha256") != canonical_sha(baseline)
        or intent.get("no_replay") is not True
    ):
        raise BootstrapError("rollback mode intent is malformed or mismatched")
    if result.get("schema") != "s20plus_g986n_f1_rollback_mode_result_v1" or result.get("version") != VERSION or result.get("binding_sha256") != binding_sha256 or result.get("replay_permitted") is not False:
        raise BootstrapError("rollback mode result is malformed or mismatched")
    if result.get("outcome") == "dispatched":
        raise BootstrapError("rollback mode already dispatched; physical handoff is closed")
    if result.get("outcome") != "uncertain":
        raise BootstrapError("rollback mode outcome is not an attended handoff state")
    if set(result) == {"schema", "version", "binding_sha256", "outcome", "failure_class", "replay_permitted"}:
        if not isinstance(result.get("failure_class"), str):
            raise BootstrapError("rollback mode failure is malformed")
    elif set(result) == {"schema", "version", "binding_sha256", "returncode", "stdout_sha256", "stderr_sha256", "outcome", "replay_permitted"}:
        if not isinstance(result.get("returncode"), int) or isinstance(result.get("returncode"), bool) or re.fullmatch(r"[0-9a-f]{64}", str(result.get("stdout_sha256"))) is None or re.fullmatch(r"[0-9a-f]{64}", str(result.get("stderr_sha256"))) is None:
            raise BootstrapError("rollback mode dispatch result is malformed")
    else:
        raise BootstrapError("rollback mode result fields are not exact")


def confirm_rollback_mode(
    run_dir: Path,
    confirmation: str,
    command: Command = bounded_command,
) -> dict[str, Any]:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    prepared = read_prepared(run_dir, allow_pre_candidate_compatible=True)
    binding_sha256 = prepared["binding_sha256"]
    if (run_dir / "rollback-intent.json").exists() or (run_dir / "rollback-result.json").exists():
        raise BootstrapError("rollback attempt already exists; replay forbidden")
    candidate_result = validate_candidate_for_physical_handoff(run_dir, binding_sha256)
    candidate_observation = validate_candidate_observation_for_physical_handoff(run_dir, candidate_result)
    ensure_recovery_continuation(run_dir, prepared)
    validate_rollback_mode_state_for_physical_handoff(run_dir, binding_sha256, candidate_observation)
    handoff_intent_path = run_dir / "rollback-handoff-intent.json"
    if not os.path.lexists(handoff_intent_path):
        if confirmation != PHYSICAL_ROLLBACK_ARM:
            raise BootstrapError("physical rollback arm confirmation mismatch")
        baseline = download_baseline(command)
        baseline_path = write_download_baseline(run_dir, "rollback-handoff-baseline", baseline)
        durable_create(handoff_intent_path, {
            "schema": "s20plus_g986n_f1_rollback_handoff_intent_v1",
            "version": VERSION,
            "binding_sha256": binding_sha256,
            "action": "physical-download-confirmation-required",
            "baseline_sha256": canonical_sha(baseline),
            "baseline_path_sha256": sha256_file(baseline_path),
            "no_replay": True,
            "at": utc_now(),
        })
        return {
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_CONFIRMATION_REQUIRED",
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
    if confirmation != PHYSICAL_ROLLBACK_CONFIRM:
        raise BootstrapError("physical rollback confirmation mismatch")
    handoff = read_exact_json(handoff_intent_path, "physical rollback handoff intent")
    baseline_path = run_dir / "rollback-handoff-baseline.json"
    baseline = validate_download_baseline(read_exact_json(baseline_path, "physical rollback handoff baseline"))
    if (
        set(handoff) != {"schema", "version", "binding_sha256", "action", "baseline_sha256", "baseline_path_sha256", "no_replay", "at"}
        or handoff.get("schema") != "s20plus_g986n_f1_rollback_handoff_intent_v1"
        or handoff.get("version") != VERSION
        or handoff.get("binding_sha256") != binding_sha256
        or handoff.get("action") != "physical-download-confirmation-required"
        or handoff.get("baseline_sha256") != canonical_sha(baseline)
        or handoff.get("baseline_path_sha256") != sha256_file(baseline_path)
        or handoff.get("no_replay") is not True
    ):
        raise BootstrapError("physical rollback handoff is malformed or mismatched")
    endpoint = identify_download(command)
    confirmation_path = run_dir / "rollback-handoff-confirmation.json"
    durable_create(confirmation_path, {
        "schema": "s20plus_g986n_f1_rollback_handoff_confirmation_v1",
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "operator_confirmed": True,
        "physical_key_path": True,
        "baseline_sha256": canonical_sha(baseline),
        "endpoint": endpoint,
        "no_replay": True,
        "at": utc_now(),
    })
    rollback_class = transfer_once(run_dir, "rollback", endpoint, 4, binding_sha256)
    if rollback_class != "odin_transfer_completed":
        result = {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_UNCERTAIN", "rollback_transfer": rollback_class, "candidate_replay_permitted": False, "rollback_replay_permitted": False}
        durable_create(run_dir / "recovery-result.json", result)
        return result
    completed_transfer_result(run_dir, "rollback", binding_sha256)
    adb = base.tool_receipt(ADB)["path"]
    prior_boot_id_sha256 = candidate_observation.get("boot_id_sha256")
    final = final_stock_health(command, adb, prior_boot_id_sha256)
    result = {
        "verdict": "RECOVERED_S20PLUS_G986N_STOCK_ROLLBACK_HEALTHY" if final["healthy"] else "RECOVERY_PENDING_S20PLUS_G986N_FINAL_HEALTH",
        "final_health": final,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }
    durable_create(run_dir / "recovery-result.json", result)
    if final["healthy"]:
        release_guard(run_dir)
    return result


def confirm_candidate_endpoint_reenumeration(
    run_dir: Path,
    confirmation: str,
    command: Command = bounded_command,
) -> dict[str, Any]:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    prepared = read_prepared(run_dir, allow_pre_candidate_compatible=True)
    if confirmation != CANDIDATE_ENDPOINT_CONFIRM:
        raise BootstrapError("candidate endpoint confirmation mismatch")
    if (run_dir / "candidate-intent.json").exists() or (run_dir / "candidate-endpoint-confirmation.json").exists():
        raise BootstrapError("candidate endpoint confirmation already consumed; replay forbidden")
    observed_endpoint = validate_candidate_endpoint_reenumeration(run_dir, prepared)
    live_endpoint = identify_download(command)
    if not endpoint_session_equivalent(live_endpoint, observed_endpoint):
        raise BootstrapError("Download endpoint changed after candidate confirmation evidence")
    ensure_pre_candidate_continuation(run_dir, prepared)
    durable_create(run_dir / "candidate-endpoint-confirmation.json", {
        "schema": "s20plus_g986n_f1_candidate_endpoint_confirmation_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "operator_confirmed": True,
        "confirmation": CANDIDATE_ENDPOINT_CONFIRM,
        "endpoint": live_endpoint,
        "no_replay": True,
        "at": utc_now(),
    })
    return execute(run_dir, prepared["approval_token"], command, confirmed_endpoint=live_endpoint)


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
    absence_re = re.compile(r"(?:/system/bin/sh: )?su: (?:not found|inaccessible(?: or not found)?|permission denied|no such file)", re.IGNORECASE)
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


def record_candidate_endpoint_reenumeration(
    run_dir: Path,
    binding_sha256: str,
    prepared_endpoint: dict[str, Any],
    observed_endpoint: dict[str, Any],
) -> Path:
    validate_download_endpoint_record(prepared_endpoint, "prepared Download endpoint")
    validate_download_endpoint_record(observed_endpoint, "observed Download endpoint")
    if observed_endpoint == prepared_endpoint:
        raise BootstrapError("Download endpoint was not re-enumerated")
    path = run_dir / "candidate-endpoint-reenumeration.json"
    if os.path.lexists(path):
        raise BootstrapError("candidate endpoint re-enumeration is already recorded; use confirmation handoff")
    durable_create(path, {
        "schema": "s20plus_g986n_f1_candidate_endpoint_reenumeration_v1",
        "version": VERSION,
        "binding_sha256": binding_sha256,
        "reason": "prepared-endpoint-reenumerated",
        "prepared_endpoint": prepared_endpoint,
        "observed_endpoint": observed_endpoint,
        "topology_continuity": observed_endpoint["topology_sha256"] == prepared_endpoint["topology_sha256"],
        "usb_profile_continuity": observed_endpoint["usb"] == prepared_endpoint["usb"],
        "operator_confirmation_required": CANDIDATE_ENDPOINT_CONFIRM,
        "no_replay": True,
        "at": utc_now(),
    })
    return path


def validate_candidate_endpoint_reenumeration(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(run_dir / "candidate-endpoint-reenumeration.json", "candidate endpoint re-enumeration")
    binding_sha256 = prepared["binding_sha256"]
    prepared_endpoint = prepared["binding"]["endpoint"]
    observed_endpoint = value.get("observed_endpoint") if isinstance(value, dict) else None
    expected_endpoint = value.get("prepared_endpoint") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "version", "binding_sha256", "reason", "prepared_endpoint", "observed_endpoint", "topology_continuity", "usb_profile_continuity", "operator_confirmation_required", "no_replay", "at"}
        or value.get("schema") != "s20plus_g986n_f1_candidate_endpoint_reenumeration_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("reason") != "prepared-endpoint-reenumerated"
        or value.get("operator_confirmation_required") != CANDIDATE_ENDPOINT_CONFIRM
        or value.get("topology_continuity") is not True
        or value.get("usb_profile_continuity") is not True
        or value.get("no_replay") is not True
        or expected_endpoint != prepared_endpoint
        or observed_endpoint == prepared_endpoint
    ):
        raise BootstrapError("candidate endpoint re-enumeration evidence is malformed or mismatched")
    validate_download_endpoint_record(expected_endpoint, "prepared Download endpoint")
    validate_download_endpoint_record(observed_endpoint, "observed Download endpoint")
    if observed_endpoint["topology_sha256"] != prepared_endpoint["topology_sha256"] or observed_endpoint["usb"] != prepared_endpoint["usb"]:
        raise BootstrapError("candidate endpoint re-enumeration lost profile/topology continuity")
    return observed_endpoint


def validate_candidate_endpoint_confirmation(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    value = read_exact_json(run_dir / "candidate-endpoint-confirmation.json", "candidate endpoint confirmation")
    endpoint = value.get("endpoint") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "version", "binding_sha256", "operator_confirmed", "confirmation", "endpoint", "no_replay", "at"}
        or value.get("schema") != "s20plus_g986n_f1_candidate_endpoint_confirmation_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != prepared["binding_sha256"]
        or value.get("operator_confirmed") is not True
        or value.get("confirmation") != CANDIDATE_ENDPOINT_CONFIRM
        or value.get("no_replay") is not True
    ):
        raise BootstrapError("candidate endpoint confirmation evidence is malformed or mismatched")
    validate_download_endpoint_record(endpoint, "confirmed Download endpoint")
    observed = validate_candidate_endpoint_reenumeration(run_dir, prepared)
    if not endpoint_session_equivalent(endpoint, observed):
        raise BootstrapError("candidate endpoint confirmation lost session continuity")
    return endpoint


def execute(
    run_dir: Path,
    approval: str,
    command: Command = bounded_command,
    confirmed_endpoint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    prepared = read_prepared(run_dir, allow_pre_candidate_compatible=confirmed_endpoint is not None)
    if approval != prepared["approval_token"]:
        raise BootstrapError("exact F1 approval token mismatch")
    if (run_dir / "candidate-intent.json").exists():
        raise BootstrapError("candidate attempt already exists; replay forbidden")
    if confirmed_endpoint is not None:
        confirmed_record = validate_candidate_endpoint_confirmation(run_dir, prepared)
        if confirmed_endpoint != confirmed_record:
            raise BootstrapError("confirmed endpoint argument does not match durable confirmation")
        ensure_pre_candidate_continuation(run_dir, prepared)
    validate_artifacts()
    adb = base.tool_receipt(ADB)["path"]
    if confirmed_endpoint is None:
        try:
            endpoint = identify_download(command)
        except Exception as exc:
            result = {
                "schema": "s20plus_g986n_magisk_bootstrap_f1_result_v1",
                "version": VERSION,
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_DOWNLOAD_ENDPOINT_UNCERTAIN",
                "failure_class": type(exc).__name__,
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
            durable_create(run_dir / "result.json", result)
            return result
        if endpoint != prepared["binding"]["endpoint"] and not endpoint_session_equivalent(endpoint, prepared["binding"]["endpoint"]):
            record_candidate_endpoint_reenumeration(run_dir, prepared["binding_sha256"], prepared["binding"]["endpoint"], endpoint)
            result = {
                "schema": "s20plus_g986n_magisk_bootstrap_f1_result_v1",
                "version": VERSION,
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_CANDIDATE_ENDPOINT_CONFIRMATION_REQUIRED",
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
                "candidate_endpoint_confirmation_required": CANDIDATE_ENDPOINT_CONFIRM,
            }
            durable_create(run_dir / "result.json", result)
            return result
    else:
        endpoint = validate_download_endpoint_record(confirmed_endpoint, "confirmed Download endpoint")
        if endpoint == prepared["binding"]["endpoint"]:
            raise BootstrapError("confirmed endpoint did not represent re-enumeration")
        if not endpoint_session_equivalent(endpoint, prepared["binding"]["endpoint"]) and (endpoint["topology_sha256"] != prepared["binding"]["endpoint"]["topology_sha256"] or endpoint["usb"] != prepared["binding"]["endpoint"]["usb"]):
            raise BootstrapError("confirmed endpoint lost profile/topology continuity")
    binding_sha256 = prepared["binding_sha256"]
    classification = transfer_once(run_dir, "candidate", endpoint, 1, binding_sha256)
    event(run_dir, 2, "candidate-transfer-finished", {"classification": classification})
    candidate_android = wait_android(command, adb, ANDROID_TIMEOUT) if classification == "odin_transfer_completed" else None
    root = {"root_verified": False, "attempts": 0}
    if candidate_android is not None:
        root = root_observation(command, adb, candidate_android[2])
    candidate_boot_id_sha256 = candidate_android[2]["boot_id_sha256"] if candidate_android is not None else None
    durable_create(run_dir / "candidate-observation.json", {"schema": "s20plus_g986n_f1_candidate_observation_v1", "version": VERSION, "classification": classification, "android_returned": candidate_android is not None, "boot_id_sha256": candidate_boot_id_sha256, **root})
    event(run_dir, 3, "candidate-observation-closed", {"root_verified": root["root_verified"]})
    rollback_mode_dispatched = False
    if candidate_android is not None:
        rollback_mode_dispatched = request_rollback_download(run_dir, command, adb, binding_sha256, candidate_android[2])
        if not rollback_mode_dispatched:
            result = {
                "schema": "s20plus_g986n_magisk_bootstrap_f1_result_v1",
                "version": VERSION,
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_MODE_UNCERTAIN",
                "candidate_transfer": classification,
                "candidate_root_verified": root["root_verified"],
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
                "rollback_mode_dispatch_confirmed": False,
                "other_target_command_count": 0,
                "s22plus_command_count": 0,
                "a90_command_count": 0,
            }
            durable_create(run_dir / "result.json", result)
            return result
    else:
        result = {
            "schema": "s20plus_g986n_magisk_bootstrap_f1_result_v1",
            "version": VERSION,
            "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED",
            "candidate_transfer": classification,
            "candidate_root_verified": root["root_verified"],
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
            "rollback_mode_dispatch_confirmed": False,
            "other_target_command_count": 0,
            "s22plus_command_count": 0,
            "a90_command_count": 0,
        }
        durable_create(run_dir / "result.json", result)
        return result
    try:
        baseline = validate_rollback_mode_transition(run_dir, binding_sha256, candidate_android[2])
    except Exception:
        result = {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_MODE_BASELINE_UNCERTAIN", "candidate_root_verified": root["root_verified"], "candidate_replay_permitted": False, "rollback_replay_permitted": False}
        durable_create(run_dir / "result.json", result)
        return result
    observed_result = wait_download_after_baseline(command, baseline, DOWNLOAD_TIMEOUT)
    if observed_result is None:
        result = {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED", "candidate_root_verified": root["root_verified"], "candidate_replay_permitted": False, "rollback_preapproved": True}
        durable_create(run_dir / "result.json", result)
        return result
    rollback_endpoint, rollback_arrival = observed_result
    durable_create(run_dir / "rollback-mode-observation.json", {"schema": "s20plus_g986n_f1_rollback_mode_observation_v1", "version": VERSION, "binding_sha256": binding_sha256, "baseline_sha256": canonical_sha(baseline), **rollback_arrival, "endpoint": rollback_endpoint, "replay_permitted": False, "at": utc_now()})
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


def recover_stock_after_candidate_android(
    run_dir: Path,
    prepared: dict[str, Any],
    command: Command,
    adb: str,
    candidate_identity: dict[str, str],
    root: dict[str, Any],
    candidate_classification: str,
) -> dict[str, Any]:
    binding_sha256 = prepared["binding_sha256"]
    if not os.path.lexists(run_dir / "rollback-mode-intent.json"):
        if not request_rollback_download(run_dir, command, adb, binding_sha256, candidate_identity):
            return {
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_MODE_UNCERTAIN",
                "candidate_root_verified": root["root_verified"],
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
    baseline = validate_rollback_mode_transition(run_dir, binding_sha256, candidate_identity)
    observation_path = run_dir / "rollback-mode-observation.json"
    if os.path.lexists(observation_path):
        rollback_endpoint = read_rollback_mode_observation(run_dir, binding_sha256, baseline)
    else:
        observed_result = wait_download_after_baseline(command, baseline, DOWNLOAD_TIMEOUT)
        if observed_result is None:
            return {
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_PHYSICAL_DOWNLOAD_REQUIRED",
                "candidate_root_verified": root["root_verified"],
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
        rollback_endpoint, rollback_arrival = observed_result
        durable_create(observation_path, {
            "schema": "s20plus_g986n_f1_rollback_mode_observation_v1",
            "version": VERSION,
            "binding_sha256": binding_sha256,
            "baseline_sha256": canonical_sha(baseline),
            **rollback_arrival,
            "endpoint": rollback_endpoint,
            "replay_permitted": False,
            "at": utc_now(),
        })
    if os.path.lexists(run_dir / "rollback-intent.json"):
        if not os.path.lexists(run_dir / "rollback-result.json"):
            return {
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_OUTCOME_UNKNOWN",
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
    else:
        rollback_class = transfer_once(run_dir, "rollback", rollback_endpoint, 4, binding_sha256)
        event(run_dir, 5, "rollback-transfer-finished", {"classification": rollback_class})
        if rollback_class != "odin_transfer_completed":
            result = {
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_UNCERTAIN",
                "rollback_transfer": rollback_class,
                "candidate_root_verified": root["root_verified"],
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
            durable_create(run_dir / "recovery-result.json", result)
            return result
    rollback_result = completed_transfer_result(run_dir, "rollback", binding_sha256)
    final = final_stock_health(command, adb, candidate_identity["boot_id_sha256"])
    verdict = (
        "PASS_S20PLUS_G986N_MAGISK_ROOT_PROVEN_STOCK_ROLLBACK_HEALTHY"
        if root["root_verified"] and final["healthy"]
        else "NO_PROOF_S20PLUS_G986N_CANDIDATE_STOCK_ROLLBACK_HEALTHY"
        if final["healthy"]
        else "RECOVERY_PENDING_S20PLUS_G986N_FINAL_HEALTH"
    )
    result = {
        "schema": "s20plus_g986n_magisk_bootstrap_f1_recovery_result_v1",
        "version": VERSION,
        "verdict": verdict,
        "candidate_transfer": candidate_classification,
        "candidate_root_verified": root["root_verified"],
        "rollback_transfer": rollback_result["classification"],
        "final_health": final,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "other_target_command_count": 0,
        "s22plus_command_count": 0,
        "a90_command_count": 0,
    }
    if final["healthy"]:
        durable_create(run_dir / "recovery-result.json", result)
        release_guard(run_dir)
    else:
        record_pending_health(run_dir, final)
    return result


def recover(run_dir: Path, command: Command = bounded_command) -> dict[str, Any]:
    if not F1_ACTIVE:
        raise BootstrapError("S20+ bootstrap F1 is not active")
    prepared = read_prepared(run_dir, allow_pre_candidate_compatible=True)
    candidate_intent = read_transfer_intent(run_dir, "candidate", prepared["binding_sha256"])
    prepared_endpoint = prepared["binding"]["endpoint"]
    prepared_mismatch = (
        candidate_intent["endpoint"]["device"] != prepared_endpoint["device"]
        or candidate_intent["endpoint"]["identity"][:3] != prepared_endpoint["endpoint_identity"][:3]
    )
    if prepared_mismatch:
        confirmed_endpoint = validate_candidate_endpoint_confirmation(run_dir, prepared)
        if candidate_intent["endpoint"] != {"device": confirmed_endpoint["device"], "identity": confirmed_endpoint["endpoint_identity"]}:
            raise BootstrapError("candidate intent does not match confirmed endpoint")
    adb = base.tool_receipt(ADB)["path"]
    candidate_result = validate_candidate_for_physical_handoff(run_dir, prepared["binding_sha256"])
    candidate_observation = validate_candidate_observation_for_physical_handoff(run_dir, candidate_result)
    if (run_dir / "rollback-intent.json").exists():
        ensure_recovery_continuation(run_dir, prepared)
        result_path = run_dir / "rollback-result.json"
        if not result_path.exists():
            return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_OUTCOME_UNKNOWN", "rollback_replay_permitted": False}
        try:
            completed_transfer_result(run_dir, "rollback", prepared["binding_sha256"])
        except BootstrapError:
            return {"verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_UNCERTAIN", "rollback_replay_permitted": False}
        late_path = run_dir / "candidate-late-observation.json"
        if os.path.lexists(late_path):
            candidate_identity, _root = observe_late_candidate_android(run_dir, prepared, command, adb)
            prior_boot_id_sha256 = candidate_identity["boot_id_sha256"]
        else:
            prior_boot_id_sha256 = candidate_observation.get("boot_id_sha256")
        final = final_stock_health(command, adb, prior_boot_id_sha256)
        result = {"verdict": "RECOVERED_S20PLUS_G986N_STOCK_ROLLBACK_HEALTHY" if final["healthy"] else "RECOVERY_PENDING_S20PLUS_G986N_FINAL_HEALTH", "final_health": final, "candidate_replay_permitted": False, "rollback_replay_permitted": False}
        if final["healthy"]:
            durable_create(run_dir / "recovery-result.json", result)
            release_guard(run_dir)
        else:
            record_pending_health(run_dir, final)
        return result
    if candidate_observation["android_returned"]:
        candidate_identity = {
            "serial_sha256": prepared["binding"]["transition"]["android_identity"]["serial_sha256"],
            "topology_sha256": prepared["binding"]["transition"]["android_identity"]["topology_sha256"],
            "boot_id_sha256": candidate_observation["boot_id_sha256"],
        }
        root = {
            key: candidate_observation[key]
            for key in candidate_observation
            if key in {"root_verified", "attempts", "output_sha256", "identity_drift", "observer_uncertain", "failure_class"}
        }
    else:
        validate_late_candidate_completion(run_dir, prepared, candidate_result, candidate_observation)
        try:
            candidate_identity, root = observe_late_candidate_android(run_dir, prepared, command, adb)
        except Exception:
            return {
                "verdict": "RECOVERY_PENDING_S20PLUS_G986N_ROLLBACK_MODE_CONFIRMATION_REQUIRED",
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
    ensure_recovery_continuation(run_dir, prepared)
    return recover_stock_after_candidate_android(
        run_dir,
        prepared,
        command,
        adb,
        candidate_identity,
        root,
        candidate_result["classification"],
    )


def render_plan() -> dict[str, Any]:
    return {"schema": "s20plus_g986n_magisk_bootstrap_f1_plan_v1", "version": VERSION, "active": F1_ACTIVE, "pre_candidate_abort_active": PRE_CANDIDATE_ABORT_ACTIVE, "target": f"{EXPECTED_MODEL}/{EXPECTED_DEVICE}/{EXPECTED_INCREMENTAL}", "candidate": {"size": CANDIDATE_SIZE, "sha256": CANDIDATE_SHA256, "member": "boot.img.lz4"}, "rollback": {"size": ROLLBACK_SIZE, "sha256": ROLLBACK_SHA256, "member": "boot.img.lz4", "mandatory": True}, "candidate_attempts": 1, "rollback_attempts": 1, "candidate_replay": False, "root_persistence_authorized": False, "live_flash_authorized": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--recover", action="store_true")
    modes.add_argument("--confirm-rollback-mode", action="store_true")
    modes.add_argument("--confirm-candidate-endpoint", action="store_true")
    modes.add_argument("--abort-pre-candidate", action="store_true")
    modes.add_argument("--close-pre-candidate", action="store_true")
    modes.add_argument("--close-endpoint-uncertain", action="store_true")
    modes.add_argument("--abandon-pre-effect", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
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
    if args.abandon_pre_effect:
        try:
            path = abandon_pre_effect(run_dir)
        except Exception:
            print("FAIL_S20PLUS_G986N_F1_PRE_EFFECT_ABANDON_CLOSED")
            return 1
        print("PASS_S20PLUS_G986N_F1_PRE_EFFECT_ABANDONED")
        print(f"result={path}")
        return 0
    if args.close_pre_candidate:
        try:
            path = close_pre_candidate_transition(run_dir)
        except Exception:
            print("FAIL_S20PLUS_G986N_F1_PRE_CANDIDATE_CLOSE_CLOSED")
            return 1
        print("PASS_S20PLUS_G986N_F1_PRE_CANDIDATE_CLOSED")
        print(f"result={path}")
        return 0
    if args.close_endpoint_uncertain:
        try:
            path = close_endpoint_uncertain_transition(run_dir)
        except Exception:
            print("FAIL_S20PLUS_G986N_F1_ENDPOINT_UNCERTAIN_CLOSE_CLOSED")
            return 1
        print("PASS_S20PLUS_G986N_F1_ENDPOINT_UNCERTAIN_CLOSED")
        print(f"result={path}")
        return 0
    if args.abort_pre_candidate:
        try:
            result = abort_pre_candidate(run_dir)
        except Exception:
            print("FAIL_S20PLUS_G986N_F1_PRE_CANDIDATE_ABORT_CLOSED")
            return 1
        print(result["verdict"])
        result_name = "pre-candidate-abort-final.json" if result["verdict"] == "PASS_S20PLUS_G986N_PRE_CANDIDATE_ABORT_NORMAL_HEALTHY" else "pre-candidate-abort-result.json"
        print(f"result={run_dir / result_name}")
        return 0
    try:
        if args.execute:
            result = execute(run_dir, args.approval or "")
        elif args.confirm_candidate_endpoint:
            result = confirm_candidate_endpoint_reenumeration(run_dir, args.confirmation or "")
        elif args.confirm_rollback_mode:
            result = confirm_rollback_mode(run_dir, args.confirmation or "")
        else:
            result = recover(run_dir)
    except Exception:
        print("FAIL_S20PLUS_G986N_F1_CLOSED")
        return 1
    print(result["verdict"])
    result_name = "result.json" if args.execute else "recovery-result.json"
    if args.confirm_rollback_mode:
        result_name = "recovery-result.json" if (run_dir / "recovery-result.json").exists() else "rollback-handoff-intent.json"
    if args.confirm_candidate_endpoint:
        result_name = "result.json"
    print(f"result={run_dir / result_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
