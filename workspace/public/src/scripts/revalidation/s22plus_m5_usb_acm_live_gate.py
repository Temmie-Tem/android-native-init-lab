#!/usr/bin/env python3
"""Guarded S22+ M5 USB-ACM native-init live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M5 does not auto-reboot. If the candidate succeeds, the expected proof is a
host-visible USB ACM device for the configfs ss_acm.0 gadget. The helper then
waits for the operator to enter download mode and rolls back to the pinned
Magisk boot-only AP. If ACM does not appear, the operator must enter download
mode and use this helper's rollback-only mode.
"""

from __future__ import annotations

import argparse
import json
import os
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


LIVE_ACK_TOKEN = "S22PLUS-M5-USB-ACM-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M5-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M5_AP_SHA256 = "8af4fd29a4268d30ac988ede6d32852837301ca80d3295ad41e539ae4913a170"
EXPECTED_M5_BOOT_SHA256 = "aeed53543fb277765ddb1657e6b8da33b27db876257b41a95e965a26f7cf1afb"
EXPECTED_M5_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M5_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M5_INIT_SHA256 = "f677ede617bbf243686a58517260c5b025bc03efbfc012087c72f17ee5e39f41"
EXPECTED_M5_MODULE_MANIFEST_SHA256 = "1c22c93496e03a7df6dd74959511797b6d033b74361d3d3733d7be8269a5fa05"
EXPECTED_M5_MARKER = "S22_NATIVE_INIT_USB_ACM_M5"
EXPECTED_M5_USB_VENDOR = "04e8"
EXPECTED_M5_USB_PRODUCT = "685d"
EXPECTED_M5_USB_SERIAL = "S22M5ACM0001"
EXPECTED_M5_MODULE_COUNT = 26
EXPECTED_M5_MODULE_BYTES = 2854024

DEFAULT_M5_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m5_usb_acm_v0_1/odin4/AP.tar.md5")
DEFAULT_M5_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m5_usb_acm_v0_1/manifest.json")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = requested
    else:
        stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
        run_dir = DEFAULT_RUN_ROOT / f"s22plus_m5_usb_acm_live_gate_{stamp}"
    run_dir = resolve(root, run_dir)
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    normalized = " ".join(agents.split())
    required = [
        "S22+ M5 USB-ACM native-init boot-only",
        EXPECTED_M5_AP_SHA256,
        EXPECTED_M5_BOOT_SHA256,
        EXPECTED_M5_BASE_BOOT_SHA256,
        EXPECTED_M5_KERNEL_SHA256,
        EXPECTED_M5_INIT_SHA256,
        EXPECTED_M5_MODULE_MANIFEST_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "configfs `ss_acm.0` gadget",
        "manual download-mode entry before rollback",
    ]
    missing = [item for item in required if item not in normalized]
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M5 live authorization markers: {missing}")


def verify_m5_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M5 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    module_summary = data.get("module_summary", {})
    m5_init = data.get("m5_init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m5_manifest_path={path}")
    append_log(log_path, f"m5_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m5_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m5_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m5_manifest_module_summary={json.dumps(module_summary, sort_keys=True)}")
    if hashes.get("ap_tar_md5") != EXPECTED_M5_AP_SHA256:
        raise SystemExit("M5 manifest AP hash does not match expected M5 AP")
    if hashes.get("boot_img") != EXPECTED_M5_BOOT_SHA256:
        raise SystemExit("M5 manifest boot image hash does not match expected M5 boot image")
    if hashes.get("base_boot") != EXPECTED_M5_BASE_BOOT_SHA256:
        raise SystemExit("M5 manifest base boot hash does not match known-booting Magisk boot")
    if hashes.get("kernel") != EXPECTED_M5_KERNEL_SHA256:
        raise SystemExit("M5 manifest kernel hash mismatch")
    if hashes.get("m5_init") != EXPECTED_M5_INIT_SHA256:
        raise SystemExit("M5 manifest init hash mismatch")
    if hashes.get("module_bundle_manifest") != EXPECTED_M5_MODULE_MANIFEST_SHA256:
        raise SystemExit("M5 manifest module-bundle manifest hash mismatch")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M5 manifest tar members mismatch: {tar_members_seen!r}")
    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace ramdisk /init and add USB module bundle",
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": False,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_insertions": "FYG8 USB-first 26-module bundle only",
        "configfs_runtime_gadget": "ss_acm.0 only",
        "watchdog": "not-touched",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M5 manifest {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit(f"M5 replaced ramdisk entry mismatch: {ramdisk.get('replaced_entry')!r}")
    if ramdisk.get("module_count") != EXPECTED_M5_MODULE_COUNT:
        raise SystemExit(f"M5 ramdisk module count mismatch: {ramdisk.get('module_count')!r}")
    if module_summary.get("module_count") != EXPECTED_M5_MODULE_COUNT:
        raise SystemExit(f"M5 module count mismatch: {module_summary.get('module_count')!r}")
    if module_summary.get("total_bytes") != EXPECTED_M5_MODULE_BYTES:
        raise SystemExit(f"M5 module byte count mismatch: {module_summary.get('total_bytes')!r}")
    required_strings = set(m5_init.get("required_strings", []))
    for required in [
        EXPECTED_M5_MARKER,
        "usb_first_modules=26",
        "gadget=ss_acm.0",
        "tty=/dev/ttyGS0",
        "no_android_handoff=1",
        "no_auto_reboot=1",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M5 required string missing from manifest: {required}")


def acm_devices(log_path: Path, label: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for path in sorted(Path("/dev").glob("ttyACM*")):
        props: dict[str, str] = {}
        result = run(["udevadm", "info", "--query=property", f"--name={path}"], timeout=5.0)
        for line in (result.stdout + result.stderr).splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                props[key] = value
        devices.append(
            {
                "path": str(path),
                "udevadm_rc": result.returncode,
                "vendor": props.get("ID_VENDOR_ID", ""),
                "product": props.get("ID_MODEL_ID", ""),
                "model": props.get("ID_MODEL", ""),
                "serial": props.get("ID_SERIAL_SHORT", ""),
                "driver": props.get("ID_USB_DRIVER", ""),
                "interface": props.get("ID_USB_INTERFACE_NUM", ""),
                "devlinks": props.get("DEVLINKS", ""),
            }
        )
    append_log(log_path, f"{label}_acm_devices={json.dumps(devices, sort_keys=True)}")
    return devices


def is_m5_acm(device: dict[str, Any]) -> bool:
    model = str(device.get("model", ""))
    return (
        device.get("vendor") == EXPECTED_M5_USB_VENDOR
        and device.get("product") == EXPECTED_M5_USB_PRODUCT
    ) or device.get("serial") == EXPECTED_M5_USB_SERIAL or "S22_Native_Init_M5_ACM" in model


def read_acm_banner(path: str, log_path: Path) -> bytes:
    payload = b""
    fd: int | None = None
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                chunk = os.read(fd, 512)
            except BlockingIOError:
                chunk = b""
            except OSError as exc:
                append_log(log_path, f"m5_acm_read_error path={path} errno={exc.errno}")
                break
            if chunk:
                payload += chunk
                if b"\n" in payload or len(payload) >= 512:
                    break
            time.sleep(0.1)
    except OSError as exc:
        append_log(log_path, f"m5_acm_open_error path={path} errno={exc.errno}")
    finally:
        if fd is not None:
            os.close(fd)
    append_log(log_path, f"m5_acm_banner_path={path} bytes={len(payload)} payload={payload!r}")
    return payload


def observe_m5_acm(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m5_acm_observe_{iteration:03d}"
        if iteration == 1 or iteration % 5 == 0:
            host_snapshot(run_dir, log_path, label, odin)
        for device in acm_devices(log_path, label):
            if is_m5_acm(device):
                path = str(device["path"])
                payload = read_acm_banner(path, log_path)
                append_log(log_path, f"m5_acm_seen=1 path={path} banner_found={int(EXPECTED_M5_MARKER.encode('ascii') in payload)}")
                return ("acm", path)
        devices = odin_devices(odin, log_path, f"{label}-odin")
        if len(devices) == 1:
            append_log(log_path, f"m5_odin_returned=1 device={devices[0]}")
            return ("odin", devices[0])
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M5 observation: {devices}")
        rows = adb_rows(log_path, f"{label}-adb")
        usable = [row for row in rows if row[1] == "device"]
        if len(usable) == 1:
            append_log(log_path, f"m5_adb_returned=1 serial={usable[0][0]}")
            return ("adb", usable[0][0])
        if len(usable) > 1:
            raise SystemExit(f"refusing ambiguous ADB devices during M5 observation: {usable}")
        time.sleep(1.0)
    append_log(log_path, "m5_acm_seen=0")
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
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M5_MARKER)
    return 0


def rollback_after_seen_download(odin: Path, rollback_ap: Path, run_dir: Path, log_path: Path, rollback_target: str, android_wait_sec: int, odin_device: str) -> int:
    rollback_rc = flash_ap(odin, rollback_ap, odin_device, log_path, f"{rollback_target}_rollback")
    if rollback_rc != 0 and rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        return rollback_rc or 5
    if rollback_rc != 0:
        return rollback_rc or 5
    serial = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if serial is None:
        return 6
    collect_android_pstore(run_dir, log_path, "post_rollback", serial, marker=EXPECTED_M5_MARKER)
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m5-ap", type=Path, default=DEFAULT_M5_AP)
    parser.add_argument("--m5-manifest", type=Path, default=DEFAULT_M5_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--acm-observe-sec", type=int, default=120)
    parser.add_argument("--post-acm-rollback-wait-sec", type=int, default=300)
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
    log_path = run_dir / "s22plus_m5_usb_acm_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus m5 usb-acm live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m5_ap = resolve(root, args.m5_ap)
    m5_manifest = resolve(root, args.m5_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_agents_exception(root, log_path)
    verify_ap(m5_ap, EXPECTED_M5_AP_SHA256, "m5_candidate", log_path)
    verify_m5_manifest(m5_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M5 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    host_snapshot(run_dir, log_path, "dryrun_current", odin)
    acm_devices(log_path, "dryrun_current")

    if not args.live:
        print(f"dry-run ok: M5 candidate, rollback APs, AGENTS exception, Android preflight, and ACM baseline verified; log={log_path}")
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        print("download mode did not appear for M5 candidate flash", file=sys.stderr)
        return 2

    candidate_rc = flash_ap(odin, m5_ap, odin_device, log_path, "candidate")
    if candidate_rc != 0:
        print(f"M5 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    kind, value = observe_m5_acm(run_dir, log_path, args.acm_observe_sec, odin)
    if kind == "acm":
        print(
            "M5 ACM device observed. Inspect it now if needed, then enter download mode; "
            "the helper will roll back when Odin appears."
        )
        rollback_device = wait_for_odin(odin, log_path, "post-acm-rollback-wait", args.post_acm_rollback_wait_sec)
        if rollback_device is None:
            print(
                "M5 ACM proof was observed, but download mode did not appear for rollback. "
                "Enter download mode manually and run --rollback-from-download.",
                file=sys.stderr,
            )
            append_log(log_path, "m5_result=acm-proof-rollback-still-required")
            return 8
        rc = rollback_after_seen_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec, rollback_device)
        if rc == 0:
            append_log(log_path, "m5_result=acm-proof-rollback-ok")
        return rc
    if kind == "odin" and value:
        append_log(log_path, "m5_result=unexpected-odin-return-rolling-back")
        return rollback_after_seen_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec, value)
    if kind == "adb":
        append_log(log_path, "m5_result=unexpected-adb-return-no-rollback")
        print(f"M5 unexpectedly returned ADB transport {value}; inspect manually before further action. log={log_path}", file=sys.stderr)
        return 7

    print(
        "M5 ACM did not appear in the observation window. Enter download mode manually "
        "and run --rollback-from-download.",
        file=sys.stderr,
    )
    return 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
