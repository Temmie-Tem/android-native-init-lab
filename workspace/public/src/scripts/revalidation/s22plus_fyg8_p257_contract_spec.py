#!/usr/bin/env python3
"""Pure P2.57 display-closure E2 stage and classifier contract."""

from __future__ import annotations

from dataclasses import dataclass

import s22plus_fyg8_p248_contract_spec as p248
import s22plus_fyg8_p252_contract_spec as p252


SCHEMA = "s22plus_fyg8_p257_contract_spec_v1"
PROFILE = p248.PROFILE

Step = p248.Step
SpecError = p248.SpecError
ClassifierDetail = p252.ClassifierDetail

KIND_LOCAL = p248.KIND_LOCAL
KIND_MODULE = p248.KIND_MODULE
KIND_GATE = p248.KIND_GATE
KIND_TERMINAL = p248.KIND_TERMINAL

DETAIL_ERRNO_MIN = p248.DETAIL_ERRNO_MIN
DETAIL_ERRNO_MAX = p248.DETAIL_ERRNO_MAX
DETAIL_REGRESSION_BASE = p248.DETAIL_REGRESSION_BASE
DETAIL_REGRESSION_MAX = p248.DETAIL_REGRESSION_MAX
DETAIL_READ_ERROR_BASE = p248.DETAIL_READ_ERROR_BASE
DETAIL_READ_ERROR_MAX = p248.DETAIL_READ_ERROR_MAX
DETAIL_CLASSIFIER_MIN = p252.DETAIL_CLASSIFIER_MIN
DETAIL_CLASSIFIER_MAX = p252.DETAIL_CLASSIFIER_MAX


@dataclass(frozen=True)
class ModuleInsertion:
    index: int
    file: str
    runtime_name: str
    params: str

    @property
    def row(self) -> tuple[str, str, str]:
        return (self.file, self.runtime_name, self.params)


DISPCC_INSERTION = ModuleInsertion(
    index=33,
    file="dispcc-waipio.ko",
    runtime_name="dispcc_waipio",
    params="",
)
MODULE_INSERTIONS = (DISPCC_INSERTION,)
HISTORICAL_MODULE_PLAN_COUNT = sum(
    step.kind == KIND_MODULE for step in p248.STEPS
)
MODULE_PLAN_COUNT = HISTORICAL_MODULE_PLAN_COUNT + len(MODULE_INSERTIONS)
MODULE_STAGE_FIRST = 0x40
MODULE_STAGE_LAST = MODULE_STAGE_FIRST + MODULE_PLAN_COUNT - 1
GATE_STAGE_FIRST = 0x7C
GATE_STAGE_LAST = 0x87
TERMINAL_STAGE = 0x8F

STEPS = p248.build_steps(
    module_stages=range(MODULE_STAGE_FIRST, MODULE_STAGE_LAST + 1),
    gate_stages=range(GATE_STAGE_FIRST, GATE_STAGE_LAST + 1),
    terminal_stage=TERMINAL_STAGE,
)
STAGE_SEQUENCE = tuple(step.stage for step in STEPS)
MODULE_START_ORDINAL = next(
    index for index, step in enumerate(STEPS) if step.kind == KIND_MODULE
)
GATE_START_ORDINAL = next(
    index for index, step in enumerate(STEPS) if step.kind == KIND_GATE
)
TERMINAL_ORDINAL = len(STEPS) - 1
GATE_COUNT = sum(step.kind == KIND_GATE for step in STEPS)

SSUSB_STAGE = 0x85
SSUSB_GATE_INDEX = 9
WAITING_FOR_SUPPLIER_PATH = p252.WAITING_FOR_SUPPLIER_PATH
GRACE_SECONDS = p252.GRACE_SECONDS
WAITING_READ_ERROR_DETAIL = p248.read_error_detail(SSUSB_GATE_INDEX)


def _bind(value: int, name: str, path: str) -> ClassifierDetail:
    return ClassifierDetail(
        value=value,
        name=name,
        category="missing-bind",
        path=path,
        expected_symlink_basename=path.rsplit("/", 1)[-1],
    )


DISPLAY_BIND_CLASSIFIERS = (
    _bind(
        0xA0E,
        "display-clock-bind-absent",
        "/sys/bus/platform/drivers/disp_cc-waipio/"
        "af00000.clock-controller",
    ),
    _bind(
        0xA0F,
        "display-rsc-bind-absent",
        "/sys/bus/platform/drivers/rpmh/af20000.rsc",
    ),
    _bind(
        0xA11,
        "display-bcm-voter-bind-absent",
        "/sys/bus/platform/drivers/bcm_voter/"
        "af20000.rsc:bcm_voter",
    ),
)

BIND_CLASSIFIERS = (
    p252.BIND_CLASSIFIERS[:3]
    + DISPLAY_BIND_CLASSIFIERS
    + p252.BIND_CLASSIFIERS[3:]
)
STATE_CLASSIFIERS = p252.STATE_CLASSIFIERS
CLASSIFIER_DETAILS = BIND_CLASSIFIERS + STATE_CLASSIFIERS
CLASSIFIER_VALUES = tuple(detail.value for detail in CLASSIFIER_DETAILS)
CLASSIFIER_BY_VALUE = {
    detail.value: detail for detail in CLASSIFIER_DETAILS
}


def validate_classifier_details(
    details: tuple[ClassifierDetail, ...] = CLASSIFIER_DETAILS,
) -> None:
    p248.validate_steps(STEPS)
    if (
        len(STEPS) != 81
        or MODULE_START_ORDINAL != 8
        or GATE_START_ORDINAL != 68
        or TERMINAL_ORDINAL != 80
        or GATE_COUNT != 12
    ):
        raise SpecError("P2.57 derived stage geometry changed")
    step = p248.step_for_stage(SSUSB_STAGE, STEPS)
    if (
        step.kind != KIND_GATE
        or step.item_index != SSUSB_GATE_INDEX
        or step.gate_index != SSUSB_GATE_INDEX
    ):
        raise SpecError("P2.57 SSUSB stage no longer maps to gate index 9")
    expected_coordinates = {
        0x84: (8, 77),
        0x85: (9, 78),
        0x86: (10, 79),
        0x87: (11, 80),
        0x8F: (0, 81),
    }
    for stage, (item, generation) in expected_coordinates.items():
        candidate = p248.step_for_stage(stage, STEPS)
        if (
            candidate.item_index != item
            or p248.ordinal_for_stage(stage, STEPS) + 1 != generation
        ):
            raise SpecError("P2.57 frontier coordinate changed")
    if len(details) != 20:
        raise SpecError("P2.57 classifier must contain exactly 20 details")
    if len({row.value for row in details}) != len(details):
        raise SpecError("P2.57 classifier detail values are not unique")
    if len({row.name for row in details}) != len(details):
        raise SpecError("P2.57 classifier detail names are not unique")
    for detail in details:
        if not DETAIL_CLASSIFIER_MIN <= detail.value <= DETAIL_CLASSIFIER_MAX:
            raise SpecError("P2.57 classifier detail is outside 0xa00..0xfff")
        if detail.category == "missing-bind":
            if (
                not detail.path
                or not detail.path.startswith("/sys/")
                or detail.expected_symlink_basename
                != detail.path.rsplit("/", 1)[-1]
            ):
                raise SpecError("P2.57 bind descriptor is malformed")
        elif (
            detail.path is not None
            or detail.expected_symlink_basename is not None
        ):
            raise SpecError("P2.57 state descriptor unexpectedly has a path")
    expected_priority = (
        0xA01,
        0xA02,
        0xA03,
        0xA0E,
        0xA0F,
        0xA11,
        0xA04,
        0xA05,
        0xA06,
        0xA07,
        0xA08,
        0xA09,
        0xA0A,
        0xA0B,
        0xA0C,
        0xA0D,
        0xA20,
        0xA21,
    )
    if tuple(row.value for row in details[:18]) != expected_priority:
        raise SpecError("P2.57 bind-classifier priority changed")
    if tuple(row.value for row in details[18:]) != (0xA10, 0xA30):
        raise SpecError("P2.57 state-classifier values changed")

    historical = {
        row.value: (
            row.name,
            row.category,
            row.path,
            row.expected_symlink_basename,
        )
        for row in p252.CLASSIFIER_DETAILS
    }
    current = {
        row.value: (
            row.name,
            row.category,
            row.path,
            row.expected_symlink_basename,
        )
        for row in details
    }
    if any(current.get(value) != identity for value, identity in historical.items()):
        raise SpecError("P2.57 changed an existing P2.52 classifier")


validate_classifier_details()


def step_for_stage(stage: int, steps: tuple[Step, ...] = STEPS) -> Step:
    return p248.step_for_stage(stage, steps)


def ordinal_for_stage(stage: int, steps: tuple[Step, ...] = STEPS) -> int:
    return p248.ordinal_for_stage(stage, steps)


def expected_item(stage: int, steps: tuple[Step, ...] = STEPS) -> int:
    return p248.expected_item(stage, steps)


def regression_detail(gate_index: int) -> int:
    return p248.regression_detail(gate_index)


def read_error_detail(gate_index: int) -> int:
    return p248.read_error_detail(gate_index)


def detail_kind(detail: int) -> str:
    return (
        "classifier"
        if detail in CLASSIFIER_BY_VALUE
        else p248.detail_kind(detail)
    )


def detail_name(detail: int) -> str:
    classifier = CLASSIFIER_BY_VALUE.get(detail)
    return classifier.name if classifier is not None else p248.detail_kind(detail)


def failure_detail_allowed(
    step: Step,
    detail: int,
    *,
    gate_count: int = GATE_COUNT,
) -> bool:
    if p248.failure_detail_allowed(step, detail, gate_count=gate_count):
        return True
    return step.stage == SSUSB_STAGE and detail in CLASSIFIER_BY_VALUE


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
    steps: tuple[Step, ...] = STEPS,
) -> None:
    p248.validate_steps(steps)
    ordinal = p248.ordinal_for_stage(stage, steps)
    step = steps[ordinal]
    if generation != ordinal + 1:
        raise SpecError("slot generation does not match the stage ordinal")
    if item_index != step.item_index:
        raise SpecError("slot item index does not match the descriptor")
    if step.kind == KIND_TERMINAL:
        if outcome != p248.model.OUTCOME_SUCCESS or detail != 0:
            raise SpecError("terminal slot must be zero-detail success")
        return
    if outcome == p248.model.OUTCOME_PROGRESS and detail == 0:
        return
    gate_count = sum(candidate.kind == KIND_GATE for candidate in steps)
    if (
        outcome != p248.model.OUTCOME_FAILURE
        or not failure_detail_allowed(step, detail, gate_count=gate_count)
    ):
        raise SpecError("nonterminal outcome or detail is outside the contract")


def failure_details(
    step: Step,
    *,
    gate_count: int = GATE_COUNT,
) -> tuple[int, ...]:
    values = list(p248.failure_details(step, gate_count=gate_count))
    if step.stage == SSUSB_STAGE:
        values.extend(CLASSIFIER_VALUES)
    result = tuple(values)
    if len(result) != len(set(result)) or any(
        not failure_detail_allowed(step, value, gate_count=gate_count)
        for value in result
    ):
        raise SpecError("generated P2.57 detail domain is invalid")
    return result
