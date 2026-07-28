#!/usr/bin/env python3
"""P2.82 stock closure over the unchanged P2.60 module plan."""

from __future__ import annotations

from contextlib import contextmanager
import sys
from typing import Any, Iterator

import s22plus_fyg8_p280_e2_stock_closure as p280
import s22plus_fyg8_p282_contract_spec as spec
import s22plus_fyg8_p282_source_contract as source_contract


ClosureError = p280.ClosureError
SCHEMA = "s22plus_fyg8_p282_stock_closure_h0_v1"
VERDICT = "PASS_P282_STOCK_CLOSURE_HOST_ONLY"
ORDER_MODEL = p280.ORDER_MODEL
EXPECTED_GENERIC_ENTRY_COUNT = p280.EXPECTED_GENERIC_ENTRY_COUNT
DEFAULT_VENDOR_RAMDISK = p280.DEFAULT_VENDOR_RAMDISK
DEFAULT_VENDOR_BOOT = p280.DEFAULT_VENDOR_BOOT
DEFAULT_LZ4 = p280.DEFAULT_LZ4
EXPECTED_MODULE_COUNT = p280.EXPECTED_MODULE_COUNT
EXPECTED_PLAN_TSV_SHA256 = p280.EXPECTED_PLAN_TSV_SHA256
EXPECTED_MODULE_CLOSURE_SHA256 = p280.EXPECTED_MODULE_CLOSURE_SHA256
EXPECTED_DISPCC = p280.EXPECTED_DISPCC
boot_verify = p280.boot_verify
receipt = p280.receipt
closure_sha256 = p280.closure_sha256

_HISTORICAL_SPEC = p280.isolated_p260.source_contract.spec
_P282_PATH_FRAGMENTS = frozenset(("/enable", "/filter"))
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *_HISTORICAL_SPEC.REQUIRED_ABSOLUTE_PATH_STRINGS,
        *spec.TRACEFS_ABSOLUTE_PATHS,
        spec.CHILD_RUNTIME_STATUS_PATH,
    )
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *_HISTORICAL_SPEC.ALLOWED_ABSOLUTE_PATH_STRINGS,
        *REQUIRED_ABSOLUTE_PATH_STRINGS,
        *_P282_PATH_FRAGMENTS,
    )
)


def _runtime_operation_contract() -> dict[str, tuple[str, int]]:
    result: dict[str, tuple[str, int]] = {}
    for name, token, count in spec.RUNTIME_OPERATION_TOKENS:
        if name in result:
            raise ClosureError("P2.82 runtime operation name is duplicated")
        result[name] = (token, count)
    expected = {
        "parent-mode-none-write": ("P282_ROLE_NONE_WRITE", 1),
        "parent-mode-peripheral-write": (
            "P282_ROLE_PERIPHERAL_WRITE",
            1,
        ),
        "parent-mode-host-write": ('"host\\n"', 0),
    }
    if {name: result.get(name) for name in expected} != expected:
        raise ClosureError("P2.82 parent role operation contract mismatch")
    if (
        spec.RUNTIME_AUTHORITY.get("userspace_parent_role_write_count") != 2
        or spec.RUNTIME_AUTHORITY.get("host_role_authority") is not False
    ):
        raise ClosureError("P2.82 parent role authority mismatch")
    return result


def _absolute_path_candidates(strings: frozenset[str]) -> frozenset[str]:
    # Static ELF bytes can form incidental one-to-three-byte slash strings.
    # Every owned runtime path is at least four bytes; short fragments are not
    # path authority and must not become an expanding artifact allowlist.
    return frozenset(
        value
        for value in strings
        if value.startswith("/") and len(value) >= 4
    )


def _validate_speed_strings(strings: frozenset[str]) -> None:
    actual = frozenset(value for value in strings if value.endswith("-speed"))
    required = _HISTORICAL_SPEC.E3_SPEED_CONTROL_STRINGS
    allowed = frozenset(
        value for value in spec.CANONICAL_SPEEDS if value.endswith("-speed")
    )
    if not required.issubset(actual) or not actual.issubset(allowed):
        raise ClosureError("P2.82 candidate speed control authority mismatch")


def _validate_p282_authority_strings(data: bytes) -> None:
    _runtime_operation_contract()
    strings = p280.isolated_p260._printable_strings(data)
    absolute_paths = _absolute_path_candidates(strings)
    if not absolute_paths.issubset(ALLOWED_ABSOLUTE_PATH_STRINGS):
        raise ClosureError("P2.82 candidate absolute-path authority mismatch")
    if not REQUIRED_ABSOLUTE_PATH_STRINGS.issubset(absolute_paths):
        raise ClosureError("P2.82 candidate required absolute path is missing")
    if not _HISTORICAL_SPEC.E3_REQUIRED_CONTROL_STRINGS.issubset(strings):
        raise ClosureError("P2.82 candidate E3 control strings are incomplete")

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
            _HISTORICAL_SPEC.E3_HEX_CONTROL_STRINGS,
            "hex control",
        ),
        (
            frozenset(value for value in strings if "functions/" in value),
            _HISTORICAL_SPEC.E3_FUNCTION_TARGET_STRINGS,
            "function target",
        ),
        (
            frozenset(
                value
                for value in strings
                if value in {"device", "host", "none", "otg", "peripheral"}
            ),
            _HISTORICAL_SPEC.E3_ROLE_CONTROL_STRINGS,
            "role control",
        ),
        (
            frozenset(
                value
                for value in strings
                if "/" not in value and value.endswith(".dwc3")
            ),
            _HISTORICAL_SPEC.E3_UDC_NAME_STRINGS,
            "UDC name",
        ),
    )
    for actual, expected, label in categorized:
        if actual != expected:
            raise ClosureError(f"P2.82 candidate {label} authority mismatch")
    _validate_speed_strings(strings)

    # Reading the "host" role is permitted. Writing it is not.
    if b"host\n" in data:
        raise ClosureError("P2.82 candidate contains forbidden host role write")


@contextmanager
def _p282_authority_override() -> Iterator[None]:
    previous = p280.isolated_p260._validate_p260_authority_strings
    p280.isolated_p260._validate_p260_authority_strings = (
        _validate_p282_authority_strings
    )
    try:
        yield
    finally:
        p280.isolated_p260._validate_p260_authority_strings = previous


def select(source_contract_id: str | None):
    try:
        source_contract.require(source_contract_id, "E2")
    except source_contract.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc
    return sys.modules[__name__]


def validate_module_closure(value, *, allow_unpinned: bool = False):
    return p280.validate_module_closure(
        value, allow_unpinned=allow_unpinned
    )


def derive_module_closure(root, vendor_ramdisk, lz4, plan_header=None):
    return p280.derive_module_closure(
        root,
        vendor_ramdisk,
        lz4,
        plan_header=plan_header,
    )


def _entrypoints(entries) -> dict[str, int]:
    return p280._entrypoints(entries)


def audit_candidate_generic_rootfs(
    boot,
    entries,
    *,
    expected_init,
    expected_child,
    run_id,
    module_closure,
):
    with _p282_authority_override():
        return p280.audit_candidate_generic_rootfs(
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
    with _p282_authority_override():
        return p280.rootfs_audit(
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
    return p280.validate_effective_rootfs(
        value,
        expected_init=expected_init,
        expected_child=expected_child,
        module_closure=module_closure,
    )


def build_result(root=None):
    result = dict(p280.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
