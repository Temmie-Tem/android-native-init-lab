#!/usr/bin/env python3
"""P2.98 stock-closure adapter over the unchanged P2.86 authority."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import sys
from typing import Iterator

from s22plus_fyg8_p286_e2_stock_closure import *  # noqa: F403
import s22plus_fyg8_p286_e2_stock_closure as p286
import s22plus_fyg8_p298_source_contract as source_contract
import s22plus_fyg8_p298_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p298_stock_closure_h0_v1"
VERDICT = "PASS_P298_STOCK_CLOSURE_HOST_ONLY"
REQUIRED_ABSOLUTE_PATH_STRINGS = p286.REQUIRED_ABSOLUTE_PATH_STRINGS
ALLOWED_ABSOLUTE_PATH_STRINGS = p286.ALLOWED_ABSOLUTE_PATH_STRINGS
_entrypoints = p286._entrypoints
_P282_VALIDATE_AUTHORITY_STRINGS = p286.p282._validate_p282_authority_strings

# The canonical P2.98 init contains one four-byte printable slash sequence
# across two AArch64 instructions.  It is not a runtime string and the whole
# ELF is already bound by the userspace receipt.  Keep this exception pinned
# to that exact artifact and exact instruction window; every other byte stream
# still goes through the inherited full-binary authority validator unchanged.
INCIDENTAL_INIT_SHA256 = (
    "e35e2a1d978d2c9f4af0d6b3ac254239324c6f503312107b1a5a89c91f702daa"
)
INCIDENTAL_INIT_SIZE = 66384
INCIDENTAL_PATH = b"/M9@"
INCIDENTAL_PATH_OFFSET = 0x5A51
INCIDENTAL_TEXT_OFFSET = 0x120
INCIDENTAL_TEXT_END = 0x7C08
INCIDENTAL_INSTRUCTION_WINDOW_OFFSET = 0x5A50
INCIDENTAL_INSTRUCTION_WINDOW = bytes.fromhex("e02f4d3940010034")


def select(source_contract_id: str | None):
    try:
        source_contract.require(source_contract_id, spec.PROFILE)
    except source_contract.SourceContractError as exc:
        raise ClosureError(str(exc)) from exc  # noqa: F405
    return sys.modules[__name__]


def _scrub_exact_incidental_opcode_path(data: bytes) -> bytes:
    if (
        len(data) != INCIDENTAL_INIT_SIZE
        or hashlib.sha256(data).hexdigest() != INCIDENTAL_INIT_SHA256
        or data.count(INCIDENTAL_PATH) != 1
        or data.find(INCIDENTAL_PATH) != INCIDENTAL_PATH_OFFSET
        or INCIDENTAL_PATH_OFFSET != INCIDENTAL_INSTRUCTION_WINDOW_OFFSET + 1
        or INCIDENTAL_INSTRUCTION_WINDOW_OFFSET < INCIDENTAL_TEXT_OFFSET
        or (
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
            + len(INCIDENTAL_INSTRUCTION_WINDOW)
            > INCIDENTAL_TEXT_END
        )
        or (
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET - INCIDENTAL_TEXT_OFFSET
        )
        % 4
        != 0
        or data[
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET:
            INCIDENTAL_INSTRUCTION_WINDOW_OFFSET
            + len(INCIDENTAL_INSTRUCTION_WINDOW)
        ]
        != INCIDENTAL_INSTRUCTION_WINDOW
    ):
        raise ClosureError(  # noqa: F405
            "P2.98 incidental opcode-path receipt mismatch"
        )

    strings = p286.p282.p280.isolated_p260._printable_strings(data)
    absolute_paths = p286.p282._absolute_path_candidates(strings)
    unexpected = absolute_paths - ALLOWED_ABSOLUTE_PATH_STRINGS
    if unexpected != {INCIDENTAL_PATH.decode("ascii")}:
        raise ClosureError(  # noqa: F405
            "P2.98 incidental opcode-path set mismatch"
        )

    return (
        data[:INCIDENTAL_PATH_OFFSET]
        + (b"\0" * len(INCIDENTAL_PATH))
        + data[INCIDENTAL_PATH_OFFSET + len(INCIDENTAL_PATH):]
    )


def _validate_p298_authority_strings(data: bytes) -> None:
    with p286._p286_authority_paths():
        try:
            _P282_VALIDATE_AUTHORITY_STRINGS(data)
        except ClosureError as original:  # noqa: F405
            try:
                scrubbed = _scrub_exact_incidental_opcode_path(data)
                _P282_VALIDATE_AUTHORITY_STRINGS(scrubbed)
            except ClosureError:  # noqa: F405
                raise original


@contextmanager
def _p298_authority_paths() -> Iterator[None]:
    """Route the inherited generic-rootfs audit through the P2.98 validator."""

    previous = p286.p282._validate_p282_authority_strings
    p286.p282._validate_p282_authority_strings = (
        _validate_p298_authority_strings
    )
    try:
        yield
    finally:
        p286.p282._validate_p282_authority_strings = previous


_p286_authority_paths = _p298_authority_paths


_validate_p286_authority_strings = _validate_p298_authority_strings
_validate_p282_authority_strings = _validate_p298_authority_strings


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
