#!/usr/bin/env python3
"""Re-derive and publish the P3.34 host-only candidate-static receipt.

P3.34 is an exact-loaded P3.33 static seam.  The only fresh closure is the
P3.34 builder output and its first-console-return observer/runtime/adapter;
this module performs no build, device access, Odin invocation, approval, or
ready publication.
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
import s22plus_fyg8_p334_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_acm_observer as resident_observer  # noqa: E402
import s22plus_fyg8_p334_first_read_rc_runtime as resident_runtime  # noqa: E402
import s22plus_fyg8_p334_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p334_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P333_STATIC_SOURCE = ANALYSIS / "s22plus_fyg8_p333_process_v2_candidate_static.py"
P333_STATIC_SOURCE_IDENTITY = {
    "size": 21_030,
    "sha256": "7b28dbdeed67d223543069e83922b3912ae0fb5517dd384048b7393e2fe3efa9",
}
BUILDER_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p334/"
    "stock-candidate-build-v1-20260904-01"
)
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
BUILDER_RESULT_IDENTITY = {
    "size": 50_133,
    "sha256": "765b70a794503e9819940926af3e975334368f551c5c766f5fd754fa8ea2868a",
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
P334_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "7f1ecf568b474575d5258c91beeb9d721a3fee6ba527b3c88083ebf16af70cc2",
}
P334_INIT_IDENTITY = {
    "size": 82_264,
    "sha256": "f4218f326d63b13f8ae6cea3034b3570476f6dd58ac31f525ecdf651ff9abdc9",
}
P334_BOOT_LZ4_IDENTITY = {
    "size": 28_622_828,
    "sha256": "4988f20b2be2ee16ab0463dcf0315d8b2cdf06a8f2432f53a71f9ed497e97b51",
}
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p334/"
    "process-v2-candidate-static-20260904-01.json"
)
SCHEMA = "s22plus_fyg8_p334_process_v2_candidate_static_v1"
VERDICT = "PASS_P334_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
RUN_ID = resident_runtime.P334_RUN_ID_HEX
PREDECESSOR_RUN_ID = candidate_build.P333_RUN_ID_HEX
OVERLAY = adapter.P334_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
AUTH_KEY_SCHEMA = artifact.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = artifact.AUTH_KEY_SIZE
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH
AUTH_ALGORITHM = getattr(resident_runtime, "AUTH_ALGORITHM", "hmac-sha256")
AUTH_KEY_IDENTITY = dict(evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY)


class StaticContractError(ValueError):
    """The exact P3.34 static closure is incomplete or changed."""


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


def _p333_static_source_receipt() -> dict[str, Any]:
    payload = _stable(
        P333_STATIC_SOURCE,
        "P3.33 candidate-static source",
        2 << 20,
        P333_STATIC_SOURCE_IDENTITY,
        nlink=1,
    )
    return {"path": _relative(P333_STATIC_SOURCE), **identity(payload)}


def _validate_header(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise StaticContractError("P3.34 static result is not an object")
    if (
        value.get("schema") != SCHEMA
        or value.get("verdict") != VERDICT
        or value.get("target") != TARGET
        or value.get("run_id") != RUN_ID
        or value.get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("userspace_overlay_contract_id") != OVERLAY
        or value.get("source_contract_id") != PARENT_SOURCE
    ):
        raise StaticContractError("P3.34 static header differs")
    return value


def _candidate_projection(built: dict[str, Any]) -> dict[str, Any]:
    phase2 = built.get("phase2")
    userspace = phase2.get("userspace") if isinstance(phase2, dict) else None
    candidate = phase2.get("candidate") if isinstance(phase2, dict) else None
    if not isinstance(candidate, dict) or not isinstance(userspace, dict):
        raise StaticContractError("P3.34 candidate/userspace projection is absent")
    init = userspace.get("a", {}).get("init")
    child = userspace.get("a", {}).get("child")
    if not isinstance(init, dict) or not isinstance(child, dict):
        raise StaticContractError("P3.34 userspace identity is absent")
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
    package_schema = "s22plus_fyg8_p334_boot_only_first_console_return_package_v1"
    for label in ("a", "b"):
        result[label]["package"]["schema"] = package_schema
    return result


def _validate_candidate(value: dict[str, Any], built: dict[str, Any]) -> None:
    candidate = value.get("candidate")
    expected = built.get("phase2", {}).get("candidate", {})
    if (
        not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("boot_only") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or candidate.get("a", {}).get("ap_tar_md5") != P334_AP_IDENTITY
        or candidate.get("a", {}).get("ap_tar_md5") == P333_AP_IDENTITY
        or candidate.get("a", {}).get("ap_tar_md5") == P332_AP_IDENTITY
        or candidate.get("a", {}).get("ap_tar_md5") == P331_AP_IDENTITY
        or candidate.get("a", {}).get("ap_tar_md5") == P330_AP_IDENTITY
        or candidate.get("a", {}).get("ap_tar_md5") != expected.get("a", {}).get("ap_tar_md5")
        or candidate.get("a", {}).get("package", {}).get("members") != ["boot.img.lz4"]
        or candidate.get("a", {}).get("package", {}).get("schema")
        != "s22plus_fyg8_p334_boot_only_first_console_return_package_v1"
        or candidate.get("image") != P334_IMAGE_IDENTITY
        or candidate.get("init") != P334_INIT_IDENTITY
        or candidate.get("a", {}).get("boot_img_lz4") != P334_BOOT_LZ4_IDENTITY
    ):
        raise StaticContractError("P3.34 candidate identity differs")


def _observer_projection() -> dict[str, Any]:
    source_identity = {
        "size": 5_523,
        "sha256": "4644eede3280c29c5619cb5b8e70a0af50b2993ab05de1df9e3f92632e860399",
    }
    runtime_identity = {
        "size": 14_564,
        "sha256": "05d21599c95a40abc679c3e5bd7ee0447dd708f52ac0734b53902f27f434c323",
    }
    return {
        "schema": resident_observer.SCHEMA,
        "contract_id": resident_observer.CONTRACT_ID,
        "source": {
            "path": _relative(Path(resident_observer.__file__)),
            **source_identity,
        },
        "runtime_source": {
            "path": _relative(Path(resident_runtime.__file__)),
            **runtime_identity,
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
        "auth_key_schema": AUTH_KEY_SCHEMA,
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
        "physical_reopen_count": resident_observer.PHYSICAL_REOPEN_COUNT,
        "entry_diagnostic_stage": resident_runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
        "entry_diagnostic_count": 2,
        "entry_diagnostic_before_console": True,
        "diagnostics_non_authoritative": True,
        "first_console_return_checkpoint_only": True,
        "first_console_return_detail_prefix": resident_runtime.P334_DETAIL_PREFIX,
        "first_console_return_detail_sentinel": resident_runtime.P334_DETAIL_SENTINEL,
        "first_read_attribution_requires_stage0_without_stage1": True,
    }


def _validate_observer(value: dict[str, Any]) -> None:
    observer = value.get("observer_adapter")
    expected = _observer_projection()
    if not isinstance(observer, dict):
        raise StaticContractError("P3.34 observer projection is absent")
    for key, expected_value in expected.items():
        if observer.get(key) != expected_value:
            raise StaticContractError(f"P3.34 observer field differs: {key}")


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
        or repair.get("logical_session_transitions") != 1
        or repair.get("same_tty_fd") is not True
        or repair.get("close_open") is not False
        or repair.get("physical_reopen_count") != 0
        or repair.get("entry_diagnostic_stage") != 0
        or repair.get("entry_diagnostic_count") != 2
        or repair.get("entry_diagnostic_before_console") is not True
        or repair.get("first_console_return_checkpoint_only") is not True
        or repair.get("first_console_return_prefix") != resident_runtime.P334_DETAIL_PREFIX
        or repair.get("first_console_return_sentinel") != resident_runtime.P334_DETAIL_SENTINEL
        or repair.get("first_read_interpretation_requires_stage0_without_stage1") is not True
        or repair.get("console_body_changed") is not False
        or repair.get("auth_key_path_published") is not False
    ):
        raise StaticContractError("P3.34 runtime binding differs")


def _validate_safety(value: dict[str, Any]) -> None:
    safety = value.get("safety")
    if not isinstance(safety, dict) or safety.get("host_only") is not True:
        raise StaticContractError("P3.34 static authority projection differs")
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
            raise StaticContractError(f"P3.34 safety flag differs: {name}")


def _project(built: dict[str, Any]) -> dict[str, Any]:
    _stable(BUILDER_RESULT, "P3.34 builder result", 4 << 20, BUILDER_RESULT_IDENTITY, mode=0o400, nlink=1)
    candidate = _candidate_projection(built)
    observer = _observer_projection()
    source_closure = {
        "busybox": _source_receipt(
            ROOT / "workspace/private/inputs/s22plus_fyg8_p326/busybox/bin/busybox-aarch64-static-1.36.1",
            "P3.34 BusyBox",
            8 << 20,
        ),
        "p334_artifact_identity": _source_receipt(
            Path(artifact.__file__).resolve(), "P3.34 artifact identity"
        ),
        "p334_first_read_rc_acm_observer": _source_receipt(
            Path(resident_observer.__file__).resolve(), "P3.34 observer"
        ),
        "p334_first_read_rc_runtime": _source_receipt(
            Path(resident_runtime.__file__).resolve(), "P3.34 runtime"
        ),
        "p334_stock_candidate_build": _source_receipt(
            Path(candidate_build.__file__).resolve(), "P3.34 builder"
        ),
        "p334_stock_process_v2_adapter": _source_receipt(
            Path(adapter.__file__).resolve(), "P3.34 adapter"
        ),
        "p333_candidate_static": _p333_static_source_receipt(),
        "rollback_ap": _source_receipt(ROLLBACK_AP, "P3.34 exact rollback AP", 64 << 20),
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
        "authority_source": {
            "path": _relative(SELF_SOURCE),
            **identity(SELF_SOURCE.read_bytes()),
        },
        "builder_result": {
            "path": _relative(BUILDER_RESULT),
            **BUILDER_RESULT_IDENTITY,
        },
        "artifact_identity": {
            "run_id_hex": RUN_ID,
            "predecessor_run_id_rejected": PREDECESSOR_RUN_ID,
            "boot_only": True,
            "candidate_a": candidate.get("run_id_join", {}).get("a"),
            "candidate_b": candidate.get("run_id_join", {}).get("b"),
            "rollback": built.get("phase2", {}).get("rollback", {}).get("artifact_identity"),
            "auth_key": AUTH_KEY_IDENTITY,
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
        raise StaticContractError(f"P3.34 static result did not regenerate: {exc}") from exc


def validate_result(value: Any) -> dict[str, Any]:
    expected = build_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.34 static result does not regenerate")
    return value


def build_bound_result() -> dict[str, Any]:
    return build_result()


def validate_bound_result(value: Any) -> dict[str, Any]:
    expected = build_bound_result()
    if type(value) is not dict or value != expected:
        raise StaticContractError("P3.34 bound static result does not regenerate")
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
        raise StaticContractError("P3.34 value is not canonical JSON") from exc


def publish(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise StaticContractError("P3.34 static output already exists")
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
                raise StaticContractError("P3.34 static publication was short")
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
