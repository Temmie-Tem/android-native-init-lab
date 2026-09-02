#!/usr/bin/env python3
"""Reconstruct and, only when requested, publish one consumed P3.27 result.

The P3.27 candidate and its exact Magisk rollback are already durable and the
journal is CLOSED.  The live runner wrote a valid framed observer receipt but
its first post-run projection was made before the receipt could be reopened;
the shared 32 KiB record bound then prevented the final result from being
written.  This run-specific finalizer repairs only that host projection and
publishes the resulting oversized state/result under a 64 KiB bound.

The default is a read-only audit.  ``--publish`` is the only mode that may
replace the exact pinned pre-state or create the missing result.  No device
backend, ADB, USB, or Odin operation is present in this module.
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
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p327_process_v2_ready_1.json"
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "p327-ready1-prepared-20260902-4"
)
STATE_PATH = RUN_DIR / "live-state.json"
RESULT_PATH = RUN_DIR / "live-result.json"

SCHEMA = "s22plus_fyg8_p327_closed_result_finalizer_v1"
AUDIT_VERDICT = "PASS_P327_CLOSED_RESULT_RECONSTRUCTED_HOST_ONLY"
PUBLISH_VERDICT = "PASS_P327_CLOSED_RESULT_PUBLISHED_HOST_ONLY"
EXPECTED_BINDING = (
    "c5a1c56728958b1153ce7c889dee233ee389c5edffb5a703ae54073172824c4d"
)
EXPECTED_BUNDLE = (
    "be4aea3badf885a972090258839faa9aae00d09b0eed290f33fa72ff27d0c960"
)
EXPECTED_EXECUTION_CLOSURE = (
    "ef8911407a7735e190aa1ac3b8b7f28820c00486c1602deff323dc0cf9ea9f8c"
)
# This is the reviewed host-side repair used to reopen the retained receipt.
# It is intentionally separate from the frozen execution closure above: the
# repair changes only projection validation and never candidate bytes.
EXPECTED_REPAIRED_LIVE_SIZE = 322_750
EXPECTED_REPAIRED_LIVE_SHA256 = (
    "d0dde8d3314909183c52d2a00d090da3ce7307a3025b594a80703943c9551a0f"
)
EXPECTED_RESULT_VERDICT = (
    "PASS_F1_V2_P327_NATIVE_PID1_FRAMED_EXEC_FIXED_COMMANDS_AND_ROLLED_BACK"
)
EXPECTED_OUTCOME = "p327_native_pid1_framed_exec_fixed_commands_rollback_verified"
EXPECTED_TERMINAL_RECORD = (
    "3c463f547f75b8713cb0051c27276cbf34243ec2afcc086757b585613e73fe1f"
)
EXPECTED_PRE_STATE_SIZE = 30_308
EXPECTED_PRE_STATE_SHA256 = (
    "70b0d09b36b63d14d7002dd4a882e6eec10fa8e5dc606044b49538210da6b2c8"
)
EXPECTED_FINAL_STATE_SIZE = 30_381
EXPECTED_FINAL_STATE_SHA256 = (
    "138cf273439433f7fd243b2b56e0b9b7cca24d13b6590245f53af52d510d4e3d"
)
EXPECTED_RESULT_SIZE = 34_047
EXPECTED_RESULT_SHA256 = (
    "ee36e0db25ef916a131f99907c5b93daf18eff58defd9693d966e200022973da"
)
CORE_MAX_RECORD = 32 * 1024
MAX_FINAL_RECORD = 64 * 1024


class FinalizerError(RuntimeError):
    """The exact consumed P3.27 run cannot be reconstructed safely."""


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


def _compact_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return _sha256(payload)


def _receipt(path: Path, label: str, maximum: int = 1024 * 1024) -> dict[str, Any]:
    payload = _stable_bytes(path, label, maximum)
    return {"path": str(path), "size": len(payload), "sha256": _sha256(payload)}


EXACT_FILES = {
    "manifest": (
        MANIFEST,
        4_105,
        "c5a4a4abcc4ae00951d895c1ae899a66acdbda1fdea2467b7fdf87fe340b9d2c",
    ),
    "core_source": (
        REVALIDATION / "device_action_f1_v2.py",
        105_207,
        "588674ecbff3f2af79b3c092d10931a3e8e7456be312eae5e808ada1d478c1c3",
    ),
    "repaired_live_source": (
        REVALIDATION / "device_action_f1_live_v2.py",
        EXPECTED_REPAIRED_LIVE_SIZE,
        EXPECTED_REPAIRED_LIVE_SHA256,
    ),
    "prepared": (
        RUN_DIR / "prepared.json",
        16_913,
        "24195a0402efdef0394bba2d999fa7b567372f8320d4ea43ebd3676ecf26d173",
    ),
    "journal_head": (
        RUN_DIR / "transaction/journal-head.json",
        276,
        "49c0a2154f6149c7fd73bda44bfb7e1827b8f840cd2b09708a5560ada6650852",
    ),
    "candidate_result": (
        RUN_DIR / "candidate-attempt-01.result.json",
        2_079,
        "252b60dacddd41b92038529b53c5f801cebf4184346084b40fe04351fd54b0bd",
    ),
    "rollback_result": (
        RUN_DIR / "rollback-attempt-01.result.json",
        2_030,
        "28976d93c339421c2f2d204d5932f170838479fc7e16e96b12b5526cc17fafc8",
    ),
    "candidate_observer": (
        RUN_DIR / "candidate-observer.json",
        7_701,
        "b8c013edcd2d8184ffab32e6c9e25395af355326f04727940cd976ff6a4161b8",
    ),
    "candidate_observer_raw": (
        RUN_DIR / "candidate-observer.raw",
        445,
        "100bf5c9011b4340bed9636becbcc467faac946f85d68001dfad9de77e761813",
    ),
    "candidate_observer_capture": (
        RUN_DIR / "candidate-observer.capture.json",
        518,
        "4d6b59b4e5f1b51f9a151b0ce3b832261b77514f5f25728c59582cf907fa6418",
    ),
    "guard_release": (
        RUN_DIR / "candidate-observer-guard-release.json",
        206,
        "366bc64880cc702e2bc09a3a9b4415487a9dc5baaf119b9ccc2350f9ddcebf87",
    ),
    "lane": (
        RUN_DIR / "p324-candidate-observer-lane.json",
        3_139,
        "115c34adc9c953a9af6e6b7c19983922a63e00efec4c40da85d7871d8064eb4f",
    ),
    "lane_arm": (
        RUN_DIR / "p324-candidate-observer-lane-arm.json",
        2_166,
        "12d2497d87514c1427d5c537f9a57d89a483572b7fcae0b9e68b759caf6cc853",
    ),
    "lane_binding": (
        RUN_DIR / "p324-typec-lane-binding.json",
        1_829,
        "3f80a810d55f39fd899a536be3b5e1fdcb5760918d7dfaf21b2bfb1422a9fa69",
    ),
    "p300_result": (
        RUN_DIR / "p300-usb-trace/result.json",
        3_133,
        "923574e4c7db987bdfb3d46cbff38de7f539d817557acd90fe6c4199da7efaaa",
    ),
    "p300_binding": (
        RUN_DIR / "p300-usb-trace-binding.json",
        1_733,
        "6eac6b86a8c7fb1a56b0399f8d92d9daba362c76a58eb508329617a7376217a0",
    ),
    "p300_process": (
        RUN_DIR / "p300-usb-trace-process.json",
        513,
        "582698f7e8dd769da47034030a9f3f255230a8317e92560937330f1504005707",
    ),
    "p300_witness": (
        RUN_DIR / "p300-candidate-observation-durable.json",
        569,
        "87ac6c526c6de6c144ac5db439992a29185028c4163b5e6c7199f189cd751eed",
    ),
}


def _verify_exact_files() -> None:
    for label, (path, size, digest) in EXACT_FILES.items():
        payload = _stable_bytes(path, label)
        if len(payload) != size or _sha256(payload) != digest:
            raise FinalizerError(f"{label} identity differs")


def _load_runtime() -> tuple[Any, Any]:
    _verify_exact_files()
    sys.path.insert(0, str(REVALIDATION))
    import device_action_f1_live_v2 as live  # noqa: PLC0415
    import device_action_f1_v2 as core  # noqa: PLC0415

    if (
        Path(core.__file__).resolve(strict=True) != EXACT_FILES["core_source"][0]
        or live.core is not core
        or core.MAX_RECORD != CORE_MAX_RECORD
    ):
        raise FinalizerError("loaded Process-v2 runtime identity differs")
    return live, core


def _load_prepared_frozen(live: Any, prepared_closure: dict[str, Any]) -> Any:
    """Load the run while retaining its frozen closure and stored lane.

    ``load_prepared`` normally recomputes the execution closure and performs a
    live Type-C revalidation.  A CLOSED run must do neither: its closure is
    already retained in prepared.json and its lane receipt is the evidence to
    reopen.  Both substitutions are scoped to this call and then restored.
    """

    original_closure = live._closure  # noqa: SLF001
    original_lane = live._p324_typec_lane_value  # noqa: SLF001

    def frozen_closure(_root: Path, _bundle: Any = None) -> dict[str, Any]:
        return prepared_closure

    def stored_lane(prepared: Any, **_kwargs: Any) -> Any:
        return original_lane(prepared, revalidate=False)

    live._closure = frozen_closure  # noqa: SLF001
    live._p324_typec_lane_value = stored_lane  # noqa: SLF001
    try:
        return live.load_prepared(ROOT, MANIFEST, RUN_DIR)
    finally:
        live._closure = original_closure  # noqa: SLF001
        live._p324_typec_lane_value = original_lane  # noqa: SLF001


def _read_only_journal(core: Any, path: Path, binding: str) -> Any:
    journal = core.Journal(path, binding)
    journal.records()
    return journal


def _validate_with_state(
    live: Any, value: dict[str, Any], prepared: Any, state: dict[str, Any]
) -> None:
    """Run the ordinary validator with an in-memory corrected state."""

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


def _state_phase(payload: bytes) -> str:
    identity = (len(payload), _sha256(payload))
    if identity == (EXPECTED_PRE_STATE_SIZE, EXPECTED_PRE_STATE_SHA256):
        return "pre"
    if identity == (EXPECTED_FINAL_STATE_SIZE, EXPECTED_FINAL_STATE_SHA256):
        return "final"
    raise FinalizerError("P3.27 live state identity differs")


def _expected_old_state(state: dict[str, Any]) -> None:
    expected = {
        "candidate_classification": "odin_transfer_completed",
        "candidate_completed": True,
        "candidate_observer_classification": "interrupted-before-receipt",
        "candidate_observer_accepted": False,
        "candidate_observer_receipt_sha256": None,
        "candidate_observer_guard_release_status": "released",
        "candidate_observer_guard_released": True,
        "download_endpoint_absent": False,
        "rollback_classification": "odin_transfer_completed",
        "rollback_completed": True,
        "final_verified": True,
        "p327_proof_class": "NO_PROOF_OBSERVER",
    }
    for key, expected_value in expected.items():
        actual_value = state.get(key)
        if type(expected_value) is bool:
            if type(actual_value) is not bool or actual_value != expected_value:
                raise FinalizerError(
                    "P3.27 live pre-state is not the pinned projection defect"
                )
        elif actual_value != expected_value:
            raise FinalizerError(
                "P3.27 live pre-state is not the pinned projection defect"
            )
    old_proof = {
        "banner_size": 49,
        "busybox_ash_command_proof": False,
        "caller_selected_command": True,
        "candidate_lane_inventory_exact": False,
        "candidate_transfer_completed": True,
        "download_departure": False,
        "final_healthy_return": True,
        "framed_session_closed": False,
        "guard_released": True,
        "interactive_pty_proof": True,
        "observer_receipt_accepted": False,
        "observer_receipt_classification": "interrupted-before-receipt",
        "observer_receipt_sha256": None,
        "observer_receipt_valid": False,
        "pid1_framed_exec_proof": False,
        "primary_source": "candidate_observer",
        "proof": False,
        "role": "p327_framed_fixed_command_session_v1",
        "rollback_transfer_completed": True,
        "same_run_typec_partner_continuity": False,
        "schema": "device_action_f1_candidate_arrival_proof_v1",
        "supplemental_carrier": None,
        "target_topology_continuity": False,
    }
    if state.get("candidate_arrival_proof") != old_proof:
        raise FinalizerError("P3.27 old arrival projection differs")


def _correct_state(
    live: Any, prepared: Any, state: dict[str, Any], phase: str
) -> dict[str, Any]:
    if phase == "pre":
        _expected_old_state(state)
    elif phase != "final":
        raise FinalizerError("P3.27 live state phase is invalid")
    durable = live._reopen_candidate_observation(prepared)  # noqa: SLF001
    required = {
        "classification": "accepted",
        "accepted": True,
        "valid_receipt": True,
        "download_endpoint_absent": True,
        "bounded": True,
        "pid1_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "framed_session_closed": True,
        "both_topologies_inventory_complete": True,
        "accepted_inventory_exact": True,
        "same_run_typec_partner_continuity": True,
        "accepted_for_p324": True,
    }
    if any(durable.get(key) != value for key, value in required.items()):
        raise FinalizerError("retained P3.27 observer did not reopen as exact proof")
    # The receipt fields themselves are negative claims.  The live-state
    # projection stores their derived positive proof flags, so check both
    # representations explicitly instead of conflating them.
    receipt = json.loads(
        _stable_bytes(
            RUN_DIR / "candidate-observer.json",
            "P3.27 observer receipt",
        ).decode("utf-8")
    )
    if (
        receipt.get("interactive_pty_proof") is not False
        or receipt.get("caller_selected_command") is not False
    ):
        raise FinalizerError("P3.27 observer receipt has forbidden command flags")
    corrected = dict(state)
    corrected.update(
        {
            "candidate_observer_classification": durable["classification"],
            "candidate_observer_accepted": durable["accepted"],
            "candidate_observer_receipt_sha256": durable["receipt_sha256"],
            "download_endpoint_absent": durable["download_endpoint_absent"],
            "pid1_framed_exec_proof": durable["pid1_framed_exec_proof"],
            "busybox_ash_command_proof": durable["busybox_ash_command_proof"],
            "framed_session_closed": durable["framed_session_closed"],
            "interactive_pty_proof": durable["interactive_pty_proof"],
            "caller_selected_command": durable["caller_selected_command"],
        }
    )
    # Compute the projection only after the corrected departure/observer
    # values are in memory.  The independent Carrier remains NO_PROOF and is
    # deliberately not rewritten here.
    projection = live._candidate_arrival_proof_projection(  # noqa: SLF001
        prepared, corrected
    )
    if not isinstance(projection, dict) or projection.get("proof") is not True:
        raise FinalizerError("P3.27 corrected arrival projection is not positive")
    if (
        projection.get("observer_receipt_sha256") != durable["receipt_sha256"]
        or projection.get("observer_receipt_classification") != "accepted"
        or projection.get("target_topology_continuity") is not True
        or projection.get("download_departure") is not True
        or projection.get("candidate_lane_inventory_exact") is not True
        or projection.get("same_run_typec_partner_continuity") is not True
        or projection.get("interactive_pty_proof") is not False
        or projection.get("caller_selected_command") is not False
    ):
        raise FinalizerError("P3.27 corrected arrival projection differs")
    corrected["candidate_arrival_proof"] = projection
    return corrected


def _validate_external_lane() -> None:
    """Bind the retained supplement to the exact framed receipt."""

    observer = json.loads(
        _stable_bytes(
            RUN_DIR / "candidate-observer.json", "P3.27 observer receipt"
        ).decode("utf-8")
    )
    lane = json.loads(
        _stable_bytes(
            RUN_DIR / "p324-candidate-observer-lane.json",
            "P3.27 lane supplement",
        ).decode("utf-8")
    )
    embedded = observer.get("lane")
    if not isinstance(embedded, dict) or not isinstance(lane, dict):
        raise FinalizerError("P3.27 retained lane supplement is malformed")
    base = lane.get("base_observer")
    expected_base = _receipt(
        RUN_DIR / "candidate-observer.json", "P3.27 observer receipt"
    )
    if base != expected_base:
        raise FinalizerError("P3.27 lane supplement is not bound to observer")
    without_base = {key: value for key, value in lane.items() if key != "base_observer"}
    if without_base != embedded:
        raise FinalizerError("P3.27 lane supplement differs from observer lane")


def reconstruct() -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, str, Any, Any]:
    if RUN_DIR.is_symlink() or RUN_DIR.absolute() != RUN_DIR.resolve(strict=True):
        raise FinalizerError("exact P3.27 run directory is indirect")
    if not RUN_DIR.is_dir():
        raise FinalizerError("exact P3.27 run directory is absent")
    _verify_exact_files()
    state_payload = _stable_bytes(STATE_PATH, "P3.27 live state", MAX_FINAL_RECORD)
    phase = _state_phase(state_payload)
    prepared_record = json.loads(
        _stable_bytes(RUN_DIR / "prepared.json", "prepared record").decode("utf-8")
    )
    closure = prepared_record.get("execution_closure")
    if (
        not isinstance(closure, dict)
        or closure.get("schema") != "device_action_f1_execution_closure_v2"
        or closure.get("sha256") != EXPECTED_EXECUTION_CLOSURE
        or _compact_json_sha256(
            {key: value for key, value in closure.items() if key != "sha256"}
        )
        != EXPECTED_EXECUTION_CLOSURE
    ):
        raise FinalizerError("frozen P3.27 execution closure differs")
    live, core = _load_runtime()
    prepared = _load_prepared_frozen(live, closure)
    if (
        prepared.binding_sha256 != EXPECTED_BINDING
        or prepared.bundle.sha256 != EXPECTED_BUNDLE
        or prepared.run_dir != RUN_DIR
        or prepared.prepared.get("execution_closure") != closure
    ):
        raise FinalizerError("prepared P3.27 binding differs")
    journal = _read_only_journal(core, RUN_DIR / "transaction", EXPECTED_BINDING)
    records = journal.records()
    if (
        journal.state() != "CLOSED"
        or len(records) != 19
        or [record.get("sequence") for record in records] != list(range(19))
        or records[-1].get("state") != "CLOSED"
        or records[-1].get("record_sha256") != EXPECTED_TERMINAL_RECORD
    ):
        raise FinalizerError("P3.27 journal is not the pinned CLOSED/19 run")
    if any(
        path.exists() or path.is_symlink()
        for path in (
            RUN_DIR / "candidate-attempt-02.start.json",
            RUN_DIR / "candidate-attempt-02.result.json",
            RUN_DIR / "rollback-attempt-02.start.json",
            RUN_DIR / "rollback-attempt-02.result.json",
        )
    ):
        raise FinalizerError("a second candidate or rollback attempt exists")
    candidate = live._validate_transfer_result(prepared, "candidate", 1)  # noqa: SLF001
    rollback = live._validate_transfer_result(prepared, "rollback", 1)  # noqa: SLF001
    if (
        candidate.get("classification") != "odin_transfer_completed"
        or rollback.get("classification") != "odin_transfer_completed"
    ):
        raise FinalizerError("candidate or rollback transfer closure differs")
    _validate_external_lane()
    state = live._state(prepared)  # noqa: SLF001
    if _canonical(state) != state_payload:
        raise FinalizerError("P3.27 live state is not canonical")
    corrected = _correct_state(live, prepared, state, phase)
    if phase == "final" and corrected != state:
        raise FinalizerError("P3.27 final live state projection differs")
    corrected_payload = _canonical(corrected)
    if (
        len(corrected_payload) != EXPECTED_FINAL_STATE_SIZE
        or _sha256(corrected_payload) != EXPECTED_FINAL_STATE_SHA256
    ):
        raise FinalizerError("P3.27 corrected live-state identity differs")
    # Validate the repaired state and result entirely in memory.  This also
    # reopens the journal through the read-only constructor, not Journal.reopen.
    verdict, outcome = (
        live.typed_evidence.P327_FRAMED_EXEC_VERDICT,
        live.typed_evidence.P327_FRAMED_EXEC_OUTCOME,
    )
    if verdict != EXPECTED_RESULT_VERDICT or outcome != EXPECTED_OUTCOME:
        raise FinalizerError("P3.27 terminal classification differs")
    value = {
        "schema": live.LIVE_RESULT_SCHEMA,
        "adapter_version": live.ADAPTER_VERSION,
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "bundle_sha256": prepared.bundle.sha256,
        "approval_binding_sha256": prepared.binding_sha256,
        "journal": journal.receipt(),
        "current_state": journal.state(),
        "timeline": core.timeline(records),
        "live_state": corrected,
        "verdict": verdict,
        "outcome_class": outcome,
        "recovery_required": False,
    }
    _validate_with_state(live, value, prepared, corrected)
    result_payload = _canonical(value)
    if (
        len(result_payload) <= CORE_MAX_RECORD
        or len(result_payload) > MAX_FINAL_RECORD
        or len(result_payload) != EXPECTED_RESULT_SIZE
        or _sha256(result_payload) != EXPECTED_RESULT_SHA256
    ):
        raise FinalizerError("P3.27 corrected result identity differs")
    _verify_exact_files()
    return (
        value,
        result_payload,
        corrected,
        corrected_payload,
        phase,
        prepared,
        live,
    )


def _fsync_dir(path: Path) -> None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_temp(path: Path, payload: bytes) -> None:
    if len(payload) > MAX_FINAL_RECORD:
        raise FinalizerError("P3.27 final record exceeds its dedicated bound")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != 0o400
            or opened.st_nlink != 1
            or opened.st_size != 0
        ):
            raise FinalizerError("P3.27 temporary identity differs")
        offset = 0
        while offset < len(payload):
            try:
                written = os.write(descriptor, payload[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise FinalizerError("P3.27 temporary write made no progress")
            offset += written
        complete = os.fstat(descriptor)
        if (
            (complete.st_dev, complete.st_ino) != (opened.st_dev, opened.st_ino)
            or complete.st_nlink != 1
            or stat.S_IMODE(complete.st_mode) != 0o400
            or complete.st_size != len(payload)
        ):
            raise FinalizerError("P3.27 completed temporary identity differs")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_state(
    live: Any, prepared: Any, corrected: dict[str, Any], payload: bytes
) -> None:
    current = _stable_bytes(STATE_PATH, "P3.27 live pre-state", MAX_FINAL_RECORD)
    phase = _state_phase(current)
    if phase == "final":
        if current != payload:
            raise FinalizerError("P3.27 existing final state differs")
        return
    if phase != "pre" or current != _canonical(live._state(prepared)):  # noqa: SLF001
        raise FinalizerError("P3.27 live pre-state changed before repair")
    if len(payload) != EXPECTED_FINAL_STATE_SIZE or _sha256(payload) != EXPECTED_FINAL_STATE_SHA256:
        raise FinalizerError("P3.27 final state identity differs")
    core = live.core
    if core.MAX_RECORD != CORE_MAX_RECORD:
        raise FinalizerError("shared record bound changed")
    core.MAX_RECORD = MAX_FINAL_RECORD
    try:
        live._save_state(prepared, corrected)  # noqa: SLF001
    finally:
        core.MAX_RECORD = CORE_MAX_RECORD
    retained = _stable_bytes(STATE_PATH, "P3.27 final live state", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(STATE_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("P3.27 final state publication differs")


def _repair_publication_cut(path: Path) -> None:
    """Remove only the private temporary alias of an exact result inode."""

    if not path.exists() and not path.is_symlink():
        return
    final = path.lstat()
    if (
        stat.S_ISLNK(final.st_mode)
        or not stat.S_ISREG(final.st_mode)
        or stat.S_IMODE(final.st_mode) != 0o400
    ):
        raise FinalizerError("P3.27 result type or mode differs")
    if final.st_nlink == 1:
        return
    if final.st_nlink != 2:
        raise FinalizerError("P3.27 result link count differs")
    pattern = re.compile(
        rf"^\.{re.escape(path.name)}\.[1-9][0-9]*\.[1-9][0-9]*\.tmp$"
    )
    candidates = [
        child for child in path.parent.iterdir() if pattern.fullmatch(child.name)
    ]
    if len(candidates) != 1:
        raise FinalizerError("P3.27 result publication cut is ambiguous")
    temporary = candidates[0]
    temp = temporary.lstat()
    if (
        stat.S_ISLNK(temp.st_mode)
        or not stat.S_ISREG(temp.st_mode)
        or stat.S_IMODE(temp.st_mode) != 0o400
        or (temp.st_dev, temp.st_ino, temp.st_size, temp.st_nlink)
        != (final.st_dev, final.st_ino, final.st_size, 2)
    ):
        raise FinalizerError("P3.27 result publication cut identity differs")
    temporary.unlink()
    _fsync_dir(path.parent)
    if path.lstat().st_nlink != 1:
        raise FinalizerError("P3.27 result publication cut was not repaired")


def _publish_result(payload: bytes) -> None:
    if (
        len(payload) != EXPECTED_RESULT_SIZE
        or _sha256(payload) != EXPECTED_RESULT_SHA256
    ):
        raise FinalizerError("P3.27 result publication identity differs")
    _repair_publication_cut(RESULT_PATH)
    if RESULT_PATH.exists() or RESULT_PATH.is_symlink():
        raise FinalizerError("P3.27 live result already exists")
    temporary = RESULT_PATH.with_name(
        f".{RESULT_PATH.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    linked = False
    try:
        _write_temp(temporary, payload)
        try:
            os.link(temporary, RESULT_PATH, follow_symlinks=False)
        except FileExistsError as exc:
            raise FinalizerError("P3.27 live result appeared concurrently") from exc
        linked = True
        _fsync_dir(RESULT_PATH.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        else:
            _fsync_dir(RESULT_PATH.parent)
    if not linked:
        raise FinalizerError("P3.27 result was not published")
    retained = _stable_bytes(RESULT_PATH, "P3.27 live result", MAX_FINAL_RECORD)
    if retained != payload or stat.S_IMODE(RESULT_PATH.stat().st_mode) != 0o400:
        raise FinalizerError("published P3.27 result bytes differ")


def finalize(*, publish: bool = False) -> dict[str, Any]:
    value, result_payload, corrected, state_payload, phase, prepared, live = reconstruct()
    if publish:
        _repair_publication_cut(RESULT_PATH)
    result_present = RESULT_PATH.exists() or RESULT_PATH.is_symlink()
    if result_present:
        retained = _stable_bytes(RESULT_PATH, "existing P3.27 live result", MAX_FINAL_RECORD)
        if retained != result_payload:
            raise FinalizerError("existing P3.27 live result differs")
        if phase != "final":
            raise FinalizerError("P3.27 result exists before final state")
        if publish:
            raise FinalizerError("P3.27 live result is already published")
    if publish:
        _publish_state(live, prepared, corrected, state_payload)
        if not result_present:
            _publish_result(result_payload)
    return {
        "schema": SCHEMA,
        "verdict": PUBLISH_VERDICT if publish else AUDIT_VERDICT,
        "run_dir": str(RUN_DIR),
        "state": {
            "path": str(STATE_PATH),
            "size": len(state_payload),
            "sha256": _sha256(state_payload),
            "corrected": True,
            "published": publish,
        },
        "result": {
            "path": str(RESULT_PATH),
            "size": len(result_payload),
            "sha256": _sha256(result_payload),
            "formal_verdict": value["verdict"],
            "outcome_class": value["outcome_class"],
            "current_state": value["current_state"],
            "recovery_required": value["recovery_required"],
        },
        "created": publish and not result_present,
        "already_present": result_present,
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
    parser.add_argument(
        "--publish",
        action="store_true",
        help="apply the exact corrected state and publish the result",
    )
    args = parser.parse_args(argv)
    try:
        result = finalize(publish=args.publish)
    except (FinalizerError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
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
