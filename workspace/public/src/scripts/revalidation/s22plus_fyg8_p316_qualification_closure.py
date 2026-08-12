#!/usr/bin/env python3
"""Create and validate the P3.16 prepackaging and final closures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import s22plus_fyg8_max77705_custom_surface_contract as surface
import s22plus_fyg8_p316_overlay_contract as overlay


PREPACKAGING_SCHEMA = "s22plus_fyg8_p316_prepackaging_closure_v1"
PREPACKAGING_VERDICT = "PASS_P316_PREPACKAGING_CLOSURE_HOST_ONLY"
FINAL_SCHEMA = "s22plus_fyg8_p316_qualification_closure_v1"
FINAL_VERDICT = "PASS_P316_QUALIFICATION_CLOSURE_HOST_ONLY"
EXPECTED_MODULE_PLAN_COUNT = 64
CANDIDATE_SCHEMA = "s22plus_fyg8_p316_candidate_artifact_result_v1"
CANDIDATE_VERDICT = "PASS_P316_DETERMINISTIC_BOOT_ONLY_CANDIDATE_HOST_ONLY"
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_USERSPACE = Path("workspace/private/outputs/s22plus_fyg8_p316/userspace")
DEFAULT_CANDIDATE_A = Path("workspace/private/outputs/s22plus_fyg8_p316/candidate-a")
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p316/candidate-b")
DEFAULT_PREPACKAGING = Path(
    "workspace/private/outputs/s22plus_fyg8_p316/qualification/"
    "prepackaging-closure.json"
)
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p316/qualification/"
    "qualification-closure.json"
)


class QualificationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii") + b"\n"


def _receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _read_regular(path: Path, label: str, maximum: int = 64 * 1024 * 1024) -> bytes:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or before.st_size > maximum:
            raise QualificationError(f"{label} is not a bounded regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise QualificationError(f"cannot read {label}") from exc
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or len(
        payload
    ) != before.st_size:
        raise QualificationError(f"{label} changed while read")
    return payload


def _read_json(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    payload = _read_regular(path, label)
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise QualificationError(f"{label} is not ASCII JSON") from exc
    if not isinstance(value, dict):
        raise QualificationError(f"{label} root differs")
    return payload, value


def _write_new(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(
        value, indent=2, sort_keys=True, allow_nan=False
    ).encode("ascii") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise QualificationError("short qualification write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _tree_receipts(directory: Path) -> dict[str, dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir():
        raise QualificationError(f"candidate tree missing: {directory}")
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
            raise QualificationError(f"candidate tree entry is indirect: {path}")
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            rows[relative] = _receipt(_read_regular(path, relative, 512 * 1024 * 1024))
    required = {"artifact-result.json", "boot.img", "boot.img.lz4", "odin4/AP.tar.md5"}
    if not required <= set(rows):
        raise QualificationError("candidate tree inventory is incomplete")
    return rows


def _requirements(exact: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": overlay.CONTRACT_ID,
        "run_id": exact["run_id"],
        "fixed_image": exact["fixed_image"],
        "source_receipts": exact["source_receipts"],
        "generated_artifacts": exact["generated_artifacts"],
        "max77705_surface_gate": exact["max77705_surface_gate"],
        "runtime_fixture": exact["runtime_fixture"],
        "late_loader_lifecycle": exact["late_loader_lifecycle"],
        "envelope_fixture": exact["envelope_fixture"],
        "runtime_policy_fixture": exact["runtime_policy_fixture"],
        "process_v2_adapter_fixture": exact["process_v2_adapter_fixture"],
        "sidecar_positive_control": exact["sidecar_positive_control"],
        "telemetry": exact["telemetry"],
        "observer": exact["observer"],
        "packaging_requirements": exact["packaging_requirements"],
        "diagnostic_module": {
            "name": "s22plus_max77705_mux_diag.ko",
            "size": surface.DIAG_MODULE_IDENTITY[0],
            "sha256": surface.DIAG_MODULE_IDENTITY[1],
            "boot_ramdisk_path": "lib/modules/s22plus_max77705_mux_diag.ko",
            "early_plan_membership": False,
            "late_load_only": True,
        },
        "packaging_validator_called_before_packaging": True,
        "missing_or_failed_proof_blocks_packaging": True,
    }


def create_prepackaging_value(root: Path, intent_path: Path) -> dict[str, Any]:
    exact = overlay.verify_intent(root, intent_path)
    requirements = _requirements(exact)
    return {
        "schema": PREPACKAGING_SCHEMA,
        "verdict": PREPACKAGING_VERDICT,
        "target": overlay.TARGET,
        "requirements": requirements,
        "requirements_sha256": hashlib.sha256(_canonical(requirements)).hexdigest(),
        "verified": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "candidate_packaged": False,
            "live_authorized": False,
        },
    }


def validate_prepackaging_artifact(
    value: dict[str, Any], *, root: Path, intent_path: Path | None = None
) -> dict[str, Any]:
    selected = intent_path or root / DEFAULT_INTENT
    expected = create_prepackaging_value(root, selected)
    if value != expected:
        raise QualificationError("P3.16 prepackaging closure differs")
    return {
        "schema": PREPACKAGING_SCHEMA,
        "requirements_sha256": value["requirements_sha256"],
        "diagnostic_module": value["requirements"]["diagnostic_module"],
        "verified": True,
    }


def _validate_candidate_result(
    value: dict[str, Any], *, prepackaging_receipt: dict[str, Any]
) -> None:
    construction = value.get("construction", {})
    safety = value.get("safety", {})
    if (
        value.get("schema") != CANDIDATE_SCHEMA
        or value.get("verdict") != CANDIDATE_VERDICT
        or value.get("prepackaging_closure") != prepackaging_receipt
        or construction.get("diagnostic_staged_path")
        != "lib/modules/s22plus_max77705_mux_diag.ko"
        or construction.get("diagnostic_staged_exactly_once") is not True
        or construction.get("diagnostic_absent_from_base") is not True
        or construction.get("diagnostic_absent_from_early_plan") is not True
        or safety.get("boot_only_ap") is not True
        or safety.get("fixed_p310_image") is not True
        or safety.get("custom_module_binaries_injected") != 1
        or safety.get("device_contact") is not False
    ):
        raise QualificationError("P3.16 candidate result differs")


def create_final_value(
    root: Path,
    intent_path: Path,
    prepackaging_path: Path,
    userspace_path: Path,
    candidate_a: Path,
    candidate_b: Path,
) -> dict[str, Any]:
    exact = overlay.verify_intent(root, intent_path)
    pre_payload, pre = _read_json(prepackaging_path, "P3.16 prepackaging closure")
    validation = validate_prepackaging_artifact(pre, root=root, intent_path=intent_path)
    user_payload, user = _read_json(
        userspace_path / "userspace-result.json", "P3.16 userspace result"
    )
    if (
        user.get("candidate_contract") != exact
        or user.get("two_build_byte_identical") is not True
        or user.get("module_plan_count") != EXPECTED_MODULE_PLAN_COUNT
        or user.get("late_diagnostic_payload_count") != 1
    ):
        raise QualificationError("P3.16 userspace result differs")
    trees = (_tree_receipts(candidate_a), _tree_receipts(candidate_b))
    if trees[0] != trees[1]:
        raise QualificationError("P3.16 candidate A/B trees differ")
    result_payloads = []
    results = []
    for label, directory in (("A", candidate_a), ("B", candidate_b)):
        payload, value = _read_json(
            directory / "artifact-result.json", f"P3.16 candidate {label} result"
        )
        _validate_candidate_result(value, prepackaging_receipt=_receipt(pre_payload))
        result_payloads.append(payload)
        results.append(value)
    if results[0] != results[1]:
        raise QualificationError("P3.16 candidate result semantics differ")
    return {
        "schema": FINAL_SCHEMA,
        "verdict": FINAL_VERDICT,
        "target": overlay.TARGET,
        "candidate_contract": exact,
        "prepackaging_closure": pre,
        "prepackaging_receipt": _receipt(pre_payload),
        "prepackaging_validation": validation,
        "userspace_receipt": _receipt(user_payload),
        "candidate_result_receipt": _receipt(result_payloads[0]),
        "candidate_tree": trees[0],
        "two_userspace_builds_byte_identical": True,
        "two_candidate_packages_byte_identical": True,
        "independent_reconstruction_required": True,
        "verified": True,
        "safety": {
            "host_only": True,
            "device_contact": False,
            "live_authorized": False,
        },
    }


def validate_qualification_artifact(
    value: dict[str, Any],
    *,
    root: Path,
    candidate_tree: dict[str, Any],
    intent_path: Path | None = None,
) -> dict[str, Any]:
    if (
        value.get("schema") != FINAL_SCHEMA
        or value.get("verdict") != FINAL_VERDICT
        or value.get("candidate_tree") != candidate_tree
        or value.get("two_candidate_packages_byte_identical") is not True
        or value.get("independent_reconstruction_required") is not True
        or value.get("verified") is not True
    ):
        raise QualificationError("P3.16 final qualification differs")
    pre = value.get("prepackaging_closure")
    if not isinstance(pre, dict):
        raise QualificationError("P3.16 final prepackaging closure is absent")
    validate_prepackaging_artifact(pre, root=root, intent_path=intent_path)
    return {"schema": FINAL_SCHEMA, "verified": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepackaging", "final"), required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[5])
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--prepackaging", type=Path, default=DEFAULT_PREPACKAGING)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--candidate-a", type=Path, default=DEFAULT_CANDIDATE_A)
    parser.add_argument("--candidate-b", type=Path, default=DEFAULT_CANDIDATE_B)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    resolve = lambda value: value if value.is_absolute() else root / value  # noqa: E731
    try:
        if args.phase == "prepackaging":
            value = create_prepackaging_value(root, resolve(args.intent))
            output = resolve(args.out or args.prepackaging)
        else:
            value = create_final_value(
                root,
                resolve(args.intent),
                resolve(args.prepackaging),
                resolve(args.userspace),
                resolve(args.candidate_a),
                resolve(args.candidate_b),
            )
            output = resolve(args.out or DEFAULT_OUT)
        _write_new(output, value)
    except (QualificationError, overlay.OverlayContractError, OSError, ValueError) as exc:
        print(json.dumps({"schema": "p316-qualification", "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": value["schema"], "verdict": value["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
