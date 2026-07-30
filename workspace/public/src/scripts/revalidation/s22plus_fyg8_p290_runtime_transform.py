#!/usr/bin/env python3
"""Exact P2.88-to-P2.90 park and adjacent-corridor transformations."""

from __future__ import annotations

import s22plus_fyg8_p288_runtime_transform as p288


class RuntimeTransformError(ValueError):
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
        raise RuntimeTransformError(
            f"{label} replacement count {actual}, expected {count}"
        )
    return data.replace(old, new)


P290_POSITION_HELPERS = b"""static void p290_progress_position(
    uint8_t position_ordinal, uint16_t detail) {
    long rc = s22_p290_checkpoint_progress_position(
        &g_checkpoint, position_ordinal, detail);
    if (rc != 0) {
        quiet_park();
    }
}

static __attribute__((noreturn)) void p290_fail_next(long detail) {
    long primary_rc = s22_p290_checkpoint_failure_next(
        &g_checkpoint, detail);
    if (primary_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    quiet_park();
}

"""


P290_WRAPPER_PARK = b"""static __attribute__((noreturn))
void p290_park_after_confirmed_publication(void) {
    p288_raw_quiet_park();
}

static __attribute__((noreturn))
void p290_checkpoint_channel_failure_sink(long last_rc) {
    (void)last_rc;
    p288_raw_quiet_park();
}

__attribute__((noreturn)) static void quiet_park(void) {
    long fallback_rc =
        s22_p290_checkpoint_unclassified_next(&g_checkpoint);
    if (fallback_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    p290_checkpoint_channel_failure_sink(fallback_rc);
}

__attribute__((noreturn)) static void fail_at(
    uint8_t stage, uint8_t item_index, long operation_error) {
    long primary_rc = g_checkpoint.initialized &&
            g_checkpoint.generation >= 88U
        ? s22_p290_checkpoint_failure_next(
            &g_checkpoint, operation_error)
        : s22_r4w1e_checkpoint_failure(
            &g_checkpoint, stage, item_index, operation_error);
    if (primary_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    long fallback_rc =
        s22_p290_checkpoint_unclassified_next(&g_checkpoint);
    if (fallback_rc == 0) {
        p290_park_after_confirmed_publication();
    }
    p290_checkpoint_channel_failure_sink(fallback_rc);
}

"""


def transform_runtime_include(data: bytes) -> bytes:
    value = replace_exact(
        data,
        p288.P288_POSITION_HELPERS,
        P290_POSITION_HELPERS,
        label="P2.90 direct position publisher",
    )
    value = replace_exact(
        value,
        b"    p282_publish_classification(\n"
        b"        P282_STAGE_SUSPENDED,\n"
        b"        classified,\n"
        b"        &classification,\n"
        b"        p282_cycle_warning_detail(cycle, P282_STAGE_SUSPENDED));\n"
        b"    return 0;\n"
        b"}\n\n"
        b"static unsigned int p282_cycle_restart(",
        b"    p282_publish_classification(\n"
        b"        P282_STAGE_SUSPENDED,\n"
        b"        classified,\n"
        b"        &classification,\n"
        b"        p282_cycle_warning_detail(cycle, P282_STAGE_SUSPENDED));\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_SUSPENDED_PUBLISH_RETURNED, 0U);\n"
        b"    return 0;\n"
        b"}\n\n"
        b"static unsigned int p282_cycle_restart(",
        label="P2.90 generation-88 publisher-return adjacency",
    )
    value = replace_exact(
        value,
        b"static unsigned int p282_cycle_restart(\n"
        b"    struct p282_cycle_context *cycle,\n"
        b"    int unrelated_fd) {\n"
        b"    struct timespec64 deadline = {0};\n"
        b"    long rc = p282_deadline_after(\n"
        b"        P282_CYCLE_DEADLINE_SEC, &deadline);\n",
        b"static unsigned int p282_cycle_restart(\n"
        b"    struct p282_cycle_context *cycle,\n"
        b"    int unrelated_fd) {\n"
        b"    struct timespec64 deadline = {0};\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_RESTART_FUNCTION_ENTERED, 0U);\n"
        b"    long rc = p282_deadline_after(\n"
        b"        P282_CYCLE_DEADLINE_SEC, &deadline);\n",
        label="P2.90 restart-entry position",
    )
    value = replace_exact(
        value,
        b"    if (rc != 0) {\n"
        b"        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);\n"
        b"    }\n"
        b"    p288_progress_position(\n"
        b"        S22_P288_POSITION_RESTART_HELPER_DISPATCH, 0U);\n",
        b"    if (rc != 0) {\n"
        b"        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);\n"
        b"    }\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_RESTART_DEADLINE_READY, 0U);\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_RESTART_HELPER_DISPATCH, 0U);\n",
        label="P2.90 restart-deadline position",
    )
    value = replace_exact(
        value,
        b"    (void)p282_cycle_suspend(&cycle, &stop_deadline);\n"
        b"    unsigned int repair_class = "
        b"p282_cycle_restart(&cycle, tty_fd);\n",
        b"    (void)p282_cycle_suspend(&cycle, &stop_deadline);\n"
        b"    p290_progress_position(\n"
        b"        S22_P290_POSITION_SUSPEND_FUNCTION_RETURNED, 0U);\n"
        b"    unsigned int repair_class = "
        b"p282_cycle_restart(&cycle, tty_fd);\n",
        label="P2.90 caller-side suspend-return position",
    )
    value = replace_exact(
        value,
        b"    if (cycle->armed) {\n"
        b"        long quality = 0;\n"
        b"        cycle->armed = 0;\n"
        b"        (void)p282_trace_finish(&cycle->trace, &quality);\n"
        b"    }\n"
        b"    quiet_park();\n"
        b"}\n\n"
        b"static __attribute__((noreturn)) "
        b"void p282_cycle_abort_condition(",
        b"    if (cycle->armed) {\n"
        b"        long quality = 0;\n"
        b"        cycle->armed = 0;\n"
        b"        (void)p282_trace_finish(&cycle->trace, &quality);\n"
        b"    }\n"
        b"    p290_park_after_confirmed_publication();\n"
        b"}\n\n"
        b"static __attribute__((noreturn)) "
        b"void p282_cycle_abort_condition(",
        label="P2.90 abort confirmed-publication park",
    )
    value = replace_exact(
        value,
        b"    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"    quiet_park();\n"
        b"}\n",
        b"    if (s22_r4w1e_checkpoint_success(&g_checkpoint) != 0) {\n"
        b"        quiet_park();\n"
        b"    }\n"
        b"    p290_park_after_confirmed_publication();\n"
        b"}\n",
        label="P2.90 terminal confirmed-publication park",
    )
    value = value.replace(
        b"p288_progress_position(", b"p290_progress_position("
    )
    value = value.replace(b"p288_fail_next(", b"p290_fail_next(")
    value = value.replace(
        b"S22_P288_POSITION_", b"S22_P290_POSITION_"
    )
    value = value.replace(
        b"s22plus_fyg8_p288_positions.h",
        b"s22plus_fyg8_p290_positions.h",
    )
    value = value.replace(
        b"s22_p288_checkpoint_", b"s22_p290_checkpoint_"
    )
    value = value.replace(b"p288_e3_run", b"p290_e3_run")
    return value


def transform_runtime_wrapper(data: bytes) -> bytes:
    value = replace_exact(
        data,
        p288.P288_WRAPPER_PARK,
        P290_WRAPPER_PARK,
        label="P2.90 checked publication park wrappers",
    )
    value = replace_exact(
        value,
        b'#include "s22plus_fyg8_p288_e3_runtime.inc.c"',
        b'#include "s22plus_fyg8_p290_e3_runtime.inc.c"',
        label="P2.90 runtime include",
    )
    return value.replace(b"p288_e3_run", b"p290_e3_run")


def transform_checkpoint(data: bytes) -> bytes:
    return (
        data.replace(
            b"S22_P288_POSITION_COUNT", b"S22_P290_POSITION_COUNT"
        )
        .replace(
            b"S22_P288_POSITION_", b"S22_P290_POSITION_"
        )
        .replace(
            b"s22_p288_checkpoint_", b"s22_p290_checkpoint_"
        )
        .replace(b"s22_fyg8_p288_", b"s22_fyg8_p290_")
        .replace(b"P2.88", b"P2.90")
    )


def transform_patch(data: bytes) -> bytes:
    return data.replace(b"s22_fyg8_p288_", b"s22_fyg8_p290_")


def transform_position_header(data: bytes) -> bytes:
    return (
        data.replace(b"P288_POSITIONS", b"P290_POSITIONS")
        .replace(
            b"S22_P288_POSITION_", b"S22_P290_POSITION_"
        )
        .replace(
            b"S22_P288_POSITION_COUNT", b"S22_P290_POSITION_COUNT"
        )
    )


def transform_checkpoint_header(data: bytes) -> bytes:
    return (
        data.replace(
            b"s22plus_fyg8_p288_positions.h",
            b"s22plus_fyg8_p290_positions.h",
        )
        .replace(
            b"s22_p288_checkpoint_", b"s22_p290_checkpoint_"
        )
    )
