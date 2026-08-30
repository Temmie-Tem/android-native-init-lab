#!/usr/bin/env python3
"""H0-only Process-v2 prerequisite audit for the P3.19 S22+ successor.

This auditor does not create a manifest, approval, live run, recovery
authority, or device command. It binds the already-consumed P3.18 rollback
evidence, exercises the generic journal/attempt code in disposable host-only
directories, and probes the raw-first auditor against a real copied source
population. The reviewed global consumed-candidate registry remains H0
capability evidence and creates no live runner authority.
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
P319_READY_MANIFEST = (
    PUBLIC_MANIFEST_DIR / "s22plus_fyg8_p319_process_v2_ready_1.json"
)
PRIVATE_RUNS = ROOT / "workspace/private/runs"
LEDGER = ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md"

SCHEMA = "s22plus_fyg8_p319_process_v2_prerequisite_audit_v1"
VERDICT = "PASS_P319_PREREQUISITE_H0"
RAW_AUDITOR_SHA256 = "122c4bd497c4d54c76f4fce572f3c8dc84b6d2ea7647087692a976dc590ce4b6"
RAW_AUDITOR_SIZE = 76_345
RAW_RECEIPT_SHA256 = "54db40b2fc63f98bc235cdc52bf87e02b9b875346859eea3b2eb257e61aa0958"
RAW_RECEIPT_SIZE = 15_075
RAW_RECEIPT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "raw-first-observer-audit-20260830-24-p319-prepared-runtime-bound.json"
)
RAW_AUDITOR = SCRIPT_DIR / "s22plus_fyg8_raw_first_observer_audit.py"
LIVE_RUNNER = SCRIPT_DIR / "device_action_f1_live_v2.py"
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
    "consumed-candidate-registry-qualification-20260830-02-p319-runtime-bound.json"
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
PREPARED_KEYS = frozenset(
    {
        "schema",
        "adapter_version",
        "manifest_id",
        "bundle_sha256",
        "manifest_status",
        "d0_result",
        "private_target",
        "execution_closure",
        "approval_binding",
        "approval_binding_sha256",
        "approval_token",
        "p300_usb_trace_binding",
        "device_contact",
        "device_writes",
        "reboot_requested",
        "odin_invoked",
        "partition_transfer",
        "f1_authorized",
        "live_authorized",
    }
)
PREPARED_RUN_CHILD_NAMES = frozenset(
    {
        "prepared.json",
        "target-private.json",
        "preflight",
        "p300-usb-trace-binding.json",
    }
)
HISTORICAL_PRE_EFFECT_PREPARED = {
    "f1-2026-08-30T055154386384Z-1788069114386414032": {
        "size": 10_632,
        "sha256": "c919cf752c539f30aca0a5afc20f1e4192aff02518eeb5cecd508df89d01ef6d",
    }
}
PREPARED_EXECUTION_SOURCE_PATHS = {
    "adapter": LIVE_RUNNER,
    "cdc_acm_observer": SCRIPT_DIR / "device_action_cdc_acm_observer_v1.py",
    "raw_capture": SCRIPT_DIR / "device_action_raw_capture_v1.py",
    "usb_trace_sidecar": SCRIPT_DIR / "device_action_usb_trace_sidecar_v1.py",
    "p300_usb_trace_binding": SCRIPT_DIR / "s22plus_fyg8_p300_usb_trace_binding.py",
    "f1_core": SCRIPT_DIR / "device_action_f1_v2.py",
    "typed_evidence": SCRIPT_DIR / "device_action_f1_evidence_v2.py",
    "checkpoint_decoder": SCRIPT_DIR / "s22plus_fyg8_r4w1e_checkpoint_contract.py",
    "d0_adapter": SCRIPT_DIR / "device_action_d0_v2.py",
    "regular_path_transport": SCRIPT_DIR / "s22plus_boot_only_f1_transport.py",
    "live_core": SCRIPT_DIR / "s22plus_boot_only_live_core.py",
    "odin_transition_core": SCRIPT_DIR / "s22plus_odin_transition_core.py",
    "usbfs_identity": SCRIPT_DIR / "s22plus_odin_usbfs_identity.py",
    "p313_guard_lifetime": SCRIPT_DIR / "s22plus_fyg8_p313_guard_lifetime.py",
    "p319_stock_adapter": SCRIPT_DIR / "s22plus_fyg8_p319_stock_process_v2_adapter.py",
    "p319_carrier_model": SCRIPT_DIR / "s22plus_fyg8_p310_carrier_model.py",
    "p319_telemetry_spec": SCRIPT_DIR / "s22plus_fyg8_p308_telemetry_spec.py",
    "consumed_candidate_registry": SCRIPT_DIR / "consumed_candidate_registry_v1.py",
    "legacy_consumed_candidate_authority": (
        SCRIPT_DIR / "device_action_f1_legacy_consumed_candidate_authority_v1.json"
    ),
}

RAW_FIRST_PREDECESSOR = {
    "auditor": {
        "size": 76_339,
        "sha256": "2819d3d26c19500c173ad36d0a9e50ad58f17258425a88ce71946f58b8598409",
    },
    "receipt": {
        "path": "workspace/private/outputs/s22plus_fyg8_p319/raw-first-observer-audit-20260830-23-p319-registry-absence.json",
        "size": 15_075,
        "sha256": "608799f12b16aab51b3ef12bcb70746c4debcc13eaf9ee342dae04f596f91c6f",
    },
}


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


def _exact_json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python bool/int or int/float coercion."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _exact_json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _exact_json_equal(item, other)
            for item, other in zip(left, right)
        )
    return left == right


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


def _validate_nonconsuming_ready_manifest(
    path: Path = P319_READY_MANIFEST,
) -> dict[str, Any] | None:
    """Classify the one P319 ready declaration without treating it as use.

    The declaration is intentionally not hash-pinned here: its candidate-static
    identity is derived from this prerequisite and pinning it would create a
    circular authority.  The live runner independently verifies every contract
    artifact before an approval or effect.  This seam only proves that the
    public object is the exact non-consuming ready schema rather than a private
    prepared/journal/claim record.
    """
    if not path.exists() and not path.is_symlink():
        return None
    value, receipt = _strict_json(
        path, "P319 non-consuming ready manifest", canonical=False
    )
    if int(receipt["mode"], 8) not in {0o644, 0o664}:
        raise AuditError("P319 ready declaration public checkout mode differs")
    if set(value) != {
        "allowed_member",
        "candidate_ap",
        "final_health_profile",
        "manifest_id",
        "observation",
        "rollback_ap",
        "run_id",
        "runner_version",
        "schema",
        "status",
        "target_profile",
    }:
        raise AuditError("P319 ready declaration schema differs")
    candidate = value.get("candidate_ap")
    rollback = value.get("rollback_ap")
    observation = value.get("observation")
    acceptance = observation.get("acceptance") if isinstance(observation, dict) else None
    contract = acceptance.get("contract") if isinstance(acceptance, dict) else None
    if (
        value.get("schema") != "device_action_f1_candidate_v2"
        or value.get("status") != "ready-for-f1-approval"
        or value.get("manifest_id") != "s22plus-fyg8-p319-process-v2-ready-1"
        or value.get("run_id") != NEW_LIVE_RUN_ID
        or value.get("allowed_member") != "boot.img.lz4"
        or value.get("runner_version") != "device-action-f1-v2-host-core-3"
        or value.get("target_profile")
        != "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
        or value.get("final_health_profile") != "s22plus-fyg8-magisk"
        or not isinstance(candidate, dict)
        or set(candidate) != {"path", "size", "sha256"}
        or candidate.get("path")
        != (
            "workspace/private/outputs/s22plus_fyg8_p319/"
            "stock-witness-runtime-v1-20260821-55/candidate-a/odin4/AP.tar.md5"
        )
        or type(candidate.get("size")) is not int
        or candidate["size"] != 27_279_401
        or not isinstance(candidate.get("sha256"), str)
        or candidate["sha256"] != CANDIDATE_AP_SHA256
        or not isinstance(rollback, dict)
        or set(rollback) != {"path", "size", "sha256"}
        or rollback.get("path")
        != "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
        or type(rollback.get("size")) is not int
        or rollback["size"] != 23_367_721
        or not isinstance(rollback.get("sha256"), str)
        or rollback["sha256"]
        != "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
        or set(observation or {}) != {"acceptance", "timeout_sec"}
        or type(observation.get("timeout_sec")) is not int
        or observation["timeout_sec"] != 300
        or not isinstance(acceptance, dict)
        or set(acceptance)
        != {
            "clean_baseline_required",
            "contract",
            "decoder",
            "kind",
            "long_family_hex",
            "minimum_success_count",
            "policy_id",
            "profile",
            "run_id",
            "source",
            "source_contract_id",
            "terminal_stage",
            "unsat_family_hex",
            "userspace_overlay_contract_id",
        }
        or acceptance.get("run_id") != CARRIER_OBSERVATION_RUN_ID
        or acceptance.get("kind")
        != "retained_e1_latest_stage_multiboot_after_rollback"
        or acceptance.get("decoder")
        != "s22plus_fyg8_p319_stock_witness_carrier_v1"
        or acceptance.get("policy_id") != "44667ee3bea864cbc9ed94598480da32"
        or acceptance.get("long_family_hex") != "53323245314c327c"
        or acceptance.get("unsat_family_hex") != "533232453155327c"
        or type(acceptance.get("terminal_stage")) is not int
        or acceptance["terminal_stage"] != 147
        or type(acceptance.get("minimum_success_count")) is not int
        or acceptance["minimum_success_count"] != 1
        or acceptance.get("clean_baseline_required") is not True
        or acceptance.get("source") != "/proc/last_kmsg"
        or acceptance.get("source_contract_id")
        != "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
        or acceptance.get("userspace_overlay_contract_id")
        != "s22plus-fyg8-p319-stock-witness-carrier-v1"
        or acceptance.get("profile") != "E2"
        or not isinstance(contract, dict)
        or set(contract) != {"candidate_static", "run_manifest", "static_check"}
    ):
        raise AuditError("P319 ready declaration identity differs")
    expected_paths = {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }
    for name, filename in expected_paths.items():
        item = contract[name]
        if (
            not isinstance(item, dict)
            or set(item) != {"path", "size", "sha256"}
            or not isinstance(item.get("path"), str)
            or re.fullmatch(
                r"workspace/private/outputs/s22plus_fyg8_p319/"
                r"process-v2-promotion-202608(?:29|30)-[0-9]{2}/"
                + re.escape(filename),
                item["path"],
            )
            is None
            or type(item.get("size")) is not int
            or item["size"] <= 0
            or not isinstance(item.get("sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None
        ):
            raise AuditError("P319 ready declaration contract identity differs")
        artifact = ROOT / item["path"]
        payload = _stable_bytes(
            artifact,
            f"P319 ready declaration {name}",
            expected={"size": item["size"], "sha256": item["sha256"]},
            mode=0o400,
            nlink=1,
            maximum=2 * 1024 * 1024,
        )
        if _identity(payload) != {
            "size": item["size"],
            "sha256": item["sha256"],
        }:
            raise AuditError("P319 ready declaration artifact differs")
    return value


def _canonical_digest(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuditError("prepared record contains non-canonical JSON values") from exc
    return _sha(payload)


def _validate_prepared_receipt(
    value: Any,
    expected_path: Path,
    label: str,
) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != {"path", "size", "sha256"}
        or value.get("path") != str(expected_path.absolute())
        or type(value.get("size")) is not int
        or value["size"] < 0
        or not isinstance(value.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value["sha256"]) is None
    ):
        raise AuditError(f"{label} receipt is malformed")
    _stable_bytes(
        expected_path,
        label,
        expected={"size": value["size"], "sha256": value["sha256"]},
        mode=0o400,
        nlink=1,
        maximum=4 * 1024 * 1024,
    )


def _current_live_prepared_schema() -> tuple[str, str, frozenset[str]]:
    """Read the active runner's prepared schema without importing its runtime."""
    try:
        source = _stable_bytes(
            LIVE_RUNNER,
            "P319 live runner source",
            maximum=2 * 1024 * 1024,
        ).decode("utf-8", "strict")
        tree = ast.parse(source, filename=str(LIVE_RUNNER))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise AuditError("P319 live runner prepared schema is not parseable") from exc

    assignments: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if not isinstance(target, ast.Name) or target.id not in {
                "ADAPTER_VERSION",
                "PREPARED_SCHEMA",
            }:
                continue
            try:
                assignments[target.id] = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise AuditError(
                    "P319 live runner prepared schema constants are not literals"
                ) from exc

    expected_keys: Any = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "load_prepared":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "expected_keys"
                for target in child.targets
            ):
                continue
            try:
                expected_keys = ast.literal_eval(child.value)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise AuditError(
                    "P319 live runner prepared key schema is not a literal"
                ) from exc
            break
        break

    adapter_version = assignments.get("ADAPTER_VERSION")
    prepared_schema = assignments.get("PREPARED_SCHEMA")
    if (
        not isinstance(adapter_version, str)
        or not adapter_version
        or not isinstance(prepared_schema, str)
        or not prepared_schema
        or not isinstance(expected_keys, set)
        or any(type(key) is not str for key in expected_keys)
        or frozenset(expected_keys) != PREPARED_KEYS
    ):
        raise AuditError("P319 live runner prepared schema differs")
    return prepared_schema, adapter_version, frozenset(expected_keys)


def _current_execution_closure() -> dict[str, Any]:
    """Rebuild the runner's fixed source closure from stable source bytes."""
    sources: dict[str, Any] = {}
    for name, path in PREPARED_EXECUTION_SOURCE_PATHS.items():
        payload = _stable_bytes(
            path,
            f"P319 prepared execution source {name}",
            maximum=2 * 1024 * 1024,
        )
        sources[name] = {
            "path": str(path.absolute()),
            **_identity(payload),
        }
    return {
        "schema": "device_action_f1_execution_closure_v2",
        "sources": sources,
        "sha256": _canonical_digest(sources),
        "repo_root": str(ROOT),
    }


def _validate_nonconsuming_prepared_record(
    path: Path,
    value: Any,
    parsed_receipt: Mapping[str, Any] | None = None,
) -> None:
    """Recognize only an exact pre-effect prepared record as non-consuming.

    A prepared record is written after connected D0 but before the transaction,
    Download request, registry claim, or candidate attempt.  It must not make
    the immutable offline qualification reject its own execute step.  Any
    execution-state sibling, malformed binding, or action flag keeps the
    record in the fail-closed consumption population.
    """
    run_dir = path.parent.absolute()
    live_root = (PRIVATE_RUNS / "device-action-f1-live-v2").absolute()
    # The population scanner parsed this exact path already.  Reopen it using
    # the stable reader and compare the receipt before treating it as the one
    # pre-effect exception; a replacement between parse and classification is
    # therefore never silently exempted.
    reopened, reopened_receipt = _strict_json(
        path,
        "P319 prepared record",
        canonical=False,
        mode=0o400,
        maximum=4 * 1024 * 1024,
    )
    if parsed_receipt is not None and (
        not _exact_json_equal(reopened, value)
        or not _exact_json_equal(reopened_receipt, dict(parsed_receipt))
    ):
        raise AuditError("P319 prepared record identity differs")
    historical_identity = HISTORICAL_PRE_EFFECT_PREPARED.get(run_dir.name)
    historical = historical_identity is not None and {
        "size": reopened_receipt["size"],
        "sha256": reopened_receipt["sha256"],
    } == historical_identity
    if historical_identity is not None and not historical:
        raise AuditError("P319 historical prepared record identity differs")
    if (
        path.name != "prepared.json"
        or run_dir.parent != live_root
        or stat.S_IMODE(path.lstat().st_mode) != 0o400
        or run_dir.is_symlink()
        or not run_dir.is_dir()
        or run_dir.resolve(strict=True) != run_dir
        or not isinstance(value, dict)
        or set(value) != _current_live_prepared_schema()[2]
    ):
        raise AuditError("P319 prepared record path or schema differs")
    children = list(run_dir.iterdir())
    if {child.name for child in children} != PREPARED_RUN_CHILD_NAMES:
        raise AuditError("P319 prepared record has unexpected run children")
    expected_child_types = {
        "prepared.json": stat.S_ISREG,
        "target-private.json": stat.S_ISREG,
        "p300-usb-trace-binding.json": stat.S_ISREG,
        "preflight": stat.S_ISDIR,
    }
    for child in children:
        if child.is_symlink() or not expected_child_types[child.name](child.stat().st_mode):
            raise AuditError("P319 prepared record has unexpected run children")

    binding = value.get("approval_binding")
    base = binding.get("base_binding") if isinstance(binding, dict) else None
    closure = value.get("execution_closure")
    prepared_schema, adapter_version, _prepared_keys = _current_live_prepared_schema()
    ready = None if historical else _validate_nonconsuming_ready_manifest()
    if not historical and ready is None:
        raise AuditError("P319 ready declaration is absent")
    expected_closure = None if historical else _current_execution_closure()
    if (
        value.get("schema") != prepared_schema
        or value.get("adapter_version") != adapter_version
        or value.get("manifest_id") != "s22plus-fyg8-p319-process-v2-ready-1"
        or value.get("manifest_status") != "ready-for-f1-approval"
        or not isinstance(value.get("bundle_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", value["bundle_sha256"]) is None
        or value.get("device_contact") is not True
        or any(
            value.get(key) is not False
            for key in (
                "device_writes",
                "reboot_requested",
                "odin_invoked",
                "partition_transfer",
                "f1_authorized",
                "live_authorized",
            )
        )
        or not isinstance(binding, dict)
        or set(binding)
        != {
            "schema",
            "adapter_version",
            "base_binding",
            "base_binding_sha256",
            "d0_result",
            "private_target",
            "execution_closure_sha256",
            "mandatory_rollback_preapproved",
            "recovery_requires_second_approval",
        }
        or binding.get("schema") != "device_action_f1_live_approval_binding_v2"
        or binding.get("adapter_version") != value["adapter_version"]
        or binding.get("d0_result") != value.get("d0_result")
        or binding.get("private_target") != value.get("private_target")
        or binding.get("mandatory_rollback_preapproved") is not True
        or binding.get("recovery_requires_second_approval") is not False
        or not isinstance(base, dict)
        or set(base)
        != {
            "schema",
            "bundle_sha256",
            "candidate_ap_sha256",
            "manifest_id",
            "observation",
            "profile_id",
            "rollback_ap_sha256",
            "rollback_preapproved",
            "runner_version",
            "target_evidence_sha256",
        }
        or base.get("schema") != "device_action_f1_approval_binding_v2"
        or base.get("bundle_sha256") != value["bundle_sha256"]
        or base.get("candidate_ap_sha256") != CANDIDATE_AP_SHA256
        or base.get("manifest_id") != value["manifest_id"]
        or base.get("profile_id") != "s22plus-fyg8"
        or base.get("rollback_ap_sha256")
        != "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"
        or base.get("rollback_preapproved") is not True
        or base.get("runner_version") != "device-action-f1-v2-host-core-3"
        or not isinstance(base.get("observation"), dict)
        or not historical
        and not _exact_json_equal(base["observation"], ready["observation"])
        or not isinstance(base.get("target_evidence_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", base["target_evidence_sha256"]) is None
        or not isinstance(closure, dict)
        or set(closure) != {"repo_root", "schema", "sha256", "sources"}
        or closure.get("repo_root") != str(ROOT)
        or closure.get("schema") != "device_action_f1_execution_closure_v2"
        or not isinstance(closure.get("sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", closure["sha256"]) is None
        or not isinstance(closure.get("sources"), dict)
        or not historical
        and not _exact_json_equal(closure, expected_closure)
        or binding.get("execution_closure_sha256") != closure.get("sha256")
        or binding.get("base_binding_sha256") != _canonical_digest(base)
        or value.get("approval_binding_sha256") != _canonical_digest(binding)
        or value.get("approval_token")
        != ("DEVICE-ACTION-F1-" + "V2-APPROVE:")
        + value["approval_binding_sha256"]
    ):
        raise AuditError("P319 prepared record identity differs")

    _validate_prepared_receipt(
        value["d0_result"], run_dir / "preflight/result.json", "prepared D0 result"
    )
    _validate_prepared_receipt(
        value["private_target"], run_dir / "target-private.json", "prepared private target"
    )
    p300 = value.get("p300_usb_trace_binding")
    if not isinstance(p300, dict):
        raise AuditError("prepared USB trace binding receipt is absent")
    _validate_prepared_receipt(
        p300,
        run_dir / "p300-usb-trace-binding.json",
        "prepared USB trace binding",
    )


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


def _assert_candidate_absent_from_registry(module: Any) -> dict[str, Any]:
    records = module.history(ROOT)
    if not isinstance(records, list):
        raise AuditError("global registry history is not a list")
    active: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise AuditError("global registry history record is not an object")
        candidate_key = record.get("candidate_key")
        if not isinstance(candidate_key, str):
            raise AuditError("global registry history candidate key is malformed")
        if record.get("event") == "claim":
            active[candidate_key] = record
        elif record.get("event") == "release":
            active.pop(candidate_key, None)
        else:
            raise AuditError("global registry history event is malformed")
    matching = [
        record
        for record in active.values()
        if record.get("candidate_ap_sha256") == CANDIDATE_AP_SHA256
    ]
    if matching:
        raise AuditError("P319 candidate AP has an active global registry claim")
    return {
        "record_count": len(records),
        "active_claim_count": len(active),
        "candidate_active_claim_absent": True,
    }


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
    _validate_nonconsuming_ready_manifest()
    for path in population:
        if path == P319_READY_MANIFEST:
            continue
        is_public = path.is_relative_to(PUBLIC_MANIFEST_DIR)
        value, receipt = _strict_json(
            path,
            "public manifest" if is_public else "private prepared/journal population",
            canonical=False,
            mode=None,
        )
        if (
            not is_public
            and path.name == "prepared.json"
            and (
                _contains(value, NEW_LIVE_RUN_ID)
                or _contains(value, CANDIDATE_AP_SHA256)
            )
        ):
            _validate_nonconsuming_prepared_record(path, value, receipt)
            continue
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
        registry_history = _assert_candidate_absent_from_registry(registry_module)
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
            1
            for path in population
            if path.is_relative_to(PUBLIC_MANIFEST_DIR)
            and path != P319_READY_MANIFEST
        ),
        "population_file_count": len(files),
        "new_live_run_id_absent_from_consumed_population": True,
        "candidate_pair_absent_from_consumed_population": True,
        "ready_manifest_is_nonconsuming_declaration": True,
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
            "history": registry_history,
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
        "predecessor": RAW_FIRST_PREDECESSOR,
        "semantic_projection_omits_only": list(RAW_PROJECTION_EXCLUDED),
        "baseline": {
            "projection_sha256": _sha(
                json.dumps(
                    base_projection, sort_keys=True, separators=(",", ":")
                ).encode()
            ),
        },
        "census_values_retained_only_in_raw_receipt": True,
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
