#!/usr/bin/env python3
"""Build S22+ M32 watchdog-managed HS-only ACM native-init artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M32 is the first post-M31B observable-transport build. It keeps the watchdog
dependency closure that let M31B survive the 120 second park window, then adds
the dependency-complete M28/M25 HS-only USB/ACM closure. Runtime module binaries
remain in stock vendor_boot /lib/modules; boot ramdisk receives only a generated
/init and a text module list.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_s22plus_inplace_m23_dts_exact_qmp_park as m23
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
from build_s22plus_m25_hs_only_usb2_acm import EXPECTED_M25_HS_ONLY_SUBSET


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m32_wdt_hs_acm_v0_1")
DEFAULT_TEMPLATE_SOURCE = Path("workspace/public/src/native-init/s22plus_init_usb_acm_m18_full_firststage_park.c")
DEFAULT_VENDOR_RAMDISK = m23.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = m23.DEFAULT_LZ4

MARKER = "S22_NATIVE_INIT_USB_ACM_M32_WDT_HS"
MODULES_RAMDISK = "s22plus_m32_wdt_hs_acm.modules"
GENERATED_SOURCE_NAME = "s22plus_init_usb_acm_m32_wdt_hs.c"
GENERATED_INIT_NAME = "s22plus_init_usb_acm_m32_wdt_hs"
USB_SERIAL = "S22M32WDTHS01"
USB_PRODUCT = "S22 Native Init M32 WDT HS ACM"

WATCHDOG_TARGET = "gh_virt_wdt.ko"

M32_EXCLUDED_MODULES = {
    "eud.ko",
    "phy-msm-ssusb-qmp.ko",
    "sec_debug_region.ko",
    "ucsi_glink.ko",
}

EXPECTED_M32_MODULES = [
    "smem.ko",
    "minidump.ko",
    "sec_debug.ko",
    "qcom_ipc_logging.ko",
    "cmd-db.ko",
    "qcom_rpmh.ko",
    "clk-rpmh.ko",
    "debug-regulator.ko",
    "proxy-consumer.ko",
    "gdsc-regulator.ko",
    "clk-qcom.ko",
    "clk-dummy.ko",
    "gcc-waipio.ko",
    "icc-bcm-voter.ko",
    "icc-debug.ko",
    "socinfo.ko",
    "icc-rpmh.ko",
    "rpmh-regulator.ko",
    "qcom-scm.ko",
    "qcom_wdt_core.ko",
    "gh_virt_wdt.ko",
    "iommu-logger.ko",
    "qnoc-qos.ko",
    "qnoc-waipio.ko",
    "phy-generic.ko",
    "qcom_iommu_util.ko",
    "sec_class.ko",
    "secure_buffer.ko",
    "arm_smmu.ko",
    "abc.ko",
    "usb_notify_layer.ko",
    "switch_class.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "pdic_notifier_module.ko",
    "usb_typec_manager.ko",
    "usb_f_ss_mon_gadget.ko",
    "phy-msm-snps-hs.ko",
    "repeater.ko",
    "phy-msm-snps-eusb2.ko",
    "redriver.ko",
    "if_cb_manager.ko",
    "qc_usb_audio.ko",
    "dwc3-msm.ko",
    "usb_f_ss_acm.ko",
]


def dependency_complete_wdt_hs_order(
    *,
    dep_map: dict[str, list[str]],
    recovery_basenames: list[str],
) -> dict[str, Any]:
    order_index = {module: index for index, module in enumerate(recovery_basenames)}
    seen: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []
    blocked_edges: set[str] = set()
    missing: set[str] = set()
    targets = list(EXPECTED_M25_HS_ONLY_SUBSET) + [WATCHDOG_TARGET]

    def sort_key(module: str) -> tuple[int, str]:
        return (order_index.get(module, 10**9), module)

    def visit(module: str, consumer: str | None = None) -> None:
        if module in seen:
            return
        if module in M32_EXCLUDED_MODULES:
            blocked_edges.add(f"{consumer or '<root>'}->{module}")
            return
        if module not in dep_map:
            missing.add(module)
            return
        if module in visiting:
            raise SystemExit(f"cycle in modules.dep while visiting {module}")
        visiting.add(module)
        for dep in sorted(dep_map[module], key=sort_key):
            visit(dep, module)
        visiting.remove(module)
        seen.add(module)
        ordered.append(module)

    for target in sorted(targets, key=sort_key):
        visit(target)

    if missing:
        raise SystemExit(f"M32 dependency closure missing modules.dep entries: {sorted(missing)}")
    if blocked_edges:
        raise SystemExit(f"M32 dependency closure hits excluded hard deps: {sorted(blocked_edges)}")
    if ordered != EXPECTED_M32_MODULES:
        raise SystemExit(f"M32 module order drifted:\nactual={ordered!r}\nexpected={EXPECTED_M32_MODULES!r}")

    dependency_violations = {
        module: [dep for dep in dep_map[module] if dep in ordered and ordered.index(dep) > ordered.index(module)]
        for module in ordered
    }
    dependency_violations = {module: deps for module, deps in dependency_violations.items() if deps}
    if dependency_violations:
        raise SystemExit(f"M32 module order violates modules.dep: {dependency_violations}")
    if len("".join(f"{module}\n" for module in ordered).encode("ascii")) >= 8192:
        raise SystemExit("M32 dependency-complete module list exceeds runtime parser buffer")
    too_long = [module for module in ordered if len(module) >= m23.RUNTIME_MODULE_NAME_BUF]
    if too_long:
        raise SystemExit(f"M32 module basename exceeds runtime parser buffer: {too_long}")

    return {
        "targets": targets,
        "modules": ordered,
        "module_count": len(ordered),
        "module_text": "".join(f"{module}\n" for module in ordered),
        "module_sha256": None,
        "watchdog_modules": ["qcom_wdt_core.ko", "gh_virt_wdt.ko"],
        "usb_modules": ["dwc3-msm.ko", "usb_f_ss_acm.ko", "usb_f_ss_mon_gadget.ko"],
        "excluded_modules": sorted(M32_EXCLUDED_MODULES),
        "stock_recovery_positions": {
            module: recovery_basenames.index(module) + 1
            for module in ordered
            if module in recovery_basenames
        },
        "order_model": "modules.dep topological order with stock modules.load.recovery tie-breaks",
    }


def generate_m32_source(template_source: Path, generated_source: Path, module_count: int) -> str:
    text = template_source.read_text(encoding="utf-8")
    replacements = [
        (
            "Samsung S22+ native-init M18 full-firststage USB add-back candidate.",
            "Samsung S22+ native-init M32 watchdog-managed HS-only ACM candidate.",
        ),
        (
            "M18 starts from the stable M13 no-module floor and reintroduces the vendor\n"
            " * first-stage modules.load set minus reset/anomaly modules, then a USB tail.",
            "M32 starts from the M31B watchdog-managed base and adds the\n"
            " * dependency-complete HS-only USB/ACM closure.",
        ),
        ("S22_NATIVE_INIT_USB_ACM_M18_FULL", MARKER),
        ("s22plus_m18_full_firststage_usb.modules", MODULES_RAMDISK),
        ("MODULES_FULL_FIRSTSTAGE_USB_BUF", "MODULES_M32_WDT_HS_ACM_BUF"),
        ("modules_full_firststage_usb", "modules_m32_wdt_hs_acm"),
        ("full_firststage_usb", "m32_wdt_hs_acm"),
        ("module_list=boot_ramdisk_m32_wdt_hs_acm", "module_list=dep_complete_wdt_hs_acm"),
        ("module_group=m32_wdt_hs_acm module_count=141", f"module_group=m32_wdt_hs_acm module_count={module_count}"),
        (
            "watchdog_blocklist=1 ",
            "watchdog_managed=1 wdt_closure=1 dep_complete=1 hs_only=1 qmp_excluded=1 dtbo_high_speed_cap=not_included ",
        ),
        ("S22 Native Init M18 Full ACM", USB_PRODUCT),
        ("S22M18FULL0001", USB_SERIAL),
        ('write_attr("/config/usb_gadget/g1/bcdUSB", "0x0320")', 'write_attr("/config/usb_gadget/g1/bcdUSB", "0x0200")'),
        ("static void M18_FULL_main(void)", "static void M32_WDT_HS_ACM_main(void)"),
        ("M18_FULL_main();", "M32_WDT_HS_ACM_main();"),
    ]
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"M32 source template replacement missing: {old!r}")
        text = text.replace(old, new)

    required = [
        MARKER,
        MODULES_RAMDISK,
        "module_list=dep_complete_wdt_hs_acm",
        f"module_count={module_count}",
        "watchdog_managed=1",
        "wdt_closure=1",
        "dep_complete=1",
        "hs_only=1",
        "qmp_excluded=1",
        "dtbo_high_speed_cap=not_included",
        "a600000.dwc3",
        "ss_acm.0",
        "ttyGS0",
        "0x0200",
        USB_PRODUCT,
        USB_SERIAL,
        f"{MARKER} READY",
        f"{MARKER} ACK status park",
    ]
    forbidden = [
        "S22_NATIVE_INIT_USB_ACM_M18_FULL",
        "s22plus_m18_full_firststage_usb",
        "M18_FULL_main",
        "watchdog_blocklist=1",
        "module_count=141",
        "0x0320",
        "full_firststage_usb",
        "boot_ramdisk_full_firststage_usb",
    ]
    for item in required:
        if item not in text:
            raise SystemExit(f"generated M32 source missing required marker: {item}")
    for item in forbidden:
        if item in text:
            raise SystemExit(f"generated M32 source still contains forbidden marker: {item}")
    generated_source.write_text(text, encoding="utf-8")
    return text


def compile_init(source: Path, out_path: Path, build_dir: Path, module_count: int) -> dict[str, Any]:
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
            "-Wl,--build-id=none",
            "-Wl,-e,_start",
            "-Wl,-z,noexecstack",
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, "compile M32 watchdog-managed HS ACM init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, "strip M32 watchdog-managed HS ACM init")

    file_info = run(["file", out_path])
    require_ok(file_info, "file M32 init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, "readelf M32 init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, "objdump M32 init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M32 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M32 init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit("M32 init disassembly does not contain svc")
    if not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit("M32 init does not load arm64 __NR_finit_module (273)")
    if any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines()):
        raise SystemExit("M32 init must not load arm64 __NR_reboot (142)")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"/{MODULES_RAMDISK}",
        "module_list=dep_complete_wdt_hs_acm",
        "watchdog_managed=1",
        "wdt_closure=1",
        "dep_complete=1",
        "hs_only=1",
        "qmp_excluded=1",
        "dtbo_high_speed_cap=not_included",
        f"module_count={module_count}",
        "no_reboot_beacon=1",
        "acm_cmd_status=1",
        "a600000.dwc3",
        "role_force=device",
        "ss_acm.0",
        "ttyGS0",
        "0x0200",
        USB_SERIAL,
        f"{MARKER} READY",
        f"{MARKER} ACK status park",
    ]
    forbidden_strings = [
        b"ld-linux",
        b"libc.so",
        b"/vendor_dlkm",
        b"download",
        b"LINUX_REBOOT",
        b"watchdog_blocklist=1",
        b"phy-msm-ssusb-qmp.ko",
        b"super-speed",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M32 /init: {required}")
    for forbidden in forbidden_strings:
        if forbidden in binary:
            raise SystemExit(f"M32 /init contains forbidden string: {forbidden!r}")

    (build_dir / "m32_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "m32_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "m32_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
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
    parser.add_argument("--template-source", type=Path, default=DEFAULT_TEMPLATE_SOURCE)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    template_source = resolve(root, args.template_source)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)

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

    vendor_metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    closure = dependency_complete_wdt_hs_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
    )
    module_list = build_dir / MODULES_RAMDISK
    module_list.write_text(str(closure["module_text"]), encoding="ascii")
    closure["module_sha256"] = sha256_file(module_list)

    generated_source = build_dir / GENERATED_SOURCE_NAME
    generate_m32_source(template_source, generated_source, int(closure["module_count"]))
    init_out = build_dir / GENERATED_INIT_NAME
    init_info = compile_init(generated_source, init_out, build_dir, int(closure["module_count"]))

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "M32 no-change unpack")
    run_in_dir([magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"], nochange_dir, "M32 no-change repack")
    nochange_sha = sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M32 no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "M32 unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "M32 extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, "M32 replace /init")
    patch_modules_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULES_RAMDISK} {module_list}"],
        work_dir,
        "M32 add module list",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M32 patch: {cpio_test_after}")

    extracted_init = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, "M32 extract replaced init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit("replaced /init does not match compiled M32 init")
    extracted_modules = build_dir / f"{MODULES_RAMDISK}.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract {MODULES_RAMDISK} {extracted_modules}"], work_dir, "M32 extract module list")
    if sha256_file(extracted_modules) != sha256_file(module_list):
        raise SystemExit("replaced M32 module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "M32 repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M32 patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "M32 unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("M32 patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M32 AP tar member mismatch: {members}")

    hashes = {
        "template_source": sha256_file(template_source),
        "generated_source": sha256_file(generated_source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m32_modules": sha256_file(module_list),
        "m32_init": sha256_file(init_out),
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
        "m32_modules": module_list.stat().st_size,
        "m32_init": init_out.stat().st_size,
        "generated_source": generated_source.stat().st_size,
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
        "purpose": "M32 watchdog-managed dependency-complete HS-only ACM transport candidate",
        "closure": closure,
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one text module list",
            "runtime": "freestanding-raw-syscall",
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "intended_reboot_syscall": False,
            "reboot_request": None,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_list_path": f"/{MODULES_RAMDISK}",
            "configfs_runtime_gadget": "ss_acm.0 only",
            "usb_role_force": True,
            "acm": True,
            "watchdog_managed": True,
            "qmp_module_excluded": True,
            "dtbo_high_speed_cap_included": False,
            "observation_model": "host sees ACM/ttyGS0 while no PMIC reset; no self-download beacon",
        },
        "vendor": {
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "vendor_ramdisk_sha256": sha256_file(vendor_ramdisk),
            "metadata_hashes": vendor_metadata["metadata_hashes"],
            "modules_load_count": vendor_metadata["modules_load_count"],
            "modules_load_recovery_count": vendor_metadata["modules_load_recovery_count"],
            "modules_dep_count": vendor_metadata["modules_dep_count"],
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "template_source": display_path(root, template_source),
            "generated_source": display_path(root, generated_source),
            "base_boot": display_path(root, base_boot),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m32_init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": MODULES_RAMDISK,
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
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    (out_dir / "sizes.txt").write_text("".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())), encoding="ascii")
    (out_dir / "required_strings.txt").write_text("\n".join(init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
