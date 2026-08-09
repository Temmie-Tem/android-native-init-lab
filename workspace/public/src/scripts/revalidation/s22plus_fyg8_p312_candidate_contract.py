#!/usr/bin/env python3
"""Verify P3.12 against its exact fixed P3.10 parent."""

from pathlib import Path

import s22plus_fyg8_p310_candidate_contract as parent
import s22plus_fyg8_p310_candidate_intent as intent
import s22plus_fyg8_p312_overlay_contract as overlay


SCHEMA = overlay.SCHEMA
VERDICT = overlay.CONTRACT_VERDICT
TARGET = overlay.TARGET
DEFAULT_SOURCE = overlay.PARENT_SOURCE
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_PATCH = overlay.PARENT_PATCH
ContractError = overlay.OverlayContractError
stable_read = parent.stable_read


def _configure() -> None:
    parent._configure()  # noqa: SLF001


def verify(root: Path, source: Path, intent_path: Path, patch_path: Path):
    _configure()
    if source != root / overlay.PARENT_SOURCE:
        raise ContractError("P3.12 parent source path differs")
    if patch_path != root / overlay.PARENT_PATCH:
        raise ContractError("P3.12 parent patch path differs")
    return overlay.verify_intent(root, intent_path)


def __getattr__(name: str):
    _configure()
    return getattr(parent, name)
