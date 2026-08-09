#!/usr/bin/env python3
"""P3.11 retained-record model over the unchanged Carrier-v2 ABI."""

from __future__ import annotations

import s22plus_fyg8_p308_telemetry_model as base


SCHEMA = "s22plus_fyg8_p311_telemetry_model_v1"

LONG_FAMILY = base.LONG_FAMILY
UNSAT_FAMILY = base.UNSAT_FAMILY
LEGACY_FAMILIES = base.LEGACY_FAMILIES
FORMAT_VERSION = base.FORMAT_VERSION
REQUEST_VERSION = base.REQUEST_VERSION
LONG_RECORD_SIZE = base.LONG_RECORD_SIZE
LONG_HEADER_SIZE = base.LONG_HEADER_SIZE
SLOT_SIZE = base.SLOT_SIZE
SLOT_COUNT = base.SLOT_COUNT
UNSAT_SIZE = base.UNSAT_SIZE
RUN_ID_SIZE = base.RUN_ID_SIZE
OUTCOME_PROGRESS = base.OUTCOME_PROGRESS
OUTCOME_SUCCESS = base.OUTCOME_SUCCESS
OUTCOME_FAILURE = base.OUTCOME_FAILURE
PROFILE_NUMBERS = base.PROFILE_NUMBERS
PROFILE_BY_NUMBER = base.PROFILE_BY_NUMBER
STAGES = base.STAGES
REQUEST_STRUCT = base.REQUEST_STRUCT
SLOT_BODY_STRUCT = base.SLOT_BODY_STRUCT
Request = base.Request
Slot = base.Slot
DesignError = base.DesignError
crc32 = base.crc32
model_run_id = base.model_run_id
unsat_record = base.unsat_record
encode_request = base.encode_request
decode_request = base.decode_request
initialize_record = base.initialize_record
decode_record = base.decode_record
apply_request = base.apply_request
classify_clean_baseline = base.classify_clean_baseline
classify_observation = base.classify_observation
