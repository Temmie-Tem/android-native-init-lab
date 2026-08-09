#!/usr/bin/env python3
"""Single-phase P3.11 early HS-PHY clock telemetry contract."""

from __future__ import annotations

from dataclasses import dataclass

import s22plus_fyg8_p308_telemetry_spec as p308
import s22plus_fyg8_p311_callsite_spec as callsites


PROFILE = p308.PROFILE
ATTR_ORDINAL = p308.ATTR_ORDINAL
SUMMARY_ORDINAL = p308.SUMMARY_ORDINAL
EARLY_EVENT_COUNT = 30
CALLSITE_EVENT_BASE = 6
CALLSITE_COUNT = callsites.CALLSITE_COUNT
RECORD_CAPACITY = 64

DOMAIN_PROBE = 0
DOMAIN_SET_SUSPEND = 1
DOMAIN_INIT = 2
DOMAIN_NONE = 3
DOMAIN_COUNT = 4

REACH_PROBE = 1 << 0
REACH_INIT = 1 << 1
REACH_SET_SUSPEND_ZERO = 1 << 2
REACH_MASK_COUNT = 8
MULTI_PATH_COUNT = 2
QSCRATCH_STATE_COUNT = p308.p307.QSCRATCH_STATE_COUNT

CLOCK_STATE_COUNT = 9
CLOCK_PAIR_COUNT = CLOCK_STATE_COUNT * CLOCK_STATE_COUNT
FIRST_DETAIL_BASE = 0xD00
FIRST_DETAIL_NO_CLOCK_PATH = FIRST_DETAIL_BASE + CLOCK_PAIR_COUNT
FIRST_DETAIL_MAX = FIRST_DETAIL_NO_CLOCK_PATH

SUMMARY_DETAIL_BASE = 0x4001
SUMMARY_VALUE_COUNT = (
    DOMAIN_COUNT * MULTI_PATH_COUNT * REACH_MASK_COUNT * QSCRATCH_STATE_COUNT
)
SUMMARY_DETAIL_MAX = SUMMARY_DETAIL_BASE + SUMMARY_VALUE_COUNT - 1

DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE = 0x6801
DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE = 0x6802
DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED = 0x6803
DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED = 0x6804
DETAIL_EARLY_PROFILE_RECORD_MISMATCH = 0x6805
DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION = 0x6806
DETAIL_EARLY_CALLER_PAIR_CONTRADICTION = 0x6807
DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION = 0x6808
DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION = 0x6809
DETAIL_EARLY_CFG_AHB_CONTRADICTION = 0x680A
DETAIL_EARLY_DOMAIN_CONTRADICTION = 0x680B
DETAIL_EARLY_TRACE_RING_LOSS = 0x680C

CONTRADICTION_DETAIL_NAMES = {
    DETAIL_EARLY_TRACE_CONTROL_UNAVAILABLE: "early-trace-control-unavailable",
    DETAIL_EARLY_TRACE_REGISTRATION_UNAVAILABLE: "early-trace-registration-unavailable",
    DETAIL_EARLY_TRACE_CLEANUP_UNVERIFIED: "early-trace-cleanup-unverified",
    DETAIL_EARLY_TRACE_SNAPSHOT_READ_FAILED: "early-trace-snapshot-read-failed",
    DETAIL_EARLY_PROFILE_RECORD_MISMATCH: "early-profile-record-mismatch",
    DETAIL_EARLY_RECORD_FORMAT_CONTRADICTION: "early-record-format-contradiction",
    DETAIL_EARLY_CALLER_PAIR_CONTRADICTION: "early-caller-pair-contradiction",
    DETAIL_EARLY_CALLSITE_FLOW_CONTRADICTION: "early-callsite-flow-contradiction",
    DETAIL_EARLY_CALLSITE_RETURN_CONTRADICTION: "early-callsite-return-contradiction",
    DETAIL_EARLY_CFG_AHB_CONTRADICTION: "early-cfg-ahb-contradiction",
    DETAIL_EARLY_DOMAIN_CONTRADICTION: "early-domain-contradiction",
    DETAIL_EARLY_TRACE_RING_LOSS: "early-trace-ring-loss",
}


@dataclass(frozen=True)
class Event:
    name: str
    definition: str
    filter: str = "common_pid >= 0"


def _caller_events() -> tuple[Event, ...]:
    module = callsites.MODULE_RUNTIME_NAME
    return (
        Event("p311_probe_in", f"p:p282/p311_probe_in {module}:msm_hsphy_probe\n"),
        Event("p311_probe_out", f"r32:p282/p311_probe_out {module}:msm_hsphy_probe rc=$retval:s32\n"),
        Event("p311_init_in", f"p:p282/p311_init_in {module}:msm_hsphy_init\n"),
        Event("p311_init_out", f"r32:p282/p311_init_out {module}:msm_hsphy_init rc=$retval:s32\n"),
        Event(
            "p311_suspend_in",
            f"p:p282/p311_suspend_in {module}:msm_hsphy_set_suspend suspend=%x1:s32\n",
        ),
        Event(
            "p311_suspend_out",
            f"r32:p282/p311_suspend_out {module}:msm_hsphy_set_suspend rc=$retval:s32\n",
        ),
    )


def _callsite_events() -> tuple[Event, ...]:
    module = callsites.MODULE_RUNTIME_NAME
    rows: list[Event] = []
    for phase, symbol, _value, _size, _cfi, _cfi_value, sites in callsites.CALLER_SPECS:
        for name, _clock, _operation, offset, _consumer in sites:
            event_name = f"p311_{name}"
            rows.append(
                Event(
                    event_name,
                    f"p:p282/{event_name} {module}:{symbol}+0x{offset:x} rc=%x0:s32\n",
                )
            )
    return tuple(rows)


EARLY_EVENTS = (*_caller_events(), *_callsite_events())
EVENT_INDEX = {event.name: index for index, event in enumerate(EARLY_EVENTS)}


def encode_first(ref_src_state: int, ref_state: int) -> int:
    if not 0 <= ref_src_state < CLOCK_STATE_COUNT:
        raise ValueError("P3.11 ref_src clock state out of range")
    if not 0 <= ref_state < CLOCK_STATE_COUNT:
        raise ValueError("P3.11 ref clock state out of range")
    return FIRST_DETAIL_BASE + ref_src_state * CLOCK_STATE_COUNT + ref_state


def decode_first(detail: int) -> dict[str, int | str]:
    if detail == FIRST_DETAIL_NO_CLOCK_PATH:
        return {"kind": "no-clock-path"}
    index = detail - FIRST_DETAIL_BASE
    if not 0 <= index < CLOCK_PAIR_COUNT:
        raise ValueError("P3.11 first detail out of range")
    return {
        "kind": "clock-pair",
        "ref_src_state": index // CLOCK_STATE_COUNT,
        "ref_state": index % CLOCK_STATE_COUNT,
    }


def encode_summary(domain: int, multi_path: int, reach_mask: int, qscratch_state: int) -> int:
    if not 0 <= domain < DOMAIN_COUNT:
        raise ValueError("P3.11 domain out of range")
    if multi_path not in (0, 1):
        raise ValueError("P3.11 multi-path flag out of range")
    if not 0 <= reach_mask < REACH_MASK_COUNT:
        raise ValueError("P3.11 reach mask out of range")
    if not 0 <= qscratch_state < QSCRATCH_STATE_COUNT:
        raise ValueError("P3.11 QSCRATCH state out of range")
    index = domain
    index = index * MULTI_PATH_COUNT + multi_path
    index = index * REACH_MASK_COUNT + reach_mask
    index = index * QSCRATCH_STATE_COUNT + qscratch_state
    return SUMMARY_DETAIL_BASE + index


def decode_summary(detail: int) -> dict[str, int]:
    index = detail - SUMMARY_DETAIL_BASE
    if not 0 <= index < SUMMARY_VALUE_COUNT:
        raise ValueError("P3.11 summary detail out of range")
    qscratch_state = index % QSCRATCH_STATE_COUNT
    index //= QSCRATCH_STATE_COUNT
    reach_mask = index % REACH_MASK_COUNT
    index //= REACH_MASK_COUNT
    multi_path = index % MULTI_PATH_COUNT
    domain = index // MULTI_PATH_COUNT
    return {
        "domain": domain,
        "multi_path": multi_path,
        "reach_mask": reach_mask,
        "qscratch_state": qscratch_state,
    }


def first_outputs() -> tuple[int, ...]:
    return tuple(range(FIRST_DETAIL_BASE, FIRST_DETAIL_MAX + 1))


def summary_outputs() -> tuple[int, ...]:
    return tuple(range(SUMMARY_DETAIL_BASE, SUMMARY_DETAIL_MAX + 1))


def validate() -> dict[str, object]:
    if len(EARLY_EVENTS) != EARLY_EVENT_COUNT or len(EVENT_INDEX) != EARLY_EVENT_COUNT:
        raise ValueError("P3.11 early event inventory differs")
    if CALLSITE_EVENT_BASE + CALLSITE_COUNT != EARLY_EVENT_COUNT:
        raise ValueError("P3.11 callsite event extent differs")
    if FIRST_DETAIL_MAX > 0xDAF:
        raise ValueError("P3.11 first family exceeds fixed exact-rule band")
    if SUMMARY_DETAIL_MAX > 0x4FFF:
        raise ValueError("P3.11 summary family exceeds fixed failure band")
    for ref_src in range(CLOCK_STATE_COUNT):
        for ref in range(CLOCK_STATE_COUNT):
            decoded = decode_first(encode_first(ref_src, ref))
            if decoded != {
                "kind": "clock-pair",
                "ref_src_state": ref_src,
                "ref_state": ref,
            }:
                raise ValueError("P3.11 clock-pair round trip differs")
    checked = 0
    for domain in range(DOMAIN_COUNT):
        for multi in range(MULTI_PATH_COUNT):
            for reach in range(REACH_MASK_COUNT):
                for qscratch in range(QSCRATCH_STATE_COUNT):
                    decoded = decode_summary(
                        encode_summary(domain, multi, reach, qscratch)
                    )
                    if decoded != {
                        "domain": domain,
                        "multi_path": multi,
                        "reach_mask": reach,
                        "qscratch_state": qscratch,
                    }:
                        raise ValueError("P3.11 summary round trip differs")
                    checked += 1
    if checked != SUMMARY_VALUE_COUNT:
        raise ValueError("P3.11 summary enumeration differs")
    return {
        "schema": "s22plus_fyg8_p311_telemetry_spec_v1",
        "early_event_count": EARLY_EVENT_COUNT,
        "callsite_count": CALLSITE_COUNT,
        "record_capacity": RECORD_CAPACITY,
        "first_detail_range": [FIRST_DETAIL_BASE, FIRST_DETAIL_MAX],
        "first_output_count": len(first_outputs()),
        "summary_detail_range": [SUMMARY_DETAIL_BASE, SUMMARY_DETAIL_MAX],
        "summary_output_count": checked,
        "contradiction_detail_count": len(CONTRADICTION_DETAIL_NAMES),
        "fixed_image_gate_compatible": True,
        "verified": True,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(validate(), sort_keys=True))
