#!/usr/bin/env python3
"""Offline codec for P2's explicit pre-exec RAM snapshot acquisition type.

MATCH is a structural result. Only the owning F1 journal can join it with the
actual transfer, source closure, leased acquisition and same-boot identity.
There is no device command, publication, activation or live entry point here.
"""
from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from typing import Any

import s20plus_g986n_p1_pid1_witness_evidence as kmsg

ROOT = Path(__file__).resolve().parents[5]
HEADER = ROOT / "workspace/public/src/native-init/s20plus_p2_ram_snapshot_contract.h"
CONSTANTS: dict[str, str | int] = {}
for _name, _value in re.findall(r'^#define (P2_[A-Z0-9_]+) ("[^"\n]*"|[0-9]+)$', HEADER.read_text(), re.M):
    if _name in CONSTANTS:
        raise ValueError("duplicate P2 declaration")
    CONSTANTS[_name] = _value[1:-1] if _value.startswith('"') else int(_value)
MAGIC = str(CONSTANTS["P2_MAGIC"])
CANDIDATE_ID = str(CONSTANTS["P2_CANDIDATE_ID"])
STAGE = str(CONSTANTS["P2_STAGE"])
SNAPSHOT_NAME = str(CONSTANTS["P2_SNAPSHOT_NAME"])
PARTIAL_NAME = str(CONSTANTS["P2_PARTIAL_NAME"])
READER_NAME = str(CONSTANTS["P2_READER_NAME"])
SNAPSHOT_HEADER = int(CONSTANTS["P2_SNAPSHOT_HEADER"])
READER_HEADER = int(CONSTANTS["P2_READER_HEADER"])
MAX_CAPTURE_BYTES = int(CONSTANTS["P2_MAX_CAPTURE_BYTES"])
MAX_SNAPSHOT_BYTES = SNAPSHOT_HEADER + MAX_CAPTURE_BYTES
MAX_STREAM_BYTES = READER_HEADER + MAX_SNAPSHOT_BYTES
MAX_RECORDS = int(CONSTANTS["P2_MAX_RECORDS"])
MAX_ELAPSED_NS = int(CONSTANTS["P2_MAX_ELAPSED_NS"])
CAPTURE_SOURCE = "pre-exec-ram-kmsg-v1"
RAM_FILESYSTEMS = {0x01021994, 0x858458F6}
SCHEMA = "s20plus_g986n_p2_ram_snapshot_analysis_v1"
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z")
WITNESS = re.compile(
    re.escape(MAGIC) + r";cand=(?P<cand>[0-9a-f]{32});pid=(?P<pid>[0-9]{10});"
    r"procself=(?P<procself>[^;]+);pidns=(?P<pidns>[^;]+);"
    r"bootid=(?P<bootid>[^;]+);stage=" + re.escape(STAGE) + r"\Z")
ASSUMPTIONS = list(kmsg.ASSUMPTIONS) + [
    "the reviewed snapshot producer and fixed reader are the actual artifact bytes",
    "the RAM file was transferred intact through the reviewed Magisk path on this boot",
    "the file is not an attestation against a hostile resident root",
]


class SnapshotError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _magic(name: str) -> bytes:
    value = str(CONSTANTS[name]).encode("ascii")
    if len(value) >= 16:
        raise SnapshotError("container magic too long")
    return value.ljust(16, b"\0")


def _boot(raw: bytes) -> str:
    try:
        value = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise SnapshotError("malformed-boot-id") from error
    if UUID.fullmatch(value) is None:
        raise SnapshotError("malformed-boot-id")
    return value


def parse_snapshot(data: bytes) -> dict[str, Any]:
    if len(data) < SNAPSHOT_HEADER or len(data) > MAX_SNAPSHOT_BYTES:
        raise SnapshotError("snapshot-extent")
    if data[:16] != _magic("P2_SNAPSHOT_MAGIC"):
        raise SnapshotError("snapshot-magic")
    version, status, size, records, error, elapsed = struct.unpack_from("<IIQQqQ", data, 16)
    statuses = {int(v) for k, v in CONSTANTS.items() if k.startswith("P2_STATUS_")}
    if version != 1 or status not in statuses or data[124:128] != b"\0" * 4:
        raise SnapshotError("snapshot-header")
    if size != len(data) - SNAPSHOT_HEADER or records > MAX_RECORDS:
        raise SnapshotError("snapshot-extent")
    if data[56:88] != CANDIDATE_ID.encode("ascii"):
        raise SnapshotError("snapshot-candidate")
    return {"status": status, "records": records, "error": error, "elapsed_ns": elapsed,
            "boot_raw": data[88:124], "raw": data[SNAPSHOT_HEADER:]}


def parse_reader(data: bytes) -> dict[str, Any]:
    if len(data) < READER_HEADER or len(data) > MAX_STREAM_BYTES:
        raise SnapshotError("reader-extent")
    if data[:16] != _magic("P2_READER_MAGIC"):
        raise SnapshotError("reader-magic")
    version, status = struct.unpack_from("<II", data, 16)
    size, fs_type, device, inode = struct.unpack_from("<QQQQ", data, 24)
    mode, links, uid, gid, partial, location = struct.unpack_from("<IIIIII", data, 56)
    statuses = {int(v) for k, v in CONSTANTS.items() if k.startswith("P2_READ_")}
    if version != 1 or status not in statuses or data[152:160] != b"\0" * 8:
        raise SnapshotError("reader-header")
    if size != len(data) - READER_HEADER or partial not in (0, 1) or location not in (0, 1):
        raise SnapshotError("reader-extent")
    return {"status": status, "fs_type": fs_type, "device": device, "inode": inode,
            "mode": mode, "links": links, "uid": uid, "gid": gid, "partial": partial,
            "location": ("/debug_ramdisk", "/sbin")[location],
            "boot_before_raw": data[80:116], "boot_after_raw": data[116:152],
            "snapshot": data[READER_HEADER:]}


def analyze(data: bytes, *, expected_boot_id_sha256: str, returncode: int) -> dict[str, Any]:
    """Analyze exact saved stdout. No caller-supplied prefix or success flag.

    The owner must separately validate raw-capture failure flags, command/source
    identity, target binding and its transfer. Even MATCH is not live authority.
    """
    result: dict[str, Any] = {"schema": SCHEMA, "capture_source": CAPTURE_SOURCE,
        "structural_verdict": "NO_PROOF", "live_authority": False,
        "raw_size": len(data), "raw_sha256": sha256(data), "assumptions": ASSUMPTIONS}
    try:
        if re.fullmatch(r"[0-9a-f]{64}", expected_boot_id_sha256) is None:
            raise SnapshotError("expected-boot-binding")
        reader = parse_reader(data)
        result["reader_status"] = reader["status"]
        result["snapshot_size"] = len(reader["snapshot"])
        result["snapshot_sha256"] = sha256(reader["snapshot"])
        expected_rc = 0 if reader["status"] == 0 else 2
        if type(returncode) is not int or returncode != expected_rc:
            raise SnapshotError("reader-exit-status")
        if reader["status"] != 0 or reader["partial"]:
            raise SnapshotError("reader-diagnostic-" + str(reader["status"]))
        if (reader["fs_type"] not in RAM_FILESYSTEMS or reader["mode"] != 0o100600
                or reader["links"] != 1 or reader["uid"] != 0 or reader["gid"] != 0
                or reader["device"] == 0 or reader["inode"] == 0):
            raise SnapshotError("reader-file-metadata")
        before, after = _boot(reader["boot_before_raw"]), _boot(reader["boot_after_raw"])
        if before != after or sha256(before.encode()) != expected_boot_id_sha256:
            raise SnapshotError("reader-boot-binding")
        snapshot = parse_snapshot(reader["snapshot"])
        result["capture_status"] = snapshot["status"]
        result["prefix_size"] = len(snapshot["raw"])
        result["prefix_sha256"] = sha256(snapshot["raw"])
        if snapshot["status"] != 0 or snapshot["error"] != 0:
            raise SnapshotError("producer-diagnostic-" + str(snapshot["status"]))
        if snapshot["elapsed_ns"] >= MAX_ELAPSED_NS:
            raise SnapshotError("producer-deadline")
        if _boot(snapshot["boot_raw"]) != before:
            raise SnapshotError("snapshot-boot-binding")
        records = kmsg.parse_capture(snapshot["raw"])
        if len(records) != snapshot["records"]:
            raise SnapshotError("producer-record-count")
        if records[0]["seq"] != 0:
            raise SnapshotError("ring-head-evicted")
        if any(b["seq"] != a["seq"] + 1 for a, b in zip(records, records[1:])):
            raise SnapshotError("capture-sequence-gap")
        witnesses = [r for r in records if r["body"].startswith(MAGIC + ";")]
        if len(witnesses) != 1:
            raise SnapshotError("witness-count")
        witness = witnesses[0]
        match = WITNESS.fullmatch(witness["body"])
        if (not match or witness["continuation"] or witness["dict_lines"]
                or witness["facility"] != 1 or witness is not records[-1]):
            raise SnapshotError("witness-record")
        fields = match.groupdict()
        if fields != {"cand": CANDIDATE_ID, "pid": "0000000001", "procself": "1",
                      "pidns": "pid:[4026531836]", "bootid": before}:
            raise SnapshotError("witness-fields")
        seen = kmsg.survey(records)
        if (seen["kernel_init"] is None or seen["kernel_init_path"] != "/init"
                or seen["kernel_init"]["seq"] >= witness["seq"]):
            raise SnapshotError("kernel-dispatch-order")
        if seen["first_userspace"] is not witness:
            raise SnapshotError("witness-record-not-earliest")
        result.update(structural_verdict="MATCH", reason="source-bound-pid1-prefix",
            records=len(records), first_seq=0, witness_seq=witness["seq"],
            boot_id_sha256=expected_boot_id_sha256, location=reader["location"],
            requires_owner_transfer_and_acquisition_binding=True)
    except (SnapshotError, kmsg.EvidenceError) as error:
        result["reason"] = str(error).split(":", 1)[0]
    return result
