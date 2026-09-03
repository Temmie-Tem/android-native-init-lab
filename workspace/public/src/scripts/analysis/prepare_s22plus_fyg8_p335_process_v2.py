#!/usr/bin/env python3
"""Prepare the P3.35 Process-v2 bundle in a host-only rehearsal."""

from __future__ import annotations

import copy
import hashlib
import json
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

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p335_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p335_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p335_stock_process_v2_adapter as adapter  # noqa: E402
import s22plus_fyg8_p335_process_v2_candidate_static as candidate_static  # noqa: E402

try:
    import s22plus_fyg8_p335_retained_listener_runtime as framed_runtime  # noqa: E402
except ModuleNotFoundError:
    framed_runtime = None
try:
    import s22plus_fyg8_p335_retained_listener_acm_observer as framed_observer  # noqa: E402
except ModuleNotFoundError:
    framed_observer = None


P334_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p334_process_v2.py"
P334_PREPARE_IDENTITY = {
    "size": 10_876,
    "sha256": "977a0130f5f4c01bb2667037a0366e9fd0afdeeb8c12abeb7d9e35db0ea76917",
}
SCHEMA = "s22plus_fyg8_p335_process_v2_promotion_v1"
VERDICT = "PASS_P335_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p335_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P335_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P335_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p335/"
    "process-v2-promotion-20260904-02"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p335_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p335-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p335-live-1"
DEFAULT_TIMEOUT_SEC = 300
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p335"
AUTH_KEY_IDENTITY = dict(evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY)


class PromotionError(ValueError):
    """The exact P3.35 promotion closure or manifest is invalid."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: Any) -> tuple[int, ...]:
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


def _stable_source() -> bytes:
    direct = P334_PREPARE_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P334_PREPARE_IDENTITY["size"] + 1)
            inside = __import__("os").fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PromotionError("P3.34 prepare source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P334_PREPARE_IDENTITY
    ):
        raise PromotionError("P3.34 prepare source identity differs")
    return payload


def _load_p334() -> types.ModuleType | None:
    if framed_runtime is None or framed_observer is None:
        return None
    payload = _stable_source()
    module = types.ModuleType("prepare_s22plus_fyg8_p334_bound_for_p335")
    module.__file__ = str(P334_PREPARE_SOURCE)
    module.__package__ = ""
    aliases = {
        "s22plus_fyg8_p334_artifact_identity": artifact,
        "s22plus_fyg8_p334_first_read_rc_acm_observer": framed_observer,
        "s22plus_fyg8_p334_first_read_rc_runtime": framed_runtime,
        "s22plus_fyg8_p334_process_v2_candidate_static": candidate_static,
        "s22plus_fyg8_p334_stock_candidate_build": candidate_build,
        "s22plus_fyg8_p334_stock_process_v2_adapter": adapter,
    }
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P334_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise PromotionError("P3.34 prepare source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    return module


_P334 = _load_p334()
if _P334 is not None:
    _P330 = _P334._P330
    _INNER = _P334._INNER
    _INNER_PROMOTION_PAYLOADS = _INNER._promotion_payloads
else:
    _P330 = None
    _INNER = None
    _INNER_PROMOTION_PAYLOADS = None


def _p335_observer_spec() -> dict[str, Any]:
    candidates = (
        "p335_authenticated_attended_resident_observer_spec",
        "p335_attended_resident_observer_spec",
        "p335_authenticated_resident_observer_spec",
    )
    for name in candidates:
        value = getattr(evidence, name, None)
        if callable(value):
            return value()
    if hasattr(candidate_static, "_observer_projection"):
        return candidate_static._observer_projection()  # noqa: SLF001
    raise PromotionError("P3.35 observer specification is unavailable")


class _EvidenceProxy:
    P328_RUN_MANIFEST_SCHEMA = getattr(
        evidence, "P335_RUN_MANIFEST_SCHEMA", "s22plus_fyg8_p335_run_manifest_v1"
    )
    P328_STATIC_RESULT_SCHEMA = getattr(
        evidence, "P335_STATIC_RESULT_SCHEMA", "s22plus_fyg8_p335_static_result_v1"
    )
    P328_STATIC_RESULT_VERDICT = getattr(
        evidence, "P335_STATIC_RESULT_VERDICT", "PASS_P335_STATIC_RESULT_HOST_ONLY"
    )
    CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE = getattr(
        evidence,
        "CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE",
        "p328_authenticated_framed_exec_session_v1",
    )

    @staticmethod
    def p328_authenticated_framed_observer_spec() -> dict[str, Any]:
        return _p335_observer_spec()

    def __getattr__(self, name: str) -> Any:
        return getattr(evidence, name)


if _P334 is not None:
    for _module in (_P330, _INNER):
        _module.evidence = _EvidenceProxy()
        _module.core = core
        _module.artifact = artifact
        _module.framed_observer = framed_observer
        _module.framed_runtime = framed_runtime
        _module.candidate_static = candidate_static
        _module.candidate_build = candidate_build
        _module.adapter = adapter
    for _name, _value in {
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
        "PRIVATE_PARENT": PRIVATE_PARENT,
        "AUTH_KEY_IDENTITY": AUTH_KEY_IDENTITY,
    }.items():
        setattr(_INNER, _name, _value)
        setattr(_P330, _name, _value)


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    if _INNER_PROMOTION_PAYLOADS is None or _INNER is None:
        raise PromotionError("P3.35 promotion engine is unavailable")
    engine_value = static_value
    authentication = static_value.get("authentication")
    if isinstance(authentication, dict) and "embedded_key_occurrences_in_init" not in authentication:
        engine_value = copy.deepcopy(static_value)
        engine_value["authentication"]["embedded_key_occurrences_in_init"] = 1
    payloads = dict(_INNER_PROMOTION_PAYLOADS(engine_value, static_payload, ap_receipt))
    run_manifest = json.loads(payloads["run_manifest"])
    run_manifest["observation_contract"]["accepted_identity"] = (
        "P335_STOCK_OBSERVER_V4_RETAINED"
    )
    run_payload = _INNER.canonical(run_manifest)
    static_result = json.loads(payloads["static_check"])
    static_result["run_binding"] = {
        "canonical_manifest_size": len(run_payload),
        "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
        "verified": True,
    }
    payloads["run_manifest"] = run_payload
    payloads["static_check"] = _INNER.canonical(static_result)
    return payloads


if _P334 is not None:
    _INNER._promotion_payloads = _promotion_payloads
    _P330._promotion_payloads = _promotion_payloads
    defaults = dict(_INNER.build.__kwdefaults__ or {})
    defaults.update(
        {
            "static_path": DEFAULT_STATIC_OUTPUT,
            "candidate_ap_path": DEFAULT_CANDIDATE_AP,
            "rollback_path": DEFAULT_ROLLBACK_AP,
            "promotion_root": DEFAULT_PROMOTION,
            "target_profile": DEFAULT_TARGET_PROFILE,
            "manifest_id": DEFAULT_MANIFEST_ID,
            "live_run_id": DEFAULT_LIVE_RUN_ID,
            "timeout_sec": DEFAULT_TIMEOUT_SEC,
        }
    )
    _INNER.build.__kwdefaults__ = defaults
    _P330.build.__kwdefaults__ = defaults


def verify_manifest(
    value: dict[str, Any],
    payload: bytes,
    *,
    promotion_payloads: dict[str, bytes] | None = None,
) -> None:
    if _INNER is None:
        raise PromotionError("P3.35 promotion engine is unavailable")
    if payload != _INNER.manifest_bytes(value):
        raise PromotionError("P3.35 ready manifest bytes differ")
    private_root = ROOT / "workspace/private"
    try:
        private_root.lstat()
    except OSError as exc:
        raise PromotionError("P3.35 private workspace is unavailable") from exc
    with tempfile.TemporaryDirectory(prefix=".p335-ready-", dir=private_root) as name:
        temporary = Path(name)
        staged_value = value
        if promotion_payloads is not None:
            staged_root = temporary / "promotion"
            _INNER.publish_promotion(staged_root, promotion_payloads)
            staged_value = json.loads(json.dumps(value))
            for key, filename in {
                "candidate_static": "candidate-static.json",
                "run_manifest": "run-manifest.json",
                "static_check": "static-check-result.json",
            }.items():
                staged_value["observation"]["acceptance"]["contract"][key]["path"] = (
                    _INNER.relative(staged_root / filename)
                )
        path = temporary / "manifest.json"
        path.write_bytes(_INNER.manifest_bytes(staged_value))
        try:
            core.verify_bundle(ROOT, path)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise PromotionError(str(exc)) from exc


if _P334 is not None:
    _INNER.verify_manifest = verify_manifest
    _P330.verify_manifest = verify_manifest
    canonical = _INNER.canonical
    manifest_bytes = _INNER.manifest_bytes
    relative = _INNER.relative
    publish_promotion = _INNER.publish_promotion
    publish_manifest = _INNER.publish_manifest
    derive_manifest = _INNER.derive_manifest
    build = _INNER.build
    main = _INNER.main
    ROLLBACK_IDENTITY = dict(_INNER.ROLLBACK_IDENTITY)
    TARGET = dict(_INNER.TARGET)
else:
    canonical = None
    manifest_bytes = None
    relative = None
    publish_promotion = None
    publish_manifest = None
    derive_manifest = None
    build = None
    main = None
    ROLLBACK_IDENTITY = {
        "size": 23_367_721,
        "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
    }
    TARGET = {"model": "SM-S906N", "codename": "g0q", "build": "S906NKSS7FYG8"}


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__" and main is not None:
    raise SystemExit(main())
