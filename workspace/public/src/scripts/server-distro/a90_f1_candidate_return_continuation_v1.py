#!/usr/bin/env python3
"""Candidate-neutral H0 state machine for an uncertain A90 F1 return.

The script owns the journal transitions and imports one fixed production
backend. Activation still requires a fresh independent PASS_GO, qualification,
manifest, and attended token.
The backend protocol deliberately exposes no caller-selected command,
endpoint, serial, reboot, or outcome.  Tests use a fake backend and therefore
never contact a device.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_f1_candidate_return_continuation_v1.py"
)
OWNER_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_boot_only_f1_minimal_v1.py"
)
ADAPTER_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_boot_only_f1_adapter_v1.py"
)
BACKEND_PATH = REPO_ROOT / (
    "workspace/public/src/scripts/server-distro/"
    "a90_f1_candidate_return_backend_v1.py"
)
CONTINUATION_REVIEW_PATH = REPO_ROOT / (
    "docs/reports/"
    "A90_F1_CANDIDATE_RETURN_CONTINUATION_INDEPENDENT_REVIEW_2026-08-21.json"
)
CONTINUATION_CLOSURE_RELS = (
    "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py",
    "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py",
    "workspace/public/src/scripts/server-distro/a90_boot_only_f1_adapter_v1.py",
    "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_backend_v1.py",
    "workspace/public/src/scripts/server-distro/a90_serial_redaction_v1.py",
    "workspace/public/src/scripts/revalidation/native_init_flash.py",
    "workspace/public/src/scripts/revalidation/a90_bridge.py",
    "workspace/public/src/scripts/revalidation/a90ctl.py",
    "workspace/public/src/scripts/revalidation/a90_observation_pipeline.py",
    "workspace/public/src/scripts/revalidation/a90_serial_lock.py",
    "workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py",
    "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py",
    "workspace/public/src/scripts/revalidation/_workspace_bootstrap.py",
)

CAPABILITY = "A90_F1_CANDIDATE_RETURN_CONTINUATION_V1"
REVIEW_SCHEMA = "a90-f1-candidate-return-continuation-independent-review-v1"
REVIEW_SCOPE = "A90_F1_CANDIDATE_RETURN_CONTINUATION_AND_NO_REPLAY"
APPROVAL_PREFIX = "A90-F1-CANDIDATE-RETURN-V1-APPROVE:"
INTENT_SCHEMA = "a90-f1-candidate-return-intent-v1"
OBSERVED_SCHEMA = "a90-f1-candidate-return-observed-v1"
OBSERVATION_INTENT_SCHEMA = "a90-f1-candidate-observation-intent-v1"
RETURN_RESULT_SCHEMA = "a90-f1-candidate-return-result-v1"
TWRP_VERSION = "3.7.0_12-0"
TWRP_SCRIPT_SHA256 = (
    "3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07"
)
TWRP_IDENTITY = {
    "version": TWRP_VERSION,
    "scriptPath": "/system/bin/rebootsystem.sh",
    "scriptSize": 89,
    "scriptSha256": TWRP_SCRIPT_SHA256,
    "scriptMode": 493,
    "scriptUid": 0,
    "scriptGid": 0,
    "scriptNlink": 1,
}

STATE_NATIVE_VISIBLE = "NATIVE_CANDIDATE_VISIBLE"
STATE_TWRP_PRESENT = "TWRP_BOUND_PRESENT"
STATE_ATTRIBUTABLE_FAILURE = "ATTRIBUTABLE_FAILURE"
STATE_TWRP_AFTER_PHYSICAL = "TWRP_RETURNED_AFTER_PHYSICAL"
STATE_AMBIGUOUS = "AMBIGUOUS"
STATE_FOREIGN = "FOREIGN_ENDPOINT"
STATE_OBSERVER_FAILURE = "OBSERVER_FAILURE"
STATES = {
    STATE_NATIVE_VISIBLE,
    STATE_TWRP_PRESENT,
    STATE_ATTRIBUTABLE_FAILURE,
    STATE_TWRP_AFTER_PHYSICAL,
    STATE_AMBIGUOUS,
    STATE_FOREIGN,
    STATE_OBSERVER_FAILURE,
}
FAILURE_CODES = {
    "WRONG_CANDIDATE_RESIDENT",
    "EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION",
    "BOUND_TWRP_RETURNED_AFTER_PHYSICAL",
}
CONTINUATION_REVIEW_CONTACT_KEYS = (
    "device",
    "dev",
    "usb",
    "network",
    "workspacePrivate",
    "otherTargets",
    "writes",
)

def _load_exact(name: str, path: Path):
    existing = sys.modules.get(name)
    if existing is not None:
        loaded = getattr(existing, "__file__", None)
        if loaded is None or Path(loaded).resolve() != path:
            raise RuntimeError(f"{name} module identity is not exact")
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"{name} import specification failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    if Path(module.__file__).resolve() != path:
        raise RuntimeError(f"{name} loaded from an unexpected path")
    return module


owner = _load_exact("a90_boot_only_f1_minimal_v1", OWNER_PATH)
adapter = _load_exact("a90_boot_only_f1_adapter_v1", ADAPTER_PATH)
backend_module = _load_exact("a90_f1_candidate_return_backend_v1", BACKEND_PATH)


class ContractError(RuntimeError):
    """Raised on an unbound, malformed, or unprovable continuation."""


class ReviewLeaseDrift(ContractError):
    """Raised when the bound continuation review or source closure changes."""


class CandidateReturnBackend(Protocol):
    """The only observations/effect methods a reviewed backend may provide."""

    def inspect_pending(self, manifest: dict[str, Any]) -> dict[str, Any]: ...

    def observe_after_continuation(
        self, manifest: dict[str, Any], *, physical_action_confirmed: bool
    ) -> dict[str, Any]: ...

    def flash(
        self, artifact: dict[str, Any], *, rollback: bool, timeout_sec: int
    ) -> owner.EffectResult: ...

    def observe(
        self,
        expected: dict[str, Any],
        fresh_state: dict[str, Any],
        *,
        require_fresh_state: bool,
        timeout_sec: int,
    ) -> owner.Snapshot: ...

    def bind_manifest(self, manifest: dict[str, Any]) -> None: ...


TWRP_IDENTITY_COMMAND = (
    "test \"$(twrp --version)\" = '3.7.0_12-0' && "
    "test ! -L /system/bin/rebootsystem.sh && "
    "test \"$(stat -c '%F|%a|%u|%g|%s|%h' /system/bin/rebootsystem.sh)\" = "
    "'regular file|755|0|0|89|1' && "
    "test \"$(sha256sum /system/bin/rebootsystem.sh | cut -d' ' -f1)\" = "
    "'3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07'"
)
# This fixed read-only identity command is shared with the exact production
# backend.  The state-machine tests inject a fake backend; the CLI selects the
# checked backend only after its normal review, qualification, token, and
# attendance gates.


@dataclass(frozen=True)
class ReviewLease:
    identity: tuple[int, int, int, int, int, int, int]
    sha256: str
    closure_sha256: str


@dataclass(frozen=True)
class Context:
    raw: bytes
    manifest: dict[str, Any]
    run: Path
    manifest_sha256: str
    review_sha256: str
    review_identity: tuple[int, int, int, int, int, int, int]
    review_closure_sha256: str
    qualification_review_sha256: str
    qualification_review_identity: tuple[int, int, int, int, int, int, int]
    pending_receipt_sha256: str
    records: dict[str, dict[str, Any]]


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    for relative in sorted(CONTINUATION_CLOSURE_RELS):
        raw = (REPO_ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _canonical(value: Any) -> bytes:
    return owner.canonical_json(value)


def _sha(value: Any, label: str) -> str:
    if type(value) is not str or owner.SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not a SHA-256")
    return value


def _revalidate_review_lease(ctx: Context) -> None:
    _revalidate_qualification_review_lease(ctx)
    current = _load_review()
    _assert_review_lease(current, ctx.review_identity, ctx.review_sha256, ctx.review_closure_sha256)


def _assert_review_lease(
    current: ReviewLease,
    identity: tuple[int, int, int, int, int, int, int],
    sha256: str,
    closure_sha256: str,
) -> None:
    if (
        current.identity != identity
        or current.sha256 != sha256
        or current.closure_sha256 != closure_sha256
    ):
        raise ReviewLeaseDrift("continuation review/closure lease drift")


def _revalidate_qualification_review_lease(ctx: Context) -> None:
    path = Path(ctx.manifest["qualification"]["review"]["path"])
    try:
        owner._verify_qualification_inputs(ctx.manifest)
    except Exception as exc:
        raise ReviewLeaseDrift("qualification review validation drifted") from exc
    identity, sha256 = _capture_file_lease(
        path,
        "qualification review",
        ctx.qualification_review_sha256,
    )
    if (
        identity != ctx.qualification_review_identity
        or sha256 != ctx.qualification_review_sha256
    ):
        raise ReviewLeaseDrift("qualification review lease drift")


def _direct_file_identity(
    path: Path, label: str
) -> tuple[int, int, int, int, int, int, int]:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ReviewLeaseDrift(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o022
        or not 1 <= metadata.st_size <= owner.MAX_JSON_BYTES
    ):
        raise ReviewLeaseDrift(f"{label} path identity mismatch")
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
    )


def _capture_file_lease(
    path: Path, label: str, expected_sha256: str | None = None
) -> tuple[tuple[int, int, int, int, int, int, int], str]:
    identity_before = _direct_file_identity(path, label)
    raw = owner._read_bounded_regular(path, label, owner.MAX_JSON_BYTES)
    identity_after = _direct_file_identity(path, label)
    if identity_before != identity_after:
        raise ReviewLeaseDrift(f"{label} changed during read")
    sha256 = owner.sha256_bytes(raw)
    if expected_sha256 is not None and sha256 != expected_sha256:
        raise ReviewLeaseDrift(f"{label} digest drifted")
    return identity_before, sha256


def _publish_checked(
    ctx: Context, name: str, kind: str, payload: dict[str, Any]
) -> None:
    _revalidate_review_lease(ctx)
    owner.publish_record(ctx.run, name, owner._record(kind, ctx.manifest_sha256, payload))
    _revalidate_review_lease(ctx)


def _read_records_checked(ctx: Context) -> dict[str, dict[str, Any]]:
    _revalidate_review_lease(ctx)
    records = owner.read_records(ctx.run)
    _revalidate_review_lease(ctx)
    return records


def _review_identity() -> tuple[int, int, int, int, int, int, int]:
    return _direct_file_identity(
        CONTINUATION_REVIEW_PATH, "continuation review"
    )


def _load_review() -> ReviewLease:
    closure_before = execution_closure_sha256()
    identity_before = _review_identity()
    raw = owner._read_bounded_regular(
        CONTINUATION_REVIEW_PATH,
        "candidate-return continuation review",
        owner.MAX_JSON_BYTES,
    )
    identity_after = _review_identity()
    closure_after = execution_closure_sha256()
    if identity_before != identity_after:
        raise ContractError("continuation review changed during read")
    if closure_before != closure_after:
        raise ContractError("continuation closure changed during review read")
    value = owner.parse_canonical(raw, "candidate-return continuation review")
    if type(value) is not dict or set(value) != {
        "schema", "capability", "verdict", "scope", "targetProfile",
        "executionClosureSha256", "findings", "contacts", "reviewer",
        "reviewDate", "liveAuthority",
    }:
        raise ContractError("continuation review fields are not exact")
    if (
        value["schema"] != REVIEW_SCHEMA
        or value["capability"] != CAPABILITY
        or value["verdict"] != "PASS_GO"
        or value["scope"] != REVIEW_SCOPE
        or value["targetProfile"] != owner.TARGET_PROFILE
        or value["executionClosureSha256"] != closure_before
        or value["liveAuthority"] is not False
        or type(value["reviewer"]) is not str
        or not value["reviewer"]
        or type(value["reviewDate"]) is not str
    ):
        raise ContractError("continuation review identity or verdict is invalid")
    findings = value["findings"]
    if (
        type(findings) is not dict
        or set(findings) != {"high", "medium", "low"}
        or any(type(findings[key]) is not list or findings[key] for key in findings)
    ):
        raise ContractError("continuation review contains a finding")
    contacts = value["contacts"]
    if (
        type(contacts) is not dict
        or set(contacts) != set(CONTINUATION_REVIEW_CONTACT_KEYS)
        or any(type(contacts[key]) is not int or contacts[key] != 0 for key in contacts)
    ):
        raise ContractError("continuation review contact boundary is invalid")
    return ReviewLease(
        identity=identity_before,
        sha256=owner.sha256_bytes(raw),
        closure_sha256=closure_before,
    )


def review_gate_present() -> bool:
    """Report whether the exact current PASS_GO review is present.

    This is an availability predicate only.  It grants no token, attendance,
    journal, backend, or device authority; callers still load and lease the
    review again before creating the fixed backend.
    """
    try:
        _load_review()
    except (OSError, ContractError, ValueError):
        return False
    return True


def _validate_record_path(records: dict[str, dict[str, Any]]) -> None:
    base = set(owner.SUCCESS_PATH[:-1])
    names = set(records)
    allowed = {
        frozenset(base),
        frozenset(owner.CANDIDATE_RETURN_PENDING_PATH),
        frozenset(owner.CANDIDATE_RETURN_INTENT_PATH),
        frozenset(owner.CANDIDATE_RETURN_RESUME_PATH),
        frozenset(owner.CANDIDATE_RETURN_OBSERVATION_PATH),
        frozenset(owner.CANDIDATE_RETURN_PARK_PATH),
        frozenset(owner.CANDIDATE_RETURN_PASS_PATH),
        frozenset(owner.CANDIDATE_RETURN_RESUME_ROLLBACK_PATH),
        frozenset(owner.CANDIDATE_RETURN_ROLLBACK_PATH),
    }
    if frozenset(names) not in allowed:
        raise ContractError("continuation journal prefix is not exact")


def _require_base_records(records: dict[str, dict[str, Any]]) -> None:
    _validate_record_path(records)
    if not set(owner.SUCCESS_PATH[:-1]).issubset(records):
        raise ContractError("continuation journal is missing the candidate result")
    if "40-terminal.json" in records or "30-rollback-intent.json" in records:
        raise ContractError("continuation journal is already terminal or rolling back")


def _pending_receipt(records: dict[str, dict[str, Any]]) -> str:
    result = records.get("22-candidate-result.json")
    expected = (
        result.get("payload", {}).get("receiptSha256")
        if type(result) is dict
        else None
    )
    if not owner._exact_uncertain_candidate_result(result):
        raise ContractError("candidate result is not the exact uncertain outcome")
    if "23-candidate-return-pending.json" in records:
        if not owner._valid_candidate_return_pending(
            records["23-candidate-return-pending.json"], expected
        ):
            raise ContractError("pending record does not join candidate receipt")
    return _sha(expected, "candidate result receipt")


def _bind_artifacts(manifest: dict[str, Any]) -> None:
    candidate = owner.BoundArtifact.open(manifest["candidate"], "candidate")
    rollback = owner.BoundArtifact.open(manifest["rollback"], "rollback")
    try:
        candidate.checkpoint()
        rollback.checkpoint()
    finally:
        candidate.close()
        rollback.close()


def _load_context(manifest_path: Path) -> Context:
    if not manifest_path.is_absolute() or manifest_path.is_symlink():
        raise ContractError("manifest path is not an absolute direct path")
    raw, manifest = owner.load_manifest(manifest_path)
    owner._verify_qualification_inputs(manifest)
    qualification_review_identity, qualification_review_sha256 = _capture_file_lease(
        Path(manifest["qualification"]["review"]["path"]),
        "qualification review",
        manifest["qualification"]["review"]["sha256"],
    )
    review_lease = _load_review()
    run = owner.RUN_ROOT / manifest["runId"]
    owner._require_run_path(run, manifest["runId"])
    records = owner.read_records(run)
    current_qualification_identity, current_qualification_sha256 = _capture_file_lease(
        Path(manifest["qualification"]["review"]["path"]),
        "qualification review",
        qualification_review_sha256,
    )
    if (
        current_qualification_identity != qualification_review_identity
        or current_qualification_sha256 != qualification_review_sha256
    ):
        raise ReviewLeaseDrift("qualification review changed during entry")
    _assert_review_lease(
        _load_review(),
        review_lease.identity,
        review_lease.sha256,
        review_lease.closure_sha256,
    )
    manifest_sha256 = owner.sha256_bytes(raw)
    if any(
        record.get("manifestSha256") != manifest_sha256
        for record in records.values()
    ):
        raise ContractError("continuation journal does not bind the manifest")
    _require_base_records(records)
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    _bind_artifacts(manifest)
    current_qualification_identity, current_qualification_sha256 = _capture_file_lease(
        Path(manifest["qualification"]["review"]["path"]),
        "qualification review",
        qualification_review_sha256,
    )
    if (
        current_qualification_identity != qualification_review_identity
        or current_qualification_sha256 != qualification_review_sha256
    ):
        raise ReviewLeaseDrift("qualification review changed during entry")
    _assert_review_lease(
        _load_review(),
        review_lease.identity,
        review_lease.sha256,
        review_lease.closure_sha256,
    )
    pending = _pending_receipt(records)
    ctx = Context(
        raw=raw,
        manifest=manifest,
        run=run,
        manifest_sha256=manifest_sha256,
        review_sha256=review_lease.sha256,
        review_identity=review_lease.identity,
        review_closure_sha256=review_lease.closure_sha256,
        qualification_review_sha256=qualification_review_sha256,
        qualification_review_identity=qualification_review_identity,
        pending_receipt_sha256=pending,
        records=records,
    )
    _revalidate_review_lease(ctx)
    return ctx


def _approval_binding(ctx: Context) -> bytes:
    return _canonical(
        {
            "capability": CAPABILITY,
            "manifestSha256": ctx.manifest_sha256,
            "runId": ctx.manifest["runId"],
            "candidateSha256": ctx.manifest["candidate"]["sha256"],
            "rollbackSha256": ctx.manifest["rollback"]["sha256"],
            "pendingReceiptSha256": ctx.pending_receipt_sha256,
            "ownerClosureSha256": owner.execution_closure_sha256(),
            "continuationClosureSha256": execution_closure_sha256(),
            "reviewSha256": ctx.review_sha256,
            "reviewIdentity": list(ctx.review_identity),
            "reviewClosureSha256": ctx.review_closure_sha256,
            "qualificationReviewSha256": ctx.qualification_review_sha256,
        }
    )


def approval_token(ctx: Context) -> str:
    return APPROVAL_PREFIX + owner.sha256_bytes(_approval_binding(ctx))


def _require_approval(ctx: Context, supplied: str) -> None:
    _revalidate_review_lease(ctx)
    if type(supplied) is not str or supplied != approval_token(ctx):
        raise ContractError("candidate-return continuation approval is not exact")


def _validate_return_intent(
    record: dict[str, Any], ctx: Context, approval: str
) -> None:
    payload = record.get("payload")
    if type(payload) is not dict or set(payload) != {
        "schema", "capability", "approvalSha256", "pendingReceiptSha256",
        "candidateReplay", "physicalSystemReturnAllowed",
        "qualificationReviewSha256",
    }:
        raise ContractError("candidate-return intent is not exact")
    if (
        payload["schema"] != INTENT_SCHEMA
        or payload["capability"] != CAPABILITY
        or payload["approvalSha256"] != owner.sha256_bytes(approval.encode("ascii"))
        or payload["pendingReceiptSha256"] != ctx.pending_receipt_sha256
        or payload["candidateReplay"] is not False
        or payload["physicalSystemReturnAllowed"] is not True
        or payload["qualificationReviewSha256"] != ctx.qualification_review_sha256
    ):
        raise ContractError("candidate-return intent binding is invalid")


def _validate_observation_intent(
    record: dict[str, Any], ctx: Context, approval: str, *, physical: bool
) -> None:
    payload = record.get("payload")
    if type(payload) is not dict or set(payload) != {
        "schema", "capability", "approvalSha256", "physicalActionConfirmed",
        "candidateReplay", "qualificationReviewSha256",
    }:
        raise ContractError("candidate observation intent is not exact")
    if (
        payload["schema"] != OBSERVATION_INTENT_SCHEMA
        or payload["capability"] != CAPABILITY
        or payload["approvalSha256"] != owner.sha256_bytes(approval.encode("ascii"))
        or payload["physicalActionConfirmed"] is not physical
        or payload["candidateReplay"] is not False
        or payload["qualificationReviewSha256"] != ctx.qualification_review_sha256
    ):
        raise ContractError("candidate observation intent binding is invalid")


def _publish_pending_from_result(ctx: Context) -> Context:
    if "23-candidate-return-pending.json" in ctx.records:
        return ctx
    result_payload = ctx.records["22-candidate-result.json"]["payload"]
    if not owner._exact_uncertain_candidate_result(
        ctx.records["22-candidate-result.json"]
    ):
        raise ContractError("cannot reconstruct pending from a non-exact result")
    payload = {
        "schema": "a90-f1-candidate-return-pending-v1",
        "terminal": "RECOVERY_REQUIRED",
        "reason": "CANDIDATE_RETURN_PENDING",
        "candidateReplay": False,
        "rollbackIntentPublished": False,
        "effectOutcome": result_payload["outcome"],
        "effectReceiptSha256": result_payload["receiptSha256"],
        "helperQuiescent": result_payload["quiescent"],
    }
    owner._require_active_guard(ctx.manifest)
    owner._require_candidate_guard(ctx.manifest)
    _publish_checked(ctx, "23-candidate-return-pending.json", "CANDIDATE_RETURN_PENDING", payload)
    records = _read_records_checked(ctx)
    return Context(
        raw=ctx.raw,
        manifest=ctx.manifest,
        run=ctx.run,
        manifest_sha256=ctx.manifest_sha256,
        review_sha256=ctx.review_sha256,
        review_identity=ctx.review_identity,
        review_closure_sha256=ctx.review_closure_sha256,
        qualification_review_sha256=ctx.qualification_review_sha256,
        qualification_review_identity=ctx.qualification_review_identity,
        pending_receipt_sha256=ctx.pending_receipt_sha256,
        records=records,
    )


def _snapshot_from_payload(value: Any, manifest: dict[str, Any]) -> owner.Snapshot:
    if type(value) is not dict or set(value) != {
        "targetEvidenceSha256", "bootId", "version", "build", "healthy",
        "recoveryAvailable", "recoveryEvidenceSha256", "freshStateObserved",
        "freshStateAbsent", "otherTargetsUntouched", "receiptSha256",
    }:
        raise ContractError("candidate snapshot fields are not exact")
    snapshot = owner.Snapshot(
        target_evidence_sha256=value["targetEvidenceSha256"],
        boot_id=value["bootId"],
        version=value["version"],
        build=value["build"],
        healthy=value["healthy"],
        recovery_available=value["recoveryAvailable"],
        recovery_evidence_sha256=value["recoveryEvidenceSha256"],
        fresh_state_observed=value["freshStateObserved"],
        fresh_state_absent=value["freshStateAbsent"],
        other_targets_untouched=value["otherTargetsUntouched"],
        receipt_sha256=value["receiptSha256"],
    )
    snapshot.validate()
    if (
        snapshot.version,
        snapshot.build,
    ) != (manifest["candidate"]["version"], manifest["candidate"]["build"]):
        raise ContractError("candidate snapshot identity is not exact")
    if (
        snapshot.recovery_evidence_sha256
        != manifest["qualification"]["review"]["sha256"]
    ):
        raise ContractError("candidate recovery evidence is not the bound review")
    if (
        not snapshot.healthy
        or not snapshot.recovery_available
        or not snapshot.fresh_state_observed
        or not snapshot.fresh_state_absent
        or not snapshot.other_targets_untouched
    ):
        raise ContractError("candidate snapshot health is not exact")
    return snapshot


def _strict_twrp_identity(value: Any) -> bool:
    if type(value) is not dict or set(value) != set(TWRP_IDENTITY):
        return False
    if any(type(key) is not str for key in value):
        return False
    return all(
        type(value[key]) is type(expected) and value[key] == expected
        for key, expected in TWRP_IDENTITY.items()
    )


def _validate_observation(value: Any, manifest: dict[str, Any], *, after_physical: bool) -> dict[str, Any]:
    if type(value) is not dict or set(value) != {
        "state", "otherTargetsUntouched", "singleSamsungInventorySha256",
        "candidateSnapshot", "twrpIdentity", "attribution",
    }:
        raise ContractError("continuation observation fields are not exact")
    state = value["state"]
    if type(state) is not str or state not in STATES:
        raise ContractError("continuation observation state is invalid")
    if type(value["otherTargetsUntouched"]) is not bool:
        raise ContractError("continuation target inventory is invalid")
    baseline = value["singleSamsungInventorySha256"]
    if baseline is not None:
        _sha(baseline, "single-Samsung inventory")
    elif state not in {STATE_AMBIGUOUS, STATE_OBSERVER_FAILURE}:
        raise ContractError("continuation single-Samsung inventory is missing")
    snapshot = value["candidateSnapshot"]
    twrp = value["twrpIdentity"]
    attribution = value["attribution"]
    if attribution is not None and type(attribution) is not str:
        raise ContractError("continuation attribution type is invalid")
    if state == STATE_NATIVE_VISIBLE:
        _snapshot_from_payload(snapshot, manifest)
        if (
            value["otherTargetsUntouched"] is not True
            or baseline is None
            or twrp is not None
            or attribution is not None
        ):
            raise ContractError("native candidate observation carries foreign attribution")
    elif state == STATE_TWRP_PRESENT:
        if (
            value["otherTargetsUntouched"] is not True
            or baseline is None
            or not _strict_twrp_identity(twrp)
            or snapshot is not None
            or attribution is not None
        ):
            raise ContractError("TWRP identity is not exact")
    elif state in {STATE_ATTRIBUTABLE_FAILURE, STATE_TWRP_AFTER_PHYSICAL}:
        if (
            value["otherTargetsUntouched"] is not True
            or baseline is None
            or snapshot is not None
            or twrp is not None
            or attribution not in FAILURE_CODES
        ):
            raise ContractError("failure attribution is not exact")
        if state == STATE_TWRP_AFTER_PHYSICAL and (
            not after_physical or attribution != "BOUND_TWRP_RETURNED_AFTER_PHYSICAL"
        ):
            raise ContractError("TWRP-after-physical attribution is not exact")
        if state == STATE_ATTRIBUTABLE_FAILURE and attribution == "BOUND_TWRP_RETURNED_AFTER_PHYSICAL":
            raise ContractError("TWRP-after-physical attribution is out of phase")
    else:
        if snapshot is not None or twrp is not None or attribution is not None:
            raise ContractError("unresolved observation carries attribution")
    return value


def _observed_payload(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": OBSERVED_SCHEMA,
        "state": observation["state"],
        "otherTargetsUntouched": observation["otherTargetsUntouched"],
        "singleSamsungInventorySha256": observation["singleSamsungInventorySha256"],
        "candidateSnapshot": observation["candidateSnapshot"],
        "twrpIdentity": observation["twrpIdentity"],
        "attribution": observation["attribution"],
        "physicalActionRequired": observation["state"] == STATE_TWRP_PRESENT,
        "candidateReplay": False,
    }


def _validate_observed_record(record: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload")
    if type(payload) is not dict or set(payload) != {
        "schema", "state", "otherTargetsUntouched", "singleSamsungInventorySha256",
        "candidateSnapshot", "twrpIdentity", "attribution",
        "physicalActionRequired", "candidateReplay",
    }:
        raise ContractError("candidate-return observed record is not exact")
    if (
        payload["schema"] != OBSERVED_SCHEMA
        or type(payload["physicalActionRequired"]) is not bool
        or payload["candidateReplay"] is not False
        or payload["physicalActionRequired"]
        != (payload["state"] == STATE_TWRP_PRESENT)
    ):
        raise ContractError("candidate-return observed record is invalid")
    return _validate_observation(
        {key: payload[key] for key in (
            "state", "otherTargetsUntouched", "singleSamsungInventorySha256",
            "candidateSnapshot", "twrpIdentity", "attribution"
        )},
        manifest,
        after_physical=False,
    )


def _publish_observed(ctx: Context, observation: dict[str, Any]) -> None:
    owner._require_active_guard(ctx.manifest)
    owner._require_candidate_guard(ctx.manifest)
    _publish_checked(
        ctx,
        "24-candidate-return-observed.json",
        "CANDIDATE_RETURN_OBSERVED",
        _observed_payload(observation),
    )


def _park(ctx: Context, reason: str) -> dict[str, Any]:
    _revalidate_review_lease(ctx)
    return owner._terminal(
        ctx.run,
        ctx.manifest_sha256,
        "RECOVERY_REQUIRED",
        None,
        reason,
        ctx.manifest,
        continuation_lease_check=lambda: _revalidate_review_lease(ctx),
    )


def _pass(ctx: Context, snapshot: owner.Snapshot, reason: str) -> dict[str, Any]:
    _revalidate_review_lease(ctx)
    return owner._terminal(
        ctx.run,
        ctx.manifest_sha256,
        "PASS_A90_RESIDENT_INSTALLED",
        snapshot,
        reason,
        ctx.manifest,
        continuation_lease_check=lambda: _revalidate_review_lease(ctx),
    )


def _rollback_once(ctx: Context, backend: CandidateReturnBackend) -> dict[str, Any]:
    _revalidate_review_lease(ctx)
    _bind_backend_manifest(backend, ctx.manifest)
    records = _read_records_checked(ctx)
    if "30-rollback-intent.json" in records:
        raise ContractError("continuation rollback was already consumed")
    owner._require_active_guard(ctx.manifest)
    owner._require_candidate_guard(ctx.manifest)
    rollback = owner.BoundArtifact.open(ctx.manifest["rollback"], "rollback")
    try:
        _publish_checked(
            ctx,
            "30-rollback-intent.json",
            "ROLLBACK_INTENT",
            {"sha256": ctx.manifest["rollback"]["sha256"]},
        )
        rollback.checkpoint()
        _publish_checked(
            ctx,
            "31-rollback-launched.json",
            "ROLLBACK_LAUNCHED",
            {"attempt": 1},
        )
        # Match the owner’s pre-effect boundary: 31 is durable, then both
        # permanent guards are revalidated immediately before the sole flash.
        # A missing/drifted guard is a consumed no-replay stop; never recreate
        # either guard or attempt the rollback again.
        owner._require_active_guard(ctx.manifest)
        owner._require_candidate_guard(ctx.manifest)
        _revalidate_review_lease(ctx)
        try:
            result = backend.flash(
                ctx.manifest["rollback"],
                rollback=True,
                timeout_sec=ctx.manifest["timeouts"]["flashSec"],
            )
        except BaseException:
            _revalidate_review_lease(ctx)
            raise
        _revalidate_review_lease(ctx)
        result.validate()
        rollback.checkpoint()
        _publish_checked(
            ctx,
            "32-rollback-result.json",
            "ROLLBACK_RESULT",
            result.payload(),
        )
        if not result.quiescent:
            return _park(ctx, "ROLLBACK_HELPER_NOT_QUIESCENT")
        try:
            _revalidate_review_lease(ctx)
            recovered = backend.observe(
                ctx.manifest["rollback"],
                ctx.manifest["qualification"]["freshState"],
                require_fresh_state=False,
                timeout_sec=ctx.manifest["timeouts"]["healthSec"],
            )
            _revalidate_review_lease(ctx)
            recovered.validate()
        except ReviewLeaseDrift:
            raise
        except Exception:
            recovered = None
        if (
            recovered is not None
            and result.completed
            and result.returncode == 0
            and result.outcome
            == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
            and recovered.healthy
            and recovered.recovery_available
            and recovered.recovery_evidence_sha256
            == ctx.manifest["qualification"]["review"]["sha256"]
            and recovered.other_targets_untouched
            and (recovered.version, recovered.build)
            == (ctx.manifest["rollback"]["version"], ctx.manifest["rollback"]["build"])
        ):
            return owner._terminal(
                ctx.run,
                ctx.manifest_sha256,
                "NO_PROOF_ROLLED_BACK",
                recovered,
                "ROLLBACK_HEALTHY",
                ctx.manifest,
                continuation_lease_check=lambda: _revalidate_review_lease(ctx),
            )
        if (
            recovered is not None
            and recovered.recovery_evidence_sha256
            != ctx.manifest["qualification"]["review"]["sha256"]
        ):
            return _park(ctx, "ROLLBACK_RECOVERY_EVIDENCE_MISMATCH")
        _revalidate_review_lease(ctx)
        return owner._terminal(
            ctx.run,
            ctx.manifest_sha256,
            "RECOVERY_REQUIRED",
            recovered,
            "ROLLBACK_HEALTH_UNPROVED",
            ctx.manifest,
            continuation_lease_check=lambda: _revalidate_review_lease(ctx),
        )
    finally:
        rollback.close()


def prepare(manifest_path: Path) -> str:
    """Host-only token derivation; writes no journal or guard."""
    ctx = _load_context(manifest_path)
    token = approval_token(ctx)
    _revalidate_review_lease(ctx)
    return token


def _bind_backend_manifest(backend: CandidateReturnBackend, manifest: dict[str, Any]) -> None:
    binder = getattr(backend, "bind_manifest", None)
    if binder is not None:
        if not callable(binder):
            raise ContractError("backend manifest binder is not callable")
        binder(manifest)


def _activation_manifest_check(ctx: Context, manifest: dict[str, Any]) -> None:
    if (
        type(manifest) is not dict
        or manifest.get("runId") != ctx.manifest["runId"]
        or owner.sha256_bytes(_canonical(manifest)) != ctx.manifest_sha256
    ):
        raise ReviewLeaseDrift("backend manifest lease drift")


def _activation_guard_check(ctx: Context) -> None:
    owner._require_active_guard(ctx.manifest)
    owner._require_candidate_guard(ctx.manifest)


def _activation_journal_check(ctx: Context) -> dict[str, dict[str, Any]]:
    """Rebind the live journal prefix to this activation before contact.

    ``owner.read_records`` proves canonical envelopes, allowlisted prefix
    ordering, and one shared manifest identity.  The activation must still
    compare that identity to its own manifest and compare the current 22/23
    receipt join to the pending receipt captured when the lease was issued;
    otherwise a complete prefix for another manifest or a substituted
    candidate receipt could pass the owner reader and reach the runner.
    """
    try:
        records = owner.read_records(ctx.run)
    except Exception as exc:
        raise ReviewLeaseDrift("activation journal envelope is not exact") from exc
    if any(
        type(record) is not dict
        or record.get("manifestSha256") != ctx.manifest_sha256
        for record in records.values()
    ):
        raise ReviewLeaseDrift("activation journal manifest binding drift")
    try:
        current_pending = _pending_receipt(records)
    except Exception as exc:
        raise ReviewLeaseDrift("activation candidate receipt join is not exact") from exc
    if current_pending != ctx.pending_receipt_sha256:
        raise ReviewLeaseDrift("activation pending receipt binding drift")
    return records


def _activation_intent_check(
    ctx: Context, approval: str, phase: str
) -> None:
    records = _activation_journal_check(ctx)
    intent = records.get("24-candidate-return-intent.json")
    if intent is None:
        raise ContractError("backend continuation intent is absent")
    _validate_return_intent(intent, ctx, approval)
    if phase == "finalize":
        observed = records.get("24-candidate-return-observed.json")
        observation_intent = records.get("25-candidate-observation-intent.json")
        if observed is None or observation_intent is None:
            raise ContractError("backend observation intent is absent")
        _validate_observed_record(observed, ctx.manifest)
        _validate_observation_intent(
            observation_intent,
            ctx,
            approval,
            physical=_validate_observed_record(observed, ctx.manifest)["state"]
            == STATE_TWRP_PRESENT,
        )


def _activation_inventory_check(
    ctx: Context, expected: str | None, value: str
) -> None:
    records = owner.read_records(ctx.run)
    observed = records.get("24-candidate-return-observed.json")
    if observed is None:
        raise ContractError("backend single-Samsung inventory has no observation record")
    observed_value = _validate_observed_record(observed, ctx.manifest).get(
        "singleSamsungInventorySha256"
    )
    if observed_value != value or (
        expected is not None and observed_value != expected
    ):
        raise ReviewLeaseDrift("backend single-Samsung inventory lease drift")


def _make_backend_activation(
    ctx: Context,
    approval: str,
    *,
    phase: str,
    single_samsung_inventory_sha256: str | None,
):
    return backend_module._issue_activation(
        sentinel=backend_module._ACTIVATION_SENTINEL,
        phase=phase,
        manifest_sha256=ctx.manifest_sha256,
        run_id=ctx.manifest["runId"],
        pending_receipt_sha256=ctx.pending_receipt_sha256,
        approval_sha256=owner.sha256_bytes(approval.encode("ascii")),
        single_samsung_inventory_sha256=single_samsung_inventory_sha256,
        lease_check=lambda: _revalidate_review_lease(ctx),
        guard_check=lambda: _activation_guard_check(ctx),
        intent_check=lambda: _activation_intent_check(ctx, approval, phase),
        manifest_check=lambda manifest: _activation_manifest_check(ctx, manifest),
        inventory_check=lambda value: _activation_inventory_check(
            ctx, single_samsung_inventory_sha256, value
        ),
    )


def _live_backend(
    phase: str,
    ctx: Context,
    approval: str,
    single_samsung_inventory_sha256: str | None = None,
) -> CandidateReturnBackend:
    if not review_gate_present():
        raise ContractError("candidate-return continuation review gate is absent or invalid")
    current_review = _load_review()
    if (
        current_review.sha256 != ctx.review_sha256
        or current_review.identity != ctx.review_identity
        or current_review.closure_sha256 != ctx.review_closure_sha256
    ):
        raise ReviewLeaseDrift("continuation review changed before backend creation")
    activation = _make_backend_activation(
        ctx,
        approval,
        phase=phase,
        single_samsung_inventory_sha256=single_samsung_inventory_sha256,
    )
    return backend_module.create(activation=activation)


def resume(
    manifest_path: Path,
    approval: str,
    backend: CandidateReturnBackend | None,
    *,
    operator_attended: bool,
) -> dict[str, Any]:
    if type(operator_attended) is not bool or not operator_attended:
        raise ContractError("resume requires explicit operator attendance")
    ctx = _load_context(manifest_path)
    _require_approval(ctx, approval)
    if "24-candidate-return-intent.json" in ctx.records:
        raise ContractError("continuation intent already consumed")
    ctx = _publish_pending_from_result(ctx)
    _require_approval(ctx, approval)
    _publish_checked(
        ctx,
        "24-candidate-return-intent.json",
        "CANDIDATE_RETURN_INTENT",
        {
            "schema": INTENT_SCHEMA,
            "capability": CAPABILITY,
            "approvalSha256": owner.sha256_bytes(approval.encode("ascii")),
            "pendingReceiptSha256": ctx.pending_receipt_sha256,
            "candidateReplay": False,
            "physicalSystemReturnAllowed": True,
            "qualificationReviewSha256": ctx.qualification_review_sha256,
        },
    )
    owner._require_active_guard(ctx.manifest)
    owner._require_candidate_guard(ctx.manifest)
    if backend is None:
        backend = _live_backend("resume", ctx, approval)
    _bind_backend_manifest(backend, ctx.manifest)
    try:
        _revalidate_review_lease(ctx)
        raw_observation = backend.inspect_pending(ctx.manifest)
        _revalidate_review_lease(ctx)
        observation = _validate_observation(
            raw_observation, ctx.manifest, after_physical=False
        )
    except ReviewLeaseDrift:
        raise
    except Exception:
        observation = {
            "state": STATE_OBSERVER_FAILURE,
            "otherTargetsUntouched": False,
            "singleSamsungInventorySha256": None,
            "candidateSnapshot": None,
            "twrpIdentity": None,
            "attribution": None,
        }
        _publish_observed(ctx, observation)
        return _park(ctx, "CANDIDATE_RETURN_OBSERVER_UNPROVED")
    _publish_observed(ctx, observation)
    if observation["state"] == STATE_NATIVE_VISIBLE:
        return {
            "schema": RETURN_RESULT_SCHEMA,
            "terminal": "CANDIDATE_NATIVE_VISIBLE_FINALIZE_REQUIRED",
            "physicalActionRequired": False,
            "candidateReplay": False,
        }
    if observation["state"] == STATE_TWRP_PRESENT:
        _revalidate_review_lease(ctx)
        return {
            "schema": RETURN_RESULT_SCHEMA,
            "terminal": "CANDIDATE_RETURN_PHYSICAL_ACTION_REQUIRED",
            "physicalActionRequired": True,
            "physicalInstruction": "Reboot -> System",
            "candidateReplay": False,
        }
    if observation["state"] == STATE_ATTRIBUTABLE_FAILURE:
        return _rollback_once(ctx, backend)
    return _park(ctx, "CANDIDATE_RETURN_UNATTRIBUTED_OR_FOREIGN")


def finalize(
    manifest_path: Path,
    approval: str,
    backend: CandidateReturnBackend | None,
    *,
    operator_attended: bool,
    physical_action_confirmed: bool,
) -> dict[str, Any]:
    if type(operator_attended) is not bool or not operator_attended:
        raise ContractError("finalize requires explicit operator attendance")
    if type(physical_action_confirmed) is not bool:
        raise ContractError("physical confirmation type is invalid")
    ctx = _load_context(manifest_path)
    _require_approval(ctx, approval)
    if set(ctx.records) != set(owner.CANDIDATE_RETURN_RESUME_PATH):
        raise ContractError("finalize requires one consumed return observation")
    _validate_return_intent(
        ctx.records["24-candidate-return-intent.json"], ctx, approval
    )
    observed = _validate_observed_record(
        ctx.records["24-candidate-return-observed.json"], ctx.manifest
    )
    physical_required = observed["state"] == STATE_TWRP_PRESENT
    if physical_action_confirmed != physical_required:
        raise ContractError("physical confirmation does not match the observed branch")
    _publish_checked(
        ctx,
        "25-candidate-observation-intent.json",
        "CANDIDATE_OBSERVATION_INTENT",
        {
            "schema": OBSERVATION_INTENT_SCHEMA,
            "capability": CAPABILITY,
            "approvalSha256": owner.sha256_bytes(approval.encode("ascii")),
            "physicalActionConfirmed": physical_action_confirmed,
            "candidateReplay": False,
            "qualificationReviewSha256": ctx.qualification_review_sha256,
        },
    )
    records = _read_records_checked(ctx)
    _validate_observation_intent(
        records["25-candidate-observation-intent.json"],
        ctx,
        approval,
        physical=physical_action_confirmed,
    )
    owner._require_active_guard(ctx.manifest)
    owner._require_candidate_guard(ctx.manifest)
    if backend is None:
        backend = _live_backend(
            "finalize",
            ctx,
            approval,
            single_samsung_inventory_sha256=observed["singleSamsungInventorySha256"],
        )
    _bind_backend_manifest(backend, ctx.manifest)
    try:
        _revalidate_review_lease(ctx)
        raw_after = backend.observe_after_continuation(
            ctx.manifest,
            physical_action_confirmed=physical_action_confirmed,
        )
        _revalidate_review_lease(ctx)
        after = _validate_observation(
            raw_after, ctx.manifest, after_physical=physical_action_confirmed
        )
    except ReviewLeaseDrift:
        raise
    except Exception:
        return _park(ctx, "CANDIDATE_RETURN_OBSERVER_UNPROVED")
    if after["state"] == STATE_NATIVE_VISIBLE:
        return _pass(
            ctx,
            _snapshot_from_payload(after["candidateSnapshot"], ctx.manifest),
            "CANDIDATE_HEALTHY_AFTER_RETURN_CONTINUATION",
        )
    if after["state"] in {STATE_ATTRIBUTABLE_FAILURE, STATE_TWRP_AFTER_PHYSICAL}:
        return _rollback_once(ctx, backend)
    return _park(ctx, "CANDIDATE_RETURN_UNATTRIBUTED_OR_FOREIGN")


def _assert_launch() -> None:
    if Path(__file__).resolve() != SCRIPT_PATH:
        raise ContractError("continuation script path is not canonical")
    if not sys.argv or Path(sys.argv[0]).resolve() != SCRIPT_PATH:
        raise ContractError("continuation argv0 is not canonical")
    if Path(owner.__file__).resolve() != OWNER_PATH:
        raise ContractError("owner module path is not canonical")
    if Path(adapter.__file__).resolve() != ADAPTER_PATH:
        raise ContractError("adapter module path is not canonical")
    if Path(backend_module.__file__).resolve() != BACKEND_PATH:
        raise ContractError("backend module path is not canonical")
    if sys.modules.get("a90_boot_only_f1_minimal_v1") is not owner:
        raise ContractError("owner module alias is not canonical")
    if sys.modules.get("a90_boot_only_f1_adapter_v1") is not adapter:
        raise ContractError("adapter module alias is not canonical")
    if sys.modules.get("a90_f1_candidate_return_backend_v1") is not backend_module:
        raise ContractError("backend module alias is not canonical")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="action", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("manifest", type=Path)
    resume_parser = sub.add_parser("resume")
    resume_parser.add_argument("manifest", type=Path)
    resume_parser.add_argument("--approval", required=True)
    resume_parser.add_argument("--operator-attended", action="store_true", required=True)
    finalize_parser = sub.add_parser("finalize")
    finalize_parser.add_argument("manifest", type=Path)
    finalize_parser.add_argument("--approval", required=True)
    finalize_parser.add_argument("--operator-attended", action="store_true", required=True)
    finalize_parser.add_argument("--physical-action-confirmed", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    _assert_launch()
    args = parser().parse_args(argv)
    if args.action == "prepare":
        print(json.dumps({"approval": prepare(args.manifest)}, sort_keys=True))
        return 0
    if args.action == "resume":
        if not review_gate_present():
            raise ContractError("resume requires the exact current PASS_GO review")
        result = resume(
            args.manifest,
            args.approval,
            None,
            operator_attended=args.operator_attended,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.action == "finalize":
        if not review_gate_present():
            raise ContractError("finalize requires the exact current PASS_GO review")
        result = finalize(
            args.manifest,
            args.approval,
            None,
            operator_attended=args.operator_attended,
            physical_action_confirmed=args.physical_action_confirmed,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    raise ContractError("unknown continuation action")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"A90_F1_CANDIDATE_RETURN_CONTINUATION_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
