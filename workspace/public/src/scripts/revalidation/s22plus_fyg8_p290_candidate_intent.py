#!/usr/bin/env python3
"""Create one P2.90 candidate intent through the versioned contract."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import s22plus_fyg8_p286_candidate_intent as base
import s22plus_fyg8_p290_source_contract as p290


SCHEMA = p290.INTENT_SCHEMA
PREIMAGE_SCHEMA = p290.PREIMAGE_SCHEMA
VERDICT = p290.INTENT_VERDICT
RUN_ID_DOMAIN = p290.RUN_ID_DOMAIN
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p290/intent")
TARGET = base.TARGET
PROFILE = base.PROFILE
PROFILE_NUMBER = base.PROFILE_NUMBER
SUPPORTED_PROFILES = base.SUPPORTED_PROFILES
DEFAULT_SOURCE = base.DEFAULT_SOURCE
DEFAULT_BASE_PATCH = base.DEFAULT_BASE_PATCH
DEFCONFIG = base.DEFCONFIG
BASE_FILES = base.BASE_FILES
IntentError = base.IntentError

RUN_ID_DOMAINS = {**base.RUN_ID_DOMAINS, "E2": RUN_ID_DOMAIN}
SUPERSEDED_FOR_NEW_CANDIDATES = {
    **base.SUPERSEDED_FOR_NEW_CANDIDATES,
    base.p286.CONTRACT_ID: p290.CONTRACT_ID,
    base.source_contracts.p288.CONTRACT_ID: p290.CONTRACT_ID,
}


def candidate_contract_ids() -> tuple[str, ...]:
    return tuple(
        contract_id
        for contract_id in base.source_contracts.contract_ids()
        if contract_id not in SUPERSEDED_FOR_NEW_CANDIDATES
    )


def selected_source_contract_for_candidate(
    source_contract_id: str | None,
    profile: str,
):
    replacement = SUPERSEDED_FOR_NEW_CANDIDATES.get(source_contract_id)
    if replacement is not None:
        raise IntentError(
            f"source contract {source_contract_id!r} is superseded for new "
            f"candidates by {replacement!r}"
        )
    try:
        return base.source_contracts.select(source_contract_id, profile)
    except base.source_contracts.SourceContractSelectionError as exc:
        raise IntentError(str(exc)) from exc


@contextmanager
def _base_context() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "PREIMAGE_SCHEMA": PREIMAGE_SCHEMA,
        "VERDICT": VERDICT,
        "RUN_ID_DOMAIN": RUN_ID_DOMAIN,
        "RUN_ID_DOMAINS": RUN_ID_DOMAINS,
        "DEFAULT_OUT": DEFAULT_OUT,
        "SUPERSEDED_FOR_NEW_CANDIDATES": SUPERSEDED_FOR_NEW_CANDIDATES,
        "candidate_contract_ids": candidate_contract_ids,
        "selected_source_contract_for_candidate": (
            selected_source_contract_for_candidate
        ),
    }
    previous = {name: getattr(base, name) for name in replacements}
    for name, value in replacements.items():
        setattr(base, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


def _configure() -> None:
    """Compatibility hook for downstream adapters."""


def __getattr__(name: str):
    return getattr(base, name)


def create(args):  # noqa: ANN001, ANN201
    with _base_context():
        return base.create(args)


def parse_args(argv: list[str] | None = None):
    with _base_context():
        return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    with _base_context():
        return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
