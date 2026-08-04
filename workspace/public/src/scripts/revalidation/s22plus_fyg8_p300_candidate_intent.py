#!/usr/bin/env python3
"""Create one P3.00 candidate intent through the versioned contract."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import s22plus_fyg8_p286_source_contracts as selector
import s22plus_fyg8_p296_candidate_intent as base
import s22plus_fyg8_p298_candidate_intent as inherited
import s22plus_fyg8_p300_source_contract as p300


SCHEMA = p300.INTENT_SCHEMA
PREIMAGE_SCHEMA = p300.PREIMAGE_SCHEMA
VERDICT = p300.INTENT_VERDICT
RUN_ID_DOMAIN = p300.RUN_ID_DOMAIN
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p300/intent")
TARGET = inherited.TARGET
PROFILE = p300.PROFILE
PROFILE_NUMBER = inherited.PROFILE_NUMBER
SUPPORTED_PROFILES = inherited.SUPPORTED_PROFILES
DEFAULT_SOURCE = p300.DRIVER_SOURCE_REFERENCE
DEFAULT_BASE_PATCH = inherited.DEFAULT_BASE_PATCH
DEFCONFIG = inherited.DEFCONFIG
BASE_FILES = dict(inherited.BASE_FILES)
IntentError = inherited.IntentError
_INHERITED_BUILD_PATCH = inherited.build_patch
_INHERITED_CONTRACT_IDS = inherited.candidate_contract_ids
_INHERITED_SELECTION = inherited.selected_source_contract_for_candidate
_SELECTOR_SELECT = inherited._selector_select  # noqa: SLF001
_SELECTOR_CONTRACT_IDS = inherited._selector_contract_ids  # noqa: SLF001
RUN_ID_DOMAINS = {**inherited.RUN_ID_DOMAINS, "E2": RUN_ID_DOMAIN}
SUPERSEDED_FOR_NEW_CANDIDATES = {
    **inherited.SUPERSEDED_FOR_NEW_CANDIDATES,
    inherited.p298.CONTRACT_ID: p300.CONTRACT_ID,
}


def build_patch(
    base_patch: bytes,
    run_id: bytes,
    unsat_tag: bytes,
    profile: str = PROFILE,
) -> bytes:
    if profile != p300.PROFILE:
        raise IntentError(f"unsupported P3.00 candidate profile: {profile}")
    replacements = (
        (
            (
                "+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="
                f'"{p300.SOURCE_CHECK_RUN_ID.hex()}"'
            ).encode("ascii"),
            (
                "+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="
                f'"{run_id.hex()}"'
            ).encode("ascii"),
        ),
        (
            (
                "+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="
                f'"{p300.SOURCE_CHECK_UNSAT_TAG.hex()}"'
            ).encode("ascii"),
            (
                "+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="
                f'"{unsat_tag.hex()}"'
            ).encode("ascii"),
        ),
    )
    counts = tuple(base_patch.count(old) for old, _new in replacements)
    if counts == (0, 0):
        return _INHERITED_BUILD_PATCH(base_patch, run_id, unsat_tag, profile)
    if counts != (1, 1):
        raise IntentError("P3.00 candidate config source binding differs")
    value = base_patch
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def candidate_contract_ids() -> tuple[str, ...]:
    inherited_ids = _INHERITED_CONTRACT_IDS()
    return tuple(
        dict.fromkeys(
            (
                *(
                    contract_id
                    for contract_id in inherited_ids
                    if contract_id not in SUPERSEDED_FOR_NEW_CANDIDATES
                ),
                p300.CONTRACT_ID,
            )
        )
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
    if source_contract_id == p300.CONTRACT_ID:
        try:
            contract = p300.require(source_contract_id, profile)
        except p300.SourceContractError as exc:
            raise IntentError(str(exc)) from exc
        return selector.SelectedSourceContract(
            module=p300,
            contract=contract,
            implementation_verdict=p300.IMPLEMENTATION_VERDICT,
            source_check_run_id=p300.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p300.USERSPACE_VERDICT,
        )
    return _INHERITED_SELECTION(source_contract_id, profile)


def _selector_select(source_contract_id: str | None, profile: str):
    if source_contract_id != p300.CONTRACT_ID:
        return _SELECTOR_SELECT(source_contract_id, profile)
    try:
        contract = p300.require(source_contract_id, profile)
    except p300.SourceContractError as exc:
        raise selector.SourceContractSelectionError(str(exc)) from exc
    return selector.SelectedSourceContract(
        module=p300,
        contract=contract,
        implementation_verdict=p300.IMPLEMENTATION_VERDICT,
        source_check_run_id=p300.SOURCE_CHECK_RUN_ID,
        userspace_verdict=p300.USERSPACE_VERDICT,
    )


def _selector_contract_ids() -> tuple[str, ...]:
    return (*_SELECTOR_CONTRACT_IDS(), p300.CONTRACT_ID)


@contextmanager
def _context() -> Iterator[None]:
    replacements = {
        "SCHEMA": SCHEMA,
        "PREIMAGE_SCHEMA": PREIMAGE_SCHEMA,
        "VERDICT": VERDICT,
        "RUN_ID_DOMAIN": RUN_ID_DOMAIN,
        "RUN_ID_DOMAINS": RUN_ID_DOMAINS,
        "PROFILE": PROFILE,
        "PROFILE_NUMBER": PROFILE_NUMBER,
        "DEFAULT_OUT": DEFAULT_OUT,
        "DEFAULT_SOURCE": DEFAULT_SOURCE,
        "BASE_FILES": BASE_FILES,
        "SUPERSEDED_FOR_NEW_CANDIDATES": SUPERSEDED_FOR_NEW_CANDIDATES,
        "candidate_contract_ids": candidate_contract_ids,
        "selected_source_contract_for_candidate": selected_source_contract_for_candidate,
        "build_patch": build_patch,
    }
    previous = {name: getattr(base, name) for name in replacements}
    previous_selector = {
        "select": selector.select,
        "contract_ids": selector.contract_ids,
    }
    for name, value in replacements.items():
        setattr(base, name, value)
    selector.select = _selector_select
    selector.contract_ids = _selector_contract_ids
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)
        for name, value in previous_selector.items():
            setattr(selector, name, value)


def audit_patch(source, patch, run_id, unsat_tag, profile=PROFILE):  # noqa: ANN001, ANN201
    with _context():
        return base.audit_patch(source, patch, run_id, unsat_tag, profile)


def _configure() -> None:
    """Compatibility hook for downstream adapters."""


def __getattr__(name: str):
    return getattr(base, name)


def create(args):  # noqa: ANN001, ANN201
    with _context():
        return base.create(args)


def parse_args(argv: list[str] | None = None):
    with _context():
        return base.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    with _context():
        return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
