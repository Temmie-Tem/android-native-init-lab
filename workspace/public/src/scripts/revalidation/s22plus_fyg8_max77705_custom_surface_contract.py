#!/usr/bin/env python3
"""Bind the FYG8 Max77705 writable baseline and narrow diagnostic closure.

This is a host-only authority/contract helper.  Its baseline mode proves what
the pinned stock sources and modules expose.  The diagnostic-source validator
is a future packaging prerequisite; declaring this contract does not claim
that a custom module has already been written, built, or qualified.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from s22plus_fyg8_f2fs_module_corpus import FILE_TYPE_REGULAR, F2FSReader


SCHEMA = "s22plus_fyg8_max77705_custom_surface_contract_v2"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
KERNEL_ROOT = Path(
    "workspace/private/work/s22plus_fyg8_kernel_build_p290_2ec2bbae/"
    "kernel_platform/msm-kernel"
)
MODULE_ROOT = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules"
)
VENDOR_RAMDISK = Path(
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
VENDOR_DLKM_IMAGE = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "order-authority-20260811-01/vendor_dlkm.img"
)
LZ4_TOOL = Path("workspace/private/tools/lz4-local/root/usr/bin/lz4")
DUMP_F2FS = Path("workspace/private/tools/f2fs-local/usr/sbin/dump.f2fs")
FIRST_STAGE_INVENTORY = Path("docs/module-map/s22plus-fyg8/inventory.tsv")
VENDOR_DLKM_INVENTORY = Path("docs/module-map/s22plus-fyg8-super/inventory.tsv")
VENDOR_DLKM_MANIFEST = Path("docs/module-map/s22plus-fyg8-super/manifest.json")
P315_PLAN = Path(
    "workspace/private/outputs/s22plus_fyg8_p315/intent/materialized-sources/"
    "s22plus_fyg8_p286_e3_plan.h"
)
DEFAULT_OUTPUT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "custom-surface-authority-20260811-04.json"
)

VENDOR_RAMDISK_IDENTITY = (
    21_813_545,
    "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193",
)
VENDOR_RAMDISK_CPIO_IDENTITY = (
    63_974_144,
    "a96c362103eeab52fd639fd1bfc06d5f9a30972a18d8086c26d20a86a0309afd",
)
VENDOR_DLKM_IDENTITY = (
    57_610_240,
    "e5386d68ccf9ad1a12cfa4cf447e704bddcef94b0442e61765f3dba580186b26",
)
LZ4_IDENTITY = (
    115_032,
    "4be960d6f6b0d7ef69e01a9e1a056591c17b8687e9851db128018b2ac5f01da0",
)
DUMP_F2FS_SHA256 = "66db38ca0ea8239cab0c335e142ee34751824352eaa494b3654fa7d663b86669"
FIRST_STAGE_INVENTORY_SHA256 = "35f1a7b903fc3582d3d51c4f119b993d154874e632465b2e212e0bf56a37ab7b"
VENDOR_DLKM_INVENTORY_SHA256 = "5ad69e151efbe48ba0348608120da3001f9e11d481b13a498177e080771c6d37"
VENDOR_DLKM_MANIFEST_SHA256 = "c23077120499012db4d492d5b494c1f69274486e5bbf7a15ec3f192dbdd71092"
EXPECTED_FIRST_STAGE_MODULES = 441
EXPECTED_VENDOR_DLKM_MODULES = 356
EXPECTED_VENDOR_DLKM_ONLY_MODULES = 50
EXPECTED_STOCK_UNION_MODULES = 491
P315_PLAN_IDENTITY = (
    4_707,
    "d5ec1423cd47aba29c935512690c4e0b9af3302e4df1b91e50ed1cc816199005",
)
EXPECTED_P315_MODULES = 61
MIN_TEMP_FREE_BYTES = 512 << 20

SOURCE_IDENTITIES = {
    "mfd": (
        Path("drivers/mfd/maxim/max77705.c"),
        40_632,
        "523fe8b765f53b775efc9f51a9cc1ddfc67088e8375894fe43d273bbde23db46",
    ),
    "pdic": (
        Path("drivers/usb/typec/maxim/max77705_usbc.c"),
        124_569,
        "4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d",
    ),
    "debug": (
        Path("drivers/usb/typec/maxim/max77705_debug.c"),
        10_904,
        "47f423efdf8f6ffde06ce3665f82bfc36fa6f79c5f58f95b2330da5ecdd29210",
    ),
    "pdic_makefile": (
        Path("drivers/usb/typec/maxim/Makefile"),
        450,
        "8055a9480971e835edccb441ce0554940a1d211be5bc1d1702ebc4587580c91d",
    ),
    "pdic_header": (
        Path("include/linux/usb/typec/maxim/max77705_usbc.h"),
        10_072,
        "1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e",
    ),
    "muic_header": (
        Path("include/linux/usb/typec/maxim/max77705-muic.h"),
        13_948,
        "3f7f2b9790940d61ec6bb636f87fd750f7971f1c609c06e6380d11907f701cb1",
    ),
    "usbc_register_header": (
        Path("include/linux/usb/typec/maxim/max77705.h"),
        13_686,
        "ff2498061ddb20c1891cb9fe6611edde655c3e1cda8fa4446d0c876a476ff1c7",
    ),
    "mfd_private_header": (
        Path("include/linux/mfd/max77705-private.h"),
        13_063,
        "a205dfc0743d38f7684a046f5aef26d466f5feef3713fe0d19bc58134a7c441e",
    ),
    "pdic_misc": (
        Path("drivers/usb/typec/common/pdic_misc.c"),
        16_791,
        "ec24080f7102a52ce94a44ec72b3c51358e3d3f18f4c871a9de1c41bbb8e49f6",
    ),
    "pdic_core": (
        Path("drivers/usb/typec/common/pdic_core.c"),
        4_632,
        "86d256315f7080c3d68f19da40e4c207c8965010934adcb3cd32554fb5e2082f",
    ),
    "pdic_sysfs": (
        Path("drivers/usb/typec/common/pdic_sysfs.c"),
        5_624,
        "18af12002f8e89453feaec33fabc1ce4f024e638152f5110079a03d97127abcf",
    ),
    "max77705_muic": (
        Path("drivers/usb/typec/maxim/max77705-muic.c"),
        76_141,
        "bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab",
    ),
    "max77705_cc": (
        Path("drivers/usb/typec/maxim/max77705_cc.c"),
        27_233,
        "45bd6c7c782e3ba80b4140a4ee257ac39e8ad3876a4691b1843b85dc46acccdb",
    ),
    "max77705_pd": (
        Path("drivers/usb/typec/maxim/max77705_pd.c"),
        62_385,
        "4818b54be4a4616f44ed3e993cf9e5e55d394b966b0202a1c6616c59cfce47ac",
    ),
    "max77705_alternate": (
        Path("drivers/usb/typec/maxim/max77705_alternate.c"),
        64_610,
        "d6812fd27e0612d8c09a1462b9a39c4b1aee0d0eb0bc88f81611bb97e79a4228",
    ),
    "max77705_muic_afc": (
        Path("drivers/usb/typec/maxim/max77705-muic-afc.c"),
        26_164,
        "7b8a775af9fa13f65a042a651e87b6d4cb4e5e735f43e358a5d04d89bd88e4d5",
    ),
    "max77705_muic_ccic": (
        Path("drivers/usb/typec/maxim/max77705-muic-ccic.c"),
        9_519,
        "6cdb78864ce17eb1a70c093a73fd993f62884d4eabafb0b02813eb1b0eadff80",
    ),
    "max77705_irq": (
        Path("drivers/mfd/maxim/max77705-irq.c"),
        16_518,
        "5ddbe1dee81c5756fc86c8c47264d77b4049c1ca7063647abbdc5c1cbc5cfabc",
    ),
    "waipio_vendor_defconfig": (
        Path("arch/arm64/configs/vendor/waipio-gki_defconfig"),
        35_621,
        "de7373038099658387dea7f2168be3c63268c554c645067e255492cb836276c7",
    ),
    "common_muic_sysfs": (
        Path("drivers/muic/common/muic_sysfs.c"),
        19_090,
        "eaa86d77f2ae0d8e554aa80a68a87afaba797fe63d5c8f7ae2cfff9a7b7d2f80",
    ),
    "common_muic_core": (
        Path("drivers/muic/common/muic-core.c"),
        16_794,
        "962d841eb2e8097eefc79a0769b844c168f4d21c37f7fc3d0365ae72b224eec1",
    ),
    "typec_class": (
        Path("drivers/usb/typec/class.c"),
        57_131,
        "992f17dc0e69f96b77d477d9e47dd4ad46e205683ade0533fbf54279e885508c",
    ),
    "if_cb_manager": (
        Path("drivers/usb/typec/manager/if_cb_manager.c"),
        5_164,
        "044b2b6aae5e9c9c042f5c9c2d5ecba53d275639057002893306b0106b554f6f",
    ),
    "dwc3_msm": (
        Path("drivers/usb/dwc3/dwc3-msm-core.c"),
        204_659,
        "1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021",
    ),
    "i2c_core": (
        Path("drivers/i2c/i2c-core-base.c"),
        68_341,
        "0292f223758b3d9eb74889e986cf2e67588b97874d54bcfbf257b15a5906ffa5",
    ),
    "firmware": (
        Path("include/linux/mfd/firmware/max77705C_pass2_specific.h"),
        318_415,
        "6c21e9ff8fdc9fdd29f994867bb6bab5a79a024e4c481cbf58c69eb51fb33d96",
    ),
}
MODULE_IDENTITIES = {
    "mfd_max77705.ko": (
        125_840,
        "26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94",
    ),
    "pdic_max77705.ko": (
        423_456,
        "27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db",
    ),
}

MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC = (
    "BOOT_FLASH_FW_PASS2",
    "max77705_usbc_fw_setting",
    "max77705_usbc_fw_update",
)
PDIC_UPDATE_IMPORTS = frozenset(
    {
        "BOOT_FLASH_FW_PASS2",
        "max77705_usbc_fw_setting",
        "max77705_usbc_fw_update",
        "request_firmware",
        "spu_firmware_signature_verify",
    }
)
PDIC_WRITABLE_DEFINED_SYMBOLS = frozenset(
    {
        "max77705_firmware_update_callback",
        "max77705_firmware_update_sysfs",
        "max77705_firmware_update_sysfs_work",
        "max77705_fw_update",
        "mxim_debug_init",
        "mxim_debug_ioctl",
        "mxim_debug_reg_store",
        "mxim_debug_opcode_store",
    }
)
PDIC_CONTROL_EXPORT_CONSUMERS = {
    "blocking_auto_vbus_control": [],
    "check_usbc_opcode_queue": [],
    "max77705_usbc_icurr": ["max77705_charger.ko"],
    "max77705_set_fw_noautoibus": ["max77705_charger.ko"],
    "max77705_set_fw_ship_mode": ["max77705_charger.ko"],
    "max77705_get_fw_ship_mode": ["max77705_charger.ko"],
    "pdic_manual_ccopen_request": [],
    "mxim_debug_init": [],
    "mxim_debug_exit": [],
    "mxim_debug_set_i2c_client": [],
}
IF_CB_EXPORT_CONSUMERS = {
    "register_usb": ["dwc3-msm.ko"],
    "register_muic": ["pdic_max77705.ko"],
    "register_usbpd": ["pdic_max77705.ko"],
    "register_lvs": ["lvstest.ko"],
    "usb_set_vbus_current": ["pdic_max77705.ko"],
    "muic_check_usb_killer": [],
    "muic_set_bc12": [],
    "usbpd_sbu_test_read": [],
    "usbpd_set_host_on": ["dwc3-msm.ko"],
    "usbpd_cc_control_command": [],
    "usbpd_wait_entermode": ["lvstest.ko"],
}
P315_FORBIDDEN_CONTROL_CONSUMERS = frozenset(
    {
        "sec_pd.ko",
        "sec-battery.ko",
        "max77705_charger.ko",
        "max77705-fuelgauge.ko",
    }
)
P315_REQUIRED_IF_CB_MODULES = frozenset({"if_cb_manager.ko", "dwc3-msm.ko"})
P315_ABSENT_IF_CB_CONSUMERS = frozenset({"lvstest.ko"})
MAX77705_MUIC_WRITABLE_ATTRIBUTES = (
    "uart_sel",
    "usb_sel",
    "uart_en",
    "otg_test",
    "apo_factory",
    "afc_disable",
    "hiccup",
)
MAX77705_MUIC_READ_ONLY_ATTRIBUTES = (
    "adc",
    "usb_state",
    "attached_dev",
    "vbus_value",
    "vbus_value_pd",
)
MAX77705_TYPEC_MUTATION_CALLBACKS = (
    "max77705_dr_set",
    "max77705_pr_set",
    "max77705_port_type_set",
)
HOST_STATE_CALLBACK_FORBIDDEN_EFFECTS = (
    "max77705_write_reg(",
    "max77705_update_reg(",
    "max77705_usbc_opcode",
    "max77705_switch_path(",
    "queue_work(",
    "schedule_work(",
    "i2c_",
    "regmap_",
    "power_supply_",
    "blocking_notifier_call_chain(",
)

# A future custom builder must import and call validate_diag_source_text()
# before compiling.  A later linked-artifact validator must independently
# establish the corresponding symbol/import properties and control flow.
CUSTOM_PREFERRED_ADDITIONS = (
    "msm-geni-se.ko",
    "gpi.ko",
    "i2c-msm-geni.ko",
    "s22plus_max77705_mux_diag.ko",
)
REJECTED_FULL_PDIC_CUSTOM_ADDITIONS = (
    "msm-geni-se.ko",
    "gpi.ko",
    "i2c-msm-geni.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
)
DIAG_REQUIRED_TOKENS = (
    '#define S22PLUS_MAX77705_PARENT_COMPATIBLE "maxim,max77705"',
    "#define S22PLUS_MAX77705_MUIC_ADDR 0x25",
    "#define S22PLUS_MAX77705_UIC_INT 0x02",
    "#define S22PLUS_MAX77705_AP_DATAOUT0 0x21",
    "#define S22PLUS_MAX77705_AP_DATAOUT_END 0x41",
    "#define S22PLUS_MAX77705_AP_DATAIN0 0x51",
    "#define S22PLUS_MAX77705_AP_CMD_RESPONSE BIT(7)",
    "#define S22PLUS_MAX77705_CONTROL1_READ 0x05",
    "#define S22PLUS_MAX77705_CONTROL1_WRITE 0x06",
    "#define S22PLUS_MAX77705_COM_USB 0x09",
    "#define S22PLUS_MAX77705_POLL_LIMIT",
    "devm_i2c_new_dummy_device",
    "static int s22plus_max77705_clear_uic_latch_once(",
    "static int s22plus_max77705_wait_ap_response(",
    "static int s22plus_max77705_control1_read_once(",
    "static int s22plus_max77705_control1_write_once(",
    "static int s22plus_max77705_diag_run(",
    "static int s22plus_max77705_diag_probe(",
    "if (pre != S22PLUS_MAX77705_COM_USB)",
    "s22plus_max77705_control1_write_once(muic, S22PLUS_MAX77705_COM_USB)",
    ".compatible = S22PLUS_MAX77705_PARENT_COMPATIBLE",
    "module_i2c_driver(",
    "static int s22plus_max77705_result_get(",
    ".set = NULL",
    ".get = s22plus_max77705_result_get",
    "module_param_cb(result",
    "0444",
)
DIAG_FORBIDDEN = (
    "BOOT_FLASH_FW_PASS2",
    "linux/mfd/firmware/",
    "max77705_usbc_fw_update",
    "__max77705_usbc_fw_update",
    "max77705_usbc_wait_response",
    "max77705_reset_ic",
    "MAX77705_SYS_FW_UPDATE",
    "PDIC_SYSFS_PROP_FW_UPDATE",
    "PDIC_SYSFS_PROP_FW_UPDATE_STATUS",
    "max77705_firmware_update_",
    "max77705_usbc_fw_setting",
    "max77705_usbc_fw_update",
    "request_firmware",
    "spu_firmware_signature_verify",
    "pdic_misc_init",
    "mfd_add_devices",
    "mfd_remove_devices",
    "max77705_attr_grp",
    "max77705_fw_update",
    "mxim_debug_",
    "blocking_auto_vbus_control",
    "request_irq(",
    "request_threaded_irq(",
    "devm_request_threaded_irq(",
    "irq_set_",
    "queue_work(",
    "schedule_work(",
    "INIT_WORK(",
    "INIT_DELAYED_WORK(",
    "create_singlethread_workqueue(",
    "blocking_notifier_call_chain(",
    "power_supply_",
    "regulator_",
    "typec_register_port(",
    "register_usbpd(",
    "register_muic(",
    "max77705_muic_probe(",
    "max77705_cc_init(",
    "max77705_pd_init(",
    "max77705_alternate",
    "max77705_muic_afc",
    "max77705_muic_enable_detecting_short",
    "max77705_set_fw_noautoibus",
    "max77705_set_enable_audio",
    "max77705_enable_alternate_mode",
    "max77705_check_pdo",
    "max77705_switch_path(",
    "com_to_usb_ap(",
    "DCD",
    "CHGDET",
    "sysfs_create_group(",
    "DEVICE_ATTR",
    "misc_register(",
    "debugfs_create",
    "proc_create",
    "module_param_named(",
    "module_param_array",
    "EXPORT_SYMBOL",
    "max77705_ops",
    "max77705_dr_set",
    "max77705_pr_set",
    "max77705_port_type_set",
    "max77705_muic_group",
    "max77705_muic_attributes",
    "max77705_muic_set_uart_sel",
    "max77705_muic_set_usb_sel",
    "max77705_muic_set_uart_en",
    "max77705_muic_set_otg_test",
    "max77705_muic_set_apo_factory",
    "max77705_muic_set_afc_disable",
    "hiccup_store",
    "sysfs_create_group(&switch_device->kobj",
    "max77705_usbc_icurr(",
    "max77705_set_fw_ship_mode(",
    "max77705_get_fw_ship_mode(",
    "EXPORT_SYMBOL(max77705_set_fw_noautoibus)",
    "fp_sec_pd_select_pdo = max77705_select_pdo",
    "fp_sec_pd_select_pps = max77705_select_pps",
    "fp_sec_pd_vpdo_auth = max77705_vpdo_auth",
    "fp_sec_pd_manual_ccopen_req = pdic_manual_ccopen_request",
    "fp_sec_pd_change_src = max77705_forced_change_srccap",
)
DIAG_GETTER_FORBIDDEN_EFFECTS = (
    "i2c_",
    "regmap_",
    "queue_work(",
    "schedule_work(",
    "power_supply_",
    "blocking_notifier_call_chain(",
)
DIAG_I2C_CALL_COUNTS = {
    "i2c_smbus_read_byte_data": 4,
    "i2c_smbus_write_i2c_block_data": 2,
    "i2c_smbus_write_byte_data": 2,
    "i2c_smbus_read_i2c_block_data": 1,
}


class SurfaceError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise SurfaceError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path: Path, size: int, digest: str, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SurfaceError(f"{label} is not a direct regular file: {path}")
    actual = (path.stat().st_size, sha256_file(path))
    if actual != (size, digest):
        raise SurfaceError(f"{label} identity mismatch: {actual}")
    return {"path": str(path), "size": actual[0], "sha256": actual[1]}


def validate_tool(path: Path, size: int | None, digest: str, label: str) -> dict[str, Any]:
    """Validate a pinned host tool while preserving a multicall symlink name."""

    if not path.is_file():
        raise SurfaceError(f"{label} is missing or not a regular-file target: {path}")
    actual_size = path.stat().st_size
    actual_digest = sha256_file(path)
    if (size is not None and actual_size != size) or actual_digest != digest:
        raise SurfaceError(
            f"{label} identity mismatch: {(actual_size, actual_digest)}"
        )
    return {
        "path": str(path),
        "size": actual_size,
        "sha256": actual_digest,
        "symlink_argument_preserved": path.is_symlink(),
    }


def parse_inventory(
    path: Path,
    *,
    expected_sha256: str,
    expected_rows: int,
) -> list[dict[str, str]]:
    if sha256_file(path) != expected_sha256:
        raise SurfaceError(f"inventory identity mismatch: {path}")
    with path.open(encoding="ascii", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != expected_rows or any(not row.get("filename") for row in rows):
        raise SurfaceError(
            f"inventory row mismatch for {path}: {len(rows)} != {expected_rows}"
        )
    names = [row["filename"] for row in rows]
    if len(set(names)) != len(names):
        raise SurfaceError(f"duplicate inventory filename in {path}")
    return rows


def parse_p315_plan(root: Path) -> tuple[list[str], dict[str, Any]]:
    path = root / P315_PLAN
    receipt = validate_file(path, *P315_PLAN_IDENTITY, "P3.15 materialized plan")
    text = path.read_text(encoding="ascii")
    match = re.search(
        r"s22plus_o2_module_plan\[\]\s*=\s*\{(.*?)\n\};",
        text,
        re.S,
    )
    if match is None:
        raise SurfaceError("P3.15 module-plan array not found")
    modules = re.findall(
        r'^\s*\{"([^"]+\.ko)",\s*"[^"]+",\s*"[^"]*"\},\s*$',
        match.group(1),
        re.M,
    )
    if len(modules) != EXPECTED_P315_MODULES or len(set(modules)) != len(modules):
        raise SurfaceError(f"P3.15 module-plan geometry mismatch: {len(modules)}")
    forbidden = sorted(P315_FORBIDDEN_CONTROL_CONSUMERS & set(modules))
    if forbidden:
        raise SurfaceError(f"P3.15 unexpectedly contains control consumers: {forbidden}")
    if set(CUSTOM_PREFERRED_ADDITIONS) & set(modules):
        raise SurfaceError("P3.15 already contains one or more custom additions")
    missing_if_cb = sorted(P315_REQUIRED_IF_CB_MODULES - set(modules))
    unexpected_if_cb = sorted(P315_ABSENT_IF_CB_CONSUMERS & set(modules))
    if missing_if_cb or unexpected_if_cb:
        raise SurfaceError(
            "P3.15 IF-callback closure mismatch: "
            f"missing={missing_if_cb} unexpected={unexpected_if_cb}"
        )
    return modules, {
        **receipt,
        "module_count": len(modules),
        "forbidden_control_consumers_absent": sorted(
            P315_FORBIDDEN_CONTROL_CONSUMERS
        ),
        "required_if_cb_modules_present": sorted(P315_REQUIRED_IF_CB_MODULES),
        "inactive_if_cb_consumers_absent": sorted(P315_ABSENT_IF_CB_CONSUMERS),
    }


def source_token_locations(root: Path, token: str) -> list[str]:
    locations: list[str] = []
    needle = token.encode("ascii")
    for path in sorted((root / "drivers").rglob("*.c")):
        if needle in path.read_bytes():
            locations.append(str(path.relative_to(root)))
    return locations


def run_checked(command: list[str], *, cwd: Path | None = None, stdin: Any = None) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        command,
        cwd=cwd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr[-4096:].decode("utf-8", errors="replace")
        raise SurfaceError(f"host command failed rc={result.returncode}: {command}: {stderr}")
    return result


def extract_first_stage_modules(
    vendor_ramdisk: Path,
    lz4: Path,
    inventory_rows: list[dict[str, str]],
    scratch: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    cpio_path = scratch / "vendor_ramdisk.cpio"
    with cpio_path.open("wb") as output:
        result = subprocess.run(
            [str(lz4), "-dc", str(vendor_ramdisk)],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        raise SurfaceError(
            "vendor ramdisk decompression failed: "
            + result.stderr[-4096:].decode("utf-8", errors="replace")
        )
    validate_file(
        cpio_path,
        VENDOR_RAMDISK_CPIO_IDENTITY[0],
        VENDOR_RAMDISK_CPIO_IDENTITY[1],
        "vendor ramdisk cpio",
    )

    with cpio_path.open("rb") as archive:
        listing_result = run_checked(["cpio", "-it"], stdin=archive)
    try:
        listing = listing_result.stdout.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SurfaceError("vendor ramdisk listing is not UTF-8") from exc
    for name in listing:
        parsed = PurePosixPath(name)
        if parsed.is_absolute() or ".." in parsed.parts or str(parsed) != name:
            raise SurfaceError(f"unsafe vendor ramdisk member: {name!r}")
    module_members = sorted(
        name for name in listing
        if name.startswith("lib/modules/") and name.endswith(".ko")
    )
    module_names = [PurePosixPath(name).name for name in module_members]
    if (
        len(module_members) != EXPECTED_FIRST_STAGE_MODULES
        or len(set(module_names)) != EXPECTED_FIRST_STAGE_MODULES
    ):
        raise SurfaceError(f"first-stage module geometry mismatch: {len(module_members)}")

    extract_root = scratch / "first-stage"
    extract_root.mkdir()
    with cpio_path.open("rb") as archive:
        run_checked(
            [
                "cpio",
                "-idm",
                "--quiet",
                "--no-absolute-filenames",
                "lib/modules/*.ko",
            ],
            cwd=extract_root,
            stdin=archive,
        )
    module_dir = extract_root / "lib/modules"
    paths = {
        path.name: path
        for path in module_dir.glob("*.ko")
        if path.is_file() and not path.is_symlink()
    }
    if set(paths) != set(module_names):
        raise SurfaceError("first-stage extracted module set differs from cpio listing")

    expected = {row["filename"]: row for row in inventory_rows}
    if set(expected) != set(paths):
        raise SurfaceError("first-stage tracked inventory differs from exact cpio module set")
    rows_for_hash: list[tuple[str, int, str]] = []
    for name, path in sorted(paths.items()):
        size = path.stat().st_size
        digest = sha256_file(path)
        row = expected[name]
        if (str(size), digest) != (row["size_bytes"], row["sha256"]):
            raise SurfaceError(f"first-stage module identity mismatch: {name}")
        rows_for_hash.append((name, size, digest))
    return paths, {
        "module_count": len(paths),
        "inventory_sha256": FIRST_STAGE_INVENTORY_SHA256,
        "corpus_sha256": canonical_hash(rows_for_hash),
        "cpio_size": cpio_path.stat().st_size,
        "cpio_sha256": sha256_file(cpio_path),
    }


def extract_vendor_dlkm_only_modules(
    image: Path,
    dump_f2fs: Path,
    inventory_rows: list[dict[str, str]],
    scratch: Path,
) -> tuple[dict[str, Path], dict[str, Any]]:
    rows = {
        row["filename"]: row
        for row in inventory_rows
        if row["reference_status"] == "vendor-dlkm-only"
    }
    if len(rows) != EXPECTED_VENDOR_DLKM_ONLY_MODULES:
        raise SurfaceError(f"vendor_dlkm-only inventory mismatch: {len(rows)}")

    reader = F2FSReader(image, dump_f2fs)
    directory_inode = reader.resolve_directory(PurePosixPath("/lib/modules"))
    entries = {
        entry.name: entry
        for entry in reader.directory(directory_inode)
        if entry.name.endswith(".ko")
    }
    if len(entries) != EXPECTED_VENDOR_DLKM_MODULES:
        raise SurfaceError(f"vendor_dlkm module geometry mismatch: {len(entries)}")
    if not set(rows).issubset(entries):
        raise SurfaceError("vendor_dlkm-only inventory has missing image entries")

    extract_root = scratch / "vendor-dlkm-only"
    extract_root.mkdir()
    paths: dict[str, Path] = {}
    rows_for_hash: list[tuple[str, int, str]] = []
    for name, row in sorted(rows.items()):
        entry = entries[name]
        if entry.file_type != FILE_TYPE_REGULAR or entry.inode != int(row["inode"]):
            raise SurfaceError(f"vendor_dlkm dentry mismatch: {name}")
        destination = extract_root / name
        reader.extract_file(entry, destination)
        size = destination.stat().st_size
        digest = sha256_file(destination)
        if (str(size), digest) != (row["size_bytes"], row["sha256"]):
            raise SurfaceError(f"vendor_dlkm-only module identity mismatch: {name}")
        paths[name] = destination
        rows_for_hash.append((name, size, digest))
    return paths, {
        "image_module_count": len(entries),
        "vendor_dlkm_only_count": len(paths),
        "inventory_sha256": VENDOR_DLKM_INVENTORY_SHA256,
        "vendor_dlkm_only_corpus_sha256": canonical_hash(rows_for_hash),
    }


def stock_module_union(root: Path, scratch: Path) -> tuple[dict[str, Path], dict[str, Any]]:
    vendor_ramdisk = root / VENDOR_RAMDISK
    image = root / VENDOR_DLKM_IMAGE
    lz4 = root / LZ4_TOOL
    # Keep the symlink spelling: f2fs-tools selects dump mode from argv[0].
    dump_f2fs = (root / DUMP_F2FS).absolute()
    first_inventory = root / FIRST_STAGE_INVENTORY
    vendor_inventory = root / VENDOR_DLKM_INVENTORY
    vendor_manifest = root / VENDOR_DLKM_MANIFEST

    inputs = {
        "vendor_ramdisk": validate_file(
            vendor_ramdisk, *VENDOR_RAMDISK_IDENTITY, "vendor ramdisk"
        ),
        "vendor_dlkm_image": validate_file(
            image, *VENDOR_DLKM_IDENTITY, "vendor_dlkm image"
        ),
        "lz4": validate_tool(lz4, *LZ4_IDENTITY, "lz4"),
        "dump_f2fs": validate_tool(
            dump_f2fs, None, DUMP_F2FS_SHA256, "dump.f2fs"
        ),
    }
    first_rows = parse_inventory(
        first_inventory,
        expected_sha256=FIRST_STAGE_INVENTORY_SHA256,
        expected_rows=EXPECTED_FIRST_STAGE_MODULES,
    )
    vendor_rows = parse_inventory(
        vendor_inventory,
        expected_sha256=VENDOR_DLKM_INVENTORY_SHA256,
        expected_rows=EXPECTED_VENDOR_DLKM_MODULES + 5,
    )
    if sha256_file(vendor_manifest) != VENDOR_DLKM_MANIFEST_SHA256:
        raise SurfaceError("vendor_dlkm manifest identity mismatch")
    manifest = json.loads(vendor_manifest.read_text(encoding="ascii"))
    counts = manifest.get("counts", {})
    expected_counts = {
        "vendor_dlkm_modules": EXPECTED_VENDOR_DLKM_MODULES,
        "reference_modules": EXPECTED_FIRST_STAGE_MODULES,
        "vendor_dlkm_only_modules": EXPECTED_VENDOR_DLKM_ONLY_MODULES,
        "union_unique_module_names": EXPECTED_STOCK_UNION_MODULES,
        "content_mismatch_modules": 0,
    }
    if any(counts.get(key) != value for key, value in expected_counts.items()):
        raise SurfaceError(f"vendor_dlkm manifest count mismatch: {counts}")
    if manifest.get("verified_vendor_dlkm_corpus") is not True:
        raise SurfaceError("vendor_dlkm overlap corpus is not verified")

    free_bytes = shutil.disk_usage(scratch).free
    if free_bytes < MIN_TEMP_FREE_BYTES:
        raise SurfaceError(f"insufficient temporary free space: {free_bytes}")
    first_paths, first_receipt = extract_first_stage_modules(
        vendor_ramdisk, lz4, first_rows, scratch
    )
    vendor_only_paths, vendor_receipt = extract_vendor_dlkm_only_modules(
        image, dump_f2fs, vendor_rows, scratch
    )
    if set(first_paths) & set(vendor_only_paths):
        raise SurfaceError("stock module corpus source classes unexpectedly overlap")
    union = {**first_paths, **vendor_only_paths}
    if len(union) != EXPECTED_STOCK_UNION_MODULES:
        raise SurfaceError(f"stock module union mismatch: {len(union)}")
    return union, {
        "absence_search_scope": (
            "all 491 unique stock module payload names across the exact 441-module "
            "vendor_ramdisk corpus and the 50 verified vendor_dlkm-only modules"
        ),
        "inputs": inputs,
        "first_stage": first_receipt,
        "vendor_dlkm_only": vendor_receipt,
        "overlap_byte_identical_count": counts["byte_identical_modules"],
        "first_stage_only_count": counts["reference_only_modules"],
        "union_unique_module_count": len(union),
    }


def readelf_symbols(path: Path) -> tuple[set[str], set[str]]:
    result = subprocess.run(
        ["readelf", "-WsW", str(path)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    defined: set[str] = set()
    undefined: set[str] = set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].endswith(":"):
            continue
        ndx, name = fields[6], fields[7]
        if ndx == "UND":
            undefined.add(name)
        else:
            defined.add(name)
    if not defined:
        raise SurfaceError(f"no symbols parsed from {path}")
    return defined, undefined


def parse_firmware_array(text: str) -> list[int]:
    match = re.search(r"BOOT_FLASH_FW_PASS2\s*\[\s*\]\s*=\s*\{(.*?)\};", text, re.S)
    if not match:
        raise SurfaceError("BOOT_FLASH_FW_PASS2 array not found")
    return [int(item, 16) for item in re.findall(r"0x([0-9a-fA-F]+)", match.group(1))]


def require_tokens(text: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SurfaceError(f"{label} is missing required tokens: {missing}")


def extract_function_block(text: str, signature: str, label: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise SurfaceError(f"{label} signature is missing")
    brace = text.find("{", start + len(signature))
    if brace < 0:
        raise SurfaceError(f"{label} opening brace is missing")
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise SurfaceError(f"{label} closing brace is missing")


def extract_braced_block_from(text: str, start: int, label: str) -> tuple[str, int]:
    brace = text.find("{", start)
    if brace < 0:
        raise SurfaceError(f"{label} opening brace is missing")
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1], index + 1
    raise SurfaceError(f"{label} closing brace is missing")


def validate_host_state_callback(text: str, label: str) -> None:
    block = extract_function_block(
        text,
        "static void max77705_usbpd_set_host_on(void *data, int mode)",
        label,
    )
    require_tokens(
        block,
        (
            "usbpd_data->device_add = 0;",
            "usbpd_data->detach_done_wait = 0;",
            "usbpd_data->host_turn_on_event = 1;",
            "usbpd_data->host_turn_on_event = 0;",
            "wake_up_interruptible(&usbpd_data->host_turn_on_wait_q);",
        ),
        label,
    )
    hits = [token for token in HOST_STATE_CALLBACK_FORBIDDEN_EFFECTS if token in block]
    if hits:
        raise SurfaceError(f"{label} gains a hardware/external effect: {hits}")


def validate_diag_source_text(text: str) -> dict[str, Any]:
    """Validate the future one-module polling diagnostic source shape.

    This validator deliberately does not accept a reduced copy of the stock
    MFD/PDIC stack.  It permits only the parent I2C bind, one dummy client at
    the USBC/MUIC address, two CONTROL1 read commands, and at most one
    conditional CONTROL1 write.  Linked output and compiled control flow still
    require independent validation before packaging.
    """

    require_tokens(text, DIAG_REQUIRED_TOKENS, "Max77705 MUX diagnostic")
    hits = [token for token in DIAG_FORBIDDEN if token in text]
    if hits:
        raise SurfaceError(f"diagnostic retains forbidden broad effect: {hits}")
    if "while (" in text or "do {" in text:
        raise SurfaceError("diagnostic contains an unregistered loop form")

    i2c_calls = re.findall(r"\b((?:devm_)?i2c_[A-Za-z0-9_]+)\s*\(", text)
    expected_i2c_calls = {
        **DIAG_I2C_CALL_COUNTS,
        "devm_i2c_new_dummy_device": 1,
    }
    actual_i2c_calls = {
        name: i2c_calls.count(name)
        for name in sorted(set(i2c_calls))
    }
    if actual_i2c_calls != expected_i2c_calls:
        raise SurfaceError(
            "diagnostic I2C call surface mismatch: "
            f"{actual_i2c_calls} != {expected_i2c_calls}"
        )

    clear_block = extract_function_block(
        text,
        "static int s22plus_max77705_clear_uic_latch_once(",
        "UIC latch clear",
    )
    require_tokens(
        clear_block,
        (
            "i2c_smbus_read_byte_data(muic, S22PLUS_MAX77705_UIC_INT)",
            "return status < 0 ? status : 0;",
        ),
        "UIC latch clear",
    )

    wait_block = extract_function_block(
        text,
        "static int s22plus_max77705_wait_ap_response(",
        "AP-command wait",
    )
    require_tokens(
        wait_block,
        (
            "for (",
            "S22PLUS_MAX77705_POLL_LIMIT",
            "i2c_smbus_read_byte_data(muic, S22PLUS_MAX77705_UIC_INT)",
            "S22PLUS_MAX77705_AP_CMD_RESPONSE",
            "usleep_range(",
            "return -ETIMEDOUT;",
        ),
        "AP-command wait",
    )
    if text.count("for (") != 1:
        raise SurfaceError("only the bounded AP-response poll may loop")

    read_block = extract_function_block(
        text,
        "static int s22plus_max77705_control1_read_once(",
        "CONTROL1 read helper",
    )
    require_tokens(
        read_block,
        (
            "S22PLUS_MAX77705_CONTROL1_READ",
            "S22PLUS_MAX77705_AP_DATAOUT0",
            "S22PLUS_MAX77705_AP_DATAOUT_END",
            "S22PLUS_MAX77705_AP_DATAIN0",
            "i2c_smbus_write_i2c_block_data(",
            "i2c_smbus_write_byte_data(",
            "s22plus_max77705_wait_ap_response(",
            "i2c_smbus_read_i2c_block_data(",
        ),
        "CONTROL1 read helper",
    )
    write_block = extract_function_block(
        text,
        "static int s22plus_max77705_control1_write_once(",
        "CONTROL1 write helper",
    )
    require_tokens(
        write_block,
        (
            "S22PLUS_MAX77705_CONTROL1_WRITE",
            "S22PLUS_MAX77705_AP_DATAOUT0",
            "S22PLUS_MAX77705_AP_DATAOUT_END",
            "S22PLUS_MAX77705_AP_DATAIN0",
            "i2c_smbus_write_i2c_block_data(",
            "i2c_smbus_write_byte_data(",
            "s22plus_max77705_wait_ap_response(",
            "i2c_smbus_read_byte_data(",
        ),
        "CONTROL1 write helper",
    )
    if any(token in write_block for token in ("for (", "while (", "goto ")):
        raise SurfaceError("CONTROL1 write helper may not retry an ambiguous write")
    if write_block.count("i2c_smbus_write_i2c_block_data(") != 1:
        raise SurfaceError("CONTROL1 write command count is not exactly one")
    if write_block.count("i2c_smbus_write_byte_data(") != 1:
        raise SurfaceError("CONTROL1 write terminator count is not exactly one")

    run_block = extract_function_block(
        text,
        "static int s22plus_max77705_diag_run(",
        "diagnostic run",
    )
    require_tokens(
        run_block,
        (
            "s22plus_max77705_read_pmic_identity(",
            "s22plus_max77705_clear_uic_latch_once(",
            "s22plus_max77705_control1_read_once(",
            "if (pre != S22PLUS_MAX77705_COM_USB)",
            "s22plus_max77705_control1_write_once(muic, S22PLUS_MAX77705_COM_USB)",
        ),
        "diagnostic run",
    )
    if text.count("s22plus_max77705_control1_write_once(") != 2:
        raise SurfaceError("CONTROL1 write helper must have exactly one call site")
    if text.count("s22plus_max77705_control1_read_once(") != 3:
        raise SurfaceError("CONTROL1 read helper must have exactly two call sites")
    if text.count("s22plus_max77705_clear_uic_latch_once(") != 2:
        raise SurfaceError("UIC latch clear helper must have exactly one call site")

    identity_call = run_block.find("s22plus_max77705_read_pmic_identity(")
    clear_call = run_block.find("s22plus_max77705_clear_uic_latch_once(")
    pre_read_call = run_block.find("s22plus_max77705_control1_read_once(muic, &pre)")
    condition = run_block.find("if (pre != S22PLUS_MAX77705_COM_USB)")
    write_call = run_block.find(
        "s22plus_max77705_control1_write_once(muic, S22PLUS_MAX77705_COM_USB)"
    )
    condition_block, condition_end = extract_braced_block_from(
        run_block, condition, "conditional CONTROL1 write"
    )
    post_read_call = run_block.find("s22plus_max77705_control1_read_once(muic, &post)")
    if not (
        0 <= identity_call < clear_call < pre_read_call < condition
        and write_call >= condition
        and write_call < condition_end
        and post_read_call >= condition_end
    ):
        raise SurfaceError(
            "diagnostic command order is not identity/clear/pre/optional-write/post"
        )
    if "s22plus_max77705_control1_read_once(muic, &post)" in condition_block:
        raise SurfaceError("post CONTROL1 read must execute after the optional-write branch")
    if "post = pre" in run_block:
        raise SurfaceError("post CONTROL1 state may not be synthesized from pre")

    getter = extract_function_block(
        text,
        "static int s22plus_max77705_result_get(",
        "read-only result getter",
    )
    getter_hits = [token for token in DIAG_GETTER_FORBIDDEN_EFFECTS if token in getter]
    if getter_hits:
        raise SurfaceError(f"result getter initiates an external effect: {getter_hits}")
    if text.count("module_param_cb(") != 1:
        raise SurfaceError("diagnostic must expose exactly one read-only result parameter")

    return {
        "source_contract_satisfied": True,
        "preferred_addition_count": len(CUSTOM_PREFERRED_ADDITIONS),
        "preferred_total_module_count": 61 + len(CUSTOM_PREFERRED_ADDITIONS),
        "direct_parent_i2c_bind": True,
        "only_muic_dummy_client_created": True,
        "control1_read_command_count": 2,
        "control1_write_maximum_count": 1,
        "stale_uic_latch_clear_count": 1,
        "post_read_is_unconditional": True,
        "write_skipped_when_pre_is_usb": True,
        "ambiguous_write_retry_forbidden": True,
        "irq_and_workqueue_absent": True,
        "mfd_children_absent": True,
        "firmware_reset_power_notifier_and_protocol_stacks_absent": True,
        "result_export_read_only_and_cached": True,
    }


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit(root: Path) -> dict[str, Any]:
    kernel = root / KERNEL_ROOT
    modules = root / MODULE_ROOT
    p315_modules, p315_plan_receipt = parse_p315_plan(root)
    source_receipts = {
        label: validate_file(kernel / relative, size, digest, label)
        for label, (relative, size, digest) in SOURCE_IDENTITIES.items()
    }
    module_receipts = {
        name: validate_file(modules / name, size, digest, name)
        for name, (size, digest) in MODULE_IDENTITIES.items()
    }

    with tempfile.TemporaryDirectory(prefix="s22plus-max77705-stock-union-") as directory:
        module_paths, corpus_receipt = stock_module_union(root, Path(directory))
        symbol_tables = {
            name: readelf_symbols(path)
            for name, path in sorted(module_paths.items())
        }
        mfd_defined, mfd_undefined = symbol_tables["mfd_max77705.ko"]
        pdic_defined, pdic_undefined = symbol_tables["pdic_max77705.ko"]
        missing_mfd = set(MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC) - mfd_defined
        missing_pdic_imports = PDIC_UPDATE_IMPORTS - pdic_undefined
        missing_pdic_definitions = PDIC_WRITABLE_DEFINED_SYMBOLS - pdic_defined
        if missing_mfd or missing_pdic_imports or missing_pdic_definitions:
            raise SurfaceError(
                "stock linked surface mismatch: "
                f"mfd={sorted(missing_mfd)} imports={sorted(missing_pdic_imports)} "
                f"definitions={sorted(missing_pdic_definitions)}"
            )
        missing_pdic_local_surface = (
            {"max77705_muic_group", "max77705_ops"}
            | set(MAX77705_TYPEC_MUTATION_CALLBACKS)
        ) - pdic_defined
        if missing_pdic_local_surface:
            raise SurfaceError(
                "stock PDIC local control surface mismatch: "
                f"{sorted(missing_pdic_local_surface)}"
            )

        consumers: dict[str, list[str]] = {}
        for symbol in MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC:
            names = sorted(
                name
                for name, (_defined, undefined) in symbol_tables.items()
                if symbol in undefined
            )
            if names != ["pdic_max77705.ko"]:
                raise SurfaceError(f"unexpected {symbol} consumers: {names}")
            consumers[symbol] = names

        control_export_consumers: dict[str, list[str]] = {}
        for symbol, expected_consumers in PDIC_CONTROL_EXPORT_CONSUMERS.items():
            definers = sorted(
                name
                for name, (defined, _undefined) in symbol_tables.items()
                if symbol in defined
            )
            names = sorted(
                name
                for name, (_defined, undefined) in symbol_tables.items()
                if symbol in undefined
            )
            if definers != ["pdic_max77705.ko"] or names != expected_consumers:
                raise SurfaceError(
                    f"unexpected {symbol} surface: "
                    f"definers={definers} consumers={names}"
                )
            control_export_consumers[symbol] = names

        if_cb_export_consumers: dict[str, list[str]] = {}
        for symbol, expected_consumers in IF_CB_EXPORT_CONSUMERS.items():
            definers = sorted(
                name
                for name, (defined, _undefined) in symbol_tables.items()
                if symbol in defined
            )
            names = sorted(
                name
                for name, (_defined, undefined) in symbol_tables.items()
                if symbol in undefined
            )
            if definers != ["if_cb_manager.ko"] or names != expected_consumers:
                raise SurfaceError(
                    f"unexpected {symbol} IF-callback surface: "
                    f"definers={definers} consumers={names}"
                )
            if_cb_export_consumers[symbol] = names

        dwc3_defined, _dwc3_undefined = symbol_tables["dwc3-msm.ko"]
        if {"ops_usb", "restart_usb_host_mode"} & dwc3_defined:
            raise SurfaceError("fixed DWC3 unexpectedly supplies an IF-callback USB op")

    mfd_text = (kernel / SOURCE_IDENTITIES["mfd"][0]).read_text(errors="strict")
    pdic_text = (kernel / SOURCE_IDENTITIES["pdic"][0]).read_text(errors="strict")
    debug_text = (kernel / SOURCE_IDENTITIES["debug"][0]).read_text(errors="strict")
    makefile_text = (kernel / SOURCE_IDENTITIES["pdic_makefile"][0]).read_text(errors="strict")
    header_text = (kernel / SOURCE_IDENTITIES["pdic_header"][0]).read_text(errors="strict")
    muic_header_text = (kernel / SOURCE_IDENTITIES["muic_header"][0]).read_text(
        errors="strict"
    )
    usbc_register_header_text = (
        kernel / SOURCE_IDENTITIES["usbc_register_header"][0]
    ).read_text(errors="strict")
    mfd_private_header_text = (
        kernel / SOURCE_IDENTITIES["mfd_private_header"][0]
    ).read_text(errors="strict")
    misc_text = (kernel / SOURCE_IDENTITIES["pdic_misc"][0]).read_text(errors="strict")
    muic_text = (kernel / SOURCE_IDENTITIES["max77705_muic"][0]).read_text(
        errors="strict"
    )
    cc_text = (kernel / SOURCE_IDENTITIES["max77705_cc"][0]).read_text(
        errors="strict"
    )
    pd_text = (kernel / SOURCE_IDENTITIES["max77705_pd"][0]).read_text(
        errors="strict"
    )
    alternate_text = (kernel / SOURCE_IDENTITIES["max77705_alternate"][0]).read_text(
        errors="strict"
    )
    muic_afc_text = (kernel / SOURCE_IDENTITIES["max77705_muic_afc"][0]).read_text(
        errors="strict"
    )
    muic_ccic_text = (kernel / SOURCE_IDENTITIES["max77705_muic_ccic"][0]).read_text(
        errors="strict"
    )
    irq_text = (kernel / SOURCE_IDENTITIES["max77705_irq"][0]).read_text(
        errors="strict"
    )
    vendor_defconfig_text = (
        kernel / SOURCE_IDENTITIES["waipio_vendor_defconfig"][0]
    ).read_text(errors="strict")
    common_muic_sysfs_text = (
        kernel / SOURCE_IDENTITIES["common_muic_sysfs"][0]
    ).read_text(errors="strict")
    common_muic_core_text = (
        kernel / SOURCE_IDENTITIES["common_muic_core"][0]
    ).read_text(errors="strict")
    typec_class_text = (kernel / SOURCE_IDENTITIES["typec_class"][0]).read_text(
        errors="strict"
    )
    if_cb_manager_text = (
        kernel / SOURCE_IDENTITIES["if_cb_manager"][0]
    ).read_text(errors="strict")
    dwc3_msm_text = (kernel / SOURCE_IDENTITIES["dwc3_msm"][0]).read_text(
        errors="strict"
    )
    i2c_core_text = (kernel / SOURCE_IDENTITIES["i2c_core"][0]).read_text(
        errors="strict"
    )
    firmware_text = (kernel / SOURCE_IDENTITIES["firmware"][0]).read_text(
        encoding="utf-8-sig", errors="strict"
    )

    require_tokens(
        mfd_text,
        (
            "max77705_usbc_fw_setting(max77705, 0);",
            "EXPORT_SYMBOL_GPL(max77705_usbc_fw_update);",
            "EXPORT_SYMBOL_GPL(max77705_usbc_fw_setting);",
        ),
        "stock MFD source",
    )
    require_tokens(
        pdic_text,
        (
            "max77705_firmware_update_sysfs_work",
            "max77705_firmware_update_callback",
            "ppdic_data->fw_data.firmware_update = max77705_firmware_update_callback;",
            "ret = pdic_misc_init(ppdic_data);",
            "sysfs_create_group(&max77705->dev->kobj, &max77705_attr_grp);",
            "mxim_debug_init();",
            "static const struct typec_operations max77705_ops",
            "usbc_data->typec_cap.ops = &max77705_ops;",
            "usbc_data->port = typec_register_port",
            "static void max77705_usbpd_set_host_on(void *data, int mode)",
            ".usbpd_set_host_on = max77705_usbpd_set_host_on,",
            ".usbpd_wait_entermode = max77705_usbpd_wait_entermode,",
            "usbc_data->man = register_usbpd(usbpd_d);",
            "pdic_manual_ccopen_request(0);",
        ),
        "stock PDIC source",
    )
    validate_host_state_callback(pdic_text, "stock PDIC host-state callback")
    require_tokens(
        muic_text,
        (
            "static const struct attribute_group max77705_muic_group",
            "sysfs_create_group(&switch_device->kobj, &max77705_muic_group)",
            "static DEVICE_ATTR(uart_sel, 0664",
            "static DEVICE_ATTR(usb_sel, 0664",
            "static DEVICE_ATTR(uart_en, 0660",
            "static DEVICE_ATTR(otg_test, 0664",
            "static DEVICE_ATTR(apo_factory, 0664",
            "static DEVICE_ATTR(afc_disable, 0664",
            "static DEVICE_ATTR_RW(hiccup)",
            "max77705_muic_init_detect",
            "com_to_usb_ap",
            "muic_data->muic_d.ops = NULL;",
            "muic_data->man = register_muic(&(muic_data->muic_d));",
        ),
        "stock Max77705 MUIC source",
    )
    require_tokens(
        pd_text,
        (
            "fp_sec_pd_select_pdo = max77705_select_pdo;",
            "fp_sec_pd_select_pps = max77705_select_pps;",
            "fp_sec_pd_vpdo_auth = max77705_vpdo_auth;",
            "fp_sec_pd_manual_ccopen_req = pdic_manual_ccopen_request;",
            "fp_sec_pd_change_src = max77705_forced_change_srccap;",
            "max77705_set_fw_noautoibus(MAX77705_AUTOIBUS_AT_OFF);",
        ),
        "stock Max77705 PD source",
    )
    require_tokens(
        cc_text,
        (
            "typec_set_pwr_role",
            "typec_set_data_role",
            "typec_register_partner",
            "typec_unregister_partner",
            "usb_set_vbus_current(usbpd_data->man, USB_CURRENT_CLEAR);",
        ),
        "stock Max77705 CC source",
    )
    require_tokens(
        irq_text,
        (
            "max77705_write_reg(i2c, max77705_mask_reg[i], 0xff)",
            "MAX77705_PMIC_REG_INTSRC_MASK",
            "request_threaded_irq(max77705->irq, NULL, max77705_irq_thread",
        ),
        "stock Max77705 IRQ source",
    )
    require_tokens(
        typec_class_text,
        (
            "port->ops = cap->ops;",
            "!port->ops || !port->ops->dr_set",
            "!port->ops || !port->ops->pr_set",
            "!port->ops || !port->ops->port_type_set",
        ),
        "Type-C class source",
    )
    require_tokens(
        if_cb_manager_text,
        (
            "struct if_cb_manager *register_usbpd(struct usbpd_dev *usbpd)",
            "man_core->usbpd_d->ops->usbpd_set_host_on(",
            "man_core->usbpd_d->ops->usbpd_wait_entermode(",
            "man_core->usb_d->ops->usb_set_vbus_current(",
        ),
        "IF callback manager source",
    )
    require_tokens(
        dwc3_msm_text,
        (
            "mdwc = devm_kzalloc(&pdev->dev, sizeof(*mdwc), GFP_KERNEL);",
            "mdwc->man = register_usb(&(mdwc->usb_d));",
            "usbpd_set_host_on(mdwc->man, on);",
        ),
        "DWC3 MSM source",
    )
    require_tokens(
        vendor_defconfig_text,
        (
            "CONFIG_HV_MUIC_MAX77705_AFC=y",
            "CONFIG_HICCUP_CHARGER=y",
            "CONFIG_MUIC_MAX77705_PDIC=y",
            "CONFIG_USB_EXTERNAL_NOTIFY=y",
            "CONFIG_CCIC_MAX77705_DEBUG=y",
            "# CONFIG_SEC_FACTORY is not set",
        ),
        "waipio vendor defconfig",
    )
    require_tokens(
        common_muic_sysfs_text,
        ("int muic_sysfs_init(struct muic_platform_data *pdata)",),
        "common MUIC sysfs source",
    )
    if "muic_sysfs_init(" in common_muic_core_text:
        raise SurfaceError("common MUIC core unexpectedly registers common sysfs")
    common_muic_sysfs_locations = source_token_locations(kernel, "muic_sysfs_init(")
    if common_muic_sysfs_locations != ["drivers/muic/common/muic_sysfs.c"]:
        raise SurfaceError(
            "common MUIC sysfs call-site scope changed: "
            f"{common_muic_sysfs_locations}"
        )
    if "muic_sysfs_init" in pdic_undefined or "muic_sysfs_deinit" in pdic_undefined:
        raise SurfaceError("stock PDIC unexpectedly imports common MUIC sysfs helpers")
    require_tokens(
        debug_text,
        (
            "misc_register(&mxim_debug_miscdev)",
            "mxim_debug_i2c_write",
            "mxim_debug_opcode_store",
            "mxim_debug_reg_store",
        ),
        "stock Max77705 debug source",
    )
    require_tokens(
        misc_text,
        (
            'NODE_OF_UMS "pdic_fwupdate"',
            "fw_data->ic_data->firmware_update(",
            "misc_register(&ums_update_device)",
        ),
        "stock PDIC misc source",
    )
    if "#define MAX77705_SYS_FW_UPDATE" not in header_text:
        raise SurfaceError("stock PDIC update macro is no longer unconditional")
    if "max77705_debug.o" not in makefile_text:
        raise SurfaceError("stock PDIC debug object is no longer linked")
    require_tokens(
        muic_header_text,
        (
            "COMMAND_CONTROL1_READ\t\t= 0x05",
            "COMMAND_CONTROL1_WRITE\t\t= 0x06",
            "COM_OPEN\t=",
            "COM_USB\t\t=",
            "MAX77705_MUIC_COM_OPEN\t\t= 0x07",
            "MAX77705_MUIC_COM_USB\t\t= 0x01",
        ),
        "Max77705 MUIC command header",
    )
    require_tokens(
        usbc_register_header_text,
        (
            "#define BIT_APCmdResI\t\t\tBIT(7)",
            "#define OPCODE_WRITE 0x21",
            "#define OPCODE_WRITE_END 0x41",
            "#define OPCODE_READ 0x51",
        ),
        "Max77705 USBC register header",
    )
    require_tokens(
        mfd_private_header_text,
        (
            "MAX77705_USBC_REG_UIC_INT\t\t= 0x02",
            "MAX77705_USBC_REG_AP_DATAOUT0\t\t= 0x21",
            "MAX77705_USBC_REG_AP_DATAIN0\t\t= 0x51",
        ),
        "Max77705 private register header",
    )
    require_tokens(
        mfd_text,
        (
            '#define I2C_ADDR_MUIC\t(0x4A >> 1)',
            "i2c_new_dummy_device",
            '{ .compatible = "maxim,max77705" }',
            "return i2c_add_driver(&max77705_i2c_driver);",
        ),
        "stock MFD direct-I2C precedent",
    )
    require_tokens(
        i2c_core_text,
        (
            "if (i2c_of_match_device(drv->of_match_table, client))",
            ".match\t\t= i2c_device_match",
            "EXPORT_SYMBOL_GPL(devm_i2c_new_dummy_device);",
        ),
        "I2C core match/dummy-client authority",
    )
    require_tokens(
        alternate_text,
        (
            "max77705_process_alternate_mode",
            "max77705_vdm_message_handler",
            "max77705_sec_uvdm_out_request_message",
        ),
        "stock alternate-mode surface",
    )
    require_tokens(
        muic_afc_text,
        (
            "max77705_muic_afc_hv_set",
            "max77705_muic_qc_hv_set",
            "max77705_muic_handle_detect_dev_afc",
        ),
        "stock AFC/QC surface",
    )
    require_tokens(
        muic_ccic_text,
        (
            "max77705_muic_handle_ccic_notification",
            "max77705_muic_register_ccic_notifier",
        ),
        "stock MUIC CCIC notifier surface",
    )

    firmware = parse_firmware_array(firmware_text)
    expected_header = [0xC1, 0x66, 0xF1, 0xCE, 0x6E, 0x40, 0x15, 0x02]
    if len(firmware) != 53_055 or firmware[:8] != expected_header:
        raise SurfaceError(
            f"pinned firmware geometry mismatch: {len(firmware)}/{firmware[:8]}"
        )

    contract = {
        "status": "REGISTERED_NOT_SATISFIED",
        "selected_design": "POLLING_SINGLE_MODULE_MUX_DIAGNOSTIC",
        "preferred_total_module_count": 65,
        "preferred_additions": list(CUSTOM_PREFERRED_ADDITIONS),
        "stock_comparison_total_module_count": 67,
        "rejected_full_pdic_custom_design": {
            "module_count": 61 + len(REJECTED_FULL_PDIC_CUSTOM_ADDITIONS),
            "additions": list(REJECTED_FULL_PDIC_CUSTOM_ADDITIONS),
            "status": "REJECTED_AS_DISPROPORTIONATE_FOR_MUX_DISCRIMINATION",
            "reason": [
                "retains parent IRQ masking and MFD child creation",
                "retains MUIC initial detection and runtime protocol branches",
                "retains CC, PD, alternate-mode, AFC/QC, and notifier control planes",
                "requires a much larger write matrix than the connector-MUX question",
            ],
        },
        "diagnostic": {
            "module": "s22plus_max77705_mux_diag.ko",
            "parent_bus": "i2c",
            "parent_compatible": "maxim,max77705",
            "parent_address": "0x66",
            "only_dummy_client_address": "0x25",
            "stock_mfd_and_pdic_loaded": False,
            "irq_requested": False,
            "workqueue_created": False,
            "mfd_children_created": False,
            "result_interface": "one cached read-only 0444 module parameter",
            "protocol": {
                "uic_interrupt_register": "0x02",
                "ap_command_response_bit": "BIT(7)",
                "ap_data_out_start": "0x21",
                "ap_data_out_end": "0x41",
                "ap_data_in_start": "0x51",
                "control1_read_opcode": "0x05",
                "control1_write_opcode": "0x06",
                "full_com_usb_byte": "0x09",
            },
            "transaction": [
                "read and validate PMIC identity",
                "clear/read the otherwise-unowned UIC interrupt latch",
                "issue exactly one bounded CONTROL1 read command and validate opcode/value",
                "if and only if pre is not 0x09, issue one CONTROL1 write of 0x09 without retry",
                "issue exactly one bounded post CONTROL1 read command and validate opcode/value",
                "cache the complete result without further hardware access",
            ],
            "source_validator": "validate_diag_source_text",
            "source_validator_must_run_before_compile": True,
        },
        "selected_closure": {
            "base_module_count": len(p315_modules),
            "custom_total_module_count": 65,
            "stock_mfd_pdic_and_spu_verify_absent_from_opened_set": True,
            "external_control_consumers_absent": sorted(
                P315_FORBIDDEN_CONTROL_CONSUMERS
            ),
            "inactive_lvs_consumer_absent": sorted(P315_ABSENT_IF_CB_CONSUMERS),
        },
        "write_inventory": {
            "status": "BOUNDED_DIAGNOSTIC_EFFECT_SET_REGISTERED_NOT_IMPLEMENTED",
            "always_present_commands": [
                "pre CONTROL1 read command",
                "post CONTROL1 read command",
            ],
            "conditional_command": "one CONTROL1 write of full byte 0x09 when pre != 0x09",
            "maximum_control1_write_count": 1,
            "ambiguous_write_retry_forbidden": True,
            "read_to_clear_uic_interrupt_reads_bounded": True,
            "excluded_effect_families": [
                "firmware update and IC reset",
                "parent IRQ and interrupt-mask programming",
                "MFD child creation",
                "MUIC attach classification and BC/DCD",
                "CC, PD, source-VBUS, sink-capability, and no-auto-IBUS",
                "alternate mode, VDM, Dex, AFC, QC, and audio accessory",
                "Type-C, MUIC, IF-manager, power-supply, and notifier publication",
                "writable sysfs, misc, debugfs, procfs, and exported control ABI",
            ],
        },
        "result_contract": {
            "pre_0x09_post_0x09_attach": "MUX was already USB; attach is not attributed to a MUX write",
            "pre_0x09_post_0x09_silent": "missing Linux MUX selection refuted for that run",
            "pre_non_0x09_post_0x09_attach": "strong MUX-causal support",
            "pre_non_0x09_post_0x09_silent": "MUX corrected but insufficient",
            "read_write_or_response_failure": "diagnostic failure; no connector claim",
            "host_fact_without_complete_device_result": "preserve host fact without inventing device causality",
        },
        "future_linked_and_runtime_proofs": [
            "actual diagnostic source passes validate_diag_source_text before compilation",
            "source, linked module, and disassembly agree on two reads and at most one conditional write",
            "no forbidden defined, undefined, relocation, or string surface survives",
            "module imports only the bounded I2C, timing, cached-result, and module-registration closure",
            "fixed-Image modversion and CFI closure matches",
            "custom module dependency closure is exactly 65 modules",
            "the unbound max77705@66 client binds only the diagnostic and creates only 0x25",
            "no stock MFD, PDIC, or SPU module is opened or loaded",
            "pre-write direct fence, command deadlines, response validation, and no-retry behavior are exercised by fixtures",
            "carrier and host-sidecar positive control distinguish every result-contract row",
        ],
    }
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "device_contact": False,
        "source_receipts": source_receipts,
        "p315_plan": p315_plan_receipt,
        "module_receipts": module_receipts,
        "stock_module_union": corpus_receipt,
        "stock_surface": {
            "firmware_header": {
                "array_bytes": len(firmware),
                "first_eight": expected_header,
                "source_version": "6E.00",
                "product_id": 1,
            },
            "mfd_exports": list(MFD_EXPORTS_CONSUMED_ONLY_BY_PDIC),
            "exclusive_consumers": consumers,
            "exclusive_consumer_search_scope": corpus_receipt["absence_search_scope"],
            "pdic_update_imports": sorted(PDIC_UPDATE_IMPORTS),
            "pdic_writable_defined_symbols": sorted(PDIC_WRITABLE_DEFINED_SYMBOLS),
            "pdic_control_export_consumers": control_export_consumers,
            "if_cb_export_consumers": if_cb_export_consumers,
            "p315_forbidden_control_consumers_absent": sorted(
                P315_FORBIDDEN_CONTROL_CONSUMERS
            ),
            "max77705_muic_group": {
                "writable_attributes": list(MAX77705_MUIC_WRITABLE_ATTRIBUTES),
                "read_only_attributes": list(MAX77705_MUIC_READ_ONLY_ATTRIBUTES),
                "stock_linked_group_and_callbacks_present": True,
            },
            "typec_role_mutation": {
                "callbacks": list(MAX77705_TYPEC_MUTATION_CALLBACKS),
                "stock_linked_ops_present": True,
                "ops_null_makes_data_and_power_role_read_only": True,
                "ops_null_hides_port_type": True,
                "natural_attach_status_reporting_is_independent": True,
            },
            "common_muic_sysfs": {
                "tree_wide_driver_c_definition_only": common_muic_sysfs_locations,
                "stock_pdic_imports_init_or_deinit": False,
                "active_additional_surface_for_this_pdic_path": False,
            },
            "if_cb_manager": {
                "fixed_dwc3_register_usb_present": True,
                "fixed_dwc3_usb_ops_linked": False,
                "usb_set_vbus_current_endpoint_effective": False,
                "custom_must_retain_usbpd_set_host_on": True,
                "usbpd_set_host_on_is_state_and_wakeup_only": True,
                "lvstest_consumer_absent_from_p315": True,
                "custom_must_null_sbu_cc_control_and_wait_entermode": True,
                "max77705_muic_ops_remain_null": True,
            },
            "separate_same_name_surfaces": {
                "common_pdic_fw_update": "firmware update",
                "parent_local_fw_update": "CONTROL1 read/write debug path",
            },
            "raw_debug_misc_and_sysfs": True,
            "pdic_firmware_misc_device": True,
            "pdic_uvdm_misc_device": True,
        },
        "custom_contract": contract,
        "custom_contract_sha256": canonical_hash(contract),
    }


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=repo_root())
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    result = audit(root)
    output = args.output or root / DEFAULT_OUTPUT
    atomic_json(output.resolve(), result)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
