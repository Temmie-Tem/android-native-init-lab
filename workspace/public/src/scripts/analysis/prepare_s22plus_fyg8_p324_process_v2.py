#!/usr/bin/env python3
"""Prepare the P3.24 static promotion and ready manifest, host-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
ANALYSIS = Path(__file__).resolve().parent
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for _directory in (ANALYSIS, REVALIDATION):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import device_action_f1_evidence_v2 as current_evidence  # noqa: E402
import device_action_f1_v2 as current_core  # noqa: E402
import s22plus_fyg8_p324_process_v2_candidate_static as p324_static  # noqa: E402
import s22plus_fyg8_p324_stock_candidate_build as p324_build  # noqa: E402
import s22plus_fyg8_p324_stock_process_v2_adapter as p324_adapter  # noqa: E402


P323_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p323_process_v2.py"
P323_PREPARE_IDENTITY = {
    "size": 13_020,
    "sha256": "d3524b9d976243280929f3af48e09c6e299ec4fd578e7734926d96d80a458a9e",
}

SCHEMA = "s22plus_fyg8_p324_process_v2_promotion_v1"
VERDICT = "PASS_P324_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p324_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P324_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P324_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = p324_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = p324_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p324/"
    "process-v2-promotion-20260901-01"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p324_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p324-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p324-live-1"
DEFAULT_TIMEOUT_SEC = 300
ROLLBACK_IDENTITY = dict(p324_static.ROLLBACK_IDENTITY)
TARGET = dict(p324_static.TARGET)
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p324"


class WrapperError(ValueError):
    """The exact P323 prepare delegate or P324 binding differs."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _stable_source(path: Path, expected: dict[str, Any]) -> bytes:
    direct = path.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(int(expected["size"]) + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise WrapperError("P323 prepare source is unavailable") from exc

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

    actual = identity(payload)
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or inode(before) != inode(inside)
        or inode(before) != inode(after)
        or len(payload) != before.st_size
        or actual != expected
    ):
        raise WrapperError("P323 prepare source identity differs")
    return payload


def _proxy(module: Any, **updates: Any) -> types.SimpleNamespace:
    values = {name: value for name, value in vars(module).items() if not name.startswith("__")}
    values.update(updates)
    return types.SimpleNamespace(**values)


def _load_delegate() -> tuple[types.ModuleType, types.ModuleType]:
    payload = _stable_source(P323_PREPARE_SOURCE, P323_PREPARE_IDENTITY)
    module = types.ModuleType("prepare_s22plus_fyg8_p323_bound_for_p324")
    module.__file__ = str(P323_PREPARE_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P323_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise WrapperError("P323 prepare source failed to load") from exc
    base = module._BASE
    build_proxy = _proxy(
        p324_build,
        P319_ROLLBACK_AP=DEFAULT_ROLLBACK_AP,
        P319_ROLLBACK_IDENTITY=ROLLBACK_IDENTITY,
    )
    adapter_proxy = _proxy(
        p324_adapter,
        P321_RUN_ID_HEX=p324_adapter.P324_RUN_ID_HEX,
        P321_OVERLAY_CONTRACT_ID=p324_adapter.P324_OVERLAY_CONTRACT_ID,
    )
    evidence_proxy = _proxy(
        current_evidence,
        P321_RUN_MANIFEST_SCHEMA=current_evidence.P324_RUN_MANIFEST_SCHEMA,
        P321_STATIC_RESULT_SCHEMA=current_evidence.P324_STATIC_RESULT_SCHEMA,
        P321_STATIC_RESULT_VERDICT=current_evidence.P324_STATIC_RESULT_VERDICT,
    )
    base.candidate_static = p324_static
    base.candidate_build = build_proxy
    base.adapter = adapter_proxy
    base.evidence = evidence_proxy
    base.core = current_core
    for name, value in {
        "SCHEMA": SCHEMA,
        "VERDICT": VERDICT,
        "READY_SCHEMA": READY_SCHEMA,
        "READY_VERDICT": READY_VERDICT,
        "REHEARSAL_VERDICT": REHEARSAL_VERDICT,
        "DEFAULT_BUILDER_OUTPUT": DEFAULT_BUILDER_OUTPUT,
        "DEFAULT_STATIC_OUTPUT": DEFAULT_STATIC_OUTPUT,
        "DEFAULT_CANDIDATE_AP": DEFAULT_CANDIDATE_AP,
        "DEFAULT_ROLLBACK_AP": DEFAULT_ROLLBACK_AP,
        "DEFAULT_PROMOTION": DEFAULT_PROMOTION,
        "DEFAULT_MANIFEST": DEFAULT_MANIFEST,
        "DEFAULT_TARGET_PROFILE": DEFAULT_TARGET_PROFILE,
        "DEFAULT_MANIFEST_ID": DEFAULT_MANIFEST_ID,
        "DEFAULT_LIVE_RUN_ID": DEFAULT_LIVE_RUN_ID,
        "DEFAULT_TIMEOUT_SEC": DEFAULT_TIMEOUT_SEC,
        "ROLLBACK_IDENTITY": ROLLBACK_IDENTITY,
        "TARGET": TARGET,
    }.items():
        setattr(base, name, value)
        setattr(module, name, value)
    return module, base


_P323, _BASE = _load_delegate()
PromotionError = _BASE.PromotionError
adapter = p324_adapter
evidence = current_evidence
core = current_core
identity = _BASE.identity
canonical = _BASE.canonical
relative = _BASE.relative
stable_bytes = _BASE.stable_bytes
decode = _BASE.decode
manifest_bytes = _BASE.manifest_bytes
publish_promotion = _BASE.publish_promotion
publish_manifest = _BASE.publish_manifest
_BASE_PROMOTION_PAYLOADS = _P323._BASE_PROMOTION_PAYLOADS
_BASE_DERIVE_MANIFEST = _P323._BASE_DERIVE_MANIFEST
_BASE_BUILD = _P323._BASE_BUILD


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    payloads = _BASE_PROMOTION_PAYLOADS(static_value, static_payload, ap_receipt)
    run_manifest = decode(payloads["run_manifest"], "P324 run manifest")
    observation = run_manifest.get("observation_contract")
    if (
        not isinstance(observation, dict)
        or observation.get("accepted_identity")
        != "P321_STOCK_OBSERVER_V4_RETAINED"
    ):
        raise PromotionError("P323 promotion observation seam differs")
    observation["accepted_identity"] = "P324_STOCK_OBSERVER_V4_RETAINED"
    run_payload = canonical(run_manifest)
    static_result = decode(payloads["static_check"], "P324 static result")
    static_result["run_binding"] = {
        "canonical_manifest_size": len(run_payload),
        "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
        "verified": True,
    }
    return {
        "candidate_static": payloads["candidate_static"],
        "run_manifest": run_payload,
        "static_check": canonical(static_result),
    }


def derive_manifest(**kwargs: Any) -> dict[str, Any]:
    value = _BASE_DERIVE_MANIFEST(**kwargs)
    run_id = p324_adapter.P324_RUN_ID_HEX
    banner = ("S22PLUS-FYG8-E3:" + run_id + "\n").encode("ascii")
    value["observation"]["candidate_observer"] = {
        "kind": "exact_cdc_acm_banner_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + run_id,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": banner.hex(),
    }
    value["observation"][current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY] = (
        current_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE
    )
    return value


def verify_manifest(
    value: dict[str, Any],
    payload: bytes,
    *,
    promotion_payloads: dict[str, bytes] | None = None,
) -> None:
    if payload != manifest_bytes(value):
        raise PromotionError("P324 ready manifest bytes differ")
    staged_value = value
    PRIVATE_PARENT.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE_PARENT.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix=".p324-ready-", dir=PRIVATE_PARENT) as name:
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
                staged_value["observation"]["acceptance"]["contract"][key]["path"] = relative(
                    staged_root / filename
                )
        path = temporary / "manifest.json"
        path.write_bytes(manifest_bytes(staged_value))
        try:
            core.verify_bundle(ROOT, path)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise PromotionError(str(exc)) from exc


_BASE._promotion_payloads = _promotion_payloads
_BASE.derive_manifest = derive_manifest
_BASE.verify_manifest = verify_manifest


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
    return _BASE_BUILD(
        static_path=static_path,
        candidate_ap_path=candidate_ap_path,
        rollback_path=rollback_path,
        promotion_root=promotion_root,
        target_profile=target_profile,
        manifest_id=manifest_id,
        live_run_id=live_run_id,
        timeout_sec=timeout_sec,
    )


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
            "run_id": p324_adapter.P324_RUN_ID_HEX,
            "verification": verification["verified"],
            "created": not args.audit_only,
            "run_directory_created": False,
            "device_contact": False,
            "odin_invoked": False,
            "live_authorized": False,
        }, sort_keys=True))
        return 0
    except (OSError, PromotionError, RuntimeError, WrapperError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


__all__ = [
    "DEFAULT_CANDIDATE_AP",
    "DEFAULT_MANIFEST",
    "DEFAULT_MANIFEST_ID",
    "DEFAULT_PROMOTION",
    "DEFAULT_ROLLBACK_AP",
    "DEFAULT_STATIC_OUTPUT",
    "DEFAULT_TARGET_PROFILE",
    "DEFAULT_TIMEOUT_SEC",
    "DEFAULT_LIVE_RUN_ID",
    "P323_PREPARE_IDENTITY",
    "P323_PREPARE_SOURCE",
    "PRIVATE_PARENT",
    "PromotionError",
    "READY_SCHEMA",
    "READY_VERDICT",
    "REHEARSAL_VERDICT",
    "ROLLBACK_IDENTITY",
    "SCHEMA",
    "TARGET",
    "VERDICT",
    "adapter",
    "build",
    "canonical",
    "core",
    "decode",
    "derive_manifest",
    "evidence",
    "identity",
    "main",
    "manifest_bytes",
    "publish_manifest",
    "publish_promotion",
    "relative",
    "stable_bytes",
    "verify_manifest",
]


if __name__ == "__main__":
    raise SystemExit(main())
