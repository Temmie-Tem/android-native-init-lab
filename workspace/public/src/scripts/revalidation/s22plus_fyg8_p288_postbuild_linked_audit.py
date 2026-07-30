#!/usr/bin/env python3
"""Post-build P2.88 audit for the Full-LTO switch-table lowering."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import s22plus_fyg8_p253_linked_audit as cfg_audit
import s22plus_fyg8_p282_linked_audit as p282_audit
import s22plus_fyg8_p288_build_repro_check as repro
import s22plus_fyg8_p288_change_freeze as freeze
import s22plus_fyg8_p288_linked_audit as legacy
import s22plus_fyg8_p288_source_contract as p288


SCHEMA = repro.SCHEMA
VERDICT = repro.VERDICT
TARGET = repro.TARGET

# The immutable candidate builder accepts this semantic adapter identity.  The
# implementation identity below distinguishes this post-build verifier and is
# included, with its exact material receipt, in the result it emits.
ADAPTER_ID = legacy.ADAPTER_ID
IMPLEMENTATION_ID = (
    "s22plus-fyg8-p288-postbuild-switch-table-linked-audit-v2"
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

AuditError = legacy.AuditError
SourceContractError = AuditError
require_gnu_aarch64_tools = legacy.require_gnu_aarch64_tools
linked_table_storage_bytes = legacy.linked_table_storage_bytes
normalize_linked_table_storage = legacy.normalize_linked_table_storage


def _instructions(disassembly: str) -> tuple[str, ...]:
    rows: list[str] = []
    for line in disassembly.splitlines():
        match = re.match(
            r"^\s*[0-9a-fA-F]+:\s+[0-9a-fA-F]{8}\s+(.+?)\s*$",
            line,
        )
        if match is not None:
            rows.append(match.group(1).split("//", 1)[0].strip())
    if not rows:
        raise AuditError("P2.88 request validator disassembly is empty")
    return tuple(rows)


def _unique_index(
    rows: tuple[str, ...],
    pattern: str,
    label: str,
    *,
    start: int = 0,
    stop: int | None = None,
) -> int:
    upper = len(rows) if stop is None else stop
    matches = tuple(
        index
        for index in range(start, upper)
        if re.fullmatch(pattern, rows[index])
    )
    if len(matches) != 1:
        raise AuditError(
            f"P2.88 switch-table {label} is not unique: {len(matches)}"
        )
    return matches[0]


def _indexed_table_base(
    rows: tuple[str, ...],
    destination: str,
    label: str,
) -> tuple[int, int]:
    matches: list[tuple[int, int]] = []
    load_pattern = re.compile(
        rf"ldr\s+{destination},\s*\[x9,\s*x8,\s*lsl\s+#3\]"
    )
    for index in range(2, len(rows)):
        if load_pattern.fullmatch(rows[index]) is None:
            continue
        page = re.fullmatch(
            r"adrp\s+x9,\s*([0-9a-fA-F]+)(?:\s+<[^>]+>)?",
            rows[index - 2],
        )
        offset = re.fullmatch(
            r"add\s+x9,\s*x9,\s*#(0x[0-9a-fA-F]+|\d+)",
            rows[index - 1],
        )
        if page is not None and offset is not None:
            matches.append(
                (int(page.group(1), 16) + int(offset.group(1), 0), index)
            )
    if len(matches) != 1:
        raise AuditError(
            f"P2.88 switch-table {label} base is not unique: "
            f"{len(matches)}"
        )
    return matches[0]


def _switch_table_structure(disassembly: str) -> dict[str, Any]:
    rows = _instructions(disassembly)
    profile = _unique_index(
        rows,
        r"ldrb\s+w0,\s*\[x0,\s*#0x5\]",
        "request profile load",
    )
    subtract = _unique_index(
        rows,
        r"sub\s+w9,\s*w0,\s*#0x1",
        "profile bias",
        start=profile + 1,
    )
    upper = _unique_index(
        rows,
        r"cmp\s+w9,\s*#0x2",
        "profile upper bound",
        start=subtract + 1,
    )
    index = _unique_index(
        rows,
        r"sxtb\s+x8,\s*w9",
        "profile index materialization",
        start=upper + 1,
    )
    reject_profile = _unique_index(
        rows,
        r"b\.hi\s+.*",
        "profile rejection branch",
        start=upper + 1,
        stop=index,
    )
    count_base, count_load = _indexed_table_base(
        rows, "x22", "sequence-count"
    )
    pointer_base, pointer_load = _indexed_table_base(
        rows, "x8", "sequence-pointer"
    )
    if not index < count_load < pointer_load:
        raise AuditError("P2.88 switch-table load order differs")
    count_compare = _unique_index(
        rows,
        r"cmp\s+x22,\s*x21",
        "generation/count comparison",
        start=count_load + 1,
        stop=pointer_load,
    )
    count_reject = _unique_index(
        rows,
        r"b\.ls\s+.*",
        "generation/count rejection branch",
        start=count_compare + 1,
        stop=pointer_load,
    )
    request_stage = _unique_index(
        rows,
        r"ldrb\s+w3,\s*\[x20,\s*#0x6\]",
        "request stage load",
        start=pointer_load + 1,
    )
    table_stage = _unique_index(
        rows,
        r"ldrb\s+w8,\s*\[x8,\s*x21\]",
        "generation-indexed sequence byte load",
        start=request_stage + 1,
    )
    stage_compare = _unique_index(
        rows,
        r"cmp\s+w3,\s*w8",
        "request/sequence stage comparison",
        start=table_stage + 1,
    )
    _unique_index(
        rows,
        r"b\.ne\s+.*",
        "stage mismatch rejection branch",
        start=stage_compare + 1,
        stop=stage_compare + 2,
    )
    return {
        "count_base": count_base,
        "pointer_base": pointer_base,
        "profile_domain": [1, 3],
        "profile_index_bias": 1,
        "profile_table_index_register": "x8",
        "generation_register": "x21",
        "entry_width": 8,
        "count_guard_before_pointer_load": count_reject < pointer_load,
        "generation_indexed_byte_load": True,
        "request_stage_compare": True,
        "structural_verified": True,
    }


def _fallback_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
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

    expected = p288.linked_table_bytes()
    structure = _switch_table_structure(
        disassembly["s22_fyg8_e1_request_allowed"]
    )
    loads = {
        "sequence": {
            "form": "profile-indexed-switch-table",
            "exact_binding_deferred_to_postbuild": True,
            "structure": {
                key: value
                for key, value in structure.items()
                if key not in {"count_base", "pointer_base"}
            },
        },
        "items": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_expected_item",
            "s22_fyg8_e2_items",
            len(expected["s22_fyg8_e2_items"]),
            "byte",
        ),
        "kinds": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_e2_kinds",
            len(expected["s22_fyg8_e2_kinds"]),
            "byte",
        ),
        "exact_rule_bytes": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_p288_detail_rules",
            len(expected["s22_fyg8_p288_detail_rules"]),
            "byte",
        ),
        "exact_rule_halfwords": p282_audit._require_load(
            disassembly,
            symbol_addresses,
            "s22_fyg8_e1_detail_allowed",
            "s22_fyg8_p288_detail_rules",
            len(expected["s22_fyg8_p288_detail_rules"]),
            "halfword",
        ),
    }
    tuple_immediates = p282_audit._immediates(
        disassembly["s22_fyg8_p288_tuple_allowed"]
    )
    tuple_span = p288.spec.TUPLE_LAST - p288.spec.TUPLE_FIRST
    if (
        p288.spec.ordinal_for_position(p288.spec.FINAL_STAGE, 1)
        not in tuple_immediates
        or p288.spec.TUPLE_FIRST not in tuple_immediates
        or not (
            p288.spec.TUPLE_LAST in tuple_immediates
            or tuple_span in tuple_immediates
        )
    ):
        raise AuditError("P2.88 linked tuple range dispatch differs")
    return {
        "audit_adapter": ADAPTER_ID,
        "audit_implementation": IMPLEMENTATION_ID,
        "writer_calls_request_validator": True,
        "request_calls_item_validator": True,
        "request_calls_detail_validator": True,
        "detail_calls_tuple_validator": True,
        "pair_tables_loaded": loads,
        "exact_rule_count": len(p288.spec.exact_detail_rules()),
        "tuple_range_verified": True,
        "writer_guard": cfg_audit._audit_writer_guard(
            disassembly["s22_fyg8_e1_write"]
        ),
        "postbuild_exact_sequence_binding_pending": True,
        "verified": False,
    }


def audit_linked_validator(
    disassembly: dict[str, str],
    calls: dict[str, list[str]],
    symbol_addresses: dict[str, int],
) -> dict[str, Any]:
    try:
        result = legacy.audit_linked_validator(
            disassembly, calls, symbol_addresses
        )
    except AuditError as exc:
        if "does not load exact table: s22_fyg8_e2_sequence" not in str(exc):
            raise
        return _fallback_validator(
            disassembly, calls, symbol_addresses
        )
    result["audit_implementation"] = IMPLEMENTATION_ID
    result["pair_tables_loaded"]["sequence_form"] = "direct"
    result["postbuild_exact_sequence_binding_pending"] = False
    return result


def _dump_address_bytes(
    objdump: Path,
    vmlinux: Path,
    start: int,
    size: int,
) -> bytes:
    text = repro._run(  # noqa: SLF001
        [
            str(objdump),
            "-s",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{start + size:x}",
            str(vmlinux),
        ],
        "objdump switch table",
    )
    addressed: dict[int, int] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([0-9a-fA-F]+)\s+(.+)$", line)
        if match is None:
            continue
        cursor = int(match.group(1), 16)
        columns = re.split(r"\s{2,}", match.group(2), maxsplit=1)[0]
        for token in columns.split():
            if (
                re.fullmatch(r"[0-9a-fA-F]{2,8}", token) is None
                or len(token) % 2
            ):
                break
            for value in bytes.fromhex(token):
                addressed[cursor] = value
                cursor += 1
    try:
        return bytes(addressed[start + offset] for offset in range(size))
    except KeyError as exc:
        raise AuditError("P2.88 linked switch-table dump is short") from exc


def _little_u64s(data: bytes) -> tuple[int, ...]:
    if not data or len(data) % 8:
        raise AuditError("P2.88 switch-table byte width differs")
    return tuple(
        int.from_bytes(data[offset : offset + 8], "little")
        for offset in range(0, len(data), 8)
    )


def _validate_switch_table_values(
    structure: dict[str, Any],
    counts: tuple[int, ...],
    pointers: tuple[int, ...],
    sequence_addresses: tuple[int, int, int],
) -> dict[str, Any]:
    expected_counts = (9, 15, len(p288.linked_table_bytes()[
        "s22_fyg8_e2_sequence"
    ]))
    if counts != expected_counts:
        raise AuditError(
            f"P2.88 linked sequence count switch differs: {counts}"
        )
    if pointers != sequence_addresses:
        raise AuditError("P2.88 linked sequence pointer switch differs")
    if (
        structure.get("profile_domain") != [1, 3]
        or structure.get("profile_index_bias") != 1
        or structure.get("entry_width") != 8
        or structure.get("count_guard_before_pointer_load") is not True
        or structure.get("generation_indexed_byte_load") is not True
        or structure.get("request_stage_compare") is not True
    ):
        raise AuditError("P2.88 linked switch-table structure differs")
    return {
        "form": "profile-indexed-switch-table",
        "profile_domain": [1, 3],
        "profile_index_bias": 1,
        "e2_profile_index": 2,
        "sequence_symbols": [
            "s22_fyg8_e1a_sequence",
            "s22_fyg8_e1b_sequence",
            "s22_fyg8_e2_sequence",
        ],
        "sequence_counts": list(expected_counts),
        "e2_count": expected_counts[2],
        "count_table_exact": True,
        "pointer_table_exact": True,
        "generation_indexed_byte_load": True,
        "request_stage_compare": True,
        "exact_e2_sequence_target": True,
        "verified": True,
    }


def _exact_switch_table_audit(
    args, result: dict[str, Any]  # noqa: ANN001
) -> dict[str, Any]:
    root = repro.candidate_contract.intent.repo_root()
    directory = repro.candidate_contract.intent.resolve(root, args.build_a)
    paths = {
        "vmlinux": directory / "vmlinux",
        "nm": repro.candidate_contract.intent.resolve(root, args.nm),
        "objdump": repro.candidate_contract.intent.resolve(root, args.objdump),
    }
    captured = {
        "vmlinux": repro.candidate_contract.stable_read(
            paths["vmlinux"],
            "P2.88 post-build linked vmlinux",
            repro.ARTIFACT_LIMITS["vmlinux"],
        ),
        "nm": repro.candidate_contract.stable_read(
            paths["nm"], "P2.88 post-build nm", 16 * 1024 * 1024
        ),
        "objdump": repro.candidate_contract.stable_read(
            paths["objdump"],
            "P2.88 post-build objdump",
            16 * 1024 * 1024,
        ),
    }
    receipts = {
        name: repro.candidate_contract.intent.receipt(data)
        for name, data in captured.items()
    }
    expected_vmlinux = (
        result.get("build_a", {})
        .get("artifacts", {})
        .get("vmlinux")
    )
    if receipts["vmlinux"] != expected_vmlinux:
        raise AuditError(
            "P2.88 post-build vmlinux changed after reproducibility audit"
        )
    with tempfile.TemporaryDirectory(
        prefix="s22-p288-postbuild-linked-"
    ) as temporary:
        staged: dict[str, Path] = {}
        for name, data in captured.items():
            path = Path(temporary) / name
            path.write_bytes(data)
            path.chmod(0o700 if name in {"nm", "objdump"} else 0o600)
            staged[name] = path
        ranges = repro._symbol_ranges(  # noqa: SLF001
            repro._run(  # noqa: SLF001
                [str(staged["nm"]), "-n", str(staged["vmlinux"])],
                "P2.88 post-build nm",
            )
        )
        request = repro._disassemble(  # noqa: SLF001
            staged["objdump"],
            staged["vmlinux"],
            ranges,
            "s22_fyg8_e1_request_allowed",
        )
        structure = _switch_table_structure(request)
        count_bytes = _dump_address_bytes(
            staged["objdump"],
            staged["vmlinux"],
            structure["count_base"],
            24,
        )
        pointer_bytes = _dump_address_bytes(
            staged["objdump"],
            staged["vmlinux"],
            structure["pointer_base"],
            24,
        )
        symbols = (
            "s22_fyg8_e1a_sequence",
            "s22_fyg8_e1b_sequence",
            "s22_fyg8_e2_sequence",
        )
        if any(symbol not in ranges for symbol in symbols):
            raise AuditError(
                "P2.88 linked sequence switch target symbol is missing"
            )
        proof = _validate_switch_table_values(
            structure,
            _little_u64s(count_bytes),
            _little_u64s(pointer_bytes),
            tuple(ranges[symbol][0] for symbol in symbols),
        )
    proof["staged_input_receipts"] = receipts
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
    if head.returncode != 0 or re.fullmatch(
        r"[0-9a-f]{40}", head.stdout.strip()
    ) is None:
        raise AuditError("P2.88 post-build support HEAD is unavailable")
    status = subprocess.run(
        ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if (
        status.returncode != 0
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
    ):
        raise AuditError("P2.88 post-build linked adapter was not applied")
    sequence = validator.get("pair_tables_loaded", {}).get("sequence")
    if (
        not isinstance(sequence, dict)
        or sequence.get("form") != "profile-indexed-switch-table"
    ):
        if validator.get("verified") is not True:
            raise AuditError("P2.88 direct linked validator is incomplete")
        exact_sequence = {
            "form": "direct",
            "verified": True,
        }
    else:
        exact_sequence = _exact_switch_table_audit(args, result)
        sequence["exact_binding_deferred_to_postbuild"] = False
        sequence["postbuild_exact_binding"] = exact_sequence
        validator["postbuild_exact_sequence_binding_pending"] = False
        validator["verified"] = True
    linked["gnu_aarch64_tools"] = tool_identity
    linked["postbuild_audit"] = {
        "implementation_id": IMPLEMENTATION_ID,
        "semantic_adapter_id": ADAPTER_ID,
        "exact_sequence_binding": exact_sequence,
        "support_delta": _support_delta(
            repro.candidate_contract.intent.repo_root()
        ),
        "verified": True,
    }
    if validator.get("verified") is not True:
        raise AuditError("P2.88 post-build validator did not close")
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
