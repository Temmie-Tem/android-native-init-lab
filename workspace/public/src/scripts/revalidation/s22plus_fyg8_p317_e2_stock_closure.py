#!/usr/bin/env python3
"""Bind the exact 69-module P3.17 substrate and effective rootfs."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import s22plus_fyg8_p316_e2_stock_closure as base
import s22plus_fyg8_p317_overlay_contract as overlay


SCHEMA = "s22plus_fyg8_p317_stock_closure_h0_v1"
VERDICT = "PASS_P317_STOCK_69_MODULE_EXECUTABILITY_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_COUNT = 69
ADDED_MODULES = (
    ("spmi-pmic-arb.ko", "spmi_pmic_arb"),
    ("pinctrl-spmi-gpio.ko", "pinctrl_spmi_gpio"),
    ("qti-regmap-debugfs.ko", "qti_regmap_debugfs"),
    ("regmap-spmi.ko", "regmap_spmi"),
    ("qcom-spmi-pmic.ko", "qcom_spmi_pmic"),
    *base.ADDED_MODULES,
)
P317_ADDITIONAL_ABSOLUTE_PATH_STRINGS = frozenset({
    "/proc/cmdline",
    "/sys/bus/spmi/devices/",
    "/soc/qcom,spmi@c42d000",
    "/soc/qcom,spmi@c42d000/qcom,pm8350c@2",
    "/soc/qcom,spmi@c42d000/qcom,pm8350c@2/pinctrl@8800",
    "/waiting_for_supplier",
    "/of_node",
})
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset({
    *base.REQUIRED_ABSOLUTE_PATH_STRINGS,
    *P317_ADDITIONAL_ABSOLUTE_PATH_STRINGS,
})
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset({
    *base.ALLOWED_ABSOLUTE_PATH_STRINGS,
    *P317_ADDITIONAL_ABSOLUTE_PATH_STRINGS,
})
ClosureError = base.ClosureError
P310 = base.P310
INCIDENTAL_PATH = base.INCIDENTAL_PATH
INCIDENTAL_PATHS = frozenset({base.INCIDENTAL_PATH, b"/e9;"})


@contextmanager
def _configured() -> Iterator[None]:
    names = (
        "SCHEMA", "VERDICT", "EXPECTED_MODULE_COUNT", "ADDED_MODULES",
        "REQUIRED_ABSOLUTE_PATH_STRINGS", "ALLOWED_ABSOLUTE_PATH_STRINGS",
        "INCIDENTAL_PATHS", "overlay",
    )
    previous = {name: getattr(base, name) for name in names}
    values = {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "EXPECTED_MODULE_COUNT": EXPECTED_MODULE_COUNT,
        "ADDED_MODULES": ADDED_MODULES,
        "REQUIRED_ABSOLUTE_PATH_STRINGS": REQUIRED_ABSOLUTE_PATH_STRINGS,
        "ALLOWED_ABSOLUTE_PATH_STRINGS": ALLOWED_ABSOLUTE_PATH_STRINGS,
        "INCIDENTAL_PATHS": INCIDENTAL_PATHS,
        "overlay": overlay,
    }
    for name, value in values.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def select(source_contract_id: str | None):
    if source_contract_id != overlay.PARENT_SOURCE_CONTRACT_ID:
        raise ClosureError("P3.17 source contract differs")
    return __import__(__name__)


def closure_sha256(value: dict[str, Any]) -> str:
    return base.closure_sha256(value)


def derive_module_closure(root: Path, vendor_ramdisk: Path, lz4: Path, plan_header: Path | None = None):
    with _configured():
        return base.derive_module_closure(root, vendor_ramdisk, lz4, plan_header)


def validate_module_closure(value: Any, *, allow_unpinned: bool = False):
    with _configured():
        return base.validate_module_closure(value, allow_unpinned=allow_unpinned)


def rootfs_audit(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configured():
        return base.rootfs_audit(*args, **kwargs)


def audit_candidate_generic_rootfs(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configured():
        return base.audit_candidate_generic_rootfs(*args, **kwargs)


def validate_effective_rootfs(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    with _configured():
        return base.validate_effective_rootfs(*args, **kwargs)


@contextmanager
def exact_init_authority(expected: bytes) -> Iterator[None]:
    with _configured():
        with base.exact_init_authority(expected):
            yield
