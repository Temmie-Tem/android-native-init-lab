#!/usr/bin/env python3
"""Guarded S22+ M25 HS-only USB2 ACM live gate.

Default dry-run and live modes require a future SHA-pinned AGENTS.md exception.
--offline-check verifies only the host-built M25 boot package, DTBO package,
and rollback APs without touching a connected device.

M25 first applies a high-speed DTBO cap, then flashes the HS-only native-init
boot candidate. Rollback restores the Magisk boot baseline and stock DTBO.
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
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    adb_rows,
    adb_root_shell,
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
    sha256_file,
    tar_members,
    utc_now,
    verify_ap,
    wait_for_odin,
)
from s22plus_m5_usb_acm_live_gate import (
    acm_devices,
    read_acm_banner,
    verify_android_stability,
)
from s22plus_reset_reason_readonly_probe import collect as collect_reset_reason


LIVE_ACK_TOKEN = "S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M25-HS-ONLY-ROLLBACK-FROM-DOWNLOAD"
RESTORE_DTBO_ACK_TOKEN = "S22PLUS-M25-RESTORE-STOCK-DTBO"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_MEMBER_BOOT = "boot.img.lz4"
EXPECTED_MEMBER_DTBO = "dtbo.img.lz4"
EXPECTED_BASE_BOOT_SHA256 = "2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e"
EXPECTED_STOCK_VENDOR_BOOT_SHA256 = "096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7"
EXPECTED_STOCK_DTBO_RAW_SHA256 = "97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c"

EXPECTED_M25_BOOT_AP_SHA256 = "7f89cfb8ff188190d1d161aee97e3edec2730bfc46efca9df37f2035f7206805"
EXPECTED_M25_BOOT_SHA256 = "0ace02ff82be1cb7473879ff52f1c9e8d1491edaa3d9a88b829f901b2c86559f"
EXPECTED_M25_INIT_SHA256 = "cc03d95f06b851717d3ccb4fc32fbecac3adfe7109c1a68454f846e3014ecf75"
EXPECTED_M25_MODULE_LIST_SHA256 = "00607484b7b777ee5cb54d7657f0cb554b9b66c42fec0e414d0544c0735d6496"
EXPECTED_M25_SOURCE_SHA256 = "22350e7de748cf3a2f47236ef984bb224df58ffa7664ced811151c9db189562f"
EXPECTED_M25_VENDOR_DTB_SHA256 = "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e"
EXPECTED_M25_VENDOR_RAMDISK_SHA256 = "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193"
EXPECTED_M25_MARKER = "S22_NATIVE_INIT_USB_ACM_M25_HS_ONLY"
EXPECTED_M25_USB_VENDOR = "04e8"
EXPECTED_M25_USB_PRODUCT = "685d"
EXPECTED_M25_USB_SERIAL = "S22M25HSONLY01"

EXPECTED_M25_DTBO_AP_SHA256 = "35afd774444066fd8e2ffe831da11dd73ee47dce3bdd5b1e37675f82344e56b6"
EXPECTED_M25_PATCHED_DTBO_RAW_SHA256 = "8962cbbded722c85dbdebfbdc2eba5476b9a64e2a2933888b81f947159eddc17"
EXPECTED_M25_STOCK_DTBO_ROLLBACK_AP_SHA256 = "6f397421bee84f4ea0c80a8519be0f6f6af84119794970e8a1faaa05f261caaa"

EXPECTED_M25_MODULES = [
    "clk-rpmh.ko",
    "gcc-waipio.ko",
    "icc-rpmh.ko",
    "qcom_ipc_logging.ko",
    "rpmh-regulator.ko",
    "clk-dummy.ko",
    "clk-qcom.ko",
    "cmd-db.ko",
    "debug-regulator.ko",
    "gdsc-regulator.ko",
    "icc-bcm-voter.ko",
    "icc-debug.ko",
    "iommu-logger.ko",
    "qnoc-waipio.ko",
    "phy-generic.ko",
    "proxy-consumer.ko",
    "qcom_iommu_util.ko",
    "qcom_rpmh.ko",
    "qcom-scm.ko",
    "qnoc-qos.ko",
    "sec_class.ko",
    "secure_buffer.ko",
    "smem.ko",
    "socinfo.ko",
    "arm_smmu.ko",
    "phy-msm-snps-hs.ko",
    "phy-msm-snps-eusb2.ko",
    "dwc3-msm.ko",
    "usb_f_ss_mon_gadget.ko",
    "usb_f_ss_acm.ko",
    "repeater.ko",
    "redriver.ko",
    "usb_notify_layer.ko",
    "switch_class.ko",
    "common_muic.ko",
    "vbus_notifier.ko",
    "usb_typec_manager.ko",
    "if_cb_manager.ko",
    "pdic_notifier_module.ko",
    "qc_usb_audio.ko",
]

DEFAULT_M25_AP = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/boot_odin4/AP.tar.md5")
DEFAULT_M25_DTBO_AP = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/dtbo_candidate_odin4/AP.tar.md5")
DEFAULT_M25_STOCK_DTBO_AP = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/dtbo_stock_rollback_odin4/AP.tar.md5")
DEFAULT_M25_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m25_hs_only_usb2_acm_v0_1/manifest.json")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m25_hs_only_usb2_acm_live_gate_{utc_stamp()}")
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
        for index, event in enumerate(data["events"]):
            if not isinstance(event, dict) or sorted(event.keys()) != ["name", "timestamp_utc"]:
                raise SystemExit(f"refusing non-canonical timeline event {index}: {path}")
            if not isinstance(event["name"], str) or not event["name"]:
                raise SystemExit(f"refusing timeline event with invalid name {index}: {path}")
            timestamp = event["timestamp_utc"]
            if not isinstance(timestamp, str) or not timestamp.endswith("Z"):
                raise SystemExit(f"refusing timeline event with invalid timestamp {index}: {path}")
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise SystemExit(f"refusing timeline event with unparsable timestamp {index}: {path}") from exc
        events = data["events"]
    events.append({"name": name, "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
    path.write_text(json.dumps({"events": events}, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def policy_required_markers() -> list[str]:
    return [
        "S22+ M25 HS-only USB2 ACM native-init boot+DTBO",
        EXPECTED_M25_BOOT_AP_SHA256,
        EXPECTED_M25_BOOT_SHA256,
        EXPECTED_M25_INIT_SHA256,
        EXPECTED_M25_MODULE_LIST_SHA256,
        EXPECTED_M25_SOURCE_SHA256,
        EXPECTED_M25_VENDOR_DTB_SHA256,
        EXPECTED_M25_DTBO_AP_SHA256,
        EXPECTED_M25_PATCHED_DTBO_RAW_SHA256,
        EXPECTED_M25_STOCK_DTBO_ROLLBACK_AP_SHA256,
        EXPECTED_BASE_BOOT_SHA256,
        EXPECTED_STOCK_DTBO_RAW_SHA256,
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        RESTORE_DTBO_ACK_TOKEN,
        "DTBO high-speed cap",
        "super-speed",
        "high-speed",
        "module_group=hs_only_usb2",
        "module_count=40",
        "s22plus_m25_hs_only_usb2.modules",
        "phy-msm-ssusb-qmp.ko intentionally excluded",
        "ss_acm.0",
        "a600000.dwc3 only",
        "stock DTBO rollback",
        "Magisk boot rollback",
        "manual download-mode rollback",
        "boot.img.lz4",
        "dtbo.img.lz4",
        *EXPECTED_M25_MODULES,
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [item for item in policy_required_markers() if item not in normalized]


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M25 HS-only live authorization markers: {missing}")


def verify_m25_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M25 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    hashes = data.get("hashes", {})
    safety = data.get("safety", {})
    boot_safety = safety.get("boot_candidate", {})
    dtbo_safety = safety.get("dtbo_candidate", {})
    dtbo = data.get("dtbo", {})
    dtbo_hashes = dtbo.get("hashes", {})
    dtbo_evidence = dtbo.get("evidence", {})
    closure = data.get("dts_hs_only", {}).get("dts_hs_only", {})
    append_log(log_path, f"m25_manifest_path={path}")
    append_log(log_path, f"m25_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m25_dtbo_hashes={json.dumps(dtbo_hashes, sort_keys=True)}")
    append_log(log_path, f"m25_manifest_safety={json.dumps(safety, sort_keys=True)}")

    expected_hashes = {
        "boot_ap_tar_md5": EXPECTED_M25_BOOT_AP_SHA256,
        "boot_img": EXPECTED_M25_BOOT_SHA256,
        "base_boot": EXPECTED_BASE_BOOT_SHA256,
        "m25_init": EXPECTED_M25_INIT_SHA256,
        "m25_hs_only_usb2": EXPECTED_M25_MODULE_LIST_SHA256,
        "generated_source": EXPECTED_M25_SOURCE_SHA256,
        "vendor_dtb": EXPECTED_M25_VENDOR_DTB_SHA256,
        "vendor_ramdisk": EXPECTED_M25_VENDOR_RAMDISK_SHA256,
        "stock_dtbo_raw": EXPECTED_STOCK_DTBO_RAW_SHA256,
    }
    for key, expected in expected_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M25 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    expected_dtbo_hashes = {
        "candidate_ap_tar_md5": EXPECTED_M25_DTBO_AP_SHA256,
        "patched_dtbo_raw": EXPECTED_M25_PATCHED_DTBO_RAW_SHA256,
        "rollback_ap_tar_md5": EXPECTED_M25_STOCK_DTBO_ROLLBACK_AP_SHA256,
        "stock_dtbo_raw": EXPECTED_STOCK_DTBO_RAW_SHA256,
    }
    for key, expected in expected_dtbo_hashes.items():
        if dtbo_hashes.get(key) != expected:
            raise SystemExit(f"M25 manifest DTBO hash {key} mismatch: {dtbo_hashes.get(key)!r} != {expected!r}")
    if data.get("boot_tar_members") != [EXPECTED_MEMBER_BOOT]:
        raise SystemExit(f"M25 boot tar members mismatch: {data.get('boot_tar_members')!r}")
    if dtbo_evidence.get("candidate_tar_members") != [EXPECTED_MEMBER_DTBO]:
        raise SystemExit(f"M25 DTBO candidate tar members mismatch: {dtbo_evidence.get('candidate_tar_members')!r}")
    if dtbo_evidence.get("rollback_tar_members") != [EXPECTED_MEMBER_DTBO]:
        raise SystemExit(f"M25 DTBO rollback tar members mismatch: {dtbo_evidence.get('rollback_tar_members')!r}")
    if dtbo_evidence.get("changed_byte_count") != 110:
        raise SystemExit(f"M25 DTBO changed-byte count mismatch: {dtbo_evidence.get('changed_byte_count')!r}")
    if len(dtbo_evidence.get("applied_patches", [])) != 11:
        raise SystemExit("M25 DTBO must patch exactly 11 maximum-speed overlay values")
    if safety.get("host_only_build") is not True or safety.get("live_flash_authorized") is not False:
        raise SystemExit("M25 manifest must remain host-only and not live-authorized")
    if boot_safety.get("boot_only") is not True:
        raise SystemExit("M25 boot candidate safety must be boot-only")
    if boot_safety.get("qmp") != "phy-msm-ssusb-qmp.ko intentionally excluded":
        raise SystemExit(f"M25 qmp policy mismatch: {boot_safety.get('qmp')!r}")
    if boot_safety.get("module_subset") != "40-module DTS-derived HS-only DWC3/HS-PHY/provider closure":
        raise SystemExit(f"M25 module-subset policy mismatch: {boot_safety.get('module_subset')!r}")
    if dtbo_safety.get("patch_model") != "equal-length string replacement in all 11 DTBO overlay blobs":
        raise SystemExit(f"M25 DTBO patch model mismatch: {dtbo_safety.get('patch_model')!r}")
    if closure.get("subset_count") != 40 or closure.get("subset") != EXPECTED_M25_MODULES:
        raise SystemExit("M25 HS-only module closure mismatch")
    for forbidden in ("phy-msm-ssusb-qmp.ko", "eud.ko", "ucsi_glink.ko", "qcom_wdt_core.ko", "gh_virt_wdt.ko"):
        if forbidden in closure.get("subset", []):
            raise SystemExit(f"forbidden module leaked into M25 subset: {forbidden}")
    required_strings = set(data.get("m25_init", {}).get("required_strings", []))
    for required in [
        EXPECTED_M25_MARKER,
        "/s22plus_m25_hs_only_usb2.modules",
        "module_group=hs_only_usb2",
        "module_count=40",
        "hs_only=1",
        "qmp_excluded=1",
        "maximum_speed_dtbo=high-speed",
        "dtbo_patch_required=1",
        "0x0200",
        EXPECTED_M25_USB_SERIAL,
        f"{EXPECTED_M25_MARKER} READY",
        f"{EXPECTED_M25_MARKER} ACK status park",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M25 required string missing from manifest: {required}")


def read_partition_hash(log_path: Path, serial: str, partition: str, label: str) -> str:
    if not partition.replace("_", "").isalnum():
        raise SystemExit(f"unsafe partition name for hash read: {partition!r}")
    result = adb_root_shell(
        f"toybox sha256sum /dev/block/by-name/{partition} 2>/dev/null || "
        f"sha256sum /dev/block/by-name/{partition}",
        serial=serial,
        timeout=60.0,
    )
    text = result.stdout + result.stderr
    append_log(log_path, f"{label}_{partition}_hash_rc={result.returncode}")
    append_log(log_path, text)
    words = text.split()
    actual_sha = words[0].lower() if words else ""
    if result.returncode != 0 or len(actual_sha) != 64 or any(ch not in "0123456789abcdef" for ch in actual_sha):
        raise SystemExit(f"{label} {partition} hash could not be read safely")
    return actual_sha


def verify_partition_hash(log_path: Path, serial: str, partition: str, expected_sha: str, label: str) -> None:
    actual_sha = read_partition_hash(log_path, serial, partition, label)
    if actual_sha != expected_sha:
        raise SystemExit(f"{label} {partition} hash mismatch: {actual_sha} != {expected_sha}")


def reboot_android_to_download(serial: str, log_path: Path, label: str) -> None:
    result = run(["adb", "-s", serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"{label}_adb_reboot_download_rc={result.returncode}")
    append_log(log_path, result.stdout + result.stderr)
    if result.returncode != 0:
        raise SystemExit(f"{label} adb reboot download failed rc={result.returncode}")


def wait_for_android_root(log_path: Path, wait_sec: int, serial: str | None = None) -> str | None:
    return poll_android(log_path, wait_sec, expect_root=True, serial=serial)


def is_m25_acm(device: dict[str, Any]) -> bool:
    model = str(device.get("model", ""))
    return (
        device.get("vendor") == EXPECTED_M25_USB_VENDOR
        and device.get("product") == EXPECTED_M25_USB_PRODUCT
    ) or device.get("serial") == EXPECTED_M25_USB_SERIAL or "M25" in model


def observe_m25(run_dir: Path, log_path: Path, seconds: int, odin: Path) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    deadline = time.monotonic() + seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        label = f"m25_observe_{iteration:03d}"
        if iteration == 1 or iteration % 5 == 0:
            host_snapshot(run_dir, log_path, label, odin)
        for device in acm_devices(log_path, label):
            if is_m25_acm(device):
                path = str(device["path"])
                payload = read_acm_banner(path, log_path)
                marker_seen = int(EXPECTED_M25_MARKER.encode("ascii") in payload)
                append_log(log_path, f"m25_acm_seen=1 path={path} banner_marker_found={marker_seen}")
                return ("acm", path)
        devices = odin_devices(odin, log_path, f"{label}-odin")
        if len(devices) == 1:
            append_log(log_path, f"m25_odin_returned=1 device={devices[0]}")
            return ("odin", devices[0])
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during M25 observation: {devices}")
        rows = adb_rows(log_path, f"{label}-adb")
        usable = [row for row in rows if row[1] == "device"]
        if len(usable) == 1:
            append_log(log_path, f"m25_adb_returned=1 serial={usable[0][0]}")
            return ("adb", usable[0][0])
        if len(usable) > 1:
            raise SystemExit(f"refusing ambiguous ADB devices during M25 observation: {usable}")
        time.sleep(1.0)
    append_log(log_path, "m25_observation_timeout=1")
    return ("none", None)


def capture_post_boot_rollback_surfaces(run_dir: Path, log_path: Path, serial: str) -> dict[str, Any]:
    label = "post_m25_boot_rollback"
    marker_found = collect_android_pstore(run_dir, log_path, label, serial, marker=EXPECTED_M25_MARKER)
    append_log(log_path, f"m25_capture_marker_found={int(marker_found)}")
    reset_dir = run_dir / "post_m25_boot_rollback_reset_reason"
    reset_dir.mkdir(parents=True, exist_ok=False)
    summary = collect_reset_reason(reset_dir, serial)
    summary["run_dir"] = str(reset_dir.relative_to(repo_root()))
    (reset_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"m25_reset_reason_result={summary.get('result')}")
    append_log(log_path, f"m25_reset_reason_summary_path={reset_dir / 'summary.json'}")
    return summary


def restore_dtbo_from_android(
    *,
    odin: Path,
    dtbo_rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    serial: str,
    odin_wait_sec: int,
    android_wait_sec: int,
) -> int:
    current = read_partition_hash(log_path, serial, "dtbo", "pre_stock_dtbo_restore")
    if current == EXPECTED_STOCK_DTBO_RAW_SHA256:
        append_log(log_path, "stock_dtbo_restore_already_stock=1")
        return 0
    if current != EXPECTED_M25_PATCHED_DTBO_RAW_SHA256:
        raise SystemExit(f"refusing stock DTBO restore from unexpected DTBO hash {current}")
    reboot_android_to_download(serial, log_path, "stock_dtbo_restore")
    device = wait_for_odin(odin, log_path, "stock-dtbo-rollback-wait", odin_wait_sec)
    if device is None:
        print("Download mode did not appear for stock DTBO restore.", file=sys.stderr)
        return 6
    record_timeline_event(run_dir, "dtbo_rollback_flash_start")
    rc = flash_ap(odin, dtbo_rollback_ap, device, log_path, "stock_dtbo_rollback")
    record_timeline_event(run_dir, "dtbo_rollback_flash_done")
    if rc != 0:
        return rc or 5
    android = wait_for_android_root(log_path, android_wait_sec, serial)
    if android is None:
        return 6
    verify_partition_hash(log_path, android, "dtbo", EXPECTED_STOCK_DTBO_RAW_SHA256, "stock_restore")
    record_timeline_event(run_dir, "dtbo_rollback_boot_ready")
    append_log(log_path, f"stock_dtbo_restore_android={android}")
    return 0


def rollback_boot_from_odin_device(
    *,
    odin: Path,
    boot_rollback_ap: Path,
    stock_boot_fallback_ap: Path,
    dtbo_rollback_ap: Path,
    odin_device: str,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    odin_wait_sec: int,
    android_wait_sec: int,
) -> int:
    record_timeline_event(run_dir, "rollback_flash_start")
    rollback_rc = flash_ap(odin, boot_rollback_ap, odin_device, log_path, f"{rollback_target}_boot_rollback")
    record_timeline_event(run_dir, "rollback_flash_done")
    if rollback_rc != 0 and rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, "magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, "stock-fallback-wait", 30)
        if fallback_device:
            record_timeline_event(run_dir, "rollback_flash_start")
            rollback_rc = flash_ap(odin, stock_boot_fallback_ap, fallback_device, log_path, "stock_boot_fallback")
            record_timeline_event(run_dir, "rollback_flash_done")
            rollback_target = ROLLBACK_STOCK
    if rollback_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        return rollback_rc or 5

    android = poll_android(log_path, android_wait_sec, expect_root=rollback_target == ROLLBACK_MAGISK)
    if android is None:
        record_timeline_event(run_dir, "live_session_end")
        return 6
    if rollback_target == ROLLBACK_MAGISK:
        verify_partition_hash(log_path, android, "boot", EXPECTED_BASE_BOOT_SHA256, "boot_restore")
    else:
        append_log(log_path, "boot_restore_hash_check=skipped rollback_target=stock root_not_expected=1")
    record_timeline_event(run_dir, "rollback_boot_ready")
    capture_post_boot_rollback_surfaces(run_dir, log_path, android)
    dtbo_rc = restore_dtbo_from_android(
        odin=odin,
        dtbo_rollback_ap=dtbo_rollback_ap,
        run_dir=run_dir,
        log_path=log_path,
        serial=android,
        odin_wait_sec=odin_wait_sec,
        android_wait_sec=android_wait_sec,
    )
    record_timeline_event(run_dir, "live_session_end")
    return dtbo_rc


def rollback_from_download(
    *,
    odin: Path,
    boot_rollback_ap: Path,
    stock_boot_fallback_ap: Path,
    dtbo_rollback_ap: Path,
    run_dir: Path,
    log_path: Path,
    rollback_target: str,
    odin_wait_sec: int,
    android_wait_sec: int,
) -> int:
    record_timeline_event(run_dir, "live_session_start")
    devices = odin_devices(odin, log_path, "m25-boot-rollback")
    if len(devices) != 1:
        raise SystemExit(f"M25 rollback requires exactly one Odin device, got {devices}")
    return rollback_boot_from_odin_device(
        odin=odin,
        boot_rollback_ap=boot_rollback_ap,
        stock_boot_fallback_ap=stock_boot_fallback_ap,
        dtbo_rollback_ap=dtbo_rollback_ap,
        odin_device=devices[0],
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=rollback_target,
        odin_wait_sec=odin_wait_sec,
        android_wait_sec=android_wait_sec,
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m25-ap", type=Path, default=DEFAULT_M25_AP)
    parser.add_argument("--m25-dtbo-ap", type=Path, default=DEFAULT_M25_DTBO_AP)
    parser.add_argument("--m25-stock-dtbo-ap", type=Path, default=DEFAULT_M25_STOCK_DTBO_AP)
    parser.add_argument("--m25-manifest", type=Path, default=DEFAULT_M25_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial", help="ADB serial to pin before live flashing")
    parser.add_argument("--m25-observe-sec", type=int, default=180)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=300)
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--restore-dtbo-from-android", action="store_true")
    parser.add_argument("--restore-dtbo-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.live,
            args.rollback_from_download,
            args.restore_dtbo_from_android,
            args.restore_dtbo_from_download,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit("mode arguments are mutually exclusive")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m25_hs_only_usb2_acm_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M25 HS-only USB2 ACM live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m25_ap = resolve(root, args.m25_ap)
    m25_dtbo_ap = resolve(root, args.m25_dtbo_ap)
    m25_stock_dtbo_ap = resolve(root, args.m25_stock_dtbo_ap)
    m25_manifest = resolve(root, args.m25_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    boot_rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_ap(m25_ap, EXPECTED_M25_BOOT_AP_SHA256, "m25_boot_candidate", log_path)
    verify_ap_member(m25_dtbo_ap, EXPECTED_M25_DTBO_AP_SHA256, EXPECTED_MEMBER_DTBO, "m25_dtbo_candidate", log_path)
    verify_ap_member(m25_stock_dtbo_ap, EXPECTED_M25_STOCK_DTBO_ROLLBACK_AP_SHA256, EXPECTED_MEMBER_DTBO, "m25_stock_dtbo_rollback", log_path)
    verify_m25_manifest(m25_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M25 boot/DTBO candidates and rollback APs verified; no device action; log={log_path}")
        return 0

    verify_agents_exception(root, log_path)

    if args.restore_dtbo_from_download:
        if args.ack != RESTORE_DTBO_ACK_TOKEN:
            raise SystemExit(f"--restore-dtbo-from-download requires --ack {RESTORE_DTBO_ACK_TOKEN}")
        record_timeline_event(run_dir, "live_session_start")
        devices = odin_devices(odin, log_path, "m25-stock-dtbo-rollback")
        if len(devices) != 1:
            raise SystemExit(f"stock DTBO rollback requires exactly one Odin device, got {devices}")
        record_timeline_event(run_dir, "dtbo_rollback_flash_start")
        rc = flash_ap(odin, m25_stock_dtbo_ap, devices[0], log_path, "stock_dtbo_rollback")
        record_timeline_event(run_dir, "dtbo_rollback_flash_done")
        if rc != 0:
            record_timeline_event(run_dir, "live_session_end")
            return rc or 5
        android = wait_for_android_root(log_path, args.android_wait_sec, args.serial)
        if android is None:
            record_timeline_event(run_dir, "live_session_end")
            return 6
        verify_partition_hash(log_path, android, "dtbo", EXPECTED_STOCK_DTBO_RAW_SHA256, "stock_dtbo_restore")
        record_timeline_event(run_dir, "dtbo_rollback_boot_ready")
        record_timeline_event(run_dir, "live_session_end")
        print(f"M25 stock DTBO restore-from-download completed rc=0; log={log_path}")
        return 0

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        rc = rollback_from_download(
            odin=odin,
            boot_rollback_ap=boot_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            dtbo_rollback_ap=m25_stock_dtbo_ap,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            odin_wait_sec=args.odin_wait_sec,
            android_wait_sec=args.android_wait_sec,
        )
        print(f"M25 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_BASE_BOOT_SHA256, "current")
    verify_partition_hash(log_path, selected_serial, "vendor_boot", EXPECTED_STOCK_VENDOR_BOOT_SHA256, "current")

    if args.restore_dtbo_from_android:
        if args.ack != RESTORE_DTBO_ACK_TOKEN:
            raise SystemExit(f"--restore-dtbo-from-android requires --ack {RESTORE_DTBO_ACK_TOKEN}")
        record_timeline_event(run_dir, "live_session_start")
        rc = restore_dtbo_from_android(
            odin=odin,
            dtbo_rollback_ap=m25_stock_dtbo_ap,
            run_dir=run_dir,
            log_path=log_path,
            serial=selected_serial,
            odin_wait_sec=args.odin_wait_sec,
            android_wait_sec=args.android_wait_sec,
        )
        record_timeline_event(run_dir, "live_session_end")
        print(f"M25 stock DTBO restore-from-android completed rc={rc}; log={log_path}")
        return rc

    verify_partition_hash(log_path, selected_serial, "dtbo", EXPECTED_STOCK_DTBO_RAW_SHA256, "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M25 boot/DTBO candidates, rollback APs, AGENTS exception, Android stability, "
            f"boot/vendor_boot/stock-DTBO hashes verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    reboot_android_to_download(selected_serial, log_path, "m25_dtbo_candidate")
    dtbo_odin_device = wait_for_odin(odin, log_path, "m25-dtbo-candidate-wait", args.odin_wait_sec)
    if dtbo_odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        return 2
    record_timeline_event(run_dir, "dtbo_candidate_flash_start")
    dtbo_rc = flash_ap(odin, m25_dtbo_ap, dtbo_odin_device, log_path, "m25_dtbo_candidate")
    record_timeline_event(run_dir, "dtbo_candidate_flash_done")
    if dtbo_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        return dtbo_rc or 3

    patched_android = wait_for_android_root(log_path, args.android_wait_sec, selected_serial)
    if patched_android is None:
        record_timeline_event(run_dir, "live_session_end")
        print("Android did not return after M25 high-speed DTBO. Enter Download and run --restore-dtbo-from-download.", file=sys.stderr)
        return 6
    verify_partition_hash(log_path, patched_android, "dtbo", EXPECTED_M25_PATCHED_DTBO_RAW_SHA256, "patched")

    reboot_android_to_download(patched_android, log_path, "m25_boot_candidate")
    boot_odin_device = wait_for_odin(odin, log_path, "m25-boot-candidate-wait", args.odin_wait_sec)
    if boot_odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print("Download mode did not appear for M25 boot flash; restore stock DTBO if needed.", file=sys.stderr)
        return 2
    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m25_ap, boot_odin_device, log_path, "m25_boot_candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        return candidate_rc or 3

    print("M25 boot candidate flashed. Waiting for HS-only ACM/ADB/Odin.")
    observed, endpoint = observe_m25(run_dir, log_path, args.m25_observe_sec, odin)
    if endpoint is not None:
        record_timeline_event(run_dir, "candidate_boot_ready")
    if observed == "acm" and endpoint:
        append_log(log_path, f"m25_result=acm_seen_manual_download_required endpoint={endpoint}")
        record_timeline_event(run_dir, "live_session_end")
        print(
            "M25 ACM appeared. Enter Download mode manually and run --rollback-from-download "
            "to restore Magisk boot and stock DTBO.",
            file=sys.stderr,
        )
        return 4
    if observed == "odin":
        odin_device = endpoint
    elif observed == "adb" and endpoint:
        append_log(log_path, f"m25_unexpected_adb_returned={endpoint}")
        reboot_android_to_download(endpoint, log_path, "m25_unexpected_adb_rollback")
        odin_device = wait_for_odin(odin, log_path, "m25-unexpected-adb-rollback-wait", args.odin_wait_sec)
    else:
        append_log(log_path, "m25_result=no_acm_no_transport_manual_download_required")
        record_timeline_event(run_dir, "live_session_end")
        print("M25 did not expose rollback transport. Enter Download mode manually and run --rollback-from-download.", file=sys.stderr)
        return 4
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        return 4

    rc = rollback_boot_from_odin_device(
        odin=odin,
        boot_rollback_ap=boot_rollback_ap,
        stock_boot_fallback_ap=stock_rollback_ap,
        dtbo_rollback_ap=m25_stock_dtbo_ap,
        odin_device=odin_device,
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=args.rollback_target,
        odin_wait_sec=args.odin_wait_sec,
        android_wait_sec=args.android_wait_sec,
    )
    print(f"M25 live gate completed rollback rc={rc}; log={log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
