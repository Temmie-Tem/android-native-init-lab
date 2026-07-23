#!/usr/bin/env python3
"""Reusable attended boot-only F1 adapter for Device Action Process v2."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ContextManager, Protocol

import device_action_d0_v2 as d0
import device_action_f1_evidence_v2 as typed_evidence
import device_action_f1_v2 as core
import s22plus_boot_only_f1_transport as transport
import s22plus_boot_only_live_core as live_core
import s22plus_odin_transition_core as odin_core
import s22plus_odin_usbfs_identity as usbfs_identity


ADAPTER_VERSION = "device-action-f1-live-v2-1"
PREPARED_SCHEMA = "device_action_f1_prepared_v2"
PRIVATE_TARGET_SCHEMA = "device_action_f1_private_target_v2"
LIVE_STATE_SCHEMA = "device_action_f1_live_state_v2"
LIVE_RESULT_SCHEMA = "device_action_f1_live_result_v2"
APPROVAL_PREFIX = "DEVICE-ACTION-F1-V2-APPROVE:"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/device-action-f1-live-v2")
DEFAULT_USB_ROOT = Path("/sys/bus/usb/devices")
MAX_PRIVATE_JSON = 1024 * 1024
MAX_ODIN_OUTPUT = 8 * 1024 * 1024
MAX_OBSERVER_BYTES = 64 * 1024 * 1024
MAX_ATTEMPTS = 2
DOWNLOAD_WAIT_SEC = 180
ROLLBACK_WAIT_SEC = 600
ANDROID_WAIT_SEC = 420
DISCONNECT_WAIT_SEC = 120
ODIN_TIMEOUT_SEC = 240
ENDPOINT_REVALIDATE_SEC = 20


class F1LiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedRun:
    root: Path
    run_dir: Path
    bundle: core.Bundle
    prepared: dict[str, Any]
    private_target: dict[str, str]

    @property
    def binding_sha256(self) -> str:
        return str(self.prepared["approval_binding_sha256"])

    @property
    def approval_token(self) -> str:
        return APPROVAL_PREFIX + self.binding_sha256


@dataclass(frozen=True)
class Endpoint:
    device: str
    sequence: int
    identity_sha256: str


@dataclass(frozen=True)
class TransferOutcome:
    classification: str
    completed: bool
    possible_device_session: bool
    receipt: dict[str, Any]


class LiveBackend(Protocol):
    def recheck_android(
        self, prepared: PreparedRun, destination: Path
    ) -> dict[str, Any]: ...

    def request_download(self, prepared: PreparedRun) -> None: ...

    def endpoint_session(self, run_dir: Path) -> ContextManager[Any]: ...

    def wait_download(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        timeout_sec: float,
    ) -> Endpoint: ...

    def transfer(
        self,
        prepared: PreparedRun,
        endpoint: Endpoint,
        kind: str,
        destination: Path,
        attempt: int,
        prefix: str,
    ) -> TransferOutcome: ...

    def observe_candidate(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
    ) -> dict[str, Any]: ...

    def verify_final(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        destination: Path,
    ) -> dict[str, Any]: ...


def _receipt(path: Path, label: str, maximum: int = MAX_PRIVATE_JSON) -> dict[str, Any]:
    payload, value = core._stable_read(path, label, maximum)
    return {**value, "sha256": hashlib.sha256(payload).hexdigest()}


def _read_json(path: Path, label: str) -> dict[str, Any]:
    payload, _value = core._stable_read(path, label, MAX_PRIVATE_JSON)
    try:
        parsed = json.loads(payload, object_pairs_hook=core._unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise F1LiveError(f"{label} is not canonical JSON") from exc
    if not isinstance(parsed, dict):
        raise F1LiveError(f"{label} must be an object")
    return parsed


def _write_exclusive(path: Path, value: Any) -> None:
    try:
        core._write_exclusive(path, value)
    except core.F1V2Error as exc:
        raise F1LiveError(str(exc)) from exc


def _write_atomic(path: Path, value: Any) -> None:
    try:
        core._write_atomic(path, value)
    except core.F1V2Error as exc:
        raise F1LiveError(str(exc)) from exc


def _closure(root: Path) -> dict[str, Any]:
    scripts = Path(__file__).resolve().parent
    paths = {
        "adapter": Path(__file__).resolve(),
        "f1_core": scripts / "device_action_f1_v2.py",
        "typed_evidence": scripts / "device_action_f1_evidence_v2.py",
        "checkpoint_decoder": scripts / "s22plus_fyg8_r4w1e_checkpoint_contract.py",
        "d0_adapter": scripts / "device_action_d0_v2.py",
        "regular_path_transport": scripts / "s22plus_boot_only_f1_transport.py",
        "live_core": scripts / "s22plus_boot_only_live_core.py",
        "odin_transition_core": scripts / "s22plus_odin_transition_core.py",
        "usbfs_identity": scripts / "s22plus_odin_usbfs_identity.py",
    }
    values = {
        name: _receipt(path.resolve(), f"execution source {name}")
        for name, path in paths.items()
    }
    return {
        "schema": "device_action_f1_execution_closure_v2",
        "sources": values,
        "sha256": core.json_sha256(values),
        "repo_root": str(root),
    }


def _private_root(root: Path) -> Path:
    direct = (root / "workspace/private").absolute()
    if (
        direct.is_symlink()
        or not direct.is_dir()
        or direct.resolve(strict=True) != direct
    ):
        raise F1LiveError("workspace/private is unavailable or indirect")
    return direct


def allocate_run_dir(root: Path, requested: Path | None = None) -> Path:
    root = root.resolve()
    private = _private_root(root)
    base_direct = (root / DEFAULT_RUN_ROOT).absolute()
    if base_direct.exists() and base_direct.resolve(strict=True) != base_direct:
        raise F1LiveError("F1 run root has an indirect path component")
    base_direct.mkdir(parents=True, exist_ok=True)
    base = base_direct.resolve(strict=True)
    try:
        base.relative_to(private)
    except ValueError as exc:
        raise F1LiveError("F1 run root escaped workspace/private") from exc
    if base.is_symlink() or not base.is_dir() or base != base_direct:
        raise F1LiveError("F1 run root is indirect")
    candidate = requested or base / f"f1-{core.utc_now().replace(':', '').replace('.', '')}-{time.time_ns()}"
    candidate = candidate if candidate.is_absolute() else root / candidate
    candidate = candidate.absolute()
    if candidate.parent != base:
        raise F1LiveError("F1 run directory must be a direct child of its private root")
    if candidate.exists() or candidate.is_symlink():
        raise F1LiveError("F1 run directory already exists")
    candidate.mkdir(mode=0o700)
    if candidate.resolve(strict=True) != candidate:
        raise F1LiveError("F1 run directory became indirect")
    core._fsync_dir(candidate.parent)
    return candidate


def _validate_private_run_dir(root: Path, run_dir: Path) -> Path:
    root = root.resolve()
    private = _private_root(root)
    base = (root / DEFAULT_RUN_ROOT).absolute()
    run_dir = run_dir.absolute()
    if (
        base.is_symlink()
        or not base.is_dir()
        or base.resolve(strict=True) != base
        or run_dir.parent != base
        or run_dir.is_symlink()
        or not run_dir.is_dir()
        or run_dir.resolve(strict=True) != run_dir
        or private not in run_dir.parents
    ):
        raise F1LiveError("F1 run directory is unavailable or indirect")
    return run_dir


def _private_target(
    client: d0.AdbReadOnlyClient, result: dict[str, Any]
) -> dict[str, str]:
    serial = client.one_serial()
    topology = client.topology(serial)
    target = result["target_evidence"]["targets"][0]
    if (
        hashlib.sha256(serial.encode()).hexdigest() != target["adb_serial_sha256"]
        or hashlib.sha256(topology.encode()).hexdigest()
        != target["usb_topology_sha256"]
    ):
        raise F1LiveError("post-D0 private target continuity mismatch")
    return {
        "schema": PRIVATE_TARGET_SCHEMA,
        "serial": serial,
        "topology": topology,
    }


def _binding(
    bundle: core.Bundle,
    d0_result: dict[str, Any],
    d0_receipt: dict[str, Any],
    private_receipt: dict[str, Any],
    closure: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    base, base_sha256 = core.approval_binding(
        bundle, d0_result["target_evidence"]
    )
    value = {
        "schema": "device_action_f1_live_approval_binding_v2",
        "adapter_version": ADAPTER_VERSION,
        "base_binding": base,
        "base_binding_sha256": base_sha256,
        "d0_result": d0_receipt,
        "private_target": private_receipt,
        "execution_closure_sha256": closure["sha256"],
        "mandatory_rollback_preapproved": True,
        "recovery_requires_second_approval": False,
    }
    return value, core.json_sha256(value)


def prepare_connected(
    root: Path,
    bundle: core.Bundle,
    run_dir: Path,
    client: d0.AdbReadOnlyClient,
    usb_root: Path = DEFAULT_USB_ROOT,
) -> dict[str, Any]:
    if bundle.manifest["status"] != "ready-for-f1-approval":
        raise F1LiveError("manifest is not ready for F1 approval")
    run_dir = _validate_private_run_dir(root, run_dir)
    preflight = run_dir / "preflight"
    preflight.mkdir(mode=0o700)
    result = d0.collect_connected(bundle, preflight, client, usb_root)
    d0.validate_result(result, bundle, preflight)
    private_target = _private_target(client, result)
    private_path = run_dir / "target-private.json"
    _write_exclusive(private_path, private_target)
    d0_path = preflight / "result.json"
    d0_receipt = _receipt(d0_path, "prepared D0 result")
    private_receipt = _receipt(private_path, "private target")
    closure = _closure(root)
    binding, binding_sha256 = _binding(
        bundle, result, d0_receipt, private_receipt, closure
    )
    prepared = {
        "schema": PREPARED_SCHEMA,
        "adapter_version": ADAPTER_VERSION,
        "manifest_id": bundle.manifest["manifest_id"],
        "bundle_sha256": bundle.sha256,
        "manifest_status": bundle.manifest["status"],
        "d0_result": d0_receipt,
        "private_target": private_receipt,
        "execution_closure": closure,
        "approval_binding": binding,
        "approval_binding_sha256": binding_sha256,
        "approval_token": APPROVAL_PREFIX + binding_sha256,
        "device_contact": True,
        "device_writes": False,
        "reboot_requested": False,
        "odin_invoked": False,
        "partition_transfer": False,
        "f1_authorized": False,
        "live_authorized": False,
    }
    _write_exclusive(run_dir / "prepared.json", prepared)
    return prepared


def load_prepared(root: Path, manifest_path: Path, run_dir: Path) -> PreparedRun:
    root = root.resolve()
    run_dir = _validate_private_run_dir(root, run_dir)
    bundle = core.verify_bundle(root, manifest_path)
    prepared = _read_json(run_dir / "prepared.json", "prepared F1 record")
    expected_keys = {
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
        "device_contact",
        "device_writes",
        "reboot_requested",
        "odin_invoked",
        "partition_transfer",
        "f1_authorized",
        "live_authorized",
    }
    if set(prepared) != expected_keys:
        raise F1LiveError("prepared F1 record shape mismatch")
    if (
        prepared["schema"] != PREPARED_SCHEMA
        or prepared["adapter_version"] != ADAPTER_VERSION
        or prepared["manifest_id"] != bundle.manifest["manifest_id"]
        or prepared["bundle_sha256"] != bundle.sha256
        or prepared["manifest_status"] != "ready-for-f1-approval"
        or bundle.manifest["status"] != "ready-for-f1-approval"
        or prepared["approval_token"]
        != APPROVAL_PREFIX + prepared["approval_binding_sha256"]
        or prepared["device_contact"] is not True
        or any(
            prepared[key] is not False
            for key in (
                "device_writes",
                "reboot_requested",
                "odin_invoked",
                "partition_transfer",
                "f1_authorized",
                "live_authorized",
            )
        )
    ):
        raise F1LiveError("prepared F1 record header mismatch")
    closure = _closure(root)
    if prepared["execution_closure"] != closure:
        raise F1LiveError("execution-critical source closure changed")
    d0_path = run_dir / "preflight/result.json"
    private_path = run_dir / "target-private.json"
    if prepared["d0_result"] != _receipt(d0_path, "prepared D0 result"):
        raise F1LiveError("prepared D0 result identity changed")
    if prepared["private_target"] != _receipt(private_path, "private target"):
        raise F1LiveError("private target identity changed")
    d0_result = _read_json(d0_path, "prepared D0 result")
    d0.validate_result(d0_result, bundle, run_dir / "preflight")
    private_target = _read_json(private_path, "private target")
    if set(private_target) != {"schema", "serial", "topology"} or private_target[
        "schema"
    ] != PRIVATE_TARGET_SCHEMA:
        raise F1LiveError("private target shape mismatch")
    target = d0_result["target_evidence"]["targets"][0]
    if (
        hashlib.sha256(private_target["serial"].encode()).hexdigest()
        != target["adb_serial_sha256"]
        or hashlib.sha256(private_target["topology"].encode()).hexdigest()
        != target["usb_topology_sha256"]
    ):
        raise F1LiveError("private target no longer matches D0 evidence")
    binding, binding_sha256 = _binding(
        bundle,
        d0_result,
        prepared["d0_result"],
        prepared["private_target"],
        closure,
    )
    if (
        prepared["approval_binding"] != binding
        or prepared["approval_binding_sha256"] != binding_sha256
    ):
        raise F1LiveError("prepared approval binding mismatch")
    return PreparedRun(root, run_dir, bundle, prepared, private_target)


def _read_sysfs(path: Path, label: str) -> str | None:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise F1LiveError(f"Download sysfs read failed: {label}") from exc
    if len(payload) > 512:
        raise F1LiveError(f"Download sysfs value is oversized: {label}")
    try:
        return payload.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise F1LiveError(f"Download sysfs value is invalid: {label}") from exc


def validate_download_endpoint(
    device: str,
    topology: str,
    profile: dict[str, Any],
    usb_root: Path = DEFAULT_USB_ROOT,
) -> dict[str, Any]:
    if transport.ODIN_DEVICE_RE.fullmatch(device) is None:
        raise F1LiveError("Download endpoint path is not canonical")
    match = re.fullmatch(r"usb:([0-9]+)-([0-9]+(?:\.[0-9]+)*)", topology)
    if match is None:
        raise F1LiveError("prepared Android USB topology is malformed")
    node_name = f"{match.group(1)}-{match.group(2)}"
    node = usb_root / node_name
    if not node.exists():
        raise F1LiveError("prepared USB topology has no Download sysfs node")
    coordinates = re.fullmatch(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})", device)
    assert coordinates is not None
    download = profile["target"]["download"]
    names = (
        "busnum",
        "devnum",
        "idVendor",
        "idProduct",
        "product",
        "manufacturer",
        "serial",
    )
    values = {
        name: _read_sysfs(node / name, name)
        for name in names
    }
    repeated = {name: _read_sysfs(node / name, name) for name in names}
    if (
        values != repeated
        or values["busnum"] != str(int(coordinates.group(1)))
        or values["devnum"] != str(int(coordinates.group(2)))
        or values["idVendor"] != download["usb_vendor_id"]
        or values["idProduct"] != download["usb_product_id"]
        or values["product"] != download["product"]
        or values["manufacturer"] != download["manufacturer"]
        or values["serial"] not in {None, ""}
    ):
        raise F1LiveError("Download endpoint does not match the prepared target")
    return {
        "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
        "identity": {
            "vendor": values["idVendor"],
            "product_id": values["idProduct"],
            "product": values["product"],
            "manufacturer": values["manufacturer"],
            "serial_absent": True,
        },
    }


def classify_acceptance(payload: bytes, acceptance: dict[str, Any]) -> dict[str, Any]:
    if acceptance.get("kind") == typed_evidence.SAME_RING_KIND:
        try:
            return typed_evidence.classify_same_ring(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.SAME_RING_MULTIBOOT_KIND:
        try:
            return typed_evidence.classify_same_ring_multiboot(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.E1_LATEST_STAGE_KIND:
        try:
            return typed_evidence.classify_e1_latest_stage(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.PID1_USERSPACE_KIND:
        try:
            return typed_evidence.classify_pid1_userspace(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    if acceptance.get("kind") == typed_evidence.CHECKPOINT_KIND:
        try:
            return typed_evidence.classify_checkpoint(payload, acceptance)
        except typed_evidence.EvidenceError as exc:
            raise F1LiveError(str(exc)) from exc
    marker = acceptance["marker"].encode()
    family = acceptance["family"].encode()
    classification = live_core.classify_marker_family(
        payload,
        exact_marker=b"\n" + marker + b"\n",
        family_prefix=family,
    )
    classification["accepted"] = (
        classification["acceptance_present"] is True
        and classification["exact_count"] == acceptance["exact_count"]
        and classification["family_count"] == acceptance["exact_count"]
        and classification["foreign_count"] == 0
        and classification["integrity_issue"] is False
    )
    return classification


def _persist_bytes(path: Path, payload: bytes) -> dict[str, Any]:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o400,
    )
    try:
        if os.write(descriptor, payload) != len(payload):
            raise F1LiveError(f"short evidence write: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    core._fsync_dir(path.parent)
    return _receipt(path, path.name, max(len(payload), 1) + 1)


def _reconcile_transfer_attempts(
    prepared: PreparedRun,
    journal: core.Journal,
    kind: str,
    *,
    repair_orphan_start: bool,
) -> int:
    if kind not in {"candidate", "rollback"}:
        raise F1LiveError("unknown F1 transfer kind")
    action = f"{kind}_transfer_attempt"
    paths = sorted(prepared.run_dir.glob(f"{kind}-attempt-*.start.json"))
    if len(paths) > MAX_ATTEMPTS or any(
        path.name != f"{kind}-attempt-{index:02d}.start.json"
        for index, path in enumerate(paths, 1)
    ):
        raise F1LiveError(f"{kind} transfer evidence sequence is invalid")
    receipts: list[dict[str, Any]] = []
    for index, path in enumerate(paths, 1):
        prefix = f"{kind}-attempt-{index:02d}"
        value = _read_json(path, f"{kind} transfer attempt start")
        if value != {
            "schema": "device_action_f1_transfer_attempt_start_v2",
            "kind": kind,
            "attempt": index,
            "prefix": prefix,
            "approval_binding_sha256": prepared.binding_sha256,
        }:
            raise F1LiveError(f"{kind} transfer attempt start is malformed")
        try:
            receipts.append(_receipt(path, f"{kind} transfer attempt start"))
        except core.F1V2Error as exc:
            raise F1LiveError(f"{kind} transfer attempt start is unavailable") from exc
    checkpoints = [
        record
        for record in journal.records()
        if record["kind"] == "checkpoint" and record["action"] == action
    ]
    if len(checkpoints) > len(paths) or len(paths) - len(checkpoints) > 1:
        raise F1LiveError(f"{kind} transfer attempt ledger is inconsistent")
    for index, record in enumerate(checkpoints, 1):
        if record["details"] != {"attempt": index, "start": receipts[index - 1]}:
            raise F1LiveError(f"{kind} transfer checkpoint does not bind its start")
    if len(paths) == len(checkpoints) + 1:
        if not repair_orphan_start:
            raise F1LiveError(f"{kind} transfer start lacks its checkpoint")
        attempt = len(paths)
        journal.checkpoint(
            action,
            "attempt_started",
            {"attempt": attempt, "start": receipts[-1]},
        )
    return len(paths)


def _begin_transfer_attempt(
    prepared: PreparedRun, journal: core.Journal, kind: str
) -> tuple[int, str, dict[str, Any]]:
    consumed = _reconcile_transfer_attempts(
        prepared, journal, kind, repair_orphan_start=True
    )
    if consumed >= MAX_ATTEMPTS:
        raise F1LiveError(f"{kind} transfer attempt bound exceeded")
    attempt = consumed + 1
    prefix = f"{kind}-attempt-{attempt:02d}"
    value = {
        "schema": "device_action_f1_transfer_attempt_start_v2",
        "kind": kind,
        "attempt": attempt,
        "prefix": prefix,
        "approval_binding_sha256": prepared.binding_sha256,
    }
    path = prepared.run_dir / f"{prefix}.start.json"
    _write_exclusive(path, value)
    start = _receipt(path, f"{kind} transfer attempt start")
    journal.checkpoint(
        f"{kind}_transfer_attempt",
        "attempt_started",
        {"attempt": attempt, "start": start},
    )
    return attempt, prefix, start


def _next_execute_preflight(run_dir: Path) -> Path:
    paths = sorted(run_dir.glob("execute-preflight-*"))
    expected = [
        f"execute-preflight-{index:02d}" for index in range(1, len(paths) + 1)
    ]
    if [path.name for path in paths] != expected or any(
        path.is_symlink() or not path.is_dir() for path in paths
    ):
        raise F1LiveError("execution preflight evidence sequence is invalid")
    if len(paths) >= MAX_ATTEMPTS:
        raise F1LiveError("execution preflight fails-twice bound exceeded")
    return run_dir / f"execute-preflight-{len(paths) + 1:02d}"


class SamsungOdinBackend:
    def __init__(
        self,
        root: Path,
        bundle: core.Bundle,
        adb: Path,
        usb_root: Path = DEFAULT_USB_ROOT,
    ):
        self.root = root.resolve()
        self.bundle = bundle
        self.client = d0.AdbReadOnlyClient(adb)
        self.usb_root = usb_root
        self.odin = core._artifact_path(
            self.root, bundle.profile["transport"]["odin"], "odin"
        )

    def recheck_android(
        self, prepared: PreparedRun, destination: Path
    ) -> dict[str, Any]:
        destination.mkdir(mode=0o700)
        result = d0.collect_connected(
            prepared.bundle, destination, self.client, self.usb_root
        )
        if result["target_evidence"] != _read_json(
            prepared.run_dir / "preflight/result.json", "prepared D0 result"
        )["target_evidence"]:
            raise F1LiveError("execution-time D0 target differs from preparation")
        serial = self.client.one_serial()
        topology = self.client.topology(serial)
        if (
            serial != prepared.private_target["serial"]
            or topology != prepared.private_target["topology"]
        ):
            raise F1LiveError("execution-time private target continuity changed")
        return {
            "d0_result_sha256": _receipt(
                destination / "result.json", "execution D0 result"
            )["sha256"],
            "target_evidence_sha256": core.json_sha256(result["target_evidence"]),
            "healthy": True,
        }

    def request_download(self, prepared: PreparedRun) -> None:
        result = d0.bounded_command(
            [
                str(self.client.adb),
                "-s",
                prepared.private_target["serial"],
                "reboot",
                "download",
            ],
            timeout=20,
        )
        if result.returncode != 0 or result.stderr:
            raise F1LiveError("Android Download request failed")

    def endpoint_session(self, run_dir: Path) -> ContextManager[Any]:
        return odin_core.transaction_session(run_dir)

    def wait_download(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        timeout_sec: float,
    ) -> Endpoint:
        sequence = len(odin_core.list_snapshot_receipts(run_dir))
        result = odin_core.wait_for_single_live_endpoint(
            self.odin,
            run_dir,
            timeout_sec=timeout_sec,
            lease=lease,
            sequence_start=sequence,
            poll_sec=0.5,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
        )
        if result.timed_out or result.ticket is None:
            raise F1LiveError("bounded wait for Download endpoint expired")
        identity = validate_download_endpoint(
            result.ticket.device,
            prepared.private_target["topology"],
            prepared.bundle.profile,
            self.usb_root,
        )
        revalidated = odin_core.revalidate_endpoint_ticket(
            self.odin,
            run_dir,
            result.ticket,
            sequence=result.next_sequence,
            lease=lease,
            timeout_sec=ENDPOINT_REVALIDATE_SEC,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
        )
        return Endpoint(
            result.ticket.device,
            result.next_sequence + 1,
            hashlib.sha256(
                (identity["endpoint_sha256"] + revalidated["device_identity"]).encode()
            ).hexdigest(),
        )

    def transfer(
        self,
        prepared: PreparedRun,
        endpoint: Endpoint,
        kind: str,
        destination: Path,
        attempt: int,
        prefix: str,
    ) -> TransferOutcome:
        if kind not in {"candidate", "rollback"}:
            raise F1LiveError("unknown F1 transfer kind")
        item = (
            prepared.bundle.manifest["candidate_ap"]
            if kind == "candidate"
            else prepared.bundle.manifest["rollback_ap"]
        )
        journal = core.Journal.reopen(
            prepared.run_dir / "transaction", prepared.binding_sha256
        )
        consumed = _reconcile_transfer_attempts(
            prepared, journal, kind, repair_orphan_start=False
        )
        start = _read_json(
            prepared.run_dir / f"{prefix}.start.json",
            f"{kind} transfer attempt start",
        )
        if (
            consumed != attempt
            or prefix != f"{kind}-attempt-{attempt:02d}"
            or start.get("attempt") != attempt
            or start.get("kind") != kind
            or start.get("approval_binding_sha256") != prepared.binding_sha256
        ):
            raise F1LiveError(f"{kind} transfer attempt is not durably armed")
        ap = core._artifact_path(self.root, item, f"{kind}_ap")
        odin = prepared.bundle.profile["transport"]["odin"]
        try:
            receipt, stdout, stderr = transport.execute_odin_boot_only(
                self.odin,
                ap,
                endpoint.device,
                odin_size=odin["size"],
                odin_sha256=odin["sha256"],
                ap_size=item["size"],
                ap_sha256=item["sha256"],
                label=kind,
                require_deterministic_metadata=kind == "candidate",
                timeout=ODIN_TIMEOUT_SEC,
                maximum_output=MAX_ODIN_OUTPUT,
            )
        except (transport.F1TransportError, subprocess.SubprocessError, OSError) as exc:
            failure = {
                "schema": "device_action_f1_transfer_failure_v2",
                "kind": kind,
                "attempt": attempt,
                "prefix": prefix,
                "possible_device_session": True,
                "error_type": type(exc).__name__,
            }
            _write_exclusive(destination / f"{prefix}.result.json", failure)
            return TransferOutcome(
                "odin_device_session_failure_or_unknown", False, True, failure
            )
        stdout_receipt = _persist_bytes(destination / f"{prefix}.stdout", stdout)
        stderr_receipt = _persist_bytes(destination / f"{prefix}.stderr", stderr)
        classification = core.classify_odin_output(
            int(receipt["returncode"]), stdout, stderr
        )
        value = {
            "schema": "device_action_f1_transfer_receipt_v2",
            "kind": kind,
            "attempt": attempt,
            "prefix": prefix,
            "classification": classification,
            "transport": receipt,
            "stdout": stdout_receipt,
            "stderr": stderr_receipt,
        }
        _write_exclusive(destination / f"{prefix}.result.json", value)
        return TransferOutcome(
            classification,
            classification == "odin_transfer_completed",
            classification != "odin_local_parse_failure",
            value,
        )

    def observe_candidate(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
    ) -> dict[str, Any]:
        sequence = len(odin_core.list_snapshot_receipts(run_dir))
        absent = odin_core.wait_for_no_live_endpoint(
            self.odin,
            run_dir,
            timeout_sec=DISCONNECT_WAIT_SEC,
            lease=lease,
            sequence_start=sequence,
            poll_sec=0.5,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
            allow_live_departure=True,
        )
        timeout = prepared.bundle.manifest["observation"]["timeout_sec"]
        started = time.monotonic()
        if absent.absent:
            time.sleep(timeout)
        return {
            "bounded": True,
            "download_endpoint_absent": absent.absent,
            "absence_timed_out": absent.timed_out,
            "requested_sec": timeout,
            "elapsed_sec": round(time.monotonic() - started, 6),
            "candidate_execution_proven": False,
        }

    def _wait_final_health(self, prepared: PreparedRun) -> tuple[str, dict[str, Any]]:
        deadline = time.monotonic() + ANDROID_WAIT_SEC
        last_error = "final Android not observed"
        while time.monotonic() < deadline:
            try:
                snapshot = d0.usb_snapshot(
                    self.usb_root, prepared.bundle.profile["target"]["download"]
                )
                if snapshot["download_endpoint_count"]:
                    raise F1LiveError("Download endpoint remains during final health")
                serial = self.client.one_serial()
                topology = self.client.topology(serial)
                if (
                    serial != prepared.private_target["serial"]
                    or topology != prepared.private_target["topology"]
                ):
                    raise F1LiveError("final target continuity mismatch")
                properties = self.client.properties(serial)
                root_health = self.client.root_health(serial)
                health = d0.validate_health(
                    prepared.bundle,
                    properties,
                    root_health,
                    True,
                    "final_health",
                )
                return serial, health
            except (d0.D0Error, F1LiveError, OSError) as exc:
                last_error = str(exc)
                time.sleep(2)
        raise F1LiveError(f"final Android health wait expired: {last_error}")

    def verify_final(
        self,
        prepared: PreparedRun,
        run_dir: Path,
        lease: Any,
        destination: Path,
    ) -> dict[str, Any]:
        sequence = len(odin_core.list_snapshot_receipts(run_dir))
        absent = odin_core.wait_for_no_live_endpoint(
            self.odin,
            run_dir,
            timeout_sec=DISCONNECT_WAIT_SEC,
            lease=lease,
            sequence_start=sequence,
            poll_sec=0.5,
            endpoint_observer_factory=odin_core.measured_usbfs_observer,
            allow_live_departure=True,
        )
        if not absent.absent:
            raise F1LiveError("rollback Odin endpoint did not disappear")
        serial, health = self._wait_final_health(prepared)
        acceptance = prepared.bundle.manifest["observation"]["acceptance"]
        payloads: list[bytes] = []
        receipts: list[dict[str, Any]] = []
        for index in (1, 2):
            path = destination / f"rollback-observer-{index}.bin"
            receipt = self.client.capture(serial, acceptance["source"], path)
            payload = d0._read_stable(path, MAX_OBSERVER_BYTES)
            stderr = d0._read_stable(
                path.with_suffix(path.suffix + ".stderr"), d0.MAX_TEXT_OUTPUT
            )
            if stderr:
                raise F1LiveError("rollback observer produced stderr")
            payloads.append(payload)
            receipts.append(receipt)
            time.sleep(0.25)
        if not payloads[0] or payloads[0] != payloads[1]:
            raise F1LiveError("rollback observer reads are not stable and identical")
        final_serial = self.client.one_serial()
        final_topology = self.client.topology(final_serial)
        if (
            final_serial != serial
            or final_serial != prepared.private_target["serial"]
            or final_topology != prepared.private_target["topology"]
        ):
            raise F1LiveError("final target changed during observer collection")
        marker_result = classify_acceptance(payloads[0], acceptance)
        accepted = marker_result["accepted"] is True
        return {
            "health": health,
            "target_evidence_sha256": core.json_sha256(
                {
                    "serial": hashlib.sha256(serial.encode()).hexdigest(),
                    "topology": hashlib.sha256(
                        prepared.private_target["topology"].encode()
                    ).hexdigest(),
                }
            ),
            "observer": {
                "reads": receipts,
                "byte_identical": True,
                "bytes": len(payloads[0]),
                "sha256": hashlib.sha256(payloads[0]).hexdigest(),
                "exact_marker_count": marker_result["exact_count"],
                "marker_family_count": marker_result["family_count"],
                "classification": marker_result,
                "accepted": accepted,
            },
            "rollback_verified": True,
        }


def _live_state_path(prepared: PreparedRun) -> Path:
    return prepared.run_dir / "live-state.json"


def _state(prepared: PreparedRun) -> dict[str, Any]:
    path = _live_state_path(prepared)
    if not path.exists():
        return {
            "schema": LIVE_STATE_SCHEMA,
            "candidate_classification": "not-attempted",
            "candidate_completed": False,
            "rollback_completed": False,
            "final_verified": False,
        }
    value = _read_json(path, "F1 live state")
    if value.get("schema") != LIVE_STATE_SCHEMA:
        raise F1LiveError("F1 live state schema mismatch")
    return value


def _save_state(prepared: PreparedRun, value: dict[str, Any]) -> None:
    value = {**value, "schema": LIVE_STATE_SCHEMA}
    _write_atomic(_live_state_path(prepared), value)


def _result(
    prepared: PreparedRun,
    journal: core.Journal,
    verdict: str,
    outcome: str,
    recovery_required: bool,
) -> dict[str, Any]:
    value = {
        "schema": LIVE_RESULT_SCHEMA,
        "adapter_version": ADAPTER_VERSION,
        "manifest_id": prepared.bundle.manifest["manifest_id"],
        "bundle_sha256": prepared.bundle.sha256,
        "approval_binding_sha256": prepared.binding_sha256,
        "journal": journal.receipt(),
        "current_state": journal.state(),
        "timeline": core.timeline(journal.records()),
        "live_state": _state(prepared),
        "verdict": verdict,
        "outcome_class": outcome,
        "recovery_required": recovery_required,
    }
    validate_live_result(value, prepared)
    _write_atomic(prepared.run_dir / "live-result.json", value)
    return value


def _validate_transfer_result(
    prepared: PreparedRun, kind: str, attempt: int
) -> dict[str, Any] | None:
    prefix = f"{kind}-attempt-{attempt:02d}"
    result_path = prepared.run_dir / f"{prefix}.result.json"
    if not result_path.exists():
        return None
    value = _read_json(result_path, f"{kind} transfer receipt")
    if value.get("schema") == "device_action_f1_transfer_failure_v2":
        if set(value) != {
            "schema",
            "kind",
            "attempt",
            "prefix",
            "possible_device_session",
            "error_type",
        } or (
            value["kind"] != kind
            or value["attempt"] != attempt
            or value["prefix"] != prefix
            or value["possible_device_session"] is not True
            or not isinstance(value["error_type"], str)
            or not value["error_type"]
        ):
            raise F1LiveError(f"{kind} transfer failure evidence is malformed")
        return {**value, "classification": "odin_device_session_failure_or_unknown"}
    if (
        value.get("schema") != "device_action_f1_transfer_receipt_v2"
        or value.get("kind") != kind
        or value.get("attempt") != attempt
        or value.get("prefix") != prefix
        or value.get("classification")
        not in {
            "odin_local_parse_failure",
            "odin_transfer_completed",
            "odin_device_session_failure_or_unknown",
        }
        or not isinstance(value.get("stdout"), dict)
        or not isinstance(value.get("stderr"), dict)
    ):
        raise F1LiveError(f"{kind} transfer evidence is malformed")
    for stream in ("stdout", "stderr"):
        path = prepared.run_dir / f"{prefix}.{stream}"
        if value[stream] != _receipt(
            path,
            f"{kind} {stream}",
            MAX_ODIN_OUTPUT,
        ):
            raise F1LiveError(f"{kind} {stream} evidence changed")
    return value


def _validate_transfer_evidence(prepared: PreparedRun, kind: str) -> dict[str, Any]:
    journal = core.Journal.reopen(
        prepared.run_dir / "transaction", prepared.binding_sha256
    )
    count = _reconcile_transfer_attempts(
        prepared, journal, kind, repair_orphan_start=False
    )
    if not count:
        raise F1LiveError(f"{kind} transfer evidence count is invalid")
    last: dict[str, Any] | None = None
    for index in range(1, count + 1):
        result = _validate_transfer_result(prepared, kind, index)
        if index == count:
            last = result
    if last is None:
        attempt = count
        return {
            "schema": "device_action_f1_transfer_interrupted_v2",
            "kind": kind,
            "attempt": attempt,
            "prefix": f"{kind}-attempt-{attempt:02d}",
            "classification": "odin_device_session_failure_or_unknown",
        }
    return last


def _validate_final_observer(prepared: PreparedRun, state: dict[str, Any]) -> None:
    evidence = state.get("final_evidence")
    if not isinstance(evidence, dict) or evidence.get("rollback_verified") is not True:
        raise F1LiveError("final evidence is missing rollback verification")
    observer = evidence.get("observer")
    if not isinstance(observer, dict) or observer.get("byte_identical") is not True:
        raise F1LiveError("final observer evidence is malformed")
    health = evidence.get("health")
    expected_health = prepared.bundle.profile["final_health"]
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
        or health.get("verified_boot_state")
        != expected_health["verified_boot_state"]
        or health.get("root_verified") is not True
        or health.get("boot_sha256") != expected_health["boot_sha256"]
        or health.get("supporting_partition_sha256")
        != expected_health["supporting_partition_sha256"]
        or health.get("odin_endpoint_absent") is not True
        or not isinstance(health.get("kernel_release"), str)
        or not health.get("kernel_release")
        or re.fullmatch(r"[0-9a-f]{64}", str(health.get("boot_id_sha256")))
        is None
    ):
        raise F1LiveError("final health evidence does not match the profile")
    expected_target = core.json_sha256(
        {
            "serial": hashlib.sha256(
                prepared.private_target["serial"].encode()
            ).hexdigest(),
            "topology": hashlib.sha256(
                prepared.private_target["topology"].encode()
            ).hexdigest(),
        }
    )
    if evidence.get("target_evidence_sha256") != expected_target:
        raise F1LiveError("final target continuity evidence mismatch")
    payloads: list[bytes] = []
    for index, receipt in enumerate(observer.get("reads", []), 1):
        if index > 2 or not isinstance(receipt, dict):
            raise F1LiveError("final observer receipt count is invalid")
        path = prepared.run_dir / f"rollback-observer-{index}.bin"
        payload = d0._read_stable(path, MAX_OBSERVER_BYTES)
        stderr = d0._read_stable(
            path.with_suffix(path.suffix + ".stderr"), d0.MAX_TEXT_OUTPUT
        )
        if (
            stderr
            or receipt.get("path") != str(path)
            or receipt.get("bytes") != len(payload)
            or receipt.get("sha256") != hashlib.sha256(payload).hexdigest()
            or receipt.get("read_to_eof") is not True
            or receipt.get("stderr_bytes") != 0
        ):
            raise F1LiveError("final observer raw evidence changed")
        payloads.append(payload)
    if len(payloads) != 2 or not payloads[0] or payloads[0] != payloads[1]:
        raise F1LiveError("final observer raw reads are not identical")
    acceptance = prepared.bundle.manifest["observation"]["acceptance"]
    marker_result = classify_acceptance(payloads[0], acceptance)
    exact = marker_result["exact_count"]
    family = marker_result["family_count"]
    accepted = marker_result["accepted"] is True
    if (
        observer.get("bytes") != len(payloads[0])
        or observer.get("sha256") != hashlib.sha256(payloads[0]).hexdigest()
        or observer.get("exact_marker_count") != exact
        or observer.get("marker_family_count") != family
        or observer.get("classification") != marker_result
        or observer.get("accepted") is not accepted
        or state.get("marker_accepted") is not accepted
    ):
        raise F1LiveError("final observer semantics mismatch")


def validate_live_result(
    result: dict[str, Any], prepared: PreparedRun
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "adapter_version",
        "manifest_id",
        "bundle_sha256",
        "approval_binding_sha256",
        "journal",
        "current_state",
        "timeline",
        "live_state",
        "verdict",
        "outcome_class",
        "recovery_required",
    }
    if set(result) != expected_keys:
        raise F1LiveError("live result shape mismatch")
    journal = core.Journal.reopen(
        prepared.run_dir / "transaction", prepared.binding_sha256
    )
    state = _state(prepared)
    if (
        result["schema"] != LIVE_RESULT_SCHEMA
        or result["adapter_version"] != ADAPTER_VERSION
        or result["manifest_id"] != prepared.bundle.manifest["manifest_id"]
        or result["bundle_sha256"] != prepared.bundle.sha256
        or result["approval_binding_sha256"] != prepared.binding_sha256
        or result["journal"] != journal.receipt()
        or result["current_state"] != journal.state()
        or result["timeline"] != core.timeline(journal.records())
        or result["live_state"] != state
    ):
        raise F1LiveError("live result does not reopen against durable state")
    candidate_classification = state.get("candidate_classification")
    if candidate_classification not in {
        "not-attempted",
        "odin_local_parse_failure",
        "odin_transfer_completed",
        "odin_device_session_failure_or_unknown",
    }:
        raise F1LiveError("live candidate classification is invalid")
    if candidate_classification != "not-attempted":
        evidence = _validate_transfer_evidence(prepared, "candidate")
        if evidence["classification"] != candidate_classification:
            raise F1LiveError("candidate transfer classification mismatch")
    if state.get("candidate_completed") is not (
        candidate_classification == "odin_transfer_completed"
    ):
        raise F1LiveError("candidate completion semantics mismatch")
    rollback_classification = state.get("rollback_classification")
    if rollback_classification is not None:
        rollback = _validate_transfer_evidence(prepared, "rollback")
        if rollback["classification"] != rollback_classification:
            raise F1LiveError("rollback transfer classification mismatch")
    if state.get("rollback_completed") is not (
        rollback_classification == "odin_transfer_completed"
    ):
        raise F1LiveError("rollback completion semantics mismatch")
    if state.get("final_verified") is True:
        if state.get("rollback_completed") is not True:
            raise F1LiveError("final verification precedes completed rollback")
        _validate_final_observer(prepared, state)
    verdict = result["verdict"]
    names = [event["name"] for event in result["timeline"]["events"]]
    if verdict == "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK":
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("candidate_completed") is not True
            or state.get("rollback_completed") is not True
            or state.get("final_verified") is not True
            or state.get("marker_accepted") is not True
            or result["recovery_required"] is not False
        ):
            raise F1LiveError("F1 PASS semantics are incomplete")
    elif verdict == "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK":
        if (
            journal.state() != "CLOSED"
            or names != list(core.TIMELINE)
            or state.get("rollback_completed") is not True
            or state.get("final_verified") is not True
            or result["recovery_required"] is not False
            or (
                state.get("candidate_completed") is True
                and state.get("marker_accepted") is True
            )
        ):
            raise F1LiveError("F1 no-proof semantics are incomplete")
    elif verdict == "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED":
        if journal.state() != "RECOVERY_DOWNLOAD" or result[
            "recovery_required"
        ] is not True:
            raise F1LiveError("F1 recovery-required semantics are invalid")
    elif verdict in {
        "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION",
        "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
    }:
        if journal.state() != "ABORTED" or result["recovery_required"] is not False:
            raise F1LiveError("F1 pre-candidate abort semantics are invalid")
    else:
        raise F1LiveError("unknown F1 live verdict")
    return result


def _events(journal: core.Journal) -> list[str]:
    return [
        item["action"] for item in journal.records() if item["kind"] == "event"
    ]


def _normalize_recovery(prepared: PreparedRun, journal: core.Journal) -> bool:
    attempt_count = _reconcile_transfer_attempts(
        prepared, journal, "candidate", repair_orphan_start=True
    )
    events = _events(journal)
    if not attempt_count:
        if "candidate_flash_start" in events:
            raise F1LiveError("candidate event exists without an attempt ledger")
        return False
    if "candidate_flash_start" not in events:
        if journal.state() != "DOWNLOAD_IDENTIFIED":
            raise F1LiveError("candidate attempt lacks its timeline start")
        journal.event(
            "candidate_flash_start", {"attempt": attempt_count, "resumed": True}
        )
    current = _state(prepared)
    if current.get("candidate_classification") == "not-attempted":
        current.update(
            {
                "candidate_classification": "odin_device_session_failure_or_unknown",
                "candidate_completed": False,
            }
        )
        _save_state(prepared, current)
    state = journal.state()
    if state == "DOWNLOAD_IDENTIFIED":
        journal.transition(
            "CANDIDATE_FLASHED",
            "interrupted_candidate_outcome_unknown",
            {"partition_transfer_possible": True, "proof": False},
        )
        journal.event("candidate_flash_done", {"proof": False, "resumed": True})
        state = "CANDIDATE_FLASHED"
    if state == "CANDIDATE_FLASHED":
        if "candidate_flash_done" not in _events(journal):
            journal.event("candidate_flash_done", {"proof": False, "resumed": True})
        journal.transition(
            "OBSERVED", "interrupted_candidate_no_proof", {"proof": False}
        )
        journal.event("candidate_boot_ready", {"proof": False, "resumed": True})
        state = "OBSERVED"
    if state == "OBSERVED" and "candidate_boot_ready" not in _events(journal):
        journal.event("candidate_boot_ready", {"proof": False, "resumed": True})
    return True


def _finish_rollback(
    prepared: PreparedRun,
    backend: LiveBackend,
    journal: core.Journal,
    endpoint_dir: Path,
    lease: Any,
) -> dict[str, Any]:
    state = journal.state()
    rollback_endpoint: Endpoint | None = None
    if state == "OBSERVED":
        print(
            "Candidate observation is closed. Enter physical Download mode for "
            "the preapproved exact Magisk rollback.",
            file=os.sys.stderr,
            flush=True,
        )
        rollback_endpoint = backend.wait_download(
            prepared, endpoint_dir, lease, ROLLBACK_WAIT_SEC
        )
        journal.transition(
            "RECOVERY_DOWNLOAD",
            "rollback_endpoint_identified",
            {"endpoint_identity_sha256": rollback_endpoint.identity_sha256},
        )
        journal.event("rollback_flash_start", {"preapproved": True})
        state = "RECOVERY_DOWNLOAD"
    if state == "RECOVERY_DOWNLOAD":
        if "rollback_flash_start" not in _events(journal):
            journal.event("rollback_flash_start", {"preapproved": True, "resumed": True})
        consumed = _reconcile_transfer_attempts(
            prepared, journal, "rollback", repair_orphan_start=True
        )
        durable = (
            _validate_transfer_result(prepared, "rollback", consumed)
            if consumed
            else None
        )
        durable_completed = (
            durable is not None
            and durable.get("classification") == "odin_transfer_completed"
        )
        if durable_completed:
            current = _state(prepared)
            current.update(
                {
                    "rollback_classification": "odin_transfer_completed",
                    "rollback_completed": True,
                }
            )
            _save_state(prepared, current)
            journal.transition(
                "ROLLBACK_FLASHED",
                "rollback_transfer_completed",
                {"exact": True, "resumed_from_durable_result": True},
            )
            state = "ROLLBACK_FLASHED"
        else:
            if consumed >= MAX_ATTEMPTS:
                raise F1LiveError("rollback transfer attempt bound exceeded")
            endpoint = rollback_endpoint or backend.wait_download(
                prepared, endpoint_dir, lease, ROLLBACK_WAIT_SEC
            )
            attempt, prefix, _start = _begin_transfer_attempt(
                prepared, journal, "rollback"
            )
            rollback = backend.transfer(
                prepared,
                endpoint,
                "rollback",
                prepared.run_dir,
                attempt,
                prefix,
            )
            current = _state(prepared)
            current.update(
                {
                    "rollback_classification": rollback.classification,
                    "rollback_completed": rollback.completed,
                }
            )
            _save_state(prepared, current)
            if not rollback.completed:
                return _result(
                    prepared,
                    journal,
                    "RECOVERY_REQUIRED_F1_V2_ROLLBACK_NOT_VERIFIED",
                    "rollback_transfer_failed_or_unknown",
                    True,
                )
            journal.transition(
                "ROLLBACK_FLASHED", "rollback_transfer_completed", {"exact": True}
            )
            state = "ROLLBACK_FLASHED"
    if state == "ROLLBACK_FLASHED":
        if "rollback_flash_done" not in _events(journal):
            journal.event("rollback_flash_done", {"exact": True, "resumed": True})
        final = backend.verify_final(
            prepared, endpoint_dir, lease, prepared.run_dir
        )
        current = _state(prepared)
        current.update(
            {
                "final_verified": True,
                "marker_accepted": final["observer"]["accepted"],
                "final_evidence": final,
            }
        )
        _save_state(prepared, current)
        journal.transition(
            "HEALTH_VERIFIED",
            "final_health_and_rollback_verified",
            {"marker_accepted": final["observer"]["accepted"]},
        )
        journal.event("rollback_boot_ready", {"healthy": True})
        journal.event("live_session_end", {"rollback_verified": True})
        state = "HEALTH_VERIFIED"
    if state == "HEALTH_VERIFIED":
        events = _events(journal)
        if "rollback_boot_ready" not in events:
            journal.event("rollback_boot_ready", {"healthy": True, "resumed": True})
            events = _events(journal)
        if "live_session_end" not in events:
            journal.event(
                "live_session_end", {"rollback_verified": True, "resumed": True}
            )
        current = _state(prepared)
        marker = current.get("marker_accepted") is True
        candidate = current.get("candidate_completed") is True
        journal.transition("CLOSED", "run_complete", {"marker_accepted": marker})
        if marker and candidate:
            return _result(
                prepared,
                journal,
                "PASS_F1_V2_CANDIDATE_PROVEN_AND_ROLLED_BACK",
                "candidate_proven_rollback_verified",
                False,
            )
        return _result(
            prepared,
            journal,
            "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
            "candidate_not_proven_rollback_verified",
            False,
        )
    raise F1LiveError(f"unsupported rollback resume state: {state}")


def _execute_prepared_locked(
    prepared: PreparedRun,
    approval: str,
    backend: LiveBackend,
) -> dict[str, Any]:
    if approval != prepared.approval_token:
        raise F1LiveError("fresh F1 approval token mismatch")
    transaction = prepared.run_dir / "transaction"
    if transaction.exists() or transaction.is_symlink():
        raise F1LiveError("prepared run already has a transaction; use recovery")
    recheck = backend.recheck_android(
        prepared, _next_execute_preflight(prepared.run_dir)
    )
    journal = core.Journal.create(
        transaction,
        prepared.binding_sha256,
        {"host_only": False, "device_contact": True, "device_writes": False},
    )
    journal.event("live_session_start", {"prepared_recheck": recheck})
    journal.transition(
        "APPROVED",
        "fresh_exact_binding",
        {
            "approval_binding_sha256": prepared.binding_sha256,
            "rollback_preapproved": True,
        },
    )
    endpoint_dir = prepared.run_dir / "odin-endpoints"
    try:
        backend.request_download(prepared)
    except Exception as exc:
        journal.transition(
            "ABORTED",
            "download_request_failed_before_candidate",
            {"error_type": type(exc).__name__, "candidate_attempted": False},
        )
        return _result(
            prepared,
            journal,
            "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
            "download_request_failed_before_candidate",
            False,
        )
    with backend.endpoint_session(endpoint_dir) as lease:
        try:
            endpoint = backend.wait_download(
                prepared, endpoint_dir, lease, DOWNLOAD_WAIT_SEC
            )
        except Exception as exc:
            journal.transition(
                "ABORTED",
                "download_endpoint_unavailable_before_candidate",
                {"error_type": type(exc).__name__, "candidate_attempted": False},
            )
            return _result(
                prepared,
                journal,
                "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
                "download_endpoint_unavailable_before_candidate",
                False,
            )
        journal.transition(
            "DOWNLOAD_IDENTIFIED",
            "candidate_endpoint_identified",
            {"endpoint_identity_sha256": endpoint.identity_sha256},
        )
        attempt, prefix, _start = _begin_transfer_attempt(
            prepared, journal, "candidate"
        )
        journal.event("candidate_flash_start", {"attempt": attempt})
        candidate = backend.transfer(
            prepared,
            endpoint,
            "candidate",
            prepared.run_dir,
            attempt,
            prefix,
        )
        _save_state(
            prepared,
            {
                "candidate_classification": candidate.classification,
                "candidate_completed": candidate.completed,
                "rollback_completed": False,
                "final_verified": False,
            },
        )
        if candidate.classification == "odin_local_parse_failure":
            journal.transition(
                "ABORTED",
                "odin_local_parse_failure",
                {"device_session_started": False, "partition_transfer": False},
            )
            return _result(
                prepared,
                journal,
                "FAIL_F1_V2_ODIN_LOCAL_PARSE_NO_DEVICE_SESSION",
                "odin_local_parse_failure",
                False,
            )
        journal.transition(
            "CANDIDATE_FLASHED",
            candidate.classification,
            {
                "completed": candidate.completed,
                "possible_device_session": candidate.possible_device_session,
            },
        )
        journal.event(
            "candidate_flash_done", {"completed": candidate.completed}
        )
        observation = backend.observe_candidate(prepared, endpoint_dir, lease)
        journal.transition(
            "OBSERVED",
            "bounded_candidate_observation_closed",
            observation,
        )
        journal.event(
            "candidate_boot_ready",
            {
                "proof": candidate.completed
                and observation.get("download_endpoint_absent") is True
            },
        )
        return _finish_rollback(prepared, backend, journal, endpoint_dir, lease)


def execute_prepared(
    prepared: PreparedRun,
    approval: str,
    backend: LiveBackend,
) -> dict[str, Any]:
    with odin_core.transaction_session(prepared.run_dir / "f1-session"):
        return _execute_prepared_locked(prepared, approval, backend)


def _recover_prepared_locked(
    prepared: PreparedRun,
    backend: LiveBackend,
) -> dict[str, Any]:
    transaction = prepared.run_dir / "transaction"
    if not transaction.is_dir() or transaction.is_symlink():
        raise F1LiveError("recovery has no approved transaction")
    journal = core.Journal.reopen(transaction, prepared.binding_sha256)
    if journal.state() in {"CLOSED", "ABORTED"}:
        raise F1LiveError("transaction is not recoverable")
    if not _normalize_recovery(prepared, journal):
        journal.transition(
            "ABORTED",
            "interrupted_before_candidate_attempt",
            {"candidate_attempted": False, "partition_transfer": False},
        )
        return _result(
            prepared,
            journal,
            "FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD",
            "interrupted_before_candidate_attempt",
            False,
        )
    endpoint_dir = prepared.run_dir / "odin-endpoints"
    with backend.endpoint_session(endpoint_dir) as lease:
        return _finish_rollback(prepared, backend, journal, endpoint_dir, lease)


def recover_prepared(
    prepared: PreparedRun,
    backend: LiveBackend,
) -> dict[str, Any]:
    with odin_core.transaction_session(prepared.run_dir / "f1-session"):
        return _recover_prepared_locked(prepared, backend)


def render_plan(root: Path, bundle: core.Bundle) -> dict[str, Any]:
    return {
        "schema": "device_action_f1_live_plan_v2",
        "adapter_version": ADAPTER_VERSION,
        "manifest_id": bundle.manifest["manifest_id"],
        "manifest_status": bundle.manifest["status"],
        "bundle_sha256": bundle.sha256,
        "execution_closure": _closure(root),
        "commands": ["validate", "render-plan", "prepare", "execute", "recover"],
        "prepare_is_d0_only": True,
        "execute_requires_fresh_exact_approval": True,
        "rollback_preapproved": True,
        "recover_can_transfer_candidate": False,
        "device_contact": False,
        "device_writes": False,
        "f1_authorized": False,
        "live_authorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--recover", action="store_true")
    parser.add_argument("--manifest", type=Path, default=core.DEFAULT_MANIFEST)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--adb", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = core.repo_root()
    try:
        bundle = core.verify_bundle(root, args.manifest)
        if args.validate or args.render_plan:
            result = render_plan(root, bundle)
            if args.validate:
                result = {
                    **result,
                    "schema": "device_action_f1_live_offline_check_v2",
                    "verdict": "PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY",
                }
        elif args.prepare:
            if bundle.manifest["status"] != "ready-for-f1-approval":
                raise F1LiveError("manifest is not ready for F1 preparation")
            run_dir = allocate_run_dir(root, args.run_dir)
            adb = args.adb or d0.default_adb()
            result = prepare_connected(
                root, bundle, run_dir, d0.AdbReadOnlyClient(adb)
            )
            result = {**result, "run_dir": str(run_dir)}
        else:
            if args.run_dir is None:
                raise F1LiveError("execute/recover requires --run-dir")
            if args.recover and args.approval is not None:
                raise F1LiveError("recovery must not require a second approval")
            prepared = load_prepared(root, args.manifest, args.run_dir)
            adb = args.adb or d0.default_adb()
            backend = SamsungOdinBackend(root, bundle, adb)
            if args.execute:
                if not args.approval:
                    raise F1LiveError("execute requires --approval")
                result = execute_prepared(prepared, args.approval, backend)
            else:
                result = recover_prepared(prepared, backend)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (
        F1LiveError,
        core.F1V2Error,
        core.F1TransportError,
        d0.D0Error,
        odin_core.OdinTransitionError,
        usbfs_identity.UsbfsIdentityError,
        live_core.LiveCoreError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"Device Action F1 live v2 error: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
