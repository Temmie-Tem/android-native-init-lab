#!/usr/bin/env python3
"""Build S22+ M18 prefix-download native-init discriminator artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M18 starts from the M13 no-module floor, loads the first N modules from the M17
power-QMP list, then requests download mode if the checkpoint is reached. The
default matrix builds P00 and P10 only; live flashing is not authorized here.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
from build_s22plus_inplace_m17_power_qmp_park import (
    DEFAULT_LZ4,
    DEFAULT_VENDOR_RAMDISK,
    EXPECTED_POWER_QMP_SUBSET,
    MODULES_POWER_QMP_RAMDISK as M17_MODULES_POWER_QMP_RAMDISK,
    extract_vendor_ramdisk_metadata,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m18_prefix_download_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m18_prefix_download.c")
M18_MODULES_POWER_QMP_RAMDISK = "s22plus_m18_power_qmp.modules"
MARKER = "S22_NATIVE_INIT_M18_PREFIX_DOWNLOAD"
DOWNLOAD_ARG = "download"
DEFAULT_PREFIXES = (0, 10)


def prefix_label(prefix_count: int) -> str:
    return f"P{prefix_count:02d}"


def compile_init(source: Path, out_path: Path, build_dir: Path, prefix_count: int) -> dict[str, str | list[str]]:
    label = prefix_label(prefix_count)
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
            f"-DM18_PREFIX_LIMIT={prefix_count}",
            f'-DM18_PREFIX_LABEL="{label}"',
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, f"compile M18 {label} prefix-download init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, f"strip M18 {label} prefix-download init")

    file_info = run(["file", out_path])
    require_ok(file_info, f"file M18 {label} init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, f"readelf M18 {label} init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, f"objdump M18 {label} init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit(f"M18 {label} init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit(f"M18 {label} init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit(f"M18 {label} init disassembly does not contain svc")
    if not any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M18 {label} init disassembly does not load arm64 __NR_reboot (142)")
    if prefix_count > 0 and not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M18 {label} init disassembly does not load arm64 __NR_finit_module (273)")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"prefix_label={label}",
        f"prefix_limit={prefix_count}",
        f"/{M18_MODULES_POWER_QMP_RAMDISK}",
        "module_list=boot_ramdisk_power_qmp",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "observation=prefix-download",
        "no_android_handoff=1",
        "no_configfs=1",
        "no_acm=1",
        "reboot_request=download",
        DOWNLOAD_ARG,
    ]
    if prefix_count == 0:
        required_strings.append("modules_prefix_skipped")
    else:
        required_strings.extend(["phase=module", "phase=modules_prefix_done"])
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M18 {label} /init: {required}")
    for forbidden in (b"ld-linux", b"libc.so", b"/vendor_dlkm", b"ttyGS0", b"ss_acm.0"):
        if forbidden in binary:
            raise SystemExit(f"M18 {label} /init contains forbidden string: {forbidden!r}")

    (build_dir / f"m18_{label}_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / f"m18_{label}_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / f"m18_{label}_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
    }


def build_prefix(
    *,
    root: Path,
    out_dir: Path,
    base_boot: Path,
    source: Path,
    magiskboot: Path,
    odin: Path,
    prefix_count: int,
    module_text: str,
    vendor_summary: dict[str, Any],
    no_odin_parse_gate: bool,
) -> dict[str, Any]:
    label = prefix_label(prefix_count)
    prefix_dir = out_dir / label
    build_dir = prefix_dir / "build"
    work_dir = prefix_dir / "magiskboot-work"
    nochange_dir = prefix_dir / "nochange-probe"
    odin_dir = prefix_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, odin_dir):
        directory.mkdir(parents=True)

    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")
    if not 0 <= prefix_count <= len(EXPECTED_POWER_QMP_SUBSET):
        raise SystemExit(f"prefix count out of range: {prefix_count}")

    subset_file = build_dir / M18_MODULES_POWER_QMP_RAMDISK
    subset_file.write_text(module_text, encoding="ascii")
    expected_prefix = EXPECTED_POWER_QMP_SUBSET[:prefix_count]
    init_out = build_dir / f"s22plus_init_m18_{label.lower()}_prefix_download"
    init_info = compile_init(source, init_out, build_dir, prefix_count)

    nochange_unpack = run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, f"M18 {label} no-change unpack")
    nochange_repack = run_in_dir(
        [magiskboot, "repack", base_boot, prefix_dir / "boot_nochange_repack.img"],
        nochange_dir,
        f"M18 {label} no-change repack",
    )
    nochange_sha = sha256_file(prefix_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M18 {label} no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, f"M18 {label} unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    extract_text = run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, f"M18 {label} extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    ramdisk_before_sha = sha256_file(ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"],
        work_dir,
        f"M18 {label} replace /init",
    )
    patch_subset_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {M18_MODULES_POWER_QMP_RAMDISK} {subset_file}"],
        work_dir,
        f"M18 {label} add module list",
    )
    patch_text = patch_init_text + "\n" + patch_subset_text
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M18 {label} patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, f"M18 {label} extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(init_out):
        raise SystemExit(f"replaced /init does not match compiled M18 {label} init")
    extracted_subset = build_dir / f"{M18_MODULES_POWER_QMP_RAMDISK}.extracted"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {M18_MODULES_POWER_QMP_RAMDISK} {extracted_subset}"],
        work_dir,
        f"M18 {label} extract module list",
    )
    if sha256_file(extracted_subset) != sha256_file(subset_file):
        raise SystemExit(f"replaced M18 {label} module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    ramdisk_after_sha = sha256_file(ramdisk_after)
    boot_img = prefix_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, f"M18 {label} repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M18 {label} patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")

    patched_unpack_dir = prefix_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    patched_unpack = run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, f"M18 {label} unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit(f"M18 {label} patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M18 {label} AP tar member mismatch: {members}")

    parse_gate_text = ""
    if not no_odin_parse_gate and odin.exists():
        invalid_odin_target = str(Path("/dev") / "bus" / "usb" / "999" / "999")
        gate = run([odin, "-a", ap_md5, "-d", invalid_odin_target])
        parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_gate_text, encoding="utf-8")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "vendor_ramdisk": str(vendor_summary["vendor_ramdisk_sha256"]),
        "m18_power_qmp": sha256_file(subset_file),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m18_init": sha256_file(init_out),
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
        "m18_power_qmp": subset_file.stat().st_size,
        "m18_init": init_out.stat().st_size,
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
        "purpose": f"M18 {label} prefix-download discriminator: load first {prefix_count} M17 modules, then reboot-download checkpoint",
        "prefix": {
            "label": label,
            "count": prefix_count,
            "expected_loaded_modules": expected_prefix,
            "expected_loaded_count": len(expected_prefix),
            "full_m17_module_list": EXPECTED_POWER_QMP_SUBSET,
            "full_m17_module_count": len(EXPECTED_POWER_QMP_SUBSET),
            "module_after_prefix": EXPECTED_POWER_QMP_SUBSET[prefix_count] if prefix_count < len(EXPECTED_POWER_QMP_SUBSET) else None,
        },
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one text module list",
            "runtime": "freestanding-raw-syscall",
            "glibc_static_startup": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": True,
            "intended_reboot_syscall": True,
            "reboot_request": "download",
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_list_path": f"/{M18_MODULES_POWER_QMP_RAMDISK}",
            "module_list_source": "M17 power-QMP full list, text only",
            "module_prefix_count": prefix_count,
            "configfs_runtime_gadget": False,
            "usb_role_force": False,
            "acm": False,
            "watchdog": "not-touched-by-init-source; watchdog modules absent from M17 power-QMP list",
            "observation_model": "host-observed self-download means checkpoint reached; no self-download means reset before checkpoint or reboot path invalid",
        },
        "paths": {
            "out_dir": display_path(root, prefix_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m18_init": init_info,
        "vendor_ramdisk": {
            "vendor_ramdisk_sha256": vendor_summary["vendor_ramdisk_sha256"],
            "m17_power_qmp": vendor_summary["m17_power_qmp"],
        },
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": M18_MODULES_POWER_QMP_RAMDISK,
            "added_subset_entry_mode": "640",
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
        "future_live_interpretation": {
            "download_mode_returns": f"M18 {label} reached the checkpoint after first {prefix_count} M17 modules",
            "no_download_and_loop": f"reset occurred before the M18 {label} checkpoint or checkpoint-download path failed",
        },
    }
    (prefix_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (prefix_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())),
        encoding="ascii",
    )
    (prefix_dir / "sizes.txt").write_text(
        "".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())),
        encoding="ascii",
    )
    (prefix_dir / "required_strings.txt").write_text("\n".join(init_info["required_strings"]) + "\n", encoding="ascii")
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--prefix", type=int, action="append", help="prefix count to build; may be repeated")
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    odin = resolve(root, args.odin)
    prefixes = args.prefix if args.prefix is not None else list(DEFAULT_PREFIXES)

    if len(prefixes) != len(set(prefixes)):
        raise SystemExit(f"duplicate prefix counts requested: {prefixes}")
    for count in prefixes:
        if not 0 <= count <= len(EXPECTED_POWER_QMP_SUBSET):
            raise SystemExit(f"prefix count out of range: {count}")

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    common_dir = out_dir / "common"
    common_dir.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)
    vendor_summary = extract_vendor_ramdisk_metadata(vendor_ramdisk, lz4_tool, common_dir)
    m17_subset = common_dir / M17_MODULES_POWER_QMP_RAMDISK
    if not m17_subset.exists():
        raise SystemExit(f"derived M17 module list missing: {m17_subset}")
    module_text = m17_subset.read_text(encoding="ascii")

    manifests = [
        build_prefix(
            root=root,
            out_dir=out_dir,
            base_boot=base_boot,
            source=source,
            magiskboot=magiskboot,
            odin=odin,
            prefix_count=count,
            module_text=module_text,
            vendor_summary=vendor_summary,
            no_odin_parse_gate=args.no_odin_parse_gate,
        )
        for count in prefixes
    ]

    top_manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M18 prefix-download discriminator matrix",
        "safety": {
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_fresh_sha_pinned_agents_exception_before_any_live_flash": True,
            "device_action": False,
        },
        "prefixes": [
            {
                "label": manifest["prefix"]["label"],
                "count": manifest["prefix"]["count"],
                "ap_tar_md5_sha256": manifest["hashes"]["ap_tar_md5"],
                "boot_img_sha256": manifest["hashes"]["boot_img"],
                "init_sha256": manifest["hashes"]["m18_init"],
                "expected_loaded_modules": manifest["prefix"]["expected_loaded_modules"],
            }
            for manifest in manifests
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(top_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(top_manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
