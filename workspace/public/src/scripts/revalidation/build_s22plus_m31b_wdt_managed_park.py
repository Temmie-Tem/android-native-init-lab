#!/usr/bin/env python3
"""Build S22+ M31B watchdog-managed park native-init artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M31B is the PMIC/PON watchdog-ceiling discriminator. It injects a direct PID1
that loads only the stock watchdog dependency closure and then parks. A future
live gate must be separately SHA-pinned in AGENTS.md before the AP can be
flashed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_s22plus_inplace_m23_dts_exact_qmp_park as m23
from build_s22plus_direct_p3_boot import (
    BOOT_PARTITION_SIZE,
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m31b_wdt_managed_park_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m31b_wdt_managed_park.c")
DEFAULT_VENDOR_RAMDISK = m23.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = m23.DEFAULT_LZ4

MODULES_RAMDISK = "s22plus_m31b_wdt_managed.modules"
MARKER = "S22_NATIVE_INIT_M31B_WDT_MANAGED_PARK"
TARGET_MODULE = "gh_virt_wdt.ko"
EXPECTED_WDT_CLOSURE = [
    "smem.ko",
    "minidump.ko",
    "qcom-scm.ko",
    "qcom_wdt_core.ko",
    "gh_virt_wdt.ko",
]
FORBIDDEN_MODULES = {
    "qcom_soc_wdt.ko",
    "sec_qc_qcom_wdt_core.ko",
    "phy-msm-ssusb-qmp.ko",
    "dwc3-msm.ko",
    "usb_f_ss_acm.ko",
    "eud.ko",
}


def watchdog_closure(*, dep_map: dict[str, list[str]], recovery_basenames: list[str]) -> dict[str, Any]:
    order_index = {module: index for index, module in enumerate(recovery_basenames)}
    seen: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []
    missing: set[str] = set()

    def sort_key(module: str) -> tuple[int, str]:
        return (order_index.get(module, 10**9), module)

    def visit(module: str) -> None:
        if module in seen:
            return
        if module in FORBIDDEN_MODULES:
            raise SystemExit(f"forbidden module reached in M31B watchdog closure: {module}")
        if module not in dep_map:
            missing.add(module)
            return
        if module in visiting:
            raise SystemExit(f"cycle in modules.dep while visiting {module}")
        visiting.add(module)
        for dep in sorted(dep_map[module], key=sort_key):
            visit(dep)
        visiting.remove(module)
        seen.add(module)
        ordered.append(module)

    visit(TARGET_MODULE)
    if missing:
        raise SystemExit(f"M31B watchdog closure missing modules.dep entries: {sorted(missing)}")
    if ordered != EXPECTED_WDT_CLOSURE:
        raise SystemExit(f"M31B watchdog closure drifted: {ordered!r} != {EXPECTED_WDT_CLOSURE!r}")

    module_text = "".join(f"{module}\n" for module in ordered)
    return {
        "target": TARGET_MODULE,
        "modules": ordered,
        "module_count": len(ordered),
        "module_text": module_text,
        "module_sha256": None,
        "stock_recovery_positions": {
            module: recovery_basenames.index(module) + 1
            for module in ordered
            if module in recovery_basenames
        },
        "order_model": "modules.dep topological order with stock modules.load.recovery tie-breaks",
    }


def compile_init(source: Path, out_path: Path, build_dir: Path, module_count: int) -> dict[str, Any]:
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-fno-asynchronous-unwind-tables",
            "-fno-unwind-tables",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wl,--build-id=none",
            "-Wl,-e,_start",
            "-Wl,-z,noexecstack",
            f"-DM31B_MODULE_LIMIT={module_count}",
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, "compile M31B watchdog-managed init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M31B watchdog-managed init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M31B init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M31B init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M31B init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M31B init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M31B init is not AArch64")
    if not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit("M31B init does not load arm64 __NR_finit_module (273)")
    if any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines()):
        raise SystemExit("M31B init must not load arm64 __NR_reboot (142)")

    required_strings = [
        MARKER,
        "version=0.1",
        "observation=watchdog-managed-park",
        "no_reboot_request=1",
        "no_download_beacon=1",
        f"module_count={module_count}",
        f"/{MODULES_RAMDISK}",
        "phase=modules_load_done",
        "phase=park_enter",
    ]
    forbidden_strings = [
        b"reboot_request=download",
        b"ttyGS0",
        b"ss_acm.0",
        b"/config",
        b"usb_gadget",
        b"ld-linux",
        b"libc.so",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M31B /init: {required}")
    for forbidden in forbidden_strings:
        if forbidden in binary:
            raise SystemExit(f"M31B /init contains forbidden string: {forbidden!r}")

    (build_dir / "m31b_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m31b_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "m31b_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    patched_unpack_dir = out_dir / "patched-unpack"
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, patched_unpack_dir, odin_dir):
        directory.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)
    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")

    vendor_metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    closure = watchdog_closure(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
    )
    module_list = build_dir / MODULES_RAMDISK
    module_list.write_text(str(closure["module_text"]), encoding="ascii")
    closure["module_sha256"] = sha256_file(module_list)

    init_out = build_dir / "s22plus_init_m31b_wdt_managed_park"
    init_info = compile_init(source, init_out, build_dir, int(closure["module_count"]))

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "M31B no-change unpack")
    run_in_dir([magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"], nochange_dir, "M31B no-change repack")
    nochange_sha = sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M31B no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "M31B unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "M31B extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, "M31B replace /init")
    patch_modules_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULES_RAMDISK} {module_list}"],
        work_dir,
        "M31B add module list",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M31B patch: {cpio_test_after}")

    extracted_init = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, "M31B extract replaced init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit("replaced /init does not match compiled M31B init")
    extracted_modules = build_dir / f"{MODULES_RAMDISK}.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract {MODULES_RAMDISK} {extracted_modules}"], work_dir, "M31B extract module list")
    if sha256_file(extracted_modules) != sha256_file(module_list):
        raise SystemExit("replaced M31B module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "M31B repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M31B patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "M31B unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("M31B patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M31B AP tar member mismatch: {members}")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m31b_wdt_modules": sha256_file(module_list),
        "m31b_init": sha256_file(init_out),
        "ramdisk_before": sha256_file(ramdisk_before),
        "ramdisk_after": sha256_file(ramdisk_after),
        "kernel": sha256_file(kernel),
        "header": sha256_file(header),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "base_boot": base_boot.stat().st_size,
        "m31b_wdt_modules": module_list.stat().st_size,
        "m31b_init": init_out.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    manifest: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M31B watchdog-managed park; test PMIC/PON watchdog ceiling removal",
        "closure": closure,
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one text module list",
            "runtime": "freestanding-raw-syscall",
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "intended_reboot_syscall": False,
            "reboot_request": None,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_list_path": f"/{MODULES_RAMDISK}",
            "configfs_runtime_gadget": False,
            "usb_role_force": False,
            "acm": False,
            "observation_model": "operator/host observes no PMIC/RDX reset past 60-120s; manual Download rollback expected",
        },
        "vendor": {
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "vendor_ramdisk_sha256": sha256_file(vendor_ramdisk),
            "metadata_hashes": vendor_metadata["metadata_hashes"],
            "modules_load_count": vendor_metadata["modules_load_count"],
            "modules_load_recovery_count": vendor_metadata["modules_load_recovery_count"],
            "modules_dep_count": vendor_metadata["modules_dep_count"],
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m31b_init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": MODULES_RAMDISK,
            "added_subset_entry_mode": "640",
            "module_files_injected_into_boot_ramdisk": 0,
            "module_list_files_injected_into_boot_ramdisk": 1,
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patch_output": patch_init_text + "\n" + patch_modules_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    (out_dir / "sizes.txt").write_text("".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())), encoding="ascii")
    (out_dir / "required_strings.txt").write_text("\n".join(init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
