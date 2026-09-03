#!/usr/bin/env python3
"""Publish the exact already-CLOSED P3.33 state and result without device access.

P3.33 completed one candidate transfer, one exact rollback, final healthy
Android, and a 19-record CLOSED journal.  The ordinary publisher stopped only
because adding the required arrival projection grew ``live-state.json`` to
32,855 bytes, 87 bytes above the ordinary 32 KiB intermediate-record bound.
This exact-run H0 finalizer leaves that bound unchanged and uses the existing
64 KiB terminal bound only for the pinned final state and canonical result.
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
REVALIDATION = Path(__file__).resolve().parent
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p333_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p333-ready1-prepared-20260904-1"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p333_closed_result_finalizer_v1"
AUDIT_VERDICT = "PASS_P333_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
PUBLISH_VERDICT = "PASS_P333_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
EXPECTED_BINDING = (
    "34787824f7de444822cf139b3d015df57120e1ab2251a13a81a67e92e5ba559e"
)
EXPECTED_BUNDLE = (
    "a53ee8797266f46629cb14cbd16565768ed6c6bcc2cc7c71d8e7b363a13901d0"
)
EXPECTED_TERMINAL_RECORD = (
    "e76974f885bf6158d7d05f376fffa1e9e742d44139579c31d071a6167d5f8704"
)
EXPECTED_RESULT_VERDICT = "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
EXPECTED_OUTCOME = (
    "p333_authenticated_logical_resident_open_entry_diagnostic_"
    "unproved_rollback_verified"
)
EXPECTED_PRE_STATE = (
    31_285,
    "372493653034ff77dda839045dea70229d3c458365695feca43b26e4029fc302",
)
EXPECTED_FINAL_STATE = (
    32_855,
    "232aeecc7339da3c2ae15120dd21de592ea2497b6a1e9388dfb8497312ba1506",
)
EXPECTED_RESULT = (
    36_652,
    "207c36a1506997fe81e45e16997c3769fd838bf5e5f6de1ed8853c861388a7ed",
)
CORE_MAX_RECORD = 32 * 1024
MAX_FINAL_RECORD = 64 * 1024

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        7_090,
        "6fb30bec1e9640ce1659b906f181dce9390f769ed24b80f3b35802418ed84f40",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        490_661,
        "e379df2fe2fa674ba4b03a718c32eaa868bb41143f16755cdc444c13f394a4c5",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        133_507,
        "8e12d03f1fadae1949318beb078d6f63567081e8c75e0516b51b758518879bba",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        20_988,
        "3261045d4dfe580e0667472c21f16875f9193bd7be497e80c4aefa97c40911fd",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "757c5489ae909c4bc24ba094db0986b3471472ba50cfc6e56115ec900a6d4965",
    ),
    "terminal_record": (
        RUN_DIR / "transaction/journal/0018-transition-run_closed.json",
        676,
        "508b1780b5bb2ad71bfcb33c2d4296e251c8b12ce7c23f695ca8d4ef630fd108",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_079,
        "197db1982276e89b61ceb73a841abee6b8bf62fcd5dc51c9a724419dc49e9861",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_030,
        "3694c03493acbcf06e2b78518f1b143e28c28284098667ab5c1d417192c103a4",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        6_801,
        "8485312a0b5e6ce118da3393faac2ff533deabddda2a5835abf62e59119cf378",
    ),
    "candidate_observer_raw": (
        RUN_DIR / "candidate-observer.raw",
        73,
        "18bc55ba6a6b0abc6c8a2d714e33bd407e35300e4d68355931e92e26c53a7eba",
    ),
}


class FinalizerError(RuntimeError):
    """The exact consumed P3.33 run cannot be finalized safely."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _stable(path: Path, label: str, maximum: int = 1024 * 1024) -> bytes:
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
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or len(payload) != before.st_size
        or len(payload) > maximum
        or identity(before) != identity(inside)
        or identity(before) != identity(after)
    ):
        raise FinalizerError(f"{label} is not one stable direct file")
    return payload


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode() + b"\n"


def _verify_exact_files() -> None:
    for label, (path, size, digest) in EXACT_FILES.items():
        payload = _stable(path, label)
        if (len(payload), _sha256(payload)) != (size, digest):
            raise FinalizerError(f"{label} identity differs")


def _state_phase(payload: bytes) -> str:
    identity = (len(payload), _sha256(payload))
    if identity == EXPECTED_PRE_STATE:
        return "pre"
    if identity == EXPECTED_FINAL_STATE:
        return "final"
    raise FinalizerError("P3.33 live state identity differs")


def _load_runtime() -> tuple[Any, Any]:
    _verify_exact_files()
    if str(REVALIDATION) not in sys.path:
        sys.path.insert(0, str(REVALIDATION))
    import device_action_f1_live_v2 as live  # noqa: PLC0415
    import device_action_f1_v2 as core  # noqa: PLC0415

    if (
        Path(live.__file__).resolve(strict=True) != EXACT_FILES["live_source"][0]
        or Path(core.__file__).resolve(strict=True) != EXACT_FILES["core_source"][0]
        or live.core is not core
        or core.MAX_RECORD != CORE_MAX_RECORD
        or core.MAX_RESULT_RECORD != MAX_FINAL_RECORD
    ):
        raise FinalizerError("loaded Process-v2 runtime identity differs")
    return live, core


def _load_prepared_stored_lane(live: Any) -> Any:
    original = live._p324_typec_lane_value  # noqa: SLF001

    def stored(prepared: Any, **_kwargs: Any) -> Any:
        return original(prepared, revalidate=False)

    live._p324_typec_lane_value = stored  # noqa: SLF001
    try:
        return live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    finally:
        live._p324_typec_lane_value = original  # noqa: SLF001


def _validate_with_state(
    live: Any, core: Any, value: dict[str, Any], prepared: Any, state: dict[str, Any]
) -> None:
    original_state = live._state  # noqa: SLF001
    original_reopen = core.Journal.__dict__["reopen"]
    live._state = lambda _prepared: state  # noqa: SLF001
    core.Journal.reopen = classmethod(
        lambda cls, path, binding: cls(path, binding)
    )
    try:
        live.validate_live_result(value, prepared)
    finally:
        core.Journal.reopen = original_reopen
        live._state = original_state  # noqa: SLF001


def reconstruct() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, str, Any]:
    if RUN_DIR.is_symlink() or RUN_DIR.absolute() != RUN_DIR.resolve(strict=True):
        raise FinalizerError("exact P3.33 run directory is indirect")
    state_payload = _stable(STATE_PATH, "P3.33 live state", MAX_FINAL_RECORD)
    phase = _state_phase(state_payload)
    live, core = _load_runtime()
    prepared = _load_prepared_stored_lane(live)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("P3.33 prepared binding differs")

    journal = core.Journal(RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    if (
        journal.state() != "CLOSED"
        or len(records) != 19
        or records[-1].get("sequence") != 18
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256") != EXPECTED_TERMINAL_RECORD
    ):
        raise FinalizerError("P3.33 journal is not the exact CLOSED run")
    for name in ("candidate", "rollback"):
        for suffix in ("start", "result"):
            extra = RUN_DIR / f"{name}-attempt-02.{suffix}.json"
            if extra.exists() or extra.is_symlink():
                raise FinalizerError("a second transfer attempt exists")
        result = live._validate_transfer_result(prepared, name, 1)  # noqa: SLF001
        if result.get("classification") != "odin_transfer_completed":
            raise FinalizerError(f"P3.33 {name} transfer differs")

    state = live._state(prepared)  # noqa: SLF001
    if _canonical(state) != state_payload:
        raise FinalizerError("P3.33 live state is not canonical")
    expected = {
        "candidate_classification": "odin_transfer_completed",
        "candidate_completed": True,
        "candidate_observer_classification": "authenticated-session-error",
        "candidate_observer_accepted": False,
        "candidate_observer_guard_release_status": "released",
        "candidate_observer_guard_released": True,
        "download_endpoint_absent": True,
        "rollback_classification": "odin_transfer_completed",
        "rollback_completed": True,
        "final_verified": True,
        "p333_proof_class": "NO_PROOF_OBSERVER",
        "session_count": 1,
        "successful_sessions": 0,
        "reconnect_count": 0,
    }
    if any(state.get(key) != expected_value for key, expected_value in expected.items()):
        raise FinalizerError("P3.33 CLOSED no-proof state differs")

    raw = _stable(
        EXACT_FILES["candidate_observer_raw"][0],
        "P3.33 candidate raw evidence",
    )
    banner = live.p333_open_entry_runtime.DEVICE_BANNER
    if not raw.startswith(banner) or len(raw) <= len(banner):
        raise FinalizerError("P3.33 native PID1 banner differs")
    frame = live.p333_open_entry_observer.decode_frame(raw[len(banner) :])
    diagnostic = live.p333_open_entry_observer.parse_diagnostic_frame(
        frame, live.p333_open_entry_runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER
    )
    if diagnostic.code != 0:
        raise FinalizerError("P3.33 console-entry diagnostic differs")

    projection = live._candidate_arrival_proof_projection(prepared, state)  # noqa: SLF001
    projection_expected = {
        "role": "p332_authenticated_logical_resident_same_fd_session_v1",
        "observer_receipt_classification": "authenticated-session-error",
        "proof": False,
        "hmac_authenticated": False,
        "logical_resident_proof": False,
        "same_tty_fd": False,
        "fixed_p330_commands": False,
    }
    if not isinstance(projection, dict) or any(
        projection.get(key) != expected_value
        for key, expected_value in projection_expected.items()
    ):
        raise FinalizerError("P3.33 arrival projection differs")
    key = live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY
    if phase == "pre":
        if key in state:
            raise FinalizerError("P3.33 pre-state already has an arrival projection")
        final_state = {**state, key: projection}
    else:
        if state.get(key) != projection:
            raise FinalizerError("P3.33 final arrival projection differs")
        final_state = state
    final_state_payload = _canonical(final_state)
    if (len(final_state_payload), _sha256(final_state_payload)) != EXPECTED_FINAL_STATE:
        raise FinalizerError("P3.33 reconstructed final state differs")

    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if (verdict, outcome) != (EXPECTED_RESULT_VERDICT, EXPECTED_OUTCOME):
        raise FinalizerError("P3.33 terminal classification differs")
    value = {
        "schema": live.LIVE_RESULT_SCHEMA,
        "adapter_version": live.ADAPTER_VERSION,
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "bundle_sha256": prepared.bundle.sha256,
        "approval_binding_sha256": prepared.binding_sha256,
        "journal": journal.receipt(),
        "current_state": journal.state(),
        "timeline": core.timeline(records),
        "live_state": final_state,
        "verdict": verdict,
        "outcome_class": outcome,
        "recovery_required": False,
    }
    _validate_with_state(live, core, value, prepared, final_state)
    payload = _canonical(value)
    if (len(payload), _sha256(payload)) != EXPECTED_RESULT:
        raise FinalizerError("P3.33 reconstructed result differs")
    _verify_exact_files()
    return value, payload, final_state, final_state_payload, phase, core


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_state(core: Any, value: dict[str, Any], payload: bytes) -> bool:
    if (len(payload), _sha256(payload)) != EXPECTED_FINAL_STATE:
        raise FinalizerError("P3.33 final state publication identity differs")
    current = _stable(STATE_PATH, "P3.33 live state before publication", MAX_FINAL_RECORD)
    phase = _state_phase(current)
    if phase == "final":
        if current != payload:
            raise FinalizerError("existing P3.33 final state differs")
        return False
    core._write_atomic_bounded(  # noqa: SLF001
        STATE_PATH, value, core.MAX_RESULT_RECORD
    )
    retained = _stable(STATE_PATH, "published P3.33 final state", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(STATE_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.33 final state differs")
    return True


def _publish_result(core: Any, value: dict[str, Any], payload: bytes) -> bool:
    if (len(payload), _sha256(payload)) != EXPECTED_RESULT:
        raise FinalizerError("P3.33 result publication identity differs")
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        if _stable(RESULT_PATH, "existing P3.33 result", MAX_FINAL_RECORD) != payload:
            raise FinalizerError("existing P3.33 result differs")
        return False
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    try:
        core._write_exclusive_bounded(  # noqa: SLF001
            temporary, value, core.MAX_RESULT_RECORD
        )
        os.link(temporary, RESULT_PATH, follow_symlinks=False)
        _fsync_dir(RESULT_PATH.parent)
    finally:
        temporary.unlink(missing_ok=True)
        _fsync_dir(RESULT_PATH.parent)
    retained = _stable(RESULT_PATH, "published P3.33 result", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.33 result differs")
    return True


def finalize(*, audit_only: bool) -> dict[str, Any]:
    if audit_only:
        reconstructed = reconstruct()
    else:
        live, _core = _load_runtime()
        with live.odin_core.transaction_session(RUN_DIR / "f1-session"):
            reconstructed = reconstruct()
            value, payload, final_state, state_payload, _phase, core = reconstructed
            state_upgraded = _publish_state(core, final_state, state_payload)
            created = _publish_result(core, value, payload)
            reconstructed = reconstruct()
    value, payload, _state, state_payload, phase, _core = reconstructed
    return {
        "schema": SCHEMA,
        "verdict": AUDIT_VERDICT if audit_only else PUBLISH_VERDICT,
        "run_dir": str(RUN_DIR),
        "state": {
            "size": len(state_payload),
            "sha256": _sha256(state_payload),
            "phase": phase,
            "upgraded": False if audit_only else state_upgraded,
        },
        "result": {
            "size": len(payload),
            "sha256": _sha256(payload),
            "formal_verdict": value["verdict"],
            "outcome_class": value["outcome_class"],
            "current_state": value["current_state"],
            "recovery_required": value["recovery_required"],
        },
        "console_entry_diagnostic_proved": True,
        "created": False if audit_only else created,
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
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = finalize(audit_only=not args.publish)
    except (FinalizerError, OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
