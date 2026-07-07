#!/usr/bin/env python3
"""Guarded S22+ ramoops-DTBO + M13 positive-control capture gate.

This is the post-DTBO-status proof path. It is deliberately separate from the
retired vendor_boot-only M13 helper: the live DTBO status gate proved that stock
DTBO is the component that disables the live ramoops node, so a positive control
must enable ramoops through the patched DTBO first.

Default dry-run and all device modes require a future SHA-pinned AGENTS.md
exception. --offline-check verifies only the DTBO/M13 packages and rollback APs
without touching a connected device.

Intended live flow, once separately authorized:
1. flash the patched DTBO that enables the live ramoops overlay;
2. require Android/root to return and verify DTBO hash plus live status=okay;
3. flash the known parking M13 native-init boot candidate;
4. observe for ACM/ADB/Odin/manual-download evidence;
5. roll boot back to Magisk, collect pstore, then restore stock DTBO.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    append_log,
    collect_android_pstore,
    flash_ap,
    host_snapshot,
    repo_root,
    require_current_android,
    resolve,
    utc_now,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability
from s22plus_m13_nomodule_configfs_live_gate import (
    DEFAULT_M13_AP,
    DEFAULT_M13_MANIFEST,
    EXPECTED_M13_AP_SHA256,
    EXPECTED_M13_BASE_BOOT_SHA256,
    EXPECTED_M13_BOOT_SHA256,
    EXPECTED_M13_INIT_SHA256,
    EXPECTED_M13_KERNEL_SHA256,
    EXPECTED_M13_MARKER,
    EXPECTED_M13_SOURCE_SHA256,
    observe_m13_acm,
    verify_current_boot_hash,
    verify_m13_manifest,
)
from s22plus_ramoops_dtbo_m18_capture_live_gate import (
    DEFAULT_DTBO_CANDIDATE_AP,
    DEFAULT_DTBO_MANIFEST,
    DEFAULT_DTBO_ROLLBACK_AP,
    EXPECTED_BOOT_MEMBER,
    EXPECTED_DTBO_CANDIDATE_AP_SHA256,
    EXPECTED_DTBO_MEMBER,
    EXPECTED_DTBO_ROLLBACK_AP_SHA256,
    EXPECTED_PATCHED_DTBO_RAW_SHA256,
    EXPECTED_STOCK_DTBO_RAW_SHA256,
    EXPECTED_TARGET,
    RESTORE_DTBO_ACK_TOKEN,
    reboot_android_to_download,
    verify_dtbo_manifest,
    wait_for_android_root,
)
from s22plus_ramoops_dtbo_status_live_gate import (
    read_current_dtbo_hash,
    restore_after_patched_android_failure,
    restore_after_patched_android_timeout,
    restore_dtbo_from_download,
    verify_ap_member,
    verify_current_dtbo_hash,
    verify_live_ramoops_status,
)


LIVE_ACK_TOKEN = "S22PLUS-RAMOOPS-DTBO-M13-CAPTURE-LIVE-GATE"
ROLLBACK_BOOT_ACK_TOKEN = "S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD"


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_ramoops_dtbo_m13_capture_{stamp}")
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
        "S22+ ramoops DTBO + M13 positive-control",
        "workspace/public/src/scripts/revalidation/s22plus_ramoops_dtbo_m13_capture_live_gate.py",
        EXPECTED_DTBO_CANDIDATE_AP_SHA256,
        EXPECTED_DTBO_ROLLBACK_AP_SHA256,
        EXPECTED_PATCHED_DTBO_RAW_SHA256,
        EXPECTED_STOCK_DTBO_RAW_SHA256,
        EXPECTED_M13_AP_SHA256,
        EXPECTED_M13_BOOT_SHA256,
        EXPECTED_M13_BASE_BOOT_SHA256,
        EXPECTED_M13_KERNEL_SHA256,
        EXPECTED_M13_INIT_SHA256,
        EXPECTED_M13_SOURCE_SHA256,
        EXPECTED_MAGISK_AP_SHA256,
        EXPECTED_STOCK_BOOT_AP_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_BOOT_ACK_TOKEN,
        RESTORE_DTBO_ACK_TOKEN,
        "dtbo.img.lz4",
        "boot.img.lz4",
        "ramoops_region/status=okay",
        "M13 positive-control",
        "pstore",
        "restore stock DTBO",
        "manual download-mode",
        "no vendor_boot",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing ramoops DTBO + M13 authorization markers: {missing}")


def rollback_boot_collect_pstore(
    odin: Path,
    boot_rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    odin_wait_sec: int,
    android_wait_sec: int,
) -> tuple[int, str | None, bool]:
    device = wait_for_odin(odin, log_path, "m13-boot-rollback-wait", odin_wait_sec)
    if device is None:
        raise SystemExit("M13 boot rollback requires exactly one Odin device")
    rc = flash_ap(odin, boot_rollback_ap, device, log_path, f"{rollback_target}_boot_rollback")
    if rc != 0:
        return (rc or 5, None, False)
    android = wait_for_android_root(log_path, android_wait_sec)
    if android is None:
        return (6, None, False)
    marker_found = collect_android_pstore(run_dir, log_path, "post_m13_boot_rollback", android, marker=EXPECTED_M13_MARKER)
    append_log(log_path, f"m13_positive_control_pstore_marker_found={int(marker_found)}")
    return (0, android, marker_found)


def restore_stock_dtbo_from_android(
    serial: str,
    odin: Path,
    dtbo_rollback_ap: Path,
    log_path: Path,
    odin_wait_sec: int,
    android_wait_sec: int,
    label: str,
) -> int:
    reboot_android_to_download(serial, log_path, label)
    return restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, odin_wait_sec, android_wait_sec, serial)


def preflight_common(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_ramoops_dtbo_m13_capture_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus ramoops DTBO M13 capture live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    dtbo_candidate_ap = resolve(root, args.dtbo_candidate_ap)
    dtbo_rollback_ap = resolve(root, args.dtbo_rollback_ap)
    dtbo_manifest = resolve(root, args.dtbo_manifest)
    m13_ap = resolve(root, args.m13_ap)
    m13_manifest = resolve(root, args.m13_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap_member(dtbo_candidate_ap, EXPECTED_DTBO_CANDIDATE_AP_SHA256, EXPECTED_DTBO_MEMBER, "dtbo_candidate", log_path)
    verify_ap_member(dtbo_rollback_ap, EXPECTED_DTBO_ROLLBACK_AP_SHA256, EXPECTED_DTBO_MEMBER, "dtbo_stock_rollback", log_path)
    verify_dtbo_manifest(dtbo_manifest, log_path)
    verify_ap_member(m13_ap, EXPECTED_M13_AP_SHA256, EXPECTED_BOOT_MEMBER, "m13_candidate", log_path)
    verify_m13_manifest(m13_manifest, log_path)
    verify_ap_member(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, EXPECTED_BOOT_MEMBER, "magisk_boot_rollback", log_path)
    verify_ap_member(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, EXPECTED_BOOT_MEMBER, "stock_boot_fallback", log_path)
    return root, run_dir, log_path, odin, dtbo_candidate_ap, dtbo_rollback_ap, m13_ap, magisk_rollback_ap, stock_rollback_ap


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dtbo-candidate-ap", type=Path, default=DEFAULT_DTBO_CANDIDATE_AP)
    parser.add_argument("--dtbo-rollback-ap", type=Path, default=DEFAULT_DTBO_ROLLBACK_AP)
    parser.add_argument("--dtbo-manifest", type=Path, default=DEFAULT_DTBO_MANIFEST)
    parser.add_argument("--m13-ap", type=Path, default=DEFAULT_M13_AP)
    parser.add_argument("--m13-manifest", type=Path, default=DEFAULT_M13_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--m13-observe-sec", type=int, default=120)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-boot-from-download", action="store_true")
    parser.add_argument("--restore-dtbo-from-download", action="store_true")
    parser.add_argument("--restore-dtbo-from-android", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.live,
            args.rollback_boot_from_download,
            args.restore_dtbo_from_download,
            args.restore_dtbo_from_android,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --live, --rollback-boot-from-download, "
            "--restore-dtbo-from-download, and --restore-dtbo-from-android are mutually exclusive"
        )

    (
        root,
        run_dir,
        log_path,
        odin,
        dtbo_candidate_ap,
        dtbo_rollback_ap,
        m13_ap,
        magisk_rollback_ap,
        stock_rollback_ap,
    ) = preflight_common(args)
    boot_rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: DTBO/M13 candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.rollback_boot_from_download:
        if args.ack != ROLLBACK_BOOT_ACK_TOKEN:
            raise SystemExit(f"--rollback-boot-from-download requires --ack {ROLLBACK_BOOT_ACK_TOKEN}")
        rc, android, marker_found = rollback_boot_collect_pstore(
            odin,
            boot_rollback_ap,
            run_dir,
            log_path,
            args.rollback_target,
            args.odin_wait_sec,
            args.android_wait_sec,
        )
        if rc != 0 or android is None:
            print(f"M13 boot rollback-from-download completed rc={rc} android={android} marker={int(marker_found)}; log={log_path}")
            return rc
        restore_rc = restore_stock_dtbo_from_android(
            android,
            odin,
            dtbo_rollback_ap,
            log_path,
            args.odin_wait_sec,
            args.android_wait_sec,
            "stock_dtbo_restore_after_m13_manual_boot_rollback",
        )
        print(
            "M13 boot rollback-from-download completed "
            f"rc={rc} android={android} marker={int(marker_found)} stock_dtbo_restore_rc={restore_rc}; log={log_path}"
        )
        return restore_rc if restore_rc != 0 else (0 if marker_found else 10)

    if args.restore_dtbo_from_download:
        if args.ack != RESTORE_DTBO_ACK_TOKEN:
            raise SystemExit(f"--restore-dtbo-from-download requires --ack {RESTORE_DTBO_ACK_TOKEN}")
        rc = restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, args.odin_wait_sec, args.android_wait_sec)
        print(f"stock DTBO restore-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_current_boot_hash(log_path, selected_serial)

    if args.restore_dtbo_from_android:
        if args.ack != RESTORE_DTBO_ACK_TOKEN:
            raise SystemExit(f"--restore-dtbo-from-android requires --ack {RESTORE_DTBO_ACK_TOKEN}")
        current_dtbo_sha = read_current_dtbo_hash(log_path, selected_serial, "pre_stock_restore")
        host_snapshot(run_dir, log_path, "restore_android_current", odin)
        if current_dtbo_sha == EXPECTED_STOCK_DTBO_RAW_SHA256:
            verify_live_ramoops_status(log_path, selected_serial, "disabled", "stock_restore_already")
            append_log(log_path, "stock_dtbo_restore_android_already_stock=1")
            print(f"stock DTBO restore-from-android already stock; log={log_path}")
            return 0
        if current_dtbo_sha != EXPECTED_PATCHED_DTBO_RAW_SHA256:
            raise SystemExit(f"refusing restore-from-android from unexpected DTBO hash {current_dtbo_sha}")
        rc = restore_stock_dtbo_from_android(
            selected_serial,
            odin,
            dtbo_rollback_ap,
            log_path,
            args.odin_wait_sec,
            args.android_wait_sec,
            "stock_dtbo_restore",
        )
        print(f"stock DTBO restore-from-android completed rc={rc}; log={log_path}")
        return rc

    verify_current_dtbo_hash(log_path, selected_serial, EXPECTED_STOCK_DTBO_RAW_SHA256, "current")
    verify_live_ramoops_status(log_path, selected_serial, "disabled", "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: DTBO/M13 candidates, rollback APs, AGENTS exception, Android stability, "
            f"boot hash, stock DTBO hash, and live disabled status verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot_android_to_download(selected_serial, log_path, "dtbo_candidate")
    device = wait_for_odin(odin, log_path, "dtbo-candidate-wait", args.odin_wait_sec)
    if device is None:
        print("download mode did not appear for DTBO candidate flash", file=sys.stderr)
        return 2
    rc = flash_ap(odin, dtbo_candidate_ap, device, log_path, "dtbo_candidate")
    if rc != 0:
        print(f"DTBO candidate Odin flash failed rc={rc}; log={log_path}", file=sys.stderr)
        return rc or 3

    patched_serial = wait_for_android_root(log_path, args.android_wait_sec)
    if patched_serial is None:
        return restore_after_patched_android_timeout(
            odin,
            dtbo_rollback_ap,
            log_path,
            args.odin_wait_sec,
            args.android_wait_sec,
        )
    try:
        verify_current_dtbo_hash(log_path, patched_serial, EXPECTED_PATCHED_DTBO_RAW_SHA256, "patched")
        verify_live_ramoops_status(log_path, patched_serial, "okay", "patched")
    except SystemExit as verify_error:
        return restore_after_patched_android_failure(
            odin,
            dtbo_rollback_ap,
            log_path,
            patched_serial,
            args.odin_wait_sec,
            args.android_wait_sec,
            verify_error,
        )

    reboot_android_to_download(patched_serial, log_path, "m13_candidate")
    device = wait_for_odin(odin, log_path, "m13-candidate-wait", args.odin_wait_sec)
    if device is None:
        print("download mode did not appear for M13 candidate flash; patched DTBO restore may be needed", file=sys.stderr)
        return 2
    rc = flash_ap(odin, m13_ap, device, log_path, "m13_candidate")
    if rc != 0:
        append_log(log_path, f"m13_candidate_flash_failed_attempting_dtbo_restore_rc={rc}")
        restore_rc = restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, args.odin_wait_sec, args.android_wait_sec)
        print(f"M13 candidate Odin flash failed rc={rc}; stock DTBO restore rc={restore_rc}; log={log_path}", file=sys.stderr)
        return rc or 3

    observed, endpoint = observe_m13_acm(run_dir, log_path, args.m13_observe_sec, odin)
    if observed == "acm":
        append_log(log_path, f"m13_result=acm_seen_manual_download_required endpoint={endpoint}")
        print(
            "M13 ACM appeared. Enter download mode manually for boot rollback, then run --rollback-boot-from-download.",
            file=sys.stderr,
        )
        return 4
    if observed == "adb" and endpoint:
        append_log(log_path, f"m13_unexpected_adb_returned={endpoint}")
        reboot_android_to_download(endpoint, log_path, "m13_unexpected_adb_rollback")
        endpoint = wait_for_odin(odin, log_path, "m13-unexpected-adb-rollback-wait", args.odin_wait_sec)
        observed = "odin" if endpoint else "none"
    if observed != "odin" or endpoint is None:
        append_log(log_path, "m13_result=no_rollback_transport_manual_download_required")
        print("M13 did not expose rollback transport. Enter download mode manually and run --rollback-boot-from-download.", file=sys.stderr)
        return 4

    rc, post_boot_rollback_android, marker_found = rollback_boot_collect_pstore(
        odin,
        boot_rollback_ap,
        run_dir,
        log_path,
        args.rollback_target,
        args.odin_wait_sec,
        args.android_wait_sec,
    )
    if rc != 0 or post_boot_rollback_android is None:
        return rc

    restore_rc = restore_stock_dtbo_from_android(
        post_boot_rollback_android,
        odin,
        dtbo_rollback_ap,
        log_path,
        args.odin_wait_sec,
        args.android_wait_sec,
        "stock_dtbo_restore_after_m13_capture",
    )
    if restore_rc != 0:
        return restore_rc
    print(
        f"ramoops DTBO + M13 capture live gate completed; pstore_marker_found={int(marker_found)}; log={log_path}"
    )
    return 0 if marker_found else 10


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
