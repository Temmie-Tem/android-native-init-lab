#!/usr/bin/env python3
"""CFG-aware linked audit for the proof-bound P2.54 contract."""

from __future__ import annotations

import collections
import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

import s22plus_fyg8_p234_build_repro_check as repro
import s22plus_fyg8_p252_source_contract as p252


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = "s22plus-fyg8-p253-linked-audit-v2"
EXPECTED_SOURCE_CONTRACT_ID = "s22plus-fyg8-p254-e2-proof-bound-v1"

_LOADS_BY_WIDTH = {
    "byte": frozenset({"ldrb", "ldarb", "ldaprb"}),
    "halfword": frozenset({"ldrh", "ldarh", "ldaprh"}),
}
_WIDTH_BYTES = {"byte": 1, "halfword": 2}
_TERMINATORS = frozenset({"ret", "br", "brk", "eret"})
_NO_DESTINATION = frozenset(
    {
        "b",
        "bl",
        "blr",
        "br",
        "brk",
        "cmp",
        "cmn",
        "tst",
        "cbz",
        "cbnz",
        "tbz",
        "tbnz",
        "ret",
        "str",
        "strb",
        "strh",
        "stp",
        "stur",
        "sturb",
        "sturh",
        "dmb",
        "dsb",
        "isb",
    }
)


class AuditError(ValueError):
    pass


SourceContractError = AuditError


@dataclass(frozen=True)
class Instruction:
    address: int
    mnemonic: str
    operands: str
    text: str


def _instructions(disassembly: str) -> tuple[Instruction, ...]:
    result: list[Instruction] = []
    for line in disassembly.splitlines():
        match = re.search(
            r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F]+\s+"
            r"([a-zA-Z0-9_.]+)\s*(.*)$",
            line,
        )
        if match is not None:
            result.append(
                Instruction(
                    address=int(match.group(1), 16),
                    mnemonic=match.group(2),
                    operands=match.group(3).strip(),
                    text=line.strip(),
                )
            )
    if not result:
        raise AuditError("linked disassembly contains no instructions")
    if len({item.address for item in result}) != len(result):
        raise AuditError("linked disassembly repeats an instruction address")
    return tuple(result)


def _normalize_register(register: str) -> str:
    if register in {"xzr", "wzr"}:
        return "xzr"
    match = re.fullmatch(r"[wx](\d+)", register)
    return f"x{match.group(1)}" if match else register


def _integer(value: str) -> int | None:
    token = value.strip()
    if token.startswith("#"):
        token = token[1:]
    try:
        return int(token, 0)
    except ValueError:
        return None


def _branch_target(instruction: Instruction) -> int | None:
    if not (
        instruction.mnemonic == "b"
        or instruction.mnemonic.startswith("b.")
        or instruction.mnemonic in {"cbz", "cbnz", "tbz", "tbnz"}
    ):
        return None
    operation = instruction.operands.split("//", 1)[0].strip()
    token = operation.split(",")[-1].strip().split()[0]
    if re.fullmatch(r"(?:0x)?[0-9a-fA-F]+", token) is None:
        return None
    return int(token.removeprefix("0x"), 16)


def _call_target(instruction: Instruction) -> str | None:
    if instruction.mnemonic != "bl":
        return None
    match = re.search(r"<([^>]+)>", instruction.operands)
    if match is None:
        return None
    name = match.group(1).split("+", 1)[0]
    if name.startswith("__pi_"):
        name = name[5:]
    return "__memcpy" if name == "memcpy" else name


def _successors(
    instructions: tuple[Instruction, ...],
) -> dict[int, tuple[int, ...]]:
    addresses = {item.address for item in instructions}
    result: dict[int, tuple[int, ...]] = {}
    for index, instruction in enumerate(instructions):
        following = (
            instructions[index + 1].address
            if index + 1 < len(instructions)
            else None
        )
        target = _branch_target(instruction)
        candidates: list[int] = []
        if instruction.mnemonic in _TERMINATORS:
            pass
        elif instruction.mnemonic == "b":
            if target in addresses:
                candidates.append(target)
        elif (
            instruction.mnemonic.startswith("b.")
            or instruction.mnemonic in {"cbz", "cbnz", "tbz", "tbnz"}
        ):
            if target in addresses:
                candidates.append(target)
            if following is not None:
                candidates.append(following)
        elif following is not None:
            candidates.append(following)
        result[instruction.address] = tuple(dict.fromkeys(candidates))
    return result


def _destination_registers(instruction: Instruction) -> tuple[str, ...]:
    if (
        instruction.mnemonic in _NO_DESTINATION
        or instruction.mnemonic.startswith("b.")
    ):
        return ()
    if instruction.mnemonic in {"ldp", "ldpsw"}:
        match = re.match(
            r"^([wx]\d+),\s*([wx]\d+),", instruction.operands
        )
        if match:
            return tuple(_normalize_register(value) for value in match.groups())
    match = re.match(r"^([wx]\d+)\b", instruction.operands)
    return (_normalize_register(match.group(1)),) if match else ()


def _transfer(
    instruction: Instruction, state: dict[str, int]
) -> dict[str, int]:
    result = dict(state)
    if instruction.mnemonic in {"bl", "blr"}:
        for index in range(19):
            result.pop(f"x{index}", None)
        return result

    address = re.match(
        r"^([xw]\d+),\s*(?:0x)?([0-9a-fA-F]+)\b",
        instruction.operands,
    )
    if instruction.mnemonic in {"adr", "adrp"} and address:
        result[_normalize_register(address.group(1))] = int(
            address.group(2), 16
        )
        return result

    arithmetic = re.match(
        r"^([xw]\d+),\s*([xw]\d+|[xw]zr),\s*"
        r"(#(?:-?0x[0-9a-fA-F]+|-?\d+)|[xw]\d+|[xw]zr)\b",
        instruction.operands,
    )
    if instruction.mnemonic in {"add", "sub"} and arithmetic:
        destination, left, right = arithmetic.groups()
        left_value = (
            0
            if _normalize_register(left) == "xzr"
            else result.get(_normalize_register(left))
        )
        right_integer = _integer(right)
        right_value = (
            right_integer
            if right_integer is not None
            else (
                0
                if _normalize_register(right) == "xzr"
                else result.get(_normalize_register(right))
            )
        )
        normalized = _normalize_register(destination)
        if left_value is not None and right_value is not None:
            value = (
                left_value + right_value
                if instruction.mnemonic == "add"
                else left_value - right_value
            )
            if destination.startswith("w"):
                value &= 0xFFFFFFFF
            result[normalized] = value & 0xFFFFFFFFFFFFFFFF
        else:
            result.pop(normalized, None)
        return result

    move = re.match(
        r"^([xw]\d+),\s*(#(?:-?0x[0-9a-fA-F]+|-?\d+)|[xw]\d+|[xw]zr)\b",
        instruction.operands,
    )
    if instruction.mnemonic == "mov" and move:
        destination, source = move.groups()
        value = _integer(source)
        if value is None:
            value = (
                0
                if _normalize_register(source) == "xzr"
                else result.get(_normalize_register(source))
            )
        normalized = _normalize_register(destination)
        if value is None:
            result.pop(normalized, None)
        else:
            if destination.startswith("w"):
                value &= 0xFFFFFFFF
            result[normalized] = value & 0xFFFFFFFFFFFFFFFF
        return result

    for register in _destination_registers(instruction):
        result.pop(register, None)
    return result


def _memory_base(
    instruction: Instruction, state: dict[str, int]
) -> tuple[int | None, str | None, bool]:
    match = re.search(
        r"\[(x\d+)"
        r"(?:,\s*(#(?:-?0x[0-9a-fA-F]+|-?\d+)|x\d+)"
        r"(?:,\s*(?:lsl|uxtw)\s*#(\d+))?)?\]",
        instruction.operands,
    )
    if match is None:
        return None, None, False
    base_register, offset, shift = match.groups()
    base = state.get(_normalize_register(base_register))
    if base is None:
        return None, base_register, False
    if offset is None:
        return base, base_register, False
    immediate = _integer(offset)
    if immediate is not None:
        return base + immediate, base_register, False
    index = state.get(_normalize_register(offset))
    if index is None:
        return base, base_register, True
    return base + (index << int(shift or "0")), base_register, False


def _table_loads(
    disassembly: str,
    table_address: int,
    table_size: int,
    width: str,
) -> list[dict[str, Any]]:
    allowed = _LOADS_BY_WIDTH.get(width)
    element_size = _WIDTH_BYTES.get(width)
    if allowed is None or element_size is None:
        raise AuditError(f"unknown linked table load width: {width}")
    instructions = _instructions(disassembly)
    by_address = {item.address: item for item in instructions}
    successors = _successors(instructions)
    queue = collections.deque([(instructions[0].address, {})])
    visited: set[tuple[int, tuple[tuple[str, int], ...]]] = set()
    while queue:
        address, state = queue.popleft()
        key = (address, tuple(sorted(state.items())))
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > 4096:
            raise AuditError("linked table CFG state bound exceeded")
        instruction = by_address[address]
        if instruction.mnemonic in allowed:
            effective, base_register, dynamic_index = _memory_base(
                instruction, state
            )
            if (
                effective is not None
                and effective == table_address
                and element_size <= table_size
            ):
                return [
                    {
                        "instruction_address": f"0x{address:x}",
                        "mnemonic": instruction.mnemonic,
                        "base_register": base_register,
                        "effective_base": f"0x{effective:x}",
                        "table_address": f"0x{table_address:x}",
                        "table_size": table_size,
                        "dynamic_index": dynamic_index,
                        "width": width,
                    }
                ]
        next_state = _transfer(instruction, state)
        for successor in successors[address]:
            queue.append((successor, next_state))
    return []


def _memory_register(instruction: Instruction) -> str | None:
    match = re.search(r"\[(x\d+)", instruction.operands)
    return _normalize_register(match.group(1)) if match else None


def _taint_transfer(
    instruction: Instruction, tainted: frozenset[str]
) -> frozenset[str]:
    result = set(tainted)
    call = _call_target(instruction)
    if instruction.mnemonic in {"bl", "blr"}:
        result.difference_update(f"x{index}" for index in range(19))
        if call == "s22_fyg8_e1_head":
            result.add("x0")
        return frozenset(result)

    move = re.match(
        r"^([xw]\d+),\s*([xw]\d+|[xw]zr)\b",
        instruction.operands,
    )
    if instruction.mnemonic == "mov" and move:
        destination, source = map(_normalize_register, move.groups())
        result.discard(destination)
        if source in result:
            result.add(destination)
        return frozenset(result)

    arithmetic = re.match(
        r"^([xw]\d+),\s*([xw]\d+|[xw]zr),\s*"
        r"(?:#(?:-?0x[0-9a-fA-F]+|-?\d+)|([xw]\d+|[xw]zr))\b",
        instruction.operands,
    )
    if instruction.mnemonic in {"add", "sub"} and arithmetic:
        destination = _normalize_register(arithmetic.group(1))
        sources = {_normalize_register(arithmetic.group(2))}
        if arithmetic.group(3):
            sources.add(_normalize_register(arithmetic.group(3)))
        result.discard(destination)
        if sources & result:
            result.add(destination)
        return frozenset(result)

    multiply_add = re.match(
        r"^([xw]\d+),\s*([xw]\d+),\s*([xw]\d+),\s*([xw]\d+)\b",
        instruction.operands,
    )
    if instruction.mnemonic in {"madd", "msub"} and multiply_add:
        destination, *sources = (
            _normalize_register(value)
            for value in multiply_add.groups()
        )
        result.discard(destination)
        if set(sources) & result:
            result.add(destination)
        return frozenset(result)

    for register in _destination_registers(instruction):
        result.discard(register)
    return frozenset(result)


def _retained_store_addresses(
    instructions: tuple[Instruction, ...],
    successors: dict[int, tuple[int, ...]],
) -> frozenset[int]:
    by_address = {item.address: item for item in instructions}
    queue = collections.deque(
        [(instructions[0].address, frozenset())]
    )
    visited: set[tuple[int, frozenset[str]]] = set()
    stores: set[int] = set()
    while queue:
        address, tainted = queue.popleft()
        key = (address, tainted)
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > 4096:
            raise AuditError("linked retained-store CFG state bound exceeded")
        instruction = by_address[address]
        base = _memory_register(instruction)
        if instruction.mnemonic.startswith("st") and base in tainted:
            stores.add(address)
        next_taint = _taint_transfer(instruction, tainted)
        for successor in successors[address]:
            queue.append((successor, next_taint))
    return frozenset(stores)


def _reachable(
    start: int, successors: dict[int, tuple[int, ...]]
) -> frozenset[int]:
    pending = [start]
    seen: set[int] = set()
    while pending:
        address = pending.pop()
        if address in seen:
            continue
        seen.add(address)
        pending.extend(successors.get(address, ()))
    return frozenset(seen)


def _dominators(
    instructions: tuple[Instruction, ...],
    successors: dict[int, tuple[int, ...]],
) -> dict[int, frozenset[int]]:
    entry = instructions[0].address
    reachable = _reachable(entry, successors)
    predecessors = {address: set() for address in reachable}
    for address, targets in successors.items():
        if address not in reachable:
            continue
        for target in targets:
            if target in reachable:
                predecessors[target].add(address)
    dominators = {
        address: ({address} if address == entry else set(reachable))
        for address in reachable
    }
    changed = True
    while changed:
        changed = False
        for address in reachable:
            if address == entry:
                continue
            incoming = predecessors[address]
            value = (
                set.intersection(
                    *(dominators[parent] for parent in incoming)
                )
                if incoming
                else set()
            )
            value.add(address)
            if value != dominators[address]:
                dominators[address] = value
                changed = True
    return {
        address: frozenset(values)
        for address, values in dominators.items()
    }


def _failure_returns_negative(
    start: int,
    instructions: tuple[Instruction, ...],
    successors: dict[int, tuple[int, ...]],
    sensitive: frozenset[int],
) -> bool:
    by_address = {item.address: item for item in instructions}
    queue = collections.deque([(start, {})])
    visited: set[tuple[int, tuple[tuple[str, int], ...]]] = set()
    returns = 0
    while queue:
        address, state = queue.popleft()
        key = (address, tuple(sorted(state.items())))
        if key in visited:
            continue
        visited.add(key)
        if len(visited) > 4096 or address in sensitive:
            return False
        instruction = by_address[address]
        if instruction.mnemonic == "ret":
            returns += 1
            value = state.get("x0")
            if value is None or value < (1 << 63):
                return False
            continue
        next_state = _transfer(instruction, state)
        for successor in successors[address]:
            queue.append((successor, next_state))
    return returns > 0


def _audit_writer_guard(writer: str) -> dict[str, Any]:
    instructions = _instructions(writer)
    successors = _successors(instructions)
    validator_calls = [
        index
        for index, instruction in enumerate(instructions)
        if _call_target(instruction) == "s22_fyg8_e1_request_allowed"
    ]
    if len(validator_calls) != 1:
        raise AuditError("linked writer validator call cardinality changed")
    call_index = validator_calls[0]
    if call_index + 1 >= len(instructions):
        raise AuditError("linked writer validator call has no result guard")
    guard = instructions[call_index + 1]
    guard_match = re.match(
        r"^w0,\s*#0,\s*(?:0x)?([0-9a-fA-F]+)\b", guard.operands
    )
    if guard.mnemonic != "tbz" or guard_match is None:
        raise AuditError(
            "linked writer does not branch on validator w0 bit zero"
        )
    failure_target = int(guard_match.group(1), 16)
    if failure_target not in successors:
        raise AuditError("linked writer validator failure target is outside writer")

    sensitive_calls = {
        instruction.address: _call_target(instruction)
        for instruction in instructions
        if _call_target(instruction)
        in {"s22_fyg8_e1_head", "__flush_dcache_area"}
    }
    if "s22_fyg8_e1_head" not in sensitive_calls.values():
        raise AuditError("linked writer retained-head boundary is missing")
    if "__flush_dcache_area" not in sensitive_calls.values():
        raise AuditError("linked writer retained-flush boundary is missing")
    retained_stores = _retained_store_addresses(instructions, successors)
    if not retained_stores:
        raise AuditError("linked writer retained stores are not dataflow-visible")
    dominators = _dominators(instructions, successors)
    if any(
        guard.address not in dominators.get(address, ())
        for address in sensitive_calls
    ):
        raise AuditError(
            "linked writer validator guard does not dominate retained writes"
        )
    if any(
        guard.address not in dominators.get(address, ())
        for address in retained_stores
    ):
        raise AuditError(
            "linked writer validator guard does not dominate retained stores"
        )
    sensitive_addresses = frozenset(sensitive_calls) | retained_stores
    if not _failure_returns_negative(
        failure_target, instructions, successors, sensitive_addresses
    ):
        raise AuditError(
            "linked writer validator failure path does not return an error"
        )
    return {
        "validator_call_address": f"0x{instructions[call_index].address:x}",
        "validator_guard_address": f"0x{guard.address:x}",
        "failure_target": f"0x{failure_target:x}",
        "guard_dominates_retained_head": True,
        "guard_dominates_retained_flushes": True,
        "guard_dominates_retained_stores": True,
        "retained_store_addresses": [
            f"0x{address:x}" for address in sorted(retained_stores)
        ],
        "failure_path_returns_negative": True,
        "verified": True,
    }


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    required = (
        "s22_fyg8_e1_expected_item",
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_e1_write",
    )
    if any(not isinstance(disassembly.get(name), str) for name in required):
        raise AuditError("P2.53 linked validator evidence is incomplete")

    writer_calls = calls.get("s22_fyg8_e1_write")
    request_calls = calls.get("s22_fyg8_e1_request_allowed")
    if not isinstance(writer_calls, list) or not isinstance(request_calls, list):
        raise AuditError("P2.53 linked validator call evidence is incomplete")
    if "s22_fyg8_e1_request_allowed" not in writer_calls:
        raise AuditError("P2.53 linked writer does not call the request validator")
    if (
        "s22_fyg8_e1_expected_item" not in request_calls
        or "s22_fyg8_e1_detail_allowed" not in request_calls
    ):
        raise AuditError(
            "P2.53 linked request validator does not call both validators"
        )

    expected_tables = p252.linked_table_bytes()
    table_requirements = (
        (
            "item",
            "s22_fyg8_e1_expected_item",
            "s22_fyg8_e2_items",
            "byte",
        ),
        (
            "classifier_stage",
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_e2_classifier_stages",
            "byte",
        ),
        (
            "classifier_detail",
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_e2_classifier_details",
            "halfword",
        ),
    )
    table_loads: dict[str, list[dict[str, Any]]] = {}
    for label, function, table, width in table_requirements:
        address = symbol_addresses.get(table)
        expected = expected_tables.get(table)
        if not isinstance(address, int) or not isinstance(expected, bytes):
            raise AuditError(f"P2.53 linked table evidence is missing: {table}")
        found = _table_loads(
            disassembly[function], address, len(expected), width
        )
        if not found:
            raise AuditError(
                f"P2.53 linked validator does not load the {label} table"
            )
        table_loads[label] = found

    stale_compare = re.compile(r"\bcmp\s+[wx]\d+,\s*#(?:0x)?8\b")
    if any(
        stale_compare.search(disassembly[name])
        for name in (
            "s22_fyg8_e1_expected_item",
            "s22_fyg8_e1_request_allowed",
            "s22_fyg8_e1_write",
        )
    ):
        raise AuditError(
            "P2.53 linked validator retains the stale eight-item compare"
        )
    writer_guard = _audit_writer_guard(disassembly["s22_fyg8_e1_write"])

    return {
        "audit_adapter": ADAPTER_ID,
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "item_validator_loads_item_table": True,
        "validator_loads_classifier_stage_table": True,
        "validator_loads_classifier_detail_table": True,
        "accepted_load_lowerings": table_loads,
        "writer_guard": writer_guard,
        "stale_eight_item_compare_absent": True,
        "verified": True,
    }


def check(args) -> dict[str, Any]:
    result = repro.check(args)
    linked = result.get("linked_audit")
    if (
        not isinstance(linked, dict)
        or linked.get("audit_adapter") != ADAPTER_ID
        or linked.get("source_contract_validator", {}).get("verified")
        is not True
    ):
        raise AuditError("P2.53 linked validator adapter was not applied")
    return result


def main(argv: list[str] | None = None) -> int:
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
    raise SystemExit(main())
