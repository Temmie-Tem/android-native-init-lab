#!/usr/bin/env python3
"""Validate and publish the P3.32 host-only candidate-static receipt.

The checker reopens the single P3.32 build, both boot-only APs, the exact
unchanged stock rollback, and the materialized resident runtime.  It records
the consumed P3.30 result as predecessor evidence and emits no approval,
ready-manifest, device, or live-authority claim.
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
import s22plus_fyg8_p332_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p332_logical_resident_acm_observer as resident_observer  # noqa: E402
import s22plus_fyg8_p332_logical_resident_exec_runtime as resident_runtime  # noqa: E402
import s22plus_fyg8_p332_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p332_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P330_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p330_process_v2_candidate_static.py"
P330_STATIC_SOURCE_IDENTITY = {
    "size": 14_889,
    "sha256": "6f185fca8a07365a8a7197387d72408ecdff6384ead3d6023e61b01041a178d1",
}
P331_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p331_process_v2_candidate_static.py"
P331_STATIC_SOURCE_IDENTITY = {
    "size": 20_330,
    "sha256": "c23a972caaf257d0a25e972f2620d0e2818521db795a0d8167ea5ee547ac16b3",
}
BUILDER_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p332/"
    "stock-candidate-build-v1-20260903-10"
)
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
BUILDER_RESULT_IDENTITY: dict[str, Any] | None = None
P330_AP_IDENTITY = candidate_build.P330_AP_IDENTITY
P330_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7a730473a60cf454ba5a3df9dd992444196299b0397369531f3e171982ee8456",
}
P330_INIT_IDENTITY = {
    "size": 82_032,
    "sha256": "4d744d3def07a000d0d31f5abfa323372709d4cac0d6493d8696cb0a0e70a7a7",
}
P331_AP_IDENTITY = candidate_build.P331_AP_IDENTITY
P331_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "f2b955860a3676a5b8c94b60f34312420b2a9d034b8b6fad4063a4840dc8d30d",
}
P331_INIT_IDENTITY = {
    "size": 82_016,
    "sha256": "9432ac324ab20870143d0bcc04609036febfa8cec4e53e1bd1afac82868c28b2",
}
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p332/"
    "process-v2-candidate-static-20260903-01.json"
)
SCHEMA = "s22plus_fyg8_p332_process_v2_candidate_static_v1"
VERDICT = "PASS_P332_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = candidate_build.P332_RUN_ID_HEX
PREDECESSOR_RUN_ID = candidate_build.P331_RUN_ID_HEX
OVERLAY = adapter.P332_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
AUTH_KEY_SCHEMA = artifact.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = artifact.AUTH_KEY_SIZE
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_ALGORITHM = getattr(resident_runtime, "AUTH_ALGORITHM", "hmac-sha256")
PER_SESSION_RANDOM_NONCE = getattr(
    resident_runtime, "PER_SESSION_RANDOM_NONCE", True
)
AUTH_KEY_IDENTITY = dict(evidence.P332_AUTH_EXEC_AUTH_KEY_IDENTITY)


class StaticContractError(ValueError):
    """The exact P3.32 static closure is incomplete or changed."""


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


def _source_receipt(path: Path, label: str, maximum: int = 2 << 20) -> dict[str, Any]:
    payload = _stable(path, label, maximum, nlink=1)
    return {"path": _relative(path), **identity(payload)}


def _refresh_builder_result_identity() -> dict[str, Any]:
    global BUILDER_RESULT_IDENTITY
    BUILDER_RESULT_IDENTITY = identity(
        _stable(
            BUILDER_RESULT,
            "P3.32 builder result",
            4 << 20,
            mode=0o400,
            nlink=1,
        )
    )
    return BUILDER_RESULT_IDENTITY


def _validate_static_header(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise StaticContractError("P3.32 static result is not an object")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("target") != TARGET
        or value.get("run_id") != RUN_ID
        or value.get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("userspace_overlay_contract_id") != OVERLAY
        or value.get("source_contract_id") != PARENT_SOURCE
    ):
        raise StaticContractError("P3.32 static header differs")
    return value


def _validate_candidate(value: dict[str, Any], built: dict[str, Any]) -> None:
    candidate = value.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("a") != candidate.get("b"):
        raise StaticContractError("P3.32 A/B candidate differs")
    built_candidate = built.get("phase2", {}).get("candidate", {})
    if (
        candidate.get("byte_identical") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or candidate.get("a", {}).get("ap_tar_md5") in (P330_AP_IDENTITY, P331_AP_IDENTITY)
        or candidate.get("a", {}).get("ap_tar_md5")
        != built_candidate.get("a", {}).get("ap_tar_md5")
        or candidate.get("a", {}).get("package", {}).get("members")
        != ["boot.img.lz4"]
        or candidate.get("a", {}).get("package", {}).get("schema")
        != "s22plus_fyg8_p332_boot_only_logical_resident_package_v1"
    ):
        raise StaticContractError("P3.32 candidate identity differs")
    if candidate.get("image") in (P330_IMAGE_IDENTITY, P331_IMAGE_IDENTITY) or candidate.get("init") in (P330_INIT_IDENTITY, P331_INIT_IDENTITY):
        raise StaticContractError("P3.32 candidate repeats a consumed P3.30/P3.31 image")


def _validate_observer(value: dict[str, Any]) -> None:
    observer = value.get("observer_adapter")
    if (
        not isinstance(observer, dict)
        or observer.get("schema") != resident_observer.SCHEMA
        or observer.get("contract_id") != resident_observer.CONTRACT_ID
        or observer.get("host_only") is not True
        or observer.get("device_contact") is not False
        or observer.get("raw_rx_forwarded_before_classification") is not True
        or observer.get("caller_selected_command") is not False
        or observer.get("proof_command_count") != len(resident_runtime.DEFAULT_COMMANDS)
        or observer.get("commands")
        != [identity(item) for item in resident_runtime.DEFAULT_COMMANDS]
        or observer.get("session_cap") != resident_runtime.MAX_SESSIONS
        or observer.get("reconnect_cap") != resident_runtime.MAX_RECONNECTS
        or observer.get("fixed_heartbeat_only") is not False
        or observer.get("fixed_p330_commands") is not True
        or observer.get("same_tty_fd") is not True
        or observer.get("host_tty_close_reopen") is not False
        or observer.get("transport_reconnect") is not False
    ):
        raise StaticContractError("P3.32 resident observer binding differs")
    source = observer.get("source")
    runtime_source = observer.get("runtime_source")
    if (
        source
        != {
            "path": _relative(Path(resident_observer.__file__)),
            **candidate_build.OBSERVER_SOURCE_IDENTITY,
        }
        or runtime_source
        != {
            "path": _relative(Path(resident_runtime.__file__)),
            **candidate_build.RUNTIME_SOURCE_IDENTITY,
        }
    ):
        raise StaticContractError("P3.32 observer source identity differs")


def _validate_runtime(value: dict[str, Any]) -> None:
    repair = value.get("runtime_repair")
    if (
        not isinstance(repair, dict)
        or repair.get("contract_id") != resident_runtime.CONTRACT_ID
        or repair.get("run_id_hex") != RUN_ID
        or repair.get("command_policy") != "fixed_p330_commands_v1"
        or repair.get("caller_selected_command") is not False
        or repair.get("max_sessions") != resident_runtime.MAX_SESSIONS
        or repair.get("max_reconnects") != resident_runtime.MAX_RECONNECTS
        or repair.get("session_count") != resident_runtime.SESSION_COUNT
        or repair.get("session_transitions") != resident_runtime.SESSION_TRANSITIONS
        or repair.get("max_reconnects") != 0
        or repair.get("logical_session_transitions") != 1
        or repair.get("same_tty_fd") is not True
        or repair.get("close_open") is not False
        or repair.get("physical_reopen_count") != 0
        or repair.get("auth_key_path_published") is not False
    ):
        raise StaticContractError("P3.32 resident runtime binding differs")
    if value.get("authentication", {}).get("path_published") is not False:
        raise StaticContractError("P3.32 authentication path leaked")


def _validate_safety(value: dict[str, Any]) -> None:
    safety = value.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True:
        raise StaticContractError("P3.32 static authority projection differs")
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
            raise StaticContractError(f"P3.32 safety flag differs: {name}")


def _project(built: dict[str, Any]) -> dict[str, Any]:
    builder_result_identity = _refresh_builder_result_identity()
    phase2 = built.get("phase2")
    if not isinstance(phase2, dict):
        raise StaticContractError("P3.32 build phase is absent")
    candidate = phase2.get("candidate")
    userspace = phase2.get("userspace")
    if not isinstance(candidate, dict) or not isinstance(userspace, dict):
        raise StaticContractError("P3.32 candidate/userspace projection is absent")
    init = userspace.get("a", {}).get("init")
    child = userspace.get("a", {}).get("child")
    if not isinstance(init, dict) or not isinstance(child, dict):
        raise StaticContractError("P3.32 userspace identity is absent")

    candidate_projection = copy.deepcopy(candidate)
    candidate_projection.update(
        {
            "boot_only": True,
            "busybox": candidate.get("a", {}).get("busybox"),
            "child": child,
            "image": candidate.get("fixed_image_identity"),
            "init": init,
        }
    )
    candidate_projection["a"]["package"]["schema"] = (
        "s22plus_fyg8_p332_boot_only_logical_resident_package_v1"
    )
    candidate_projection["b"]["package"]["schema"] = (
        "s22plus_fyg8_p332_boot_only_logical_resident_package_v1"
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "target": TARGET,
        "run_id": RUN_ID,
        "predecessor_run_id": PREDECESSOR_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": OVERLAY,
        "profile": adapter.PROFILE,
        "authority_source": {
            "path": _relative(SELF_SOURCE),
            **identity(SELF_SOURCE.read_bytes()),
        },
        "builder_result": {
            "path": _relative(BUILDER_RESULT),
            **builder_result_identity,
        },
        "artifact_identity": {
            "run_id_hex": RUN_ID,
            "predecessor_run_id_rejected": PREDECESSOR_RUN_ID,
            "boot_only": True,
            "candidate_a": candidate.get("run_id_join", {}).get("a"),
            "candidate_b": candidate.get("run_id_join", {}).get("b"),
            "rollback": phase2.get("rollback", {}).get("artifact_identity"),
            "auth_key": AUTH_KEY_IDENTITY,
            "auth_key_path_published": False,
        },
        "adapter": adapter.audit(),
        "observer_adapter": {
            "schema": resident_observer.SCHEMA,
            "contract_id": resident_observer.CONTRACT_ID,
            "source": {
                "path": _relative(Path(resident_observer.__file__)),
                **candidate_build.OBSERVER_SOURCE_IDENTITY,
            },
            "runtime_source": {
                "path": _relative(Path(resident_runtime.__file__)),
                **candidate_build.RUNTIME_SOURCE_IDENTITY,
            },
            "wire_magic": resident_runtime.FRAME_MAGIC.decode("ascii"),
            "frame_header_size": resident_runtime.FRAME_HEADER_SIZE,
            "commands": [identity(item) for item in resident_runtime.DEFAULT_COMMANDS],
            "proof_command_count": len(resident_runtime.DEFAULT_COMMANDS),
            "max_commands": resident_runtime.MAX_COMMANDS,
            "caller_selected_command": False,
            "command_timeout_sec": resident_runtime.COMMAND_TIMEOUT_SEC,
            "max_output_bytes": resident_runtime.MAX_OUTPUT_BYTES,
            "auth_algorithm": AUTH_ALGORITHM,
            "auth_tag_size": resident_runtime.AUTH_TAG_SIZE,
            "auth_key_schema": artifact.AUTH_KEY_SCHEMA,
            "auth_key": AUTH_KEY_IDENTITY,
            "auth_key_path_published": False,
            "per_session_random_nonce": True,
            "fixed_heartbeat_only": False,
            "fixed_p330_commands": True,
            "session_cap": resident_runtime.MAX_SESSIONS,
            "reconnect_cap": resident_runtime.MAX_RECONNECTS,
            "host_only": True,
            "device_contact": False,
            "raw_rx_forwarded_before_classification": True,
            "interactive_pty": False,
            "same_tty_fd": True,
            "host_tty_close_reopen": False,
            "transport_reconnect": False,
        },
        "runtime_repair": copy.deepcopy(built.get("lineage", {}).get("runtime_repair")),
        "source_closure": {
            "busybox": _source_receipt(
                ROOT / "workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/busybox-aarch64-static-1.36.1",
                "P3.32 BusyBox",
                8 << 20,
            ),
            "p332_artifact_identity": _source_receipt(artifact.P332_ARTIFACT_SOURCE, "P3.32 artifact"),
            "p332_logical_resident_acm_observer": _source_receipt(Path(resident_observer.__file__), "P3.32 observer"),
            "p332_logical_resident_exec_runtime": _source_receipt(Path(resident_runtime.__file__), "P3.32 runtime"),
            "p332_stock_candidate_build": _source_receipt(candidate_build.SELF_SOURCE, "P3.32 builder"),
            "p332_stock_process_v2_adapter": _source_receipt(adapter.P332_ADAPTER_SOURCE, "P3.32 adapter"),
            "p331_candidate_static": {
                "path": _relative(P331_STATIC_SOURCE),
                **P331_STATIC_SOURCE_IDENTITY,
            },
            "rollback_ap": _source_receipt(ROLLBACK_AP, "P3.32 exact rollback AP", 64 << 20),
        },
        "authentication": {
            "required": True,
            "scheme": "auth-key-v1",
            "key": AUTH_KEY_IDENTITY,
            "path_published": False,
            "candidate_possession_implies_key_possession": True,
            "hardware_backed": False,
        },
        "candidate": candidate_projection,
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
    try:
        built = candidate_build.audit_existing(BUILDER_OUTPUT)
        value = _project(built)
        _validate_static_header(value)
        _validate_candidate(value, built)
        _validate_observer(value)
        _validate_runtime(value)
        _validate_safety(value)
        return value
    except StaticContractError:
        raise
    except Exception as exc:
        raise StaticContractError(f"P3.32 static result did not regenerate: {exc}") from exc


def validate_result(value: Any) -> dict[str, Any]:
    expected = build_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.32 static result does not regenerate")
    return value


def build_bound_result() -> dict[str, Any]:
    """P3.32 is already key-bound; its runtime-bound view is identical."""

    return build_result()


def validate_bound_result(value: Any) -> dict[str, Any]:
    expected = build_bound_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.32 bound static result does not regenerate")
    return value


def canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise StaticContractError("P3.32 value is not canonical JSON") from exc


def publish(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise StaticContractError("P3.32 static output already exists")
    direct.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    direct.parent.chmod(0o700)
    descriptor = os.open(
        direct,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("P3.32 static publication was short")
            offset += written
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(direct.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


if BUILDER_RESULT.exists():
    try:
        _refresh_builder_result_identity()
    except StaticContractError:
        # Import remains useful before the first host build; build_result()
        # performs the required fail-closed refresh when the output exists.
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        value = build_result()
        payload = canonical(value)
        if not args.audit_only:
            publish(output, payload)
    except (OSError, RuntimeError, StaticContractError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
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
