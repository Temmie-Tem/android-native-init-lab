#!/usr/bin/env python3
"""Create one P3.10 Carrier v2 candidate intent."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import s22plus_fyg8_p300_candidate_intent as parent
import s22plus_fyg8_p310_source_contract as p310


base = parent.base
selector = parent.selector
leaf = parent.base.base.base.base
SCHEMA = p310.INTENT_SCHEMA
PREIMAGE_SCHEMA = p310.PREIMAGE_SCHEMA
VERDICT = p310.INTENT_VERDICT
RUN_ID_DOMAIN = p310.RUN_ID_DOMAIN
DEFAULT_OUT = Path("workspace/private/outputs/s22plus_fyg8_p310/intent")
TARGET = parent.TARGET
PROFILE = p310.PROFILE
PROFILE_NUMBER = parent.PROFILE_NUMBER
SUPPORTED_PROFILES = parent.SUPPORTED_PROFILES
DEFAULT_SOURCE = p310.DRIVER_SOURCE_REFERENCE
DEFAULT_BASE_PATCH = parent.DEFAULT_BASE_PATCH
DEFCONFIG = parent.DEFCONFIG
BASE_FILES = dict(parent.BASE_FILES)
decoder = p310.decoder
IntentError = parent.IntentError
RUN_ID_DOMAINS = {**parent.RUN_ID_DOMAINS, "E2": RUN_ID_DOMAIN}
SUPERSEDED_FOR_NEW_CANDIDATES = {
    **parent.SUPERSEDED_FOR_NEW_CANDIDATES,
    parent.p300.CONTRACT_ID: p310.CONTRACT_ID,
}
_PARENT_SELECTION = parent.selected_source_contract_for_candidate
_PARENT_CONTRACT_IDS = parent.candidate_contract_ids
_SELECTOR_SELECT = parent._selector_select  # noqa: SLF001
_SELECTOR_CONTRACT_IDS = parent._selector_contract_ids  # noqa: SLF001
_BASE_IDENTITY_PREIMAGE = leaf.identity_preimage
_PARENT_BUILD_PATCH = parent.build_patch


def build_patch(base_patch: bytes, run_id: bytes, unsat_tag: bytes, profile: str = PROFILE) -> bytes:
    replacements = (
        (
            f'+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{p310.SOURCE_CHECK_RUN_ID.hex()}"'.encode(),
            f'+CONFIG_S22PLUS_FYG8_E1_RUN_ID_HEX="{run_id.hex()}"'.encode(),
        ),
        (
            f'+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{p310.SOURCE_CHECK_UNSAT_TAG.hex()}"'.encode(),
            f'+CONFIG_S22PLUS_FYG8_E1_UNSAT_TAG_HEX="{unsat_tag.hex()}"'.encode(),
        ),
    )
    counts = tuple(base_patch.count(old) for old, _new in replacements)
    if counts == (0, 0):
        return _PARENT_BUILD_PATCH(base_patch, run_id, unsat_tag, profile)
    if counts != (1, 1):
        raise IntentError("P3.10 candidate config source binding differs")
    value = base_patch
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def candidate_contract_ids() -> tuple[str, ...]:
    return tuple(dict.fromkeys((*_PARENT_CONTRACT_IDS(), p310.CONTRACT_ID)))


def selected_source_contract_for_candidate(source_contract_id: str | None, profile: str):
    if source_contract_id == p310.CONTRACT_ID:
        return selector.SelectedSourceContract(
            module=p310,
            contract=p310.require(source_contract_id, profile),
            implementation_verdict=p310.IMPLEMENTATION_VERDICT,
            source_check_run_id=p310.SOURCE_CHECK_RUN_ID,
            userspace_verdict=p310.USERSPACE_VERDICT,
        )
    replacement = SUPERSEDED_FOR_NEW_CANDIDATES.get(source_contract_id)
    if replacement is not None:
        raise IntentError(f"source contract {source_contract_id!r} is superseded for new candidates by {replacement!r}")
    return _PARENT_SELECTION(source_contract_id, profile)


def _selector_select(source_contract_id: str | None, profile: str):
    if source_contract_id == p310.CONTRACT_ID:
        return selected_source_contract_for_candidate(source_contract_id, profile)
    return _SELECTOR_SELECT(source_contract_id, profile)


def _selector_contract_ids() -> tuple[str, ...]:
    return (*_SELECTOR_CONTRACT_IDS(), p310.CONTRACT_ID)


def identity_preimage(nonce, sources, profile=PROFILE, source_contract_id=None):  # noqa: ANN001, ANN201
    value = _BASE_IDENTITY_PREIMAGE(nonce, sources, profile, source_contract_id)
    if source_contract_id == p310.CONTRACT_ID:
        value["record_layout"] = "S22E1L2-192-ab-header-slot-crc-payload64"
    return value


@contextmanager
def _context() -> Iterator[None]:
    with parent._context():  # noqa: SLF001
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
            "identity_preimage": identity_preimage,
            "build_patch": build_patch,
        }
        previous = {name: getattr(base, name) for name in replacements}
        old_selector = {"select": selector.select, "contract_ids": selector.contract_ids}
        old_leaf_identity_preimage = leaf.identity_preimage
        for name, value in replacements.items():
            setattr(base, name, value)
        selector.select = _selector_select
        selector.contract_ids = _selector_contract_ids
        leaf.identity_preimage = identity_preimage
        try:
            yield
        finally:
            for name, value in previous.items():
                setattr(base, name, value)
            selector.select = old_selector["select"]
            selector.contract_ids = old_selector["contract_ids"]
            leaf.identity_preimage = old_leaf_identity_preimage


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
