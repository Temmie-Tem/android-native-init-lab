#!/usr/bin/env python3
"""Re-derive and publish the P3.35 host-only candidate-static receipt.

This is a narrow P3.34 static seam.  It exact-loads the reviewed P3.34
validator only for its stable-file and canonical-publication primitives, then
binds the fresh P3.35 builder result, runtime, observer, rollback and safety
projection.  It performs no build, device access, Odin invocation, approval,
or ready publication.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types
from collections.abc import Mapping
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p335_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p335_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p335_stock_process_v2_adapter as adapter  # noqa: E402
import device_action_f1_evidence_v2 as evidence  # noqa: E402

try:
    import s22plus_fyg8_p335_retained_listener_runtime as resident_runtime  # noqa: E402
except ModuleNotFoundError:
    resident_runtime = None
try:
    import s22plus_fyg8_p335_retained_listener_acm_observer as resident_observer  # noqa: E402
except ModuleNotFoundError:
    resident_observer = None


SELF_SOURCE = Path(__file__).resolve()
P334_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p334_process_v2_candidate_static.py"
P334_STATIC_SOURCE_IDENTITY = {
    "size": 21_943,
    "sha256": "80df64cd5ebbc83f3671f963d63c97a3bba70715ebe2d9547cc3ecca975487d3",
}
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
P335_BUILDER_RESULT_IDENTITY: dict[str, Any] = {
    "size": 56_292,
    "sha256": "f8c957ad36c4b2fcdff93bd5dc0fd9b79250ca5344b1264ec6ee6d736b00c397",
}
P334_RUN_ID_HEX = "c334f1e0a90b5e6d7c8a9b0c1d2e3f6b"
P335_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P334_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc",
}
P335_RUNTIME_SOURCE_IDENTITY = dict(candidate_build.P335_RUNTIME_SOURCE_IDENTITY)
P335_OBSERVER_SOURCE_IDENTITY = dict(candidate_build.P335_OBSERVER_SOURCE_IDENTITY)
P335_AP_IDENTITY: dict[str, Any] = {
    "size": 28_631_081,
    "sha256": "99a6299e8f54ccda5fbde896af045af34c15be1a03fa4b49ab3c76843b518b75",
}
P333_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "1a6036b688ae92c94f459aee66e06a817e767aa615c6a7a9cb2a22b7d13487b3",
}
P332_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "e1309080879700445b88cef08eb3becb4e57e524f5467979857fc79ee36a9a9d",
}
P331_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "729b33c3bad602e1d5863fa8cfa6a4bdf22f194a74d378f7417879897bf4d08d",
}
P330_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "f458498c1b33961a9a7049a3ad8e74d4ab67ab64e672ba20af21d074f418175b",
}
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p335/"
    "process-v2-candidate-static-20260904-04.json"
)
SCHEMA = "s22plus_fyg8_p335_process_v2_candidate_static_v1"
VERDICT = "PASS_P335_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = P335_RUN_ID_HEX
PREDECESSOR_RUN_ID = P334_RUN_ID_HEX
OVERLAY = adapter.P335_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_KEY_SCHEMA = artifact.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = artifact.AUTH_KEY_SIZE
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
AUTH_KEY_IDENTITY = dict(evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY)


class StaticContractError(ValueError):
    """The exact P3.35 static closure is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
    return (
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


def _stable(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise StaticContractError(f"{label} is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise StaticContractError(f"{label} identity differs")
    return payload


def _relative(path: Path) -> str:
    try:
        return str(path.absolute().relative_to(ROOT))
    except ValueError:
        return str(path.absolute())


def _source_receipt(
    path: Path,
    label: str,
    maximum: int = 2 << 20,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _stable(path, label, maximum, expected, nlink=1)
    return {"path": _relative(path), **identity(payload)}


def _load_p334_static() -> types.ModuleType | None:
    if resident_runtime is None or resident_observer is None:
        return None
    payload = _stable(
        P334_STATIC_SOURCE,
        "P3.34 candidate-static source",
        2 << 20,
        P334_STATIC_SOURCE_IDENTITY,
        nlink=1,
    )
    module = types.ModuleType("s22plus_fyg8_p334_static_bound_for_p335")
    module.__file__ = str(P334_STATIC_SOURCE)
    module.__package__ = ""
    aliases = {
        "s22plus_fyg8_p334_artifact_identity": artifact,
        "s22plus_fyg8_p334_stock_candidate_build": candidate_build,
        "s22plus_fyg8_p334_stock_process_v2_adapter": adapter,
        "s22plus_fyg8_p334_first_read_rc_runtime": resident_runtime,
        "s22plus_fyg8_p334_first_read_rc_acm_observer": resident_observer,
    }
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P334_STATIC_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise StaticContractError("P3.34 static source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    return module


_P334 = _load_p334_static()
if _P334 is not None:
    canonical = _P334.canonical
    publish = _P334.publish
else:
    canonical = None
    publish = None


def _observer_projection() -> dict[str, Any]:
    if resident_runtime is None or resident_observer is None:
        raise StaticContractError("P3.35 runtime/observer sources are unavailable")
    value = dict(resident_observer.audit_binding())
    value.update(
        {
            "source": {
                "path": _relative(Path(resident_observer.__file__)),
                **P335_OBSERVER_SOURCE_IDENTITY,
            },
            "runtime_source": {
                "path": _relative(Path(resident_runtime.__file__)),
                **P335_RUNTIME_SOURCE_IDENTITY,
            },
            "commands": [identity(item) for item in resident_runtime.DEFAULT_COMMANDS],
            "proof_command_count": len(resident_runtime.DEFAULT_COMMANDS),
            "caller_selected_command": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "initial_session_count": 2,
            "initial_reconnect_count": 1,
            "per_boot_identity_required": True,
            "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
            "resident_lease_duration_sec": 3_600,
            "resident_lease_action_cap": 16,
            "listener_wait_after_proof": True,
            "action_retry": False,
            "host_only": True,
            "device_contact": False,
            "raw_rx_forwarded_before_classification": True,
            "interactive_pty": False,
            "same_tty_fd": True,
            "host_tty_close_reopen": True,
            "transport_reconnect": True,
        }
    )
    return value


def _validate_header(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise StaticContractError("P3.35 static result is not an object")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("target") != TARGET
        or value.get("run_id") != RUN_ID
        or value.get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("userspace_overlay_contract_id") != OVERLAY
        or value.get("source_contract_id") != PARENT_SOURCE
    ):
        raise StaticContractError("P3.35 static header differs")
    return value


def _candidate_projection(built: dict[str, Any]) -> dict[str, Any]:
    phase2 = built.get("phase2")
    userspace = phase2.get("userspace") if isinstance(phase2, dict) else None
    candidate = phase2.get("candidate") if isinstance(phase2, dict) else None
    if not isinstance(candidate, dict) or not isinstance(userspace, dict):
        raise StaticContractError("P3.35 candidate/userspace projection is absent")
    init = userspace.get("a", {}).get("init")
    child = userspace.get("a", {}).get("child")
    if not isinstance(init, dict) or not isinstance(child, dict):
        raise StaticContractError("P3.35 userspace identity is absent")
    result = copy.deepcopy(candidate)
    result.update(
        {
            "boot_only": True,
            "busybox": candidate.get("a", {}).get("busybox"),
            "child": child,
            "image": candidate.get("fixed_image_identity"),
            "init": init,
        }
    )
    for label in ("a", "b"):
        result[label]["package"]["schema"] = (
            "s22plus_fyg8_p335_boot_only_attended_resident_package_v1"
        )
    return result


def _validate_candidate(value: dict[str, Any], built: dict[str, Any]) -> None:
    candidate = value.get("candidate")
    expected = built.get("phase2", {}).get("candidate", {})
    ap = P335_AP_IDENTITY
    if ap is None:
        ap = expected.get("a", {}).get("ap_tar_md5")
    if (
        not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or candidate.get("a", {}).get("ap_tar_md5") != ap
        or ap in (P334_AP_IDENTITY, P333_AP_IDENTITY, P332_AP_IDENTITY, P331_AP_IDENTITY, P330_AP_IDENTITY)
        or candidate.get("a", {}).get("ap_tar_md5") != expected.get("a", {}).get("ap_tar_md5")
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
        or candidate.get("a", {}).get("package", {}).get("schema")
        != "s22plus_fyg8_p335_boot_only_attended_resident_package_v1"
    ):
        raise StaticContractError("P3.35 candidate identity differs")


def _validate_observer(value: dict[str, Any]) -> None:
    observer = value.get("observer_adapter")
    expected = _observer_projection()
    if not isinstance(observer, dict):
        raise StaticContractError("P3.35 observer projection is absent")
    for key, expected_value in expected.items():
        if key in {"source", "runtime_source"}:
            continue
        if observer.get(key) != expected_value:
            raise StaticContractError(f"P3.35 observer field differs: {key}")


def _validate_runtime(value: dict[str, Any]) -> None:
    repair = value.get("runtime_repair")
    if resident_runtime is None or not isinstance(repair, dict):
        raise StaticContractError("P3.35 runtime binding is absent")
    checks = {
        "runtime_contract": resident_runtime.CONTRACT_ID,
        "run_id_hex": RUN_ID,
        "command_policy": "fixed_p335_three_commands_v1",
        "caller_selected_command": False,
        "session_count": 2,
        "reconnect_count": 1,
        "physical_reopen_count": 1,
        "same_tty_fd_initial_sessions": True,
        "listener": True,
        "listener_replays_commands": False,
        "per_boot_identity": True,
        "persistent_state": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "resident_lease_schema": "s22plus_fyg8_p335_resident_lease_v1",
        "resident_lease_duration_sec": 3_600,
        "resident_lease_action_cap": 16,
        "per_boot_identity_required": True,
    }
    for key, expected in checks.items():
        if repair.get(key) != expected:
            raise StaticContractError(f"P3.35 runtime field differs: {key}")


def _validate_safety(value: dict[str, Any]) -> None:
    safety = value.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True:
        raise StaticContractError("P3.35 static authority projection differs")
    for name in (
        "device_contact",
        "device_write",
        "odin_invoked",
        "odin_transfer",
        "flash",
        "partition_write",
        "live_authorized",
        "d0_authorized",
        "d1_authorized",
        "f1_authorized",
        "replay_authorized",
        "causal_result_allowed",
        "candidate_success",
    ):
        if safety.get(name) is not False:
            raise StaticContractError(f"P3.35 safety flag differs: {name}")


def _project(built: dict[str, Any]) -> dict[str, Any]:
    expected_builder = P335_BUILDER_RESULT_IDENTITY
    if expected_builder is None:
        expected_builder = identity(BUILDER_RESULT.read_bytes())
    _stable(
        BUILDER_RESULT,
        "P3.35 builder result",
        4 << 20,
        expected_builder,
        mode=0o400,
        nlink=1,
    )
    candidate = _candidate_projection(built)
    observer = _observer_projection()
    source_closure = {
        "busybox": _source_receipt(
            ROOT / "workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/busybox-aarch64-static-1.36.1",
            "P3.35 BusyBox",
            8 << 20,
        ),
        "p335_artifact_identity": _source_receipt(
            Path(artifact.__file__).resolve(), "P3.35 artifact identity"
        ),
        "p335_retained_listener_acm_observer": _source_receipt(
            Path(resident_observer.__file__).resolve(),
            "P3.35 observer",
            2 << 20,
            P335_OBSERVER_SOURCE_IDENTITY,
        ),
        "p335_retained_listener_runtime": _source_receipt(
            Path(resident_runtime.__file__).resolve(),
            "P3.35 runtime",
            2 << 20,
            P335_RUNTIME_SOURCE_IDENTITY,
        ),
        "p335_stock_candidate_build": _source_receipt(
            Path(candidate_build.__file__).resolve(), "P3.35 builder"
        ),
        "p335_stock_process_v2_adapter": _source_receipt(
            Path(adapter.__file__).resolve(), "P3.35 adapter"
        ),
        "p334_candidate_static": _source_receipt(
            P334_STATIC_SOURCE, "P3.34 candidate static", 2 << 20
        ),
        "rollback_ap": _source_receipt(ROLLBACK_AP, "P3.35 exact rollback AP", 64 << 20),
    }
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "run_id": RUN_ID,
        "predecessor_run_id": PREDECESSOR_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": OVERLAY,
        "profile": adapter.PROFILE,
        "authority_source": {"path": _relative(SELF_SOURCE), **identity(SELF_SOURCE.read_bytes())},
        "builder_result": {"path": _relative(BUILDER_RESULT), **expected_builder},
        "artifact_identity": {
            "run_id_hex": RUN_ID,
            "predecessor_run_id_rejected": PREDECESSOR_RUN_ID,
            "boot_only": True,
            "candidate_a": candidate.get("run_id_join", {}).get("a"),
            "candidate_b": candidate.get("run_id_join", {}).get("b"),
            "rollback": built.get("phase2", {}).get("rollback", {}).get("artifact_identity"),
            "auth_key_path_published": False,
        },
        "adapter": adapter.audit(),
        "observer_adapter": observer,
        "runtime_repair": copy.deepcopy(built.get("lineage", {}).get("runtime_repair")),
        "source_closure": source_closure,
        "authentication": {
            "required": True,
            "scheme": "auth-key-v1",
            "key": AUTH_KEY_IDENTITY,
            "path_published": False,
            "candidate_possession_implies_key_possession": True,
            "hardware_backed": False,
        },
        "candidate": candidate,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "d0_authorized": False,
            "d1_authorized": False,
            "f1_authorized": False,
            "replay_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
        "approval_created": False,
        "ready_manifest_created": False,
        "run_manifest_created": False,
    }


def build_result() -> dict[str, Any]:
    if resident_runtime is None or resident_observer is None or _P334 is None:
        raise StaticContractError("P3.35 static dependencies are unavailable")
    try:
        built = candidate_build.audit_existing(BUILDER_OUTPUT)
        value = _project(built)
        _validate_header(value)
        _validate_candidate(value, built)
        _validate_observer(value)
        _validate_runtime(value)
        _validate_safety(value)
        return value
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P3.35 static result did not regenerate: {exc}") from exc


def validate_result(value: Any) -> dict[str, Any]:
    expected = build_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.35 static result does not regenerate")
    return value


def build_bound_result() -> dict[str, Any]:
    return build_result()


def validate_bound_result(value: Any) -> dict[str, Any]:
    expected = build_bound_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.35 bound static result does not regenerate")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        value = build_result()
        if canonical is None:
            raise StaticContractError("P3.34 canonical publisher is unavailable")
        payload = canonical(value)
        if not args.audit_only:
            publish(output, payload)
    except (OSError, RuntimeError, StaticContractError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "verdict": VERDICT,
                "output": str(output),
                "identity": identity(payload),
                "created": not args.audit_only,
                "device_contact": False,
                "live_authorized": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
