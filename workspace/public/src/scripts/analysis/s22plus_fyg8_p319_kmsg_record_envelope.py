#!/usr/bin/env python3
"""Small host prototype for the Linux /dev/kmsg record envelope.

This does not modify the consumed P3.19 parser or define a new candidate ABI.
It separates the human message from valid continuation dictionary lines while
preserving unknown header extensions for later candidate integration.
"""

from __future__ import annotations

from typing import Any


MAX_RECORD_BYTES = 4096
UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1


class EnvelopeError(ValueError):
    """A kmsg record is outside the bounded envelope contract."""


def _decimal(value: bytes, maximum: int, label: str) -> int:
    if (
        not value
        or (len(value) > 1 and value.startswith(b"0"))
        or any(byte < ord("0") or byte > ord("9") for byte in value)
    ):
        raise EnvelopeError(f"{label} is not canonical decimal")
    parsed = int(value)
    if parsed > maximum:
        raise EnvelopeError(f"{label} is out of range")
    return parsed


def _extension(value: bytes) -> str:
    if (
        not value
        or any(byte < 0x20 or byte > 0x7E for byte in value)
        or b";" in value
    ):
        raise EnvelopeError("header extension is not bounded ASCII")
    return value.decode("ascii")


def parse_record(record: bytes) -> dict[str, Any]:
    """Parse one length-framed /dev/kmsg read without parsing witness text."""
    if not record or len(record) > MAX_RECORD_BYTES:
        raise EnvelopeError("record length is outside the bounded range")
    if not record.endswith(b"\n"):
        raise EnvelopeError("record lacks its terminal newline")

    semicolon = record.find(b";")
    if semicolon < 0:
        raise EnvelopeError("record lacks the header terminator")
    fields = record[:semicolon].split(b",")
    if len(fields) < 4:
        raise EnvelopeError("record lacks mandatory header fields")

    facility_level = _decimal(fields[0], UINT32_MAX, "facility/level")
    sequence = _decimal(fields[1], UINT64_MAX, "sequence")
    timestamp_us = _decimal(fields[2], UINT64_MAX, "timestamp")
    if fields[3] not in (b"-", b"c"):
        raise EnvelopeError("record flag differs")

    body_lines = record[semicolon + 1 : -1].split(b"\n")
    message = body_lines[0]
    dictionary = body_lines[1:]
    if any(not line.startswith(b" ") for line in dictionary):
        raise EnvelopeError("continuation line lacks its leading space")

    return {
        "facility_level": facility_level,
        "sequence": sequence,
        "timestamp_us": timestamp_us,
        "flag": fields[3].decode("ascii"),
        "header_extensions": [_extension(value) for value in fields[4:]],
        "message": message,
        "dictionary": dictionary,
        "record_length": len(record),
    }
