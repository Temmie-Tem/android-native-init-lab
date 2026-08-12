#!/usr/bin/env python3
"""Bind the exact 64-module P3.16 stock substrate and init authority."""

from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_p304_e2_stock_closure as module_parent
import s22plus_fyg8_p315_e2_stock_closure as parent
import s22plus_fyg8_p316_generator as p316_generator
import s22plus_fyg8_p310_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p316_stock_closure_h0_v1"
VERDICT = "PASS_P316_STOCK_64_MODULE_SUBSTRATE_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_COUNT = 64
P315_PARENT_ARTIFACT_RESULTS = (
    Path("workspace/private/outputs/s22plus_fyg8_p315/candidate-a/artifact-result.json"),
    Path("workspace/private/outputs/s22plus_fyg8_p315/candidate-b/artifact-result.json"),
)
EXPECTED_P315_PARENT_ARTIFACT_RESULT = {
    "size": 589919,
    "sha256": "8bc2379bcaec094eea37659ef226ad2bbfa8fcbbcdd1f2dc23373e74419ffaa6",
}
ADDED_MODULES = (
    ("msm-geni-se.ko", "msm_geni_se"),
    ("gpi.ko", "gpi"),
    ("i2c-msm-geni.ko", "i2c_msm_geni"),
)
FROZEN_PARENT_INTENT = p316_generator.EXPECTED_P315_INTENT
ClosureError = parent.ClosureError
P310 = parent.parent.parent.p310_parent
INCIDENTAL_PATH = P310.INCIDENTAL_PATH
INCIDENTAL_PATHS = frozenset({INCIDENTAL_PATH})
PARENT_SOURCE_CONTRACT_ID = source_contract.CONTRACT_ID
# Successors temporarily replace this operation-time authority while reusing
# the frozen generic-rootfs implementation. Keep it unbound at module import
# so the evidence adapter cannot recurse through the P3.16 overlay graph.
overlay = None
P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS = frozenset(
    {
        "/proc/modules",
        "/sys/bus/platform/devices/",
        "/sys/module/s22plus_max77705_mux_diag/parameters/result",
    }
)
P316_RETIRED_REQUIRED_PATH_STRINGS = frozenset(
    {
        "/sys/devices/platform/soc/a600000.ssusb/power/runtime_status",
        "/sys/devices/platform/soc/a600000.ssusb/a600000.dwc3/power/runtime_status",
    }
)
P316_DYNAMIC_PATH_SUFFIX_STRINGS = frozenset(
    {"/driver", "/driver_override", "/of_node/compatible"}
)
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    {
        *(P310.REQUIRED_ABSOLUTE_PATH_STRINGS - P316_RETIRED_REQUIRED_PATH_STRINGS),
        *P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS,
        *P316_DYNAMIC_PATH_SUFFIX_STRINGS,
    }
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    {
        *P310.ALLOWED_ABSOLUTE_PATH_STRINGS,
        *P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS,
        *P316_DYNAMIC_PATH_SUFFIX_STRINGS,
    }
)


def _overlay_module():
    # Evidence imports this closure while the P3.16 adapter import graph is
    # still being initialized. Bind the immutable parent ID above and load the
    # full overlay only when an operation needs its intent verifier.
    if overlay is not None:
        return overlay
    import s22plus_fyg8_p316_overlay_contract as selected

    return selected


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def closure_sha256(value: dict[str, Any]) -> str:
    body = {key: item for key, item in value.items() if key != "closure_sha256"}
    return hashlib.sha256(_canonical(body)).hexdigest()


def select(source_contract_id: str | None):
    if source_contract_id != PARENT_SOURCE_CONTRACT_ID:
        raise ClosureError("P3.16 source contract differs")
    return __import__(__name__)


def _frozen_parent_closure(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payloads = [
        module_parent.p241.stable_read(
            root / relative, f"P3.16 frozen P3.15 candidate {index}", 2 * 1024 * 1024
        )
        for index, relative in enumerate(P315_PARENT_ARTIFACT_RESULTS)
    ]
    if payloads[0] != payloads[1] or module_parent.receipt(payloads[0]) != EXPECTED_P315_PARENT_ARTIFACT_RESULT:
        raise ClosureError("P3.16 frozen P3.15 candidate result differs")
    try:
        artifact = json.loads(payloads[0].decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClosureError("P3.16 frozen P3.15 candidate result is invalid") from exc
    candidate = artifact.get("candidate_contract", {})
    if (
        artifact.get("schema")
        != "s22plus_fyg8_p315_candidate_artifact_result_v1"
        or artifact.get("verdict")
        != "PASS_P315_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
        or candidate.get("contract_id") != parent.overlay.CONTRACT_ID
        or candidate.get("overlay_intent") != FROZEN_PARENT_INTENT
    ):
        raise ClosureError("P3.16 frozen P3.15 candidate authority differs")
    closure = parent.validate_module_closure(artifact.get("module_closure"))
    return closure, module_parent.receipt(payloads[0])


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    if plan_header is None:
        raise ClosureError("P3.16 exact materialized plan is missing")
    overlay = _overlay_module()
    intent_path = plan_header.parent.parent / "overlay-intent.json"
    exact = overlay.verify_intent(root, intent_path)
    supplied = module_parent.p241.stable_read(
        plan_header, "P3.16 materialized plan", 1024 * 1024
    )
    expected = exact.get("generated_artifacts", {}).get("plan_header")
    if module_parent.receipt(supplied) != expected:
        raise ClosureError("P3.16 supplied plan identity differs")
    names = module_parent.plan_spec.module_names(supplied)
    _metadata, p304_plan, _insertion = module_parent._expanded_plan(root)  # noqa: SLF001
    expanded = replace(
        p304_plan,
        modules=p304_plan.modules + tuple(name for name, _runtime in ADDED_MODULES),
    )
    if (
        names != expanded.modules
        or len(names) != EXPECTED_MODULE_COUNT
        or names[-len(ADDED_MODULES):]
        != tuple(name for name, _runtime in ADDED_MODULES)
        or len(set(names)) != EXPECTED_MODULE_COUNT
    ):
        raise ClosureError("P3.16 exact 64-module order differs")
    parent_closure, parent_artifact = _frozen_parent_closure(root)
    audit = module_parent.p241.audit_vendor_modules(
        root, vendor_ramdisk, lz4, expanded
    )
    if (
        audit.get("module_count") != EXPECTED_MODULE_COUNT
        or tuple(row.get("file") for row in audit.get("modules", ()))
        [-len(ADDED_MODULES):]
        != tuple(name for name, _runtime in ADDED_MODULES)
    ):
        raise ClosureError("P3.16 vendor 64-module audit differs")
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "files": [row["file"] for row in audit["modules"]],
        "runtime_names": [row["runtime_name"] for row in audit["modules"]],
        "count": audit["module_count"],
        "modules": audit["modules"],
        "added_modules": [
            {"file": name, "runtime_name": runtime}
            for name, runtime in ADDED_MODULES
        ],
        "plan_header": module_parent.receipt(supplied),
        "parent_closure": parent_closure,
        "parent_closure_sha256": parent_closure["closure_sha256"],
        "parent_candidate_artifact": parent_artifact,
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
        raise ClosureError("P3.16 stock module closure shape differs")
    rows = value.get("modules")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or not isinstance(rows, list)
        or len(rows) != EXPECTED_MODULE_COUNT
        or any(row.get("index") != index for index, row in enumerate(rows))
        or value.get("files") != [row.get("file") for row in rows]
        or value.get("runtime_names") != [row.get("runtime_name") for row in rows]
        or value.get("count") != EXPECTED_MODULE_COUNT
        or len(set(value["files"])) != EXPECTED_MODULE_COUNT
        or len(set(value["runtime_names"])) != EXPECTED_MODULE_COUNT
        or tuple(value["files"][-len(ADDED_MODULES):])
        != tuple(name for name, _runtime in ADDED_MODULES)
        or tuple(value["runtime_names"][-len(ADDED_MODULES):])
        != tuple(runtime for _name, runtime in ADDED_MODULES)
        or value.get("added_modules")
        != [{"file": name, "runtime_name": runtime} for name, runtime in ADDED_MODULES]
        or value.get("parent_closure_sha256")
        != value.get("parent_closure", {}).get("closure_sha256")
        or value.get("verified") is not True
        or value.get("closure_sha256") != closure_sha256(value)
    ):
        raise ClosureError("P3.16 64-module closure differs")
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
    selected = validate_module_closure(module_closure)
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
        layers.append(
            (
                f"vendor[{index}]/{fragment.name}",
                module_parent.boot_verify.parse_newc(
                    module_parent.boot_verify.decompress_lz4(lz4_tool, fragment.data)
                ),
            )
        )
    seen: dict[str, tuple[str, Any]] = {}
    for label, entries in layers:
        for entry in entries:
            if entry.name in seen:
                raise ClosureError(f"P3.16 effective rootfs duplicate: {entry.name}")
            if entry.file_type == "symlink" or entry.nlink != 1:
                raise ClosureError(f"P3.16 effective rootfs alias: {label}:{entry.name}")
            seen[entry.name] = (label, entry)
    module_rows = []
    for row in selected["modules"]:
        value = seen.get(f"lib/modules/{row['file']}")
        if value is None:
            raise ClosureError(f"P3.16 effective module missing: {row['file']}")
        label, entry = value
        if (
            not label.startswith("vendor[")
            or entry.file_type != "regular"
            or module_parent.receipt(entry.data)
            != {"size": row["size"], "sha256": row["sha256"]}
        ):
            raise ClosureError(f"P3.16 effective module differs: {row['file']}")
        module_rows.append(
            {"file": row["file"], "runtime": row["runtime_name"], "layer": label}
        )
    if any(
        b"rdinit=" in value
        for value in (
            boot.header["cmdline"].encode("ascii"),
            vendor.cmdline.encode("ascii"),
            vendor.bootconfig,
        )
    ):
        raise ClosureError("P3.16 effective rootfs has an rdinit override")
    result = {
        "composition_order": [label for label, _entries in layers],
        "entry_count": len(seen),
        "generic_rootfs": generic_rootfs,
        "no_duplicate_override_or_alias": True,
        "init": {**expected_init, "elf": generic_rootfs["init"]["elf"], "run_id_count": 1},
        "child": {**expected_child, "elf": generic_rootfs["child"]["elf"]},
        "modules": module_rows,
        "module_count": EXPECTED_MODULE_COUNT,
        "module_closure_sha256": selected["closure_sha256"],
        "rdinit_override_absent": True,
        "verified": True,
        "diagnostic_boot_module": {
        "file": "s22plus_max77705_mux_diag.ko",
        "layer": "generic",
        "size": surface.DIAG_MODULE_IDENTITY[0],
        "sha256": surface.DIAG_MODULE_IDENTITY[1],
        "early_plan_membership": False,
        "verified": True,
        },
    }
    return validate_effective_rootfs(
        result,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=selected,
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
    selected = validate_module_closure(module_closure)
    diagnostics = [
        entry
        for entry in entries
        if entry.name == "lib/modules/s22plus_max77705_mux_diag.ko"
    ]
    if (
        len(diagnostics) != 1
        or diagnostics[0].file_type != "regular"
        or module_parent.receipt(diagnostics[0].data)
        != {"size": surface.DIAG_MODULE_IDENTITY[0], "sha256": surface.DIAG_MODULE_IDENTITY[1]}
    ):
        raise ClosureError("P3.16 generic diagnostic module differs")
    legacy_entries = tuple(
        entry
        for entry in entries
        if entry.name != "lib/modules/s22plus_max77705_mux_diag.ko"
    )
    result = parent.audit_candidate_generic_rootfs(
        boot,
        legacy_entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=selected["parent_closure"],
    )
    result = copy.deepcopy(result)
    result["diagnostic_boot_module"] = {
        "file": "s22plus_max77705_mux_diag.ko",
        "size": surface.DIAG_MODULE_IDENTITY[0],
        "sha256": surface.DIAG_MODULE_IDENTITY[1],
        "early_plan_membership": False,
        "verified": True,
    }
    result["entry_count"] = len(entries)
    return result


def validate_effective_rootfs(
    value: Any,
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    module_closure: dict[str, Any],
):
    selected = validate_module_closure(module_closure)
    if not isinstance(value, dict):
        raise ClosureError("P3.16 effective rootfs shape differs")
    expected_modules = [
        {"file": row["file"], "runtime": row["runtime_name"], "layer": "vendor[0]/"}
        for row in selected["modules"]
    ]
    diagnostic = value.get("diagnostic_boot_module")
    if (
        value.get("modules") != expected_modules
        or value.get("module_count") != EXPECTED_MODULE_COUNT
        or value.get("module_closure_sha256") != selected["closure_sha256"]
        or diagnostic
        != {
            "file": "s22plus_max77705_mux_diag.ko",
            "layer": "generic",
            "size": surface.DIAG_MODULE_IDENTITY[0],
            "sha256": surface.DIAG_MODULE_IDENTITY[1],
            "early_plan_membership": False,
            "verified": True,
        }
    ):
        raise ClosureError("P3.16 effective module closure differs")
    legacy = copy.deepcopy(value)
    del legacy["diagnostic_boot_module"]
    diagnostic_generic = legacy["generic_rootfs"].pop("diagnostic_boot_module")
    if diagnostic_generic.get("verified") is not True:
        raise ClosureError("P3.16 generic diagnostic proof differs")
    legacy["generic_rootfs"]["entry_count"] -= 1
    legacy["entry_count"] -= 1
    del legacy["modules"][-len(ADDED_MODULES):]
    legacy["module_count"] = EXPECTED_MODULE_COUNT - len(ADDED_MODULES)
    legacy["module_closure_sha256"] = selected["parent_closure_sha256"]
    parent.validate_effective_rootfs(
        legacy,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=selected["parent_closure"],
    )
    return value


def _validate_p316_authority_strings(data: bytes) -> None:
    printable = P310.parent.p286.p282.p280.isolated_p260._printable_strings(data)  # noqa: SLF001
    paths = P310.parent.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
    incidental = paths - ALLOWED_ABSOLUTE_PATH_STRINGS
    if (
        REQUIRED_ABSOLUTE_PATH_STRINGS - paths
        or incidental != {path.decode("ascii") for path in INCIDENTAL_PATHS}
        or any(data.count(path) != 1 for path in INCIDENTAL_PATHS)
        or any(data.count(value.encode("ascii")) != 1 for value in P316_ADDITIONAL_ABSOLUTE_PATH_STRINGS)
    ):
        raise ClosureError("P3.16 candidate absolute-path authority mismatch")
    scrubbed = data
    for incidental_path in INCIDENTAL_PATHS:
        offset = scrubbed.find(incidental_path)
        scrubbed = (
            scrubbed[:offset]
            + b"\0" * len(incidental_path)
            + scrubbed[offset + len(incidental_path):]
        )
    p300 = P310.parent
    previous_required = p300.REQUIRED_ABSOLUTE_PATH_STRINGS
    previous_allowed = p300.ALLOWED_ABSOLUTE_PATH_STRINGS
    p300.REQUIRED_ABSOLUTE_PATH_STRINGS = REQUIRED_ABSOLUTE_PATH_STRINGS
    p300.ALLOWED_ABSOLUTE_PATH_STRINGS = ALLOWED_ABSOLUTE_PATH_STRINGS
    try:
        with p300._p300_authority_globals():  # noqa: SLF001
            p300._P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)  # noqa: SLF001
    finally:
        p300.REQUIRED_ABSOLUTE_PATH_STRINGS = previous_required
        p300.ALLOWED_ABSOLUTE_PATH_STRINGS = previous_allowed


@contextmanager
def exact_init_authority(expected: bytes) -> Iterator[None]:
    def validate(data: bytes) -> None:
        if data != expected:
            raise ClosureError("P3.16 effective init differs from source-bound userspace")
        _validate_p316_authority_strings(data)

    p300 = P310.parent
    previous = p300.p286.p282._validate_p282_authority_strings  # noqa: SLF001
    p300.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001
