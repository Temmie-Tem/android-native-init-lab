#!/usr/bin/env python3
"""Guarded S22+ M4T2 raw-park native-init live gate.

Dry-run is the default.  Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M4T2 is intentionally not self-rolling-back.  If the raw PID1 runs correctly it
parks forever, so the helper cannot regain ADB or Odin by itself.  After a dark
park or bootloop observation, the operator must manually enter download mode
and run this helper's rollback-only mode.
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


LIVE_ACK_TOKEN = "S22PLUS-M4T2-RAW-PARK-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M4T2-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M4T2_AP_SHA256 = "66d7f24b348702f58efbe1945b0d2751052ed27f6ce1f6fc4e5da63f3a585b24"
EXPECTED_M4T2_BOOT_SHA256 = "8103bce76fb3e41d71b64735a64d2f2f29431a44ea1c9a85dc0bc151d71afd15"
EXPECTED_M4T2_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M4T2_RAW_INIT_SHA256 = "b8371e3ac671ff71e9be752b8ff1087a4f20811c871a43ca8e698eee47783d12"
EXPECTED_M4T2_MARKER = "S22_NATIVE_INIT_PARK_M4T2"

DEFAULT_M4T2_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m4t2_park_v0_1/odin4/AP.tar.md5")
DEFAULT_M4T2_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m4t2_park_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested
    else:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
        run_dir = DEFAULT_RUN_ROOT / f"s22plus_m4t2_park_live_gate_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M4T2 raw-park native-init boot-only",
        EXPECTED_M4T2_AP_SHA256,
        EXPECTED_M4T2_BOOT_SHA256,
        EXPECTED_M4T2_BASE_BOOT_SHA256,
        EXPECTED_M4T2_RAW_INIT_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "first candidate action is infinite park",
        "no libc startup",
        "no syscalls",
        "no reboot request",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M4T2 live authorization markers: {missing}")


def verify_m4t2_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M4T2 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    raw_init = data.get("raw_init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m4t2_manifest_path={path}")
    append_log(log_path, f"m4t2_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m4t2_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m4t2_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m4t2_manifest_raw_init_file={raw_init.get('file', '')}")
    if hashes.get("ap_tar_md5") != EXPECTED_M4T2_AP_SHA256:
        raise SystemExit("M4T2 manifest AP hash does not match expected M4T2 AP")
    if hashes.get("boot_img") != EXPECTED_M4T2_BOOT_SHA256:
        raise SystemExit("M4T2 manifest boot image hash does not match expected M4T2 boot image")
    if hashes.get("base_boot") != EXPECTED_M4T2_BASE_BOOT_SHA256:
        raise SystemExit("M4T2 manifest base boot hash does not match expected known-booting Magisk boot")
    if hashes.get("raw_park_init") != EXPECTED_M4T2_RAW_INIT_SHA256:
        raise SystemExit("M4T2 manifest raw init hash mismatch")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M4T2 manifest tar members mismatch: {tar_members_seen!r}")
    required_safety = {
        "construction": "magiskboot unpack/repack; replace only ramdisk /init",
        "mkbootimg_from_scratch": False,
        "first_candidate_action": "infinite-park",
        "libc": False,
        "syscalls": False,
        "reboot_request": False,
        "marker_write": False,
        "module_insertions": False,
        "configfs_runtime_gadget": False,
        "watchdog": "not-touched",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M4T2 manifest {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit(f"M4T2 replaced ramdisk entry mismatch: {ramdisk.get('replaced_entry')!r}")


def observe_transport(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m4t2_observe_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, f"m4t2_odin_seen=1 device={devices[0]}")
            return ("odin", devices[0])
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M4T2 observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        usable = [row for row in rows if row[1] == "device"]
        if len(usable) == 1:
            append_log(log_path, f"m4t2_adb_seen=1 serial={usable[0][0]}")
            return ("adb", usable[0][0])
        if len(usable) > 1:
            raise SystemExit(f"refusing ambiguous ADB devices during M4T2 observation: {usable}")
        time.sleep(1.0)
    append_log(log_path, "m4t2_transport_seen=0")
    return ("none", None)


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
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M4T2_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4t2-ap", type=Path, default=DEFAULT_M4T2_AP)
    parser.add_argument("--m4t2-manifest", type=Path, default=DEFAULT_M4T2_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--observation-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    if args.live and args.rollback_from_download:
        raise SystemExit("--live and --rollback-from-download are mutually exclusive")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m4t2_park_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m4t2 raw-park live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m4t2_ap = resolve(root, args.m4t2_ap)
    m4t2_manifest = resolve(root, args.m4t2_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m4t2_ap, EXPECTED_M4T2_AP_SHA256, "m4t2_candidate", log_path)
    verify_m4t2_manifest(m4t2_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M4T2 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M4T2 candidate, rollback APs, AGENTS exception, and Android preflight verified; log={log_path}")
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M4T2 candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m4t2_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M4T2 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    kind, value = observe_transport(run_dir, log_path, args.observation_sec, odin)
    if kind == "odin" and value:
        append_log(log_path, "m4t2_result=transport-returned-odin-rolling-back")
        rollback_rc = flash_ap(odin, rollback_ap, value, log_path, f"{args.rollback_target}_rollback_after_transport")
        if rollback_rc != 0:
            return rollback_rc or 5
        serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
        if serial is None:
            return 6
        collect_android_pstore(run_dir, log_path, "post_rollback_transport_returned", serial, marker=EXPECTED_M4T2_MARKER)
        return 7
    if kind == "adb":
        append_log(log_path, f"m4t2_result=unexpected-adb-return serial={value}")
        print(f"M4T2 unexpectedly returned ADB; manual assessment required. log={log_path}", file=sys.stderr)
        return 8

    append_log(log_path, "m4t2_result=no-transport-after-observation-manual-download-required")
    print(
        "M4T2 produced no ADB/Odin transport during the observation window. "
        "Manual download-mode entry is required, then run --rollback-from-download.",
        file=sys.stderr,
    )
    return 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
