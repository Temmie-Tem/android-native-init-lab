#!/usr/bin/env python3
"""Expose P3.23 candidate arrival through the existing bounded ACM banner.

P3.22 reaches ``p319_stock_publish`` with an open raw gadget TTY and then
explicitly discards that descriptor.  Its first fallible witness-copy/encoder
step can therefore park before any host-visible byte exists.  P3.23 changes one
line at that publisher entry: attempt the already-qualified, run-bound 49-byte
banner once before the stock witness path.  The exact P3.22 Carrier path still
runs afterward as supplemental experiment evidence regardless of the banner
result.

The banner proves only arrival at the native PID-1 publisher after gadget bind
and the direct USB fence.  It does not claim that the Max77705 stock witness
encoded or that its scientific result succeeded.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


CONTRACT_ID = "s22plus-fyg8-p323-acm-primary-runtime-v1"
SCHEMA = CONTRACT_ID
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
RUNTIME_KEY = "p290_e3_runtime_include"

P322_RUNTIME_MARKER = (
    b"/* P3.19 stock-emitter envelope: no diagnostic binding/result ABI. */"
)
PUBLISHER = b"static __attribute__((noreturn)) void p319_stock_publish(int tty_fd) {"
BANNER_WRITER = b"static struct s22plus_p318_banner_result s22plus_p318_banner_attempt(int fd) {"
P322_BRIDGE = (
    b"static void p319_stock_bypass_to_pair(void) {\n"
    b"    if (g_checkpoint.terminal || g_checkpoint.generation > 105U) {\n"
    b"        p290_fail_next(P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION);\n"
    b"    }\n"
    b"    while (g_checkpoint.generation < 105U) {\n"
    b"        p290_progress_position((uint8_t)g_checkpoint.generation, 0U);\n"
    b"    }\n"
    b"}\n"
)

P322_ENTRY_PREIMAGE = (
    b"    (void)tty_fd;\n"
    b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
)

P323_ENTRY_POSTIMAGE = (
    b"    (void)s22plus_p318_banner_attempt(tty_fd);\n"
    b"    if (p319_witness_summary_state_v2_copy(&witness) != 0)\n"
)


class AcmPrimaryError(ValueError):
    """The P3.22 preimage or P3.23 one-function delta is not exact."""


def _bytes(value: bytes, label: str) -> None:
    if type(value) is not bytes:
        raise AcmPrimaryError(f"{label} must be bytes")


def validate_p322_runtime(value: bytes) -> dict[str, Any]:
    _bytes(value, "P322 runtime")
    required = (P322_RUNTIME_MARKER, PUBLISHER, BANNER_WRITER, P322_BRIDGE)
    for marker in required:
        if value.count(marker) != 1:
            raise AcmPrimaryError("P322 runtime closure differs")
    if value.count(P322_ENTRY_PREIMAGE) != 1 or P323_ENTRY_POSTIMAGE in value:
        raise AcmPrimaryError("P322 publisher entry preimage differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "acm_primary": False,
        "retained_fallback": True,
    }


def validate_p323_runtime(value: bytes) -> dict[str, Any]:
    _bytes(value, "P323 runtime")
    required = (P322_RUNTIME_MARKER, PUBLISHER, BANNER_WRITER, P322_BRIDGE)
    for marker in required:
        if value.count(marker) != 1:
            raise AcmPrimaryError("P323 runtime closure differs")
    if value.count(P323_ENTRY_POSTIMAGE) != 1 or P322_ENTRY_PREIMAGE in value:
        raise AcmPrimaryError("P323 publisher entry postimage differs")
    publisher_offset = value.index(PUBLISHER)
    banner_offset = value.index(P323_ENTRY_POSTIMAGE, publisher_offset)
    copy_offset = value.index(b"p319_witness_summary_state_v2_copy", banner_offset)
    encode_offset = value.index(b"s22plus_max77705_p319_stock_encode", copy_offset)
    bridge_offset = value.index(b"p319_stock_bypass_to_pair();", encode_offset)
    if not publisher_offset < banner_offset < copy_offset < encode_offset < bridge_offset:
        raise AcmPrimaryError("P323 ACM/stock publisher order differs")
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "target": TARGET,
        "acm_primary": True,
        "primary_claim": "native_pid1_publisher_arrival",
        "banner_bytes": 49,
        "banner_deadline_sec": 5,
        "banner_attempts": 1,
        "banner_before_stock_witness": True,
        "retained_path_always_continues": True,
        "retained_role": "supplemental_experiment_evidence",
        "scientific_result_claimed_by_banner": False,
    }


def validate_transform(before: bytes, after: bytes) -> dict[str, Any]:
    validate_p322_runtime(before)
    result = validate_p323_runtime(after)
    old = before.index(P322_ENTRY_PREIMAGE)
    new = after.index(P323_ENTRY_POSTIMAGE)
    if (
        before[:old] != after[:new]
        or before[old + len(P322_ENTRY_PREIMAGE) :]
        != after[new + len(P323_ENTRY_POSTIMAGE) :]
    ):
        raise AcmPrimaryError("P323 delta is wider than p319_stock_publish")
    return result | {
        "changed_anchor": "p319_stock_publish",
        "changed_only_in_anchor": True,
    }


def transform_runtime_include(value: bytes) -> bytes:
    validate_p322_runtime(value)
    result = value.replace(P322_ENTRY_PREIMAGE, P323_ENTRY_POSTIMAGE, 1)
    validate_transform(value, result)
    return result


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    if not isinstance(source, Mapping) or RUNTIME_KEY not in source:
        raise AcmPrimaryError("P323 source bundle lacks the runtime include")
    result = dict(source)
    result[RUNTIME_KEY] = transform_runtime_include(source[RUNTIME_KEY])
    changed = {key for key in result if result[key] != source[key]}
    if changed != {RUNTIME_KEY}:
        raise AcmPrimaryError("P323 source delta differs")
    return result


__all__ = [
    "AcmPrimaryError",
    "CONTRACT_ID",
    "P322_ENTRY_PREIMAGE",
    "P323_ENTRY_POSTIMAGE",
    "RUNTIME_KEY",
    "SCHEMA",
    "TARGET",
    "transform_artifacts",
    "transform_runtime_include",
    "validate_p322_runtime",
    "validate_p323_runtime",
    "validate_transform",
]
