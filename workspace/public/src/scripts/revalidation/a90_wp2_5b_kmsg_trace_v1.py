#!/usr/bin/env python3
"""Generate and validate the host-only A90 WP2-5b.1 kmsg trace contract.

This module is deliberately incapable of opening a device or dispatching an
effect.  It defines the exact binary trace, validates raw /dev/kmsg records,
binds them to the existing WP2-4 property result, and models no-replay journal
prefixes.  Runtime integration and live authority remain separate work.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
BASE = "docs/security/hardening/a90-wlan-vendor-property-ablation-2026-08-15"
DEFAULT_CONTRACT = ROOT / BASE / "schema/a90-wp2-5b-kmsg-trace-v1.json"
DEFAULT_HEADER = (
    ROOT
    / "workspace/public/src/native-init/helpers/"
    "a90_wp2_5b_kmsg_contract.h"
)

WP2_GENERATOR_REL = (
    "workspace/public/src/scripts/revalidation/"
    "a90_h24_wlan_property_observation_schema_v1.py"
)
WP2_SCHEMA_REL = f"{BASE}/schema/a90-h24-wlan-property-observation-schema-v1.json"
SOURCE_REPORT_REL = "docs/reports/A90_WLAN_KERNEL_SOURCE_CONFIRMATION_H0_2026-08-16.md"
MAC_REPORT_REL = "docs/reports/A90_WLAN_MAC_PROVISIONING_EXISTING_EVIDENCE_H0_2026-08-16.md"

PINNED_INPUTS = {
    WP2_GENERATOR_REL: (
        60728,
        "afdab4bbfc5c25b9be62433e3cecc0265c9d106bfc8da7d27e76594a5672f935",
    ),
    WP2_SCHEMA_REL: (
        25818,
        "fa31a4845d48baeedba81bda1a7cad29e83e7328ab7450f836079756d05d9248",
    ),
    SOURCE_REPORT_REL: (
        28372,
        "9414541bf79d9f59facccb0554d5e7226656f2f7c49c204130e79213beaf5403",
    ),
    MAC_REPORT_REL: (
        15385,
        "144bf161f8009f518c1a5d6b815b2a00e24ef7a0b131619ccce37add417b673b",
    ),
}

CONTRACT_SCHEMA = "a90-wp2-5b-kmsg-trace-contract-v1"
TRACE_SCHEMA = "a90-wp2-5b-kmsg-trace-v1"
QUALIFIED_SCHEMA = "a90-wp2-5b-kmsg-qualified-expectation-v1"
JOURNAL_RECORD_SCHEMA = "a90-wp2-5b-kmsg-journal-record-v1"
BOUND_RESULT_SCHEMA = "a90-wp2-5b-kmsg-bound-result-v1"
DRIVER_OUTCOME_SCHEMA = "a90-wp2-5b-driver-outcome-receipt-v1"

TRACE_MAGIC = b"A90K5B1\x00"
TRACE_VERSION = 1
TRACE_HEADER = struct.Struct(">8sHHI")
FRAME_HEADER = struct.Struct(">BBHI")
ARM_PAYLOAD = struct.Struct(">32s32s32s32sIQ")
FAULT_PAYLOAD = struct.Struct(">IiIQ")
END_PAYLOAD = struct.Struct(">32s32sIQQQ")

FRAME_ARM = 1
FRAME_RECORD = 2
FRAME_FAULT = 3
FRAME_END = 4
FRAME_NAMES = {
    FRAME_ARM: "ARM",
    FRAME_RECORD: "RECORD",
    FRAME_FAULT: "FAULT",
    FRAME_END: "END",
}

FAULT_READ = 1
FAULT_POLL = 2
FAULT_EPIPE = 3
FAULT_EINVAL = 4
FAULT_RECORD_FORMAT = 5
FAULT_SEQUENCE = 6
FAULT_COUNT_CAP = 7
FAULT_BYTE_CAP = 8
FAULT_BOUNDARY = 9
FAULT_EFAULT = 10
FAULT_NAMES = {
    FAULT_READ: "READ_ERROR",
    FAULT_POLL: "POLL_ERROR",
    FAULT_EPIPE: "EPIPE_OVERRUN",
    FAULT_EINVAL: "EINVAL_CURSOR_ADVANCED",
    FAULT_RECORD_FORMAT: "RECORD_FORMAT_ERROR",
    FAULT_SEQUENCE: "SEQUENCE_ERROR",
    FAULT_COUNT_CAP: "RECORD_COUNT_CAP_EXHAUSTED",
    FAULT_BYTE_CAP: "RECORD_BYTE_CAP_EXHAUSTED",
    FAULT_BOUNDARY: "BOUNDARY_ERROR",
    FAULT_EFAULT: "EFAULT_CURSOR_ADVANCED",
}

KMSG_RECORD_MAX = 8192
KMSG_PRIORITY_MAX = (255 << 3) | 7
UINT32_MAX = (1 << 32) - 1
UINT64_MAX = (1 << 64) - 1
ZERO_SHA256 = "0" * 64

TYPE0_ABSENT = "WLAN MAC address is not set, type 0"
TYPE1_ABSENT = "WLAN MAC address is not set, type 1"
MAC_TRUE_FAILURE = "getting MAC address from platform driver failed"

JOURNAL_EVENTS = (
    "OBSERVER_ARMED",
    "EFFECT_INTENT",
    "EFFECT_DISPATCHED",
    "DRIVER_OUTCOME_BOUND",
    "CAPTURE_CLOSED",
    "TERMINAL",
)
JOURNAL_RECORD_KEYS = {
    "event",
    "payloadSha256",
    "previousRecordSha256",
    "runBindingSha256",
    "schema",
    "sequence",
}
TRACE_EXPECTATION_KEYS = {
    "captureCloseBindingSha256",
    "contractSha256",
    "driverInitEpochSha256",
    "observerBinarySha256",
    "qualificationSha256",
    "recordByteCap",
    "recordCountCap",
    "runBindingSha256",
}
QUALIFIED_KEYS = TRACE_EXPECTATION_KEYS | {
    "effectCommandSha256",
    "proofSubjectSha256",
    "propertyExpectation",
    "schema",
}
BOUND_RESULT_KEYS = {
    "authority",
    "bindings",
    "deviceSafetyState",
    "experimentProofOutcome",
    "findings",
    "generationPromotionEligible",
    "journal",
    "schema",
    "trace",
    "workflowState",
}
DRIVER_OUTCOME_KEYS = {
    "bootIdSha256",
    "driverIdentityReceiptSha256",
    "driverInitEpochSha256",
    "interfaceOutcomeReceiptSha256",
    "runBindingSha256",
    "schema",
    "wlanOutcome",
}
DRIVER_OUTCOMES = {
    "WLAN0_UP_EXACT_DRIVER",
    "MAC_INIT_FAILED_EXACT_SIGNATURE",
    "OTHER_OR_UNPROVED",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _is_sha256(value: Any, *, allow_zero: bool = False) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    if any(ch not in "0123456789abcdef" for ch in value):
        return False
    return allow_zero or value != ZERO_SHA256


def _strict_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        if any(type(key) is not str for key in left) or set(left) != set(right):
            return False
        return all(_strict_json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _strict_json_equal(a, b) for a, b in zip(left, right)
        )
    return left == right


def _read_pinned_regular(rel: str) -> bytes:
    path = ROOT / rel
    root = ROOT.resolve(strict=True)
    resolved = path.resolve(strict=True)
    if os.path.commonpath((str(root), str(resolved))) != str(root):
        raise ValueError(f"pinned input escapes repository: {rel}")
    before = path.lstat()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ValueError(f"unsafe pinned input: {rel}")
        chunks = []
        while True:
            chunk = os.read(fd, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        after_open = os.fstat(fd)
    finally:
        os.close(fd)
    after_path = path.lstat()
    identity = (opened.st_dev, opened.st_ino)
    if (
        identity != (after_open.st_dev, after_open.st_ino)
        or identity != (after_path.st_dev, after_path.st_ino)
        or opened.st_size != after_open.st_size
        or opened.st_mtime_ns != after_open.st_mtime_ns
    ):
        raise ValueError(f"pinned input changed during read: {rel}")
    return b"".join(chunks)


def _pinned_receipts() -> list[dict[str, Any]]:
    receipts = []
    for rel, (expected_size, expected_sha) in sorted(PINNED_INPUTS.items()):
        data = _read_pinned_regular(rel)
        actual = (len(data), _sha256(data))
        if actual != (expected_size, expected_sha):
            raise ValueError(
                f"pinned input drift: {rel}: expected "
                f"{expected_size}/{expected_sha}, got {actual[0]}/{actual[1]}"
            )
        receipts.append(
            {"path": rel, "bytes": expected_size, "sha256": expected_sha}
        )
    return receipts


def build_contract() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "status": "H0_TRACE_CORE_ONLY_RUNTIME_INTEGRATION_ABSENT",
        "scope": {
            "target": "Samsung Galaxy A90 5G only",
            "workPackage": "WP2-5b.1",
            "hazard": "A90_WP2_5B_POSTHOC_KMSG_RETENTION_GAP",
            "permanentInvariant": "WP2_5B_KMSG_STREAM_COMPLETENESS",
            "retiredGate": None,
            "openGate": "WP2_5B_STREAMING_KMSG_OBSERVER_ABSENT",
            "statement": (
                "This contract closes only raw framing, sequence validation, "
                "WP2-4 result binding, and H0 no-replay prefix semantics. It "
                "does not open /dev/kmsg, publish a durable journal, qualify "
                "a runtime observer, select numeric budgets, or authorize a run."
            ),
        },
        "authority": {
            "tier": "H0",
            "candidateEligible": False,
            "deviceContact": False,
            "d0Authorized": False,
            "d1Authorized": False,
            "f1Authorized": False,
            "liveExecutionAuthorized": False,
            "propertyProvisionAuthorized": False,
            "ufsMutationAuthorized": False,
            "generationPromotionAuthorized": False,
        },
        "sourcePins": _pinned_receipts(),
        "wireFormat": {
            "magicHex": TRACE_MAGIC.hex(),
            "version": TRACE_VERSION,
            "traceHeader": ">8sHHI",
            "frameHeader": ">BBHI",
            "frameFlags": 0,
            "frameReserved": 0,
            "frames": [
                {
                    "id": FRAME_ARM,
                    "name": "ARM",
                    "cardinality": "EXACTLY_ONE_FIRST",
                    "payload": ">32s32s32s32sIQ",
                },
                {
                    "id": FRAME_RECORD,
                    "name": "RECORD",
                    "cardinality": "ZERO_OR_MORE_BEFORE_FAULT_OR_END",
                    "payload": "ONE_EXACT_DEV_KMSG_READ_1_TO_8192_BYTES",
                },
                {
                    "id": FRAME_FAULT,
                    "name": "FAULT",
                    "cardinality": "ZERO_OR_ONE_TERMINAL_FAULT_BEFORE_END",
                    "payload": ">IiIQ",
                },
                {
                    "id": FRAME_END,
                    "name": "END",
                    "cardinality": "EXACTLY_ONE_LAST",
                    "payload": ">32s32sIQQQ",
                },
            ],
            "faultReasons": [
                {"id": key, "name": value}
                for key, value in sorted(FAULT_NAMES.items())
            ],
        },
        "kmsgRecordContract": {
            "source": "/dev/kmsg",
            "sourceKind": "NON_SYMLINK_CHAR_DEVICE_RDEV_1_11",
            "openFlags": ["O_RDONLY", "O_NONBLOCK", "O_CLOEXEC"],
            "initialSeek": "SEEK_END_OFFSET_0",
            "fallbacksForbidden": [
                "/proc/kmsg",
                "dmesg snapshot",
                "last_kmsg",
                "pstore absence",
            ],
            "recordMaxBytes": KMSG_RECORD_MAX,
            "headerGrammar": "priority,sequence,timestamp,continuation;body",
            "priorityRange": [0, KMSG_PRIORITY_MAX],
            "escapedTextGrammar": (
                "Printable ASCII except backslash is literal; every backslash "
                "introduces exactly lowercase \\xHH for a raw byte below 0x20, "
                "at least 0x7f, or backslash itself. Dictionary data begins with "
                "a space-prefixed line; only its source-derived final newline "
                "may be empty."
            ),
            "continuationFlags": ["-", "c"],
            "completeProof": [
                "ARM precedes durable effect intent and driver init",
                "zero FAULT frames",
                "zero EPIPE and zero POLLERR",
                "strict sequence increment by one across every RECORD",
                "every read is one complete canonical extended record",
                "END follows the bound driver outcome and final EAGAIN drain",
                "record and raw-byte counts match END and qualified caps",
            ],
            "consumedReadFaults": {
                "sourceOrdering": (
                    "The selected devkmsg_read advances user->idx and "
                    "user->seq before testing len > count or copy_to_user."
                ),
                "EINVAL": (
                    "The current record is already consumed before -EINVAL; "
                    "emit one terminal EINVAL_CURSOR_ADVANCED fault and never "
                    "retry or read again from that descriptor."
                ),
                "EFAULT": (
                    "The current record is already consumed before -EFAULT; "
                    "emit one terminal EFAULT_CURSOR_ADVANCED fault and never "
                    "retry or read again from that descriptor."
                ),
                "whySequenceAloneIsInsufficient": (
                    "A later sequence gap may expose the loss, but no later "
                    "record is guaranteed; the errno itself is terminal proof "
                    "of observer loss."
                ),
                "postIntentResult": "NO_PROOF_OBSERVER_AND_NO_EFFECT_REPLAY",
            },
            "macFalseSignature": {
                "priority": 3,
                "continuation": "-",
                "body": TYPE0_ABSENT,
                "exactCount": 1,
                "type1ExactCount": 0,
            },
            "macTrueSignature": {
                "priority": 3,
                "continuation": "-",
                "bodySuffix": MAC_TRUE_FAILURE,
                "sourceShape": (
                    "QDF hdd_err prepends a dynamic wlan/PID/module/function/"
                    "line prefix; the pinned source-unique literal is therefore "
                    "matched as the exact final suffix, not as the whole body."
                ),
                "exactCount": 1,
            },
        },
        "journalContract": {
            "recordSchema": JOURNAL_RECORD_SCHEMA,
            "events": list(JOURNAL_EVENTS),
            "chain": "sha256(canonical JSON record); first previous hash is zero",
            "payloadBindings": {
                "OBSERVER_ARMED": "trace header plus ARM frame SHA-256",
                "EFFECT_INTENT": "qualified proof-subject SHA-256",
                "EFFECT_DISPATCHED": "qualified exact-command SHA-256",
                "DRIVER_OUTCOME_BOUND": "bound driver-outcome receipt SHA-256",
                "CAPTURE_CLOSED": "complete raw trace SHA-256",
                "TERMINAL": "canonical WP2-4 property result SHA-256",
            },
            "noReplay": (
                "At and after durable EFFECT_INTENT the attempt is consumed. "
                "This H0 validator never returns dispatch authority; incomplete "
                "post-intent prefixes are observation, cleanup, and recovery only."
            ),
            "durableWriterImplemented": False,
            "rawCanonicalParserImplemented": False,
        },
        "boundConsumer": {
            "existingResultSchema": "a90-h24-wlan-property-observation-result-v1",
            "driverOutcomeReceiptSchema": DRIVER_OUTCOME_SCHEMA,
            "driverOutcomeReceiptTiming": "POST_EFFECT_CANONICAL_PUBLICATION",
            "driverOutcomeReceiptProducerImplemented": False,
            "qualifiedExpectationSchema": QUALIFIED_SCHEMA,
            "boundResultSchema": BOUND_RESULT_SCHEMA,
            "proofAxes": [
                "experimentProofOutcome",
                "deviceSafetyState",
                "workflowState",
            ],
            "promotion": "ALWAYS_FALSE_IN_THIS_H0_UNIT",
        },
        "negativeCorpus": [
            "bad magic/version/header reserved",
            "unknown/duplicate/misordered/trailing frame",
            "short/oversized/malformed /dev/kmsg record",
            "EPIPE/POLLERR/EINVAL/EFAULT/read fault",
            "sequence gap/duplicate/regression/overflow",
            "record-count or byte-cap exhaustion",
            "total framed-trace envelope exhaustion",
            "wrong priority/continuation/dictionary signature",
            "type-0 count not one or type-1 count not zero",
            "ARM/END run/qualification/observer/driver/close mismatch",
            "journal event/order/chain/payload mismatch",
            "driver-outcome receipt/result/run/boot/epoch laundering",
            "post-intent prefix never permits replay",
            "WP2-4 result/expectation/trace binding mismatch",
            "bool-for-int and extra/missing-key substitution",
        ],
        "sequencingConstraint": {
            "current": "WP2-5b.1 H0 trace core and state contract",
            "next": (
                "A separately reviewed runtime owner must integrate the exact "
                "/dev/kmsg open/poll/drain lifecycle and durable no-replace "
                "journal, then qualify measured caps and obtain fresh live authority."
            ),
            "deviceOrdinalsConsumed": 0,
        },
        "generatedDeterministically": True,
    }


def canonical_contract_text() -> str:
    return json.dumps(build_contract(), indent=2, sort_keys=True) + "\n"


def contract_sha256() -> str:
    return _sha256(canonical_contract_text().encode())


def validate_contract(value: Any) -> list[str]:
    try:
        expected = build_contract()
    except (OSError, ValueError):
        return ["PINNED_SOURCE_MODEL_UNAVAILABLE"]
    if not _strict_json_equal(value, expected):
        return ["PINNED_SEMANTIC_MISMATCH"]
    return []


def canonical_header_text() -> str:
    digest = bytes.fromhex(contract_sha256())
    digest_values = ", ".join(f"0x{byte:02x}" for byte in digest)
    return f"""/* Generated by a90_wp2_5b_kmsg_trace_v1.py; do not edit. */
#ifndef A90_WP2_5B_KMSG_CONTRACT_V1_H
#define A90_WP2_5B_KMSG_CONTRACT_V1_H

#include <stddef.h>
#include <stdint.h>

#define A90_WP2_5B_TRACE_VERSION {TRACE_VERSION}u
#define A90_WP2_5B_TRACE_HEADER_SIZE {TRACE_HEADER.size}u
#define A90_WP2_5B_FRAME_HEADER_SIZE {FRAME_HEADER.size}u
#define A90_WP2_5B_ARM_PAYLOAD_SIZE {ARM_PAYLOAD.size}u
#define A90_WP2_5B_FAULT_PAYLOAD_SIZE {FAULT_PAYLOAD.size}u
#define A90_WP2_5B_END_PAYLOAD_SIZE {END_PAYLOAD.size}u
#define A90_WP2_5B_KMSG_RECORD_MAX {KMSG_RECORD_MAX}u
#define A90_WP2_5B_KMSG_PRIORITY_MAX {KMSG_PRIORITY_MAX}u

#define A90_WP2_5B_FRAME_ARM {FRAME_ARM}u
#define A90_WP2_5B_FRAME_RECORD {FRAME_RECORD}u
#define A90_WP2_5B_FRAME_FAULT {FRAME_FAULT}u
#define A90_WP2_5B_FRAME_END {FRAME_END}u

#define A90_WP2_5B_FAULT_READ {FAULT_READ}u
#define A90_WP2_5B_FAULT_POLL {FAULT_POLL}u
#define A90_WP2_5B_FAULT_EPIPE {FAULT_EPIPE}u
#define A90_WP2_5B_FAULT_EINVAL {FAULT_EINVAL}u
#define A90_WP2_5B_FAULT_RECORD_FORMAT {FAULT_RECORD_FORMAT}u
#define A90_WP2_5B_FAULT_SEQUENCE {FAULT_SEQUENCE}u
#define A90_WP2_5B_FAULT_COUNT_CAP {FAULT_COUNT_CAP}u
#define A90_WP2_5B_FAULT_BYTE_CAP {FAULT_BYTE_CAP}u
#define A90_WP2_5B_FAULT_BOUNDARY {FAULT_BOUNDARY}u
#define A90_WP2_5B_FAULT_EFAULT {FAULT_EFAULT}u

#define A90_WP2_5B_TYPE0_ABSENT \"{TYPE0_ABSENT}\"
#define A90_WP2_5B_TYPE1_ABSENT \"{TYPE1_ABSENT}\"
#define A90_WP2_5B_MAC_TRUE_FAILURE \"{MAC_TRUE_FAILURE}\"

static const unsigned char a90_wp2_5b_trace_magic[8] = {{
    0x41, 0x39, 0x30, 0x4b, 0x35, 0x42, 0x31, 0x00
}};
static const unsigned char a90_wp2_5b_contract_sha256[32] = {{
    {digest_values}
}};

typedef int (*a90_wp2_5b_emit_fn)(void *opaque,
                                  const unsigned char *data,
                                  size_t length);

struct a90_wp2_5b_stream {{
    a90_wp2_5b_emit_fn emit;
    void *opaque;
    uint32_t record_count_cap;
    uint64_t record_byte_cap;
    uint32_t record_count;
    uint64_t record_bytes;
    uint64_t first_seq;
    uint64_t last_seq;
    int armed;
    int faulted;
    int ended;
}};

int a90_wp2_5b_stream_begin(struct a90_wp2_5b_stream *stream,
                            a90_wp2_5b_emit_fn emit,
                            void *opaque,
                            const unsigned char run_binding_sha256[32],
                            const unsigned char qualification_sha256[32],
                            const unsigned char observer_binary_sha256[32],
                            uint32_t record_count_cap,
                            uint64_t record_byte_cap);
int a90_wp2_5b_stream_add_record(struct a90_wp2_5b_stream *stream,
                                 const unsigned char *record,
                                 size_t length);
int a90_wp2_5b_stream_note_fault(struct a90_wp2_5b_stream *stream,
                                 uint32_t reason,
                                 int32_t os_errno,
                                 uint32_t poll_revents);
int a90_wp2_5b_stream_end(
    struct a90_wp2_5b_stream *stream,
    const unsigned char driver_init_epoch_sha256[32],
    const unsigned char capture_close_binding_sha256[32]);

#endif
"""


def _frame(frame_type: int, payload: bytes) -> bytes:
    return FRAME_HEADER.pack(frame_type, 0, 0, len(payload)) + payload


def _trace_prefix() -> bytes:
    return TRACE_HEADER.pack(
        TRACE_MAGIC,
        TRACE_VERSION,
        TRACE_HEADER.size,
        0,
    )


def _canonical_decimal(raw: bytes, maximum: int) -> int | None:
    if not raw or any(byte < 48 or byte > 57 for byte in raw):
        return None
    if len(raw) > 1 and raw[0] == 48:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    if value > maximum or str(value).encode() != raw:
        return None
    return value


def _canonical_extended_text(raw: bytes) -> bool:
    index = 0
    while index < len(raw):
        byte = raw[index]
        if byte != 92:
            if not 32 <= byte <= 126:
                return False
            index += 1
            continue
        if index + 4 > len(raw) or raw[index + 1] != ord("x"):
            return False
        digits = raw[index + 2 : index + 4]
        if any(value not in b"0123456789abcdef" for value in digits):
            return False
        decoded = int(digits, 16)
        if not (decoded < 32 or decoded >= 127 or decoded == 92):
            return False
        index += 4
    return True


def _canonical_extended_dictionary(raw: bytes) -> bool:
    if not raw:
        return True
    if not raw.endswith(b"\n"):
        return False
    lines = raw.split(b"\n")[:-1]
    if not lines or lines[0] == b"":
        return False
    for index, line in enumerate(lines):
        if line == b"":
            if index != len(lines) - 1:
                return False
            continue
        if not line.startswith(b" ") or not _canonical_extended_text(line[1:]):
            return False
        if line == b" " and index == len(lines) - 1:
            return False
    return True


def parse_kmsg_record(raw: Any) -> tuple[dict[str, Any] | None, list[str]]:
    findings: set[str] = set()
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= KMSG_RECORD_MAX:
        return None, ["KMSG_RECORD_SIZE_MISMATCH"]
    if b"\x00" in raw:
        return None, ["KMSG_RECORD_FORMAT_MISMATCH"]
    semi = raw.find(b";")
    if semi <= 0:
        return None, ["KMSG_RECORD_FORMAT_MISMATCH"]
    fields = raw[:semi].split(b",")
    if len(fields) != 4:
        return None, ["KMSG_RECORD_FORMAT_MISMATCH"]
    priority = _canonical_decimal(fields[0], KMSG_PRIORITY_MAX)
    sequence = _canonical_decimal(fields[1], UINT64_MAX)
    timestamp = _canonical_decimal(fields[2], UINT64_MAX)
    if priority is None or sequence is None or timestamp is None:
        findings.add("KMSG_RECORD_FORMAT_MISMATCH")
    if fields[3] not in (b"-", b"c"):
        findings.add("KMSG_RECORD_FORMAT_MISMATCH")
    body = raw[semi + 1 :]
    if not body or not body.endswith(b"\n"):
        findings.add("KMSG_RECORD_FORMAT_MISMATCH")
    first_newline = body.find(b"\n")
    if first_newline < 0:
        findings.add("KMSG_RECORD_FORMAT_MISMATCH")
        message = b""
        dictionary = b""
    else:
        message = body[:first_newline]
        dictionary = body[first_newline + 1 :]
        if not _canonical_extended_text(message) or not _canonical_extended_dictionary(
            dictionary
        ):
            findings.add("KMSG_RECORD_FORMAT_MISMATCH")
    if findings:
        return None, sorted(findings)
    assert priority is not None and sequence is not None and timestamp is not None
    return {
        "priority": priority,
        "facility": priority >> 3,
        "level": priority & 7,
        "sequence": sequence,
        "timestampUsec": timestamp,
        "continuation": fields[3].decode("ascii"),
        "body": message.decode("ascii"),
        "dictionaryPresent": bool(dictionary),
        "rawBytes": len(raw),
        "rawSha256": _sha256(raw),
    }, []


def validate_trace_expectation(value: Any) -> list[str]:
    findings: set[str] = set()
    if not isinstance(value, dict) or set(value) != TRACE_EXPECTATION_KEYS:
        return ["TRACE_EXPECTATION_SCHEMA_MISMATCH"]
    for key in TRACE_EXPECTATION_KEYS - {"recordCountCap", "recordByteCap"}:
        if not _is_sha256(value.get(key)):
            findings.add("TRACE_EXPECTATION_SCHEMA_MISMATCH")
    if (
        type(value.get("recordCountCap")) is not int
        or not 1 <= value["recordCountCap"] <= UINT32_MAX
        or type(value.get("recordByteCap")) is not int
        or not 1 <= value["recordByteCap"] <= UINT64_MAX
    ):
        findings.add("TRACE_EXPECTATION_SCHEMA_MISMATCH")
    try:
        current_contract_sha256 = contract_sha256()
    except (OSError, ValueError):
        findings.add("PINNED_SOURCE_MODEL_UNAVAILABLE")
    else:
        if value.get("contractSha256") != current_contract_sha256:
            findings.add("TRACE_CONTRACT_BINDING_MISMATCH")
    return sorted(findings)


def maximum_trace_bytes(trace_expectation: Any) -> int | None:
    """Return the exact largest framed trace admitted by the qualified caps."""
    if not isinstance(trace_expectation, dict):
        return None
    count_cap = trace_expectation.get("recordCountCap")
    byte_cap = trace_expectation.get("recordByteCap")
    if (
        type(count_cap) is not int
        or not 1 <= count_cap <= UINT32_MAX
        or type(byte_cap) is not int
        or not 1 <= byte_cap <= UINT64_MAX
    ):
        return None
    return (
        TRACE_HEADER.size
        + FRAME_HEADER.size
        + ARM_PAYLOAD.size
        + (count_cap * FRAME_HEADER.size)
        + byte_cap
        + FRAME_HEADER.size
        + FAULT_PAYLOAD.size
        + FRAME_HEADER.size
        + END_PAYLOAD.size
    )


def _empty_trace_summary(trace_sha: str) -> dict[str, Any]:
    return {
        "outcome": "NO_PROOF_OBSERVER",
        "traceSha256": trace_sha,
        "armReceiptSha256": ZERO_SHA256,
        "recordCount": 0,
        "recordBytes": 0,
        "firstSequence": None,
        "lastSequence": None,
        "faultCount": 0,
        "type0AbsentCount": 0,
        "type1AbsentCount": 0,
        "macTrueFailureCount": 0,
    }


def validate_trace(
    raw_trace: Any, trace_expectation: Any
) -> tuple[dict[str, Any], list[str]]:
    findings: set[str] = set(validate_trace_expectation(trace_expectation))
    summary = _empty_trace_summary(ZERO_SHA256)
    if not isinstance(raw_trace, bytes):
        findings.add("TRACE_HEADER_MISMATCH")
        return summary, sorted(findings)
    trace_cap = maximum_trace_bytes(trace_expectation)
    if trace_cap is None:
        findings.add("TRACE_EXPECTATION_SCHEMA_MISMATCH")
        return summary, sorted(findings)
    if len(raw_trace) > trace_cap:
        findings.add("TRACE_TOTAL_BYTE_CAP_EXHAUSTED")
        return summary, sorted(findings)
    trace_sha = _sha256(raw_trace)
    summary = _empty_trace_summary(trace_sha)
    if len(raw_trace) < TRACE_HEADER.size:
        findings.add("TRACE_HEADER_MISMATCH")
        return summary, sorted(findings)
    try:
        magic, version, header_size, reserved = TRACE_HEADER.unpack_from(raw_trace)
    except struct.error:
        findings.add("TRACE_HEADER_MISMATCH")
        return summary, sorted(findings)
    if (
        magic != TRACE_MAGIC
        or version != TRACE_VERSION
        or header_size != TRACE_HEADER.size
        or reserved != 0
    ):
        findings.add("TRACE_HEADER_MISMATCH")

    offset = TRACE_HEADER.size
    frame_index = 0
    armed = False
    faulted = False
    ended = False
    records: list[dict[str, Any]] = []
    record_bytes = 0
    fault_count = 0
    arm_receipt = ZERO_SHA256
    end_values: tuple[bytes, bytes, int, int, int, int] | None = None
    expected_count_cap = (
        trace_expectation.get("recordCountCap")
        if isinstance(trace_expectation, dict)
        and type(trace_expectation.get("recordCountCap")) is int
        else -1
    )
    expected_byte_cap = (
        trace_expectation.get("recordByteCap")
        if isinstance(trace_expectation, dict)
        and type(trace_expectation.get("recordByteCap")) is int
        else -1
    )
    while offset < len(raw_trace):
        if ended:
            findings.add("TRACE_TRAILING_BYTES")
            break
        if len(raw_trace) - offset < FRAME_HEADER.size:
            findings.add("TRACE_FRAME_TRUNCATED")
            break
        frame_start = offset
        try:
            frame_type, flags, reserved16, payload_len = FRAME_HEADER.unpack_from(
                raw_trace, offset
            )
        except struct.error:
            findings.add("TRACE_FRAME_TRUNCATED")
            break
        offset += FRAME_HEADER.size
        if flags != 0 or reserved16 != 0:
            findings.add("TRACE_FRAME_HEADER_MISMATCH")
        if payload_len > len(raw_trace) - offset:
            findings.add("TRACE_FRAME_TRUNCATED")
            break
        payload = raw_trace[offset : offset + payload_len]
        offset += payload_len

        if frame_type == FRAME_ARM:
            if frame_index != 0 or armed or payload_len != ARM_PAYLOAD.size:
                findings.add("TRACE_ARM_MISMATCH")
            else:
                try:
                    run, qualification, observer, contract, count_cap, byte_cap = (
                        ARM_PAYLOAD.unpack(payload)
                    )
                except struct.error:
                    findings.add("TRACE_ARM_MISMATCH")
                else:
                    expected = trace_expectation if isinstance(trace_expectation, dict) else {}
                    if (
                        run.hex() != expected.get("runBindingSha256")
                        or qualification.hex() != expected.get("qualificationSha256")
                        or observer.hex() != expected.get("observerBinarySha256")
                        or contract.hex() != expected.get("contractSha256")
                        or count_cap != expected.get("recordCountCap")
                        or byte_cap != expected.get("recordByteCap")
                    ):
                        findings.add("TRACE_ARM_BINDING_MISMATCH")
                    arm_receipt = _sha256(raw_trace[:offset])
                    armed = True
        elif frame_type == FRAME_RECORD:
            if not armed or faulted or ended:
                findings.add("TRACE_FRAME_ORDER_MISMATCH")
            parsed, record_findings = parse_kmsg_record(payload)
            findings.update(record_findings)
            if parsed is not None:
                if records:
                    previous = records[-1]["sequence"]
                    if previous == UINT64_MAX or parsed["sequence"] != previous + 1:
                        findings.add("TRACE_SEQUENCE_MISMATCH")
                records.append(parsed)
                record_bytes += len(payload)
                if len(records) > expected_count_cap:
                    findings.add("TRACE_RECORD_COUNT_CAP_EXHAUSTED")
                if record_bytes > expected_byte_cap:
                    findings.add("TRACE_RECORD_BYTE_CAP_EXHAUSTED")
        elif frame_type == FRAME_FAULT:
            if not armed or faulted or ended or payload_len != FAULT_PAYLOAD.size:
                findings.add("TRACE_FAULT_MISMATCH")
            else:
                try:
                    reason, _os_errno, _poll_revents, last_seq = FAULT_PAYLOAD.unpack(
                        payload
                    )
                except struct.error:
                    findings.add("TRACE_FAULT_MISMATCH")
                else:
                    expected_last = records[-1]["sequence"] if records else UINT64_MAX
                    if reason not in FAULT_NAMES or last_seq != expected_last:
                        findings.add("TRACE_FAULT_MISMATCH")
                fault_count += 1
                faulted = True
                findings.add("TRACE_REPORTED_FAULT")
        elif frame_type == FRAME_END:
            if not armed or ended or payload_len != END_PAYLOAD.size:
                findings.add("TRACE_END_MISMATCH")
            else:
                try:
                    end_values = END_PAYLOAD.unpack(payload)
                except struct.error:
                    findings.add("TRACE_END_MISMATCH")
                ended = True
        else:
            findings.add("TRACE_UNKNOWN_FRAME")
        frame_index += 1

    if not armed:
        findings.add("TRACE_ARM_MISSING")
    if not ended or end_values is None:
        findings.add("TRACE_END_MISSING")
    else:
        driver, close_binding, count, byte_count, first_seq, last_seq = end_values
        expected = trace_expectation if isinstance(trace_expectation, dict) else {}
        derived_first = records[0]["sequence"] if records else UINT64_MAX
        derived_last = records[-1]["sequence"] if records else UINT64_MAX
        if (
            driver.hex() != expected.get("driverInitEpochSha256")
            or close_binding.hex() != expected.get("captureCloseBindingSha256")
            or count != len(records)
            or byte_count != record_bytes
            or first_seq != derived_first
            or last_seq != derived_last
        ):
            findings.add("TRACE_END_BINDING_MISMATCH")

    type0 = sum(
        item["priority"] == 3
        and item["continuation"] == "-"
        and item["body"] == TYPE0_ABSENT
        and item["dictionaryPresent"] is False
        for item in records
    )
    type1 = sum(
        item["priority"] == 3
        and item["continuation"] == "-"
        and item["body"] == TYPE1_ABSENT
        and item["dictionaryPresent"] is False
        for item in records
    )
    mac_true = sum(
        item["priority"] == 3
        and item["continuation"] == "-"
        and item["body"].endswith(MAC_TRUE_FAILURE)
        and item["dictionaryPresent"] is False
        for item in records
    )
    summary.update(
        armReceiptSha256=arm_receipt,
        recordCount=len(records),
        recordBytes=record_bytes,
        firstSequence=records[0]["sequence"] if records else None,
        lastSequence=records[-1]["sequence"] if records else None,
        faultCount=fault_count,
        type0AbsentCount=type0,
        type1AbsentCount=type1,
        macTrueFailureCount=mac_true,
    )
    if not findings and not faulted:
        summary["outcome"] = "VALID_COMPLETE"
    return summary, sorted(findings)


_WP2_MODULE: Any = None


def _load_wp2_module() -> Any:
    global _WP2_MODULE
    if _WP2_MODULE is not None:
        return _WP2_MODULE
    _pinned_receipts()
    path = ROOT / WP2_GENERATOR_REL
    spec = importlib.util.spec_from_file_location("a90_wp2_4_bound", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load pinned WP2-4 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _WP2_MODULE = module
    return module


def _run_binding_digest(binding_projection: Any) -> str:
    return _sha256(_canonical_bytes(binding_projection))


def trace_expectation_from_qualified(value: Any) -> dict[str, Any]:
    return {
        key: value[key]
        for key in sorted(TRACE_EXPECTATION_KEYS)
        if isinstance(value, dict) and key in value
    }


def validate_qualified_expectation(value: Any) -> list[str]:
    findings: set[str] = set()
    if not isinstance(value, dict) or set(value) != QUALIFIED_KEYS:
        return ["QUALIFIED_EXPECTATION_SCHEMA_MISMATCH"]
    if value.get("schema") != QUALIFIED_SCHEMA:
        findings.add("QUALIFIED_EXPECTATION_SCHEMA_MISMATCH")
    findings.update(validate_trace_expectation(trace_expectation_from_qualified(value)))
    for key in (
        "effectCommandSha256",
        "proofSubjectSha256",
    ):
        if not _is_sha256(value.get(key)):
            findings.add("QUALIFIED_EXPECTATION_SCHEMA_MISMATCH")
    try:
        wp2 = _load_wp2_module()
    except (OSError, ValueError, RuntimeError, ImportError):
        findings.add("PINNED_SOURCE_MODEL_UNAVAILABLE")
        return sorted(findings)
    prop = value.get("propertyExpectation")
    if (
        not isinstance(prop, dict)
        or set(prop) != wp2.QUALIFIED_EXPECTATION_KEYS
        or not isinstance(prop.get("bindingProjection"), dict)
        or set(prop["bindingProjection"]) != wp2.QUALIFIED_BINDING_KEYS
    ):
        findings.add("QUALIFIED_EXPECTATION_SCHEMA_MISMATCH")
        return sorted(findings)
    try:
        expected_run_binding = _run_binding_digest(prop["bindingProjection"])
    except (TypeError, ValueError):
        findings.add("QUALIFIED_EXPECTATION_SCHEMA_MISMATCH")
        return sorted(findings)
    if (
        value.get("runBindingSha256") != expected_run_binding
        or value.get("qualificationSha256")
        != prop["bindingProjection"].get("qualificationSha256")
        or value.get("observerBinarySha256")
        != prop["bindingProjection"].get("observerSha256")
    ):
        findings.add("QUALIFIED_BINDING_MISMATCH")
    return sorted(findings)


def journal_record_digest(record: dict[str, Any]) -> str:
    return _sha256(_canonical_bytes(record))


def validate_journal(
    records: Any,
    run_binding_sha256: Any,
    expected_payloads: dict[str, str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    findings: set[str] = set()
    if not _is_sha256(run_binding_sha256):
        findings.add("JOURNAL_RUN_BINDING_MISMATCH")
    expected_prefix = (
        set(JOURNAL_EVENTS[: min(len(records), len(JOURNAL_EVENTS))])
        if isinstance(records, list)
        else set()
    )
    if (
        not isinstance(expected_payloads, dict)
        or set(expected_payloads) != expected_prefix
        or any(
            not _is_sha256(expected_payloads.get(event))
            for event in expected_prefix
        )
    ):
        findings.add("JOURNAL_PAYLOAD_EXPECTATION_MISMATCH")
        expected_payloads = {}
    if not isinstance(records, list) or len(records) > len(JOURNAL_EVENTS):
        records = [] if not isinstance(records, list) else records
        findings.add("JOURNAL_SCHEMA_MISMATCH")
    previous = ZERO_SHA256
    events: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != JOURNAL_RECORD_KEYS:
            findings.add("JOURNAL_SCHEMA_MISMATCH")
            continue
        valid_shape = (
            record.get("schema") != JOURNAL_RECORD_SCHEMA
            or type(record.get("sequence")) is not int
            or record.get("sequence") != index
            or record.get("event")
            != (JOURNAL_EVENTS[index] if index < len(JOURNAL_EVENTS) else None)
            or record.get("runBindingSha256") != run_binding_sha256
            or record.get("previousRecordSha256") != previous
            or not _is_sha256(record.get("payloadSha256"))
        )
        if valid_shape:
            findings.add("JOURNAL_SCHEMA_MISMATCH")
        event = record.get("event")
        if isinstance(event, str):
            events.append(event)
        if (
            isinstance(event, str)
            and event in expected_payloads
            and record.get("payloadSha256") != expected_payloads[event]
        ):
            findings.add("JOURNAL_PAYLOAD_BINDING_MISMATCH")
        try:
            previous = journal_record_digest(record)
        except (TypeError, ValueError):
            findings.add("JOURNAL_SCHEMA_MISMATCH")
            previous = ZERO_SHA256
    effect_consumed = "EFFECT_INTENT" in events
    terminal = events == list(JOURNAL_EVENTS)
    if terminal and not findings:
        state = "TERMINAL_BOUND"
        mode = "TERMINAL_READ_ONLY"
    elif effect_consumed:
        state = "NO_PROOF_OBSERVER"
        mode = "OBSERVE_CLEANUP_RECOVERY_ONLY"
    else:
        state = "PRE_EFFECT_INCOMPLETE"
        mode = "NO_LIVE_ACTION_AUTHORIZED"
    return {
        "state": state,
        "events": events,
        "journalChainSha256": previous,
        "effectConsumed": effect_consumed,
        "effectReplayAllowed": False,
        "reconciliationMode": mode,
    }, sorted(findings)


def make_journal_record(
    sequence: int,
    event: str,
    run_binding_sha256: str,
    previous_record_sha256: str,
    payload_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": JOURNAL_RECORD_SCHEMA,
        "sequence": sequence,
        "event": event,
        "runBindingSha256": run_binding_sha256,
        "previousRecordSha256": previous_record_sha256,
        "payloadSha256": payload_sha256,
    }


def build_journal(
    run_binding_sha256: str,
    payloads: dict[str, str],
    length: int = len(JOURNAL_EVENTS),
) -> list[dict[str, Any]]:
    if type(length) is not int or not 0 <= length <= len(JOURNAL_EVENTS):
        raise ValueError("invalid journal prefix length")
    records = []
    previous = ZERO_SHA256
    for sequence, event in enumerate(JOURNAL_EVENTS[:length]):
        record = make_journal_record(
            sequence,
            event,
            run_binding_sha256,
            previous,
            payloads[event],
        )
        records.append(record)
        previous = journal_record_digest(record)
    return records


def _property_result_validation(
    value: Any, property_expectation: Any
) -> list[str]:
    try:
        wp2 = _load_wp2_module()
    except (OSError, ValueError, RuntimeError, ImportError):
        return ["PINNED_SOURCE_MODEL_UNAVAILABLE"]
    if not isinstance(value, dict):
        return ["PROPERTY_RESULT_SCHEMA_MISMATCH"]
    terminal = value.get("terminal")
    try:
        if terminal == "PROPERTY_ABSENT_PROVED":
            return wp2.validate_property_absent_result(value, property_expectation)
        if terminal == "PROPERTY_FINITE_SEED_PROVED":
            return wp2.validate_property_finite_seed_result(value, property_expectation)
    except (TypeError, ValueError, KeyError, OverflowError, AttributeError):
        return ["PROPERTY_VALIDATOR_EXCEPTION"]
    return ["PROPERTY_TERMINAL_MISMATCH"]


def validate_driver_outcome_receipt(
    value: Any,
    qualified_expectation: Any,
    property_result: Any,
) -> list[str]:
    findings: set[str] = set()
    if validate_qualified_expectation(qualified_expectation):
        findings.add("DRIVER_OUTCOME_RECEIPT_QUALIFICATION_REJECTED")
    property_expectation = (
        qualified_expectation.get("propertyExpectation")
        if isinstance(qualified_expectation, dict)
        else None
    )
    if _property_result_validation(property_result, property_expectation):
        findings.add("DRIVER_OUTCOME_RECEIPT_RESULT_REJECTED")
    if not isinstance(value, dict) or set(value) != DRIVER_OUTCOME_KEYS:
        findings.add("DRIVER_OUTCOME_RECEIPT_SCHEMA_MISMATCH")
        return sorted(findings)
    if (
        value.get("schema") != DRIVER_OUTCOME_SCHEMA
        or type(value.get("wlanOutcome")) is not str
        or value.get("wlanOutcome") not in DRIVER_OUTCOMES
        or any(
            not _is_sha256(value.get(key))
            for key in DRIVER_OUTCOME_KEYS
            - {"schema", "wlanOutcome"}
        )
    ):
        findings.add("DRIVER_OUTCOME_RECEIPT_SCHEMA_MISMATCH")
    qualified = qualified_expectation if isinstance(qualified_expectation, dict) else {}
    property_expectation = qualified.get("propertyExpectation")
    projection = (
        property_expectation.get("bindingProjection")
        if isinstance(property_expectation, dict)
        else {}
    )
    if (
        value.get("runBindingSha256") != qualified.get("runBindingSha256")
        or value.get("driverInitEpochSha256")
        != qualified.get("driverInitEpochSha256")
        or value.get("bootIdSha256") != projection.get("bootIdSha256")
    ):
        findings.add("DRIVER_OUTCOME_RECEIPT_BINDING_MISMATCH")
    effect = (
        property_result.get("macProvisioningEffect")
        if isinstance(property_result, dict)
        else None
    )
    if (
        not isinstance(effect, dict)
        or value.get("wlanOutcome") != effect.get("wlanOutcome")
    ):
        findings.add("DRIVER_OUTCOME_RECEIPT_RESULT_MISMATCH")
    return sorted(findings)


def build_bound_result(
    raw_trace: Any,
    property_result: Any,
    qualified_expectation: Any,
    driver_outcome_receipt: Any,
    journal_records: Any,
) -> dict[str, Any]:
    qualified_findings = validate_qualified_expectation(qualified_expectation)
    findings: set[str] = set(qualified_findings)
    trace_expectation = trace_expectation_from_qualified(qualified_expectation)
    trace, trace_findings = validate_trace(raw_trace, trace_expectation)
    findings.update(trace_findings)
    property_expectation = (
        qualified_expectation.get("propertyExpectation")
        if isinstance(qualified_expectation, dict)
        else None
    )
    property_findings = _property_result_validation(
        property_result, property_expectation
    )
    if property_findings:
        findings.add("PROPERTY_RESULT_REJECTED")
        findings.update(f"PROPERTY::{item}" for item in property_findings)
    driver_receipt_findings = validate_driver_outcome_receipt(
        driver_outcome_receipt, qualified_expectation, property_result
    )
    findings.update(driver_receipt_findings)
    try:
        driver_receipt_sha = (
            _sha256(_canonical_bytes(driver_outcome_receipt))
            if isinstance(driver_outcome_receipt, dict)
            else ZERO_SHA256
        )
    except (TypeError, ValueError):
        driver_receipt_sha = ZERO_SHA256
        findings.add("DRIVER_OUTCOME_RECEIPT_SCHEMA_MISMATCH")

    try:
        property_sha = (
            _sha256(_canonical_bytes(property_result))
            if isinstance(property_result, dict)
            else ZERO_SHA256
        )
    except (TypeError, ValueError):
        property_sha = ZERO_SHA256
        findings.add("PROPERTY_RESULT_SCHEMA_MISMATCH")
    raw_trace_sha = trace.get("traceSha256", ZERO_SHA256)
    expected_payloads = {
        "OBSERVER_ARMED": trace.get("armReceiptSha256", ZERO_SHA256),
        "EFFECT_INTENT": (
            qualified_expectation.get("proofSubjectSha256", ZERO_SHA256)
            if isinstance(qualified_expectation, dict)
            else ZERO_SHA256
        ),
        "EFFECT_DISPATCHED": (
            qualified_expectation.get("effectCommandSha256", ZERO_SHA256)
            if isinstance(qualified_expectation, dict)
            else ZERO_SHA256
        ),
        "DRIVER_OUTCOME_BOUND": (
            driver_receipt_sha
        ),
        "CAPTURE_CLOSED": raw_trace_sha,
        "TERMINAL": property_sha,
    }
    run_binding = (
        qualified_expectation.get("runBindingSha256", ZERO_SHA256)
        if isinstance(qualified_expectation, dict)
        else ZERO_SHA256
    )
    journal_prefix_payloads = (
        {
            event: expected_payloads[event]
            for event in JOURNAL_EVENTS[: min(len(journal_records), len(JOURNAL_EVENTS))]
        }
        if isinstance(journal_records, list)
        else {}
    )
    journal, journal_findings = validate_journal(
        journal_records, run_binding, journal_prefix_payloads
    )
    findings.update(journal_findings)

    decision = None
    effect = None
    if isinstance(property_result, dict):
        effect = property_result.get("macProvisioningEffect")
        if isinstance(effect, dict):
            decision = effect.get("decision")
    proof = "NO_PROOF_OBSERVER"
    all_bound = (
        not findings
        and trace.get("outcome") == "VALID_COMPLETE"
        and journal.get("state") == "TERMINAL_BOUND"
    )
    if all_bound and decision == "MAC_PROVISION_FALSE_PROVED_EXACT_RUN":
        if (
            trace.get("type0AbsentCount") == 1
            and trace.get("type1AbsentCount") == 0
            and trace.get("macTrueFailureCount") == 0
            and effect.get("wlanOutcome") == "WLAN0_UP_EXACT_DRIVER"
            and effect.get("provisionedAbsenceAtDriverLookup")
            == "TYPE0_ABSENT_EXACT_BOUND_DRIVER_INIT"
        ):
            proof = decision
        else:
            findings.add("MAC_KMSG_SIGNATURE_MISMATCH")
    elif all_bound and decision == "MAC_PROVISION_TRUE_PROVED_EXACT_RUN":
        if (
            trace.get("macTrueFailureCount") == 1
            and effect.get("wlanOutcome") == "MAC_INIT_FAILED_EXACT_SIGNATURE"
        ):
            proof = decision
        else:
            findings.add("MAC_KMSG_SIGNATURE_MISMATCH")
    elif all_bound and decision not in (
        "MAC_PROVISION_VALUE_UNRESOLVED",
        "NO_PROOF_OBSERVER",
    ):
        findings.add("MAC_DECISION_MISMATCH")

    if findings:
        proof = "NO_PROOF_OBSERVER"
    safety_terminal_bound = (
        not qualified_findings
        and not property_findings
        and not driver_receipt_findings
        and not journal_findings
        and journal.get("state") == "TERMINAL_BOUND"
    )
    if safety_terminal_bound:
        device_safety = property_result["deviceSafetyState"]
        workflow = property_result["workflowState"]
    else:
        device_safety = "RECOVERY_REQUIRED"
        workflow = "RECOVERY_PARKED"
    try:
        current_contract_sha256 = contract_sha256()
    except (OSError, ValueError):
        current_contract_sha256 = ZERO_SHA256
        findings.add("PINNED_SOURCE_MODEL_UNAVAILABLE")
    bindings = {
        "contractSha256": current_contract_sha256,
        "runBindingSha256": run_binding,
        "qualificationSha256": trace_expectation.get(
            "qualificationSha256", ZERO_SHA256
        ),
        "driverInitEpochSha256": trace_expectation.get(
            "driverInitEpochSha256", ZERO_SHA256
        ),
        "driverOutcomeReceiptSha256": (
            driver_receipt_sha
        ),
        "captureCloseBindingSha256": trace_expectation.get(
            "captureCloseBindingSha256", ZERO_SHA256
        ),
        "kmsgTraceSha256": raw_trace_sha,
        "propertyResultSha256": property_sha,
        "journalChainSha256": journal["journalChainSha256"],
    }
    return {
        "schema": BOUND_RESULT_SCHEMA,
        "bindings": bindings,
        "trace": trace,
        "journal": journal,
        "experimentProofOutcome": proof,
        "deviceSafetyState": device_safety,
        "workflowState": workflow,
        "generationPromotionEligible": False,
        "authority": {
            "tier": "H0",
            "deviceContact": False,
            "liveExecutionAuthorized": False,
            "candidateEligible": False,
        },
        "findings": sorted(findings),
    }


def validate_bound_result(
    value: Any,
    raw_trace: Any,
    property_result: Any,
    qualified_expectation: Any,
    driver_outcome_receipt: Any,
    journal_records: Any,
) -> list[str]:
    if not isinstance(value, dict) or set(value) != BOUND_RESULT_KEYS:
        return ["BOUND_RESULT_SCHEMA_MISMATCH"]
    expected = build_bound_result(
        raw_trace,
        property_result,
        qualified_expectation,
        driver_outcome_receipt,
        journal_records,
    )
    if not _strict_json_equal(value, expected):
        return ["BOUND_RESULT_MISMATCH"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check-contract", type=Path, metavar="PATH")
    group.add_argument("--write-contract", type=Path, nargs="?", const=DEFAULT_CONTRACT)
    group.add_argument("--check-header", type=Path, metavar="PATH")
    group.add_argument("--write-header", type=Path, nargs="?", const=DEFAULT_HEADER)
    args = parser.parse_args()
    if args.check_contract is not None:
        if args.check_contract.read_text() != canonical_contract_text():
            raise SystemExit(f"contract drift: {args.check_contract}")
        return 0
    if args.write_contract is not None:
        args.write_contract.parent.mkdir(parents=True, exist_ok=True)
        args.write_contract.write_text(canonical_contract_text())
        return 0
    if args.check_header is not None:
        if args.check_header.read_text() != canonical_header_text():
            raise SystemExit(f"header drift: {args.check_header}")
        return 0
    if args.write_header is not None:
        args.write_header.parent.mkdir(parents=True, exist_ok=True)
        args.write_header.write_text(canonical_header_text())
        return 0
    print(canonical_contract_text(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
