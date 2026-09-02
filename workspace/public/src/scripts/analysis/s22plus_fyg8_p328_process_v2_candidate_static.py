#!/usr/bin/env python3
"""Build the P3.28 Process-v2 candidate-static receipt (host-only).

The P3.28 candidate is already built by the bounded stock-candidate builder.
This checker reopens that result, both real boot-only APs, the exact rollback,
the materialized authenticated runtime, and the private 32-byte key identity.
It publishes no key bytes and creates no device or live authority.
"""

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

import s22plus_fyg8_p328_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p328_auth_acm_observer as observer_adapter  # noqa: E402
import s22plus_fyg8_p328_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p328_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p328_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
BUILDER_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p328/"
    "stock-candidate-build-v1-20260902-04"
)
BUILDER_RESULT = BUILDER_OUTPUT / "result.json"
BUILDER_RESULT_IDENTITY = {
    "size": 44_823,
    "sha256": "9901493f13e5a568f634710b353e9f557019c8ed43435b5130af68fe8c2fd286",
}
BUILDER_SOURCE_IDENTITY = {
    "size": 33_410,
    "sha256": "2d55eb45eca5d5094a6369e9fc82e337a66dba20d1ad5d1f2e3cce8bd5ebbfff",
}
RUNTIME_SOURCE_IDENTITY = {
    "size": 21_068,
    "sha256": "e69b5603998c19f2c24f48b16d8149c3c5046ae9a42a8baf9de497c3f56d328a",
}
OBSERVER_SOURCE_IDENTITY = {
    "size": 18_326,
    "sha256": "2ec10d550b575f69f91f2424d9a605b5635ed9d5a853b59bb24563c85c6a9e25",
}
ADAPTER_SOURCE_IDENTITY = {
    "size": 15_396,
    "sha256": "e0339f87daea4c911e999f07b769fc258ff7908ba6e7341c7955d04e13c8e750",
}
ARTIFACT_SOURCE_IDENTITY = {
    "size": 11_503,
    "sha256": "e849578b1e7fcb9853ee0a07eaafb28922aa3e5f6b6f746851122f354cc00931",
}
P328_AP_IDENTITY = {
    "size": 28_631_081,
    "sha256": "4ff89343a35a3bd0081ac8ed09ef0a872921b2ace5e9be266ce0c4d5a2bffbdb",
}
P328_IMAGE_IDENTITY = {
    "size": 41_490_944,
    "sha256": "bc6ae05ea6ec36c1baf1807b6b52d434528b4eae2d25d1c95b7518db14f6af7a",
}
P328_INIT_IDENTITY = {
    "size": 82_032,
    "sha256": "8cb723aa8171b9dafa60a6d0cf390d0e2e098761712c54cc20cb944a09a90086",
}
P328_KEY_IDENTITY = {
    "size": 32,
    "sha256": "7eb6a32ca96daa9cd125b2798834f45515265a76d653ae719091d98f0a1f515b",
}
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}

DEFAULT_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p328/"
    "process-v2-candidate-static-20260902-01.json"
)
SCHEMA = "s22plus_fyg8_p328_process_v2_candidate_static_v1"
VERDICT = "PASS_P328_PROCESS_V2_CANDIDATE_STATIC_HOST_ONLY"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
RUN_ID = adapter.P328_RUN_ID_HEX
PREDECESSOR_RUN_ID = adapter.P327_RUN_ID_HEX
OVERLAY = adapter.P328_OVERLAY_CONTRACT_ID
PARENT_SOURCE = adapter.PARENT_SOURCE_CONTRACT_ID
AUTH_KEY_SCHEMA = adapter.AUTH_KEY_SCHEMA
AUTH_KEY_SIZE = adapter.AUTH_KEY_SIZE
DEFAULT_AUTH_KEY_PATH = artifact.DEFAULT_AUTH_KEY_PATH


class StaticContractError(ValueError):
    """The P3.28 static closure is incomplete or changed."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


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
        raise StaticContractError("P3.28 value is not canonical JSON") from exc


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

    def inode(value: os.stat_result) -> tuple[int, ...]:
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
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise StaticContractError(f"{label} identity differs")
    return payload


def receipt(
    path: Path,
    label: str,
    maximum: int,
    expected: Mapping[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> dict[str, Any]:
    return {
        "path": str(path.absolute().relative_to(ROOT)),
        **identity(stable_bytes(path, label, maximum, expected, mode=mode, nlink=nlink)),
    }


def _key_identity() -> dict[str, Any]:
    expected = DEFAULT_AUTH_KEY_PATH.absolute()
    fixed = ROOT / "workspace/private/inputs/s22plus_fyg8_p328/auth-key-v1.bin"
    if expected != fixed.absolute():
        raise StaticContractError("P3.28 auth key path is not the fixed private input")
    try:
        value = artifact.auth_key_identity(expected)
    except Exception as exc:
        raise StaticContractError("P3.28 auth key did not reopen") from exc
    if value != P328_KEY_IDENTITY:
        raise StaticContractError("P3.28 auth key identity differs")
    return {"size": value["size"], "sha256": value["sha256"]}


def _assert_key_projection(value: Any, label: str, expected: dict[str, Any]) -> None:
    if value != expected:
        raise StaticContractError(f"{label} differs")


def _builder(*, runtime_bound: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = stable_bytes(
        BUILDER_RESULT,
        "P3.28 builder result",
        4 * 1024 * 1024,
        BUILDER_RESULT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    value = decode(payload, "P3.28 builder result")
    if not runtime_bound:
        try:
            audited = candidate_build.audit_existing(
                BUILDER_OUTPUT,
                auth_key=DEFAULT_AUTH_KEY_PATH,
            )
        except Exception as exc:
            raise StaticContractError("P3.28 builder did not reopen") from exc
        if audited != value:
            raise StaticContractError("P3.28 builder audit differs")

    key_identity = (
        dict(P328_KEY_IDENTITY) if runtime_bound else _key_identity()
    )
    phase2 = value.get("phase2")
    candidate = phase2.get("candidate") if isinstance(phase2, dict) else None
    userspace = phase2.get("userspace") if isinstance(phase2, dict) else None
    rollback = phase2.get("rollback") if isinstance(phase2, dict) else None
    auth = value.get("authentication")
    framed = value.get("framed_exec")
    lineage = value.get("lineage")
    if (
        value.get("schema") != candidate_build.SCHEMA
        or value.get("verdict") != candidate_build.VERDICT
        or value.get("target") != TARGET
        or value.get("run_id_hex") != RUN_ID
        or not isinstance(lineage, dict)
        or lineage.get("predecessor_run_id") != PREDECESSOR_RUN_ID
        or value.get("scope", {}).get("device_contact") is not False
        or value.get("scope", {}).get("live_authority_created") is not False
        or value.get("scope", {}).get("tier") != "H0"
        or not isinstance(auth, dict)
        or auth.get("required") is not True
        or auth.get("scheme") != "auth-key-v1"
        or auth.get("path_published") is not False
        or not isinstance(framed, dict)
        or framed.get("authenticated") is not True
        or framed.get("authentication_required") is not True
        or framed.get("auth_algorithm") != "hmac-sha256"
        or framed.get("auth_key_schema") != AUTH_KEY_SCHEMA
        or framed.get("auth_key_path_published") is not False
        or framed.get("wire_magic") != "S328"
        or framed.get("frame_header_size") != 16
        or framed.get("max_commands") != 16
        or framed.get("proof_command_count") != 3
        or framed.get("command_timeout_sec") != 15
        or framed.get("max_output_bytes") != 128 * 1024
        or framed.get("caller_selected_command") is not True
        or framed.get("interactive_pty") is not False
        or framed.get("per_session_random_nonce") is not True
        or not isinstance(candidate, dict)
        or candidate.get("a") != candidate.get("b")
        or candidate.get("byte_identical") is not True
        or candidate.get("differs_from_consumed_p327") is not True
        or candidate.get("run_id_join", {}).get("joined") is not True
        or candidate.get("run_id_join", {}).get("run_id_hex") != RUN_ID
        or candidate.get("fixed_image_identity") != P328_IMAGE_IDENTITY
        or not isinstance(userspace, dict)
        or userspace.get("a") != userspace.get("b")
        or userspace.get("a", {}).get("init") != P328_INIT_IDENTITY
        or not isinstance(rollback, dict)
        or rollback.get("untouched") is not True
        or rollback.get("identity") != ROLLBACK_IDENTITY
    ):
        raise StaticContractError("P3.28 builder contract differs")
    _assert_key_projection(auth.get("key"), "P3.28 authentication key", key_identity)
    _assert_key_projection(framed.get("auth_key"), "P3.28 framed key", key_identity)
    repair = lineage.get("runtime_repair")
    if (
        not isinstance(repair, dict)
        or repair.get("authenticated") is not True
        or repair.get("authentication_required") is not True
        or repair.get("auth_key_schema") != AUTH_KEY_SCHEMA
        or repair.get("auth_key_path_published") is not False
        or repair.get("auth_key_sha256") != key_identity["sha256"]
    ):
        raise StaticContractError("P3.28 runtime key binding differs")
    _assert_key_projection(repair.get("auth_key"), "P3.28 runtime key", key_identity)

    commands = framed.get("commands")
    expected_commands = [
        {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
        for command in observer_adapter.DEFAULT_COMMANDS
    ]
    if commands != expected_commands:
        raise StaticContractError("P3.28 fixed proof commands differ")
    for label in ("a", "b"):
        item = candidate[label]
        package = item.get("package")
        if (
            not isinstance(package, dict)
            or package.get("members") != ["boot.img.lz4"]
            or package.get("host_only") is not True
            or package.get("device_contact") is not False
            or package.get("odin_invoked") is not False
            or item.get("busybox") != candidate_build.BUSYBOX_IDENTITY
            or item.get("busybox_path") != "bin/busybox"
            or item.get("overlay_members") != ["lib/modules/s22plus_dwc3_event_latch.ko"]
        ):
            raise StaticContractError("P3.28 boot-only package differs")
    return value, {"path": str(BUILDER_RESULT.relative_to(ROOT)), **identity(payload)}, key_identity


def _artifacts(
    builder: dict[str, Any],
    key_identity: dict[str, Any],
    *,
    bind_private_key: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any], bytes, bytes, bytes]:
    phase2 = builder["phase2"]
    candidate = phase2["candidate"]
    userspace = phase2["userspace"]
    image = stable_bytes(
        BUILDER_OUTPUT / "inputs/fixed-Image",
        "P3.28 Image",
        64 * 1024 * 1024,
        P328_IMAGE_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    init = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/init",
        "P3.28 init",
        2 * 1024 * 1024,
        P328_INIT_IDENTITY,
        mode=0o400,
        nlink=1,
    )
    if bind_private_key:
        try:
            auth_key = artifact.read_auth_key(DEFAULT_AUTH_KEY_PATH)
        except artifact.ArtifactIdentityError as exc:
            raise StaticContractError(
                "P3.28 auth key did not reopen for init binding"
            ) from exc
        if identity(auth_key) != key_identity or init.count(auth_key) != 1:
            raise StaticContractError(
                "P3.28 init does not contain exactly one bound auth key"
            )
    child_identity = userspace["a"]["child"]
    child = stable_bytes(
        BUILDER_OUTPUT / "userspace-a/s22-e1-child",
        "P3.28 child",
        2 * 1024 * 1024,
        child_identity,
        mode=0o400,
        nlink=1,
    )
    joined: list[dict[str, Any]] = []
    for label in ("a", "b"):
        try:
            joined.append(
                artifact.inspect_ap(
                    BUILDER_OUTPUT / f"candidate-{label}/odin4/AP.tar.md5",
                    expected_run_id=artifact.P328_RUN_ID,
                    expected_image=image,
                    expected_init=init,
                    expected_child=child,
                    expected_ap=candidate[label]["ap_tar_md5"],
                    label=f"P3.28 candidate {label.upper()} AP",
                )
            )
        except artifact.ArtifactIdentityError as exc:
            raise StaticContractError(str(exc)) from exc
    if joined[0] != joined[1]:
        raise StaticContractError("P3.28 A/B AP join differs")
    if joined[0].get("ap") != P328_AP_IDENTITY:
        raise StaticContractError("P3.28 candidate AP identity differs")
    try:
        rollback = artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
    except artifact.ArtifactIdentityError as exc:
        raise StaticContractError(str(exc)) from exc
    return joined, rollback, image, init, child


def _runtime(builder: dict[str, Any], key_identity: dict[str, Any]) -> dict[str, Any]:
    runtime_path = BUILDER_OUTPUT / "stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
    expected = builder["source_closure"]["s22plus_fyg8_p290_e3_runtime.inc.c"]
    after = stable_bytes(
        runtime_path,
        "P3.28 materialized runtime",
        2 * 1024 * 1024,
        expected,
        mode=0o400,
        nlink=1,
    )
    try:
        value = framed_runtime.validate_p328_runtime(
            after,
            auth_key_sha256=key_identity["sha256"],
        )
    except framed_runtime.AuthRuntimeError as exc:
        raise StaticContractError(str(exc)) from exc
    repair = builder.get("lineage", {}).get("runtime_repair")
    if not isinstance(repair, dict):
        raise StaticContractError("P3.28 runtime repair receipt is missing")
    if repair.get("after_identity") != identity(after):
        raise StaticContractError("P3.28 runtime repair identity differs")
    if repair.get("auth_key") != key_identity:
        raise StaticContractError("P3.28 runtime repair key differs")
    return {
        **value,
        "before_identity": repair.get("before_identity"),
        "after_identity": identity(after),
        "authenticated": True,
        "authentication_required": True,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "run_id_hex": RUN_ID,
    }


def _source_closure(
    runtime_receipt: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    try:
        return {
            "p328_candidate_static": receipt(
                SELF_SOURCE, "P3.28 candidate static", 2 * 1024 * 1024
            ),
            "p328_stock_candidate_build": receipt(
                candidate_build.SELF_SOURCE,
                "P3.28 builder",
                2 * 1024 * 1024,
                BUILDER_SOURCE_IDENTITY,
                nlink=1,
            ),
            "p328_stock_process_v2_adapter": receipt(
                candidate_build.P328_ADAPTER_SOURCE,
                "P3.28 adapter",
                2 * 1024 * 1024,
                ADAPTER_SOURCE_IDENTITY,
                nlink=1,
            ),
            "p328_artifact_identity": receipt(
                candidate_build.P328_ARTIFACT_SOURCE,
                "P3.28 artifact helper",
                2 * 1024 * 1024,
                ARTIFACT_SOURCE_IDENTITY,
                nlink=1,
            ),
            "p328_authenticated_exec_runtime": receipt(
                candidate_build.P328_RUNTIME_SOURCE,
                "P3.28 runtime helper",
                2 * 1024 * 1024,
                RUNTIME_SOURCE_IDENTITY,
                nlink=1,
            ),
            "p328_authenticated_acm_observer": receipt(
                candidate_build.P328_OBSERVER_SOURCE,
                "P3.28 observer",
                2 * 1024 * 1024,
                OBSERVER_SOURCE_IDENTITY,
                nlink=1,
            ),
            "busybox": receipt(
                candidate_build.BUSYBOX,
                "P3.28 BusyBox",
                4 * 1024 * 1024,
                candidate_build.BUSYBOX_IDENTITY,
                nlink=1,
            ),
            "rollback_ap": receipt(
                ROLLBACK_AP,
                "P3.28 exact rollback",
                64 * 1024 * 1024,
                ROLLBACK_IDENTITY,
                nlink=1,
            ),
        }
    except (KeyError, ValueError) as exc:
        raise StaticContractError("P3.28 source closure is unavailable") from exc


def build_result(*, runtime_bound: bool = False) -> dict[str, Any]:
    builder, builder_receipt, key_identity = _builder(runtime_bound=runtime_bound)
    joined, rollback, _image, _init, _child = _artifacts(
        builder,
        key_identity,
        bind_private_key=not runtime_bound,
    )
    runtime_receipt = _runtime(builder, key_identity)
    sources = _source_closure(runtime_receipt)
    try:
        lineage = adapter.bind_exact_sources(
            auth_key=None if runtime_bound else DEFAULT_AUTH_KEY_PATH
        )
        if runtime_bound:
            lineage["auth_key"] = dict(key_identity)
        acceptance = dict(adapter.acceptance_fixture())
        acceptance["auth_key"] = key_identity
        acceptance["auth_key_schema"] = AUTH_KEY_SCHEMA
        acceptance["auth_key_size"] = AUTH_KEY_SIZE
        acceptance = adapter.validate_acceptance_item(acceptance)
    except Exception as exc:
        raise StaticContractError("P3.28 adapter did not reopen") from exc
    if (
        lineage.get("run_id") != RUN_ID
        or lineage.get("predecessor_run_id_rejected") != PREDECESSOR_RUN_ID
        or lineage.get("overlay_contract_id") != OVERLAY
        or lineage.get("auth_key") != key_identity
        or acceptance.get("run_id") != RUN_ID
        or acceptance.get("userspace_overlay_contract_id") != OVERLAY
        or acceptance.get("candidate_success") is not False
        or acceptance.get("auth_key") != key_identity
        or acceptance.get("auth_key_schema") != AUTH_KEY_SCHEMA
        or acceptance.get("auth_key_size") != AUTH_KEY_SIZE
    ):
        raise StaticContractError("P3.28 adapter binding differs")

    phase2 = builder["phase2"]
    candidate = phase2["candidate"]
    userspace = phase2["userspace"]
    commands = [
        {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
        for command in observer_adapter.DEFAULT_COMMANDS
    ]
    observer_value = {
        "schema": observer_adapter.SCHEMA,
        "contract_id": observer_adapter.CONTRACT_ID,
        "source": sources["p328_authenticated_acm_observer"],
        "runtime_source": sources["p328_authenticated_exec_runtime"],
        "wire_magic": framed_runtime.FRAME_MAGIC.decode("ascii"),
        "frame_header_size": framed_runtime.FRAME_HEADER_SIZE,
        "max_frame_payload": framed_runtime.MAX_FRAME_PAYLOAD,
        "max_commands": framed_runtime.MAX_COMMANDS,
        "proof_command_count": len(commands),
        "command_timeout_sec": framed_runtime.COMMAND_TIMEOUT_SEC,
        "max_output_bytes": framed_runtime.MAX_OUTPUT_BYTES,
        "commands": commands,
        "caller_selected_command": True,
        "interactive_pty": False,
        "raw_rx_forwarded_before_classification": True,
        "authenticated": True,
        "authentication_required": True,
        "auth_algorithm": "hmac-sha256",
        "per_session_random_nonce": True,
        "auth_tag_size": framed_runtime.AUTH_TAG_SIZE,
        "auth_key_schema": AUTH_KEY_SCHEMA,
        "auth_key": key_identity,
        "auth_key_path_published": False,
        "host_only": True,
        "device_contact": False,
    }
    authentication = {
        "required": True,
        "scheme": "auth-key-v1",
        "key": key_identity,
        "embedded_key_occurrences_in_init": 1,
        "hardware_backed": False,
        "candidate_possession_implies_key_possession": True,
        "path_published": False,
    }
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "authority_source": sources["p328_candidate_static"],
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
                "a": joined[0],
                "b": joined[1],
                "joined": True,
            },
        },
        "adapter": {
            "lineage": lineage,
            "acceptance": acceptance,
            "source": sources["p328_stock_process_v2_adapter"],
        },
        "observer_adapter": observer_value,
        "authentication": authentication,
        "artifact_identity": {
            "candidate_a": joined[0],
            "candidate_b": joined[1],
            "rollback": rollback,
            "auth_key": key_identity,
        },
        "runtime_repair": runtime_receipt,
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
    if result["runtime_repair"]["auth_key"] != key_identity:
        raise StaticContractError("P3.28 static runtime key projection differs")
    return result


def validate_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value != build_result():
        raise StaticContractError("P3.28 static result does not regenerate")
    return value


def validate_bound_result(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value != build_result(runtime_bound=True):
        raise StaticContractError("P3.28 bound static result differs")
    return value


def publish(path: Path, payload: bytes) -> None:
    direct = path.absolute()
    if direct.exists() or direct.is_symlink():
        raise StaticContractError("P3.28 static output already exists")
    direct.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    direct.parent.chmod(0o700)
    descriptor = os.open(
        direct,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        0o400,
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise StaticContractError("P3.28 static publication was short")
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
