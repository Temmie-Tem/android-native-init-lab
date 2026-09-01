#!/usr/bin/env python3
"""Finish the host-only result publication for one CLOSED P3.24 F1 run.

The ordinary publisher stopped after the journal reached CLOSED because adding
the final candidate-arrival projection grew ``live-state.json`` beyond the
shared 32 KiB record limit.  This exact-run finalizer performs no device work:
it reopens the frozen run, derives that one projection, permits only the pinned
pre-state to become the pinned post-state under a dedicated 64 KiB bound, and
publishes only the pinned canonical ``live-result.json``.
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
    "s22plus_fyg8_p324_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-09-01T123633300336437Z"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p324_closed_result_finalizer_v1"
VERDICT = "PASS_P324_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
AUDIT_VERDICT = "PASS_P324_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
EXPECTED_BINDING = "bb75a3ce58043f3538b69acabfd5ee05cdc4e75f8acd2cb0e3f12e8b52abeb36"
EXPECTED_BUNDLE = "47cc7f3693ac5b3b4a784afeb169b9971e4f397d9508c24ce6ee525259201a1e"
EXPECTED_RESULT_VERDICT = "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
EXPECTED_OUTCOME = (
    "p324_acm_primary_native_pid1_arrival_unproved_rollback_verified"
)
EXPECTED_PRE_STATE_SIZE = 29_102
EXPECTED_PRE_STATE_SHA256 = (
    "e3a8b0ea953bb77720fe45f19cd77974a3809de6c29fb2faa013a6380d3338a1"
)
EXPECTED_FINAL_STATE_SIZE = 34_672
EXPECTED_FINAL_STATE_SHA256 = (
    "9f23ecbf34ebec17693d6f5b62283e0b4a0970866d36124d0563919967b1ab24"
)
EXPECTED_RESULT_SIZE = 38_558
EXPECTED_RESULT_SHA256 = (
    "b2eca7a4921e8d8294f3ef9dad01ec6dd18acf4fd4d74aa23015c0b0caf6749a"
)
MAX_FINAL_RECORD = 64 * 1024
CORE_MAX_RECORD = 32 * 1024

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        3_327,
        "d7fecb3a443c0df78c297c1a748f81529b7c486092694032a86e006f39daba54",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        258_279,
        "27824e6beeb0ed06be75971beeacde1f8f491fc65080ed5befd4d70163f83070",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        94_861,
        "9ae2b5e551d10c82fdfd88983f84c65659f3c462aa2702b695e2edc63a7fc78f",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        14_596,
        "14ce808751c8bcacd1456e0c8cdae91f33f44e0d288a447bcd1a309b9c39afcc",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "51f2c6f14f352fd1702734b7d37937f3fb4dab6f48394931ea2dcd6663c910f4",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_076,
        "7489bb3885f30c5c55f410ddd1b2ef9a078690894bdfa9013401c6f102a607c2",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_027,
        "63f11ace3440b168ad777d9bcc1c47589efb483fd4b303ee22b51eb6f14373da",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        1_776,
        "211c2ca47dec5077a0ee60eead5b75155a68c17c8f466267faf938211edf8921",
    ),
    "guard_release": (
        RUN_DIR / "candidate-observer-guard-release.json",
        206,
        "b416c4e1be98d5060c639630b19c514ddcf52401cd15eab5cb45aae6d1738d4d",
    ),
    "p324_lane": (
        RUN_DIR / "p324-candidate-observer-lane.json",
        3_064,
        "fac8490aa57ed491c603f83d4c30b7307a7dcb1b7e453316aa373d966c83596f",
    ),
    "p300_trace": (
        RUN_DIR / "p300-usb-trace/result.json",
        3_133,
        "c375321421cdc413715fce1e3179e329e462cf825fc5f5b7691281a6bcdf8187",
    ),
}


class FinalizerError(RuntimeError):
    """The exact closed-run state/result cannot be finalized."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: os.stat_result) -> tuple[int, ...]:
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
    if (
        len(payload) != before.st_size
        or len(payload) > maximum
        or _identity(before) != _identity(inside)
        or _identity(before) != _identity(after)
    ):
        raise FinalizerError(f"{label} changed while read")
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


def _state_phase(payload: bytes) -> str:
    identity = (len(payload), _sha256(payload))
    if identity == (EXPECTED_PRE_STATE_SIZE, EXPECTED_PRE_STATE_SHA256):
        return "pre"
    if identity == (EXPECTED_FINAL_STATE_SIZE, EXPECTED_FINAL_STATE_SHA256):
        return "final"
    raise FinalizerError("P3.24 live state identity differs")


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


def _validate_with_state(live: Any, value: dict[str, Any], prepared: Any, state: dict[str, Any]) -> None:
    original = live._state  # noqa: SLF001
    live._state = lambda _prepared: state  # noqa: SLF001
    try:
        live.validate_live_result(value, prepared)
    finally:
        live._state = original  # noqa: SLF001


def reconstruct() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, str, Any, Any]:
    if RUN_DIR.absolute() != RUN_DIR.resolve(strict=True) or RUN_DIR.is_symlink():
        raise FinalizerError("exact P3.24 run directory is indirect")
    if not RUN_DIR.is_dir():
        raise FinalizerError("exact P3.24 run directory is absent")
    _verify_exact_files()
    state_payload = _stable_bytes(STATE_PATH, "P3.24 live state", MAX_FINAL_RECORD)
    phase = _state_phase(state_payload)
    live, core = _load_runtime()
    prepared = _load_prepared_stored_lane(live)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
    ):
        raise FinalizerError("prepared P3.24 binding differs")
    journal = core.Journal.reopen(RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    if journal.state() != "CLOSED" or len(records) != 19:
        raise FinalizerError("P3.24 journal is not the exact CLOSED 19-record run")
    if (
        records[-1].get("sequence") != 18
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256")
        != "cf637858e9d72cf2a2560f3e523b8edfd5ce785357106d445223f4d48235a1b7"
    ):
        raise FinalizerError("P3.24 terminal journal record differs")
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
    if _canonical(state) != state_payload:
        raise FinalizerError("P3.24 live state is not canonical")
    if (
        state.get("candidate_classification") != "odin_transfer_completed"
        or state.get("candidate_completed") is not True
        or state.get("candidate_observer_classification") != "identity-mismatch"
        or state.get("candidate_observer_accepted") is not False
        or state.get("candidate_observer_guard_release_status") != "released"
        or state.get("candidate_observer_guard_released") is not True
        or state.get("download_endpoint_absent") is not True
        or state.get("rollback_classification") != "odin_transfer_completed"
        or state.get("rollback_completed") is not True
        or state.get("final_verified") is not True
        or state.get("p324_proof_class") != "NO_PROOF_OBSERVER"
    ):
        raise FinalizerError("P3.24 CLOSED live state differs")
    expected_projection = live._candidate_arrival_proof_projection(  # noqa: SLF001
        prepared, state
    )
    if not isinstance(expected_projection, dict) or expected_projection.get("proof") is not False:
        raise FinalizerError("P3.24 no-proof arrival projection differs")
    if phase == "pre":
        if "candidate_arrival_proof" in state:
            raise FinalizerError("P3.24 pre-state already contains an arrival projection")
        final_state = {**state, "candidate_arrival_proof": expected_projection}
    else:
        if state.get("candidate_arrival_proof") != expected_projection:
            raise FinalizerError("P3.24 final arrival projection differs")
        final_state = state
    final_state_payload = _canonical(final_state)
    if (
        len(final_state_payload) != EXPECTED_FINAL_STATE_SIZE
        or _sha256(final_state_payload) != EXPECTED_FINAL_STATE_SHA256
    ):
        raise FinalizerError("P3.24 reconstructed live state identity differs")

    verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
    if verdict != EXPECTED_RESULT_VERDICT or outcome != EXPECTED_OUTCOME:
        raise FinalizerError("P3.24 terminal classification differs")
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
    _validate_with_state(live, value, prepared, final_state)
    payload = _canonical(value)
    if (
        len(payload) <= CORE_MAX_RECORD
        or len(payload) > MAX_FINAL_RECORD
        or len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
    ):
        raise FinalizerError("P3.24 reconstructed result identity differs")
    _verify_exact_files()
    return value, payload, final_state, final_state_payload, phase, prepared, live


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_temp(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_FINAL_RECORD:
        raise FinalizerError("P3.24 final record exceeds its dedicated bound")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o400,
        )
    except OSError as exc:
        raise FinalizerError("P3.24 result temporary cannot be created") from exc
    try:
        os.fchmod(descriptor, 0o400)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o400
            or opened.st_nlink != 1
            or opened.st_size != 0
        ):
            raise FinalizerError("P3.24 result temporary identity differs")
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise FinalizerError("P3.24 result write made no progress")
            offset += written
        complete = os.fstat(descriptor)
        if (
            complete.st_dev != opened.st_dev
            or complete.st_ino != opened.st_ino
            or complete.st_nlink != 1
            or stat.S_IMODE(complete.st_mode) != 0o400
            or complete.st_size != len(payload)
        ):
            raise FinalizerError("P3.24 result completed identity differs")
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
        raise FinalizerError("P3.24 result type or mode differs")
    if final.st_nlink == 1:
        return
    if final.st_nlink != 2:
        raise FinalizerError("P3.24 result link count differs")
    pattern = re.compile(
        rf"^\.{re.escape(path.name)}\.[1-9][0-9]*\.[1-9][0-9]*\.tmp$"
    )
    candidates = [child for child in path.parent.iterdir() if pattern.fullmatch(child.name)]
    if len(candidates) != 1:
        raise FinalizerError("P3.24 result publication cut is ambiguous")
    temporary = candidates[0]
    temp = temporary.lstat()
    if (
        stat.S_ISLNK(temp.st_mode)
        or not stat.S_ISREG(temp.st_mode)
        or (temp.st_dev, temp.st_ino, temp.st_size, temp.st_nlink)
        != (final.st_dev, final.st_ino, final.st_size, 2)
        or stat.S_IMODE(temp.st_mode) != 0o400
    ):
        raise FinalizerError("P3.24 result publication cut identity differs")
    temporary.unlink()
    _fsync_directory(path.parent)
    if path.lstat().st_nlink != 1:
        raise FinalizerError("P3.24 result publication cut was not repaired")


def _publish_exact(payload: bytes) -> None:
    if (
        len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
    ):
        raise FinalizerError("P3.24 result publication identity differs")
    _repair_publication_cut(RESULT_PATH)
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        raise FinalizerError("P3.24 live result already exists")
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    linked = False
    try:
        _write_temp(temporary, payload)
        try:
            os.link(temporary, RESULT_PATH, follow_symlinks=False)
        except FileExistsError as exc:
            raise FinalizerError("P3.24 live result appeared concurrently") from exc
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
        raise FinalizerError("P3.24 result was not published")
    retained = _stable_bytes(RESULT_PATH, "P3.24 live result", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.24 result bytes differ")


def _publish_final_state(live: Any, prepared: Any, value: dict[str, Any], payload: bytes) -> None:
    current = _stable_bytes(STATE_PATH, "P3.24 live pre-state", MAX_FINAL_RECORD)
    if _state_phase(current) == "final":
        if current != payload:
            raise FinalizerError("existing P3.24 final state differs")
        return
    if len(payload) != EXPECTED_FINAL_STATE_SIZE or _sha256(payload) != EXPECTED_FINAL_STATE_SHA256:
        raise FinalizerError("P3.24 final state publication identity differs")
    core = live.core
    if core.MAX_RECORD != CORE_MAX_RECORD:
        raise FinalizerError("shared record bound changed")
    core.MAX_RECORD = MAX_FINAL_RECORD
    try:
        live._save_state(prepared, value)  # noqa: SLF001
    finally:
        core.MAX_RECORD = CORE_MAX_RECORD
    retained = _stable_bytes(STATE_PATH, "P3.24 final live state", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(STATE_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.24 final state bytes differ")


def finalize(*, audit_only: bool) -> dict[str, Any]:
    value, payload, final_state, state_payload, phase, prepared, live = reconstruct()
    _repair_publication_cut(RESULT_PATH)
    result_existed = RESULT_PATH.exists() or RESULT_PATH.is_symlink()
    state_upgraded = False
    if result_existed:
        retained = _stable_bytes(RESULT_PATH, "existing P3.24 live result", MAX_FINAL_RECORD)
        if retained != payload or phase != "final":
            raise FinalizerError("existing P3.24 live result differs")
        _validate_with_state(live, value, prepared, final_state)
        if not audit_only:
            raise FinalizerError("P3.24 live result already published")
    elif not audit_only:
        if phase == "pre":
            _publish_final_state(live, prepared, final_state, state_payload)
            state_upgraded = True
        _publish_exact(payload)
        retained_state = _stable_bytes(
            STATE_PATH, "published P3.24 final live state", MAX_FINAL_RECORD
        )
        if retained_state != state_payload:
            raise FinalizerError("P3.24 final state changed after publication")
        _validate_with_state(live, value, prepared, final_state)
    return {
        "schema": SCHEMA,
        "verdict": AUDIT_VERDICT if audit_only else VERDICT,
        "run_dir": str(RUN_DIR),
        "state": {
            "path": str(STATE_PATH),
            "size": len(state_payload),
            "sha256": _sha256(state_payload),
            "phase_before": phase,
            "upgraded": state_upgraded,
        },
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
        "already_present": result_existed,
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
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
