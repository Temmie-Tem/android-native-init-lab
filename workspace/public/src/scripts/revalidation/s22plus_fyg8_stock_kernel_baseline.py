#!/usr/bin/env python3
"""Generate a host-only static baseline for the pinned FYG8 stock boot kernel."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_stock_kernel_baseline_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SOURCE_DATE_EPOCH = 1754027756
DEFAULT_INPUT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/stock-baseline"
)
EXPECTED_BOOT_SHA256 = "4150b962314e6136acba61b20f471d6ee1c418b83cf8c3ee4d9cf7c91a3640ae"
EXPECTED_KERNEL_SHA256 = "027d4ab6f39d4544f87d33b219bb7877ab9b662b40434bfb96464c1193aeb69d"
EXPECTED_KERNEL_RELEASE = "5.10.226-android12-9-30958166-abS906NKSS7FYG8"
EXPECTED_COMPILER = "Android (7284624, based on r416183b) clang version 12.0.5"
ANDROID_MAGIC = b"ANDROID!"
ARM64_IMAGE_MAGIC = 0x644D5241
IKCONFIG_START = b"IKCFG_ST"
IKCONFIG_END = b"IKCFG_ED"


class BaselineError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise BaselineError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decode_os_version(value: int) -> dict[str, Any]:
    major = (value >> 25) & 0x7F
    minor = (value >> 18) & 0x7F
    patch = (value >> 11) & 0x7F
    year = ((value >> 4) & 0x7F) + 2000
    month = value & 0xF
    return {
        "encoded": value,
        "os_version": f"{major}.{minor}.{patch}",
        "os_patch_level": f"{year:04d}-{month:02d}",
    }


def parse_boot_header(data: bytes) -> dict[str, Any]:
    if len(data) < 1584 or data[:8] != ANDROID_MAGIC:
        raise BaselineError("not an Android boot image v3/v4 header")
    kernel_size, ramdisk_size, os_version, header_size = struct.unpack_from("<4I", data, 8)
    header_version = struct.unpack_from("<I", data, 40)[0]
    if header_version not in (3, 4):
        raise BaselineError(f"unexpected boot header version: {header_version}")
    command_line = data[44:1580].split(b"\0", 1)[0].decode("ascii", errors="strict")
    signature_size = struct.unpack_from("<I", data, 1580)[0] if header_version == 4 else 0
    return {
        "magic": "ANDROID!",
        "header_version": header_version,
        "header_size": header_size,
        "alignment_bytes": 4096,
        "kernel_size": kernel_size,
        "ramdisk_size": ramdisk_size,
        "signature_size": signature_size,
        "command_line": command_line,
        "load_addresses_encoded": False,
        **decode_os_version(os_version),
    }


def parse_arm64_image(data: bytes) -> dict[str, Any]:
    if len(data) < 64:
        raise BaselineError("kernel payload is too short for arm64 Image header")
    text_offset, image_size, flags = struct.unpack_from("<3Q", data, 8)
    magic = struct.unpack_from("<I", data, 56)[0]
    if magic != ARM64_IMAGE_MAGIC:
        raise BaselineError(f"unexpected arm64 Image magic: 0x{magic:08x}")
    return {
        "format": "arm64 Image",
        "magic": "ARM64",
        "text_offset": text_offset,
        "image_size": image_size,
        "flags": flags,
    }


def extract_ikconfig(data: bytes) -> bytes:
    start = data.find(IKCONFIG_START)
    end = data.find(IKCONFIG_END, start + len(IKCONFIG_START))
    if start < 0 or end < 0:
        raise BaselineError("embedded IKCONFIG markers not found")
    compressed = data[start + len(IKCONFIG_START) : end]
    try:
        config = gzip.decompress(compressed)
    except gzip.BadGzipFile as exc:
        raise BaselineError("embedded IKCONFIG gzip payload is invalid") from exc
    if not config.startswith(b"#\n# Automatically generated file"):
        raise BaselineError("embedded IKCONFIG has unexpected prefix")
    return config


def find_ascii(data: bytes, pattern: bytes, label: str) -> str:
    match = re.search(pattern, data)
    if match is None:
        raise BaselineError(f"{label} not found in stock kernel")
    return match.group(1).decode("ascii")


def load_hash_manifest(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for raw in path.read_text(encoding="ascii").splitlines():
        digest, filename = raw.split(None, 1)
        hashes[Path(filename).name] = digest
    return hashes


def build_artifacts(root: Path, input_dir: Path) -> dict[str, bytes]:
    boot = input_dir / "raw/boot.img"
    kernel = input_dir / "unpack-boot/kernel"
    ramdisk = input_dir / "unpack-boot/ramdisk"
    signature = input_dir / "unpack-boot/boot_signature"
    hash_manifest = input_dir / "S906NKSS7FYG8_SKC_extracted_images.sha256"
    for path in (boot, kernel, ramdisk, signature, hash_manifest):
        if not path.is_file():
            raise BaselineError(f"required stock artifact missing: {path}")
    boot_sha = sha256_file(boot)
    kernel_sha = sha256_file(kernel)
    if boot_sha != EXPECTED_BOOT_SHA256:
        raise BaselineError(f"stock boot SHA256 mismatch: {boot_sha}")
    if kernel_sha != EXPECTED_KERNEL_SHA256:
        raise BaselineError(f"stock kernel SHA256 mismatch: {kernel_sha}")
    pinned_hashes = load_hash_manifest(hash_manifest)
    if pinned_hashes.get("boot.img") != boot_sha:
        raise BaselineError("stock boot does not match extracted-images SHA256 manifest")

    boot_data = boot.read_bytes()
    kernel_data = kernel.read_bytes()
    ikconfig = extract_ikconfig(kernel_data)
    kernel_release = find_ascii(
        kernel_data,
        rb"(5\.10\.226-android12-9-30958166-abS906NKSS7FYG8)",
        "kernel release",
    )
    linux_banner = find_ascii(kernel_data, rb"(Linux version 5\.10\.226[^\x00\n]+)", "Linux banner")
    if kernel_release != EXPECTED_KERNEL_RELEASE or EXPECTED_COMPILER not in linux_banner:
        raise BaselineError("stock kernel release or compiler identity mismatch")
    config_text = ikconfig.decode("ascii")
    required_config = {
        "CONFIG_IKCONFIG": "y",
        "CONFIG_IKCONFIG_PROC": "y",
        "CONFIG_LTO_CLANG_FULL": "y",
        "CONFIG_MODVERSIONS": "y",
        "CONFIG_ARM64_4K_PAGES": "y",
    }
    config_results = {
        key: bool(re.search(rf"^{re.escape(key)}={re.escape(value)}$", config_text, re.MULTILINE))
        for key, value in required_config.items()
    }
    if not all(config_results.values()):
        raise BaselineError(f"required stock IKCONFIG values missing: {config_results}")

    baseline = {
        "schema": SCHEMA,
        "target": TARGET,
        "generated_epoch": SOURCE_DATE_EPOCH,
        "host_only": True,
        "inputs": {
            "boot_img": {"path": display_path(root, boot), "size": boot.stat().st_size, "sha256": boot_sha},
            "kernel": {"path": display_path(root, kernel), "size": kernel.stat().st_size, "sha256": kernel_sha},
            "ramdisk": {"path": display_path(root, ramdisk), "size": ramdisk.stat().st_size, "sha256": sha256_file(ramdisk)},
            "boot_signature": {"path": display_path(root, signature), "size": signature.stat().st_size, "sha256": sha256_file(signature)},
            "hash_manifest": {"path": display_path(root, hash_manifest), "sha256": sha256_file(hash_manifest)},
        },
        "boot_img_sha256_manifest_crosscheck": "match",
        "boot_header": parse_boot_header(boot_data),
        "kernel_payload": {
            **parse_arm64_image(kernel_data),
            "sha256": kernel_sha,
            "payload_bytes": len(kernel_data),
            "compression": "none",
        },
        "kernel_release": kernel_release,
        "linux_banner": linux_banner,
        "ikconfig": {
            "present": True,
            "bytes": len(ikconfig),
            "sha256": hashlib.sha256(ikconfig).hexdigest(),
            "required_values": config_results,
        },
        "interpretation": {
            "stock_static_baseline": True,
            "rebuild_compatibility_proved": False,
            "bootability_proved": False,
            "flash_authorized": False,
        },
        "safety": {
            "device_contact": False,
            "image_unpack": False,
            "image_packaging": False,
            "flash": False,
            "partition_write": False,
        },
    }
    baseline_bytes = (json.dumps(baseline, indent=2, sort_keys=True) + "\n").encode("ascii")
    return {
        "stock-kernel-baseline.json": baseline_bytes,
        "stock-ikconfig": ikconfig,
        "stock-ikconfig.sha256": (hashlib.sha256(ikconfig).hexdigest() + "  stock-ikconfig\n").encode("ascii"),
    }


def write_artifacts(out_dir: Path, artifacts: dict[str, bytes]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in artifacts.items():
        (out_dir / name).write_bytes(data)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    out_dir = resolve(root, args.out)
    artifacts = build_artifacts(root, resolve(root, args.input))
    write_artifacts(out_dir, artifacts)
    baseline = json.loads(artifacts["stock-kernel-baseline.json"])
    print(json.dumps({"result": "pass", "out": display_path(root, out_dir), "kernel_release": baseline["kernel_release"], "boot_header_version": baseline["boot_header"]["header_version"], "ikconfig_sha256": baseline["ikconfig"]["sha256"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BaselineError, OSError, UnicodeError) as exc:
        raise SystemExit(str(exc)) from exc
