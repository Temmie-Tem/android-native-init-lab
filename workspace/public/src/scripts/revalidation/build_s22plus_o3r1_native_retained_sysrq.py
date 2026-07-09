#!/usr/bin/env python3
"""Build the host-only S22+ O3R1 native-PID1 retained SysRq control."""

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
    ensure_magiskboot,
    run_in_dir,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/o3r1_native_retained_sysrq_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_o3r1_native_retained_sysrq.c")
MARKER = "S22_NATIVE_INIT_O3R1_RETAINED_SYSRQ"

EXPECTED_SYSCALLS = {
    "mknodat": 33,
    "mkdirat": 34,
    "mount": 40,
    "openat": 56,
    "close": 57,
    "write": 64,
    "exit_group": 94,
}


def verify_source_contract(source: Path) -> dict[str, Any]:
    text = source.read_text(encoding="ascii")
    required = [
        MARKER,
        "entry-pre-proc",
        "proc-mount",
        "sysrq-open",
        "before-sysrq-c",
        "sysrq-returned",
        "pid1-exit-group-panic",
        'o3r1_open("/proc/sysrq-trigger"',
        "o3r1_exit_group(exit_code)",
    ]
    forbidden = [
        "/dev/pmsg0",
        "/proc/sys/kernel/sysrq",
        "/sys/",
        "/config/",
        "/lib/modules",
        "finit_module",
        "usb_gadget",
        "a600000",
        "download",
        "NR_REBOOT",
        "NR_CLONE",
    ]
    missing = [token for token in required if token not in text]
    present = [token for token in forbidden if token.lower() in text.lower()]
    if missing or present:
        raise SystemExit(f"O3R1 source contract failed missing={missing} forbidden={present}")
    order = [text.index(token) for token in ["entry-pre-proc", "proc-mount", "sysrq-open", "before-sysrq-c", "sysrq-returned"]]
    if order != sorted(order) or len(set(order)) != len(order):
        raise SystemExit("O3R1 phase markers are not ordered")
    return {"required": required, "forbidden_absent": forbidden, "phase_order": order}


def compile_init(source: Path, output: Path, build_dir: Path) -> dict[str, Any]:
    command = [
        "aarch64-linux-gnu-gcc",
        "-std=gnu11",
        "-nostdlib",
        "-static",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-tree-loop-distribute-patterns",
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
        str(source),
        "-o",
        str(output),
    ]
    require_ok(run(command), "compile O3R1 init")
    require_ok(run(["aarch64-linux-gnu-strip", "-s", output]), "strip O3R1 init")
    file_result = run(["file", output])
    readelf_result = run(["aarch64-linux-gnu-readelf", "-h", "-l", output])
    objdump_result = run(["aarch64-linux-gnu-objdump", "-d", output])
    undefined_result = run(["aarch64-linux-gnu-nm", "-u", output])
    require_ok(file_result, "file O3R1 init")
    require_ok(readelf_result, "readelf O3R1 init")
    require_ok(objdump_result, "objdump O3R1 init")
    require_ok(undefined_result, "undefined O3R1 init")
    file_text = (file_result.stdout + file_result.stderr).decode("utf-8", errors="replace")
    readelf_text = readelf_result.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump_result.stdout.decode("utf-8", errors="replace")
    undefined_text = undefined_result.stdout.decode("utf-8", errors="replace").strip()
    if "ARM aarch64" not in file_text or "statically linked" not in file_text:
        raise SystemExit(f"O3R1 init is not static AArch64: {file_text.strip()}")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("O3R1 init unexpectedly has PT_INTERP")
    if undefined_text:
        raise SystemExit(f"O3R1 init has undefined symbols: {undefined_text}")
    if output.stat().st_size >= 65536:
        raise SystemExit(f"O3R1 init unexpectedly large: {output.stat().st_size}")
    for name, number in EXPECTED_SYSCALLS.items():
        needle = f"#0x{number:x}"
        if not any("mov" in line and "x8" in line and needle in line for line in objdump_text.splitlines()):
            raise SystemExit(f"O3R1 init does not load arm64 __NR_{name} ({number})")
    for forbidden_number, label in [(142, "reboot"), (273, "finit_module"), (220, "clone")]:
        needle = f"#0x{forbidden_number:x}"
        if any("mov" in line and "x8" in line and needle in line for line in objdump_text.splitlines()):
            raise SystemExit(f"O3R1 init unexpectedly loads __NR_{label} ({forbidden_number})")
    binary = output.read_bytes()
    for token in [MARKER, "/dev/kmsg", "/proc/sysrq-trigger", "intentional-kernel-panic", "pid1-exit-group-panic"]:
        if token.encode("ascii") not in binary:
            raise SystemExit(f"O3R1 init required string missing: {token}")
    for token in [b"pmsg0", b"/proc/sys/kernel/sysrq", b"download", b"usb_gadget", b"a600000"]:
        if token in binary:
            raise SystemExit(f"O3R1 init forbidden string present: {token!r}")
    (build_dir / "o3r1_init.file.txt").write_text(file_text, encoding="utf-8")
    (build_dir / "o3r1_init.readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "o3r1_init.objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "command": command,
        "file": file_text.strip(),
        "sha256": sha256_file(output),
        "size": output.stat().st_size,
        "no_interp": True,
        "undefined_symbols": [],
        "syscalls": EXPECTED_SYSCALLS,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    patched_unpack_dir = out_dir / "patched-unpack"
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, patched_unpack_dir, odin_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_contract = verify_source_contract(source)
    ensure_magiskboot(magiskboot, magisk_apk)
    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size}")

    init_out = build_dir / "init"
    init_info = compile_init(source, init_out, build_dir)

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "O3R1 no-change unpack")
    nochange_boot = out_dir / "boot_nochange_repack.img"
    run_in_dir([magiskboot, "repack", base_boot, nochange_boot], nochange_dir, "O3R1 no-change repack")
    nochange_sha = sha256_file(nochange_boot)
    if nochange_sha != base_sha:
        raise SystemExit(f"O3R1 no-change repack differs: {nochange_sha}")

    run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "O3R1 unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "O3R1 extract init")
    if sha256_file(original_init) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit("O3R1 original Magisk init mismatch")
    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_before != 1:
        raise SystemExit(f"O3R1 base ramdisk test rc mismatch: {cpio_before}")
    run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, "O3R1 replace init")
    cpio_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_after not in (1, 2):
        raise SystemExit(f"O3R1 patched ramdisk test rc mismatch: {cpio_after}")
    extracted_init = build_dir / "init.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, "O3R1 verify init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit("O3R1 ramdisk init mismatch")
    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)

    boot_img = out_dir / "boot.img"
    run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "O3R1 repack")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"O3R1 boot size mismatch: {boot_img.stat().st_size}")
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "O3R1 unpack patched")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("O3R1 patched boot kernel changed")
    patched_init = build_dir / "init.patched-boot"
    run_in_dir(
        [magiskboot, "cpio", patched_unpack_dir / "ramdisk.cpio", f"extract init {patched_init}"],
        patched_unpack_dir,
        "O3R1 extract patched init",
    )
    if sha256_file(patched_init) != sha256_file(init_out):
        raise SystemExit("O3R1 patched boot init mismatch")

    boot_lz4 = odin_dir / "boot.img.lz4"
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_boot_lz4(boot_img, boot_lz4)
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"O3R1 AP member mismatch: {members}")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": sha256_file(original_init),
        "init": sha256_file(init_out),
        "ramdisk_before": sha256_file(ramdisk_before),
        "ramdisk_after": sha256_file(ramdisk_after),
        "kernel": sha256_file(kernel),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    manifest = {
        "schema": "s22plus_o3r1_native_retained_sysrq_build_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "native-PID1 kmsg plus SysRq retained-console positive control",
        "paths": {
            "out_dir": display_path(root, out_dir),
            "base_boot": display_path(root, base_boot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": {
            "init": init_out.stat().st_size,
            "boot_img": boot_img.stat().st_size,
            "boot_img_lz4": boot_lz4.stat().st_size,
            "ap_tar_md5": ap_md5.stat().st_size,
        },
        "source_contract": source_contract,
        "init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_before,
            "cpio_test_after_rc": cpio_after,
            "replaced_entry": "init",
            "added_entries": [],
            "replaced_entry_mode": "750",
        },
        "tar_members": members,
        "safety": {
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "boot_only": True,
            "kernel_changed": False,
            "construction": "magiskboot in-place repack; replace ramdisk /init only",
            "runtime": "freestanding-raw-syscall",
            "intentional_kernel_crash": "sysrq-trigger-c",
            "failure_fallback": "global PID1 exit_group panic",
            "procfs_mount": True,
            "procfs_write_allowlist": ["/proc/sysrq-trigger=c"],
            "kernel_sysrq_sysctl_write": False,
            "pmsg_write": False,
            "module_insertion": False,
            "sysfs_write": False,
            "configfs_write": False,
            "usb_setup": False,
            "reboot_syscall": False,
            "block_device_write": False,
            "persistent_partition_mount": False,
            "no_android_or_magisk_handoff": True,
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
