#!/usr/bin/env python3
"""P2.90 post-build proof by host exhaustion and direct ELF table data."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import s22plus_fyg8_p288_postbuild_linked_audit as inherited
import s22plus_fyg8_p290_build_repro_check as repro
import s22plus_fyg8_p290_linked_audit as linked
import s22plus_fyg8_p290_source_contract as p290


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = linked.ADAPTER_ID
IMPLEMENTATION_ID = (
    "s22plus-fyg8-p290-source-exhaustive-and-elf-data-audit-v1"
)
EXPECTED_SOURCE_CONTRACT_ID = p290.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p290_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = linked.LINKED_VALIDATOR_SYMBOLS
LINKED_DATA_SYMBOLS = (
    "s22_fyg8_e2_sequence",
    "s22_fyg8_e2_items",
    "s22_fyg8_e2_kinds",
    "s22_fyg8_p290_detail_rules",
)
HOST_GENERATIONS = len(p290.spec.POSITIONS) + 1
PAIR_DOMAIN_SIZE = 1 << 16
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p290.spec.POSITIONS)
HOST_OUTPUT = (
    f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n"
).encode("ascii")

AuditError = linked.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = linked.require_gnu_aarch64_tools
linked_table_storage_bytes = linked.linked_table_storage_bytes
normalize_linked_table_storage = linked.normalize_linked_table_storage


def _added_span(patch: bytes, begin: bytes, end: bytes) -> bytes:
    try:
        return inherited._added_span(  # noqa: SLF001
            patch, begin, end
        )
    except inherited.AuditError as exc:
        raise AuditError(str(exc)) from exc


def production_validator_source(patch: bytes) -> bytes:
    structures = _added_span(
        patch,
        b"+struct s22_fyg8_e1_request {\n",
        b"+static const u8 s22_fyg8_e1_long_family[]",
    )
    sequences = _added_span(
        patch,
        b"+static const u8 s22_fyg8_e1a_sequence[]",
        b"+static bool s22_fyg8_e1_parse_reg(",
    )
    selector = _added_span(
        patch,
        b"+static const u8 *s22_fyg8_e1_sequence(",
        b"+static noinline __used bool s22_fyg8_e1_expected_item(",
    )
    expected_item = _added_span(
        patch,
        b"+static noinline __used bool s22_fyg8_e1_expected_item(",
        b"+struct s22_fyg8_p290_detail_rule {\n",
    )
    classifiers = _added_span(
        patch,
        b"+struct s22_fyg8_p290_detail_rule {\n",
        b"+static void s22_fyg8_e1_record_entry(",
    )
    required = (
        b"static const u8 s22_fyg8_e2_sequence[] __used",
        b"static const u8 s22_fyg8_e2_items[] __used",
        b"static const u8 s22_fyg8_e2_kinds[] __used",
        b"static noinline __used bool s22_fyg8_e1_expected_item(",
        b"static noinline __used bool s22_fyg8_e1_detail_allowed(",
        b"static noinline __used bool s22_fyg8_e1_request_allowed(",
        b"request->stage != sequence[ordinal]",
        b"request->item_index != expected_item",
    )
    source = structures + sequences + selector + expected_item + classifiers
    if any(source.count(token) != 1 for token in required):
        raise AuditError("P2.90 production validator source is incomplete")
    return source


def host_validator_tu(patch: bytes) -> bytes:
    production = production_validator_source(patch).decode("ascii")
    stages = ", ".join(
        f"0x{position.stage:02x}" for position in p290.spec.POSITIONS
    )
    items = ", ".join(
        f"0x{position.item_index:02x}"
        for position in p290.spec.POSITIONS
    )
    prelude = f"""
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint16_t __le16;
typedef uint32_t __le32;

#define __packed __attribute__((packed))
#define noinline __attribute__((noinline))
#define __used __attribute__((used))
#define ARRAY_SIZE(value) (sizeof(value) / sizeof((value)[0]))
#define READ_ONCE(value) (value)
#define le16_to_cpu(value) (value)
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "P2.90 host validator requires a little-endian execution host"
#endif
#define S22_FYG8_E1_HEADER_SIZE {p290.decoder.model.LONG_HEADER_SIZE}
#define S22_FYG8_E1_PROFILE_E1A 1U
#define S22_FYG8_E1_PROFILE_E1B 2U
#define S22_FYG8_E1_PROFILE_E2 3U
#define S22_FYG8_E1_PROGRESS 0U
#define S22_FYG8_E1_SUCCESS 1U
#define S22_FYG8_E1_FAILURE 2U
"""
    oracle = (
        f"static const u8 p290_expected_stage[] = {{{stages}}};\n"
        f"static const u8 p290_expected_item[] = {{{items}}};\n"
    )
    main = f"""
int main(void)
{{
    struct s22_fyg8_e1_request request;
    uint64_t checked = 0;
    uint64_t accepted = 0;
    unsigned int generation;
    unsigned int stage;
    unsigned int item;

    memset(&request, 0, sizeof(request));
    request.profile = S22_FYG8_E1_PROFILE_E2;
    request.detail = 0;
    for (generation = 0; generation < {HOST_GENERATIONS}; ++generation) {{
        s22_fyg8_e1_state.generation = (u8)generation;
        request.outcome = generation + 1U == {HOST_ACCEPT_COUNT}
            ? S22_FYG8_E1_SUCCESS : S22_FYG8_E1_PROGRESS;
        for (stage = 0; stage < 256U; ++stage) {{
            request.stage = (u8)stage;
            for (item = 0; item < 256U; ++item) {{
                bool expected;
                bool actual;

                request.item_index = (u8)item;
                expected = generation < {HOST_ACCEPT_COUNT} &&
                    request.stage == p290_expected_stage[generation] &&
                    request.item_index == p290_expected_item[generation];
                actual = s22_fyg8_e1_request_allowed(&request);
                ++checked;
                if (actual)
                    ++accepted;
                if (actual != expected) {{
                    fprintf(stderr,
                        "mismatch generation=%u stage=%u item=%u "
                        "actual=%u expected=%u\\n",
                        generation, stage, item, actual, expected);
                    return 10;
                }}
            }}
        }}
    }}
    if (checked != {HOST_CASE_COUNT} || accepted != {HOST_ACCEPT_COUNT})
        return 11;
    printf("checked=%llu accepted=%llu\\n",
        (unsigned long long)checked, (unsigned long long)accepted);
    return 0;
}}
"""
    return (prelude + production + oracle + main).encode("ascii")


def run_host_validator_tu(tu: bytes) -> dict[str, Any]:
    previous = {
        "HOST_GENERATIONS": inherited.HOST_GENERATIONS,
        "HOST_CASE_COUNT": inherited.HOST_CASE_COUNT,
        "HOST_ACCEPT_COUNT": inherited.HOST_ACCEPT_COUNT,
        "HOST_OUTPUT": inherited.HOST_OUTPUT,
    }
    inherited.HOST_GENERATIONS = HOST_GENERATIONS
    inherited.HOST_CASE_COUNT = HOST_CASE_COUNT
    inherited.HOST_ACCEPT_COUNT = HOST_ACCEPT_COUNT
    inherited.HOST_OUTPUT = HOST_OUTPUT
    try:
        return inherited.run_host_validator_tu(tu)
    except inherited.AuditError as exc:
        raise AuditError(str(exc)) from exc
    finally:
        for name, value in previous.items():
            setattr(inherited, name, value)


def host_native_exhaustive(root: Path) -> dict[str, Any]:
    patch = p290.generate(root)["patch"]
    result = run_host_validator_tu(host_validator_tu(patch))
    result["identity_patch"] = p290.receipt(patch)
    result["production_validator_source"] = p290.receipt(
        production_validator_source(patch)
    )
    return result


def verify_linked_table_data(
    vmlinux: bytes, expected: dict[str, bytes]
) -> dict[str, Any]:
    if tuple(expected) != LINKED_DATA_SYMBOLS:
        raise AuditError("P2.90 expected linked table set differs")
    tables: dict[str, Any] = {}
    for symbol_name in LINKED_DATA_SYMBOLS:
        expected_bytes = expected[symbol_name]
        try:
            actual = inherited.elf_symbol_bytes(vmlinux, symbol_name)
        except inherited.AuditError as exc:
            raise AuditError(str(exc)) from exc
        if actual != expected_bytes:
            raise AuditError(
                f"P2.90 linked table bytes differ: {symbol_name}"
            )
        tables[symbol_name] = {
            "symbol_size": len(actual),
            "symbol_receipt": p290.receipt(actual),
            "expected_receipt": p290.receipt(expected_bytes),
            "byte_identical": True,
        }
    sequence = expected["s22_fyg8_e2_sequence"]
    items = expected["s22_fyg8_e2_items"]
    kinds = expected["s22_fyg8_e2_kinds"]
    if (
        len(sequence) != len(p290.spec.POSITIONS)
        or len(items) != len(sequence)
        or len(kinds) != len(sequence)
        or tuple(zip(sequence, items, strict=True))
        != p290.spec.POSITION_SEQUENCE
    ):
        raise AuditError("P2.90 linked position-table encoding differs")
    return {
        "symbols": tables,
        "position_count": len(p290.spec.POSITIONS),
        "position_pairs_unique": (
            len(set(p290.spec.POSITION_SEQUENCE))
            == len(p290.spec.POSITION_SEQUENCE)
        ),
        "terminal_generation": p290.spec.TERMINAL_GENERATION,
        "direct_elf_symbol_data": True,
        "objdump_text_not_used": True,
        "stage_and_item_bytes_equal_position_sequence": True,
        "kind_and_detail_rule_bytes_equal_source_contract": True,
        "verified": True,
    }


def linked_table_data(args, result: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN001
    root = repro.candidate_contract.intent.repo_root()
    directory = repro.candidate_contract.intent.resolve(root, args.build_a)
    vmlinux = repro.candidate_contract.stable_read(
        directory / "vmlinux",
        "P2.90 direct-ELF linked vmlinux",
        repro.ARTIFACT_LIMITS["vmlinux"],
    )
    receipt = repro.candidate_contract.intent.receipt(vmlinux)
    expected_receipt = (
        result.get("build_a", {}).get("artifacts", {}).get("vmlinux")
    )
    if receipt != expected_receipt:
        raise AuditError(
            "P2.90 linked vmlinux changed after reproducibility audit"
        )
    proof = verify_linked_table_data(vmlinux, p290.linked_table_bytes())
    proof["vmlinux"] = receipt
    return proof


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    return linked.audit_linked_validator(
        disassembly, calls, symbol_addresses
    )


def check(args) -> dict[str, Any]:  # noqa: ANN001
    tool_identity = require_gnu_aarch64_tools(args)
    result = repro.check(args)
    linked_result = result.get("linked_audit")
    validator = (
        linked_result.get("source_contract_validator")
        if isinstance(linked_result, dict)
        else None
    )
    if (
        not isinstance(linked_result, dict)
        or linked_result.get("audit_adapter") != ADAPTER_ID
        or linked_result.get("source_contract_semantics", {}).get("verified")
        is not True
        or not isinstance(validator, dict)
        or validator.get("validator_semantics_pending_host_exhaustive")
        is not True
    ):
        raise AuditError("P2.90 linked adapter was not applied")
    root = repro.candidate_contract.intent.repo_root()
    host_proof = host_native_exhaustive(root)
    table_proof = linked_table_data(args, result)
    validator["host_native_exhaustive"] = host_proof
    validator["linked_table_data"] = table_proof
    validator["validator_semantics_pending_host_exhaustive"] = False
    validator["verified"] = True
    linked_result["gnu_aarch64_tools"] = tool_identity
    linked_result["postbuild_audit"] = {
        "implementation_id": IMPLEMENTATION_ID,
        "semantic_adapter_id": ADAPTER_ID,
        "host_native_exhaustive": host_proof,
        "linked_table_data": table_proof,
        "verified": True,
    }
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
    sys.modules.setdefault(ADAPTER_MODULE, sys.modules[__name__])
    raise SystemExit(main())
