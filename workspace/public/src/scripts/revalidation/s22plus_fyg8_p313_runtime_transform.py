#!/usr/bin/env python3
"""Materialize the P3.13 post-bind resume-cycle userspace runtime."""

from __future__ import annotations

from typing import Mapping


class TransformError(ValueError):
    pass


def _replace_exact(data: bytes, old: bytes, new: bytes, *, label: str) -> bytes:
    if data.count(old) != 1 or (new and new != old and new in data):
        raise TransformError(f"P3.13 {label} anchor differs")
    return data.replace(old, new, 1)


def _replace_between(
    data: bytes, start: bytes, end: bytes, replacement: bytes, *, label: str
) -> bytes:
    if data.count(start) != 1 or data.count(end) != 1:
        raise TransformError(f"P3.13 {label} boundary differs")
    left = data.index(start)
    right = data.index(end, left)
    return data[:left] + replacement + data[right:]


_ROLE_TABLE = b'''static const struct p282_event_descriptor p282_role_events[] = {
    {"start_in", "p:p282/start_in dwc3_msm:dwc3_otg_start_peripheral on=%x1:s32\\n", "common_pid > 0"},
    {"parent_pm_out", "p:p282/parent_pm_out dwc3_msm:dwc3_otg_start_peripheral+0x34 rc=%x0:s32\\n", "common_pid > 0"},
    {"child_pm_out", "p:p282/child_pm_out dwc3_msm:dwc3_otg_start_peripheral+0x450 rc=%x0:s32\\n", "common_pid > 0"},
    {"start_out", "r:p282/start_out dwc3_msm:dwc3_otg_start_peripheral rc=$retval:s32\\n", "common_pid > 0"},
    {"role_qscratch", "p:p282/role_qscratch dwc3_msm:dwc3_otg_start_peripheral+0x4cc rc=%x21:s32\\n", "common_pid > 0"},
};

'''


_CYCLE_TABLE = b'''static const struct p282_event_descriptor p282_cycle_events[] = {
    {"start_peripheral_in", "p:p282/start_peripheral_in dwc3_msm:dwc3_otg_start_peripheral on=%x1:s32\\n", "common_pid > 0"},
    {"start_peripheral_out", "r:p282/start_peripheral_out dwc3_msm:dwc3_otg_start_peripheral rc=$retval:s32\\n", "common_pid > 0"},
    {"child_suspend_in", "p:p282/child_suspend_in dwc3_runtime_suspend\\n", "common_pid > 0"},
    {"child_suspend_out", "r:p282/child_suspend_out dwc3_runtime_suspend rc=$retval:s32\\n", "common_pid > 0"},
    {"child_resume_in", "p:p282/child_resume_in dwc3_runtime_resume\\n", "common_pid > 0"},
    {"child_resume_out", "r:p282/child_resume_out dwc3_runtime_resume rc=$retval:s32\\n", "common_pid > 0"},
    {"phy_suspend_in", "p:p282/phy_suspend_in phy_msm_snps_hs:msm_hsphy_set_suspend suspend=%x1:s32\\n", "common_pid > 0"},
    {"phy_suspend_out", "r:p282/phy_suspend_out phy_msm_snps_hs:msm_hsphy_set_suspend rc=$retval:s32\\n", "common_pid > 0"},
    {"phy_power_in", "p:p282/phy_power_in phy_msm_snps_hs:msm_hsphy_enable_power on=%x1:s32\\n", "common_pid > 0"},
    {"phy_power_out", "r:p282/phy_power_out phy_msm_snps_hs:msm_hsphy_enable_power rc=$retval:s32\\n", "common_pid > 0"},
    {"phy_init_in", "p:p282/phy_init_in phy_msm_snps_hs:msm_hsphy_init\\n", "common_pid > 0"},
    {"phy_init_out", "r:p282/phy_init_out phy_msm_snps_hs:msm_hsphy_init rc=$retval:s32\\n", "common_pid > 0"},
    {"notify_connect_in", "p:p282/notify_connect_in phy_msm_snps_hs:msm_hsphy_notify_connect\\n", "common_pid > 0"},
    {"notify_connect_out", "r:p282/notify_connect_out phy_msm_snps_hs:msm_hsphy_notify_connect rc=$retval:s32\\n", "common_pid > 0"},
    {"outer_sm_work_in", "p:p282/outer_sm_work_in dwc3_msm:dwc3_otg_sm_work\\n", "common_pid > 0"},
    {"outer_sm_work_out", "r:p282/outer_sm_work_out dwc3_msm:dwc3_otg_sm_work rc=$retval:s32\\n", "common_pid > 0"},
    {"cycle_qscratch", "p:p282/cycle_qscratch dwc3_msm:dwc3_otg_start_peripheral+0x4cc rc=%x21:s32\\n", "common_pid > 0"},
    {"cycle_pull_in", "p:p282/cycle_pull_in dwc3_gadget_pullup on=%x1:s32\\n", "common_pid > 0"},
    {"cycle_pull_out", "r:p282/cycle_pull_out dwc3_gadget_pullup rc=$retval:s32\\n", "common_pid > 0"},
    {"cycle_run_in", "p:p282/cycle_run_in dwc3_gadget_run_stop on=%x1:s32\\n", "common_pid > 0"},
    {"cycle_run_out", "r:p282/cycle_run_out dwc3_gadget_run_stop rc=$retval:s32\\n", "common_pid > 0"},
    {"cycle_start_in", "p:p282/cycle_start_in __dwc3_gadget_start dwc=%x0:u64\\n", "common_pid > 0"},
    {"cycle_start_out", "r:p282/cycle_start_out __dwc3_gadget_start rc=$retval:s32\\n", "common_pid > 0"},
    {"cycle_state_snapshot", "p:p282/cycle_state_snapshot s22_p294_dwc3_state_snapshot link=%x0:u32 run_stop=%x1:u32 devctrlhlt=%x2:u32 coreidle=%x3:u32 prtcap=%x4:u32 susphy=%x5:u32 connect_speed=%x6:u32\\n", "common_pid > 0"},
    {"cycle_event_config", "p:p282/cycle_event_config s22_p300_dwc3_event_config_snapshot dwc=%x0:u64 evt=%x1:u64 devten=%x2:u32 gevntsiz=%x3:u32 gevntcount=%x4:u32 evt_length=%x5:u32 evt_count=%x6:u32 evt_flags=%x7:u32\\n", "common_pid > 0"},
};

'''


def transform_trace_descriptor(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b"#define P282_ROLE_EVENT_COUNT 4U\n#define P282_CYCLE_EVENT_COUNT 29U\n",
        b"#define P282_ROLE_EVENT_COUNT 5U\n#define P282_CYCLE_EVENT_COUNT 25U\n",
        label="event cardinalities",
    )
    value = _replace_between(
        value,
        b"static const struct p282_event_descriptor p282_role_events[] = {\n",
        b"static const struct p282_event_descriptor p282_cycle_events[] = {\n",
        _ROLE_TABLE,
        label="role descriptor",
    )
    value = _replace_between(
        value,
        b"static const struct p282_event_descriptor p282_cycle_events[] = {\n",
        b"static const struct p282_event_descriptor p282_bind_events[] = {\n",
        _CYCLE_TABLE,
        label="cycle descriptor",
    )
    return value


_POSITION_NAMES = b'''
#define S22_P313_POSITION_BANNER_DEFERRED 84U
#define S22_P313_POSITION_ROLE_READY 85U
#define S22_P313_POSITION_DIRECT_OBSERVER_READY 86U
#define S22_P313_POSITION_DIRECT_BIND_RETURNED 87U
#define S22_P313_POSITION_DIRECT_START_CLASSIFIED 88U
#define S22_P313_POSITION_DIRECT_FENCE_STARTED 89U
#define S22_P313_POSITION_DIRECT_FENCE_CLOSED 90U
#define S22_P313_POSITION_BRANCH_SELECTED 91U
#define S22_P313_POSITION_CYCLE_OBSERVER_READY 92U
#define S22_P313_POSITION_STOP_HELPER_RETURNED 93U
#define S22_P313_POSITION_CHILD_SUSPENDED 94U
#define S22_P313_POSITION_PARENT_SUSPENDED 95U
#define S22_P313_POSITION_STOP_CLASSIFIED 96U
#define S22_P313_POSITION_RESTART_HELPER_RETURNED 97U
#define S22_P313_POSITION_RESTART_READBACKS 98U
#define S22_P313_POSITION_RESUME_CLASSIFIED 99U
#define S22_P313_POSITION_POST_CYCLE_TUPLE 100U
#define S22_P313_POSITION_FINAL_WINDOW 101U
#define S22_P313_POSITION_TRACE_INTEGRITY 102U
#define S22_P313_POSITION_RESULT_CLASSIFIED 103U
#define S22_P313_POSITION_PAIR_READY 104U
#define S22_P313_POSITION_A_DETAIL 105U
#define S22_P313_POSITION_B_DETAIL 106U

'''


def transform_positions(data: bytes) -> bytes:
    anchor = b"#define S22_P294_POSITION_COUNT S22_P290_POSITION_COUNT\n"
    if data.count(anchor) != 1 or _POSITION_NAMES in data:
        raise TransformError("P3.13 position-name anchor differs")
    return data.replace(anchor, _POSITION_NAMES + anchor, 1)


def transform_runtime_wrapper(data: bytes) -> bytes:
    value = _replace_exact(
        data,
        b"    struct p282_trace_control p311_early_trace = {0};\n"
        b"    int p311_early_armed = 0;\n",
        b"",
        label="early trace declaration removal",
    )
    value = _replace_exact(
        value,
        b"        if (index == 55U) {\n"
        b"            long p311_begin_rc = p311_early_trace_begin(\n"
        b"                &p311_early_trace);\n"
        b"            if (p311_begin_rc != 0) p290_fail_next(p311_begin_rc);\n"
        b"            p311_early_armed = 1;\n"
        b"        }\n",
        b"",
        label="early trace arm removal",
    )
    value = _replace_exact(
        value,
        b"    if (!p311_early_armed) {\n"
        b"        p290_fail_next(P311_DETAIL_EARLY_DOMAIN_CONTRADICTION);\n"
        b"    }\n"
        b"    long p311_finish_rc = p311_early_trace_finish(\n"
        b"        &p311_early_trace);\n"
        b"    if (p311_finish_rc != 0) p290_fail_next(p311_finish_rc);\n\n",
        b"",
        label="early trace finish removal",
    )
    return value


_P313_SUPPORT = r'''

/* P3.13 post-bind same-boot resume-cycle observer. */
#define P313_ROLE_EVENT_COUNT 5U
#define P313_DIRECT_EVENT_COUNT 15U
#define P313_CYCLE_EVENT_COUNT 25U
#define P313_DIRECT_PREFIX_CLEAN 10U
#define P313_DIRECT_PREFIX_DRIFT_MAX 22U
#define P313_DIRECT_PREFIX_CONTRADICTION_MIN 23U
#define P313_CYCLE_CLEAN_RECORDS 37U
#define P313_CYCLE_DRIFT_RECORDS 45U
#define P313_A_DETAIL_BASE 0xd00U
#define P313_A_STATE_COUNT 9U
#define P313_A_SPEED_COUNT 7U
#define P313_A_CYCLE_STRIDE 63U
#define P313_NORMAL_DETAIL_BASE 0x4801U
#define P313_DIRECT_LATE_SUCCESS 0x4c01U
#define P313_DIRECT_NONBASELINE_ACTIVITY 0x4c02U
#define P313_CONTROLLER_DETAIL_BASE 0x5001U
#define P313_DRIFT_DETAIL_BASE 0x5061U
#define P313_CONTRADICTION_DETAIL_BASE 0x6701U

#define P313_DETAIL_TRACE_CONTROL_UNAVAILABLE 0x6701U
#define P313_DETAIL_TRACE_REGISTRATION_UNAVAILABLE 0x6702U
#define P313_DETAIL_TRACE_CLEANUP_UNVERIFIED 0x6703U
#define P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED 0x6704U
#define P313_DETAIL_PROFILE_RECORD_DEFICIT 0x6705U
#define P313_DETAIL_TRACE_RING_LOSS 0x6706U
#define P313_DETAIL_RECORD_FORMAT_CONTRADICTION 0x6707U
#define P313_DETAIL_ROLE_QSCRATCH_MISSING 0x6708U
#define P313_DETAIL_ROLE_QSCRATCH_DUPLICATE 0x6709U
#define P313_DETAIL_ROLE_QSCRATCH_FOREIGN_PID 0x670aU
#define P313_DETAIL_ROLE_QSCRATCH_ORDER 0x670bU
#define P313_DETAIL_ROLE_QSCRATCH_VALUE 0x670cU
#define P313_DETAIL_DIRECT_PREFIX_MULTIPLICITY 0x670dU
#define P313_DETAIL_DIRECT_TRIGGER_STATE 0x670eU
#define P313_DETAIL_DIRECT_STREAM_INTEGRITY 0x670fU
#define P313_DETAIL_DIRECT_POINTER_CONTRADICTION 0x6710U
#define P313_DETAIL_CYCLE_RECORD_OVERFLOW 0x6711U
#define P313_DETAIL_CYCLE_EVENT_MULTIPLICITY 0x6712U
#define P313_DETAIL_CYCLE_PAIRING_CONTRADICTION 0x6713U
#define P313_DETAIL_CYCLE_POSITIVE_RETURN 0x6714U
#define P313_DETAIL_CYCLE_QSCRATCH_CONTRADICTION 0x6715U
#define P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION 0x6716U
#define P313_DETAIL_CYCLE_POINTER_CONTRADICTION 0x6717U
#define P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED 0x6718U
#define P313_DETAIL_CYCLE_READBACK_CONTRADICTION 0x6719U
#define P313_DETAIL_CYCLE_UDC_BINDING_DRIFT 0x671aU
#define P313_DETAIL_CYCLE_PARENT_PM_CONTRADICTION 0x671bU
#define P313_DETAIL_CYCLE_CHILD_PM_CONTRADICTION 0x671cU
#define P313_DETAIL_CYCLE_RESUME_PRECONDITION 0x671dU
#define P313_DETAIL_CYCLE_FINAL_STATE_UNSTABLE 0x671eU
#define P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION 0x671fU
#define P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION 0x6720U

#define P313_DRIFT_PULLUP 0x01U
#define P313_DRIFT_START_QSCRATCH 0x02U
#define P313_DRIFT_OUTER_WORK 0x04U
#define P313_DRIFT_RESUME_NESTING 0x08U
#define P313_DRIFT_UDC_ROLE_DIRECT 0x10U

#define P313_EBUSY 16
#define P313_ENOMEM 12

_Static_assert(P282_ROLE_EVENT_COUNT == P313_ROLE_EVENT_COUNT,
    "P3.13 role descriptor extent");
_Static_assert(P282_BIND_EVENT_COUNT == P313_DIRECT_EVENT_COUNT,
    "P3.13 direct descriptor extent");
_Static_assert(P282_CYCLE_EVENT_COUNT == P313_CYCLE_EVENT_COUNT,
    "P3.13 cycle descriptor extent");
_Static_assert(P313_CYCLE_DRIFT_RECORDS < P282_RECORD_CAPACITY,
    "P3.13 cycle record headroom");
_Static_assert(P313_A_DETAIL_BASE + 126U - 1U <= 0xdafU,
    "P3.13 A fixed Image band");

struct p313_cycle_pair {
    uint8_t entered;
    uint8_t returned;
    long pid;
    int32_t rc;
    uint64_t entry_counter;
    uint64_t return_counter;
};

struct p313_cycle_result {
    struct p313_cycle_pair start_off;
    struct p313_cycle_pair start_on;
    struct p313_cycle_pair child_suspend;
    struct p313_cycle_pair child_resume;
    struct p313_cycle_pair phy_suspend_off;
    struct p313_cycle_pair phy_suspend_on;
    struct p313_cycle_pair power_off;
    struct p313_cycle_pair power_on;
    struct p313_cycle_pair phy_init;
    struct p313_cycle_pair notify_connect;
    struct p313_cycle_pair run_off;
    struct p313_cycle_pair run_on;
    struct p313_cycle_pair gadget_start;
    uint64_t outer_pairs;
    uint64_t pullup_pairs;
    uint64_t run_pairs;
    uint64_t gadget_start_pairs;
    uint64_t qscratch_hits;
    uint64_t state_hits;
    uint64_t config_hits;
    uint64_t total_records;
    uint64_t qscratch_counter;
    uint64_t state_counter;
    uint64_t config_counter;
    uint64_t record_hits[P313_CYCLE_EVENT_COUNT];
    uint32_t qscratch;
    uint8_t snapshot_seen;
    uint8_t event_config_seen;
    uint8_t link_state;
    uint8_t run_stop;
    uint8_t devctrlhlt;
    uint8_t coreidle;
    uint8_t prtcap;
    uint8_t susphy;
    uint8_t connect_speed;
    uint64_t event_dwc;
    uint64_t event_evt;
    uint64_t devten;
    uint64_t gevntsiz;
    uint64_t gevntcount;
    uint64_t evt_length;
    uint64_t evt_count;
    uint64_t evt_flags;
    uint8_t drift_mask;
};

static long p313_setup_detail(long rc) {
    if (rc == P282_CONTROL_TRACE_CONTROL_UNAVAILABLE)
        return P313_DETAIL_TRACE_CONTROL_UNAVAILABLE;
    if (rc == P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE)
        return P313_DETAIL_TRACE_REGISTRATION_UNAVAILABLE;
    if (rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED)
        return P313_DETAIL_TRACE_CLEANUP_UNVERIFIED;
    return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
}

static long p313_errno_bucket(int32_t rc) {
    if (rc == -ETIMEDOUT) return 0;
    if (rc == -P313_EBUSY) return 1;
    if (rc == -EINVAL) return 2;
    if (rc == -EAGAIN) return 3;
    if (rc == -EIO) return 4;
    if (rc == -ENODEV) return 5;
    if (rc == -P313_ENOMEM) return 6;
    return rc < 0 ? 7 : -P260_EPROTO;
}

static long p313_controller_detail(
    unsigned int source, int32_t rc, uint16_t *detail) {
    long bucket = p313_errno_bucket(rc);
    if (detail == NULL || source >= 10U || bucket < 0 || bucket >= 8) {
        return P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
    }
    *detail = (uint16_t)(P313_CONTROLLER_DETAIL_BASE + source * 8U
        + (unsigned int)bucket);
    return 0;
}

static long p313_a_detail(
    unsigned int cycle_attempted,
    unsigned int state,
    unsigned int speed,
    uint16_t *detail) {
    if (detail == NULL || cycle_attempted > 1U
        || state >= P313_A_STATE_COUNT || speed >= P313_A_SPEED_COUNT) {
        return P313_DETAIL_TERMINAL_DOMAIN_CONTRADICTION;
    }
    *detail = (uint16_t)(P313_A_DETAIL_BASE
        + cycle_attempted * P313_A_CYCLE_STRIDE
        + state * P313_A_SPEED_COUNT + speed);
    return 0;
}

static void p313_bypass_to_pair(void) {
    if (g_checkpoint.terminal || g_checkpoint.generation > 105U) {
        p290_fail_next(P313_DETAIL_CHECKPOINT_POSITION_CONTRADICTION);
    }
    while (g_checkpoint.generation < 105U) {
        p290_progress_position((uint8_t)g_checkpoint.generation, 0U);
    }
}

static __attribute__((noreturn)) void p313_publish_and_banner(
    int tty_fd,
    unsigned int cycle_attempted,
    unsigned int state,
    unsigned int speed,
    uint16_t terminal_detail) {
    unsigned int current_state = 0;
    unsigned int current_speed = 0;
    long read_rc = p282_read_final_pair(&current_state, &current_speed);
    if (read_rc != 0) p290_fail_next(P313_DETAIL_CYCLE_READBACK_CONTRADICTION);
    (void)state;
    (void)speed;
    uint16_t first_detail = 0;
    long rc = p313_a_detail(
        cycle_attempted, current_state, current_speed, &first_detail);
    if (rc != 0) p290_fail_next(rc);
    p313_bypass_to_pair();
    rc = p294_publish_final_pair(first_detail, terminal_detail);
    if (rc != 0) p292_park_after_checkpoint_error(rc);
    (void)p260_write_banner(tty_fd);
    p290_park_after_confirmed_publication();
}

static long p313_pair_collect(
    const struct p282_trace_record *records,
    size_t count,
    uint8_t entry_event,
    uint8_t return_event,
    int argument_kind,
    int argument_value,
    struct p313_cycle_pair *first,
    uint64_t *pair_count) {
    uint64_t pairs = 0;
    if (first != NULL) *first = (struct p313_cycle_pair){0};
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *entry = &records[index];
        if (entry->event_index != entry_event
            || !p282_record_argument_matches(
                entry, argument_kind, argument_value)) continue;
        const struct p282_trace_record *returned = NULL;
        for (size_t other = index + 1U; other < count; ++other) {
            const struct p282_trace_record *candidate = &records[other];
            if (candidate->pid != entry->pid) continue;
            if (candidate->event_index == entry_event
                && p282_record_argument_matches(
                    candidate, argument_kind, argument_value)) {
                return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
            }
            if (candidate->event_index == return_event) {
                returned = candidate;
                break;
            }
        }
        if (returned == NULL || !returned->has_rc) {
            return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
        }
        if (pairs == 0U && first != NULL) {
            *first = (struct p313_cycle_pair){
                .entered = 1U,
                .returned = 1U,
                .pid = entry->pid,
                .rc = returned->rc,
                .entry_counter = entry->counter,
                .return_counter = returned->counter,
            };
        }
        if (pairs == UINT64_MAX) return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;
        ++pairs;
    }
    *pair_count = pairs;
    return 0;
}

static int p313_counter_nested(
    const struct p313_cycle_pair *outer,
    const struct p313_cycle_pair *inner) {
    return outer->entered && outer->returned
        && inner->entered && inner->returned
        && outer->entry_counter < inner->entry_counter
        && inner->return_counter < outer->return_counter;
}

static long p313_parse_cycle(
    const struct p282_trace_control *control,
    struct p313_cycle_result *result,
    int final) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    *result = (struct p313_cycle_result){0};
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc == -P260_EOVERFLOW) return P313_DETAIL_CYCLE_RECORD_OVERFLOW;
    if (rc != 0) return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
    result->total_records = count;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index >= P313_CYCLE_EVENT_COUNT
            || result->record_hits[record->event_index] == UINT64_MAX) {
            return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;
        }
        ++result->record_hits[record->event_index];
    }

    uint64_t count_value = 0;
#define P313_PAIR(member, entry, returned, kind, value, count_target) do { \
    rc = p313_pair_collect(records, count, entry, returned, kind, value, \
        &result->member, &count_value); \
    if (rc != 0) return rc; \
    result->count_target = count_value; \
} while (0)
    P313_PAIR(start_off, 0U, 1U, 1, 0, run_pairs);
    uint64_t start_off_count = result->run_pairs;
    P313_PAIR(start_on, 0U, 1U, 1, 1, run_pairs);
    uint64_t start_on_count = result->run_pairs;
    P313_PAIR(child_suspend, 2U, 3U, 0, 0, run_pairs);
    uint64_t child_suspend_count = result->run_pairs;
    P313_PAIR(child_resume, 4U, 5U, 0, 0, run_pairs);
    uint64_t child_resume_count = result->run_pairs;
    P313_PAIR(phy_suspend_off, 6U, 7U, 2, 1, run_pairs);
    uint64_t phy_suspend_off_count = result->run_pairs;
    P313_PAIR(phy_suspend_on, 6U, 7U, 2, 0, run_pairs);
    uint64_t phy_suspend_on_count = result->run_pairs;
    P313_PAIR(power_off, 8U, 9U, 1, 0, run_pairs);
    uint64_t power_off_count = result->run_pairs;
    P313_PAIR(power_on, 8U, 9U, 1, 1, run_pairs);
    uint64_t power_on_count = result->run_pairs;
    P313_PAIR(phy_init, 10U, 11U, 0, 0, run_pairs);
    uint64_t phy_init_count = result->run_pairs;
    P313_PAIR(notify_connect, 12U, 13U, 0, 0, run_pairs);
    uint64_t notify_count = result->run_pairs;
    struct p313_cycle_pair outer_first = {0};
    rc = p313_pair_collect(records, count, 14U, 15U, 0, 0,
        &outer_first, &result->outer_pairs);
    if (rc != 0) return rc;
    struct p313_cycle_pair pull_first = {0};
    rc = p313_pair_collect(records, count, 17U, 18U, 0, 0,
        &pull_first, &result->pullup_pairs);
    if (rc != 0) return rc;
    P313_PAIR(run_off, 19U, 20U, 1, 0, run_pairs);
    uint64_t run_off_count = result->run_pairs;
    P313_PAIR(run_on, 19U, 20U, 1, 1, run_pairs);
    uint64_t run_on_count = result->run_pairs;
    result->run_pairs = run_off_count + run_on_count;
    rc = p313_pair_collect(records, count, 21U, 22U, 0, 0,
        &result->gadget_start, &result->gadget_start_pairs);
    if (rc != 0) return rc;
#undef P313_PAIR

    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index == 16U) {
            if (!record->has_rc || result->qscratch_hits == UINT64_MAX)
                return P313_DETAIL_CYCLE_QSCRATCH_CONTRADICTION;
            if (result->qscratch_hits == 0U) {
                result->qscratch = (uint32_t)record->rc;
                result->qscratch_counter = record->counter;
            }
            ++result->qscratch_hits;
        } else if (record->event_index == 23U) {
            if (!record->has_link || !record->has_run_stop
                || !record->has_devctrlhlt || !record->has_coreidle
                || !record->has_prtcap || !record->has_susphy
                || !record->has_connect_speed)
                return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
            ++result->state_hits;
            if (result->state_hits == 1U) {
                result->snapshot_seen = 1U;
                result->state_counter = record->counter;
                result->link_state = (uint8_t)record->link;
                result->run_stop = (uint8_t)record->run_stop;
                result->devctrlhlt = (uint8_t)record->devctrlhlt;
                result->coreidle = (uint8_t)record->coreidle;
                result->prtcap = (uint8_t)record->prtcap;
                result->susphy = (uint8_t)record->susphy;
                result->connect_speed = (uint8_t)record->connect_speed;
            }
        } else if (record->event_index == 24U) {
            if (!record->has_dwc || !record->has_evt || !record->has_devten
                || !record->has_gevntsiz || !record->has_gevntcount
                || !record->has_evt_length || !record->has_evt_count
                || !record->has_evt_flags)
                return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
            ++result->config_hits;
            if (result->config_hits == 1U) {
                result->event_config_seen = 1U;
                result->config_counter = record->counter;
                result->event_dwc = record->dwc;
                result->event_evt = record->evt;
                result->devten = record->devten;
                result->gevntsiz = record->gevntsiz;
                result->gevntcount = record->gevntcount;
                result->evt_length = record->evt_length;
                result->evt_count = record->evt_count;
                result->evt_flags = record->evt_flags;
            }
        }
    }

    if (start_off_count > 1U || start_on_count > 1U
        || child_suspend_count > 1U || child_resume_count > 1U
        || phy_suspend_off_count > 1U || phy_suspend_on_count > 1U
        || power_off_count > 1U || power_on_count > 1U
        || phy_init_count > 1U || notify_count > 1U)
        return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;
    if (!final) return 0;
    if (result->record_hits[0] != start_off_count + start_on_count
        || result->record_hits[1] != start_off_count + start_on_count
        || result->record_hits[2] != child_suspend_count
        || result->record_hits[3] != child_suspend_count
        || result->record_hits[4] != child_resume_count
        || result->record_hits[5] != child_resume_count
        || result->record_hits[6]
            != phy_suspend_off_count + phy_suspend_on_count
        || result->record_hits[7]
            != phy_suspend_off_count + phy_suspend_on_count
        || result->record_hits[8] != power_off_count + power_on_count
        || result->record_hits[9] != power_off_count + power_on_count
        || result->record_hits[10] != phy_init_count
        || result->record_hits[11] != phy_init_count
        || result->record_hits[12] != notify_count
        || result->record_hits[13] != notify_count
        || result->record_hits[14] != result->outer_pairs
        || result->record_hits[15] != result->outer_pairs
        || result->record_hits[16] != result->qscratch_hits
        || result->record_hits[17] != result->pullup_pairs
        || result->record_hits[18] != result->pullup_pairs
        || result->record_hits[19] != result->run_pairs
        || result->record_hits[20] != result->run_pairs
        || result->record_hits[21] != result->gadget_start_pairs
        || result->record_hits[22] != result->gadget_start_pairs
        || result->record_hits[23] != result->state_hits
        || result->record_hits[24] != result->config_hits)
        return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
    if (count != P313_CYCLE_CLEAN_RECORDS
        && count != P313_CYCLE_DRIFT_RECORDS)
        return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;
    if (start_off_count != 1U || start_on_count != 1U
        || child_suspend_count != 1U || child_resume_count != 1U
        || phy_suspend_off_count != 1U || phy_suspend_on_count != 1U
        || power_off_count != 1U || power_on_count != 1U
        || phy_init_count != 1U || notify_count != 1U)
        return P313_DETAIL_CYCLE_EVENT_MULTIPLICITY;
    if (result->start_off.rc != 0 || result->start_on.rc != 0
        || result->phy_suspend_off.rc != 0
        || result->phy_suspend_on.rc != 0
        || result->notify_connect.rc != 0)
        return P313_DETAIL_CYCLE_POSITIVE_RETURN;
    if (result->snapshot_seen
        && (result->link_state > 15U || result->run_stop > 1U
            || result->devctrlhlt > 1U || result->coreidle > 1U
            || result->prtcap > 3U || result->susphy > 1U
            || result->connect_speed > 7U))
        return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
    if (result->event_config_seen
        && (result->event_dwc == 0U || result->event_evt == 0U
            || (result->devten & 6U) != 6U
            || result->evt_length != 4096U
            || (result->gevntsiz & 0xffffU) != result->evt_length
            || result->evt_count > result->evt_length
            || (result->evt_count & 3U) != 0U
            || result->evt_flags > 1U
            || (result->gevntcount & 0xfffcU) > result->evt_length))
        return P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION;
    if (result->outer_pairs != 4U) result->drift_mask |= P313_DRIFT_OUTER_WORK;
    if (result->pullup_pairs != 0U) result->drift_mask |= P313_DRIFT_PULLUP;
    if (result->qscratch_hits != 1U || result->gadget_start_pairs != 1U
        || result->run_pairs != 2U || result->state_hits != 1U
        || result->config_hits != 1U)
        result->drift_mask |= P313_DRIFT_START_QSCRATCH;
    if (!p313_counter_nested(&result->start_off, &result->child_suspend)
        || !p313_counter_nested(&result->child_suspend, &result->run_off)
        || !p313_counter_nested(&result->start_on, &result->child_resume)
        || !p313_counter_nested(&result->child_resume, &result->phy_init)
        || !p313_counter_nested(&result->child_resume, &result->gadget_start)
        || !p313_counter_nested(&result->child_resume, &result->run_on))
        result->drift_mask |= P313_DRIFT_RESUME_NESTING;
    if (result->qscratch_hits == 1U
        && !(result->start_on.entry_counter < result->qscratch_counter
             && result->qscratch_counter < result->start_on.return_counter))
        result->drift_mask |= P313_DRIFT_RESUME_NESTING;
    if (result->state_hits == 1U && result->config_hits == 1U
        && (!(result->run_on.entry_counter < result->state_counter
              && result->state_counter < result->run_on.return_counter)
            || !(result->run_on.entry_counter < result->config_counter
                 && result->config_counter < result->run_on.return_counter)))
        result->drift_mask |= P313_DRIFT_RESUME_NESTING;
    return 0;
}

static long p313_cycle_profile_relations(
    const struct p282_trace_control *control,
    const struct p313_cycle_result *result) {
    for (size_t index = 0; index < P313_CYCLE_EVENT_COUNT; ++index) {
        if (control->profile_hits[index] < result->record_hits[index])
            return P313_DETAIL_PROFILE_RECORD_DEFICIT;
    }
    return 0;
}

static long p313_cycle_finish(
    struct p282_trace_control *control,
    struct p313_cycle_result *result) {
    long detail = p282_trace_disable(control);
    if (detail == 0) detail = p282_trace_read_snapshot(control, 1);
    if (detail == 0) detail = p313_parse_cycle(control, result, 1);
    if (detail == 0) detail = p313_cycle_profile_relations(control, result);
    if (detail == 0) detail = p300_ring_stats_clean();
    long cleanup_rc = p282_trace_cleanup(control);
    if (cleanup_rc != 0) return P313_DETAIL_TRACE_CLEANUP_UNVERIFIED;
    if (detail < 0) return P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED;
    return detail;
}

static long p313_cycle_close_partial(
    struct p282_trace_control *control,
    struct p313_cycle_result *result) {
    long detail = p282_trace_disable(control);
    if (detail == 0) detail = p282_trace_read_snapshot(control, 1);
    if (detail == 0) detail = p313_parse_cycle(control, result, 0);
    if (detail == 0) detail = p313_cycle_profile_relations(control, result);
    if (detail == 0) detail = p300_ring_stats_clean();
    long cleanup_rc = p282_trace_cleanup(control);
    if (cleanup_rc != 0) return P313_DETAIL_TRACE_CLEANUP_UNVERIFIED;
    if (detail < 0) return P313_DETAIL_TRACE_SNAPSHOT_READ_FAILED;
    return detail;
}

static __attribute__((noreturn)) void p313_cycle_fail(
    struct p282_trace_control *control, long detail) {
    long disable_rc = p282_trace_disable(control);
    long cleanup_rc = p282_trace_cleanup(control);
    if (disable_rc != 0 || cleanup_rc != 0)
        p290_fail_next(P313_DETAIL_TRACE_CLEANUP_UNVERIFIED);
    p290_fail_next(detail);
}

static __attribute__((noreturn)) void p313_cycle_terminal(
    struct p282_trace_control *control,
    int tty_fd,
    unsigned int cycle_attempted,
    uint16_t detail) {
    struct p313_cycle_result partial = {0};
    long rc = p313_cycle_close_partial(control, &partial);
    if (rc != 0) p290_fail_next(rc);
    p313_publish_and_banner(tty_fd, cycle_attempted, 0U, 0U, detail);
}

static int p313_direct_known_baseline(
    const struct p282_bind_trace_result *result) {
    int event_baseline = result->device_records == 0U
        || (result->device_records == 1U
            && result->other_device_records == 1U
            && result->other_type_mask == (1U << 2U)
            && result->first_other_info_seen
            && result->first_other_info == 3U
            && !result->unknown_subtype_seen);
    return result->prefix_records == P313_DIRECT_PREFIX_CLEAN
        && result->pullup_returned_zero
        && result->branch == P282_BIND_DIRECT
        && result->start_entered && result->start_returned
        && result->start_rc == 0 && result->ep_enable_hits == 2U
        && result->run_stop_seen && result->run_stop_rc == 0
        && result->snapshot_seen && result->event_config_seen
        && !result->reset_seen && !result->connect_done_seen
        && event_baseline;
}

static long p313_finish_direct(
    struct p282_trace_control *control,
    struct p282_bind_trace_result *result) {
    long detail = p298_finish_observer(control, result, 0);
    if (detail == 0 && result->prefix_records >=
        P313_DIRECT_PREFIX_CONTRADICTION_MIN)
        return P313_DETAIL_DIRECT_PREFIX_MULTIPLICITY;
    return detail;
}

static long p313_wait_state_window(
    long seconds,
    unsigned int *state,
    unsigned int *speed,
    int *configured_high) {
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(seconds, &deadline);
    if (rc != 0) return rc;
    *configured_high = 0;
    unsigned int previous_state = 0;
    unsigned int previous_speed = 0;
    int have_previous = 0;
    int stable = 0;
    for (;;) {
        rc = p282_read_final_pair(state, speed);
        if (rc != 0) return rc;
        stable = have_previous && previous_state == *state
            && previous_speed == *speed;
        if (*state == P282_STATE_CONFIGURED && *speed == P282_SPEED_HIGH) {
            *configured_high = 1;
            return 0;
        }
        if (p282_deadline_expired(&deadline))
            return stable ? 0 : -EAGAIN;
        previous_state = *state;
        previous_speed = *speed;
        have_previous = 1;
        p282_poll_delay();
    }
}

static long p313_expect_udc_binding(void) {
    return p260_expect_value("/config/usb_gadget/g1/UDC", p260_udc_name);
}

static long p313_wait_parent_active(
    const struct timespec64 *deadline, int *matched) {
    return p282_wait_exact_value(
        P286_PARENT_RUNTIME_STATUS_PATH, "active", deadline, matched);
}

static long p313_pair_return_domain(const struct p313_cycle_pair *pair) {
    if (!pair->entered || !pair->returned)
        return P313_DETAIL_CYCLE_PAIRING_CONTRADICTION;
    return pair->rc > 0 ? P313_DETAIL_CYCLE_POSITIVE_RETURN : 0;
}

static long p313_tuple_delta(
    const struct p282_bind_trace_result *direct,
    const struct p313_cycle_result *cycle,
    uint16_t *detail) {
    if (!direct->event_config_seen || !cycle->event_config_seen
        || direct->event_dwc == 0U || direct->event_evt == 0U
        || direct->event_dwc != cycle->event_dwc
        || direct->event_evt != cycle->event_evt)
        return P313_DETAIL_CYCLE_POINTER_CONTRADICTION;
    unsigned int mask = 0;
    if (direct->link_state != cycle->link_state) mask |= 1U << 0U;
    if (direct->coreidle != cycle->coreidle) mask |= 1U << 1U;
    if (direct->susphy != cycle->susphy) mask |= 1U << 2U;
    if (direct->connect_speed != cycle->connect_speed) mask |= 1U << 3U;
    if (((g_p313_role_qscratch >> 20U) & 1U)
        != ((cycle->qscratch >> 20U) & 1U)) mask |= 1U << 4U;
    if (((g_p313_role_qscratch >> 28U) & 1U)
        != ((cycle->qscratch >> 28U) & 1U)) mask |= 1U << 5U;
    if (direct->run_stop != cycle->run_stop
        || direct->devctrlhlt != cycle->devctrlhlt
        || direct->prtcap != cycle->prtcap) mask |= 1U << 6U;
    if (direct->devten != cycle->devten) mask |= 1U << 7U;
    if (direct->gevntsiz != cycle->gevntsiz
        || direct->evt_length != cycle->evt_length) mask |= 1U << 8U;
    if (direct->gevntcount != cycle->gevntcount
        || direct->evt_count != cycle->evt_count
        || direct->evt_flags != cycle->evt_flags) mask |= 1U << 9U;
    *detail = (uint16_t)(P313_NORMAL_DETAIL_BASE + mask);
    return 0;
}

static __attribute__((noreturn)) void p313_run(void) {
    (void)p311_early_trace_begin;
    (void)p311_early_trace_finish;
    (void)p282_cycle_stop;
    (void)p282_cycle_suspend;
    (void)p282_cycle_restart;
    (void)p282_phase_bind;
    (void)p282_wait_final_pair;
    p260_derive_identity();
    long rc = p260_mount_configfs();
    if (rc != 0) fail_at(P260_CONFIG_STAGE, 0U, rc);
    p260_progress(P260_CONFIG_STAGE);
    rc = p260_create_gadget();
    if (rc != 0) fail_at(P260_GADGET_STAGE, 0U, rc);
    p260_progress(P260_GADGET_STAGE);
    unsigned int major_number = 0;
    unsigned int minor_number = 0;
    rc = p260_wait_tty_dev(&major_number, &minor_number);
    if (rc != 0) fail_at(P260_TTY_CLASS_STAGE, 0U, rc);
    p260_progress(P260_TTY_CLASS_STAGE);
    rc = p260_prepare_tty_node(major_number, minor_number);
    int tty_fd = -1;
    if (rc == 0) rc = p260_open_raw_tty(&tty_fd);
    if (rc != 0) fail_at(P260_TTY_RAW_STAGE, 0U, rc);
    p260_progress(P260_TTY_RAW_STAGE);

    p290_progress_position(S22_P313_POSITION_BANNER_DEFERRED, 0U);
    uint16_t role_warning = 0;
    rc = p282_phase_role(&role_warning, tty_fd);
    if (rc != 0 || role_warning != 0U || !g_p313_role_qscratch_valid
        || ((g_p313_role_qscratch >> 20U) & 1U) == 0U
        || ((g_p313_role_qscratch >> 28U) & 1U) == 0U)
        p290_fail_next(rc != 0 ? rc : P313_DETAIL_ROLE_QSCRATCH_VALUE);
    p290_progress_position(S22_P313_POSITION_ROLE_READY, 0U);

    struct p282_trace_control direct_control = {0};
    rc = p282_trace_setup(P282_PHASE_BIND, &direct_control);
    if (rc != 0) p290_fail_next(p313_setup_detail(rc));
    p290_progress_position(S22_P313_POSITION_DIRECT_OBSERVER_READY, 0U);
    rc = p260_bind_udc();
    if (rc != 0) p298_fail_with_trace(&direct_control, rc);
    p290_progress_position(S22_P313_POSITION_DIRECT_BIND_RETURNED, 0U);

    rc = p282_trace_read_snapshot(&direct_control, 0);
    struct p282_bind_trace_result direct_initial = {0};
    if (rc == 0)
        rc = p300_parse_bind_stream(&direct_control, &direct_initial, 0);
    if (rc != 0 || p298_start_result_detail(&direct_initial) != 0)
        p298_fail_with_trace(&direct_control,
            rc != 0 ? rc : P313_DETAIL_DIRECT_STREAM_INTEGRITY);
    p290_progress_position(S22_P313_POSITION_DIRECT_START_CLASSIFIED, 0U);
    p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_STARTED, 0U);
    unsigned int direct_state = 0;
    unsigned int direct_speed = 0;
    int direct_configured = 0;
    rc = p313_wait_state_window(P282_FINAL_DEADLINE_SEC,
        &direct_state, &direct_speed, &direct_configured);
    if (rc != 0) p298_fail_with_trace(&direct_control, rc);
    struct p282_bind_trace_result direct = {0};
    long direct_detail = p313_finish_direct(&direct_control, &direct);
    p290_progress_position(S22_P313_POSITION_DIRECT_FENCE_CLOSED, 0U);

    uint16_t direct_terminal = 0;
    int cycle_selected = 0;
    if (direct_configured) {
        direct_terminal = P313_DIRECT_LATE_SUCCESS;
    } else if (direct_detail != 0) {
        p290_fail_next(direct_detail);
    } else if (direct.connect_done_seen) {
        direct_terminal = P313_DIRECT_LATE_SUCCESS;
    } else if (p313_direct_known_baseline(&direct)) {
        cycle_selected = 1;
    } else {
        direct_terminal = P313_DIRECT_NONBASELINE_ACTIVITY;
    }
    p290_progress_position(S22_P313_POSITION_BRANCH_SELECTED, 0U);
    if (!cycle_selected) {
        p313_publish_and_banner(
            tty_fd, 0U, direct_state, direct_speed, direct_terminal);
    }

    struct p282_trace_control cycle_control = {0};
    rc = p282_trace_setup(P282_PHASE_CYCLE, &cycle_control);
    if (rc != 0) p290_fail_next(p313_setup_detail(rc));
    p290_progress_position(S22_P313_POSITION_CYCLE_OBSERVER_READY, 0U);
    unsigned int gap_state = 0;
    unsigned int gap_speed = 0;
    rc = p282_read_final_pair(&gap_state, &gap_speed);
    if (rc != 0) p313_cycle_fail(
        &cycle_control, P313_DETAIL_CYCLE_READBACK_CONTRADICTION);
    if (gap_state != direct_state || gap_speed != direct_speed) {
        p313_cycle_terminal(&cycle_control, tty_fd, 0U,
            (uint16_t)(P313_DRIFT_DETAIL_BASE
                + P313_DRIFT_UDC_ROLE_DIRECT - 1U));
    }

    struct timespec64 stop_deadline = {0};
    rc = p282_deadline_after(P282_CYCLE_DEADLINE_SEC, &stop_deadline);
    if (rc != 0) p313_cycle_fail(
        &cycle_control, P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED);
    struct p286_helper_observation stop_helper = {0};
    rc = p286_run_cycle_role_helper(P282_HELPER_OPERATION_NONE_WRITE,
        tty_fd, &stop_deadline, &stop_helper);
    if (rc != 0 || stop_helper.timed_out || stop_helper.unreaped
        || stop_helper.malformed || !stop_helper.record_complete)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED);
    p290_progress_position(S22_P313_POSITION_STOP_HELPER_RETURNED, 0U);
    if (stop_helper.result > 0)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_POSITIVE_RETURN);
    if (stop_helper.result < 0) {
        uint16_t detail = 0;
        rc = p313_controller_detail(0U, stop_helper.result, &detail);
        if (rc != 0) p313_cycle_fail(&cycle_control, rc);
        p313_cycle_terminal(&cycle_control, tty_fd, 1U, detail);
    }
    if (p260_expect_value(P282_PARENT_MODE_PATH,
            P282_ROLE_NONE_READBACK) != 0)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_READBACK_CONTRADICTION);
    int child_suspended = 0;
    rc = p282_wait_exact_value(P282_CHILD_RUNTIME_STATUS_PATH,
        P282_CHILD_SUSPENDED_READBACK, &stop_deadline, &child_suspended);
    if (rc != 0 || !child_suspended)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_CHILD_PM_CONTRADICTION);
    p290_progress_position(S22_P313_POSITION_CHILD_SUSPENDED, 0U);
    int parent_suspended = 0;
    rc = p282_wait_exact_value(P286_PARENT_RUNTIME_STATUS_PATH,
        P286_PARENT_SUSPENDED_READBACK, &stop_deadline, &parent_suspended);
    if (rc != 0 || !parent_suspended)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_PARENT_PM_CONTRADICTION);
    p290_progress_position(S22_P313_POSITION_PARENT_SUSPENDED, 0U);
    if (p313_expect_udc_binding() != 0)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_UDC_BINDING_DRIFT);
    rc = p282_trace_read_snapshot(&cycle_control, 0);
    struct p313_cycle_result stop_result = {0};
    if (rc == 0) rc = p313_parse_cycle(&cycle_control, &stop_result, 0);
    if (rc != 0) p313_cycle_fail(&cycle_control, rc);
    if (p313_pair_return_domain(&stop_result.start_off) != 0
        || p313_pair_return_domain(&stop_result.child_suspend) != 0
        || p313_pair_return_domain(&stop_result.run_off) != 0
        || p313_pair_return_domain(&stop_result.power_off) != 0)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_POSITIVE_RETURN);
    if (stop_result.start_off.rc < 0) {
        uint16_t detail = 0;
        rc = p313_controller_detail(0U, stop_result.start_off.rc, &detail);
        if (rc != 0) p313_cycle_fail(&cycle_control, rc);
        p313_cycle_terminal(&cycle_control, tty_fd, 1U, detail);
    }
    if (stop_result.child_suspend.rc < 0 || stop_result.run_off.rc < 0
        || stop_result.power_off.rc < 0) {
        unsigned int source = stop_result.child_suspend.rc < 0 ? 1U
            : stop_result.run_off.rc < 0 ? 2U : 3U;
        int32_t negative = source == 1U ? stop_result.child_suspend.rc
            : source == 2U ? stop_result.run_off.rc : stop_result.power_off.rc;
        uint16_t detail = 0;
        rc = p313_controller_detail(source, negative, &detail);
        if (rc != 0) p313_cycle_fail(&cycle_control, rc);
        p313_cycle_terminal(&cycle_control, tty_fd, 1U, detail);
    }
    p290_progress_position(S22_P313_POSITION_STOP_CLASSIFIED, 0U);

    struct timespec64 restart_deadline = {0};
    rc = p282_deadline_after(P282_CYCLE_DEADLINE_SEC, &restart_deadline);
    if (rc != 0) p313_cycle_fail(
        &cycle_control, P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED);
    struct p286_helper_observation restart_helper = {0};
    rc = p286_run_cycle_role_helper(P282_HELPER_OPERATION_PERIPHERAL_WRITE,
        tty_fd, &restart_deadline, &restart_helper);
    if (rc != 0 || restart_helper.timed_out || restart_helper.unreaped
        || restart_helper.malformed || !restart_helper.record_complete)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_TIMEOUT_OR_UNREAPED);
    p290_progress_position(S22_P313_POSITION_RESTART_HELPER_RETURNED, 0U);
    if (restart_helper.result > 0)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_POSITIVE_RETURN);
    if (restart_helper.result < 0) {
        uint16_t detail = 0;
        rc = p313_controller_detail(4U, restart_helper.result, &detail);
        if (rc != 0) p313_cycle_fail(&cycle_control, rc);
        p313_cycle_terminal(&cycle_control, tty_fd, 1U, detail);
    }
    int child_active = 0;
    int parent_active = 0;
    rc = p282_wait_exact_value(P282_CHILD_RUNTIME_STATUS_PATH,
        P282_CHILD_ACTIVE_READBACK, &restart_deadline, &child_active);
    if (rc == 0) rc = p313_wait_parent_active(&restart_deadline, &parent_active);
    if (rc != 0 || !child_active || !parent_active
        || p260_expect_value(P282_PARENT_MODE_PATH,
            P282_ROLE_PERIPHERAL_READBACK) != 0
        || p313_expect_udc_binding() != 0)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_READBACK_CONTRADICTION);
    p290_progress_position(S22_P313_POSITION_RESTART_READBACKS, 0U);

    rc = p282_trace_read_snapshot(&cycle_control, 0);
    struct p313_cycle_result restart_result = {0};
    if (rc == 0) rc = p313_parse_cycle(&cycle_control, &restart_result, 0);
    if (rc != 0) p313_cycle_fail(&cycle_control, rc);
    const struct p313_cycle_pair *resume_pairs[] = {
        &restart_result.start_on,
        &restart_result.child_resume,
        &restart_result.phy_init,
        &restart_result.power_on,
        &restart_result.gadget_start,
        &restart_result.run_on,
    };
    for (size_t index = 0;
         index < sizeof(resume_pairs) / sizeof(resume_pairs[0]); ++index) {
        rc = p313_pair_return_domain(resume_pairs[index]);
        if (rc != 0) p313_cycle_fail(&cycle_control, rc);
    }
    if (restart_result.start_on.rc < 0) {
        uint16_t detail = 0;
        rc = p313_controller_detail(4U, restart_result.start_on.rc, &detail);
        if (rc != 0) p313_cycle_fail(&cycle_control, rc);
        p313_cycle_terminal(&cycle_control, tty_fd, 1U, detail);
    }
    int32_t resume_values[] = {
        restart_result.child_resume.rc,
        restart_result.phy_init.rc,
        restart_result.power_on.rc,
        restart_result.gadget_start.rc,
        restart_result.run_on.rc,
    };
    unsigned int resume_sources[] = {5U, 6U, 7U, 8U, 9U};
    for (size_t index = 0;
         index < sizeof(resume_values) / sizeof(resume_values[0]); ++index) {
        if (resume_values[index] < 0) {
            uint16_t detail = 0;
            rc = p313_controller_detail(
                resume_sources[index], resume_values[index], &detail);
            if (rc != 0) p313_cycle_fail(&cycle_control, rc);
            p313_cycle_terminal(&cycle_control, tty_fd, 1U, detail);
        }
    }
    p290_progress_position(S22_P313_POSITION_RESUME_CLASSIFIED, 0U);
    if (!restart_result.snapshot_seen || !restart_result.event_config_seen
        || restart_result.qscratch_hits == 0U)
        p313_cycle_fail(
            &cycle_control, P313_DETAIL_CYCLE_SNAPSHOT_CONTRADICTION);
    p290_progress_position(S22_P313_POSITION_POST_CYCLE_TUPLE, 0U);

    unsigned int final_state = 0;
    unsigned int final_speed = 0;
    int final_configured = 0;
    rc = p313_wait_state_window(P282_FINAL_DEADLINE_SEC,
        &final_state, &final_speed, &final_configured);
    if (rc != 0) p313_cycle_fail(
        &cycle_control, P313_DETAIL_CYCLE_FINAL_STATE_UNSTABLE);
    (void)final_configured;
    p290_progress_position(S22_P313_POSITION_FINAL_WINDOW, 0U);
    struct p313_cycle_result cycle = {0};
    rc = p313_cycle_finish(&cycle_control, &cycle);
    if (rc != 0) p290_fail_next(rc);
    p290_progress_position(S22_P313_POSITION_TRACE_INTEGRITY, 0U);

    uint16_t terminal_detail = 0;
    if (cycle.drift_mask != 0U) {
        terminal_detail = (uint16_t)(P313_DRIFT_DETAIL_BASE
            + cycle.drift_mask - 1U);
    } else {
        rc = p313_tuple_delta(&direct, &cycle, &terminal_detail);
        if (rc != 0) p290_fail_next(rc);
    }
    p290_progress_position(S22_P313_POSITION_RESULT_CLASSIFIED, 0U);
    p290_progress_position(S22_P313_POSITION_PAIR_READY, 0U);
    p313_publish_and_banner(
        tty_fd, 1U, final_state, final_speed, terminal_detail);
}
'''.encode("ascii")


_P313_EARLY_DECLARATIONS = b'''
#define P313_DIRECT_PREFIX_CLEAN 10U
#define P313_DIRECT_PREFIX_CONTRADICTION_MIN 23U
#define P313_DETAIL_RECORD_FORMAT_CONTRADICTION 0x6707U
#define P313_DETAIL_ROLE_QSCRATCH_MISSING 0x6708U
#define P313_DETAIL_ROLE_QSCRATCH_DUPLICATE 0x6709U
#define P313_DETAIL_ROLE_QSCRATCH_FOREIGN_PID 0x670aU
#define P313_DETAIL_ROLE_QSCRATCH_ORDER 0x670bU
#define P313_DETAIL_ROLE_QSCRATCH_VALUE 0x670cU
#define P313_DETAIL_DIRECT_PREFIX_MULTIPLICITY 0x670dU
static uint32_t g_p313_role_qscratch;
static uint8_t g_p313_role_qscratch_valid;

'''


def _extend_generic_unsigned_parser(data: bytes) -> bytes:
    anchor = b'''            if (rc == 0) {
                rc = p298_parse_unsigned_field(
                    event_end + 1, line_end, "dwc=",
                    &record.dwc, &record.has_dwc);
            }
            if (rc != 0) {
'''
    replacement = anchor[:-len(b"            if (rc != 0) {\n")] + b'''            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "evt=", &record.evt, &record.has_evt);
            }
            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "devten=", &record.devten, &record.has_devten);
            }
            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "gevntsiz=", &record.gevntsiz, &record.has_gevntsiz);
            }
            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "gevntcount=", &record.gevntcount, &record.has_gevntcount);
            }
            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "evt_length=", &record.evt_length, &record.has_evt_length);
            }
            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "evt_count=", &record.evt_count, &record.has_evt_count);
            }
            if (rc == 0) {
                rc = p298_parse_unsigned_field(event_end + 1, line_end,
                    "evt_flags=", &record.evt_flags, &record.has_evt_flags);
            }
            if (rc != 0) {
'''
    return _replace_exact(data, anchor, replacement, label="generic unsigned parser")


def _strict_role_parser(data: bytes) -> bytes:
    start = b"static long p282_parse_role_result(\n"
    end = b"static int p282_record_argument_matches(\n"
    new = r'''static long p282_parse_role_result(
    const struct p282_trace_control *control,
    struct p282_role_result *result) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc != 0) return rc;
    size_t first = count;
    for (size_t index = 0; index < count; ++index) {
        if (records[index].event_index != 0U) continue;
        if (!records[index].has_on || records[index].on != 1)
            return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
        if (first != count)
            return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
        first = index;
    }
    if (first == count) {
        *result = (struct p282_role_result){
            .classification = P282_ROLE_NO_START,
        };
        return 0;
    }
    long pid = records[first].pid;
    size_t positions[5] = {first, count, count, count, count};
    for (size_t index = first + 1U; index < count; ++index) {
        uint8_t event = records[index].event_index;
        if (event == 4U && records[index].pid != pid)
            return P313_DETAIL_ROLE_QSCRATCH_FOREIGN_PID;
        if (records[index].pid != pid) continue;
        if (event == 0U || event > 4U)
            return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
        if (positions[event] != count)
            return event == 4U
                ? P313_DETAIL_ROLE_QSCRATCH_DUPLICATE
                : P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
        positions[event] = index;
    }
    if (positions[3] == count) {
        *result = (struct p282_role_result){
            .classification = P282_ROLE_START_NO_RETURN,
            .pid = pid,
        };
        return 0;
    }
    if (positions[4] == count) return P313_DETAIL_ROLE_QSCRATCH_MISSING;
    if (positions[1] == count || positions[2] == count)
        return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
    if (!(positions[0] < positions[1]
          && positions[1] < positions[2]
          && positions[2] < positions[4]
          && positions[4] < positions[3]))
        return P313_DETAIL_ROLE_QSCRATCH_ORDER;
    const struct p282_trace_record *parent = &records[positions[1]];
    const struct p282_trace_record *child = &records[positions[2]];
    const struct p282_trace_record *stop = &records[positions[3]];
    const struct p282_trace_record *qscratch = &records[positions[4]];
    if (!parent->has_rc || !child->has_rc || !stop->has_rc
        || !qscratch->has_rc || stop->rc != 0)
        return P313_DETAIL_RECORD_FORMAT_CONTRADICTION;
    uint32_t raw = (uint32_t)qscratch->rc;
    if (((raw >> 20U) & 1U) == 0U || ((raw >> 28U) & 1U) == 0U)
        return P313_DETAIL_ROLE_QSCRATCH_VALUE;
    enum p282_role_classification classification = P282_ROLE_COMPLETE;
    if (parent->rc < 0) classification = P282_ROLE_PARENT_PM_NEGATIVE;
    else if (child->rc < 0) classification = P282_ROLE_CHILD_PM_NEGATIVE;
    g_p313_role_qscratch = raw;
    g_p313_role_qscratch_valid = 1U;
    *result = (struct p282_role_result){
        .classification = classification,
        .pid = pid,
        .parent_pm_rc = parent->rc,
        .child_pm_rc = child->rc,
    };
    return 0;
}

'''.encode("ascii")
    return _replace_between(data, start, end, new, label="strict role parser")


def transform_runtime_include(data: bytes) -> bytes:
    declaration_anchor = b"struct p282_trace_control {\n"
    if data.count(declaration_anchor) != 1 or _P313_EARLY_DECLARATIONS in data:
        raise TransformError("P3.13 early declaration anchor differs")
    value = data.replace(
        declaration_anchor, _P313_EARLY_DECLARATIONS + declaration_anchor, 1
    )
    value = _replace_exact(
        value,
        b"#define P300_PREFIX_RECORD_CAPACITY 16U\n",
        b"#define P300_PREFIX_RECORD_CAPACITY 32U\n",
        label="direct prefix capacity",
    )
    value = _replace_exact(
        value,
        b"    uint64_t nondevice_entries;\n"
        b"    uint64_t entries_in_buffer;\n",
        b"    uint64_t nondevice_entries;\n"
        b"    uint64_t prefix_records;\n"
        b"    uint64_t entries_in_buffer;\n",
        label="direct prefix result field",
    )
    value = _replace_exact(
        value,
        b"    if (detail == 0) detail = p300_parse_bind_prefix(&state, result);\n",
        b"    result->prefix_records = state.prefix_count;\n"
        b"    if (detail == 0 && state.prefix_count == P313_DIRECT_PREFIX_CLEAN)\n"
        b"        detail = p300_parse_bind_prefix(&state, result);\n"
        b"    if (detail == 0 && state.prefix_count >=\n"
        b"        P313_DIRECT_PREFIX_CONTRADICTION_MIN)\n"
        b"        detail = P313_DETAIL_DIRECT_PREFIX_MULTIPLICITY;\n",
        label="direct prefix classification",
    )
    value = _extend_generic_unsigned_parser(value)
    value = _strict_role_parser(value)
    value = _replace_exact(
        value,
        b"                P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,\n"
        b"                parse_rc == 0\n"
        b"                    && role_result.classification >= P282_ROLE_COMPLETE);\n",
        b"                (parse_rc >= 0x6701 && parse_rc <= 0x673f)\n"
        b"                    ? parse_rc\n"
        b"                    : P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,\n"
        b"                parse_rc == 0\n"
        b"                    && role_result.classification >= P282_ROLE_COMPLETE);\n",
        label="strict role completed parse propagation",
    )
    value = _replace_exact(
        value,
        b"            if (parse_rc != 0) {\n"
        b"                return P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;\n"
        b"            }\n",
        b"            if (parse_rc != 0) {\n"
        b"                return (parse_rc >= 0x6701 && parse_rc <= 0x673f)\n"
        b"                    ? parse_rc\n"
        b"                    : P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION;\n"
        b"            }\n",
        label="strict role final parse propagation",
    )
    value = _replace_exact(
        value,
        b"                    P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,\n"
        b"                    0);\n"
        b"            }\n"
        b"            (void)sys_close(pipe_fds[0]);\n"
        b"            long detail = P282_DETAIL_ROLE_WRITE_PRE_START_TIMEOUT;\n",
        b"                    (parse_rc >= 0x6701 && parse_rc <= 0x673f)\n"
        b"                        ? parse_rc\n"
        b"                        : P282_DETAIL_ROLE_TRACE_SOURCE_CONTRADICTION,\n"
        b"                    0);\n"
        b"            }\n"
        b"            (void)sys_close(pipe_fds[0]);\n"
        b"            long detail = P282_DETAIL_ROLE_WRITE_PRE_START_TIMEOUT;\n",
        label="strict role timeout parse propagation",
    )
    value = _replace_exact(
        value,
        b"static int p301_terminal_detail_allowed(uint16_t detail) {\n"
        b"    return (detail >= P307_SUMMARY_DETAIL_BASE\n"
        b"            && detail <= P308_SUMMARY_DETAIL_MAX)\n"
        b"        || (detail >= P301_FINAL_DRIFT_DETAIL_BASE\n"
        b"            && detail <= P301_FINAL_DRIFT_DETAIL_MAX)\n"
        b"        || (detail >= P301_DETAIL_SUBTYPE_EMPTY_MASK\n"
        b"            && detail <= P301_DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION)\n"
        b"        || (detail >= P308_DEGRADED_DETAIL_BASE\n"
        b"            && detail <= P308_DEGRADED_DETAIL_MAX);\n"
        b"}\n",
        b"static int p301_terminal_detail_allowed(uint16_t detail) {\n"
        b"    return (detail >= 0x4801U && detail <= 0x4c02U)\n"
        b"        || (detail >= 0x5001U && detail <= 0x5050U)\n"
        b"        || (detail >= 0x5061U && detail <= 0x507fU)\n"
        b"        || (detail >= 0x6701U && detail <= 0x673fU);\n"
        b"}\n",
        label="P3.13 terminal gate",
    )
    start = b"static __attribute__((noreturn)) void p290_e3_run(void) {\n"
    if value.count(start) != 1:
        raise TransformError("P3.13 run entry anchor differs")
    value = value[:value.index(start)] + _P313_SUPPORT + b"\n"
    value += b'''static __attribute__((noreturn)) void p290_e3_run(void) {
    p313_run();
}
'''
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["runtime_wrapper"] = transform_runtime_wrapper(source["runtime_wrapper"])
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    result["trace_descriptor_header"] = transform_trace_descriptor(
        source["trace_descriptor_header"]
    )
    result["p290_position_header"] = transform_positions(
        source["p290_position_header"]
    )
    changed = {key for key in result if result[key] != source[key]}
    expected = {
        "runtime_wrapper",
        "p290_e3_runtime_include",
        "trace_descriptor_header",
        "p290_position_header",
    }
    if changed != expected:
        raise TransformError(f"P3.13 delta differs: {sorted(changed)}")
    return result
