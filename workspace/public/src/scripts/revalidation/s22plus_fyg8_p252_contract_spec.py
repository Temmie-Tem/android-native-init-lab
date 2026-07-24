#!/usr/bin/env python3
"""Pure P2.52 SSUSB timeout-classifier contract."""

from __future__ import annotations

from dataclasses import dataclass

import s22plus_fyg8_p248_contract_spec as p248


SCHEMA = "s22plus_fyg8_p252_contract_spec_v1"
PROFILE = p248.PROFILE

Step = p248.Step
SpecError = p248.SpecError

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
DETAIL_CLASSIFIER_MIN = 0xA00
DETAIL_CLASSIFIER_MAX = 0xFFF

STEPS = p248.STEPS
STAGE_SEQUENCE = p248.STAGE_SEQUENCE
TERMINAL_STAGE = p248.TERMINAL_STAGE
MODULE_START_ORDINAL = p248.MODULE_START_ORDINAL
GATE_START_ORDINAL = p248.GATE_START_ORDINAL
TERMINAL_ORDINAL = p248.TERMINAL_ORDINAL
GATE_COUNT = p248.GATE_COUNT

SSUSB_STAGE = 0x84
SSUSB_GATE_INDEX = 9
WAITING_FOR_SUPPLIER_PATH = (
    "/sys/devices/platform/soc/a600000.ssusb/waiting_for_supplier"
)
GRACE_SECONDS = 5
WAITING_READ_ERROR_DETAIL = p248.read_error_detail(SSUSB_GATE_INDEX)


@dataclass(frozen=True)
class ClassifierDetail:
    value: int
    name: str
    category: str
    path: str | None = None
    expected_symlink_basename: str | None = None


def _bind(
    value: int,
    name: str,
    path: str,
) -> ClassifierDetail:
    return ClassifierDetail(
        value=value,
        name=name,
        category="missing-bind",
        path=path,
        expected_symlink_basename=path.rsplit("/", 1)[-1],
    )


BIND_CLASSIFIERS = (
    _bind(
        0xA01,
        "usb3-gdsc-bind-absent",
        "/sys/bus/platform/drivers/gdsc/149004.qcom,gdsc",
    ),
    _bind(
        0xA02,
        "pdc-bind-absent",
        "/sys/bus/platform/drivers/qcom-pdc/"
        "b220000.interrupt-controller",
    ),
    _bind(
        0xA03,
        "qnoc-aggre1-bind-absent",
        "/sys/bus/platform/drivers/qnoc-waipio/16e0000.interconnect",
    ),
    _bind(
        0xA04,
        "qnoc-mc-virt-bind-absent",
        "/sys/bus/platform/drivers/qnoc-waipio/soc:interconnect@1",
    ),
    _bind(
        0xA05,
        "qnoc-config-bind-absent",
        "/sys/bus/platform/drivers/qnoc-waipio/1500000.interconnect",
    ),
    _bind(
        0xA06,
        "qnoc-gem-bind-absent",
        "/sys/bus/platform/drivers/qnoc-waipio/19100000.interconnect",
    ),
    _bind(
        0xA07,
        "eud-bind-absent",
        "/sys/bus/platform/drivers/msm-eud/88e0000.qcom,msm-eud",
    ),
    _bind(
        0xA08,
        "waipio-tlmm-bind-absent",
        "/sys/bus/platform/drivers/waipio-pinctrl/f000000.pinctrl",
    ),
    _bind(
        0xA09,
        "ssphy-vdd-ldob1-bind-absent",
        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
        "17a00000.rsc:rpmh-regulator-ldob1",
    ),
    _bind(
        0xA0A,
        "ssphy-core-ldob6-bind-absent",
        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
        "17a00000.rsc:rpmh-regulator-ldob6",
    ),
    _bind(
        0xA0B,
        "hsphy-vdd-ldob5-bind-absent",
        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
        "17a00000.rsc:rpmh-regulator-ldob5",
    ),
    _bind(
        0xA0C,
        "hsphy-vdda18-ldoc1-bind-absent",
        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
        "17a00000.rsc:rpmh-regulator-ldoc1",
    ),
    _bind(
        0xA0D,
        "hsphy-vdda33-ldob2-bind-absent",
        "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
        "17a00000.rsc:rpmh-regulator-ldob2",
    ),
    _bind(
        0xA20,
        "hsphy-bind-absent",
        "/sys/bus/platform/drivers/msm-usb-hsphy/88e3000.hsphy",
    ),
    _bind(
        0xA21,
        "ssphy-bind-absent",
        "/sys/bus/platform/drivers/msm-usb-ssphy-qmp/88e8000.ssphy",
    ),
)

STATE_CLASSIFIERS = (
    ClassifierDetail(
        value=0xA10,
        name="waiting-for-supplier",
        category="waiting-state",
    ),
    ClassifierDetail(
        value=0xA30,
        name="all-known-ready-parent-absent-after-grace",
        category="grace-exhausted",
    ),
)

CLASSIFIER_DETAILS = BIND_CLASSIFIERS + STATE_CLASSIFIERS
CLASSIFIER_VALUES = tuple(detail.value for detail in CLASSIFIER_DETAILS)
CLASSIFIER_BY_VALUE = {
    detail.value: detail for detail in CLASSIFIER_DETAILS
}


def validate_classifier_details(
    details: tuple[ClassifierDetail, ...] = CLASSIFIER_DETAILS,
) -> None:
    p248.validate_steps(STEPS)
    step = p248.step_for_stage(SSUSB_STAGE)
    if (
        step.kind != KIND_GATE
        or step.item_index != SSUSB_GATE_INDEX
        or step.gate_index != SSUSB_GATE_INDEX
    ):
        raise SpecError("P2.52 SSUSB stage no longer maps to gate index 9")
    if len(details) != 17:
        raise SpecError("P2.52 classifier must contain exactly 17 details")
    if len({detail.value for detail in details}) != len(details):
        raise SpecError("P2.52 classifier detail values are not unique")
    if len({detail.name for detail in details}) != len(details):
        raise SpecError("P2.52 classifier detail names are not unique")
    for detail in details:
        if not DETAIL_CLASSIFIER_MIN <= detail.value <= DETAIL_CLASSIFIER_MAX:
            raise SpecError("P2.52 classifier detail is outside 0xa00..0xfff")
        if detail.category == "missing-bind":
            if (
                not detail.path
                or not detail.path.startswith("/sys/")
                or detail.expected_symlink_basename
                != detail.path.rsplit("/", 1)[-1]
            ):
                raise SpecError("P2.52 bind descriptor is malformed")
        elif detail.path is not None or detail.expected_symlink_basename is not None:
            raise SpecError("P2.52 state descriptor unexpectedly has a path")
    if tuple(detail.value for detail in details[:15]) != (
        0xA01,
        0xA02,
        0xA03,
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
    ):
        raise SpecError("P2.52 bind-classifier priority changed")
    if tuple(detail.value for detail in details[15:]) != (0xA10, 0xA30):
        raise SpecError("P2.52 state-classifier values changed")


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
    if detail in CLASSIFIER_BY_VALUE:
        return "classifier"
    return p248.detail_kind(detail)


def detail_name(detail: int) -> str:
    classifier = CLASSIFIER_BY_VALUE.get(detail)
    if classifier is not None:
        return classifier.name
    return p248.detail_kind(detail)


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
        raise SpecError("generated P2.52 detail domain is invalid")
    return result
