#!/usr/bin/env python3
"""P3.10 post-build proof for Carrier v2 and corrected telemetry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import s22plus_fyg8_p290_postbuild_linked_audit as base
import s22plus_fyg8_p300_postbuild_linked_audit as parent
import s22plus_fyg8_p310_build_repro_check as repro
import s22plus_fyg8_p310_carrier_model as carrier
import s22plus_fyg8_p310_linked_audit as linked
import s22plus_fyg8_p310_source_contract as p310
import s22plus_fyg8_p309_tracefs_abi_audit as tracefs_abi


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = linked.ADAPTER_ID
IMPLEMENTATION_ID = "s22plus-fyg8-p310-carrier-v2-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p310.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p310_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = linked.LINKED_VALIDATOR_SYMBOLS
LINKED_DATA_SYMBOLS = base.LINKED_DATA_SYMBOLS
HOST_GENERATIONS = len(p310.spec.POSITIONS) + 1
PAIR_DOMAIN_SIZE = base.PAIR_DOMAIN_SIZE
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p310.spec.POSITIONS)
HOST_OUTPUT = f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n".encode("ascii")
AuditError = linked.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = linked.require_gnu_aarch64_tools
linked_table_storage_bytes = linked.linked_table_storage_bytes
normalize_linked_table_storage = linked.normalize_linked_table_storage


def production_validator_source(patch: bytes) -> bytes:
    return parent.production_validator_source(patch)


def host_validator_tu(patch: bytes) -> bytes:
    source = parent.host_validator_tu(patch)
    old = b"#define S22_FYG8_E1_HEADER_SIZE 25\n"
    new = (
        b"#define S22_FYG8_E1_HEADER_SIZE 32\n"
        b"#define S22_FYG8_E1_SLOT_PAYLOAD_SIZE 67\n"
        b"#define S22_FYG8_E1_REQUEST_PAYLOAD_SIZE 64\n"
    )
    if source.count(old) != 1:
        raise AuditError("P3.10 host validator Carrier v2 constants differ")
    return source.replace(old, new)


def run_host_validator_tu(tu: bytes) -> dict[str, Any]:
    return parent.run_host_validator_tu(tu)


def host_native_exhaustive(root: Path) -> dict[str, Any]:
    patch = p310.generate(root)["patch"]
    result = run_host_validator_tu(host_validator_tu(patch))
    result["identity_patch"] = p310.receipt(patch)
    result["production_validator_source"] = p310.receipt(production_validator_source(patch))
    result["carrier"] = carrier.validate()
    return result


def verify_linked_table_data(vmlinux: bytes, expected: dict[str, bytes]) -> dict[str, Any]:
    previous = base.p290
    base.p290 = p310
    try:
        return parent._BASE_VERIFY_LINKED_TABLE_DATA(vmlinux, expected)  # noqa: SLF001
    finally:
        base.p290 = previous


def linked_table_data(args, result: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    root = repro.candidate_contract.intent.repo_root()
    directory = repro.candidate_contract.intent.resolve(root, args.build_a)
    vmlinux = repro.candidate_contract.stable_read(
        directory / "vmlinux",
        "P3.10 direct-ELF linked vmlinux",
        repro.ARTIFACT_LIMITS["vmlinux"],
    )
    receipt = repro.candidate_contract.intent.receipt(vmlinux)
    expected_receipt = result.get("build_a", {}).get("artifacts", {}).get("vmlinux")
    if receipt != expected_receipt:
        raise AuditError("P3.10 linked vmlinux changed after reproducibility audit")
    proof = verify_linked_table_data(vmlinux, p310.linked_table_bytes())
    proof["vmlinux"] = receipt
    return proof


def audit_linked_validator(disassembly, calls, symbol_addresses):  # noqa: ANN001, ANN201
    result = dict(parent.audit_linked_validator(disassembly, calls, symbol_addresses))
    result["audit_adapter"] = ADAPTER_ID
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
            f"P3.10 A/B disassembly failed for {symbol}: "
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
    result = linked.audit_gadget_start_callsite_pair(disassembly["build_a"], disassembly["build_b"])
    result["objdump"] = {
        "path": str(objdump.resolve()),
        "sha256": hashlib.sha256(objdump.read_bytes()).hexdigest(),
    }
    result["both_actual_full_lto_bundles_disassembled"] = True
    return result


def carrier_linked_pair(args) -> dict[str, Any]:  # noqa: ANN001
    root = repro.candidate_contract.intent.repo_root()
    tokens = (
        carrier.LONG_FAMILY,
        b"S22PLUS-FYG8-P310-HEADER-V2",
        b"S22PLUS-FYG8-P310-SLOT-V2",
    )
    rows = {}
    for label, relative in (("build_a", args.build_a), ("build_b", args.build_b)):
        directory = repro.candidate_contract.intent.resolve(root, relative)
        image = repro.candidate_contract.stable_read(
            directory / "vmlinux", f"P3.10 {label} vmlinux", repro.ARTIFACT_LIMITS["vmlinux"]
        )
        counts = {token.decode("ascii"): image.count(token) for token in tokens}
        if any(count != 1 for count in counts.values()):
            raise AuditError(f"P3.10 {label} linked Carrier v2 token count differs")
        rows[label] = counts
    if rows["build_a"] != rows["build_b"]:
        raise AuditError("P3.10 A/B linked Carrier v2 tokens differ")
    return {"token_counts": rows, "carrier": carrier.validate(), "verified": True}


def tracefs_abi_linked_pair(args, candidate_contract: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    """Prove the corrected descriptor against source and this new A/B pair."""

    root = repro.candidate_contract.intent.repo_root()
    source_registers = tracefs_abi.extract_source_registers(
        repro.candidate_contract.stable_read(
            root / tracefs_abi.PTRACE, "P3.10 arm64 tracefs register source"
        )
    )
    trace_probe = repro.candidate_contract.stable_read(
        root / tracefs_abi.TRACE_PROBE, "P3.10 trace fetch-type source"
    )
    source_types = tracefs_abi.extract_source_types(trace_probe)
    names = tracefs_abi.extract_source_name_contract(
        repro.candidate_contract.stable_read(
            root / tracefs_abi.TRACE_H, "P3.10 trace event-name source"
        ),
        trace_probe,
        repro.candidate_contract.stable_read(
            root / tracefs_abi.TRACE_PROBE_H, "P3.10 trace argument-name source"
        ),
    )
    run_id = bytes.fromhex(candidate_contract["run_id"])
    generated = p310.generator.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=carrier.unsat_record(p310.PROFILE, run_id)[len(carrier.UNSAT_FAMILY) :],
        profile=p310.PROFILE,
    )
    descriptor = tracefs_abi.validate_descriptor(
        generated["trace_descriptor_header"], source_registers, source_types, names
    )
    linked_sets: dict[str, dict[str, tuple[str, ...]]] = {}
    linked_meta: dict[str, Any] = {}
    for label, relative in (("build_a", args.build_a), ("build_b", args.build_b)):
        vmlinux = repro.candidate_contract.intent.resolve(root, relative) / "vmlinux"
        registers, register_meta = tracefs_abi._linked_names(  # noqa: SLF001
            vmlinux, "regoffset_table", 16
        )
        types, type_meta = tracefs_abi._linked_names(  # noqa: SLF001
            vmlinux, "probe_fetch_types", 48
        )
        linked_sets[label] = {"registers": registers, "types": types}
        linked_meta[label] = {
            "vmlinux_sha256": register_meta["sha256"],
            "register_symbol_size": register_meta["symbol_size"],
            "fetch_type_symbol_size": type_meta["symbol_size"],
        }
    if not (
        set(source_registers)
        == set(linked_sets["build_a"]["registers"])
        == set(linked_sets["build_b"]["registers"])
        and set(source_types)
        == set(linked_sets["build_a"]["types"])
        == set(linked_sets["build_b"]["types"])
    ):
        raise AuditError("P3.10 source/A/B tracefs ABI sets differ")
    return {
        "source_equals_a_equals_b": True,
        "registers": tracefs_abi._set_receipt(source_registers),  # noqa: SLF001
        "fetch_types": tracefs_abi._set_receipt(source_types),  # noqa: SLF001
        "descriptor": descriptor,
        "linked": linked_meta,
        "verified": True,
    }


def _configure() -> None:
    repro._configure()
    base.repro = repro
    base.linked = linked
    base.p290 = p310
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
    result["linked_audit"]["postbuild_audit"]["full_lto_p310_probe_callsites"] = full_lto_callsite_pair(args)
    result["linked_audit"]["postbuild_audit"]["carrier_v2_linked_pair"] = carrier_linked_pair(args)
    result["linked_audit"]["postbuild_audit"]["tracefs_abi_source_a_b"] = (
        tracefs_abi_linked_pair(args, result["candidate_contract"])
    )
    result["linked_audit"]["source_contract_validator"]["accept_to_resume_pending_postbuild"] = False
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
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
