#!/usr/bin/env python3
"""Fixed production backend for the A90 candidate-return continuation.

This module contains the reviewed contact boundary only.  It has no caller
supplied command, serial, endpoint, reboot, or outcome.  Tests inject a fake
``CommandRunner``; the default runner is the existing bounded HostRunner and
uses only the fixed repository tools.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_f1_candidate_return_backend_v1.py"
)
OWNER_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_boot_only_f1_minimal_v1.py"
)
ADAPTER_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_boot_only_f1_adapter_v1.py"
)
FIXED_PYTHON = Path("/usr/bin/python3.14")
ADB = Path("/usr/bin/adb")
LSUSB = Path("/usr/bin/lsusb")
FIXED_SERIAL = "/dev/serial/by-id/usb-A90-LNX_A90_Linux_ARM64_A90NATIVE001-if00"
MAX_TIMEOUT_SEC = 300
USB_LINE_RE = re.compile(
    rb"^Bus [0-9]{3} Device [0-9]{3}: ID "
    rb"(?P<vendor>[0-9a-f]{4}):(?P<product>[0-9a-f]{4}) (?P<description>.+)$"
)
ADB_SERIAL_RE = re.compile(r"^[!-~]{1,256}$")
ADB_ATTRIBUTE_RE = re.compile(r"^(?:usb|product|model|device|transport_id):[!-~]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
A90_VENDOR = "04e8"
A90_NATIVE_PRODUCT = "6861"
A90_RECOVERY_PRODUCT = "6860"
ADB_STATES = {"device", "recovery", "offline", "unauthorized", "no permissions"}
ADB_ROLE_NATIVE = "NATIVE_NO_RECOVERY"
ADB_ROLE_RECOVERY = "BOUND_RECOVERY_PRESENT"
ADB_ROLE_AMBIGUOUS = "AMBIGUOUS"

STATE_NATIVE_VISIBLE = "NATIVE_CANDIDATE_VISIBLE"
STATE_TWRP_PRESENT = "TWRP_BOUND_PRESENT"
STATE_ATTRIBUTABLE_FAILURE = "ATTRIBUTABLE_FAILURE"
STATE_TWRP_AFTER_PHYSICAL = "TWRP_RETURNED_AFTER_PHYSICAL"
STATE_AMBIGUOUS = "AMBIGUOUS"
STATE_FOREIGN = "FOREIGN_ENDPOINT"
STATE_OBSERVER_FAILURE = "OBSERVER_FAILURE"

TWRP_VERSION = "3.7.0_12-0"
TWRP_SCRIPT_SHA256 = (
    "3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07"
)
TWRP_IDENTITY = {
    "version": TWRP_VERSION,
    "scriptPath": "/system/bin/rebootsystem.sh",
    "scriptSize": 89,
    "scriptSha256": TWRP_SCRIPT_SHA256,
    "scriptMode": 493,
    "scriptUid": 0,
    "scriptGid": 0,
    "scriptNlink": 1,
}
TWRP_IDENTITY_COMMAND = (
    "test \"$(twrp --version)\" = '3.7.0_12-0' && "
    "test ! -L /system/bin/rebootsystem.sh && "
    "test \"$(stat -c '%F|%a|%u|%g|%s|%h' /system/bin/rebootsystem.sh)\" = "
    "'regular file|755|0|0|89|1' && "
    "test \"$(sha256sum /system/bin/rebootsystem.sh | cut -d' ' -f1)\" = "
    "'3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07'"
)


def _load_exact(name: str, path: Path):
    existing = __import__("sys").modules.get(name)
    if existing is not None:
        if Path(getattr(existing, "__file__", "")).resolve() != path:
            raise RuntimeError(f"{name} module identity is not exact")
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{name} import specification failed")
    module = importlib.util.module_from_spec(spec)
    __import__("sys").modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        __import__("sys").modules.pop(name, None)
        raise
    if Path(module.__file__).resolve() != path:
        raise RuntimeError(f"{name} loaded from an unexpected path")
    return module


owner = _load_exact("a90_boot_only_f1_minimal_v1", OWNER_PATH)
adapter = _load_exact("a90_boot_only_f1_adapter_v1", ADAPTER_PATH)


class BackendError(RuntimeError):
    """A bounded inventory, parser, transport, or attribution failure."""


class ActivationError(BackendError):
    """The continuation lease, phase, manifest, or guards are not exact."""


_ACTIVATION_SENTINEL = object()
ACTIVATION_SCHEMA = "a90-f1-candidate-return-backend-activation-v1"


@dataclass(frozen=True)
class Activation:
    """Opaque continuation-issued lease required for every backend contact."""

    schema: str
    sentinel: object
    phase: str
    manifest_sha256: str
    run_id: str
    pending_receipt_sha256: str
    approval_sha256: str
    single_samsung_inventory_sha256: str | None
    lease_check: Callable[[], None]
    guard_check: Callable[[], None]
    intent_check: Callable[[], None]
    manifest_check: Callable[[dict[str, Any]], None]
    inventory_check: Callable[[str], None]

    def check(
        self,
        manifest: dict[str, Any] | None = None,
        *,
        operation: str | None = None,
    ) -> None:
        if (
            self.schema != ACTIVATION_SCHEMA
            or self.sentinel is not _ACTIVATION_SENTINEL
            or type(self.phase) is not str
            or self.phase not in {"resume", "finalize"}
            or type(self.manifest_sha256) is not str
            or SHA256_RE.fullmatch(self.manifest_sha256) is None
            or type(self.run_id) is not str
            or type(self.pending_receipt_sha256) is not str
            or SHA256_RE.fullmatch(self.pending_receipt_sha256) is None
            or type(self.approval_sha256) is not str
            or SHA256_RE.fullmatch(self.approval_sha256) is None
            or (
                self.single_samsung_inventory_sha256 is not None
                and (
                    type(self.single_samsung_inventory_sha256) is not str
                    or SHA256_RE.fullmatch(self.single_samsung_inventory_sha256) is None
                )
            )
            or not callable(self.lease_check)
            or not callable(self.guard_check)
            or not callable(self.intent_check)
            or not callable(self.manifest_check)
            or not callable(self.inventory_check)
        ):
            raise ActivationError("backend activation identity is not exact")
        allowed_phases = {
            "inspect": {"resume"},
            "continuation-observe": {"finalize"},
            "effect": {"resume", "finalize"},
            "rollback-observe": {"resume", "finalize"},
        }
        if operation is not None and self.phase not in allowed_phases.get(operation, set()):
            raise ActivationError("backend operation is not valid for this phase")
        for callback in (self.lease_check, self.guard_check, self.intent_check):
            if callback() is not None:
                raise ActivationError("backend activation callback returned a value")
        if manifest is not None:
            if type(manifest) is not dict:
                raise ActivationError("backend manifest is not an object")
            if self.manifest_check(manifest) is not None:
                raise ActivationError("backend manifest callback returned a value")


def _issue_activation(
    *,
    sentinel: object,
    phase: str,
    manifest_sha256: str,
    run_id: str,
    pending_receipt_sha256: str,
    approval_sha256: str,
    single_samsung_inventory_sha256: str | None,
    lease_check: Callable[[], None],
    guard_check: Callable[[], None],
    intent_check: Callable[[], None],
    manifest_check: Callable[[dict[str, Any]], None],
    inventory_check: Callable[[str], None],
) -> Activation:
    if sentinel is not _ACTIVATION_SENTINEL:
        raise ActivationError("backend activation sentinel is not exact")
    activation = Activation(
        schema=ACTIVATION_SCHEMA,
        sentinel=sentinel,
        phase=phase,
        manifest_sha256=manifest_sha256,
        run_id=run_id,
        pending_receipt_sha256=pending_receipt_sha256,
        approval_sha256=approval_sha256,
        single_samsung_inventory_sha256=single_samsung_inventory_sha256,
        lease_check=lease_check,
        guard_check=guard_check,
        intent_check=intent_check,
        manifest_check=manifest_check,
        inventory_check=inventory_check,
    )
    activation.check()
    return activation


@dataclass(frozen=True)
class Inventory:
    adb_rows: tuple[tuple[str, str, tuple[str, ...]], ...]
    a90_native_count: int
    a90_recovery_serial: str | None
    a90_recovery_count: int
    single_samsung_inventory_sha256: str
    usb_inventory_sha256: str
    adb_inventory_sha256: str
    adb_role: str


class _ActivatedRunner:
    """Runner proxy that brackets every subprocess with lease checks."""

    def __init__(
        self,
        runner: Any,
        activation: Activation,
        manifest: dict[str, Any],
        operation: str,
    ):
        self._runner = runner
        self._activation = activation
        self._manifest = manifest
        self._operation = operation

    def run(self, label: str, argv: tuple[str, ...], timeout_sec: int):
        self._activation.check(self._manifest, operation=self._operation)
        result = self._runner.run(label, argv, timeout_sec)
        self._activation.check(self._manifest, operation=self._operation)
        return result


def _canonical(value: Any) -> bytes:
    return owner.canonical_json(value)


def _digest(value: Any) -> str:
    return owner.sha256_bytes(_canonical(value))


def _validate_sha(value: Any, label: str) -> str:
    if type(value) is not str or SHA256_RE.fullmatch(value) is None:
        raise BackendError(f"{label} is not a SHA-256")
    return value


def _parse_usb(raw: bytes) -> tuple[tuple[str, str, str], ...]:
    if not raw or len(raw) > adapter.MAX_OUTPUT_BYTES:
        raise BackendError("USB inventory is empty or oversized")
    rows: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        match = USB_LINE_RE.fullmatch(line)
        if match is None:
            raise BackendError("USB inventory line is malformed")
        try:
            description = match.group("description").decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BackendError("USB description is not UTF-8") from exc
        rows.append(
            (
                match.group("vendor").decode("ascii"),
                match.group("product").decode("ascii"),
                description,
            )
        )
    if not rows:
        raise BackendError("USB inventory has no endpoints")
    return tuple(rows)


def _parse_adb(raw: bytes) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    if len(raw) > adapter.MAX_OUTPUT_BYTES:
        raise BackendError("ADB inventory is oversized")
    try:
        lines = raw.decode("ascii").replace("\r", "").splitlines()
    except UnicodeDecodeError as exc:
        raise BackendError("ADB inventory is not ASCII") from exc
    if not lines or lines[0] != "List of devices attached":
        raise BackendError("ADB inventory header is not exact")
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for line in lines[1:]:
        if not line:
            continue
        fields = line.split(None, 2)
        if len(fields) < 2 or not ADB_SERIAL_RE.fullmatch(fields[0]):
            raise BackendError("ADB inventory endpoint is malformed")
        serial, state = fields[0], fields[1]
        rest = fields[2] if len(fields) == 3 else ""
        if state == "no" and rest.startswith("permissions"):
            state = "no permissions"
            rest = rest[len("permissions") :].lstrip()
        if state not in ADB_STATES or serial in seen:
            raise BackendError("ADB inventory has an unknown state or duplicate")
        seen.add(serial)
        attributes = tuple(sorted(rest.split())) if rest else ()
        if any(ADB_ATTRIBUTE_RE.fullmatch(item) is None for item in attributes):
            raise BackendError("ADB inventory has an unknown attribute")
        rows.append((serial, state, attributes))
    return tuple(rows)


def _single_inventory_digest(usb_raw: bytes, adb_raw: bytes, role: str) -> str:
    return _digest(
        {
            "usbSha256": owner.sha256_bytes(usb_raw),
            "adbSha256": owner.sha256_bytes(adb_raw),
            "role": role,
        }
    )


def _strict_result(result: Any, label: str) -> bytes:
    if (
        not isinstance(result, adapter.CommandResult)
        or type(result.returncode) is not int
        or type(result.quiescent) is not bool
        or result.returncode != 0
        or result.quiescent is not True
        or result.stderr
    ):
        raise BackendError(f"{label} producer failed")
    return result.stdout


class CandidateReturnBackend:
    """Fixed owner for A90 inventory, observation, and rollback calls."""

    def __init__(
        self,
        *,
        activation: Activation,
        runner: Any | None = None,
        log_directory: Path | None = None,
    ) -> None:
        if not isinstance(activation, Activation):
            raise ActivationError("backend requires a continuation activation")
        activation.check()
        self._activation = activation
        self._runner = runner
        self._activated_runner: _ActivatedRunner | None = None
        self._operation = "inspect"
        self._log_directory = log_directory
        self._rollback_binding: dict[str, Any] | None = None
        self._bridge_binding: dict[str, Any] | None = None

    def _runner_for(self, manifest: dict[str, Any]):
        if self._runner is None:
            if self._log_directory is None:
                self._log_directory = owner.RUN_ROOT / (
                    f"{manifest['runId']}-candidate-return-{self._activation.phase}-1-logs"
                )
            recovery_sha256 = manifest["qualification"]["recoveryIdentity"][
                "adbSerialSha256"
            ]
            redactor = adapter.SerialRedactor(hashes=(recovery_sha256,))
            # The Native ACM path is fixed source identity rather than an ADB
            # endpoint, but it can still be echoed by bridge diagnostics.
            redactor.register_secret(FIXED_SERIAL)
            self._runner = adapter.HostRunner(
                self._log_directory,
                redactor=redactor,
            )
        return self._runner

    def _register_runner_serials(
        self,
        manifest: dict[str, Any],
        rows: tuple[tuple[str, str, tuple[str, ...]], ...],
    ) -> None:
        runner = self._runner_for(manifest)
        redactor = getattr(runner, "redactor", None)
        if redactor is not None:
            for serial, _state, _attrs in rows:
                redactor.register_secret(serial)

    def _check(self, manifest: dict[str, Any], operation: str | None = None) -> None:
        self._activation.check(manifest, operation=operation)

    def _contact_runner(self, manifest: dict[str, Any], operation: str | None = None):
        selected_operation = operation or self._operation
        self._check(manifest, selected_operation)
        if getattr(self, "_manifest", None) is not manifest:
            raise ActivationError("backend manifest was not bound by continuation")
        if self._activated_runner is None:
            self._activated_runner = _ActivatedRunner(
                self._runner_for(manifest), self._activation, manifest,
                selected_operation,
            )
        else:
            self._activated_runner._operation = selected_operation
        return self._activated_runner

    def _run(self, manifest: dict[str, Any], label: str, argv: tuple[str, ...], timeout: int):
        if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT_SEC:
            raise BackendError("backend timeout is outside the fixed bound")
        return self._contact_runner(manifest).run(label, argv, timeout)

    def _inventory(self, manifest: dict[str, Any]) -> Inventory:
        qualification = manifest["qualification"]
        recovery_identity = qualification["recoveryIdentity"]["adbSerialSha256"]
        _validate_sha(recovery_identity, "qualified recovery serial")
        usb_raw = _strict_result(
            self._run(manifest, "usb-inventory", (str(LSUSB),), 10),
            "USB inventory",
        )
        adb_raw = _strict_result(
            self._run(manifest, "adb-inventory", (str(ADB), "devices", "-l"), 10),
            "ADB inventory",
        )
        usb_rows = _parse_usb(usb_raw)
        samsung_rows = tuple(row for row in usb_rows if row[0] == A90_VENDOR)
        adb_rows = _parse_adb(adb_raw)
        self._register_runner_serials(manifest, adb_rows)
        a90_native_count = sum(row[1] == A90_NATIVE_PRODUCT for row in samsung_rows)
        a90_recovery_count_usb = sum(row[1] == A90_RECOVERY_PRODUCT for row in samsung_rows)
        matching_recovery = [
            serial
            for serial, state, _attrs in adb_rows
            if state == "recovery"
            and owner.sha256_bytes(serial.encode("utf-8")) == recovery_identity
        ]
        a90_recovery_count = sum(
            1
            for serial, _state, _attrs in adb_rows
            if owner.sha256_bytes(serial.encode("utf-8")) == recovery_identity
        )
        recovery_rows = [
            (serial, state)
            for serial, state, _attrs in adb_rows
            if state == "recovery"
        ]
        if (
            len(samsung_rows) == 1
            and a90_native_count == 1
            and a90_recovery_count == 0
            and not adb_rows
        ):
            adb_role = ADB_ROLE_NATIVE
        elif (
            len(samsung_rows) == 1
            and a90_recovery_count_usb == 1
            and len(adb_rows) == 1
            and len(matching_recovery) == 1
            and recovery_rows == [(matching_recovery[0], "recovery")]
        ):
            adb_role = ADB_ROLE_RECOVERY
        else:
            adb_role = ADB_ROLE_AMBIGUOUS
        single_samsung_inventory_sha256 = _single_inventory_digest(
            usb_raw, adb_raw, adb_role
        )
        return Inventory(
            adb_rows=tuple(adb_rows),
            a90_native_count=a90_native_count,
            a90_recovery_serial=(matching_recovery[0] if len(matching_recovery) == 1 else None),
            a90_recovery_count=a90_recovery_count,
            single_samsung_inventory_sha256=single_samsung_inventory_sha256,
            usb_inventory_sha256=owner.sha256_bytes(usb_raw),
            adb_inventory_sha256=owner.sha256_bytes(adb_raw),
            adb_role=adb_role,
        )

    @staticmethod
    def _same_inventory(before: Inventory, after: Inventory) -> bool:
        return (
            before.single_samsung_inventory_sha256
            == after.single_samsung_inventory_sha256
            and after.a90_native_count == before.a90_native_count
            and after.a90_recovery_count == before.a90_recovery_count
        )

    @staticmethod
    def _exact_endpoint_role(inventory: Inventory, role: str) -> bool:
        """Return true only for the one fixed A90 endpoint role."""
        recovery_rows = [
            (serial, state)
            for serial, state, _attrs in inventory.adb_rows
            if state == "recovery"
        ]
        if role == "native":
            return (
                inventory.adb_role == ADB_ROLE_NATIVE
                and inventory.a90_native_count == 1
                and inventory.a90_recovery_count == 0
                and not recovery_rows
            )
        if role == "recovery":
            return (
                inventory.adb_role == ADB_ROLE_RECOVERY
                and inventory.a90_native_count == 0
                and inventory.a90_recovery_count == 1
                and inventory.a90_recovery_serial is not None
                and len(recovery_rows) == 1
                and recovery_rows[0][0] == inventory.a90_recovery_serial
            )
        raise BackendError("unknown A90 endpoint role")

    @staticmethod
    def _observation(
        state: str,
        *,
        single_samsung_inventory_sha256: str | None,
        untouched: bool,
        snapshot: owner.Snapshot | None = None,
        twrp: dict[str, Any] | None = None,
        attribution: str | None = None,
    ) -> dict[str, Any]:
        return {
            "state": state,
            "otherTargetsUntouched": untouched,
            "singleSamsungInventorySha256": single_samsung_inventory_sha256,
            "candidateSnapshot": None if snapshot is None else snapshot.payload(),
            "twrpIdentity": twrp,
            "attribution": attribution,
        }

    def _unresolved(self, single_samsung_inventory_sha256: str | None = None) -> dict[str, Any]:
        return self._observation(
            STATE_AMBIGUOUS,
            single_samsung_inventory_sha256=single_samsung_inventory_sha256,
            untouched=single_samsung_inventory_sha256 is not None,
        )

    def _candidate_snapshot(self, manifest: dict[str, Any]) -> owner.Snapshot:
        fixed = adapter.FixedA90Adapter(
            self._contact_runner(manifest), qualification=manifest["qualification"]
        )
        snapshot = fixed.observe(
            manifest["candidate"],
            manifest["qualification"]["freshState"],
            require_fresh_state=True,
            timeout_sec=manifest["timeouts"]["healthSec"],
        )
        return snapshot

    def _bridge_preflight(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Read and strictly bind the managed Native bridge generation."""
        raw = _strict_result(
            self._run(
                manifest,
                "bridge-preflight",
                (
                    str(adapter.PYTHON), str(adapter.BRIDGE), "preflight",
                    "--device", FIXED_SERIAL,
                    "--device-glob", FIXED_SERIAL,
                    "--pin-selected-realpath", "--json",
                ),
                10,
            ),
            "bridge preflight",
        )
        try:
            payload = adapter._json(raw, "bridge preflight")
            selected = adapter._validate_bridge(payload)
        except Exception as exc:
            raise BackendError("Native bridge preflight is not exact") from exc
        metadata = payload.get("metadata")
        if (
            type(metadata) is not dict
            or type(metadata.get("started_at")) is not str
            or not metadata.get("started_at")
            or payload.get("ambiguous") is not False
            or type(payload.get("serial_candidates")) is not list
            or len(payload["serial_candidates"]) != 1
        ):
            raise BackendError("Native bridge generation metadata is not exact")
        stable = {
            "selectedDevice": selected["selectedDevice"],
            "selectedRealpath": selected["selectedRealpath"],
            "bridgePid": selected["bridgePid"],
            "portSocketInodes": payload.get("port_socket_inodes"),
            "portSockets": payload.get("port_sockets"),
            "processes": payload.get("processes"),
            "command": metadata.get("command"),
            "startedAt": metadata.get("started_at"),
        }
        binding = {
            "receiptSha256": owner.sha256_bytes(owner.canonical_json(payload)),
            "generationSha256": owner.sha256_bytes(owner.canonical_json(stable)),
            "selectedRealpath": selected["selectedRealpath"],
            "bridgePid": selected["bridgePid"],
        }
        self._bridge_binding = binding
        return binding

    def _publish_bridge_binding(
        self,
        manifest: dict[str, Any],
        initial: dict[str, Any],
        final: dict[str, Any],
    ) -> None:
        runner = self._runner_for(manifest)
        log_directory = getattr(runner, "log_directory", None)
        if not isinstance(log_directory, Path):
            return
        payload = owner.canonical_json(
            {"schema": "a90-f1-native-bridge-binding-v1", "initial": initial, "final": final}
        )
        path = log_directory / "bridge-binding.json"
        try:
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
                0o600,
            )
            try:
                offset = 0
                while offset < len(payload):
                    written = os.write(descriptor, payload[offset:])
                    if written <= 0:
                        raise OSError("bridge binding receipt write stalled")
                    offset += written
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            adapter._fsync_directory(log_directory)
        except OSError as exc:
            raise BackendError("Native bridge binding receipt could not be published") from exc

    def _twrp_identity(self, manifest: dict[str, Any], serial: str) -> dict[str, Any] | None:
        result = self._run(
            manifest,
            "twrp-identity",
            (
                str(ADB), "-s", serial, "shell", "sh", "-c",
                TWRP_IDENTITY_COMMAND,
            ),
            15,
        )
        if (
            not isinstance(result, adapter.CommandResult)
            or type(result.returncode) is not int
            or result.returncode != 0
            or result.quiescent is not True
            or result.stderr
            or result.stdout
        ):
            return None
        return dict(TWRP_IDENTITY)

    def _classify(self, manifest: dict[str, Any], before: Inventory, *, after_physical: bool) -> dict[str, Any]:
        if before.a90_native_count > 1 or before.a90_recovery_count > 1:
            return self._unresolved(before.single_samsung_inventory_sha256)
        if before.a90_recovery_count and before.a90_recovery_serial is None:
            return self._unresolved(before.single_samsung_inventory_sha256)
        if before.a90_native_count == 1 and before.a90_recovery_serial is not None:
            return self._unresolved(before.single_samsung_inventory_sha256)
        if before.a90_native_count == 1:
            try:
                snapshot = self._candidate_snapshot(manifest)
            except ActivationError:
                raise
            except Exception:
                after = self._inventory(manifest)
                return self._unresolved(
                    before.single_samsung_inventory_sha256
                    if self._same_inventory(before, after)
                    else None
                )
            after = self._inventory(manifest)
            if not self._same_inventory(before, after):
                return self._observation(
                    "FOREIGN_ENDPOINT",
                    single_samsung_inventory_sha256=before.single_samsung_inventory_sha256,
                    untouched=False,
                )
            snapshot = replace(snapshot, other_targets_untouched=True)
            if snapshot.version != manifest["candidate"]["version"] or snapshot.build != manifest["candidate"]["build"]:
                return self._observation(
                    "ATTRIBUTABLE_FAILURE",
                    single_samsung_inventory_sha256=before.single_samsung_inventory_sha256,
                    untouched=True,
                    attribution="WRONG_CANDIDATE_RESIDENT",
                )
            if snapshot.healthy is not True:
                return self._observation(
                    "ATTRIBUTABLE_FAILURE",
                    single_samsung_inventory_sha256=before.single_samsung_inventory_sha256,
                    untouched=True,
                    attribution="EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION",
                )
            return self._observation(
                STATE_NATIVE_VISIBLE,
                single_samsung_inventory_sha256=before.single_samsung_inventory_sha256,
                untouched=True,
                snapshot=snapshot,
            )
        if before.a90_recovery_serial is not None:
            # A second recovery endpoint is ambiguous even when one serial
            # hash matches the qualification.  Do not send the fixed TWRP
            # identity probe until both the ADB and USB roles are singular.
            # In particular, one bound ADB serial does not identify which of
            # two identical 04e8:6860 USB rows is the A90 endpoint.
            if not self._exact_endpoint_role(before, "recovery"):
                return self._unresolved(before.single_samsung_inventory_sha256)
            twrp = self._twrp_identity(manifest, before.a90_recovery_serial)
            after = self._inventory(manifest)
            if not self._same_inventory(before, after) or after.a90_recovery_serial != before.a90_recovery_serial:
                return self._observation(
                    STATE_FOREIGN,
                    single_samsung_inventory_sha256=before.single_samsung_inventory_sha256,
                    untouched=False,
                )
            if twrp is None:
                return self._unresolved(before.single_samsung_inventory_sha256)
            return self._observation(
                STATE_TWRP_AFTER_PHYSICAL if after_physical else STATE_TWRP_PRESENT,
                single_samsung_inventory_sha256=before.single_samsung_inventory_sha256,
                untouched=True,
                twrp=twrp,
                attribution=(
                    "BOUND_TWRP_RETURNED_AFTER_PHYSICAL" if after_physical else None
                ),
            )
        return self._unresolved(before.single_samsung_inventory_sha256)

    def inspect_pending(self, manifest: dict[str, Any]) -> dict[str, Any]:
        self._operation = "inspect"
        self._check(manifest, self._operation)
        try:
            inventory = self._inventory(manifest)
        except ActivationError:
            raise
        except Exception:
            return self._unresolved()
        try:
            return self._classify(manifest, inventory, after_physical=False)
        except ActivationError:
            raise
        except Exception:
            return self._unresolved(inventory.single_samsung_inventory_sha256)
        finally:
            self._check(manifest, self._operation)

    def _observed_single_samsung_inventory_sha256(self, manifest: dict[str, Any]) -> str:
        self._check(manifest)
        run = owner.RUN_ROOT / manifest["runId"]
        records = owner.read_records(run)
        record = records.get("24-candidate-return-observed.json")
        payload = record.get("payload") if isinstance(record, dict) else None
        if type(payload) is not dict:
            raise BackendError("candidate observation record is unavailable")
        value = _validate_sha(payload.get("singleSamsungInventorySha256"), "single-Samsung inventory")
        if self._activation.inventory_check(value) is not None:
            raise ActivationError("backend single-Samsung inventory callback returned a value")
        return value

    def observe_after_continuation(
        self, manifest: dict[str, Any], *, physical_action_confirmed: bool
    ) -> dict[str, Any]:
        if type(physical_action_confirmed) is not bool:
            raise BackendError("physical confirmation is not boolean")
        self._operation = "continuation-observe"
        self._check(manifest, self._operation)
        self._observed_single_samsung_inventory_sha256(manifest)
        current = self._inventory(manifest)
        result = self._classify(
            manifest, current, after_physical=physical_action_confirmed
        )
        self._check(manifest, self._operation)
        return result

    def flash(self, artifact: dict[str, Any], *, rollback: bool, timeout_sec: int):
        if type(rollback) is not bool or rollback is not True:
            raise BackendError("candidate flash is forbidden in continuation backend")
        manifest = getattr(self, "_manifest", None)
        if not isinstance(manifest, dict):
            raise BackendError("flash requires the bound manifest")
        self._require_rollback_artifact(artifact)
        self._operation = "effect"
        self._check(manifest, self._operation)
        baseline = self._observed_single_samsung_inventory_sha256(manifest)
        before = self._inventory(manifest)
        if before.single_samsung_inventory_sha256 != baseline:
            raise BackendError("single-Samsung inventory changed before rollback effect")
        exact_native = self._exact_endpoint_role(before, "native")
        exact_recovery = self._exact_endpoint_role(before, "recovery")
        if not (exact_native or exact_recovery):
            raise BackendError("A90 endpoint is ambiguous before rollback effect")
        bridge_binding = None
        if exact_native:
            bridge_binding = self._bridge_preflight(manifest)
        self._check(manifest, self._operation)
        rollback_file = self._open_rollback_artifact()
        try:
            self._check(manifest, self._operation)
            rollback_file.checkpoint()
            if exact_native:
                current_bridge = self._bridge_preflight(manifest)
                if (
                    bridge_binding is None
                    or current_bridge["generationSha256"]
                    != bridge_binding["generationSha256"]
                    or current_bridge["selectedRealpath"]
                    != bridge_binding["selectedRealpath"]
                    or current_bridge["bridgePid"] != bridge_binding["bridgePid"]
                ):
                    raise BackendError("Native bridge changed before rollback helper")
                self._publish_bridge_binding(manifest, bridge_binding, current_bridge)
                rollback_file.checkpoint()
            # This is the final exact-one-Samsung inventory. Its complete raw
            # USB/ADB digests are passed to the owner helper, which captures
            # and checks the same streams again before any effect.
            current = self._inventory(manifest)
            expected_role = "native" if exact_native else "recovery"
            if (
                current.single_samsung_inventory_sha256 != baseline
                or not self._exact_endpoint_role(current, expected_role)
                or current.adb_role != (
                    ADB_ROLE_NATIVE if exact_native else ADB_ROLE_RECOVERY
                )
                or current.single_samsung_inventory_sha256
                != before.single_samsung_inventory_sha256
            ):
                raise BackendError("A90 endpoint or single-Samsung inventory changed before rollback helper")
            self._check(manifest, self._operation)
            rollback_file.checkpoint()
            fixed = adapter.FixedA90Adapter(
                self._contact_runner(manifest), qualification=manifest["qualification"]
            )
            result = fixed.flash(
                self._rollback_binding,
                rollback=True,
                timeout_sec=timeout_sec,
                owner_usb_inventory_sha256=current.usb_inventory_sha256,
                owner_adb_inventory_sha256=current.adb_inventory_sha256,
                owner_adb_role=current.adb_role,
            )
            self._check(manifest, self._operation)
            rollback_file.checkpoint()
        finally:
            rollback_file.close()
        # The helper may legitimately transition Native <-> Recovery, so the
        # post-effect raw USB/ADB bytes are evidence only.  The owner helper
        # already enforced the exact role before its effect; a fresh inventory
        # here must still parse and classify as one of the two exact roles.
        after = self._inventory(manifest)
        if not (
            self._exact_endpoint_role(after, "native")
            or self._exact_endpoint_role(after, "recovery")
        ):
            raise BackendError("post-rollback A90 role is not exact")
        self._check(manifest, self._operation)
        return result

    def observe(
        self,
        expected: dict[str, Any],
        fresh_state: dict[str, Any],
        *,
        require_fresh_state: bool,
        timeout_sec: int,
    ) -> owner.Snapshot:
        manifest = getattr(self, "_manifest", None)
        if not isinstance(manifest, dict):
            raise BackendError("observation requires the bound manifest")
        self._require_rollback_artifact(expected)
        self._operation = "rollback-observe"
        self._check(manifest, self._operation)
        self._observed_single_samsung_inventory_sha256(manifest)
        before = self._inventory(manifest)
        if not self._exact_endpoint_role(before, "native"):
            raise BackendError("rollback observation requires exact Native role")
        fixed = adapter.FixedA90Adapter(
            self._contact_runner(manifest), qualification=manifest["qualification"]
        )
        snapshot = fixed.observe(
            expected,
            fresh_state,
            require_fresh_state=require_fresh_state,
            timeout_sec=timeout_sec,
        )
        self._check(manifest, self._operation)
        after = self._inventory(manifest)
        if not self._exact_endpoint_role(after, "native"):
            raise BackendError("post-observation A90 role is not exact Native")
        self._check(manifest, self._operation)
        return replace(snapshot, other_targets_untouched=True)

    def bind_manifest(self, manifest: dict[str, Any]) -> None:
        self._check(manifest)
        if manifest.get("runId") != self._activation.run_id:
            raise ActivationError("backend run binding is not exact")
        try:
            self._rollback_binding = dict(owner._artifact(manifest["rollback"], "rollback"))
        except Exception as exc:
            raise ActivationError("manifest rollback artifact is not exact") from exc
        self._manifest = manifest
        self._activated_runner = _ActivatedRunner(
            self._runner_for(manifest), self._activation, manifest, self._operation
        )

    def _require_rollback_artifact(self, artifact: Any) -> dict[str, Any]:
        if self._rollback_binding is None:
            raise ActivationError("rollback artifact was not bound by continuation")
        try:
            checked = owner._artifact(artifact, "rollback")
        except Exception as exc:
            raise BackendError("rollback artifact schema is not exact") from exc
        if checked != self._rollback_binding:
            raise BackendError("rollback artifact is not the manifest-bound artifact")
        return checked

    def _open_rollback_artifact(self):
        if self._rollback_binding is None:
            raise ActivationError("rollback artifact was not bound by continuation")
        try:
            artifact = owner.BoundArtifact.open(self._rollback_binding, "rollback")
            artifact.checkpoint()
            return artifact
        except Exception as exc:
            raise BackendError("manifest rollback artifact identity is not exact") from exc


def create(*, activation: Activation) -> CandidateReturnBackend:
    """Create only from a continuation-issued, phase-bound activation lease."""
    if not isinstance(activation, Activation):
        raise ActivationError("backend requires a continuation activation")
    activation.check()
    return CandidateReturnBackend(activation=activation)
