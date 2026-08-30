#!/usr/bin/env python3
"""Bind the P3.22 artifact-joined candidate to a thin H0 static contract.

The validator reopens the final P3.22 stock-candidate build, independently
unpacks both real boot-only APs, and joins their Image, ``/init``, child, and
run-ID receipts.  The P3.22 runtime repair is checked as one exact function
delta.  This module is host-only: it creates no manifest, approval, device
session, transfer, or live authority.
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

import s22plus_fyg8_p322_artifact_identity as artifact_identity  # noqa: E402
import s22plus_fyg8_p322_runtime_repair as runtime_repair  # noqa: E402
import s22plus_fyg8_p322_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p322_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
P321_OUTPUT = candidate_build.P321_OUTPUT
P321_RESULT = P321_OUTPUT / "result.json"
P321_RUNTIME = P321_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
P322_RUNTIME = BUILDER_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
ROLLBACK_AP = candidate_build.p321.P319_ROLLBACK_AP
P319_IMAGE = artifact_identity.P319_IMAGE

DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p322/"
    "process-v2-candidate-static-20260831-02.json"
)
SCHEMA = "s22plus_fyg8_p322_process_v2_candidate_static_v1"
VERDICT = "PASS_P322_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P322_RUN_ID = adapter.P322_RUN_ID_HEX
P321_RUN_ID = adapter.P321_RUN_ID_HEX
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
OVERLAY = adapter.P322_OVERLAY_CONTRACT_ID
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
P322_BUILDER_RESULT_IDENTITY = {
    "size": 39_444,
    "sha256": "ed8cc4a3a17d48fe84a8f7da98fe26bcdb74209821c3dcfdff7636d6cb2a4082",
}
P322_AP_IDENTITY = {
    "size": 27_279_401,
    "sha256": "ff7f189d02ba7c124ba6bc805f9a8f385bc4995fb235b5c13b4e436ae69cd412",
}
P322_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "29606fb42162d629bdfbd752e408b8962121e0a25b17dbee925d6366e762275f",
}
P322_INIT_IDENTITY = {
    "size": 80_504,
    "sha256": "d2350352ddbc76ec116f32c83e33b7aaf9e8c229671778341843dd29a94de3e5",
}
P322_CHILD_IDENTITY = {
    "size": 1_376,
    "sha256": "eb3c072b41ab4d4953fd1d862388d3be5ca5a40e9a07f074cb273f96a28557cf",
}
P322_BUILDER_SOURCE_IDENTITY = {
    "size": 21_976,
    "sha256": "ef6e5b5d4a75e0251348a8ce5d21f09189c92c11e1a07883d567b8ffca722ae1",
}
P322_ARTIFACT_SOURCE_IDENTITY = {
    "size": 9_453,
    "sha256": "8e77653fa23f47f48980fb2eae906118239e53e763d4e9643be27a71b0749975",
}
P322_REPAIR_SOURCE_IDENTITY = {
    "size": 9_590,
    "sha256": "8d0edac55ba37c20a76394f70b8d21aeb6403849aeea7f94208ad6b1157fff6f",
}
P322_ADAPTER_SOURCE_IDENTITY = {
    "size": 12_739,
    "sha256": "574f88d966b091fb24a3feb6ea7cbdde54f630fcaab688ca25d10c8181cd4bda",
}
P321_RESULT_IDENTITY = {
    "size": 33_947,
    "sha256": "4bf4edcbe78456768e3494b47a497628ba9549f8767b5c214f3f50c79aad293e",
}


class StaticContractError(ValueError):
    """The P3.22 candidate-static contract cannot be trusted."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise StaticContractError("P322 static path escaped repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    maximum: int = 128 * 1024 * 1024,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    """Read one unchanged, direct regular file and optionally bind its hash."""
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
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("ascii")


def _load_source(path: Path, name: str) -> tuple[types.ModuleType, bytes]:
    source = stable_bytes(path, f"P322 {name} source", 8 * 1024 * 1024)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise StaticContractError(f"P322 {name} source failed to load") from exc
    return module, source


def _receipt(
    path: Path,
    label: str,
    maximum: int = 128 * 1024 * 1024,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> dict[str, Any]:
    payload = stable_bytes(path, label, maximum, expected, mode=mode, nlink=nlink)
    return {"path": relative(path), **identity(payload)}


def _builder_result(*, runtime_bound: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = stable_bytes(
        BUILDER_RESULT,
        "P322 builder result",
        4 * 1024 * 1024,
        P322_BUILDER_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    value = decode(payload, "P322 builder result")
    if not runtime_bound:
        try:
            audited = candidate_build.audit_existing(BUILDER_OUTPUT)
        except Exception as exc:
            raise StaticContractError("P322 builder result did not reopen") from exc
        if audited != value:
            raise StaticContractError("P322 builder audit result differs")
    return value, {"path": relative(BUILDER_RESULT), **identity(payload)}


def _validate_builder(value: dict[str, Any]) -> None:
    if (
        value.get("schema") != candidate_build.SCHEMA
        or value.get("verdict") != candidate_build.VERDICT
        or value.get("target") != TARGET
        or value.get("run_id_hex") != P322_RUN_ID
    ):
        raise StaticContractError("P322 builder header differs")
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
        raise StaticContractError("P322 builder scope differs")
    phase2 = value.get("phase2")
    if not isinstance(phase2, dict) or phase2.get("built") is not True:
        raise StaticContractError("P322 builder Phase-2 result is incomplete")
    if phase2.get("static_aarch64") is not True:
        raise StaticContractError("P322 userspace is not static AArch64")
    candidate = phase2.get("candidate")
    if not isinstance(candidate, dict):
        raise StaticContractError("P322 candidate package closure is absent")
    if (
        candidate.get("byte_identical") is not True
        or candidate.get("fixed_image") is not True
        or candidate.get("one_boot_img_lz4_member") is not True
        or candidate.get("diagnostic_absent") is not True
        or candidate.get("ap_differs_from_consumed_p319") is not True
        or candidate.get("differs_from_consumed_p321") is not True
        or candidate.get("overlay_members") != ["lib/modules/s22plus_dwc3_event_latch.ko"]
    ):
        raise StaticContractError("P322 candidate package closure differs")
    if candidate.get("a") != candidate.get("b"):
        raise StaticContractError("P322 candidate A/B builder receipts differ")
    for label in ("a", "b"):
        item = candidate[label]
        if (
            item.get("ap_tar_md5") != P322_AP_IDENTITY
            or item.get("boot_img", {}).get("size") != 100_663_296
            or item.get("boot_img_lz4", {}).get("size") != 27_269_441
            or item.get("overlay_members") != ["lib/modules/s22plus_dwc3_event_latch.ko"]
            or item.get("package", {}).get("ap_structure", {}).get("members") != ["boot.img.lz4"]
            or item.get("package", {}).get("safety") != {
                "boot_only": True,
                "device_contact": False,
                "device_write": False,
                "host_only": True,
                "live_authorized": False,
                "odin_invoked": False,
            }
        ):
            raise StaticContractError(f"P322 candidate {label} package is not boot-only")
    join = candidate.get("run_id_join")
    if (
        not isinstance(join, dict)
        or join.get("run_id_hex") != P322_RUN_ID
        or join.get("joined") is not True
        or join.get("a") != join.get("b")
    ):
        raise StaticContractError("P322 builder A/B run-ID join differs")
    userspace = phase2.get("userspace")
    if (
        not isinstance(userspace, dict)
        or userspace.get("a") != userspace.get("b")
        or userspace.get("a", {}).get("init") != P322_INIT_IDENTITY
        or userspace.get("a", {}).get("child") != P322_CHILD_IDENTITY
    ):
        raise StaticContractError("P322 userspace closure differs")
    if value.get("inputs", {}).get("fixed-Image") != P322_IMAGE_IDENTITY:
        raise StaticContractError("P322 fixed Image identity differs")
    rollback = phase2.get("rollback")
    if not isinstance(rollback, dict) or rollback.get("untouched") is not True:
        raise StaticContractError("P322 rollback preservation differs")
    if rollback.get("artifact_identity", {}).get("identity") != ROLLBACK_IDENTITY:
        raise StaticContractError("P322 rollback identity differs")


def _repair_receipt(builder: dict[str, Any]) -> dict[str, Any]:
    predecessor_payload = stable_bytes(
        P321_RESULT,
        "P321 predecessor result",
        4 * 1024 * 1024,
        P321_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    predecessor = decode(predecessor_payload, "P321 predecessor result")
    expected_before = predecessor.get("source_closure", {}).get(
        "s22plus_fyg8_p290_e3_runtime.inc.c"
    )
    expected_after = builder.get("source_closure", {}).get(
        "s22plus_fyg8_p290_e3_runtime.inc.c"
    )
    if not isinstance(expected_before, dict) or not isinstance(expected_after, dict):
        raise StaticContractError("P322 runtime repair source receipts are absent")
    before = stable_bytes(
        P321_RUNTIME,
        "P321 runtime repair input",
        2 * 1024 * 1024,
        expected_before,
        mode=0o400,
        nlink=1,
    )
    after = stable_bytes(
        P322_RUNTIME,
        "P322 repaired runtime",
        2 * 1024 * 1024,
        expected_after,
        mode=0o400,
        nlink=1,
    )
    try:
        receipt = runtime_repair.validate_repair(before, after) | {
            "before_identity": identity(before),
            "after_identity": identity(after),
        }
    except runtime_repair.RuntimeRepairError as exc:
        raise StaticContractError("P322 one-function runtime repair is not exact") from exc
    if receipt != builder.get("lineage", {}).get("runtime_repair"):
        raise StaticContractError("P322 builder repair receipt differs")
    return receipt


def _inspect_candidate_aps(
    builder: dict[str, Any],
) -> tuple[bytes, bytes, bytes, list[dict[str, Any]]]:
    candidate = builder["phase2"]["candidate"]
    image = stable_bytes(
        BUILDER_OUTPUT / "inputs/fixed-Image",
        "P322 fixed Image",
        64 * 1024 * 1024,
        P322_IMAGE_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    init = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/init",
        "P322 /init",
        2 * 1024 * 1024,
        P322_INIT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    child = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/s22-e1-child",
        "P322 child",
        2 * 1024 * 1024,
        P322_CHILD_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    joined: list[dict[str, Any]] = []
    for label in ("a", "b"):
        try:
            joined.append(
                artifact_identity.inspect_ap(
                    BUILDER_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
                    expected_run_id=adapter.P322_RUN_ID,
                    expected_image=image,
                    expected_init=init,
                    expected_child=child,
                    expected_ap=P322_AP_IDENTITY,
                    label=f"P322 candidate {label.upper()} AP",
                )
            )
        except artifact_identity.ArtifactIdentityError as exc:
            raise StaticContractError(str(exc)) from exc
    expected_join = candidate.get("run_id_join")
    if (
        not isinstance(expected_join, dict)
        or expected_join.get("a") != joined[0]
        or expected_join.get("b") != joined[1]
        or expected_join.get("joined") is not True
        or expected_join.get("run_id_hex") != P322_RUN_ID
        or joined[0] != joined[1]
    ):
        raise StaticContractError("P322 real A/B AP unpack/join differs")
    return image, init, child, joined


def build_result(*, runtime_bound: bool = False) -> dict[str, Any]:
    builder, builder_receipt = _builder_result(runtime_bound=runtime_bound)
    _validate_builder(builder)
    repair_receipt = _repair_receipt(builder)
    image, init, child, joined = _inspect_candidate_aps(builder)
    image_result = artifact_identity.validate_image(image, expected_run_id=adapter.P322_RUN_ID)
    if image_result["identity"] != P322_IMAGE_IDENTITY:
        raise StaticContractError("P322 Image validation identity differs")
    if identity(init) != P322_INIT_IDENTITY or identity(child) != P322_CHILD_IDENTITY:
        raise StaticContractError("P322 userspace identity differs")
    try:
        rollback = artifact_identity.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    except artifact_identity.ArtifactIdentityError as exc:
        raise StaticContractError(str(exc)) from exc
    if rollback != builder["phase2"]["rollback"]["artifact_identity"]:
        raise StaticContractError("P322 rollback receipt differs")

    try:
        adapter_lineage = adapter.bind_exact_sources()
        acceptance = adapter.validate_acceptance_item(adapter.acceptance_fixture())
    except Exception as exc:
        raise StaticContractError("P322 adapter binding did not reopen") from exc
    if (
        adapter_lineage.get("run_id") != P322_RUN_ID
        or adapter_lineage.get("predecessor_run_id_rejected") != P321_RUN_ID
        or adapter_lineage.get("overlay_contract_id") != OVERLAY
        or adapter_lineage.get("parent_source_contract_id") != PARENT_SOURCE
        or acceptance.get("run_id") != P322_RUN_ID
        or acceptance.get("userspace_overlay_contract_id") != OVERLAY
        or acceptance.get("causal_result_allowed") is not False
        or acceptance.get("candidate_success") is not False
    ):
        raise StaticContractError("P322 adapter identity differs")

    source_closure = {
        "p322_candidate_static": _receipt(
            SELF_SOURCE, "P322 candidate-static source", 4 * 1024 * 1024
        ),
        "p322_stock_candidate_build": _receipt(
            candidate_build.SELF_SOURCE,
            "P322 builder source",
            4 * 1024 * 1024,
            P322_BUILDER_SOURCE_IDENTITY,
        ),
        "p322_stock_process_v2_adapter": _receipt(
            candidate_build.P322_ADAPTER_SOURCE,
            "P322 adapter source",
            4 * 1024 * 1024,
            P322_ADAPTER_SOURCE_IDENTITY,
        ),
        "p322_artifact_identity": _receipt(
            candidate_build.P322_ARTIFACT_SOURCE,
            "P322 artifact identity source",
            4 * 1024 * 1024,
            P322_ARTIFACT_SOURCE_IDENTITY,
        ),
        "p322_runtime_repair": _receipt(
            candidate_build.P322_REPAIR_SOURCE,
            "P322 runtime repair source",
            4 * 1024 * 1024,
            P322_REPAIR_SOURCE_IDENTITY,
        ),
        "p319_fixed_image": _receipt(
            P319_IMAGE,
            "P319 fixed Image source",
            64 * 1024 * 1024,
            artifact_identity.P319_IMAGE_IDENTITY,
        ),
        "p319_rollback_ap": _receipt(
            ROLLBACK_AP,
            "P319 exact rollback AP",
            64 * 1024 * 1024,
            ROLLBACK_IDENTITY,
        ),
    }
    builder_candidate = builder["phase2"]["candidate"]
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority_source": source_closure["p322_candidate_static"],
        "target": TARGET,
        "profile": adapter.PROFILE,
        "run_id": P322_RUN_ID,
        "source_contract_id": PARENT_SOURCE,
        "userspace_overlay_contract_id": OVERLAY,
        "builder_result": builder_receipt,
        "candidate": {
            "a": builder_candidate["a"],
            "b": builder_candidate["b"],
            "byte_identical": builder_candidate["byte_identical"],
            "boot_only": builder_candidate["one_boot_img_lz4_member"],
            "image": builder["inputs"]["fixed-Image"],
            "init": builder["phase2"]["userspace"]["a"]["init"],
            "child": builder["phase2"]["userspace"]["a"]["child"],
            "run_id_join": {
                "run_id_hex": P322_RUN_ID,
                "a": joined[0],
                "b": joined[1],
                "joined": True,
            },
        },
        "adapter": {
            "lineage": adapter_lineage,
            "acceptance": acceptance,
            "source": _receipt(
                candidate_build.P322_ADAPTER_SOURCE,
                "P322 adapter delegate",
                4 * 1024 * 1024,
                P322_ADAPTER_SOURCE_IDENTITY,
            ),
        },
        "artifact_identity": {
            "image_transform": builder["lineage"]["image_transform"],
            "base_boot_replacement": builder_candidate["base_boot_replacement"],
            "candidate_a": joined[0],
            "candidate_b": joined[1],
            "a_b_equal": joined[0] == joined[1],
            "rollback": rollback,
        },
        "runtime_repair": repair_receipt,
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
        raise StaticContractError("P322 static result is not an object")
    expected = build_result(runtime_bound=False)
    if value != expected:
        raise StaticContractError("P322 static result does not regenerate exactly")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    """Reopen immutable inputs without rerunning the builder's full audit."""
    if not isinstance(value, dict):
        raise StaticContractError("P322 static result is not an object")
    expected = build_result(runtime_bound=True)
    if value != expected:
        raise StaticContractError("P322 runtime-bound static result differs")
    return value


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise StaticContractError("P322 static output already exists")
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
                raise StaticContractError("P322 static publication was short")
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
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": VERDICT,
                    "output": str(output),
                    "identity": identity(payload),
                    "created": not args.audit_only,
                    "device_contact": False,
                    "ready_manifest_created": False,
                    "live_authorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, StaticContractError, RuntimeError) as exc:
        print(
            json.dumps(
                {"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
