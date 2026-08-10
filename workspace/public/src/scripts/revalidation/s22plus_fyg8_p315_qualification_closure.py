#!/usr/bin/env python3
"""Create P3.15 prepackaging and final reproducibility closures."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import build_s22plus_fyg8_p315_candidate as builder
import device_action_f1_evidence_v2 as evidence
import prepare_s22plus_fyg8_p315_ready_manifest as ready_manifest
import s22plus_fyg8_p315_carrier_model as carrier
import s22plus_fyg8_p315_design_contract as design
import s22plus_fyg8_p315_overlay_contract as overlay
import s22plus_fyg8_p315_telemetry_decoder as decoder


SCHEMA = design.QUALIFICATION_SCHEMA
PREPACKAGING_SCHEMA = design.ARTIFACT_SCHEMA
PREPACKAGING_VERDICT = design.VERDICT
VERDICT = design.QUALIFICATION_VERDICT
DEFAULT_INTENT = overlay.DEFAULT_INTENT
DEFAULT_PREPACKAGING = builder.DEFAULT_PREPACKAGING
DEFAULT_USERSPACE = Path("workspace/private/outputs/s22plus_fyg8_p315/userspace")
DEFAULT_CANDIDATE_A = builder.DEFAULT_OUT
DEFAULT_CANDIDATE_B = Path("workspace/private/outputs/s22plus_fyg8_p315/candidate-b")
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_p315/qualification/"
    "qualification-closure.json"
)


class QualificationError(ValueError):
    pass


def _receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _read_json(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        before = path.stat(follow_symlinks=False)
        if path.is_symlink() or not path.is_file() or before.st_size > 64 * 1024 * 1024:
            raise QualificationError(f"{label} is not a bounded regular file")
        payload = path.read_bytes()
        after = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise QualificationError(f"{label} is unavailable") from exc
    if (
        len(payload) != before.st_size
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        raise QualificationError(f"{label} changed while reading")
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
    if path.exists() or path.is_symlink():
        raise QualificationError(f"qualification output exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
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
        raise QualificationError(f"candidate tree is unavailable: {directory}")
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise QualificationError("candidate tree contains a symlink")
        if path.is_file():
            rows[path.relative_to(directory).as_posix()] = _receipt(path.read_bytes())
    return rows


def _ready_rehearsal(
    root: Path,
    exact: dict[str, Any],
    candidate_a: Path,
    candidate_tree: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ap_relative = "odin4/AP.tar.md5"
    ap = candidate_tree.get(ap_relative)
    if not isinstance(ap, dict):
        raise QualificationError("P3.15 candidate AP receipt missing")
    rollback_path = root / ready_manifest.DEFAULT_ROLLBACK_AP
    rollback_payload = rollback_path.read_bytes()
    placeholder = root / "workspace/private/outputs/s22plus_fyg8_p315/qualification"
    paths = {
        "candidate_static": candidate_a / "artifact-result.json",
        "run_manifest": placeholder / "rehearsal-run-manifest.json",
        "static_check": placeholder / "rehearsal-static-check.json",
    }
    receipts = {
        "candidate_static": candidate_tree["artifact-result.json"],
        "run_manifest": {"size": 1, "sha256": "1" * 64},
        "static_check": {"size": 1, "sha256": "2" * 64},
    }
    run_manifest = {
        "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "profile": overlay.PROFILE,
        "run_id": exact["run_id"],
        "decoder": decoder.DECODER_ID,
        "policy_id": decoder.POLICY_ID,
        "records": {
            "long_family_hex": carrier.LONG_FAMILY.hex(),
            "unsat_family_hex": carrier.UNSAT_FAMILY.hex(),
            "terminal_stage": evidence._latest_stage_terminal(  # noqa: SLF001
                decoder, overlay.PROFILE
            ),
        },
        "observation_contract": {
            "accepted_identity": evidence._latest_stage_accepted_identity(  # noqa: SLF001
                overlay.PROFILE,
                overlay.PARENT_SOURCE_CONTRACT_ID,
                overlay.CONTRACT_ID,
            ),
            "minimum_success_count": 1,
            "clean_baseline_required": True,
        },
    }
    manifest = ready_manifest.derive_manifest(
        root=root,
        run_manifest=run_manifest,
        evidence_paths=paths,
        evidence_receipts=receipts,
        candidate_ap={
            "path": (candidate_a / ap_relative).relative_to(root).as_posix(),
            **ap,
        },
        rollback_ap={
            "path": rollback_path.relative_to(root).as_posix(),
            **_receipt(rollback_payload),
        },
        target_profile=root / ready_manifest.DEFAULT_TARGET_PROFILE,
        manifest_id="s22plus-fyg8-p315-qualification-rehearsal",
        live_run_id="s22plus-fyg8-p315-qualification-rehearsal-live",
        timeout_sec=300,
    )
    acceptance = manifest.get("observation", {}).get("acceptance", {})
    if (
        manifest.get("status") != "ready-for-f1-approval"
        or acceptance.get("userspace_overlay_contract_id") != overlay.CONTRACT_ID
        or acceptance.get("decoder") != decoder.DECODER_ID
    ):
        raise QualificationError("P3.15 ready-manifest rehearsal differs")
    return {
        "builder": "prepare_s22plus_fyg8_p315_ready_manifest.derive_manifest",
        "status": manifest["status"],
        "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        "decoder": decoder.DECODER_ID,
        "verified": True,
    }


def create_prepackaging_value(root: Path, intent_path: Path) -> dict[str, Any]:
    exact = overlay.verify_intent(root, intent_path)
    value = exact.get("prepackaging_closure")
    if not isinstance(value, dict):
        raise QualificationError("P3.15 intent omitted prepackaging closure")
    design.validate_successor_artifact(value, root=root)
    return value


def create_final_value(
    root: Path,
    intent_path: Path,
    prepackaging_path: Path,
    userspace_path: Path,
    candidate_a: Path,
    candidate_b: Path,
) -> dict[str, Any]:
    exact = overlay.verify_intent(root, intent_path)
    prepack_payload, prepack = _read_json(
        prepackaging_path, "P3.15 prepackaging closure"
    )
    prepack_validation = design.validate_successor_artifact(prepack, root=root)
    _, userspace = _read_json(
        userspace_path / "userspace-result.json", "P3.15 userspace result"
    )
    if userspace.get("two_build_byte_identical") is not True:
        raise QualificationError("P3.15 userspace reproducibility differs")
    trees = (_tree_receipts(candidate_a), _tree_receipts(candidate_b))
    if trees[0] != trees[1]:
        raise QualificationError("P3.15 candidate trees are not byte-identical")
    for directory in (candidate_a, candidate_b):
        _, result = _read_json(
            directory / "artifact-result.json", "P3.15 artifact result"
        )
        safety = result.get("safety", {})
        if (
            safety.get("p315_prepackaging_closure") != _receipt(prepack_payload)
            or safety.get("p315_prepackaging_validation") != prepack_validation
        ):
            raise QualificationError("P3.15 package omitted validated closure")
    rehearsal = _ready_rehearsal(root, exact, candidate_a, trees[0])
    value = {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "requirements_sha256": design.requirements_sha256(),
        "prepackaging_closure": prepack,
        "prepackaging_receipt": design.artifact_receipt(prepack),
        "packaging_wiring": {
            "validated_artifact_receipted_by_qualification": True,
            "receipt_binds_requirements_and_artifact_sha256": True,
            "ready_manifest_rehearsal_after_reproducible_packaging": True,
            "ready_manifest_rehearsal": rehearsal,
            "verified": True,
        },
        "artifacts": {
            "fixed_image_unchanged": True,
            "kernel_hooks_unchanged": True,
            "trace_descriptor_unchanged": True,
            "module_plan_unchanged": True,
            "carrier_layout_unchanged": True,
            "rollback_unchanged": True,
            "full_lto_performed": False,
            "userspace_builds_reproducible": True,
            "packages_reproducible": True,
            "candidate_tree": trees[0],
            "verified": True,
        },
        "verified": True,
    }
    design.validate_qualification_artifact(
        value, root=root, candidate_tree=trees[0]
    )
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("prepackaging", "final"), required=True)
    parser.add_argument("--intent", type=Path, default=DEFAULT_INTENT)
    parser.add_argument("--prepackaging", type=Path, default=DEFAULT_PREPACKAGING)
    parser.add_argument("--userspace", type=Path, default=DEFAULT_USERSPACE)
    parser.add_argument("--candidate-a", type=Path, default=DEFAULT_CANDIDATE_A)
    parser.add_argument("--candidate-b", type=Path, default=DEFAULT_CANDIDATE_B)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parents[5]
    try:
        if args.phase == "prepackaging":
            output = args.out or DEFAULT_PREPACKAGING
            value = create_prepackaging_value(root, root / args.intent)
        else:
            output = args.out or DEFAULT_OUT
            value = create_final_value(
                root,
                root / args.intent,
                root / args.prepackaging,
                root / args.userspace,
                root / args.candidate_a,
                root / args.candidate_b,
            )
        _write_new(root / output, value)
    except (
        QualificationError,
        design.P315DesignError,
        overlay.OverlayContractError,
        OSError,
        RuntimeError,
        ValueError,
    ) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    print(json.dumps({"schema": value["schema"], "verdict": value["verdict"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
