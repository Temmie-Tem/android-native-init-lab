#!/usr/bin/env python3
"""Materialize the P3.21 identity-joined stock candidate, H0 only.

P3.21 keeps the reviewed P3.20 userspace/observer composition but derives a
fresh run identity across every candidate seam.  The pinned P3.19 Image is
transformed only at its one compiled run-ID string and its exact embedded
IKCONFIG gzip stream; the deterministic same-length transform preserves the
Image layout and module-provider/CRC regions.  The real AP is unpacked again
after packaging and the Image/config to ``/init`` join is checked before the
result is published.  No device, ADB, Odin, transfer, authority, or recovery
action is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
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


SELF_SOURCE = Path(__file__).resolve()
P320_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p320_stock_candidate_build.py"
P320_BUILDER_IDENTITY = {
    "size": 43_749,
    "sha256": "79f99ac8e918f7c03ad6f5fa8db49b24ffd8378aee543de3538ad49f19b4cc2b",
}
P319_STOCK_BUILDER = ANALYSIS / "s22plus_fyg8_p319_stock_candidate_build.py"
P319_FIXED_IMAGE = artifact_identity.P319_IMAGE
P319_MODULE = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "stock-witness-runtime-v1-20260821-55/module-bytes/"
    "s22plus_dwc3_event_latch.ko"
)
P319_MODULE_IDENTITY = {
    "size": 423_232,
    "sha256": "27be8abfe121867e50b0f8b2094fff1d615181e2e0168e5c37e9f8fab2364a2b",
}
P319_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
O2_LOADER_CORE = ROOT / "workspace/public/src/native-init/s22plus_o2_loader_core.h"
P321_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p321_stock_process_v2_adapter.py"
P321_IDENTITY_SOURCE = REVALIDATION / "s22plus_fyg8_p321_artifact_identity.py"

DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p321/"
    "stock-candidate-build-v1-20260831-02"
)
SCHEMA = "s22plus-fyg8-p321-stock-candidate-build-v1"
VERDICT = "PASS_P321_STOCK_CANDIDATE_BUILD_H0_IDENTITY_JOINED"
STATUS = "IMPLEMENTED_H0_IDENTITY_JOINED_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P319_RUN_ID = artifact_identity.P319_RUN_ID
P320_RUN_ID = artifact_identity.P320_RUN_ID
P321_RUN_ID = artifact_identity.P321_RUN_ID
P321_RUN_ID_HEX = artifact_identity.P321_RUN_ID_HEX
P319_IMAGE_IDENTITY = artifact_identity.P319_IMAGE_IDENTITY
P319_ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


class AuditError(RuntimeError):
    """A P3.21 source, transform, package, or identity join differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


P321_SOURCE_INPUTS = {
    "p321-stock-candidate-build.py": ("p321_stock_candidate_build.py", SELF_SOURCE),
    "p321-stock-process-v2-adapter.py": ("p321_stock_process_v2_adapter.py", P321_ADAPTER_SOURCE),
    "p321-artifact-identity.py": ("p321_artifact_identity.py", P321_IDENTITY_SOURCE),
}


def _current_p321_sources() -> dict[str, bytes]:
    return {
        helper_name: stable_bytes(path, f"current {helper_name}", 8 * 1024 * 1024)
        for helper_name, path in (
            ("p321_stock_candidate_build.py", SELF_SOURCE),
            ("p321_stock_process_v2_adapter.py", P321_ADAPTER_SOURCE),
            ("p321_artifact_identity.py", P321_IDENTITY_SOURCE),
        )
    }


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
        raise AuditError(f"{label} is unavailable") from exc
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
        raise AuditError(f"{label} identity differs")
    return payload


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("ascii")


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = item
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root is not an object")
    return value


def _mkdir(path: Path) -> None:
    path.mkdir(mode=0o700)
    path.chmod(0o700)


def _write_exclusive(path: Path, payload: bytes, mode: int = 0o400) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        mode,
    )
    try:
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise AuditError(f"short private publication: {path.name}")
            offset += written
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_nlink != 1
            or state.st_size != len(payload)
            or stat.S_IMODE(state.st_mode) != mode
        ):
            raise AuditError(f"private publication identity differs: {path.name}")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _load_source(path: Path, expected: Mapping[str, Any], name: str) -> tuple[types.ModuleType, bytes]:
    source = stable_bytes(path, f"bound {name} source", 8 * 1024 * 1024, expected)
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(compile(source.decode("utf-8"), str(path), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise AuditError(f"bound {name} failed to load") from exc
    return module, source


def _copy_input(source: Path, destination: Path, expected: Mapping[str, Any], label: str) -> dict[str, Any]:
    payload = stable_bytes(source, label, 128 * 1024 * 1024, expected)
    _write_exclusive(destination, payload)
    return identity(payload)


def _copy_transformed_input(destination: Path, payload: bytes) -> dict[str, Any]:
    _write_exclusive(destination, payload)
    return identity(payload)


def _replace_base_image(base_boot: bytes, old_image: bytes, new_image: bytes) -> tuple[bytes, dict[str, Any]]:
    """Replace the sole P319 raw Image span in the fixed-size P311 base boot."""
    if len(old_image) != len(new_image) or not old_image or not new_image:
        raise AuditError("P321 base-boot Image replacement sizes differ")
    count = base_boot.count(old_image)
    if count != 1:
        raise AuditError("P311 base boot does not contain one exact P319 Image")
    offset = base_boot.find(old_image)
    if offset != 4096:
        raise AuditError("P311 base boot kernel offset differs")
    replaced = base_boot[:offset] + new_image + base_boot[offset + len(old_image):]
    if len(replaced) != len(base_boot):
        raise AuditError("P321 base-boot Image replacement changed size")
    if (
        replaced[:offset] != base_boot[:offset]
        or replaced[offset + len(new_image):] != base_boot[offset + len(old_image):]
    ):
        raise AuditError("P321 base-boot replacement changed bytes outside Image")
    return replaced, {
        "offset": offset,
        "size": len(old_image),
        "old_image": identity(old_image),
        "new_image": identity(new_image),
        "old_occurrences": count,
        "outside_image_unchanged": True,
    }


def _strict_children(path: Path, expected: set[str], label: str) -> None:
    try:
        state = path.lstat()
        children = {child.name for child in path.iterdir()}
    except OSError as exc:
        raise AuditError(f"{label} is unavailable") from exc
    if (
        stat.S_ISLNK(state.st_mode)
        or not stat.S_ISDIR(state.st_mode)
        or stat.S_IMODE(state.st_mode) != 0o700
        or children != expected
    ):
        raise AuditError(f"{label} child set differs")


def _load_p320() -> tuple[types.ModuleType, bytes]:
    return _load_source(P320_BUILDER_SOURCE, P320_BUILDER_IDENTITY, "P320 builder")


def _prepare_helpers(helper: types.ModuleType) -> tuple[types.ModuleType, types.ModuleType, dict[str, bytes]]:
    wiring, envelope, helper_sources = helper._bind_p320_helpers()
    observer, observer_source = helper._bind_observer_contract()
    helper_sources["p320_observer_contract.py"] = observer_source
    return wiring, observer, helper_sources | {
        "p320_kmsg_record_envelope.py": helper_sources["p319_kmsg_record_envelope.py"],
    }


def _build_once(output_root: Path) -> dict[str, Any]:
    p321_sources = _current_p321_sources()
    helper, p320_source = _load_p320()
    live_result, _live_payload = helper._load_live_result()
    _wiring, observer, helper_sources = _prepare_helpers(helper)
    packager, packager_source = helper._load_bound_module(
        helper.P319_STOCK_BUILDER,
        helper.P319_STOCK_BUILDER_IDENTITY,
        "p319_stock_builder_bound_for_p321",
    )
    packager.RUN_ID = P321_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    rollback_before = helper.stable_bytes(
        helper.P319_ROLLBACK_AP,
        "P319 rollback before P321 build",
        64 * 1024 * 1024,
        helper.P319_ROLLBACK_IDENTITY,
    )
    old_image = stable_bytes(P319_FIXED_IMAGE, "P319 source Image", 64 * 1024 * 1024, P319_IMAGE_IDENTITY)
    try:
        image_bytes, image_transform = artifact_identity.transform_image(old_image)
    except artifact_identity.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc

    original_runtime = helper.stable_bytes(
        helper.P319_SOURCE_ROOT / helper.RUNTIME_INCLUDE_NAME,
        "P319 runtime source",
        2 * 1024 * 1024,
        helper.P319_RUNTIME_IDENTITY,
        required_mode=0o400,
        required_nlink=1,
    )
    original_wrapper = helper.stable_bytes(
        helper.P319_SOURCE_ROOT / helper.RUNTIME_NAME,
        "P319 runtime wrapper",
        2 * 1024 * 1024,
        helper.P319_SOURCE_IDENTITIES[helper.RUNTIME_NAME],
        required_mode=0o400,
        required_nlink=1,
    )
    transformed_runtime, runtime_transform = helper.transform_runtime(original_runtime, observer)
    transformed_wrapper, wrapper_transform = helper.transform_wrapper(original_wrapper, observer)

    _mkdir(output_root)
    input_root = output_root / "inputs"
    _mkdir(input_root)
    input_identities: dict[str, dict[str, Any]] = {}
    input_identities["p319-live-result.json"] = _copy_input(
        helper.P319_RESULT,
        input_root / "p319-live-result.json",
        helper.P319_RESULT_IDENTITY,
        "P319 live result",
    )
    input_identities["p320-stock-candidate-build.py"] = _copy_input(
        P320_BUILDER_SOURCE,
        input_root / "p320-stock-candidate-build.py",
        P320_BUILDER_IDENTITY,
        "P320 builder",
    )
    input_identities["p319-stock-candidate-build.py"] = _copy_input(
        helper.P319_STOCK_BUILDER,
        input_root / "p319-stock-candidate-build.py",
        helper.P319_STOCK_BUILDER_IDENTITY,
        "P319 builder",
    )
    input_identities["p320-kmsg-witness-wiring.py"] = _copy_input(
        helper.P320_WIRING,
        input_root / "p320-kmsg-witness-wiring.py",
        helper.P320_WIRING_IDENTITY,
        "P320 wiring",
    )
    input_identities["p320-observer-contract.py"] = _copy_input(
        helper.P320_OBSERVER,
        input_root / "p320-observer-contract.py",
        helper.P320_OBSERVER_SOURCE_IDENTITY,
        "P320 observer contract",
    )
    input_identities["p319-kmsg-record-envelope.py"] = _copy_input(
        helper.P319_ENVELOPE,
        input_root / "p319-kmsg-record-envelope.py",
        helper.P319_ENVELOPE_IDENTITY,
        "P319 envelope",
    )
    input_identities["s22plus_o2_loader_core.h"] = _copy_input(
        helper.O2_LOADER_CORE,
        input_root / "s22plus_o2_loader_core.h",
        helper.O2_LOADER_CORE_IDENTITY,
        "O2 loader helper",
    )
    input_identities["p321-stock-process-v2-adapter.py"] = _copy_input(
        P321_ADAPTER_SOURCE,
        input_root / "p321-stock-process-v2-adapter.py",
        identity(p321_sources["p321_stock_process_v2_adapter.py"]),
        "P321 adapter",
    )
    input_identities["p321-artifact-identity.py"] = _copy_input(
        P321_IDENTITY_SOURCE,
        input_root / "p321-artifact-identity.py",
        identity(p321_sources["p321_artifact_identity.py"]),
        "P321 artifact identity helper",
    )
    input_identities["p321-stock-candidate-build.py"] = _copy_input(
        SELF_SOURCE,
        input_root / "p321-stock-candidate-build.py",
        identity(p321_sources["p321_stock_candidate_build.py"]),
        "P321 candidate builder",
    )
    input_identities["fixed-Image"] = _copy_transformed_input(input_root / "fixed-Image", image_bytes)
    input_identities["p311-base-boot.img"] = _copy_input(
        helper.P319_BASE_BOOT,
        input_root / "p311-base-boot.img",
        live_result["phase2"]["candidate"]["base"],
        "P311 base boot",
    )
    input_identities[helper.CHILD_NAME] = _copy_input(
        helper.P319_CHILD_SOURCE,
        input_root / helper.CHILD_NAME,
        helper.P319_CHILD_IDENTITY,
        "P319 child source",
    )
    base_boot = stable_bytes(
        input_root / "p311-base-boot.img",
        "P321 base boot source",
        128 * 1024 * 1024,
        live_result["phase2"]["candidate"]["base"],
    )
    prepared_base_boot, base_replacement = _replace_base_image(
        base_boot,
        old_image,
        image_bytes,
    )
    source_identities = helper._copy_source_closure(
        output_root,
        live_result,
        {
            helper.RUNTIME_INCLUDE_NAME: transformed_runtime,
            helper.RUNTIME_NAME: transformed_wrapper,
        },
    )
    module_root = output_root / "module-bytes"
    _mkdir(module_root)
    _copy_input(
        P319_MODULE,
        module_root / "s22plus_dwc3_event_latch.ko",
        P319_MODULE_IDENTITY,
        "P319 latch module",
    )
    phase2 = helper._build_phase2(
        output_root,
        packager,
        prepared_base_boot,
        stable_bytes(input_root / "fixed-Image", "P321 transformed Image", 64 * 1024 * 1024, identity(image_bytes)),
        rollback_before,
    )
    init_bytes = stable_bytes(
        output_root / "userspace-a/init",
        "P321 /init",
        2 * 1024 * 1024,
        phase2["userspace"]["a"]["init"],
        mode=0o400,
        nlink=1,
    )
    child_bytes = stable_bytes(
        output_root / "userspace-a/s22-e1-child",
        "P321 child",
        2 * 1024 * 1024,
        phase2["userspace"]["a"]["child"],
        mode=0o400,
        nlink=1,
    )
    try:
        artifact_a = artifact_identity.inspect_ap(
            output_root / "candidate-a/odin4/AP.tar.md5",
            expected_run_id=P321_RUN_ID,
            expected_image=image_bytes,
            expected_init=init_bytes,
            expected_child=child_bytes,
            expected_ap=phase2["candidate"]["a"]["ap_tar_md5"],
            label="P321 candidate A AP",
        )
        artifact_b = artifact_identity.inspect_ap(
            output_root / "candidate-b/odin4/AP.tar.md5",
            expected_run_id=P321_RUN_ID,
            expected_image=image_bytes,
            expected_init=init_bytes,
            expected_child=child_bytes,
            expected_ap=phase2["candidate"]["b"]["ap_tar_md5"],
            label="P321 candidate B AP",
        )
    except artifact_identity.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    if artifact_a != artifact_b:
        raise AuditError("P321 AP A/B artifact identity differs")
    try:
        rollback_identity = artifact_identity.validate_rollback_ap(
            helper.P319_ROLLBACK_AP,
            helper.P319_ROLLBACK_IDENTITY,
        )
    except artifact_identity.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    phase2["candidate"]["fixed_image_identity"] = identity(image_bytes)
    phase2["candidate"]["base_boot_replacement"] = base_replacement
    phase2["candidate"]["run_id_join"] = {
        "image_run_id_hex": P321_RUN_ID_HEX,
        "init_run_id_hex": P321_RUN_ID_HEX,
        "joined": True,
        "a": artifact_a,
        "b": artifact_b,
    }
    phase2["rollback"]["artifact_identity"] = rollback_identity
    helper_sources.update({
        "p320_stock_candidate_build.py": p320_source,
        "p321_stock_candidate_build.py": p321_sources["p321_stock_candidate_build.py"],
        "p321_stock_process_v2_adapter.py": p321_sources["p321_stock_process_v2_adapter.py"],
        "p321_artifact_identity.py": p321_sources["p321_artifact_identity.py"],
    })
    helper_sources["p319_stock_candidate_build.py"] = packager_source
    tools = {
        name: dict(packager.TOOL_IDENTITIES[name])
        for name in sorted(packager.TOOL_IDENTITIES)
    }
    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": STATUS,
        "target": TARGET,
        "run_id_hex": P321_RUN_ID_HEX,
        "scope": {
            "tier": "H0",
            "host_only": True,
            "device_contact": False,
            "adb_commands": 0,
            "odin_invocations": 0,
            "candidate_transfers": 0,
            "rollback_transfers": 0,
            "live_authority_created": False,
            "replay": False,
        },
        "lineage": {
            "predecessor_p320_run_id": P320_RUN_ID.hex(),
            "predecessor_p319_run_id": P319_RUN_ID.hex(),
            "p319_image": P319_IMAGE_IDENTITY,
            "p319_rollback": helper.P319_ROLLBACK_IDENTITY,
            "p320_builder": {"path": str(P320_BUILDER_SOURCE.relative_to(ROOT)), **P320_BUILDER_IDENTITY},
            "image_transform": image_transform,
            "fresh_run_id": P321_RUN_ID_HEX,
            "run_id_join": "Image_IKCONFIG_and_rodata_to_init_raw_bytes",
        },
        "inputs": input_identities,
        "module_bytes": {"s22plus_dwc3_event_latch.ko": P319_MODULE_IDENTITY},
        "source_closure": source_identities,
        "helper_sources": {
            name: identity(payload) for name, payload in helper_sources.items()
        },
        "tools": tools,
        "runtime_transform": runtime_transform,
        "wrapper_transform": wrapper_transform,
        "phase2": phase2,
        "limitations": [
            "P321 changes only the run-ID-bearing kernel string and embedded IKCONFIG stream; all Image provider/CRC sections remain byte-identical.",
            "P321 reuses the reviewed P320 observer logic under a fresh adapter run-ID binding and rejects P319/P320 Carrier records.",
            "The real packaged AP is unpacked after build; Image IKCONFIG, compiled Image string, and /init raw bytes must join to one P321 ID.",
            "This H0 unit creates no approval, D0/D1/F1/recovery/replay/live authority.",
        ],
        "preservation": {
            "p319_consumed_candidate_unchanged": True,
            "p320_source_reused_by_exact_hash": True,
            "p320_run_id_rejected_by_adapter": True,
            "p319_run_id_rejected_by_adapter": True,
            "image_size_and_layout_preserved": True,
            "image_provider_and_crc_regions_preserved": True,
            "ap_boot_only": True,
            "ab_artifact_identity_equal": True,
            "rollback_untouched": True,
        },
    }
    payload = _json_bytes(result)
    _write_exclusive(output_root / "result.json", payload)
    _fsync_directory(input_root)
    _fsync_directory(output_root / "stock-sources")
    _fsync_directory(module_root)
    _fsync_directory(output_root)
    return result


def build_result(output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P321 output already exists")
    if not output_root.parent.exists():
        output_root.parent.mkdir(mode=0o700, parents=True)
        output_root.parent.chmod(0o700)
    return _build_once(output_root)


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    result_payload = stable_bytes(
        output_root / "result.json",
        "P321 result",
        4 * 1024 * 1024,
        mode=0o400,
        nlink=1,
    )
    result = _strict_json(result_payload, "P321 result")
    if (
        result.get("schema") != SCHEMA
        or result.get("verdict") != VERDICT
        or result.get("status") != STATUS
        or result.get("target") != TARGET
        or result.get("run_id_hex") != P321_RUN_ID_HEX
    ):
        raise AuditError("P321 result header differs")
    expected_scope = {
        "tier": "H0",
        "host_only": True,
        "device_contact": False,
        "adb_commands": 0,
        "odin_invocations": 0,
        "candidate_transfers": 0,
        "rollback_transfers": 0,
        "live_authority_created": False,
        "replay": False,
    }
    if result.get("scope") != expected_scope:
        raise AuditError("P321 result safety scope differs")
    _strict_children(
        output_root,
        {"inputs", "stock-sources", "module-bytes", "userspace-a", "userspace-b", "candidate-a", "candidate-b", "result.json"},
        "P321 output root",
    )
    input_identities = result.get("inputs")
    if not isinstance(input_identities, dict):
        raise AuditError("P321 input receipt is missing")
    _strict_children(output_root / "inputs", set(input_identities), "P321 input bundle")
    _strict_children(output_root / "module-bytes", {"s22plus_dwc3_event_latch.ko"}, "P321 module bundle")
    helper, _ = _load_p320()
    live_result, _ = helper._load_live_result()
    _wiring, observer, _helper_sources = _prepare_helpers(helper)
    current_p321_sources = _current_p321_sources()
    helper_receipts = result.get("helper_sources")
    if not isinstance(helper_receipts, dict):
        raise AuditError("P321 helper source receipts are missing")
    for input_name, (helper_name, source_path) in P321_SOURCE_INPUTS.items():
        current = current_p321_sources[helper_name]
        expected = identity(current)
        if helper_receipts.get(helper_name) != expected:
            raise AuditError(f"P321 helper source receipt differs: {helper_name}")
        copied = stable_bytes(
            output_root / "inputs" / input_name,
            f"P321 copied {helper_name}",
            8 * 1024 * 1024,
            expected,
            mode=0o400,
            nlink=1,
        )
        if copied != current:
            raise AuditError(f"P321 copied source differs: {helper_name}")
    old_image = stable_bytes(P319_FIXED_IMAGE, "P319 source Image", 64 * 1024 * 1024, P319_IMAGE_IDENTITY)
    image_bytes, transform = artifact_identity.transform_image(old_image)
    if result.get("lineage", {}).get("image_transform") != transform:
        raise AuditError("P321 Image transform receipt differs")
    image = stable_bytes(output_root / "inputs/fixed-Image", "P321 output Image", 64 * 1024 * 1024, identity(image_bytes), mode=0o400, nlink=1)
    try:
        artifact_identity.validate_image(image)
    except artifact_identity.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    for name, expected in input_identities.items():
        expected_identity = expected if name != "fixed-Image" else identity(image_bytes)
        stable_bytes(output_root / "inputs" / name, f"P321 input {name}", 128 * 1024 * 1024, expected_identity, mode=0o400, nlink=1)
    original_base_boot = stable_bytes(
        output_root / "inputs/p311-base-boot.img",
        "P321 base boot source",
        128 * 1024 * 1024,
        live_result["phase2"]["candidate"]["base"],
        mode=0o400,
        nlink=1,
    )
    _prepared_base_boot, base_replacement = _replace_base_image(
        original_base_boot,
        old_image,
        image,
    )
    if result.get("phase2", {}).get("candidate", {}).get("base_boot_replacement") != base_replacement:
        raise AuditError("P321 base-boot replacement receipt differs")
    _strict_children(output_root / "userspace-a", {"init", "s22-e1-child"}, "P321 userspace A")
    _strict_children(output_root / "userspace-b", {"init", "s22-e1-child"}, "P321 userspace B")
    userspace = result.get("phase2", {}).get("userspace")
    if not isinstance(userspace, dict) or userspace.get("byte_identical") is not True:
        raise AuditError("P321 userspace A/B metadata differs")
    init = stable_bytes(output_root / "userspace-a/init", "P321 userspace init", 2 * 1024 * 1024, userspace["a"]["init"], mode=0o400, nlink=1)
    child = stable_bytes(output_root / "userspace-a/s22-e1-child", "P321 userspace child", 2 * 1024 * 1024, userspace["a"]["child"], mode=0o400, nlink=1)
    if init != stable_bytes(output_root / "userspace-b/init", "P321 userspace B init", 2 * 1024 * 1024, userspace["b"]["init"], mode=0o400, nlink=1):
        raise AuditError("P321 userspace init A/B differs")
    if child != stable_bytes(output_root / "userspace-b/s22-e1-child", "P321 userspace B child", 2 * 1024 * 1024, userspace["b"]["child"], mode=0o400, nlink=1):
        raise AuditError("P321 userspace child A/B differs")
    packager, _ = helper._load_bound_module(
        helper.P319_STOCK_BUILDER,
        helper.P319_STOCK_BUILDER_IDENTITY,
        "p319_stock_builder_audit_bound_for_p321",
    )
    packager.RUN_ID = P321_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    candidate = result.get("phase2", {}).get("candidate")
    if not isinstance(candidate, dict) or candidate.get("byte_identical") is not True:
        raise AuditError("P321 candidate A/B metadata differs")
    modules = {"s22plus_dwc3_event_latch.ko": stable_bytes(output_root / "module-bytes/s22plus_dwc3_event_latch.ko", "P321 latch", 8 * 1024 * 1024, P319_MODULE_IDENTITY, mode=0o400, nlink=1)}
    overlay = ("s22plus_dwc3_event_latch.ko",)
    for label in ("a", "b"):
        expected_candidate = candidate[label]
        packager._verify_packaged_candidate(
            output_root / f"candidate-{label}",
            expected_candidate,
            init,
            child,
            modules,
            image,
            overlay,
            f"P321-audit-candidate-{label}",
        )
    try:
        artifact_a = artifact_identity.inspect_ap(
            output_root / "candidate-a/odin4/AP.tar.md5",
            expected_run_id=P321_RUN_ID,
            expected_image=image,
            expected_init=init,
            expected_child=child,
            expected_ap=candidate["a"]["ap_tar_md5"],
            label="P321 audit candidate A AP",
        )
        artifact_b = artifact_identity.inspect_ap(
            output_root / "candidate-b/odin4/AP.tar.md5",
            expected_run_id=P321_RUN_ID,
            expected_image=image,
            expected_init=init,
            expected_child=child,
            expected_ap=candidate["b"]["ap_tar_md5"],
            label="P321 audit candidate B AP",
        )
        artifact_identity.validate_rollback_ap(helper.P319_ROLLBACK_AP, helper.P319_ROLLBACK_IDENTITY)
    except artifact_identity.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    if artifact_a != artifact_b or candidate.get("run_id_join", {}).get("a") != artifact_a:
        raise AuditError("P321 AP identity join receipt differs")
    helper._audit_source_output(output_root, result, observer)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    output = args.out if args.out.is_absolute() else ROOT / args.out
    try:
        result = build_result(output, audit_only=args.audit_only)
    except (AuditError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"schema": SCHEMA, "verdict": result["verdict"], "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
