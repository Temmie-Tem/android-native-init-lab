#!/usr/bin/env python3
"""Guarded S22+ M34 S8B1 download-beacon state-probe live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

M34 S8B1 keeps the S7A2 module recipe fixed, skips downstream configfs/UDC
work, reads one predicate after module load, then uses reboot(download) as a
1-bit host-visible state probe:

    /sys/class/typec/port0 exists OR /sys/bus/i2c/devices/57-0066 exists

Predicate true means HIT and should re-enter Download mode. Predicate false
parks, requiring manual Download rollback.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_m34_runtime_gadget_split import (
    M34_S7A_RISK_MODULES,
    M34_S7A_SESSION_PRODUCER_TARGETS,
    M34_S7A2_EXPECTED_NEW_MODULES,
    M34_S7A2_I2C_GENI_TRANSPORT_TARGETS,
)
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
from s22plus_m34_s7a2_geni_i2c_live_gate import (
    EXPECTED_MODULES,
    M34_S7A2_I2C_ORDER_ACTUAL,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability


LIVE_ACK_TOKEN = "S22PLUS-M34-S8B1-BEACON-PROBE-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M34-S8B1-BEACON-PROBE-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_STAGE = "S8B1"
EXPECTED_M34_MARKER = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S8B1"
EXPECTED_M34_AP_SHA256 = "0bf313cdf24a5f5babc3d0073a1e90686f1b734b6dafdfa548154ef3eac6c2c8"
EXPECTED_M34_BOOT_SHA256 = "4e599087f242fdf2ae6bee1465e0725b60057bad893b665a178bcf87b88b9a20"
EXPECTED_M34_INIT_SHA256 = "a1cbc9828a24a7e302bd569de93b4f41e2ceb159130ea373d2ea9c9572f5a20d"
EXPECTED_M34_MODULE_LIST_SHA256 = "c0c35e02fe61a3f6c18c221a9ae2cc1a54aafd38374117fa954dbfa675700998"
EXPECTED_M34_TEMPLATE_SOURCE_SHA256 = "35978182a80e0502a0aec89ec66e35ca378ebbb3b7c58c573ad0e8ff55cc248d"
EXPECTED_M34_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M34_BASE_BOOT_SHA256 = EXPECTED_BASE_BOOT_SHA256
EXPECTED_MODULE_ENTRY = "s22plus_m34_s8b1_runtime_gadget_split.modules"
EXPECTED_STOCK_RECIPE_REPORT = "docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md"
EXPECTED_PROBE = "typec_port_or_i2c_device"
EXPECTED_PROBE_PATHS = ["/sys/class/typec/port0", "/sys/bus/i2c/devices/57-0066"]
M34_S8B1_RISK_MODULES = M34_S7A_RISK_MODULES

DEFAULT_M34_AP = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_8/S8B1/odin4/AP.tar.md5")
DEFAULT_M34_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_8/manifest.json")


@dataclass(frozen=True)
class RollbackResult:
    rc: int
    android_serial: str | None
    rollback_target: str
    rollback_device: str


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m34_s8b1_beacon_probe_live_gate_{utc_stamp()}")
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
        "S22+ M34 S8B1 download-beacon state-probe native-init boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py",
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
        "S8B1 keeps the S7A2 module recipe fixed",
        "GENI I2C transport closure",
        "stock max77705 PDIC altmode session-producer closure",
        "module_count=86",
        "session_producer_parity=1",
        "max77705_session=1",
        "geni_i2c_transport=1",
        "i2c_msm_geni=1",
        "gpi_dma=1",
        "msm_geni_se=1",
        "typec_readback=0",
        "role_write_discriminator=0",
        "configfs_gadget=0",
        "udc_bind=0",
        "ssusb_mode_peripheral=0",
        "functionfs=0",
        "stock_composite=0",
        f"s8_beacon_probe={EXPECTED_PROBE}",
        "predicate=typec_port_or_i2c_device",
        "/sys/class/typec/port0",
        "/sys/bus/i2c/devices/57-0066",
        "reboot_request=download",
        "download_beacon=1",
        "true_action=reboot_download",
        "false_action=park",
        "download-beacon-hit",
        "download-beacon-miss-parked-manual-download-required",
        "host-visible HIT = new Odin Download endpoint appears",
        "MISS = no new Odin endpoint during bounded observation; manual Download rollback required",
        "no configfs gadget setup",
        "no UDC bind",
        "no TypeC role write",
        "no ssusb role write",
        "no FunctionFS",
        "no stock composite",
        "no Android/Magisk handoff",
        "no persistent partition mount",
        "no block write",
        "no charge-current write",
        "no OTG/VBUS boost write",
        "no regulator/GDSC/GPIO/raw PMIC write",
        "manual Download rollback is recovery-only",
        "PMIC/RDX abnormal reset before the observation window is FAIL",
        "sec_debug_region.ko present due stock charger dependency",
        "requires_s7a_specific_live_risk_review",
        *M34_S7A2_I2C_GENI_TRANSPORT_TARGETS,
        *M34_S7A_SESSION_PRODUCER_TARGETS,
        *M34_S7A2_EXPECTED_NEW_MODULES,
        *M34_S8B1_RISK_MODULES,
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
    return f"""   **DRAFT ONLY - Narrow operator-authorized exception (2026-07-09, S22+ M34 S8B1 download-beacon state-probe boot-only live gate):**
   This draft is not active authorization unless the operator explicitly approves
   it and the block is inserted into `AGENTS.md`. After approval, Codex may run
   one bounded attended boot-partition-only M34 S8B1 live gate on the Samsung S22+
   `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py`.
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

   The candidate is limited to freestanding direct PID1 M34 S8B1 behavior.
   S8B1 keeps the S7A2 module recipe fixed: GENI I2C transport closure,
   stock max77705 PDIC altmode session-producer closure, `module_count=86`,
   `session_producer_parity=1`, `max77705_session=1`,
   `geni_i2c_transport=1`, `i2c_msm_geni=1`, `gpi_dma=1`,
   `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `sec_debug_region.ko present due stock charger dependency`, and
   `requires_s7a_specific_live_risk_review`.

   S8B1 intentionally performs no downstream USB gadget work:
   `configfs_gadget=0`, `udc_bind=0`, `ssusb_mode_peripheral=0`,
   `typec_readback=0`, `role_write_discriminator=0`, no configfs gadget setup,
   no UDC bind, no TypeC role write, no ssusb role write, no FunctionFS, and
   no stock composite. Its only observation is
   `s8_beacon_probe={EXPECTED_PROBE}` / `predicate=typec_port_or_i2c_device`,
   reading `/sys/class/typec/port0` and `/sys/bus/i2c/devices/57-0066`.
   Predicate true requests `reboot_request=download` with `download_beacon=1`
   and records `true_action=reboot_download`; predicate false records
   `false_action=park` and parks. The host-visible HIT is that a new Odin
   Download endpoint appears after the original Download endpoint disconnects.
   MISS means no new Odin endpoint during bounded observation; manual Download
   rollback is required and is recovery-only.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S1/S2/S3/S4/S5/S6/S7A/S7A2 repeat,
   B2/B3/B4, descriptor/composition pivots, FunctionFS/conn_gadget parity,
   display/distro candidates, kernel rebuilds, RDX PC dump retrieval, or any
   non-boot partition action.

   Required policy marker coverage:
{marker_lines}
"""


def agents_exception_active_template() -> str:
    text = agents_exception_draft()
    text = text.replace(
        "**DRAFT ONLY - Narrow operator-authorized exception",
        "**Narrow operator-authorized exception",
        1,
    )
    text = text.replace(
        "   This draft is not active authorization unless the operator explicitly approves\n"
        "   it and the block is inserted into `AGENTS.md`. After approval, Codex may run\n",
        "   Codex may run\n",
        1,
    )
    return text


def verify_agents_exception(root: Path, log_path: Path) -> None:
    agents = (root / "AGENTS.md").read_text(encoding="utf-8")
    draft_only = has_draft_only_m34_exception(agents)
    append_log(log_path, f"agents_exception_draft_only_present={int(draft_only)}")
    if draft_only:
        raise SystemExit("AGENTS.md contains draft-only M34 S8B1 authorization text; refuse to treat draft as active live auth")
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"AGENTS.md missing M34 S8B1 beacon-probe authorization markers: {missing}")


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
    append_log(log_path, f"m34_manifest_path={path}")
    append_log(log_path, f"m34_s8b1_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m34_manifest_safety={json.dumps(safety, sort_keys=True)}")
    append_log(log_path, f"m34_manifest_matrix={json.dumps(matrix, sort_keys=True)}")
    append_log(log_path, f"m34_s8b1_manifest_runtime_steps={json.dumps(runtime_steps, sort_keys=True)}")
    append_log(log_path, f"m34_s8b1_manifest_closure={json.dumps(closure, sort_keys=True)}")

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
    if matrix.get("host_build_order") != ["S1", "S2", "S3", "S4", "S5", "S6", "S7A", "S7A2", "S8B1"]:
        raise SystemExit(f"M34 host-build order mismatch: {matrix.get('host_build_order')!r}")
    if matrix.get("next_host_only_candidate") != "S8B1":
        raise SystemExit(f"M34 next host-only candidate mismatch: {matrix.get('next_host_only_candidate')!r}")
    if matrix.get("s8b1_download_beacon_probe") != EXPECTED_PROBE:
        raise SystemExit(f"M34 S8B1 probe mismatch: {matrix.get('s8b1_download_beacon_probe')!r}")
    if matrix.get("s8b1_true_action") != "reboot(download)" or matrix.get("s8b1_false_action") != "park":
        raise SystemExit("M34 S8B1 true/false action mismatch")
    if matrix.get("s8b1_probe_paths") != EXPECTED_PROBE_PATHS:
        raise SystemExit(f"M34 S8B1 probe paths mismatch: {matrix.get('s8b1_probe_paths')!r}")
    if matrix.get("s8b1_keeps_s7a2_module_recipe") is not True:
        raise SystemExit("M34 S8B1 matrix does not prove S7A2 module recipe reuse")
    if matrix.get("s8b1_skips_downstream_configfs_and_udc_to_isolate_probe") is not True:
        raise SystemExit("M34 S8B1 matrix does not prove downstream USB isolation")

    if stage.get("stage_number") != 9:
        raise SystemExit(f"M34 S8B1 stage number mismatch: {stage.get('stage_number')!r}")
    expected_steps = {
        "configfs_gadget": False,
        "udc_none": False,
        "max_speed_high_speed": False,
        "usb_role_force": False,
        "ssusb_speed_high_speed": False,
        "ssusb_mode_peripheral": False,
        "udc_bind": False,
        "soft_connect": False,
        "stock_softdep_parity": True,
        "qmp_module_included": True,
        "eud_module_included": True,
        "ucsi_glink_included": True,
        "session_producer_parity": True,
        "max77705_session_modules_included": True,
        "typec_readback_markers": False,
        "geni_i2c_transport_parity": True,
        "typec_role_write_discriminator": False,
        "beacon_probe": EXPECTED_PROBE,
    }
    if runtime_steps != expected_steps:
        raise SystemExit(f"M34 S8B1 runtime steps mismatch: {runtime_steps!r}")

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
            raise SystemExit(f"M34 S8B1 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if stage.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit(f"M34 S8B1 manifest tar members mismatch: {stage.get('tar_members')!r}")

    required_safety = {
        "boot_only": True,
        "host_only_build": True,
        "live_flash_authorized": False,
        "requires_new_sha_pinned_agents_exception_before_flash": True,
        "base_is_known_booting_magisk_boot": True,
        "mkbootimg_from_scratch": False,
        "no_android_or_magisk_handoff": True,
        "auto_reboot": "download-if-probe-true",
        "intended_reboot_syscall": True,
        "reboot_request": "download-if-probe-true",
        "persistent_partition_mount": False,
        "block_device_writes": False,
        "module_binary_injection": False,
        "stage_s8b1_starts_from_s7a2_module_recipe": True,
        "stage_s8b1_beacon_probe": EXPECTED_PROBE,
        "stage_s8b1_true_reboot_download_false_park": True,
        "stage_s8b1_no_configfs_udc_or_role_write": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M34 manifest safety {key} mismatch: {safety.get(key)!r} != {expected!r}")

    if closure.get("modules") != list(EXPECTED_MODULES):
        raise SystemExit(f"M34 S8B1 module closure mismatch: {closure.get('modules')!r}")
    if closure.get("module_count") != len(EXPECTED_MODULES):
        raise SystemExit(f"M34 S8B1 module closure count mismatch: {closure.get('module_count')!r}")
    if closure.get("module_sha256") != EXPECTED_M34_MODULE_LIST_SHA256:
        raise SystemExit(f"M34 S8B1 module list SHA mismatch: {closure.get('module_sha256')!r}")
    if closure.get("geni_i2c_transport_targets") != M34_S7A2_I2C_GENI_TRANSPORT_TARGETS:
        raise SystemExit(f"M34 S8B1 closure GENI I2C targets mismatch: {closure.get('geni_i2c_transport_targets')!r}")
    if closure.get("geni_i2c_transport_order_actual") != M34_S7A2_I2C_ORDER_ACTUAL:
        raise SystemExit(f"M34 S8B1 closure GENI I2C order mismatch: {closure.get('geni_i2c_transport_order_actual')!r}")
    modules = closure.get("modules", [])
    if modules.index("i2c-msm-geni.ko") >= modules.index("pdic_max77705.ko"):
        raise SystemExit("M34 S8B1 module order must load i2c-msm-geni.ko before pdic_max77705.ko")
    if closure.get("session_producer_targets") != M34_S7A_SESSION_PRODUCER_TARGETS:
        raise SystemExit(f"M34 S8B1 session-producer targets mismatch: {closure.get('session_producer_targets')!r}")
    if closure.get("additional_new_modules") != M34_S7A2_EXPECTED_NEW_MODULES:
        raise SystemExit(f"M34 S8B1 additional module list mismatch: {closure.get('additional_new_modules')!r}")
    if closure.get("risk_modules") != M34_S8B1_RISK_MODULES:
        raise SystemExit(f"M34 S8B1 risk module list mismatch: {closure.get('risk_modules')!r}")
    if closure.get("contains_sec_debug_region") is not True:
        raise SystemExit("M34 S8B1 closure does not explicitly carry sec_debug_region")
    if closure.get("requires_live_risk_review") is not True:
        raise SystemExit("M34 S8B1 closure does not require live risk review")

    if ramdisk.get("replaced_entry") != "init":
        raise SystemExit("M34 S8B1 manifest did not replace /init")
    if ramdisk.get("added_subset_entry") != EXPECTED_MODULE_ENTRY:
        raise SystemExit(f"M34 S8B1 module-list ramdisk entry mismatch: {ramdisk.get('added_subset_entry')!r}")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M34 S8B1 must not inject module binaries into boot ramdisk")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M34_MARKER,
        "version=0.8",
        "module_list=dep_complete_runtime_gadget_split",
        "stage=S8B1",
        "runtime_step=S8B1",
        "module_count=86",
        "phase=modules_load_done",
        "phase=park_enter",
        "reboot_request=download",
        "download_beacon=1",
        "configfs_gadget=0",
        "udc_bind=0",
        "ssusb_mode_peripheral=0",
        "typec_readback=0",
        "geni_i2c_transport=1",
        "role_write_discriminator=0",
        f"s8_beacon_probe={EXPECTED_PROBE}",
        "phase=s8_b1_probe",
        "predicate=typec_port_or_i2c_device",
        "true_action=reboot_download",
        "false_action=park",
        "/sys/class/typec/port0",
        "/sys/bus/i2c/devices/57-0066",
        "download",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M34 S8B1 required string missing from manifest: {required}")
    for forbidden in [
        "phase=configfs_done",
        "/config/usb_gadget/g1/functions/ss_acm.0",
        "/config/usb_gadget/g1/UDC",
        "/sys/class/udc",
        "a600000.dwc3",
        "phase=udc_bind",
        "phase=typec_role_write",
        "/sys/class/typec/port0/data_role",
        "/sys/class/typec/port0/power_role",
        "/sys/devices/platform/soc/a600000.ssusb/mode",
    ]:
        if forbidden in required_strings:
            raise SystemExit(f"M34 S8B1 manifest unexpectedly requires forbidden string: {forbidden}")

    objdump_path = path.parent / EXPECTED_STAGE / str(init_info.get("objdump_path", ""))
    if not objdump_path.is_file():
        raise SystemExit(f"M34 S8B1 objdump missing: {objdump_path}")
    objdump = objdump_path.read_text(encoding="utf-8", errors="replace")
    if not any("mov" in line and "#0x111" in line and "// #273" in line for line in objdump.splitlines()):
        raise SystemExit("M34 S8B1 /init does not load arm64 __NR_finit_module (273)")
    if not any("mov" in line and "#0x8e" in line and "// #142" in line for line in objdump.splitlines()):
        raise SystemExit("M34 S8B1 /init does not load arm64 __NR_reboot (142)")


def verify_m34_artifacts(
    *,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> None:
    verify_ap(m34_ap, EXPECTED_M34_AP_SHA256, "m34_s8b1_candidate", log_path)
    verify_m34_manifest(m34_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)


def run_android_readonly_preflight(
    *,
    run_dir: Path,
    log_path: Path,
    odin: Path,
    serial: str | None,
    stability_samples: int,
    stability_interval_sec: float,
    snapshot_label: str,
    agents_exception_checked: bool,
) -> str:
    selected_serial = require_current_android(log_path, serial)
    verify_android_stability(
        log_path,
        selected_serial,
        stability_samples,
        stability_interval_sec,
    )
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_M34_BASE_BOOT_SHA256, "current")
    host_snapshot(run_dir, log_path, snapshot_label, odin)
    append_log(
        log_path,
        "android_readonly_preflight=ok device_action=0 "
        f"agents_exception_checked={int(agents_exception_checked)} "
        "android_checked=1 current_boot_hash_checked=1",
    )
    return selected_serial


def write_result_summary(
    run_dir: Path,
    log_path: Path,
    *,
    result: str,
    rc: int,
    rollback_target: str,
    rollback_device: str | None = None,
    android_serial: str | None = None,
    note: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "schema": "s22plus_m34_s8b1_result_v1",
        "timestamp_utc": utc_now(),
        "target": EXPECTED_TARGET,
        "stage": EXPECTED_STAGE,
        "result": result,
        "rc": rc,
        "rollback_target": rollback_target,
        "candidate_ap_sha256": EXPECTED_M34_AP_SHA256,
        "candidate_boot_sha256": EXPECTED_M34_BOOT_SHA256,
        "candidate_init_sha256": EXPECTED_M34_INIT_SHA256,
        "base_boot_sha256": EXPECTED_M34_BASE_BOOT_SHA256,
    }
    if rollback_device is not None:
        payload["rollback_device"] = rollback_device
    if android_serial is not None:
        payload["android_serial"] = android_serial
    if note is not None:
        payload["note"] = note
    path = run_dir / "result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"result_json={path}")
    append_log(log_path, f"result_summary={json.dumps(payload, sort_keys=True)}")
    write_result_analysis(run_dir, log_path, path)


def write_result_analysis(run_dir: Path, log_path: Path, result_json: Path) -> None:
    try:
        from analyze_s22plus_m34_s8b1_result import classify_result, load_json

        timeline_json = run_dir / "timeline.json"
        result_payload = load_json(result_json)
        timeline_payload = load_json(timeline_json) if timeline_json.is_file() else None
        analysis = classify_result(result_payload, timeline_payload)
        analysis["result_json"] = str(result_json)
        analysis["timeline_json"] = str(timeline_json) if timeline_json.is_file() else None
        analysis_path = run_dir / "s22plus_m34_s8b1_result_analysis.json"
        analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        append_log(log_path, f"result_analysis_json={analysis_path}")
        append_log(
            log_path,
            "result_analysis="
            f"decision={analysis.get('decision')} "
            f"ok_to_advance={int(bool(analysis.get('ok_to_advance')))} "
            f"ok_to_live_next_stage={int(bool(analysis.get('ok_to_live_next_stage')))}",
        )
    except Exception as exc:  # pragma: no cover - rollback/result emission must remain non-fatal.
        append_log(log_path, f"result_analysis_error={type(exc).__name__}: {exc}")


def shell_cmd(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def optional_serial_args(serial: str | None) -> list[str]:
    return ["--serial", serial] if serial else []


def path_args(args: argparse.Namespace) -> list[str]:
    return [
        "--m34-ap",
        str(args.m34_ap),
        "--m34-manifest",
        str(args.m34_manifest),
        "--magisk-rollback-ap",
        str(args.magisk_rollback_ap),
        "--stock-rollback-ap",
        str(args.stock_rollback_ap),
        "--odin",
        str(args.odin),
    ]


def runbook_result_json(args: argparse.Namespace) -> str:
    return str(args.run_dir / "result.json") if args.run_dir is not None else "<run-dir>/result.json"


def runbook_phase_run_dir(run_dir: Path | None, phase: str) -> Path | None:
    if run_dir is None:
        return None
    if phase == "live":
        return run_dir
    return Path(f"{run_dir}_{phase}")


def runbook_phase_run_dir_args(run_dir: Path | None, phase: str) -> list[str]:
    phase_run_dir = runbook_phase_run_dir(run_dir, phase)
    return ["--run-dir", str(phase_run_dir)] if phase_run_dir is not None else []


def runbook_phase_run_dirs(run_dir: Path) -> dict[str, str]:
    phases = ("preflight", "template", "dryrun", "live", "rollback")
    return {phase: str(runbook_phase_run_dir(run_dir, phase)) for phase in phases}


def planned_rollback_result_json(live_run_dir: Path) -> Path:
    rollback_dir = runbook_phase_run_dir(live_run_dir, "rollback")
    if rollback_dir is None:
        raise AssertionError("live_run_dir unexpectedly resolved to None")
    return rollback_dir / "result.json"


def prelive_packet_notes(live_run_dir: Path) -> list[str]:
    return [
        "The live command handles HIT rollback and also handles MISS manual rollback internally if Download appears before --manual-download-wait-sec expires.",
        "Run the rollback-from-download command only if the live command exits after MISS without rollback, or if the device is placed in Download mode later.",
        f"Analyze {live_run_dir / 'result.json'} for B1 proof; {planned_rollback_result_json(live_run_dir)} is cleanup-only evidence if the fallback rollback command is needed.",
    ]


def planned_live_run_dir(packet_run_dir: Path) -> Path:
    base = Path(f"{packet_run_dir}_live")
    if not base.exists():
        return base
    for suffix in range(100):
        candidate = Path(f"{base}_{suffix:02d}")
        if not candidate.exists():
            return candidate
    raise SystemExit(f"could not allocate planned live run directory near {packet_run_dir}")


def resolved_runbook_args(
    args: argparse.Namespace,
    *,
    run_dir: Path,
    odin: Path,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
) -> argparse.Namespace:
    packet_args = argparse.Namespace(**vars(args))
    packet_args.run_dir = run_dir
    packet_args.odin = odin
    packet_args.m34_ap = m34_ap
    packet_args.m34_manifest = m34_manifest
    packet_args.magisk_rollback_ap = magisk_rollback_ap
    packet_args.stock_rollback_ap = stock_rollback_ap
    return packet_args


def live_runbook(args: argparse.Namespace) -> str:
    helper = "workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py"
    analyzer = "workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py"
    base = ["PYTHONPYCACHEPREFIX=/tmp/a90_pycache", "python3", helper]
    analyze_base = ["PYTHONPYCACHEPREFIX=/tmp/a90_pycache", "python3", analyzer]
    common_paths = path_args(args)
    result_json = runbook_result_json(args)
    common_android = [
        "--android-stability-samples",
        str(args.android_stability_samples),
        "--android-stability-interval-sec",
        str(args.android_stability_interval_sec),
        *optional_serial_args(args.serial),
    ]
    live_args = [
        "--observe-sec",
        str(args.observe_sec),
        "--snapshot-interval-sec",
        str(args.snapshot_interval_sec),
        "--post-flash-disconnect-wait-sec",
        str(args.post_flash_disconnect_wait_sec),
        "--manual-download-wait-sec",
        str(args.manual_download_wait_sec),
        "--odin-wait-sec",
        str(args.odin_wait_sec),
        "--android-wait-sec",
        str(args.android_wait_sec),
        "--rollback-target",
        args.rollback_target,
    ]
    lines = [
        "# S22+ M34 S8B1 live runbook (no command below inserts AGENTS.md by itself)",
        "# 1. No-write readiness check",
        shell_cmd([*base, "--readonly-preflight", *common_paths, *runbook_phase_run_dir_args(args.run_dir, "preflight"), *common_android]),
        "",
        "# 2. Print the active AGENTS.md exception template, then insert it manually after review",
        shell_cmd([*base, "--print-agents-exception-active-template", *common_paths, *runbook_phase_run_dir_args(args.run_dir, "template")]),
        "",
        "# 3. After AGENTS.md has the active exception, run the default dry-run gate",
        shell_cmd([*base, *common_paths, *runbook_phase_run_dir_args(args.run_dir, "dryrun"), *common_android]),
        "",
        "# 4. Live gate with explicit ack token",
        "#    This command handles HIT rollback. On MISS it also waits for manual Download",
        "#    and performs rollback inside the live run directory if Download appears in time.",
        shell_cmd([*base, "--live", "--ack", LIVE_ACK_TOKEN, *common_paths, *runbook_phase_run_dir_args(args.run_dir, "live"), *common_android, *live_args]),
        "",
        "# 5. Fallback only: run this if step 4 exits after MISS without rollback,",
        "#    or if the device is placed in Download mode after the bounded live wait.",
        shell_cmd(
            [
                *base,
                "--rollback-from-download",
                "--ack",
                ROLLBACK_ACK_TOKEN,
                *common_paths,
                *runbook_phase_run_dir_args(args.run_dir, "rollback"),
                "--android-wait-sec",
                str(args.android_wait_sec),
                "--rollback-target",
                args.rollback_target,
            ]
        ),
        "",
        "# 6. Interpret the live run directory for B1 proof",
        "#    If step 5 was needed, its result directory is cleanup evidence, not B1 proof.",
        shell_cmd([*analyze_base, result_json, "--write-report"]),
        shell_cmd([*analyze_base, result_json, "--require-advance"]),
        shell_cmd([*analyze_base, result_json, "--require-live-next-stage"]),
        "",
    ]
    return "\n".join(lines)


def write_prelive_packet(
    *,
    run_dir: Path,
    log_path: Path,
    args: argparse.Namespace,
    selected_serial: str,
    odin: Path,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
) -> Path:
    live_run_dir = planned_live_run_dir(run_dir)
    packet_args = resolved_runbook_args(
        args,
        run_dir=live_run_dir,
        odin=odin,
        m34_ap=m34_ap,
        m34_manifest=m34_manifest,
        magisk_rollback_ap=magisk_rollback_ap,
        stock_rollback_ap=stock_rollback_ap,
    )
    runbook = live_runbook(packet_args)
    active_template = agents_exception_active_template()
    missing = missing_policy_markers(active_template)
    if missing:
        raise SystemExit(f"internal active template is missing policy markers: {missing}")
    if has_draft_only_m34_exception(active_template):
        raise SystemExit("internal active template still looks draft-only")

    runbook_path = run_dir / "s22plus_m34_s8b1_live_runbook.txt"
    active_template_path = run_dir / "s22plus_m34_s8b1_active_exception_template.txt"
    packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
    runbook_path.write_text(runbook, encoding="utf-8")
    active_template_path.write_text(active_template, encoding="utf-8")
    payload = {
        "schema": "s22plus_m34_s8b1_prelive_packet_v1",
        "generated_utc": utc_now(),
        "target": EXPECTED_TARGET,
        "stage": "S8B1",
        "device_action": False,
        "agents_exception_inserted": False,
        "agents_exception_checked": False,
        "android_checked": True,
        "selected_serial": selected_serial,
        "candidate_ap_sha256": EXPECTED_M34_AP_SHA256,
        "candidate_boot_sha256": EXPECTED_M34_BOOT_SHA256,
        "candidate_init_sha256": EXPECTED_M34_INIT_SHA256,
        "base_boot_sha256": EXPECTED_M34_BASE_BOOT_SHA256,
        "live_ack_token": LIVE_ACK_TOKEN,
        "rollback_ack_token": ROLLBACK_ACK_TOKEN,
        "m34_ap": str(m34_ap),
        "m34_manifest": str(m34_manifest),
        "magisk_rollback_ap": str(magisk_rollback_ap),
        "stock_rollback_ap": str(stock_rollback_ap),
        "odin": str(odin),
        "log": str(log_path),
        "packet_run_dir": str(run_dir),
        "planned_live_run_dir": str(live_run_dir),
        "planned_phase_run_dirs": runbook_phase_run_dirs(live_run_dir),
        "planned_result_json": str(live_run_dir / "result.json"),
        "planned_rollback_result_json": str(planned_rollback_result_json(live_run_dir)),
        "runbook_notes": prelive_packet_notes(live_run_dir),
        "runbook": str(runbook_path),
        "active_exception_template": str(active_template_path),
    }
    packet_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"prelive_packet_json={packet_path}")
    append_log(log_path, f"prelive_packet_planned_live_run_dir={live_run_dir}")
    append_log(log_path, f"prelive_packet_runbook={runbook_path}")
    append_log(log_path, f"prelive_packet_active_exception_template={active_template_path}")
    append_log(log_path, "prelive_packet=ok device_action=0 agents_exception_checked=0 android_checked=1")
    return packet_path


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


def observe_download_beacon(
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
    append_log(log_path, f"m34_s8b1_observe_start_utc={utc_now()}")
    append_log(log_path, f"m34_s8b1_observe_sec={observe_sec}")
    while time.monotonic() < deadline:
        now = time.monotonic()
        elapsed = now - start
        if now >= next_snapshot:
            iteration += 1
            label = f"m34_s8b1_beacon_observe_{iteration:03d}"
            append_log(log_path, f"{label}_elapsed_sec={elapsed:.3f}")
            host_snapshot(run_dir, log_path, label, odin)
            devices = odin_devices(odin, log_path, f"{label}-odin-extra")
            if len(devices) == 1:
                append_log(log_path, f"m34_s8b1_result=download-beacon-hit elapsed_sec={elapsed:.3f} device={devices[0]}")
                return "download-beacon-hit", devices[0]
            if len(devices) > 1:
                raise SystemExit(f"refusing ambiguous Odin devices during M34 S8B1 observation: {devices}")
            rows = adb_rows(log_path, f"{label}-adb-extra")
            usable = [row for row in rows if row[1] == "device"]
            if usable:
                append_log(log_path, f"m34_s8b1_result=unexpected-adb-before-rollback elapsed_sec={elapsed:.3f} rows={usable}")
                return "unexpected-adb-before-rollback", None
            next_snapshot = now + snapshot_interval_sec
        time.sleep(0.5)
    append_log(log_path, "m34_s8b1_result=download-beacon-miss-parked-manual-download-required")
    return "download-beacon-miss-parked-manual-download-required", None


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
) -> RollbackResult:
    actual_rollback_target = rollback_target
    actual_rollback_device = odin_device
    record_timeline_event(run_dir, f"{label}_rollback_flash_start")
    record_timeline_event(run_dir, "rollback_flash_start")
    rollback_rc = flash_ap(odin, rollback_ap, odin_device, log_path, f"{label}_{rollback_target}_boot_rollback")
    record_timeline_event(run_dir, f"{label}_rollback_flash_done")
    if rollback_rc != 0 and rollback_target == ROLLBACK_MAGISK:
        append_log(log_path, f"m34_s8b1_{label}_magisk_rollback_failed_attempting_stock_fallback=1")
        fallback_device = wait_for_odin(odin, log_path, f"{label}-stock-fallback-wait", 30)
        if fallback_device:
            record_timeline_event(run_dir, f"{label}_stock_fallback_flash_start")
            rollback_rc = flash_ap(odin, stock_boot_fallback_ap, fallback_device, log_path, f"{label}_stock_boot_fallback")
            record_timeline_event(run_dir, f"{label}_stock_fallback_flash_done")
            actual_rollback_target = ROLLBACK_STOCK
            actual_rollback_device = fallback_device
    record_timeline_event(run_dir, "rollback_flash_done")
    if rollback_rc != 0:
        return RollbackResult(
            rc=rollback_rc or 5,
            android_serial=None,
            rollback_target=actual_rollback_target,
            rollback_device=actual_rollback_device,
        )

    android = poll_android(log_path, android_wait_sec, expect_root=actual_rollback_target == ROLLBACK_MAGISK)
    if android is None:
        return RollbackResult(
            rc=6,
            android_serial=None,
            rollback_target=actual_rollback_target,
            rollback_device=actual_rollback_device,
        )
    if actual_rollback_target == ROLLBACK_MAGISK:
        verify_partition_hash(log_path, android, "boot", EXPECTED_M34_BASE_BOOT_SHA256, f"{label}_boot_restore")
    else:
        append_log(log_path, f"m34_s8b1_{label}_boot_restore_hash_check=skipped rollback_target={actual_rollback_target}")
    record_timeline_event(run_dir, "rollback_boot_ready")
    record_timeline_event(run_dir, f"{label}_rollback_boot_ready")
    marker_found = collect_android_pstore(run_dir, log_path, f"post_m34_s8b1_{label}_rollback", android, marker=EXPECTED_M34_MARKER)
    append_log(log_path, f"m34_s8b1_{label}_retained_marker_found={int(marker_found)}")
    return RollbackResult(
        rc=0,
        android_serial=android,
        rollback_target=actual_rollback_target,
        rollback_device=actual_rollback_device,
    )


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
    devices = odin_devices(odin, log_path, "m34-s8b1-rollback-only")
    if len(devices) != 1:
        raise SystemExit(f"M34 S8B1 rollback requires exactly one Odin device, got {devices}")
    rollback = rollback_boot_only_from_download(
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
    write_result_summary(
        run_dir,
        log_path,
        result="rollback-from-download-completed",
        rc=rollback.rc,
        rollback_target=rollback.rollback_target,
        rollback_device=rollback.rollback_device,
        android_serial=rollback.android_serial,
    )
    return rollback.rc


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
    parser.add_argument("--readonly-preflight", action="store_true")
    parser.add_argument("--prelive-packet", action="store_true")
    parser.add_argument("--print-live-runbook", action="store_true")
    parser.add_argument("--print-agents-exception-draft", action="store_true")
    parser.add_argument("--print-agents-exception-active-template", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.readonly_preflight,
            args.prelive_packet,
            args.print_live_runbook,
            args.print_agents_exception_draft,
            args.print_agents_exception_active_template,
            args.live,
            args.rollback_from_download,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --readonly-preflight, --print-agents-exception-draft, "
            "--print-agents-exception-active-template, --print-live-runbook, "
            "--prelive-packet, --live, and --rollback-from-download are mutually exclusive"
        )
    if args.observe_sec < 30:
        raise SystemExit("--observe-sec must be at least 30 for the M34 S8B1 download-beacon probe")
    if args.snapshot_interval_sec < 1.0:
        raise SystemExit("--snapshot-interval-sec must be at least 1.0")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m34_s8b1_beacon_probe_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M34 S8B1 download-beacon probe live gate ===")
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

    if args.print_agents_exception_active_template:
        template = agents_exception_active_template()
        missing = missing_policy_markers(template)
        append_log(log_path, f"agents_exception_active_template_missing={missing}")
        append_log(log_path, f"agents_exception_active_template_draft_only_present={int(has_draft_only_m34_exception(template))}")
        if missing:
            raise SystemExit(f"internal active template is missing policy markers: {missing}")
        if has_draft_only_m34_exception(template):
            raise SystemExit("internal active template still looks draft-only")
        print(template, end="")
        return 0

    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M34 S8B1 candidate and rollback APs verified; no device action; log={log_path}")
        return 0

    if args.readonly_preflight:
        selected_serial = run_android_readonly_preflight(
            run_dir=run_dir,
            log_path=log_path,
            odin=odin,
            serial=args.serial,
            stability_samples=args.android_stability_samples,
            stability_interval_sec=args.android_stability_interval_sec,
            snapshot_label="readonly_preflight_current",
            agents_exception_checked=False,
        )
        print(
            "readonly-preflight ok: M34 S8B1 candidate, rollback APs, Android stability, "
            f"and current boot hash verified for {selected_serial}; no AGENTS exception required; log={log_path}"
        )
        return 0

    if args.prelive_packet:
        selected_serial = run_android_readonly_preflight(
            run_dir=run_dir,
            log_path=log_path,
            odin=odin,
            serial=args.serial,
            stability_samples=args.android_stability_samples,
            stability_interval_sec=args.android_stability_interval_sec,
            snapshot_label="prelive_packet_current",
            agents_exception_checked=False,
        )
        packet_path = write_prelive_packet(
            run_dir=run_dir,
            log_path=log_path,
            args=args,
            selected_serial=selected_serial,
            odin=odin,
            m34_ap=m34_ap,
            m34_manifest=m34_manifest,
            magisk_rollback_ap=magisk_rollback_ap,
            stock_rollback_ap=stock_rollback_ap,
        )
        print(
            "prelive-packet ok: M34 S8B1 artifacts, rollback APs, Android stability, "
            f"current boot hash, active-template, and runbook captured for {selected_serial}; "
            f"no AGENTS exception inserted; packet={packet_path}"
        )
        return 0

    if args.print_live_runbook:
        append_log(log_path, "live_runbook_printed=1 device_action=0 agents_exception_checked=0 android_checked=0")
        print(live_runbook(args))
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
        print(f"M34 S8B1 rollback-from-download completed rc={rc}; log={log_path}")
        return rc

    selected_serial = run_android_readonly_preflight(
        run_dir=run_dir,
        log_path=log_path,
        odin=odin,
        serial=args.serial,
        stability_samples=args.android_stability_samples,
        stability_interval_sec=args.android_stability_interval_sec,
        snapshot_label="dryrun_current",
        agents_exception_checked=True,
    )

    if not args.live:
        print(
            "dry-run ok: M34 S8B1 candidate, rollback APs, AGENTS exception, Android stability, "
            f"and current boot hash verified; log={log_path}"
        )
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    print(
        "M34 S8B1 live gate starting. HIT should self-enter Download mode if "
        "typec port0 or i2c 57-0066 exists; MISS parks and needs manual Download rollback.",
        flush=True,
    )
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(
            run_dir,
            log_path,
            result="candidate-download-mode-missing",
            rc=2,
            rollback_target=args.rollback_target,
            note="adb reboot download did not produce an Odin endpoint",
        )
        print("download mode did not appear for M34 S8B1 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m34_ap, odin_device, log_path, "candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(
            run_dir,
            log_path,
            result="candidate-flash-failed",
            rc=candidate_rc or 3,
            rollback_target=args.rollback_target,
            rollback_device=odin_device,
        )
        print(f"M34 S8B1 candidate Odin flash failed rc={candidate_rc}; log={log_path}", file=sys.stderr)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        append_log(log_path, "m34_s8b1_result=no-proof-original-download-never-disconnected")
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            write_result_summary(
                run_dir,
                log_path,
                result="no-proof-original-download-never-disconnected",
                rc=4,
                rollback_target=args.rollback_target,
                note="original Odin endpoint never disconnected and rollback endpoint was unavailable",
            )
            print(f"rollback download mode unavailable after no-disconnect; manual recovery required. log={log_path}", file=sys.stderr)
            return 4
        rollback = rollback_boot_only_from_download(
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
        write_result_summary(
            run_dir,
            log_path,
            result="no-proof-original-download-never-disconnected",
            rc=rollback.rc or 7,
            rollback_target=rollback.rollback_target,
            rollback_device=rollback.rollback_device,
            android_serial=rollback.android_serial,
            note="rolled back from still-present original Download endpoint; not a beacon proof",
        )
        return rollback.rc or 7

    record_timeline_event(run_dir, "candidate_boot_ready")
    print(f"M34 S8B1 candidate flashed. Observing download beacon for {args.observe_sec}s.", flush=True)
    result, rollback_device = observe_download_beacon(
        run_dir=run_dir,
        log_path=log_path,
        odin=odin,
        observe_sec=args.observe_sec,
        snapshot_interval_sec=args.snapshot_interval_sec,
    )

    if result == "download-beacon-hit":
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            write_result_summary(
                run_dir,
                log_path,
                result=result,
                rc=4,
                rollback_target=args.rollback_target,
                note="HIT was recorded but no rollback Odin endpoint was available",
            )
            print(f"M34 S8B1 HIT recorded but no rollback device is available. log={log_path}", file=sys.stderr)
            return 4
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="beacon_hit",
        )
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(
            run_dir,
            log_path,
            result=result,
            rc=rollback.rc,
            rollback_target=rollback.rollback_target,
            rollback_device=rollback.rollback_device,
            android_serial=rollback.android_serial,
        )
        print(f"M34 S8B1 live gate completed rc={rollback.rc}; result={result}; log={log_path}")
        return rollback.rc

    if result != "download-beacon-miss-parked-manual-download-required":
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(
            run_dir,
            log_path,
            result=result,
            rc=4,
            rollback_target=args.rollback_target,
            note="stopped before clean HIT/MISS proof",
        )
        print(
            f"M34 S8B1 stopped before clean HIT/MISS proof ({result}). If the device is not in Android, "
            "enter Download manually and run --rollback-from-download.",
            file=sys.stderr,
        )
        return 4

    print(
        f"M34 S8B1 result={result}. Enter Download mode manually for rollback now; "
        f"waiting up to {args.manual_download_wait_sec}s.",
        flush=True,
    )
    rollback_device = wait_for_odin(odin, log_path, "manual-rollback-wait", args.manual_download_wait_sec)
    if rollback_device is None:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(
            run_dir,
            log_path,
            result=result,
            rc=4,
            rollback_target=args.rollback_target,
            note="MISS observed and manual Download rollback did not appear within the bounded wait",
        )
        print(
            f"M34 S8B1 MISS observed, but manual Download mode did not appear. "
            f"Run --rollback-from-download after entering Download mode. log={log_path}",
            file=sys.stderr,
        )
        return 4

    rollback = rollback_boot_only_from_download(
        odin=odin,
        rollback_ap=rollback_ap,
        stock_boot_fallback_ap=stock_rollback_ap,
        odin_device=rollback_device,
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=args.rollback_target,
        android_wait_sec=args.android_wait_sec,
        label="manual_after_miss",
    )
    record_timeline_event(run_dir, "live_session_end")
    write_result_summary(
        run_dir,
        log_path,
        result=result,
        rc=rollback.rc,
        rollback_target=rollback.rollback_target,
        rollback_device=rollback.rollback_device,
        android_serial=rollback.android_serial,
    )
    print(f"M34 S8B1 live gate completed rc={rollback.rc}; result={result}; log={log_path}")
    return rollback.rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
