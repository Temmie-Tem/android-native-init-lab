#!/usr/bin/env python3
"""Verify P3.04 against the exact P3.03 parent and fixed P3.00 Image."""

from pathlib import Path

import s22plus_fyg8_p300_candidate_contract as parent
import s22plus_fyg8_p300_candidate_intent as intent
import s22plus_fyg8_p304_overlay_contract as overlay


SCHEMA = overlay.SCHEMA
VERDICT = overlay.CONTRACT_VERDICT
TARGET = overlay.TARGET
DEFAULT_SOURCE = overlay.PARENT_SOURCE
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_PATCH = overlay.PARENT_PATCH
ContractError = overlay.OverlayContractError
stable_read = parent.stable_read


def verify(root: Path, source: Path, intent_path: Path, patch_path: Path):
    if source != root / overlay.PARENT_SOURCE:
        raise ContractError("P3.04 parent source path differs")
    if patch_path != root / overlay.PARENT_PATCH:
        raise ContractError("P3.04 parent patch path differs")
    return overlay.verify_intent(root, intent_path)


def __getattr__(name: str):
    return getattr(parent, name)
