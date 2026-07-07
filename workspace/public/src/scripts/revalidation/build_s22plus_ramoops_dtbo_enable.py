#!/usr/bin/env python3
"""Build a host-only S22+ DTBO candidate that enables ramoops.

This script does not flash, reboot, or touch a connected device. It parses the
stock FYG8 dtbo.img as concatenated FDT blobs, finds the Samsung overlay that
targets the vendor DTB symbol `ramoops_mem`, and changes only that overlay's
`status = "disabled"` value to an equal-length `"okay"` value.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import struct
import subprocess
import tarfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_ramoops_dtbo_enable_v0_1")
DEFAULT_DTBO = Path("workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/dtbo.img")
DEFAULT_VENDOR_DTB = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/unpack-vendor-boot/dtb"
)
EXPECTED_DTBO_SHA256 = "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"
FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9
DISABLED_VALUE = b"disabled\0"
OKAY_SAME_LEN_VALUE = b"okay\0" + b"\0" * (len(DISABLED_VALUE) - len(b"okay\0"))
TARGET_FIXUP = "/fragment@116:target:0"
TARGET_STATUS_PATH = "/fragment@116/__overlay__"
EXPECTED_PATCH_COUNT = 2
DTBO_AVB_HASH_IMAGE_SIZE = 7_777_749
DTBO_AVB_SALT_HEX = "cd2e0e500c8eba1677c63ef2336da873c0d18d0c4cfc7f7166828b1e73086a2b"
DTBO_AVB_DESCRIPTOR_DIGEST_HEX = "fc4274765cb8e785d1d88c974a5a6ef7119961a66fac452c305ba0dc2fbd3ed1"


@dataclass(frozen=True)
class FdtBlob:
    index: int
    offset: int
    totalsize: int
    data: bytes


@dataclass(frozen=True)
class FdtProp:
    blob_index: int
    blob_offset: int
    path: str
    name: str
    length: int
    value_offset: int
    value: bytes


@dataclass(frozen=True)
class PatchTarget:
    blob_index: int
    blob_offset: int
    value_offset: int
    old_value: bytes


def align4(value: int) -> int:
    return (value + 3) & ~3


def iter_fdt_blobs(image: bytes) -> list[FdtBlob]:
    blobs: list[FdtBlob] = []
    magic = struct.pack(">I", FDT_MAGIC)
    offset = 0
    while True:
        found = image.find(magic, offset)
        if found < 0:
            break
        if found + 8 <= len(image):
            totalsize = struct.unpack_from(">I", image, found + 4)[0]
            if 0 < totalsize <= len(image) - found:
                blobs.append(FdtBlob(len(blobs), found, totalsize, image[found : found + totalsize]))
        offset = found + 4
    return blobs


def read_c_string(data: bytes, offset: int) -> tuple[str, int]:
    end = data.find(b"\0", offset)
    if end < 0:
        raise ValueError("unterminated FDT node name")
    return data[offset:end].decode("ascii", errors="strict"), align4(end + 1)


def read_string_table(data: bytes, offset: int) -> str:
    end = data.find(b"\0", offset)
    if end < 0:
        raise ValueError("unterminated FDT string-table entry")
    return data[offset:end].decode("ascii", errors="strict")


def node_path(stack: list[str]) -> str:
    if not stack:
        return "/"
    return "/" + "/".join(stack)


def parse_fdt_props(blob: FdtBlob) -> list[FdtProp]:
    data = blob.data
    if len(data) < 40:
        raise ValueError(f"FDT blob {blob.index} too small")
    header = struct.unpack_from(">10I", data, 0)
    magic, totalsize, off_struct, off_strings, _off_mem, _version, _last_comp, _boot_cpuid, size_strings, size_struct = header
    if magic != FDT_MAGIC:
        raise ValueError(f"FDT blob {blob.index} bad magic")
    if totalsize != blob.totalsize:
        raise ValueError(f"FDT blob {blob.index} totalsize drift")
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    if struct_end > len(data) or strings_end > len(data):
        raise ValueError(f"FDT blob {blob.index} section outside totalsize")

    props: list[FdtProp] = []
    stack: list[str] = []
    pos = off_struct
    while pos + 4 <= struct_end:
        token = struct.unpack_from(">I", data, pos)[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, pos = read_c_string(data, pos)
            if name:
                stack.append(name)
        elif token == FDT_END_NODE:
            if stack:
                stack.pop()
        elif token == FDT_PROP:
            if pos + 8 > struct_end:
                raise ValueError(f"FDT blob {blob.index} truncated property header")
            length, nameoff = struct.unpack_from(">II", data, pos)
            pos += 8
            name = read_string_table(data, off_strings + nameoff)
            value_offset = blob.offset + pos
            value = data[pos : pos + length]
            props.append(
                FdtProp(
                    blob_index=blob.index,
                    blob_offset=blob.offset,
                    path=node_path(stack),
                    name=name,
                    length=length,
                    value_offset=value_offset,
                    value=value,
                )
            )
            pos = align4(pos + length)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
        else:
            raise ValueError(f"FDT blob {blob.index} unknown token {token} at 0x{pos - 4:x}")
    return props


def decode_string_list(value: bytes) -> list[str]:
    return [part.decode("ascii", errors="strict") for part in value.split(b"\0") if part]


def summarize_dtbo(image: bytes) -> dict[str, object]:
    blobs = iter_fdt_blobs(image)
    blob_summaries: list[dict[str, object]] = []
    targets: list[PatchTarget] = []
    for blob in blobs:
        props = parse_fdt_props(blob)
        fixup_values = [
            decode_string_list(prop.value)
            for prop in props
            if prop.path == "/__fixups__" and prop.name == "ramoops_mem"
        ]
        has_target_fixup = any(TARGET_FIXUP in value for values in fixup_values for value in values)
        status_props = [
            prop
            for prop in props
            if prop.path == TARGET_STATUS_PATH and prop.name == "status" and prop.value == DISABLED_VALUE
        ]
        if has_target_fixup:
            for prop in status_props:
                if prop.length != len(DISABLED_VALUE):
                    raise SystemExit(
                        f"candidate status length drift in blob {blob.index}: {prop.length} != {len(DISABLED_VALUE)}"
                    )
                targets.append(PatchTarget(blob.index, blob.offset, prop.value_offset, prop.value))
        blob_summaries.append(
            {
                "index": blob.index,
                "offset_hex": f"0x{blob.offset:x}",
                "totalsize": blob.totalsize,
                "has_ramoops_mem_fixup_to_fragment116": has_target_fixup,
                "fragment116_disabled_status_count": len(status_props),
            }
        )
    return {
        "blob_count": len(blobs),
        "blobs": blob_summaries,
        "patch_targets": [
            {
                "blob_index": target.blob_index,
                "blob_offset_hex": f"0x{target.blob_offset:x}",
                "value_offset_hex": f"0x{target.value_offset:x}",
                "old_value_hex": target.old_value.hex(),
                "new_value_hex": OKAY_SAME_LEN_VALUE.hex(),
            }
            for target in targets
        ],
    }


def summarize_vendor_boot_dtb(image: bytes) -> dict[str, object]:
    blobs = iter_fdt_blobs(image)
    status_values: list[dict[str, object]] = []
    for blob in blobs:
        for prop in parse_fdt_props(blob):
            if prop.path == "/reserved-memory/ramoops_region" and prop.name == "status":
                status_values.append(
                    {
                        "blob_index": blob.index,
                        "value_offset_hex": f"0x{prop.value_offset:x}",
                        "length": prop.length,
                        "value_hex": prop.value.hex(),
                        "strings": decode_string_list(prop.value),
                    }
                )
    return {
        "blob_count": len(blobs),
        "ramoops_status_property_count": len(status_values),
        "ramoops_status_values": status_values,
    }


def patch_dtbo(image: bytes, summary: dict[str, object]) -> tuple[bytes, list[dict[str, object]]]:
    patch_targets = summary["patch_targets"]
    if not isinstance(patch_targets, list):
        raise SystemExit("internal summary shape error")
    if len(patch_targets) != EXPECTED_PATCH_COUNT:
        raise SystemExit(f"expected {EXPECTED_PATCH_COUNT} patch targets, found {len(patch_targets)}")

    patched = bytearray(image)
    applied: list[dict[str, object]] = []
    for target in patch_targets:
        offset = int(str(target["value_offset_hex"]), 16)
        old = bytes.fromhex(str(target["old_value_hex"]))
        if bytes(patched[offset : offset + len(old)]) != old:
            raise SystemExit(f"target bytes drift at 0x{offset:x}")
        patched[offset : offset + len(old)] = OKAY_SAME_LEN_VALUE
        applied.append(
            {
                "blob_index": target["blob_index"],
                "value_offset_hex": target["value_offset_hex"],
                "old_value_hex": old.hex(),
                "new_value_hex": OKAY_SAME_LEN_VALUE.hex(),
            }
        )
    return bytes(patched), applied


def changed_byte_count(before: bytes, after: bytes) -> int:
    if len(before) != len(after):
        raise ValueError("length mismatch")
    return sum(1 for left, right in zip(before, after) if left != right)


def dtbo_avb_digest(image: bytes) -> str:
    if len(image) < DTBO_AVB_HASH_IMAGE_SIZE:
        raise ValueError("DTBO image smaller than AVB hash descriptor image size")
    salt = bytes.fromhex(DTBO_AVB_SALT_HEX)
    return hashlib.sha256(salt + image[:DTBO_AVB_HASH_IMAGE_SIZE]).hexdigest()


def diff_ranges(before: bytes, after: bytes) -> list[dict[str, object]]:
    if len(before) != len(after):
        raise ValueError("length mismatch")
    ranges: list[dict[str, object]] = []
    start: int | None = None
    for idx, (left, right) in enumerate(zip(before, after)):
        if left != right and start is None:
            start = idx
        elif left == right and start is not None:
            ranges.append(
                {
                    "start_hex": f"0x{start:x}",
                    "end_hex": f"0x{idx:x}",
                    "length": idx - start,
                    "before_hex": before[start:idx].hex(),
                    "after_hex": after[start:idx].hex(),
                }
            )
            start = None
    if start is not None:
        ranges.append(
            {
                "start_hex": f"0x{start:x}",
                "end_hex": f"0x{len(before):x}",
                "length": len(before) - start,
                "before_hex": before[start:].hex(),
                "after_hex": after[start:].hex(),
            }
        )
    return ranges


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
    parser.add_argument("--dtbo", type=Path, default=DEFAULT_DTBO)
    parser.add_argument("--vendor-dtb", type=Path, default=DEFAULT_VENDOR_DTB)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    dtbo = resolve(root, args.dtbo)
    vendor_dtb = resolve(root, args.vendor_dtb)
    odin = resolve(root, args.odin)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    candidate_odin_dir = out_dir / "candidate_odin4"
    rollback_odin_dir = out_dir / "stock_rollback_odin4"
    build_dir.mkdir(parents=True)
    candidate_odin_dir.mkdir(parents=True)
    rollback_odin_dir.mkdir(parents=True)

    stock_dtbo_sha = sha256_file(dtbo)
    if stock_dtbo_sha != EXPECTED_DTBO_SHA256:
        raise SystemExit(f"stock dtbo SHA mismatch: {stock_dtbo_sha}")

    stock_image = dtbo.read_bytes()
    stock_summary = summarize_dtbo(stock_image)
    vendor_dtb_summary = summarize_vendor_boot_dtb(vendor_dtb.read_bytes())
    if vendor_dtb_summary["ramoops_status_property_count"] != 0:
        raise SystemExit("vendor_boot DTB unexpectedly contains a ramoops status property")

    patched_image, applied = patch_dtbo(stock_image, stock_summary)
    patched_summary = summarize_dtbo(patched_image)
    remaining_targets = patched_summary["patch_targets"]
    if isinstance(remaining_targets, list) and remaining_targets:
        raise SystemExit(f"patched image still has target disabled overlays: {remaining_targets}")

    diff = diff_ranges(stock_image, patched_image)
    if len(diff) != EXPECTED_PATCH_COUNT:
        raise SystemExit(f"expected {EXPECTED_PATCH_COUNT} diff ranges, found {len(diff)}")
    changed = changed_byte_count(stock_image, patched_image)
    expected_changed = EXPECTED_PATCH_COUNT * sum(1 for left, right in zip(DISABLED_VALUE, OKAY_SAME_LEN_VALUE) if left != right)
    if changed != expected_changed:
        raise SystemExit(f"unexpected changed-byte count: {changed} != {expected_changed}")

    stock_avb_digest = dtbo_avb_digest(stock_image)
    patched_avb_digest = dtbo_avb_digest(patched_image)
    if stock_avb_digest != DTBO_AVB_DESCRIPTOR_DIGEST_HEX:
        raise SystemExit(f"stock DTBO AVB descriptor digest mismatch: {stock_avb_digest}")

    stock_raw = build_dir / "stock_dtbo.img"
    patched_raw = build_dir / "dtbo.img"
    stock_raw.write_bytes(stock_image)
    patched_raw.write_bytes(patched_image)

    candidate_lz4 = candidate_odin_dir / "dtbo.img.lz4"
    rollback_lz4 = rollback_odin_dir / "dtbo.img.lz4"
    write_lz4_store(patched_raw, candidate_lz4)
    write_lz4_store(stock_raw, rollback_lz4)

    candidate_ap_tar = candidate_odin_dir / "AP.tar"
    candidate_ap_md5 = candidate_odin_dir / "AP.tar.md5"
    rollback_ap_tar = rollback_odin_dir / "AP.tar"
    rollback_ap_md5 = rollback_odin_dir / "AP.tar.md5"
    write_single_member_tar_md5(candidate_lz4, "dtbo.img.lz4", candidate_ap_tar, candidate_ap_md5)
    write_single_member_tar_md5(rollback_lz4, "dtbo.img.lz4", rollback_ap_tar, rollback_ap_md5)

    candidate_members = tar_members(candidate_ap_md5)
    rollback_members = tar_members(rollback_ap_md5)
    if candidate_members != ["dtbo.img.lz4"] or rollback_members != ["dtbo.img.lz4"]:
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
        "purpose": "host-only DTBO candidate to enable ramoops by overriding the ramoops_mem overlay status",
        "safety": {
            "host_only": True,
            "touches_connected_device": False,
            "live_flash_authorized": False,
            "partition_scope_if_later_authorized": "dtbo only",
            "requires_new_sha_pinned_dtbo_exception_before_flash": True,
            "current_agents_boot_only_rule_does_not_authorize_this_live_flash": True,
            "forbidden_partitions_touched": False,
            "rollback_ap_built": True,
            "stock_dtbo_avb_descriptor_matches": True,
            "patched_dtbo_avb_descriptor_matches": False,
            "patched_dtbo_requires_disabled_vbmeta_or_resigning_before_live": True,
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "stock_dtbo": display_path(root, dtbo),
            "vendor_boot_dtb_checked": display_path(root, vendor_dtb),
            "candidate_ap_tar_md5": display_path(root, candidate_ap_md5),
            "rollback_ap_tar_md5": display_path(root, rollback_ap_md5),
        },
        "hashes": {
            "stock_dtbo_raw": stock_dtbo_sha,
            "patched_dtbo_raw": sha256_file(patched_raw),
            "candidate_dtbo_lz4": sha256_file(candidate_lz4),
            "candidate_ap_tar": sha256_file(candidate_ap_tar),
            "candidate_ap_tar_md5": sha256_file(candidate_ap_md5),
            "rollback_dtbo_lz4": sha256_file(rollback_lz4),
            "rollback_ap_tar": sha256_file(rollback_ap_tar),
            "rollback_ap_tar_md5": sha256_file(rollback_ap_md5),
            "vendor_boot_dtb_checked": sha256_file(vendor_dtb),
            "stock_dtbo_avb_hash_descriptor_digest": stock_avb_digest,
            "patched_dtbo_avb_hash_descriptor_recomputed_digest": patched_avb_digest,
        },
        "sizes": {
            "dtbo_raw": len(stock_image),
            "patched_dtbo_raw": len(patched_image),
            "candidate_dtbo_lz4": candidate_lz4.stat().st_size,
            "candidate_ap_tar_md5": candidate_ap_md5.stat().st_size,
            "rollback_dtbo_lz4": rollback_lz4.stat().st_size,
            "rollback_ap_tar_md5": rollback_ap_md5.stat().st_size,
        },
        "evidence": {
            "vendor_boot_dtb": vendor_dtb_summary,
            "stock_dtbo": stock_summary,
            "patched_dtbo": patched_summary,
            "applied_patches": applied,
            "diff_ranges": diff,
            "changed_byte_count": changed,
            "dtbo_avb_hash_descriptor": {
                "partition_name": "dtbo",
                "hash_algorithm": "sha256",
                "image_size": DTBO_AVB_HASH_IMAGE_SIZE,
                "salt_hex": DTBO_AVB_SALT_HEX,
                "descriptor_digest_hex": DTBO_AVB_DESCRIPTOR_DIGEST_HEX,
                "stock_recomputed_digest_hex": stock_avb_digest,
                "stock_matches_descriptor": True,
                "patched_recomputed_digest_hex": patched_avb_digest,
                "patched_matches_descriptor": patched_avb_digest == DTBO_AVB_DESCRIPTOR_DIGEST_HEX,
            },
            "candidate_tar_members": candidate_members,
            "rollback_tar_members": rollback_members,
            "odin_parse_gate_candidate": candidate_parse_gate,
            "odin_parse_gate_rollback": rollback_parse_gate,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
