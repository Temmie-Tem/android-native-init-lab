#!/usr/bin/env python3
"""P2.88 pair-indexed attributable checkpoint position contract."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from s22plus_fyg8_p286_contract_spec import *  # noqa: F403
import s22plus_fyg8_p260_contract_spec as p260
import s22plus_fyg8_p286_contract_spec as p286


SCHEMA = "s22plus_fyg8_p288_contract_spec_v1"


@dataclass(frozen=True)
class Position:
    name: str
    stage: int
    item_index: int
    kind: str
    gate_index: int | None = None

    @property
    def pair(self) -> tuple[int, int]:
        return self.stage, self.item_index


P286_PREFIX_GENERATIONS = 88
LOCAL_DIAGNOSTIC_START_ORDINAL = 80
PREFIX_POSITIONS = tuple(
    Position(
        name=f"inherited_generation_{generation:03d}",
        stage=step.stage,
        item_index=step.item_index,
        kind=step.kind,
        gate_index=step.gate_index,
    )
    for generation, step in enumerate(
        p286.STEPS[:P286_PREFIX_GENERATIONS], 1
    )
)
SUCCESSOR_POSITIONS = (
    Position("restart_helper_dispatch", RESTART_STAGE, 0, KIND_LOCAL),  # noqa: F405
    Position("restart_helper_returned", RESTART_STAGE, 1, KIND_LOCAL),  # noqa: F405
    Position("restart_child_active", RESTART_STAGE, 2, KIND_LOCAL),  # noqa: F405
    Position("restart_parent_peripheral", RESTART_STAGE, 3, KIND_LOCAL),  # noqa: F405
    Position("restart_exact_udc", RESTART_STAGE, 4, KIND_LOCAL),  # noqa: F405
    Position("restart_refresh_returned", RESTART_STAGE, 5, KIND_LOCAL),  # noqa: F405
    Position("restart_capture_returned", RESTART_STAGE, 6, KIND_LOCAL),  # noqa: F405
    Position("restart_classified", RESTART_STAGE, 7, KIND_LOCAL),  # noqa: F405
    Position("bind_cycle_cleanup_returned", BIND_STAGE, 0, KIND_LOCAL),  # noqa: F405
    Position("bind_trace_setup_returned", BIND_STAGE, 1, KIND_LOCAL),  # noqa: F405
    Position("bind_udc_returned", BIND_STAGE, 2, KIND_LOCAL),  # noqa: F405
    Position("bind_trace_classified", BIND_STAGE, 3, KIND_LOCAL),  # noqa: F405
    Position("final_sampling_started", FINAL_STAGE, 0, KIND_LOCAL),  # noqa: F405
    Position("final_result_classified", FINAL_STAGE, 1, KIND_LOCAL),  # noqa: F405
    Position("terminal", TERMINAL_STAGE, 0, KIND_TERMINAL),  # noqa: F405
)
POSITIONS = PREFIX_POSITIONS + SUCCESSOR_POSITIONS
POSITION_SEQUENCE = tuple(position.pair for position in POSITIONS)
POSITION_NAMES = tuple(position.name for position in POSITIONS)
POSITION_BY_PAIR = {
    position.pair: position for position in POSITIONS
}
GENERATION_BY_PAIR = {
    position.pair: generation
    for generation, position in enumerate(POSITIONS, 1)
}
STEPS = tuple(
    p286.Step(
        stage=position.stage,
        item_index=position.item_index,
        kind=position.kind,
        gate_index=position.gate_index,
    )
    for position in POSITIONS
)
STAGE_SEQUENCE = tuple(position.stage for position in POSITIONS)
TERMINAL_ORDINAL = len(POSITIONS) - 1
TERMINAL_GENERATION = len(POSITIONS)
TERMINAL_POSITION = POSITIONS[-1].pair

PERIPHERAL_HELPER_TIMEOUT_DETAIL = 0xC5D
UNCLASSIFIED_DETAIL = 0xC5E
RETIRED_DETAIL_VALUES = frozenset((0xC57, 0xC58, 0xC59, 0xC5C))


def _p288_details():
    return (
        p286.p284.DiagnosticDetail(
            PERIPHERAL_HELPER_TIMEOUT_DETAIL,
            "peripheral-helper-timeout",
            "helper-boundary",
            (OUTCOME_FAILURE,),  # noqa: F405
            (RESTART_STAGE,),  # noqa: F405
        ),
        p286.p284.DiagnosticDetail(
            UNCLASSIFIED_DETAIL,
            "unclassified-runtime-state",
            "fail-closed-unclassified",
            (OUTCOME_FAILURE,),  # noqa: F405
            tuple(sorted(set(STAGE_SEQUENCE))),
        ),
    )


P288_DIAGNOSTIC_DETAILS = _p288_details()
DIAGNOSTIC_DETAILS = tuple(
    detail
    for detail in p286.DIAGNOSTIC_DETAILS
    if detail.value not in RETIRED_DETAIL_VALUES
) + P288_DIAGNOSTIC_DETAILS
EXACT_DETAIL_CANDIDATES = tuple(
    {
        detail.value: detail
        for detail in (
            *p286.CLASSIFIER_DETAILS,
            *p286.ALL_DIAGNOSTIC_DETAILS,
            *P288_DIAGNOSTIC_DETAILS,
        )
        if detail.value not in RETIRED_DETAIL_VALUES
    }.values()
)
EXACT_DIAGNOSTIC_DETAILS = EXACT_DETAIL_CANDIDATES
ALL_DIAGNOSTIC_DETAILS = EXACT_DETAIL_CANDIDATES
DETAIL_BY_VALUE = {
    detail.value: detail for detail in EXACT_DETAIL_CANDIDATES
}
DETAIL_VALUES = tuple(detail.value for detail in EXACT_DETAIL_CANDIDATES)


def position_for_generation(generation: int) -> Position:
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or not 1 <= generation <= len(POSITIONS)
    ):
        raise SpecError("P2.88 generation is outside its position sequence")  # noqa: F405
    return POSITIONS[generation - 1]


@lru_cache(maxsize=None)
def generation_for_position(stage: int, item_index: int) -> int:
    try:
        return GENERATION_BY_PAIR[(stage, item_index)]
    except KeyError as exc:
        raise SpecError(  # noqa: F405
            f"position (0x{stage:02x},{item_index}) is outside P2.88"
        ) from exc


def ordinal_for_position(stage: int, item_index: int) -> int:
    return generation_for_position(stage, item_index) - 1


def step_for_position(stage: int, item_index: int):  # noqa: ANN201
    return STEPS[ordinal_for_position(stage, item_index)]


def ordinal_for_stage(stage: int) -> int:
    matches = tuple(
        index for index, position in enumerate(POSITIONS)
        if position.stage == stage
    )
    if len(matches) != 1:
        raise SpecError(  # noqa: F405
            f"stage-only lookup for 0x{stage:02x} is ambiguous in P2.88"
        )
    return matches[0]


def expected_item(stage: int) -> int:
    return POSITIONS[ordinal_for_stage(stage)].item_index


def detail_name(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    return detail.name if detail is not None else p286.detail_name(value)


def detail_kind(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    return detail.category if detail is not None else p286.detail_kind(value)


def detail_outcomes(detail) -> tuple[int, ...]:  # noqa: ANN001
    outcomes = getattr(detail, "outcomes", None)
    return (
        tuple(outcomes)
        if outcomes is not None
        else (OUTCOME_FAILURE,)  # noqa: F405
    )


_RESTART_DETAIL_ITEMS = {
    0xC01: (5,),
    0xC02: (5,),
    0xC03: (5,),
    0xC04: (),
    0xC05: (1, 6, 7),
    0xC06: (1,),
    0xC20: (7,),
    0xC21: (7,),
    0xC22: (7,),
    0xC23: (7,),
    0xC24: (7,),
    0xC25: (7,),
    0xC26: (7,),
    0xC27: (7,),
    0xC28: (7,),
    0xC29: (7,),
    0xC2A: (7,),
    0xC2B: (7,),
    0xC2C: (2, 7),
    0xC2D: (7,),
    0xC2E: (4, 7),
    0xC2F: (7,),
    0xC30: (7,),
    0xC52: (1,),
    0xC53: (1,),
    0xC54: (1,),
    0xC5A: (1,),
    0xC5B: (3,),
    PERIPHERAL_HELPER_TIMEOUT_DETAIL: (1,),
}
_BIND_DETAIL_ITEMS = {
    **{value: (3,) for value in range(0xC40, 0xC4B)},
    0xC04: (0,),
    0xC4A: (1, 3),
}
_FINAL_DETAIL_ITEMS = {0xC4B: (1,)}


@lru_cache(maxsize=None)
def _successor_exact_positions(
    value: int,
) -> tuple[tuple[int, int], ...]:
    if value == UNCLASSIFIED_DETAIL:
        return POSITION_SEQUENCE
    if value == 0xC04:
        return ((BIND_STAGE, 0),)  # noqa: F405
    detail = DETAIL_BY_VALUE.get(value)
    if detail is None or not hasattr(detail, "stages"):
        return ()
    result: list[tuple[int, int]] = []
    for stage in detail.stages:
        if stage == RESTART_STAGE:  # noqa: F405
            items = _RESTART_DETAIL_ITEMS.get(value, ())
        elif stage == BIND_STAGE:  # noqa: F405
            items = _BIND_DETAIL_ITEMS.get(value, ())
        elif stage == FINAL_STAGE:  # noqa: F405
            items = _FINAL_DETAIL_ITEMS.get(value, ())
        else:
            items = tuple(
                position.item_index
                for position in POSITIONS
                if position.stage == stage
            )
        result.extend((stage, item) for item in items)
    return tuple(result)


@lru_cache(maxsize=None)
def _position_exact_allowed(
    stage: int,
    item_index: int,
    outcome: int,
    value: int,
) -> bool:
    if value in RETIRED_DETAIL_VALUES:
        return False
    try:
        generation = generation_for_position(stage, item_index)
    except SpecError:  # noqa: F405
        return False
    if value == UNCLASSIFIED_DETAIL:
        return outcome == OUTCOME_FAILURE  # noqa: F405
    if generation <= P286_PREFIX_GENERATIONS:
        try:
            p286.validate_slot(
                generation=generation,
                stage=stage,
                outcome=outcome,
                item_index=item_index,
                detail=value,
            )
        except p286.SpecError:
            return False
        return value in DETAIL_BY_VALUE
    detail = DETAIL_BY_VALUE.get(value)
    return (
        detail is not None
        and outcome in detail_outcomes(detail)
        and (stage, item_index) in _successor_exact_positions(value)
    )


@lru_cache(maxsize=None)
def detail_positions(value: int) -> tuple[tuple[int, int], ...]:
    detail = DETAIL_BY_VALUE.get(value)
    if detail is None:
        return ()
    outcomes = detail_outcomes(detail)
    return tuple(
        position.pair
        for position in POSITIONS
        if any(
            _position_exact_allowed(
                position.stage,
                position.item_index,
                outcome,
                value,
            )
            for outcome in outcomes
        )
    )


def position_detail_allowed(
    stage: int,
    item_index: int,
    outcome: int,
    value: int,
) -> bool:
    if TUPLE_FIRST <= value <= TUPLE_LAST:  # noqa: F405
        decoded = decode_tuple(value)  # noqa: F405
        return (
            (stage, item_index) == (FINAL_STAGE, 1)  # noqa: F405
            and outcome == decoded.outcome
        )
    return _position_exact_allowed(
        stage, item_index, outcome, value
    )


def detail_allowed(stage: int, outcome: int, value: int) -> bool:
    pairs = tuple(
        pair for pair in detail_positions(value) if pair[0] == stage
    )
    if len(pairs) > 1:
        raise SpecError(  # noqa: F405
            f"stage-only detail lookup for 0x{stage:02x} is ambiguous"
        )
    return bool(
        pairs
        and position_detail_allowed(
            pairs[0][0], pairs[0][1], outcome, value
        )
    )


@lru_cache(maxsize=None)
def position_failure_details(
    stage: int, item_index: int
) -> tuple[int, ...]:
    step = step_for_position(stage, item_index)
    generation = generation_for_position(stage, item_index)
    if step.kind == KIND_TERMINAL:  # noqa: F405
        inherited: tuple[int, ...] = ()
    elif generation <= P286_PREFIX_GENERATIONS:
        inherited = tuple(
            value
            for value in p286.failure_details(
                p286.STEPS[generation - 1]
            )
            if value not in RETIRED_DETAIL_VALUES
        )
    else:
        inherited = tuple(
            range(p260.DETAIL_ERRNO_MIN, p260.DETAIL_ERRNO_MAX + 1)
        )
        if (
            step.kind == KIND_GATE  # noqa: F405
            or generation - 1 >= LOCAL_DIAGNOSTIC_START_ORDINAL
        ):
            inherited += tuple(
                p260.regression_detail(index)
                for index in (
                    range(step.item_index)
                    if step.kind == KIND_GATE  # noqa: F405
                    else range(GATE_COUNT)  # noqa: F405
                )
            )
            inherited += tuple(
                p260.read_error_detail(index)
                for index in (
                    range(step.item_index + 1)
                    if step.kind == KIND_GATE  # noqa: F405
                    else range(GATE_COUNT)  # noqa: F405
                )
            )
    exact = tuple(
        detail.value
        for detail in EXACT_DIAGNOSTIC_DETAILS
        if position_detail_allowed(
            stage,
            item_index,
            OUTCOME_FAILURE,  # noqa: F405
            detail.value,
        )
    )
    tuples = (
        tuple(
            value
            for value in range(TUPLE_FIRST, TUPLE_LAST + 1)  # noqa: F405
            if position_detail_allowed(
                stage,
                item_index,
                OUTCOME_FAILURE,  # noqa: F405
                value,
            )
        )
        if (stage, item_index) == (FINAL_STAGE, 1)  # noqa: F405
        else ()
    )
    return tuple(dict.fromkeys((*inherited, *exact, *tuples)))


@lru_cache(maxsize=None)
def position_progress_details(
    stage: int, item_index: int
) -> tuple[int, ...]:
    exact = tuple(
        detail.value
        for detail in EXACT_DIAGNOSTIC_DETAILS
        if position_detail_allowed(
            stage,
            item_index,
            OUTCOME_PROGRESS,  # noqa: F405
            detail.value,
        )
    )
    tuples = (
        tuple(
            value
            for value in range(TUPLE_FIRST, TUPLE_LAST + 1)  # noqa: F405
            if position_detail_allowed(
                stage,
                item_index,
                OUTCOME_PROGRESS,  # noqa: F405
                value,
            )
        )
        if (stage, item_index) == (FINAL_STAGE, 1)  # noqa: F405
        else ()
    )
    return tuple(dict.fromkeys((0, *exact, *tuples)))


def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    rules: list[tuple[int, int, int]] = []
    for generation, position in enumerate(POSITIONS, 1):
        for detail in EXACT_DIAGNOSTIC_DETAILS:
            for outcome in detail_outcomes(detail):
                if position_detail_allowed(
                    position.stage,
                    position.item_index,
                    outcome,
                    detail.value,
                ):
                    rules.append((generation - 1, outcome, detail.value))
    return tuple(rules)


def failure_details(step):  # noqa: ANN001, ANN201
    return position_failure_details(step.stage, step.item_index)


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
        raise SpecError(  # noqa: F405
            "slot generation does not match the P2.88 position pair"
        )
    if position.kind == KIND_TERMINAL:  # noqa: F405
        if outcome == OUTCOME_SUCCESS and detail == 0:  # noqa: F405
            return
        if position_detail_allowed(
            stage, item_index, outcome, detail
        ):
            return
        raise SpecError("P2.88 terminal slot is outside its contract")  # noqa: F405
    if outcome == OUTCOME_PROGRESS and detail == 0:  # noqa: F405
        return
    if (
        outcome == OUTCOME_FAILURE  # noqa: F405
        and detail in position_failure_details(stage, item_index)
    ):
        return
    if position_detail_allowed(stage, item_index, outcome, detail):
        return
    raise SpecError("slot outcome or detail is outside P2.88")  # noqa: F405


def validate_positions() -> None:
    if len(POSITIONS) != 103 or TERMINAL_GENERATION != 103:
        raise SpecError("P2.88 terminal position must be generation 103")  # noqa: F405
    if len(POSITIONS) > 0xFF:
        raise SpecError("P2.88 position sequence does not fit generation")  # noqa: F405
    if len(POSITION_BY_PAIR) != len(POSITIONS):
        raise SpecError("P2.88 position pairs are not unique")  # noqa: F405
    if POSITION_SEQUENCE[:P286_PREFIX_GENERATIONS] != tuple(
        (step.stage, step.item_index)
        for step in p286.STEPS[:P286_PREFIX_GENERATIONS]
    ):
        raise SpecError("P2.88 changed the proven P2.86 prefix")  # noqa: F405
    if LOCAL_DIAGNOSTIC_START_ORDINAL != len(p260.P258_PREFIX_STEPS):
        raise SpecError("P2.88 local diagnostic start ordinal drifted")  # noqa: F405
    if (
        POSITIONS[LOCAL_DIAGNOSTIC_START_ORDINAL].kind != KIND_LOCAL  # noqa: F405
        or POSITIONS[LOCAL_DIAGNOSTIC_START_ORDINAL - 1].kind
        != KIND_GATE  # noqa: F405
    ):
        raise SpecError("P2.88 local diagnostic boundary is not exact")  # noqa: F405
    if POSITIONS[-1].kind != KIND_TERMINAL:  # noqa: F405
        raise SpecError("P2.88 terminal position is not terminal")  # noqa: F405
    for stage in (RESTART_STAGE, BIND_STAGE, FINAL_STAGE):  # noqa: F405
        items = tuple(
            position.item_index
            for position in POSITIONS
            if position.stage == stage
        )
        if items != tuple(range(len(items))):
            raise SpecError(
                f"P2.88 stage 0x{stage:02x} item sequence is not contiguous"
            )
    if RETIRED_DETAIL_VALUES & set(DETAIL_VALUES):
        raise SpecError("P2.88 retained a retired exact detail")  # noqa: F405
    if set(detail_positions(UNCLASSIFIED_DETAIL)) != set(
        POSITION_SEQUENCE
    ):
        raise SpecError("P2.88 unclassified route is not position-complete")  # noqa: F405


def validate() -> None:
    p286.validate()
    validate_positions()
    if len(DETAIL_BY_VALUE) != len(EXACT_DIAGNOSTIC_DETAILS):
        raise SpecError("P2.88 exact diagnostic values are not unique")  # noqa: F405
    for detail in EXACT_DIAGNOSTIC_DETAILS:
        if not detail_positions(detail.value):
            raise SpecError(
                f"P2.88 detail 0x{detail.value:03x} has no position"
            )


EXACT_DIAGNOSTIC_DETAILS = tuple(
    detail
    for detail in EXACT_DETAIL_CANDIDATES
    if detail_positions(detail.value)
)
ALL_DIAGNOSTIC_DETAILS = EXACT_DIAGNOSTIC_DETAILS
DETAIL_BY_VALUE = {
    detail.value: detail for detail in EXACT_DIAGNOSTIC_DETAILS
}
DETAIL_VALUES = tuple(detail.value for detail in EXACT_DIAGNOSTIC_DETAILS)


validate()
