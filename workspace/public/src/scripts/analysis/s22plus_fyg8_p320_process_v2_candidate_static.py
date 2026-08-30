#!/usr/bin/env python3
"""Bind the P3.20 stock candidate build to a small H0 static closure.

P3.20 does not repeat the P3.19 qualification ladder.  It reopens the final
observer-integrated stock-builder result, the exact P3.19 candidate-static
predecessor, and the P320 adapter/source closure.  The output is a private,
non-authorizing contract consumed by the P320 offline promotion step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SELF_SOURCE = Path(__file__).resolve()
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p320_stock_process_v2_adapter.py"
BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p320_stock_candidate_build.py"
P319_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p319_process_v2_candidate_static.py"
P319_STATIC_RESULT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-candidate-static-20260830-14.json"
)
P319_AP = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-55/candidate-a/odin4/AP.tar.md5"
)
ROLLBACK_AP = ROOT / (
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p320/"
    "process-v2-candidate-static-20260830-03.json"
)

SCHEMA = "s22plus_fyg8_p320_process_v2_candidate_static_v1"
VERDICT = "PASS_P320_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P320_RUN_ID = "c320f1e0a90b5e6d7c8a9b0c1d2e3f40"
P319_RUN_ID = "b9cc424d0d184f5accbce94a844e817d"
P319_OVERLAY = "s22plus-fyg8-p319-stock-witness-carrier-v1"
PARENT_SOURCE = "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
P320_OVERLAY = "s22plus-fyg8-p320-observer-v4-carrier-v1"
P319_AP_IDENTITY = {
    "size": 27_279_401,
    "sha256": "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6",
}
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


class StaticContractError(ValueError):
    """The P320 candidate-static closure cannot be trusted."""


def canonical(value: Any) -> bytes:
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
    except (TypeError, ValueError, UnicodeError) as exc:
        raise StaticContractError("P3.20 candidate-static value is not canonical JSON") from exc


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise StaticContractError("P3.20 source escaped the repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    maximum: int = 2 * 1024 * 1024,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise StaticContractError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    inside_id = (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before_id != inside_id
        or before_id != after_id
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
        or (expected is not None and identity(payload) != dict(expected))
    ):
        raise StaticContractError(f"{label} identity differs")
    return payload


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StaticContractError("P3.20 JSON contains a duplicate key")
        value[key] = item
    return value


def decode(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StaticContractError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise StaticContractError(f"{label} is not an object")
    return value


def _load_source(path: Path, name: str) -> tuple[types.ModuleType, bytes]:
    source = stable_bytes(path, f"{name} source", 8 * 1024 * 1024)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    except Exception as exc:
        raise StaticContractError(f"{name} source failed to load") from exc
    return module, source


def _receipt(path: Path, label: str, maximum: int = 2 * 1024 * 1024) -> dict[str, Any]:
    payload = stable_bytes(path, label, maximum)
    return {"path": relative(path), **identity(payload)}


def _exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise StaticContractError(f"{label} shape differs")
    return value


def _builder_and_result(*, runtime_bound: bool) -> tuple[Any, bytes, dict[str, Any], dict[str, Any]]:
    builder, builder_source = _load_source(BUILDER_SOURCE, "P320 stock candidate builder")
    output_root = Path(builder.DEFAULT_OUTPUT_ROOT)
    result_path = output_root / "result.json"
    result_payload = stable_bytes(
        result_path,
        "P320 builder result",
        2 * 1024 * 1024,
        mode=0o400,
        nlink=1,
    )
    result = decode(result_payload, "P320 builder result")
    if not runtime_bound:
        try:
            audited = builder.audit_existing(output_root)
        except Exception as exc:
            raise StaticContractError("P320 builder result did not reopen") from exc
        if audited != result:
            raise StaticContractError("P320 builder audit result differs")
    return builder, builder_source, result, {
        "path": relative(result_path),
        **identity(result_payload),
    }


def _validate_builder_result(builder: Any, result: dict[str, Any]) -> None:
    if (
        result.get("schema") != builder.SCHEMA
        or result.get("verdict") != builder.VERDICT
        or result.get("target") != TARGET
        or result.get("run_id_hex") != P320_RUN_ID
    ):
        raise StaticContractError("P320 builder result header differs")
    scope = result.get("scope")
    if scope != {
        "tier": "H0",
        "host_only": True,
        "device_contact": False,
        "adb_commands": 0,
        "odin_invocations": 0,
        "candidate_transfers": 0,
        "rollback_transfers": 0,
        "live_authority_created": False,
        "replay": False,
    }:
        raise StaticContractError("P320 builder safety scope differs")
    phase2 = result.get("phase2")
    if not isinstance(phase2, dict) or (
        phase2.get("built") is not True
        or phase2.get("static_aarch64") is not True
        or phase2.get("boot_builds") != 2
        or phase2.get("ap_builds") != 2
    ):
        raise StaticContractError("P320 builder package closure is incomplete")
    candidate = phase2.get("candidate")
    if not isinstance(candidate, dict) or (
        candidate.get("byte_identical") is not True
        or candidate.get("fixed_image") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
        or candidate.get("diagnostic_absent") is not True
        or candidate.get("ap_differs_from_consumed_p319") is not True
        or candidate.get("overlay_members") != ["lib/modules/s22plus_dwc3_event_latch.ko"]
    ):
        raise StaticContractError("P320 candidate A/B closure is incomplete")
    a = candidate.get("a")
    b = candidate.get("b")
    if not isinstance(a, dict) or not isinstance(b, dict) or a != b:
        raise StaticContractError("P320 candidate A/B bytes differ")
    package = a.get("package")
    if not isinstance(package, dict) or package.get("ap_structure", {}).get("members") != ["boot.img.lz4"]:
        raise StaticContractError("P320 AP is not one boot.img.lz4 member")
    if a.get("ap_tar_md5") != package.get("ap_tar_md5"):
        raise StaticContractError("P320 packaged AP identity differs")
    rollback = phase2.get("rollback")
    if rollback != {"identity": ROLLBACK_IDENTITY, "untouched": True}:
        raise StaticContractError("P319 rollback preservation differs")
    transform = result.get("runtime_transform")
    if not isinstance(transform, dict) or (
        transform.get("parser_entry") != "p319_witness_observe_v2"
        or transform.get("payload_abi") != 4
        or transform.get("receipt_offset") != 61
        or transform.get("receipt_size") != 15
        or transform.get("human_message_only") is not True
        or transform.get("dictionary_lines_excluded") is not True
        or transform.get("header_extensions_excluded") is not True
        or transform.get("fragment_flag_metadata_excluded") is not True
        or transform.get("fragment_reassembly") is not False
        or transform.get("new_detail_namespace") is not False
        or transform.get("final_ambiguous_on_observer_error") is not True
        or transform.get("stock_payload_carrier_decoder_semantics_preserved") is not True
    ):
        raise StaticContractError("P320 observer transform boundary differs")
    wrapper = result.get("wrapper_transform")
    if not isinstance(wrapper, dict) or wrapper.get("module_load_fail_fast") is not True:
        raise StaticContractError("P320 wrapper transform boundary differs")


def _candidate_from_builder(result: dict[str, Any]) -> dict[str, Any]:
    phase2 = result["phase2"]
    source = phase2["candidate"]
    return {
        "a": {key: source["a"][key] for key in ("ap_tar_md5", "boot_img", "boot_img_lz4")},
        "b": {key: source["b"][key] for key in ("ap_tar_md5", "boot_img", "boot_img_lz4")},
        "userspace": phase2["userspace"],
        "byte_identical": source["byte_identical"],
        "static_aarch64": phase2["static_aarch64"],
        "fixed_image": source["fixed_image"],
        "one_boot_img_lz4_member": source["one_boot_img_lz4_member"],
        "overlay_members": source["overlay_members"],
    }


def _validate_bound(value: Any, *, runtime_bound: bool = False) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "schema", "verdict", "authority_source", "target", "profile", "run_id",
            "source_contract_id", "userspace_overlay_contract_id", "builder_result",
            "predecessor", "candidate", "builder_closure", "source_closure",
            "adapter_contract", "result_contract_arming", "runtime_observation_contract",
            "ready_manifest_created", "run_manifest_created", "approval_created", "safety",
        },
        "P3.20 candidate-static result",
    )
    authority = _exact(item["authority_source"], {"path", "size", "sha256"}, "P3.20 authority")
    current_authority = _receipt(SELF_SOURCE, "P3.20 candidate-static authority", 4 * 1024 * 1024)
    if authority != current_authority or authority["path"] != relative(SELF_SOURCE):
        raise StaticContractError("P3.20 candidate-static authority differs")
    if (
        item["schema"] != SCHEMA
        or item["verdict"] != VERDICT
        or item["target"] != TARGET
        or item["profile"] != "E2"
        or item["run_id"] != P320_RUN_ID
        or item["source_contract_id"] != PARENT_SOURCE
        or item["userspace_overlay_contract_id"] != P320_OVERLAY
        or item["ready_manifest_created"] is not False
        or item["run_manifest_created"] is not False
        or item["approval_created"] is not False
    ):
        raise StaticContractError("P3.20 candidate-static header differs")

    builder, builder_source, builder_result, builder_receipt = _builder_and_result(
        runtime_bound=runtime_bound
    )
    _validate_builder_result(builder, builder_result)
    if item["builder_result"] != builder_receipt:
        raise StaticContractError("P320 builder result identity differs")
    expected_builder_closure = {
        "inputs": builder_result.get("inputs"),
        "source_closure": builder_result.get("source_closure"),
        "helper_sources": builder_result.get("helper_sources"),
        "module_bytes": builder_result.get("module_bytes"),
        "tools": builder_result.get("tools"),
    }
    if item["builder_closure"] != expected_builder_closure:
        raise StaticContractError("P320 builder source closure differs")

    predecessor = _exact(
        item["predecessor"],
        {"path", "identity", "run_id", "source_contract_id", "userspace_overlay_contract_id", "validated"},
        "P3.19 predecessor closure",
    )
    predecessor_payload = stable_bytes(
        P319_STATIC_RESULT, "P3.19 predecessor static result", 2 * 1024 * 1024,
        mode=0o400, nlink=1,
    )
    predecessor_value = decode(predecessor_payload, "P3.19 predecessor static result")
    if (
        predecessor["path"] != relative(P319_STATIC_RESULT)
        or predecessor["identity"] != identity(predecessor_payload)
        or predecessor["run_id"] != P319_RUN_ID
        or predecessor["source_contract_id"] != PARENT_SOURCE
        or predecessor["userspace_overlay_contract_id"] != P319_OVERLAY
        or predecessor["validated"] is not True
    ):
        raise StaticContractError("P3.19 predecessor identity differs")
    # The P319 result is a consumed predecessor, not a new qualification
    # input.  Reopen its recorded contract/header and exact identity here;
    # rerunning its long integration ladder would make this P320 delta depend
    # on unrelated current runner bytes.
    if (
        predecessor_value.get("schema")
        != "s22plus_fyg8_p319_process_v2_candidate_static_v1"
        or predecessor_value.get("verdict")
        != "PASS_P319_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
        or predecessor_value.get("target") != TARGET
        or predecessor_value.get("profile") != "E2"
        or predecessor_value.get("run_id") != P319_RUN_ID
        or predecessor_value.get("source_contract_id") != PARENT_SOURCE
        or predecessor_value.get("userspace_overlay_contract_id") != P319_OVERLAY
        or predecessor_value.get("ready_manifest_created") is not False
        or predecessor_value.get("run_manifest_created") is not False
        or predecessor_value.get("approval_created") is not False
    ):
        raise StaticContractError("P3.19 predecessor header differs")
    predecessor_safety = predecessor_value.get("safety")
    if (
        not isinstance(predecessor_safety, dict)
        or predecessor_safety.get("host_only") is not True
        or any(
            predecessor_safety.get(name) is not False
            for name in (
                "device_contact", "device_write", "odin_invoked", "odin_transfer",
                "flash", "partition_write", "live_authorized", "d0_authorized",
                "d1_authorized", "f1_authorized", "replay_authorized",
                "causal_result_allowed", "candidate_success",
            )
        )
    ):
        raise StaticContractError("P3.19 predecessor safety differs")

    adapter, adapter_source = _load_source(ADAPTER_SOURCE, "P320 stock adapter")
    try:
        lineage = adapter.bind_exact_sources()
        adapter_contract = adapter.acceptance_fixture()
        adapter.validate_acceptance_item(adapter_contract)
        source_payloads = adapter.source_bytes(ROOT)
    except Exception as exc:
        raise StaticContractError("P320 adapter/source closure did not reopen") from exc
    if item["adapter_contract"] != adapter_contract:
        raise StaticContractError("P320 adapter contract differs")
    source_closure: dict[str, dict[str, Any]] = {
        "p320_candidate_static": current_authority,
        "p320_stock_candidate_builder": {"path": relative(BUILDER_SOURCE), **identity(builder_source)},
        "p320_stock_process_v2_adapter": {"path": relative(ADAPTER_SOURCE), **identity(adapter_source)},
        "p319_process_v2_candidate_static": {"path": relative(P319_STATIC_SOURCE), **identity(stable_bytes(P319_STATIC_SOURCE, "P3.19 static source", 4 * 1024 * 1024))},
        "p319_consumed_ap": {"path": relative(P319_AP), **identity(stable_bytes(P319_AP, "P3.19 consumed AP", 64 * 1024 * 1024, P319_AP_IDENTITY))},
        "p319_rollback_ap": {"path": relative(ROLLBACK_AP), **identity(stable_bytes(ROLLBACK_AP, "P319 rollback AP", 64 * 1024 * 1024, ROLLBACK_IDENTITY))},
    }
    for name, payload in source_payloads.items():
        source_closure[name] = {"path": adapter.SOURCE_PATHS[name], **identity(payload)}
    if item["source_closure"] != source_closure:
        raise StaticContractError("P320 execution source closure differs")
    if lineage.get("run_id") != P320_RUN_ID or lineage.get("predecessor_run_id_rejected") != P319_RUN_ID:
        raise StaticContractError("P320 run identity closure differs")

    expected_candidate = _candidate_from_builder(builder_result)
    if item["candidate"] != expected_candidate:
        raise StaticContractError("P320 candidate artifact closure differs")
    if item["candidate"]["a"]["ap_tar_md5"] == P319_AP_IDENTITY:
        raise StaticContractError("P320 candidate AP repeats consumed P319 AP")
    terminals = item["result_contract_arming"]
    if terminals != {
        "COMPLETE": {"accepted": True, "proof_class": "NONCAUSAL_SUCCESS_PATH", "detail": 0x6724, "receipt_zero": True},
        "INCOMPLETE": {"accepted": False, "proof_class": "NO_PROOF_EXPERIMENT_PRECONDITION", "detail": 0x6725, "receipt_zero": True},
        "AMBIGUOUS": {"accepted": False, "proof_class": "NO_PROOF_OBSERVER", "detail": 0x6726, "receipt_zero": False},
    }:
        raise StaticContractError("P320 result contract arming differs")
    runtime = item["runtime_observation_contract"]
    if runtime != {
        "accepted_identity": "P320_STOCK_OBSERVER_V4_RETAINED",
        "runtime_values_observed": False,
        "complete_result": "NONCAUSAL_SUCCESS_PATH",
        "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "receipt_or_ambiguous_result": "NO_PROOF_OBSERVER",
        "receipt_implies_ambiguous": True,
        "clean_terminal_requires_zero_receipt": True,
        "causal_result_allowed": False,
        "candidate_success": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
    }:
        raise StaticContractError("P320 runtime result boundary differs")
    safety = {
        "host_only": True, "device_contact": False, "device_write": False,
        "odin_invoked": False, "odin_transfer": False, "flash": False,
        "partition_write": False, "live_authorized": False, "d0_authorized": False,
        "d1_authorized": False, "f1_authorized": False, "replay_authorized": False,
        "causal_result_allowed": False, "candidate_success": False,
    }
    if item["safety"] != safety:
        raise StaticContractError("P320 H0 safety boundary differs")
    return item


def validate_result(value: Any) -> dict[str, Any]:
    return _validate_bound(value, runtime_bound=False)


def validate_bound_result(value: Any) -> dict[str, Any]:
    return _validate_bound(value, runtime_bound=True)


def build_result() -> dict[str, Any]:
    builder, builder_source, builder_result, builder_receipt = _builder_and_result(runtime_bound=False)
    _validate_builder_result(builder, builder_result)
    predecessor_payload = stable_bytes(P319_STATIC_RESULT, "P3.19 predecessor static result", 2 * 1024 * 1024, mode=0o400, nlink=1)
    predecessor_source = stable_bytes(P319_STATIC_SOURCE, "P3.19 static source", 4 * 1024 * 1024)
    predecessor = {
        "path": relative(P319_STATIC_RESULT),
        "identity": identity(predecessor_payload),
        "run_id": P319_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": P319_OVERLAY,
        "validated": True,
    }
    adapter, adapter_source = _load_source(ADAPTER_SOURCE, "P320 stock adapter")
    lineage = adapter.bind_exact_sources()
    adapter_contract = adapter.acceptance_fixture()
    adapter.validate_acceptance_item(adapter_contract)
    source_payloads = adapter.source_bytes(ROOT)
    source_closure = {
        "p320_candidate_static": _receipt(SELF_SOURCE, "P3.20 candidate-static authority", 4 * 1024 * 1024),
        "p320_stock_candidate_builder": {"path": relative(BUILDER_SOURCE), **identity(builder_source)},
        "p320_stock_process_v2_adapter": {"path": relative(ADAPTER_SOURCE), **identity(adapter_source)},
        "p319_process_v2_candidate_static": {"path": relative(P319_STATIC_SOURCE), **identity(predecessor_source)},
        "p319_consumed_ap": {"path": relative(P319_AP), **identity(stable_bytes(P319_AP, "P3.19 consumed AP", 64 * 1024 * 1024, P319_AP_IDENTITY))},
        "p319_rollback_ap": {"path": relative(ROLLBACK_AP), **identity(stable_bytes(ROLLBACK_AP, "P319 rollback AP", 64 * 1024 * 1024, ROLLBACK_IDENTITY))},
    }
    for name, payload in source_payloads.items():
        source_closure[name] = {"path": adapter.SOURCE_PATHS[name], **identity(payload)}
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority_source": source_closure["p320_candidate_static"],
        "target": TARGET,
        "profile": "E2",
        "run_id": P320_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": P320_OVERLAY,
        "builder_result": builder_receipt,
        "predecessor": predecessor,
        "candidate": _candidate_from_builder(builder_result),
        "builder_closure": {
            "inputs": builder_result.get("inputs"),
            "source_closure": builder_result.get("source_closure"),
            "helper_sources": builder_result.get("helper_sources"),
            "module_bytes": builder_result.get("module_bytes"),
            "tools": builder_result.get("tools"),
        },
        "source_closure": source_closure,
        "adapter_contract": adapter_contract,
        "result_contract_arming": {
            "COMPLETE": {"accepted": True, "proof_class": "NONCAUSAL_SUCCESS_PATH", "detail": 0x6724, "receipt_zero": True},
            "INCOMPLETE": {"accepted": False, "proof_class": "NO_PROOF_EXPERIMENT_PRECONDITION", "detail": 0x6725, "receipt_zero": True},
            "AMBIGUOUS": {"accepted": False, "proof_class": "NO_PROOF_OBSERVER", "detail": 0x6726, "receipt_zero": False},
        },
        "runtime_observation_contract": {
            "accepted_identity": "P320_STOCK_OBSERVER_V4_RETAINED",
            "runtime_values_observed": False,
            "complete_result": "NONCAUSAL_SUCCESS_PATH",
            "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "receipt_or_ambiguous_result": "NO_PROOF_OBSERVER",
            "receipt_implies_ambiguous": True,
            "clean_terminal_requires_zero_receipt": True,
            "causal_result_allowed": False,
            "candidate_success": False,
            "mux_result_claimable": False,
            "host_silent_claimable": False,
        },
        "ready_manifest_created": False,
        "run_manifest_created": False,
        "approval_created": False,
        "safety": {
            "host_only": True, "device_contact": False, "device_write": False,
            "odin_invoked": False, "odin_transfer": False, "flash": False,
            "partition_write": False, "live_authorized": False, "d0_authorized": False,
            "d1_authorized": False, "f1_authorized": False, "replay_authorized": False,
            "causal_result_allowed": False, "candidate_success": False,
        },
    }
    validate_result(result)
    return result


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise StaticContractError("P3.20 candidate-static output already exists")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        os.fchmod(descriptor, 0o400)
        if os.write(descriptor, payload) != len(payload):
            raise StaticContractError("P3.20 candidate-static write was short")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        if args.audit_only:
            payload = stable_bytes(output, "P3.20 candidate-static result", 2 * 1024 * 1024, mode=0o400, nlink=1)
            value = decode(payload, "P3.20 candidate-static result")
            validate_result(value)
            created = False
        else:
            value = build_result()
            payload = canonical(value)
            output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            publish(output, payload)
            created = True
        print(json.dumps({"schema": SCHEMA, "verdict": VERDICT, "output": str(output), "created": created}, sort_keys=True))
        return 0
    except (OSError, StaticContractError, RuntimeError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
