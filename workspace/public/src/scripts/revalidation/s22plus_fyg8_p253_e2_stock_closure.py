#!/usr/bin/env python3
"""P2.53 E2 stock closure with isolated P2.52/P2.54 entrypoints."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import s22plus_fyg8_p242_e2_stock_closure as legacy
import s22plus_fyg8_p245_e2_stock_closure as p245
import s22plus_fyg8_p245_source_contract as p245_contract
import s22plus_fyg8_p248_source_contract as p248_contract
import s22plus_fyg8_p252_source_contract as p252_contract


ClosureError = legacy.ClosureError
EXPECTED_ELF_ENTRYPOINTS = {"init": 0x4014F0, "child": 0x4000CC}
P254_CONTRACT_ID = "s22plus-fyg8-p254-e2-proof-bound-v1"
_ISOLATED_MODULE_NAME = "_s22plus_fyg8_p253_isolated_p242_stock_closure"


def _load_isolated_legacy() -> ModuleType:
    path = Path(legacy.__file__).resolve()
    spec = importlib.util.spec_from_file_location(_ISOLATED_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ClosureError("cannot create isolated P2.42 stock-closure module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_ISOLATED_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(_ISOLATED_MODULE_NAME, None)
        raise
    module.EXPECTED_ELF_ENTRYPOINTS = dict(EXPECTED_ELF_ENTRYPOINTS)
    return module


isolated_legacy = _load_isolated_legacy()


def select(source_contract_id: str | None):
    if source_contract_id is None:
        return legacy
    if source_contract_id in {
        p245_contract.CONTRACT_ID,
        p248_contract.CONTRACT_ID,
    }:
        return p245
    if source_contract_id == p252_contract.CONTRACT_ID:
        raise ClosureError(
            "P2.52 stock closure is not proof-bound; use the P2.54 contract"
        )
    if source_contract_id == P254_CONTRACT_ID:
        return sys.modules[__name__]
    raise ClosureError(
        f"unsupported E2 stock-closure source contract: {source_contract_id!r}"
    )


def _legacy_view(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["plan_header"] = dict(p245.LEGACY_PLAN_HEADER)
    isolated_legacy.validate_module_closure(result)
    return result


def validate_module_closure(
    value: Any, *, allow_unpinned: bool = False
) -> dict[str, Any]:
    return p245.validate_module_closure(
        value, allow_unpinned=allow_unpinned
    )


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    return p245.derive_module_closure(
        root,
        vendor_ramdisk,
        lz4,
        plan_header=plan_header,
    )


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
    return isolated_legacy.audit_candidate_generic_rootfs(
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
    result = isolated_legacy.rootfs_audit(
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
        "module_closure_sha256": p245.closure_sha256(closure),
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
    if value.get("module_closure_sha256") != p245.closure_sha256(closure):
        raise ClosureError("P2.53 effective E2 closure digest mismatch")
    legacy_value = copy.deepcopy(value)
    legacy_value["module_closure_sha256"] = (
        isolated_legacy.closure_sha256(_legacy_view(closure))
    )
    isolated_legacy.validate_effective_rootfs(
        legacy_value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=_legacy_view(closure),
    )
    return value
