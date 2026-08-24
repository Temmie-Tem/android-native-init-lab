#!/usr/bin/env python3
"""H0-only Process-v2 prerequisite audit for the P3.19 S22+ successor.

This auditor does not create a manifest, approval, live run, recovery
authority, or device command. It binds the already-consumed P3.18 rollback
evidence, exercises the generic journal/attempt code in disposable host-only
directories, and probes the raw-first auditor against a real copied source
population. The result is intentionally blocked until a reviewed global
consumed-candidate registry is consumed by the live runner.
"""

from __future__ import annotations

import copy
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tarfile
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
PUBLIC_MANIFEST_DIR = ROOT / "workspace/public/src/device-action/manifests"
PRIVATE_RUNS = ROOT / "workspace/private/runs"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"

SCHEMA = "s22plus_fyg8_p319_process_v2_prerequisite_audit_v1"
VERDICT = "PASS_P319_PREREQUISITE_H0"
RAW_AUDITOR_SHA256 = "ab6c04b5acbe01dce3f3aadd25abf387849b7447b4d615151f8324d65e387ced"
RAW_AUDITOR_SIZE = 64_544
RAW_RECEIPT_SHA256 = "9c5d892c032c972fef1106dd9c564664ae69049409d31b1008d11f42fe2ef1ea"
RAW_RECEIPT_SIZE = 11_792
RAW_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260824-03-p319-d0-fresh-baseline.json"
)
RAW_AUDITOR = SCRIPT_DIR / "s22plus_fyg8_raw_first_observer_audit.py"
RESTART_PROBE = ROOT / "workspace/public/src/scripts/h0/s22plus_fyg8_p319_restart_probe.py"
RESTART_PROBE_SIZE = 2_974
RESTART_PROBE_SHA256 = "e24090b43d9a0b59f675f7a4c2bab8ee6343183dd34e3bdee9ff86f116dc1e7f"
RAW_PROJECTION_EXCLUDED = (
    "all_revalidation_python_files_scanned",
    "subprocess_modules_scanned",
)
CONSUMED_REGISTRY = SCRIPT_DIR / "consumed_candidate_registry_v1.py"
CONSUMED_REGISTRY_QUALIFICATION_HELPER = ROOT / (
    "workspace/public/src/scripts/h0/"
    "device_action_f1_consumed_candidate_registry_qualification_v1.py"
)
CONSUMED_REGISTRY_QUALIFICATION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "consumed-candidate-registry-qualification-20260823-02.json"
)

P318_RUN = ROOT / (
    "workspace/private/runs/device-action-f1-live-v2/"
    "s22plus-fyg8-p318-live-1"
)
P318_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
P318_CLOSE_AUDIT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "postrollback-close-audit-20260817-01.json"
)
P319_CANDIDATE_AP = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-49/candidate-a/odin4/AP.tar.md5"
)
NEW_LIVE_RUN_ID = "s22plus-fyg8-p319-live-1"
CARRIER_OBSERVATION_RUN_ID = "b9cc424d0d184f5accbce94a844e817d"
CANDIDATE_AP_SHA256 = "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6"
P318_BINDING_SHA256 = "fd68d3b4713d13afceaabdc5f97240f76808a5be2d09fc59b8853bcfd6e39136"
PRIVATE_JSON_NAMES = frozenset(
    {"prepared.json", "live-result.json", "live-state.json", "journal-head.json"}
)


class AuditError(RuntimeError):
    """An execution-critical prerequisite or evidence identity is invalid."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": _sha(data)}


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _stable_bytes(
    path: Path,
    label: str,
    *,
    expected: Mapping[str, Any] | None = None,
    mode: int | None = None,
    nlink: int | None = None,
    maximum: int = 64 * 1024 * 1024,
) -> bytes:
    direct = path.absolute()
    try:
        before = os.lstat(direct)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise AuditError(f"{label} is not a direct regular file: {direct}")
        if direct.resolve(strict=True) != direct:
            raise AuditError(f"{label} has an indirect path: {direct}")
        descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            inside_before = os.fstat(descriptor)
            chunks: list[bytes] = []
            total = 0
            while chunk := os.read(descriptor, 1024 * 1024):
                total += len(chunk)
                if total > maximum:
                    raise AuditError(f"{label} exceeds its size bound")
                chunks.append(chunk)
            inside_after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        after = os.lstat(direct)
    except OSError as exc:
        raise AuditError(f"{label} is unavailable: {direct}") from exc
    before_id = (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    )
    inside_before_id = (
        inside_before.st_dev,
        inside_before.st_ino,
        inside_before.st_size,
        inside_before.st_mtime_ns,
    )
    inside_after_id = (
        inside_after.st_dev,
        inside_after.st_ino,
        inside_after.st_size,
        inside_after.st_mtime_ns,
    )
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    data = b"".join(chunks)
    if (
        before_id != inside_before_id
        or inside_before_id != inside_after_id
        or inside_after_id != after_id
        or len(data) != before.st_size
        or expected is not None and _identity(data) != dict(expected)
        or mode is not None and stat.S_IMODE(before.st_mode) != mode
        or nlink is not None and before.st_nlink != nlink
    ):
        raise AuditError(f"{label} identity differs: {direct}")
    return data


def _strict_json(
    path: Path,
    label: str,
    *,
    canonical: bool = False,
    mode: int | None = None,
    maximum: int = 64 * 1024 * 1024,
) -> tuple[dict[str, Any], dict[str, Any]]:
    data = _stable_bytes(path, label, mode=mode, nlink=1, maximum=maximum)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> Any:
        raise AuditError(f"{label} has non-finite JSON constant: {value}")

    try:
        value = json.loads(data, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not a JSON object")
    if canonical:
        pretty = (
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode()
        compact = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
        ).encode()
        if data not in {pretty, compact}:
            raise AuditError(f"{label} is not canonical JSON")
    info = path.stat()
    return value, {
        "path": _relative(path),
        **_identity(data),
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        "nlink": info.st_nlink,
    }


def _contains(value: Any, needle: str) -> bool:
    if isinstance(value, str):
        return value == needle
    if isinstance(value, dict):
        return any(
            _contains(key, needle) or _contains(item, needle)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains(item, needle) for item in value)
    return False


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    previous = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous
    return module


def _journal_receipts(
    journal_dir: Path, start: int, end: int
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for sequence in range(start, end + 1):
        matches = sorted(journal_dir.glob(f"{sequence:04d}-*.json"))
        if len(matches) != 1:
            raise AuditError(f"journal sequence {sequence} is not uniquely present")
        _value, receipt = _strict_json(
            matches[0], f"journal record {sequence}", mode=0o400
        )
        result[f"{sequence:04d}"] = receipt
    return result


def audit_recovery_usability() -> dict[str, Any]:
    """Bind the exact P3.18 rollback AP to the demonstrated Download path."""
    start_path = P318_RUN / "rollback-attempt-01.start.json"
    result_path = P318_RUN / "rollback-attempt-01.result.json"
    raw_path = P318_RUN / "p318-topology-rollback-download.raw.json"
    topology_path = P318_RUN / "p318-topology-rollback-download.record.json"
    start_topology_path = P318_RUN / "p318-topology-download-start.record.json"
    live_result_path = P318_RUN / "live-result.json"
    health_path = P318_RUN / "p318-postrollback-final-health.json"
    journal_head_path = P318_RUN / "transaction/journal-head.json"

    start, start_receipt = _strict_json(
        start_path, "rollback attempt start", mode=0o400
    )
    if start != {
        "approval_binding_sha256": P318_BINDING_SHA256,
        "attempt": 1,
        "kind": "rollback",
        "prefix": "rollback-attempt-01",
        "schema": "device_action_f1_transfer_attempt_start_v2",
    }:
        raise AuditError("rollback attempt start is not the exact bound record")

    transfer, transfer_receipt = _strict_json(
        result_path, "rollback transfer result", mode=0o400
    )
    if (
        transfer.get("schema") != "device_action_f1_transfer_receipt_v2"
        or transfer.get("kind") != "rollback"
        or transfer.get("attempt") != 1
        or transfer.get("prefix") != "rollback-attempt-01"
        or transfer.get("classification") != "odin_transfer_completed"
    ):
        raise AuditError("rollback transfer is not one completed exact attempt")
    transport = transfer.get("transport")
    if not isinstance(transport, dict):
        raise AuditError("rollback transfer lacks transport receipt")
    if transport.get("label") != "rollback" or transport.get("returncode") != 0:
        raise AuditError("rollback transport completion is not proven")
    if (
        transport.get("regular_path_inputs") is not True
        or transport.get("anonymous_proc_fd_inputs") is not False
    ):
        raise AuditError("rollback did not use regular absolute path inputs")
    ap = transport.get("ap")
    ap_data = _stable_bytes(
        P318_ROLLBACK_AP,
        "rollback AP",
        mode=0o600,
        nlink=1,
        maximum=256 * 1024 * 1024,
    )
    if (
        not isinstance(ap, dict)
        or ap.get("path") != str(P318_ROLLBACK_AP.resolve())
        or ap.get("sha256") != _sha(ap_data)
        or ap.get("size") != len(ap_data)
    ):
        raise AuditError("rollback transport AP is not the exact d2373b artifact")
    try:
        with tarfile.open(fileobj=io.BytesIO(ap_data), mode="r:") as archive:
            members = archive.getmembers()
    except (tarfile.TarError, OSError) as exc:
        raise AuditError("rollback AP is not a readable tar archive") from exc
    if len(members) != 1 or members[0].name != "boot.img.lz4" or not members[0].isreg():
        raise AuditError("rollback AP does not have exactly one regular boot.img.lz4 member")

    raw, raw_receipt = _strict_json(
        raw_path, "rollback topology raw", mode=0o400
    )
    record, record_receipt = _strict_json(
        topology_path, "rollback topology record", mode=0o400
    )
    start_record, _ = _strict_json(
        start_topology_path, "candidate start topology record", mode=0o400
    )
    if (
        raw.get("schema") != "s22plus_fyg8_p318_topology_raw_snapshot_v1"
        or raw.get("phase") != "rollback_download"
        or raw.get("capture_complete") is not True
        or not isinstance(raw.get("endpoints"), list)
        or len(raw["endpoints"]) != 1
    ):
        raise AuditError("rollback topology raw snapshot is incomplete")
    if (
        record.get("schema") != "s22plus_fyg8_p318_topology_phase_record_v1"
        or record.get("phase") != "rollback_download"
        or record.get("authority_state") != "rollback_bound_exact"
        or record.get("comparison_binding_id_sha256") != P318_BINDING_SHA256
        or record.get("binding_id_sha256") != P318_BINDING_SHA256
        or record.get("match_count") != 1
        or record.get("decision", {}).get("relationship") != "same"
        or record.get("decision", {}).get("rollback_resume") is not True
        or record.get("decision", {}).get("park") is not False
        or record.get("snapshot_capture_complete") is not True
        or record.get("observation_window_complete") is not True
    ):
        raise AuditError("rollback topology record does not prove rollback_bound_exact")
    if (
        record.get("target_identity_sha256") != start_record.get("target_identity_sha256")
        or record.get("topology_sha256") != start_record.get("topology_sha256")
        or record.get("controller_path_sha256") != start_record.get("controller_path_sha256")
        or record.get("usb_device_path_sha256") != start_record.get("usb_device_path_sha256")
    ):
        raise AuditError("rollback topology is not the demonstrated same-path rebind")

    live_result, live_receipt = _strict_json(
        live_result_path, "P318 live result", mode=0o400
    )
    final_evidence = live_result.get("live_state", {}).get("final_evidence", {})
    if (
        live_result.get("current_state") != "CLOSED"
        or final_evidence.get("rollback_verified") is not True
    ):
        raise AuditError("P318 live result is not a closed rollback-verified run")
    health, health_receipt = _strict_json(
        health_path, "post-rollback final health", mode=0o400
    )
    health_value = health.get("health")
    if not isinstance(health_value, dict) or any(
        health_value.get(key) is not True
        for key in (
            "android_boot_completed",
            "boot_animation_stopped",
            "odin_endpoint_absent",
            "root_verified",
        )
    ):
        raise AuditError("post-rollback final health is not healthy")

    journal_module = _load_module(
        SCRIPT_DIR / "device_action_f1_v2.py", "p319_prereq_journal_core"
    )
    journal = journal_module.Journal.reopen(
        P318_RUN / "transaction", P318_BINDING_SHA256
    )
    records = journal.records()
    expected_tail = [
        ("transition", "RECOVERY_DOWNLOAD", "recovery_download_identified"),
        ("event", "RECOVERY_DOWNLOAD", "rollback_flash_start"),
        ("checkpoint", "RECOVERY_DOWNLOAD", "rollback_transfer_attempt"),
        ("transition", "ROLLBACK_FLASHED", "rollback_flashed"),
        ("event", "ROLLBACK_FLASHED", "rollback_flash_done"),
        ("transition", "HEALTH_VERIFIED", "final_health_verified"),
        ("event", "HEALTH_VERIFIED", "rollback_boot_ready"),
        ("event", "HEALTH_VERIFIED", "live_session_end"),
        ("transition", "CLOSED", "run_closed"),
    ]
    actual_tail = [
        (item["kind"], item["state"], item["action"]) for item in records[10:19]
    ]
    if (
        actual_tail != expected_tail
        or journal.state() != "CLOSED"
        or len(records) != 19
    ):
        raise AuditError("P318 journal tail is not the exact closed rollback chain")
    journal_receipts = _journal_receipts(
        P318_RUN / "transaction/journal", 10, 18
    )
    _head, head_receipt = _strict_json(
        journal_head_path, "journal head", mode=0o400
    )

    close, close_receipt = _strict_json(
        P318_CLOSE_AUDIT, "P318 postrollback close audit", mode=0o400
    )
    terminal = close.get("terminal", {})
    if (
        close.get("verdict") != "PASS_P318_POSTROLLBACK_CLOSE_AUDIT_H0"
        or terminal.get("journal_state") != "CLOSED"
        or terminal.get("journal_record_count") != 19
        or terminal.get("candidate_transfers") != 1
        or terminal.get("rollback_transfers") != 1
        or terminal.get("candidate_attempt_2_absent") is not True
        or terminal.get("rollback_attempt_2_absent") is not True
        or terminal.get("recovery_required") is not False
    ):
        raise AuditError("P318 postrollback close audit terminal differs")
    return {
        "artifact": {
            "path": _relative(P318_ROLLBACK_AP),
            **_identity(ap_data),
            "mode": "0600",
            "nlink": 1,
            "single_member": "boot.img.lz4",
        },
        "transport": {
            "classification": transfer["classification"],
            "attempts": 1,
            "attempt_2_absent": not (
                P318_RUN / "rollback-attempt-02.start.json"
            ).exists(),
            "start": start_receipt,
            "result": transfer_receipt,
        },
        "topology": {
            "raw": raw_receipt,
            "record": record_receipt,
            "authority_state": record["authority_state"],
            "same_path": True,
        },
        "journal": {
            "records_0010_0018": journal_receipts,
            "head": head_receipt,
            "record_count": len(records),
            "state": journal.state(),
        },
        "postrollback_close_audit": close_receipt,
        "final_health": health_receipt,
        "demonstrated_download_path": True,
        "rollback_bound_exact": True,
        "classification": "odin_transfer_completed",
        "final_healthy_closed": True,
    }


def _population_paths() -> list[Path]:
    paths = list(sorted(PUBLIC_MANIFEST_DIR.glob("*.json")))
    for path in sorted(PRIVATE_RUNS.rglob("*.json")):
        if (
            path.name in PRIVATE_JSON_NAMES
            or path.parent.name == "journal"
            or path.name.endswith(".start.json")
            or path.name.endswith(".result.json")
        ):
            paths.append(path)
    return paths


def _qualify_registry(module: Any) -> dict[str, Any]:
    helper = _load_module(
        CONSUMED_REGISTRY_QUALIFICATION_HELPER,
        "global consumed-candidate registry qualification helper",
    )
    value = helper.build(module, ROOT)
    helper_data = _stable_bytes(
        CONSUMED_REGISTRY_QUALIFICATION_HELPER,
        "global registry qualification helper",
        maximum=2 * 1024 * 1024,
    )
    value["qualification_helper"] = {
        "path": _relative(CONSUMED_REGISTRY_QUALIFICATION_HELPER),
        **_identity(helper_data),
    }
    return value


def audit_no_replay() -> dict[str, Any]:
    candidate_data = _stable_bytes(
        P319_CANDIDATE_AP,
        "P319 candidate AP",
        expected={"size": 27_279_401, "sha256": CANDIDATE_AP_SHA256},
        mode=0o400,
        nlink=1,
        maximum=256 * 1024 * 1024,
    )
    try:
        with tarfile.open(fileobj=io.BytesIO(candidate_data), mode="r:") as archive:
            candidate_members = archive.getmembers()
    except (tarfile.TarError, OSError) as exc:
        raise AuditError("P319 candidate AP is not a readable tar archive") from exc
    if (
        len(candidate_members) != 1
        or candidate_members[0].name != "boot.img.lz4"
        or not candidate_members[0].isreg()
    ):
        raise AuditError("P319 candidate AP is not exactly one boot-only member")
    files: list[dict[str, Any]] = []
    public_live_ids: list[str] = []
    observation_ids: list[str] = []
    occurrences: list[str] = []
    population = _population_paths()
    for path in population:
        is_public = path.is_relative_to(PUBLIC_MANIFEST_DIR)
        value, receipt = _strict_json(
            path,
            "public manifest" if is_public else "private prepared/journal population",
            canonical=False,
            mode=None,
        )
        files.append(receipt)
        if is_public:
            if isinstance(value.get("run_id"), str):
                if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,95}", value["run_id"]):
                    raise AuditError(f"manifest run_id is not ID_RE: {path}")
                public_live_ids.append(value["run_id"])
            acceptance = value.get("observation", {}).get("acceptance", {})
            if isinstance(acceptance, dict) and isinstance(
                acceptance.get("run_id"), str
            ):
                observation_ids.append(acceptance["run_id"])
        if _contains(value, NEW_LIVE_RUN_ID) or _contains(value, CANDIDATE_AP_SHA256):
            occurrences.append(receipt["path"])
    ledger_data = _stable_bytes(
        LEDGER, "campaign ledger", maximum=64 * 1024 * 1024
    )
    ledger_text = ledger_data.decode("utf-8")
    if NEW_LIVE_RUN_ID in ledger_text or CANDIDATE_AP_SHA256 in ledger_text:
        occurrences.append(_relative(LEDGER))
    if CARRIER_OBSERVATION_RUN_ID not in observation_ids:
        raise AuditError("carrier observation run_id is absent from public observation namespace")
    if CARRIER_OBSERVATION_RUN_ID in public_live_ids:
        raise AuditError("carrier observation run_id leaked into top-level live namespace")
    if occurrences:
        raise AuditError(
            "new P319 live_run_id/candidate pair is already present: "
            + ",".join(occurrences)
        )

    registry_module = _load_module(
        CONSUMED_REGISTRY, "global consumed-candidate registry"
    )
    try:
        qualification = _qualify_registry(registry_module)
        live_consumption = _audit_live_registry_consumption()
    except Exception as exc:
        raise AuditError(
            f"global consumed-candidate registry qualification failed: {type(exc).__name__}"
        ) from exc
    qualification_value = {
        **qualification,
        "registry_source": {
            "path": _relative(CONSUMED_REGISTRY),
            **_identity(_stable_bytes(CONSUMED_REGISTRY, "registry source", maximum=2 * 1024 * 1024)),
        },
        "live_runner_consumption": live_consumption,
        "device_contact": False,
        "live_authorized": False,
    }
    if CONSUMED_REGISTRY_QUALIFICATION.exists() or CONSUMED_REGISTRY_QUALIFICATION.is_symlink():
        existing, qualification_receipt = _strict_json(
            CONSUMED_REGISTRY_QUALIFICATION,
            "consumed-candidate registry qualification receipt",
            mode=0o400,
            canonical=False,
        )
        if existing != qualification_value:
            raise AuditError("global registry qualification receipt changed")
    else:
        qualification_receipt = write_receipt(
            CONSUMED_REGISTRY_QUALIFICATION,
            qualification_value,
            canonical=True,
        )
    registry = registry_module.registry_root(ROOT)
    registry_present = registry.is_dir() and not registry.is_symlink()
    runner_consumes_registry = (
        live_consumption["ast_imported"] is True
        and live_consumption["preflight_before_download_request"] is True
        and live_consumption["claim_before_backend_transfer"] is True
    )
    capability_authoritative = (
        registry_present and qualification_receipt["nlink"] == 1
    )
    return {
        "carrier_observation_run_id": CARRIER_OBSERVATION_RUN_ID,
        "process_live_run_id": NEW_LIVE_RUN_ID,
        "candidate_ap": {
            "path": _relative(P319_CANDIDATE_AP),
            **_identity(candidate_data),
            "mode": "0400",
            "nlink": 1,
            "single_member": "boot.img.lz4",
        },
        "observation_and_consumption_namespaces_distinct": True,
        "public_manifest_count": sum(
            1 for path in population if path.is_relative_to(PUBLIC_MANIFEST_DIR)
        ),
        "population_file_count": len(files),
        "new_live_run_id_absent": True,
        "candidate_pair_absent": True,
        "strict_population_scan": True,
        "global_consumed_run_registry": {
            "path": _relative(registry),
            "present": registry_present,
            "runner_consumes_it": runner_consumes_registry,
            "capability_authoritative": capability_authoritative,
            "runner_registry_consumption_proved": runner_consumes_registry,
            "runner_recovery_closed": False,
            "runner_ready": False,
            "qualification": qualification_receipt,
            "structural_consumption": live_consumption,
        },
        "status": VERDICT,
        "reason": (
            "global registry is fixed, hash-chained, restart-durable, and consumed "
            "before candidate backend transfer; historical APs are blocked at activation"
        ),
    }


def _validate_restart_probe_source(path: Path = RESTART_PROBE) -> dict[str, Any]:
    data = _stable_bytes(
        path,
        "fresh-process restart probe",
        expected={"size": RESTART_PROBE_SIZE, "sha256": RESTART_PROBE_SHA256},
        maximum=128 * 1024,
    )
    try:
        tree = ast.parse(data.decode("utf-8"), filename=str(path))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise AuditError("fresh-process restart probe is not valid Python") from exc
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            if node.func.attr != "run":
                raise AuditError("restart probe uses a non-run subprocess API")
            calls.append(node)
    if len(calls) != 1:
        raise AuditError("restart probe must contain exactly one subprocess.run call")
    call = calls[0]
    if len(call.args) != 1 or not isinstance(call.args[0], ast.List):
        raise AuditError("restart probe subprocess command shape differs")
    command = call.args[0].elts
    if not (
        len(command) == 3
        and isinstance(command[0], ast.Attribute)
        and isinstance(command[0].value, ast.Name)
        and command[0].value.id == "sys"
        and command[0].attr == "executable"
        and isinstance(command[1], ast.Constant)
        and command[1].value == "-c"
        and isinstance(command[2], ast.Name)
        and command[2].id == "code"
    ):
        raise AuditError("restart probe is not a fresh Python -c invocation")
    allowed_keywords = {"cwd", "check", "capture_output", "text"}
    if {item.arg for item in call.keywords} != allowed_keywords:
        raise AuditError("restart probe subprocess keyword shape differs")
    info = path.stat()
    return {
        "path": _relative(path),
        **_identity(data),
        "mode_observed": f"{stat.S_IMODE(info.st_mode):04o}",
        "nlink": info.st_nlink,
        "fresh_python_command_only": True,
    }


def audit_restart_durability() -> dict[str, Any]:
    helper_receipt = _validate_restart_probe_source()
    probe = _load_module(RESTART_PROBE, "p319_restart_probe")
    with tempfile.TemporaryDirectory(prefix="p319-process-journal-") as temporary:
        run_dir = Path(temporary) / "run"
        outputs: list[dict[str, Any]] = []
        try:
            outputs = probe.run_probe(SCRIPT_DIR, run_dir, ROOT)
        except Exception as exc:
            raise AuditError(f"journal restart probe failed: {exc}") from exc
        if (
            outputs[0].get("attempt") != 1
            or outputs[1].get("attempt") != 2
            or outputs[2].get("rejected") is not True
        ):
            raise AuditError("journal attempt restart sequence is not 1, 2, reject")
        if any(item.get("backend_calls") != 0 for item in outputs):
            raise AuditError("journal probe invoked a backend")
        journal_module = _load_module(
            SCRIPT_DIR / "device_action_f1_v2.py", "p319_restart_check_core"
        )
        journal = journal_module.Journal.reopen(run_dir / "transaction", "a" * 64)
        records = journal.records()
        start_paths = sorted(run_dir.glob("candidate-attempt-*.start.json"))
        checkpoints = [
            item
            for item in records
            if item["kind"] == "checkpoint"
            and item["action"] == "candidate_transfer_attempt"
        ]
        if (
            len(start_paths) != 2
            or len(checkpoints) != 2
            or journal.state() != "DOWNLOAD_IDENTIFIED"
        ):
            raise AuditError(
                "journal start/checkpoint evidence did not survive process restart"
            )
        retained = {}
        for path in start_paths:
            _value, receipt = _strict_json(
                path, "retained candidate attempt start", mode=0o400
            )
            receipt["path"] = path.name
            retained[path.name] = receipt
        return {
            "helper": helper_receipt,
            "process_restarts": outputs,
            "attempts_after_reopen": 2,
            "third_attempt_rejected": True,
            "journal_state": journal.state(),
            "retained_start_receipts": retained,
            "retained_checkpoint_count": len(checkpoints),
            "backend_transfer_calls": 0,
            "device_function_calls": 0,
        }


def _raw_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    projection = copy.deepcopy(dict(value))
    missing = [name for name in RAW_PROJECTION_EXCLUDED if name not in projection]
    if missing:
        raise AuditError("raw-first receipt lacks census fields: " + ",".join(missing))
    for name in RAW_PROJECTION_EXCLUDED:
        projection.pop(name)
    return projection


def audit_raw_first_population() -> dict[str, Any]:
    auditor_data = _stable_bytes(
        RAW_AUDITOR,
        "raw-first auditor",
        expected={"size": RAW_AUDITOR_SIZE, "sha256": RAW_AUDITOR_SHA256},
        maximum=2 * 1024 * 1024,
    )
    auditor_info = RAW_AUDITOR.stat()
    if auditor_info.st_nlink != 1:
        raise AuditError("raw-first auditor has an unexpected link count")
    receipt, receipt_identity = _strict_json(
        RAW_RECEIPT, "raw-first receipt", mode=0o400, maximum=16 * 1024 * 1024
    )
    if (
        receipt_identity["size"] != RAW_RECEIPT_SIZE
        or receipt_identity["sha256"] != RAW_RECEIPT_SHA256
    ):
        raise AuditError("raw-first receipt identity differs")
    if receipt.get("verdict") != "PASS_S22PLUS_FYG8_RAW_FIRST_OBSERVER_BOUNDARY_H0":
        raise AuditError("raw-first receipt verdict differs")
    raw_module = _load_module(RAW_AUDITOR, "p319_raw_first_bound")
    with tempfile.TemporaryDirectory(prefix="p319-raw-first-probe-") as temporary:
        copied = Path(temporary) / "revalidation"
        shutil.copytree(SCRIPT_DIR, copied, copy_function=shutil.copy2)
        baseline = raw_module.audit_sources(copied)
        inert = copied / "inert_p319_process_v2_projection_probe.py"
        inert.write_text("def inert_probe():\n    return None\n", encoding="utf-8")
        after_add = raw_module.audit_sources(copied)
        inert.unlink()
        neutral = copied / "neutral_p319_host_process.py"
        neutral.write_text(
            "from subprocess import run\n"
            "def neutral_probe():\n"
            "    return run([\"true\"], capture_output=True)\n",
            encoding="utf-8",
        )
        after_neutral = raw_module.audit_sources(copied)
        neutral.unlink()
        after_delete = raw_module.audit_sources(copied)
        relevant = copied / "s22plus_fyg8_p319_max77705_attribute_stage_a.py"
        relevant.write_text(
            relevant.read_text(encoding="utf-8")
            + "\n# relevant mutation probe\n",
            encoding="utf-8",
        )
        try:
            raw_module.audit_sources(copied)
        except Exception as exc:
            relevant_failure = type(exc).__name__
        else:
            raise AuditError("relevant S22 acquiring-source mutation was accepted")
    base_projection = _raw_projection(baseline)
    if (
        _raw_projection(receipt) != base_projection
        or _raw_projection(after_add) != base_projection
        or _raw_projection(after_neutral) != base_projection
        or after_add.get("all_revalidation_python_files_scanned")
        <= baseline.get("all_revalidation_python_files_scanned")
        or after_neutral.get("subprocess_modules_scanned")
        <= baseline.get("subprocess_modules_scanned")
    ):
        raise AuditError("inert population addition changed the safety projection incorrectly")
    if after_delete != baseline:
        raise AuditError("deleting inert population did not restore the exact baseline receipt")
    return {
        "auditor": {
            "path": _relative(RAW_AUDITOR),
            **_identity(auditor_data),
            "mode_observed": f"{stat.S_IMODE(auditor_info.st_mode):04o}",
            "nlink": auditor_info.st_nlink,
            "mode_is_not_authority": True,
        },
        "receipt": receipt_identity,
        "semantic_projection_omits_only": list(RAW_PROJECTION_EXCLUDED),
        "baseline": {
            "all_revalidation_python_files_scanned": baseline[
                "all_revalidation_python_files_scanned"
            ],
            "subprocess_modules_scanned": baseline["subprocess_modules_scanned"],
            "projection_sha256": _sha(
                json.dumps(
                    base_projection, sort_keys=True, separators=(",", ":")
                ).encode()
            ),
        },
        "inert_addition": {
            "full_census_changed": True,
            "projection_unchanged": True,
            "restored_exactly_after_deletion": True,
        },
        "neutral_host_process_addition": {
            "full_subprocess_census_changed": True,
            "projection_unchanged": True,
        },
        "relevant_s22_mutation": {
            "failed_closed": True,
            "error_type": relevant_failure,
        },
        "override_vs_disk_population_mismatch": (
            "test-surface-only; this probe uses actual copied on-disk files "
            "and no overrides"
        ),
    }


def _audit_live_registry_consumption() -> dict[str, Any]:
    """Bind runner consumption structurally, including call ordering."""

    path = SCRIPT_DIR / "device_action_f1_live_v2.py"
    data = _stable_bytes(path, "generic live runner", maximum=2 * 1024 * 1024)
    try:
        tree = ast.parse(data.decode("utf-8"), filename=str(path))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise AuditError("generic live runner is not valid Python") from exc
    imported = any(
        isinstance(node, ast.Import)
        and any(alias.name == "consumed_candidate_registry_v1" for alias in node.names)
        for node in ast.walk(tree)
    )
    claim_calls: list[int] = []
    preflight_calls: list[int] = []
    transfer_calls: list[int] = []
    request_calls: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "consumed_registry":
            continue
        if node.func.attr == "claim":
            claim_calls.append(node.lineno)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "request_download":
                request_calls.append(node.lineno)
            elif node.func.attr == "transfer":
                transfer_calls.append(node.lineno)
    execute = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "_execute_prepared_locked"
        ),
        None,
    )
    if execute is None or not imported or len(claim_calls) != 1:
        raise AuditError("live runner registry consumption structure is incomplete")
    preflight_calls = [
        node.lineno
        for node in ast.walk(execute)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_preflight_candidate_global"
    ]
    if execute is None or not imported or len(claim_calls) != 1 or len(preflight_calls) != 1:
        raise AuditError("live runner registry consumption structure is incomplete")
    execute_calls: dict[str, list[int]] = {
        "_preflight_candidate_global": [],
        "_begin_transfer_attempt": [],
        "_claim_candidate_global": [],
    }
    execute_request_calls: list[int] = []
    execute_transfer_calls: list[int] = []
    for node in ast.walk(execute):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in execute_calls:
            execute_calls[node.func.id].append(node.lineno)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "request_download":
                execute_request_calls.append(node.lineno)
            elif node.func.attr == "transfer":
                execute_transfer_calls.append(node.lineno)
    helper_names = {
        "_preflight_candidate_global",
        "_begin_transfer_attempt",
        "_claim_candidate_global",
    }
    if not all(execute_calls[name] for name in helper_names):
        raise AuditError("live runner execute path does not consume global registry")
    ordered = bool(
        execute_request_calls
        and execute_transfer_calls
        and execute_calls["_preflight_candidate_global"][0]
        < execute_request_calls[0]
        < execute_calls["_claim_candidate_global"][0]
        < execute_calls["_begin_transfer_attempt"][0]
        < execute_transfer_calls[0]
    )
    if not ordered:
        raise AuditError("live runner registry ordering is not before candidate backend")
    candidate_transfer_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "transfer"
        and len(node.args) >= 3
        and isinstance(node.args[2], ast.Constant)
        and node.args[2].value == "candidate"
    ]
    if (
        len(candidate_transfer_calls) != 1
        or candidate_transfer_calls[0] not in set(ast.walk(execute))
        or len(execute_transfer_calls) != 1
    ):
        raise AuditError("live runner candidate backend call is not unique to execute")
    wrapper_checks: dict[str, dict[str, bool]] = {}
    for name, locked_name in (
        ("execute_prepared", "_execute_prepared_locked"),
        ("recover_prepared", "_recover_prepared_locked"),
    ):
        function = next(
            (node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name),
            None,
        )
        target_with = [] if function is None else [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.With)
            and any(
                isinstance(item.context_expr, ast.Call)
                and isinstance(item.context_expr.func, ast.Attribute)
                and isinstance(item.context_expr.func.value, ast.Name)
                and item.context_expr.func.value.id == "consumed_registry"
                and item.context_expr.func.attr == "target_session_lease"
                for item in node.items
            )
        ]
        transaction_inside = [] if len(target_with) != 1 else [
            node
            for node in ast.walk(target_with[0])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "odin_core"
            and node.func.attr == "transaction_session"
        ]
        locked_inside = [] if len(target_with) != 1 else [
            node
            for node in ast.walk(target_with[0])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == locked_name
        ]
        wrapper_checks[name] = {
            "one_target_lease": len(target_with) == 1,
            "transaction_nested": len(transaction_inside) == 1,
            "locked_body_nested": len(locked_inside) == 1,
        }
    if not all(all(checks.values()) for checks in wrapper_checks.values()):
        raise AuditError("live runner does not hold the target-session lease across execute/recover")
    return {
        "path": _relative(path),
        **_identity(data),
        "ast_imported": imported,
        "reserve_call_count": 0,
        "claim_call_count": len(claim_calls),
        "preflight_before_download_request": execute_calls["_preflight_candidate_global"][0] < execute_request_calls[0],
        "claim_before_backend_transfer": execute_calls["_claim_candidate_global"][0] < execute_transfer_calls[0],
        "claim_before_local_attempt": execute_calls["_claim_candidate_global"][0] < execute_calls["_begin_transfer_attempt"][0],
        "candidate_backend_call_count": len(candidate_transfer_calls),
        "recover_candidate_backend_call_count": 0,
        "target_session_lease_wrappers": wrapper_checks,
        "behavioral_probe": "qualification_probe",
    }


def build_receipt() -> dict[str, Any]:
    recovery = audit_recovery_usability()
    no_replay = audit_no_replay()
    restart = audit_restart_durability()
    raw_first = audit_raw_first_population()
    authority = {
        "tier": "H0",
        "host_only": True,
        "device_contact": False,
        "approval_created": False,
        "live_authorized": False,
        "candidate_success": False,
        "causal_result_allowed": False,
        "mux_result_claimable": False,
        "host_silent_claimable": False,
        "candidate_replay_authorized": False,
        "recovery_authorized": False,
        "transfer": False,
        "odin_invocations": 0,
        "adb_commands": 0,
    }
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": VERDICT,
        "target": {
            "model": "SM-S906N",
            "codename": "g0q",
            "build": "S906NKSS7FYG8",
        },
        "authority": authority,
        "recovery_usability_provenance": recovery,
        "no_replay": no_replay,
        "restart_durability": restart,
        "raw_first_execution_closure": raw_first,
        "global_registry_blocker": None,
        "scope": {
            "tier": "H0",
            "host_only": True,
            "device_contact": False,
            "approval_created": False,
            "live_authorized": False,
            "candidate_success": False,
            "causal_result_allowed": False,
            "mux_result_claimable": False,
            "host_silent_claimable": False,
        },
    }


def write_receipt(
    path: Path, value: Mapping[str, Any] | None = None, *, canonical: bool = False
) -> dict[str, Any]:
    value = dict(value or build_receipt())
    if path.exists() or path.is_symlink():
        raise AuditError(f"receipt publication is not no-clobber: {path}")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    if canonical:
        data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    else:
        data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode() + b"\n"
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                raise AuditError("short prerequisite receipt write")
            offset += written
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    _stable_bytes(
        path,
        "published prerequisite receipt",
        expected=_identity(data),
        mode=0o400,
        nlink=1,
        maximum=max(len(data), 1),
    )
    return {
        **_identity(data),
        "path": _relative(path),
        "mode": "0400",
        "nlink": 1,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        value = build_receipt()
        if args.output is not None:
            write_receipt(args.output, value)
    except AuditError as exc:
        print(f"BLOCKED_PREREQUISITE_AUDIT: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
