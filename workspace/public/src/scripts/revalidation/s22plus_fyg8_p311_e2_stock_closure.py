#!/usr/bin/env python3
"""Bind the unchanged 61-module/rootfs closure to the P3.11 overlay plan."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from pathlib import Path
from typing import Any, Iterator

from s22plus_fyg8_p310_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p304_e2_stock_closure as module_parent
import s22plus_fyg8_p310_e2_stock_closure as parent
import s22plus_fyg8_p311_overlay_contract as overlay


SCHEMA = "s22plus_fyg8_p311_stock_closure_h0_v1"
VERDICT = "PASS_P311_STOCK_61_MODULE_CLOSURE_HOST_ONLY"
ClosureError = parent.ClosureError
INCIDENTAL_INIT_SIZE = 66416
INCIDENTAL_PATH = b'/E9"'
INCIDENTAL_PATH_OFFSET = 0x4795
INCIDENTAL_TEXT_OFFSET = 0x120
INCIDENTAL_TEXT_END = 0x952C
INCIDENTAL_TEXT_SHA256 = (
    "2356d13c293ecaf1079b38da768bcc81d7f3812d3e0e74345f96ffa37a0885b3"
)
INCIDENTAL_INSTRUCTION_WINDOW_OFFSET = 0x4794
INCIDENTAL_INSTRUCTION_WINDOW = bytes.fromhex("e02f4539220000b0")


def select(source_contract_id: str | None):
    if source_contract_id != overlay.PARENT_SOURCE_CONTRACT_ID:
        raise ClosureError("P3.11 source contract differs")
    return __import__(__name__)


def derive_module_closure(
    root: Path,
    vendor_ramdisk: Path,
    lz4: Path,
    plan_header: Path | None = None,
) -> dict[str, Any]:
    if plan_header is None:
        raise ClosureError("P3.11 exact materialized plan is missing")
    intent_path = plan_header.parent.parent / "overlay-intent.json"
    exact = overlay.verify_intent(root, intent_path)
    supplied = module_parent.p241.stable_read(
        plan_header, "P3.11 materialized plan", 1024 * 1024
    )
    expected = exact.get("generated_artifacts", {}).get("plan_header")
    if module_parent.receipt(supplied) != expected:
        raise ClosureError("P3.11 supplied plan identity differs")
    result = module_parent.derive_module_closure(
        root, vendor_ramdisk, lz4, plan_header=plan_header
    )
    if result.get("plan_header") != expected:
        raise ClosureError("P3.11 derived plan receipt differs")
    return result


validate_module_closure = module_parent.validate_module_closure
audit_candidate_generic_rootfs = module_parent.audit_candidate_generic_rootfs
rootfs_audit = module_parent.rootfs_audit
validate_effective_rootfs = module_parent.validate_effective_rootfs


def _scrub_exact_incidental_opcode_path(data: bytes) -> bytes:
    text = data[INCIDENTAL_TEXT_OFFSET:INCIDENTAL_TEXT_END]
    if (
        len(data) != INCIDENTAL_INIT_SIZE
        or hashlib.sha256(text).hexdigest() != INCIDENTAL_TEXT_SHA256
        or data.count(INCIDENTAL_PATH) != 1
        or data.find(INCIDENTAL_PATH) != INCIDENTAL_PATH_OFFSET
        or INCIDENTAL_PATH_OFFSET != INCIDENTAL_INSTRUCTION_WINDOW_OFFSET + 1
        or data[
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET:
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET + len(INCIDENTAL_INSTRUCTION_WINDOW)
        ]
        != INCIDENTAL_INSTRUCTION_WINDOW
    ):
        raise ClosureError("P3.11 incidental opcode-path receipt mismatch")
    return (
        data[:INCIDENTAL_PATH_OFFSET]
        + (b"\0" * len(INCIDENTAL_PATH))
        + data[INCIDENTAL_PATH_OFFSET + len(INCIDENTAL_PATH):]
    )


def _validate_p311_authority_strings(data: bytes) -> None:
    p300 = parent.parent
    printable = p300.p286.p282.p280.isolated_p260._printable_strings(data)  # noqa: SLF001
    paths = p300.p286.p282._absolute_path_candidates(printable)  # noqa: SLF001
    incidental = paths - parent.ALLOWED_ABSOLUTE_PATH_STRINGS
    if (
        parent.REQUIRED_ABSOLUTE_PATH_STRINGS - paths
        or incidental != {INCIDENTAL_PATH.decode("ascii")}
        or any(
            data.count(value.encode("ascii")) != 1
            for value in parent.ADDITIONAL_ABSOLUTE_PATH_STRINGS
        )
    ):
        raise ClosureError("P3.11 candidate absolute-path authority mismatch")
    scrubbed = _scrub_exact_incidental_opcode_path(data)
    previous_required = p300.REQUIRED_ABSOLUTE_PATH_STRINGS
    previous_allowed = p300.ALLOWED_ABSOLUTE_PATH_STRINGS
    p300.REQUIRED_ABSOLUTE_PATH_STRINGS = parent.REQUIRED_ABSOLUTE_PATH_STRINGS
    p300.ALLOWED_ABSOLUTE_PATH_STRINGS = parent.ALLOWED_ABSOLUTE_PATH_STRINGS
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
            raise ClosureError("P3.11 effective init differs from source-bound userspace")
        _validate_p311_authority_strings(data)

    p300 = parent.parent
    previous = p300.p286.p282._validate_p282_authority_strings  # noqa: SLF001
    p300.p286.p282._validate_p282_authority_strings = validate  # noqa: SLF001
    try:
        yield
    finally:
        p300.p286.p282._validate_p282_authority_strings = previous  # noqa: SLF001
