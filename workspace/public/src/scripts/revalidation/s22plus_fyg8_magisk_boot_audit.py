#!/usr/bin/env python3
"""Audit the pinned FYG8 stock and known-booting Magisk boot images.

Host-only and read-only with respect to all input images. The only output is a
JSON report. This tool deliberately does not repack a boot image or contact a
device.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import lzma
import stat
import struct
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_magisk_boot_audit_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
PAGE_SIZE = 4096
ANDROID_MAGIC = b"ANDROID!"
CPIO_NEWC_MAGIC = {b"070701", b"070702"}
IKCONFIG_START = b"IKCFG_ST"
IKCONFIG_END = b"IKCFG_ED"

DEFAULT_STOCK_BOOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/boot.img"
)
DEFAULT_MAGISK_BOOT = Path("workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img")
DEFAULT_MAGISK_APK = Path("workspace/private/inputs/magisk/v30.7/Magisk-v30.7.apk")
DEFAULT_LZ4 = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)
DEFAULT_AVBTOOL = Path(
    "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/avbtool"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_magisk_boot_analysis_r0/audit.json"
)

EXPECTED_STOCK_BOOT_SHA256 = "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae"
EXPECTED_MAGISK_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_MAGISK_APK_SHA256 = "e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5"
EXPECTED_LZ4_SHA256 = "91975bf197d485b81475dfa6267aa2284550b844e8e8d64a4e7e35d9a1fa9fb8"
EXPECTED_AVBTOOL_SHA256 = "063d7c7a19744ceeb72553c95962ac98fff977fc27f5f95e6063c2f15f8d3e88"
EXPECTED_STOCK_KERNEL_SHA256 = "027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d"
EXPECTED_MAGISK_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_STOCK_INIT_SHA256 = "5bc266151967c4da67e0253b4f0917150b1ccb799e199858fb436f322f10a428"
EXPECTED_MAGISK_INIT_SHA256 = "383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468"

DEFEX_BEFORE = bytes.fromhex("821B8012")
DEFEX_AFTER = bytes.fromhex("E2FF8F12")
PROCA_BEFORE = b"proca_config\0"
PROCA_AFTER = b"proca_magisk\0"
RKP_BEFORE = bytes.fromhex(
    "49010054011440B93FA00F71E9000054010840B93FA00F7189000054001840B91FA00F7188010054"
)
RKP_AFTER = bytes.fromhex(
    "A1020054011440B93FA00F7140020054010840B93FA00F71E0010054001840B91FA00F7181010054"
)
LEGACY_SAR_BEFORE = b"skip_initramfs\0"
LEGACY_SAR_AFTER = b"want_initramfs\0"
EXPECTED_MAGISK_ONLY_ENTRIES = [
    ".backup",
    ".backup/.magisk",
    ".backup/.rmlist",
    ".backup/init.xz",
    "overlay.d",
    "overlay.d/sbin",
    "overlay.d/sbin/init-ld.xz",
    "overlay.d/sbin/magisk.xz",
    "overlay.d/sbin/stub.xz",
]


class AuditError(ValueError):
    pass


@dataclass(frozen=True)
class CpioEntry:
    name: str
    mode: int
    uid: int
    gid: int
    mtime: int
    data: bytes

    def summary(self) -> dict[str, Any]:
        return {
            "mode": f"{stat.S_IMODE(self.mode):04o}",
            "type": file_type(self.mode),
            "uid": self.uid,
            "gid": self.gid,
            "mtime": self.mtime,
            "size": len(self.data),
            "sha256": sha256_bytes(self.data),
        }


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise AuditError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def align(value: int, alignment: int = PAGE_SIZE) -> int:
    return (value + alignment - 1) // alignment * alignment


def decode_os_version(value: int) -> dict[str, Any]:
    return {
        "encoded": value,
        "os_version": f"{(value >> 25) & 0x7f}.{(value >> 18) & 0x7f}.{(value >> 11) & 0x7f}",
        "os_patch_level": f"{((value >> 4) & 0x7f) + 2000:04d}-{value & 0xf:02d}",
    }


def parse_boot_image(data: bytes) -> dict[str, Any]:
    if len(data) < 1584 or data[:8] != ANDROID_MAGIC:
        raise AuditError("not an Android boot image v3/v4")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", data, 8)
    header_version = struct.unpack_from("<I", data, 40)[0]
    if header_version not in (3, 4):
        raise AuditError(f"unsupported boot header version: {header_version}")
    if header_size < 1580 or header_size > PAGE_SIZE:
        raise AuditError(f"invalid boot header size: {header_size}")
    signature_size = struct.unpack_from("<I", data, 1580)[0] if header_version == 4 else 0
    kernel_offset = PAGE_SIZE
    ramdisk_offset = align(kernel_offset + kernel_size)
    signature_offset = align(ramdisk_offset + ramdisk_size)
    used_end = signature_offset + signature_size
    if used_end > len(data):
        raise AuditError("boot image sections exceed file size")
    cmdline = data[44:1580].split(b"\0", 1)[0].decode("ascii", errors="strict")
    return {
        "header": {
            "magic": "ANDROID!",
            "header_version": header_version,
            "header_size": header_size,
            "kernel_size": kernel_size,
            "ramdisk_size": ramdisk_size,
            "signature_size": signature_size,
            "command_line": cmdline,
            **decode_os_version(os_version),
        },
        "kernel": data[kernel_offset : kernel_offset + kernel_size],
        "ramdisk": data[ramdisk_offset : ramdisk_offset + ramdisk_size],
        "signature": data[signature_offset:used_end],
        "layout": {
            "kernel_offset": kernel_offset,
            "ramdisk_offset": ramdisk_offset,
            "signature_offset": signature_offset,
            "used_end": used_end,
            "file_size": len(data),
            "trailing_padding_bytes": len(data) - used_end,
        },
    }


def parse_avb_footer(data: bytes) -> dict[str, Any]:
    if len(data) < 64:
        raise AuditError("image is too short for an AVB footer")
    magic, major, minor, original_size, vbmeta_offset, vbmeta_size, reserved = struct.unpack(
        "!4s2I3Q28s", data[-64:]
    )
    if magic != b"AVBf":
        raise AuditError("AVB footer magic not found")
    if any(reserved):
        raise AuditError("AVB footer reserved bytes are nonzero")
    if vbmeta_offset + vbmeta_size > len(data) - 64:
        raise AuditError("AVB vbmeta range exceeds image")
    vbmeta = data[vbmeta_offset : vbmeta_offset + vbmeta_size]
    if not vbmeta.startswith(b"AVB0"):
        raise AuditError("AVB vbmeta header magic not found at footer offset")
    return {
        "version": f"{major}.{minor}",
        "original_image_size": original_size,
        "vbmeta_offset": vbmeta_offset,
        "vbmeta_size": vbmeta_size,
        "vbmeta_sha256": sha256_bytes(vbmeta),
        "vbmeta": vbmeta,
    }


def parse_newc(data: bytes) -> dict[str, CpioEntry]:
    entries: dict[str, CpioEntry] = {}
    offset = 0
    while True:
        if offset + 110 > len(data):
            raise AuditError("truncated newc header")
        header = data[offset : offset + 110]
        if header[:6] not in CPIO_NEWC_MAGIC:
            raise AuditError(f"invalid newc magic at offset {offset}")
        try:
            fields = [int(header[6 + index * 8 : 14 + index * 8], 16) for index in range(13)]
        except ValueError as exc:
            raise AuditError(f"invalid newc field at offset {offset}") from exc
        mode, uid, gid, mtime, file_size = fields[1], fields[2], fields[3], fields[5], fields[6]
        name_size = fields[11]
        if name_size < 1:
            raise AuditError("newc entry has empty encoded name")
        name_start = offset + 110
        name_end = name_start + name_size
        if name_end > len(data) or data[name_end - 1] != 0:
            raise AuditError("truncated or unterminated newc name")
        name = data[name_start : name_end - 1].decode("utf-8", errors="strict")
        content_start = align(name_end, 4)
        content_end = content_start + file_size
        if content_end > len(data):
            raise AuditError(f"truncated newc content: {name}")
        if name == "TRAILER!!!":
            return entries
        if name in entries:
            raise AuditError(f"duplicate newc entry: {name}")
        entries[name] = CpioEntry(name, mode, uid, gid, mtime, data[content_start:content_end])
        offset = align(content_end, 4)


def extract_ikconfig(data: bytes) -> bytes:
    start = data.find(IKCONFIG_START)
    end = data.find(IKCONFIG_END, start + len(IKCONFIG_START))
    if start < 0 or end < 0:
        raise AuditError("embedded IKCONFIG markers not found")
    try:
        return gzip.decompress(data[start + len(IKCONFIG_START) : end])
    except gzip.BadGzipFile as exc:
        raise AuditError("embedded IKCONFIG is invalid") from exc


def config_values(data: bytes, keys: list[str]) -> dict[str, str | None]:
    values: dict[str, str | None] = {key: None for key in keys}
    for raw in data.decode("ascii", errors="strict").splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in values:
            values[key] = value
    return values


def file_type(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def decompress_lz4(tool: Path, compressed: bytes) -> bytes:
    with tempfile.TemporaryDirectory(prefix="s22-magisk-audit-") as temp:
        source = Path(temp) / "ramdisk.lz4"
        source.write_bytes(compressed)
        result = subprocess.run(
            [str(tool), "-d", "-c", str(source)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    if result.returncode != 0:
        raise AuditError(f"lz4 decompression failed: {result.stderr.decode(errors='replace')}")
    return result.stdout


def run_avb_verify(tool: Path, image: Path) -> dict[str, Any]:
    result = subprocess.run(
        [str(tool), "verify_image", "--image", str(image)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    combined = stdout + stderr
    return {
        "returncode": result.returncode,
        "vbmeta_signature_verified": "Successfully verified footer and SHA256_RSA4096 vbmeta struct" in combined,
        "payload_hash_verified": "Successfully verified sha256 hash" in combined,
        "payload_hash_mismatch": "does not match digest in descriptor" in combined,
        "stdout": stdout,
        "stderr": stderr,
    }


def require_entry(entries: dict[str, CpioEntry], name: str) -> CpioEntry:
    try:
        return entries[name]
    except KeyError as exc:
        raise AuditError(f"required ramdisk entry missing: {name}") from exc


def diff_ranges(before: bytes, after: bytes) -> list[dict[str, Any]]:
    if len(before) != len(after):
        raise AuditError("cannot range-diff payloads of unequal length")
    ranges: list[dict[str, Any]] = []
    start: int | None = None
    for offset, (left, right) in enumerate(zip(before, after)):
        if left != right and start is None:
            start = offset
        elif left == right and start is not None:
            ranges.append(make_diff_range(before, after, start, offset))
            start = None
    if start is not None:
        ranges.append(make_diff_range(before, after, start, len(before)))
    return ranges


def make_diff_range(before: bytes, after: bytes, start: int, end: int) -> dict[str, Any]:
    return {
        "start": start,
        "end_exclusive": end,
        "length": end - start,
        "stock_hex": before[start:end].hex(),
        "magisk_hex": after[start:end].hex(),
    }


def locate_unique(data: bytes, needle: bytes) -> int | None:
    first = data.find(needle)
    if first < 0:
        return None
    if data.find(needle, first + 1) >= 0:
        raise AuditError(f"expected unique pattern appears more than once: {needle.hex()}")
    return first


def kernel_patch_audit(stock: bytes, magisk: bytes, boot_patch: bytes) -> dict[str, Any]:
    ranges = diff_ranges(stock, magisk)
    defex_offset = locate_unique(stock, DEFEX_BEFORE)
    proca_offset = locate_unique(stock, PROCA_BEFORE)
    expected = bytearray(stock)
    if defex_offset is not None:
        expected[defex_offset : defex_offset + len(DEFEX_AFTER)] = DEFEX_AFTER
    if proca_offset is not None:
        expected[proca_offset : proca_offset + len(PROCA_AFTER)] = PROCA_AFTER
    expected_ranges = diff_ranges(stock, bytes(expected))
    exact = (
        defex_offset is not None
        and proca_offset is not None
        and magisk[defex_offset : defex_offset + len(DEFEX_AFTER)] == DEFEX_AFTER
        and magisk[proca_offset : proca_offset + len(PROCA_AFTER)] == PROCA_AFTER
        and ranges == expected_ranges
    )
    script_contract = {
        "defex_hexpatch_present": (
            DEFEX_BEFORE.hex().upper().encode() in boot_patch
            and DEFEX_AFTER.hex().upper().encode() in boot_patch
        ),
        "proca_hexpatch_present": (
            PROCA_BEFORE.hex().upper().encode() in boot_patch
            and PROCA_AFTER.hex().upper().encode() in boot_patch
        ),
        "rkp_hexpatch_present": (
            RKP_BEFORE.hex().upper().encode() in boot_patch
            and RKP_AFTER.hex().upper().encode() in boot_patch
        ),
        "legacy_sar_hexpatch_present": (
            LEGACY_SAR_BEFORE.hex().upper().encode() in boot_patch
            and LEGACY_SAR_AFTER.hex().upper().encode() in boot_patch
        ),
    }
    return {
        "stock_sha256": sha256_bytes(stock),
        "magisk_sha256": sha256_bytes(magisk),
        "same_size": len(stock) == len(magisk),
        "changed_bytes": sum(item["length"] for item in ranges),
        "diff_ranges": ranges,
        "recognized_patches": {
            "defex": {"offset": defex_offset, "before": DEFEX_BEFORE.hex(), "after": DEFEX_AFTER.hex()},
            "proca": {"offset": proca_offset, "before": PROCA_BEFORE.hex(), "after": PROCA_AFTER.hex()},
            "rkp_applied": RKP_BEFORE in stock and RKP_AFTER in magisk and RKP_BEFORE not in magisk,
            "legacy_sar_applied": (
                LEGACY_SAR_BEFORE in stock
                and LEGACY_SAR_AFTER in magisk
                and LEGACY_SAR_BEFORE not in magisk
            ),
        },
        "pattern_counts": {
            "rkp_before_stock": stock.count(RKP_BEFORE),
            "rkp_after_magisk": magisk.count(RKP_AFTER),
            "legacy_sar_before_stock": stock.count(LEGACY_SAR_BEFORE),
            "legacy_sar_after_magisk": magisk.count(LEGACY_SAR_AFTER),
        },
        "boot_patch_script_contract": script_contract,
        "exactly_defex_and_proca": exact and all(script_contract.values()),
    }


def ramdisk_entry_audit(
    stock: dict[str, CpioEntry], magisk: dict[str, CpioEntry]
) -> dict[str, Any]:
    stock_names = set(stock)
    magisk_names = set(magisk)
    common = sorted(stock_names & magisk_names)
    preserved = [name for name in common if stock[name] == magisk[name]]
    changed = [name for name in common if stock[name] != magisk[name]]
    removed = sorted(stock_names - magisk_names)
    added = sorted(magisk_names - stock_names)
    exact = (
        changed == ["init"]
        and not removed
        and added == EXPECTED_MAGISK_ONLY_ENTRIES
        and len(preserved) == len(stock) - 1
    )
    return {
        "stock_entries": sorted(stock),
        "magisk_entries": sorted(magisk),
        "preserved_entries": preserved,
        "changed_entries": changed,
        "removed_entries": removed,
        "added_entries": added,
        "expected_magisk_only_entries": EXPECTED_MAGISK_ONLY_ENTRIES,
        "complete_classification": exact,
    }


def parse_properties(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in data.decode("ascii", errors="strict").splitlines():
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            raise AuditError(f"invalid Magisk config line: {raw!r}")
        key, value = raw.split("=", 1)
        result[key] = value
    return result


def apk_payloads(apk: Path) -> dict[str, bytes]:
    names = {
        "boot_patch": "assets/boot_patch.sh",
        "magiskinit": "lib/arm64-v8a/libmagiskinit.so",
        "magisk": "lib/arm64-v8a/libmagisk.so",
        "init_ld": "lib/arm64-v8a/libinit-ld.so",
        "stub": "assets/stub.apk",
    }
    with zipfile.ZipFile(apk) as archive:
        return {key: archive.read(name) for key, name in names.items()}


def audit(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    stock_path = resolve(root, args.stock_boot)
    magisk_path = resolve(root, args.magisk_boot)
    apk_path = resolve(root, args.magisk_apk)
    lz4_path = resolve(root, args.lz4)
    avbtool_path = resolve(root, args.avbtool)
    required = (stock_path, magisk_path, apk_path, lz4_path, avbtool_path)
    for path in required:
        if not path.is_file():
            raise AuditError(f"required input missing: {path}")
    pins = {
        stock_path: EXPECTED_STOCK_BOOT_SHA256,
        magisk_path: EXPECTED_MAGISK_BOOT_SHA256,
        apk_path: EXPECTED_MAGISK_APK_SHA256,
        lz4_path: EXPECTED_LZ4_SHA256,
        avbtool_path: EXPECTED_AVBTOOL_SHA256,
    }
    for path, expected in pins.items():
        actual = sha256_file(path)
        if actual != expected:
            raise AuditError(f"SHA256 mismatch for {path}: {actual}")

    stock_data = stock_path.read_bytes()
    magisk_data = magisk_path.read_bytes()
    stock = parse_boot_image(stock_data)
    magisk = parse_boot_image(magisk_data)
    stock_avb = parse_avb_footer(stock_data)
    magisk_avb = parse_avb_footer(magisk_data)
    stock_avb_verify = run_avb_verify(avbtool_path, stock_path)
    magisk_avb_verify = run_avb_verify(avbtool_path, magisk_path)
    apk = apk_payloads(apk_path)
    stock_cpio_data = decompress_lz4(lz4_path, stock["ramdisk"])
    magisk_cpio_data = decompress_lz4(lz4_path, magisk["ramdisk"])
    stock_cpio = parse_newc(stock_cpio_data)
    magisk_cpio = parse_newc(magisk_cpio_data)
    entry_audit = ramdisk_entry_audit(stock_cpio, magisk_cpio)

    stock_init = require_entry(stock_cpio, "init")
    magisk_init = require_entry(magisk_cpio, "init")
    backup_init_xz = require_entry(magisk_cpio, ".backup/init.xz")
    config_entry = require_entry(magisk_cpio, ".backup/.magisk")
    rmlist_entry = require_entry(magisk_cpio, ".backup/.rmlist")
    build_prop_stock = require_entry(stock_cpio, "system/etc/ramdisk/build.prop")
    build_prop_magisk = require_entry(magisk_cpio, "system/etc/ramdisk/build.prop")
    try:
        backup_init = lzma.decompress(backup_init_xz.data)
    except lzma.LZMAError as exc:
        raise AuditError("Magisk backup init.xz is invalid") from exc
    config = parse_properties(config_entry.data)
    rmlist = [part.decode("utf-8") for part in rmlist_entry.data.split(b"\0") if part]

    payload_map = {
        "magiskinit": (magisk_init.data, apk["magiskinit"]),
        "magisk": (lzma.decompress(require_entry(magisk_cpio, "overlay.d/sbin/magisk.xz").data), apk["magisk"]),
        "init_ld": (lzma.decompress(require_entry(magisk_cpio, "overlay.d/sbin/init-ld.xz").data), apk["init_ld"]),
        "stub": (lzma.decompress(require_entry(magisk_cpio, "overlay.d/sbin/stub.xz").data), apk["stub"]),
    }
    payload_results = {
        key: {
            "ramdisk_sha256": sha256_bytes(ramdisk_payload),
            "apk_sha256": sha256_bytes(apk_payload),
            "exact_match": ramdisk_payload == apk_payload,
        }
        for key, (ramdisk_payload, apk_payload) in payload_map.items()
    }
    kernel = kernel_patch_audit(stock["kernel"], magisk["kernel"], apk["boot_patch"])
    stock_ikconfig = extract_ikconfig(stock["kernel"])
    magisk_ikconfig = extract_ikconfig(magisk["kernel"])
    hardening_keys = [
        "CONFIG_UH",
        "CONFIG_RKP",
        "CONFIG_KDP",
        "CONFIG_SECURITY_DEFEX",
        "CONFIG_FIVE",
        "CONFIG_PROCA",
    ]
    hardening_config = config_values(stock_ikconfig, hardening_keys)
    hardening_all_enabled = all(value == "y" for value in hardening_config.values())
    rkp_preserved = (
        hardening_config["CONFIG_RKP"] == "y"
        and kernel["exactly_defex_and_proca"]
        and not kernel["recognized_patches"]["rkp_applied"]
    )
    header_equal_except_ramdisk_size = {
        key: stock["header"][key] == magisk["header"][key]
        for key in stock["header"]
        if key != "ramdisk_size"
    }
    expected_rmlist = [
        "overlay.d",
        "overlay.d/sbin",
        "overlay.d/sbin/init-ld.xz",
        "overlay.d/sbin/magisk.xz",
        "overlay.d/sbin/stub.xz",
    ]
    config_sha1_match = config.get("SHA1") == hashlib.sha1(stock_data).hexdigest()
    all_checks = {
        "stock_kernel_pin": sha256_bytes(stock["kernel"]) == EXPECTED_STOCK_KERNEL_SHA256,
        "magisk_kernel_pin": sha256_bytes(magisk["kernel"]) == EXPECTED_MAGISK_KERNEL_SHA256,
        "header_invariants": all(header_equal_except_ramdisk_size.values()),
        "signatures_identical": stock["signature"] == magisk["signature"],
        "signatures_all_zero": bool(stock["signature"]) and not any(stock["signature"]),
        "avb_vbmeta_identical": stock_avb["vbmeta"] == magisk_avb["vbmeta"],
        "stock_avb_fully_verifies": stock_avb_verify["returncode"] == 0 and stock_avb_verify["payload_hash_verified"],
        "magisk_avb_expected_stale_hash": (
            magisk_avb_verify["returncode"] != 0
            and magisk_avb_verify["vbmeta_signature_verified"]
            and magisk_avb_verify["payload_hash_mismatch"]
        ),
        "kernel_exactly_defex_proca": kernel["exactly_defex_and_proca"],
        "kernel_ikconfig_preserved": stock_ikconfig == magisk_ikconfig,
        "stock_hardening_configs_enabled": hardening_all_enabled,
        "rkp_stock_configuration_and_code_preserved": rkp_preserved,
        "stock_init_pin": sha256_bytes(stock_init.data) == EXPECTED_STOCK_INIT_SHA256,
        "magisk_init_pin": sha256_bytes(magisk_init.data) == EXPECTED_MAGISK_INIT_SHA256,
        "backup_init_exact": backup_init == stock_init.data,
        "build_prop_preserved": build_prop_stock.data == build_prop_magisk.data,
        "apk_payloads_exact": all(item["exact_match"] for item in payload_results.values()),
        "config_stock_sha1_exact": config_sha1_match,
        "rmlist_exact": rmlist == expected_rmlist,
        "ramdisk_entries_fully_classified": entry_audit["complete_classification"],
    }
    verdict = "PASS_EXACT_MAGISK_SEMANTICS_IDENTIFIED" if all(all_checks.values()) else "FAIL_CLOSED"
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "scope": {
            "host_only": True,
            "input_images_read_only": True,
            "device_contact": False,
            "boot_repack": False,
            "flash_authorized": False,
        },
        "inputs": {
            "stock_boot": {
                "path": display_path(root, stock_path),
                "size": len(stock_data),
                "sha256": sha256_bytes(stock_data),
            },
            "magisk_boot": {
                "path": display_path(root, magisk_path),
                "size": len(magisk_data),
                "sha256": sha256_bytes(magisk_data),
            },
            "magisk_apk": {
                "path": display_path(root, apk_path),
                "size": apk_path.stat().st_size,
                "sha256": sha256_file(apk_path),
            },
            "lz4": {"path": display_path(root, lz4_path), "sha256": sha256_file(lz4_path)},
            "avbtool": {"path": display_path(root, avbtool_path), "sha256": sha256_file(avbtool_path)},
        },
        "boot_container": {
            "stock_header": stock["header"],
            "magisk_header": magisk["header"],
            "header_equal_except_ramdisk_size": header_equal_except_ramdisk_size,
            "stock_layout": stock["layout"],
            "magisk_layout": magisk["layout"],
            "stock_signature": {"sha256": sha256_bytes(stock["signature"]), "all_zero": not any(stock["signature"])},
            "magisk_signature": {
                "sha256": sha256_bytes(magisk["signature"]),
                "all_zero": not any(magisk["signature"]),
            },
            "avb": {
                "stock_footer": {key: value for key, value in stock_avb.items() if key != "vbmeta"},
                "magisk_footer": {key: value for key, value in magisk_avb.items() if key != "vbmeta"},
                "vbmeta_exact_match": stock_avb["vbmeta"] == magisk_avb["vbmeta"],
                "stock_verify": stock_avb_verify,
                "magisk_verify": magisk_avb_verify,
            },
        },
        "kernel": kernel,
        "ramdisk": {
            "stock_compressed": {"size": len(stock["ramdisk"]), "sha256": sha256_bytes(stock["ramdisk"])},
            "magisk_compressed": {"size": len(magisk["ramdisk"]), "sha256": sha256_bytes(magisk["ramdisk"])},
            "stock_cpio": {
                "size": len(stock_cpio_data),
                "sha256": sha256_bytes(stock_cpio_data),
                "entries": len(stock_cpio),
            },
            "magisk_cpio": {
                "size": len(magisk_cpio_data),
                "sha256": sha256_bytes(magisk_cpio_data),
                "entries": len(magisk_cpio),
            },
            "stock_init": stock_init.summary(),
            "magisk_init": magisk_init.summary(),
            "backup_init_xz": backup_init_xz.summary(),
            "backup_init_decompressed": {
                "size": len(backup_init),
                "sha256": sha256_bytes(backup_init),
                "exact_stock_init": backup_init == stock_init.data,
            },
            "config_entry": config_entry.summary(),
            "config": config,
            "config_sha1_is_exact_stock_boot": config_sha1_match,
            "rmlist_entry": rmlist_entry.summary(),
            "rmlist": rmlist,
            "build_prop_preserved": build_prop_stock.data == build_prop_magisk.data,
            "payloads": payload_results,
            "entry_classification": entry_audit,
        },
        "checks": all_checks,
        "interpretation": {
            "known_magisk_boot_is_not_stock_kernel_identical": stock["kernel"] != magisk["kernel"],
            "kernel_delta": (
                "exactly Magisk v30.7 DEFEX and PROCA binary patches; 9 bytes in 2 ranges"
                if kernel["exactly_defex_and_proca"]
                else "unclassified kernel delta"
            ),
            "rkp_binary_pattern_patch_applied": kernel["recognized_patches"]["rkp_applied"],
            "rkp_config_enabled": hardening_config["CONFIG_RKP"] == "y",
            "rkp_stock_configuration_and_code_preserved": rkp_preserved,
            "legacy_sar_patch_applied": kernel["recognized_patches"]["legacy_sar_applied"],
            "stock_init_recoverable_from_ramdisk_backup": backup_init == stock_init.data,
            "preinit_device": config.get("PREINITDEVICE"),
            "preinit_device_partition_meaning": "unresolved for S22+ by this host-only audit",
            "r3_implication": (
                "kernel replacement policy must explicitly choose unpatched "
                "stock-equivalent or Magisk-equivalent DEFEX+PROCA patches"
            ),
            "avb_implication": (
                "Magisk copied the signed stock vbmeta exactly; its payload hash is stale "
                "and host verification fails as expected for this unlocked known-booting baseline"
            ),
        },
        "stock_hardening_ikconfig": {
            "sha256": sha256_bytes(stock_ikconfig),
            "magisk_embedded_ikconfig_exact_match": stock_ikconfig == magisk_ikconfig,
            "values": hardening_config,
        },
        "verdict": verdict,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-boot", type=Path, default=DEFAULT_STOCK_BOOT)
    parser.add_argument("--magisk-boot", type=Path, default=DEFAULT_MAGISK_BOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--avbtool", type=Path, default=DEFAULT_AVBTOOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    report = audit(args)
    out = resolve(root, args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"verdict={report['verdict']}")
    print(f"kernel_changed_bytes={report['kernel']['changed_bytes']}")
    print(f"kernel_diff_ranges={len(report['kernel']['diff_ranges'])}")
    print(f"stock_init_backup_exact={int(report['ramdisk']['backup_init_decompressed']['exact_stock_init'])}")
    print(f"apk_payloads_exact={int(report['checks']['apk_payloads_exact'])}")
    print(f"output={display_path(root, out)}")
    return 0 if report["verdict"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
