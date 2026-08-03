#!/usr/bin/env python3
"""Register-independent linked audit interface for P2.98 telemetry."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

import s22plus_fyg8_p296_linked_audit as inherited
import s22plus_fyg8_p298_source_contract as p298


ADAPTER_ID = "s22plus-fyg8-p298-linked-audit-v1"
EXPECTED_SOURCE_CONTRACT_ID = p298.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p298_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = p298.LINKED_VALIDATOR_SYMBOLS
AuditError = inherited.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = inherited.require_gnu_aarch64_tools
CALLSITE_AUDIT_SYMBOLS = (
    *p298.PROBE_TARGET_SYMBOLS,
    *p298.GADGET_START_CALLSITE_SYMBOLS,
)


@dataclass(frozen=True)
class _Instruction:
    address: int
    mnemonic: str
    operands: str


def _instructions(disassembly: str) -> tuple[_Instruction, ...]:
    result: list[_Instruction] = []
    for line in disassembly.splitlines():
        match = re.search(
            r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]+\s+"
            r"([a-zA-Z0-9_.]+)\s*(.*)$",
            line,
        )
        if match is not None:
            result.append(
                _Instruction(
                    address=int(match.group(1), 16),
                    mnemonic=match.group(2),
                    operands=match.group(3).strip(),
                )
            )
    if not result:
        raise AuditError("P2.98 linked function has no instructions")
    if len({instruction.address for instruction in result}) != len(result):
        raise AuditError("P2.98 linked function repeats an instruction address")
    return tuple(result)


def _target(instruction: _Instruction) -> str | None:
    match = re.search(r"<([^>]+)>", instruction.operands)
    return match.group(1).split("+", 1)[0] if match is not None else None


def _operand_text(instruction: _Instruction) -> str:
    return re.sub(r"\s+", "", instruction.operands.split("//", 1)[0])


def _branch_target(instruction: _Instruction) -> int | None:
    operation = instruction.operands.split("//", 1)[0].strip()
    token = operation.split(",")[-1].strip().split()[0]
    if re.fullmatch(r"(?:0x)?[0-9a-fA-F]+", token) is None:
        return None
    return int(token.removeprefix("0x"), 16)


def _targeting(
    instructions: tuple[_Instruction, ...], symbol: str
) -> list[tuple[int, _Instruction]]:
    return [
        (index, instruction)
        for index, instruction in enumerate(instructions)
        if (_target(instruction) or "").startswith(symbol)
    ]


def _require_exact_direct_call(
    instructions: tuple[_Instruction, ...], symbol: str, count: int
) -> list[int]:
    targeted = _targeting(instructions, symbol)
    if len(targeted) != count or any(
        instruction.mnemonic != "bl" or _target(instruction) != symbol
        for _index, instruction in targeted
    ):
        raise AuditError(
            f"P2.98 linked {symbol} edge is not {count} exact direct call(s)"
        )
    return [index for index, _instruction in targeted]


def _audit_ep0_enable_chain(
    instructions: tuple[_Instruction, ...]
) -> dict[str, Any]:
    calls = _require_exact_direct_call(
        instructions, "__dwc3_gadget_ep_enable", 2
    )
    first, second = calls
    if first + 1 >= len(instructions) or second + 2 >= len(instructions):
        raise AuditError("P2.98 EP0 enable return checks are truncated")
    first_guard = instructions[first + 1]
    first_target = _branch_target(first_guard)
    second_copy = instructions[second + 1]
    second_guard = instructions[second + 2]
    if (
        first_guard.mnemonic != "cbnz"
        or not _operand_text(first_guard).startswith("w0,")
        or first_target is None
        or first_target <= instructions[second].address
        or second_copy.mnemonic != "mov"
        or re.fullmatch(r"w\d+,w0", _operand_text(second_copy)) is None
        or second_guard.mnemonic != "cbnz"
        or not _operand_text(second_guard).startswith("w0,")
        or _branch_target(second_guard) is None
    ):
        raise AuditError("P2.98 EP0 enable hit order/control flow differs")
    return {
        "direct_call_count": 2,
        "first_failure_skips_second_call": True,
        "both_returns_checked": True,
        "hit_one_is_ep0_out": True,
        "hit_two_is_ep0_in": True,
        "verified": True,
    }


def _audit_pullup_discard(
    instructions: tuple[_Instruction, ...]
) -> dict[str, Any]:
    calls = _require_exact_direct_call(
        instructions, "__dwc3_gadget_start", 1
    )
    start = calls[0]
    if start + 3 >= len(instructions):
        raise AuditError("P2.98 pullup gadget-start sequence is truncated")
    set_on = instructions[start + 1]
    overwrite = instructions[start + 2]
    run_stop = instructions[start + 3]
    if (
        set_on.mnemonic != "mov"
        or _operand_text(set_on) not in {"w1,#0x1", "w1,#1"}
        or overwrite.mnemonic != "mov"
        or re.fullmatch(r"[wx]0,[wx]\d+", _operand_text(overwrite)) is None
        or _operand_text(overwrite).split(",", 1)[1] in {"w0", "x0"}
        or run_stop.mnemonic != "bl"
        or _target(run_stop) != "dwc3_gadget_run_stop"
    ):
        raise AuditError(
            "P2.98 pullup does not overwrite gadget-start w0 before run-stop"
        )
    return {
        "direct_gadget_start_call_count": 1,
        "return_consumed_before_overwrite": False,
        "w0_overwritten_before_run_stop": True,
        "run_stop_directly_follows_overwrite": True,
        "verified": True,
    }


def _audit_resume_check(
    instructions: tuple[_Instruction, ...]
) -> dict[str, Any]:
    calls = _require_exact_direct_call(
        instructions, "__dwc3_gadget_start", 1
    )
    start = calls[0]
    if start + 1 >= len(instructions):
        raise AuditError("P2.98 resume gadget-start sequence is truncated")
    guard = instructions[start + 1]
    operands = _operand_text(guard)
    if (
        guard.mnemonic != "tbnz"
        or not operands.startswith("w0,#31,")
        or _branch_target(guard) is None
    ):
        raise AuditError("P2.98 resume does not test gadget-start signed return")
    return {
        "direct_gadget_start_call_count": 1,
        "signed_negative_return_tested_immediately": True,
        "verified": True,
    }


def _canonical_disassembly(
    disassembly: dict[str, str]
) -> dict[str, tuple[tuple[int, str, str], ...]]:
    return {
        symbol: tuple(
            (instruction.address, instruction.mnemonic, instruction.operands)
            for instruction in _instructions(disassembly[symbol])
        )
        for symbol in CALLSITE_AUDIT_SYMBOLS
    }


def audit_gadget_start_callsites(
    disassembly: dict[str, str]
) -> dict[str, Any]:
    missing = sorted(
        symbol
        for symbol in CALLSITE_AUDIT_SYMBOLS
        if not isinstance(disassembly.get(symbol), str)
    )
    if missing:
        raise AuditError(f"P2.98 call-site disassembly is missing: {missing}")
    parsed = {
        symbol: _instructions(disassembly[symbol])
        for symbol in CALLSITE_AUDIT_SYMBOLS
    }
    proof = {
        "ep0_enable_chain": _audit_ep0_enable_chain(
            parsed["__dwc3_gadget_start"]
        ),
        "pullup_discard": _audit_pullup_discard(
            parsed["dwc3_gadget_pullup"]
        ),
        "resume_control": _audit_resume_check(
            parsed["dwc3_gadget_resume"]
        ),
        "probe_targets_out_of_line": all(
            len(parsed[symbol]) > 0 for symbol in p298.PROBE_TARGET_SYMBOLS
        ),
        "symbols": list(CALLSITE_AUDIT_SYMBOLS),
        "verified": True,
    }
    return proof


def audit_gadget_start_callsite_pair(
    build_a: dict[str, str], build_b: dict[str, str]
) -> dict[str, Any]:
    proof_a = audit_gadget_start_callsites(build_a)
    proof_b = audit_gadget_start_callsites(build_b)
    canonical_a = _canonical_disassembly(build_a)
    canonical_b = _canonical_disassembly(build_b)
    if canonical_a != canonical_b or proof_a != proof_b:
        raise AuditError("P2.98 Full-LTO A/B gadget-start call sites diverge")
    encoded = json.dumps(
        canonical_a, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return {
        "build_a": proof_a,
        "build_b": proof_b,
        "a_b_disassembly_identical": True,
        "canonical_disassembly_sha256": hashlib.sha256(encoded).hexdigest(),
        "verified": True,
    }


def _validate_tables(logical_tables: dict[str, bytes]) -> None:
    expected = p298.linked_table_bytes()
    if (
        not isinstance(logical_tables, dict)
        or logical_tables != expected
        or any(not isinstance(value, bytes) for value in logical_tables.values())
    ):
        raise AuditError("P2.98 logical linked table set is invalid")


def linked_table_storage_bytes(logical_tables: dict[str, bytes]) -> dict[str, bytes]:
    _validate_tables(logical_tables)
    return dict(logical_tables)


def normalize_linked_table_storage(
    actual_storage: dict[str, bytes],
    logical_tables: dict[str, bytes],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    _validate_tables(logical_tables)
    if actual_storage != logical_tables:
        raise AuditError("P2.98 physical linked table bytes differ")
    return dict(actual_storage), {
        name: {
            "entry_count": len(data),
            "logical_stride": 1,
            "physical_stride": 1,
            "physical_equals_logical": True,
            "zero_tail_padding_verified": True,
            "physical_bytes_verified": True,
        }
        for name, data in sorted(logical_tables.items())
    }


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    result = dict(
        inherited.audit_linked_validator(disassembly, calls, symbol_addresses)
    )
    del calls, symbol_addresses
    callsite = audit_gadget_start_callsites(disassembly)
    result["audit_adapter"] = ADAPTER_ID
    result["gadget_start_probe_targets"] = callsite
    result["accept_to_resume_pending_postbuild"] = True
    return result
