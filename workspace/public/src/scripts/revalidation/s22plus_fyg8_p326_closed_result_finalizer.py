#!/usr/bin/env python3
"""Publish the exact oversized result for one already-CLOSED P3.26 run.

The candidate transfer, positive bounded observation, exact rollback, and final
health are already durable.  Only the canonical ``live-result.json`` exceeded
the shared 32 KiB host-record bound.  This finalizer has no device backend and
accepts one pinned CLOSED run and one pinned 33,879-byte result under a local
64 KiB publication bound.
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
    "s22plus_fyg8_p326_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "f1-2026-09-01T205241481447Z-1788295961481481403"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p326_closed_result_finalizer_v1"
VERDICT = "PASS_P326_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
AUDIT_VERDICT = "PASS_P326_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
EXPECTED_BINDING = (
    "60e6e2ce130c20ed3b1597de574ea4219ad9836a3f58db09219c936aca5a0a82"
)
EXPECTED_BUNDLE = (
    "343f95d5778cbbcda55a1c4cb9a9496e977427234e2e0dc928cb876a5e15c8b1"
)
EXPECTED_RESULT_VERDICT = (
    "PASS_F1_V2_P326_NATIVE_PID1_BIDIRECTIONAL_USB_BUSYBOX_SHELL_AND_ROLLED_BACK"
)
EXPECTED_OUTCOME = (
    "p326_native_pid1_bidirectional_usb_busybox_shell_rollback_verified"
)
EXPECTED_STATE_SIZE = 30_189
EXPECTED_STATE_SHA256 = (
    "565e16113ab58d7d2859bd9af01ac83397f2675a3390f7d3314b8b1e0679e028"
)
EXPECTED_RESULT_SIZE = 33_879
EXPECTED_RESULT_SHA256 = (
    "a78a9c50c8242506e6f531cc3d48f5fcadbe19410b1da8a7fc5215847aef91b5"
)
EXPECTED_TERMINAL_RECORD_SHA256 = (
    "1d5f0dc7ee87ca7bfc350898277918b1e95786633bbf92ac7923db26bcfc3517"
)
CORE_MAX_RECORD = 32 * 1024
MAX_FINAL_RECORD = 64 * 1024

EXACT_FILES = {
    "manifest": (
        MANIFEST,
        3_533,
        "840878c4875f511799671c071a73db83294871be3f93cf71783cbea4e2496b0a",
    ),
    "live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        276_379,
        "8301f090864498500d305290d2c400e11780a221f33afb03de363067d7149785",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        100_820,
        "9b499dcb3e93c8de615db84ffc48b1ab6abec8b85f1f2990981d856d2b6bb793",
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        15_768,
        "b113ca368a2b742c26b258c040e559eafc11cde33aa267acbe55faa126f4c826",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "a3c984009181221e944e9fe49422565195b83d22dc7367c44e514137940cd2d8",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_127,
        "4d36051e92d1530fef08bc94103197b6e2e6d264f3c2dba3b1b771e85a4782c1",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_078,
        "87e75f9939c5541f1421b07e334570847814525b055944680f6cfb24c99a5d97",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        1_803,
        "acfd4747307ca793c00537d9bd5f96dc9c4548a32082dff094c970a5d33627c1",
    ),
    "candidate_observer_raw": (
        RUN_DIR / "candidate-observer.raw",
        145,
        "8e5136ac8d61b322595d2795ab946022ba2818f0100214a1e47358b88f3c6279",
    ),
    "candidate_observer_capture": (
        RUN_DIR / "candidate-observer.capture.json",
        513,
        "773ba231169979103236a5361212f04f17d7b4832e9346ec2294f7e96ce65c9f",
    ),
    "p326_roundtrip": (
        RUN_DIR / "p326-candidate-observer-roundtrip.json",
        1_355,
        "0981eb9dd40318f3d1ce23ddfe4fe54034259ce13191e9821b90d67151a7fc54",
    ),
    "guard_release": (
        RUN_DIR / "candidate-observer-guard-release.json",
        206,
        "9f575b5cd579993b1976e1e91739f5507c9b4ee1606a6204a272e0f238f1da7f",
    ),
    "p324_lane": (
        RUN_DIR / "p324-candidate-observer-lane.json",
        3_113,
        "d7f2094a69f1532516e98405c08c9f12acc4f9b4d7069e48885247cecc76fbb6",
    ),
    "p300_trace": (
        RUN_DIR / "p300-usb-trace/result.json",
        3_164,
        "2c8d278d5394e068a4af1c5a42f9833b4b7e662c073cc0ab6e82d8f7b85969a6",
    ),
    "live_state": (STATE_PATH, EXPECTED_STATE_SIZE, EXPECTED_STATE_SHA256),
}


class FinalizerError(RuntimeError):
    """The exact P3.26 CLOSED result cannot be reconstructed or published."""


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


def _read_only_journal(core: Any, path: Path, binding: str) -> Any:
    journal = core.Journal(path, binding)
    journal.records()
    return journal


def _with_stored_lane(live: Any) -> Any:
    original = live._p324_typec_lane_value  # noqa: SLF001

    def stored_lane(prepared: Any, **_kwargs: Any) -> Any:
        return original(prepared, revalidate=False)

    live._p324_typec_lane_value = stored_lane  # noqa: SLF001
    return original


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
        raise FinalizerError("exact P3.26 run directory is indirect")
    live, core = _load_runtime()
    original_lane = _with_stored_lane(live)
    try:
        prepared = live.load_prepared(ROOT, MANIFEST, RUN_DIR)
        if (
            prepared.binding_sha256 != EXPECTED_BINDING
            or prepared.bundle.sha256 != EXPECTED_BUNDLE
            or prepared.run_dir != RUN_DIR
        ):
            raise FinalizerError("prepared P3.26 binding differs")
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
            raise FinalizerError("P3.26 journal is not the exact CLOSED/19 run")
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
        state_payload = _stable_bytes(
            STATE_PATH, "P3.26 live state", MAX_FINAL_RECORD
        )
        state = live._state(prepared)  # noqa: SLF001
        if _canonical(state) != state_payload:
            raise FinalizerError("P3.26 live state is not canonical")
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
            or state.get("p326_proof_class") != "NO_PROOF_OBSERVER"
        ):
            raise FinalizerError("P3.26 CLOSED live state differs")
        projection = live._candidate_arrival_proof_projection(  # noqa: SLF001
            prepared, state
        )
        if (
            not isinstance(projection, dict)
            or projection.get("proof") is not True
            or projection.get("banner_size") != 145
            or projection.get("pid1_bidirectional_proof") is not True
            or projection.get("busybox_shell_roundtrip_proof") is not True
            or projection.get("supplemental_carrier") is not None
            or state.get("candidate_arrival_proof") != projection
        ):
            raise FinalizerError("P3.26 positive arrival projection differs")
        verdict, outcome = live._closed_terminal_classification(prepared)  # noqa: SLF001
        if verdict != EXPECTED_RESULT_VERDICT or outcome != EXPECTED_OUTCOME:
            raise FinalizerError("P3.26 terminal classification differs")
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
    finally:
        live._p324_typec_lane_value = original_lane  # noqa: SLF001
    if (
        len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
        or len(payload) <= CORE_MAX_RECORD
        or len(payload) > MAX_FINAL_RECORD
    ):
        raise FinalizerError("P3.26 reconstructed result identity differs")
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
    if len(payload) != EXPECTED_RESULT_SIZE or _sha256(payload) != EXPECTED_RESULT_SHA256:
        raise FinalizerError("P3.26 result publication identity differs")
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        raise FinalizerError("P3.26 live result already exists")
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise FinalizerError("P3.26 result write made no progress")
            offset += written
        os.fsync(descriptor)
        complete = os.fstat(descriptor)
        if (
            not stat.S_ISREG(complete.st_mode)
            or stat.S_IMODE(complete.st_mode) != 0o400
            or complete.st_nlink != 1
            or complete.st_size != len(payload)
        ):
            raise FinalizerError("P3.26 result temporary identity differs")
    finally:
        os.close(descriptor)
    try:
        os.link(temporary, RESULT_PATH, follow_symlinks=False)
        _fsync_dir(RESULT_PATH.parent)
    finally:
        temporary.unlink(missing_ok=True)
        _fsync_dir(RESULT_PATH.parent)
    retained = _stable_bytes(RESULT_PATH, "P3.26 live result", MAX_FINAL_RECORD)
    if (
        retained != payload
        or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400
        or RESULT_PATH.stat().st_nlink != 1
    ):
        raise FinalizerError("published P3.26 result differs")


def finalize(*, audit_only: bool) -> dict[str, Any]:
    value, payload, _live, _prepared, _state = reconstruct()
    already_present = RESULT_PATH.exists() or RESULT_PATH.is_symlink()
    if already_present:
        retained = _stable_bytes(
            RESULT_PATH, "existing P3.26 live result", MAX_FINAL_RECORD
        )
        if retained != payload:
            raise FinalizerError("existing P3.26 live result differs")
        if not audit_only:
            raise FinalizerError("P3.26 live result is already published")
    elif not audit_only:
        _publish(payload)
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
