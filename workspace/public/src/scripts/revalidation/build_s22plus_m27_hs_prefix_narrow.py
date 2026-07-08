#!/usr/bin/env python3
"""Build S22+ M27 HS-only prefix-narrow discriminator artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M27 narrows the M26-proven boundary: P00 reached reboot(download), while P24 did
not.  Each generated candidate loads the first N modules from the M25 HS-only
USB2 list, then requests download mode if it reaches the checkpoint.
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
from build_s22plus_m25_hs_only_usb2_acm import (
    DEFAULT_OUT as DEFAULT_M25_OUT,
    EXPECTED_M25_HS_ONLY_SUBSET,
    MODULES_RAMDISK as M25_MODULES_RAMDISK,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m27_hs_prefix_narrow_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m27_hs_prefix_download.c")
DEFAULT_M25_MANIFEST = DEFAULT_M25_OUT / "manifest.json"
M27_MODULES_RAMDISK = "s22plus_m27_hs_only_usb2.modules"
MARKER = "S22_NATIVE_INIT_M27_HS_PREFIX_DOWNLOAD"
DOWNLOAD_ARG = "download"
EXPECTED_HS_ONLY_COUNT = 40
DEFAULT_PREFIXES = (8, 12, 16, 20, 22, 23, 24)


def prefix_label(prefix_count: int) -> str:
    return f"P{prefix_count:02d}"


def load_m25_hs_context(root: Path, m25_manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(m25_manifest_path.read_text(encoding="utf-8"))
    if manifest.get("target") != "SM-S906N/g0q/S906NKSS7FYG8":
        raise SystemExit(f"unexpected M25 target: {manifest.get('target')!r}")
    safety = manifest.get("safety", {})
    if safety.get("live_flash_authorized") is not False or safety.get("host_only_build") is not True:
        raise SystemExit("M25 manifest safety flags are not host-only/live_flash_authorized=false")

    hs = manifest.get("dts_hs_only", {}).get("dts_hs_only", {})
    modules = hs.get("subset", [])
    if modules != EXPECTED_M25_HS_ONLY_SUBSET:
        raise SystemExit("M25 HS-only subset differs from builder constant")
    if int(hs.get("subset_count", -1)) != EXPECTED_HS_ONLY_COUNT:
        raise SystemExit(f"M25 HS-only subset_count mismatch: {hs.get('subset_count')}")
    module_text = "".join(f"{module}\n" for module in modules)
    if len(module_text.encode("ascii")) >= 8192:
        raise SystemExit("M27 HS-only module list exceeds runtime parser buffer")

    m25_module_file = m25_manifest_path.parent / "build" / M25_MODULES_RAMDISK
    if not m25_module_file.exists():
        raise SystemExit(f"M25 module list file missing: {m25_module_file}")
    if m25_module_file.read_text(encoding="ascii") != module_text:
        raise SystemExit("M25 module list file does not match manifest subset")
    module_sha = sha256_file(m25_module_file)
    expected_module_sha = manifest.get("hashes", {}).get("m25_hs_only_usb2")
    if module_sha != expected_module_sha:
        raise SystemExit(f"M25 module list SHA mismatch: {module_sha} != {expected_module_sha}")

    dtbo = manifest.get("dtbo", {})
    dtbo_hashes = dtbo.get("hashes", {})
    dtbo_paths = dtbo.get("paths", {})
    candidate_dtbo_ap = resolve(root, Path(dtbo_paths.get("candidate_ap_tar_md5", "")))
    stock_dtbo_rollback_ap = resolve(root, Path(dtbo_paths.get("rollback_ap_tar_md5", "")))
    if sha256_file(candidate_dtbo_ap) != dtbo_hashes.get("candidate_ap_tar_md5"):
        raise SystemExit("M25 DTBO candidate AP hash mismatch")
    if sha256_file(stock_dtbo_rollback_ap) != dtbo_hashes.get("rollback_ap_tar_md5"):
        raise SystemExit("M25 stock-DTBO rollback AP hash mismatch")
    if tar_members(candidate_dtbo_ap) != ["dtbo.img.lz4"]:
        raise SystemExit("M25 DTBO candidate AP is not dtbo-only")
    if tar_members(stock_dtbo_rollback_ap) != ["dtbo.img.lz4"]:
        raise SystemExit("M25 stock-DTBO rollback AP is not dtbo-only")

    return {
        "source_manifest": display_path(root, m25_manifest_path),
        "module_count": len(modules),
        "modules": modules,
        "module_text": module_text,
        "module_sha256": module_sha,
        "blocked_dependency_edges": hs.get("blocked_dependency_edges", []),
        "blocklist": hs.get("blocklist", []),
        "subset_recovery_positions": hs.get("subset_recovery_positions", {}),
        "dtbo": {
            "candidate_ap_tar_md5": display_path(root, candidate_dtbo_ap),
            "candidate_ap_tar_md5_sha256": dtbo_hashes.get("candidate_ap_tar_md5"),
            "patched_dtbo_raw_sha256": dtbo_hashes.get("patched_dtbo_raw"),
            "stock_dtbo_rollback_ap_tar_md5": display_path(root, stock_dtbo_rollback_ap),
            "stock_dtbo_rollback_ap_tar_md5_sha256": dtbo_hashes.get("rollback_ap_tar_md5"),
            "stock_dtbo_raw_sha256": dtbo_hashes.get("stock_dtbo_raw"),
        },
    }


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
            f"-DM27_PREFIX_LIMIT={prefix_count}",
            f'-DM27_PREFIX_LABEL="{label}"',
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, f"compile M27 {label} checkpoint init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, f"strip M27 {label} checkpoint init")

    file_info = run(["file", out_path])
    require_ok(file_info, f"file M27 {label} init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, f"readelf M27 {label} init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, f"objdump M27 {label} init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit(f"M27 {label} init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit(f"M27 {label} init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit(f"M27 {label} init disassembly does not contain svc")
    if not any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M27 {label} init disassembly does not load arm64 __NR_reboot (142)")
    if prefix_count > 0 and not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M27 {label} init disassembly does not load arm64 __NR_finit_module (273)")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"prefix_label={label}",
        f"prefix_limit={prefix_count}",
        f"/{M27_MODULES_RAMDISK}",
        "module_count=40",
        "module_list=boot_ramdisk_hs_only_usb2",
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
            raise SystemExit(f"required marker missing from M27 {label} /init: {required}")
    for forbidden in (b"ld-linux", b"libc.so", b"/vendor_dlkm", b"ttyGS0", b"ss_acm.0", b"/config"):
        if forbidden in binary:
            raise SystemExit(f"M27 {label} /init contains forbidden string: {forbidden!r}")
    (build_dir / f"m27_{label}_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / f"m27_{label}_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / f"m27_{label}_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
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
    prefix_count: int,
    hs_context: dict[str, Any],
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
    modules = list(hs_context["modules"])
    if not 0 <= prefix_count <= len(modules):
        raise SystemExit(f"prefix count out of range: {prefix_count}")

    module_list = build_dir / M27_MODULES_RAMDISK
    module_list.write_text(str(hs_context["module_text"]), encoding="ascii")
    init_out = build_dir / f"s22plus_init_m27_{label.lower()}_hs_prefix_download"
    init_info = compile_init(source, init_out, build_dir, prefix_count)

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, f"M27 {label} no-change unpack")
    run_in_dir([magiskboot, "repack", base_boot, prefix_dir / "boot_nochange_repack.img"], nochange_dir, f"M27 {label} no-change repack")
    nochange_sha = sha256_file(prefix_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M27 {label} no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, f"M27 {label} unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, f"M27 {label} extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, f"M27 {label} replace /init")
    patch_modules_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {M27_MODULES_RAMDISK} {module_list}"],
        work_dir,
        f"M27 {label} add module list",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M27 {label} patch: {cpio_test_after}")

    extracted_init = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, f"M27 {label} extract replaced init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit(f"replaced /init does not match compiled M27 {label} init")
    extracted_modules = build_dir / f"{M27_MODULES_RAMDISK}.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract {M27_MODULES_RAMDISK} {extracted_modules}"], work_dir, f"M27 {label} extract module list")
    if sha256_file(extracted_modules) != sha256_file(module_list):
        raise SystemExit(f"replaced M27 {label} module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = prefix_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, f"M27 {label} repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M27 {label} patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")
    patched_unpack_dir = prefix_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, f"M27 {label} unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit(f"M27 {label} patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M27 {label} AP tar member mismatch: {members}")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m27_hs_only_modules": sha256_file(module_list),
        "m27_init": sha256_file(init_out),
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
        "m27_hs_only_modules": module_list.stat().st_size,
        "m27_init": init_out.stat().st_size,
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
        "purpose": f"M27 {label} HS-only prefix-narrow: load first {prefix_count} of 40 M25 HS-only modules, then reboot-download",
        "prefix": {
            "label": label,
            "count": prefix_count,
            "expected_loaded_modules": modules[:prefix_count],
            "expected_loaded_count": prefix_count,
            "module_after_prefix": modules[prefix_count] if prefix_count < len(modules) else None,
        },
        "hs_only_modules": {key: value for key, value in hs_context.items() if key not in {"modules", "module_text"}},
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
            "module_list_path": f"/{M27_MODULES_RAMDISK}",
            "module_list_source": "M25 HS-only USB2 closure, text only",
            "module_prefix_count": prefix_count,
            "dtbo_high_speed_cap_required": True,
            "configfs_runtime_gadget": False,
            "usb_role_force": False,
            "acm": False,
            "observation_model": "host-observed self-download means checkpoint reached",
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
        "m27_init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": M27_MODULES_RAMDISK,
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
        "future_live_interpretation": {
            "download_mode_returns": f"M27 {label} reached checkpoint after first {prefix_count} modules",
            "no_download_and_loop": f"reset occurred before M27 {label} checkpoint or checkpoint-download path failed",
        },
    }
    (prefix_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (prefix_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    (prefix_dir / "sizes.txt").write_text("".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())), encoding="ascii")
    (prefix_dir / "required_strings.txt").write_text("\n".join(init_info["required_strings"]) + "\n", encoding="ascii")
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--m25-manifest", type=Path, default=DEFAULT_M25_MANIFEST)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--prefix", type=int, action="append", help="prefix count to build; may be repeated")
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    m25_manifest = resolve(root, args.m25_manifest)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    prefixes = args.prefix if args.prefix is not None else list(DEFAULT_PREFIXES)
    if len(prefixes) != len(set(prefixes)):
        raise SystemExit(f"duplicate prefix counts requested: {prefixes}")
    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)
    hs_context = load_m25_hs_context(root, m25_manifest)
    for count in prefixes:
        if not 0 <= count <= len(hs_context["modules"]):
            raise SystemExit(f"prefix count out of range: {count}")

    (out_dir / M27_MODULES_RAMDISK).write_text(str(hs_context["module_text"]), encoding="ascii")
    manifests = [
        build_prefix(
            root=root,
            out_dir=out_dir,
            base_boot=base_boot,
            source=source,
            magiskboot=magiskboot,
            prefix_count=count,
            hs_context=hs_context,
        )
        for count in prefixes
    ]
    top_manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M27 HS-only prefix-narrow discriminator matrix between P00 hit and P24 no-hit",
        "safety": {
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_fresh_sha_pinned_agents_exception_before_any_live_flash": True,
            "device_action": False,
        },
        "hs_only_modules": {key: value for key, value in hs_context.items() if key not in {"modules", "module_text"}},
        "prefixes": [
            {
                "label": manifest["prefix"]["label"],
                "count": manifest["prefix"]["count"],
                "ap_tar_md5_sha256": manifest["hashes"]["ap_tar_md5"],
                "boot_img_sha256": manifest["hashes"]["boot_img"],
                "init_sha256": manifest["hashes"]["m27_init"],
                "expected_loaded_count": manifest["prefix"]["expected_loaded_count"],
                "module_after_prefix": manifest["prefix"]["module_after_prefix"],
            }
            for manifest in manifests
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(top_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(top_manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
