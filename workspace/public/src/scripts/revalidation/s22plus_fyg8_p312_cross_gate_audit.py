#!/usr/bin/env python3
"""Execute every P3.12 output against runtime, checkpoint, kernel, and Carrier-v2 gates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import s22plus_fyg8_p308_cross_gate_audit as inherited
import s22plus_fyg8_p308_telemetry_spec as p308
import s22plus_fyg8_p312_carrier_model as model
import s22plus_fyg8_p312_generator as generator
import s22plus_fyg8_p312_telemetry_decoder as decoder
import s22plus_fyg8_p312_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p312_cross_gate_audit_v1"
VERDICT = "PASS_P312_ACTUAL_ENCODER_OUTPUTS_SUBSET_ALL_GATES_HOST_ONLY"
AuditError = inherited.AuditError


def _generated(root: Path) -> dict[str, bytes]:
    run_id, unsat_tag, profile = generator.frozen_identity(root)
    return generator.generate_bytes(
        root,
        run_id=run_id,
        unsat_tag=unsat_tag,
        profile=profile,
    )


def _contradiction_array() -> bytes:
    return inherited._array("p312_contradictions", sorted(spec.CONTRADICTION_DETAIL_NAMES))  # noqa: SLF001


def _checkpoint_contradiction_tu(checkpoint: bytes, header: bytes) -> bytes:
    source = inherited._checkpoint_gate_tu(checkpoint, header)  # noqa: SLF001
    source = source.replace(b"int main(void) {", _contradiction_array() + b"int main(void) {", 1)
    needle = b"    if (rc) return rc;\n"
    addition = (
        b"    for (size_t ordinal = 0; !rc && ordinal <= 106U; ++ordinal) {\n"
        b"        for (size_t index = 0; index < sizeof(p312_contradictions) / sizeof(p312_contradictions[0]); ++index) {\n"
        b"            if (!p288_detail_allowed(ordinal, 2U, p312_contradictions[index])) rc = 40;\n"
        b"        }\n"
        b"    }\n" + needle
    )
    if source.count(needle) != 1:
        raise AuditError("P3.12 checkpoint gate insertion anchor differs")
    return source.replace(needle, addition, 1)


def _kernel_contradiction_tu(patch: bytes) -> bytes:
    source = inherited._kernel_gate_tu(patch)  # noqa: SLF001
    source = source.replace(b"int main(void) {", _contradiction_array() + b"int main(void) {", 1)
    needle = b"    if (rc) return rc;\n"
    addition = (
        b"    for (size_t ordinal = 0; !rc && ordinal <= 106U; ++ordinal) {\n"
        b"        for (size_t index = 0; index < sizeof(p312_contradictions) / sizeof(p312_contradictions[0]); ++index) {\n"
        b"            if (!s22_fyg8_e1_detail_allowed(3U, ordinal, 107U, 2U, p312_contradictions[index])) rc = 40;\n"
        b"        }\n"
        b"    }\n" + needle
    )
    if source.count(needle) != 1:
        raise AuditError("P3.12 kernel gate insertion anchor differs")
    return source.replace(needle, addition, 1)


def _apply_pair(first: int, terminal: int) -> dict[str, Any]:
    run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
    record = model.initialize_record(spec.PROFILE, run_id)
    for generation, position in enumerate(p308.POSITIONS, 1):
        if generation == spec.ATTR_ORDINAL + 1:
            outcome, detail = model.OUTCOME_PROGRESS, first
        elif generation == spec.SUMMARY_ORDINAL + 1:
            outcome, detail = model.OUTCOME_FAILURE, terminal
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
        raise AuditError("P3.12 Carrier-v2 observation round trip differs")
    return decoded


def audit(root: Path) -> dict[str, Any]:
    inherited_result = inherited.audit(root)
    artifacts = _generated(root)
    first = set(spec.first_outputs())
    summary = set(spec.summary_outputs())
    if not first <= set(p308.clock_outputs()):
        raise AuditError("P3.12 A outputs exceed executed inherited A gate set")
    if not summary <= set(p308.summary_outputs()):
        raise AuditError("P3.12 B outputs exceed executed inherited B gate set")
    checkpoint = inherited._compile(  # noqa: SLF001
        _checkpoint_contradiction_tu(
            artifacts["checkpoint_client"], artifacts["p290_checkpoint_header"]
        ),
        "p312-checkpoint-contradictions",
    )
    kernel = inherited._compile(  # noqa: SLF001
        _kernel_contradiction_tu(artifacts["candidate_patch"]),
        "p312-kernel-contradictions",
    )
    if checkpoint != "checkpoint-a=313 checkpoint-b=5675 holes=4\n":
        raise AuditError("P3.12 checkpoint executed gate differs")
    if kernel != "kernel-a=313 kernel-b=5675 holes=4\n":
        raise AuditError("P3.12 kernel executed gate differs")
    pair = _apply_pair(spec.FIRST_DETAIL_NO_CLOCK_PATH, spec.SUMMARY_DETAIL_BASE)
    if pair.get("p312_pair", {}).get("kind") != "normal":
        raise AuditError("P3.12 retained pair round trip differs")
    if model.validate().get("verified") is not True:
        raise AuditError("P3.12 Carrier-v2 model validation differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "telemetry": spec.validate(),
        "inherited_executed_gate_closure": inherited_result,
        "first_outputs_subset_executed_a_gate": len(first),
        "summary_outputs_subset_executed_b_gate": len(summary),
        "contradiction_outputs_checkpoint_and_kernel": len(spec.CONTRADICTION_DETAIL_NAMES),
        "contradiction_ordinals_checked": 107,
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
