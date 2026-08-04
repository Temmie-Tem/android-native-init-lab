#!/usr/bin/env python3
"""Attach an inert, non-alloc P3.02 identity section to a stripped ELF."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import tempfile


CARRIER_ID = "P302_ELECTRICAL_CARRIER_V1"
CARRIER_PAYLOAD = (CARRIER_ID + "\n").encode("ascii")
SECTION = ".p302_identity"
ALLOC_SECTIONS = (".text", ".rodata", ".data.rel.ro", ".data", ".bss")
ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")
SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")
SHT_PROGBITS = 1
SHT_NOBITS = 8
SHF_ALLOC = 0x2
# Adding a section necessarily changes these ELF header fields even though the
# section is not mapped: e_shoff, e_shnum, and e_shstrndx.  The ELF header is
# covered by the first PT_LOAD in this binary, so compare every program-segment
# byte after masking only those section-table locator fields.
SECTION_TABLE_HEADER_RANGES = ((40, 8), (60, 4))


class BinaryCarrierError(ValueError):
    pass


def _run(command: list[str], label: str) -> bytes:
    result = subprocess.run(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise BinaryCarrierError(
            f"{label} failed: {result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return result.stdout


def _tool(name: str) -> str:
    value = shutil.which(name)
    if value is None or not Path(value).is_file():
        raise BinaryCarrierError(f"required P3.02 tool is missing: {name}")
    return value


def _bounded(data: bytes, offset: int, size: int, label: str) -> bytes:
    if offset < 0 or size < 0 or offset > len(data) or size > len(data) - offset:
        raise BinaryCarrierError(f"P3.02 {label} is out of bounds")
    return data[offset : offset + size]


def _elf(data: bytes, label: str) -> dict:
    if len(data) < ELF_HEADER.size:
        raise BinaryCarrierError(f"P3.02 {label} ELF header is truncated")
    header = ELF_HEADER.unpack_from(data)
    ident = header[0]
    if (
        ident[:4] != b"\x7fELF"
        or ident[4] != 2
        or ident[5] != 1
        or header[2] != 183
        or header[8] != ELF_HEADER.size
        or header[9] != PROGRAM_HEADER.size
        or header[11] != SECTION_HEADER.size
    ):
        raise BinaryCarrierError(f"P3.02 {label} is not the expected ELF64 AArch64")
    phoff = header[5]
    phnum = header[10]
    shoff = header[6]
    shnum = header[12]
    shstrndx = header[13]
    if phnum <= 0 or shnum <= 0 or shstrndx >= shnum:
        raise BinaryCarrierError(f"P3.02 {label} ELF table dimensions differ")
    phdr_bytes = _bounded(
        data, phoff, phnum * PROGRAM_HEADER.size, f"{label} program headers"
    )
    program_headers = [
        PROGRAM_HEADER.unpack_from(phdr_bytes, index * PROGRAM_HEADER.size)
        for index in range(phnum)
    ]
    shdr_bytes = _bounded(
        data, shoff, shnum * SECTION_HEADER.size, f"{label} section headers"
    )
    section_headers = [
        SECTION_HEADER.unpack_from(shdr_bytes, index * SECTION_HEADER.size)
        for index in range(shnum)
    ]
    shstr = section_headers[shstrndx]
    strings = _bounded(data, shstr[4], shstr[5], f"{label} section names")
    sections = []
    names = set()
    for row in section_headers:
        name_offset = row[0]
        if name_offset >= len(strings):
            raise BinaryCarrierError(f"P3.02 {label} section name is out of bounds")
        end = strings.find(b"\0", name_offset)
        if end < 0:
            raise BinaryCarrierError(f"P3.02 {label} section name is unterminated")
        try:
            name = strings[name_offset:end].decode("ascii")
        except UnicodeError as exc:
            raise BinaryCarrierError(
                f"P3.02 {label} section name is not ASCII"
            ) from exc
        if name and name in names:
            raise BinaryCarrierError(f"P3.02 {label} section name is duplicated")
        names.add(name)
        content = (
            None
            if row[1] == SHT_NOBITS
            else _bounded(data, row[4], row[5], f"{label} section {name}")
        )
        sections.append(
            {
                "name_offset": name_offset,
                "name": name,
                "type": row[1],
                "flags": row[2],
                "address": row[3],
                "offset": row[4],
                "size": row[5],
                "link": row[6],
                "info": row[7],
                "align": row[8],
                "entsize": row[9],
                "content": content,
            }
        )
    critical_header = (
        header[0],
        header[1],
        header[2],
        header[3],
        header[4],
        header[5],
        header[7],
        header[8],
        header[9],
        header[10],
        header[11],
    )
    return {
        "critical_header": critical_header,
        "section_header_offset": shoff,
        "section_count": shnum,
        "section_name_index": shstrndx,
        "program_header_bytes": phdr_bytes,
        "program_headers": program_headers,
        "sections": sections,
    }


def _alloc_sections(value: dict) -> dict[str, tuple]:
    result = {}
    for row in value["sections"]:
        if row["flags"] & SHF_ALLOC:
            result[row["name"]] = (
                row["type"],
                row["flags"],
                row["address"],
                row["offset"],
                row["size"],
                row["link"],
                row["info"],
                row["align"],
                row["entsize"],
                row["content"],
            )
    return result


def _section_exact(row: dict) -> tuple:
    return (
        row["name_offset"],
        row["name"],
        row["type"],
        row["flags"],
        row["address"],
        row["offset"],
        row["size"],
        row["link"],
        row["info"],
        row["align"],
        row["entsize"],
        row["content"],
    )


def _masked_program_segment(data: bytes, offset: int, size: int, label: str) -> bytes:
    segment = bytearray(_bounded(data, offset, size, label))
    segment_end = offset + size
    for field_offset, field_size in SECTION_TABLE_HEADER_RANGES:
        field_end = field_offset + field_size
        overlap_start = max(offset, field_offset)
        overlap_end = min(segment_end, field_end)
        if overlap_start < overlap_end:
            relative = overlap_start - offset
            segment[relative : relative + overlap_end - overlap_start] = b"\0" * (
                overlap_end - overlap_start
            )
    return bytes(segment)


def _masked_elf_prefix(data: bytes, size: int, label: str) -> bytes:
    prefix = bytearray(_bounded(data, 0, size, label))
    for field_offset, field_size in SECTION_TABLE_HEADER_RANGES:
        if field_offset + field_size > size:
            raise BinaryCarrierError(f"P3.02 {label} excludes an ELF header field")
        prefix[field_offset : field_offset + field_size] = b"\0" * field_size
    return bytes(prefix)


def verify(carried: Path, baseline: Path) -> dict:
    for path, label in ((carried, "carried"), (baseline, "baseline")):
        metadata = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
            raise BinaryCarrierError(f"P3.02 {label} ELF is indirect or not regular")
    carried_data = carried.read_bytes()
    baseline_data = baseline.read_bytes()
    if (
        carried_data == baseline_data
        or carried_data.count(CARRIER_ID.encode("ascii")) != 1
        or carried_data.count(CARRIER_PAYLOAD) != 1
        or CARRIER_ID.encode("ascii") in baseline_data
    ):
        raise BinaryCarrierError("P3.02 carried ELF identity differs")
    before = _elf(baseline_data, "baseline")
    after = _elf(carried_data, "carried")
    if before["critical_header"] != after["critical_header"]:
        raise BinaryCarrierError("P3.02 changed execution-critical ELF header")
    if (
        before["program_header_bytes"] != after["program_header_bytes"]
        or before["program_headers"] != after["program_headers"]
    ):
        raise BinaryCarrierError("P3.02 changed program headers")
    for row in before["program_headers"]:
        offset = row[2]
        file_size = row[5]
        if _masked_program_segment(
            baseline_data, offset, file_size, "baseline program segment"
        ) != _masked_program_segment(
            carried_data, offset, file_size, "carried program segment"
        ):
            raise BinaryCarrierError("P3.02 changed program segment bytes")
    baseline_alloc = _alloc_sections(before)
    carried_alloc = _alloc_sections(after)
    if (
        tuple(baseline_alloc) != ALLOC_SECTIONS
        or tuple(carried_alloc) != ALLOC_SECTIONS
        or baseline_alloc != carried_alloc
    ):
        raise BinaryCarrierError("P3.02 changed SHF_ALLOC section closure")
    baseline_names = [row["name"] for row in before["sections"]]
    carried_names = [row["name"] for row in after["sections"]]
    expected_names = list(baseline_names)
    expected_names.insert(before["section_name_index"], SECTION)
    if (
        carried_names != expected_names
        or after["section_count"] != before["section_count"] + 1
        or after["section_name_index"] != before["section_name_index"] + 1
    ):
        raise BinaryCarrierError("P3.02 section-name closure differs")
    baseline_by_name = {row["name"]: row for row in before["sections"]}
    carried_by_name = {row["name"]: row for row in after["sections"]}
    for name in baseline_names:
        if name == ".shstrtab":
            continue
        if _section_exact(baseline_by_name[name]) != _section_exact(
            carried_by_name[name]
        ):
            raise BinaryCarrierError("P3.02 changed an existing ELF section")
    baseline_identity = [
        row for row in before["sections"] if row["name"] == SECTION
    ]
    carried_identity = [
        row for row in after["sections"] if row["name"] == SECTION
    ]
    if baseline_identity or len(carried_identity) != 1:
        raise BinaryCarrierError("P3.02 identity section count differs")
    identity = carried_identity[0]
    baseline_shstr = baseline_by_name[".shstrtab"]
    carried_shstr = carried_by_name[".shstrtab"]
    if _masked_elf_prefix(
        baseline_data,
        baseline_shstr["offset"],
        "baseline pre-identity file prefix",
    ) != _masked_elf_prefix(
        carried_data,
        baseline_shstr["offset"],
        "carried pre-identity file prefix",
    ):
        raise BinaryCarrierError("P3.02 changed pre-identity file bytes or padding")
    if (
        identity["name_offset"] != len(baseline_shstr["content"])
        or identity["type"] != SHT_PROGBITS
        or identity["flags"] != 0
        or identity["address"] != 0
        or identity["size"] != len(CARRIER_PAYLOAD)
        or identity["link"] != 0
        or identity["info"] != 0
        or identity["align"] != 1
        or identity["entsize"] != 0
        or identity["content"] != CARRIER_PAYLOAD
    ):
        raise BinaryCarrierError("P3.02 identity section contract differs")
    expected_shstr = dict(baseline_shstr)
    expected_shstr["offset"] += len(CARRIER_PAYLOAD)
    expected_shstr["size"] += len(SECTION) + 1
    expected_shstr["content"] += SECTION.encode("ascii") + b"\0"
    if _section_exact(carried_shstr) != _section_exact(expected_shstr):
        raise BinaryCarrierError("P3.02 section-name table delta differs")
    expected_section_header_offset = (
        carried_shstr["offset"] + carried_shstr["size"] + 7
    ) & ~7
    expected_file_size = (
        expected_section_header_offset
        + after["section_count"] * SECTION_HEADER.size
    )
    if (
        identity["offset"] != baseline_shstr["offset"]
        or after["section_header_offset"] != expected_section_header_offset
        or any(
            baseline_data[
                baseline_shstr["offset"]
                + baseline_shstr["size"] : before["section_header_offset"]
            ]
        )
        or any(
            carried_data[
                carried_shstr["offset"]
                + carried_shstr["size"] : after["section_header_offset"]
            ]
        )
        or len(carried_data) != expected_file_size
        or len(baseline_data)
        != before["section_header_offset"]
        + before["section_count"] * SECTION_HEADER.size
    ):
        raise BinaryCarrierError("P3.02 ELF file-layout delta differs")
    identity_start = identity["offset"]
    identity_end = identity_start + identity["size"]
    if any(
        row[5] > 0
        and identity_start < row[2] + row[5]
        and identity_end > row[2]
        for row in after["program_headers"]
    ):
        raise BinaryCarrierError("P3.02 identity section overlaps a program segment")
    return {
        "carrier_id": CARRIER_ID,
        "section": SECTION,
        "section_allocatable": False,
        "alloc_sections_byte_identical": list(ALLOC_SECTIONS),
        "elf_header_execution_fields_identical": True,
        "program_headers_byte_identical": True,
        "program_segment_bytes_identical_except_section_table_fields": True,
        "file_prefix_and_padding_identical_except_section_table_fields": True,
        "identity_section_exact": True,
        "identity_in_program_segment": False,
        "baseline_size": len(baseline_data),
        "carried_size": len(carried_data),
        "verified": True,
    }


def apply(path: Path) -> dict:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BinaryCarrierError("P3.02 carrier input is indirect or not regular")
    original = path.read_bytes()
    if original.count(CARRIER_ID.encode("ascii")) != 0:
        raise BinaryCarrierError("P3.02 carrier identity already exists")
    objcopy = _tool("aarch64-linux-gnu-objcopy")
    with tempfile.TemporaryDirectory(prefix="s22-p302-elf-") as name:
        work = Path(name)
        payload = work / "identity"
        output = work / "init"
        payload.write_bytes(CARRIER_PAYLOAD)
        _run(
            [
                objcopy,
                "--add-section",
                f"{SECTION}={payload}",
                "--set-section-flags",
                f"{SECTION}=readonly,contents",
                str(path),
                str(output),
            ],
            "attach P3.02 identity section",
        )
        verified = verify(output, path)
        output.chmod(stat.S_IMODE(metadata.st_mode))
        os.replace(output, path)
    return {
        **verified,
        "input_size": len(original),
        "output_size": path.stat().st_size,
    }
