#!/usr/bin/env python3
"""Build the P3.27 Process-v2 candidate-static receipt (host-only)."""

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

import s22plus_fyg8_p327_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p327_framed_acm_observer as observer_adapter  # noqa: E402
import s22plus_fyg8_p327_framed_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p327_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p327_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
P326_RUNTIME = candidate_build.P326_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
P327_RUNTIME = BUILDER_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p327/"
    "process-v2-candidate-static-20260902-01.json"
)

SCHEMA = "s22plus_fyg8_p327_process_v2_candidate_static_v1"
VERDICT = "PASS_P327_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
RUN_ID = adapter.P327_RUN_ID_HEX
PREDECESSOR_RUN_ID = adapter.P326_RUN_ID_HEX
OVERLAY = adapter.P327_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


class StaticContractError(ValueError):
    pass


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def canonical(value: Any) -> bytes:
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


def decode(payload: bytes, label: str) -> dict[str, Any]:
    def unique(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise StaticContractError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StaticContractError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise StaticContractError(f"{label} is not an object")
    return value


def stable_bytes(
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
    inode = lambda value: (  # noqa: E731
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
        or (expected is not None and identity(payload) != dict(expected))
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
    ):
        raise StaticContractError(f"{label} identity differs")
    return payload


def receipt(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {"path": str(path.relative_to(ROOT)), **identity(stable_bytes(path, label, maximum, expected))}


def _builder(*, runtime_bound: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = stable_bytes(BUILDER_RESULT, "P327 builder result", 2 << 20, mode=0o400)
    value = decode(payload, "P327 builder result")
    if not runtime_bound:
        try:
            if candidate_build.audit_existing(BUILDER_OUTPUT) != value:
                raise StaticContractError("P327 builder audit differs")
        except StaticContractError:
            raise
        except Exception as exc:
            raise StaticContractError("P327 builder did not reopen") from exc
    candidate = value.get("phase2", {}).get("candidate")
    userspace = value.get("phase2", {}).get("userspace")
    rollback = value.get("phase2", {}).get("rollback")
    if (
        value.get("schema") != candidate_build.SCHEMA
        or value.get("verdict") != candidate_build.VERDICT
        or value.get("target") != TARGET
        or value.get("run_id_hex") != RUN_ID
        or value.get("lineage", {}).get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("scope", {}).get("device_contact") is not False
        or value.get("scope", {}).get("live_authority_created") is not False
        or value.get("framed_exec", {}).get("caller_selected_command") is not False
        or value.get("framed_exec", {}).get("interactive_pty") is not False
        or value.get("framed_exec", {}).get("command_count") != 3
        or value.get("framed_exec", {}).get("runtime_contract") != framed_runtime.CONTRACT_ID
        or value.get("framed_exec", {}).get("observer_contract") != observer_adapter.CONTRACT_ID
        or not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("differs_from_consumed_p326") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or not isinstance(userspace, dict)
        or userspace.get("a") != userspace.get("b")
        or not isinstance(rollback, dict)
        or rollback.get("untouched") is not True
        or rollback.get("identity") != ROLLBACK_IDENTITY
    ):
        raise StaticContractError("P327 builder contract differs")
    for label in ("a", "b"):
        package = candidate[label].get("package", {})
        if (
            package.get("members") != ["boot.img.lz4"]
            or package.get("host_only") is not True
            or package.get("device_contact") is not False
            or candidate[label].get("busybox") != candidate_build.BUSYBOX_IDENTITY
            or candidate[label].get("busybox_path") != "bin/busybox"
        ):
            raise StaticContractError("P327 boot-only BusyBox package differs")
    return value, {"path": str(BUILDER_RESULT.relative_to(ROOT)), **identity(payload)}


def _artifacts(builder: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate = builder["phase2"]["candidate"]
    userspace = builder["phase2"]["userspace"]
    image = stable_bytes(
        BUILDER_OUTPUT / "inputs/fixed-Image", "P327 Image", 64 << 20,
        candidate["fixed_image_identity"], mode=0o400,
    )
    init = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/init", "P327 init", 2 << 20,
        userspace["a"]["init"], mode=0o400,
    )
    child = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/s22-e1-child", "P327 child", 2 << 20,
        userspace["a"]["child"], mode=0o400,
    )
    joined = []
    for label in ("a", "b"):
        try:
            joined.append(artifact.inspect_ap(
                BUILDER_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
                expected_run_id=artifact.P327_RUN_ID,
                expected_image=image,
                expected_init=init,
                expected_child=child,
                expected_ap=candidate[label]["ap_tar_md5"],
                label=f"P327 candidate {label.upper()} AP",
            ))
        except artifact.ArtifactIdentityError as exc:
            raise StaticContractError(str(exc)) from exc
    if joined[0] != joined[1]:
        raise StaticContractError("P327 A/B AP join differs")
    try:
        rollback = artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    except artifact.ArtifactIdentityError as exc:
        raise StaticContractError(str(exc)) from exc
    return joined, rollback


def _runtime(builder: dict[str, Any]) -> dict[str, Any]:
    before = stable_bytes(
        P326_RUNTIME,
        "P326 runtime",
        2 << 20,
        framed_runtime.P326_RUNTIME_IDENTITY,
        mode=0o400,
    )
    after = stable_bytes(
        P327_RUNTIME, "P327 runtime", 2 << 20,
        builder["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"], mode=0o400,
    )
    try:
        return framed_runtime.validate_transform(before, after) | {
            "before_identity": identity(before), "after_identity": identity(after)
        }
    except framed_runtime.FramedRuntimeError as exc:
        raise StaticContractError(str(exc)) from exc


def build_result(*, runtime_bound: bool = False) -> dict[str, Any]:
    builder, builder_receipt = _builder(runtime_bound=runtime_bound)
    joined, rollback = _artifacts(builder)
    runtime_receipt = _runtime(builder)
    try:
        lineage = adapter.bind_exact_sources()
        acceptance = adapter.validate_acceptance_item(adapter.acceptance_fixture())
    except Exception as exc:
        raise StaticContractError("P327 adapter did not reopen") from exc
    if (
        lineage.get("run_id") != RUN_ID
        or lineage.get("predecessor_run_id_rejected") != PREDECESSOR_RUN_ID
        or lineage.get("overlay_contract_id") != OVERLAY
        or acceptance.get("run_id") != RUN_ID
        or acceptance.get("userspace_overlay_contract_id") != OVERLAY
        or acceptance.get("candidate_success") is not False
    ):
        raise StaticContractError("P327 adapter binding differs")
    candidate = builder["phase2"]["candidate"]
    userspace = builder["phase2"]["userspace"]
    sources = {
        "p327_candidate_static": receipt(SELF_SOURCE, "P327 static", 2 << 20),
        "p327_stock_candidate_build": receipt(candidate_build.SELF_SOURCE, "P327 builder", 2 << 20),
        "p327_stock_process_v2_adapter": receipt(candidate_build.P327_ADAPTER_SOURCE, "P327 adapter", 2 << 20),
        "p327_artifact_identity": receipt(candidate_build.P327_ARTIFACT_SOURCE, "P327 artifact", 2 << 20),
        "p327_framed_exec_runtime": receipt(candidate_build.P327_RUNTIME_SOURCE, "P327 runtime helper", 2 << 20),
        "p327_framed_acm_observer": receipt(candidate_build.P327_OBSERVER_SOURCE, "P327 observer", 2 << 20),
        "busybox": receipt(candidate_build.BUSYBOX, "P327 BusyBox", 4 << 20, candidate_build.BUSYBOX_IDENTITY),
        "rollback_ap": receipt(ROLLBACK_AP, "P327 rollback", 64 << 20, ROLLBACK_IDENTITY),
    }
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority_source": sources["p327_candidate_static"],
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
            "image": candidate["fixed_image_identity"],
            "init": userspace["a"]["init"],
            "child": userspace["a"]["child"],
            "busybox": candidate_build.BUSYBOX_IDENTITY,
            "run_id_join": {
                "run_id_hex": RUN_ID,
                "a": joined[0], "b": joined[1], "joined": True,
            },
        },
        "adapter": {"lineage": lineage, "acceptance": acceptance, "source": sources["p327_stock_process_v2_adapter"]},
        "observer_adapter": {
            "schema": observer_adapter.SCHEMA,
            "contract_id": observer_adapter.CONTRACT_ID,
            "source": sources["p327_framed_acm_observer"],
            "runtime_source": sources["p327_framed_exec_runtime"],
            "wire_magic": framed_runtime.FRAME_MAGIC.decode("ascii"),
            "frame_header_size": framed_runtime.FRAME_HEADER_SIZE,
            "max_frame_payload": framed_runtime.MAX_FRAME_PAYLOAD,
            "max_commands": framed_runtime.MAX_COMMANDS,
            "command_timeout_sec": framed_runtime.COMMAND_TIMEOUT_SEC,
            "max_output_bytes": framed_runtime.MAX_OUTPUT_BYTES,
            "commands": [identity(command) for command in observer_adapter.DEFAULT_COMMANDS],
            "caller_selected_command": False,
            "interactive_pty": False,
            "raw_rx_forwarded_before_classification": True,
            "host_only": True,
            "device_contact": False,
        },
        "artifact_identity": {"candidate_a": joined[0], "candidate_b": joined[1], "rollback": rollback},
        "runtime_repair": runtime_receipt,
        "source_closure": sources,
        "ready_manifest_created": False,
        "run_manifest_created": False,
        "approval_created": False,
        "safety": {
            "host_only": True, "device_contact": False, "device_write": False,
            "odin_invoked": False, "odin_transfer": False, "flash": False,
            "partition_write": False, "live_authorized": False,
            "d0_authorized": False, "d1_authorized": False, "f1_authorized": False,
            "replay_authorized": False, "causal_result_allowed": False,
            "candidate_success": False,
        },
    }


def validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value != build_result():
        raise StaticContractError("P327 static result does not regenerate")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value != build_result(runtime_bound=True):
        raise StaticContractError("P327 bound static result differs")
    return value


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise StaticContractError("P327 static output already exists")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o400)
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("P327 static publication was short")
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
    except (OSError, RuntimeError, StaticContractError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({
        "schema": SCHEMA, "verdict": VERDICT, "output": str(output),
        "identity": identity(payload), "created": not args.audit_only,
        "device_contact": False, "live_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
