#!/usr/bin/env python3
"""Validate the unchanged P3.17 69-stock substrate under P3.18's 70 plan.

The first P3.18 early-plan row is a separately ABI-qualified custom latch.
This adapter removes exactly that one row before invoking the reviewed P3.17
stock-rootfs closure; it never treats the custom binary as stock input.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
from pathlib import Path
import tempfile
from typing import Any

import s22plus_fyg8_p317_e2_stock_closure as base


SCHEMA = "s22plus_fyg8_p318_stock_closure_h0_v1"
VERDICT = "PASS_P318_UNCHANGED_69_STOCK_PLUS_SEPARATE_EARLY_LATCH_HOST_ONLY"
PARENT_SOURCE_CONTRACT_ID = base.PARENT_SOURCE_CONTRACT_ID
EXPECTED_STOCK_MODULE_COUNT = 69
EXPECTED_EFFECTIVE_EARLY_COUNT = 70
LATCH_IDENTITY = (
    423232,
    "27be8abfe121867e50b0f8b2094fff1d615181e2e0168e5c37e9f8fab2364a2b",
)
DIAGNOSTIC_IDENTITY = (
    303112,
    "d7dac722a11b2df932083bc16a6fac209ef1d90654d529b25391d85c6e1dec85",
)
LATCH_PATH = "lib/modules/s22plus_dwc3_event_latch.ko"
DIAGNOSTIC_PATH = "lib/modules/s22plus_max77705_mux_diag_p318.ko"
P318_AUTHORITY_PATHS = frozenset({
    "/sys/module/s22plus_dwc3_event_latch/parameters/expose_gate",
    "/sys/module/s22plus_dwc3_event_latch/parameters/snapshot",
    "/sys/module/s22plus_max77705_mux_diag_p318/parameters/result",
})
P317_RETIRED_DIAGNOSTIC_PATH = (
    "/sys/module/s22plus_max77705_mux_diag/parameters/result"
)
P318_OPERATIONAL_ABSOLUTE_PATH_STRINGS = frozenset({
    *(base.base.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS
      - {P317_RETIRED_DIAGNOSTIC_PATH}),
    *P318_AUTHORITY_PATHS,
})
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset({
    *(base.REQUIRED_ABSOLUTE_PATH_STRINGS - {P317_RETIRED_DIAGNOSTIC_PATH}),
    *P318_AUTHORITY_PATHS,
})
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset({
    *(base.ALLOWED_ABSOLUTE_PATH_STRINGS - {P317_RETIRED_DIAGNOSTIC_PATH}),
    *P318_AUTHORITY_PATHS,
})
INCIDENTAL_PATHS = frozenset({b"/E9B"})
LATCH_ROW = (
    b'    {"s22plus_dwc3_event_latch.ko", '
    b'"s22plus_dwc3_event_latch", ""},\n'
)
ClosureError = base.ClosureError


def select(source_contract_id: str | None):
    if source_contract_id != PARENT_SOURCE_CONTRACT_ID:
        raise ClosureError("P3.18 source contract differs")
    return __import__(__name__)


def closure_sha256(value: dict[str, Any]) -> str:
    return base.closure_sha256(value)


def _stock_plan(plan_header: Path) -> bytes:
    try:
        payload = plan_header.read_bytes()
    except OSError as exc:
        raise ClosureError("P3.18 materialized plan is unavailable") from exc
    if payload.count(LATCH_ROW) != 1 or payload.count(b'.ko"') != 70:
        raise ClosureError("P3.18 custom-early/stock plan boundary differs")
    stock = payload.replace(LATCH_ROW, b"", 1)
    if stock.count(b'.ko"') != 69:
        raise ClosureError("P3.18 stock plan projection differs")
    return stock


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
):
    if plan_header is None:
        raise ClosureError("P3.18 stock closure requires its materialized plan")
    import s22plus_fyg8_p317_overlay_contract as p317_overlay
    import s22plus_fyg8_p318_overlay_contract as p318_overlay

    intent_path = plan_header.parent.parent / "overlay-intent.json"
    exact = p318_overlay.verify_intent(root, intent_path)
    supplied = plan_header.read_bytes()
    supplied_receipt = {
        "size": len(supplied),
        "sha256": hashlib.sha256(supplied).hexdigest(),
    }
    if supplied_receipt != exact.get("generated_artifacts", {}).get("plan_header"):
        raise ClosureError("P3.18 supplied 70-row plan identity differs")
    stock = _stock_plan(plan_header)
    with tempfile.TemporaryDirectory(prefix="s22-p318-stock-plan-") as name:
        projected = Path(name) / "p317-stock-plan.h"
        projected.write_bytes(stock)
        stock_receipt = {
            "size": len(stock),
            "sha256": hashlib.sha256(stock).hexdigest(),
        }
        original_verify = p317_overlay.verify_intent

        def verify_frozen_projection(_root: Path, _intent_path: Path):
            return {"generated_artifacts": {"plan_header": stock_receipt}}

        p317_overlay.verify_intent = verify_frozen_projection
        try:
            return base.derive_module_closure(
                root, vendor_ramdisk, lz4, plan_header=projected
            )
        finally:
            p317_overlay.verify_intent = original_verify


def validate_module_closure(value: Any, *, allow_unpinned: bool = False):
    return base.validate_module_closure(value, allow_unpinned=allow_unpinned)


def _custom_descriptor(name: str, identity: tuple[int, str], *, early: bool):
    return {
        "file": Path(name).name,
        "layer": "generic",
        "size": identity[0],
        "sha256": identity[1],
        "early_plan_membership": early,
        "verified": True,
    }


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
):
    selected = validate_module_closure(module_closure)
    custom = {
        LATCH_PATH: LATCH_IDENTITY,
        DIAGNOSTIC_PATH: DIAGNOSTIC_IDENTITY,
    }
    for path, identity in custom.items():
        matches = [entry for entry in entries if entry.name == path]
        if (
            len(matches) != 1
            or matches[0].file_type != "regular"
            or base.base.module_parent.receipt(matches[0].data)
            != {"size": identity[0], "sha256": identity[1]}
        ):
            raise ClosureError(f"P3.18 generic custom module differs: {path}")
    if any(entry.name == "lib/modules/s22plus_max77705_mux_diag.ko" for entry in entries):
        raise ClosureError("P3.18 predecessor diagnostic survived")
    legacy_entries = tuple(entry for entry in entries if entry.name not in custom)
    result = base.base.parent.audit_candidate_generic_rootfs(
        boot,
        legacy_entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=selected["parent_closure"],
    )
    result = copy.deepcopy(result)
    result["latch_boot_module"] = _custom_descriptor(
        LATCH_PATH, LATCH_IDENTITY, early=True
    )
    result["diagnostic_boot_module"] = _custom_descriptor(
        DIAGNOSTIC_PATH, DIAGNOSTIC_IDENTITY, early=False
    )
    result["entry_count"] = len(entries)
    return result


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
    selected = validate_module_closure(module_closure)
    module_parent = base.base.module_parent
    boot = module_parent.boot_verify.parse_boot_v4(candidate)
    vendor = module_parent.boot_verify.parse_vendor_boot_v4(vendor_boot)
    generic_entries = module_parent.boot_verify.parse_newc(
        module_parent.boot_verify.decompress_lz4(lz4_tool, boot.ramdisk)
    )
    generic_rootfs = audit_candidate_generic_rootfs(
        boot,
        generic_entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=selected,
    )
    layers: list[tuple[str, tuple[Any, ...]]] = [("generic", generic_entries)]
    for index, fragment in enumerate(vendor.fragments):
        layers.append((
            f"vendor[{index}]/{fragment.name}",
            module_parent.boot_verify.parse_newc(
                module_parent.boot_verify.decompress_lz4(lz4_tool, fragment.data)
            ),
        ))
    seen: dict[str, tuple[str, Any]] = {}
    for label, layer_entries in layers:
        for entry in layer_entries:
            if entry.name in seen:
                raise ClosureError(f"P3.18 effective rootfs duplicate: {entry.name}")
            if entry.file_type == "symlink" or entry.nlink != 1:
                raise ClosureError(f"P3.18 effective rootfs alias: {label}:{entry.name}")
            seen[entry.name] = (label, entry)
    module_rows = []
    for row in selected["modules"]:
        value = seen.get(f"lib/modules/{row['file']}")
        if value is None:
            raise ClosureError(f"P3.18 effective module missing: {row['file']}")
        label, entry = value
        if (
            not label.startswith("vendor[")
            or entry.file_type != "regular"
            or module_parent.receipt(entry.data)
            != {"size": row["size"], "sha256": row["sha256"]}
        ):
            raise ClosureError(f"P3.18 effective module differs: {row['file']}")
        module_rows.append({
            "file": row["file"], "runtime": row["runtime_name"], "layer": label
        })
    if any(
        b"rdinit=" in value
        for value in (
            boot.header["cmdline"].encode("ascii"),
            vendor.cmdline.encode("ascii"),
            vendor.bootconfig,
        )
    ):
        raise ClosureError("P3.18 effective rootfs has an rdinit override")
    result = {
        "composition_order": [label for label, _entries in layers],
        "entry_count": len(seen),
        "generic_rootfs": generic_rootfs,
        "no_duplicate_override_or_alias": True,
        "init": {**expected_init, "elf": generic_rootfs["init"]["elf"], "run_id_count": 1},
        "child": {**expected_child, "elf": generic_rootfs["child"]["elf"]},
        "modules": module_rows,
        "module_count": EXPECTED_STOCK_MODULE_COUNT,
        "module_closure_sha256": selected["closure_sha256"],
        "rdinit_override_absent": True,
        "latch_boot_module": _custom_descriptor(LATCH_PATH, LATCH_IDENTITY, early=True),
        "diagnostic_boot_module": _custom_descriptor(
            DIAGNOSTIC_PATH, DIAGNOSTIC_IDENTITY, early=False
        ),
        "verified": True,
    }
    return validate_effective_rootfs(
        result,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=selected,
    )


def validate_effective_rootfs(
    value: Any,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    module_closure: dict[str, Any],
):
    selected = validate_module_closure(module_closure)
    if not isinstance(value, dict):
        raise ClosureError("P3.18 effective rootfs shape differs")
    expected_modules = [
        {"file": row["file"], "runtime": row["runtime_name"], "layer": "vendor[0]/"}
        for row in selected["modules"]
    ]
    if (
        value.get("modules") != expected_modules
        or value.get("module_count") != EXPECTED_STOCK_MODULE_COUNT
        or value.get("module_closure_sha256") != selected["closure_sha256"]
        or value.get("latch_boot_module")
        != _custom_descriptor(LATCH_PATH, LATCH_IDENTITY, early=True)
        or value.get("diagnostic_boot_module")
        != _custom_descriptor(DIAGNOSTIC_PATH, DIAGNOSTIC_IDENTITY, early=False)
    ):
        raise ClosureError("P3.18 effective module closure differs")
    legacy = copy.deepcopy(value)
    del legacy["latch_boot_module"]
    del legacy["diagnostic_boot_module"]
    for key in ("latch_boot_module", "diagnostic_boot_module"):
        witness = legacy["generic_rootfs"].pop(key)
        if witness.get("verified") is not True:
            raise ClosureError("P3.18 generic custom module proof differs")
    legacy["generic_rootfs"]["entry_count"] -= 2
    legacy["entry_count"] -= 2
    added = len(selected.get("added_modules", ()))
    if added <= 0:
        raise ClosureError("P3.18 stock delta is absent")
    del legacy["modules"][-added:]
    legacy["module_count"] = EXPECTED_STOCK_MODULE_COUNT - added
    legacy["module_closure_sha256"] = selected["parent_closure_sha256"]
    base.base.parent.validate_effective_rootfs(
        legacy,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=selected["parent_closure"],
    )
    return value


@contextmanager
def exact_init_authority(expected: bytes):  # noqa: ANN201
    names = (
        "REQUIRED_ABSOLUTE_PATH_STRINGS",
        "ALLOWED_ABSOLUTE_PATH_STRINGS",
        "INCIDENTAL_PATHS",
    )
    previous = {name: getattr(base, name) for name in names}
    previous_operational = base.base.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS
    values = {
        "REQUIRED_ABSOLUTE_PATH_STRINGS": REQUIRED_ABSOLUTE_PATH_STRINGS,
        "ALLOWED_ABSOLUTE_PATH_STRINGS": ALLOWED_ABSOLUTE_PATH_STRINGS,
        "INCIDENTAL_PATHS": INCIDENTAL_PATHS,
    }
    for name, value in values.items():
        setattr(base, name, value)
    base.base.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS = (
        P318_OPERATIONAL_ABSOLUTE_PATH_STRINGS
    )
    try:
        with base.exact_init_authority(expected):
            yield
    finally:
        base.base.P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS = previous_operational
        for name, value in previous.items():
            setattr(base, name, value)
