#!/usr/bin/env python3
"""Host-only closure for the P2.98 gadget-start/event observer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

import s22plus_fyg8_p292_accept_to_resume as inherited
import s22plus_fyg8_p296_identity_tiers as baseline_identity
import s22plus_fyg8_p296_source_contract as p296
import s22plus_fyg8_p298_telemetry_generator as generator
import s22plus_fyg8_p298_telemetry_spec as spec
import s22plus_fyg8_p298_telemetry_transform as transform


SCHEMA = "s22plus_fyg8_p298_telemetry_closure_v1"
VERDICT = "PASS_P298_GADGET_START_EVENT_TELEMETRY_CLOSURE_HOST_ONLY"


class ClosureError(ValueError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _generated(root: Path) -> dict[str, bytes]:
    return generator.generate_bytes(
        root,
        run_id=baseline_identity.SOURCE_CHECK_RUN_ID,
        unsat_tag=baseline_identity.SOURCE_CHECK_UNSAT_TAG,
        profile=spec.PROFILE,
    )


def _fnv_update(value: int, word: int) -> int:
    return ((value ^ word) * 1099511628211) & ((1 << 64) - 1)


def _expected_classifier_result() -> dict[str, Any]:
    value = 1469598103934665603
    details = set()
    count = 0
    for run_stop in range(2):
        for devctrlhlt in range(2):
            for coreidle in range(2):
                for prtcap in range(4):
                    for susphy in range(2):
                        for connect_speed in range(8):
                            for state in range(len(spec.UDC_STATES)):
                                for speed in range(len(spec.USB_SPEEDS)):
                                    result = spec.classify(
                                        spec.Snapshot(
                                            0,
                                            run_stop,
                                            devctrlhlt,
                                            coreidle,
                                            prtcap,
                                            susphy,
                                            connect_speed,
                                            state,
                                            speed,
                                        )
                                    )
                                    value = _fnv_update(
                                        value,
                                        result.detail | (result.outcome << 16),
                                    )
                                    details.add(result.detail)
                                    count += 1
    return {
        "case_count": count,
        "detail_count": len(details),
        "fnv64": f"{value:016x}",
    }


def _classifier_tu(runtime: bytes) -> bytes:
    struct_start = runtime.find(b"struct p294_capture_values {\n")
    marker = b"static struct p294_capture_values g_p294_capture;\n"
    struct_end = runtime.find(marker, struct_start)
    if struct_start < 0 or struct_end < 0:
        raise ClosureError("P2.98 capture state source is absent")
    struct_end += len(marker)
    start, end = transform.base._function_span(  # noqa: SLF001
        runtime, b"p294_terminal_detail"
    )
    classifier = runtime[start:end]
    return (
        b"#include <stdint.h>\n#include <stdio.h>\n"
        b"#define P260_EPROTO 71\n"
        b"#define P282_STATE_COUNT 9U\n"
        b"#define P282_SPEED_HIGH 3U\n"
        b"#define P294_FINAL_DETAIL_BASE 0xe00U\n"
        b"#define P294_MISMATCH_DETAIL_BASE 0xf80U\n"
        b"#define P294_STATE_SPEED_CONTRADICTION 0xf8fU\n"
        b"#define P294_CONNECT_SPEED_CONTRADICTION 0xf90U\n"
        + runtime[struct_start:struct_end]
        + classifier
        + b"""
static uint64_t update(uint64_t value, uint32_t word) {
    return (value ^ word) * UINT64_C(1099511628211);
}

int main(void) {
    uint64_t hash = UINT64_C(1469598103934665603);
    uint8_t seen[65536] = {0};
    unsigned int cases = 0;
    unsigned int details = 0;
    g_p294_capture.dwc3_seen = 1U;
    g_p294_capture.probe_armed = 1U;
    g_p294_capture.start_rc_zero = 1U;
    g_p294_capture.ep_enable_hits = 2U;
    g_p294_capture.start_dwc = 1U;
    for (unsigned int run_stop = 0; run_stop < 2; ++run_stop)
    for (unsigned int devctrlhlt = 0; devctrlhlt < 2; ++devctrlhlt)
    for (unsigned int coreidle = 0; coreidle < 2; ++coreidle)
    for (unsigned int prtcap = 0; prtcap < 4; ++prtcap)
    for (unsigned int susphy = 0; susphy < 2; ++susphy)
    for (unsigned int connect_speed = 0; connect_speed < 8; ++connect_speed)
    for (unsigned int state = 0; state < 9; ++state)
    for (unsigned int speed = 0; speed < 7; ++speed) {
        g_p294_capture.run_stop = (uint8_t)run_stop;
        g_p294_capture.devctrlhlt = (uint8_t)devctrlhlt;
        g_p294_capture.coreidle = (uint8_t)coreidle;
        g_p294_capture.prtcap = (uint8_t)prtcap;
        g_p294_capture.susphy = (uint8_t)susphy;
        g_p294_capture.connect_speed = (uint8_t)connect_speed;
        uint16_t detail = 0;
        long rc = p294_terminal_detail(state, speed, &detail);
        if (rc != 0) return 2;
        unsigned int outcome =
            detail >= 0xe50U && detail <= 0xe53U ? 1U : 2U;
        hash = update(hash, (uint32_t)detail | (outcome << 16));
        if (!seen[detail]) { seen[detail] = 1U; ++details; }
        ++cases;
    }
    printf("cases=%u details=%u fnv64=%016llx\\n",
        cases, details, (unsigned long long)hash);
    return 0;
}
"""
    )


def audit_runtime_classifier(runtime: bytes) -> dict[str, Any]:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise ClosureError("host C compiler is unavailable")
    expected = _expected_classifier_result()
    expected_line = (
        f"cases={expected['case_count']} details={expected['detail_count']} "
        f"fnv64={expected['fnv64']}\n"
    )
    with tempfile.TemporaryDirectory(prefix="s22-p298-classifier-") as tmp:
        directory = Path(tmp)
        source = directory / "classifier.c"
        output = directory / "classifier"
        source.write_bytes(_classifier_tu(runtime))
        compiled = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compiled.returncode != 0:
            raise ClosureError(
                "P2.98 classifier host compile failed: "
                + compiled.stderr.decode("utf-8", "replace")[-2000:]
            )
        executed = subprocess.run(
            [str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    actual = executed.stdout.decode("ascii", "replace")
    if executed.returncode != 0 or actual != expected_line:
        raise ClosureError(
            f"P2.98 classifier SoT differs: expected={expected_line!r}, "
            f"actual={actual!r}, rc={executed.returncode}"
        )
    return {
        **expected,
        "compiler": str(Path(compiler).resolve()),
        "runtime_matches_python_sot": True,
        "verified": True,
    }


def _expected_start_classifier_result() -> dict[str, Any]:
    value = 1469598103934665603
    details = set()
    count = 0
    for entered in (False, True):
        for returned in (False, True):
            for rc in (-110, -22, -11, -5, -1, 0, 1):
                for hits in range(4):
                    detail = spec.start_result_detail(
                        entered=entered,
                        returned=returned,
                        rc=rc,
                        ep_enable_hits=hits,
                    )
                    value = _fnv_update(value, detail)
                    details.add(detail)
                    count += 1
    return {
        "case_count": count,
        "detail_count": len(details),
        "fnv64": f"{value:016x}",
    }


def _start_classifier_tu(runtime: bytes) -> bytes:
    marker = b"struct p282_bind_trace_result {\n"
    start = runtime.find(marker)
    end = runtime.find(b"};\n", start)
    if start < 0 or end < 0:
        raise ClosureError("P2.98 bind-result source is absent")
    end += len(b"};\n")
    fn_start, fn_end = transform.base._function_span(  # noqa: SLF001
        runtime, b"p298_start_result_detail"
    )
    return (
        b"#include <stdint.h>\n#include <stdio.h>\n"
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define EAGAIN 11\n#define EINVAL 22\n#define ETIMEDOUT 110\n"
        b"#define P298_DETAIL_GADGET_START_NOT_REACHED 0xf64U\n"
        b"#define P298_DETAIL_GADGET_START_NO_RETURN 0xf65U\n"
        b"#define P298_DETAIL_GADGET_START_POSITIVE_RC 0xf66U\n"
        b"#define P298_DETAIL_EP_ENABLE_HIT_CONTRADICTION 0xf67U\n"
        b"#define P298_DETAIL_EP0_OUT_EINVAL 0xf68U\n"
        b"#define P298_DETAIL_EP0_OUT_EAGAIN 0xf69U\n"
        b"#define P298_DETAIL_EP0_OUT_ETIMEDOUT 0xf6aU\n"
        b"#define P298_DETAIL_EP0_IN_EINVAL 0xf6bU\n"
        b"#define P298_DETAIL_EP0_IN_EAGAIN 0xf6cU\n"
        b"#define P298_DETAIL_EP0_IN_ETIMEDOUT 0xf6dU\n"
        b"#define P298_DETAIL_GADGET_START_NEGATIVE_RC_CONTRADICTION 0xf6eU\n"
        + runtime[start:end]
        + runtime[fn_start:fn_end]
        + b"""
static uint64_t update(uint64_t value, uint32_t word) {
    return (value ^ word) * UINT64_C(1099511628211);
}
int main(void) {
    static const int rcs[] = {-110, -22, -11, -5, -1, 0, 1};
    uint64_t hash = UINT64_C(1469598103934665603);
    uint8_t seen[65536] = {0};
    unsigned int cases = 0;
    unsigned int details = 0;
    for (unsigned int entered = 0; entered < 2; ++entered)
    for (unsigned int returned = 0; returned < 2; ++returned)
    for (unsigned int r = 0; r < sizeof(rcs) / sizeof(rcs[0]); ++r)
    for (unsigned int hits = 0; hits < 4; ++hits) {
        struct p282_bind_trace_result result = {0};
        result.start_entered = (uint8_t)entered;
        result.start_returned = (uint8_t)returned;
        result.start_rc = rcs[r];
        result.ep_enable_hits = (uint8_t)hits;
        uint32_t detail = (uint32_t)p298_start_result_detail(&result);
        hash = update(hash, detail);
        if (!seen[detail]) { seen[detail] = 1U; ++details; }
        ++cases;
    }
    printf("cases=%u details=%u fnv64=%016llx\\n",
        cases, details, (unsigned long long)hash);
    return 0;
}
"""
    )


def audit_start_classifier(runtime: bytes) -> dict[str, Any]:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise ClosureError("host C compiler is unavailable")
    expected = _expected_start_classifier_result()
    expected_line = (
        f"cases={expected['case_count']} details={expected['detail_count']} "
        f"fnv64={expected['fnv64']}\n"
    )
    with tempfile.TemporaryDirectory(prefix="s22-p298-start-classifier-") as tmp:
        directory = Path(tmp)
        source = directory / "start-classifier.c"
        output = directory / "start-classifier"
        source.write_bytes(_start_classifier_tu(runtime))
        compiled = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compiled.returncode != 0:
            raise ClosureError(
                "P2.98 start classifier host compile failed: "
                + compiled.stderr.decode("utf-8", "replace")[-2000:]
            )
        executed = subprocess.run(
            [str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    actual = executed.stdout.decode("ascii", "replace")
    if executed.returncode != 0 or actual != expected_line:
        raise ClosureError(
            f"P2.98 start classifier SoT differs: expected={expected_line!r}, "
            f"actual={actual!r}, rc={executed.returncode}"
        )
    return {
        **expected,
        "runtime_matches_python_sot": True,
        "verified": True,
    }


def _definition(runtime: bytes, marker: bytes) -> bytes:
    start = runtime.find(marker)
    if start < 0 or runtime.find(marker, start + 1) >= 0:
        raise ClosureError(
            f"P2.98 C definition marker differs: {marker[:60]!r}"
        )
    brace = runtime.find(b"{", start)
    if brace < 0:
        raise ClosureError("P2.98 C definition has no body")
    depth = 0
    for index in range(brace, len(runtime)):
        if runtime[index] == ord("{"):
            depth += 1
        elif runtime[index] == ord("}"):
            depth -= 1
            if depth == 0:
                end = index + 1
                if end < len(runtime) and runtime[end : end + 1] == b"\n":
                    end += 1
                return runtime[start:end]
    raise ClosureError("P2.98 C definition body is unterminated")


def _struct(runtime: bytes, marker: bytes) -> bytes:
    start = runtime.find(marker)
    end = runtime.find(b"};\n", start)
    if start < 0 or end < 0:
        raise ClosureError(f"P2.98 C struct differs: {marker!r}")
    return runtime[start : end + len(b"};\n")]


def _trace_parser_tu(runtime: bytes) -> bytes:
    structures = b"".join(
        _struct(runtime, marker)
        for marker in (
            b"struct p282_trace_record {\n",
            b"struct p282_trace_pair {\n",
            b"struct p282_trace_control {\n",
            b"struct p282_bind_trace_result {\n",
        )
    )
    functions = b"".join(
        _definition(runtime, marker)
        for marker in (
            b"static const char *p282_find_bytes(\n",
            b"static int p282_is_space(char value) {\n",
            b"static int p282_is_digit(char value) {\n",
            b"static long p282_parse_unsigned(\n"
            b"    const char *start,\n"
            b"    const char *end,\n"
            b"    uint64_t *result) {\n",
            b"static long p282_parse_signed(\n",
            b"static const char *p282_line_find(\n",
            b"static long p282_parse_field(\n",
            b"static long p298_parse_unsigned_field(\n",
            b"static long p282_parse_line_identity(\n",
            b"static int p282_record_argument_matches(\n",
            b"static long p282_pair_in_window(\n",
            b"static long p282_parse_trace_records(\n",
            b"static long p282_parse_bind_result(\n",
            b"static long p298_profile_matches(\n",
        )
    )
    return (
        b"#include <errno.h>\n#include <limits.h>\n#include <stdint.h>\n"
        b"#include <stdio.h>\n"
        b"#include <string.h>\n"
        b"#define P260_EPROTO 71\n#define P260_EOVERFLOW 75\n"
        b"#define P282_CYCLE_EVENT_COUNT 16U\n"
        b"#define P282_BIND_EVENT_COUNT 12U\n"
        b"#define P282_RECORD_CAPACITY 64U\n"
        b"#define P282_BIND_DIRECT 0U\n"
        b"#define P282_BIND_RESUME_NESTED 1U\n"
        b"#define P282_BIND_DIAGNOSTIC_DEGRADED 2U\n"
        b"#define P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH 0xf72U\n"
        b"struct p282_event_descriptor { const char *name; };\n"
        b"static const struct p282_event_descriptor p282_bind_events[] = {\n"
        b" {\"resume_in\"}, {\"resume_out\"}, {\"pull_in\"}, {\"pull_out\"},\n"
        b" {\"run_in\"}, {\"run_out\"}, {\"dwc3_state_snapshot\"},\n"
        b" {\"gadget_start_in\"}, {\"gadget_start_out\"}, {\"ep_enable_in\"},\n"
        b" {\"reset_in\"}, {\"connect_done_in\"},\n};\n"
        + structures
        + b"static char p282_trace_buffer[16384];\n"
        b"static size_t p282_trace_length;\n"
        b"static size_t cstr_len(const char *value) { return strlen(value); }\n"
        b"static int p260_bytes_equal(const void *a, const void *b, size_t n) {\n"
        b"    return memcmp(a, b, n) == 0;\n}\n"
        + functions
        + br'''
static void set_trace(const char *trace) {
    p282_trace_length = strlen(trace);
    if (p282_trace_length >= sizeof(p282_trace_buffer)) {
        p282_trace_length = 0;
        return;
    }
    memcpy(p282_trace_buffer, trace, p282_trace_length);
}

static int expect_ok(
    const char *trace,
    int entered,
    int returned,
    int start_rc,
    int hits,
    int reset,
    int connect_done) {
    struct p282_trace_control control = {
        .events = p282_bind_events,
        .event_count = P282_BIND_EVENT_COUNT,
    };
    struct p282_bind_trace_result result = {0};
    set_trace(trace);
    long rc = p282_parse_bind_result(&control, &result);
    if (rc != 0
        || result.start_entered != entered
        || result.start_returned != returned
        || result.start_rc != start_rc
        || result.ep_enable_hits != hits
        || result.reset_seen != reset
        || result.connect_done_seen != connect_done
        || !result.snapshot_seen
        || !result.pullup_returned_zero
        || !result.run_stop_seen
        || result.branch != P282_BIND_DIRECT) {
        return 1;
    }
    if (entered && result.start_dwc != UINT64_C(18446744073709551600)) {
        return 2;
    }
    for (size_t index = 0; index < control.event_count; ++index) {
        control.profile_hits[index] = result.record_hits[index];
    }
    if (p298_profile_matches(&control, &result) != 0) {
        return 3;
    }
    ++control.profile_hits[7];
    if (p298_profile_matches(&control, &result)
        != P298_DETAIL_FINAL_TRACE_PROFILE_MISMATCH) {
        return 4;
    }
    return 0;
}

static int expect_fail(const char *trace) {
    struct p282_trace_control control = {
        .events = p282_bind_events,
        .event_count = P282_BIND_EVENT_COUNT,
    };
    struct p282_bind_trace_result result = {0};
    set_trace(trace);
    return p282_parse_bind_result(&control, &result) == 0;
}

#define PULL_IN "init-1 [000] 1: pull_in: on=1\n"
#define START_IN "init-1 [000] 2: gadget_start_in: dwc=18446744073709551600\n"
#define EP1 "init-1 [000] 3: ep_enable_in:\n"
#define EP2 "init-1 [000] 4: ep_enable_in:\n"
#define START_ZERO "init-1 [000] 5: gadget_start_out: rc=0\n"
#define RUN_IN "init-1 [000] 6: run_in: on=1\n"
#define SNAPSHOT "init-1 [000] 7: dwc3_state_snapshot: link=0 run_stop=1 devctrlhlt=0 coreidle=1 prtcap=2 susphy=0 connect_speed=0\n"
#define RUN_OUT "init-1 [000] 8: run_out: rc=0\n"
#define PULL_OUT "init-1 [000] 9: pull_out: rc=0\n"

int main(void) {
    unsigned int cases = 0;
    int rc = expect_ok(
        PULL_IN START_IN EP1 EP2 START_ZERO RUN_IN SNAPSHOT RUN_OUT PULL_OUT,
        1, 1, 0, 2, 0, 0);
    if (rc != 0) return 10 + rc;
    ++cases;
    rc = expect_ok(
        PULL_IN START_IN EP1
        "init-1 [000] 4: gadget_start_out: rc=-22\n"
        "init-1 [000] 5: run_in: on=1\n"
        "init-1 [000] 6: dwc3_state_snapshot: link=0 run_stop=1 devctrlhlt=0 coreidle=1 prtcap=2 susphy=0 connect_speed=0\n"
        "init-1 [000] 7: run_out: rc=0\n"
        "init-1 [000] 8: pull_out: rc=0\n",
        1, 1, -22, 1, 0, 0);
    if (rc != 0) return 20 + rc;
    ++cases;
    rc = expect_ok(
        PULL_IN START_IN EP1 EP2
        "init-1 [000] 5: gadget_start_out: rc=-110\n"
        RUN_IN SNAPSHOT RUN_OUT PULL_OUT,
        1, 1, -110, 2, 0, 0);
    if (rc != 0) return 30 + rc;
    ++cases;
    rc = expect_ok(
        PULL_IN START_IN EP1 EP2 START_ZERO RUN_IN SNAPSHOT RUN_OUT PULL_OUT
        "irq-42 [001] 10: reset_in: dwc=18446744073709551600\n"
        "irq-42 [001] 11: connect_done_in: dwc=18446744073709551600\n",
        1, 1, 0, 2, 1, 1);
    if (rc != 0) return 40 + rc;
    ++cases;
    rc = expect_ok(
        PULL_IN
        "init-1 [000] 2: run_in: on=1\n"
        "init-1 [000] 3: dwc3_state_snapshot: link=0 run_stop=1 devctrlhlt=0 coreidle=1 prtcap=2 susphy=0 connect_speed=0\n"
        "init-1 [000] 4: run_out: rc=0\n"
        "init-1 [000] 5: pull_out: rc=0\n",
        0, 0, 0, 0, 0, 0);
    if (rc != 0) return 50 + rc;
    ++cases;
    rc = expect_ok(
        PULL_IN START_IN EP1 EP2 RUN_IN SNAPSHOT RUN_OUT PULL_OUT,
        1, 0, 0, 2, 0, 0);
    if (rc != 0) return 60 + rc;
    ++cases;
    if (expect_fail(
        PULL_IN START_IN EP1 EP2 START_ZERO RUN_IN SNAPSHOT RUN_OUT PULL_OUT
        "irq-42 [001] 10: reset_in: dwc=7\n")) return 70;
    ++cases;
    if (expect_fail(
        PULL_IN START_IN
        "init-1 [000] 3: gadget_start_in: dwc=18446744073709551600\n"
        EP2 START_ZERO RUN_IN SNAPSHOT RUN_OUT PULL_OUT)) return 80;
    ++cases;
    if (expect_fail(
        "init-2 [000] 1: pull_in: on=1\n"
        START_IN EP1 EP2 START_ZERO RUN_IN SNAPSHOT RUN_OUT PULL_OUT)) return 90;
    ++cases;
    if (expect_fail(
        PULL_IN START_IN EP1 EP2 START_ZERO
        "init-1 [000] 4: run_in: on=1\n"
        SNAPSHOT RUN_OUT PULL_OUT)) return 100;
    ++cases;
    printf("cases=%u exact-profile=1 mismatch-profile=1 uint64-dwc=1\n", cases);
    return 0;
}
'''
    )


def audit_trace_parser(runtime: bytes) -> dict[str, Any]:
    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        raise ClosureError("host C compiler is unavailable")
    expected = "cases=10 exact-profile=1 mismatch-profile=1 uint64-dwc=1\n"
    with tempfile.TemporaryDirectory(prefix="s22-p298-trace-parser-") as tmp:
        directory = Path(tmp)
        source = directory / "trace-parser.c"
        output = directory / "trace-parser"
        source.write_bytes(_trace_parser_tu(runtime))
        compiled = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(source),
                "-o",
                str(output),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if compiled.returncode != 0:
            raise ClosureError(
                "P2.98 trace parser host compile failed: "
                + compiled.stderr.decode("utf-8", "replace")[-4000:]
            )
        executed = subprocess.run(
            [str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    actual = executed.stdout.decode("ascii", "replace")
    if executed.returncode != 0 or actual != expected:
        raise ClosureError(
            f"P2.98 trace parser execution differs: expected={expected!r}, "
            f"actual={actual!r}, rc={executed.returncode}"
        )
    return {
        "case_count": 10,
        "negative_out_and_in": True,
        "zero_hit_distinct": True,
        "missing_return_distinct": True,
        "wrong_pid_rejected": True,
        "wrong_dwc_rejected": True,
        "duplicate_entry_rejected": True,
        "counter_order_rejected": True,
        "uint64_dwc_executed": True,
        "profile_record_match_executed": True,
        "verified": True,
    }


def audit_pair_adjacency(runtime: bytes) -> dict[str, Any]:
    return inherited.audit_pair_publication_adjacency(
        runtime,
        helper_name="p294_publish_final_pair",
        first_publish_expression=(
            b"s22_p294_checkpoint_progress_position(\n"
            b"        &g_checkpoint, "
            b"S22_P294_POSITION_USBLNKST, first_detail)"
        ),
        terminal_publish_expression=(
            b"s22_p294_checkpoint_terminal_position(\n"
            b"        &g_checkpoint, "
            b"S22_P294_POSITION_FINAL_STATE, terminal_detail)"
        ),
    )


def audit_delivery(artifacts: dict[str, bytes]) -> dict[str, Any]:
    patch = artifacts["candidate_patch"]
    descriptor = artifacts["trace_descriptor_header"]
    runtime = artifacts["p290_e3_runtime_include"]
    required_targets = {
        b"__dwc3_gadget_start": 2,
        b"__dwc3_gadget_ep_enable": 1,
        b"dwc3_gadget_reset_interrupt": 1,
        b"dwc3_gadget_conndone_interrupt": 1,
    }
    if (
        patch.count(b"s22_p294_dwc3_state_snapshot") != 2
        or descriptor.count(b"s22_p294_dwc3_state_snapshot") != 1
        or b"#define P282_BIND_EVENT_COUNT 12U" not in descriptor
        or any(
            descriptor.count(symbol) != count
            for symbol, count in required_targets.items()
        )
        or runtime.count(b"p298_finish_observer") < 3
        or runtime.count(b"profile_hits") < 4
    ):
        raise ClosureError("P2.98 built-in observer delivery differs")
    return {
        "bind_event_count": 12,
        "probe_targets": [
            target.decode("ascii") for target in required_targets
        ],
        "candidate_module_injection_required": False,
        "verified": True,
    }


def audit_result_contract(runtime: bytes) -> dict[str, Any]:
    setup = runtime.find(b"long setup_rc = p282_trace_setup(P282_PHASE_BIND")
    bind = runtime.find(b"long bind_rc = p260_bind_udc();", setup)
    setup_failure = runtime.find(b"p298_setup_failure_detail(setup_rc)", setup)
    initial_read = runtime.find(b"p282_trace_read_snapshot(control, 0)", bind)
    final_finish = runtime.find(b"p298_finish_observer(\n                control", initial_read)
    publish = runtime.find(b"p294_publish_final_pair(first_detail", final_finish)
    if not (
        0 <= setup < setup_failure < bind < initial_read < final_finish < publish
    ):
        raise ClosureError("P2.98 observer lifecycle ordering differs")
    required = (
        b"control->profile_hits[index] != result->record_hits[index]",
        b"result->ep_enable_hits == 2U",
        b"P298_DETAIL_GADGET_START_NOT_REACHED",
        b"P298_DETAIL_GADGET_START_NO_RETURN",
        b"P298_DETAIL_EP0_OUT_ETIMEDOUT",
        b"P298_DETAIL_EP0_IN_ETIMEDOUT",
        b"record->dwc != result->start_dwc",
        b"event_mask * 16U",
    )
    if any(token not in runtime for token in required):
        raise ClosureError("P2.98 observer result contract differs")
    return {
        "setup_failure_prevents_bind": True,
        "zero_hit_distinct_from_registration_failure": True,
        "profile_record_counts_exact": True,
        "ep0_out_in_attributed_by_entry_hits": True,
        "controller_pointer_attributed": True,
        "trace_cleanup_precedes_final_pair": True,
        "verified": True,
    }


def audit_driver_source(root: Path) -> dict[str, Any]:
    reference = root / p296.DRIVER_SOURCE_REFERENCE
    common = reference / "kernel_platform/common/drivers/usb/dwc3/gadget.c"
    msm = reference / "kernel_platform/msm-kernel/drivers/usb/dwc3/gadget.c"
    common_data = common.read_bytes()
    msm_data = msm.read_bytes()
    if common_data != msm_data:
        raise ClosureError("P2.98 common/msm DWC3 gadget sources differ")
    start = common_data.find(
        b"static int __dwc3_gadget_start(struct dwc3 *dwc)\n{"
    )
    end = common_data.find(b"\n}\n", start) + 3
    function = common_data[start:end]
    if (
        start < 0
        or function.count(b"__dwc3_gadget_ep_enable(") != 2
        or function.count(b"goto err0;") != 1
        or function.count(b"goto err1;") != 1
        or b"dep = dwc->eps[0];" not in function
        or b"dep = dwc->eps[1];" not in function
    ):
        raise ClosureError("P2.98 EP0 enable command chain source differs")

    def source_function(signature: bytes) -> bytes:
        function_start = common_data.find(signature)
        function_end = common_data.find(b"\n}\n", function_start) + 3
        if function_start < 0 or function_end <= 2:
            raise ClosureError(
                f"P2.98 driver source function differs: {signature!r}"
            )
        return common_data[function_start:function_end]

    send_command = source_function(b"int dwc3_send_gadget_ep_cmd(")
    resize = source_function(b"static int dwc3_gadget_resize_tx_fifos(")
    start_config = source_function(b"static int dwc3_gadget_start_config(")
    xfer_resource = source_function(b"static int dwc3_gadget_set_xfer_resource(")
    set_config = source_function(b"static int dwc3_gadget_set_ep_config(")
    ep_enable = source_function(b"static int __dwc3_gadget_ep_enable(")
    errno_domain = {
        match.decode("ascii")
        for match in re.findall(br"\bret = -(E[A-Z0-9]+);", send_command)
    }
    if (
        errno_domain != {"EINVAL", "EAGAIN", "ETIMEDOUT"}
        or b"if (!usb_endpoint_dir_in(dep->endpoint.desc) || dep->number <= 1)\n"
        b"\t\treturn 0;" not in resize
        or start_config.count(b"dwc3_send_gadget_ep_cmd(") != 1
        or start_config.count(b"dwc3_gadget_set_xfer_resource(") != 1
        or xfer_resource.count(b"dwc3_send_gadget_ep_cmd(") != 1
        or set_config.count(b"dwc3_send_gadget_ep_cmd(") != 1
        or ep_enable.count(b"dwc3_gadget_start_config(") != 1
        or ep_enable.count(b"dwc3_gadget_set_ep_config(") != 1
        or b"if (usb_endpoint_xfer_control(desc))\n\t\t\tgoto out;"
        not in ep_enable
    ):
        raise ClosureError("P2.98 EP0 command errno closure differs")
    return {
        "common": _receipt(common_data),
        "msm": _receipt(msm_data),
        "byte_identical": True,
        "ep_enable_call_count": 2,
        "failure_edges": ["err0", "err1"],
        "command_chain": [
            "dwc3_gadget_start_config",
            "dwc3_gadget_set_xfer_resource",
            "dwc3_gadget_set_ep_config",
            "dwc3_send_gadget_ep_cmd",
        ],
        "expected_negative_errno": sorted(errno_domain),
        "ep0_skips_non_control_start_transfer": True,
        "claim": "EP0_ENABLE_COMMAND_CHAIN_PROVED",
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
            "candidate_patch": _receipt(artifacts["candidate_patch"]),
            "verified": True,
        },
        "runtime_classifier": audit_runtime_classifier(
            artifacts["p290_e3_runtime_include"]
        ),
        "start_result_classifier": audit_start_classifier(
            artifacts["p290_e3_runtime_include"]
        ),
        "trace_parser": audit_trace_parser(
            artifacts["p290_e3_runtime_include"]
        ),
        "pair_adjacency": audit_pair_adjacency(
            artifacts["p290_e3_runtime_include"]
        ),
        "delivery": audit_delivery(artifacts),
        "result_contract": audit_result_contract(
            artifacts["p290_e3_runtime_include"]
        ),
        "driver_source": audit_driver_source(root),
        "baseline": {
            "control": "P2.96 historical behavioral no-probe baseline",
            "dedicated_control_f1_required": False,
            "reopen_conditions": [
                "unexplained-prefix-or-tuple-drift",
                "probe-provenance-contradiction",
                "new-health-anomaly",
                "new-hazard-class",
            ],
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
