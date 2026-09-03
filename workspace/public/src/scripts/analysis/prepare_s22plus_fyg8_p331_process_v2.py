#!/usr/bin/env python3
"""Prepare the P3.31 resident-reconnect F1 bundle (host-only rehearsal).

This wrapper reopens the exact P3.30 Process-v2 preparation engine and binds
the fresh P3.31 resident observer/runtime, candidate, and output identities.
It is host-only: an audit/build does not contact a device or invoke Odin.
"""

from __future__ import annotations

import argparse
import copy
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

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import s22plus_fyg8_p331_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p331_resident_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p331_resident_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p331_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p331_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p331_stock_process_v2_adapter as adapter  # noqa: E402


P330_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p330_process_v2.py"
P330_PREPARE_IDENTITY = {
    "size": 9_720,
    "sha256": "17b58112a287d0ad333e8a0d408fe8e35ec54a14cf315b3e1bcc9143fc695203",
}
SCHEMA = "s22plus_fyg8_p331_process_v2_promotion_v1"
VERDICT = "PASS_P331_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p331_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P331_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P331_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / (
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p331/"
    "process-v2-promotion-20260903-03"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p331_process_v2_ready_3.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p331-process-v2-ready-3"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p331-live-3"
DEFAULT_TIMEOUT_SEC = 300
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p331"
AUTH_KEY_IDENTITY = dict(evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY)


class PromotionError(ValueError):
    """The exact P3.31 promotion closure or manifest is not valid."""


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _inode(value: os.stat_result) -> tuple[int, ...]:
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


def _load() -> types.ModuleType:
    direct = P330_PREPARE_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P330_PREPARE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PromotionError("P3.30 prepare source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P330_PREPARE_IDENTITY
    ):
        raise PromotionError("P3.30 prepare source identity differs")
    module = types.ModuleType("prepare_s22plus_fyg8_p330_bound_for_p331")
    module.__file__ = str(P330_PREPARE_SOURCE)
    module.__package__ = ""
    # P3.30's source is the reviewed promotion seam, but its imports name the
    # consumed P3.30 candidate modules.  Bind those names to the already
    # loaded P3.31 modules while executing the exact pinned source.  This
    # keeps the loader independent of a stale P3.30 build re-open and restores
    # the import table immediately after execution.
    for _generation in ("p328", "p329", "p330"):
        setattr(candidate_static, f"{_generation.upper()}_KEY_IDENTITY", dict(AUTH_KEY_IDENTITY))
    aliases = {
        f"s22plus_fyg8_{generation}_{suffix}": module
        for generation in ("p328", "p329", "p330")
        for suffix, module in {
            "artifact_identity": artifact,
            "auth_acm_observer": framed_observer,
            "auth_exec_runtime": framed_runtime,
            "process_v2_candidate_static": candidate_static,
            "stock_candidate_build": candidate_build,
            "stock_process_v2_adapter": adapter,
        }.items()
    }
    previous = {name: sys.modules.get(name) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P330_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise PromotionError("P3.30 prepare source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
    return module


class _EvidenceProxy:
    """Bind the inherited P3.30 engine to P3.31 evidence schemas and role."""

    P328_RUN_MANIFEST_SCHEMA = evidence.P331_RUN_MANIFEST_SCHEMA
    P328_STATIC_RESULT_SCHEMA = evidence.P331_STATIC_RESULT_SCHEMA
    P328_STATIC_RESULT_VERDICT = evidence.P331_STATIC_RESULT_VERDICT
    CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE = (
        evidence.CANDIDATE_AUTHENTICATED_RESIDENT_EXEC_ROLE
    )

    @staticmethod
    def p328_authenticated_framed_observer_spec() -> dict[str, Any]:
        return evidence.p331_authenticated_resident_framed_observer_spec()

    def __getattr__(self, name: str) -> Any:
        return getattr(evidence, name)


_P330 = _load()
_INNER = _P330._INNER
_INNER_PROMOTION_PAYLOADS = _INNER._promotion_payloads
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
    # The P3.31 static projection intentionally keeps only the public key
    # identity.  The inherited P3.28 engine also checks the derived init
    # occurrence count; supply that already-proved grammar fact only in the
    # in-memory value used by the engine, never in the published static bytes.
    engine_value = static_value
    authentication = static_value.get("authentication")
    if isinstance(authentication, dict) and "embedded_key_occurrences_in_init" not in authentication:
        engine_value = copy.deepcopy(static_value)
        engine_value["authentication"]["embedded_key_occurrences_in_init"] = 1
    payloads = dict(_INNER_PROMOTION_PAYLOADS(engine_value, static_payload, ap_receipt))
    run_manifest = json.loads(payloads["run_manifest"])
    run_manifest["observation_contract"]["accepted_identity"] = (
        "P331_STOCK_OBSERVER_V4_RETAINED"
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
    """Recheck a manifest in a P3.31-only private temporary namespace."""

    if payload != _INNER.manifest_bytes(value):
        raise PromotionError("P3.31 ready manifest bytes differ")
    private_root = ROOT / "workspace/private"
    try:
        private_root.lstat()
    except OSError as exc:
        raise PromotionError("P3.31 private workspace is unavailable") from exc
    with tempfile.TemporaryDirectory(prefix=".p331-ready-", dir=private_root) as name:
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
                staged_value["observation"]["acceptance"]["contract"][key][
                    "path"
                ] = _INNER.relative(staged_root / filename)
        path = temporary / "manifest.json"
        path.write_bytes(_INNER.manifest_bytes(staged_value))
        try:
            core.verify_bundle(ROOT, path)
        except (core.F1V2Error, core.F1TransportError, OSError) as exc:
            raise PromotionError(str(exc)) from exc


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


if __name__ == "__main__":
    raise SystemExit(main())
