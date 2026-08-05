#!/usr/bin/env python3
"""P3.03 HS-PHY silent-failure attribution telemetry contract."""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from typing import Any, Mapping, Sequence

import s22plus_fyg8_p301_telemetry_spec as base


SCHEMA = "s22plus_fyg8_p303_hsphy_silent_failure_telemetry_spec_v1"
PROFILE = base.PROFILE

OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE
CLOCK_ORDINAL = base.EVENT_LINK_ORDINAL
LOG_ORDINAL = base.FINAL_STATE_ORDINAL

CLOCK_DETAIL_BASE = 0xD00
CLOCK_ERRNO_BUCKETS = 4
CLOCK_RESULT_STATES = 1 + 2 * CLOCK_ERRNO_BUCKETS
CLOCK_PAIR_STATES = CLOCK_RESULT_STATES * CLOCK_RESULT_STATES
CLOCK_MISSED_INDEX = 0
CLOCK_EUD_INDEX_BASE = 1
CLOCK_NORMAL_INDEX_BASE = CLOCK_EUD_INDEX_BASE + CLOCK_PAIR_STATES
CLOCK_VALUE_COUNT = 1 + 2 * CLOCK_PAIR_STATES
CLOCK_DETAIL_MAX = CLOCK_DETAIL_BASE + CLOCK_VALUE_COUNT - 1

LOG_DETAIL_BASE = 0x4001
LOG_OFFSET_CODES = 128
LOG_COUNT_BUCKETS = 4
LOG_RESET_MASKS = 4
LOG_VALUE_COUNT = LOG_OFFSET_CODES * LOG_COUNT_BUCKETS * LOG_RESET_MASKS
LOG_DETAIL_MAX = LOG_DETAIL_BASE + LOG_VALUE_COUNT - 1

DETAIL_CALLSITE_COUNT_CONTRADICTION = 0x6001
DETAIL_CALLSITE_BRANCH_CONTRADICTION = 0x6002
DETAIL_CFG_AHB_PRESENCE_CONTRADICTION = 0x6003
DETAIL_CALLSITE_RETURN_DOMAIN_CONTRADICTION = 0x6004
DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION = 0x6005
DETAIL_KMSG_OPEN_FAILED = 0x6006
DETAIL_KMSG_READ_FAILED = 0x6007
DETAIL_KMSG_RING_LOSS = 0x6008
DETAIL_KMSG_SEQUENCE_CONTRADICTION = 0x6009
DETAIL_KMSG_PATH_NOT_REACHED = 0x600A
DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION = 0x600B
DETAIL_KMSG_COUNT_OVERFLOW = 0x600C
DETAIL_CLOCK_INIT_PATH_CONTRADICTION = 0x600D
DETAIL_CLOCK_PROFILE_RECORD_MISMATCH = 0x600E
DETAIL_TERMINAL_DOMAIN_CONTRADICTION = 0x600F

CONTRADICTION_DETAIL_NAMES = {
    DETAIL_CALLSITE_COUNT_CONTRADICTION: "hsphy-clock-callsite-count-contradiction",
    DETAIL_CALLSITE_BRANCH_CONTRADICTION: "hsphy-clock-branch-contradiction",
    DETAIL_CFG_AHB_PRESENCE_CONTRADICTION: "hsphy-cfg-ahb-unexpectedly-present",
    DETAIL_CALLSITE_RETURN_DOMAIN_CONTRADICTION: "hsphy-clock-return-domain-contradiction",
    DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION: "hsphy-clock-control-flow-contradiction",
    DETAIL_KMSG_OPEN_FAILED: "hsphy-kmsg-open-or-seek-failed",
    DETAIL_KMSG_READ_FAILED: "hsphy-kmsg-read-failed",
    DETAIL_KMSG_RING_LOSS: "hsphy-kmsg-ring-loss",
    DETAIL_KMSG_SEQUENCE_CONTRADICTION: "hsphy-kmsg-sequence-contradiction",
    DETAIL_KMSG_PATH_NOT_REACHED: "hsphy-kmsg-normal-path-not-reached",
    DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION: "hsphy-kmsg-readback-format-contradiction",
    DETAIL_KMSG_COUNT_OVERFLOW: "hsphy-kmsg-counter-overflow",
    DETAIL_CLOCK_INIT_PATH_CONTRADICTION: "hsphy-init-path-contradiction",
    DETAIL_CLOCK_PROFILE_RECORD_MISMATCH: "hsphy-clock-profile-record-mismatch",
    DETAIL_TERMINAL_DOMAIN_CONTRADICTION: "hsphy-terminal-domain-contradiction",
}

MODULE_PATH = (
    "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/vendor_dlkm/lib/modules/phy-msm-snps-hs.ko"
)
MODULE_SHA256 = "22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94"
MODULE_BUILD_ID = "cdb249f9a7599440ca66208f02caec0a6601bc03"
MODULE_RUNTIME_NAME = "phy_msm_snps_hs"
CALLSITE_SYMBOL = "msm_hsphy_init"
CALLSITE_SYMBOL_VALUE = 0x11F4

# Each probe is at the instruction immediately after BL.  The instruction at
# the probe site consumes w0 (CBNZ for prepare, CBZ for enable), proving that
# w0 is still the AArch64 return register rather than a path-dependent
# epilogue scratch value.
CALLSITES = (
    ("eud_ref_src_prepare", "eud", "ref_clk_src", "prepare", 0x0B4, "cbnz"),
    ("eud_ref_src_enable", "eud", "ref_clk_src", "enable", 0x0C0, "cbz"),
    ("eud_ref_prepare", "eud", "ref_clk", "prepare", 0x0DC, "cbnz"),
    ("eud_ref_enable", "eud", "ref_clk", "enable", 0x0E8, "cbz"),
    ("eud_cfg_prepare", "eud", "cfg_ahb_clk", "prepare", 0x104, "cbnz"),
    ("eud_cfg_enable", "eud", "cfg_ahb_clk", "enable", 0x110, "cbz"),
    ("normal_ref_src_prepare", "normal", "ref_clk_src", "prepare", 0x574, "cbnz"),
    ("normal_ref_src_enable", "normal", "ref_clk_src", "enable", 0x580, "cbz"),
    ("normal_ref_prepare", "normal", "ref_clk", "prepare", 0x59C, "cbnz"),
    ("normal_ref_enable", "normal", "ref_clk", "enable", 0x5A8, "cbz"),
    ("normal_cfg_prepare", "normal", "cfg_ahb_clk", "prepare", 0x5C4, "cbnz"),
    ("normal_cfg_enable", "normal", "cfg_ahb_clk", "enable", 0x5D0, "cbz"),
)
CALLSITE_COUNT = len(CALLSITES)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def errno_bucket(rc: int) -> int:
    if rc >= 0:
        raise ValueError("P3.03 errno bucket requires a negative return")
    if rc == -22:
        return 0
    if rc == -5:
        return 1
    if rc == -110:
        return 2
    return 3


def clock_state(*, prepare_rc: int, enable_hit: int, enable_rc: int) -> int:
    if prepare_rc > 0 or enable_rc > 0 or enable_hit not in (0, 1):
        raise ValueError("P3.03 clock return domain differs")
    if prepare_rc < 0:
        if enable_hit != 0:
            raise ValueError("P3.03 enable ran after prepare failure")
        return 1 + errno_bucket(prepare_rc)
    if enable_hit != 1:
        raise ValueError("P3.03 enable did not follow successful prepare")
    if enable_rc < 0:
        return 1 + CLOCK_ERRNO_BUCKETS + errno_bucket(enable_rc)
    return 0


def encode_clock(branch: str, ref_src_state: int, ref_state: int) -> int:
    if not 0 <= ref_src_state < CLOCK_RESULT_STATES:
        raise ValueError("P3.03 ref source state differs")
    if not 0 <= ref_state < CLOCK_RESULT_STATES:
        raise ValueError("P3.03 ref clock state differs")
    pair = ref_src_state * CLOCK_RESULT_STATES + ref_state
    if branch == "eud":
        index = CLOCK_EUD_INDEX_BASE + pair
    elif branch == "normal":
        index = CLOCK_NORMAL_INDEX_BASE + pair
    else:
        raise ValueError("P3.03 clock branch differs")
    return CLOCK_DETAIL_BASE + index


def encode_clock_missed() -> int:
    return CLOCK_DETAIL_BASE + CLOCK_MISSED_INDEX


def decode_clock(detail: int) -> dict[str, int | str]:
    index = detail - CLOCK_DETAIL_BASE
    if index == CLOCK_MISSED_INDEX:
        return {"branch": "missed", "ref_src_state": -1, "ref_state": -1}
    if CLOCK_EUD_INDEX_BASE <= index < CLOCK_NORMAL_INDEX_BASE:
        branch = "eud"
        pair = index - CLOCK_EUD_INDEX_BASE
    elif CLOCK_NORMAL_INDEX_BASE <= index < CLOCK_VALUE_COUNT:
        branch = "normal"
        pair = index - CLOCK_NORMAL_INDEX_BASE
    else:
        raise ValueError("P3.03 detail is not a clock result")
    ref_src_state, ref_state = divmod(pair, CLOCK_RESULT_STATES)
    return {
        "branch": branch,
        "ref_src_state": ref_src_state,
        "ref_state": ref_state,
    }


def readback_count_bucket(count: int) -> int:
    if count < 0:
        raise ValueError("P3.03 readback count is negative")
    if count == 0:
        return 0
    if count == 1:
        return 1
    if count <= 3:
        return 2
    return 3


def encode_log(*, readback_count: int, first_offset: int, reset_mask: int) -> int:
    bucket = readback_count_bucket(readback_count)
    if not 0 <= reset_mask < LOG_RESET_MASKS:
        raise ValueError("P3.03 reset mask differs")
    if readback_count == 0:
        if first_offset != 0:
            raise ValueError("P3.03 empty readback has an offset")
        offset_code = 0
    else:
        if first_offset < 0 or first_offset & 3:
            raise ValueError("P3.03 first readback offset is not aligned")
        offset_code = first_offset // 4 + 1
        if not 1 <= offset_code < LOG_OFFSET_CODES:
            raise ValueError("P3.03 first readback offset is out of range")
    index = (offset_code * LOG_COUNT_BUCKETS + bucket) * LOG_RESET_MASKS + reset_mask
    return LOG_DETAIL_BASE + index


def decode_log(detail: int) -> dict[str, int]:
    index = detail - LOG_DETAIL_BASE
    if not 0 <= index < LOG_VALUE_COUNT:
        raise ValueError("P3.03 detail is not a kmsg result")
    pair, reset_mask = divmod(index, LOG_RESET_MASKS)
    offset_code, count_bucket = divmod(pair, LOG_COUNT_BUCKETS)
    return {
        "first_offset": 0 if offset_code == 0 else (offset_code - 1) * 4,
        "count_bucket": count_bucket,
        "reset_mask": reset_mask,
    }


def classify_clock(hits: Sequence[int], returns: Sequence[int]) -> int:
    if len(hits) != CALLSITE_COUNT or len(returns) != CALLSITE_COUNT:
        raise ValueError("P3.03 callsite vector length differs")
    if any(hit not in (0, 1) for hit in hits):
        return DETAIL_CALLSITE_COUNT_CONTRADICTION
    if any(rc > 0 for hit, rc in zip(hits, returns) if hit):
        return DETAIL_CALLSITE_RETURN_DOMAIN_CONTRADICTION
    eud_active = any(hits[:6])
    normal_active = any(hits[6:])
    if eud_active and normal_active:
        return DETAIL_CALLSITE_BRANCH_CONTRADICTION
    if not eud_active and not normal_active:
        return encode_clock_missed()
    start = 0 if eud_active else 6
    branch = "eud" if eud_active else "normal"
    active = hits[start : start + 6]
    inactive = hits[6:] if eud_active else hits[:6]
    if any(inactive):
        return DETAIL_CALLSITE_BRANCH_CONTRADICTION
    if active[4] or active[5]:
        return DETAIL_CFG_AHB_PRESENCE_CONTRADICTION
    states = []
    for prepare_index, enable_index in ((0, 1), (2, 3)):
        if active[prepare_index] != 1:
            return DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION
        prepare_rc = returns[start + prepare_index]
        enable_hit = active[enable_index]
        enable_rc = returns[start + enable_index]
        try:
            states.append(
                clock_state(
                    prepare_rc=prepare_rc,
                    enable_hit=enable_hit,
                    enable_rc=enable_rc,
                )
            )
        except ValueError:
            return DETAIL_CALLSITE_CONTROL_FLOW_CONTRADICTION
    return encode_clock(branch, states[0], states[1])


@lru_cache(maxsize=1)
def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    return base.exact_detail_rules()


def descriptor() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "fixed_image": "P3.00 exact kernel Image; no kernel rebuild",
        "clock": {
            "ordinal": CLOCK_ORDINAL,
            "outcome": OUTCOME_PROGRESS,
            "detail_range": [CLOCK_DETAIL_BASE, CLOCK_DETAIL_MAX],
            "value_count": CLOCK_VALUE_COUNT,
            "cfg_ahb_clock": "absent in all four exact FYG8 DTBs",
        },
        "log": {
            "ordinal": LOG_ORDINAL,
            "outcome": OUTCOME_FAILURE,
            "detail_range": [LOG_DETAIL_BASE, LOG_DETAIL_MAX],
            "value_count": LOG_VALUE_COUNT,
            "stock_baseline": "same-campaign post-baseline-rotation D0 side evidence",
        },
        "module": {
            "path": MODULE_PATH,
            "sha256": MODULE_SHA256,
            "build_id": MODULE_BUILD_ID,
            "runtime_name": MODULE_RUNTIME_NAME,
            "symbol": CALLSITE_SYMBOL,
            "symbol_value": CALLSITE_SYMBOL_VALUE,
            "runtime_d0_receipt_required": True,
        },
        "offset_probe_rationale": {
            "p300_epilogue_rule_not_generalized": True,
            "p300_rejected_shape": (
                "one epilogue reached by multiple paths with path-dependent "
                "register allocation"
            ),
            "probe_site": "instruction immediately after one named BL",
            "value_source": "AArch64 integer return register w0",
            "next_instruction_consumes_w0": True,
            "path_dependent_epilogue_registers": False,
            "a_b_offset_identity": (
                "the runtime module is one fixed FYG8 vendor_dlkm object bound "
                "by SHA256 and Build ID; both candidate builds materialize the "
                "same 12 descriptor offsets"
            ),
        },
        "reachability_contract": {
            "phy_init_required": "entered, returned, and rc zero",
            "all_callsite_hits_zero": (
                "clock activation block not executed; no clock return conclusion"
            ),
            "hit_zero_is_not_rc_zero": True,
        },
        "callsites": [
            {
                "name": name,
                "branch": branch,
                "clock": clock,
                "call": call,
                "offset": offset,
                "consumer": consumer,
            }
            for name, branch, clock, call, offset, consumer in CALLSITES
        ],
        "contradictions": {
            f"0x{detail:x}": name
            for detail, name in sorted(CONTRADICTION_DETAIL_NAMES.items())
        },
    }


def descriptor_sha256() -> str:
    return hashlib.sha256(_canonical(descriptor())).hexdigest()


def validate() -> Mapping[str, Any]:
    clock_values = {
        encode_clock(branch, ref_src, ref)
        for branch in ("eud", "normal")
        for ref_src in range(CLOCK_RESULT_STATES)
        for ref in range(CLOCK_RESULT_STATES)
    }
    clock_values.add(encode_clock_missed())
    log_values = {
        LOG_DETAIL_BASE + index for index in range(LOG_VALUE_COUNT)
    }
    required_clock_rules = {
        (CLOCK_ORDINAL, OUTCOME_PROGRESS, detail) for detail in clock_values
    }
    if (
        CALLSITE_COUNT != 12
        or len({row[0] for row in CALLSITES}) != CALLSITE_COUNT
        or len({row[4] for row in CALLSITES}) != CALLSITE_COUNT
        or len(clock_values) != 163
        or min(clock_values) != 0xD00
        or max(clock_values) != 0xDA2
        or len(log_values) != 2048
        or min(log_values) != 0x4001
        or max(log_values) != 0x4800
        or not clock_values <= set(range(0xD00, 0xDB0))
        or not log_values <= set(range(0x4001, 0x5000))
        or not required_clock_rules <= set(exact_detail_rules())
        or set(CONTRADICTION_DETAIL_NAMES) != set(range(0x6001, 0x6010))
    ):
        raise ValueError("P3.03 telemetry contract differs")
    return {
        "schema": SCHEMA,
        "descriptor_sha256": descriptor_sha256(),
        "callsite_count": CALLSITE_COUNT,
        "clock_value_count": len(clock_values),
        "log_value_count": len(log_values),
        "contradiction_value_count": len(CONTRADICTION_DETAIL_NAMES),
        "verified": True,
    }


validate()


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
