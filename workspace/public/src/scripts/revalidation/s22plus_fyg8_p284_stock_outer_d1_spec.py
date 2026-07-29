#!/usr/bin/env python3
"""Frozen design constants for the P2.84 stock outer-work D1 discriminator.

This module is data and pure classification logic only.  It performs no
device contact and grants no live authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import s22plus_fyg8_p282_contract_spec as p282


SCHEMA = "s22plus_fyg8_p284_stock_outer_d1_spec_v1"
PROFILE = p282.PROFILE
TARGET = p282.TARGET
TRACE_GROUP = "p284stock"
TRACE_INSTANCE = "p284stock"
TRACE_BUFFER_KB = 128
TRACE_CLOCK = "mono"
LANE_WRITER_COMM = "p284-lane"

PARENT_MODE_PATH = p282.PARENT_MODE_PATH
CHILD_RUNTIME_STATUS_PATH = p282.CHILD_RUNTIME_STATUS_PATH
ROLE_NONE_WRITE = "none\n"
ROLE_PERIPHERAL_WRITE = "peripheral\n"
CHILD_SUSPENDED_READBACK = "suspended"
CHILD_ACTIVE_READBACK = "active"
POLL_INTERVAL_MSEC = p282.POLL_INTERVAL_MSEC

DWC3_MSM_MODULE_RUNTIME_NAME = p282.DWC3_MSM_MODULE_RUNTIME_NAME
HSPHY_MODULE_RUNTIME_NAME = p282.HSPHY_MODULE_RUNTIME_NAME
EXACT_DWC3_MSM_SHA256 = p282.EXACT_DWC3_MSM_SHA256
EXACT_HSPHY_SHA256 = p282.EXACT_HSPHY_SHA256

DWC3_MSM_SUSPEND_SYMBOL_VALUE = 0x8EF0
DWC3_MSM_SUSPEND_SYMBOL_SIZE = 0x73C

# Each marker is the first instruction after the named boundary.  The offsets
# are pinned to the exact FYG8 dwc3-msm.ko above, not inferred from source
# helper names.  All are four-byte AArch64 instruction boundaries.
PARENT_SUSPEND_BOUNDARY_OFFSETS = MappingProxyType(
    {
        "parent_mutex_acquired": 0x044,
        "parent_perf_cancel_done": 0x064,
        "parent_prepare_done": 0x13C,
        "parent_irq_disabled": 0x144,
        "parent_hsphy_done": 0x180,
        "parent_ssphy_done": 0x2E0,
        "parent_clocks_done": 0x358,
        "parent_gdsc_done": 0x3E4,
        "parent_bus_vote_done": 0x3F0,
        "parent_wake_irq_done": 0x610,
        "parent_mutex_released": 0x680,
    }
)

# Little-endian AArch64 instruction words at the marker sites.  These pin the
# offsets to the exact module body and catch accidental reuse with another
# binary even when a symbol name survives.
PARENT_SUSPEND_BOUNDARY_WORDS = MappingProxyType(
    {
        "parent_mutex_acquired": 0x910EA288,
        "parent_perf_cancel_done": 0xB943D288,
        "parent_prepare_done": 0xB941E680,
        "parent_irq_disabled": 0xAA1403E0,
        "parent_hsphy_done": 0x394D4288,
        "parent_ssphy_done": 0xD5033E9F,
        "parent_clocks_done": 0x394D4288,
        "parent_gdsc_done": 0xAA1403E0,
        "parent_bus_vote_done": 0xB943AE82,
        "parent_wake_irq_done": 0xF9400280,
        "parent_mutex_released": 0x2A1F03F6,
    }
)

# Ranked diagnostic priority for the eight source-level synchronous
# boundaries.  This is not a root-cause verdict: a probe at each corresponding
# completion marker is still required.  The exact source and binary demote the
# perf-work cancellation because it uses system_wq, an earlier cancellation in
# the already-proven stop helper returned, and no enable occurs in between.
PARENT_SUSPEND_BOUNDARY_RANKING = (
    (
        1,
        "suspend_resume_mutex",
        "parent_mutex_acquired",
        "unbounded acquisition dominates the entry-to-post-lock interval",
    ),
    (
        2,
        "disable_irq(PWR_EVNT_IRQ)",
        "parent_irq_disabled",
        "synchronous IRQ drain has no local deadline",
    ),
    (
        3,
        "clock disable/rate framework",
        "parent_clocks_done",
        "provider and framework lock waits are not locally bounded",
    ),
    (
        4,
        "GDSC/regulator collapse",
        "parent_gdsc_done",
        "framework waits may block although the GDSC poll itself is bounded",
    ),
    (
        5,
        "interconnect bandwidth votes",
        "parent_bus_vote_done",
        "RPMh waits have a 10-second timeout; write returns error, batch BUGs",
    ),
    (
        6,
        "HS/SS PHY suspend callbacks",
        "parent_hsphy_done,parent_ssphy_done",
        "both callbacks are repeated already-suspended fast-return paths",
    ),
    (
        7,
        "cancel_delayed_work_sync(perf_vote_work)",
        "parent_perf_cancel_done",
        "system_wq work was already synchronously cancelled with no re-enable",
    ),
    (
        8,
        "wake IRQ setup",
        "parent_wake_irq_done",
        "the exact stopped state skips this mode-conditional block",
    ),
)

ROLE_WRITE_RETURN_DEADLINE_SEC = 15
CHILD_SUSPENDED_DEADLINE_SEC = 15
CONTROL_OUTER_RETURN_DEADLINE_SEC = 15
RECOVERY_WATCHDOG_DEADLINE_SEC = 20
FINAL_HEALTH_DEADLINE_SEC = 240
REACTION_MARGIN_MULTIPLIER = 4
MIN_INTERVENTION_MARGIN_NS = 10_000_000


@dataclass(frozen=True)
class TraceEvent:
    phase: str
    name: str
    probe_kind: str
    symbol: str
    module: str | None
    fetch: str = ""
    offset: int | None = None

    @property
    def post_call_ordinal(self) -> None:
        """Compatibility with the generic attachment-name gate."""

        return None

    def target(self) -> str:
        symbol = self.symbol
        if self.offset is not None:
            symbol = f"{symbol}+0x{self.offset:x}"
        return f"{self.module}:{symbol}" if self.module else symbol

    def definition(self, _offsets: tuple[int, int] | None = None) -> str:
        prefix = "r" if self.probe_kind == "return" else "p"
        return (
            f"{prefix}:{TRACE_GROUP}/{self.name} {self.target()}"
            f"{self.fetch}\n"
        )


@dataclass(frozen=True)
class ModeStoreCaller:
    """Caller identity parsed from a mode_store entry trace header."""

    pid: int
    comm: str


def _entry(
    phase: str,
    name: str,
    symbol: str,
    module: str | None,
    fetch: str = "",
    offset: int | None = None,
) -> TraceEvent:
    return TraceEvent(
        phase=phase,
        name=name,
        probe_kind="entry",
        symbol=symbol,
        module=module,
        fetch=fetch,
        offset=offset,
    )


def _return(
    phase: str,
    name: str,
    symbol: str,
    module: str | None,
    fetch: str = "",
) -> TraceEvent:
    return TraceEvent(
        phase=phase,
        name=name,
        probe_kind="return",
        symbol=symbol,
        module=module,
        fetch=fetch,
    )


TRACE_EVENTS = (
    _entry("writer", "mode_store_in", "mode_store", DWC3_MSM_MODULE_RUNTIME_NAME),
    _return(
        "writer",
        "mode_store_out",
        "mode_store",
        DWC3_MSM_MODULE_RUNTIME_NAME,
        " rc=$retval:s64",
    ),
    _entry(
        "outer",
        "outer_sm_work_in",
        "dwc3_otg_sm_work",
        DWC3_MSM_MODULE_RUNTIME_NAME,
    ),
    _return(
        "outer",
        "outer_sm_work_out",
        "dwc3_otg_sm_work",
        DWC3_MSM_MODULE_RUNTIME_NAME,
    ),
    _entry(
        "stop",
        "stop_peripheral_in",
        "dwc3_otg_start_peripheral",
        DWC3_MSM_MODULE_RUNTIME_NAME,
        " on=%x1:s32",
    ),
    _return(
        "stop",
        "stop_peripheral_out",
        "dwc3_otg_start_peripheral",
        DWC3_MSM_MODULE_RUNTIME_NAME,
        " rc=$retval:s32",
    ),
    _entry("child", "child_suspend_in", "dwc3_runtime_suspend", None),
    _return(
        "child",
        "child_suspend_out",
        "dwc3_runtime_suspend",
        None,
        " rc=$retval:s32",
    ),
    _entry(
        "phy",
        "phy_suspend_in",
        "msm_hsphy_set_suspend",
        HSPHY_MODULE_RUNTIME_NAME,
        " suspend=%x1:s32",
    ),
    _return(
        "phy",
        "phy_suspend_out",
        "msm_hsphy_set_suspend",
        HSPHY_MODULE_RUNTIME_NAME,
        " rc=$retval:s32",
    ),
    _entry(
        "phy",
        "phy_power_in",
        "msm_hsphy_enable_power",
        HSPHY_MODULE_RUNTIME_NAME,
        " on=%x1:s32",
    ),
    _return(
        "phy",
        "phy_power_out",
        "msm_hsphy_enable_power",
        HSPHY_MODULE_RUNTIME_NAME,
        " rc=$retval:s32",
    ),
    _entry(
        "parent",
        "parent_runtime_suspend_in",
        "dwc3_msm_runtime_suspend",
        DWC3_MSM_MODULE_RUNTIME_NAME,
    ),
    _return(
        "parent",
        "parent_runtime_suspend_out",
        "dwc3_msm_runtime_suspend",
        DWC3_MSM_MODULE_RUNTIME_NAME,
        " rc=$retval:s32",
    ),
    _entry(
        "parent",
        "parent_suspend_in",
        "dwc3_msm_suspend",
        DWC3_MSM_MODULE_RUNTIME_NAME,
    ),
    _return(
        "parent",
        "parent_suspend_out",
        "dwc3_msm_suspend",
        DWC3_MSM_MODULE_RUNTIME_NAME,
        " rc=$retval:s32",
    ),
    *tuple(
        _entry(
            "parent-boundary",
            name,
            "dwc3_msm_suspend",
            DWC3_MSM_MODULE_RUNTIME_NAME,
            offset=offset,
        )
        for name, offset in PARENT_SUSPEND_BOUNDARY_OFFSETS.items()
    ),
)


def challenge_eligibility(
    *,
    none_dispatch_ns: int,
    child_suspended_observed_ns: int,
    outer_return_ns: int,
    measured_reaction_ns: int,
) -> dict[str, Any]:
    """Classify whether the control exposed a reproducible overlap window.

    ``measured_reaction_ns`` is the control-lane upper bound from the exact
    suspended-read completion point to entry in the expected ``mode_store``.
    Trace data is used here only after the control lane has completed.
    """

    values = (
        none_dispatch_ns,
        child_suspended_observed_ns,
        outer_return_ns,
        measured_reaction_ns,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("challenge timing inputs must be integer nanoseconds")
    if any(value < 0 for value in values):
        raise ValueError("challenge timing inputs must be nonnegative")
    if child_suspended_observed_ns < none_dispatch_ns:
        raise ValueError("child observation precedes NONE dispatch")
    if outer_return_ns < none_dispatch_ns:
        raise ValueError("outer return precedes NONE dispatch")

    none_to_outer_ns = outer_return_ns - none_dispatch_ns
    overlap_window_ns = outer_return_ns - child_suspended_observed_ns
    required_margin_ns = max(
        MIN_INTERVENTION_MARGIN_NS,
        REACTION_MARGIN_MULTIPLIER * measured_reaction_ns,
    )
    if overlap_window_ns <= 0:
        reason = "CONTROL_OUTER_RETURNED_BEFORE_REACTOR_READY"
        eligible = False
    elif overlap_window_ns < required_margin_ns:
        reason = "CONTROL_WINDOW_TOO_SHORT"
        eligible = False
    else:
        reason = "CONTROL_WINDOW_INTERVENTION_CAPABLE"
        eligible = True

    return {
        "eligible": eligible,
        "reason": reason,
        "none_to_outer_ns": none_to_outer_ns,
        "overlap_window_ns": overlap_window_ns,
        "measured_reaction_ns": measured_reaction_ns,
        "required_margin_ns": required_margin_ns,
    }


def classify_mode_store_callers(
    callers: tuple[ModeStoreCaller, ...],
    *,
    expected_writer_pid: int,
    expected_writer_comm: str,
) -> dict[str, Any]:
    """Detect a mode-store caller outside the one lane-owned writer.

    Tracefs text carries both ``comm`` and ``common_pid`` in each event header.
    The lane binds both fields before its first role write.  Any other pair is
    Android-framework interference and makes that lane no-proof.
    """

    if (
        isinstance(expected_writer_pid, bool)
        or not isinstance(expected_writer_pid, int)
        or expected_writer_pid <= 0
    ):
        raise ValueError("expected writer PID must be positive")
    if expected_writer_comm != LANE_WRITER_COMM:
        raise ValueError("expected writer comm is not the frozen lane identity")
    for caller in callers:
        if not isinstance(caller, ModeStoreCaller):
            raise ValueError("mode_store callers must be ModeStoreCaller values")
        if (
            isinstance(caller.pid, bool)
            or not isinstance(caller.pid, int)
            or caller.pid <= 0
        ):
            raise ValueError("mode_store caller PIDs must be positive")
        if not isinstance(caller.comm, str) or not caller.comm:
            raise ValueError("mode_store caller comm values must be nonempty")
    external = tuple(
        caller
        for caller in callers
        if (
            caller.pid != expected_writer_pid
            or caller.comm != expected_writer_comm
        )
    )
    return {
        "expected_writer_pid": expected_writer_pid,
        "expected_writer_comm": expected_writer_comm,
        "call_count": len(callers),
        "external_writer_observed": bool(external),
        "external_call_count": len(external),
        "external_callers": tuple(
            {"pid": caller.pid, "comm": caller.comm}
            for caller in external
        ),
    }


def validate_static_spec() -> None:
    if set(PARENT_SUSPEND_BOUNDARY_OFFSETS) != set(
        PARENT_SUSPEND_BOUNDARY_WORDS
    ):
        raise ValueError("parent boundary offset/word inventories differ")
    offsets = tuple(PARENT_SUSPEND_BOUNDARY_OFFSETS.values())
    if (
        len(offsets) != len(set(offsets))
        or any(offset % 4 for offset in offsets)
        or any(not 0 < offset < DWC3_MSM_SUSPEND_SYMBOL_SIZE for offset in offsets)
    ):
        raise ValueError("parent boundary offsets are not unique in-body instructions")
    names = tuple(event.name for event in TRACE_EVENTS)
    if len(names) != len(set(names)):
        raise ValueError("trace event names are not unique")
    if not LANE_WRITER_COMM or len(LANE_WRITER_COMM.encode("ascii")) > 15:
        raise ValueError("lane writer comm does not fit TASK_COMM_LEN")
    ranking = PARENT_SUSPEND_BOUNDARY_RANKING
    if tuple(item[0] for item in ranking) != tuple(range(1, 9)):
        raise ValueError("parent boundary ranks are not exactly 1..8")
    known_markers = set(PARENT_SUSPEND_BOUNDARY_OFFSETS)
    for _, _, marker_csv, _ in ranking:
        if not set(marker_csv.split(",")).issubset(known_markers):
            raise ValueError("ranked parent boundary lacks an exact marker")
    if not (
        CONTROL_OUTER_RETURN_DEADLINE_SEC
        < RECOVERY_WATCHDOG_DEADLINE_SEC
        < FINAL_HEALTH_DEADLINE_SEC
    ):
        raise ValueError("D1 time bounds are not nested")
    stage_deadlines = (
        ROLE_WRITE_RETURN_DEADLINE_SEC,
        CHILD_SUSPENDED_DEADLINE_SEC,
        CONTROL_OUTER_RETURN_DEADLINE_SEC,
    )
    if any(
        deadline <= 0 or deadline >= RECOVERY_WATCHDOG_DEADLINE_SEC
        for deadline in stage_deadlines
    ):
        raise ValueError("a D1 stage bound does not precede recovery")


validate_static_spec()
