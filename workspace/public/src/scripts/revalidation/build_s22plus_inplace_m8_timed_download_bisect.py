#!/usr/bin/env python3
"""Build the S22+ M8 timed-download module-bisect native-init candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M8 is a discriminator after the M7 live bootloop. It preserves the M7
freestanding runtime and stock vendor_boot /lib/modules source, but does not
try ACM/configfs. Instead it loads the first half of the M7-only module delta
relative to M5, then immediately requests Samsung download mode. A future live
self-download proves PID1 survived that bounded module batch.
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
from build_s22plus_inplace_m5_usb_acm import (
    DEFAULT_MODULE_BUNDLE as DEFAULT_M5_MODULE_BUNDLE,
    EXPECTED_MODULE_COUNT as EXPECTED_M5_MODULE_COUNT,
)
from build_s22plus_inplace_m7_usb_subset import (
    DEFAULT_LZ4,
    DEFAULT_VENDOR_RAMDISK,
    WATCHDOG_BLOCKLIST,
    extract_vendor_ramdisk_metadata,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m8_timed_download_bisect_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m8_timed_download_bisect.c")
MARKER = "S22_NATIVE_INIT_M8_TIMED_DOWNLOAD"
MODULE_BATCH_RAMDISK = "s22plus_m8_delta_batch.modules"
EXPECTED_M7_SUBSET_COUNT = 53
EXPECTED_M7_ONLY_COUNT = 36
EXPECTED_M8_BATCH_COUNT = 18


def read_m5_module_names(module_bundle: Path) -> list[str]:
    manifest_path = module_bundle / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"M5 module bundle manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    modules = manifest.get("modules")
    if not isinstance(modules, list):
        raise SystemExit("M5 module bundle manifest has no modules list")
    names: list[str] = []
    for item in modules:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise SystemExit(f"bad M5 module item: {item!r}")
        names.append(str(item["name"]))
    if len(names) != EXPECTED_M5_MODULE_COUNT:
        raise SystemExit(f"M5 module count mismatch: {len(names)} != {EXPECTED_M5_MODULE_COUNT}")
    if len(set(names)) != len(names):
        raise SystemExit("M5 module list contains duplicates")
    return names


def derive_m8_batch(vendor_summary: dict[str, object], m5_names: list[str], build_dir: Path) -> dict[str, object]:
    m7_info = vendor_summary.get("m7_usb_subset")
    if not isinstance(m7_info, dict):
        raise SystemExit("vendor summary missing m7_usb_subset")
    m7_subset = m7_info.get("subset")
    if not isinstance(m7_subset, list) or not all(isinstance(item, str) for item in m7_subset):
        raise SystemExit("vendor summary has invalid M7 subset")
    if len(m7_subset) != EXPECTED_M7_SUBSET_COUNT:
        raise SystemExit(f"M7 subset count mismatch: {len(m7_subset)} != {EXPECTED_M7_SUBSET_COUNT}")
    if len(set(m7_subset)) != len(m7_subset):
        raise SystemExit("M7 subset contains duplicates")

    m5_set = set(m5_names)
    m7_only = [module for module in m7_subset if module not in m5_set]
    m5_overlap = [module for module in m7_subset if module in m5_set]
    m5_only = [module for module in m5_names if module not in set(m7_subset)]
    if len(m7_only) != EXPECTED_M7_ONLY_COUNT:
        raise SystemExit(f"M7-only delta count mismatch: {len(m7_only)} != {EXPECTED_M7_ONLY_COUNT}")
    if len(m5_overlap) + len(m7_only) != len(m7_subset):
        raise SystemExit("M5/M7 set accounting mismatch")

    batch = m7_only[:EXPECTED_M8_BATCH_COUNT]
    if len(batch) != EXPECTED_M8_BATCH_COUNT:
        raise SystemExit(f"M8 batch count mismatch: {len(batch)} != {EXPECTED_M8_BATCH_COUNT}")
    if any(module in WATCHDOG_BLOCKLIST for module in batch):
        raise SystemExit(f"M8 batch contains watchdog module: {batch}")
    if any("audio" in module.lower() or "snd" in module.lower() for module in batch):
        raise SystemExit(f"M8 batch contains audio module: {batch}")
    batch_text = "".join(f"{module}\n" for module in batch)
    if len(batch_text.encode("utf-8")) >= 4096:
        raise SystemExit("M8 batch text does not fit runtime parser buffer")
    if any(len(module) >= 128 for module in batch):
        raise SystemExit("M8 batch module basename does not fit runtime parser buffer")

    batch_path = build_dir / MODULE_BATCH_RAMDISK
    batch_path.write_text(batch_text, encoding="ascii")
    (build_dir / "m8_m7_only_delta_full.txt").write_text("".join(f"{module}\n" for module in m7_only), encoding="ascii")
    (build_dir / "m8_m5_overlap_with_m7.txt").write_text(
        "".join(f"{module}\n" for module in m5_overlap),
        encoding="ascii",
    )
    (build_dir / "m8_m5_only_not_in_m7.txt").write_text("".join(f"{module}\n" for module in m5_only), encoding="ascii")

    return {
        "strategy": "m7_only_first_half",
        "m5_count": len(m5_names),
        "m7_subset_count": len(m7_subset),
        "m7_only_count": len(m7_only),
        "m7_overlap_with_m5_count": len(m5_overlap),
        "m5_only_not_in_m7_count": len(m5_only),
        "batch_count": len(batch),
        "batch_bytes": len(batch_text.encode("utf-8")),
        "batch_path": "/" + MODULE_BATCH_RAMDISK,
        "batch": batch,
        "m7_only_delta": m7_only,
        "m7_overlap_with_m5": m5_overlap,
        "m5_only_not_in_m7": m5_only,
        "watchdog_blocklist": sorted(WATCHDOG_BLOCKLIST),
    }


def compile_init(source: Path, out_path: Path, build_dir: Path) -> dict[str, str | list[str]]:
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wl,-e,_start",
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, "compile M8 timed-download init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M8 timed-download init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M8 timed-download init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M8 timed-download init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M8 timed-download init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M8 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M8 init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit("M8 init disassembly does not contain svc")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        "/s22plus_m8_delta_batch.modules",
        "batch_strategy=m7_only_first_half",
        "expected_module_count=18",
        "no_usb_acm=1",
        "no_configfs=1",
        "auto_reboot_download_after_batch=1",
        "phase=timed_download",
        "download",
    ]
    forbidden_strings = [
        b"ld-linux",
        b"libc.so",
        b"/vendor_dlkm",
        b"ttyGS0",
        b"ss_acm.0",
        b"usb_gadget",
        b"/config",
        b"modules.load.recovery",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M8 /init: {required}")
    for forbidden in forbidden_strings:
        if forbidden in binary:
            raise SystemExit(f"M8 /init contains forbidden string: {forbidden!r}")

    (build_dir / "m8_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m8_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "m8_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
        "forbidden_strings": [item.decode("ascii") for item in forbidden_strings],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--m5-module-bundle", type=Path, default=DEFAULT_M5_MODULE_BUNDLE)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
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
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    m5_module_bundle = resolve(root, args.m5_module_bundle)
    lz4_tool = resolve(root, args.lz4)
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

    vendor_summary = extract_vendor_ramdisk_metadata(vendor_ramdisk, lz4_tool, build_dir)
    m5_names = read_m5_module_names(m5_module_bundle)
    batch_summary = derive_m8_batch(vendor_summary, m5_names, build_dir)
    m8_init = build_dir / "s22plus_init_m8_timed_download"
    m8_init_info = compile_init(source, m8_init, build_dir)

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

    batch_file = build_dir / MODULE_BATCH_RAMDISK
    if not batch_file.exists():
        raise SystemExit(f"M8 batch file missing: {batch_file}")
    patch_init_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 750 init {m8_init}"],
        work_dir,
        "replace /init with M8 init",
    )
    patch_batch_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULE_BATCH_RAMDISK} {batch_file}"],
        work_dir,
        "add M8 delta batch list",
    )
    patch_text = patch_init_text + "\n" + patch_batch_text
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M8 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(m8_init):
        raise SystemExit("replaced /init does not match compiled M8 init")
    extracted_batch = build_dir / f"{MODULE_BATCH_RAMDISK}.extracted"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {MODULE_BATCH_RAMDISK} {extracted_batch}"],
        work_dir,
        "extract M8 delta batch list",
    )
    if sha256_file(extracted_batch) != sha256_file(batch_file):
        raise SystemExit("replaced M8 batch list does not match builder output")

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
        "vendor_ramdisk": sha256_file(vendor_ramdisk),
        "m5_module_bundle_manifest": sha256_file(m5_module_bundle / "manifest.json"),
        "m8_delta_batch": sha256_file(batch_file),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m8_init": sha256_file(m8_init),
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
        "vendor_ramdisk_lz4": vendor_ramdisk.stat().st_size,
        "vendor_ramdisk_cpio": int(vendor_summary["cpio_size"]),
        "m8_delta_batch": batch_file.stat().st_size,
        "m8_init": m8_init.stat().st_size,
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
        "purpose": "M8 in-place native-init timed-download bisect for the first half of M7-only module delta",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one module-list text file",
            "runtime": "freestanding-raw-syscall",
            "glibc_static_startup": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": "download-after-bounded-module-batch",
            "host_commanded_reboot_download": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_insertions": "boot ramdisk gets text list only; runtime uses stock vendor_boot /lib/modules",
            "module_binary_injection": False,
            "module_list_path": f"/{MODULE_BATCH_RAMDISK}",
            "module_subset": "first 18 modules from M7-only delta relative to M5, in M7 recovery order",
            "configfs_runtime_gadget": False,
            "udc_binding": False,
            "usb_role_force": False,
            "watchdog": "not-touched-by-init-source; watchdog modules excluded from inherited M7 subset",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "m5_module_bundle": display_path(root, m5_module_bundle),
            "lz4": display_path(root, lz4_tool),
            "magiskboot": display_path(root, magiskboot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m8_init": m8_init_info,
        "vendor_ramdisk": vendor_summary,
        "m8_batch": batch_summary,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_batch_entry": MODULE_BATCH_RAMDISK,
            "added_batch_entry_mode": "640",
            "module_files_injected_into_boot_ramdisk": 0,
            "module_list_files_injected_into_boot_ramdisk": 1,
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
    (out_dir / "required_strings.txt").write_text("\n".join(m8_init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
