#!/usr/bin/env python3
"""Build the S22+ M21A raw nanosleep-then-download boot candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M21A follows the M20A manual-download correction. It keeps the runtime below
C/libc/fs/modules/configfs, but inserts a raw nanosleep dwell before the raw
reboot(download) syscall so a future live helper can distinguish automatic
self-download from manual recovery or an early bootloader artifact.
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m21a_raw_nanosleep_download_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_raw_nanosleep_download_m21a.S")
MARKER = "S22_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD"
DOWNLOAD_ARG = "download"
DWELL_SEC = 90
NR_NANOSLEEP = 101
NR_REBOOT = 142


def compile_raw_init(source: Path, out_path: Path, build_dir: Path) -> dict[str, Any]:
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-Wl,--build-id=none",
            "-Wl,-e,_start",
            "-Wl,-z,noexecstack",
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, "compile M21A raw init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M21A raw init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M21A raw init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M21A raw init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M21A raw init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    objdump_lines = objdump_text.splitlines()
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M21A raw init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M21A raw init is not AArch64")
    if not any("mov" in line and "x8" in line and "#0x65" in line for line in objdump_lines):
        raise SystemExit("M21A raw init does not load arm64 __NR_nanosleep (101)")
    if not any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_lines):
        raise SystemExit("M21A raw init does not load arm64 __NR_reboot (142)")
    svc_count = sum(1 for line in objdump_lines if "svc" in line and "#0x0" in line)
    if svc_count != 2:
        raise SystemExit(f"M21A raw init expected exactly 2 svc #0 instructions, got {svc_count}")

    required_strings = [MARKER, f"nanosleep_sec={DWELL_SEC}", DOWNLOAD_ARG]
    forbidden_strings = [
        b"ld-linux",
        b"libc.so",
        b"/dev/kmsg",
        b"/lib/modules",
        b"finit_module",
        b"modules.load",
        b"ttyGS0",
        b"ss_acm.0",
        b"usb_gadget",
        b"/config",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required static string missing from M21A raw init: {required}")
    for forbidden in forbidden_strings:
        if forbidden in binary:
            raise SystemExit(f"M21A raw init contains forbidden string: {forbidden!r}")

    (build_dir / "m21a_raw_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m21a_raw_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "m21a_raw_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
        "forbidden_strings": [item.decode("ascii") for item in forbidden_strings],
        "syscalls": [
            {"name": "nanosleep", "nr": NR_NANOSLEEP, "purpose": "pre-download dwell separator"},
            {"name": "reboot", "nr": NR_REBOOT, "purpose": "request Samsung download mode"},
        ],
        "dwell_sec": DWELL_SEC,
        "svc_count": svc_count,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
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

    raw_init = build_dir / "s22plus_init_raw_nanosleep_download_m21a"
    raw_init_info = compile_raw_init(source, raw_init, build_dir)

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

    patch_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {raw_init}"], work_dir, "replace ramdisk /init")
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after replacing /init: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(raw_init):
        raise SystemExit("replaced ramdisk /init does not match compiled M21A init")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    ramdisk_after_sha = sha256_file(ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "magiskboot repack")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")

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
        "base_boot": sha256_file(base_boot),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "init": sha256_file(raw_init),
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
        "init": raw_init.stat().st_size,
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
        "label": "M21A_RAW_NANOSLEEP_DOWNLOAD",
        "purpose": "timed raw PID1 discriminator after M20A manual-download correction",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace only ramdisk /init",
            "mkbootimg_from_scratch": False,
            "runtime": "raw-assembly",
            "glibc_static_startup": False,
            "no_android_or_magisk_handoff": True,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_insertions": False,
            "module_binary_injection": False,
            "module_list_files_injected_into_boot_ramdisk": 0,
            "configfs_runtime_gadget": False,
            "udc_binding": False,
            "usb_role_force": False,
            "watchdog": "not-touched",
            "kmsg_marker_write": False,
            "pre_reboot_dwell_sec": DWELL_SEC,
            "pre_reboot_syscalls": ["nanosleep"],
            "auto_reboot": "download",
            "on_reboot_syscall_return": "infinite-park",
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
        "init": raw_init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "only_intended_entry_change": "init",
            "module_files_injected_into_boot_ramdisk": 0,
            "module_list_files_injected_into_boot_ramdisk": 0,
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patched_unpack_output": patched_unpack,
            "extract_output": extract_text,
            "patch_output": patch_text,
            "nochange_unpack_output": nochange_unpack,
            "nochange_repack_output": nochange_repack,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "odin_invalid_device_parse_gate": parse_gate_text,
        "future_live_interpretation": {
            "pass": "no early loop; no operator key intervention; Odin appears only after dwell+grace; rollback ok",
            "early_odin_or_loop": "no automatic proof; manual or bootloader artifact, or failure before/inside dwell",
            "no_download_after_dwell": "candidate failed to prove reboot syscall; manual rollback required",
        },
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
        "\n".join(raw_init_info["required_strings"]) + "\n",
        encoding="ascii",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
