#!/usr/bin/env python3
"""Guarded S22+ M24 pmsg-step native-init live gate.

Default dry-run and live modes require a fresh SHA-pinned AGENTS.md exception
plus a recovered rooted Android baseline.  --offline-check verifies only the
host-built M24 package and rollback APs without touching any device.

M24 keeps the M23 DTS-exact QMP/DWC3 module closure and adds A90_STEP:M24
markers to /dev/pmsg0.  If it loops, rollback is operator-attended Download
mode, then this helper captures pstore/pmsg, /proc/last_kmsg, and Samsung
reset-context surfaces.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
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
    acm_devices,
    read_acm_banner,
    verify_android_stability,
    verify_current_boot_hash,
)
from s22plus_m23_dts_exact_qmp_reset_summary_live_gate import EXPECTED_M23_MODULES
from s22plus_reset_reason_readonly_probe import collect as collect_reset_reason


LIVE_ACK_TOKEN = "S22PLUS-M24-PMSG-STEPS-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M24-PMSG-STEPS-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_M24_AP_SHA256 = "e09538024abe89585486d54856a5c86bef666da456f314084d4d4d8bb6553fe8"
EXPECTED_M24_BOOT_SHA256 = "0cccc003687227c4265081fa59d440f4be3e7f40fbb64aca2a3930ca7d5ca3df"
EXPECTED_M24_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_M24_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M24_INIT_SHA256 = "4086d18f453980893fa1b8022f93991775b0ee28a6088f1216de82b74cbaf341"
EXPECTED_M24_MODULE_LIST_SHA256 = "a542b86aee8d2b09d0ca233e0a81d7deb8919a77657122d91f3b46e0a7933349"
EXPECTED_M24_SOURCE_SHA256 = "f9a060f7804571c036631c954b3e88c064aa33176d7d8ec6abe9da8b8bf84bdd"
EXPECTED_M24_VENDOR_DTB_SHA256 = "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e"
EXPECTED_M24_MARKER = "S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS"
EXPECTED_M24_PMSG_PREFIX = "A90_STEP:M24:"
EXPECTED_M24_USB_VENDOR = "04e8"
EXPECTED_M24_USB_PRODUCT = "685d"
EXPECTED_M24_USB_SERIAL = "S22M24PMSG001"
EXPECTED_M24_MODULES = EXPECTED_M23_MODULES

DEFAULT_M24_AP = Path("workspace/private/outputs/s22plus_native_init/inplace_m24_pmsg_steps_v0_1/odin4/AP.tar.md5")
DEFAULT_M24_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/inplace_m24_pmsg_steps_v0_1/manifest.json")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m24_pmsg_steps_live_gate_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def record_timeline_event(run_dir: Path, name: str) -> None:
    path = run_dir / "timeline.json"
    events: list[dict[str, str]] = []
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if sorted(data.keys()) != ["events"] or not isinstance(data.get("events"), list):
            raise SystemExit(f"refusing non-canonical timeline shape: {path}")
        events = data["events"]
    events.append({"name": name, "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
    path.write_text(json.dumps({"events": events}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def policy_required_markers() -> list[str]:
    return [
        "S22+ M24 pmsg-step DTS-exact QMP/DWC3 native-init boot-only",
        EXPECTED_M24_AP_SHA256,
        EXPECTED_M24_BOOT_SHA256,
        EXPECTED_M24_BASE_BOOT_SHA256,
        EXPECTED_M24_KERNEL_SHA256,
        EXPECTED_M24_INIT_SHA256,
        EXPECTED_M24_MODULE_LIST_SHA256,
        EXPECTED_M24_SOURCE_SHA256,
        EXPECTED_M24_VENDOR_DTB_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        "43-module DTS-derived QMP/DWC3/HS-PHY/provider closure",
        "module_group=dts_exact_qmp",
        "module_count=43",
        "s22plus_m24_pmsg_steps.modules",
        "pmsg step markers",
        EXPECTED_M24_PMSG_PREFIX,
        "/dev/pmsg0",
        "fallback_pmsg_major=507",
        "module_prepare",
        "module_finit",
        "pmsg/pstore/last_kmsg/reset-context post-rollback capture",
        "/proc/reset_summary",
        "/proc/reset_klog",
        "/proc/reset_history",
        "/proc/reset_tzlog",
        "/proc/enhanced_boot_stat",
        "manual download-mode rollback",
        "no reboot beacon",
        "EUD extcon excluded",
        "no EUD sysfs write",
        *EXPECTED_M24_MODULES,
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [item for item in policy_required_markers() if item not in normalized]


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M24 pmsg-step live authorization markers: {missing}")


def verify_m24_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M24 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    ramdisk = data.get("ramdisk", {})
    m24_init = data.get("m24_init", {})
    tar_members_seen = data.get("tar_members")
    append_log(log_path, f"m24_manifest_path={path}")
    append_log(log_path, f"m24_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m24_manifest_safety={json.dumps(safety, sort_keys=True)}")

    expected_hashes = {
        "ap_tar_md5": EXPECTED_M24_AP_SHA256,
        "boot_img": EXPECTED_M24_BOOT_SHA256,
        "base_boot": EXPECTED_M24_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M24_KERNEL_SHA256,
        "m24_init": EXPECTED_M24_INIT_SHA256,
        "m24_pmsg_steps": EXPECTED_M24_MODULE_LIST_SHA256,
        "generated_source": EXPECTED_M24_SOURCE_SHA256,
        "vendor_dtb": EXPECTED_M24_VENDOR_DTB_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M24 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M24 manifest tar members mismatch: {tar_members_seen!r}")

    required_safety: dict[str, Any] = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "construction": "magiskboot unpack/repack; replace ramdisk /init and add one module-list text file",
        "runtime": "freestanding-raw-syscall",
        "glibc_static_startup": False,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": False,
        "reboot_syscall": False,
        "host_commanded_reboot_download": False,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_binary_injection": False,
        "module_list_path": "/s22plus_m24_pmsg_steps.modules",
        "module_subset": "same 43-module DTS-derived QMP/DWC3/HS-PHY/provider closure as M23",
        "configfs_runtime_gadget": "ss_acm.0 only",
        "udc_binding": "a600000.dwc3 only; never dummy_udc.0",
        "usb_role_force": "attempt /sys/class/usb_role/*/role=device",
        "eud": "EUD extcon observed but intentionally not loaded/opened/enabled in this candidate",
        "watchdog": "gh_virt_wdt/qcom_wdt_core reset path blocklisted; sec_debug/minidump/abc also blocklisted",
        "pmsg_step_markers": True,
        "pmsg_path": "/dev/pmsg0",
        "pmsg_fallback_chrdev": "major=507 minor=0 mode=0222",
        "pmsg_marker_prefix": EXPECTED_M24_PMSG_PREFIX,
        "observation_model": "park plus host ACM enumeration; if it loops, rollback then inspect retained pmsg/pstore/reset surfaces",
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M24 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M24 manifest did not replace /init")
    if ramdisk.get("added_subset_entry") != "s22plus_m24_pmsg_steps.modules":
        raise SystemExit("M24 manifest did not add the expected module-list file")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 1:
        raise SystemExit("M24 must inject exactly one module-list text file into boot ramdisk")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M24 must not inject vendor modules into boot ramdisk")

    dts = data.get("dts_exact_qmp", {})
    closure = dts.get("dts_exact_qmp", {})
    if dts.get("dtb_blob_count") != 4:
        raise SystemExit(f"M24 expected four vendor DTB blobs, got {dts.get('dtb_blob_count')!r}")
    if dts.get("eud_policy") != "EUD extcon observed but excluded; no EUD enable/open because Phase-B proved TZ-gated rc:-22":
        raise SystemExit(f"M24 EUD policy mismatch: {dts.get('eud_policy')!r}")
    if len(dts.get("blob_results", [])) != 4:
        raise SystemExit("M24 must record four per-DTB closure results")
    if closure.get("subset_count") != 43:
        raise SystemExit(f"M24 module subset count mismatch: {closure.get('subset_count')!r}")
    if closure.get("subset") != EXPECTED_M24_MODULES:
        raise SystemExit(f"M24 module subset mismatch: {closure.get('subset')!r}")
    if closure.get("blocked_dependency_edges") != ["abc.ko", "minidump.ko", "sec_debug.ko"]:
        raise SystemExit(f"M24 blocked dependency edges mismatch: {closure.get('blocked_dependency_edges')!r}")
    blocklist = closure.get("blocklist", [])
    for module in ("gh_virt_wdt.ko", "qcom_wdt_core.ko", "sec_debug.ko", "minidump.ko", "abc.ko"):
        if module not in blocklist:
            raise SystemExit(f"M24 blocklist missing {module}")

    required_strings = set(m24_init.get("required_strings", []))
    for required in [
        EXPECTED_M24_MARKER,
        "/s22plus_m24_pmsg_steps.modules",
        "module_list=boot_ramdisk_dts_exact_qmp",
        "module_group=dts_exact_qmp",
        "module_count=43",
        "watchdog_blocklist=1",
        "pmsg_steps=1",
        "fallback_pmsg_major=507",
        "no_reboot_beacon=1",
        "acm_cmd_status=1",
        "module_source=stock_vendor_boot_ramdisk",
        "module_injection=list_only",
        "a600000.dwc3",
        "role_force=device",
        "ss_acm.0",
        "ttyGS0",
        EXPECTED_M24_USB_SERIAL,
        EXPECTED_M24_PMSG_PREFIX,
        "module_prepare",
        "module_finit",
        "S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS READY",
        "S22_NATIVE_INIT_USB_ACM_M24_PMSG_STEPS ACK status park",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M24 required string missing from manifest: {required}")

    objdump = str(m24_init.get("objdump", ""))
    reboot_nr_lines = [
        line
        for line in objdump.splitlines()
        if "mov" in line and "x8" in line and "#0x8e" in line and "// #142" in line
    ]
    if reboot_nr_lines:
        raise SystemExit(f"M24 /init unexpectedly loads arm64 __NR_reboot: {reboot_nr_lines}")
    finit_nr_lines = [
        line
        for line in objdump.splitlines()
        if "mov" in line and "#0x111" in line and "// #273" in line
    ]
    if not finit_nr_lines:
        raise SystemExit("M24 /init must load arm64 __NR_finit_module (273)")

    init_path = path.parent / "build" / "s22plus_init_usb_acm_m24_pmsg_steps"
    if init_path.is_file():
        binary = init_path.read_bytes()
        for forbidden in (
            b"download",
            b"M18_FULL",
            b"full_firststage",
            b"modules.load",
            b"modules.load.recovery",
            b"s22plus_m18_full_firststage_usb",
            b"/vendor_dlkm",
            b"ld-linux",
            b"libc.so",
        ):
            if forbidden in binary:
                raise SystemExit(f"M24 /init contains forbidden string: {forbidden!r}")
        append_log(log_path, f"m24_init_binary_checked={init_path}")


def is_m24_acm(device: dict[str, Any]) -> bool:
    model = str(device.get("model", ""))
    return (
        device.get("vendor") == EXPECTED_M24_USB_VENDOR
        and device.get("product") == EXPECTED_M24_USB_PRODUCT
    ) or device.get("serial") == EXPECTED_M24_USB_SERIAL or "M24" in model


def observe_m24(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m24_observe_{iteration:03d}"
        if iteration == 1 or iteration % 5 == 0:
            host_snapshot(run_dir, log_path, label, odin)
        for device in acm_devices(log_path, label):
            if is_m24_acm(device):
                path = str(device["path"])
                payload = read_acm_banner(path, log_path)
                marker_seen = int(EXPECTED_M24_MARKER.encode("ascii") in payload)
                append_log(log_path, f"m24_acm_seen=1 path={path} banner_marker_found={marker_seen}")
                return ("acm", path)
        devices = odin_devices(odin, log_path, f"{label}-odin")
        if len(devices) == 1:
            append_log(log_path, f"m24_odin_returned=1 device={devices[0]}")
            return ("odin", devices[0])
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M24 observation: {devices}")
        rows = adb_rows(log_path, f"{label}-adb")
        usable = [row for row in rows if row[1] == "device"]
        if len(usable) == 1:
            append_log(log_path, f"m24_adb_returned=1 serial={usable[0][0]}")
            return ("adb", usable[0][0])
        if len(usable) > 1:
            raise SystemExit(f"refusing ambiguous ADB devices during M24 observation: {usable}")
        time.sleep(1.0)
    append_log(log_path, "m24_observation_timeout=1")
    return ("none", None)


def summarize_pmsg_steps(run_dir: Path, log_path: Path, label: str) -> list[str]:
    pstore_dir = run_dir / "android_pstore"
    pattern = re.compile(r"A90_STEP:M24:[^\r\n]*")
    steps: list[str] = []
    for path in sorted(pstore_dir.glob(f"{label}_*.bin")):
        payload = path.read_bytes().decode("utf-8", errors="replace")
        for match in pattern.findall(payload):
            if match not in steps:
                steps.append(match)
    out_path = run_dir / f"{label}_pmsg_steps.txt"
    out_path.write_text("\n".join(steps) + ("\n" if steps else ""), encoding="utf-8")
    append_log(log_path, f"{label}_pmsg_step_count={len(steps)}")
    if steps:
        append_log(log_path, f"{label}_pmsg_last_step={steps[-1]}")
    return steps


def capture_post_rollback_surfaces(run_dir: Path, log_path: Path, serial: str) -> dict[str, Any]:
    label = "post_m24_boot_rollback"
    marker_found = collect_android_pstore(run_dir, log_path, label, serial, marker=EXPECTED_M24_PMSG_PREFIX)
    append_log(log_path, f"m24_capture_pstore_pmsg_prefix_found={int(marker_found)}")
    steps = summarize_pmsg_steps(run_dir, log_path, label)
    reset_dir = run_dir / "post_m24_boot_rollback_reset_reason"
    reset_dir.mkdir(parents=True, exist_ok=False)
    summary = collect_reset_reason(reset_dir, serial)
    summary["run_dir"] = str(reset_dir.relative_to(repo_root()))
    summary["m24_pmsg_step_count"] = len(steps)
    summary["m24_pmsg_last_step"] = steps[-1] if steps else ""
    (reset_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"m24_reset_reason_result={summary.get('result')}")
    append_log(log_path, f"m24_reset_reason_summary_path={reset_dir / 'summary.json'}")
    return summary


def rollback_from_download(
    odin: Path,
    rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
) -> int:
    record_timeline_event(run_dir, "live_session_start")
    devices = odin_devices(odin, log_path, "m24-boot-rollback")
    if len(devices) != 1:
        raise SystemExit(f"M24 rollback requires exactly one Odin device, got {devices}")
    record_timeline_event(run_dir, "rollback_flash_start")
    rollback_rc = flash_ap(odin, rollback_ap, devices[0], log_path, f"{rollback_target}_boot_rollback")
    record_timeline_event(run_dir, "rollback_flash_done")
    if rollback_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        return rollback_rc or 5
    android = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if android is None:
        record_timeline_event(run_dir, "live_session_end")
        return 6
    record_timeline_event(run_dir, "rollback_boot_ready")
    summary = capture_post_rollback_surfaces(run_dir, log_path, android)
    record_timeline_event(run_dir, "live_session_end")
    return 0 if summary.get("result") == "pass" else 7


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m24-ap", type=Path, default=DEFAULT_M24_AP)
    parser.add_argument("--m24-manifest", type=Path, default=DEFAULT_M24_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--m24-observe-sec", type=int, default=180)
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
    log_path = run_dir / "s22plus_m24_pmsg_steps_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M24 pmsg-step live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m24_ap = resolve(root, args.m24_ap)
    m24_manifest = resolve(root, args.m24_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap(m24_ap, EXPECTED_M24_AP_SHA256, "m24_candidate", log_path)
    verify_m24_manifest(m24_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M24 candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(odin, rollback_ap, run_dir, log_path, args.rollback_target, args.android_wait_sec)
        print(f"M24 rollback-from-download completed rc={rc}; log={log_path}")
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
            "dry-run ok: M24 candidate, rollback APs, AGENTS exception, Android stability, "
            f"and boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "m24-candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print("download mode did not appear for M24 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m24_ap, odin_device, log_path, "m24_candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        print(f"M24 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    print("M24 candidate flashed. Waiting for ACM/ADB/Odin; pmsg steps are checked after rollback.")
    observed, endpoint = observe_m24(run_dir, log_path, args.m24_observe_sec, odin)
    if endpoint is not None:
        record_timeline_event(run_dir, "candidate_boot_ready")
    if observed == "acm" and endpoint:
        append_log(log_path, f"m24_result=acm_seen_manual_download_required endpoint={endpoint}")
        record_timeline_event(run_dir, "live_session_end")
        print(
            "M24 ACM appeared. Enter Download mode manually and run --rollback-from-download "
            "so pmsg/pstore/reset-context surfaces can be captured after rollback.",
            file=sys.stderr,
        )
        return 4
    if observed == "odin":
        odin_device = endpoint
    elif observed == "adb" and endpoint:
        append_log(log_path, f"m24_unexpected_adb_returned={endpoint}")
        reboot_back = run(["adb", "-s", endpoint, "reboot", "download"], timeout=20.0)
        append_log(log_path, f"m24_unexpected_adb_reboot_download_rc={reboot_back.returncode}")
        append_log(log_path, reboot_back.stdout + reboot_back.stderr)
        odin_device = wait_for_odin(odin, log_path, "m24-unexpected-adb-rollback-wait", args.odin_wait_sec)
    else:
        append_log(log_path, "m24_result=no_acm_no_transport_manual_download_required")
        record_timeline_event(run_dir, "live_session_end")
        print("M24 did not expose rollback transport. Enter Download mode manually and run --rollback-from-download.", file=sys.stderr)
        return 4
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print("M24 Download mode did not appear; manual Download rollback required.", file=sys.stderr)
        return 4

    record_timeline_event(run_dir, "rollback_flash_start")
    rollback_rc = flash_ap(odin, rollback_ap, odin_device, log_path, f"{args.rollback_target}_boot_rollback")
    record_timeline_event(run_dir, "rollback_flash_done")
    if rollback_rc != 0 and args.rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            record_timeline_event(run_dir, "rollback_flash_start")
            rollback_rc = flash_ap(odin, stock_rollback_ap, fallback_device, log_path, "stock_boot_fallback")
            record_timeline_event(run_dir, "rollback_flash_done")
    if rollback_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        return rollback_rc or 5

    post_rollback_serial = poll_android(log_path, args.android_wait_sec, expect_root=args.rollback_target == ROLLBACK_MAGISK)
    if post_rollback_serial is None:
        record_timeline_event(run_dir, "live_session_end")
        return 6
    record_timeline_event(run_dir, "rollback_boot_ready")
    summary = capture_post_rollback_surfaces(run_dir, log_path, post_rollback_serial)
    record_timeline_event(run_dir, "live_session_end")
    rc = 0 if summary.get("result") == "pass" else 7
    print(f"M24 live gate completed rollback and retained-surface capture rc={rc}; log={log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
