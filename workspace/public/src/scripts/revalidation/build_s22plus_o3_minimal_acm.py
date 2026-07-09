#!/usr/bin/env python3
"""Build the S22+ O3 direct-PID1 minimal generic-ACM candidate.

Host-only. The resulting AP is not authorized for live use until its exact
hashes and rollback conditions are pinned by a fresh one-shot exception.
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
import s22plus_o2_module_plan as o2
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


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/o3_minimal_acm_v0_1")
DEFAULT_INIT_SOURCE = Path("workspace/public/src/native-init/s22plus_init_o3_minimal_acm.c")
DEFAULT_DAEMON_SOURCE = Path("workspace/public/src/android/s22plus_o3_tty_control.c")
DEFAULT_LOADER_HEADER = Path("workspace/public/src/native-init/s22plus_o2_loader_core.h")
DEFAULT_METADATA = o2.DEFAULT_METADATA_DIR
DEFAULT_VENDOR_RAMDISK = m23.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = m23.DEFAULT_LZ4

MARKER = "S22_NATIVE_INIT_O3_MINIMAL_ACM"
DAEMON_RAMDISK = "s22plus_o3_tty_control"
EXPECTED_PLAN_COUNT = o2.EXPECTED_O3_MINIMAL_ACM_PLAN_COUNT
EXPECTED_PLAN_SHA256 = o2.EXPECTED_O3_MINIMAL_ACM_PLAN_TSV_SHA256


def compile_binary(
    *,
    label: str,
    source: Path,
    output: Path,
    include_dirs: list[Path],
    required_strings: list[str],
    build_dir: Path,
) -> dict[str, Any]:
    command = [
        "aarch64-linux-gnu-gcc",
        "-std=gnu11",
        "-static",
        "-Os",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-fno-stack-protector",
        "-fno-asynchronous-unwind-tables",
        "-fno-unwind-tables",
        "-Wl,--build-id=none",
        "-Wl,-z,noexecstack",
    ]
    for include_dir in include_dirs:
        command.extend(["-I", include_dir])
    command.extend([source, "-o", output])
    require_ok(run(command), f"compile O3 {label}")
    require_ok(run(["aarch64-linux-gnu-strip", "-s", output]), f"strip O3 {label}")

    file_result = run(["file", output])
    require_ok(file_result, f"file O3 {label}")
    readelf_result = run(["aarch64-linux-gnu-readelf", "-h", "-l", output])
    require_ok(readelf_result, f"readelf O3 {label}")
    objdump_result = run(["aarch64-linux-gnu-objdump", "-d", output])
    require_ok(objdump_result, f"objdump O3 {label}")
    file_text = (file_result.stdout + file_result.stderr).decode("utf-8", errors="replace")
    readelf_text = readelf_result.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump_result.stdout.decode("utf-8", errors="replace")
    if "ARM aarch64" not in file_text or "statically linked" not in file_text:
        raise SystemExit(f"O3 {label} is not a static AArch64 executable: {file_text.strip()}")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit(f"O3 {label} unexpectedly has an interpreter")
    if "svc" not in objdump_text:
        raise SystemExit(f"O3 {label} contains no syscall instruction")
    binary = output.read_bytes()
    missing = [value for value in required_strings if value.encode("ascii") not in binary]
    if missing:
        raise SystemExit(f"O3 {label} required strings missing: {missing}")

    (build_dir / f"{label}.file.txt").write_text(file_text, encoding="utf-8")
    (build_dir / f"{label}.readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / f"{label}.objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "command": [str(item) for item in command],
        "file": file_text.strip(),
        "required_strings": required_strings,
        "sha256": sha256_file(output),
        "size": output.stat().st_size,
        "no_interp": True,
    }


def verify_source_contract(init_source: Path, daemon_source: Path) -> dict[str, Any]:
    init_text = init_source.read_text(encoding="ascii")
    daemon_text = daemon_source.read_text(encoding="ascii")
    required_init = [
        "s22plus_o2_execute_module_plan",
        "s22plus_o2_scan_proc_modules",
        "S22PLUS_O2_BIND_GATE_COUNT",
        "/config/usb_gadget/g1/functions/acm.usb0",
        "/sys/devices/platform/soc/a600000.ssusb/mode",
        "a600000.dwc3",
        "/dev/ttyGS0",
        "execve(O3_DAEMON_PATH",
    ]
    forbidden_init = [
        "ss_acm",
        "functionfs",
        "ffs.adb",
        "max77705",
        "sysrq",
        "SYS_reboot",
        "/sys/module/eud/parameters/enable",
        "/system/bin/init",
        "system(",
    ]
    missing = [token for token in required_init if token not in init_text]
    present = [token for token in forbidden_init if token.lower() in init_text.lower()]
    if missing or present:
        raise SystemExit(f"O3 init source contract failed missing={missing} forbidden={present}")
    for token in ["O3 STATUS", "protocol_result=%s", "protocol_handled=%u", "S2O0"]:
        if token not in daemon_text:
            raise SystemExit(f"O3 daemon source contract missing: {token}")
    if "system(" in daemon_text:
        raise SystemExit("O3 daemon source contains system()")
    return {
        "init_required": required_init,
        "init_forbidden_absent": forbidden_init,
        "daemon_protocol": "S2O0-v1 with O3 STATUS and 128 echo requests",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--init-source", type=Path, default=DEFAULT_INIT_SOURCE)
    parser.add_argument("--daemon-source", type=Path, default=DEFAULT_DAEMON_SOURCE)
    parser.add_argument("--loader-header", type=Path, default=DEFAULT_LOADER_HEADER)
    parser.add_argument("--metadata-dir", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    init_source = resolve(root, args.init_source)
    daemon_source = resolve(root, args.daemon_source)
    loader_header = resolve(root, args.loader_header)
    metadata_dir = resolve(root, args.metadata_dir)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    plan_dir = build_dir / "plan"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    patched_unpack_dir = out_dir / "patched-unpack"
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, plan_dir, work_dir, nochange_dir, patched_unpack_dir, odin_dir):
        directory.mkdir(parents=True, exist_ok=True)

    source_contract = verify_source_contract(init_source, daemon_source)
    ensure_magiskboot(magiskboot, magisk_apk)
    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size}")

    metadata = o2.load_metadata(metadata_dir)
    o2.verify_fyg8_pins(metadata)
    plan = o2.build_plan(metadata, o2.O3_MINIMAL_ACM_ROOTS)
    o2.validate_plan_contract(metadata, plan)
    o2.verify_o3_minimal_acm_plan_identity(metadata, plan)
    plan_manifest = o2.write_outputs(root, plan_dir, metadata, plan)
    plan_tsv = plan_dir / "module-plan.tsv"
    plan_header = plan_dir / "module-plan.generated.h"
    if len(plan.modules) != EXPECTED_PLAN_COUNT or sha256_file(plan_tsv) != EXPECTED_PLAN_SHA256:
        raise SystemExit("O3 plan identity changed after writing build artifacts")

    vendor = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, build_dir)
    missing_vendor_modules = sorted(set(plan.modules) - set(vendor["ko_names"]))
    if missing_vendor_modules:
        raise SystemExit(f"O3 plan modules absent from stock vendor_boot: {missing_vendor_modules}")
    for name in ["modules.dep", "modules.softdep", "modules.load", "modules.load.recovery", "modules.alias"]:
        if vendor["metadata_hashes"].get(name) != metadata.metadata_hashes.get(name):
            raise SystemExit(f"vendor_boot metadata differs from O3 planner input: {name}")

    init_out = build_dir / "init"
    daemon_out = build_dir / DAEMON_RAMDISK
    init_info = compile_binary(
        label="o3-init",
        source=init_source,
        output=init_out,
        include_dirs=[loader_header.parent, plan_header.parent],
        required_strings=[
            MARKER,
            "version=%s",
            "0.1",
            "plan_count=%zu",
            "gadget_function=acm.usb0",
            "udc=a600000.dwc3",
            "/s22plus_o3_tty_control",
            "control-ready",
        ],
        build_dir=build_dir,
    )
    daemon_info = compile_binary(
        label="o3-control",
        source=daemon_source,
        output=daemon_out,
        include_dirs=[],
        required_strings=[
            "S2O0",
            "O3 STATUS",
            "S22_O3_CONTROL",
            "protocol_result=%s",
            "protocol_handled=%u",
        ],
        build_dir=build_dir,
    )

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "O3 no-change unpack")
    nochange_boot = out_dir / "boot_nochange_repack.img"
    run_in_dir([magiskboot, "repack", base_boot, nochange_boot], nochange_dir, "O3 no-change repack")
    nochange_sha = sha256_file(nochange_boot)
    if nochange_sha != base_sha:
        raise SystemExit(f"O3 no-change repack differs: {nochange_sha} != {base_sha}")

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "O3 unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "O3 extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch: {original_init_sha}")
    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"unexpected base ramdisk test rc: {cpio_test_before}")

    patch_init = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, "O3 replace /init")
    patch_daemon = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 750 {DAEMON_RAMDISK} {daemon_out}"],
        work_dir,
        "O3 add control daemon",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected patched ramdisk test rc: {cpio_test_after}")
    extracted_init = build_dir / "init.extracted"
    extracted_daemon = build_dir / f"{DAEMON_RAMDISK}.extracted"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, "O3 verify /init")
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {DAEMON_RAMDISK} {extracted_daemon}"],
        work_dir,
        "O3 verify control daemon",
    )
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit("O3 ramdisk /init differs from compiled artifact")
    if sha256_file(extracted_daemon) != sha256_file(daemon_out):
        raise SystemExit("O3 ramdisk control daemon differs from compiled artifact")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = out_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "O3 repack")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"O3 patched boot size mismatch: {boot_img.stat().st_size}")
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, "O3 unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit("O3 patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_boot_lz4(boot_img, boot_lz4)
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"O3 AP member mismatch: {members}")

    hashes = {
        "init_source": sha256_file(init_source),
        "daemon_source": sha256_file(daemon_source),
        "loader_header": sha256_file(loader_header),
        "plan_tsv": sha256_file(plan_tsv),
        "plan_header": sha256_file(plan_header),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
        "original_magisk_init": original_init_sha,
        "o3_init": sha256_file(init_out),
        "o3_control": sha256_file(daemon_out),
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
        "o3_init": init_out.stat().st_size,
        "o3_control": daemon_out.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    manifest = {
        "schema": "s22plus_o3_minimal_acm_build_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": o2.TARGET,
        "purpose": "O3 direct-PID1 stock-loader-parity generic configfs ACM control proof",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot in-place repack; replace /init and add one static control daemon",
            "kernel_changed": False,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": False,
            "reboot_syscall": False,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_source": "stock vendor_boot /lib/modules",
            "configfs_runtime_gadget": "one generic acm.usb0 function",
            "udc_binding": "a600000.dwc3 only",
            "sysfs_write_allowlist": ["/sys/devices/platform/soc/a600000.ssusb/mode=peripheral"],
            "eud_enable": False,
            "sec_debug_trigger": False,
            "pmic_typec_power_write": False,
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "base_boot": display_path(root, base_boot),
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": sizes,
        "plan": {
            "module_count": len(plan.modules),
            "tsv_sha256": hashes["plan_tsv"],
            "header_sha256": hashes["plan_header"],
            "modules": list(plan.modules),
            "roots": list(plan.requested_roots),
            "tolerated_unresolved_softdeps": {
                key: list(value) for key, value in plan.tolerated_unresolved_softdeps.items()
            },
            "manifest": plan_manifest,
        },
        "vendor": {
            "ramdisk_sha256": sha256_file(vendor_ramdisk),
            "ko_count": vendor["ko_count"],
            "all_plan_modules_present": True,
            "metadata_hashes": vendor["metadata_hashes"],
        },
        "source_contract": source_contract,
        "init": init_info,
        "control": daemon_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "added_entry": DAEMON_RAMDISK,
            "entry_modes": {"init": "750", DAEMON_RAMDISK: "750"},
            "module_files_injected": 0,
        },
        "magiskboot": {
            "nochange_repack_byte_identical": True,
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patch_output": patch_init + "\n" + patch_daemon,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii"
    )
    (out_dir / "sizes.txt").write_text(
        "".join(f"{value:12d}  {key}\n" for key, value in sorted(sizes.items())), encoding="ascii"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
