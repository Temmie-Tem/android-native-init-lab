#!/usr/bin/env python3
"""Build the S22+ M4A fast-dwell direct-PID1 boot candidate.

Host-only.  This script builds a boot-only Odin AP containing exactly
`boot.img.lz4`; it does not reboot, flash, or touch a connected device.

M4A keeps the M3.2 marker-only, stock legacy-LZ4 ramdisk packaging but changes
the dwell to two seconds before requesting download mode.  The live question is
whether the earlier bootloop was caused by parking long enough for a watchdog
reset before the self-download reboot path ran.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from build_s22plus_direct_p3_boot import (
    BOOT_PARTITION_SIZE,
    DEFAULT_KERNEL,
    DEFAULT_MKBOOTIMG,
    DEFAULT_MKBOOTIMG_ARGS,
    DEFAULT_ODIN,
    DEFAULT_STOCK_ROOT,
    EXPECTED_STOCK_KERNEL_SHA256,
    copy_stock_ramdisk_root,
    display_path,
    normalize_tree_metadata,
    pack_cpio,
    pad_file,
    parse_null_args,
    repo_root,
    replace_mkbootimg_arg,
    require_ok,
    resolve,
    run,
    sha256_file,
    tar_members,
    write_ap_tar,
    write_boot_lz4,
)
from build_s22plus_marker_m31_boot import compile_init
from build_s22plus_marker_m32_boot import DEFAULT_RAMDISK_LZ4, LEGACY_LZ4_MAGIC, write_ramdisk_lz4_legacy


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/marker_m4a_fastdwell_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_marker_m4a.c")
MARKER = "S22_NATIVE_INIT_FAST_DWELL_M4A"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stock-ramdisk-root", type=Path, default=DEFAULT_STOCK_ROOT)
    parser.add_argument("--mkbootimg-args", type=Path, default=DEFAULT_MKBOOTIMG_ARGS)
    parser.add_argument("--kernel", type=Path, default=DEFAULT_KERNEL)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--mkbootimg", type=Path, default=DEFAULT_MKBOOTIMG)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--ramdisk-lz4", type=Path, default=DEFAULT_RAMDISK_LZ4)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    stock_root = resolve(root, args.stock_ramdisk_root)
    mkbootimg_args_path = resolve(root, args.mkbootimg_args)
    kernel = resolve(root, args.kernel)
    source = resolve(root, args.source)
    mkbootimg = resolve(root, args.mkbootimg)
    odin = resolve(root, args.odin)
    ramdisk_lz4_bin = resolve(root, args.ramdisk_lz4)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    root_dir = out_dir / "root"
    odin_dir = out_dir / "odin4"
    build_dir.mkdir(parents=True)
    odin_dir.mkdir(parents=True)

    kernel_sha = sha256_file(kernel)
    if kernel_sha != EXPECTED_STOCK_KERNEL_SHA256:
        raise SystemExit(f"stock kernel SHA mismatch: {kernel_sha}")
    if not ramdisk_lz4_bin.exists():
        raise SystemExit(f"legacy-LZ4 tool missing: {ramdisk_lz4_bin}")

    marker_init = build_dir / "s22plus_init_marker_m4a"
    compile_init(source, marker_init)

    copy_stock_ramdisk_root(stock_root, root_dir, marker_init)
    normalize_tree_metadata(root_dir)

    installed_init = (root_dir / "init").read_bytes()
    required_strings = (
        MARKER,
        "proof=watchdog-hypothesis-fast-self-download",
        "ramdisk_format=legacy-lz4",
        "fallback_pmsg_major=507",
        "no_usb_modules=1",
        "no_configfs=1",
        "download_reboot_after_sec=2",
        "watchdog_open_if_present=1",
    )
    for required in required_strings:
        if required.encode("ascii") not in installed_init:
            raise SystemExit(f"required marker missing from installed /init: {required}")

    ramdisk_cpio = out_dir / "ramdisk_marker_m4a.cpio"
    ramdisk_lz4 = out_dir / "ramdisk_marker_m4a.lz4"
    pack_cpio(root_dir, ramdisk_cpio)
    write_ramdisk_lz4_legacy(ramdisk_cpio, ramdisk_lz4, ramdisk_lz4_bin, build_dir)
    if ramdisk_lz4.read_bytes()[:4] != LEGACY_LZ4_MAGIC:
        raise SystemExit("legacy-LZ4 magic gate failed")

    mkargs = parse_null_args(mkbootimg_args_path)
    mkargs = replace_mkbootimg_arg(mkargs, "--kernel", kernel)
    mkargs = replace_mkbootimg_arg(mkargs, "--ramdisk", ramdisk_lz4)
    boot_unpadded = out_dir / "boot_marker_m4a_unpadded.img"
    boot_padded = out_dir / "boot.img"
    mk = run(["python3", mkbootimg, *mkargs, "--output", boot_unpadded])
    require_ok(mk, "mkbootimg")
    pad_file(boot_unpadded, boot_padded, BOOT_PARTITION_SIZE)

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_padded, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"AP tar member mismatch: {members}")

    parse_gate_text = ""
    if not args.no_odin_parse_gate and odin.exists():
        gate = run([odin, "-a", ap_md5, "-d", "/dev/bus/usb/999/999"])
        parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_gate_text, encoding="utf-8")

    hashes = {
        "source": sha256_file(source),
        "stock_kernel": kernel_sha,
        "marker_init": sha256_file(marker_init),
        "ramdisk_cpio": sha256_file(ramdisk_cpio),
        "ramdisk_lz4": sha256_file(ramdisk_lz4),
        "boot_unpadded": sha256_file(boot_unpadded),
        "boot_img": sha256_file(boot_padded),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "marker_init": marker_init.stat().st_size,
        "ramdisk_cpio": ramdisk_cpio.stat().st_size,
        "ramdisk_lz4": ramdisk_lz4.stat().st_size,
        "boot_unpadded": boot_unpadded.stat().st_size,
        "boot_img": boot_padded.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M4A fast-dwell watchdog-hypothesis direct native-init candidate",
        "safety": {
            "boot_only": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": "download-after-2s-fast-dwell",
            "persistent_partition_mount": False,
            "module_insertions": False,
            "configfs_runtime_gadget": False,
            "watchdog": "open-existing-device-only-no-mknod",
        },
        "ramdisk_packaging": {
            "format": "legacy-lz4",
            "magic_hex": ramdisk_lz4.read_bytes()[:4].hex(),
            "roundtrip_sha256": hashes["ramdisk_cpio"],
            "lz4_tool": display_path(root, ramdisk_lz4_bin),
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "stock_ramdisk_root": display_path(root, stock_root),
            "kernel": display_path(root, kernel),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "tar_members": members,
        "required_strings": list(required_strings),
        "odin_invalid_device_parse_gate": parse_gate_text,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())),
        encoding="ascii",
    )
    (out_dir / "sizes.txt").write_text(
        "".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())),
        encoding="ascii",
    )
    (out_dir / "required_strings.txt").write_text("\n".join(required_strings) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
