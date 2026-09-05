#!/usr/bin/env python3
"""Build the host-only P3.42 boot/AP identity successor.

The P3.41 packaging engine is loaded and namespace-projected in memory.  Its
real A/B packager, compiler and post-packaging audits are reused unchanged;
only the predecessor/target identities, source paths and output namespace are
rebound.  No device, ADB, Odin or live-authority operation is performed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import types
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import s22plus_fyg8_p341_artifact_identity as predecessor_artifact
import s22plus_fyg8_p341_open_read_branch_acm_observer as predecessor_observer
import s22plus_fyg8_p341_open_read_branch_runtime as predecessor_runtime
import s22plus_fyg8_p341_stock_candidate_build as predecessor_builder
import s22plus_fyg8_p342_artifact_identity as artifact
import s22plus_fyg8_p342_open_read_branch_acm_observer as observer
import s22plus_fyg8_p342_open_read_branch_runtime as runtime


SELF_SOURCE = Path(__file__).resolve()
PREDECESSOR_BUILDER_SOURCE = Path(predecessor_builder.__file__).resolve()
PREDECESSOR_BUILDER_IDENTITY = {
    "size": 6_461,
    "sha256": "3926181e80ab4a1afc1a20863c3e624bc52d92f83d5a93c3b786e00569f8153a",
}
GENERATED_ENGINE_IDENTITY = {
    "size": 33_305,
    "sha256": "597a2d550d6602c3ea039203513ba121357e74cb2df57330cbb2199bd7faf4f2",
}
P341_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p341/"
    "stock-candidate-build-v1-20260905-02"
)
P341_RESULT = P341_OUTPUT / "result.json"
P341_RESULT_IDENTITY = {
    "size": 79_393,
    "sha256": "5733271ebbe1c88db405921275152e5696ca4e38226894d08c6eb434021b2e47",
}
P341_BUILDER_IDENTITY = dict(PREDECESSOR_BUILDER_IDENTITY)
P341_ARTIFACT_SOURCE = Path(predecessor_artifact.__file__).resolve()
P341_RUNTIME_SOURCE = Path(predecessor_runtime.__file__).resolve()
P341_OBSERVER_SOURCE = Path(predecessor_observer.__file__).resolve()
P341_ADAPTER_SOURCE = (
    REVALIDATION / "s22plus_fyg8_p341_stock_process_v2_adapter.py"
)
P341_BUILDER_SOURCE = PREDECESSOR_BUILDER_SOURCE
P341_RUN_ID_HEX = predecessor_runtime.P341_RUN_ID_HEX
P341_RUN_ID = predecessor_runtime.P341_RUN_ID
P341_IMAGE_IDENTITY = dict(artifact.P341_IMAGE_IDENTITY)
P341_AP_IDENTITY = dict(artifact.P341_AP_IDENTITY)
P342_RUN_ID_HEX = runtime.P342_RUN_ID_HEX
P342_RUN_ID = runtime.P342_RUN_ID
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p342/"
    "stock-candidate-build-v1-20260905-02"
)
SCHEMA = "s22plus-fyg8-p342-stock-candidate-build-v1"
VERDICT = "PASS_P342_STOCK_CANDIDATE_BUILD_H0_IDLE_REUSE"
STATUS = "IMPLEMENTED_H0_IDLE_REUSE_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.41 predecessor or P3.42 identity closure differs."""


def identity(value: bytes) -> dict[str, Any]:
    return {"size": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _load_engine_source() -> str:
    payload = PREDECESSOR_BUILDER_SOURCE.read_bytes()
    if identity(payload) != PREDECESSOR_BUILDER_IDENTITY:
        raise AuditError("P3.41 builder source identity differs")
    generated = predecessor_builder.source
    if identity(generated.encode("utf-8")) != GENERATED_ENGINE_IDENTITY:
        raise AuditError("P3.41 generated engine identity differs")
    # Stage both namespaces before shifting the predecessor one generation.
    source = generated.replace("P341", "__P342_UPPER__")
    source = source.replace("p341", "__p342_lower__")
    source = source.replace("P3.41", "__P342_DOT__")
    source = source.replace("P340", "P341")
    source = source.replace("p340", "p341")
    source = source.replace("P3.40", "P3.41")
    source = source.replace("__P342_UPPER__", "P342")
    source = source.replace("__p342_lower__", "p342")
    source = source.replace("__P342_DOT__", "P3.42")
    generated_observer = "s22plus-fyg8-p342-host-first-open-acm-observer-v1"
    if source.count(generated_observer) != 1:
        raise AuditError("P3.42 observer contract anchor differs")
    source = source.replace(generated_observer, observer.CONTRACT_ID, 1)
    old_path = (
        "workspace/private/outputs/s22plus_fyg8_p341/"
        "stock-candidate-build-v1-20260905-01"
    )
    new_path = (
        "workspace/private/outputs/s22plus_fyg8_p341/"
        "stock-candidate-build-v1-20260905-02"
    )
    if source.count(old_path) != 1:
        raise AuditError("P3.41 predecessor output path anchor differs")
    source = source.replace(old_path, new_path, 1)
    def replace_once(old: str, new: str, label: str) -> None:
        nonlocal source
        if source.count(old) != 1:
            raise AuditError(f"P3.42 engine {label} anchor differs")
        source = source.replace(old, new, 1)

    replace_once(
        '"runtime_delta_identity_only": False, "host_first_open": True',
        '"runtime_delta_identity_only": True, "host_first_open": True, '
        '"runtime_behavior_unchanged": True, "idle_listener_unchanged": True, '
        '"initial_session_count": 4, "resident_sessions": 4, '
        '"initial_reconnect_count": 1, "resident_reconnects": 1, '
        '"same_fd_session_count": 3, "idle_seconds": 120, '
        '"total_session_count": 4, "total_command_count": 12, '
        '"resident_lease_schema": "s22plus_fyg8_p342_idle_reuse_lease_v1", '
        '"later_action_lease_active": False',
        "identity-only preservation",
    )
    replace_once(
        '"open_header_capture_best_effort": True})',
        '"open_header_capture_best_effort": True, "host_first_open": True, '
        '"initial_session_count": 4, '
        '"resident_sessions": 4, "session_cap": 4, "resident_session_cap": 4, '
        '"same_fd_session_count": 3, "idle_seconds": 120, '
        '"total_session_count": 4, "total_command_count": 12, '
        '"resident_lease_schema": "s22plus_fyg8_p342_idle_reuse_lease_v1", '
        '"later_action_lease_active": False, "runtime_behavior_unchanged": True, '
        '"idle_listener_unchanged": True})',
        "session geometry",
    )
    replace_once(
        'result["limitations"] = ["P342 changes initial OPEN ordering and consumed-input handling in /init, plus fresh run identity; Image layout is preserved.", "Existing diagnostic encoding is retained; no-input waits emit no unsolicited data and partial input is consumed.", "P342 reuses the existing pinned P319 packaging helper and exact P341 -01 source closure.", "Only boot is packaged; exact Magisk rollback remains mandatory.", "This H0 unit creates no device, approval, D0/D1/F1/recovery/replay/live authority."]',
        'result["limitations"] = ["P342 changes only the fixed run identity; P341 host-first OPEN/device behavior and wire framing are unchanged.", "The dormant H0 idle-reuse schedule is three same-FD sessions, 120 seconds of silent idle, then one close/reopen fourth session and 12 fixed commands.", "P342 reuses the existing pinned P319 packaging helper and exact P341 -02 source closure.", "Only boot is packaged; exact Magisk rollback remains mandatory.", "This H0 unit creates no device, approval, D0/D1/F1/recovery/replay/live authority."]',
        "limitations",
    )
    return source


_ENGINE_SOURCE = _load_engine_source()
_ENGINE = types.ModuleType("s22plus_fyg8_p342_bound_packager")
_ENGINE.__file__ = str(SELF_SOURCE)
try:
    exec(  # noqa: S102
        compile(_ENGINE_SOURCE, str(PREDECESSOR_BUILDER_SOURCE), "exec", dont_inherit=True),
        _ENGINE.__dict__,
    )
except Exception as exc:
    raise AuditError("P3.42 packaging engine failed to load") from exc

# Bind the generated engine's predecessor to the completed P341 output and
# its target to the fresh P342 wrappers.  These are data/module bindings only;
# no predecessor module is mutated.
_ENGINE.P341_OUTPUT = P341_OUTPUT
_ENGINE.P341_RESULT = P341_RESULT
_ENGINE.P341_RESULT_IDENTITY = dict(P341_RESULT_IDENTITY)
_ENGINE.P341_BUILDER_SOURCE = P341_BUILDER_SOURCE
_ENGINE.P341_BUILDER_IDENTITY = dict(P341_BUILDER_IDENTITY)
_ENGINE.P341_ARTIFACT_SOURCE = P341_ARTIFACT_SOURCE
_ENGINE.P341_RUNTIME_SOURCE = P341_RUNTIME_SOURCE
_ENGINE.P341_OBSERVER_SOURCE = P341_OBSERVER_SOURCE
_ENGINE.P341_ADAPTER_SOURCE = P341_ADAPTER_SOURCE
_ENGINE.P341_RUN_ID_HEX = P341_RUN_ID_HEX
_ENGINE.P341_RUN_ID = P341_RUN_ID
_ENGINE.P341_IMAGE_IDENTITY = dict(P341_IMAGE_IDENTITY)
_ENGINE.P341_AP_IDENTITY = dict(P341_AP_IDENTITY)
_ENGINE.P342_ARTIFACT_SOURCE = Path(artifact.__file__).resolve()
_ENGINE.P342_RUNTIME_SOURCE = Path(runtime.__file__).resolve()
_ENGINE.P342_OBSERVER_SOURCE = Path(observer.__file__).resolve()
_ENGINE.P342_ADAPTER_SOURCE = REVALIDATION / (
    "s22plus_fyg8_p342_stock_process_v2_adapter.py"
)
_ENGINE.P342_RUN_ID_HEX = P342_RUN_ID_HEX
_ENGINE.P342_RUN_ID = P342_RUN_ID
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
P342_ARTIFACT_SOURCE = _ENGINE.P342_ARTIFACT_SOURCE
P342_RUNTIME_SOURCE = _ENGINE.P342_RUNTIME_SOURCE
P342_OBSERVER_SOURCE = _ENGINE.P342_OBSERVER_SOURCE
P342_ADAPTER_SOURCE = _ENGINE.P342_ADAPTER_SOURCE


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    result = _ENGINE.audit_existing(output_root)
    expected = {
        "p319_stock_candidate_build.py": _ENGINE.P319_PACKAGER_SOURCE,
        "host-first-open.py": runtime.HOST_FIRST_SOURCE,
        "p341_stock_candidate_build.py": P341_BUILDER_SOURCE,
        "p341_artifact_identity.py": P341_ARTIFACT_SOURCE,
        "p341_open_read_branch_runtime.py": P341_RUNTIME_SOURCE,
        "p341_open_read_branch_acm_observer.py": P341_OBSERVER_SOURCE,
        "p342_stock_candidate_build.py": SELF_SOURCE,
        "p342_artifact_identity.py": P342_ARTIFACT_SOURCE,
        "p342_open_read_branch_runtime.py": P342_RUNTIME_SOURCE,
        "p342_open_read_branch_acm_observer.py": P342_OBSERVER_SOURCE,
        "p342_stock_process_v2_adapter.py": P342_ADAPTER_SOURCE,
    }
    if set(result.get("helper_sources", {})) != set(expected):
        raise AuditError("P3.42 helper source membership differs")
    # The generated engine's stable reader remains authoritative for all
    # copied inputs.  This additional check binds the new wrapper source
    # names explicitly without duplicating the packaging implementation.
    for name, path in expected.items():
        if name in result.get("helper_sources", {}):
            _ENGINE._stable(
                path,
                "P3.42 current helper",
                2 << 20,
                result["helper_sources"][name],
            )
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
