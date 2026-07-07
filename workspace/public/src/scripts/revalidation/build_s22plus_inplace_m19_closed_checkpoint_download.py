#!/usr/bin/env python3
"""Build S22+ M19 dependency-closed checkpoint/download artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M19 uses the post-M18 dependency-closed USB-tail module list. Each generated
candidate loads the first N modules from that list, then requests download mode
if it reaches the checkpoint. This provides an external progress signal without
depending on pstore/last_kmsg or ACM.
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
from s22plus_m18_capture_postmortem import (
    RESET_ANOMALY_BLOCKLIST,
    module_basename,
    parse_modules_dep,
    read_module_list,
)


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m19_closed_checkpoint_download_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m19_closed_checkpoint_download.c")
DEFAULT_M18_MANIFEST = Path(
    "workspace/private/outputs/s22plus_native_init/inplace_m18_full_firststage_usb_v0_1/manifest.json"
)
M19_MODULES_RAMDISK = "s22plus_m19_closed_usb.modules"
MARKER = "S22_NATIVE_INIT_M19_CLOSED_CHECKPOINT"
DOWNLOAD_ARG = "download"
EXPECTED_CLOSED_COUNT = 150
DEFAULT_PREFIXES = (0, 129, 135, 137, 140, 144, 145, 147, 150)


def prefix_label(prefix_count: int) -> str:
    return f"C{prefix_count:03d}"


def derive_closed_modules(m18_manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(m18_manifest_path.read_text(encoding="utf-8"))
    vendor = manifest.get("vendor_ramdisk", {}).get("m18_full_firststage_usb", {})
    base = vendor.get("subset", [])
    if not isinstance(base, list) or not base:
        raise SystemExit("M18 manifest missing vendor_ramdisk.m18_full_firststage_usb.subset")
    metadata_dir = m18_manifest_path.parent / "build" / "vendor_ramdisk_metadata" / "lib" / "modules"
    dep_path = metadata_dir / "modules.dep"
    recovery_path = metadata_dir / "modules.load.recovery"
    if not dep_path.exists() or not recovery_path.exists():
        raise SystemExit(f"M18 vendor module metadata missing under {metadata_dir}")

    deps = parse_modules_dep(dep_path)
    recovery = read_module_list(recovery_path)
    recovery_index = {name: index for index, name in enumerate(recovery)}
    base_modules = [module_basename(str(item)) for item in base]
    seen: list[str] = []
    seen_set: set[str] = set()

    def add_module(module: str) -> None:
        if module in seen_set or module in RESET_ANOMALY_BLOCKLIST:
            return
        for dep in deps.get(module, []):
            if dep not in RESET_ANOMALY_BLOCKLIST:
                add_module(dep)
        if module not in seen_set:
            seen.append(module)
            seen_set.add(module)

    for module in base_modules:
        add_module(module)

    added = [module for module in seen if module not in set(base_modules)]
    unresolved_nonblocked = {
        module: [dep for dep in deps.get(module, []) if dep not in seen_set and dep not in RESET_ANOMALY_BLOCKLIST]
        for module in seen
    }
    unresolved_nonblocked = {module: missing for module, missing in unresolved_nonblocked.items() if missing}
    blocked_edges = {
        module: [dep for dep in deps.get(module, []) if dep in RESET_ANOMALY_BLOCKLIST]
        for module in seen
    }
    blocked_edges = {module: missing for module, missing in blocked_edges.items() if missing}
    if len(seen) != EXPECTED_CLOSED_COUNT:
        raise SystemExit(f"M19 closed module count changed: {len(seen)} != {EXPECTED_CLOSED_COUNT}")
    if unresolved_nonblocked:
        raise SystemExit(f"M19 closed module list still has non-reset unresolved deps: {unresolved_nonblocked}")
    module_text = "".join(f"{module}\n" for module in seen)
    if len(module_text.encode("ascii")) >= 8192:
        raise SystemExit("M19 closed module list exceeds runtime parser buffer")
    return {
        "base_count": len(base_modules),
        "closed_count": len(seen),
        "added_count": len(added),
        "added_modules": added,
        "added_recovery_positions": {
            module: recovery_index[module] + 1 for module in added if module in recovery_index
        },
        "blocked_dependency_module_count": len(blocked_edges),
        "blocked_dependency_edge_count": sum(len(value) for value in blocked_edges.values()),
        "unresolved_nonblocked": unresolved_nonblocked,
        "modules": seen,
        "module_text": module_text,
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
            f"-DM19_PREFIX_LIMIT={prefix_count}",
            f'-DM19_PREFIX_LABEL="{label}"',
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, f"compile M19 {label} checkpoint init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, f"strip M19 {label} checkpoint init")

    file_info = run(["file", out_path])
    require_ok(file_info, f"file M19 {label} init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, f"readelf M19 {label} init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, f"objdump M19 {label} init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit(f"M19 {label} init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit(f"M19 {label} init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit(f"M19 {label} init disassembly does not contain svc")
    if not any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M19 {label} init disassembly does not load arm64 __NR_reboot (142)")
    if prefix_count > 0 and not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M19 {label} init disassembly does not load arm64 __NR_finit_module (273)")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"prefix_label={label}",
        f"prefix_limit={prefix_count}",
        f"/{M19_MODULES_RAMDISK}",
        "module_count=150",
        "module_list=boot_ramdisk_closed_usb",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "observation=checkpoint-download",
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
            raise SystemExit(f"required marker missing from M19 {label} /init: {required}")
    for forbidden in (b"ld-linux", b"libc.so", b"/vendor_dlkm", b"ttyGS0", b"ss_acm.0", b"/config"):
        if forbidden in binary:
            raise SystemExit(f"M19 {label} /init contains forbidden string: {forbidden!r}")
    (build_dir / f"m19_{label}_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / f"m19_{label}_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / f"m19_{label}_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
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
    closed: dict[str, Any],
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
    modules = list(closed["modules"])
    if not 0 <= prefix_count <= len(modules):
        raise SystemExit(f"prefix count out of range: {prefix_count}")

    module_list = build_dir / M19_MODULES_RAMDISK
    module_list.write_text(str(closed["module_text"]), encoding="ascii")
    init_out = build_dir / f"s22plus_init_m19_{label.lower()}_closed_checkpoint"
    init_info = compile_init(source, init_out, build_dir, prefix_count)

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, f"M19 {label} no-change unpack")
    run_in_dir([magiskboot, "repack", base_boot, prefix_dir / "boot_nochange_repack.img"], nochange_dir, f"M19 {label} no-change repack")
    nochange_sha = sha256_file(prefix_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M19 {label} no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, f"M19 {label} unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, f"M19 {label} extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, f"M19 {label} replace /init")
    patch_modules_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {M19_MODULES_RAMDISK} {module_list}"],
        work_dir,
        f"M19 {label} add module list",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M19 {label} patch: {cpio_test_after}")

    extracted_init = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, f"M19 {label} extract replaced init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit(f"replaced /init does not match compiled M19 {label} init")
    extracted_modules = build_dir / f"{M19_MODULES_RAMDISK}.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract {M19_MODULES_RAMDISK} {extracted_modules}"], work_dir, f"M19 {label} extract module list")
    if sha256_file(extracted_modules) != sha256_file(module_list):
        raise SystemExit(f"replaced M19 {label} module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = prefix_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, f"M19 {label} repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M19 {label} patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")
    patched_unpack_dir = prefix_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, f"M19 {label} unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit(f"M19 {label} patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M19 {label} AP tar member mismatch: {members}")

    hashes = {
        "source": sha256_file(source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m19_closed_modules": sha256_file(module_list),
        "m19_init": sha256_file(init_out),
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
        "m19_closed_modules": module_list.stat().st_size,
        "m19_init": init_out.stat().st_size,
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
        "purpose": f"M19 {label} dependency-closed checkpoint/download: load first {prefix_count} of 150 modules, then reboot-download",
        "prefix": {
            "label": label,
            "count": prefix_count,
            "expected_loaded_modules": modules[:prefix_count],
            "expected_loaded_count": prefix_count,
            "module_after_prefix": modules[prefix_count] if prefix_count < len(modules) else None,
        },
        "closed_modules": {key: value for key, value in closed.items() if key not in {"modules", "module_text"}},
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
            "module_list_path": f"/{M19_MODULES_RAMDISK}",
            "module_prefix_count": prefix_count,
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
        "m19_init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": M19_MODULES_RAMDISK,
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
            "download_mode_returns": f"M19 {label} reached checkpoint after first {prefix_count} modules",
            "no_download_and_loop": f"reset occurred before M19 {label} checkpoint or checkpoint-download path failed",
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
    parser.add_argument("--m18-manifest", type=Path, default=DEFAULT_M18_MANIFEST)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--prefix", type=int, action="append", help="prefix count to build; may be repeated")
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    source = resolve(root, args.source)
    m18_manifest = resolve(root, args.m18_manifest)
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
    closed = derive_closed_modules(m18_manifest)
    for count in prefixes:
        if not 0 <= count <= len(closed["modules"]):
            raise SystemExit(f"prefix count out of range: {count}")

    (out_dir / M19_MODULES_RAMDISK).write_text(str(closed["module_text"]), encoding="ascii")
    manifests = [
        build_prefix(
            root=root,
            out_dir=out_dir,
            base_boot=base_boot,
            source=source,
            magiskboot=magiskboot,
            prefix_count=count,
            closed=closed,
        )
        for count in prefixes
    ]
    top_manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M19 dependency-closed checkpoint/download matrix",
        "safety": {
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_fresh_sha_pinned_agents_exception_before_any_live_flash": True,
            "device_action": False,
        },
        "closed_modules": {key: value for key, value in closed.items() if key not in {"modules", "module_text"}},
        "prefixes": [
            {
                "label": manifest["prefix"]["label"],
                "count": manifest["prefix"]["count"],
                "ap_tar_md5_sha256": manifest["hashes"]["ap_tar_md5"],
                "boot_img_sha256": manifest["hashes"]["boot_img"],
                "init_sha256": manifest["hashes"]["m19_init"],
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
