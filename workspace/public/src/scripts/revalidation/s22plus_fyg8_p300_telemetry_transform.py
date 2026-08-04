#!/usr/bin/env python3
"""Transform P2.98 into the P3.00 event-ingress/IRQ observer."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p298_telemetry_transform as inherited
import s22plus_fyg8_p300_telemetry_spec as spec


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


P300_PATCH_HELPER = b"""+static noinline __used void s22_p300_dwc3_event_config_snapshot(
+		struct dwc3 *dwc, struct dwc3_event_buffer *evt,
+		u32 devten, u32 gevntsiz, u32 gevntcount,
+		u32 evt_length, u32 evt_count, u32 evt_flags)
+{
+	barrier_data(dwc);
+	barrier_data(evt);
+	barrier_data(devten);
+	barrier_data(gevntsiz);
+	barrier_data(gevntcount);
+	barrier_data(evt_length);
+	barrier_data(evt_count);
+	barrier_data(evt_flags);
+}
+
"""


def transform_candidate_patch(data: bytes) -> bytes:
    value = base._replace_table(  # noqa: SLF001
        data,
        b"+static const struct s22_fyg8_p290_detail_rule\n"
        b"+s22_fyg8_p290_detail_rules[] __used = {\n",
        _kernel_rule_table(),
        label="P3.00 kernel detail",
    )
    helper_anchor = (
        b"+\tbarrier_data(connect_speed);\n"
        b"+}\n"
        b"+\n"
        b" static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)\n"
    )
    value = base.replace_exact(
        value,
        helper_anchor,
        helper_anchor[:-len(
            b" static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)\n"
        )]
        + P300_PATCH_HELPER
        + b" static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)\n",
        label="P3.00 event-config snapshot helper",
    )
    value = base.replace_exact(
        value,
        b"+\tif (is_on) {\n"
        b"+\t\tu32 dctl = dwc3_readl(dwc->regs, DWC3_DCTL);\n",
        b"+\tif (is_on) {\n"
        b"+\t\tstruct dwc3_event_buffer *evt = dwc->ev_buf;\n"
        b"+\t\tu32 dctl = dwc3_readl(dwc->regs, DWC3_DCTL);\n",
        label="P3.00 event-buffer capture",
    )
    value = base.replace_exact(
        value,
        b"+\t\t\t!!(gusb2 & DWC3_GUSB2PHYCFG_SUSPHY),\n"
        b"+\t\t\tdsts & DWC3_DSTS_CONNECTSPD);\n",
        b"+\t\t\t!!(gusb2 & DWC3_GUSB2PHYCFG_SUSPHY),\n"
        b"+\t\t\tdsts & DWC3_DSTS_CONNECTSPD);\n"
        b"+\t\ts22_p300_dwc3_event_config_snapshot(\n"
        b"+\t\t\tdwc, evt, dwc3_readl(dwc->regs, DWC3_DEVTEN),\n"
        b"+\t\t\tdwc3_readl(dwc->regs, DWC3_GEVNTSIZ(0)),\n"
        b"+\t\t\tdwc3_readl(dwc->regs, DWC3_GEVNTCOUNT(0)),\n"
        b"+\t\t\tevt ? evt->length : 0, evt ? evt->count : 0,\n"
        b"+\t\t\tevt ? evt->flags : 0);\n",
        label="P3.00 event-config snapshot call",
    )
    value = p252._recount_kernel_patch_hunks(value)  # noqa: SLF001
    value = base.replace_exact(
        value,
        b"@@ -2488,6 +2488,19 @@ static void __dwc3_gadget_set_speed(struct dwc3 *dwc)\n",
        b"@@ -2488,6 +2488,34 @@ static void __dwc3_gadget_set_speed(struct dwc3 *dwc)\n",
        label="P3.00 snapshot-helper hunk count",
    )
    value = base.replace_exact(
        value,
        b"@@ -2527,6 +2540,22 @@ static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)\n",
        b"@@ -2527,6 +2555,29 @@ static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)\n",
        label="P3.00 run-stop hunk count",
    )
    if not value.endswith(b"\n"):
        raise TelemetryTransformError("P3.00 candidate patch lacks newline")
    return value


def transform_checkpoint_client(data: bytes) -> bytes:
    return base._replace_table(  # noqa: SLF001
        data,
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n",
        _client_rule_table(),
        label="P3.00 userspace detail",
    )


P300_DETAIL_DEFINES = b"""#define P300_DETAIL_TRIGGER_SETUP_OR_READBACK 0xf73U
#define P300_DETAIL_TRIGGER_STATE_CONTRADICTION 0xf74U
#define P300_DETAIL_TRACE_STREAM_READ_FAILED 0xf75U
#define P300_DETAIL_TRACE_STREAM_LINE_MALFORMED 0xf76U
#define P300_DETAIL_TRACE_RING_LOSS 0xf77U
#define P300_DETAIL_EVENT_CONFIG_CONTRADICTION 0xf78U
#define P300_DETAIL_FOREIGN_POINTER_CONTRADICTION 0xf79U
#define P300_DETAIL_IRQ_PAIRING_CONTRADICTION 0xf7aU
#define P300_DETAIL_IRQ_RETURN_CONTRADICTION 0xf7bU
#define P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION 0xf7cU
#define P300_DETAIL_RAW_EVENT_CONTRADICTION 0xf7dU
#define P300_DETAIL_PROFILE_RELATION_CONTRADICTION 0xf7eU
#define P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION 0xf7fU

"""


P300_BIND_EVENTS = b"""    {"resume_in", "p:p282/resume_in dwc3_runtime_resume\\n", "common_pid > 0"},
    {"resume_out", "r:p282/resume_out dwc3_runtime_resume rc=$retval:s32\\n", "common_pid > 0"},
    {"pull_in", "p:p282/pull_in dwc3_gadget_pullup on=%x1:s32\\n", "common_pid > 0"},
    {"pull_out", "r:p282/pull_out dwc3_gadget_pullup rc=$retval:s32\\n", "common_pid > 0"},
    {"run_in", "p:p282/run_in dwc3_gadget_run_stop on=%x1:s32\\n", "common_pid > 0"},
    {"run_out", "r:p282/run_out dwc3_gadget_run_stop rc=$retval:s32\\n", "common_pid > 0"},
    {"dwc3_state_snapshot", "p:p282/dwc3_state_snapshot s22_p294_dwc3_state_snapshot link=%x0:u32 run_stop=%x1:u32 devctrlhlt=%x2:u32 coreidle=%x3:u32 prtcap=%x4:u32 susphy=%x5:u32 connect_speed=%x6:u32\\n", "common_pid > 0"},
    {"gadget_start_in", "p:p282/gadget_start_in __dwc3_gadget_start dwc=%x0:u64\\n", "common_pid > 0"},
    {"gadget_start_out", "r:p282/gadget_start_out __dwc3_gadget_start rc=$retval:s32\\n", "common_pid > 0"},
    {"ep_enable_in", "p:p282/ep_enable_in __dwc3_gadget_ep_enable\\n", "common_pid > 0"},
    {"event_config", "p:p282/event_config s22_p300_dwc3_event_config_snapshot dwc=%x0:u64 evt=%x1:u64 devten=%x2:u32 gevntsiz=%x3:u32 gevntcount=%x4:u32 evt_length=%x5:u32 evt_count=%x6:u32 evt_flags=%x7:u32\\n", "common_pid > 0"},
    {"irq_in", "p:p282/irq_in dwc3_interrupt evt=%x1:u64 dwc=+40(%x1):u64\\n", "common_pid >= 0"},
    {"irq_out", "r32:p282/irq_out dwc3_interrupt rc=$retval:s32\\n", "common_pid >= 0"},
    {"thread_in", "p:p282/thread_in dwc3_thread_interrupt evt=%x1:u64 dwc=+40(%x1):u64 evt_count=+24(%x1):u32 evt_flags=+28(%x1):u32\\n", "common_pid >= 0"},
    {"device_event_in", "p:p282/device_event_in dwc3_process_event_entry dwc=%x0:u64 raw=+0(%x1):u32 low=+0(%x1):u8 type=+0(%x1):b4@8/32\\n", "common_pid >= 0 && low == 1"},
};
"""


def transform_trace_descriptor(data: bytes) -> bytes:
    value = base.replace_exact(
        data,
        b"#define P282_BIND_EVENT_COUNT 12U\n",
        b"#define P282_BIND_EVENT_COUNT 15U\n",
        label="P3.00 bind event count",
    )
    value = base.replace_exact(
        value,
        b"#define P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH 0xf72U\n\n",
        b"#define P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH 0xf72U\n\n"
        + P300_DETAIL_DEFINES,
        label="P3.00 observer detail definitions",
    )
    start = value.find(b"static const struct p282_event_descriptor p282_bind_events[] = {\n")
    end = value.find(b"\nstatic const struct p282_detail_descriptor", start)
    if start < 0 or end < 0:
        raise TelemetryTransformError("P3.00 bind descriptor table differs")
    return value[:start] + (
        b"static const struct p282_event_descriptor p282_bind_events[] = {\n"
        + P300_BIND_EVENTS
    ) + value[end:]


P300_TRACE_RECORD = b"""struct p282_trace_record {
    uint64_t counter;
    long pid;
    uint8_t event_index;
    uint8_t has_on;
    uint8_t has_suspend;
    uint8_t has_rc;
    uint8_t has_present;
    uint8_t has_vbus;
    uint8_t has_link;
    uint8_t has_run_stop;
    uint8_t has_devctrlhlt;
    uint8_t has_coreidle;
    uint8_t has_prtcap;
    uint8_t has_susphy;
    uint8_t has_connect_speed;
    uint8_t has_dwc;
    uint8_t has_evt;
    uint8_t has_devten;
    uint8_t has_gevntsiz;
    uint8_t has_gevntcount;
    uint8_t has_evt_length;
    uint8_t has_evt_count;
    uint8_t has_evt_flags;
    uint8_t has_raw;
    uint8_t has_low;
    uint8_t has_type;
    int32_t present;
    int32_t vbus;
    int32_t link;
    int32_t run_stop;
    int32_t devctrlhlt;
    int32_t coreidle;
    int32_t prtcap;
    int32_t susphy;
    int32_t connect_speed;
    uint64_t dwc;
    uint64_t evt;
    uint64_t devten;
    uint64_t gevntsiz;
    uint64_t gevntcount;
    uint64_t evt_length;
    uint64_t evt_count;
    uint64_t evt_flags;
    uint64_t raw;
    uint64_t low;
    uint64_t type;
    int32_t on;
    int32_t suspend;
    int32_t rc;
};
"""


P300_BIND_RESULT_STRUCT = b"""struct p282_bind_trace_result {
    uint8_t source_consistent;
    uint8_t pullup_returned_zero;
    uint8_t run_stop_seen;
    int32_t run_stop_rc;
    unsigned int branch;
    uint8_t snapshot_seen;
    uint8_t event_config_seen;
    uint8_t start_entered;
    uint8_t start_returned;
    uint8_t ep_enable_hits;
    uint8_t reset_seen;
    uint8_t connect_done_seen;
    uint8_t other_device_seen;
    uint8_t link_state;
    uint8_t run_stop;
    uint8_t devctrlhlt;
    uint8_t coreidle;
    uint8_t prtcap;
    uint8_t susphy;
    uint8_t connect_speed;
    uint8_t irq_open;
    uint8_t header_seen;
    int32_t start_rc;
    uint64_t start_dwc;
    uint64_t event_dwc;
    uint64_t event_evt;
    uint64_t devten;
    uint64_t gevntsiz;
    uint64_t gevntcount;
    uint64_t evt_length;
    uint64_t evt_count;
    uint64_t evt_flags;
    uint64_t irq_entries;
    uint64_t irq_returns;
    uint64_t irq_return_mask;
    uint64_t thread_entries;
    uint64_t thread_empty_passes;
    uint64_t expected_process_entries;
    uint64_t device_records;
    uint64_t nondevice_entries;
    uint64_t entries_in_buffer;
    uint64_t entries_written;
    uint64_t observed_dwc;
    uint64_t observed_evt;
    uint64_t record_hits[P282_CYCLE_EVENT_COUNT];
};
"""


P300_CAPTURE_DECLARATIONS = b"""struct p294_capture_values {
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
    uint64_t event_dwc;
    uint64_t event_evt;
    uint64_t devten;
    uint64_t gevntsiz;
    uint64_t evt_length;
};

static struct p294_capture_values g_p294_capture;

"""


P300_TRIGGER_HELPERS = b"""
static long p300_trigger_path(char *path, size_t capacity) {
    return p282_event_path(
        path, capacity, "device_event_in", "/trigger");
}

static long p300_trigger_remaining(
    const struct p282_trace_control *control,
    unsigned int *remaining) {
    if (!control->trigger_armed || remaining == NULL) {
        return -P260_EPROTO;
    }
    char path[P282_PATH_CAPACITY];
    long rc = p300_trigger_path(path, sizeof(path));
    char value[2048];
    size_t length = 0;
    if (rc == 0) {
        rc = p282_read_file(path, value, sizeof(value), &length);
    }
    unsigned int count_zero = p282_count_bytes(
        value, length, "traceoff:count=0 if type == 2\\n");
    unsigned int count_one = p282_count_bytes(
        value, length, "traceoff:count=1 if type == 2\\n");
    if (rc != 0 || count_zero + count_one != 1U
        || p282_count_bytes(value, length, "traceoff:") != 1U) {
        return rc != 0 ? rc : -P260_EPROTO;
    }
    *remaining = count_one;
    return 0;
}

static long p300_trigger_readback(
    const struct p282_trace_control *control,
    unsigned int expected_count) {
    if (expected_count > 1U) return -P260_EPROTO;
    unsigned int actual_count = 0;
    long rc = p300_trigger_remaining(control, &actual_count);
    if (rc != 0 || actual_count != expected_count) {
        return rc != 0 ? rc : -P260_EPROTO;
    }
    return 0;
}

static long p300_trigger_arm(struct p282_trace_control *control) {
    char path[P282_PATH_CAPACITY];
    long rc = p300_trigger_path(path, sizeof(path));
    if (rc == 0) {
        rc = p282_write_control(path, "traceoff:1 if type == 2\\n");
    }
    if (rc == 0) {
        control->trigger_armed = 1U;
        rc = p300_trigger_readback(control, 1U);
    }
    return rc;
}

static long p300_trigger_remove(struct p282_trace_control *control) {
    if (!control->trigger_armed) {
        return 0;
    }
    char path[P282_PATH_CAPACITY];
    long rc = p300_trigger_path(path, sizeof(path));
    if (rc == 0) {
        rc = p282_write_control(path, "!traceoff:1 if type == 2\\n");
    }
    char value[2048];
    size_t length = 0;
    if (rc == 0) {
        rc = p282_read_file(path, value, sizeof(value), &length);
    }
    if (rc == 0 && p282_find_bytes(value, length, "traceoff:") != NULL) {
        rc = -P260_EPROTO;
    }
    if (rc == 0) {
        control->trigger_armed = 0U;
    }
    return rc;
}

static long p300_read_tracing_on(unsigned int *is_on) {
    if (is_on == NULL) return -P260_EPROTO;
    char value[8];
    size_t length = 0;
    long rc = p282_read_file(
        "/sys/kernel/tracing/instances/p282/tracing_on",
        value, sizeof(value), &length);
    if (rc != 0 || length != 2U || value[1] != '\\n'
        || (value[0] != '0' && value[0] != '1')) {
        return rc != 0 ? rc : -P260_EPROTO;
    }
    *is_on = value[0] == '1';
    return 0;
}

static long p300_close_recording_window(
    struct p282_trace_control *control) {
    if (!control->active || !control->trigger_armed
        || control->recording_window_closed) {
        return -P260_EPROTO;
    }
    unsigned int remaining = 0;
    long rc = p300_trigger_remaining(control, &remaining);
    if (rc == 0) rc = p300_trigger_remove(control);
    unsigned int tracing_on = 0;
    if (rc == 0) rc = p300_read_tracing_on(&tracing_on);
    if (rc == 0 && remaining == 0U && tracing_on != 0U) {
        rc = -P260_EPROTO;
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/events/p282/enable",
            "0\\n");
    }
    if (rc == 0) {
        rc = p282_write_control(
            "/sys/kernel/tracing/instances/p282/tracing_on", "0\\n");
    }
    if (rc == 0) {
        control->active = 0U;
        control->trigger_remaining_before_close = (uint8_t)remaining;
        control->tracing_on_before_disable = (uint8_t)tracing_on;
        control->recording_window_closed = 1U;
    }
    return rc;
}

"""


P300_CPU_STATS_PATHS = b"""static const char *const p300_cpu_stats_paths[32] = {
""" + b"".join(
    f'    "/sys/kernel/tracing/instances/p282/per_cpu/cpu{cpu}/stats",\n'.encode(
        "ascii"
    )
    for cpu in range(32)
) + b"};\n"


P300_STREAM_SUPPORT = br'''
#define P300_PREFIX_RECORD_CAPACITY 16U

static long p300_validate_closed_window(
    const struct p282_trace_control *control,
    const struct p282_bind_trace_result *result) {
    if (!control->recording_window_closed
        || control->trigger_remaining_before_close > 1U
        || control->tracing_on_before_disable > 1U) {
        return P300_DETAIL_TRIGGER_STATE_CONTRADICTION;
    }
    if (result->connect_done_seen) {
        return control->tracing_on_before_disable == 0U
            ? 0 : P300_DETAIL_TRIGGER_STATE_CONTRADICTION;
    }
    return control->trigger_remaining_before_close == 1U
            && control->tracing_on_before_disable == 1U
        ? 0 : P300_DETAIL_TRIGGER_STATE_CONTRADICTION;
}

struct p300_stream_state {
    struct p282_bind_trace_result *result;
    struct p282_trace_record prefix[P300_PREFIX_RECORD_CAPACITY];
    size_t prefix_count;
    uint64_t previous_counter;
    uint8_t have_previous;
};

static long p300_parse_header(
    const char *line,
    const char *line_end,
    struct p282_bind_trace_result *result) {
    static const char prefix[] =
        "# entries-in-buffer/entries-written:";
    size_t prefix_length = sizeof(prefix) - 1U;
    if ((size_t)(line_end - line) < prefix_length
        || !p260_bytes_equal(line, prefix, prefix_length)) {
        return 0;
    }
    if (result->header_seen) {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    const char *cursor = line + prefix_length;
    while (cursor < line_end && p282_is_space(*cursor)) ++cursor;
    const char *left_start = cursor;
    while (cursor < line_end && p282_is_digit(*cursor)) ++cursor;
    const char *left_end = cursor;
    if (cursor >= line_end || *cursor != '/') {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    ++cursor;
    const char *right_start = cursor;
    while (cursor < line_end && p282_is_digit(*cursor)) ++cursor;
    const char *right_end = cursor;
    if (right_start == right_end
        || (right_end < line_end && !p282_is_space(*right_end))) {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    uint64_t left = 0;
    uint64_t right = 0;
    long rc = p282_parse_unsigned(left_start, left_end, &left);
    if (rc == 0) rc = p282_parse_unsigned(right_start, right_end, &right);
    if (rc != 0) return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    result->header_seen = 1U;
    result->entries_in_buffer = left;
    result->entries_written = right;
    return 0;
}

static long p300_parse_event_record(
    const struct p282_trace_control *control,
    const char *line,
    const char *line_end,
    struct p282_trace_record *record) {
    const char *bracket = p282_line_find(line, line_end, "[");
    const char *close = bracket == NULL
        ? NULL : p282_line_find(bracket, line_end, "]");
    const char *marker = close == NULL
        ? NULL : p282_line_find(close, line_end, ": ");
    if (marker == NULL) return 1;
    const char *event_start = marker + cstr_len(": ");
    const char *event_end = event_start;
    while (event_end < line_end && *event_end != ':') ++event_end;
    if (event_end == line_end) return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    size_t event_index = control->event_count;
    for (size_t index = 0; index < control->event_count; ++index) {
        size_t length = cstr_len(control->events[index].name);
        if ((size_t)(event_end - event_start) == length
            && p260_bytes_equal(event_start, control->events[index].name, length)) {
            event_index = index;
            break;
        }
    }
    if (event_index == control->event_count) {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    *record = (struct p282_trace_record){
        .event_index = (uint8_t)event_index,
    };
    long rc = p282_parse_line_identity(
        line, line_end, marker, &record->pid, &record->counter);
#define P300_PARSE_SIGNED(name, member) \
    do { \
        if (rc == 0) rc = p282_parse_field( \
            event_end + 1, line_end, name "=", \
            &record->member, &record->has_##member); \
    } while (0)
#define P300_PARSE_UNSIGNED(name, member) \
    do { \
        if (rc == 0) rc = p298_parse_unsigned_field( \
            event_end + 1, line_end, name "=", \
            &record->member, &record->has_##member); \
    } while (0)
    P300_PARSE_SIGNED("on", on);
    P300_PARSE_SIGNED("rc", rc);
    P300_PARSE_SIGNED("link", link);
    P300_PARSE_SIGNED("run_stop", run_stop);
    P300_PARSE_SIGNED("devctrlhlt", devctrlhlt);
    P300_PARSE_SIGNED("coreidle", coreidle);
    P300_PARSE_SIGNED("prtcap", prtcap);
    P300_PARSE_SIGNED("susphy", susphy);
    P300_PARSE_SIGNED("connect_speed", connect_speed);
    P300_PARSE_UNSIGNED("dwc", dwc);
    P300_PARSE_UNSIGNED("evt", evt);
    P300_PARSE_UNSIGNED("devten", devten);
    P300_PARSE_UNSIGNED("gevntsiz", gevntsiz);
    P300_PARSE_UNSIGNED("gevntcount", gevntcount);
    P300_PARSE_UNSIGNED("evt_length", evt_length);
    P300_PARSE_UNSIGNED("evt_count", evt_count);
    P300_PARSE_UNSIGNED("evt_flags", evt_flags);
    P300_PARSE_UNSIGNED("raw", raw);
    P300_PARSE_UNSIGNED("low", low);
    P300_PARSE_UNSIGNED("type", type);
#undef P300_PARSE_UNSIGNED
#undef P300_PARSE_SIGNED
    return rc == 0 ? 0 : P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
}

static long p300_observe_pointer(
    struct p282_bind_trace_result *result,
    uint64_t dwc,
    uint64_t evt,
    int has_evt) {
    if (dwc == 0U || (has_evt && evt == 0U)) {
        return P300_DETAIL_FOREIGN_POINTER_CONTRADICTION;
    }
    if (result->observed_dwc != 0U && result->observed_dwc != dwc) {
        return P300_DETAIL_FOREIGN_POINTER_CONTRADICTION;
    }
    if (has_evt && result->observed_evt != 0U && result->observed_evt != evt) {
        return P300_DETAIL_FOREIGN_POINTER_CONTRADICTION;
    }
    result->observed_dwc = dwc;
    if (has_evt) result->observed_evt = evt;
    return 0;
}

static long p300_consume_event(
    struct p300_stream_state *state,
    const struct p282_trace_record *record) {
    struct p282_bind_trace_result *result = state->result;
    if (record->event_index >= P282_BIND_EVENT_COUNT
        || result->record_hits[record->event_index] == UINT64_MAX) {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    if ((record->event_index <= 10U && record->pid != 1)
        || (record->event_index > 10U && record->pid < 0)) {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    if (state->have_previous && record->counter <= state->previous_counter) {
        return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    state->have_previous = 1U;
    state->previous_counter = record->counter;
    ++result->record_hits[record->event_index];
    if (record->event_index <= 10U) {
        if (state->prefix_count == P300_PREFIX_RECORD_CAPACITY) {
            return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
        }
        state->prefix[state->prefix_count++] = *record;
        return 0;
    }
    if (record->event_index == 11U) {
        if (!record->has_dwc || !record->has_evt || result->irq_open) {
            return P300_DETAIL_IRQ_PAIRING_CONTRADICTION;
        }
        long rc = p300_observe_pointer(result, record->dwc, record->evt, 1);
        if (rc != 0) return rc;
        result->irq_open = 1U;
        if (result->irq_entries == UINT64_MAX) {
            return P300_DETAIL_IRQ_PAIRING_CONTRADICTION;
        }
        ++result->irq_entries;
        return 0;
    }
    if (record->event_index == 12U) {
        if (!record->has_rc || !result->irq_open) {
            return P300_DETAIL_IRQ_PAIRING_CONTRADICTION;
        }
        if (record->rc < 0 || record->rc > 2) {
            return P300_DETAIL_IRQ_RETURN_CONTRADICTION;
        }
        result->irq_open = 0U;
        if (result->irq_returns == UINT64_MAX) {
            return P300_DETAIL_IRQ_PAIRING_CONTRADICTION;
        }
        ++result->irq_returns;
        result->irq_return_mask |= UINT64_C(1) << (unsigned int)record->rc;
        return 0;
    }
    if (record->event_index == 13U) {
        if (!record->has_dwc || !record->has_evt
            || !record->has_evt_count || !record->has_evt_flags) {
            return P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION;
        }
        long rc = p300_observe_pointer(result, record->dwc, record->evt, 1);
        if (rc != 0) return rc;
        if (record->evt_count > 4096U || (record->evt_count & 3U) != 0U
            || record->evt_flags > 1U) {
            return P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION;
        }
        if (result->thread_entries == UINT64_MAX) {
            return P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION;
        }
        ++result->thread_entries;
        if ((record->evt_flags & 1U) == 0U || record->evt_count == 0U) {
            ++result->thread_empty_passes;
        } else {
            uint64_t entries = record->evt_count / 4U;
            if (result->expected_process_entries > UINT64_MAX - entries) {
                return P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION;
            }
            result->expected_process_entries += entries;
        }
        return 0;
    }
    if (!record->has_dwc || !record->has_raw || !record->has_low
        || !record->has_type || result->thread_entries == 0U) {
        return P300_DETAIL_RAW_EVENT_CONTRADICTION;
    }
    long rc = p300_observe_pointer(result, record->dwc, 0U, 0);
    if (rc != 0) return rc;
    if (record->raw > UINT32_MAX || record->low != 1U
        || (record->raw & 0xffU) != 1U
        || record->type != ((record->raw >> 8U) & 0xfU)) {
        return P300_DETAIL_RAW_EVENT_CONTRADICTION;
    }
    if (result->device_records == UINT64_MAX) {
        return P300_DETAIL_RAW_EVENT_CONTRADICTION;
    }
    ++result->device_records;
    if (record->type == 1U) {
        result->reset_seen = 1U;
    } else if (record->type == 2U) {
        if (result->connect_done_seen) {
            return P300_DETAIL_TRIGGER_STATE_CONTRADICTION;
        }
        result->connect_done_seen = 1U;
    } else {
        result->other_device_seen = 1U;
    }
    return 0;
}

static long p300_consume_trace_line(
    const struct p282_trace_control *control,
    struct p300_stream_state *state,
    const char *line,
    const char *line_end) {
    long rc = p300_parse_header(line, line_end, state->result);
    if (rc != 0 || (state->result->header_seen
        && (size_t)(line_end - line) >= 2U
        && line[0] == '#' && line[1] == ' ')) {
        return rc;
    }
    if (line == line_end || *line == '#') return 0;
    struct p282_trace_record record = {0};
    rc = p300_parse_event_record(control, line, line_end, &record);
    if (rc == 1) return P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    if (rc != 0) return rc;
    return p300_consume_event(state, &record);
}

static long p300_parse_bind_prefix(
    struct p300_stream_state *state,
    struct p282_bind_trace_result *result) {
    const struct p282_trace_record *records = state->prefix;
    size_t count = state->prefix_count;
    struct p282_trace_pair pull = {0};
    long rc = p282_pair_in_window(
        records, count, 2U, 3U, 1, 0, UINT64_MAX, 1, 1, &pull);
    if (rc != 0 || !pull.entered || !pull.returned || pull.rc != 0) {
        return P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
    }
    result->pullup_returned_zero = 1U;
    struct p282_trace_pair resume = {0};
    struct p282_trace_pair run = {0};
    struct p282_trace_pair start = {0};
    rc = p282_pair_in_window(
        records, count, 0U, 1U, 1,
        pull.entry_counter, pull.return_counter, 0, 0, &resume);
    if (rc == 0) rc = p282_pair_in_window(
        records, count, 4U, 5U, 1,
        pull.entry_counter, pull.return_counter, 1, 1, &run);
    if (rc == 0) rc = p282_pair_in_window(
        records, count, 7U, 8U, 1,
        pull.entry_counter, pull.return_counter, 0, 0, &start);
    if (rc != 0 || (resume.entered && !resume.returned)
        || (run.entered && !run.returned)
        || (resume.returned && resume.rc < 0)
        || !run.entered || run.rc != 0) {
        return P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
    }
    result->run_stop_seen = 1U;
    result->run_stop_rc = run.rc;
    if (resume.returned) {
        if (!(resume.entry_counter < run.entry_counter
              && run.return_counter < resume.return_counter)) {
            return P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
        }
        result->branch = P282_BIND_RESUME_NESTED;
    } else {
        result->branch = P282_BIND_DIRECT;
    }
    result->start_entered = start.entered;
    result->start_returned = start.returned;
    result->start_rc = start.rc;
    if (start.entered) {
        if (start.entry_counter >= run.entry_counter
            || (start.returned && start.return_counter >= run.entry_counter)) {
            return P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
        }
        const struct p282_trace_record *start_record = NULL;
        for (size_t index = 0; index < count; ++index) {
            if (records[index].event_index == 7U
                && records[index].counter == start.entry_counter) {
                start_record = &records[index];
                break;
            }
        }
        if (start_record == NULL || !start_record->has_dwc
            || start_record->dwc == 0U) {
            return P300_DETAIL_FOREIGN_POINTER_CONTRADICTION;
        }
        result->start_dwc = start_record->dwc;
        uint64_t upper = start.returned
            ? start.return_counter : run.entry_counter;
        for (size_t index = 0; index < count; ++index) {
            if (records[index].event_index == 9U
                && records[index].counter > start.entry_counter
                && records[index].counter < upper) {
                if (result->ep_enable_hits == UINT8_MAX) {
                    return P298_DETAIL_EP_ENABLE_HIT_CONTRADICTION;
                }
                ++result->ep_enable_hits;
            }
        }
    }
    unsigned int state_matches = 0;
    unsigned int config_matches = 0;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index == 6U
            && record->counter > run.entry_counter
            && record->counter < run.return_counter) {
            if (!record->has_link || !record->has_run_stop
                || !record->has_devctrlhlt || !record->has_coreidle
                || !record->has_prtcap || !record->has_susphy
                || !record->has_connect_speed || state_matches != 0U
                || record->link < 0 || record->link > 15
                || record->run_stop < 0 || record->run_stop > 1
                || record->devctrlhlt < 0 || record->devctrlhlt > 1
                || record->coreidle < 0 || record->coreidle > 1
                || record->prtcap < 0 || record->prtcap > 3
                || record->susphy < 0 || record->susphy > 1
                || record->connect_speed < 0 || record->connect_speed > 7) {
                return P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
            }
            result->snapshot_seen = 1U;
            result->link_state = (uint8_t)record->link;
            result->run_stop = (uint8_t)record->run_stop;
            result->devctrlhlt = (uint8_t)record->devctrlhlt;
            result->coreidle = (uint8_t)record->coreidle;
            result->prtcap = (uint8_t)record->prtcap;
            result->susphy = (uint8_t)record->susphy;
            result->connect_speed = (uint8_t)record->connect_speed;
            ++state_matches;
        }
        if (record->event_index == 10U
            && record->counter > run.entry_counter
            && record->counter < run.return_counter) {
            if (!record->has_dwc || !record->has_evt || !record->has_devten
                || !record->has_gevntsiz || !record->has_gevntcount
                || !record->has_evt_length || !record->has_evt_count
                || !record->has_evt_flags || config_matches != 0U) {
                return P300_DETAIL_EVENT_CONFIG_CONTRADICTION;
            }
            result->event_config_seen = 1U;
            result->event_dwc = record->dwc;
            result->event_evt = record->evt;
            result->devten = record->devten;
            result->gevntsiz = record->gevntsiz;
            result->gevntcount = record->gevntcount;
            result->evt_length = record->evt_length;
            result->evt_count = record->evt_count;
            result->evt_flags = record->evt_flags;
            ++config_matches;
        }
    }
    if (state_matches != 1U || config_matches != 1U) {
        return config_matches != 1U
            ? P300_DETAIL_EVENT_CONFIG_CONTRADICTION
            : P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION;
    }
    if (result->event_dwc == 0U || result->event_evt == 0U
        || (result->start_dwc != 0U && result->event_dwc != result->start_dwc)
        || (result->observed_dwc != 0U
            && result->observed_dwc != result->event_dwc)
        || (result->observed_evt != 0U
            && result->observed_evt != result->event_evt)) {
        return P300_DETAIL_FOREIGN_POINTER_CONTRADICTION;
    }
    if ((result->devten & 6U) != 6U
        || result->evt_length != 4096U
        || (result->gevntsiz & 0xffffU) != result->evt_length
        || result->evt_count > result->evt_length
        || (result->evt_count & 3U) != 0U
        || result->evt_flags > 1U
        || (result->gevntcount & 0xfffcU) > result->evt_length) {
        return P300_DETAIL_EVENT_CONFIG_CONTRADICTION;
    }
    if (result->thread_entries != 0U && result->irq_entries == 0U) {
        return P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION;
    }
    return 0;
}

static long p300_parse_bind_stream(
    const struct p282_trace_control *control,
    struct p282_bind_trace_result *result,
    int final) {
    *result = (struct p282_bind_trace_result){
        .source_consistent = 1U,
        .branch = P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    struct p300_stream_state state = {.result = result};
    long fd = sys_openat(
        "/sys/kernel/tracing/instances/p282/trace", O_RDONLY | O_CLOEXEC, 0);
    if (fd < 0) return P300_DETAIL_TRACE_STREAM_READ_FAILED;
    char input[P300_TRACE_READ_CAPACITY];
    char line[P300_TRACE_LINE_CAPACITY];
    size_t line_length = 0;
    long detail = 0;
    for (;;) {
        long amount = sys_read((int)fd, input, sizeof(input));
        if (amount == -P260_EINTR) continue;
        if (amount < 0) {
            detail = P300_DETAIL_TRACE_STREAM_READ_FAILED;
            break;
        }
        if (amount == 0) break;
        for (long index = 0; index < amount; ++index) {
            char value = input[index];
            if (value == '\n') {
                detail = p300_consume_trace_line(
                    control, &state, line, line + line_length);
                line_length = 0;
                if (detail != 0) break;
                continue;
            }
            if (line_length == sizeof(line)) {
                detail = P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
                break;
            }
            line[line_length++] = value;
        }
        if (detail != 0) break;
    }
    long close_rc = sys_close((int)fd);
    if (detail == 0 && close_rc != 0) {
        detail = P300_DETAIL_TRACE_STREAM_READ_FAILED;
    }
    if (detail == 0 && line_length != 0U) {
        detail = P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    if (detail == 0 && !result->header_seen) {
        detail = P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    if (detail == 0) detail = p300_parse_bind_prefix(&state, result);
    if (detail == 0 && final
        && (result->irq_open || result->irq_entries != result->irq_returns)) {
        detail = P300_DETAIL_IRQ_PAIRING_CONTRADICTION;
    }
    if (detail == 0 && final
        && result->entries_in_buffer != result->entries_written) {
        detail = P300_DETAIL_TRACE_RING_LOSS;
    }
    uint64_t parsed_records = 0;
    for (size_t index = 0;
         detail == 0 && final && index < control->event_count;
         ++index) {
        if (parsed_records > UINT64_MAX - result->record_hits[index]) {
            detail = P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
        } else {
            parsed_records += result->record_hits[index];
        }
    }
    if (detail == 0 && final
        && parsed_records != result->entries_in_buffer) {
        detail = P300_DETAIL_TRACE_STREAM_LINE_MALFORMED;
    }
    return detail;
}

static long p300_parse_stats_field(
    const char *value,
    size_t length,
    const char *name,
    uint64_t *result) {
    if (p282_count_bytes(value, length, name) != 1U) return -P260_EPROTO;
    const char *start = p282_find_bytes(value, length, name);
    const char *end = value + length;
    start += cstr_len(name);
    while (start < end && p282_is_space(*start)) ++start;
    const char *number_end = start;
    while (number_end < end && p282_is_digit(*number_end)) ++number_end;
    return p282_parse_unsigned(start, number_end, result);
}

static long p300_ring_stats_clean(void) {
    unsigned int seen = 0;
    for (size_t cpu = 0; cpu < 32U; ++cpu) {
        char value[2048];
        size_t length = 0;
        long rc = p282_read_file(
            p300_cpu_stats_paths[cpu], value, sizeof(value), &length);
        if (rc == -ENOENT) continue;
        if (rc != 0) return P300_DETAIL_TRACE_STREAM_READ_FAILED;
        uint64_t overrun = 0;
        uint64_t commit_overrun = 0;
        uint64_t dropped = 0;
        rc = p300_parse_stats_field(value, length, "\noverrun:", &overrun);
        if (rc == 0) rc = p300_parse_stats_field(
            value, length, "\ncommit overrun:", &commit_overrun);
        if (rc == 0) rc = p300_parse_stats_field(
            value, length, "\ndropped events:", &dropped);
        if (rc != 0 || overrun != 0U || commit_overrun != 0U || dropped != 0U) {
            return P300_DETAIL_TRACE_RING_LOSS;
        }
        ++seen;
    }
    return seen == 0U ? P300_DETAIL_TRACE_RING_LOSS : 0;
}

static long p300_profile_relations(
    const struct p282_trace_control *control,
    struct p282_bind_trace_result *result) {
    if (!control->recording_window_closed) {
        return P300_DETAIL_PROFILE_RELATION_CONTRADICTION;
    }
    for (size_t index = 0; index < control->event_count; ++index) {
        if (control->profile_hits[index] < result->record_hits[index]) {
            return P300_DETAIL_PROFILE_RELATION_CONTRADICTION;
        }
    }
    if (!result->connect_done_seen) {
        for (size_t index = 11U; index <= 13U; ++index) {
            if (control->profile_hits[index] != result->record_hits[index]) {
                return P300_DETAIL_PROFILE_RELATION_CONTRADICTION;
            }
        }
        if (control->profile_hits[14] != result->expected_process_entries
            || control->profile_hits[14] < result->device_records) {
            return P300_DETAIL_PROFILE_RELATION_CONTRADICTION;
        }
        result->nondevice_entries =
            control->profile_hits[14] - result->device_records;
    }
    return 0;
}

static long p300_ingress_class(
    const struct p282_bind_trace_result *result) {
    if (!result->event_config_seen || !result->snapshot_seen) {
        return P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION;
    }
    if (result->connect_done_seen) return result->reset_seen ? 10 : 9;
    if (result->reset_seen) return 8;
    if (result->other_device_seen) return 7;
    if (result->thread_entries != 0U) {
        if (result->expected_process_entries == 0U
            && result->thread_empty_passes == result->thread_entries) return 5;
        if (result->nondevice_entries != 0U) return 6;
        return P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION;
    }
    if ((result->irq_return_mask & (UINT64_C(1) << 2U)) != 0U) return 4;
    if ((result->irq_return_mask & (UINT64_C(1) << 1U)) != 0U) return 3;
    if (result->irq_entries != 0U
        && result->irq_return_mask == (UINT64_C(1) << 0U)) return 2;
    if (result->irq_entries == 0U) {
        return (result->gevntcount & 0xfffcU) == 0U ? 0 : 1;
    }
    return P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION;
}
'''


P300_TRACE_READ_SNAPSHOT = b"""static long p282_trace_read_snapshot(
    struct p282_trace_control *control,
    int require_profile) {
    if (control->event_count == P282_BIND_EVENT_COUNT) {
        if (!require_profile) return 0;
        long rc = p282_read_file(
            p282_profile_path,
            p282_profile_buffer,
            sizeof(p282_profile_buffer),
            &p282_profile_length);
        return rc != 0 ? rc : p282_profile_clean(control);
    }
    long rc = p282_read_file(
        "/sys/kernel/tracing/instances/p282/trace",
        p282_trace_buffer,
        sizeof(p282_trace_buffer),
        &p282_trace_length);
    if (rc != 0 || !require_profile) {
        return rc;
    }
    rc = p282_read_file(
        p282_profile_path,
        p282_profile_buffer,
        sizeof(p282_profile_buffer),
        &p282_profile_length);
    return rc != 0 ? rc : p282_profile_clean(control);
}
"""


P300_PROFILE_MATCHES = b"""static long p298_profile_matches(
    const struct p282_trace_control *control,
    struct p282_bind_trace_result *result) {
    return p300_profile_relations(control, result);
}
"""


P300_FINISH_OBSERVER = b"""static long p298_finish_observer(
    struct p282_trace_control *control,
    struct p282_bind_trace_result *result,
    long source_detail) {
    (void)source_detail;
    long detail = 0;
    long close_rc = p300_close_recording_window(control);
    if (close_rc != 0) {
        detail = P300_DETAIL_TRIGGER_STATE_CONTRADICTION;
    }
    if (detail == 0) {
        detail = p300_parse_bind_stream(control, result, 1);
    }
    if (detail == 0) {
        detail = p300_validate_closed_window(control, result);
    }
    if (detail == 0) {
        detail = p300_ring_stats_clean();
    }
    if (detail == 0) {
        long profile_rc = p282_read_file(
            p282_profile_path,
            p282_profile_buffer,
            sizeof(p282_profile_buffer),
            &p282_profile_length);
        if (profile_rc != 0) {
            detail = P298_DETAIL_FINAL_TRACE_READBACK_FAILED;
        } else if (p282_profile_clean(control) != 0) {
            detail = P300_DETAIL_PROFILE_RELATION_CONTRADICTION;
        }
    }
    if (detail == 0) {
        detail = p298_profile_matches(control, result);
    }
    long cleanup_rc = p282_trace_cleanup(control);
    if (cleanup_rc != 0) {
        return P298_DETAIL_FINAL_TRACE_CLEANUP_UNVERIFIED;
    }
    return detail;
}
"""


def transform_runtime_include(data: bytes) -> bytes:
    """Runtime transformation is assembled below in source-sized units."""
    value = base.replace_exact(
        data,
        b"#define P282_RECORD_CAPACITY 64U\n",
        b"#define P282_RECORD_CAPACITY 64U\n"
        b"#define P300_TRACE_LINE_CAPACITY 1024U\n"
        b"#define P300_TRACE_READ_CAPACITY 4096U\n"
        b"#define P300_IRQ_RETURN_MAXACTIVE 32U\n",
        label="P3.00 streaming capacities",
    )
    value = base.replace_exact(
        value,
        b"    uint8_t active;\n"
        b"    uint64_t profile_hits[P282_CYCLE_EVENT_COUNT];\n",
        b"    uint8_t active;\n"
        b"    uint8_t trigger_armed;\n"
        b"    uint8_t recording_window_closed;\n"
        b"    uint8_t trigger_remaining_before_close;\n"
        b"    uint8_t tracing_on_before_disable;\n"
        b"    uint64_t profile_hits[P282_CYCLE_EVENT_COUNT];\n",
        label="P3.00 trigger and recording-window state",
    )
    record_start = value.find(b"struct p282_trace_record {\n")
    record_end = value.find(b"};\n", record_start) + len(b"};\n")
    if record_start < 0 or record_end <= len(b"};\n"):
        raise TelemetryTransformError("P3.00 trace record struct differs")
    value = value[:record_start] + P300_TRACE_RECORD + value[record_end:]
    result_start = value.find(b"struct p282_bind_trace_result {\n")
    result_end = value.find(b"};\n", result_start) + len(b"};\n")
    if result_start < 0 or result_end <= len(b"};\n"):
        raise TelemetryTransformError("P3.00 bind result struct differs")
    value = value[:result_start] + P300_BIND_RESULT_STRUCT + value[result_end:]
    value = base.replace_exact(
        value,
        inherited.P298_CAPTURE_DECLARATIONS,
        P300_CAPTURE_DECLARATIONS,
        label="P3.00 capture state",
    )
    event_path_start, event_path_end = base._function_span(  # noqa: SLF001
        value, b"p282_event_path"
    )
    value = value[:event_path_end] + P300_TRIGGER_HELPERS + value[event_path_end:]
    value = base.replace_exact(
        value,
        b"static char p282_profile_buffer[P282_PROFILE_CAPACITY];\n",
        b"static char p282_profile_buffer[P282_PROFILE_CAPACITY];\n"
        + P300_CPU_STATS_PATHS,
        label="P3.00 per-CPU stats paths",
    )
    bind_parser_start, _bind_parser_end = base._function_span(  # noqa: SLF001
        value, b"p282_parse_bind_result"
    )
    value = value[:bind_parser_start] + P300_STREAM_SUPPORT + value[bind_parser_start:]
    value = base.replace_function(
        value,
        b"p282_parse_bind_result",
        b"""static long p282_parse_bind_result(
    const struct p282_trace_control *control,
    struct p282_bind_trace_result *result) {
    return p300_parse_bind_stream(control, result, 0);
}
""",
    )
    value = base.replace_exact(
        value,
        b"    rc = p282_verify_buffer_size();\n"
        b"    if (rc != 0) {\n"
        b"        return rc;\n"
        b"    }\n"
        b"    for (size_t index = 0; index < control->event_count; ++index) {\n",
        b"    rc = p282_verify_buffer_size();\n"
        b"    if (rc != 0) {\n"
        b"        return rc;\n"
        b"    }\n"
        b"    if (control->event_count == P282_BIND_EVENT_COUNT) {\n"
        b"        rc = p260_expect_value(\n"
        b"            \"/sys/kernel/tracing/instances/p282/options/overwrite\",\n"
        b"            \"1\");\n"
        b"        if (rc != 0) {\n"
        b"            return rc;\n"
        b"        }\n"
        b"    }\n"
        b"    for (size_t index = 0; index < control->event_count; ++index) {\n",
        label="P3.00 overwrite readback",
    )
    value = base.replace_exact(
        value,
        b"    while (control->registered_count != 0U) {\n",
        b"    if (control->trigger_armed) {\n"
        b"        long rc = p300_trigger_remove(control);\n"
        b"        if (rc != 0 && result == 0) {\n"
        b"            result = rc;\n"
        b"        }\n"
        b"    }\n"
        b"    while (control->registered_count != 0U) {\n",
        label="P3.00 trigger cleanup",
    )
    value = base.replace_exact(
        value,
        b"    if (rc == 0) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/buffer_size_kb\",\n"
        b"            \"64\\n\");\n"
        b"    }\n"
        b"    for (size_t index = 0; rc == 0 && index < event_count; ++index) {\n",
        b"    if (rc == 0) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/buffer_size_kb\",\n"
        b"            \"64\\n\");\n"
        b"    }\n"
        b"    if (rc == 0 && phase == P282_PHASE_BIND) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/options/overwrite\",\n"
        b"            \"1\\n\");\n"
        b"    }\n"
        b"    for (size_t index = 0; rc == 0 && index < event_count; ++index) {\n",
        label="P3.00 overwrite setup",
    )
    value = base.replace_exact(
        value,
        b"    if (rc == 0) {\n"
        b"        rc = p282_clear_trace();\n"
        b"    }\n"
        b"    if (rc == 0) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/events/p282/enable\",\n"
        b"            \"1\\n\");\n"
        b"    }\n"
        b"    if (rc == 0) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/tracing_on\", \"1\\n\");\n"
        b"    }\n"
        b"    if (rc == 0) {\n"
        b"        control->active = 1;\n"
        b"        return 0;\n"
        b"    }\n",
        b"    if (rc == 0) {\n"
        b"        rc = p282_clear_trace();\n"
        b"    }\n"
        b"    if (rc == 0) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/tracing_on\", \"1\\n\");\n"
        b"        if (rc == 0) control->active = 1U;\n"
        b"    }\n"
        b"    if (rc == 0) {\n"
        b"        rc = p282_write_control(\n"
        b"            \"/sys/kernel/tracing/instances/p282/events/p282/enable\",\n"
        b"            \"1\\n\");\n"
        b"    }\n"
        b"    if (rc == 0 && phase == P282_PHASE_BIND) {\n"
        b"        long trigger_rc = p300_trigger_arm(control);\n"
        b"        if (trigger_rc != 0) {\n"
        b"            warning = P300_DETAIL_TRIGGER_SETUP_OR_READBACK;\n"
        b"        }\n"
        b"        rc = trigger_rc;\n"
        b"    }\n"
        b"    if (rc == 0) {\n"
        b"        return 0;\n"
        b"    }\n",
        label="P3.00 closed recording-window setup",
    )
    value = base.replace_function(
        value, b"p282_trace_read_snapshot", P300_TRACE_READ_SNAPSHOT
    )
    value = base.replace_function(
        value, b"p298_profile_matches", P300_PROFILE_MATCHES
    )
    value = base.replace_function(
        value, b"p298_finish_observer", P300_FINISH_OBSERVER
    )
    value = base.replace_exact(
        value,
        b"    if (setup_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {\n"
        b"        return P298_DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED;\n"
        b"    }\n",
        b"    if (setup_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {\n"
        b"        return P298_DETAIL_BIND_TRACE_SETUP_CLEANUP_UNVERIFIED;\n"
        b"    }\n"
        b"    if (setup_rc == P300_DETAIL_TRIGGER_SETUP_OR_READBACK) {\n"
        b"        return P300_DETAIL_TRIGGER_SETUP_OR_READBACK;\n"
        b"    }\n",
        label="P3.00 setup failure detail",
    )
    value = base.replace_exact(
        value,
        b"    if (parse_rc != 0) {\n"
        b"        p298_fail_with_trace(\n"
        b"            control, P298_DETAIL_BIND_TRACE_SOURCE_CONTRADICTION);\n"
        b"    }\n"
        b"    long start_detail = p298_start_result_detail(&trace_result);\n",
        b"    if (parse_rc != 0) {\n"
        b"        p298_fail_with_trace(control, parse_rc);\n"
        b"    }\n"
        b"    long start_detail = p298_start_result_detail(&trace_result);\n",
        label="P3.00 initial parser detail",
    )
    value = base.replace_exact(
        value,
        b"    g_p294_capture.connect_speed = trace_result.connect_speed;\n",
        b"    g_p294_capture.connect_speed = trace_result.connect_speed;\n"
        b"    g_p294_capture.event_dwc = trace_result.event_dwc;\n"
        b"    g_p294_capture.event_evt = trace_result.event_evt;\n"
        b"    g_p294_capture.devten = trace_result.devten;\n"
        b"    g_p294_capture.gevntsiz = trace_result.gevntsiz;\n"
        b"    g_p294_capture.evt_length = trace_result.evt_length;\n",
        label="P3.00 config capture",
    )
    value = base.replace_exact(
        value,
        b"                || final_result.connect_speed\n"
        b"                    != g_p294_capture.connect_speed) {\n",
        b"                || final_result.connect_speed\n"
        b"                    != g_p294_capture.connect_speed\n"
        b"                || final_result.event_dwc != g_p294_capture.event_dwc\n"
        b"                || final_result.event_evt != g_p294_capture.event_evt\n"
        b"                || final_result.devten != g_p294_capture.devten\n"
        b"                || final_result.gevntsiz != g_p294_capture.gevntsiz\n"
        b"                || final_result.evt_length != g_p294_capture.evt_length) {\n",
        label="P3.00 final config identity",
    )
    value = base.replace_exact(
        value,
        b"            unsigned int event_mask =\n"
        b"                (final_result.reset_seen ? 1U : 0U)\n"
        b"                | (final_result.connect_done_seen ? 2U : 0U);\n"
        b"            uint16_t first_detail = (uint16_t)(\n"
        b"                P294_LINK_DETAIL_BASE\n"
        b"                + event_mask * 16U\n"
        b"                + final_result.link_state);\n",
        b"            long ingress_class = p300_ingress_class(&final_result);\n"
        b"            if (ingress_class < 0 || ingress_class > 10) {\n"
        b"                p290_fail_next(\n"
        b"                    P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION);\n"
        b"            }\n"
        b"            uint16_t first_detail = (uint16_t)(\n"
        b"                P294_LINK_DETAIL_BASE\n"
        b"                + (unsigned int)ingress_class * 16U\n"
        b"                + final_result.link_state);\n",
        label="P3.00 ingress classification",
    )
    return value


def transform_artifacts(source: Mapping[str, bytes]) -> dict[str, bytes]:
    result = dict(source)
    result["candidate_patch"] = transform_candidate_patch(source["candidate_patch"])
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
