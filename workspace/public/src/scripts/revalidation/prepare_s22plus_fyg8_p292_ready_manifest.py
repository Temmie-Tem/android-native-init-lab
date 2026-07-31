#!/usr/bin/env python3
"""Create one verified Process-v2 ready manifest for P2.92."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

import device_action_f1_evidence_v2 as evidence
import device_action_f1_v2 as core
from s22plus_boot_only_f1_transport import (
    BOOT_MEMBER,
    pin_boot_only_ap,
    read_boot_only_member,
)


SCHEMA = "s22plus_fyg8_p292_ready_manifest_builder_v1"
VERDICT = "PASS_P292_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P292_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
SOURCE_CONTRACT_ID = evidence.P292_SOURCE_CONTRACT_ID
DEFAULT_CANDIDATE_STATIC = Path(
    "workspace/private/device-action/s22plus_fyg8_p292_ready_1/"
    "evidence/candidate-static.json"
)
DEFAULT_RUN_MANIFEST = Path(
    "workspace/private/device-action/s22plus_fyg8_p292_ready_1/"
    "evidence/run-manifest.json"
)
DEFAULT_STATIC_CHECK = Path(
    "workspace/private/device-action/s22plus_fyg8_p292_ready_1/"
    "evidence/static-check-result.json"
)
DEFAULT_CANDIDATE_AP = Path(
    "workspace/private/device-action/s22plus_fyg8_p292_ready_1/"
    "candidate/AP.tar.md5"
)
DEFAULT_ROLLBACK_AP = Path(
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
DEFAULT_OUT = Path(
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p292_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = Path(
    "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p292-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p292-live-1"
DEFAULT_TIMEOUT_SEC = 300
MAX_EVIDENCE = 16 * 1024 * 1024


class ManifestError(ValueError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def resolve(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def stable_read(path: Path, label: str, maximum: int) -> bytes:
    before = path.stat()
    if path.is_symlink() or not path.is_file():
        raise ManifestError(f"{label} is not an exact regular file")
    if before.st_size <= 0 or before.st_size > maximum:
        raise ManifestError(f"{label} size is invalid")
    payload = path.read_bytes()
    after = path.stat()
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ) or len(payload) != before.st_size:
        raise ManifestError(f"{label} changed while reading")
    return payload


def receipt(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def repo_relative(root: Path, path: Path, label: str) -> str:
    absolute = path.absolute()
    try:
        return absolute.relative_to(root).as_posix()
    except ValueError as exc:
        raise ManifestError(f"{label} must stay below the repository") from exc


def parse_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"{label} is not an object")
    return value


def derive_manifest(
    *,
    root: Path,
    run_manifest: dict[str, Any],
    evidence_paths: dict[str, Path],
    evidence_receipts: dict[str, dict[str, Any]],
    candidate_ap: dict[str, Any],
    rollback_ap: dict[str, Any],
    target_profile: Path,
    manifest_id: str,
    live_run_id: str,
    timeout_sec: int,
) -> dict[str, Any]:
    source_contract_id = run_manifest.get("source_contract_id")
    run_id = run_manifest.get("run_id")
    if (
        source_contract_id != SOURCE_CONTRACT_ID
        or run_manifest.get("profile") != "E2"
        or not isinstance(run_id, str)
        or len(run_id) != 32
    ):
        raise ManifestError("P2.92 run-manifest identity mismatch")
    records = run_manifest.get("records")
    observation = run_manifest.get("observation_contract")
    if not isinstance(records, dict) or not isinstance(observation, dict):
        raise ManifestError("P2.92 observation contract is missing")
    contract = {
        name: {
            "path": repo_relative(root, evidence_paths[name], name),
            **evidence_receipts[name],
        }
        for name in ("candidate_static", "run_manifest", "static_check")
    }
    acceptance = {
        "kind": evidence.E1_LATEST_STAGE_KIND,
        "source": evidence.CHECKPOINT_SOURCE,
        "decoder": run_manifest.get("decoder"),
        "policy_id": run_manifest.get("policy_id"),
        "profile": "E2",
        "run_id": run_id,
        "source_contract_id": source_contract_id,
        "long_family_hex": records.get("long_family_hex"),
        "unsat_family_hex": records.get("unsat_family_hex"),
        "terminal_stage": records.get("terminal_stage"),
        "minimum_success_count": observation.get("minimum_success_count"),
        "clean_baseline_required": observation.get("clean_baseline_required"),
        "contract": contract,
    }
    try:
        evidence.validate_acceptance(acceptance)
        selected = core.candidate_intent.selected_source_contract(
            source_contract_id, "E2"
        )
        observer = selected.module.candidate_observer(bytes.fromhex(run_id))
        core.verify_candidate_observer_binding(acceptance, observer)
    except (ValueError, evidence.EvidenceError, core.F1V2Error) as exc:
        raise ManifestError(str(exc)) from exc
    return {
        "schema": core.MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "run_id": live_run_id,
        "status": "ready-for-f1-approval",
        "target_profile": repo_relative(root, target_profile, "target profile"),
        "candidate_ap": candidate_ap,
        "rollback_ap": rollback_ap,
        "allowed_member": BOOT_MEMBER,
        "observation": {
            "timeout_sec": timeout_sec,
            "acceptance": acceptance,
            "candidate_observer": observer,
        },
        "final_health_profile": "s22plus-fyg8-magisk",
        "runner_version": core.RUNNER_VERSION,
    }


def durable_create(path: Path, payload: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ManifestError("short manifest write")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def verify_and_finalize(
    *,
    root: Path,
    output: Path,
    canonical_directory: Path,
    payload: bytes,
    verify_only: bool,
) -> bool:
    if output.parent.absolute() != canonical_directory.absolute():
        raise ManifestError("manifest output directory is not canonical")
    if output.exists():
        raise ManifestError("manifest output already exists")
    with tempfile.TemporaryDirectory(prefix="p292-ready-manifest-") as temporary:
        proposal = Path(temporary) / "manifest.json"
        proposal.write_bytes(payload)
        core.verify_bundle(root, proposal)
    if verify_only:
        return False
    durable_create(output, payload)
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-static", type=Path, default=DEFAULT_CANDIDATE_STATIC)
    parser.add_argument("--run-manifest", type=Path, default=DEFAULT_RUN_MANIFEST)
    parser.add_argument("--static-check", type=Path, default=DEFAULT_STATIC_CHECK)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--rollback-ap", type=Path, default=DEFAULT_ROLLBACK_AP)
    parser.add_argument("--target-profile", type=Path, default=DEFAULT_TARGET_PROFILE)
    parser.add_argument("--manifest-id", default=DEFAULT_MANIFEST_ID)
    parser.add_argument("--live-run-id", default=DEFAULT_LIVE_RUN_ID)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    try:
        paths = {
            "candidate_static": resolve(root, args.candidate_static),
            "run_manifest": resolve(root, args.run_manifest),
            "static_check": resolve(root, args.static_check),
        }
        payloads = {
            name: stable_read(path, name, MAX_EVIDENCE)
            for name, path in paths.items()
        }
        receipts = {name: receipt(payload) for name, payload in payloads.items()}
        run_manifest = parse_json(payloads["run_manifest"], "run manifest")
        candidate_path = resolve(root, args.candidate_ap)
        rollback_path = resolve(root, args.rollback_ap)
        expected_candidate = run_manifest.get("candidate_ap")
        if (
            not isinstance(expected_candidate, dict)
            or set(expected_candidate) != {"size", "sha256"}
        ):
            raise ManifestError("run manifest candidate AP identity is missing")
        with pin_boot_only_ap(
            candidate_path,
            label="candidate AP",
            expected_size=expected_candidate["size"],
            expected_sha256=expected_candidate["sha256"],
            require_deterministic_metadata=True,
        ) as candidate:
            candidate_frame = read_boot_only_member(candidate, label="candidate AP")
            candidate_receipt = {
                "path": repo_relative(root, candidate.path, "candidate AP"),
                "size": candidate.size,
                "sha256": candidate.sha256,
            }
            candidate_for_evidence = {
                **candidate.receipt(),
                "member": {
                    "name": BOOT_MEMBER,
                    "size": len(candidate_frame),
                    "sha256": hashlib.sha256(candidate_frame).hexdigest(),
                },
            }
        with pin_boot_only_ap(
            rollback_path,
            label="rollback AP",
            expected_size=rollback_path.stat().st_size,
            expected_sha256=hashlib.sha256(rollback_path.read_bytes()).hexdigest(),
            require_deterministic_metadata=False,
        ) as rollback:
            rollback_receipt = {
                "path": repo_relative(root, rollback.path, "rollback AP"),
                "size": rollback.size,
                "sha256": rollback.sha256,
            }
        manifest = derive_manifest(
            root=root,
            run_manifest=run_manifest,
            evidence_paths=paths,
            evidence_receipts=receipts,
            candidate_ap=candidate_receipt,
            rollback_ap=rollback_receipt,
            target_profile=resolve(root, args.target_profile),
            manifest_id=args.manifest_id,
            live_run_id=args.live_run_id,
            timeout_sec=args.timeout_sec,
        )
        acceptance = manifest["observation"]["acceptance"]
        try:
            verification = evidence.verify_offline_contract(
                acceptance,
                payloads=payloads,
                receipts=receipts,
                candidate_ap=candidate_for_evidence,
            )
        except evidence.EvidenceError as exc:
            raise ManifestError(str(exc)) from exc
        payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        output = resolve(root, args.out)
        manifest_directory = resolve(root, DEFAULT_OUT).parent
        created = verify_and_finalize(
            root=root,
            output=output,
            canonical_directory=manifest_directory,
            payload=payload,
            verify_only=args.verify_only,
        )
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": REHEARSAL_VERDICT if args.verify_only else VERDICT,
                    "manifest": {
                        "path": str(output),
                        **receipt(payload),
                        "created": created,
                    },
                    "offline_contract": verification,
                    "safety": {
                        "host_only": True,
                        "device_contact": False,
                        "device_write": False,
                        "d0_started": False,
                        "f1_authorized": False,
                        "manifest_created": created,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (
        ManifestError,
        core.F1V2Error,
        core.F1TransportError,
        OSError,
    ) as exc:
        print(f"P2.92 ready-manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
