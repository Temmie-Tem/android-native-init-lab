#!/usr/bin/env python3
"""Prepare the P3.39 Process-v2 bundle in a host-only rehearsal.

P3.39 keeps the reviewed P3.38 manifest/promotion engine in an isolated
module graph and binds every authority-bearing identity to the fresh P339
overlay.  This file only performs host-side validation and publication; it
never contacts a device or invokes ADB/Odin.
"""

from __future__ import annotations

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
import s22plus_fyg8_p339_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p339_open_read_branch_acm_observer as framed_observer  # noqa: E402
import s22plus_fyg8_p339_open_read_branch_runtime as framed_runtime  # noqa: E402
import s22plus_fyg8_p339_process_v2_candidate_static as candidate_static  # noqa: E402
import s22plus_fyg8_p339_stock_candidate_build as candidate_build  # noqa: E402
import s22plus_fyg8_p339_stock_process_v2_adapter as adapter  # noqa: E402


P338_PREPARE_SOURCE = ANALYSIS / "prepare_s22plus_fyg8_p338_process_v2.py"
P338_PREPARE_IDENTITY = {
    "size": 14_218,
    "sha256": "516e17c39ecf308eefd83f6677f0ebb386b83fc73aa3f3a6bd9e6a28c8f602ba",
}
SCHEMA = "s22plus_fyg8_p339_process_v2_promotion_v1"
VERDICT = "PASS_P339_PROCESS_V2_PROMOTION_HOST_ONLY"
READY_SCHEMA = "s22plus_fyg8_p339_ready_manifest_builder_v1"
READY_VERDICT = "PASS_P339_PROCESS_V2_READY_MANIFEST_HOST_ONLY"
REHEARSAL_VERDICT = "PASS_P339_PROCESS_V2_READY_MANIFEST_REHEARSAL_HOST_ONLY"
DEFAULT_BUILDER_OUTPUT = candidate_build.DEFAULT_OUTPUT_ROOT
DEFAULT_STATIC_OUTPUT = candidate_static.DEFAULT_OUTPUT
DEFAULT_CANDIDATE_AP = DEFAULT_BUILDER_OUTPUT / "candidate-a/odin4/AP.tar.md5"
DEFAULT_ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
DEFAULT_PROMOTION = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p339/process-v2-promotion-20260905-02"
)
DEFAULT_MANIFEST = ROOT / (
    "workspace/public/src/device-action/manifests/s22plus_fyg8_p339_process_v2_ready_2.json"
)
DEFAULT_TARGET_PROFILE = ROOT / "workspace/public/src/device-action/profiles/s22plus_fyg8.json"
DEFAULT_MANIFEST_ID = "s22plus-fyg8-p339-process-v2-ready-2"
DEFAULT_LIVE_RUN_ID = "s22plus-fyg8-p339-live-2"
DEFAULT_TIMEOUT_SEC = 300
PRIVATE_PARENT = ROOT / "workspace/private/outputs/s22plus_fyg8_p339"
AUTH_KEY_IDENTITY = dict(evidence.P339_AUTH_EXEC_AUTH_KEY_IDENTITY)
P338_RUN_ID_HEX = adapter.P338_PREDECESSOR_RUN_ID_HEX
P339_RUN_ID_HEX = adapter.P339_RUN_ID_HEX


class PromotionError(ValueError):
    """The exact P3.38 promotion closure or P3.39 manifest is invalid."""


# The historical P336 loader reaches one private predecessor engine attribute
# while importing the P338 prepare source.  Give that loader a compatibility
# namespace without importing or mutating the consumed P338 adapter module.
_LEGACY_ADAPTER = types.ModuleType("s22plus_fyg8_p338_stock_process_v2_adapter")
_LEGACY_ADAPTER.__file__ = str(Path(adapter.__file__).resolve())
_LEGACY_ADAPTER.__dict__.update(vars(adapter))
_LEGACY_ADAPTER.P337_PREDECESSOR_RUN_ID_HEX = adapter.P338_PREDECESSOR_RUN_ID_HEX
_P338_ADAPTER = getattr(adapter, "predecessor", None)
_P337_ADAPTER = getattr(_P338_ADAPTER, "predecessor", None)
_LEGACY_ADAPTER._P335 = getattr(_P337_ADAPTER, "_P335", None)
_LEGACY_ADAPTER.predecessor = types.SimpleNamespace(
    _P335=_LEGACY_ADAPTER._P335
)


def _legacy_adapter_getattr(name: str) -> Any:
    return getattr(adapter, name)


_LEGACY_ADAPTER.__getattr__ = _legacy_adapter_getattr


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
    direct = P338_PREPARE_SOURCE.absolute()
    try:
        before = direct.lstat()
        resolved = direct.resolve(strict=True)
        with direct.open("rb") as stream:
            payload = stream.read(P338_PREPARE_IDENTITY["size"] + 1)
            inside = __import__("os").fstat(stream.fileno())
        after = direct.lstat()
    except OSError as exc:
        raise PromotionError("P3.37 prepare source is unavailable") from exc
    if (
        direct != resolved
        or stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or _inode(before) != _inode(inside)
        or _inode(before) != _inode(after)
        or len(payload) != before.st_size
        or identity(payload) != P338_PREPARE_IDENTITY
    ):
        raise PromotionError("P3.37 prepare source identity differs")
    return payload


def _load_p338() -> types.ModuleType:
    payload = _stable_source()
    module = types.ModuleType("prepare_s22plus_fyg8_p338_bound_for_p339")
    module.__file__ = str(P338_PREPARE_SOURCE)
    module.__package__ = ""
    aliases = {
        "s22plus_fyg8_p338_artifact_identity": artifact,
        "s22plus_fyg8_p338_open_read_branch_acm_observer": framed_observer,
        "s22plus_fyg8_p338_open_read_branch_runtime": framed_runtime,
        "s22plus_fyg8_p338_open_read_diag_acm_observer": framed_observer,
        "s22plus_fyg8_p338_open_read_diag_runtime": framed_runtime,
        "s22plus_fyg8_p338_long_idle_acm_observer": framed_observer,
        "s22plus_fyg8_p338_long_idle_runtime": framed_runtime,
        "s22plus_fyg8_p338_retained_listener_acm_observer": framed_observer,
        "s22plus_fyg8_p338_retained_listener_runtime": framed_runtime,
        "s22plus_fyg8_p338_process_v2_candidate_static": candidate_static,
        "s22plus_fyg8_p338_stock_candidate_build": candidate_build,
        "s22plus_fyg8_p338_stock_process_v2_adapter": _LEGACY_ADAPTER,
    }
    hidden: dict[str, types.ModuleType] = {}
    for name in list(sys.modules):
        if name.startswith("s22plus_fyg8_p") and not name.startswith(
            "s22plus_fyg8_p339_"
        ):
            hidden[name] = sys.modules.pop(name)
    missing = object()
    previous = {name: sys.modules.get(name, missing) for name in aliases}
    try:
        sys.modules.update(aliases)
        exec(compile(payload, str(P338_PREPARE_SOURCE), "exec", dont_inherit=True), module.__dict__)  # noqa: S102
    except Exception as exc:
        raise PromotionError("P3.37 prepare source failed to load") from exc
    finally:
        for name, old in previous.items():
            if old is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old
        for name, old in hidden.items():
            if name not in sys.modules:
                sys.modules[name] = old
    return module


_P338 = _load_p338()
_P330 = _P338._P330
_INNER = _P338._INNER
_INNER_PROMOTION_PAYLOADS = _INNER._promotion_payloads


def _p339_observer_spec() -> dict[str, Any]:
    return dict(evidence.p339_authenticated_open_read_branch_observer_spec())


_PREDECESSOR_ENGINE = _LEGACY_ADAPTER._P335


class _P339PrepareAdapterProxy:
    """Expose only the predecessor ABI labels inside the private graph."""

    LONG_FAMILY = getattr(_PREDECESSOR_ENGINE, "LONG_FAMILY")
    UNSAT_FAMILY = getattr(_PREDECESSOR_ENGINE, "UNSAT_FAMILY")
    TERMINAL_STAGE = getattr(_PREDECESSOR_ENGINE, "TERMINAL_STAGE")
    P328_RUN_ID_HEX = P339_RUN_ID_HEX
    P328_RUN_ID = bytes.fromhex(P339_RUN_ID_HEX)
    P328_STOCK_RUN_ID = P328_RUN_ID
    P328_DECODER_ID = adapter.DECODER_ID
    P328_OBSERVER_CONTRACT_ID = adapter.OBSERVER_CONTRACT_ID
    P328_OVERLAY_CONTRACT_ID = adapter.OVERLAY_CONTRACT_ID
    P328_POLICY_ID = adapter.POLICY_ID
    P328_POLICY_PREIMAGE = adapter.POLICY_PREIMAGE

    def __getattr__(self, name: str) -> Any:
        return getattr(adapter, name)


_PREPARE_ADAPTER = _P339PrepareAdapterProxy()


class _EvidenceProxy:
    P328_RUN_MANIFEST_SCHEMA = evidence.P339_RUN_MANIFEST_SCHEMA
    P328_STATIC_RESULT_SCHEMA = evidence.P339_STATIC_RESULT_SCHEMA
    P328_STATIC_RESULT_VERDICT = evidence.P339_STATIC_RESULT_VERDICT
    CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE = getattr(
        evidence, "CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE"
    )

    @staticmethod
    def p328_authenticated_framed_observer_spec() -> dict[str, Any]:
        return _p339_observer_spec()

    def __getattr__(self, name: str) -> Any:
        return getattr(evidence, name)


def _patch_prepare_graph() -> None:
    # P338's wrapper retains a private P336 prepare module in addition to the
    # public P330/P328 engine. Rebind that module too so its stale static
    # callback cannot reopen a P338 result before P339 is checked.
    modules = [_P338, getattr(_P338, "_P336", None), _P330, _INNER]
    modules = [module for module in modules if isinstance(module, types.ModuleType)]
    for module in modules:
        module.evidence = _EvidenceProxy()
        module.core = core
        module.artifact = artifact
        module.framed_observer = framed_observer
        module.framed_runtime = framed_runtime
        module.candidate_static = candidate_static
        module.candidate_build = candidate_build
        module.adapter = _PREPARE_ADAPTER
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
            "PRIVATE_PARENT": PRIVATE_PARENT,
            "AUTH_KEY_IDENTITY": AUTH_KEY_IDENTITY,
            "TARGET": dict(candidate_build.TARGET),
            "P336_RUN_ID_HEX": P339_RUN_ID_HEX,
            "P338_RUN_ID_HEX": P339_RUN_ID_HEX,
        }.items():
            setattr(module, name, value)


_patch_prepare_graph()


def _promotion_payloads(
    static_value: dict[str, Any],
    static_payload: bytes,
    ap_receipt: dict[str, Any],
) -> dict[str, bytes]:
    payloads = dict(_INNER_PROMOTION_PAYLOADS(static_value, static_payload, ap_receipt))
    run_manifest = json.loads(payloads["run_manifest"])
    run_manifest["observation_contract"]["accepted_identity"] = (
        evidence._latest_stage_accepted_identity(  # noqa: SLF001
            adapter.PROFILE,
            adapter.PARENT_SOURCE_CONTRACT_ID,
            adapter.OVERLAY_CONTRACT_ID,
        )
    )
    payloads["run_manifest"] = _INNER.canonical(run_manifest)
    static_check = json.loads(payloads["static_check"])
    static_check["run_binding"] = {
        "canonical_manifest_size": len(payloads["run_manifest"]),
        "canonical_manifest_sha256": hashlib.sha256(payloads["run_manifest"]).hexdigest(),
        "verified": True,
    }
    payloads["static_check"] = _INNER.canonical(static_check)
    return payloads


_INNER._promotion_payloads = _promotion_payloads
_P330._promotion_payloads = _promotion_payloads
_defaults = dict(_INNER.build.__kwdefaults__ or {})
_defaults.update(
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
_INNER.build.__kwdefaults__ = _defaults
_P330.build.__kwdefaults__ = _defaults


def verify_manifest(
    value: dict[str, Any],
    payload: bytes,
    *,
    promotion_payloads: dict[str, bytes] | None = None,
) -> None:
    if payload != _INNER.manifest_bytes(value):
        raise PromotionError("P3.39 ready manifest bytes differ")
    private_root = ROOT / "workspace/private"
    try:
        private_root.lstat()
    except OSError as exc:
        raise PromotionError("P3.39 private workspace is unavailable") from exc
    with tempfile.TemporaryDirectory(prefix=".p339-ready-", dir=private_root) as name:
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


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    if main is None:
        raise SystemExit(2)
    raise SystemExit(main())
