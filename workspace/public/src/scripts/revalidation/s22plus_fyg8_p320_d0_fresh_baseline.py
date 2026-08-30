#!/usr/bin/env python3
"""P3.20 exact-target D0 fresh-baseline producer.

The normal path is a host-only rehearsal.  A live invocation is read-only and
requires a fresh P3.20 D1 result, the exact D0 binding approval, and the
independent reviews recorded by those bindings.  It binds the returned D1
serial/topology/boot, captures ``/proc/last_kmsg`` through the durable raw
capture helper, and only then asks the P3.20 adapter to classify the bytes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
SCRIPT_DIR = SCRIPT.parent
ADAPTER = SCRIPT_DIR / "s22plus_fyg8_p320_stock_process_v2_adapter.py"
D1_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p320_d1_fresh_baseline.py"
D1_BINDING = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p320_d1_fresh_baseline.json"
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
BINDING_MANIFEST = ROOT / "workspace/public/src/device-action/bindings/s22plus_fyg8_p320_d0_fresh_baseline.json"

RUN_PARENT = ROOT / "workspace/private/runs/device-action-d0-p320-fresh-baseline"
RUN_DIR = RUN_PARENT / "p320-d0-fresh-baseline-1"
RUN_ARM = RUN_PARENT / "p320-d0-fresh-baseline-1.arm.json"
RUN_STOP = RUN_DIR / "stop.json"
RESULT_PATH = RUN_DIR / "result.json"
OBSERVER_PATH = RUN_DIR / "baseline-observer.bin"
RAW_ADB_DIR = RUN_DIR / "raw-adb"
ADB_SNAPSHOT = RUN_DIR / "adb-05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"

TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P320_RUN_ID = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
ORDINAL = "p320-d0-fresh-baseline-1"
BINDING_SCHEMA = "s22plus_fyg8_p320_d0_fresh_baseline_execution_binding_v1"
BINDING_ID = "s22plus-fyg8-p320-d0-fresh-baseline-v1"
AUTHORITY_PREFIX = "DEVICE-ACTION-D0-P320-FRESH-BASELINE-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P320_D0_FRESH_BASELINE_H0_CAPABILITY_V1"
D1_REVIEW_VERDICT = "PASS_GO_P320_D1_FRESH_BASELINE_H0_CAPABILITY_V1"
RESULT_SCHEMA = "s22plus_fyg8_p320_d0_fresh_baseline_result_v1"
RESULT_VERDICT = "PASS_P320_D0_FRESH_BASELINE_RAW_FIRST_V1"
STOP_SCHEMA = "s22plus_fyg8_p320_d0_fresh_baseline_stop_v1"
STOP_VERDICT = "STOP_P320_D0_FRESH_BASELINE_CONSUMED_NO_REPLAY"
HOST_ADB_SIZE = 716_968
HOST_ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
RAW_SIZE = 2_097_136
MAX_TEXT = 64 * 1024
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class D0Error(RuntimeError):
    """The P3.20 D0 action failed closed."""


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise D0Error("value is not canonical JSON") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.absolute())


def _receipt(path: Path, payload: bytes, *, mode: str | None = None) -> dict[str, Any]:
    value = {"path": _relative(path), "size": len(payload), "sha256": sha256_bytes(payload)}
    if mode is not None:
        value.update({"mode": mode, "nlink": 1})
    return value


def _stable_read(path: Path, label: str, *, maximum: int = 8 * 1024 * 1024,
                 expected: Mapping[str, Any] | None = None, mode: int | None = None,
                 owner: int | None = os.getuid()) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise D0Error(f"{label} path is indirect")
        descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise D0Error(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or (owner is not None and before.st_uid != owner)
            or before.st_nlink != 1
            or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
            or before.st_size > maximum
        ):
            raise D0Error(f"{label} identity differs")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, name) != getattr(after, name) for name in fields):
        raise D0Error(f"{label} changed while reading")
    payload = b"".join(chunks)
    if expected is not None and {"size": len(payload), "sha256": sha256_bytes(payload)} != {"size": expected.get("size"), "sha256": expected.get("sha256")}:
        raise D0Error(f"{label} bytes differ")
    return payload


def _strict(payload: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise D0Error(f"{label} contains duplicate key")
            value[key] = item
        return value
    try:
        value = json.loads(payload.decode("utf-8"), object_pairs_hook=unique,
                           parse_constant=lambda item: (_ for _ in ()).throw(D0Error(f"{label} contains non-finite JSON: {item}")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D0Error(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict) or canonical(value) != payload:
        raise D0Error(f"{label} is not a canonical object")
    return value


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(_typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def _source_receipts() -> dict[str, dict[str, Any]]:
    paths = {
        "d0_source": SCRIPT,
        "adapter": ADAPTER,
        "d1_source": D1_SOURCE,
        "d1_binding": D1_BINDING,
        "d0_runtime": D0_RUNTIME,
        "raw_capture": RAW_CAPTURE,
        "profile": PROFILE,
        "host_adb": HOST_ADB,
    }
    result = {}
    for name, path in paths.items():
        payload = _stable_read(path, name, maximum=HOST_ADB_SIZE if name == "host_adb" else 2 * 1024 * 1024, owner=None if name == "host_adb" else os.getuid())
        result[name] = _receipt(path, payload)
    return result


def _expected_binding(inputs: Mapping[str, Any], review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": BINDING_ID,
        "action": "one exact connected read-only P3.20 fresh-baseline acquisition",
        "authority_prefix": AUTHORITY_PREFIX,
        "target": TARGET,
        "ordinal": ORDINAL,
        "inputs": dict(inputs),
        "d1_dependency": {
            "binding": _relative(D1_BINDING),
            "binding_review_verdict": D1_REVIEW_VERDICT,
            "result": _relative(ROOT / "workspace/private/runs/device-action-d1-p320-fresh-baseline/p320-d1-fresh-baseline-1/result.json"),
            "result_schema": "s22plus_fyg8_p320_d1_fresh_baseline_v1_result",
            "result_verdict": "PASS_P320_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH",
            "result_replay_authorized": False,
        },
        "run": {
            "parent": _relative(RUN_PARENT),
            "directory": _relative(RUN_DIR),
            "arm": _relative(RUN_ARM),
            "stop": _relative(RUN_STOP),
            "result": _relative(RESULT_PATH),
            "observer": _relative(OBSERVER_PATH),
            "raw_adb": _relative(RAW_ADB_DIR),
            "adb_snapshot": _relative(ADB_SNAPSHOT),
        },
        "bounds": {
            "observer_source": "/proc/last_kmsg",
            "observer_bytes": RAW_SIZE,
            "observer_read_count": 1,
            "observer_timeout_sec": 180,
            "read_timeout_sec": 180,
            "raw_text_maximum": MAX_TEXT,
        },
        "safety": {
            "device_writes": False,
            "reboot": False,
            "partition_transfer": False,
            "download_transition": False,
            "odin": False,
            "f1_authorized": False,
            "replay_authorized": False,
            "other_targets_commanded": False,
        },
        "independent_review": dict(review),
    }


def _validated_static_inputs() -> dict[str, Any]:
    payloads = _source_receipts()
    binding_payload = _stable_read(BINDING_MANIFEST, "P3.20 D0 binding", maximum=256 * 1024)
    binding = _strict(binding_payload, "P3.20 D0 binding")
    review = binding.get("independent_review")
    if review not in ({"status": "review-pending", "verdict": None}, {"status": "pass-go", "verdict": REVIEW_VERDICT}):
        raise D0Error("P3.20 D0 review state differs")
    if not _typed_equal(binding, _expected_binding(payloads, review)):
        raise D0Error("P3.20 D0 binding does not match exact inputs")
    d1_binding_payload = _stable_read(
        D1_BINDING, "P3.20 D1 binding", maximum=256 * 1024
    )
    d1 = _strict(d1_binding_payload, "P3.20 D1 binding")
    if d1.get("schema") != "s22plus_fyg8_p320_d1_fresh_baseline_execution_binding_v1" or d1.get("binding_id") != "s22plus-fyg8-p320-d1-fresh-baseline-v1" or d1.get("target", {}).get("model") != TARGET["model"] or d1.get("target", {}).get("codename") != TARGET["codename"] or d1.get("target", {}).get("build") != TARGET["build"]:
        raise D0Error("P3.20 D1 predecessor identity differs")
    return {
        "manifest": binding,
        "manifest_payload": binding_payload,
        "manifest_receipt": _receipt(BINDING_MANIFEST, binding_payload),
        "authority": AUTHORITY_PREFIX + sha256_bytes(binding_payload),
        "approval_sha256": sha256_bytes((AUTHORITY_PREFIX + sha256_bytes(binding_payload)).encode("ascii")),
        "payloads": payloads,
        "d1_binding": d1,
    }


def _load_adapter(payload: bytes) -> Any:
    spec = importlib.util.spec_from_file_location("p320_stock_adapter_bound", ADAPTER)
    if spec is None or spec.loader is None:
        raise D0Error("P3.20 adapter import failed")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        exec(compile(payload, str(ADAPTER), "exec"), module.__dict__)
    except BaseException as exc:
        raise D0Error(f"P3.20 adapter failed to load: {type(exc).__name__}") from exc
    finally:
        sys.path.pop(0)
    return module


def _load_runtime(d0_payload: bytes, raw_payload: bytes) -> tuple[Any, Any]:
    raw = types.ModuleType("device_action_raw_capture_v1")
    raw.__file__ = str(RAW_CAPTURE)
    f1 = types.ModuleType("device_action_f1_v2")
    f1.json_sha256 = lambda value: sha256_bytes(canonical(value).rstrip(b"\n"))
    d0 = types.ModuleType("device_action_d0_v2")
    d0.__file__ = str(D0_RUNTIME)
    old = {name: sys.modules.get(name) for name in ("device_action_raw_capture_v1", "device_action_f1_v2", "device_action_d0_v2")}
    try:
        sys.modules["device_action_raw_capture_v1"] = raw
        exec(compile(raw_payload, str(RAW_CAPTURE), "exec"), raw.__dict__)
        sys.modules["device_action_f1_v2"] = f1
        sys.modules["device_action_d0_v2"] = d0
        exec(compile(d0_payload, str(D0_RUNTIME), "exec"), d0.__dict__)
    except BaseException as exc:
        raise D0Error(f"bound D0 runtime failed to load: {type(exc).__name__}") from exc
    finally:
        for name, value in old.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    return d0, raw


def _durable_create(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical(dict(value))
    parent = path.parent.absolute()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.resolve(strict=True) != parent:
        raise D0Error("journal parent is indirect")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0), 0o400)
    except FileExistsError as exc:
        raise D0Error(f"journal already exists: {path.name}; replay is forbidden") from exc
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D0Error("journal write made no progress")
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
        raise D0Error("host ADB snapshot source differs")
    parent = path.parent.absolute()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.resolve(strict=True) != parent:
        raise D0Error("ADB snapshot parent is indirect")
    if path.exists() or path.is_symlink():
        current = _stable_read(path, "ADB snapshot", maximum=HOST_ADB_SIZE, mode=0o500)
        if current != payload:
            raise D0Error("ADB snapshot already exists with different bytes")
        return
    descriptor, temporary_name = tempfile.mkstemp(prefix=".adb-", dir=parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o500)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D0Error("ADB snapshot write made no progress")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise D0Error("ADB snapshot publication raced; replay is forbidden") from exc
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


def _validate_d1_value(
    value: Mapping[str, Any],
    static: Mapping[str, Any],
    d1_binding_payload: bytes,
) -> None:
    """Require the exact consumed D1 result before any D0 device read."""
    if not isinstance(value, dict):
        raise D0Error("P3.20 D1 result is not an object")
    expected_manifest = _receipt(D1_BINDING, d1_binding_payload)
    if (
        value.get("schema") != "s22plus_fyg8_p320_d1_fresh_baseline_v1_result"
        or value.get("verdict") != "PASS_P320_D1_FRESH_BASELINE_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
        or value.get("execution_manifest") != expected_manifest
        or value.get("ordinal") != static["d1_binding"].get("ordinal")
        or value.get("run_id") != P320_RUN_ID
        or value.get("run_directory")
        != static["manifest"]["d1_dependency"]["result"].rsplit("/", 1)[0]
        or value.get("reboot_count") != 1
    ):
        raise D0Error("P3.20 D1 result identity differs")
    required_flags = {
        "device_contact": True,
        "live_authorized": True,
        "device_writes": False,
        "candidate_transfer": False,
        "partition_transfer": False,
        "odin_invoked": False,
        "download_transition_requested": False,
        "f1_authorized": False,
        "other_targets_commanded": False,
    }
    if any(type(value.get(key)) is not bool or value.get(key) is not expected for key, expected in required_flags.items()):
        raise D0Error("P3.20 D1 result safety flags differ")
    selection = value.get("selection")
    if not isinstance(selection, dict) or set(selection) != {
        "inventory_count",
        "inventory_models",
        "inventory_sha256",
        "selected_serial_sha256",
        "selected_topology_sha256",
        "other_targets_commanded",
    }:
        raise D0Error("P3.20 D1 result selection shape differs")
    if (
        type(selection["inventory_count"]) is not int
        or selection["inventory_count"] < 1
        or not isinstance(selection["inventory_models"], list)
        or "SM_S906N" not in selection["inventory_models"]
        or selection["other_targets_commanded"] is not False
        or not isinstance(selection["selected_serial_sha256"], str)
        or not isinstance(selection["selected_topology_sha256"], str)
        or HEX64.fullmatch(selection["selected_serial_sha256"]) is None
        or HEX64.fullmatch(selection["selected_topology_sha256"]) is None
        or selection["selected_serial_sha256"]
        != static["d1_binding"]["target"].get("adb_serial_sha256")
    ):
        raise D0Error("P3.20 D1 result target selection differs")
    before = value.get("before")
    after = value.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise D0Error("P3.20 D1 result health shape differs")
    for health in (before, after):
        boot_id = health.get("boot_id_sha256")
        if not isinstance(boot_id, str) or HEX64.fullmatch(boot_id) is None:
            raise D0Error("P3.20 D1 result boot identity differs")
    if before["boot_id_sha256"] == after["boot_id_sha256"]:
        raise D0Error("P3.20 D1 result did not prove a changed boot")


def _load_d1_result(static: Mapping[str, Any]) -> dict[str, Any]:
    path = ROOT / "workspace/private/runs/device-action-d1-p320-fresh-baseline/p320-d1-fresh-baseline-1/result.json"
    payload = _stable_read(path, "P3.20 D1 result", maximum=512 * 1024, mode=0o400)
    value = _strict(payload, "P3.20 D1 result")
    d1_binding_payload = _stable_read(
        D1_BINDING,
        "P3.20 D1 binding",
        maximum=256 * 1024,
        expected=static["payloads"]["d1_binding"],
    )
    _validate_d1_value(value, static, d1_binding_payload)
    return {"value": value, "receipt": _receipt(path, payload), "path": path}


def _health(profile: Mapping[str, Any], properties: Mapping[str, str], root_health: Mapping[str, str], usb: Mapping[str, Any], expected_boot_id: str) -> dict[str, Any]:
    expected = profile["final_health"]
    if properties.get("model") != TARGET["model"] or properties.get("device") != TARGET["codename"] or properties.get("incremental") != TARGET["build"] or properties.get("boot_completed") != "1" or properties.get("bootanim") != "stopped" or properties.get("verified_boot_state") != expected["verified_boot_state"] or not root_health.get("root", "").startswith("uid=0(root)") or root_health.get("boot") != expected["boot_sha256"] or usb.get("download_endpoint_count") != 0:
        raise D0Error("D0 Android health differs")
    for name, digest in expected["supporting_partition_sha256"].items():
        if root_health.get(name) != digest:
            raise D0Error(f"D0 supporting partition differs: {name}")
    boot_id = properties.get("boot_id")
    if not isinstance(boot_id, str) or not boot_id or sha256_bytes(boot_id.encode()) != expected_boot_id:
        raise D0Error("D0 returned boot identity differs from D1")
    return {
        "android_boot_completed": True,
        "boot_animation_stopped": True,
        "boot_id_sha256": expected_boot_id,
        "boot_sha256": root_health["boot"],
        "kernel_release": properties.get("kernel_release", ""),
        "odin_endpoint_absent": True,
        "root_verified": True,
        "supporting_partition_sha256": {name: root_health[name] for name in ("dtbo", "recovery", "vendor_boot")},
        "verified_boot_state": properties["verified_boot_state"],
    }


def _raw_inventory(raw: Any) -> dict[str, Any]:
    try:
        directory = RAW_ADB_DIR.lstat()
    except FileNotFoundError:
        return {"directory_present": False, "complete": False, "handles": [], "children": []}
    if not stat.S_ISDIR(directory.st_mode) or stat.S_IMODE(directory.st_mode) != 0o700 or directory.st_uid != os.getuid() or RAW_ADB_DIR.resolve(strict=True) != RAW_ADB_DIR.absolute():
        raise D0Error("raw ADB directory identity differs")
    children = sorted(RAW_ADB_DIR.iterdir(), key=lambda item: item.name)
    handles = []
    for child in children:
        if not child.name.endswith(".capture.json"):
            continue
        handle = raw.load_handle(child)
        handles.append({"name": handle.name, "returncode": handle.returncode, "timed_out": handle.timed_out, "output_exceeded": handle.output_exceeded, "producer_error_type": handle.producer_error_type, "receipt": child.name})
    return {
        "directory_present": True,
        "complete": bool(handles) and all(item["returncode"] == 0 and item["timed_out"] is False and item["output_exceeded"] is False and item["producer_error_type"] is None for item in handles),
        "children": [item.name for item in children],
        "handles": handles,
    }


def _preflight() -> None:
    for path in (RUN_PARENT, RUN_ARM, RUN_DIR):
        if path.exists() or path.is_symlink():
            raise D0Error(f"fixed P3.20 D0 namespace already exists: {path.name}; replay is forbidden")


def _classify_clean_baseline(adapter: Any, payload: bytes) -> dict[str, Any]:
    """Keep the run-id guard at the D0 seam even for zero-record baselines."""
    bound = getattr(adapter, "P320_STOCK_RUN_ID", None)
    if not isinstance(bound, bytes) or bound.hex() != P320_RUN_ID:
        raise D0Error("P3.20 adapter run ID is not bound")
    result = adapter.classify_clean_baseline(payload, expected_run_id=bound)
    if result.get("classification") != "ZERO_AMBIGUOUS" or result.get("baseline_clean") is not True:
        raise D0Error("P3.20 clean baseline classification differs")
    return result


def run_live(approval: str) -> dict[str, Any]:
    static = _validated_static_inputs()
    if static["manifest"]["independent_review"] != {"status": "pass-go", "verdict": REVIEW_VERDICT}:
        raise D0Error("P3.20 D0 independent review is absent")
    if static["d1_binding"].get("independent_review") != {"status": "pass-go", "verdict": D1_REVIEW_VERDICT}:
        raise D0Error("P3.20 D1 independent review is absent")
    if approval != static["authority"]:
        raise D0Error("exact P3.20 D0 approval is absent")
    d1 = _load_d1_result(static)
    _preflight()
    _durable_create(RUN_ARM, {
        "schema": f"{BINDING_SCHEMA}_arm",
        "execution_manifest": static["manifest_receipt"],
        "approval_sha256": static["approval_sha256"],
        "ordinal": ORDINAL,
        "d1_result_receipt": d1["receipt"],
        "consumed": True,
        "device_contact_before_arm": False,
        "replay_authorized": False,
    })
    try:
        profile = _strict(_stable_read(PROFILE, "S22+ profile"), "S22+ profile")
        adb_payload = _stable_read(HOST_ADB, "host ADB", maximum=HOST_ADB_SIZE, expected={"size": HOST_ADB_SIZE, "sha256": HOST_ADB_SHA256}, owner=None)
        # The host ADB snapshot is intentionally inside the run namespace;
        # create that namespace once after the consumed arm, before publishing
        # the no-replace snapshot into it.
        RUN_DIR.mkdir(mode=0o700, parents=False, exist_ok=False)
        _prepare_snapshot(adb_payload, ADB_SNAPSHOT)
        d0_payload = _stable_read(
            D0_RUNTIME,
            "D0 runtime",
            maximum=2 * 1024 * 1024,
            expected=static["payloads"]["d0_runtime"],
        )
        raw_payload = _stable_read(
            RAW_CAPTURE,
            "raw capture",
            maximum=2 * 1024 * 1024,
            expected=static["payloads"]["raw_capture"],
        )
        adapter_payload = _stable_read(
            ADAPTER,
            "P3.20 adapter",
            maximum=2 * 1024 * 1024,
            expected=static["payloads"]["adapter"],
        )
        d0, raw = _load_runtime(d0_payload, raw_payload)
        adapter = _load_adapter(adapter_payload)
        client = d0.AdbReadOnlyClient(ADB_SNAPSHOT, expected_model=TARGET["model"], expected_device=TARGET["codename"])
        client.bind_raw_capture_dir(RUN_DIR)
        serial = client.one_serial()
        topology = client.topology(serial)
        if sha256_bytes(serial.encode()) != d1["value"]["selection"]["selected_serial_sha256"] or sha256_bytes(topology.encode()) != d1["value"]["selection"]["selected_topology_sha256"]:
            raise D0Error("D0 serial/topology differs from D1")
        properties = client.properties(serial)
        root_health = client.root_health(serial)
        usb = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile["target"]["download"])
        initial_health = _health(profile, properties, root_health, usb, d1["value"]["after"]["boot_id_sha256"])
        capture = client.capture(serial, "/proc/last_kmsg", OBSERVER_PATH)
        observer_handle = capture.handle
        payload = raw.read_stdout(observer_handle, maximum=RAW_SIZE)
        if len(payload) != RAW_SIZE:
            raise D0Error("P3.20 observer size differs")
        # The raw handle and both streams are re-opened and verified before
        # the P3.20 parser sees the bytes.
        observer_result = _classify_clean_baseline(adapter, payload)
        final_serial = client.one_serial()
        final_topology = client.topology(final_serial)
        final_properties = client.properties(final_serial)
        final_root = client.root_health(final_serial)
        final_usb = d0.usb_snapshot(d0.DEFAULT_USB_ROOT, profile["target"]["download"])
        final_health = _health(profile, final_properties, final_root, final_usb, d1["value"]["after"]["boot_id_sha256"])
        if final_serial != serial or final_topology != topology:
            raise D0Error("D0 final target/topology changed")
        observer_receipt_payload = _stable_read(observer_handle.receipt_path, "observer raw receipt", maximum=64 * 1024, mode=0o400)
        result = {
            "schema": RESULT_SCHEMA,
            "version": "device-action-d0-p320-v1",
            "verdict": RESULT_VERDICT,
            "execution_manifest": static["manifest_receipt"],
            "approval_sha256": static["approval_sha256"],
            "ordinal": ORDINAL,
            "run_directory": _relative(RUN_DIR),
            "d1_result": d1["receipt"],
            "target_evidence": {"model": TARGET["model"], "device": TARGET["codename"], "build": TARGET["build"], "adb_serial_sha256": sha256_bytes(serial.encode()), "usb_topology_sha256": sha256_bytes(topology.encode())},
            "initial_health": initial_health,
            "health": final_health,
            "observer": {"source": "/proc/last_kmsg", "path": _relative(OBSERVER_PATH), "bytes": len(payload), "sha256": sha256_bytes(payload), "raw_receipt": _receipt(observer_handle.receipt_path, observer_receipt_payload, mode="0400"), "raw_first": True, "parser_started_after_raw_publish": True, "read_to_eof": True, "stderr_bytes": 0},
            "classification": observer_result,
            "raw_adb": _raw_inventory(raw),
            "host_tool": _receipt(ADB_SNAPSHOT, _stable_read(ADB_SNAPSHOT, "ADB snapshot", maximum=HOST_ADB_SIZE, mode=0o500), mode="0500"),
            "device_contact": True,
            "device_writes": False,
            "reboot_requested": False,
            "download_transition_requested": False,
            "odin_invoked": False,
            "partition_transfer": False,
            "f1_authorized": False,
            "live_authorized": True,
            "candidate_success": False,
            "causal_result_allowed": False,
            "other_targets_commanded": False,
        }
        _durable_create(RESULT_PATH, result)
        return result
    except BaseException as exc:
        if RUN_DIR.exists() and not RUN_STOP.exists():
            _durable_create(RUN_STOP, {
                "schema": STOP_SCHEMA,
                "verdict": STOP_VERDICT,
                "execution_manifest": static["manifest_receipt"],
                "approval_sha256": static["approval_sha256"],
                "ordinal": ORDINAL,
                "run_directory": _relative(RUN_DIR),
                "error_type": type(exc).__name__,
                "error": str(exc)[:512],
                "replay_authorized": False,
                "result_reusable": False,
                "device_writes": False,
                "reboot_requested": False,
                "partition_transfer": False,
            })
        raise D0Error("P3.20 D0 stopped after consumed arm; replay is forbidden") from exc


def self_test() -> dict[str, Any]:
    static = _validated_static_inputs()
    adapter = _load_adapter(static["payloads"]["adapter_bytes"] if "adapter_bytes" in static["payloads"] else _stable_read(ADAPTER, "P3.20 adapter", maximum=2 * 1024 * 1024))
    clean = _classify_clean_baseline(adapter, bytes(RAW_SIZE))
    rejected = False
    try:
        old_adapter = types.SimpleNamespace(
            P320_STOCK_RUN_ID=bytes.fromhex("b9cc424d0d184f5accbce94a844e817d"),
            classify_clean_baseline=adapter.classify_clean_baseline,
        )
        _classify_clean_baseline(old_adapter, bytes(RAW_SIZE))
    except Exception:
        rejected = True
    if clean.get("classification") != "ZERO_AMBIGUOUS" or clean.get("baseline_clean") is not True or not rejected:
        raise D0Error("P3.20 clean-baseline fixture differs")
    return {
        "schema": "s22plus_fyg8_p320_d0_fresh_baseline_fixture_h0",
        "verdict": "PASS_P320_D0_FRESH_BASELINE_FIXTURE_H0",
        "ordinal": ORDINAL,
        "run_id": P320_RUN_ID,
        "raw_first": True,
        "clean_baseline": True,
        "p319_run_id_rejected": True,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in ([], ["--self-test"]):
            value = self_test()
        elif len(arguments) == 3 and arguments[:2] == ["--live", "--approval"]:
            value = run_live(arguments[2])
        else:
            raise D0Error("accepted argv is empty/--self-test or exact --live --approval TOKEN")
    except (D0Error, OSError, KeyError, TypeError) as exc:
        print(f"P3.20 D0 blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
