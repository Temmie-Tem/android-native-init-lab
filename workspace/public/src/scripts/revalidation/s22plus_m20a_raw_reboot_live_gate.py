#!/usr/bin/env python3
"""Guarded S22+ M20A raw reboot-download native-init live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M20A is the first post-M19 floor split.  Its first runtime action is one raw
arm64 reboot(2) syscall requesting "download".  If download mode reappears
after the candidate flash and after the original Odin endpoint disconnects, the
raw reboot path still works under the current operator timing.  If no later
endpoint appears, manual download-mode entry is required before rollback.
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


LIVE_ACK_TOKEN = "S22PLUS-M20A-RAW-REBOOT-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M20A-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M20A_LABEL = "M20A_RAW"
EXPECTED_M20A_AP_SHA256 = "795e071107fdd7011a5acdc48ca7415273e5f2a3e19af45386702617292021fc"
EXPECTED_M20A_BOOT_SHA256 = "4fada63c986abc774e2a41eebc590f0635f1f1dcc8a207baa8d02cbfeb20eeb5"
EXPECTED_M20A_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M20A_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M20A_INIT_SHA256 = "4b27b050b11a4f0f28f340172515a397f65e1d151507e149bc9cbe47c6beab17"
EXPECTED_M20A_SOURCE_SHA256 = "ffce971408433acfb9bebb5bef236dab572fc8266d53a6c09e68419039f4abf1"
EXPECTED_M20A_MARKER = "S22_NATIVE_INIT_M20A_RAW_REBOOT"

DEFAULT_M20A_AP = Path("workspace/private/outputs/s22plus_native_init/m20_floor_split_v0_1/M20A_RAW/odin4/AP.tar.md5")
DEFAULT_M20A_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m20_floor_split_v0_1/M20A_RAW/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m20a_raw_reboot_live_gate_{stamp}")
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
        "S22+ M20A raw-reboot floor-split native-init boot-only",
        EXPECTED_M20A_AP_SHA256,
        EXPECTED_M20A_BOOT_SHA256,
        EXPECTED_M20A_BASE_BOOT_SHA256,
        EXPECTED_M20A_KERNEL_SHA256,
        EXPECTED_M20A_INIT_SHA256,
        EXPECTED_M20A_SOURCE_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_M20A_LABEL,
        "first-action raw `reboot(..., \"download\")` positive control",
        "no fs setup",
        "no marker write",
        "M20B/M20C not authorized",
        "host-observed self-download after the original Odin endpoint disconnects",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M20A live authorization markers: {missing}")


def verify_m20a_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M20A manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    init_info = data.get("init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m20a_manifest_path={path}")
    append_log(log_path, f"m20a_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m20a_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m20a_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m20a_manifest_init_file={init_info.get('file', '')}")

    required_hashes = {
        "ap_tar_md5": EXPECTED_M20A_AP_SHA256,
        "boot_img": EXPECTED_M20A_BOOT_SHA256,
        "base_boot": EXPECTED_M20A_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M20A_KERNEL_SHA256,
        "init": EXPECTED_M20A_INIT_SHA256,
        "source": EXPECTED_M20A_SOURCE_SHA256,
    }
    for key, expected in required_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M20A manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M20A manifest tar members mismatch: {tar_members_seen!r}")

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
        "auto_reboot": "download",
        "on_reboot_syscall_return": "infinite-park",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M20A manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M20A manifest did not replace /init")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M20A must not inject module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M20A must not inject module-list files into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [EXPECTED_M20A_MARKER, "download"]:
        if required not in required_strings:
            raise SystemExit(f"M20A required string missing from manifest: {required}")
    objdump = str(init_info.get("objdump", ""))
    reboot_nr_lines = [
        line
        for line in objdump.splitlines()
        if "mov" in line and "x8" in line and "#0x8e" in line
    ]
    if not reboot_nr_lines:
        raise SystemExit("M20A /init does not load arm64 __NR_reboot (142)")


def verify_current_boot_hash(log_path: Path, serial: str) -> None:
    result = adb_shell(
        "su -c 'dd if=/dev/block/by-name/boot bs=4096 2>/dev/null | sha256sum'",
        serial=serial,
        timeout=45.0,
    )
    text = result.stdout + result.stderr
    append_log(log_path, f"current_boot_hash_rc={result.returncode}")
    append_log(log_path, text)
    if result.returncode != 0 or EXPECTED_M20A_BASE_BOOT_SHA256 not in text:
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


def observe_until_odin(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> str | None:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m20a_self_download_{iteration:03d}"
        host_snapshot(run_dir, log_path, label, odin)
        devices = odin_devices(odin, log_path, f"{label}-extra")
        if len(devices) == 1:
            append_log(log_path, f"m20a_self_download_seen=1 device={devices[0]}")
            return devices[0]
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M20A observation: {devices}")
        rows = adb_rows(log_path, f"{label}-extra")
        if rows:
            append_log(log_path, f"m20a_candidate_adb_rows={rows}")
        time.sleep(1.0)
    append_log(log_path, "m20a_self_download_seen=0")
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
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M20A_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m20a-ap", type=Path, default=DEFAULT_M20A_AP)
    parser.add_argument("--m20a-manifest", type=Path, default=DEFAULT_M20A_MANIFEST)
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
    log_path = run_dir / "s22plus_m20a_raw_reboot_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m20a raw-reboot live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m20a_ap = resolve(root, args.m20a_ap)
    m20a_manifest = resolve(root, args.m20a_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m20a_ap, EXPECTED_M20A_AP_SHA256, "m20a_candidate", log_path)
    verify_m20a_manifest(m20a_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.offline_check:
        print(f"offline-check ok: M20A candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M20A rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_current_boot_hash(log_path, selected_serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M20A candidate, rollback APs, AGENTS exception, "
            f"current boot hash, and Android preflight verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M20A candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m20a_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M20A candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(
        odin,
        log_path,
        "post-candidate-disconnect",
        args.post_flash_disconnect_wait_sec,
    )
    if not left_download:
        print(
            "M20A candidate flash completed but the original Odin device did not disconnect; "
            "rolling back without claiming self-download proof.",
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
        append_log(log_path, "m20a_result=no-proof-original-download-never-disconnected")
        collect_android_pstore(
            run_dir,
            log_path,
            "post_rollback_no_disconnect",
            post_rollback_serial,
            marker=EXPECTED_M20A_MARKER,
        )
        return 7

    print("M20A candidate flashed. Waiting for candidate's raw reboot-download syscall.")
    rollback_device = observe_until_odin(run_dir, log_path, args.self_download_wait_sec, odin)
    if rollback_device is None:
        print(
            "M20A self-download did not appear. If the device is parked or looping, enter download mode manually "
            "and run --rollback-from-download.",
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
        print(f"rollback Odin flash failed rc={rollback_rc}; log={log_path}", file=sys.stderr)
        return rollback_rc or 5

    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
    if post_rollback_serial is None:
        print(f"rollback transferred but Android/root verification failed; log={log_path}", file=sys.stderr)
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", post_rollback_serial, marker=EXPECTED_M20A_MARKER)
    print(f"M20A live gate completed with self-download and rollback ok; log={log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
