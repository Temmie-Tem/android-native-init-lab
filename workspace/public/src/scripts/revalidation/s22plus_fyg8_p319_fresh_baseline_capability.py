#!/usr/bin/env python3
"""Host-only P3.19 fresh-baseline capability.

This module is the boundary between a future attended D1 normal-reboot result,
a future raw-first D0 capture, and the Process-v2 integration consumer.  It
does not arm D1, create a run directory, contact a device, or publish a
success receipt during H0.  The D1 and D0 result schemas are deliberately
separate: a hand-written set of ``fresh`` booleans is not evidence.

The H0 baseline-design identity binds the exact target/profile and the reducer,
D1 design, and current D0 runtime source bytes. The active candidate intent and
qualification remain a separate current-candidate identity; no public
Process-v2 manifest is created by this design-only unit.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
SCRIPT_DIR = SCRIPT.parent
PRIVATE = ROOT / "workspace/private"
INTENT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-10/intent.json"
)
QUALIFICATION = PRIVATE / (
    "outputs/s22plus_fyg8_p319/candidate-qualification-v1-20260821-10/qualification.json"
)
P319_ADAPTER = SCRIPT_DIR / "s22plus_fyg8_p319_stock_process_v2_adapter.py"
D1_SUCCESSOR = SCRIPT_DIR / "s22plus_fyg8_p319_d1_fresh_baseline.py"
RAW_CAPTURE = SCRIPT_DIR / "device_action_raw_capture_v1.py"
D0_RUNTIME = SCRIPT_DIR / "device_action_d0_v2.py"
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_OUT = PRIVATE / (
    "outputs/s22plus_fyg8_p319/fresh-baseline-v1/result.json"
)
RAW_SIZE = 2_097_136
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P319_DECODER = "s22plus_fyg8_p319_stock_witness_carrier_v1"
P319_SOURCE_CONTRACT = "s22plus-fyg8-p319-stock-witness-carrier-v1"
D1_SCHEMA = "s22plus_fyg8_p319_d1_fresh_baseline_v1_result"
D0_SCHEMA = "s22plus_fyg8_p319_d0_fresh_baseline_v1_result"
SCHEMA = "s22plus_fyg8_p319_fresh_baseline_v1"
VERDICT = "PASS_P319_FRESH_BASELINE_H0_NORMALIZED"
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-d1-p319-fresh-baseline/"
    "p319-fresh-baseline-1"
)
RUN_ARM = Path(str(RUN_DIR) + ".arm.json")
D0_RUN_DIR = RUN_DIR.parent / "d0-p319-fresh-baseline-1"
DEFAULT_D1 = RUN_DIR / "result.json"
DEFAULT_D0 = D0_RUN_DIR / "result.json"
BASELINE_DESIGN_SCHEMA = "s22plus_fyg8_p319_fresh_baseline_design_v1"
BASELINE_DESIGN_ID = "s22plus-fyg8-p319-fresh-baseline-design-v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
CURRENT_SOURCE_KEY_COUNT = 437
CURRENT_SOURCE_KEY_DIGEST = "f41bfd2d1a4cf62aa62500a636a22e2035f3d56f9151e806e80da86f6c9cdded"
P319_LATCH_MODULE = "s22plus_dwc3_event_latch.ko"


class FreshBaselineError(ValueError):
    """The fresh-baseline evidence is not authoritative."""


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise FreshBaselineError("value is not canonical JSON") from exc


def _identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _stable(path: Path, label: str, *, maximum: int = 512 * 1024 * 1024,
            mode: int | None = None, nlink: int | None = None) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise FreshBaselineError(f"{label} is unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise FreshBaselineError(f"{label} is not a direct regular file")
    if mode is not None and stat.S_IMODE(before.st_mode) != mode:
        raise FreshBaselineError(f"{label} mode differs")
    if nlink is not None and before.st_nlink != nlink:
        raise FreshBaselineError(f"{label} link count differs")
    if before.st_size > maximum:
        raise FreshBaselineError(f"{label} exceeds the bounded read")
    try:
        with path.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
    except OSError as exc:
        raise FreshBaselineError(f"{label} cannot be read") from exc
    after = path.lstat()
    if len(payload) != before.st_size or len(payload) > maximum:
        raise FreshBaselineError(f"{label} size changed while reading")
    def stat_tuple(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)

    if any(stat_tuple(item) != stat_tuple(before) for item in (inside, after)):
        raise FreshBaselineError(f"{label} changed while reading")
    return payload


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FreshBaselineError("duplicate JSON key")
        result[key] = value
    return result


def _json(path: Path, label: str, *, canonical: bool = True, mode: int | None = 0o400, nlink: int | None = 1) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = _stable(path, label, mode=mode, nlink=nlink, maximum=4 * 1024 * 1024)
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique,
            parse_constant=lambda value: (_ for _ in ()).throw(
                FreshBaselineError(f"{label} contains non-finite JSON: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FreshBaselineError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise FreshBaselineError(f"{label} is not an object")
    if canonical and payload != _canonical(value):
        raise FreshBaselineError(f"{label} is not canonical JSON")
    return value, {"path": _relative(path), **_identity(payload)}


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise FreshBaselineError(f"{label} key set differs")
    return value


def _bool(value: Any, label: str, expected: bool | None = None) -> bool:
    if type(value) is not bool or (expected is not None and value is not expected):
        raise FreshBaselineError(f"{label} is not a typed boolean")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise FreshBaselineError(f"{label} is not a lowercase SHA-256")
    return value


def _profile() -> dict[str, Any]:
    value, _ = _json(PROFILE, "S22+ target profile", canonical=False, mode=None, nlink=None)
    if value.get("schema") != "device_action_target_profile_v2":
        raise FreshBaselineError("target profile schema differs")
    target = value.get("target")
    if not isinstance(target, dict):
        raise FreshBaselineError("target profile target is malformed")
    if {
        "model": target.get("model"),
        "codename": target.get("device"),
        "build": target.get("firmware_incremental"),
    } != TARGET:
        raise FreshBaselineError("target profile identity differs")
    return value


def _source_identity(path: Path, label: str, *, maximum: int = 512 * 1024) -> dict[str, Any]:
    payload = _stable(path, label, maximum=maximum)
    return {"path": _relative(path), **_identity(payload)}


def _baseline_design_identity() -> dict[str, Any]:
    return {
        "schema": BASELINE_DESIGN_SCHEMA,
        "design_id": BASELINE_DESIGN_ID,
        "target": TARGET,
        "profile": _source_identity(PROFILE, "S22+ target profile"),
        "reducer": _source_identity(SCRIPT, "P3.19 baseline reducer"),
        "d1_source": _source_identity(D1_SUCCESSOR, "P3.19 D1 design source"),
        "d0_runtime": _source_identity(D0_RUNTIME, "current D0 runtime", maximum=128 * 1024),
    }


def _source_key_digest(source_keys: Mapping[str, Any]) -> str:
    payload = json.dumps(
        dict(source_keys), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_current_candidate_closure(
    intent: Mapping[str, Any], qualification: Mapping[str, Any]
) -> dict[str, Any]:
    source_keys = intent.get("source_keys")
    qualification_intent = qualification.get("intent")
    if not isinstance(source_keys, dict) or not isinstance(qualification_intent, dict):
        raise FreshBaselineError("current candidate source closure is absent")
    if qualification_intent.get("schema") != intent.get("schema"):
        raise FreshBaselineError("current candidate qualification intent schema differs")
    if qualification_intent.get("source_keys") != source_keys:
        raise FreshBaselineError("current candidate qualification source closure differs")
    if len(source_keys) != CURRENT_SOURCE_KEY_COUNT or _source_key_digest(source_keys) != CURRENT_SOURCE_KEY_DIGEST:
        raise FreshBaselineError("current candidate source-key closure digest differs")
    for logical_name, identity in source_keys.items():
        if not isinstance(logical_name, str) or not isinstance(identity, dict) or set(identity) != {"logical_path", "size", "sha256"}:
            raise FreshBaselineError(f"current candidate source key shape differs: {logical_name!r}")
        if not isinstance(identity["logical_path"], str) or type(identity["size"]) is not int or identity["size"] <= 0:
            raise FreshBaselineError(f"current candidate source key metadata differs: {logical_name!r}")
        _sha(identity["sha256"], f"current candidate source key {logical_name}")
    module_names = [name.removeprefix("module:") for name in source_keys if name.startswith("module:")]
    plan = intent.get("module_plan")
    if not isinstance(plan, dict) or set(plan) != {"count", "eud_index", "overlay_delta"}:
        raise FreshBaselineError("current candidate module plan schema differs")
    if "module:eud.ko" not in source_keys or len(module_names) != 73 or plan["count"] != len(module_names):
        raise FreshBaselineError("current candidate module-plan count differs")
    if type(plan["eud_index"]) is not int or plan["eud_index"] != 38:
        raise FreshBaselineError("current candidate EUD index differs")
    overlay = plan["overlay_delta"]
    if overlay != [P319_LATCH_MODULE] or qualification.get("overlay") != overlay:
        raise FreshBaselineError("current candidate overlay is not latch-only")
    if qualification.get("derived_eud_index") != plan["eud_index"]:
        raise FreshBaselineError("qualification EUD derivation differs")
    if qualification.get("exact_one_member_generic_overlay") is not True or qualification.get("vendor_layer_stock_modules") != len(module_names) - len(overlay):
        raise FreshBaselineError("qualification module-plan semantics differ")
    return {
        "source_keys": {"count": len(source_keys), "sha256": _source_key_digest(source_keys)},
        "module_plan": dict(plan),
    }


def _current_candidate_identity() -> dict[str, Any]:
    intent, intent_id = _json(INTENT, "current P3.19 intent")
    qualification, qualification_id = _json(QUALIFICATION, "current P3.19 qualification")
    if intent.get("schema") != "s22plus_fyg8_p319_candidate_intent_v1":
        raise FreshBaselineError("current candidate intent schema differs")
    if qualification.get("schema") != "s22plus_fyg8_p319_candidate_qualification_v1":
        raise FreshBaselineError("current candidate qualification schema differs")
    closure = _validate_current_candidate_closure(intent, qualification)
    if intent.get("target") != TARGET or qualification.get("target") != TARGET:
        raise FreshBaselineError("current candidate target differs")
    run_id = intent.get("run_id")
    if not isinstance(run_id, str) or HEX32.fullmatch(run_id) is None:
        raise FreshBaselineError("current candidate run_id differs")
    fixed = intent.get("fixed_image")
    if not isinstance(fixed, dict) or fixed != qualification.get("fixed_image"):
        raise FreshBaselineError("current candidate Image identity differs")
    if type(fixed.get("size")) is not int or fixed["size"] <= 0:
        raise FreshBaselineError("current candidate Image size differs")
    _sha(fixed.get("sha256"), "current candidate Image")
    if intent.get("process_v2_integration_created") is not False:
        raise FreshBaselineError("candidate intent already claims Process-v2 integration")
    fresh = qualification.get("fresh_live_baseline")
    if not isinstance(fresh, dict) or fresh.get("satisfied") is not False:
        raise FreshBaselineError("candidate qualification fresh-baseline state differs")
    scope = qualification.get("scope")
    if not isinstance(scope, dict) or scope.get("device_contact") is not False:
        raise FreshBaselineError("candidate qualification scope is not H0")
    marker_tokens = [
        "s22_checkpoint", "native-init", run_id, run_id.encode().hex()
    ]
    return {
        "target": TARGET,
        "run_id": run_id,
        "fixed_image": dict(fixed),
        "intent": intent_id,
        "qualification": qualification_id,
        "closure": closure,
        "marker_tokens": marker_tokens,
    }


def _load_adapter() -> Any:
    if P319_ADAPTER.is_symlink():
        raise FreshBaselineError("P3.19 adapter is indirect")
    spec = importlib.util.spec_from_file_location("p319_fresh_bound_adapter", P319_ADAPTER)
    if spec is None or spec.loader is None:
        raise FreshBaselineError("P3.19 adapter cannot be loaded")
    old = list(sys.path)
    sys.path.insert(0, str(P319_ADAPTER.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        raise FreshBaselineError(f"P3.19 adapter failed to load: {type(exc).__name__}") from exc
    finally:
        sys.path[:] = old


def collect_d0_live(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Explicit non-executable placeholder for a future reviewed D0 producer."""
    raise FreshBaselineError(
        "P3.19 D0 producer is H0 design-only; no device or acquisition implementation "
        "is present until self-binding, durable pre-contact intent, typed stop publication, "
        "and independent review"
    )


def _adapter_identity() -> dict[str, Any]:
    payload = _stable(P319_ADAPTER, "P3.19 baseline adapter", maximum=512 * 1024)
    module = _load_adapter()
    try:
        decoder_id = module.DECODER_ID
        source_contract_id = module.OVERLAY_CONTRACT_ID
        policy_id = module.POLICY_ID
    except AttributeError as exc:
        raise FreshBaselineError("P3.19 adapter metadata is incomplete") from exc
    if decoder_id != P319_DECODER:
        raise FreshBaselineError("P3.19 decoder identity differs")
    if source_contract_id != P319_SOURCE_CONTRACT:
        raise FreshBaselineError("P3.19 adapter contract identity differs")
    return {"path": _relative(P319_ADAPTER), **_identity(payload), "decoder": P319_DECODER,
            "source_contract_id": P319_SOURCE_CONTRACT, "policy_id": policy_id}


def _d0_runtime_identity() -> dict[str, Any]:
    payload = _stable(D0_RUNTIME, "current D0 raw-first runtime", maximum=128 * 1024)
    return {"path": _relative(D0_RUNTIME), **_identity(payload), "raw_first": True}


def _d1_identity() -> dict[str, Any]:
    payload = _stable(D1_SUCCESSOR, "P3.19 D1 successor", maximum=512 * 1024)
    return {"path": _relative(D1_SUCCESSOR), **_identity(payload),
            "schema": "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1"}


def _health(value: Any, label: str, profile: dict[str, Any]) -> dict[str, Any]:
    expected = profile["start_health"]
    item = _exact(value, {
        "android_boot_completed", "boot_animation_stopped", "verified_boot_state",
        "root_verified", "boot_sha256", "supporting_partition_sha256",
        "odin_endpoint_absent", "kernel_release", "boot_id_sha256",
    }, label)
    for key in ("android_boot_completed", "boot_animation_stopped", "root_verified", "odin_endpoint_absent"):
        _bool(item[key], f"{label}.{key}", True)
    if item["verified_boot_state"] != expected["verified_boot_state"]:
        raise FreshBaselineError(f"{label} verified-boot state differs")
    if item["boot_sha256"] != expected["boot_sha256"]:
        raise FreshBaselineError(f"{label} boot identity differs")
    if item["supporting_partition_sha256"] != expected["supporting_partition_sha256"]:
        raise FreshBaselineError(f"{label} supporting partition identity differs")
    if not isinstance(item["kernel_release"], str) or not item["kernel_release"]:
        raise FreshBaselineError(f"{label} kernel identity differs")
    _sha(item["boot_id_sha256"], f"{label} boot id")
    return dict(item)


def _validate_d1(value: Any, design: dict[str, Any], candidate: dict[str, Any], profile: dict[str, Any], result_path: Path) -> dict[str, Any]:
    item = _exact(value, {
        "schema", "version", "mode", "baseline_design_id", "target", "binding", "before", "after",
        "selection", "journal", "reboot_count", "candidate_transfer", "device_writes",
        "download_transition_requested", "odin_invoked", "partition_transfer",
        "f1_authorized", "live_authorized", "other_targets_commanded", "verdict",
    }, "D1 result")
    if item["schema"] != D1_SCHEMA or item["version"] != "device-action-d1-p319-v1" or item["mode"] != "attended-normal-reboot":
        raise FreshBaselineError("D1 result header differs")
    if item["baseline_design_id"] != design["design_id"] or item["target"] != TARGET:
        raise FreshBaselineError("D1 result baseline-design/target differs")
    if item["verdict"] != "PASS_P319_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH":
        raise FreshBaselineError("D1 result verdict differs")
    if item["reboot_count"] != 1 or item["other_targets_commanded"] is not False:
        raise FreshBaselineError("D1 reboot accounting differs")
    for key in ("candidate_transfer", "device_writes", "download_transition_requested", "odin_invoked", "partition_transfer", "f1_authorized", "live_authorized"):
        _bool(item[key], f"D1 result.{key}", False)
    before = _health(item["before"], "D1 before", profile)
    after = _health(item["after"], "D1 after", profile)
    if before["boot_id_sha256"] == after["boot_id_sha256"]:
        raise FreshBaselineError("D1 reboot did not produce a new boot identity")
    if item["binding"].get("baseline_design") != design or item["binding"].get("candidate") != candidate:
        raise FreshBaselineError("D1 binding does not bind current baseline-design/candidate")
    binding = item["binding"]
    required_binding = {
        "schema", "action", "adapter", "baseline_design", "candidate",
        "run_directory", "run_approval_arm", "journal", "candidate_transfer",
        "partition_payload", "odin", "download_transition", "f1_authorized",
    }
    if set(binding) != required_binding or binding["schema"] != "s22plus_fyg8_p319_d1_fresh_baseline_binding_v1":
        raise FreshBaselineError("D1 binding shape differs")
    if binding["action"] != "one exact attended normal Android reboot":
        raise FreshBaselineError("D1 binding action differs")
    if binding["adapter"] != _d1_identity():
        raise FreshBaselineError("D1 adapter identity differs")
    for key in ("candidate_transfer", "partition_payload", "odin", "download_transition", "f1_authorized"):
        _bool(binding[key], f"D1 binding.{key}", False)
    if binding["run_directory"] != {"path": _relative(RUN_DIR), "publication": "directory-no-replace-then-durable-start-no-replace"}:
        raise FreshBaselineError("D1 fixed run directory differs")
    if binding["run_approval_arm"] != {"path": _relative(RUN_ARM), "publication": "file-no-replace-fsync-then-directory-fsync"}:
        raise FreshBaselineError("D1 fixed arm path differs")
    journal = _exact(binding["journal"], {"arm", "start", "result"}, "D1 journal")
    if item["journal"] != journal:
        raise FreshBaselineError("D1 top-level journal is not bound to its binding journal")
    expected_journal_paths = {
        "arm": RUN_ARM.absolute(),
        "start": (RUN_DIR / "start.json").absolute(),
        "result": (RUN_DIR / "result.json").absolute(),
    }
    if result_path.absolute() != expected_journal_paths["result"]:
        raise FreshBaselineError("D1 result path is outside the fixed run directory")
    for name in ("arm", "start"):
        receipt = _exact(
            journal[name], {"path", "size", "sha256", "mode", "nlink"},
            f"D1 journal {name}",
        )
        if receipt["mode"] != "0400" or receipt["nlink"] != 1 or type(receipt["size"]) is not int or receipt["size"] <= 0:
            raise FreshBaselineError(f"D1 journal {name} metadata differs")
        _sha(receipt["sha256"], f"D1 journal {name}")
        journal_path = Path(receipt["path"])
        if not journal_path.is_absolute():
            journal_path = ROOT / journal_path
        if journal_path.absolute() != expected_journal_paths[name]:
            raise FreshBaselineError(f"D1 journal {name} path is outside the fixed arm/run names")
        parsed, actual = _json(journal_path, f"D1 journal {name}", canonical=False)
        if actual["size"] != receipt["size"] or actual["sha256"] != receipt["sha256"]:
            raise FreshBaselineError(f"D1 journal {name} identity differs")
        if name == "arm":
            if parsed.get("schema") != "s22plus_fyg8_p319_d1_fresh_baseline_arm_v1" or parsed.get("consumed") is not True or parsed.get("attempt") != 1:
                raise FreshBaselineError("D1 arm journal is not consumed exactly once")
        elif parsed.get("schema") != "s22plus_fyg8_p319_d1_fresh_baseline_start_v1" or parsed.get("reboot_count") != 1 or parsed.get("reboot_requested") is not True or parsed.get("before") != before:
            raise FreshBaselineError("D1 start journal is not one-shot")
    result_ref = _exact(journal["result"], {"path"}, "D1 result journal reference")
    result_ref_path = Path(result_ref["path"])
    if not result_ref_path.is_absolute():
        result_ref_path = ROOT / result_ref_path
    if result_ref_path.absolute() != expected_journal_paths["result"] or result_ref_path.absolute() != result_path.absolute():
        raise FreshBaselineError("D1 journal result path differs")
    selection = _exact(item["selection"], {
        "inventory_count", "inventory_digest", "selected_serial_sha256", "selected_topology_sha256", "other_targets_commanded"
    }, "D1 selection")
    if type(selection["inventory_count"]) is not int or selection["inventory_count"] < 1:
        raise FreshBaselineError("D1 inventory count differs")
    _sha(selection["inventory_digest"], "D1 inventory")
    _sha(selection["selected_serial_sha256"], "D1 serial")
    _sha(selection["selected_topology_sha256"], "D1 topology")
    if selection["other_targets_commanded"] is not False:
        raise FreshBaselineError("D1 other-target command claim differs")
    return {"result": item, "before": before, "after": after, "selection": selection}


def _read_raw_handle(receipt: Path, observer: Path) -> bytes:
    raw_module_spec = importlib.util.spec_from_file_location("p319_raw_capture_bound", RAW_CAPTURE)
    if raw_module_spec is None or raw_module_spec.loader is None:
        raise FreshBaselineError("raw capture module cannot be loaded")
    module = importlib.util.module_from_spec(raw_module_spec)
    sys.modules[raw_module_spec.name] = module
    raw_module_spec.loader.exec_module(module)
    try:
        handle = module.load_handle(receipt)
        module.require_success(handle)
    except Exception as exc:
        raise FreshBaselineError(f"D0 raw capture receipt is invalid: {type(exc).__name__}") from exc
    if handle.stdout_path != observer or handle.stderr_path != observer.with_suffix(observer.suffix + ".stderr"):
        raise FreshBaselineError("D0 raw handle is not bound to observer bytes")
    if int(handle.stderr["size"]) != 0:
        raise FreshBaselineError("D0 raw stderr is not empty")
    payload = _stable(observer, "D0 retained stdout", maximum=RAW_SIZE, mode=0o400, nlink=1)
    if len(payload) != RAW_SIZE or int(handle.stdout["size"]) != RAW_SIZE or handle.stdout["sha256"] != hashlib.sha256(payload).hexdigest():
        raise FreshBaselineError("D0 raw stdout size/hash differs")
    return payload


def _validate_d0(value: Any, design: dict[str, Any], d1: dict[str, Any], candidate: dict[str, Any], profile: dict[str, Any]) -> tuple[dict[str, Any], bytes]:
    item = _exact(value, {
        "schema", "version", "mode", "baseline_design_id", "run_directory", "runtime", "target_evidence", "health", "observer", "usb", "host_tool", "verdict", "device_contact", "device_writes", "reboot_requested", "download_transition_requested", "odin_invoked", "partition_transfer", "f1_authorized", "live_authorized", "candidate_marker_family_absent", "marker_residual",
    }, "D0 result")
    if item["schema"] != D0_SCHEMA or item["version"] != "device-action-d0-p319-v1" or item["mode"] != "connected-read-only":
        raise FreshBaselineError("D0 result header differs")
    if item["baseline_design_id"] != design["design_id"]:
        raise FreshBaselineError("D0 result baseline-design differs")
    if item["runtime"] != _d0_runtime_identity():
        raise FreshBaselineError("D0 raw-first runtime identity differs")
    if item["verdict"] != "PASS_P319_D0_FRESH_BASELINE_RAW_V1":
        raise FreshBaselineError("D0 result verdict differs")
    _bool(item["device_contact"], "D0 device_contact", True)
    for key in ("device_writes", "reboot_requested", "download_transition_requested", "odin_invoked", "partition_transfer", "f1_authorized", "live_authorized", "marker_residual"):
        _bool(item[key], f"D0 result.{key}", False)
    _bool(item["candidate_marker_family_absent"], "D0 candidate marker family", True)
    host_tool = _exact(item["host_tool"], {"path", "size", "sha256", "version_output_sha256"}, "D0 host-tool receipt")
    if not isinstance(host_tool["path"], str) or not host_tool["path"] or type(host_tool["size"]) is not int or host_tool["size"] <= 0:
        raise FreshBaselineError("D0 host-tool receipt shape differs")
    _sha(host_tool["sha256"], "D0 host-tool binary")
    _sha(host_tool["version_output_sha256"], "D0 host-tool version")
    run_dir_value = item["run_directory"]
    if not isinstance(run_dir_value, str) or Path(run_dir_value).resolve() != Path(run_dir_value) or Path(run_dir_value) != (RUN_DIR.parent / "d0-p319-fresh-baseline-1").absolute():
        raise FreshBaselineError("D0 run directory is not fixed")
    targets = item["target_evidence"]
    if not isinstance(targets, dict) or set(targets) != {"targets", "odin_endpoint_absent"} or targets["odin_endpoint_absent"] is not True:
        raise FreshBaselineError("D0 target evidence shape differs")
    rows = targets["targets"]
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise FreshBaselineError("D0 target cardinality differs")
    row = rows[0]
    if row.get("model") != TARGET["model"] or row.get("device") != TARGET["codename"] or row.get("firmware_incremental") != TARGET["build"]:
        raise FreshBaselineError("D0 target identity differs")
    _sha(row.get("adb_serial_sha256"), "D0 serial")
    _sha(row.get("usb_topology_sha256"), "D0 topology")
    if d1["selection"]["selected_serial_sha256"] != row["adb_serial_sha256"]:
        raise FreshBaselineError("D1 selected serial is not the sole D0 target serial")
    if d1["selection"]["selected_topology_sha256"] != row["usb_topology_sha256"]:
        raise FreshBaselineError("D1 selected topology is not the sole D0 target topology")
    health = _health(item["health"], "D0 health", profile)
    if health["boot_id_sha256"] != d1["after"]["boot_id_sha256"]:
        raise FreshBaselineError("D0 health is not from the D1 returned boot")
    usb = item["usb"]
    if not isinstance(usb, dict) or set(usb) != {"initial", "final"}:
        raise FreshBaselineError("D0 USB evidence shape differs")
    for key in ("initial", "final"):
        snap = usb[key]
        if not isinstance(snap, dict) or snap.get("download_endpoint_count") != 0 or type(snap.get("enumerated_devices")) is not int or snap["enumerated_devices"] <= 0:
            raise FreshBaselineError(f"D0 {key} USB evidence differs")
        _sha(snap.get("snapshot_sha256"), f"D0 {key} USB snapshot")
    observer = item["observer"]
    required = {"path", "raw_capture", "source", "bytes", "sha256", "read_to_eof", "stderr_bytes", "raw_first", "parser_started_after_raw_publish"}
    if not isinstance(observer, dict) or set(observer) != required or observer["source"] != "/proc/last_kmsg" or observer["bytes"] != RAW_SIZE or observer["read_to_eof"] is not True or observer["stderr_bytes"] != 0 or observer["raw_first"] is not True or observer["parser_started_after_raw_publish"] is not True:
        raise FreshBaselineError("D0 observer raw-first evidence differs")
    _sha(observer["sha256"], "D0 observer")
    path = Path(observer["path"])
    raw_receipt = _exact(observer["raw_capture"], {"path", "size", "sha256"}, "D0 raw capture")
    receipt = Path(raw_receipt["path"])
    expected_dir = Path(run_dir_value)
    if not path.is_absolute() or path != expected_dir / "baseline-observer.bin" or not receipt.is_absolute() or receipt.parent != expected_dir:
        raise FreshBaselineError("D0 observer paths are not fixed")
    payload = _read_raw_handle(receipt, path)
    receipt_payload = _stable(receipt, "D0 raw capture receipt", maximum=64 * 1024, mode=0o400, nlink=1)
    if len(receipt_payload) != raw_receipt["size"] or hashlib.sha256(receipt_payload).hexdigest() != raw_receipt["sha256"]:
        raise FreshBaselineError("D0 raw capture receipt hash differs")
    if hashlib.sha256(payload).hexdigest() != observer["sha256"]:
        raise FreshBaselineError("D0 observer hash does not bind raw stdout")
    return {"result": item, "health": health, "observer": observer}, payload


def _marker_absent(payload: bytes, candidate: dict[str, Any]) -> bool:
    return not any(token.encode("ascii") in payload for token in candidate["marker_tokens"])


def normalize(d1_path: Path, d0_path: Path) -> dict[str, Any]:
    """Validate future D1/D0 outputs and return the exact integration result."""
    profile = _profile()
    design = _baseline_design_identity()
    candidate = _current_candidate_identity()
    d1_value, d1_identity = _json(d1_path, "P3.19 D1 result")
    d0_value, d0_identity = _json(d0_path, "P3.19 D0 result")
    d1 = _validate_d1(d1_value, design, candidate, profile, d1_path)
    d0, payload = _validate_d0(d0_value, design, d1, candidate, profile)
    adapter = _load_adapter()
    try:
        decoded = adapter.classify_clean_baseline(
            payload, expected_profile=adapter.PROFILE,
            expected_run_id=bytes.fromhex(candidate["run_id"]),
        )
    except Exception as exc:
        raise FreshBaselineError(f"P3.19 clean-baseline decoder rejected raw D0: {type(exc).__name__}") from exc
    if not isinstance(decoded, dict) or decoded.get("baseline_clean") is not True or decoded.get("classification") != "ZERO_AMBIGUOUS" or decoded.get("integrity_issue") is not False:
        raise FreshBaselineError("P3.19 raw D0 is not a clean baseline")
    if not _marker_absent(payload, candidate):
        raise FreshBaselineError("candidate marker residual is present in raw baseline")
    adapter_identity = _adapter_identity()
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "baseline_design": design,
        "candidate_identity": candidate,
        "d1": {"receipt": d1_identity, "returned_health": d1["after"], "selection": d1["selection"]},
        "d0": {"receipt": d0_identity, "runtime": d0["result"]["runtime"], "target_evidence": d0["result"]["target_evidence"], "health": d0["health"], "observer": d0["observer"]},
        "raw": {"size": RAW_SIZE, "sha256": hashlib.sha256(payload).hexdigest(), "source": "/proc/last_kmsg", "raw_first": True},
        "decoder": {**adapter_identity, "classification": decoded},
        "fresh": True,
        "clean": True,
        "candidate_marker_family_absent": True,
        "marker_residual": False,
        "device_contact": False,
        "d1_device_contact": True,
        "d0_device_contact": True,
        "producer_execution_closure_reviewed": False,
        "producer_execution_closure_authoritative": False,
        "ready": False,
        "live_authorized": False,
        "d0_authorized": False,
        "d1_authorized": False,
        "f1_authorized": False,
        "replay_authorized": False,
        "candidate_success": False,
        "causal_result_allowed": False,
    }
    validate_result(result)
    return result


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a normalized result without trusting summary booleans alone."""
    required = {
        "schema", "verdict", "target", "baseline_design", "candidate_identity", "d1", "d0", "raw", "decoder", "fresh", "clean", "candidate_marker_family_absent", "marker_residual", "device_contact", "d1_device_contact", "d0_device_contact", "producer_execution_closure_reviewed", "producer_execution_closure_authoritative", "ready", "live_authorized", "d0_authorized", "d1_authorized", "f1_authorized", "replay_authorized", "candidate_success", "causal_result_allowed",
    }
    if set(value) != required:
        raise FreshBaselineError("normalized fresh-baseline key set differs")
    if value["schema"] != SCHEMA or value["verdict"] != VERDICT or value["target"] != TARGET:
        raise FreshBaselineError("normalized fresh-baseline identity differs")
    for key, expected in {
        "fresh": True, "clean": True, "candidate_marker_family_absent": True, "marker_residual": False,
        "device_contact": False, "d1_device_contact": True, "d0_device_contact": True,
        "producer_execution_closure_reviewed": False, "producer_execution_closure_authoritative": False,
        "ready": False, "live_authorized": False, "d0_authorized": False, "d1_authorized": False,
        "f1_authorized": False, "replay_authorized": False, "candidate_success": False,
        "causal_result_allowed": False,
    }.items():
        _bool(value[key], f"normalized.{key}", expected)
    if value["baseline_design"] != _baseline_design_identity():
        raise FreshBaselineError("normalized baseline-design identity differs")
    for key in ("baseline_design", "candidate_identity", "d1", "d0", "raw", "decoder"):
        if not isinstance(value[key], dict):
            raise FreshBaselineError(f"normalized.{key} is not an object")
    raw = value["raw"]
    if raw.get("size") != RAW_SIZE or raw.get("source") != "/proc/last_kmsg" or raw.get("raw_first") is not True:
        raise FreshBaselineError("normalized raw evidence differs")
    _sha(raw.get("sha256"), "normalized raw")
    classification = value["decoder"].get("classification")
    if not isinstance(classification, dict) or classification.get("baseline_clean") is not True or classification.get("classification") != "ZERO_AMBIGUOUS":
        raise FreshBaselineError("normalized decoder output differs")
    if value["d0"].get("observer", {}).get("sha256") != raw["sha256"]:
        raise FreshBaselineError("normalized D0/raw binding differs")
    if value["d0"].get("runtime") != _d0_runtime_identity():
        raise FreshBaselineError("normalized D0 runtime binding differs")
    if value["d0"].get("health", {}).get("boot_id_sha256") != value["d1"].get("returned_health", {}).get("boot_id_sha256"):
        raise FreshBaselineError("normalized D1/D0 boot binding differs")
    return dict(value)


def validate_published_result(path: Path) -> dict[str, Any]:
    value, identity = _json(path, "published fresh baseline")
    # Do not trust any nested summary from the published reducer.  Reopen the
    # fixed D1/D0 producer results, their journal/raw handles, the current
    # baseline design, candidate intent/qualification, and the live P3.19 classifier,
    # then require byte-for-byte canonical equality with the publication.
    expected = normalize(DEFAULT_D1, DEFAULT_D0)
    if value != expected:
        raise FreshBaselineError("published fresh baseline is not the deterministic reduction of its inputs")
    result = validate_result(expected)
    return {"result": result, "identity": identity, "authoritative": False, "capability": _identity(_stable(SCRIPT, "fresh-baseline capability", maximum=512 * 1024))}


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise FreshBaselineError("refusing to clobber fresh-baseline receipt")
    payload = _canonical(dict(value))
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o400)
    try:
        os.write(fd, payload)
        os.fchmod(fd, 0o400)
        os.fsync(fd)
    finally:
        os.close(fd)
    dir_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    _stable(path, "published fresh baseline", maximum=max(len(payload), 1), mode=0o400, nlink=1)
    return _identity(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d1", type=Path, default=DEFAULT_D1)
    parser.add_argument("--d0", type=Path, default=DEFAULT_D0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        result = normalize(args.d1, args.d0)
        publish_exclusive(args.out, result)
    except (FreshBaselineError, OSError, KeyError, TypeError) as exc:
        print(f"P3.19 fresh-baseline capability blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
