#!/usr/bin/env python3
"""Build the S22+ O1 stock-first-stage Magisk overlay control candidate.

Host-only. The builder starts from the known-booting FYG8 Magisk boot image,
keeps its kernel and /init, and adds exactly one overlay rc, one bounded service
script, and the O0-proven framed tty echo daemon. It does not touch a device.
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
from s22plus_o0_stock_usb_control import build_daemon


RUN_ID = "V3404"
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MAGISKBOOT_SHA256 = "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/o1_magisk_overlay_v0_1")
DEFAULT_RC = Path("workspace/public/src/android/s22plus_o1_control.rc")
DEFAULT_SERVICE = Path("workspace/public/src/android/s22plus_o1_service.sh")

RC_ENTRY = "overlay.d/s22plus_o1_control.rc"
SERVICE_ENTRY = "overlay.d/sbin/s22plus_o1_service.sh"
DAEMON_ENTRY = "overlay.d/sbin/s22plus_o1_tty_echo"
INTENDED_ENTRIES = [RC_ENTRY, SERVICE_ENTRY, DAEMON_ENTRY]
EXPECTED_ENTRY_MODES = {
    RC_ENTRY: "-rw-r--r--",
    SERVICE_ENTRY: "-rwxr-x---",
    DAEMON_ENTRY: "-rwxr-x---",
}


def cpio_result(magiskboot: Path, ramdisk: Path, command: str, *, cwd: Path) -> tuple[int, str]:
    result = run([magiskboot, "cpio", ramdisk, command], cwd=cwd)
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    return result.returncode, text


def parse_cpio_listing(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in text.splitlines():
        columns = line.split("\t")
        if len(columns) < 2 or not columns[0].startswith(("-", "d", "l")):
            continue
        entries[columns[-1]] = columns[0]
    return entries


def require_source_contract(rc_path: Path, service_path: Path) -> dict[str, Any]:
    rc = rc_path.read_text(encoding="utf-8")
    service = service_path.read_text(encoding="utf-8")
    rc_required = [
        "on property:sys.usb.configured=configured",
        "start s22plus_o1_control",
        "service s22plus_o1_control ${MAGISKTMP}/s22plus_o1_service.sh ${MAGISKTMP}/s22plus_o1_tty_echo",
        "disabled",
        "oneshot",
    ]
    rc_prohibited = ["stop DR-daemon", "write /sys/", "write /config/", "insmod", "reboot"]
    service_required = [
        'STOCK_SERVICE="DR-daemon"',
        'STOCK_PROCESS="ddexe"',
        'MARKER="/dev/.s22plus_o1_control_once"',
        'STATUS="/dev/.s22plus_o1_status"',
        "setprop ctl.stop",
        "setprop ctl.start",
        "wait_stock_state stopped",
        "wait_stock_state running",
        '"$DAEMON"',
        "--device /dev/ttyGS0",
        "--max-requests",
        "--idle-timeout-ms",
        "result=pass\\ndaemon_rc=0\\nrestore_rc=0",
    ]
    service_prohibited = ["/data/", "/config/", "/sys/", "insmod", "modprobe", "reboot", "dd if=", "dd of="]
    state = {
        "rc_required": {token: token in rc for token in rc_required},
        "rc_prohibited": {token: token in rc for token in rc_prohibited},
        "service_required": {token: token in service for token in service_required},
        "service_prohibited": {token: token in service for token in service_prohibited},
    }
    ready = (
        all(state["rc_required"].values())
        and not any(state["rc_prohibited"].values())
        and all(state["service_required"].values())
        and not any(state["service_prohibited"].values())
    )
    if not ready:
        raise SystemExit(f"O1 overlay source contract failed: {state}")
    state["ready"] = True
    return state


def add_and_verify_entry(
    magiskboot: Path,
    ramdisk: Path,
    *,
    entry: str,
    mode: str,
    source: Path,
    extract_dir: Path,
    cwd: Path,
) -> dict[str, Any]:
    run_in_dir([magiskboot, "cpio", ramdisk, f"add {mode} {entry} {source}"], cwd, f"add {entry}")
    extracted = extract_dir / entry.replace("/", "_")
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract {entry} {extracted}"], cwd, f"extract {entry}")
    if sha256_file(extracted) != sha256_file(source):
        raise SystemExit(f"cpio entry verification mismatch: {entry}")
    return {
        "entry": entry,
        "mode": mode,
        "source": display_path(repo_root(), source),
        "sha256": sha256_file(source),
        "size": source.stat().st_size,
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    safety = manifest.get("safety") or {}
    ramdisk = manifest.get("ramdisk") or {}
    if manifest.get("target") != EXPECTED_TARGET:
        reasons.append("target-mismatch")
    expected_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "base_is_known_booting_magisk_boot": True,
        "stock_first_stage_preserved": True,
        "stock_magisk_init_preserved": True,
        "kernel_preserved": True,
        "configfs_write": False,
        "sysfs_write": False,
        "module_insertions": False,
        "reboot_request": False,
        "persistent_partition_mount": False,
    }
    for key, expected in expected_safety.items():
        if safety.get(key) != expected:
            reasons.append(f"safety-{key}-mismatch")
    if manifest.get("tar_members") != ["boot.img.lz4"]:
        reasons.append("tar-members-not-boot-only")
    if ramdisk.get("added_entries") != INTENDED_ENTRIES:
        reasons.append("ramdisk-added-entries-mismatch")
    if ramdisk.get("replaced_entries") != []:
        reasons.append("ramdisk-replaced-entry-present")
    listing_diff = ramdisk.get("listing_diff") or {}
    if listing_diff.get("added") != sorted(INTENDED_ENTRIES):
        reasons.append("ramdisk-listing-added-mismatch")
    if listing_diff.get("removed") != []:
        reasons.append("ramdisk-listing-removed-entry-present")
    if listing_diff.get("entry_modes") != EXPECTED_ENTRY_MODES:
        reasons.append("ramdisk-listing-mode-mismatch")
    if manifest.get("hashes", {}).get("base_boot") != EXPECTED_BASE_BOOT_SHA256:
        reasons.append("base-boot-hash-mismatch")
    if manifest.get("hashes", {}).get("original_magisk_init_before") != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        reasons.append("original-init-before-mismatch")
    if manifest.get("hashes", {}).get("original_magisk_init_after") != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        reasons.append("original-init-after-mismatch")
    return reasons


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    odin = resolve(root, args.odin)
    rc_path = resolve(root, args.rc)
    service_path = resolve(root, args.service)

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force: {out_dir}")
        shutil.rmtree(out_dir)
    build_dir = out_dir / "build"
    work_dir = out_dir / "magiskboot-work"
    nochange_dir = out_dir / "nochange-probe"
    verify_dir = out_dir / "verify"
    odin_dir = out_dir / "odin4"
    for directory in (build_dir, work_dir, nochange_dir, verify_dir, odin_dir):
        directory.mkdir(parents=True)

    ensure_magiskboot(magiskboot, magisk_apk)
    if sha256_file(magiskboot) != EXPECTED_MAGISKBOOT_SHA256:
        raise SystemExit("magiskboot SHA mismatch")
    if sha256_file(base_boot) != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit("known-good Magisk base boot SHA mismatch")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit("known-good Magisk base boot size mismatch")
    source_contract = require_source_contract(rc_path, service_path)
    daemon_build = build_daemon(build_dir / "daemon", args.cc)
    daemon_path = resolve(root, Path(daemon_build["path"]))

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "O1 no-change unpack")
    nochange_boot = out_dir / "boot_nochange_repack.img"
    run_in_dir([magiskboot, "repack", base_boot, nochange_boot], nochange_dir, "O1 no-change repack")
    if sha256_file(nochange_boot) != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit("O1 no-change repack is not byte-identical")

    unpack_output = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, "O1 unpack base boot")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    original_init = verify_dir / "init.before"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, "O1 extract original init")
    if sha256_file(original_init) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit("O1 original Magisk init SHA mismatch")
    if cpio_result(magiskboot, ramdisk, "test", cwd=work_dir)[0] != 1:
        raise SystemExit("O1 base ramdisk is not recognized as Magisk ramdisk")
    before_list_rc, before_list_text = cpio_result(magiskboot, ramdisk, "ls -r /", cwd=work_dir)
    if before_list_rc != 0:
        raise SystemExit("O1 could not list base ramdisk")
    before_listing = parse_cpio_listing(before_list_text)
    (verify_dir / "ramdisk_listing.before.txt").write_text(before_list_text, encoding="utf-8")
    for entry in INTENDED_ENTRIES:
        if cpio_result(magiskboot, ramdisk, f"exists {entry}", cwd=work_dir)[0] == 0:
            raise SystemExit(f"O1 entry already exists in base ramdisk: {entry}")

    ramdisk_before = verify_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    entries = [
        add_and_verify_entry(
            magiskboot,
            ramdisk,
            entry=RC_ENTRY,
            mode="644",
            source=rc_path,
            extract_dir=verify_dir,
            cwd=work_dir,
        ),
        add_and_verify_entry(
            magiskboot,
            ramdisk,
            entry=SERVICE_ENTRY,
            mode="750",
            source=service_path,
            extract_dir=verify_dir,
            cwd=work_dir,
        ),
        add_and_verify_entry(
            magiskboot,
            ramdisk,
            entry=DAEMON_ENTRY,
            mode="750",
            source=daemon_path,
            extract_dir=verify_dir,
            cwd=work_dir,
        ),
    ]
    if cpio_result(magiskboot, ramdisk, "test", cwd=work_dir)[0] != 1:
        raise SystemExit("O1 patched ramdisk lost Magisk structure")
    cpio_list_rc, cpio_list = cpio_result(magiskboot, ramdisk, "ls -r /", cwd=work_dir)
    if cpio_list_rc != 0:
        raise SystemExit("O1 patched ramdisk listing is incomplete")
    after_listing = parse_cpio_listing(cpio_list)
    listing_diff = {
        "added": sorted(set(after_listing) - set(before_listing)),
        "removed": sorted(set(before_listing) - set(after_listing)),
        "entry_modes": {entry: after_listing.get(entry) for entry in INTENDED_ENTRIES},
    }
    if listing_diff != {
        "added": sorted(INTENDED_ENTRIES),
        "removed": [],
        "entry_modes": EXPECTED_ENTRY_MODES,
    }:
        raise SystemExit(f"O1 ramdisk listing delta mismatch: {listing_diff}")
    (verify_dir / "ramdisk_listing.after.txt").write_text(cpio_list, encoding="utf-8")

    init_after = verify_dir / "init.after"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {init_after}"], work_dir, "O1 extract init after")
    if sha256_file(init_after) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit("O1 changed Magisk /init")
    ramdisk_after = verify_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)

    boot_img = out_dir / "boot.img"
    repack_output = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, "O1 repack boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit("O1 boot image size mismatch")
    patched_unpack = out_dir / "patched-unpack"
    patched_unpack.mkdir()
    patched_unpack_output = run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack, "O1 unpack patched boot")
    if sha256_file(patched_unpack / "kernel") != sha256_file(kernel):
        raise SystemExit("O1 patched boot kernel changed")
    patched_init = verify_dir / "init.patched-boot"
    run_in_dir(
        [magiskboot, "cpio", patched_unpack / "ramdisk.cpio", f"extract init {patched_init}"],
        patched_unpack,
        "O1 extract patched boot init",
    )
    if sha256_file(patched_init) != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit("O1 patched boot Magisk /init changed")
    for entry in INTENDED_ENTRIES:
        if cpio_result(magiskboot, patched_unpack / "ramdisk.cpio", f"exists {entry}", cwd=patched_unpack)[0] != 0:
            raise SystemExit(f"O1 patched boot missing overlay entry: {entry}")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"O1 AP tar member mismatch: {members}")

    odin_parse = ""
    if not args.no_odin_parse_gate and odin.is_file():
        result = run([odin, "-a", ap_md5, "-d", "/dev/bus/usb/999/999"])
        odin_parse = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        (odin_dir / "parse_dry_run_invalid_device.txt").write_text(odin_parse, encoding="utf-8")

    hashes = {
        "base_boot": sha256_file(base_boot),
        "nochange_repack_boot": sha256_file(nochange_boot),
        "magiskboot": sha256_file(magiskboot),
        "original_magisk_init_before": sha256_file(original_init),
        "original_magisk_init_after": sha256_file(init_after),
        "kernel_before": sha256_file(kernel),
        "kernel_after": sha256_file(patched_unpack / "kernel"),
        "overlay_rc": sha256_file(rc_path),
        "overlay_service": sha256_file(service_path),
        "o0_daemon": sha256_file(daemon_path),
        "ramdisk_before": sha256_file(ramdisk_before),
        "ramdisk_after": sha256_file(ramdisk_after),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    manifest: dict[str, Any] = {
        "schema": "s22plus_o1_magisk_overlay_build_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": RUN_ID,
        "target": EXPECTED_TARGET,
        "purpose": "stock-first-stage early-boot O0 protocol over existing FYG8 ACM",
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; add three overlay.d entries only",
            "stock_first_stage_preserved": True,
            "stock_magisk_init_preserved": True,
            "kernel_preserved": True,
            "mkbootimg_from_scratch": False,
            "configfs_write": False,
            "sysfs_write": False,
            "active_gadget_change": False,
            "module_insertions": False,
            "reboot_request": False,
            "persistent_partition_mount": False,
            "dr_daemon_handoff": "bounded-stop-run-restore-inside-service-script",
        },
        "runtime_contract": {
            "trigger": "property:sys.usb.configured=configured",
            "stock_tty_service": "DR-daemon",
            "stock_tty_process": "ddexe",
            "device_tty": "/dev/ttyGS0",
            "host_tty_expected": "/dev/ttyACM0",
            "protocol": "O0 S2O0 v1 framed echo",
            "max_requests": 128,
            "idle_timeout_ms": 180000,
            "one_shot_marker": "/dev/.s22plus_o1_control_once",
            "volatile_result_file": "/dev/.s22plus_o1_status",
            "service_restore_required_for_success": True,
        },
        "source_contract": source_contract,
        "paths": {
            "out_dir": display_path(root, out_dir),
            "base_boot": display_path(root, base_boot),
            "magiskboot": display_path(root, magiskboot),
            "overlay_rc": display_path(root, rc_path),
            "overlay_service": display_path(root, service_path),
            "o0_daemon_source": "workspace/public/src/android/s22plus_o0_tty_echo.c",
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
        },
        "hashes": hashes,
        "sizes": {
            "base_boot": base_boot.stat().st_size,
            "boot_img": boot_img.stat().st_size,
            "boot_img_lz4": boot_lz4.stat().st_size,
            "ap_tar_md5": ap_md5.stat().st_size,
            "ramdisk_before": ramdisk_before.stat().st_size,
            "ramdisk_after": ramdisk_after.stat().st_size,
        },
        "ramdisk": {
            "added_entries": INTENDED_ENTRIES,
            "replaced_entries": [],
            "entries": entries,
            "listing_diff": listing_diff,
            "cpio_test_before_rc": 1,
            "cpio_test_after_rc": 1,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
        "magiskboot": {
            "unpack_output": unpack_output,
            "repack_output": repack_output,
            "patched_unpack_output": patched_unpack_output,
            "nochange_repack_byte_identical": True,
        },
        "odin_invalid_device_parse_gate": odin_parse,
    }
    reasons = validate_manifest(manifest)
    if reasons:
        raise SystemExit(f"O1 manifest validation failed: {reasons}")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text(
        "".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())),
        encoding="ascii",
    )
    if not getattr(args, "quiet", False):
        print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--rc", type=Path, default=DEFAULT_RC)
    parser.add_argument("--service", type=Path, default=DEFAULT_SERVICE)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-odin-parse-gate", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    build(parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
