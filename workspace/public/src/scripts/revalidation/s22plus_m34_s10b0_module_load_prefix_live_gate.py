#!/usr/bin/env python3
"""Guarded S22+ M34 S10B0 module-load prefix download-beacon live gate.

Dry-run is the default. Live mode requires a fresh SHA-pinned AGENTS.md
exception and an explicit ack token.

S10B0 keeps the S9/S10A 89-module runtime recipe but narrows the one-bit
beacon to the first /proc/modules prefix predicate:

    cmd_db

Predicate true means HIT and should re-enter Download mode. Predicate false
parks, requiring manual Download rollback.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_s22plus_m34_runtime_gadget_split import (
    M34_S10A_PROC_MODULES_CORE_NAMES,
    M34_S10B_PROC_MODULE_PREFIX_BY_LABEL,
)
from s22plus_m3_observable_live_gate import (
    DEFAULT_MAGISK_ROLLBACK_AP,
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    DEFAULT_STOCK_ROLLBACK_AP,
    EXPECTED_MAGISK_AP_SHA256,
    EXPECTED_STOCK_BOOT_AP_SHA256,
    ROLLBACK_MAGISK,
    ROLLBACK_STOCK,
    append_log,
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


LIVE_ACK_TOKEN = "S22PLUS-M34-S10B0-MODULE-LOAD-PREFIX-LIVE-GATE"
ROLLBACK_ACK_TOKEN = "S22PLUS-M34-S10B0-MODULE-LOAD-PREFIX-ROLLBACK-FROM-DOWNLOAD"

EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
EXPECTED_STAGE = "S10B0"
EXPECTED_STAGE_NUMBER = 13
DISPLAY_SERIAL_REDACTED = "<S22_SERIAL_REDACTED>"
EXPECTED_M34_MARKER = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT_S10B0"
EXPECTED_M34_AP_SHA256 = "c117d8789b4ed990afd047ef3a6bb8d32f0b7b5d76bdce58eecf8ae98725d47c"
EXPECTED_M34_BOOT_SHA256 = "a30120d094d3484b6b4234e0a285f6c26e95120f032ed9ec3671fd287661b610"
EXPECTED_M34_INIT_SHA256 = "50bd942c92d6aad3b143e1f215c0e7a313819994f5dbfa580c11666d32d5f761"
EXPECTED_M34_MODULE_LIST_SHA256 = "c07425f4c738b53822e9f6783a142a2b5eafd72a15bd34c06fb3b49357c8fe26"
EXPECTED_M34_TEMPLATE_SOURCE_SHA256 = "6ac888ddf29e559a9a9b7522eda4edd54c5a38264782dddd2bd5c80d6d8e21a6"
EXPECTED_M34_KERNEL_SHA256 = "bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff"
EXPECTED_M34_BASE_BOOT_SHA256 = EXPECTED_BASE_BOOT_SHA256
EXPECTED_MODULE_COUNT = 89
EXPECTED_MEMBER = "boot.img.lz4"
EXPECTED_MODULE_ENTRY = "s22plus_m34_s10b0_runtime_gadget_split.modules"
EXPECTED_PROBE = "proc_modules_prefix_1"
EXPECTED_SCHEMA = "s22plus_m34_s10b0_result_v1"
EXPECTED_PREFIX_INDEX = 0
EXPECTED_PREFIX_EXPECTED = 1
EXPECTED_PREFIX_MODULES = ["cmd_db"]

DEFAULT_M34_AP = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_12/S10B0/odin4/AP.tar.md5")
DEFAULT_M34_MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_12/manifest.json")
ACTIVE_EXCEPTION_INSERT_ANCHOR = "   **Consumed exception (2026-07-09, S22+ M34 S10A module-load\n"


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
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_m34_s10b0_module_load_prefix_live_gate_{utc_stamp()}")
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
        "S22+ M34 S10B0 module-load prefix download-beacon native-init boot-only",
        "workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py",
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
        "S10B0 starts from the S9/S10A 89-module recipe",
        "S10B0 bisects the S10A all-core /proc/modules MISS",
        "s10b_ladder=1",
        "s10b_module_load_prefix_probe=1",
        f"module_load_probe={EXPECTED_PROBE}",
        "predicate=proc_modules_prefix",
        f"prefix_index={EXPECTED_PREFIX_INDEX}",
        f"prefix_expected={EXPECTED_PREFIX_EXPECTED}",
        "prefix_modules=cmd_db",
        "proc_modules=1",
        "cmd_db=1",
        "both_graphs_closure=1",
        "devlink_supplier_closure=1",
        "substrate_load_set=waipio_devlink",
        "driver_load_only=1",
        "manual_power_write=0",
        f"module_count={EXPECTED_MODULE_COUNT}",
        "session_producer_parity=1",
        "max77705_session=1",
        "geni_i2c_transport=1",
        "i2c_msm_geni=1",
        "gpi_dma=1",
        "msm_geni_se=1",
        "functionfs=0",
        "stock_composite=0",
        "configfs_gadget=0",
        "udc_bind=0",
        "role_write_discriminator=0",
        "typec_readback=0",
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
        "S10B0 HIT means cmd_db appears in /proc/modules under native-init",
        "S10B0 MISS means cmd_db never appears or /proc/modules cannot be trusted there",
        *EXPECTED_PREFIX_MODULES,
        *M34_S10A_PROC_MODULES_CORE_NAMES,
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [marker for marker in policy_required_markers() if marker not in normalized]


def has_exact_active_exception_template(text: str) -> bool:
    return " ".join(agents_exception_active_template().split()) in " ".join(text.split())


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
    return f"""   **DRAFT ONLY - Narrow operator-authorized exception (2026-07-09, S22+ M34 S10B0 module-load prefix boot-only live gate):**
   This draft is not active authorization unless the operator explicitly approves
   it and the block is inserted into `AGENTS.md`. After approval, Codex may run
   one bounded attended boot-partition-only M34 S10B0 live gate on the Samsung
   S22+ `SM-S906N`/`g0q` `S906NKSS7FYG8` using only the checked helper
   `workspace/public/src/scripts/revalidation/s22plus_m34_s10b0_module_load_prefix_live_gate.py`.
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

   The candidate is limited to freestanding direct PID1 M34 S10B0 behavior:
   `S22+ M34 S10B0 module-load prefix download-beacon native-init boot-only`,
   `{EXPECTED_M34_MARKER}`, `S10B0 starts from the S9/S10A 89-module recipe`,
   and `S10B0 bisects the S10A all-core /proc/modules MISS`. It remains
   driver-load-only: `both_graphs_closure=1`, `devlink_supplier_closure=1`,
   `substrate_load_set=waipio_devlink`, `driver_load_only=1`,
   `manual_power_write=0`, `module_count=89`, `session_producer_parity=1`,
   `max77705_session=1`, `geni_i2c_transport=1`, `i2c_msm_geni=1`,
   `gpi_dma=1`, `msm_geni_se=1`, `functionfs=0`, `stock_composite=0`,
   `configfs_gadget=0`, `udc_bind=0`, `role_write_discriminator=0`, and
   `typec_readback=0`.

   S10B0 intentionally performs no downstream USB gadget work: no configfs
   gadget setup, no UDC bind, no TypeC role write, no ssusb role write, no
   FunctionFS, and no stock composite. Its only observation is
   `s10b_ladder=1`, `s10b_module_load_prefix_probe=1`,
   `module_load_probe={EXPECTED_PROBE}`, `predicate=proc_modules_prefix`,
   `proc_modules=1`, `prefix_index=0`, `prefix_expected=1`, and
   `prefix_modules=cmd_db`. Predicate true requests
   `reboot_request=download` with `download_beacon=1` and records
   `true_action=reboot_download`; predicate false records `false_action=park`
   and parks. The host-visible HIT is `download-beacon-hit`, where a new Odin
   Download endpoint appears after the original Download endpoint disconnects.
   MISS is `download-beacon-miss-parked-manual-download-required`; manual
   Download rollback is required and is recovery-only. S10B0 HIT means cmd_db
   appears in /proc/modules under native-init. S10B0 MISS means cmd_db never
   appears or /proc/modules cannot be trusted there.

   The candidate must have no Android/Magisk handoff, no persistent partition
   mount, no block write, no module binary injection into boot ramdisk, no raw
   host `dd`, no fastboot, no Magisk modules, no multidisabler, no format data,
   no DTBO/vendor_boot/recovery/vbmeta/non-boot flash, and no A90 action. It
   must not write charge current, OTG/VBUS boost, regulator, GDSC, GPIO,
   display, raw PMIC knobs, EUD sysfs, TypeC role nodes, configfs, UDC, or
   ssusb role nodes. PMIC/RDX abnormal reset before the observation window is
   FAIL. This exception does not authorize S10B1/S10B2/S10B3/S10B4/S10B5/
   S10B6, S10A/S9 repeat, B2/B3/B4, descriptor/composition pivots,
   FunctionFS/conn_gadget parity, display/distro candidates, kernel rebuilds,
   RDX PC dump retrieval, or any non-boot partition action.

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


def verify_agents_text(agents: str, log_path: Path, *, source_label: str) -> None:
    draft_only = has_draft_only_m34_exception(agents)
    append_log(log_path, f"agents_exception_source={source_label}")
    append_log(log_path, f"agents_exception_draft_only_present={int(draft_only)}")
    if draft_only:
        raise SystemExit(
            f"{source_label} contains draft-only M34 S10B0 authorization text; "
            "refuse to treat draft as active live auth"
        )
    missing = missing_policy_markers(agents)
    append_log(log_path, f"agents_exception_missing={missing}")
    if missing:
        raise SystemExit(f"{source_label} missing M34 S10B0 module-load prefix authorization markers: {missing}")
    active_template_present = has_exact_active_exception_template(agents)
    append_log(log_path, f"agents_exception_exact_active_template_present={int(active_template_present)}")
    if not active_template_present:
        raise SystemExit(
            f"{source_label} marker coverage is present but exact M34 S10B0 active authorization template is absent"
        )


def verify_agents_exception(root: Path, log_path: Path) -> None:
    verify_agents_text((root / "AGENTS.md").read_text(encoding="utf-8"), log_path, source_label="AGENTS.md")


def agents_candidate_text(current_agents: str) -> str:
    template = agents_exception_active_template()
    missing = missing_policy_markers(template)
    if missing:
        raise SystemExit(f"internal active template is missing policy markers: {missing}")
    if has_draft_only_m34_exception(template):
        raise SystemExit("internal active template still looks draft-only")
    if has_draft_only_m34_exception(current_agents):
        raise SystemExit("source AGENTS contains draft-only M34 S10B0 text; refuse to build active candidate over it")
    if has_exact_active_exception_template(current_agents):
        return current_agents
    if not missing_policy_markers(current_agents):
        raise SystemExit("source AGENTS is marker-complete but exact M34 S10B0 active template is absent")
    if ACTIVE_EXCEPTION_INSERT_ANCHOR not in current_agents:
        raise SystemExit("source AGENTS missing M34 S10A consumed-exception insertion anchor")
    return current_agents.replace(ACTIVE_EXCEPTION_INSERT_ANCHOR, template + "\n" + ACTIVE_EXCEPTION_INSERT_ANCHOR, 1)


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
    runtime_steps = stage.get("runtime_steps", {})
    init_info = stage.get("init", {})
    ramdisk = stage.get("ramdisk", {})
    append_log(log_path, f"m34_manifest_path={path}")
    append_log(log_path, f"m34_s10b0_manifest_hashes={json.dumps(hashes, sort_keys=True)}")
    append_log(log_path, f"m34_s10b0_manifest_runtime_steps={json.dumps(runtime_steps, sort_keys=True)}")

    if data.get("target") != EXPECTED_TARGET:
        raise SystemExit(f"M34 target mismatch: {data.get('target')!r}")
    if data.get("hashes", {}).get("template_source") != EXPECTED_M34_TEMPLATE_SOURCE_SHA256:
        raise SystemExit("M34 template source hash mismatch")
    if data.get("hashes", {}).get("nochange_repack_boot") != EXPECTED_M34_BASE_BOOT_SHA256:
        raise SystemExit("M34 no-change MagiskBoot repack is not pinned to the known booting base")
    if data.get("magiskboot", {}).get("nochange_repack_byte_identical") is not True:
        raise SystemExit("M34 no-change MagiskBoot repack is not byte-identical")
    if matrix.get("next_host_only_candidate") != EXPECTED_STAGE:
        raise SystemExit(f"M34 next host-only candidate mismatch: {matrix.get('next_host_only_candidate')!r}")
    ladder = matrix.get("s10b_module_load_prefix_ladder")
    if not isinstance(ladder, list):
        raise SystemExit("M34 S10B ladder missing from manifest")
    expected_ladder_entry = {
        "label": EXPECTED_STAGE,
        "stage_number": EXPECTED_STAGE_NUMBER,
        "module_load_probe": EXPECTED_PROBE,
        "prefix_index": EXPECTED_PREFIX_INDEX,
        "prefix_expected": EXPECTED_PREFIX_EXPECTED,
        "prefix_modules": EXPECTED_PREFIX_MODULES,
    }
    if expected_ladder_entry not in ladder:
        raise SystemExit(f"M34 S10B ladder missing S10B0 entry: {expected_ladder_entry!r}")
    if M34_S10B_PROC_MODULE_PREFIX_BY_LABEL.get(EXPECTED_STAGE) != EXPECTED_PREFIX_MODULES:
        raise SystemExit("builder S10B0 prefix table mismatch")
    if matrix.get("s10b_starts_from_s9_module_recipe") is not True:
        raise SystemExit("M34 S10B matrix does not prove S9 module recipe base")
    if matrix.get("s10b_bisects_s10a_all_core_miss") is not True:
        raise SystemExit("M34 S10B matrix does not prove S10A bisection purpose")
    if matrix.get("s10b_skips_downstream_configfs_and_udc_to_isolate_module_load") is not True:
        raise SystemExit("M34 S10B matrix does not prove downstream USB isolation")
    if matrix.get("s10b_true_action") != "reboot(download)" or matrix.get("s10b_false_action") != "park":
        raise SystemExit("M34 S10B true/false action mismatch")

    if stage.get("stage_number") != EXPECTED_STAGE_NUMBER:
        raise SystemExit(f"M34 S10B0 stage number mismatch: {stage.get('stage_number')!r}")
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
        "beacon_probe": None,
        "module_load_probe": EXPECTED_PROBE,
    }
    if runtime_steps != expected_steps:
        raise SystemExit(f"M34 S10B0 runtime steps mismatch: {runtime_steps!r}")

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
            raise SystemExit(f"M34 S10B0 manifest hash {key} mismatch: {hashes.get(key)!r} != {expected!r}")
    if stage.get("tar_members") != [EXPECTED_MEMBER]:
        raise SystemExit(f"M34 S10B0 tar members mismatch: {stage.get('tar_members')!r}")
    if closure.get("module_count") != EXPECTED_MODULE_COUNT:
        raise SystemExit(f"M34 S10B0 module count mismatch: {closure.get('module_count')!r}")
    if closure.get("module_sha256") != EXPECTED_M34_MODULE_LIST_SHA256:
        raise SystemExit("M34 S10B0 module list SHA mismatch")
    if ramdisk.get("added_subset_entry") != EXPECTED_MODULE_ENTRY:
        raise SystemExit(f"M34 S10B0 module-list ramdisk entry mismatch: {ramdisk.get('added_subset_entry')!r}")
    if ramdisk.get("module_files_injected_into_boot_ramdisk") != 0:
        raise SystemExit("M34 S10B0 must not inject module binaries into boot ramdisk")

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
        "stage_s10b_starts_from_s9_module_recipe": True,
        "stage_s10b_bisects_s10a_all_core_miss": True,
        "stage_s10b_true_reboot_download_false_park": True,
        "stage_s10b_no_configfs_udc_or_role_write": True,
        "stage_s10b_driver_load_only_no_manual_power_write": True,
    }
    for key, expected in required_safety.items():
        if safety.get(key) != expected:
            raise SystemExit(f"M34 S10B0 safety {key} mismatch: {safety.get(key)!r} != {expected!r}")
    if safety.get("stage_s10b_module_load_prefix_ladder") != ladder:
        raise SystemExit("M34 S10B safety ladder does not match matrix ladder")

    required_strings = set(init_info.get("required_strings", []))
    for required in [
        EXPECTED_M34_MARKER,
        "version=0.10",
        "stage=S10B0",
        "runtime_step=S10B0",
        "module_count=89",
        "reboot_request=download",
        "download_beacon=1",
        "configfs_gadget=0",
        "udc_bind=0",
        "role_write_discriminator=0",
        "typec_readback=0",
        "devlink_supplier_closure=1",
        "both_graphs_closure=1",
        "module_load_probe=proc_modules_prefix_1",
        "s10b_module_load_prefix_probe=1",
        "proc_modules=1",
        "s10b_ladder=1",
        "prefix_index=0",
        "prefix_expected=1",
        "prefix_modules=cmd_db",
        "phase=s10b_module_load_prefix_probe",
        "predicate=proc_modules_prefix",
        "expected=1",
        "modules=cmd_db",
        "true_action=reboot_download",
        "false_action=park",
        "phase=s10b_module_load_reboot_returned",
        "/proc/modules",
    ]:
        if required not in required_strings:
            raise SystemExit(f"M34 S10B0 required string missing from manifest: {required}")
    for forbidden in [
        "s10a_module_load_probe=1",
        "phase=s10a_module_load_probe",
        "module_load_probe=proc_modules_core_loaded",
        "s8_beacon_probe=typec_port_or_i2c_any_0066",
        "phase=s9_b1_probe",
        "/sys/bus/i2c/devices",
        "/sys/class/typec/port0",
        "phase=configfs_done",
        "/config/usb_gadget/g1/UDC",
        "/sys/class/udc",
        "phase=udc_bind",
        "phase=typec_role_write",
    ]:
        if forbidden in required_strings:
            raise SystemExit(f"M34 S10B0 manifest unexpectedly requires forbidden string: {forbidden}")


def verify_m34_artifacts(
    *,
    m34_ap: Path,
    m34_manifest: Path,
    magisk_rollback_ap: Path,
    stock_rollback_ap: Path,
    log_path: Path,
) -> None:
    verify_ap(m34_ap, EXPECTED_M34_AP_SHA256, "m34_s10b0_candidate", log_path)
    verify_m34_manifest(m34_manifest, log_path)
    verify_ap(magisk_rollback_ap, EXPECTED_MAGISK_AP_SHA256, "magisk_boot_rollback", log_path)
    verify_ap(stock_rollback_ap, EXPECTED_STOCK_BOOT_AP_SHA256, "stock_boot_fallback", log_path)


def observe_download_beacon(
    *,
    run_dir: Path,
    log_path: Path,
    odin: Path,
    observe_sec: int,
    snapshot_interval_sec: float,
) -> tuple[str, str | None]:
    deadline = time.monotonic() + observe_sec
    next_snapshot = 0.0
    while time.monotonic() < deadline:
        devices = odin_devices(odin, log_path, "candidate-beacon-observe")
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices during S10B0 observation: {devices}")
        if len(devices) == 1:
            host_snapshot(run_dir, log_path, "candidate_beacon_hit", odin)
            append_log(log_path, f"s10b0_result=download-beacon-hit odin_device={devices[0]}")
            return "download-beacon-hit", devices[0]
        now = time.monotonic()
        if now >= next_snapshot:
            host_snapshot(run_dir, log_path, "candidate_observe", odin)
            next_snapshot = now + snapshot_interval_sec
        time.sleep(1.0)
    append_log(log_path, "s10b0_result=download-beacon-miss-parked-manual-download-required")
    return "download-beacon-miss-parked-manual-download-required", None


def wait_for_odin_absent(odin: Path, log_path: Path, label: str, wait_sec: int) -> bool:
    deadline = time.monotonic() + wait_sec
    saw_absent = False
    while time.monotonic() < deadline:
        devices = odin_devices(odin, log_path, label)
        if len(devices) == 0:
            saw_absent = True
            break
        if len(devices) > 1:
            raise SystemExit(f"refusing ambiguous Odin devices while waiting for disconnect: {devices}")
        time.sleep(1.0)
    append_log(log_path, f"{label}_odin_absent={int(saw_absent)}")
    return saw_absent


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
    if rollback_target not in {ROLLBACK_MAGISK, ROLLBACK_STOCK}:
        raise SystemExit(f"invalid rollback target: {rollback_target}")
    primary_target = rollback_target
    primary_ap = rollback_ap if rollback_target == ROLLBACK_MAGISK else stock_boot_fallback_ap
    fallback_target = ROLLBACK_STOCK if rollback_target == ROLLBACK_MAGISK else ROLLBACK_MAGISK
    fallback_ap = stock_boot_fallback_ap if rollback_target == ROLLBACK_MAGISK else rollback_ap

    record_timeline_event(run_dir, "rollback_flash_start")
    rc = flash_ap(odin, primary_ap, odin_device, log_path, f"{label}_{primary_target}_rollback")
    record_timeline_event(run_dir, "rollback_flash_done")
    used_target = primary_target
    used_device = odin_device
    if rc != 0:
        append_log(log_path, f"{label}_primary_rollback_failed_rc={rc}")
        retry_device = wait_for_odin(odin, log_path, f"{label}_fallback_wait", 20)
        if retry_device is None:
            return RollbackResult(rc=rc or 6, android_serial=None, rollback_target=used_target, rollback_device=used_device)
        record_timeline_event(run_dir, "rollback_flash_start")
        rc = flash_ap(odin, fallback_ap, retry_device, log_path, f"{label}_{fallback_target}_rollback")
        record_timeline_event(run_dir, "rollback_flash_done")
        used_target = fallback_target
        used_device = retry_device
    if rc != 0:
        return RollbackResult(rc=rc, android_serial=None, rollback_target=used_target, rollback_device=used_device)

    android = poll_android(log_path, android_wait_sec, expect_root=(used_target == ROLLBACK_MAGISK))
    if android is None:
        return RollbackResult(rc=5, android_serial=None, rollback_target=used_target, rollback_device=used_device)
    record_timeline_event(run_dir, "rollback_boot_ready")
    if used_target == ROLLBACK_MAGISK:
        verify_partition_hash(log_path, android, "boot", EXPECTED_M34_BASE_BOOT_SHA256, f"{label}_boot_restore")
    return RollbackResult(rc=0, android_serial=android, rollback_target=used_target, rollback_device=used_device)


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
        "schema": EXPECTED_SCHEMA,
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
        "module_load_probe": EXPECTED_PROBE,
        "prefix_modules": EXPECTED_PREFIX_MODULES,
    }
    if rollback_device is not None:
        payload["rollback_device"] = rollback_device
    if android_serial is not None:
        payload["android_serial"] = DISPLAY_SERIAL_REDACTED
    if note is not None:
        payload["note"] = note
    path = run_dir / "result.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_log(log_path, f"result_json={path}")
    append_log(log_path, f"result_summary={json.dumps(payload, sort_keys=True)}")


def print_only_mode(args: argparse.Namespace) -> bool:
    return (
        args.print_agents_exception_draft
        or args.print_agents_exception_active_template
        or args.write_agents_candidate is not None
        or args.verify_agents_candidate is not None
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m34-ap", type=Path, default=DEFAULT_M34_AP)
    parser.add_argument("--m34-manifest", type=Path, default=DEFAULT_M34_MANIFEST)
    parser.add_argument("--magisk-rollback-ap", type=Path, default=DEFAULT_MAGISK_ROLLBACK_AP)
    parser.add_argument("--stock-rollback-ap", type=Path, default=DEFAULT_STOCK_ROLLBACK_AP)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--observe-sec", type=int, default=90)
    parser.add_argument("--snapshot-interval-sec", type=float, default=5.0)
    parser.add_argument("--post-flash-disconnect-wait-sec", type=int, default=20)
    parser.add_argument("--manual-download-wait-sec", type=int, default=300)
    parser.add_argument("--odin-wait-sec", type=int, default=90)
    parser.add_argument("--android-wait-sec", type=int, default=240)
    parser.add_argument("--android-stability-samples", type=int, default=2)
    parser.add_argument("--android-stability-interval-sec", type=float, default=2.0)
    parser.add_argument("--rollback-target", choices=[ROLLBACK_MAGISK, ROLLBACK_STOCK], default=ROLLBACK_MAGISK)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--print-agents-exception-draft", action="store_true")
    parser.add_argument("--print-agents-exception-active-template", action="store_true")
    parser.add_argument("--write-agents-candidate", type=Path)
    parser.add_argument("--verify-agents-candidate", type=Path)
    parser.add_argument("--rollback-from-download", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(
        1
        for enabled in (
            args.offline_check,
            args.print_agents_exception_draft,
            args.print_agents_exception_active_template,
            args.write_agents_candidate is not None,
            args.verify_agents_candidate is not None,
            args.rollback_from_download,
            args.live,
        )
        if enabled
    )
    if modes > 1:
        raise SystemExit(
            "--offline-check, --print-agents-exception-draft, "
            "--print-agents-exception-active-template, --write-agents-candidate, "
            "--verify-agents-candidate, --rollback-from-download, and --live are mutually exclusive"
        )
    if args.observe_sec < 30:
        raise SystemExit("--observe-sec must be at least 30 for the M34 S10B0 download-beacon probe")
    if args.snapshot_interval_sec < 1.0:
        raise SystemExit("--snapshot-interval-sec must be at least 1.0")

    root = repo_root()
    m34_ap = resolve(root, args.m34_ap)
    m34_manifest = resolve(root, args.m34_manifest)
    magisk_rollback_ap = resolve(root, args.magisk_rollback_ap)
    stock_rollback_ap = resolve(root, args.stock_rollback_ap)

    if print_only_mode(args):
        with tempfile.TemporaryDirectory(prefix="s22plus_m34_s10b0_print_") as tmp:
            log_path = Path(tmp) / "s22plus_m34_s10b0_module_load_prefix_live_gate.txt"
            append_log(log_path, f"=== {utc_now()} s22plus M34 S10B0 module-load prefix live gate ===")
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
                if missing:
                    raise SystemExit(f"internal draft is missing policy markers: {missing}")
                print(draft, end="")
                return 0
            if args.print_agents_exception_active_template:
                template = agents_exception_active_template()
                missing = missing_policy_markers(template)
                if missing:
                    raise SystemExit(f"internal active template is missing policy markers: {missing}")
                if has_draft_only_m34_exception(template):
                    raise SystemExit("internal active template still looks draft-only")
                print(template, end="")
                return 0
            if args.write_agents_candidate is not None:
                candidate_path = resolve(root, args.write_agents_candidate)
                agents_path = (root / "AGENTS.md").resolve()
                if candidate_path == agents_path:
                    raise SystemExit("--write-agents-candidate refuses to write AGENTS.md directly")
                if candidate_path.exists():
                    raise SystemExit(f"AGENTS candidate already exists; refuse to overwrite: {candidate_path}")
                candidate = agents_candidate_text((root / "AGENTS.md").read_text(encoding="utf-8"))
                verify_agents_text(candidate, log_path, source_label=str(candidate_path))
                candidate_path.parent.mkdir(parents=True, exist_ok=True)
                candidate_path.write_text(candidate, encoding="utf-8")
                print(
                    "write-agents-candidate ok: exact M34 S10B0 active exception inserted into candidate; "
                    f"no AGENTS.md write, no device action; candidate={candidate_path}"
                )
                return 0
            if args.verify_agents_candidate is not None:
                candidate_path = resolve(root, args.verify_agents_candidate)
                verify_agents_text(
                    candidate_path.read_text(encoding="utf-8"),
                    log_path,
                    source_label=str(candidate_path),
                )
                print(
                    "verify-agents-candidate ok: exact M34 S10B0 active exception is present; "
                    f"no AGENTS.md write, no device action; candidate={candidate_path}"
                )
                return 0

    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_m34_s10b0_module_load_prefix_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus M34 S10B0 module-load prefix live gate ===")

    verify_m34_artifacts(
        m34_ap=m34_ap,
        m34_manifest=m34_manifest,
        magisk_rollback_ap=magisk_rollback_ap,
        stock_rollback_ap=stock_rollback_ap,
        log_path=log_path,
    )
    if args.offline_check:
        append_log(log_path, "offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0")
        print(f"offline-check ok: M34 S10B0 artifacts verified; no AGENTS/device action; log={log_path}")
        return 0

    odin = resolve(root, args.odin)
    if not odin.is_file():
        raise SystemExit(f"odin4 missing: {odin}")
    verify_agents_exception(root, log_path)

    if args.rollback_from_download:
        if args.ack != ROLLBACK_ACK_TOKEN:
            raise SystemExit(f"--rollback-from-download requires --ack {ROLLBACK_ACK_TOKEN}")
        devices = odin_devices(odin, log_path, "rollback-only")
        if len(devices) != 1:
            raise SystemExit(f"S10B0 rollback requires exactly one Odin device, got {devices}")
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=devices[0],
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="rollback_only",
        )
        write_result_summary(
            run_dir,
            log_path,
            result="rollback-only-no-s10b0-proof",
            rc=rollback.rc,
            rollback_target=rollback.rollback_target,
            rollback_device=rollback.rollback_device,
            android_serial=rollback.android_serial,
        )
        print(f"M34 S10B0 rollback-from-download completed rc={rollback.rc}; log={log_path}")
        return rollback.rc

    selected_serial = require_current_android(log_path, args.serial)
    verify_android_stability(log_path, selected_serial, args.android_stability_samples, args.android_stability_interval_sec)
    verify_partition_hash(log_path, selected_serial, "boot", EXPECTED_M34_BASE_BOOT_SHA256, "current")
    host_snapshot(run_dir, log_path, "dryrun_current", odin)

    if not args.live:
        print(f"dry-run ok: M34 S10B0 candidate, rollback APs, AGENTS exception, Android, and boot hash verified; log={log_path}")
        return 0
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")

    record_timeline_event(run_dir, "live_session_start")
    print("M34 S10B0 live gate starting. HIT should self-enter Download mode if cmd_db is loaded.", flush=True)
    reboot = run(["adb", "-s", selected_serial, "reboot", "download"], timeout=20.0)
    append_log(log_path, f"adb_reboot_download_rc={reboot.returncode}")
    append_log(log_path, reboot.stdout + reboot.stderr)
    odin_device = wait_for_odin(odin, log_path, "candidate-wait", args.odin_wait_sec)
    if odin_device is None:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result="candidate-download-mode-missing", rc=2, rollback_target=args.rollback_target)
        print("download mode did not appear for M34 S10B0 candidate flash", file=sys.stderr)
        return 2

    record_timeline_event(run_dir, "candidate_flash_start")
    candidate_rc = flash_ap(odin, m34_ap, odin_device, log_path, "candidate")
    record_timeline_event(run_dir, "candidate_flash_done")
    if candidate_rc != 0:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result="candidate-flash-failed", rc=candidate_rc or 3, rollback_target=args.rollback_target, rollback_device=odin_device)
        return candidate_rc or 3

    left_download = wait_for_odin_absent(odin, log_path, "post-candidate-disconnect", args.post_flash_disconnect_wait_sec)
    if not left_download:
        rollback_device = wait_for_odin(odin, log_path, "rollback-still-download-wait", 5)
        if rollback_device is None:
            record_timeline_event(run_dir, "live_session_end")
            write_result_summary(run_dir, log_path, result="no-proof-original-download-never-disconnected", rc=4, rollback_target=args.rollback_target)
            return 4
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="no_disconnect",
        )
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result="no-proof-original-download-never-disconnected", rc=rollback.rc or 7, rollback_target=rollback.rollback_target, rollback_device=rollback.rollback_device, android_serial=rollback.android_serial)
        return rollback.rc or 7

    record_timeline_event(run_dir, "candidate_boot_ready")
    print(f"M34 S10B0 candidate flashed. Observing download beacon for {args.observe_sec}s.", flush=True)
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
            write_result_summary(run_dir, log_path, result=result, rc=4, rollback_target=args.rollback_target)
            return 4
        rollback = rollback_boot_only_from_download(
            odin=odin,
            rollback_ap=magisk_rollback_ap,
            stock_boot_fallback_ap=stock_rollback_ap,
            odin_device=rollback_device,
            run_dir=run_dir,
            log_path=log_path,
            rollback_target=args.rollback_target,
            android_wait_sec=args.android_wait_sec,
            label="beacon_hit",
        )
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result=result, rc=rollback.rc, rollback_target=rollback.rollback_target, rollback_device=rollback.rollback_device, android_serial=rollback.android_serial)
        print(f"M34 S10B0 live gate completed rc={rollback.rc}; result={result}; log={log_path}")
        return rollback.rc

    print(f"M34 S10B0 result={result}. Enter Download mode manually for rollback now; waiting up to {args.manual_download_wait_sec}s.", flush=True)
    rollback_device = wait_for_odin(odin, log_path, "manual-rollback-wait", args.manual_download_wait_sec)
    if rollback_device is None:
        record_timeline_event(run_dir, "live_session_end")
        write_result_summary(run_dir, log_path, result=result, rc=4, rollback_target=args.rollback_target, note="manual Download rollback did not appear within bounded wait")
        print(f"M34 S10B0 MISS observed, but manual Download mode did not appear. Run --rollback-from-download after entering Download mode. log={log_path}", file=sys.stderr)
        return 4
    rollback = rollback_boot_only_from_download(
        odin=odin,
        rollback_ap=magisk_rollback_ap,
        stock_boot_fallback_ap=stock_rollback_ap,
        odin_device=rollback_device,
        run_dir=run_dir,
        log_path=log_path,
        rollback_target=args.rollback_target,
        android_wait_sec=args.android_wait_sec,
        label="manual_after_miss",
    )
    record_timeline_event(run_dir, "live_session_end")
    write_result_summary(run_dir, log_path, result=result, rc=rollback.rc, rollback_target=rollback.rollback_target, rollback_device=rollback.rollback_device, android_serial=rollback.android_serial)
    print(f"M34 S10B0 live gate completed rc={rollback.rc}; result={result}; log={log_path}")
    return rollback.rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
