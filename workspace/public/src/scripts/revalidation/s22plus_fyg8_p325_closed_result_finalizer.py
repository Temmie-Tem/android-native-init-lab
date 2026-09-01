#!/usr/bin/env python3
"""Publish the exact oversized result for one already-CLOSED P3.25 run.

The device transaction, exact rollback, and final health are already complete.
Only the canonical ``live-result.json`` exceeded the shared 32 KiB host record
bound.  This finalizer has no device backend and accepts one pinned CLOSED run
and one pinned 33,677-byte result under a local 64 KiB publication bound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p325_process_v2_ready_3.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-09-01T151137093213Z-1788275497093253263"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p325_closed_result_finalizer_v1"
VERDICT = "PASS_P325_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
AUDIT_VERDICT = "PASS_P325_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
EXPECTED_BINDING = (
    "1155089efb561f2c0ae0a73f142d1d6df634817bccbbfad093837f0d9a0bfead"
)
EXPECTED_BUNDLE = (
    "7282a912ce901f75c050934bd1b5deeef6b8f2dfa3b4862187bcf241e2186848"
)
EXPECTED_RESULT_VERDICT = (
    "PASS_F1_V2_P325_ACM_PRIMARY_NATIVE_PID1_USB_ARRIVAL_AND_ROLLED_BACK"
)
EXPECTED_OUTCOME = "p325_acm_primary_native_pid1_usb_arrival_rollback_verified"
EXPECTED_STATE_SIZE = 30_011
EXPECTED_STATE_SHA256 = (
    "c6094a55993fb3751a153d9eae781a3ea378b2d94ef3dc1fbc8fab9d8b91a3f8"
)
EXPECTED_RESULT_SIZE = 33_677
EXPECTED_RESULT_SHA256 = (
    "c96b7900d9f7fe615a7da889dabb4d5bb58d85029c455bd1d332e274e9e3572c"
)
EXPECTED_TERMINAL_RECORD_SHA256 = (
    "0f47b922ea1e74f66620622f9ba5ff31823b28b29a087524e781c1da0291a2dd"
)
CORE_MAX_RECORD = 32 * 1024
MAX_FINAL_RECORD = 64 * 1024

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        3_327,
        "a197709728fc7efd35ca1de715e7b884b4c912d52a579fd744009b41a5eabb0b",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        266_773,
        "e9504fa1268684a7ffe86bbfd379db4cdfe9bb1c782b357553c7b5c7e605b7f5",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        96_984,
        "e01b58562be2f0e0022907be3bc7d7bdbae5577d4baa6df0083122c395c28b69",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        15_099,
        "b73c88796dc4226f0d96d60dd06386f3d2c5c76ad4a080c8cf1512a0f62520fe",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "2d8e2f29a6759e6f9d1da8f84c0baff53d584c5a6bc1ae363bdd8cd7b29569a8",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_127,
        "86deea5a69efb3aea5248a4b28b45561ac266d8313274ee096830bdb8247ed8d",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_078,
        "8faf7724942ae644e582da366155930026bc95b0e588ce7a13696866693b7ea8",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        1_800,
        "7f91d8bbff5f6ba03773a61d9ea14f4ce718a441cf4348bb88de42729baf20d3",
    ),
    "candidate_observer_raw": (
        RUN_DIR / "candidate-observer.raw",
        49,
        "72653f08249ec15c01ec44dade168f87910c2bb5718d68465f7fadc3bbbffd7d",
    ),
    "candidate_observer_capture": (
        RUN_DIR / "candidate-observer.capture.json",
        512,
        "23e67d23fa86bf1b2be6042038f9617731568bd74de1c49f11c6418f670da9b6",
    ),
    "guard_release": (
        RUN_DIR / "candidate-observer-guard-release.json",
        206,
        "074a7879111effbe0e788c5c0bc999dc4d547c885cddb2940b91727d12141790",
    ),
    "p324_lane": (
        RUN_DIR / "p324-candidate-observer-lane.json",
        3_113,
        "cff25c7d13cc09571af4c07d5cc6380fb5cab83afa40a47d2fda6e539dbb5739",
    ),
    "p300_trace": (
        RUN_DIR / "p300-usb-trace/result.json",
        3_163,
        "7615665191996221f740f9321d01a714267b87be0bb998eb926818a69428a0fa",
    ),
    "live_state": (
        STATE_PATH,
        EXPECTED_STATE_SIZE,
        EXPECTED_STATE_SHA256,
    ),
}


class FinalizerError(RuntimeError):
    """The exact P3.25 CLOSED result cannot be reconstructed or published."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _metadata(value: os.stat_result) -> tuple[int, ...]:
    return (
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


def _stable_bytes(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise FinalizerError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or _metadata(before) != _metadata(inside)
        or _metadata(before) != _metadata(after)
    ):
        raise FinalizerError(f"{label} is not one stable direct file")
    return payload


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("utf-8") + b"\n"


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


def _load_prepared_stored_lane(live: Any) -> Any:
    original = live._p324_typec_lane_value  # noqa: SLF001

    def stored_lane(prepared: Any, **_kwargs: Any) -> Any:
        return original(prepared, revalidate=False)

    live._p324_typec_lane_value = stored_lane  # noqa: SLF001
    try:
        return live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    finally:
        live._p324_typec_lane_value = original  # noqa: SLF001


def _read_only_journal(core: Any, path: Path, binding: str) -> Any:
    journal = core.Journal(path, binding)
    journal.records()
    return journal


def _validate_result(
    live: Any, value: dict[str, Any], prepared: Any, state: dict[str, Any]
) -> None:
    core = live.core
    original_state = live._state  # noqa: SLF001
    original_reopen = core.Journal.__dict__["reopen"]

    def read_only_reopen(cls: Any, path: Path, binding: str) -> Any:
        del cls
        return _read_only_journal(core, path, binding)

    live._state = lambda _prepared: state  # noqa: SLF001
    core.Journal.reopen = classmethod(read_only_reopen)
    try:
        live.validate_live_result(value, prepared)
    finally:
        core.Journal.reopen = original_reopen
        live._state = original_state  # noqa: SLF001


def reconstruct() -> tuple[dict[str, Any], bytes, Any, Any, dict[str, Any]]:
    if RUN_DIR.is_symlink() or RUN_DIR.absolute() != RUN_DIR.resolve(strict=True):
        raise FinalizerError("exact P3.25 run directory is indirect")
    live, core = _load_runtime()
    prepared = _load_prepared_stored_lane(live)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("prepared P3.25 binding differs")

    journal = _read_only_journal(
        core, RUN_DIR / "transaction", EXPECTED_BINDING
    )
    records = journal.records()
    if (
        journal.state() != "CLOSED"
        or len(records) != 19
        or records[-1].get("sequence") != 18
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256")
        != EXPECTED_TERMINAL_RECORD_SHA256
    ):
        raise FinalizerError("P3.25 journal is not the exact CLOSED/19 run")
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
        candidate.get("classification") != "odin_transfer_completed"
        or rollback.get("classification") != "odin_transfer_completed"
    ):
        raise FinalizerError("candidate or rollback transfer differs")

    state_payload = _stable_bytes(STATE_PATH, "P3.25 live state", MAX_FINAL_RECORD)
    state = live._state(prepared)  # noqa: SLF001
    if _canonical(state) != state_payload:
        raise FinalizerError("P3.25 live state is not canonical")
    if (
        state.get("candidate_classification") != "odin_transfer_completed"
        or state.get("candidate_completed") is not True
        or state.get("candidate_observer_classification") != "accepted"
        or state.get("candidate_observer_accepted") is not True
        or state.get("candidate_observer_guard_release_status") != "released"
        or state.get("candidate_observer_guard_released") is not True
        or state.get("download_endpoint_absent") is not True
        or state.get("rollback_classification") != "odin_transfer_completed"
        or state.get("rollback_completed") is not True
        or state.get("final_verified") is not True
        or state.get("p325_proof_class") != "NO_PROOF_OBSERVER"
    ):
        raise FinalizerError("P3.25 CLOSED live state differs")
    projection = live._candidate_arrival_proof_projection(  # noqa: SLF001
        prepared, state
    )
    if (
        not isinstance(projection, dict)
        or projection.get("proof") is not True
        or projection.get("banner_size") != 49
        or projection.get("supplemental_carrier") is not None
        or state.get("candidate_arrival_proof") != projection
    ):
        raise FinalizerError("P3.25 positive arrival projection differs")

    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if verdict != EXPECTED_RESULT_VERDICT or outcome != EXPECTED_OUTCOME:
        raise FinalizerError("P3.25 terminal classification differs")
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
    _validate_result(live, value, prepared, state)
    payload = _canonical(value)
    if (
        len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
        or len(payload) <= CORE_MAX_RECORD
        or len(payload) > MAX_FINAL_RECORD
    ):
        raise FinalizerError("P3.25 reconstructed result identity differs")
    _verify_exact_files()
    return value, payload, live, prepared, state


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish(payload: bytes) -> None:
    if (
        len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
    ):
        raise FinalizerError("P3.25 result publication identity differs")
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        raise FinalizerError("P3.25 live result already exists")
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    linked = False
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise FinalizerError("P3.25 result write made no progress")
            offset += written
        os.fsync(descriptor)
        complete = os.fstat(descriptor)
        if (
            not stat.S_ISREG(complete.st_mode)
            or stat.S_IMODE(complete.st_mode) != 0o400
            or complete.st_nlink != 1
            or complete.st_size != len(payload)
        ):
            raise FinalizerError("P3.25 result temporary identity differs")
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, RESULT_PATH, follow_symlinks=False)
        linked = True
        _fsync_dir(RESULT_PATH.parent)
    finally:
        temporary.unlink(missing_ok=True)
        _fsync_dir(RESULT_PATH.parent)
    if not linked:
        raise FinalizerError("P3.25 result was not published")
    retained = _stable_bytes(RESULT_PATH, "P3.25 live result", MAX_FINAL_RECORD)
    if (
        retained != payload
        or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400
        or RESULT_PATH.stat().st_nlink != 1
    ):
        raise FinalizerError("published P3.25 result differs")


def finalize(*, audit_only: bool) -> dict[str, Any]:
    value, payload, live, prepared, state = reconstruct()
    already_present = RESULT_PATH.exists() or RESULT_PATH.is_symlink()
    if already_present:
        retained = _stable_bytes(RESULT_PATH, "existing P3.25 live result", MAX_FINAL_RECORD)
        if retained != payload:
            raise FinalizerError("existing P3.25 live result differs")
        if not audit_only:
            raise FinalizerError("P3.25 live result is already published")
    elif not audit_only:
        _publish(payload)
        _validate_result(live, value, prepared, state)
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
        "already_present": already_present,
        "device_contact": False,
        "adb_invoked": False,
        "usb_revalidated": False,
        "odin_invoked": False,
        "candidate_transfer": False,
        "rollback_transfer": False,
        "live_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = finalize(audit_only=args.audit_only)
    except (FinalizerError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
