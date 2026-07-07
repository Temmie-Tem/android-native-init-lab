#!/usr/bin/env python3
"""Guarded S22+ DTBO-only ramoops status live gate.

Default live/dry-run modes require a future SHA-pinned AGENTS.md exception. This
helper is intentionally narrower than the old DTBO+M18 capture gate: it flashes
only the patched DTBO, proves live `ramoops_region/status=okay`, then restores
stock DTBO. It never flashes a boot/native-init candidate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from s22plus_m3_observable_live_gate import (
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    adb_shell,
    append_log,
    flash_ap,
    host_snapshot,
    repo_root,
    require_current_android,
    resolve,
    sha256_file,
    tar_members,
    utc_now,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability
from s22plus_ramoops_dtbo_m18_capture_live_gate import (
    DEFAULT_DTBO_CANDIDATE_AP,
    DEFAULT_DTBO_MANIFEST,
    DEFAULT_DTBO_ROLLBACK_AP,
    EXPECTED_DTBO_CANDIDATE_AP_SHA256,
    EXPECTED_DTBO_MEMBER,
    EXPECTED_DTBO_ROLLBACK_AP_SHA256,
    EXPECTED_PATCHED_DTBO_RAW_SHA256,
    EXPECTED_STOCK_DTBO_RAW_SHA256,
    EXPECTED_TARGET,
    RESTORE_DTBO_ACK_TOKEN,
    reboot_android_to_download,
    verify_current_boot_hash,
    verify_dtbo_manifest,
    wait_for_android_root,
)


LIVE_ACK_TOKEN = "S22PLUS-RAMOOPS-DTBO-STATUS-LIVE-GATE"


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_ramoops_dtbo_status_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def verify_ap_member(path: Path, expected_sha: str, expected_member: str, label: str, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"{label} AP missing: {path}")
    actual_sha = sha256_file(path)
    members = tar_members(path)
    append_log(log_path, f"{label}_sha256={actual_sha}")
    append_log(log_path, f"{label}_members={members}")
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} AP SHA mismatch: {actual_sha}")
    if members != [expected_member]:
        raise SystemExit(f"{label} AP must contain exactly {expected_member!r}, got {members!r}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ ramoops DTBO status-only",
        EXPECTED_DTBO_CANDIDATE_AP_SHA256,
        EXPECTED_DTBO_ROLLBACK_AP_SHA256,
        EXPECTED_PATCHED_DTBO_RAW_SHA256,
        EXPECTED_STOCK_DTBO_RAW_SHA256,
        LIVE_ACK_TOKEN,
        RESTORE_DTBO_ACK_TOKEN,
        EXPECTED_DTBO_MEMBER,
        "ramoops_region/status=okay",
        "restore stock DTBO",
        "no boot candidate",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing ramoops DTBO status-only authorization markers: {missing}")


def read_current_dtbo_hash(log_path: Path, serial: str, label: str) -> str:
    result = adb_shell("su -c 'dd if=/dev/block/by-name/dtbo bs=4096 2>/dev/null | sha256sum'", serial=serial, timeout=45.0)
    text = result.stdout + result.stderr
    append_log(log_path, f"{label}_dtbo_hash_rc={result.returncode}")
    append_log(log_path, text)
    words = text.split()
    actual_sha = words[0].lower() if words else ""
    if result.returncode != 0 or len(actual_sha) != 64 or any(ch not in "0123456789abcdef" for ch in actual_sha):
        raise SystemExit(f"{label} DTBO hash could not be read safely")
    return actual_sha


def verify_current_dtbo_hash(log_path: Path, serial: str, expected_sha: str, label: str) -> None:
    actual_sha = read_current_dtbo_hash(log_path, serial, label)
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} DTBO hash does not match expected {expected_sha}")


def read_live_ramoops_status(log_path: Path, serial: str, label: str) -> str:
    result = adb_shell(
        "su -c 'p=/proc/device-tree/reserved-memory/ramoops_region/status; "
        "if [ -e \"$p\" ]; then tr \"\\000\" \"\\n\" < \"$p\" | head -1; else echo __MISSING__; fi'",
        serial=serial,
        timeout=20.0,
    )
    text = (result.stdout + result.stderr).strip()
    append_log(log_path, f"{label}_ramoops_status_rc={result.returncode}")
    append_log(log_path, f"{label}_ramoops_status={text}")
    if result.returncode != 0 or not text or "__MISSING__" in text:
        raise SystemExit(f"{label} live ramoops status could not be read")
    return text.splitlines()[0].strip()


def verify_live_ramoops_status(log_path: Path, serial: str, expected_status: str, label: str) -> None:
    status = read_live_ramoops_status(log_path, serial, label)
    if status != expected_status:
        raise SystemExit(f"{label} live ramoops status {status!r} != {expected_status!r}")


def restore_dtbo_from_download(
    odin: Path,
    dtbo_rollback_ap: Path,
    log_path: Path,
    odin_wait_sec: int,
    android_wait_sec: int,
    serial: str | None = None,
) -> int:
    device = wait_for_odin(odin, log_path, "stock-dtbo-rollback-wait", odin_wait_sec)
    if device is None:
        raise SystemExit("stock DTBO rollback requires exactly one Odin device")
    rc = flash_ap(odin, dtbo_rollback_ap, device, log_path, "stock_dtbo_rollback")
    if rc != 0:
        return rc or 5
    android = wait_for_android_root(log_path, android_wait_sec, serial)
    if android is None:
        return 6
    verify_current_dtbo_hash(log_path, android, EXPECTED_STOCK_DTBO_RAW_SHA256, "stock_restore")
    verify_live_ramoops_status(log_path, android, "disabled", "stock_restore")
    append_log(log_path, f"stock_dtbo_restore_android={android}")
    return 0


def restore_after_patched_android_failure(
    odin: Path,
    dtbo_rollback_ap: Path,
    log_path: Path,
    patched_serial: str,
    odin_wait_sec: int,
    android_wait_sec: int,
    reason: BaseException,
) -> int:
    append_log(log_path, f"patched_dtbo_verification_failed={reason}")
    print(f"patched DTBO verification failed; attempting stock DTBO restore before exit: {reason}", file=sys.stderr)
    try:
        reboot_android_to_download(patched_serial, log_path, "stock_dtbo_restore_after_patched_verify_fail")
        rc = restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, odin_wait_sec, android_wait_sec, patched_serial)
    except SystemExit as restore_error:
        append_log(log_path, f"stock_dtbo_restore_after_patched_verify_fail_failed={restore_error}")
        print(f"stock DTBO restore after patched verification failure failed: {restore_error}", file=sys.stderr)
        raise
    append_log(log_path, f"stock_dtbo_restore_after_patched_verify_fail_rc={rc}")
    if rc != 0:
        return rc
    return 10


def preflight_common(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_ramoops_dtbo_status_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus ramoops DTBO status live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    dtbo_candidate_ap = resolve(root, args.dtbo_candidate_ap)
    dtbo_rollback_ap = resolve(root, args.dtbo_rollback_ap)
    dtbo_manifest = resolve(root, args.dtbo_manifest)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap_member(dtbo_candidate_ap, EXPECTED_DTBO_CANDIDATE_AP_SHA256, EXPECTED_DTBO_MEMBER, "dtbo_candidate", log_path)
    verify_ap_member(dtbo_rollback_ap, EXPECTED_DTBO_ROLLBACK_AP_SHA256, EXPECTED_DTBO_MEMBER, "dtbo_stock_rollback", log_path)
    verify_dtbo_manifest(dtbo_manifest, log_path)
    return root, run_dir, log_path, odin, dtbo_candidate_ap, dtbo_rollback_ap


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dtbo-candidate-ap", type=Path, default=DEFAULT_DTBO_CANDIDATE_AP)
    parser.add_argument("--dtbo-rollback-ap", type=Path, default=DEFAULT_DTBO_ROLLBACK_AP)
    parser.add_argument("--dtbo-manifest", type=Path, default=DEFAULT_DTBO_MANIFEST)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--restore-dtbo-from-download", action="store_true")
    parser.add_argument("--restore-dtbo-from-android", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.live,
            args.restore_dtbo_from_download,
            args.restore_dtbo_from_android,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit("--offline-check, --live, --restore-dtbo-from-download, and --restore-dtbo-from-android are mutually exclusive")

    root, run_dir, log_path, odin, dtbo_candidate_ap, dtbo_rollback_ap = preflight_common(args)

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: DTBO status candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.restore_dtbo_from_download:
        if args.ack != RESTORE_DTBO_ACK_TOKEN:
            raise SystemExit(f"--restore-dtbo-from-download requires --ack {RESTORE_DTBO_ACK_TOKEN}")
        rc = restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, args.odin_wait_sec, args.android_wait_sec)
        print(f"stock DTBO restore-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(log_path, selected_serial, args.android_stability_samples, args.android_stability_interval_sec)
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
        reboot_android_to_download(selected_serial, log_path, "stock_dtbo_restore")
        rc = restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, args.odin_wait_sec, args.android_wait_sec, selected_serial)
        print(f"stock DTBO restore-from-android completed rc={rc}; log={log_path}")
        return rc

    verify_current_dtbo_hash(log_path, selected_serial, EXPECTED_STOCK_DTBO_RAW_SHA256, "current")
    verify_live_ramoops_status(log_path, selected_serial, "disabled", "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: DTBO status candidate, rollback AP, AGENTS exception, Android stability, "
            f"boot hash, stock DTBO hash, and live disabled status verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot_android_to_download(selected_serial, log_path, "dtbo_status_candidate")
    device = wait_for_odin(odin, log_path, "dtbo-status-candidate-wait", args.odin_wait_sec)
    if device is None:
        print("download mode did not appear for DTBO status candidate flash", file=sys.stderr)
        return 2
    rc = flash_ap(odin, dtbo_candidate_ap, device, log_path, "dtbo_status_candidate")
    if rc != 0:
        print(f"DTBO status candidate Odin flash failed rc={rc}; log={log_path}", file=sys.stderr)
        return rc or 3

    patched_serial = wait_for_android_root(log_path, args.android_wait_sec)
    if patched_serial is None:
        print("Android did not return after patched DTBO. Enter download mode and run --restore-dtbo-from-download.", file=sys.stderr)
        return 6
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

    reboot_android_to_download(patched_serial, log_path, "stock_dtbo_restore_after_status_gate")
    rc = restore_dtbo_from_download(odin, dtbo_rollback_ap, log_path, args.odin_wait_sec, args.android_wait_sec, patched_serial)
    print(f"ramoops DTBO status live gate completed rc={rc}; log={log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
