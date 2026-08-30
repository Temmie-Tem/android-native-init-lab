#!/usr/bin/env python3
"""Bind the P3.21 artifact-joined candidate to a thin H0 static contract.

This is the P3.21 successor to the larger P3.20 static ladder.  It reopens
the already-built P3.21 result, the exact P3.21 adapter, and the real AP
identity join.  It creates no approval, manifest, device contact, or live
authority; Process-v2 promotion remains a separate step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p321_artifact_identity as artifact_identity  # noqa: E402
import s22plus_fyg8_p321_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p321_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p321/"
    "process-v2-candidate-static-20260831-02.json"
)
SCHEMA = "s22plus_fyg8_p321_process_v2_candidate_static_v1"
VERDICT = "PASS_P321_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P321_RUN_ID = adapter.P321_RUN_ID_HEX
P320_RUN_ID = adapter.PREDECESSOR_P320_RUN_ID.hex()
OVERLAY = adapter.P321_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
ROLLBACK_IDENTITY = candidate_build.P319_ROLLBACK_IDENTITY


class StaticContractError(ValueError):
    """The P3.21 candidate-static contract cannot be trusted."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise StaticContractError("P321 static path escaped repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    maximum: int = 128 * 1024 * 1024,
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
    before_id = (
        before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
        before.st_uid, before.st_gid, before.st_size, before.st_mtime_ns,
        before.st_ctime_ns,
    )
    inside_id = (
        inside.st_dev, inside.st_ino, inside.st_mode, inside.st_nlink,
        inside.st_uid, inside.st_gid, inside.st_size, inside.st_mtime_ns,
        inside.st_ctime_ns,
    )
    after_id = (
        after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
        after.st_uid, after.st_gid, after.st_size, after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before_id != inside_id
        or before_id != after_id
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
        or (expected is not None and identity(payload) != dict(expected))
    ):
        raise StaticContractError(f"{label} identity differs")
    return payload


def decode(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise StaticContractError(f"{label} has a duplicate key")
            result[key] = item
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StaticContractError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise StaticContractError(f"{label} is not an object")
    return value


def canonical(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")


def _load_source(path: Path, name: str) -> tuple[types.ModuleType, bytes]:
    source = stable_bytes(path, f"P321 {name} source", 8 * 1024 * 1024)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise StaticContractError(f"P321 {name} source failed to load") from exc
    return module, source


def _receipt(path: Path, label: str, maximum: int = 128 * 1024 * 1024) -> dict[str, Any]:
    payload = stable_bytes(path, label, maximum)
    return {"path": relative(path), **identity(payload)}


def _builder_result(
    *, runtime_bound: bool = False
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    output = candidate_build.DEFAULT_OUTPUT_ROOT
    path = output / "result.json"
    payload = stable_bytes(path, "P321 builder result", 4 * 1024 * 1024, mode=0o400, nlink=1)
    value = decode(payload, "P321 builder result")
    if not runtime_bound:
        try:
            audited = candidate_build.audit_existing(output)
        except Exception as exc:
            raise StaticContractError("P321 builder result did not reopen") from exc
        if audited != value:
            raise StaticContractError("P321 builder audit result differs")
    return value, _receipt(path, "P321 builder result receipt", 4 * 1024 * 1024), payload


def _validate_builder(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != candidate_build.SCHEMA
        or value.get("verdict") != candidate_build.VERDICT
        or value.get("target") != TARGET
        or value.get("run_id_hex") != P321_RUN_ID
    ):
        raise StaticContractError("P321 builder header differs")
    if value.get("scope") != {
        "tier": "H0",
        "host_only": True,
        "device_contact": False,
        "adb_commands": 0,
        "odin_invocations": 0,
        "candidate_transfers": 0,
        "rollback_transfers": 0,
        "live_authority_created": False,
        "replay": False,
    }:
        raise StaticContractError("P321 builder scope differs")
    phase2 = value.get("phase2")
    if not isinstance(phase2, dict) or phase2.get("built") is not True:
        raise StaticContractError("P321 builder Phase-2 result is incomplete")
    candidate = phase2.get("candidate")
    if not isinstance(candidate, dict) or (
        candidate.get("byte_identical") is not True
        or candidate.get("fixed_image") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
        or candidate.get("diagnostic_absent") is not True
        or candidate.get("overlay_members") != ["lib/modules/s22plus_dwc3_event_latch.ko"]
        or candidate.get("run_id_join", {}).get("joined") is not True
    ):
        raise StaticContractError("P321 candidate package closure differs")
    join = candidate["run_id_join"]
    if (
        join.get("image_run_id_hex") != P321_RUN_ID
        or join.get("init_run_id_hex") != P321_RUN_ID
        or join.get("a") != join.get("b")
    ):
        raise StaticContractError("P321 Image/init A/B join differs")
    rollback = phase2.get("rollback")
    if not isinstance(rollback, dict) or rollback.get("identity") != ROLLBACK_IDENTITY or rollback.get("untouched") is not True:
        raise StaticContractError("P321 rollback identity differs")


def build_result(*, runtime_bound: bool = False) -> dict[str, Any]:
    builder, builder_receipt, _builder_payload = _builder_result(
        runtime_bound=runtime_bound
    )
    _validate_builder(builder)
    adapter_lineage = adapter.bind_exact_sources()
    acceptance = adapter.validate_acceptance_item(adapter.acceptance_fixture())
    if (
        adapter_lineage.get("run_id") != P321_RUN_ID
        or adapter_lineage.get("predecessor_run_id_rejected") != P320_RUN_ID
        or acceptance.get("run_id") != P321_RUN_ID
        or acceptance.get("userspace_overlay_contract_id") != OVERLAY
    ):
        raise StaticContractError("P321 adapter identity differs")
    candidate = builder["phase2"]["candidate"]
    artifact_a = candidate["run_id_join"]["a"]
    artifact_b = candidate["run_id_join"]["b"]
    source_closure = {
        "p321_candidate_static": _receipt(SELF_SOURCE, "P321 static source", 4 * 1024 * 1024),
        "p321_stock_candidate_build": _receipt(candidate_build.SELF_SOURCE, "P321 builder source", 4 * 1024 * 1024),
        "p321_stock_process_v2_adapter": _receipt(candidate_build.P321_ADAPTER_SOURCE, "P321 adapter source", 4 * 1024 * 1024),
        "p321_artifact_identity": _receipt(candidate_build.P321_IDENTITY_SOURCE, "P321 artifact identity source", 4 * 1024 * 1024),
        "p319_fixed_image": {"path": relative(candidate_build.P319_FIXED_IMAGE), **candidate_build.P319_IMAGE_IDENTITY},
        "p319_rollback_ap": {"path": relative(candidate_build.P319_ROLLBACK_AP), **candidate_build.P319_ROLLBACK_IDENTITY},
    }
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority_source": _receipt(SELF_SOURCE, "P321 static source", 4 * 1024 * 1024),
        "target": TARGET,
        "profile": adapter.PROFILE,
        "run_id": P321_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": OVERLAY,
        "builder_result": builder_receipt,
        "candidate": {
            "a": candidate["a"],
            "b": candidate["b"],
            "byte_identical": candidate["byte_identical"],
            "boot_only": candidate["one_boot_img_lz4_member"],
            "image": builder["inputs"]["fixed-Image"],
            "init": builder["phase2"]["userspace"]["a"]["init"],
            "child": builder["phase2"]["userspace"]["a"]["child"],
            "run_id_join": {"run_id_hex": P321_RUN_ID, "a": artifact_a, "b": artifact_b, "joined": True},
        },
        "adapter": {
            "lineage": adapter_lineage,
            "acceptance": acceptance,
            "source": _receipt(adapter.P320_ADAPTER_SOURCE, "P320 adapter delegate", 4 * 1024 * 1024),
        },
        "artifact_identity": {
            "image_transform": builder["lineage"]["image_transform"],
            "base_boot_replacement": candidate["base_boot_replacement"],
            "candidate_a": artifact_a,
            "candidate_b": artifact_b,
            "a_b_equal": artifact_a == artifact_b,
            "rollback": builder["phase2"]["rollback"]["artifact_identity"],
        },
        "source_closure": source_closure,
        "ready_manifest_created": False,
        "run_manifest_created": False,
        "approval_created": False,
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
    }


def validate_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StaticContractError("P321 static result is not an object")
    expected = build_result(runtime_bound=False)
    if value != expected:
        raise StaticContractError("P321 static result does not regenerate exactly")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    """Reopen immutable live inputs without rerunning the host build audit."""

    if not isinstance(value, dict):
        raise StaticContractError("P321 static result is not an object")
    expected = build_result(runtime_bound=True)
    if value != expected:
        raise StaticContractError("P321 runtime-bound static result differs")
    return value


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise StaticContractError("P321 static output already exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o400)
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("P321 static publication was short")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
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
        print(json.dumps({
            "schema": SCHEMA,
            "verdict": VERDICT,
            "output": str(output),
            "identity": identity(payload),
            "created": not args.audit_only,
            "device_contact": False,
            "ready_manifest_created": False,
            "live_authorized": False,
        }, sort_keys=True))
        return 0
    except (OSError, StaticContractError, RuntimeError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
