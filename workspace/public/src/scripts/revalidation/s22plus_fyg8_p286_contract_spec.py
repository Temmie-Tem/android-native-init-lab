#!/usr/bin/env python3
"""P2.86 parent-quiescence and bounded restart contract."""

from __future__ import annotations

from dataclasses import replace

from s22plus_fyg8_p284_contract_spec import *  # noqa: F403
import s22plus_fyg8_p284_contract_spec as p284


SCHEMA = "s22plus_fyg8_p286_contract_spec_v1"

PARENT_RUNTIME_STATUS_PATH = (
    "/sys/devices/platform/soc/a600000.ssusb/power/runtime_status"
)
PARENT_SUSPENDED_READBACK = "suspended"
REAP_DEADLINE_MSEC = 1000

TRACE_EVENTS = tuple(
    replace(
        event,
        name={
            "worker_in": "start_peripheral_in",
            "worker_out": "start_peripheral_out",
        }.get(event.name, event.name),
    )
    for event in p284.TRACE_EVENTS
) + (
    p284.p282._entry(  # noqa: SLF001
        PHASE_CYCLE,  # noqa: F405
        "outer_sm_work_in",
        "dwc3_otg_sm_work",
        DWC3_MSM_MODULE_RUNTIME_NAME,  # noqa: F405
    ),
    p284.p282._return(  # noqa: SLF001
        PHASE_CYCLE,  # noqa: F405
        "outer_sm_work_out",
        "dwc3_otg_sm_work",
        DWC3_MSM_MODULE_RUNTIME_NAME,  # noqa: F405
    ),
)


def _p286_details():
    rows = (
        (
            "parent-status-not-suspended",
            "parent-pm-postcondition",
            OUTCOME_FAILURE,  # noqa: F405
            (SUSPENDED_STAGE,),  # noqa: F405
        ),
        (
            "parent-status-read-error",
            "parent-pm-read-error",
            OUTCOME_FAILURE,  # noqa: F405
            (SUSPENDED_STAGE,),  # noqa: F405
        ),
        (
            "helper-dispatch-failed",
            "helper-dispatch",
            OUTCOME_FAILURE,  # noqa: F405
            (STOP_STAGE, RESTART_STAGE),  # noqa: F405
        ),
        (
            "helper-unreaped",
            "helper-reap",
            OUTCOME_FAILURE,  # noqa: F405
            (STOP_STAGE, RESTART_STAGE),  # noqa: F405
        ),
        (
            "helper-completion-malformed",
            "helper-completion",
            OUTCOME_FAILURE,  # noqa: F405
            (STOP_STAGE, RESTART_STAGE),  # noqa: F405
        ),
        (
            "none-write-timeout",
            "none-write-boundary",
            OUTCOME_FAILURE,  # noqa: F405
            (STOP_STAGE,),  # noqa: F405
        ),
        (
            "none-write-returned-error",
            "none-write-result",
            OUTCOME_FAILURE,  # noqa: F405
            (STOP_STAGE,),  # noqa: F405
        ),
        (
            "peripheral-flush-timeout",
            "flush-boundary",
            OUTCOME_FAILURE,  # noqa: F405
            (RESTART_STAGE,),  # noqa: F405
        ),
        (
            "residual-outer-tail-timeout",
            "outer-work-boundary",
            OUTCOME_FAILURE,  # noqa: F405
            (RESTART_STAGE,),  # noqa: F405
        ),
        (
            "start-peripheral-no-return",
            "start-peripheral-boundary",
            OUTCOME_FAILURE,  # noqa: F405
            (RESTART_STAGE,),  # noqa: F405
        ),
        (
            "peripheral-write-returned-error",
            "peripheral-write-result",
            OUTCOME_FAILURE,  # noqa: F405
            (RESTART_STAGE,),  # noqa: F405
        ),
        (
            "peripheral-write-completed-readback-failed",
            "role-postcondition",
            OUTCOME_FAILURE,  # noqa: F405
            (RESTART_STAGE,),  # noqa: F405
        ),
    )
    return tuple(
        p284.DiagnosticDetail(
            0xC50 + index,
            name,
            category,
            (outcome,),
            stages,
        )
        for index, (name, category, outcome, stages) in enumerate(rows)
    )


P286_DIAGNOSTIC_DETAILS = _p286_details()
DIAGNOSTIC_DETAILS = (
    *p284.DIAGNOSTIC_DETAILS,
    *P286_DIAGNOSTIC_DETAILS,
)
ALL_DIAGNOSTIC_DETAILS = (
    *p284.INHERITED_DIAGNOSTIC_DETAILS,
    *DIAGNOSTIC_DETAILS,
)
DETAIL_BY_VALUE = {detail.value: detail for detail in DIAGNOSTIC_DETAILS}
DETAIL_VALUES = tuple(detail.value for detail in DIAGNOSTIC_DETAILS)
STAGE_EXACT_MASKS = {
    detail.value: detail.stage_mask for detail in DIAGNOSTIC_DETAILS
}
DEFAULT_STAGE_EXACT_MASKS = dict(STAGE_EXACT_MASKS)

RUNTIME_AUTHORITY_ITEMS = (
    *p284.RUNTIME_AUTHORITY_ITEMS,
    (
        "userspace_parent_runtime_status_gate",
        "exact-parent-suspended-on-existing-stop-deadline",
    ),
    (
        "userspace_restart_helper_reap",
        "kill-plus-bounded-wnohang-with-explicit-unreaped-failure",
    ),
)
RUNTIME_AUTHORITY = dict(RUNTIME_AUTHORITY_ITEMS)

RUNTIME_EXTERNAL_CONSTANTS = (
    *p284.RUNTIME_EXTERNAL_CONSTANTS,
    ("P286_REAP_DEADLINE_MSEC", REAP_DEADLINE_MSEC),
)
RUNTIME_STRING_CONSTANTS = (
    *p284.RUNTIME_STRING_CONSTANTS,
    ("P286_PARENT_RUNTIME_STATUS_PATH", PARENT_RUNTIME_STATUS_PATH),
    ("P286_PARENT_SUSPENDED_READBACK", PARENT_SUSPENDED_READBACK),
)
RUNTIME_OPERATION_TOKENS = (
    *tuple(
        (
            name,
            token.replace(
                "p282_run_cycle_role_helper(",
                "p286_run_cycle_role_helper(",
            ),
            count,
        )
        for name, token, count in p284.RUNTIME_OPERATION_TOKENS
    ),
    (
        "parent-runtime-suspended-wait",
        "p282_wait_exact_value(\n"
        "        P286_PARENT_RUNTIME_STATUS_PATH,\n"
        "        P286_PARENT_SUSPENDED_READBACK,",
        1,
    ),
    ("blocking-specific-child-wait4", "sys_wait4(pid, &child_status, 0)", 0),
    (
        "bounded-specific-child-reap",
        "sys_wait4(\n                            "
        "pid, &child_status, WNOHANG)",
        1,
    ),
    ("timeout-classification-before-reap", "observation->timed_out = !malformed;", 1),
    ("explicit-unreaped-classification", "observation->unreaped = 1;", 2),
    ("helper-classification-dispatch", "p286_classify_helper(", 2),
    ("parent-status-classification", "p286_classify_parent_status(", 1),
    (
        "peripheral-readback-classification",
        "p286_classify_peripheral_readback(",
        1,
    ),
    ("outer-work-state-parser", "rc = p286_outer_state(records, count, result);", 1),
    (
        "pre-dispatch-residual-outer-snapshot",
        "residual_outer_open = cycle->observed.outer_open;",
        1,
    ),
)


def events_for_phase(phase: str):  # noqa: ANN201
    events = tuple(event for event in TRACE_EVENTS if event.phase == phase)
    if not events:
        raise SpecError(f"unknown P2.86 phase: {phase}")  # noqa: F405
    return events


def all_details() -> tuple[object, ...]:
    return ALL_DIAGNOSTIC_DETAILS


def detail_name(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    return detail.name if detail is not None else p284.detail_name(value)


def detail_kind(value: int) -> str:
    detail = DETAIL_BY_VALUE.get(value)
    return detail.category if detail is not None else p284.detail_kind(value)


def detail_allowed(stage: int, outcome: int, value: int) -> bool:
    detail = DETAIL_BY_VALUE.get(value)
    if detail is not None:
        return stage in detail.stages and outcome in detail.outcomes
    return p284.detail_allowed(stage, outcome, value)


def failure_details(step):  # noqa: ANN001, ANN201
    inherited = p284.failure_details(step)
    additions = tuple(
        detail.value
        for detail in P286_DIAGNOSTIC_DETAILS
        if detail_allowed(step.stage, OUTCOME_FAILURE, detail.value)  # noqa: F405
    )
    return inherited + additions


def validate_slot(
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> None:
    ordinal = ordinal_for_stage(stage)  # noqa: F405
    step = STEPS[ordinal]  # noqa: F405
    if generation != ordinal + 1:
        raise SpecError("slot generation does not match the stage ordinal")  # noqa: F405
    if item_index != step.item_index:
        raise SpecError("slot item index does not match the descriptor")  # noqa: F405
    if step.kind == KIND_TERMINAL:  # noqa: F405
        if outcome != OUTCOME_SUCCESS or detail != 0:  # noqa: F405
            raise SpecError("terminal slot must be zero-detail success")  # noqa: F405
        return
    if outcome == OUTCOME_PROGRESS and detail == 0:  # noqa: F405
        return
    if not detail_allowed(stage, outcome, detail):
        raise SpecError("nonterminal outcome or detail is outside P2.86")  # noqa: F405


def render_classifier_contract_c() -> str:
    inherited = p284.render_classifier_contract_c()
    marker = "#endif\n"
    if not inherited.endswith(marker):
        raise SpecError("P2.84 classifier contract terminator drifted")  # noqa: F405
    additions = []
    for detail in P286_DIAGNOSTIC_DETAILS:
        additions.extend(
            (
                f"#define {detail.macro} 0x{detail.value:03x}U",
                f"#define {detail.macro}_OUTCOME {detail.outcomes[0]}U",
                f"#define {detail.macro}_STAGE_MASK "
                f"0x{detail.stage_mask:02x}U",
            )
        )
    return inherited[: -len(marker)] + "\n".join((*additions, "#endif", ""))


def validate() -> None:
    p284.validate()
    if tuple(detail.value for detail in P286_DIAGNOSTIC_DETAILS) != tuple(
        range(0xC50, 0xC5C)
    ):
        raise SpecError("P2.86 diagnostic detail domain drifted")  # noqa: F405
    if len(DETAIL_BY_VALUE) != len(DIAGNOSTIC_DETAILS):
        raise SpecError("P2.86 diagnostic values are not unique")  # noqa: F405
    cycle_names = tuple(
        event.name for event in events_for_phase(PHASE_CYCLE)  # noqa: F405
    )
    if cycle_names[:2] != (
        "start_peripheral_in",
        "start_peripheral_out",
    ) or cycle_names[-2:] != ("outer_sm_work_in", "outer_sm_work_out"):
        raise SpecError("P2.86 cycle attachment names drifted")  # noqa: F405
    attachments = {event.name: event.symbol for event in TRACE_EVENTS}
    if attachments.get("outer_sm_work_in") != "dwc3_otg_sm_work":
        raise SpecError("P2.86 outer entry is not attached to actual work")  # noqa: F405
    if attachments.get("start_peripheral_in") != (
        "dwc3_otg_start_peripheral"
    ):
        raise SpecError("P2.86 start-peripheral label drifted")  # noqa: F405
    if len(RUNTIME_AUTHORITY) != len(RUNTIME_AUTHORITY_ITEMS):
        raise SpecError("P2.86 runtime authority keys are not unique")  # noqa: F405
    if len(dict(RUNTIME_EXTERNAL_CONSTANTS)) != len(
        RUNTIME_EXTERNAL_CONSTANTS
    ):
        raise SpecError("P2.86 numeric runtime constants are not unique")  # noqa: F405
    if len(dict(RUNTIME_STRING_CONSTANTS)) != len(
        RUNTIME_STRING_CONSTANTS
    ):
        raise SpecError("P2.86 string runtime constants are not unique")  # noqa: F405


validate()
