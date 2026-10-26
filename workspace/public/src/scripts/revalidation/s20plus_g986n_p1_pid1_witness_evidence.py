#!/usr/bin/env python3
"""H0 consumer for the S20+ P1 same-boot PID1 witness (raw-input schema v4).

A positive result is controlled-experiment evidence under ASSUMPTIONS, not an
attestation against a hostile root. The fixed producer reads getpid/procfs and
writes before execing resident init without forking. Its text fields are not
intrinsically authenticated by kmsg: the exact transferred candidate and its
reviewed execution path provide that attribution.

The predicate requires a contiguous prefix beginning at sequence zero, a
facility-0 kernel /init handover record, and the witness as the first nonzero-
facility record. The target kernel does not let /dev/kmsg writers choose
facility zero. These facts constrain record ordering; they do not independently
prove that no silent userspace process existed. The previous init-prefix
predicate was refuted by an evicted head and a missing middle range, both kept
as regression fixtures.

Input is the exact bounded raw file, including a partial trailing record. This
consumer verifies its size/digest and derives the aligned prefix itself. A
separately supplied prefix cannot stand in for that raw file. Only the prefix
is interpreted; the original bytes remain private and unchanged. Acquisition
failure and parsing failure are distinct, and missing-prefix evidence supports
neither a positive result nor a claim that the witness never ran.

FIFO eviction can remove sequence zero while retaining a later witness. Actual
same-boot retention remains a device-only unknown. The production fixed reader
returns bounded prefixes, not drain proof; the `complete` input class is kept
for explicit complete fixtures and cannot be inferred from host-side silence.

Android return, rollback and terminal health remain separate F1 outcomes. This
module reads local files only and grants no device authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

SCHEMA = "s20plus_g986n_p1_pid1_witness_evidence_v4"
ATTESTATION_SCHEMA = "s20plus_g986n_p1_pid1_witness_attestation_v4"

# No device observation capability is active in this module or anywhere else yet.
DEVICE_OBSERVATION_ACTIVE = False

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}

# Must equal build_s20plus_g986n_p1_pid1_witness_h0.CANDIDATE_ID. Duplicated
# rather than imported so this consumer has no dependency on a builder that
# reaches magiskboot and the private artifact tree; the focused tests assert the
# two constants are equal.
CANDIDATE_ID = "6f3a1c7d0b45e29840d17ac6e5b93f21"

# The exact prepared artifacts. A caller-declared candidate id is a label; these
# are the bytes the F1 transfer journal records as having been written to `boot`,
# and the attestation must name them. Rotated with the producer source.
CANDIDATE_BOOT_SHA256 = "9e6ce6689d8f36693c83b9a7137bb6df39754b63699c634a8dc1cb71baa3a2cf"
CANDIDATE_AP_SHA256 = "2d80698a6cbcf2690cc4ae9a9ee70934df0f671102645e60f040d525b184e70b"

MAGIC = "S20PLUS_P1_PID1_WITNESS_V1"
STAGE = "PRE_EXEC_HANDOFF"
UNAVAILABLE = "unavailable"
FIELD_ORDER = ("cand", "pid", "procself", "pidns", "bootid", "stage")

PID_NS_INIT_INO = 0xEFFFFFFC
EXPECTED_PIDNS = f"pid:[{PID_NS_INIT_INO}]"
EXPECTED_PID = "0000000001"
EXPECTED_PROCSELF = "1"

# The kernel's own facility for its own records. devkmsg_write() cannot be made
# to emit it, so it partitions the ring by origin.
KERNEL_FACILITY = 0
# What devkmsg_write() assigns a userspace write with no facility prefix.
USER_FACILITY = 1

# Printed by run_init_process() with pr_info immediately before do_execve. This
# is a kernel record and it is load bearing: it is the point after which exactly
# one userspace process exists.
KERNEL_INIT_MARKER = re.compile(r"^Run (?P<path>\S+) as init process$")
EXPECTED_INIT_PATH = "/init"

# Counted for corroboration and reported. Nothing turns on them: a body prefix
# identifies no process and its absence bounds no window.
DOWNSTREAM_MARKERS = ("magiskinit: ", "init: ")

CAPTURE_SOURCE = "live-dev-kmsg"
# The only reader outcome that can carry a capture to PROVED. Every other value
# names a bounded read that stopped early, and an early stop cannot support a
# claim about the whole boot.
# Acquisition statuses, mirrored from the reader. Only these five leave a
# contiguous prefix beginning at the ring head, and only `complete` additionally
# supports an ABSENCE claim - host-side silence is not a proved device drain.
COMPLETE_READER_STATUS = "complete"
# Both of these can carry a capture to PROVED, and the reason the second one can
# is worth being explicit about: the predicate asks whether the witness record is
# the first userspace-facility record of the boot, and every record that could
# refute that has a lower sequence number. A contiguous prefix starting at
# sequence 0 that contains the witness therefore contains everything that could
# refute it. What a prefix cannot support is an ABSENCE claim, which is why
# `witness-record-absent` is reachable only from a `complete` capture.
ATTRIBUTING_READER_STATUSES = (
    COMPLETE_READER_STATUS,
    "idle-stop",
    "deadline",
    "byte-limit",
    "record-limit",
)
READER_STATUSES = ATTRIBUTING_READER_STATUSES + ("acquisition-failed", "unreadable")

# Parse statuses, which describe the record-aligned DERIVATIVE of the raw
# capture rather than the acquisition. They are reported separately because a
# framing failure is not an acquisition failure and must not be renamed as one.
USABLE_PARSE_STATUSES = ("record-aligned", "trailing-partial-record")
PARSE_STATUSES = USABLE_PARSE_STATUSES + ("sequence-gap", "unparsable")

CAPTURE_CONTRACT = {
    "source": CAPTURE_SOURCE,
    "node": "/dev/kmsg",
    "reader": "s20plus_g986n_p1_pid1_kmsg_observer.py (dormant)",
    "open": "a fresh open starts at log_first_seq, so the capture begins at the "
    "oldest record still in the ring",
    "read": "records are concatenated in the order read, unmodified, until a "
    "bound stops the read; -EPIPE leaves a sequence gap, which is reported and "
    "never repaired",
    "raw_first": "the exact bounded bytes are published before any parse; the "
    "evaluated capture is a record-aligned prefix of them, named by its offset "
    "and length and bound to the raw digest",
    "completeness": "PROVED requires a bounded acquisition status, a usable "
    "parse status, first_seq=0, a contiguous sequence, and a derivative that "
    "spans the raw capture",
    "silence_is_not_a_drain": "host-side silence is idle-stop, not complete; "
    "only complete supports an absence claim",
    "same_session_reads": [
        "/proc/sys/kernel/random/boot_id",
        "the exact-target identity the routine D0 already reads",
    ],
    "publication": "atomic no-clobber mode-0400 private raw file, published "
    "before any parse, with its size and SHA-256 carried in the attestation",
    "privacy": "the capture is private raw evidence; this consumer publishes "
    "counts, the candidate id, and a digest of the boot id - never log bytes",
    "not_this_node": "/proc/last_kmsg is a different, retained, previous-boot "
    "surface owned by the dormant last_kmsg Record-Format D0. That capability "
    "decides record formats and lends no authority to read this one.",
}

# `<prifac>,<seq>,<ts_usec>,<flag>;` - exactly what msg_print_ext_header() emits
# on this kernel. Further comma-separated header fields a newer kernel might add
# are tolerated and ignored.
RECORD_HEADER = re.compile(r"^(\d{1,10}),(\d{1,20}),(\d{1,20}),([^,;]*)((?:,[^;]*)*);")
WITNESS_GRAMMAR = re.compile(
    r"^"
    + re.escape(MAGIC)
    + r";cand=(?P<cand>[0-9a-zA-Z:\[\].\-_]{1,64})"
    r";pid=(?P<pid>[0-9]{10})"
    r";procself=(?P<procself>[0-9a-zA-Z:\[\].\-_]{1,64})"
    r";pidns=(?P<pidns>[0-9a-zA-Z:\[\].\-_]{1,64})"
    r";bootid=(?P<bootid>[0-9a-zA-Z:\[\].\-_]{1,64})"
    r";stage=(?P<stage>[0-9a-zA-Z:\[\].\-_]{1,64})$"
)
BOOT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA256_TEXT = re.compile(r"^[0-9a-f]{64}$")
CANDIDATE_ID_TEXT = re.compile(r"^[0-9a-f]{32}$")

ATTESTATION_KEYS = {
    "schema",
    "source",
    "target",
    "candidate_id",
    "candidate_boot_sha256",
    "candidate_ap_sha256",
    "boot_id",
    # The raw capture: the exact bounded bytes the transport delivered, which
    # are published before anything parses them.
    "raw_sha256",
    "raw_size",
    # The evaluated derivative: a record-aligned prefix of those bytes, named by
    # its own offset and length so it cannot be presented as the raw capture.
    "capture_sha256",
    "capture_size",
    "aligned_offset",
    "trailing_partial_bytes",
    "acquisition_status",
    "parse_status",
    "reader_first_seq",
    "reader_last_seq",
    "reader_records",
}


class EvidenceError(ValueError):
    """A refusal that is a verdict, not a crash."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


MAX_RAW_BYTES = 8 * 1024 * 1024


def read_regular_bytes(path: Path, label: str) -> bytes:
    maximum = 16384 if label == "attestation" else MAX_RAW_BYTES
    if path.is_symlink():
        raise EvidenceError("indirect-input", label)
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 <= before.st_size <= maximum
                or path.resolve(strict=True) != path.absolute()):
            raise EvidenceError("indirect-input", label)
        data = bytearray()
        while len(data) <= maximum:
            chunk = os.read(descriptor, min(65536, maximum + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(descriptor)
        if (len(data) != before.st_size or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise EvidenceError("changed-input", label)
        return bytes(data)
    finally:
        os.close(descriptor)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("malformed-attestation", "duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise EvidenceError("malformed-attestation", "non-finite value")


def parse_attestation(data: bytes) -> dict[str, Any]:
    try:
        attestation = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceError("malformed-attestation", str(error)) from error
    if not isinstance(attestation, dict):
        raise EvidenceError("malformed-attestation", "not an object")
    if set(attestation) != ATTESTATION_KEYS:
        raise EvidenceError("malformed-attestation", "unexpected key set")
    if attestation["schema"] != ATTESTATION_SCHEMA:
        raise EvidenceError("malformed-attestation", "schema")
    if attestation["source"] != CAPTURE_SOURCE:
        # /proc/last_kmsg, a dmesg text dump or a hand-assembled file are all
        # different evidence classes and none of them can reach PROVED here.
        raise EvidenceError("unsupported-capture-source", str(attestation["source"]))
    if attestation["target"] != TARGET:
        raise EvidenceError("target-mismatch", "attested target is not this exact S20+")
    for name, pattern in (
        ("candidate_id", CANDIDATE_ID_TEXT),
        ("boot_id", BOOT_ID),
        ("capture_sha256", SHA256_TEXT),
        ("raw_sha256", SHA256_TEXT),
        ("candidate_boot_sha256", SHA256_TEXT),
        ("candidate_ap_sha256", SHA256_TEXT),
    ):
        value = attestation[name]
        if not isinstance(value, str) or pattern.fullmatch(value) is None:
            raise EvidenceError("malformed-attestation", name)
    for name in (
        "capture_size",
        "raw_size",
        "aligned_offset",
        "trailing_partial_bytes",
        "reader_first_seq",
        "reader_last_seq",
        "reader_records",
    ):
        value = attestation[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise EvidenceError("malformed-attestation", name)
    if attestation["acquisition_status"] not in READER_STATUSES:
        raise EvidenceError("malformed-attestation", "acquisition_status")
    if attestation["parse_status"] not in PARSE_STATUSES:
        raise EvidenceError("malformed-attestation", "parse_status")
    # The derivative must be a prefix of the raw capture and must account for
    # every raw byte, so a capture cannot quietly be larger than what was read.
    if attestation["aligned_offset"] != 0:
        raise EvidenceError("malformed-attestation", "aligned_offset")
    if (
        attestation["capture_size"] + attestation["trailing_partial_bytes"]
        != attestation["raw_size"]
    ):
        raise EvidenceError("capture-binding-mismatch", "derivative does not span the raw capture")
    if attestation["candidate_id"] != CANDIDATE_ID:
        raise EvidenceError("candidate-id-mismatch", "attested candidate is not this one")
    # The identity that matters is the bytes, not the label.
    if attestation["candidate_boot_sha256"] != CANDIDATE_BOOT_SHA256:
        raise EvidenceError("candidate-artifact-mismatch", "boot.img")
    if attestation["candidate_ap_sha256"] != CANDIDATE_AP_SHA256:
        raise EvidenceError("candidate-artifact-mismatch", "AP.tar.md5")
    return attestation


def unescape_body(body: str) -> str:
    """Undo the `\\xNN` escaping msg_print_ext_body applies.

    The witness record is pure printable ASCII, so any escape inside it means the
    bytes on the device were not the bytes this candidate writes.
    """
    out: list[str] = []
    index = 0
    while index < len(body):
        if body[index] == "\\":
            if body[index : index + 2] != "\\x" or len(body) < index + 4:
                raise EvidenceError("malformed-capture", "truncated escape")
            try:
                out.append(chr(int(body[index + 2 : index + 4], 16)))
            except ValueError as error:
                raise EvidenceError("malformed-capture", "bad escape") from error
            index += 4
        else:
            out.append(body[index])
            index += 1
    return "".join(out)


def parse_capture(data: bytes) -> list[dict[str, Any]]:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as error:
        # /dev/kmsg escapes everything outside printable ASCII, so a non-ASCII
        # byte means this is not a /dev/kmsg capture.
        raise EvidenceError("malformed-capture", str(error)) from error
    if text and not text.endswith("\n"):
        # Every record the kernel hands a reader is newline terminated, so a
        # capture that does not end on one lost bytes on the way here.
        raise EvidenceError("truncated-capture", "capture does not end on a record boundary")
    records: list[dict[str, Any]] = []
    for number, line in enumerate(text.split("\n")):
        if line == "":
            continue
        if line.startswith(" "):
            # A dictionary continuation of the preceding record. Its content is
            # never evidence here, but an orphan one means the capture is not
            # record-aligned.
            if not records:
                raise EvidenceError("malformed-capture", f"orphan dict line {number}")
            records[-1]["dict_lines"] += 1
            continue
        match = RECORD_HEADER.match(line)
        if match is None:
            raise EvidenceError("malformed-capture", f"line {number} is not a record")
        prifac, seq, ts_usec, flag = match.group(1), match.group(2), match.group(3), match.group(4)
        records.append(
            {
                "facility": int(prifac) >> 3,
                "level": int(prifac) & 7,
                "seq": int(seq),
                "ts_usec": int(ts_usec),
                "continuation": flag == "c",
                "body": line[match.end() :],
                "dict_lines": 0,
            }
        )
    if not records:
        raise EvidenceError("empty-capture", "no records")
    return records


def require_complete_capture(records: list[dict[str, Any]], attestation: dict[str, Any]) -> None:
    """Refuse anything that cannot support a claim about the whole boot.

    Every check here rejects a capture that is *incomplete*, never one that is
    merely negative: none of these outcomes is reported as the absence of a
    witness record, because none of them is evidence about what was written.
    """
    if attestation["acquisition_status"] not in ATTRIBUTING_READER_STATUSES:
        # The read did not stop at a bound; it broke. Nothing about the bytes
        # can repair that, and it is not renamed as a framing problem.
        raise EvidenceError("incomplete-acquisition", str(attestation["acquisition_status"]))
    if attestation["parse_status"] not in USABLE_PARSE_STATUSES:
        raise EvidenceError("unusable-framing", str(attestation["parse_status"]))
    first, last = records[0]["seq"], records[-1]["seq"]
    if (first, last, len(records)) != (
        attestation["reader_first_seq"],
        attestation["reader_last_seq"],
        attestation["reader_records"],
    ):
        # The reader said what it read; the bytes must agree, or something
        # between the read and here dropped or added records.
        raise EvidenceError("capture-binding-mismatch", "reader extent")
    if first != 0:
        # log_first_seq starts at 0 on every boot, so a higher first sequence
        # means the head of this boot has already been overwritten. The records
        # that would show whether this witness was the first userspace writer
        # are simply gone.
        raise EvidenceError("ring-head-evicted", f"capture starts at sequence {first}")
    for previous, current in zip(records, records[1:]):
        if current["seq"] != previous["seq"] + 1:
            # log_store() does log_next_seq++ per record, so the ring has no
            # holes. A hole means the reader overran (-EPIPE) or the capture was
            # edited; either way the missing range could contain anything.
            raise EvidenceError(
                "capture-sequence-gap", f"{previous['seq']} -> {current['seq']}"
            )


def survey(records: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {marker.strip(): 0 for marker in DOWNSTREAM_MARKERS}
    earliest_downstream: dict[str, Any] | None = None
    kernel_init: dict[str, Any] | None = None
    kernel_init_path: str | None = None
    first_userspace: dict[str, Any] | None = None
    for record in records:
        body = record["body"]
        if record["facility"] != KERNEL_FACILITY and first_userspace is None:
            first_userspace = record
        for marker in DOWNSTREAM_MARKERS:
            if body.startswith(marker):
                counts[marker.strip()] += 1
                if earliest_downstream is None:
                    earliest_downstream = record
        if kernel_init is None and record["facility"] == KERNEL_FACILITY:
            match = KERNEL_INIT_MARKER.match(body)
            if match is not None:
                kernel_init = record
                kernel_init_path = match.group("path")
    return {
        "counts": counts,
        "earliest_downstream": earliest_downstream,
        "kernel_init": kernel_init,
        "kernel_init_path": kernel_init_path,
        "first_userspace": first_userspace,
    }


def parse_witness_record(record: dict[str, Any]) -> dict[str, str]:
    body = unescape_body(record["body"])
    if body != record["body"]:
        raise EvidenceError("malformed-witness-record", "record carries escaped bytes")
    if record["continuation"]:
        raise EvidenceError("malformed-witness-record", "record is a continuation fragment")
    match = WITNESS_GRAMMAR.match(body)
    if match is None:
        raise EvidenceError("malformed-witness-record", "grammar")
    fields = {name: match.group(name) for name in FIELD_ORDER}
    # Field order is part of the grammar above; this asserts the constant list
    # and the pattern have not drifted apart.
    if tuple(fields) != FIELD_ORDER:
        raise EvidenceError("malformed-witness-record", "field order")
    return fields


def evaluate(raw: bytes, attestation: dict[str, Any]) -> dict[str, Any]:
    # The input is the untouched raw file. Derive its prefix here, so a caller
    # cannot bind a claimed raw digest to a different, independently supplied
    # prefix. The tail remains on disk even when the prefix is usable.
    if len(raw) != attestation["raw_size"] or sha256_hex(raw) != attestation["raw_sha256"]:
        raise EvidenceError("capture-binding-mismatch", "raw bytes")
    capture = raw[:attestation["capture_size"]]
    tail = raw[attestation["capture_size"]:]
    if len(tail) != attestation["trailing_partial_bytes"]:
        raise EvidenceError("capture-binding-mismatch", "raw derivative extent")
    if attestation["parse_status"] in USABLE_PARSE_STATUSES:
        expected_status = "trailing-partial-record" if tail else "record-aligned"
        if attestation["parse_status"] != expected_status or b"\n" in tail:
            raise EvidenceError("capture-binding-mismatch", "raw derivative boundary")
    if len(capture) != attestation["capture_size"]:
        raise EvidenceError("capture-binding-mismatch", "size")
    if sha256_hex(capture) != attestation["capture_sha256"]:
        raise EvidenceError("capture-binding-mismatch", "sha256")

    records = parse_capture(capture)
    # Completeness first. Everything downstream is a claim about the boot, and a
    # partial capture cannot carry one - including a negative one.
    require_complete_capture(records, attestation)

    seen = survey(records)
    witnesses = [record for record in records if record["body"].startswith(MAGIC + ";")]
    observation = {
        "records": len(records),
        "first_seq": records[0]["seq"],
        "last_seq": records[-1]["seq"],
        "sequence_contiguous": True,
        "ring_head_present": True,
        "acquisition_status": attestation["acquisition_status"],
        "parse_status": attestation["parse_status"],
        "raw_size": attestation["raw_size"],
        "raw_sha256": attestation["raw_sha256"],
        "trailing_partial_bytes": attestation["trailing_partial_bytes"],
        "witness_records": len(witnesses),
        "downstream_marker_counts": seen["counts"],
        "kernel_init_marker": "present" if seen["kernel_init"] is not None else "absent",
        "kernel_init_path": seen["kernel_init_path"],
    }

    if len(witnesses) > 1:
        raise EvidenceError("duplicate-witness-record", f"{len(witnesses)} records")
    if not witnesses:
        if attestation["acquisition_status"] != COMPLETE_READER_STATUS:
            # A prefix that stops before the witness would have been written
            # looks exactly like a boot that never wrote one. Refuse to call it
            # an absence.
            raise EvidenceError("incomplete-capture", "a bounded prefix carries no record")
        raise EvidenceError("witness-record-absent", "complete capture carries no record")

    witness = witnesses[0]
    fields = parse_witness_record(witness)
    observation["witness_seq"] = witness["seq"]
    observation["witness_ts_usec"] = witness["ts_usec"]
    observation["witness_facility"] = witness["facility"]
    observation["candidate_id"] = fields["cand"]
    observation["boot_id_sha256"] = sha256_hex(fields["bootid"].encode("ascii"))

    for name in ("procself", "pidns", "bootid"):
        if fields[name] == UNAVAILABLE:
            # A partial emission. The witness deliberately still writes a
            # well-formed record so this is distinguishable from silence.
            raise EvidenceError("field-unavailable", name)

    if witness["facility"] != USER_FACILITY:
        # LOG_USER is what devkmsg_write() assigns a userspace write with no
        # facility prefix. Anything else did not come through /dev/kmsg the way
        # this witness writes.
        raise EvidenceError("unexpected-facility", str(witness["facility"]))
    if fields["stage"] != STAGE:
        raise EvidenceError("unexpected-stage", fields["stage"])
    if fields["cand"] != attestation["candidate_id"]:
        raise EvidenceError("candidate-id-mismatch", "record does not name the attested candidate")
    if fields["pid"] != EXPECTED_PID:
        raise EvidenceError("pid-not-one", fields["pid"])
    if fields["procself"] != EXPECTED_PROCSELF:
        raise EvidenceError("pid-not-one", f"procself={fields['procself']}")
    if fields["pidns"] != EXPECTED_PIDNS:
        raise EvidenceError("not-initial-pid-namespace", fields["pidns"])
    if fields["bootid"] != attestation["boot_id"]:
        raise EvidenceError("boot-id-mismatch", "record is not from the attested boot")

    # The kernel handover. This is a facility-0 record, so unlike a body prefix
    # it cannot have been written by any userspace process.
    if seen["kernel_init"] is None:
        return {
            "verdict": "OBSERVED",
            "reason": "no-kernel-handover-record",
            "observation": observation,
        }
    observation["kernel_init_seq"] = seen["kernel_init"]["seq"]
    if seen["kernel_init_path"] != EXPECTED_INIT_PATH:
        # The kernel exec'd something other than the ramdisk /init this
        # candidate replaced.
        raise EvidenceError("unexpected-init-path", str(seen["kernel_init_path"]))
    if witness["seq"] <= seen["kernel_init"]["seq"]:
        raise EvidenceError("witness-record-precedes-kernel-handover", "impossible ordering")

    # This checks ordering, not authorship. Attribution additionally depends
    # on the fixed candidate's reviewed execution path and ASSUMPTIONS.
    first_userspace = seen["first_userspace"]
    observation["first_userspace_seq"] = None if first_userspace is None else first_userspace["seq"]
    if first_userspace is None or first_userspace["seq"] != witness["seq"]:
        raise EvidenceError(
            "witness-record-not-earliest",
            "a userspace record precedes the witness, so it is not the first userspace writer",
        )

    earliest = seen["earliest_downstream"]
    if earliest is not None:
        # Corroboration only. It is recorded, and nothing depends on it.
        observation["earliest_downstream_seq"] = earliest["seq"]
        observation["earliest_downstream_ts_usec"] = earliest["ts_usec"]

    return {
        "verdict": "PROVED",
        "reason": "first-userspace-record-of-a-complete-attested-boot",
        "observation": observation,
    }


ESTABLISHES = [
    "the pinned candidate's /init executed",
    "the kernel returned PID 1 to it, corroborated by procfs's own /proc/self",
    "it was in the initial PID namespace (PROC_PID_INIT_INO)",
    "the record was written on the attested boot",
    "the record is the first userspace-facility record of that boot",
]
ASSUMPTIONS = [
    "the reviewed /init entry path is the sole in-scope source of matching "
    "witness text; no alternate producer fabricated that record; being the "
    "first log alone does not establish this",
    "the attested boot.img and AP digests are the ones the F1 transfer journal "
    "records as written to the boot partition",
    "the capture and the boot_id it is compared against were read in the same "
    "attended session, from the boot that session prepared",
    "the threat model is implementation error, not a hostile resident root that "
    "ran before /init on this boot",
]
DOES_NOT_ESTABLISH = [
    "that the boot partition held the pinned AP - that is the F1 transfer journal's claim",
    "Android return, rollback success, or final device health",
    "that the exec handoff to magiskinit completed",
    "who wrote the record, from the kernel timestamp alone - the timestamp "
    "establishes ordering and nothing more",
    "anything about a capture this consumer was handed rather than collected",
]


def result_document(
    capture_path: Path, attestation_path: Path, outcome: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "tier": "H0",
        "device_observation_active": DEVICE_OBSERVATION_ACTIVE,
        "device_commands": 0,
        "adb_commands": 0,
        "su_commands": 0,
        "target": dict(TARGET),
        "candidate_id": CANDIDATE_ID,
        "candidate_boot_sha256": CANDIDATE_BOOT_SHA256,
        "inputs": {"capture": capture_path.name, "attestation": attestation_path.name},
        "establishes": list(ESTABLISHES) if outcome["verdict"] == "PROVED" else [],
        "assumptions": list(ASSUMPTIONS) if outcome["verdict"] == "PROVED" else [],
        "does_not_establish": list(DOES_NOT_ESTABLISH),
        **outcome,
    }


def validate(capture_path: Path, attestation_path: Path) -> dict[str, Any]:
    try:
        attestation = parse_attestation(read_regular_bytes(attestation_path, "attestation"))
        capture = read_regular_bytes(capture_path, "capture")
        outcome = evaluate(capture, attestation)
    except EvidenceError as error:
        outcome = {"verdict": "NO_PROOF", "reason": error.reason, "detail": error.detail}
    return result_document(capture_path, attestation_path, outcome)


def main() -> int:
    parser = argparse.ArgumentParser(description="S20+ P1 PID1 witness evidence consumer")
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--attestation", type=Path)
    parser.add_argument("--render-capture-contract", action="store_true")
    args = parser.parse_args()
    if args.render_capture_contract:
        print(
            json.dumps(
                {"schema": SCHEMA, "capture_contract": CAPTURE_CONTRACT, "assumptions": ASSUMPTIONS},
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.capture is None or args.attestation is None:
        parser.error("--capture and --attestation are both required")
    try:
        result = validate(args.capture, args.attestation)
    except OSError as error:
        result = {
            "schema": SCHEMA,
            "verdict": "NO_PROOF",
            "reason": "unreadable-input",
            "detail": str(error),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "PROVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
