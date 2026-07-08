#!/usr/bin/env python3
"""Guarded S22+ M33 P30 watchdog-prefix park native-init live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M33 P30 is not a Download beacon and does not expose USB ACM. It loads the
watchdog-managed full-ACM-module-without-configfs prefix, parks, and lets the
host/operator decide whether that module boundary survives past the PMIC/PON
reset window.
"""

from __future__ import annotations

import argparse
import json
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
from s22plus_m25_hs_only_usb2_acm_live_gate import (
    EXPECTED_BASE_BOOT_SHA256,
    record_timeline_event,
    verify_partition_hash,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability


LIVE_ACK_TOKEN = "S22PLUS-M33-P30-WDT-PREFIX-PARK-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M33-P30-WDT-PREFIX-PARK-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_VARIANT = "P30"
EXPECTED_PREFIX_COUNT = 30
EXPECTED_M33_MARKER = "S22_NATIVE_INIT_M33_WDT_PREFIX_PARK_P30"
EXPECTED_M33_AP_SHA256 = "e7cadd856da852e577adf32e088c0fee668904f265cdad1e9309072ccb2b18fd"
EXPECTED_M33_BOOT_SHA256 = "0a972bcb4af2b75d5177ae9767e34a4caa8b8c94237afa708bb4a577b2ba7bfe"
EXPECTED_M33_INIT_SHA256 = "48afc2af4fc1bdbfa7724cbff02d68249fc75a62005da073d5092e6c12dd4baa"
EXPECTED_M33_MODULE_LIST_SHA256 = "2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c"
EXPECTED_M33_SOURCE_SHA256 = "88d05498dc8956c95799cd0e6edb3b7080a8cd5d12b662a17545a7de7ffadf68"
EXPECTED_M33_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M33_BASE_BOOT_SHA256 = EXPECTED_BASE_BOOT_SHA256
EXPECTED_MODULE_ENTRY = "s22plus_m33_p30_wdt_prefix_park.modules"

EXPECTED_MODULES = [
    "smem.ko",
    "minidump.ko",
    "sec_debug.ko",
    "qcom_ipc_logging.ko",
    "cmd-db.ko",
    "qcom_rpmh.ko",
    "clk-rpmh.ko",
    "debug-regulator.ko",
    "proxy-consumer.ko",
    "gdsc-regulator.ko",
    "clk-qcom.ko",
    "clk-dummy.ko",
    "gcc-waipio.ko",
    "icc-bcm-voter.ko",
    "icc-debug.ko",
    "socinfo.ko",
    "icc-rpmh.ko",
    "rpmh-regulator.ko",
    "qcom-scm.ko",
    "qcom_wdt_core.ko",
    "gh_virt_wdt.ko",
    "iommu-logger.ko",
    "qnoc-qos.ko",
    "qnoc-waipio.ko",
    "phy-generic.ko",
    "qcom_iommu_util.ko",
    "sec_class.ko",
    "secure_buffer.ko",
    "arm_smmu.ko",
    "abc.ko",
    "usb_notify_layer.ko",
    "switch_class.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "pdic_notifier_module.ko",
    "usb_typec_manager.ko",
    "usb_f_ss_mon_gadget.ko",
    "phy-msm-snps-hs.ko",
    "repeater.ko",
    "phy-msm-snps-eusb2.ko",
    "redriver.ko",
    "if_cb_manager.ko",
    "qc_usb_audio.ko",
    "dwc3-msm.ko",
    "usb_f_ss_acm.ko",
]

DEFAULT_M33_AP = Path("workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/P30/odin4/AP.tar.md5")
DEFAULT_M33_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m33_wdt_prefix_park_matrix_v0_1/manifest.json")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m33_p30_wdt_prefix_park_live_gate_{utc_stamp()}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def policy_required_markers() -> list[str]:
    return [
        "S22+ M33 P30 watchdog-prefix park native-init boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_m33_p30_wdt_prefix_park_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_VARIANT,
        EXPECTED_M33_MARKER,
        EXPECTED_M33_AP_SHA256,
        EXPECTED_M33_BOOT_SHA256,
        EXPECTED_M33_INIT_SHA256,
        EXPECTED_M33_MODULE_LIST_SHA256,
        EXPECTED_M33_SOURCE_SHA256,
        EXPECTED_M33_KERNEL_SHA256,
        EXPECTED_M33_BASE_BOOT_SHA256,
        "watchdog-managed prefix park",
        "prefix_targets=30",
        "module_load_only=1",
        "full-ACM-module-without-configfs prefix",
        "ACM function module included",
        "no runtime ACM/configfs binding",
        "no reboot syscall",
        "no Download beacon",
        "no runtime USB/configfs/ACM",
        "manual Download rollback is recovery-only",
        "survives past 60-90 seconds",
        "PMIC/RDX abnormal reset before the observation window is FAIL",
        "phy-msm-ssusb-qmp.ko intentionally excluded",
        "EUD excluded",
        *EXPECTED_MODULES,
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [marker for marker in policy_required_markers() if marker not in normalized]


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M33 P30 watchdog-prefix authorization markers: {missing}")


def find_p30_variant(data: dict[str, Any]) -> dict[str, Any]:
    for variant in data.get("variants", []):
        if variant.get("label") == EXPECTED_VARIANT:
            return variant
    raise SystemExit("M33 manifest does not contain P30 variant")


def verify_m33_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M33 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    variant = find_p30_variant(data)
    hashes = variant.get("hashes", {})
    safety = data.get("safety", {})
    matrix = data.get("matrix", {})
    closure = variant.get("closure", {})
    ramdisk = variant.get("ramdisk", {})
    init_info = variant.get("init", {})
    tar_members_seen = variant.get("tar_members")
    append_log(log_path, f"m33_manifest_path={path}")
    append_log(log_path, f"m33_p30_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m33_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m33_manifest_matrix={json.dumps(matrix, sort_keys=True)}")
    append_log(log_path, f"m33_p30_manifest_closure={json.dumps(closure, sort_keys=True)}")
    append_log(log_path, f"m33_p30_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m33_p30_manifest_init_file={init_info.get('file', '')}")

    if data.get("target") != EXPECTED_TARGET:
        raise SystemExit(f"M33 target mismatch: {data.get('target')!r}")
    if variant.get("prefix_count") != EXPECTED_PREFIX_COUNT:
        raise SystemExit(f"M33 P30 prefix count mismatch: {variant.get('prefix_count')!r}")
    required_hashes = {
        "ap_tar_md5": EXPECTED_M33_AP_SHA256,
        "boot_img": EXPECTED_M33_BOOT_SHA256,
        "base_boot": EXPECTED_M33_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M33_KERNEL_SHA256,
        "m33_init": EXPECTED_M33_INIT_SHA256,
        "m33_modules": EXPECTED_M33_MODULE_LIST_SHA256,
        "generated_source": EXPECTED_M33_SOURCE_SHA256,
    }
    for key, expected in required_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M33 P30 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if data.get("hashes", {}).get("nochange_repack_boot") != EXPECTED_M33_BASE_BOOT_SHA256:
        raise SystemExit("M33 no-change MagiskBoot repack is not pinned to the known booting base")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M33 P30 manifest tar members mismatch: {tar_members_seen!r}")

    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": False,
        "intended_reboot_syscall": False,
        "reboot_request": None,
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_binary_injection": False,
        "configfs_runtime_gadget": False,
        "usb_role_force": False,
        "acm": False,
        "watchdog_managed": True,
        "qmp_module_excluded": True,
        "eud_module_excluded": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M33 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if matrix.get("configfs_runtime_gadget") is not False or matrix.get("acm_runtime_setup") is not False:
        raise SystemExit("M33 matrix unexpectedly enables configfs or ACM runtime setup")

    if closure.get("modules") != EXPECTED_MODULES:
        raise SystemExit(f"M33 P30 module closure mismatch: {closure.get('modules')!r}")
    if closure.get("module_count") != len(EXPECTED_MODULES):
        raise SystemExit(f"M33 P30 module closure count mismatch: {closure.get('module_count')!r}")
    if closure.get("module_sha256") != EXPECTED_M33_MODULE_LIST_SHA256:
        raise SystemExit(f"M33 P30 module list SHA mismatch: {closure.get('module_sha256')!r}")
    if any(module in closure.get("modules", []) for module in ("phy-msm-ssusb-qmp.ko", "eud.ko")):
        raise SystemExit("M33 P30 excluded QMP/EUD module leaked into closure")
    boundaries = closure.get("key_boundaries", {})
    expected_boundaries = {
        "includes_arm_smmu": True,
        "includes_hs_phy": True,
        "includes_eusb2_phy": True,
        "includes_dwc3": True,
        "includes_monitor_gadget_module": True,
        "includes_acm_module": True,
        "configfs_runtime_gadget": False,
    }
    for key, expected in expected_boundaries.items():
        if boundaries.get(key) is not expected:
            raise SystemExit(f"M33 P30 boundary {key} mismatch: {boundaries.get(key)!r} != {expected!r}")
    for key in (
        "includes_arm_smmu",
        "includes_hs_phy",
        "includes_eusb2_phy",
        "includes_dwc3",
        "includes_monitor_gadget_module",
        "includes_acm_module",
        "configfs_runtime_gadget",
    ):
        if key not in boundaries:
            raise SystemExit(f"M33 P30 boundary {key} missing")

    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M33 P30 manifest did not replace /init")
    if ramdisk.get("added_subset_entry") != EXPECTED_MODULE_ENTRY:
        raise SystemExit(f"M33 P30 module list ramdisk entry mismatch: {ramdisk.get('added_subset_entry')!r}")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M33 P30 must not inject module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 1:
        raise SystemExit("M33 P30 must inject exactly one module-list text file into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M33_MARKER,
        "version=0.1",
        "module_list=wdt_prefix_park",
        "variant=P30",
        "prefix_targets=30",
        "module_load_only=1",
        "no_configfs=1",
        "no_acm=1",
        "no_reboot_request=1",
        "no_download_beacon=1",
        "module_count=45",
        "phase=modules_load_done",
        "phase=park_enter",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M33 P30 required string missing from manifest: {required}")

    objdump_path = path.parent / EXPECTED_VARIANT / str(init_info.get("objdump_path", ""))
    if not objdump_path.is_file():
        raise SystemExit(f"M33 P30 objdump missing: {objdump_path}")
    objdump = objdump_path.read_text(encoding="utf-8", errors="replace")
    if not any("mov" in line and "#0x111" in line and "// #273" in line for line in objdump.splitlines()):
        raise SystemExit("M33 P30 /init does not load arm64 __NR_finit_module (273)")
    if any("mov" in line and "#0x8e" in line and "// #142" in line for line in objdump.splitlines()):
        raise SystemExit("M33 P30 /init must not load arm64 __NR_reboot (142)")


def verify_m33_artifacts(
    *,
    m33_ap: Path,
    m33_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> None:
    verify_ap(m33_ap, EXPECTED_M33_AP_SHA256, "m33_p30_candidate", log_path)
    verify_m33_manifest(m33_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)


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


def observe_park_survival(
    *,
    run_dir: Path,
    log_path: Path,
    odin: Path,
    observe_sec: int,
    snapshot_interval_sec: float,
) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    start = time.monotonic()
    deadline = start + observe_sec
    next_snapshot = start
    iteration = 0
    append_log(log_path, f"m33_p30_observe_start_utc={utc_now()}")
    append_log(log_path, f"m33_p30_observe_sec={observe_sec}")
    while time.monotonic() < deadline:
        now = time.monotonic()
        elapsed = now - start
        if now >= next_snapshot:
            iteration += 1
            label = f"m33_p30_park_observe_{iteration:03d}"
            append_log(log_path, f"{label}_elapsed_sec={elapsed:.3f}")
            host_snapshot(run_dir, log_path, label, odin)
            devices = odin_devices(odin, log_path, f"{label}-odin-extra")
            if len(devices) == 1:
                append_log(log_path, f"m33_p30_result=unexpected_odin_before_survival_window elapsed_sec={elapsed:.3f} device={devices[0]}")
                return "unexpected-odin-before-survival-window", devices[0]
            if len(devices) > 1:
                raise SystemExit(f"refusing ambiguous Odin devices during M33 P30 observation: {devices}")
            rows = adb_rows(log_path, f"{label}-adb-extra")
            usable = [row for row in rows if row[1] == "device"]
            if usable:
                append_log(log_path, f"m33_p30_result=unexpected_adb_before_survival_window elapsed_sec={elapsed:.3f} rows={usable}")
                return "unexpected-adb-before-survival-window", None
            next_snapshot = now + snapshot_interval_sec
        time.sleep(0.5)
    append_log(log_path, "m33_p30_survival_window_pass=1")
    append_log(log_path, "m33_p30_result=survived-observation-window-manual-download-required")
    return "survived-observation-window-manual-download-required", None


def rollback_boot_only_from_download(
    *,
    odin: Path,
    rollback_ap: Path,
    stock_boot_fallback_ap: Path,
    odin_device: str,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
    label: str,
) -> tuple[int, str | None]:
    record_timeline_event(run_dir, f"{label}_rollback_flash_start")
    record_timeline_event(run_dir, "rollback_flash_start")
    rollback_rc = flash_ap(odin, rollback_ap, odin_device, log_path, f"{label}_{rollback_target}_boot_rollback")
    record_timeline_event(run_dir, "rollback_flash_done")
    record_timeline_event(run_dir, f"{label}_rollback_flash_done")
    if rollback_rc != 0 and rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, f"m33_p30_{label}_magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, f"{label}-stock-fallback-wait", 30)
        if fallback_device:
            record_timeline_event(run_dir, f"{label}_stock_fallback_flash_start")
            rollback_rc = flash_ap(odin, stock_boot_fallback_ap, fallback_device, log_path, f"{label}_stock_boot_fallback")
            record_timeline_event(run_dir, f"{label}_stock_fallback_flash_done")
            rollback_target = ROLLBACK_STOCK
    if rollback_rc != 0:
        return (rollback_rc or 5, None)

    android = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if android is None:
        return (6, None)
    if rollback_target == ROLLBACK_MAGISK:
        verify_partition_hash(log_path, android, "boot", EXPECTED_M33_BASE_BOOT_SHA256, f"{label}_boot_restore")
    else:
        append_log(log_path, f"m33_p30_{label}_boot_restore_hash_check=skipped rollback_target=stock")
    record_timeline_event(run_dir, "rollback_boot_ready")
    record_timeline_event(run_dir, f"{label}_rollback_boot_ready")
    marker_found = collect_android_pstore(run_dir, log_path, f"post_m33_p30_{label}_rollback", android, marker=EXPECTED_M33_MARKER)
    append_log(log_path, f"m33_p30_{label}_retained_marker_found={int(marker_found)}")
    return (0, android)


def rollback_from_download(
    *,
    odin: Path,
    rollback_ap: Path,
    stock_boot_fallback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    android_wait_sec: int,
) -> int:
    record_timeline_event(run_dir, "live_session_start")
    devices = odin_devices(odin, log_path, "m33-p30-rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"M33 P30 rollback requires exactly one Odin device, got {devices}")
    rc, _android = rollback_boot_only_from_download(
        odin=odin,
        rollback_ap=rollback_ap,
        stock_boot_fallback_ap=stock_boot_fallback_ap,
        odin_device=devices[0],
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=rollback_target,
        android_wait_sec=android_wait_sec,
        label="manual",
    )
    record_timeline_event(run_dir, "live_session_end")
    return rc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m33-ap", type=Path, default=DEFAULT_M33_AP)
    parser.add_argument("--m33-manifest", type=Path, default=DEFAULT_M33_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--observe-sec", type=int, default=90)
    parser.add_argument("--snapshot-interval-sec", type=float, default=5.0)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--manual-download-wait-sec", type=int, default=300)
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
    if args.observe_sec < 60:
        raise SystemExit("--observe-sec must be at least 60 for the M33 P30 watchdog-prefix discriminator")
    if args.snapshot_interval_sec < 1.0:
        raise SystemExit("--snapshot-interval-sec must be at least 1.0")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m33_p30_wdt_prefix_park_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M33 P30 watchdog-prefix park live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m33_ap = resolve(root, args.m33_ap)
    m33_manifest = resolve(root, args.m33_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_m33_artifacts(
        m33_ap=m33_ap,
        m33_manifest=m33_manifest,
        magisk_rollback_ap=magisk_rollback_ap,
        stock_rollback_ap=stock_rollback_ap,
        log_path=log_path,
    )

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M33 P30 candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(
            odin=odin,
            rollback_ap=rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
        )
        print(f"M33 P30 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_M33_BASE_BOOT_SHA256, "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M33 P30 candidate, rollback APs, AGENTS exception, Android stability, "
            f"and current boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    print(
        "M33 P30 live gate starting. This candidate should park; do not press keys during "
        f"the {args.observe_sec}s observation window. Manual Download is only for rollback after the helper asks.",
        flush=True,
    )
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print("download mode did not appear for M33 P30 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m33_ap, odin_device, log_path, "candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        print(f"M33 P30 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        append_log(log_path, "m33_p30_result=no-proof-original-download-never-disconnected")
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            print(f"rollback download mode unavailable after no-disconnect; manual recovery required. log={log_path}", file=sys.stderr)
            return 4
        rc, _android = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="no_disconnect",
        )
        record_timeline_event(run_dir, "live_session_end")
        return rc or 7

    record_timeline_event(run_dir, "candidate_boot_ready")
    print(f"M33 P30 candidate flashed. Observing for {args.observe_sec}s survival window.", flush=True)
    result, rollback_device = observe_park_survival(
        run_dir=run_dir,
        log_path=log_path,
        odin=odin,
        observe_sec=args.observe_sec,
        snapshot_interval_sec=args.snapshot_interval_sec,
    )
    if result != "survived-observation-window-manual-download-required":
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            print(
                f"M33 P30 stopped before survival proof ({result}). If the device is not in Android, "
                "enter Download manually and run --rollback-from-download.",
                file=sys.stderr,
            )
            return 4
        rc, _android = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="unexpected_endpoint",
        )
        record_timeline_event(run_dir, "live_session_end")
        return rc or 8

    print(
        "M33 P30 survived the observation window. Enter Download mode manually for rollback now; "
        f"waiting up to {args.manual_download_wait_sec}s.",
        flush=True,
    )
    rollback_device = wait_for_odin(odin, log_path, "manual-rollback-wait", args.manual_download_wait_sec)
    if rollback_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print(
            f"M33 P30 survival window passed, but manual Download mode did not appear. "
            f"Run --rollback-from-download after entering Download mode. log={log_path}",
            file=sys.stderr,
        )
        return 4

    rc, _android = rollback_boot_only_from_download(
        odin=odin,
        rollback_ap=rollback_ap,
        stock_boot_fallback_ap=stock_rollback_ap,
        odin_device=rollback_device,
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=args.rollback_target,
        android_wait_sec=args.android_wait_sec,
        label="manual_after_survival",
    )
    record_timeline_event(run_dir, "live_session_end")
    print(f"M33 P30 live gate completed rc={rc}; result={result}; log={log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
