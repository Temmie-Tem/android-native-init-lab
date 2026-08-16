#!/usr/bin/env python3
"""Exact P3.18 S22+ one-reboot baseline-rotation adapter.

The reviewed P2.96 primitive owns the one-command state machine.  This adapter
pins its bytes, the current P3.18 ready manifest, one durable historical D0
identity/health receipt, and the exact target profile.  The historical USB
topology is deliberately not current authority: live selection requires the
same exact serial identity and records one current topology that must remain
unchanged through return health.

The default mode is a host-only fixture.  Live mode still requires the exact
fresh approval string and creates no F1, recovery, replay, or payload authority.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve(strict=True)
BINDING_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p318_d1_baseline_rotation_v1.json"
)
BASE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p296/d1-baseline-rotation/"
    "s22plus_fyg8_p296_baseline_rotation_d1.py"
)
BASE_SHA256 = "bfec4bc9c947e098b6a18134a805524aa8fe8103edd5ddc4bc3b398895cad8ea"
BASE_SIZE = 18578
D0_RUNTIME = ROOT / (
    "workspace/public/src/scripts/revalidation/device_action_d0_v2.py"
)
D0_RUNTIME_SHA256 = (
    "fc4849381bfc40629cb27752fd87b0a24143bf69cd21914188bcb0b491fcf3de"
)
D0_RUNTIME_SIZE = 40024
MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p318_process_v2_ready_1.json"
)
MANIFEST_SHA256 = "082c046f90914730172426c16222981039027d9384d3912fb09ee99d081a73d3"
MANIFEST_SIZE = 2778
HISTORICAL_D0 = ROOT / (
    "workspace/private/runs/device-action-d0-v2/"
    "p308-post-rotation-health-20260807-1/result.json"
)
HISTORICAL_D0_SHA256 = (
    "e75d62206d0aee6f88e0759e0248a6a8937fd9888340e00d21001bcdd6a8522f"
)
HISTORICAL_D0_SIZE = 2934
PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
PROFILE_SHA256 = "7afa7b690b71eabca14c99e83efc55bdb453256bcd40f7ccdf5d41bed78d6c28"
PROFILE_SIZE = 2285
ADB = Path("/usr/lib/android-sdk/platform-tools/adb")
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
ADB_SIZE = 716968
ADB_SNAPSHOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p318/"
    "d1-baseline-rotation-v1/adb-" + ADB_SHA256
)
RUN_DIR = ROOT / (
    "workspace/private/runs/device-action-d1-p318-baseline-rotation/"
    "p318-baseline-rotation-1"
)
RUN_ARM = Path(str(RUN_DIR) + ".arm.json")
AUTHORITY_PREFIX = "DEVICE-ACTION-D1-P318-BASELINE-ROTATE-V1-APPROVE:"


class AdapterError(RuntimeError):
    pass


def _stable_read(
    path: Path,
    expected_sha256: str | None,
    expected_size: int | None,
    label: str,
) -> bytes:
    direct = path.absolute()
    if direct != path or direct.resolve(strict=True) != direct:
        raise AdapterError(f"{label} path is indirect")
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(direct, flags)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or (expected_size is not None and before.st_size != expected_size)
        ):
            raise AdapterError(f"{label} file identity differs")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_nlink",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(before, name) != getattr(after, name) for name in stable_fields):
        raise AdapterError(f"{label} changed while open")
    if expected_size is not None and len(payload) != expected_size:
        raise AdapterError(f"{label} size differs")
    if (
        expected_sha256 is not None
        and hashlib.sha256(payload).hexdigest() != expected_sha256
    ):
        raise AdapterError(f"{label} hash differs")
    return payload


def _decode_object(payload: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AdapterError(f"{label} contains a duplicate key")
            result[key] = value
        return result

    def reject_nonfinite(value: str) -> None:
        raise AdapterError(f"{label} contains non-finite JSON: {value}")

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AdapterError(f"{label} is not an object")
    return value


def _typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            _typed_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(
            _typed_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _stable_inventory_metadata(metadata: set[str]) -> list[str]:
    transport_tokens = sorted(
        item for item in metadata if item.startswith("transport_id:")
    )
    if len(transport_tokens) != 1:
        raise AdapterError("ADB inventory transport_id cardinality differs")
    transport_id = transport_tokens[0].removeprefix("transport_id:")
    if not transport_id or not transport_id.isascii() or not transport_id.isdigit():
        raise AdapterError("ADB inventory transport_id is not ASCII decimal")
    return sorted(item for item in metadata if item != transport_tokens[0])


def _receipt(path: Path, payload: bytes) -> dict[str, object]:
    try:
        rendered_path = str(path.relative_to(ROOT))
    except ValueError:
        rendered_path = str(path)
    return {
        "path": rendered_path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


def _prepare_executable_snapshot(payload: bytes, destination: Path) -> None:
    if (
        len(payload) != ADB_SIZE
        or hashlib.sha256(payload).hexdigest() != ADB_SHA256
    ):
        raise AdapterError("host ADB snapshot source differs")
    parent = destination.parent.absolute()
    try:
        parent.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(parent, 0o700)
    except FileExistsError:
        pass
    if parent.resolve(strict=True) != parent:
        raise AdapterError("host ADB snapshot directory is indirect")
    parent_stat = parent.stat(follow_symlinks=False)
    if (
        not stat.S_ISDIR(parent_stat.st_mode)
        or parent_stat.st_uid != os.getuid()
        or parent_stat.st_mode & 0o777 != 0o700
    ):
        raise AdapterError("host ADB snapshot parent metadata differs")

    if destination.exists() or destination.is_symlink():
        existing = _stable_read(destination, ADB_SHA256, ADB_SIZE, "host ADB snapshot")
        metadata = destination.stat(follow_symlinks=False)
        if metadata.st_mode & 0o777 != 0o500 or existing != payload:
            raise AdapterError("host ADB snapshot metadata differs")
        return

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".adb-snapshot-", dir=parent
    )
    temporary = Path(temporary_name)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AdapterError("host ADB snapshot write failed")
            offset += written
        os.fchmod(descriptor, 0o500)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, destination, follow_symlinks=False)
        except FileExistsError:
            pass
        directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    final = _stable_read(destination, ADB_SHA256, ADB_SIZE, "host ADB snapshot")
    metadata = destination.stat(follow_symlinks=False)
    if metadata.st_mode & 0o777 != 0o500 or final != payload:
        raise AdapterError("host ADB snapshot publication differs")


def _durable_arm(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("utf-8") + b"\n"
    parent = path.parent.absolute()
    try:
        parent.mkdir(mode=0o700, parents=True, exist_ok=False)
        os.chmod(parent, 0o700)
    except FileExistsError:
        pass
    if parent.resolve(strict=True) != parent:
        raise AdapterError("D1 arm directory is indirect")
    parent_stat = parent.stat(follow_symlinks=False)
    if (
        not stat.S_ISDIR(parent_stat.st_mode)
        or parent_stat.st_uid != os.getuid()
        or stat.S_IMODE(parent_stat.st_mode) != 0o700
    ):
        raise AdapterError("D1 arm directory metadata differs")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o400)
    except FileExistsError as exc:
        raise AdapterError("D1 approval arm already exists") from exc
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AdapterError("D1 approval arm write failed")
            offset += written
        os.fchmod(descriptor, 0o400)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_nlink != 1
            or metadata.st_size != len(payload)
        ):
            raise AdapterError("D1 approval arm metadata differs")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _validate_inputs() -> tuple[
    bytes,
    bytes,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    str,
    bytes,
]:
    binding_manifest_payload = _stable_read(
        BINDING_MANIFEST, None, None, "P3.18 D1 binding manifest"
    )
    binding_manifest = _decode_object(
        binding_manifest_payload, "P3.18 D1 binding manifest"
    )
    script_payload = _stable_read(SCRIPT, None, None, "P3.18 D1 adapter")
    manifest_payload = _stable_read(
        MANIFEST, MANIFEST_SHA256, MANIFEST_SIZE, "P3.18 ready manifest"
    )
    d0_payload = _stable_read(
        HISTORICAL_D0,
        HISTORICAL_D0_SHA256,
        HISTORICAL_D0_SIZE,
        "historical healthy D0",
    )
    profile_payload = _stable_read(
        PROFILE, PROFILE_SHA256, PROFILE_SIZE, "S22+ target profile"
    )
    adb_payload = _stable_read(ADB, ADB_SHA256, ADB_SIZE, "host ADB executable")
    base_payload = _stable_read(
        BASE, BASE_SHA256, BASE_SIZE, "P2.96 baseline-rotation primitive"
    )
    d0_runtime_payload = _stable_read(
        D0_RUNTIME,
        D0_RUNTIME_SHA256,
        D0_RUNTIME_SIZE,
        "P3.18 D1 minimal D0 runtime source",
    )
    manifest = _decode_object(manifest_payload, "P3.18 ready manifest")
    historical = _decode_object(d0_payload, "historical healthy D0")
    profile = _decode_object(profile_payload, "S22+ target profile")
    binding_manifest_sha256 = hashlib.sha256(binding_manifest_payload).hexdigest()
    authority = AUTHORITY_PREFIX + binding_manifest_sha256
    try:
        acceptance = manifest["observation"]["acceptance"]
        target = historical["target_evidence"]["targets"][0]
        targets = historical["target_evidence"]["targets"]
        health = historical["health"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AdapterError("pinned input shape differs") from exc
    expected_receipts = {
        "adapter": _receipt(SCRIPT, script_payload),
        "ready_manifest": _receipt(MANIFEST, manifest_payload),
        "historical_d0_identity_health": _receipt(HISTORICAL_D0, d0_payload),
        "target_profile": _receipt(PROFILE, profile_payload),
        "host_adb": _receipt(ADB, adb_payload),
        "pinned_reboot_primitive": _receipt(BASE, base_payload),
        "pinned_d0_runtime_source": _receipt(D0_RUNTIME, d0_runtime_payload),
    }
    review = binding_manifest.get("independent_review")
    expected_review: dict[str, str | None]
    if review == {"status": "review-pending", "verdict": None}:
        expected_review = {"status": "review-pending", "verdict": None}
    elif review == {
        "status": "pass-go",
        "verdict": "PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1",
    }:
        expected_review = {
            "status": "pass-go",
            "verdict": "PASS_GO_P318_D1_BASELINE_ROTATION_H0_CAPABILITY_V1",
        }
    else:
        raise AdapterError("independent D1 review shape differs")
    expected_binding_manifest = {
        "action": "one exact normal Android adb reboot",
        "authority_prefix": AUTHORITY_PREFIX,
        "binding_id": "s22plus-fyg8-p318-d1-baseline-rotation-v1",
        "candidate_transfer": False,
        "command_count": 1,
        "f1_authorized": False,
        "historical_topology_is_current_authority": False,
        "host_adb_execution_snapshot": {
            "mode": "0500",
            "path": str(ADB_SNAPSHOT.relative_to(ROOT)),
            "publication": "file-fsync-link-no-replace-directory-fsync",
            "sha256": ADB_SHA256,
            "size": ADB_SIZE,
        },
        "independent_review": expected_review,
        "initiation_bound_sec": 60,
        "inputs": expected_receipts,
        "live_exact_serial_identity_required": True,
        "live_topology_continuity_required": True,
        "odin": False,
        "partition_payload": False,
        "return_bound_sec": 240,
        "run_directory": {
            "path": str(RUN_DIR.relative_to(ROOT)),
            "publication": "directory-no-replace-then-durable-start-no-replace",
        },
        "run_approval_arm": {
            "path": str(RUN_ARM.relative_to(ROOT)),
            "publication": "file-no-replace-fsync-then-directory-fsync",
        },
        "schema": "s22plus_fyg8_p318_d1_baseline_rotation_binding_v1",
    }
    if (
        not _typed_equal(binding_manifest, expected_binding_manifest)
        or manifest.get("schema") != "device_action_f1_candidate_v2"
        or manifest.get("manifest_id")
        != "s22plus-fyg8-p318-process-v2-ready-1"
        or manifest.get("status") != "ready-for-f1-approval"
        or manifest.get("run_id") != "s22plus-fyg8-p318-live-1"
        or manifest.get("target_profile")
        != "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
        or acceptance.get("clean_baseline_required") is not True
        or acceptance.get("source_contract_id")
        != "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1"
        or acceptance.get("decoder")
        != "s22plus_fyg8_p318_max77705_carrier_v2_envelope_v4"
        or historical.get("schema") != "device_action_d0_result_v2"
        or historical.get("verdict")
        != "PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY"
        or not isinstance(targets, list)
        or len(targets) != 1
        or target.get("model") != "SM-S906N"
        or target.get("device") != "g0q"
        or target.get("firmware_incremental") != "S906NKSS7FYG8"
        or not isinstance(target.get("adb_serial_sha256"), str)
        or len(target["adb_serial_sha256"]) != 64
        or historical.get("device_writes") is not False
        or historical.get("reboot_requested") is not False
        or historical.get("download_transition_requested") is not False
        or historical.get("partition_transfer") is not False
        or historical.get("odin_invoked") is not False
        or historical.get("f1_authorized") is not False
        or health.get("android_boot_completed") is not True
        or health.get("boot_animation_stopped") is not True
        or health.get("root_verified") is not True
        or health.get("odin_endpoint_absent") is not True
        or profile.get("schema") != "device_action_target_profile_v2"
        or profile.get("profile_id") != "s22plus-fyg8"
        or profile.get("target", {}).get("model") != "SM-S906N"
        or profile.get("target", {}).get("device") != "g0q"
        or profile.get("target", {}).get("firmware_incremental")
        != "S906NKSS7FYG8"
    ):
        raise AdapterError("pinned input semantics differ")

    current_target = {
        key: target[key]
        for key in (
            "model",
            "device",
            "firmware_incremental",
            "adb_serial_sha256",
        )
    }
    prior_binding = {
        "target": current_target,
        "health": json.loads(json.dumps(health)),
    }
    binding = {
        "schema": "s22plus_fyg8_p318_d1_baseline_rotation_input_binding_v1",
        "binding_manifest": _receipt(BINDING_MANIFEST, binding_manifest_payload),
        "independent_review": json.loads(json.dumps(review)),
        "authority_sha256": hashlib.sha256(authority.encode("ascii")).hexdigest(),
        "ready_manifest": _receipt(MANIFEST, manifest_payload),
        "historical_d0_identity_health": _receipt(HISTORICAL_D0, d0_payload),
        "target_profile": _receipt(PROFILE, profile_payload),
        "host_adb": _receipt(ADB, adb_payload),
        "host_adb_execution_snapshot": {
            "path": str(ADB_SNAPSHOT.relative_to(ROOT)),
            "sha256": ADB_SHA256,
            "size": ADB_SIZE,
            "mode": "0500",
            "publication": "file-fsync-link-no-replace-directory-fsync",
        },
        "pinned_reboot_primitive": _receipt(BASE, base_payload),
        "pinned_d0_runtime_source": _receipt(D0_RUNTIME, d0_runtime_payload),
        "pinned_d0_runtime_import_mode": (
            "verified-source exec with adapter-owned minimal f1.json_sha256 stub"
        ),
        "manifest_id": manifest["manifest_id"],
        "source_contract_id": acceptance["source_contract_id"],
        "historical_topology_is_current_authority": False,
        "live_exact_serial_identity_required": True,
        "live_topology_continuity_required": True,
        "action": "one exact normal Android adb reboot",
        "attendance_predicate": (
            "operator remains present through the 240-second return bound"
        ),
        "failure_rule": "park without replay or a second reboot command",
        "run_directory": {
            "path": str(RUN_DIR.relative_to(ROOT)),
            "publication": "directory-no-replace-then-durable-start-no-replace",
        },
        "run_approval_arm": {
            "path": str(RUN_ARM.relative_to(ROOT)),
            "publication": "file-no-replace-fsync-then-directory-fsync",
        },
        "other_targets_commanded": False,
        "payload": False,
        "odin": False,
        "download_transition": False,
        "f1_authorized": False,
    }
    return (
        base_payload,
        d0_runtime_payload,
        binding,
        prior_binding,
        profile,
        authority,
        adb_payload,
    )


def _select_current_topology(
    rows: list[tuple[str, str, set[str]]],
    target: dict[str, Any],
    topology: str,
    previous_serial: str | None,
    previous_topology_sha256: str | None,
) -> tuple[str, str, dict[str, Any]]:
    matches = [
        serial
        for serial, state, metadata in rows
        if state == "device"
        and "model:SM_S906N" in metadata
        and "device:g0q" in metadata
    ]
    if len(matches) != 1:
        raise AdapterError(
            f"expected exactly one connected FYG8 S22+, found {len(matches)}"
        )
    serial = matches[0]
    serial_sha256 = hashlib.sha256(serial.encode("utf-8")).hexdigest()
    topology_sha256 = hashlib.sha256(topology.encode("utf-8")).hexdigest()
    if serial_sha256 != target.get("adb_serial_sha256"):
        raise AdapterError("selected S22+ serial identity differs")
    if previous_serial is not None and serial != previous_serial:
        raise AdapterError("selected S22+ changed")
    if (
        previous_topology_sha256 is not None
        and topology_sha256 != previous_topology_sha256
    ):
        raise AdapterError("selected S22+ topology changed during D1")
    models = sorted(
        item.split(":", 1)[1]
        for _serial, _state, metadata in rows
        for item in metadata
        if item.startswith("model:")
    )
    inventory_receipt = [
        {
            "serial_sha256": hashlib.sha256(serial_value.encode("utf-8")).hexdigest(),
            "state": state,
            "stable_metadata": _stable_inventory_metadata(metadata),
        }
        for serial_value, state, metadata in sorted(rows, key=lambda row: row[0])
    ]
    return serial, topology_sha256, {
        "inventory_count": len(rows),
        "inventory_models": models,
        "inventory_sha256": _json_sha256(inventory_receipt),
        "selected_serial_sha256": serial_sha256,
        "selected_topology_sha256": topology_sha256,
        "other_targets_commanded": False,
    }


def _load_base(  # noqa: ANN202
    base_payload: bytes, d0_runtime_payload: bytes, authority: str
):
    prior_path = list(sys.path)
    prior_d0 = sys.modules.get("device_action_d0_v2")
    prior_f1 = sys.modules.get("device_action_f1_v2")
    f1_stub = types.ModuleType("device_action_f1_v2")
    f1_stub.json_sha256 = _json_sha256
    d0_module = types.ModuleType("device_action_d0_v2")
    d0_module.__file__ = str(D0_RUNTIME)
    d0_module.__package__ = None
    module = types.ModuleType("p318_pinned_p296_d1")
    module.__file__ = str(BASE)
    module.__package__ = None
    prior_base = sys.modules.get(module.__name__)
    try:
        sys.modules["device_action_f1_v2"] = f1_stub
        sys.modules["device_action_d0_v2"] = d0_module
        exec(
            compile(d0_runtime_payload, str(D0_RUNTIME), "exec"),
            d0_module.__dict__,
        )
        sys.modules[module.__name__] = module
        exec(compile(base_payload, str(BASE), "exec"), module.__dict__)
    finally:
        sys.path[:] = prior_path
        for name, prior in (
            ("device_action_d0_v2", prior_d0),
            ("device_action_f1_v2", prior_f1),
            (module.__name__, prior_base),
        ):
            if prior is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prior

    module.SCHEMA = "s22plus_fyg8_p318_d1_baseline_rotation_v1"
    module.VERDICT = "PASS_P318_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH"
    module.APPROVAL = authority
    module.RUN_ROOT = ROOT / (
        "workspace/private/runs/device-action-d1-p318-baseline-rotation"
    )
    base_real_transport = module.RealTransport

    class CurrentTopologyRealTransport(base_real_transport):
        def __init__(self, adb: Path, binding: dict[str, Any]):
            super().__init__(adb, binding)
            self.current_topology_sha256: str | None = None

        def select_exact(self) -> tuple[str, dict[str, Any]]:
            rows = self._inventory()
            candidates = [
                serial
                for serial, state, metadata in rows
                if state == "device"
                and "model:SM_S906N" in metadata
                and "device:g0q" in metadata
            ]
            if len(candidates) != 1:
                raise module.RotationError(
                    "expected exactly one connected FYG8 S22+, "
                    f"found {len(candidates)}"
                )
            candidate = candidates[0]
            if (
                hashlib.sha256(candidate.encode("utf-8")).hexdigest()
                != self.binding["target"].get("adb_serial_sha256")
            ):
                raise module.RotationError("selected S22+ serial identity differs")
            topology = self.client.topology(candidate)
            try:
                serial, topology_sha256, selection = _select_current_topology(
                    rows,
                    self.binding["target"],
                    topology,
                    self.selected,
                    self.current_topology_sha256,
                )
            except AdapterError as exc:
                raise module.RotationError(str(exc)) from exc
            self.selected = serial
            self.current_topology_sha256 = topology_sha256
            return serial, selection

        def snapshot(self, serial: str) -> dict[str, Any]:
            value = super().snapshot(serial)
            topology = value.get("topology")
            if (
                not isinstance(topology, str)
                or self.current_topology_sha256 is None
                or hashlib.sha256(topology.encode("utf-8")).hexdigest()
                != self.current_topology_sha256
            ):
                raise module.RotationError(
                    "selected S22+ topology changed during health snapshot"
                )
            return value

    module.RealTransport = CurrentTopologyRealTransport
    base_self_test = module.self_test

    def p318_self_test() -> dict[str, Any]:
        result = base_self_test()
        if (
            result.get("verdict")
            != "PASS_P296_D1_BASELINE_ROTATION_FIXTURE_H0"
            or result.get("reboot_count") != 1
            or result.get("other_target_commands") != 0
            or result.get("device_contact") is not False
        ):
            raise module.RotationError("pinned P2.96 fixture result differs")
        return {
            **result,
            "schema": "s22plus_fyg8_p318_d1_baseline_rotation_v1_fixture_rehearsal",
            "verdict": "PASS_P318_D1_BASELINE_ROTATION_FIXTURE_H0",
        }

    module.self_test = p318_self_test
    return module


def main(argv: list[str] | None = None) -> int:
    try:
        (
            base_payload,
            d0_runtime_payload,
            binding,
            prior_binding,
            profile,
            authority,
            adb_payload,
        ) = _validate_inputs()
        arguments = list(sys.argv[1:] if argv is None else argv)
        if (
            "--live" in arguments
            and binding["independent_review"]["status"] != "pass-go"
        ):
            raise AdapterError("independent D1 adapter review is absent")
        if "--live" in arguments:
            if arguments != ["--live", "--approval", authority]:
                raise AdapterError(
                    "live D1 accepts only the exact approval; caller paths are forbidden"
                )
            _durable_arm(
                RUN_ARM,
                {
                    "schema": "s22plus_fyg8_p318_d1_baseline_rotation_arm_v1",
                    "binding_manifest": binding["binding_manifest"],
                    "approval_sha256": hashlib.sha256(
                        authority.encode("ascii")
                    ).hexdigest(),
                    "run_directory": binding["run_directory"],
                    "action": binding["action"],
                    "command_count": 1,
                    "device_contact_before_arm": False,
                },
            )
            _prepare_executable_snapshot(adb_payload, ADB_SNAPSHOT)
            arguments.extend(
                (
                    "--run-dir",
                    str(RUN_DIR),
                    "--adb",
                    str(ADB_SNAPSHOT),
                )
            )
        module = _load_base(base_payload, d0_runtime_payload, authority)
        durable_create = module.d0.durable_create
        load_json = module.load_json
        base_self_test = module.self_test
        module.prior_binding = lambda: json.loads(json.dumps(prior_binding))

        def bound_self_test() -> dict[str, Any]:
            result = base_self_test()
            return {**result, "p318_adapter_binding": binding}

        def pinned_load_json(path: Path, label: str) -> dict[str, Any]:
            if path != module.PROFILE or label != "S22+ target profile":
                raise module.RotationError("P3.18 D1 attempted an unbound JSON reopen")
            return json.loads(json.dumps(profile))

        def bound_durable_create(path: Path, value: dict[str, Any]) -> None:
            if path.name in {"start.json", "result.json"}:
                if "p318_adapter_binding" in value:
                    raise module.RotationError("P3.18 D1 binding key already exists")
                value = {**value, "p318_adapter_binding": binding}
            durable_create(path, value)

        module.d0.durable_create = bound_durable_create
        module.load_json = pinned_load_json
        module.self_test = bound_self_test
        try:
            result = module.main(arguments)
            if "--live" in arguments:
                _stable_read(
                    ADB_SNAPSHOT,
                    ADB_SHA256,
                    ADB_SIZE,
                    "post-run host ADB snapshot",
                )
            return result
        finally:
            module.d0.durable_create = durable_create
            module.load_json = load_json
            module.self_test = base_self_test
    except (AdapterError, OSError, KeyError, TypeError) as exc:
        print(f"P3.18 baseline rotation adapter error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
