#!/usr/bin/env python3
"""P3.06 DWC3 MSM IPC state-machine telemetry contract."""

from __future__ import annotations

from typing import Any

import s22plus_fyg8_p303_telemetry_spec as parent


SCHEMA = "s22plus_fyg8_p306_ipc_state_telemetry_spec_v1"
PROFILE = parent.PROFILE
CHAIN_ORDINAL = parent.CLOCK_ORDINAL
SUMMARY_ORDINAL = parent.LOG_ORDINAL
OUTCOME_PROGRESS = parent.OUTCOME_PROGRESS
OUTCOME_FAILURE = parent.OUTCOME_FAILURE

CHAIN_DETAIL_BASE = 0xD01
CHAIN_MARKER_BITS = 7
CHAIN_VALUE_COUNT = 1 << CHAIN_MARKER_BITS
CHAIN_DETAIL_MAX = CHAIN_DETAIL_BASE + CHAIN_VALUE_COUNT - 1

SUMMARY_DETAIL_BASE = 0x4001
SUMMARY_CONDITION_MASKS = 16
SUMMARY_COUNT_BUCKETS = 4
SUMMARY_COMPLETE_STATES = 2
SUMMARY_VALUE_COUNT = (
    SUMMARY_CONDITION_MASKS
    * SUMMARY_COUNT_BUCKETS
    * SUMMARY_COUNT_BUCKETS
    * SUMMARY_COUNT_BUCKETS
    * SUMMARY_COMPLETE_STATES
)
SUMMARY_DETAIL_MAX = SUMMARY_DETAIL_BASE + SUMMARY_VALUE_COUNT - 1

MARKER_MODE_DEVICE = 1 << 0
MARKER_QRW_ENABLE = 1 << 1
MARKER_QRW_DISABLE = 1 << 2
MARKER_BSV_SET = 1 << 3
MARKER_INPUTS_BSV = 1 << 4
MARKER_START_GADGET = 1 << 5
MARKER_PERIPHERAL = 1 << 6

CONDITION_BSV_CLEAR = 1 << 0
CONDITION_CORE_INIT_FAILED = 1 << 1
CONDITION_UNDEFINED_NO_BSV = 1 << 2
CONDITION_NO_PULLUP = 1 << 3

DETAIL_MOUNT_FAILED = 0x6001
DETAIL_PATH_UNAVAILABLE = 0x6002
DETAIL_READ_FAILED = 0x6003
DETAIL_FORMAT_CONTRADICTION = 0x6004
DETAIL_CLEANUP_FAILED = 0x6005
DETAIL_LIFECYCLE_CONTRADICTION = 0x6006

MARKER_NAMES = {
    MARKER_MODE_DEVICE: "mode-device",
    MARKER_QRW_ENABLE: "q-rw-vbus-enable",
    MARKER_QRW_DISABLE: "q-rw-vbus-disable",
    MARKER_BSV_SET: "b-session-valid-set",
    MARKER_INPUTS_BSV: "inputs-b-session-valid",
    MARKER_START_GADGET: "start-gadget",
    MARKER_PERIPHERAL: "peripheral-state",
}
CONDITION_NAMES = {
    CONDITION_BSV_CLEAR: "b-session-valid-clear-seen",
    CONDITION_CORE_INIT_FAILED: "core-init-failed-seen",
    CONDITION_UNDEFINED_NO_BSV: "undefined-no-bsv-seen",
    CONDITION_NO_PULLUP: "no-pullup-seen",
}


def count_bucket(count: int) -> int:
    if count < 0:
        raise ValueError("P3.06 count is negative")
    if count == 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    return 3


def encode_chain(marker_mask: int) -> int:
    if not 0 <= marker_mask < CHAIN_VALUE_COUNT:
        raise ValueError("P3.06 marker mask differs")
    return CHAIN_DETAIL_BASE + marker_mask


def decode_chain(detail: int) -> dict[str, Any]:
    marker_mask = detail - CHAIN_DETAIL_BASE
    if not 0 <= marker_mask < CHAIN_VALUE_COUNT:
        raise ValueError("P3.06 detail is not a chain result")
    return {
        "marker_mask": marker_mask,
        "markers": [
            name for bit, name in MARKER_NAMES.items() if marker_mask & bit
        ],
    }


def encode_summary(
    *,
    condition_mask: int,
    bsv_set_count: int,
    start_gadget_count: int,
    peripheral_count: int,
    ordered_chain_complete: bool,
) -> int:
    if not 0 <= condition_mask < SUMMARY_CONDITION_MASKS:
        raise ValueError("P3.06 condition mask differs")
    index = condition_mask
    for count in (bsv_set_count, start_gadget_count, peripheral_count):
        index = index * SUMMARY_COUNT_BUCKETS + count_bucket(count)
    index = index * SUMMARY_COMPLETE_STATES + int(ordered_chain_complete)
    return SUMMARY_DETAIL_BASE + index


def decode_summary(detail: int) -> dict[str, Any]:
    index = detail - SUMMARY_DETAIL_BASE
    if not 0 <= index < SUMMARY_VALUE_COUNT:
        raise ValueError("P3.06 detail is not an IPC summary")
    index, complete = divmod(index, SUMMARY_COMPLETE_STATES)
    index, peripheral = divmod(index, SUMMARY_COUNT_BUCKETS)
    index, start = divmod(index, SUMMARY_COUNT_BUCKETS)
    condition_mask, bsv = divmod(index, SUMMARY_COUNT_BUCKETS)
    return {
        "condition_mask": condition_mask,
        "conditions": [
            name
            for bit, name in CONDITION_NAMES.items()
            if condition_mask & bit
        ],
        "bsv_set_count_bucket": bsv,
        "start_gadget_count_bucket": start,
        "peripheral_count_bucket": peripheral,
        "ordered_chain_complete": bool(complete),
    }


def validate() -> dict[str, Any]:
    rules = set(parent.exact_detail_rules())
    chain = {
        (CHAIN_ORDINAL, OUTCOME_PROGRESS, encode_chain(mask))
        for mask in range(CHAIN_VALUE_COUNT)
    }
    if (
        CHAIN_DETAIL_BASE != 0xD01
        or CHAIN_DETAIL_MAX != 0xD80
        or SUMMARY_VALUE_COUNT != 2048
        or SUMMARY_DETAIL_MAX != 0x4800
        or not chain.issubset(rules)
    ):
        raise ValueError("P3.06 fixed-Image encoding contract differs")
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "chain_value_count": CHAIN_VALUE_COUNT,
        "chain_detail_range": [CHAIN_DETAIL_BASE, CHAIN_DETAIL_MAX],
        "summary_value_count": SUMMARY_VALUE_COUNT,
        "summary_detail_range": [SUMMARY_DETAIL_BASE, SUMMARY_DETAIL_MAX],
        "fixed_image_exact_rules": True,
        "verified": True,
    }

