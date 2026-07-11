#!/usr/bin/env python3
"""Build the host-only S22+ V3441 debug-level MID rescue boot AP.

The candidate starts from the known-booting FYG8 Magisk boot image and replaces
only ramdisk /init.  The raw AArch64 init makes one first-action reboot(2)
request with argument ``debug0x494d`` and parks if the syscall returns.
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


DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_native_init/v3441_debug_mid_rescue_v0_1"
)
DEFAULT_SOURCE = Path(
    "workspace/public/src/native-init/s22plus_init_raw_debug_mid_rescue_v3441.S"
)
MARKER = "S22_V3441_RAW_DEBUG_MID_RESCUE"
REBOOT_ARG = "debug0x494d"
EXPECTED_KERNEL_SHA256 = (
    "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
)


def compile_raw_init(source: Path, output: Path, build_dir: Path) -> dict[str, str]:
    compile_result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-Wl,--build-id=none",
            "-Wl,-e,_start",
            "-Wl,-z,noexecstack",
            "-o",
            output,
            source,
        ]
    )
    require_ok(compile_result, "compile V3441 raw MID rescue init")
    require_ok(run(["aarch64-linux-gnu-strip", "-s", output]), "strip V3441 init")

    file_result = run(["file", output])
    require_ok(file_result, "file V3441 init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", output])
    require_ok(readelf, "readelf V3441 init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", output])
    require_ok(objdump, "objdump V3441 init")
    symbols = run(["aarch64-linux-gnu-nm", "-n", output])
    require_ok(symbols, "nm V3441 init")

    readelf_text = readelf.stdout.decode(errors="replace")
    objdump_text = objdump.stdout.decode(errors="replace")
    if "INTERP" in readelf_text or "AArch64" not in readelf_text:
        raise SystemExit("V3441 init ELF shape mismatch")
    if objdump_text.count("svc\t#0x0") != 1:
        raise SystemExit("V3441 init must contain exactly one svc #0")
    start_text = objdump_text.split("<_start>:", 1)[-1]
    if "#0x8e" not in start_text or "svc\t#0x0" not in start_text:
        raise SystemExit("V3441 init does not load arm64 __NR_reboot then svc")
    if any(token in start_text.split("svc\t#0x0", 1)[0] for token in ("str\t", "stp\t", "bl\t")):
        raise SystemExit("V3441 first action unexpectedly uses stack, stores, or calls")

    binary = output.read_bytes()
    for required in (MARKER.encode(), REBOOT_ARG.encode()):
        if required not in binary:
            raise SystemExit(f"V3441 required string missing: {required!r}")
    for forbidden in (b"download", b"/dev/", b"/sys/", b"/proc/", b"/data/", b"ld-linux"):
        if forbidden in binary:
            raise SystemExit(f"V3441 forbidden string present: {forbidden!r}")

    (build_dir / "raw_init_file.txt").write_bytes(file_result.stdout + file_result.stderr)
    (build_dir / "raw_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "raw_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_result.stdout + file_result.stderr).decode(errors="replace").strip(),
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
    parser.add_argument("--force", action="store_true")
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
            raise SystemExit(f"output exists; pass --force: {out_dir}")
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
        raise SystemExit("base boot partition size mismatch")

    raw_init = build_dir / "s22plus_v3441_debug_mid_rescue_init"
    raw_info = compile_raw_init(source, raw_init, build_dir)

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "no-change unpack")
    nochange_boot = out_dir / "boot_nochange_repack.img"
    run_in_dir([magiskboot, "repack", base_boot, nochange_boot], nochange_dir, "no-change repack")
    if sha256_file(nochange_boot) != base_sha:
        raise SystemExit("magiskboot no-change repack is not byte-identical")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "unpack base")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "extract init")
    if sha256_file(original_init) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit("original Magisk init SHA mismatch")
    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    before_test = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if before_test != 1:
        raise SystemExit(f"unexpected base ramdisk test rc={before_test}")
    run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {raw_init}"], work_dir, "replace init")
    after_test = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if after_test not in (1, 2):
        raise SystemExit(f"unexpected patched ramdisk test rc={after_test}")
    extracted = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted}"], work_dir, "verify init")
    if sha256_file(extracted) != sha256_file(raw_init):
        raise SystemExit("repacked init mismatch")
    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)

    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "repack rescue boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit("rescue boot partition size mismatch")
    verify_dir = out_dir / "patched-unpack"
    verify_dir.mkdir()
    patched_unpack = run_in_dir([magiskboot, "unpack", "-h", boot_img], verify_dir, "verify rescue boot")
    kernel_sha = sha256_file(verify_dir / "kernel")
    if kernel_sha != EXPECTED_KERNEL_SHA256 or kernel_sha != sha256_file(kernel):
        raise SystemExit("rescue boot changed the pinned Magisk kernel")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"rescue AP member mismatch: {members}")

    parse_text = ""
    if not args.no_odin_parse_gate and odin.is_file():
        parse_result = run([odin, "-a", ap_md5, "-d", "/dev/bus/usb/999/999"])
        parse_text = (parse_result.stdout + parse_result.stderr).decode(errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_text, encoding="utf-8")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "nochange_repack_boot": sha256_file(nochange_boot),
        "original_magisk_init": sha256_file(original_init),
        "raw_mid_rescue_init": sha256_file(raw_init),
        "ramdisk_before": sha256_file(ramdisk_before),
        "ramdisk_after": sha256_file(ramdisk_after),
        "kernel": kernel_sha,
        "header": sha256_file(header),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    manifest = {
        "schema": "s22plus_v3441_debug_mid_rescue_build_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "boot-only emergency MID restoration before a future HIGH experiment",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "construction": "magiskboot unpack/repack; replace only ramdisk /init",
            "mkbootimg_from_scratch": False,
            "first_candidate_action": "raw-reboot-debug0x494d-syscall",
            "reboot_request": REBOOT_ARG,
            "libc": False,
            "intended_syscalls": ["reboot"],
            "intended_syscall_count": 1,
            "marker_write": False,
            "persistent_partition_mount": False,
            "block_write": False,
            "module_insertions": False,
            "configfs_runtime_gadget": False,
            "watchdog": "not-touched",
            "on_reboot_syscall_return": "infinite-park",
            "expected_repeated_boot_behavior": "repeat idempotent MID request until manual Download entry",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "raw_init": raw_info,
        "required_strings": [MARKER, REBOOT_ARG],
        "ramdisk": {
            "cpio_test_before_rc": before_test,
            "cpio_test_after_rc": after_test,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "only_intended_entry_change": "init",
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patched_unpack_output": patched_unpack,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "odin_invalid_device_parse_gate": parse_text,
        "recovery_contract": {
            "primary": "physical Download -> flash rescue AP -> MID reboot loop -> physical Download -> flash Magisk rollback AP",
            "high_to_mid_transition_live_proven": False,
            "rescue_boot_live_proven": False,
        },
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())),
        encoding="ascii",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
