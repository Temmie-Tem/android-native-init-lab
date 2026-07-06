#!/usr/bin/env python3
"""Build the S22+ observable native-init M3 boot candidate.

Host-only.  This script builds a boot-only Odin AP containing exactly
`boot.img.lz4`; it does not reboot, flash, or touch a connected device.

M3 extends the P3 direct-PID1 candidate with the measured USB-first vendor
module bundle and a minimal NCM configfs observation path.  The private module
bundle is copied into the ramdisk under `/lib/modules/s22plus-m3/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
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
    pad_file,
    pack_cpio,
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/observable_m3_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_observable_m3.c")
DEFAULT_MODULE_BUNDLE = Path("workspace/private/inputs/s22plus_module_bundles/FYG8_usb_first_m2")
MARKER = "S22_NATIVE_INIT_OBSERVABLE_M3"
MODULE_INSTALL_DIR = Path("lib/modules/s22plus-m3")
EXPECTED_MODULE_COUNT = 26


def normalize_tree_metadata(root_dir: Path) -> None:
    for path in sorted(root_dir.rglob("*")):
        # Keep symlink metadata normalization best-effort and deterministic.
        try:
            path.chmod(path.stat(follow_symlinks=False).st_mode & 0o7777, follow_symlinks=False)
        except (NotImplementedError, OSError):
            pass
        os_utime(path)
    os_utime(root_dir)


def os_utime(path: Path) -> None:
    import os

    os.utime(path, (0, 0), follow_symlinks=False)


def read_module_manifest(module_bundle: Path) -> dict[str, object]:
    manifest_path = module_bundle / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"module bundle manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    modules = manifest.get("modules")
    if not isinstance(modules, list):
        raise SystemExit("module bundle manifest has no modules list")
    if len(modules) != EXPECTED_MODULE_COUNT:
        raise SystemExit(f"module bundle count mismatch: {len(modules)} != {EXPECTED_MODULE_COUNT}")
    missing = manifest.get("missing")
    if missing:
        raise SystemExit(f"module bundle manifest records missing modules: {missing}")
    return manifest


def install_module_bundle(module_bundle: Path, root_dir: Path) -> dict[str, object]:
    manifest = read_module_manifest(module_bundle)
    modules = manifest["modules"]
    target_dir = root_dir / MODULE_INSTALL_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    installed: list[dict[str, object]] = []
    for item in modules:
        if not isinstance(item, dict):
            raise SystemExit(f"bad module manifest item: {item!r}")
        name = item.get("name")
        expected_sha = item.get("sha256")
        if not isinstance(name, str) or not isinstance(expected_sha, str):
            raise SystemExit(f"bad module manifest item: {item!r}")
        src = module_bundle / "modules" / name
        if not src.exists():
            raise SystemExit(f"module missing from bundle: {src}")
        actual_sha = sha256_file(src)
        if actual_sha != expected_sha:
            raise SystemExit(f"module SHA mismatch for {name}: {actual_sha} != {expected_sha}")
        dst = target_dir / name
        shutil.copy2(src, dst)
        dst.chmod(0o644)
        installed.append({
            "name": name,
            "size": dst.stat().st_size,
            "sha256": actual_sha,
            "ramdisk_path": "/" + str(MODULE_INSTALL_DIR / name),
        })

    (target_dir / "order.txt").write_text("".join(str(item["name"]) + "\n" for item in installed), encoding="ascii")
    (target_dir / "manifest.json").write_text(json.dumps({
        "target": manifest.get("target"),
        "module_count": len(installed),
        "total_bytes": sum(int(item["size"]) for item in installed),
        "modules": installed,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "module_count": len(installed),
        "total_bytes": sum(int(item["size"]) for item in installed),
        "modules": installed,
        "module_bundle_manifest_sha256": sha256_file(module_bundle / "manifest.json"),
    }


def compile_init(source: Path, out_path: Path) -> None:
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-static",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, "compile observable init")
    strip = run(["aarch64-linux-gnu-strip", out_path])
    require_ok(strip, "strip observable init")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stock-ramdisk-root", type=Path, default=DEFAULT_STOCK_ROOT)
    parser.add_argument("--mkbootimg-args", type=Path, default=DEFAULT_MKBOOTIMG_ARGS)
    parser.add_argument("--kernel", type=Path, default=DEFAULT_KERNEL)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--module-bundle", type=Path, default=DEFAULT_MODULE_BUNDLE)
    parser.add_argument("--mkbootimg", type=Path, default=DEFAULT_MKBOOTIMG)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    stock_root = resolve(root, args.stock_ramdisk_root)
    mkbootimg_args_path = resolve(root, args.mkbootimg_args)
    kernel = resolve(root, args.kernel)
    source = resolve(root, args.source)
    module_bundle = resolve(root, args.module_bundle)
    mkbootimg = resolve(root, args.mkbootimg)
    odin = resolve(root, args.odin)

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

    observable_init = build_dir / "s22plus_init_observable_m3"
    compile_init(source, observable_init)

    copy_stock_ramdisk_root(stock_root, root_dir, observable_init)
    module_summary = install_module_bundle(module_bundle, root_dir)
    normalize_tree_metadata(root_dir)

    required_init = (root_dir / "init").read_bytes()
    for required in (MARKER, "finit_rc", "ncm.0", "pmsg", "link_only=1"):
        if required.encode("ascii") not in required_init:
            raise SystemExit(f"required marker missing from installed /init: {required}")

    ramdisk_cpio = out_dir / "ramdisk_observable_m3.cpio"
    pack_cpio(root_dir, ramdisk_cpio)

    mkargs = parse_null_args(mkbootimg_args_path)
    mkargs = replace_mkbootimg_arg(mkargs, "--kernel", kernel)
    mkargs = replace_mkbootimg_arg(mkargs, "--ramdisk", ramdisk_cpio)
    boot_unpadded = out_dir / "boot_observable_m3_unpadded.img"
    boot_padded = out_dir / "boot.img"
    mkcmd = ["python3", mkbootimg, *mkargs, "--output", boot_unpadded]
    mk = run(mkcmd)
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
        "observable_init": sha256_file(observable_init),
        "module_bundle_manifest": module_summary["module_bundle_manifest_sha256"],
        "ramdisk_cpio": sha256_file(ramdisk_cpio),
        "boot_unpadded": sha256_file(boot_unpadded),
        "boot_img": sha256_file(boot_padded),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "observable_init": observable_init.stat().st_size,
        "module_bundle_total": int(module_summary["total_bytes"]),
        "ramdisk_cpio": ramdisk_cpio.stat().st_size,
        "boot_unpadded": boot_unpadded.stat().st_size,
        "boot_img": boot_padded.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M3 observable native-init host-only candidate",
        "safety": {
            "boot_only": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "persistent_partition_mount": False,
            "module_insertions": "USB-first vendor .ko bundle only",
            "configfs_runtime_gadget": "ncm.0 link-only",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "stock_ramdisk_root": display_path(root, stock_root),
            "kernel": display_path(root, kernel),
            "module_bundle": display_path(root, module_bundle),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "module_summary": module_summary,
        "hashes": hashes,
        "sizes": sizes,
        "tar_members": members,
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
    (out_dir / "required_strings.txt").write_text(
        f"{MARKER}\nfinit_rc\nncm.0\npmsg\nlink_only=1\n",
        encoding="ascii",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
