#!/usr/bin/env python3
"""P2.86 stock-closure adapter over the unchanged P2.82 module plan."""

from __future__ import annotations

from contextlib import contextmanager
import sys
from typing import Iterator

from s22plus_fyg8_p282_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p282_e2_stock_closure as p282
import s22plus_fyg8_p286_contract_spec as spec
import s22plus_fyg8_p286_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p286_stock_closure_h0_v1"
VERDICT = "PASS_P286_STOCK_CLOSURE_HOST_ONLY"
_entrypoints = p282._entrypoints
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *p282.REQUIRED_ABSOLUTE_PATH_STRINGS,
        spec.PARENT_RUNTIME_STATUS_PATH,
    )
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    (
        *p282.ALLOWED_ABSOLUTE_PATH_STRINGS,
        spec.PARENT_RUNTIME_STATUS_PATH,
    )
)


def select(source_contract_id: str | None):
    try:
        source_contract.require(source_contract_id, spec.PROFILE)
    except source_contract.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc  # noqa: F405
    return sys.modules[__name__]


@contextmanager
def _p286_authority_paths() -> Iterator[None]:
    previous_required = p282.REQUIRED_ABSOLUTE_PATH_STRINGS
    previous_allowed = p282.ALLOWED_ABSOLUTE_PATH_STRINGS
    p282.REQUIRED_ABSOLUTE_PATH_STRINGS = REQUIRED_ABSOLUTE_PATH_STRINGS
    p282.ALLOWED_ABSOLUTE_PATH_STRINGS = ALLOWED_ABSOLUTE_PATH_STRINGS
    try:
        yield
    finally:
        p282.REQUIRED_ABSOLUTE_PATH_STRINGS = previous_required
        p282.ALLOWED_ABSOLUTE_PATH_STRINGS = previous_allowed


def _validate_p286_authority_strings(data: bytes) -> None:
    if (
        REQUIRED_ABSOLUTE_PATH_STRINGS
        - p282.REQUIRED_ABSOLUTE_PATH_STRINGS
        != {spec.PARENT_RUNTIME_STATUS_PATH}
        or ALLOWED_ABSOLUTE_PATH_STRINGS
        - p282.ALLOWED_ABSOLUTE_PATH_STRINGS
        != {spec.PARENT_RUNTIME_STATUS_PATH}
    ):
        raise ClosureError("P2.86 parent path authority delta drifted")
    with _p286_authority_paths():
        p282._validate_p282_authority_strings(data)


_validate_p282_authority_strings = _validate_p286_authority_strings


def build_result(root=None):
    result = dict(p282.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
