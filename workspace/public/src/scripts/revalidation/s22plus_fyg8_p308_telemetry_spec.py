#!/usr/bin/env python3
"""P3.08 loss-resistant EUD, clock, and QSCRATCH telemetry contract."""

from __future__ import annotations

from functools import lru_cache
from itertools import product
from typing import Any

import s22plus_fyg8_p301_telemetry_spec as p301
import s22plus_fyg8_p303_telemetry_spec as p303
import s22plus_fyg8_p307_telemetry_spec as p307


SCHEMA = "s22plus_fyg8_p308_loss_resistant_telemetry_spec_v1"
PROFILE = p307.PROFILE
ATTR_ORDINAL = p307.ATTR_ORDINAL
SUMMARY_ORDINAL = p307.SUMMARY_ORDINAL
OUTCOME_PROGRESS = p307.OUTCOME_PROGRESS
OUTCOME_FAILURE = p307.OUTCOME_FAILURE

POSITION_SEQUENCE = p301.POSITION_SEQUENCE
POSITIONS = p301.POSITIONS
TERMINAL_POSITION = p301.TERMINAL_POSITION
TERMINAL_STAGE = p301.TERMINAL_STAGE
position_for_generation = p301.position_for_generation
SpecError = p301.SpecError

ATTR_DETAIL_BASE = p307.ATTR_DETAIL_BASE
ATTR_DETAIL_MAX = p307.ATTR_DETAIL_MAX
CLOCK_DETAIL_BASE = p303.CLOCK_DETAIL_BASE
CLOCK_DETAIL_MAX = p303.CLOCK_DETAIL_MAX
SUMMARY_DETAIL_BASE = p307.SUMMARY_DETAIL_BASE
SUMMARY_DETAIL_MAX = p307.SUMMARY_DETAIL_MAX
QSCRATCH_STATE_COUNT = p307.QSCRATCH_STATE_COUNT

PREFIX_INIT = 1 << 0
PREFIX_CSR = 1 << 1
PREFIX_DPDM = 1 << 2
PREFIX_CLOCK = 1 << 3
PREFIX_MASK_MAX = 0xF
PREFIX_NAMES = {
    PREFIX_INIT: "init-phy-flags",
    PREFIX_CSR: "csr",
    PREFIX_DPDM: "dpdm-enable",
    PREFIX_CLOCK: "clocks-enabled",
}

FAILURE_SITE_LINE = 0
FAILURE_SITE_CSR = 1
FAILURE_SITE_DPDM = 2
FAILURE_SITE_CLOCK = 3
FAILURE_SITE_COUNT = 4
FAILURE_SITE_NAMES = {
    FAILURE_SITE_LINE: "record-line-or-multiple-domain",
    FAILURE_SITE_CSR: "csr-signature-or-order",
    FAILURE_SITE_DPDM: "dpdm-binary-value",
    FAILURE_SITE_CLOCK: "clock-binary-pair",
}

DEGRADED_DETAIL_BASE = 0x6100
DEGRADED_WITNESS_COUNT = FAILURE_SITE_COUNT * (PREFIX_MASK_MAX + 1)
DEGRADED_VALUE_COUNT = DEGRADED_WITNESS_COUNT * QSCRATCH_STATE_COUNT
DEGRADED_DETAIL_MAX = DEGRADED_DETAIL_BASE + DEGRADED_VALUE_COUNT - 1


@lru_cache(maxsize=1)
def attribution_outputs() -> tuple[int, ...]:
    return tuple(sorted({
        p307.encode_attribution(
            cache_value=cache,
            init_state=init,
            dpdm_state=dpdm,
            preclock_state=preclock,
        )
        for cache, init, dpdm, preclock in product(
            range(p307.ATTR_CACHE_STATES),
            range(p307.ATTR_INIT_STATES),
            range(p307.ATTR_DPDM_STATES),
            range(p307.ATTR_PRECLOCK_STATES),
        )
    }))


@lru_cache(maxsize=1)
def clock_outputs() -> tuple[int, ...]:
    values = {p303.encode_clock_missed()}
    for branch, ref_src, ref in product(
        ("eud", "normal"),
        range(p303.CLOCK_RESULT_STATES),
        range(p303.CLOCK_RESULT_STATES),
    ):
        values.add(p303.encode_clock(branch, ref_src, ref))
    return tuple(sorted(values))


@lru_cache(maxsize=1)
def summary_outputs() -> tuple[int, ...]:
    return tuple(sorted({
        p307.encode_summary(clock_detail=clock, qscratch_state=qscratch)
        for clock, qscratch in product(
            clock_outputs(), range(QSCRATCH_STATE_COUNT)
        )
    }))


def encode_degraded(
    *, failure_site: int, prefix_mask: int, qscratch_state: int
) -> int:
    if not 0 <= failure_site < FAILURE_SITE_COUNT:
        raise ValueError("P3.08 parser failure site differs")
    if not 0 <= prefix_mask <= PREFIX_MASK_MAX:
        raise ValueError("P3.08 parser prefix mask differs")
    if not 0 <= qscratch_state < QSCRATCH_STATE_COUNT:
        raise ValueError("P3.08 QSCRATCH state differs")
    witness = failure_site * (PREFIX_MASK_MAX + 1) + prefix_mask
    return DEGRADED_DETAIL_BASE + witness * QSCRATCH_STATE_COUNT + qscratch_state


def decode_degraded(detail: int) -> dict[str, Any]:
    index = detail - DEGRADED_DETAIL_BASE
    if not 0 <= index < DEGRADED_VALUE_COUNT:
        raise ValueError("P3.08 detail is not a degraded result")
    witness, qscratch_state = divmod(index, QSCRATCH_STATE_COUNT)
    failure_site, prefix_mask = divmod(witness, PREFIX_MASK_MAX + 1)
    return {
        "failure_site": failure_site,
        "failure_site_name": FAILURE_SITE_NAMES[failure_site],
        "prefix_mask": prefix_mask,
        "prefixes_seen": tuple(
            name for bit, name in PREFIX_NAMES.items() if prefix_mask & bit
        ),
        "qscratch_state": qscratch_state,
        "qscratch": p307.decode_qscratch(qscratch_state),
    }


@lru_cache(maxsize=1)
def degraded_outputs() -> tuple[int, ...]:
    return tuple(sorted({
        encode_degraded(
            failure_site=site,
            prefix_mask=mask,
            qscratch_state=qscratch,
        )
        for site, mask, qscratch in product(
            range(FAILURE_SITE_COUNT),
            range(PREFIX_MASK_MAX + 1),
            range(QSCRATCH_STATE_COUNT),
        )
    }))


def is_terminal_detail(detail: int) -> bool:
    return (
        p301.is_terminal_detail(detail)
        or SUMMARY_DETAIL_BASE <= detail <= SUMMARY_DETAIL_MAX
        or DEGRADED_DETAIL_BASE <= detail <= DEGRADED_DETAIL_MAX
    )


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    position = position_for_generation(generation)
    if (stage, item_index) != position.pair:
        raise SpecError("slot generation does not match the P3.08 position pair")
    ordinal = generation - 1
    if ordinal == SUMMARY_ORDINAL:
        if outcome != OUTCOME_FAILURE or not is_terminal_detail(detail):
            raise SpecError("P3.08 B must be a declared terminal failure detail")
        return
    p301.validate_slot(
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
    )


def validate() -> dict[str, Any]:
    attr = attribution_outputs()
    clocks = clock_outputs()
    summaries = summary_outputs()
    degraded = degraded_outputs()
    fixed_rules = set(p303.exact_detail_rules())
    if (
        len(attr) != 150
        or attr[0] != 0xD00
        or attr[-1] != 0xD95
        or len(clocks) != 163
        or clocks[0] != 0xD00
        or clocks[-1] != 0xDA2
        or len(summaries) != 4075
        or summaries[0] != 0x4001
        or summaries[-1] != 0x4FEB
        or len(degraded) != 1600
        or degraded[0] != 0x6100
        or degraded[-1] != 0x673F
        or not {
            (ATTR_ORDINAL, OUTCOME_PROGRESS, value) for value in attr
        }.issubset(fixed_rules)
        or not {
            (ATTR_ORDINAL, OUTCOME_PROGRESS, value) for value in clocks
        }.issubset(fixed_rules)
    ):
        raise ValueError("P3.08 encoder output contract differs")
    return {
        "schema": SCHEMA,
        "profile": PROFILE,
        "attribution_output_count": len(attr),
        "clock_output_count": len(clocks),
        "summary_output_count": len(summaries),
        "degraded_output_count": len(degraded),
        "enumerated_family_value_count": (
            len(attr) + len(clocks) + len(summaries) + len(degraded)
        ),
        "summary_detail_range": [SUMMARY_DETAIL_BASE, SUMMARY_DETAIL_MAX],
        "degraded_detail_range": [DEGRADED_DETAIL_BASE, DEGRADED_DETAIL_MAX],
        "fixed_image_exact_a_rules": True,
        "verified": True,
    }


def __getattr__(name: str):
    """Retain the unchanged P3.01 position/record ABI for the P3.08 model."""
    return getattr(p301, name)
