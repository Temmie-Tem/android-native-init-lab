#!/usr/bin/env python3
"""P3.07 EUD, late-clock, and QSCRATCH telemetry contract."""

from __future__ import annotations

from typing import Any, Sequence

import s22plus_fyg8_p303_telemetry_spec as parent


SCHEMA = "s22plus_fyg8_p307_eud_qscratch_telemetry_spec_v1"
PROFILE = parent.PROFILE
ATTR_ORDINAL = parent.CLOCK_ORDINAL
SUMMARY_ORDINAL = parent.LOG_ORDINAL
OUTCOME_PROGRESS = parent.OUTCOME_PROGRESS
OUTCOME_FAILURE = parent.OUTCOME_FAILURE

ATTR_DETAIL_BASE = 0xD00
ATTR_CACHE_STATES = 2
ATTR_INIT_STATES = 3
ATTR_DPDM_STATES = 5
ATTR_PRECLOCK_STATES = 5
ATTR_VALUE_COUNT = (
    ATTR_CACHE_STATES
    * ATTR_INIT_STATES
    * ATTR_DPDM_STATES
    * ATTR_PRECLOCK_STATES
)
ATTR_DETAIL_MAX = ATTR_DETAIL_BASE + ATTR_VALUE_COUNT - 1

INIT_NOT_REACHED = 0
INIT_REACHED_NO_CSR = 1
INIT_REACHED_CSR = 2

DPDM_NOT_SEEN = 0
DPDM_BEFORE_INIT_0 = 1
DPDM_BEFORE_INIT_1 = 2
DPDM_AFTER_INIT_0 = 3
DPDM_AFTER_INIT_1 = 4

PRECLOCK_NOT_SEEN = 0
PRECLOCK_0_0 = 1
PRECLOCK_0_1 = 2
PRECLOCK_1_0 = 3
PRECLOCK_1_1 = 4

INIT_NAMES = {
    INIT_NOT_REACHED: "not-reached",
    INIT_REACHED_NO_CSR: "reached-no-csr",
    INIT_REACHED_CSR: "reached-csr-eud",
}
DPDM_NAMES = {
    DPDM_NOT_SEEN: "not-seen",
    DPDM_BEFORE_INIT_0: "before-init-value-0",
    DPDM_BEFORE_INIT_1: "before-init-value-1",
    DPDM_AFTER_INIT_0: "after-init-value-0",
    DPDM_AFTER_INIT_1: "after-init-value-1",
}
PRECLOCK_NAMES = {
    PRECLOCK_NOT_SEEN: "not-seen",
    PRECLOCK_0_0: "clocks-disabled-request-off",
    PRECLOCK_0_1: "clocks-disabled-request-on",
    PRECLOCK_1_0: "clocks-enabled-request-off",
    PRECLOCK_1_1: "clocks-enabled-request-on",
}

QSCRATCH_COUNT_BUCKETS = 4
QSCRATCH_BIT_CATEGORIES = 6
QSCRATCH_STATE_COUNT = 1 + QSCRATCH_COUNT_BUCKETS * QSCRATCH_BIT_CATEGORIES

SUMMARY_DETAIL_BASE = 0x4001
SUMMARY_CLOCK_STATES = parent.CLOCK_VALUE_COUNT
SUMMARY_VALUE_COUNT = SUMMARY_CLOCK_STATES * QSCRATCH_STATE_COUNT
SUMMARY_DETAIL_MAX = SUMMARY_DETAIL_BASE + SUMMARY_VALUE_COUNT - 1

DETAIL_EUD_CACHE_READ_FAILED = 0x6010
DETAIL_EUD_CACHE_FORMAT_CONTRADICTION = 0x6011
DETAIL_EUD_CACHE_LIFECYCLE_CONTRADICTION = 0x6012
DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION = 0x6013
DETAIL_KMSG_ATTRIBUTION_ORDER_CONTRADICTION = 0x6014
DETAIL_KMSG_ATTRIBUTION_DOMAIN_CONTRADICTION = 0x6015
DETAIL_QSCRATCH_PROFILE_RECORD_MISMATCH = 0x6016
DETAIL_QSCRATCH_RECORD_CONTRADICTION = 0x6017
DETAIL_QSCRATCH_VALUE_DOMAIN_CONTRADICTION = 0x6018
DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION = 0x6019

CONTRADICTION_DETAIL_NAMES = {
    DETAIL_EUD_CACHE_READ_FAILED: "eud-cache-read-failed",
    DETAIL_EUD_CACHE_FORMAT_CONTRADICTION: "eud-cache-format-contradiction",
    DETAIL_EUD_CACHE_LIFECYCLE_CONTRADICTION: "eud-cache-lifecycle-contradiction",
    DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION: "kmsg-attribution-format-contradiction",
    DETAIL_KMSG_ATTRIBUTION_ORDER_CONTRADICTION: "kmsg-attribution-order-contradiction",
    DETAIL_KMSG_ATTRIBUTION_DOMAIN_CONTRADICTION: "kmsg-attribution-domain-contradiction",
    DETAIL_QSCRATCH_PROFILE_RECORD_MISMATCH: "qscratch-profile-record-mismatch",
    DETAIL_QSCRATCH_RECORD_CONTRADICTION: "qscratch-record-contradiction",
    DETAIL_QSCRATCH_VALUE_DOMAIN_CONTRADICTION: "qscratch-value-domain-contradiction",
    DETAIL_FINAL_PAIR_DOMAIN_CONTRADICTION: "final-pair-domain-contradiction",
}

EUD_CACHE_PATH = "/sys/module/eud/parameters/enable"
EUD_MODULE_INDEX = 37
HSPHY_MODULE_INDEX = 55
DWC3_MSM_MODULE_INDEX = 58

DWC3_MODULE_PATH = (
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/ramdisk-list/vendor/extract/lib/modules/dwc3-msm.ko"
)
DWC3_MODULE_SHA256 = "8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1"
DWC3_MODULE_BUILD_ID = "9c5379199e420d34e1e0f0e6857705cf34f03f1b"
DWC3_MODULE_RUNTIME_NAME = "dwc3_msm"
QSCRATCH_SYMBOL = "dwc3_otg_start_peripheral"
QSCRATCH_SYMBOL_VALUE = 0xCC3C
QSCRATCH_PROBE_OFFSET = 0x4CC
QSCRATCH_READBACK_OFFSET = 0x4B4
QSCRATCH_VBUS_VALID_BIT = 20
QSCRATCH_SW_SESSVLD_SEL_BIT = 28


def encode_attribution(
    *, cache_value: int, init_state: int, dpdm_state: int, preclock_state: int
) -> int:
    if cache_value not in range(ATTR_CACHE_STATES):
        raise ValueError("P3.07 EUD cache value differs")
    if init_state not in INIT_NAMES:
        raise ValueError("P3.07 init state differs")
    if dpdm_state not in DPDM_NAMES:
        raise ValueError("P3.07 DPDM state differs")
    if preclock_state not in PRECLOCK_NAMES:
        raise ValueError("P3.07 pre-init clock state differs")
    index = cache_value
    index = index * ATTR_INIT_STATES + init_state
    index = index * ATTR_DPDM_STATES + dpdm_state
    index = index * ATTR_PRECLOCK_STATES + preclock_state
    return ATTR_DETAIL_BASE + index


def decode_attribution(detail: int) -> dict[str, Any]:
    index = detail - ATTR_DETAIL_BASE
    if not 0 <= index < ATTR_VALUE_COUNT:
        raise ValueError("P3.07 detail is not an attribution result")
    index, preclock_state = divmod(index, ATTR_PRECLOCK_STATES)
    index, dpdm_state = divmod(index, ATTR_DPDM_STATES)
    cache_value, init_state = divmod(index, ATTR_INIT_STATES)
    pair = (cache_value, int(init_state == INIT_REACHED_CSR))
    if init_state == INIT_NOT_REACHED:
        conclusion = "init-not-reached-no-eud-conclusion"
    elif pair == (1, 1):
        conclusion = "eud-seen-by-secure-cache-and-phy-init"
    elif pair == (0, 0):
        conclusion = "eud-branch-refuted-at-both-samples"
    else:
        conclusion = "timing-or-reader-divergence-no-causal-conclusion"
    return {
        "cache_value": cache_value,
        "init_state": init_state,
        "init_state_name": INIT_NAMES[init_state],
        "init_csr_eud_seen": init_state == INIT_REACHED_CSR,
        "dpdm_state": dpdm_state,
        "dpdm_state_name": DPDM_NAMES[dpdm_state],
        "preclock_state": preclock_state,
        "preclock_state_name": PRECLOCK_NAMES[preclock_state],
        "eud_pair_conclusion": conclusion,
    }


def qscratch_count_bucket(count: int) -> int:
    if count <= 0:
        raise ValueError("P3.07 QSCRATCH hit bucket requires a hit")
    if count == 1:
        return 0
    if count <= 3:
        return 1
    if count <= 7:
        return 2
    return 3


def qscratch_bit_category(values: Sequence[int]) -> int:
    if not values:
        raise ValueError("P3.07 QSCRATCH bit category requires values")
    vbus = {(value >> QSCRATCH_VBUS_VALID_BIT) & 1 for value in values}
    sess = {(value >> QSCRATCH_SW_SESSVLD_SEL_BIT) & 1 for value in values}
    if len(vbus) > 1:
        return 5
    if vbus == {0}:
        return 0 if sess == {0} else 1
    if sess == {0}:
        return 2
    if sess == {1}:
        return 3
    return 4


def encode_qscratch(values: Sequence[int]) -> int:
    if not values:
        return 0
    if any(not 0 <= value <= 0xFFFFFFFF for value in values):
        raise ValueError("P3.07 QSCRATCH value differs")
    return (
        1
        + qscratch_count_bucket(len(values)) * QSCRATCH_BIT_CATEGORIES
        + qscratch_bit_category(values)
    )


def decode_qscratch(state: int) -> dict[str, Any]:
    if not 0 <= state < QSCRATCH_STATE_COUNT:
        raise ValueError("P3.07 QSCRATCH state differs")
    if state == 0:
        return {
            "hit_count_bucket": 0,
            "bit_category": -1,
            "bit_category_name": "not-reached",
        }
    bucket, category = divmod(state - 1, QSCRATCH_BIT_CATEGORIES)
    names = {
        0: "vbus-clear-session-select-clear",
        1: "vbus-clear-session-select-set-or-mixed",
        2: "vbus-set-session-select-clear",
        3: "vbus-set-session-select-set",
        4: "vbus-set-session-select-mixed",
        5: "vbus-valid-mixed",
    }
    return {
        "hit_count_bucket": bucket + 1,
        "bit_category": category,
        "bit_category_name": names[category],
    }


def encode_summary(*, clock_detail: int, qscratch_state: int) -> int:
    clock_index = clock_detail - parent.CLOCK_DETAIL_BASE
    if not 0 <= clock_index < SUMMARY_CLOCK_STATES:
        raise ValueError("P3.07 clock detail differs")
    if not 0 <= qscratch_state < QSCRATCH_STATE_COUNT:
        raise ValueError("P3.07 QSCRATCH state differs")
    return SUMMARY_DETAIL_BASE + clock_index * QSCRATCH_STATE_COUNT + qscratch_state


def decode_summary(detail: int) -> dict[str, Any]:
    index = detail - SUMMARY_DETAIL_BASE
    if not 0 <= index < SUMMARY_VALUE_COUNT:
        raise ValueError("P3.07 detail is not a combined summary")
    clock_index, qscratch_state = divmod(index, QSCRATCH_STATE_COUNT)
    clock_detail = parent.CLOCK_DETAIL_BASE + clock_index
    return {
        "clock_detail": clock_detail,
        "clock": parent.decode_clock(clock_detail),
        "qscratch_state": qscratch_state,
        "qscratch": decode_qscratch(qscratch_state),
    }


def validate() -> dict[str, Any]:
    rules = set(parent.exact_detail_rules())
    attr = {
        (ATTR_ORDINAL, OUTCOME_PROGRESS, detail)
        for detail in range(ATTR_DETAIL_BASE, ATTR_DETAIL_MAX + 1)
    }
    if (
        ATTR_VALUE_COUNT != 150
        or ATTR_DETAIL_MAX != 0xD95
        or not attr.issubset(rules)
        or QSCRATCH_STATE_COUNT != 25
        or SUMMARY_VALUE_COUNT != 4075
        or SUMMARY_DETAIL_MAX != 0x4FEB
        or not (0x4000 < SUMMARY_DETAIL_BASE <= SUMMARY_DETAIL_MAX <= 0x4FFF)
    ):
        raise ValueError("P3.07 fixed-Image encoding contract differs")
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "attribution_value_count": ATTR_VALUE_COUNT,
        "attribution_detail_range": [ATTR_DETAIL_BASE, ATTR_DETAIL_MAX],
        "qscratch_state_count": QSCRATCH_STATE_COUNT,
        "summary_value_count": SUMMARY_VALUE_COUNT,
        "summary_detail_range": [SUMMARY_DETAIL_BASE, SUMMARY_DETAIL_MAX],
        "eud_cache_path": EUD_CACHE_PATH,
        "eud_module_index": EUD_MODULE_INDEX,
        "hsphy_module_index": HSPHY_MODULE_INDEX,
        "dwc3_msm_module_index": DWC3_MSM_MODULE_INDEX,
        "fixed_image_exact_rules": True,
        "verified": True,
    }
