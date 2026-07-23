#!/usr/bin/env python3
"""P2.45 E2 stock-rootfs adapter with byte-exact P2.42 preservation."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import s22plus_fyg8_p242_e2_stock_closure as legacy
import s22plus_fyg8_p244_e2_provider_sources as provider_sources
import s22plus_fyg8_p245_source_contract as source_contract


ClosureError = legacy.ClosureError
SCHEMA = legacy.SCHEMA
ORDER_MODEL = legacy.ORDER_MODEL
EXPECTED_ELF_ENTRYPOINTS = legacy.EXPECTED_ELF_ENTRYPOINTS
EXPECTED_GENERIC_ENTRY_COUNT = legacy.EXPECTED_GENERIC_ENTRY_COUNT
DEFAULT_VENDOR_RAMDISK = legacy.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = legacy.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = legacy.DEFAULT_LZ4
boot_verify = legacy.boot_verify
p241 = legacy.p241
receipt = legacy.receipt
closure_sha256 = legacy.closure_sha256

EXPECTED_MODULE_CLOSURE_SHA256 = (
    "9c0a6a944334eeee8fc617b9f99cd7a0a6afb3e06dbb6a9fc1813acd6af6b359"
)
LEGACY_PLAN_HEADER = {
    "size": 4105,
    "sha256": provider_sources.BASE_SHA256["plan"],
}
P245_PLAN_HEADER = {
    "size": 4605,
    "sha256": provider_sources.GENERATED_SHA256["plan"],
}


def select(source_contract_id: str | None):
    if source_contract_id is None:
        return legacy
    source_contract.require(source_contract_id, "E2")
    return sys.modules[__name__]


def _legacy_view(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["plan_header"] = dict(LEGACY_PLAN_HEADER)
    legacy.validate_module_closure(result)
    return result


def validate_module_closure(
    value: Any, *, allow_unpinned: bool = False
) -> dict[str, Any]:
    legacy.validate_module_closure(value, allow_unpinned=True)
    if value.get("plan_header") != P245_PLAN_HEADER:
        raise ClosureError("P2.45 E2 generated plan identity mismatch")
    digest = closure_sha256(value)
    if not allow_unpinned and digest != EXPECTED_MODULE_CLOSURE_SHA256:
        raise ClosureError(f"P2.45 E2 stock module closure digest mismatch: {digest}")
    _legacy_view(value)
    return value


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    generated = provider_sources.generate(root)["plan"]
    if plan_header is not None:
        supplied = p241.stable_read(
            plan_header, "P2.45 generated E2 plan header", 1024 * 1024
        )
        if supplied != generated:
            raise ClosureError("P2.45 plan differs from the P2.44 generator")
    base_header = root / provider_sources.BASE_PATHS["plan"]
    result = legacy.derive_module_closure(
        root,
        vendor_ramdisk,
        lz4,
        plan_header=base_header,
    )
    result = {**result, "plan_header": receipt(generated)}
    validate_module_closure(result)
    return result


def audit_candidate_generic_rootfs(
    boot: boot_verify.BootImageV4,
    entries: tuple[boot_verify.CpioEntry, ...],
    *,
    expected_init: dict[str, Any],
    expected_child: dict[str, Any],
    run_id: bytes,
    module_closure: dict[str, Any],
) -> dict[str, Any]:
    closure = validate_module_closure(module_closure)
    return legacy.audit_candidate_generic_rootfs(
        boot,
        entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=_legacy_view(closure),
    )


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
    result = legacy.rootfs_audit(
        candidate,
        vendor_boot,
        lz4_tool,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=_legacy_view(closure),
    )
    result = {
        **result,
        "module_closure_sha256": closure_sha256(closure),
    }
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
        raise ClosureError("effective E2 rootfs shape mismatch")
    if value.get("module_closure_sha256") != closure_sha256(closure):
        raise ClosureError("P2.45 effective E2 closure digest mismatch")
    legacy_value = copy.deepcopy(value)
    legacy_value["module_closure_sha256"] = legacy.closure_sha256(
        _legacy_view(closure)
    )
    legacy.validate_effective_rootfs(
        legacy_value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=_legacy_view(closure),
    )
    return value
