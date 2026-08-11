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


SCHEMA = "s22plus_fyg8_max77705_custom_surface_contract_v10"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
DIAG_SOURCE = Path(
    "workspace/public/src/kernel-modules/s22plus_max77705_mux_diag/"
    "s22plus_max77705_mux_diag.c"
)
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
    "custom-surface-authority-20260812-15.json"
)
DIAG_BUILD_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "custom-module-build-20260812-07/build-audit.json"
)
RUNTIME_PARSER_RECEIPT = Path(
    "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "runtime-parser-20260812-01.json"
)
RUNTIME_PARSER_RECEIPT_IDENTITY = (
    2_368,
    "ec315f67f6420df506e63a8e2c7e1c329ffeafcf8a1b7e079411c6ccea8104e6",
)
RUNTIME_PARSER_SOURCE_IDENTITY = (
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_result_parser.inc.c",
    19_499,
    "d8b3d152823dbf706682802142328f515c7d6c422a18a7309331814bf69e4b65",
)
RUNTIME_PARSER_FIXTURE_SOURCE_IDENTITY = (
    "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_result_parser_fixture.c",
    1_937,
    "3093151c9f613ed781a9c7fa00efcede4148f061bb25e30c8c992cbd789d9f92",
)
RUNTIME_PARSER_FIXTURE_DRIVER_IDENTITY = (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_runtime_parser_fixture.py",
    13_362,
    "1d73a82e69701006d0c31efcd16fa476ccd95351fdac46323a9deebb4cf27374",
)
RUNTIME_PARSER_TELEMETRY_AUTHORITY_IDENTITY = (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_telemetry.py",
    36_607,
    "9c72afcf172aa109158c844b111efa9b0f1ff7027f10185aac9b80b996b156cc",
)
RUNTIME_PARSER_CLANG_IDENTITY = (
    "workspace/private/work/toolchains/aosp-clang-android12-release/"
    "clang-r416183b/bin/clang",
    2_999_243,
    "b2ce016755bddbab76549895bca07b1dc8d14a3e315b8b3567097fef04eadae1",
)
DIAG_BUILD_RECEIPT_IDENTITY = (
    19_492,
    "5ea484ae1381b23c42c71163a8bb5add2e54f8b936e7730aee7b87e6a8ffeadd",
)
DIAG_MODULE_IDENTITY = (
    293_400,
    "4f4f485a35cdb12206b814390b56674ca6a6d691c9a1d7a29c97030053231849",
)
DIAG_SOURCE_VALIDATOR_FUNCTION_SHA256 = (
    "0914d607dac146b4e1aec41df36a104cfaa93c3c09568171f4fe75ec9cd08c3d"
)
DIAG_EXPECTED_VERMAGIC = (
    "5.10.226-android12-9-30958166-abS906NKSS7FYG8 SMP preempt "
    "mod_unload modversions aarch64"
)
DIAG_EXPECTED_UNDEFINED = {
    "__stack_chk_fail",
    "__stack_chk_guard",
    "arm64_const_caps_ready",
    "bin2hex",
    "cpu_hwcap_keys",
    "devm_i2c_new_dummy_device",
    "i2c_del_driver",
    "i2c_register_driver",
    "i2c_smbus_read_byte_data",
    "i2c_smbus_read_i2c_block_data",
    "i2c_smbus_write_byte_data",
    "i2c_smbus_write_i2c_block_data",
    "msleep",
    "scnprintf",
    "usleep_range",
}

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
DIAG_RUNTIME_TERMINAL_BUCKETS = {
    "late_finit_module_failure": "NO_PROOF_OBSERVER_DIAGNOSTIC_LOAD",
    "driver_registered_without_matching_parent": (
        "NO_PROOF_OBSERVER_DIAGNOSTIC_NO_MATCH"
    ),
    "matching_parent_identity_rejected": (
        "NO_PROOF_OBSERVER_DIAGNOSTIC_PARENT_IDENTITY"
    ),
    "parent_ownership_conflict": (
        "NO_PROOF_OBSERVER_DIAGNOSTIC_PARENT_OWNERSHIP"
    ),
    "probe_terminal_failure": "NO_PROOF_DIAGNOSTIC_TRANSACTION",
    "result_not_ready_eagain": "NO_PROOF_OBSERVER_DIAGNOSTIC_NOT_READY",
    "result_read_timeout": "NO_PROOF_OBSERVER_DIAGNOSTIC_RESULT_TIMEOUT",
    "synchronous_probe_or_publication_contradiction": (
        "NO_PROOF_OBSERVER_DIAGNOSTIC_SYNC_CONTRADICTION"
    ),
    "result_payload_unrepresentable": (
        "NO_PROOF_OBSERVER_DIAGNOSTIC_PAYLOAD_OVERFLOW"
    ),
}
DIAG_EAGAIN_BINDING_WITNESS_FIELDS = (
    "loader_state",
    "pre_exact_parent_present",
    "pre_exact_parent_driver_state",
    "pre_matching_unbound_parent_count",
    "pre_wrong_address_compatible_parent_count",
    "post_exact_parent_driver_state",
    "post_diagnostic_bound_parent_count",
    "post_exact_adapter_muic_0x25_client_count",
    "post_foreign_0x25_client_count",
)
DIAG_EAGAIN_OBSERVABLE_ROWS = {
    "probe_in_progress": {
        "loader_state": "FINIT_MODULE_IN_PROGRESS",
        "terminal": False,
        "bounded_continuation": "WAIT_FOR_LOADER_OR_REGISTERED_TIMEOUT",
    },
    "no_matching_parent": {
        "loader_state": "FINIT_MODULE_RETURNED_SUCCESS",
        "pre_exact_parent_present": False,
        "pre_matching_unbound_parent_count": 0,
        "pre_wrong_address_compatible_parent_count": 0,
        "post_diagnostic_bound_parent_count": 0,
        "post_exact_adapter_muic_0x25_client_count": 0,
        "terminal_bucket_key": "driver_registered_without_matching_parent",
    },
    "wrong_address_compatible_parent": {
        "loader_state": "FINIT_MODULE_RETURNED_SUCCESS",
        "pre_exact_parent_present": False,
        "pre_wrong_address_compatible_parent_count_min": 1,
        "post_diagnostic_bound_parent_count": 0,
        "post_exact_adapter_muic_0x25_client_count": 0,
        "terminal_bucket_key": "matching_parent_identity_rejected",
    },
    "exact_parent_owned_by_other_driver": {
        "loader_state": "FINIT_MODULE_RETURNED_SUCCESS",
        "pre_exact_parent_driver_state": "OTHER_DRIVER",
        "post_exact_parent_driver_state": "OTHER_DRIVER",
        "terminal_bucket_key": "parent_ownership_conflict",
    },
    "exact_parent_unbound_after_sync_return": {
        "loader_state": "FINIT_MODULE_RETURNED_SUCCESS",
        "pre_exact_parent_present": True,
        "post_exact_parent_driver_state": "UNBOUND",
        "terminal_bucket_key": "synchronous_probe_or_publication_contradiction",
        "investigation_scope": "DRIVER_CORE_PRE_PROBE_OR_PROBE_REACHABILITY",
    },
    "diagnostic_binding_ready_but_result_eagain": {
        "loader_state": "FINIT_MODULE_RETURNED_SUCCESS",
        "post_exact_parent_driver_state": "DIAGNOSTIC",
        "post_diagnostic_bound_parent_count": 1,
        "post_exact_adapter_muic_0x25_client_count": 1,
        "post_foreign_0x25_client_count": 0,
        "terminal_bucket_key": "synchronous_probe_or_publication_contradiction",
        "investigation_scope": "MODULE_PUBLICATION_OR_RESULT_READ_PATH",
    },
}
DIAG_EAGAIN_NEGATIVE_INVARIANTS = {
    "claim_busy_after_sync_return": {
        "decodable_vector_allowed": False,
        "encoder_acceptance_is_hard_error": True,
        "reason": (
            "the first successful claim path publishes a cached result and "
            "returns zero before force-synchronous driver registration returns"
        ),
        "if_observed_in_raw_witnesses": "DEVICE_MULTIPLICITY_OR_SOURCE_DRIFT",
    },
}
DIAG_EAGAIN_CLASSIFICATION_PRIORITY = (
    "probe_in_progress",
    "exact_parent_owned_by_other_driver",
    "diagnostic_binding_ready_but_result_eagain",
    "exact_parent_unbound_after_sync_return",
    "wrong_address_compatible_parent",
    "no_matching_parent",
)
DIAG_TERMINAL_ROW_ADMISSION_RULE = {
    "scope": "LOCAL_MAX77705_DESIGN_ONLY",
    "common_process_v2_gate": False,
    "source_reachable_or_required_negative_invariant": True,
    "changes_safety_causal_interpretation_or_next_action": True,
    "distinct_retained_witness_required": True,
    "merge_when_semantics_and_followup_are_equivalent": True,
}
DIAG_RETAINED_PAYLOAD_CONTRACT = {
    "fixed_image_carrier": "S22E1L2-192",
    "record_count": 1,
    "retained_slot_count": 2,
    "request_payload_bytes_per_slot": 64,
    "fixed_envelope_bytes": 128,
    "encoding": "MAX77705_DIAG_V2_PACKBITS_OR_BOUNDED_OVERFLOW_SUMMARY",
    "lossless_poll_bytes_required_for_causal_rows": True,
    "unrepresentable_poll_payload_is_terminal_no_proof": True,
    "unrepresentable_terminal_bucket_key": "result_payload_unrepresentable",
    "overflow_payload_bytes": 44,
    "overflow_payload_layout": {
        "raw_poll_sha256": [0, 32],
        "per_command_or": [32, 36],
        "per_command_poll0": [36, 40],
        "per_command_nonzero_count": [40, 44],
    },
    "overflow_payload_spare_bytes": 32,
    "overflow_causal_result_allowed": False,
    "response_seen_implies_slot_or_apcmdresi": True,
    "timeout_active_slot_or_apcmdresi_forbidden": True,
    "or_apcmdresi_without_response_seen_allowed": True,
    "or_zero_iff_nonzero_count_zero": True,
    "full_lto_or_fixed_image_change_required": False,
}
DIAG_POST2_RETENTION_MATRIX = {
    "applicability": (
        "complete result with validated post1 and post2 CONTROL1_R responses "
        "and post1 CONTROL1 equal to COM_USB"
    ),
    "post2_poll0_interval": (
        "latch accumulated after the final post1 UIC read through the first "
        "post2 UIC poll"
    ),
    "detection_latch_mask": 0x7B,
    "bc12_redetection_latch_mask": 0x0A,
    "rows": {
        "post2_usb_without_detection_latch": (
            "quiet retention interval; weak opcode-visible maintenance evidence"
        ),
        "post2_usb_with_detection_latch": (
            "detection event presence correlated with retained opcode-visible COM_USB"
        ),
        "post2_nonusb_with_detection_latch": (
            "late opcode-visible reversion correlated with detection event presence"
        ),
        "post2_nonusb_without_detection_latch": (
            "late opcode-visible reversion without a retained detection-event witness"
        ),
    },
    "event_presence_only": True,
    "physical_switch_movement_proven": False,
    "causal_trigger_proven": False,
}
REJECTED_FULL_PDIC_CUSTOM_ADDITIONS = (
    "msm-geni-se.ko",
    "gpi.ko",
    "i2c-msm-geni.ko",
    "mfd_max77705.ko",
    "pdic_max77705.ko",
)
DIAG_REQUIRED_TOKENS = (
    '#define S22PLUS_MAX77705_PARENT_COMPATIBLE "maxim,max77705"',
    "#define S22PLUS_MAX77705_PARENT_ADDR 0x66",
    "#define S22PLUS_MAX77705_MUIC_ADDR 0x25",
    "#define S22PLUS_MAX77705_PMIC_ID_REG 0x00",
    "#define S22PLUS_MAX77705_PMIC_REV_REG 0x01",
    "#define S22PLUS_MAX77705_EXPECTED_PMIC_ID 0x15",
    "#define S22PLUS_MAX77705_EXPECTED_PMIC_REV_LOW3 0x02",
    "#define S22PLUS_MAX77705_UIC_INT 0x02",
    "#define S22PLUS_MAX77705_AP_DATAOUT0 0x21",
    "#define S22PLUS_MAX77705_AP_DATAOUT_END 0x41",
    "#define S22PLUS_MAX77705_AP_DATAIN0 0x51",
    "#define S22PLUS_MAX77705_AP_CMD_RESPONSE BIT(7)",
    "#define S22PLUS_MAX77705_CONTROL1_READ 0x05",
    "#define S22PLUS_MAX77705_CONTROL1_WRITE 0x06",
    "#define S22PLUS_MAX77705_COM_USB 0x09",
    "#define S22PLUS_MAX77705_POLL_LIMIT",
    "#define S22PLUS_MAX77705_RETENTION_MS 30000U",
    "devm_i2c_new_dummy_device",
    "static int s22plus_max77705_clear_uic_latch_once(",
    "static int s22plus_max77705_wait_ap_response(",
    "static int s22plus_max77705_control1_read_once(",
    "static int s22plus_max77705_control1_write_once(",
    "static int s22plus_max77705_diag_run(",
    "static int s22plus_max77705_diag_probe(",
    "atomic_cmpxchg(&s22plus_max77705_claimed, 0, 1)",
    "if (IS_ERR(muic))",
    "if (pre != S22PLUS_MAX77705_COM_USB)",
    "s22plus_max77705_control1_write_once(",
    "msleep(S22PLUS_MAX77705_RETENTION_MS)",
    ".compatible = S22PLUS_MAX77705_PARENT_COMPATIBLE",
    ".probe_type = PROBE_FORCE_SYNCHRONOUS",
    "module_i2c_driver(",
    "struct i2c_client *parent, const struct i2c_device_id *id)",
    "static int s22plus_max77705_result_get(",
    "char *buffer, const struct kernel_param *parameter)",
    "static int cached_result_ready;",
    "smp_store_release(&cached_result_ready, 1);",
    "if (!smp_load_acquire(&cached_result_ready))",
    "return -EAGAIN;",
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
    "MODULE_DEVICE_TABLE(",
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
    "i2c_smbus_read_byte_data": 5,
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


def validate_runtime_parser_receipt(root: Path) -> dict[str, Any]:
    path = root / RUNTIME_PARSER_RECEIPT
    size, digest = RUNTIME_PARSER_RECEIPT_IDENTITY
    validate_file(path, size, digest, "Max77705 runtime-parser receipt")
    value = json.loads(path.read_text(encoding="utf-8"))
    expected_parser_path, expected_parser_size, expected_parser_digest = (
        RUNTIME_PARSER_SOURCE_IDENTITY
    )
    expected_fixture_path, expected_fixture_size, expected_fixture_digest = (
        RUNTIME_PARSER_FIXTURE_SOURCE_IDENTITY
    )
    expected_driver_path, expected_driver_size, expected_driver_digest = (
        RUNTIME_PARSER_FIXTURE_DRIVER_IDENTITY
    )
    expected_telemetry_path, expected_telemetry_size, expected_telemetry_digest = (
        RUNTIME_PARSER_TELEMETRY_AUTHORITY_IDENTITY
    )
    expected_clang_path, expected_clang_size, expected_clang_digest = (
        RUNTIME_PARSER_CLANG_IDENTITY
    )
    if (
        value.get("schema")
        != "s22plus_fyg8_max77705_runtime_parser_fixture_v1"
        or value.get("verdict")
        != "PASS_MAX77705_ACTUAL_PID1_PARSER_AND_SUMMARY_HOST_ONLY"
        or value.get("host_only") is not True
        or value.get("device_contact") is not False
        or value.get("valid_vector_count") != 4
        or value.get("invalid_mutation_count") != 13
        or value.get("python_summary_matches_actual_c") is not True
        or value.get("strict_module_string_grammar") is not True
        or value.get("aarch64_freestanding_compile") is not True
        or value.get("sysfs_path_or_driver_override_integrated") is not False
        or value.get("fresh_d0_still_required") is not True
        or value.get("verified") is not True
        or value.get("parser_source")
        != {
            "path": expected_parser_path,
            "size": expected_parser_size,
            "sha256": expected_parser_digest,
        }
        or value.get("host_fixture_source")
        != {
            "path": expected_fixture_path,
            "size": expected_fixture_size,
            "sha256": expected_fixture_digest,
        }
        or value.get("fixture_driver_source")
        != {
            "path": expected_driver_path,
            "size": expected_driver_size,
            "sha256": expected_driver_digest,
        }
        or value.get("telemetry_authority_source")
        != {
            "path": expected_telemetry_path,
            "size": expected_telemetry_size,
            "sha256": expected_telemetry_digest,
        }
        or {
            key: value.get("pinned_aarch64_clang", {}).get(key)
            for key in ("path", "size", "sha256")
        }
        != {
            "path": expected_clang_path,
            "size": expected_clang_size,
            "sha256": expected_clang_digest,
        }
    ):
        raise SurfaceError("Max77705 runtime-parser receipt contract differs")
    return {
        "path": str(RUNTIME_PARSER_RECEIPT),
        "size": size,
        "sha256": digest,
        "payload": value,
    }


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
    the USBC/MUIC address, three CONTROL1 read commands, one fixed retention
    dwell, and at most one conditional CONTROL1 write.  Linked output and
    compiled control flow still require independent validation before
    packaging.
    """

    require_tokens(text, DIAG_REQUIRED_TOKENS, "Max77705 MUX diagnostic")
    hits = [token for token in DIAG_FORBIDDEN if token in text]
    if hits:
        raise SurfaceError(f"diagnostic retains forbidden broad effect: {hits}")
    if "while (" in text or "do {" in text:
        raise SurfaceError("diagnostic contains an unregistered loop form")
    if "PROBE_PREFER_ASYNCHRONOUS" in text:
        raise SurfaceError("diagnostic probe must remain force-synchronous")

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

    identity_block = extract_function_block(
        text,
        "static int s22plus_max77705_read_pmic_identity(",
        "PMIC identity",
    )
    require_tokens(
        identity_block,
        (
            "i2c_smbus_read_byte_data(parent,",
            "S22PLUS_MAX77705_PMIC_ID_REG",
            "S22PLUS_MAX77705_PMIC_REV_REG",
            "result->pmic_id = (u8)value;",
            "result->pmic_rev = (u8)value;",
            "result->pmic_id != S22PLUS_MAX77705_EXPECTED_PMIC_ID",
            "(result->pmic_rev & 0x7U) !=",
            "S22PLUS_MAX77705_EXPECTED_PMIC_REV_LOW3",
            "return -ENODEV;",
        ),
        "PMIC identity",
    )
    if identity_block.count("i2c_smbus_read_byte_data(") != 2:
        raise SurfaceError("PMIC identity must issue exactly two direct reads")
    if identity_block.count("result->pmic_rev & 0x7U") != 1:
        raise SurfaceError("PMIC revision must use the stock low-three-bit identity")

    clear_block = extract_function_block(
        text,
        "static int s22plus_max77705_clear_uic_latch_once(",
        "UIC latch clear",
    )
    require_tokens(
        clear_block,
        (
            "i2c_smbus_read_byte_data(",
            "S22PLUS_MAX77705_UIC_INT",
            "if (status < 0)",
            "return status;",
            "result->initial_uic = (u8)status;",
            "result->initial_uic_valid = 1U;",
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
            "i2c_smbus_read_byte_data(",
            "if (status < 0)",
            "result->poll_bytes[slot][attempt] = (u8)status;",
            "result->poll_count[slot] = (u8)(attempt + 1U);",
            "S22PLUS_MAX77705_AP_CMD_RESPONSE",
            "usleep_range(",
            "return -ETIMEDOUT;",
        ),
        "AP-command wait",
    )
    if text.count("for (") != 1:
        raise SurfaceError("only the bounded AP-response poll may loop")
    if text.count("msleep(") != 1:
        raise SurfaceError("diagnostic must have exactly one retention dwell")

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
            "if (rc != 2)",
            "result->response_opcode[slot] = response[0];",
            "result->response_value[slot] = response[1];",
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
            "result->write_attempted = 1U;",
            "result->write_ambiguous = 1U;",
            "result->write_ambiguous = 0U;",
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
            "S22PLUS_MAX77705_COM_USB",
            "result->stage = S22PLUS_MAX77705_STAGE_COMPLETE;",
            "return 0;",
        ),
        "diagnostic run",
    )
    if text.count("s22plus_max77705_control1_write_once(") != 2:
        raise SurfaceError("CONTROL1 write helper must have exactly one call site")
    if text.count("s22plus_max77705_control1_read_once(") != 4:
        raise SurfaceError("CONTROL1 read helper must have exactly three call sites")
    if text.count("s22plus_max77705_clear_uic_latch_once(") != 2:
        raise SurfaceError("UIC latch clear helper must have exactly one call site")

    identity_call = run_block.find("s22plus_max77705_read_pmic_identity(")
    clear_call = run_block.find("s22plus_max77705_clear_uic_latch_once(")
    pre_read_call = run_block.find("S22PLUS_MAX77705_SLOT_PRE, &pre")
    condition = run_block.find("if (pre != S22PLUS_MAX77705_COM_USB)")
    write_call = run_block.find("s22plus_max77705_control1_write_once(")
    condition_block, condition_end = extract_braced_block_from(
        run_block, condition, "conditional CONTROL1 write"
    )
    post1_read_call = run_block.find("S22PLUS_MAX77705_SLOT_POST1, &post1")
    retention_call = run_block.find("msleep(S22PLUS_MAX77705_RETENTION_MS)")
    post2_read_call = run_block.find("S22PLUS_MAX77705_SLOT_POST2, &post2")
    if not (
        0 <= identity_call < clear_call < pre_read_call < condition
        and write_call >= condition
        and write_call < condition_end
        and condition_end <= post1_read_call < retention_call < post2_read_call
    ):
        raise SurfaceError(
            "diagnostic command order is not "
            "identity/clear/pre/optional-write/post1/retention/post2"
        )
    if any(
        token in condition_block
        for token in (
            "S22PLUS_MAX77705_SLOT_POST1, &post1",
            "S22PLUS_MAX77705_SLOT_POST2, &post2",
        )
    ):
        raise SurfaceError(
            "post CONTROL1 reads must execute after the optional-write branch"
        )
    if any(
        token in run_block
        for token in ("post1 = pre", "post2 = post1", "post2 = pre")
    ):
        raise SurfaceError("post CONTROL1 state may not be synthesized")
    if any(
        expression in run_block
        for expression in (
            "post1 == S22PLUS_MAX77705_COM_USB",
            "post1 != S22PLUS_MAX77705_COM_USB",
            "post2 == S22PLUS_MAX77705_COM_USB",
            "post2 != S22PLUS_MAX77705_COM_USB",
        )
    ):
        raise SurfaceError(
            "post readback values are diagnostic results, not terminal errors"
        )

    probe_block = extract_function_block(
        text,
        "static int s22plus_max77705_diag_probe(",
        "diagnostic probe",
    )
    require_tokens(
        probe_block,
        (
            "if (parent->addr != S22PLUS_MAX77705_PARENT_ADDR)",
            "return -ENODEV;",
            "atomic_cmpxchg(&s22plus_max77705_claimed, 0, 1)",
            "devm_i2c_new_dummy_device(",
            "if (IS_ERR(muic))",
            "s22plus_max77705_cache_result(&s22plus_max77705_result);",
            "return 0;",
        ),
        "diagnostic probe",
    )
    if probe_block.find(
        "if (parent->addr != S22PLUS_MAX77705_PARENT_ADDR)"
    ) > probe_block.find("atomic_cmpxchg("):
        raise SurfaceError("diagnostic parent address must be checked before claim")
    if probe_block.rfind("return 0;") < probe_block.find(
        "s22plus_max77705_cache_result(&s22plus_max77705_result);"
    ):
        raise SurfaceError("attempted probe can escape before caching its result")
    if probe_block.count("atomic_cmpxchg(") != 1:
        raise SurfaceError("diagnostic probe claim must be one exact atomic transition")
    if probe_block.count("return 0;") != 1:
        raise SurfaceError("attempted diagnostic probe must have one cached terminal return")

    cache_block = extract_function_block(
        text,
        "static void s22plus_max77705_cache_result(",
        "cached result encoder",
    )
    require_tokens(
        cache_block,
        (
            "result->pmic_id",
            "result->pmic_rev",
            "result->initial_uic",
            "result->command_issued_mask",
            "result->response_seen_mask",
            "result->write_attempted",
            "result->write_ambiguous",
            "result->response_opcode[0]",
            "result->response_value[0]",
            "result->poll_count[0]",
            "result->poll_count[1]",
            "result->poll_count[2]",
            "result->poll_count[3]",
            "result->poll_bytes[0]",
            "result->poll_bytes[1]",
            "result->poll_bytes[2]",
            "result->poll_bytes[3]",
            "smp_store_release(&cached_result_ready, 1);",
        ),
        "cached result encoder",
    )
    if cache_block.count("s22plus_max77705_append_poll(") != 4:
        raise SurfaceError("cached result must retain all four poll-byte vectors")
    if cache_block.count("smp_store_release(&cached_result_ready, 1);") != 1:
        raise SurfaceError("cached result must have one release publication")
    if cache_block.find("smp_store_release(&cached_result_ready, 1);") < cache_block.rfind(
        "scnprintf("
    ):
        raise SurfaceError("cached result publication must follow terminal encoding")

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
    require_tokens(
        getter,
        (
            "if (!smp_load_acquire(&cached_result_ready))",
            "return -EAGAIN;",
            'return scnprintf(buffer, PAGE_SIZE, "%s", cached_result);',
        ),
        "read-only result getter",
    )
    if getter.count("smp_load_acquire(&cached_result_ready)") != 1:
        raise SurfaceError("result getter must have one acquire readiness check")
    if getter.find("smp_load_acquire(&cached_result_ready)") > getter.find(
        "scnprintf("
    ):
        raise SurfaceError("result readiness must be checked before cached bytes")
    if text.count("smp_store_release(&cached_result_ready, 1);") != 1 or text.count(
        "smp_load_acquire(&cached_result_ready)"
    ) != 1:
        raise SurfaceError("result publication must be one release/acquire pair")

    return {
        "source_contract_satisfied": True,
        "preferred_addition_count": len(CUSTOM_PREFERRED_ADDITIONS),
        "preferred_total_module_count": 61 + len(CUSTOM_PREFERRED_ADDITIONS),
        "direct_parent_i2c_bind": True,
        "exact_parent_i2c_address": "0x66",
        "only_muic_dummy_client_created": True,
        "exact_pmic_identity": {
            "pmic_id": "0x15",
            "pmic_rev_low3": "0x02",
            "pmic_rev_raw_retained": True,
        },
        "control1_read_command_count": 3,
        "control1_write_maximum_count": 1,
        "stale_uic_latch_clear_count": 1,
        "post1_read_is_unconditional": True,
        "post2_read_is_after_retention_window": True,
        "retention_window_ms": 30_000,
        "all_successful_uic_reads_retained": True,
        "post_values_are_results_not_errors": True,
        "attempted_probe_retry_suppressed": True,
        "write_skipped_when_pre_is_usb": True,
        "ambiguous_write_retry_forbidden": True,
        "irq_and_workqueue_absent": True,
        "mfd_children_absent": True,
        "firmware_reset_power_notifier_and_protocol_stacks_absent": True,
        "result_export_read_only_and_cached": True,
        "terminal_cache_release_acquire": True,
        "probe_force_synchronous": True,
    }


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_runtime_integration_contract(diagnostic: dict[str, Any]) -> bool:
    runtime = diagnostic.get("runtime_integration", {})
    if not isinstance(runtime, dict):
        raise SurfaceError("diagnostic runtime integration contract is missing")
    base = runtime.get("base_module_count")
    substrate = runtime.get("early_substrate_module_count")
    early = runtime.get("generic_early_load_count")
    staged = runtime.get("diagnostic_staged_payload_count")
    total = runtime.get("total_packaged_module_count")
    bind_timeout = runtime.get("inherited_bind_gate_timeout_sec")
    late_lifetime = runtime.get("late_load_minimum_lifetime_sec")
    if (
        not all(isinstance(value, int) for value in (
            base, substrate, early, staged, total, bind_timeout, late_lifetime
        ))
        or base + substrate != early
        or early + staged != total
        or early != 64
        or staged != 1
        or total != 65
    ):
        raise SurfaceError("diagnostic early/late module arithmetic mismatch")
    if (
        bind_timeout != 20
        or late_lifetime < 31
        or late_lifetime <= bind_timeout
        or late_lifetime <= 30
    ):
        raise SurfaceError("diagnostic late-load lifetime cannot contain its dwell")
    for name in (
        "diagnostic_forbidden_in_generic_load_loop",
        "bind_gate_must_close_before_late_load",
        "late_load_forbidden_inside_bind_gate",
        "late_load_lifetime_exceeds_retention_window",
        "gadget_path_ready_before_late_load",
        "host_sidecar_armed_before_late_load",
        "successful_synchronous_finit_module_is_completion_witness",
        "probe_force_synchronous",
        "result_read_only_after_successful_finit_module_return",
        "eagain_is_distinct_from_terminal_diagnostic_failure",
        "future_async_or_missing-client_drift_must_not_expose_cache",
    ):
        if runtime.get(name) is not True:
            raise SurfaceError(f"diagnostic runtime invariant is not fixed: {name}")
    if runtime.get("dedicated_finit_module_callsite_count") != 1:
        raise SurfaceError("diagnostic must have one dedicated late-load callsite")

    arming = diagnostic.get("result_contract_arming_precondition", {})
    if (
        not isinstance(arming, dict)
        or arming.get("status") != "REGISTERED_NOT_SATISFIED"
        or arming.get("required_terminal_buckets") != DIAG_RUNTIME_TERMINAL_BUCKETS
        or tuple(arming.get("eagain_binding_witness_fields", ()))
        != DIAG_EAGAIN_BINDING_WITNESS_FIELDS
        or arming.get("eagain_observable_rows") != DIAG_EAGAIN_OBSERVABLE_ROWS
        or arming.get("eagain_negative_invariants")
        != DIAG_EAGAIN_NEGATIVE_INVARIANTS
        or tuple(arming.get("eagain_classification_priority", ()))
        != DIAG_EAGAIN_CLASSIFICATION_PRIORITY
        or arming.get("eagain_is_a_standalone_terminal") is not False
        or arming.get("eagain_binding_witness_cross_axis_required") is not True
        or arming.get("binding_witness_values_retained_end_to_end") is not True
        or arming.get("observable_obligation_surjectivity_required") is not True
        or arming.get("negative_invariant_decode_preimage_must_be_empty") is not True
        or arming.get("unique_retained_vector_reverse_map_required") is not True
        or arming.get("real_encoder_carrier_decoder_round_trip_required") is not True
        or arming.get("synthesized_retained_representation_required") is not True
        or arming.get("physical_condition_reproduction_required") is not False
        or arming.get("every_existing_mux_result_row_also_required") is not True
        or arming.get("blocks_packaging_and_f1_approval_until_receipted") is not True
    ):
        raise SurfaceError("diagnostic result-contract arming gate is incomplete")
    for row in DIAG_EAGAIN_OBSERVABLE_ROWS.values():
        bucket_key = row.get("terminal_bucket_key")
        if bucket_key is not None and bucket_key not in DIAG_RUNTIME_TERMINAL_BUCKETS:
            raise SurfaceError("EAGAIN decomposition references an unknown bucket")
    for invariant in DIAG_EAGAIN_NEGATIVE_INVARIANTS.values():
        if (
            invariant.get("decodable_vector_allowed") is not False
            or invariant.get("encoder_acceptance_is_hard_error") is not True
        ):
            raise SurfaceError("EAGAIN negative invariant is not fail-closed")
    if diagnostic.get("terminal_row_admission_rule") != DIAG_TERMINAL_ROW_ADMISSION_RULE:
        raise SurfaceError("local terminal-row admission rule is incomplete")
    if diagnostic.get("retained_payload_contract") != DIAG_RETAINED_PAYLOAD_CONTRACT:
        raise SurfaceError("diagnostic retained-payload contract is incomplete")
    if diagnostic.get("post2_retention_matrix") != DIAG_POST2_RETENTION_MATRIX:
        raise SurfaceError("diagnostic post2-retention matrix is incomplete")
    runtime_parser = diagnostic.get("runtime_result_parser", {})
    parser_receipt = runtime_parser.get("receipt", {})
    if (
        runtime_parser.get("status") != "HOST_EXECUTED_NOT_SYSFS_INTEGRATED"
        or parser_receipt.get("path") != str(RUNTIME_PARSER_RECEIPT)
        or (parser_receipt.get("size"), parser_receipt.get("sha256"))
        != RUNTIME_PARSER_RECEIPT_IDENTITY
        or runtime_parser.get("allocation_free") is not True
        or runtime_parser.get("io_free") is not True
        or runtime_parser.get("strict_canonical_module_string_grammar") is not True
        or runtime_parser.get("python_summary_matches_actual_c") is not True
        or runtime_parser.get("aarch64_freestanding_compile") is not True
        or runtime_parser.get("sysfs_and_driver_override_require_fresh_d0")
        is not True
        or runtime_parser.get(
            "blocks_packaging_until_live_callsite_is_wired_and_tested"
        )
        is not True
    ):
        raise SurfaceError("diagnostic runtime-result parser gate is incomplete")
    return True


def validate_diag_build_payload(
    payload: dict[str, Any], diag_source_receipt: dict[str, Any]
) -> dict[str, Any]:
    if (
        payload.get("schema") != "s22plus_fyg8_max77705_mux_diag_build_v1"
        or payload.get("target") != TARGET
        or payload.get("host_only") is not True
        or payload.get("verdict") != "PASS_AB_REPRODUCIBLE_LINKED_ABI_AUDITED"
        or payload.get("authority") != "H0_BUILD_ONLY_NO_DEVICE_AUTHORITY"
        or payload.get("a_b_byte_identical") is not True
    ):
        raise SurfaceError("diagnostic linked-build verdict or authority mismatch")

    safety = payload.get("safety", {})
    if safety != {
        "device_contact": False,
        "partition_write": False,
        "image_packaging": False,
        "module_insertion": False,
    }:
        raise SurfaceError(f"diagnostic linked-build safety mismatch: {safety}")

    source = payload.get("module_sources", {}).get(
        "s22plus_max77705_mux_diag.c", {}
    )
    if (
        source.get("size") != diag_source_receipt["size"]
        or source.get("sha256") != diag_source_receipt["sha256"]
    ):
        raise SurfaceError("diagnostic source and linked-build source disagree")

    precompile = payload.get("precompile_source_contract", {})
    if (
        precompile.get("verified_before_compile") is not True
        or precompile.get("module_source_sha256") != diag_source_receipt["sha256"]
        or precompile.get("validator_function_sha256")
        != DIAG_SOURCE_VALIDATOR_FUNCTION_SHA256
        or precompile.get("validation") != diag_source_receipt["validation"]
    ):
        raise SurfaceError("diagnostic precompile source-contract proof mismatch")

    expected_linked_surface = {
        "firmware_update": False,
        "reset": False,
        "irq": False,
        "workqueue": False,
        "notifier": False,
        "power_supply": False,
        "exported_symbols": 0,
        "conditional_control1_write_maximum": 1,
        "control1_read_count": 3,
        "retention_window_ms": 30_000,
    }
    if payload.get("linked_surface") != expected_linked_surface:
        raise SurfaceError("diagnostic linked effect surface mismatch")

    modules = payload.get("modules", {})
    builds = payload.get("builds", {})
    if set(modules) != {"a", "b"} or set(builds) != {"a", "b"}:
        raise SurfaceError("diagnostic A/B linked artifacts are incomplete")
    for side in ("a", "b"):
        module = modules[side]
        build = builds[side]
        if (
            module.get("verified") is not True
            or (module.get("size"), module.get("sha256")) != DIAG_MODULE_IDENTITY
            or (build.get("size"), build.get("sha256")) != DIAG_MODULE_IDENTITY
            or module.get("exports") != []
            or set(module.get("undefined_imports", [])) != DIAG_EXPECTED_UNDEFINED
            or set(module.get("modversions", {}))
            != DIAG_EXPECTED_UNDEFINED | {"module_layout"}
        ):
            raise SurfaceError(f"diagnostic linked module {side} surface mismatch")
        cfi = module.get("cfi", {})
        if (
            cfi.get("cfi_check_present") is not True
            or cfi.get("callback_relocations_target_cfi_jump_tables") is not True
        ):
            raise SurfaceError(f"diagnostic linked module {side} CFI mismatch")
        modinfo = module.get("modinfo", {})
        if (
            modinfo.get("name") != ["s22plus_max77705_mux_diag"]
            or modinfo.get("vermagic") != [DIAG_EXPECTED_VERMAGIC]
            or modinfo.get("depends") != [""]
        ):
            raise SurfaceError(f"diagnostic linked module {side} metadata mismatch")

    fixed = payload.get("fixed_p310_abi", {})
    if fixed.get("verified") is not True or fixed.get("a_b_identity") is not True:
        raise SurfaceError("diagnostic fixed P3.10 ABI proof mismatch")
    if (
        payload.get("source_authority", {}).get("verified") is not True
        or payload.get("toolchain", {}).get("verified") is not True
        or payload.get("kmi_whitelist", {}).get("verified") is not True
        or payload.get("protocol_authority", {}).get("verified") is not True
    ):
        raise SurfaceError("diagnostic build authority closure is incomplete")

    return {
        "linked_build_satisfied": True,
        "verdict": payload["verdict"],
        "a_b_byte_identical": True,
        "source_contract_verified_before_compile": True,
        "module_size": DIAG_MODULE_IDENTITY[0],
        "module_sha256": DIAG_MODULE_IDENTITY[1],
        "vermagic": DIAG_EXPECTED_VERMAGIC,
        "undefined_import_count": len(DIAG_EXPECTED_UNDEFINED),
        "modversion_count": len(DIAG_EXPECTED_UNDEFINED) + 1,
        "cfi_callbacks_verified": True,
        "exported_symbol_count": 0,
    }


def validate_diag_build_receipt(
    root: Path, diag_source_receipt: dict[str, Any]
) -> dict[str, Any]:
    path = root / DIAG_BUILD_RECEIPT
    identity = validate_file(
        path,
        DIAG_BUILD_RECEIPT_IDENTITY[0],
        DIAG_BUILD_RECEIPT_IDENTITY[1],
        "diagnostic linked-build receipt",
    )
    try:
        payload = json.loads(path.read_text(encoding="ascii"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SurfaceError(f"invalid diagnostic linked-build receipt: {error}") from error
    if not isinstance(payload, dict):
        raise SurfaceError("diagnostic linked-build receipt is not an object")
    return {
        "receipt": identity,
        "validation": validate_diag_build_payload(payload, diag_source_receipt),
    }


def audit(root: Path) -> dict[str, Any]:
    kernel = root / KERNEL_ROOT
    modules = root / MODULE_ROOT
    diag_source = root / DIAG_SOURCE
    if diag_source.is_symlink() or not diag_source.is_file():
        raise SurfaceError(f"diagnostic source is not a direct regular file: {diag_source}")
    diag_source_text = diag_source.read_text(encoding="utf-8", errors="strict")
    diag_source_validation = validate_diag_source_text(diag_source_text)
    diag_source_receipt = {
        "path": str(DIAG_SOURCE),
        "size": diag_source.stat().st_size,
        "sha256": sha256_file(diag_source),
        "validation": diag_source_validation,
    }
    diag_build_receipt = validate_diag_build_receipt(root, diag_source_receipt)
    runtime_parser_receipt = validate_runtime_parser_receipt(root)
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
        "status": "SOURCE_AND_LINKED_AB_ABI_QUALIFIED_RUNTIME_NOT_SATISFIED",
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
            "source": diag_source_receipt,
            "linked_build": diag_build_receipt,
            "parent_bus": "i2c",
            "parent_compatible": "maxim,max77705",
            "parent_address": "0x66",
            "only_dummy_client_address": "0x25",
            "stock_mfd_and_pdic_loaded": False,
            "irq_requested": False,
            "workqueue_created": False,
            "mfd_children_created": False,
            "result_interface": "one cached read-only 0444 module parameter",
            "load_timing": (
                "after gadget path activation and host sidecar arming; the probe "
                "then owns one bounded 30000-ms retention/correlation dwell"
            ),
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
                "read/consume the full otherwise-unowned UIC interrupt latch once and retain its byte",
                "issue exactly one bounded CONTROL1 read command and validate opcode/value",
                "if and only if pre is not 0x09, issue one CONTROL1 write of 0x09 without retry",
                "issue one immediate post1 CONTROL1 read and validate opcode/value",
                "hold an exact 30000-ms host-correlation window without another MUX write",
                "issue one terminal post2 CONTROL1 read and validate opcode/value",
                "cache the complete result without further hardware access",
            ],
            "initial_uic_read_scope": {
                "whole_register_read_to_clear_accepted": True,
                "non_ap_latches_consumed": [
                    "SYSMsgI",
                    "VBUSDetI",
                    "VbADCI",
                    "DCDTmoI",
                    "CHGTypI",
                    "UIDADCI",
                ],
                "raw_initial_byte_must_be_retained": True,
                "no_competing_linux_consumer_required": True,
            },
            "interpretation_ceiling": {
                "control1_readback_proves_physical_switch_contact": False,
                "control1_shadow_or_command_state_possible": True,
                "cold_write_may_require_unobserved_classification": True,
                "silent_result_refutes_physical_mux_hypothesis": False,
                "host_attach_is_independent_physical_witness": True,
            },
            "source_validator": "validate_diag_source_text",
            "source_validator_must_run_before_compile": True,
            "linked_build_receipt_must_match_before_packaging": True,
            "retry_suppression_scope": (
                "one loaded module instance; unload/reinsert is a separate runtime "
                "attempt and is forbidden"
            ),
            "runtime_integration": {
                "base_module_count": 61,
                "early_substrate_module_count": 3,
                "generic_early_load_count": 64,
                "diagnostic_staged_payload_count": 1,
                "total_packaged_module_count": 65,
                "diagnostic_forbidden_in_generic_load_loop": True,
                "inherited_bind_gate_timeout_sec": 20,
                "bind_gate_must_close_before_late_load": True,
                "late_load_forbidden_inside_bind_gate": True,
                "late_load_minimum_lifetime_sec": 31,
                "late_load_lifetime_exceeds_retention_window": True,
                "gadget_path_ready_before_late_load": True,
                "host_sidecar_armed_before_late_load": True,
                "dedicated_finit_module_callsite_count": 1,
                "successful_synchronous_finit_module_is_completion_witness": True,
                "probe_force_synchronous": True,
                "result_read_only_after_successful_finit_module_return": True,
                "eagain_is_distinct_from_terminal_diagnostic_failure": True,
                "future_async_or_missing-client_drift_must_not_expose_cache": True,
            },
            "result_contract_arming_precondition": {
                "status": "REGISTERED_NOT_SATISFIED",
                "required_terminal_buckets": DIAG_RUNTIME_TERMINAL_BUCKETS,
                "eagain_binding_witness_fields": (
                    DIAG_EAGAIN_BINDING_WITNESS_FIELDS
                ),
                "eagain_observable_rows": DIAG_EAGAIN_OBSERVABLE_ROWS,
                "eagain_negative_invariants": DIAG_EAGAIN_NEGATIVE_INVARIANTS,
                "eagain_classification_priority": (
                    DIAG_EAGAIN_CLASSIFICATION_PRIORITY
                ),
                "eagain_is_a_standalone_terminal": False,
                "eagain_binding_witness_cross_axis_required": True,
                "binding_witness_values_retained_end_to_end": True,
                "observable_obligation_surjectivity_required": True,
                "negative_invariant_decode_preimage_must_be_empty": True,
                "unique_retained_vector_reverse_map_required": True,
                "real_encoder_carrier_decoder_round_trip_required": True,
                "synthesized_retained_representation_required": True,
                "physical_condition_reproduction_required": False,
                "every_existing_mux_result_row_also_required": True,
                "blocks_packaging_and_f1_approval_until_receipted": True,
            },
            "terminal_row_admission_rule": DIAG_TERMINAL_ROW_ADMISSION_RULE,
            "retained_payload_contract": DIAG_RETAINED_PAYLOAD_CONTRACT,
            "post2_retention_matrix": DIAG_POST2_RETENTION_MATRIX,
            "runtime_result_parser": {
                "status": "HOST_EXECUTED_NOT_SYSFS_INTEGRATED",
                "receipt": runtime_parser_receipt,
                "allocation_free": True,
                "io_free": True,
                "strict_canonical_module_string_grammar": True,
                "python_summary_matches_actual_c": True,
                "aarch64_freestanding_compile": True,
                "sysfs_and_driver_override_require_fresh_d0": True,
                "blocks_packaging_until_live_callsite_is_wired_and_tested": True,
            },
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
            "status": "BOUNDED_DIAGNOSTIC_EFFECT_SET_LINKED_ABI_AUDITED_NOT_PACKAGED",
            "always_present_commands": [
                "pre CONTROL1 read command",
                "immediate post1 CONTROL1 read command",
                "terminal post2 CONTROL1 read command after 30000 ms",
            ],
            "conditional_command": "one CONTROL1 write of full byte 0x09 when pre != 0x09",
            "maximum_control1_write_count": 1,
            "ambiguous_write_retry_forbidden": True,
            "read_to_clear_uic_interrupt_reads_bounded": True,
            "initial_whole_uic_latch_consumption_accepted_and_retained": True,
            "retention_window_ms": 30_000,
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
            "pre_non_0x09_post1_post2_0x09_attach": "strong MUX-causal support",
            "pre_non_0x09_post1_post2_0x09_silent": (
                "opcode-visible state retained for the bounded window, but physical "
                "contact and the MUX hypothesis remain unresolved"
            ),
            "pre_0x09_post1_post2_0x09_attach": (
                "MUX was opcode-visible as USB; attach is not attributed to a MUX write"
            ),
            "pre_0x09_post1_post2_0x09_silent": (
                "absence of opcode-visible COM_USB is refuted, but physical MUX "
                "continuity is not"
            ),
            "post1_0x09_post2_non_0x09": (
                "late opcode-visible reversion observed; no maintained-MUX claim"
            ),
            "read_write_or_response_failure": "diagnostic failure; no connector claim",
            "host_fact_without_complete_device_result": "preserve host fact without inventing device causality",
            "post2_retention_matrix": DIAG_POST2_RETENTION_MATRIX,
        },
        "satisfied_source_and_linked_proofs": [
            "actual diagnostic source passes validate_diag_source_text",
            "source and linked A/B modules agree on three reads and at most one conditional write",
            "no forbidden defined, undefined, relocation, metadata, or export surface survives",
            "module imports only the bounded I2C, timing, cached-result, and module-registration closure",
            "fixed-Image modversion, CFI callback, toolchain, KMI, and A/B byte-identity closure matches",
        ],
        "remaining_runtime_and_packaging_proofs": [
            "custom module dependency closure is exactly 65 modules",
            "the unbound max77705@66 client binds only the diagnostic and creates only 0x25",
            "no stock MFD, PDIC, or SPU module is opened or loaded",
            "late diagnostic load occurs only after gadget-path and host-sidecar readiness",
            "the generic 20-second bind gate closes before a dedicated diagnostic late-load lifetime of at least 31 seconds begins",
            "the diagnostic is staged as the sixty-fifth payload but is absent from the 64-entry generic early-load loop",
            "the plan loads the diagnostic exactly once and exposes no unload/reinsert path",
            "the exact 30000-ms retention dwell fits the candidate and guard budgets",
            "all late-load and cached-result terminal buckets round-trip through the real encoder carrier and decoder before packaging or F1 approval",
            "one fixed Carrier-v2 record retains one 128-byte two-slot envelope; only losslessly represented poll bytes may support a causal row, while an oversized lossless payload terminates as explicit no-proof with SHA-256 plus per-command OR, poll0, and nonzero-count summary",
            "EAGAIN is never decoded alone; six observable rows are surjective over unique retained vectors while claim-busy has an empty decoder preimage",
            "pre-write direct fence, command deadlines, response validation, and no-retry behavior are exercised by fixtures",
            "carrier and host-sidecar positive control distinguish every result-contract row",
        ],
    }
    validate_runtime_integration_contract(contract["diagnostic"])
    return {
        "schema": SCHEMA,
        "target": TARGET,
        "host_only": True,
        "device_contact": False,
        "source_receipts": source_receipts,
        "p315_plan": p315_plan_receipt,
        "module_receipts": module_receipts,
        "diagnostic_linked_build": diag_build_receipt,
        "runtime_result_parser": runtime_parser_receipt,
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
