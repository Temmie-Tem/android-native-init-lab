#!/usr/bin/env python3
"""Guarded S22+ M5B mount/reboot native-init live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M5B tests the front of M5 without the USB module/configfs gadget chain:
freestanding C PID1, virtual filesystem mounts, kmsg marker, then
reboot("download"). If download mode reappears after the candidate flash, the
freestanding C + VFS mount path reached the reboot request. If no transport
appears, manual download-mode entry is required before rollback.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_MEMBER,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    adb_rows,
    append_log,
    collect_android_pstore,
    flash_ap,
    host_snapshot,
    odin_devices,
    poll_android,
    repo_root,
    require_current_android,
    resolve,
    run,
    utc_now,
    verify_ap,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability, verify_current_boot_hash


LIVE_ACK_TOKEN = "S22PLUS-M5B-MOUNT-REBOOT-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M5B-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M5B_AP_SHA256 = "872de3ee417eebbe8f55c14d226eaefe5e06d5989ffe96176b1bb02994793a59"
EXPECTED_M5B_BOOT_SHA256 = "21a61c84d273390a3681d029977ff6150991036568aa455a0a4879ff24590239"
EXPECTED_M5B_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M5B_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M5B_INIT_SHA256 = "accfc6f5e04d7d302ee17c6e4ce93ee14240ebdbb70274424934805e542b9bac"
EXPECTED_M5B_MARKER = "S22_NATIVE_INIT_MOUNT_REBOOT_M5B"

DEFAULT_M5B_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m5b_mount_reboot_v0_1/odin4/AP.tar.md5")
DEFAULT_M5B_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m5b_mount_reboot_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested
    else:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
        run_dir = DEFAULT_RUN_ROOT / f"s22plus_m5b_mount_reboot_live_gate_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M5B mount-reboot native-init boot-only",
        EXPECTED_M5B_AP_SHA256,
        EXPECTED_M5B_BOOT_SHA256,
        EXPECTED_M5B_BASE_BOOT_SHA256,
        EXPECTED_M5B_KERNEL_SHA256,
        EXPECTED_M5B_INIT_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "mount only runtime virtual filesystems",
        "no module insertion",
        "no USB gadget setup",
        "`reboot(..., \"download\")`",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M5B live authorization markers: {missing}")


def verify_m5b_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M5B manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    m5b_init = data.get("m5b_init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m5b_manifest_path={path}")
    append_log(log_path, f"m5b_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m5b_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m5b_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m5b_manifest_init_file={m5b_init.get('file', '')}")
    if hashes.get("ap_tar_md5") != EXPECTED_M5B_AP_SHA256:
        raise SystemExit("M5B manifest AP hash does not match expected M5B AP")
    if hashes.get("boot_img") != EXPECTED_M5B_BOOT_SHA256:
        raise SystemExit("M5B manifest boot image hash does not match expected M5B boot image")
    if hashes.get("base_boot") != EXPECTED_M5B_BASE_BOOT_SHA256:
        raise SystemExit("M5B manifest base boot hash mismatch")
    if hashes.get("kernel") != EXPECTED_M5B_KERNEL_SHA256:
        raise SystemExit("M5B manifest kernel hash mismatch")
    if hashes.get("m5b_init") != EXPECTED_M5B_INIT_SHA256:
        raise SystemExit("M5B manifest init hash mismatch")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M5B manifest tar members mismatch: {tar_members_seen!r}")
    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace only ramdisk /init",
        "runtime": "freestanding-raw-syscall",
        "glibc_static_startup": False,
        "mkbootimg_from_scratch": False,
        "first_candidate_action": "mount-virtual-filesystems-then-reboot-download",
        "module_insertions": False,
        "configfs_runtime_gadget": False,
        "usb_gadget_setup": False,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "watchdog": "not-touched",
        "on_reboot_syscall_return": "infinite-park",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M5B manifest {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit(f"M5B replaced ramdisk entry mismatch: {ramdisk.get('replaced_entry')!r}")
    required_strings = set(m5b_init.get("required_strings", []))
    for required in [
        EXPECTED_M5B_MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        "mounts=dev,proc,sys,config",
        "no_modules=1",
        "no_usb_gadget=1",
        "reboot_download=1",
        "download",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M5B required string missing from manifest: {required}")


def wait_for_odin_absent(odin: Path, log_path: Path, label: str, wait_sec: int) -> bool:
    deadline = time.monotonic() + wait_sec
    while True:
        devices = odin_devices(odin, log_path, label)
        if not devices:
            append_log(log_path, f"{label}_odin_absent=1")
            return True
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices while waiting for disconnect: {devices}")
        if time.monotonic() >= deadline:
            append_log(log_path, f"{label}_odin_absent=0 still_present={devices}")
            return False
        time.sleep(1.0)


def observe_until_odin(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> str | None:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m5b_self_download_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, f"m5b_self_download_seen=1 device={devices[0]}")
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M5B observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"m5b_candidate_adb_rows={rows}")
        time.sleep(1.0)
    append_log(log_path, "m5b_self_download_seen=0")
    return None


def rollback_from_download(odin: Path, rollback_ap: Path, run_dir: Path, log_path: Path, rollback_target: str, android_wait_sec: int) -> int:
    devices = odin_devices(odin, log_path, "rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"rollback-only requires exactly one Odin device, got {devices}")
    rollback_rc = flash_ap(odin, rollback_ap, devices[0], log_path, f"{rollback_target}_rollback")
    if rollback_rc != 0:
        return rollback_rc or 5
    serial = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if serial is None:
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M5B_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m5b-ap", type=Path, default=DEFAULT_M5B_AP)
    parser.add_argument("--m5b-manifest", type=Path, default=DEFAULT_M5B_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--self-download-wait-sec", type=int, default=60)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    if args.live and args.rollback_from_download:
        raise SystemExit("--live and --rollback-from-download are mutually exclusive")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m5b_mount_reboot_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m5b mount-reboot live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m5b_ap = resolve(root, args.m5b_ap)
    m5b_manifest = resolve(root, args.m5b_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m5b_ap, EXPECTED_M5B_AP_SHA256, "m5b_candidate", log_path)
    verify_m5b_manifest(m5b_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M5B rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_current_boot_hash(log_path, selected_serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M5B candidate, rollback APs, AGENTS exception, Android stability, and boot hash verified; log={log_path}")
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M5B candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m5b_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M5B candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        print("M5B original Odin device did not disconnect; rolling back without proof.", file=sys.stderr)
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            return 4
        rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback_no_disconnect")
        if rollback_rc != 0:
            return rollback_rc or 5
        post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
        if post_rollback_serial is None:
            return 6
        collect_android_pstore(run_dir, log_path, "post_rollback_no_disconnect", post_rollback_serial, marker=EXPECTED_M5B_MARKER)
        append_log(log_path, "m5b_result=no-proof-original-download-never-disconnected")
        return 7

    print("M5B candidate flashed. Waiting for mount/reboot beacon self-download.")
    rollback_device = observe_until_odin(run_dir, log_path, args.self_download_wait_sec, odin)
    if rollback_device is None:
        print(
            "M5B self-download did not appear. Enter download mode manually and run --rollback-from-download.",
            file=sys.stderr,
        )
        return 4

    rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback")
    if rollback_rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            rollback_rc = flash_ap(odin, stock_rollback_ap, fallback_device, log_path, "stock_fallback")
    if rollback_rc != 0:
        return rollback_rc or 5

    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
    if post_rollback_serial is None:
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M5B_MARKER)
    print(f"M5B live gate completed with self-download and rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
