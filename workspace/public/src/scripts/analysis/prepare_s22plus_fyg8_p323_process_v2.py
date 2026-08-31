#!/usr/bin/env python3
"""Prepare the P3.23 static promotion and ready manifest, host-only."""

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
import s22plus_fyg8_p323_process_v2_candidate_static as p323_static  # noqa: E402
import s22plus_fyg8_p323_stock_candidate_build as p323_build  # noqa: E402
import s22plus_fyg8_p323_stock_process_v2_adapter as p323_adapter  # noqa: E402


P322_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p322_process_v2.py"
P322_PREPARE_IDENTITY = {
    "size": 10_988,
    "sha256": "f4510b7aaf83bf90a188e1f27e5639889a7bcad31936ab21ad5de347c4ed165a",
}

SCHEMA = "s22plus_fyg8_p323_process_v2_promotion_v1"
VERDICT = "PASS_P323_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p323_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P323_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P323_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = p323_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = p323_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p323/process-v2-promotion-20260831-01"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p323_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p323-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p323-live-1"
DEFAULT_TIMEOUT_SEC = 300
ROLLBACK_IDENTITY = dict(p323_static.ROLLBACK_IDENTITY)
TARGET = dict(p323_static.TARGET)
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p323"


class WrapperError(ValueError):
    """The exact P322 prepare delegate or P323 binding differs."""


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
        raise WrapperError("P322 prepare source is unavailable") from exc

    def inode(value: os.stat_result) -> tuple[int, ...]:
        return (
            value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns,
            value.st_ctime_ns,
        )

    actual = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
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
        raise WrapperError("P322 prepare source identity differs")
    return payload


def _proxy(module: Any, **updates: Any) -> types.SimpleNamespace:
    values = {name: value for name, value in vars(module).items() if not name.startswith("__")}
    values.update(updates)
    return types.SimpleNamespace(**values)


def _load_delegate() -> tuple[types.ModuleType, types.ModuleType]:
    payload = _stable_source(P322_PREPARE_SOURCE, P322_PREPARE_IDENTITY)
    module = types.ModuleType("prepare_s22plus_fyg8_p322_bound_for_p323")
    module.__file__ = str(P322_PREPARE_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P322_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise WrapperError("P322 prepare source failed to load") from exc
    delegate = module._DELEGATE
    build_proxy = _proxy(
        p323_build,
        P319_ROLLBACK_AP=DEFAULT_ROLLBACK_AP,
        P319_ROLLBACK_IDENTITY=ROLLBACK_IDENTITY,
    )
    adapter_proxy = _proxy(
        p323_adapter,
        P321_RUN_ID_HEX=p323_adapter.P323_RUN_ID_HEX,
        P321_OVERLAY_CONTRACT_ID=p323_adapter.P323_OVERLAY_CONTRACT_ID,
    )
    evidence_proxy = _proxy(
        current_evidence,
        P321_RUN_MANIFEST_SCHEMA=current_evidence.P323_RUN_MANIFEST_SCHEMA,
        P321_STATIC_RESULT_SCHEMA=current_evidence.P323_STATIC_RESULT_SCHEMA,
        P321_STATIC_RESULT_VERDICT=current_evidence.P323_STATIC_RESULT_VERDICT,
    )
    delegate.candidate_static = p323_static
    delegate.candidate_build = build_proxy
    delegate.adapter = adapter_proxy
    delegate.evidence = evidence_proxy
    delegate.core = current_core
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
        setattr(delegate, name, value)
        setattr(module, name, value)
    return module, delegate


_P322, _BASE = _load_delegate()
PromotionError = _BASE.PromotionError
adapter = _BASE.adapter
evidence = _BASE.evidence
core = current_core
identity = _BASE.identity
canonical = _BASE.canonical
relative = _BASE.relative
stable_bytes = _BASE.stable_bytes
decode = _BASE.decode
manifest_bytes = _BASE.manifest_bytes
publish_promotion = _BASE.publish_promotion
publish_manifest = _BASE.publish_manifest
_BASE_PROMOTION_PAYLOADS = _P322._ORIGINAL_PROMOTION_PAYLOADS
_BASE_DERIVE_MANIFEST = _BASE.derive_manifest
_BASE_BUILD = _P322._ORIGINAL_BUILD


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    payloads = _BASE_PROMOTION_PAYLOADS(static_value, static_payload, ap_receipt)
    run_manifest = decode(payloads["run_manifest"], "P323 run manifest")
    observation = run_manifest.get("observation_contract")
    if not isinstance(observation, dict) or observation.get("accepted_identity") != "P321_STOCK_OBSERVER_V4_RETAINED":
        raise PromotionError("P321 promotion seam differs")
    observation["accepted_identity"] = "P323_STOCK_OBSERVER_V4_RETAINED"
    run_payload = canonical(run_manifest)
    static_result = decode(payloads["static_check"], "P323 static result")
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
    run_id = p323_adapter.P323_RUN_ID_HEX
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
        raise PromotionError("P323 ready manifest bytes differ")
    staged_value = value
    PRIVATE_PARENT.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE_PARENT.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix=".p323-ready-", dir=PRIVATE_PARENT) as name:
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
                staged_value["observation"]["acceptance"]["contract"][key]["path"] = relative(staged_root / filename)
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
            "static": args.static, "candidate": args.candidate_ap,
            "rollback": args.rollback_ap, "promotion": args.promotion,
            "manifest": args.manifest,
        }.items()
    }
    try:
        manifest, payloads, verification = build(
            static_path=paths["static"], candidate_ap_path=paths["candidate"],
            rollback_path=paths["rollback"], promotion_root=paths["promotion"],
        )
        if not args.audit_only:
            publish_promotion(paths["promotion"], payloads)
            verify_manifest(manifest, manifest_bytes(manifest))
            publish_manifest(paths["manifest"], manifest_bytes(manifest))
        print(json.dumps({
            "schema": SCHEMA, "verdict": VERDICT, "ready_schema": READY_SCHEMA,
            "ready_verdict": REHEARSAL_VERDICT if args.audit_only else READY_VERDICT,
            "promotion": str(paths["promotion"]), "manifest": str(paths["manifest"]),
            "manifest_id": manifest["manifest_id"], "run_id": p323_adapter.P323_RUN_ID_HEX,
            "verification": verification["verified"], "created": not args.audit_only,
            "run_directory_created": False, "device_contact": False,
            "odin_invoked": False, "live_authorized": False,
        }, sort_keys=True))
        return 0
    except (OSError, PromotionError, RuntimeError, WrapperError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
