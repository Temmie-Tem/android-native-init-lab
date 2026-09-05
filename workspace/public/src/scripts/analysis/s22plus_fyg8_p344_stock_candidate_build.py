#!/usr/bin/env python3
"""Build the host-only P3.44 boot/AP identity successor.

The consumed P3.43 result and its exact source closure are reopened by
identity.  P3.44 changes only the same-length Image and runtime run markers;
the reviewed named-read catalog, host-first observer, and idle geometry are
unchanged.  Packaging is delegated to the existing pinned P3.19 helper; no
device, ADB, Odin, or live-authority operation is performed.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p343_artifact_identity as predecessor_artifact  # noqa: E402
import s22plus_fyg8_p343_open_read_branch_acm_observer as predecessor_observer  # noqa: E402
import s22plus_fyg8_p343_open_read_branch_runtime as predecessor_runtime  # noqa: E402
import s22plus_fyg8_p343_stock_candidate_build as predecessor_builder  # noqa: E402
import s22plus_fyg8_p344_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p344_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p344_open_read_branch_runtime as runtime  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P343_BUILDER_SOURCE = Path(predecessor_builder.__file__).resolve()
P343_BUILDER_IDENTITY = {
    "size": 14_512,
    "sha256": "c37cb609e5540e9a192239b7b9ef38fb934cc29a3db926f3a927a3586c4d0a26",
}
P343_ENGINE_IDENTITY = {
    "size": 34_560,
    "sha256": "8fe1017cbef0864bab7c49de30da4559594ae316f044bda9a39a996cf83bbd1b",
}
P343_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p343/"
    "stock-candidate-build-v1-20260905-01"
)
P343_RESULT = P343_OUTPUT / "result.json"
P343_RESULT_IDENTITY = {
    "size": 93_068,
    "sha256": "47d676f6591d25bcb9076d80109adcb4eb215b34893413220f294a69b3c4cbe4",
}
P343_ARTIFACT_SOURCE = Path(predecessor_artifact.__file__).resolve()
P343_RUNTIME_SOURCE = Path(predecessor_runtime.__file__).resolve()
P343_OBSERVER_SOURCE = Path(predecessor_observer.__file__).resolve()
P343_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p343_stock_process_v2_adapter.py"
P343_IMAGE_IDENTITY = dict(predecessor_artifact.P343_IMAGE_IDENTITY)
P343_AP_IDENTITY = dict(predecessor_artifact.P343_AP_IDENTITY)
P343_RUN_ID_HEX = predecessor_runtime.P343_RUN_ID_HEX
P343_RUN_ID = predecessor_runtime.P343_RUN_ID
P344_RUN_ID_HEX = runtime.P344_RUN_ID_HEX
P344_RUN_ID = runtime.P344_RUN_ID
P344_ARTIFACT_SOURCE = Path(artifact.__file__).resolve()
P344_RUNTIME_SOURCE = Path(runtime.__file__).resolve()
P344_OBSERVER_SOURCE = Path(observer.__file__).resolve()
P344_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p344_stock_process_v2_adapter.py"
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p344/"
    "stock-candidate-build-v1-20260905-01"
)
SCHEMA = "s22plus-fyg8-p344-stock-candidate-build-v1"
VERDICT = "PASS_P344_STOCK_CANDIDATE_BUILD_H0_IDENTITY_ONLY"
STATUS = "IMPLEMENTED_H0_IDENTITY_ONLY_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.43 predecessor or P3.44 identity closure differs."""


def identity(value: bytes) -> dict[str, Any]:
    return {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _load_engine_source() -> str:
    payload = predecessor_builder._ENGINE_SOURCE.encode("utf-8")
    if identity(payload) != P343_ENGINE_IDENTITY:
        raise AuditError("P3.43 generated engine identity differs")
    source = predecessor_builder._ENGINE_SOURCE
    source = source.replace("P343", "__P344_UPPER__")
    source = source.replace("p343", "__p344_lower__")
    source = source.replace("P3.43", "__P344_DOT__")
    source = source.replace("P342", "P343")
    source = source.replace("p342", "p343")
    source = source.replace("P3.42", "P3.43")
    source = source.replace("__P344_UPPER__", "P344")
    source = source.replace("__p344_lower__", "p344")
    source = source.replace("__P344_DOT__", "P3.44")

    # The predecessor engine contains the P344 observer ID after the namespace
    # shift; replace that one semantic anchor with the fresh observer.
    old_observer = "s22plus-fyg8-p344-readonly-exploration-acm-observer-v1"
    if source.count(old_observer) != 1:
        raise AuditError("P3.44 observer contract anchor differs")
    source = source.replace(old_observer, observer.CONTRACT_ID, 1)

    old = (
        '"runtime_delta_identity_only": False, "host_first_open": True, '
        '"runtime_behavior_unchanged": False, '
        '"default_runtime_behavior_unchanged": True, '
        '"catalog_allowlist_expanded": True, '
        '"middle_command_allowlist": True, '
        '"initial_proof_default_action": "kernel", '
        '"idle_listener_unchanged": True'
    )
    new = (
        '"runtime_delta_identity_only": True, "host_first_open": True, '
        '"runtime_behavior_unchanged": True, '
        '"default_runtime_behavior_unchanged": True, '
        '"catalog_unchanged": True, '
        '"catalog_allowlist_expanded": False, '
        '"middle_command_allowlist": True, '
        '"initial_proof_default_action": "kernel", '
        '"idle_listener_unchanged": True'
    )
    if source.count(old) != 1:
        raise AuditError("P3.44 identity-only preservation anchor differs")
    source = source.replace(old, new, 1)

    old = (
        '"runtime_behavior_unchanged": False, '
        '"default_runtime_behavior_unchanged": True, '
        '"catalog_allowlist_expanded": True, '
        '"middle_command_allowlist": True, '
        '"initial_proof_default_action": "kernel", '
        '"idle_listener_unchanged": True})'
    )
    new = (
        '"runtime_behavior_unchanged": True, '
        '"default_runtime_behavior_unchanged": True, '
        '"catalog_unchanged": True, '
        '"catalog_allowlist_expanded": False, '
        '"middle_command_allowlist": True, '
        '"initial_proof_default_action": "kernel", '
        '"idle_listener_unchanged": True})'
    )
    if source.count(old) != 1:
        raise AuditError("P3.44 runtime preservation anchor differs")
    source = source.replace(old, new, 1)

    old = (
        "P344 changes the fresh run identity and the exact middle-command "
        "named read-only allowlist; P343 host-first OPEN/device behavior, "
        "framing, and default kernel proof are unchanged."
    )
    new = (
        "P344 changes only the fresh run identity; P343 host-first OPEN/device "
        "behavior, framing, five named queries, and default kernel proof are "
        "unchanged."
    )
    if source.count(old) != 1:
        raise AuditError("P3.44 limitations anchor differs")
    source = source.replace(old, new, 1)
    return source


_ENGINE_SOURCE = _load_engine_source()
_ENGINE = types.ModuleType("s22plus_fyg8_p344_bound_packager")
_ENGINE.__file__ = str(SELF_SOURCE)
try:
    exec(  # noqa: S102
        compile(_ENGINE_SOURCE, str(P343_BUILDER_SOURCE), "exec", dont_inherit=True),
        _ENGINE.__dict__,
    )
except Exception as exc:
    raise AuditError("P3.44 packaging engine failed to load") from exc

# Bind the projected engine to the exact completed P343 output and the fresh
# P344 wrappers.  These are module/data bindings only; no predecessor module
# or private output is mutated.
_ENGINE.P343_OUTPUT = P343_OUTPUT
_ENGINE.P343_RESULT = P343_RESULT
_ENGINE.P343_RESULT_IDENTITY = dict(P343_RESULT_IDENTITY)
_ENGINE.P343_BUILDER_SOURCE = P343_BUILDER_SOURCE
_ENGINE.P343_BUILDER_IDENTITY = dict(P343_BUILDER_IDENTITY)
_ENGINE.P343_ARTIFACT_SOURCE = P343_ARTIFACT_SOURCE
_ENGINE.P343_RUNTIME_SOURCE = P343_RUNTIME_SOURCE
_ENGINE.P343_OBSERVER_SOURCE = P343_OBSERVER_SOURCE
_ENGINE.P343_ADAPTER_SOURCE = P343_ADAPTER_SOURCE
_ENGINE.P343_RUN_ID_HEX = P343_RUN_ID_HEX
_ENGINE.P343_RUN_ID = P343_RUN_ID
_ENGINE.P343_IMAGE_IDENTITY = dict(P343_IMAGE_IDENTITY)
_ENGINE.P343_AP_IDENTITY = dict(P343_AP_IDENTITY)
_ENGINE.P344_ARTIFACT_SOURCE = P344_ARTIFACT_SOURCE
_ENGINE.P344_RUNTIME_SOURCE = P344_RUNTIME_SOURCE
_ENGINE.P344_OBSERVER_SOURCE = P344_OBSERVER_SOURCE
_ENGINE.P344_ADAPTER_SOURCE = P344_ADAPTER_SOURCE
_ENGINE.P344_RUN_ID_HEX = P344_RUN_ID_HEX
_ENGINE.P344_RUN_ID = P344_RUN_ID
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = dict(TARGET)
_ENGINE.SELF_SOURCE = SELF_SOURCE
_ENGINE.artifact = artifact
_ENGINE.runtime = runtime
_ENGINE.observer = observer


def _fresh_result(result: dict[str, Any]) -> dict[str, Any]:
    """Project identity-only P344 metadata after the engine's audits."""

    value = copy.deepcopy(result)
    value.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P344_RUN_ID_HEX,
            "runtime_delta_identity_only": True,
            "catalog_unchanged": True,
            "catalog_allowlist_expanded": False,
            "catalog_allowlist_actions": list(runtime.CATALOG_ACTIONS),
            "middle_command_allowlist": True,
            "default_command_tuple_unchanged": True,
            "default_runtime_behavior_unchanged": True,
            "runtime_behavior_unchanged": True,
            "resident_lease_schema": "s22plus_fyg8_p344_exploration_lease_v1",
            "initial_proof_default_action": "kernel",
            "device_contact": False,
            "live_authorized": False,
        }
    )
    preservation = value.get("preservation")
    if isinstance(preservation, dict):
        preservation.update(
            {
                "runtime_delta_identity_only": True,
                "runtime_behavior_unchanged": True,
                "default_runtime_behavior_unchanged": True,
                "catalog_unchanged": True,
                "catalog_allowlist_expanded": False,
                "middle_command_allowlist": True,
                "resident_lease_schema": "s22plus_fyg8_p344_exploration_lease_v1",
                "initial_proof_default_action": "kernel",
                "idle_listener_unchanged": True,
            }
        )
        value["preservation"] = preservation
    for section_name in ("framed_exec", "resident"):
        section = value.get(section_name)
        if isinstance(section, dict):
            section.update(
                {
                    "runtime_behavior_unchanged": True,
                    "default_runtime_behavior_unchanged": True,
                    "catalog_unchanged": True,
                    "catalog_allowlist_expanded": False,
                    "middle_command_allowlist": True,
                    "resident_lease_schema": "s22plus_fyg8_p344_exploration_lease_v1",
                    "initial_proof_default_action": "kernel",
                    "idle_listener_unchanged": True,
                }
            )
    value["limitations"] = [
        "P344 changes only the fresh run identity; P343 host-first OPEN/device behavior, framing, five named queries, and default kernel proof are unchanged.",
        "The inherited H0 idle-reuse schedule is three same-FD sessions, 120 seconds of silent idle, then one close/reopen fourth session and 12 fixed default commands.",
        "The named catalog remains closed, read-only, dormant, and accepts no caller shell, path, lease, or live action; selected-command integration is owned separately.",
        "Only boot is packaged; exact Magisk rollback remains mandatory.",
        "This H0 unit creates no device, approval, D0/D1/F1/recovery/replay/live authority.",
    ]
    return value


def _rewrite_result(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Persist the audited P344 metadata through the private result path."""

    import os

    payload = (
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("ascii")
    path.chmod(0o600)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError("short P344 result metadata publication")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    path.chmod(0o400)
    return result


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    result = _ENGINE.audit_existing(Path(output_root).absolute())
    expected = {
        "p319_stock_candidate_build.py": _ENGINE.P319_PACKAGER_SOURCE,
        "host-first-open.py": runtime.HOST_FIRST_SOURCE,
        "p343_stock_candidate_build.py": P343_BUILDER_SOURCE,
        "p343_artifact_identity.py": P343_ARTIFACT_SOURCE,
        "p343_open_read_branch_runtime.py": P343_RUNTIME_SOURCE,
        "p343_open_read_branch_acm_observer.py": P343_OBSERVER_SOURCE,
        "p344_stock_candidate_build.py": SELF_SOURCE,
        "p344_artifact_identity.py": P344_ARTIFACT_SOURCE,
        "p344_open_read_branch_runtime.py": P344_RUNTIME_SOURCE,
        "p344_open_read_branch_acm_observer.py": P344_OBSERVER_SOURCE,
        "p344_stock_process_v2_adapter.py": P344_ADAPTER_SOURCE,
    }
    if set(result.get("helper_sources", {})) != set(expected):
        raise AuditError("P3.44 helper source membership differs")
    for name, path in expected.items():
        _ENGINE._stable(
            path,
            "P3.44 current helper",
            2 << 20,
            result["helper_sources"][name],
        )
    result = _fresh_result(result)
    _rewrite_result(Path(output_root).absolute() / "result.json", result)
    return result


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False
) -> dict[str, Any]:
    output_root = Path(output_root).absolute()
    if not audit_only:
        _ENGINE._build_once(output_root)
    return audit_existing(output_root)


def __getattr__(name: str) -> Any:
    return getattr(_ENGINE, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_ENGINE)))


if __name__ == "__main__":
    _ENGINE.build_result = build_result
    raise SystemExit(_ENGINE.main())
