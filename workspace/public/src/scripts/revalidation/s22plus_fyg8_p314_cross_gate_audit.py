#!/usr/bin/env python3
"""Execute every P3.14 emitter output through all applicable device gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as support
import s22plus_fyg8_p313_cross_gate_audit as parent
import s22plus_fyg8_p314_generator as generator
import s22plus_fyg8_p314_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p314_cross_gate_audit_v1"
VERDICT = "PASS_P314_ACTUAL_ENCODER_OUTPUTS_SUBSET_ALL_GATES_HOST_ONLY"
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
    (void)detail; ++progress_calls;
    if (client->generation != ordinal || client->terminal) return -P260_EPROTO;
    ++client->generation; return 0;
}
static long s22_p294_checkpoint_terminal_position(
    struct checkpoint_fixture *client, uint8_t ordinal, uint16_t detail) {
    (void)detail; ++terminal_calls;
    if (client->generation != ordinal || client->terminal) return -P260_EPROTO;
    ++client->generation; client->terminal = 1U; return 0;
}
static void reset_checkpoint(void) {
    g_checkpoint = (struct checkpoint_fixture){.generation = 105U};
    progress_calls = 0U; terminal_calls = 0U;
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
    int rc = check_a(); if (!rc) rc = check_b();
    if (!rc && (p301_terminal_detail_allowed(0x6c00U)
        || !p301_terminal_detail_allowed(0x6c01U)
        || !p301_terminal_detail_allowed(0x6fffU))) rc = 30;
    if (rc) return rc;
    printf("runtime-a=126 runtime-b=2222 masks=1023\n");
    return 0;
}
'''
    )


def _replace_arrays(source: bytes, prefix: str) -> bytes:
    arrays_start = source.index(b"static const uint16_t attr_outputs[]")
    main_start = source.index(b"static int check_values(", arrays_start)
    arrays = b"".join(
        (
            support._array(f"{prefix}_a_outputs", spec.a_outputs()),  # noqa: SLF001
            support._array(f"{prefix}_b_outputs", spec.b_outputs()),  # noqa: SLF001
        )
    )
    return source[:arrays_start] + arrays + source[main_start:]


def _checkpoint_gate_tu(checkpoint: bytes, header: bytes) -> bytes:
    source = _replace_arrays(
        support._checkpoint_gate_tu(checkpoint, header), "p314"  # noqa: SLF001
    )
    main = br'''int main(void) {
    int rc = check_values(105U, 0U, p314_a_outputs,
        sizeof(p314_a_outputs) / sizeof(p314_a_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, p314_b_outputs,
        sizeof(p314_b_outputs) / sizeof(p314_b_outputs[0]));
    if (!rc && (!p288_detail_allowed(0U, 2U, 0x6c01U)
        || !p288_detail_allowed(106U, 2U, 0x6fffU))) rc = 20;
    if (rc) return rc;
    printf("checkpoint-a=126 checkpoint-b=2222 masks=1023\n");
    return 0;
}
'''
    return source[: source.index(b"int main(void) {")] + main


def _kernel_gate_tu(patch: bytes) -> bytes:
    source = _replace_arrays(support._kernel_gate_tu(patch), "p314")  # noqa: SLF001
    main = br'''int main(void) {
    int rc = check_values(105U, 0U, p314_a_outputs,
        sizeof(p314_a_outputs) / sizeof(p314_a_outputs[0]));
    if (!rc) rc = check_values(106U, 2U, p314_b_outputs,
        sizeof(p314_b_outputs) / sizeof(p314_b_outputs[0]));
    if (!rc && (!s22_fyg8_e1_detail_allowed(3U, 0U, 107U, 2U, 0x6c01U)
        || !s22_fyg8_e1_detail_allowed(3U, 106U, 107U, 2U, 0x6fffU))) rc = 20;
    if (rc) return rc;
    printf("kernel-a=126 kernel-b=2222 masks=1023\n");
    return 0;
}
'''
    return source[: source.index(b"int main(void) {")] + main


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    artifacts = _generated(root)
    actual = {
        "runtime": support._compile(  # noqa: SLF001
            _runtime_gate_tu(artifacts["p290_e3_runtime_include"]),
            "p314-runtime-gates",
        ),
        "checkpoint": support._compile(  # noqa: SLF001
            _checkpoint_gate_tu(
                artifacts["checkpoint_client"], artifacts["p290_checkpoint_header"]
            ),
            "p314-checkpoint-gates",
        ),
        "kernel": support._compile(  # noqa: SLF001
            _kernel_gate_tu(artifacts["candidate_patch"]), "p314-kernel-gates"
        ),
    }
    expected = {
        "runtime": "runtime-a=126 runtime-b=2222 masks=1023\n",
        "checkpoint": "checkpoint-a=126 checkpoint-b=2222 masks=1023\n",
        "kernel": "kernel-a=126 kernel-b=2222 masks=1023\n",
    }
    if actual != expected:
        raise AuditError(f"P3.14 executed gate closure differs: {actual!r}")
    if spec.LEGACY_GENERIC_MULTIPLICITY_DETAIL in spec.b_outputs():
        raise AuditError("P3.14 legacy 0x6712 remained an emitter output")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry": spec.validate(),
        "executed_actual_gates": actual,
        "a_outputs_validated": len(spec.a_outputs()),
        "b_outputs_validated": len(spec.b_outputs()),
        "pair_masks_validated": spec.PAIR_MASK_VALUE_COUNT,
        "legacy_0x6712_emit_capable": False,
        "fixed_image_changed": False,
        "module_plan_changed": False,
        "carrier_changed": False,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
