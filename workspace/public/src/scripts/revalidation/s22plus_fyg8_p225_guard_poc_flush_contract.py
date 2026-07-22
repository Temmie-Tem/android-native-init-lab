#!/usr/bin/env python3
"""Validate the FYG8 P2.25 target guard and PoC cache-flush patch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import build_s22plus_v3435_ramoops_console_dtbo as stock_dt  # noqa: E402
import s22plus_fyg8_p219_same_ring_contract as p219  # noqa: E402
from build_s22plus_ramoops_vendor_boot_enable import (  # noqa: E402
    iter_fdt_blobs,
)


SCHEMA = "s22plus_fyg8_p225_guard_poc_flush_contract_v1"
VERDICT = "PASS_P225_GUARD_AND_POC_FLUSH_IMPLEMENTATION_HOST_ONLY"
TARGET = p219.TARGET
CONFIG = p219.CONFIG
DEFAULT_SOURCE = p219.DEFAULT_SOURCE
DEFAULT_PATCH = Path(
    "workspace/public/src/patches/s22plus_fyg8_p225_guard_poc_flush.patch"
)
DEFAULT_DTBO = stock_dt.DEFAULT_DTBO
DEFAULT_VENDOR_DTB = stock_dt.DEFAULT_VENDOR_DTB
DEFAULT_FDTOVERLAY = stock_dt.DEFAULT_FDTOVERLAY
DEFAULT_LIBFDT = stock_dt.DEFAULT_LIBFDT_DIR / "libfdt.so.1.7.2"

PATCH_SHA256 = "fbbbcc43685f4899fdceb95d4b8b9e92d111fad07bfaf582752aa8c36ccf9254"
PATCHED_FILES = {
    "kernel_platform/common/init/main.c": (
        "6acafc9a0ca1b920a6ec542cf1599761205b0c5a93b1df25e4faa746114806b5"
    ),
    "kernel_platform/common/init/Kconfig": (
        "064f48fb37f8f835c27b8f69b381e14f20774de8e31b29c4eed4d6e3322561b3"
    ),
    "kernel_platform/common/arch/arm64/configs/gki_defconfig": (
        "b696b4da1514d2a7afab2335d400641fced9f08453d257e69aae1002c0414722"
    ),
}

INPUT_PINS = {
    DEFAULT_DTBO: "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c",
    DEFAULT_VENDOR_DTB: (
        "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e"
    ),
    DEFAULT_FDTOVERLAY: (
        "5ceccef2df580cea6fa136e30a66e9ae84efca642583345275ab6b8a21e1e3b2"
    ),
    DEFAULT_LIBFDT: (
        "f9cd7d2d8222f016951dc3dca7c67326a6411fb9f28766f41951591988a11444"
    ),
}

ACTIVE_OVERLAY_INDEX = 10
ACTIVE_OVERLAY_SHA256 = (
    "79eeb405f8eae4c31329183cee1a39dc9103234ed4676450869a8a023fe7429f"
)
ACTIVE_OVERLAY_MODEL = "Samsung G0Q PROJECT (board-id,12)"
APPLICABLE_BASES = {
    0: (
        "Qualcomm Technologies, Inc. Waipio v2 SoC",
        "9d52ae44ee66e271667925bd81dad030e3d96bffd40bdc64e895d52f9227d9a5",
    ),
    1: (
        "Qualcomm Technologies, Inc. Waipio SoC",
        "38bb2575509d831b46c553a953ac552916c95ffdc56998f16286dfc6a74f1dda",
    ),
}
LOG_NODE = "/soc/samsung,kernel_log_buf"
LOG_BASE = 0x800200000
LOG_SIZE = 0x200000
REG_CELLS = (0x8, 0x200000, 0x0, 0x200000)
MEMORY_NODE = "/reserved-memory/sec_debug_region_log@8001FF000"
MEMORY_BASE = 0x8001FF000
MEMORY_SIZE = 0x901000
MEMORY_REG_CELLS = (0x8, 0x1FF000, 0x0, 0x901000)

ENTRY_PROOF = p219.ENTRY_PROOF
USERSPACE_PROOF = p219.USERSPACE_PROOF
UNSAT_PROOF = p219.UNSAT_PROOF
REQUEST = p219.REQUEST
RECORDS = p219.RECORDS


class CheckError(ValueError):
    pass


def _added_lines(text: str) -> list[str]:
    return [
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _function(text: str, start: str, end: str) -> str:
    try:
        begin = text.index(start)
        finish = text.index(end, begin)
    except ValueError as exc:
        raise CheckError(f"required source boundary missing: {start}") from exc
    return text[begin:finish]


def _initializer(added_text: str, name: str) -> bytes:
    match = re.search(
        rf"{name}\[[A-Z0-9_]+\] = \{{(.*?)\n\}};",
        added_text,
        flags=re.DOTALL,
    )
    if match is None:
        raise CheckError(f"byte initializer missing: {name}")
    return bytes(
        int(value, 16)
        for value in re.findall(r"0x([0-9a-fA-F]{2})", match.group(1))
    )


def _text_property(value: bytes | None, label: str) -> str:
    if value is None or not value.endswith(b"\0"):
        raise CheckError(f"{label} is not one terminated string")
    try:
        return value[:-1].decode("ascii")
    except UnicodeDecodeError as exc:
        raise CheckError(f"{label} is not ASCII") from exc


def _u32_property(value: bytes | None, label: str) -> int:
    if value is None or len(value) != 4:
        raise CheckError(f"{label} is not one big-endian u32")
    return int.from_bytes(value, "big")


def decode_reg_cells(
    cells: tuple[int, ...], address_cells: int, size_cells: int, index: int = 0
) -> tuple[int, int]:
    if address_cells <= 0 or size_cells <= 0 or index < 0:
        raise CheckError("invalid reg decoder geometry")
    stride = address_cells + size_cells
    start = index * stride
    selected = cells[start : start + stride]
    if len(selected) != stride:
        raise CheckError("reg property is too short for the requested resource")
    address = 0
    size = 0
    for cell in selected[:address_cells]:
        if not 0 <= cell <= 0xFFFFFFFF:
            raise CheckError("reg address cell is outside u32")
        address = (address << 32) | cell
    for cell in selected[address_cells:]:
        if not 0 <= cell <= 0xFFFFFFFF:
            raise CheckError("reg size cell is outside u32")
        size = (size << 32) | cell
    return address, size


def check_reg_semantics(cells: tuple[int, ...]) -> dict[str, Any]:
    if cells != REG_CELLS:
        raise CheckError(f"stock log reg cells changed: {cells}")
    samsung = decode_reg_cells(cells, 2, 2)
    generic = decode_reg_cells(cells, 1, 1)
    if samsung != (LOG_BASE, LOG_SIZE):
        raise CheckError(f"current-node 2/2 decoding changed: {samsung}")
    if generic != (0x8, LOG_SIZE):
        raise CheckError(f"parent-node 1/1 decoding changed: {generic}")
    return {
        "reg_cells": list(cells),
        "current_node_2_2": {"base": samsung[0], "size": samsung[1]},
        "parent_node_1_1_resource_zero": {
            "base": generic[0],
            "size": generic[1],
        },
        "semantic_mismatch_proven": samsung != generic,
        "verified": True,
    }


def check_record_derivation() -> dict[str, Any]:
    return p219.check_record_derivation()


def check_patch(patch: Path) -> dict[str, Any]:
    if patch.is_symlink() or not patch.is_file():
        raise CheckError("P2.25 patch missing or indirect")
    actual = p219.shared.sha256_file(patch)
    if actual != PATCH_SHA256:
        raise CheckError(f"P2.25 patch SHA256 mismatch: {actual}")
    text = patch.read_text(encoding="ascii")
    targets = re.findall(r"^\+\+\+ b/(.+)$", text, flags=re.MULTILINE)
    if set(targets) != set(p219.shared.BASE_FILES) or len(targets) != len(
        p219.shared.BASE_FILES
    ):
        raise CheckError(f"unexpected patch targets: {targets}")
    added = _added_lines(text)
    added_text = "\n".join(added)
    configs = {
        symbol
        for line in added
        for symbol in re.findall(r"CONFIG_[A-Z0-9_]+", line)
    }
    if configs != {CONFIG}:
        raise CheckError(f"unexpected config symbols: {sorted(configs)}")
    forbidden = (
        "panic(",
        "emergency_restart",
        "kernel_restart",
        "reboot(",
        "filp_open",
        "kernel_write",
        "blkdev_get",
        "submit_bio",
        "ioremap(",
        "sec_log_buf",
        "of_address_to_resource",
        "of_get_address",
        "<linux/of_address.h>",
        "struct resource",
        "resource_size(",
        "smp_wmb()",
    )
    hits = [token for token in forbidden if token in added_text]
    if hits:
        raise CheckError(f"forbidden operation or obsolete guard found: {hits}")
    metadata_writes = re.findall(
        r"head->(?:magic|idx|prev_idx|boot_cnt)\s*=", added_text
    )
    if metadata_writes:
        raise CheckError(f"retained header write found: {metadata_writes}")
    required = (
        ENTRY_PROOF.decode("ascii").strip(),
        USERSPACE_PROOF.decode("ascii").strip(),
        'of_find_node_by_path("/")',
        'strcmp(model, "Samsung G0Q PROJECT (board-id,12)")',
        '"samsung,kernel_log_buf"',
        '"sec,strategy"',
        '"#address-cells"',
        '"#size-cells"',
        'of_get_property(node, "reg", &length)',
        "length != (address_cells + size_cells) * sizeof(*reg)",
        "*base = of_read_number(reg, address_cells)",
        "*size = of_read_number(reg + address_cells, size_cells)",
        "base != S22PLUS_FYG8_P1S_LOG_BASE",
        "size != S22PLUS_FYG8_P1S_LOG_SIZE",
        "seed_idx >= S22PLUS_FYG8_P1S_ENTRY_SIZE",
        "seed_idx >= S22PLUS_FYG8_P1S_UNSAT_SIZE",
        "__flush_dcache_area(slot, proof_size)",
        'proc_create("s22_checkpoint", 0200',
    )
    missing = [token for token in required if token not in added_text]
    if missing:
        raise CheckError(f"required implementation tokens missing: {missing}")
    if added_text.count("[[S22P1U|") != 2:
        raise CheckError("long record family cardinality mismatch")
    if added_text.count("__flush_dcache_area(") != 1:
        raise CheckError("cache flush implementation cardinality mismatch")
    if _initializer(added_text, "s22plus_fyg8_p1s_unsat") != UNSAT_PROOF:
        raise CheckError("kernel UNSAT bytes differ from the fixed contract")
    if _initializer(added_text, "s22plus_fyg8_p1s_request") != REQUEST:
        raise CheckError("kernel request bytes differ from the exact runtime")
    return {
        "path": str(patch),
        "sha256": actual,
        "targets": targets,
        "config": CONFIG,
        "forbidden_hits": hits,
        "header_metadata_writes": metadata_writes,
        "record_bytes_unchanged_from_p219": True,
        "verified": True,
    }


def apply_and_check(source: Path, patch: Path) -> dict[str, Any]:
    p219.shared.check_base_files(source)
    with tempfile.TemporaryDirectory(prefix="s22plus-p225-") as temp_name:
        temporary = Path(temp_name)
        for relative in p219.shared.BASE_FILES:
            destination = temporary / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, destination)
        completed = subprocess.run(
            ["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
            cwd=temporary,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if completed.returncode != 0:
            raise CheckError(f"patch application failed: {completed.stdout[-2000:]}")
        hashes = {
            relative: p219.shared.sha256_file(temporary / relative)
            for relative in p219.shared.BASE_FILES
        }
        if hashes != PATCHED_FILES:
            raise CheckError(f"patched file identities mismatch: {hashes}")
        main = (temporary / "kernel_platform/common/init/main.c").read_text(
            encoding="ascii"
        )
        parser = _function(
            main,
            "static bool s22plus_fyg8_p1s_parse_reg",
            "static struct s22plus_fyg8_p1s_log_head *s22plus_fyg8_p1s_head",
        )
        target = _function(
            main,
            "static struct s22plus_fyg8_p1s_log_head *s22plus_fyg8_p1s_head",
            "static bool s22plus_fyg8_p1s_header_matches",
        )
        store = _function(
            main,
            "static bool s22plus_fyg8_p1s_store",
            "static void s22plus_fyg8_p1s_record_entry",
        )
        entry = _function(
            main,
            "static void s22plus_fyg8_p1s_record_entry",
            "static ssize_t s22plus_fyg8_p1s_write",
        )
        writer = _function(
            main,
            "static ssize_t s22plus_fyg8_p1s_write",
            "static const struct proc_ops s22plus_fyg8_p1s_ops",
        )
        ordered = (
            (
                "parser",
                parser,
                (
                    'of_property_read_u32(node, "#address-cells"',
                    'of_property_read_u32(node, "#size-cells"',
                    "address_cells != S22PLUS_FYG8_P1S_ADDRESS_CELLS",
                    "size_cells != S22PLUS_FYG8_P1S_SIZE_CELLS",
                    'of_get_property(node, "reg", &length)',
                    "length != (address_cells + size_cells) * sizeof(*reg)",
                    "*base = of_read_number(reg, address_cells)",
                    "*size = of_read_number(reg + address_cells, size_cells)",
                ),
            ),
            (
                "target",
                target,
                (
                    'of_find_node_by_path("/")',
                    'of_property_read_string(root, "model", &model)',
                    'strcmp(model, "Samsung G0Q PROJECT (board-id,12)")',
                    "of_find_compatible_node",
                    'of_property_read_u32(log_node, "sec,strategy", &strategy)',
                    "s22plus_fyg8_p1s_parse_reg(log_node, &base, &size)",
                    "base != S22PLUS_FYG8_P1S_LOG_BASE",
                    "size != S22PLUS_FYG8_P1S_LOG_SIZE",
                    "phys_to_virt((phys_addr_t)base)",
                ),
            ),
            (
                "store",
                store,
                (
                    "memcpy(slot, proof, proof_size)",
                    "__flush_dcache_area(slot, proof_size)",
                    "memcmp(slot, proof, proof_size)",
                ),
            ),
            (
                "entry",
                entry,
                (
                    'strcmp(init_filename, "/init")',
                    "task_pid_nr(current) != 1",
                    "s22plus_fyg8_p1s_head()",
                    "READ_ONCE(head->magic) != S22PLUS_FYG8_P1S_LOG_MAGIC",
                    "seed_idx >= S22PLUS_FYG8_P1S_ENTRY_SIZE",
                    "seed_idx >= S22PLUS_FYG8_P1S_UNSAT_SIZE",
                    "s22plus_fyg8_p1s_header_matches(head, seed_idx, seed_boot_cnt)",
                    "s22plus_fyg8_p1s_store(head, proof_pos, proof, proof_size)",
                    "if (!arm_userspace)",
                    "s22plus_fyg8_p1s_state.ready = true",
                ),
            ),
            (
                "writer",
                writer,
                (
                    "task_pid_nr(current) != 1",
                    "!s22plus_fyg8_p1s_state.ready",
                    "copy_from_user(request, buffer, sizeof(request))",
                    "memcmp(request, s22plus_fyg8_p1s_request, sizeof(request))",
                    "s22plus_fyg8_p1s_head()",
                    "memcmp(slot, s22plus_fyg8_p1s_entry",
                    "s22plus_fyg8_p1s_store(head",
                    "s22plus_fyg8_p1s_state.userspace_proven = true",
                ),
            ),
        )
        for label, body, tokens in ordered:
            positions = [body.index(token) for token in tokens]
            if positions != sorted(positions):
                raise CheckError(f"{label} guard/order mismatch")
        if "phys_to_virt" in parser or "__flush_dcache_area" in target:
            raise CheckError("target parser touches retained memory or cache early")
        if store.count("__flush_dcache_area(") != 1 or "smp_wmb" in store:
            raise CheckError("store is not the exact copy/flush/readback sequence")
        if entry.count("s22plus_fyg8_p1s_header_matches(") != 2:
            raise CheckError("entry does not have exact pre/post header checks")
        if writer.count("s22plus_fyg8_p1s_header_matches(") != 2:
            raise CheckError("writer does not have exact pre/post header checks")
        edge = _function(main, "if (ramdisk_execute_command)", "/*\n\t * We try")
        expected_edge = (
            "ret = run_init_process(ramdisk_execute_command);\n"
            "\t\tif (!ret) {\n"
            "\t\t\ts22plus_fyg8_p1s_record_entry(ramdisk_execute_command);"
        )
        if (
            expected_edge not in edge
            or main.count("s22plus_fyg8_p1s_record_entry(") != 3
        ):
            raise CheckError("record hook is not on the unique exec-success edge")
        return {
            "patched_files": hashes,
            "current_node_reg_parser": True,
            "generic_resource_helper_absent": True,
            "copy_poc_flush_readback_order": True,
            "reset_retention_proven": False,
            "pre_post_header_checks": True,
            "source_semantics": True,
            "verified": True,
        }


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def _verify_pin(path: Path, expected: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CheckError(f"pinned stock input missing or indirect: {path}")
    actual = p219.shared.sha256_file(path)
    if actual != expected:
        raise CheckError(f"pinned stock input changed: {path}: {actual}")
    return {"size": path.stat().st_size, "sha256": actual}


def check_stock_dtb(
    root: Path,
    dtbo_path: Path,
    vendor_dtb_path: Path,
    fdtoverlay_path: Path,
    libfdt_path: Path,
) -> dict[str, Any]:
    requested = {
        dtbo_path: INPUT_PINS[DEFAULT_DTBO],
        vendor_dtb_path: INPUT_PINS[DEFAULT_VENDOR_DTB],
        fdtoverlay_path: INPUT_PINS[DEFAULT_FDTOVERLAY],
        libfdt_path: INPUT_PINS[DEFAULT_LIBFDT],
    }
    pins = {str(path.relative_to(root)): _verify_pin(path, digest) for path, digest in requested.items()}
    dtbo = dtbo_path.read_bytes()
    vendor_dtb = vendor_dtb_path.read_bytes()
    header, entries = stock_dt.parse_dt_table(dtbo)
    if header.entry_count != 11 or len(entries) != 11:
        raise CheckError("stock DTBO entry count changed")
    entry = entries[ACTIVE_OVERLAY_INDEX]
    if entry.index != ACTIVE_OVERLAY_INDEX:
        raise CheckError("active rev12 overlay index changed")
    overlay = stock_dt.entry_blob(dtbo, entry)
    if hashlib.sha256(overlay).hexdigest() != ACTIVE_OVERLAY_SHA256:
        raise CheckError("active rev12 overlay identity changed")
    overlay_props = stock_dt.property_map(overlay)
    if _text_property(overlay_props.get(("/", "model")), "overlay model") != ACTIVE_OVERLAY_MODEL:
        raise CheckError("active overlay model changed")

    roots = iter_fdt_blobs(vendor_dtb)
    if len(roots) != 4:
        raise CheckError("stock vendor_boot DTB root count changed")
    selected = [root_blob for root_blob in roots if root_blob.index in APPLICABLE_BASES]
    if [item.index for item in selected] != sorted(APPLICABLE_BASES):
        raise CheckError("applicable Waipio base indices changed")

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="s22plus-p225-dt-") as temp_name:
        temporary = Path(temp_name)
        library_dir = temporary / "lib"
        library_dir.mkdir()
        (library_dir / "libfdt.so.1").symlink_to(libfdt_path)
        environment = os.environ.copy()
        environment["LD_LIBRARY_PATH"] = str(library_dir)
        overlay_file = temporary / "active-rev12.dtbo"
        overlay_file.write_bytes(overlay)
        for root_blob in selected:
            expected_model, expected_digest = APPLICABLE_BASES[root_blob.index]
            actual_digest = hashlib.sha256(root_blob.data).hexdigest()
            if actual_digest != expected_digest:
                raise CheckError(f"vendor base {root_blob.index} identity changed")
            base_file = temporary / f"base-{root_blob.index}.dtb"
            merged_file = temporary / f"merged-{root_blob.index}.dtb"
            base_file.write_bytes(root_blob.data)
            completed = subprocess.run(
                [
                    str(fdtoverlay_path),
                    "-i",
                    str(base_file),
                    "-o",
                    str(merged_file),
                    str(overlay_file),
                ],
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=45,
                check=False,
            )
            if completed.returncode != 0:
                raise CheckError(
                    f"stock overlay merge failed for base {root_blob.index}: "
                    f"{completed.stdout[-1000:]}"
                )
            properties = stock_dt.property_map(merged_file.read_bytes())
            base_model = _text_property(
                properties.get(("/", "model")), "merged base model"
            )
            if base_model != expected_model:
                raise CheckError(f"merged base {root_blob.index} model changed")
            compatible_nodes = [
                path
                for (path, name), value in properties.items()
                if name == "compatible"
                and b"samsung,kernel_log_buf\0" in value
            ]
            if compatible_nodes != [LOG_NODE]:
                raise CheckError(
                    f"merged base {root_blob.index} log-node cardinality changed"
                )
            reg = properties.get((LOG_NODE, "reg"))
            if reg is None or len(reg) != 16:
                raise CheckError("stock log reg is not exactly 16 bytes")
            cells = tuple(
                int.from_bytes(reg[offset : offset + 4], "big")
                for offset in range(0, len(reg), 4)
            )
            if _u32_property(
                properties.get((LOG_NODE, "#address-cells")),
                "log node #address-cells",
            ) != 2 or _u32_property(
                properties.get((LOG_NODE, "#size-cells")),
                "log node #size-cells",
            ) != 2:
                raise CheckError("stock log current-node cell geometry changed")
            if _u32_property(
                properties.get(("/soc", "#address-cells")),
                "soc #address-cells",
            ) != 1 or _u32_property(
                properties.get(("/soc", "#size-cells")),
                "soc #size-cells",
            ) != 1:
                raise CheckError("stock log parent cell geometry changed")
            if _u32_property(
                properties.get((LOG_NODE, "sec,strategy")), "log strategy"
            ) != 3:
                raise CheckError("stock log strategy changed")
            if _text_property(
                properties.get((LOG_NODE, "status")), "log status"
            ) != "okay":
                raise CheckError("stock log status changed")
            if properties.get(
                (LOG_NODE, "sec,use-partial_reserved_mem")
            ) is None:
                raise CheckError("stock partial-reserved-memory mode disappeared")
            memory_phandle = _u32_property(
                properties.get((LOG_NODE, "memory-region")),
                "log memory-region",
            )
            matching_memory_nodes = [
                path
                for (path, name), value in properties.items()
                if name == "phandle"
                and len(value) == 4
                and int.from_bytes(value, "big") == memory_phandle
            ]
            if matching_memory_nodes != [MEMORY_NODE]:
                raise CheckError(
                    "stock log memory-region target changed: "
                    f"{matching_memory_nodes}"
                )
            if _text_property(
                properties.get((MEMORY_NODE, "compatible")),
                "log carveout compatible",
            ) != "samsung,carve-out":
                raise CheckError("stock log carveout compatible changed")
            if (MEMORY_NODE, "no-map") in properties:
                raise CheckError("stock log carveout unexpectedly has no-map")
            if _u32_property(
                properties.get(("/reserved-memory", "#address-cells")),
                "reserved-memory #address-cells",
            ) != 2 or _u32_property(
                properties.get(("/reserved-memory", "#size-cells")),
                "reserved-memory #size-cells",
            ) != 2:
                raise CheckError("stock reserved-memory cell geometry changed")
            memory_reg = properties.get((MEMORY_NODE, "reg"))
            if memory_reg is None or len(memory_reg) != 16:
                raise CheckError("stock log carveout reg is not exactly 16 bytes")
            memory_cells = tuple(
                int.from_bytes(memory_reg[offset : offset + 4], "big")
                for offset in range(0, len(memory_reg), 4)
            )
            if memory_cells != MEMORY_REG_CELLS:
                raise CheckError("stock log carveout reg cells changed")
            memory_base, memory_size = decode_reg_cells(memory_cells, 2, 2)
            if (memory_base, memory_size) != (MEMORY_BASE, MEMORY_SIZE):
                raise CheckError("stock log carveout range changed")
            if not (
                memory_base <= LOG_BASE
                and LOG_BASE + LOG_SIZE <= memory_base + memory_size
            ):
                raise CheckError("stock log range escaped its direct-map carveout")
            results.append(
                {
                    "base_index": root_blob.index,
                    "base_model": base_model,
                    "base_sha256": actual_digest,
                    "node": LOG_NODE,
                    "node_address_cells": 2,
                    "node_size_cells": 2,
                    "parent_address_cells": 1,
                    "parent_size_cells": 1,
                    "strategy": 3,
                    "reg": check_reg_semantics(cells),
                    "direct_map": {
                        "partial_reserved_memory": True,
                        "memory_node": MEMORY_NODE,
                        "memory_phandle": memory_phandle,
                        "memory_base": memory_base,
                        "memory_size": memory_size,
                        "no_map": False,
                        "contains_log_range": True,
                        "verified": True,
                    },
                    "verified": True,
                }
            )
    return {
        "pins": pins,
        "active_overlay_index": ACTIVE_OVERLAY_INDEX,
        "active_overlay_sha256": ACTIVE_OVERLAY_SHA256,
        "active_overlay_model": ACTIVE_OVERLAY_MODEL,
        "applicable_base_indices": sorted(APPLICABLE_BASES),
        "merged_bases": results,
        "generic_parser_regression_proven": all(
            item["reg"]["parent_node_1_1_resource_zero"]["base"] == 0x8
            for item in results
        ),
        "samsung_parser_target_proven": all(
            item["reg"]["current_node_2_2"]["base"] == LOG_BASE
            for item in results
        ),
        "direct_map_prerequisites_proven": all(
            item["direct_map"]["verified"] for item in results
        ),
        "verified": len(results) == 2,
    }


def classify_compiled_blob(blob: bytes, label: str) -> dict[str, Any]:
    try:
        return p219.classify_compiled_blob(blob, label)
    except p219.CheckError as exc:
        raise CheckError(str(exc)) from exc


def run(
    source: Path,
    patch: Path,
    root: Path,
    dtbo: Path,
    vendor_dtb: Path,
    fdtoverlay: Path,
    libfdt: Path,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "record_contract": check_record_derivation(),
        "patch": check_patch(patch),
        "source": apply_and_check(source, patch),
        "stock_dtb": check_stock_dtb(
            root, dtbo, vendor_dtb, fdtoverlay, libfdt
        ),
        "linked_audit": {
            "performed": False,
            "reason": "requires-linked-vmlinux-build-adapter",
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "kernel_build": False,
            "image_created": False,
            "manifest_created": False,
            "reset_retention_proven": False,
            "flash": False,
            "live_authorized": False,
        },
        "verdict": VERDICT,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--dtbo", type=Path, default=DEFAULT_DTBO)
    parser.add_argument("--vendor-dtb", type=Path, default=DEFAULT_VENDOR_DTB)
    parser.add_argument("--fdtoverlay", type=Path, default=DEFAULT_FDTOVERLAY)
    parser.add_argument("--libfdt", type=Path, default=DEFAULT_LIBFDT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = p219.shared.repo_root()
    source = _resolve(root, args.source)
    patch = _resolve(root, args.patch)
    dtbo = _resolve(root, args.dtbo)
    vendor_dtb = _resolve(root, args.vendor_dtb)
    fdtoverlay = _resolve(root, args.fdtoverlay)
    libfdt = _resolve(root, args.libfdt)
    try:
        result = run(
            source, patch, root, dtbo, vendor_dtb, fdtoverlay, libfdt
        )
    except (
        CheckError,
        p219.CheckError,
        p219.design.ContractError,
        p219.shared.CheckError,
        stock_dt.BuildError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
