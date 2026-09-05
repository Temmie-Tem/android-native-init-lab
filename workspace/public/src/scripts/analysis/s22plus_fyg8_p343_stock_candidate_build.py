#!/usr/bin/env python3
"""Build the host-only P3.43 boot/AP identity successor.

The P3.42 packaging engine is projected in memory and reused for the real A/B
builder, compiler, and post-packaging audits.  P3.43 changes only the fresh
run-bound Image/runtime identities and the closed device-side named-read
validator; no Full-LTO, device, ADB, Odin, or live-authority operation is
performed.
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

import s22plus_fyg8_p342_artifact_identity as predecessor_artifact  # noqa: E402
import s22plus_fyg8_p342_open_read_branch_acm_observer as predecessor_observer  # noqa: E402
import s22plus_fyg8_p342_open_read_branch_runtime as predecessor_runtime  # noqa: E402
import s22plus_fyg8_p342_stock_candidate_build as predecessor_builder  # noqa: E402
import s22plus_fyg8_p343_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p343_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p343_open_read_branch_runtime as runtime  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P342_BUILDER_SOURCE = Path(predecessor_builder.__file__).resolve()
P342_BUILDER_IDENTITY = {
    "size": 11_664,
    "sha256": "c61e49f65af450b0dec717f6fd06d035b29ef73ab2fab93e7d7e7a1c471ba1c6",
}
P342_ENGINE_IDENTITY = {
    "size": 34_098,
    "sha256": "d6eee4e9bd2b39e1c1c31ec8e32c0d50f39392e99bf4537c47f57e4463e43ba5",
}
P342_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p342/"
    "stock-candidate-build-v1-20260905-02"
)
P342_RESULT = P342_OUTPUT / "result.json"
P342_RESULT_IDENTITY = {
    "size": 82_774,
    "sha256": "9868c30c966ecd308f680f51f79d7715aa8151e319efada475efc4f7f1185a7b",
}
P342_ARTIFACT_SOURCE = Path(predecessor_artifact.__file__).resolve()
P342_RUNTIME_SOURCE = Path(predecessor_runtime.__file__).resolve()
P342_OBSERVER_SOURCE = Path(predecessor_observer.__file__).resolve()
P342_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p342_stock_process_v2_adapter.py"
P342_IMAGE_IDENTITY = dict(artifact.P342_IMAGE_IDENTITY)
P342_AP_IDENTITY = dict(artifact.P342_AP_IDENTITY)
P342_RUN_ID_HEX = predecessor_runtime.P342_RUN_ID_HEX
P342_RUN_ID = predecessor_runtime.P342_RUN_ID
# Historical static callers use P341_* for the immediate predecessor slot;
# retain that compatibility spelling while keeping the explicit P342 names.
P341_RUN_ID_HEX = P342_RUN_ID_HEX
P341_RUN_ID = P342_RUN_ID
P343_RUN_ID_HEX = runtime.P343_RUN_ID_HEX
P343_RUN_ID = runtime.P343_RUN_ID
P343_ARTIFACT_SOURCE = Path(artifact.__file__).resolve()
P343_RUNTIME_SOURCE = Path(runtime.__file__).resolve()
P343_OBSERVER_SOURCE = Path(observer.__file__).resolve()
P343_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p343_stock_process_v2_adapter.py"
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p343/"
    "stock-candidate-build-v1-20260905-01"
)
SCHEMA = "s22plus-fyg8-p343-stock-candidate-build-v1"
VERDICT = "PASS_P343_STOCK_CANDIDATE_BUILD_H0_READONLY_EXPLORATION"
STATUS = "IMPLEMENTED_H0_READONLY_EXPLORATION_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.42 predecessor or P3.43 identity closure differs."""


def identity(value: bytes) -> dict[str, Any]:
    return {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _load_engine_source() -> str:
    payload = predecessor_builder._ENGINE_SOURCE.encode("utf-8")
    if identity(payload) != P342_ENGINE_IDENTITY:
        raise AuditError("P3.42 generated engine identity differs")
    source = predecessor_builder._ENGINE_SOURCE
    # Stage the current-generation namespace before shifting P342's consumed
    # predecessor to P342.  This avoids changing substrings twice.
    source = source.replace("P342", "__P343_UPPER__")
    source = source.replace("p342", "__p343_lower__")
    source = source.replace("P3.42", "__P343_DOT__")
    source = source.replace("P341", "P342")
    source = source.replace("p341", "p342")
    source = source.replace("P3.41", "P3.42")
    source = source.replace("__P343_UPPER__", "P343")
    source = source.replace("__p343_lower__", "p343")
    source = source.replace("__P343_DOT__", "P3.43")

    old_observer = "s22plus-fyg8-p343-idle-reuse-acm-observer-v1"
    if source.count(old_observer) != 1:
        raise AuditError("P3.42 observer contract anchor differs")
    source = source.replace(old_observer, observer.CONTRACT_ID, 1)

    # The predecessor engine's functional default tuple remains the initial
    # kernel action, but P343 additionally carries the closed named catalog.
    old = '"runtime_delta_identity_only": True, "host_first_open": True'
    new = (
        '"runtime_delta_identity_only": False, "host_first_open": True, '
        '"runtime_behavior_unchanged": False, '
        '"default_runtime_behavior_unchanged": True, '
        '"catalog_allowlist_expanded": True, '
        '"middle_command_allowlist": True, '
        '"initial_proof_default_action": "kernel", '
        '"idle_listener_unchanged": True'
    )
    if source.count(old) != 1:
        raise AuditError("P3.43 preservation anchor differs")
    source = source.replace(old, new, 1)
    old = '"runtime_behavior_unchanged": True, "idle_listener_unchanged": True})'
    new = (
        '"runtime_behavior_unchanged": False, '
        '"default_runtime_behavior_unchanged": True, '
        '"catalog_allowlist_expanded": True, '
        '"middle_command_allowlist": True, '
        '"initial_proof_default_action": "kernel", '
        '"idle_listener_unchanged": True})'
    )
    if source.count(old) != 1:
        raise AuditError("P3.43 runtime preservation anchor differs")
    source = source.replace(old, new, 1)
    old = "P343 changes only the fixed run identity; P342 host-first OPEN/device behavior and wire framing are unchanged."
    new = (
        "P343 changes the fresh run identity and the exact middle-command named "
        "read-only allowlist; P342 host-first OPEN/device behavior, framing, "
        "and default kernel proof are unchanged."
    )
    if source.count(old) != 1:
        raise AuditError("P3.43 limitations anchor differs")
    source = source.replace(old, new, 1)
    return source


_ENGINE_SOURCE = _load_engine_source()
_ENGINE = types.ModuleType("s22plus_fyg8_p343_bound_packager")
_ENGINE.__file__ = str(SELF_SOURCE)
try:
    exec(  # noqa: S102
        compile(_ENGINE_SOURCE, str(P342_BUILDER_SOURCE), "exec", dont_inherit=True),
        _ENGINE.__dict__,
    )
except Exception as exc:
    raise AuditError("P3.43 packaging engine failed to load") from exc

# Bind the projected engine's predecessor to the completed P342 output and
# its current-generation wrappers.  These are data/module bindings only; no
# predecessor module is mutated.
_ENGINE.P342_OUTPUT = P342_OUTPUT
_ENGINE.P342_RESULT = P342_RESULT
_ENGINE.P342_RESULT_IDENTITY = dict(P342_RESULT_IDENTITY)
_ENGINE.P342_BUILDER_SOURCE = P342_BUILDER_SOURCE
_ENGINE.P342_BUILDER_IDENTITY = dict(P342_BUILDER_IDENTITY)
_ENGINE.P342_ARTIFACT_SOURCE = P342_ARTIFACT_SOURCE
_ENGINE.P342_RUNTIME_SOURCE = P342_RUNTIME_SOURCE
_ENGINE.P342_OBSERVER_SOURCE = P342_OBSERVER_SOURCE
_ENGINE.P342_ADAPTER_SOURCE = P342_ADAPTER_SOURCE
_ENGINE.P342_RUN_ID_HEX = predecessor_runtime.P342_RUN_ID_HEX
_ENGINE.P342_RUN_ID = predecessor_runtime.P342_RUN_ID
_ENGINE.P342_IMAGE_IDENTITY = dict(P342_IMAGE_IDENTITY)
_ENGINE.P342_AP_IDENTITY = dict(P342_AP_IDENTITY)
_ENGINE.P343_ARTIFACT_SOURCE = P343_ARTIFACT_SOURCE
_ENGINE.P343_RUNTIME_SOURCE = P343_RUNTIME_SOURCE
_ENGINE.P343_OBSERVER_SOURCE = P343_OBSERVER_SOURCE
_ENGINE.P343_ADAPTER_SOURCE = P343_ADAPTER_SOURCE
_ENGINE.P343_RUN_ID_HEX = P343_RUN_ID_HEX
_ENGINE.P343_RUN_ID = P343_RUN_ID
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = dict(TARGET)
_ENGINE.SELF_SOURCE = SELF_SOURCE
_ENGINE.artifact = artifact
_ENGINE.runtime = runtime
_ENGINE.observer = observer

SCHEMA = _ENGINE.SCHEMA
VERDICT = _ENGINE.VERDICT
STATUS = _ENGINE.STATUS
TARGET = _ENGINE.TARGET
P343_ARTIFACT_SOURCE = _ENGINE.P343_ARTIFACT_SOURCE
P343_RUNTIME_SOURCE = _ENGINE.P343_RUNTIME_SOURCE
P343_OBSERVER_SOURCE = _ENGINE.P343_OBSERVER_SOURCE
P343_ADAPTER_SOURCE = _ENGINE.P343_ADAPTER_SOURCE


def _fresh_result(result: dict[str, Any]) -> dict[str, Any]:
    """Add P343 catalog identity without weakening the engine's audits."""

    value = copy.deepcopy(result)
    value.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P343_RUN_ID_HEX,
            "catalog_allowlist_expanded": True,
            "catalog_allowlist_actions": list(runtime.CATALOG_ACTIONS),
            "middle_command_allowlist": True,
            "default_command_tuple_unchanged": True,
            "default_runtime_behavior_unchanged": True,
            "runtime_behavior_unchanged": False,
            "initial_proof_default_action": "kernel",
            "device_contact": False,
            "live_authorized": False,
        }
    )
    preservation = value.get("preservation")
    if isinstance(preservation, dict):
        preservation.update(
            {
                "runtime_delta_identity_only": False,
                "runtime_behavior_unchanged": False,
                "default_runtime_behavior_unchanged": True,
                "catalog_allowlist_expanded": True,
                "middle_command_allowlist": True,
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
                    "runtime_behavior_unchanged": False,
                    "default_runtime_behavior_unchanged": True,
                    "catalog_allowlist_expanded": True,
                    "middle_command_allowlist": True,
                    "initial_proof_default_action": "kernel",
                    "idle_listener_unchanged": True,
                }
            )
    value["limitations"] = [
        "P343 changes the fresh run identity and exact middle-command named read-only allowlist; P342 host-first OPEN/device behavior, framing, and default kernel proof are unchanged.",
        "The inherited H0 idle-reuse schedule is three same-FD sessions, 120 seconds of silent idle, then one close/reopen fourth session and 12 fixed default commands.",
        "The named catalog is dormant and accepts no caller shell, path, lease, or live action; selected-command integration is owned separately.",
        "Only boot is packaged; exact Magisk rollback remains mandatory.",
        "This H0 unit creates no device, approval, D0/D1/F1/recovery/replay/live authority.",
    ]
    return value


def _rewrite_result(path: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Rewrite the engine result through its own strict publication path."""

    # The engine already produced a complete mode-0400 result.  Updating it
    # here is limited to P343 metadata and is followed by the same atomic
    # exclusive-style checks at the audit seam.
    payload = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")
    import os
    # The engine publishes results mode 0400.  Reopen that exact regular file
    # for this host-only metadata projection, then restore the private mode.
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
                raise AuditError("short P343 result metadata publication")
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
        "p342_stock_candidate_build.py": P342_BUILDER_SOURCE,
        "p342_artifact_identity.py": P342_ARTIFACT_SOURCE,
        "p342_open_read_branch_runtime.py": P342_RUNTIME_SOURCE,
        "p342_open_read_branch_acm_observer.py": P342_OBSERVER_SOURCE,
        "p343_stock_candidate_build.py": SELF_SOURCE,
        "p343_artifact_identity.py": P343_ARTIFACT_SOURCE,
        "p343_open_read_branch_runtime.py": P343_RUNTIME_SOURCE,
        "p343_open_read_branch_acm_observer.py": P343_OBSERVER_SOURCE,
        "p343_stock_process_v2_adapter.py": P343_ADAPTER_SOURCE,
    }
    if set(result.get("helper_sources", {})) != set(expected):
        raise AuditError("P3.43 helper source membership differs")
    for name, path in expected.items():
        _ENGINE._stable(
            path,
            "P3.43 current helper",
            2 << 20,
            result["helper_sources"][name],
        )
    # The generated engine's metadata predates the named catalog.  Reopen the
    # result and expose the corrected P343 projection only after all package
    # and predecessor audits have passed.
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
