#!/usr/bin/env python3
"""Bind the unchanged 61-module/rootfs closure to the P3.12 overlay plan."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from s22plus_fyg8_p311_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p304_e2_stock_closure as module_parent
import s22plus_fyg8_p310_e2_stock_closure as p310_parent
import s22plus_fyg8_p311_e2_stock_closure as parent
import s22plus_fyg8_p312_overlay_contract as overlay


SCHEMA = "s22plus_fyg8_p312_stock_closure_h0_v1"
VERDICT = "PASS_P312_STOCK_61_MODULE_CLOSURE_HOST_ONLY"
ClosureError = parent.ClosureError


def select(source_contract_id: str | None):
    if source_contract_id != overlay.PARENT_SOURCE_CONTRACT_ID:
        raise ClosureError("P3.12 source contract differs")
    return __import__(__name__)


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    if plan_header is None:
        raise ClosureError("P3.12 exact materialized plan is missing")
    intent_path = plan_header.parent.parent / "overlay-intent.json"
    exact = overlay.verify_intent(root, intent_path)
    supplied = module_parent.p241.stable_read(
        plan_header, "P3.12 materialized plan", 1024 * 1024
    )
    expected = exact.get("generated_artifacts", {}).get("plan_header")
    if module_parent.receipt(supplied) != expected:
        raise ClosureError("P3.12 supplied plan identity differs")
    result = module_parent.derive_module_closure(
        root, vendor_ramdisk, lz4, plan_header=plan_header
    )
    if result.get("plan_header") != expected:
        raise ClosureError("P3.12 derived plan receipt differs")
    return result


validate_module_closure = module_parent.validate_module_closure
audit_candidate_generic_rootfs = module_parent.audit_candidate_generic_rootfs
rootfs_audit = module_parent.rootfs_audit
validate_effective_rootfs = module_parent.validate_effective_rootfs


def _scrub_exact_incidental_opcode_path(data: bytes) -> bytes:
    path = parent.INCIDENTAL_PATH
    offset = parent.INCIDENTAL_PATH_OFFSET
    window_offset = parent.INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
    window = parent.INCIDENTAL_INSTRUCTION_WINDOW
    if (
        data.count(path) != 1
        or data.find(path) != offset
        or offset != window_offset + 1
        or data[window_offset:window_offset + len(window)] != window
    ):
        raise ClosureError("P3.12 incidental opcode-path receipt mismatch")
    return data[:offset] + (b"\0" * len(path)) + data[offset + len(path):]


def _validate_p312_authority_strings(data: bytes) -> None:
    p300 = p310_parent.parent
    printable = p300.p286.p282.p280.isolated_p260._printable_strings(data)  # noqa: SLF001
    paths = p300.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
    incidental = paths - p310_parent.ALLOWED_ABSOLUTE_PATH_STRINGS
    if (
        p310_parent.REQUIRED_ABSOLUTE_PATH_STRINGS - paths
        or incidental != {parent.INCIDENTAL_PATH.decode("ascii")}
        or any(
            data.count(value.encode("ascii")) != 1
            for value in p310_parent.ADDITIONAL_ABSOLUTE_PATH_STRINGS
        )
    ):
        raise ClosureError("P3.12 candidate absolute-path authority mismatch")
    scrubbed = _scrub_exact_incidental_opcode_path(data)
    previous_required = p300.REQUIRED_ABSOLUTE_PATH_STRINGS
    previous_allowed = p300.ALLOWED_ABSOLUTE_PATH_STRINGS
    p300.REQUIRED_ABSOLUTE_PATH_STRINGS = p310_parent.REQUIRED_ABSOLUTE_PATH_STRINGS
    p300.ALLOWED_ABSOLUTE_PATH_STRINGS = p310_parent.ALLOWED_ABSOLUTE_PATH_STRINGS
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
            raise ClosureError("P3.12 effective init differs from source-bound userspace")
        _validate_p312_authority_strings(data)

    p300 = p310_parent.parent
    previous = p300.p286.p282._validate_p282_authority_strings  # noqa: SLF001
    p300.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001
