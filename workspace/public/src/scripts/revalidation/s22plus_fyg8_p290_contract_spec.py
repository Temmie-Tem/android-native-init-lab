#!/usr/bin/env python3
"""P2.90 positions: adjacent 0x8f corridor plus the P2.88 suffix."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from s22plus_fyg8_p288_contract_spec import *  # noqa: F403
import s22plus_fyg8_p288_contract_spec as base


SCHEMA = "s22plus_fyg8_p290_contract_spec_v1"
Position = base.Position
SpecError = base.SpecError
p260 = base.p260
p286 = base.p286

P286_PREFIX_GENERATIONS = base.P286_PREFIX_GENERATIONS
LOCAL_DIAGNOSTIC_START_ORDINAL = base.LOCAL_DIAGNOSTIC_START_ORDINAL
PREFIX_POSITIONS = base.PREFIX_POSITIONS
CORRIDOR_POSITIONS = (
    Position(
        "suspended_publish_returned",
        SUSPENDED_STAGE,  # noqa: F405
        1,
        KIND_LOCAL,  # noqa: F405
    ),
    Position(
        "suspend_function_returned",
        SUSPENDED_STAGE,  # noqa: F405
        2,
        KIND_LOCAL,  # noqa: F405
    ),
    Position(
        "restart_function_entered",
        SUSPENDED_STAGE,  # noqa: F405
        3,
        KIND_LOCAL,  # noqa: F405
    ),
    Position(
        "restart_deadline_ready",
        SUSPENDED_STAGE,  # noqa: F405
        4,
        KIND_LOCAL,  # noqa: F405
    ),
)
SUCCESSOR_POSITIONS = CORRIDOR_POSITIONS + base.SUCCESSOR_POSITIONS
POSITIONS = PREFIX_POSITIONS + SUCCESSOR_POSITIONS
POSITION_SEQUENCE = tuple(position.pair for position in POSITIONS)
POSITION_NAMES = tuple(position.name for position in POSITIONS)
POSITION_BY_PAIR = {position.pair: position for position in POSITIONS}
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

PERIPHERAL_HELPER_TIMEOUT_DETAIL = base.PERIPHERAL_HELPER_TIMEOUT_DETAIL
UNCLASSIFIED_DETAIL = base.UNCLASSIFIED_DETAIL
RETIRED_DETAIL_VALUES = base.RETIRED_DETAIL_VALUES
P288_DIAGNOSTIC_DETAILS = base.P288_DIAGNOSTIC_DETAILS
DIAGNOSTIC_DETAILS = base.DIAGNOSTIC_DETAILS
EXACT_DETAIL_CANDIDATES = base.EXACT_DETAIL_CANDIDATES
EXACT_DIAGNOSTIC_DETAILS = base.EXACT_DIAGNOSTIC_DETAILS
ALL_DIAGNOSTIC_DETAILS = EXACT_DIAGNOSTIC_DETAILS
DETAIL_BY_VALUE = dict(base.DETAIL_BY_VALUE)
DETAIL_VALUES = tuple(base.DETAIL_VALUES)

_CONTEXT_VALUES = {
    "POSITIONS": POSITIONS,
    "POSITION_SEQUENCE": POSITION_SEQUENCE,
    "POSITION_NAMES": POSITION_NAMES,
    "POSITION_BY_PAIR": POSITION_BY_PAIR,
    "GENERATION_BY_PAIR": GENERATION_BY_PAIR,
    "STEPS": STEPS,
    "STAGE_SEQUENCE": STAGE_SEQUENCE,
    "TERMINAL_ORDINAL": TERMINAL_ORDINAL,
    "TERMINAL_GENERATION": TERMINAL_GENERATION,
    "TERMINAL_POSITION": TERMINAL_POSITION,
    "SUCCESSOR_POSITIONS": SUCCESSOR_POSITIONS,
    "EXACT_DIAGNOSTIC_DETAILS": EXACT_DIAGNOSTIC_DETAILS,
    "ALL_DIAGNOSTIC_DETAILS": ALL_DIAGNOSTIC_DETAILS,
    "DETAIL_BY_VALUE": DETAIL_BY_VALUE,
    "DETAIL_VALUES": DETAIL_VALUES,
}
_CACHE_NAMES = (
    "generation_for_position",
    "_successor_exact_positions",
    "_position_exact_allowed",
    "detail_positions",
    "position_failure_details",
    "position_progress_details",
)


def _clear_base_caches() -> None:
    for name in _CACHE_NAMES:
        function = getattr(base, name)
        clear = getattr(function, "cache_clear", None)
        if clear is not None:
            clear()


@contextmanager
def base_context() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _CONTEXT_VALUES}
    _clear_base_caches()
    for name, value in _CONTEXT_VALUES.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)
        _clear_base_caches()


def _call(name: str, *args: Any, **kwargs: Any):
    with base_context():
        return getattr(base, name)(*args, **kwargs)


def position_for_generation(generation: int) -> Position:
    if (
        isinstance(generation, bool)
        or not isinstance(generation, int)
        or not 1 <= generation <= len(POSITIONS)
    ):
        raise SpecError("P2.90 generation is outside its position sequence")
    return POSITIONS[generation - 1]


def generation_for_position(stage: int, item_index: int) -> int:
    try:
        return GENERATION_BY_PAIR[(stage, item_index)]
    except KeyError as exc:
        raise SpecError(
            f"position (0x{stage:02x},{item_index}) is outside P2.90"
        ) from exc


def ordinal_for_position(stage: int, item_index: int) -> int:
    return generation_for_position(stage, item_index) - 1


def step_for_position(stage: int, item_index: int):  # noqa: ANN201
    return STEPS[ordinal_for_position(stage, item_index)]


def ordinal_for_stage(stage: int) -> int:
    matches = tuple(
        index
        for index, position in enumerate(POSITIONS)
        if position.stage == stage
    )
    if len(matches) != 1:
        raise SpecError(
            f"stage-only lookup for 0x{stage:02x} is ambiguous in P2.90"
        )
    return matches[0]


def expected_item(stage: int) -> int:
    return POSITIONS[ordinal_for_stage(stage)].item_index


def detail_name(value: int) -> str:
    return base.detail_name(value)


def detail_kind(value: int) -> str:
    return base.detail_kind(value)


def detail_outcomes(detail) -> tuple[int, ...]:  # noqa: ANN001
    return base.detail_outcomes(detail)


def detail_positions(value: int) -> tuple[tuple[int, int], ...]:
    return _call("detail_positions", value)


def position_detail_allowed(
    stage: int, item_index: int, outcome: int, value: int
) -> bool:
    return _call(
        "position_detail_allowed", stage, item_index, outcome, value
    )


def detail_allowed(stage: int, outcome: int, value: int) -> bool:
    return _call("detail_allowed", stage, outcome, value)


def position_failure_details(
    stage: int, item_index: int
) -> tuple[int, ...]:
    return _call("position_failure_details", stage, item_index)


def position_progress_details(
    stage: int, item_index: int
) -> tuple[int, ...]:
    return _call("position_progress_details", stage, item_index)


def exact_detail_rules() -> tuple[tuple[int, int, int], ...]:
    return _call("exact_detail_rules")


def failure_details(step):  # noqa: ANN001, ANN201
    return position_failure_details(step.stage, step.item_index)


def validate_slot(**kwargs: Any) -> None:
    with base_context():
        base.validate_slot(**kwargs)


def validate_positions() -> None:
    if len(POSITIONS) != 107 or TERMINAL_GENERATION != 107:
        raise SpecError("P2.90 terminal position must be generation 107")
    if len(POSITIONS) > 0xFF:
        raise SpecError("P2.90 position sequence does not fit generation")
    if len(POSITION_BY_PAIR) != len(POSITIONS):
        raise SpecError("P2.90 position pairs are not unique")
    if POSITION_SEQUENCE[:P286_PREFIX_GENERATIONS] != base.POSITION_SEQUENCE[
        :P286_PREFIX_GENERATIONS
    ]:
        raise SpecError("P2.90 changed the live-proven generation-88 prefix")
    if SUCCESSOR_POSITIONS[4:] != base.SUCCESSOR_POSITIONS:
        raise SpecError("P2.90 changed the inherited P2.88 suffix")
    if POSITIONS[-1].kind != KIND_TERMINAL:  # noqa: F405
        raise SpecError("P2.90 terminal position is not terminal")
    for stage in (
        SUSPENDED_STAGE,  # noqa: F405
        RESTART_STAGE,  # noqa: F405
        BIND_STAGE,  # noqa: F405
        FINAL_STAGE,  # noqa: F405
    ):
        items = tuple(
            position.item_index
            for position in POSITIONS
            if position.stage == stage
        )
        if items != tuple(range(len(items))):
            raise SpecError(
                f"P2.90 stage 0x{stage:02x} item sequence is not contiguous"
            )
    if set(detail_positions(UNCLASSIFIED_DETAIL)) != set(
        POSITION_SEQUENCE
    ):
        raise SpecError("P2.90 unclassified route is not position-complete")


def validate() -> None:
    p286.validate()
    validate_positions()
    if len(DETAIL_BY_VALUE) != len(EXACT_DIAGNOSTIC_DETAILS):
        raise SpecError("P2.90 exact diagnostic values are not unique")
    for detail in EXACT_DIAGNOSTIC_DETAILS:
        if not detail_positions(detail.value):
            raise SpecError(
                f"P2.90 detail 0x{detail.value:03x} has no position"
            )


validate()
