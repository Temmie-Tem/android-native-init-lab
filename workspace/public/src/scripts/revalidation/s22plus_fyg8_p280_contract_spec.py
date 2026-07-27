#!/usr/bin/env python3
"""Single-source P2.80 diagnostic, event, and stage contract."""

from __future__ import annotations

from dataclasses import dataclass

import s22plus_fyg8_p260_contract_spec as p260


SCHEMA = "s22plus_fyg8_p280_contract_spec_v1"
PROFILE = p260.PROFILE
TARGET = p260.TARGET

Step = p260.Step
SpecError = p260.SpecError

KIND_LOCAL = p260.KIND_LOCAL
KIND_TERMINAL = p260.KIND_TERMINAL

STEPS = p260.STEPS
STAGE_SEQUENCE = p260.STAGE_SEQUENCE
TERMINAL_STAGE = p260.TERMINAL_STAGE
TERMINAL_ORDINAL = p260.TERMINAL_ORDINAL
GATE_COUNT = p260.GATE_COUNT

ROLE_UDC_STAGE = p260.ROLE_UDC_STAGE
UDC_BIND_STAGE = p260.UDC_BIND_STAGE
CONFIGURED_STAGE = p260.CONFIGURED_STAGE

OUTCOME_PROGRESS = p260.p258.p257.p248.model.OUTCOME_PROGRESS
OUTCOME_FAILURE = p260.p258.p257.p248.model.OUTCOME_FAILURE
OUTCOME_SUCCESS = p260.p258.p257.p248.model.OUTCOME_SUCCESS

PHASE_ROLE = "role"
PHASE_BIND = "bind"
TRACE_GROUP = "p280"
TRACE_INSTANCE = "p280"
TRACE_BUFFER_KB = 64
ROLE_DEADLINE_SEC = 30
TRACE_CONTROL_ALLOWANCE_SEC = 15

MODULE_RUNTIME_NAME = "dwc3_msm"
PARENT_SYMBOL = "dwc3_otg_start_peripheral"
PM_CALLEE = "__pm_runtime_resume"
EXACT_DWC3_MSM_SHA256 = (
    "8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1"
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
                raise SpecError("P2.80 post-call offsets are unavailable")
            offset = offsets[self.post_call_ordinal]
            symbol = f"{symbol}+0x{offset:x}"
        return f"{self.module}:{symbol}" if self.module else symbol

    def definition(self, offsets: tuple[int, int] | None = None) -> str:
        prefix = "r" if self.probe_kind == "return" else "p"
        return (
            f"{prefix}:{TRACE_GROUP}/{self.name} {self.target(offsets)}"
            f"{self.fetch}\n"
        )


TRACE_EVENTS = (
    TraceEvent(
        PHASE_ROLE,
        "start_in",
        "entry",
        PARENT_SYMBOL,
        MODULE_RUNTIME_NAME,
        " on=%x1:s32",
        "on == 1",
    ),
    TraceEvent(
        PHASE_ROLE,
        "parent_pm_out",
        "entry",
        PARENT_SYMBOL,
        MODULE_RUNTIME_NAME,
        " rc=%x0:s32",
        "1",
        post_call_ordinal=0,
    ),
    TraceEvent(
        PHASE_ROLE,
        "child_pm_out",
        "entry",
        PARENT_SYMBOL,
        MODULE_RUNTIME_NAME,
        " rc=%x0:s32",
        "1",
        post_call_ordinal=1,
    ),
    TraceEvent(
        PHASE_ROLE,
        "start_out",
        "return",
        PARENT_SYMBOL,
        MODULE_RUNTIME_NAME,
        " rc=$retval:s32",
        "1",
    ),
    TraceEvent(
        PHASE_BIND,
        "resume_in",
        "entry",
        "dwc3_runtime_resume",
        None,
        "",
        "common_pid == 1",
    ),
    TraceEvent(
        PHASE_BIND,
        "resume_out",
        "return",
        "dwc3_runtime_resume",
        None,
        " rc=$retval:s32",
        "common_pid == 1",
    ),
    TraceEvent(
        PHASE_BIND,
        "pull_in",
        "entry",
        "dwc3_gadget_pullup",
        None,
        " on=%x1:s32",
        "common_pid == 1",
    ),
    TraceEvent(
        PHASE_BIND,
        "pull_out",
        "return",
        "dwc3_gadget_pullup",
        None,
        " rc=$retval:s32",
        "common_pid == 1",
    ),
    TraceEvent(
        PHASE_BIND,
        "run_in",
        "entry",
        "dwc3_gadget_run_stop",
        None,
        " on=%x1:s32",
        "common_pid == 1",
    ),
    TraceEvent(
        PHASE_BIND,
        "run_out",
        "return",
        "dwc3_gadget_run_stop",
        None,
        " rc=$retval:s32",
        "common_pid == 1",
    ),
)


@dataclass(frozen=True)
class DiagnosticDetail:
    value: int
    name: str
    category: str
    outcomes: tuple[int, ...]
    stages: tuple[int, ...]
    required_phase: str | None = None
    canonical_states: tuple[str, ...] = ()


DIAGNOSTIC_DETAILS = (
    DiagnosticDetail(
        0xB01,
        "trace-control-unavailable",
        "diagnostic-warning",
        (OUTCOME_PROGRESS,),
        (ROLE_UDC_STAGE, UDC_BIND_STAGE, CONFIGURED_STAGE),
    ),
    DiagnosticDetail(
        0xB02,
        "trace-registration-unavailable",
        "diagnostic-warning",
        (OUTCOME_PROGRESS,),
        (ROLE_UDC_STAGE, UDC_BIND_STAGE, CONFIGURED_STAGE),
    ),
    DiagnosticDetail(
        0xB03,
        "bind-trace-incomplete",
        "diagnostic-warning",
        (OUTCOME_PROGRESS,),
        (UDC_BIND_STAGE, CONFIGURED_STAGE),
        required_phase=PHASE_BIND,
    ),
    DiagnosticDetail(
        0xB04,
        "trace-cleanup-unverified",
        "instrumentation-failure",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE, UDC_BIND_STAGE),
    ),
    DiagnosticDetail(
        0xB10,
        "initial-role-peripheral",
        "role-model-contradiction",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
    ),
    DiagnosticDetail(
        0xB11,
        "initial-role-host",
        "unsafe-role-contradiction",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
    ),
    DiagnosticDetail(
        0xB12,
        "role-write-pre-start-timeout",
        "role-boundary",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB13,
        "role-write-returned-no-start",
        "role-boundary",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB14,
        "parent-start-no-return",
        "parent-worker-boundary",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB15,
        "parent-runtime-pm-negative",
        "runtime-pm-failure",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB16,
        "child-runtime-pm-negative",
        "runtime-pm-failure",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB17,
        "role-trace-source-contradiction",
        "trace-source-contradiction",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB18,
        "role-worker-quiescence-unproved",
        "instrumentation-failure",
        (OUTCOME_FAILURE,),
        (ROLE_UDC_STAGE,),
        required_phase=PHASE_ROLE,
    ),
    DiagnosticDetail(
        0xB20,
        "pullup-zero-without-run-stop",
        "pullup-boundary",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        required_phase=PHASE_BIND,
        canonical_states=("not attached",),
    ),
    DiagnosticDetail(
        0xB21,
        "nested-run-stop-failure-swallowed",
        "run-stop-boundary",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        required_phase=PHASE_BIND,
        canonical_states=("not attached",),
    ),
    DiagnosticDetail(
        0xB22,
        "run-stop-zero-no-bus-state",
        "electrical-boundary",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        required_phase=PHASE_BIND,
        canonical_states=("not attached",),
    ),
    DiagnosticDetail(
        0xB23,
        "udc-attached-or-powered",
        "usb-bus-progress",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        canonical_states=("attached", "powered"),
    ),
    DiagnosticDetail(
        0xB24,
        "udc-default",
        "usb-bus-progress",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        canonical_states=("default",),
    ),
    DiagnosticDetail(
        0xB25,
        "udc-addressed",
        "usb-bus-progress",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        canonical_states=("addressed",),
    ),
    DiagnosticDetail(
        0xB26,
        "udc-late-nonconfigured-state",
        "usb-bus-progress",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        canonical_states=("reconnecting", "unauthenticated", "suspended"),
    ),
    DiagnosticDetail(
        0xB27,
        "not-attached-without-clean-bind-trace",
        "diagnostic-incomplete",
        (OUTCOME_FAILURE,),
        (CONFIGURED_STAGE,),
        canonical_states=("not attached",),
    ),
)

DETAIL_BY_VALUE = {detail.value: detail for detail in DIAGNOSTIC_DETAILS}
DETAIL_VALUES = tuple(detail.value for detail in DIAGNOSTIC_DETAILS)
CANONICAL_UDC_STATES = tuple(
    dict.fromkeys(
        state
        for detail in DIAGNOSTIC_DETAILS
        for state in detail.canonical_states
    )
)


RUNTIME_AUTHORITY_ITEMS = (
    (
        "userspace_tracefs_mount_scope",
        "source-contract-bound-p280-mount-if-absent-owned-unmount-only"
    ),
    (
        "userspace_tracefs_global_event_scope",
        (
            "source-contract-bound-p280-exact-group-event-register-readback-"
            "and-remove"
        ),
    ),
    (
        "userspace_tracefs_instance_control_scope",
        (
            "source-contract-bound-p280-isolated-instance-create-remove-"
            "filter-enable-clock-buffer-trace-and-tracing-on"
        ),
    ),
    (
        "dynamic_kernel_text_instrumentation_scope",
        "standard-tracefs-kprobe-events-at-exact-source-bound-sites",
    ),
    ("no_global_tracer_or_global_buffer_reset", True),
)
RUNTIME_AUTHORITY = dict(RUNTIME_AUTHORITY_ITEMS)


def events_for_phase(phase: str) -> tuple[TraceEvent, ...]:
    events = tuple(event for event in TRACE_EVENTS if event.phase == phase)
    if not events:
        raise SpecError(f"unknown P2.80 phase: {phase}")
    return events


def detail_name(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    return detail.name if detail else p260.detail_name(value)


def detail_kind(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    return detail.category if detail else p260.detail_kind(value)


def detail_allowed(stage: int, outcome: int, value: int) -> bool:
    detail = DETAIL_BY_VALUE.get(value)
    if detail is None:
        try:
            step = p260.step_for_stage(stage)
        except SpecError:
            return False
        return (
            outcome == OUTCOME_FAILURE
            and p260.failure_detail_allowed(step, value)
        )
    return stage in detail.stages and outcome in detail.outcomes


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    ordinal = p260.ordinal_for_stage(stage)
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
        raise SpecError("nonterminal outcome or detail is outside P2.80")


def validate() -> None:
    p260.validate_steps()
    if len(DETAIL_BY_VALUE) != len(DIAGNOSTIC_DETAILS):
        raise SpecError("P2.80 diagnostic values are not unique")
    if any(not 0xB00 < value < 0xC00 for value in DETAIL_VALUES):
        raise SpecError("P2.80 diagnostic value escaped its explicit band")
    if tuple(event.name for event in events_for_phase(PHASE_ROLE)) != (
        "start_in",
        "parent_pm_out",
        "child_pm_out",
        "start_out",
    ):
        raise SpecError("P2.80 role event order changed")
    if tuple(event.name for event in events_for_phase(PHASE_BIND)) != (
        "resume_in",
        "resume_out",
        "pull_in",
        "pull_out",
        "run_in",
        "run_out",
    ):
        raise SpecError("P2.80 bind event order changed")
    if RUNTIME_AUTHORITY != dict(RUNTIME_AUTHORITY_ITEMS):
        raise SpecError("P2.80 runtime authority map changed")
    for detail in DIAGNOSTIC_DETAILS:
        for stage in detail.stages:
            p260.step_for_stage(stage)
            for outcome in detail.outcomes:
                if not detail_allowed(stage, outcome, detail.value):
                    raise SpecError("P2.80 detail self-validation failed")


validate()
