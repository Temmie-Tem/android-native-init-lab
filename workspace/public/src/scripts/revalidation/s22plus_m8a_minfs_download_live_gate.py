#!/usr/bin/env python3
"""Guarded S22+ M8A minimal-fs timed-download native-init live gate.

Default dry-run and live modes require a SHA-pinned AGENTS.md exception plus a
recovered rooted Android baseline. --offline-check verifies only the host-built
M8A package and rollback APs without touching any device.

M8A is not a module or USB proof. The expected live proof is automatic return
to Samsung download mode after direct native PID1 mounts only dev/proc/sys/run
and requests reboot("download"). The helper must not count the original
candidate Odin endpoint as proof: it waits for that endpoint to disconnect,
then treats a later Odin endpoint as the candidate's self-download result.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

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
from s22plus_m5_usb_acm_live_gate import (
    verify_android_stability,
    verify_current_boot_hash,
)


LIVE_ACK_TOKEN = "S22PLUS-M8A-MINFS-DOWNLOAD-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M8A-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M8A_AP_SHA256 = "c97d29e38fe3293ad145a7743b61ae5fddae8f1b028e619dcd56e2f640de3c19"
EXPECTED_M8A_BOOT_SHA256 = "8a816fb3bf8e644de4bbe0409f6cf94fd06a33d16e672569c130535ce139ad44"
EXPECTED_M8A_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M8A_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M8A_INIT_SHA256 = "aac2a03a2b20e72c3d69cfa3c4d3e5c045c817c293c347ac2aaf81f1bfb029b1"
EXPECTED_M8A_SOURCE_SHA256 = "830f95cc0f4237f10f2e132ead873a69f543134a503816fa2281205d41362538"
EXPECTED_M8A_MARKER = "S22_NATIVE_INIT_M8A_MINFS_DOWNLOAD"

DEFAULT_M8A_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m8a_minfs_download_v0_1/odin4/AP.tar.md5")
DEFAULT_M8A_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m8a_minfs_download_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m8a_minfs_download_live_gate_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M8A minimal-fs timed-download native-init boot-only",
        EXPECTED_M8A_AP_SHA256,
        EXPECTED_M8A_BOOT_SHA256,
        EXPECTED_M8A_BASE_BOOT_SHA256,
        EXPECTED_M8A_KERNEL_SHA256,
        EXPECTED_M8A_INIT_SHA256,
        EXPECTED_M8A_SOURCE_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "mount only `/dev`, `/proc`, `/sys`, and `/run`",
        "no module insertion",
        "no configfs",
        "automatic Samsung download-mode return",
        "wait for the original Odin endpoint to disconnect",
        "manual download-mode rollback",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M8A live authorization markers: {missing}")


def verify_m8a_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M8A manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    init_info = data.get("m8a_init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m8a_manifest_path={path}")
    append_log(log_path, f"m8a_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m8a_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m8a_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")

    expected_hashes = {
        "ap_tar_md5": EXPECTED_M8A_AP_SHA256,
        "boot_img": EXPECTED_M8A_BOOT_SHA256,
        "base_boot": EXPECTED_M8A_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M8A_KERNEL_SHA256,
        "m8a_init": EXPECTED_M8A_INIT_SHA256,
        "source": EXPECTED_M8A_SOURCE_SHA256,
        "nochange_repack_boot": EXPECTED_M8A_BASE_BOOT_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M8A manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M8A manifest tar members mismatch: {tar_members_seen!r}")

    expected_safety: dict[str, Any] = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace only ramdisk /init",
        "runtime": "freestanding-raw-syscall",
        "glibc_static_startup": False,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": "download-after-minimal-fs",
        "host_commanded_reboot_download": False,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_insertions": False,
        "module_binary_injection": False,
        "module_list_files_injected_into_boot_ramdisk": 0,
        "configfs_runtime_gadget": False,
        "udc_binding": False,
        "usb_role_force": False,
        "watchdog": "not-touched",
        "on_reboot_syscall_return": "infinite-park",
    }
    for key, expected in expected_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M8A manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")

    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M8A manifest did not replace /init")
    if ramdisk.get("only_intended_entry_change") != "init":
        raise SystemExit("M8A manifest intended ramdisk change is not only /init")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M8A must not inject vendor module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M8A must not inject module-list files into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M8A_MARKER,
        "version=0.1",
        "runtime=freestanding",
        "raw_syscalls=1",
        "minfs=dev,proc,sys,run",
        "no_modules=1",
        "no_configfs=1",
        "no_usb_acm=1",
        "no_gadget_setup=1",
        "auto_reboot_download_after_minfs=1",
        "phase=timed_download",
        "download",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M8A required string missing from manifest: {required}")
    forbidden_strings = set(init_info.get("forbidden_strings", []))
    for forbidden in [
        "ld-linux",
        "libc.so",
        "/lib/modules",
        "finit_module",
        "modules.load",
        "s22plus_m8_delta_batch",
        "ttyGS0",
        "ss_acm.0",
        "usb_gadget",
        "/config",
    ]:
        if forbidden not in forbidden_strings:
            raise SystemExit(f"M8A forbidden-string gate missing from manifest: {forbidden}")


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
        label = f"m8a_self_download_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, f"m8a_self_download_seen=1 device={devices[0]}")
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M8A observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"m8a_candidate_adb_rows={rows}")
        time.sleep(1.0)
    append_log(log_path, "m8a_self_download_seen=0")
    return None


def rollback_from_download(
    odin: Path,
    rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
) -> int:
    devices = odin_devices(odin, log_path, "rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"rollback-only requires exactly one Odin device, got {devices}")
    rollback_rc = flash_ap(odin, rollback_ap, devices[0], log_path, f"{rollback_target}_rollback")
    if rollback_rc != 0:
        return rollback_rc or 5
    serial = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if serial is None:
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M8A_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m8a-ap", type=Path, default=DEFAULT_M8A_AP)
    parser.add_argument("--m8a-manifest", type=Path, default=DEFAULT_M8A_MANIFEST)
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
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(1 for enabled in (args.offline_check, args.live, args.rollback_from_download) if enabled)
    if modes > 1:
        raise SystemExit("--offline-check, --live, and --rollback-from-download are mutually exclusive")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m8a_minfs_download_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m8a minfs download live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m8a_ap = resolve(root, args.m8a_ap)
    m8a_manifest = resolve(root, args.m8a_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap(m8a_ap, EXPECTED_M8A_AP_SHA256, "m8a_candidate", log_path)
    verify_m8a_manifest(m8a_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M8A candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M8A rollback-from-download completed rc={rc}; log={log_path}")
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
        print(
            "dry-run ok: M8A candidate, rollback APs, AGENTS exception, Android stability, "
            f"and boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M8A candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m8a_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M8A candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        print(
            "M8A candidate flash completed but the original Odin device did not disconnect; "
            "rolling back without claiming self-download proof.",
            file=sys.stderr,
        )
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            print(f"rollback download mode unavailable after no-disconnect; manual recovery required. log={log_path}", file=sys.stderr)
            return 4
        rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback_no_disconnect")
        if rollback_rc != 0:
            return rollback_rc or 5
        post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
        if post_rollback_serial is None:
            return 6
        append_log(log_path, "m8a_result=no-proof-original-download-never-disconnected")
        collect_android_pstore(run_dir, log_path, "post_rollback_no_disconnect", post_rollback_serial, marker=EXPECTED_M8A_MARKER)
        return 7

    print("M8A candidate flashed. Waiting for minimal-fs timed-download self-return.")
    rollback_device = observe_until_odin(run_dir, log_path, args.self_download_wait_sec, odin)
    if rollback_device is None:
        print("M8A self-download did not appear; enter download mode manually and run --rollback-from-download.", file=sys.stderr)
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
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M8A_MARKER)
    print(f"M8A live gate completed with minimal-fs timed-download self-return and rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
