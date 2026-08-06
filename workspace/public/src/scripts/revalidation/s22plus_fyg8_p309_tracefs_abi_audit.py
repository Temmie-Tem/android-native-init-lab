#!/usr/bin/env python3
"""Cross-check generated trace descriptors against exact source and linked ABI."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import struct
from typing import Any

import s22plus_fyg8_p307_qscratch_audit as qscratch_audit
import s22plus_fyg8_p307_telemetry_spec as p307
from s22plus_fyg8_r4w1b_elf_audit import Elf64, ElfAuditError


SCHEMA = "s22plus_fyg8_p309_tracefs_abi_cross_authority_v1"
VERDICT = "PASS_P309_TRACEFS_ABI_SOURCE_A_B_AND_DESCRIPTOR_HOST_ONLY"
KERNEL = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/common"
)
PTRACE = KERNEL / "arch/arm64/kernel/ptrace.c"
TRACE_PROBE = KERNEL / "kernel/trace/trace_probe.c"
TRACE_PROBE_H = KERNEL / "kernel/trace/trace_probe.h"
TRACE_H = KERNEL / "kernel/trace/trace.h"
P300 = Path("workspace/private/outputs/s22plus_fyg8_p300/full-lto-e324abae-v1")
VMLINUX_A = P300 / "artifacts-a/vmlinux"
VMLINUX_B = P300 / "artifacts-b/vmlinux"
MANIFEST_A = P300 / "build-a/source-overlay-audit/reconstructed-final-members.jsonl"
MANIFEST_B = P300 / "build-b/source-overlay-audit/reconstructed-final-members.jsonl"


class AuditError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_regular(path: Path, label: str) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise AuditError(f"{label} is missing or indirect")
    return path.read_bytes()


def _strip_comments(source: str) -> str:
    output: list[str] = []
    index = 0
    quote = ""
    while index < len(source):
        char = source[index]
        if quote:
            output.append(char)
            if char == "\\" and index + 1 < len(source):
                index += 1
                output.append(source[index])
            elif char == quote:
                quote = ""
            index += 1
            continue
        if char in ('"', "'"):
            quote = char
            output.append(char)
            index += 1
            continue
        if source.startswith("//", index):
            end = source.find("\n", index)
            if end < 0:
                break
            output.append("\n")
            index = end + 1
            continue
        if source.startswith("/*", index):
            end = source.find("*/", index + 2)
            if end < 0:
                raise AuditError("unterminated C comment")
            output.extend("\n" for char in source[index : end + 2] if char == "\n")
            index = end + 2
            continue
        output.append(char)
        index += 1
    if quote:
        raise AuditError("unterminated C string while stripping comments")
    return "".join(output)


def _initializer_entries(source: str, declaration: str) -> list[str]:
    clean = _strip_comments(source)
    if clean.count(declaration) != 1:
        raise AuditError(f"initializer declaration cardinality differs: {declaration}")
    start = clean.index(declaration) + len(declaration)
    brace = clean.find("{", start)
    if brace < 0:
        raise AuditError(f"initializer body is absent: {declaration}")
    entries: list[str] = []
    token: list[str] = []
    depths = {"(": 0, "[": 0, "{": 0}
    closes = {")": "(", "]": "[", "}": "{"}
    quote = ""
    index = brace + 1
    while index < len(clean):
        char = clean[index]
        if quote:
            token.append(char)
            if char == "\\" and index + 1 < len(clean):
                index += 1
                token.append(clean[index])
            elif char == quote:
                quote = ""
        elif char in ('"', "'"):
            quote = char
            token.append(char)
        elif char in depths:
            depths[char] += 1
            token.append(char)
        elif char == "}" and not any(depths.values()):
            tail = "".join(token).strip()
            if tail:
                entries.append(tail)
            if clean[clean.find("}", index) + 1 :].lstrip()[:1] != ";":
                raise AuditError(f"initializer terminator differs: {declaration}")
            return entries
        elif char in closes:
            opening = closes[char]
            if depths[opening] <= 0:
                raise AuditError(f"unbalanced initializer: {declaration}")
            depths[opening] -= 1
            token.append(char)
        elif char == "," and not any(depths.values()):
            entry = "".join(token).strip()
            if entry:
                entries.append(entry)
            token = []
        else:
            token.append(char)
        index += 1
    raise AuditError(f"unterminated initializer: {declaration}")


def extract_source_registers(source: bytes) -> tuple[str, ...]:
    entries = _initializer_entries(
        source.decode("utf-8"),
        "static const struct pt_regs_offset regoffset_table[] =",
    )
    names: list[str] = []
    sentinel = 0
    for index, entry in enumerate(entries):
        if entry == "REG_OFFSET_END":
            sentinel += 1
            if index != len(entries) - 1:
                raise AuditError("register sentinel is not final")
            continue
        match = re.fullmatch(r"GPR_OFFSET_NAME\(\s*(\d+)\s*\)", entry)
        if match:
            names.append(f"x{int(match.group(1))}")
            continue
        match = re.fullmatch(r"REG_OFFSET_NAME\(\s*([A-Za-z_]\w*)\s*\)", entry)
        if match:
            names.append(match.group(1))
            continue
        match = re.search(r"\.name\s*=\s*\"([^\"]+)\"", entry)
        if match and entry.startswith("{") and entry.endswith("}"):
            names.append(match.group(1))
            continue
        raise AuditError(f"unconsumed register initializer: {entry}")
    if sentinel != 1 or len(names) != len(set(names)):
        raise AuditError("register initializer sentinel or uniqueness differs")
    return tuple(names)


def extract_source_types(source: bytes) -> tuple[str, ...]:
    entries = _initializer_entries(
        source.decode("utf-8"),
        "static const struct fetch_type probe_fetch_types[] =",
    )
    names: list[str] = []
    sentinel = 0
    for index, entry in enumerate(entries):
        if entry == "ASSIGN_FETCH_TYPE_END":
            sentinel += 1
            if index != len(entries) - 1:
                raise AuditError("fetch-type sentinel is not final")
            continue
        match = re.match(r'__ASSIGN_FETCH_TYPE\(\s*"([^"]+)"\s*,', entry, re.S)
        if match:
            names.append(match.group(1))
            continue
        match = re.match(
            r"ASSIGN_FETCH_TYPE(?:_ALIAS)?\(\s*([A-Za-z_]\w*)\s*,",
            entry,
            re.S,
        )
        if match:
            names.append(match.group(1))
            continue
        raise AuditError(f"unconsumed fetch-type initializer: {entry}")
    if sentinel != 1 or len(names) != len(set(names)):
        raise AuditError("fetch-type initializer sentinel or uniqueness differs")
    return tuple(names)


def _function(source: str, declaration: str) -> str:
    clean = _strip_comments(source)
    if clean.count(declaration) != 1:
        raise AuditError(f"function declaration cardinality differs: {declaration}")
    start = clean.index(declaration)
    brace = clean.find("{", start + len(declaration))
    if brace < 0:
        raise AuditError(f"function body is absent: {declaration}")
    depth = 0
    quote = ""
    index = brace
    while index < len(clean):
        char = clean[index]
        if quote:
            if char == "\\" and index + 1 < len(clean):
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return clean[start : index + 1]
        index += 1
    raise AuditError(f"function body is unterminated: {declaration}")


def extract_source_name_contract(
    trace_h: bytes, trace_probe: bytes, trace_probe_h: bytes
) -> dict[str, Any]:
    header = trace_h.decode("utf-8")
    probe = trace_probe.decode("utf-8")
    probe_header = trace_probe_h.decode("utf-8")
    limits = re.findall(r"^#define MAX_EVENT_NAME_LEN\s+(\d+)\s*$", header, re.M)
    if len(limits) != 1:
        raise AuditError("MAX_EVENT_NAME_LEN source authority differs")
    event_max = int(limits[0])
    arg_limits = re.findall(
        r"^#define MAX_ARG_NAME_LEN\s+(\d+)\s*$", probe_header, re.M
    )
    if len(arg_limits) != 1:
        raise AuditError("MAX_ARG_NAME_LEN source authority differs")
    good = _function(header, "static inline bool is_good_name(const char *name)")
    compact_good = re.sub(r"\s+", " ", good)
    for token in (
        "if (!isalpha(*name) && *name != '_') return false;",
        "while (*++name != '\\0')",
        "if (!isalpha(*name) && !isdigit(*name) && *name != '_') return false;",
    ):
        if token not in compact_good:
            raise AuditError("is_good_name source semantics differ")
    parse_name = _function(
        probe,
        "int traceprobe_parse_event_name(const char **pevent, const char **pgroup,",
    )
    compact_parse = re.sub(r"\s+", " ", parse_name)
    for token in (
        "slash - event + 1 > MAX_EVENT_NAME_LEN",
        "len > MAX_EVENT_NAME_LEN",
        "if (!is_good_name(buf))",
        "if (!is_good_name(event))",
    ):
        if token not in compact_parse:
            raise AuditError("traceprobe name-bound source semantics differ")
    type_lookup = _function(
        probe, "static const struct fetch_type *find_fetch_type(const char *type)"
    )
    if "if (*type == 'b')" not in type_lookup:
        raise AuditError("tracefs bitfield source semantics differ")
    bitfield_bases = tuple(
        int(value)
        for value in re.findall(
            r'case\s+(\d+):\s+return find_fetch_type\("u\d+"\);',
            type_lookup,
            re.S,
        )
    )
    if not bitfield_bases or len(bitfield_bases) != len(set(bitfield_bases)):
        raise AuditError("tracefs bitfield base-size source semantics differ")
    bitfield_parse = _function(
        probe, "static int __parse_bitfield_probe_arg(const char *bf,"
    )
    compact_bitfield = re.sub(r"\s+", " ", bitfield_parse)
    for token in (
        "if (bw == 0 || *tail != '@') return -EINVAL;",
        "if (tail == bf || *tail != '/') return -EINVAL;",
        "return (BYTES_TO_BITS(t->size) < (bw + bo)) ? -EINVAL : 0;",
    ):
        if token not in compact_bitfield:
            raise AuditError("tracefs bitfield bound source semantics differ")
    return {
        "group_max": event_max - 1,
        "event_max": event_max,
        "argument_max": int(arg_limits[0]),
        "grammar": "first-alpha-or-underscore-rest-alnum-or-underscore",
        "bitfield_prefix": "b",
        "bitfield_base_bits": list(bitfield_bases),
        "is_good_name_sha256": _sha256(good.encode("utf-8")),
        "parse_event_name_sha256": _sha256(parse_name.encode("utf-8")),
        "find_fetch_type_sha256": _sha256(type_lookup.encode("utf-8")),
        "parse_bitfield_sha256": _sha256(bitfield_parse.encode("utf-8")),
        "verified": True,
    }


def _cstring_at_vaddr(elf: Elf64, address: int) -> str:
    matches = [
        row
        for row in elf.programs
        if row["type"] == 1
        and row["vaddr"] <= address < row["vaddr"] + row["file_size"]
    ]
    if len(matches) != 1:
        raise AuditError(f"string address {address:#x} has {len(matches)} mappings")
    row = matches[0]
    offset = row["offset"] + address - row["vaddr"]
    limit = row["offset"] + row["file_size"]
    try:
        value = elf.cstring(offset, limit)
        value.encode("ascii")
    except (ElfAuditError, UnicodeError) as exc:
        raise AuditError(f"linked ABI string at {address:#x} is invalid") from exc
    return value


def _linked_names(
    vmlinux: Path, symbol_name: str, entry_size: int
) -> tuple[tuple[str, ...], dict[str, Any]]:
    try:
        with Elf64(vmlinux) as elf:
            symbol = elf.symbols({symbol_name})[symbol_name]
            raw = bytes(elf.symbol_bytes(symbol))
            if len(raw) % entry_size:
                raise AuditError(f"linked {symbol_name} size is not entry aligned")
            names: list[str] = []
            sentinel = 0
            for offset in range(0, len(raw), entry_size):
                pointer = struct.unpack_from("<Q", raw, offset)[0]
                entry = raw[offset : offset + entry_size]
                if pointer == 0:
                    sentinel += 1
                    if offset + entry_size != len(raw) or any(entry):
                        raise AuditError(f"linked {symbol_name} sentinel differs")
                    continue
                if sentinel:
                    raise AuditError(f"linked {symbol_name} has data after sentinel")
                names.append(_cstring_at_vaddr(elf, pointer))
            if sentinel != 1 or len(names) != len(set(names)):
                raise AuditError(f"linked {symbol_name} sentinel or uniqueness differs")
            return tuple(names), {
                "path": vmlinux.as_posix(),
                "size": vmlinux.stat().st_size,
                "sha256": _sha256_file(vmlinux),
                "symbol_value": int(symbol["value"]),
                "symbol_size": int(symbol["size"]),
                "entry_size": entry_size,
                "entry_count_with_sentinel": len(raw) // entry_size,
            }
    except ElfAuditError as exc:
        raise AuditError(str(exc)) from exc


def _set_receipt(values: tuple[str, ...]) -> dict[str, Any]:
    canonical = "\n".join(sorted(values)).encode("ascii") + b"\n"
    return {
        "count": len(values),
        "sha256": _sha256(canonical),
        "values": sorted(values),
    }


def _manifest_row(manifest: Path, relative: str) -> dict[str, Any]:
    payload = _read_regular(manifest, "P3.00 reconstructed-source manifest")
    rows = []
    for line in payload.splitlines():
        try:
            row = json.loads(line)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise AuditError("P3.00 reconstructed-source manifest is invalid") from exc
        if row.get("path") == relative:
            rows.append(row)
    if len(rows) != 1 or rows[0].get("type") != "file":
        raise AuditError(f"P3.00 source manifest row differs: {relative}")
    return rows[0]


def _decode_c_string(literal: str) -> str:
    try:
        value = ast.literal_eval(literal)
    except (SyntaxError, ValueError) as exc:
        raise AuditError("descriptor C string literal is invalid") from exc
    if not isinstance(value, str):
        raise AuditError("descriptor initializer is not a string")
    return value


def _descriptor_rows(descriptor: bytes) -> list[dict[str, str]]:
    source = descriptor.decode("utf-8")
    rows: list[dict[str, str]] = []
    counts = {
        "role": "P282_ROLE_EVENT_COUNT",
        "cycle": "P282_CYCLE_EVENT_COUNT",
        "bind": "P282_BIND_EVENT_COUNT",
    }
    for family, macro in counts.items():
        entries = _initializer_entries(
            source,
            f"static const struct p282_event_descriptor p282_{family}_events[] =",
        )
        match = re.search(rf"^#define {macro} (\d+)U$", source, re.M)
        if match is None or int(match.group(1)) != len(entries):
            raise AuditError(f"descriptor {family} count differs")
        for entry in entries:
            strings = re.findall(r'"(?:\\.|[^"\\])*"', entry)
            residue = re.sub(r'"(?:\\.|[^"\\])*"', '""', entry)
            row_pattern = r"\{\s*\"\"\s*,\s*\"\"\s*,\s*\"\"\s*\}"
            if len(strings) != 3 or not re.fullmatch(row_pattern, residue, re.S):
                raise AuditError(f"descriptor {family} row grammar differs")
            name, definition, filter_value = map(_decode_c_string, strings)
            rows.append({
                "family": family,
                "name": name,
                "definition": definition,
                "filter": filter_value,
            })
    return rows


def _good_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value))


def _bitfield_parts(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(
        r"b(0[xX][0-9A-Fa-f]+|0[0-7]*|[1-9]\d*)"
        r"@(0[xX][0-9A-Fa-f]+|0[0-7]*|[1-9]\d*)"
        r"/(0[xX][0-9A-Fa-f]+|0[0-7]*|[1-9]\d*)",
        value,
    )
    if match is None:
        return None
    return tuple(int(part, 0) for part in match.groups())


def validate_descriptor(
    descriptor: bytes,
    registers: tuple[str, ...],
    fetch_types: tuple[str, ...],
    name_contract: dict[str, Any],
) -> dict[str, Any]:
    register_set = set(registers)
    type_set = set(fetch_types)
    rows = _descriptor_rows(descriptor)
    seen_registers: set[str] = set()
    seen_types: set[str] = set()
    bitfields: set[str] = set()
    trace_events: set[tuple[str, str]] = set()
    for row in rows:
        definition = row["definition"]
        match = re.match(
            r"^(?:p|r\d*):([A-Za-z_][A-Za-z0-9_]*)/"
            r"([A-Za-z_][A-Za-z0-9_]*)\s+\S+(?:\s+(.*))?\n$",
            definition,
        )
        if match is None:
            raise AuditError(f"descriptor definition grammar differs: {row['name']}")
        group, event, arguments = match.groups()
        if (
            not _good_name(group)
            or not _good_name(event)
            or len(group) > name_contract["group_max"]
            or len(event) > name_contract["event_max"]
            or event != row["name"]
        ):
            raise AuditError(f"descriptor group/event contract differs: {row['name']}")
        trace_event = (group, event)
        if trace_event in trace_events:
            raise AuditError(f"descriptor group/event is duplicated: {group}/{event}")
        trace_events.add(trace_event)
        if arguments:
            aliases: set[str] = set()
            for argument in arguments.split():
                if "=" not in argument:
                    raise AuditError(f"descriptor fetch argument differs: {row['name']}")
                alias, expression = argument.split("=", 1)
                if (
                    not _good_name(alias)
                    or len(alias) > name_contract["argument_max"]
                    or alias in aliases
                    or ":" not in expression
                ):
                    raise AuditError(f"descriptor fetch alias/type differs: {row['name']}")
                aliases.add(alias)
                value_expression, type_name = expression.rsplit(":", 1)
                register_match = re.fullmatch(
                    r"%([A-Za-z_][A-Za-z0-9_]*)"
                    r"|[+-](?:0[xX][0-9A-Fa-f]+|\d+)"
                    r"\(%([A-Za-z_][A-Za-z0-9_]*)\)",
                    value_expression,
                )
                if value_expression == "$retval":
                    registers_in_expression: tuple[str, ...] = ()
                elif register_match is None:
                    raise AuditError(
                        f"descriptor register expression differs: {row['name']}"
                    )
                else:
                    registers_in_expression = tuple(
                        value for value in register_match.groups() if value is not None
                    )
                for register in registers_in_expression:
                    if register not in register_set:
                        raise AuditError(
                            f"descriptor register is outside linked ABI: {register}"
                        )
                    seen_registers.add(register)
                bitfield = _bitfield_parts(type_name)
                if bitfield is not None:
                    width, offset, base_bits = bitfield
                    if (
                        width == 0
                        or base_bits not in name_contract["bitfield_base_bits"]
                        or width + offset > base_bits
                    ):
                        raise AuditError(
                            f"descriptor bitfield bounds differ: {row['name']}"
                        )
                    bitfields.add(type_name)
                elif type_name not in type_set:
                    raise AuditError(f"descriptor type is outside linked ABI: {type_name}")
                else:
                    seen_types.add(type_name)
    qscratch = [row for row in rows if row["name"] == "p307_qscratch"]
    if len(qscratch) != 1 or "rc=%x21:s32" not in qscratch[0]["definition"]:
        raise AuditError("corrected QSCRATCH descriptor is absent")
    if "%w21" in qscratch[0]["definition"]:
        raise AuditError("invalid arm64 tracefs w21 name survived")
    return {
        "event_count": len(rows),
        "family_counts": {
            family: sum(row["family"] == family for row in rows)
            for family in ("role", "cycle", "bind")
        },
        "registers_used": sorted(seen_registers),
        "fetch_types_used": sorted(seen_types),
        "bitfield_types_used": sorted(bitfields),
        "qscratch_trace_fetch_register": "x21",
        "verified": True,
    }


def audit(root: Path, descriptor: bytes) -> dict[str, Any]:
    source_paths = {
        "registers": root / PTRACE,
        "types": root / TRACE_PROBE,
        "type_header": root / TRACE_PROBE_H,
        "names": root / TRACE_H,
    }
    source_data = {
        key: _read_regular(path, f"P3.09 {key} source")
        for key, path in source_paths.items()
    }
    source_registers = extract_source_registers(source_data["registers"])
    source_types = extract_source_types(source_data["types"])
    name_contract = extract_source_name_contract(
        source_data["names"], source_data["types"], source_data["type_header"]
    )
    linked: dict[str, dict[str, Any]] = {}
    linked_sets: dict[str, dict[str, tuple[str, ...]]] = {}
    for side, relative in (("a", VMLINUX_A), ("b", VMLINUX_B)):
        vmlinux = root / relative
        registers, register_meta = _linked_names(vmlinux, "regoffset_table", 16)
        types, type_meta = _linked_names(vmlinux, "probe_fetch_types", 48)
        linked_sets[side] = {"registers": registers, "types": types}
        linked[side] = {
            "vmlinux": {
                "path": register_meta["path"],
                "size": register_meta["size"],
                "sha256": register_meta["sha256"],
            },
            "registers": {
                key: value
                for key, value in register_meta.items()
                if key not in {"path", "size", "sha256"}
            },
            "types": {
                key: value
                for key, value in type_meta.items()
                if key not in {"path", "size", "sha256"}
            },
        }
    if not (
        set(source_registers)
        == set(linked_sets["a"]["registers"])
        == set(linked_sets["b"]["registers"])
    ):
        raise AuditError("source/A/B tracefs register sets differ")
    if not (
        set(source_types)
        == set(linked_sets["a"]["types"])
        == set(linked_sets["b"]["types"])
    ):
        raise AuditError("source/A/B tracefs fetch-type sets differ")
    if linked["a"]["vmlinux"]["sha256"] != linked["b"]["vmlinux"]["sha256"]:
        raise AuditError("P3.00 A/B vmlinux receipts differ")

    manifest_receipts: dict[str, Any] = {}
    manifest_map = {
        "registers": "kernel_platform/common/arch/arm64/kernel/ptrace.c",
        "types": "kernel_platform/common/kernel/trace/trace_probe.c",
        "type_header": "kernel_platform/common/kernel/trace/trace_probe.h",
        "names": "kernel_platform/common/kernel/trace/trace.h",
    }
    for side, relative in (("a", MANIFEST_A), ("b", MANIFEST_B)):
        manifest_receipts[side] = {}
        for key, member in manifest_map.items():
            row = _manifest_row(root / relative, member)
            current = source_data[key]
            if row.get("size") != len(current) or row.get("sha256") != _sha256(current):
                raise AuditError(f"P3.00 {side} source authority differs: {member}")
            manifest_receipts[side][key] = {
                "path": member,
                "size": row["size"],
                "sha256": row["sha256"],
            }

    descriptor_result = validate_descriptor(
        descriptor, source_registers, source_types, name_contract
    )
    try:
        machine = qscratch_audit.audit(
            root,
            Path(p307.DWC3_MODULE_PATH),
            "aarch64-linux-gnu-objdump",
            "readelf",
        )
    except qscratch_audit.AuditError as exc:
        raise AuditError(str(exc)) from exc
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority": {
            "registers": {
                "source": _set_receipt(source_registers),
                "linked_a": _set_receipt(linked_sets["a"]["registers"]),
                "linked_b": _set_receipt(linked_sets["b"]["registers"]),
                "source_equals_a_equals_b": True,
            },
            "fetch_types": {
                "source": _set_receipt(source_types),
                "linked_a": _set_receipt(linked_sets["a"]["types"]),
                "linked_b": _set_receipt(linked_sets["b"]["types"]),
                "source_equals_a_equals_b": True,
            },
            "linked": linked,
            "source_manifests": manifest_receipts,
            "names": name_contract,
        },
        "descriptor": descriptor_result,
        "qscratch": {
            "trace_fetch_register": "x21",
            "trace_fetch_type": "s32",
            "machine_readback_register": machine["probe"]["register"],
            "machine_w21_unmodified_to_probe": machine["probe"][
                "w21_unmodified_from_readback_to_probe"
            ],
            "x21_lower_32_bits_are_w21": True,
            "callsite": machine,
            "verified": True,
        },
        "p308_immutable": True,
        "device_contact": False,
        "verified": True,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--descriptor", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    descriptor = (
        args.descriptor if args.descriptor.is_absolute() else root / args.descriptor
    )
    try:
        result = audit(root, _read_regular(descriptor, "P3.09 descriptor"))
    except (AuditError, OSError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}
            )
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
