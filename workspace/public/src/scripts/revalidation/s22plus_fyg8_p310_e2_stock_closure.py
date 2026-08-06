#!/usr/bin/env python3
"""P3.10 stock-closure adapter over the unchanged P3.00 authority."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from s22plus_fyg8_p300_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p300_e2_stock_closure as parent
import s22plus_fyg8_p310_source_contract as source_contract


SCHEMA = "s22plus_fyg8_p310_stock_closure_h0_v1"
VERDICT = "PASS_P310_STOCK_CLOSURE_HOST_ONLY"
ClosureError = parent.ClosureError


@contextmanager
def _context() -> Iterator[None]:
    previous = {
        "source_contract": parent.source_contract,
        "SCHEMA": parent.SCHEMA,
        "VERDICT": parent.VERDICT,
    }
    parent.source_contract = source_contract
    parent.SCHEMA = SCHEMA
    parent.VERDICT = VERDICT
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(parent, name, value)


def select(source_contract_id: str | None):
    source_contract.require(source_contract_id, source_contract.PROFILE)
    return __import__(__name__)


def build_result(root=None):  # noqa: ANN001, ANN201
    with _context():
        return parent.build_result(root)
