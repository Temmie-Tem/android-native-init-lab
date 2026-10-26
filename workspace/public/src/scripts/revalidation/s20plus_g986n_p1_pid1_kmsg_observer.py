#!/usr/bin/env python3
"""Dormant, exact-target same-boot kmsg acquisition for the S20+ P1 owner.

The owner supplies its isolated, leased F1 engine, not a caller-selected command
runner. Its existing raw-capture primitive writes and fsyncs bounded stdout and
stderr before returning a handle. Parsing happens only after that publication;
a record-aligned prefix is a derivative, never a replacement for the raw bytes.

The fixed device command uses the stock toybox timeout and head applets. Head
caps newline-terminated output, and timeout kills its process group after five
seconds even if the ADB client disappears. Neither silence nor a host deadline
is a device-side drain. A successful head exit or the expected device deadline
is only a bounded prefix; an error, host deadline or overflow is NO_PROOF.

No mount, staging, write, reboot or other-target operation is introduced. The
public entry point remains inactive; the private engine also enforces its
session lease and exact serial/command/argument/output bounds at dispatch.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

SCHEMA = "s20plus_g986n_p1_pid1_kmsg_observer_v1"
RECEIPT_SCHEMA = "s20plus_g986n_p1_pid1_kmsg_receipt_v1"
ATTESTATION_SCHEMA = "s20plus_g986n_p1_pid1_witness_attestation_v4"

# No live read is authorized. Rotating this to True is an activation and needs
# its own review; nothing in this repository binds a runner while it is False.
OBSERVER_ACTIVE = False

CAPTURE_SOURCE = "live-dev-kmsg"
KMSG_NODE = "/dev/kmsg"

# This command and its raw-capture arguments are also bound by the F1 shell.
# The host deadline exceeds the remote timeout so normal expiry returns 137.
MAX_CAPTURE_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 65_536
MAX_STDERR_BYTES = 4096
DEADLINE_SECONDS = 15
REMOTE_SECONDS = 5
CAPTURE_LABEL = "p1-kmsg"
CAPTURE_NAME = "p1-kmsg-capture.raw"
STDERR_NAME = "p1-kmsg.stderr"
ATTESTATION_NAME = "p1-kmsg-attestation.json"
BINDING_NAME = "p1-kmsg-binding.json"
READ_SCRIPT = (
    "exec /system/bin/toybox timeout -s KILL 5 "
    "/system/bin/toybox head -n 65536 /dev/kmsg"
)
CAPTURE_KWARGS = {
    "timeout": DEADLINE_SECONDS,
    "stdout_maximum": MAX_CAPTURE_BYTES,
    "stderr_maximum": MAX_STDERR_BYTES,
    "stdout_name": CAPTURE_NAME,
    "stderr_name": STDERR_NAME,
}

STATUS_COMPLETE = "complete"
STATUS_IDLE = "idle-stop"
STATUS_DEADLINE = "deadline"
STATUS_BYTE_LIMIT = "byte-limit"
STATUS_RECORD_LIMIT = "record-limit"
STATUS_FAILED = "acquisition-failed"
STATUS_UNREADABLE = "unreadable"
# Stops that leave a contiguous prefix beginning at the ring head.
BOUNDED_STATUSES = (
    STATUS_COMPLETE,
    STATUS_IDLE,
    STATUS_DEADLINE,
    STATUS_BYTE_LIMIT,
    STATUS_RECORD_LIMIT,
)
STATUSES = BOUNDED_STATUSES + (STATUS_FAILED, STATUS_UNREADABLE)

PARSE_ALIGNED = "record-aligned"
PARSE_TRAILING_PARTIAL = "trailing-partial-record"
PARSE_SEQUENCE_GAP = "sequence-gap"
PARSE_UNPARSABLE = "unparsable"
PARSE_STATUSES = (PARSE_ALIGNED, PARSE_TRAILING_PARTIAL, PARSE_SEQUENCE_GAP, PARSE_UNPARSABLE)

RECORD_HEADER = re.compile(rb"^(\d{1,10}),(\d{1,20}),(\d{1,20}),([^,;]*)((?:,[^;]*)*);")
BOOT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA256_TEXT = re.compile(r"^[0-9a-f]{64}$")


class ObserverError(RuntimeError):
    pass


class PublishError(ObserverError):
    """A publication that did not complete. Never a successful capture."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Publication. Raw bytes, complete, atomic, no-clobber, verified after the fact.
# --------------------------------------------------------------------------

def _write_all(descriptor: int, payload: bytes, label: str) -> int:
    """Write every byte or raise. Never reports success on a short write.

    `os.write` is permitted to write fewer bytes than it was given, and the
    earlier revision of this function called it once and ignored the result: a
    16-byte capture published as 3 bytes, with a receipt digest describing the
    input rather than the file. Each case that can stop this loop is handled
    explicitly rather than being allowed to look like completion.
    """
    offset = 0
    while offset < len(payload):
        try:
            written = os.write(descriptor, payload[offset:])
        except InterruptedError:
            # EINTR: no progress, no failure. Retry the same range.
            continue
        except OSError as error:
            if error.errno == errno.EINTR:
                continue
            raise PublishError(
                f"{label} write failed after {offset} of {len(payload)} bytes: {error}"
            ) from error
        if written <= 0 or written > len(payload) - offset:
            # Zero progress on a regular file is not a retryable condition; it
            # would spin forever if it were treated as one.
            raise PublishError(
                f"{label} write made no progress at {offset} of {len(payload)} bytes"
            )
        offset += written
    return offset


def publish_raw(path: Path, data: bytes) -> dict[str, Any]:
    """Publish exact bytes atomically, no-clobber, mode 0400.

    The receipt describes the bytes that are actually on disk: after linking, the
    published file is read back and its size and digest are recomputed from what
    was read. A write loop bug, a short write or a truncating filesystem cannot
    produce a successful receipt, because the receipt is not derived from the
    input at all.

    Before link publication, a write failure leaves no intended name. A later
    durability or read-back failure may leave a complete final file but never
    returns a success receipt. The staged bytes are kept
    under `<name>.incomplete` so a partial acquisition stays diagnosable, and
    that name can never be mistaken for a capture.
    """
    if path.exists() or path.is_symlink():
        raise PublishError(f"refusing to clobber {path.name}")
    staged = path.with_name(path.name + ".partial")
    if staged.exists() or staged.is_symlink():
        raise PublishError(f"refusing to clobber {staged.name}")
    descriptor = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o400)
    try:
        _write_all(descriptor, data, "capture")
        os.fsync(descriptor)
        staged_size = os.fstat(descriptor).st_size
    except BaseException:
        os.close(descriptor)
        _quarantine(staged, path)
        raise
    os.close(descriptor)
    if staged_size != len(data):
        _quarantine(staged, path)
        raise PublishError(f"staged capture is {staged_size} bytes, not {len(data)}")

    os.link(staged, path)
    os.unlink(staged)
    _fsync_directory(path.parent)

    # The receipt is computed from the published file, never from `data`.
    published = _read_published(path)
    if published != data:
        raise PublishError("published capture differs from the acquired bytes")
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o400
        or info.st_nlink != 1
        or info.st_size != len(data)
    ):
        raise PublishError("published capture is not a mode-0400 direct regular file")
    return {
        "schema": RECEIPT_SCHEMA,
        "name": path.name,
        "size": info.st_size,
        "sha256": sha256_hex(published),
        "mode": "0400",
        "complete": True,
    }


def _quarantine(staged: Path, intended: Path) -> None:
    """Keep partial bytes, under a name that is not a capture."""
    try:
        if staged.exists():
            failed = intended.with_name(intended.name + ".incomplete")
            if not failed.exists():
                os.link(staged, failed)
                os.unlink(staged)
            # An earlier incomplete file is evidence too. Keep both names if
            # the quarantine name already exists; never overwrite or discard it.
            _fsync_directory(intended.parent)
    except OSError:
        pass


def _read_published(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        size = before.st_size
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 <= size <= MAX_CAPTURE_BYTES):
            raise PublishError("published capture identity or size is invalid")
        payload = bytearray()
        while len(payload) < size:
            block = os.read(descriptor, size - len(payload))
            if not block:
                break
            payload.extend(block)
        if os.read(descriptor, 1):
            raise PublishError("published capture grew during read-back")
        after = os.fstat(descriptor)
        if (len(payload) != size or (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                != (size, before.st_mtime_ns, before.st_ctime_ns)):
            raise PublishError("published capture changed during read-back")
    finally:
        os.close(descriptor)
    return bytes(payload)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


# Acquisition uses the existing raw-first, leased engine backend. The API is
# private to the fixed owner; offline tests substitute only its process boundary.
def acquire(engine, *, out_dir: Path, serial: str) -> dict[str, Any]:
    handle = engine.raw_capture.acquire_command(
        [str(engine.ADB), "-s", serial, "shell", "su", "-c",
         engine.shlex.quote(READ_SCRIPT)],
        out_dir, CAPTURE_LABEL, **CAPTURE_KWARGS,
    )
    return read_acquisition(engine, out_dir)


def read_acquisition(engine, out_dir: Path) -> dict[str, Any]:
    """Reopen the durable acquisition; never acquire again to repair a report."""
    handle = engine.raw_capture.load_handle(out_dir / (CAPTURE_LABEL + ".capture.json"))
    if (handle.name != CAPTURE_LABEL or handle.stdout.get("name") != CAPTURE_NAME
            or handle.stderr.get("name") != STDERR_NAME):
        raise ObserverError("P1 raw handle does not name the fixed capture streams")
    raw = engine.raw_capture.read_stdout(handle, maximum=MAX_CAPTURE_BYTES)
    stderr = engine.raw_capture.read_stderr(handle, maximum=MAX_STDERR_BYTES)
    if (handle.timed_out or handle.output_exceeded or handle.producer_error_type
            or stderr or handle.returncode not in (0, 137)):
        status = STATUS_FAILED
    else:
        # /dev/kmsg does not EOF. A zero exit is the fixed head limit, not proof
        # that the ring was drained; 137 is the toybox KILL deadline.
        status = STATUS_RECORD_LIMIT if handle.returncode == 0 else STATUS_DEADLINE
    return {
        "raw": raw,
        "status": status,
        "returncode": handle.returncode,
        "timed_out": handle.timed_out,
        "output_exceeded": handle.output_exceeded,
        "producer_error_type": handle.producer_error_type,
        "stderr_size": len(stderr),
        "stderr_sha256": sha256_hex(stderr),
        "bytes": len(raw),
    }


# --------------------------------------------------------------------------
# Framing. A derivative of the raw bytes, described as one.
# --------------------------------------------------------------------------

def _split_records(data: bytes) -> tuple[list[bytes], int]:
    """Whole newline-terminated lines, and the length of the partial tail."""
    end = data.rfind(b"\n")
    if end < 0:
        return [], len(data)
    aligned = data[: end + 1]
    lines = aligned.split(b"\n")[:-1]
    return lines, len(data) - (end + 1)


def extent(data: bytes) -> dict[str, Any]:
    """Sequence extent and continuity, without interpreting record bodies."""
    first: int | None = None
    last: int | None = None
    records = 0
    contiguous = True
    for line in _split_records(data)[0]:
        if line.startswith(b" "):
            continue  # a dictionary continuation of the preceding record
        match = RECORD_HEADER.match(line)
        if match is None:
            raise ObserverError("capture line is not a /dev/kmsg record")
        sequence = int(match.group(2))
        if first is None:
            first = sequence
        elif last is not None and sequence != last + 1:
            contiguous = False
        last = sequence
        records += 1
    return {
        "first_seq": 0 if first is None else first,
        "last_seq": 0 if last is None else last,
        "records": records,
        "contiguous": contiguous,
    }


def frame(raw: bytes) -> dict[str, Any]:
    """Derive the record-aligned prefix that evaluation runs on.

    The result names its own byte range inside the raw capture and carries the
    raw digest, so it can never be presented as the untouched capture. Nothing
    here modifies, reorders or rewrites a byte: the derivative is a prefix.
    """
    lines, trailing = _split_records(raw)
    aligned_length = len(raw) - trailing
    aligned = raw[:aligned_length]
    try:
        measured = extent(aligned)
        parse_status = PARSE_TRAILING_PARTIAL if trailing else PARSE_ALIGNED
    except ObserverError as error:
        return {
            "aligned": b"",
            "raw_sha256": sha256_hex(raw),
            "raw_size": len(raw),
            "aligned_offset": 0,
            "aligned_size": 0,
            "trailing_partial_bytes": trailing,
            "parse_status": PARSE_UNPARSABLE,
            "parse_detail": str(error),
            "extent": {"first_seq": 0, "last_seq": 0, "records": 0, "contiguous": False},
        }
    if not measured["contiguous"]:
        parse_status = PARSE_SEQUENCE_GAP
    return {
        "aligned": aligned,
        "raw_sha256": sha256_hex(raw),
        "raw_size": len(raw),
        "aligned_offset": 0,
        "aligned_size": aligned_length,
        "trailing_partial_bytes": trailing,
        "parse_status": parse_status,
        "parse_detail": "",
        "extent": measured,
        "lines": len(lines),
    }


def build_attestation(
    *,
    framed: dict[str, Any],
    acquisition_status: str,
    target: dict[str, str],
    candidate_id: str,
    candidate_boot_sha256: str,
    candidate_ap_sha256: str,
    boot_id: str,
) -> dict[str, Any]:
    """Exactly the document the evidence consumer accepts, and nothing more.

    It carries both statuses and both digests: what was acquired, and what the
    evaluated prefix is. The candidate is named by the bytes the transfer journal
    recorded as written to `boot`, not only by its label.
    """
    if acquisition_status not in STATUSES:
        raise ObserverError(f"unknown acquisition status {acquisition_status!r}")
    if framed["parse_status"] not in PARSE_STATUSES:
        raise ObserverError(f"unknown parse status {framed['parse_status']!r}")
    if BOOT_ID.match(boot_id) is None:
        raise ObserverError("boot_id is not a kernel boot id")
    for name, value in (
        ("candidate_boot_sha256", candidate_boot_sha256),
        ("candidate_ap_sha256", candidate_ap_sha256),
        ("raw_sha256", framed["raw_sha256"]),
    ):
        if SHA256_TEXT.match(value) is None:
            raise ObserverError(f"{name} is not a sha256")
    measured = framed["extent"]
    return {
        "schema": ATTESTATION_SCHEMA,
        "source": CAPTURE_SOURCE,
        "target": dict(target),
        "candidate_id": candidate_id,
        "candidate_boot_sha256": candidate_boot_sha256,
        "candidate_ap_sha256": candidate_ap_sha256,
        "boot_id": boot_id,
        "raw_sha256": framed["raw_sha256"],
        "raw_size": framed["raw_size"],
        "capture_sha256": sha256_hex(framed["aligned"]),
        "capture_size": framed["aligned_size"],
        "aligned_offset": framed["aligned_offset"],
        "trailing_partial_bytes": framed["trailing_partial_bytes"],
        "acquisition_status": acquisition_status,
        "parse_status": framed["parse_status"],
        "reader_first_seq": measured["first_seq"],
        "reader_last_seq": measured["last_seq"],
        "reader_records": measured["records"],
    }


def snapshot(engine, expected: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Reuse the exact owner identity parser and lease-bound fixed ADB reads."""
    rows = engine.adb_inventory(health_only=True)
    row = engine.exact_adb_row(rows, expected["serial_sha256"], "device")
    serial = row["serial"]
    topology = sha256_hex(engine.adb_devpath(serial).encode())
    if topology != expected["topology_sha256"]:
        raise ObserverError("P1 acquisition topology differs from prepared target")
    values = engine.parse_public_snapshot(engine.base.bounded_command(
        [str(engine.ADB), "-s", serial, "exec-out", "sh", "-c",
         engine.PUBLIC_SNAPSHOT_SCRIPT], 20, engine.MAX_ADB_BYTES,
    ))
    return {
        "inventory": engine.sanitized_inventory(rows),
        "serial_sha256": sha256_hex(serial.encode()),
        "topology_sha256": topology,
        "values": values,
    }, serial


def run_acquisition(engine, *, out_dir: Path, expected: dict[str, Any],
                    candidate_id: str, candidate_boot_sha256: str,
                    candidate_ap_sha256: str, candidate_boot_id_sha256: str) -> dict[str, Any]:
    """Bind before and after the sole capture; publish raw before interpretation."""
    before, serial = snapshot(engine, expected)
    boot_id = before["values"]["boot_id"]
    if (sha256_hex(boot_id.encode()) != candidate_boot_id_sha256
            or candidate_boot_id_sha256 == expected["boot_id_sha256"]):
        raise ObserverError("P1 acquisition is not on the observed candidate boot")
    outcome = acquire(engine, out_dir=out_dir, serial=serial)
    # This publication is metadata only. The raw primitive has already fsynced
    # both original streams and its outcome, even on a failed acquisition.
    after, final_serial = snapshot(engine, expected)
    target_keys = ("serial_sha256", "topology_sha256", "values")
    if any(after[key] != before[key] for key in target_keys) or final_serial != serial:
        raise ObserverError("P1 acquisition target or boot changed during capture")
    binding = {
        "schema": "s20plus_g986n_p1_kmsg_binding_v1",
        "serial_sha256": before["serial_sha256"],
        "topology_sha256": before["topology_sha256"],
        "boot_id_sha256": candidate_boot_id_sha256,
        "snapshot_sha256": engine.digest(before),
        "pre_post_identical": True,
        "candidate_boot_sha256": candidate_boot_sha256,
        "candidate_ap_sha256": candidate_ap_sha256,
    }
    engine.durable_json(out_dir / BINDING_NAME, binding)
    framed = frame(outcome["raw"])
    attestation = build_attestation(
        framed=framed, acquisition_status=outcome["status"],
        target=dict(engine.TARGET), candidate_id=candidate_id,
        candidate_boot_sha256=candidate_boot_sha256,
        candidate_ap_sha256=candidate_ap_sha256, boot_id=boot_id,
    )
    engine.durable_json(out_dir / ATTESTATION_NAME, attestation)
    return {
        "schema": SCHEMA, "serial": serial, "binding": binding,
        "acquisition": {key: value for key, value in outcome.items() if key != "raw"},
        "attestation": attestation,
        "capture_path": out_dir / CAPTURE_NAME,
        "attestation_path": out_dir / ATTESTATION_NAME,
    }


def require_active() -> None:
    if OBSERVER_ACTIVE is not True:
        raise ObserverError("STOP_S20PLUS_G986N_P1_PID1_KMSG_OBSERVER_NOT_ACTIVE")


def observe(engine, **kwargs: Any) -> dict[str, Any]:
    require_active()
    return run_acquisition(engine, **kwargs)


def render_plan() -> dict[str, Any]:
    return {
        "schema": SCHEMA, "tier": "D0", "observer_active": OBSERVER_ACTIVE,
        "source": CAPTURE_SOURCE, "node": KMSG_NODE, "read_script": READ_SCRIPT,
        "device_writes": 0, "reboot_commands": 0, "partition_transfers": 0,
        "limits": dict(CAPTURE_KWARGS), "remote_timeout_seconds": REMOTE_SECONDS,
        "acquisition_statuses": list(STATUSES), "parse_statuses": list(PARSE_STATUSES),
        "silence_is_not_a_drain": True,
        "publication": "engine raw capture precedes binding and prefix parsing",
        "not_this_node": "/proc/last_kmsg is a different retained surface; no authority is borrowed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render-plan", action="store_true")
    args = parser.parse_args()
    if args.render_plan:
        print(json.dumps(render_plan(), indent=2, sort_keys=True))
        return 0
    print("STOP_S20PLUS_G986N_P1_PID1_KMSG_OBSERVER_NOT_ACTIVE")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
