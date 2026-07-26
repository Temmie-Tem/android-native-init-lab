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

# arm64 asm-generic UAPI plus fs/configfs/mount.c. Keep configfs distinct
# from SYSFS_MAGIC; these values are audited before Full LTO.
CONFIGFS_MAGIC = 0x62656570
SYSFS_MAGIC = 0x62656572
RUNTIME_EXTERNAL_CONSTANTS = (
    ("P260_NR_IOCTL", 29),
    ("P260_NR_SYMLINKAT", 36),
    ("P260_O_NOCTTY", 0o00000400),
    ("P260_CONFIGFS_MAGIC", CONFIGFS_MAGIC),
    ("P260_EINTR", 4),
    ("P260_EBUSY", 16),
    ("P260_ENOTTY", 25),
    ("P260_EPROTO", 71),
    ("P260_EOVERFLOW", 75),
    ("P260_TCGETS", 0x5401),
    ("P260_TCSETS", 0x5402),
    ("P260_CSIZE", 0o0000060),
    ("P260_CS8", 0o0000060),
    ("P260_CREAD", 0o0000200),
    ("P260_PARENB", 0o0000400),
    ("P260_CLOCAL", 0o0004000),
)
CONFIGFS_FUNCTION_LINK_CREATE_TARGET = (
    "/config/usb_gadget/g1/functions/acm.usb0"
)
CONFIGFS_FUNCTION_LINK_READBACK_TARGET = (
    "../../../../usb_gadget/g1/functions/acm.usb0"
)
RUNTIME_EXTERNAL_STRINGS = (
    ("p260_link_create_target", CONFIGFS_FUNCTION_LINK_CREATE_TARGET),
    ("p260_link_readback_target", CONFIGFS_FUNCTION_LINK_READBACK_TARGET),
)
USB_VENDOR_ID = "04e8"
USB_PRODUCT_ID = "6861"
USB_DRIVER = "cdc_acm"
USB_INTERFACE_NUMBER = "00"
USB_SERIAL_PREFIX = "S22E3"
BANNER_PREFIX = "S22PLUS-FYG8-E3:"
USB_SERIAL_SIZE = len(USB_SERIAL_PREFIX) + 32
BANNER_SIZE = len(BANNER_PREFIX) + 32 + 1
E3_RUNTIME_INCLUDE_SHA256 = (
    "767bd359de56cb24be84c4479cd01d4f710a676490c23f966617b996fe5cc612"
)
ELF_SLASH_ARTIFACT_STRINGS = ("/", "/8@", "/@")
E3_AUTHORITY_STRINGS = (
    "/config",
    "configfs",
    "/config/usb_gadget/g1",
    "/config/usb_gadget/g1/UDC",
    "/config/usb_gadget/g1/strings/0x409",
    "/config/usb_gadget/g1/configs/b.1",
    "/config/usb_gadget/g1/configs/b.1/strings/0x409",
    "/config/usb_gadget/g1/functions/acm.usb0",
    "/config/usb_gadget/g1/configs/b.1/acm.usb0",
    "/config/usb_gadget/g1/idVendor",
    "/config/usb_gadget/g1/idProduct",
    "/config/usb_gadget/g1/bcdUSB",
    "/config/usb_gadget/g1/bcdDevice",
    "/config/usb_gadget/g1/max_speed",
    "/config/usb_gadget/g1/strings/0x409/manufacturer",
    "/config/usb_gadget/g1/strings/0x409/product",
    "/config/usb_gadget/g1/strings/0x409/serialnumber",
    "/config/usb_gadget/g1/configs/b.1/bmAttributes",
    "/config/usb_gadget/g1/configs/b.1/MaxPower",
    "/config/usb_gadget/g1/configs/b.1/strings/0x409/configuration",
    "/sys/class/tty/ttyGS0/dev",
    "/dev/ttyGS0",
    "/sys/class/udc/a600000.dwc3/state",
    "/sys/class/udc/a600000.dwc3/current_speed",
    "/sys/devices/platform/soc/a600000.ssusb/mode",
)
BASE_ABSOLUTE_PATH_STRINGS = (
    "/dev/null",
    "/lib/modules/",
    "/proc",
    "/proc/modules",
    "/proc/s22_checkpoint",
    "/run",
    "/s22-e1-child",
    "/sys",
    "/sys/bus/platform/drivers/bcm_voter/af20000.rsc:bcm_voter",
    "/sys/bus/platform/drivers/clk-rpmh/17a00000.rsc:qcom,rpmhclk",
    "/sys/bus/platform/drivers/cmd-db/80860000.aop_cmd_db_region",
    "/sys/bus/platform/drivers/disp_cc-waipio/af00000.clock-controller",
    "/sys/bus/platform/drivers/dwc3/a600000.dwc3",
    "/sys/bus/platform/drivers/gcc-waipio/100000.clock-controller",
    "/sys/bus/platform/drivers/gdsc/149004.qcom,gdsc",
    "/sys/bus/platform/drivers/msm-dwc3/a600000.ssusb",
    "/sys/bus/platform/drivers/msm-eud/88e0000.qcom,msm-eud",
    "/sys/bus/platform/drivers/msm-usb-hsphy/88e3000.hsphy",
    "/sys/bus/platform/drivers/msm-usb-ssphy-qmp/88e8000.ssphy",
    "/sys/bus/platform/drivers/psci-cpuidle-domain/soc:psci",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-cxlvl",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-ldob1",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-ldob2",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-ldob5",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-ldob6",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-ldoc1",
    "/sys/bus/platform/drivers/qcom,rpmh-regulator/"
    "17a00000.rsc:rpmh-regulator-mxlvl",
    "/sys/bus/platform/drivers/qcom-pdc/b220000.interrupt-controller",
    "/sys/bus/platform/drivers/qcom-smem/soc:qcom,smem",
    "/sys/bus/platform/drivers/qcom_hwspinlock/soc:hwlock",
    "/sys/bus/platform/drivers/qnoc-waipio/1500000.interconnect",
    "/sys/bus/platform/drivers/qnoc-waipio/16e0000.interconnect",
    "/sys/bus/platform/drivers/qnoc-waipio/19100000.interconnect",
    "/sys/bus/platform/drivers/qnoc-waipio/soc:interconnect@1",
    "/sys/bus/platform/drivers/rpmh/17a00000.rsc",
    "/sys/bus/platform/drivers/rpmh/af20000.rsc",
    "/sys/bus/platform/drivers/waipio-pinctrl/f000000.pinctrl",
    "/sys/class/udc",
    "/sys/class/udc/a600000.dwc3",
    "/sys/devices/platform/soc/a600000.ssusb/waiting_for_supplier",
)
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *BASE_ABSOLUTE_PATH_STRINGS,
        *(
            value
            for value in E3_AUTHORITY_STRINGS
            if value.startswith("/")
        ),
    )
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    (*REQUIRED_ABSOLUTE_PATH_STRINGS, *ELF_SLASH_ARTIFACT_STRINGS)
)
E3_REQUIRED_CONTROL_STRINGS = frozenset(
    (
        "configfs",
        CONFIGFS_FUNCTION_LINK_CREATE_TARGET,
        CONFIGFS_FUNCTION_LINK_READBACK_TARGET,
        "0x0003",
        "0x0200",
        "0x04e8",
        "0x6861",
        "0x80",
        "500",
        "Android Native Init Lab",
        "S22+ E3 ACM",
        "acm",
        "a600000.dwc3",
        "configured",
        "high-speed",
        "host",
        "none",
        "peripheral",
    )
)
E3_HEX_CONTROL_STRINGS = frozenset(
    ("0x0003", "0x0200", "0x04e8", "0x6861", "0x80")
)
E3_FUNCTION_TARGET_STRINGS = frozenset(
    (
        CONFIGFS_FUNCTION_LINK_CREATE_TARGET,
        CONFIGFS_FUNCTION_LINK_READBACK_TARGET,
    )
)
E3_SPEED_CONTROL_STRINGS = frozenset(("high-speed",))
E3_ROLE_CONTROL_STRINGS = frozenset(("host", "none", "peripheral"))
E3_UDC_NAME_STRINGS = frozenset(("a600000.dwc3",))


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
