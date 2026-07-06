#!/usr/bin/env python3
"""Build the S22+ M5 in-place USB-ACM native-init boot candidate.

Host-only.  This script does not reboot, flash, or touch a connected device.

M5 is the first control-channel candidate after M4T2/M4T3 proved custom PID1
execution and recovery.  It starts from the known-booting Magisk boot image,
replaces only ramdisk `/init`, injects the measured FYG8 USB-first module
bundle under `/lib/modules/s22plus-m5/`, and builds a boot-only Odin AP.
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
    DEFAULT_ODIN,
    display_path,
    repo_root,
    require_ok,
    resolve,
    run,
    sha256_file,
    tar_members,
    write_ap_tar,
    write_boot_lz4,
)
from build_s22plus_inplace_m4t1_magiskboot import (
    DEFAULT_BASE_BOOT,
    DEFAULT_MAGISK_APK,
    DEFAULT_MAGISKBOOT,
    EXPECTED_BASE_BOOT_SHA256,
    EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
    diff_ranges,
    ensure_magiskboot,
    run_in_dir,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m5_usb_acm_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m5.c")
DEFAULT_MODULE_BUNDLE = Path("workspace/private/inputs/s22plus_module_bundles/FYG8_usb_first_m2")
MARKER = "S22_NATIVE_INIT_USB_ACM_M5"
MODULE_INSTALL_DIR = Path("lib/modules/s22plus-m5")
EXPECTED_MODULE_COUNT = 26


def compile_init(source: Path, out_path: Path, build_dir: Path) -> dict[str, str]:
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
    require_ok(result, "compile M5 USB-ACM init")
    strip = run(["aarch64-linux-gnu-strip", out_path])
    require_ok(strip, "strip M5 USB-ACM init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M5 USB-ACM init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M5 USB-ACM init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    binary = out_path.read_bytes()
    required_strings = [
        MARKER,
        "usb_first_modules=26",
        "gadget=ss_acm.0",
        "tty=/dev/ttyGS0",
        "no_android_handoff=1",
        "no_auto_reboot=1",
        "finit_rc",
        "ss_acm.0",
        "ttyGS0",
    ]
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M5 /init: {required}")
    (build_dir / "m5_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m5_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "required_strings": required_strings,
    }


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


def module_cpio_commands(module_bundle: Path, build_dir: Path) -> tuple[list[str], dict[str, object]]:
    manifest = read_module_manifest(module_bundle)
    modules = manifest["modules"]
    commands = [
        "mkdir 755 lib",
        "mkdir 755 lib/modules",
        f"mkdir 755 {MODULE_INSTALL_DIR}",
    ]
    installed: list[dict[str, object]] = []
    total_bytes = 0
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
        total_bytes += src.stat().st_size
        commands.append(f"add 644 {MODULE_INSTALL_DIR / name} {src}")
        installed.append(
            {
                "name": name,
                "size": src.stat().st_size,
                "sha256": actual_sha,
                "ramdisk_path": "/" + str(MODULE_INSTALL_DIR / name),
            }
        )
    order_file = build_dir / "s22plus-m5-module-order.txt"
    order_file.write_text("".join(str(item["name"]) + "\n" for item in installed), encoding="ascii")
    commands.append(f"add 644 {MODULE_INSTALL_DIR / 'order.txt'} {order_file}")
    return commands, {
        "module_count": len(installed),
        "total_bytes": total_bytes,
        "modules": installed,
        "module_bundle_manifest_sha256": sha256_file(module_bundle / "manifest.json"),
        "install_dir": "/" + str(MODULE_INSTALL_DIR),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--module-bundle", type=Path, default=DEFAULT_MODULE_BUNDLE)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    module_bundle = resolve(root, args.module_bundle)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    odin = resolve(root, args.odin)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, odin_dir):
        directory.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)

    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")

    m5_init = build_dir / "s22plus_init_usb_acm_m5"
    m5_init_info = compile_init(source, m5_init, build_dir)
    module_commands, module_summary = module_cpio_commands(module_bundle, build_dir)

    nochange_unpack = run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "magiskboot no-change unpack")
    nochange_repack = run_in_dir(
        [magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"],
        nochange_dir,
        "magiskboot no-change repack",
    )
    nochange_sha = sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"magiskboot no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "magiskboot unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    extract_text = run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "extract original Magisk init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    ramdisk_before_sha = sha256_file(ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_commands = [f"add 750 init {m5_init}", *module_commands]
    patch_text = run_in_dir([magiskboot, "cpio", ramdisk, *patch_commands], work_dir, "replace /init and add M5 modules")
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M5 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(m5_init):
        raise SystemExit("replaced /init does not match compiled M5 init")
    first_module = module_summary["modules"][0]
    first_module_extract = build_dir / f"module.{first_module['name']}.extract"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {MODULE_INSTALL_DIR / str(first_module['name'])} {first_module_extract}"],
        work_dir,
        "extract first M5 module",
    )
    if sha256_file(first_module_extract) != str(first_module["sha256"]):
        raise SystemExit("first inserted M5 module hash mismatch")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    ramdisk_after_sha = sha256_file(ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "magiskboot repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")

    patched_unpack_dir = out_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    patched_unpack = run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
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
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m5_init": sha256_file(m5_init),
        "module_bundle_manifest": module_summary["module_bundle_manifest_sha256"],
        "ramdisk_before": ramdisk_before_sha,
        "ramdisk_after": ramdisk_after_sha,
        "kernel": sha256_file(kernel),
        "header": sha256_file(header),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "base_boot": base_boot.stat().st_size,
        "m5_init": m5_init.stat().st_size,
        "module_bundle_total": int(module_summary["total_bytes"]),
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M5 in-place USB-ACM native-init control-channel candidate",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add USB module bundle",
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_insertions": "FYG8 USB-first 26-module bundle only",
            "configfs_runtime_gadget": "ss_acm.0 only",
            "watchdog": "not-touched",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "module_bundle": display_path(root, module_bundle),
            "magiskboot": display_path(root, magiskboot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m5_init": m5_init_info,
        "module_summary": module_summary,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "module_install_dir": "/" + str(MODULE_INSTALL_DIR),
            "module_count": module_summary["module_count"],
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patched_unpack_output": patched_unpack,
            "nochange_unpack_output": nochange_unpack,
            "nochange_repack_output": nochange_repack,
            "extract_output": extract_text,
            "patch_output": patch_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
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
    (out_dir / "required_strings.txt").write_text("\n".join(m5_init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
