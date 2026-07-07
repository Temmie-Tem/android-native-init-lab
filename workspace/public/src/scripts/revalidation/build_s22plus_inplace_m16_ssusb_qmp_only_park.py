#!/usr/bin/env python3
"""Build the S22+ M16 SSUSB-QMP-only add-back native-init candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M16 starts from the stable M13 no-module floor and reintroduces only
phy-msm-ssusb-qmp.ko from the failed M15 PHY-side pair. This separates the
first PHY module from the complementary phy-msm-snps-eusb2.ko candidate and
from the loader/open-only control. The boot ramdisk gets only a small text
list; module binaries remain in stock vendor_boot /lib/modules.
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m16_ssusb_qmp_only_v0_1")
DEFAULT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m16_ssusb_qmp_only_park.c")
DEFAULT_VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/"
    "unpack-vendor-boot/vendor_ramdisk00"
)
DEFAULT_LZ4 = Path("workspace/private/tools/lz4-local/root/usr/bin/lz4")
MARKER = "S22_NATIVE_INIT_USB_ACM_M16"
EXPECTED_KO_COUNT = 441
EXPECTED_MODULES_LOAD_COUNT = 140
EXPECTED_MODULES_LOAD_RECOVERY_COUNT = 446
EXPECTED_MODULES_DEP_COUNT = 441
RUNTIME_MODULES_SSUSB_QMP_ONLY_BUF = 8192
RUNTIME_MODULE_NAME_BUF = 128
MODULES_SSUSB_QMP_ONLY_RAMDISK = "s22plus_m16_ssusb_qmp_only.modules"
MODULES_LOAD_RECOVERY = "lib/modules/modules.load.recovery"
MODULES_LOAD = "lib/modules/modules.load"
MODULES_SOFTDEP = "lib/modules/modules.softdep"
MODULES_DEP = "lib/modules/modules.dep"

SSUSB_QMP_ONLY_MODULES = [
    "phy-msm-ssusb-qmp.ko",
]

M15_WITHHELD_AFTER_M16 = [
    "phy-msm-snps-eusb2.ko",
]

M14_WITHHELD_AFTER_M16 = [
    "dwc3-msm.ko",
    "usb_f_ss_acm.ko",
]

M12_WITHHELD_AFTER_M16 = [
    "usb_f_diag.ko",
    "usb_f_qdss.ko",
    "usb_f_gsi.ko",
    "usb_f_conn_gadget.ko",
    "usb_f_ss_mon_gadget.ko",
    "repeater.ko",
    "redriver.ko",
    "usb_notify_layer.ko",
    "ipa_fmwk.ko",
    "usb_bam.ko",
    "sps_drv.ko",
    "switch_class.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "usb_typec_manager.ko",
    "if_cb_manager.ko",
    "pdic_notifier_module.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
    "spu_verify.ko",
]

EXPLICIT_M16_BLOCKLIST = {
    "abc.ko",
    "icc-debug.ko",
    "minidump.ko",
    "sec_debug.ko",
    "pmic_glink.ko",
    "altmode-glink.ko",
    "ucsi_glink.ko",
    "qcom_glink.ko",
    "qcom_glink_smem.ko",
    "qcom_smd.ko",
    "pdr_interface.ko",
    "qmi_helpers.ko",
    "rproc_qcom_common.ko",
    "eud.ko",
    "qc_usb_audio.ko",
    "gh_virt_wdt.ko",
    "qcom_wdt_core.ko",
    "qcom_soc_wdt.ko",
    "sec_qc_qcom_wdt_core.ko",
}

NON_USB_BLOCKLIST_SUBSTRINGS = (
    "dispcc",
    "msm_drm",
    "panel",
    "cfg80211",
    "wlan",
    "thermal",
    "sensor",
    "kgsl",
    "gpu",
    "camera",
    "cam_",
    "snd",
    "audio",
)


def nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("#")]


def module_basename(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def is_blocked_module(name: str) -> bool:
    if name in EXPLICIT_M16_BLOCKLIST:
        return True
    lower = name.lower()
    return any(token in lower for token in NON_USB_BLOCKLIST_SUBSTRINGS)


def parse_modules_dep(lines: list[str]) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for line in lines:
        lhs, sep, rhs = line.partition(":")
        if sep != ":":
            raise SystemExit(f"malformed modules.dep line without colon: {line!r}")
        name = module_basename(lhs.strip())
        dep_names = [module_basename(item) for item in rhs.split()]
        if name in deps:
            raise SystemExit(f"duplicate modules.dep lhs: {name}")
        deps[name] = dep_names
    return deps


def derive_ssusb_qmp_only(recovery_lines: list[str], modules_dep_lines: list[str]) -> dict[str, object]:
    recovery_set = set(recovery_lines)
    dep_map = parse_modules_dep(modules_dep_lines)

    missing_recovery = sorted(module for module in SSUSB_QMP_ONLY_MODULES if module not in recovery_set)
    missing_dep = sorted(module for module in SSUSB_QMP_ONLY_MODULES if module not in dep_map)
    if missing_recovery:
        raise SystemExit(f"SSUSB-QMP-only module missing from modules.load.recovery: {missing_recovery}")
    if missing_dep:
        raise SystemExit(f"SSUSB-QMP-only module missing from modules.dep: {missing_dep}")

    ordered = list(SSUSB_QMP_ONLY_MODULES)
    if len(ordered) != 1:
        raise SystemExit(f"SSUSB-QMP-only module count changed: {len(ordered)} != 1")
    if len(set(ordered)) != len(ordered):
        raise SystemExit("SSUSB-QMP-only common module list contains duplicates")
    if any(is_blocked_module(name) for name in ordered):
        raise SystemExit("SSUSB-QMP-only common module list includes an explicit M16 blocklist item")
    if not ordered:
        raise SystemExit("derived M16 SSUSB QMP only is empty")

    subset_text = "".join(f"{name}\n" for name in ordered)
    if len(subset_text.encode("utf-8")) >= RUNTIME_MODULES_SSUSB_QMP_ONLY_BUF:
        raise SystemExit(
            "M16 SSUSB QMP only does not fit runtime parser buffer: "
            f"{len(subset_text.encode('utf-8'))} >= {RUNTIME_MODULES_SSUSB_QMP_ONLY_BUF}"
        )
    too_long = [name for name in ordered if len(name) >= RUNTIME_MODULE_NAME_BUF]
    if too_long:
        raise SystemExit(f"M16 SSUSB QMP only basename exceeds runtime parser buffer: {too_long[:5]}")

    return {
        "ssusb_qmp_only_modules": SSUSB_QMP_ONLY_MODULES,
        "ssusb_qmp_only_count": len(SSUSB_QMP_ONLY_MODULES),
        "m15_withheld_after_m16": M15_WITHHELD_AFTER_M16,
        "m15_withheld_after_m16_count": len(M15_WITHHELD_AFTER_M16),
        "m14_withheld_after_m16": M14_WITHHELD_AFTER_M16,
        "m14_withheld_after_m16_count": len(M14_WITHHELD_AFTER_M16),
        "m12_withheld_after_m16": M12_WITHHELD_AFTER_M16,
        "m12_withheld_after_m16_count": len(M12_WITHHELD_AFTER_M16),
        "order_source": "M15 PHY-side pair split: SSUSB-QMP only",
        "explicit_m16_blocklist": sorted(EXPLICIT_M16_BLOCKLIST),
        "non_usb_blocklist_substrings": list(NON_USB_BLOCKLIST_SUBSTRINGS),
        "subset_count": len(ordered),
        "subset_bytes": len(subset_text.encode("utf-8")),
        "runtime_modules_ssusb_qmp_only_buffer": RUNTIME_MODULES_SSUSB_QMP_ONLY_BUF,
        "runtime_module_name_buffer": RUNTIME_MODULE_NAME_BUF,
        "subset_max_basename_len": max(len(name) for name in ordered),
        "subset": ordered,
        "subset_positions": {module: recovery_lines.index(module) + 1 for module in ordered},
        "subset_text": subset_text,
    }


def extract_vendor_ramdisk_metadata(vendor_ramdisk: Path, lz4_tool: Path, build_dir: Path) -> dict[str, object]:
    if not vendor_ramdisk.exists():
        raise SystemExit(f"vendor ramdisk missing: {vendor_ramdisk}")
    if not lz4_tool.exists():
        raise SystemExit(f"lz4 tool missing: {lz4_tool}")
    cpio_result = run([lz4_tool, "-dc", vendor_ramdisk])
    require_ok(cpio_result, "decompress vendor_boot vendor_ramdisk00")
    cpio_bytes = cpio_result.stdout

    list_result = run(["cpio", "-it"], input_bytes=cpio_bytes)
    require_ok(list_result, "list vendor_boot vendor ramdisk cpio")
    listing = list_result.stdout.decode("utf-8", errors="replace").splitlines()
    (build_dir / "vendor_ramdisk_listing.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
    verbose_result = run(["cpio", "-tv"], input_bytes=cpio_bytes)
    require_ok(verbose_result, "verbose-list vendor_boot vendor ramdisk cpio")
    verbose_listing = verbose_result.stdout.decode("utf-8", errors="replace").splitlines()
    (build_dir / "vendor_ramdisk_listing_verbose.txt").write_text(
        "\n".join(verbose_listing) + "\n",
        encoding="utf-8",
    )

    metadata_dir = build_dir / "vendor_ramdisk_metadata"
    metadata_dir.mkdir()
    extract_result = run(
        [
            "cpio",
            "-id",
            "--no-absolute-filenames",
            MODULES_LOAD,
            MODULES_LOAD_RECOVERY,
            MODULES_SOFTDEP,
            MODULES_DEP,
        ],
        cwd=metadata_dir,
        input_bytes=cpio_bytes,
    )
    require_ok(extract_result, "extract vendor_boot module metadata")

    metadata: dict[str, str] = {}
    for rel in (MODULES_LOAD, MODULES_LOAD_RECOVERY, MODULES_SOFTDEP, MODULES_DEP):
        path = metadata_dir / rel
        if not path.exists():
            raise SystemExit(f"vendor ramdisk metadata missing after extract: {rel}")
        metadata[rel] = path.read_text(encoding="utf-8", errors="replace")

    ko_paths = sorted(path for path in listing if path.startswith("lib/modules/") and path.endswith(".ko"))
    ko_names = sorted(path.split("/")[-1] for path in ko_paths)
    module_sizes: dict[str, int] = {}
    for line in verbose_listing:
        parts = line.split(maxsplit=8)
        if len(parts) != 9:
            continue
        path = parts[8]
        if not path.startswith("lib/modules/") or not path.endswith(".ko"):
            continue
        module_sizes[path] = int(parts[4])
    if sorted(module_sizes) != ko_paths:
        raise SystemExit("verbose cpio listing did not cover the same vendor .ko set")
    recovery_lines = nonempty_lines(metadata[MODULES_LOAD_RECOVERY])
    recovery_basenames = [line.rsplit("/", 1)[-1] for line in recovery_lines]
    recovery_bytes = len(metadata[MODULES_LOAD_RECOVERY].encode("utf-8"))
    modules_load_lines = nonempty_lines(metadata[MODULES_LOAD])
    modules_dep_lines = nonempty_lines(metadata[MODULES_DEP])
    softdep_text = metadata[MODULES_SOFTDEP]
    recovery_inline_whitespace = [line for line in recovery_lines if line.split() != [line]]
    recovery_non_ko = [line for line, name in zip(recovery_lines, recovery_basenames) if not name.endswith(".ko")]
    recovery_too_long = [name for name in recovery_basenames if len(name) >= RUNTIME_MODULE_NAME_BUF]
    ssusb_qmp_only = derive_ssusb_qmp_only(recovery_lines, modules_dep_lines)

    missing_ko = sorted(module for module in SSUSB_QMP_ONLY_MODULES if module not in ko_names)
    missing_recovery = sorted(module for module in SSUSB_QMP_ONLY_MODULES if module not in recovery_lines)
    if missing_ko:
        raise SystemExit(f"SSUSB-QMP-only vendor .ko missing from vendor ramdisk: {missing_ko}")
    if missing_recovery:
        raise SystemExit(f"SSUSB-QMP-only module missing from modules.load.recovery: {missing_recovery}")
    expected_softdep = "softdep dwc3_msm pre: phy-generic phy-msm-snps-hs phy-msm-snps-eusb2 phy-msm-ssusb-qmp eud post: ucsi_glink"
    if expected_softdep not in softdep_text:
        raise SystemExit("expected dwc3_msm softdep line missing")
    if len(ko_paths) != EXPECTED_KO_COUNT:
        raise SystemExit(f"vendor .ko count mismatch: {len(ko_paths)} != {EXPECTED_KO_COUNT}")
    if len(modules_load_lines) != EXPECTED_MODULES_LOAD_COUNT:
        raise SystemExit(f"modules.load count mismatch: {len(modules_load_lines)} != {EXPECTED_MODULES_LOAD_COUNT}")
    if len(recovery_lines) != EXPECTED_MODULES_LOAD_RECOVERY_COUNT:
        raise SystemExit(
            f"modules.load.recovery count mismatch: {len(recovery_lines)} != {EXPECTED_MODULES_LOAD_RECOVERY_COUNT}"
        )
    if recovery_bytes >= 32768:
        raise SystemExit(
            "modules.load.recovery unexpectedly exceeded the historical M6 parser bound: "
            f"{recovery_bytes} >= 32768"
        )
    if recovery_inline_whitespace:
        raise SystemExit(f"modules.load.recovery has inline whitespace tokens: {recovery_inline_whitespace[:5]}")
    if recovery_non_ko:
        raise SystemExit(f"modules.load.recovery contains non-.ko entries: {recovery_non_ko[:5]}")
    if recovery_too_long:
        raise SystemExit(
            "modules.load.recovery basename exceeds M16 runtime parser buffer: "
            f"{recovery_too_long[:5]}"
        )
    if len(modules_dep_lines) != EXPECTED_MODULES_DEP_COUNT:
        raise SystemExit(f"modules.dep count mismatch: {len(modules_dep_lines)} != {EXPECTED_MODULES_DEP_COUNT}")

    positions = {module: recovery_lines.index(module) + 1 for module in SSUSB_QMP_ONLY_MODULES}
    (build_dir / "modules.load.recovery.head.txt").write_text(
        "\n".join(recovery_lines[:80]) + "\n",
        encoding="utf-8",
    )
    (build_dir / "modules.softdep.dwc3.txt").write_text(expected_softdep + "\n", encoding="utf-8")
    (build_dir / MODULES_SSUSB_QMP_ONLY_RAMDISK).write_text(str(ssusb_qmp_only["subset_text"]), encoding="ascii")
    (build_dir / "m16_ssusb_qmp_only.txt").write_text(str(ssusb_qmp_only["subset_text"]), encoding="ascii")
    return {
        "vendor_ramdisk_sha256": sha256_file(vendor_ramdisk),
        "vendor_ramdisk_lz4_size": vendor_ramdisk.stat().st_size,
        "cpio_size": len(cpio_bytes),
        "entry_count": len(listing),
        "ko_count": len(ko_paths),
        "modules_total_bytes": sum(module_sizes.values()),
        "modules_load_count": len(modules_load_lines),
        "modules_load_recovery_count": len(recovery_lines),
        "modules_load_recovery_bytes": recovery_bytes,
        "runtime_modules_ssusb_qmp_only_buffer": RUNTIME_MODULES_SSUSB_QMP_ONLY_BUF,
        "runtime_module_name_buffer": RUNTIME_MODULE_NAME_BUF,
        "modules_load_recovery_max_token_len": max(len(line) for line in recovery_lines),
        "modules_load_recovery_max_basename_len": max(len(name) for name in recovery_basenames),
        "modules_load_recovery_duplicate_count": len(recovery_lines) - len(set(recovery_lines)),
        "modules_load_recovery_has_path_components": any("/" in line for line in recovery_lines),
        "modules_load_recovery_has_inline_whitespace": False,
        "modules_load_recovery_all_ko": True,
        "modules_dep_count": len(modules_dep_lines),
        "modules_softdep_has_dwc3_msm": True,
        "required_recovery_module_positions": positions,
        "m16_ssusb_qmp_only": {key: value for key, value in ssusb_qmp_only.items() if key != "subset_text"},
        "recovery_head": recovery_lines[:40],
        "metadata_hashes": {
            "modules.load": sha256_file(metadata_dir / MODULES_LOAD),
            "modules.load.recovery": sha256_file(metadata_dir / MODULES_LOAD_RECOVERY),
            "modules.softdep": sha256_file(metadata_dir / MODULES_SOFTDEP),
            "modules.dep": sha256_file(metadata_dir / MODULES_DEP),
        },
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
    require_ok(result, "compile M16 SSUSB-QMP-only init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M16 SSUSB-QMP-only init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M16 SSUSB-QMP-only init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M16 SSUSB-QMP-only init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M16 SSUSB-QMP-only init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M16 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M16 init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit("M16 init disassembly does not contain svc")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        "/s22plus_m16_ssusb_qmp_only.modules",
        "module_list=boot_ramdisk_ssusb_qmp_only",
        "module_group=ssusb_qmp_only",
        "module_count=1",
        "watchdog_blocklist=1",
        "no_reboot_beacon=1",
        "acm_cmd_status=1",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "a600000.dwc3",
        "role_force=device",
        "ss_acm.0",
        "ttyGS0",
        "S22M16ACM0001",
        "S22_NATIVE_INIT_USB_ACM_M16 READY",
        "S22_NATIVE_INIT_USB_ACM_M16 ACK status park",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M16 /init: {required}")
    reboot_nr_lines = [
        line
        for line in objdump_text.splitlines()
        if "mov" in line and "x8" in line and "#0x8e" in line and "// #142" in line
    ]
    if reboot_nr_lines:
        raise SystemExit("M16 init unexpectedly contains arm64 __NR_reboot (142)")
    for forbidden in (b"ld-linux", b"libc.so", b"/vendor_dlkm", b"s22plus-m5", b"modules.load.recovery", b"download"):
        if forbidden in binary:
            raise SystemExit(f"M16 /init contains forbidden string: {forbidden!r}")

    (build_dir / "m16_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m16_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "m16_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
    }


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
    m16_init = build_dir / "s22plus_init_usb_acm_m16"
    m16_init_info = compile_init(source, m16_init, build_dir)

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

    subset_file = build_dir / MODULES_SSUSB_QMP_ONLY_RAMDISK
    if not subset_file.exists():
        raise SystemExit(f"M16 subset file missing: {subset_file}")
    patch_init_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 750 init {m16_init}"],
        work_dir,
        "replace /init with M16 init",
    )
    patch_subset_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULES_SSUSB_QMP_ONLY_RAMDISK} {subset_file}"],
        work_dir,
        "add M16 SSUSB QMP only list",
    )
    patch_text = patch_init_text + "\n" + patch_subset_text
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M16 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if sha256_file(extracted_replaced) != sha256_file(m16_init):
        raise SystemExit("replaced /init does not match compiled M16 init")
    extracted_subset = build_dir / MODULES_SSUSB_QMP_ONLY_RAMDISK
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {MODULES_SSUSB_QMP_ONLY_RAMDISK} {extracted_subset}.extracted"],
        work_dir,
        "extract M16 SSUSB QMP only list",
    )
    if sha256_file(Path(f"{extracted_subset}.extracted")) != sha256_file(subset_file):
        raise SystemExit("replaced M16 SSUSB QMP only list does not match builder output")

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
        "vendor_ramdisk": sha256_file(vendor_ramdisk),
        "m16_ssusb_qmp_only": sha256_file(subset_file),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m16_init": sha256_file(m16_init),
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
        "m16_ssusb_qmp_only": subset_file.stat().st_size,
        "m16_init": m16_init.stat().st_size,
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
        "purpose": "M16 in-place park-based USB-ACM native-init using only phy-msm-ssusb-qmp.ko from the failed M15 PHY-side pair",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init only",
            "runtime": "freestanding-raw-syscall",
            "glibc_static_startup": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "reboot_syscall": False,
            "host_commanded_reboot_download": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_insertions": "boot ramdisk gets text list only; runtime uses stock vendor_boot /lib/modules",
            "module_binary_injection": False,
            "module_list_path": f"/{MODULES_SSUSB_QMP_ONLY_RAMDISK}",
            "module_subset": "one-module SSUSB-QMP-only split from the failed M15 PHY-side pair: phy-msm-ssusb-qmp",
            "configfs_runtime_gadget": "ss_acm.0 only",
            "udc_binding": "a600000.dwc3 only; never dummy_udc.0",
            "usb_role_force": "attempt /sys/class/usb_role/*/role=device",
            "watchdog": "not-touched-by-init-source; watchdog modules absent from M16 SSUSB-QMP-only subset",
            "observation_model": "park-vs-loop plus host ACM enumeration; no reboot beacon",
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "source": display_path(root, source),
            "base_boot": display_path(root, base_boot),
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "lz4": display_path(root, lz4_tool),
            "magiskboot": display_path(root, magiskboot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m16_init": m16_init_info,
        "vendor_ramdisk": vendor_summary,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": MODULES_SSUSB_QMP_ONLY_RAMDISK,
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
    (out_dir / "required_strings.txt").write_text("\n".join(m16_init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
