#!/usr/bin/env python3
"""Pure P2.48 E2 stage and failure-detail contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import s22plus_fyg8_p232_e1_latest_stage_design as model
import s22plus_fyg8_p244_e2_provider_sources as p244


SCHEMA = "s22plus_fyg8_p248_contract_spec_v1"
PROFILE = "E2"

KIND_LOCAL = "local"
KIND_MODULE = "module"
KIND_GATE = "gate"
KIND_TERMINAL = "terminal"

DETAIL_ERRNO_MIN = 0x001
DETAIL_ERRNO_MAX = 0x7FF
DETAIL_REGRESSION_BASE = 0x800
DETAIL_REGRESSION_MAX = 0x8FF
DETAIL_READ_ERROR_BASE = 0x900
DETAIL_READ_ERROR_MAX = 0x9FF
DETAIL_RESERVED_MIN = 0xA00
DETAIL_MAX = 0xFFF


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class Step:
    stage: int
    item_index: int
    kind: str
    gate_index: int | None = None


def _build_steps(
    *,
    local_stages: Iterable[int] = model.E1_LOCAL_SEQUENCE,
    module_stages: Iterable[int] = range(
        p244.MODULE_STAGE_FIRST, p244.MODULE_STAGE_LAST + 1
    ),
    gate_stages: Iterable[int] = range(
        p244.GATE_STAGE_FIRST, p244.GATE_STAGE_LAST + 1
    ),
    terminal_stage: int = p244.SUCCESS_STAGE,
) -> tuple[Step, ...]:
    local = tuple(
        Step(stage=stage, item_index=0, kind=KIND_LOCAL)
        for stage in local_stages
    )
    modules = tuple(
        Step(stage=stage, item_index=index, kind=KIND_MODULE)
        for index, stage in enumerate(module_stages)
    )
    gates = tuple(
        Step(
            stage=stage,
            item_index=index,
            kind=KIND_GATE,
            gate_index=index,
        )
        for index, stage in enumerate(gate_stages)
    )
    return local + modules + gates + (
        Step(stage=terminal_stage, item_index=0, kind=KIND_TERMINAL),
    )


STEPS = _build_steps()
STAGE_SEQUENCE = tuple(step.stage for step in STEPS)
TERMINAL_STAGE = STEPS[-1].stage
MODULE_START_ORDINAL = next(
    index for index, step in enumerate(STEPS) if step.kind == KIND_MODULE
)
GATE_START_ORDINAL = next(
    index for index, step in enumerate(STEPS) if step.kind == KIND_GATE
)
TERMINAL_ORDINAL = len(STEPS) - 1
GATE_COUNT = sum(step.kind == KIND_GATE for step in STEPS)


def validate_steps(steps: tuple[Step, ...]) -> None:
    if not steps:
        raise SpecError("P2.48 step sequence is empty")
    if len(steps) > 0xFF:
        raise SpecError("P2.48 generation no longer fits one byte")
    if len({step.stage for step in steps}) != len(steps):
        raise SpecError("P2.48 stage values are not unique")
    if steps[-1].kind != KIND_TERMINAL or steps[-1].item_index != 0:
        raise SpecError("P2.48 terminal descriptor is invalid")
    gates = tuple(step for step in steps if step.kind == KIND_GATE)
    if len(gates) > 0x100:
        raise SpecError("P2.48 gate index no longer fits detail low byte")
    if tuple(step.gate_index for step in gates) != tuple(range(len(gates))):
        raise SpecError("P2.48 gate indices are not contiguous")
    for step in steps:
        if not 0 <= step.stage <= 0xFF or not 0 <= step.item_index <= 0xFF:
            raise SpecError("P2.48 stage or item does not fit one byte")
        if step.kind not in {
            KIND_LOCAL,
            KIND_MODULE,
            KIND_GATE,
            KIND_TERMINAL,
        }:
            raise SpecError(f"P2.48 unknown step kind: {step.kind}")
        if step.kind != KIND_GATE and step.gate_index is not None:
            raise SpecError("P2.48 non-gate step has a gate index")


validate_steps(STEPS)


def step_for_stage(stage: int, steps: tuple[Step, ...] = STEPS) -> Step:
    for step in steps:
        if step.stage == stage:
            return step
    raise SpecError(f"stage 0x{stage:02x} is outside the P2.48 contract")


def ordinal_for_stage(stage: int, steps: tuple[Step, ...] = STEPS) -> int:
    for ordinal, step in enumerate(steps):
        if step.stage == stage:
            return ordinal
    raise SpecError(f"stage 0x{stage:02x} is outside the P2.48 contract")


def expected_item(stage: int, steps: tuple[Step, ...] = STEPS) -> int:
    return step_for_stage(stage, steps).item_index


def regression_detail(gate_index: int) -> int:
    if not 0 <= gate_index <= 0xFF:
        raise SpecError("regression gate index is outside one byte")
    return DETAIL_REGRESSION_BASE + gate_index


def read_error_detail(gate_index: int) -> int:
    if not 0 <= gate_index <= 0xFF:
        raise SpecError("read-error gate index is outside one byte")
    return DETAIL_READ_ERROR_BASE + gate_index


def detail_kind(detail: int) -> str:
    if DETAIL_ERRNO_MIN <= detail <= DETAIL_ERRNO_MAX:
        return "errno"
    if DETAIL_REGRESSION_BASE <= detail <= DETAIL_REGRESSION_MAX:
        return "regression"
    if DETAIL_READ_ERROR_BASE <= detail <= DETAIL_READ_ERROR_MAX:
        return "read-error"
    if DETAIL_RESERVED_MIN <= detail <= DETAIL_MAX:
        return "reserved"
    return "invalid"


def failure_detail_allowed(
    step: Step,
    detail: int,
    *,
    gate_count: int = GATE_COUNT,
) -> bool:
    kind = detail_kind(detail)
    if kind == "errno":
        return True
    if step.kind != KIND_GATE or step.gate_index is None:
        return False
    encoded_index = detail & 0xFF
    if encoded_index >= gate_count:
        return False
    if kind == "regression":
        return encoded_index < step.gate_index
    if kind == "read-error":
        return encoded_index <= step.gate_index
    return False


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
    steps: tuple[Step, ...] = STEPS,
) -> None:
    validate_steps(steps)
    ordinal = ordinal_for_stage(stage, steps)
    step = steps[ordinal]
    if generation != ordinal + 1:
        raise SpecError("slot generation does not match the stage ordinal")
    if item_index != step.item_index:
        raise SpecError("slot item index does not match the descriptor")
    if step.kind == KIND_TERMINAL:
        if outcome != model.OUTCOME_SUCCESS or detail != 0:
            raise SpecError("terminal slot must be zero-detail success")
        return
    if outcome == model.OUTCOME_PROGRESS and detail == 0:
        return
    gate_count = sum(candidate.kind == KIND_GATE for candidate in steps)
    if (
        outcome != model.OUTCOME_FAILURE
        or not failure_detail_allowed(step, detail, gate_count=gate_count)
    ):
        raise SpecError("nonterminal outcome or detail is outside the contract")


def failure_details(
    step: Step,
    *,
    gate_count: int = GATE_COUNT,
) -> tuple[int, ...]:
    values = list(range(DETAIL_ERRNO_MIN, DETAIL_ERRNO_MAX + 1))
    if step.kind == KIND_GATE and step.gate_index is not None:
        values.extend(
            regression_detail(index) for index in range(step.gate_index)
        )
        values.extend(
            read_error_detail(index) for index in range(step.gate_index + 1)
        )
    result = tuple(values)
    if any(
        not failure_detail_allowed(step, value, gate_count=gate_count)
        for value in result
    ):
        raise SpecError("generated P2.48 detail domain is invalid")
    return result


def build_mutated_steps(
    stage: int,
    *,
    before_terminal: bool = True,
) -> tuple[Step, ...]:
    if not before_terminal:
        raise SpecError("synthetic P2.48 steps must remain nonterminal")
    if stage in STAGE_SEQUENCE:
        raise SpecError("synthetic stage collides with the base sequence")
    last_gate = max(
        step.gate_index
        for step in STEPS
        if step.kind == KIND_GATE and step.gate_index is not None
    )
    mutated = STEPS[:-1] + (
        Step(
            stage=stage,
            item_index=last_gate + 1,
            kind=KIND_GATE,
            gate_index=last_gate + 1,
        ),
        STEPS[-1],
    )
    validate_steps(mutated)
    return mutated
