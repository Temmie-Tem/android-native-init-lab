#!/usr/bin/env python3
"""P3.20 S22+ one-shot D1 baseline rotation.

The default invocation is an H0 fixture rehearsal.  The live branch is a
single exact ``adb reboot`` for the bound SM-S906N/g0q/FYG8 target.  It uses
the reviewed P2.96 state-machine shape and the common raw-capture helper,
but has its own P3.20 namespace, ordinal, binding, and approval.  It never
flashes, enters Download, or grants F1 authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import types
from typing import Any, Mapping, Protocol


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
SCRIPT_DIR = SCRIPT.parent
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p320_d1_fresh_baseline.json"
)
P296_PRIMITIVE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p296/d1-baseline-rotation/"
    "s22plus_fyg8_p296_baseline_rotation_d1.py"
)
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")

RUN_PARENT = ROOT / "workspace/private/runs/device-action-d1-p320-fresh-baseline"
RUN_DIR = RUN_PARENT / "p320-d1-fresh-baseline-1"
RUN_ARM = RUN_PARENT / "p320-d1-fresh-baseline-1.arm.json"
RUN_STOP = RUN_DIR / "stop.json"
RAW_ROOT = RUN_PARENT / "p320-d1-fresh-baseline-1-raw"
RAW_ADB_DIR = RAW_ROOT / "raw-adb"
ADB_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p320/d1-fresh-baseline/"
    "adb-05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)

TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
    # This is a digest, not the Android serial.  The serial itself is never
    # written to the tracked binding or any result.
    "adb_serial_sha256": "c5302ccc08374d408ca3ec4df0ef23770d5ecd35ce173b7d150c4316e9a0757b",
}
P320_RUN_ID = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
ORDINAL = "p320-d1-fresh-baseline-1"
BINDING_SCHEMA = "s22plus_fyg8_p320_d1_fresh_baseline_execution_binding_v1"
BINDING_ID = "s22plus-fyg8-p320-d1-fresh-baseline-v1"
AUTHORITY_PREFIX = "DEVICE-ACTION-D1-P320-FRESH-BASELINE-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P320_D1_FRESH_BASELINE_H0_CAPABILITY_V1"
RESULT_SCHEMA = "s22plus_fyg8_p320_d1_fresh_baseline_v1_result"
RESULT_VERDICT = "PASS_P320_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
STOP_SCHEMA = "s22plus_fyg8_p320_d1_fresh_baseline_stop_v1"
STOP_VERDICT = "STOP_P320_D1_FRESH_BASELINE_CONSUMED_NO_REPLAY"
HOST_ADB_SIZE = 716_968
HOST_ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
RAW_MAX = 4 * 1024 * 1024
SERIAL_RE = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
DEVPATH_RE = re.compile(r"usb:[0-9]+(?:-[0-9]+(?:\.[0-9]+)*)?\Z")


class D1Error(RuntimeError):
    """The P3.20 D1 action failed closed."""


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class RealClock:
    @staticmethod
    def now() -> float:
        return time.monotonic()

    @staticmethod
    def sleep(seconds: float) -> None:
        time.sleep(seconds)


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise D1Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.absolute())


def _identity(payload: bytes) -> dict[str, Any]:
    return {"path": _relative(SCRIPT), "size": len(payload), "sha256": sha256_bytes(payload)}


def _receipt(path: Path, payload: bytes, *, mode: str | None = None) -> dict[str, Any]:
    value = {"path": _relative(path), "size": len(payload), "sha256": sha256_bytes(payload)}
    if mode is not None:
        value.update({"mode": mode, "nlink": 1})
    return value


def _stable_read(path: Path, label: str, *, maximum: int = 8 * 1024 * 1024,
                 expected: Mapping[str, Any] | None = None,
                 mode: int | None = None, owner: int | None = os.getuid()) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise D1Error(f"{label} path is indirect")
        descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise D1Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or (owner is not None and before.st_uid != owner)
            or before.st_nlink != 1
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
            or before.st_size > maximum
        ):
            raise D1Error(f"{label} identity differs")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
              "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, name) != getattr(after, name) for name in fields):
        raise D1Error(f"{label} changed while reading")
    payload = b"".join(chunks)
    if expected is not None and {
        "size": len(payload), "sha256": sha256_bytes(payload)
    } != {"size": expected.get("size"), "sha256": expected.get("sha256")}:
        raise D1Error(f"{label} bytes differ")
    return payload


def _strict_object(
    payload: bytes,
    label: str,
    *,
    canonical_required: bool,
) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise D1Error(f"{label} contains a duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique,
                           parse_constant=lambda item: (_ for _ in ()).throw(
                               D1Error(f"{label} contains non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D1Error(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise D1Error(f"{label} is not an object")
    if canonical_required and canonical(value) != payload:
        raise D1Error(f"{label} is not a canonical object")
    return value


def _strict(payload: bytes, label: str) -> dict[str, Any]:
    return _strict_object(payload, label, canonical_required=True)


def _strict_document(payload: bytes, label: str) -> dict[str, Any]:
    return _strict_object(payload, label, canonical_required=False)


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def _load_json(path: Path, label: str) -> dict[str, Any]:
    return _strict(_stable_read(path, label, maximum=512 * 1024), label)


def _source_receipts() -> dict[str, dict[str, Any]]:
    paths = {
        "d1_source": SCRIPT,
        "p296_primitive": P296_PRIMITIVE,
        "d0_runtime": D0_RUNTIME,
        "raw_capture": RAW_CAPTURE,
        "profile": PROFILE,
        "host_adb": HOST_ADB,
    }
    result: dict[str, dict[str, Any]] = {}
    for name, path in paths.items():
        payload = _stable_read(path, name, maximum=HOST_ADB_SIZE if name == "host_adb" else 2 * 1024 * 1024,
                               owner=None if name == "host_adb" else os.getuid())
        result[name] = _receipt(path, payload)
    return result


def _expected_binding(inputs: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": BINDING_ID,
        "action": "one exact attended normal Android reboot with raw-first D1 evidence",
        "authority_prefix": AUTHORITY_PREFIX,
        "target": TARGET,
        "ordinal": ORDINAL,
        "inputs": dict(inputs),
        "run": {
            "parent": _relative(RUN_PARENT),
            "directory": _relative(RUN_DIR),
            "arm": _relative(RUN_ARM),
            "stop": _relative(RUN_STOP),
            "raw_root": _relative(RAW_ROOT),
            "raw_adb": _relative(RAW_ADB_DIR),
            "adb_snapshot": _relative(ADB_SNAPSHOT),
        },
        "bounds": {
            "reboot_count": 1,
            "other_target_commands": 0,
            "initiation_bound_sec": 60,
            "return_bound_sec": 240,
            "inventory_timeout_sec": 10,
            "read_timeout_sec": 180,
            "raw_text_maximum": RAW_MAX,
        },
        "safety": {
            "partition_payload": False,
            "odin": False,
            "download_transition": False,
            "candidate_transfer": False,
            "f1_authorized": False,
            "replay_authorized": False,
            "other_targets_commanded": False,
        },
        "independent_review": dict(review),
    }


def _validated_static_inputs() -> dict[str, Any]:
    payloads = _source_receipts()
    binding_payload = _stable_read(BINDING_MANIFEST, "P3.20 D1 binding", maximum=256 * 1024)
    binding = _strict(binding_payload, "P3.20 D1 binding")
    review = binding.get("independent_review")
    if review not in (
        {"status": "review-pending", "verdict": None},
        {"status": "pass-go", "verdict": REVIEW_VERDICT},
    ):
        raise D1Error("P3.20 D1 review state differs")
    if not _typed_equal(binding, _expected_binding(payloads, review)):
        raise D1Error("P3.20 D1 binding does not match exact inputs")
    return {
        "manifest": binding,
        "manifest_payload": binding_payload,
        "manifest_receipt": _receipt(BINDING_MANIFEST, binding_payload),
        "authority": AUTHORITY_PREFIX + sha256_bytes(binding_payload),
        "approval_sha256": sha256_bytes(
            (AUTHORITY_PREFIX + sha256_bytes(binding_payload)).encode("ascii")
        ),
        "payloads": payloads,
    }


def _durable_create(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical(dict(value))
    parent = path.parent.absolute()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.resolve(strict=True) != parent:
        raise D1Error("journal parent is indirect")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC |
                             getattr(os, "O_NOFOLLOW", 0), 0o400)
    except FileExistsError as exc:
        raise D1Error(f"journal already exists: {path.name}; replay is forbidden") from exc
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D1Error("journal write made no progress")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _prepare_snapshot(payload: bytes, path: Path) -> None:
    if len(payload) != HOST_ADB_SIZE or sha256_bytes(payload) != HOST_ADB_SHA256:
        raise D1Error("host ADB snapshot source differs")
    parent = path.parent.absolute()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.resolve(strict=True) != parent:
        raise D1Error("ADB snapshot parent is indirect")
    if path.exists() or path.is_symlink():
        current = _stable_read(path, "ADB snapshot", maximum=HOST_ADB_SIZE, mode=0o500, owner=os.getuid())
        if current != payload:
            raise D1Error("ADB snapshot already exists with different bytes")
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=".adb-", dir=parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o500)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D1Error("ADB snapshot write made no progress")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise D1Error("ADB snapshot publication raced; replay is forbidden") from exc
        directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    if _stable_read(path, "published ADB snapshot", maximum=HOST_ADB_SIZE, mode=0o500) != payload:
        raise D1Error("published ADB snapshot differs")


def _inventory_rows(text: str) -> list[tuple[str, str, set[str]]]:
    rows: list[tuple[str, str, set[str]]] = []
    for line in text.splitlines():
        if not line or line.startswith("List of devices attached"):
            continue
        fields = line.split()
        if len(fields) < 2:
            raise D1Error("ADB inventory contains a malformed row")
        rows.append((fields[0], fields[1], set(fields[2:])))
    return rows


def _inventory_digest(rows: list[tuple[str, str, set[str]]]) -> str:
    value = []
    for serial, state, metadata in sorted(rows, key=lambda item: item[0]):
        transport = sorted(item for item in metadata if item.startswith("transport_id:"))
        if len(transport) != 1 or not transport[0].removeprefix("transport_id:").isascii() or not transport[0].removeprefix("transport_id:").isdigit():
            raise D1Error("ADB inventory transport_id differs")
        value.append({
            "serial_sha256": sha256_text(serial),
            "state": state,
            "stable_metadata": sorted(metadata - set(transport)),
        })
    return sha256_bytes(canonical(value).rstrip(b"\n"))


def _raw_inventory(raw: Any) -> dict[str, Any]:
    try:
        root_stat = RAW_ROOT.lstat()
    except FileNotFoundError:
        return {"root_present": False, "directory_present": False, "complete": False, "handles": []}
    if not stat.S_ISDIR(root_stat.st_mode) or stat.S_IMODE(root_stat.st_mode) != 0o700 or root_stat.st_uid != os.getuid() or RAW_ROOT.resolve(strict=True) != RAW_ROOT.absolute():
        raise D1Error("raw root identity differs")
    if not RAW_ADB_DIR.exists():
        return {"root_present": True, "directory_present": False, "complete": False, "handles": []}
    directory = RAW_ADB_DIR.lstat()
    if not stat.S_ISDIR(directory.st_mode) or stat.S_IMODE(directory.st_mode) != 0o700 or directory.st_uid != os.getuid() or RAW_ADB_DIR.resolve(strict=True) != RAW_ADB_DIR.absolute():
        raise D1Error("raw ADB directory identity differs")
    children = sorted(item.name for item in RAW_ADB_DIR.iterdir())
    handles = []
    for name in children:
        if not name.endswith(".capture.json"):
            continue
        try:
            handle = raw.load_handle(RAW_ADB_DIR / name)
        except BaseException as exc:
            raise D1Error("raw ADB receipt differs") from exc
        handles.append({
            "name": handle.name,
            "returncode": handle.returncode,
            "timed_out": handle.timed_out,
            "output_exceeded": handle.output_exceeded,
            "producer_error_type": handle.producer_error_type,
            "receipt": name,
            "stdout": handle.stdout_path.name,
            "stderr": handle.stderr_path.name,
        })
    return {
        "root_present": True,
        "directory_present": True,
        "complete": bool(handles) and all(
            item["returncode"] == 0 and not item["timed_out"] and not item["output_exceeded"] and item["producer_error_type"] is None
            for item in handles
        ),
        "children": children,
        "handles": handles,
    }


def _health(profile: Mapping[str, Any], properties: Mapping[str, str], root_health: Mapping[str, str], no_download: bool, *, initial: bool) -> dict[str, Any]:
    expected = profile["start_health"] if initial else profile["final_health"]
    target = profile["target"]
    if (
        properties.get("model") != TARGET["model"]
        or properties.get("device") != TARGET["codename"]
        or properties.get("incremental") != TARGET["build"]
        or properties.get("boot_completed") != "1"
        or properties.get("bootanim") != "stopped"
        or properties.get("verified_boot_state") != expected["verified_boot_state"]
        or not root_health.get("root", "").startswith("uid=0(root)")
        or no_download is not True
        or root_health.get("boot") != expected["boot_sha256"]
    ):
        raise D1Error("Android health differs from the bound FYG8 profile")
    for name, digest in expected["supporting_partition_sha256"].items():
        if root_health.get(name) != digest:
            raise D1Error(f"supporting partition identity differs: {name}")
    boot_id = properties.get("boot_id")
    kernel = properties.get("kernel_release")
    if not isinstance(boot_id, str) or not boot_id or not isinstance(kernel, str) or not kernel:
        raise D1Error("boot identity or kernel release is unavailable")
    return {
        "android_boot_completed": True,
        "boot_animation_stopped": True,
        "boot_id_sha256": sha256_text(boot_id),
        "boot_sha256": root_health["boot"],
        "kernel_release": kernel,
        "odin_endpoint_absent": True,
        "root_verified": True,
        "supporting_partition_sha256": {
            name: root_health[name] for name in ("dtbo", "recovery", "vendor_boot")
        },
        "verified_boot_state": properties["verified_boot_state"],
    }


class RotationTransport(Protocol):
    reboot_count: int
    other_target_commands: int
    def select_exact(self) -> tuple[str, dict[str, Any]]: ...
    def snapshot(self, serial: str, *, initial: bool) -> dict[str, Any]: ...
    def reboot_once(self, serial: str) -> None: ...
    def poll(self, serial: str) -> dict[str, Any]: ...


def _load_runtime(payloads: Mapping[str, Any]) -> tuple[Any, Any]:
    raw_module = types.ModuleType("device_action_raw_capture_v1")
    raw_module.__file__ = str(RAW_CAPTURE)
    f1_module = types.ModuleType("device_action_f1_v2")
    f1_module.json_sha256 = lambda value: sha256_bytes(canonical(value).rstrip(b"\n"))
    d0_module = types.ModuleType("device_action_d0_v2")
    d0_module.__file__ = str(D0_RUNTIME)
    prior_raw = sys.modules.get("device_action_raw_capture_v1")
    prior_f1 = sys.modules.get("device_action_f1_v2")
    prior_d0 = sys.modules.get("device_action_d0_v2")
    try:
        sys.modules["device_action_raw_capture_v1"] = raw_module
        exec(compile(payloads["raw_capture_bytes"], str(RAW_CAPTURE), "exec"), raw_module.__dict__)
        sys.modules["device_action_f1_v2"] = f1_module
        sys.modules["device_action_d0_v2"] = d0_module
        exec(compile(payloads["d0_runtime_bytes"], str(D0_RUNTIME), "exec"), d0_module.__dict__)
    except BaseException as exc:
        raise D1Error(f"bound D0 runtime failed to load: {type(exc).__name__}") from exc
    finally:
        if prior_raw is None:
            sys.modules.pop("device_action_raw_capture_v1", None)
        else:
            sys.modules["device_action_raw_capture_v1"] = prior_raw
        if prior_f1 is None:
            sys.modules.pop("device_action_f1_v2", None)
        else:
            sys.modules["device_action_f1_v2"] = prior_f1
        if prior_d0 is None:
            sys.modules.pop("device_action_d0_v2", None)
        else:
            sys.modules["device_action_d0_v2"] = prior_d0
    return d0_module, raw_module


class RawFirstTransport:
    def __init__(self, d0: Any, raw: Any, profile: Mapping[str, Any], binding: Mapping[str, Any], raw_root: Path, adb: Path):
        self.d0 = d0
        self.raw = raw
        self.profile = profile
        self.binding = binding
        self.client = d0.AdbReadOnlyClient(adb)
        self.client.bind_raw_capture_dir(raw_root)
        self.adb = self.client.adb
        self.selected: str | None = None
        self.topology_sha256: str | None = None
        self.reboot_count = 0
        self.other_target_commands = 0

    def _inventory(self, *, poll: bool = False) -> list[tuple[str, str, set[str]]]:
        del poll
        return _inventory_rows(self.client._run(["devices", "-l"], "adb inventory", 10))

    def select_exact(self) -> tuple[str, dict[str, Any]]:
        rows = self._inventory()
        matches = [serial for serial, state, metadata in rows if state == "device" and {"model:SM_S906N", "device:g0q"} <= metadata]
        if len(matches) != 1:
            raise D1Error(f"expected exactly one connected FYG8 S22+, found {len(matches)}")
        serial = matches[0]
        if SERIAL_RE.fullmatch(serial) is None or sha256_text(serial) != TARGET["adb_serial_sha256"]:
            raise D1Error("selected S22+ serial identity differs")
        topology = self.client.topology(serial)
        if DEVPATH_RE.fullmatch(topology) is None:
            raise D1Error("selected S22+ topology is malformed")
        topology_sha = sha256_text(topology)
        if self.selected is not None and serial != self.selected:
            raise D1Error("selected S22+ changed")
        if self.topology_sha256 is not None and topology_sha != self.topology_sha256:
            raise D1Error("selected S22+ topology changed")
        self.selected = serial
        self.topology_sha256 = topology_sha
        models = sorted(token.split(":", 1)[1] for _s, _state, metadata in rows for token in metadata if token.startswith("model:"))
        return serial, {
            "inventory_count": len(rows),
            "inventory_models": models,
            "inventory_sha256": _inventory_digest(rows),
            "selected_serial_sha256": sha256_text(serial),
            "selected_topology_sha256": topology_sha,
            "other_targets_commanded": False,
        }

    def snapshot(self, serial: str, *, initial: bool | None = None) -> dict[str, Any]:
        if serial != self.selected:
            raise D1Error("snapshot target differs")
        properties = self.client.properties(serial)
        root_health = self.client.root_health(serial)
        topology = self.client.topology(serial)
        if self.topology_sha256 != sha256_text(topology):
            raise D1Error("snapshot topology changed")
        no_download = self.d0.usb_snapshot(self.d0.DEFAULT_USB_ROOT, self.profile["target"]["download"])["download_endpoint_count"] == 0
        # Keep the P2.96 transport contract: the reviewed primitive owns the
        # health predicate and consumes this exact read-only snapshot shape.
        return {
            "properties": properties,
            "root_health": root_health,
            "topology": topology,
            "no_odin": no_download,
        }

    def reboot_once(self, serial: str) -> None:
        if serial != self.selected or self.reboot_count:
            raise D1Error("reboot target or count differs")
        # Mark the command consumed before checking its receipt.  A cut after
        # dispatch is never eligible for a second reboot.
        self.reboot_count = 1
        handle = self.client.capture_command(["-s", serial, "reboot"], "adb normal reboot", timeout=20, maximum=RAW_MAX)
        current = self.raw.load_handle(handle.receipt_path)
        self.raw.require_success(current)
        if self.raw.read_stdout(current, maximum=RAW_MAX) or self.raw.read_stderr(current, maximum=RAW_MAX):
            raise D1Error("normal reboot emitted output")

    def poll(self, serial: str) -> dict[str, Any]:
        rows = self._inventory(poll=True)
        row = next((item for item in rows if item[0] == serial), None)
        if row is None or row[1] != "device":
            return {"connected": False}
        if serial != self.selected:
            self.other_target_commands += 1
            raise D1Error("poll target differs")
        try:
            properties = self.client.properties(serial)
        except (self.d0.D0Error, OSError):
            return {"connected": True, "ready": False}
        return {
            "connected": True,
            "ready": properties.get("boot_completed") == "1" and properties.get("bootanim") == "stopped",
            "boot_id": properties.get("boot_id"),
        }


def _load_p296(payload: bytes, d0: Any) -> Any:
    """Load the exact reviewed primitive; no local reboot loop is copied."""
    module = types.ModuleType("p320_bound_p296_d1")
    module.__file__ = str(P296_PRIMITIVE)
    old_d0 = sys.modules.get("device_action_d0_v2")
    old_module = sys.modules.get(module.__name__)
    try:
        sys.modules["device_action_d0_v2"] = d0
        sys.modules[module.__name__] = module
        exec(compile(payload, str(P296_PRIMITIVE), "exec"), module.__dict__)
    except BaseException as exc:
        raise D1Error(f"P2.96 primitive failed to load: {type(exc).__name__}") from exc
    finally:
        if old_d0 is None:
            sys.modules.pop("device_action_d0_v2", None)
        else:
            sys.modules["device_action_d0_v2"] = old_d0
        if old_module is None:
            sys.modules.pop(module.__name__, None)
        else:
            sys.modules[module.__name__] = old_module
    return module


def perform_rotation(transport: RotationTransport, binding: Mapping[str, Any], profile: Mapping[str, Any], clock: Clock, raw: Any, raw_evidence: dict[str, Any], primitive_payload: bytes, d0: Any) -> dict[str, Any]:
    """Run P2.96's one-reboot primitive with P3.20-owned journals."""
    serial, selection = transport.select_exact()
    primitive_binding = {
        "target": {
            "model": TARGET["model"],
            "device": TARGET["codename"],
            "firmware_incremental": TARGET["build"],
            "adb_serial_sha256": selection["selected_serial_sha256"],
            "usb_topology_sha256": selection["selected_topology_sha256"],
        },
        "health": {
            "verified_boot_state": profile["start_health"]["verified_boot_state"],
            "boot_sha256": profile["start_health"]["boot_sha256"],
            "supporting_partition_sha256": dict(profile["start_health"]["supporting_partition_sha256"]),
        },
    }
    module = _load_p296(primitive_payload, d0)
    module.SCHEMA = "s22plus_fyg8_p320_d1_fresh_baseline_v1"
    module.VERDICT = RESULT_VERDICT
    module.APPROVAL = binding["approval"]
    module.RUN_ROOT = RUN_PARENT
    module.PROFILE = PROFILE
    module.INITIATION_BOUND_SEC = 60.0
    module.RETURN_BOUND_SEC = 240.0
    original_create = d0.durable_create

    def bound_create(path: Path, value: dict[str, Any]) -> None:
        if path == RUN_DIR / "start.json":
            value = {
                **value,
                "execution_manifest": binding["manifest_receipt"],
                "ordinal": ORDINAL,
                "run_id": P320_RUN_ID,
                "raw_evidence": _raw_inventory(raw),
                "reboot_requested": True,
            }
        elif path == RUN_DIR / "result.json":
            value = {
                **value,
                "execution_manifest": binding["manifest_receipt"],
                "ordinal": ORDINAL,
                "run_id": P320_RUN_ID,
                "raw_evidence": _raw_inventory(raw),
                "device_contact": True,
                "live_authorized": True,
                "other_targets_commanded": False,
            }
        else:
            raise D1Error("P2.96 attempted an unbound journal path")
        _durable_create(path, value)

    d0.durable_create = bound_create
    try:
        # P2.96 invokes the primitive's exact select/snapshot/reboot/poll
        # choreography.  The transport above is the only P3.20 seam.
        module.perform_rotation(transport, primitive_binding, module.RealClock() if clock is None else clock, RUN_DIR)
        payload = _stable_read(RUN_DIR / "result.json", "P3.20 D1 result", maximum=512 * 1024, mode=0o400)
        result = _strict(payload, "P3.20 D1 result")
        if result.get("schema") != RESULT_SCHEMA or result.get("verdict") != RESULT_VERDICT or result.get("reboot_count") != 1 or result.get("before", {}).get("boot_id_sha256") == result.get("after", {}).get("boot_id_sha256"):
            raise D1Error("P3.20 result transformed from P2.96 primitive differs")
        return result
    finally:
        d0.durable_create = original_create


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
    def now(self) -> float:
        return self.value
    def sleep(self, seconds: float) -> None:
        self.value += seconds


class FixtureTransport:
    def __init__(self) -> None:
        self.serial = "FIXTURE_S22"
        self.topology = "usb:1-1"
        self.before_boot_id = "11111111-1111-1111-1111-111111111111"
        self.after_boot_id = "22222222-2222-2222-2222-222222222222"
        self.reboot_count = 0
        self.other_target_commands = 0
        self.poll_count = 0

    def select_exact(self) -> tuple[str, dict[str, Any]]:
        return self.serial, {
            "inventory_count": 2,
            "inventory_models": ["SM_G986N", "SM_S906N"],
            "inventory_sha256": "a" * 64,
            "selected_serial_sha256": sha256_text(self.serial),
            "selected_topology_sha256": sha256_text(self.topology),
            "other_targets_commanded": False,
        }

    def snapshot(self, serial: str, *, initial: bool | None = None) -> dict[str, Any]:
        if serial != self.serial:
            self.other_target_commands += 1
            raise D1Error("fixture targeted another device")
        boot_id = self.after_boot_id if self.reboot_count else self.before_boot_id
        return {
            "properties": {
                "model": TARGET["model"],
                "device": TARGET["codename"],
                "incremental": TARGET["build"],
                "boot_completed": "1",
                "bootanim": "stopped",
                "verified_boot_state": "orange",
                "boot_id": boot_id,
                "kernel_release": "fixture-kernel",
            },
            "root_health": {
                "root": "uid=0(root) gid=0(root)",
                "boot": "1" * 64,
                "vendor_boot": "4" * 64,
                "dtbo": "2" * 64,
                "recovery": "3" * 64,
            },
            "topology": self.topology,
            "no_odin": True,
        }

    def reboot_once(self, serial: str) -> None:
        if serial != self.serial or self.reboot_count:
            raise D1Error("fixture reboot target/count differs")
        self.reboot_count = 1

    def poll(self, serial: str) -> dict[str, Any]:
        if serial != self.serial:
            self.other_target_commands += 1
            raise D1Error("fixture poll targeted another device")
        self.poll_count += 1
        return {"connected": self.poll_count > 1, "ready": self.poll_count > 1, "boot_id": self.after_boot_id}


def _fixture_binding() -> dict[str, Any]:
    return {
        "manifest_receipt": {"path": "fixture-binding.json", "size": 1, "sha256": "a" * 64},
        "approval_sha256": "b" * 64,
        "approval": "fixture-approval",
    }


def self_test() -> dict[str, Any]:
    transport = FixtureTransport()
    d0_payload = _stable_read(D0_RUNTIME, "D0 runtime", maximum=2 * 1024 * 1024)
    raw_payload = _stable_read(RAW_CAPTURE, "raw capture", maximum=2 * 1024 * 1024)
    d0, raw = _load_runtime({"d0_runtime_bytes": d0_payload, "raw_capture_bytes": raw_payload})
    primitive_payload = _stable_read(P296_PRIMITIVE, "P2.96 primitive", maximum=2 * 1024 * 1024)
    profile = {
        "start_health": {
            "verified_boot_state": "orange",
            "boot_sha256": "1" * 64,
            "supporting_partition_sha256": {
                "vendor_boot": "4" * 64,
                "dtbo": "2" * 64,
                "recovery": "3" * 64,
            },
        }
    }
    with tempfile.TemporaryDirectory(prefix="p320-d1-fixture-") as temporary:
        global RUN_DIR
        previous = RUN_DIR
        RUN_DIR = Path(temporary) / "run"
        try:
            result = perform_rotation(
                transport,
                _fixture_binding(),
                profile,
                FakeClock(),
                raw,
                {"complete": True, "handles": []},
                primitive_payload,
                d0,
            )
        finally:
            RUN_DIR = previous
    if result["reboot_count"] != 1 or transport.reboot_count != 1 or transport.other_target_commands != 0 or result["before"]["boot_id_sha256"] == result["after"]["boot_id_sha256"]:
        raise D1Error("P3.20 D1 fixture result differs")
    return {
        "schema": "s22plus_fyg8_p320_d1_fresh_baseline_fixture_h0",
        "verdict": "PASS_P320_D1_FRESH_BASELINE_FIXTURE_H0",
        "ordinal": ORDINAL,
        "run_id": P320_RUN_ID,
        "reboot_count": transport.reboot_count,
        "other_target_commands": transport.other_target_commands,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
    }


def _preflight() -> None:
    for path in (RUN_PARENT, RUN_ARM, RUN_DIR, RAW_ROOT, ADB_SNAPSHOT):
        if path.exists() or path.is_symlink():
            raise D1Error(f"fixed P3.20 D1 namespace already exists: {path.name}; replay is forbidden")


def _prepare_raw_root() -> None:
    """Create the owned raw root after the arm and before transport binding."""
    if not RUN_PARENT.is_dir() or RUN_PARENT.is_symlink():
        raise D1Error("P3.20 D1 arm parent is unavailable")
    try:
        os.mkdir(RAW_ROOT, 0o700)
    except FileExistsError as exc:
        raise D1Error("P3.20 D1 raw root already exists; replay is forbidden") from exc
    os.chmod(RAW_ROOT, 0o700)
    metadata = RAW_ROOT.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or metadata.st_uid != os.getuid()
        or RAW_ROOT.resolve(strict=True) != RAW_ROOT.absolute()
    ):
        raise D1Error("P3.20 D1 raw root identity differs")
    directory = os.open(RUN_PARENT, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _publish_stop(inputs: Mapping[str, Any], error: BaseException) -> None:
    if not RUN_DIR.exists():
        RUN_DIR.mkdir(mode=0o700, parents=False)
    stage = "after-result-publication" if (RUN_DIR / "result.json").exists() else "after-start-before-result" if (RUN_DIR / "start.json").exists() else "after-arm-before-start"
    value = {
        "schema": STOP_SCHEMA,
        "verdict": STOP_VERDICT,
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "ordinal": ORDINAL,
        "run_directory": _relative(RUN_DIR),
        "stage": stage,
        "error_type": type(error).__name__,
        "error": str(error)[:512],
        "reboot_dispatch_possible": (RUN_DIR / "start.json").exists(),
        "candidate_transfer": False,
        "partition_transfer": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
        "result_reusable": False,
        "replay_authorized": False,
        "private_raw_evidence_preserved": RAW_ROOT.exists(),
    }
    _durable_create(RUN_STOP, value)


def run_live(approval: str) -> dict[str, Any]:
    static = _validated_static_inputs()
    if static["manifest"]["independent_review"] != {"status": "pass-go", "verdict": REVIEW_VERDICT}:
        raise D1Error("P3.20 D1 independent review is absent")
    if approval != static["authority"]:
        raise D1Error("exact P3.20 D1 approval is absent")
    _preflight()
    payloads = static["payloads"]
    profile = _strict_document(
        _stable_read(
            PROFILE,
            "S22+ target profile",
            maximum=2 * 1024 * 1024,
            expected=payloads["profile"],
        ),
        "S22+ target profile",
    )
    if profile.get("schema") != "device_action_target_profile_v2" or profile.get("target", {}).get("model") != TARGET["model"] or profile.get("target", {}).get("device") != TARGET["codename"] or profile.get("target", {}).get("firmware_incremental") != TARGET["build"]:
        raise D1Error("S22+ profile identity differs")
    _durable_create(RUN_ARM, {
        "schema": f"{BINDING_SCHEMA}_arm",
        "execution_manifest": static["manifest_receipt"],
        "approval_sha256": sha256_bytes(approval.encode("ascii")),
        "ordinal": ORDINAL,
        "action": static["manifest"]["action"],
        "consumed": True,
        "device_contact_before_arm": False,
        "replay_authorized": False,
    })
    try:
        _prepare_raw_root()
        adb_payload = _stable_read(HOST_ADB, "host ADB", maximum=HOST_ADB_SIZE, expected={"size": HOST_ADB_SIZE, "sha256": HOST_ADB_SHA256}, owner=None)
        _prepare_snapshot(adb_payload, ADB_SNAPSHOT)
        d0_payload = _stable_read(
            D0_RUNTIME,
            "D0 runtime",
            maximum=2 * 1024 * 1024,
            expected=payloads["d0_runtime"],
        )
        raw_payload = _stable_read(
            RAW_CAPTURE,
            "raw capture",
            maximum=2 * 1024 * 1024,
            expected=payloads["raw_capture"],
        )
        primitive_payload = _stable_read(
            P296_PRIMITIVE,
            "P2.96 primitive",
            maximum=2 * 1024 * 1024,
            expected=payloads["p296_primitive"],
        )
        d0, raw = _load_runtime({"d0_runtime_bytes": d0_payload, "raw_capture_bytes": raw_payload})
        binding = {
            "manifest_receipt": static["manifest_receipt"],
            "approval_sha256": sha256_bytes(approval.encode("ascii")),
            "approval": approval,
        }
        transport = RawFirstTransport(d0, raw, profile, binding, RAW_ROOT, ADB_SNAPSHOT)
        raw_evidence = _raw_inventory(raw)
        result = perform_rotation(
            transport,
            binding,
            profile,
            RealClock(),
            raw,
            raw_evidence,
            primitive_payload,
            d0,
        )
        return result
    except BaseException as exc:
        try:
            _publish_stop(static, exc)
        except BaseException as stop_exc:
            raise D1Error(f"P3.20 D1 stopped; stop publication failed: {type(stop_exc).__name__}") from exc
        raise D1Error("P3.20 D1 stopped after consumed arm; replay is forbidden") from exc


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in ([], ["--self-test"]):
            value = self_test()
        elif len(arguments) == 3 and arguments[:2] == ["--live", "--approval"]:
            value = run_live(arguments[2])
        else:
            raise D1Error("accepted argv is empty/--self-test or exact --live --approval TOKEN")
    except (D1Error, OSError, KeyError, TypeError) as exc:
        print(f"P3.20 D1 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
