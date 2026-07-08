#!/usr/bin/env python3
"""Guarded S22+ M34 S2 pullup-knobs runtime-gadget native-init live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M34 S2 starts from the P30-proven full ACM module closure and the S1-proven
stock configfs gadget setup, adds only the two off-stock pullup knobs
(`max_speed=high-speed`, `usb_role=device`), and parks before the final
`UDC=a600000.dwc3` pullup.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_m32_wdt_hs_acm import EXPECTED_M32_MODULES
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


LIVE_ACK_TOKEN = "S22PLUS-M34-S2-PULLUP-KNOBS-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M34-S2-PULLUP-KNOBS-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_STAGE = "S2"
EXPECTED_M34_MARKER = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S2"
EXPECTED_M34_AP_SHA256 = "d235e6fd7c77c9fc2b63bd7280dcbf430783c9b62b5f361f43441c24687c38b3"
EXPECTED_M34_BOOT_SHA256 = "f8838867e0b0fab5ffe5aa8717565d9304f635ef04487596a0baeb03b2dd7a70"
EXPECTED_M34_INIT_SHA256 = "fba33555bcc73d834a7dbfe87dc5e6fe3b622184d163ae72d478e18a0ce653b8"
EXPECTED_M34_MODULE_LIST_SHA256 = "2291dc1c72add131c42d0b4ed6649880c20316d0598e0a2af942cc774949062c"
EXPECTED_M34_TEMPLATE_SOURCE_SHA256 = "ac20dcf724cf6864540d65958332d561d45409e7e85785a8c014882b37e29193"
EXPECTED_M34_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M34_BASE_BOOT_SHA256 = EXPECTED_BASE_BOOT_SHA256
EXPECTED_MODULE_ENTRY = "s22plus_m34_s2_runtime_gadget_split.modules"
EXPECTED_STOCK_RECIPE_REPORT = "docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md"
EXPECTED_MODULES = EXPECTED_M32_MODULES

DEFAULT_M34_AP = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_2/S2/odin4/AP.tar.md5")
DEFAULT_M34_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_2/manifest.json")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m34_s2_runtime_gadget_live_gate_{utc_stamp()}")
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
        "S22+ M34 S2 pullup-knobs runtime-gadget native-init boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_m34_s2_runtime_gadget_live_gate.py",
        LIVE_ACK_TOKEN,
        ROLLBACK_ACK_TOKEN,
        EXPECTED_TARGET,
        EXPECTED_STAGE,
        EXPECTED_M34_MARKER,
        EXPECTED_M34_AP_SHA256,
        EXPECTED_M34_BOOT_SHA256,
        EXPECTED_M34_INIT_SHA256,
        EXPECTED_M34_MODULE_LIST_SHA256,
        EXPECTED_M34_TEMPLATE_SOURCE_SHA256,
        EXPECTED_M34_KERNEL_SHA256,
        EXPECTED_M34_BASE_BOOT_SHA256,
        "stock-ordered configfs gadget/function/config",
        "UDC=none",
        "0x04E8:0x6860",
        "ss_acm.0 link",
        "max_speed=high-speed",
        "usb_role=device",
        "no final UDC bind",
        "no UDC=a600000.dwc3",
        "no reboot syscall",
        "no Download beacon",
        "no Android/Magisk handoff",
        "no persistent partition mount",
        "no block write",
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


def has_draft_only_m34_exception(text: str) -> bool:
    normalized = " ".join(text.split())
    has_m34_marker = LIVE_ACK_TOKEN in normalized or EXPECTED_M34_MARKER in normalized
    has_draft_marker = any(
        marker in normalized
        for marker in (
            "DRAFT ONLY",
            "This draft is not active authorization",
            "draft is not active authorization",
        )
    )
    return has_m34_marker and has_draft_marker


def agents_exception_draft() -> str:
    marker_lines = "\n".join(f"   `{marker}`" for marker in policy_required_markers())
    return f"""   **DRAFT ONLY - Narrow operator-authorized exception (2026-07-09, S22+ M34 S2 pullup-knobs runtime-gadget boot-only live gate):**
   This draft is not active authorization unless the operator explicitly approves
   it and the block is inserted into `AGENTS.md`. After approval, Codex may run
   one bounded attended boot-partition-only M34 S2 live gate on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s2_runtime_gadget_live_gate.py`.
   Live ack token: `{LIVE_ACK_TOKEN}`. Rollback ack token:
   `{ROLLBACK_ACK_TOKEN}`.

   The exact candidate AP.tar.md5 SHA256 must be
   `{EXPECTED_M34_AP_SHA256}`; contained padded `boot.img` SHA256 must be
   `{EXPECTED_M34_BOOT_SHA256}`; direct `/init` SHA256 must be
   `{EXPECTED_M34_INIT_SHA256}`; template source SHA256 must be
   `{EXPECTED_M34_TEMPLATE_SOURCE_SHA256}`; module-list SHA256 must be
   `{EXPECTED_M34_MODULE_LIST_SHA256}`; preserved kernel SHA256 must be
   `{EXPECTED_M34_KERNEL_SHA256}`; and known-booting base Magisk boot SHA256
   must be `{EXPECTED_M34_BASE_BOOT_SHA256}`. The AP must contain exactly one
   tar member, `boot.img.lz4`, and must not carry recovery, vendor_boot, dtbo,
   vbmeta, vbmeta_system, BL, CP, CSC, super, persist, userdata, EFS,
   sec_efs, RPMB, keymaster, modem, bootloader, or any other partition payload.

   The candidate is limited to freestanding direct PID1 M34 S2 behavior:
   stock-ordered configfs gadget/function/config, `UDC=none`, stock IDs
   `0x04E8:0x6860`, `ss_acm.0 link`, `max_speed=high-speed`, and
   `usb_role=device`. It must have no final UDC bind and no
   `UDC=a600000.dwc3`. It must have no reboot syscall, no Download beacon, no
   Android/Magisk handoff, no persistent partition mount, no block write, no
   module binary injection into boot ramdisk, no raw host `dd`, no fastboot, no
   Magisk modules, no multidisabler, no format data, no DTBO/vendor_boot/
   recovery/vbmeta/non-boot flash, and no A90 action. Manual Download rollback
   is recovery-only after the helper requests it. Survival proof requires it
   survives past 60-90 seconds; PMIC/RDX abnormal reset before the observation
   window is FAIL. The module closure must keep `phy-msm-ssusb-qmp.ko
   intentionally excluded` and `EUD excluded`. This exception does not
   authorize S1 repeat, S3 live, final UDC pullup, DTBO surgery, M32 repeat, display/
   distro candidates, kernel rebuilds, RDX PC dump retrieval, EUD writes, or
   any non-boot partition action.

   Required policy marker coverage:
{marker_lines}
"""


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    draft_only = has_draft_only_m34_exception(agents)
    append_log(log_path, f"agents_exception_draft_only_present={int(draft_only)}")
    if draft_only:
        raise SystemExit("AGENTS.md contains draft-only M34 S2 authorization text; refuse to treat draft as active live auth")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M34 S2 runtime-gadget authorization markers: {missing}")


def find_stage(data: dict[str, Any], label: str) -> dict[str, Any]:
    for stage in data.get("stages", []):
        if stage.get("label") == label:
            return stage
    raise SystemExit(f"M34 manifest does not contain {label} stage")


def verify_m34_manifest(path: Path, log_path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"M34 manifest missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    stage = find_stage(data, EXPECTED_STAGE)
    hashes = stage.get("hashes", {})
    safety = data.get("safety", {})
    matrix = data.get("matrix", {})
    closure = stage.get("closure", {})
    ramdisk = stage.get("ramdisk", {})
    init_info = stage.get("init", {})
    runtime_steps = stage.get("runtime_steps", {})
    tar_members_seen = stage.get("tar_members")
    append_log(log_path, f"m34_manifest_path={path}")
    append_log(log_path, f"m34_s2_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m34_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m34_manifest_matrix={json.dumps(matrix, sort_keys=True)}")
    append_log(log_path, f"m34_s2_manifest_runtime_steps={json.dumps(runtime_steps, sort_keys=True)}")
    append_log(log_path, f"m34_s2_manifest_closure={json.dumps(closure, sort_keys=True)}")
    append_log(log_path, f"m34_s2_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m34_s2_manifest_init_file={init_info.get('file', '')}")

    if data.get("target") != EXPECTED_TARGET:
        raise SystemExit(f"M34 target mismatch: {data.get('target')!r}")
    if data.get("stock_recipe_report") != EXPECTED_STOCK_RECIPE_REPORT:
        raise SystemExit(f"M34 stock recipe report mismatch: {data.get('stock_recipe_report')!r}")
    if data.get("hashes", {}).get("template_source") != EXPECTED_M34_TEMPLATE_SOURCE_SHA256:
        raise SystemExit("M34 template source hash mismatch")
    if data.get("hashes", {}).get("nochange_repack_boot") != EXPECTED_M34_BASE_BOOT_SHA256:
        raise SystemExit("M34 no-change MagiskBoot repack is not pinned to the known booting base")
    if data.get("magiskboot", {}).get("nochange_repack_byte_identical") is not True:
        raise SystemExit("M34 no-change MagiskBoot repack is not byte-identical")
    if matrix.get("live_order") != ["S1", "S2", "S3"]:
        raise SystemExit(f"M34 live order mismatch: {matrix.get('live_order')!r}")
    if matrix.get("p30_is_s0") is not True or matrix.get("module_closure_matches_p30_and_m32") is not True:
        raise SystemExit("M34 matrix no longer treats P30 as S0 or closure no longer matches")

    if stage.get("stage_number") != 2:
        raise SystemExit(f"M34 S2 stage number mismatch: {stage.get('stage_number')!r}")
    expected_steps = {
        "configfs_gadget": True,
        "udc_none": True,
        "max_speed_high_speed": True,
        "usb_role_force": True,
        "udc_bind": False,
    }
    if runtime_steps != expected_steps:
        raise SystemExit(f"M34 S2 runtime steps mismatch: {runtime_steps!r}")
    required_hashes = {
        "ap_tar_md5": EXPECTED_M34_AP_SHA256,
        "boot_img": EXPECTED_M34_BOOT_SHA256,
        "base_boot": EXPECTED_M34_BASE_BOOT_SHA256,
        "kernel": EXPECTED_M34_KERNEL_SHA256,
        "m34_init": EXPECTED_M34_INIT_SHA256,
        "m34_modules": EXPECTED_M34_MODULE_LIST_SHA256,
    }
    for key, expected in required_hashes.items():
        if hashes.get(key) != expected:
            raise SystemExit(f"M34 S2 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M34 S2 manifest tar members mismatch: {tar_members_seen!r}")

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
        "stage_s2_sets_max_speed_high_speed": True,
        "stage_s2_no_udc_bind": True,
        "stock_order_udc_none_before_ids_and_link": True,
        "watchdog_managed": True,
        "qmp_module_excluded": True,
        "eud_module_excluded": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M34 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")

    if closure.get("modules") != EXPECTED_MODULES:
        raise SystemExit(f"M34 S2 module closure mismatch: {closure.get('modules')!r}")
    if closure.get("module_count") != len(EXPECTED_MODULES):
        raise SystemExit(f"M34 S2 module closure count mismatch: {closure.get('module_count')!r}")
    if closure.get("module_sha256") != EXPECTED_M34_MODULE_LIST_SHA256:
        raise SystemExit(f"M34 S2 module list SHA mismatch: {closure.get('module_sha256')!r}")
    if any(module in closure.get("modules", []) for module in ("phy-msm-ssusb-qmp.ko", "eud.ko")):
        raise SystemExit("M34 S2 excluded QMP/EUD module leaked into closure")

    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M34 S2 manifest did not replace /init")
    if ramdisk.get("added_subset_entry") != EXPECTED_MODULE_ENTRY:
        raise SystemExit(f"M34 S2 module list ramdisk entry mismatch: {ramdisk.get('added_subset_entry')!r}")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M34 S2 must not inject module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 1:
        raise SystemExit("M34 S2 must inject exactly one module-list text file into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M34_MARKER,
        "version=0.2",
        "module_list=dep_complete_runtime_gadget_split",
        "stage=S2",
        "runtime_step=S2",
        "module_count=45",
        "phase=modules_load_done",
        "phase=configfs_done",
        "phase=park_enter",
        "/config/usb_gadget/g1",
        "/config/usb_gadget/g1/UDC",
        "/config/usb_gadget/g1/functions/ss_acm.0",
        "../../functions/ss_acm.0",
        "stock_order=1",
        "udc_none=1",
        "0x04E8",
        "0x0200",
        "0x6860",
        "900",
        "none",
        "max_speed_high_speed=1",
        "/config/usb_gadget/g1/max_speed",
        "high-speed",
        "phase=max_speed",
        "role_force=1",
        "/sys/class/usb_role",
        "phase=usb_role_done",
        "udc_bind=0",
        "no_reboot_request=1",
        "no_download_beacon=1",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M34 S2 required string missing from manifest: {required}")
    for forbidden in [
        "phase=udc_bind",
        "a600000.dwc3",
    ]:
        if forbidden in required_strings:
            raise SystemExit(f"M34 S2 forbidden string present in manifest: {forbidden}")

    objdump_path = path.parent / EXPECTED_STAGE / str(init_info.get("objdump_path", ""))
    if not objdump_path.is_file():
        raise SystemExit(f"M34 S2 objdump missing: {objdump_path}")
    objdump = objdump_path.read_text(encoding="utf-8", errors="replace")
    if not any("mov" in line and "#0x111" in line and "// #273" in line for line in objdump.splitlines()):
        raise SystemExit("M34 S2 /init does not load arm64 __NR_finit_module (273)")
    if any("mov" in line and "#0x8e" in line and "// #142" in line for line in objdump.splitlines()):
        raise SystemExit("M34 S2 /init must not load arm64 __NR_reboot (142)")


def verify_m34_artifacts(
    *,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> None:
    verify_ap(m34_ap, EXPECTED_M34_AP_SHA256, "m34_s2_candidate", log_path)
    verify_m34_manifest(m34_manifest, log_path)
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
    append_log(log_path, f"m34_s2_observe_start_utc={utc_now()}")
    append_log(log_path, f"m34_s2_observe_sec={observe_sec}")
    while time.monotonic() < deadline:
        now = time.monotonic()
        elapsed = now - start
        if now >= next_snapshot:
            iteration += 1
            label = f"m34_s2_park_observe_{iteration:03d}"
            append_log(log_path, f"{label}_elapsed_sec={elapsed:.3f}")
            host_snapshot(run_dir, log_path, label, odin)
            devices = odin_devices(odin, log_path, f"{label}-odin-extra")
            if len(devices) == 1:
                append_log(log_path, f"m34_s2_result=unexpected_odin_before_survival_window elapsed_sec={elapsed:.3f} device={devices[0]}")
                return "unexpected-odin-before-survival-window", devices[0]
            if len(devices) > 1:
                raise SystemExit(f"refusing ambiguous Odin devices during M34 S2 observation: {devices}")
            rows = adb_rows(log_path, f"{label}-adb-extra")
            usable = [row for row in rows if row[1] == "device"]
            if usable:
                append_log(log_path, f"m34_s2_result=unexpected_adb_before_survival_window elapsed_sec={elapsed:.3f} rows={usable}")
                return "unexpected-adb-before-survival-window", None
            next_snapshot = now + snapshot_interval_sec
        time.sleep(0.5)
    append_log(log_path, "m34_s2_survival_window_pass=1")
    append_log(log_path, "m34_s2_result=survived-observation-window-manual-download-required")
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
        append_log(log_path, f"m34_s2_{label}_magisk_rollback_failed_attempting_stock_fallback=1")
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
        verify_partition_hash(log_path, android, "boot", EXPECTED_M34_BASE_BOOT_SHA256, f"{label}_boot_restore")
    else:
        append_log(log_path, f"m34_s2_{label}_boot_restore_hash_check=skipped rollback_target=stock")
    record_timeline_event(run_dir, "rollback_boot_ready")
    record_timeline_event(run_dir, f"{label}_rollback_boot_ready")
    marker_found = collect_android_pstore(run_dir, log_path, f"post_m34_s2_{label}_rollback", android, marker=EXPECTED_M34_MARKER)
    append_log(log_path, f"m34_s2_{label}_retained_marker_found={int(marker_found)}")
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
    devices = odin_devices(odin, log_path, "m34-s2-rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"M34 S2 rollback requires exactly one Odin device, got {devices}")
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
    parser.add_argument("--m34-ap", type=Path, default=DEFAULT_M34_AP)
    parser.add_argument("--m34-manifest", type=Path, default=DEFAULT_M34_MANIFEST)
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
    parser.add_argument("--print-agents-exception-draft", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (args.offline_check, args.print_agents_exception_draft, args.live, args.rollback_from_download)
        if enabled
    )
    if modes > 1:
        raise SystemExit("--offline-check, --print-agents-exception-draft, --live, and --rollback-from-download are mutually exclusive")
    if args.observe_sec < 60:
        raise SystemExit("--observe-sec must be at least 60 for the M34 S2 pullup-knobs discriminator")
    if args.snapshot_interval_sec < 1.0:
        raise SystemExit("--snapshot-interval-sec must be at least 1.0")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m34_s2_runtime_gadget_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M34 S2 runtime gadget live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")

    odin = resolve(root, args.odin)
    m34_ap = resolve(root, args.m34_ap)
    m34_manifest = resolve(root, args.m34_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)
    rollback_ap = magisk_rollback_ap if args.rollback_target == ROLLBACK_MAGISK else stock_rollback_ap
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")

    verify_m34_artifacts(
        m34_ap=m34_ap,
        m34_manifest=m34_manifest,
        magisk_rollback_ap=magisk_rollback_ap,
        stock_rollback_ap=stock_rollback_ap,
        log_path=log_path,
    )

    if args.print_agents_exception_draft:
        draft = agents_exception_draft()
        missing = missing_policy_markers(draft)
        append_log(log_path, f"agents_exception_draft_missing={missing}")
        if missing:
            raise SystemExit(f"internal draft is missing policy markers: {missing}")
        print(draft, end="")
        return 0

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M34 S2 candidate and rollback APs verified; no device action; log={log_path}")
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
        print(f"M34 S2 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(
        log_path,
        selected_serial,
        args.android_stability_samples,
        args.android_stability_interval_sec,
    )
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_M34_BASE_BOOT_SHA256, "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(
            "dry-run ok: M34 S2 candidate, rollback APs, AGENTS exception, Android stability, "
            f"and current boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    print(
        "M34 S2 live gate starting. This candidate should park after S2 pullup-knobs setup "
        f"with UDC=none; do not press keys during the {args.observe_sec}s observation window. "
        "Manual Download is only for rollback after the helper asks.",
        flush=True,
    )
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print("download mode did not appear for M34 S2 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m34_ap, odin_device, log_path, "candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        print(f"M34 S2 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        append_log(log_path, "m34_s2_result=no-proof-original-download-never-disconnected")
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
    print(f"M34 S2 candidate flashed. Observing for {args.observe_sec}s survival window.", flush=True)
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
                f"M34 S2 stopped before survival proof ({result}). If the device is not in Android, "
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
        "M34 S2 survived the observation window. Enter Download mode manually for rollback now; "
        f"waiting up to {args.manual_download_wait_sec}s.",
        flush=True,
    )
    rollback_device = wait_for_odin(odin, log_path, "manual-rollback-wait", args.manual_download_wait_sec)
    if rollback_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print(
            f"M34 S2 survival window passed, but manual Download mode did not appear. "
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
    print(f"M34 S2 live gate completed rc={rc}; result={result}; log={log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
