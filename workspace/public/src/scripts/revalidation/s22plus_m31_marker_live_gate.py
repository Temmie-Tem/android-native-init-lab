#!/usr/bin/env python3
"""Guarded S22+ M3.1 marker-only native-init live gate.

Dry-run is the default.  Live mode requires:

- the exact SHA-pinned M3.1 AGENTS.md exception;
- exact M3.1 boot-only AP hash and single `boot.img.lz4` tar member;
- exact pinned Magisk boot-only rollback AP and stock boot-only fallback AP;
- a single normal Android ADB target matching SM-S906N/g0q/S906NKSS7FYG8;
- an explicit ack token.

M3.1 is marker-only.  It does not bring up USB/NCM itself; the host observes
download-mode return and collects pstore after rollback.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from s22plus_m3_observable_live_gate import (
    EXPECTED_BUILD,
    EXPECTED_DEVICE,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_MEMBER,
    EXPECTED_MODEL,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    DEFAULT_STOCK_ROLLBACK_AP,
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
    sha256_file,
    tar_members,
    utc_now,
    verify_ap,
    wait_for_odin,
    run,
)


ACK_TOKEN = "S22PLUS-M31-MARKER-LIVE-GATE"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M31_AP_SHA256 = "999beeb67f73c39eaa0b637bc3c62fe2d8474fa707110640ae51adca0fbd2cfb"
EXPECTED_M31_BOOT_SHA256 = "f3dea68c02be295141265820f4acdd425a12460e05957edf75c83a62c4a617c5"
EXPECTED_M31_MARKER = "S22_NATIVE_INIT_MARKER_ONLY_M31"

DEFAULT_M31_AP = Path("workspace/private/outputs/s22plus_native_init/marker_m31_v0_1/odin4/AP.tar.md5")
DEFAULT_M31_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/marker_m31_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested
    else:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
        run_dir = DEFAULT_RUN_ROOT / f"s22plus_m31_marker_live_gate_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def verify_m31_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M3.1 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m31_manifest_path={path}")
    append_log(log_path, f"m31_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m31_manifest_safety={json.dumps(safety, sort_keys=True)}")
    if hashes.get("ap_tar_md5") != EXPECTED_M31_AP_SHA256:
        raise SystemExit("M3.1 manifest AP hash does not match expected M3.1 AP")
    if hashes.get("boot_img") != EXPECTED_M31_BOOT_SHA256:
        raise SystemExit("M3.1 manifest boot image hash does not match expected M3.1 boot image")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M3.1 manifest tar members mismatch: {tar_members_seen!r}")
    if safety.get("auto_reboot") != "download-after-10s-observation":
        raise SystemExit(f"M3.1 manifest auto_reboot mismatch: {safety.get('auto_reboot')!r}")
    if safety.get("module_insertions") is not False:
        raise SystemExit(f"M3.1 manifest module_insertions mismatch: {safety.get('module_insertions')!r}")
    if safety.get("configfs_runtime_gadget") is not False:
        raise SystemExit(f"M3.1 manifest configfs_runtime_gadget mismatch: {safety.get('configfs_runtime_gadget')!r}")


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M3.1 marker-only native-init boot-only",
        EXPECTED_M31_AP_SHA256,
        EXPECTED_M31_BOOT_SHA256,
        ACK_TOKEN,
        EXPECTED_M31_MARKER,
        "fallback `/dev/pmsg0`",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M3.1 live authorization markers: {missing}")


def observe_candidate(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> None:
    host_snapshot(run_dir, log_path, "before_candidate", odin)
    deadline = utc_seconds() + seconds
    iteration = 0
    while utc_seconds() < deadline:
        iteration += 1
        label = f"candidate_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if devices:
            append_log(log_path, f"candidate_odin_seen={devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"candidate_adb_rows={rows}")
        sleep_short()


def utc_seconds() -> float:
    import time

    return time.monotonic()


def sleep_short() -> None:
    import time

    time.sleep(2.0)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m31-ap", type=Path, default=DEFAULT_M31_AP)
    parser.add_argument("--m31-manifest", type=Path, default=DEFAULT_M31_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--candidate-observe-sec", type=int, default=35)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--rollback-wait-sec", type=int, default=180)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack", help=f"required with --live: {ACK_TOKEN}")
    args = parser.parse_args(argv)

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m31_marker_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m31 marker live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m31_ap = resolve(root, args.m31_ap)
    m31_manifest = resolve(root, args.m31_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m31_ap, EXPECTED_M31_AP_SHA256, "m31_candidate", log_path)
    verify_m31_manifest(m31_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)
    selected_serial = require_current_android(log_path, args.serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M3.1 candidate, rollback APs, AGENTS exception, and Android preflight verified; log={log_path}")
        return 0
    if args.ack != ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M3.1 candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m31_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M3.1 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    observe_candidate(run_dir, log_path, args.candidate_observe_sec, odin)
    print("M3.1 observation window ended. Waiting for download mode for rollback.")
    rollback_device = wait_for_odin(odin, log_path, "rollback-wait", args.rollback_wait_sec)
    if rollback_device is None:
        print(f"rollback download mode did not appear; manual recovery required. log={log_path}", file=sys.stderr)
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
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M31_MARKER)
    print(f"M3.1 live gate completed with rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
