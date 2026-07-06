#!/usr/bin/env python3
"""Build the S22+ M4T1 in-place Magisk-boot instant-download candidate.

Host-only.  This script does not reboot, flash, or touch a connected device.

M4T1 keeps the M4T0 first action (`reboot(..., "download")`) but changes the
construction method: instead of rebuilding boot.img with mkbootimg, it starts
from the known-booting Magisk boot image and uses magiskboot to replace only the
ramdisk `/init` entry before repacking against the original boot image.
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
from build_s22plus_marker_m31_boot import compile_init


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m4t1_magiskboot_v0_1")
DEFAULT_BASE_BOOT = Path("workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img")
DEFAULT_MAGISKBOOT = Path("workspace/private/tools/magisk-v30.7/magiskboot")
DEFAULT_MAGISK_APK = Path("workspace/private/inputs/magisk/v30.7/Magisk-v30.7.apk")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_instant_download_m4t0.c")
EXPECTED_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_ORIGINAL_MAGISK_INIT_SHA256 = "383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468"
MARKER = "S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0"


def ensure_magiskboot(magiskboot: Path, magisk_apk: Path) -> None:
    if magiskboot.exists():
        return
    if not magisk_apk.exists():
        raise SystemExit(f"magiskboot missing and Magisk APK unavailable: {magisk_apk}")
    magiskboot.parent.mkdir(parents=True, exist_ok=True)
    result = run(["unzip", "-p", magisk_apk, "lib/x86_64/libmagiskboot.so"])
    require_ok(result, "extract x86_64 magiskboot from Magisk APK")
    magiskboot.write_bytes(result.stdout)
    magiskboot.chmod(0o755)


def run_in_dir(argv: list[str | Path], cwd: Path, context: str) -> str:
    result = run(argv, cwd=cwd)
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit(f"{context} failed rc={result.returncode}\n{text}")
    return text


def diff_ranges(old: Path, new: Path, *, max_ranges: int = 64) -> dict[str, object]:
    old_bytes = old.read_bytes()
    new_bytes = new.read_bytes()
    if len(old_bytes) != len(new_bytes):
        raise SystemExit(f"diff size mismatch: {old}={len(old_bytes)} {new}={len(new_bytes)}")
    ranges: list[dict[str, int]] = []
    changed = 0
    first: int | None = None
    last: int | None = None
    current_start: int | None = None
    for idx, (a, b) in enumerate(zip(old_bytes, new_bytes, strict=True)):
        if a == b:
            if current_start is not None:
                if len(ranges) < max_ranges:
                    ranges.append(
                        {
                            "start": current_start,
                            "end_exclusive": idx,
                            "length": idx - current_start,
                        }
                    )
                current_start = None
            continue
        changed += 1
        if first is None:
            first = idx
        last = idx
        if current_start is None:
            current_start = idx
    if current_start is not None and len(ranges) < max_ranges:
        ranges.append(
            {
                "start": current_start,
                "end_exclusive": len(old_bytes),
                "length": len(old_bytes) - current_start,
            }
        )

    prefix = first if first is not None else len(old_bytes)
    suffix = 0
    while suffix < len(old_bytes) - prefix and old_bytes[len(old_bytes) - 1 - suffix] == new_bytes[len(new_bytes) - 1 - suffix]:
        suffix += 1
    return {
        "same_size": True,
        "total_size": len(old_bytes),
        "changed_byte_count": changed,
        "first_changed_offset": first,
        "last_changed_offset": last,
        "unchanged_prefix_bytes": prefix,
        "unchanged_suffix_bytes": suffix,
        "range_count_reported": len(ranges),
        "range_count_truncated": changed > 0 and len(ranges) == max_ranges,
        "ranges": ranges,
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

    instant_init = build_dir / "s22plus_init_instant_download_m4t1"
    compile_init(source, instant_init)
    installed_init = instant_init.read_bytes()
    required_strings = (
        MARKER,
        "proof=first-action-download-reboot",
        "no_marker_before_reboot=1",
        "no_usb_modules=1",
        "no_configfs=1",
        "no_android_handoff=1",
    )
    for required in required_strings:
        if required.encode("ascii") not in installed_init:
            raise SystemExit(f"required marker missing from /init candidate: {required}")

    nochange_unpack = run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "magiskboot no-change unpack")
    nochange_repack = run_in_dir([magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"], nochange_dir, "magiskboot no-change repack")
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
    patch_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {instant_init}"], work_dir, "replace ramdisk /init")
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after replacing /init: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(instant_init):
        raise SystemExit("replaced /init does not match compiled instant-download init")

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
        "instant_init": sha256_file(instant_init),
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
        "instant_init": instant_init.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    diff = diff_ranges(base_boot, boot_img)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M4T1 in-place Magisk-boot instant-download acceptance candidate",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace only ramdisk /init",
            "mkbootimg_from_scratch": False,
            "first_candidate_action": "reboot-download",
            "marker_before_reboot": False,
            "persistent_partition_mount": False,
            "module_insertions": False,
            "configfs_runtime_gadget": False,
            "watchdog": "not-touched",
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
        "required_strings": list(required_strings),
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
        "boot_diff_vs_base": diff,
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
    (out_dir / "required_strings.txt").write_text("\n".join(required_strings) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
