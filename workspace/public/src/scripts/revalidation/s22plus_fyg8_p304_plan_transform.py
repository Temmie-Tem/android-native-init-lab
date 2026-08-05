#!/usr/bin/env python3
"""Add the exact stock USB notifier bridge to the P3.03 module plan."""

from __future__ import annotations

import re


MODULE_NAME = "usb_notifier_qcom.ko"
MODULE_RUNTIME = "usb_notifier_qcom"
MODULE_PLAN_COUNT = 61
_PREVIOUS = b'    {"dwc3-msm.ko", "dwc3_msm", ""},\n'
_NEXT = b'    {"ucsi_glink.ko", "ucsi_glink", ""},\n'
_INSERTED = (
    _PREVIOUS
    + b'    {"usb_notifier_qcom.ko", "usb_notifier_qcom", ""},\n'
    + _NEXT
)


class PlanTransformError(ValueError):
    pass


def module_names(data: bytes) -> tuple[str, ...]:
    return tuple(
        value.decode("ascii")
        for value in re.findall(rb'^\s+\{"([^"]+\.ko)",', data, re.MULTILINE)
    )


def transform(data: bytes) -> bytes:
    anchor = _PREVIOUS + _NEXT
    names = module_names(data)
    if (
        data.count(anchor) != 1
        or MODULE_NAME in names
        or len(names) != MODULE_PLAN_COUNT - 1
        or len(set(names)) != len(names)
    ):
        raise PlanTransformError("P3.03 module-plan preimage differs")
    result = data.replace(anchor, _INSERTED, 1)
    transformed = module_names(result)
    position = transformed.index(MODULE_NAME)
    if (
        result.count(_INSERTED) != 1
        or len(transformed) != MODULE_PLAN_COUNT
        or len(set(transformed)) != MODULE_PLAN_COUNT
        or transformed[position - 1] != "dwc3-msm.ko"
        or transformed[position + 1] != "ucsi_glink.ko"
    ):
        raise PlanTransformError("P3.04 module-plan postimage differs")
    return result
