#!/usr/bin/env python3
"""Bind the exact P3.19 73-row plan to the SSUSB mode and UDC path.

Host-only.  This checker answers the narrow question left by the stock
recovery control: whether the current candidate plan is missing a module or a
known DT supplier needed to create ``a600000.ssusb/mode`` and the
``a600000.dwc3`` UDC.  It deliberately keeps static membership/ABI closure
separate from runtime driver bind and probe success.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = Path(__file__).resolve().parent
REVALIDATION = SCRIPT_DIR.parent / "revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_boot_verify as boot_verify  # noqa: E402
import s22plus_fyg8_p251_ssusb_dependency_audit as p251  # noqa: E402
import s22plus_fyg8_p251b_phy_nested_closure_audit as p251b  # noqa: E402
import s22plus_fyg8_p319_module_closure_plan as closure  # noqa: E402
import s22plus_fyg8_usb_role_static_re as static_re  # noqa: E402
import s22plus_v3434_boot_boundary_map as boot_boundary  # noqa: E402


SCHEMA = "s22plus-fyg8-p319-ssusb-udc-plan-closure-v1"
VERDICT = "PASS_P319_SSUSB_UDC_PLAN_CLOSURE_H0"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}

PHASE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-50"
)
PHASE_RESULT = PHASE / "result.json"
PLAN_SOURCE = PHASE / "stock-sources/s22plus_fyg8_p286_e3_plan.h"
WRAPPER_SOURCE = PHASE / "stock-sources/s22plus_fyg8_p290_e3_runtime.c"
RUNTIME_SOURCE = PHASE / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
ROLE_SOURCE = PHASE / "stock-sources/s22plus_fyg8_p260_e3_runtime.inc.c"
MODULE_DIR = PHASE / "module-bytes"
IMAGE = ROOT / "workspace/private/outputs/s22plus_fyg8_p311/fixed-p310-ready-1/Image"
VENDOR_RAMDISK = ROOT / (
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/vendor_ramdisk00"
)
VENDOR_DTB = ROOT / (
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/unpack-vendor-boot/dtb"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "ssusb-udc-plan-closure-v1-20260824-01/result.json"
)

EXPECTED = {
    "phase_result": (382_264, "982f903f7685f63e5b2fbadebc5a3bbef5d98f009207ac352bda80777b09e886"),
    "plan_source": (5_316, "57d7467887797d2377186e46cafecd2efaa9e660a5c48f7b543441251102c9f1"),
    "wrapper_source": (31_282, "c55aae39ac4846e952e2d6c8672b93dd44f8a8d2388645aa8cd8dcd761f60064"),
    "runtime_source": (435_334, "0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9"),
    "role_source": (20_665, "767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612"),
    "image": (41_490_944, "71f573eb77e67c82b9191bfe0926153f6c8dd5fefe3bba01f884c9beb0c4bae8"),
    "vendor_ramdisk": (21_813_545, "41b2481b779ff48863c300250dabf1b3dcc45c7f58fab421fcf6df1245145193"),
    "vendor_dtb": (1_721_428, "2cd64d43a4f6b89a7c5523f3ef73fbb84dcad92c6d857e649cd1f0baa7c0080e"),
}

HELPERS = {
    "boot_verify": REVALIDATION / "s22plus_boot_verify.py",
    "dt_parser": REVALIDATION / "s22plus_fyg8_p241_dtbo_role_contract.py",
    "rpmh_dependency": REVALIDATION / "s22plus_fyg8_p243_rpmh_dependency_audit.py",
    "ssusb_dependency": REVALIDATION / "s22plus_fyg8_p251_ssusb_dependency_audit.py",
    "phy_nested_dependency": REVALIDATION / "s22plus_fyg8_p251b_phy_nested_closure_audit.py",
    "module_closure": REVALIDATION / "s22plus_fyg8_p319_module_closure_plan.py",
    "elf_static": REVALIDATION / "s22plus_fyg8_usb_role_static_re.py",
    "ikconfig": REVALIDATION / "s22plus_v3434_boot_boundary_map.py",
}

REQUIRED_CONFIG = {
    "CONFIG_USB": "y",
    "CONFIG_USB_GADGET": "y",
    "CONFIG_USB_DWC3": "y",
    "CONFIG_USB_DWC3_DUAL_ROLE": "y",
    "CONFIG_USB_ROLE_SWITCH": "y",
    "CONFIG_TYPEC": "y",
    "CONFIG_TYPEC_UCSI": "y",
}

MODE_SYMBOLS = {
    "dwc3_msm_probe": (0x5DB0, 0x12EC),
    "mode_store": (0xA108, 0xA8),
    "dwc3_msm_set_role": (0xA1B0, 0x250),
    "dwc3_ext_event_notify": (0x45E4, 0x460),
    "dwc3_otg_start_peripheral": (0xCC3C, 0xD7C),
}

PLAN_ROW_RE = re.compile(
    r'^\s*\{"([^\"]+\.ko)", "([^\"]+)", "([^\"]*)"\},\s*$',
    re.MULTILINE,
)
GATE_RE = re.compile(
    r'^\s*\{(\d+)U, "([^\"]+)", "([^\"]+)", "([^\"]+)"\},\s*$',
    re.MULTILINE,
)


class AuditError(RuntimeError):
    """An exact input, static derivation, or publication invariant differs."""


_BOUND_AUDITOR_SOURCE = globals().get("_P319_SSUSB_UDC_BOUND_SOURCE")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": sha256(payload)}


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    expected: tuple[int, str] | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        resolved.name != direct.name
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink < 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _stat_identity(before) != _stat_identity(inside)
        or _stat_identity(before) != _stat_identity(after)
        or expected is not None
        and identity(payload) != {"size": expected[0], "sha256": expected[1]}
    ):
        raise AuditError(f"{label} identity differs")
    return payload


def json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root is not an object")
    return value


def ascii_text(payload: bytes, label: str) -> str:
    try:
        return payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise AuditError(f"{label} is not ASCII") from exc


def load_bound_auditor() -> types.ModuleType:
    source = stable_bytes(Path(__file__), "auditor", 1024 * 1024)
    module = types.ModuleType("p319_ssusb_udc_plan_closure_bound")
    module.__dict__["__file__"] = str(Path(__file__).resolve())
    module.__dict__["_P319_SSUSB_UDC_BOUND_SOURCE"] = source
    exec(compile(source, str(Path(__file__).resolve()), "exec"), module.__dict__)
    return module


def modinfo_from_bytes(payload: bytes, label: str) -> dict[str, list[str]]:
    section = closure.elf_section(payload, ".modinfo")
    if section is None:
        raise AuditError(f"{label} lacks .modinfo")
    values: dict[str, list[str]] = {}
    for item in section.split(b"\x00"):
        if b"=" not in item:
            continue
        key, _, value = item.partition(b"=")
        values.setdefault(
            key.decode("utf-8", "replace"), []
        ).append(value.decode("utf-8", "replace"))
    return values


def direct_dependencies(payload: bytes, label: str) -> list[str]:
    value = modinfo_from_bytes(payload, label).get("depends", [""])[0]
    return [f"{name}.ko" for name in value.split(",") if name]


def parse_plan(plan_source: bytes) -> tuple[list[tuple[str, str, str]], list[dict[str, Any]]]:
    text = ascii_text(plan_source, "P319 plan source")
    rows = PLAN_ROW_RE.findall(text)
    gates = [
        {"order": int(order), "id": name, "kind": kind, "path": path}
        for order, name, kind, path in GATE_RE.findall(text)
    ]
    if len(rows) != 73 or len(set(rows)) != 73:
        raise AuditError("P319 plan is not 73 unique rows")
    expected_gates = (
        (10, "ssusb", "driver-bind-symlink", "/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb"),
        (11, "dwc3-core", "driver-bind-symlink", "/sys/bus/platform/drivers/dwc3/a600000.dwc3"),
        (12, "udc", "class-device", "/sys/class/udc/a600000.dwc3"),
    )
    if len(gates) != 12 or tuple(
        (row["order"], row["id"], row["kind"], row["path"])
        for row in gates[-3:]
    ) != expected_gates:
        raise AuditError("P319 SSUSB/DWC3/UDC gates differ")
    return rows, gates


def audit_plan(
    phase: dict[str, Any],
    plan_source: bytes,
    module_payloads: dict[str, bytes],
) -> dict[str, Any]:
    rows, gates = parse_plan(plan_source)
    phase_rows = [
        (row.get("file"), row.get("runtime_name"), row.get("params"))
        for row in phase.get("plan", {}).get("rows", [])
    ]
    if phase_rows != rows or phase.get("plan", {}).get("module_count") != 73:
        raise AuditError("P319 phase result and plan source differ")
    positions = {row[0]: index for index, row in enumerate(rows)}
    if positions.get("dwc3-msm.ko") != 59 or positions.get("ucsi_glink.ko") != 61:
        raise AuditError("P319 DWC3/UCSI positions differ")

    receipts = {
        row.get("file"): row
        for row in phase.get("module_crc_closure", {}).get("modules", [])
    }
    if set(receipts) != set(positions) or set(module_payloads) != set(positions):
        raise AuditError("P319 module receipt population differs")

    dependency_edges: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    violations: list[dict[str, Any]] = []
    for name, runtime_name, _params in rows:
        payload = module_payloads[name]
        receipt = receipts[name]
        if identity(payload) != {
            "size": receipt.get("size"), "sha256": receipt.get("sha256")
        }:
            raise AuditError(f"P319 module identity differs: {name}")
        info = modinfo_from_bytes(payload, name)
        if info.get("name", [""])[0] != runtime_name:
            raise AuditError(f"P319 module runtime name differs: {name}")
        for dependency in direct_dependencies(payload, name):
            edge = {
                "before": dependency,
                "after": name,
                "before_index": positions.get(dependency),
                "after_index": positions[name],
            }
            dependency_edges.append(edge)
            if dependency not in positions:
                missing.append({"module": name, "dependency": dependency})
            elif positions[dependency] >= positions[name]:
                violations.append(edge)
    if len(dependency_edges) != 110 or missing or violations:
        raise AuditError("P319 declared module dependency closure differs")

    required = set(p251.REQUIRED_MODULES) | set(p251b.MODULES)
    required_positions = {name: positions[name] for name in sorted(required)}
    if set(required_positions) != required or any(
        index > positions["dwc3-msm.ko"] for index in required_positions.values()
    ):
        raise AuditError("known SSUSB provider module set is not ordered")

    crc = phase.get("module_crc_closure", {})
    expected_crc = {
        "module_count": 73,
        "total_imports": 3566,
        "ordered_crc_closed": True,
        "missing_provider_count": 0,
        "ambiguous_provider_count": 0,
        "duplicate_provider_count": 0,
    }
    if any(crc.get(key) != value for key, value in expected_crc.items()):
        raise AuditError("P319 ordered Image/module provider closure differs")
    if crc.get("provider_resolution") != {
        "earlier_module_imports": 328,
        "fixed_image_imports": 3238,
        "total_resolved_imports": 3566,
    }:
        raise AuditError("P319 provider-resolution partition differs")

    return {
        "module_count": len(rows),
        "eud_index": phase["plan"]["eud_index"],
        "declared_dependency_edges": len(dependency_edges),
        "missing_declared_dependencies": missing,
        "dependency_order_violations": violations,
        "audited_ssusb_module_set": required_positions,
        "audited_ssusb_modules_precede_dwc3_msm": True,
        "dwc3_msm_index": positions["dwc3-msm.ko"],
        "pmic_glink_index": positions["pmic_glink.ko"],
        "ucsi_glink_index": positions["ucsi_glink.ko"],
        "pdic_max77705_index": positions["pdic_max77705.ko"],
        "qcom_q6v5_pas_present": "qcom_q6v5_pas.ko" in positions,
        "qcom_q6v5_present": "qcom_q6v5.ko" in positions,
        "crc_provider_closure": {
            key: crc[key]
            for key in (
                "module_count", "total_imports", "ordered_crc_closed",
                "missing_provider_count", "ambiguous_provider_count",
                "duplicate_provider_count", "provider_resolution",
            )
        },
        "terminal_gates": gates[-3:],
        "verified": True,
    }


def audit_vendor_ramdisk(
    ramdisk: bytes,
    phase: dict[str, Any],
) -> dict[str, Any]:
    cpio = boot_verify.decompress_lz4_stream_python(
        ramdisk, expected_size=63_974_144, maximum=80 * 1024 * 1024
    )
    entries = boot_verify.parse_newc(cpio)
    by_name = {entry.name: entry for entry in entries}
    if len(entries) != 452 or len(by_name) != len(entries):
        raise AuditError("vendor ramdisk newc population differs")
    recovery_entry = by_name.get("lib/modules/modules.load.recovery")
    first_entry = by_name.get("lib/modules/modules.load")
    if recovery_entry is None or first_entry is None:
        raise AuditError("vendor ramdisk module lists are absent")
    recovery_bytes = recovery_entry.data
    first_bytes = first_entry.data
    if identity(recovery_bytes) != {
        "size": 7_239,
        "sha256": "616bdb71f2b68d76eca23f72883aea25d5202d4e14f5c99dd934720df863ac10",
    }:
        raise AuditError("modules.load.recovery identity differs")
    if identity(first_bytes) != {
        "size": 2_228,
        "sha256": "8491b842e6e05cfba42694ad003301a6598e8d152ec10cc8f0cc6fb17f10e232",
    }:
        raise AuditError("modules.load identity differs")
    recovery = [line for line in ascii_text(recovery_bytes, "recovery list").splitlines() if line]
    first = [line for line in ascii_text(first_bytes, "first-stage list").splitlines() if line]
    if len(recovery) != 446 or len(set(recovery)) != 441:
        raise AuditError("recovery module-list cardinality differs")

    rows = phase["plan"]["rows"]
    stock_rows = [row for row in rows if row["file"] != "s22plus_dwc3_event_latch.ko"]
    if len(stock_rows) != 72 or any(row["file"] not in recovery for row in stock_rows):
        raise AuditError("P319 stock rows are not a recovery-list subset")
    mismatches: list[str] = []
    for row in stock_rows:
        entry = by_name.get(f"lib/modules/{row['file']}")
        phase_module = next(
            item for item in phase["module_crc_closure"]["modules"]
            if item["file"] == row["file"]
        )
        if entry is None or identity(entry.data) != {
            "size": phase_module["size"], "sha256": phase_module["sha256"]
        }:
            mismatches.append(row["file"])
    if mismatches:
        raise AuditError(f"P319/vendor-ramdisk module bytes differ: {mismatches}")

    return {
        "compressed_ramdisk": identity(ramdisk),
        "newc_size": len(cpio),
        "newc_entry_count": len(entries),
        "modules_load": {**identity(first_bytes), "line_count": len(first)},
        "modules_load_recovery": {
            **identity(recovery_bytes),
            "line_count": len(recovery),
            "unique_count": len(set(recovery)),
        },
        "candidate_plan_rows_in_recovery": 72,
        "candidate_stock_row_count": 72,
        "candidate_custom_row_count": 1,
        "candidate_stock_module_bytes_identical_to_vendor_ramdisk": 72,
        "candidate_rows_in_first_stage_list": sum(
            row["file"] in first for row in stock_rows
        ),
        "recovery_unique_members_outside_candidate": len(set(recovery) - {row["file"] for row in stock_rows}),
        "only_non_recovery_candidate_row": "s22plus_dwc3_event_latch.ko",
        "verified": True,
    }


def audit_image(image: bytes) -> dict[str, Any]:
    config = boot_boundary.extract_ikconfig(IMAGE)
    if any(config.get(key) != value for key, value in REQUIRED_CONFIG.items()):
        raise AuditError("fixed Image DWC3/gadget config differs")
    if stable_bytes(IMAGE, "post-IKCONFIG fixed Image", 64 * 1024 * 1024, EXPECTED["image"]) != image:
        raise AuditError("fixed Image changed during IKCONFIG extraction")
    return {
        "image": identity(image),
        "required_config": {key: config[key] for key in sorted(REQUIRED_CONFIG)},
        "additional_config": {
            key: config.get(key, "unset")
            for key in (
                "CONFIG_USB_DWC3_GADGET",
                "CONFIG_USB_DWC3_HOST",
                "CONFIG_USB_DWC3_QCOM",
            )
        },
        "dwc3_core_built_in": config["CONFIG_USB_DWC3"] == "y",
        "gadget_core_built_in": config["CONFIG_USB_GADGET"] == "y",
        "ucsi_core_built_in": config["CONFIG_TYPEC_UCSI"] == "y",
        "verified": True,
    }


def audit_mode_producer(module_payload: bytes) -> dict[str, Any]:
    path = MODULE_DIR / "dwc3-msm.ko"
    symbols, by_address = static_re.parse_symbols(path)
    calls = static_re.parse_call_edges(path, by_address)
    if stable_bytes(path, "post-static dwc3-msm", 1024 * 1024) != module_payload:
        raise AuditError("dwc3-msm changed during static analysis")
    for name, (address, size) in MODE_SYMBOLS.items():
        row = symbols.get(name, {})
        if row.get("address") != address or row.get("size") != size:
            raise AuditError(f"dwc3-msm symbol differs: {name}")
    required_edges = {
        ("mode_store", "dwc3_msm_set_role"),
        ("dwc3_msm_set_role", "dwc3_ext_event_notify"),
        ("dwc3_msm_usb_role_switch_set_role", "dwc3_msm_set_role"),
        ("dwc3_msm_probe", "usb_role_switch_register"),
        ("dwc3_otg_start_peripheral", "usb_gadget_connect"),
    }
    if not required_edges.issubset(calls):
        raise AuditError("dwc3-msm role/UDC call edges differ")
    info = modinfo_from_bytes(module_payload, "dwc3-msm.ko")
    aliases = set(info.get("alias", []))
    if "of:N*T*Cqcom,dwc-usb3-msm" not in aliases:
        raise AuditError("dwc3-msm OF alias differs")
    return {
        "module": identity(module_payload),
        "of_alias": "qcom,dwc-usb3-msm",
        "symbols": {
            name: {"address": hex(address), "size": size}
            for name, (address, size) in MODE_SYMBOLS.items()
        },
        "required_call_edges": [f"{caller}->{callee}" for caller, callee in sorted(required_edges)],
        "direct_mode_path": [
            "mode_store",
            "dwc3_msm_set_role",
            "dwc3_ext_event_notify",
        ],
        "peripheral_start_connect_edge": "dwc3_otg_start_peripheral->usb_gadget_connect",
        "verified": True,
    }


def require_order(text: str, label: str, tokens: tuple[str, ...]) -> list[int]:
    try:
        positions = [text.index(token) for token in tokens]
    except ValueError as exc:
        raise AuditError(f"{label} lacks an ordered token") from exc
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise AuditError(f"{label} ordering differs")
    return positions


def audit_runtime(wrapper_data: bytes, runtime_data: bytes, role_data: bytes) -> dict[str, Any]:
    wrapper = ascii_text(wrapper_data, "P319 wrapper")
    runtime = ascii_text(runtime_data, "P319 runtime")
    role = ascii_text(role_data, "P319 role source")
    wrapper_positions = require_order(
        wrapper,
        "P319 module/gate wrapper",
        (
            "for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index)",
            "for (size_t index = P305_FOLDED_MODULE_INDEX;",
            "while (completed < S22PLUS_O2_BIND_GATE_COUNT)",
            "p290_e3_run();",
        ),
    )
    for token in (
        "long p319_post_load_rc = p319_after_module_load(index, 0L);",
        "long p319_post_load_rc = p319_after_module_load(index, p305_folded_load_rc);",
        "static long p282_role_write_once(uint32_t *byte_count)",
        'static const char role[] = "peripheral";',
        "record.result = p282_role_write_once(&byte_count);",
        "rc = p282_phase_role(&role_warning, tty_fd);",
    ):
        if token not in wrapper + runtime:
            raise AuditError(f"P319 runtime token differs: {token}")
    for token in (
        'static const char p260_udc_name[] = "a600000.dwc3";',
        '"/sys/devices/platform/soc/a600000.ssusb/mode";',
        "rc = p260_write_value(p260_role_path, \"peripheral\");",
        '"/config/usb_gadget/g1/UDC",',
    ):
        if token not in role:
            raise AuditError(f"P319 direct-role source token differs: {token}")
    return {
        "module_loops_precede_bind_gates": wrapper_positions[1] < wrapper_positions[2],
        "all_bind_gates_precede_experiment_runtime": wrapper_positions[2] < wrapper_positions[3],
        "direct_and_folded_post_load_hooks_present": True,
        "ssusb_dwc3_udc_gates_precede_role_write": True,
        "direct_role_write_paths": ["p260_wait_role_and_udc", "p282_role_write_once"],
        "direct_role_value": "peripheral",
        "exact_role_path": "/sys/devices/platform/soc/a600000.ssusb/mode",
        "exact_udc": "a600000.dwc3",
        "verified": True,
    }


def build_result() -> dict[str, Any]:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        raise AuditError("auditor is not bound to its source bytes")
    paths = {
        "phase_result": PHASE_RESULT,
        "plan_source": PLAN_SOURCE,
        "wrapper_source": WRAPPER_SOURCE,
        "runtime_source": RUNTIME_SOURCE,
        "role_source": ROLE_SOURCE,
        "image": IMAGE,
        "vendor_ramdisk": VENDOR_RAMDISK,
        "vendor_dtb": VENDOR_DTB,
    }
    limits = {
        "phase_result": 2 * 1024 * 1024,
        "plan_source": 64 * 1024,
        "wrapper_source": 128 * 1024,
        "runtime_source": 1024 * 1024,
        "role_source": 128 * 1024,
        "image": 64 * 1024 * 1024,
        "vendor_ramdisk": 32 * 1024 * 1024,
        "vendor_dtb": 4 * 1024 * 1024,
    }
    data = {
        name: stable_bytes(path, name, limits[name], EXPECTED[name])
        for name, path in paths.items()
    }
    helper_data = {
        name: stable_bytes(path, f"helper {name}", 2 * 1024 * 1024)
        for name, path in HELPERS.items()
    }
    phase = json_object(data["phase_result"], "P319 phase result")
    if (
        phase.get("schema") != "s22plus-fyg8-p319-stock-witness-runtime-v1"
        or phase.get("verdict") != "PASS_P319_STOCK_WITNESS_RUNTIME_H0"
        or phase.get("target") != TARGET
        or phase.get("scope", {}).get("device_contact") is not False
    ):
        raise AuditError("P319 phase authority differs")
    module_payloads = {
        row["file"]: stable_bytes(
            MODULE_DIR / row["file"],
            f"module {row['file']}",
            2 * 1024 * 1024,
            (row["size"], row["sha256"]),
        )
        for row in phase["module_crc_closure"]["modules"]
    }

    plan = audit_plan(phase, data["plan_source"], module_payloads)
    vendor = audit_vendor_ramdisk(data["vendor_ramdisk"], phase)
    direct_dtb = p251.audit_vendor_dtb(data["vendor_dtb"])
    nested_dtb = p251b.audit_vendor_dtb(data["vendor_dtb"])
    image = audit_image(data["image"])
    mode = audit_mode_producer(module_payloads["dwc3-msm.ko"])
    runtime = audit_runtime(
        data["wrapper_source"], data["runtime_source"], data["role_source"]
    )

    for name, path in HELPERS.items():
        if stable_bytes(path, f"post-run helper {name}", 2 * 1024 * 1024) != helper_data[name]:
            raise AuditError(f"helper changed during execution: {name}")
    if stable_bytes(Path(__file__), "post-run auditor", 1024 * 1024) != _BOUND_AUDITOR_SOURCE:
        raise AuditError("auditor changed during execution")

    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": "IMPLEMENTED_REVIEW_PENDING",
        "target": TARGET,
        "scope": {
            "tier": "H0",
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "usb_actions": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "recovery_actions": 0,
            "candidate_bytes_changed": False,
            "live_authority_created": False,
        },
        "implementation": {"auditor": identity(_BOUND_AUDITOR_SOURCE)},
        "inputs": {
            **{name: identity(payload) for name, payload in sorted(data.items())},
            "helpers": {name: identity(payload) for name, payload in sorted(helper_data.items())},
        },
        "plan_closure": plan,
        "recovery_control_comparison": vendor,
        "device_tree": {
            "direct": direct_dtb,
            "nested": nested_dtb,
        },
        "fixed_image": image,
        "mode_producer": mode,
        "runtime": runtime,
        "conclusion": {
            "known_ssusb_module_membership_closed": True,
            "all_declared_module_dependencies_closed_and_ordered": True,
            "all_72_vendor_module_bytes_match_vendor_ramdisk": True,
            "dwc3_core_and_gadget_support_built_in": True,
            "mode_attribute_exact_producer_bound": True,
            "direct_mode_write_bypasses_ucsi_role_production": True,
            "natural_ucsi_stock_path_closed": False,
            "natural_ucsi_limit": (
                "ucsi_glink and built-in UCSI core are present, but qcom_q6v5_pas/"
                "qcom_q6v5 are absent from the plan; another channel producer is "
                "not established either way, and the direct mode write does not "
                "require this stock role path"
            ),
            "dynamic_supplier_bind_proved": False,
            "dwc3_msm_probe_success_proved": False,
            "candidate_udc_creation_proved": False,
            "missing_module_is_evidence_based_next_hypothesis": False,
            "next_discriminator": (
                "retain the existing ssusb/dwc3/UDC gates and waiting_for_supplier/"
                "provider diagnostics; do not grow the module plan"
            ),
        },
    }


def encode(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def run() -> tuple[dict[str, Any], bytes]:
    result = build_result()
    return result, encode(result)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish(payload: bytes) -> None:
    parent = OUTPUT.parent
    if parent.exists() or parent.is_symlink():
        raise AuditError("output directory already exists")
    parent.mkdir(mode=0o700, parents=True)
    parent.chmod(0o700)
    descriptor = os.open(
        OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError("short result write")
            offset += written
        os.fsync(descriptor)
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or stat.S_IMODE(state.st_mode) != 0o400
            or state.st_nlink != 1
            or state.st_size != len(payload)
        ):
            raise AuditError("result metadata differs")
    finally:
        os.close(descriptor)
    _fsync_directory(parent)


def main() -> int:
    if type(_BOUND_AUDITOR_SOURCE) is not bytes:
        return load_bound_auditor().main()
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    _result, payload = run()
    if args.write:
        publish(payload)
    else:
        existing = stable_bytes(
            OUTPUT,
            "private closure receipt",
            2 * 1024 * 1024,
            (len(payload), sha256(payload)),
        )
        if existing != payload:
            raise AuditError("private closure receipt differs")
    print(f"{VERDICT} {len(payload)} {sha256(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
