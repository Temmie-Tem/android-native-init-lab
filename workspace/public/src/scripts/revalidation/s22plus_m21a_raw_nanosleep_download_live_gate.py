#!/usr/bin/env python3
"""Guarded S22+ M21A raw nanosleep-download native-init live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M21A is the post-M20A floor discriminator. Its first runtime action is a raw
arm64 nanosleep(90s) syscall, followed only by a raw reboot(2) syscall
requesting Samsung download mode. The dwell makes the old helper-only
"later Odin endpoint" inference testable: early Odin or operator intervention
is no proof, not a pass.
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
    adb_shell,
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


LIVE_ACK_TOKEN = "S22PLUS-M21A-RAW-NANOSLEEP-DOWNLOAD-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M21A-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M21A_LABEL = "M21A_RAW_NANOSLEEP_DOWNLOAD"
EXPECTED_M21A_AP_SHA256 = "d1949a56c60c71498d68753d2ffd6064719fafce1ad0e3959ebb8a4255bb6c79"
EXPECTED_M21A_BOOT_SHA256 = "61d7dc9818b79c810b30370edfe4df2b55ec451588defb48458fefae9c6c00a5"
EXPECTED_M21A_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M21A_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M21A_INIT_SHA256 = "10f525760b170cba4ec55d7fd4955c466601253258371cb571eb45515bd9cf30"
EXPECTED_M21A_SOURCE_SHA256 = "300ed990c8ea476c3744e18327ae08277c0d27dc443e99245aeecba457968c4f"
EXPECTED_M21A_MARKER = "S22_NATIVE_INIT_M21A_RAW_NANOSLEEP_DOWNLOAD"
EXPECTED_DWELL_SEC = 90

DEFAULT_M21A_AP = Path("workspace/private/outputs/s22plus_native_init/m21a_raw_nanosleep_download_v0_1/odin4/AP.tar.md5")
DEFAULT_M21A_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m21a_raw_nanosleep_download_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m21a_raw_nanosleep_download_live_gate_{stamp}")
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
        "S22+ M21A raw nanosleep-download floor discriminator native-init boot-only",
        EXPECTED_M21A_AP_SHA256,
        EXPECTED_M21A_BOOT_SHA256,
        EXPECTED_M21A_BASE_BOOT_SHA256,
        EXPECTED_M21A_KERNEL_SHA256,
        EXPECTED_M21A_INIT_SHA256,
        EXPECTED_M21A_SOURCE_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_M21A_LABEL,
        "nanosleep({90,0}, NULL)",
        "no Odin endpoint before the 90 second dwell threshold",
        "host-observed download mode only after dwell and within grace",
        "operator manual download-mode entry",
        "M21A and does not authorize M20B",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M21A live authorization markers: {missing}")


def verify_m21a_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M21A manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    init_info = data.get("init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m21a_manifest_path={path}")
    append_log(log_path, f"m21a_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m21a_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m21a_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m21a_manifest_init_file={init_info.get('file', '')}")

    required_hashes = {
        "ap_tar_md5": EXPECTED_M21A_AP_SHA256,
        "boot_img": EXPECTED_M21A_BOOT_SHA256,
        "base_boot": EXPECTED_M21A_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M21A_KERNEL_SHA256,
        "init": EXPECTED_M21A_INIT_SHA256,
        "source": EXPECTED_M21A_SOURCE_SHA256,
    }
    for key, expected in required_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M21A manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M21A manifest tar members mismatch: {tar_members_seen!r}")

    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace only ramdisk /init",
        "mkbootimg_from_scratch": False,
        "runtime": "raw-assembly",
        "glibc_static_startup": False,
        "no_android_or_magisk_handoff": True,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_insertions": False,
        "module_binary_injection": False,
        "module_list_files_injected_into_boot_ramdisk": 0,
        "configfs_runtime_gadget": False,
        "udc_binding": False,
        "usb_role_force": False,
        "watchdog": "not-touched",
        "kmsg_marker_write": False,
        "pre_reboot_dwell_sec": EXPECTED_DWELL_SEC,
        "pre_reboot_syscalls": ["nanosleep"],
        "auto_reboot": "download",
        "on_reboot_syscall_return": "infinite-park",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M21A manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M21A manifest did not replace /init")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M21A must not inject module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M21A must not inject module-list files into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [EXPECTED_M21A_MARKER, f"nanosleep_sec={EXPECTED_DWELL_SEC}", "download"]:
        if required not in required_strings:
            raise SystemExit(f"M21A required string missing from manifest: {required}")
    if init_info.get("dwell_sec") != EXPECTED_DWELL_SEC:
        raise SystemExit(f"M21A init dwell mismatch: {init_info.get('dwell_sec')!r}")
    if init_info.get("svc_count") != 2:
        raise SystemExit(f"M21A init svc count mismatch: {init_info.get('svc_count')!r}")
    objdump = str(init_info.get("objdump", ""))
    if not any("mov" in line and "x8" in line and "#0x65" in line for line in objdump.splitlines()):
        raise SystemExit("M21A /init does not load arm64 __NR_nanosleep (101)")
    if not any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump.splitlines()):
        raise SystemExit("M21A /init does not load arm64 __NR_reboot (142)")


def verify_current_boot_hash(log_path: Path, serial: str) -> None:
    result = adb_shell(
        "su -c 'dd if=/dev/block/by-name/boot bs=4096 2>/dev/null | sha256sum'",
        serial=serial,
        timeout=45.0,
    )
    text = result.stdout + result.stderr
    append_log(log_path, f"current_boot_hash_rc={result.returncode}")
    append_log(log_path, text)
    if result.returncode != 0 or EXPECTED_M21A_BASE_BOOT_SHA256 not in text:
        raise SystemExit("current boot hash does not match known-booting Magisk baseline")


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


def observe_timed_download(
    run_dir: Path,
    log_path: Path,
    *,
    odin: Path,
    dwell_sec: int,
    dwell_grace_sec: int,
) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    start = time.monotonic()
    threshold = start + dwell_sec
    deadline = threshold + dwell_grace_sec
    append_log(log_path, f"m21a_observe_start_utc={utc_now()}")
    append_log(log_path, f"m21a_expected_dwell_sec={dwell_sec}")
    append_log(log_path, f"m21a_dwell_grace_sec={dwell_grace_sec}")
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        now = time.monotonic()
        elapsed = now - start
        phase = "pre_dwell" if now < threshold else "post_dwell"
        label = f"m21a_timed_download_{iteration:03d}_{phase}"
        append_log(log_path, f"{label}_elapsed_sec={elapsed:.3f}")
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, f"m21a_download_seen=1 phase={phase} elapsed_sec={elapsed:.3f} device={devices[0]}")
            if now < threshold:
                append_log(log_path, "m21a_result=no-proof-early-odin-before-dwell")
                return "early-odin-before-dwell", devices[0]
            append_log(log_path, "m21a_result=timed-download-after-dwell")
            return "timed-download-after-dwell", devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M21A observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"m21a_candidate_adb_rows={rows}")
            append_log(log_path, "m21a_result=no-proof-adb-returned")
            return "adb-returned", None
        time.sleep(1.0)
    append_log(log_path, "m21a_download_seen=0")
    append_log(log_path, "m21a_result=no-download-after-dwell-grace")
    return "no-download-after-dwell-grace", None


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
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M21A_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m21a-ap", type=Path, default=DEFAULT_M21A_AP)
    parser.add_argument("--m21a-manifest", type=Path, default=DEFAULT_M21A_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--dwell-sec", type=int, default=EXPECTED_DWELL_SEC)
    parser.add_argument("--dwell-grace-sec", type=int, default=30)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(1 for enabled in (args.offline_check, args.live, args.rollback_from_download) if enabled)
    if modes > 1:
        raise SystemExit("--offline-check, --live, and --rollback-from-download are mutually exclusive")
    if args.dwell_sec != EXPECTED_DWELL_SEC:
        raise SystemExit(f"M21A dwell is SHA-pinned to {EXPECTED_DWELL_SEC}s; got --dwell-sec {args.dwell_sec}")
    if args.dwell_grace_sec < 5:
        raise SystemExit("--dwell-grace-sec must be at least 5")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m21a_raw_nanosleep_download_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m21a raw nanosleep-download live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m21a_ap = resolve(root, args.m21a_ap)
    m21a_manifest = resolve(root, args.m21a_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m21a_ap, EXPECTED_M21A_AP_SHA256, "m21a_candidate", log_path)
    verify_m21a_manifest(m21a_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.offline_check:
        print(f"offline-check ok: M21A candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M21A rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_current_boot_hash(log_path, selected_serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M21A candidate, rollback APs, AGENTS exception, "
            f"current boot hash, Android preflight, and dwell policy verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    print(
        "M21A live gate starting. After candidate flash, do not press recovery/download keys "
        f"until at least {args.dwell_sec + args.dwell_grace_sec}s after the original Odin endpoint disconnects, "
        "or until this helper asks for manual rollback.",
        flush=True,
    )
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M21A candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m21a_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M21A candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(
        odin,
        log_path,
        "post-candidate-disconnect",
        args.post_flash_disconnect_wait_sec,
    )
    if not left_download:
        print(
            "M21A candidate flash completed but the original Odin device did not disconnect; "
            "rolling back without claiming proof.",
            file=sys.stderr,
        )
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            print(f"rollback download mode unavailable after no-disconnect; manual recovery required. log={log_path}", file=sys.stderr)
            return 4
        rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback_no_disconnect")
        if rollback_rc != 0:
            print(f"rollback Odin flash failed rc={rollback_rc}; log={log_path}", file=sys.stderr)
            return rollback_rc or 5
        post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
        if post_rollback_serial is None:
            print(f"rollback transferred but Android/root verification failed; log={log_path}", file=sys.stderr)
            return 6
        append_log(log_path, "m21a_result=no-proof-original-download-never-disconnected")
        collect_android_pstore(
            run_dir,
            log_path,
            "post_rollback_no_disconnect",
            post_rollback_serial,
            marker=EXPECTED_M21A_MARKER,
        )
        return 7

    print(
        f"M21A candidate flashed. Waiting {args.dwell_sec}s dwell + {args.dwell_grace_sec}s grace. "
        "Do not manually enter download mode during this window.",
        flush=True,
    )
    result, rollback_device = observe_timed_download(
        run_dir,
        log_path,
        odin=odin,
        dwell_sec=args.dwell_sec,
        dwell_grace_sec=args.dwell_grace_sec,
    )
    if result != "timed-download-after-dwell":
        print(
            f"M21A did not produce an automatic timed-download proof ({result}). "
            "If the device is parked or looping, enter download mode manually and run --rollback-from-download.",
            file=sys.stderr,
        )
        return 4
    if rollback_device is None:
        raise SystemExit("internal error: timed-download result without rollback device")

    rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, f"{args.rollback_target}_rollback")
    if rollback_rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            rollback_rc = flash_ap(odin, stock_rollback_ap, fallback_device, log_path, "stock_fallback")
    if rollback_rc != 0:
        print(f"rollback Odin flash failed rc={rollback_rc}; log={log_path}", file=sys.stderr)
        return rollback_rc or 5

    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
    if post_rollback_serial is None:
        print(f"rollback transferred but Android/root verification failed; log={log_path}", file=sys.stderr)
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M21A_MARKER)
    print(f"M21A live gate completed with timed-download proof and rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
