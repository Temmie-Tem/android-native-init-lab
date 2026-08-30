#!/usr/bin/env python3
"""Promote the P3.21 artifact-joined candidate into a host-only F1 bundle.

The builder validates the already-published P3.21 static receipt and real
boot-only AP, then creates immutable private contract files and a data-only
ready manifest.  It never allocates a Process-v2 run directory, approves F1,
contacts a device, invokes Odin, or transfers an artifact.
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
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p321_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p321_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p321_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_boot_verify as boot_verify  # noqa: E402


SCHEMA = "s22plus_fyg8_p321_process_v2_promotion_v1"
VERDICT = "PASS_P321_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p321_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P321_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P321_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = candidate_build.P319_ROLLBACK_AP
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p321/"
    "process-v2-promotion-20260831-02"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p321_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p321-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p321-live-1"
DEFAULT_TIMEOUT_SEC = 300
ROLLBACK_IDENTITY = candidate_build.P319_ROLLBACK_IDENTITY
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


class PromotionError(ValueError):
    pass


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise PromotionError("P3.21 promotion value is not canonical JSON") from exc


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise PromotionError("P3.21 path escaped the repository") from exc


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
        raise PromotionError(f"{label} is unavailable") from exc
    before_id = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    inside_id = (inside.st_dev, inside.st_ino, inside.st_size, inside.st_mtime_ns)
    after_id = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
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
    ):
        raise PromotionError(f"{label} identity differs")
    return payload


def decode(payload: bytes, label: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in items:
            if key in value:
                raise PromotionError(f"{label} has a duplicate key")
            value[key] = item
        return value

    try:
        value = json.loads(payload.decode("ascii"), object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PromotionError(f"{label} is not strict JSON") from exc
    if not isinstance(value, dict):
        raise PromotionError(f"{label} is not an object")
    return value


def _candidate_inputs(
    static_path: Path,
    candidate_ap_path: Path,
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, dict[str, Any]]:
    static_payload = stable_bytes(
        static_path, "P3.21 candidate-static", 2 * 1024 * 1024, mode=0o400, nlink=1
    )
    static_value = decode(static_payload, "P3.21 candidate-static")
    try:
        candidate_static.validate_result(static_value)
    except Exception as exc:
        raise PromotionError("P3.21 candidate-static did not reopen") from exc
    builder_path = DEFAULT_BUILDER_OUTPUT / "result.json"
    builder_payload = stable_bytes(
        builder_path, "P3.21 builder result", 4 * 1024 * 1024, mode=0o400, nlink=1
    )
    builder_value = decode(builder_payload, "P3.21 builder result")
    try:
        audited = candidate_build.audit_existing(DEFAULT_BUILDER_OUTPUT)
    except Exception as exc:
        raise PromotionError("P3.21 builder result did not reopen") from exc
    if audited != builder_value:
        raise PromotionError("P3.21 builder result changed")
    ap_payload = stable_bytes(candidate_ap_path, "P3.21 candidate AP", 64 * 1024 * 1024)
    try:
        ap_info, frame = boot_verify.parse_ap_tar_md5(ap_payload)
    except boot_verify.BootVerifyError as exc:
        raise PromotionError("P3.21 candidate AP is invalid") from exc
    if ap_info["member"]["name"] != "boot.img.lz4":
        raise PromotionError("P3.21 candidate AP is not boot-only")
    ap_receipt = {
        **identity(ap_payload),
        "member": {"name": "boot.img.lz4", **identity(frame)},
    }
    candidate = static_value.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("a", {}).get("ap_tar_md5") != {
        key: ap_receipt[key] for key in ("size", "sha256")
    }:
        raise PromotionError("P3.21 candidate-static AP identity differs")
    return static_value, static_payload, builder_value, builder_payload, ap_receipt


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    candidate = static_value["candidate"]
    static_identity = identity(static_payload)
    records = {
        "long_family_hex": adapter.LONG_FAMILY.hex(),
        "unsat_family_hex": adapter.UNSAT_FAMILY.hex(),
        "terminal_stage": adapter.TERMINAL_STAGE,
    }
    observation = {
        "accepted_identity": "P321_STOCK_OBSERVER_V4_RETAINED",
        "minimum_success_count": 1,
        "clean_baseline_required": True,
        "runtime_values_preflighted": False,
        "complete_is_noncausal": True,
        "incomplete_result": "NO_PROOF_EXPERIMENT_PRECONDITION",
        "receipt_result": "NO_PROOF_OBSERVER",
    }
    run_manifest = {
        "schema": evidence.P321_RUN_MANIFEST_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "profile": adapter.PROFILE,
        "run_id": adapter.P321_RUN_ID_HEX,
        "decoder": adapter.DECODER_ID,
        "policy_id": adapter.POLICY_ID,
        "records": records,
        "observation_contract": observation,
        "candidate_ap": {key: ap_receipt[key] for key in ("size", "sha256")},
        "candidate_static": static_identity,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.P321_OVERLAY_CONTRACT_ID,
    }
    run_payload = canonical(run_manifest)
    static_result = {
        "schema": evidence.P321_STATIC_RESULT_SCHEMA,
        "target": evidence.PID1_USERSPACE_TARGET,
        "verdict": evidence.P321_STATIC_RESULT_VERDICT,
        "profile": adapter.PROFILE,
        "run_id": adapter.P321_RUN_ID_HEX,
        "decoder": adapter.DECODER_ID,
        "policy_id": adapter.POLICY_ID,
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.P321_OVERLAY_CONTRACT_ID,
        "run_binding": {
            "canonical_manifest_size": len(run_payload),
            "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
            "verified": True,
        },
        "candidate": {
            "artifacts": {
                "ap": {key: ap_receipt[key] for key in ("size", "sha256")},
                "candidate_static": static_identity,
                "boot_image": candidate["a"]["boot_img"],
                "boot_img_lz4": candidate["a"]["boot_img_lz4"],
                "image": candidate["image"],
                "init": candidate["init"],
                "child": candidate["child"],
                "latch": evidence.P319_EXACT_ARTIFACTS["latch"],
            },
            "boot_only_ap": True,
            "independent_static_contract": True,
            "complete_is_noncausal": True,
            "runtime_values_observed": False,
            "verified": True,
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "device_write": False,
            "odin_invoked": False,
            "odin_transfer": False,
            "flash": False,
            "partition_write": False,
            "live_authorized": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        },
    }
    return {
        "candidate_static": static_payload,
        "run_manifest": run_payload,
        "static_check": canonical(static_result),
    }


def _acceptance(output: Path, payloads: dict[str, bytes]) -> dict[str, Any]:
    names = {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }
    item = adapter.acceptance_fixture()
    item["contract"] = {
        name: {"path": relative(output / filename), **identity(payloads[name])}
        for name, filename in names.items()
    }
    try:
        evidence.validate_acceptance(item)
    except evidence.EvidenceError as exc:
        raise PromotionError(str(exc)) from exc
    return item


def _write_exclusive(path: Path, payload: bytes, mode: int) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        mode,
    )
    try:
        offset = 0
        while offset < len(payload):
            count = os.write(descriptor, payload[offset:])
            if count <= 0:
                raise PromotionError("P3.21 publication was short")
            offset += count
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_promotion(output: Path, payloads: dict[str, bytes]) -> None:
    if output.exists() or output.is_symlink():
        raise PromotionError("P3.21 promotion output already exists")
    output.mkdir(mode=0o700, parents=True)
    for name, filename in {
        "candidate_static": "candidate-static.json",
        "run_manifest": "run-manifest.json",
        "static_check": "static-check-result.json",
    }.items():
        _write_exclusive(output / filename, payloads[name], 0o400)
    descriptor = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


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
    run_manifest = decode(payloads["run_manifest"], "P3.21 run manifest")
    expected = {
        "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
        "userspace_overlay_contract_id": adapter.P321_OVERLAY_CONTRACT_ID,
        "profile": adapter.PROFILE,
        "run_id": adapter.P321_RUN_ID_HEX,
        "candidate_ap": {key: candidate_ap[key] for key in ("size", "sha256")},
        "candidate_static": identity(payloads["candidate_static"]),
    }
    if any(run_manifest.get(key) != value for key, value in expected.items()):
        raise PromotionError("P3.21 promotion run manifest differs")
    acceptance = _acceptance(promotion_root, payloads)
    if type(timeout_sec) is not int or not 1 <= timeout_sec <= 600:
        raise PromotionError("P3.21 observation timeout is invalid")
    return {
        "schema": core.MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "run_id": live_run_id,
        "status": "ready-for-f1-approval",
        "target_profile": relative(target_profile),
        "candidate_ap": {
            key: candidate_ap[key] for key in ("path", "size", "sha256")
        },
        "rollback_ap": rollback_ap,
        "allowed_member": "boot.img.lz4",
        "observation": {"timeout_sec": timeout_sec, "acceptance": acceptance},
        "final_health_profile": "s22plus-fyg8-magisk",
        "runner_version": core.RUNNER_VERSION,
    }


def manifest_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")


def verify_manifest(
    value: dict[str, Any],
    payload: bytes,
    *,
    promotion_payloads: dict[str, bytes] | None = None,
) -> None:
    if payload != manifest_bytes(value):
        raise PromotionError("P3.21 ready manifest bytes differ")
    staged_value = value
    private_parent = ROOT / "workspace/private/outputs/s22plus_fyg8_p321"
    private_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".p321-ready-manifest-", dir=private_parent
    ) as name:
        temporary = Path(name)
        if promotion_payloads is not None:
            staged_root = temporary / "promotion"
            publish_promotion(staged_root, promotion_payloads)
            staged_value = json.loads(json.dumps(value))
            for key, filename in {
                "candidate_static": "candidate-static.json",
                "run_manifest": "run-manifest.json",
                "static_check": "static-check-result.json",
            }.items():
                staged_value["observation"]["acceptance"]["contract"][key][
                    "path"
                ] = relative(staged_root / filename)
        path = temporary / "manifest.json"
        path.write_bytes(manifest_bytes(staged_value))
        try:
            core.verify_bundle(ROOT, path)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise PromotionError(str(exc)) from exc


def publish_manifest(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise PromotionError("P3.21 ready manifest already exists")
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    _write_exclusive(path, payload, 0o644)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build(
    *,
    static_path: Path = DEFAULT_STATIC_OUTPUT,
    candidate_ap_path: Path = DEFAULT_CANDIDATE_AP,
    rollback_path: Path = DEFAULT_ROLLBACK_AP,
    promotion_root: Path = DEFAULT_PROMOTION,
    target_profile: Path = DEFAULT_TARGET_PROFILE,
    manifest_id: str = DEFAULT_MANIFEST_ID,
    live_run_id: str = DEFAULT_LIVE_RUN_ID,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, Any]]:
    static_value, static_payload, _builder_value, _builder_payload, ap_receipt = _candidate_inputs(
        static_path, candidate_ap_path
    )
    payloads = _promotion_payloads(static_value, static_payload, ap_receipt)
    candidate_ap = {
        "path": relative(candidate_ap_path),
        **{key: ap_receipt[key] for key in ("size", "sha256")},
    }
    rollback_payload = stable_bytes(rollback_path, "P3.21 exact rollback AP", 64 * 1024 * 1024)
    rollback_ap = {"path": relative(rollback_path), **identity(rollback_payload)}
    if {key: rollback_ap[key] for key in ("size", "sha256")} != ROLLBACK_IDENTITY:
        raise PromotionError("P3.21 rollback identity differs")
    try:
        verification = evidence.verify_offline_contract(
            _acceptance(promotion_root, payloads),
            payloads=payloads,
            receipts={name: identity(value) for name, value in payloads.items()},
            candidate_ap=ap_receipt,
        )
        frame = boot_verify.parse_ap_tar_md5(
            stable_bytes(candidate_ap_path, "P3.21 candidate AP recheck", 64 * 1024 * 1024)
        )[1]
        evidence.validate_e2_ap_payload(frame, verification["ap_payload_closure"])
    except (evidence.EvidenceError, boot_verify.BootVerifyError) as exc:
        raise PromotionError(str(exc)) from exc
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
    payload = manifest_bytes(manifest)
    verify_manifest(manifest, payload, promotion_payloads=payloads)
    return manifest, payloads, verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", type=Path, default=DEFAULT_STATIC_OUTPUT)
    parser.add_argument("--candidate-ap", type=Path, default=DEFAULT_CANDIDATE_AP)
    parser.add_argument("--rollback-ap", type=Path, default=DEFAULT_ROLLBACK_AP)
    parser.add_argument("--promotion", type=Path, default=DEFAULT_PROMOTION)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args(argv)
    paths = {
        name: value if value.is_absolute() else ROOT / value
        for name, value in {
            "static": args.static,
            "candidate": args.candidate_ap,
            "rollback": args.rollback_ap,
            "promotion": args.promotion,
            "manifest": args.manifest,
        }.items()
    }
    try:
        manifest, payloads, verification = build(
            static_path=paths["static"],
            candidate_ap_path=paths["candidate"],
            rollback_path=paths["rollback"],
            promotion_root=paths["promotion"],
        )
        if not args.audit_only:
            publish_promotion(paths["promotion"], payloads)
            verify_manifest(manifest, manifest_bytes(manifest))
            publish_manifest(paths["manifest"], manifest_bytes(manifest))
        print(json.dumps({
            "schema": SCHEMA,
            "verdict": VERDICT,
            "ready_schema": READY_SCHEMA,
            "ready_verdict": REHEARSAL_VERDICT if args.audit_only else READY_VERDICT,
            "promotion": str(paths["promotion"]),
            "manifest": str(paths["manifest"]),
            "manifest_id": manifest["manifest_id"],
            "run_id": adapter.P321_RUN_ID_HEX,
            "verification": verification["verified"],
            "created": not args.audit_only,
            "run_directory_created": False,
            "device_contact": False,
            "odin_invoked": False,
            "live_authorized": False,
        }, sort_keys=True))
        return 0
    except (OSError, PromotionError, RuntimeError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
