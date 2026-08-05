#!/usr/bin/env python3
"""Fold the final two P3.04 module loads into one inherited checkpoint slot."""

from __future__ import annotations


MINIMUM_MODULE_COUNT = 60
FOLDED_FAILURE_BASE = 0x700
MAX_MODULE_COUNT = 256


class TransformError(ValueError):
    pass


_OLD_LOOP = b"""    for (size_t index = 0; index < S22PLUS_O2_MODULE_PLAN_COUNT; ++index) {
        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
    }
"""

_NEW_LOOP = b"""    enum {
        P305_MODULE_STAGE_CAPACITY =
            S22_P241_GATE_STAGE_BASE - S22_P241_MODULE_STAGE_BASE,
        P305_FOLDED_MODULE_INDEX = P305_MODULE_STAGE_CAPACITY - 1U,
        P305_FOLDED_FAILURE_BASE = 0x700U,
    };
    _Static_assert(
        S22_P241_GATE_STAGE_BASE > S22_P241_MODULE_STAGE_BASE,
        "P3.05 positive module stage space");
    _Static_assert(
        S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX <
            S22_P241_GATE_STAGE_BASE,
        "P3.05 module stage and bind gate do not overlap");
    _Static_assert(
        S22PLUS_O2_MODULE_PLAN_COUNT >= P305_MODULE_STAGE_CAPACITY,
        "P3.05 folded tail exists");
    _Static_assert(
        S22PLUS_O2_MODULE_PLAN_COUNT <= 256U,
        "P3.05 module index fits retained detail");
    for (size_t index = 0; index < P305_FOLDED_MODULE_INDEX; ++index) {
        E1_REQUIRE(
            S22_P241_MODULE_STAGE_BASE + (uint8_t)index,
            (uint8_t)index,
            p241_load_and_verify_module(index));
    }
    for (size_t index = P305_FOLDED_MODULE_INDEX;
         index < S22PLUS_O2_MODULE_PLAN_COUNT;
         ++index) {
        long p305_folded_load_rc = p241_load_and_verify_module(index);
        if (p305_folded_load_rc != 0) {
            fail_at(
                S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX,
                P305_FOLDED_MODULE_INDEX,
                (long)(P305_FOLDED_FAILURE_BASE + index));
        }
    }
    long p305_checkpoint_rc = s22_r4w1e_checkpoint_progress(
        &g_checkpoint,
        S22_P241_MODULE_STAGE_BASE + P305_FOLDED_MODULE_INDEX,
        P305_FOLDED_MODULE_INDEX);
    if (p305_checkpoint_rc != 0) {
        quiet_park();
    }
"""


def transform(runtime: bytes) -> bytes:
    if runtime.count(_OLD_LOOP) != 1 or _NEW_LOOP in runtime:
        raise TransformError("P3.04 module loop shape differs")
    result = runtime.replace(_OLD_LOOP, _NEW_LOOP, 1)
    if result.count(_OLD_LOOP) != 0 or result.count(_NEW_LOOP) != 1:
        raise TransformError("P3.05 folded module loop replacement differs")
    return result
