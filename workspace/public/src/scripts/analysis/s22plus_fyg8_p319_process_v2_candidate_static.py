#!/usr/bin/env python3
"""Build the P3.19 Process-v2 candidate-static contract without device contact.

This is deliberately not a ready-manifest builder.  It converts the reviewed
post-registration Integration V2 result into one exact offline contract for
the stock witness adapter.  The four device facts remain future F1 outputs;
only their encoder/carrier/decoder and classification contract is armed here.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
INTEGRATION_SOURCE = (
    SCRIPT_DIR / "s22plus_fyg8_p319_process_v2_integration_qualification_v2.py"
)
ADAPTER_SOURCE = SCRIPT_DIR / "s22plus_fyg8_p319_stock_process_v2_adapter.py"
INTEGRATION_RESULT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-integration-qualification-v2-20260829-05/result.json"
)
INTEGRATION_IDENTITY = {
    "size": 125_814,
    "sha256": "16c9901f3e429370c39907e1632dfe4699656db698c8fb4f3c9ab87cef3e3e9c",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "process-v2-candidate-static-20260829-01.json"
)

SCHEMA = "s22plus_fyg8_p319_process_v2_candidate_static_v1"
VERDICT = "PASS_P319_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
RUN_ID = "b9cc424d0d184f5accbce94a844e817d"
RUNTIME_WITNESSES = (
    "initial_status_classification_probe",
    "module_results",
    "retained_carrier",
    "vbusdet_irq_tuple",
)


class StaticContractError(ValueError):
    """The P3.19 candidate-static contract cannot be trusted."""


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
        raise StaticContractError("candidate-static value is not canonical JSON") from exc


def identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise StaticContractError("candidate-static input is outside the repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    *,
    expected: Mapping[str, Any] | None = None,
    maximum: int = 2 * 1024 * 1024,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise StaticContractError(f"{label} is not a direct regular file")
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise StaticContractError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    inside_id = (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if (
        before_id != inside_id
        or before_id != after_id
        or len(data) != before.st_size
        or len(data) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
        or (expected is not None and identity(data) != dict(expected))
    ):
        raise StaticContractError(f"{label} identity differs")
    return data


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StaticContractError("candidate-static input has a duplicate JSON key")
        result[key] = value
    return result


def decode_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("ascii"),
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=lambda item: (_ for _ in ()).throw(
                StaticContractError(f"{label} contains non-finite JSON: {item}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StaticContractError(f"{label} is not JSON") from exc
    if not isinstance(value, dict) or canonical(value) != data:
        raise StaticContractError(f"{label} is not canonical JSON")
    return value


def load_local(path: Path, name: str) -> Any:
    if path.is_symlink() or not path.is_file():
        raise StaticContractError(f"{name} source is unavailable")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise StaticContractError(f"{name} source cannot be loaded")
    old_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:
        raise StaticContractError(f"{name} source failed to load: {type(exc).__name__}") from exc
    finally:
        sys.path[:] = old_path


def exact_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            exact_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            exact_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _source_receipts(adapter: Any) -> dict[str, dict[str, Any]]:
    try:
        payloads = adapter.source_bytes(ROOT)
    except Exception as exc:
        raise StaticContractError("P3.19 adapter source closure failed") from exc
    if not isinstance(payloads, dict) or set(payloads) != set(adapter.SOURCE_KEYS):
        raise StaticContractError("P3.19 adapter source closure differs")
    return {
        name: {
            "path": relative(ROOT / adapter.SOURCE_PATHS[name]),
            **identity(payload),
        }
        for name, payload in sorted(payloads.items())
    }


def _validate_integration(value: Mapping[str, Any], integration: Any) -> None:
    try:
        integration.validate_result(value)
    except Exception as exc:
        raise StaticContractError("reviewed Integration V2 result is invalid") from exc
    if (
        value.get("verdict") != integration.NOT_READY_VERDICT
        or value.get("status")
        != "SOURCE_CLOSURE_PASS_RUNTIME_CLASSIFICATION_PENDING"
        or value.get("blockers") != []
        or value.get("blocker_count") != 0
        or value.get("source_closure_pass") is not True
        or value.get("runtime_classification_gate_pending") is not True
        or value.get("runner_recovery_closed") is not True
        or value.get("registry_capability_authoritative") is not True
        or value.get("runner_registry_consumption_proved") is not True
        or value.get("fresh_baseline_present") is not True
        or value.get("global_consumed_candidate_registry_present") is not True
    ):
        raise StaticContractError("Integration V2 is not the reviewed zero-blocker predecessor")
    false_flags = (
        "ready",
        "runner_ready",
        "ready_manifest_created",
        "run_manifest_created",
        "approval_created",
        "live_authorized",
        "d0_authorized",
        "d1_authorized",
        "f1_authorized",
        "replay_authorized",
        "causal_result_allowed",
        "candidate_success",
        "device_contact",
    )
    if any(value.get(name) is not False for name in false_flags):
        raise StaticContractError("Integration V2 exposes authority before static promotion")


def _derive(value: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    components = value.get("components")
    if not isinstance(components, dict):
        raise StaticContractError("Integration V2 components are absent")
    adapter = load_local(ADAPTER_SOURCE, "P3.19 stock adapter")
    try:
        armed = adapter.audit_result_contract_arming()
        adapter_audit = adapter.audit()
    except Exception as exc:
        raise StaticContractError("P3.19 stock adapter audit failed") from exc
    integration_arming = components.get("arming")
    admitted = armed.get("admitted_terminals") if isinstance(armed, dict) else None
    if (
        not isinstance(integration_arming, dict)
        or integration_arming.get("admitted_terminals") != admitted
        or integration_arming.get("admitted_terminal_count") != 3
        or integration_arming.get("admitted_digest")
        != identity(canonical(admitted))["sha256"]
        or not isinstance(admitted, list)
        or [item.get("state") for item in admitted]
        != ["COMPLETE", "INCOMPLETE", "AMBIGUOUS"]
        or [item.get("proof_class") for item in admitted]
        != [
            "NONCAUSAL_SUCCESS_PATH",
            "NO_PROOF_EXPERIMENT_PRECONDITION",
            "NO_PROOF_OBSERVER",
        ]
        or [item.get("accepted") for item in admitted] != [True, False, False]
        or armed.get("causal_result_allowed") is not False
        or armed.get("candidate_success") is not False
        or armed.get("device_contact") is not False
        or adapter_audit.get("verified") is not True
    ):
        raise StaticContractError("P3.19 result-contract arming differs")

    executability = components.get("executability")
    runtime = (
        executability.get("runtime_evaluability_witnesses")
        if isinstance(executability, dict)
        else None
    )
    if not isinstance(runtime, dict) or tuple(sorted(runtime)) != RUNTIME_WITNESSES:
        raise StaticContractError("P3.19 future runtime witness set differs")
    for name in RUNTIME_WITNESSES:
        item = runtime[name]
        if (
            not isinstance(item, dict)
            or set(item) != {
                "required",
                "status",
                "accepted_as_preflight_fact",
                "requirement",
            }
            or item.get("required") is not True
            or item.get("status") != "PENDING_FRESH_CANDIDATE_RUN"
            or item.get("accepted_as_preflight_fact") is not False
            or not isinstance(item.get("requirement"), str)
            or not item["requirement"]
        ):
            raise StaticContractError(f"P3.19 future runtime witness differs: {name}")

    cross = components.get("candidate_baseline_cross_binding")
    if (
        not isinstance(cross, dict)
        or cross.get("status") != "PASS_AUTHORITATIVE"
        or cross.get("authoritative") is not True
    ):
        raise StaticContractError("P3.19 candidate/baseline cross-binding is absent")
    fresh = components.get("fresh_baseline")
    normalized = fresh.get("normalized") if isinstance(fresh, dict) else None
    candidate_identity = (
        normalized.get("candidate_identity") if isinstance(normalized, dict) else None
    )
    closure = (
        candidate_identity.get("closure")
        if isinstance(candidate_identity, dict)
        else None
    )
    plan = closure.get("module_plan") if isinstance(closure, dict) else None
    if plan != {
        "count": 73,
        "eud_index": 38,
        "overlay_delta": ["s22plus_dwc3_event_latch.ko"],
    }:
        raise StaticContractError("P3.19 candidate module plan differs")
    if candidate_identity.get("run_id") != RUN_ID:
        raise StaticContractError("P3.19 candidate run identity differs")

    adapter_contract = {
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "decoder": adapter.DECODER_ID,
        "policy_id": adapter.POLICY_ID,
        "profile": adapter.PROFILE,
        "acm_supplemental": True,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
    }
    try:
        adapter.validate_contract(adapter_contract)
    except Exception as exc:
        raise StaticContractError("P3.19 adapter contract metadata differs") from exc

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "profile": adapter.PROFILE,
        "run_id": RUN_ID,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "integration": {
            "receipt": dict(receipt),
            "source": {
                "path": relative(INTEGRATION_SOURCE),
                **identity(stable_bytes(INTEGRATION_SOURCE, "Integration V2 source")),
            },
            "zero_blockers": True,
            "candidate_baseline_cross_binding": "PASS_AUTHORITATIVE",
            "runtime_values_observed": False,
        },
        "candidate": {
            "plan": plan,
            "identity": candidate_identity,
            "cross_binding": cross,
            "artifacts": cross.get("artifacts"),
            "artifact_files": cross.get("artifact_files"),
        },
        "preflight": {
            "fresh_baseline": {
                "identity": fresh.get("identity"),
                "authoritative": fresh.get("authoritative"),
            },
            "consumed_candidate_registry": components.get(
                "consumed_candidate_registry"
            ),
            "prerequisite": components.get("prerequisite"),
            "download_request_recovery": components.get(
                "download_request_recovery"
            ),
        },
        "adapter_contract": adapter_contract,
        "adapter_source_receipts": _source_receipts(adapter),
        "result_contract_arming": armed,
        "runtime_observation_contract": {
            "post_run_classification_only": True,
            "runtime_values_observed": False,
            "witnesses": runtime,
            "missing_or_malformed_result": "NO_PROOF_OBSERVER",
            "precondition_failure_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
            "complete_result": "NONCAUSAL_SUCCESS_PATH",
            "acm_supplemental": True,
            "causal_result_allowed": False,
            "candidate_success": False,
            "mux_result_claimable": False,
            "host_silent_claimable": False,
        },
        "ready_manifest_created": False,
        "run_manifest_created": False,
        "approval_created": False,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "d0_authorized": False,
            "d1_authorized": False,
            "f1_authorized": False,
            "replay_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }


def build_result() -> dict[str, Any]:
    integration = load_local(INTEGRATION_SOURCE, "Integration V2")
    payload = stable_bytes(
        INTEGRATION_RESULT,
        "reviewed Integration V2 result",
        expected=INTEGRATION_IDENTITY,
        maximum=256 * 1024,
        mode=0o400,
        nlink=1,
    )
    stored = decode_object(payload, "reviewed Integration V2 result")
    _validate_integration(stored, integration)
    try:
        regenerated = integration.build_result()
    except Exception as exc:
        raise StaticContractError("Integration V2 regeneration failed") from exc
    if not exact_equal(stored, regenerated):
        raise StaticContractError("Integration V2 is not byte-reproducible")
    result = _derive(stored, {"path": relative(INTEGRATION_RESULT), **identity(payload)})
    validate_result(result, stored=stored)
    return result


def validate_result(value: Mapping[str, Any], *, stored: Mapping[str, Any] | None = None) -> None:
    if stored is None:
        payload = stable_bytes(
            INTEGRATION_RESULT,
            "reviewed Integration V2 result",
            expected=INTEGRATION_IDENTITY,
            maximum=256 * 1024,
            mode=0o400,
            nlink=1,
        )
        stored = decode_object(payload, "reviewed Integration V2 result")
        receipt = {"path": relative(INTEGRATION_RESULT), **identity(payload)}
    else:
        receipt = {"path": relative(INTEGRATION_RESULT), **INTEGRATION_IDENTITY}
    integration = load_local(INTEGRATION_SOURCE, "Integration V2 validation")
    _validate_integration(stored, integration)
    expected = _derive(stored, receipt)
    if not exact_equal(dict(value), expected):
        raise StaticContractError("P3.19 candidate-static result differs")


def publish_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise StaticContractError("candidate-static output already exists")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("candidate-static output write was short")
            offset += written
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1:
            raise StaticContractError("candidate-static output metadata differs")
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
    try:
        result = build_result()
        payload = canonical(result)
        if not args.audit_only:
            output = args.out if args.out.is_absolute() else ROOT / args.out
            publish_exclusive(output, payload)
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": VERDICT,
                    "result": identity(payload),
                    "created": not args.audit_only,
                    "device_contact": False,
                    "ready_manifest_created": False,
                    "live_authorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (StaticContractError, OSError) as exc:
        print(f"P3.19 candidate-static error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
