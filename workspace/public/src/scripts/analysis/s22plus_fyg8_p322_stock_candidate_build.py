#!/usr/bin/env python3
"""Build the P3.22 stock candidate with one repaired checkpoint bridge, H0 only.

P3.22 reopens the completed P3.21 host build, copies its exact stock source
closure, and changes only ``p319_stock_bypass_to_pair``.  The fixed P3.19
Image receives a fresh same-length identity transform.  Userspace is rebuilt,
but only ``/init`` changes while the child reproduces its predecessor bytes.
Packaging remains boot-only and deterministic; this module never contacts a
device or invokes Odin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import s22plus_fyg8_p321_stock_candidate_build as p321  # noqa: E402
import s22plus_fyg8_p322_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p322_runtime_repair as repair  # noqa: E402
import s22plus_fyg8_p322_stock_process_v2_adapter as adapter  # noqa: E402


SELF_SOURCE = Path(__file__).resolve()
P321_BUILDER_SOURCE = ANALYSIS / "s22plus_fyg8_p321_stock_candidate_build.py"
P321_BUILDER_IDENTITY = {
    "size": 30_912,
    "sha256": "68821264d18f7b8fb92a252d97c34732c9760dc940c61e09b35e6cbaec6b7567",
}
P321_OUTPUT = p321.DEFAULT_OUTPUT_ROOT
P322_ARTIFACT_SOURCE = REVALIDATION / "s22plus_fyg8_p322_artifact_identity.py"
P322_REPAIR_SOURCE = REVALIDATION / "s22plus_fyg8_p322_runtime_repair.py"
P322_ADAPTER_SOURCE = REVALIDATION / "s22plus_fyg8_p322_stock_process_v2_adapter.py"

DEFAULT_OUTPUT_ROOT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p322/"
    "stock-candidate-build-v1-20260831-02"
)
SCHEMA = "s22plus-fyg8-p322-stock-candidate-build-v1"
VERDICT = "PASS_P322_STOCK_CANDIDATE_BUILD_H0_CHECKPOINT_REPAIRED"
STATUS = "IMPLEMENTED_H0_CHECKPOINT_REPAIRED_REVIEW_PENDING"
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
P322_RUN_ID = artifact.P322_RUN_ID
P322_RUN_ID_HEX = artifact.P322_RUN_ID_HEX


class AuditError(RuntimeError):
    """The P3.22 source, artifact, or predecessor binding differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("ascii")


def _strict_json(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise AuditError(f"{label} has duplicate key {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} is not an object")
    return value


def _stable(
    path: Path,
    label: str,
    maximum: int,
    expected: dict[str, Any] | None = None,
    *,
    mode: int | None = None,
    nlink: int | None = None,
) -> bytes:
    try:
        return p321.stable_bytes(
            path,
            label,
            maximum,
            expected,
            mode=mode,
            nlink=nlink,
        )
    except (p321.AuditError, OSError) as exc:
        raise AuditError(str(exc)) from exc


def _current_sources() -> dict[str, bytes]:
    return {
        "p322_stock_candidate_build.py": _stable(
            SELF_SOURCE, "P322 builder source", 2 << 20
        ),
        "p322_artifact_identity.py": _stable(
            P322_ARTIFACT_SOURCE, "P322 artifact helper source", 2 << 20
        ),
        "p322_runtime_repair.py": _stable(
            P322_REPAIR_SOURCE, "P322 runtime repair source", 2 << 20
        ),
        "p322_stock_process_v2_adapter.py": _stable(
            P322_ADAPTER_SOURCE, "P322 adapter source", 2 << 20
        ),
    }


def _predecessor() -> tuple[dict[str, Any], bytes, bytes]:
    p321_source = _stable(
        P321_BUILDER_SOURCE,
        "P321 builder source",
        2 << 20,
        P321_BUILDER_IDENTITY,
    )
    try:
        value = p321.audit_existing(P321_OUTPUT)
    except (p321.AuditError, OSError, subprocess.SubprocessError) as exc:
        raise AuditError("P321 predecessor audit failed") from exc
    payload = _stable(
        P321_OUTPUT / "result.json",
        "P321 predecessor result",
        4 << 20,
        mode=0o400,
        nlink=1,
    )
    if _strict_json(payload, "P321 predecessor result") != value:
        raise AuditError("P321 predecessor result differs after audit")
    return value, payload, p321_source


def _copy(path: Path, destination: Path, expected: dict[str, Any], label: str) -> dict[str, Any]:
    payload = _stable(path, label, 128 << 20, expected)
    p321._write_exclusive(destination, payload)
    return identity(payload)


def _copy_bytes(destination: Path, payload: bytes) -> dict[str, Any]:
    p321._write_exclusive(destination, payload)
    return identity(payload)


def _copy_source_closure(
    output_root: Path, predecessor: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    source_root = output_root / "stock-sources"
    p321._mkdir(source_root)
    receipts: dict[str, dict[str, Any]] = {}
    repair_receipt: dict[str, Any] | None = None
    expected_closure = predecessor.get("source_closure")
    if not isinstance(expected_closure, dict) or len(expected_closure) != 12:
        raise AuditError("P321 source closure is invalid")
    for name, expected in sorted(expected_closure.items()):
        before = _stable(
            P321_OUTPUT / "stock-sources" / name,
            f"P321 source {name}",
            2 << 20,
            expected,
            mode=0o400,
            nlink=1,
        )
        after = before
        if name == "s22plus_fyg8_p290_e3_runtime.inc.c":
            try:
                after = repair.transform_runtime_include(before)
                repair_receipt = repair.validate_repair(before, after) | {
                    "before_identity": identity(before),
                    "after_identity": identity(after),
                }
            except repair.RuntimeRepairError as exc:
                raise AuditError(str(exc)) from exc
        p321._write_exclusive(source_root / name, after)
        receipts[name] = identity(after)
    if repair_receipt is None:
        raise AuditError("P322 runtime repair target is absent")
    p321._fsync_directory(source_root)
    return receipts, repair_receipt


def _load_packager() -> tuple[Any, Any, bytes]:
    helper, _p320_source = p321._load_p320()
    packager, packager_source = helper._load_bound_module(
        helper.P319_STOCK_BUILDER,
        helper.P319_STOCK_BUILDER_IDENTITY,
        "p319_stock_builder_bound_for_p322",
    )
    packager.RUN_ID = P322_RUN_ID
    packager._ACTIVE_TOOLS = None
    packager._bind_tools()
    return helper, packager, packager_source


def _build_once(output_root: Path) -> dict[str, Any]:
    sources = _current_sources()
    predecessor, predecessor_payload, p321_source = _predecessor()
    try:
        adapter_audit = adapter.audit()
    except Exception as exc:
        raise AuditError("P322 adapter audit failed") from exc
    helper, packager, packager_source = _load_packager()

    old_image = _stable(
        artifact.P319_IMAGE,
        "P319 source Image",
        64 << 20,
        artifact.P319_IMAGE_IDENTITY,
    )
    try:
        image, image_transform = artifact.transform_image(old_image)
        artifact.validate_image(image)
    except artifact.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    rollback_before = _stable(
        helper.P319_ROLLBACK_AP,
        "exact rollback before P322 build",
        64 << 20,
        helper.P319_ROLLBACK_IDENTITY,
    )

    p321._mkdir(output_root)
    inputs = output_root / "inputs"
    p321._mkdir(inputs)
    input_receipts: dict[str, dict[str, Any]] = {}
    input_receipts["p321-result.json"] = _copy_bytes(
        inputs / "p321-result.json", predecessor_payload
    )
    input_receipts["p321-stock-candidate-build.py"] = _copy_bytes(
        inputs / "p321-stock-candidate-build.py", p321_source
    )
    for key, payload in sorted(sources.items()):
        filename = key.replace("_", "-")
        input_receipts[filename] = _copy_bytes(inputs / filename, payload)
    image_receipt = _copy_bytes(inputs / "fixed-Image", image)
    input_receipts["fixed-Image"] = image_receipt
    input_receipts["p311-base-boot.img"] = _copy(
        P321_OUTPUT / "inputs/p311-base-boot.img",
        inputs / "p311-base-boot.img",
        predecessor["inputs"]["p311-base-boot.img"],
        "P321 base boot input",
    )
    input_receipts["child-source.c"] = _copy(
        P321_OUTPUT / "inputs/child-source.c",
        inputs / "child-source.c",
        predecessor["inputs"]["child-source.c"],
        "P321 child source input",
    )
    base_boot = _stable(
        inputs / "p311-base-boot.img",
        "P322 base boot input",
        128 << 20,
        input_receipts["p311-base-boot.img"],
        mode=0o400,
        nlink=1,
    )
    prepared_boot, replacement = p321._replace_base_image(
        base_boot, old_image, image
    )

    source_receipts, repair_receipt = _copy_source_closure(output_root, predecessor)
    module_root = output_root / "module-bytes"
    p321._mkdir(module_root)
    module_identity = predecessor["module_bytes"]["s22plus_dwc3_event_latch.ko"]
    _copy(
        P321_OUTPUT / "module-bytes/s22plus_dwc3_event_latch.ko",
        module_root / "s22plus_dwc3_event_latch.ko",
        module_identity,
        "P321 latch module",
    )
    phase2 = helper._build_phase2(
        output_root,
        packager,
        prepared_boot,
        image,
        rollback_before,
    )
    init = _stable(
        output_root / "userspace-a/init",
        "P322 /init",
        2 << 20,
        phase2["userspace"]["a"]["init"],
        mode=0o400,
        nlink=1,
    )
    child = _stable(
        output_root / "userspace-a/s22-e1-child",
        "P322 child",
        2 << 20,
        phase2["userspace"]["a"]["child"],
        mode=0o400,
        nlink=1,
    )
    try:
        joined = [
            artifact.inspect_ap(
                output_root / f"candidate-{label}/odin4/AP.tar.md5",
                expected_run_id=P322_RUN_ID,
                expected_image=image,
                expected_init=init,
                expected_child=child,
                expected_ap=phase2["candidate"][label]["ap_tar_md5"],
                label=f"P322 candidate {label.upper()} AP",
            )
            for label in ("a", "b")
        ]
        rollback = artifact.validate_rollback_ap(
            helper.P319_ROLLBACK_AP, helper.P319_ROLLBACK_IDENTITY
        )
    except artifact.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    if joined[0] != joined[1]:
        raise AuditError("P322 A/B AP identity join differs")
    predecessor_ap = predecessor["phase2"]["candidate"]["a"]["ap_tar_md5"]
    if phase2["candidate"]["a"]["ap_tar_md5"] == predecessor_ap:
        raise AuditError("P322 AP repeats consumed P321 AP")
    phase2["candidate"]["fixed_image_identity"] = image_receipt
    phase2["candidate"]["base_boot_replacement"] = replacement
    phase2["candidate"]["run_id_join"] = {
        "run_id_hex": P322_RUN_ID_HEX,
        "joined": True,
        "a": joined[0],
        "b": joined[1],
    }
    phase2["candidate"]["differs_from_consumed_p321"] = True
    phase2["rollback"]["artifact_identity"] = rollback

    result = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": STATUS,
        "target": TARGET,
        "run_id_hex": P322_RUN_ID_HEX,
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
            "predecessor_run_id": artifact.P321_PREDECESSOR_RUN_ID_HEX,
            "predecessor_result": identity(predecessor_payload),
            "predecessor_ap": predecessor_ap,
            "fresh_run_id": P322_RUN_ID_HEX,
            "image_transform": image_transform,
            "runtime_repair": repair_receipt,
        },
        "inputs": input_receipts,
        "source_closure": source_receipts,
        "module_bytes": {"s22plus_dwc3_event_latch.ko": module_identity},
        "helper_sources": {
            "p321_stock_candidate_build.py": identity(p321_source),
            "p319_stock_candidate_build.py": identity(packager_source),
            **{name: identity(payload) for name, payload in sources.items()},
        },
        "adapter_audit": adapter_audit,
        "tools": {
            name: dict(packager.TOOL_IDENTITIES[name])
            for name in sorted(packager.TOOL_IDENTITIES)
        },
        "phase2": phase2,
        "limitations": [
            "P322 changes only the Image run identity and one userspace checkpoint bridge.",
            "P322 advances the missing finite generation range 92 through 104 before stock publication.",
            "No kernel Full-LTO, device contact, approval, D0, D1, F1, recovery, replay, or live authority is created.",
        ],
        "preservation": {
            "p321_consumed_candidate_unchanged": True,
            "p321_source_closure_reopened": True,
            "runtime_delta_one_function": True,
            "diagnostic_provider_widening": False,
            "image_size_and_layout_preserved": True,
            "ap_boot_only": True,
            "ab_artifact_identity_equal": True,
            "rollback_untouched": True,
        },
    }
    p321._write_exclusive(output_root / "result.json", _json_bytes(result))
    for directory in (inputs, source_root := output_root / "stock-sources", module_root, output_root):
        p321._fsync_directory(directory)
    del source_root
    return result


def build_result(
    output_root: Path = DEFAULT_OUTPUT_ROOT, *, audit_only: bool = False
) -> dict[str, Any]:
    output_root = output_root.absolute()
    if audit_only:
        return audit_existing(output_root)
    if output_root.exists() or output_root.is_symlink():
        raise AuditError("P322 output already exists")
    output_root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.parent.chmod(0o700)
    return _build_once(output_root)


def audit_existing(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.absolute()
    payload = _stable(
        output_root / "result.json", "P322 result", 4 << 20, mode=0o400, nlink=1
    )
    result = _strict_json(payload, "P322 result")
    if (
        result.get("schema") != SCHEMA
        or result.get("verdict") != VERDICT
        or result.get("status") != STATUS
        or result.get("target") != TARGET
        or result.get("run_id_hex") != P322_RUN_ID_HEX
        or result.get("scope", {}).get("device_contact") is not False
        or result.get("scope", {}).get("live_authority_created") is not False
    ):
        raise AuditError("P322 result header or scope differs")
    expected_root = {
        "inputs", "stock-sources", "module-bytes", "userspace-a", "userspace-b",
        "candidate-a", "candidate-b", "result.json",
    }
    p321._strict_children(output_root, expected_root, "P322 output root")

    sources = _current_sources()
    predecessor, predecessor_payload, p321_source = _predecessor()
    helper_receipts = result.get("helper_sources", {})
    if helper_receipts.get("p321_stock_candidate_build.py") != identity(p321_source):
        raise AuditError("P322 P321 builder receipt differs")
    for name, source in sources.items():
        if helper_receipts.get(name) != identity(source):
            raise AuditError(f"P322 helper source receipt differs: {name}")
    if result.get("lineage", {}).get("predecessor_result") != identity(predecessor_payload):
        raise AuditError("P322 predecessor result receipt differs")

    image_source = _stable(
        artifact.P319_IMAGE, "P319 source Image", 64 << 20, artifact.P319_IMAGE_IDENTITY
    )
    try:
        image, image_transform = artifact.transform_image(image_source)
    except artifact.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
    if result["lineage"].get("image_transform") != image_transform:
        raise AuditError("P322 Image transform receipt differs")
    _stable(
        output_root / "inputs/fixed-Image", "P322 fixed Image", 64 << 20,
        identity(image), mode=0o400, nlink=1,
    )

    source_receipts = result.get("source_closure")
    if not isinstance(source_receipts, dict) or set(source_receipts) != set(predecessor["source_closure"]):
        raise AuditError("P322 source closure set differs")
    runtime_name = "s22plus_fyg8_p290_e3_runtime.inc.c"
    for name, predecessor_identity in sorted(predecessor["source_closure"].items()):
        before = _stable(
            P321_OUTPUT / "stock-sources" / name,
            f"P321 audit source {name}", 2 << 20, predecessor_identity,
            mode=0o400, nlink=1,
        )
        expected = repair.transform_runtime_include(before) if name == runtime_name else before
        _stable(
            output_root / "stock-sources" / name,
            f"P322 audit source {name}", 2 << 20, identity(expected),
            mode=0o400, nlink=1,
        )
        if source_receipts[name] != identity(expected):
            raise AuditError(f"P322 source receipt differs: {name}")
    runtime_before = _stable(
        P321_OUTPUT / "stock-sources" / runtime_name,
        "P321 runtime repair input", 2 << 20,
        predecessor["source_closure"][runtime_name], mode=0o400, nlink=1,
    )
    runtime_after = repair.transform_runtime_include(runtime_before)
    expected_repair = repair.validate_repair(runtime_before, runtime_after) | {
        "before_identity": identity(runtime_before),
        "after_identity": identity(runtime_after),
    }
    if result["lineage"].get("runtime_repair") != expected_repair:
        raise AuditError("P322 runtime repair receipt differs")

    helper, packager, _packager_source = _load_packager()
    phase2 = result.get("phase2")
    if not isinstance(phase2, dict) or phase2.get("built") is not True:
        raise AuditError("P322 Phase-2 result is incomplete")
    userspace = phase2.get("userspace", {})
    init = _stable(
        output_root / "userspace-a/init", "P322 audit init", 2 << 20,
        userspace["a"]["init"], mode=0o400, nlink=1,
    )
    child = _stable(
        output_root / "userspace-a/s22-e1-child", "P322 audit child", 2 << 20,
        userspace["a"]["child"], mode=0o400, nlink=1,
    )
    if init != _stable(
        output_root / "userspace-b/init", "P322 audit init B", 2 << 20,
        userspace["b"]["init"], mode=0o400, nlink=1,
    ) or child != _stable(
        output_root / "userspace-b/s22-e1-child", "P322 audit child B", 2 << 20,
        userspace["b"]["child"], mode=0o400, nlink=1,
    ):
        raise AuditError("P322 userspace A/B bytes differ")
    module_identity = result["module_bytes"]["s22plus_dwc3_event_latch.ko"]
    modules = {"s22plus_dwc3_event_latch.ko": _stable(
        output_root / "module-bytes/s22plus_dwc3_event_latch.ko",
        "P322 latch module", 8 << 20, module_identity, mode=0o400, nlink=1,
    )}
    candidate = phase2.get("candidate", {})
    joined = []
    for label in ("a", "b"):
        packager._verify_packaged_candidate(
            output_root / f"candidate-{label}", candidate[label], init, child,
            modules, image, ("s22plus_dwc3_event_latch.ko",), f"P322-audit-{label}",
        )
        try:
            joined.append(artifact.inspect_ap(
                output_root / f"candidate-{label}/odin4/AP.tar.md5",
                expected_run_id=P322_RUN_ID, expected_image=image,
                expected_init=init, expected_child=child,
                expected_ap=candidate[label]["ap_tar_md5"],
                label=f"P322 audit {label.upper()} AP",
            ))
        except artifact.ArtifactIdentityError as exc:
            raise AuditError(str(exc)) from exc
    if joined[0] != joined[1] or candidate.get("run_id_join", {}).get("a") != joined[0]:
        raise AuditError("P322 audited AP join differs")
    try:
        artifact.validate_rollback_ap(helper.P319_ROLLBACK_AP, helper.P319_ROLLBACK_IDENTITY)
    except artifact.ArtifactIdentityError as exc:
        raise AuditError(str(exc)) from exc
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
