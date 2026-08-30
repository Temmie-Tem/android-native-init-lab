#!/usr/bin/env python3
"""P3.20 host-only observer-error contract.

P3.19 made a useful distinction between the stock witness chain and the
/proc/last_kmsg transport, but its record path still returned parser details
directly to the module-plan caller.  P3.20 keeps that predecessor immutable
and supplies a small composition seam instead:

* the committed kmsg envelope owns record boundaries and sends only the human
  message to the retained p319_witness_observe_v2 parser;
* envelope, header, body, sequence, and witness failures become one first
  error in a separate internal namespace and return success to the module
  loop, so an observer fault cannot call the failure publisher early;
* the existing 15-byte stock payload tail carries a compact ABI-v4 receipt.

This file is deliberately an H0 source contract.  It does not build an image,
package a candidate, contact a device, or retain raw log bytes.  The raw
record remains attributable to the mandatory retained /proc/last_kmsg capture;
the compact receipt is only an index/checksum into that raw evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import struct
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
TARGET = {
    "model": "SM-S906N",
    "codename": "g0q",
    "build": "S906NKSS7FYG8",
}

RUNTIME_SOURCE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-55/stock-sources/"
    "s22plus_fyg8_p290_e3_runtime.inc.c"
)
RUNTIME_SOURCE_SIZE = 435_334
RUNTIME_SOURCE_SHA256 = (
    "0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9"
)
ENVELOPE_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p319_kmsg_record_envelope.py"
)
ENVELOPE_SOURCE_SIZE = 6_367
ENVELOPE_SOURCE_SHA256 = (
    "a0f6f9d1dffd85cc5e6beaa838a8f57e229b54c50a7e169c7f91dfe86a074c24"
)
WIRING_SOURCE = Path(__file__).with_name(
    "s22plus_fyg8_p320_kmsg_witness_wiring.py"
)
WIRING_SOURCE_SIZE = 11_181
WIRING_SOURCE_SHA256 = (
    "dd396e1d0db584c7a6e9b3f7fe886a21d691c57c33f20e690d8402ae1a0cd5ee"
)

RAW_CHECKPOINT_SOURCE = "/proc/last_kmsg"
P319_RUNTIME_ABI = 2
P320_PAYLOAD_ABI = 4
P319_PAYLOAD_ABI = 3
STOCK_PAYLOAD_SIZE = 76
OBSERVER_RECEIPT_OFFSET = 61
OBSERVER_RECEIPT_SIZE = 15
MAX_RECORD_BYTES = 4_096
MAX_MODULE_INDEX = 72
UINT16_MAX = (1 << 16) - 1
UINT64_MAX = (1 << 64) - 1

# These are checkpoint/publication details from P3.19.  They are intentionally
# not reused as observer error values.
P319_LEGACY_OBSERVER_DETAILS = frozenset((0x6020, 0x6021, 0x6022))
STOCK_DETAIL_COMPLETE = 0x6724
STOCK_DETAIL_INCOMPLETE = 0x6725
STOCK_DETAIL_AMBIGUOUS = 0x6726


class ContractError(ValueError):
    """An input is outside the bounded P3.20 contract."""


ObserverContractError = ContractError


class ObserverErrorKind(IntEnum):
    """Typed P3.20 observer namespace, independent from checkpoint details."""

    NONE = 0
    ENVELOPE = 1
    HEADER = 2
    BODY = 3
    SEQUENCE = 4
    WITNESS = 5
    UNKNOWN = 0xFF


ERROR_KIND_NAMESPACE = "P320_OBSERVER_ERROR_KIND"
ERROR_KIND_VALUES = {
    ObserverErrorKind.NONE: "NONE",
    ObserverErrorKind.ENVELOPE: "ENVELOPE",
    ObserverErrorKind.HEADER: "HEADER",
    ObserverErrorKind.BODY: "BODY",
    ObserverErrorKind.SEQUENCE: "SEQUENCE",
    ObserverErrorKind.WITNESS: "WITNESS",
    ObserverErrorKind.UNKNOWN: "UNKNOWN",
}

RECEIPT_FLAG_SEQUENCE_KNOWN = 1 << 0
RECEIPT_FLAG_MODULE_KNOWN = 1 << 1
RECEIPT_FLAG_FLAG_KNOWN = 1 << 2
RECEIPT_FLAG_LENGTH_SATURATED = 1 << 3
RECEIPT_FLAGS_ALL = (
    RECEIPT_FLAG_SEQUENCE_KNOWN
    | RECEIPT_FLAG_MODULE_KNOWN
    | RECEIPT_FLAG_FLAG_KNOWN
    | RECEIPT_FLAG_LENGTH_SATURATED
)


@dataclass(frozen=True)
class SourceSpec:
    path: Path
    size: int
    sha256: str


SOURCE_SPECS = {
    "p319_runtime": SourceSpec(
        RUNTIME_SOURCE, RUNTIME_SOURCE_SIZE, RUNTIME_SOURCE_SHA256
    ),
    "p320_envelope": SourceSpec(
        ENVELOPE_SOURCE, ENVELOPE_SOURCE_SIZE, ENVELOPE_SOURCE_SHA256
    ),
    "p320_wiring": SourceSpec(
        WIRING_SOURCE, WIRING_SOURCE_SIZE, WIRING_SOURCE_SHA256
    ),
}


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_source(spec: SourceSpec) -> bytes:
    """Read a direct regular source once and verify its complete identity."""
    direct = spec.path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(spec.size + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise ContractError(f"source is unavailable: {direct}") from exc
    before_id = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_uid,
        before.st_gid,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    inside_id = (
        inside.st_dev,
        inside.st_ino,
        inside.st_mode,
        inside.st_nlink,
        inside.st_uid,
        inside.st_gid,
        inside.st_size,
        inside.st_mtime_ns,
        inside.st_ctime_ns,
    )
    after_id = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_uid,
        after.st_gid,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != spec.size
        or before_id != inside_id
        or before_id != after_id
        or sha256(payload) != spec.sha256
    ):
        raise ContractError(f"source identity differs: {direct}")
    return payload


def bind_exact_sources() -> dict[str, Any]:
    """Bind the exact consumed P3.19 runtime and committed P3.20 sources."""
    identities: dict[str, dict[str, Any]] = {}
    for name, spec in SOURCE_SPECS.items():
        payload = _stable_source(spec)
        identities[name] = {
            "path": (
                str(spec.path.relative_to(ROOT))
                if spec.path.is_relative_to(ROOT)
                else str(spec.path)
            ),
            "size": len(payload),
            "sha256": sha256(payload),
        }
    return {
        "target": dict(TARGET),
        "runtime_abi": P319_RUNTIME_ABI,
        "raw_checkpoint_source": RAW_CHECKPOINT_SOURCE,
        "sources": identities,
        "exact_runtime_bound": True,
        "envelope_source_bound": True,
        "wiring_source_bound": True,
    }


bind_lineage = bind_exact_sources


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load committed source: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def committed_c_sources() -> tuple[bytes, bytes]:
    """Return C fragments exported by the identity-bound envelope and wiring."""
    bind_exact_sources()
    envelope = _load_module(
        ENVELOPE_SOURCE, "s22plus_fyg8_p319_kmsg_record_envelope_p320_bound"
    )
    wiring = _load_module(
        WIRING_SOURCE, "s22plus_fyg8_p320_kmsg_witness_wiring_p320_bound"
    )
    envelope_source = getattr(envelope, "P320_C_SOURCE", None)
    wiring_source = getattr(wiring, "P320_C_WIRING_SOURCE", None)
    if not isinstance(envelope_source, str) or not isinstance(wiring_source, str):
        raise ContractError("committed P3.20 C fragments are absent")
    return envelope_source.encode("ascii"), wiring_source.encode("ascii")


# P3.20 receipt C source.  It deliberately contains no checkpoint publication
# call.  The candidate builder composes these functions into the retained
# runtime and calls the v4 payload finalizer only after the ordinary stock
# fields have been populated.
P320_C_OBSERVER_SOURCE = r'''
/* P3.20 observer-error contract; raw evidence remains /proc/last_kmsg. */
#define P320_OBSERVER_ERROR_KIND_NONE 0U
#define P320_OBSERVER_ERROR_KIND_ENVELOPE 1U
#define P320_OBSERVER_ERROR_KIND_HEADER 2U
#define P320_OBSERVER_ERROR_KIND_BODY 3U
#define P320_OBSERVER_ERROR_KIND_SEQUENCE 4U
#define P320_OBSERVER_ERROR_KIND_WITNESS 5U
#define P320_OBSERVER_ERROR_KIND_UNKNOWN 0xffU
#define P320_OBSERVER_RECEIPT_SIZE 15U
#define P320_OBSERVER_RECEIPT_OFFSET 61U
#define P320_OBSERVER_PAYLOAD_SIZE 76U
#define P320_OBSERVER_MAX_MODULE_INDEX 72U
#define P320_OBSERVER_MAX_RECORD_LENGTH 4096U
#define P320_OBSERVER_FLAG_SEQUENCE_KNOWN (1U << 0U)
#define P320_OBSERVER_FLAG_MODULE_KNOWN (1U << 1U)
#define P320_OBSERVER_FLAG_FLAG_KNOWN (1U << 2U)
#define P320_OBSERVER_FLAG_LENGTH_SATURATED (1U << 3U)
#define P320_OBSERVER_RECEIPT_FLAGS_ALL 0x0fU
#define P320_OBSERVER_STOCK_PAYLOAD_ABI 4U
#define P320_OBSERVER_STOCK_DETAIL_AMBIGUOUS 0x6726U

/* This prototype is resolved by the retained P3.19 parser below this seam. */
static long p319_witness_observe_v2(const char *message, size_t length);

struct p320_observer_error_state {
    uint8_t latched;
    uint8_t kind;
    uint8_t flags;
    uint8_t flag;
    uint8_t module_index;
    uint16_t record_length;
    uint64_t sequence;
    uint8_t record_checksum;
    uint8_t sequence_seen;
    uint64_t previous_sequence;
    uint8_t active_module_valid;
    uint32_t active_module_index;
};

static struct p320_observer_error_state g_p320_observer = {0};

static uint8_t p320_observer_record_checksum(
        const char *record, size_t length)
{
    uint32_t hash = 0x811c9dc5U;
    if (record == NULL) return 0U;
    for (size_t index = 0U; index < length; ++index) {
        hash ^= (uint8_t)record[index];
        hash *= 0x01000193U;
    }
    return (uint8_t)hash;
}

static void p320_observer_reset(void) {
    memset(&g_p320_observer, 0, sizeof(g_p320_observer));
}

/* The exact 73-row module plan makes its index a stable active identity. */
static int p320_observer_set_active_module(uint32_t index, int valid) {
    if (!valid) {
        g_p320_observer.active_module_valid = 0U;
        g_p320_observer.active_module_index = 0U;
        return 0;
    }
    if (index > P320_OBSERVER_MAX_MODULE_INDEX) return -1;
    g_p320_observer.active_module_valid = 1U;
    g_p320_observer.active_module_index = index;
    return 0;
}

static void p320_observer_latch(
        uint8_t kind, const char *record, size_t length,
        uint8_t flag, int flag_known,
        uint64_t sequence, int sequence_known) {
    if (g_p320_observer.latched) return;
    if (kind == P320_OBSERVER_ERROR_KIND_NONE
        || kind == P320_OBSERVER_ERROR_KIND_UNKNOWN
        || kind > P320_OBSERVER_ERROR_KIND_WITNESS) {
        kind = P320_OBSERVER_ERROR_KIND_UNKNOWN;
    }
    g_p320_observer.latched = 1U;
    g_p320_observer.kind = kind;
    g_p320_observer.flags = 0U;
    g_p320_observer.flag = 0U;
    g_p320_observer.module_index = 0xffU;
    g_p320_observer.sequence = 0U;
    g_p320_observer.record_checksum =
        p320_observer_record_checksum(record, length);
    if (flag_known && (flag == '-' || flag == 'c')) {
        g_p320_observer.flags |= P320_OBSERVER_FLAG_FLAG_KNOWN;
        g_p320_observer.flag = flag;
    }
    if (sequence_known) {
        g_p320_observer.flags |= P320_OBSERVER_FLAG_SEQUENCE_KNOWN;
        g_p320_observer.sequence = sequence;
    }
    if (g_p320_observer.active_module_valid) {
        g_p320_observer.flags |= P320_OBSERVER_FLAG_MODULE_KNOWN;
        g_p320_observer.module_index =
            (uint8_t)g_p320_observer.active_module_index;
    }
    if (length > UINT16_MAX) {
        g_p320_observer.flags |= P320_OBSERVER_FLAG_LENGTH_SATURATED;
        g_p320_observer.record_length = UINT16_MAX;
    } else {
        g_p320_observer.record_length = (uint16_t)length;
    }
}

static uint8_t p320_observer_kind_for_envelope(long rc) {
    if (rc == P320_KMSG_ENVELOPE_BOUNDARY_ERROR)
        return P320_OBSERVER_ERROR_KIND_ENVELOPE;
    if (rc == P320_KMSG_ENVELOPE_HEADER_ERROR)
        return P320_OBSERVER_ERROR_KIND_HEADER;
    if (rc == P320_KMSG_ENVELOPE_BODY_ERROR)
        return P320_OBSERVER_ERROR_KIND_BODY;
    return P320_OBSERVER_ERROR_KIND_ENVELOPE;
}

static int p320_observer_header_hint(
        const char *record, size_t length,
        uint64_t *sequence, char *flag) {
    if (record == NULL || sequence == NULL || flag == NULL || length == 0U)
        return 0;
    const char *cursor = record;
    const char *end = record + length;
    uint64_t value = 0U;
    for (unsigned int field = 0U; field < 3U; ++field) {
        const char *start = cursor;
        uint64_t maximum = field == 0U ? UINT32_MAX : UINT64_MAX;
        if (cursor >= end || (*cursor == '0' && cursor + 1 < end
                              && cursor[1] >= '0' && cursor[1] <= '9'))
            return 0;
        value = 0U;
        while (cursor < end && *cursor >= '0' && *cursor <= '9') {
            uint64_t digit = (uint64_t)(*cursor - '0');
            if (value > (maximum - digit) / 10U) return 0;
            value = value * 10U + digit;
            ++cursor;
        }
        if (cursor == start || cursor >= end || *cursor != ',') return 0;
        if (field == 1U) *sequence = value;
        ++cursor;
    }
    if (cursor >= end || (*cursor != '-' && *cursor != 'c')) return 0;
    *flag = *cursor;
    return 1;
}

static int p320_observer_is_known_flag(char flag) {
    return flag == '-' || flag == 'c';
}

/*
 * One complete record enters here.  All observer failures are consumed and
 * return zero.  The caller may continue loading modules and draining the
 * retained raw source; the first error makes the final stock chain ambiguous.
 */
static long p320_observer_record_continue(
        const char *record, size_t length) {
    struct p320_kmsg_record_view view = {0};
    long rc = p320_kmsg_record_envelope(record, length, &view);
    if (rc != 0) {
        uint8_t kind = p320_observer_kind_for_envelope(rc);
        uint64_t hint_sequence = 0U;
        char hint_flag = 0;
        int hint_known = p320_observer_header_hint(
            record, length, &hint_sequence, &hint_flag);
        int view_known = p320_observer_is_known_flag(view.flag);
        int known = hint_known || view_known;
        p320_observer_latch(
            kind, record, length,
            hint_known ? hint_flag : view.flag,
            known,
            hint_known ? hint_sequence : view.sequence,
            known);
        return 0L;
    }
    if (g_p320_observer.sequence_seen
        && (g_p320_observer.previous_sequence == UINT64_MAX
            || view.sequence != g_p320_observer.previous_sequence + 1U)) {
        p320_observer_latch(
            P320_OBSERVER_ERROR_KIND_SEQUENCE, record, length,
            view.flag, 1, view.sequence, 1);
        return 0L;
    }
    g_p320_observer.sequence_seen = 1U;
    g_p320_observer.previous_sequence = view.sequence;
    rc = p319_witness_observe_v2(view.message, view.message_length);
    if (rc != 0L) {
        p320_observer_latch(
            P320_OBSERVER_ERROR_KIND_WITNESS, record, length,
            view.flag, 1, view.sequence, 1);
        return 0L;
    }
    return 0L;
}

static int p320_observer_error_latched(void) {
    return g_p320_observer.latched != 0U;
}

static int p320_observer_chain_ambiguous(void) {
    return g_p320_observer.latched != 0U;
}

static int p320_observer_encode_receipt(
        uint8_t receipt[P320_OBSERVER_RECEIPT_SIZE]) {
    if (receipt == NULL) return -1;
    memset(receipt, 0, P320_OBSERVER_RECEIPT_SIZE);
    if (!g_p320_observer.latched) return 0;
    receipt[0] = g_p320_observer.kind;
    receipt[1] = g_p320_observer.flags & P320_OBSERVER_RECEIPT_FLAGS_ALL;
    receipt[2] = g_p320_observer.flag;
    receipt[3] = g_p320_observer.module_index;
    receipt[4] = (uint8_t)g_p320_observer.record_length;
    receipt[5] = (uint8_t)(g_p320_observer.record_length >> 8U);
    for (unsigned int index = 0U; index < 8U; ++index)
        receipt[6U + index] =
            (uint8_t)(g_p320_observer.sequence >> (index * 8U));
    receipt[14] = g_p320_observer.record_checksum;
    return 0;
}

/* Called after the ordinary stock fields are populated. */
static int p320_observer_finalize_stock_payload_v4(
        uint8_t payload[P320_OBSERVER_PAYLOAD_SIZE]) {
    if (payload == NULL) return -1;
    payload[0] = P320_OBSERVER_STOCK_PAYLOAD_ABI;
    if (g_p320_observer.latched) {
        payload[3] |= (uint8_t)(1U << 4U);
        payload[3] &= (uint8_t)~(1U << 3U);
    }
    return p320_observer_encode_receipt(
        payload + P320_OBSERVER_RECEIPT_OFFSET);
}
'''


# The retained P319 p303 record function is replaced as one deterministic
# source transform.  It retains accounting, P308 supplemental observation,
# and the existing readback/path projections, but no longer lets an envelope
# or witness parser error escape to the module-plan failure publisher.
P320_C_RECORD_SOURCE = r'''
static long p303_kmsg_record(const char *record, size_t length) {
    if (record == NULL || length == 0U) {
        /* A malformed envelope is an observer error, not a module abort. */
        (void)p320_observer_record_continue(record, length);
        return 0L;
    }
    if (length > P303_KMSG_RECORD_CAPACITY
        || g_p303_kmsg.drain_record_count >= P319_KMSG_MAX_DRAIN_RECORDS
        || length > (size_t)(P319_KMSG_MAX_DRAIN_BYTES - g_p303_kmsg.drain_bytes)
        || g_p303_kmsg.record_count >= P319_KMSG_MAX_TOTAL_RECORDS
        || length > (size_t)(P319_KMSG_MAX_TOTAL_BYTES - g_p303_kmsg.record_bytes)) {
        return P319_DETAIL_WITNESS_BOUNDARY;
    }
    ++g_p303_kmsg.drain_record_count;
    g_p303_kmsg.drain_bytes += (uint32_t)length;
    ++g_p303_kmsg.record_count;
    g_p303_kmsg.record_bytes += (uint64_t)length;

    /* This path always consumes observer errors and therefore returns zero. */
    (void)p320_observer_record_continue(record, length);
    struct p320_kmsg_record_view view = {0};
    long rc = p320_kmsg_record_envelope(record, length, &view);
    if (rc != 0L) return 0L;
    if (!g_p303_kmsg.sequence_seen) g_p303_kmsg.first_sequence = view.sequence;
    g_p303_kmsg.sequence_seen = 1U;
    g_p303_kmsg.previous_sequence = view.sequence;

    rc = p308_kmsg_observe(view.message, view.message_length);
    if (rc != 0L) return rc;
    if (p282_find_bytes(
            view.message, view.message_length,
            "msm_hsphy_enable_clocks():") != NULL) {
        g_p303_kmsg.path_seen = 1U;
    }
    if (p282_find_bytes(
            view.message, view.message_length,
            "phy_reset assert failed") != NULL) {
        g_p303_kmsg.reset_mask |= 1U;
    }
    if (p282_find_bytes(
            view.message, view.message_length,
            "phy_reset deassert failed") != NULL) {
        g_p303_kmsg.reset_mask |= 2U;
    }
    const char *writeback = p282_find_bytes(
        view.message, view.message_length, "msm_usb_write_readback: write:");
    if (writeback == NULL) return 0L;
    const char *offset = p282_find_bytes(
        view.message, view.message_length, "QSCRATCH:");
    const char *failed = p282_find_bytes(
        view.message, view.message_length, "FAILED");
    if (offset == NULL || failed == NULL || offset >= failed)
        return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
    offset += cstr_len("QSCRATCH:");
    while (offset < failed && p282_is_space(*offset)) ++offset;
    const char *offset_end = offset;
    while (offset_end < failed
        && ((*offset_end >= '0' && *offset_end <= '9')
            || (*offset_end >= 'a' && *offset_end <= 'f')
            || (*offset_end >= 'A' && *offset_end <= 'F'))) {
        ++offset_end;
    }
    uint32_t parsed_offset = 0U;
    rc = p303_parse_hex(offset, offset_end, &parsed_offset);
    if (rc != 0L || parsed_offset > 0x1f8U || (parsed_offset & 3U) != 0U)
        return P303_DETAIL_KMSG_READBACK_FORMAT_CONTRADICTION;
    if (g_p303_kmsg.readback_count == UINT32_MAX)
        return P303_DETAIL_KMSG_COUNT_OVERFLOW;
    if (g_p303_kmsg.readback_count == 0U)
        g_p303_kmsg.first_offset = parsed_offset;
    ++g_p303_kmsg.readback_count;
    return 0L;
}
'''

# Explicit aliases make the composition seam discoverable without requiring a
# builder to depend on one historical symbol spelling.
P320_C_OBSERVER_ERROR_SOURCE = P320_C_OBSERVER_SOURCE
P320_C_RECORD_TRANSFORM_SOURCE = P320_C_RECORD_SOURCE


class ReceiptError(ContractError):
    """A compact P3.20 receipt is not canonical."""


@dataclass(frozen=True)
class ObserverError:
    """The first typed observer failure retained in the 15-byte receipt."""

    kind: ObserverErrorKind
    flag: str | None
    active_module_index: int | None
    record_length: int
    sequence: int | None
    record_checksum: int
    length_saturated: bool = False

    @property
    def active_module_identity(self) -> int | None:
        """The fixed 73-row plan index is the compact active identity."""
        return self.active_module_index

    @property
    def sequence_known(self) -> bool:
        return self.sequence is not None

    @property
    def flag_known(self) -> bool:
        return self.flag is not None

    @property
    def module_known(self) -> bool:
        return self.active_module_index is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "namespace": ERROR_KIND_NAMESPACE,
            "kind": self.kind.name,
            "kind_value": int(self.kind),
            "flag": self.flag,
            "flag_known": self.flag_known,
            "active_module_index": self.active_module_index,
            "active_module_identity": self.active_module_identity,
            "module_known": self.module_known,
            "record_length": self.record_length,
            "length_saturated": self.length_saturated,
            "sequence": self.sequence,
            "sequence_known": self.sequence_known,
            "record_checksum": self.record_checksum,
        }


def _strict_int(value: Any, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ReceiptError(f"{label} is outside its bounded integer range")
    return value


def _coerce_kind(value: ObserverErrorKind | int | str) -> ObserverErrorKind:
    if isinstance(value, ObserverErrorKind):
        return value
    if type(value) is int:
        try:
            return ObserverErrorKind(value)
        except ValueError as exc:
            raise ReceiptError("observer error kind is unknown") from exc
    if isinstance(value, str):
        try:
            return ObserverErrorKind[value]
        except KeyError as exc:
            raise ReceiptError("observer error kind is unknown") from exc
    raise ReceiptError("observer error kind type differs")


def _normalise_error(value: ObserverError | Mapping[str, Any]) -> ObserverError:
    if isinstance(value, ObserverError):
        item = value
    elif isinstance(value, Mapping):
        item = ObserverError(
            kind=_coerce_kind(value.get("kind", value.get("kind_value"))),
            flag=value.get("flag"),
            active_module_index=value.get(
                "active_module_index", value.get("active_module_identity")
            ),
            record_length=value.get("record_length", 0),
            sequence=value.get("sequence"),
            record_checksum=value.get("record_checksum", 0),
            length_saturated=value.get("length_saturated", False),
        )
    else:
        raise ReceiptError("observer error shape differs")
    kind = _coerce_kind(item.kind)
    if kind == ObserverErrorKind.NONE:
        raise ReceiptError("NONE is reserved for a zero receipt")
    if item.flag is not None and item.flag not in ("-", "c"):
        raise ReceiptError("observer flag is unknown")
    module = item.active_module_index
    if module is not None:
        _strict_int(module, 0, MAX_MODULE_INDEX, "active module index")
    length = _strict_int(item.record_length, 0, UINT16_MAX, "record length")
    sequence = item.sequence
    if sequence is not None:
        _strict_int(sequence, 0, UINT64_MAX, "sequence")
    checksum = _strict_int(item.record_checksum, 0, 0xFF, "record checksum")
    if type(item.length_saturated) is not bool:
        raise ReceiptError("length saturation flag type differs")
    return ObserverError(
        kind=kind,
        flag=item.flag,
        active_module_index=module,
        record_length=length,
        sequence=sequence,
        record_checksum=checksum,
        length_saturated=item.length_saturated,
    )


def fnv1a8(record: bytes) -> int:
    """The low byte of FNV-1a over the retained raw record."""
    if not isinstance(record, bytes):
        raise ReceiptError("record must be bytes")
    value = 0x811C9DC5
    for byte in record:
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value & 0xFF


def make_observer_error(
    kind: ObserverErrorKind | int | str,
    *,
    record: bytes = b"",
    flag: str | None = None,
    active_module_index: int | None = None,
    sequence: int | None = None,
    record_length: int | None = None,
    record_checksum: int | None = None,
    length_saturated: bool = False,
) -> ObserverError:
    """Create a canonical error, deriving length/checksum from raw bytes."""
    if not isinstance(record, bytes):
        raise ReceiptError("record must be bytes")
    actual_length = len(record)
    saturated = actual_length > UINT16_MAX
    if record_length is None:
        record_length = min(actual_length, UINT16_MAX)
    if record_checksum is None:
        record_checksum = fnv1a8(record)
    return _normalise_error(
        ObserverError(
            kind=_coerce_kind(kind),
            flag=flag,
            active_module_index=active_module_index,
            record_length=record_length,
            sequence=sequence,
            record_checksum=record_checksum,
            length_saturated=bool(length_saturated or saturated),
        )
    )


def encode_error_receipt(
    error: ObserverError | Mapping[str, Any] | None,
) -> bytes:
    """Encode a canonical error or the all-zero clean receipt."""
    if error is None:
        return bytes(OBSERVER_RECEIPT_SIZE)
    item = _normalise_error(error)
    flags = 0
    if item.sequence is not None:
        flags |= RECEIPT_FLAG_SEQUENCE_KNOWN
    if item.active_module_index is not None:
        flags |= RECEIPT_FLAG_MODULE_KNOWN
    if item.flag is not None:
        flags |= RECEIPT_FLAG_FLAG_KNOWN
    if item.length_saturated:
        flags |= RECEIPT_FLAG_LENGTH_SATURATED
    result = bytearray(OBSERVER_RECEIPT_SIZE)
    result[0] = int(item.kind)
    result[1] = flags
    result[2] = ord(item.flag) if item.flag is not None else 0
    result[3] = (
        item.active_module_index if item.active_module_index is not None else 0xFF
    )
    struct.pack_into("<H", result, 4, item.record_length)
    struct.pack_into("<Q", result, 6, item.sequence or 0)
    result[14] = item.record_checksum
    return bytes(result)


def decode_error_receipt(receipt: bytes) -> ObserverError | None:
    """Decode and strictly validate one 15-byte ABI-v4 receipt."""
    if not isinstance(receipt, bytes) or len(receipt) != OBSERVER_RECEIPT_SIZE:
        raise ReceiptError("observer receipt size differs")
    if receipt == bytes(OBSERVER_RECEIPT_SIZE):
        return None
    try:
        kind = ObserverErrorKind(receipt[0])
    except ValueError as exc:
        raise ReceiptError("observer receipt kind differs") from exc
    if kind == ObserverErrorKind.NONE:
        raise ReceiptError("nonzero receipt has NONE kind")
    flags = receipt[1]
    if flags & ~RECEIPT_FLAGS_ALL:
        raise ReceiptError("observer receipt reserved flags are set")
    flag_known = bool(flags & RECEIPT_FLAG_FLAG_KNOWN)
    if flag_known:
        if receipt[2] not in (ord("-"), ord("c")):
            raise ReceiptError("observer receipt flag differs")
        flag: str | None = chr(receipt[2])
    else:
        if receipt[2] != 0:
            raise ReceiptError("unknown observer flag carries a byte")
        flag = None
    module_known = bool(flags & RECEIPT_FLAG_MODULE_KNOWN)
    if module_known:
        if receipt[3] > MAX_MODULE_INDEX:
            raise ReceiptError("observer receipt module index differs")
        module: int | None = receipt[3]
    else:
        if receipt[3] != 0xFF:
            raise ReceiptError("unknown observer module carries an index")
        module = None
    record_length = struct.unpack_from("<H", receipt, 4)[0]
    sequence_value = struct.unpack_from("<Q", receipt, 6)[0]
    sequence_known = bool(flags & RECEIPT_FLAG_SEQUENCE_KNOWN)
    if sequence_known:
        sequence: int | None = sequence_value
    else:
        if sequence_value != 0:
            raise ReceiptError("unknown observer sequence carries bytes")
        sequence = None
    return _normalise_error(
        ObserverError(
            kind=kind,
            flag=flag,
            active_module_index=module,
            record_length=record_length,
            sequence=sequence,
            record_checksum=receipt[14],
            length_saturated=bool(flags & RECEIPT_FLAG_LENGTH_SATURATED),
        )
    )


decode_receipt = decode_error_receipt
encode_receipt = encode_error_receipt
validate_receipt = decode_error_receipt


def _header_metadata(record: bytes) -> tuple[int, str] | None:
    semicolon = record.find(b";")
    if semicolon < 0:
        return None
    fields = record[:semicolon].split(b",")
    if len(fields) < 4:
        return None
    values = []
    for value, maximum in zip(fields[:3], (0xFFFFFFFF, UINT64_MAX, UINT64_MAX)):
        if not value or (len(value) > 1 and value.startswith(b"0")):
            return None
        if any(byte < ord("0") or byte > ord("9") for byte in value):
            return None
        parsed = int(value)
        if parsed > maximum:
            return None
        values.append(parsed)
    if fields[3] not in (b"-", b"c"):
        return None
    return values[1], fields[3].decode("ascii")


def _classify_envelope_failure(record: bytes, message: str) -> ObserverErrorKind:
    if not record or len(record) > MAX_RECORD_BYTES:
        return ObserverErrorKind.ENVELOPE
    metadata = _header_metadata(record)
    if metadata is None:
        return ObserverErrorKind.HEADER
    if "extension" in message or "header" in message:
        return ObserverErrorKind.HEADER
    return ObserverErrorKind.BODY


def _envelope_parse(record: bytes) -> dict[str, Any]:
    module = _load_module(
        ENVELOPE_SOURCE, "s22plus_fyg8_p319_kmsg_record_envelope_p320_runtime"
    )
    return module.parse_record(record)


@dataclass(frozen=True)
class ObservationOutcome:
    returned_code: int
    accepted: bool
    error: ObserverError | None
    chain_ambiguous: bool
    human_message: bytes | None


@dataclass
class ObserverState:
    """A small Python model of the one-shot C observer seam."""

    active_module_index: int | None = None
    previous_sequence: int | None = None
    first_error: ObserverError | None = None

    @property
    def chain_ambiguous(self) -> bool:
        return self.first_error is not None

    @property
    def error_latched(self) -> bool:
        return self.first_error is not None

    def set_active_module(self, index: int | None) -> None:
        if index is None:
            self.active_module_index = None
            return
        _strict_int(index, 0, MAX_MODULE_INDEX, "active module index")
        self.active_module_index = index

    def latch(self, error: ObserverError) -> ObserverError:
        if self.first_error is None:
            self.first_error = _normalise_error(error)
        return self.first_error

    def observe(
        self,
        record: bytes,
        *,
        witness_return_code: int = 0,
    ) -> ObservationOutcome:
        if not isinstance(record, bytes):
            raise ContractError("kmsg record must be bytes")
        metadata = _header_metadata(record)
        try:
            value = _envelope_parse(record)
        except Exception as exc:  # EnvelopeError is loaded from a bound source.
            message = str(exc)
            kind = _classify_envelope_failure(record, message)
            sequence = metadata[0] if metadata is not None else None
            flag = metadata[1] if metadata is not None else None
            error = make_observer_error(
                kind,
                record=record,
                flag=flag,
                active_module_index=self.active_module_index,
                sequence=sequence,
            )
            first = self.latch(error)
            return ObservationOutcome(0, False, first, True, None)
        sequence = int(value["sequence"])
        flag = str(value["flag"])
        if (
            self.previous_sequence is not None
            and (
                self.previous_sequence == UINT64_MAX
                or sequence != self.previous_sequence + 1
            )
        ):
            error = make_observer_error(
                ObserverErrorKind.SEQUENCE,
                record=record,
                flag=flag,
                active_module_index=self.active_module_index,
                sequence=sequence,
            )
            first = self.latch(error)
            return ObservationOutcome(0, False, first, True, value["message"])
        self.previous_sequence = sequence
        if type(witness_return_code) is not int:
            raise ContractError("witness return code type differs")
        if witness_return_code != 0:
            error = make_observer_error(
                ObserverErrorKind.WITNESS,
                record=record,
                flag=flag,
                active_module_index=self.active_module_index,
                sequence=sequence,
            )
            first = self.latch(error)
            return ObservationOutcome(0, False, first, True, value["message"])
        return ObservationOutcome(
            0, True, self.first_error, self.chain_ambiguous, value["message"]
        )

    def receipt(self) -> bytes:
        return encode_error_receipt(self.first_error)

    def payload_v4(self, base_payload: bytes) -> bytes:
        return encode_stock_payload_v4(base_payload, self.first_error)


def encode_stock_payload_v4(
    base_payload: bytes,
    error: ObserverError | Mapping[str, Any] | None = None,
) -> bytes:
    """Upgrade an ordinary P3.19 76-byte payload to ABI-v4.

    base_payload is the already populated stock payload.  The only semantic
    changes are the ABI byte, the existing ambiguous bit on error, and the
    15-byte tail.  No new checkpoint detail is introduced.
    """
    if not isinstance(base_payload, bytes) or len(base_payload) != STOCK_PAYLOAD_SIZE:
        raise ContractError("stock payload size differs")
    if base_payload[0] not in (P319_PAYLOAD_ABI, P320_PAYLOAD_ABI):
        raise ContractError("stock payload ABI predecessor differs")
    if any(base_payload[OBSERVER_RECEIPT_OFFSET:]):
        raise ContractError("stock payload observer tail is already populated")
    payload = bytearray(base_payload)
    payload[0] = P320_PAYLOAD_ABI
    if error is not None:
        payload[3] |= 1 << 4
        payload[3] &= ~(1 << 3)
    payload[OBSERVER_RECEIPT_OFFSET:] = encode_error_receipt(error)
    validate_stock_payload_v4(bytes(payload))
    return bytes(payload)


def validate_stock_payload_v4(payload: bytes) -> dict[str, Any]:
    """Strictly validate ABI-v4 stock payload and return its state summary."""
    if not isinstance(payload, bytes) or len(payload) != STOCK_PAYLOAD_SIZE:
        raise ContractError("stock payload size differs")
    if payload[0] != P320_PAYLOAD_ABI:
        raise ContractError("ABI3 or unknown stock payload is not ABI4")
    if payload[3] & 0xC0:
        raise ContractError("stock chain reserved bits are set")
    stage = payload[3] & 0x07
    complete = bool(payload[3] & (1 << 3))
    ambiguous = bool(payload[3] & (1 << 4))
    if stage > 4 or (complete and stage != 4) or (complete and ambiguous):
        raise ContractError("stock chain state is inconsistent")
    if payload[56:59] != bytes((3, 1, 1)):
        raise ContractError("stock status or parent-unavailable markers differ")
    receipt = decode_error_receipt(payload[OBSERVER_RECEIPT_OFFSET:])
    if receipt is not None and not ambiguous:
        raise ContractError("observer receipt does not mark chain ambiguous")
    state = "AMBIGUOUS" if ambiguous else "COMPLETE" if complete else "INCOMPLETE"
    detail = {
        "COMPLETE": STOCK_DETAIL_COMPLETE,
        "INCOMPLETE": STOCK_DETAIL_INCOMPLETE,
        "AMBIGUOUS": STOCK_DETAIL_AMBIGUOUS,
    }[state]
    return {
        "payload_abi": P320_PAYLOAD_ABI,
        "chain_stage": stage,
        "chain_complete": complete,
        "chain_ambiguous": ambiguous,
        "state": state,
        "terminal_detail": detail,
        "observer_receipt": receipt,
        "observer_receipt_zero": receipt is None,
        "raw_checkpoint_source": RAW_CHECKPOINT_SOURCE,
    }


decode_stock_payload_v4 = validate_stock_payload_v4
encode_payload_v4 = encode_stock_payload_v4
decode_payload_v4 = validate_stock_payload_v4
validate_payload_v4 = validate_stock_payload_v4


def terminal_detail_for_payload(payload: bytes) -> int:
    return int(validate_stock_payload_v4(payload)["terminal_detail"])


def _extract_c_function(source: bytes, name: bytes) -> bytes:
    """Extract one simple C function, preserving source bytes exactly."""
    token = b"static long " + name + b"("
    start = source.find(token)
    if start < 0:
        raise ContractError(f"runtime function is absent: {name.decode()}")
    open_paren = source.find(b"(", start)
    depth = 0
    close_paren = -1
    in_string = False
    escaped = False
    for index in range(open_paren, len(source)):
        byte = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif byte == ord("\\"):
                escaped = True
            elif byte == ord('"'):
                in_string = False
            continue
        if byte == ord('"'):
            in_string = True
        elif byte == ord("("):
            depth += 1
        elif byte == ord(")"):
            depth -= 1
            if depth == 0:
                close_paren = index
                break
    if close_paren < 0:
        raise ContractError(f"runtime function signature is truncated: {name.decode()}")
    cursor = close_paren + 1
    while cursor < len(source) and chr(source[cursor]).isspace():
        cursor += 1
    if cursor >= len(source) or source[cursor] != ord("{"):
        raise ContractError(f"runtime function body is absent: {name.decode()}")
    depth = 0
    in_string = False
    escaped = False
    in_line_comment = False
    in_block_comment = False
    index = cursor
    while index < len(source):
        byte = source[index]
        next_byte = source[index + 1] if index + 1 < len(source) else 0
        if in_line_comment:
            if byte == ord("\n"):
                in_line_comment = False
        elif in_block_comment:
            if byte == ord("*") and next_byte == ord("/"):
                in_block_comment = False
                index += 1
        elif in_string:
            if escaped:
                escaped = False
            elif byte == ord("\\"):
                escaped = True
            elif byte == ord('"'):
                in_string = False
        elif byte == ord('"'):
            in_string = True
        elif byte == ord("/") and next_byte == ord("/"):
            in_line_comment = True
            index += 1
        elif byte == ord("/") and next_byte == ord("*"):
            in_block_comment = True
            index += 1
        elif byte == ord("{"):
            depth += 1
        elif byte == ord("}"):
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
        index += 1
    raise ContractError(f"runtime function body is truncated: {name.decode()}")


def _replace_once(source: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = source.count(old)
    if count != 1:
        raise ContractError(f"{label} anchor count is {count}, expected one")
    return source.replace(old, new, 1)


def compose_runtime(runtime: bytes | None = None) -> bytes:
    """Compose the P3.20 observer seam into exact consumed P3.19 source.

    The returned bytes are a host-side deterministic transform only.  The
    caller still has to perform the normal independent candidate qualification
    and review before any device use.
    """
    if runtime is None:
        runtime = _stable_source(SOURCE_SPECS["p319_runtime"])
    elif not isinstance(runtime, bytes):
        raise ContractError("runtime source must be bytes")
    if len(runtime) != RUNTIME_SOURCE_SIZE or sha256(runtime) != RUNTIME_SOURCE_SHA256:
        raise ContractError("runtime is not the exact consumed P3.19 source")
    envelope, wiring = committed_c_sources()
    # Suppress only the standalone helper warning in this composed runtime.
    wiring = _replace_once(
        wiring,
        b"static long p320_kmsg_witness_observe_v2(",
        b"static __attribute__((unused)) long p320_kmsg_witness_observe_v2(",
        "P320 wiring helper",
    )
    anchor = (
        b"#define S22PLUS_MAX77705_P319_STOCK_STATUS_WIDTH 3U\n"
        b"#define P319_WITNESS_ABI_VERSION 2U\n"
    )
    composed = _replace_once(
        runtime,
        anchor,
        b"/* P3.20 committed envelope and wiring seam. */\n"
        + envelope
        + b"\n"
        + wiring
        + b"\n"
        + P320_C_OBSERVER_SOURCE.encode("ascii")
        + b"\n"
        + anchor,
        "P3.20 runtime insertion",
    )
    old_record = _extract_c_function(composed, b"p303_kmsg_record")
    composed = _replace_once(
        composed,
        old_record,
        P320_C_RECORD_SOURCE.encode("ascii"),
        "P3.20 record transform",
    )
    composed = _replace_once(
        composed,
        b"#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 3U",
        b"#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 4U",
        "P3.20 payload ABI",
    )
    composed = _replace_once(
        composed,
        b"witness->malformed_count != 0U ||\n"
        b"        witness->initial_chain_stage > 4U ||",
        b"witness->malformed_count != 0U && !p320_observer_error_latched() ||\n"
        b"        witness->initial_chain_stage > 4U ||",
        "P3.20 observer-malformed gate",
    )
    composed = _replace_once(
        composed,
        b"if (terminal_state == 2U && witness->initial_chain_ambiguous == 0U)\n"
        b"        return -1;",
        b"if (terminal_state == 2U && witness->initial_chain_ambiguous == 0U\n"
        b"        && !p320_observer_error_latched()) return -1;",
        "P3.20 observer terminal gate",
    )
    old_terminal = (
        b"terminal_state = witness.initial_chain_ambiguous != 0U ? 2U\n"
        b"        : (witness.initial_chain_complete != 0U ? 0U : 1U);"
    )
    new_terminal = (
        b"terminal_state = p320_observer_chain_ambiguous()\n"
        b"        || witness.initial_chain_ambiguous != 0U ? 2U\n"
        b"        : (witness.initial_chain_complete != 0U ? 0U : 1U);"
    )
    composed = _replace_once(
        composed, old_terminal, new_terminal, "P3.20 terminal state"
    )
    payload_tail = b"    payload[60] = (uint8_t)witness->deferred_status_count;"
    composed = _replace_once(
        composed,
        payload_tail,
        payload_tail
        + b"\n    if (p320_observer_finalize_stock_payload_v4(payload) != 0) return -1;",
        "P3.20 stock payload tail",
    )
    return composed


compose_stock_runtime = compose_runtime


def observer_source_fragment() -> bytes:
    return P320_C_OBSERVER_SOURCE.encode("ascii")


def host_fixture_source() -> bytes:
    """Build a small C fixture for Python/C parity tests."""
    envelope, wiring = committed_c_sources()
    wiring = wiring.replace(
        b"static long p320_kmsg_witness_observe_v2(",
        b"static __attribute__((unused)) long p320_kmsg_witness_observe_v2(",
        1,
    )
    prefix = b"""#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static long g_fixture_witness_rc;
static unsigned int g_fixture_witness_calls;
static unsigned char g_fixture_last_message[4096];
static size_t g_fixture_last_message_length;
static long p319_witness_observe_v2(const char *message, size_t length) {
    ++g_fixture_witness_calls;
    if (length > sizeof(g_fixture_last_message)) return -77L;
    if (message != NULL && length != 0U)
        memcpy(g_fixture_last_message, message, length);
    g_fixture_last_message_length = length;
    return g_fixture_witness_rc;
}
"""
    suffix = r'''
static int fixture_hex(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return 10 + value - 'a';
    if (value >= 'A' && value <= 'F') return 10 + value - 'A';
    return -1;
}
static size_t fixture_decode(const char *text, unsigned char *out, size_t cap) {
    size_t length = strlen(text);
    if ((length & 1U) != 0U || length / 2U > cap) return 0U;
    for (size_t index = 0U; index < length / 2U; ++index) {
        int high = fixture_hex(text[index * 2U]);
        int low = fixture_hex(text[index * 2U + 1U]);
        if (high < 0 || low < 0) return 0U;
        out[index] = (unsigned char)((high << 4) | low);
    }
    return length / 2U;
}
static void fixture_print_hex(const unsigned char *value, size_t length) {
    for (size_t index = 0U; index < length; ++index)
        printf("%02x", value[index]);
}
int main(int argc, char **argv) {
    unsigned char record[8192];
    unsigned char receipt[P320_OBSERVER_RECEIPT_SIZE];
    unsigned char payload[P320_OBSERVER_PAYLOAD_SIZE] = {0};
    payload[3] = 0x0cU;
    payload[56] = 3U;
    payload[57] = 1U;
    payload[58] = 1U;
    p320_observer_reset();
    (void)&p320_kmsg_witness_observe_v2;
    for (int index = 1; index < argc; ++index) {
        if (strncmp(argv[index], "module=", 7) == 0) {
            char *end = NULL;
            unsigned long value = strtoul(argv[index] + 7, &end, 10);
            if (end == argv[index] + 7 || *end != '\0'
                || p320_observer_set_active_module((uint32_t)value, 1) != 0)
                return 10;
            continue;
        }
        if (strncmp(argv[index], "witness=", 8) == 0) {
            char *end = NULL;
            g_fixture_witness_rc = strtol(argv[index] + 8, &end, 10);
            if (end == argv[index] + 8 || *end != '\0') return 11;
            continue;
        }
        size_t length = fixture_decode(argv[index], record, sizeof(record));
        if (length == 0U && argv[index][0] != '\0') return 12;
        (void)p320_observer_record_continue((const char *)record, length);
    }
    if (p320_observer_encode_receipt(receipt) != 0) return 13;
    if (p320_observer_finalize_stock_payload_v4(payload) != 0) return 14;
    printf("%u %u %u %u %u %u %u %u ",
        g_fixture_witness_calls, p320_observer_error_latched(),
        p320_observer_chain_ambiguous(), receipt[0], receipt[1], receipt[2],
        receipt[3], (unsigned)receipt[4] | ((unsigned)receipt[5] << 8U));
    fixture_print_hex(receipt, sizeof(receipt));
    printf(" ");
    fixture_print_hex(payload, sizeof(payload));
    printf(" ");
    fixture_print_hex(g_fixture_last_message, g_fixture_last_message_length);
    printf("\n");
    return 0;
}
'''.encode("ascii")
    return (
        prefix
        + envelope
        + b"\n"
        + wiring
        + b"\n"
        + P320_C_OBSERVER_SOURCE.encode("ascii")
        + suffix
    )


__all__ = [
    "ContractError",
    "ERROR_KIND_NAMESPACE",
    "ERROR_KIND_VALUES",
    "ENVELOPE_SOURCE",
    "ENVELOPE_SOURCE_SHA256",
    "ENVELOPE_SOURCE_SIZE",
    "MAX_MODULE_INDEX",
    "MAX_RECORD_BYTES",
    "ObserverContractError",
    "ObserverError",
    "ObserverErrorKind",
    "ObserverState",
    "ObservationOutcome",
    "OBSERVER_RECEIPT_OFFSET",
    "OBSERVER_RECEIPT_SIZE",
    "P319_LEGACY_OBSERVER_DETAILS",
    "P319_PAYLOAD_ABI",
    "P320_C_OBSERVER_SOURCE",
    "P320_C_OBSERVER_ERROR_SOURCE",
    "P320_C_RECORD_SOURCE",
    "P320_C_RECORD_TRANSFORM_SOURCE",
    "P320_PAYLOAD_ABI",
    "ReceiptError",
    "RAW_CHECKPOINT_SOURCE",
    "RUNTIME_SOURCE",
    "RUNTIME_SOURCE_SHA256",
    "RUNTIME_SOURCE_SIZE",
    "STOCK_DETAIL_AMBIGUOUS",
    "STOCK_DETAIL_COMPLETE",
    "STOCK_DETAIL_INCOMPLETE",
    "STOCK_PAYLOAD_SIZE",
    "WIRING_SOURCE",
    "WIRING_SOURCE_SHA256",
    "WIRING_SOURCE_SIZE",
    "bind_exact_sources",
    "bind_lineage",
    "committed_c_sources",
    "compose_runtime",
    "compose_stock_runtime",
    "decode_error_receipt",
    "decode_payload_v4",
    "decode_receipt",
    "decode_stock_payload_v4",
    "encode_error_receipt",
    "encode_payload_v4",
    "encode_receipt",
    "encode_stock_payload_v4",
    "fnv1a8",
    "host_fixture_source",
    "make_observer_error",
    "observer_source_fragment",
    "terminal_detail_for_payload",
    "validate_payload_v4",
    "validate_receipt",
    "validate_stock_payload_v4",
]
