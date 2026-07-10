#!/usr/bin/env python3
"""Build the host-only S22+ V3435 ramoops console/dmesg DTBO candidate.

The stock FYG8 ramoops region is 2 MiB and assigns all of it to pmsg. This
builder preserves that reserved-memory allocation, enables the existing node,
and repartitions the same 2 MiB for pmsg, console, and panic/oops records.

It never contacts a device, reboots, flashes, or authorizes live work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_ramoops_dtbo_enable import (
    DEFAULT_ODIN,
    DTBO_AVB_DESCRIPTOR_DIGEST_HEX,
    DTBO_AVB_HASH_IMAGE_SIZE,
    DTBO_AVB_SALT_HEX,
    decode_string_list,
    dtbo_avb_digest,
    iter_fdt_blobs,
    parse_fdt_props,
    repo_root,
    resolve,
    run_odin_parse_gate,
    sha256_file,
    write_lz4_store,
    write_single_member_tar_md5,
)
from build_s22plus_direct_p3_boot import display_path, tar_members
from s22plus_v3434_boot_boundary_map import extract_ikconfig


SCHEMA = "s22plus_v3435_ramoops_console_dtbo_contract_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

DEFAULT_DTBO = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/dtbo.img"
)
DEFAULT_VENDOR_DTB = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/dtb"
)
DEFAULT_KERNEL = Path(
    "workspace/private/outputs/s22plus_native_init/"
    "v3432_pid1_keystone_v0_1/magiskboot-work/kernel"
)
DEFAULT_SOURCE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
DEFAULT_FDTPUT = Path("workspace/private/tools/dtc_pkg/sysroot/usr/bin/fdtput")
DEFAULT_FDTOVERLAY = Path(
    "workspace/private/tools/dtc_pkg/sysroot/usr/bin/fdtoverlay"
)
DEFAULT_LIBFDT_DIR = Path(
    "workspace/private/tools/dtc_pkg/sysroot/usr/lib/x86_64-linux-gnu"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_v3435_ramoops_console_dtbo_v0_1"
)
DEFAULT_CONTRACT_OUT = Path(
    "docs/plans/s22plus-v3435-ramoops-console-dtbo-contract.json"
)

PINS = {
    DEFAULT_DTBO: "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c",
    DEFAULT_VENDOR_DTB: "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e",
    DEFAULT_KERNEL: "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff",
    DEFAULT_SOURCE: "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
    DEFAULT_FDTPUT: "1e2d249c4f3d302870471bd86e6f6cb94ba94f4596a881ab1ac9ef663cb4f348",
    DEFAULT_FDTOVERLAY: "5ceccef2df580cea6fa136e30a66e9ae84efca642583345275ab6b8a21e1e3b2",
    DEFAULT_LIBFDT_DIR / "libfdt.so.1.7.2": (
        "f9cd7d2d8222f016951dc3dca7c67326a6411fb9f28766f41951591988a11444"
    ),
}

RAM_SOURCE = "kernel_platform/common/fs/pstore/ram.c"
PSTORE_SOURCE = "kernel_platform/common/fs/pstore/platform.c"
RAMOOPS_NODE = "/reserved-memory/ramoops_region"
FIXUP_NODE = "/__fixups__"
OVERLAY_NODE = "/fragment@116/__overlay__"
FIXUP_PROPERTY = "ramoops_mem"
FIXUP_TARGET = "/fragment@116:target:0"

REGION_SIZE = 0x200000
PMSG_SIZE = 0x100000
CONSOLE_SIZE = 0x80000
RECORD_SIZE = 0x40000
FTRACE_SIZE = 0
DMESG_SIZE = REGION_SIZE - PMSG_SIZE - CONSOLE_SIZE - FTRACE_SIZE
DMESG_RECORD_COUNT = DMESG_SIZE // RECORD_SIZE

DT_TABLE_MAGIC = 0xD7B7AB1E
EXPECTED_DT_ENTRY_COUNT = 11
EXPECTED_VENDOR_DTB_COUNT = 4
EXPECTED_TARGET_OVERLAYS = 2


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class DtTableHeader:
    magic: int
    total_size: int
    header_size: int
    entry_size: int
    entry_count: int
    entries_offset: int
    page_size: int
    version: int


@dataclass(frozen=True)
class DtTableEntry:
    index: int
    dt_size: int
    dt_offset: int
    ident: int
    revision: int
    custom0: int
    custom1: int
    custom2: int
    custom3: int


def verify_pin(path: Path, expected: str) -> str:
    if not path.is_file():
        raise BuildError(f"missing pinned input: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise BuildError(f"pin mismatch for {path}: {actual} != {expected}")
    return actual


def parse_dt_table(image: bytes) -> tuple[DtTableHeader, list[DtTableEntry]]:
    if len(image) < 32:
        raise BuildError("DTBO image is too small for the DT table header")
    fields = struct.unpack_from(">8I", image, 0)
    header = DtTableHeader(*fields)
    if header.magic != DT_TABLE_MAGIC:
        raise BuildError(f"DT table magic mismatch: 0x{header.magic:08x}")
    if header.header_size != 32 or header.entry_size != 32:
        raise BuildError("unexpected DT table header or entry size")
    if header.entry_count != EXPECTED_DT_ENTRY_COUNT:
        raise BuildError(f"unexpected DT entry count: {header.entry_count}")
    if header.entries_offset != header.header_size:
        raise BuildError("DT entry table is not directly after the header")
    table_end = header.entries_offset + header.entry_count * header.entry_size
    if table_end > len(image):
        raise BuildError("DT entry table exceeds image")

    entries: list[DtTableEntry] = []
    for index in range(header.entry_count):
        offset = header.entries_offset + index * header.entry_size
        values = struct.unpack_from(">8I", image, offset)
        entries.append(DtTableEntry(index, *values))

    if entries[0].dt_offset != table_end:
        raise BuildError("first FDT does not start at the end of the entry table")
    cursor = entries[0].dt_offset
    for entry in entries:
        if entry.dt_offset != cursor:
            raise BuildError(f"non-contiguous FDT entry {entry.index}")
        if entry.dt_offset + entry.dt_size > header.total_size:
            raise BuildError(f"FDT entry {entry.index} exceeds DT table total")
        cursor += entry.dt_size
    if cursor != header.total_size:
        raise BuildError("DT table total does not end after the final FDT")
    return header, entries


def entry_blob(image: bytes, entry: DtTableEntry) -> bytes:
    return image[entry.dt_offset : entry.dt_offset + entry.dt_size]


def property_map(blob: bytes) -> dict[tuple[str, str], bytes]:
    blobs = iter_fdt_blobs(blob)
    if len(blobs) != 1 or blobs[0].offset != 0 or blobs[0].totalsize != len(blob):
        raise BuildError("expected one exact FDT blob")
    output: dict[tuple[str, str], bytes] = {}
    for prop in parse_fdt_props(blobs[0]):
        key = (prop.path, prop.name)
        if key in output:
            raise BuildError(f"duplicate FDT property: {key}")
        output[key] = prop.value
    return output


def compact_fdt_strings(blob: bytes, target_size: int) -> tuple[bytes, dict[str, int]]:
    if len(blob) < 40:
        raise BuildError("FDT is too small to compact")
    header = list(struct.unpack_from(">10I", blob, 0))
    magic, _total, off_struct, off_strings, _off_mem, _version, _last, _cpu, size_strings, size_struct = header
    if magic != 0xD00DFEED:
        raise BuildError("FDT magic mismatch during string compaction")
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    if struct_end != off_strings or strings_end > len(blob):
        raise BuildError("FDT sections are not contiguous before compaction")

    mutable_struct = bytearray(blob[off_struct:struct_end])
    strings = blob[off_strings:strings_end]
    references: list[tuple[int, bytes]] = []
    position = 0
    while position + 4 <= len(mutable_struct):
        token = struct.unpack_from(">I", mutable_struct, position)[0]
        position += 4
        if token == 1:
            end = mutable_struct.find(0, position)
            if end < 0:
                raise BuildError("unterminated FDT node during compaction")
            position = (end + 4) & ~3
        elif token in (2, 4):
            continue
        elif token == 3:
            if position + 8 > len(mutable_struct):
                raise BuildError("truncated FDT property during compaction")
            length, name_offset = struct.unpack_from(">II", mutable_struct, position)
            if name_offset >= len(strings):
                raise BuildError("FDT property name offset outside string table")
            name_end = strings.find(b"\0", name_offset)
            if name_end < 0:
                raise BuildError("unterminated FDT property name")
            references.append((position + 4, strings[name_offset:name_end]))
            position = (position + 8 + length + 3) & ~3
        elif token == 9:
            break
        else:
            raise BuildError(f"unknown FDT token during compaction: {token}")

    names = {name for _, name in references}
    roots = sorted(
        name for name in names if not any(other != name and other.endswith(name) for other in names)
    )
    compact = bytearray()
    root_offsets: dict[bytes, int] = {}
    for name in roots:
        root_offsets[name] = len(compact)
        compact.extend(name)
        compact.append(0)
    name_offsets: dict[bytes, int] = {}
    for name in names:
        candidates = [
            offset + len(root) - len(name)
            for root, offset in root_offsets.items()
            if root.endswith(name)
        ]
        if not candidates:
            raise BuildError(f"could not place FDT property name: {name!r}")
        name_offsets[name] = min(candidates)
    for nameoff_position, name in references:
        struct.pack_into(">I", mutable_struct, nameoff_position, name_offsets[name])

    minimum_size = off_strings + len(compact)
    if minimum_size > target_size:
        raise BuildError(
            f"compacted FDT still exceeds original size: {minimum_size} > {target_size}"
        )
    header[1] = target_size
    header[8] = len(compact)
    rebuilt = bytearray(target_size)
    rebuilt[:off_struct] = blob[:off_struct]
    struct.pack_into(">10I", rebuilt, 0, *header)
    rebuilt[off_struct:off_strings] = mutable_struct
    rebuilt[off_strings : off_strings + len(compact)] = compact
    result = bytes(rebuilt)
    if property_map(result) != property_map(blob):
        raise BuildError("FDT string compaction changed property semantics")
    return result, {
        "string_bytes_before": size_strings,
        "string_bytes_after": len(compact),
        "string_bytes_reclaimed": size_strings - len(compact),
        "minimum_size_after_compaction": minimum_size,
        "final_padded_size": target_size,
        "trailing_padding": target_size - minimum_size,
    }


def be_u32(value: bytes, label: str) -> int:
    if len(value) != 4:
        raise BuildError(f"{label} is not one u32 cell")
    return struct.unpack(">I", value)[0]


def be_size(value: bytes, label: str) -> int:
    if len(value) == 4:
        return struct.unpack(">I", value)[0]
    if len(value) == 8:
        return struct.unpack(">Q", value)[0]
    raise BuildError(f"{label} is neither one nor two cells")


def overlay_targets_ramoops(props: dict[tuple[str, str], bytes]) -> bool:
    value = props.get((FIXUP_NODE, FIXUP_PROPERTY), b"")
    return FIXUP_TARGET in decode_string_list(value)


def analyze_vendor_dtb(image: bytes) -> list[dict[str, Any]]:
    blobs = iter_fdt_blobs(image)
    if len(blobs) != EXPECTED_VENDOR_DTB_COUNT:
        raise BuildError(f"unexpected vendor DTB count: {len(blobs)}")
    output: list[dict[str, Any]] = []
    for blob in blobs:
        props = property_map(blob.data)
        compatible = decode_string_list(props[(RAMOOPS_NODE, "compatible")])
        size = be_size(props[(RAMOOPS_NODE, "size")], "ramoops size")
        pmsg = be_u32(props[(RAMOOPS_NODE, "pmsg-size")], "pmsg-size")
        if compatible != ["ramoops"] or size != REGION_SIZE or pmsg != REGION_SIZE:
            raise BuildError(f"vendor DTB {blob.index} ramoops baseline drift")
        forbidden = [
            name
            for name in ("record-size", "console-size", "ftrace-size", "reg", "status")
            if (RAMOOPS_NODE, name) in props
        ]
        if forbidden:
            raise BuildError(
                f"vendor DTB {blob.index} has unexpected ramoops properties: {forbidden}"
            )
        output.append(
            {
                "index": blob.index,
                "offset": blob.offset,
                "totalsize": blob.totalsize,
                "compatible": compatible,
                "size": size,
                "allocation": "dynamic_reserved_memory_size_plus_alloc_ranges",
                "has_reg": False,
                "pmsg_size": pmsg,
                "console_size": 0,
                "record_size": 0,
                "dmesg_size": 0,
            }
        )
    return output


def read_tar_sources(archive: Path) -> dict[str, str]:
    wanted = {RAM_SOURCE, PSTORE_SOURCE}
    output: dict[str, str] = {}
    with tarfile.open(archive, "r:gz") as tar:
        for info in tar:
            if info.name not in wanted:
                continue
            stream = tar.extractfile(info)
            if stream is None:
                raise BuildError(f"could not extract {info.name}")
            output[info.name] = stream.read().decode("utf-8")
            if len(output) == len(wanted):
                break
    missing = wanted.difference(output)
    if missing:
        raise BuildError(f"missing source members: {sorted(missing)}")
    return output


def source_contract(source: Path, kernel: Path) -> dict[str, Any]:
    config = extract_ikconfig(kernel)
    expected_config = {
        "CONFIG_PSTORE": "y",
        "CONFIG_PSTORE_CONSOLE": "y",
        "CONFIG_PSTORE_PMSG": "y",
        "CONFIG_PSTORE_RAM": "y",
    }
    for key, value in expected_config.items():
        if config.get(key) != value:
            raise BuildError(f"kernel config mismatch {key}: {config.get(key)} != {value}")

    sources = read_tar_sources(source)
    ram = sources[RAM_SOURCE]
    platform = sources[PSTORE_SOURCE]
    required_ram = {
        "zero_missing_record_size": 'parse_u32("record-size", pdata->record_size, 0);',
        "zero_missing_console_size": 'parse_u32("console-size", pdata->console_size, 0);',
        "zero_missing_ftrace_size": 'parse_u32("ftrace-size", pdata->ftrace_size, 0);',
        "zero_missing_pmsg_size": 'parse_u32("pmsg-size", pdata->pmsg_size, 0);',
        "dump_remainder": (
            "dump_mem_sz = cxt->size - cxt->console_size - cxt->ftrace_size\n"
            "\t\t\t- cxt->pmsg_size;"
        ),
        "dmesg_flag": "cxt->pstore.flags |= PSTORE_FLAGS_DMESG;",
        "console_flag": "cxt->pstore.flags |= PSTORE_FLAGS_CONSOLE;",
        "pmsg_flag": "cxt->pstore.flags |= PSTORE_FLAGS_PMSG;",
    }
    required_platform = {
        "console_enabled": (
            "pstore_console.flags = CON_PRINTBUFFER | CON_ENABLED | CON_ANYTIME;"
        ),
        "console_registration": "register_console(&pstore_console);",
    }
    for label, needle in required_ram.items():
        if needle not in ram:
            raise BuildError(f"ramoops source proof missing: {label}")
    for label, needle in required_platform.items():
        if needle not in platform:
            raise BuildError(f"pstore source proof missing: {label}")
    return {
        "kernel_config": expected_config,
        "ramoops_size_defaults": "missing record/console/ftrace properties parse as zero",
        "dmesg_space_formula": "region - console - ftrace - pmsg",
        "frontend_flags": {
            "dmesg": "set only when at least one record zone exists",
            "console": "set only when console-size is nonzero",
            "pmsg": "set only when pmsg-size is nonzero",
        },
        "console_null_effect": (
            "not a blocker: pstore registers its own CON_ENABLED console when "
            "PSTORE_FLAGS_CONSOLE is present"
        ),
    }


def tool_env(libfdt_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    current = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = str(libfdt_dir) + (":" + current if current else "")
    return env


def run_checked(command: list[str], env: dict[str, str]) -> None:
    result = subprocess.run(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=45,
    )
    if result.returncode != 0:
        raise BuildError(
            f"command failed rc={result.returncode}: {' '.join(command)}\n"
            f"{result.stdout.strip()}"
        )


def patch_overlay_blob(
    blob: bytes, fdtput: Path, libfdt_dir: Path, temp_dir: Path
) -> tuple[bytes, dict[str, Any]]:
    before = property_map(blob)
    if not overlay_targets_ramoops(before):
        raise BuildError("attempted to patch a non-ramoops overlay")
    if before.get((OVERLAY_NODE, "status")) != b"disabled\0":
        raise BuildError("ramoops overlay status is not disabled")
    for name in ("pmsg-size", "console-size", "record-size"):
        if (OVERLAY_NODE, name) in before:
            raise BuildError(f"ramoops overlay already has {name}")

    target = temp_dir / f"overlay-{hashlib.sha256(blob).hexdigest()[:16]}.dtbo"
    target.write_bytes(blob)
    env = tool_env(libfdt_dir)
    updates = (
        ("s", "status", "okay"),
        ("x", "pmsg-size", f"{PMSG_SIZE:x}"),
        ("x", "console-size", f"{CONSOLE_SIZE:x}"),
        ("x", "record-size", f"{RECORD_SIZE:x}"),
    )
    for value_type, name, value in updates:
        run_checked(
            [str(fdtput), "-t", value_type, str(target), OVERLAY_NODE, name, value],
            env,
        )

    expanded = target.read_bytes()
    patched, compaction = compact_fdt_strings(expanded, len(blob))
    after = property_map(patched)
    allowed = {
        (OVERLAY_NODE, "status"),
        (OVERLAY_NODE, "pmsg-size"),
        (OVERLAY_NODE, "console-size"),
        (OVERLAY_NODE, "record-size"),
    }
    before_stable = {key: value for key, value in before.items() if key not in allowed}
    after_stable = {key: value for key, value in after.items() if key not in allowed}
    if before_stable != after_stable:
        raise BuildError("overlay semantic diff escaped the ramoops property allowlist")
    expected = {
        (OVERLAY_NODE, "status"): b"okay\0",
        (OVERLAY_NODE, "pmsg-size"): struct.pack(">I", PMSG_SIZE),
        (OVERLAY_NODE, "console-size"): struct.pack(">I", CONSOLE_SIZE),
        (OVERLAY_NODE, "record-size"): struct.pack(">I", RECORD_SIZE),
    }
    for key, value in expected.items():
        if after.get(key) != value:
            raise BuildError(f"patched overlay value mismatch: {key}")
    return patched, {
        "old_size": len(blob),
        "new_size": len(patched),
        "growth": len(patched) - len(blob),
        "fdtput_expanded_size": len(expanded),
        "string_compaction": compaction,
        "changed_properties": [
            "status=okay",
            f"pmsg-size=0x{PMSG_SIZE:x}",
            f"console-size=0x{CONSOLE_SIZE:x}",
            f"record-size=0x{RECORD_SIZE:x}",
        ],
        "semantic_diff_allowlist_only": True,
    }


def rebuild_dtbo(
    stock: bytes, fdtput: Path, libfdt_dir: Path, temp_dir: Path
) -> tuple[bytes, dict[str, Any], list[bytes]]:
    header, entries = parse_dt_table(stock)
    signer_trailer = stock[header.total_size : DTBO_AVB_HASH_IMAGE_SIZE]
    if len(signer_trailer) != 512 or not signer_trailer.startswith(b"SignerVer02\0"):
        raise BuildError("Samsung DTBO signer trailer shape drift")

    blobs: list[bytes] = []
    patched_indices: list[int] = []
    patches: list[dict[str, Any]] = []
    for entry in entries:
        blob = entry_blob(stock, entry)
        props = property_map(blob)
        if overlay_targets_ramoops(props):
            blob, patch = patch_overlay_blob(blob, fdtput, libfdt_dir, temp_dir)
            patched_indices.append(entry.index)
            patch["entry_index"] = entry.index
            patches.append(patch)
        blobs.append(blob)
    if len(patched_indices) != EXPECTED_TARGET_OVERLAYS:
        raise BuildError(f"expected two ramoops overlays, found {patched_indices}")

    candidate_mutable = bytearray(stock)
    for entry, blob in zip(entries, blobs):
        if len(blob) != entry.dt_size:
            raise BuildError(
                f"FDT entry {entry.index} size changed after compaction: "
                f"{len(blob)} != {entry.dt_size}"
            )
        candidate_mutable[entry.dt_offset : entry.dt_offset + entry.dt_size] = blob
    candidate = bytes(candidate_mutable)
    candidate_header, candidate_entries = parse_dt_table(candidate)
    if candidate_header != header or candidate_entries != entries:
        raise BuildError("DT table header or entries changed")
    for entry, blob in zip(candidate_entries, blobs):
        if entry_blob(candidate, entry) != blob:
            raise BuildError(f"rebuilt FDT entry {entry.index} mismatch")
    if candidate[header.total_size:] != stock[header.total_size:]:
        raise BuildError("Samsung signer trailer or AVB region changed")

    return candidate, {
        "stock_header": asdict(header),
        "candidate_header": asdict(candidate_header),
        "patched_entry_indices": patched_indices,
        "patches": patches,
        "dt_table_header_and_entries_preserved": True,
        "all_fdt_entry_sizes_preserved": True,
        "samsung_signer_trailer_size": len(signer_trailer),
        "samsung_signer_trailer_sha256": hashlib.sha256(signer_trailer).hexdigest(),
        "samsung_signer_trailer_preserved": True,
        "raw_image_size_preserved": True,
        "all_bytes_after_dt_table_preserved_from_offset": header.total_size,
    }, blobs


def verify_overlay_applications(
    vendor_dtb: bytes,
    patched_blobs: list[bytes],
    fdt_overlay: Path,
    libfdt_dir: Path,
    temp_dir: Path,
) -> list[dict[str, Any]]:
    roots = iter_fdt_blobs(vendor_dtb)
    target_overlays = [
        (index, blob)
        for index, blob in enumerate(patched_blobs)
        if overlay_targets_ramoops(property_map(blob))
    ]
    results: list[dict[str, Any]] = []
    env = tool_env(libfdt_dir)
    for root in roots:
        base = temp_dir / f"vendor-root-{root.index}.dtb"
        base.write_bytes(root.data)
        for overlay_index, overlay_data in target_overlays:
            overlay = temp_dir / f"candidate-overlay-{overlay_index}.dtbo"
            applied = temp_dir / f"applied-{root.index}-{overlay_index}.dtb"
            overlay.write_bytes(overlay_data)
            run_checked(
                [
                    str(fdt_overlay),
                    "-i",
                    str(base),
                    "-o",
                    str(applied),
                    str(overlay),
                ],
                env,
            )
            props = property_map(applied.read_bytes())
            values = {
                "status": decode_string_list(props[(RAMOOPS_NODE, "status")]),
                "size": be_size(props[(RAMOOPS_NODE, "size")], "applied size"),
                "pmsg_size": be_u32(
                    props[(RAMOOPS_NODE, "pmsg-size")], "applied pmsg-size"
                ),
                "console_size": be_u32(
                    props[(RAMOOPS_NODE, "console-size")],
                    "applied console-size",
                ),
                "record_size": be_u32(
                    props[(RAMOOPS_NODE, "record-size")], "applied record-size"
                ),
                "has_reg": (RAMOOPS_NODE, "reg") in props,
            }
            expected = {
                "status": ["okay"],
                "size": REGION_SIZE,
                "pmsg_size": PMSG_SIZE,
                "console_size": CONSOLE_SIZE,
                "record_size": RECORD_SIZE,
                "has_reg": False,
            }
            if values != expected:
                raise BuildError(
                    f"overlay {overlay_index} on vendor root {root.index} "
                    f"produced {values}, expected {expected}"
                )
            results.append(
                {
                    "vendor_root_index": root.index,
                    "overlay_entry_index": overlay_index,
                    **values,
                    "pass": True,
                }
            )
    if len(results) != EXPECTED_VENDOR_DTB_COUNT * EXPECTED_TARGET_OVERLAYS:
        raise BuildError("not every target overlay was tested on every vendor root")
    return results


def summarize_odin_parse(output: str) -> dict[str, bool]:
    if output == "skipped":
        return {
            "executed": False,
            "archive_check_reached": False,
            "invalid_device_boundary_reached": False,
        }
    return {
        "executed": True,
        "archive_check_reached": "Check file :" in output,
        "invalid_device_boundary_reached": (
            "No such file or directory" in output and "usb device Fail" in output
        ),
    }


def build_contract(
    root: Path,
    dtbo: Path,
    vendor_dtb: Path,
    kernel: Path,
    source: Path,
    fdtput: Path,
    fdt_overlay: Path,
    libfdt_dir: Path,
    out_dir: Path,
    odin: Path,
    run_odin_gate: bool,
) -> dict[str, Any]:
    requested = {
        dtbo: PINS[DEFAULT_DTBO],
        vendor_dtb: PINS[DEFAULT_VENDOR_DTB],
        kernel: PINS[DEFAULT_KERNEL],
        source: PINS[DEFAULT_SOURCE],
        fdtput: PINS[DEFAULT_FDTPUT],
        fdt_overlay: PINS[DEFAULT_FDTOVERLAY],
        libfdt_dir / "libfdt.so.1.7.2": PINS[
            DEFAULT_LIBFDT_DIR / "libfdt.so.1.7.2"
        ],
    }
    verified = {display_path(root, path): verify_pin(path, pin) for path, pin in requested.items()}

    stock = dtbo.read_bytes()
    vendor = vendor_dtb.read_bytes()
    vendor_summary = analyze_vendor_dtb(vendor)
    source_summary = source_contract(source, kernel)

    with tempfile.TemporaryDirectory(prefix="s22-v3435-dtbo-") as temp:
        temp_dir = Path(temp)
        candidate, container, blobs = rebuild_dtbo(
            stock, fdtput, libfdt_dir, temp_dir
        )
        applications = verify_overlay_applications(
            vendor, blobs, fdt_overlay, libfdt_dir, temp_dir
        )

    build_dir = out_dir / "build"
    candidate_dir = out_dir / "candidate_odin4"
    rollback_dir = out_dir / "stock_rollback_odin4"
    build_dir.mkdir(parents=True)
    candidate_dir.mkdir(parents=True)
    rollback_dir.mkdir(parents=True)
    stock_raw = build_dir / "stock_dtbo.img"
    candidate_raw = build_dir / "dtbo.img"
    stock_raw.write_bytes(stock)
    candidate_raw.write_bytes(candidate)
    candidate_lz4 = candidate_dir / "dtbo.img.lz4"
    rollback_lz4 = rollback_dir / "dtbo.img.lz4"
    write_lz4_store(candidate_raw, candidate_lz4)
    write_lz4_store(stock_raw, rollback_lz4)
    candidate_tar = candidate_dir / "AP.tar"
    candidate_ap = candidate_dir / "AP.tar.md5"
    rollback_tar = rollback_dir / "AP.tar"
    rollback_ap = rollback_dir / "AP.tar.md5"
    write_single_member_tar_md5(candidate_lz4, "dtbo.img.lz4", candidate_tar, candidate_ap)
    write_single_member_tar_md5(rollback_lz4, "dtbo.img.lz4", rollback_tar, rollback_ap)
    if tar_members(candidate_ap) != ["dtbo.img.lz4"]:
        raise BuildError("candidate AP is not single-member dtbo-only")
    if tar_members(rollback_ap) != ["dtbo.img.lz4"]:
        raise BuildError("rollback AP is not single-member dtbo-only")

    odin_candidate = "skipped"
    odin_rollback = "skipped"
    if run_odin_gate:
        odin_candidate = run_odin_parse_gate(odin, candidate_ap)
        odin_rollback = run_odin_parse_gate(odin, rollback_ap)
        (candidate_dir / "parse_dry_run_invalid_device.txt").write_text(
            odin_candidate, encoding="utf-8"
        )
        (rollback_dir / "parse_dry_run_invalid_device.txt").write_text(
            odin_rollback, encoding="utf-8"
        )

    stock_digest = dtbo_avb_digest(stock)
    candidate_digest = dtbo_avb_digest(candidate)
    if stock_digest != DTBO_AVB_DESCRIPTOR_DIGEST_HEX:
        raise BuildError("stock AVB descriptor digest mismatch")

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "verdict": "HOST_BUILD_PASS_NO_LIVE",
        "safety": {
            "host_only": True,
            "device_contact": False,
            "reboot": False,
            "flash": False,
            "live_authorized": False,
            "future_partition_scope": "dtbo only after a fresh exception",
            "future_positive_control_first": True,
            "direct_pid1_candidate_authorized": False,
        },
        "objective": {
            "final_state": "native/Debian without Android userspace",
            "stock_pid1_supervisor": "interim bring-up and recovery fallback only",
            "current_unit": "enable a real pre/early-userspace ramoops console/dmesg witness",
        },
        "pins": verified,
        "source_contract": source_summary,
        "stock_ramoops": {
            "vendor_dtb_variants": vendor_summary,
            "region_size": REGION_SIZE,
            "pmsg_size": REGION_SIZE,
            "console_size": 0,
            "record_size": 0,
            "dmesg_size": 0,
            "root_cause": "pmsg consumes the entire region",
        },
        "candidate_layout": {
            "region_size": REGION_SIZE,
            "pmsg_size": PMSG_SIZE,
            "console_size": CONSOLE_SIZE,
            "ftrace_size": FTRACE_SIZE,
            "record_size": RECORD_SIZE,
            "dmesg_size": DMESG_SIZE,
            "dmesg_record_count": DMESG_RECORD_COUNT,
            "sum_exact": PMSG_SIZE + CONSOLE_SIZE + FTRACE_SIZE + DMESG_SIZE
            == REGION_SIZE,
            "all_nonzero_sizes_power_of_two": all(
                value > 0 and value & (value - 1) == 0
                for value in (PMSG_SIZE, CONSOLE_SIZE, RECORD_SIZE)
            ),
            "new_reserved_region": False,
            "cmdline_change": False,
        },
        "candidate": {
            "container": container,
            "overlay_application_matrix": applications,
            "raw_size": len(candidate),
            "raw_sha256": sha256_file(candidate_raw),
            "lz4_sha256": sha256_file(candidate_lz4),
            "ap_tar_sha256": sha256_file(candidate_tar),
            "ap_tar_md5_sha256": sha256_file(candidate_ap),
            "ap_members": ["dtbo.img.lz4"],
            "avb_hash_descriptor": {
                "hash_image_size": DTBO_AVB_HASH_IMAGE_SIZE,
                "salt_hex": DTBO_AVB_SALT_HEX,
                "stock_digest": stock_digest,
                "candidate_recomputed_digest": candidate_digest,
                "candidate_matches_stock_descriptor": candidate_digest
                == DTBO_AVB_DESCRIPTOR_DIGEST_HEX,
                "metadata_tail_preserved": True,
                "future_live_requires_verified_boot_disabled_or_resigning": True,
            },
            "paths": {
                "raw": display_path(root, candidate_raw),
                "ap_tar_md5": display_path(root, candidate_ap),
                "rollback_ap_tar_md5": display_path(root, rollback_ap),
            },
            "odin_parse_gate": {
                "candidate": summarize_odin_parse(odin_candidate),
                "rollback": summarize_odin_parse(odin_rollback),
            },
        },
        "future_live_gate": {
            "authorized": False,
            "first_action": "Android positive control, not direct PID1",
            "requires": [
                "fresh SHA-pinned DTBO exception",
                "fresh one-shot intentional-panic exception",
                "known Magisk boot baseline",
                "stock DTBO rollback staged",
                "live DT property and ramoops backend-registration proof before panic",
            ],
            "pass": "run-bound marker recovered from console/dmesg/pmsg after reset",
            "fail": "retire ramoops and move to EUD/UART",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dtbo", type=Path, default=DEFAULT_DTBO)
    parser.add_argument("--vendor-dtb", type=Path, default=DEFAULT_VENDOR_DTB)
    parser.add_argument("--kernel", type=Path, default=DEFAULT_KERNEL)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--fdtput", type=Path, default=DEFAULT_FDTPUT)
    parser.add_argument("--fdtoverlay", type=Path, default=DEFAULT_FDTOVERLAY)
    parser.add_argument("--libfdt-dir", type=Path, default=DEFAULT_LIBFDT_DIR)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--contract-out", type=Path, default=DEFAULT_CONTRACT_OUT)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    dtbo = resolve(root, args.dtbo)
    vendor_dtb = resolve(root, args.vendor_dtb)
    kernel = resolve(root, args.kernel)
    source = resolve(root, args.source)
    fdtput = resolve(root, args.fdtput)
    fdt_overlay = resolve(root, args.fdtoverlay)
    libfdt_dir = resolve(root, args.libfdt_dir)
    odin = resolve(root, args.odin)
    out_dir = resolve(root, args.out)
    contract_out = resolve(root, args.contract_out)
    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    contract = build_contract(
        root,
        dtbo,
        vendor_dtb,
        kernel,
        source,
        fdtput,
        fdt_overlay,
        libfdt_dir,
        out_dir,
        odin,
        not args.no_odin_parse_gate,
    )
    rendered = json.dumps(contract, indent=2, sort_keys=True) + "\n"
    contract_out.parent.mkdir(parents=True, exist_ok=True)
    contract_out.write_text(rendered, encoding="utf-8")
    private_manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contract": contract,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(private_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
