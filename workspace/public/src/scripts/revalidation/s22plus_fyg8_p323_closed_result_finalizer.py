#!/usr/bin/env python3
"""Publish the missing result for one already-CLOSED P3.23 F1 journal.

This incident finalizer is deliberately incapable of device work.  It reopens
one exact prepared run, requires its already-durable candidate/rollback/final
health closure, reconstructs the ordinary Process-v2 result, validates it with
the frozen live implementation, and publishes only ``live-result.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p323_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-09-01T100714815943Z-1788257234815987455"
)
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p323_closed_result_finalizer_v1"
VERDICT = "PASS_P323_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
AUDIT_VERDICT = "PASS_P323_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
EXPECTED_BINDING = "da580d2c6980c8ab8fd87dc799c31ab65e9f0bb084513fe294b8f3ca7c5dbd7c"
EXPECTED_BUNDLE = "81c9af01f684702b144d008f66ee4e147a4774351649b0e1d4d2755bf8f80c47"
EXPECTED_RESULT_VERDICT = "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
EXPECTED_OUTCOME = (
    "p323_acm_primary_native_pid1_arrival_unproved_rollback_verified"
)
EXPECTED_RESULT_SIZE = 34_937
EXPECTED_RESULT_SHA256 = (
    "de24b959c37357a2532556258dbb0e64dd21390cb0ae2d16662add6776e26829"
)
MAX_RESULT = 64 * 1024
CORE_MAX_RECORD = 32 * 1024

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        3_327,
        "ef8bd5ad6b5b525d77fb69f8d6e24c39900ebf6a2635a07049fd14ea1b37c2ef",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        241_592,
        "458c26a00b180cce8dcb6d3edb1c0ad83103113252412d132e2f249e7ebd2570",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        93_359,
        "bc809238f69b9212f487a7f0c0ac30d2c3a936379a5cc4c65d31dd61f23b4b9b",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        13_624,
        "5d8012b14d9a378112a5869593f9cf8f58e28cfd573e88e4c31fd46cc6f34153",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "0cceb5a75d6871c5a28b5df2c6936dfb184a33aeda074c98b0079a3c246a0814",
    ),
    "live_state": (
        RUN_DIR / "live-state.json",
        31_205,
        "97e2b4314e1545f90d68398b8ff5eaf0673903bfed73b4ea4d253d95b3341b16",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_127,
        "fe8475868e7aeb5261acb3fc04cb5cc5caad269ee6b0df8dcd66a8cb0fdfce09",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_078,
        "e9367c1e91be6da7deb79be3e2a740577afae2ef1c8f59bf947509c850cfa5c5",
    ),
}


class FinalizerError(RuntimeError):
    """The exact closed-run result cannot be reconstructed or published."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable_bytes(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
    except OSError as exc:
        raise FinalizerError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size < 0
        or before.st_size > maximum
    ):
        raise FinalizerError(f"{label} is not a bounded direct single-link file")
    try:
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise FinalizerError(f"{label} cannot be read") from exc
    identity = lambda value: (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    if (
        len(payload) != before.st_size
        or len(payload) > maximum
        or identity(before) != identity(inside)
        or identity(before) != identity(after)
    ):
        raise FinalizerError(f"{label} changed while read")
    return payload


def _verify_exact_files() -> None:
    for label, (path, size, sha256) in EXACT_FILES.items():
        payload = _stable_bytes(path, label)
        if len(payload) != size or _sha256(payload) != sha256:
            raise FinalizerError(f"{label} identity differs")


def _load_runtime() -> tuple[Any, Any]:
    _verify_exact_files()
    sys.path.insert(0, str(REVALIDATION))
    import device_action_f1_live_v2 as live  # noqa: PLC0415
    import device_action_f1_v2 as core  # noqa: PLC0415

    if (
        Path(live.__file__).resolve(strict=True) != EXACT_FILES["live_source"][0]
        or Path(core.__file__).resolve(strict=True) != EXACT_FILES["core_source"][0]
        or live.core is not core
        or core.MAX_RECORD != CORE_MAX_RECORD
    ):
        raise FinalizerError("loaded Process-v2 runtime identity differs")
    return live, core


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("utf-8") + b"\n"


def reconstruct() -> tuple[dict[str, Any], bytes, Any, Any]:
    if RUN_DIR.absolute() != RUN_DIR.resolve(strict=True) or RUN_DIR.is_symlink():
        raise FinalizerError("exact P3.23 run directory is indirect")
    if not RUN_DIR.is_dir():
        raise FinalizerError("exact P3.23 run directory is absent")
    _verify_exact_files()
    live, core = _load_runtime()
    prepared = live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("prepared P3.23 binding differs")
    journal = core.Journal.reopen(RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    if journal.state() != "CLOSED" or len(records) != 19:
        raise FinalizerError("P3.23 journal is not the exact CLOSED 19-record run")
    if (
        records[-1].get("sequence") != 18
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256")
        != "0662020127e9e3bab39524f9cbfe28ad835c0a8dc1ab288e7f4cfa8f792cf60e"
    ):
        raise FinalizerError("P3.23 terminal journal record differs")
    if any(
        path.exists() or path.is_symlink()
        for path in (
            RUN_DIR / "candidate-attempt-02.start.json",
            RUN_DIR / "candidate-attempt-02.result.json",
            RUN_DIR / "rollback-attempt-02.start.json",
            RUN_DIR / "rollback-attempt-02.result.json",
        )
    ):
        raise FinalizerError("a second transfer attempt exists")
    candidate = live._validate_transfer_result(prepared, "candidate", 1)  # noqa: SLF001
    rollback = live._validate_transfer_result(prepared, "rollback", 1)  # noqa: SLF001
    if (
        not isinstance(candidate, dict)
        or candidate.get("classification") != "odin_transfer_completed"
        or not isinstance(rollback, dict)
        or rollback.get("classification") != "odin_transfer_completed"
    ):
        raise FinalizerError("candidate/rollback transfer closure differs")
    state = live._state(prepared)  # noqa: SLF001
    arrival = state.get("candidate_arrival_proof")
    if (
        state.get("candidate_classification") != "odin_transfer_completed"
        or state.get("candidate_completed") is not True
        or state.get("candidate_observer_classification") != "endpoint-timeout"
        or state.get("candidate_observer_accepted") is not False
        or state.get("rollback_classification") != "odin_transfer_completed"
        or state.get("rollback_completed") is not True
        or state.get("final_verified") is not True
        or not isinstance(arrival, dict)
        or arrival.get("role") != "cdc_acm_primary_v1"
        or arrival.get("proof") is not False
    ):
        raise FinalizerError("P3.23 CLOSED live state differs")
    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if verdict != EXPECTED_RESULT_VERDICT or outcome != EXPECTED_OUTCOME:
        raise FinalizerError("P3.23 terminal classification differs")
    value = {
        "schema": live.LIVE_RESULT_SCHEMA,
        "adapter_version": live.ADAPTER_VERSION,
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "bundle_sha256": prepared.bundle.sha256,
        "approval_binding_sha256": prepared.binding_sha256,
        "journal": journal.receipt(),
        "current_state": journal.state(),
        "timeline": core.timeline(records),
        "live_state": state,
        "verdict": verdict,
        "outcome_class": outcome,
        "recovery_required": False,
    }
    live.validate_live_result(value, prepared)
    payload = _canonical(value)
    if (
        len(payload) <= CORE_MAX_RECORD
        or len(payload) > MAX_RESULT
        or len(payload) != EXPECTED_RESULT_SIZE
        or (EXPECTED_RESULT_SHA256 and _sha256(payload) != EXPECTED_RESULT_SHA256)
    ):
        raise FinalizerError("P3.23 reconstructed result identity differs")
    _verify_exact_files()
    return value, payload, prepared, live


def _write_temp(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_RESULT:
        raise FinalizerError("P3.23 result exceeds its dedicated bound")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
        )
    except OSError as exc:
        raise FinalizerError("P3.23 result temporary cannot be created") from exc
    try:
        os.fchmod(descriptor, 0o400)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o400
            or opened.st_nlink != 1
            or opened.st_size != 0
        ):
            raise FinalizerError("P3.23 result temporary identity differs")
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise FinalizerError("P3.23 result write made no progress")
            offset += written
        complete = os.fstat(descriptor)
        if (
            complete.st_dev != opened.st_dev
            or complete.st_ino != opened.st_ino
            or complete.st_nlink != 1
            or stat.S_IMODE(complete.st_mode) != 0o400
            or complete.st_size != len(payload)
        ):
            raise FinalizerError("P3.23 result completed identity differs")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _repair_publication_cut(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    final = path.lstat()
    if (
        stat.S_ISLNK(final.st_mode)
        or not stat.S_ISREG(final.st_mode)
        or stat.S_IMODE(final.st_mode) != 0o400
    ):
        raise FinalizerError("P3.23 result type or mode differs")
    if final.st_nlink == 1:
        return
    if final.st_nlink != 2:
        raise FinalizerError("P3.23 result link count differs")
    pattern = re.compile(
        rf"^\.{re.escape(path.name)}\.[1-9][0-9]*\.[1-9][0-9]*\.tmp$"
    )
    candidates = [child for child in path.parent.iterdir() if pattern.fullmatch(child.name)]
    if len(candidates) != 1:
        raise FinalizerError("P3.23 result publication cut is ambiguous")
    temporary = candidates[0]
    temp = temporary.lstat()
    if (
        stat.S_ISLNK(temp.st_mode)
        or not stat.S_ISREG(temp.st_mode)
        or (temp.st_dev, temp.st_ino, temp.st_size, temp.st_nlink)
        != (final.st_dev, final.st_ino, final.st_size, 2)
        or stat.S_IMODE(temp.st_mode) != 0o400
    ):
        raise FinalizerError("P3.23 result publication cut identity differs")
    temporary.unlink()
    _fsync_directory(path.parent)
    if path.lstat().st_nlink != 1:
        raise FinalizerError("P3.23 result publication cut was not repaired")


def _publish_exact(payload: bytes) -> None:
    if (
        len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
    ):
        raise FinalizerError("P3.23 result publication identity differs")
    _repair_publication_cut(RESULT_PATH)
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        raise FinalizerError("P3.23 live result already exists")
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    linked = False
    try:
        _write_temp(temporary, payload)
        try:
            os.link(temporary, RESULT_PATH, follow_symlinks=False)
        except FileExistsError as exc:
            raise FinalizerError("P3.23 live result appeared concurrently") from exc
        linked = True
        _fsync_directory(RESULT_PATH.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        else:
            _fsync_directory(RESULT_PATH.parent)
    if not linked:
        raise FinalizerError("P3.23 result was not published")
    retained = _stable_bytes(RESULT_PATH, "P3.23 live result", MAX_RESULT)
    if retained != payload or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.23 result bytes differ")


def finalize(*, audit_only: bool) -> dict[str, Any]:
    value, payload, prepared, live = reconstruct()
    _repair_publication_cut(RESULT_PATH)
    existed = RESULT_PATH.exists() or RESULT_PATH.is_symlink()
    if existed:
        retained = _stable_bytes(RESULT_PATH, "existing P3.23 live result", MAX_RESULT)
        if (
            retained != payload
            or stat.S_IMODE(RESULT_PATH.lstat().st_mode) != 0o400
        ):
            raise FinalizerError("existing P3.23 live result differs")
        live.validate_live_result(value, prepared)
        if not audit_only:
            raise FinalizerError("P3.23 live result already published")
    elif not audit_only:
        _publish_exact(payload)
        live.validate_live_result(value, prepared)
    return {
        "schema": SCHEMA,
        "verdict": AUDIT_VERDICT if audit_only else VERDICT,
        "run_dir": str(RUN_DIR),
        "result": {
            "path": str(RESULT_PATH),
            "size": len(payload),
            "sha256": _sha256(payload),
            "formal_verdict": value["verdict"],
            "outcome_class": value["outcome_class"],
            "current_state": value["current_state"],
            "recovery_required": value["recovery_required"],
        },
        "created": not audit_only,
        "already_present": existed,
        "device_contact": False,
        "adb_invoked": False,
        "odin_invoked": False,
        "candidate_transfer": False,
        "rollback_transfer": False,
        "live_authorized": False,
    }


RETIRED_REASON = (
    "This P3.23 finalizer predates the P3.24 review finding and still reads the "
    "journal through the common repairing Journal.reopen. Running it, including "
    "with --audit-only, rewrites identical journal-head bytes and changes the "
    "inode and timestamps of P3.23's retained evidence. P3.23 is closed, "
    "consumed and already published, so there is no reason to run it again. "
    "Successors use the read-only journal view; see "
    "docs/reports/S22PLUS_FYG8_P325_CLOSED_RESULT_FINALIZER_INDEPENDENT_REVIEW_"
    "2026-09-02.md."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument(
        "--i-accept-p323-evidence-mutation",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(argv)
    if not args.i_accept_p323_evidence_mutation:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": "REFUSED_RETIRED_FINALIZER",
                    "reason": RETIRED_REASON,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    try:
        result = finalize(audit_only=args.audit_only)
    except (FinalizerError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
