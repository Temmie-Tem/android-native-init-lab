#!/usr/bin/env python3
"""Exercise P3.13 Carrier-v2 through the real Process-v2 evidence adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import device_action_f1_evidence_v2 as evidence
import s22plus_fyg8_p312_carrier_model as model
import s22plus_fyg8_p313_overlay_contract as overlay
import s22plus_fyg8_p313_telemetry_decoder as decoder
import s22plus_fyg8_p313_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p313_process_v2_adapter_fixture_v1"
VERDICT = "PASS_P313_PROCESS_V2_CARRIER_V2_ADAPTER_HOST_ONLY"


class FixtureError(ValueError):
    pass


def _record(run_id: bytes) -> bytes:
    record = model.initialize_record(overlay.PROFILE, run_id)
    for generation, position in enumerate(spec.POSITIONS, 1):
        if generation == spec.ATTR_ORDINAL + 1:
            outcome = spec.OUTCOME_PROGRESS
            detail = spec.encode_a(
                cycle_attempted=1,
                state_index=0,
                speed_index=0,
            )
        elif generation == spec.SUMMARY_ORDINAL + 1:
            outcome = spec.OUTCOME_FAILURE
            detail = spec.encode_normal(0)
        else:
            outcome = model.OUTCOME_PROGRESS
            detail = 0
        record = model.apply_request(
            record,
            model.encode_request(
                overlay.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=outcome,
                item_index=position.item_index,
                detail=detail,
            ),
        )
        if generation == spec.SUMMARY_ORDINAL + 1:
            break
    return record


def _acceptance(contract: dict[str, Any]) -> dict[str, Any]:
    artifact = {"path": "fixture", "size": 1, "sha256": "0" * 64}
    return {
        "kind": evidence.E1_LATEST_STAGE_KIND,
        "source": evidence.CHECKPOINT_SOURCE,
        "decoder": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "profile": overlay.PROFILE,
        "run_id": contract["run_id"],
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


def audit(root: Path | None = None) -> dict[str, Any]:
    root = (root or Path(__file__).resolve().parents[5]).resolve()
    contract = overlay.verify_intent(root, root / overlay.DEFAULT_INTENT)
    run_id = bytes.fromhex(contract["run_id"])
    selected = evidence._latest_stage_observation_decoder(  # noqa: SLF001
        overlay.PARENT_SOURCE_CONTRACT_ID,
        overlay.PROFILE,
        overlay.CONTRACT_ID,
    )
    classified = evidence.classify_e1_latest_stage(
        _record(run_id), _acceptance(contract)
    )
    encoded = json.dumps(
        classified,
        sort_keys=True,
        allow_nan=False,
    ).encode("ascii")
    decoded = json.loads(encoded.decode("ascii"))
    pair = decoded.get("records", [{}])[0].get("p313_pair", {})
    if (
        selected is not decoder
        or decoded.get("accepted") is not True
        or decoded.get("telemetry_count") != 1
        or decoded.get("foreign_count") != 0
        or pair.get("kind") != "normal-cycle"
        or pair.get("cycle_attempted") is not True
        or pair.get("observer_complete") is not True
    ):
        raise FixtureError("P3.13 Process-v2 adapter round trip differs")
    changed = _acceptance(contract)
    changed["userspace_overlay_contract_id"] = overlay.CONTRACT_ID + "-unknown"
    try:
        evidence.classify_e1_latest_stage(_record(run_id), changed)
    except evidence.EvidenceError:
        unknown_rejected = True
    else:
        unknown_rejected = False
    if not unknown_rejected:
        raise FixtureError("P3.13 unknown Carrier authority was accepted")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "decoder_id": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "carrier_v2_family": model.LONG_FAMILY.decode("ascii"),
        "json_safe": True,
        "foreign_count_zero": True,
        "unknown_overlay_rejected": True,
        "verified": True,
    }


def main() -> int:
    try:
        result = audit()
    except (FixtureError, evidence.EvidenceError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
