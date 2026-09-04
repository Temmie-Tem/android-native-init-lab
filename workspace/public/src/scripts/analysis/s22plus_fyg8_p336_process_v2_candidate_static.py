#!/usr/bin/env python3
"""Publish the P3.36 host-only candidate-static receipt.

This validator reopens the fresh P3.36 builder result and exact-loads the
reviewed P3.35 static seam only for canonical JSON/no-clobber publication.
The changed closure is explicit: P336 artifact identity, adapter, runtime,
observer, named action runner/activation, builder, the P335 static predecessor,
and the unchanged exact rollback.  No device, ADB, Odin, approval, transfer,
or live authority is created.
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

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_fyg8_p336_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p336_long_idle_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p336_long_idle_action as action  # noqa: E402
import s22plus_fyg8_p336_long_idle_runtime as runtime  # noqa: E402
import s22plus_fyg8_p336_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p336_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P335_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p335_process_v2_candidate_static.py"
P335_STATIC_SOURCE_IDENTITY = {
    "size": 20_870,
    "sha256": "16a7e4d629823b68d41f3baa3e0a10b9a6a7ebe0566b62c2315a8d823eb41df1",
}
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
# Updated only when a new no-clobber builder ordinal is promoted.  Keeping the
# identity here makes static reopening fail closed on stale or mixed outputs.
BUILDER_RESULT_IDENTITY = {
    "size": 56_894,
    "sha256": "e5581e4b1685ab4b90d9e14ab31301d681e173615fa05e08f8521928e7527437",
}
P335_RUN_ID_HEX = "c335f1e0a90b5e6d7c8a9b0c1d2e3f5b"
P336_RUN_ID_HEX = "c336f1e0a90b5e6d7c8a9b0c1d2e3f4b"
P335_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "99a6299e8f54ccda5fbde896af045af34c15be1a03fa4b49ab3c76843b518b75",
}
P334_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc",
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
    "workspace/private/outputs/s22plus_fyg8_p336/"
    "process-v2-candidate-static-20260904-05.json"
)
SCHEMA = "s22plus_fyg8_p336_process_v2_candidate_static_v1"
VERDICT = "PASS_P336_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = P336_RUN_ID_HEX
PREDECESSOR_RUN_ID = P335_RUN_ID_HEX
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_KEY_IDENTITY = dict(evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY)


class StaticContractError(ValueError):
    """The exact P3.36 static closure is incomplete or changed."""


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
    payload = _stable(path, label, maximum, expected)
    return {"path": _relative(path), **identity(payload)}


def _load_p335_static() -> types.ModuleType:
    payload = _stable(
        P335_STATIC_SOURCE,
        "P3.35 candidate-static source",
        2 << 20,
        P335_STATIC_SOURCE_IDENTITY,
    )
    module = types.ModuleType("s22plus_fyg8_p335_static_bound_for_p336")
    module.__file__ = str(P335_STATIC_SOURCE)
    module.__package__ = ""
    aliases = {
        "s22plus_fyg8_p335_artifact_identity": artifact,
        "s22plus_fyg8_p335_stock_candidate_build": candidate_build,
        "s22plus_fyg8_p335_stock_process_v2_adapter": adapter,
        "s22plus_fyg8_p335_retained_listener_runtime": runtime,
        "s22plus_fyg8_p335_retained_listener_acm_observer": observer,
    }
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P335_STATIC_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise StaticContractError("P3.35 static source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    return module


_P335 = _load_p335_static()
canonical = _P335.canonical
publish = _P335.publish


def _observer_projection() -> dict[str, Any]:
    value = dict(observer.audit_binding())
    value.update(
        {
            "source": {
                "path": _relative(P336_OBSERVER_SOURCE),
                **P336_OBSERVER_SOURCE_IDENTITY,
            },
            "runtime_source": {
                "path": _relative(P336_RUNTIME_SOURCE),
                **P336_RUNTIME_SOURCE_IDENTITY,
            },
            "commands": [identity(item) for item in runtime.DEFAULT_COMMANDS],
            "proof_command_count": len(runtime.DEFAULT_COMMANDS),
            "caller_selected_command": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
            "initial_session_count": 3,
            "initial_reconnect_count": 1,
            "per_boot_identity_required": True,
            "long_idle_host_resync": True,
            "open_before_resync": True,
            "max_preamble_pairs": observer.MAX_PREAMBLE_PAIRS,
            "max_resync_bytes": observer.MAX_RESYNC_BYTES,
            "resident_lease_schema": adapter.LEASE_SCHEMA,
            "resident_lease_duration_sec": 3_600,
            "resident_lease_action_cap": 16,
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


P336_RUNTIME_SOURCE = Path(runtime.__file__).resolve()
P336_OBSERVER_SOURCE = Path(observer.__file__).resolve()
P336_ACTION_SOURCE = Path(action.__file__).resolve()
P336_ACTION_BINDING = action.ACTIVATION
P336_RUNTIME_SOURCE_IDENTITY = dict(runtime.identity(P336_RUNTIME_SOURCE.read_bytes()))
P336_OBSERVER_SOURCE_IDENTITY = dict(observer.identity(P336_OBSERVER_SOURCE.read_bytes()))
P336_ACTION_SOURCE_IDENTITY = dict(action.identity(P336_ACTION_SOURCE.read_bytes()))


def _candidate_projection(built: dict[str, Any]) -> dict[str, Any]:
    phase2 = built.get("phase2")
    if not isinstance(phase2, dict):
        raise StaticContractError("P3.36 phase-2 projection is absent")
    userspace = phase2.get("userspace")
    candidate = phase2.get("candidate")
    if not isinstance(userspace, dict) or not isinstance(candidate, dict):
        raise StaticContractError("P3.36 candidate/userspace projection is absent")
    a = userspace.get("a")
    if not isinstance(a, dict) or not isinstance(a.get("init"), dict) or not isinstance(a.get("child"), dict):
        raise StaticContractError("P3.36 userspace identities are absent")
    result = copy.deepcopy(candidate)
    result.update(
        {
            "boot_only": True,
            "busybox": candidate.get("a", {}).get("busybox"),
            "child": a["child"],
            "image": candidate.get("fixed_image_identity"),
            "init": a["init"],
        }
    )
    for label in ("a", "b"):
        result[label]["package"].update(
            {
                "schema": "s22plus_fyg8_p336_boot_only_long_idle_package_v1",
                "verdict": "PASS_P336_DETERMINISTIC_BOOT_ONLY_LONG_IDLE_H0",
            }
        )
    return result


def _validate_candidate(value: dict[str, Any], built: dict[str, Any]) -> None:
    candidate = value.get("candidate")
    expected = built.get("phase2", {}).get("candidate", {})
    if not isinstance(candidate, dict):
        raise StaticContractError("P3.36 candidate is absent")
    ap = candidate.get("a", {}).get("ap_tar_md5")
    if (
        candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or ap != expected.get("a", {}).get("ap_tar_md5")
        or ap in (
            P335_AP_IDENTITY,
            P334_AP_IDENTITY,
            P333_AP_IDENTITY,
            P332_AP_IDENTITY,
            P331_AP_IDENTITY,
            P330_AP_IDENTITY,
        )
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
        or candidate.get("a", {}).get("package", {}).get("schema")
        != "s22plus_fyg8_p336_boot_only_long_idle_package_v1"
    ):
        raise StaticContractError("P3.36 candidate identity differs")


def _validate_runtime(value: dict[str, Any], built: dict[str, Any]) -> None:
    repair = value.get("runtime_repair")
    expected = built.get("lineage", {}).get("runtime_repair")
    if not isinstance(repair, dict) or repair != expected:
        raise StaticContractError("P3.36 runtime repair receipt differs")
    checks = {
        "runtime_contract": runtime.CONTRACT_ID,
        "run_id_hex": RUN_ID,
        "input_lineage": "p335-runtime-include",
        "command_policy": "fixed_p335_three_commands_v1",
        "caller_selected_command": False,
        "initial_session_count": 3,
        "initial_reconnect_count": 1,
        "fixed_p330_commands": True,
        "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
        "long_idle_host_resync": True,
        "later_action_open_before_resync": True,
        "per_boot_identity_required": True,
        "listener_replays_commands": False,
        "persistent_state": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
    }
    for key, expected_value in checks.items():
        if repair.get(key) != expected_value:
            raise StaticContractError(f"P3.36 runtime field differs: {key}")


def _validate_safety(value: dict[str, Any]) -> None:
    safety = value.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True:
        raise StaticContractError("P3.36 static authority projection differs")
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
            raise StaticContractError(f"P3.36 safety flag differs: {name}")


def _project(built: dict[str, Any]) -> dict[str, Any]:
    _stable(BUILDER_RESULT, "P3.36 builder result", 4 << 20, BUILDER_RESULT_IDENTITY, mode=0o400)
    static_candidate = _candidate_projection(built)
    ap = static_candidate["a"]["ap_tar_md5"]
    action_activation = action.validate_activation(require_pass=False)
    source_closure = {
        "busybox": _source_receipt(
            ROOT / "workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/busybox-aarch64-static-1.36.1",
            "P3.36 BusyBox",
            8 << 20,
        ),
        "p336_artifact_identity": _source_receipt(
            Path(artifact.__file__).resolve(), "P3.36 artifact identity"
        ),
        "p336_long_idle_acm_observer": _source_receipt(
            P336_OBSERVER_SOURCE, "P3.36 observer", 2 << 20, P336_OBSERVER_SOURCE_IDENTITY
        ),
        "p336_long_idle_runtime": _source_receipt(
            P336_RUNTIME_SOURCE, "P3.36 runtime", 2 << 20, P336_RUNTIME_SOURCE_IDENTITY
        ),
        "p336_long_idle_action": _source_receipt(
            P336_ACTION_SOURCE, "P3.36 action runner", 2 << 20, P336_ACTION_SOURCE_IDENTITY
        ),
        "p336_long_idle_action_activation": _source_receipt(
            P336_ACTION_BINDING, "P3.36 action activation", 2 << 20
        ),
        "p336_stock_candidate_build": _source_receipt(
            Path(candidate_build.__file__).resolve(), "P3.36 builder"
        ),
        "p336_stock_process_v2_adapter": _source_receipt(
            Path(adapter.__file__).resolve(), "P3.36 adapter"
        ),
        "p335_candidate_static": _source_receipt(
            P335_STATIC_SOURCE, "P3.35 candidate static", 2 << 20, P335_STATIC_SOURCE_IDENTITY
        ),
        "rollback_ap": _source_receipt(ROLLBACK_AP, "P3.36 exact rollback AP", 64 << 20, ROLLBACK_IDENTITY),
    }
    value = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "run_id": RUN_ID,
        "predecessor_run_id": PREDECESSOR_RUN_ID,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
        "profile": adapter.PROFILE,
        "authority_source": {"path": _relative(SELF_SOURCE), **identity(SELF_SOURCE.read_bytes())},
        "builder_result": {"path": _relative(BUILDER_RESULT), **BUILDER_RESULT_IDENTITY},
        "artifact_identity": {
            "run_id_hex": RUN_ID,
            "predecessor_run_id_rejected": PREDECESSOR_RUN_ID,
            "boot_only": True,
            "candidate_a": static_candidate.get("run_id_join", {}).get("a"),
            "candidate_b": static_candidate.get("run_id_join", {}).get("b"),
            "rollback": built.get("phase2", {}).get("rollback", {}).get("artifact_identity"),
            "auth_key_path_published": False,
        },
        "adapter": adapter.audit(),
        "observer_adapter": _observer_projection(),
        "action_runner": {
            "source": {"path": _relative(P336_ACTION_SOURCE), **P336_ACTION_SOURCE_IDENTITY},
            "activation": action_activation["receipt"],
            "activation_path": _relative(P336_ACTION_BINDING),
            "independent_review": action_activation["value"].get("independent_review"),
            "device_contact": False,
            "live_authorized": False,
        },
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
        "candidate": static_candidate,
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
    _validate_candidate(value, built)
    _validate_runtime(value, built)
    _validate_safety(value)
    return value


def build_result() -> dict[str, Any]:
    try:
        built = candidate_build.audit_existing(BUILDER_OUTPUT)
        if built.get("schema") != "s22plus-fyg8-p336-stock-candidate-build-v1" or built.get("run_id_hex") != RUN_ID:
            raise StaticContractError("P3.36 builder header differs")
        return _project(built)
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P3.36 static result did not regenerate: {exc}") from exc


def validate_result(value: Any) -> dict[str, Any]:
    expected = build_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.36 static result does not regenerate")
    return value


def build_bound_result() -> dict[str, Any]:
    return build_result()


def validate_bound_result(value: Any) -> dict[str, Any]:
    return validate_result(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        value = build_result()
        payload = canonical(value)
        if args.audit_only:
            stored = _stable(output, "P3.36 stored static result", 4 << 20)
            if stored != payload:
                raise StaticContractError("P3.36 stored static result differs")
        else:
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


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    raise SystemExit(main())
