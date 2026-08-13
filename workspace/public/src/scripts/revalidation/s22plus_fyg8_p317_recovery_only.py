#!/usr/bin/env python3
"""Resume only the exact P3.17 rollback after historical endpoint ambiguity.

The consumed P3.17 candidate is never transferable through this adapter.  The
adapter preserves the historical two-endpoint receipt, treats that one sealed
receipt as an epoch boundary only while replaying history, and still rejects a
fresh multi-endpoint snapshot.  Live use requires a separately reviewed,
byte-bound recovery-only approval.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any, Iterator, NoReturn


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402
import s22plus_odin_transition_core as odin_core  # noqa: E402


AUTHORITY_SCHEMA = "s22plus_fyg8_p317_recovery_only_authority_v1"
BINDING_SCHEMA = "s22plus_fyg8_p317_recovery_only_binding_v1"
ARM_SCHEMA = "s22plus_fyg8_p317_recovery_only_arm_v1"
APPROVAL_PREFIX = "DEVICE-ACTION-S22PLUS-P317-RECOVERY-ONLY-V1-APPROVE:"
TARGET = {
    "model": "SM-S906N",
    "device": "g0q",
    "firmware_incremental": "S906NKSS7FYG8",
    "topology": "usb:2-1.3",
}
DEFAULT_AUTHORITY = (
    ROOT
    / "workspace/public/src/device-action/recovery"
    / "s22plus_fyg8_p317_recovery_only_v1.json"
)
ARM_FILENAME = "p317-recovery-only-arm.json"
LOADED_AUTHORITY_IDENTITY = "_loaded_authority_identity"


class RecoveryOnlyError(RuntimeError):
    """The exact recovery-only boundary is not satisfied."""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_regular(path: Path, label: str, maximum: int = 16 * 1024 * 1024) -> bytes:
    try:
        direct = path.absolute()
        resolved = direct.resolve(strict=True)
        info = direct.lstat()
    except OSError as exc:
        raise RecoveryOnlyError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_size < 0
        or info.st_size > maximum
    ):
        raise RecoveryOnlyError(f"{label} is not a bounded regular file")
    try:
        with path.open("rb") as stream:
            payload = stream.read(maximum + 1)
    except OSError as exc:
        raise RecoveryOnlyError(f"{label} cannot be read") from exc
    if len(payload) != info.st_size or len(payload) > maximum:
        raise RecoveryOnlyError(f"{label} changed or exceeded its bound")
    return payload


def _file_identity(path: Path, label: str, maximum: int = 16 * 1024 * 1024) -> dict[str, Any]:
    payload = _read_regular(path, label, maximum)
    return {
        "path": str(path.relative_to(ROOT)),
        "size": len(payload),
        "sha256": _sha256_bytes(payload),
    }


def _load_json(path: Path, label: str, maximum: int = 16 * 1024 * 1024) -> dict[str, Any]:
    payload = _read_regular(path, label, maximum)
    try:
        value = json.loads(payload.decode("utf-8", "strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryOnlyError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryOnlyError(f"{label} is not a JSON object")
    return value


def _resolve_relative(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise RecoveryOnlyError(f"{label} path is not repository-relative")
    path = (ROOT / value).absolute()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise RecoveryOnlyError(f"{label} path escapes the repository") from exc
    return path


def _verify_identity(value: Any, label: str, maximum: int = 16 * 1024 * 1024) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise RecoveryOnlyError(f"{label} identity shape differs")
    path = _resolve_relative(value["path"], label)
    if _file_identity(path, label, maximum) != value:
        raise RecoveryOnlyError(f"{label} identity changed")
    return path


def load_authority(path: Path = DEFAULT_AUTHORITY) -> dict[str, Any]:
    payload = _read_regular(path, "P3.17 recovery authority", 256 * 1024)
    try:
        value = json.loads(payload.decode("utf-8", "strict"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RecoveryOnlyError("P3.17 recovery authority is not strict JSON") from exc
    if not isinstance(value, dict):
        raise RecoveryOnlyError("P3.17 recovery authority is not a JSON object")
    if set(value) != {
        "schema",
        "binding",
        "approval_binding_sha256",
        "approval_token",
    } or value.get("schema") != AUTHORITY_SCHEMA:
        raise RecoveryOnlyError("P3.17 recovery authority shape differs")
    binding = value.get("binding")
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise RecoveryOnlyError("P3.17 recovery binding shape differs")
    digest = live.core.json_sha256(binding)
    if (
        value.get("approval_binding_sha256") != digest
        or value.get("approval_token") != APPROVAL_PREFIX + digest
    ):
        raise RecoveryOnlyError("P3.17 recovery approval binding differs")
    if binding.get("target") != TARGET:
        raise RecoveryOnlyError("P3.17 recovery target differs")
    constraints = binding.get("constraints")
    if constraints != {
        "candidate_transfer_allowed": False,
        "rollback_transfer_maximum": 1,
        "fresh_multi_endpoint_allowed": False,
        "historical_receipt_preserved": True,
        "partition_payload": "boot-only-exact-rollback",
    }:
        raise RecoveryOnlyError("P3.17 recovery constraints differ")
    adapter = _verify_identity(binding.get("adapter"), "recovery adapter", 512 * 1024)
    if adapter.resolve(strict=True) != Path(__file__).resolve(strict=True):
        raise RecoveryOnlyError("P3.17 recovery adapter path differs")
    absolute = path.absolute()
    try:
        identity_path = str(absolute.relative_to(ROOT))
    except ValueError:
        identity_path = str(absolute)
    value[LOADED_AUTHORITY_IDENTITY] = {
        "path": identity_path,
        "size": len(payload),
        "sha256": _sha256_bytes(payload),
    }
    return value


def _binding_paths(authority: dict[str, Any]) -> dict[str, Path]:
    binding = authority["binding"]
    incident = binding.get("incident")
    immutable = binding.get("immutable_inputs")
    initial = binding.get("initial_mutable_inputs")
    if (
        not isinstance(incident, dict)
        or not isinstance(immutable, dict)
        or not isinstance(initial, dict)
        or set(immutable)
        != {
            "manifest",
            "prepared",
            "target_private",
            "candidate_start",
            "candidate_result",
            "historical_ambiguity_receipt",
            "rollback_ap",
            "live_adapter",
            "odin_transition_core",
        }
        or set(initial) != {"live_state", "journal_head", "endpoint_index"}
    ):
        raise RecoveryOnlyError("P3.17 recovery input inventory differs")
    paths: dict[str, Path] = {}
    for name, identity in immutable.items():
        maximum = 64 * 1024 * 1024 if name == "rollback_ap" else 16 * 1024 * 1024
        paths[name] = _verify_identity(identity, name.replace("_", " "), maximum)
    for name, identity in initial.items():
        path = _resolve_relative(identity.get("path") if isinstance(identity, dict) else None, name)
        paths[name] = path
    expected_run = _resolve_relative(incident.get("run_dir"), "incident run")
    if not expected_run.is_dir() or expected_run.is_symlink():
        raise RecoveryOnlyError("P3.17 incident run directory differs")
    paths["run_dir"] = expected_run
    if (
        incident.get("approval_binding_sha256")
        != "d5c2c24dbfdcb98482cef143a4a0f507ce010d4388f466a4b0893e799a954f2f"
        or incident.get("execution_closure_sha256")
        != "7fae669c5f5b60893bb39f34f491d813e50cc1acb52580a61f85f8716215a842"
        or incident.get("historical_ambiguity_sequence") != 17
        or incident.get("historical_ambiguity_identity_count") != 2
    ):
        raise RecoveryOnlyError("P3.17 incident identity differs")
    expected_receipt = expected_run / "odin-endpoints/receipts/odin-snapshot-000017.json"
    if paths["historical_ambiguity_receipt"] != expected_receipt:
        raise RecoveryOnlyError("P3.17 historical ambiguity path differs")
    return paths


def _initial_inputs_match(authority: dict[str, Any]) -> None:
    initial = authority["binding"]["initial_mutable_inputs"]
    for name, identity in initial.items():
        _verify_identity(identity, name.replace("_", " "), 16 * 1024 * 1024)


def _arm_path(run_dir: Path) -> Path:
    return run_dir / ARM_FILENAME


def _expected_arm(authority: dict[str, Any]) -> dict[str, Any]:
    loaded_identity = authority.get(LOADED_AUTHORITY_IDENTITY)
    if not isinstance(loaded_identity, dict):
        raise RecoveryOnlyError("loaded recovery authority identity is absent")
    return {
        "schema": ARM_SCHEMA,
        "approval_binding_sha256": authority["approval_binding_sha256"],
        "approval_token": authority["approval_token"],
        "authority": loaded_identity,
        "adapter": authority["binding"]["adapter"],
        "initial_mutable_inputs": authority["binding"]["initial_mutable_inputs"],
        "candidate_transfer_allowed": False,
        "rollback_transfer_maximum": 1,
        "device_actions": False,
    }


def _publish_arm_exclusive(path: Path, value: dict[str, Any]) -> bool:
    """Atomically publish a complete arm without replacing an existing arm."""

    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
    )
    linked = False
    try:
        live._write_exclusive(temporary, value)  # noqa: SLF001
        try:
            os.link(temporary, path, follow_symlinks=False)
        except FileExistsError:
            return False
        linked = True
        live.core._fsync_dir(path.parent)  # noqa: SLF001
        return True
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        else:
            live.core._fsync_dir(path.parent)  # noqa: SLF001
        if linked and not path.exists():
            raise RecoveryOnlyError("P3.17 recovery arm publication vanished")


def arm_recovery(authority: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    path = _arm_path(run_dir)
    expected = _expected_arm(authority)
    if (
        _file_identity(DEFAULT_AUTHORITY, "P3.17 recovery authority", 256 * 1024)
        != expected["authority"]
    ):
        raise RecoveryOnlyError("loaded recovery authority changed before arm")
    if path.exists() or path.is_symlink():
        value = _load_json(path, "P3.17 recovery arm", 256 * 1024)
        if value != expected:
            raise RecoveryOnlyError("P3.17 recovery arm changed")
        if (
            _file_identity(
                DEFAULT_AUTHORITY, "P3.17 recovery authority", 256 * 1024
            )
            != expected["authority"]
        ):
            raise RecoveryOnlyError("loaded recovery authority changed during arm")
        return value
    _initial_inputs_match(authority)
    try:
        published = _publish_arm_exclusive(path, expected)
    except (live.F1LiveError, OSError) as exc:
        raise RecoveryOnlyError("P3.17 recovery arm could not be published") from exc
    if not published:
        value = _load_json(path, "P3.17 recovery arm", 256 * 1024)
        if value != expected:
            raise RecoveryOnlyError("P3.17 recovery arm changed")
        if (
            _file_identity(
                DEFAULT_AUTHORITY, "P3.17 recovery authority", 256 * 1024
            )
            != expected["authority"]
        ):
            raise RecoveryOnlyError("loaded recovery authority changed during arm")
        return value
    if _load_json(path, "P3.17 recovery arm", 256 * 1024) != expected:
        raise RecoveryOnlyError("P3.17 recovery arm did not reopen exactly")
    if (
        _file_identity(DEFAULT_AUTHORITY, "P3.17 recovery authority", 256 * 1024)
        != expected["authority"]
    ):
        raise RecoveryOnlyError("loaded recovery authority changed during arm")
    return expected


class _ReplayTracker(odin_core.EndpointGenerationTracker):
    def historical_barrier(self) -> None:
        self._previous_live = ()  # noqa: SLF001


class HistoricalAmbiguityPatch:
    """Allow one exact ambiguous receipt only during historical replay."""

    def __init__(self, endpoint_dir: Path, sequence: int, receipt_sha256: str):
        self.endpoint_dir = endpoint_dir.absolute()
        self.sequence = sequence
        self.receipt_sha256 = receipt_sha256
        self.receipt_path = (
            self.endpoint_dir / "receipts" / f"odin-snapshot-{sequence:06d}.json"
        )
        self._original_resume = odin_core._resume_tracker  # noqa: SLF001
        self._original_validate = odin_core._validate_ticket_against_receipts  # noqa: SLF001

    def _barrier(self, record: dict[str, Any]) -> bool:
        identities = record.get("live_device_identities")
        if not isinstance(identities, list):
            raise odin_core.OdinTransitionError("historical endpoint identities are invalid")
        if len(identities) <= 1:
            return False
        if (
            record.get("sequence") != self.sequence
            or record.get("path") != str(self.receipt_path)
            or record.get("sha256") != self.receipt_sha256
            or len(identities) != 2
        ):
            raise odin_core.OdinTransitionError(
                "unapproved historical endpoint ambiguity"
            )
        return True

    def _replay(self, receipts: list[dict[str, Any]]) -> _ReplayTracker:
        tracker = _ReplayTracker()
        barriers = 0
        for record in receipts:
            identities = tuple(
                tuple(value) for value in record["live_device_identities"]
            )
            if self._barrier(record):
                barriers += 1
                tracker.historical_barrier()
            else:
                tracker.observe(identities)
        if len(receipts) > self.sequence and barriers != 1:
            raise odin_core.OdinTransitionError(
                "approved historical ambiguity receipt is absent"
            )
        return tracker

    def resume(
        self,
        run_dir: Path,
        sequence_start: int,
        *,
        lease: Any,
    ) -> tuple[_ReplayTracker, list[dict[str, Any]]]:
        if run_dir.absolute() != self.endpoint_dir:
            raise odin_core.OdinTransitionError("recovery endpoint directory differs")
        odin_core._require_active_lease(run_dir, lease)  # noqa: SLF001
        odin_core._reconcile_receipt_index_unlocked(run_dir)  # noqa: SLF001
        receipts = odin_core.list_snapshot_receipts(run_dir)
        phases = odin_core.list_phase_receipts(run_dir)
        if odin_core._audit_index_against_receipts(run_dir, receipts, phases):  # noqa: SLF001
            raise odin_core.OdinTransitionError(
                "transaction index still has an unindexed receipt"
            )
        sequences = [record["sequence"] for record in receipts]
        if sequences != list(range(len(sequences))):
            raise odin_core.OdinTransitionError(
                f"snapshot receipts are not contiguous from zero: {sequences}"
            )
        if sequence_start != len(receipts):
            raise odin_core.OdinTransitionError(
                f"snapshot sequence resume mismatch: expected {len(receipts)}, "
                f"received {sequence_start}"
            )
        return self._replay(receipts), receipts

    def validate_ticket(
        self,
        run_dir: Path,
        ticket: odin_core.EndpointTicket,
        receipts: list[dict[str, Any]],
    ) -> None:
        if run_dir.absolute() != self.endpoint_dir:
            raise odin_core.OdinTransitionError("recovery endpoint directory differs")
        if (
            ticket.generation <= 0
            or ticket.snapshot_sequence < 0
            or ticket.snapshot_sequence >= len(receipts)
        ):
            raise odin_core.OdinTransitionError(
                "Odin endpoint ticket metadata is invalid"
            )
        original = receipts[ticket.snapshot_sequence]
        expected_path = str(
            run_dir
            / "receipts"
            / f"odin-snapshot-{ticket.snapshot_sequence:06d}.json"
        )
        if (
            ticket.snapshot_receipt != expected_path
            or original["path"] != expected_path
            or ticket.snapshot_receipt_sha256 != original["sha256"]
            or original["live_device_identities"]
            != [[ticket.device, ticket.device_identity]]
        ):
            raise odin_core.OdinTransitionError(
                "Odin endpoint ticket receipt binding is invalid"
            )
        tracker = self._replay(receipts[: ticket.snapshot_sequence + 1])
        if tracker.generation != ticket.generation:
            raise odin_core.OdinTransitionError(
                "Odin endpoint ticket generation is invalid"
            )

    @contextlib.contextmanager
    def installed(self) -> Iterator[None]:
        odin_core._resume_tracker = self.resume  # type: ignore[assignment]  # noqa: SLF001
        odin_core._validate_ticket_against_receipts = self.validate_ticket  # type: ignore[assignment]  # noqa: SLF001
        try:
            yield
        finally:
            odin_core._resume_tracker = self._original_resume  # type: ignore[assignment]  # noqa: SLF001
            odin_core._validate_ticket_against_receipts = self._original_validate  # type: ignore[assignment]  # noqa: SLF001


class ExactRollbackBackend(live.SamsungOdinBackend):
    """Permit only the one exact rollback transfer owned by this incident."""

    def __init__(self, *args: Any, authority: dict[str, Any], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.authority = authority
        self.rollback_transfer_calls = 0

    def request_download(self, prepared: live.PreparedRun) -> NoReturn:
        raise RecoveryOnlyError("recovery-only adapter cannot request Download mode")

    def transfer(
        self,
        prepared: live.PreparedRun,
        endpoint: live.Endpoint,
        kind: str,
        destination: Path,
        attempt: int,
        prefix: str,
    ) -> live.TransferOutcome:
        if (
            kind != "rollback"
            or attempt != 1
            or prefix != "rollback-attempt-01"
            or self.rollback_transfer_calls != 0
        ):
            raise RecoveryOnlyError("recovery-only transfer is not the exact rollback")
        expected = self.authority["binding"]["immutable_inputs"]["rollback_ap"]
        actual = prepared.bundle.manifest.get("rollback_ap")
        if not isinstance(actual, dict) or {
            key: actual.get(key) for key in ("path", "size", "sha256")
        } != expected:
            raise RecoveryOnlyError("prepared rollback differs from recovery authority")
        self.rollback_transfer_calls += 1
        return super().transfer(
            prepared, endpoint, kind, destination, attempt, prefix
        )


class SingleRollbackAttemptPatch:
    """Reject candidate or second rollback starts before durable publication."""

    def __init__(self):
        self._original_begin = live._begin_transfer_attempt  # noqa: SLF001

    def begin(
        self,
        prepared: live.PreparedRun,
        journal: live.core.Journal,
        kind: str,
    ) -> tuple[int, str, dict[str, Any]]:
        if kind != "rollback":
            raise RecoveryOnlyError("recovery-only attempt kind differs")
        if list(prepared.run_dir.glob("rollback-attempt-*.start.json")):
            raise RecoveryOnlyError(
                "rollback attempt 1 is already consumed; retry is forbidden"
            )
        attempt, prefix, start = self._original_begin(prepared, journal, kind)
        if attempt != 1 or prefix != "rollback-attempt-01":
            raise RecoveryOnlyError("recovery-only attempt ordinal differs")
        return attempt, prefix, start

    @contextlib.contextmanager
    def installed(self) -> Iterator[None]:
        live._begin_transfer_attempt = self.begin  # type: ignore[assignment]  # noqa: SLF001
        try:
            yield
        finally:
            live._begin_transfer_attempt = self._original_begin  # type: ignore[assignment]  # noqa: SLF001


def _verify_attempt_files(run_dir: Path) -> None:
    candidate_starts = sorted(run_dir.glob("candidate-attempt-*.start.json"))
    candidate_results = sorted(run_dir.glob("candidate-attempt-*.result.json"))
    rollback_starts = sorted(run_dir.glob("rollback-attempt-*.start.json"))
    rollback_results = sorted(run_dir.glob("rollback-attempt-*.result.json"))
    if candidate_starts != [run_dir / "candidate-attempt-01.start.json"] or candidate_results != [
        run_dir / "candidate-attempt-01.result.json"
    ]:
        raise RecoveryOnlyError("candidate attempt count differs from exactly one")
    if rollback_starts not in ([], [run_dir / "rollback-attempt-01.start.json"]):
        raise RecoveryOnlyError("rollback start count exceeds one")
    if rollback_results not in ([], [run_dir / "rollback-attempt-01.result.json"]):
        raise RecoveryOnlyError("rollback result count exceeds one")
    if rollback_results and not rollback_starts:
        raise RecoveryOnlyError("rollback result lacks its durable start")


def _rollback_resume_disposition(
    prepared: live.PreparedRun,
    journal_state: str,
    current: dict[str, Any],
) -> str:
    """Classify whether exact attempt 1 is unspent or durably complete."""

    _verify_attempt_files(prepared.run_dir)
    start = prepared.run_dir / "rollback-attempt-01.start.json"
    result_path = prepared.run_dir / "rollback-attempt-01.result.json"
    if not start.exists():
        if result_path.exists():
            raise RecoveryOnlyError("rollback result lacks its durable start")
        if journal_state not in {"OBSERVED", "RECOVERY_DOWNLOAD"}:
            raise RecoveryOnlyError("advanced recovery state lacks rollback attempt 1")
        if (
            current.get("rollback_classification") is not None
            or current.get("rollback_completed") is not False
        ):
            raise RecoveryOnlyError("unspent rollback state differs")
        return "attempt-1-unspent"
    if journal_state == "OBSERVED":
        raise RecoveryOnlyError("rollback attempt precedes recovery Download state")
    result = live._validate_transfer_result(prepared, "rollback", 1)  # noqa: SLF001
    if result is None:
        raise RecoveryOnlyError(
            "rollback attempt 1 is consumed without a durable result; retry is forbidden"
        )
    if result.get("classification") != "odin_transfer_completed":
        raise RecoveryOnlyError(
            "rollback attempt 1 is consumed without durable completion; retry is forbidden"
        )
    durable_state = (
        current.get("rollback_classification"),
        current.get("rollback_completed"),
    )
    if durable_state not in {
        (None, False),
        ("odin_transfer_completed", True),
    }:
        raise RecoveryOnlyError("durable rollback state differs from attempt 1")
    if journal_state in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED", "CLOSED"} and durable_state != (
        "odin_transfer_completed",
        True,
    ):
        raise RecoveryOnlyError("advanced recovery state lacks durable rollback completion")
    return "attempt-1-durably-completed"


def verify_incident(authority: dict[str, Any]) -> tuple[live.PreparedRun, live.core.Journal]:
    paths = _binding_paths(authority)
    run_dir = paths["run_dir"]
    manifest = paths["manifest"]
    prepared = live.load_prepared(ROOT, manifest, run_dir)
    incident = authority["binding"]["incident"]
    if (
        prepared.binding_sha256 != incident["approval_binding_sha256"]
        or prepared.prepared["execution_closure"]["sha256"]
        != incident["execution_closure_sha256"]
        or prepared.private_target.get("topology") != TARGET["topology"]
    ):
        raise RecoveryOnlyError("prepared incident binding differs")
    _verify_attempt_files(run_dir)
    journal = live.core.Journal.reopen(
        run_dir / "transaction", prepared.binding_sha256
    )
    state = journal.state()
    if state not in {
        "OBSERVED",
        "RECOVERY_DOWNLOAD",
        "ROLLBACK_FLASHED",
        "HEALTH_VERIFIED",
        "CLOSED",
    }:
        raise RecoveryOnlyError("incident is not on the rollback-only state path")
    current = live._state(prepared)  # noqa: SLF001
    if current.get("candidate_completed") is not True:
        raise RecoveryOnlyError("consumed candidate completion is not durable")
    _rollback_resume_disposition(prepared, state, current)
    if state in {"OBSERVED", "RECOVERY_DOWNLOAD", "ROLLBACK_FLASHED"} and (
        current.get("final_verified") is not False
    ):
        raise RecoveryOnlyError("pre-health incident state differs")
    if state in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED", "CLOSED"}:
        result = live._validate_transfer_result(prepared, "rollback", 1)  # noqa: SLF001
        if (
            result is None
            or result.get("classification") != "odin_transfer_completed"
            or current.get("rollback_completed") is not True
        ):
            raise RecoveryOnlyError("durable rollback completion differs")
    if state in {"HEALTH_VERIFIED", "CLOSED"} and current.get("final_verified") is not True:
        raise RecoveryOnlyError("durable final health differs")
    return prepared, journal


def audit_historical_replay(
    authority: dict[str, Any], prepared: live.PreparedRun
) -> dict[str, Any]:
    """Exercise the repair against the immutable incident receipts in memory."""

    endpoint_dir = prepared.run_dir / "odin-endpoints"
    receipts = odin_core.list_snapshot_receipts(endpoint_dir)
    incident = authority["binding"]["incident"]
    if (
        len(receipts) != incident["historical_ambiguity_sequence"] + 1
        or receipts[-1]["sequence"] != incident["historical_ambiguity_sequence"]
        or len(receipts[-1]["live_device_identities"])
        != incident["historical_ambiguity_identity_count"]
    ):
        raise RecoveryOnlyError("historical endpoint receipt boundary differs")
    original = odin_core.EndpointGenerationTracker()
    original_failed = False
    try:
        for record in receipts:
            original.observe(
                tuple(tuple(value) for value in record["live_device_identities"])
            )
    except odin_core.OdinTransitionError as exc:
        original_failed = "ambiguous live Odin endpoints" in str(exc)
    if not original_failed:
        raise RecoveryOnlyError("historical endpoint failure was not reproduced")
    patch = HistoricalAmbiguityPatch(
        endpoint_dir,
        incident["historical_ambiguity_sequence"],
        authority["binding"]["immutable_inputs"]["historical_ambiguity_receipt"][
            "sha256"
        ],
    )
    repaired = patch._replay(receipts)
    generation_before_fixture = repaired.generation
    fixture_generation = repaired.observe(
        (("/dev/bus/usb/999/999", "host-only-fresh-single-fixture"),)
    )
    ambiguous_rejected = False
    try:
        repaired.observe(
            (
                ("/dev/bus/usb/999/998", "host-only-fresh-multi-a"),
                ("/dev/bus/usb/999/999", "host-only-fresh-multi-b"),
            )
        )
    except odin_core.OdinTransitionError as exc:
        ambiguous_rejected = "ambiguous live Odin endpoints" in str(exc)
    if (
        generation_before_fixture != 1
        or fixture_generation != 2
        or not ambiguous_rejected
    ):
        raise RecoveryOnlyError("historical endpoint repair fixture differs")
    return {
        "receipt_count": len(receipts),
        "historical_ambiguity_sequence": receipts[-1]["sequence"],
        "historical_ambiguity_sha256": receipts[-1]["sha256"],
        "original_failure_reproduced": True,
        "replayed_generation_before_fixture": generation_before_fixture,
        "fresh_single_fixture_generation": fixture_generation,
        "fresh_multi_fixture_rejected": True,
        "device_contact": False,
        "receipt_write": False,
    }


def render_plan(authority_path: Path = DEFAULT_AUTHORITY) -> dict[str, Any]:
    authority = load_authority(authority_path)
    prepared, journal = verify_incident(authority)
    if not _arm_path(prepared.run_dir).exists():
        _initial_inputs_match(authority)
    replay = audit_historical_replay(authority, prepared)
    return {
        "schema": "s22plus_fyg8_p317_recovery_only_plan_v1",
        "verdict": "PASS_P317_RECOVERY_ONLY_HOST_READY_REVIEW_REQUIRED",
        "approval_token": authority["approval_token"],
        "approval_binding_sha256": authority["approval_binding_sha256"],
        "incident_binding_sha256": prepared.binding_sha256,
        "journal_state": journal.state(),
        "candidate_transfer_allowed": False,
        "rollback_transfer_maximum": 1,
        "historical_ambiguity_sequence": 17,
        "historical_replay": replay,
        "fresh_multi_endpoint_allowed": False,
        "device_contact": False,
        "partition_transfer": False,
        "live_authorized": False,
        "independent_review_required": True,
    }


def recover(authority_path: Path, approval: str, adb: Path) -> dict[str, Any]:
    if authority_path.absolute() != DEFAULT_AUTHORITY.absolute():
        raise RecoveryOnlyError("live recovery requires the canonical authority path")
    authority = load_authority(authority_path)
    if approval != authority["approval_token"]:
        raise RecoveryOnlyError("fresh recovery-only approval differs")
    prepared, journal = verify_incident(authority)
    if journal.state() == "CLOSED":
        result = _load_json(prepared.run_dir / "live-result.json", "closed live result")
        live.validate_live_result(result, prepared)
        if result.get("recovery_required") is not False:
            raise RecoveryOnlyError("closed incident still requires recovery")
        return result
    arm_recovery(authority, prepared.run_dir)
    patch = HistoricalAmbiguityPatch(
        prepared.run_dir / "odin-endpoints",
        authority["binding"]["incident"]["historical_ambiguity_sequence"],
        authority["binding"]["immutable_inputs"]["historical_ambiguity_receipt"][
            "sha256"
        ],
    )
    backend = ExactRollbackBackend(ROOT, prepared.bundle, adb, authority=authority)
    attempt_patch = SingleRollbackAttemptPatch()
    with patch.installed(), attempt_patch.installed():
        result = live.recover_prepared(prepared, backend)
    _verify_attempt_files(prepared.run_dir)
    if backend.rollback_transfer_calls > 1:
        raise RecoveryOnlyError("rollback transfer call bound exceeded")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--recover", action="store_true")
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--approval")
    parser.add_argument("--adb", type=Path, default=Path("/usr/bin/adb"))
    args = parser.parse_args(argv)
    try:
        if args.validate:
            result = render_plan(args.authority)
        else:
            if not isinstance(args.approval, str):
                raise RecoveryOnlyError("--recover requires exact --approval")
            result = recover(args.authority, args.approval, args.adb)
    except (
        RecoveryOnlyError,
        live.F1LiveError,
        live.core.F1V2Error,
        odin_core.OdinTransitionError,
        OSError,
    ) as exc:
        print(f"P3.17 recovery-only error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
