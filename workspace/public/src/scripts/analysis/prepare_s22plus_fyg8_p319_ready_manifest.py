#!/usr/bin/env python3
"""Create or rehearse the exact P3.19 Process-v2 ready manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p319_process_v2 as promotion  # noqa: E402
from s22plus_boot_only_f1_transport import (  # noqa: E402
    BOOT_MEMBER,
    pin_boot_only_ap,
    read_boot_only_member,
)


SCHEMA = "s22plus_fyg8_p319_ready_manifest_builder_v1"
VERDICT = "PASS_P319_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P319_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_PROMOTION = promotion.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = promotion.DEFAULT_CANDIDATE_AP
DEFAULT_ROLLBACK_AP = ROOT / (
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}
DEFAULT_TARGET_PROFILE = ROOT / (
    "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)
DEFAULT_OUTPUT = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p319_process_v2_ready_1.json"
)
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p319-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p319-live-1"
DEFAULT_TIMEOUT_SEC = 300


class ReadyManifestError(ValueError):
    pass


def identity(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ReadyManifestError("P3.19 ready path is outside the repository") from exc


def stable_bytes(path: Path, label: str, maximum: int) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise ReadyManifestError(f"{label} is not a direct regular file")
        if stat.S_IMODE(before.st_mode) != 0o400 or before.st_nlink != 1:
            raise ReadyManifestError(f"{label} metadata differs")
        with path.open("rb") as stream:
            data = stream.read(maximum + 1)
            inside = os.fstat(stream.fileno())
        after = path.lstat()
    except OSError as exc:
        raise ReadyManifestError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if (
        before_id
        != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or before_id
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(data) != before.st_size
        or len(data) > maximum
    ):
        raise ReadyManifestError(f"{label} changed while reading")
    return data


def decode(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadyManifestError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise ReadyManifestError(f"{label} is not an object")
    return value


def derive_manifest(
    *,
    promotion_root: Path,
    payloads: dict[str, bytes],
    candidate_ap: dict[str, Any],
    rollback_ap: dict[str, Any],
    target_profile: Path,
    manifest_id: str,
    live_run_id: str,
    timeout_sec: int,
) -> dict[str, Any]:
    run_manifest = decode(payloads["run_manifest"], "P3.19 run manifest")
    contract = {
        name: {
            "path": relative(promotion_root / filename),
            **identity(payloads[name]),
        }
        for name, filename in {
            "candidate_static": "candidate-static.json",
            "run_manifest": "run-manifest.json",
            "static_check": "static-check-result.json",
        }.items()
    }
    acceptance = evidence.p319_stock_adapter.acceptance_fixture()
    acceptance["contract"] = contract
    if (
        run_manifest.get("source_contract_id")
        != evidence.p319_stock_adapter.PARENT_SOURCE_CONTRACT_ID
        or run_manifest.get("userspace_overlay_contract_id")
        != evidence.P319_STOCK_OVERLAY_CONTRACT_ID
        or run_manifest.get("profile") != evidence.p319_stock_adapter.PROFILE
        or run_manifest.get("run_id") != evidence.P319_RUN_ID
        or run_manifest.get("candidate_ap")
        != {name: candidate_ap[name] for name in ("size", "sha256")}
        or run_manifest.get("candidate_static")
        != identity(payloads["candidate_static"])
    ):
        raise ReadyManifestError("P3.19 promotion run manifest differs")
    try:
        evidence.validate_acceptance(acceptance)
        core.verify_candidate_observer_binding(acceptance, None)
    except (evidence.EvidenceError, core.F1V2Error) as exc:
        raise ReadyManifestError(str(exc)) from exc
    return {
        "schema": core.MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "run_id": live_run_id,
        "status": "ready-for-f1-approval",
        "target_profile": relative(target_profile),
        "candidate_ap": candidate_ap,
        "rollback_ap": rollback_ap,
        "allowed_member": BOOT_MEMBER,
        "observation": {
            "timeout_sec": timeout_sec,
            "acceptance": acceptance,
        },
        "final_health_profile": "s22plus-fyg8-magisk",
        "runner_version": core.RUNNER_VERSION,
    }


def verify_bundle(manifest: dict[str, Any]) -> bytes:
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("ascii")
    with tempfile.TemporaryDirectory(prefix="p319-ready-manifest-") as name:
        proposal = Path(name) / "manifest.json"
        proposal.write_bytes(payload)
        try:
            core.verify_bundle(ROOT, proposal)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise ReadyManifestError(str(exc)) from exc
    return payload


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ReadyManifestError("P3.19 ready manifest already exists")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400
    )
    try:
        os.fchmod(descriptor, 0o400)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ReadyManifestError("P3.19 ready manifest write was short")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def build(
    promotion_root: Path = DEFAULT_PROMOTION,
    candidate_path: Path = DEFAULT_CANDIDATE_AP,
    rollback_path: Path = DEFAULT_ROLLBACK_AP,
    target_profile: Path = DEFAULT_TARGET_PROFILE,
    *,
    manifest_id: str = DEFAULT_MANIFEST_ID,
    live_run_id: str = DEFAULT_LIVE_RUN_ID,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> tuple[dict[str, Any], bytes]:
    filenames = {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }
    payloads = {
        name: stable_bytes(promotion_root / filename, name, 2 * 1024 * 1024)
        for name, filename in filenames.items()
    }
    run_manifest = decode(payloads["run_manifest"], "P3.19 run manifest")
    expected_candidate = run_manifest.get("candidate_ap")
    if not isinstance(expected_candidate, dict):
        raise ReadyManifestError("P3.19 candidate AP identity is absent")
    try:
        with pin_boot_only_ap(
            candidate_path,
            label="P3.19 candidate AP",
            expected_size=expected_candidate["size"],
            expected_sha256=expected_candidate["sha256"],
            require_deterministic_metadata=True,
        ) as candidate:
            frame = read_boot_only_member(candidate, label="P3.19 candidate AP")
            candidate_receipt = {
                "path": relative(candidate.path),
                "size": candidate.size,
                "sha256": candidate.sha256,
            }
            candidate_for_evidence = {
                **candidate.receipt(),
                "member": {"name": BOOT_MEMBER, **identity(frame)},
            }
        with pin_boot_only_ap(
            rollback_path,
            label="P3.19 rollback AP",
            expected_size=ROLLBACK_IDENTITY["size"],
            expected_sha256=ROLLBACK_IDENTITY["sha256"],
            require_deterministic_metadata=False,
        ) as rollback:
            rollback_receipt = {
                "path": relative(rollback.path),
                "size": rollback.size,
                "sha256": rollback.sha256,
            }
    except (core.F1TransportError, KeyError) as exc:
        raise ReadyManifestError(str(exc)) from exc
    manifest = derive_manifest(
        promotion_root=promotion_root,
        payloads=payloads,
        candidate_ap=candidate_receipt,
        rollback_ap=rollback_receipt,
        target_profile=target_profile,
        manifest_id=manifest_id,
        live_run_id=live_run_id,
        timeout_sec=timeout_sec,
    )
    try:
        verification = evidence.verify_offline_contract(
            manifest["observation"]["acceptance"],
            payloads=payloads,
            receipts={name: identity(data) for name, data in payloads.items()},
            candidate_ap=candidate_for_evidence,
        )
        evidence.validate_e2_ap_payload(frame, verification["ap_payload_closure"])
    except evidence.EvidenceError as exc:
        raise ReadyManifestError(str(exc)) from exc
    return manifest, verify_bundle(manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promotion", type=Path, default=DEFAULT_PROMOTION)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--rollback-ap", type=Path, default=DEFAULT_ROLLBACK_AP)
    parser.add_argument("--target-profile", type=Path, default=DEFAULT_TARGET_PROFILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest-id", default=DEFAULT_MANIFEST_ID)
    parser.add_argument("--live-run-id", default=DEFAULT_LIVE_RUN_ID)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        resolve = lambda value: value if value.is_absolute() else ROOT / value
        manifest, payload = build(
            resolve(args.promotion),
            resolve(args.candidate_ap),
            resolve(args.rollback_ap),
            resolve(args.target_profile),
            manifest_id=args.manifest_id,
            live_run_id=args.live_run_id,
            timeout_sec=args.timeout_sec,
        )
        output = resolve(args.out)
        if not args.verify_only:
            publish(output, payload)
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": REHEARSAL_VERDICT if args.verify_only else VERDICT,
                    "manifest": {"path": relative(output), **identity(payload)},
                    "created": not args.verify_only,
                    "status": manifest["status"],
                    "device_contact": False,
                    "f1_authorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (ReadyManifestError, OSError) as exc:
        print(f"P3.19 ready-manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
