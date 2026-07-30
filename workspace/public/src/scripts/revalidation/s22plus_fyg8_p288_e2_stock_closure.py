#!/usr/bin/env python3
"""P2.88 stock-closure adapter over the unchanged P2.86 authority."""

from __future__ import annotations

import sys

from s22plus_fyg8_p286_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p286_e2_stock_closure as p286
import s22plus_fyg8_p288_contract_spec as spec
import s22plus_fyg8_p288_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p288_stock_closure_h0_v1"
VERDICT = "PASS_P288_STOCK_CLOSURE_HOST_ONLY"
REQUIRED_ABSOLUTE_PATH_STRINGS = p286.REQUIRED_ABSOLUTE_PATH_STRINGS
ALLOWED_ABSOLUTE_PATH_STRINGS = p286.ALLOWED_ABSOLUTE_PATH_STRINGS
_p286_authority_paths = p286._p286_authority_paths
_entrypoints = p286._entrypoints


def select(source_contract_id: str | None):
    try:
        source_contract.require(source_contract_id, spec.PROFILE)
    except source_contract.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc  # noqa: F405
    return sys.modules[__name__]


def _validate_p288_authority_strings(data: bytes) -> None:
    with _p286_authority_paths():
        p286._validate_p286_authority_strings(data)


_validate_p286_authority_strings = _validate_p288_authority_strings
_validate_p282_authority_strings = _validate_p288_authority_strings


def build_result(root=None):  # noqa: ANN001, ANN201
    result = dict(p286.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
