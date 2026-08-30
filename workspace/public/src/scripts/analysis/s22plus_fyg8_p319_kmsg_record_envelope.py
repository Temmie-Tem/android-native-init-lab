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


P320_C_SOURCE = r'''
#define P320_KMSG_ENVELOPE_MAX_RECORD 4096U
#define P320_KMSG_ENVELOPE_MAX_EXTENSIONS 16U
#define P320_KMSG_ENVELOPE_HEADER_ERROR (-1L)
#define P320_KMSG_ENVELOPE_BODY_ERROR (-2L)
#define P320_KMSG_ENVELOPE_BOUNDARY_ERROR (-3L)

struct p320_kmsg_record_view {
    uint32_t facility_level;
    uint64_t sequence;
    uint64_t timestamp_us;
    char flag;
    const char *message;
    size_t message_length;
    uint32_t extension_fields;
    uint32_t dictionary_lines;
};

static long p320_kmsg_decimal(
    const char **cursor, const char *end, uint64_t maximum, uint64_t *value) {
    const char *start = *cursor;
    if (start >= end || (*start == '0' && start + 1 < end
                         && start[1] >= '0' && start[1] <= '9'))
        return P320_KMSG_ENVELOPE_HEADER_ERROR;
    uint64_t result = 0;
    while (*cursor < end && **cursor >= '0' && **cursor <= '9') {
        uint64_t digit = (uint64_t)(**cursor - '0');
        if (result > (maximum - digit) / 10U)
            return P320_KMSG_ENVELOPE_HEADER_ERROR;
        result = result * 10U + digit;
        ++*cursor;
    }
    if (*cursor == start) return P320_KMSG_ENVELOPE_HEADER_ERROR;
    *value = result;
    return 0;
}

static long p320_kmsg_comma(
    const char **cursor, const char *end, uint64_t maximum, uint64_t *value) {
    long rc = p320_kmsg_decimal(cursor, end, maximum, value);
    if (rc != 0 || *cursor >= end || **cursor != ',')
        return P320_KMSG_ENVELOPE_HEADER_ERROR;
    ++*cursor;
    return 0;
}

static long p320_kmsg_record_envelope(
    const char *record, size_t length, struct p320_kmsg_record_view *view) {
    if (record == NULL || view == NULL || length == 0U
        || length > P320_KMSG_ENVELOPE_MAX_RECORD)
        return P320_KMSG_ENVELOPE_BOUNDARY_ERROR;
    const char *end = record + length;
    if (*(end - 1) != '\n') return P320_KMSG_ENVELOPE_BODY_ERROR;

    const char *cursor = record;
    uint64_t facility = 0;
    long rc = p320_kmsg_comma(&cursor, end, UINT32_MAX, &facility);
    if (rc == 0) rc = p320_kmsg_comma(&cursor, end, UINT64_MAX, &view->sequence);
    if (rc == 0) rc = p320_kmsg_comma(&cursor, end, UINT64_MAX, &view->timestamp_us);
    if (rc != 0 || cursor >= end || (*cursor != '-' && *cursor != 'c'))
        return P320_KMSG_ENVELOPE_HEADER_ERROR;
    view->facility_level = (uint32_t)facility;
    view->flag = *cursor++;
    view->extension_fields = 0U;

    while (cursor < end && *cursor == ',') {
        if (view->extension_fields >= P320_KMSG_ENVELOPE_MAX_EXTENSIONS)
            return P320_KMSG_ENVELOPE_BOUNDARY_ERROR;
        ++cursor;
        const char *field = cursor;
        while (cursor < end && *cursor != ',' && *cursor != ';') {
            if (*cursor < ' ' || *cursor > '~')
                return P320_KMSG_ENVELOPE_HEADER_ERROR;
            ++cursor;
        }
        if (cursor == field) return P320_KMSG_ENVELOPE_HEADER_ERROR;
        ++view->extension_fields;
    }
    if (cursor >= end || *cursor != ';')
        return P320_KMSG_ENVELOPE_HEADER_ERROR;
    ++cursor;

    const char *body_end = end - 1;
    const char *message_end = cursor;
    while (message_end < body_end && *message_end != '\n') ++message_end;
    view->message = cursor;
    view->message_length = (size_t)(message_end - cursor);
    view->dictionary_lines = 0U;
    cursor = message_end;
    while (cursor < body_end) {
        ++cursor;
        if (cursor >= body_end || *cursor != ' ')
            return P320_KMSG_ENVELOPE_BODY_ERROR;
        ++view->dictionary_lines;
        while (cursor < body_end && *cursor != '\n') ++cursor;
    }
    return 0;
}
'''


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
