#!/usr/bin/env python3
"""Close the exact P3.18 incident after both boot transfers completed once.

The ordinary Process-v2 run reached durable ROLLBACK_FLASHED, then rejected an
integrity-clean stage-101 progress record before publishing final health.  This
incident-specific adapter can only reuse the two existing rollback-observer
reads, obtain exact read-only Android health, and close the existing journal.
It has no Download request, Odin invocation, candidate transfer, or rollback
transfer path.  Live finalization requires one separately reviewed exact
approval bound to the immutable incident and this adapter's bytes.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import json
import os
import re
import stat
import sys
import time
from pathlib import Path
from typing import Any, Iterator, NoReturn


ROOT = Path(__file__).resolve().parents[5]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402


AUTHORITY_SCHEMA = "s22plus_fyg8_p318_postrollback_finalize_authority_v1"
BINDING_SCHEMA = "s22plus_fyg8_p318_postrollback_finalize_binding_v1"
ARM_SCHEMA = "s22plus_fyg8_p318_postrollback_finalize_arm_v1"
HEALTH_SCHEMA = "s22plus_fyg8_p318_postrollback_final_health_v1"
APPROVAL_PREFIX = (
    "DEVICE-ACTION-S22PLUS-P318-POSTROLLBACK-FINALIZE-V1-APPROVE:"
)
TARGET = {
    "model": "SM-S906N",
    "device": "g0q",
    "firmware_incremental": "S906NKSS7FYG8",
    "topology": "usb:2-1.3",
}
DEFAULT_AUTHORITY = (
    ROOT
    / "workspace/public/src/device-action/recovery"
    / "s22plus_fyg8_p318_postrollback_finalize_v1.json"
)
DEFAULT_MANIFEST = (
    ROOT
    / "workspace/public/src/device-action/manifests"
    / "s22plus_fyg8_p318_process_v2_ready_1.json"
)
DEFAULT_RUN_DIR = (
    ROOT
    / "workspace/private/runs/device-action-f1-live-v2"
    / "s22plus-fyg8-p318-live-1"
)
ARM_FILENAME = "p318-postrollback-finalize-arm.json"
HEALTH_FILENAME = "p318-postrollback-final-health.json"
DEFAULT_ADB = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "d1-baseline-rotation-v1/"
    "adb-05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
)
INITIAL_LIVE_SNAPSHOT = "p318-postrollback-initial-live-state.json"
INITIAL_HEAD_SNAPSHOT = "p318-postrollback-initial-journal-head.json"
LOADED_AUTHORITY_IDENTITY = "_loaded_authority_identity"
MAX_JSON = 16 * 1024 * 1024
EXPECTED_PROGRESS = {
    "profile": "E2",
    "generation": 46,
    "stage": 101,
    "outcome": 0,
    "detail": 0,
    "classification": "E2_PROGRESS_OBSERVED",
    "slot_status": ["valid", "bad-body"],
}


class FinalizeError(RuntimeError):
    """The exact post-rollback finalization boundary is not satisfied."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _stable_read(path: Path, label: str, maximum: int = MAX_JSON) -> bytes:
    try:
        direct = path.absolute()
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
    except OSError as exc:
        raise FinalizeError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_size < 0
        or before.st_size > maximum
    ):
        raise FinalizeError(f"{label} is not a bounded direct single-link file")
    try:
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise FinalizeError(f"{label} cannot be read") from exc
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
        raise FinalizeError(f"{label} changed while read")
    return payload


def _strict_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise FinalizeError(f"{label} is not strict unique-key JSON") from exc
    if not isinstance(value, dict):
        raise FinalizeError(f"{label} is not a JSON object")
    return value


def _load_json(path: Path, label: str, maximum: int = MAX_JSON) -> dict[str, Any]:
    return _strict_json_bytes(_stable_read(path, label, maximum), label)


def _relative(path: Path, label: str) -> str:
    try:
        direct = path.absolute()
        resolved = direct.resolve(strict=True)
        if direct != resolved:
            raise FinalizeError(f"{label} is not a direct canonical path")
        return resolved.relative_to(ROOT).as_posix()
    except (OSError, ValueError) as exc:
        raise FinalizeError(f"{label} escaped the repository") from exc


def _resolve(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise FinalizeError(f"{label} path is not repository-relative")
    direct = (ROOT / value).absolute()
    try:
        resolved = direct.resolve(strict=True)
        if direct != resolved:
            raise FinalizeError(f"{label} is not a direct canonical path")
        resolved.relative_to(ROOT)
    except (OSError, ValueError) as exc:
        raise FinalizeError(f"{label} path escaped the repository") from exc
    return resolved


def _identity(
    path: Path,
    label: str,
    maximum: int = MAX_JSON,
    *,
    allow_external: bool = False,
) -> dict[str, Any]:
    payload = _stable_read(path, label, maximum)
    resolved = path.resolve(strict=True)
    try:
        identity_path = resolved.relative_to(ROOT).as_posix()
    except ValueError:
        if not allow_external:
            raise FinalizeError(f"{label} escaped the repository")
        identity_path = str(resolved)
    return {
        "path": identity_path,
        "size": len(payload),
        "sha256": _sha256(payload),
    }


def _verify_identity(
    value: Any,
    label: str,
    maximum: int = MAX_JSON,
    *,
    allow_external: bool = False,
) -> Path:
    if not isinstance(value, dict) or set(value) != {"path", "size", "sha256"}:
        raise FinalizeError(f"{label} identity shape differs")
    if (
        type(value["size"]) is not int
        or value["size"] < 0
        or re.fullmatch(r"[0-9a-f]{64}", str(value["sha256"])) is None
    ):
        raise FinalizeError(f"{label} identity value differs")
    if allow_external:
        raw = value["path"]
        if not isinstance(raw, str) or not raw.startswith("/"):
            raise FinalizeError(f"{label} external path differs")
        path = Path(raw)
        try:
            if path.absolute() != path.resolve(strict=True):
                raise FinalizeError(f"{label} external path is not canonical")
        except OSError as exc:
            raise FinalizeError(f"{label} external path is unavailable") from exc
    else:
        path = _resolve(value["path"], label)
    if _identity(path, label, maximum, allow_external=allow_external) != value:
        raise FinalizeError(f"{label} identity changed")
    return path


def load_authority(path: Path = DEFAULT_AUTHORITY) -> dict[str, Any]:
    payload = _stable_read(path, "P3.18 finalizer authority", 512 * 1024)
    value = _strict_json_bytes(payload, "P3.18 finalizer authority")
    if set(value) != {
        "schema",
        "binding",
        "approval_binding_sha256",
        "approval_token",
    } or value.get("schema") != AUTHORITY_SCHEMA:
        raise FinalizeError("P3.18 finalizer authority shape differs")
    binding = value.get("binding")
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        raise FinalizeError("P3.18 finalizer binding shape differs")
    digest = live.core.json_sha256(binding)
    if (
        value.get("approval_binding_sha256") != digest
        or value.get("approval_token") != APPROVAL_PREFIX + digest
    ):
        raise FinalizeError("P3.18 finalizer approval binding differs")
    if set(binding) != {
        "schema",
        "adapter",
        "target",
        "incident",
        "constraints",
        "immutable_inputs",
        "initial_mutable_inputs",
    }:
        raise FinalizeError("P3.18 finalizer binding inventory differs")
    if binding.get("target") != TARGET:
        raise FinalizeError("P3.18 finalizer target differs")
    if binding.get("constraints") != {
        "candidate_transfer_allowed": False,
        "rollback_transfer_allowed": False,
        "download_request_allowed": False,
        "odin_invocation_allowed": False,
        "device_writes": False,
        "fresh_health_reads_only": True,
        "existing_observer_bytes_only": True,
    }:
        raise FinalizeError("P3.18 finalizer constraints differ")
    adapter = _verify_identity(binding.get("adapter"), "finalizer adapter", 1024 * 1024)
    if adapter.resolve(strict=True) != Path(__file__).resolve(strict=True):
        raise FinalizeError("P3.18 finalizer adapter path differs")
    value[LOADED_AUTHORITY_IDENTITY] = {
        "path": _relative(path, "P3.18 finalizer authority"),
        "size": len(payload),
        "sha256": _sha256(payload),
    }
    return value


def _canonical_incident_paths() -> dict[str, Path]:
    run = DEFAULT_RUN_DIR
    scripts = REVALIDATION
    return {
        "manifest": DEFAULT_MANIFEST,
        "prepared": run / "prepared.json",
        "target_private": run / "target-private.json",
        "candidate_start": run / "candidate-attempt-01.start.json",
        "candidate_result": run / "candidate-attempt-01.result.json",
        "rollback_start": run / "rollback-attempt-01.start.json",
        "rollback_result": run / "rollback-attempt-01.result.json",
        "observer_one": run / "rollback-observer-1.bin",
        "observer_one_stderr": run / "rollback-observer-1.bin.stderr",
        "observer_two": run / "rollback-observer-2.bin",
        "observer_two_stderr": run / "rollback-observer-2.bin.stderr",
        "candidate_topology_raw": run / "p318-topology-candidate-end.raw.json",
        "candidate_topology_record": run / "p318-topology-candidate-end.record.json",
        "initial_live_state_snapshot": run / INITIAL_LIVE_SNAPSHOT,
        "initial_journal_head_snapshot": run / INITIAL_HEAD_SNAPSHOT,
        "live_adapter": scripts / "device_action_f1_live_v2.py",
        "f1_core": scripts / "device_action_f1_v2.py",
        "d0_adapter": scripts / "device_action_d0_v2.py",
        "typed_evidence": scripts / "device_action_f1_evidence_v2.py",
        "telemetry_decoder": scripts / "s22plus_fyg8_p318_max77705_telemetry_decoder.py",
        "topology_receipt": scripts / "s22plus_fyg8_p318_topology_receipt.py",
        "topology_transition": scripts / "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py",
        "adb": DEFAULT_ADB,
    }


def build_authority() -> dict[str, Any]:
    """Derive the immutable authority from the one exact parked incident."""

    paths = _canonical_incident_paths()
    prepared = live.load_prepared(ROOT, paths["manifest"], DEFAULT_RUN_DIR)
    journal = live.core.Journal.reopen(
        prepared.run_dir / "transaction", prepared.binding_sha256
    )
    if journal.state() not in {"ROLLBACK_FLASHED", "HEALTH_VERIFIED", "CLOSED"}:
        raise FinalizeError("P3.18 incident is not at a resumable rollback barrier")
    private = prepared.private_target
    if private.get("topology") != TARGET["topology"]:
        raise FinalizeError("P3.18 incident topology differs")
    candidate = live._validate_transfer_evidence(prepared, "candidate")  # noqa: SLF001
    rollback = live._validate_transfer_evidence(prepared, "rollback")  # noqa: SLF001
    if (
        candidate.get("classification") != "odin_transfer_completed"
        or rollback.get("classification") != "odin_transfer_completed"
    ):
        raise FinalizeError("P3.18 incident transfer barrier differs")
    payloads = [
        _stable_read(paths[name], name.replace("_", " "), 4 * 1024 * 1024)
        for name in ("observer_one", "observer_two")
    ]
    if not payloads[0] or payloads[0] != payloads[1]:
        raise FinalizeError("P3.18 incident observer barrier differs")
    _exact_progress(
        live.classify_acceptance(
            payloads[0], prepared.bundle.manifest["observation"]["acceptance"]
        )
    )
    immutable: dict[str, Any] = {}
    for name, path in paths.items():
        maximum = 4 * 1024 * 1024 if name.startswith("observer_") else MAX_JSON
        immutable[name] = _identity(
            path,
            name.replace("_", " "),
            maximum,
            allow_external=False,
        )
    journal_paths = sorted((prepared.run_dir / "transaction/journal").glob("*.json"))
    if len(journal_paths) < 15:
        raise FinalizeError("P3.18 incident journal inventory differs")
    initial_live_payload = _stable_read(
        paths["initial_live_state_snapshot"], "initial live-state snapshot"
    )
    initial_head_payload = _stable_read(
        paths["initial_journal_head_snapshot"], "initial journal-head snapshot"
    )
    if journal.state() == "ROLLBACK_FLASHED" and (
        _stable_read(prepared.run_dir / "live-state.json", "live state")
        != initial_live_payload
        or _stable_read(
            prepared.run_dir / "transaction/journal-head.json", "journal head"
        )
        != initial_head_payload
    ):
        raise FinalizeError("P3.18 mutable barrier differs from its snapshot")
    def initial_identity(path: Path, payload: bytes, label: str) -> dict[str, Any]:
        return {
            "path": _relative(path, label),
            "size": len(payload),
            "sha256": _sha256(payload),
        }
    initial = {
        "live_state": initial_identity(
            prepared.run_dir / "live-state.json",
            initial_live_payload,
            "live state",
        ),
        "journal_head": initial_identity(
            prepared.run_dir / "transaction/journal-head.json",
            initial_head_payload,
            "journal head",
        ),
        "journal_records": [
            _identity(path, f"journal record {index}")
            for index, path in enumerate(journal_paths[:15])
        ],
    }
    binding = {
        "schema": BINDING_SCHEMA,
        "adapter": _identity(Path(__file__), "finalizer adapter", 1024 * 1024),
        "target": TARGET,
        "incident": {
            "run_dir": _relative(prepared.run_dir, "incident run"),
            "approval_binding_sha256": prepared.binding_sha256,
            "execution_closure_sha256": prepared.prepared["execution_closure"]["sha256"],
            "journal_state": "ROLLBACK_FLASHED",
            "candidate_transfers": 1,
            "rollback_transfers": 1,
            "progress_record": EXPECTED_PROGRESS,
        },
        "constraints": {
            "candidate_transfer_allowed": False,
            "rollback_transfer_allowed": False,
            "download_request_allowed": False,
            "odin_invocation_allowed": False,
            "device_writes": False,
            "fresh_health_reads_only": True,
            "existing_observer_bytes_only": True,
        },
        "immutable_inputs": immutable,
        "initial_mutable_inputs": initial,
    }
    digest = live.core.json_sha256(binding)
    return {
        "schema": AUTHORITY_SCHEMA,
        "binding": binding,
        "approval_binding_sha256": digest,
        "approval_token": APPROVAL_PREFIX + digest,
    }


def encode_authority(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _paths(authority: dict[str, Any]) -> dict[str, Path]:
    binding = authority["binding"]
    incident = binding["incident"]
    immutable = binding["immutable_inputs"]
    initial = binding["initial_mutable_inputs"]
    if (
        not isinstance(incident, dict)
        or not isinstance(immutable, dict)
        or not isinstance(initial, dict)
    ):
        raise FinalizeError("P3.18 finalizer input groups differ")
    expected_immutable = {
        "manifest",
        "prepared",
        "target_private",
        "candidate_start",
        "candidate_result",
        "rollback_start",
        "rollback_result",
        "observer_one",
        "observer_one_stderr",
        "observer_two",
        "observer_two_stderr",
        "candidate_topology_raw",
        "candidate_topology_record",
        "initial_live_state_snapshot",
        "initial_journal_head_snapshot",
        "live_adapter",
        "f1_core",
        "d0_adapter",
        "typed_evidence",
        "telemetry_decoder",
        "topology_receipt",
        "topology_transition",
        "adb",
    }
    if set(immutable) != expected_immutable or set(initial) != {
        "live_state",
        "journal_head",
        "journal_records",
    }:
        raise FinalizeError("P3.18 finalizer exact input inventory differs")
    paths: dict[str, Path] = {}
    for name, identity in immutable.items():
        maximum = 4 * 1024 * 1024 if name.startswith("observer_") else MAX_JSON
        paths[name] = _verify_identity(
            identity,
            name.replace("_", " "),
            maximum,
            allow_external=False,
        )
    records = initial["journal_records"]
    if not isinstance(records, list) or len(records) != 15:
        raise FinalizeError("P3.18 initial journal record inventory differs")
    for index, identity in enumerate(records):
        paths[f"journal_record_{index}"] = _resolve(
            identity.get("path") if isinstance(identity, dict) else None,
            f"journal record {index}",
        )
    for name in ("live_state", "journal_head"):
        identity = initial[name]
        paths[name] = _resolve(
            identity.get("path") if isinstance(identity, dict) else None,
            name.replace("_", " "),
        )
    run_dir = _resolve(incident.get("run_dir"), "incident run")
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise FinalizeError("P3.18 incident run directory differs")
    paths["run_dir"] = run_dir
    if (
        incident.get("approval_binding_sha256")
        != "fd68d3b4713d13afceaabdc5f97240f76808a5be2d09fc59b8853bcfd6e39136"
        or incident.get("execution_closure_sha256")
        != "fb4805c6828599d4d263a0c2ba77b9d9c8e3eb6593bd76dffd96f9370d9d27d4"
        or incident.get("journal_state") != "ROLLBACK_FLASHED"
        or incident.get("candidate_transfers") != 1
        or incident.get("rollback_transfers") != 1
        or incident.get("progress_record") != EXPECTED_PROGRESS
    ):
        raise FinalizeError("P3.18 incident identity differs")
    return paths


def _initial_inputs_match(authority: dict[str, Any]) -> None:
    initial = authority["binding"]["initial_mutable_inputs"]
    _verify_identity(initial["live_state"], "initial live state")
    _verify_identity(initial["journal_head"], "initial journal head")
    for index, identity in enumerate(initial["journal_records"]):
        _verify_identity(identity, f"initial journal record {index}")


def _initial_journal_prefix_match(authority: dict[str, Any]) -> None:
    initial = authority["binding"]["initial_mutable_inputs"]
    for index, identity in enumerate(initial["journal_records"]):
        _verify_identity(identity, f"initial journal record {index}")


def _validate_resumable_state(
    authority: dict[str, Any],
    prepared: live.PreparedRun,
    journal: live.core.Journal,
) -> None:
    """Accept only the initial barrier or exact host-reporting cuts after it."""

    state_name = journal.state()
    records = journal.records()
    live_state = live._state(prepared)  # noqa: SLF001
    _initial_journal_prefix_match(authority)
    if state_name == "ROLLBACK_FLASHED":
        if len(records) != 15:
            raise FinalizeError("P3.18 rollback barrier record count differs")
        if live_state.get("final_verified") is not True:
            _verify_identity(
                authority["binding"]["initial_mutable_inputs"]["live_state"],
                "initial live state",
            )
            _verify_identity(
                authority["binding"]["initial_mutable_inputs"]["journal_head"],
                "initial journal head",
            )
            return
    elif state_name == "HEALTH_VERIFIED":
        if len(records) not in {16, 17, 18}:
            raise FinalizeError("P3.18 health cut record count differs")
    elif state_name == "CLOSED":
        if len(records) != 19:
            raise FinalizeError("P3.18 closed record count differs")
    else:
        raise FinalizeError("P3.18 incident is not post-rollback")
    if live_state.get("final_verified") is not True:
        raise FinalizeError("P3.18 post-health state lacks final verification")
    health_path = prepared.run_dir / HEALTH_FILENAME
    health_value = _validate_health_value(
        authority,
        prepared,
        _load_published_json(health_path, "P3.18 final health", 512 * 1024),
    )
    evidence = live_state.get("final_evidence")
    if (
        not isinstance(evidence, dict)
        or evidence.get("health") != health_value["health"]
        or evidence.get("target_evidence_sha256")
        != health_value["target_evidence_sha256"]
    ):
        raise FinalizeError("P3.18 final health evidence differs")
    live._validate_final_observer(prepared, live_state)  # noqa: SLF001


def _exact_progress(classified: dict[str, Any]) -> dict[str, Any]:
    records = classified.get("records")
    if (
        classified.get("accepted") is not False
        or classified.get("classification") != EXPECTED_PROGRESS["classification"]
        or classified.get("exact_count") != 0
        or classified.get("family_count") != 1
        or classified.get("integrity_issue") is not False
        or not isinstance(records, list)
        or len(records) != 1
    ):
        raise FinalizeError("P3.18 incident classification differs")
    row = records[0]
    active = row.get("active") if isinstance(row, dict) else None
    if (
        not isinstance(active, dict)
        or row.get("profile") != EXPECTED_PROGRESS["profile"]
        or row.get("fallback_used") is not True
        or row.get("header_crc_valid") is not True
        or row.get("terminal_success") is not False
        or row.get("slot_status") != EXPECTED_PROGRESS["slot_status"]
        or row.get("max77705") is not None
        or active.get("generation") != EXPECTED_PROGRESS["generation"]
        or active.get("stage") != EXPECTED_PROGRESS["stage"]
        or active.get("outcome") != EXPECTED_PROGRESS["outcome"]
        or active.get("detail") != EXPECTED_PROGRESS["detail"]
    ):
        raise FinalizeError("P3.18 stage-101 progress evidence differs")
    return row


class ProgressCorrelationPatch:
    """Normalize only the immutable stage-101/no-terminal incident."""

    def __init__(self) -> None:
        self.original = live.typed_evidence.correlate_p318_candidate_topology

    def correlate(
        self, classified: dict[str, Any], phase_record: dict[str, Any]
    ) -> dict[str, Any]:
        _exact_progress(classified)
        decision = phase_record.get("decision")
        if (
            phase_record.get("phase") != "candidate_end"
            or phase_record.get("authority_state") != "candidate_approved_exact"
            or phase_record.get("causal_terminal_ready") is not False
            or phase_record.get("observation_window_complete") is not True
            or phase_record.get("snapshot_capture_complete") is not True
            or not isinstance(decision, dict)
            or decision.get("proof_class") != "NO_PROOF_OBSERVER"
            or decision.get("effect") != "NO_PROOF_OBSERVER_and_park"
            or decision.get("relationship") != "absent"
            or decision.get("experiment_proof_reclassified_by_rollback") is not False
        ):
            raise FinalizeError("P3.18 candidate topology decision differs")
        result = copy.deepcopy(classified)
        result["host_correlation_proof_class"] = "NO_PROOF_OBSERVER"
        result["causal_result_allowed"] = False
        result["p318_incomplete_terminal"] = {
            "generation": EXPECTED_PROGRESS["generation"],
            "stage": EXPECTED_PROGRESS["stage"],
            "slot_status": EXPECTED_PROGRESS["slot_status"],
            "terminal_record_present": False,
            "observer_bytes_stable": True,
        }
        return result

    @contextlib.contextmanager
    def installed(self) -> Iterator[None]:
        if live.typed_evidence.correlate_p318_candidate_topology is not self.original:
            raise FinalizeError("P3.18 correlation seam already changed")
        live.typed_evidence.correlate_p318_candidate_topology = self.correlate
        try:
            yield
        finally:
            live.typed_evidence.correlate_p318_candidate_topology = self.original


def _verify_observers(
    authority: dict[str, Any], prepared: live.PreparedRun
) -> tuple[bytes, list[dict[str, Any]]]:
    paths = _paths(authority)
    payloads: list[bytes] = []
    receipts: list[dict[str, Any]] = []
    source = prepared.bundle.manifest["observation"]["acceptance"]["source"]
    for index, key in enumerate(("observer_one", "observer_two"), 1):
        path = paths[key]
        payload = _stable_read(path, f"rollback observer {index}", 4 * 1024 * 1024)
        stderr = _stable_read(
            paths[f"observer_{'one' if index == 1 else 'two'}_stderr"],
            f"rollback observer {index} stderr",
            64 * 1024,
        )
        if stderr:
            raise FinalizeError("P3.18 rollback observer stderr is not empty")
        payloads.append(payload)
        receipts.append(
            {
                "path": str(path),
                "bytes": len(payload),
                "sha256": _sha256(payload),
                "read_to_eof": True,
                "stderr_bytes": 0,
                "source": source,
                "elapsed_sec": 0.0,
            }
        )
    if not payloads[0] or payloads[0] != payloads[1]:
        raise FinalizeError("P3.18 rollback observer bytes are not identical")
    classified = live.classify_acceptance(
        payloads[0], prepared.bundle.manifest["observation"]["acceptance"]
    )
    _exact_progress(classified)
    return payloads[0], receipts


def verify_incident(
    authority: dict[str, Any]
) -> tuple[live.PreparedRun, live.core.Journal, dict[str, Any]]:
    paths = _paths(authority)
    prepared = live.load_prepared(ROOT, paths["manifest"], paths["run_dir"])
    incident = authority["binding"]["incident"]
    if (
        prepared.binding_sha256 != incident["approval_binding_sha256"]
        or prepared.prepared["execution_closure"]["sha256"]
        != incident["execution_closure_sha256"]
    ):
        raise FinalizeError("P3.18 prepared incident binding differs")
    journal = live.core.Journal.reopen(
        prepared.run_dir / "transaction", prepared.binding_sha256
    )
    _validate_resumable_state(authority, prepared, journal)
    candidate = live._validate_transfer_evidence(prepared, "candidate")  # noqa: SLF001
    rollback = live._validate_transfer_evidence(prepared, "rollback")  # noqa: SLF001
    if (
        candidate.get("classification") != "odin_transfer_completed"
        or rollback.get("classification") != "odin_transfer_completed"
        or (prepared.run_dir / "candidate-attempt-02.start.json").exists()
        or (prepared.run_dir / "rollback-attempt-02.start.json").exists()
    ):
        raise FinalizeError("P3.18 one-shot transfer evidence differs")
    state = live._state(prepared)  # noqa: SLF001
    if (
        state.get("candidate_completed") is not True
        or state.get("rollback_completed") is not True
        or state.get("candidate_observer_accepted") is not False
        or state.get("candidate_observer_classification") != "endpoint-timeout"
    ):
        raise FinalizeError("P3.18 durable live state differs")
    payload, _receipts = _verify_observers(authority, prepared)
    classified = live.classify_acceptance(
        payload, prepared.bundle.manifest["observation"]["acceptance"]
    )
    patch = ProgressCorrelationPatch()
    with patch.installed():
        correlated, evidence = live._p318_finalize_candidate_phase(  # noqa: SLF001
            prepared, classified
        )
    if (
        correlated.get("host_correlation_proof_class") != "NO_PROOF_OBSERVER"
        or correlated.get("causal_result_allowed") is not False
        or correlated.get("accepted") is not False
    ):
        raise FinalizeError("P3.18 normalized incident result differs")
    return prepared, journal, evidence


def _expected_arm(authority: dict[str, Any]) -> dict[str, Any]:
    identity = authority.get(LOADED_AUTHORITY_IDENTITY)
    if not isinstance(identity, dict):
        raise FinalizeError("loaded P3.18 finalizer authority identity is absent")
    return {
        "schema": ARM_SCHEMA,
        "approval_binding_sha256": authority["approval_binding_sha256"],
        "approval_token": authority["approval_token"],
        "authority": identity,
        "adapter": authority["binding"]["adapter"],
        "initial_mutable_inputs": authority["binding"]["initial_mutable_inputs"],
        "candidate_transfer_allowed": False,
        "rollback_transfer_allowed": False,
        "device_writes": False,
        "fresh_health_reads_only": True,
    }


def _write_bytes_exclusive(
    path: Path, payload: bytes, mode: int, label: str
) -> None:
    if len(payload) > MAX_JSON:
        raise FinalizeError(f"{label} exceeds its bound")
    if mode not in {0o400, 0o500}:
        raise FinalizeError(f"{label} mode is not allowed")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            mode,
        )
    except OSError as exc:
        raise FinalizeError(f"{label} cannot be created exclusively") from exc
    try:
        os.fchmod(descriptor, mode)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or stat.S_IMODE(opened.st_mode) != mode
            or opened.st_nlink != 1
            or opened.st_size != 0
        ):
            raise FinalizeError(f"{label} new receipt identity differs")
        view = memoryview(payload)
        offset = 0
        while offset < len(view):
            try:
                written = os.write(descriptor, view[offset:])
            except InterruptedError:
                continue
            if written <= 0:
                raise FinalizeError(f"{label} receipt write made no progress")
            offset += written
        complete = os.fstat(descriptor)
        if (
            complete.st_dev != opened.st_dev
            or complete.st_ino != opened.st_ino
            or complete.st_nlink != 1
            or stat.S_IMODE(complete.st_mode) != mode
            or complete.st_size != len(payload)
        ):
            raise FinalizeError(f"{label} completed receipt identity differs")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    live.core._fsync_dir(path.parent)  # noqa: SLF001


def _write_mode0400_exclusive(
    path: Path, value: dict[str, Any], label: str
) -> None:
    payload = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode() + b"\n"
    _write_bytes_exclusive(path, payload, 0o400, label)


def _publish_exclusive(path: Path, value: dict[str, Any], label: str) -> bool:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    linked = False
    try:
        _write_mode0400_exclusive(temporary, value, f"{label} temporary receipt")
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
            raise FinalizeError(f"{label} publication vanished")


def _repair_link_publication_cut(path: Path, label: str) -> None:
    """Collapse only the exact final+temp hardlink cut left by this publisher."""

    try:
        final = path.lstat()
    except OSError as exc:
        raise FinalizeError(f"{label} publication is unavailable") from exc
    if not stat.S_ISREG(final.st_mode) or stat.S_ISLNK(final.st_mode):
        raise FinalizeError(f"{label} publication is not a regular file")
    if final.st_nlink == 1:
        return
    if final.st_nlink != 2:
        raise FinalizeError(f"{label} publication link count differs")
    pattern = re.compile(
        rf"^\.{re.escape(path.name)}\.[1-9][0-9]*\.[1-9][0-9]*\.tmp$"
    )
    try:
        candidates = [
            child
            for child in path.parent.iterdir()
            if pattern.fullmatch(child.name) is not None
        ]
    except OSError as exc:
        raise FinalizeError(f"{label} publication directory is unavailable") from exc
    if len(candidates) != 1:
        raise FinalizeError(f"{label} publication cut is ambiguous")
    temporary = candidates[0]
    try:
        temp = temporary.lstat()
    except OSError as exc:
        raise FinalizeError(f"{label} publication temp is unavailable") from exc
    if (
        stat.S_ISLNK(temp.st_mode)
        or not stat.S_ISREG(temp.st_mode)
        or temp.st_dev != final.st_dev
        or temp.st_ino != final.st_ino
        or temp.st_nlink != 2
        or temp.st_size != final.st_size
    ):
        raise FinalizeError(f"{label} publication cut identity differs")
    try:
        temporary.unlink()
        live.core._fsync_dir(path.parent)  # noqa: SLF001
        repaired = path.lstat()
    except OSError as exc:
        raise FinalizeError(f"{label} publication cut cannot be repaired") from exc
    if (
        not stat.S_ISREG(repaired.st_mode)
        or stat.S_ISLNK(repaired.st_mode)
        or repaired.st_dev != final.st_dev
        or repaired.st_ino != final.st_ino
        or repaired.st_nlink != 1
        or repaired.st_size != final.st_size
    ):
        raise FinalizeError(f"{label} publication repair differs")


def _verify_adb_execution_input(
    path: Path, expected: dict[str, Any], label: str
) -> Path:
    payload = _stable_read(path, label, MAX_JSON)
    metadata = path.lstat()
    if (
        stat.S_IMODE(metadata.st_mode) != 0o500
        or metadata.st_nlink != 1
        or not isinstance(expected, dict)
        or expected.get("size") != len(payload)
        or expected.get("sha256") != _sha256(payload)
    ):
        raise FinalizeError(f"{label} identity differs")
    return path


def _load_published_json(
    path: Path, label: str, maximum: int = MAX_JSON
) -> dict[str, Any]:
    _repair_link_publication_cut(path, label)
    return _load_json(path, label, maximum)


def arm_finalizer(authority: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    path = run_dir / ARM_FILENAME
    expected = _expected_arm(authority)
    current_authority = _identity(
        DEFAULT_AUTHORITY, "P3.18 finalizer authority", 512 * 1024
    )
    if current_authority != expected["authority"]:
        raise FinalizeError("loaded P3.18 finalizer authority changed before arm")
    if path.exists() or path.is_symlink():
        value = _load_published_json(
            path, "P3.18 finalizer arm", 512 * 1024
        )
        if value != expected:
            raise FinalizeError("P3.18 finalizer arm changed")
        return value
    health_path = run_dir / HEALTH_FILENAME
    if health_path.exists() or health_path.is_symlink():
        raise FinalizeError("post-health P3.18 finalizer arm is absent")
    _initial_inputs_match(authority)
    try:
        published = _publish_exclusive(path, expected, "P3.18 finalizer arm")
    except (FinalizeError, live.F1LiveError, OSError) as exc:
        raise FinalizeError("P3.18 finalizer arm could not be published") from exc
    if not published:
        value = _load_published_json(
            path, "P3.18 finalizer arm", 512 * 1024
        )
        if value != expected:
            raise FinalizeError("P3.18 finalizer arm changed")
        return value
    if _load_published_json(
        path, "P3.18 finalizer arm", 512 * 1024
    ) != expected:
        raise FinalizeError("P3.18 finalizer arm did not reopen exactly")
    if _identity(DEFAULT_AUTHORITY, "P3.18 finalizer authority", 512 * 1024) != expected[
        "authority"
    ]:
        raise FinalizeError("loaded P3.18 finalizer authority changed during arm")
    return expected


def verify_existing_arm(authority: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    path = run_dir / ARM_FILENAME
    if not path.exists() and not path.is_symlink():
        raise FinalizeError("closed P3.18 finalizer arm is absent")
    expected = _expected_arm(authority)
    value = _load_published_json(path, "closed P3.18 finalizer arm", 512 * 1024)
    if value != expected:
        raise FinalizeError("closed P3.18 finalizer arm changed")
    return value


def _health_value(
    authority: dict[str, Any], prepared: live.PreparedRun, health: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": HEALTH_SCHEMA,
        "approval_binding_sha256": authority["approval_binding_sha256"],
        "incident_binding_sha256": prepared.binding_sha256,
        "target_evidence_sha256": live.core.json_sha256(
            {
                "serial": hashlib.sha256(
                    prepared.private_target["serial"].encode()
                ).hexdigest(),
                "topology": hashlib.sha256(
                    prepared.private_target["topology"].encode()
                ).hexdigest(),
            }
        ),
        "health": health,
        "device_contact": True,
        "device_writes": False,
        "download_request": False,
        "odin_invoked": False,
        "candidate_transfer": False,
        "rollback_transfer": False,
    }


def _validate_health_value(
    authority: dict[str, Any], prepared: live.PreparedRun, value: dict[str, Any]
) -> dict[str, Any]:
    if set(value) != {
        "schema",
        "approval_binding_sha256",
        "incident_binding_sha256",
        "target_evidence_sha256",
        "health",
        "device_contact",
        "device_writes",
        "download_request",
        "odin_invoked",
        "candidate_transfer",
        "rollback_transfer",
    } or (
        value.get("schema") != HEALTH_SCHEMA
        or value.get("approval_binding_sha256") != authority["approval_binding_sha256"]
        or value.get("incident_binding_sha256") != prepared.binding_sha256
        or value.get("device_contact") is not True
        or any(
            value.get(key) is not False
            for key in (
                "device_writes",
                "download_request",
                "odin_invoked",
                "candidate_transfer",
                "rollback_transfer",
            )
        )
    ):
        raise FinalizeError("P3.18 final health receipt shape differs")
    expected_target = _health_value(authority, prepared, value.get("health"))[  # type: ignore[arg-type]
        "target_evidence_sha256"
    ]
    if value.get("target_evidence_sha256") != expected_target:
        raise FinalizeError("P3.18 final health target differs")
    expected = prepared.bundle.profile["final_health"]
    health = value.get("health")
    if (
        not isinstance(health, dict)
        or set(health)
        != {
            "android_boot_completed",
            "boot_animation_stopped",
            "verified_boot_state",
            "root_verified",
            "boot_sha256",
            "supporting_partition_sha256",
            "odin_endpoint_absent",
            "kernel_release",
            "boot_id_sha256",
        }
        or health.get("android_boot_completed") is not True
        or health.get("boot_animation_stopped") is not True
        or health.get("verified_boot_state") != expected["verified_boot_state"]
        or health.get("root_verified") is not True
        or health.get("boot_sha256") != expected["boot_sha256"]
        or health.get("supporting_partition_sha256")
        != expected["supporting_partition_sha256"]
        or health.get("odin_endpoint_absent") is not True
        or not isinstance(health.get("kernel_release"), str)
        or not health["kernel_release"]
        or not isinstance(health.get("boot_id_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", health["boot_id_sha256"]) is None
    ):
        raise FinalizeError("P3.18 final health semantics differ")
    return value


class FinalHealthOnlyBackend:
    def __init__(
        self,
        authority: dict[str, Any],
        prepared: live.PreparedRun,
        adb: Path,
    ) -> None:
        self.authority = authority
        self.prepared = prepared
        self.delegate = live.SamsungOdinBackend(ROOT, prepared.bundle, adb)

    def endpoint_session(self, _run_dir: Path) -> contextlib.AbstractContextManager[Any]:
        return contextlib.nullcontext(None)

    def wait_download(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        raise FinalizeError("P3.18 finalizer cannot wait for Download")

    def transfer(self, *_args: Any, **_kwargs: Any) -> NoReturn:
        raise FinalizeError("P3.18 finalizer cannot transfer a partition")

    def verify_final(
        self,
        prepared: live.PreparedRun,
        _run_dir: Path,
        _lease: Any,
        _destination: Path,
    ) -> dict[str, Any]:
        if prepared.binding_sha256 != self.prepared.binding_sha256:
            raise FinalizeError("P3.18 finalizer prepared binding changed")
        health_path = prepared.run_dir / HEALTH_FILENAME
        if health_path.exists() or health_path.is_symlink():
            value = _validate_health_value(
                self.authority,
                prepared,
                _load_published_json(
                    health_path, "P3.18 final health", 512 * 1024
                ),
            )
        else:
            serial, health = self.delegate._wait_final_health(prepared)  # noqa: SLF001
            if serial != prepared.private_target["serial"]:
                raise FinalizeError("P3.18 final health serial differs")
            expected = _health_value(self.authority, prepared, health)
            try:
                published = _publish_exclusive(
                    health_path, expected, "P3.18 final health"
                )
            except (FinalizeError, live.F1LiveError, OSError) as exc:
                raise FinalizeError("P3.18 final health could not be published") from exc
            value = _load_published_json(
                health_path, "P3.18 final health", 512 * 1024
            )
            if (published and value != expected) or value != expected:
                raise FinalizeError("P3.18 final health changed during publication")
            value = _validate_health_value(self.authority, prepared, value)
        payload, receipts = _verify_observers(self.authority, prepared)
        classified = live.classify_acceptance(
            payload, prepared.bundle.manifest["observation"]["acceptance"]
        )
        correlated, topology = live._p318_finalize_candidate_phase(  # noqa: SLF001
            prepared, classified
        )
        if (
            correlated.get("accepted") is not False
            or correlated.get("host_correlation_proof_class")
            != "NO_PROOF_OBSERVER"
        ):
            raise FinalizeError("P3.18 final correlation differs")
        return {
            "health": value["health"],
            "target_evidence_sha256": value["target_evidence_sha256"],
            "observer": {
                "reads": receipts,
                "byte_identical": True,
                "bytes": len(payload),
                "sha256": _sha256(payload),
                "exact_marker_count": correlated["exact_count"],
                "marker_family_count": correlated["family_count"],
                "classification": correlated,
                "accepted": False,
            },
            "rollback_verified": True,
            "p318_candidate_topology": topology,
        }


def render_plan(authority_path: Path = DEFAULT_AUTHORITY) -> dict[str, Any]:
    authority = load_authority(authority_path)
    prepared, journal, evidence = verify_incident(authority)
    arm_path = prepared.run_dir / ARM_FILENAME
    health_path = prepared.run_dir / HEALTH_FILENAME
    if arm_path.exists() or arm_path.is_symlink():
        verify_existing_arm(authority, prepared.run_dir)
    elif health_path.exists() or health_path.is_symlink():
        raise FinalizeError("post-health P3.18 plan lacks its exact arm")
    elif journal.state() != "ROLLBACK_FLASHED":
        raise FinalizeError("advanced P3.18 plan lacks its exact arm")
    else:
        _initial_inputs_match(authority)
    return {
        "schema": "s22plus_fyg8_p318_postrollback_finalize_plan_v1",
        "verdict": "PASS_P318_POSTROLLBACK_FINALIZE_HOST_READY_REVIEW_REQUIRED",
        "approval_token": authority["approval_token"],
        "approval_binding_sha256": authority["approval_binding_sha256"],
        "incident_binding_sha256": prepared.binding_sha256,
        "journal_state": journal.state(),
        "candidate_transfers": 1,
        "rollback_transfers": 1,
        "candidate_transfer_allowed": False,
        "rollback_transfer_allowed": False,
        "existing_observer_bytes_only": True,
        "candidate_topology_record": evidence["record"],
        "device_contact": False,
        "device_writes": False,
        "live_authorized": False,
        "independent_review_required": True,
    }


def finalize(authority_path: Path, approval: str, adb: Path) -> dict[str, Any]:
    if authority_path.absolute() != DEFAULT_AUTHORITY.absolute():
        raise FinalizeError("live finalization requires the canonical authority path")
    authority = load_authority(authority_path)
    if approval != authority["approval_token"]:
        raise FinalizeError("fresh post-rollback finalizer approval differs")
    bound_adb = _paths(authority)["adb"]
    _verify_adb_execution_input(
        bound_adb,
        authority["binding"]["immutable_inputs"]["adb"],
        "P3.18 finalizer ADB execution input",
    )
    try:
        current_adb = adb.resolve(strict=True)
    except OSError as exc:
        raise FinalizeError("P3.18 finalizer ADB is unavailable") from exc
    if current_adb != bound_adb:
        raise FinalizeError("P3.18 finalizer ADB path differs")
    prepared, journal, _evidence = verify_incident(authority)
    if journal.state() == "CLOSED":
        verify_existing_arm(authority, prepared.run_dir)
        patch = ProgressCorrelationPatch()
        with patch.installed():
            result_path = prepared.run_dir / "live-result.json"
            if result_path.exists() or result_path.is_symlink():
                result = _load_json(result_path, "closed live result")
            else:
                result = live._result(  # noqa: SLF001
                    prepared,
                    journal,
                    "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
                    "candidate_not_proven_rollback_verified",
                    False,
                )
            live.validate_live_result(result, prepared)
        return result
    arm_finalizer(authority, prepared.run_dir)
    authority = load_authority(authority_path)
    prepared, journal, _evidence = verify_incident(authority)
    bound_adb = _paths(authority)["adb"]
    _verify_adb_execution_input(
        bound_adb,
        authority["binding"]["immutable_inputs"]["adb"],
        "P3.18 finalizer ADB execution input",
    )
    backend = FinalHealthOnlyBackend(authority, prepared, bound_adb)
    patch = ProgressCorrelationPatch()
    try:
        with patch.installed():
            result = live.recover_prepared(prepared, backend)
    finally:
        _verify_adb_execution_input(
            bound_adb,
            authority["binding"]["immutable_inputs"]["adb"],
            "post-run P3.18 finalizer ADB execution input",
        )
    if (
        result.get("verdict") != "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK"
        or result.get("outcome_class") != "candidate_not_proven_rollback_verified"
        or result.get("recovery_required") is not False
        or result.get("current_state") != "CLOSED"
        or result.get("live_state", {}).get("candidate_completed") is not True
        or result.get("live_state", {}).get("rollback_completed") is not True
        or result.get("live_state", {}).get("final_verified") is not True
        or (prepared.run_dir / "candidate-attempt-02.start.json").exists()
        or (prepared.run_dir / "rollback-attempt-02.start.json").exists()
    ):
        raise FinalizeError("P3.18 finalizer terminal result differs")
    with patch.installed():
        live.validate_live_result(result, prepared)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build-authority", action="store_true")
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--finalize", action="store_true")
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--approval")
    parser.add_argument("--adb", type=Path, default=DEFAULT_ADB)
    args = parser.parse_args(argv)
    try:
        if args.build_authority:
            sys.stdout.buffer.write(encode_authority(build_authority()))
            return 0
        if args.validate:
            result = render_plan(args.authority)
        else:
            if not isinstance(args.approval, str):
                raise FinalizeError("--finalize requires exact --approval")
            result = finalize(args.authority, args.approval, args.adb)
    except (
        FinalizeError,
        live.F1LiveError,
        live.core.F1V2Error,
        OSError,
    ) as exc:
        print(f"P3.18 post-rollback finalizer error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
