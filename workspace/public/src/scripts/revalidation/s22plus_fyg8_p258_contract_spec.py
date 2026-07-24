#!/usr/bin/env python3
"""P2.58A UDC-membership oracle over the unchanged P2.57 record ABI."""

from __future__ import annotations

from dataclasses import dataclass

import s22plus_fyg8_p257_contract_spec as p257


SCHEMA = "s22plus_fyg8_p258_contract_spec_v1"
PROFILE = p257.PROFILE

Step = p257.Step
SpecError = p257.SpecError
ClassifierDetail = p257.ClassifierDetail
ModuleInsertion = p257.ModuleInsertion

KIND_LOCAL = p257.KIND_LOCAL
KIND_MODULE = p257.KIND_MODULE
KIND_GATE = p257.KIND_GATE
KIND_TERMINAL = p257.KIND_TERMINAL

DETAIL_ERRNO_MIN = p257.DETAIL_ERRNO_MIN
DETAIL_ERRNO_MAX = p257.DETAIL_ERRNO_MAX
DETAIL_REGRESSION_BASE = p257.DETAIL_REGRESSION_BASE
DETAIL_REGRESSION_MAX = p257.DETAIL_REGRESSION_MAX
DETAIL_READ_ERROR_BASE = p257.DETAIL_READ_ERROR_BASE
DETAIL_READ_ERROR_MAX = p257.DETAIL_READ_ERROR_MAX
DETAIL_CLASSIFIER_MIN = p257.DETAIL_CLASSIFIER_MIN
DETAIL_CLASSIFIER_MAX = p257.DETAIL_CLASSIFIER_MAX

DISPCC_INSERTION = p257.DISPCC_INSERTION
MODULE_INSERTIONS = p257.MODULE_INSERTIONS
HISTORICAL_MODULE_PLAN_COUNT = p257.HISTORICAL_MODULE_PLAN_COUNT
MODULE_PLAN_COUNT = p257.MODULE_PLAN_COUNT
MODULE_STAGE_FIRST = p257.MODULE_STAGE_FIRST
MODULE_STAGE_LAST = p257.MODULE_STAGE_LAST
GATE_STAGE_FIRST = p257.GATE_STAGE_FIRST
GATE_STAGE_LAST = p257.GATE_STAGE_LAST
TERMINAL_STAGE = p257.TERMINAL_STAGE

STEPS = p257.STEPS
STAGE_SEQUENCE = p257.STAGE_SEQUENCE
MODULE_START_ORDINAL = p257.MODULE_START_ORDINAL
GATE_START_ORDINAL = p257.GATE_START_ORDINAL
TERMINAL_ORDINAL = p257.TERMINAL_ORDINAL
GATE_COUNT = p257.GATE_COUNT

SSUSB_STAGE = p257.SSUSB_STAGE
SSUSB_GATE_INDEX = p257.SSUSB_GATE_INDEX
WAITING_FOR_SUPPLIER_PATH = p257.WAITING_FOR_SUPPLIER_PATH
GRACE_SECONDS = p257.GRACE_SECONDS
WAITING_READ_ERROR_DETAIL = p257.WAITING_READ_ERROR_DETAIL

BIND_CLASSIFIERS = p257.BIND_CLASSIFIERS
STATE_CLASSIFIERS = p257.STATE_CLASSIFIERS
CLASSIFIER_DETAILS = p257.CLASSIFIER_DETAILS
CLASSIFIER_VALUES = p257.CLASSIFIER_VALUES
CLASSIFIER_BY_VALUE = p257.CLASSIFIER_BY_VALUE

DWC3_GATE_INDEX = 10
UDC_GATE_INDEX = 11
UDC_STAGE = GATE_STAGE_FIRST + UDC_GATE_INDEX
UDC_DWELL_SECONDS = 5
UDC_TARGET_NAME = "a600000.dwc3"
UDC_TARGET_PATH = f"/sys/class/udc/{UDC_TARGET_NAME}"
UDC_STOCK_PEER = "dummy_udc.0"
STOCK_TOPOLOGY_PATH = (
    "docs/module-map/s22plus-fyg8/stock-usb-runtime-topology.json"
)


@dataclass(frozen=True)
class UdcOracleCase:
    name: str
    entries: tuple[str, ...]
    target_is_symlink: bool
    target_basename: str | None
    expected: bool


UDC_ORACLE_CASES = (
    UdcOracleCase(
        "target-absent",
        (UDC_STOCK_PEER,),
        False,
        None,
        False,
    ),
    UdcOracleCase(
        "real-only",
        (UDC_TARGET_NAME,),
        True,
        UDC_TARGET_NAME,
        True,
    ),
    UdcOracleCase(
        "known-good-stock",
        (UDC_TARGET_NAME, UDC_STOCK_PEER),
        True,
        UDC_TARGET_NAME,
        True,
    ),
    UdcOracleCase(
        "unrelated-peer",
        (UDC_TARGET_NAME, "foreign_udc.0"),
        True,
        UDC_TARGET_NAME,
        True,
    ),
    UdcOracleCase(
        "wrong-target",
        (UDC_TARGET_NAME, UDC_STOCK_PEER),
        True,
        "wrong-controller",
        False,
    ),
    UdcOracleCase(
        "wrong-type",
        (UDC_TARGET_NAME, UDC_STOCK_PEER),
        False,
        UDC_TARGET_NAME,
        False,
    ),
    UdcOracleCase(
        "duplicate-target",
        (UDC_TARGET_NAME, UDC_TARGET_NAME, UDC_STOCK_PEER),
        True,
        UDC_TARGET_NAME,
        False,
    ),
)


def evaluate_udc_oracle(case: UdcOracleCase) -> bool:
    return (
        case.entries.count(UDC_TARGET_NAME) == 1
        and case.target_is_symlink
        and case.target_basename == UDC_TARGET_NAME
    )


def validate_udc_oracle(
    cases: tuple[UdcOracleCase, ...] = UDC_ORACLE_CASES,
) -> None:
    expected_names = {
        "target-absent",
        "real-only",
        "known-good-stock",
        "unrelated-peer",
        "wrong-target",
        "wrong-type",
        "duplicate-target",
    }
    by_name = {case.name: case for case in cases}
    if len(by_name) != len(cases) or set(by_name) != expected_names:
        raise SpecError("P2.58A UDC oracle case inventory changed")
    stock = by_name["known-good-stock"]
    if (
        stock.entries != (UDC_TARGET_NAME, UDC_STOCK_PEER)
        or UDC_STOCK_PEER not in stock.entries
        or not stock.expected
    ):
        raise SpecError("P2.58A known-good two-UDC oracle changed")
    peer = by_name["unrelated-peer"]
    if len(peer.entries) < 2 or not peer.expected:
        raise SpecError("P2.58A unrelated-peer policy changed")
    for case in cases:
        if evaluate_udc_oracle(case) is not case.expected:
            raise SpecError(f"P2.58A UDC oracle mismatch: {case.name}")


validate_classifier_details = p257.validate_classifier_details
step_for_stage = p257.step_for_stage
ordinal_for_stage = p257.ordinal_for_stage
expected_item = p257.expected_item
regression_detail = p257.regression_detail
read_error_detail = p257.read_error_detail
detail_kind = p257.detail_kind
detail_name = p257.detail_name
failure_detail_allowed = p257.failure_detail_allowed
validate_slot = p257.validate_slot
failure_details = p257.failure_details


p257.validate_classifier_details()
validate_udc_oracle()

if (
    step_for_stage(UDC_STAGE).item_index != UDC_GATE_INDEX
    or step_for_stage(UDC_STAGE).kind != KIND_GATE
    or DWC3_GATE_INDEX + 1 != UDC_GATE_INDEX
    or UDC_DWELL_SECONDS != GRACE_SECONDS
):
    raise SpecError("P2.58A UDC frontier geometry changed")
