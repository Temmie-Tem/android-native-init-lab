#!/usr/bin/env python3
"""Pure P2.60 E3 ACM-banner stage and identity contract."""

from __future__ import annotations

from dataclasses import replace

import s22plus_fyg8_p258_contract_spec as p258


SCHEMA = "s22plus_fyg8_p260_contract_spec_v1"
PROFILE = p258.PROFILE
TARGET = p258.TARGET

Step = p258.Step
SpecError = p258.SpecError
ClassifierDetail = p258.ClassifierDetail
ModuleInsertion = p258.ModuleInsertion

KIND_LOCAL = p258.KIND_LOCAL
KIND_MODULE = p258.KIND_MODULE
KIND_GATE = p258.KIND_GATE
KIND_TERMINAL = p258.KIND_TERMINAL

DETAIL_ERRNO_MIN = p258.DETAIL_ERRNO_MIN
DETAIL_ERRNO_MAX = p258.DETAIL_ERRNO_MAX
DETAIL_REGRESSION_BASE = p258.DETAIL_REGRESSION_BASE
DETAIL_REGRESSION_MAX = p258.DETAIL_REGRESSION_MAX
DETAIL_READ_ERROR_BASE = p258.DETAIL_READ_ERROR_BASE
DETAIL_READ_ERROR_MAX = p258.DETAIL_READ_ERROR_MAX
DETAIL_CLASSIFIER_MIN = p258.DETAIL_CLASSIFIER_MIN
DETAIL_CLASSIFIER_MAX = p258.DETAIL_CLASSIFIER_MAX

DISPCC_INSERTION = p258.DISPCC_INSERTION
MODULE_INSERTIONS = p258.MODULE_INSERTIONS
HISTORICAL_MODULE_PLAN_COUNT = p258.HISTORICAL_MODULE_PLAN_COUNT
MODULE_PLAN_COUNT = p258.MODULE_PLAN_COUNT
MODULE_STAGE_FIRST = p258.MODULE_STAGE_FIRST
MODULE_STAGE_LAST = p258.MODULE_STAGE_LAST
GATE_STAGE_FIRST = p258.GATE_STAGE_FIRST
GATE_STAGE_LAST = p258.GATE_STAGE_LAST
GATE_COUNT = p258.GATE_COUNT

SSUSB_STAGE = p258.SSUSB_STAGE
SSUSB_GATE_INDEX = p258.SSUSB_GATE_INDEX
DWC3_GATE_INDEX = p258.DWC3_GATE_INDEX
UDC_GATE_INDEX = p258.UDC_GATE_INDEX
UDC_STAGE = p258.UDC_STAGE
UDC_DWELL_SECONDS = p258.UDC_DWELL_SECONDS
UDC_TARGET_NAME = p258.UDC_TARGET_NAME
UDC_TARGET_PATH = p258.UDC_TARGET_PATH

BIND_CLASSIFIERS = p258.BIND_CLASSIFIERS
STATE_CLASSIFIERS = p258.STATE_CLASSIFIERS
CLASSIFIER_DETAILS = p258.CLASSIFIER_DETAILS
CLASSIFIER_VALUES = p258.CLASSIFIER_VALUES
CLASSIFIER_BY_VALUE = p258.CLASSIFIER_BY_VALUE

E3_LOCAL_STAGES = tuple(range(0x88, 0x90))
TERMINAL_STAGE = 0x90
P258_PREFIX_STEPS = p258.STEPS[:-1]
P258_PREFIX_STAGES = tuple(step.stage for step in P258_PREFIX_STEPS)
STEPS = P258_PREFIX_STEPS + tuple(
    Step(stage=stage, item_index=0, kind=KIND_LOCAL)
    for stage in E3_LOCAL_STAGES
) + (
    replace(p258.STEPS[-1], stage=TERMINAL_STAGE),
)
STAGE_SEQUENCE = tuple(step.stage for step in STEPS)
MODULE_START_ORDINAL = p258.MODULE_START_ORDINAL
GATE_START_ORDINAL = p258.GATE_START_ORDINAL
TERMINAL_ORDINAL = len(STEPS) - 1

CONFIGFS_STAGE = 0x88
GADGET_STAGE = 0x89
TTY_CLASS_STAGE = 0x8A
TTY_RAW_STAGE = 0x8B
BANNER_STAGE = 0x8C
ROLE_UDC_STAGE = 0x8D
UDC_BIND_STAGE = 0x8E
CONFIGURED_STAGE = 0x8F

USB_VENDOR_ID = "04e8"
USB_PRODUCT_ID = "6861"
USB_DRIVER = "cdc_acm"
USB_INTERFACE_NUMBER = "00"
USB_SERIAL_PREFIX = "S22E3"
BANNER_PREFIX = "S22PLUS-FYG8-E3:"
USB_SERIAL_SIZE = len(USB_SERIAL_PREFIX) + 32
BANNER_SIZE = len(BANNER_PREFIX) + 32 + 1


def usb_serial(run_id: bytes) -> str:
    if len(run_id) != 16 or not any(run_id):
        raise SpecError("P2.60 run ID must be one nonzero 128-bit value")
    return USB_SERIAL_PREFIX + run_id.hex()


def banner(run_id: bytes) -> bytes:
    if len(run_id) != 16 or not any(run_id):
        raise SpecError("P2.60 run ID must be one nonzero 128-bit value")
    return (BANNER_PREFIX + run_id.hex() + "\n").encode("ascii")


def candidate_observer(run_id: bytes) -> dict[str, str]:
    return {
        "kind": "exact_cdc_acm_banner_v1",
        "usb_vendor_id": USB_VENDOR_ID,
        "usb_product_id": USB_PRODUCT_ID,
        "usb_serial": usb_serial(run_id),
        "usb_driver": USB_DRIVER,
        "usb_interface_number": USB_INTERFACE_NUMBER,
        "banner_hex": banner(run_id).hex(),
    }


def validate_classifier_details(
    details: tuple[ClassifierDetail, ...] = CLASSIFIER_DETAILS,
) -> None:
    p258.validate_classifier_details(details)


def step_for_stage(stage: int, steps: tuple[Step, ...] = STEPS) -> Step:
    return p258.p257.p248.step_for_stage(stage, steps)


def ordinal_for_stage(stage: int, steps: tuple[Step, ...] = STEPS) -> int:
    return p258.p257.p248.ordinal_for_stage(stage, steps)


def expected_item(stage: int, steps: tuple[Step, ...] = STEPS) -> int:
    return step_for_stage(stage, steps).item_index


def regression_detail(gate_index: int) -> int:
    return p258.regression_detail(gate_index)


def read_error_detail(gate_index: int) -> int:
    return p258.read_error_detail(gate_index)


def detail_kind(detail: int) -> str:
    return p258.detail_kind(detail)


def detail_name(detail: int) -> str:
    return p258.detail_name(detail)


def _is_e3_local(step: Step) -> bool:
    return step.kind == KIND_LOCAL and step.stage in E3_LOCAL_STAGES


def failure_detail_allowed(
    step: Step,
    detail: int,
    *,
    gate_count: int = GATE_COUNT,
) -> bool:
    if step.stage in P258_PREFIX_STAGES:
        return p258.failure_detail_allowed(
            step, detail, gate_count=gate_count
        )
    if DETAIL_ERRNO_MIN <= detail <= DETAIL_ERRNO_MAX:
        return _is_e3_local(step)
    if _is_e3_local(step):
        encoded_index = detail & 0xFF
        if encoded_index >= gate_count:
            return False
        return (
            DETAIL_REGRESSION_BASE <= detail <= DETAIL_REGRESSION_MAX
            or DETAIL_READ_ERROR_BASE <= detail <= DETAIL_READ_ERROR_MAX
        )
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
    p258.p257.p248.validate_steps(steps)
    ordinal = ordinal_for_stage(stage, steps)
    step = steps[ordinal]
    if generation != ordinal + 1:
        raise SpecError("slot generation does not match the stage ordinal")
    if item_index != step.item_index:
        raise SpecError("slot item index does not match the descriptor")
    model = p258.p257.p248.model
    if step.kind == KIND_TERMINAL:
        if outcome != model.OUTCOME_SUCCESS or detail != 0:
            raise SpecError("terminal slot must be zero-detail success")
        return
    if outcome == model.OUTCOME_PROGRESS and detail == 0:
        return
    if (
        outcome != model.OUTCOME_FAILURE
        or not failure_detail_allowed(step, detail)
    ):
        raise SpecError("nonterminal outcome or detail is outside P2.60")


def failure_details(
    step: Step,
    *,
    gate_count: int = GATE_COUNT,
) -> tuple[int, ...]:
    if step.stage in P258_PREFIX_STAGES:
        return p258.failure_details(step, gate_count=gate_count)
    if not _is_e3_local(step):
        return ()
    return (
        tuple(range(DETAIL_ERRNO_MIN, DETAIL_ERRNO_MAX + 1))
        + tuple(regression_detail(index) for index in range(gate_count))
        + tuple(read_error_detail(index) for index in range(gate_count))
    )


def validate_steps(steps: tuple[Step, ...] = STEPS) -> None:
    p258.p257.p248.validate_steps(steps)
    if (
        len(steps) != 89
        or steps[:80] != p258.STEPS[:80]
        or steps[79].stage != p258.UDC_STAGE
        or tuple(step.stage for step in steps[80:88])
        != E3_LOCAL_STAGES
        or TERMINAL_ORDINAL != 88
        or ordinal_for_stage(CONFIGURED_STAGE, steps) + 1 != 88
        or ordinal_for_stage(TERMINAL_STAGE, steps) + 1 != 89
    ):
        raise SpecError("P2.60 E3 descriptor geometry changed")
    for step in steps[80:88]:
        if step.kind != KIND_LOCAL or step.item_index != 0:
            raise SpecError("P2.60 E3 stages must remain local item zero")
    for step in steps:
        for detail in failure_details(step):
            if not failure_detail_allowed(step, detail):
                raise SpecError("P2.60 generated detail domain changed")
    if len(usb_serial(b"\x01" * 16)) != USB_SERIAL_SIZE:
        raise SpecError("P2.60 USB serial size changed")
    if len(banner(b"\x01" * 16)) != BANNER_SIZE:
        raise SpecError("P2.60 banner size changed")


validate_classifier_details()
validate_steps()
