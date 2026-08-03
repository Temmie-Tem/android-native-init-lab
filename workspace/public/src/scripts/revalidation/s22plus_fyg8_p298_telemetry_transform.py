#!/usr/bin/env python3
"""Transform P2.96 into the P2.98 gadget-start/event observer."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p296_telemetry_transform as inherited
import s22plus_fyg8_p298_telemetry_spec as spec


base = inherited.base


class TelemetryTransformError(ValueError):
    pass


def _kernel_rule_table() -> bytes:
    rows = b"".join(
        f"+\t{{{ordinal}, {outcome}, 0x{detail:x}}},\n".encode("ascii")
        for ordinal, outcome, detail in spec.exact_detail_rules()
    )
    return (
        b"+static const struct s22_fyg8_p290_detail_rule\n"
        b"+s22_fyg8_p290_detail_rules[] __used = {\n"
        + rows
        + b"+};\n"
    )


def _client_rule_table() -> bytes:
    rows = b"".join(
        f"    {{{ordinal}U, {outcome}U, 0x{detail:x}U}},\n".encode("ascii")
        for ordinal, outcome, detail in spec.exact_detail_rules()
    )
    return (
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n"
        + rows
        + b"};\n"
    )


def transform_checkpoint_client(data: bytes) -> bytes:
    value = base._replace_table(  # noqa: SLF001
        data,
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n",
        _client_rule_table(),
        label="P2.98 userspace detail",
    )
    return base.replace_exact(
        value,
        b"    uint8_t outcome = detail >= 0xcc0U && detail <= 0xcc3U\n"
        b"        ? S22_P233_OUTCOME_SUCCESS\n"
        b"        : S22_P233_OUTCOME_FAILURE;\n",
        b"    uint8_t outcome = detail >= 0xe50U && detail <= 0xe53U\n"
        b"        ? S22_P233_OUTCOME_SUCCESS\n"
        b"        : S22_P233_OUTCOME_FAILURE;\n",
        label="P2.98 terminal success family",
    )


def transform_candidate_patch(data: bytes) -> bytes:
    value = base._replace_table(  # noqa: SLF001
        data,
        b"+static const struct s22_fyg8_p290_detail_rule\n"
        b"+s22_fyg8_p290_detail_rules[] __used = {\n",
        _kernel_rule_table(),
        label="P2.98 kernel detail",
    )
    value = p252._recount_kernel_patch_hunks(value)  # noqa: SLF001
    if not value.endswith(b"\n"):
        raise TelemetryTransformError("P2.98 candidate patch lacks newline")
    return value


P298_DETAIL_DEFINES = b"""#define P298_DETAIL_BIND_TRACE_CONTROL_UNAVAILABLE 0xf60U
#define P298_DETAIL_BIND_TRACE_REGISTRATION_UNAVAILABLE 0xf61U
#define P298_DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED 0xf62U
#define P298_DETAIL_BIND_TRACE_SNAPSHOT_READ_FAILED 0xf63U
#define P298_DETAIL_GADGET_START_NOT_REACHED 0xf64U
#define P298_DETAIL_GADGET_START_NO_RETURN 0xf65U
#define P298_DETAIL_GADGET_START_POSITIVE_RC 0xf66U
#define P298_DETAIL_EP_ENABLE_HIT_CONTRADICTION 0xf67U
#define P298_DETAIL_EP0_OUT_EINVAL 0xf68U
#define P298_DETAIL_EP0_OUT_EAGAIN 0xf69U
#define P298_DETAIL_EP0_OUT_ETIMEDOUT 0xf6aU
#define P298_DETAIL_EP0_IN_EINVAL 0xf6bU
#define P298_DETAIL_EP0_IN_EAGAIN 0xf6cU
#define P298_DETAIL_EP0_IN_ETIMEDOUT 0xf6dU
#define P298_DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION 0xf6eU
#define P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION 0xf6fU
#define P298_DETAIL_FINAL_TRACE_READBACK_FAILED 0xf70U
#define P298_DETAIL_FINAL_TRACE_CLEANUP_UNVERIFIED 0xf71U
#define P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH 0xf72U

"""


P298_BIND_EVENTS = b"""    {"dwc3_state_snapshot", "p:p282/dwc3_state_snapshot s22_p294_dwc3_state_snapshot link=%x0:u32 run_stop=%x1:u32 devctrlhlt=%x2:u32 coreidle=%x3:u32 prtcap=%x4:u32 susphy=%x5:u32 connect_speed=%x6:u32\\n", "common_pid > 0"},
    {"gadget_start_in", "p:p282/gadget_start_in __dwc3_gadget_start dwc=%x0:u64\\n", "common_pid > 0"},
    {"gadget_start_out", "r:p282/gadget_start_out __dwc3_gadget_start rc=$retval:s32\\n", "common_pid > 0"},
    {"ep_enable_in", "p:p282/ep_enable_in __dwc3_gadget_ep_enable\\n", "common_pid > 0"},
    {"reset_in", "p:p282/reset_in dwc3_gadget_reset_interrupt dwc=%x0:u64\\n", "common_pid > 0"},
    {"connect_done_in", "p:p282/connect_done_in dwc3_gadget_conndone_interrupt dwc=%x0:u64\\n", "common_pid > 0"},
};
"""


def transform_trace_descriptor(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 7U\n",
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 12U\n",
        label="P2.98 bind event count",
    )
    value = base.replace_exact(
        value,
        b"#define P282_DETAIL_COUNT 59U\n\n",
        b"#define P282_DETAIL_COUNT 59U\n\n" + P298_DETAIL_DEFINES,
        label="P2.98 observer detail definitions",
    )
    anchor = (
        b'    {"dwc3_state_snapshot", "p:p282/dwc3_state_snapshot '
        b's22_p294_dwc3_state_snapshot link=%x0:u32 run_stop=%x1:u32 '
        b'devctrlhlt=%x2:u32 coreidle=%x3:u32 prtcap=%x4:u32 '
        b'susphy=%x5:u32 connect_speed=%x6:u32\\n", '
        b'"common_pid > 0"},\n};\n'
    )
    return base.replace_exact(
        value,
        anchor,
        P298_BIND_EVENTS,
        label="P2.98 bind observer descriptors",
    )


P298_CAPTURE_DECLARATIONS = b"""struct p294_capture_values {
    uint8_t dwc3_seen;
    uint8_t probe_armed;
    uint8_t start_rc_zero;
    uint8_t ep_enable_hits;
    uint8_t link_state;
    uint8_t run_stop;
    uint8_t devctrlhlt;
    uint8_t coreidle;
    uint8_t prtcap;
    uint8_t susphy;
    uint8_t connect_speed;
    uint64_t start_dwc;
};

static struct p294_capture_values g_p294_capture;

"""


P298_TERMINAL_DETAIL = b"""static long p294_terminal_detail(
    unsigned int state,
    unsigned int speed,
    uint16_t *detail) {
    unsigned int mismatch = 0;
    if (!g_p294_capture.dwc3_seen
        || !g_p294_capture.probe_armed
        || !g_p294_capture.start_rc_zero
        || g_p294_capture.ep_enable_hits != 2U
        || g_p294_capture.start_dwc == 0U) {
        return -P260_EPROTO;
    }
    if (g_p294_capture.run_stop != 1U) mismatch |= 1U;
    if (g_p294_capture.devctrlhlt != 0U) mismatch |= 2U;
    if (g_p294_capture.prtcap != 2U) mismatch |= 4U;
    if (mismatch != 0U) {
        *detail = (uint16_t)(P294_MISMATCH_DETAIL_BASE + mismatch - 1U);
        return 0;
    }
    unsigned int category = 0;
    if (state == 0U) {
        if (speed != 0U) {
            *detail = P294_STATE_SPEED_CONTRADICTION;
            return 0;
        }
    } else {
        if (state >= P282_STATE_COUNT || speed > P282_SPEED_HIGH) {
            *detail = P294_STATE_SPEED_CONTRADICTION;
            return 0;
        }
        category = 1U + (state - 1U) * 4U + speed;
    }
    if (speed != 0U) {
        unsigned int expected = speed == 1U ? 2U : speed == 2U ? 1U : 0U;
        if (g_p294_capture.connect_speed != expected) {
            *detail = P294_CONNECT_SPEED_CONTRADICTION;
            return 0;
        }
    }
    unsigned int index =
        ((category * 2U + g_p294_capture.coreidle) * 2U)
        + g_p294_capture.susphy;
    if (index >= 132U) {
        return -P260_EPROTO;
    }
    *detail = (uint16_t)(P294_FINAL_DETAIL_BASE + index);
    return 0;
}
"""


P298_PARSE_UNSIGNED_FIELD = b"""
static long p298_parse_unsigned_field(
    const char *start,
    const char *end,
    const char *name,
    uint64_t *result,
    uint8_t *present) {
    const char *cursor = start;
    size_t name_length = cstr_len(name);
    *present = 0;
    while (cursor < end) {
        const char *found = p282_line_find(cursor, end, name);
        if (found == NULL) {
            return 0;
        }
        if ((found == start || p282_is_space(found[-1]))
            && found + name_length < end) {
            const char *value_start = found + name_length;
            const char *value_end = value_start;
            while (value_end < end && p282_is_digit(*value_end)) {
                ++value_end;
            }
            if (value_start == value_end
                || (value_end < end && !p282_is_space(*value_end))) {
                return -P260_EPROTO;
            }
            uint64_t value = 0;
            long rc = p282_parse_unsigned(value_start, value_end, &value);
            if (rc != 0 || *present) {
                return rc != 0 ? rc : -P260_EPROTO;
            }
            *present = 1;
            *result = value;
            cursor = value_end;
            continue;
        }
        cursor = found + 1;
    }
    return 0;
}
"""


P298_PROFILE_CLEAN = b"""static long p282_profile_clean(
    struct p282_trace_control *control) {
    uint8_t seen[P282_CYCLE_EVENT_COUNT] = {0};
    memset(control->profile_hits, 0, sizeof(control->profile_hits));
    const char *cursor = p282_profile_buffer;
    const char *end = p282_profile_buffer + p282_profile_length;
    while (cursor < end) {
        const char *line_end = cursor;
        while (line_end < end && *line_end != '\\n') {
            ++line_end;
        }
        const char *name_start = cursor;
        while (name_start < line_end && p282_is_space(*name_start)) {
            ++name_start;
        }
        const char *name_end = name_start;
        while (name_end < line_end && !p282_is_space(*name_end)) {
            ++name_end;
        }
        for (size_t index = 0; index < control->event_count; ++index) {
            size_t length = cstr_len(control->events[index].name);
            if ((size_t)(name_end - name_start) != length
                || !p260_bytes_equal(
                    name_start, control->events[index].name, length)) {
                continue;
            }
            if (seen[index]) {
                return -P260_EPROTO;
            }
            const char *hits_start = name_end;
            while (hits_start < line_end && p282_is_space(*hits_start)) {
                ++hits_start;
            }
            const char *hits_end = hits_start;
            while (hits_end < line_end && p282_is_digit(*hits_end)) {
                ++hits_end;
            }
            const char *missed_start = hits_end;
            while (missed_start < line_end && p282_is_space(*missed_start)) {
                ++missed_start;
            }
            const char *missed_end = missed_start;
            while (missed_end < line_end && p282_is_digit(*missed_end)) {
                ++missed_end;
            }
            uint64_t hits = 0;
            uint64_t missed = 0;
            long rc = p282_parse_unsigned(hits_start, hits_end, &hits);
            if (rc == 0) {
                rc = p282_parse_unsigned(missed_start, missed_end, &missed);
            }
            if (rc != 0 || missed != 0U) {
                return rc != 0 ? rc : -EIO;
            }
            control->profile_hits[index] = hits;
            seen[index] = 1;
        }
        cursor = line_end < end ? line_end + 1 : end;
    }
    for (size_t index = 0; index < control->event_count; ++index) {
        if (!seen[index]) {
            return -EIO;
        }
    }
    return 0;
}
"""


P298_BIND_RESULT_STRUCT = b"""struct p282_bind_trace_result {
    uint8_t source_consistent;
    uint8_t pullup_returned_zero;
    uint8_t run_stop_seen;
    int32_t run_stop_rc;
    unsigned int branch;
    uint8_t snapshot_seen;
    uint8_t start_entered;
    uint8_t start_returned;
    uint8_t ep_enable_hits;
    uint8_t reset_seen;
    uint8_t connect_done_seen;
    uint8_t link_state;
    uint8_t run_stop;
    uint8_t devctrlhlt;
    uint8_t coreidle;
    uint8_t prtcap;
    uint8_t susphy;
    uint8_t connect_speed;
    int32_t start_rc;
    uint64_t start_dwc;
    uint64_t record_hits[P282_CYCLE_EVENT_COUNT];
};
"""


P298_BIND_PARSER = b"""static long p282_parse_bind_result(
    const struct p282_trace_control *control,
    struct p282_bind_trace_result *result) {
    struct p282_trace_record records[P282_RECORD_CAPACITY];
    size_t count = 0;
    *result = (struct p282_bind_trace_result){
        .source_consistent = 1,
        .branch = P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    long rc = p282_parse_trace_records(control, records, &count);
    if (rc != 0) {
        return rc;
    }
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index >= P282_BIND_EVENT_COUNT
            || result->record_hits[record->event_index] == UINT64_MAX) {
            return -P260_EPROTO;
        }
        ++result->record_hits[record->event_index];
        if ((record->event_index < 10U && record->pid != 1)
            || (record->event_index >= 10U && record->pid <= 0)) {
            return -P260_EPROTO;
        }
    }
    struct p282_trace_pair pull = {0};
    rc = p282_pair_in_window(
        records, count, 2U, 3U, 1, 0, UINT64_MAX, 1, 1, &pull);
    if (rc != 0 || !pull.entered || !pull.returned || pull.rc != 0) {
        return rc != 0 ? rc : -P260_EPROTO;
    }
    result->pullup_returned_zero = 1;

    struct p282_trace_pair resume = {0};
    struct p282_trace_pair run = {0};
    struct p282_trace_pair start = {0};
    rc = p282_pair_in_window(
        records, count, 0U, 1U, 1,
        pull.entry_counter, pull.return_counter, 0, 0, &resume);
    if (rc == 0) {
        rc = p282_pair_in_window(
            records, count, 4U, 5U, 1,
            pull.entry_counter, pull.return_counter, 1, 1, &run);
    }
    if (rc == 0) {
        rc = p282_pair_in_window(
            records, count, 7U, 8U, 1,
            pull.entry_counter, pull.return_counter, 0, 0, &start);
    }
    if (rc != 0
        || (resume.entered && !resume.returned)
        || (run.entered && !run.returned)
        || (resume.returned && resume.rc < 0)
        || !run.entered || run.rc != 0) {
        return rc != 0 ? rc : -P260_EPROTO;
    }
    result->run_stop_seen = 1;
    result->run_stop_rc = run.rc;
    if (resume.returned) {
        if (!(resume.entry_counter < run.entry_counter
              && run.return_counter < resume.return_counter)) {
            return -P260_EPROTO;
        }
        result->branch = P282_BIND_RESUME_NESTED;
    } else {
        result->branch = P282_BIND_DIRECT;
    }

    result->start_entered = start.entered;
    result->start_returned = start.returned;
    result->start_rc = start.rc;
    const struct p282_trace_record *start_record = NULL;
    if (start.entered) {
        if (start.entry_counter >= run.entry_counter
            || (start.returned
                && start.return_counter >= run.entry_counter)) {
            return -P260_EPROTO;
        }
        for (size_t index = 0; index < count; ++index) {
            const struct p282_trace_record *record = &records[index];
            if (record->event_index == 7U
                && record->counter == start.entry_counter) {
                start_record = record;
                break;
            }
        }
        if (start_record == NULL || !start_record->has_dwc
            || start_record->dwc == 0U) {
            return -P260_EPROTO;
        }
        result->start_dwc = start_record->dwc;
        uint64_t upper = start.returned
            ? start.return_counter : run.entry_counter;
        for (size_t index = 0; index < count; ++index) {
            const struct p282_trace_record *record = &records[index];
            if (record->event_index == 9U
                && record->counter > start.entry_counter
                && record->counter < upper) {
                if (result->ep_enable_hits == UINT8_MAX) {
                    return -P260_EOVERFLOW;
                }
                ++result->ep_enable_hits;
            }
        }
    }

    unsigned int matches = 0;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index == 6U
            && record->counter > run.entry_counter
            && record->counter < run.return_counter) {
            if (!record->has_link || !record->has_run_stop
                || !record->has_devctrlhlt || !record->has_coreidle
                || !record->has_prtcap || !record->has_susphy
                || !record->has_connect_speed
                || record->link < 0 || record->link > 15
                || record->run_stop < 0 || record->run_stop > 1
                || record->devctrlhlt < 0 || record->devctrlhlt > 1
                || record->coreidle < 0 || record->coreidle > 1
                || record->prtcap < 0 || record->prtcap > 3
                || record->susphy < 0 || record->susphy > 1
                || record->connect_speed < 0
                || record->connect_speed > 7 || matches != 0U) {
                return -P260_EPROTO;
            }
            result->snapshot_seen = 1U;
            result->link_state = (uint8_t)record->link;
            result->run_stop = (uint8_t)record->run_stop;
            result->devctrlhlt = (uint8_t)record->devctrlhlt;
            result->coreidle = (uint8_t)record->coreidle;
            result->prtcap = (uint8_t)record->prtcap;
            result->susphy = (uint8_t)record->susphy;
            result->connect_speed = (uint8_t)record->connect_speed;
            ++matches;
        }
    }
    if (matches != 1U) {
        return -P260_EPROTO;
    }
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index < 10U
            || !start.entered
            || record->counter <= start.entry_counter) {
            continue;
        }
        if (!record->has_dwc || record->dwc != result->start_dwc) {
            return -P260_EPROTO;
        }
        if (record->event_index == 10U) {
            result->reset_seen = 1U;
        } else if (record->event_index == 11U) {
            result->connect_done_seen = 1U;
        }
    }
    return 0;
}
"""


P298_BIND_HELPERS_AND_PHASE = b"""static long p298_setup_failure_detail(long setup_rc) {
    if (setup_rc == P282_CONTROL_TRACE_CONTROL_UNAVAILABLE) {
        return P298_DETAIL_BIND_TRACE_CONTROL_UNAVAILABLE;
    }
    if (setup_rc == P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE) {
        return P298_DETAIL_BIND_TRACE_REGISTRATION_UNAVAILABLE;
    }
    if (setup_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {
        return P298_DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED;
    }
    return P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
}

static long p298_profile_matches(
    const struct p282_trace_control *control,
    const struct p282_bind_trace_result *result) {
    for (size_t index = 0; index < control->event_count; ++index) {
        if (control->profile_hits[index] != result->record_hits[index]) {
            return P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH;
        }
    }
    return 0;
}

static long p298_finish_observer(
    struct p282_trace_control *control,
    struct p282_bind_trace_result *result,
    long source_detail) {
    long quality = 0;
    long finish_rc = p282_trace_finish(control, &quality);
    if (finish_rc != 0) {
        return P298_DETAIL_FINAL_TRACE_CLEANUP_UNVERIFIED;
    }
    if (quality != 0) {
        return P298_DETAIL_FINAL_TRACE_READBACK_FAILED;
    }
    long parse_rc = p282_parse_bind_result(control, result);
    if (parse_rc != 0) {
        return source_detail;
    }
    return p298_profile_matches(control, result);
}

static long p298_start_result_detail(
    const struct p282_bind_trace_result *result) {
    if (!result->start_entered) {
        return P298_DETAIL_GADGET_START_NOT_REACHED;
    }
    if (!result->start_returned) {
        return P298_DETAIL_GADGET_START_NO_RETURN;
    }
    if (result->start_rc > 0) {
        return P298_DETAIL_GADGET_START_POSITIVE_RC;
    }
    if (result->start_rc == 0) {
        return result->ep_enable_hits == 2U
            ? 0 : P298_DETAIL_EP_ENABLE_HIT_CONTRADICTION;
    }
    if (result->ep_enable_hits != 1U && result->ep_enable_hits != 2U) {
        return P298_DETAIL_EP_ENABLE_HIT_CONTRADICTION;
    }
    if (result->ep_enable_hits == 1U) {
        if (result->start_rc == -EINVAL) return P298_DETAIL_EP0_OUT_EINVAL;
        if (result->start_rc == -EAGAIN) return P298_DETAIL_EP0_OUT_EAGAIN;
        if (result->start_rc == -ETIMEDOUT) {
            return P298_DETAIL_EP0_OUT_ETIMEDOUT;
        }
    } else {
        if (result->start_rc == -EINVAL) return P298_DETAIL_EP0_IN_EINVAL;
        if (result->start_rc == -EAGAIN) return P298_DETAIL_EP0_IN_EAGAIN;
        if (result->start_rc == -ETIMEDOUT) {
            return P298_DETAIL_EP0_IN_ETIMEDOUT;
        }
    }
    return P298_DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION;
}

static long p298_revalidate_detail(void) {
    for (size_t index = 0; index < S22PLUS_O2_BIND_GATE_COUNT; ++index) {
        long rc = p241_check_gate(index);
        if (rc != 0) {
            return rc == -ENODEV
                ? S22_P248_DETAIL_REGRESSION_BASE + (long)index
                : S22_P248_DETAIL_READ_ERROR_BASE + (long)index;
        }
    }
    return 0;
}

static __attribute__((noreturn)) void p298_fail_with_trace(
    struct p282_trace_control *control,
    long intended_detail) {
    struct p282_bind_trace_result final_result = {0};
    long observer_detail = p298_finish_observer(
        control, &final_result,
        P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH);
    if (observer_detail != 0) {
        p290_fail_next(observer_detail);
    }
    if (p298_start_result_detail(&final_result) != 0) {
        p290_fail_next(P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH);
    }
    p290_fail_next(intended_detail);
}

static unsigned int p282_phase_bind(
    unsigned int repair_class,
    struct p282_trace_control *control) {
    long setup_rc = p282_trace_setup(P282_PHASE_BIND, control);
    if (setup_rc != 0) {
        p290_fail_next(p298_setup_failure_detail(setup_rc));
    }
    p290_progress_position(
        S22_P290_POSITION_BIND_TRACE_SETUP_RETURNED, 0U);

    long bind_rc = p260_bind_udc();
    if (bind_rc != 0) {
        p298_fail_with_trace(control, bind_rc);
    }
    p290_progress_position(S22_P290_POSITION_BIND_UDC_RETURNED, 0U);

    long snapshot_rc = p282_trace_read_snapshot(control, 0);
    if (snapshot_rc != 0) {
        p298_fail_with_trace(
            control, P298_DETAIL_BIND_TRACE_SNAPSHOT_READ_FAILED);
    }
    struct p282_bind_trace_result trace_result = {0};
    long parse_rc = p282_parse_bind_result(control, &trace_result);
    if (parse_rc != 0) {
        p298_fail_with_trace(
            control, P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);
    }
    long start_detail = p298_start_result_detail(&trace_result);
    if (start_detail != 0) {
        struct p282_bind_trace_result final_result = {0};
        long observer_detail = p298_finish_observer(
            control, &final_result,
            P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);
        if (observer_detail != 0) {
            p290_fail_next(observer_detail);
        }
        start_detail = p298_start_result_detail(&final_result);
        p290_fail_next(
            start_detail != 0
                ? start_detail
                : P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);
    }

    struct p282_bind_observation observation = {
        .cleanup_verified = 1,
        .source_consistent = trace_result.source_consistent,
        .trace_authoritative = 1,
        .pullup_returned_zero = trace_result.pullup_returned_zero,
        .run_stop_seen = trace_result.run_stop_seen,
        .run_stop_rc = trace_result.run_stop_rc,
        .repair_class = repair_class,
        .bind_branch = trace_result.branch,
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_bind(&observation, &classification);
    uint16_t bind_detail = classified > 0
        ? (uint16_t)classification.detail : 0U;
    if (classified < 0
        || classification.outcome == P282_OUTCOME_FAILURE
        || bind_detail != P282_DETAIL_HELPER_OFF_ON_ZERO_DIRECT_RUN_STOP
        || !trace_result.snapshot_seen) {
        p298_fail_with_trace(
            control, P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);
    }
    g_p294_capture.dwc3_seen = trace_result.snapshot_seen;
    g_p294_capture.probe_armed = 1U;
    g_p294_capture.start_rc_zero = 1U;
    g_p294_capture.ep_enable_hits = trace_result.ep_enable_hits;
    g_p294_capture.start_dwc = trace_result.start_dwc;
    g_p294_capture.link_state = trace_result.link_state;
    g_p294_capture.run_stop = trace_result.run_stop;
    g_p294_capture.devctrlhlt = trace_result.devctrlhlt;
    g_p294_capture.coreidle = trace_result.coreidle;
    g_p294_capture.prtcap = trace_result.prtcap;
    g_p294_capture.susphy = trace_result.susphy;
    g_p294_capture.connect_speed = trace_result.connect_speed;
    p290_progress_position(
        S22_P290_POSITION_BIND_TRACE_CLASSIFIED, bind_detail);
    return observation.bind_branch;
}
"""


P298_FINAL_WAIT = b"""static __attribute__((noreturn)) void p282_wait_final_pair(
    unsigned int repair_class,
    unsigned int bind_branch,
    struct p282_trace_control *control) {
    (void)p282_classify_final_pair;
    _Static_assert(
        sizeof(p282_descriptor_udc_states)
                / sizeof(p282_descriptor_udc_states[0])
            == P282_STATE_COUNT,
        "P2.98 generated UDC state table cardinality");
    _Static_assert(
        sizeof(p282_descriptor_usb_speeds)
                / sizeof(p282_descriptor_usb_speeds[0])
            == P282_SPEED_COUNT,
        "P2.98 generated USB speed table cardinality");

    if (repair_class != P282_REPAIR_POWER_HELPER_OFF_ON_ZERO
        || bind_branch != P282_BIND_DIRECT
        || !control->active) {
        p298_fail_with_trace(
            control, P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);
    }
    p290_progress_position(
        S22_P290_POSITION_FINAL_SAMPLING_STARTED, 0U);
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(P282_FINAL_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        p298_fail_with_trace(control, rc);
    }
    unsigned int previous_state = 0;
    unsigned int previous_speed = 0;
    unsigned int current_state = 0;
    unsigned int current_speed = 0;
    int have_previous = 0;
    for (;;) {
        rc = p298_revalidate_detail();
        if (rc != 0) {
            p298_fail_with_trace(control, rc);
        }
        rc = p282_read_final_pair(&current_state, &current_speed);
        if (rc == 0) {
            rc = p298_revalidate_detail();
        }
        if (rc != 0) {
            p298_fail_with_trace(control, rc);
        }
        int stable = have_previous
            && previous_state == current_state
            && previous_speed == current_speed;
        int configured_high = current_state == P282_STATE_CONFIGURED
            && current_speed == P282_SPEED_HIGH;
        if ((stable && configured_high) || p282_deadline_expired(&deadline)) {
            if (!have_previous) {
                p298_fail_with_trace(
                    control, P282_DETAIL_FINAL_STATE_SPEED_UNSTABLE);
            }
            struct p282_bind_trace_result final_result = {0};
            long observer_detail = p298_finish_observer(
                control, &final_result,
                P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH);
            if (observer_detail != 0) {
                p290_fail_next(observer_detail);
            }
            if (p298_start_result_detail(&final_result) != 0
                || final_result.start_dwc != g_p294_capture.start_dwc
                || final_result.link_state != g_p294_capture.link_state
                || final_result.run_stop != g_p294_capture.run_stop
                || final_result.devctrlhlt != g_p294_capture.devctrlhlt
                || final_result.coreidle != g_p294_capture.coreidle
                || final_result.prtcap != g_p294_capture.prtcap
                || final_result.susphy != g_p294_capture.susphy
                || final_result.connect_speed
                    != g_p294_capture.connect_speed) {
                p290_fail_next(P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH);
            }
            uint16_t terminal_detail = 0;
            rc = p294_terminal_detail(
                current_state, current_speed, &terminal_detail);
            if (rc != 0) {
                p290_fail_next(rc);
            }
            unsigned int event_mask =
                (final_result.reset_seen ? 1U : 0U)
                | (final_result.connect_done_seen ? 2U : 0U);
            uint16_t first_detail = (uint16_t)(
                P294_LINK_DETAIL_BASE
                + event_mask * 16U
                + final_result.link_state);
            rc = p294_publish_final_pair(first_detail, terminal_detail);
            if (rc != 0) {
                p292_park_after_checkpoint_error(rc);
            }
            p290_park_after_confirmed_publication();
        }
        previous_state = current_state;
        previous_speed = current_speed;
        have_previous = 1;
        p282_poll_delay();
    }
}
"""


def _insert_unsigned_parser(data: bytes) -> bytes:
    _start, end = base._function_span(data, b"p282_parse_field")  # noqa: SLF001
    return data[:end] + P298_PARSE_UNSIGNED_FIELD + data[end:]


def transform_runtime_include(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"    uint8_t active;\n};\n",
        b"    uint8_t active;\n"
        b"    uint64_t profile_hits[P282_CYCLE_EVENT_COUNT];\n};\n",
        label="P2.98 profile hit retention",
    )
    value = base.replace_exact(
        value,
        b"    uint8_t has_connect_speed;\n",
        b"    uint8_t has_connect_speed;\n    uint8_t has_dwc;\n",
        label="P2.98 DWC trace presence",
    )
    value = base.replace_exact(
        value,
        b"    int32_t connect_speed;\n    int32_t on;\n",
        b"    int32_t connect_speed;\n    uint64_t dwc;\n    int32_t on;\n",
        label="P2.98 DWC trace value",
    )
    value = _insert_unsigned_parser(value)
    value = base.replace_exact(
        value,
        b"            if (rc != 0) {\n                return rc;\n            }\n"
        b"            if (\n                have_previous\n",
        b"            if (rc == 0) {\n"
        b"                rc = p298_parse_unsigned_field(\n"
        b"                    event_end + 1, line_end, \"dwc=\",\n"
        b"                    &record.dwc, &record.has_dwc);\n"
        b"            }\n"
        b"            if (rc != 0) {\n                return rc;\n            }\n"
        b"            if (\n                have_previous\n",
        label="P2.98 DWC field parse",
    )
    value = base.replace_function(
        value, b"p282_profile_clean", P298_PROFILE_CLEAN
    )
    value = base.replace_exact(
        value,
        b"static long p282_trace_read_snapshot(\n"
        b"    const struct p282_trace_control *control,\n",
        b"static long p282_trace_read_snapshot(\n"
        b"    struct p282_trace_control *control,\n",
        label="P2.98 mutable profile snapshot",
    )
    start, end = base._function_span(  # noqa: SLF001
        value, b"p282_parse_bind_result"
    )
    struct_start = value.rfind(b"struct p282_bind_trace_result {\n", 0, start)
    struct_end = value.find(b"};\n", struct_start) + len(b"};\n")
    if struct_start < 0 or struct_end <= len(b"};\n"):
        raise TelemetryTransformError("P2.98 bind result struct differs")
    value = value[:struct_start] + P298_BIND_RESULT_STRUCT + value[struct_end:]
    value = base.replace_function(
        value, b"p282_parse_bind_result", P298_BIND_PARSER
    )
    value = base.replace_exact(
        value,
        inherited.P296_CAPTURE_DECLARATIONS,
        P298_CAPTURE_DECLARATIONS,
        label="P2.98 probe capture state",
    )
    value = base.replace_exact(
        value,
        b"#define P294_LINK_DETAIL_BASE 0xc60U\n"
        b"#define P294_FINAL_DETAIL_BASE 0xc70U\n"
        b"#define P294_MISMATCH_DETAIL_BASE 0xf40U\n"
        b"#define P294_STATE_SPEED_CONTRADICTION 0xf4fU\n"
        b"#define P294_CONNECT_SPEED_CONTRADICTION 0xf50U\n",
        b"#define P294_LINK_DETAIL_BASE 0xd00U\n"
        b"#define P294_FINAL_DETAIL_BASE 0xe00U\n"
        b"#define P294_MISMATCH_DETAIL_BASE 0xf80U\n"
        b"#define P294_STATE_SPEED_CONTRADICTION 0xf8fU\n"
        b"#define P294_CONNECT_SPEED_CONTRADICTION 0xf90U\n",
        label="P2.98 final detail families",
    )
    value = base.replace_function(
        value, b"p294_terminal_detail", P298_TERMINAL_DETAIL
    )
    value = base.replace_function(
        value, b"p282_phase_bind", P298_BIND_HELPERS_AND_PHASE
    )
    value = base.replace_function(
        value, b"p282_wait_final_pair", P298_FINAL_WAIT
    )
    return base.replace_exact(
        value,
        b"    unsigned int bind_branch = p282_phase_bind(repair_class);\n"
        b"    p282_wait_final_pair(repair_class, bind_branch);\n",
        b"    struct p282_trace_control bind_trace;\n"
        b"    unsigned int bind_branch = p282_phase_bind(\n"
        b"        repair_class, &bind_trace);\n"
        b"    p282_wait_final_pair(\n"
        b"        repair_class, bind_branch, &bind_trace);\n",
        label="P2.98 live bind observer handoff",
    )


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["candidate_patch"] = transform_candidate_patch(
        source["candidate_patch"]
    )
    result["checkpoint_client"] = transform_checkpoint_client(
        source["checkpoint_client"]
    )
    result["trace_descriptor_header"] = transform_trace_descriptor(
        source["trace_descriptor_header"]
    )
    result["p290_e3_runtime_include"] = transform_runtime_include(
        source["p290_e3_runtime_include"]
    )
    return result
