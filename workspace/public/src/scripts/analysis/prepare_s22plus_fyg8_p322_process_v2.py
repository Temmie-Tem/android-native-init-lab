#!/usr/bin/env python3
"""Thin P3.22 Process-v2 promotion/ready wrapper, host-only."""

from __future__ import annotations

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
import s22plus_fyg8_p322_process_v2_candidate_static as p322_static  # noqa: E402
import s22plus_fyg8_p322_stock_candidate_build as p322_build  # noqa: E402
import s22plus_fyg8_p322_stock_process_v2_adapter as p322_adapter  # noqa: E402


P321_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p321_process_v2.py"
P321_PREPARE_IDENTITY = {
    "size": 20_544,
    "sha256": "856014ff9772a58b3d435395baba8457e3ab9842932bd1ba097d4f52c7b475e8",
}

SCHEMA = "s22plus_fyg8_p322_process_v2_promotion_v1"
VERDICT = "PASS_P322_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p322_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P322_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P322_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = p322_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = p322_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = p322_build.p321.P319_ROLLBACK_AP
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p322/"
    "process-v2-promotion-20260831-02"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p322_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p322-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p322-live-1"
DEFAULT_TIMEOUT_SEC = 300
ROLLBACK_IDENTITY = dict(p322_build.p321.P319_ROLLBACK_IDENTITY)
TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p322"


class WrapperError(ValueError):
    pass


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
        raise WrapperError("P321 prepare source is unavailable") from exc
    fields = lambda value: (  # noqa: E731
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
        or fields(before) != fields(inside)
        or fields(before) != fields(after)
        or len(payload) != before.st_size
        or actual != expected
    ):
        raise WrapperError("P321 prepare source identity differs")
    return payload


def _proxy(module: Any, **updates: Any) -> types.SimpleNamespace:
    values = {name: value for name, value in vars(module).items() if not name.startswith("__")}
    values.update(updates)
    return types.SimpleNamespace(**values)


def _load_delegate() -> types.ModuleType:
    payload = _stable_source(P321_PREPARE_SOURCE, P321_PREPARE_IDENTITY)
    module = types.ModuleType("prepare_s22plus_fyg8_p321_bound_for_p322")
    module.__file__ = str(P321_PREPARE_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P321_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise WrapperError("P321 prepare source failed to load") from exc

    build_proxy = _proxy(
        p322_build,
        P319_ROLLBACK_AP=DEFAULT_ROLLBACK_AP,
        P319_ROLLBACK_IDENTITY=ROLLBACK_IDENTITY,
    )
    adapter_proxy = _proxy(
        p322_adapter,
        P321_RUN_ID_HEX=p322_adapter.P322_RUN_ID_HEX,
        P321_OVERLAY_CONTRACT_ID=p322_adapter.P322_OVERLAY_CONTRACT_ID,
    )
    evidence_proxy = _proxy(
        current_evidence,
        P321_RUN_MANIFEST_SCHEMA=current_evidence.P322_RUN_MANIFEST_SCHEMA,
        P321_STATIC_RESULT_SCHEMA=current_evidence.P322_STATIC_RESULT_SCHEMA,
        P321_STATIC_RESULT_VERDICT=current_evidence.P322_STATIC_RESULT_VERDICT,
    )
    module.candidate_static = p322_static
    module.candidate_build = build_proxy
    module.adapter = adapter_proxy
    module.evidence = evidence_proxy
    module.core = current_core
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
        setattr(module, name, value)
    return module


_DELEGATE = _load_delegate()
PromotionError = _DELEGATE.PromotionError
adapter = _DELEGATE.adapter
evidence = _DELEGATE.evidence
core = current_core
identity = _DELEGATE.identity
canonical = _DELEGATE.canonical
relative = _DELEGATE.relative
stable_bytes = _DELEGATE.stable_bytes
decode = _DELEGATE.decode
derive_manifest = _DELEGATE.derive_manifest
manifest_bytes = _DELEGATE.manifest_bytes
publish_promotion = _DELEGATE.publish_promotion
publish_manifest = _DELEGATE.publish_manifest
_ORIGINAL_BUILD = _DELEGATE.build
_ORIGINAL_PROMOTION_PAYLOADS = _DELEGATE._promotion_payloads


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    """Rotate the one P321 presentation literal and its dependent run hash."""
    payloads = _ORIGINAL_PROMOTION_PAYLOADS(
        static_value, static_payload, ap_receipt
    )
    run_manifest = decode(payloads["run_manifest"], "P3.22 run manifest")
    observation = run_manifest.get("observation_contract")
    if (
        not isinstance(observation, dict)
        or observation.get("accepted_identity")
        != "P321_STOCK_OBSERVER_V4_RETAINED"
    ):
        raise PromotionError("P3.21 promotion observation seam differs")
    observation["accepted_identity"] = "P322_STOCK_OBSERVER_V4_RETAINED"
    run_payload = canonical(run_manifest)
    static_result = decode(payloads["static_check"], "P3.22 static result")
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


def verify_manifest(
    value: dict[str, Any],
    payload: bytes,
    *,
    promotion_payloads: dict[str, bytes] | None = None,
) -> None:
    """Run the inherited bundle verifier in an isolated P322 temp namespace."""
    if payload != manifest_bytes(value):
        raise PromotionError("P3.22 ready manifest bytes differ")
    staged_value = value
    PRIVATE_PARENT.mkdir(mode=0o700, parents=True, exist_ok=True)
    PRIVATE_PARENT.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix=".p322-ready-manifest-", dir=PRIVATE_PARENT) as name:
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
    """Call the inherited builder with every captured P321 default replaced."""
    return _ORIGINAL_BUILD(
        static_path=static_path,
        candidate_ap_path=candidate_ap_path,
        rollback_path=rollback_path,
        promotion_root=promotion_root,
        target_profile=target_profile,
        manifest_id=manifest_id,
        live_run_id=live_run_id,
        timeout_sec=timeout_sec,
    )


_DELEGATE.verify_manifest = verify_manifest
_DELEGATE.build = build
_DELEGATE._promotion_payloads = _promotion_payloads
main = _DELEGATE.main


__all__ = [
    "DEFAULT_CANDIDATE_AP", "DEFAULT_MANIFEST", "DEFAULT_MANIFEST_ID",
    "DEFAULT_PROMOTION", "DEFAULT_ROLLBACK_AP", "DEFAULT_STATIC_OUTPUT",
    "DEFAULT_TARGET_PROFILE", "DEFAULT_TIMEOUT_SEC", "DEFAULT_LIVE_RUN_ID",
    "P321_PREPARE_IDENTITY", "P321_PREPARE_SOURCE", "PRIVATE_PARENT",
    "PromotionError", "READY_SCHEMA", "READY_VERDICT", "REHEARSAL_VERDICT",
    "ROLLBACK_IDENTITY", "SCHEMA", "TARGET", "VERDICT", "adapter", "build",
    "canonical", "core", "decode", "derive_manifest", "evidence", "identity",
    "main", "manifest_bytes", "publish_manifest", "publish_promotion",
    "relative", "stable_bytes", "verify_manifest",
]


if __name__ == "__main__":
    raise SystemExit(main())
