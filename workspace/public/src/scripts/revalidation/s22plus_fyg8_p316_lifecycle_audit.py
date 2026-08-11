#!/usr/bin/env python3
"""Audit the P3.16 late-loader child lifecycle in materialized C."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p316_generator as generator


SCHEMA = "s22plus_fyg8_p316_lifecycle_audit_v1"
VERDICT = "PASS_P316_LATE_LOADER_LIFECYCLE_HOST_ONLY"


class LifecycleError(ValueError):
    pass


def _ordered(value: bytes, tokens: tuple[bytes, ...], label: str) -> None:
    cursor = 0
    for token in tokens:
        found = value.find(token, cursor)
        if found < 0:
            raise LifecycleError(f"{label} token/order differs: {token!r}")
        cursor = found + len(token)


def _final_drain_tu(runtime: bytes) -> bytes:
    record = support._struct(  # noqa: SLF001
        runtime, b"struct p316_diag_helper_record {"
    )
    drain = support._definition(  # noqa: SLF001
        runtime, b"static long p316_drain_helper_pipe("
    )
    return (
        br'''
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define P260_EINTR EINTR

static uint8_t fake_record[12];
static unsigned int fake_read_index;
static long sys_read(int fd, void *value, size_t capacity) {
    (void)fd;
    if (fake_read_index++ == 0U) return -EAGAIN;
    if (capacity < sizeof(fake_record)) return -EOVERFLOW;
    memcpy(value, fake_record, sizeof(fake_record));
    return (long)sizeof(fake_record);
}
'''
        + record
        + drain
        + br'''
int main(void) {
    struct p316_diag_helper_record expected = {
        .magic = 0x4d584448U,
        .version = 1U,
        .reserved = 0U,
        .result = 0,
    };
    struct p316_diag_helper_record observed = {0};
    size_t observed_bytes = 0U;
    memcpy(fake_record, &expected, sizeof(expected));

    if (p316_drain_helper_pipe(7, &observed, &observed_bytes) != 0
        || observed_bytes != 0U) return 1;
    /* Models wait4() reaping between the two drain calls. */
    if (p316_drain_helper_pipe(7, &observed, &observed_bytes) != 0
        || observed_bytes != sizeof(observed)
        || memcmp(&observed, &expected, sizeof(observed)) != 0) return 2;
    printf("first=eagain reaped=1 final=%zu reads=%u\n",
        observed_bytes, fake_read_index);
    return 0;
}
'''
    )


def _abort_reap_tu(runtime: bytes) -> bytes:
    abort = support._definition(  # noqa: SLF001
        runtime, b"static long p316_abort_and_reap_child("
    )
    return (
        br'''
#include <errno.h>
#include <signal.h>
#include <stdio.h>

static int kill_calls;
static int reap_calls;
static long reap_result;
static long sys_kill(long pid, int signal) {
    if (pid != 123 || signal != SIGKILL) return -EINVAL;
    ++kill_calls;
    return 0;
}
static long p316_reap_deadline(long pid, int *status) {
    if (pid != 123) return -EINVAL;
    ++reap_calls;
    *status = 77;
    return reap_result;
}
'''
        + abort
        + br'''
int main(void) {
    int reaped = 0;
    int status = 0;
    if (p316_abort_and_reap_child(123, &reaped, &status) != 0
        || reaped != 1 || status != 77
        || kill_calls != 1 || reap_calls != 1)
        return 1;
    if (p316_abort_and_reap_child(123, &reaped, &status) != 0
        || kill_calls != 1 || reap_calls != 1)
        return 2;
    reaped = 0;
    reap_result = -EIO;
    if (p316_abort_and_reap_child(123, &reaped, &status) != -EIO
        || reaped != 0 || kill_calls != 2 || reap_calls != 2)
        return 3;
    printf("abort-reap-cases=3 kill=%d reap=%d\n", kill_calls, reap_calls);
    return 0;
}
'''
    )


def _observer_error_tu(runtime: bytes) -> bytes:
    site_enum = support._struct(  # noqa: SLF001
        runtime, b"enum s22plus_max77705_observer_site {"
    )
    error_enum = support._struct(  # noqa: SLF001
        runtime, b"enum s22plus_max77705_observer_error_class {"
    )
    classifier = support._definition(  # noqa: SLF001
        runtime, b"static uint8_t p316_observer_error_class("
    )
    return (
        br'''
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#define P260_EBUSY EBUSY
#define P260_EINTR EINTR
#define P260_EOVERFLOW EOVERFLOW
'''
        + site_enum
        + error_enum
        + classifier
        + br'''
int main(void) {
    const long input[] = {
        -ENOENT, -ENODEV, -EBUSY, -ETIMEDOUT, -EAGAIN,
        -EIO, -EINVAL, -EOVERFLOW, -EINTR, -ENOMEM, 0, 1,
    };
    const uint8_t expected[] = {1,1,2,3,3,4,4,4,5,6,7,7};
    for (size_t index = 0U; index < sizeof(input) / sizeof(input[0]); ++index) {
        if (p316_observer_error_class(input[index]) != expected[index])
            return (int)index + 1;
    }
    printf("observer-error-cases=%zu\n", sizeof(input) / sizeof(input[0]));
    return 0;
}
'''
    )


def _late_priority_tu(runtime: bytes) -> bytes:
    priority_enum = support._struct(  # noqa: SLF001
        runtime, b"enum p316_late_evidence_priority {"
    )
    priority = support._definition(  # noqa: SLF001
        runtime, b"static uint8_t p316_late_evidence_priority("
    )
    return (
        br'''
#include <stdint.h>
#include <stdio.h>
'''
        + priority_enum
        + priority
        + br'''
int main(void) {
    if (p316_late_evidence_priority(0, 0, 0) !=
            P316_LATE_EVIDENCE_NONE
        || p316_late_evidence_priority(0, 0, -5) !=
            P316_LATE_EVIDENCE_RESULT_READ_FAILURE
        || p316_late_evidence_priority(1, 0, -5) !=
            P316_LATE_EVIDENCE_LOADER_DEADLINE
        || p316_late_evidence_priority(0, 1, -5) !=
            P316_LATE_EVIDENCE_HELPER_FAILURE
        || p316_late_evidence_priority(1, 1, -5) !=
            P316_LATE_EVIDENCE_HELPER_FAILURE)
        return 1;
    printf("late-evidence-priority-cases=5\n");
    return 0;
}
'''
    )


def _observer_failure_tu(runtime: bytes) -> bytes:
    pieces = b"".join(
        (
            support._macro(  # noqa: SLF001
                runtime, b"S22PLUS_MAX77705_LOADER_NOT_STARTED"
            ),
            support._macro(  # noqa: SLF001
                runtime, b"S22PLUS_MAX77705_LOADER_IN_PROGRESS"
            ),
            support._macro(  # noqa: SLF001
                runtime, b"S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"enum s22plus_max77705_envelope_semantic_kind {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"enum s22plus_max77705_terminal_code {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"enum s22plus_max77705_observer_site {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"enum s22plus_max77705_observer_error_class {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"struct s22plus_max77705_binding_witness {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"struct s22plus_max77705_runtime_result {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"struct s22plus_max77705_runtime_poll_summary {"
            ),
            support._struct(  # noqa: SLF001
                runtime, b"struct p316_diag_observation {"
            ),
        )
    )
    classifier = support._definition(  # noqa: SLF001
        runtime, b"static uint8_t p316_observer_error_class("
    )
    failure = support._definition(  # noqa: SLF001
        runtime, b"static __attribute__((noreturn)) void p316_fail_observer("
    )
    return (
        br'''
#include <errno.h>
#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define P260_EBUSY EBUSY
#define P260_EINTR EINTR
#define P260_EOVERFLOW EOVERFLOW
#define S22PLUS_MAX77705_RUNTIME_COMMANDS 4U
#define S22PLUS_MAX77705_RUNTIME_POLL_LIMIT 100U
'''
        + pieces
        + br'''
static jmp_buf publish_return;
static struct p316_diag_observation published;
static __attribute__((noreturn)) void p316_publish(
    int tty_fd, const struct p316_diag_observation *observation) {
    (void)tty_fd;
    published = *observation;
    longjmp(publish_return, 1);
}
'''
        + classifier
        + failure
        + br'''
static int run_failure(
    unsigned int site, long error,
    const struct p316_diag_observation *prior) {
    memset(&published, 0, sizeof(published));
    if (setjmp(publish_return) == 0)
        p316_fail_observer(-1, site, error, prior);
    return 0;
}

int main(void) {
    if (run_failure(
            S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE,
            -ENOENT, NULL) != 0
        || published.binding.loader_state !=
            S22PLUS_MAX77705_LOADER_NOT_STARTED
        || published.observer_site !=
            S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE
        || published.observer_error_class !=
            S22PLUS_MAX77705_OBSERVER_ERROR_NOT_FOUND
        || published.result_valid != 0U)
        return 1;

    struct p316_diag_observation prior = {0};
    prior.binding.loader_state =
        S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS;
    prior.binding.pre_exact_parent_present = 1U;
    prior.binding.pre_exact_parent_driver_state = 1U;
    prior.binding.pre_matching_unbound_parent_count = 1U;
    prior.result_valid = 1U;
    if (run_failure(
            S22PLUS_MAX77705_OBSERVER_SITE_POST_TOPOLOGY,
            -EIO, &prior) != 0
        || published.binding.loader_state !=
            S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS
        || published.binding.pre_exact_parent_present != 1U
        || published.binding.pre_matching_unbound_parent_count != 1U
        || published.observer_site !=
            S22PLUS_MAX77705_OBSERVER_SITE_POST_TOPOLOGY
        || published.observer_error_class !=
            S22PLUS_MAX77705_OBSERVER_ERROR_IO_FORMAT
        || published.result_valid != 0U)
        return 2;

    prior.binding.loader_state = S22PLUS_MAX77705_LOADER_IN_PROGRESS;
    if (run_failure(
            S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER,
            -ETIMEDOUT, &prior) != 0
        || published.binding.loader_state !=
            S22PLUS_MAX77705_LOADER_IN_PROGRESS
        || published.observer_error_class !=
            S22PLUS_MAX77705_OBSERVER_ERROR_TIMEOUT_RETRY)
        return 3;
    printf("observer-failure-paths=3 preserved=2\n");
    return 0;
}
'''
    )


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    artifacts = generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )
    runtime = artifacts["p290_e3_runtime_include"]
    wrapper = artifacts["runtime_wrapper"]
    observe = support._definition(  # noqa: SLF001
        runtime, b"static long p316_observe_diagnostic("
    )
    abort = support._definition(  # noqa: SLF001
        runtime, b"static long p316_abort_and_reap_child("
    )
    child = support._definition(  # noqa: SLF001
        runtime, b"static __attribute__((noreturn)) void p316_diag_child("
    )
    final_drain = support._definition(  # noqa: SLF001
        runtime, b"static long p316_drain_helper_pipe("
    )
    run = support._definition(  # noqa: SLF001
        runtime, b"static __attribute__((noreturn)) void p316_run("
    )
    if observe.count(b"sys_clone()") != 1:
        raise LifecycleError("late loader clone cardinality differs")
    if observe.count(b"p316_abort_and_reap_child(") != 4:
        raise LifecycleError("late loader bounded cleanup cardinality differs")
    _ordered(
        observe,
        (
            b"sys_openat(module_path, O_RDONLY | O_CLOEXEC, 0)",
            b"if (module_fd < 0)",
            b"S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER",
            b"return module_fd;",
            b"sys_pipe2(pipe_fds, O_CLOEXEC | O_NONBLOCK)",
        ),
        "diagnostic module-open observer failure",
    )
    _ordered(
        observe,
        (
            b"long pid = sys_clone();",
            b"if (pid < 0)",
            b"if (pid == 0)",
            b"sys_close(pipe_fds[1])",
            b"sys_close((int)module_fd)",
            b"S22PLUS_MAX77705_LOADER_IN_PROGRESS",
            b"p282_deadline_after(P316_DIAG_DEADLINE_SEC",
            b"p282_read_file(",
            b"p316_drain_helper_pipe(",
            b"sys_wait4(pid, &child_status, WNOHANG)",
            b"waited < 0 && waited != -P260_EINTR",
            b"p316_abort_and_reap_child(",
            b"return cleanup_rc != 0 ? cleanup_rc : waited;",
            b"if (child_reaped)",
            b"p316_drain_helper_pipe(",
            b"break;",
            b"if (p282_deadline_expired(&deadline))",
            b"p316_abort_and_reap_child(",
            b"if (observation->semantic_kind != 0U) return 0;",
            b"helper_bytes != sizeof(helper)",
            b"if (helper.result > 0) return -EIO;",
            b"uint8_t late_priority = p316_late_evidence_priority(",
            b"P316_LATE_EVIDENCE_HELPER_FAILURE",
            b"S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS",
            b"p316_scan_i2c_topology(&post)",
            b"p316_binding_post(",
            b"if (late_priority == P316_LATE_EVIDENCE_RESULT_READ_FAILURE)",
            b"S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ",
            b"return result_read_error;",
            b"s22plus_max77705_runtime_parse_result(",
            b"p316_classify_result(observation)",
        ),
        "late loader",
    )
    _ordered(
        abort,
        (
            b"if (*child_reaped) return 0;",
            b"sys_kill(pid, SIGKILL)",
            b"p316_reap_deadline(pid, child_status)",
            b"if (rc == 0) *child_reaped = 1;",
        ),
        "abort/reap",
    )
    _ordered(
        child,
        (
            b"p241_finit_module(module_fd, \"\")",
            b"sys_close(module_fd)",
            b"sys_write(pipe_fd, &record, sizeof(record))",
            b"sys_close(pipe_fd)",
            b"sys_exit(",
        ),
        "diagnostic child",
    )
    _ordered(
        final_drain,
        (
            b"*record_bytes > sizeof(*record)",
            b"while (*record_bytes < sizeof(*record))",
            b"sys_read(",
            b"*record_bytes += (size_t)amount",
            b"amount == 0 || amount == -EAGAIN",
            b"amount == -P260_EINTR",
        ),
        "helper pipe drain",
    )
    if (
        observe.find(
            b"if (late_priority == P316_LATE_EVIDENCE_RESULT_READ_FAILURE)"
        )
        < observe.find(b"p316_binding_post(")
        or observe.find(b"if (helper.result > 0) return -EIO;")
        > observe.find(b"S22PLUS_MAX77705_LOADER_RETURNED_SUCCESS")
    ):
        raise LifecycleError("late loader result or helper precedence differs")
    if (
        observe.count(b"S22PLUS_MAX77705_OBSERVER_SITE_RESULT_READ") != 2
        or observe.count(b"return result_read_error;") != 1
        or observe.count(b"return read_rc;") != 1
    ):
        raise LifecycleError("result-read errno/site preservation differs")
    if (
        observe.count(b"S22PLUS_MAX77705_TERMINAL_LATE_LOAD_FAILURE") != 1
        or observe.find(b"P316_LATE_EVIDENCE_HELPER_FAILURE")
        > observe.find(b"S22PLUS_MAX77705_TERMINAL_LATE_LOAD_FAILURE")
    ):
        raise LifecycleError("finit_module failure terminal provenance differs")
    if observe.count(b"p316_drain_helper_pipe(") != 2:
        raise LifecycleError("late loader initial/final drain cardinality differs")
    if run.count(b"p316_fail_observer(") != 3:
        raise LifecycleError("P3.16 observer-failure caller cardinality differs")
    _ordered(
        run,
        (
            b"p316_verify_substrate_bindings();",
            b"S22PLUS_MAX77705_OBSERVER_SITE_SUBSTRATE_VERIFY, rc, NULL",
            b"p316_scan_i2c_topology(&topology);",
            b"S22PLUS_MAX77705_OBSERVER_SITE_PRE_TOPOLOGY, rc, NULL",
            b"p316_observe_diagnostic(tty_fd, &topology, &observation);",
            b"observation.observer_site != S22PLUS_MAX77705_OBSERVER_SITE_NONE",
            b"S22PLUS_MAX77705_OBSERVER_SITE_LATE_LOADER",
            b"rc, &observation",
        ),
        "P3.16 observer-failure immediate callers",
    )
    if wrapper.count(b"p316_fail_observer(") != 1:
        raise LifecycleError("pre-module observer-failure caller differs")
    _ordered(
        wrapper,
        (
            b"long p316_override_rc = p316_prepare_overrides();",
            b"S22PLUS_MAX77705_OBSERVER_SITE_OVERRIDE_PREPARE",
            b"p316_override_rc, NULL",
        ),
        "pre-module observer-failure caller",
    )
    final_drain_output = support._compile(  # noqa: SLF001
        _final_drain_tu(runtime), "p316-final-helper-drain"
    )
    if final_drain_output != "first=eagain reaped=1 final=12 reads=2\n":
        raise LifecycleError(
            f"late loader final drain fixture differs: {final_drain_output!r}"
        )
    abort_reap_output = support._compile(  # noqa: SLF001
        _abort_reap_tu(runtime), "p316-abort-reap-child"
    )
    if abort_reap_output != "abort-reap-cases=3 kill=2 reap=2\n":
        raise LifecycleError(
            f"late loader abort/reap fixture differs: {abort_reap_output!r}"
        )
    observer_error_output = support._compile(  # noqa: SLF001
        _observer_error_tu(runtime), "p316-observer-error-class"
    )
    if observer_error_output != "observer-error-cases=12\n":
        raise LifecycleError(
            f"observer error-class fixture differs: {observer_error_output!r}"
        )
    late_priority_output = support._compile(  # noqa: SLF001
        _late_priority_tu(runtime), "p316-late-evidence-priority"
    )
    if late_priority_output != "late-evidence-priority-cases=5\n":
        raise LifecycleError(
            "late evidence-priority fixture differs: "
            f"{late_priority_output!r}"
        )
    observer_failure_output = support._compile(  # noqa: SLF001
        _observer_failure_tu(runtime), "p316-observer-failure-path"
    )
    if observer_failure_output != "observer-failure-paths=3 preserved=2\n":
        raise LifecycleError(
            "observer failure-path fixture differs: "
            f"{observer_failure_output!r}"
        )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "materialized_runtime_sha256": hashlib.sha256(runtime).hexdigest(),
        "single_clone": True,
        "all_post_clone_local_error_exits_boundedly_reap": True,
        "abort_reap_actual_c_executed": True,
        "abort_reap_cases": 3,
        "wait4_error_boundedly_aborts_and_reaps": True,
        "deadline_kills_and_reaps": True,
        "positive_helper_result_rejected": True,
        "module_open_error_is_observer_tagged": True,
        "late_load_failure_requires_child_finit_module_error": True,
        "post_binding_captured_before_deferred_result_read_failure": True,
        "result_read_errors_preserve_errno_and_site": True,
        "result_parsed_only_after_sync_loader_completion": True,
        "post_reap_final_pipe_drain": True,
        "eagain_then_child_exit_interleaving_executed": True,
        "observer_error_class_actual_c_executed": True,
        "observer_error_class_cases": 12,
        "late_evidence_priority_actual_c_executed": True,
        "late_evidence_priority_cases": 5,
        "observer_failure_actual_c_executed": True,
        "observer_failure_paths": 3,
        "late_and_post_binding_preserved": True,
        "observer_failure_immediate_callers_verified": True,
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (LifecycleError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
