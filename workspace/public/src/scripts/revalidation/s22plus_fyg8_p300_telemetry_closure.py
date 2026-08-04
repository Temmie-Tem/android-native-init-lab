#!/usr/bin/env python3
"""Host-only closure for the P3.00 event-ingress/IRQ observer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p286_userspace_build as userspace
import s22plus_fyg8_p298_source_contract as p298_contract
import s22plus_fyg8_p298_telemetry_closure as inherited
import s22plus_fyg8_p300_telemetry_generator as generator
import s22plus_fyg8_p300_telemetry_model as model
import s22plus_fyg8_p300_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p300_telemetry_closure_v1"
VERDICT = "PASS_P300_EVENT_INGRESS_IRQ_TELEMETRY_CLOSURE_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P300-SOURCE-CHECK-V1"
).digest()[:16]
SOURCE_CHECK_UNSAT_TAG = model.unsat_record(
    spec.PROFILE, SOURCE_CHECK_RUN_ID
)[len(model.UNSAT_FAMILY) :]


class ClosureError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _generated(root: Path) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=spec.PROFILE,
    )


def _compile_and_run(source: bytes, label: str) -> str:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise ClosureError("host C compiler is unavailable")
    with tempfile.TemporaryDirectory(prefix=f"s22-p300-{label}-") as tmp:
        directory = Path(tmp)
        source_path = directory / f"{label}.c"
        output = directory / label
        source_path.write_bytes(source)
        compiled = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source_path),
                "-o",
                str(output),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compiled.returncode != 0:
            raise ClosureError(
                f"P3.00 {label} host compile failed: "
                + compiled.stderr.decode("utf-8", "replace")[-5000:]
            )
        executed = subprocess.run(
            [str(output)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if executed.returncode != 0:
        raise ClosureError(
            f"P3.00 {label} execution failed rc={executed.returncode}: "
            + executed.stderr.decode("utf-8", "replace")[-2000:]
        )
    return executed.stdout.decode("ascii", "replace")


def _classification_tu(runtime: bytes) -> bytes:
    structures = b"".join(
        inherited._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"struct p282_trace_record {\n",
            b"struct p282_trace_control {\n",
            b"struct p282_bind_trace_result {\n",
            b"struct p300_stream_state {\n",
        )
    )
    functions = b"".join(
        inherited._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static long p300_observe_pointer(\n",
            b"static long p300_consume_event(\n",
            b"static long p300_validate_closed_window(\n",
            b"static long p300_profile_relations(\n",
            b"static long p300_ingress_class(\n",
        )
    )
    return (
        b"#include <limits.h>\n#include <stdint.h>\n#include <stdio.h>\n"
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 15U\n"
        b"#define P300_PREFIX_RECORD_CAPACITY 16U\n"
        b"#define P300_DETAIL_TRIGGER_STATE_CONTRADICTION 0xf74U\n"
        b"#define P300_DETAIL_TRACE_STREAM_LINE_MALFORMED 0xf76U\n"
        b"#define P300_DETAIL_FOREIGN_POINTER_CONTRADICTION 0xf79U\n"
        b"#define P300_DETAIL_IRQ_PAIRING_CONTRADICTION 0xf7aU\n"
        b"#define P300_DETAIL_IRQ_RETURN_CONTRADICTION 0xf7bU\n"
        b"#define P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION 0xf7cU\n"
        b"#define P300_DETAIL_RAW_EVENT_CONTRADICTION 0xf7dU\n"
        b"#define P300_DETAIL_PROFILE_RELATION_CONTRADICTION 0xf7eU\n"
        b"#define P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION 0xf7fU\n"
        b"struct p282_event_descriptor;\n"
        + structures
        + functions
        + br'''
static struct p282_bind_trace_result class_fixture(unsigned int value) {
    struct p282_bind_trace_result result = {
        .snapshot_seen = 1U,
        .event_config_seen = 1U,
    };
    switch (value) {
    case 0: break;
    case 1: result.gevntcount = 4U; break;
    case 2:
        result.irq_entries = 1U;
        result.irq_return_mask = UINT64_C(1) << 0U;
        break;
    case 3:
        result.irq_entries = 1U;
        result.irq_return_mask = UINT64_C(1) << 1U;
        break;
    case 4:
        result.irq_entries = 1U;
        result.irq_return_mask = UINT64_C(1) << 2U;
        break;
    case 5:
        result.thread_entries = 1U;
        result.thread_empty_passes = 1U;
        break;
    case 6:
        result.thread_entries = 1U;
        result.expected_process_entries = 1U;
        result.nondevice_entries = 1U;
        break;
    case 7:
        result.thread_entries = 1U;
        result.expected_process_entries = 1U;
        result.device_records = 1U;
        result.other_device_seen = 1U;
        break;
    case 8: result.reset_seen = 1U; break;
    case 9: result.connect_done_seen = 1U; break;
    case 10:
        result.reset_seen = 1U;
        result.connect_done_seen = 1U;
        break;
    }
    return result;
}

static int classifications(void) {
    for (unsigned int value = 0; value < 11U; ++value) {
        struct p282_bind_trace_result result = class_fixture(value);
        if (p300_ingress_class(&result) != (long)value) return 10 + value;
    }
    struct p282_bind_trace_result invalid = {0};
    if (p300_ingress_class(&invalid)
        != P300_DETAIL_INGRESS_CLASSIFICATION_CONTRADICTION) return 30;
    return 0;
}

static int consume_faults(void) {
    struct p282_bind_trace_result result = {0};
    struct p300_stream_state state = {.result = &result};
    struct p282_trace_record irq = {
        .event_index = 11U, .has_dwc = 1U, .has_evt = 1U,
        .counter = 1U, .dwc = 1U, .evt = 2U,
    };
    if (p300_consume_event(&state, &irq) != 0) return 41;
    irq.counter = 2U;
    if (p300_consume_event(&state, &irq)
        != P300_DETAIL_IRQ_PAIRING_CONTRADICTION) return 42;
    struct p282_trace_record out = {
        .event_index = 12U, .has_rc = 1U, .counter = 3U, .rc = 2,
    };
    if (p300_consume_event(&state, &out) != 0) return 43;
    if (result.irq_entries != 1U || result.irq_returns != 1U
        || result.irq_return_mask != (UINT64_C(1) << 2U)) return 44;

    result = (struct p282_bind_trace_result){0};
    state = (struct p300_stream_state){.result = &result};
    if (p300_consume_event(&state, &out)
        != P300_DETAIL_IRQ_PAIRING_CONTRADICTION) return 45;
    out.rc = 3;
    out.counter = 4U;
    result.irq_open = 1U;
    if (p300_consume_event(&state, &out)
        != P300_DETAIL_IRQ_RETURN_CONTRADICTION) return 46;

    result = (struct p282_bind_trace_result){0};
    state = (struct p300_stream_state){.result = &result};
    struct p282_trace_record thread = {
        .event_index = 13U,
        .has_dwc = 1U, .has_evt = 1U,
        .has_evt_count = 1U, .has_evt_flags = 1U,
        .counter = 1U, .dwc = 1U, .evt = 2U,
        .evt_count = 4U, .evt_flags = 0U,
    };
    if (p300_consume_event(&state, &thread) != 0
        || result.thread_empty_passes != 1U) return 47;
    thread.evt_count = 0U;
    thread.evt_flags = 1U;
    thread.counter = 2U;
    if (p300_consume_event(&state, &thread) != 0
        || result.thread_empty_passes != 2U) return 48;
    thread.evt_count = 2U;
    thread.counter = 3U;
    if (p300_consume_event(&state, &thread)
        != P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION) return 49;
    thread.evt_count = 4U;
    thread.evt_flags = 2U;
    thread.counter = 4U;
    if (p300_consume_event(&state, &thread)
        != P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION) return 50;

    result = (struct p282_bind_trace_result){0};
    state = (struct p300_stream_state){.result = &result};
    struct p282_trace_record raw = {
        .event_index = 14U,
        .has_dwc = 1U, .has_raw = 1U, .has_low = 1U, .has_type = 1U,
        .counter = 1U, .dwc = 1U, .raw = 0x101U, .low = 1U, .type = 1U,
    };
    if (p300_consume_event(&state, &raw)
        != P300_DETAIL_RAW_EVENT_CONTRADICTION) return 51;
    result.thread_entries = 1U;
    raw.counter = 2U;
    if (p300_consume_event(&state, &raw) != 0 || !result.reset_seen) return 52;
    raw.raw = 0x201U;
    raw.type = 2U;
    raw.counter = 3U;
    if (p300_consume_event(&state, &raw) != 0
        || !result.connect_done_seen) return 53;
    raw.counter = 4U;
    if (p300_consume_event(&state, &raw)
        != P300_DETAIL_TRIGGER_STATE_CONTRADICTION) return 54;
    raw.dwc = 3U;
    raw.type = 3U;
    raw.raw = 0x301U;
    raw.counter = 5U;
    if (p300_consume_event(&state, &raw)
        != P300_DETAIL_FOREIGN_POINTER_CONTRADICTION) return 55;
    return 0;
}

static int profile_relations(void) {
    struct p282_trace_control control = {.recording_window_closed = 1U};
    struct p282_bind_trace_result result = {0};
    result.record_hits[11] = 1U;
    result.record_hits[12] = 1U;
    result.record_hits[13] = 1U;
    result.record_hits[14] = 1U;
    result.expected_process_entries = 2U;
    result.device_records = 1U;
    for (unsigned int i = 0; i < P282_BIND_EVENT_COUNT; ++i) {
        control.profile_hits[i] = result.record_hits[i];
    }
    control.profile_hits[14] = 2U;
    control.event_count = P282_BIND_EVENT_COUNT;
    if (p300_profile_relations(&control, &result) != 0
        || result.nondevice_entries != 1U) return 61;
    control.profile_hits[11] = 2U;
    if (p300_profile_relations(&control, &result)
        != P300_DETAIL_PROFILE_RELATION_CONTRADICTION) return 62;
    result.connect_done_seen = 1U;
    if (p300_profile_relations(&control, &result) != 0) return 63;
    control.profile_hits[14] = 0U;
    if (p300_profile_relations(&control, &result)
        != P300_DETAIL_PROFILE_RELATION_CONTRADICTION) return 64;
    control.recording_window_closed = 0U;
    if (p300_profile_relations(&control, &result)
        != P300_DETAIL_PROFILE_RELATION_CONTRADICTION) return 65;
    return 0;
}

static int recording_window_states(void) {
    struct p282_trace_control control = {
        .recording_window_closed = 1U,
        .trigger_remaining_before_close = 1U,
        .tracing_on_before_disable = 1U,
    };
    struct p282_bind_trace_result result = {0};
    if (p300_validate_closed_window(&control, &result) != 0) return 71;
    control.recording_window_closed = 0U;
    if (p300_validate_closed_window(&control, &result)
        != P300_DETAIL_TRIGGER_STATE_CONTRADICTION) return 72;
    control.recording_window_closed = 1U;
    control.tracing_on_before_disable = 0U;
    if (p300_validate_closed_window(&control, &result)
        != P300_DETAIL_TRIGGER_STATE_CONTRADICTION) return 73;
    result.connect_done_seen = 1U;
    if (p300_validate_closed_window(&control, &result) != 0) return 74;
    control.trigger_remaining_before_close = 0U;
    if (p300_validate_closed_window(&control, &result) != 0) return 75;
    control.tracing_on_before_disable = 1U;
    if (p300_validate_closed_window(&control, &result)
        != P300_DETAIL_TRIGGER_STATE_CONTRADICTION) return 76;
    return 0;
}

int main(void) {
    int rc = classifications();
    if (rc == 0) rc = consume_faults();
    if (rc == 0) rc = profile_relations();
    if (rc == 0) rc = recording_window_states();
    if (rc != 0) return rc;
    printf(
        "classes=11 irq-pairing=1 thread-empty-variants=2 "
        "raw=1 profile=1 window=1\n");
    return 0;
}
'''
    )


def audit_runtime_classification(runtime: bytes) -> dict[str, Any]:
    expected = (
        "classes=11 irq-pairing=1 thread-empty-variants=2 "
        "raw=1 profile=1 window=1\n"
    )
    actual = _compile_and_run(_classification_tu(runtime), "classification")
    if actual != expected:
        raise ClosureError(
            f"P3.00 runtime classification differs: {actual!r}"
        )
    return {
        "ingress_classes_executed": 11,
        "irq_pairing_faults_executed": True,
        "thread_empty_source_semantics_executed": True,
        "raw_mask_and_pointer_faults_executed": True,
        "profile_cutoff_relations_executed": True,
        "recording_window_faults_executed": True,
        "verified": True,
    }


def _stream_parser_tu(runtime: bytes) -> bytes:
    structures = b"".join(
        inherited._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"struct p282_trace_record {\n",
            b"struct p282_trace_control {\n",
            b"struct p282_bind_trace_result {\n",
        )
    )
    functions = b"".join(
        inherited._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static const char *p282_find_bytes(\n",
            b"static int p282_is_digit(char value) {\n",
            b"static int p282_is_space(char value) {\n",
            b"static long p282_parse_unsigned(\n"
            b"    const char *start,\n"
            b"    const char *end,\n"
            b"    uint64_t *result) {\n",
            b"static long p282_parse_signed(\n",
            b"static const char *p282_line_find(\n",
            b"static long p282_parse_field(\n",
            b"static long p298_parse_unsigned_field(\n",
            b"static long p282_parse_line_identity(\n",
            b"static long p300_parse_header(\n",
            b"static long p300_parse_event_record(\n",
        )
    )
    return (
        b"#include <errno.h>\n#include <limits.h>\n#include <stdint.h>\n"
        b"#include <stdio.h>\n#include <string.h>\n"
        b"#define P260_EPROTO 71\n#define P260_EOVERFLOW 75\n"
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 15U\n"
        b"#define P300_DETAIL_TRACE_STREAM_LINE_MALFORMED 0xf76U\n"
        b"struct p282_event_descriptor { const char *name; };\n"
        + structures
        + br'''
static const struct p282_event_descriptor events[P282_BIND_EVENT_COUNT] = {
    {"resume_in"}, {"resume_out"}, {"pull_in"}, {"pull_out"},
    {"run_in"}, {"run_out"}, {"dwc3_state_snapshot"},
    {"gadget_start_in"}, {"gadget_start_out"}, {"ep_enable_in"},
    {"event_config"}, {"irq_in"}, {"irq_out"}, {"thread_in"},
    {"device_event_in"},
};
static size_t cstr_len(const char *value) { return strlen(value); }
static int p260_bytes_equal(const void *left, const void *right, size_t length) {
    return memcmp(left, right, length) == 0;
}
'''
        + functions
        + br'''
static long parse(
    const struct p282_trace_control *control,
    const char *line,
    struct p282_trace_record *record) {
    return p300_parse_event_record(control, line, line + strlen(line), record);
}

int main(void) {
    struct p282_bind_trace_result result = {0};
    const char *header = "# entries-in-buffer/entries-written: 3/3   #P:32";
    if (p300_parse_header(header, header + strlen(header), &result) != 0
        || result.entries_in_buffer != 3U || result.entries_written != 3U
        || !result.header_seen) return 10;
    if (p300_parse_header(header, header + strlen(header), &result)
        != P300_DETAIL_TRACE_STREAM_LINE_MALFORMED) return 11;
    result = (struct p282_bind_trace_result){0};
    const char *bad_header =
        "# entries-in-buffer/entries-written: 3/3x   #P:32";
    if (p300_parse_header(
            bad_header, bad_header + strlen(bad_header), &result)
        != P300_DETAIL_TRACE_STREAM_LINE_MALFORMED) return 12;

    struct p282_trace_control control = {
        .events = events, .event_count = P282_BIND_EVENT_COUNT,
    };
    struct p282_trace_record record = {0};
    const char *config =
        "init-1 [000] 10: event_config: dwc=1 evt=2 devten=6 "
        "gevntsiz=4096 gevntcount=0 evt_length=4096 evt_count=0 evt_flags=0";
    if (parse(&control, config, &record) != 0
        || record.event_index != 10U || record.pid != 1 || record.counter != 10U
        || !record.has_dwc || record.dwc != 1U
        || !record.has_evt_flags || record.evt_flags != 0U) return 20;
    const char *irq = "swapper-0 [003] 11: irq_in: evt=2 dwc=1";
    if (parse(&control, irq, &record) != 0
        || record.event_index != 11U || record.pid != 0 || record.counter != 11U
        || record.evt != 2U || record.dwc != 1U) return 21;
    const char *ret = "swapper-0 [003] 12: irq_out: rc=-22";
    if (parse(&control, ret, &record) != 0
        || record.event_index != 12U || !record.has_rc || record.rc != -22)
        return 22;
    const char *raw =
        "irq-42 [003] 13: device_event_in: dwc=1 raw=513 low=1 type=2";
    if (parse(&control, raw, &record) != 0
        || record.event_index != 14U || record.raw != 513U
        || record.low != 1U || record.type != 2U) return 23;
    const char *unknown = "init-1 [000] 14: unknown: rc=0";
    if (parse(&control, unknown, &record)
        != P300_DETAIL_TRACE_STREAM_LINE_MALFORMED) return 24;
    const char *duplicate =
        "init-1 [000] 15: irq_in: evt=2 dwc=1 dwc=2";
    if (parse(&control, duplicate, &record)
        != P300_DETAIL_TRACE_STREAM_LINE_MALFORMED) return 25;
    printf("header=3 event-config=1 irq-pid0=1 signed-return=1 raw=1 faults=3\n");
    return 0;
}
'''
    )


def audit_stream_parser(runtime: bytes) -> dict[str, Any]:
    expected = (
        "header=3 event-config=1 irq-pid0=1 signed-return=1 raw=1 faults=3\n"
    )
    actual = _compile_and_run(_stream_parser_tu(runtime), "stream-parser")
    if actual != expected:
        raise ClosureError(f"P3.00 stream parser differs: {actual!r}")
    return {
        "header_count_and_syntax_executed": True,
        "pid_zero_irq_executed": True,
        "signed_return_executed": True,
        "raw_bitfield_fields_executed": True,
        "unknown_and_duplicate_fields_rejected": True,
        "verified": True,
    }


def _lifecycle_tu(runtime: bytes) -> bytes:
    control = inherited._struct(  # noqa: SLF001
        runtime, b"struct p282_trace_control {\n"
    )
    functions = b"".join(
        inherited._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static long p300_trigger_path(",
            b"static long p300_trigger_remaining(",
            b"static long p300_trigger_readback(",
            b"static long p300_trigger_arm(",
            b"static long p300_trigger_remove(",
            b"static long p300_read_tracing_on(",
            b"static long p300_close_recording_window(",
            b"static long p300_validate_closed_window(",
            b"static long p282_trace_cleanup(",
            b"static long p282_trace_setup(",
        )
    )
    return (
        br'''
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define P260_EPROTO EPROTO
#define P282_PATH_CAPACITY 512U
#define P282_PROFILE_CAPACITY 4096U
#define P282_CYCLE_EVENT_COUNT 16U
#define P282_ROLE_EVENT_COUNT 4U
#define P282_BIND_EVENT_COUNT 15U
#define P282_AT_REMOVEDIR 0x200
#define P282_TRACEFS_MAGIC 0x74726163L
#define P282_PHASE_ROLE 1U
#define P282_PHASE_CYCLE 2U
#define P282_PHASE_BIND 3U
#define P282_CONTROL_TRACE_CONTROL_UNAVAILABLE 0xf60L
#define P282_CONTROL_TRACE_REGISTRATION_UNAVAILABLE 0xf61L
#define P282_CONTROL_TRACE_CLEANUP_UNVERIFIED 0xf62L
#define P300_DETAIL_TRIGGER_SETUP_OR_READBACK 0xf73L
#define P300_DETAIL_TRIGGER_STATE_CONTRADICTION 0xf74L

struct p282_event_descriptor {
    const char *name;
    const char *definition;
    const char *filter;
};
'''
        + control
        + br'''
struct p282_bind_trace_result {
    uint8_t connect_done_seen;
};
struct statfs_probe {
    long f_type;
};

static const struct p282_event_descriptor
    p282_role_events[P282_ROLE_EVENT_COUNT] = {{0}};
static const struct p282_event_descriptor
    p282_cycle_events[P282_CYCLE_EVENT_COUNT] = {{0}};
static const struct p282_event_descriptor
    p282_bind_events[P282_BIND_EVENT_COUNT] = {{0}};
static const char p282_global_events_path[] = "global-events";
static const char p282_global_group_root[] = "global-group";
static const char p282_instance_root[] = "instance";
static const char p282_trace_root[] = "trace-root";
static char p282_definitions_buffer[4096];

enum operation {
    OP_TRACE_ON = 1,
    OP_GROUP_ON = 2,
    OP_TRIGGER_ARM = 3,
    OP_TRIGGER_COUNT = 4,
    OP_TRIGGER_REMOVE = 5,
    OP_TRACING_READ = 6,
    OP_GROUP_OFF = 7,
    OP_TRACE_OFF = 8,
};
static unsigned int operations[256];
static size_t operation_count;
static unsigned int tracing_on_state;
static unsigned int group_enabled_state;
static unsigned int trigger_installed_state;
static unsigned int trigger_remaining_state;
static unsigned int instance_active;
static unsigned int mount_active;
static unsigned int fire_during_remove;
static unsigned int malformed_trigger_once;
static unsigned int malformed_tracing_once;
static unsigned int fail_arm_once;
static unsigned int fail_remove_once;

static void record_operation(unsigned int operation) {
    if (operation_count < sizeof(operations) / sizeof(operations[0])) {
        operations[operation_count++] = operation;
    }
}

static long operation_index(unsigned int operation, size_t start) {
    for (size_t index = start; index < operation_count; ++index) {
        if (operations[index] == operation) return (long)index;
    }
    return -1;
}

static void reset_log(void) {
    memset(operations, 0, sizeof(operations));
    operation_count = 0;
}

static void reset_state(void) {
    reset_log();
    tracing_on_state = 0;
    group_enabled_state = 0;
    trigger_installed_state = 0;
    trigger_remaining_state = 0;
    instance_active = 0;
    mount_active = 0;
    fire_during_remove = 0;
    malformed_trigger_once = 0;
    malformed_tracing_once = 0;
    fail_arm_once = 0;
    fail_remove_once = 0;
}

static int no_residue(const struct p282_trace_control *control) {
    return tracing_on_state == 0U
        && group_enabled_state == 0U
        && trigger_installed_state == 0U
        && instance_active == 0U
        && mount_active == 0U
        && control->registered_count == 0U
        && control->active == 0U
        && control->trigger_armed == 0U;
}

static unsigned int p282_count_bytes(
    const char *value, size_t length, const char *needle) {
    size_t needle_length = strlen(needle);
    unsigned int count = 0;
    if (needle_length == 0U || needle_length > length) return 0;
    for (size_t index = 0; index + needle_length <= length; ++index) {
        if (memcmp(value + index, needle, needle_length) == 0) ++count;
    }
    return count;
}

static const char *p282_find_bytes(
    const char *value, size_t length, const char *needle) {
    size_t needle_length = strlen(needle);
    if (needle_length == 0U || needle_length > length) return NULL;
    for (size_t index = 0; index + needle_length <= length; ++index) {
        if (memcmp(value + index, needle, needle_length) == 0) {
            return value + index;
        }
    }
    return NULL;
}

static long p282_event_path(
    char *path,
    size_t capacity,
    const char *name,
    const char *suffix) {
    (void)name;
    const char *value = strcmp(suffix, "/trigger") == 0
        ? "trigger" : "event";
    size_t length = strlen(value);
    if (length + 1U > capacity) return -EOVERFLOW;
    memcpy(path, value, length + 1U);
    return 0;
}

static long p282_write_control(const char *path, const char *value) {
    if (strcmp(path, "trigger") == 0) {
        if (value != NULL && value[0] == '!') {
            record_operation(OP_TRIGGER_REMOVE);
            if (fail_remove_once) {
                fail_remove_once = 0;
                return -EIO;
            }
            if (fire_during_remove && trigger_remaining_state == 1U) {
                trigger_remaining_state = 0U;
                tracing_on_state = 0U;
                fire_during_remove = 0U;
            }
            trigger_installed_state = 0U;
            return 0;
        }
        record_operation(OP_TRIGGER_ARM);
        if (fail_arm_once) {
            fail_arm_once = 0;
            return -EIO;
        }
        trigger_installed_state = 1U;
        trigger_remaining_state = 1U;
        return 0;
    }
    if (strcmp(
            path, "/sys/kernel/tracing/instances/p282/tracing_on") == 0) {
        if (value != NULL && value[0] == '1') {
            tracing_on_state = 1U;
            record_operation(OP_TRACE_ON);
        } else {
            tracing_on_state = 0U;
            record_operation(OP_TRACE_OFF);
        }
        return 0;
    }
    if (strcmp(
            path,
            "/sys/kernel/tracing/instances/p282/events/p282/enable") == 0) {
        if (value != NULL && value[0] == '1') {
            group_enabled_state = 1U;
            record_operation(OP_GROUP_ON);
        } else {
            group_enabled_state = 0U;
            record_operation(OP_GROUP_OFF);
        }
        return 0;
    }
    return 0;
}

static long p282_read_file(
    const char *path,
    char *value,
    size_t capacity,
    size_t *length) {
    int written = 0;
    if (strcmp(path, "trigger") == 0) {
        record_operation(OP_TRIGGER_COUNT);
        if (malformed_trigger_once) {
            malformed_trigger_once = 0;
            written = snprintf(value, capacity, "malformed\n");
        } else if (trigger_installed_state) {
            written = snprintf(
                value,
                capacity,
                "traceoff:count=%u if type == 2\n",
                trigger_remaining_state);
        } else {
            written = snprintf(value, capacity, "# no triggers\n");
        }
    } else if (strcmp(
            path,
            "/sys/kernel/tracing/instances/p282/tracing_on") == 0) {
        record_operation(OP_TRACING_READ);
        if (malformed_tracing_once) {
            malformed_tracing_once = 0;
            written = snprintf(value, capacity, "x\n");
        } else {
            written = snprintf(value, capacity, "%u\n", tracing_on_state);
        }
    } else {
        if (capacity == 0U) return -EOVERFLOW;
        value[0] = '\0';
        written = 0;
    }
    if (written < 0 || (size_t)written >= capacity) return -EOVERFLOW;
    *length = (size_t)written;
    return 0;
}

static long p282_trace_mount(struct p282_trace_control *control) {
    mount_active = 1U;
    control->mount_owned = 1U;
    return 0;
}
static long p282_path_absent(const char *path) {
    (void)path;
    return 0;
}
static long sys_mkdirat(const char *path, int mode) {
    (void)path;
    (void)mode;
    instance_active = 1U;
    return 0;
}
static long p282_event_registration_state(
    const struct p282_trace_control *control, size_t index) {
    (void)control;
    (void)index;
    return 1;
}
static long p282_verify_event_registration(
    const struct p282_trace_control *control) {
    (void)control;
    return 0;
}
static long p282_verify_control_readback(
    const struct p282_trace_control *control) {
    (void)control;
    return 0;
}
static long p282_clear_trace(void) {
    return 0;
}
static long p282_delete_event(const char *name) {
    (void)name;
    return 0;
}
static long p282_copy_path_part(
    char *output,
    size_t capacity,
    size_t *cursor,
    const char *value) {
    if (value == NULL) value = "event";
    size_t length = strlen(value);
    if (*cursor > capacity || length >= capacity - *cursor) return -EOVERFLOW;
    memcpy(output + *cursor, value, length);
    *cursor += length;
    output[*cursor] = '\0';
    return 0;
}
static long p282_unlinkat(const char *path, int flags) {
    (void)path;
    (void)flags;
    instance_active = 0U;
    return 0;
}
static long p282_umount2(const char *path, int flags) {
    (void)path;
    (void)flags;
    mount_active = 0U;
    return 0;
}
static long sys_statfs(const char *path, struct statfs_probe *probe) {
    (void)path;
    if (!mount_active) return -ENOENT;
    probe->f_type = P282_TRACEFS_MAGIC;
    return 0;
}
'''
        + functions[: functions.find(b"static long p282_trace_cleanup(")]
        + br'''
'''
        + functions[functions.find(b"static long p282_trace_cleanup(") :]
        .replace(
            b"static long p282_trace_setup(",
            b"static long (*const p282_cleanup_partial_trace)(\n"
            b"    struct p282_trace_control *) = p282_trace_cleanup;\n\n"
            b"static long p282_trace_setup(",
            1,
        )
        + br'''

static int setup_success_and_no_cutoff(void) {
    struct p282_trace_control control = {0};
    reset_state();
    if (p282_trace_setup(P282_PHASE_BIND, &control) != 0) return 10;
    long trace_on = operation_index(OP_TRACE_ON, 0U);
    long group_on = operation_index(OP_GROUP_ON, 0U);
    long arm = operation_index(OP_TRIGGER_ARM, 0U);
    if (!(0 <= trace_on && trace_on < group_on && group_on < arm)) return 11;
    reset_log();
    if (p300_close_recording_window(&control) != 0) return 12;
    long count = operation_index(OP_TRIGGER_COUNT, 0U);
    long remove = operation_index(OP_TRIGGER_REMOVE, 0U);
    long state = operation_index(OP_TRACING_READ, 0U);
    long group_off = operation_index(OP_GROUP_OFF, 0U);
    long trace_off = operation_index(OP_TRACE_OFF, 0U);
    if (!(0 <= count && count < remove && remove < state
          && state < group_off && group_off < trace_off)) return 13;
    struct p282_bind_trace_result result = {0};
    if (p300_validate_closed_window(&control, &result) != 0) return 14;
    if (p282_trace_cleanup(&control) != 0 || !no_residue(&control)) return 15;
    return 0;
}

static int cutoff_states(void) {
    struct p282_trace_control control = {0};
    struct p282_bind_trace_result result = {.connect_done_seen = 1U};
    reset_state();
    if (p282_trace_setup(P282_PHASE_BIND, &control) != 0) return 20;
    trigger_remaining_state = 0U;
    tracing_on_state = 0U;
    if (p300_close_recording_window(&control) != 0
        || control.trigger_remaining_before_close != 0U
        || control.tracing_on_before_disable != 0U
        || p300_validate_closed_window(&control, &result) != 0) return 21;
    if (p282_trace_cleanup(&control) != 0 || !no_residue(&control)) return 22;

    reset_state();
    control = (struct p282_trace_control){0};
    if (p282_trace_setup(P282_PHASE_BIND, &control) != 0) return 23;
    fire_during_remove = 1U;
    if (p300_close_recording_window(&control) != 0
        || control.trigger_remaining_before_close != 1U
        || control.tracing_on_before_disable != 0U
        || p300_validate_closed_window(&control, &result) != 0) return 24;
    if (p282_trace_cleanup(&control) != 0 || !no_residue(&control)) return 25;

    reset_state();
    control = (struct p282_trace_control){0};
    if (p282_trace_setup(P282_PHASE_BIND, &control) != 0) return 26;
    trigger_remaining_state = 0U;
    tracing_on_state = 1U;
    if (p300_close_recording_window(&control) == 0
        || control.recording_window_closed != 0U) return 27;
    if (p282_trace_cleanup(&control) != 0 || !no_residue(&control)) return 28;
    return 0;
}

static int cleanup_faults(void) {
    struct p282_trace_control control = {0};
    reset_state();
    malformed_trigger_once = 1U;
    if (p282_trace_setup(P282_PHASE_BIND, &control)
        != P300_DETAIL_TRIGGER_SETUP_OR_READBACK) return 30;
    if (!no_residue(&control)) return 31;

    reset_state();
    control = (struct p282_trace_control){0};
    if (p282_trace_setup(P282_PHASE_BIND, &control) != 0) return 32;
    fail_remove_once = 1U;
    if (p300_close_recording_window(&control) == 0) return 33;
    if (p282_trace_cleanup(&control) != 0 || !no_residue(&control)) return 34;

    reset_state();
    control = (struct p282_trace_control){0};
    if (p282_trace_setup(P282_PHASE_BIND, &control) != 0) return 35;
    malformed_tracing_once = 1U;
    if (p300_close_recording_window(&control) == 0) return 36;
    if (p282_trace_cleanup(&control) != 0 || !no_residue(&control)) return 37;

    reset_state();
    control = (struct p282_trace_control){0};
    fail_arm_once = 1U;
    if (p282_trace_setup(P282_PHASE_BIND, &control)
        != P300_DETAIL_TRIGGER_SETUP_OR_READBACK) return 38;
    if (!no_residue(&control)) return 39;
    return 0;
}

int main(void) {
    int rc = setup_success_and_no_cutoff();
    if (rc == 0) rc = cutoff_states();
    if (rc == 0) rc = cleanup_faults();
    if (rc != 0) return rc;
    printf(
        "setup=1 trigger=1 close-states=3 cleanup-faults=4 no-residue=1\n");
    return 0;
}
'''
    )


def audit_executable_lifecycle(runtime: bytes) -> dict[str, Any]:
    expected = (
        "setup=1 trigger=1 close-states=3 cleanup-faults=4 no-residue=1\n"
    )
    actual = _compile_and_run(_lifecycle_tu(runtime), "trace-lifecycle")
    if actual != expected:
        raise ClosureError(f"P3.00 executable lifecycle differs: {actual!r}")
    return {
        "actual_generated_setup_executed": True,
        "actual_generated_trigger_arm_remove_executed": True,
        "actual_generated_close_window_executed": True,
        "actual_generated_cleanup_executed": True,
        "no_cutoff_order_executed": True,
        "earlier_cutoff_and_close_race_executed": True,
        "impossible_cutoff_state_rejected": True,
        "arm_remove_readback_fault_cleanup_executed": True,
        "zero_tracefs_residue_after_failures": True,
        "verified": True,
    }


def audit_delivery_and_lifecycle(artifacts: dict[str, bytes]) -> dict[str, Any]:
    patch = artifacts["candidate_patch"]
    descriptor = artifacts["trace_descriptor_header"]
    runtime = artifacts["p290_e3_runtime_include"]
    required_descriptor = (
        b"#define P282_BIND_EVENT_COUNT 15U",
        b"r32:p282/irq_out",
        b"dwc3_interrupt evt=%x1:u64 dwc=+40(%x1):u64",
        b"evt_count=+24(%x1):u32 evt_flags=+28(%x1):u32",
        b"type=+0(%x1):b4@8/32",
    )
    required_runtime = (
        b"traceoff:1 if type == 2\\n",
        b"traceoff:count=1 if type == 2\\n",
        b"traceoff:count=0 if type == 2\\n",
        b"!traceoff:1 if type == 2\\n",
        b"phase == P282_PHASE_BIND",
        b"entries_in_buffer != result->entries_written",
        b"\\noverrun:",
        b"\\ncommit overrun:",
        b"\\ndropped events:",
        b"p300_parse_bind_stream(control, result, 1)",
        b"p300_profile_relations(control, result)",
        b"p300_close_recording_window(control)",
        b"p300_validate_closed_window(control, result)",
        b"recording_window_closed",
    )
    if (
        any(token not in descriptor for token in required_descriptor)
        or any(token not in runtime for token in required_runtime)
        or patch.count(b"s22_p300_dwc3_event_config_snapshot") != 2
        or b"dwc3-msm-core.c" in patch
    ):
        raise ClosureError("P3.00 delivery/lifecycle contract differs")
    setup = runtime.find(b"static long p282_trace_setup(")
    setup_trace_on = runtime.find(
        b'"/sys/kernel/tracing/instances/p282/tracing_on", "1\\n"', setup
    )
    setup_group_on = runtime.find(
        b'"/sys/kernel/tracing/instances/p282/events/p282/enable",\n'
        b'            "1\\n"', setup_trace_on
    )
    arm = runtime.find(
        b"long trigger_rc = p300_trigger_arm(control)", setup_group_on
    )
    bind = runtime.find(b"long bind_rc = p260_bind_udc();", arm)
    close_function = runtime.find(b"static long p300_close_recording_window(")
    close_count = runtime.find(
        b"p300_trigger_remaining(control, &remaining)", close_function
    )
    close_remove = runtime.find(
        b"p300_trigger_remove(control)", close_count
    )
    close_state = runtime.find(
        b"p300_read_tracing_on(&tracing_on)", close_remove
    )
    close_group_off = runtime.find(
        b'"/sys/kernel/tracing/instances/p282/events/p282/enable",\n'
        b'            "0\\n"', close_state
    )
    close_trace_off = runtime.find(
        b'"/sys/kernel/tracing/instances/p282/tracing_on", "0\\n"',
        close_group_off,
    )
    finish = runtime.find(b"static long p298_finish_observer(")
    close = runtime.find(b"p300_close_recording_window(control)", finish)
    stream = runtime.find(b"p300_parse_bind_stream(control, result, 1)", close)
    window = runtime.find(
        b"p300_validate_closed_window(control, result)", stream
    )
    stats = runtime.find(b"p300_ring_stats_clean()", window)
    profile = runtime.find(b"p282_profile_clean(control)", stats)
    cleanup = runtime.find(b"p282_trace_cleanup(control)", profile)
    if not (
        0 <= setup < setup_trace_on < setup_group_on < arm < bind
        and 0 <= close_function < close_count < close_remove
        < close_state < close_group_off < close_trace_off < finish
        and finish < close < stream < window < stats < profile < cleanup
    ):
        raise ClosureError("P3.00 lifecycle ordering differs")
    return {
        "bind_event_count": 15,
        "irq_return_maxactive": 32,
        "conditional_post_trigger": True,
        "streaming_parser": True,
        "ring_loss_contract_static_and_compiled": True,
        "final_stream_count_contract_static_and_compiled": True,
        "profile_nmissed_readback_contract_static_and_compiled": True,
        "profile_before_filter_contract": True,
        "recording_window_gap_closed": True,
        "cutoff_race_state_executed": True,
        "external_module_patch_count": 0,
        "verified": True,
    }


def audit_patch_and_userspace(
    root: Path, artifacts: dict[str, bytes]
) -> dict[str, Any]:
    required_tools = (
        "aarch64-linux-gnu-gcc",
        "aarch64-linux-gnu-nm",
        "file",
    )
    tools = {name: shutil.which(name) for name in required_tools}
    if any(value is None for value in tools.values()):
        raise ClosureError("P3.00 AArch64 compile tools are unavailable")
    with tempfile.TemporaryDirectory(prefix="s22-p300-integrated-") as tmp:
        directory = Path(tmp)
        patch_result = p298_contract._audit_patch(  # noqa: SLF001
            root, artifacts["candidate_patch"], directory
        )
        materialized = directory / "materialized"
        materialized.mkdir()
        for key, relative in generator.artifact_paths().items():
            if key == "candidate_patch":
                continue
            (materialized / relative.name).write_bytes(artifacts[key])
        output_a = directory / "init-a"
        output_b = directory / "init-b"
        define = "{" + ",".join(
            f"0x{value:02x}" for value in SOURCE_CHECK_RUN_ID
        ) + "}"
        command = [
            str(tools["aarch64-linux-gnu-gcc"]),
            *userspace.COMPILE_FLAGS,
            "-DS22PLUS_FYG8_P233_PROFILE=3",
            f"-DS22PLUS_FYG8_P233_RUN_ID_BYTES={define}",
            "-I",
            str(materialized),
            "-I",
            str(root / "workspace/public/src/native-init"),
            str(materialized / generator.artifact_paths()["runtime_wrapper"].name),
            str(materialized / generator.artifact_paths()["checkpoint_client"].name),
        ]
        outputs = []
        for output in (output_a, output_b):
            completed = subprocess.run(
                [*command, "-o", str(output)],
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if completed.returncode != 0:
                raise ClosureError(
                    "P3.00 integrated AArch64 compile failed: "
                    + completed.stderr.decode("utf-8", "replace")[-5000:]
                )
            outputs.append(output.read_bytes())
        if outputs[0] != outputs[1]:
            raise ClosureError("P3.00 repeated AArch64 link differs")
        file_result = subprocess.run(
            [str(tools["file"]), "-b", str(output_a)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        undefined = subprocess.run(
            [str(tools["aarch64-linux-gnu-nm"]), "-u", str(output_a)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    file_text = file_result.stdout.decode("ascii", "replace")
    if (
        file_result.returncode != 0
        or "ELF 64-bit LSB executable, ARM aarch64" not in file_text
        or "statically linked" not in file_text
        or undefined.returncode != 0
        or undefined.stdout.strip()
    ):
        raise ClosureError("P3.00 integrated userspace ELF contract differs")
    return {
        "candidate_patch": patch_result,
        "userspace": {
            **_receipt(outputs[0]),
            "static_aarch64": True,
            "two_link_reproducible": True,
            "verified": True,
        },
        "verified": True,
    }


def run_closure(root: Path) -> dict[str, Any]:
    artifacts = _generated(root)
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry_sot": spec.validate(),
        "generator": {
            "artifact_count": len(artifacts),
            "delta_keys": sorted(generator.P298_DELTA_KEYS),
            "candidate_patch": _receipt(artifacts["candidate_patch"]),
            "verified": True,
        },
        "terminal_classifier": inherited.audit_runtime_classifier(
            artifacts["p290_e3_runtime_include"]
        ),
        "start_classifier": inherited.audit_start_classifier(
            artifacts["p290_e3_runtime_include"]
        ),
        "runtime_ingress": audit_runtime_classification(
            artifacts["p290_e3_runtime_include"]
        ),
        "stream_parser": audit_stream_parser(
            artifacts["p290_e3_runtime_include"]
        ),
        "pair_adjacency": inherited.audit_pair_adjacency(
            artifacts["p290_e3_runtime_include"]
        ),
        "delivery_lifecycle": audit_delivery_and_lifecycle(artifacts),
        "executable_lifecycle": audit_executable_lifecycle(
            artifacts["p290_e3_runtime_include"]
        ),
        "integrated_build": audit_patch_and_userspace(root, artifacts),
        "baseline": {
            "control": "P2.96 historical behavioral no-probe baseline",
            "host_sidecar": "device_action_usb_trace_sidecar_v1",
            "same_f1_binding_complete": False,
            "future_attempt_binding_required": True,
        },
        "slot_16": {
            "used": False,
            "reason": "no exact built-in candidate-window connector-role-vbus observer",
            "future_builtin_execution_proof_required": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "payload_write": False,
            "live_authorized": False,
        },
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(run_closure(Path.cwd()), indent=2, sort_keys=True))
