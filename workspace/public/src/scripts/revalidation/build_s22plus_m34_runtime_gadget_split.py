#!/usr/bin/env python3
"""Build S22+ M34 runtime gadget split native-init artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M34 starts after P30 proved the full ACM module closure can park safely without
runtime gadget binding. These artifacts encode the stock ACM recipe, then
isolate the HS-only/PD-less knobs, the final pullup, and the stock-kernel-proven
role lever:

S1: create configfs gadget/function/config, UDC=none, no max_speed/role/bind.
S2: S1 plus max_speed=high-speed and usb_role=device, no UDC bind.
S3: S2 plus UDC bind/pullup on a600000.dwc3.
S4: S3 behavior, but replace the dead usb_role path with
    ssusb/speed=high-speed + ssusb/mode=peripheral before UDC bind.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
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
from build_s22plus_m32_wdt_hs_acm import EXPECTED_M32_MODULES, dependency_complete_wdt_hs_order


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_3")
DEFAULT_TEMPLATE_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c")
DEFAULT_VENDOR_RAMDISK = m23.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = m23.DEFAULT_LZ4

MARKER_PREFIX = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT"


@dataclass(frozen=True)
class RuntimeStage:
    label: str
    number: int
    purpose: str
    configfs_gadget: bool
    udc_none: bool
    max_speed_high_speed: bool
    usb_role_force: bool
    ssusb_speed_high_speed: bool
    ssusb_mode_peripheral: bool
    udc_bind: bool

    @property
    def lower(self) -> str:
        return self.label.lower()

    @property
    def marker(self) -> str:
        return f"{MARKER_PREFIX}_{self.label}"

    @property
    def modules_ramdisk(self) -> str:
        return f"s22plus_m34_{self.lower}_runtime_gadget_split.modules"

    @property
    def init_name(self) -> str:
        return f"s22plus_init_m34_{self.lower}_runtime_gadget_split"


STAGES = [
    RuntimeStage(
        "S1",
        1,
        "stock configfs gadget/function/config plus UDC=none; no max_speed, no role force, no UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
    ),
    RuntimeStage(
        "S2",
        2,
        "S1 plus max_speed=high-speed and usb_role=device; no UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=True,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
    ),
    RuntimeStage(
        "S3",
        3,
        "S2 plus UDC bind/pullup on a600000.dwc3",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=True,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=True,
    ),
    RuntimeStage(
        "S4",
        4,
        "S3 with the dead usb_role path replaced by ssusb/speed=high-speed and ssusb/mode=peripheral before UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=False,
        ssusb_speed_high_speed=True,
        ssusb_mode_peripheral=True,
        udc_bind=True,
    ),
]


def _stage_by_label(label: str) -> RuntimeStage:
    for stage in STAGES:
        if stage.label == label:
            return stage
    raise KeyError(label)


def c_define_string(name: str, value: str) -> str:
    return f'-D{name}="{value}"'


def compile_init(source: Path, out_path: Path, build_dir: Path, stage: RuntimeStage, module_count: int) -> dict[str, Any]:
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
            f"-DM34_STAGE={stage.number}",
            c_define_string("M34_STAGE_NAME", stage.label),
            c_define_string("M34_MARKER", stage.marker),
            f"-DM34_MODULE_LIMIT={module_count}",
            c_define_string("M34_MODULES_RAMDISK", f"/{stage.modules_ramdisk}"),
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, f"compile M34 {stage.label} runtime gadget split init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, f"strip M34 {stage.label} runtime gadget split init")

    file_info = run(["file", out_path])
    require_ok(file_info, f"file M34 {stage.label} init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, f"readelf M34 {stage.label} init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, f"objdump M34 {stage.label} init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit(f"M34 {stage.label} init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit(f"M34 {stage.label} init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit(f"M34 {stage.label} init disassembly does not contain svc")
    if not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M34 {stage.label} init does not load arm64 __NR_finit_module (273)")
    if any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M34 {stage.label} init must not load arm64 __NR_reboot (142)")

    required_strings = [
        stage.marker,
        "version=0.3",
        "runtime=freestanding",
        "raw_syscalls=1",
        f"/{stage.modules_ramdisk}",
        "module_list=dep_complete_runtime_gadget_split",
        f"stage={stage.label}",
        f"runtime_step={stage.label}",
        f"module_count={module_count}",
        "no_android_handoff=1",
        "no_reboot_request=1",
        "no_download_beacon=1",
        "phase=modules_load_done",
        "phase=configfs_done",
        "phase=park_enter",
        "/config/usb_gadget/g1",
        "/config/usb_gadget/g1/UDC",
        "/config/usb_gadget/g1/functions/ss_acm.0",
        "../../functions/ss_acm.0",
        "stock_order=1",
        "udc_none=1",
        "0x04E8",
        "0x0200",
        "0x6860",
        "900",
        "none",
        "S22 Native Init M34 Runtime Split",
        "S22M34RUNTIME01",
    ]
    if stage.max_speed_high_speed:
        required_strings.extend(["max_speed_high_speed=1", "/config/usb_gadget/g1/max_speed", "high-speed", "phase=max_speed"])
    else:
        required_strings.append("max_speed_high_speed=0")
    if stage.usb_role_force:
        required_strings.extend(["role_force=1", "/sys/class/usb_role", "phase=usb_role_done"])
    else:
        required_strings.append("role_force=0")
    if stage.ssusb_speed_high_speed:
        required_strings.extend([
            "ssusb_speed_high_speed=1",
            "/sys/devices/platform/soc/a600000.ssusb/speed",
            "phase=ssusb_speed",
        ])
    else:
        required_strings.append("ssusb_speed_high_speed=0")
    if stage.ssusb_mode_peripheral:
        required_strings.extend([
            "ssusb_mode_peripheral=1",
            "/sys/devices/platform/soc/a600000.ssusb/mode",
            "peripheral",
            "phase=ssusb_mode",
        ])
    else:
        required_strings.append("ssusb_mode_peripheral=0")
    if stage.udc_bind:
        required_strings.extend(["udc_bind=1", "/config/usb_gadget/g1/UDC", "/sys/class/udc", "a600000.dwc3", "phase=udc_bind"])
    else:
        required_strings.append("udc_bind=0")

    forbidden_strings = [
        b"ld-linux",
        b"libc.so",
        b"/vendor_dlkm",
        b"reboot_request=download",
        b"LINUX_REBOOT",
        b"ttyGS0",
    ]
    if not stage.max_speed_high_speed:
        forbidden_strings.extend([b"/config/usb_gadget/g1/max_speed", b"phase=max_speed", b"high-speed"])
    if not stage.usb_role_force:
        forbidden_strings.extend([b"/sys/class/usb_role", b"phase=usb_role_done"])
    if not stage.ssusb_speed_high_speed:
        forbidden_strings.extend([b"/sys/devices/platform/soc/a600000.ssusb/speed", b"phase=ssusb_speed"])
    if not stage.ssusb_mode_peripheral:
        forbidden_strings.extend([b"/sys/devices/platform/soc/a600000.ssusb/mode", b"phase=ssusb_mode", b"value=peripheral"])
    if not stage.udc_bind:
        forbidden_strings.extend([b"/sys/class/udc", b"a600000.dwc3", b"phase=udc_bind"])

    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M34 {stage.label} /init: {required}")
    for forbidden in forbidden_strings:
        if forbidden in binary:
            raise SystemExit(f"M34 {stage.label} /init contains forbidden string: {forbidden!r}")

    (build_dir / f"{stage.lower}_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / f"{stage.lower}_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / f"{stage.lower}_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "required_strings": required_strings,
        "readelf_path": f"build/{stage.lower}_init_readelf.txt",
        "objdump_path": f"build/{stage.lower}_init_objdump.txt",
    }


def build_stage(
    *,
    root: Path,
    out_dir: Path,
    base_boot: Path,
    template_source: Path,
    magiskboot: Path,
    closure: dict[str, Any],
    stage: RuntimeStage,
) -> dict[str, Any]:
    stage_dir = out_dir / stage.label
    build_dir = stage_dir / "build"
    work_dir = stage_dir / "magiskboot-work"
    patched_unpack_dir = stage_dir / "patched-unpack"
    odin_dir = stage_dir / "odin4"
    for directory in (build_dir, work_dir, patched_unpack_dir, odin_dir):
        directory.mkdir(parents=True)

    stage_closure = json.loads(json.dumps(closure))
    module_list = build_dir / stage.modules_ramdisk
    module_list.write_text(str(stage_closure["module_text"]), encoding="ascii")
    stage_closure["module_sha256"] = sha256_file(module_list)

    init_out = build_dir / stage.init_name
    init_info = compile_init(template_source, init_out, build_dir, stage, int(stage_closure["module_count"]))

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, f"M34 {stage.label} unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, f"M34 {stage.label} extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch for M34 {stage.label}: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1 for M34 {stage.label}, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, f"M34 {stage.label} replace /init")
    patch_modules_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {stage.modules_ramdisk} {module_list}"],
        work_dir,
        f"M34 {stage.label} add module list",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M34 {stage.label} patch: {cpio_test_after}")

    extracted_init = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, f"M34 {stage.label} extract replaced init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit(f"replaced /init does not match compiled M34 {stage.label} init")
    extracted_modules = build_dir / f"{stage.modules_ramdisk}.extracted"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {stage.modules_ramdisk} {extracted_modules}"],
        work_dir,
        f"M34 {stage.label} extract module list",
    )
    if sha256_file(extracted_modules) != sha256_file(module_list):
        raise SystemExit(f"replaced M34 {stage.label} module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = stage_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, f"M34 {stage.label} repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M34 {stage.label} patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, f"M34 {stage.label} unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit(f"M34 {stage.label} patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M34 {stage.label} AP tar member mismatch: {members}")

    hashes = {
        "base_boot": sha256_file(base_boot),
        "original_magisk_init": original_init_sha,
        "m34_modules": sha256_file(module_list),
        "m34_init": sha256_file(init_out),
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
        "m34_modules": module_list.stat().st_size,
        "m34_init": init_out.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    stage_manifest = {
        "label": stage.label,
        "stage_number": stage.number,
        "purpose": stage.purpose,
        "runtime_steps": {
            "configfs_gadget": stage.configfs_gadget,
            "udc_none": stage.udc_none,
            "max_speed_high_speed": stage.max_speed_high_speed,
            "usb_role_force": stage.usb_role_force,
            "ssusb_speed_high_speed": stage.ssusb_speed_high_speed,
            "ssusb_mode_peripheral": stage.ssusb_mode_peripheral,
            "udc_bind": stage.udc_bind,
        },
        "closure": stage_closure,
        "paths": {
            "stage_dir": display_path(root, stage_dir),
            "template_source": display_path(root, template_source),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
            "module_list": display_path(root, module_list),
        },
        "hashes": hashes,
        "sizes": sizes,
        "init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": stage.modules_ramdisk,
            "added_subset_entry_mode": "640",
            "module_files_injected_into_boot_ramdisk": 0,
            "module_list_files_injected_into_boot_ramdisk": 1,
        },
        "magiskboot": {
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patch_output": patch_init_text + "\n" + patch_modules_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
    }
    (stage_dir / "manifest.json").write_text(json.dumps(stage_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return stage_manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--template-source", type=Path, default=DEFAULT_TEMPLATE_SOURCE)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--stages", nargs="*", default=[stage.label for stage in STAGES])
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
    selected_stages = [_stage_by_label(label) for label in args.stages]

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    common_build_dir = out_dir / "build"
    nochange_dir = out_dir / "nochange-probe"
    common_build_dir.mkdir()
    nochange_dir.mkdir()

    ensure_magiskboot(magiskboot, magisk_apk)
    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")

    vendor_metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, common_build_dir)
    closure = dependency_complete_wdt_hs_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
    )
    if closure["modules"] != EXPECTED_M32_MODULES:
        raise SystemExit("M34 closure drifted from P30/M32 full ACM module closure")

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "M34 no-change unpack")
    run_in_dir([magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"], nochange_dir, "M34 no-change repack")
    nochange_sha = sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M34 no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    stage_manifests = [
        build_stage(
            root=root,
            out_dir=out_dir,
            base_boot=base_boot,
            template_source=template_source,
            magiskboot=magiskboot,
            closure=closure,
            stage=stage,
        )
        for stage in selected_stages
    ]

    hashes: dict[str, str] = {
        "template_source": sha256_file(template_source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
    }
    for stage_manifest in stage_manifests:
        label = stage_manifest["label"]
        for key in ("boot_img", "boot_img_lz4", "ap_tar", "ap_tar_md5", "m34_init", "m34_modules"):
            hashes[f"{label}.{key}"] = stage_manifest["hashes"][key]

    manifest: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
        "purpose": (
            "M34 stock-ordered runtime gadget split plus S4 ssusb role-lever candidate"
        ),
        "stock_recipe_report": "docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md",
        "stages": stage_manifests,
        "matrix": {
            "stages": [
                {
                    "label": stage.label,
                    "stage_number": stage.number,
                    "purpose": stage.purpose,
                    "configfs_gadget": stage.configfs_gadget,
                    "udc_none": stage.udc_none,
                    "max_speed_high_speed": stage.max_speed_high_speed,
                    "usb_role_force": stage.usb_role_force,
                    "ssusb_speed_high_speed": stage.ssusb_speed_high_speed,
                    "ssusb_mode_peripheral": stage.ssusb_mode_peripheral,
                    "udc_bind": stage.udc_bind,
                }
                for stage in selected_stages
            ],
            "live_order": ["S1", "S2", "S3", "S4"],
            "p30_is_s0": True,
            "module_closure_matches_p30_and_m32": True,
        },
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one text module list per stage",
            "runtime": "freestanding-raw-syscall",
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "intended_reboot_syscall": False,
            "reboot_request": None,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_files_injected_into_boot_ramdisk": 0,
            "watchdog_managed": True,
            "qmp_module_excluded": True,
            "eud_module_excluded": True,
            "stock_order_udc_none_before_ids_and_link": True,
            "stock_order_udc_bind_last": True,
            "stage_s1_no_max_speed_high_speed": True,
            "stage_s1_no_role_force": True,
            "stage_s1_no_udc_bind": True,
            "stage_s2_sets_max_speed_high_speed": True,
            "stage_s2_no_udc_bind": True,
            "stage_s3_binds_only_a600000_dwc3": True,
            "stage_s4_replaces_dead_usb_role_with_ssusb_role_lever": True,
            "stage_s4_sets_ssusb_speed_high_speed_before_udc_bind": True,
            "stage_s4_sets_ssusb_mode_peripheral_before_udc_bind": True,
            "stage_s4_no_usb_role_force": True,
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
            "base_boot": display_path(root, base_boot),
        },
        "hashes": hashes,
        "magiskboot": {
            "nochange_repack_byte_identical": True,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
