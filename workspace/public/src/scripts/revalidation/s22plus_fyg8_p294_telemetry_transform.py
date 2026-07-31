#!/usr/bin/env python3
"""Transform P2.92 materialized artifacts into P2.94 telemetry artifacts."""

from __future__ import annotations

from typing import Mapping

import s22plus_fyg8_p252_source_contract as p252
import s22plus_fyg8_p294_telemetry_spec as spec


class TelemetryTransformError(ValueError):
    pass


def replace_exact(
    data: bytes,
    old: bytes,
    new: bytes,
    *,
    count: int = 1,
    label: str,
) -> bytes:
    actual = data.count(old)
    if actual != count:
        raise TelemetryTransformError(
            f"{label} replacement count {actual}, expected {count}"
        )
    return data.replace(old, new)


def _function_span(data: bytes, name: bytes) -> tuple[int, int]:
    needle = name + b"("
    starts = []
    cursor = 0
    while True:
        found = data.find(needle, cursor)
        if found < 0:
            break
        line = data.rfind(b"\n", 0, found) + 1
        if b"static" in data[line:found]:
            starts.append(line)
        cursor = found + len(needle)
    if len(starts) != 1:
        raise TelemetryTransformError(
            f"C function {name.decode()} definition count {len(starts)}"
        )
    start = starts[0]
    brace = data.find(b"{", start)
    if brace < 0:
        raise TelemetryTransformError(f"C function {name.decode()} has no body")
    depth = 0
    index = brace
    while index < len(data):
        if data[index:index + 1] == b"{":
            depth += 1
        elif data[index:index + 1] == b"}":
            depth -= 1
            if depth == 0:
                end = index + 1
                if data[end:end + 1] == b"\n":
                    end += 1
                return start, end
        index += 1
    raise TelemetryTransformError(f"C function {name.decode()} is unterminated")


def replace_function(data: bytes, name: bytes, replacement: bytes) -> bytes:
    start, end = _function_span(data, name)
    return data[:start] + replacement + data[end:]


def _replace_table(
    data: bytes, marker: bytes, replacement: bytes, *, label: str
) -> bytes:
    start = data.find(marker)
    if start < 0 or data.find(marker, start + 1) >= 0:
        raise TelemetryTransformError(f"{label} table marker differs")
    end = data.find(b"};\n", start)
    if end < 0:
        raise TelemetryTransformError(f"{label} table terminator is absent")
    end += len(b"};\n")
    return data[:start] + replacement + data[end:]


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
        (
            f"    {{{ordinal}U, {outcome}U, 0x{detail:x}U}},\n"
        ).encode("ascii")
        for ordinal, outcome, detail in spec.exact_detail_rules()
    )
    return (
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n"
        + rows
        + b"};\n"
    )


KERNEL_TUPLE_ALLOWED = b"""+static noinline __used bool s22_fyg8_p290_tuple_allowed(
+	size_t ordinal, u8 outcome, u16 detail)
+{
+	(void)ordinal;
+	(void)outcome;
+	(void)detail;
+	return false;
+}
"""


CLIENT_TUPLE_ALLOWED = b"""static int p288_tuple_allowed(
    size_t ordinal, uint8_t outcome, uint16_t detail) {
    (void)ordinal;
    (void)outcome;
    (void)detail;
    return 0;
}
"""


CLIENT_TERMINAL_API = b"""long s22_p294_checkpoint_progress_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail) {
    return p288_publish_next(
        client, S22_P233_OUTCOME_PROGRESS, detail, 1, position_ordinal);
}

long s22_p294_checkpoint_terminal_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail) {
    uint8_t outcome = detail >= 0xcc0U && detail <= 0xcc3U
        ? S22_P233_OUTCOME_SUCCESS
        : S22_P233_OUTCOME_FAILURE;
    return p288_publish_next(client, outcome, detail, 1, position_ordinal);
}

"""


def transform_checkpoint_client(data: bytes) -> bytes:
    value = _replace_table(
        data,
        b"static const struct p288_detail_rule k_p288_detail_rules[] = {\n",
        _client_rule_table(),
        label="P2.94 userspace detail",
    )
    value = replace_function(
        value, b"p288_tuple_allowed", CLIENT_TUPLE_ALLOWED
    )
    value = replace_exact(
        value,
        b"    if (step->kind == S22_P248_STEP_TERMINAL) {\n"
        b"        return outcome == S22_P233_OUTCOME_SUCCESS && detail == 0U;\n"
        b"    }\n",
        b"    if (step->kind == S22_P248_STEP_TERMINAL) {\n"
        b"        return 0;\n"
        b"    }\n",
        label="P2.94 userspace terminal fallback",
    )
    insertion = b"long s22_p290_checkpoint_failure_next(\n"
    if value.count(insertion) != 1:
        raise TelemetryTransformError("P2.94 terminal API insertion differs")
    return value.replace(insertion, CLIENT_TERMINAL_API + insertion)


def transform_checkpoint_header(data: bytes) -> bytes:
    anchor = b"long s22_p290_checkpoint_failure_next(\n"
    prototype = b"""long s22_p294_checkpoint_progress_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail);
long s22_p294_checkpoint_terminal_position(
    struct s22_r4w1e_checkpoint_client *client,
    uint8_t position_ordinal,
    uint16_t detail);
"""
    return replace_exact(
        data, anchor, prototype + anchor, label="P2.94 client prototypes"
    )


def transform_position_header(data: bytes) -> bytes:
    anchor = b"#define S22_P290_POSITION_TERMINAL 106U\n\n#endif\n"
    addition = b"""#define S22_P290_POSITION_TERMINAL 106U

#define S22_P294_POSITION_COUNT S22_P290_POSITION_COUNT
#define S22_P294_POSITION_USBLNKST 105U
#define S22_P294_POSITION_FINAL_STATE 106U

#endif
"""
    return replace_exact(
        data, anchor, addition, label="P2.94 position aliases"
    )


def transform_trace_descriptor(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 6U\n",
        b"#define P282_CYCLE_EVENT_COUNT 17U\n"
        b"#define P282_BIND_EVENT_COUNT 7U\n",
        label="P2.94 trace event counts",
    )
    cycle_anchor = (
        b'    {"outer_sm_work_out", "r:p282/outer_sm_work_out '
        b'dwc3_msm:dwc3_otg_sm_work rc=$retval:s32\\n", '
        b'"common_pid > 0"},\n};\n\n'
        b"static const struct p282_event_descriptor p282_bind_events[] = {\n"
    )
    cycle_replacement = (
        cycle_anchor.split(b"};\n\n", 1)[0]
        + b'    {"wrapper_vbus_snapshot", "p:p282/wrapper_vbus_snapshot '
        b'dwc3_msm:s22_p294_wrapper_vbus_snapshot present=%x0:u32 '
        b'vbus=%x1:u32\\n", "common_pid > 0"},\n};\n\n'
        b"static const struct p282_event_descriptor p282_bind_events[] = {\n"
    )
    value = replace_exact(
        value,
        cycle_anchor,
        cycle_replacement,
        label="P2.94 cycle snapshot descriptor",
    )
    bind_anchor = (
        b'    {"run_out", "r:p282/run_out dwc3_gadget_run_stop '
        b'rc=$retval:s32\\n", "common_pid > 0"},\n};\n'
    )
    bind_replacement = (
        bind_anchor[:-len(b"};\n")]
        + b'    {"dwc3_state_snapshot", "p:p282/dwc3_state_snapshot '
        b's22_p294_dwc3_state_snapshot link=%x0:u32 run_stop=%x1:u32 '
        b'devctrlhlt=%x2:u32 coreidle=%x3:u32 prtcap=%x4:u32 '
        b'susphy=%x5:u32 connect_speed=%x6:u32\\n", '
        b'"common_pid > 0"},\n};\n'
    )
    return replace_exact(
        value,
        bind_anchor,
        bind_replacement,
        label="P2.94 bind snapshot descriptor",
    )


TRACE_RECORD_FIELDS = b"""    uint8_t has_present;
    uint8_t has_vbus;
    uint8_t has_link;
    uint8_t has_run_stop;
    uint8_t has_devctrlhlt;
    uint8_t has_coreidle;
    uint8_t has_prtcap;
    uint8_t has_susphy;
    uint8_t has_connect_speed;
    int32_t present;
    int32_t vbus;
    int32_t link;
    int32_t run_stop;
    int32_t devctrlhlt;
    int32_t coreidle;
    int32_t prtcap;
    int32_t susphy;
    int32_t connect_speed;
"""


TRACE_PARSE_FIELDS = b"""            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "present=", &record.present, &record.has_present);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "vbus=", &record.vbus, &record.has_vbus);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "link=", &record.link, &record.has_link);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "run_stop=", &record.run_stop, &record.has_run_stop);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "devctrlhlt=", &record.devctrlhlt,
                    &record.has_devctrlhlt);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "coreidle=", &record.coreidle, &record.has_coreidle);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "prtcap=", &record.prtcap, &record.has_prtcap);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "susphy=", &record.susphy, &record.has_susphy);
            }
            if (rc == 0) {
                rc = p282_parse_field(event_end + 1, line_end,
                    "connect_speed=", &record.connect_speed,
                    &record.has_connect_speed);
            }
"""


CAPTURE_DECLARATIONS = b"""struct p294_capture_values {
    uint8_t wrapper_seen;
    uint8_t dwc3_seen;
    uint8_t link_state;
    uint8_t run_stop;
    uint8_t devctrlhlt;
    uint8_t coreidle;
    uint8_t prtcap;
    uint8_t susphy;
    uint8_t connect_speed;
    uint8_t vbus_valid;
};

static struct p294_capture_values g_p294_capture;

"""


PAIR_AND_CLASSIFIER = b"""#define P294_LINK_DETAIL_BASE 0xc60U
#define P294_FINAL_DETAIL_BASE 0xc70U
#define P294_MISMATCH_DETAIL_BASE 0xf40U
#define P294_STATE_SPEED_CONTRADICTION 0xf4fU
#define P294_CONNECT_SPEED_CONTRADICTION 0xf50U

static long p294_publish_final_pair(
    uint16_t first_detail, uint16_t terminal_detail) {
    long first_rc = s22_p294_checkpoint_progress_position(
        &g_checkpoint, S22_P294_POSITION_USBLNKST, first_detail);
    if (first_rc != 0) {
        return first_rc;
    }
    return s22_p294_checkpoint_terminal_position(
        &g_checkpoint, S22_P294_POSITION_FINAL_STATE, terminal_detail);
}

static long p294_terminal_detail(
    unsigned int state,
    unsigned int speed,
    uint16_t *detail) {
    unsigned int mismatch = 0;
    if (!g_p294_capture.dwc3_seen || !g_p294_capture.wrapper_seen) {
        return -P260_EPROTO;
    }
    if (g_p294_capture.run_stop != 1U) mismatch |= 1U;
    if (g_p294_capture.devctrlhlt != 0U) mismatch |= 2U;
    if (g_p294_capture.prtcap != 2U) mismatch |= 4U;
    if (g_p294_capture.vbus_valid != 1U) mismatch |= 8U;
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


FINAL_WAIT_FUNCTION = b"""static __attribute__((noreturn)) void p282_wait_final_pair(
    unsigned int repair_class,
    unsigned int bind_branch) {
    (void)p282_classify_final_pair;
    _Static_assert(
        sizeof(p282_descriptor_udc_states)
                / sizeof(p282_descriptor_udc_states[0])
            == P282_STATE_COUNT,
        "P2.94 generated UDC state table cardinality");
    _Static_assert(
        sizeof(p282_descriptor_usb_speeds)
                / sizeof(p282_descriptor_usb_speeds[0])
            == P282_SPEED_COUNT,
        "P2.94 generated USB speed table cardinality");

    if (repair_class != P282_REPAIR_POWER_HELPER_OFF_ON_ZERO
        || bind_branch != P282_BIND_DIRECT) {
        p290_fail_next(-P260_EPROTO);
    }
    p290_progress_position(
        S22_P290_POSITION_FINAL_SAMPLING_STARTED, 0U);
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(P282_FINAL_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        p290_fail_next(rc);
    }
    unsigned int previous_state = 0;
    unsigned int previous_speed = 0;
    unsigned int current_state = 0;
    unsigned int current_speed = 0;
    int have_previous = 0;
    for (;;) {
        p260_revalidate_or_fail(P282_STAGE_FINAL);
        rc = p282_read_final_pair(&current_state, &current_speed);
        p260_revalidate_or_fail(P282_STAGE_FINAL);
        if (rc != 0) {
            p290_fail_next(rc);
        }
        int stable = have_previous
            && previous_state == current_state
            && previous_speed == current_speed;
        int configured_high = current_state == P282_STATE_CONFIGURED
            && current_speed == P282_SPEED_HIGH;
        if ((stable && configured_high) || p282_deadline_expired(&deadline)) {
            if (!have_previous) {
                p290_fail_next(P282_DETAIL_FINAL_STATE_SPEED_UNSTABLE);
            }
            uint16_t terminal_detail = 0;
            rc = p294_terminal_detail(
                current_state, current_speed, &terminal_detail);
            if (rc != 0) {
                p290_fail_next(rc);
            }
            uint16_t first_detail = (uint16_t)(
                P294_LINK_DETAIL_BASE + g_p294_capture.link_state);
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


def _extend_result_structs(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"    uint8_t outer_open;\n};\n\n"
        b"struct p282_bind_trace_result {\n",
        b"    uint8_t outer_open;\n"
        b"    uint8_t wrapper_seen;\n"
        b"    uint8_t wrapper_vbus_valid;\n"
        b"};\n\n"
        b"struct p282_bind_trace_result {\n",
        label="P2.94 cycle snapshot result",
    )
    return replace_exact(
        value,
        b"    unsigned int branch;\n};\n\n",
        b"    unsigned int branch;\n"
        b"    uint8_t snapshot_seen;\n"
        b"    uint8_t link_state;\n"
        b"    uint8_t run_stop;\n"
        b"    uint8_t devctrlhlt;\n"
        b"    uint8_t coreidle;\n"
        b"    uint8_t prtcap;\n"
        b"    uint8_t susphy;\n"
        b"    uint8_t connect_speed;\n"
        b"};\n\n",
        label="P2.94 DWC3 snapshot result",
    )


def _extend_cycle_parser(data: bytes) -> bytes:
    start, end = _function_span(data, b"p282_parse_cycle_result")
    function = data[start:end]
    anchor = b"    if (rc == 0) {\n        rc = p286_outer_state(records, count, result);\n    }\n"
    addition = b"""    if (rc == 0 && result->restart_worker.entered) {
        unsigned int matches = 0;
        uint64_t upper = result->restart_worker.returned
            ? result->restart_worker.return_counter : UINT64_MAX;
        for (size_t index = 0; index < count; ++index) {
            const struct p282_trace_record *record = &records[index];
            if (record->event_index != 16U
                || record->pid != restart_pid
                || record->counter <= result->restart_worker.entry_counter
                || record->counter >= upper) {
                continue;
            }
            if (!record->has_present || !record->has_vbus
                || record->present != 1 || record->vbus < 0
                || record->vbus > 1 || matches != 0U) {
                rc = -P260_EPROTO;
                break;
            }
            result->wrapper_seen = 1U;
            result->wrapper_vbus_valid = (uint8_t)record->vbus;
            ++matches;
        }
        if (rc == 0 && matches != 1U) {
            rc = -P260_EPROTO;
        }
    }
    if (rc == 0) {
        rc = p286_outer_state(records, count, result);
    }
"""
    function = replace_exact(
        function, anchor, addition, label="P2.94 cycle snapshot parser"
    )
    return data[:start] + function + data[end:]


def _extend_bind_parser(data: bytes) -> bytes:
    start, end = _function_span(data, b"p282_parse_bind_result")
    function = data[start:end]
    anchor = b"    return 0;\n}\n"
    if not function.endswith(anchor):
        raise TelemetryTransformError("P2.94 bind parser tail differs")
    addition = b"""    unsigned int matches = 0;
    for (size_t index = 0; index < count; ++index) {
        const struct p282_trace_record *record = &records[index];
        if (record->event_index != 6U
            || record->counter <= run.entry_counter
            || record->counter >= run.return_counter) {
            continue;
        }
        if (record->pid != 1 || !record->has_link
            || !record->has_run_stop || !record->has_devctrlhlt
            || !record->has_coreidle || !record->has_prtcap
            || !record->has_susphy || !record->has_connect_speed
            || record->link < 0 || record->link > 15
            || record->run_stop < 0 || record->run_stop > 1
            || record->devctrlhlt < 0 || record->devctrlhlt > 1
            || record->coreidle < 0 || record->coreidle > 1
            || record->prtcap < 0 || record->prtcap > 3
            || record->susphy < 0 || record->susphy > 1
            || record->connect_speed < 0 || record->connect_speed > 7
            || matches != 0U) {
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
    if (matches != 1U) {
        return -P260_EPROTO;
    }
    return 0;
}
"""
    function = function[:-len(anchor)] + addition
    return data[:start] + function + data[end:]


def transform_runtime_include(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"    uint8_t has_rc;\n"
        b"    int32_t on;\n",
        b"    uint8_t has_rc;\n" + TRACE_RECORD_FIELDS + b"    int32_t on;\n",
        label="P2.94 trace record fields",
    )
    value = replace_exact(
        value,
        b"            if (rc != 0) {\n                return rc;\n            }\n"
        b"            if (\n                have_previous\n",
        TRACE_PARSE_FIELDS
        + b"            if (rc != 0) {\n                return rc;\n            }\n"
        b"            if (\n                have_previous\n",
        label="P2.94 trace field parser",
    )
    value = _extend_result_structs(value)
    value = _extend_cycle_parser(value)
    value = _extend_bind_parser(value)
    value = replace_exact(
        value,
        b"static unsigned int p282_cycle_restart(\n",
        CAPTURE_DECLARATIONS + PAIR_AND_CLASSIFIER
        + b"static unsigned int p282_cycle_restart(\n",
        label="P2.94 capture state and pair helpers",
    )
    value = replace_exact(
        value,
        b"    cycle->observed = final_result;\n"
        b"    p290_progress_position(\n",
        b"    cycle->observed = final_result;\n"
        b"    g_p294_capture.wrapper_seen = final_result.wrapper_seen;\n"
        b"    g_p294_capture.vbus_valid = final_result.wrapper_vbus_valid;\n"
        b"    p290_progress_position(\n",
        label="P2.94 wrapper snapshot handoff",
    )
    value = replace_exact(
        value,
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_BIND_TRACE_CLASSIFIED,\n"
        b"        classified > 0 ? (uint16_t)classification.detail : 0U);\n"
        b"    return observation.bind_branch;\n",
        b"    uint16_t bind_detail = classified > 0\n"
        b"        ? (uint16_t)classification.detail : 0U;\n"
        b"    if (bind_detail != P282_DETAIL_HELPER_OFF_ON_ZERO_DIRECT_RUN_STOP) {\n"
        b"        p290_fail_next(bind_detail != 0U ? bind_detail : -P260_EPROTO);\n"
        b"    }\n"
        b"    if (!trace_result.snapshot_seen) {\n"
        b"        p290_fail_next(-P260_EPROTO);\n"
        b"    }\n"
        b"    g_p294_capture.dwc3_seen = trace_result.snapshot_seen;\n"
        b"    g_p294_capture.link_state = trace_result.link_state;\n"
        b"    g_p294_capture.run_stop = trace_result.run_stop;\n"
        b"    g_p294_capture.devctrlhlt = trace_result.devctrlhlt;\n"
        b"    g_p294_capture.coreidle = trace_result.coreidle;\n"
        b"    g_p294_capture.prtcap = trace_result.prtcap;\n"
        b"    g_p294_capture.susphy = trace_result.susphy;\n"
        b"    g_p294_capture.connect_speed = trace_result.connect_speed;\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_BIND_TRACE_CLASSIFIED, bind_detail);\n"
        b"    return observation.bind_branch;\n",
        label="P2.94 canonical bind precondition",
    )
    value = replace_function(
        value, b"p282_wait_final_pair", FINAL_WAIT_FUNCTION
    )
    value = replace_exact(
        value,
        b"    p282_wait_final_pair(repair_class, bind_branch);\n\n"
        b"    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"    p290_park_after_confirmed_publication();\n",
        b"    p282_wait_final_pair(repair_class, bind_branch);\n",
        label="P2.94 terminal pair owns completion",
    )
    return value


def transform_candidate_patch(data: bytes) -> bytes:
    value = _replace_table(
        data,
        b"+static const struct s22_fyg8_p290_detail_rule\n"
        b"+s22_fyg8_p290_detail_rules[] __used = {\n",
        _kernel_rule_table(),
        label="P2.94 kernel detail",
    )
    value = replace_function(
        value, b"s22_fyg8_p290_tuple_allowed", KERNEL_TUPLE_ALLOWED
    )
    value = replace_exact(
        value,
        b"+\tif (ordinal + 1 == count)\n"
        b"+\t\treturn outcome == S22_FYG8_E1_SUCCESS && !detail;\n",
        b"+\tif (ordinal + 1 == count)\n"
        b"+\t\treturn false;\n",
        label="P2.94 kernel terminal fallback",
    )
    value = p252._recount_kernel_patch_hunks(value)  # noqa: SLF001
    if not value.endswith(b"\n"):
        raise TelemetryTransformError("P2.94 candidate patch lacks newline")
    return value + DRIVER_PATCH


def _driver_patch() -> bytes:
    value = b"""diff --git a/kernel_platform/common/drivers/usb/dwc3/gadget.c b/kernel_platform/common/drivers/usb/dwc3/gadget.c
--- a/kernel_platform/common/drivers/usb/dwc3/gadget.c
+++ b/kernel_platform/common/drivers/usb/dwc3/gadget.c
@@ -2488,6 +2488,19 @@ static void __dwc3_gadget_set_speed(struct dwc3 *dwc)
 \tdwc3_writel(dwc->regs, DWC3_DCFG, reg);
 }
@P294_CONTEXT_BLANK@
+static noinline __used void s22_p294_dwc3_state_snapshot(
+\t\tu32 link_state, u32 run_stop, u32 devctrlhlt,
+\t\tu32 coreidle, u32 prtcap, u32 susphy, u32 connect_speed)
+{
+\tbarrier_data(link_state);
+\tbarrier_data(run_stop);
+\tbarrier_data(devctrlhlt);
+\tbarrier_data(coreidle);
+\tbarrier_data(prtcap);
+\tbarrier_data(susphy);
+\tbarrier_data(connect_speed);
+}
+
 static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)
 {
 \tu32\t\t\treg;
@@ -2527,6 +2540,22 @@ static int dwc3_gadget_run_stop(struct dwc3 *dwc, int is_on)
 \t\tdev_err(dwc->dev, "failed to %s controller\\n",
 \t\t\t\tis_on ? "start" : "stop");
 \t\treturn -ETIMEDOUT;
+\t}
+
+\tif (is_on) {
+\t\tu32 dctl = dwc3_readl(dwc->regs, DWC3_DCTL);
+\t\tu32 dsts = dwc3_readl(dwc->regs, DWC3_DSTS);
+\t\tu32 gctl = dwc3_readl(dwc->regs, DWC3_GCTL);
+\t\tu32 gusb2 = dwc3_readl(dwc->regs, DWC3_GUSB2PHYCFG(0));
+
+\t\ts22_p294_dwc3_state_snapshot(
+\t\t\tDWC3_DSTS_USBLNKST(dsts),
+\t\t\t!!(dctl & DWC3_DCTL_RUN_STOP),
+\t\t\t!!(dsts & DWC3_DSTS_DEVCTRLHLT),
+\t\t\t!!(dsts & DWC3_DSTS_COREIDLE),
+\t\t\tDWC3_GCTL_PRTCAP(gctl),
+\t\t\t!!(gusb2 & DWC3_GUSB2PHYCFG_SUSPHY),
+\t\t\tdsts & DWC3_DSTS_CONNECTSPD);
 \t}
@P294_CONTEXT_BLANK@
 \treturn 0;
diff --git a/kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c b/kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c
--- a/kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c
+++ b/kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c
@@ -6604,11 +6604,22 @@ static int dwc3_msm_start_host(struct dwc3_msm *mdwc, int on)
 \treturn 0;
 }
@P294_CONTEXT_BLANK@
+static noinline __used void s22_p294_wrapper_vbus_snapshot(
+\t\tu32 present, u32 vbus_valid)
+{
+\tbarrier_data(present);
+\tbarrier_data(vbus_valid);
+}
+
 static void dwc3_override_vbus_status(struct dwc3_msm *mdwc, bool vbus_present)
 {
 \t/* Update OTG VBUS Valid from HSPHY to controller */
 \tdwc3_msm_write_reg_field(mdwc->base, HS_PHY_CTRL_REG,
 \t\t\tUTMI_OTG_VBUS_VALID, !!vbus_present);
+\ts22_p294_wrapper_vbus_snapshot(
+\t\t!!vbus_present,
+\t\t!!(dwc3_msm_read_reg(mdwc->base, HS_PHY_CTRL_REG) &
+\t\t\tUTMI_OTG_VBUS_VALID));
@P294_CONTEXT_BLANK@
 \t/* Update VBUS Valid from SSPHY to controller */
 \tif (vbus_present) {
"""
    marker = b"@P294_CONTEXT_BLANK@"
    if value.count(marker) != 4:
        raise TelemetryTransformError("P2.94 driver context markers differ")
    return value.replace(marker, b" ")


DRIVER_PATCH = _driver_patch()


def transform_artifacts(
    baseline: Mapping[str, bytes],
) -> dict[str, bytes]:
    result = dict(baseline)
    result["candidate_patch"] = transform_candidate_patch(
        baseline["candidate_patch"]
    )
    result["checkpoint_client"] = transform_checkpoint_client(
        baseline["checkpoint_client"]
    )
    result["p290_checkpoint_header"] = transform_checkpoint_header(
        baseline["p290_checkpoint_header"]
    )
    result["p290_position_header"] = transform_position_header(
        baseline["p290_position_header"]
    )
    result["trace_descriptor_header"] = transform_trace_descriptor(
        baseline["trace_descriptor_header"]
    )
    result["p290_e3_runtime_include"] = transform_runtime_include(
        baseline["p290_e3_runtime_include"]
    )
    return result
