#!/usr/bin/env python3
"""Exact P2.86-to-P2.88 runtime transformations."""

from __future__ import annotations


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


def replace_span(
    data: bytes,
    start: bytes,
    stop: bytes,
    replacement: bytes,
    *,
    label: str,
) -> bytes:
    if data.count(start) != 1:
        raise RuntimeTransformError(f"{label} start marker is not unique")
    begin = data.index(start)
    end = data.find(stop, begin)
    if end < 0:
        raise RuntimeTransformError(f"{label} stop marker is absent")
    return data[:begin] + replacement + data[end:]


def transform_legacy_runtime(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"__attribute__((noreturn)) static void quiet_park(void) {",
        b"__attribute__((noreturn)) static void p288_raw_quiet_park(void) {",
        label="P2.88 raw park definition",
    )
    return replace_span(
        value,
        b"__attribute__((noreturn)) static void fail_at(\n",
        b"#define E1_REQUIRE(stage, item_index, operation)",
        b"",
        label="P2.88 legacy failure publisher removal",
    )


P288_POSITION_HELPERS = b"""static void p288_progress_position(
    uint8_t position_ordinal, uint16_t detail) {
    long next_stage = s22_p288_checkpoint_next_stage(&g_checkpoint);
    if (next_stage < 0) {
        quiet_park();
    }
    p260_revalidate_or_fail((uint8_t)next_stage);
    long rc = s22_p288_checkpoint_progress_position(
        &g_checkpoint, position_ordinal, detail);
    if (rc != 0) {
        quiet_park();
    }
}

static __attribute__((noreturn)) void p288_fail_next(long detail) {
    (void)s22_p288_checkpoint_failure_next(&g_checkpoint, detail);
    quiet_park();
}

"""


P288_CYCLE_CLEANUP = b"""static long p286_cycle_cleanup_after_marker(
    struct p282_cycle_context *cycle) {
    if (!cycle->armed) {
        return 0;
    }
    cycle->armed = 0;
    long cleanup_rc = p282_trace_cleanup(&cycle->trace);
    return cleanup_rc == 0
        ? 0
        : P282_CONTROL_TRACE_CLEANUP_UNVERIFIED;
}

"""


P288_RESTART = b"""static unsigned int p282_cycle_restart(
    struct p282_cycle_context *cycle,
    int unrelated_fd) {
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(
        P282_CYCLE_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_HELPER_DISPATCH, 0U);

    struct p286_helper_observation helper = {0};
    rc = p286_run_cycle_role_helper(
        P282_HELPER_OPERATION_PERIPHERAL_WRITE,
        unrelated_fd,
        &deadline,
        &helper);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    struct p282_classification helper_classification = {0};
    int helper_classified = p288_classify_helper(
        P282_STAGE_RESTART, &helper, &helper_classification);
    if (helper_classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_RESTART,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    if (helper_classified > 0) {
        p282_cycle_abort(
            cycle,
            P282_STAGE_RESTART,
            (long)helper_classification.detail);
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_HELPER_RETURNED, 0U);

    int status_active = 0;
    rc = p282_wait_exact_value(
        P282_CHILD_RUNTIME_STATUS_PATH,
        P282_CHILD_ACTIVE_READBACK,
        &deadline,
        &status_active);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    if (!status_active) {
        p288_fail_next(P282_DETAIL_CHILD_STATUS_NOT_ACTIVE);
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_CHILD_ACTIVE, 0U);

    int mode_peripheral = 0;
    rc = p282_wait_exact_value(
        P282_PARENT_MODE_PATH,
        P282_ROLE_PERIPHERAL_READBACK,
        &deadline,
        &mode_peripheral);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    if (!mode_peripheral) {
        struct p282_classification readback_classification = {0};
        int readback_classified = p286_classify_peripheral_readback(
            helper.write_completed,
            (unsigned int)mode_peripheral,
            &readback_classification);
        if (readback_classified <= 0) {
            quiet_park();
        }
        p282_cycle_abort(
            cycle,
            P282_STAGE_RESTART,
            (long)readback_classification.detail);
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_PARENT_PERIPHERAL, 0U);

    int exact_udc = 0;
    rc = p282_wait_exact_udc(&deadline, &exact_udc);
    if (rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, rc);
    }
    if (!exact_udc) {
        p288_fail_next(
            P282_DETAIL_EXACT_UDC_REGRESSION_AFTER_RESTART);
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_EXACT_UDC, 0U);

    if (cycle->trace_authoritative) {
        do {
            (void)p282_cycle_refresh(cycle, P282_STAGE_RESTART);
            if (
                !cycle->trace_authoritative
                || cycle->observed.restart_worker.returned
            ) {
                break;
            }
            p282_poll_delay();
        } while (!p282_deadline_expired(&deadline));
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_REFRESH_RETURNED,
        p282_cycle_warning_detail(cycle, P282_STAGE_RESTART));

    struct p282_cycle_trace_result final_result = cycle->observed;
    long capture_rc = p286_cycle_capture(cycle, &final_result);
    if (capture_rc == P282_CONTROL_TRACE_SOURCE_CONTRADICTION) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_RESTART,
            (unsigned int)capture_rc);
    }
    if (capture_rc != 0) {
        p282_cycle_abort(cycle, P282_STAGE_RESTART, capture_rc);
    }
    cycle->observed = final_result;
    p288_progress_position(
        S22_P288_POSITION_RESTART_CAPTURE_RETURNED, 0U);

    struct p282_restart_observation observation = {
        .peripheral_readback = (unsigned int)mode_peripheral,
        .trace_authoritative = cycle->trace_authoritative,
        .worker_entered = final_result.restart_worker.entered,
        .worker_returned = final_result.restart_worker.returned,
        .worker_rc = final_result.restart_worker.rc,
        .resume_entered = final_result.child_resume.entered,
        .resume_returned = final_result.child_resume.returned,
        .resume_rc = final_result.child_resume.rc,
        .init_entered = final_result.phy_init.entered,
        .init_returned = final_result.phy_init.returned,
        .init_rc = final_result.phy_init.rc,
        .power_on_entered = final_result.power_on.entered,
        .power_on_returned = final_result.power_on.returned,
        .power_on_rc = final_result.power_on.rc,
        .notify_connect = final_result.notify_connect.entered,
        .status_active = (unsigned int)status_active,
        .mode_peripheral = (unsigned int)mode_peripheral,
        .exact_udc = (unsigned int)exact_udc,
        .off_on_zero_pair = (
            cycle->stop_power_off_zero
            && final_result.power_on.returned
            && final_result.power_on.rc == 0
        ),
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_restart(
        &observation, &classification);
    unsigned int repair_class = P282_REPAIR_DIAGNOSTIC_DEGRADED;
    if (cycle->trace_authoritative) {
        repair_class = observation.off_on_zero_pair
            ? P282_REPAIR_POWER_HELPER_OFF_ON_ZERO
            : P282_REPAIR_SOFTWARE_REINIT;
    }
    if (classified < 0) {
        p282_cycle_abort_condition(
            cycle,
            P282_STAGE_RESTART,
            P282_CONTROL_TRACE_SOURCE_CONTRADICTION);
    }
    if (
        classified > 0
        && classification.outcome == P282_OUTCOME_FAILURE
    ) {
        p282_cycle_abort(
            cycle,
            P282_STAGE_RESTART,
            (long)classification.detail);
    }
    p288_progress_position(
        S22_P288_POSITION_RESTART_CLASSIFIED,
        classified > 0 ? (uint16_t)classification.detail : 0U);

    long cleanup_rc = p286_cycle_cleanup_after_marker(cycle);
    if (cleanup_rc != 0) {
        p288_fail_next(P282_DETAIL_TRACE_CLEANUP_UNVERIFIED);
    }
    p288_progress_position(
        S22_P288_POSITION_BIND_CYCLE_CLEANUP_RETURNED, 0U);
    return repair_class;
}

"""


P288_BIND = b"""static unsigned int p282_phase_bind(unsigned int repair_class) {
    struct p282_trace_control control;
    long setup_rc = p282_trace_setup(P282_PHASE_BIND, &control);
    int armed = setup_rc == 0;
    if (setup_rc == P282_CONTROL_TRACE_CLEANUP_UNVERIFIED) {
        p288_fail_next(P282_DETAIL_BIND_TRACE_CLEANUP_UNVERIFIED);
    }
    p288_progress_position(
        S22_P288_POSITION_BIND_TRACE_SETUP_RETURNED, 0U);

    long bind_rc = p260_bind_udc();
    if (bind_rc != 0) {
        p288_fail_next(bind_rc);
    }
    p288_progress_position(
        S22_P288_POSITION_BIND_UDC_RETURNED, 0U);

    long quality = 0;
    long finish_rc = armed
        ? p282_trace_finish(&control, &quality)
        : 0;
    if (finish_rc != 0) {
        p288_fail_next(P282_DETAIL_BIND_TRACE_CLEANUP_UNVERIFIED);
    }

    struct p282_bind_trace_result trace_result = {
        .source_consistent = 1,
        .branch = P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    int trace_authoritative = armed && quality == 0;
    if (trace_authoritative) {
        long parse_rc = p282_parse_bind_result(
            &control, &trace_result);
        if (parse_rc != 0) {
            trace_result.source_consistent = 0;
        }
    }
    struct p282_bind_observation observation = {
        .cleanup_verified = 1,
        .source_consistent = trace_result.source_consistent,
        .trace_authoritative = (unsigned int)trace_authoritative,
        .pullup_returned_zero = trace_authoritative
            ? trace_result.pullup_returned_zero
            : 1U,
        .run_stop_seen = trace_result.run_stop_seen,
        .run_stop_rc = trace_result.run_stop_rc,
        .repair_class = repair_class,
        .bind_branch = trace_authoritative
            ? trace_result.branch
            : P282_BIND_DIAGNOSTIC_DEGRADED,
    };
    struct p282_classification classification = {0};
    int classified = p282_classify_bind(
        &observation, &classification);
    if (classified < 0) {
        observation.source_consistent = 0;
        classified = p282_classify_bind(
            &observation, &classification);
    }
    if (classified < 0) {
        quiet_park();
    }
    if (
        classified > 0
        && classification.outcome == P282_OUTCOME_FAILURE
    ) {
        p288_fail_next((long)classification.detail);
    }
    p288_progress_position(
        S22_P288_POSITION_BIND_TRACE_CLASSIFIED,
        classified > 0 ? (uint16_t)classification.detail : 0U);
    return observation.bind_branch;
}

"""


P288_FINAL = b"""static void p282_wait_final_pair(
    unsigned int repair_class,
    unsigned int bind_branch) {
    _Static_assert(
        sizeof(p282_descriptor_udc_states)
                / sizeof(p282_descriptor_udc_states[0])
            == P282_STATE_COUNT,
        "P2.82 generated UDC state table cardinality");
    _Static_assert(
        sizeof(p282_descriptor_usb_speeds)
                / sizeof(p282_descriptor_usb_speeds[0])
            == P282_SPEED_COUNT,
        "P2.82 generated USB speed table cardinality");

    p288_progress_position(
        S22_P288_POSITION_FINAL_SAMPLING_STARTED, 0U);
    struct timespec64 deadline = {0};
    long rc = p282_deadline_after(
        P282_FINAL_DEADLINE_SEC, &deadline);
    if (rc != 0) {
        p288_fail_next(rc);
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
            p288_fail_next(rc);
        }
        int stable = have_previous
            && previous_state == current_state
            && previous_speed == current_speed;
        int configured_high = (
            current_state == P282_STATE_CONFIGURED
            && current_speed == P282_SPEED_HIGH
        );
        if (
            (stable && configured_high)
            || p282_deadline_expired(&deadline)
        ) {
            if (!have_previous) {
                p288_fail_next(P282_DETAIL_FINAL_STATE_SPEED_UNSTABLE);
            }
            struct p282_final_pair_observation observation = {
                .first_state = previous_state,
                .first_speed = previous_speed,
                .second_state = current_state,
                .second_speed = current_speed,
                .repair_class = repair_class,
                .bind_branch = bind_branch,
            };
            struct p282_classification classification = {0};
            int classified = p282_classify_final_pair(
                &observation, &classification);
            if (classified < 0) {
                p288_fail_next(-P260_EPROTO);
            }
            if (
                classified > 0
                && classification.outcome == P282_OUTCOME_FAILURE
            ) {
                p288_fail_next((long)classification.detail);
            }
            p288_progress_position(
                S22_P288_POSITION_FINAL_RESULT_CLASSIFIED,
                classified > 0
                    ? (uint16_t)classification.detail
                    : 0U);
            return;
        }
        previous_state = current_state;
        previous_speed = current_speed;
        have_previous = 1;
        p282_poll_delay();
    }
}

"""


def transform_runtime_include(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"/* P2.86 parent-quiescence and bounded restart over the P2.84 E3 path. */",
        b"/* P2.88 pair-indexed attributable restart over the P2.86 path. */",
        label="P2.88 runtime banner",
    )
    value = replace_exact(
        value,
        b'#include "s22plus_fyg8_p286_classifier.inc.c"',
        b'#include "s22plus_fyg8_p288_positions.h"\n'
        b'#include "s22plus_fyg8_p288_classifier.inc.c"',
        label="P2.88 classifier and position includes",
    )
    progress_end = (
        b"static long p282_role_trace_detail(long condition) {"
    )
    progress_start = b"static long p282_role_trace_detail(long condition) {"
    value = replace_exact(
        value,
        progress_start,
        P288_POSITION_HELPERS + progress_end,
        label="P2.88 position publication helpers",
    )
    value = replace_span(
        value,
        b"static long p286_cycle_cleanup_after_marker(",
        b"static long p282_exact_udc_present(",
        P288_CYCLE_CLEANUP,
        label="P2.88 cycle cleanup",
    )
    value = replace_span(
        value,
        b"static void p282_restart_exact_failure(",
        b"static unsigned int p282_cycle_restart(",
        b"",
        label="P2.88 retired restart exact-failure adapter",
    )
    value = replace_span(
        value,
        b"static unsigned int p282_cycle_restart(",
        b"static unsigned int p282_phase_bind(",
        P288_RESTART,
        label="P2.88 restart corridor",
    )
    value = replace_span(
        value,
        b"static unsigned int p282_phase_bind(",
        b"static long p282_parse_canonical(",
        P288_BIND,
        label="P2.88 bind corridor",
    )
    value = replace_span(
        value,
        b"static void p282_wait_final_pair(",
        b"static __attribute__((noreturn)) void p286_e3_run(",
        P288_FINAL,
        label="P2.88 final corridor",
    )
    value = replace_exact(
        value,
        b"static __attribute__((noreturn)) void p286_e3_run(",
        b"static __attribute__((noreturn)) void p288_e3_run(",
        label="P2.88 runtime entry",
    )
    value = replace_exact(
        value,
        b"long publish_rc = s22_r4w1e_checkpoint_failure(\n"
        b"        &g_checkpoint, stage, 0U, detail);",
        b"(void)stage;\n"
        b"    long publish_rc = s22_p288_checkpoint_failure_next(\n"
        b"        &g_checkpoint, detail);",
        label="P2.88 abort next-position failure",
    )
    return value


P288_WRAPPER_PARK = b"""__attribute__((noreturn)) static void quiet_park(void) {
    (void)s22_p288_checkpoint_unclassified_next(&g_checkpoint);
    p288_raw_quiet_park();
}

__attribute__((noreturn)) static void fail_at(
    uint8_t stage, uint8_t item_index, long operation_error) {
    long rc = g_checkpoint.initialized &&
            g_checkpoint.generation >= 88U
        ? s22_p288_checkpoint_failure_next(
            &g_checkpoint, operation_error)
        : s22_r4w1e_checkpoint_failure(
            &g_checkpoint, stage, item_index, operation_error);
    if (rc != 0) {
        (void)s22_p288_checkpoint_unclassified_next(&g_checkpoint);
    }
    p288_raw_quiet_park();
}

"""


def transform_runtime_wrapper(data: bytes) -> bytes:
    value = replace_exact(
        data,
        b"#define e1_run s22_p241_included_e1b_run\n"
        b"#define _start s22_p241_included_start\n"
        b'#include "s22plus_r4w1e_e1_runtime.c"\n'
        b"#undef _start\n"
        b"#undef e1_run\n",
        b"#include <stdint.h>\n"
        b"__attribute__((noreturn)) static void quiet_park(void);\n"
        b"__attribute__((noreturn)) static void fail_at(\n"
        b"    uint8_t stage, uint8_t item_index, long operation_error);\n"
        b"#define e1_run s22_p241_included_e1b_run\n"
        b"#define _start s22_p241_included_start\n"
        b'#include "s22plus_r4w1e_e1_runtime.c"\n'
        b"#undef _start\n"
        b"#undef e1_run\n"
        + P288_WRAPPER_PARK,
        label="P2.88 raw park isolation",
    )
    value = replace_exact(
        value,
        b'#include "s22plus_fyg8_p286_e3_runtime.inc.c"',
        b'#include "s22plus_fyg8_p288_e3_runtime.inc.c"',
        label="P2.88 runtime include",
    )
    return replace_exact(
        value,
        b"    p286_e3_run();\n",
        b"    p288_e3_run();\n",
        label="P2.88 runtime handoff",
    )
