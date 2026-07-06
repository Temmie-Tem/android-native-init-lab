#!/usr/bin/env python3
"""Guarded S22+ M4T0 instant-download native-init live gate.

Dry-run is the default.  Live mode requires:

- the exact SHA-pinned M4T0 AGENTS.md exception;
- exact M4T0 boot-only AP hash and single `boot.img.lz4` tar member;
- exact pinned Magisk boot-only rollback AP and stock boot-only fallback AP;
- a single normal Android ADB target matching SM-S906N/g0q/S906NKSS7FYG8;
- an explicit ack token.

M4T0 is the direct-PID1 floor probe.  Its first candidate action is a Samsung
download reboot before marker writes, modules, USB, configfs, or Android handoff.
If download mode reappears after the candidate flash, the kernel executed custom
`/init` and rollback must run immediately.
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


ACK_TOKEN = "S22PLUS-M4T0-INSTANT-DOWNLOAD-LIVE-GATE"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M4T0_AP_SHA256 = "ba445b131fddd79887a4ace357a77a42b1f49367eaeea156a3cfebfd883b1904"
EXPECTED_M4T0_BOOT_SHA256 = "4617a8804b93435cd0b6a5307862b4d5f55ca7e25befa0c19b2e7619284979e9"
EXPECTED_M4T0_MARKER = "S22_NATIVE_INIT_INSTANT_DOWNLOAD_M4T0"

DEFAULT_M4T0_AP = Path("workspace/private/outputs/s22plus_native_init/instant_download_m4t0_v0_1/odin4/AP.tar.md5")
DEFAULT_M4T0_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/instant_download_m4t0_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested
    else:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
        run_dir = DEFAULT_RUN_ROOT / f"s22plus_m4t0_instant_download_live_gate_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M4T0 instant-download native-init boot-only",
        EXPECTED_M4T0_AP_SHA256,
        EXPECTED_M4T0_BOOT_SHA256,
        ACK_TOKEN,
        EXPECTED_M4T0_MARKER,
        "first candidate action must be `reboot(..., \"download\")`",
        "no marker before the reboot syscall",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M4T0 live authorization markers: {missing}")


def verify_m4t0_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M4T0 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    packaging = data.get("ramdisk_packaging", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m4t0_manifest_path={path}")
    append_log(log_path, f"m4t0_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m4t0_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m4t0_manifest_ramdisk_packaging={json.dumps(packaging, sort_keys=True)}")
    if hashes.get("ap_tar_md5") != EXPECTED_M4T0_AP_SHA256:
        raise SystemExit("M4T0 manifest AP hash does not match expected M4T0 AP")
    if hashes.get("boot_img") != EXPECTED_M4T0_BOOT_SHA256:
        raise SystemExit("M4T0 manifest boot image hash does not match expected M4T0 boot image")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M4T0 manifest tar members mismatch: {tar_members_seen!r}")
    if safety.get("auto_reboot") != "download-first-action":
        raise SystemExit(f"M4T0 manifest auto_reboot mismatch: {safety.get('auto_reboot')!r}")
    if safety.get("marker_before_reboot") is not False:
        raise SystemExit(f"M4T0 manifest marker_before_reboot mismatch: {safety.get('marker_before_reboot')!r}")
    if safety.get("module_insertions") is not False:
        raise SystemExit(f"M4T0 manifest module_insertions mismatch: {safety.get('module_insertions')!r}")
    if safety.get("configfs_runtime_gadget") is not False:
        raise SystemExit(f"M4T0 manifest configfs_runtime_gadget mismatch: {safety.get('configfs_runtime_gadget')!r}")
    if safety.get("watchdog") != "not-touched":
        raise SystemExit(f"M4T0 manifest watchdog mismatch: {safety.get('watchdog')!r}")
    if packaging.get("format") != "legacy-lz4":
        raise SystemExit(f"M4T0 ramdisk format mismatch: {packaging.get('format')!r}")
    if packaging.get("magic_hex") != "02214c18":
        raise SystemExit(f"M4T0 ramdisk magic mismatch: {packaging.get('magic_hex')!r}")
    if packaging.get("roundtrip_sha256") != hashes.get("ramdisk_cpio"):
        raise SystemExit("M4T0 ramdisk roundtrip hash does not match ramdisk_cpio hash")


def observe_until_odin(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> str | None:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m4t0_self_download_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, f"m4t0_self_download_seen=1 device={devices[0]}")
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M4T0 observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"m4t0_candidate_adb_rows={rows}")
        time.sleep(1.0)
    append_log(log_path, "m4t0_self_download_seen=0")
    return None


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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4t0-ap", type=Path, default=DEFAULT_M4T0_AP)
    parser.add_argument("--m4t0-manifest", type=Path, default=DEFAULT_M4T0_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--self-download-wait-sec", type=int, default=45)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack", help=f"required with --live: {ACK_TOKEN}")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m4t0_instant_download_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m4t0 instant-download live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m4t0_ap = resolve(root, args.m4t0_ap)
    m4t0_manifest = resolve(root, args.m4t0_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m4t0_ap, EXPECTED_M4T0_AP_SHA256, "m4t0_candidate", log_path)
    verify_m4t0_manifest(m4t0_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    selected_serial = require_current_android(log_path, args.serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M4T0 candidate, rollback APs, AGENTS exception, and Android preflight verified; log={log_path}")
        return 0
    if args.ack != ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M4T0 candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m4t0_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M4T0 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        print(
            "M4T0 candidate flash completed but the original Odin device did not disconnect; "
            "rolling back without claiming self-download proof.",
            file=sys.stderr,
        )
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            print(f"rollback download mode unavailable after no-disconnect; manual recovery required. log={log_path}", file=sys.stderr)
            return 4
        rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
        rollback_label = f"{args.rollback_target}_rollback_no_disconnect"
        rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, rollback_label)
        if rollback_rc != 0:
            print(f"rollback Odin flash failed rc={rollback_rc}; log={log_path}", file=sys.stderr)
            return rollback_rc or 5
        post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
        if post_rollback_serial is None:
            print(f"rollback transferred but Android/root verification failed; log={log_path}", file=sys.stderr)
            return 6
        append_log(log_path, "m4t0_result=no-proof-original-download-never-disconnected")
        collect_android_pstore(run_dir, log_path, "post_rollback_no_disconnect", post_rollback_serial, marker=EXPECTED_M4T0_MARKER)
        return 7

    print("M4T0 candidate flashed. Waiting for candidate's first-action download reboot.")
    rollback_device = observe_until_odin(run_dir, log_path, args.self_download_wait_sec, odin)
    if rollback_device is None:
        print(f"M4T0 self-download did not appear; manual download-mode recovery required. log={log_path}", file=sys.stderr)
        return 4

    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    rollback_label = f"{args.rollback_target}_rollback"
    rollback_rc = flash_ap(odin, rollback_ap, rollback_device, log_path, rollback_label)
    if rollback_rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            rollback_rc = flash_ap(odin, stock_rollback_ap, fallback_device, log_path, "stock_fallback")
    if rollback_rc != 0:
        print(f"rollback Odin flash failed rc={rollback_rc}; log={log_path}", file=sys.stderr)
        return rollback_rc or 5

    expect_root = args.rollback_target == ROLLBACK_MAGISK
    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=expect_root)
    android_ok = post_rollback_serial is not None
    append_log(log_path, f"post_rollback_android_ok={int(android_ok)} expect_root={int(expect_root)}")
    if not android_ok:
        print(f"rollback transferred but Android/root verification failed; log={log_path}", file=sys.stderr)
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M4T0_MARKER)
    print(f"M4T0 live gate completed with self-download and rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
