#!/usr/bin/env python3
"""Host-only closure for the P3.01 subtype and ordinal refinement."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p300_telemetry_closure as inherited
import s22plus_fyg8_p300_telemetry_generator as p300_generator
import s22plus_fyg8_p301_telemetry_generator as generator
import s22plus_fyg8_p301_telemetry_model as model
import s22plus_fyg8_p301_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p301_telemetry_closure_v1"
VERDICT = "PASS_P301_DEVICE_EVENT_SUBTYPE_TELEMETRY_CLOSURE_HOST_ONLY"
SOURCE_CHECK_RUN_ID = hashlib.sha256(
    b"S22PLUS-FYG8-P301-SOURCE-CHECK-V1"
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


def _subtype_ordinal_tu(runtime: bytes) -> bytes:
    structures = b"".join(
        inherited.inherited._struct(runtime, marker)  # noqa: SLF001
        for marker in (
            b"struct p282_trace_record {\n",
            b"struct p282_bind_trace_result {\n",
            b"struct p300_stream_state {\n",
        )
    )
    functions = b"".join(
        inherited.inherited._definition(runtime, marker)  # noqa: SLF001
        for marker in (
            b"static long p300_observe_pointer(\n",
            b"static long p300_consume_event(\n",
            b"static unsigned int p301_count_bucket(",
            b"static int p301_terminal_detail_allowed(",
            b"static long p301_terminal_detail(\n",
            b"static long p294_publish_final_pair(\n",
        )
    )
    expected_final_define = (
        f"#define P301_EXPECTED_FINAL_DETAIL "
        f"0x{spec.EXPECTED_FINAL_STATE_DETAIL:x}U\n"
    ).encode("ascii")
    return (
        br'''
#include <limits.h>
#include <stdint.h>
#include <stdio.h>

#define P260_EPROTO 71
#define P282_CYCLE_EVENT_COUNT 16U
#define P282_BIND_EVENT_COUNT 15U
#define P300_PREFIX_RECORD_CAPACITY 16U
#define P300_DETAIL_TRIGGER_STATE_CONTRADICTION 0xf74U
#define P300_DETAIL_TRACE_STREAM_LINE_MALFORMED 0xf76U
#define P300_DETAIL_FOREIGN_POINTER_CONTRADICTION 0xf79U
#define P300_DETAIL_IRQ_PAIRING_CONTRADICTION 0xf7aU
#define P300_DETAIL_IRQ_RETURN_CONTRADICTION 0xf7bU
#define P300_DETAIL_THREAD_SNAPSHOT_CONTRADICTION 0xf7cU
#define P300_DETAIL_RAW_EVENT_CONTRADICTION 0xf7dU
#define P294_LINK_DETAIL_BASE 0xd00U
#define P294_FINAL_DETAIL_BASE 0xe00U
#define P294_MISMATCH_DETAIL_BASE 0xf80U
#define P294_STATE_SPEED_CONTRADICTION 0xf8fU
#define P294_CONNECT_SPEED_CONTRADICTION 0xf90U
#define P301_SUBTYPE_DETAIL_BASE 0x4001U
#define P301_SUBTYPE_DETAIL_MAX 0x4fc0U
#define P301_UNKNOWN_SUBTYPE_DETAIL 0x4fc1U
#define P301_FINAL_DRIFT_DETAIL_BASE 0x5001U
#define P301_FINAL_DRIFT_DETAIL_MAX 0x5084U
#define P301_DETAIL_SUBTYPE_EMPTY_MASK 0x6001U
#define P301_DETAIL_SUBTYPE_EMPTY_COUNT 0x6002U
#define P301_DETAIL_SUBTYPE_INFO_MISSING 0x6003U
#define P301_DETAIL_SUBTYPE_MASK_RANGE 0x6004U
#define P301_DETAIL_FINAL_MISMATCH_BASE 0x6005U
#define P301_DETAIL_STATE_SPEED_CONTRADICTION 0x600cU
#define P301_DETAIL_CONNECT_SPEED_CONTRADICTION 0x600dU
#define P301_DETAIL_TERMINAL_DOMAIN_CONTRADICTION 0x600eU
#define P301_DETAIL_CHECKPOINT_ORDINAL_CONTRADICTION 0x600fU
'''
        + expected_final_define
        + br'''
#define P301_KNOWN_OTHER_MASK_MAX 0x3fU
#define S22_P294_POSITION_USBLNKST 105U
#define S22_P294_POSITION_FINAL_STATE 106U

struct checkpoint_fixture {
    uint8_t generation;
    uint8_t terminal;
};
static struct checkpoint_fixture g_checkpoint;
static unsigned int progress_calls;
static unsigned int terminal_calls;
static uint16_t progress_detail;
static uint16_t terminal_detail_seen;

static long s22_p294_checkpoint_progress_position(
    struct checkpoint_fixture *client,
    uint8_t ordinal,
    uint16_t detail) {
    ++progress_calls;
    if (client->generation != ordinal || client->terminal) return -P260_EPROTO;
    progress_detail = detail;
    ++client->generation;
    return 0;
}

static long s22_p294_checkpoint_terminal_position(
    struct checkpoint_fixture *client,
    uint8_t ordinal,
    uint16_t detail) {
    ++terminal_calls;
    if (client->generation != ordinal || client->terminal) return -P260_EPROTO;
    terminal_detail_seen = detail;
    ++client->generation;
    client->terminal = 1U;
    return 0;
}
'''
        + structures
        + functions
        + br'''
static void reset_checkpoint(unsigned int generation) {
    g_checkpoint = (struct checkpoint_fixture){
        .generation = (uint8_t)generation,
    };
    progress_calls = 0U;
    terminal_calls = 0U;
    progress_detail = 0U;
    terminal_detail_seen = 0U;
}

static long consume_other(
    struct p300_stream_state *state,
    unsigned int type,
    unsigned int info,
    uint64_t counter) {
    struct p282_trace_record record = {
        .counter = counter,
        .pid = 0,
        .event_index = 14U,
        .has_dwc = 1U,
        .has_raw = 1U,
        .has_low = 1U,
        .has_type = 1U,
        .dwc = 1U,
        .raw = 1U | ((uint64_t)type << 8U) | ((uint64_t)info << 16U),
        .low = 1U,
        .type = type,
    };
    state->result->thread_entries = 1U;
    return p300_consume_event(state, &record);
}

static int known_and_unknown_types(void) {
    struct p282_bind_trace_result result = {0};
    struct p300_stream_state state = {.result = &result};
    if (consume_other(&state, 0U, 10U, 1U) != 0) return 10;
    if (result.other_type_mask != 1U
        || result.first_other_info != 10U
        || !result.first_other_info_seen
        || result.other_device_records != 1U
        || result.unknown_subtype_seen) return 11;
    uint16_t detail = 0U;
    if (p301_terminal_detail(
            &result, 7U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
        || detail != 0x4029U) return 12;
    if (consume_other(&state, 11U, 2U, 2U) != 0) return 13;
    if (result.other_type_mask != 0x21U
        || result.first_other_info != 10U
        || result.other_device_records != 2U) return 14;
    if (p301_terminal_detail(
            &result, 7U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
        || detail != (uint16_t)(0x4001U + ((0x20U * 16U + 10U) * 4U) + 1U))
        return 15;

    result = (struct p282_bind_trace_result){0};
    state = (struct p300_stream_state){.result = &result};
    if (consume_other(&state, 8U, 3U, 1U) != 0
        || !result.unknown_subtype_seen
        || result.other_type_mask != 0U) return 16;
    if (p301_terminal_detail(
            &result, 7U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
        || detail != P301_UNKNOWN_SUBTYPE_DETAIL) return 17;

    result = (struct p282_bind_trace_result){0};
    state = (struct p300_stream_state){.result = &result};
    if (consume_other(&state, 4U, 4U, 1U) != 0
        || consume_other(&state, 12U, 5U, 2U) != 0) return 18;
    if (result.other_type_mask != 2U || !result.unknown_subtype_seen) return 19;
    if (p301_terminal_detail(
            &result, 7U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
        || detail != P301_UNKNOWN_SUBTYPE_DETAIL) return 20;
    return 0;
}

static int buckets_drift_and_guard(void) {
    const uint64_t counts[] = {1U, 2U, 4U, 8U};
    for (unsigned int bucket = 0U; bucket < 4U; ++bucket) {
        struct p282_bind_trace_result result = {
            .other_type_mask = 1U,
            .first_other_info = 0U,
            .first_other_info_seen = 1U,
            .other_device_records = counts[bucket],
        };
        uint16_t detail = 0U;
        if (p301_terminal_detail(
                &result, 7U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
            || detail != (uint16_t)(0x4001U + bucket)) return 30 + bucket;
    }
    struct p282_bind_trace_result zero_mask = {
        .first_other_info_seen = 1U,
        .other_device_records = 1U,
    };
    uint16_t detail = 0U;
    if (p301_terminal_detail(
            &zero_mask, 7U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
        || detail != P301_DETAIL_SUBTYPE_EMPTY_MASK) return 35;
    if (p301_terminal_detail(
            &zero_mask, 7U, P301_EXPECTED_FINAL_DETAIL + 1U, &detail) != 0
        || detail != 0x5004U) return 36;
    if (p301_terminal_detail(
            &zero_mask, 0U, P301_EXPECTED_FINAL_DETAIL, &detail) != 0
        || detail != 0x5003U) return 37;
    if (p301_terminal_detail(&zero_mask, 7U, 0xf80U, &detail) != 0
        || detail != 0x6005U) return 38;
    return 0;
}

static int ordinal_contract(void) {
    reset_checkpoint(105U);
    if (p294_publish_final_pair(0xd70U, 0x4fc1U) != 0) return 50;
    if (g_checkpoint.generation != 107U || !g_checkpoint.terminal
        || progress_calls != 1U || terminal_calls != 1U
        || progress_detail != 0xd70U || terminal_detail_seen != 0x4fc1U)
        return 51;
    reset_checkpoint(104U);
    if (p294_publish_final_pair(0xd70U, 0x4fc1U) != -P260_EPROTO
        || progress_calls != 0U || terminal_calls != 0U) return 52;
    reset_checkpoint(106U);
    if (p294_publish_final_pair(0xd70U, 0x4fc1U) != -P260_EPROTO
        || progress_calls != 0U || terminal_calls != 0U) return 53;
    reset_checkpoint(105U);
    if (p294_publish_final_pair(0xcffU, 0x4fc1U) != -P260_EPROTO
        || progress_calls != 0U) return 54;
    reset_checkpoint(105U);
    if (p294_publish_final_pair(0xd70U, 0x4fc2U) != -P260_EPROTO
        || progress_calls != 1U || terminal_calls != 0U
        || g_checkpoint.generation != 106U || g_checkpoint.terminal) return 55;
    return 0;
}

int main(void) {
    int rc = known_and_unknown_types();
    if (rc == 0) rc = buckets_drift_and_guard();
    if (rc == 0) rc = ordinal_contract();
    if (rc != 0) return rc;
    printf("known=6 unknown=2 mixed=1 buckets=4 mask-zero=guarded ordinal=105-106\n");
    return 0;
}
'''
    )


def audit_subtype_and_ordinal(runtime: bytes) -> dict[str, Any]:
    expected = (
        "known=6 unknown=2 mixed=1 buckets=4 mask-zero=guarded "
        "ordinal=105-106\n"
    )
    actual = inherited._compile_and_run(  # noqa: SLF001
        _subtype_ordinal_tu(runtime), "p301-subtype-ordinal"
    )
    if actual != expected:
        raise ClosureError(f"P3.01 subtype/ordinal execution differs: {actual!r}")
    return {
        "known_event_type_mapping_executed": True,
        "unknown_type_8_executed": True,
        "unknown_type_12_executed": True,
        "known_unknown_mix_fails_closed": True,
        "count_buckets_executed": 4,
        "mask_zero_guard_before_subtraction": True,
        "a_ordinal_105_progress_executed": True,
        "b_ordinal_106_failure_detail_executed": True,
        "wrong_generation_104_rejected": True,
        "wrong_generation_106_rejected": True,
        "verified": True,
    }


def audit_fixed_image_delta(
    root: Path, artifacts: dict[str, bytes]
) -> dict[str, Any]:
    baseline = p300_generator.generate_bytes(
        root,
        run_id=SOURCE_CHECK_RUN_ID,
        unsat_tag=SOURCE_CHECK_UNSAT_TAG,
        profile=spec.PROFILE,
    )
    changed = {key for key in artifacts if artifacts[key] != baseline[key]}
    if changed != generator.P300_DELTA_KEYS:
        raise ClosureError(f"P3.01 fixed-Image delta differs: {sorted(changed)}")
    return {
        "changed_keys": sorted(changed),
        "candidate_patch": _receipt(artifacts["candidate_patch"]),
        "checkpoint_client": _receipt(artifacts["checkpoint_client"]),
        "trace_descriptor_header": _receipt(
            artifacts["trace_descriptor_header"]
        ),
        "kernel_rebuild_required": False,
        "full_lto_ab_required": False,
        "verified": True,
    }


def run_closure(root: Path) -> dict[str, Any]:
    artifacts = _generated(root)
    runtime = artifacts["p290_e3_runtime_include"]
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry_sot": spec.validate(),
        "fixed_image_delta": audit_fixed_image_delta(root, artifacts),
        "subtype_ordinal": audit_subtype_and_ordinal(runtime),
        "inherited_runtime_ingress": inherited.audit_runtime_classification(
            runtime
        ),
        "inherited_stream_parser": inherited.audit_stream_parser(runtime),
        "inherited_delivery_lifecycle": inherited.audit_delivery_and_lifecycle(
            artifacts
        ),
        "inherited_executable_lifecycle": inherited.audit_executable_lifecycle(
            runtime
        ),
        "integrated_build": inherited.audit_patch_and_userspace(root, artifacts),
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
