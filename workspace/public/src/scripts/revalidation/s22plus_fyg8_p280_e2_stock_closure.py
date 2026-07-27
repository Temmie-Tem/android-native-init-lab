#!/usr/bin/env python3
"""P2.80 stock closure over the unchanged P2.60 module plan."""

from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import s22plus_fyg8_p260_e2_stock_closure as p260
import s22plus_fyg8_p280_contract_spec as spec
import s22plus_fyg8_p280_source_contract as source_contract


ClosureError = p260.ClosureError
SCHEMA = "s22plus_fyg8_p280_stock_closure_h0_v1"
VERDICT = "PASS_P280_STOCK_CLOSURE_HOST_ONLY"
ORDER_MODEL = p260.ORDER_MODEL
EXPECTED_GENERIC_ENTRY_COUNT = p260.EXPECTED_GENERIC_ENTRY_COUNT
DEFAULT_VENDOR_RAMDISK = p260.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = p260.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = p260.DEFAULT_LZ4
EXPECTED_MODULE_COUNT = p260.EXPECTED_MODULE_COUNT
EXPECTED_PLAN_TSV_SHA256 = p260.EXPECTED_PLAN_TSV_SHA256
EXPECTED_MODULE_CLOSURE_SHA256 = p260.EXPECTED_MODULE_CLOSURE_SHA256
EXPECTED_DISPCC = p260.EXPECTED_DISPCC
boot_verify = p260.boot_verify
receipt = p260.receipt
closure_sha256 = p260.closure_sha256

_ISOLATED_MODULE_NAME = "_s22plus_fyg8_p280_isolated_p260_stock_closure"
_P280_PATH_FRAGMENTS = frozenset(("/enable", "/filter"))
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *p260.source_contract.spec.REQUIRED_ABSOLUTE_PATH_STRINGS,
        *spec.TRACEFS_ABSOLUTE_PATHS,
    )
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *p260.source_contract.spec.ALLOWED_ABSOLUTE_PATH_STRINGS,
        *REQUIRED_ABSOLUTE_PATH_STRINGS,
        *_P280_PATH_FRAGMENTS,
    )
)


def _load_isolated_p260() -> ModuleType:
    path = Path(p260.__file__).resolve()
    module_spec = importlib.util.spec_from_file_location(
        _ISOLATED_MODULE_NAME, path
    )
    if module_spec is None or module_spec.loader is None:
        raise ClosureError("cannot create isolated P2.80 stock-closure module")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[_ISOLATED_MODULE_NAME] = module
    try:
        module_spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(_ISOLATED_MODULE_NAME, None)
        raise
    return module


isolated_p260 = _load_isolated_p260()
_P260_AUDIT = isolated_p260._p260_audit_candidate_generic_rootfs


def _validate_p280_authority_strings(data: bytes) -> None:
    strings = isolated_p260._printable_strings(data)
    absolute_paths = frozenset(
        value for value in strings if value.startswith("/")
    )
    if not absolute_paths.issubset(ALLOWED_ABSOLUTE_PATH_STRINGS):
        raise ClosureError("P2.80 candidate absolute-path authority mismatch")
    if not REQUIRED_ABSOLUTE_PATH_STRINGS.issubset(absolute_paths):
        raise ClosureError("P2.80 candidate required absolute path is missing")
    if not isolated_p260.source_contract.spec.E3_REQUIRED_CONTROL_STRINGS.issubset(
        strings
    ):
        raise ClosureError("P2.80 candidate E3 control strings are incomplete")

    historical = isolated_p260.source_contract.spec
    categorized = (
        (
            frozenset(
                value
                for value in strings
                if value[:2].lower() == "0x"
                and len(value) > 2
                and all(
                    character in "0123456789abcdefABCDEF"
                    for character in value[2:]
                )
            ),
            historical.E3_HEX_CONTROL_STRINGS,
            "hex control",
        ),
        (
            frozenset(value for value in strings if "functions/" in value),
            historical.E3_FUNCTION_TARGET_STRINGS,
            "function target",
        ),
        (
            frozenset(value for value in strings if value.endswith("-speed")),
            historical.E3_SPEED_CONTROL_STRINGS,
            "speed control",
        ),
        (
            frozenset(
                value
                for value in strings
                if value in {"device", "host", "none", "otg", "peripheral"}
            ),
            historical.E3_ROLE_CONTROL_STRINGS,
            "role control",
        ),
        (
            frozenset(
                value
                for value in strings
                if "/" not in value and value.endswith(".dwc3")
            ),
            historical.E3_UDC_NAME_STRINGS,
            "UDC name",
        ),
    )
    for actual, expected, label in categorized:
        if actual != expected:
            raise ClosureError(f"P2.80 candidate {label} authority mismatch")


isolated_p260._validate_p260_authority_strings = (
    _validate_p280_authority_strings
)


def _entrypoints(entries) -> dict[str, int]:
    by_name = {entry.name: entry for entry in entries}
    if set(("init", "s22-e1-child")) - set(by_name):
        raise ClosureError("P2.80 candidate executable inventory is incomplete")
    try:
        return {
            "init": isolated_p260.isolated_legacy.e1_static.inspect_static_elf(
                by_name["init"].data, "P2.80 /init"
            )["entrypoint"],
            "child": isolated_p260.isolated_legacy.e1_static.inspect_static_elf(
                by_name["s22-e1-child"].data, "P2.80 child"
            )["entrypoint"],
        }
    except isolated_p260.isolated_legacy.e1_static.CheckError as exc:
        raise ClosureError(
            "P2.80 candidate executable ELF contract mismatch"
        ) from exc


@contextmanager
def _expected_entrypoints(values: dict[str, int]) -> Iterator[None]:
    previous_adapter = isolated_p260.EXPECTED_ELF_ENTRYPOINTS
    previous_legacy = isolated_p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS
    isolated_p260.EXPECTED_ELF_ENTRYPOINTS = dict(values)
    isolated_p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS = dict(values)
    try:
        yield
    finally:
        isolated_p260.EXPECTED_ELF_ENTRYPOINTS = previous_adapter
        isolated_p260.isolated_legacy.EXPECTED_ELF_ENTRYPOINTS = previous_legacy


def _p280_audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    with _expected_entrypoints(_entrypoints(entries)):
        return _P260_AUDIT(
            boot,
            entries,
            expected_init=expected_init,
            expected_child=expected_child,
            run_id=run_id,
            module_closure=module_closure,
        )


@contextmanager
def _p280_audit_override() -> Iterator[None]:
    previous = isolated_p260._p260_audit_candidate_generic_rootfs
    isolated_p260._p260_audit_candidate_generic_rootfs = (
        _p280_audit_candidate_generic_rootfs
    )
    try:
        yield
    finally:
        isolated_p260._p260_audit_candidate_generic_rootfs = previous


def select(source_contract_id: str | None):
    try:
        source_contract.require(source_contract_id, "E2")
    except source_contract.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc
    return sys.modules[__name__]


def validate_module_closure(value, *, allow_unpinned: bool = False):
    return isolated_p260.validate_module_closure(
        value, allow_unpinned=allow_unpinned
    )


def derive_module_closure(root, vendor_ramdisk, lz4, plan_header=None):
    return isolated_p260.derive_module_closure(
        root,
        vendor_ramdisk,
        lz4,
        plan_header=plan_header,
    )


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    return _p280_audit_candidate_generic_rootfs(
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
    with _p280_audit_override():
        return isolated_p260.rootfs_audit(
            candidate,
            vendor_boot,
            lz4_tool,
            expected_init=expected_init,
            expected_child=expected_child,
            run_id=run_id,
            module_closure=module_closure,
        )


def validate_effective_rootfs(
    value: Any,
    *,
    expected_init,
    expected_child,
    module_closure,
):
    try:
        entrypoints = {
            "init": value["init"]["elf"]["entrypoint"],
            "child": value["child"]["elf"]["entrypoint"],
        }
    except (KeyError, TypeError) as exc:
        raise ClosureError("P2.80 effective rootfs entrypoint is missing") from exc
    if any(isinstance(item, bool) or not isinstance(item, int) for item in entrypoints.values()):
        raise ClosureError("P2.80 effective rootfs entrypoint is malformed")
    with _expected_entrypoints(entrypoints):
        return isolated_p260.validate_effective_rootfs(
            value,
            expected_init=expected_init,
            expected_child=expected_child,
            module_closure=module_closure,
        )


def build_result(root=None):
    result = dict(isolated_p260.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
