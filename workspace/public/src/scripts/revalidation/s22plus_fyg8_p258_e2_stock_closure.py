#!/usr/bin/env python3
"""P2.58A proof-bound stock closure over the unchanged 60-module plan."""

from __future__ import annotations

import sys

import s22plus_fyg8_p257_e2_stock_closure as p257
import s22plus_fyg8_p258_source_contract as source_contract


ClosureError = p257.ClosureError
SCHEMA = p257.SCHEMA
ORDER_MODEL = p257.ORDER_MODEL
EXPECTED_ELF_ENTRYPOINTS = p257.EXPECTED_ELF_ENTRYPOINTS
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
    return p257.audit_candidate_generic_rootfs(
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
    return p257.rootfs_audit(
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
    return p257.validate_effective_rootfs(
        value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=module_closure,
    )


def build_result(root=None):
    return p257.build_result(root)


if __name__ == "__main__":
    raise SystemExit(p257.main())
