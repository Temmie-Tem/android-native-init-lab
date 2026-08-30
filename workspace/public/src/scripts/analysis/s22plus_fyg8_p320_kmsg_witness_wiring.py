#!/usr/bin/env python3
"""Host-only P3.20 kmsg-envelope to P3.19-witness wiring fixture.

The P3.19 candidate is consumed evidence.  This successor reads the exact
retained stock-candidate runtime, extracts its existing v2 witness parser
without editing it, and defines the smallest seam needed to pass the
envelope's human message to that parser.  Header extensions, dictionary
lines, and the ``c`` flag are envelope metadata; this module deliberately
keeps no fragment reassembly state and grants no candidate or device
authority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ENVELOPE_SCRIPT = Path(__file__).with_name("s22plus_fyg8_p319_kmsg_record_envelope.py")
RETAINED_RUNTIME = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-25/stock-sources/"
    "s22plus_fyg8_p290_e3_runtime.inc.c"
)

RETAINED_RUNTIME_SIZE = 435_446
RETAINED_RUNTIME_SHA256 = (
    "4cf48cc790881bebc0b27facf9919e7b81e892b54dcf10c8e03c7b4e77c5c198"
)
P319_PARSER_ABI_VERSION = 2
P319_PARSER_START = b"#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH"
P319_RECORD_START = b"static long p303_kmsg_record"
P319_PARSER_ENTRY = b"p319_witness_observe_v2"


class WiringError(ValueError):
    """A retained source or wiring input is outside this H0 fixture."""


def _load_envelope_module() -> Any:
    """Load the committed envelope prototype without making scripts a package."""
    import importlib.util
    import sys

    name = "s22plus_fyg8_p319_kmsg_record_envelope_for_p320"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, ENVELOPE_SCRIPT)
    if spec is None or spec.loader is None:
        raise WiringError("P319 envelope module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_ENVELOPE = _load_envelope_module()
EnvelopeError = _ENVELOPE.EnvelopeError

# Re-export the exact committed C envelope source so a fixture cannot silently
# drift to a second hand-written envelope implementation.
P320_C_SOURCE = _ENVELOPE.P320_C_SOURCE


P320_C_WIRING_SOURCE = r'''
/*
 * P3.20 H0 seam: envelope parsing owns the record boundary.  The consumed
 * P3.19 v2 parser receives exactly view.message/view.message_length.  No
 * header, dictionary line, or fragment accumulator is passed across it.
 */
static long p320_kmsg_witness_observe_v2(
    const char *record, size_t length) {
    struct p320_kmsg_record_view view = {0};
    long rc = p320_kmsg_record_envelope(record, length, &view);
    if (rc != 0) return rc;
    return p319_witness_observe_v2(view.message, view.message_length);
}
'''


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_retained_runtime(path: Path = RETAINED_RUNTIME) -> bytes:
    """Read the exact consumed P3.19 stock runtime with an identity check."""
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        payload = direct.read_bytes()
        after = direct.lstat()
    except OSError as exc:
        raise WiringError("retained P3.19 stock runtime is unavailable") from exc
    if (
        direct != resolved
        or not direct.is_file()
        or before.st_nlink != 1
        or before.st_size != RETAINED_RUNTIME_SIZE
        or len(payload) != RETAINED_RUNTIME_SIZE
        or _sha256(payload) != RETAINED_RUNTIME_SHA256
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        raise WiringError("retained P3.19 stock runtime identity differs")
    return payload


def extract_retained_parser(runtime: bytes | None = None) -> bytes:
    """Extract the consumed candidate's existing P3.19 v2 parser bytes."""
    source = load_retained_runtime() if runtime is None else runtime
    start = source.find(P319_PARSER_START)
    end = source.find(P319_RECORD_START, start)
    if start < 0 or end < 0 or start >= end:
        raise WiringError("retained P3.19 parser boundaries are absent")
    parser = source[start:end]
    marker = f"#define P319_WITNESS_ABI_VERSION {P319_PARSER_ABI_VERSION}U".encode("ascii")
    if parser.count(marker) != 1 or parser.count(P319_PARSER_ENTRY) < 1:
        raise WiringError("retained P3.19 parser ABI differs")
    return parser


def human_message(record: bytes) -> bytes:
    """Return only the envelope's human message for the existing parser."""
    return _ENVELOPE.parse_record(record)["message"]


def record_to_witness_message(record: bytes) -> bytes:
    """Explicitly named alias for the one-way, stateless transform."""
    return human_message(record)


def transform_record(record: bytes) -> bytes:
    """Transform one complete kmsg record; never joins adjacent ``c`` records."""
    return human_message(record)


def transform_records(records: list[bytes] | tuple[bytes, ...]) -> list[bytes]:
    """Apply the stateless transform independently to each complete record."""
    return [human_message(record) for record in records]


def build_fixture_source(parser: bytes | None = None) -> bytes:
    """Compose a host C fixture from the retained parser and committed envelope."""
    parser_source = extract_retained_parser() if parser is None else parser
    if not isinstance(parser_source, bytes) or not parser_source:
        raise WiringError("parser source is empty")
    prefix = (
        b"#include <stdint.h>\n"
        b"#include <stddef.h>\n"
        b"#include <limits.h>\n"
        b"#include <string.h>\n"
        b"static size_t cstr_len(const char *s) { return strlen(s); }\n"
        b"static int p260_bytes_equal(const char *a, const char *b, size_t n) { return memcmp(a, b, n) == 0; }\n"
        b"struct p303_kmsg_capture { int fd; uint8_t started; uint8_t final; uint8_t path_seen; uint8_t reset_mask; uint8_t sequence_seen; uint32_t readback_count; uint32_t first_offset; uint64_t previous_sequence; uint64_t first_sequence; uint64_t record_count; uint64_t record_bytes; uint32_t drain_count; uint32_t module_count; uint32_t module_drain_count; uint32_t drain_record_count; uint32_t drain_bytes; };\n"
        b"static struct p303_kmsg_capture g_p303_kmsg;\n"
    )
    return prefix + parser_source + P320_C_SOURCE.encode("ascii") + P320_C_WIRING_SOURCE.encode("ascii")


__all__ = [
    "EnvelopeError",
    "P320_C_SOURCE",
    "P320_C_WIRING_SOURCE",
    "RETAINED_RUNTIME",
    "RETAINED_RUNTIME_SHA256",
    "RETAINED_RUNTIME_SIZE",
    "WiringError",
    "build_fixture_source",
    "extract_retained_parser",
    "human_message",
    "load_retained_runtime",
    "record_to_witness_message",
    "transform_record",
    "transform_records",
]
