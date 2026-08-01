#!/usr/bin/env python3
"""P2.96 post-build proof with linked built-in telemetry closure."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p290_postbuild_linked_audit as base
import s22plus_fyg8_p292_postbuild_linked_audit as exact_slot
import s22plus_fyg8_p296_build_repro_check as repro
import s22plus_fyg8_p296_linked_audit as linked
import s22plus_fyg8_p296_source_contract as p296
import s22plus_fyg8_p296_telemetry_closure as closure


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = linked.ADAPTER_ID
IMPLEMENTATION_ID = "s22plus-fyg8-p296-linked-builtin-value-telemetry-v1"
EXPECTED_SOURCE_CONTRACT_ID = p296.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p296_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = linked.LINKED_VALIDATOR_SYMBOLS
LINKED_DATA_SYMBOLS = base.LINKED_DATA_SYMBOLS
HOST_GENERATIONS = len(p296.spec.POSITIONS) + 1
PAIR_DOMAIN_SIZE = base.PAIR_DOMAIN_SIZE
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p296.spec.POSITIONS)
HOST_OUTPUT = f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n".encode("ascii")
AuditError = linked.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = linked.require_gnu_aarch64_tools
linked_table_storage_bytes = linked.linked_table_storage_bytes
normalize_linked_table_storage = linked.normalize_linked_table_storage
_BASE_RUN_HOST_VALIDATOR_TU = base.run_host_validator_tu
_BASE_VERIFY_LINKED_TABLE_DATA = base.verify_linked_table_data


def production_validator_source(patch: bytes) -> bytes:
    return exact_slot.production_validator_source(patch)


def host_validator_tu(patch: bytes) -> bytes:
    previous = base.production_validator_source
    base.production_validator_source = exact_slot.production_validator_source
    try:
        source = exact_slot.host_validator_tu(patch)
    finally:
        base.production_validator_source = previous
    assignment = b"s22_fyg8_e1_state.active.generation = (u8)generation;"
    replacement = (
        assignment
        + b"\n        request.detail = generation + 1U == "
        + str(HOST_ACCEPT_COUNT).encode("ascii")
        + b" ? 0xcc0U : 0U;"
    )
    if source.count(assignment) != 1 or source.count(b"request.detail = 0;") != 1:
        raise AuditError("P2.96 host validator detail injection differs")
    return source.replace(assignment, replacement)


def run_host_validator_tu(tu: bytes) -> dict[str, Any]:
    previous = {
        "HOST_GENERATIONS": base.HOST_GENERATIONS,
        "HOST_CASE_COUNT": base.HOST_CASE_COUNT,
        "HOST_ACCEPT_COUNT": base.HOST_ACCEPT_COUNT,
        "HOST_OUTPUT": base.HOST_OUTPUT,
    }
    base.HOST_GENERATIONS = HOST_GENERATIONS
    base.HOST_CASE_COUNT = HOST_CASE_COUNT
    base.HOST_ACCEPT_COUNT = HOST_ACCEPT_COUNT
    base.HOST_OUTPUT = HOST_OUTPUT
    try:
        return _BASE_RUN_HOST_VALIDATOR_TU(tu)
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def host_native_exhaustive(root: Path) -> dict[str, Any]:
    patch = p296.generate(root)["patch"]
    result = run_host_validator_tu(host_validator_tu(patch))
    result["identity_patch"] = p296.receipt(patch)
    result["production_validator_source"] = p296.receipt(
        production_validator_source(patch)
    )
    result["terminal_telemetry_detail"] = "0xcc0"
    return result


def verify_linked_table_data(
    vmlinux: bytes,
    expected: dict[str, bytes],
) -> dict[str, Any]:
    previous = base.p290
    base.p290 = p296
    try:
        return _BASE_VERIFY_LINKED_TABLE_DATA(vmlinux, expected)
    finally:
        base.p290 = previous


def linked_table_data(args, result: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    root = repro.candidate_contract.intent.repo_root()
    directory = repro.candidate_contract.intent.resolve(root, args.build_a)
    vmlinux = repro.candidate_contract.stable_read(
        directory / "vmlinux",
        "P2.96 direct-ELF linked vmlinux",
        repro.ARTIFACT_LIMITS["vmlinux"],
    )
    receipt = repro.candidate_contract.intent.receipt(vmlinux)
    expected_receipt = result.get("build_a", {}).get("artifacts", {}).get("vmlinux")
    if receipt != expected_receipt:
        raise AuditError("P2.96 linked vmlinux changed after reproducibility audit")
    proof = verify_linked_table_data(vmlinux, p296.linked_table_bytes())
    proof["vmlinux"] = receipt
    return proof


def _audit_writer_guard(writer: str) -> dict[str, Any]:
    """Run the inherited writer proof with noreturn fallthroughs removed."""

    instructions = cfg_audit._instructions(writer)  # noqa: SLF001
    _successors, noreturn_calls = exact_slot._prune_noreturn_successors(  # noqa: SLF001
        instructions,
        cfg_audit._successors(instructions),  # noqa: SLF001
    )
    if len(noreturn_calls) != 1:
        raise AuditError(
            "P2.96 linked writer stack-check failure call is missing"
        )

    original_successors = cfg_audit._successors  # noqa: SLF001

    def corrected_successors(candidate_instructions):  # noqa: ANN001, ANN202
        return exact_slot._prune_noreturn_successors(  # noqa: SLF001
            candidate_instructions,
            original_successors(candidate_instructions),
        )[0]

    cfg_audit._successors = corrected_successors  # noqa: SLF001
    try:
        result = dict(cfg_audit._audit_writer_guard(writer))  # noqa: SLF001
    finally:
        cfg_audit._successors = original_successors  # noqa: SLF001
    result["noreturn_call_fallthroughs_pruned"] = len(noreturn_calls)
    result["noreturn_call_target"] = "__stack_chk_fail"
    return result


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    _symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    required = (
        "s22_fyg8_e1_expected_item",
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_p290_tuple_allowed",
        "s22_fyg8_e1_write",
        "s22_p294_dwc3_state_snapshot",
    )
    missing = sorted(
        name
        for name in required
        if not isinstance(disassembly.get(name), str)
    )
    if missing:
        raise AuditError(f"P2.96 linked validator symbols are missing: {missing}")

    def require_call(caller: str, callee: str) -> None:
        row = calls.get(caller)
        if not isinstance(row, list) or row.count(callee) != 1:
            raise AuditError(
                f"P2.96 linked call edge is not exact: {caller}->{callee}"
            )

    require_call("s22_fyg8_e1_write", "s22_fyg8_e1_request_allowed")
    require_call("s22_fyg8_e1_request_allowed", "s22_fyg8_e1_expected_item")
    require_call("s22_fyg8_e1_request_allowed", "s22_fyg8_e1_detail_allowed")
    detail_calls = calls.get("s22_fyg8_e1_detail_allowed")
    tuple_calls = calls.get("s22_fyg8_p290_tuple_allowed")
    if (
        not isinstance(detail_calls, list)
        or detail_calls.count("s22_fyg8_p290_tuple_allowed") != 0
        or tuple_calls != []
    ):
        raise AuditError("P2.96 constant-false tuple fallback was not call-elided")
    if "s22_p294_wrapper_vbus_snapshot" in disassembly:
        raise AuditError("P2.96 external-module telemetry symbol is unexpected")
    return {
        "audit_adapter": ADAPTER_ID,
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "detail_calls_tuple_validator": False,
        "constant_false_tuple_fallback_call_elided": True,
        "writer_guard": _audit_writer_guard(
            disassembly["s22_fyg8_e1_write"]
        ),
        "register_specific_validator_patterns_used": False,
        "validator_semantics_pending_host_exhaustive": True,
        "telemetry_symbols": {
            "symbols": ["s22_p294_dwc3_state_snapshot"],
            "external_module_symbols": [],
            "full_lto_retained": True,
            "verified": True,
        },
        "accept_to_resume_pending_postbuild": True,
        "verified": False,
    }


def _configure() -> None:
    repro._configure()
    base.repro = repro
    base.linked = linked
    base.p290 = p296
    base.SCHEMA = SCHEMA
    base.VERDICT = VERDICT
    base.TARGET = TARGET
    base.ADAPTER_ID = ADAPTER_ID
    base.IMPLEMENTATION_ID = IMPLEMENTATION_ID
    base.EXPECTED_SOURCE_CONTRACT_ID = EXPECTED_SOURCE_CONTRACT_ID
    base.ADAPTER_MODULE = ADAPTER_MODULE
    base.LINKED_VALIDATOR_SYMBOLS = LINKED_VALIDATOR_SYMBOLS
    base.LINKED_DATA_SYMBOLS = LINKED_DATA_SYMBOLS
    base.HOST_GENERATIONS = HOST_GENERATIONS
    base.HOST_CASE_COUNT = HOST_CASE_COUNT
    base.HOST_ACCEPT_COUNT = HOST_ACCEPT_COUNT
    base.HOST_OUTPUT = HOST_OUTPUT
    base.production_validator_source = production_validator_source
    base.host_validator_tu = host_validator_tu
    base.run_host_validator_tu = run_host_validator_tu
    base.host_native_exhaustive = host_native_exhaustive
    base.verify_linked_table_data = verify_linked_table_data
    base.linked_table_data = linked_table_data
    base.audit_linked_validator = audit_linked_validator


def check(args):  # noqa: ANN001, ANN201
    _configure()
    result = base.check(args)
    proof = closure.run_closure(repro.candidate_contract.intent.repo_root())
    if proof.get("verdict") != closure.VERDICT or proof.get("verified") is not True:
        raise AuditError("P2.96 telemetry postbuild closure differs")
    linked_result = result["linked_audit"]
    linked_result["postbuild_audit"]["value_telemetry"] = proof
    linked_result["source_contract_validator"][
        "accept_to_resume_pending_postbuild"
    ] = False
    return result


def main(argv: list[str] | None = None) -> int:
    _configure()
    try:
        result = check(repro.parse_args(argv))
    except (
        AuditError,
        repro.CheckError,
        repro.candidate_contract.ContractError,
        repro.candidate_contract.intent.IntentError,
        subprocess.TimeoutExpired,
        OSError,
    ) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
