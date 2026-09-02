#!/usr/bin/env python3
"""Prepare the P3.29 bounded-udev-settle F1 bundle (host-only)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
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
import s22plus_fyg8_p329_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p329_auth_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p329_auth_exec_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p329_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p329_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p329_stock_process_v2_adapter as adapter  # noqa: E402


P328_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p328_process_v2.py"
P328_PREPARE_IDENTITY = {
    "size": 27_737,
    "sha256": "bdbaf4567d05785703c5738b5062e9b5d95b978a05de26f5cd21254f4ba4a1c1",
}
SCHEMA = "s22plus_fyg8_p329_process_v2_promotion_v1"
VERDICT = "PASS_P329_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p329_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P329_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P329_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / (
    "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
)
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p329/"
    "process-v2-promotion-20260903-01"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/"
    "s22plus_fyg8_p329_process_v2_ready_1.json"
)
DEFAULT_TARGET_PROFILE = ROOT / (
    "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
)
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p329-process-v2-ready-1"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p329-live-1"
DEFAULT_TIMEOUT_SEC = 300
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p329"
AUTH_KEY_IDENTITY = dict(candidate_static.P329_KEY_IDENTITY)


class PromotionError(ValueError):
    """The exact P3.28 promotion engine or P3.29 closure differs."""


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
    direct = P328_PREPARE_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P328_PREPARE_IDENTITY["size"] + 1)
            inside = os.fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PromotionError("P3.28 prepare source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P328_PREPARE_IDENTITY
    ):
        raise PromotionError("P3.28 prepare source identity differs")
    module = types.ModuleType("prepare_s22plus_fyg8_p328_bound_for_p329")
    module.__file__ = str(P328_PREPARE_SOURCE)
    module.__package__ = ""
    try:
        exec(compile(payload, str(P328_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise PromotionError("P3.28 prepare source failed to load") from exc
    return module


class _EvidenceProxy:
    P328_RUN_MANIFEST_SCHEMA = evidence.P329_RUN_MANIFEST_SCHEMA
    P328_STATIC_RESULT_SCHEMA = evidence.P329_STATIC_RESULT_SCHEMA
    P328_STATIC_RESULT_VERDICT = evidence.P329_STATIC_RESULT_VERDICT
    CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE = (
        evidence.CANDIDATE_AUTHENTICATED_SETTLED_EXEC_ROLE
    )

    @staticmethod
    def p328_authenticated_framed_observer_spec() -> dict[str, Any]:
        return evidence.p329_authenticated_framed_observer_spec()

    def __getattr__(self, name: str) -> Any:
        return getattr(evidence, name)


_P328 = _load()
_P328_PROMOTION_PAYLOADS = _P328._promotion_payloads
_P328.evidence = _EvidenceProxy()
_P328.core = core
_P328.artifact = artifact
_P328.framed_observer = framed_observer
_P328.framed_runtime = framed_runtime
_P328.candidate_static = candidate_static
_P328.candidate_build = candidate_build
_P328.adapter = adapter
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
    setattr(_P328, _name, _value)


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    payloads = dict(_P328_PROMOTION_PAYLOADS(static_value, static_payload, ap_receipt))
    run_manifest = json.loads(payloads["run_manifest"])
    run_manifest["observation_contract"][
        "accepted_identity"
    ] = "P329_STOCK_OBSERVER_V4_RETAINED"
    run_payload = _P328.canonical(run_manifest)
    static_result = json.loads(payloads["static_check"])
    static_result["run_binding"] = {
        "canonical_manifest_size": len(run_payload),
        "canonical_manifest_sha256": hashlib.sha256(run_payload).hexdigest(),
        "verified": True,
    }
    payloads["run_manifest"] = run_payload
    payloads["static_check"] = _P328.canonical(static_result)
    return payloads


_P328._promotion_payloads = _promotion_payloads
defaults = dict(_P328.build.__kwdefaults__ or {})
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
_P328.build.__kwdefaults__ = defaults

canonical = _P328.canonical
manifest_bytes = _P328.manifest_bytes
relative = _P328.relative
publish_promotion = _P328.publish_promotion
publish_manifest = _P328.publish_manifest
verify_manifest = _P328.verify_manifest
derive_manifest = _P328.derive_manifest
build = _P328.build
main = _P328.main
ROLLBACK_IDENTITY = dict(_P328.ROLLBACK_IDENTITY)
TARGET = dict(_P328.TARGET)


if __name__ == "__main__":
    raise SystemExit(main())
