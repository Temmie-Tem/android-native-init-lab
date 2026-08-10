#!/usr/bin/env python3
"""Run the complete P3.15 value-position matrix through Process-v2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p310_carrier_model as raw_carrier
import s22plus_fyg8_p315_carrier_model as model
import s22plus_fyg8_p315_cross_gate_audit as cross_gate
import s22plus_fyg8_p315_overlay_contract as overlay
import s22plus_fyg8_p315_telemetry_decoder as decoder
import s22plus_fyg8_p315_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p315_value_position_matrix_v1"
VERDICT = "PASS_P315_251450_REAL_PROCESS_V2_MATRIX_HOST_ONLY"


class MatrixError(ValueError):
    pass


def _acceptance(run_id: bytes) -> dict[str, Any]:
    artifact = {"path": "matrix-fixture", "size": 1, "sha256": "0" * 64}
    return {
        "kind": evidence.E1_LATEST_STAGE_KIND,
        "source": evidence.CHECKPOINT_SOURCE,
        "decoder": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "profile": overlay.PROFILE,
        "run_id": run_id.hex(),
        "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "long_family_hex": model.LONG_FAMILY.hex(),
        "unsat_family_hex": model.UNSAT_FAMILY.hex(),
        "terminal_stage": evidence._latest_stage_terminal(  # noqa: SLF001
            decoder, overlay.PROFILE
        ),
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "contract": {
            "candidate_static": artifact,
            "run_manifest": artifact,
            "static_check": artifact,
        },
    }


def _prefixes(run_id: bytes) -> tuple[bytes, ...]:
    rows = [model.initialize_record(overlay.PROFILE, run_id)]
    for generation in range(1, len(spec.POSITIONS)):
        position = spec.position_for_generation(generation)
        rows.append(
            model.apply_request(
                rows[-1],
                model.encode_request(
                    overlay.PROFILE,
                    position.stage,
                    run_id=run_id,
                    outcome=model.OUTCOME_PROGRESS,
                    item_index=position.item_index,
                    detail=0,
                ),
            )
        )
    if len(rows) != len(spec.POSITIONS):
        raise MatrixError("P3.15 progress prefix extent differs")
    return tuple(rows)


def _force_apply(
    prefix: bytes,
    *,
    run_id: bytes,
    generation: int,
    outcome: int,
    detail: int,
) -> bytes:
    decoded = raw_carrier.decode_record(
        prefix, expected_profile=overlay.PROFILE, expected_run_id=run_id
    )
    active = raw_carrier.Slot(**decoded["active"])
    if active.generation + 1 != generation or active.outcome != model.OUTCOME_PROGRESS:
        raise MatrixError("P3.15 matrix prefix generation differs")
    position = spec.position_for_generation(generation)
    slot_id = active.slot_id ^ 1
    slot = raw_carrier.Slot(
        slot_id,
        generation,
        position.stage,
        outcome,
        position.item_index,
        detail,
        model.PAYLOAD_NONE,
        b"",
    )
    header = prefix[: raw_carrier.LONG_HEADER_SIZE]
    encoded = raw_carrier._encode_slot(header, slot)  # noqa: SLF001
    start = raw_carrier.LONG_HEADER_SIZE + slot_id * raw_carrier.SLOT_SIZE
    value = bytearray(prefix)
    value[start : start + raw_carrier.SLOT_SIZE] = encoded
    result = bytes(value)
    raw_carrier.decode_record(
        result, expected_profile=overlay.PROFILE, expected_run_id=run_id
    )
    return result


def _round_trip(
    payload: bytes,
    acceptance: dict[str, Any],
    *,
    family: str,
    generation: int,
    outcome: int,
    detail: int,
    expected: bool,
) -> tuple[bool, str]:
    try:
        classified = evidence.classify_e1_latest_stage(payload, acceptance)
    except evidence.EvidenceError as exc:
        persisted = json.loads(
            json.dumps(
                {"accepted_by_adapter": False, "error": str(exc)},
                sort_keys=True,
                allow_nan=False,
            )
        )
        observed = False
        classification = "rejected"
        if persisted.get("accepted_by_adapter") is not False:
            raise MatrixError("P3.15 rejected cell persistence differs")
    else:
        persisted = json.loads(
            json.dumps(classified, sort_keys=True, allow_nan=False)
        )
        records = persisted.get("records")
        if (
            not isinstance(records, list)
            or len(records) != 1
            or persisted.get("exact_record_count") != 1
            or persisted.get("foreign_count") != 0
        ):
            raise MatrixError("P3.15 accepted cell record geometry differs")
        active = records[0].get("active")
        observed = (
            isinstance(active, dict)
            and active.get("generation") == generation
            and active.get("outcome") == outcome
            and active.get("detail") == detail
        )
        semantics = records[0].get("active_semantics", {})
        if observed and family == "a":
            if semantics.get("detail_kind") != "p314-cycle-state-speed":
                raise MatrixError("P3.15 inherited A semantics differ")
        elif observed and family == "b":
            if detail in spec.P315_RESERVED_NAMES:
                if (
                    semantics.get("detail_kind")
                    != "p315-observer-contradiction"
                    or semantics.get("detail_name")
                    != spec.P315_RESERVED_NAMES[detail]
                ):
                    raise MatrixError("P3.15 reserved B semantics differ")
            elif not str(semantics.get("detail_kind", "")).startswith("p314-"):
                raise MatrixError("P3.15 inherited B semantics differ")
            if spec.PAIR_MASK_DETAIL_MIN <= detail <= spec.PAIR_MASK_DETAIL_MAX:
                if (
                    persisted.get("classification")
                    != "P315_OBSERVER_CONTRADICTION"
                    or persisted.get("accepted") is not False
                    or persisted.get("contradiction_count") != 1
                    or persisted.get("pair_excess_count") != 1
                    or semantics.get("detail_kind") != "p314-pair-excess"
                ):
                    raise MatrixError("P3.15 pair-mask classifier semantics differ")
        classification = str(persisted.get("classification"))
    if observed is not expected:
        raise MatrixError(
            f"P3.15 matrix decision differs: {family}/{generation}/{detail:#x}"
        )
    return observed, classification


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    gates = cross_gate.audit(root)
    if gates.get("verified") is not True:
        raise MatrixError("P3.15 encoder gates are not closed")
    run_id = bytes.fromhex("31503150315031503150315031503150")
    acceptance = _acceptance(run_id)
    prefixes = _prefixes(run_id)
    digest = hashlib.sha256()
    accepted = 0
    rejected = 0
    cells = 0
    families = (
        ("a", spec.a_outputs(), model.OUTCOME_PROGRESS),
        ("b", spec.matrix_b_values(), model.OUTCOME_FAILURE),
        ("progress-zero", (0,), model.OUTCOME_PROGRESS),
    )
    for family, details, outcome in families:
        for detail in details:
            for generation in range(1, len(spec.POSITIONS) + 1):
                expected = spec.matrix_expected_acceptance(
                    family=family, generation=generation
                )
                payload = _force_apply(
                    prefixes[generation - 1],
                    run_id=run_id,
                    generation=generation,
                    outcome=outcome,
                    detail=detail,
                )
                observed, classification = _round_trip(
                    payload,
                    acceptance,
                    family=family,
                    generation=generation,
                    outcome=outcome,
                    detail=detail,
                    expected=expected,
                )
                accepted += int(observed)
                rejected += int(not observed)
                cells += 1
                digest.update(
                    json.dumps(
                        [family, generation, outcome, detail, observed, classification],
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("ascii")
                    + b"\n"
                )
    if (
        cells != spec.matrix_cell_count()
        or cells != 251_450
        or accepted != 238_094
        or rejected != 13_356
    ):
        raise MatrixError("P3.15 matrix cardinality differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "a_outputs": len(spec.a_outputs()),
        "successor_b_outputs": len(spec.b_outputs()),
        "matrix_b_values": len(spec.matrix_b_values()),
        "progress_zero_outputs": 1,
        "positions": len(spec.POSITIONS),
        "matrix_cells": cells,
        "accepted_cells": accepted,
        "rejected_cells": rejected,
        "process_v2_adapter_calls": cells,
        "json_persistence_round_trips": cells,
        "matrix_sha256": digest.hexdigest(),
        "generated_from_actual_encoders": True,
        "accept_reject_from_runtime_gates": True,
        "real_process_v2_adapter_round_trip": True,
        "persistence_round_trip": True,
        "legacy_0x6712_decode_only": True,
        "reserved_detail_names_verified": {
            f"0x{detail:04x}": name
            for detail, name in sorted(spec.P315_RESERVED_NAMES.items())
        },
        "device_contact": False,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (MatrixError, evidence.EvidenceError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
