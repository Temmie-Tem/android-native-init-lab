#!/usr/bin/env python3
"""P2.54 decoder identity over unchanged P2.52 record semantics."""

from __future__ import annotations

import hashlib

import s22plus_fyg8_p252_e1_decoder as p252


SCHEMA = "s22plus_fyg8_p254_e2_decoder_v1"
DECODER_ID = "s22plus_fyg8_p254_e2_proof_bound_v1"
PROFILE = p252.PROFILE
STAGE_SEQUENCE = p252.STAGE_SEQUENCE
TERMINAL_STAGE = p252.TERMINAL_STAGE
POLICY_PREIMAGE = (
    "S22PLUS_FYG8_P254_E2_DECODER_V1|"
    f"semantics={p252.POLICY_ID}|"
    "proof=cfg-linked-validator-and-isolated-stock-closure|"
    "result=bounded-settled-snapshot-pointer-not-permanent-root-cause"
)
POLICY_SHA256 = hashlib.sha256(POLICY_PREIMAGE.encode("ascii")).hexdigest()
POLICY_ID = POLICY_SHA256[:32]

model = p252.model
DecodeError = p252.DecodeError
encode_slot = p252.encode_slot
decode_record = p252.decode_record
classify_clean_baseline = p252.classify_clean_baseline
classify_observation = p252.classify_observation
