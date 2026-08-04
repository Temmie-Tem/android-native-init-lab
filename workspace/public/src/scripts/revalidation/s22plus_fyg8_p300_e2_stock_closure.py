#!/usr/bin/env python3
"""P3.00 stock-closure adapter over the unchanged P2.98 authority."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import sys
from typing import Iterator

from s22plus_fyg8_p298_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p298_e2_stock_closure as p298
import s22plus_fyg8_p300_source_contract as source_contract
import s22plus_fyg8_p300_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p300_stock_closure_h0_v1"
VERDICT = "PASS_P300_STOCK_CLOSURE_HOST_ONLY"
p286 = p298.p286
TRACE_STAT_PATHS = frozenset(
    f"/sys/kernel/tracing/instances/p282/per_cpu/cpu{cpu}/stats"
    for cpu in range(32)
)
P300_TRACE_PATHS = frozenset(
    {
        *TRACE_STAT_PATHS,
        "/sys/kernel/tracing/instances/p282/options/overwrite",
        "/trigger",
    }
)
REQUIRED_ABSOLUTE_PATH_STRINGS = frozenset(
    {*p298.REQUIRED_ABSOLUTE_PATH_STRINGS, *P300_TRACE_PATHS}
)
ALLOWED_ABSOLUTE_PATH_STRINGS = frozenset(
    {*p298.ALLOWED_ABSOLUTE_PATH_STRINGS, *P300_TRACE_PATHS}
)
_entrypoints = p298._entrypoints  # noqa: SLF001
_P282_VALIDATE_AUTHORITY_STRINGS = p298._P282_VALIDATE_AUTHORITY_STRINGS  # noqa: SLF001

# The two candidate nonces exercised before intent derivation produce distinct
# whole-ELF receipts but the same text receipt and exact instruction bytes.
# The printable slash sequence is therefore pinned to the invariant .text
# section rather than to mutable run-ID data in .rodata.
INCIDENTAL_INIT_SIZE = 66384
INCIDENTAL_PATH = b'/E9"'
INCIDENTAL_PATH_OFFSET = 0x3929
INCIDENTAL_TEXT_OFFSET = 0x120
INCIDENTAL_TEXT_END = 0x8F14
INCIDENTAL_TEXT_SHA256 = (
    "1b812bac3281c1ca9acd8d2b8ab8aeea6afc5175caeb879b115413e440584ba5"
)
INCIDENTAL_INSTRUCTION_WINDOW_OFFSET = 0x3928
INCIDENTAL_INSTRUCTION_WINDOW = bytes.fromhex("e02f4539220000b0")


def select(source_contract_id: str | None):
    try:
        source_contract.require(source_contract_id, spec.PROFILE)
    except source_contract.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc  # noqa: F405
    return sys.modules[__name__]


def _scrub_exact_incidental_opcode_path(data: bytes) -> bytes:
    text = data[INCIDENTAL_TEXT_OFFSET:INCIDENTAL_TEXT_END]
    if (
        len(data) != INCIDENTAL_INIT_SIZE
        or hashlib.sha256(text).hexdigest() != INCIDENTAL_TEXT_SHA256
        or data.count(INCIDENTAL_PATH) != 1
        or data.find(INCIDENTAL_PATH) != INCIDENTAL_PATH_OFFSET
        or INCIDENTAL_PATH_OFFSET != INCIDENTAL_INSTRUCTION_WINDOW_OFFSET + 1
        or INCIDENTAL_INSTRUCTION_WINDOW_OFFSET < INCIDENTAL_TEXT_OFFSET
        or (
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
            + len(INCIDENTAL_INSTRUCTION_WINDOW)
            > INCIDENTAL_TEXT_END
        )
        or (INCIDENTAL_INSTRUCTION_WINDOW_OFFSET - INCIDENTAL_TEXT_OFFSET) % 4
        != 0
        or data[
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET:
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
            + len(INCIDENTAL_INSTRUCTION_WINDOW)
        ]
        != INCIDENTAL_INSTRUCTION_WINDOW
    ):
        raise ClosureError("P3.00 incidental opcode-path receipt mismatch")  # noqa: F405
    strings = p286.p282.p280.isolated_p260._printable_strings(data)
    absolute_paths = p286.p282._absolute_path_candidates(strings)
    unexpected = absolute_paths - ALLOWED_ABSOLUTE_PATH_STRINGS
    if unexpected != {INCIDENTAL_PATH.decode("ascii")}:
        raise ClosureError("P3.00 incidental opcode-path set mismatch")  # noqa: F405
    return (
        data[:INCIDENTAL_PATH_OFFSET]
        + (b"\0" * len(INCIDENTAL_PATH))
        + data[INCIDENTAL_PATH_OFFSET + len(INCIDENTAL_PATH):]
    )


@contextmanager
def _p300_authority_globals() -> Iterator[None]:
    previous_required = p286.p282.REQUIRED_ABSOLUTE_PATH_STRINGS
    previous_allowed = p286.p282.ALLOWED_ABSOLUTE_PATH_STRINGS
    p286.p282.REQUIRED_ABSOLUTE_PATH_STRINGS = REQUIRED_ABSOLUTE_PATH_STRINGS
    p286.p282.ALLOWED_ABSOLUTE_PATH_STRINGS = ALLOWED_ABSOLUTE_PATH_STRINGS
    try:
        yield
    finally:
        p286.p282.REQUIRED_ABSOLUTE_PATH_STRINGS = previous_required
        p286.p282.ALLOWED_ABSOLUTE_PATH_STRINGS = previous_allowed


def _validate_p300_authority_strings(data: bytes) -> None:
    with _p300_authority_globals():
        try:
            _P282_VALIDATE_AUTHORITY_STRINGS(data)
        except ClosureError as original:  # noqa: F405
            try:
                _P282_VALIDATE_AUTHORITY_STRINGS(
                    _scrub_exact_incidental_opcode_path(data)
                )
            except ClosureError:  # noqa: F405
                raise original


@contextmanager
def _p300_authority_paths() -> Iterator[None]:
    previous = p286.p282._validate_p282_authority_strings
    p286.p282._validate_p282_authority_strings = _validate_p300_authority_strings
    try:
        yield
    finally:
        p286.p282._validate_p282_authority_strings = previous


_p286_authority_paths = _p300_authority_paths


_validate_p286_authority_strings = _validate_p300_authority_strings
_validate_p282_authority_strings = _validate_p300_authority_strings


def build_result(root=None):  # noqa: ANN001, ANN201
    with _p300_authority_paths():
        result = dict(p286.build_result(root))
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "contract_id": source_contract.CONTRACT_ID,
        }
    )
    return result
