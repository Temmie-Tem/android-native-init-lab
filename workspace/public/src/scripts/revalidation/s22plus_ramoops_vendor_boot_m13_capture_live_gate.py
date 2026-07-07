#!/usr/bin/env python3
"""Guarded S22+ ramoops-vendor_boot + M13 positive-control live gate.

Default dry-run and all device modes require a future SHA-pinned AGENTS.md
exception. --offline-check verifies only the host-built vendor_boot/M13 packages
and rollback APs without touching a connected device.

Intended live flow, once separately authorized:
1. flash the direct-patched vendor_boot that enables ramoops;
2. require Android/root to return and verify vendor_boot hash plus live DT status;
3. flash the known parking M13 native-init boot candidate;
4. observe for ACM/ADB/Odin/manual-download evidence;
5. roll boot back to Magisk, collect pstore, then restore stock vendor_boot.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    adb_shell,
    append_log,
    collect_android_pstore,
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
from s22plus_ramoops_dtbo_m18_capture_live_gate import reboot_android_to_download, wait_for_android_root


LIVE_ACK_TOKEN = "S22PLUS-RAMOOPS-VENDORBOOT-M13-CAPTURE-LIVE-GATE"
ROLLBACK_BOOT_ACK_TOKEN = "S22PLUS-RAMOOPS-M13-ROLLBACK-BOOT-FROM-DOWNLOAD"
RESTORE_VENDOR_BOOT_ACK_TOKEN = "S22PLUS-RAMOOPS-RESTORE-STOCK-VENDOR-BOOT"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_BOOT_MEMBER = "boot.img.lz4"
EXPECTED_VENDOR_BOOT_MEMBER = "vendor_boot.img.lz4"

EXPECTED_VENDOR_BOOT_CANDIDATE_AP_SHA256 = "0af250628c7cd5d7062b53823162f55716d1758d31ff88f65ea1c61dd0da83c3"
EXPECTED_VENDOR_BOOT_ROLLBACK_AP_SHA256 = "2f9075fe609e7aa66c2ec88a2bd0223d6a9d7ff23d8bab0f7c4eb44633f480bb"
EXPECTED_STOCK_VENDOR_BOOT_SHA256 = "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"
EXPECTED_PATCHED_VENDOR_BOOT_SHA256 = "d62f2da241e1104db9e4b72aa0ba1927c0e85afd22fe380bff62c8df52bd3245"
EXPECTED_SOURCE_DTB_SHA256 = "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e"
EXPECTED_PATCHED_DTB_SHA256 = "b862359dc65adb1eb9f5f17f1b8be637eb0135e88a681d779f9cbeda3ae5a3ec"
EXPECTED_DTB_SIZE_DELTA = 80
EXPECTED_CHANGED_OUTSIDE_ALLOWED = 0

DEFAULT_VENDOR_BOOT_CANDIDATE_AP = Path(
    "workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1/candidate_odin4/AP.tar.md5"
)
DEFAULT_VENDOR_BOOT_ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1/stock_rollback_odin4/AP.tar.md5"
)
DEFAULT_VENDOR_BOOT_MANIFEST = Path("workspace/private/outputs/s22plus_ramoops_vendor_boot_direct_enable_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_ramoops_vendor_boot_m13_capture_{stamp}")
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


def verify_vendor_boot_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"vendor_boot manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    sizes = data.get("sizes", {})
    safety = data.get("safety", {})
    evidence = data.get("evidence", {})
    direct = evidence.get("direct_patch", {})
    append_log(log_path, f"vendor_boot_manifest_path={path}")
    append_log(log_path, f"vendor_boot_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"vendor_boot_manifest_safety={json.dumps(safety, sort_keys=True)}")

    required_hashes = {
        "candidate_ap_tar_md5": EXPECTED_VENDOR_BOOT_CANDIDATE_AP_SHA256,
        "rollback_ap_tar_md5": EXPECTED_VENDOR_BOOT_ROLLBACK_AP_SHA256,
        "stock_vendor_boot": EXPECTED_STOCK_VENDOR_BOOT_SHA256,
        "patched_vendor_boot": EXPECTED_PATCHED_VENDOR_BOOT_SHA256,
        "source_dtb": EXPECTED_SOURCE_DTB_SHA256,
        "patched_dtb": EXPECTED_PATCHED_DTB_SHA256,
    }
    for key, expected in required_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"vendor_boot manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")

    required_safety: dict[str, Any] = {
        "host_only": True,
        "touches_connected_device": False,
        "live_flash_authorized": False,
        "partition_scope_if_later_authorized": "vendor_boot only",
        "requires_new_sha_pinned_vendor_boot_exception_before_flash": True,
        "current_agents_does_not_authorize_this_live_flash": True,
        "forbidden_partitions_touched": False,
        "rollback_ap_built": True,
        "stock_vendor_boot_available": True,
        "magiskboot_repack_used": False,
        "byte_preserving_layout": True,
        "vendor_ramdisk_table_offset_unchanged": True,
        "bootconfig_offset_unchanged": True,
        "tail_footer_bytes_unchanged": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"vendor_boot manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if sizes.get("dtb_size_delta") != EXPECTED_DTB_SIZE_DELTA:
        raise SystemExit(f"vendor_boot DTB size delta mismatch: {sizes.get('dtb_size_delta')!r}")
    if sizes.get("stock_vendor_boot") != sizes.get("patched_vendor_boot"):
        raise SystemExit("vendor_boot direct patch changed partition image size")
    if direct.get("changed_outside_allowed_count") != EXPECTED_CHANGED_OUTSIDE_ALLOWED:
        raise SystemExit(f"vendor_boot changed outside allowed spans: {direct.get('changed_outside_allowed_count')!r}")
    status_values = direct.get("patched_status_values")
    if not isinstance(status_values, list) or len(status_values) != 4:
        raise SystemExit(f"vendor_boot expected four patched status values, got {status_values!r}")
    for item in status_values:
        if item.get("value") != "okay":
            raise SystemExit(f"vendor_boot patched status is not okay: {item!r}")
    if evidence.get("candidate_tar_members") != [EXPECTED_VENDOR_BOOT_MEMBER]:
        raise SystemExit(f"vendor_boot candidate members mismatch: {evidence.get('candidate_tar_members')!r}")
    if evidence.get("rollback_tar_members") != [EXPECTED_VENDOR_BOOT_MEMBER]:
        raise SystemExit(f"vendor_boot rollback members mismatch: {evidence.get('rollback_tar_members')!r}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ ramoops vendor_boot + M13 positive-control",
        EXPECTED_VENDOR_BOOT_CANDIDATE_AP_SHA256,
        EXPECTED_VENDOR_BOOT_ROLLBACK_AP_SHA256,
        EXPECTED_PATCHED_VENDOR_BOOT_SHA256,
        EXPECTED_STOCK_VENDOR_BOOT_SHA256,
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
        RESTORE_VENDOR_BOOT_ACK_TOKEN,
        "vendor_boot.img.lz4",
        "boot.img.lz4",
        "M13 positive-control",
        "restore stock vendor_boot",
        "manual download-mode",
        "changed_outside_allowed_count=0",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing ramoops vendor_boot + M13 authorization markers: {missing}")


def verify_current_vendor_boot_hash(log_path: Path, serial: str, expected_sha: str, label: str) -> None:
    result = adb_shell("su -c 'sha256sum /dev/block/by-name/vendor_boot'", serial=serial, timeout=45.0)
    text = result.stdout + result.stderr
    append_log(log_path, f"{label}_vendor_boot_hash_rc={result.returncode}")
    append_log(log_path, text)
    if result.returncode != 0 or expected_sha not in text:
        raise SystemExit(f"{label} vendor_boot hash does not match expected {expected_sha}")


def verify_live_ramoops_status(log_path: Path, serial: str) -> None:
    result = adb_shell(
        "su -c 'printf status=; cat /proc/device-tree/reserved-memory/ramoops_region/status 2>/dev/null; "
        "printf \"\\n\"; printf compatible=; cat /proc/device-tree/reserved-memory/ramoops_region/compatible 2>/dev/null; "
        "printf \"\\n\"; printf pstore_files=; ls -1 /sys/fs/pstore 2>/dev/null | tr \"\\n\" \" \"'",
        serial=serial,
        timeout=25.0,
    )
    text = result.stdout + result.stderr
    append_log(log_path, f"live_ramoops_status_rc={result.returncode}")
    append_log(log_path, text)
    if result.returncode != 0 or "status=okay" not in text:
        raise SystemExit("patched vendor_boot booted Android but live ramoops status is not okay")


def restore_vendor_boot_from_download(
    odin: Path,
    vendor_boot_rollback_ap: Path,
    log_path: Path,
    android_wait_sec: int,
    serial: str | None = None,
) -> int:
    device = wait_for_odin(odin, log_path, "stock-vendor-boot-rollback-wait", 5)
    if device is None:
        raise SystemExit("stock vendor_boot rollback requires exactly one Odin device")
    rc = flash_ap(odin, vendor_boot_rollback_ap, device, log_path, "stock_vendor_boot_rollback")
    if rc != 0:
        return rc or 5
    android = wait_for_android_root(log_path, android_wait_sec, serial)
    if android is None:
        return 6
    verify_current_vendor_boot_hash(log_path, android, EXPECTED_STOCK_VENDOR_BOOT_SHA256, "stock_restore")
    append_log(log_path, f"stock_vendor_boot_restore_android={android}")
    return 0


def rollback_boot_collect_pstore(
    odin: Path,
    boot_rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
) -> tuple[int, str | None, bool]:
    device = wait_for_odin(odin, log_path, "boot-rollback-wait", 5)
    if device is None:
        raise SystemExit("boot rollback requires exactly one Odin device")
    rc = flash_ap(odin, boot_rollback_ap, device, log_path, f"{rollback_target}_boot_rollback")
    if rc != 0:
        return (rc or 5, None, False)
    android = wait_for_android_root(log_path, android_wait_sec)
    if android is None:
        return (6, None, False)
    marker_found = collect_android_pstore(run_dir, log_path, "post_m13_boot_rollback", android, marker=EXPECTED_M13_MARKER)
    append_log(log_path, f"m13_positive_control_pstore_marker_found={int(marker_found)}")
    return (0, android, marker_found)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor-boot-ap", type=Path, default=DEFAULT_VENDOR_BOOT_CANDIDATE_AP)
    parser.add_argument("--vendor-boot-rollback-ap", type=Path, default=DEFAULT_VENDOR_BOOT_ROLLBACK_AP)
    parser.add_argument("--vendor-boot-manifest", type=Path, default=DEFAULT_VENDOR_BOOT_MANIFEST)
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
    parser.add_argument("--restore-vendor-boot-from-download", action="store_true")
    parser.add_argument("--restore-vendor-boot-from-android", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.live,
            args.rollback_boot_from_download,
            args.restore_vendor_boot_from_download,
            args.restore_vendor_boot_from_android,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --live, --rollback-boot-from-download, "
            "--restore-vendor-boot-from-download, and --restore-vendor-boot-from-android are mutually exclusive"
        )

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_ramoops_vendor_boot_m13_capture_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus ramoops vendor_boot M13 capture live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    vendor_boot_ap = resolve(root, args.vendor_boot_ap)
    vendor_boot_rollback_ap = resolve(root, args.vendor_boot_rollback_ap)
    vendor_boot_manifest = resolve(root, args.vendor_boot_manifest)
    m13_ap = resolve(root, args.m13_ap)
    m13_manifest = resolve(root, args.m13_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    boot_rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap

    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap_member(vendor_boot_ap, EXPECTED_VENDOR_BOOT_CANDIDATE_AP_SHA256, EXPECTED_VENDOR_BOOT_MEMBER, "vendor_boot_candidate", log_path)
    verify_ap_member(vendor_boot_rollback_ap, EXPECTED_VENDOR_BOOT_ROLLBACK_AP_SHA256, EXPECTED_VENDOR_BOOT_MEMBER, "vendor_boot_rollback", log_path)
    verify_vendor_boot_manifest(vendor_boot_manifest, log_path)
    verify_ap_member(m13_ap, EXPECTED_M13_AP_SHA256, EXPECTED_BOOT_MEMBER, "m13_candidate", log_path)
    verify_m13_manifest(m13_manifest, log_path)
    verify_ap_member(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, EXPECTED_BOOT_MEMBER, "magisk_boot_rollback", log_path)
    verify_ap_member(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, EXPECTED_BOOT_MEMBER, "stock_boot_fallback", log_path)

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: vendor_boot/M13 candidates and rollback APs verified; no device action; log={log_path}")
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
            args.android_wait_sec,
        )
        print(f"M13 boot rollback-from-download completed rc={rc} android={android} marker={int(marker_found)}; log={log_path}")
        return rc

    if args.restore_vendor_boot_from_download:
        if args.ack != RESTORE_VENDOR_BOOT_ACK_TOKEN:
            raise SystemExit(f"--restore-vendor-boot-from-download requires --ack {RESTORE_VENDOR_BOOT_ACK_TOKEN}")
        rc = restore_vendor_boot_from_download(odin, vendor_boot_rollback_ap, log_path, args.android_wait_sec)
        print(f"stock vendor_boot restore-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_current_boot_hash(log_path, selected_serial)
    verify_current_vendor_boot_hash(log_path, selected_serial, EXPECTED_STOCK_VENDOR_BOOT_SHA256, "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if args.restore_vendor_boot_from_android:
        if args.ack != RESTORE_VENDOR_BOOT_ACK_TOKEN:
            raise SystemExit(f"--restore-vendor-boot-from-android requires --ack {RESTORE_VENDOR_BOOT_ACK_TOKEN}")
        reboot_android_to_download(selected_serial, log_path, "stock_vendor_boot_restore")
        rc = restore_vendor_boot_from_download(odin, vendor_boot_rollback_ap, log_path, args.android_wait_sec, selected_serial)
        print(f"stock vendor_boot restore-from-android completed rc={rc}; log={log_path}")
        return rc

    if not args.live:
        print(
            "dry-run ok: vendor_boot/M13 candidates, rollback APs, AGENTS exception, Android stability, "
            f"boot hash, and stock vendor_boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot_android_to_download(selected_serial, log_path, "vendor_boot_candidate")
    device = wait_for_odin(odin, log_path, "vendor-boot-candidate-wait", args.odin_wait_sec)
    if device is None:
        print("download mode did not appear for vendor_boot candidate flash", file=sys.stderr)
        return 2
    rc = flash_ap(odin, vendor_boot_ap, device, log_path, "vendor_boot_candidate")
    if rc != 0:
        print(f"vendor_boot candidate Odin flash failed rc={rc}; log={log_path}", file=sys.stderr)
        return rc or 3

    patched_serial = wait_for_android_root(log_path, args.android_wait_sec)
    if patched_serial is None:
        print(
            "Android did not return after patched vendor_boot. Enter download mode and run --restore-vendor-boot-from-download.",
            file=sys.stderr,
        )
        return 6
    verify_current_vendor_boot_hash(log_path, patched_serial, EXPECTED_PATCHED_VENDOR_BOOT_SHA256, "patched")
    verify_live_ramoops_status(log_path, patched_serial)

    reboot_android_to_download(patched_serial, log_path, "m13_candidate")
    device = wait_for_odin(odin, log_path, "m13-candidate-wait", args.odin_wait_sec)
    if device is None:
        print("download mode did not appear for M13 candidate flash", file=sys.stderr)
        return 2
    rc = flash_ap(odin, m13_ap, device, log_path, "m13_candidate")
    if rc != 0:
        print(f"M13 candidate Odin flash failed rc={rc}; log={log_path}", file=sys.stderr)
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
        args.android_wait_sec,
    )
    if rc != 0:
        return rc

    reboot_android_to_download(post_boot_rollback_android or "", log_path, "stock_vendor_boot_restore_after_capture")
    rc = restore_vendor_boot_from_download(odin, vendor_boot_rollback_ap, log_path, args.android_wait_sec)
    if rc != 0:
        return rc or 8
    print(
        f"ramoops vendor_boot + M13 capture live gate completed; pstore_marker_found={int(marker_found)}; log={log_path}"
    )
    return 0 if marker_found else 10


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
