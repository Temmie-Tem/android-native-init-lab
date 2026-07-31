#!/usr/bin/env python3
"""Shared pure marker/fact contracts for the Phase 2D display observer."""

from __future__ import annotations

import sys
from pathlib import Path


REVAL_DIR = Path(__file__).resolve().parents[1] / "revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

from a90_observation_pipeline import (  # noqa: E402,F401
    FactState,
    ObservationContractError,
    classify_phase2_display_facts,
    facts_to_dict,
    parse_exact_marker,
    validate_bounded_failure_marker,
    validate_debian_ready_marker,
    validate_native_release_evidence,
)


ContractError = ObservationContractError
