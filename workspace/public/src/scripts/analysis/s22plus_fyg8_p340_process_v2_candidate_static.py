#!/usr/bin/env python3
"""Reopen the P340 boot-only build as a host-only static receipt.

P340 reuses the consumed P339 Process-v2 shape while binding the fresh
identity-only artifact, runtime, observer, adapter, and initial collector.
This module only reads immutable host inputs and can publish one private
0400 JSON receipt.  It never contacts a device or creates F1 authority.
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
from collections.abc import Mapping
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import s22plus_fyg8_p340_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p340_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p340_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p340_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p340_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
BUILDER_RESULT_IDENTITY = {
    "size": 71_170,
    "sha256": "f145ed1f55b78ad85b15d112e8c3d1849b792a6d6fbc3dc1435ea3c3404f8454",
}
P339_AP_IDENTITY = dict(artifact.P339_AP_IDENTITY)
P340_RUN_ID_HEX = artifact.P340_RUN_ID_HEX
P339_PREDECESSOR_RUN_ID_HEX = artifact.P339_PREDECESSOR_RUN_ID_HEX
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p340/"
    "process-v2-candidate-static-20260905-01.json"
)
SCHEMA = "s22plus_fyg8_p340_process_v2_candidate_static_v1"
VERDICT = "PASS_P340_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = P340_RUN_ID_HEX
PREDECESSOR_RUN_ID = P339_PREDECESSOR_RUN_ID_HEX
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_KEY_IDENTITY = dict(evidence.P340_AUTH_EXEC_AUTH_KEY_IDENTITY)
AUTH_KEY_SCHEMA = evidence.P339_AUTH_EXEC_AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = evidence.P339_AUTH_EXEC_AUTH_KEY_SIZE


class StaticContractError(ValueError):
    """The exact P340 static closure is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise StaticContractError("P340 static value is not canonical JSON") from exc


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


def _publish(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise StaticContractError("P340 static result already exists")
    direct.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        direct,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            count = os.write(descriptor, payload[offset:])
            if count <= 0:
                raise StaticContractError("P340 static publication was short")
            offset += count
        os.fchmod(descriptor, 0o400)
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_nlink != 1
            or state.st_size != len(payload)
            or stat.S_IMODE(state.st_mode) != 0o400
        ):
            raise StaticContractError("P340 static publication identity differs")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(
        direct.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    )
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _candidate_projection(built: dict[str, Any]) -> dict[str, Any]:
    phase2 = built.get("phase2")
    if not isinstance(phase2, dict):
        raise StaticContractError("P340 phase-2 projection is absent")
    userspace = phase2.get("userspace")
    candidate = phase2.get("candidate")
    if not isinstance(userspace, dict) or not isinstance(candidate, dict):
        raise StaticContractError("P340 candidate/userspace projection is absent")
    user_a = userspace.get("a")
    if (
        not isinstance(user_a, dict)
        or not isinstance(user_a.get("init"), dict)
        or not isinstance(user_a.get("child"), dict)
    ):
        raise StaticContractError("P340 userspace identities are absent")
    if (
        candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or candidate.get("a", {}).get("ap_tar_md5") == P339_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members")
        != ["boot.img.lz4"]
    ):
        raise StaticContractError("P340 candidate identity differs")
    result = copy.deepcopy(candidate)
    result.update(
        {
            "boot_only": True,
            "busybox": candidate["a"].get("busybox"),
            "child": user_a["child"],
            "image": candidate.get("fixed_image_identity"),
            "init": user_a["init"],
        }
    )
    for label in ("a", "b"):
        package = result[label].get("package")
        if not isinstance(package, dict):
            raise StaticContractError("P340 package projection is absent")
        package.update(
            {
                "schema": "s22plus_fyg8_p340_boot_only_open_header_capture_package_v1",
                "verdict": "PASS_P340_DETERMINISTIC_BOOT_ONLY_OPEN_HEADER_CAPTURE_H0",
            }
        )
    return result


def _observer_projection() -> dict[str, Any]:
    value = dict(observer.audit_binding())
    runtime_source = Path(runtime.__file__).resolve()
    observer_source = Path(observer.__file__).resolve()
    value.update(
        {
            "source": {"path": _relative(observer_source), **identity(observer_source.read_bytes())},
            "runtime_source": {"path": _relative(runtime_source), **identity(runtime_source.read_bytes())},
            "commands": [identity(item) for item in runtime.DEFAULT_COMMANDS],
            "proof_command_count": len(runtime.DEFAULT_COMMANDS),
            "caller_selected_command": False,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
            "initial_session_count": 3,
            "initial_reconnect_count": 1,
            "per_boot_identity_required": True,
            "open_read_branch_ordinals": {
                str(key): label for key, label in runtime.OPEN_READ_BRANCHES.items()
            },
            "open_read_branch_count": len(runtime.OPEN_READ_BRANCHES),
            "open_header_word_stages": list(runtime.OPEN_HEADER_WORD_STAGES),
            "open_header_size": runtime.OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
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


def _validate_runtime(built: dict[str, Any]) -> dict[str, Any]:
    repair = built.get("lineage", {}).get("runtime_repair")
    if not isinstance(repair, dict):
        raise StaticContractError("P340 runtime repair receipt is absent")
    predecessor, _ = candidate_build._predecessor()
    source = candidate_build._stable(
        candidate_build.P339_OUTPUT
        / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
        "P339 runtime source for P340 static",
        2 << 20,
        predecessor["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"],
        mode=0o400,
        nlink=1,
    )
    key = runtime.predecessor._materialized_key(source)
    transformed = runtime.transform_runtime_include(source, key)
    expected = candidate_build._runtime_receipt(source, transformed)
    if repair != expected:
        raise StaticContractError("P340 runtime repair receipt differs")
    return copy.deepcopy(repair)


def _validate_safety(value: dict[str, Any]) -> None:
    safety = value.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True:
        raise StaticContractError("P340 static authority projection differs")
    for name in (
        "device_contact", "device_write", "odin_invoked", "odin_transfer",
        "flash", "partition_write", "live_authorized", "d0_authorized",
        "d1_authorized", "f1_authorized", "replay_authorized",
        "causal_result_allowed", "candidate_success",
    ):
        if safety.get(name) is not False:
            raise StaticContractError(f"P340 safety flag differs: {name}")


def _project(built: dict[str, Any]) -> dict[str, Any]:
    _stable(BUILDER_RESULT, "P340 builder result", 4 << 20, BUILDER_RESULT_IDENTITY, mode=0o400)
    candidate = _candidate_projection(built)
    adapter_value = adapter.audit()
    observer_value = _observer_projection()
    capture_source = Path(observer.capture.__file__).resolve()
    source_closure = {
        "p340_artifact_identity": _source_receipt(Path(artifact.__file__).resolve(), "P340 artifact identity"),
        "p340_open_read_branch_runtime": _source_receipt(Path(runtime.__file__).resolve(), "P340 runtime"),
        "p340_open_read_branch_acm_observer": _source_receipt(Path(observer.__file__).resolve(), "P340 observer"),
        "p340_open_failure_capture": _source_receipt(capture_source, "P340 initial collector"),
        "p340_stock_candidate_build": _source_receipt(Path(candidate_build.__file__).resolve(), "P340 builder"),
        "p340_stock_process_v2_adapter": _source_receipt(Path(adapter.__file__).resolve(), "P340 adapter"),
        "latch": _source_receipt(
            BUILDER_OUTPUT / "module-bytes/s22plus_dwc3_event_latch.ko",
            "P340 latch module",
            8 << 20,
            built["module_bytes"]["s22plus_dwc3_event_latch.ko"],
        ),
        "rollback_ap": _source_receipt(ROLLBACK_AP, "P340 exact rollback AP", 64 << 20, ROLLBACK_IDENTITY),
    }
    if observer_value.get("capture_source") != identity(capture_source.read_bytes()):
        raise StaticContractError("P340 collector source identity differs")
    runtime_repair = _validate_runtime(built)
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
            "candidate_a": candidate["run_id_join"]["a"],
            "candidate_b": candidate["run_id_join"]["b"],
            "rollback": built.get("phase2", {}).get("rollback", {}).get("artifact_identity"),
            "auth_key_path_published": False,
        },
        "adapter": adapter_value,
        "observer_adapter": observer_value,
        "action_runner": None,
        "later_action_authorized": False,
        "runtime_repair": runtime_repair,
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
    _validate_safety(value)
    return value


def build_result() -> dict[str, Any]:
    try:
        built = candidate_build.audit_existing(BUILDER_OUTPUT)
        if built.get("schema") != "s22plus-fyg8-p340-stock-candidate-build-v1" or built.get("run_id_hex") != RUN_ID:
            raise StaticContractError("P340 builder header differs")
        return _project(built)
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P340 static result did not regenerate: {exc}") from exc


def validate_result(value: Any) -> dict[str, Any]:
    expected = build_result()
    if type(value) is not dict or canonical(value) != canonical(expected):
        raise StaticContractError("P340 static result does not regenerate")
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
            stored = _stable(output, "P340 stored static result", 4 << 20, mode=0o400)
            if stored != payload:
                raise StaticContractError("P340 stored static result differs")
        else:
            _publish(output, payload)
    except (OSError, RuntimeError, StaticContractError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT, "output": str(output), "identity": identity(payload), "created": not args.audit_only, "device_contact": False, "live_authorized": False}, sort_keys=True))
    return 0


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    raise SystemExit(main())
