#!/usr/bin/env python3
"""Publish the exact already-CLOSED P3.32 result without device access.

The device-side run is complete: one candidate transfer, one exact rollback,
final healthy Android, and a CLOSED journal.  The ordinary publisher stopped
after adding the required arrival-proof projection made ``live-state.json``
32,779 bytes, eleven bytes above the ordinary 32 KiB intermediate-record
bound.  This run-specific H0 finalizer leaves that bound unchanged.  It allows
only the pinned P3.32 pre-state to become the pinned final state under the
existing 64 KiB terminal bound, then publishes the pinned canonical result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = Path(__file__).resolve().parent
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p332_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p332-ready1-prepared-20260904-2"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p332_closed_result_finalizer_v1"
AUDIT_VERDICT = "PASS_P332_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
PUBLISH_VERDICT = "PASS_P332_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
EXPECTED_BINDING = (
    "fbae30c85a7f0ff681813cfcb4bcf1350833c70aa619a19d104d407737431f79"
)
EXPECTED_BUNDLE = (
    "b2f4003b7d078f562e9ee08d13f78f4ced910a417cca97cb7d26063aafbd668c"
)
EXPECTED_TERMINAL_RECORD = (
    "1f6db8d6d4e0bf22106366dc4cca3fcd0a265dfd534c3fdc27e23ce6335467b0"
)
EXPECTED_RESULT_VERDICT = "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
EXPECTED_OUTCOME = (
    "p332_authenticated_logical_resident_same_fd_unproved_rollback_verified"
)
EXPECTED_PRE_STATE = (
    31_209,
    "ff1927414d6df475116bbc77c527a41c0cea8b85c7e4a08d3a704acf12905a95",
)
EXPECTED_FINAL_STATE = (
    32_779,
    "7bf83fb129addbaecd124f4ca527118013b4fbc4fc0110538968415bac16b198",
)
EXPECTED_RESULT = (
    36_558,
    "3a76c74eba93999d568154710a57628d36390cbf552453ba5eba280c4439b112",
)
CORE_MAX_RECORD = 32 * 1024
MAX_FINAL_RECORD = 64 * 1024

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        6_827,
        "a95641eb82a10aaa8b0371b0dccf8d6d6adf182627e1eb00588173a2851cdfc0",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        478_497,
        "4a236c527fc8d6125201fe13fcc59fe185eb04fcec8a84c7bea211d90febe6fb",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        129_770,
        "92f8d7e15e618303d1462e53901e56626dbab6bb6c14c91520445d5258836b8b",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        20_693,
        "5b93e5bbf914fdb26730790e6a3db5f8c10b254864daa4098444975614cc8808",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "0031d7871747091bd82e0449dabf2c165f0f372f1907abae7c2169e3a6150a57",
    ),
    "terminal_record": (
        RUN_DIR / "transaction/journal/0018-transition-run_closed.json",
        676,
        "aa2e9277159168008c88139c5cedbf95c8961dab4b4b95ea0e8a283b8922c633",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_079,
        "8ec7f5bd1e230f0840b3a2cc391fda6e267efbaf68d71fa466727bc2557c0888",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_030,
        "7e5cc8dcf0147d174e1412fa0dd01fd38916f1f1bd74055b91942ab6924256b4",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        6_803,
        "e4d5f56fe3c3d87cc5fe9c78e6ef2a1a2b756d418b343984a86aa641baf4c145",
    ),
    "candidate_observer_raw": (
        RUN_DIR / "candidate-observer.raw",
        49,
        "ac1cd94304104e8494d6a27cd0b71192ecad420284056936c0ea71adc26c0f26",
    ),
}


class FinalizerError(RuntimeError):
    """The exact consumed P3.32 run cannot be finalized safely."""


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
    raise FinalizerError("P3.32 live state identity differs")


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


def reconstruct() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, str, Any, Any]:
    if RUN_DIR.is_symlink() or RUN_DIR.absolute() != RUN_DIR.resolve(strict=True):
        raise FinalizerError("exact P3.32 run directory is indirect")
    state_payload = _stable(STATE_PATH, "P3.32 live state", MAX_FINAL_RECORD)
    phase = _state_phase(state_payload)
    live, core = _load_runtime()
    prepared = _load_prepared_stored_lane(live)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("P3.32 prepared binding differs")

    journal = core.Journal(RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    if (
        journal.state() != "CLOSED"
        or len(records) != 19
        or records[-1].get("sequence") != 18
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256") != EXPECTED_TERMINAL_RECORD
    ):
        raise FinalizerError("P3.32 journal is not the exact CLOSED run")
    for name in ("candidate", "rollback"):
        for suffix in ("start", "result"):
            extra = RUN_DIR / f"{name}-attempt-02.{suffix}.json"
            if extra.exists() or extra.is_symlink():
                raise FinalizerError("a second transfer attempt exists")
        result = live._validate_transfer_result(prepared, name, 1)  # noqa: SLF001
        if result.get("classification") != "odin_transfer_completed":
            raise FinalizerError(f"P3.32 {name} transfer differs")

    state = live._state(prepared)  # noqa: SLF001
    if _canonical(state) != state_payload:
        raise FinalizerError("P3.32 live state is not canonical")
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
        "p332_proof_class": "NO_PROOF_OBSERVER",
        "session_count": 1,
        "successful_sessions": 0,
        "reconnect_count": 0,
    }
    if any(state.get(key) != value for key, value in expected.items()):
        raise FinalizerError("P3.32 CLOSED no-proof state differs")

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
        projection.get(key) != value for key, value in projection_expected.items()
    ):
        raise FinalizerError("P3.32 arrival projection differs")
    key = live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY
    if phase == "pre":
        if key in state:
            raise FinalizerError("P3.32 pre-state already has an arrival projection")
        final_state = {**state, key: projection}
    else:
        if state.get(key) != projection:
            raise FinalizerError("P3.32 final arrival projection differs")
        final_state = state
    final_state_payload = _canonical(final_state)
    if (len(final_state_payload), _sha256(final_state_payload)) != EXPECTED_FINAL_STATE:
        raise FinalizerError("P3.32 reconstructed final state differs")

    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if (verdict, outcome) != (EXPECTED_RESULT_VERDICT, EXPECTED_OUTCOME):
        raise FinalizerError("P3.32 terminal classification differs")
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
        raise FinalizerError("P3.32 reconstructed result differs")
    _verify_exact_files()
    return value, payload, final_state, final_state_payload, phase, live, core


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_state(core: Any, value: dict[str, Any], payload: bytes) -> bool:
    current = _stable(STATE_PATH, "P3.32 live state before publication", MAX_FINAL_RECORD)
    phase = _state_phase(current)
    if phase == "final":
        if current != payload:
            raise FinalizerError("existing P3.32 final state differs")
        return False
    if (len(payload), _sha256(payload)) != EXPECTED_FINAL_STATE:
        raise FinalizerError("P3.32 final state publication identity differs")
    core._write_atomic_bounded(STATE_PATH, value, core.MAX_RESULT_RECORD)  # noqa: SLF001
    retained = _stable(STATE_PATH, "published P3.32 final state", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(STATE_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.32 final state differs")
    return True


def _repair_result_cut(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    final = path.lstat()
    if (
        stat.S_ISLNK(final.st_mode)
        or not stat.S_ISREG(final.st_mode)
        or stat.S_IMODE(final.st_mode) != 0o400
    ):
        raise FinalizerError("P3.32 result type differs")
    if final.st_nlink == 1:
        return
    pattern = re.compile(rf"^\.{re.escape(path.name)}\.[1-9][0-9]*\.[1-9][0-9]*\.tmp$")
    matches = [child for child in path.parent.iterdir() if pattern.fullmatch(child.name)]
    if final.st_nlink != 2 or len(matches) != 1:
        raise FinalizerError("P3.32 result publication cut is ambiguous")
    temporary = matches[0]
    temp = temporary.lstat()
    if (
        stat.S_ISLNK(temp.st_mode)
        or not stat.S_ISREG(temp.st_mode)
        or stat.S_IMODE(temp.st_mode) != 0o400
        or (temp.st_dev, temp.st_ino, temp.st_nlink, temp.st_size)
        != (final.st_dev, final.st_ino, 2, final.st_size)
    ):
        raise FinalizerError("P3.32 result publication cut identity differs")
    temporary.unlink()
    _fsync_dir(path.parent)
    if path.lstat().st_nlink != 1:
        raise FinalizerError("P3.32 result publication cut did not close")


def _publish_result(core: Any, value: dict[str, Any], payload: bytes) -> bool:
    if (len(payload), _sha256(payload)) != EXPECTED_RESULT:
        raise FinalizerError("P3.32 result publication identity differs")
    _repair_result_cut(RESULT_PATH)
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        if _stable(RESULT_PATH, "existing P3.32 result", MAX_FINAL_RECORD) != payload:
            raise FinalizerError("existing P3.32 result differs")
        return False
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    try:
        core._write_exclusive_bounded(temporary, value, core.MAX_RESULT_RECORD)  # noqa: SLF001
        os.link(temporary, RESULT_PATH, follow_symlinks=False)
        _fsync_dir(RESULT_PATH.parent)
    finally:
        temporary.unlink(missing_ok=True)
        _fsync_dir(RESULT_PATH.parent)
    retained = _stable(RESULT_PATH, "published P3.32 result", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.32 result differs")
    return True


def finalize(*, audit_only: bool) -> dict[str, Any]:
    if audit_only:
        reconstructed = reconstruct()
    else:
        live, _core = _load_runtime()
        with live.odin_core.transaction_session(RUN_DIR / "f1-session"):
            reconstructed = reconstruct()
            value, payload, final_state, state_payload, _phase, _live, core = reconstructed
            state_upgraded = _publish_state(core, final_state, state_payload)
            created = _publish_result(core, value, payload)
            reconstructed = reconstruct()
    value, payload, _state, state_payload, phase, _live, _core = reconstructed
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
