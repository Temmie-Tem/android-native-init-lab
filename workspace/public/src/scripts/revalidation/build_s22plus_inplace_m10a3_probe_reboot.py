#!/usr/bin/env python3
"""Build the S22+ M10A3 no-syscall probe then reboot native-init candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M10A3 is the post-M10A2 split. M10A2 bootlooped after one non-VFS getpid()
syscall before reboot. M10A3 keeps the extra pre-reboot helper call and stack
probe shape, but removes the pre-reboot syscall.
"""

from __future__ import annotations

import argparse
import json
import re
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m10a3_probe_reboot_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m10a3_probe_reboot.c")
REQUIRED_STRINGS = ["download"]
FORBIDDEN_STRINGS = [
    b"ld-linux",
    b"libc.so",
    b"S22_NATIVE_INIT",
    b"/dev",
    b"/proc",
    b"/sys",
    b"/run",
    b"/lib/modules",
    b"getpid",
    b"newfstatat",
    b"mkdir",
    b"mknod",
    b"mount",
    b"finit_module",
    b"modules.load",
    b"ttyGS0",
    b"ss_acm.0",
    b"usb_gadget",
    b"/config",
]


def parse_objdump_addr(line: str) -> int | None:
    match = re.match(r"\s*([0-9a-f]+):", line)
    return int(match.group(1), 16) if match else None


def function_start_for_instruction(lines: list[str], instruction_index: int) -> int:
    for index in range(instruction_index - 1, -1, -1):
        if "\tret" in lines[index] or " ret" in lines[index]:
            for next_index in range(index + 1, instruction_index + 1):
                address = parse_objdump_addr(lines[next_index])
                if address is not None:
                    return address
    for line in lines[: instruction_index + 1]:
        address = parse_objdump_addr(line)
        if address is not None:
            return address
    raise SystemExit("could not recover function start from objdump")


def compile_init(source: Path, out_path: Path, build_dir: Path) -> dict[str, str | int | list[str]]:
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
    require_ok(result, "compile M10A3 probe reboot init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M10A3 probe reboot init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M10A3 probe reboot init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", "-S", out_path])
    require_ok(readelf, "readelf M10A3 probe reboot init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M10A3 probe reboot init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M10A3 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M10A3 init is not AArch64")

    objdump_lines = objdump_text.splitlines()
    svc_lines = [line for line in objdump_lines if "\tsvc" in line or " svc" in line]
    svc_count = len(svc_lines)
    if svc_count != 1:
        raise SystemExit(f"M10A3 init expected exactly one svc instruction, saw {svc_count}: {svc_lines}")
    reboot_nr_lines = [index for index, line in enumerate(objdump_lines) if "mov" in line and "x8" in line and "#0x8e" in line]
    getpid_nr_lines = [line for line in objdump_lines if "mov" in line and "x8" in line and "#0xac" in line]
    forbidden_nr_lines = [
        line
        for line in objdump_lines
        if "mov" in line and "x8" in line and ("#0x4f" in line or "#0x22" in line or "#0x28" in line or "#0x21" in line)
    ]
    if not reboot_nr_lines:
        raise SystemExit("M10A3 init does not load arm64 __NR_reboot (142) into x8")
    if getpid_nr_lines:
        raise SystemExit(f"M10A3 init unexpectedly loads arm64 __NR_getpid (172): {getpid_nr_lines}")
    if forbidden_nr_lines:
        raise SystemExit(f"M10A3 init unexpectedly loads a VFS-ish syscall number: {forbidden_nr_lines}")

    reboot_func_start = function_start_for_instruction(objdump_lines, reboot_nr_lines[0])
    branch_targets: list[int] = []
    for line in objdump_lines:
        if "\tbl\t" not in line and " bl " not in line:
            continue
        match = re.search(r"\bbl\s+0x([0-9a-f]+)", line)
        if match:
            branch_targets.append(int(match.group(1), 16))
    try:
        reboot_call_index = branch_targets.index(reboot_func_start)
    except ValueError as exc:
        raise SystemExit(
            "M10A3 _start does not branch to the reboot helper "
            f"(branches={branch_targets!r}, reboot=0x{reboot_func_start:x})"
        ) from exc
    if reboot_call_index == 0:
        raise SystemExit("M10A3 _start calls reboot before the pre-reboot probe helper")
    if any(target == reboot_func_start for target in branch_targets[:reboot_call_index]):
        raise SystemExit(f"M10A3 unexpected earlier reboot branch: {branch_targets!r}")

    binary = out_path.read_bytes()
    for required in REQUIRED_STRINGS:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"M10A3 /init missing required string: {required}")
    for forbidden in FORBIDDEN_STRINGS:
        if forbidden in binary:
            raise SystemExit(f"M10A3 /init contains forbidden string: {forbidden!r}")

    (build_dir / "m10a3_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m10a3_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "m10a3_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "svc_count": svc_count,
        "reboot_func_start": f"0x{reboot_func_start:x}",
        "pre_reboot_branch_target": f"0x{branch_targets[0]:x}",
        "branch_targets": [f"0x{target:x}" for target in branch_targets],
        "required_strings": REQUIRED_STRINGS,
        "forbidden_strings": [item.decode("ascii") for item in FORBIDDEN_STRINGS],
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
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, odin_dir):
        directory.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)

    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")

    m10a3_init = build_dir / "s22plus_init_m10a3_probe_reboot"
    m10a3_init_info = compile_init(source, m10a3_init, build_dir)

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

    patch_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {m10a3_init}"], work_dir, "replace /init with M10A3 init")
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M10A3 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(m10a3_init):
        raise SystemExit("replaced /init does not match compiled M10A3 init")

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
        invalid_odin_target = str(Path("/dev") / "bus" / "usb" / "999" / "999")
        gate = run([odin, "-a", ap_md5, "-d", invalid_odin_target])
        parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_gate_text, encoding="utf-8")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m10a3_init": sha256_file(m10a3_init),
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
        "m10a3_init": m10a3_init.stat().st_size,
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
        "purpose": "M10A3 in-place freestanding C no-syscall probe then reboot discriminator",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace only ramdisk /init",
            "runtime": "freestanding-c-raw-syscall",
            "glibc_static_startup": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "pre_reboot_helper": "stack-probe-no-syscall",
            "first_runtime_side_effect": "none-before-reboot",
            "first_externally_observable_action": "probe-helper-then-reboot-download",
            "intended_syscalls": ["reboot"],
            "intended_syscall_count": 1,
            "auto_reboot": "download-after-stack-probe-helper",
            "marker_write": False,
            "kmsg_write": False,
            "vfs_setup": "none",
            "vfs_mutation": False,
            "pathname_access": False,
            "getpid": False,
            "mkdirat": False,
            "mknodat": False,
            "mounts": False,
            "sleep_before_reboot": False,
            "host_commanded_reboot_download": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_insertions": False,
            "module_binary_injection": False,
            "module_list_files_injected_into_boot_ramdisk": 0,
            "configfs_runtime_gadget": False,
            "udc_binding": False,
            "usb_role_force": False,
            "watchdog": "not-touched",
            "on_reboot_syscall_return": "infinite-park",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "magiskboot": display_path(root, magiskboot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m10a3_init": m10a3_init_info,
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
            "nochange_unpack_output": nochange_unpack,
            "nochange_repack_output": nochange_repack,
            "extract_output": extract_text,
            "patch_output": patch_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "odin_invalid_device_parse_gate": parse_gate_text,
        "future_live_interpretation": {
            "download_mode_returns_without_manual_entry": "the extra helper/stack shape is survivable; M10A2 points at the prior getpid syscall",
            "no_download_mode": "the extra helper/timing/stack shape is enough to lose self-download; compare against M9A instruction shape",
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
    (out_dir / "required_strings.txt").write_text("\n".join(REQUIRED_STRINGS) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
