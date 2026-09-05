#!/usr/bin/env python3
"""Compact P345 H0 promotion; fixed five-session qualification, no lease.

Default is non-publishing rehearsal. This prepares no connected run or F1
approval; publication still requires the root's independent review decision.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT / "workspace/public/src/scripts/revalidation"), str(Path(__file__).parent)]
import device_action_f1_evidence_v2 as evidence
import device_action_f1_v2 as core
import s22plus_fyg8_p345_process_v2_candidate_static as candidate_static
import s22plus_fyg8_p345_stock_candidate_build as candidate_build
import s22plus_fyg8_p345_stock_process_v2_adapter as adapter

DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_PROMOTION = ROOT / "workspace/private/outputs/s22plus_fyg8_p345/process-v2-promotion-20260906-01"
DEFAULT_MANIFEST = ROOT / "workspace/public/src/device-action/manifests/s22plus_fyg8_p345_process_v2_ready_1.json"
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_CANDIDATE_AP = candidate_build.DEFAULT_OUTPUT_ROOT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p345-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p345-live-1"
VERDICT = "PASS_P345_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P345_PROCESS_V2_PROMOTION_REHEARSAL_HOST_ONLY"
canonical = candidate_static.canonical
identity = candidate_static.identity

class PromotionError(ValueError):
    pass

def _receipt(path: Path, payload: bytes) -> dict[str, Any]:
    return {"path": str(path.relative_to(ROOT)), **identity(payload)}

def _payloads(static: dict[str, Any], *, static_path: Path, promotion: Path):
    raw = canonical(static)
    static_pin = _receipt(static_path, raw)
    promotion_id = hashlib.sha256(raw).hexdigest()[:32]
    run, check = candidate_static.promotion_payloads(static, static_pin, run_id=promotion_id)
    payloads = {"candidate_static": raw, "run_manifest": canonical(run), "static_check": canonical(check)}
    paths = {"candidate_static": static_path, "run_manifest": promotion / "run-manifest.json",
             "static_check": promotion / "static-check.json"}
    pins = {name: _receipt(paths[name], value) for name, value in payloads.items()}
    return payloads, paths, pins

def _manifest(static: dict[str, Any], pins: dict[str, Any]) -> dict[str, Any]:
    acceptance = adapter.acceptance_fixture()
    acceptance["contract"] = copy.deepcopy(pins)
    return {"schema": core.MANIFEST_SCHEMA, "manifest_id": DEFAULT_MANIFEST_ID,
        "run_id": DEFAULT_LIVE_RUN_ID, "status": "ready-for-f1-approval",
        "target_profile": str(DEFAULT_TARGET_PROFILE.relative_to(ROOT)),
        "candidate_ap": {"path": str(DEFAULT_CANDIDATE_AP.relative_to(ROOT)),
                         **static["candidate"]["a"]["ap_tar_md5"]},
        "rollback_ap": static["rollback_ap"], "allowed_member": "boot.img.lz4",
        "observation": {"timeout_sec": 300, "acceptance": acceptance,
            "candidate_observer": evidence.p345_research_shell_observer_spec(),
            evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE},
        "final_health_profile": "s22plus-fyg8-magisk", "runner_version": core.RUNNER_VERSION}

def _write(path: Path, payload: bytes, mode: int) -> bool:
    if path.exists() or path.is_symlink():
        existing = candidate_static.artifact.stable_bytes(path, str(path), maximum=2 << 20, nlink=1)
        if existing != payload or path.stat().st_mode & 0o777 != mode:
            raise PromotionError("existing P345 publication differs: " + str(path))
        return False
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)
    return True

def verify_manifest(static: dict[str, Any]) -> dict[str, Any]:
    """Rehearse the real bundle verifier in P345-only temporary storage."""
    private = DEFAULT_PROMOTION.parent
    if not private.is_dir() or private.is_symlink() or private.resolve() != private.absolute():
        raise PromotionError("P345 private output namespace is absent or indirect")
    with tempfile.TemporaryDirectory(prefix="p345-ready-audit-", dir=private) as temporary:
        root = Path(temporary)
        payloads, paths, pins = _payloads(static, static_path=root / "candidate-static.json", promotion=root)
        for name, payload in payloads.items():
            _write(paths[name], payload, 0o400)
        manifest = _manifest(static, pins)
        manifest_path = root / "manifest.json"
        _write(manifest_path, canonical(manifest), 0o600)
        bundle = core.verify_bundle(ROOT, manifest_path)
        verification = bundle.receipt["observation_contract"]["verification"]
        if verification.get("verified") is not True or verification.get("run_id") != adapter.P345_RUN_ID_HEX:
            raise PromotionError("P345 real bundle rehearsal failed")
        return {"common_offline_verified": True, "bundle_sha256": bundle.sha256,
                "candidate_ap": bundle.receipt["candidate_ap"]}

def build(*, publish: bool = False) -> dict[str, Any]:
    if type(publish) is not bool:
        raise PromotionError("publish flag differs")
    static = candidate_static.build_result()
    payloads, paths, pins = _payloads(static, static_path=DEFAULT_STATIC_OUTPUT, promotion=DEFAULT_PROMOTION)
    manifest = _manifest(static, pins)
    profile, _ = core.load_json(DEFAULT_TARGET_PROFILE, "P345 target profile")
    core.validate_manifest(manifest, core.validate_profile(profile))
    checked = verify_manifest(static)
    created = False
    if publish:
        DEFAULT_PROMOTION.mkdir(mode=0o700, exist_ok=True)
        if DEFAULT_PROMOTION.resolve() != DEFAULT_PROMOTION.absolute() or DEFAULT_PROMOTION.stat().st_mode & 0o777 != 0o700:
            raise PromotionError("P345 promotion directory differs")
        for name, payload in payloads.items():
            created = _write(paths[name], payload, 0o400) or created
        created = _write(DEFAULT_MANIFEST, canonical(manifest), 0o644) or created
        # Verify the actual final names, not just the intended temporary copy.
        checked["bundle_sha256"] = core.verify_bundle(ROOT, DEFAULT_MANIFEST).sha256
    return {"verdict": VERDICT if publish else REHEARSAL_VERDICT,
        "manifest": _receipt(DEFAULT_MANIFEST, canonical(manifest)),
        "artifacts": pins, **checked, "created": created, "published": publish,
        "run_directory_created": False, "device_contact": False,
        "odin_invoked": False, "live_authorized": False, "later_action_lease_active": False}

def main(argv=None):
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--publish", action="store_true")
    group.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    print(canonical(build(publish=args.publish)).decode())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
