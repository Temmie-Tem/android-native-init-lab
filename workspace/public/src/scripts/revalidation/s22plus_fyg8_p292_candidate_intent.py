#!/usr/bin/env python3
"""Create one P2.92 candidate intent through the versioned contract."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import s22plus_fyg8_p286_candidate_intent as base
import s22plus_fyg8_p292_source_contract as p292


SCHEMA = p292.INTENT_SCHEMA
PREIMAGE_SCHEMA = p292.PREIMAGE_SCHEMA
VERDICT = p292.INTENT_VERDICT
RUN_ID_DOMAIN = p292.RUN_ID_DOMAIN
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p292/intent")
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
    base.p286.CONTRACT_ID: p292.CONTRACT_ID,
    base.source_contracts.p288.CONTRACT_ID: p292.CONTRACT_ID,
    base.source_contracts.p290.CONTRACT_ID: p292.CONTRACT_ID,
}


def build_patch(
    base_patch: bytes,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str = PROFILE,
) -> bytes:
    if profile != p292.PROFILE:
        raise IntentError(f"unsupported P2.92 candidate profile: {profile}")
    replacements = (
        (
            (
                "+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="
                f'"{p292.SOURCE_CHECK_RUN_ID.hex()}"'
            ).encode("ascii"),
            (
                "+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="
                f'"{run_id.hex()}"'
            ).encode("ascii"),
        ),
        (
            (
                "+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="
                f'"{p292.SOURCE_CHECK_UNSAT_TAG.hex()}"'
            ).encode("ascii"),
            (
                "+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="
                f'"{unsat_tag.hex()}"'
            ).encode("ascii"),
        ),
    )
    value = base_patch
    for old, new in replacements:
        if value.count(old) != 1 or old == new:
            raise IntentError(
                "P2.92 candidate config source binding differs"
            )
        value = value.replace(old, new)
    return value


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
        "build_patch": build_patch,
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
