#!/usr/bin/env python3
"""Build S22+ M34 runtime gadget split native-init artifacts.

Host-only. This script does not reboot, flash, or touch a connected device.

M34 starts after P30 proved the full ACM module closure can park safely without
runtime gadget binding. These artifacts encode the stock ACM recipe, then
isolate the HS-only/PD-less knobs, the final pullup, the stock-kernel-proven
role lever, and the stock SuperSpeed softdep parity gap:

S1: create configfs gadget/function/config, UDC=none, no max_speed/role/bind.
S2: S1 plus max_speed=high-speed and usb_role=device, no UDC bind.
S3: S2 plus UDC bind/pullup on a600000.dwc3.
S4: S3 behavior, but replace the dead usb_role path with
    ssusb/speed=high-speed + ssusb/mode=peripheral before UDC bind.
S5: S4 plus the UDC soft_connect=connect fallback after UDC bind.
S6: S4 lineage with all high-speed forcing removed, ssusb mode=peripheral
    retained, QMP/EUD/ucsi softdep parity restored, and no soft_connect.
S7A: S6 plus the stock max77705/PDIC/altmode session-producer module chain
     and TypeC/UDC readback markers, still ACM-only and no soft_connect.
S7A2: S7A plus the missing GENI I2C transport for the max77705 bus and a
      bounded TypeC role-write discriminator if no partner is present.
S8B1: S7A2 module recipe plus a 1-bit reboot(download) beacon probe for
      max77705 TypeC port or exact I2C-device presence; false parks.
S8B1A: Same as S8B1 but scans all I2C adapter entries for any *-0066 max77705
       device, avoiding the Android-only bus-number assumption.
S9: S8B1A B1 beacon again, but with the resolved Waipio devlink supplier
    substrate load-set pinned and the missing provider modules added before
    GENI I2C/max77705 probe.
S10A: S9 module recipe again, but the 1-bit beacon checks /proc/modules for
      core substrate and max77705 modules, separating module-load failure from
      later driver probe/bind failure.
S10B0..S10B6: same S9 module recipe again, but split S10A's all-core predicate
      into prefix predicates so later live runs can identify the first missing
      module/load-failure boundary instead of only learning "not all 8".
S10C0: same S9 module recipe again, but stop relying on /proc/modules for the
      first boundary and use the direct cmd-db.ko finit_module rc as the
      download-beacon predicate.
S11P0: after the S10C0 live hit proved direct cmd-db.ko finit acceptance, keep
       the same module recipe and positive-control the /proc/modules read path
       against watchdog modules expected to be loaded on the survival path.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_s22plus_inplace_m23_dts_exact_qmp_park as m23
from build_s22plus_direct_p3_boot import (
    BOOT_PARTITION_SIZE,
    display_path,
    repo_root,
    require_ok,
    resolve,
    run,
    sha256_file,
    tar_members,
    write_ap_tar,
    write_boot_lz4,
)
from build_s22plus_inplace_m4t1_magiskboot import (
    DEFAULT_BASE_BOOT,
    DEFAULT_MAGISK_APK,
    DEFAULT_MAGISKBOOT,
    EXPECTED_BASE_BOOT_SHA256,
    EXPECTED_ORIGINAL_MAGISK_INIT_SHA256,
    diff_ranges,
    ensure_magiskboot,
    run_in_dir,
)
from build_s22plus_m32_wdt_hs_acm import EXPECTED_M32_MODULES, dependency_complete_wdt_hs_order


DEFAULT_OUT = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_14")
DEFAULT_TEMPLATE_SOURCE = Path("workspace/public/src/native-init/s22plus_init_m34_runtime_gadget_split.c")
DEFAULT_VENDOR_RAMDISK = m23.DEFAULT_VENDOR_RAMDISK
DEFAULT_LZ4 = m23.DEFAULT_LZ4

MARKER_PREFIX = "S22_NATIVE_INIT_M34_RUNTIME_GADGET_SPLIT"
RUNTIME_MODULES_LOAD_BUF = 4096
M34_S6_STOCK_SOFTDEP_TARGETS = [
    "phy-msm-ssusb-qmp.ko",
    "eud.ko",
    "ucsi_glink.ko",
]
M34_S6_EXPECTED_NEW_MODULES = [
    "eud.ko",
    "phy-msm-ssusb-qmp.ko",
    "qmi_helpers.ko",
    "qcom_glink.ko",
    "qcom_glink_smem.ko",
    "qcom_smd.ko",
    "rproc_qcom_common.ko",
    "pdr_interface.ko",
    "pmic_glink.ko",
    "ucsi_glink.ko",
]
M34_S7A_SESSION_PRODUCER_TARGETS = [
    # Stock /proc/modules prints qcom_i2c_pmic; the firmware module file uses hyphens.
    "qcom-i2c-pmic.ko",
    "mfd_max77705.ko",
    "max77705_charger.ko",
    "max77705-fuelgauge.ko",
    "pdic_max77705.ko",
    "charger-ulog-glink.ko",
    "altmode-glink.ko",
]
M34_S7A2_I2C_GENI_TRANSPORT_TARGETS = [
    "gpi.ko",
    "msm-geni-se.ko",
    "i2c-msm-geni.ko",
]
M34_S7A2_SESSION_PRODUCER_TARGETS = [
    *M34_S7A2_I2C_GENI_TRANSPORT_TARGETS,
    *M34_S7A_SESSION_PRODUCER_TARGETS,
]
M34_S7A_EXPECTED_NEW_MODULES = [
    "charger-ulog-glink.ko",
    "altmode-glink.ko",
    "qti-regmap-debugfs.ko",
    "qcom-i2c-pmic.ko",
    "sec_pm_log.ko",
    "qcom-cpufreq-hw.ko",
    "sched-walt.ko",
    "kryo_arm64_edac.ko",
    "memory_dump_v2.ko",
    "sec_key_notifier.ko",
    "sec_crashkey_long.ko",
    "sec_debug_region.ko",
    "sec_param.ko",
    "sec_qc_dbg_partition.ko",
    "sec_qc_summary.ko",
    "sec_upload_cause.ko",
    "sec_qc_upload_cause.ko",
    "sec_qc_user_reset.ko",
    "sec_qc_smem.ko",
    "sec_qc_hw_param.ko",
    "sb-core.ko",
    "sec_pd.ko",
    "sec-battery.ko",
    "mfd_max77705.ko",
    "spu_verify.ko",
    "pdic_max77705.ko",
    "max77705_charger.ko",
    "max77705-fuelgauge.ko",
]
M34_S7A2_EXPECTED_NEW_MODULES = [
    "msm-geni-se.ko",
    "gpi.ko",
    "charger-ulog-glink.ko",
    "altmode-glink.ko",
    "qti-regmap-debugfs.ko",
    "qcom-i2c-pmic.ko",
    "i2c-msm-geni.ko",
    "sec_pm_log.ko",
    "qcom-cpufreq-hw.ko",
    "sched-walt.ko",
    "kryo_arm64_edac.ko",
    "memory_dump_v2.ko",
    "sec_key_notifier.ko",
    "sec_crashkey_long.ko",
    "sec_debug_region.ko",
    "sec_param.ko",
    "sec_qc_dbg_partition.ko",
    "sec_qc_summary.ko",
    "sec_upload_cause.ko",
    "sec_qc_upload_cause.ko",
    "sec_qc_user_reset.ko",
    "sec_qc_smem.ko",
    "sec_qc_hw_param.ko",
    "sb-core.ko",
    "sec_pd.ko",
    "sec-battery.ko",
    "mfd_max77705.ko",
    "spu_verify.ko",
    "pdic_max77705.ko",
    "max77705_charger.ko",
    "max77705-fuelgauge.ko",
]
M34_S9_DEVLINK_SUPPLIER_LOAD_SET = [
    "clk-qcom.ko",
    "pinctrl-msm.ko",
    "qcom_rpmh.ko",
    "icc-rpmh.ko",
    "icc-bcm-voter.ko",
    "gcc-waipio.ko",
    "pinctrl-waipio.ko",
    "clk-rpmh.ko",
    "rpmh-regulator.ko",
    "gdsc-regulator.ko",
    "qnoc-waipio.ko",
    "arm_smmu.ko",
    "qcom-pdc.ko",
]
M34_S9_EXPECTED_NEW_MODULES = [
    "qcom-pdc.ko",
    "pinctrl-msm.ko",
    "pinctrl-waipio.ko",
]
M34_S10A_PROC_MODULES_CORE_NAMES = [
    "cmd_db",
    "qcom_rpmh",
    "gcc_waipio",
    "pinctrl_waipio",
    "qcom_pdc",
    "i2c_msm_geni",
    "mfd_max77705",
    "pdic_max77705",
]
M34_S10B_PROC_MODULE_PREFIXES = [
    ("S10B0", 13, ["cmd_db"]),
    ("S10B1", 14, ["cmd_db", "qcom_rpmh"]),
    ("S10B2", 15, ["cmd_db", "qcom_rpmh", "gcc_waipio"]),
    ("S10B3", 16, ["cmd_db", "qcom_rpmh", "gcc_waipio", "pinctrl_waipio", "qcom_pdc"]),
    ("S10B4", 17, ["cmd_db", "qcom_rpmh", "gcc_waipio", "pinctrl_waipio", "qcom_pdc", "i2c_msm_geni"]),
    (
        "S10B5",
        18,
        ["cmd_db", "qcom_rpmh", "gcc_waipio", "pinctrl_waipio", "qcom_pdc", "i2c_msm_geni", "mfd_max77705"],
    ),
    ("S10B6", 19, list(M34_S10A_PROC_MODULES_CORE_NAMES)),
]
M34_S10B_PROC_MODULE_PREFIX_BY_LABEL = {
    label: modules for label, _number, modules in M34_S10B_PROC_MODULE_PREFIXES
}
M34_S10C0_PROBE_MODULE = "cmd-db.ko"
M34_S10C0_PROBE_PROC_NAME = "cmd_db"
M34_S11P0_MODULE_LOAD_PROBE = "finit_cmd_db_accepted_and_watchdog_proc_visible"
M34_S11P0_POSITIVE_CONTROL_PROC_NAMES = ["qcom_wdt_core", "gh_virt_wdt"]
M34_S11P0_POSITIVE_CONTROL_MODULES = ["qcom_wdt_core.ko", "gh_virt_wdt.ko"]
M34_S7A_RISK_MODULES = [
    "memory_dump_v2.ko",
    "sec_debug_region.ko",
    "sec_param.ko",
    "sec_qc_dbg_partition.ko",
    "sec_qc_summary.ko",
    "sec_upload_cause.ko",
    "sec_qc_upload_cause.ko",
    "sec_qc_user_reset.ko",
]


@dataclass(frozen=True)
class RuntimeStage:
    label: str
    number: int
    purpose: str
    configfs_gadget: bool
    udc_none: bool
    max_speed_high_speed: bool
    usb_role_force: bool
    ssusb_speed_high_speed: bool
    ssusb_mode_peripheral: bool
    udc_bind: bool
    soft_connect: bool
    stock_softdep_parity: bool = False
    qmp_module_included: bool = False
    eud_module_included: bool = False
    ucsi_glink_included: bool = False
    session_producer_parity: bool = False
    max77705_session_modules_included: bool = False
    typec_readback_markers: bool = False
    geni_i2c_transport_parity: bool = False
    typec_role_write_discriminator: bool = False
    beacon_probe: str | None = None
    module_load_probe: str | None = None
    devlink_supplier_closure: bool = False

    @property
    def lower(self) -> str:
        return self.label.lower()

    @property
    def marker(self) -> str:
        return f"{MARKER_PREFIX}_{self.label}"

    @property
    def modules_ramdisk(self) -> str:
        return f"s22plus_m34_{self.lower}_runtime_gadget_split.modules"

    @property
    def init_name(self) -> str:
        return f"s22plus_init_m34_{self.lower}_runtime_gadget_split"


def s10b_prefix_modules(stage: RuntimeStage) -> list[str] | None:
    return M34_S10B_PROC_MODULE_PREFIX_BY_LABEL.get(stage.label)


def s10b_prefix_index(stage: RuntimeStage) -> int | None:
    for index, (label, _number, _modules) in enumerate(M34_S10B_PROC_MODULE_PREFIXES):
        if stage.label == label:
            return index
    return None


def s10b_prefix_stage(label: str, number: int, modules: list[str]) -> RuntimeStage:
    return RuntimeStage(
        label,
        number,
        (
            "S9 module recipe plus a 1-bit /proc/modules prefix download-beacon "
            f"probe for {','.join(modules)}; true requests reboot(download), false parks"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        module_load_probe=f"proc_modules_prefix_{len(modules)}",
        devlink_supplier_closure=True,
    )


def s10c_loader_audit_stage() -> RuntimeStage:
    return RuntimeStage(
        "S10C0",
        20,
        (
            "S9 module recipe plus a direct module-loader audit download-beacon "
            "probe for cmd-db.ko finit_module acceptance; true requests "
            "reboot(download), false parks"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        module_load_probe="finit_cmd_db_accepted",
        devlink_supplier_closure=True,
    )


def s11p0_proc_modules_positive_control_stage() -> RuntimeStage:
    return RuntimeStage(
        "S11P0",
        21,
        (
            "S9/S10C0 module recipe plus a direct cmd-db.ko finit acceptance "
            "gate and a /proc/modules positive-control beacon for watchdog "
            "modules; true requests reboot(download), false parks"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        module_load_probe=M34_S11P0_MODULE_LOAD_PROBE,
        devlink_supplier_closure=True,
    )


STAGES = [
    RuntimeStage(
        "S1",
        1,
        "stock configfs gadget/function/config plus UDC=none; no max_speed, no role force, no UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
    ),
    RuntimeStage(
        "S2",
        2,
        "S1 plus max_speed=high-speed and usb_role=device; no UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=True,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
    ),
    RuntimeStage(
        "S3",
        3,
        "S2 plus UDC bind/pullup on a600000.dwc3",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=True,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=True,
        soft_connect=False,
    ),
    RuntimeStage(
        "S4",
        4,
        "S3 with the dead usb_role path replaced by ssusb/speed=high-speed and ssusb/mode=peripheral before UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=False,
        ssusb_speed_high_speed=True,
        ssusb_mode_peripheral=True,
        udc_bind=True,
        soft_connect=False,
    ),
    RuntimeStage(
        "S5",
        5,
        "S4 plus /sys/class/udc/a600000.dwc3/soft_connect=connect after UDC bind",
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=True,
        usb_role_force=False,
        ssusb_speed_high_speed=True,
        ssusb_mode_peripheral=True,
        udc_bind=True,
        soft_connect=True,
    ),
    RuntimeStage(
        "S6",
        6,
        (
            "stock-speed controller parity: remove configfs/ssusb high-speed forcing, keep "
            "ssusb mode=peripheral and UDC bind, restore QMP/EUD/ucsi softdep modules, no EUD sysfs write, no soft_connect"
        ),
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=True,
        udc_bind=True,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
    ),
    RuntimeStage(
        "S7A",
        7,
        (
            "session producer parity: start from S6, add the stock max77705/PDIC/altmode "
            "producer chain in dep-correct order, keep minimal ss_acm configfs, keep "
            "ssusb mode=peripheral and UDC bind, add TypeC/UDC readback markers, no soft_connect"
        ),
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=True,
        udc_bind=True,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=True,
    ),
    RuntimeStage(
        "S7A2",
        8,
        (
            "S7A plus the missing GENI I2C transport for the max77705 994000.i2c bus "
            "and a bounded TypeC role-write discriminator before UDC bind when no partner is present"
        ),
        configfs_gadget=True,
        udc_none=True,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=True,
        udc_bind=True,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=True,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=True,
    ),
    RuntimeStage(
        "S8B1",
        9,
        (
            "S7A2 module recipe plus a 1-bit download-beacon probe: after module "
            "load, poll for /sys/class/typec/port0 or /sys/bus/i2c/devices/57-0066; "
            "true requests reboot(download), false parks"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        beacon_probe="typec_port_or_i2c_device",
    ),
    RuntimeStage(
        "S8B1A",
        10,
        (
            "S7A2 module recipe plus a widened 1-bit download-beacon probe: after module "
            "load, poll for /sys/class/typec/port0 or any /sys/bus/i2c/devices/*-0066 entry; "
            "true requests reboot(download), false parks"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        beacon_probe="typec_port_or_i2c_any_0066",
    ),
    RuntimeStage(
        "S9",
        11,
        (
            "S8B1A wide B1 download-beacon probe with the devlink supplier substrate "
            "load-set pinned and the missing qcom-pdc/waipio pinctrl provider modules "
            "added before GENI I2C/max77705"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        beacon_probe="typec_port_or_i2c_any_0066",
        devlink_supplier_closure=True,
    ),
    RuntimeStage(
        "S10A",
        12,
        (
            "S9 module recipe plus a 1-bit download-beacon probe over /proc/modules: "
            "after module load, poll for core substrate and max77705 modules; true "
            "requests reboot(download), false parks"
        ),
        configfs_gadget=False,
        udc_none=False,
        max_speed_high_speed=False,
        usb_role_force=False,
        ssusb_speed_high_speed=False,
        ssusb_mode_peripheral=False,
        udc_bind=False,
        soft_connect=False,
        stock_softdep_parity=True,
        qmp_module_included=True,
        eud_module_included=True,
        ucsi_glink_included=True,
        session_producer_parity=True,
        max77705_session_modules_included=True,
        typec_readback_markers=False,
        geni_i2c_transport_parity=True,
        typec_role_write_discriminator=False,
        module_load_probe="proc_modules_core_loaded",
        devlink_supplier_closure=True,
    ),
    *[
        s10b_prefix_stage(label, number, modules)
        for label, number, modules in M34_S10B_PROC_MODULE_PREFIXES
    ],
    s10c_loader_audit_stage(),
    s11p0_proc_modules_positive_control_stage(),
]


def _stage_by_label(label: str) -> RuntimeStage:
    for stage in STAGES:
        if stage.label == label:
            return stage
    raise KeyError(label)


def c_define_string(name: str, value: str) -> str:
    return f'-D{name}="{value}"'


def _dependency_complete_order(
    *,
    dep_map: dict[str, list[str]],
    recovery_basenames: list[str],
    base_closure: dict[str, Any],
    stage_label: str,
    order_model: str,
    additional_targets: list[str],
    expected_new_modules: list[str],
    forbidden_modules: list[str] | None = None,
) -> dict[str, Any]:
    order_index = {module: index for index, module in enumerate(recovery_basenames)}
    seen: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []
    missing: set[str] = set()
    targets = list(base_closure["targets"]) + list(additional_targets)
    forbidden_modules = forbidden_modules or []

    def sort_key(module: str) -> tuple[int, str]:
        return (order_index.get(module, 10**9), module)

    def visit(module: str) -> None:
        if module in seen:
            return
        if module not in dep_map:
            missing.add(module)
            return
        if module in visiting:
            raise SystemExit(f"cycle in modules.dep while visiting {module}")
        visiting.add(module)
        for dep in sorted(dep_map[module], key=sort_key):
            visit(dep)
        visiting.remove(module)
        seen.add(module)
        ordered.append(module)

    for target in sorted(targets, key=sort_key):
        visit(target)

    if missing:
        raise SystemExit(f"M34 {stage_label} dependency closure missing modules.dep entries: {sorted(missing)}")

    dependency_violations = {
        module: [dep for dep in dep_map[module] if dep in ordered and ordered.index(dep) > ordered.index(module)]
        for module in ordered
    }
    dependency_violations = {module: deps for module, deps in dependency_violations.items() if deps}
    if dependency_violations:
        raise SystemExit(f"M34 {stage_label} module order violates modules.dep: {dependency_violations}")

    new_modules = [module for module in ordered if module not in base_closure["modules"]]
    if new_modules != expected_new_modules:
        raise SystemExit(f"M34 {stage_label} new module set drifted:\nactual={new_modules!r}\nexpected={expected_new_modules!r}")
    for required in additional_targets:
        if required not in ordered:
            raise SystemExit(f"M34 {stage_label} additional target missing: {required}")
    forbidden_present = [module for module in forbidden_modules if module in ordered]
    if forbidden_present:
        raise SystemExit(f"M34 {stage_label} forbidden module(s) present: {forbidden_present}")

    module_text = "".join(f"{module}\n" for module in ordered)
    if len(module_text.encode("ascii")) >= RUNTIME_MODULES_LOAD_BUF:
        raise SystemExit(f"M34 {stage_label} dependency-complete module list exceeds runtime parser buffer")
    too_long = [module for module in ordered if len(module) >= m23.RUNTIME_MODULE_NAME_BUF]
    if too_long:
        raise SystemExit(f"M34 {stage_label} module basename exceeds runtime parser buffer: {too_long}")

    return {
        "targets": targets,
        "modules": ordered,
        "module_count": len(ordered),
        "module_text": module_text,
        "module_sha256": None,
        "watchdog_modules": ["qcom_wdt_core.ko", "gh_virt_wdt.ko"],
        "usb_modules": ["dwc3-msm.ko", "usb_f_ss_acm.ko", "usb_f_ss_mon_gadget.ko"],
        "additional_targets": list(additional_targets),
        "additional_new_modules": new_modules,
        "forbidden_modules": list(forbidden_modules),
        "risk_modules": [module for module in M34_S7A_RISK_MODULES if module in ordered],
        "stock_recovery_positions": {
            module: recovery_basenames.index(module) + 1
            for module in ordered
            if module in recovery_basenames
        },
        "order_model": order_model,
    }


def dependency_complete_stock_softdep_order(
    *,
    dep_map: dict[str, list[str]],
    recovery_basenames: list[str],
    base_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = _dependency_complete_order(
        dep_map=dep_map,
        recovery_basenames=recovery_basenames,
        base_closure=base_closure,
        stage_label="S6",
        order_model="modules.dep topological order with stock modules.load.recovery tie-breaks plus dwc3_msm QMP/EUD/ucsi softdep",
        additional_targets=list(M34_S6_STOCK_SOFTDEP_TARGETS),
        expected_new_modules=list(M34_S6_EXPECTED_NEW_MODULES),
        forbidden_modules=["sec_debug_region.ko"],
    )
    closure["stock_softdep_targets"] = list(M34_S6_STOCK_SOFTDEP_TARGETS)
    closure["stock_softdep_new_modules"] = list(closure["additional_new_modules"])
    closure["excluded_modules"] = ["sec_debug_region.ko"]
    return closure


def dependency_complete_session_producer_order(
    *,
    dep_map: dict[str, list[str]],
    recovery_basenames: list[str],
    base_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = _dependency_complete_order(
        dep_map=dep_map,
        recovery_basenames=recovery_basenames,
        base_closure=base_closure,
        stage_label="S7A",
        order_model=(
            "modules.dep topological order with stock modules.load.recovery tie-breaks plus S6 "
            "QMP/EUD/ucsi and max77705/PDIC/altmode session-producer targets"
        ),
        additional_targets=list(M34_S7A_SESSION_PRODUCER_TARGETS),
        expected_new_modules=list(M34_S7A_EXPECTED_NEW_MODULES),
    )
    closure["stock_softdep_targets"] = list(M34_S6_STOCK_SOFTDEP_TARGETS)
    closure["stock_softdep_new_modules"] = list(M34_S6_EXPECTED_NEW_MODULES)
    closure["session_producer_targets"] = list(M34_S7A_SESSION_PRODUCER_TARGETS)
    closure["session_producer_new_modules"] = list(closure["additional_new_modules"])
    closure["contains_sec_debug_region"] = "sec_debug_region.ko" in closure["modules"]
    closure["requires_live_risk_review"] = bool(closure["risk_modules"])
    return closure


def dependency_complete_session_producer_i2c_order(
    *,
    dep_map: dict[str, list[str]],
    recovery_basenames: list[str],
    base_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = _dependency_complete_order(
        dep_map=dep_map,
        recovery_basenames=recovery_basenames,
        base_closure=base_closure,
        stage_label="S7A2",
        order_model=(
            "modules.dep topological order with stock modules.load.recovery tie-breaks plus S6 "
            "QMP/EUD/ucsi, GENI I2C transport, and max77705/PDIC/altmode session-producer targets"
        ),
        additional_targets=list(M34_S7A2_SESSION_PRODUCER_TARGETS),
        expected_new_modules=list(M34_S7A2_EXPECTED_NEW_MODULES),
    )
    closure["stock_softdep_targets"] = list(M34_S6_STOCK_SOFTDEP_TARGETS)
    closure["stock_softdep_new_modules"] = list(M34_S6_EXPECTED_NEW_MODULES)
    closure["geni_i2c_transport_targets"] = list(M34_S7A2_I2C_GENI_TRANSPORT_TARGETS)
    closure["geni_i2c_transport_new_modules"] = [
        module for module in M34_S7A2_I2C_GENI_TRANSPORT_TARGETS if module in closure["additional_new_modules"]
    ]
    closure["geni_i2c_transport_order_actual"] = [
        module for module in closure["modules"] if module in M34_S7A2_I2C_GENI_TRANSPORT_TARGETS
    ]
    closure["session_producer_targets"] = list(M34_S7A_SESSION_PRODUCER_TARGETS)
    closure["session_producer_new_modules"] = [
        module for module in closure["additional_new_modules"] if module in M34_S7A_EXPECTED_NEW_MODULES
    ]
    closure["contains_sec_debug_region"] = "sec_debug_region.ko" in closure["modules"]
    closure["requires_live_risk_review"] = bool(closure["risk_modules"])
    return closure


def dependency_complete_devlink_supplier_i2c_order(
    *,
    dep_map: dict[str, list[str]],
    recovery_basenames: list[str],
    base_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = _dependency_complete_order(
        dep_map=dep_map,
        recovery_basenames=recovery_basenames,
        base_closure=base_closure,
        stage_label="S9",
        order_model=(
            "modules.dep topological order with stock modules.load.recovery tie-breaks plus "
            "S8B1A wide B1 recipe and the resolved Waipio devlink supplier substrate load-set"
        ),
        additional_targets=list(M34_S9_DEVLINK_SUPPLIER_LOAD_SET),
        expected_new_modules=list(M34_S9_EXPECTED_NEW_MODULES),
    )
    closure["stock_softdep_targets"] = list(M34_S6_STOCK_SOFTDEP_TARGETS)
    closure["stock_softdep_new_modules"] = list(M34_S6_EXPECTED_NEW_MODULES)
    closure["geni_i2c_transport_targets"] = list(M34_S7A2_I2C_GENI_TRANSPORT_TARGETS)
    closure["geni_i2c_transport_new_modules"] = [
        module for module in M34_S7A2_I2C_GENI_TRANSPORT_TARGETS if module in closure["additional_new_modules"]
    ]
    closure["geni_i2c_transport_order_actual"] = [
        module for module in closure["modules"] if module in M34_S7A2_I2C_GENI_TRANSPORT_TARGETS
    ]
    closure["session_producer_targets"] = list(M34_S7A_SESSION_PRODUCER_TARGETS)
    closure["session_producer_new_modules"] = [
        module for module in closure["additional_new_modules"] if module in M34_S7A_EXPECTED_NEW_MODULES
    ]
    closure["devlink_supplier_load_set"] = list(M34_S9_DEVLINK_SUPPLIER_LOAD_SET)
    closure["devlink_supplier_targets"] = list(M34_S9_DEVLINK_SUPPLIER_LOAD_SET)
    closure["devlink_supplier_new_modules"] = list(closure["additional_new_modules"])
    closure["devlink_supplier_order_actual"] = [
        module for module in closure["modules"] if module in M34_S9_DEVLINK_SUPPLIER_LOAD_SET
    ]
    closure["devlink_supplier_already_present_modules"] = [
        module
        for module in M34_S9_DEVLINK_SUPPLIER_LOAD_SET
        if module in base_closure["modules"]
    ]
    closure["contains_sec_debug_region"] = "sec_debug_region.ko" in closure["modules"]
    closure["requires_live_risk_review"] = bool(closure["risk_modules"])
    return closure


def compile_init(source: Path, out_path: Path, build_dir: Path, stage: RuntimeStage, module_count: int) -> dict[str, Any]:
    has_download_probe = bool(stage.beacon_probe or stage.module_load_probe)
    s10b_prefix = s10b_prefix_modules(stage)
    version_marker = (
        "version=0.12"
        if stage.module_load_probe == M34_S11P0_MODULE_LOAD_PROBE
        else "version=0.11"
        if stage.module_load_probe == "finit_cmd_db_accepted"
        else "version=0.10"
        if s10b_prefix
        else "version=0.9"
        if stage.module_load_probe
        else "version=0.8"
        if stage.beacon_probe
        else "version=0.6"
    )
    result = run(
        [
            "aarch64-linux-gnu-gcc",
            "-nostdlib",
            "-static",
            "-ffreestanding",
            "-fno-builtin",
            "-fno-stack-protector",
            "-fno-asynchronous-unwind-tables",
            "-fno-unwind-tables",
            "-Os",
            "-Wall",
            "-Wextra",
            "-Werror",
            *(["-Wno-unused-function"] if has_download_probe else []),
            "-Wl,--build-id=none",
            "-Wl,-e,_start",
            "-Wl,-z,noexecstack",
            f"-DM34_STAGE={stage.number}",
            c_define_string("M34_STAGE_NAME", stage.label),
            c_define_string("M34_MARKER", stage.marker),
            f"-DM34_MODULE_LIMIT={module_count}",
            c_define_string("M34_MODULES_RAMDISK", f"/{stage.modules_ramdisk}"),
            "-o",
            out_path,
            source,
        ]
    )
    require_ok(result, f"compile M34 {stage.label} runtime gadget split init")
    strip = run(["aarch64-linux-gnu-strip", "-s", out_path])
    require_ok(strip, f"strip M34 {stage.label} runtime gadget split init")

    file_info = run(["file", out_path])
    require_ok(file_info, f"file M34 {stage.label} init")
    readelf = run(["aarch64-linux-gnu-readelf", "-h", "-l", out_path])
    require_ok(readelf, f"readelf M34 {stage.label} init")
    objdump = run(["aarch64-linux-gnu-objdump", "-d", out_path])
    require_ok(objdump, f"objdump M34 {stage.label} init")
    readelf_text = readelf.stdout.decode("utf-8", errors="replace")
    objdump_text = objdump.stdout.decode("utf-8", errors="replace")
    if "INTERP" in readelf_text or "Requesting program interpreter" in readelf_text:
        raise SystemExit(f"M34 {stage.label} init unexpectedly has a program interpreter")
    if "AArch64" not in readelf_text:
        raise SystemExit(f"M34 {stage.label} init is not AArch64")
    if "svc" not in objdump_text:
        raise SystemExit(f"M34 {stage.label} init disassembly does not contain svc")
    if not any("#0x111" in line and "// #273" in line for line in objdump_text.splitlines()):
        raise SystemExit(f"M34 {stage.label} init does not load arm64 __NR_finit_module (273)")
    has_reboot_nr = any("mov" in line and "x8" in line and "#0x8e" in line for line in objdump_text.splitlines())
    if has_download_probe:
        if not has_reboot_nr:
            raise SystemExit(f"M34 {stage.label} download-probe init does not load arm64 __NR_reboot (142)")
    elif has_reboot_nr:
        raise SystemExit(f"M34 {stage.label} init must not load arm64 __NR_reboot (142)")

    required_strings = [
        stage.marker,
        version_marker,
        "runtime=freestanding",
        "raw_syscalls=1",
        f"/{stage.modules_ramdisk}",
        "module_list=dep_complete_runtime_gadget_split",
        f"stage={stage.label}",
        f"runtime_step={stage.label}",
        f"module_count={module_count}",
        "no_android_handoff=1",
        "phase=modules_load_done",
        "phase=park_enter",
    ]
    if has_download_probe:
        required_strings.extend(["reboot_request=download", "download_beacon=1"])
    else:
        required_strings.extend(["no_reboot_request=1", "no_download_beacon=1"])
    if stage.configfs_gadget:
        required_strings.extend(
            [
                "phase=configfs_done",
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
                "S22 Native Init M34 Runtime Split",
                "S22M34RUNTIME01",
            ]
        )
    else:
        required_strings.extend(["configfs_gadget=0", "stock_order=0", "udc_none=0"])
    if stage.max_speed_high_speed:
        required_strings.extend(["max_speed_high_speed=1", "/config/usb_gadget/g1/max_speed", "high-speed", "phase=max_speed"])
    else:
        required_strings.append("max_speed_high_speed=0")
    if stage.usb_role_force:
        required_strings.extend(["role_force=1", "/sys/class/usb_role", "phase=usb_role_done"])
    else:
        required_strings.append("role_force=0")
    if stage.ssusb_speed_high_speed:
        required_strings.extend([
            "ssusb_speed_high_speed=1",
            "/sys/devices/platform/soc/a600000.ssusb/speed",
            "phase=ssusb_speed",
        ])
    else:
        required_strings.append("ssusb_speed_high_speed=0")
    if stage.ssusb_mode_peripheral:
        required_strings.extend([
            "ssusb_mode_peripheral=1",
            "/sys/devices/platform/soc/a600000.ssusb/mode",
            "peripheral",
            "phase=ssusb_mode",
        ])
    else:
        required_strings.append("ssusb_mode_peripheral=0")
    if stage.udc_bind:
        required_strings.extend(["udc_bind=1", "/config/usb_gadget/g1/UDC", "/sys/class/udc", "a600000.dwc3", "phase=udc_bind"])
    else:
        required_strings.append("udc_bind=0")
    if stage.soft_connect:
        required_strings.extend([
            "soft_connect=1",
            "/sys/class/udc/a600000.dwc3/soft_connect",
            "phase=soft_connect",
            "value=connect",
        ])
    else:
        required_strings.append("soft_connect=0")
    if stage.stock_softdep_parity:
        required_strings.extend(["stock_softdep_parity=1", "qmp_module=1", "eud_module=1", "ucsi_glink=1"])
    else:
        required_strings.extend(["stock_softdep_parity=0", "qmp_module=0", "eud_module=0", "ucsi_glink=0"])
    if stage.session_producer_parity:
        required_strings.extend(
            [
                "session_producer_parity=1",
                "max77705_session=1",
                "functionfs=0",
                "stock_composite=0",
            ]
        )
    else:
        required_strings.extend(["session_producer_parity=0", "max77705_session=0", "typec_readback=0"])
    if stage.typec_readback_markers:
        required_strings.extend(
            [
                "typec_readback=1",
                "/sys/devices/platform/soc/a600000.ssusb/speed",
                "/sys/class/typec/port0/data_role",
                "/sys/class/typec/port0/power_role",
                "/sys/class/typec/port0/port_type",
                "/sys/class/typec/port0-partner/uevent",
                "/sys/class/udc/a600000.dwc3/state",
                "/sys/class/udc/a600000.dwc3/current_speed",
                "/sys/class/udc/a600000.dwc3/function",
                "typec_pre_bind",
                "typec_post_bind",
                "udc_pre_bind",
                "udc_post_bind",
            ]
        )
    elif stage.session_producer_parity:
        required_strings.append("typec_readback=0")
    if stage.geni_i2c_transport_parity:
        required_strings.extend(
            [
                "geni_i2c_transport=1",
                "i2c_msm_geni=1",
                "gpi_dma=1",
                "msm_geni_se=1",
            ]
        )
    else:
        required_strings.append("geni_i2c_transport=0")
    if stage.typec_role_write_discriminator:
        required_strings.extend(
            [
                "role_write_discriminator=1",
                "phase=typec_partner_check",
                "phase=typec_role_write",
                "role_device_rc=",
                "role_sink_rc=",
                "/sys/class/typec/port0/data_role",
                "/sys/class/typec/port0/power_role",
                "device",
                "sink",
            ]
        )
    else:
        required_strings.append("role_write_discriminator=0")
    if stage.devlink_supplier_closure:
        required_strings.extend(
            [
                "devlink_supplier_closure=1",
                "substrate_load_set=waipio_devlink",
                "clk_qcom=1",
                "qcom_rpmh=1",
                "icc_rpmh=1",
                "icc_bcm_voter=1",
                "gcc_waipio=1",
                "clk_rpmh=1",
                "rpmh_regulator=1",
                "gdsc_regulator=1",
                "qnoc_waipio=1",
                "arm_smmu=1",
                "qcom_pdc=1",
                "pinctrl_msm=1",
                "pinctrl_waipio=1",
                "driver_load_only=1",
                "manual_power_write=0",
            ]
        )
    if stage.beacon_probe:
        required_strings.extend(
            [
                f"s8_beacon_probe={stage.beacon_probe}",
                "true_action=reboot_download",
                "false_action=park",
                "/sys/class/typec/port0",
                "download",
            ]
        )
        if stage.beacon_probe == "typec_port_or_i2c_device":
            required_strings.extend(
                [
                    "b1=1",
                    "phase=s8_b1_probe",
                    "predicate=typec_port_or_i2c_device",
                    "/sys/bus/i2c/devices/57-0066",
                ]
            )
        elif stage.beacon_probe == "typec_port_or_i2c_any_0066":
            phase = "phase=s9_b1_probe" if stage.label == "S9" else "phase=s8_b1a_probe"
            flag = "s9_b1=1" if stage.label == "S9" else "b1a=1"
            required_strings.extend(
                [
                    flag,
                    phase,
                    "predicate=typec_port_or_i2c_any_0066",
                    "/sys/bus/i2c/devices",
                    "*-0066",
                ]
            )
        else:
            raise SystemExit(f"unknown M34 beacon probe contract for {stage.label}: {stage.beacon_probe}")
    if stage.module_load_probe:
        if stage.module_load_probe == "proc_modules_core_loaded":
            required_strings.extend(
                [
                    f"module_load_probe={stage.module_load_probe}",
                    "s10a_module_load_probe=1",
                    "proc_modules=1",
                    f"core_module_count={len(M34_S10A_PROC_MODULES_CORE_NAMES)}",
                    "core_modules=" + ",".join(M34_S10A_PROC_MODULES_CORE_NAMES),
                    "both_graphs_closure=1",
                    "cmd_db=1",
                    "smem=1",
                    "qcom_scm=1",
                    "qcom_ipc_logging=1",
                    "phase=s10a_module_load_probe",
                    "predicate=proc_modules_core_loaded",
                    "loaded_count=",
                    f"expected={len(M34_S10A_PROC_MODULES_CORE_NAMES)}",
                    "modules=" + ",".join(M34_S10A_PROC_MODULES_CORE_NAMES),
                    "true_action=reboot_download",
                    "false_action=park",
                    "phase=s10a_module_load_reboot_returned",
                    "/proc/modules",
                    "download",
                ]
            )
        elif s10b_prefix:
            prefix_index = s10b_prefix_index(stage)
            if prefix_index is None:
                raise SystemExit(f"unknown M34 S10B prefix stage: {stage.label}")
            expected_probe = f"proc_modules_prefix_{len(s10b_prefix)}"
            if stage.module_load_probe != expected_probe:
                raise SystemExit(f"M34 {stage.label} prefix probe mismatch: {stage.module_load_probe} != {expected_probe}")
            required_strings.extend(
                [
                    f"module_load_probe={stage.module_load_probe}",
                    "s10b_module_load_prefix_probe=1",
                    "proc_modules=1",
                    "s10b_ladder=1",
                    f"prefix_index={prefix_index}",
                    f"prefix_expected={len(s10b_prefix)}",
                    "prefix_modules=" + ",".join(s10b_prefix),
                    "both_graphs_closure=1",
                    "cmd_db=1",
                    "smem=1",
                    "qcom_scm=1",
                    "qcom_ipc_logging=1",
                    "phase=s10b_module_load_prefix_probe",
                    "predicate=proc_modules_prefix",
                    "loaded_count=",
                    f"expected={len(s10b_prefix)}",
                    "modules=" + ",".join(s10b_prefix),
                    "true_action=reboot_download",
                    "false_action=park",
                    "phase=s10b_module_load_reboot_returned",
                    "/proc/modules",
                    "download",
                ]
            )
        elif stage.module_load_probe == "finit_cmd_db_accepted":
            required_strings.extend(
                [
                    "module_load_probe=finit_cmd_db_accepted",
                    "s10c_loader_audit=1",
                    "proc_modules=0",
                    "direct_finit_rc=1",
                    f"probe_module={M34_S10C0_PROBE_MODULE}",
                    f"probe_proc_name={M34_S10C0_PROBE_PROC_NAME}",
                    f"cmd_db_file={M34_S10C0_PROBE_MODULE}",
                    "both_graphs_closure=1",
                    "cmd_db=1",
                    "smem=1",
                    "qcom_scm=1",
                    "qcom_ipc_logging=1",
                    "phase=modules_load_done",
                    "attempted=",
                    "ok=",
                    "eexist=",
                    "fail=",
                    "phase=s10c_module_loader_audit_probe",
                    "predicate=cmd_db_finit_accepted",
                    "modules_open_rc=",
                    "modules_read_rc=",
                    "first_fail_index=",
                    "first_fail_rc=",
                    "first_fail_name=",
                    "cmd_db_seen=",
                    "cmd_db_rc=",
                    "true_action=reboot_download",
                    "false_action=park",
                    "phase=s10c_module_loader_audit_reboot_returned",
                    "download",
                ]
            )
        elif stage.module_load_probe == M34_S11P0_MODULE_LOAD_PROBE:
            required_strings.extend(
                [
                    f"module_load_probe={M34_S11P0_MODULE_LOAD_PROBE}",
                    "s11_proc_modules_positive_control=1",
                    "proc_modules=1",
                    "direct_finit_rc=1",
                    f"probe_module={M34_S10C0_PROBE_MODULE}",
                    f"probe_proc_name={M34_S10C0_PROBE_PROC_NAME}",
                    "positive_control=watchdog_proc_visible",
                    "positive_control_proc_names=" + ",".join(M34_S11P0_POSITIVE_CONTROL_PROC_NAMES),
                    "positive_control_modules=" + ",".join(M34_S11P0_POSITIVE_CONTROL_MODULES),
                    f"cmd_db_file={M34_S10C0_PROBE_MODULE}",
                    "both_graphs_closure=1",
                    "cmd_db=1",
                    "qcom_wdt_core=1",
                    "gh_virt_wdt=1",
                    "smem=1",
                    "qcom_scm=1",
                    "qcom_ipc_logging=1",
                    "phase=modules_load_done",
                    "attempted=",
                    "ok=",
                    "eexist=",
                    "fail=",
                    "phase=s11_proc_modules_positive_control_probe",
                    "predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
                    "modules_open_rc=",
                    "modules_read_rc=",
                    "first_fail_index=",
                    "first_fail_rc=",
                    "first_fail_name=",
                    "cmd_db_seen=",
                    "cmd_db_rc=",
                    "direct_cmd_db=",
                    "cmd_db_proc_seen=",
                    "qcom_wdt_core_proc_seen=",
                    "gh_virt_wdt_proc_seen=",
                    "watchdog_proc_seen=",
                    "waited_sec=",
                    "true_action=reboot_download",
                    "false_action=park",
                    "phase=s11_proc_modules_positive_control_reboot_returned",
                    "/proc/modules",
                    "download",
                ]
            )
        else:
            raise SystemExit(f"unknown M34 module-load probe contract for {stage.label}: {stage.module_load_probe}")

    forbidden_strings = [
        b"ld-linux",
        b"libc.so",
        b"/vendor_dlkm",
        b"ttyGS0",
    ]
    if has_download_probe:
        forbidden_strings.extend([b"no_reboot_request=1", b"no_download_beacon=1"])
    else:
        forbidden_strings.extend([
            b" reboot_request=download ",
            b" download_beacon=1 ",
            b"LINUX_REBOOT",
        ])
    if stage.beacon_probe:
        if stage.beacon_probe == "typec_port_or_i2c_device":
            forbidden_strings.extend([b"phase=s8_b1a_probe", b"predicate=typec_port_or_i2c_any_0066", b"*-0066"])
        elif stage.beacon_probe == "typec_port_or_i2c_any_0066":
            forbidden_strings.extend([b"phase=s8_b1_probe", b"predicate=typec_port_or_i2c_device", b"/sys/bus/i2c/devices/57-0066"])
            if stage.label == "S9":
                forbidden_strings.append(b"phase=s8_b1a_probe")
    if not stage.devlink_supplier_closure:
        forbidden_strings.extend([
            b"devlink_supplier_closure=1",
            b"substrate_load_set=waipio_devlink",
            b"qcom_pdc=1",
            b"pinctrl_waipio=1",
        ])
    if stage.beacon_probe:
        if stage.label != "S9":
            forbidden_strings.append(b"phase=s9_b1_probe")
    else:
        forbidden_strings.extend([
            b"phase=s8_b1_probe",
            b"phase=s8_b1a_probe",
            b"phase=s9_b1_probe",
            b"/sys/bus/i2c/devices/57-0066",
            b"/sys/bus/i2c/devices",
        ])
    if stage.module_load_probe:
        forbidden_strings.extend([
            b"s8_beacon_probe=",
            b"phase=s8_b1_probe",
            b"phase=s8_b1a_probe",
            b"phase=s9_b1_probe",
            b"predicate=typec_port_or_i2c",
            b"/sys/bus/i2c/devices",
            b"/sys/class/typec/port0",
        ])
        if s10b_prefix:
            forbidden_strings.extend([
                b"s10a_module_load_probe=1",
                b"phase=s10a_module_load_probe",
                b"predicate=proc_modules_core_loaded",
                b"s10c_loader_audit=1",
                b"phase=s10c_module_loader_audit_probe",
                b"predicate=cmd_db_finit_accepted",
                b"s11_proc_modules_positive_control=1",
                b"phase=s11_proc_modules_positive_control_probe",
                b"predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
            ])
        elif stage.module_load_probe == "proc_modules_core_loaded":
            forbidden_strings.extend([
                b"s10b_module_load_prefix_probe=1",
                b"phase=s10b_module_load_prefix_probe",
                b"predicate=proc_modules_prefix",
                b"s10c_loader_audit=1",
                b"phase=s10c_module_loader_audit_probe",
                b"predicate=cmd_db_finit_accepted",
                b"s11_proc_modules_positive_control=1",
                b"phase=s11_proc_modules_positive_control_probe",
                b"predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
            ])
        elif stage.module_load_probe == "finit_cmd_db_accepted":
            forbidden_strings.extend([
                b"s10a_module_load_probe=1",
                b"phase=s10a_module_load_probe",
                b"predicate=proc_modules_core_loaded",
                b"s10b_module_load_prefix_probe=1",
                b"phase=s10b_module_load_prefix_probe",
                b"predicate=proc_modules_prefix",
                b"/proc/modules",
                b"s11_proc_modules_positive_control=1",
                b"phase=s11_proc_modules_positive_control_probe",
                b"predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
            ])
        elif stage.module_load_probe == M34_S11P0_MODULE_LOAD_PROBE:
            forbidden_strings.extend([
                b"s10a_module_load_probe=1",
                b"phase=s10a_module_load_probe",
                b"predicate=proc_modules_core_loaded",
                b"s10b_module_load_prefix_probe=1",
                b"phase=s10b_module_load_prefix_probe",
                b"predicate=proc_modules_prefix",
                b"s10c_loader_audit=1",
                b"phase=s10c_module_loader_audit_probe",
            ])
    else:
        forbidden_strings.extend([
            b"s10a_module_load_probe=1",
            b"module_load_probe=proc_modules_core_loaded",
            b"phase=s10a_module_load_probe",
            b"predicate=proc_modules_core_loaded",
            b"s10b_module_load_prefix_probe=1",
            b"phase=s10b_module_load_prefix_probe",
            b"predicate=proc_modules_prefix",
            b"s10c_loader_audit=1",
            b"module_load_probe=finit_cmd_db_accepted",
            b"phase=s10c_module_loader_audit_probe",
            b"predicate=cmd_db_finit_accepted",
            b"s11_proc_modules_positive_control=1",
            b"module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible",
            b"phase=s11_proc_modules_positive_control_probe",
            b"predicate=cmd_db_finit_accepted_and_watchdog_proc_visible",
            b"/proc/modules",
        ])
    if not stage.configfs_gadget:
        forbidden_strings.extend([
            b"phase=configfs_done",
            b"/config/usb_gadget/g1/functions/ss_acm.0",
            b"../../functions/ss_acm.0",
            b"S22 Native Init M34 Runtime Split",
            b"S22M34RUNTIME01",
        ])
    if not stage.max_speed_high_speed:
        forbidden_strings.extend([b"/config/usb_gadget/g1/max_speed", b"phase=max_speed", b"high-speed"])
    if not stage.usb_role_force:
        forbidden_strings.extend([b"/sys/class/usb_role", b"phase=usb_role_done"])
    if not stage.ssusb_speed_high_speed:
        forbidden_strings.append(b"phase=ssusb_speed")
        if not stage.typec_readback_markers:
            forbidden_strings.append(b"/sys/devices/platform/soc/a600000.ssusb/speed")
    if not stage.ssusb_mode_peripheral:
        forbidden_strings.extend([b"/sys/devices/platform/soc/a600000.ssusb/mode", b"phase=ssusb_mode", b"value=peripheral"])
    if not stage.udc_bind:
        forbidden_strings.extend([b"/sys/class/udc", b"a600000.dwc3", b"phase=udc_bind"])
    if not stage.soft_connect:
        forbidden_strings.extend([b"/sys/class/udc/a600000.dwc3/soft_connect", b"phase=soft_connect"])
    if not stage.typec_readback_markers:
        forbidden_strings.extend(
            [
                b"/sys/class/typec/port0/power_role",
                b"/sys/class/typec/port0/port_type",
                b"/sys/class/typec/port0-partner/uevent",
                b"typec_pre_bind",
                b"typec_post_bind",
                b"udc_pre_bind",
                b"udc_post_bind",
            ]
        )
        if not stage.beacon_probe:
            forbidden_strings.append(b"/sys/class/typec/port0")
        if not stage.udc_bind:
            forbidden_strings.extend([b"/sys/class/udc/a600000.dwc3/state", b"/sys/class/udc/a600000.dwc3/current_speed", b"/sys/class/udc/a600000.dwc3/function"])
    if not stage.geni_i2c_transport_parity:
        forbidden_strings.extend([b"geni_i2c_transport=1", b"i2c_msm_geni=1", b"gpi_dma=1", b"msm_geni_se=1"])
    if not stage.typec_role_write_discriminator:
        forbidden_strings.extend([b"role_write_discriminator=1", b"phase=typec_partner_check", b"phase=typec_role_write", b"role_device_rc=", b"role_sink_rc="])

    binary = out_path.read_bytes()
    for required in required_strings:
        if required.encode("ascii") not in binary:
            raise SystemExit(f"required marker missing from M34 {stage.label} /init: {required}")
    for forbidden in forbidden_strings:
        if forbidden in binary:
            raise SystemExit(f"M34 {stage.label} /init contains forbidden string: {forbidden!r}")

    (build_dir / f"{stage.lower}_init_file.txt").write_bytes(file_info.stdout + file_info.stderr)
    (build_dir / f"{stage.lower}_init_readelf.txt").write_text(readelf_text, encoding="utf-8")
    (build_dir / f"{stage.lower}_init_objdump.txt").write_text(objdump_text, encoding="utf-8")
    return {
        "file": (file_info.stdout + file_info.stderr).decode("utf-8", errors="replace").strip(),
        "required_strings": required_strings,
        "readelf_path": f"build/{stage.lower}_init_readelf.txt",
        "objdump_path": f"build/{stage.lower}_init_objdump.txt",
    }


def build_stage(
    *,
    root: Path,
    out_dir: Path,
    base_boot: Path,
    template_source: Path,
    magiskboot: Path,
    closure: dict[str, Any],
    stage: RuntimeStage,
) -> dict[str, Any]:
    stage_dir = out_dir / stage.label
    build_dir = stage_dir / "build"
    work_dir = stage_dir / "magiskboot-work"
    patched_unpack_dir = stage_dir / "patched-unpack"
    odin_dir = stage_dir / "odin4"
    for directory in (build_dir, work_dir, patched_unpack_dir, odin_dir):
        directory.mkdir(parents=True)

    stage_closure = json.loads(json.dumps(closure))
    module_list = build_dir / stage.modules_ramdisk
    module_list.write_text(str(stage_closure["module_text"]), encoding="ascii")
    stage_closure["module_sha256"] = sha256_file(module_list)

    init_out = build_dir / stage.init_name
    init_info = compile_init(template_source, init_out, build_dir, stage, int(stage_closure["module_count"]))

    unpack_text = run_in_dir([magiskboot, "unpack", "-h", base_boot], work_dir, f"M34 {stage.label} unpack")
    ramdisk = work_dir / "ramdisk.cpio"
    kernel = work_dir / "kernel"
    header = work_dir / "header"
    original_init = build_dir / "init.magisk.original"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {original_init}"], work_dir, f"M34 {stage.label} extract original init")
    original_init_sha = sha256_file(original_init)
    if original_init_sha != EXPECTED_ORIGINAL_MAGISK_INIT_SHA256:
        raise SystemExit(f"original Magisk /init SHA mismatch for M34 {stage.label}: {original_init_sha}")

    ramdisk_before = build_dir / "ramdisk.before.cpio"
    shutil.copy2(ramdisk, ramdisk_before)
    cpio_test_before = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_before != 1:
        raise SystemExit(f"expected Magisk ramdisk cpio test rc=1 for M34 {stage.label}, got {cpio_test_before}")

    patch_init_text = run_in_dir([magiskboot, "cpio", ramdisk, f"add 750 init {init_out}"], work_dir, f"M34 {stage.label} replace /init")
    patch_modules_text = run_in_dir(
        [magiskboot, "cpio", ramdisk, f"add 640 {stage.modules_ramdisk} {module_list}"],
        work_dir,
        f"M34 {stage.label} add module list",
    )
    cpio_test_after = run([magiskboot, "cpio", ramdisk, "test"], cwd=work_dir).returncode
    if cpio_test_after not in (1, 2):
        raise SystemExit(f"unexpected ramdisk cpio test rc after M34 {stage.label} patch: {cpio_test_after}")

    extracted_init = build_dir / "init.replaced"
    run_in_dir([magiskboot, "cpio", ramdisk, f"extract init {extracted_init}"], work_dir, f"M34 {stage.label} extract replaced init")
    if sha256_file(extracted_init) != sha256_file(init_out):
        raise SystemExit(f"replaced /init does not match compiled M34 {stage.label} init")
    extracted_modules = build_dir / f"{stage.modules_ramdisk}.extracted"
    run_in_dir(
        [magiskboot, "cpio", ramdisk, f"extract {stage.modules_ramdisk} {extracted_modules}"],
        work_dir,
        f"M34 {stage.label} extract module list",
    )
    if sha256_file(extracted_modules) != sha256_file(module_list):
        raise SystemExit(f"replaced M34 {stage.label} module list does not match builder output")

    ramdisk_after = build_dir / "ramdisk.after.cpio"
    shutil.copy2(ramdisk, ramdisk_after)
    boot_img = stage_dir / "boot.img"
    repack_text = run_in_dir([magiskboot, "repack", base_boot, boot_img], work_dir, f"M34 {stage.label} repack patched boot")
    if boot_img.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"M34 {stage.label} patched boot size mismatch: {boot_img.stat().st_size} != {BOOT_PARTITION_SIZE}")
    run_in_dir([magiskboot, "unpack", "-h", boot_img], patched_unpack_dir, f"M34 {stage.label} unpack patched boot")
    if sha256_file(patched_unpack_dir / "kernel") != sha256_file(kernel):
        raise SystemExit(f"M34 {stage.label} patched boot kernel changed")

    boot_lz4 = odin_dir / "boot.img.lz4"
    write_boot_lz4(boot_img, boot_lz4)
    ap_tar = odin_dir / "AP.tar"
    ap_md5 = odin_dir / "AP.tar.md5"
    write_ap_tar(boot_lz4, ap_tar, ap_md5)
    members = tar_members(ap_md5)
    if members != ["boot.img.lz4"]:
        raise SystemExit(f"M34 {stage.label} AP tar member mismatch: {members}")

    hashes = {
        "base_boot": sha256_file(base_boot),
        "original_magisk_init": original_init_sha,
        "m34_modules": sha256_file(module_list),
        "m34_init": sha256_file(init_out),
        "ramdisk_before": sha256_file(ramdisk_before),
        "ramdisk_after": sha256_file(ramdisk_after),
        "kernel": sha256_file(kernel),
        "header": sha256_file(header),
        "boot_img": sha256_file(boot_img),
        "boot_img_lz4": sha256_file(boot_lz4),
        "ap_tar": sha256_file(ap_tar),
        "ap_tar_md5": sha256_file(ap_md5),
    }
    sizes = {
        "m34_modules": module_list.stat().st_size,
        "m34_init": init_out.stat().st_size,
        "original_magisk_init": original_init.stat().st_size,
        "ramdisk_before": ramdisk_before.stat().st_size,
        "ramdisk_after": ramdisk_after.stat().st_size,
        "boot_img": boot_img.stat().st_size,
        "boot_img_lz4": boot_lz4.stat().st_size,
        "ap_tar": ap_tar.stat().st_size,
        "ap_tar_md5": ap_md5.stat().st_size,
    }
    stage_manifest = {
        "label": stage.label,
        "stage_number": stage.number,
        "purpose": stage.purpose,
        "runtime_steps": {
            "configfs_gadget": stage.configfs_gadget,
            "udc_none": stage.udc_none,
            "max_speed_high_speed": stage.max_speed_high_speed,
            "usb_role_force": stage.usb_role_force,
            "ssusb_speed_high_speed": stage.ssusb_speed_high_speed,
            "ssusb_mode_peripheral": stage.ssusb_mode_peripheral,
            "udc_bind": stage.udc_bind,
            "soft_connect": stage.soft_connect,
            "stock_softdep_parity": stage.stock_softdep_parity,
            "qmp_module_included": stage.qmp_module_included,
            "eud_module_included": stage.eud_module_included,
            "ucsi_glink_included": stage.ucsi_glink_included,
            "session_producer_parity": stage.session_producer_parity,
            "max77705_session_modules_included": stage.max77705_session_modules_included,
            "typec_readback_markers": stage.typec_readback_markers,
            "geni_i2c_transport_parity": stage.geni_i2c_transport_parity,
            "typec_role_write_discriminator": stage.typec_role_write_discriminator,
            "beacon_probe": stage.beacon_probe,
            "module_load_probe": stage.module_load_probe,
        },
        "closure": stage_closure,
        "paths": {
            "stage_dir": display_path(root, stage_dir),
            "template_source": display_path(root, template_source),
            "boot_img": display_path(root, boot_img),
            "ap_tar_md5": display_path(root, ap_md5),
            "module_list": display_path(root, module_list),
        },
        "hashes": hashes,
        "sizes": sizes,
        "init": init_info,
        "ramdisk": {
            "cpio_test_before_rc": cpio_test_before,
            "cpio_test_after_rc": cpio_test_after,
            "replaced_entry": "init",
            "replaced_entry_mode": "750",
            "added_subset_entry": stage.modules_ramdisk,
            "added_subset_entry_mode": "640",
            "module_files_injected_into_boot_ramdisk": 0,
            "module_list_files_injected_into_boot_ramdisk": 1,
        },
        "magiskboot": {
            "unpack_output": unpack_text,
            "repack_output": repack_text,
            "patch_output": patch_init_text + "\n" + patch_modules_text,
        },
        "boot_diff_vs_base": diff_ranges(base_boot, boot_img),
        "tar_members": members,
    }
    (stage_dir / "manifest.json").write_text(json.dumps(stage_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return stage_manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--base-boot", type=Path, default=DEFAULT_BASE_BOOT)
    parser.add_argument("--template-source", type=Path, default=DEFAULT_TEMPLATE_SOURCE)
    parser.add_argument("--vendor-ramdisk", type=Path, default=DEFAULT_VENDOR_RAMDISK)
    parser.add_argument("--lz4", type=Path, default=DEFAULT_LZ4)
    parser.add_argument("--magiskboot", type=Path, default=DEFAULT_MAGISKBOOT)
    parser.add_argument("--magisk-apk", type=Path, default=DEFAULT_MAGISK_APK)
    parser.add_argument("--stages", nargs="*", default=[stage.label for stage in STAGES])
    parser.add_argument("--force", action="store_true", help="remove an existing output directory first")
    args = parser.parse_args(argv)

    root = repo_root()
    out_dir = resolve(root, args.out)
    base_boot = resolve(root, args.base_boot)
    template_source = resolve(root, args.template_source)
    vendor_ramdisk = resolve(root, args.vendor_ramdisk)
    lz4_tool = resolve(root, args.lz4)
    magiskboot = resolve(root, args.magiskboot)
    magisk_apk = resolve(root, args.magisk_apk)
    selected_stages = [_stage_by_label(label) for label in args.stages]

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory exists; pass --force to replace: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    common_build_dir = out_dir / "build"
    nochange_dir = out_dir / "nochange-probe"
    common_build_dir.mkdir()
    nochange_dir.mkdir()

    ensure_magiskboot(magiskboot, magisk_apk)
    base_sha = sha256_file(base_boot)
    if base_sha != EXPECTED_BASE_BOOT_SHA256:
        raise SystemExit(f"base Magisk boot SHA mismatch: {base_sha}")
    if base_boot.stat().st_size != BOOT_PARTITION_SIZE:
        raise SystemExit(f"base boot size mismatch: {base_boot.stat().st_size} != {BOOT_PARTITION_SIZE}")

    vendor_metadata = m23.extract_vendor_metadata(vendor_ramdisk, lz4_tool, common_build_dir)
    m32_closure = dependency_complete_wdt_hs_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
    )
    if m32_closure["modules"] != EXPECTED_M32_MODULES:
        raise SystemExit("M34 closure drifted from P30/M32 full ACM module closure")
    stock_softdep_closure = dependency_complete_stock_softdep_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
        base_closure=m32_closure,
    )
    session_producer_closure = dependency_complete_session_producer_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
        base_closure=stock_softdep_closure,
    )
    session_producer_i2c_closure = dependency_complete_session_producer_i2c_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
        base_closure=stock_softdep_closure,
    )
    devlink_supplier_i2c_closure = dependency_complete_devlink_supplier_i2c_order(
        dep_map=vendor_metadata["dep_map"],
        recovery_basenames=vendor_metadata["recovery_basenames"],
        base_closure=session_producer_i2c_closure,
    )
    closure_by_stage = {
        stage.label: (
            devlink_supplier_i2c_closure
            if stage.devlink_supplier_closure
            else session_producer_i2c_closure
            if stage.geni_i2c_transport_parity
            else session_producer_closure
            if stage.session_producer_parity
            else stock_softdep_closure
            if stage.stock_softdep_parity
            else m32_closure
        )
        for stage in selected_stages
    }

    run_in_dir([magiskboot, "unpack", "-h", base_boot], nochange_dir, "M34 no-change unpack")
    run_in_dir([magiskboot, "repack", base_boot, out_dir / "boot_nochange_repack.img"], nochange_dir, "M34 no-change repack")
    nochange_sha = sha256_file(out_dir / "boot_nochange_repack.img")
    if nochange_sha != base_sha:
        raise SystemExit(f"M34 no-change repack is not byte-identical: {nochange_sha} != {base_sha}")

    stage_manifests = [
        build_stage(
            root=root,
            out_dir=out_dir,
            base_boot=base_boot,
            template_source=template_source,
            magiskboot=magiskboot,
            closure=closure_by_stage[stage.label],
            stage=stage,
        )
        for stage in selected_stages
    ]

    hashes: dict[str, str] = {
        "template_source": sha256_file(template_source),
        "base_boot": base_sha,
        "nochange_repack_boot": nochange_sha,
    }
    for stage_manifest in stage_manifests:
        label = stage_manifest["label"]
        for key in ("boot_img", "boot_img_lz4", "ap_tar", "ap_tar_md5", "m34_init", "m34_modules"):
            hashes[f"{label}.{key}"] = stage_manifest["hashes"][key]
    any_download_probe = any(stage.beacon_probe or stage.module_load_probe for stage in selected_stages)

    manifest: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": "SM-S906N/g0q/S906NKSS7FYG8",
            "purpose": (
                "M34 stock-ordered runtime gadget split plus S4 ssusb role-lever, S5 soft_connect, "
                "S6 stock-speed QMP/EUD/ucsi, S7A max77705/PDIC/altmode session-producer, "
                "S7A2 GENI I2C transport, S8B1 exact-bus download beacon, S8B1A widened "
                "I2C-device download beacon, S9 devlink-supplier substrate B1, S10A "
                "/proc/modules all-core beacon, S10B prefix-bisection module-load "
                "beacon, S10C direct-finit loader-audit, and S11P0 /proc/modules "
                "positive-control host-build candidates"
            ),
        "stock_recipe_report": "docs/reports/S22PLUS_STOCK_USB_GADGET_ACM_RECIPE_2026-07-09.md",
        "stages": stage_manifests,
        "matrix": {
            "stages": [
                {
                    "label": stage.label,
                    "stage_number": stage.number,
                    "purpose": stage.purpose,
                    "configfs_gadget": stage.configfs_gadget,
                    "udc_none": stage.udc_none,
                    "max_speed_high_speed": stage.max_speed_high_speed,
                    "usb_role_force": stage.usb_role_force,
                    "ssusb_speed_high_speed": stage.ssusb_speed_high_speed,
                    "ssusb_mode_peripheral": stage.ssusb_mode_peripheral,
                    "udc_bind": stage.udc_bind,
                    "soft_connect": stage.soft_connect,
                    "stock_softdep_parity": stage.stock_softdep_parity,
                    "qmp_module_included": stage.qmp_module_included,
                    "eud_module_included": stage.eud_module_included,
                    "ucsi_glink_included": stage.ucsi_glink_included,
                    "session_producer_parity": stage.session_producer_parity,
                    "max77705_session_modules_included": stage.max77705_session_modules_included,
                    "typec_readback_markers": stage.typec_readback_markers,
                    "geni_i2c_transport_parity": stage.geni_i2c_transport_parity,
                    "typec_role_write_discriminator": stage.typec_role_write_discriminator,
                    "beacon_probe": stage.beacon_probe,
                    "module_load_probe": stage.module_load_probe,
                    "devlink_supplier_closure": stage.devlink_supplier_closure,
                }
                for stage in selected_stages
            ],
            "live_order": ["S1", "S2", "S3", "S4", "S5", "S6"],
            "host_build_order": [stage.label for stage in selected_stages],
            "next_host_only_candidate": "S11P0",
            "p30_is_s0": True,
            "module_closure_matches_p30_and_m32_for_s1_s5": True,
            "s6_module_closure_restores_stock_dwc3_softdep": True,
            "s6_stock_softdep_targets": list(M34_S6_STOCK_SOFTDEP_TARGETS),
            "s6_stock_softdep_new_modules": list(M34_S6_EXPECTED_NEW_MODULES),
            "s7a_module_closure_restores_stock_session_producer_chain": True,
            "s7a_session_producer_targets": list(M34_S7A_SESSION_PRODUCER_TARGETS),
            "s7a_session_producer_new_modules": list(M34_S7A_EXPECTED_NEW_MODULES),
            "s7a_risk_modules": list(M34_S7A_RISK_MODULES),
            "s7a_uses_firmware_module_filename_qcom_i2c_pmic": "qcom-i2c-pmic.ko",
            "s7a_keeps_minimal_ss_acm_without_functionfs_or_conn_gadget": True,
            "s7a2_closes_missing_geni_i2c_transport": True,
            "s7a2_geni_i2c_transport_targets": list(M34_S7A2_I2C_GENI_TRANSPORT_TARGETS),
            "s7a2_geni_i2c_transport_order_actual": list(session_producer_i2c_closure["geni_i2c_transport_order_actual"]),
            "s7a2_session_producer_targets": list(M34_S7A_SESSION_PRODUCER_TARGETS),
            "s7a2_session_producer_new_modules": list(M34_S7A2_EXPECTED_NEW_MODULES),
            "s7a2_risk_modules": list(M34_S7A_RISK_MODULES),
            "s7a2_typec_role_write_discriminator": True,
            "s8b1_download_beacon_probe": "typec_port_or_i2c_device",
            "s8b1_true_action": "reboot(download)",
            "s8b1_false_action": "park",
            "s8b1_probe_paths": ["/sys/class/typec/port0", "/sys/bus/i2c/devices/57-0066"],
            "s8b1_keeps_s7a2_module_recipe": True,
            "s8b1_skips_downstream_configfs_and_udc_to_isolate_probe": True,
            "s8b1a_download_beacon_probe": "typec_port_or_i2c_any_0066",
            "s8b1a_true_action": "reboot(download)",
            "s8b1a_false_action": "park",
            "s8b1a_probe_paths": ["/sys/class/typec/port0", "/sys/bus/i2c/devices/*-0066"],
            "s8b1a_keeps_s7a2_module_recipe": True,
            "s8b1a_widens_i2c_adapter_number_assumption": True,
            "s8b1a_skips_downstream_configfs_and_udc_to_isolate_probe": True,
            "s9_download_beacon_probe": "typec_port_or_i2c_any_0066",
            "s9_true_action": "reboot(download)",
            "s9_false_action": "park",
            "s9_probe_paths": ["/sys/class/typec/port0", "/sys/bus/i2c/devices/*-0066"],
            "s9_starts_from_s8b1a_b1_recipe": True,
            "s9_closes_devlink_supplier_substrate": True,
            "s9_devlink_supplier_load_set": list(M34_S9_DEVLINK_SUPPLIER_LOAD_SET),
            "s9_devlink_supplier_targets": list(M34_S9_DEVLINK_SUPPLIER_LOAD_SET),
            "s9_devlink_supplier_new_modules": list(M34_S9_EXPECTED_NEW_MODULES),
            "s9_skips_downstream_configfs_and_udc_to_isolate_probe": True,
            "s10a_module_load_probe": "proc_modules_core_loaded",
            "s10a_true_action": "reboot(download)",
            "s10a_false_action": "park",
            "s10a_core_proc_modules": list(M34_S10A_PROC_MODULES_CORE_NAMES),
            "s10a_starts_from_s9_module_recipe": True,
            "s10a_separates_module_load_from_probe_bind_failure": True,
            "s10a_skips_downstream_configfs_and_udc_to_isolate_module_load": True,
            "s10b_module_load_prefix_ladder": [
                {
                    "label": label,
                    "stage_number": number,
                    "module_load_probe": f"proc_modules_prefix_{len(modules)}",
                    "prefix_index": index,
                    "prefix_expected": len(modules),
                    "prefix_modules": list(modules),
                }
                for index, (label, number, modules) in enumerate(M34_S10B_PROC_MODULE_PREFIXES)
            ],
            "s10b_true_action": "reboot(download)",
            "s10b_false_action": "park",
            "s10b_starts_from_s9_module_recipe": True,
            "s10b_bisects_s10a_all_core_miss": True,
            "s10b_skips_downstream_configfs_and_udc_to_isolate_module_load": True,
            "s10c0_module_load_probe": "finit_cmd_db_accepted",
            "s10c0_probe_module": M34_S10C0_PROBE_MODULE,
            "s10c0_probe_proc_name": M34_S10C0_PROBE_PROC_NAME,
            "s10c0_true_action": "reboot(download)",
            "s10c0_false_action": "park",
            "s10c0_starts_from_s9_module_recipe": True,
            "s10c0_avoids_proc_modules_dependency": True,
            "s10c0_uses_direct_finit_module_rc": True,
            "s10c0_beacon_hit_means_cmd_db_finit_accepted": True,
            "s10c0_skips_downstream_configfs_and_udc_to_isolate_module_load": True,
            "s11p0_module_load_probe": M34_S11P0_MODULE_LOAD_PROBE,
            "s11p0_probe_module": M34_S10C0_PROBE_MODULE,
            "s11p0_probe_proc_name": M34_S10C0_PROBE_PROC_NAME,
            "s11p0_positive_control_proc_names": list(M34_S11P0_POSITIVE_CONTROL_PROC_NAMES),
            "s11p0_positive_control_modules": list(M34_S11P0_POSITIVE_CONTROL_MODULES),
            "s11p0_true_action": "reboot(download)",
            "s11p0_false_action": "park",
            "s11p0_starts_from_s10c0_module_recipe": True,
            "s11p0_uses_direct_finit_module_rc": True,
            "s11p0_beacon_hit_means_proc_modules_can_see_watchdog": True,
            "s11p0_skips_downstream_configfs_and_udc_to_isolate_module_load": True,
        },
        "safety": {
            "boot_only": True,
            "host_only_build": True,
            "live_flash_authorized": False,
            "requires_new_sha_pinned_agents_exception_before_flash": True,
            "requires_s7a_specific_live_risk_review": True,
            "base_is_known_booting_magisk_boot": True,
            "construction": "magiskboot unpack/repack; replace ramdisk /init and add one text module list per stage",
            "runtime": "freestanding-raw-syscall",
            "runtime_module_list_buffer_bytes": RUNTIME_MODULES_LOAD_BUF,
            "mkbootimg_from_scratch": False,
            "no_android_or_magisk_handoff": True,
            "auto_reboot": "download-if-probe-true" if any_download_probe else False,
            "intended_reboot_syscall": bool(any_download_probe),
            "reboot_request": "download-if-probe-true" if any_download_probe else None,
            "persistent_partition_mount": False,
            "block_device_writes": False,
            "module_binary_injection": False,
            "module_files_injected_into_boot_ramdisk": 0,
            "watchdog_managed": True,
            "qmp_module_excluded_for_s1_s5": True,
            "eud_module_excluded_for_s1_s5": True,
            "ucsi_glink_excluded_for_s1_s5": True,
            "stage_s6_includes_qmp_eud_ucsi_softdep_parity": True,
            "stage_s6_no_high_speed_force": True,
            "stage_s6_no_soft_connect": True,
            "stage_s6_no_eud_sysfs_write": True,
            "stock_order_udc_none_before_ids_and_link": True,
            "stock_order_udc_bind_last": True,
            "stage_s1_no_max_speed_high_speed": True,
            "stage_s1_no_role_force": True,
            "stage_s1_no_udc_bind": True,
            "stage_s2_sets_max_speed_high_speed": True,
            "stage_s2_no_udc_bind": True,
            "stage_s3_binds_only_a600000_dwc3": True,
            "stage_s4_replaces_dead_usb_role_with_ssusb_role_lever": True,
            "stage_s4_sets_ssusb_speed_high_speed_before_udc_bind": True,
            "stage_s4_sets_ssusb_mode_peripheral_before_udc_bind": True,
            "stage_s4_no_usb_role_force": True,
            "stage_s5_soft_connect_after_udc_bind": True,
            "stage_s5_no_descriptor_or_companion_change": True,
            "stage_s6_restores_stock_speed_policy": True,
            "stage_s6_keeps_ssusb_mode_peripheral_before_udc_bind": True,
            "stage_s6_no_descriptor_or_companion_change": True,
            "stage_s7a_starts_from_s6": True,
            "stage_s7a_restores_max77705_pdic_altmode_session_producer_chain": True,
            "stage_s7a_adds_typec_udc_readback_markers": True,
            "stage_s7a_keeps_ssusb_mode_peripheral_before_udc_bind": True,
            "stage_s7a_no_high_speed_force": True,
            "stage_s7a_no_soft_connect": True,
            "stage_s7a_no_functionfs_or_conn_gadget": True,
            "stage_s7a_contains_sec_debug_region_due_stock_charger_dependency": True,
            "stage_s7a2_starts_from_s7a": True,
            "stage_s7a2_adds_geni_i2c_transport": True,
            "stage_s7a2_geni_i2c_transport_order_dep_safe": True,
            "stage_s7a2_role_write_discriminator_if_no_partner": True,
            "stage_s7a2_keeps_minimal_ss_acm_without_functionfs_or_conn_gadget": True,
            "stage_s7a2_no_high_speed_force": True,
            "stage_s7a2_no_soft_connect": True,
            "stage_s7a2_no_charge_otg_rail_gpio_writes": True,
            "stage_s8b1_starts_from_s7a2_module_recipe": True,
            "stage_s8b1_beacon_probe": "typec_port_or_i2c_device",
            "stage_s8b1_true_reboot_download_false_park": True,
            "stage_s8b1_no_configfs_udc_or_role_write": True,
            "stage_s8b1a_starts_from_s7a2_module_recipe": True,
            "stage_s8b1a_beacon_probe": "typec_port_or_i2c_any_0066",
            "stage_s8b1a_true_reboot_download_false_park": True,
            "stage_s8b1a_no_configfs_udc_or_role_write": True,
            "stage_s8b1a_widens_i2c_adapter_number_assumption": True,
            "stage_s9_starts_from_s8b1a_b1_recipe": True,
            "stage_s9_closes_devlink_supplier_substrate": True,
            "stage_s9_beacon_probe": "typec_port_or_i2c_any_0066",
            "stage_s9_true_reboot_download_false_park": True,
            "stage_s9_no_configfs_udc_or_role_write": True,
            "stage_s9_driver_load_only_no_manual_power_write": True,
            "stage_s10a_starts_from_s9_module_recipe": True,
            "stage_s10a_module_load_probe": "proc_modules_core_loaded",
            "stage_s10a_core_proc_modules": list(M34_S10A_PROC_MODULES_CORE_NAMES),
            "stage_s10a_true_reboot_download_false_park": True,
            "stage_s10a_no_configfs_udc_or_role_write": True,
            "stage_s10a_driver_load_only_no_manual_power_write": True,
            "stage_s10a_separates_module_load_from_probe_bind_failure": True,
            "stage_s10b_starts_from_s9_module_recipe": True,
            "stage_s10b_module_load_prefix_ladder": [
                {
                    "label": label,
                    "stage_number": number,
                    "module_load_probe": f"proc_modules_prefix_{len(modules)}",
                    "prefix_index": index,
                    "prefix_expected": len(modules),
                    "prefix_modules": list(modules),
                }
                for index, (label, number, modules) in enumerate(M34_S10B_PROC_MODULE_PREFIXES)
            ],
            "stage_s10b_true_reboot_download_false_park": True,
            "stage_s10b_no_configfs_udc_or_role_write": True,
            "stage_s10b_driver_load_only_no_manual_power_write": True,
            "stage_s10b_bisects_s10a_all_core_miss": True,
            "stage_s10c0_starts_from_s9_module_recipe": True,
            "stage_s10c0_module_load_probe": "finit_cmd_db_accepted",
            "stage_s10c0_probe_module": M34_S10C0_PROBE_MODULE,
            "stage_s10c0_true_reboot_download_false_park": True,
            "stage_s10c0_no_proc_modules_dependency": True,
            "stage_s10c0_no_configfs_udc_or_role_write": True,
            "stage_s10c0_driver_load_only_no_manual_power_write": True,
            "stage_s11p0_starts_from_s10c0_module_recipe": True,
            "stage_s11p0_module_load_probe": M34_S11P0_MODULE_LOAD_PROBE,
            "stage_s11p0_positive_control_proc_names": list(M34_S11P0_POSITIVE_CONTROL_PROC_NAMES),
            "stage_s11p0_true_reboot_download_false_park": True,
            "stage_s11p0_no_configfs_udc_or_role_write": True,
            "stage_s11p0_driver_load_only_no_manual_power_write": True,
        },
        "vendor": {
            "vendor_ramdisk": display_path(root, vendor_ramdisk),
            "vendor_ramdisk_sha256": sha256_file(vendor_ramdisk),
            "metadata_hashes": vendor_metadata["metadata_hashes"],
            "modules_load_count": vendor_metadata["modules_load_count"],
            "modules_load_recovery_count": vendor_metadata["modules_load_recovery_count"],
            "modules_dep_count": vendor_metadata["modules_dep_count"],
        },
        "paths": {
            "out_dir": display_path(root, out_dir),
            "template_source": display_path(root, template_source),
            "base_boot": display_path(root, base_boot),
        },
        "hashes": hashes,
        "magiskboot": {
            "nochange_repack_byte_identical": True,
        },
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "sha256.txt").write_text("".join(f"{value}  {key}\n" for key, value in sorted(hashes.items())), encoding="ascii")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
