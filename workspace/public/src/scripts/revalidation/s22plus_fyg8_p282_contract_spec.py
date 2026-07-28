#!/usr/bin/env python3
"""Single-source P2.82 stage, diagnostic, tuple, and classifier contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum

import s22plus_fyg8_p280_contract_spec as p280


SCHEMA = "s22plus_fyg8_p282_contract_spec_v1"
PROFILE = p280.PROFILE
TARGET = p280.TARGET

Step = p280.Step
SpecError = p280.SpecError

KIND_LOCAL = p280.KIND_LOCAL
KIND_MODULE = p280.KIND_MODULE
KIND_GATE = p280.KIND_GATE
KIND_TERMINAL = p280.KIND_TERMINAL

OUTCOME_PROGRESS = p280.OUTCOME_PROGRESS
OUTCOME_SUCCESS = p280.OUTCOME_SUCCESS
OUTCOME_FAILURE = p280.OUTCOME_FAILURE

GATE_COUNT = p280.GATE_COUNT
CLASSIFIER_DETAILS = p280.CLASSIFIER_DETAILS
SSUSB_STAGE = p280.SSUSB_STAGE
ROLE_UDC_STAGE = 0x8D
STOP_STAGE = 0x8E
SUSPENDED_STAGE = 0x8F
RESTART_STAGE = 0x90
BIND_STAGE = 0x91
FINAL_STAGE = 0x92
TERMINAL_STAGE = 0x93

P280_PREFIX_STEPS = p280.STEPS[
    : p280.ordinal_for_stage(ROLE_UDC_STAGE) + 1
]
LOCAL_STAGES = (
    STOP_STAGE,
    SUSPENDED_STAGE,
    RESTART_STAGE,
    BIND_STAGE,
    FINAL_STAGE,
)
STEPS = P280_PREFIX_STEPS + tuple(
    Step(stage=stage, item_index=0, kind=KIND_LOCAL)
    for stage in LOCAL_STAGES
) + (replace(p280.STEPS[-1], stage=TERMINAL_STAGE),)
STAGE_SEQUENCE = tuple(step.stage for step in STEPS)
TERMINAL_ORDINAL = len(STEPS) - 1

PHASE_ROLE = "role"
PHASE_CYCLE = "cycle"
PHASE_BIND = "bind"
TRACE_GROUP = "p282"
TRACE_INSTANCE = "p282"
TRACE_BUFFER_KB = 64
ROLE_DEADLINE_SEC = p280.ROLE_DEADLINE_SEC
CYCLE_DEADLINE_SEC = 30
FINAL_DEADLINE_SEC = 30
POLL_INTERVAL_MSEC = 100

PARENT_MODE_PATH = "/sys/devices/platform/soc/a600000.ssusb/mode"
CHILD_RUNTIME_STATUS_PATH = (
    "/sys/devices/platform/soc/a600000.ssusb/"
    "a600000.dwc3/power/runtime_status"
)
EXACT_UDC_PATH = "/sys/class/udc/a600000.dwc3"
UDC_STATE_PATH = f"{EXACT_UDC_PATH}/state"
UDC_SPEED_PATH = f"{EXACT_UDC_PATH}/current_speed"
ROLE_NONE_WRITE = "none\n"
ROLE_PERIPHERAL_WRITE = "peripheral\n"
ROLE_NONE_READBACK = "none\n"
ROLE_PERIPHERAL_READBACK = "peripheral\n"
CHILD_SUSPENDED_READBACK = "suspended\n"
CHILD_ACTIVE_READBACK = "active\n"

DWC3_MSM_MODULE_RUNTIME_NAME = "dwc3_msm"
HSPHY_MODULE_RUNTIME_NAME = "phy_msm_snps_hs"
PARENT_SYMBOL = "dwc3_otg_start_peripheral"
MODULE_RUNTIME_NAME = DWC3_MSM_MODULE_RUNTIME_NAME
MODULE_HSPHY_NAME = HSPHY_MODULE_RUNTIME_NAME
EXACT_DWC3_MSM_SHA256 = (
    "8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1"
)
EXACT_HSPHY_SHA256 = (
    "22a866320ba0de46619484efafaf0cf7ea3f7ba387cee7c3dd085f3a82492e94"
)


@dataclass(frozen=True)
class TraceEvent:
    phase: str
    name: str
    probe_kind: str
    symbol: str
    module: str | None
    fetch: str
    filter_expression: str
    post_call_ordinal: int | None = None

    def target(self, offsets: tuple[int, int] | None = None) -> str:
        symbol = self.symbol
        if self.post_call_ordinal is not None:
            if offsets is None or len(offsets) != 2:
                raise SpecError("P2.82 role post-call offsets are unavailable")
            symbol = f"{symbol}+0x{offsets[self.post_call_ordinal]:x}"
        return f"{self.module}:{symbol}" if self.module else symbol

    def definition(self, offsets: tuple[int, int] | None = None) -> str:
        prefix = "r" if self.probe_kind == "return" else "p"
        return (
            f"{prefix}:{TRACE_GROUP}/{self.name} {self.target(offsets)}"
            f"{self.fetch}\n"
        )


def _entry(
    phase: str,
    name: str,
    symbol: str,
    module: str | None,
    fetch: str = "",
    post_call_ordinal: int | None = None,
) -> TraceEvent:
    return TraceEvent(
        phase,
        name,
        "entry",
        symbol,
        module,
        fetch,
        "common_pid > 0",
        post_call_ordinal,
    )


def _return(
    phase: str,
    name: str,
    symbol: str,
    module: str | None,
) -> TraceEvent:
    return TraceEvent(
        phase,
        name,
        "return",
        symbol,
        module,
        " rc=$retval:s32",
        "common_pid > 0",
        None,
    )


TRACE_EVENTS = (
    _entry(
        PHASE_ROLE,
        "start_in",
        "dwc3_otg_start_peripheral",
        MODULE_RUNTIME_NAME,
        " on=%x1:s32",
    ),
    _entry(
        PHASE_ROLE,
        "parent_pm_out",
        "dwc3_otg_start_peripheral",
        MODULE_RUNTIME_NAME,
        " rc=%x0:s32",
        post_call_ordinal=0,
    ),
    _entry(
        PHASE_ROLE,
        "child_pm_out",
        "dwc3_otg_start_peripheral",
        MODULE_RUNTIME_NAME,
        " rc=%x0:s32",
        post_call_ordinal=1,
    ),
    _return(
        PHASE_ROLE,
        "start_out",
        "dwc3_otg_start_peripheral",
        MODULE_RUNTIME_NAME,
    ),
    _entry(
        PHASE_CYCLE,
        "worker_in",
        "dwc3_otg_start_peripheral",
        MODULE_RUNTIME_NAME,
        " on=%x1:s32",
    ),
    _return(
        PHASE_CYCLE,
        "worker_out",
        "dwc3_otg_start_peripheral",
        MODULE_RUNTIME_NAME,
    ),
    _entry(
        PHASE_CYCLE,
        "child_suspend_in",
        "dwc3_runtime_suspend",
        None,
    ),
    _return(
        PHASE_CYCLE,
        "child_suspend_out",
        "dwc3_runtime_suspend",
        None,
    ),
    _entry(
        PHASE_CYCLE,
        "child_resume_in",
        "dwc3_runtime_resume",
        None,
    ),
    _return(
        PHASE_CYCLE,
        "child_resume_out",
        "dwc3_runtime_resume",
        None,
    ),
    _entry(
        PHASE_CYCLE,
        "phy_suspend_in",
        "msm_hsphy_set_suspend",
        MODULE_HSPHY_NAME,
        " suspend=%x1:s32",
    ),
    _return(
        PHASE_CYCLE,
        "phy_suspend_out",
        "msm_hsphy_set_suspend",
        MODULE_HSPHY_NAME,
    ),
    _entry(
        PHASE_CYCLE,
        "phy_power_in",
        "msm_hsphy_enable_power",
        MODULE_HSPHY_NAME,
        " on=%x1:s32",
    ),
    _return(
        PHASE_CYCLE,
        "phy_power_out",
        "msm_hsphy_enable_power",
        MODULE_HSPHY_NAME,
    ),
    _entry(
        PHASE_CYCLE,
        "phy_init_in",
        "msm_hsphy_init",
        MODULE_HSPHY_NAME,
    ),
    _return(
        PHASE_CYCLE,
        "phy_init_out",
        "msm_hsphy_init",
        MODULE_HSPHY_NAME,
    ),
    _entry(
        PHASE_CYCLE,
        "notify_connect_in",
        "msm_hsphy_notify_connect",
        MODULE_HSPHY_NAME,
    ),
    _return(
        PHASE_CYCLE,
        "notify_connect_out",
        "msm_hsphy_notify_connect",
        MODULE_HSPHY_NAME,
    ),
    _entry(PHASE_BIND, "resume_in", "dwc3_runtime_resume", None),
    _return(PHASE_BIND, "resume_out", "dwc3_runtime_resume", None),
    _entry(
        PHASE_BIND,
        "pull_in",
        "dwc3_gadget_pullup",
        None,
        " on=%x1:s32",
    ),
    _return(PHASE_BIND, "pull_out", "dwc3_gadget_pullup", None),
    _entry(
        PHASE_BIND,
        "run_in",
        "dwc3_gadget_run_stop",
        None,
        " on=%x1:s32",
    ),
    _return(PHASE_BIND, "run_out", "dwc3_gadget_run_stop", None),
)


@dataclass(frozen=True)
class DiagnosticDetail:
    value: int
    name: str
    category: str
    outcomes: tuple[int, ...]
    stages: tuple[int, ...]

    @property
    def stage_mask(self) -> int:
        return stage_mask(self.stages)

    @property
    def macro(self) -> str:
        return "P282_DETAIL_" + self.name.upper().replace("-", "_")


def _details(
    start: int,
    rows: tuple[tuple[str, str, int, tuple[int, ...]], ...],
) -> tuple[DiagnosticDetail, ...]:
    return tuple(
        DiagnosticDetail(start + index, name, category, (outcome,), stages)
        for index, (name, category, outcome, stages) in enumerate(rows)
    )


INSTRUMENTATION_DETAILS = _details(
    0xC01,
    (
        (
            "cycle-trace-control-unavailable",
            "diagnostic-warning",
            OUTCOME_PROGRESS,
            (STOP_STAGE, SUSPENDED_STAGE, RESTART_STAGE),
        ),
        (
            "cycle-trace-registration-unavailable",
            "diagnostic-warning",
            OUTCOME_PROGRESS,
            (STOP_STAGE, SUSPENDED_STAGE, RESTART_STAGE),
        ),
        (
            "cycle-trace-incomplete",
            "diagnostic-warning",
            OUTCOME_PROGRESS,
            (STOP_STAGE, SUSPENDED_STAGE, RESTART_STAGE),
        ),
        (
            "cycle-trace-cleanup-unverified",
            "instrumentation-failure",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "cycle-trace-source-contradiction",
            "trace-source-contradiction",
            OUTCOME_FAILURE,
            (STOP_STAGE, SUSPENDED_STAGE, RESTART_STAGE),
        ),
        (
            "cycle-helper-source-contradiction",
            "helper-source-contradiction",
            OUTCOME_FAILURE,
            (STOP_STAGE, RESTART_STAGE),
        ),
    ),
)

STOP_SUSPEND_DETAILS = _details(
    0xC10,
    (
        ("none-readback-not-reached", "role-boundary", OUTCOME_FAILURE, (STOP_STAGE,)),
        ("stop-worker-not-entered", "worker-boundary", OUTCOME_FAILURE, (STOP_STAGE,)),
        ("stop-worker-no-return", "worker-boundary", OUTCOME_FAILURE, (STOP_STAGE,)),
        (
            "stop-worker-unexpected-return",
            "worker-source-contradiction",
            OUTCOME_FAILURE,
            (STOP_STAGE,),
        ),
        (
            "child-suspend-not-entered",
            "child-pm-boundary",
            OUTCOME_FAILURE,
            (SUSPENDED_STAGE,),
        ),
        (
            "child-suspend-no-return",
            "child-pm-boundary",
            OUTCOME_FAILURE,
            (SUSPENDED_STAGE,),
        ),
        ("child-suspend-negative", "child-pm-failure", OUTCOME_FAILURE, (SUSPENDED_STAGE,)),
        (
            "child-status-not-suspended",
            "child-pm-postcondition",
            OUTCOME_FAILURE,
            (SUSPENDED_STAGE,),
        ),
        (
            "suspended-power-helper-off-zero",
            "repair-progress",
            OUTCOME_PROGRESS,
            (SUSPENDED_STAGE,),
        ),
        (
            "suspended-no-power-helper-off",
            "repair-progress",
            OUTCOME_PROGRESS,
            (SUSPENDED_STAGE,),
        ),
        (
            "suspended-power-helper-off-negative",
            "repair-progress",
            OUTCOME_PROGRESS,
            (SUSPENDED_STAGE,),
        ),
    ),
)

RESTART_DETAILS = _details(
    0xC20,
    (
        (
            "peripheral-readback-not-reached",
            "role-boundary",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        ("start-worker-not-entered", "worker-boundary", OUTCOME_FAILURE, (RESTART_STAGE,)),
        ("start-worker-no-return", "worker-boundary", OUTCOME_FAILURE, (RESTART_STAGE,)),
        (
            "start-worker-unexpected-return",
            "worker-source-contradiction",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "child-resume-not-entered-after-suspend",
            "child-pm-boundary",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        ("child-resume-no-return", "child-pm-boundary", OUTCOME_FAILURE, (RESTART_STAGE,)),
        (
            "femto-init-not-entered-in-resume",
            "phy-init-boundary",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "femto-power-on-not-entered-in-init",
            "phy-power-boundary",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        ("femto-power-on-negative", "phy-power-failure", OUTCOME_FAILURE, (RESTART_STAGE,)),
        ("femto-init-negative", "phy-init-failure", OUTCOME_FAILURE, (RESTART_STAGE,)),
        (
            "child-resume-negative-after-init",
            "child-pm-failure",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "hsphy-notify-connect-missing",
            "phy-connect-boundary",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "child-status-not-active",
            "child-pm-postcondition",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "parent-mode-not-peripheral",
            "role-postcondition",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "exact-udc-regression-after-restart",
            "udc-postcondition",
            OUTCOME_FAILURE,
            (RESTART_STAGE,),
        ),
        (
            "reinit-power-helper-off-on-zero",
            "repair-progress",
            OUTCOME_PROGRESS,
            (RESTART_STAGE,),
        ),
        (
            "reinit-software-only",
            "repair-progress",
            OUTCOME_PROGRESS,
            (RESTART_STAGE,),
        ),
    ),
)

BIND_FINAL_DETAILS = _details(
    0xC40,
    (
        (
            "helper-off-on-zero-direct-run-stop",
            "bind-progress",
            OUTCOME_PROGRESS,
            (BIND_STAGE,),
        ),
        (
            "helper-off-on-zero-resume-run-stop",
            "bind-progress",
            OUTCOME_PROGRESS,
            (BIND_STAGE,),
        ),
        ("software-direct-run-stop", "bind-progress", OUTCOME_PROGRESS, (BIND_STAGE,)),
        ("software-resume-run-stop", "bind-progress", OUTCOME_PROGRESS, (BIND_STAGE,)),
        ("degraded-direct-run-stop", "bind-progress", OUTCOME_PROGRESS, (BIND_STAGE,)),
        ("degraded-resume-run-stop", "bind-progress", OUTCOME_PROGRESS, (BIND_STAGE,)),
        (
            "bind-diagnostic-branch-unknown",
            "diagnostic-warning",
            OUTCOME_PROGRESS,
            (BIND_STAGE,),
        ),
        (
            "bind-pullup-zero-without-run-stop",
            "pullup-boundary",
            OUTCOME_FAILURE,
            (BIND_STAGE,),
        ),
        ("nested-run-stop-negative", "run-stop-failure", OUTCOME_FAILURE, (BIND_STAGE,)),
        (
            "bind-trace-source-contradiction",
            "trace-source-contradiction",
            OUTCOME_FAILURE,
            (BIND_STAGE,),
        ),
        (
            "bind-trace-cleanup-unverified",
            "instrumentation-failure",
            OUTCOME_FAILURE,
            (BIND_STAGE,),
        ),
        (
            "final-state-speed-unstable",
            "final-pair-instability",
            OUTCOME_FAILURE,
            (FINAL_STAGE,),
        ),
    ),
)

DIAGNOSTIC_DETAILS = (
    *INSTRUMENTATION_DETAILS,
    *STOP_SUSPEND_DETAILS,
    *RESTART_DETAILS,
    *BIND_FINAL_DETAILS,
)
INHERITED_DIAGNOSTIC_DETAILS = p280.DIAGNOSTIC_DETAILS
ALL_DIAGNOSTIC_DETAILS = (
    *INHERITED_DIAGNOSTIC_DETAILS,
    *DIAGNOSTIC_DETAILS,
)
DETAIL_BY_VALUE = {detail.value: detail for detail in DIAGNOSTIC_DETAILS}
DETAIL_VALUES = tuple(detail.value for detail in DIAGNOSTIC_DETAILS)


class RepairClass(IntEnum):
    POWER_HELPER_OFF_ON_ZERO = 0
    SOFTWARE_REINIT = 1
    DIAGNOSTIC_DEGRADED = 2


class BindClass(IntEnum):
    DIRECT_RUN_STOP = 0
    RESUME_NESTED_RUN_STOP = 1
    DIAGNOSTIC_DEGRADED = 2


CANONICAL_UDC_STATES = (
    "not attached",
    "attached",
    "powered",
    "default",
    "addressed",
    "configured",
    "reconnecting",
    "unauthenticated",
    "suspended",
)
CANONICAL_SPEEDS = (
    "UNKNOWN",
    "low-speed",
    "full-speed",
    "high-speed",
    "wireless",
    "super-speed",
    "super-speed-plus",
)
UDC_STATES = CANONICAL_UDC_STATES
USB_SPEEDS = CANONICAL_SPEEDS
STATE_CONFIGURED = CANONICAL_UDC_STATES.index("configured")
SPEED_HIGH = CANONICAL_SPEEDS.index("high-speed")
TUPLE_BASE = 0xD00
TUPLE_COUNT = (
    len(RepairClass) * len(BindClass)
    * len(CANONICAL_UDC_STATES) * len(CANONICAL_SPEEDS)
)
TUPLE_MAX = TUPLE_BASE + TUPLE_COUNT - 1
TUPLE_FIRST = TUPLE_BASE
TUPLE_LAST = TUPLE_MAX


@dataclass(frozen=True)
class TupleValue:
    repair: RepairClass
    bind: BindClass
    state_index: int
    speed_index: int

    @property
    def state(self) -> str:
        return CANONICAL_UDC_STATES[self.state_index]

    @property
    def speed(self) -> str:
        return CANONICAL_SPEEDS[self.speed_index]

    @property
    def outcome(self) -> int:
        if self.state == "configured" and self.speed == "high-speed":
            return OUTCOME_PROGRESS
        return OUTCOME_FAILURE


def encode_tuple(
    repair: int | RepairClass,
    bind: int | BindClass,
    state: int | str,
    speed: int | str,
) -> int:
    try:
        repair_value = RepairClass(repair)
        bind_value = BindClass(bind)
        state_index = (
            CANONICAL_UDC_STATES.index(state)
            if isinstance(state, str)
            else int(state)
        )
        speed_index = (
            CANONICAL_SPEEDS.index(speed)
            if isinstance(speed, str)
            else int(speed)
        )
    except (ValueError, TypeError) as exc:
        raise SpecError("P2.82 tuple input is outside its descriptor") from exc
    if not 0 <= state_index < len(CANONICAL_UDC_STATES):
        raise SpecError("P2.82 tuple state is outside its descriptor")
    if not 0 <= speed_index < len(CANONICAL_SPEEDS):
        raise SpecError("P2.82 tuple speed is outside its descriptor")
    return TUPLE_BASE + (
        (
            (int(repair_value) * len(BindClass) + int(bind_value))
            * len(CANONICAL_UDC_STATES)
            + state_index
        )
        * len(CANONICAL_SPEEDS)
        + speed_index
    )


def decode_tuple(value: int) -> TupleValue:
    if not TUPLE_BASE <= value <= TUPLE_MAX:
        raise SpecError("detail is outside the P2.82 final tuple domain")
    remainder = value - TUPLE_BASE
    speed_index = remainder % len(CANONICAL_SPEEDS)
    remainder //= len(CANONICAL_SPEEDS)
    state_index = remainder % len(CANONICAL_UDC_STATES)
    remainder //= len(CANONICAL_UDC_STATES)
    bind = BindClass(remainder % len(BindClass))
    repair = RepairClass(remainder // len(BindClass))
    return TupleValue(repair, bind, state_index, speed_index)


def tuple_values() -> tuple[int, ...]:
    return tuple(range(TUPLE_BASE, TUPLE_MAX + 1))


def stage_mask(stages: tuple[int, ...]) -> int:
    mask = 0
    for stage in stages:
        try:
            bit = (
                ROLE_UDC_STAGE,
                STOP_STAGE,
                SUSPENDED_STAGE,
                RESTART_STAGE,
                BIND_STAGE,
                FINAL_STAGE,
                TERMINAL_STAGE,
            ).index(stage)
        except ValueError as exc:
            raise SpecError(
                f"stage 0x{stage:02x} has no P2.82 exact-mask bit"
            ) from exc
        mask |= 1 << bit
    return mask


STAGE_EXACT_MASKS = {
    detail.value: detail.stage_mask for detail in DIAGNOSTIC_DETAILS
}
DEFAULT_STAGE_EXACT_MASKS = dict(STAGE_EXACT_MASKS)


@dataclass(frozen=True)
class ClassifierFixture:
    detail: int
    function: str
    fields: tuple[tuple[str, int], ...]
    stage: int
    outcome: int


def _fixture(
    value: int,
    function: str,
    fields: dict[str, int],
    *,
    stage: int | None = None,
) -> ClassifierFixture:
    detail = DETAIL_BY_VALUE[value]
    selected_stage = detail.stages[0] if stage is None else stage
    return ClassifierFixture(
        value,
        function,
        tuple(fields.items()),
        selected_stage,
        detail.outcomes[0],
    )


CLASSIFIER_FIXTURES = (
    *(
        _fixture(
            value,
            "p282_classify_cycle_control",
            {"condition": value - 0xC00},
        )
        for value in range(0xC01, 0xC07)
    ),
    _fixture(0xC10, "p282_classify_stop", {"none_readback": 0}),
    _fixture(0xC11, "p282_classify_stop", {"worker_entered": 0}),
    _fixture(0xC12, "p282_classify_stop", {"worker_returned": 0}),
    _fixture(0xC13, "p282_classify_stop", {"worker_rc": -1}),
    _fixture(0xC14, "p282_classify_suspend", {"suspend_entered": 0}),
    _fixture(0xC15, "p282_classify_suspend", {"suspend_returned": 0}),
    _fixture(0xC16, "p282_classify_suspend", {"suspend_rc": -1}),
    _fixture(0xC17, "p282_classify_suspend", {"status_suspended": 0}),
    _fixture(0xC18, "p282_classify_suspend", {}),
    _fixture(0xC19, "p282_classify_suspend", {"power_off_entered": 0}),
    _fixture(0xC1A, "p282_classify_suspend", {"power_off_rc": -1}),
    _fixture(0xC20, "p282_classify_restart", {"peripheral_readback": 0}),
    _fixture(0xC21, "p282_classify_restart", {"worker_entered": 0}),
    _fixture(0xC22, "p282_classify_restart", {"worker_returned": 0}),
    _fixture(0xC23, "p282_classify_restart", {"worker_rc": -1}),
    _fixture(0xC24, "p282_classify_restart", {"resume_entered": 0}),
    _fixture(0xC25, "p282_classify_restart", {"resume_returned": 0}),
    _fixture(0xC26, "p282_classify_restart", {"init_entered": 0}),
    _fixture(0xC27, "p282_classify_restart", {"power_on_entered": 0}),
    _fixture(0xC28, "p282_classify_restart", {"power_on_rc": -1}),
    _fixture(0xC29, "p282_classify_restart", {"init_rc": -1}),
    _fixture(0xC2A, "p282_classify_restart", {"resume_rc": -1}),
    _fixture(0xC2B, "p282_classify_restart", {"notify_connect": 0}),
    _fixture(0xC2C, "p282_classify_restart", {"status_active": 0}),
    _fixture(0xC2D, "p282_classify_restart", {"mode_peripheral": 0}),
    _fixture(0xC2E, "p282_classify_restart", {"exact_udc": 0}),
    _fixture(0xC2F, "p282_classify_restart", {}),
    _fixture(0xC30, "p282_classify_restart", {"off_on_zero_pair": 0}),
    _fixture(
        0xC40,
        "p282_classify_bind",
        {"repair_class": int(RepairClass.POWER_HELPER_OFF_ON_ZERO)},
    ),
    _fixture(
        0xC41,
        "p282_classify_bind",
        {
            "repair_class": int(RepairClass.POWER_HELPER_OFF_ON_ZERO),
            "bind_branch": int(BindClass.RESUME_NESTED_RUN_STOP),
        },
    ),
    _fixture(
        0xC42,
        "p282_classify_bind",
        {"repair_class": int(RepairClass.SOFTWARE_REINIT)},
    ),
    _fixture(
        0xC43,
        "p282_classify_bind",
        {
            "repair_class": int(RepairClass.SOFTWARE_REINIT),
            "bind_branch": int(BindClass.RESUME_NESTED_RUN_STOP),
        },
    ),
    _fixture(
        0xC44,
        "p282_classify_bind",
        {"repair_class": int(RepairClass.DIAGNOSTIC_DEGRADED)},
    ),
    _fixture(
        0xC45,
        "p282_classify_bind",
        {
            "repair_class": int(RepairClass.DIAGNOSTIC_DEGRADED),
            "bind_branch": int(BindClass.RESUME_NESTED_RUN_STOP),
        },
    ),
    _fixture(
        0xC46,
        "p282_classify_bind",
        {
            "repair_class": int(RepairClass.DIAGNOSTIC_DEGRADED),
            "bind_branch": int(BindClass.DIAGNOSTIC_DEGRADED),
        },
    ),
    _fixture(0xC47, "p282_classify_bind", {"run_stop_seen": 0}),
    _fixture(
        0xC48,
        "p282_classify_bind",
        {
            "bind_branch": int(BindClass.RESUME_NESTED_RUN_STOP),
            "run_stop_rc": -1,
        },
    ),
    _fixture(0xC49, "p282_classify_bind", {"source_consistent": 0}),
    _fixture(0xC4A, "p282_classify_bind", {"cleanup_verified": 0}),
    _fixture(
        0xC4B,
        "p282_classify_final_pair",
        {"second_speed": 1},
    ),
)


RUNTIME_AUTHORITY_ITEMS = (
    *tuple(
        (
            name,
            value.replace("p280", "p282")
            if isinstance(value, str)
            else value,
        )
        for name, value in p280.RUNTIME_AUTHORITY_ITEMS
    ),
    (
        "userspace_parent_role_cycle_scope",
        "exactly-one-none-write-and-one-peripheral-write-before-one-udc-bind",
    ),
    ("userspace_parent_role_write_count", 2),
    ("direct_power_clock_reset_mmio_authority", False),
    ("host_role_authority", False),
)
RUNTIME_AUTHORITY = dict(RUNTIME_AUTHORITY_ITEMS)
SAFETY_USERSPACE_WRITE_SCOPE = (
    "source-contract-bound-p282-prebind-child-reinit-and-e3-acm"
)
SAFETY_USB_SCOPE = (
    "bounded-prebind-none-peripheral-cycle-configfs-cdc-acm-banner"
)

RUNTIME_EXTERNAL_CONSTANTS = (
    ("P282_NR_UNLINKAT", 35),
    ("P282_NR_UMOUNT2", 39),
    ("P282_AT_REMOVEDIR", 0x200),
    ("P282_O_WRONLY", 0o00000001),
    ("P282_O_TRUNC", 0o00001000),
    ("P282_S_IFREG", 0o100000),
    ("P282_TRACEFS_MAGIC", 0x74726163),
    ("P282_TRACE_CAPACITY", 64 * 1024),
    ("P282_PROFILE_CAPACITY", 64 * 1024),
    ("P282_DEFINITIONS_CAPACITY", 32 * 1024),
    ("P282_PATH_CAPACITY", 256),
    ("P282_RECORD_CAPACITY", 64),
    ("P282_HELPER_MAGIC", 0x50323830),
    ("P282_HELPER_VERSION", 1),
    ("P282_HELPER_OPERATION_ROLE_WRITE", 1),
    ("P282_HELPER_OPERATION_NONE_WRITE", 2),
    ("P282_HELPER_OPERATION_PERIPHERAL_WRITE", 3),
    ("P282_CYCLE_DEADLINE_SEC", CYCLE_DEADLINE_SEC),
    ("P282_FINAL_DEADLINE_SEC", FINAL_DEADLINE_SEC),
    ("P282_POLL_INTERVAL_MSEC", POLL_INTERVAL_MSEC),
    ("P282_PHASE_ROLE", 1),
    ("P282_PHASE_CYCLE", 2),
    ("P282_PHASE_BIND", 3),
)

RUNTIME_STRING_CONSTANTS = (
    ("P282_PARENT_MODE_PATH", PARENT_MODE_PATH),
    ("P282_CHILD_RUNTIME_STATUS_PATH", CHILD_RUNTIME_STATUS_PATH),
    ("P282_EXACT_UDC_PATH", EXACT_UDC_PATH),
    ("P282_UDC_STATE_PATH", UDC_STATE_PATH),
    ("P282_UDC_SPEED_PATH", UDC_SPEED_PATH),
    ("P282_ROLE_NONE_WRITE", ROLE_NONE_WRITE),
    ("P282_ROLE_PERIPHERAL_WRITE", ROLE_PERIPHERAL_WRITE),
    ("P282_ROLE_NONE_READBACK", ROLE_NONE_READBACK),
    ("P282_ROLE_PERIPHERAL_READBACK", ROLE_PERIPHERAL_READBACK),
    ("P282_CHILD_SUSPENDED_READBACK", CHILD_SUSPENDED_READBACK),
    ("P282_CHILD_ACTIVE_READBACK", CHILD_ACTIVE_READBACK),
)

TRACEFS_ABSOLUTE_PATHS = (
    "/sys/kernel/tracing",
    "/sys/kernel/tracing/events/p282",
    "/sys/kernel/tracing/instances/p282",
    "/sys/kernel/tracing/instances/p282/buffer_size_kb",
    "/sys/kernel/tracing/instances/p282/events/p282/",
    "/sys/kernel/tracing/instances/p282/events/p282/enable",
    "/sys/kernel/tracing/instances/p282/trace",
    "/sys/kernel/tracing/instances/p282/trace_clock",
    "/sys/kernel/tracing/instances/p282/tracing_on",
    "/sys/kernel/tracing/kprobe_events",
    "/sys/kernel/tracing/kprobe_profile",
)

RUNTIME_OPERATION_TOKENS = (
    *tuple(
        (
            name,
            token.replace("p280", "p282").replace("P280", "P282"),
            count,
        )
        for name, token, count in p280.RUNTIME_OPERATION_TOKENS
    ),
    ("parent-mode-none-write", "P282_ROLE_NONE_WRITE", 1),
    (
        "parent-mode-peripheral-write",
        "P282_ROLE_PERIPHERAL_WRITE",
        1,
    ),
    ("parent-mode-host-write", '"host\\n"', 0),
    ("cycle-trace-setup", "p282_trace_setup(P282_PHASE_CYCLE", 1),
    ("cycle-trace-cleanup", "p282_trace_cleanup(", 2),
    (
        "cycle-none-helper-operation",
        "p282_run_cycle_role_helper(\n"
        "        P282_HELPER_OPERATION_NONE_WRITE,",
        1,
    ),
    (
        "cycle-peripheral-helper-operation",
        "p282_run_cycle_role_helper(\n"
        "        P282_HELPER_OPERATION_PERIPHERAL_WRITE,",
        1,
    ),
    (
        "restart-failure-stage",
        "p282_emit(\n"
        "        &classification,\n"
        "        P282_STAGE_RESTART,",
        1,
    ),
    ("udc-bind-once", "p260_bind_udc();", 1),
    ("banner-write-once", "p260_write_banner(tty_fd);", 1),
)


def events_for_phase(phase: str) -> tuple[TraceEvent, ...]:
    events = tuple(event for event in TRACE_EVENTS if event.phase == phase)
    if not events:
        raise SpecError(f"unknown P2.82 phase: {phase}")
    return events


def all_details() -> tuple[object, ...]:
    return ALL_DIAGNOSTIC_DETAILS


def detail_name(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    if detail:
        return detail.name
    if TUPLE_BASE <= value <= TUPLE_MAX:
        decoded = decode_tuple(value)
        return (
            f"final-{decoded.repair.name.lower().replace('_', '-')}-"
            f"{decoded.bind.name.lower().replace('_', '-')}-"
            f"{decoded.state.replace(' ', '-')}-{decoded.speed.lower()}"
        )
    return p280.detail_name(value)


def detail_kind(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    if detail:
        return detail.category
    if TUPLE_BASE <= value <= TUPLE_MAX:
        decoded = decode_tuple(value)
        return (
            "final-tuple-progress"
            if decoded.outcome == OUTCOME_PROGRESS
            else "final-tuple-failure"
        )
    return p280.detail_kind(value)


def detail_allowed(stage: int, outcome: int, value: int) -> bool:
    detail = DETAIL_BY_VALUE.get(value)
    if detail is not None:
        return stage in detail.stages and outcome in detail.outcomes
    if TUPLE_BASE <= value <= TUPLE_MAX:
        decoded = decode_tuple(value)
        return stage == FINAL_STAGE and outcome == decoded.outcome
    if stage in tuple(step.stage for step in P280_PREFIX_STEPS):
        return p280.detail_allowed(stage, outcome, value)
    try:
        step = step_for_stage(stage)
    except SpecError:
        return False
    if step.kind != KIND_LOCAL or outcome != OUTCOME_FAILURE:
        return False
    if p280.p260.DETAIL_ERRNO_MIN <= value <= p280.p260.DETAIL_ERRNO_MAX:
        return True
    encoded_index = value & 0xFF
    if encoded_index >= GATE_COUNT:
        return False
    return (
        p280.p260.DETAIL_REGRESSION_BASE
        <= value
        <= p280.p260.DETAIL_REGRESSION_MAX
        or p280.p260.DETAIL_READ_ERROR_BASE
        <= value
        <= p280.p260.DETAIL_READ_ERROR_MAX
    )


def ordinal_for_stage(
    stage: int, steps: tuple[Step, ...] = STEPS
) -> int:
    for ordinal, step in enumerate(steps):
        if step.stage == stage:
            return ordinal
    raise SpecError(f"stage 0x{stage:02x} is outside the P2.82 contract")


def step_for_stage(
    stage: int, steps: tuple[Step, ...] = STEPS
) -> Step:
    return steps[ordinal_for_stage(stage, steps)]


def expected_item(stage: int) -> int:
    return step_for_stage(stage).item_index


def failure_detail_allowed(step: Step, value: int) -> bool:
    return detail_allowed(step.stage, OUTCOME_FAILURE, value)


def failure_details(step: Step) -> tuple[int, ...]:
    inherited = ()
    if step.stage in tuple(value.stage for value in P280_PREFIX_STEPS):
        inherited = p280.failure_details(step)
    exact = tuple(
        detail.value
        for detail in DIAGNOSTIC_DETAILS
        if detail_allowed(step.stage, OUTCOME_FAILURE, detail.value)
    )
    tuples = (
        tuple(
            value
            for value in tuple_values()
            if detail_allowed(step.stage, OUTCOME_FAILURE, value)
        )
        if step.stage == FINAL_STAGE
        else ()
    )
    return inherited + exact + tuples


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    ordinal = ordinal_for_stage(stage)
    step = STEPS[ordinal]
    if generation != ordinal + 1:
        raise SpecError("slot generation does not match the stage ordinal")
    if item_index != step.item_index:
        raise SpecError("slot item index does not match the descriptor")
    if step.kind == KIND_TERMINAL:
        if outcome != OUTCOME_SUCCESS or detail != 0:
            raise SpecError("terminal slot must be zero-detail success")
        return
    if outcome == OUTCOME_PROGRESS and detail == 0:
        return
    if not detail_allowed(stage, outcome, detail):
        raise SpecError("nonterminal outcome or detail is outside P2.82")


def render_classifier_contract_c() -> str:
    lines = (
        "#ifndef S22PLUS_FYG8_P282_CLASSIFIER_CONTRACT_GENERATED_H",
        "#define S22PLUS_FYG8_P282_CLASSIFIER_CONTRACT_GENERATED_H",
        "#define P282_CLASSIFIER_CONTRACT_DEFINED 1",
        f"#define P282_OUTCOME_PROGRESS {OUTCOME_PROGRESS}U",
        f"#define P282_OUTCOME_FAILURE {OUTCOME_FAILURE}U",
        f"#define P282_STAGE_ROLE_UDC 0x{ROLE_UDC_STAGE:02x}U",
        f"#define P282_STAGE_STOP 0x{STOP_STAGE:02x}U",
        f"#define P282_STAGE_SUSPENDED 0x{SUSPENDED_STAGE:02x}U",
        f"#define P282_STAGE_RESTART 0x{RESTART_STAGE:02x}U",
        f"#define P282_STAGE_BIND 0x{BIND_STAGE:02x}U",
        f"#define P282_STAGE_FINAL 0x{FINAL_STAGE:02x}U",
        f"#define P282_STAGE_TERMINAL 0x{TERMINAL_STAGE:02x}U",
        f"#define P282_TUPLE_BASE 0x{TUPLE_BASE:03x}U",
        f"#define P282_TUPLE_MAX 0x{TUPLE_MAX:03x}U",
        f"#define P282_REPAIR_COUNT {len(RepairClass)}U",
        f"#define P282_BIND_COUNT {len(BindClass)}U",
        f"#define P282_STATE_COUNT {len(CANONICAL_UDC_STATES)}U",
        f"#define P282_SPEED_COUNT {len(CANONICAL_SPEEDS)}U",
        f"#define P282_STATE_CONFIGURED {STATE_CONFIGURED}U",
        f"#define P282_SPEED_HIGH {SPEED_HIGH}U",
    )
    generated = list(lines)
    for detail in DIAGNOSTIC_DETAILS:
        generated.extend(
            (
                f"#define {detail.macro} 0x{detail.value:03x}U",
                f"#define {detail.macro}_OUTCOME {detail.outcomes[0]}U",
                f"#define {detail.macro}_STAGE_MASK "
                f"0x{detail.stage_mask:02x}U",
            )
        )
    generated.extend(("#endif", ""))
    return "\n".join(generated)


def validate() -> None:
    if len(STEPS) != 92 or TERMINAL_ORDINAL != 91:
        raise SpecError("P2.82 descriptor must end at generation 92")
    if steps_prefix := STEPS[: len(P280_PREFIX_STEPS)]:
        if steps_prefix != P280_PREFIX_STEPS:
            raise SpecError("P2.82 P2.80 prefix changed")
    if tuple(step.stage for step in STEPS[-6:]) != (
        STOP_STAGE,
        SUSPENDED_STAGE,
        RESTART_STAGE,
        BIND_STAGE,
        FINAL_STAGE,
        TERMINAL_STAGE,
    ):
        raise SpecError("P2.82 local stage sequence changed")
    if len(DIAGNOSTIC_DETAILS) != 46:
        raise SpecError("P2.82 must define exactly 46 C-band details")
    if len(DETAIL_BY_VALUE) != len(DIAGNOSTIC_DETAILS):
        raise SpecError("P2.82 diagnostic values are not unique")
    expected_values = (
        *range(0xC01, 0xC07),
        *range(0xC10, 0xC1B),
        *range(0xC20, 0xC31),
        *range(0xC40, 0xC4C),
    )
    if DETAIL_VALUES != expected_values:
        raise SpecError("P2.82 C-band detail domain changed")
    if len(CLASSIFIER_FIXTURES) != 46:
        raise SpecError("P2.82 classifier fixture count changed")
    if {fixture.detail for fixture in CLASSIFIER_FIXTURES} != set(
        DETAIL_VALUES
    ):
        raise SpecError("P2.82 classifier fixtures are not exhaustive")
    if TUPLE_COUNT != 567 or (TUPLE_BASE, TUPLE_MAX) != (0xD00, 0xF36):
        raise SpecError("P2.82 final tuple geometry changed")
    if len(set(tuple_values())) != 567:
        raise SpecError("P2.82 final tuples are not unique")
    if DEFAULT_STAGE_EXACT_MASKS != STAGE_EXACT_MASKS:
        raise SpecError("P2.82 default exact masks drifted")
    if STAGE_EXACT_MASKS[0xC06] != stage_mask(
        (STOP_STAGE, RESTART_STAGE)
    ):
        raise SpecError("P2.82 c06 exact non-contiguous mask changed")
    if tuple(event.name for event in events_for_phase(PHASE_CYCLE)) != (
        "worker_in",
        "worker_out",
        "child_suspend_in",
        "child_suspend_out",
        "child_resume_in",
        "child_resume_out",
        "phy_suspend_in",
        "phy_suspend_out",
        "phy_power_in",
        "phy_power_out",
        "phy_init_in",
        "phy_init_out",
        "notify_connect_in",
        "notify_connect_out",
    ):
        raise SpecError("P2.82 cycle trace order changed")
    if tuple(event.name for event in events_for_phase(PHASE_ROLE)) != (
        "start_in",
        "parent_pm_out",
        "child_pm_out",
        "start_out",
    ):
        raise SpecError("P2.82 initial role trace order changed")
    if tuple(
        event.post_call_ordinal
        for event in events_for_phase(PHASE_ROLE)
    ) != (None, 0, 1, None):
        raise SpecError("P2.82 initial role post-call ordinals changed")
    if len(events_for_phase(PHASE_BIND)) != 6:
        raise SpecError("P2.82 bind trace event count changed")
    if RUNTIME_AUTHORITY != dict(RUNTIME_AUTHORITY_ITEMS):
        raise SpecError("P2.82 runtime authority map changed")
    if len(RUNTIME_AUTHORITY) != len(RUNTIME_AUTHORITY_ITEMS):
        raise SpecError("P2.82 runtime authority keys are duplicated")
    if len(dict(RUNTIME_EXTERNAL_CONSTANTS)) != len(
        RUNTIME_EXTERNAL_CONSTANTS
    ):
        raise SpecError("P2.82 runtime constants are not unique")
    if len(dict(RUNTIME_STRING_CONSTANTS)) != len(
        RUNTIME_STRING_CONSTANTS
    ):
        raise SpecError("P2.82 runtime strings are not unique")
    if len(set(TRACEFS_ABSOLUTE_PATHS)) != len(TRACEFS_ABSOLUTE_PATHS):
        raise SpecError("P2.82 trace paths are not unique")
    for detail in DIAGNOSTIC_DETAILS:
        for stage in detail.stages:
            if not detail_allowed(stage, detail.outcomes[0], detail.value):
                raise SpecError("P2.82 detail self-validation failed")
        for stage in (
            STOP_STAGE,
            SUSPENDED_STAGE,
            RESTART_STAGE,
            BIND_STAGE,
            FINAL_STAGE,
        ):
            expected = stage in detail.stages
            actual = detail_allowed(stage, detail.outcomes[0], detail.value)
            if actual != expected:
                raise SpecError("P2.82 exact stage mask broadened")
    for value in tuple_values():
        decoded = decode_tuple(value)
        if encode_tuple(
            decoded.repair,
            decoded.bind,
            decoded.state_index,
            decoded.speed_index,
        ) != value:
            raise SpecError("P2.82 tuple round-trip failed")


validate()
