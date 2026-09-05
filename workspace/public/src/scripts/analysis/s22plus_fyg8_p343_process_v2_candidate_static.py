#!/usr/bin/env python3
"""Reopen the P343 boot-only candidate as an H0 static receipt.

The P343 builder owns byte production.  This wrapper reopens its immutable
result, binds the fresh idle/reuse observer and source closure, and emits no
approval, ready manifest, device action, or later-action lease.
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
import s22plus_fyg8_idle_reuse_probe as idle_probe  # noqa: E402
import s22plus_fyg8_p343_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p343_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p343_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p343_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p343_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
BUILDER_OUTPUT = Path(candidate_build.DEFAULT_OUTPUT_ROOT).absolute()
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p343/"
    "process-v2-candidate-static-20260905-01.json"
)
SCHEMA = evidence.P343_CANDIDATE_STATIC_SCHEMA
VERDICT = evidence.P343_CANDIDATE_STATIC_VERDICT
RUN_ID = candidate_build.P343_RUN_ID_HEX
PREDECESSOR_RUN_ID = candidate_build.P341_RUN_ID_HEX
TARGET = dict(candidate_build.TARGET)
AUTH_KEY_IDENTITY = dict(evidence.P343_AUTH_EXEC_AUTH_KEY_IDENTITY)


class StaticContractError(ValueError):
    """The exact P343 static closure is incomplete or changed."""


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
        raise StaticContractError("P343 static value is not canonical JSON") from exc


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
    nlink: int = 1,
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
        or before.st_nlink != nlink
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
        return path.absolute().relative_to(ROOT).as_posix()
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


def _candidate_projection(built: dict[str, Any]) -> dict[str, Any]:
    phase2 = built.get("phase2")
    if not isinstance(phase2, dict):
        raise StaticContractError("P343 builder phase-2 projection is absent")
    candidate = phase2.get("candidate")
    userspace = phase2.get("userspace")
    if not isinstance(candidate, dict) or not isinstance(userspace, dict):
        raise StaticContractError("P343 candidate/userspace projection is absent")
    user_a = userspace.get("a")
    if (
        not isinstance(user_a, dict)
        or not isinstance(user_a.get("init"), dict)
        or not isinstance(user_a.get("child"), dict)
    ):
        raise StaticContractError("P343 userspace identities are absent")
    join = candidate.get("run_id_join")
    if (
        not isinstance(candidate.get("a"), dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("ab_artifact_identity_equal") is not True
        or candidate.get("byte_identical") is not True
        or not isinstance(join, dict)
        or join.get("joined") is not True
        or join.get("run_id_hex") != RUN_ID
        or join.get("image_run_id_hex") != RUN_ID
        or join.get("init_run_id_hex") != RUN_ID
        or candidate.get("a", {}).get("ap_tar_md5") == artifact.P342_AP_IDENTITY
        or candidate.get("a", {}).get("package", {}).get("members")
        != ["boot.img.lz4"]
    ):
        raise StaticContractError("P343 candidate identity differs")
    result = copy.deepcopy(candidate)
    result.update(
        {
            "boot_only": True,
            "busybox": candidate["a"].get("busybox"),
            "child": user_a["child"],
            "image": candidate.get("fixed_image_identity"),
            "init": user_a["init"],
            "differs_from_consumed_p342": True,
            "same_fd_session_count": adapter.SAME_FD_SESSION_COUNT,
            "idle_seconds": adapter.IDLE_SECONDS,
            "total_session_count": adapter.INITIAL_SESSION_COUNT,
            "total_command_count": adapter.TOTAL_COMMANDS,
            "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
        }
    )
    if not isinstance(result.get("image"), dict):
        raise StaticContractError("P343 fixed Image identity is absent")
    for label in ("a", "b"):
        package = result[label].get("package")
        if not isinstance(package, dict):
            raise StaticContractError("P343 package projection is absent")
        package.update(
            {
                "schema": "s22plus_fyg8_p343_named_exploration_boot_only_package_v1",
                "verdict": "PASS_P343_NAMED_EXPLORATION_BOOT_ONLY_H0",
            }
        )
    return result


def _observer_projection() -> dict[str, Any]:
    value = dict(observer.audit_binding())
    observer_source = Path(observer.__file__).resolve()
    runtime_source = Path(runtime.__file__).resolve()
    capture_source = REVALIDATION / "s22plus_fyg8_open_failure_capture.py"
    idle_source = REVALIDATION / "s22plus_fyg8_idle_reuse_probe.py"
    value.update(
        {
            "source": {"path": _relative(observer_source), **identity(observer_source.read_bytes())},
            "runtime_source": {"path": _relative(runtime_source), **identity(runtime_source.read_bytes())},
            "capture_source": identity(capture_source.read_bytes()),
            "idle_reuse_source": {"path": _relative(idle_source), **identity(idle_source.read_bytes())},
            "commands": [identity(item) for item in runtime.DEFAULT_COMMANDS],
            "proof_command_count": len(runtime.DEFAULT_COMMANDS),
            "command_count_per_session": len(runtime.DEFAULT_COMMANDS),
            "initial_session_count": adapter.INITIAL_SESSION_COUNT,
            "initial_reconnect_count": adapter.INITIAL_RECONNECT_COUNT,
            "same_fd_session_count": adapter.SAME_FD_SESSION_COUNT,
            "idle_seconds": adapter.IDLE_SECONDS,
            "total_session_count": adapter.INITIAL_SESSION_COUNT,
            "total_command_count": adapter.TOTAL_COMMANDS,
            "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
            "physical_reopen_indexes": list(evidence.P343_PHYSICAL_REOPEN_INDEXES),
            "per_boot_identity_required": True,
            "open_read_branch_ordinals": dict(runtime.OPEN_READ_BRANCHES),
            "open_read_branch_count": len(runtime.OPEN_READ_BRANCHES),
            "open_header_word_stages": list(runtime.OPEN_HEADER_WORD_STAGES),
            "open_header_size": runtime.OPEN_HEADER_SIZE,
            "open_header_capture_best_effort": True,
            "resident_lease_schema": adapter.LEASE_SCHEMA,
            "resident_lease_duration_sec": adapter.LEASE_DURATION_SEC,
            "resident_lease_action_cap": adapter.LEASE_ACTION_CAP,
            "host_first_open": True,
            "host_open_before_banner": True,
            "device_banner_after_open": True,
            "stage_zero_after_banner": True,
            "open_parsed_after_stage_zero": True,
            "no_unsolicited_device_tx": True,
            "silent_no_peer_no_proof": True,
            "consumed_partial_open_no_replay": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_order_changed": True,
            "later_action_lease_active": False,
            "host_only": True,
            "device_contact": False,
            "interactive_pty": False,
            "same_tty_fd": True,
        }
    )
    return value


def _validate_runtime(built: dict[str, Any]) -> dict[str, Any]:
    repair = built.get("lineage", {}).get("runtime_repair")
    expected = built.get("source_closure", {}).get("s22plus_fyg8_p290_e3_runtime.inc.c")
    if not isinstance(repair, dict) or not isinstance(expected, dict):
        raise StaticContractError("P343 runtime repair/source receipt is absent")
    source = _stable(
        BUILDER_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c",
        "P343 runtime include",
        2 << 20,
        expected,
        mode=0o400,
    )
    try:
        checked = runtime.validate_p343_runtime(source)
    except Exception as exc:
        raise StaticContractError("P343 runtime include did not validate") from exc
    for name, required in {
        "host_first_open": True,
        "host_open_before_banner": True,
        "device_banner_after_open": True,
        "stage_zero_after_banner": True,
        "open_parsed_after_stage_zero": True,
        "no_unsolicited_device_tx": True,
        "silent_no_peer_no_proof": True,
        "consumed_partial_open_no_replay": True,
        "runtime_order_changed": True,
        "runtime_behavior_unchanged": False,
        "default_runtime_behavior_unchanged": True,
        "catalog_allowlist_expanded": True,
        "middle_command_allowlist": True,
        "initial_proof_default_action": "kernel",
        "successful_wire_exchange_unchanged": False,
        "retry_added": False,
        "timeout_changed": False,
    }.items():
        if checked.get(name) != required or repair.get(name) != required:
            raise StaticContractError(f"P343 runtime field differs: {name}")
    return copy.deepcopy(repair)


def _validate_safety(value: dict[str, Any]) -> None:
    safety = value.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True:
        raise StaticContractError("P343 static safety projection differs")
    for name in (
        "device_contact", "device_write", "odin_invoked", "odin_transfer",
        "flash", "partition_write", "live_authorized", "d0_authorized",
        "d1_authorized", "f1_authorized", "replay_authorized",
        "causal_result_allowed", "candidate_success",
    ):
        if safety.get(name) is not False:
            raise StaticContractError(f"P343 safety flag differs: {name}")


def build_result() -> dict[str, Any]:
    try:
        built = candidate_build.audit_existing(BUILDER_OUTPUT)
        if (
            built.get("schema") != candidate_build.SCHEMA
            or built.get("run_id_hex") != RUN_ID
            or built.get("target") != TARGET
            or built.get("scope", {}).get("tier") != "H0"
            or built.get("scope", {}).get("device_contact") is not False
        ):
            raise StaticContractError("P343 builder header or scope differs")
        candidate = _candidate_projection(built)
        adapter_value = adapter.audit()
        observer_value = _observer_projection()
        capture_path = REVALIDATION / "s22plus_fyg8_open_failure_capture.py"
        idle_path = REVALIDATION / "s22plus_fyg8_idle_reuse_probe.py"
        source_closure = {
            "latch": _source_receipt(
                BUILDER_OUTPUT / "module-bytes/s22plus_dwc3_event_latch.ko",
                "P343 latch module",
                8 << 20,
                built["module_bytes"]["s22plus_dwc3_event_latch.ko"],
            ),
            "p343_artifact_identity": _source_receipt(
                Path(artifact.__file__).resolve(), "P343 artifact identity"
            ),
            "p343_host_first_open": _source_receipt(
                runtime.HOST_FIRST_SOURCE, "P343 host-first OPEN helper"
            ),
            "p343_open_failure_capture": _source_receipt(
                capture_path, "P343 initial failure capture"
            ),
            "p343_open_read_branch_acm_observer": _source_receipt(
                Path(observer.__file__).resolve(), "P343 observer"
            ),
            "p343_open_read_branch_runtime": _source_receipt(
                Path(runtime.__file__).resolve(), "P343 runtime"
            ),
            "p343_idle_reuse_probe": _source_receipt(
                idle_path, "P343 idle-reuse probe"
            ),
            "p343_stock_candidate_build": _source_receipt(
                Path(candidate_build.__file__).resolve(), "P343 builder"
            ),
            "p343_stock_process_v2_adapter": _source_receipt(
                Path(adapter.__file__).resolve(), "P343 adapter"
            ),
            "p343_exploration_session": _source_receipt(
                REVALIDATION / "s22plus_fyg8_p343_exploration_session.py",
                "P343 exploration session",
            ),
            "p343_exploration_action": _source_receipt(
                REVALIDATION / "s22plus_fyg8_p343_exploration_action.py",
                "P343 exploration action",
            ),
            "p343_readonly_exploration": _source_receipt(
                REVALIDATION / "s22plus_fyg8_readonly_exploration.py",
                "P343 read-only exploration catalog",
            ),
            "p335_resident_session": _source_receipt(
                REVALIDATION / "s22plus_fyg8_p335_resident_session.py",
                "P335 resident session predecessor",
            ),
            "p335_resident_action": _source_receipt(
                REVALIDATION / "s22plus_fyg8_p335_resident_action.py",
                "P335 resident action predecessor",
            ),
            "rollback_ap": _source_receipt(
                ROLLBACK_AP, "P343 exact rollback AP", 64 << 20, ROLLBACK_IDENTITY
            ),
        }
        if observer_value.get("capture_source") != {
            key: source_closure["p343_open_failure_capture"][key]
            for key in ("size", "sha256")
        }:
            raise StaticContractError("P343 failure-capture source identity differs")
        if observer_value.get("idle_reuse_source") != source_closure["p343_idle_reuse_probe"]:
            raise StaticContractError("P343 idle-reuse source identity differs")
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
            "builder_result": {"path": _relative(BUILDER_RESULT), **identity(BUILDER_RESULT.read_bytes())},
            "artifact_identity": {
                "run_id_hex": RUN_ID,
                "predecessor_run_id_rejected": PREDECESSOR_RUN_ID,
                "predecessor_ap_identity_rejected": dict(artifact.P342_AP_IDENTITY),
                "boot_only": True,
                "candidate_a": candidate["run_id_join"]["a"],
                "candidate_b": candidate["run_id_join"]["b"],
                "rollback": phase2_rollback_identity(built),
                "auth_key_path_published": False,
            },
            "adapter": adapter_value,
            "observer_adapter": observer_value,
            "action_runner": None,
            "later_action_authorized": False,
            "later_action_lease_active": False,
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
            "host_first_open": True,
            "host_open_before_banner": True,
            "device_banner_after_open": True,
            "stage_zero_after_banner": True,
            "open_parsed_after_stage_zero": True,
            "no_unsolicited_device_tx": True,
            "silent_no_peer_no_proof": True,
            "consumed_partial_open_no_replay": True,
            "successful_wire_exchange_unchanged": False,
            "runtime_behavior_unchanged": False,
            "default_runtime_behavior_unchanged": True,
            "catalog_allowlist_expanded": True,
            "catalog_allowlist_actions": list(runtime.CATALOG_ACTIONS),
            "middle_command_allowlist": True,
            "initial_proof_default_action": "kernel",
            "runtime_order_changed": True,
            "same_fd_session_count": adapter.SAME_FD_SESSION_COUNT,
            "idle_seconds": adapter.IDLE_SECONDS,
            "total_session_count": adapter.INITIAL_SESSION_COUNT,
            "total_command_count": adapter.TOTAL_COMMANDS,
            "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
            "physical_reopen_indexes": list(evidence.P343_PHYSICAL_REOPEN_INDEXES),
            "idle_reuse": {
                "phase": idle_probe.CONTRACT_ID,
                "before_session_index": 2,
                "requested_seconds": adapter.IDLE_SECONDS,
                "elapsed_seconds_min": evidence.P343_IDLE_REUSE_MIN_ELAPSED_SECONDS,
                "elapsed_seconds_max": evidence.P343_IDLE_REUSE_MAX_ELAPSED_SECONDS,
            },
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
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P343 static result did not regenerate: {exc}") from exc


def phase2_rollback_identity(built: dict[str, Any]) -> dict[str, Any] | None:
    phase2 = built.get("phase2")
    if not isinstance(phase2, dict):
        return None
    rollback = phase2.get("rollback")
    if not isinstance(rollback, dict):
        return None
    value = rollback.get("artifact_identity")
    return dict(value) if isinstance(value, dict) else None


def validate_result(value: Any) -> dict[str, Any]:
    expected = build_result()
    if type(value) is not dict or canonical(value) != canonical(expected):
        raise StaticContractError("P343 static result differs from current closure")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    return validate_result(value)


def _publish(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise StaticContractError("P343 static result already exists")
    direct.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(
        direct,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise StaticContractError("P343 static publication was short")
            written += count
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(direct.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    value = build_result()
    if args.audit_only:
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")
    _publish(args.output, payload)
    print(json.dumps({"path": str(args.output.absolute()), **identity(payload)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
