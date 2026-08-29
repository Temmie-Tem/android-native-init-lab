#!/usr/bin/env python3
"""Bounded P3.19 D0 V3 fresh-baseline producer.

The default mode is a zero-device H0 rehearsal.  The live branch is fixed to
one reviewed V3 binding and one approval string; callers cannot select a target,
path, command, timeout, or output.  A durable consumed intent precedes any
transport construction.  Every device read is read-only and the sole large
observer acquisition is published through the common raw-first handle before
the P3.19 classifier receives bytes.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import importlib.abc
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
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d0_fresh_baseline_v3.json"
)
REDUCER = SCRIPT_DIR / "s22plus_fyg8_p319_fresh_baseline_capability_v3.py"
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
ADAPTER = SCRIPT_DIR / "s22plus_fyg8_p319_stock_process_v2_adapter.py"
D1_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p319_d1_fresh_baseline_v3.py"
D1_BINDING = ROOT / (
    "workspace/public/src/device-action/bindings/"
    "s22plus_fyg8_p319_d1_fresh_baseline_v3.json"
)
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
INTENT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "candidate-qualification-v1-20260821-10/intent.json"
)
QUALIFICATION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "candidate-qualification-v1-20260821-10/qualification.json"
)
HOST_ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
HOST_ADB_SIZE = 716_968
HOST_ADB_SHA256 = (
    "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)
RUN_PARENT = ROOT / "workspace/private/runs/device-action-d0-p319-fresh-baseline-v3"
RUN_DIR = RUN_PARENT / "d0-p319-fresh-baseline-3"
RUN_ARM = Path(str(RUN_DIR) + ".arm.json")
RUN_STOP = Path(str(RUN_DIR) + ".stop.json")
RESULT_PATH = RUN_DIR / "result.json"
OBSERVER_PATH = RUN_DIR / "baseline-observer.bin"
RAW_RECEIPT = RUN_DIR / "baseline-observer.capture.json"
RAW_ADB_DIR = RUN_DIR / "raw-adb"
ADB_SNAPSHOT = RUN_DIR / ("adb-" + HOST_ADB_SHA256)
D1_RUN_PARENT = ROOT / "workspace/private/runs/device-action-d1-p319-fresh-baseline-v3"
D1_RUN_DIR = D1_RUN_PARENT / "p319-fresh-baseline-3"
D1_RUN_ARM = D1_RUN_PARENT / "p319-fresh-baseline-3.arm.json"
D1_RESULT = D1_RUN_DIR / "result.json"
D1_START = D1_RUN_DIR / "start.json"
D1_RAW_ROOT = D1_RUN_PARENT / "p319-fresh-baseline-3-raw"
D1_RAW_ADB_DIR = D1_RAW_ROOT / "raw-adb"
USB_ROOT = Path("/sys/bus/usb/devices")

SCHEMA = "s22plus_fyg8_p319_d0_fresh_baseline_v3_result"
VERSION = "device-action-d0-p319-v3"
VERDICT = "PASS_P319_D0_FRESH_BASELINE_RAW_V3"
STOP_SCHEMA = "s22plus_fyg8_p319_d0_fresh_baseline_stop_v3"
STOP_VERDICT = "STOP_P319_D0_FRESH_BASELINE_V3_CONSUMED_NO_REPLAY"
RESULT_REQUIRED_KEYS = {
    "schema", "version", "mode", "baseline_design_id", "run_directory",
    "runtime", "binding", "journal", "target_evidence", "initial_health",
    "health", "observer", "raw_adb", "usb", "host_tool", "verdict",
    "device_contact", "device_writes", "reboot_requested",
    "download_transition_requested", "odin_invoked", "partition_transfer",
    "f1_authorized", "live_authorized", "candidate_marker_family_absent",
    "marker_residual",
}
BINDING_SCHEMA = "s22plus_fyg8_p319_d0_fresh_baseline_execution_binding_v3"
BINDING_ID = "s22plus-fyg8-p319-d0-fresh-baseline-v3"
AUTHORITY_PREFIX = "DEVICE-ACTION-D0-P319-FRESH-BASELINE-V3-APPROVE:"
REVIEW_VERDICT = "PASS_GO_P319_D0_FRESH_BASELINE_V3_H0_CAPABILITY_V1"
D1_BINDING_PREDECESSOR_SHA256 = (
    "65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9"
)
RAW_SIZE = 2_097_136
MAX_TEXT = 64 * 1024
SUCCESS_RAW_ADB_HANDLE_COUNT = 9
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
HEX64 = re.compile(r"[0-9a-f]{64}\Z")

# Complete local import closure reached while importing the P3.19 adapter.
# The fixed list prevents a new local import from escaping the source binding.
ADAPTER_MODULES = (
    "s22plus_boot_verify",
    "s22plus_fyg8_p232_e1_latest_stage_design",
    "s22plus_fyg8_p233_e1_decoder",
    "s22plus_fyg8_p233_e1_static_checker",
    "s22plus_fyg8_p241_dtbo_role_contract",
    "s22plus_fyg8_p241_e2_static_checker",
    "s22plus_fyg8_p243_rpmh_dependency_audit",
    "s22plus_fyg8_p244_e2_provider_sources",
    "s22plus_fyg8_p248_contract_spec",
    "s22plus_fyg8_p252_contract_spec",
    "s22plus_fyg8_p257_contract_spec",
    "s22plus_fyg8_p258_contract_spec",
    "s22plus_fyg8_p260_contract_spec",
    "s22plus_fyg8_p280_contract_spec",
    "s22plus_fyg8_p282_contract_spec",
    "s22plus_fyg8_p284_contract_spec",
    "s22plus_fyg8_p286_contract_spec",
    "s22plus_fyg8_p288_contract_spec",
    "s22plus_fyg8_p288_latest_stage_model",
    "s22plus_fyg8_p290_contract_spec",
    "s22plus_fyg8_p290_latest_stage_model",
    "s22plus_fyg8_p292_checkpoint_sot",
    "s22plus_fyg8_p292_repair_spec",
    "s22plus_fyg8_p294_telemetry_spec",
    "s22plus_fyg8_p296_telemetry_spec",
    "s22plus_fyg8_p298_telemetry_spec",
    "s22plus_fyg8_p300_telemetry_spec",
    "s22plus_fyg8_p301_telemetry_spec",
    "s22plus_fyg8_p303_telemetry_spec",
    "s22plus_fyg8_p307_telemetry_spec",
    "s22plus_fyg8_p308_telemetry_spec",
    "s22plus_fyg8_p310_carrier_model",
    "s22plus_fyg8_p319_result_contract_arming",
    "s22plus_fyg8_p319_stock_process_v2_adapter",
    "s22plus_fyg8_r4w1b_candidate_static_checker",
    "s22plus_fyg8_r4w1e_checkpoint_contract",
    "s22plus_fyg8_r4w1e_e1_host_contract",
    "s22plus_fyg8_retained_snapshot_model",
    "s22plus_o2_module_plan",
)
ADAPTER_ROOT = "s22plus_fyg8_p319_stock_process_v2_adapter"


class D0FreshBaselineError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise D0FreshBaselineError("value is not canonical JSON") from exc


def _identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _relative(path: Path) -> str:
    try:
        return path.absolute().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.absolute())


def _stable_read(
    path: Path, label: str, *, expected: Mapping[str, Any] | None = None,
    mode: int | None = None, maximum: int = 8 * 1024 * 1024,
) -> bytes:
    direct = path.absolute()
    try:
        if direct != path or direct.resolve(strict=True) != direct:
            raise D0FreshBaselineError(f"{label} path is indirect")
        flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(direct, flags)
    except OSError as exc:
        raise D0FreshBaselineError(f"{label} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise D0FreshBaselineError(f"{label} is not a single-link regular file")
        if mode is not None and stat.S_IMODE(before.st_mode) != mode:
            raise D0FreshBaselineError(f"{label} mode differs")
        if before.st_size > maximum:
            raise D0FreshBaselineError(f"{label} exceeds its bounded read")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    fields = (
        "st_dev", "st_ino", "st_mode", "st_nlink", "st_size",
        "st_mtime_ns", "st_ctime_ns",
    )
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise D0FreshBaselineError(f"{label} changed while open")
    payload = b"".join(chunks)
    if expected is not None and (
        type(expected.get("size")) is not int
        or expected.get("size") != len(payload)
        or expected.get("sha256") != hashlib.sha256(payload).hexdigest()
    ):
        raise D0FreshBaselineError(f"{label} identity differs")
    return payload


def _source_receipt(path: Path, payload: bytes) -> dict[str, Any]:
    return {"path": _relative(path), **_identity(payload)}


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise D0FreshBaselineError("duplicate JSON key")
        value[key] = item
    return value


def _strict_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_unique,
            parse_constant=lambda item: (_ for _ in ()).throw(
                D0FreshBaselineError(f"{label} contains non-finite JSON: {item}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise D0FreshBaselineError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise D0FreshBaselineError(f"{label} is not an object")
    return value


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _typed_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise D0FreshBaselineError(f"{label} is not a lowercase SHA-256")
    return value


def _profile_value(payload: bytes) -> dict[str, Any]:
    value = _strict_object(payload, "S22+ target profile")
    target = value.get("target")
    if (
        value.get("schema") != "device_action_target_profile_v2"
        or not isinstance(target, dict)
        or {
            "model": target.get("model"),
            "codename": target.get("device"),
            "build": target.get("firmware_incremental"),
        }
        != TARGET
    ):
        raise D0FreshBaselineError("S22+ target profile identity differs")
    return value


def _candidate_identity(intent_payload: bytes, qualification_payload: bytes) -> dict[str, Any]:
    intent = _strict_object(intent_payload, "current P3.19 intent")
    qualification = _strict_object(
        qualification_payload, "current P3.19 qualification"
    )
    run_id = intent.get("run_id")
    source_keys = intent.get("source_keys")
    plan = intent.get("module_plan")
    if (
        intent.get("schema") != "s22plus_fyg8_p319_candidate_intent_v1"
        or qualification.get("schema")
        != "s22plus_fyg8_p319_candidate_qualification_v1"
        or intent.get("target") != TARGET
        or qualification.get("target") != TARGET
        or not isinstance(run_id, str)
        or re.fullmatch(r"[0-9a-f]{32}", run_id) is None
        or not isinstance(source_keys, dict)
        or len(source_keys) != 437
        or not isinstance(plan, dict)
        or plan != {
            "count": 73, "eud_index": 38,
            "overlay_delta": ["s22plus_dwc3_event_latch.ko"],
        }
        or qualification.get("intent", {}).get("source_keys") != source_keys
        or qualification.get("fresh_live_baseline", {}).get("satisfied") is not False
    ):
        raise D0FreshBaselineError("current P3.19 candidate identity differs")
    source_digest = hashlib.sha256(
        json.dumps(
            source_keys, sort_keys=True, separators=(",", ":"),
            ensure_ascii=True, allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    if source_digest != "f41bfd2d1a4cf62aa62500a636a22e2035f3d56f9151e806e80da86f6c9cdded":
        raise D0FreshBaselineError("current source-key closure differs")
    fixed = intent.get("fixed_image")
    if not isinstance(fixed, dict) or fixed != qualification.get("fixed_image"):
        raise D0FreshBaselineError("current fixed Image identity differs")
    return {
        "target": TARGET,
        "run_id": run_id,
        "fixed_image": dict(fixed),
        "intent": _source_receipt(INTENT, intent_payload),
        "qualification": _source_receipt(QUALIFICATION, qualification_payload),
        "closure": {
            "source_keys": {"count": 437, "sha256": source_digest},
            "module_plan": dict(plan),
        },
        "marker_tokens": [
            "s22_checkpoint", "native-init", run_id, run_id.encode().hex()
        ],
    }


def _baseline_design(
    reducer_payload: bytes, d1_payload: bytes, d0_payload: bytes,
    profile_payload: bytes,
) -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p319_fresh_baseline_design_v3",
        "design_id": "s22plus-fyg8-p319-fresh-baseline-design-v3",
        "target": TARGET,
        "profile": _source_receipt(PROFILE, profile_payload),
        "reducer": _source_receipt(REDUCER, reducer_payload),
        "d1_source": _source_receipt(D1_SOURCE, d1_payload),
        "d0_runtime": _source_receipt(D0_RUNTIME, d0_payload),
    }


def _adapter_payloads() -> dict[str, bytes]:
    return {
        name: _stable_read(
            SCRIPT_DIR / f"{name}.py", f"P3.19 adapter source {name}",
            maximum=2 * 1024 * 1024,
        )
        for name in ADAPTER_MODULES
    }


def _audit_adapter_imports(payloads: Mapping[str, bytes]) -> None:
    names = set(payloads)
    for name, payload in payloads.items():
        try:
            tree = ast.parse(payload.decode("utf-8"), filename=f"{name}.py")
        except (UnicodeDecodeError, SyntaxError) as exc:
            raise D0FreshBaselineError(f"adapter source cannot parse: {name}") from exc
        local: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                local.update(alias.name for alias in node.names if (SCRIPT_DIR / f"{alias.name}.py").exists())
            elif isinstance(node, ast.ImportFrom) and node.module and (SCRIPT_DIR / f"{node.module}.py").exists():
                local.add(node.module)
        if not local <= names:
            raise D0FreshBaselineError(
                f"adapter local import closure differs: {name}: {sorted(local - names)}"
            )


def _expected_manifest(
    *, script_payload: bytes, reducer_payload: bytes, d0_payload: bytes,
    raw_payload: bytes, adapter_payloads: Mapping[str, bytes],
    d1_payload: bytes, d1_binding_payload: bytes, profile_payload: bytes,
    adb_payload: bytes, candidate: Mapping[str, Any],
    design: Mapping[str, Any], review: Mapping[str, Any],
) -> dict[str, Any]:
    adapter_sources = {
        name: _source_receipt(SCRIPT_DIR / f"{name}.py", payload)
        for name, payload in sorted(adapter_payloads.items())
    }
    return {
        "schema": BINDING_SCHEMA,
        "binding_id": BINDING_ID,
        "action": "one exact connected read-only P3.19 fresh-baseline acquisition",
        "authority_prefix": AUTHORITY_PREFIX,
        "target": TARGET,
        "target_profile": _source_receipt(PROFILE, profile_payload),
        "current_candidate": dict(candidate),
        "baseline_design": dict(design),
        "inputs": {
            "d0_source": _source_receipt(SCRIPT, script_payload),
            "fresh_baseline_reducer": _source_receipt(REDUCER, reducer_payload),
            "common_d0_runtime": _source_receipt(D0_RUNTIME, d0_payload),
            "raw_capture": _source_receipt(RAW_CAPTURE, raw_payload),
            "adapter_sources": adapter_sources,
            "d1_source": _source_receipt(D1_SOURCE, d1_payload),
            "d1_execution_binding": _source_receipt(
                D1_BINDING, d1_binding_payload
            ),
            "host_adb": _source_receipt(HOST_ADB, adb_payload),
        },
        "d1_dependency": {
            "result_path": _relative(D1_RESULT),
            "arm_path": _relative(D1_RUN_ARM),
            "start_path": _relative(D1_START),
            "raw_root": _relative(D1_RAW_ROOT),
            "raw_adb": _relative(D1_RAW_ADB_DIR),
            "result_schema": "s22plus_fyg8_p319_d1_fresh_baseline_v3_result",
            "binding_review": {
                "status": "pass-go",
                "verdict": (
                    "PASS_GO_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_"
                    "H0_CAPABILITY_V1"
                ),
            },
            "canonical_validator": "_post_validate",
            "consumed_predecessor_binding_sha256": D1_BINDING_PREDECESSOR_SHA256,
        },
        "host_adb_execution_snapshot": {
            "path": _relative(ADB_SNAPSHOT),
            "size": HOST_ADB_SIZE,
            "sha256": HOST_ADB_SHA256,
            "mode": "0500",
            "publication": "file-fsync-link-no-replace-directory-fsync",
        },
        "run_directory": {
            "path": _relative(RUN_DIR),
            "publication": "directory-no-replace-after-consumed-arm",
        },
        "run_approval_arm": {
            "path": _relative(RUN_ARM),
            "publication": "file-no-replace-fsync-then-directory-fsync",
        },
        "run_stop": {
            "path": _relative(RUN_STOP),
            "publication": "file-no-replace-fsync-then-directory-fsync",
        },
        "limits": {
            "observer_source": "/proc/last_kmsg",
            "observer_bytes": RAW_SIZE,
            "observer_read_count": 1,
            "observer_timeout_sec": 180,
            "stderr_bytes": 0,
        },
        "safety": {
            "device_writes": False,
            "reboot": False,
            "download_transition": False,
            "odin": False,
            "partition_transfer": False,
            "module_action": False,
            "property_or_service_action": False,
            "f1_authorized": False,
            "replay_authorized": False,
        },
        "independent_review": dict(review),
        "failure_rule": "consumed typed stop without retry or replay",
    }


def _compile_module(name: str, path: Path, payload: bytes) -> Any:
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    if spec is None:
        raise D0FreshBaselineError(f"cannot construct pinned module: {name}")
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    module.__package__ = None
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(compile(payload, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException as exc:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise D0FreshBaselineError(f"pinned module failed to load: {name}: {type(exc).__name__}") from exc
    if prior is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = prior
    return module


def _load_reducer(payload: bytes) -> Any:
    module = _compile_module("p319_d0_bound_reducer", REDUCER, payload)
    if _stable_read(REDUCER, "post-import reducer", expected=_identity(payload), maximum=512 * 1024) != payload:
        raise D0FreshBaselineError("reducer changed during import")
    return module


class _GraphLoader(importlib.abc.Loader):
    def __init__(self, name: str, payloads: Mapping[str, bytes]):
        self.name = name
        self.payloads = payloads

    def create_module(self, spec: Any) -> None:
        return None

    def exec_module(self, module: Any) -> None:
        path = SCRIPT_DIR / f"{self.name}.py"
        module.__file__ = str(path)
        module.__package__ = None
        exec(
            compile(self.payloads[self.name], str(path), "exec", dont_inherit=True),
            module.__dict__,
        )


class _GraphFinder(importlib.abc.MetaPathFinder):
    def __init__(self, payloads: Mapping[str, bytes]):
        self.payloads = payloads

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> Any:
        del path, target
        if fullname not in self.payloads:
            return None
        return importlib.util.spec_from_loader(
            fullname, _GraphLoader(fullname, self.payloads),
            origin=str(SCRIPT_DIR / f"{fullname}.py"),
        )


def _load_adapter(payloads: Mapping[str, bytes]) -> Any:
    _audit_adapter_imports(payloads)
    prior = {name: sys.modules.get(name) for name in payloads}
    for name in payloads:
        sys.modules.pop(name, None)
    finder = _GraphFinder(payloads)
    sys.meta_path.insert(0, finder)
    try:
        module = importlib.import_module(ADAPTER_ROOT)
    except BaseException as exc:
        raise D0FreshBaselineError(
            f"pinned P3.19 adapter failed to load: {type(exc).__name__}"
        ) from exc
    finally:
        sys.meta_path.remove(finder)
        for name, value in prior.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    for name, payload in payloads.items():
        current = _stable_read(
            SCRIPT_DIR / f"{name}.py", f"post-import adapter source {name}",
            expected=_identity(payload), maximum=2 * 1024 * 1024,
        )
        if current != payload:
            raise D0FreshBaselineError(f"adapter source changed during import: {name}")
    return module


def _load_runtime(d0_payload: bytes, raw_payload: bytes) -> tuple[Any, Any]:
    raw_name = "device_action_raw_capture_v1"
    # The V3 producer repins the unchanged common D0 runtime bytes; keep its
    # historical import name so its pinned ``import device_action_d0_v2``
    # dependency remains byte-identical.
    d0_name = "device_action_d0_v2"
    f1_name = "device_action_f1_v2"
    prior = {name: sys.modules.get(name) for name in (raw_name, d0_name, f1_name)}
    raw_module = types.ModuleType(raw_name)
    raw_module.__file__ = str(RAW_CAPTURE)
    raw_module.__package__ = None
    f1_stub = types.ModuleType(f1_name)
    f1_stub.json_sha256 = lambda value: hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    d0_module = types.ModuleType(d0_name)
    d0_module.__file__ = str(D0_RUNTIME)
    d0_module.__package__ = None
    try:
        sys.modules[raw_name] = raw_module
        exec(compile(raw_payload, str(RAW_CAPTURE), "exec", dont_inherit=True), raw_module.__dict__)
        sys.modules[f1_name] = f1_stub
        sys.modules[d0_name] = d0_module
        exec(compile(d0_payload, str(D0_RUNTIME), "exec", dont_inherit=True), d0_module.__dict__)
    except BaseException as exc:
        raise D0FreshBaselineError(
            f"pinned D0 runtime failed to load: {type(exc).__name__}"
        ) from exc
    finally:
        for name, value in prior.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    for path, payload, label in (
        (D0_RUNTIME, d0_payload, "post-import common D0 runtime"),
        (RAW_CAPTURE, raw_payload, "post-import raw-capture helper"),
    ):
        if _stable_read(path, label, expected=_identity(payload), maximum=512 * 1024) != payload:
            raise D0FreshBaselineError(f"{label} changed")
    return d0_module, raw_module


def _load_stop_raw(inputs: Mapping[str, Any]) -> Any:
    """Load only the already-bound raw receipt reader for cut reporting."""

    return _compile_module(
        "p319_d0_stop_raw_capture", RAW_CAPTURE, inputs["raw_payload"]
    )


def _validated_static_inputs() -> dict[str, Any]:
    script_payload = _stable_read(SCRIPT, "P3.19 D0 source", maximum=1024 * 1024)
    reducer_payload = _stable_read(REDUCER, "fresh-baseline reducer", maximum=1024 * 1024)
    d0_payload = _stable_read(D0_RUNTIME, "common D0 runtime", maximum=256 * 1024)
    raw_payload = _stable_read(RAW_CAPTURE, "raw-capture helper", maximum=256 * 1024)
    adapter_payloads = _adapter_payloads()
    _audit_adapter_imports(adapter_payloads)
    d1_payload = _stable_read(D1_SOURCE, "P3.19 D1 source", maximum=1024 * 1024)
    d1_binding_payload = _stable_read(D1_BINDING, "P3.19 D1 binding", maximum=64 * 1024)
    d1_binding = _strict_object(d1_binding_payload, "P3.19 D1 binding")
    if d1_binding_payload != canonical(d1_binding) or d1_binding.get("independent_review") != {
        "status": "pass-go",
        "verdict": (
            "PASS_GO_P319_D1_FRESH_BASELINE_CANONICAL_ARM_V3_H0_CAPABILITY_V1"
        ),
    }:
        raise D0FreshBaselineError("P3.19 D1 binding is not exact pass-go")
    if (
        d1_binding.get("schema")
        != "s22plus_fyg8_p319_d1_fresh_baseline_execution_binding_v3"
        or d1_binding.get("binding_id")
        != "s22plus-fyg8-p319-d1-fresh-baseline-v3"
        or d1_binding.get("authority_prefix")
        != "DEVICE-ACTION-D1-P319-FRESH-BASELINE-V3-APPROVE:"
        or d1_binding.get("target") != TARGET
        or d1_binding.get("successor")
        != _source_receipt(D1_SOURCE, d1_payload)
    ):
        raise D0FreshBaselineError("P3.19 D1 binding identity differs")
    profile_payload = _stable_read(PROFILE, "S22+ target profile", maximum=16 * 1024)
    profile = _profile_value(profile_payload)
    intent_payload = _stable_read(INTENT, "current P3.19 intent", mode=0o400, maximum=256 * 1024)
    qualification_payload = _stable_read(QUALIFICATION, "current P3.19 qualification", mode=0o400, maximum=256 * 1024)
    candidate = _candidate_identity(intent_payload, qualification_payload)
    design = _baseline_design(reducer_payload, d1_payload, d0_payload, profile_payload)
    adb_payload = _stable_read(
        HOST_ADB, "host ADB", expected={"size": HOST_ADB_SIZE, "sha256": HOST_ADB_SHA256},
        maximum=HOST_ADB_SIZE,
    )
    binding_payload = _stable_read(BINDING_MANIFEST, "P3.19 D0 binding", maximum=128 * 1024)
    binding = _strict_object(binding_payload, "P3.19 D0 binding")
    if binding_payload != canonical(binding):
        raise D0FreshBaselineError("P3.19 D0 binding is not canonical")
    review = binding.get("independent_review")
    allowed = (
        {"status": "review-pending", "verdict": None},
        {"status": "pass-go", "verdict": REVIEW_VERDICT},
    )
    if not any(_typed_equal(review, value) for value in allowed):
        raise D0FreshBaselineError("P3.19 D0 review state differs")
    expected = _expected_manifest(
        script_payload=script_payload, reducer_payload=reducer_payload,
        d0_payload=d0_payload, raw_payload=raw_payload,
        adapter_payloads=adapter_payloads, d1_payload=d1_payload,
        d1_binding_payload=d1_binding_payload, profile_payload=profile_payload,
        adb_payload=adb_payload, candidate=candidate, design=design, review=review,
    )
    if not _typed_equal(binding, expected):
        raise D0FreshBaselineError("P3.19 D0 execution binding differs")
    receipt = _source_receipt(BINDING_MANIFEST, binding_payload)
    authority = AUTHORITY_PREFIX + receipt["sha256"]
    return {
        "manifest": binding,
        "manifest_receipt": receipt,
        "authority": authority,
        "approval_sha256": hashlib.sha256(authority.encode("ascii")).hexdigest(),
        "profile": profile,
        "candidate": candidate,
        "baseline_design": design,
        "script_payload": script_payload,
        "reducer_payload": reducer_payload,
        "d0_payload": d0_payload,
        "raw_payload": raw_payload,
        "adapter_payloads": adapter_payloads,
        "d1_payload": d1_payload,
        "d1_binding_payload": d1_binding_payload,
        "adb_payload": adb_payload,
    }


def _validated_execution_inputs(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Load reviewed executable bytes only after the live approval gate."""

    reducer = _load_reducer(inputs["reducer_payload"])
    if not _typed_equal(
        reducer._current_candidate_identity(), inputs["candidate"]
    ):
        raise D0FreshBaselineError("reducer candidate identity differs")
    if not _typed_equal(
        reducer._baseline_design_identity(), inputs["baseline_design"]
    ):
        raise D0FreshBaselineError("reducer baseline design differs")
    return {**dict(inputs), "reducer": reducer}


def _durable_create(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical(dict(value))
    parent = path.parent.absolute()
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if parent.resolve(strict=True) != parent:
        raise D0FreshBaselineError("journal parent is indirect")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o400)
    except FileExistsError as exc:
        raise D0FreshBaselineError(f"journal already exists: {path.name}") from exc
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D0FreshBaselineError("short journal write")
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
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    parent = path.parent.absolute()
    if parent.resolve(strict=True) != parent:
        raise D0FreshBaselineError("ADB snapshot parent is indirect")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".adb-snapshot-", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o500)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise D0FreshBaselineError("short ADB snapshot write")
            offset += written
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError as exc:
            raise D0FreshBaselineError(
                "ADB snapshot already exists; D0 replay is forbidden"
            ) from exc
        directory = os.open(
            parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )
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
    _validate_snapshot(path, payload)


def _arm_value(inputs: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p319_d0_fresh_baseline_arm_v3",
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": inputs["manifest"]["run_directory"],
        "action": inputs["manifest"]["action"],
        "attempt": 1,
        "consumed": True,
        "device_contact_before_arm": False,
    }


def _journal_receipt(path: Path, label: str) -> dict[str, Any]:
    payload = _stable_read(path, label, mode=0o400, maximum=512 * 1024)
    return {"path": _relative(path), **_identity(payload), "mode": "0400", "nlink": 1}


def _load_d1_evidence(inputs: Mapping[str, Any]) -> dict[str, Any]:
    reducer = inputs["reducer"]
    value, receipt = reducer._json(D1_RESULT, "P3.19 D1 result")
    validated = reducer._validate_d1(
        value, inputs["baseline_design"], inputs["candidate"],
        reducer._profile(), D1_RESULT,
    )
    return {**validated, "receipt": receipt}


def _health(d0: Any, profile: Mapping[str, Any], properties: dict[str, str], root_health: dict[str, str], usb: dict[str, Any]) -> dict[str, Any]:
    bundle = types.SimpleNamespace(profile=profile)
    return d0.validate_health(
        bundle, properties, root_health,
        usb.get("download_endpoint_count") == 0,
    )


def _target_evidence(serial: str, topology: str) -> dict[str, Any]:
    return {
        "targets": [{
            "model": TARGET["model"],
            "device": TARGET["codename"],
            "firmware_incremental": TARGET["build"],
            "android_transport": "adb",
            "adb_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
            "usb_topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
        }],
        "odin_endpoint_absent": True,
    }


def _observer_receipt(handle: Any, payload: bytes) -> dict[str, Any]:
    receipt_payload = _stable_read(
        handle.receipt_path, "raw capture receipt", mode=0o400, maximum=64 * 1024
    )
    return {
        "path": str(handle.stdout_path),
        "raw_capture": {
            "path": str(handle.receipt_path), **_identity(receipt_payload)
        },
        "source": "/proc/last_kmsg",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "read_to_eof": True,
        "stderr_bytes": 0,
        "raw_first": True,
        "parser_started_after_raw_publish": True,
    }


def _result_binding(inputs: Mapping[str, Any], d1: Mapping[str, Any], journal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "s22plus_fyg8_p319_d0_fresh_baseline_binding_v3",
        "action": inputs["manifest"]["action"],
        "adapter": _source_receipt(SCRIPT, inputs["script_payload"]),
        "baseline_design": inputs["baseline_design"],
        "candidate": inputs["candidate"],
        "d1": {
            "receipt": d1["receipt"],
            "returned_health": d1["after"],
            "selection": d1["selection"],
            "raw_evidence": d1["raw_evidence"],
        },
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": inputs["manifest"]["run_directory"],
        "run_approval_arm": inputs["manifest"]["run_approval_arm"],
        "journal": dict(journal),
        "device_writes": False,
        "reboot": False,
        "download_transition": False,
        "odin": False,
        "partition_transfer": False,
        "f1_authorized": False,
    }


def _assert_cross_binding(d1: Mapping[str, Any], serial: str, topology: str, health: Mapping[str, Any]) -> None:
    if hashlib.sha256(serial.encode()).hexdigest() != d1["selection"]["selected_serial_sha256"]:
        raise D0FreshBaselineError("D0 serial differs from D1 selection")
    if hashlib.sha256(topology.encode()).hexdigest() != d1["selection"]["selected_topology_sha256"]:
        raise D0FreshBaselineError("D0 topology differs from D1 selection")
    if health["boot_id_sha256"] != d1["after"]["boot_id_sha256"]:
        raise D0FreshBaselineError("D0 boot identity differs from D1 return")


def _validate_snapshot(path: Path, payload: bytes) -> None:
    current = _stable_read(
        path, "post-run ADB snapshot", expected=_identity(payload),
        mode=0o500, maximum=len(payload),
    )
    if current != payload:
        raise D0FreshBaselineError("ADB snapshot changed during D0")


def _node_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "regular"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "special"


def _raw_adb_inventory(raw: Any, *, run_directory_valid: bool = True) -> dict[str, Any]:
    """Reopen and account for every child of the generic ADB capture lane."""

    if not run_directory_valid:
        base = {
            "schema": "s22plus_fyg8_p319_d0_raw_adb_inventory_v1",
            "directory": str(RAW_ADB_DIR),
            "directory_present": False,
            "directory_presence_known": False,
            "directory_node_valid": False,
            "complete": False,
            "children": [],
            "handles": [],
            "invalid_receipts": [],
            "unclaimed_children": [],
        }
        return {
            **base,
            "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest(),
        }
    try:
        directory_stat = RAW_ADB_DIR.lstat()
    except FileNotFoundError:
        base = {
            "schema": "s22plus_fyg8_p319_d0_raw_adb_inventory_v1",
            "directory": str(RAW_ADB_DIR),
            "directory_present": False,
            "directory_presence_known": True,
            "directory_node_valid": False,
            "complete": False,
            "children": [],
            "handles": [],
            "invalid_receipts": [],
            "unclaimed_children": [],
        }
        return {
            **base,
            "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest(),
        }
    directory_valid = (
        stat.S_ISDIR(directory_stat.st_mode)
        and stat.S_IMODE(directory_stat.st_mode) == 0o700
        and directory_stat.st_uid == os.getuid()
        and RAW_ADB_DIR.resolve(strict=True) == RAW_ADB_DIR.absolute()
    )
    if not directory_valid:
        base = {
            "schema": "s22plus_fyg8_p319_d0_raw_adb_inventory_v1",
            "directory": str(RAW_ADB_DIR),
            "directory_present": True,
            "directory_presence_known": True,
            "directory_node_valid": False,
            "complete": False,
            "children": [],
            "handles": [],
            "invalid_receipts": [],
            "unclaimed_children": [],
        }
        return {
            **base,
            "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest(),
        }

    children: list[dict[str, Any]] = []
    child_map: dict[str, dict[str, Any]] = {}
    for child in sorted(RAW_ADB_DIR.iterdir(), key=lambda item: item.name):
        metadata = child.lstat()
        valid = (
            stat.S_ISREG(metadata.st_mode)
            and stat.S_IMODE(metadata.st_mode) == 0o400
            and metadata.st_nlink == 1
            and metadata.st_uid == os.getuid()
        )
        entry: dict[str, Any] = {
            "name": child.name,
            "node_type": _node_type(metadata.st_mode),
            "node_valid": valid,
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            "nlink": metadata.st_nlink,
            "size": metadata.st_size,
        }
        if valid:
            payload = _stable_read(
                child, f"raw-adb child {child.name}", mode=0o400,
                maximum=MAX_TEXT,
            )
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
        children.append(entry)
        child_map[child.name] = entry

    handles: list[dict[str, Any]] = []
    invalid_receipts: list[str] = []
    claimed: set[str] = set()
    for receipt_name in sorted(
        name for name in child_map if name.endswith(".capture.json")
    ):
        receipt_entry = child_map[receipt_name]
        if not receipt_entry["node_valid"]:
            invalid_receipts.append(receipt_name)
            continue
        try:
            handle = raw.load_handle(RAW_ADB_DIR / receipt_name)
        except Exception:
            invalid_receipts.append(receipt_name)
            continue
        names = {
            handle.receipt_path.name,
            handle.stdout_path.name,
            handle.stderr_path.name,
        }
        if len(names) != 3 or not names <= set(child_map):
            invalid_receipts.append(receipt_name)
            continue
        if any(not child_map[name]["node_valid"] for name in names):
            invalid_receipts.append(receipt_name)
            continue
        if claimed & names:
            invalid_receipts.append(receipt_name)
            continue
        claimed.update(names)
        handles.append({
            "name": handle.name,
            "receipt": dict(child_map[handle.receipt_path.name]),
            "stdout": dict(child_map[handle.stdout_path.name]),
            "stderr": dict(child_map[handle.stderr_path.name]),
            "returncode": handle.returncode,
            "timed_out": handle.timed_out,
            "output_exceeded": handle.output_exceeded,
            "producer_error_type": handle.producer_error_type,
        })
    unclaimed = sorted(set(child_map) - claimed)
    complete = (
        all(item["node_valid"] for item in children)
        and not invalid_receipts
        and not unclaimed
        and len(claimed) == len(children)
    )
    base = {
        "schema": "s22plus_fyg8_p319_d0_raw_adb_inventory_v1",
        "directory": str(RAW_ADB_DIR),
        "directory_present": True,
        "directory_presence_known": True,
        "directory_node_valid": True,
        "complete": complete,
        "children": children,
        "handles": handles,
        "invalid_receipts": invalid_receipts,
        "unclaimed_children": unclaimed,
    }
    return {
        **base,
        "aggregate_sha256": hashlib.sha256(canonical(base)).hexdigest(),
    }


def _require_success_raw_adb(inventory: Mapping[str, Any]) -> None:
    if (
        inventory.get("complete") is not True
        or inventory.get("directory_node_valid") is not True
        or len(inventory.get("handles", [])) != SUCCESS_RAW_ADB_HANDLE_COUNT
        or len(inventory.get("children", []))
        != SUCCESS_RAW_ADB_HANDLE_COUNT * 3
    ):
        raise D0FreshBaselineError("raw-adb success inventory differs")


def validate_result(
    value: Mapping[str, Any], inputs: Mapping[str, Any], d1: Mapping[str, Any],
    *, publishing: bool = False, raw: Any | None = None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != RESULT_REQUIRED_KEYS:
        raise D0FreshBaselineError("D0 result key set differs")
    if (
        value["schema"] != SCHEMA or value["version"] != VERSION
        or value["mode"] != "connected-read-only" or value["verdict"] != VERDICT
        or value["baseline_design_id"] != inputs["baseline_design"]["design_id"]
        or value["run_directory"] != str(RUN_DIR)
    ):
        raise D0FreshBaselineError("D0 result header differs")
    for key, expected in {
        "device_contact": True, "device_writes": False,
        "reboot_requested": False, "download_transition_requested": False,
        "odin_invoked": False, "partition_transfer": False,
        "f1_authorized": False, "live_authorized": False,
        "candidate_marker_family_absent": True, "marker_residual": False,
    }.items():
        if type(value[key]) is not bool or value[key] is not expected:
            raise D0FreshBaselineError(f"D0 result boolean differs: {key}")
    journal = value["journal"]
    if not isinstance(journal, dict) or set(journal) != {"arm", "result"}:
        raise D0FreshBaselineError("D0 journal shape differs")
    expected_binding = _result_binding(inputs, d1, journal)
    if not _typed_equal(value["binding"], expected_binding):
        raise D0FreshBaselineError("D0 result binding differs")
    if value["runtime"] != {
        **_source_receipt(D0_RUNTIME, inputs["d0_payload"]), "raw_first": True
    }:
        raise D0FreshBaselineError("D0 runtime identity differs")
    target = value["target_evidence"]
    if not isinstance(target, dict) or set(target) != {"targets", "odin_endpoint_absent"} or target["odin_endpoint_absent"] is not True or len(target["targets"]) != 1:
        raise D0FreshBaselineError("D0 target evidence differs")
    row = target["targets"][0]
    expected_row_keys = {
        "model", "device", "firmware_incremental", "android_transport",
        "adb_serial_sha256", "usb_topology_sha256",
    }
    if not isinstance(row, dict) or set(row) != expected_row_keys or row["model"] != TARGET["model"] or row["device"] != TARGET["codename"] or row["firmware_incremental"] != TARGET["build"] or row["android_transport"] != "adb":
        raise D0FreshBaselineError("D0 target row differs")
    _sha(row["adb_serial_sha256"], "D0 serial")
    _sha(row["usb_topology_sha256"], "D0 topology")
    if row["adb_serial_sha256"] != d1["selection"]["selected_serial_sha256"] or row["usb_topology_sha256"] != d1["selection"]["selected_topology_sha256"]:
        raise D0FreshBaselineError("D0 target row is not cross-bound to D1")
    initial_health = _validate_stop_health(
        value["initial_health"], "D0 initial", inputs
    )
    health = _validate_stop_health(value["health"], "D0 final", inputs)
    if (
        initial_health["boot_id_sha256"] != d1["after"]["boot_id_sha256"]
        or health["boot_id_sha256"] != d1["after"]["boot_id_sha256"]
    ):
        raise D0FreshBaselineError(
            "D0 initial/final health is not the D1 returned boot"
        )
    usb = value["usb"]
    if not isinstance(usb, dict) or set(usb) != {"initial", "final"}:
        raise D0FreshBaselineError("D0 USB shape differs")
    for name in ("initial", "final"):
        _validated_usb_snapshot(usb[name], f"D0 USB {name}")
    observer = value["observer"]
    required_observer = {
        "path", "raw_capture", "source", "bytes", "sha256", "read_to_eof",
        "stderr_bytes", "raw_first", "parser_started_after_raw_publish",
    }
    if not isinstance(observer, dict) or set(observer) != required_observer or observer["path"] != str(OBSERVER_PATH) or observer["source"] != "/proc/last_kmsg" or observer["bytes"] != RAW_SIZE or observer["read_to_eof"] is not True or observer["stderr_bytes"] != 0 or observer["raw_first"] is not True or observer["parser_started_after_raw_publish"] is not True:
        raise D0FreshBaselineError("D0 observer receipt differs")
    _sha(observer["sha256"], "D0 observer")
    raw_receipt = observer["raw_capture"]
    if not isinstance(raw_receipt, dict) or set(raw_receipt) != {"path", "size", "sha256"} or raw_receipt["path"] != str(RAW_RECEIPT):
        raise D0FreshBaselineError("D0 raw-capture receipt differs")
    if not isinstance(value["host_tool"], dict) or set(value["host_tool"]) != {
        "path", "size", "sha256", "version_output_sha256"
    } or value["host_tool"].get("path") != str(ADB_SNAPSHOT) or value["host_tool"].get("size") != HOST_ADB_SIZE or value["host_tool"].get("sha256") != HOST_ADB_SHA256:
        raise D0FreshBaselineError("D0 host-tool receipt differs")
    _sha(value["host_tool"].get("version_output_sha256"), "D0 ADB version")
    if raw is None:
        raw = _load_runtime(inputs["d0_payload"], inputs["raw_payload"])[1]
    raw_adb = _raw_adb_inventory(raw)
    _require_success_raw_adb(raw_adb)
    if not _typed_equal(value["raw_adb"], raw_adb):
        raise D0FreshBaselineError("D0 raw-adb inventory differs")
    if not publishing:
        try:
            handle = raw.load_handle(RAW_RECEIPT)
            raw.require_success(handle)
            payload = raw.read_stdout(handle, maximum=RAW_SIZE)
        except Exception as exc:
            raise D0FreshBaselineError(
                f"D0 raw evidence cannot reopen: {type(exc).__name__}"
            ) from exc
        if handle.stdout_path != OBSERVER_PATH or len(payload) != RAW_SIZE or hashlib.sha256(payload).hexdigest() != observer["sha256"]:
            raise D0FreshBaselineError("D0 raw evidence identity differs")
        arm_value = _strict_object(
            _stable_read(RUN_ARM, "D0 arm", mode=0o400, maximum=64 * 1024),
            "D0 arm",
        )
        if not _typed_equal(arm_value, _arm_value(inputs)):
            raise D0FreshBaselineError("D0 arm bytes differ")
        result_payload = _stable_read(
            RESULT_PATH, "D0 result", mode=0o400, maximum=2 * 1024 * 1024
        )
        if result_payload != canonical(dict(value)):
            raise D0FreshBaselineError("D0 result publication differs")
    return dict(value)


def _execute(
    inputs: Mapping[str, Any], d1: Mapping[str, Any], *,
    client_factory: Any | None = None, capture_factory: Any | None = None,
    usb_factory: Any | None = None, adapter: Any | None = None,
    progress: dict[str, Any] | None = None,
) -> dict[str, Any]:
    progress = {} if progress is None else progress
    try:
        RUN_DIR.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise D0FreshBaselineError("fixed D0 run directory already exists") from exc
    _prepare_snapshot(inputs["adb_payload"], ADB_SNAPSHOT)
    d0, raw = _load_runtime(inputs["d0_payload"], inputs["raw_payload"])
    progress["_raw_module"] = raw
    client = (
        d0.AdbReadOnlyClient(
            ADB_SNAPSHOT, expected_model=TARGET["model"],
            expected_device=TARGET["codename"],
        )
        if client_factory is None else client_factory(d0, raw, ADB_SNAPSHOT)
    )
    if hasattr(client, "bind_raw_capture_dir"):
        client.bind_raw_capture_dir(RUN_DIR)
    host_tool = client.receipt()
    serial = client.one_serial()
    topology = client.topology(serial)
    usb_fn = d0.usb_snapshot if usb_factory is None else usb_factory
    initial_properties = client.properties(serial)
    initial_root_health = client.root_health(serial)
    initial_usb = _validated_usb_snapshot(
        usb_fn(USB_ROOT, inputs["profile"]["target"]["download"]),
        "D0 initial USB",
    )
    initial_health = _health(
        d0, inputs["profile"], initial_properties,
        initial_root_health, initial_usb,
    )
    _assert_cross_binding(d1, serial, topology, initial_health)
    target = _target_evidence(serial, topology)
    progress["initial"] = {
        "target_evidence": target, "health": initial_health,
        "usb": initial_usb, "host_tool": host_tool,
    }
    argv = [
        str(ADB_SNAPSHOT), "-s", serial, "exec-out",
        "su -c 'cat /proc/last_kmsg'",
    ]
    handle = (
        raw.acquire_command(
            argv, RUN_DIR, "baseline-observer", timeout=180,
            stdout_maximum=RAW_SIZE, stderr_maximum=MAX_TEXT,
            stdout_name=OBSERVER_PATH.name,
            stderr_name=OBSERVER_PATH.name + ".stderr",
        )
        if capture_factory is None else capture_factory(raw, argv, RUN_DIR)
    )
    progress["raw_receipt_path"] = str(handle.receipt_path)
    try:
        raw.require_success(handle)
        payload = raw.read_stdout(handle, maximum=RAW_SIZE)
        stderr = raw.read_stderr(handle, maximum=MAX_TEXT)
    except Exception as exc:
        raise D0FreshBaselineError(
            f"raw-first observer acquisition failed: {type(exc).__name__}"
        ) from exc
    if len(payload) != RAW_SIZE or stderr:
        raise D0FreshBaselineError("raw-first observer size/stderr differs")
    progress["raw_complete"] = True
    adapter = _load_adapter(inputs["adapter_payloads"]) if adapter is None else adapter
    try:
        decoded = adapter.classify_clean_baseline(
            payload, expected_profile=adapter.PROFILE,
            expected_run_id=bytes.fromhex(inputs["candidate"]["run_id"]),
        )
    except Exception as exc:
        raise D0FreshBaselineError(
            f"P3.19 baseline classifier rejected raw: {type(exc).__name__}"
        ) from exc
    if decoded != {
        "classification": "ZERO_AMBIGUOUS", "accepted": False,
        "records": [], "baseline_size": RAW_SIZE,
        "baseline_clean": True, "integrity_issue": False,
    }:
        raise D0FreshBaselineError("P3.19 baseline classification differs")
    if any(token.encode("ascii") in payload for token in inputs["candidate"]["marker_tokens"]):
        raise D0FreshBaselineError("candidate marker family remains in baseline")
    final_serial = client.one_serial()
    final_topology = client.topology(final_serial)
    final_properties = client.properties(final_serial)
    final_root_health = client.root_health(final_serial)
    final_usb = _validated_usb_snapshot(
        usb_fn(USB_ROOT, inputs["profile"]["target"]["download"]),
        "D0 final USB",
    )
    final_health = _health(
        d0, inputs["profile"], final_properties,
        final_root_health, final_usb,
    )
    if final_serial != serial or final_topology != topology:
        raise D0FreshBaselineError("D0 target serial/topology changed")
    _assert_cross_binding(d1, final_serial, final_topology, final_health)
    progress["final"] = {
        "target_evidence": _target_evidence(final_serial, final_topology),
        "health": final_health, "usb": final_usb,
    }
    _validate_snapshot(ADB_SNAPSHOT, inputs["adb_payload"])
    arm = _journal_receipt(RUN_ARM, "D0 consumed arm")
    journal = {"arm": arm, "result": {"path": _relative(RESULT_PATH)}}
    observer = _observer_receipt(handle, payload)
    raw_adb = _raw_adb_inventory(raw)
    _require_success_raw_adb(raw_adb)
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "mode": "connected-read-only",
        "baseline_design_id": inputs["baseline_design"]["design_id"],
        "run_directory": str(RUN_DIR),
        "runtime": {
            **_source_receipt(D0_RUNTIME, inputs["d0_payload"]),
            "raw_first": True,
        },
        "binding": _result_binding(inputs, d1, journal),
        "journal": journal,
        "target_evidence": target,
        "initial_health": initial_health,
        "health": final_health,
        "observer": observer,
        "raw_adb": raw_adb,
        "usb": {"initial": initial_usb, "final": final_usb},
        "host_tool": host_tool,
        "verdict": VERDICT,
        "device_contact": True,
        "device_writes": False,
        "reboot_requested": False,
        "download_transition_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
        "candidate_marker_family_absent": True,
        "marker_residual": False,
    }
    validate_result(result, inputs, d1, publishing=True, raw=raw)
    _durable_create(RESULT_PATH, result)
    return validate_result(result, inputs, d1, raw=raw)


def _node_state(
    path: Path, *, directory: bool, expected_mode: int
) -> dict[str, bool]:
    try:
        item = path.lstat()
    except FileNotFoundError:
        return {"present": False, "node_valid": False}
    except OSError:
        return {"present": True, "node_valid": False}
    node_valid = (
        (stat.S_ISDIR(item.st_mode) if directory else stat.S_ISREG(item.st_mode))
        and stat.S_IMODE(item.st_mode) == expected_mode
        and item.st_uid == os.getuid()
        and (directory or item.st_nlink == 1)
    )
    if directory and node_valid:
        try:
            node_valid = path.resolve(strict=True) == path.absolute()
        except OSError:
            node_valid = False
    return {"present": True, "node_valid": node_valid}


def _arm_state(inputs: Mapping[str, Any]) -> dict[str, bool]:
    state = _node_state(RUN_ARM, directory=False, expected_mode=0o400)
    if not state["node_valid"]:
        return {**state, "bytes_complete": False}
    try:
        payload = _stable_read(RUN_ARM, "D0 arm after cut", maximum=64 * 1024)
        complete = _typed_equal(
            _strict_object(payload, "D0 arm after cut"), _arm_value(inputs)
        ) and payload == canonical(_arm_value(inputs))
    except D0FreshBaselineError:
        complete = False
    return {**state, "bytes_complete": complete}


def _run_state() -> dict[str, bool]:
    return _node_state(RUN_DIR, directory=True, expected_mode=0o700)


def _result_state(run_state: Mapping[str, bool]) -> dict[str, bool]:
    if not run_state["node_valid"]:
        return {
            "presence_known": False,
            "present": False,
            "node_valid": False,
            "bytes_complete": False,
        }
    state = _node_state(RESULT_PATH, directory=False, expected_mode=0o400)
    complete = False
    if state["node_valid"]:
        try:
            payload = _stable_read(
                RESULT_PATH, "D0 result after cut", mode=0o400,
                maximum=2 * 1024 * 1024,
            )
            parsed = _strict_object(payload, "D0 result after cut")
            complete = (
                payload == canonical(parsed)
                and set(parsed) == RESULT_REQUIRED_KEYS
                and parsed.get("schema") == SCHEMA
                and parsed.get("version") == VERSION
                and parsed.get("verdict") == VERDICT
            )
        except D0FreshBaselineError:
            complete = False
    return {"presence_known": True, **state, "bytes_complete": complete}


def _raw_stop_receipt(
    raw: Any, *, run_directory_valid: bool
) -> dict[str, Any]:
    if not run_directory_valid:
        return {
            "presence_known": False, "receipt_present": False,
            "receipt_node_valid": False, "complete": False,
            "receipt": None, "handle": None,
        }
    state = _node_state(RAW_RECEIPT, directory=False, expected_mode=0o400)
    if not state["present"]:
        return {
            "presence_known": True, "receipt_present": False,
            "receipt_node_valid": False, "complete": False,
            "receipt": None, "handle": None,
        }
    if not state["node_valid"]:
        return {
            "presence_known": True, "receipt_present": True,
            "receipt_node_valid": False, "complete": False,
            "receipt": None, "handle": None,
        }
    payload = _stable_read(RAW_RECEIPT, "D0 raw receipt after cut", maximum=64 * 1024)
    receipt = {"path": str(RAW_RECEIPT), **_identity(payload)}
    try:
        handle = raw.load_handle(RAW_RECEIPT)
    except Exception:
        return {
            "presence_known": True, "receipt_present": True,
            "receipt_node_valid": True, "complete": False,
            "receipt": receipt, "handle": None,
        }
    return {
        "presence_known": True, "receipt_present": True,
        "receipt_node_valid": True, "complete": True,
        "receipt": receipt,
        "handle": {
            "stdout": dict(handle.stdout), "stderr": dict(handle.stderr),
            "returncode": handle.returncode, "timed_out": handle.timed_out,
            "output_exceeded": handle.output_exceeded,
            "producer_error_type": handle.producer_error_type,
        },
    }


def _validate_stop_target(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"targets", "odin_endpoint_absent"} or value["odin_endpoint_absent"] is not True or not isinstance(value["targets"], list) or len(value["targets"]) != 1:
        raise D0FreshBaselineError(f"{label} target evidence differs")
    row = value["targets"][0]
    if not isinstance(row, dict) or set(row) != {
        "model", "device", "firmware_incremental", "android_transport",
        "adb_serial_sha256", "usb_topology_sha256",
    } or row["model"] != TARGET["model"] or row["device"] != TARGET["codename"] or row["firmware_incremental"] != TARGET["build"] or row["android_transport"] != "adb":
        raise D0FreshBaselineError(f"{label} target row differs")
    _sha(row["adb_serial_sha256"], f"{label} serial")
    _sha(row["usb_topology_sha256"], f"{label} topology")
    return row


def _validate_stop_health(value: Any, label: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "android_boot_completed", "boot_animation_stopped",
        "verified_boot_state", "root_verified", "boot_sha256",
        "supporting_partition_sha256", "odin_endpoint_absent",
        "kernel_release", "boot_id_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise D0FreshBaselineError(f"{label} health shape differs")
    expected = inputs["profile"]["start_health"]
    if any(value[key] is not True for key in (
        "android_boot_completed", "boot_animation_stopped", "root_verified",
        "odin_endpoint_absent",
    )) or value["verified_boot_state"] != expected["verified_boot_state"] or value["boot_sha256"] != expected["boot_sha256"] or value["supporting_partition_sha256"] != expected["supporting_partition_sha256"] or not isinstance(value["kernel_release"], str) or not value["kernel_release"]:
        raise D0FreshBaselineError(f"{label} health identity differs")
    _sha(value["boot_id_sha256"], f"{label} boot identity")
    return value


def _validated_usb_snapshot(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "enumerated_devices", "download_endpoint_count", "snapshot_sha256"
    } or type(value["enumerated_devices"]) is not int or value["enumerated_devices"] <= 0 or type(value["download_endpoint_count"]) is not int or value["download_endpoint_count"] != 0:
        raise D0FreshBaselineError(f"{label} USB evidence differs")
    _sha(value["snapshot_sha256"], f"{label} USB snapshot")
    return dict(value)


def _validate_stop_progress(
    value: Any, label: str, inputs: Mapping[str, Any], d1: Mapping[str, Any],
    *, final: bool,
) -> dict[str, Any] | None:
    if value is None:
        return None
    required = {"target_evidence", "health", "usb"}
    if not final:
        required.add("host_tool")
    if not isinstance(value, dict) or set(value) != required:
        raise D0FreshBaselineError(f"{label} evidence shape differs")
    row = _validate_stop_target(value["target_evidence"], label)
    health = _validate_stop_health(value["health"], label, inputs)
    _validated_usb_snapshot(value["usb"], label)
    if (
        row["adb_serial_sha256"]
        != d1["selection"]["selected_serial_sha256"]
        or row["usb_topology_sha256"]
        != d1["selection"]["selected_topology_sha256"]
        or health["boot_id_sha256"] != d1["after"]["boot_id_sha256"]
    ):
        raise D0FreshBaselineError(f"{label} differs from D1 return evidence")
    if not final:
        host = value["host_tool"]
        if not isinstance(host, dict) or set(host) != {
            "path", "size", "sha256", "version_output_sha256"
        } or host["path"] != str(ADB_SNAPSHOT) or host["size"] != HOST_ADB_SIZE or host["sha256"] != HOST_ADB_SHA256:
            raise D0FreshBaselineError("D0 stop host-tool evidence differs")
        _sha(host["version_output_sha256"], "D0 stop ADB version")
    return {"row": row, "health": health}


def validate_stop(
    value: Mapping[str, Any], inputs: Mapping[str, Any], d1: Mapping[str, Any],
    *, publishing: bool = False, raw: Any | None = None,
) -> dict[str, Any]:
    required = {
        "schema", "verdict", "execution_manifest", "approval_sha256",
        "run_directory", "stage", "error_type", "arm_present",
        "arm_node_valid", "arm_bytes_complete", "run_directory_present",
        "run_directory_node_valid", "result_presence_known",
        "result_present", "result_node_valid", "result_bytes_complete",
        "raw_capture", "raw_adb",
        "initial", "final", "consumed", "replay_authorized",
        "device_contact_unknown", "device_writes", "reboot_requested",
        "download_transition_requested", "odin_invoked", "partition_transfer",
        "f1_authorized", "live_authorized",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise D0FreshBaselineError("D0 stop key set differs")
    if value["schema"] != STOP_SCHEMA or value["verdict"] != STOP_VERDICT or value["execution_manifest"] != inputs["manifest_receipt"] or value["approval_sha256"] != inputs["approval_sha256"] or value["run_directory"] != str(RUN_DIR):
        raise D0FreshBaselineError("D0 stop header differs")
    if value["stage"] != "post-intent-failure" or not isinstance(value["error_type"], str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", value["error_type"]) is None or value["device_contact_unknown"] is not True:
        raise D0FreshBaselineError("D0 stop classification differs")
    arm = _arm_state(inputs)
    run = _run_state()
    result = _result_state(run)
    if (
        value["arm_present"] is not arm["present"]
        or value["arm_node_valid"] is not arm["node_valid"]
        or value["arm_bytes_complete"] is not arm["bytes_complete"]
        or value["run_directory_present"] is not run["present"]
        or value["run_directory_node_valid"] is not run["node_valid"]
        or value["result_presence_known"] is not result["presence_known"]
        or value["result_present"] is not result["present"]
        or value["result_node_valid"] is not result["node_valid"]
        or value["result_bytes_complete"] is not result["bytes_complete"]
    ):
        raise D0FreshBaselineError("D0 stop cut-state booleans differ")
    if not arm["present"] or value["consumed"] is not True or value["replay_authorized"] is not False:
        raise D0FreshBaselineError("D0 stop is not consumed fail-closed")
    if run["node_valid"]:
        allowed = {
            ADB_SNAPSHOT.name, "raw-adb", OBSERVER_PATH.name,
            OBSERVER_PATH.name + ".stderr", RAW_RECEIPT.name,
            RESULT_PATH.name,
        }
        children = {child.name for child in RUN_DIR.iterdir()}
        if not children <= allowed:
            raise D0FreshBaselineError("D0 stop run namespace has an extra child")
        for child in RUN_DIR.iterdir():
            item = child.lstat()
            if child.name == "raw-adb":
                continue
            if child.name == RESULT_PATH.name:
                # The separately recorded result node state owns this cut.
                continue
            elif not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
                raise D0FreshBaselineError("D0 stop namespace has an indirect child")
    if raw is None:
        raw = _load_stop_raw(inputs)
    if value["raw_capture"] != _raw_stop_receipt(
        raw, run_directory_valid=run["node_valid"]
    ):
        raise D0FreshBaselineError("D0 stop raw capture differs")
    raw_adb = _raw_adb_inventory(
        raw, run_directory_valid=run["node_valid"]
    )
    if not _typed_equal(value["raw_adb"], raw_adb):
        raise D0FreshBaselineError("D0 stop raw-adb inventory differs")
    initial = _validate_stop_progress(
        value["initial"], "D0 stop initial", inputs, d1, final=False
    )
    final = _validate_stop_progress(
        value["final"], "D0 stop final", inputs, d1, final=True
    )
    if final is not None and initial is None:
        raise D0FreshBaselineError("D0 stop final evidence lacks initial evidence")
    if initial is not None and final is not None and (
        initial["row"] != final["row"]
        or initial["health"]["boot_id_sha256"]
        != final["health"]["boot_id_sha256"]
    ):
        raise D0FreshBaselineError("D0 stop target/boot continuity differs")
    for key, expected in {
        "device_writes": False, "reboot_requested": False,
        "download_transition_requested": False, "odin_invoked": False,
        "partition_transfer": False, "f1_authorized": False,
        "live_authorized": False,
    }.items():
        if value[key] is not expected:
            raise D0FreshBaselineError(f"D0 stop effect claim differs: {key}")
    if not publishing:
        payload = _stable_read(RUN_STOP, "D0 stop receipt", mode=0o400, maximum=512 * 1024)
        if payload != canonical(dict(value)):
            raise D0FreshBaselineError("D0 stop publication differs")
    return dict(value)


def _publish_stop(
    inputs: Mapping[str, Any], d1: Mapping[str, Any], exc: BaseException,
    progress: Mapping[str, Any],
) -> None:
    arm = _arm_state(inputs)
    if not arm["present"]:
        return
    run = _run_state()
    result = _result_state(run)
    raw = progress.get("_raw_module") or _load_stop_raw(inputs)
    value = {
        "schema": STOP_SCHEMA,
        "verdict": STOP_VERDICT,
        "execution_manifest": inputs["manifest_receipt"],
        "approval_sha256": inputs["approval_sha256"],
        "run_directory": str(RUN_DIR),
        "stage": "post-intent-failure",
        "error_type": type(exc).__name__,
        "arm_present": arm["present"],
        "arm_node_valid": arm["node_valid"],
        "arm_bytes_complete": arm["bytes_complete"],
        "run_directory_present": run["present"],
        "run_directory_node_valid": run["node_valid"],
        "result_presence_known": result["presence_known"],
        "result_present": result["present"],
        "result_node_valid": result["node_valid"],
        "result_bytes_complete": result["bytes_complete"],
        "raw_capture": _raw_stop_receipt(
            raw, run_directory_valid=run["node_valid"]
        ),
        "raw_adb": _raw_adb_inventory(
            raw, run_directory_valid=run["node_valid"]
        ),
        "initial": progress.get("initial"),
        "final": progress.get("final"),
        "consumed": True,
        "replay_authorized": False,
        "device_contact_unknown": True,
        "device_writes": False,
        "reboot_requested": False,
        "download_transition_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    validate_stop(value, inputs, d1, publishing=True, raw=raw)
    _durable_create(RUN_STOP, value)


def run_live(approval: str) -> dict[str, Any]:
    inputs = _validated_static_inputs()
    if inputs["manifest"]["independent_review"] != {
        "status": "pass-go", "verdict": REVIEW_VERDICT,
    }:
        raise D0FreshBaselineError("independent D0 capability review is absent")
    if approval != inputs["authority"]:
        raise D0FreshBaselineError("exact D0 approval is absent")
    inputs = _validated_execution_inputs(inputs)
    d1 = _load_d1_evidence(inputs)
    progress: dict[str, Any] = {}
    try:
        _durable_create(RUN_ARM, _arm_value(inputs))
        return _execute(inputs, d1, progress=progress)
    except BaseException as exc:
        if not _arm_state(inputs)["present"]:
            raise D0FreshBaselineError(
                f"D0 stopped before durable intent: {type(exc).__name__}"
            ) from exc
        if RUN_STOP.exists() or RUN_STOP.is_symlink():
            raise D0FreshBaselineError("D0 stop already exists; replay is forbidden") from exc
        try:
            _publish_stop(inputs, d1, exc, progress)
        except BaseException as stop_exc:
            raise D0FreshBaselineError(
                f"D0 stopped after intent; stop publication failed: {type(stop_exc).__name__}"
            ) from exc
        raise D0FreshBaselineError(
            f"D0 stopped after durable intent: {type(exc).__name__}"
        ) from exc


def self_test() -> dict[str, Any]:
    inputs = _validated_static_inputs()
    inputs = _validated_execution_inputs(inputs)
    adapter = _load_adapter(inputs["adapter_payloads"])
    payload = bytes(RAW_SIZE)
    decoded = adapter.classify_clean_baseline(
        payload, expected_profile=adapter.PROFILE,
        expected_run_id=bytes.fromhex(inputs["candidate"]["run_id"]),
    )
    if decoded.get("classification") != "ZERO_AMBIGUOUS" or decoded.get("baseline_clean") is not True:
        raise D0FreshBaselineError("host-only baseline fixture did not classify cleanly")
    with tempfile.TemporaryDirectory(prefix="p319-d0-raw-first-") as temporary:
        _d0, raw = _load_runtime(inputs["d0_payload"], inputs["raw_payload"])
        root = Path(temporary)
        handle = raw.publish_captured_bytes(
            root, "baseline-observer", stdout=payload,
            stdout_name="baseline-observer.bin",
            stderr_name="baseline-observer.bin.stderr",
        )
        raw.require_success(handle)
        reopened = raw.read_stdout(handle, maximum=RAW_SIZE)
        if reopened != payload:
            raise D0FreshBaselineError("host-only raw-first fixture changed")
    return {
        "schema": "s22plus_fyg8_p319_d0_fresh_baseline_fixture_v3",
        "verdict": "PASS_P319_D0_FRESH_BASELINE_FIXTURE_H0",
        "review_status": inputs["manifest"]["independent_review"]["status"],
        "classification": "ZERO_AMBIGUOUS",
        "raw_bytes": RAW_SIZE,
        "d1_v3_result_present": D1_RESULT.exists() or D1_RESULT.is_symlink(),
        "fixed_d0_result_present": RESULT_PATH.exists() or RESULT_PATH.is_symlink(),
        "device_contact": False,
        "live_authorized": False,
        "approval_created": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments in ([], ["--self-test"]):
            value = self_test()
        elif len(arguments) == 3 and arguments[:2] == ["--live", "--approval"]:
            value = run_live(arguments[2])
        else:
            raise D0FreshBaselineError(
                "accepted argv is empty/--self-test or exact --live --approval TOKEN"
            )
    except D0FreshBaselineError as exc:
        print(f"P3.19 D0 fresh-baseline blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
