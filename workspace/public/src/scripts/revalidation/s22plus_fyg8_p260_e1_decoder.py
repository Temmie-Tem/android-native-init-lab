#!/usr/bin/env python3
"""Decode P2.60 E3 records with exact local-stage semantics."""

from __future__ import annotations

import hashlib
from typing import Any

import s22plus_fyg8_p252_e1_decoder as p252
import s22plus_fyg8_p260_contract_spec as spec


SCHEMA = "s22plus_fyg8_p260_e3_decoder_v1"
DECODER_ID = "s22plus_fyg8_p260_e3_acm_banner_v1"
PROFILE = spec.PROFILE
STAGE_SEQUENCE = spec.STAGE_SEQUENCE
TERMINAL_STAGE = spec.TERMINAL_STAGE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P260_E3_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|"
    "unsat=S22E1U1-24|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-p260-terminal-success|"
    "reject=foreign,malformed,partial,unknown-detail|zero=ambiguous|"
    "detail=001-7ff-errno,800-8ff-regression,900-9ff-read-error,"
    f"classifier={','.join(f'{value:03x}' for value in spec.CLASSIFIER_VALUES)}|"
    f"stages={','.join(f'{stage:02x}' for stage in STAGE_SEQUENCE)}|"
    f"spec={spec.SCHEMA}|model={p252.model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]

model = p252.model
DecodeError = p252.DecodeError


def encode_slot(
    header: bytes,
    *,
    generation: int,
    stage: int,
    outcome: int,
    item_index: int,
    detail: int,
) -> bytes:
    return p252.encode_slot(
        header,
        generation=generation,
        stage=stage,
        outcome=outcome,
        item_index=item_index,
        detail=detail,
        _contract_spec=spec,
    )


def decode_record(
    record: bytes,
    *,
    expected_profile: str = PROFILE,
    expected_run_id: bytes | None = None,
) -> dict[str, Any]:
    return p252.decode_record(
        record,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
        _contract_spec=spec,
    )


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return p252.classify_clean_baseline(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
        _contract_spec=spec,
    )


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    return p252.classify_observation(
        payload,
        expected_profile=expected_profile,
        expected_run_id=expected_run_id,
        _contract_spec=spec,
    )
