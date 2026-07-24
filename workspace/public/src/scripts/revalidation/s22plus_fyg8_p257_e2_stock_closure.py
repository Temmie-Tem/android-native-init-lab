#!/usr/bin/env python3
"""Proof-bound P2.57 stock-rootfs closure for the 60-module plan."""

from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
import sys
from typing import Any

import s22plus_fyg8_p242_e2_stock_closure as p242
import s22plus_fyg8_p253_e2_stock_closure as p253
import s22plus_fyg8_p257_source_contract as source_contract
import s22plus_o2_module_plan as planner


ClosureError = p242.ClosureError
SCHEMA = p242.SCHEMA
ORDER_MODEL = p242.ORDER_MODEL
EXPECTED_ELF_ENTRYPOINTS = dict(p253.EXPECTED_ELF_ENTRYPOINTS)
EXPECTED_GENERIC_ENTRY_COUNT = p242.EXPECTED_GENERIC_ENTRY_COUNT
DEFAULT_VENDOR_RAMDISK = p242.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = p242.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = p242.DEFAULT_LZ4
boot_verify = p242.boot_verify
receipt = p242.receipt
closure_sha256 = p242.closure_sha256

EXPECTED_MODULE_COUNT = 60
EXPECTED_PLAN_TSV_SHA256 = (
    "02a4f054941001b08ac7b53b79a2278ab4915081573b1d1ee8770a8f61ab96a6"
)
EXPECTED_MODULE_CLOSURE_SHA256 = (
    "0d1e8830f382eaa6b618337e3cac39481e91487302546e2acbc6bdc4b571c510"
)
EXPECTED_DISPCC = {
    "index": source_contract.spec.DISPCC_INSERTION.index,
    "file": source_contract.spec.DISPCC_INSERTION.file,
    "runtime_name": source_contract.spec.DISPCC_INSERTION.runtime_name,
    "size": 116168,
    "sha256": "7e4c404e639996982bdbcc08350139a09ab13b24de90cade81f8cfc8d71dacc5",
}


def select(source_contract_id: str | None):
    source_contract.require(source_contract_id, "E2")
    return sys.modules[__name__]


def _derived_plan(root: Path) -> tuple[planner.ModuleMetadata, planner.ModulePlan]:
    metadata = planner.load_metadata(root / planner.DEFAULT_METADATA_DIR)
    planner.verify_fyg8_pins(metadata)
    historical = planner.build_e2_profile_plan(metadata)
    planner.verify_e2_profile_plan_identity(metadata, historical)
    insertion = source_contract.spec.DISPCC_INSERTION
    if (
        len(historical.modules)
        != source_contract.spec.HISTORICAL_MODULE_PLAN_COUNT
        or insertion.file in historical.modules
        or not 0 <= insertion.index < len(historical.modules)
    ):
        raise ClosureError("P2.57 historical module insertion point changed")
    plan = replace(
        historical,
        modules=(
            historical.modules[: insertion.index]
            + (insertion.file,)
            + historical.modules[insertion.index :]
        ),
    )
    planner.validate_plan_contract(metadata, plan)
    if (
        len(plan.modules) != EXPECTED_MODULE_COUNT
        or planner.sha256_text(planner.render_plan_tsv(metadata, plan))
        != EXPECTED_PLAN_TSV_SHA256
    ):
        raise ClosureError("P2.57 derived module plan identity changed")
    return metadata, plan


def validate_module_closure(
    value: Any, *, allow_unpinned: bool = False
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClosureError("P2.57 stock module closure shape mismatch")
    rows = value.get("modules")
    if (
        not isinstance(rows, list)
        or len(rows) != EXPECTED_MODULE_COUNT
        or any(
            not isinstance(row, dict)
            or row.get("index") != index
            for index, row in enumerate(rows)
        )
    ):
        raise ClosureError("P2.57 stock module rows are malformed")
    files = [row.get("file") for row in rows]
    runtime_names = [row.get("runtime_name") for row in rows]
    if (
        value.get("count") != EXPECTED_MODULE_COUNT
        or value.get("files") != files
        or value.get("runtime_names") != runtime_names
        or len(set(files)) != EXPECTED_MODULE_COUNT
        or len(set(runtime_names)) != EXPECTED_MODULE_COUNT
        or value.get("constraint_count") != 210
        or value.get("plan_tsv_sha256") != EXPECTED_PLAN_TSV_SHA256
        or value.get("plan_header")
        != receipt(source_contract.generate()["plan"])
        or rows[source_contract.spec.DISPCC_INSERTION.index]
        != EXPECTED_DISPCC
    ):
        raise ClosureError("P2.57 dispcc or generated plan identity mismatch")
    p253.validate_module_closure(_legacy_view(value))
    digest = closure_sha256(value)
    if not allow_unpinned and digest != EXPECTED_MODULE_CLOSURE_SHA256:
        raise ClosureError(
            f"P2.57 stock module closure digest mismatch: {digest}"
        )
    return value


def _legacy_view(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    rows = result.get("modules")
    if not isinstance(rows, list) or len(rows) != EXPECTED_MODULE_COUNT:
        raise ClosureError("P2.57 legacy module view is unavailable")
    if rows.pop(source_contract.spec.DISPCC_INSERTION.index) != EXPECTED_DISPCC:
        raise ClosureError("P2.57 legacy module view lost exact dispcc")
    for index, row in enumerate(rows):
        row["index"] = index
    result["files"] = [row["file"] for row in rows]
    result["runtime_names"] = [row["runtime_name"] for row in rows]
    result["count"] = 59
    result["plan_tsv_sha256"] = planner.EXPECTED_E2_PROFILE_PLAN_TSV_SHA256
    result["plan_header"] = dict(p253.p245.P245_PLAN_HEADER)
    p253.validate_module_closure(result)
    return result


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    generated_plan = source_contract.generate(root)["plan"]
    if plan_header is not None:
        supplied = p242.p241.stable_read(
            plan_header, "P2.57 generated E2 plan header", 1024 * 1024
        )
        if supplied != generated_plan:
            raise ClosureError("P2.57 supplied plan differs from generator")
    metadata, plan = _derived_plan(root)
    module_audit = p242.p241.audit_vendor_modules(
        root, vendor_ramdisk, lz4, plan
    )
    result = {
        "schema": SCHEMA,
        "files": [row["file"] for row in module_audit["modules"]],
        "runtime_names": [
            row["runtime_name"] for row in module_audit["modules"]
        ],
        "count": module_audit["module_count"],
        "modules": module_audit["modules"],
        "order_model": ORDER_MODEL,
        "constraint_count": len(plan.constraints),
        "plan_tsv_sha256": planner.sha256_text(
            planner.render_plan_tsv(metadata, plan)
        ),
        "plan_header": receipt(generated_plan),
        "foundation": list(planner.E2_PROVEN_E1B_FOUNDATION),
        "vendor_ramdisk": module_audit["vendor_ramdisk"],
        "vendor_entry_count": module_audit["entry_count"],
        "request_firmware_string_hits": module_audit[
            "request_firmware_string_hits"
        ],
        "sec_log_buf_absent": module_audit["sec_log_buf_absent"],
        "verified": True,
    }
    return validate_module_closure(result)


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = validate_module_closure(module_closure)
    result = p253.audit_candidate_generic_rootfs(
        boot,
        entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=_legacy_view(closure),
    )
    _require_dispcc_runtime(entries)
    return result


def _require_dispcc_runtime(entries) -> None:
    init_entries = [entry for entry in entries if entry.name == "init"]
    if len(init_entries) != 1:
        raise ClosureError("P2.57 candidate init is not unique")
    data = init_entries[0].data
    if (
        data.count(source_contract.spec.DISPCC_INSERTION.file.encode("ascii"))
        != 1
        or data.count(
            source_contract.spec.DISPCC_INSERTION.runtime_name.encode("ascii")
        )
        != 1
    ):
        raise ClosureError("P2.57 candidate init lacks exact dispcc runtime")


def _dispcc_effective_row(vendor_boot: bytes, lz4_tool: Path) -> dict[str, str]:
    vendor = boot_verify.parse_vendor_boot_v4(vendor_boot)
    found = []
    for index, fragment in enumerate(vendor.fragments):
        label = f"vendor[{index}]/{fragment.name}"
        entries = boot_verify.parse_newc(
            boot_verify.decompress_lz4(lz4_tool, fragment.data)
        )
        found.extend(
            (label, entry)
            for entry in entries
            if entry.name
            == f"lib/modules/{source_contract.spec.DISPCC_INSERTION.file}"
        )
    if len(found) != 1:
        raise ClosureError("P2.57 effective dispcc module is not unique")
    label, entry = found[0]
    if (
        entry.file_type != "regular"
        or receipt(entry.data)
        != {
            "size": EXPECTED_DISPCC["size"],
            "sha256": EXPECTED_DISPCC["sha256"],
        }
    ):
        raise ClosureError("P2.57 effective dispcc module identity mismatch")
    return {
        "file": EXPECTED_DISPCC["file"],
        "runtime": EXPECTED_DISPCC["runtime_name"],
        "layer": label,
    }


def rootfs_audit(
    candidate: bytes,
    vendor_boot: bytes,
    lz4_tool: Path,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = validate_module_closure(module_closure)
    result = p253.rootfs_audit(
        candidate,
        vendor_boot,
        lz4_tool,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=_legacy_view(closure),
    )
    boot = boot_verify.parse_boot_v4(candidate)
    generic_entries = boot_verify.parse_newc(
        boot_verify.decompress_lz4(lz4_tool, boot.ramdisk)
    )
    _require_dispcc_runtime(generic_entries)
    result["modules"].insert(
        source_contract.spec.DISPCC_INSERTION.index,
        _dispcc_effective_row(vendor_boot, lz4_tool),
    )
    result["module_count"] = EXPECTED_MODULE_COUNT
    result["module_closure_sha256"] = closure_sha256(closure)
    validate_effective_rootfs(
        result,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=closure,
    )
    return result


def validate_effective_rootfs(
    value: Any,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = validate_module_closure(module_closure)
    if not isinstance(value, dict):
        raise ClosureError("P2.57 effective rootfs shape mismatch")
    expected_modules = [
        {
            "file": row["file"],
            "runtime": row["runtime_name"],
            "layer": "vendor[0]/",
        }
        for row in closure["modules"]
    ]
    if (
        value.get("modules") != expected_modules
        or value.get("module_count") != EXPECTED_MODULE_COUNT
        or value.get("module_closure_sha256")
        != closure_sha256(closure)
    ):
        raise ClosureError("P2.57 effective module closure mismatch")
    legacy_value = copy.deepcopy(value)
    legacy_value["modules"].pop(source_contract.spec.DISPCC_INSERTION.index)
    legacy_value["module_count"] = (
        source_contract.spec.HISTORICAL_MODULE_PLAN_COUNT
    )
    legacy_closure = _legacy_view(closure)
    legacy_value["module_closure_sha256"] = closure_sha256(
        legacy_closure
    )
    p253.validate_effective_rootfs(
        legacy_value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=legacy_closure,
    )
    return value


def build_result(root: Path | None = None) -> dict[str, Any]:
    repository = (
        source_contract.p243.repo_root() if root is None else root
    )
    closure = derive_module_closure(
        repository,
        repository / DEFAULT_VENDOR_RAMDISK,
        repository / DEFAULT_LZ4,
    )
    return {
        "schema": "s22plus_fyg8_p257_stock_closure_h0_v1",
        "verdict": "PASS_P257_STOCK_CLOSURE_HOST_ONLY",
        "contract_id": source_contract.CONTRACT_ID,
        "module_count": closure["count"],
        "plan_header": closure["plan_header"],
        "dispcc": closure["modules"][
            source_contract.spec.DISPCC_INSERTION.index
        ],
        "module_closure_sha256": closure_sha256(closure),
        "verified": True,
        "safety": {
            "host_only": True,
            "kernel_built": False,
            "image_built": False,
            "candidate_created": False,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "live_authorized": False,
        },
    }
