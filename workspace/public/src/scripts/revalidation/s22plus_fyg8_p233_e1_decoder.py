#!/usr/bin/env python3
"""Decode compact E1A/E1B/E2 records from raw retained bytes."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p232_e1_latest_stage_design as model  # noqa: E402


SCHEMA = "s22plus_fyg8_p233_e1_decoder_v1"
DECODER_ID = "s22plus_fyg8_p233_e1_latest_stage_v1"
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P233_E1_DECODER_V1|"
    "layout=S22E1L1-45-ab-crc32|unsat=S22E1U1-24|"
    "baseline=all-related-families-absent|"
    "accept=one-or-more-profile-terminal-success|"
    "reject=foreign,malformed,partial|zero=ambiguous|"
    f"model={model.SCHEMA}"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]


class DecodeError(ValueError):
    pass


def _validate_identity(profile: str, run_id: bytes) -> None:
    if profile not in model.PROFILE_NUMBERS:
        raise DecodeError(f"unsupported P2.33 E1 profile: {profile}")
    if len(run_id) != model.RUN_ID_SIZE or not any(run_id):
        raise DecodeError("P2.33 run ID must be one nonzero 128-bit value")


def classify_clean_baseline(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    _validate_identity(expected_profile, expected_run_id)
    try:
        model.classify_observation(
            payload,
            b"",
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except model.DesignError as exc:
        return {
            "classification": "BASELINE_RELATED_EVIDENCE_PRESENT",
            "baseline_clean": False,
            "integrity_issue": True,
            "error": str(exc),
        }
    return {
        "classification": "BASELINE_CLEAN",
        "baseline_clean": True,
        "integrity_issue": False,
        "error": None,
    }


def classify_observation(
    payload: bytes, *, expected_profile: str, expected_run_id: bytes
) -> dict[str, Any]:
    _validate_identity(expected_profile, expected_run_id)
    try:
        return model.classify_observation(
            b"",
            payload,
            expected_profile=expected_profile,
            expected_run_id=expected_run_id,
        )
    except model.DesignError as exc:
        raise DecodeError(str(exc)) from exc
