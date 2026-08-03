#!/usr/bin/env python3
"""P2.98 post-build proof with linked gadget-start/event closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import s22plus_fyg8_p290_postbuild_linked_audit as base
import s22plus_fyg8_p292_postbuild_linked_audit as exact_slot
import s22plus_fyg8_p296_postbuild_linked_audit as inherited
import s22plus_fyg8_p298_build_repro_check as repro
import s22plus_fyg8_p298_linked_audit as linked
import s22plus_fyg8_p298_source_contract as p298
import s22plus_fyg8_p298_telemetry_closure as closure


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = linked.ADAPTER_ID
IMPLEMENTATION_ID = "s22plus-fyg8-p298-linked-gadget-start-event-v1"
EXPECTED_SOURCE_CONTRACT_ID = p298.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p298_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = linked.LINKED_VALIDATOR_SYMBOLS
LINKED_DATA_SYMBOLS = base.LINKED_DATA_SYMBOLS
HOST_GENERATIONS = len(p298.spec.POSITIONS) + 1
PAIR_DOMAIN_SIZE = base.PAIR_DOMAIN_SIZE
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p298.spec.POSITIONS)
HOST_OUTPUT = f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n".encode(
    "ascii"
)
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
        + b" ? 0xe50U : 0U;"
    )
    if source.count(assignment) != 1 or source.count(b"request.detail = 0;") != 1:
        raise AuditError("P2.98 host validator detail injection differs")
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
    patch = p298.generate(root)["patch"]
    result = run_host_validator_tu(host_validator_tu(patch))
    result["identity_patch"] = p298.receipt(patch)
    result["production_validator_source"] = p298.receipt(
        production_validator_source(patch)
    )
    result["terminal_telemetry_detail"] = "0xe50"
    return result


def verify_linked_table_data(
    vmlinux: bytes,
    expected: dict[str, bytes],
) -> dict[str, Any]:
    previous = base.p290
    base.p290 = p298
    try:
        return _BASE_VERIFY_LINKED_TABLE_DATA(vmlinux, expected)
    finally:
        base.p290 = previous


def linked_table_data(args, result: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    root = repro.candidate_contract.intent.repo_root()
    directory = repro.candidate_contract.intent.resolve(root, args.build_a)
    vmlinux = repro.candidate_contract.stable_read(
        directory / "vmlinux",
        "P2.98 direct-ELF linked vmlinux",
        repro.ARTIFACT_LIMITS["vmlinux"],
    )
    receipt = repro.candidate_contract.intent.receipt(vmlinux)
    expected_receipt = result.get("build_a", {}).get("artifacts", {}).get("vmlinux")
    if receipt != expected_receipt:
        raise AuditError("P2.98 linked vmlinux changed after reproducibility audit")
    proof = verify_linked_table_data(vmlinux, p298.linked_table_bytes())
    proof["vmlinux"] = receipt
    return proof


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    result = dict(
        inherited.audit_linked_validator(disassembly, calls, symbol_addresses)
    )
    del calls, symbol_addresses
    callsite = linked.audit_gadget_start_callsites(disassembly)
    result["audit_adapter"] = ADAPTER_ID
    result["gadget_start_probe_targets"] = callsite
    result["accept_to_resume_pending_postbuild"] = True
    result["verified"] = False
    return result


def _disassemble_symbol(tool: Path, vmlinux: Path, symbol: str) -> str:
    completed = subprocess.run(
        [str(tool), "-d", f"--disassemble={symbol}", str(vmlinux)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0 or completed.stderr:
        raise AuditError(
            f"P2.98 A/B disassembly failed for {symbol}: "
            + completed.stderr.decode("utf-8", "replace")[-1000:]
        )
    return completed.stdout.decode("ascii", "replace")


def full_lto_callsite_pair(args) -> dict[str, Any]:  # noqa: ANN001
    root = repro.candidate_contract.intent.repo_root()
    directories = {
        "build_a": repro.candidate_contract.intent.resolve(root, args.build_a),
        "build_b": repro.candidate_contract.intent.resolve(root, args.build_b),
    }
    objdump = Path(args.objdump)
    disassembly = {
        name: {
            symbol: _disassemble_symbol(objdump, directory / "vmlinux", symbol)
            for symbol in linked.CALLSITE_AUDIT_SYMBOLS
        }
        for name, directory in directories.items()
    }
    result = linked.audit_gadget_start_callsite_pair(
        disassembly["build_a"], disassembly["build_b"]
    )
    result["objdump"] = {
        "path": str(objdump.resolve()),
        "sha256": hashlib.sha256(objdump.read_bytes()).hexdigest(),
    }
    result["both_actual_full_lto_bundles_disassembled"] = True
    return result


def _configure() -> None:
    repro._configure()
    base.repro = repro
    base.linked = linked
    base.p290 = p298
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
    callsite_pair = full_lto_callsite_pair(args)
    proof = closure.run_closure(repro.candidate_contract.intent.repo_root())
    if proof.get("verdict") != closure.VERDICT or proof.get("verified") is not True:
        raise AuditError("P2.98 telemetry postbuild closure differs")
    linked_result = result["linked_audit"]
    linked_result["postbuild_audit"]["gadget_start_event_telemetry"] = proof
    linked_result["postbuild_audit"]["full_lto_gadget_start_callsites"] = (
        callsite_pair
    )
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
