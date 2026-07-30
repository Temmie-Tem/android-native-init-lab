#!/usr/bin/env python3
"""Post-build P2.88 audit using source semantics and direct ELF data."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p288_build_repro_check as repro
import s22plus_fyg8_p288_change_freeze as freeze
import s22plus_fyg8_p288_linked_audit as legacy
import s22plus_fyg8_p288_source_contract as p288


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET
ADAPTER_ID = legacy.ADAPTER_ID
IMPLEMENTATION_ID = (
    "s22plus-fyg8-p288-source-exhaustive-and-elf-data-audit-v3"
)
EXPECTED_SOURCE_CONTRACT_ID = p288.CONTRACT_ID
ADAPTER_MODULE = "s22plus_fyg8_p288_postbuild_linked_audit"
LINKED_VALIDATOR_SYMBOLS = legacy.LINKED_VALIDATOR_SYMBOLS

SUPPORT_BASE_COMMIT = "e7a88ff320e15021d0dae0ba10c5cec5e382da6f"
EXPECTED_SUPPORT_PATHS = (
    "tests/test_s22plus_fyg8_p288_postbuild_linked_audit.py",
    (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_candidate_static_checker.py"
    ),
    (
        "workspace/public/src/scripts/revalidation/"
        "s22plus_fyg8_p288_postbuild_linked_audit.py"
    ),
)

HOST_GENERATIONS = 104
PAIR_DOMAIN_SIZE = 1 << 16
HOST_CASE_COUNT = HOST_GENERATIONS * PAIR_DOMAIN_SIZE
HOST_ACCEPT_COUNT = len(p288.spec.POSITIONS)
HOST_OUTPUT = (
    f"checked={HOST_CASE_COUNT} accepted={HOST_ACCEPT_COUNT}\n"
).encode("ascii")
LINKED_DATA_SYMBOLS = (
    "s22_fyg8_e2_sequence",
    "s22_fyg8_e2_items",
    "s22_fyg8_e2_kinds",
    "s22_fyg8_p288_detail_rules",
)

AuditError = legacy.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = legacy.require_gnu_aarch64_tools
linked_table_storage_bytes = legacy.linked_table_storage_bytes
normalize_linked_table_storage = legacy.normalize_linked_table_storage


def _added_span(patch: bytes, begin: bytes, end: bytes) -> bytes:
    lines = patch.splitlines(keepends=True)
    starts = tuple(
        index for index, line in enumerate(lines) if line.startswith(begin)
    )
    stops = tuple(
        index for index, line in enumerate(lines) if line.startswith(end)
    )
    if len(starts) != 1 or len(stops) != 1 or starts[0] >= stops[0]:
        raise AuditError(
            "P2.88 production validator source span is not unique"
        )
    selected = lines[starts[0] : stops[0]]
    if any(not line.startswith(b"+") for line in selected):
        raise AuditError(
            "P2.88 production validator span contains non-added source"
        )
    return b"".join(line[1:] for line in selected)


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
        b"+struct s22_fyg8_p288_detail_rule {\n",
    )
    classifiers = _added_span(
        patch,
        b"+struct s22_fyg8_p288_detail_rule {\n",
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
        raise AuditError("P2.88 production validator source is incomplete")
    return source


def _c_u8_array(name: str, values: tuple[int, ...]) -> str:
    body = ", ".join(f"0x{value:02x}" for value in values)
    return f"static const u8 {name}[] = {{{body}}};\n"


def host_validator_tu(patch: bytes) -> bytes:
    production = production_validator_source(patch).decode("ascii")
    expected_stages = tuple(
        position.stage for position in p288.spec.POSITIONS
    )
    expected_items = tuple(
        position.item_index for position in p288.spec.POSITIONS
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
#error "P2.88 host validator requires a little-endian execution host"
#endif
#define S22_FYG8_E1_HEADER_SIZE {p288.decoder.model.LONG_HEADER_SIZE}
#define S22_FYG8_E1_PROFILE_E1A 1U
#define S22_FYG8_E1_PROFILE_E1B 2U
#define S22_FYG8_E1_PROFILE_E2 3U
#define S22_FYG8_E1_PROGRESS 0U
#define S22_FYG8_E1_SUCCESS 1U
#define S22_FYG8_E1_FAILURE 2U
"""
    oracle = (
        _c_u8_array("p288_expected_stage", expected_stages)
        + _c_u8_array("p288_expected_item", expected_items)
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
                    request.stage == p288_expected_stage[generation] &&
                    request.item_index == p288_expected_item[generation];
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


def _stable_tool(path: Path, label: str) -> dict[str, Any]:
    data = repro.candidate_contract.stable_read(
        path, label, 128 * 1024 * 1024
    )
    return repro.candidate_contract.intent.receipt(data)


def run_host_validator_tu(tu: bytes) -> dict[str, Any]:
    compiler_name = shutil.which("cc")
    if compiler_name is None:
        raise AuditError("P2.88 host C compiler is unavailable")
    compiler = Path(compiler_name).resolve()
    compiler_receipt = _stable_tool(compiler, "P2.88 host C compiler")
    version = subprocess.run(
        (str(compiler), "--version"),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
    )
    if version.returncode != 0 or not version.stdout:
        raise AuditError("P2.88 host C compiler identity is unavailable")
    with tempfile.TemporaryDirectory(
        prefix="s22-p288-host-validator-"
    ) as temporary:
        source = Path(temporary) / "validator.c"
        binary = Path(temporary) / "validator"
        source.write_bytes(tu)
        compiled = subprocess.run(
            (
                str(compiler),
                "-std=c11",
                "-O2",
                "-fno-lto",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(binary),
            ),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )
        if compiled.returncode != 0:
            raise AuditError(
                "P2.88 host validator compile failed: "
                + compiled.stdout[-2000:].decode("utf-8", "replace")
            )
        executed = subprocess.run(
            (str(binary),),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    if (
        executed.returncode != 0
        or executed.stdout != HOST_OUTPUT
        or executed.stderr
    ):
        detail = (executed.stdout + executed.stderr)[-2000:]
        raise AuditError(
            "P2.88 host validator exhaustive evaluation failed: "
            + detail.decode("utf-8", "replace")
        )
    return {
        "compiler": compiler_receipt,
        "compiler_version_sha256": hashlib.sha256(version.stdout).hexdigest(),
        "translation_unit": repro.candidate_contract.intent.receipt(tu),
        "generation_domain": [0, HOST_GENERATIONS - 1],
        "stage_domain": [0, 255],
        "item_index_domain": [0, 255],
        "checked_pairs": HOST_CASE_COUNT,
        "accepted_pairs": HOST_ACCEPT_COUNT,
        "expected_output": HOST_OUTPUT.decode("ascii").strip(),
        "same_production_functions_unmodified": True,
        "register_allocation_independent": True,
        "exhaustive_pair_domain": True,
        "verified": True,
    }


def host_native_exhaustive(root: Path) -> dict[str, Any]:
    patch = p288.generate(root)["patch"]
    result = run_host_validator_tu(host_validator_tu(patch))
    result["identity_patch"] = p288.receipt(patch)
    result["production_validator_source"] = p288.receipt(
        production_validator_source(patch)
    )
    return result


def _section_headers(data: bytes) -> tuple[list[tuple[int, ...]], int]:
    if (
        len(data) < 64
        or data[:4] != b"\x7fELF"
        or data[4] != 2
        or data[5] != 1
    ):
        raise AuditError("P2.88 linked vmlinux is not ELF64 little-endian")
    header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    section_offset = header[5]
    section_size = header[10]
    section_count = header[11]
    string_index = header[12]
    if section_size != 64 or not section_count:
        raise AuditError("P2.88 linked ELF section table is unsupported")
    end = section_offset + section_size * section_count
    if section_offset < 64 or end > len(data):
        raise AuditError("P2.88 linked ELF section table is out of bounds")
    sections = [
        struct.unpack_from("<IIQQQQIIQQ", data, section_offset + 64 * index)
        for index in range(section_count)
    ]
    if string_index >= section_count:
        raise AuditError("P2.88 linked ELF string section is invalid")
    return sections, string_index


def _slice(data: bytes, offset: int, size: int, label: str) -> bytes:
    if (
        isinstance(offset, bool)
        or isinstance(size, bool)
        or offset < 0
        or size < 0
        or offset + size > len(data)
    ):
        raise AuditError(f"P2.88 linked ELF {label} is out of bounds")
    return data[offset : offset + size]


def _c_string(table: bytes, offset: int) -> str:
    if not 0 <= offset < len(table):
        raise AuditError("P2.88 linked ELF string offset is invalid")
    end = table.find(b"\0", offset)
    if end < 0:
        raise AuditError("P2.88 linked ELF string is unterminated")
    try:
        return table[offset:end].decode("ascii")
    except UnicodeError as exc:
        raise AuditError("P2.88 linked ELF symbol is not ASCII") from exc


def elf_symbol_bytes(data: bytes, symbol_name: str) -> bytes:
    sections, _string_index = _section_headers(data)
    matches: list[bytes] = []
    for section in sections:
        (
            _name,
            section_type,
            _flags,
            _address,
            offset,
            size,
            link,
            _info,
            _alignment,
            entry_size,
        ) = section
        if section_type != 2:
            continue
        if entry_size != 24 or link >= len(sections):
            raise AuditError("P2.88 linked ELF symbol table is malformed")
        string_section = sections[link]
        strings = _slice(
            data,
            string_section[4],
            string_section[5],
            "symbol strings",
        )
        symbols = _slice(data, offset, size, "symbol table")
        if len(symbols) % 24:
            raise AuditError("P2.88 linked ELF symbol table is truncated")
        for cursor in range(0, len(symbols), 24):
            name, _info, _other, index, value, symbol_size = (
                struct.unpack_from("<IBBHQQ", symbols, cursor)
            )
            if _c_string(strings, name) != symbol_name:
                continue
            if index == 0 or index >= len(sections) or not symbol_size:
                raise AuditError("P2.88 linked ELF symbol placement is invalid")
            target = sections[index]
            relative = value - target[3]
            if relative < 0 or relative + symbol_size > target[5]:
                raise AuditError("P2.88 linked ELF symbol exceeds its section")
            matches.append(
                _slice(
                    data,
                    target[4] + relative,
                    symbol_size,
                    f"symbol {symbol_name}",
                )
            )
    if len(matches) != 1:
        raise AuditError(
            f"P2.88 linked ELF symbol cardinality differs: "
            f"{symbol_name}={len(matches)}"
        )
    return matches[0]


def verify_linked_table_data(
    vmlinux: bytes, expected: dict[str, bytes]
) -> dict[str, Any]:
    if tuple(expected) != LINKED_DATA_SYMBOLS:
        raise AuditError("P2.88 expected linked table set differs")
    tables: dict[str, Any] = {}
    for symbol_name in LINKED_DATA_SYMBOLS:
        expected_bytes = expected[symbol_name]
        actual = elf_symbol_bytes(vmlinux, symbol_name)
        if actual != expected_bytes:
            raise AuditError(
                f"P2.88 linked table bytes differ: {symbol_name}"
            )
        tables[symbol_name] = {
            "symbol_size": len(actual),
            "symbol_receipt": p288.receipt(actual),
            "expected_receipt": p288.receipt(expected_bytes),
            "byte_identical": True,
        }
    sequence = expected["s22_fyg8_e2_sequence"]
    items = expected["s22_fyg8_e2_items"]
    kinds = expected["s22_fyg8_e2_kinds"]
    if (
        len(sequence) != 103
        or len(items) != len(sequence)
        or len(kinds) != len(sequence)
        or tuple(zip(sequence, items, strict=True))
        != p288.spec.POSITION_SEQUENCE
    ):
        raise AuditError("P2.88 linked position-table encoding differs")
    return {
        "symbols": tables,
        "position_count": len(p288.spec.POSITIONS),
        "position_pairs_unique": (
            len(set(p288.spec.POSITION_SEQUENCE))
            == len(p288.spec.POSITION_SEQUENCE)
        ),
        "terminal_generation": p288.spec.TERMINAL_GENERATION,
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
        "P2.88 direct-ELF linked vmlinux",
        repro.ARTIFACT_LIMITS["vmlinux"],
    )
    receipt = repro.candidate_contract.intent.receipt(vmlinux)
    expected_receipt = (
        result.get("build_a", {}).get("artifacts", {}).get("vmlinux")
    )
    if receipt != expected_receipt:
        raise AuditError(
            "P2.88 linked vmlinux changed after reproducibility audit"
        )
    proof = verify_linked_table_data(vmlinux, p288.linked_table_bytes())
    proof["vmlinux"] = receipt
    return proof


def _support_delta(root: Path) -> dict[str, Any]:
    derived = freeze.git_derived_changed_paths(root, SUPPORT_BASE_COMMIT)
    if derived != EXPECTED_SUPPORT_PATHS:
        raise AuditError(
            "P2.88 post-build support delta differs: "
            f"expected={EXPECTED_SUPPORT_PATHS} actual={derived}"
        )
    direct_sources = {
        path.as_posix()
        for path in freeze.planned_direct_source_paths().values()
    }
    overlap = sorted(set(derived) & direct_sources)
    if overlap:
        raise AuditError(
            "P2.88 post-build support delta touches SOURCE_KEYS: "
            + ",".join(overlap)
        )
    materials = {}
    for relative in derived:
        data = repro.candidate_contract.stable_read(
            root / relative,
            f"P2.88 post-build support {relative}",
            16 * 1024 * 1024,
        )
        materials[relative] = repro.candidate_contract.intent.receipt(data)
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    status = subprocess.run(
        ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if (
        head.returncode != 0
        or re.fullmatch(r"[0-9a-f]{40}", head.stdout.strip()) is None
        or status.returncode != 0
        or status.stdout
        or head.stdout.strip() == SUPPORT_BASE_COMMIT
    ):
        raise AuditError(
            "P2.88 post-build support checkout is not a clean committed delta"
        )
    return {
        "base_commit": SUPPORT_BASE_COMMIT,
        "head_commit": head.stdout.strip(),
        "changed_paths": list(derived),
        "source_key_path_overlap": [],
        "source_key_count": len(p288.SOURCE_KEYS),
        "materials": materials,
        "verified": True,
    }


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    _symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    required = (
        "s22_fyg8_e1_expected_item",
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_p288_tuple_allowed",
        "s22_fyg8_e1_write",
    )
    if any(not isinstance(disassembly.get(name), str) for name in required):
        raise AuditError("P2.88 linked validator evidence is incomplete")
    legacy._require_call(
        calls, "s22_fyg8_e1_write", "s22_fyg8_e1_request_allowed"
    )
    legacy._require_call(
        calls,
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_expected_item",
    )
    legacy._require_call(
        calls,
        "s22_fyg8_e1_request_allowed",
        "s22_fyg8_e1_detail_allowed",
    )
    legacy._require_call(
        calls,
        "s22_fyg8_e1_detail_allowed",
        "s22_fyg8_p288_tuple_allowed",
    )
    return {
        "audit_adapter": ADAPTER_ID,
        "audit_implementation": IMPLEMENTATION_ID,
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "detail_calls_tuple_validator": True,
        "writer_guard": cfg_audit._audit_writer_guard(
            disassembly["s22_fyg8_e1_write"]
        ),
        "register_specific_validator_patterns_used": False,
        "validator_semantics_pending_host_exhaustive": True,
        "verified": False,
    }


def check(args) -> dict[str, Any]:  # noqa: ANN001
    tool_identity = require_gnu_aarch64_tools(args)
    previous = repro.LINKED_VALIDATOR_ADAPTERS.get(
        EXPECTED_SOURCE_CONTRACT_ID
    )
    if previous not in {
        None,
        legacy.ADAPTER_MODULE,
        ADAPTER_MODULE,
    }:
        raise AuditError("P2.88 linked adapter registry conflicts")
    repro.LINKED_VALIDATOR_ADAPTERS[EXPECTED_SOURCE_CONTRACT_ID] = (
        ADAPTER_MODULE
    )
    try:
        result = repro.check(args)
    finally:
        if previous is None:
            repro.LINKED_VALIDATOR_ADAPTERS.pop(
                EXPECTED_SOURCE_CONTRACT_ID, None
            )
        else:
            repro.LINKED_VALIDATOR_ADAPTERS[
                EXPECTED_SOURCE_CONTRACT_ID
            ] = previous
    linked = result.get("linked_audit")
    validator = (
        linked.get("source_contract_validator")
        if isinstance(linked, dict)
        else None
    )
    if (
        not isinstance(linked, dict)
        or linked.get("audit_adapter") != ADAPTER_ID
        or linked.get("source_contract_semantics", {}).get("verified")
        is not True
        or not isinstance(validator, dict)
        or validator.get("validator_semantics_pending_host_exhaustive")
        is not True
    ):
        raise AuditError("P2.88 post-build linked adapter was not applied")
    root = repro.candidate_contract.intent.repo_root()
    host_proof = host_native_exhaustive(root)
    table_proof = linked_table_data(args, result)
    validator["host_native_exhaustive"] = host_proof
    validator["linked_table_data"] = table_proof
    validator["validator_semantics_pending_host_exhaustive"] = False
    validator["verified"] = True
    linked["gnu_aarch64_tools"] = tool_identity
    linked["postbuild_audit"] = {
        "implementation_id": IMPLEMENTATION_ID,
        "semantic_adapter_id": ADAPTER_ID,
        "host_native_exhaustive": host_proof,
        "linked_table_data": table_proof,
        "support_delta": _support_delta(root),
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
