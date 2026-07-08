#!/usr/bin/env python3
"""Build the S22+ M24 pmsg-step native-init candidate.

Host-only. This script does not reboot, flash, or touch a connected device.

M24 keeps the M23 DTS-exact QMP/DWC3 43-module substrate, but adds retained
`A90_STEP:` markers to `/dev/pmsg0` before module insertion work. The goal is
to turn a blind bootloop into a last-step report after rollback, if Samsung's
pmsg path retains the write across the warm reset.
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/inplace_m24_pmsg_steps_v0_1")
MARKER = "S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS"
MODULES_RAMDISK = "s22plus_m24_pmsg_steps.modules"
GENERATED_SOURCE_NAME = "s22plus_init_usb_acm_m24_pmsg_steps.c"
GENERATED_INIT_NAME = "s22plus_init_usb_acm_m24_pmsg_steps"
USB_SERIAL = "S22M24PMSG001"
USB_PRODUCT = "S22 Native Init M24 PMSG ACM"
PMSG_STEP_PREFIX = "A90_STEP:M24:"


def generate_m24_source(template_source: Path, generated_source: Path, module_count: int) -> str:
    text = template_source.read_text(encoding="utf-8")
    replacements = [
        (
            "Samsung S22+ native-init M18 full-firststage USB add-back candidate.",
            "Samsung S22+ native-init M24 pmsg-step DTS-exact QMP/DWC3 candidate.",
        ),
        (
            "M18 starts from the stable M13 no-module floor and reintroduces the vendor\n"
            " * first-stage modules.load set minus reset/anomaly modules, then a USB tail.",
            "M24 keeps the M23 DTS-exact QMP/DWC3 module closure and writes\n"
            " * A90_STEP pmsg markers before each risky module insertion.",
        ),
        ("S22_NATIVE_INIT_USB_ACM_M18_FULL", MARKER),
        ("s22plus_m18_full_firststage_usb.modules", MODULES_RAMDISK),
        ("MODULES_FULL_FIRSTSTAGE_USB_BUF", "MODULES_DTS_EXACT_QMP_BUF"),
        ("modules_full_firststage_usb", "modules_dts_exact_qmp"),
        ("full_firststage_usb", "dts_exact_qmp"),
        ("M18 Full ACM", USB_PRODUCT),
        ("S22M18FULL0001", USB_SERIAL),
        ("module_count=141", f"module_count={module_count}"),
        ("watchdog_blocklist=1 ", "watchdog_blocklist=1 pmsg_steps=1 fallback_pmsg_major=507 "),
        ("static void M18_FULL_main(void)", "static void M24_main(void)"),
        ("M18_FULL_main();", "M24_main();"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    node_old = '    ensure_chr_node("/dev/kmsg", 0600, 1, 11);\n'
    node_new = node_old + '    ensure_chr_node("/dev/pmsg0", 0222, 507, 0);\n'
    if node_old not in text:
        raise SystemExit("pmsg injection point missing: /dev/kmsg node")
    text = text.replace(node_old, node_new, 1)

    emit_old = """static void emit(const char *s) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, s);
    emit_buf(&sb);
}

"""
    emit_new = emit_old + r'''static void emit_pmsg_buf(const struct sbuf *sb) {
    long fd = sys_openat(AT_FDCWD, "/dev/pmsg0", O_WRONLY | O_CLOEXEC, 0);
    if (fd >= 0) {
        (void)sys_write((int)fd, sb->data, sb->len);
        (void)sys_close((int)fd);
    }
}

static void emit_pmsg_phase(const char *phase) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "A90_STEP:M24:");
    sb_puts(&sb, phase);
    sb_putc(&sb, '\n');
    emit_pmsg_buf(&sb);
}

static void emit_pmsg_module(size_t index, const char *name, const char *phase) {
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "A90_STEP:M24:");
    sb_puts(&sb, phase);
    sb_puts(&sb, " index=");
    sb_put_u64(&sb, (uint64_t)index);
    sb_puts(&sb, " name=");
    sb_puts(&sb, name);
    sb_putc(&sb, '\n');
    emit_pmsg_buf(&sb);
}

'''
    if emit_old not in text:
        raise SystemExit("pmsg injection point missing: emit()")
    text = text.replace(emit_old, emit_new, 1)

    load_old = """static void load_one_module(size_t index, const char *name) {
    char path[256];
"""
    load_new = """static void load_one_module(size_t index, const char *name) {
    emit_pmsg_module(index, name, "module_prepare");
    char path[256];
"""
    if load_old not in text:
        raise SystemExit("pmsg injection point missing: load_one_module start")
    text = text.replace(load_old, load_new, 1)

    finit_old = """    long rc = sys_finit_module((int)fd, "", 0);
"""
    finit_new = """    emit_pmsg_module(index, name, "module_finit");
    long rc = sys_finit_module((int)fd, "", 0);
"""
    if finit_old not in text:
        raise SystemExit("pmsg injection point missing: sys_finit_module")
    text = text.replace(finit_old, finit_new, 1)

    module_start_old = """static void load_dts_exact_qmp_modules(void) {
    static char text[MODULES_DTS_EXACT_QMP_BUF];
"""
    module_start_new = """static void load_dts_exact_qmp_modules(void) {
    emit_pmsg_phase("modules_start");
    static char text[MODULES_DTS_EXACT_QMP_BUF];
"""
    if module_start_old not in text:
        raise SystemExit("pmsg injection point missing: module-list start")
    text = text.replace(module_start_old, module_start_new, 1)

    module_done_old = """    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS phase=modules_dts_exact_qmp_done count=");
"""
    module_done_new = """    emit_pmsg_phase("modules_done");
    struct sbuf sb = {.data = {0}, .len = 0};
    sb_puts(&sb, "S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS phase=modules_dts_exact_qmp_done count=");
"""
    if module_done_old not in text:
        raise SystemExit("pmsg injection point missing: module-list done")
    text = text.replace(module_done_old, module_done_new, 1)

    main_old = """static void M24_main(void) {
    setup_minimal_fs();
    emit(k_marker);
    load_dts_exact_qmp_modules();
    force_usb_roles_device();
    (void)create_acm_gadget();
    serial_probe_loop();
}
"""
    main_new = """static void M24_main(void) {
    setup_minimal_fs();
    emit_pmsg_phase("pid1_start");
    emit_pmsg_phase("mounts_done");
    emit(k_marker);
    emit_pmsg_phase("modules_call");
    load_dts_exact_qmp_modules();
    emit_pmsg_phase("usb_role_call");
    force_usb_roles_device();
    emit_pmsg_phase("acm_gadget_call");
    (void)create_acm_gadget();
    emit_pmsg_phase("park_loop");
    serial_probe_loop();
}
"""
    if main_old not in text:
        raise SystemExit("pmsg injection point missing: M24_main")
    text = text.replace(main_old, main_new, 1)

    for forbidden in ("S22_NATIVE_INIT_USB_ACM_M18_FULL", "s22plus_m18_full_firststage_usb", "full_firststage_usb"):
        if forbidden in text:
            raise SystemExit(f"generated M24 source still contains {forbidden}")
    for required in (MARKER, MODULES_RAMDISK, USB_SERIAL, PMSG_STEP_PREFIX, "fallback_pmsg_major=507"):
        if required not in text:
            raise SystemExit(f"generated M24 source missing required marker: {required}")
    generated_source.write_text(text, encoding="utf-8")
    return text


def compile_init(source: Path, out_path: Path, build_dir: Path, module_count: int) -> dict[str, Any]:
    result = m23.run(
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
    m23.require_ok(result, "compile M24 pmsg-step init")
    strip = m23.run(["aarch64-linux-gnu-strip", "-s", out_path])
    m23.require_ok(strip, "strip M24 pmsg-step init")

    file_info = m23.run(["file", out_path])
    m23.require_ok(file_info, "file M24 pmsg-step init")
    readelf = m23.run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    m23.require_ok(readelf, "readelf M24 pmsg-step init")
    objdump = m23.run(["aarch64-linux-gnu-objdump", "-d", out_path])
    m23.require_ok(objdump, "objdump M24 pmsg-step init")

    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit("M24 init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit("M24 init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit("M24 init disassembly does not contain svc")

    required_strings = [
        MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"/{MODULES_RAMDISK}",
        "module_list=boot_ramdisk_dts_exact_qmp",
        "module_group=dts_exact_qmp",
        f"module_count={module_count}",
        "watchdog_blocklist=1",
        "pmsg_steps=1",
        "fallback_pmsg_major=507",
        "no_reboot_beacon=1",
        "acm_cmd_status=1",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "a600000.dwc3",
        "role_force=device",
        "ss_acm.0",
        "ttyGS0",
        USB_SERIAL,
        PMSG_STEP_PREFIX,
        "module_prepare",
        "module_finit",
        f"{MARKER} READY",
        f"{MARKER} ACK status park",
    ]
    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M24 /init: {required}")
    reboot_nr_lines = [
        line
        for line in objdump_text.splitlines()
        if "mov" in line and "x8" in line and "#0x8e" in line and "// #142" in line
    ]
    if reboot_nr_lines:
        raise SystemExit("M24 init unexpectedly contains arm64 __NR_reboot (142)")
    for forbidden in (
        b"ld-linux",
        b"libc.so",
        b"/vendor_dlkm",
        b"s22plus-m5",
        b"modules.load.recovery",
        b"download",
        b"M18_FULL",
        b"m18_full",
        b"full_firststage",
    ):
        if forbidden in binary:
            raise SystemExit(f"M24 /init contains forbidden string: {forbidden!r}")

    (build_dir / "M24_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / "M24_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / "M24_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "readelf": readelf_text,
        "objdump": objdump_text,
        "required_strings": required_strings,
    }


def build_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=m23.DEFAULT_BASE_BOOT)
    parser.add_argument("--template-source", type=Path, default=m23.DEFAULT_TEMPLATE_SOURCE)
    parser.add_argument("--vendor-dtb", type=Path, default=m23.DEFAULT_VENDOR_DTB)
    parser.add_argument("--vendor-ramdisk", type=Path, default=m23.DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=m23.DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=m23.DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=m23.DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=m23.DEFAULT_ODIN)
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    args = parser.parse_args(argv)

    root = m23.repo_root()
    out_dir = m23.resolve(root, args.out)
    base_boot = m23.resolve(root, args.base_boot)
    template_source = m23.resolve(root, args.template_source)
    vendor_dtb = m23.resolve(root, args.vendor_dtb)
    vendor_ramdisk = m23.resolve(root, args.vendor_ramdisk)
    lz4_tool = m23.resolve(root, args.lz4)
    magiskboot = m23.resolve(root, args.magiskboot)
    magisk_apk = m23.resolve(root, args.magisk_apk)
    odin = m23.resolve(root, args.odin)

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

    m23.ensure_magiskboot(magiskboot, magisk_apk)
    for required_path, label in (
        (template_source, "template source"),
        (vendor_dtb, "vendor DTB"),
        (vendor_ramdisk, "vendor ramdisk"),
        (base_boot, "base boot"),
    ):
        if not required_path.exists():
            raise SystemExit(f"{label} missing: {required_path}")

    base_sha = m23.sha256_file(base_boot)
    if base_sha != m23.EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != m23.BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {m23.BOOT_PARTITION_SIZE}")

    vendor_metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    dtb_image = vendor_dtb.read_bytes()
    dts_exact_qmp = m23.derive_dts_exact_qmp(
        dtb_image=dtb_image,
        compat_to_modules=vendor_metadata["compat_to_modules"],
        dep_map=vendor_metadata["dep_map"],
        recovery_lines=vendor_metadata["recovery_lines"],
    )
    subset_text = str(dts_exact_qmp["subset_text"])
    module_count = int(dts_exact_qmp["dts_exact_qmp"]["subset_count"])
    subset_file = build_dir / MODULES_RAMDISK
    subset_file.write_text(subset_text, encoding="ascii")
    (build_dir / "m24_pmsg_steps.txt").write_text(subset_text, encoding="ascii")

    generated_source = build_dir / GENERATED_SOURCE_NAME
    generate_m24_source(template_source, generated_source, module_count)
    m24_init = build_dir / GENERATED_INIT_NAME
    m24_init_info = compile_init(generated_source, m24_init, build_dir, module_count)

    nochange_unpack = m23.run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "magiskboot no-change unpack")
    nochange_repack = m23.run_in_dir(
        [magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"],
        nochange_dir,
        "magiskboot no-change repack",
    )
    nochange_sha = m23.sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"magiskboot no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    unpack_text = m23.run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "magiskboot unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    extract_text = m23.run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "extract original Magisk init")
    original_init_sha = m23.sha256_file(original_init)
    if original_init_sha != m23.EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    ramdisk_before_sha = m23.sha256_file(ramdisk_before)
    cpio_test_before = m23.run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1, got {cpio_test_before}")

    patch_init_text = m23.run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {m24_init}"], work_dir, "replace /init with M24 init")
    patch_subset_text = m23.run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {MODULES_RAMDISK} {subset_file}"],
        work_dir,
        "add M24 pmsg-step module list",
    )
    patch_text = patch_init_text + "\n" + patch_subset_text
    cpio_test_after = m23.run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M24 patch: {cpio_test_after}")

    extracted_replaced = build_dir / "init.replaced"
    m23.run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_replaced}"], work_dir, "extract replaced init")
    if m23.sha256_file(extracted_replaced) != m23.sha256_file(m24_init):
        raise SystemExit("replaced /init does not match compiled M24 init")
    extracted_subset = build_dir / f"{MODULES_RAMDISK}.extracted"
    m23.run_in_dir([magiskboot, "cpio", ramdisk, f"extract {MODULES_RAMDISK} {extracted_subset}"], work_dir, "extract M24 module list")
    if m23.sha256_file(extracted_subset) != m23.sha256_file(subset_file):
        raise SystemExit("replaced M24 module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    ramdisk_after_sha = m23.sha256_file(ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = m23.run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "magiskboot repack patched boot")
    if boot_img.stat().st_size != m23.BOOT_PARTITION_SIZE:
        raise SystemExit(f"patched boot size mismatch: {boot_img.stat().st_size} != {m23.BOOT_PARTITION_SIZE}")

    patched_unpack_dir = out_dir / "patched-unpack"
    patched_unpack_dir.mkdir()
    patched_unpack = m23.run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "unpack patched boot")
    if m23.sha256_file(patched_unpack_dir / "kernel") != m23.sha256_file(kernel):
        raise SystemExit("patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    m23.write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    m23.write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = m23.tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"AP tar member mismatch: {members}")

    parse_gate_text = ""
    if not args.no_odin_parse_gate and odin.exists():
        invalid_odin_target = str(Path("/dev") / "bus" / "usb" / "999" / "999")
        gate = m23.run([odin, "-a", ap_md5, "-d", invalid_odin_target])
        parse_gate_text = (gate.stdout + gate.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(parse_gate_text, encoding="utf-8")

    hashes = {
        "template_source": m23.sha256_file(template_source),
        "generated_source": m23.sha256_file(generated_source),
        "base_boot": base_sha,
        "vendor_dtb": m23.sha256_file(vendor_dtb),
        "vendor_ramdisk": m23.sha256_file(vendor_ramdisk),
        "m24_pmsg_steps": m23.sha256_file(subset_file),
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "m24_init": m23.sha256_file(m24_init),
        "ramdisk_before": ramdisk_before_sha,
        "ramdisk_after": ramdisk_after_sha,
        "kernel": m23.sha256_file(kernel),
        "header": m23.sha256_file(header),
        "boot_img": m23.sha256_file(boot_img),
        "boot_img_lz4": m23.sha256_file(boot_lz4),
        "ap_tar": m23.sha256_file(ap_tar),
        "ap_tar_md5": m23.sha256_file(ap_md5),
    }
    sizes = {
        "base_boot": base_boot.stat().st_size,
        "vendor_dtb": vendor_dtb.stat().st_size,
        "vendor_ramdisk_lz4": vendor_ramdisk.stat().st_size,
        "vendor_ramdisk_cpio": int(vendor_metadata["cpio_size"]),
        "m24_pmsg_steps": subset_file.stat().st_size,
        "generated_source": generated_source.stat().st_size,
        "m24_init": m24_init.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }

    vendor_summary = {
        "vendor_ramdisk_sha256": m23.sha256_file(vendor_ramdisk),
        "vendor_ramdisk_lz4_size": vendor_ramdisk.stat().st_size,
        "vendor_dtb_sha256": m23.sha256_file(vendor_dtb),
        "vendor_dtb_size": vendor_dtb.stat().st_size,
        "cpio_size": int(vendor_metadata["cpio_size"]),
        "entry_count": int(vendor_metadata["entry_count"]),
        "ko_count": int(vendor_metadata["ko_count"]),
        "modules_load_count": int(vendor_metadata["modules_load_count"]),
        "modules_load_recovery_count": int(vendor_metadata["modules_load_recovery_count"]),
        "modules_dep_count": int(vendor_metadata["modules_dep_count"]),
        "metadata_hashes": vendor_metadata["metadata_hashes"],
    }

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": "M24 pmsg-step DTS-exact QMP/DWC3 dependency closure native-init park candidate",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one module-list text file",
            "runtime": "freestanding-raw-syscall",
            "glibc_static_startup": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "reboot_syscall": False,
            "host_commanded_reboot_download": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_list_path": f"/{MODULES_RAMDISK}",
            "module_subset": "same 43-module DTS-derived QMP/DWC3/HS-PHY/provider closure as M23",
            "configfs_runtime_gadget": "ss_acm.0 only",
            "udc_binding": "a600000.dwc3 only; never dummy_udc.0",
            "usb_role_force": "attempt /sys/class/usb_role/*/role=device",
            "eud": "EUD extcon observed but intentionally not loaded/opened/enabled in this candidate",
            "watchdog": "gh_virt_wdt/qcom_wdt_core reset path blocklisted; sec_debug/minidump/abc also blocklisted",
            "pmsg_step_markers": True,
            "pmsg_path": "/dev/pmsg0",
            "pmsg_fallback_chrdev": "major=507 minor=0 mode=0222",
            "pmsg_marker_prefix": PMSG_STEP_PREFIX,
            "observation_model": "park plus host ACM enumeration; if it loops, rollback then inspect retained pmsg/pstore/reset surfaces",
        },
        "paths": {
            "out_dir": m23.display_path(root, out_dir),
            "template_source": m23.display_path(root, template_source),
            "generated_source": m23.display_path(root, generated_source),
            "base_boot": m23.display_path(root, base_boot),
            "vendor_dtb": m23.display_path(root, vendor_dtb),
            "vendor_ramdisk": m23.display_path(root, vendor_ramdisk),
            "lz4": m23.display_path(root, lz4_tool),
            "magiskboot": m23.display_path(root, magiskboot),
            "boot_img": m23.display_path(root, boot_img),
            "ap_tar_md5": m23.display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "m24_init": m24_init_info,
        "vendor": vendor_summary,
        "dts_exact_qmp": {key: value for key, value in dts_exact_qmp.items() if key != "subset_text"},
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
            "patched_unpack_output": patched_unpack,
            "nochange_unpack_output": nochange_unpack,
            "nochange_repack_output": nochange_repack,
            "extract_output": extract_text,
            "patch_output": patch_text,
        },
        "boot_diff_vs_base": m23.diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "odin_invalid_device_parse_gate": parse_gate_text,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    (out_dir / "sizes.txt").write_text("".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())), encoding="ascii")
    (out_dir / "required_strings.txt").write_text("\n".join(m24_init_info["required_strings"]) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(build_main(sys.argv[1:]))
