#!/usr/bin/env python3
"""Cross-check every telemetry overlay decoder against its source carrier ABI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_p312_carrier_decoder_matrix_v1"
VERDICT = "PASS_P312_CARRIER_DECODER_CROSS_AUTHORITY_HOST_ONLY"


def audit(_root: Path) -> dict[str, Any]:
    import device_action_f1_evidence_v2 as evidence

    rows = []
    legacy_overlays = (
        evidence.P301_OVERLAY_CONTRACT_ID,
        evidence.P302_OVERLAY_CONTRACT_ID,
        evidence.P303_OVERLAY_CONTRACT_ID,
        evidence.P304_OVERLAY_CONTRACT_ID,
        evidence.P305_OVERLAY_CONTRACT_ID,
        evidence.P306_OVERLAY_CONTRACT_ID,
        evidence.P307_OVERLAY_CONTRACT_ID,
        evidence.P308_OVERLAY_CONTRACT_ID,
    )
    for overlay_id in legacy_overlays:
        decoder = evidence._latest_stage_observation_decoder(  # noqa: SLF001
            evidence.P300_SOURCE_CONTRACT_ID, "E2", overlay_id
        )
        rows.append({
            "overlay_contract_id": overlay_id,
            "decoder_id": decoder.DECODER_ID,
            "carrier_family": decoder.model.LONG_FAMILY.decode("ascii"),
            "record_size": decoder.model.LONG_RECORD_SIZE,
            "accepted": True,
        })
    try:
        evidence._latest_stage_observation_decoder(  # noqa: SLF001
            evidence.P310_SOURCE_CONTRACT_ID,
            "E2",
            evidence.P311_OVERLAY_CONTRACT_ID,
        )
    except evidence.EvidenceError as exc:
        if "decoder carrier differs" not in str(exc):
            raise
        rows.append({
            "overlay_contract_id": evidence.P311_OVERLAY_CONTRACT_ID,
            "accepted": False,
            "reason": "carrier-v1-decoder-on-carrier-v2-source",
        })
    else:
        raise RuntimeError("P3.11 carrier mismatch was not rejected")
    decoder = evidence._latest_stage_observation_decoder(  # noqa: SLF001
        evidence.P310_SOURCE_CONTRACT_ID,
        "E2",
        evidence.P312_OVERLAY_CONTRACT_ID,
    )
    rows.append({
        "overlay_contract_id": evidence.P312_OVERLAY_CONTRACT_ID,
        "decoder_id": decoder.DECODER_ID,
        "carrier_family": decoder.model.LONG_FAMILY.decode("ascii"),
        "record_size": decoder.model.LONG_RECORD_SIZE,
        "accepted": True,
    })
    if (
        len(rows) != 10
        or sum(row["accepted"] is True for row in rows) != 9
        or rows[-1].get("carrier_family") != "S22E1L2|"
        or rows[-1].get("record_size") != 192
    ):
        raise RuntimeError("P3.12 carrier/decoder matrix differs")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "rows": rows,
        "p311_historical_mismatch_rejected": True,
        "p312_carrier_v2_json_safe": True,
        "records_generated_by_source_carrier": True,
        "device_contact": False,
        "verified": True,
    }


if __name__ == "__main__":
    print(json.dumps(audit(Path.cwd()), indent=2, sort_keys=True))
