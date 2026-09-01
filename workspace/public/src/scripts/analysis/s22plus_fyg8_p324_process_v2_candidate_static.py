#!/usr/bin/env python3
"""Build the P3.24 Process-v2 candidate-static receipt, host-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p324_acm_primary_runtime as acm  # noqa: E402
import s22plus_fyg8_p324_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p324_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p324_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
P323_OUTPUT = candidate_build.P323_OUTPUT
P323_RUNTIME = P323_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
P324_RUNTIME = BUILDER_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p324/"
    "process-v2-candidate-static-20260901-03.json"
)

SCHEMA = "s22plus_fyg8_p324_process_v2_candidate_static_v1"
VERDICT = "PASS_P324_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
RUN_ID = adapter.P324_RUN_ID_HEX
PREDECESSOR_RUN_ID = adapter.P323_RUN_ID_HEX
OVERLAY = adapter.P324_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID

ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


class StaticContractError(ValueError):
    """The exact P3.24 host result or artifact closure differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise StaticContractError("P324 static path escaped repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = 1,
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

    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns,
        )

    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
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
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise StaticContractError(f"{label} has duplicate keys")
            value[key] = item
        return value

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StaticContractError(f"{label} is not strict JSON") from exc
    if type(value) is not dict:
        raise StaticContractError(f"{label} is not an object")
    return value


def canonical(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def receipt(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
) -> dict[str, Any]:
    payload = stable_bytes(path, label, maximum, expected, mode=mode)
    return {"path": relative(path), **identity(payload)}


def _builder(*, runtime_bound: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = stable_bytes(
        BUILDER_RESULT,
        "P324 builder result",
        2 * 1024 * 1024,
        mode=0o400,
    )
    value = decode(payload, "P324 builder result")
    if not runtime_bound:
        try:
            if candidate_build.audit_existing(BUILDER_OUTPUT) != value:
                raise StaticContractError("P324 builder audit differs")
        except StaticContractError:
            raise
        except Exception as exc:
            raise StaticContractError("P324 builder did not reopen") from exc
    if (
        value.get("schema") != candidate_build.SCHEMA
        or value.get("verdict") != candidate_build.VERDICT
        or value.get("target") != TARGET
        or value.get("run_id_hex") != RUN_ID
        or value.get("lineage", {}).get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("scope") != {
            "tier": "H0", "host_only": True, "device_contact": False,
            "adb_commands": 0, "odin_invocations": 0, "candidate_transfers": 0,
            "rollback_transfers": 0, "live_authority_created": False,
            "replay": False,
        }
    ):
        raise StaticContractError("P324 builder header or scope differs")
    candidate = value.get("phase2", {}).get("candidate")
    userspace = value.get("phase2", {}).get("userspace")
    rollback = value.get("phase2", {}).get("rollback")
    if (
        not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
        or candidate.get("differs_from_consumed_p323") is not True
        or not isinstance(userspace, dict)
        or userspace.get("a") != userspace.get("b")
        or not isinstance(rollback, dict)
        or rollback.get("untouched") is not True
        or rollback.get("identity") != ROLLBACK_IDENTITY
    ):
        raise StaticContractError("P324 builder artifact contract differs")
    return value, {"path": relative(BUILDER_RESULT), **identity(payload)}


def _real_artifacts(builder: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    image_meta = builder.get("phase2", {}).get("candidate", {}).get("fixed_image_identity")
    image = stable_bytes(
        BUILDER_OUTPUT / "inputs/fixed-Image",
        "P324 Image",
        64 * 1024 * 1024,
        image_meta,
        mode=0o400,
    )
    init_meta = builder["phase2"]["userspace"]["a"]["init"]
    child_meta = builder["phase2"]["userspace"]["a"]["child"]
    init = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/init", "P324 init", 2 * 1024 * 1024,
        init_meta, mode=0o400,
    )
    child = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/s22-e1-child", "P324 child",
        2 * 1024 * 1024, child_meta, mode=0o400,
    )
    joined: list[dict[str, Any]] = []
    for name in ("a", "b"):
        try:
            joined.append(
                artifact.inspect_ap(
                    BUILDER_OUTPUT / f"candidate-{name}/odin4/AP.tar.md5",
                    expected_run_id=artifact.P324_RUN_ID,
                    expected_image=image,
                    expected_init=init,
                    expected_child=child,
                    expected_ap=builder["phase2"]["candidate"][name]["ap_tar_md5"],
                    label=f"P324 candidate {name.upper()} AP",
                )
            )
        except artifact.ArtifactIdentityError as exc:
            raise StaticContractError(str(exc)) from exc
    if joined[0] != joined[1]:
        raise StaticContractError("P324 A/B AP join differs")
    try:
        rollback = artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    except artifact.ArtifactIdentityError as exc:
        raise StaticContractError(str(exc)) from exc
    return joined, rollback


def _runtime_receipt(builder: dict[str, Any]) -> dict[str, Any]:
    before = stable_bytes(P323_RUNTIME, "P323 runtime", 2 * 1024 * 1024, mode=0o400)
    expected_after = builder.get("source_closure", {}).get(
        "s22plus_fyg8_p290_e3_runtime.inc.c"
    )
    after = stable_bytes(
        P324_RUNTIME,
        "P324 runtime",
        2 * 1024 * 1024,
        expected_after,
        mode=0o400,
    )
    try:
        value = acm.validate_transform(before, after) | {
            "before_identity": identity(before),
            "after_identity": identity(after),
        }
    except acm.AcmPrimaryError as exc:
        raise StaticContractError("P324 ACM-primary runtime differs") from exc
    if value != builder.get("lineage", {}).get("runtime_repair"):
        raise StaticContractError("P324 runtime receipt differs")
    return value


def build_result(*, runtime_bound: bool = False) -> dict[str, Any]:
    builder, builder_receipt = _builder(runtime_bound=runtime_bound)
    joined, rollback = _real_artifacts(builder)
    runtime = _runtime_receipt(builder)
    try:
        lineage = adapter.bind_exact_sources()
        acceptance = adapter.validate_acceptance_item(adapter.acceptance_fixture())
    except Exception as exc:
        raise StaticContractError("P324 adapter did not reopen") from exc
    if (
        lineage.get("run_id") != RUN_ID
        or lineage.get("predecessor_run_id_rejected") != PREDECESSOR_RUN_ID
        or lineage.get("overlay_contract_id") != OVERLAY
        or acceptance.get("run_id") != RUN_ID
        or acceptance.get("userspace_overlay_contract_id") != OVERLAY
        or acceptance.get("candidate_success") is not False
    ):
        raise StaticContractError("P324 adapter binding differs")
    candidate = builder["phase2"]["candidate"]
    userspace = builder["phase2"]["userspace"]
    sources = {
        "p324_candidate_static": receipt(SELF_SOURCE, "P324 static source", 2 * 1024 * 1024),
        "p324_stock_candidate_build": receipt(candidate_build.SELF_SOURCE, "P324 builder source", 2 * 1024 * 1024),
        "p324_stock_process_v2_adapter": receipt(candidate_build.P324_ADAPTER_SOURCE, "P324 adapter source", 2 * 1024 * 1024),
        "p324_artifact_identity": receipt(candidate_build.P324_ARTIFACT_SOURCE, "P324 artifact source", 2 * 1024 * 1024),
        "p324_acm_primary_runtime": receipt(candidate_build.P324_ACM_SOURCE, "P324 ACM source", 2 * 1024 * 1024),
        "p323_p322_carrier_reanalysis": receipt(candidate_build.P323_CARRIER_SOURCE, "P323 Carrier reanalysis", 2 * 1024 * 1024),
        "rollback_ap": receipt(ROLLBACK_AP, "P324 rollback AP", 64 * 1024 * 1024, ROLLBACK_IDENTITY),
    }
    if userspace.get("a") != userspace.get("b"):
        raise StaticContractError("P324 userspace A/B bytes differ")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority_source": sources["p324_candidate_static"],
        "target": TARGET,
        "profile": adapter.PROFILE,
        "run_id": RUN_ID,
        "predecessor_run_id": PREDECESSOR_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": OVERLAY,
        "builder_result": builder_receipt,
        "candidate": {
            "a": candidate["a"],
            "b": candidate["b"],
            "byte_identical": True,
            "boot_only": True,
            "image": candidate.get("fixed_image_identity"),
            "init": userspace["a"]["init"],
            "child": userspace["a"]["child"],
            "run_id_join": {
                "run_id_hex": RUN_ID,
                "a": joined[0],
                "b": joined[1],
                "joined": True,
            },
        },
        "adapter": {
            "lineage": lineage,
            "acceptance": acceptance,
            "source": sources["p324_stock_process_v2_adapter"],
        },
        "artifact_identity": {
            "candidate_a": joined[0],
            "candidate_b": joined[1],
            "rollback": rollback,
        },
        "runtime_repair": runtime,
        "source_closure": sources,
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
    expected = build_result(runtime_bound=False)
    if type(value) is not dict or value != expected:
        raise StaticContractError("P324 static result does not regenerate")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    expected = build_result(runtime_bound=True)
    if type(value) is not dict or value != expected:
        raise StaticContractError("P324 bound static result differs")
    return value


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise StaticContractError("P324 static output already exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("P324 static publication was short")
            offset += written
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_nlink != 1
            or state.st_size != len(payload)
            or stat.S_IMODE(state.st_mode) != 0o400
        ):
            raise StaticContractError("P324 static publication identity differs")
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
            "live_authorized": False,
        }, sort_keys=True))
        return 0
    except (OSError, RuntimeError, StaticContractError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
