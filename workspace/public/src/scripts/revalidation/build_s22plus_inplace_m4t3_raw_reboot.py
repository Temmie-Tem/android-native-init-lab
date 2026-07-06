#!/usr/bin/env python3
"""Build the S22+ M4T3 in-place raw reboot-download PID1 boot candidate.

Host-only.  This script does not reboot, flash, or touch a connected device.

M4T3 builds upward from the M4T2 raw park proof.  It starts from the same
known-booting Magisk boot image, replaces only ramdisk `/init`, and the
replacement is raw AArch64 assembly with no libc and exactly one intended first
primitive: a direct reboot(2) syscall requesting "download", then an infinite
park if the syscall returns.
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m4t3_raw_reboot_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_raw_reboot_m4t3.S")
MARKER = "S22_NATIVE_INIT_RAW_REBOOT_M4T3"
DOWNLOAD_ARG = "download"


def compile_raw_init(source: Path, out_path: Path, build_dir: Path) -> dict[str, str]:
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
    require_ok(result, "compile raw reboot init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip raw reboot init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file raw reboot init")
    readelf_headers = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf_headers, "readelf raw reboot init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump raw reboot init")

    readelf_text = readelf_headers.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text:
        raise SystemExit("raw reboot init unexpectedly has a PT_INTERP segment")
    if "AArch64" not in readelf_text:
        raise SystemExit("raw reboot init is not AArch64")
    objdump_lines = objdump_text.splitlines()
    if not any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_lines):
        raise SystemExit("raw reboot init disassembly does not load arm64 __NR_reboot (142) into x8")
    if not any("svc" in line and "#0x0" in line for line in objdump_lines):
        raise SystemExit("raw reboot init disassembly does not contain the expected svc #0")

    binary = out_path.read_bytes()
    for required in (MARKER, DOWNLOAD_ARG):
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required static string missing from raw init: {required}")
    if b"/lib" in binary or b"ld-linux" in binary:
        raise SystemExit("raw reboot init unexpectedly contains dynamic loader strings")

    (build_dir / "raw_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "raw_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "raw_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
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

    raw_init = build_dir / "s22plus_init_raw_reboot_m4t3"
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
        raise SystemExit("replaced /init does not match compiled raw reboot init")

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
        "raw_reboot_init": sha256_file(raw_init),
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
        "raw_reboot_init": raw_init.stat().st_size,
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
        "purpose": "M4T3 in-place raw PID1 reboot-download syscall discriminator",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace only ramdisk /init",
            "mkbootimg_from_scratch": False,
            "first_candidate_action": "raw-reboot-download-syscall",
            "libc": False,
            "intended_syscalls": ["reboot"],
            "intended_syscall_count": 1,
            "reboot_request": "download",
            "marker_write": False,
            "persistent_partition_mount": False,
            "module_insertions": False,
            "configfs_runtime_gadget": False,
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
        "raw_init": raw_init_info,
        "required_strings": [MARKER, DOWNLOAD_ARG],
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_before_meaning": "Magisk ramdisk",
            "cpio_test_after_rc": cpio_test_after,
            "cpio_test_after_meaning": "Magisk structure may remain because .backup/overlay.d are preserved; /init hash is the replacement gate",
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "only_intended_entry_change": "init",
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
            "download_mode_returns": "raw reboot syscall path works from custom PID1",
            "no_transport_and_stable_park": "custom PID1 survived but reboot syscall returned or was rejected",
            "fast_bootloop": "raw reboot syscall path or immediate PID1 action is unstable",
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
    (out_dir / "required_strings.txt").write_text("\n".join([MARKER, DOWNLOAD_ARG]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
