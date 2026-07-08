#!/usr/bin/env python3
"""Guarded S22+ M34 S6 stock-speed softdep runtime-gadget live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M34 S6 removes the USB2 high-speed forcing used by S2-S5, restores the stock
QMP/EUD/ucsi dwc3_msm softdep closure, keeps `ssusb/mode=peripheral`, binds
`UDC=a600000.dwc3`, and parks for host observation. It does not write EUD sysfs
knobs and does not soft_connect.
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

from build_s22plus_m32_wdt_hs_acm import EXPECTED_M32_MODULES
from build_s22plus_m34_runtime_gadget_split import M34_S6_EXPECTED_NEW_MODULES, M34_S6_STOCK_SOFTDEP_TARGETS
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


LIVE_ACK_TOKEN = "S22PLUS-M34-S6-STOCK-SOFTDEP-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M34-S6-STOCK-SOFTDEP-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_STAGE = "S6"
EXPECTED_M34_MARKER = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S6"
EXPECTED_M34_AP_SHA256 = "f1ff77b7df434536029db417291689bff8b3a7dcdf4fda38fef5322475daad39"
EXPECTED_M34_BOOT_SHA256 = "b1bfc4ece7ece60af752bc570e0ae4ce76230d13b129b1c58d4e840cd92225f6"
EXPECTED_M34_INIT_SHA256 = "ca3eb2b5a0fedff73cfb0aaa249d42f4b92fcb99b360e9ec5a041649dcd7dd8c"
EXPECTED_M34_MODULE_LIST_SHA256 = "51ba77aeed1966a2de8c78d307ca3d6fe5440daa2b96488679446f6056142515"
EXPECTED_M34_TEMPLATE_SOURCE_SHA256 = "ce023ba98006e49839433ce16ec8321bd9003b74151f39879fcecb682fef9ecc"
EXPECTED_M34_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M34_BASE_BOOT_SHA256 = EXPECTED_BASE_BOOT_SHA256
EXPECTED_MODULE_ENTRY = "s22plus_m34_s6_runtime_gadget_split.modules"
EXPECTED_STOCK_RECIPE_REPORT = "docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md"
EXPECTED_MODULES = (
    EXPECTED_M32_MODULES[:29]
    + ["eud.ko", "phy-msm-ssusb-qmp.ko"]
    + EXPECTED_M32_MODULES[29:]
    + M34_S6_EXPECTED_NEW_MODULES[2:]
)

DEFAULT_M34_AP = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/S6/odin4/AP.tar.md5")
DEFAULT_M34_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_5/manifest.json")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m34_s6_stock_softdep_live_gate_{utc_stamp()}")
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
        "S22+ M34 S6 stock-speed softdep runtime-gadget native-init boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py",
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
        "no g1/max_speed=high-speed",
        "no /sys/class/usb_role",
        "no ssusb/speed=high-speed",
        "ssusb/mode=peripheral",
        "final UDC bind",
        "UDC=a600000.dwc3",
        "no soft_connect",
        "no /sys/class/udc/a600000.dwc3/soft_connect",
        "stock dwc3_msm softdep parity",
        "stock_softdep_parity=1",
        "qmp_module=1",
        "eud_module=1",
        "ucsi_glink=1",
        "phy-msm-ssusb-qmp.ko included",
        "eud.ko included without EUD sysfs write",
        "ucsi_glink.ko included",
        "no descriptor or companion-function change",
        "enhanced host USB observation",
        "lsusb -d 04e8:6860 -v",
        "usb-devices",
        "udev properties",
        "host dmesg delta",
        "no reboot syscall",
        "no Download beacon",
        "no Android/Magisk handoff",
        "no persistent partition mount",
        "no block write",
        "manual Download rollback is recovery-only",
        "survives past 60-90 seconds",
        "PMIC/RDX abnormal reset before the observation window is FAIL",
        "no EUD sysfs write",
        *M34_S6_STOCK_SOFTDEP_TARGETS,
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
    return f"""   **DRAFT ONLY - Narrow operator-authorized exception (2026-07-09, S22+ M34 S6 stock-speed softdep runtime-gadget boot-only live gate):**
   This draft is not active authorization unless the operator explicitly approves
   it and the block is inserted into `AGENTS.md`. After approval, Codex may run
   one bounded attended boot-partition-only M34 S6 live gate on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s6_stock_softdep_live_gate.py`.
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

   The candidate is limited to freestanding direct PID1 M34 S6 behavior:
   stock-ordered configfs gadget/function/config, `UDC=none`, stock IDs
   `0x04E8:0x6860`, `ss_acm.0 link`, no `g1/max_speed=high-speed`, no
   `/sys/class/usb_role`, no `ssusb/speed=high-speed`,
   `ssusb/mode=peripheral`, final UDC bind, `UDC=a600000.dwc3`, no
   `soft_connect`, and no `/sys/class/udc/a600000.dwc3/soft_connect`.
   It must restore stock dwc3_msm softdep parity through the module list:
   `stock_softdep_parity=1`, `qmp_module=1`, `eud_module=1`,
   `ucsi_glink=1`, `phy-msm-ssusb-qmp.ko included`,
   `eud.ko included without EUD sysfs write`, and `ucsi_glink.ko included`.
   It must make no descriptor or companion-function change and no EUD sysfs write.
   It must have no
   reboot syscall, no Download beacon, no
   Android/Magisk handoff, no persistent partition mount, no block write, no
   module binary injection into boot ramdisk, no raw host `dd`, no fastboot, no
   Magisk modules, no multidisabler, no format data, no DTBO/vendor_boot/
   recovery/vbmeta/non-boot flash, and no A90 action. Manual Download rollback
   is recovery-only after the helper requests it. Survival proof requires it
   survives past 60-90 seconds; PMIC/RDX abnormal reset before the observation
   window is FAIL. The helper must collect enhanced host USB observation
   including `lsusb -d 04e8:6860 -v`, `usb-devices`, udev properties, and host
   dmesg delta. The module closure must include `phy-msm-ssusb-qmp.ko`,
   `eud.ko`, `ucsi_glink.ko`, and their dependency-complete closure. This
   exception does not authorize S1/S2/S3/S4/S5 repeat, post-pullup command
   channels, DTBO surgery, M32 repeat, display/distro candidates, kernel
   rebuilds, RDX PC dump retrieval, EUD sysfs writes, or
   any non-boot partition action.

   Required policy marker coverage:
{marker_lines}
"""


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    draft_only = has_draft_only_m34_exception(agents)
    append_log(log_path, f"agents_exception_draft_only_present={int(draft_only)}")
    if draft_only:
        raise SystemExit("AGENTS.md contains draft-only M34 S6 authorization text; refuse to treat draft as active live auth")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M34 S6 runtime-gadget authorization markers: {missing}")


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
    append_log(log_path, f"m34_s6_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m34_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m34_manifest_matrix={json.dumps(matrix, sort_keys=True)}")
    append_log(log_path, f"m34_s6_manifest_runtime_steps={json.dumps(runtime_steps, sort_keys=True)}")
    append_log(log_path, f"m34_s6_manifest_closure={json.dumps(closure, sort_keys=True)}")
    append_log(log_path, f"m34_s6_manifest_ramdisk={json.dumps(ramdisk, sort_keys=True)}")
    append_log(log_path, f"m34_s6_manifest_init_file={init_info.get('file', '')}")

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
    if matrix.get("live_order") != ["S1", "S2", "S3", "S4", "S5", "S6"]:
        raise SystemExit(f"M34 live order mismatch: {matrix.get('live_order')!r}")
    if (
        matrix.get("p30_is_s0") is not True
        or matrix.get("module_closure_matches_p30_and_m32_for_s1_s5") is not True
        or matrix.get("s6_module_closure_restores_stock_dwc3_softdep") is not True
    ):
        raise SystemExit("M34 matrix no longer proves P30/S1-S5/S6 closure contract")
    if matrix.get("s6_stock_softdep_targets") != M34_S6_STOCK_SOFTDEP_TARGETS:
        raise SystemExit(f"M34 S6 stock softdep targets mismatch: {matrix.get('s6_stock_softdep_targets')!r}")
    if matrix.get("s6_stock_softdep_new_modules") != M34_S6_EXPECTED_NEW_MODULES:
        raise SystemExit(f"M34 S6 new module list mismatch: {matrix.get('s6_stock_softdep_new_modules')!r}")

    if stage.get("stage_number") != 6:
        raise SystemExit(f"M34 S6 stage number mismatch: {stage.get('stage_number')!r}")
    expected_steps = {
        "configfs_gadget": True,
        "udc_none": True,
        "max_speed_high_speed": False,
        "usb_role_force": False,
        "ssusb_speed_high_speed": False,
        "ssusb_mode_peripheral": True,
        "udc_bind": True,
        "soft_connect": False,
        "stock_softdep_parity": True,
        "qmp_module_included": True,
        "eud_module_included": True,
        "ucsi_glink_included": True,
    }
    if runtime_steps != expected_steps:
        raise SystemExit(f"M34 S6 runtime steps mismatch: {runtime_steps!r}")
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
            raise SystemExit(f"M34 S6 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if tar_members_seen != [EXPECTED_MEMBER]:
        raise SystemExit(f"M34 S6 manifest tar members mismatch: {tar_members_seen!r}")

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
        "stage_s3_binds_only_a600000_dwc3": True,
        "stage_s4_replaces_dead_usb_role_with_ssusb_role_lever": True,
        "stage_s4_sets_ssusb_speed_high_speed_before_udc_bind": True,
        "stage_s4_sets_ssusb_mode_peripheral_before_udc_bind": True,
        "stage_s4_no_usb_role_force": True,
        "stage_s5_soft_connect_after_udc_bind": True,
        "stage_s5_no_descriptor_or_companion_change": True,
        "stage_s6_includes_qmp_eud_ucsi_softdep_parity": True,
        "stage_s6_no_high_speed_force": True,
        "stage_s6_no_soft_connect": True,
        "stage_s6_no_eud_sysfs_write": True,
        "stage_s6_restores_stock_speed_policy": True,
        "stage_s6_keeps_ssusb_mode_peripheral_before_udc_bind": True,
        "stage_s6_no_descriptor_or_companion_change": True,
        "stock_order_udc_none_before_ids_and_link": True,
        "watchdog_managed": True,
        "qmp_module_excluded_for_s1_s5": True,
        "eud_module_excluded_for_s1_s5": True,
        "ucsi_glink_excluded_for_s1_s5": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M34 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")

    if closure.get("modules") != EXPECTED_MODULES:
        raise SystemExit(f"M34 S6 module closure mismatch: {closure.get('modules')!r}")
    if closure.get("module_count") != len(EXPECTED_MODULES):
        raise SystemExit(f"M34 S6 module closure count mismatch: {closure.get('module_count')!r}")
    if closure.get("module_sha256") != EXPECTED_M34_MODULE_LIST_SHA256:
        raise SystemExit(f"M34 S6 module list SHA mismatch: {closure.get('module_sha256')!r}")
    for module in ("phy-msm-ssusb-qmp.ko", "eud.ko", "ucsi_glink.ko"):
        if module not in closure.get("modules", []):
            raise SystemExit(f"M34 S6 stock softdep module missing from closure: {module}")
    if closure.get("stock_softdep_targets") != M34_S6_STOCK_SOFTDEP_TARGETS:
        raise SystemExit(f"M34 S6 closure stock targets mismatch: {closure.get('stock_softdep_targets')!r}")
    if closure.get("stock_softdep_new_modules") != M34_S6_EXPECTED_NEW_MODULES:
        raise SystemExit(f"M34 S6 closure new modules mismatch: {closure.get('stock_softdep_new_modules')!r}")
    if "sec_debug_region.ko" in closure.get("modules", []):
        raise SystemExit("M34 S6 sec_debug_region leaked into closure")

    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M34 S6 manifest did not replace /init")
    if ramdisk.get("added_subset_entry") != EXPECTED_MODULE_ENTRY:
        raise SystemExit(f"M34 S6 module list ramdisk entry mismatch: {ramdisk.get('added_subset_entry')!r}")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M34 S6 must not inject module binaries into boot ramdisk")
    if ramdisk.get("module_list_files_injected_into_boot_ramdisk") != 1:
        raise SystemExit("M34 S6 must inject exactly one module-list text file into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M34_MARKER,
        "version=0.5",
        "module_list=dep_complete_runtime_gadget_split",
        "stage=S6",
        "runtime_step=S6",
        "module_count=55",
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
        "max_speed_high_speed=0",
        "role_force=0",
        "ssusb_speed_high_speed=0",
        "ssusb_mode_peripheral=1",
        "/sys/devices/platform/soc/a600000.ssusb/mode",
        "peripheral",
        "phase=ssusb_mode",
        "udc_bind=1",
        "/sys/class/udc",
        "a600000.dwc3",
        "phase=udc_bind",
        "soft_connect=0",
        "stock_softdep_parity=1",
        "qmp_module=1",
        "eud_module=1",
        "ucsi_glink=1",
        "no_reboot_request=1",
        "no_download_beacon=1",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M34 S6 required string missing from manifest: {required}")
    forbidden_required_strings = [
        "/sys/class/usb_role",
        "phase=usb_role_done",
        "/config/usb_gadget/g1/max_speed",
        "high-speed",
        "phase=max_speed",
        "/sys/devices/platform/soc/a600000.ssusb/speed",
        "phase=ssusb_speed",
        "/sys/class/udc/a600000.dwc3/soft_connect",
        "phase=soft_connect",
        "value=connect",
    ]
    for forbidden in forbidden_required_strings:
        if forbidden in required_strings:
            raise SystemExit(f"M34 S6 manifest unexpectedly requires forbidden string: {forbidden}")

    objdump_path = path.parent / EXPECTED_STAGE / str(init_info.get("objdump_path", ""))
    if not objdump_path.is_file():
        raise SystemExit(f"M34 S6 objdump missing: {objdump_path}")
    objdump = objdump_path.read_text(encoding="utf-8", errors="replace")
    if not any("mov" in line and "#0x111" in line and "// #273" in line for line in objdump.splitlines()):
        raise SystemExit("M34 S6 /init does not load arm64 __NR_finit_module (273)")
    if any("mov" in line and "#0x8e" in line and "// #142" in line for line in objdump.splitlines()):
        raise SystemExit("M34 S6 /init must not load arm64 __NR_reboot (142)")


def verify_m34_artifacts(
    *,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> None:
    verify_ap(m34_ap, EXPECTED_M34_AP_SHA256, "m34_s6_candidate", log_path)
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


def redact_host_usb_text(text: str) -> str:
    text = re.sub(r"(?im)^(\s*iSerial\s+\d+\s+).*$", r"\1<redacted>", text)
    text = re.sub(r"(?im)^(ID_SERIAL(?:_SHORT)?=).*$", r"\1<redacted>", text)
    text = re.sub(r"(?im)^(ID_USB_SERIAL(?:_SHORT)?=).*$", r"\1<redacted>", text)
    text = re.sub(r"(?im)^(DEVLINKS=.*)$", lambda m: re.sub(r"/by-id/\S+", "/by-id/<redacted>", m.group(1)), text)
    text = re.sub(r"RFCT[0-9A-Z]+", "<redacted>", text)
    return text


def host_usb_command(run_dir: Path, log_path: Path, label: str, name: str, command: list[str], timeout: float = 10.0) -> str:
    result = run(command, timeout=timeout)
    text = redact_host_usb_text(result.stdout + result.stderr)
    out_path = run_dir / f"{label}_{name}.txt"
    out_path.write_text(text, encoding="utf-8", errors="replace")
    append_log(log_path, f"{label}_{name}_rc={result.returncode} bytes={len(text.encode('utf-8'))} path={out_path}")
    return text


def samsung_usb_devices_summary(usb_devices_text: str) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", usb_devices_text):
        product_match = re.search(r"(?im)^P:\s+Vendor=04e8\s+ProdID=([0-9a-f]{4})\b", block)
        if not product_match:
            continue
        speed_match = re.search(r"(?im)^T:.*\bSpd=\s*([0-9]+)", block)
        name_match = re.search(r"(?im)^S:\s+Product=(.*)$", block)
        rev_match = re.search(r"(?im)^P:.*\bRev=([0-9a-fA-F.]+)", block)
        classes: list[str] = []
        drivers: list[str] = []
        for iface in re.finditer(r"(?im)^I:.*?\bCls=([0-9a-f]{2})\(([^)]*)\).*?\bDriver=(\S+)", block):
            cls = iface.group(1).lower()
            desc = " ".join(iface.group(2).split())
            driver = iface.group(3)
            classes.append(f"{cls}:{desc}")
            drivers.append(driver)
        devices.append(
            {
                "product_id": product_match.group(1).lower(),
                "product": " ".join(name_match.group(1).split()) if name_match else "",
                "rev": rev_match.group(1) if rev_match else "",
                "speed_mbps": int(speed_match.group(1)) if speed_match else None,
                "interface_classes": sorted(set(classes)),
                "drivers": sorted(set(drivers)),
            }
        )
    return devices


def enhanced_host_usb_snapshot(run_dir: Path, log_path: Path, label: str) -> dict[str, Any]:
    lsusb_device = host_usb_command(run_dir, log_path, label, "lsusb_04e8_6860", ["lsusb", "-d", "04e8:6860", "-v"], 12.0)
    lsusb_tree = host_usb_command(run_dir, log_path, label, "lsusb_tree", ["lsusb", "-t"], 10.0)
    usb_devices = host_usb_command(run_dir, log_path, label, "usb_devices", ["usb-devices"], 10.0)
    tty_listing = host_usb_command(
        run_dir,
        log_path,
        label,
        "tty_listing",
        ["bash", "-lc", "ls -l /dev/ttyACM* /dev/serial/by-id/* /dev/serial/by-path/* 2>/dev/null || true"],
        10.0,
    )
    tty_udev = host_usb_command(
        run_dir,
        log_path,
        label,
        "tty_udev",
        [
            "bash",
            "-lc",
            "for n in /dev/ttyACM*; do "
            "[ -e \"$n\" ] || continue; "
            "echo \"tty=$n\"; "
            "udevadm info -q property -n \"$n\" 2>/dev/null | sort; "
            "done",
        ],
        10.0,
    )
    dmesg_tail = host_usb_command(
        run_dir,
        log_path,
        label,
        "dmesg_tail",
        ["bash", "-lc", "dmesg -T 2>/dev/null | tail -n 260 || true"],
        10.0,
    )
    samsung_devices = samsung_usb_devices_summary(usb_devices)
    samsung_product_ids = sorted({str(device.get("product_id", "")) for device in samsung_devices if device.get("product_id")})
    samsung_products = sorted({str(device.get("product", "")) for device in samsung_devices if device.get("product")})
    samsung_upload_download_present = any(
        str(device.get("product_id", "")).lower() == "685d"
        or str(device.get("product", "")).upper() in {"MSM_UPLOAD", "SAMSUNG USB"}
        for device in samsung_devices
    )
    summary = {
        "any_samsung_04e8_present": bool(samsung_devices),
        "samsung_product_ids": samsung_product_ids,
        "samsung_products": samsung_products,
        "samsung_usb_devices": samsung_devices,
        "samsung_upload_download_present": samsung_upload_download_present,
        "lsusb_04e8_6860_present": (
            "04e8:6860" in lsusb_device.lower()
            or ("idvendor" in lsusb_device.lower() and "04e8" in lsusb_device.lower()
                and "idproduct" in lsusb_device.lower() and "6860" in lsusb_device.lower())
        ),
        "lsusb_has_cdc_acm": "cdc abstract control model" in lsusb_device.lower() or "cdc acm" in lsusb_device.lower(),
        "lsusb_tree_has_cdc_acm": "cdc_acm" in lsusb_tree.lower(),
        "usb_devices_has_04e8_6860": "vend=04e8" in usb_devices.lower() and "prod=6860" in usb_devices.lower(),
        "tty_listing_has_acm": "/dev/ttyACM" in tty_listing,
        "tty_udev_has_04e8_6860": "ID_VENDOR_ID=04e8" in tty_udev and "ID_MODEL_ID=6860" in tty_udev,
        "dmesg_mentions_04e8_6860": "04e8" in dmesg_tail.lower() and "6860" in dmesg_tail.lower(),
    }
    append_log(log_path, f"{label}_host_usb_summary={json.dumps(summary, sort_keys=True)}")
    return summary


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
                "serial": "<redacted>" if props.get("ID_SERIAL_SHORT", "") else "",
                "driver": props.get("ID_USB_DRIVER", ""),
                "interface": props.get("ID_USB_INTERFACE_NUM", ""),
                "devlinks": redact_host_usb_text(props.get("DEVLINKS", "")),
            }
        )
    append_log(log_path, f"{label}_acm_devices={json.dumps(devices, sort_keys=True)}")
    return devices


def is_m34_s6_acm(device: dict[str, Any]) -> bool:
    return (
        str(device.get("vendor", "")).lower() == "04e8"
        and str(device.get("product", "")).lower() == "6860"
    )


def observe_park_survival(
    *,
    run_dir: Path,
    log_path: Path,
    odin: Path,
    observe_sec: int,
    snapshot_interval_sec: float,
) -> tuple[str, str | None]:
    host_snapshot(run_dir, log_path, "after_candidate_flash", odin)
    enhanced_host_usb_snapshot(run_dir, log_path, "after_candidate_flash")
    start = time.monotonic()
    deadline = start + observe_sec
    next_snapshot = start
    iteration = 0
    append_log(log_path, f"m34_s6_observe_start_utc={utc_now()}")
    append_log(log_path, f"m34_s6_observe_sec={observe_sec}")
    while time.monotonic() < deadline:
        now = time.monotonic()
        elapsed = now - start
        if now >= next_snapshot:
            iteration += 1
            label = f"m34_s6_park_observe_{iteration:03d}"
            append_log(log_path, f"{label}_elapsed_sec={elapsed:.3f}")
            host_snapshot(run_dir, log_path, label, odin)
            enhanced_host_usb_snapshot(run_dir, log_path, label)
            devices = odin_devices(odin, log_path, f"{label}-odin-extra")
            if len(devices) == 1:
                append_log(log_path, f"m34_s6_result=unexpected_odin_before_survival_window elapsed_sec={elapsed:.3f} device={devices[0]}")
                return "unexpected-odin-before-survival-window", devices[0]
            if len(devices) > 1:
                raise SystemExit(f"refusing ambiguous Odin devices during M34 S6 observation: {devices}")
            rows = adb_rows(log_path, f"{label}-adb-extra")
            usable = [row for row in rows if row[1] == "device"]
            if usable:
                append_log(log_path, f"m34_s6_result=unexpected_adb_before_survival_window elapsed_sec={elapsed:.3f} rows={usable}")
                return "unexpected-adb-before-survival-window", None
            for device in acm_devices(log_path, label):
                if is_m34_s6_acm(device):
                    append_log(log_path, f"m34_s6_acm_seen=1 elapsed_sec={elapsed:.3f} device={json.dumps(device, sort_keys=True)}")
                    return "acm-seen-manual-download-required", None
            next_snapshot = now + snapshot_interval_sec
        time.sleep(0.5)
    append_log(log_path, "m34_s6_survival_window_pass=1")
    append_log(log_path, "m34_s6_result=survived-observation-window-manual-download-required")
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
        append_log(log_path, f"m34_s6_{label}_magisk_rollback_failed_attempting_stock_fallback=1")
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
        append_log(log_path, f"m34_s6_{label}_boot_restore_hash_check=skipped rollback_target=stock")
    record_timeline_event(run_dir, "rollback_boot_ready")
    record_timeline_event(run_dir, f"{label}_rollback_boot_ready")
    marker_found = collect_android_pstore(run_dir, log_path, f"post_m34_s6_{label}_rollback", android, marker=EXPECTED_M34_MARKER)
    append_log(log_path, f"m34_s6_{label}_retained_marker_found={int(marker_found)}")
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
    devices = odin_devices(odin, log_path, "m34-s6-rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"M34 S6 rollback requires exactly one Odin device, got {devices}")
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
        raise SystemExit("--observe-sec must be at least 60 for the M34 S6 stock-speed softdep discriminator")
    if args.snapshot_interval_sec < 1.0:
        raise SystemExit("--snapshot-interval-sec must be at least 1.0")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m34_s6_stock_softdep_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M34 S6 stock-speed softdep live gate ===")
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
        print(f"offline-check ok: M34 S6 candidate and rollback APs verified; no device action; log={log_path}")
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
        print(f"M34 S6 rollback-from-download completed rc={rc}; log={log_path}")
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
    enhanced_host_usb_snapshot(run_dir, log_path, "dryrun_current")

    if not args.live:
        print(
            "dry-run ok: M34 S6 candidate, rollback APs, AGENTS exception, Android stability, "
            f"and current boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    print(
        "M34 S6 live gate starting. This candidate should park after stock-speed QMP/EUD/ucsi setup "
        f"with UDC=a600000.dwc3; do not press keys during the {args.observe_sec}s observation window. "
        "Manual Download is only for rollback after the helper asks.",
        flush=True,
    )
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print("download mode did not appear for M34 S6 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m34_ap, odin_device, log_path, "candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        print(f"M34 S6 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        append_log(log_path, "m34_s6_result=no-proof-original-download-never-disconnected")
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
    print(f"M34 S6 candidate flashed. Observing for {args.observe_sec}s survival window.", flush=True)
    result, rollback_device = observe_park_survival(
        run_dir=run_dir,
        log_path=log_path,
        odin=odin,
        observe_sec=args.observe_sec,
        snapshot_interval_sec=args.snapshot_interval_sec,
    )
    successful_result = result in {
        "survived-observation-window-manual-download-required",
        "acm-seen-manual-download-required",
    }
    if not successful_result:
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            print(
                f"M34 S6 stopped before survival proof ({result}). If the device is not in Android, "
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
        f"M34 S6 result={result}. Enter Download mode manually for rollback now; "
        f"waiting up to {args.manual_download_wait_sec}s.",
        flush=True,
    )
    rollback_device = wait_for_odin(odin, log_path, "manual-rollback-wait", args.manual_download_wait_sec)
    if rollback_device is None:
        record_timeline_event(run_dir, "live_session_end")
        print(
            f"M34 S6 survival window passed, but manual Download mode did not appear. "
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
    print(f"M34 S6 live gate completed rc={rc}; result={result}; log={log_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
