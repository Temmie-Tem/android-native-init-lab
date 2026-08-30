#!/usr/bin/env python3
"""Repair the P3.19 stock publisher checkpoint bridge, host-only.

P3.19's generated stock publisher treats generation 105 as an already
completed precondition.  That is inconsistent with the reviewed P3.13
checkpoint shape: an uncommitted checkpoint below 105 must advance through
the missing positions, while a terminal or overrun checkpoint must fail
closed.  P3.22 changes only the exact ``p319_stock_bypass_to_pair`` function
in a P3.19 stock runtime include.  It does not build an artifact, contact a
device, invoke Odin, or widen the diagnostic/provider closure.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


P322_CONTRACT_ID = "s22plus-fyg8-p322-stock-runtime-repair-v1"
P322_SCHEMA = P322_CONTRACT_ID
P322_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
P322_RUNTIME_KEY = "p290_e3_runtime_include"

P319_STOCK_RUNTIME_MARKER = (
    b"/* P3.19 stock-emitter envelope: no diagnostic binding/result ABI. */"
)
P319_STOCK_PUBLISHER_DEFINITION = (
    b"static __attribute__((noreturn)) void "
    b"p319_stock_publish(int tty_fd) {"
)
P319_STOCK_PUBLISHER_CALL = b"p319_stock_bypass_to_pair();"
P319_STOCK_ENCODER_SYMBOL = b"s22plus_max77705_p319_stock_encode("

# This is the exact generated P3.19 preimage.  Keep the function name in the
# preimage: a generic condition-only replacement could silently repair an
# unrelated checkpoint bridge elsewhere in the runtime.
P319_BYPASS_PREIMAGE = (
    b"static void p319_stock_bypass_to_pair(void) {\n"
    b"    if (g_checkpoint.terminal || g_checkpoint.generation != 105U)\n"
    b"        p290_fail_next(P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION);\n"
    b"}\n"
)

# P313's reviewed shape, retaining the P319 stock symbol and detail domain.
P322_BYPASS_POSTIMAGE = (
    b"static void p319_stock_bypass_to_pair(void) {\n"
    b"    if (g_checkpoint.terminal || g_checkpoint.generation > 105U) {\n"
    b"        p290_fail_next(P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION);\n"
    b"    }\n"
    b"    while (g_checkpoint.generation < 105U) {\n"
    b"        p290_progress_position((uint8_t)g_checkpoint.generation, 0U);\n"
    b"    }\n"
    b"}\n"
)

# These markers fence the closure that this repair is expressly forbidden to
# widen.  The transformed source must have the same count for every marker as
# its P319 input.  The exact prefix/suffix comparison below is the stronger
# byte-level check; these counts make the intended hazard legible to callers
# and tests.
P322_DIAGNOSTIC_PROVIDER_MARKERS = (
    b"p316_",
    b"p317_",
    b"P316_",
    b"P317_",
    b"diagnostic",
    b"DIAG",
    b"provider",
    b"PROVIDER",
)


class RuntimeRepairError(ValueError):
    """The P319 preimage or P322 postimage is not exact."""


def _require_bytes(data: bytes, label: str) -> None:
    if type(data) is not bytes:
        raise RuntimeRepairError(f"{label} must be bytes")


def _require_p319_shell(data: bytes) -> None:
    """Require the small set of identity markers for a generated P3.19 file."""
    _require_bytes(data, "P322 runtime")
    required_once = (
        (P319_STOCK_RUNTIME_MARKER, "stock-emitter marker"),
        (P319_STOCK_PUBLISHER_DEFINITION, "stock publisher definition"),
        (P319_STOCK_PUBLISHER_CALL, "stock publisher bypass call"),
    )
    for marker, label in required_once:
        if data.count(marker) != 1:
            raise RuntimeRepairError(
                f"P322 P319 {label} count {data.count(marker)}, expected 1"
            )
    # The symbol is present once in its definition and once at the call site;
    # the exact old function body below fences the definition itself.
    if data.count(P319_STOCK_ENCODER_SYMBOL) < 1:
        raise RuntimeRepairError("P322 P319 stock encoder symbol is absent")


def validate_p319_preimage(data: bytes) -> dict[str, Any]:
    """Validate and describe one untouched generated P3.19 runtime include."""
    _require_p319_shell(data)
    old_count = data.count(P319_BYPASS_PREIMAGE)
    if old_count != 1:
        raise RuntimeRepairError(
            f"P322 P319 bypass preimage count {old_count}, expected 1"
        )
    if data.count(P322_BYPASS_POSTIMAGE):
        raise RuntimeRepairError("P322 postimage is already present in preimage")
    return {
        "contract_id": P322_CONTRACT_ID,
        "schema": P322_SCHEMA,
        "target": P322_TARGET,
        "source_kind": "P3.19 generated stock runtime include",
        "bypass_preimage_count": old_count,
        "bypass_postimage_count": 0,
        "diagnostic_provider_counts": {
            marker.decode("ascii"): data.count(marker)
            for marker in P322_DIAGNOSTIC_PROVIDER_MARKERS
        },
    }


def _validate_p322_postimage(data: bytes) -> dict[str, Any]:
    _require_p319_shell(data)
    post_count = data.count(P322_BYPASS_POSTIMAGE)
    if post_count != 1:
        raise RuntimeRepairError(
            f"P322 bypass postimage count {post_count}, expected 1"
        )
    if data.count(P319_BYPASS_PREIMAGE):
        raise RuntimeRepairError("P322 old P319 bypass preimage remains")
    if b"g_checkpoint.terminal || g_checkpoint.generation != 105U" in data:
        # The complete preimage check above catches the generated helper, but
        # this explicit condition guard prevents a malformed postimage from
        # retaining the rejected equality predicate in the same source.
        raise RuntimeRepairError("P322 old generation-equality predicate remains")
    return {
        "contract_id": P322_CONTRACT_ID,
        "schema": P322_SCHEMA,
        "target": P322_TARGET,
        "source_kind": "P322 transformed P3.19 stock runtime include",
        "bypass_preimage_count": 0,
        "bypass_postimage_count": post_count,
        "diagnostic_provider_counts": {
            marker.decode("ascii"): data.count(marker)
            for marker in P322_DIAGNOSTIC_PROVIDER_MARKERS
        },
    }


def _validate_exact_delta(before: bytes, after: bytes) -> None:
    """Prove that one contiguous old function became one new function."""
    old_start = before.index(P319_BYPASS_PREIMAGE)
    old_end = old_start + len(P319_BYPASS_PREIMAGE)
    new_start = after.index(P322_BYPASS_POSTIMAGE)
    new_end = new_start + len(P322_BYPASS_POSTIMAGE)
    if (
        before[:old_start] != after[:new_start]
        or before[old_end:] != after[new_end:]
    ):
        raise RuntimeRepairError(
            "P322 runtime delta is wider than p319_stock_bypass_to_pair"
        )
    for marker in P322_DIAGNOSTIC_PROVIDER_MARKERS:
        if before.count(marker) != after.count(marker):
            raise RuntimeRepairError(
                "P322 diagnostic/provider marker count widened: "
                + marker.decode("ascii")
            )


def validate_transformed_runtime(data: bytes) -> dict[str, Any]:
    """Validate the exact P322 postimage without changing it."""
    return _validate_p322_postimage(data)


def validate_repair(before: bytes, after: bytes) -> dict[str, Any]:
    """Validate a P319-to-P322 pair, including the no-widening delta."""
    before_receipt = validate_p319_preimage(before)
    after_receipt = validate_transformed_runtime(after)
    _validate_exact_delta(before, after)
    return {
        "contract_id": P322_CONTRACT_ID,
        "schema": P322_SCHEMA,
        "target": P322_TARGET,
        "source_kind": "P3.19 generated stock runtime include",
        "transformed_kind": "P322 transformed P3.19 stock runtime include",
        "before": before_receipt,
        "after": after_receipt,
        "changed_anchor": "p319_stock_bypass_to_pair",
        "changed_only_in_anchor": True,
        "diagnostic_provider_widening": False,
    }


def validate_runtime(data: bytes) -> dict[str, Any]:
    """Public alias for the P322 transformed-runtime validator."""
    return validate_transformed_runtime(data)


def transform_runtime_include(data: bytes) -> bytes:
    """Apply the one-anchor P322 repair to a P3.19 runtime include."""
    validate_p319_preimage(data)
    result = data.replace(P319_BYPASS_PREIMAGE, P322_BYPASS_POSTIMAGE, 1)
    validate_repair(data, result)
    return result


def transform_runtime(data: bytes) -> bytes:
    """Compatibility spelling for callers that name the include "runtime"."""
    return transform_runtime_include(data)


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    """Transform one named runtime member and reject any other source delta."""
    if not isinstance(source, Mapping):
        raise RuntimeRepairError("P322 source bundle must be a mapping")
    if P322_RUNTIME_KEY not in source:
        raise RuntimeRepairError(f"P322 source bundle lacks {P322_RUNTIME_KEY}")
    result = dict(source)
    result[P322_RUNTIME_KEY] = transform_runtime_include(source[P322_RUNTIME_KEY])
    changed = {key for key in result if result[key] != source[key]}
    if changed != {P322_RUNTIME_KEY}:
        raise RuntimeRepairError(f"P322 artifact delta differs: {sorted(changed)}")
    return result


__all__ = [
    "P319_BYPASS_PREIMAGE",
    "P319_STOCK_ENCODER_SYMBOL",
    "P319_STOCK_PUBLISHER_CALL",
    "P319_STOCK_PUBLISHER_DEFINITION",
    "P319_STOCK_RUNTIME_MARKER",
    "P322_BYPASS_POSTIMAGE",
    "P322_CONTRACT_ID",
    "P322_DIAGNOSTIC_PROVIDER_MARKERS",
    "P322_RUNTIME_KEY",
    "P322_SCHEMA",
    "P322_TARGET",
    "RuntimeRepairError",
    "transform_artifacts",
    "transform_runtime",
    "transform_runtime_include",
    "validate_p319_preimage",
    "validate_repair",
    "validate_runtime",
    "validate_transformed_runtime",
]
