#!/usr/bin/env python3
"""Inspect the final R4W1-B AArch64 ELF without third-party Python modules."""

from __future__ import annotations

import hashlib
import mmap
import struct
from pathlib import Path
from typing import Any, Iterator


ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")
SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")
SYMBOL = struct.Struct("<IBBHQQ")
EM_AARCH64 = 183
PT_LOAD = 1
SHT_SYMTAB = 2


class ElfAuditError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def branch_target(pc: int, word: int) -> int | None:
    if word & 0xFC000000 not in (0x14000000, 0x94000000):
        return None
    return pc + sign_extend((word & 0x03FFFFFF) << 2, 28)


def compare_branch(word: int) -> dict[str, int] | None:
    if word & 0x7E000000 != 0x34000000:
        return None
    return {
        "nonzero": (word >> 24) & 1,
        "register": word & 0x1F,
        "target_delta": sign_extend((word >> 5) & 0x7FFFF, 19) << 2,
    }


def conditional_branch(word: int) -> dict[str, int] | None:
    if word & 0xFF000010 != 0x54000000:
        return None
    return {
        "condition": word & 0xF,
        "target_delta": sign_extend((word >> 5) & 0x7FFFF, 19) << 2,
    }


def adrp_target(pc: int, word: int) -> tuple[int, int] | None:
    if word & 0x9F000000 != 0x90000000:
        return None
    immediate = sign_extend(
        (((word >> 5) & 0x7FFFF) << 2) | ((word >> 29) & 0x3),
        21,
    )
    return word & 0x1F, (pc & ~0xFFF) + (immediate << 12)


def add_immediate(word: int) -> dict[str, int] | None:
    if word & 0xFF000000 != 0x91000000:
        return None
    shift = 12 if (word >> 22) & 1 else 0
    return {
        "destination": word & 0x1F,
        "source": (word >> 5) & 0x1F,
        "immediate": ((word >> 10) & 0xFFF) << shift,
    }


def compare_w_immediate(word: int) -> dict[str, int] | None:
    if word & 0x7F00001F != 0x7100001F:
        return None
    shift = 12 if (word >> 22) & 1 else 0
    return {
        "register": (word >> 5) & 0x1F,
        "immediate": ((word >> 10) & 0xFFF) << shift,
    }


def is_mrs_sp_el0(word: int) -> bool:
    return word & 0xFFFFFFE0 == 0xD5384100


class Elf64:
    def __init__(self, path: Path):
        self.path = path
        self.file = path.open("rb")
        self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        if len(self.data) < ELF_HEADER.size:
            raise ElfAuditError("ELF is shorter than its header")
        fields = ELF_HEADER.unpack_from(self.data)
        ident = fields[0]
        if ident[:4] != b"\x7fELF" or ident[4] != 2 or ident[5] != 1:
            raise ElfAuditError("expected ELF64 little-endian input")
        if fields[2] != EM_AARCH64:
            raise ElfAuditError(f"expected AArch64 ELF, machine={fields[2]}")
        self.program_offset = fields[5]
        self.section_offset = fields[6]
        self.program_entry_size = fields[9]
        self.program_count = fields[10]
        self.section_entry_size = fields[11]
        self.section_count = fields[12]
        self.section_name_index = fields[13]
        if self.program_entry_size != PROGRAM_HEADER.size:
            raise ElfAuditError("unexpected ELF program-header size")
        if self.section_entry_size != SECTION_HEADER.size:
            raise ElfAuditError("unexpected ELF section-header size")
        self.programs = self._read_programs()
        self.sections = self._read_sections()

    def close(self) -> None:
        self.data.close()
        self.file.close()

    def __enter__(self) -> "Elf64":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _bounded(self, offset: int, size: int, label: str) -> None:
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise ElfAuditError(f"{label} exceeds ELF bounds")

    def _read_programs(self) -> list[dict[str, int]]:
        rows = []
        for index in range(self.program_count):
            offset = self.program_offset + index * self.program_entry_size
            self._bounded(offset, PROGRAM_HEADER.size, "program header")
            row = PROGRAM_HEADER.unpack_from(self.data, offset)
            rows.append(
                {
                    "type": row[0],
                    "offset": row[2],
                    "vaddr": row[3],
                    "file_size": row[5],
                    "memory_size": row[6],
                }
            )
        return rows

    def _read_sections(self) -> list[dict[str, int]]:
        raw = []
        for index in range(self.section_count):
            offset = self.section_offset + index * self.section_entry_size
            self._bounded(offset, SECTION_HEADER.size, "section header")
            row = SECTION_HEADER.unpack_from(self.data, offset)
            raw.append(
                {
                    "name_offset": row[0],
                    "type": row[1],
                    "address": row[3],
                    "offset": row[4],
                    "size": row[5],
                    "link": row[6],
                    "entry_size": row[9],
                }
            )
        if self.section_name_index >= len(raw):
            raise ElfAuditError("invalid section-name table index")
        names = raw[self.section_name_index]
        for row in raw:
            row["name"] = self.cstring(
                names["offset"] + row["name_offset"], names["offset"] + names["size"]
            )
        return raw

    def cstring(self, offset: int, limit: int) -> str:
        self._bounded(offset, 0, "string offset")
        end = self.data.find(b"\0", offset, min(limit, len(self.data)))
        if end < 0:
            raise ElfAuditError("unterminated ELF string")
        return self.data[offset:end].decode("utf-8", errors="strict")

    def symbols(self, requested: set[str]) -> dict[str, dict[str, int | str]]:
        matches: dict[str, list[dict[str, int | str]]] = {
            name: [] for name in requested
        }
        for section in self.sections:
            if section["type"] != SHT_SYMTAB:
                continue
            if section["entry_size"] != SYMBOL.size or section["link"] >= len(
                self.sections
            ):
                raise ElfAuditError("invalid ELF symbol table")
            strings = self.sections[section["link"]]
            count = section["size"] // SYMBOL.size
            for index in range(count):
                offset = section["offset"] + index * SYMBOL.size
                self._bounded(offset, SYMBOL.size, "symbol table")
                name_offset, info, other, section_index, value, size = SYMBOL.unpack_from(
                    self.data, offset
                )
                if not name_offset:
                    continue
                name = self.cstring(
                    strings["offset"] + name_offset,
                    strings["offset"] + strings["size"],
                )
                if name in matches and section_index != 0:
                    matches[name].append(
                        {
                            "name": name,
                            "value": value,
                            "size": size,
                            "section_index": section_index,
                            "info": info,
                            "other": other,
                        }
                    )
        result: dict[str, dict[str, int | str]] = {}
        for name, rows in matches.items():
            concrete = [row for row in rows if row["value"] and row["size"]]
            if len(concrete) != 1:
                raise ElfAuditError(
                    f"expected one concrete symbol {name}, found {len(concrete)}"
                )
            result[name] = concrete[0]
        return result

    def symbol_bytes(self, symbol: dict[str, int | str]) -> bytes:
        section_index = int(symbol["section_index"])
        if section_index >= len(self.sections):
            raise ElfAuditError(f"symbol {symbol['name']} has invalid section")
        section = self.sections[section_index]
        delta = int(symbol["value"]) - section["address"]
        if delta < 0 or delta + int(symbol["size"]) > section["size"]:
            raise ElfAuditError(f"symbol {symbol['name']} exceeds its section")
        offset = section["offset"] + delta
        self._bounded(offset, int(symbol["size"]), f"symbol {symbol['name']}")
        return self.data[offset : offset + int(symbol["size"])]

    def file_offset_to_vaddr(self, offset: int) -> int:
        matches = [
            row
            for row in self.programs
            if row["type"] == PT_LOAD
            and row["offset"] <= offset < row["offset"] + row["file_size"]
        ]
        if len(matches) != 1:
            raise ElfAuditError(
                f"file offset {offset:#x} maps to {len(matches)} PT_LOAD segments"
            )
        row = matches[0]
        return row["vaddr"] + offset - row["offset"]

    def mapped_file_offset_to_vaddr(self, offset: int) -> int | None:
        matches = [
            row
            for row in self.programs
            if row["type"] == PT_LOAD
            and row["offset"] <= offset < row["offset"] + row["file_size"]
        ]
        if not matches:
            return None
        if len(matches) != 1:
            raise ElfAuditError(
                f"file offset {offset:#x} maps to multiple PT_LOAD segments"
            )
        row = matches[0]
        return row["vaddr"] + offset - row["offset"]

    def find_all(self, needle: bytes) -> list[int]:
        offsets = []
        cursor = 0
        while True:
            cursor = self.data.find(needle, cursor)
            if cursor < 0:
                return offsets
            offsets.append(cursor)
            cursor += 1


def iter_words(code: bytes, start: int) -> Iterator[tuple[int, int, int]]:
    if len(code) % 4:
        raise ElfAuditError("AArch64 function size is not instruction-aligned")
    for index in range(0, len(code), 4):
        yield index // 4, start + index, struct.unpack_from("<I", code, index)[0]


def adrp_add_references(
    instructions: list[tuple[int, int, int]], targets: set[int]
) -> list[dict[str, int]]:
    references = []
    for left, right in zip(instructions, instructions[1:]):
        _, pc, first = left
        _, _, second = right
        page = adrp_target(pc, first)
        add = add_immediate(second)
        if page is None or add is None:
            continue
        register, base = page
        if add["destination"] != register or add["source"] != register:
            continue
        target = base + add["immediate"]
        if target in targets:
            references.append(
                {
                    "index": left[0],
                    "pc": pc,
                    "register": register,
                    "target": target,
                }
            )
    return references


def inspect_final_vmlinux(path: Path, marker: bytes) -> dict[str, Any]:
    required_symbols = {
        "kernel_init",
        "run_init_process",
        "strcmp",
        "builtime_crypto_hmac",
        "integrity_crypto_addrs",
        "crypto_buildtime_address",
    }
    with Elf64(path) as elf:
        symbols = elf.symbols(required_symbols)
        marker_offsets = elf.find_all(marker)
        marker_vaddrs = {elf.file_offset_to_vaddr(offset) for offset in marker_offsets}
        init_offsets = elf.find_all(b"/init\0")
        init_vaddrs = {
            address
            for offset in init_offsets
            if (address := elf.mapped_file_offset_to_vaddr(offset)) is not None
        }
        kernel_init = symbols["kernel_init"]
        code = elf.symbol_bytes(kernel_init)
        instructions = list(iter_words(code, int(kernel_init["value"])))
        marker_references = adrp_add_references(instructions, marker_vaddrs)
        init_references = adrp_add_references(instructions, init_vaddrs)

        run_address = int(symbols["run_init_process"]["value"])
        strcmp_address = int(symbols["strcmp"]["value"])
        run_calls = [
            row
            for row in instructions
            if row[2] & 0xFC000000 == 0x94000000
            and branch_target(row[1], row[2]) == run_address
        ]
        strcmp_calls = [
            row
            for row in instructions
            if row[2] & 0xFC000000 == 0x94000000
            and branch_target(row[1], row[2]) == strcmp_address
        ]

        success_edges = []
        for run_call in run_calls:
            run_index = run_call[0]
            return_guards = [
                row
                for row in instructions[run_index + 1 : run_index + 4]
                if (decoded := compare_branch(row[2])) is not None
                and decoded["nonzero"] == 1
                and decoded["register"] == 0
            ]
            later_strcmp = [
                row
                for row in strcmp_calls
                if run_index < row[0] <= run_index + 16
            ]
            if len(return_guards) != 1 or len(later_strcmp) != 1:
                continue
            strcmp_call = later_strcmp[0]
            path_refs = [
                row
                for row in init_references
                if strcmp_call[0] - 6 <= row["index"] < strcmp_call[0]
                and row["register"] == 1
            ]
            path_guards = [
                row
                for row in instructions[strcmp_call[0] + 1 : strcmp_call[0] + 4]
                if (decoded := compare_branch(row[2])) is not None
                and decoded["nonzero"] == 1
                and decoded["register"] == 0
            ]
            pid_mrs = [
                row
                for row in instructions[strcmp_call[0] + 1 : strcmp_call[0] + 8]
                if is_mrs_sp_el0(row[2])
            ]
            pid_compares = [
                row
                for row in instructions[strcmp_call[0] + 1 : strcmp_call[0] + 10]
                if (decoded := compare_w_immediate(row[2])) is not None
                and decoded["immediate"] == 1
            ]
            eq_branches = [
                row
                for row in instructions[strcmp_call[0] + 1 : strcmp_call[0] + 12]
                if (decoded := conditional_branch(row[2])) is not None
                and decoded["condition"] == 0
            ]
            if not (
                len(path_refs) == 1
                and len(path_guards) == 1
                and len(pid_mrs) == 1
                and len(pid_compares) == 1
                and len(eq_branches) == 1
            ):
                continue
            branch = eq_branches[0]
            decoded_branch = conditional_branch(branch[2])
            assert decoded_branch is not None
            target = branch[1] + decoded_branch["target_delta"]
            target_index = (target - int(kernel_init["value"])) // 4
            target_marker_refs = [
                row
                for row in marker_references
                if target_index <= row["index"] <= target_index + 128
            ]
            if len(target_marker_refs) != 1:
                continue
            success_edges.append(
                {
                    "run_init_process_call_pc": run_call[1],
                    "return_zero_guard_pc": return_guards[0][1],
                    "init_path_reference_pc": path_refs[0]["pc"],
                    "strcmp_call_pc": strcmp_call[1],
                    "path_match_guard_pc": path_guards[0][1],
                    "sp_el0_read_pc": pid_mrs[0][1],
                    "pid_one_compare_pc": pid_compares[0][1],
                    "pid_equal_branch_pc": branch[1],
                    "witness_block_pc": target,
                    "marker_reference_pc": target_marker_refs[0]["pc"],
                }
            )

        hmac_symbol = symbols["builtime_crypto_hmac"]
        hmac_bytes = elf.symbol_bytes(hmac_symbol)
        address_table = elf.symbol_bytes(symbols["integrity_crypto_addrs"])
        build_address = elf.symbol_bytes(symbols["crypto_buildtime_address"])
        build_address_value = (
            struct.unpack("<Q", build_address)[0] if len(build_address) == 8 else None
        )
        fips = {
            "hmac_symbol_address": int(hmac_symbol["value"]),
            "hmac_size": len(hmac_bytes),
            "hmac_hex": hmac_bytes.hex(),
            "hmac_sha256": sha256_bytes(hmac_bytes),
            "hmac_nonzero": any(hmac_bytes),
            "address_table_size": len(address_table),
            "address_table_sha256": sha256_bytes(address_table),
            "address_table_nonzero": any(address_table),
            "build_address_size": len(build_address),
            "build_address_value": build_address_value,
            "build_address_matches_symbol": (
                build_address_value
                == int(symbols["crypto_buildtime_address"]["value"])
            ),
        }
        fips["verified"] = (
            fips["hmac_size"] == 32
            and fips["hmac_nonzero"]
            and fips["address_table_size"] == 65536
            and fips["address_table_nonzero"]
            and fips["build_address_matches_symbol"]
        )
        control_flow = {
            "kernel_init_address": int(kernel_init["value"]),
            "kernel_init_size": int(kernel_init["size"]),
            "kernel_init_sha256": sha256_bytes(code),
            "run_init_process_address": run_address,
            "run_init_process_call_count": len(run_calls),
            "strcmp_address": strcmp_address,
            "strcmp_call_count": len(strcmp_calls),
            "init_string_count_in_elf": len(init_offsets),
            "init_reference_count_in_kernel_init": len(init_references),
            "marker_count_in_elf": len(marker_offsets),
            "marker_reference_count_in_kernel_init": len(marker_references),
            "success_edge_count": len(success_edges),
            "success_edges": success_edges,
        }
        control_flow["verified"] = (
            len(marker_offsets) == 1
            and len(marker_references) == 1
            and len(success_edges) == 1
        )
        return {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "machine": "AArch64",
            "symbols": symbols,
            "fips": fips,
            "control_flow": control_flow,
            "verified": fips["verified"] and control_flow["verified"],
        }
