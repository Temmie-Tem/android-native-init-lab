#!/usr/bin/env python3
"""Build or rehearse the P3.20 ready-manifest candidate, H0 only.

The script binds the private P320 promotion artifacts, exact boot-only AP and
rollback identities, and the existing S22+ profile.  It never approves or
executes F1; publishing the tracked manifest remains an operator/reviewer
decision after the H0 closure is accepted.
"""

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
import prepare_s22plus_fyg8_p320_process_v2 as promotion  # noqa: E402
import s22plus_fyg8_p320_stock_candidate_build as candidate_build  # noqa: E402
from s22plus_boot_only_f1_transport import BOOT_MEMBER  # noqa: E402


SCHEMA = "s22plus_fyg8_p320_ready_manifest_builder_v1"
VERDICT = "PASS_P320_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P320_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_PROMOTION = promotion.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = promotion.DEFAULT_CANDIDATE_AP
DEFAULT_ROLLBACK_AP = candidate_build.P319_ROLLBACK_AP
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_OUTPUT = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p320_process_v2_ready_1.json"
)
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p320-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p320-live-1"
DEFAULT_TIMEOUT_SEC = 300
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


class ReadyManifestError(ValueError):
    pass


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ReadyManifestError("P3.20 ready path escaped the repository") from exc


def stable_bytes(
    path: Path,
    label: str,
    maximum: int,
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
        raise ReadyManifestError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before_id != (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
        or before_id != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(payload) != before.st_size
        or len(payload) > maximum
        or (mode is not None and stat.S_IMODE(before.st_mode) != mode)
        or (nlink is not None and before.st_nlink != nlink)
    ):
        raise ReadyManifestError(f"{label} identity differs")
    return payload


def decode(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadyManifestError(f"{label} is not JSON") from exc
    if not isinstance(value, dict):
        raise ReadyManifestError(f"{label} is not an object")
    return value


def _ap_receipt(path: Path) -> dict[str, Any]:
    payload = stable_bytes(path, "P3.20 candidate AP", 64 * 1024 * 1024)
    try:
        info, frame = promotion.boot_verify.parse_ap_tar_md5(payload)
    except promotion.boot_verify.BootVerifyError as exc:
        raise ReadyManifestError("P3.20 candidate AP is invalid") from exc
    if info["member"]["name"] != BOOT_MEMBER:
        raise ReadyManifestError("P3.20 candidate AP is not boot-only")
    return {
        "path": relative(path),
        **identity(payload),
        "member": {"name": BOOT_MEMBER, **identity(frame)},
    }


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
    run_manifest = decode(payloads["run_manifest"], "P3.20 run manifest")
    expected = {
        "source_contract_id": evidence.p320_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": evidence.P320_STOCK_OVERLAY_CONTRACT_ID,
        "profile": evidence.p320_stock_adapter.PROFILE,
        "run_id": evidence.P320_RUN_ID,
        "candidate_ap": {name: candidate_ap[name] for name in ("size", "sha256")},
        "candidate_static": identity(payloads["candidate_static"]),
    }
    if any(run_manifest.get(key) != value for key, value in expected.items()):
        raise ReadyManifestError("P3.20 promotion run manifest differs")
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
    acceptance = evidence.p320_stock_adapter.acceptance_fixture()
    acceptance["contract"] = contract
    try:
        evidence.validate_acceptance(acceptance)
        core.verify_candidate_observer_binding(acceptance, None)
    except (evidence.EvidenceError, core.F1V2Error) as exc:
        raise ReadyManifestError(str(exc)) from exc
    if type(timeout_sec) is not int or not 1 <= timeout_sec <= 600:
        raise ReadyManifestError("P3.20 observation timeout is invalid")
    return {
        "schema": core.MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "run_id": live_run_id,
        "status": "ready-for-f1-approval",
        "target_profile": relative(target_profile),
        "candidate_ap": {
            name: candidate_ap[name] for name in ("path", "size", "sha256")
        },
        "rollback_ap": rollback_ap,
        "allowed_member": BOOT_MEMBER,
        "observation": {"timeout_sec": timeout_sec, "acceptance": acceptance},
        "final_health_profile": "s22plus-fyg8-magisk",
        "runner_version": core.RUNNER_VERSION,
    }


def _manifest_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")


def verify_bundle(manifest: dict[str, Any]) -> bytes:
    payload = _manifest_bytes(manifest)
    with tempfile.TemporaryDirectory(prefix="p320-ready-manifest-") as name:
        proposal = Path(name) / "manifest.json"
        proposal.write_bytes(payload)
        try:
            core.verify_bundle(ROOT, proposal)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise ReadyManifestError(str(exc)) from exc
    return payload


def publish(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ReadyManifestError("P3.20 ready manifest already exists")
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o644,
    )
    try:
        os.fchmod(descriptor, 0o644)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise ReadyManifestError("P3.20 ready manifest write was short")
            offset += written
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
        name: stable_bytes(
            promotion_root / filename,
            f"P3.20 promotion {name}",
            2 * 1024 * 1024,
            mode=0o400,
            nlink=1,
        )
        for name, filename in filenames.items()
    }
    candidate_ap = _ap_receipt(candidate_path)
    rollback_payload = stable_bytes(
        rollback_path, "P3.20 exact rollback AP", 64 * 1024 * 1024
    )
    rollback_ap = {"path": relative(rollback_path), **identity(rollback_payload)}
    if rollback_ap != {"path": relative(rollback_path), **ROLLBACK_IDENTITY}:
        raise ReadyManifestError("P3.20 rollback identity differs")
    profile_payload = stable_bytes(target_profile, "S22+ target profile", 2 * 1024 * 1024)
    profile = decode(profile_payload, "S22+ target profile")
    try:
        core.validate_profile(profile)
    except core.F1V2Error as exc:
        raise ReadyManifestError(str(exc)) from exc
    manifest = derive_manifest(
        promotion_root=promotion_root,
        payloads=payloads,
        candidate_ap=candidate_ap,
        rollback_ap=rollback_ap,
        target_profile=target_profile,
        manifest_id=manifest_id,
        live_run_id=live_run_id,
        timeout_sec=timeout_sec,
    )
    payload = verify_bundle(manifest)
    return manifest, payload


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
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    paths = {
        name: path if path.is_absolute() else ROOT / path
        for name, path in {
            "promotion": args.promotion,
            "candidate": args.candidate_ap,
            "rollback": args.rollback_ap,
            "profile": args.target_profile,
            "output": args.out,
        }.items()
    }
    try:
        manifest, payload = build(
            paths["promotion"],
            paths["candidate"],
            paths["rollback"],
            paths["profile"],
            manifest_id=args.manifest_id,
            live_run_id=args.live_run_id,
            timeout_sec=args.timeout_sec,
        )
        if not args.audit_only:
            publish(paths["output"], payload)
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "verdict": VERDICT if not args.audit_only else REHEARSAL_VERDICT,
                    "manifest": manifest,
                    "manifest_sha256": hashlib.sha256(payload).hexdigest(),
                    "created": not args.audit_only,
                    "device_contact": False,
                    "live_authorized": False,
                },
                sort_keys=True,
            )
        )
        return 0
    except (OSError, ReadyManifestError, RuntimeError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
