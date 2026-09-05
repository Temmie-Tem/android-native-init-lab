#!/usr/bin/env python3
"""Host-only P3.45 boot/AP builder for the bounded research shell.

P3.44 is the consumed exact predecessor.  This wrapper projects the reviewed
P3.44 packaging engine in memory, changes only the fresh P3.45 Image/runtime
identity and the already-reviewed sequence-4 read-only shell transform, then
uses the pinned P3.19 packager for deterministic A/B boot/AP output.  It does
not contact a device, run ADB/Odin, create live authority, or build Full-LTO.

The P3.45 artifact, runtime, adapter and read-only child are source inputs
owned by their respective H0 workers.  There is intentionally no new
artifact/adapter framework here; the existing P3.44 engine remains the
packaging implementation.
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

import s22plus_fyg8_p344_artifact_identity as predecessor_artifact  # noqa: E402
import s22plus_fyg8_p344_open_read_branch_acm_observer as predecessor_observer  # noqa: E402
import s22plus_fyg8_p344_open_read_branch_runtime as predecessor_runtime  # noqa: E402
import s22plus_fyg8_p344_stock_candidate_build as predecessor_builder  # noqa: E402
import s22plus_fyg8_p345_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p345_readonly_child as child  # noqa: E402
import s22plus_fyg8_p345_research_shell_runtime as runtime  # noqa: E402
import s22plus_fyg8_p345_research_shell_observer as observer  # noqa: E402
import s22plus_fyg8_p345_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P344_BUILDER_SOURCE = Path(predecessor_builder.__file__).resolve()
P344_BUILDER_IDENTITY = {
    "size": 14_473,
    "sha256": "93eab87e495a75e384d626b82ac6ab600e613e9a343dc9eebc4d33e036be9b50",
}
P344_ENGINE_IDENTITY = {
    "size": 34_583,
    "sha256": "e725531254ab1aa5b135f999d8924492d63d3196b48404e23cd7018cf950f860",
}
P344_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p344/"
    "stock-candidate-build-v1-20260905-01"
)
P344_RESULT = P344_OUTPUT / "result.json"
P344_RESULT_IDENTITY = {
    "size": 105_068,
    "sha256": "d299eeb15d216040bd26294e760f71bfd4d9ac7e40d95d2aaefb6a476a20e6cd",
}
P344_ARTIFACT_SOURCE = Path(predecessor_artifact.__file__).resolve()
P344_ARTIFACT_IDENTITY = {
    "size": 17_369,
    "sha256": "6578805fa29dd677eba383eb85ed1fcb05c3693a4ea4fbd1e89e5daf28a400a7",
}
P344_RUNTIME_SOURCE = Path(predecessor_runtime.__file__).resolve()
P344_RUNTIME_IDENTITY = {
    "size": 14_035,
    "sha256": "9b4493e4c2c1eefd5bab9dc08b467f2b242dfc9c5797fdefada221daf93335f9",
}
P344_OBSERVER_SOURCE = Path(predecessor_observer.__file__).resolve()
P345_RUNTIME_SOURCE = Path(runtime.__file__).resolve()
P345_RUNTIME_IDENTITY = {
    "size": 40_666,
    "sha256": "eab728141657d1d0fa11b4ce5affc7d42426927331c6bdd6500079a1842911d7",
}
P345_RUNTIME_CONTRACT_ID = getattr(
    runtime,
    "CONTRACT_ID",
    "s22plus-fyg8-p345-research-shell-runtime-v1",
)
P345_CHILD_SOURCE = child.SOURCE
P345_CHILD_IDENTITY = dict(child.SOURCE_IDENTITY)
P345_ARTIFACT_SOURCE = Path(artifact.__file__).resolve()
P345_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p345_stock_process_v2_adapter.py"
P345_OBSERVER_SOURCE = Path(observer.__file__).resolve()
P345_ARTIFACT_IDENTITY = {
    "size": 4_090,
    "sha256": "db540159a31b3f82a67c91837e814aa873c74d2b373dd6eb2291bb2c107d5402",
}
P345_OBSERVER_IDENTITY = {
    "size": 42_583,
    "sha256": "dd9da49059b6cbb9ef79c6fac30a5bec491161a4003a99ad9e3b3775b70acfee",
}
P345_ADAPTER_IDENTITY = {
    "size": 7_753,
    "sha256": "f9934c7d274a93ee079ee15e5f7daca089326d8da075086f03eaf77acf7bae40",
}

P344_RUN_ID_HEX = predecessor_runtime.P344_RUN_ID_HEX
P344_RUN_ID = predecessor_runtime.P344_RUN_ID
P345_RUN_ID_HEX = runtime.P345_RUN_ID_HEX
P345_RUN_ID = runtime.P345_RUN_ID
P344_IMAGE_IDENTITY = dict(predecessor_artifact.P344_IMAGE_IDENTITY)
P344_AP_IDENTITY = dict(predecessor_artifact.P344_AP_IDENTITY)
DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p345/"
    "stock-candidate-build-v1-20260906-02"
)
SCHEMA = "s22plus-fyg8-p345-stock-candidate-build-v1"
VERDICT = "PASS_P345_STOCK_CANDIDATE_BUILD_H0_RESEARCH_SHELL"
STATUS = "IMPLEMENTED_H0_RESEARCH_SHELL_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class AuditError(RuntimeError):
    """The exact P3.44 predecessor or P3.45 source closure differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_source(path: Path, expected: dict[str, Any], label: str) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if identity(payload) != expected:
        raise AuditError(f"{label} identity differs")
    return payload


P345_IMAGE_IDENTITY = dict(artifact.P345_IMAGE_IDENTITY)
P345_AP_IDENTITY = getattr(artifact, "P345_AP_IDENTITY", None)


def _runtime_view() -> types.ModuleType:
    """Expose P345 runtime plus the inherited host-first source path."""

    value = types.ModuleType("s22plus_fyg8_p345_runtime_bound")
    value.__dict__.update(vars(runtime))
    value.__file__ = str(P345_RUNTIME_SOURCE)
    value.HOST_FIRST_SOURCE = predecessor_runtime.HOST_FIRST_SOURCE
    value.CONTRACT_ID = P345_RUNTIME_CONTRACT_ID
    return value


runtime_view = _runtime_view()


def _project_engine_source() -> str:
    payload = predecessor_builder._ENGINE_SOURCE.encode("utf-8")
    if identity(payload) != P344_ENGINE_IDENTITY:
        raise AuditError("P3.44 generated engine identity differs")
    source = predecessor_builder._ENGINE_SOURCE
    source = source.replace("P344", "__P345_UPPER__")
    source = source.replace("p344", "__p345_lower__")
    source = source.replace("P3.44", "__P345_DOT__")
    source = source.replace("P343", "P344")
    source = source.replace("p343", "p344")
    source = source.replace("P3.43", "P3.44")
    source = source.replace("__P345_UPPER__", "P345")
    source = source.replace("__p345_lower__", "p345")
    source = source.replace("__P345_DOT__", "P3.45")
    source = source.replace(
        "import s22plus_fyg8_p345_artifact_identity as artifact  # noqa: E402",
        "# artifact is bound by the outer P3.45 wrapper",
    )
    source = source.replace(
        "import s22plus_fyg8_p345_open_read_branch_runtime as runtime  # noqa: E402",
        "# runtime is bound by the outer P3.45 wrapper",
    )
    old_contract = "s22plus-fyg8-p345-readonly-exploration-acm-observer-v1"
    if source.count(old_contract) != 1:
        raise AuditError("P3.45 observer contract anchor differs")
    source = source.replace(old_contract, observer.CONTRACT_ID, 1)

    # The adapter is a separate worker but is a real source input.  The
    # published P345 qualification observer is copied as-is; no wrapper is
    # fabricated here.
    child_item = '("p345-runtime.py", P345_RUNTIME_SOURCE), '
    if source.count(child_item) != 1:
        raise AuditError("P3.45 runtime input anchor differs")
    source = source.replace(
        child_item,
        child_item + '("p345-readonly-child.inc.c", P345_CHILD_SOURCE), ',
        1,
    )
    observer_item = (
        '"p345_open_read_branch_acm_observer.py": '
        "identity(P345_OBSERVER_SOURCE.read_bytes()), "
    )
    if source.count(observer_item) != 1:
        raise AuditError("P3.45 observer helper receipt anchor differs")
    source = source.replace(
        observer_item,
        '"p345_observer.py": identity(P345_OBSERVER_SOURCE.read_bytes()), ',
        1,
    )
    helper_item = '"p345_open_read_branch_runtime.py": identity(P345_RUNTIME_SOURCE.read_bytes()), '
    if source.count(helper_item) != 1:
        raise AuditError("P3.45 runtime receipt anchor differs")
    source = source.replace(
        helper_item,
        helper_item + '"p345_readonly_child.inc.c": identity(P345_CHILD_SOURCE.read_bytes()), ',
        1,
    )
    return source


_ENGINE_SOURCE = _project_engine_source()
_ENGINE = types.ModuleType("s22plus_fyg8_p345_bound_packager")
_ENGINE.__file__ = str(SELF_SOURCE)
_ENGINE.artifact = artifact
_ENGINE.runtime = runtime_view
try:
    exec(compile(_ENGINE_SOURCE, str(P344_BUILDER_SOURCE), "exec", dont_inherit=True), _ENGINE.__dict__)  # noqa: S102
except Exception as exc:
    raise AuditError("P3.45 packaging engine failed to load") from exc

# Rebind every engine input to the exact completed P344 output and the fresh
# P345 source workers.  These are immutable host-side identities only.
_ENGINE.P344_OUTPUT = P344_OUTPUT
_ENGINE.P344_RESULT = P344_RESULT
_ENGINE.P344_RESULT_IDENTITY = dict(P344_RESULT_IDENTITY)
_ENGINE.P344_BUILDER_SOURCE = P344_BUILDER_SOURCE
_ENGINE.P344_BUILDER_IDENTITY = dict(P344_BUILDER_IDENTITY)
_ENGINE.P344_ARTIFACT_SOURCE = P344_ARTIFACT_SOURCE
_ENGINE.P344_RUNTIME_SOURCE = P344_RUNTIME_SOURCE
_ENGINE.P344_OBSERVER_SOURCE = P344_OBSERVER_SOURCE
_ENGINE.P344_RUN_ID_HEX = P344_RUN_ID_HEX
_ENGINE.P344_RUN_ID = P344_RUN_ID
_ENGINE.P344_IMAGE_IDENTITY = dict(P344_IMAGE_IDENTITY)
_ENGINE.P344_AP_IDENTITY = dict(P344_AP_IDENTITY)
_ENGINE.P345_ARTIFACT_SOURCE = P345_ARTIFACT_SOURCE
_ENGINE.P345_RUNTIME_SOURCE = P345_RUNTIME_SOURCE
_ENGINE.P345_OBSERVER_SOURCE = P345_OBSERVER_SOURCE
_ENGINE.P345_ADAPTER_SOURCE = P345_ADAPTER_SOURCE
_ENGINE.P345_CHILD_SOURCE = P345_CHILD_SOURCE
_ENGINE.P345_RUN_ID_HEX = P345_RUN_ID_HEX
_ENGINE.P345_RUN_ID = P345_RUN_ID
_ENGINE.DEFAULT_OUTPUT_ROOT = DEFAULT_OUTPUT_ROOT
_ENGINE.SCHEMA = SCHEMA
_ENGINE.VERDICT = VERDICT
_ENGINE.STATUS = STATUS
_ENGINE.TARGET = dict(TARGET)
_ENGINE.SELF_SOURCE = SELF_SOURCE
_ENGINE.artifact = artifact
_ENGINE.runtime = runtime_view


def _fresh_result(value: dict[str, Any]) -> dict[str, Any]:
    """Mark the real engine result with the P345 behavior delta."""

    result = copy.deepcopy(value)
    # P345 intentionally changes the shell/cancellation path.  Do not carry
    # P344's broad "default unchanged" labels into this candidate; retain only
    # the narrow fact that sequence 3/5 outer witnesses remain fixed.
    result.pop("default_runtime_behavior_unchanged", None)
    result.pop("default_command_tuple_unchanged", None)
    result.pop("named_readonly_catalog_unchanged", None)
    result.update(
        {
            "schema": SCHEMA,
            "verdict": VERDICT,
            "status": STATUS,
            "run_id_hex": P345_RUN_ID_HEX,
            "runtime_delta_identity_only": False,
            "runtime_behavior_unchanged": False,
            "read_only_child_boundary": True,
            "authenticated_cancel": True,
            "catalog_unchanged": False,
            "catalog_allowlist_expanded": False,
            "middle_command_validator_widened": True,
            "fixed_outer_id_nonce_commands_unchanged": True,
            "middle_command_allowlist": True,
            "initial_proof_default_action": "kernel",
            "device_contact": False,
            "live_authorized": False,
            "f1_ready": False,
            "p345_image_identity": dict(P345_IMAGE_IDENTITY),
            "p345_child_source": dict(P345_CHILD_IDENTITY),
            "initial_session_count": observer.SESSION_COUNT,
            "same_fd_session_count": observer.SAME_FD_SESSION_COUNT,
            "initial_reconnect_count": observer.RECONNECT_COUNT,
            "idle_seconds": 0,
            "total_session_count": observer.SESSION_COUNT,
            "total_command_count": observer.SESSION_COUNT * len(runtime.DEFAULT_COMMANDS),
            "later_action_lease_active": False,
        }
    )
    result["lineage"] = dict(result.get("lineage", {}))
    result["lineage"].update(
        {
            "construction_base_run_id": P344_RUN_ID_HEX,
            "predecessor_run_id": P344_RUN_ID_HEX,
            "fresh_run_id": P345_RUN_ID_HEX,
            "construction_base_result": dict(P344_RESULT_IDENTITY),
            "construction_base_ap": dict(P344_AP_IDENTITY),
            "runtime_source": dict(P345_RUNTIME_IDENTITY),
            "readonly_child_source": dict(P345_CHILD_IDENTITY),
            "image_identity": dict(P345_IMAGE_IDENTITY),
            "image_transform": dict(result["lineage"].get("image_transform", {})),
            "p344_source_closure_reopened": True,
            "behavior_delta": "sequence-4-readonly-child-and-authenticated-cancel",
        }
    )
    result["adapter_audit"] = adapter.audit()
    result["qualification_observer"] = observer.audit_binding()
    result["artifact_binding"] = artifact.validate_p345_identity()
    sections = (result.get("framed_exec"), result.get("resident"))
    for section in sections:
        if isinstance(section, dict):
            section.update(
                {
                    "runtime_contract": P345_RUNTIME_CONTRACT_ID,
                    "observer_contract": observer.CONTRACT_ID,
                    "runtime_delta_identity_only": False,
                    "runtime_behavior_unchanged": False,
                    "catalog_unchanged": False,
                    "catalog_allowlist_expanded": False,
                    "middle_command_validator_widened": True,
                    "fixed_outer_id_nonce_commands_unchanged": True,
                    "middle_command_allowlist": True,
                    "initial_proof_default_action": "kernel",
                    "read_only_child_boundary": True,
                    "authenticated_cancel": True,
                    "resident_lease_schema": None,
                    "initial_session_count": observer.SESSION_COUNT,
                    "resident_sessions": observer.SESSION_COUNT,
                    "session_cap": observer.SESSION_COUNT,
                    "resident_session_cap": observer.SESSION_COUNT,
                    "same_fd_session_count": observer.SAME_FD_SESSION_COUNT,
                    "idle_seconds": 0,
                    "initial_reconnect_count": observer.RECONNECT_COUNT,
                    "resident_reconnects": observer.RECONNECT_COUNT,
                    "total_session_count": observer.SESSION_COUNT,
                    "total_command_count": observer.SESSION_COUNT * len(runtime.DEFAULT_COMMANDS),
                    "later_action_lease_active": False,
                }
            )
            section.pop("fixed_p330_commands", None)
            section.pop("default_runtime_behavior_unchanged", None)
            section.pop("named_readonly_catalog_unchanged", None)
    preservation = result.get("preservation")
    if isinstance(preservation, dict):
        preservation.update(
            {
                "runtime_delta_identity_only": False,
                "runtime_behavior_unchanged": False,
                "catalog_unchanged": False,
                "catalog_allowlist_expanded": False,
                "middle_command_validator_widened": True,
                "fixed_outer_id_nonce_commands_unchanged": True,
                "middle_command_allowlist": True,
                "initial_proof_default_action": "kernel",
                "read_only_child_boundary": True,
                "authenticated_cancel": True,
                "resident_lease_schema": None,
                "initial_session_count": observer.SESSION_COUNT,
                "resident_sessions": observer.SESSION_COUNT,
                "initial_reconnect_count": observer.RECONNECT_COUNT,
                "resident_reconnects": observer.RECONNECT_COUNT,
                "same_fd_session_count": observer.SAME_FD_SESSION_COUNT,
                "idle_seconds": 0,
                "total_session_count": observer.SESSION_COUNT,
                "total_command_count": observer.SESSION_COUNT * len(runtime.DEFAULT_COMMANDS),
                "later_action_lease_active": False,
            }
        )
        preservation.pop("default_runtime_behavior_unchanged", None)
        preservation.pop("named_readonly_catalog_unchanged", None)
        preservation.pop("fixed_p330_commands", None)
    result["limitations"] = [
        "P345 changes the runtime behavior only for sequence-4 arbitrary ash: the fixed sequence-3/5 identity witnesses, wire framing, host-first OPEN and default kernel proof remain bound to P344.",
        "Sequence 4 is entered only after the fixed read-only child setup; missing namespace, snapshot, privilege, limit or seccomp support fails before ash execution.",
        "The child view contains one static BusyBox bind and six bounded text snapshots; full proc/sys, process roots/fd/mem/kcore, devices, storage and network are absent.",
        "The first qualification remains five same-descriptor bounded sessions with no idle, reopen, retry or later lease and mandatory rollback; this H0 build creates no device authority or F1 approval.",
    ]
    return result


def _rewrite_result(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    import os

    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")
    path.chmod(0o600)
    descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        offset = 0
        while offset < len(payload):
            amount = os.write(descriptor, payload[offset:])
            if amount <= 0:
                raise AuditError("short P3.45 result publication")
            offset += amount
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    path.chmod(0o400)
    return value


def _stable_worker_sources(result: dict[str, Any]) -> None:
    expected = {
        "p344-stock-candidate-build.py": (P344_BUILDER_SOURCE, P344_BUILDER_IDENTITY),
        "p344-artifact-identity.py": (P344_ARTIFACT_SOURCE, P344_ARTIFACT_IDENTITY),
        "p344-runtime.py": (P344_RUNTIME_SOURCE, P344_RUNTIME_IDENTITY),
        "p345-artifact-identity.py": (P345_ARTIFACT_SOURCE, P345_ARTIFACT_IDENTITY),
        "p345-runtime.py": (P345_RUNTIME_SOURCE, P345_RUNTIME_IDENTITY),
        "p345-observer.py": (
            P345_OBSERVER_SOURCE,
            P345_OBSERVER_IDENTITY,
        ),
        "p345-readonly-child.inc.c": (P345_CHILD_SOURCE, P345_CHILD_IDENTITY),
        "p345-adapter.py": (
            P345_ADAPTER_SOURCE,
            P345_ADAPTER_IDENTITY,
        ),
    }
    inputs = result.get("inputs", {})
    for name, (path, expected_identity) in expected.items():
        if name not in inputs:
            raise AuditError(f"P3.45 input receipt missing: {name}")
        if inputs[name] != expected_identity:
            raise AuditError(f"P3.45 input receipt differs: {name}")
        _stable_source(path, expected_identity, name)


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    global P345_AP_IDENTITY
    result = _ENGINE.audit_existing(Path(output_root).absolute())
    _stable_worker_sources(result)
    result = _fresh_result(result)
    artifact.P345_AP_IDENTITY = dict(result["phase2"]["candidate"]["a"]["ap_tar_md5"])
    P345_AP_IDENTITY = dict(artifact.P345_AP_IDENTITY)
    result["p345_ap_identity"] = dict(artifact.P345_AP_IDENTITY)
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
