#!/usr/bin/env python3
"""P2.60 proof-bound stock closure over the unchanged 60-module plan."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import s22plus_fyg8_p242_e2_stock_closure as legacy
import s22plus_fyg8_p253_e2_stock_closure as p253
import s22plus_fyg8_p257_e2_stock_closure as p257
import s22plus_fyg8_p260_source_contract as source_contract


ClosureError = p257.ClosureError
SCHEMA = "s22plus_fyg8_p260_stock_closure_h0_v1"
VERDICT = "PASS_P260_STOCK_CLOSURE_HOST_ONLY"
ORDER_MODEL = p257.ORDER_MODEL
EXPECTED_ELF_ENTRYPOINTS = {"init": 0x401A98, "child": 0x4000CC}
EXPECTED_GENERIC_ENTRY_COUNT = p257.EXPECTED_GENERIC_ENTRY_COUNT
DEFAULT_VENDOR_RAMDISK = p257.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = p257.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = p257.DEFAULT_LZ4
EXPECTED_MODULE_COUNT = p257.EXPECTED_MODULE_COUNT
EXPECTED_PLAN_TSV_SHA256 = p257.EXPECTED_PLAN_TSV_SHA256
EXPECTED_MODULE_CLOSURE_SHA256 = p257.EXPECTED_MODULE_CLOSURE_SHA256
EXPECTED_DISPCC = p257.EXPECTED_DISPCC
boot_verify = p257.boot_verify
receipt = p257.receipt
closure_sha256 = p257.closure_sha256
_ISOLATED_MODULE_NAME = "_s22plus_fyg8_p260_isolated_p242_stock_closure"


def _load_isolated_legacy() -> ModuleType:
    path = Path(legacy.__file__).resolve()
    spec = importlib.util.spec_from_file_location(_ISOLATED_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise ClosureError("cannot create isolated P2.60 stock-closure module")
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


def _call_with_p260_entrypoints(function, *args, **kwargs):
    previous = p253.isolated_legacy
    p253.isolated_legacy = isolated_legacy
    try:
        return function(*args, **kwargs)
    finally:
        p253.isolated_legacy = previous


def select(source_contract_id: str | None):
    source_contract.require(source_contract_id, "E2")
    return sys.modules[__name__]


def validate_module_closure(value, *, allow_unpinned: bool = False):
    return p257.validate_module_closure(
        value, allow_unpinned=allow_unpinned
    )


def derive_module_closure(root, vendor_ramdisk, lz4, plan_header=None):
    result = p257.derive_module_closure(
        root,
        vendor_ramdisk,
        lz4,
        plan_header=plan_header,
    )
    return validate_module_closure(result)


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    return _call_with_p260_entrypoints(
        p257.audit_candidate_generic_rootfs,
        boot,
        entries,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=module_closure,
    )


def rootfs_audit(
    candidate,
    vendor_boot,
    lz4_tool,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    return _call_with_p260_entrypoints(
        p257.rootfs_audit,
        candidate,
        vendor_boot,
        lz4_tool,
        expected_init=expected_init,
        expected_child=expected_child,
        run_id=run_id,
        module_closure=module_closure,
    )


def validate_effective_rootfs(
    value,
    *,
    expected_init,
    expected_child,
    module_closure,
):
    return _call_with_p260_entrypoints(
        p257.validate_effective_rootfs,
        value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=module_closure,
    )


def build_result(root=None):
    result = dict(p257.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
