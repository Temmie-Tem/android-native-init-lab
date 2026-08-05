#!/usr/bin/env python3
"""Proof-bound 61-module stock closure for the P3.04 notifier bridge."""

from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p241_e2_static_checker as p241
import s22plus_fyg8_p257_e2_stock_closure as p257
import s22plus_fyg8_p300_e2_stock_closure as parent
import s22plus_fyg8_p304_overlay_contract as overlay
import s22plus_fyg8_p304_plan_transform as plan_spec


ClosureError = parent.ClosureError
SCHEMA = "s22plus_fyg8_p304_stock_closure_h0_v1"
VERDICT = "PASS_P304_STOCK_61_MODULE_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_COUNT = plan_spec.MODULE_PLAN_COUNT
DEFAULT_VENDOR_RAMDISK = parent.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = parent.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = parent.DEFAULT_LZ4
boot_verify = parent.boot_verify
receipt = parent.receipt


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def closure_sha256(value: dict[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "closure_sha256"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def _expanded_plan(root: Path):  # noqa: ANN201
    metadata, old = p257._derived_plan(root)  # noqa: SLF001
    if plan_spec.MODULE_NAME in old.modules or old.modules.count("dwc3-msm.ko") != 1:
        raise ClosureError("P3.04 parent module plan differs")
    index = old.modules.index("dwc3-msm.ko") + 1
    expanded = replace(
        old,
        modules=old.modules[:index] + (plan_spec.MODULE_NAME,) + old.modules[index:],
    )
    if (
        len(expanded.modules) != EXPECTED_MODULE_COUNT
        or expanded.modules[index - 1 : index + 2]
        != ("dwc3-msm.ko", plan_spec.MODULE_NAME, "ucsi_glink.ko")
    ):
        raise ClosureError("P3.04 expanded module order differs")
    return metadata, expanded, index


def select(source_contract_id: str | None):
    if source_contract_id != overlay.PARENT_SOURCE_CONTRACT_ID:
        raise ClosureError("P3.04 source contract differs")
    return __import__(__name__)


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    if plan_header is None:
        raise ClosureError("P3.04 exact materialized plan is missing")
    exact = overlay.verify_intent(root, root / overlay.DEFAULT_INTENT)
    supplied = p241.stable_read(plan_header, "P3.04 materialized plan", 1024 * 1024)
    expected_plan = exact["generated_artifacts"]["plan_header"]
    if receipt(supplied) != expected_plan:
        raise ClosureError("P3.04 supplied plan identity differs")
    names = plan_spec.module_names(supplied)
    _metadata, expanded, insertion = _expanded_plan(root)
    if names != expanded.modules:
        raise ClosureError("P3.04 supplied plan order differs")
    parent_closure = parent.derive_module_closure(
        root, vendor_ramdisk, lz4, plan_header=None
    )
    audit = p241.audit_vendor_modules(root, vendor_ramdisk, lz4, expanded)
    notifier = audit["modules"][insertion]
    if (
        notifier.get("file") != plan_spec.MODULE_NAME
        or notifier.get("runtime_name") != plan_spec.MODULE_RUNTIME
        or {key: notifier.get(key) for key in ("size", "sha256")}
        != {"size": overlay.MODULE_SIZE, "sha256": overlay.MODULE_SHA256}
    ):
        raise ClosureError("P3.04 effective stock notifier identity differs")
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "files": [row["file"] for row in audit["modules"]],
        "runtime_names": [row["runtime_name"] for row in audit["modules"]],
        "count": audit["module_count"],
        "modules": audit["modules"],
        "insertion_index": insertion,
        "plan_header": receipt(supplied),
        "parent_closure": parent_closure,
        "parent_closure_sha256": parent.closure_sha256(parent_closure),
        "vendor_ramdisk": audit["vendor_ramdisk"],
        "vendor_entry_count": audit["entry_count"],
        "request_firmware_string_hits": audit["request_firmware_string_hits"],
        "sec_log_buf_absent": audit["sec_log_buf_absent"],
        "verified": True,
    }
    result["closure_sha256"] = closure_sha256(result)
    return validate_module_closure(result)


def validate_module_closure(value: Any, *, allow_unpinned: bool = False):
    del allow_unpinned
    if not isinstance(value, dict):
        raise ClosureError("P3.04 stock module closure shape differs")
    rows = value.get("modules")
    insertion = value.get("insertion_index")
    if (
        not isinstance(rows, list)
        or len(rows) != EXPECTED_MODULE_COUNT
        or insertion != next(
            (index for index, row in enumerate(rows) if row.get("file") == plan_spec.MODULE_NAME),
            None,
        )
        or any(row.get("index") != index for index, row in enumerate(rows))
        or value.get("files") != [row.get("file") for row in rows]
        or value.get("runtime_names") != [row.get("runtime_name") for row in rows]
        or value.get("count") != EXPECTED_MODULE_COUNT
        or len(set(value["files"])) != EXPECTED_MODULE_COUNT
        or len(set(value["runtime_names"])) != EXPECTED_MODULE_COUNT
        or rows[insertion - 1]["file"] != "dwc3-msm.ko"
        or rows[insertion + 1]["file"] != "ucsi_glink.ko"
        or {key: rows[insertion].get(key) for key in ("size", "sha256")}
        != {"size": overlay.MODULE_SIZE, "sha256": overlay.MODULE_SHA256}
        or value.get("verified") is not True
        or value.get("closure_sha256") != closure_sha256(value)
    ):
        raise ClosureError("P3.04 61-module closure differs")
    parent.validate_module_closure(value.get("parent_closure"))
    return value


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
    result = parent.rootfs_audit(
        candidate,
        vendor_boot,
        lz4_tool,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=closure["parent_closure"],
    )
    insertion = closure["insertion_index"]
    row = closure["modules"][insertion]
    vendor = boot_verify.parse_vendor_boot_v4(vendor_boot)
    found = []
    for index, fragment in enumerate(vendor.fragments):
        entries = boot_verify.parse_newc(
            boot_verify.decompress_lz4(lz4_tool, fragment.data)
        )
        found.extend(
            (f"vendor[{index}]/{fragment.name}", entry)
            for entry in entries
            if entry.name == f"lib/modules/{plan_spec.MODULE_NAME}"
        )
    if len(found) != 1:
        raise ClosureError("P3.04 effective notifier module is not unique")
    label, entry = found[0]
    if entry.file_type != "regular" or receipt(entry.data) != {
        "size": row["size"],
        "sha256": row["sha256"],
    }:
        raise ClosureError("P3.04 effective notifier module differs")
    result = copy.deepcopy(result)
    result["modules"].insert(
        insertion,
        {"file": row["file"], "runtime": row["runtime_name"], "layer": label},
    )
    result["module_count"] = EXPECTED_MODULE_COUNT
    result["module_closure_sha256"] = closure["closure_sha256"]
    return validate_effective_rootfs(
        result,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=closure,
    )


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
):
    closure = validate_module_closure(module_closure)
    adapter = parent.p282.p280
    parent_generic_closure = adapter.isolated_p260.p253._legacy_view(  # noqa: SLF001
        adapter.isolated_p260.p257._legacy_view(  # noqa: SLF001
            closure["parent_closure"]
        )
    )
    result = parent.audit_candidate_generic_rootfs(
        boot,
        entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=parent_generic_closure,
    )
    init_entries = [entry for entry in entries if entry.name == "init"]
    if (
        len(init_entries) != 1
        or init_entries[0].data.count(plan_spec.MODULE_NAME.encode("ascii")) != 1
        or init_entries[0].data.count(
            plan_spec.MODULE_RUNTIME.encode("ascii") + b"\0"
        ) != 1
    ):
        raise ClosureError("P3.04 candidate init lacks the exact notifier bridge")
    return result


def validate_effective_rootfs(
    value: Any,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    module_closure: dict[str, Any],
):
    closure = validate_module_closure(module_closure)
    if not isinstance(value, dict):
        raise ClosureError("P3.04 effective rootfs shape differs")
    expected_modules = [
        {"file": row["file"], "runtime": row["runtime_name"], "layer": "vendor[0]/"}
        for row in closure["modules"]
    ]
    if (
        value.get("modules") != expected_modules
        or value.get("module_count") != EXPECTED_MODULE_COUNT
        or value.get("module_closure_sha256") != closure["closure_sha256"]
    ):
        raise ClosureError("P3.04 effective module closure differs")
    legacy = copy.deepcopy(value)
    legacy["modules"].pop(closure["insertion_index"])
    legacy["module_count"] = EXPECTED_MODULE_COUNT - 1
    legacy["module_closure_sha256"] = parent.closure_sha256(
        closure["parent_closure"]
    )
    parent.validate_effective_rootfs(
        legacy,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=closure["parent_closure"],
    )
    return value
