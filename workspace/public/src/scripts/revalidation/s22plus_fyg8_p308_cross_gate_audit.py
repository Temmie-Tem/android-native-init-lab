#!/usr/bin/env python3
"""Execute P3.08 encoder outputs against the actual inherited gates."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Iterable

import s22plus_fyg8_p300_telemetry_closure as compile_support
import s22plus_fyg8_p303_telemetry_spec as p303
import s22plus_fyg8_p307_telemetry_spec as p307
import s22plus_fyg8_p308_generator as generator
import s22plus_fyg8_p308_telemetry_decoder as decoder
import s22plus_fyg8_p308_telemetry_model as model
import s22plus_fyg8_p308_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p308_cross_gate_audit_v1"
VERDICT = "PASS_P308_ACTUAL_ENCODER_OUTPUTS_SUBSET_ALL_GATES_HOST_ONLY"


class AuditError(ValueError):
    pass


def _generated(root: Path) -> dict[str, bytes]:
    run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
    unsat = model.unsat_record(spec.PROFILE, run_id)
    return generator.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat[len(model.UNSAT_FAMILY) :],
        profile=spec.PROFILE,
    )


def _definition(source: bytes, marker: bytes, *, last: bool = False) -> bytes:
    start = source.rfind(marker) if last else source.find(marker)
    if start < 0 or (not last and source.find(marker, start + 1) >= 0):
        raise AuditError(f"C definition marker differs: {marker!r}")
    brace = source.find(b"{", start)
    if brace < 0:
        raise AuditError(f"C definition has no body: {marker!r}")
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == ord("{"):
            depth += 1
        elif source[index] == ord("}"):
            depth -= 1
            if depth == 0:
                end = index + 1
                if source[end : end + 1] == b"\n":
                    end += 1
                return source[start:end]
    raise AuditError(f"C definition is unterminated: {marker!r}")


def _struct(source: bytes, marker: bytes) -> bytes:
    start = source.find(marker)
    if start < 0 or source.find(marker, start + 1) >= 0:
        raise AuditError(f"C struct marker differs: {marker!r}")
    end = source.find(b"};\n", start)
    if end < 0:
        raise AuditError(f"C struct is unterminated: {marker!r}")
    return source[start : end + 3]


def _table(source: bytes, marker: bytes) -> bytes:
    start = source.find(marker)
    if start < 0 or source.find(marker, start + 1) >= 0:
        raise AuditError(f"C table marker differs: {marker!r}")
    end = source.find(b"};\n", start)
    if end < 0:
        raise AuditError(f"C table is unterminated: {marker!r}")
    return source[start : end + 3]


def _macro(source: bytes, name: bytes) -> bytes:
    match = re.search(rb"^#define " + re.escape(name) + rb" [^\n]+\n", source, re.M)
    if match is None:
        raise AuditError(f"C macro differs: {name!r}")
    return match.group(0)


def _array(name: str, values: Iterable[int]) -> bytes:
    encoded = ",".join(f"0x{value:x}U" for value in values)
    return f"static const uint16_t {name}[] = {{{encoded}}};\n".encode("ascii")


def _compile(source: bytes, label: str) -> str:
    try:
        return compile_support._compile_and_run(source, label)  # noqa: SLF001
    except compile_support.ClosureError as exc:
        raise AuditError(str(exc)) from exc


def _runtime_gate_tu(runtime: bytes) -> bytes:
    macros = b"".join(
        _macro(runtime, name)
        for name in (
            b"P294_LINK_DETAIL_BASE",
            b"P301_FINAL_DRIFT_DETAIL_BASE",
            b"P301_FINAL_DRIFT_DETAIL_MAX",
            b"P301_DETAIL_SUBTYPE_EMPTY_MASK",
            b"P301_DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION",
            b"P307_SUMMARY_DETAIL_BASE",
            b"P308_SUMMARY_DETAIL_MAX",
            b"P308_DEGRADED_DETAIL_BASE",
            b"P308_DEGRADED_DETAIL_MAX",
        )
    )
    arrays = b"".join(
        (
            _array("attr_outputs", spec.attribution_outputs()),
            _array("clock_outputs", spec.clock_outputs()),
            _array("summary_outputs", spec.summary_outputs()),
            _array("degraded_outputs", spec.degraded_outputs()),
        )
    )
    guard = _definition(runtime, b"static int p301_terminal_detail_allowed(")
    publisher = _definition(runtime, b"static long p294_publish_final_pair(")
    return (
        br'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define P260_EPROTO 71
#define S22_P294_POSITION_USBLNKST 105U
#define S22_P294_POSITION_FINAL_STATE 106U
struct checkpoint_fixture { uint8_t generation; uint8_t terminal; };
static struct checkpoint_fixture g_checkpoint;
static unsigned int progress_calls;
static unsigned int terminal_calls;
static long s22_p294_checkpoint_progress_position(
    struct checkpoint_fixture *client, uint8_t ordinal, uint16_t detail) {
    (void)detail;
    ++progress_calls;
    if (client->generation != ordinal || client->terminal) return -P260_EPROTO;
    ++client->generation;
    return 0;
}
static long s22_p294_checkpoint_terminal_position(
    struct checkpoint_fixture *client, uint8_t ordinal, uint16_t detail) {
    (void)detail;
    ++terminal_calls;
    if (client->generation != ordinal || client->terminal) return -P260_EPROTO;
    ++client->generation;
    client->terminal = 1U;
    return 0;
}
static void reset_checkpoint(void) {
    g_checkpoint = (struct checkpoint_fixture){.generation = 105U};
    progress_calls = 0U;
    terminal_calls = 0U;
}
'''
        + macros
        + guard
        + publisher
        + arrays
        + br'''
static int check_a(const uint16_t *values, size_t count) {
    for (size_t index = 0; index < count; ++index) {
        reset_checkpoint();
        if (p294_publish_final_pair(values[index], 0x4001U) != 0
            || progress_calls != 1U || terminal_calls != 1U) return 10;
    }
    return 0;
}
static int check_b(const uint16_t *values, size_t count) {
    for (size_t index = 0; index < count; ++index) {
        reset_checkpoint();
        if (p294_publish_final_pair(0xd00U, values[index]) != 0
            || progress_calls != 1U || terminal_calls != 1U) return 20;
    }
    return 0;
}
int main(void) {
    int rc = check_a(attr_outputs, sizeof(attr_outputs) / sizeof(attr_outputs[0]));
    if (!rc) rc = check_a(clock_outputs, sizeof(clock_outputs) / sizeof(clock_outputs[0]));
    if (!rc) rc = check_b(summary_outputs, sizeof(summary_outputs) / sizeof(summary_outputs[0]));
    if (!rc) rc = check_b(degraded_outputs, sizeof(degraded_outputs) / sizeof(degraded_outputs[0]));
    if (!rc && (p301_terminal_detail_allowed(0x4febU) != 1
        || p301_terminal_detail_allowed(0x4fecU) != 0
        || p301_terminal_detail_allowed(0x60ffU) != 0
        || p301_terminal_detail_allowed(0x6100U) != 1
        || p301_terminal_detail_allowed(0x673fU) != 1
        || p301_terminal_detail_allowed(0x6740U) != 0)) rc = 30;
    reset_checkpoint();
    if (!rc && (p294_publish_final_pair(0xdb0U, 0x4001U) != -P260_EPROTO
        || progress_calls != 0U || terminal_calls != 0U)) rc = 31;
    if (rc) return rc;
    printf("runtime-a=313 runtime-b=5675 boundaries=7\n");
    return 0;
}
'''
    )


def _checkpoint_gate_tu(checkpoint: bytes, header: bytes) -> bytes:
    macros = b"".join(
        _macro(checkpoint, name)
        for name in (
            b"S22_P233_OUTCOME_PROGRESS",
            b"S22_P233_OUTCOME_FAILURE",
            b"S22_P248_STEP_NORMAL",
            b"S22_P248_STEP_GATE",
            b"S22_P248_STEP_TERMINAL",
            b"S22_P248_DETAIL_ERRNO_MAX",
            b"S22_P248_DETAIL_REGRESSION_BASE",
            b"S22_P248_DETAIL_REGRESSION_MAX",
            b"S22_P248_DETAIL_READ_ERROR_BASE",
            b"S22_P248_DETAIL_READ_ERROR_MAX",
        )
    ) + b"".join(
        _macro(header, name)
        for name in (
            b"S22_P292_PUBLICATION_ERRNO_MAX",
            b"S22_P292_PUBLICATION_OPEN_BASE",
            b"S22_P292_PUBLICATION_WRITE_BASE",
            b"S22_P292_PUBLICATION_CLOSE_BASE",
        )
    )
    pieces = b"".join(
        (
            _struct(checkpoint, b"struct s22_p248_step {\n"),
            _table(checkpoint, b"static const struct s22_p248_step k_p248_e2_steps[]"),
            _struct(checkpoint, b"struct p288_detail_rule {\n"),
            _table(checkpoint, b"static const struct p288_detail_rule k_p288_detail_rules[]"),
            _definition(checkpoint, b"static int p288_tuple_allowed("),
            _definition(checkpoint, b"static int p288_detail_allowed("),
        )
    )
    arrays = b"".join(
        (
            _array("attr_outputs", spec.attribution_outputs()),
            _array("clock_outputs", spec.clock_outputs()),
            _array("summary_outputs", spec.summary_outputs()),
            _array("degraded_outputs", spec.degraded_outputs()),
        )
    )
    return (
        b"#include <stddef.h>\n#include <stdint.h>\n#include <stdio.h>\n"
        + macros
        + pieces
        + arrays
        + br'''
static int check_values(
    size_t ordinal, uint8_t outcome, const uint16_t *values, size_t count) {
    for (size_t index = 0; index < count; ++index) {
        if (!p288_detail_allowed(ordinal, outcome, values[index])) return 10;
    }
    return 0;
}
int main(void) {
    int rc = check_values(105U, 0U, attr_outputs, sizeof(attr_outputs) / sizeof(attr_outputs[0]));
    if (!rc) rc = check_values(105U, 0U, clock_outputs, sizeof(clock_outputs) / sizeof(clock_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, summary_outputs, sizeof(summary_outputs) / sizeof(summary_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, degraded_outputs, sizeof(degraded_outputs) / sizeof(degraded_outputs[0]));
    if (!rc && (p288_detail_allowed(105U, 0U, 0xdb0U)
        || p288_detail_allowed(106U, 2U, 0x4000U)
        || p288_detail_allowed(106U, 2U, 0x5000U)
        || p288_detail_allowed(106U, 2U, 0x6000U))) rc = 20;
    if (rc) return rc;
    printf("checkpoint-a=313 checkpoint-b=5675 holes=4\n");
    return 0;
}
'''
    )


def _added_patch_source(patch: bytes) -> bytes:
    return b"".join(
        line[1:]
        for line in patch.splitlines(keepends=True)
        if line.startswith(b"+") and not line.startswith(b"+++")
    )


def _kernel_gate_tu(patch: bytes) -> bytes:
    added = _added_patch_source(patch)
    pieces = b"".join(
        (
            _struct(added, b"struct s22_fyg8_p290_detail_rule {\n"),
            _table(added, b"static const struct s22_fyg8_p290_detail_rule\ns22_fyg8_p290_detail_rules[]"),
            _definition(added, b"static noinline __used bool s22_fyg8_p290_tuple_allowed("),
            _definition(added, b"static noinline __used bool s22_fyg8_e1_detail_allowed("),
        )
    )
    arrays = b"".join(
        (
            _array("attr_outputs", spec.attribution_outputs()),
            _array("clock_outputs", spec.clock_outputs()),
            _array("summary_outputs", spec.summary_outputs()),
            _array("degraded_outputs", spec.degraded_outputs()),
        )
    )
    return (
        br'''
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t u8;
typedef uint16_t u16;
#define noinline __attribute__((noinline))
#define __used __attribute__((used))
#define ARRAY_SIZE(value) (sizeof(value) / sizeof((value)[0]))
#define READ_ONCE(value) (value)
#define S22_FYG8_E1_PROFILE_E2 3U
#define S22_FYG8_E1_PROGRESS 0U
#define S22_FYG8_E1_FAILURE 2U
static const u8 s22_fyg8_e2_kinds[107] = {0};
static const u8 s22_fyg8_e2_items[107] = {0};
'''
        + pieces
        + arrays
        + br'''
static int check_values(
    size_t ordinal, u8 outcome, const uint16_t *values, size_t count) {
    for (size_t index = 0; index < count; ++index) {
        if (!s22_fyg8_e1_detail_allowed(
                S22_FYG8_E1_PROFILE_E2, ordinal, 107U,
                outcome, values[index])) return 10;
    }
    return 0;
}
int main(void) {
    int rc = check_values(105U, 0U, attr_outputs, sizeof(attr_outputs) / sizeof(attr_outputs[0]));
    if (!rc) rc = check_values(105U, 0U, clock_outputs, sizeof(clock_outputs) / sizeof(clock_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, summary_outputs, sizeof(summary_outputs) / sizeof(summary_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, degraded_outputs, sizeof(degraded_outputs) / sizeof(degraded_outputs[0]));
    if (!rc && (s22_fyg8_e1_detail_allowed(3U, 105U, 107U, 0U, 0xdb0U)
        || s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x4000U)
        || s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x5000U)
        || s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x6000U))) rc = 20;
    if (rc) return rc;
    printf("kernel-a=313 kernel-b=5675 holes=4\n");
    return 0;
}
'''
    )


def _parser_tu(runtime: bytes) -> bytes:
    structures = b"".join(
        (
            _struct(runtime, b"struct p303_kmsg_capture {\n"),
            _struct(runtime, b"struct p307_attribution_capture {\n"),
            _struct(runtime, b"struct p308_parser_capture {\n"),
        )
    )
    functions = b"".join(
        (
            _definition(runtime, b"static int p282_is_digit("),
            _definition(runtime, b"static int p282_is_space("),
            _definition(runtime, b"static const char *p282_find_bytes("),
            _definition(runtime, b"static long p282_parse_unsigned(", last=True),
            _definition(runtime, b"static long p303_parse_hex("),
            _definition(runtime, b"static long p307_parse_binary_after("),
            _definition(runtime, b"static void p308_latch_failure("),
            _definition(runtime, b"static long p308_kmsg_observe("),
            _definition(runtime, b"static long p303_kmsg_record("),
            _definition(runtime, b"static long p303_kmsg_drain("),
            _definition(runtime, b"static long p303_kmsg_finish("),
        )
    )
    macros = b"".join(
        _macro(runtime, name)
        for name in (
            b"P303_DETAIL_KMSG_READ_FAILED",
            b"P303_DETAIL_KMSG_RING_LOSS",
            b"P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION",
            b"P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION",
            b"P303_DETAIL_KMSG_COUNT_OVERFLOW",
            b"P303_KMSG_RECORD_CAPACITY",
            b"P303_EPIPE",
            b"P307_DETAIL_EUD_CACHE_READ_FAILED",
            b"P307_DETAIL_KMSG_ATTRIBUTION_FORMAT_CONTRADICTION",
            b"P308_FAILURE_SITE_LINE",
            b"P308_FAILURE_SITE_CSR",
            b"P308_FAILURE_SITE_DPDM",
            b"P308_FAILURE_SITE_CLOCK",
            b"P308_PREFIX_INIT",
            b"P308_PREFIX_CSR",
            b"P308_PREFIX_DPDM",
            b"P308_PREFIX_CLOCK",
        )
    )
    return (
        br'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define NULL ((void *)0)
#define EAGAIN 11
#define EINVAL 22
#define P260_EPROTO 71
#define P260_EOVERFLOW 75
'''
        + macros
        + structures
        + br'''
static size_t cstr_len(const char *value) { return strlen(value); }
static int p260_bytes_equal(const void *left, const void *right, size_t size) {
    return memcmp(left, right, size) == 0;
}
static struct p303_kmsg_capture g_p303_kmsg = {.fd = -1};
static struct p307_attribution_capture g_p307_attr;
static struct p308_parser_capture g_p308_parser;
static const char *const *fixture_records;
static size_t fixture_count;
static size_t fixture_index;
static int fixture_ring_loss;
static long sys_read(int fd, void *output, size_t capacity) {
    (void)fd;
    if (fixture_ring_loss) return -P303_EPIPE;
    if (fixture_index >= fixture_count) return -EAGAIN;
    const char *value = fixture_records[fixture_index++];
    size_t length = strlen(value);
    if (length > capacity) return -1;
    memcpy(output, value, length);
    return (long)length;
}
static long sys_close(int fd) { return fd == 3 ? 0 : -1; }
'''
        + functions
        + br'''
static void reset_fixture(const char *const *records, size_t count) {
    g_p303_kmsg = (struct p303_kmsg_capture){.fd = 3, .started = 1U};
    g_p307_attr = (struct p307_attribution_capture){0};
    g_p308_parser = (struct p308_parser_capture){0};
    fixture_records = records;
    fixture_count = count;
    fixture_index = 0U;
    fixture_ring_loss = 0;
}
int main(void) {
    static const char *const valid[] = {
        "6,1,0,-;msm_hsphy_init phy_flags:0x0\n msm_hsphy_dpdm_regulator_enable dpdm_enable:2\n",
        "6,2,0,-;csr:0x1 eud is enabled\n",
        "6,3,0,-;msm_hsphy_dpdm_regulator_enable dpdm_enable:0\n",
        "6,4,0,-;msm_hsphy_enable_clocks(): clocks_enabled:1 on:1\n",
    };
    reset_fixture(valid, sizeof(valid) / sizeof(valid[0]));
    if (p303_kmsg_finish() != 0 || !g_p303_kmsg.final
        || g_p308_parser.failure_latched
        || g_p308_parser.prefix_mask != 0xfU
        || g_p307_attr.init_count != 1U || !g_p307_attr.first_init_csr
        || g_p307_attr.dpdm_state != 3U) return 10;

    static const char *const degraded[] = {
        "6,1,0,-;msm_hsphy_dpdm_regulator_enable dpdm_enable:2\n",
        "6,2,0,-;msm_hsphy_enable_clocks(): clocks_enabled:0 on:1\n",
    };
    reset_fixture(degraded, sizeof(degraded) / sizeof(degraded[0]));
    if (p303_kmsg_finish() != 0 || !g_p303_kmsg.final
        || !g_p308_parser.failure_latched
        || g_p308_parser.failure_site != P308_FAILURE_SITE_DPDM
        || g_p308_parser.prefix_mask != (P308_PREFIX_DPDM | P308_PREFIX_CLOCK)
        || g_p307_attr.dpdm_state != 0U
        || g_p307_attr.preclock_state != 2U) return 20;

    static const char *const no_lf[] = {
        "6,1,0,-;msm_hsphy_enable_clocks(): clocks_enabled:0 on:1",
    };
    reset_fixture(no_lf, 1U);
    if (p303_kmsg_finish() != 0 || !g_p303_kmsg.final
        || g_p308_parser.failure_site != P308_FAILURE_SITE_LINE) return 30;

    static const char *const bad_sequence[] = {
        "6,1,0,-;msm_hsphy_init phy_flags:0x0\n",
        "6,3,0,-;msm_hsphy_enable_clocks(): clocks_enabled:0 on:1\n",
    };
    reset_fixture(bad_sequence, 2U);
    if (p303_kmsg_finish() != P303_DETAIL_KMSG_SEQUENCE_CONTRADICTION
        || g_p303_kmsg.final) return 40;

    reset_fixture(NULL, 0U);
    fixture_ring_loss = 1;
    if (p303_kmsg_finish() != P303_DETAIL_KMSG_RING_LOSS
        || g_p303_kmsg.final) return 50;
    printf("line-split=4 local-degraded-continues=1 parent-errors-immediate=2\n");
    return 0;
}
'''
    )


def _apply_pair(first: int, terminal: int) -> dict[str, Any]:
    run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
    record = model.initialize_record(spec.PROFILE, run_id)
    for generation, position in enumerate(spec.POSITIONS, 1):
        if generation == spec.ATTR_ORDINAL + 1:
            outcome, detail = spec.OUTCOME_PROGRESS, first
        elif generation == spec.SUMMARY_ORDINAL + 1:
            outcome, detail = spec.OUTCOME_FAILURE, terminal
        else:
            outcome, detail = model.OUTCOME_PROGRESS, 0
        request = model.encode_request(
            spec.PROFILE,
            position.stage,
            run_id=run_id,
            outcome=outcome,
            item_index=position.item_index,
            detail=detail,
        )
        record = model.apply_request(record, request)
        if generation == spec.SUMMARY_ORDINAL + 1:
            break
    return decoder.decode_record(
        record, expected_profile=spec.PROFILE, expected_run_id=run_id
    )


def audit_python_model_and_decoder() -> dict[str, Any]:
    attr = spec.attribution_outputs()
    clocks = spec.clock_outputs()
    summaries = spec.summary_outputs()
    degraded = spec.degraded_outputs()
    a_position = spec.position_for_generation(spec.ATTR_ORDINAL + 1)
    b_position = spec.position_for_generation(spec.SUMMARY_ORDINAL + 1)
    for value in (*attr, *clocks):
        spec.validate_slot(
            generation=spec.ATTR_ORDINAL + 1,
            stage=a_position.stage,
            outcome=spec.OUTCOME_PROGRESS,
            item_index=a_position.item_index,
            detail=value,
        )
    for value in (*summaries, *degraded):
        spec.validate_slot(
            generation=spec.SUMMARY_ORDINAL + 1,
            stage=b_position.stage,
            outcome=spec.OUTCOME_FAILURE,
            item_index=b_position.item_index,
            detail=value,
        )
    if any(
        spec.is_terminal_detail(value)
        for value in (0x4FEC, 0x60FF, 0x6740)
    ):
        raise AuditError("P3.08 host terminal boundary differs")
    for value in summaries:
        if decoder.decode_detail(
            value,
            outcome=spec.OUTCOME_FAILURE,
            generation=spec.SUMMARY_ORDINAL + 1,
        )["detail_kind"] != "p308-clock-qscratch-summary":
            raise AuditError("P3.08 normal decoder output differs")
    for value in degraded:
        if decoder.decode_detail(
            value,
            outcome=spec.OUTCOME_FAILURE,
            generation=spec.SUMMARY_ORDINAL + 1,
        )["detail_kind"] != "p308-degraded-observer-contradiction":
            raise AuditError("P3.08 degraded decoder output differs")
    normal = _apply_pair(0xD00, 0x4FC1)
    degraded_pair = _apply_pair(0xD00, 0x6100)
    if normal.get("p308_pair", {}).get("kind") != "normal":
        raise AuditError("P3.08 0x4FC1 pair context differs")
    if degraded_pair.get("p308_pair", {}).get("kind") != "degraded":
        raise AuditError("P3.08 0xD00 degraded pair context differs")
    return {
        "a_outputs_validated": len(attr) + len(clocks),
        "b_outputs_validated": len(summaries) + len(degraded),
        "normal_0x4fc1_pair_context": True,
        "degraded_0xd00_pair_context": True,
        "verified": True,
    }


def audit(root: Path) -> dict[str, Any]:
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    checkpoint = artifacts["checkpoint_client"]
    header = artifacts["p290_checkpoint_header"]
    patch = artifacts["candidate_patch"]
    runtime_result = _compile(_runtime_gate_tu(runtime), "p308-runtime-gates")
    checkpoint_result = _compile(
        _checkpoint_gate_tu(checkpoint, header), "p308-checkpoint-gate"
    )
    kernel_result = _compile(_kernel_gate_tu(patch), "p308-kernel-gate")
    parser_result = _compile(_parser_tu(runtime), "p308-kmsg-parser")
    expected = {
        "runtime": "runtime-a=313 runtime-b=5675 boundaries=7\n",
        "checkpoint": "checkpoint-a=313 checkpoint-b=5675 holes=4\n",
        "kernel": "kernel-a=313 kernel-b=5675 holes=4\n",
        "parser": (
            "line-split=4 local-degraded-continues=1 "
            "parent-errors-immediate=2\n"
        ),
    }
    actual = {
        "runtime": runtime_result,
        "checkpoint": checkpoint_result,
        "kernel": kernel_result,
        "parser": parser_result,
    }
    if actual != expected:
        raise AuditError(f"P3.08 executed closure differs: {actual!r}")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry": spec.validate(),
        "executed_actual_gates": actual,
        "host_model_and_decoder": audit_python_model_and_decoder(),
        "fixed_image_changed": False,
        "module_plan_changed": False,
        "carrier_changed": False,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
