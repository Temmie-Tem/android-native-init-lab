#!/usr/bin/env python3
"""Build a byte-preserving S22+ vendor_boot candidate that enables ramoops.

This script is host-only. It does not flash, reboot, or touch a connected
device.

Unlike build_s22plus_ramoops_vendor_boot_enable.py, this builder does not use
magiskboot to repack vendor_boot. It parses the stock FYG8 vendor_boot v4 image,
patches the embedded DTB payload directly, updates only the vendor_boot header
dtb_size field, and verifies that every changed byte is confined to:

- the 4-byte dtb_size header field; or
- the already allocated DTB page region.

The DTB grows by 80 bytes, but the stock DTB page padding has enough zero slack
to absorb that growth without moving vendor_ramdisk_table, bootconfig, or any
tail/footer bytes.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import struct
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_direct_p3_boot import (
    DEFAULT_ODIN,
    display_path,
    lz4_frame_store,
    lz4_frame_store_decode,
    md5_file,
    repo_root,
    resolve,
    sha256_file,
    tar_members,
)
from build_s22plus_ramoops_vendor_boot_enable import (
    EXPECTED_VENDOR_BOOT_SHA256,
    TARGET_NODE,
    DEFAULT_VENDOR_BOOT,
    patch_concatenated_dtb,
)
from build_s22plus_ramoops_dtbo_enable import parse_fdt_props, iter_fdt_blobs


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1")
VENDOR_BOOT_MAGIC = b"VNDRBOOT"
VENDOR_BOOT_HEADER_VERSION = 4
VENDOR_BOOT_HEADER_V4_SIZE = 2128
DTB_SIZE_FIELD_OFFSET = 0x834


@dataclass(frozen=True)
class VendorBootLayout:
    header_version: int
    page_size: int
    vendor_ramdisk_size: int
    header_size: int
    dtb_size: int
    dtb_addr: int
    vendor_ramdisk_table_size: int
    vendor_ramdisk_table_entry_num: int
    vendor_ramdisk_table_entry_size: int
    bootconfig_size: int
    vendor_ramdisk_offset: int
    dtb_offset: int
    vendor_ramdisk_table_offset: int
    bootconfig_offset: int
    used_end: int
    dtb_allocated_size: int
    dtb_padding_size: int


def align(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def parse_vendor_boot_v4(image: bytes) -> VendorBootLayout:
    if len(image) < VENDOR_BOOT_HEADER_V4_SIZE:
        raise ValueError("vendor_boot image too small for v4 header")
    if image[: len(VENDOR_BOOT_MAGIC)] != VENDOR_BOOT_MAGIC:
        raise ValueError("vendor_boot magic mismatch")

    header_version, page_size, _kernel_addr, _ramdisk_addr, vendor_ramdisk_size = struct.unpack_from("<5I", image, 8)
    if header_version != VENDOR_BOOT_HEADER_VERSION:
        raise ValueError(f"expected vendor_boot header version 4, got {header_version}")
    if page_size == 0 or page_size & (page_size - 1):
        raise ValueError(f"unexpected page size {page_size}")

    header_size = struct.unpack_from("<I", image, 0x830)[0]
    dtb_size = struct.unpack_from("<I", image, DTB_SIZE_FIELD_OFFSET)[0]
    dtb_addr = struct.unpack_from("<Q", image, 0x838)[0]
    vendor_ramdisk_table_size, entry_num, entry_size, bootconfig_size = struct.unpack_from("<4I", image, 0x840)
    if header_size != VENDOR_BOOT_HEADER_V4_SIZE:
        raise ValueError(f"unexpected vendor_boot header size {header_size}")

    vendor_ramdisk_offset = align(header_size, page_size)
    dtb_offset = vendor_ramdisk_offset + align(vendor_ramdisk_size, page_size)
    dtb_allocated_size = align(dtb_size, page_size)
    vendor_ramdisk_table_offset = dtb_offset + dtb_allocated_size
    bootconfig_offset = vendor_ramdisk_table_offset + align(vendor_ramdisk_table_size, page_size)
    used_end = bootconfig_offset + align(bootconfig_size, page_size)
    if used_end > len(image):
        raise ValueError(f"parsed vendor_boot layout exceeds image: used_end={used_end} size={len(image)}")

    return VendorBootLayout(
        header_version=header_version,
        page_size=page_size,
        vendor_ramdisk_size=vendor_ramdisk_size,
        header_size=header_size,
        dtb_size=dtb_size,
        dtb_addr=dtb_addr,
        vendor_ramdisk_table_size=vendor_ramdisk_table_size,
        vendor_ramdisk_table_entry_num=entry_num,
        vendor_ramdisk_table_entry_size=entry_size,
        bootconfig_size=bootconfig_size,
        vendor_ramdisk_offset=vendor_ramdisk_offset,
        dtb_offset=dtb_offset,
        vendor_ramdisk_table_offset=vendor_ramdisk_table_offset,
        bootconfig_offset=bootconfig_offset,
        used_end=used_end,
        dtb_allocated_size=dtb_allocated_size,
        dtb_padding_size=dtb_allocated_size - dtb_size,
    )


def changed_ranges(left: bytes, right: bytes) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    prev: int | None = None
    max_len = max(len(left), len(right))
    for index in range(max_len):
        a = left[index] if index < len(left) else None
        b = right[index] if index < len(right) else None
        if a == b:
            continue
        if start is None:
            start = prev = index
        elif prev is not None and index == prev + 1:
            prev = index
        else:
            ranges.append((start, prev if prev is not None else start))
            start = prev = index
    if start is not None:
        ranges.append((start, prev if prev is not None else start))
    return ranges


def count_changed_bytes(ranges: list[tuple[int, int]]) -> int:
    return sum(end - start + 1 for start, end in ranges)


def in_range(index: int, span: tuple[int, int]) -> bool:
    return span[0] <= index < span[1]


def count_changes_outside_allowed(ranges: list[tuple[int, int]], allowed_spans: list[tuple[int, int]]) -> int:
    outside = 0
    for start, end in ranges:
        for index in range(start, end + 1):
            if not any(in_range(index, span) for span in allowed_spans):
                outside += 1
    return outside


def summarize_ranges(ranges: list[tuple[int, int]], limit: int = 20) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    selected = ranges[:limit]
    if len(ranges) > limit:
        selected = ranges[: limit // 2] + ranges[-(limit // 2) :]
    for start, end in selected:
        summary.append({"start_hex": f"0x{start:x}", "end_hex": f"0x{end:x}", "length": end - start + 1})
    return summary


def status_values(dtb: bytes) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for blob in iter_fdt_blobs(dtb):
        for prop in parse_fdt_props(blob):
            if prop.path == TARGET_NODE and prop.name == "status":
                values.append(
                    {
                        "blob_index": blob.index,
                        "length": prop.length,
                        "value": prop.value.rstrip(b"\0").decode("ascii", errors="replace"),
                        "value_hex": prop.value.hex(),
                    }
                )
    return values


def patch_vendor_boot_direct(image: bytes) -> tuple[bytes, dict[str, Any]]:
    layout = parse_vendor_boot_v4(image)
    dtb_start = layout.dtb_offset
    dtb_end = dtb_start + layout.dtb_size
    dtb_alloc_end = dtb_start + layout.dtb_allocated_size
    source_dtb = image[dtb_start:dtb_end]
    old_padding = image[dtb_end:dtb_alloc_end]
    if any(old_padding):
        raise ValueError("stock DTB page padding is not all zero")

    before_status = status_values(source_dtb)
    patched_dtb, dtb_patch = patch_concatenated_dtb(source_dtb)
    if len(patched_dtb) > layout.dtb_allocated_size:
        raise ValueError(
            f"patched DTB size {len(patched_dtb)} exceeds allocated DTB page size {layout.dtb_allocated_size}"
        )

    patched = bytearray(image)
    struct.pack_into("<I", patched, DTB_SIZE_FIELD_OFFSET, len(patched_dtb))
    patched[dtb_start : dtb_start + len(patched_dtb)] = patched_dtb
    patched[dtb_start + len(patched_dtb) : dtb_alloc_end] = b"\0" * (dtb_alloc_end - (dtb_start + len(patched_dtb)))
    patched_bytes = bytes(patched)

    new_layout = parse_vendor_boot_v4(patched_bytes)
    if new_layout.vendor_ramdisk_table_offset != layout.vendor_ramdisk_table_offset:
        raise ValueError("vendor_ramdisk_table offset moved after direct patch")
    if new_layout.bootconfig_offset != layout.bootconfig_offset:
        raise ValueError("bootconfig offset moved after direct patch")
    if len(patched_bytes) != len(image):
        raise ValueError("direct patch changed vendor_boot image size")

    ranges = changed_ranges(image, patched_bytes)
    allowed_spans = [(DTB_SIZE_FIELD_OFFSET, DTB_SIZE_FIELD_OFFSET + 4), (dtb_start, dtb_alloc_end)]
    outside = count_changes_outside_allowed(ranges, allowed_spans)
    if outside:
        raise ValueError(f"direct patch changed {outside} bytes outside allowed spans")

    patched_status = status_values(patched_bytes[dtb_start : dtb_start + new_layout.dtb_size])
    return patched_bytes, {
        "layout_before": layout.__dict__,
        "layout_after": new_layout.__dict__,
        "dtb_offset_hex": f"0x{dtb_start:x}",
        "dtb_alloc_end_hex": f"0x{dtb_alloc_end:x}",
        "dtb_padding_zero": True,
        "before_status_values": before_status,
        "patched_status_values": patched_status,
        "dtb_patch": dtb_patch,
        "allowed_change_spans": [
            {"name": "vendor_boot_header_dtb_size", "start_hex": f"0x{DTB_SIZE_FIELD_OFFSET:x}", "end_hex": f"0x{DTB_SIZE_FIELD_OFFSET + 4:x}"},
            {"name": "vendor_boot_dtb_allocated_region", "start_hex": f"0x{dtb_start:x}", "end_hex": f"0x{dtb_alloc_end:x}"},
        ],
        "changed_range_count": len(ranges),
        "changed_byte_count": count_changed_bytes(ranges),
        "changed_outside_allowed_count": outside,
        "changed_ranges_sample": summarize_ranges(ranges),
    }


def write_lz4_store(raw: Path, out_lz4: Path) -> None:
    data = raw.read_bytes()
    frame = lz4_frame_store(data)
    if lz4_frame_store_decode(frame) != data:
        raise SystemExit(f"LZ4 roundtrip failed for {raw}")
    out_lz4.write_bytes(frame)


def write_single_member_tar_md5(member: Path, member_name: str, ap_tar: Path, ap_md5: Path) -> None:
    payload = member.read_bytes()
    with tarfile.open(ap_tar, "w") as tar:
        info = tarfile.TarInfo(member_name)
        info.size = len(payload)
        info.mode = 0o644
        info.mtime = 0
        tar.addfile(info, fileobj=io.BytesIO(payload))
    trailer = f"{md5_file(ap_tar)}  AP.tar\n".encode("ascii")
    ap_md5.write_bytes(ap_tar.read_bytes() + trailer)


def run_odin_parse_gate(odin: Path, ap_md5: Path) -> str:
    if not odin.exists():
        return "odin4_missing_parse_gate_skipped"
    result = subprocess.run(
        [str(odin), "-a", str(ap_md5), "-d", "/dev/bus/usb/999/999"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return (result.stdout + result.stderr).decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--vendor-boot", type=Path, default=DEFAULT_VENDOR_BOOT)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    vendor_boot = resolve(root, args.vendor_boot)
    odin = resolve(root, args.odin)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    candidate_odin_dir = out_dir / "candidate_odin4"
    rollback_odin_dir = out_dir / "stock_rollback_odin4"
    for directory in (build_dir, candidate_odin_dir, rollback_odin_dir):
        directory.mkdir(parents=True)

    stock_sha = sha256_file(vendor_boot)
    if stock_sha != EXPECTED_VENDOR_BOOT_SHA256:
        raise SystemExit(f"stock vendor_boot SHA mismatch: {stock_sha}")

    stock_bytes = vendor_boot.read_bytes()
    patched_bytes, patch_info = patch_vendor_boot_direct(stock_bytes)
    patched_vendor_boot = build_dir / "vendor_boot.ramoops_status_okay.direct.img"
    patched_vendor_boot.write_bytes(patched_bytes)
    source_dtb = stock_bytes[
        patch_info["layout_before"]["dtb_offset"] : patch_info["layout_before"]["dtb_offset"]
        + patch_info["layout_before"]["dtb_size"]
    ]
    patched_dtb = patched_bytes[
        patch_info["layout_after"]["dtb_offset"] : patch_info["layout_after"]["dtb_offset"]
        + patch_info["layout_after"]["dtb_size"]
    ]
    source_dtb_path = build_dir / "dtb.source"
    patched_dtb_path = build_dir / "dtb.ramoops_status_okay.direct"
    source_dtb_path.write_bytes(source_dtb)
    patched_dtb_path.write_bytes(patched_dtb)

    candidate_lz4 = candidate_odin_dir / "vendor_boot.img.lz4"
    rollback_lz4 = rollback_odin_dir / "vendor_boot.img.lz4"
    write_lz4_store(patched_vendor_boot, candidate_lz4)
    write_lz4_store(vendor_boot, rollback_lz4)
    candidate_ap_tar = candidate_odin_dir / "AP.tar"
    candidate_ap_md5 = candidate_odin_dir / "AP.tar.md5"
    rollback_ap_tar = rollback_odin_dir / "AP.tar"
    rollback_ap_md5 = rollback_odin_dir / "AP.tar.md5"
    write_single_member_tar_md5(candidate_lz4, "vendor_boot.img.lz4", candidate_ap_tar, candidate_ap_md5)
    write_single_member_tar_md5(rollback_lz4, "vendor_boot.img.lz4", rollback_ap_tar, rollback_ap_md5)
    candidate_members = tar_members(candidate_ap_md5)
    rollback_members = tar_members(rollback_ap_md5)
    if candidate_members != ["vendor_boot.img.lz4"] or rollback_members != ["vendor_boot.img.lz4"]:
        raise SystemExit(f"AP tar member mismatch: candidate={candidate_members} rollback={rollback_members}")

    candidate_parse_gate = ""
    rollback_parse_gate = ""
    if not args.no_odin_parse_gate:
        candidate_parse_gate = run_odin_parse_gate(odin, candidate_ap_md5)
        rollback_parse_gate = run_odin_parse_gate(odin, rollback_ap_md5)
        (candidate_odin_dir / "parse_dry_run_invalid_device.txt").write_text(candidate_parse_gate, encoding="utf-8")
        (rollback_odin_dir / "parse_dry_run_invalid_device.txt").write_text(rollback_parse_gate, encoding="utf-8")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "host-only byte-preserving vendor_boot direct DTB patch to enable ramoops status=okay",
        "safety": {
            "host_only": True,
            "touches_connected_device": False,
            "live_flash_authorized": False,
            "partition_scope_if_later_authorized": "vendor_boot only",
            "requires_new_sha_pinned_vendor_boot_exception_before_flash": True,
            "current_agents_does_not_authorize_this_live_flash": True,
            "forbidden_partitions_touched": False,
            "rollback_ap_built": True,
            "stock_vendor_boot_available": True,
            "magiskboot_repack_used": False,
            "byte_preserving_layout": True,
            "vendor_ramdisk_table_offset_unchanged": True,
            "bootconfig_offset_unchanged": True,
            "tail_footer_bytes_unchanged": True,
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "stock_vendor_boot": display_path(root, vendor_boot),
            "patched_vendor_boot": display_path(root, patched_vendor_boot),
            "source_dtb": display_path(root, source_dtb_path),
            "patched_dtb": display_path(root, patched_dtb_path),
            "candidate_ap_tar_md5": display_path(root, candidate_ap_md5),
            "rollback_ap_tar_md5": display_path(root, rollback_ap_md5),
        },
        "hashes": {
            "stock_vendor_boot": stock_sha,
            "source_dtb": sha256_file(source_dtb_path),
            "patched_dtb": sha256_file(patched_dtb_path),
            "patched_vendor_boot": sha256_file(patched_vendor_boot),
            "candidate_vendor_boot_lz4": sha256_file(candidate_lz4),
            "candidate_ap_tar": sha256_file(candidate_ap_tar),
            "candidate_ap_tar_md5": sha256_file(candidate_ap_md5),
            "rollback_vendor_boot_lz4": sha256_file(rollback_lz4),
            "rollback_ap_tar": sha256_file(rollback_ap_tar),
            "rollback_ap_tar_md5": sha256_file(rollback_ap_md5),
        },
        "sizes": {
            "stock_vendor_boot": vendor_boot.stat().st_size,
            "patched_vendor_boot": patched_vendor_boot.stat().st_size,
            "source_dtb": source_dtb_path.stat().st_size,
            "patched_dtb": patched_dtb_path.stat().st_size,
            "dtb_size_delta": patched_dtb_path.stat().st_size - source_dtb_path.stat().st_size,
            "candidate_vendor_boot_lz4": candidate_lz4.stat().st_size,
            "candidate_ap_tar_md5": candidate_ap_md5.stat().st_size,
            "rollback_vendor_boot_lz4": rollback_lz4.stat().st_size,
            "rollback_ap_tar_md5": rollback_ap_md5.stat().st_size,
        },
        "evidence": {
            "direct_patch": patch_info,
            "candidate_tar_members": candidate_members,
            "rollback_tar_members": rollback_members,
            "odin_parse_gate_candidate": candidate_parse_gate,
            "odin_parse_gate_rollback": rollback_parse_gate,
        },
    }
    if manifest["sizes"]["stock_vendor_boot"] != manifest["sizes"]["patched_vendor_boot"]:
        raise SystemExit("patched vendor_boot size drifted")
    if manifest["evidence"]["direct_patch"]["changed_outside_allowed_count"] != 0:
        raise SystemExit("direct patch changed bytes outside allowed spans")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
