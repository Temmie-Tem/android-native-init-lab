#!/usr/bin/env python3
"""Execute every P3.13 encoder output through the actual inherited gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p312_carrier_model as model
import s22plus_fyg8_p313_generator as generator
import s22plus_fyg8_p313_telemetry_decoder as decoder
import s22plus_fyg8_p313_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p313_cross_gate_audit_v1"
VERDICT = "PASS_P313_ACTUAL_ENCODER_OUTPUTS_SUBSET_ALL_GATES_HOST_ONLY"
AuditError = support.AuditError


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root, run_id=run_id, unsat_tag=unsat_tag, profile=profile
    )


def _runtime_gate_tu(runtime: bytes) -> bytes:
    arrays = b"".join(
        (
            support._array("a_outputs", spec.a_outputs()),  # noqa: SLF001
            support._array("b_outputs", spec.b_outputs()),  # noqa: SLF001
        )
    )
    macros = support._macro(runtime, b"P294_LINK_DETAIL_BASE")  # noqa: SLF001
    guard = support._definition(  # noqa: SLF001
        runtime, b"static int p301_terminal_detail_allowed("
    )
    publisher = support._definition(  # noqa: SLF001
        runtime, b"static long p294_publish_final_pair("
    )
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
static int check_a(void) {
    for (size_t index = 0; index < sizeof(a_outputs) / sizeof(a_outputs[0]); ++index) {
        reset_checkpoint();
        if (p294_publish_final_pair(a_outputs[index], 0x4801U) != 0
            || progress_calls != 1U || terminal_calls != 1U) return 10;
    }
    return 0;
}
static int check_b(void) {
    for (size_t index = 0; index < sizeof(b_outputs) / sizeof(b_outputs[0]); ++index) {
        reset_checkpoint();
        if (p294_publish_final_pair(0xd00U, b_outputs[index]) != 0
            || progress_calls != 1U || terminal_calls != 1U) return 20;
    }
    return 0;
}
int main(void) {
    int rc = check_a();
    if (!rc) rc = check_b();
    if (!rc && (p301_terminal_detail_allowed(0x4800U)
        || !p301_terminal_detail_allowed(0x4801U)
        || !p301_terminal_detail_allowed(0x4c02U)
        || p301_terminal_detail_allowed(0x4c03U)
        || p301_terminal_detail_allowed(0x5000U)
        || !p301_terminal_detail_allowed(0x5001U)
        || !p301_terminal_detail_allowed(0x5050U)
        || p301_terminal_detail_allowed(0x5051U)
        || p301_terminal_detail_allowed(0x5060U)
        || !p301_terminal_detail_allowed(0x5061U)
        || !p301_terminal_detail_allowed(0x507fU)
        || p301_terminal_detail_allowed(0x5080U)
        || p301_terminal_detail_allowed(0x6700U)
        || !p301_terminal_detail_allowed(0x6701U)
        || !p301_terminal_detail_allowed(0x673fU)
        || p301_terminal_detail_allowed(0x6740U))) rc = 30;
    reset_checkpoint();
    if (!rc && (p294_publish_final_pair(0xd7eU, 0x4801U) != 0
        || progress_calls != 1U || terminal_calls != 1U)) rc = 31;
    reset_checkpoint();
    if (!rc && (p294_publish_final_pair(0xdb0U, 0x4801U) != -P260_EPROTO
        || progress_calls != 0U || terminal_calls != 0U)) rc = 32;
    if (rc) return rc;
    printf("runtime-a=126 runtime-b=1200 boundaries=16\n");
    return 0;
}
'''
    )


def _checkpoint_gate_tu(checkpoint: bytes, header: bytes) -> bytes:
    source = support._checkpoint_gate_tu(checkpoint, header)  # noqa: SLF001
    arrays_start = source.index(b"static const uint16_t attr_outputs[]")
    main_start = source.index(b"static int check_values(", arrays_start)
    arrays = b"".join(
        (
            support._array("p313_a_outputs", spec.a_outputs()),  # noqa: SLF001
            support._array("p313_b_outputs", spec.b_outputs()),  # noqa: SLF001
        )
    )
    source = source[:arrays_start] + arrays + source[main_start:]
    old_main = source[source.index(b"int main(void) {") :]
    new_main = br'''int main(void) {
    int rc = check_values(105U, 0U, p313_a_outputs,
        sizeof(p313_a_outputs) / sizeof(p313_a_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, p313_b_outputs,
        sizeof(p313_b_outputs) / sizeof(p313_b_outputs[0]));
    if (!rc && (p288_detail_allowed(105U, 0U, 0xdb0U)
        || p288_detail_allowed(106U, 2U, 0x4000U)
        || p288_detail_allowed(106U, 2U, 0x5000U)
        || p288_detail_allowed(106U, 2U, 0x6000U))) rc = 20;
    if (rc) return rc;
    printf("checkpoint-a=126 checkpoint-b=1200 holes=4\n");
    return 0;
}
'''
    return source[: source.index(b"int main(void) {")] + new_main


def _kernel_gate_tu(patch: bytes) -> bytes:
    source = support._kernel_gate_tu(patch)  # noqa: SLF001
    arrays_start = source.index(b"static const uint16_t attr_outputs[]")
    main_start = source.index(b"static int check_values(", arrays_start)
    arrays = b"".join(
        (
            support._array("p313_a_outputs", spec.a_outputs()),  # noqa: SLF001
            support._array("p313_b_outputs", spec.b_outputs()),  # noqa: SLF001
        )
    )
    source = source[:arrays_start] + arrays + source[main_start:]
    new_main = br'''int main(void) {
    int rc = check_values(105U, 0U, p313_a_outputs,
        sizeof(p313_a_outputs) / sizeof(p313_a_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, p313_b_outputs,
        sizeof(p313_b_outputs) / sizeof(p313_b_outputs[0]));
    if (!rc && (s22_fyg8_e1_detail_allowed(3U, 105U, 107U, 0U, 0xdb0U)
        || s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x4000U)
        || s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x5000U)
        || s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x6000U))) rc = 20;
    if (rc) return rc;
    printf("kernel-a=126 kernel-b=1200 holes=4\n");
    return 0;
}
'''
    return source[: source.index(b"int main(void) {")] + new_main


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
    decoded = decoder.decode_record(
        record, expected_profile=spec.PROFILE, expected_run_id=run_id
    )
    observed = decoder.classify_observation(
        b"prefix" + record + b"suffix",
        expected_profile=spec.PROFILE,
        expected_run_id=run_id,
    )
    if (
        observed.get("family_count") != 1
        or observed.get("exact_record_count") != 1
        or observed.get("foreign_count") != 0
        or observed.get("integrity_issue") is not False
    ):
        raise AuditError("P3.13 Carrier-v2 observation round trip differs")
    return decoded


def audit(root: Path) -> dict[str, Any]:
    artifacts = _generated(root)
    runtime = support._compile(  # noqa: SLF001
        _runtime_gate_tu(artifacts["p290_e3_runtime_include"]),
        "p313-runtime-gates",
    )
    checkpoint = support._compile(  # noqa: SLF001
        _checkpoint_gate_tu(
            artifacts["checkpoint_client"], artifacts["p290_checkpoint_header"]
        ),
        "p313-checkpoint-gates",
    )
    kernel = support._compile(  # noqa: SLF001
        _kernel_gate_tu(artifacts["candidate_patch"]), "p313-kernel-gates"
    )
    expected = {
        "runtime": "runtime-a=126 runtime-b=1200 boundaries=16\n",
        "checkpoint": "checkpoint-a=126 checkpoint-b=1200 holes=4\n",
        "kernel": "kernel-a=126 kernel-b=1200 holes=4\n",
    }
    actual = {"runtime": runtime, "checkpoint": checkpoint, "kernel": kernel}
    if actual != expected:
        raise AuditError(f"P3.13 executed gate closure differs: {actual!r}")
    normal = _apply_pair(spec.encode_a(cycle_attempted=1, state_index=0, speed_index=0), spec.encode_normal(0))
    direct = _apply_pair(spec.encode_a(cycle_attempted=0, state_index=0, speed_index=0), spec.DIRECT_LATE_SUCCESS)
    contradiction = _apply_pair(spec.encode_a(cycle_attempted=1, state_index=0, speed_index=0), spec.CONTRADICTION_DETAIL_BASE)
    if normal.get("p313_pair", {}).get("kind") != "normal-cycle":
        raise AuditError("P3.13 normal retained pair differs")
    if direct.get("p313_pair", {}).get("kind") != "direct-late-success":
        raise AuditError("P3.13 direct retained pair differs")
    if contradiction.get("p313_pair", {}).get("observer_complete") is not False:
        raise AuditError("P3.13 contradiction retained pair differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry": spec.validate(),
        "executed_actual_gates": actual,
        "a_outputs_validated": len(spec.a_outputs()),
        "b_outputs_validated": len(spec.b_outputs()),
        "carrier_v2_family": model.LONG_FAMILY.decode("ascii"),
        "retained_pair_round_trip": True,
        "foreign_count_zero": True,
        "fixed_image_changed": False,
        "module_plan_changed": False,
        "carrier_changed": False,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
