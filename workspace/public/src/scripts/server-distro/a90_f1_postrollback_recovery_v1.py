#!/usr/bin/env python3
"""Candidate-neutral, observation-only closure after a consumed rollback."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Protocol


ROOT = Path(__file__).resolve().parents[5]
OWNER_PATH = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
CONTINUATION_PATH = ROOT / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
SCHEMA = "a90-f1-postrollback-recovery-v1"
DECISION = "V2321_HEALTHY_EXTERNAL_ROLLBACK_OUTCOME_UNPROVED"
OUTCOME = "UNPROVED_EXTERNAL_CONTINUATION"
RECORD_NAME = "41-recovery-closed.json"
UUID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
REVIEW_PATH = ROOT / "docs/reports/A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json"
REVIEW_SCHEMA = "a90-f1-postrollback-recovery-independent-review-v1"
CAPABILITY = "A90_F1_POSTROLLBACK_RECOVERY_V1"
SELF_REL = "workspace/public/src/scripts/server-distro/a90_f1_postrollback_recovery_v1.py"
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"


def _load_owner():
    name = "a90_boot_only_f1_minimal_v1"
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(getattr(existing, "__file__", "")).resolve() != OWNER_PATH:
            raise RuntimeError("minimal owner module identity is not exact")
        return existing
    spec = importlib.util.spec_from_file_location(name, OWNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("minimal owner import failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


owner = _load_owner()


def _load_continuation():
    name = "a90_f1_candidate_return_continuation_v1"
    existing = sys.modules.get(name)
    if existing is not None:
        if Path(getattr(existing, "__file__", "")).resolve() != CONTINUATION_PATH:
            raise RuntimeError("candidate-return continuation module identity is not exact")
        return existing
    spec = importlib.util.spec_from_file_location(name, CONTINUATION_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("candidate-return continuation import failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    if Path(module.__file__).resolve() != CONTINUATION_PATH:
        raise RuntimeError("candidate-return continuation path changed")
    return module


def execution_closure_sha256() -> str:
    """Bind owner, continuation validators, and this recovery-only entrypoint."""
    digest = hashlib.sha256()
    digest.update(owner.execution_closure_sha256().encode("ascii"))
    digest.update(b"\0")
    for relative in (SELF_REL, TARGET_CONTRACT_REL):
        raw = (ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
        digest.update(b"\0")
    digest.update(b"continuation-closure\0")
    digest.update(_load_continuation().execution_closure_sha256().encode("ascii"))
    digest.update(b"\0")
    return digest.hexdigest()


def _review_lease() -> tuple[str, str]:
    try:
        raw = owner._read_bounded_regular(
            REVIEW_PATH, "postrollback recovery review", owner.MAX_JSON_BYTES
        )
    except owner.ContractError as exc:
        raise owner.ContractError("postrollback recovery review is unavailable") from exc
    review = owner._object(
        owner.parse_canonical(raw, "postrollback recovery review"),
        {
            "schema", "capability", "verdict", "executionClosureSha256",
            "findings", "contacts", "reviewer", "reviewDate", "liveAuthority",
        },
        "postrollback recovery review",
    )
    findings = owner._object(
        review["findings"], {"high", "medium", "low"}, "recovery review findings"
    )
    contacts = owner._object(
        review["contacts"],
        {"device", "dev", "usb", "network", "workspacePrivate", "otherTargets", "writes"},
        "recovery review contacts",
    )
    closure = execution_closure_sha256()
    if (
        review["schema"] != REVIEW_SCHEMA
        or review["capability"] != CAPABILITY
        or review["verdict"] != "PASS_GO"
        or review["executionClosureSha256"] != closure
        or any(type(findings[key]) is not list or findings[key] for key in findings)
        or any(type(value) is not int or value != 0 for value in contacts.values())
        or type(review["reviewer"]) is not str
        or not review["reviewer"]
        or type(review["reviewDate"]) is not str
        or re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}", review["reviewDate"]) is None
        or review["liveAuthority"] is not False
    ):
        raise owner.ContractError("postrollback recovery review is not current PASS_GO")
    return owner.sha256_bytes(raw), closure


class RecoveryBackend(Protocol):
    def observe(
        self,
        expected: dict[str, Any],
        fresh_state: dict[str, Any],
        *,
        require_fresh_state: bool,
        timeout_sec: int,
    ) -> owner.Snapshot: ...


def _sha(value: Any, label: str) -> str:
    return owner._sha(value, label)


def _directory_entry_present(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise owner.ContractError("active guard presence is uncertain") from exc
    return True


def _recovered_snapshot(
    value: Any, manifest: dict[str, Any], qualification_review_sha: str
) -> owner.Snapshot:
    snapshot = owner._object(
        value,
        {
            "targetEvidenceSha256", "bootId", "version", "build", "healthy",
            "recoveryAvailable", "recoveryEvidenceSha256", "freshStateObserved",
            "freshStateAbsent", "otherTargetsUntouched", "receiptSha256",
        },
        "recovered V2321 snapshot",
    )
    result = owner.Snapshot(
        target_evidence_sha256=snapshot["targetEvidenceSha256"],
        boot_id=snapshot["bootId"],
        version=snapshot["version"],
        build=snapshot["build"],
        healthy=snapshot["healthy"],
        recovery_available=snapshot["recoveryAvailable"],
        recovery_evidence_sha256=snapshot["recoveryEvidenceSha256"],
        fresh_state_observed=snapshot["freshStateObserved"],
        fresh_state_absent=snapshot["freshStateAbsent"],
        other_targets_untouched=snapshot["otherTargetsUntouched"],
        receipt_sha256=snapshot["receiptSha256"],
    )
    result.validate()
    if (
        UUID_RE.fullmatch(result.boot_id) is None
        or result.healthy is not True
        or result.recovery_available is not True
        or result.recovery_evidence_sha256 != qualification_review_sha
        or result.fresh_state_observed is not False
        or result.fresh_state_absent is not False
        or result.other_targets_untouched is not True
        or (result.version, result.build)
        != (manifest["rollback"]["version"], manifest["rollback"]["build"])
    ):
        raise owner.ContractError("fresh V2321 recovery snapshot is not exact")
    return result


def _payload(snapshot: owner.Snapshot, current_review_sha: str) -> dict[str, Any]:
    recovered = snapshot.payload()
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "candidateReplay": False,
        "rollbackReplay": False,
        "rollbackOutcome": OUTCOME,
        "currentReviewSha256": current_review_sha,
        "recoveredSnapshot": recovered,
        "recoveredSnapshotSha256": owner.sha256_bytes(owner.canonical_json(recovered)),
    }


def _validate_payload(
    payload: Any,
    manifest: dict[str, Any],
    qualification_review_sha: str,
    current_review_sha: str,
) -> dict[str, Any]:
    if type(payload) is not dict or set(payload) != {
        "schema", "decision", "candidateReplay", "rollbackReplay", "rollbackOutcome",
        "currentReviewSha256", "recoveredSnapshot", "recoveredSnapshotSha256",
    }:
        raise owner.ContractError("postrollback recovery fields mismatch")
    if (
        payload["schema"] != SCHEMA
        or payload["decision"] != DECISION
        or payload["candidateReplay"] is not False
        or payload["rollbackReplay"] is not False
        or payload["rollbackOutcome"] != OUTCOME
        or payload["currentReviewSha256"] != current_review_sha
        or _sha(payload["recoveredSnapshotSha256"], "recovered snapshot digest")
        != owner.sha256_bytes(owner.canonical_json(payload["recoveredSnapshot"]))
    ):
        raise owner.ContractError("postrollback recovery decision is invalid")
    _recovered_snapshot(
        payload["recoveredSnapshot"], manifest, qualification_review_sha
    )
    return payload


def _continuation_paths() -> tuple[tuple[str, ...], ...]:
    return (
        owner.CANDIDATE_RETURN_RESUME_ROLLBACK_PATH,
        owner.CANDIDATE_RETURN_RESUME_ROLLBACK_PATH + (RECORD_NAME,),
        owner.CANDIDATE_RETURN_ROLLBACK_PATH,
        owner.CANDIDATE_RETURN_ROLLBACK_PATH + (RECORD_NAME,),
    )


def _continuation_context(
    records: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    manifest_sha: str,
    pending_receipt_sha256: str,
):
    continuation = _load_continuation()
    return continuation, continuation.Context(
        raw=b"",
        manifest=manifest,
        run=owner.RUN_ROOT / manifest["runId"],
        manifest_sha256=manifest_sha,
        review_sha256="0" * 64,
        review_identity=(0, 0, 0, 0, 0, 0, 0),
        review_closure_sha256="0" * 64,
        qualification_review_sha256=manifest["qualification"]["review"]["sha256"],
        qualification_review_identity=(0, 0, 0, 0, 0, 0, 0),
        pending_receipt_sha256=pending_receipt_sha256,
        records=records,
    )


def _validate_continuation_records(
    records: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    manifest_sha: str,
    present_path: tuple[str, ...],
) -> None:
    """Validate 23/24/25 and the physical-branch sidecar before rollback use."""
    if not owner._exact_uncertain_candidate_result(
        records.get("22-candidate-result.json")
    ):
        raise owner.ContractError("continuation candidate result is not exact uncertain")
    candidate_payload = records["22-candidate-result.json"]["payload"]
    expected_receipt = candidate_payload["receiptSha256"]
    pending = records.get("23-candidate-return-pending.json")
    if pending is None or not owner._valid_candidate_return_pending(
        pending, expected_receipt
    ):
        raise owner.ContractError("continuation pending receipt join is invalid")
    continuation = _load_continuation()
    intent = owner._object(
        records["24-candidate-return-intent.json"]["payload"],
        {
            "schema", "capability", "approvalSha256", "pendingReceiptSha256",
            "candidateReplay", "physicalSystemReturnAllowed",
            "qualificationReviewSha256",
        },
        "candidate-return intent",
    )
    qualification_sha = manifest["qualification"]["review"]["sha256"]
    approval_sha = owner._sha(
        intent["approvalSha256"], "candidate-return approval digest"
    )
    if (
        intent["schema"] != continuation.INTENT_SCHEMA
        or intent["capability"] != continuation.CAPABILITY
        or intent["pendingReceiptSha256"] != expected_receipt
        or intent["candidateReplay"] is not False
        or intent["physicalSystemReturnAllowed"] is not True
        or intent["qualificationReviewSha256"] != qualification_sha
    ):
        raise owner.ContractError("candidate-return intent binding changed")
    continuation, context = _continuation_context(
        records, manifest, manifest_sha, expected_receipt
    )
    observed_record = records.get("24-candidate-return-observed.json")
    if observed_record is None:
        raise owner.ContractError("candidate-return observed record is missing")
    observed_payload = observed_record.get("payload")
    if type(observed_payload) is not dict or set(observed_payload) != {
        "schema", "state", "otherTargetsUntouched", "singleSamsungInventorySha256",
        "candidateSnapshot", "twrpIdentity", "attribution",
        "physicalActionRequired", "candidateReplay",
    }:
        raise owner.ContractError("candidate-return observed record is not exact")
    state = observed_payload.get("state")
    if observed_payload["schema"] != continuation.OBSERVED_SCHEMA:
        raise owner.ContractError("candidate-return observed schema changed")
    continuation._validate_observation(
        {key: observed_payload[key] for key in (
            "state", "otherTargetsUntouched", "singleSamsungInventorySha256",
            "candidateSnapshot", "twrpIdentity", "attribution",
        )},
        manifest,
        after_physical=False,
    )
    if (
        observed_payload["candidateReplay"] is not False
        or type(observed_payload["physicalActionRequired"]) is not bool
        or observed_payload["physicalActionRequired"]
        != (state == continuation.STATE_TWRP_PRESENT)
    ):
        raise owner.ContractError("candidate-return observed binding changed")
    observation_intent = records.get("25-candidate-observation-intent.json")
    has_observation_intent = "25-candidate-observation-intent.json" in present_path
    if not has_observation_intent:
        if observation_intent is not None or state != continuation.STATE_ATTRIBUTABLE_FAILURE:
            raise owner.ContractError("resume rollback branch is not exact")
        sidecar_path = owner.RUN_ROOT / (
            f"{manifest['runId']}-{continuation.UNCERTAIN_EVIDENCE_RESULT_SUFFIX}"
        )
        try:
            sidecar_path.lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise owner.ContractError("uncertain evidence sidecar presence is unknown") from exc
        else:
            raise owner.ContractError("nonphysical continuation carries evidence sidecar")
        return
    payload = owner._object(
        observation_intent["payload"] if observation_intent else None,
        {
            "schema", "capability", "approvalSha256", "physicalActionConfirmed",
            "candidateReplay", "qualificationReviewSha256",
            "uncertainEvidenceIntent",
        },
        "candidate observation intent",
    )
    if (
        payload["schema"] != continuation.OBSERVATION_INTENT_SCHEMA
        or payload["capability"] != continuation.CAPABILITY
        or payload["approvalSha256"] != approval_sha
        or type(payload["physicalActionConfirmed"]) is not bool
        or payload["candidateReplay"] is not False
        or payload["qualificationReviewSha256"] != qualification_sha
    ):
        raise owner.ContractError("candidate observation intent binding changed")
    physical = state == continuation.STATE_TWRP_PRESENT
    if payload["physicalActionConfirmed"] is not physical:
        raise owner.ContractError("candidate observation physical branch changed")
    sidecar_path = owner.RUN_ROOT / (
        f"{manifest['runId']}-{continuation.UNCERTAIN_EVIDENCE_RESULT_SUFFIX}"
    )
    if not physical:
        if state != continuation.STATE_NATIVE_VISIBLE:
            raise owner.ContractError("nonphysical finalize rollback branch is not exact")
        if payload["uncertainEvidenceIntent"] is not None:
            raise owner.ContractError("nonphysical continuation carries evidence intent")
        try:
            sidecar_path.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            raise owner.ContractError(
                "uncertain evidence sidecar presence is unknown"
            ) from exc
        raise owner.ContractError("nonphysical continuation carries evidence sidecar")

    continuation._validate_uncertain_evidence_intent_binding(
        payload["uncertainEvidenceIntent"]
    )
    try:
        sidecar_path.lstat()
    except FileNotFoundError:
        # The post-physical observation may itself have been an attributable
        # failure.  That branch launches the same one-shot rollback without
        # attempting failed-boot capture.  A present sidecar, however, names
        # the TWRP-returned branch and must validate completely below.
        return
    except OSError as exc:
        raise owner.ContractError(
            "uncertain evidence sidecar presence is unknown"
        ) from exc
    observation_sha = owner.sha256_bytes(owner.canonical_json(observation_intent))
    try:
        evidence = continuation._load_uncertain_evidence_result(
            context, observation_sha
        )
    except Exception as exc:
        raise owner.ContractError(
            "uncertain evidence sidecar binding is invalid"
        ) from exc
    if evidence.quiescent is not True:
        raise owner.ContractError("uncertain evidence sidecar is not quiescent")


def _require_prefix(records: dict[str, dict[str, Any]], manifest: dict[str, Any], manifest_sha: str) -> None:
    allowed_paths = (
        owner.ROLLBACK_PATH,
        owner.POSTROLLBACK_RECOVERY_PATH,
        owner.ROLLBACK_WITH_FAILED_BOOT_EVIDENCE_PATH,
        owner.POSTROLLBACK_RECOVERY_WITH_FAILED_BOOT_EVIDENCE_PATH,
        *_continuation_paths(),
    )
    present_path = tuple(records)
    if present_path not in allowed_paths:
        raise owner.ContractError("journal is not a consumed rollback prefix")
    evidence_path = present_path in (
        owner.ROLLBACK_WITH_FAILED_BOOT_EVIDENCE_PATH,
        owner.POSTROLLBACK_RECOVERY_WITH_FAILED_BOOT_EVIDENCE_PATH,
    )
    continuation_path = present_path in _continuation_paths()
    for name in present_path:
        record = records[name]
        if record["manifestSha256"] != manifest_sha:
            raise owner.ContractError("rollback journal manifest binding changed")
    if evidence_path:
        owner.validate_failed_boot_evidence_intent_payload(
            records["26-failed-boot-evidence-intent.json"]["payload"]
        )
        owner.validate_failed_boot_evidence_payload(
            records["27-failed-boot-evidence-result.json"]["payload"]
        )
    if continuation_path:
        _validate_continuation_records(records, manifest, manifest_sha, present_path)
    prepared = owner._load_prepared(records, manifest_sha, manifest["runId"])
    for role in ("candidate", "rollback"):
        checkpoint = owner._object(
            prepared[role],
            {"role", "path", "dev", "ino", "mode", "uid", "gid", "nlink", "size", "sha256"},
            f"prepared {role} checkpoint",
        )
        if (
            checkpoint["role"] != role
            or checkpoint["path"] != manifest[role]["path"]
            or checkpoint["size"] != manifest[role]["size"]
            or checkpoint["sha256"] != manifest[role]["sha256"]
            or any(
                type(checkpoint[key]) is not int
                for key in ("dev", "ino", "mode", "uid", "gid", "nlink", "size")
            )
            or checkpoint["nlink"] != 1
        ):
            raise owner.ContractError(f"prepared {role} checkpoint changed")
    snapshot = owner._prepared_snapshot_binding(prepared["snapshot"])
    prepared_snapshot = owner.Snapshot(
        target_evidence_sha256=snapshot["targetEvidenceSha256"],
        boot_id=snapshot["bootId"],
        version=snapshot["version"],
        build=snapshot["build"],
        healthy=snapshot["healthy"],
        recovery_available=snapshot["recoveryAvailable"],
        recovery_evidence_sha256=snapshot["recoveryEvidenceSha256"],
        fresh_state_observed=snapshot["freshStateObserved"],
        fresh_state_absent=snapshot["freshStateAbsent"],
        other_targets_untouched=snapshot["otherTargetsUntouched"],
        receipt_sha256=prepared["snapshot"]["receiptSha256"],
    )
    prepared_snapshot.validate()
    expected_start = manifest["expectedStart"]
    if (
        prepared_snapshot.healthy is not True
        or prepared_snapshot.recovery_available is not True
        or prepared_snapshot.fresh_state_observed is not True
        or prepared_snapshot.fresh_state_absent is not True
        or prepared_snapshot.other_targets_untouched is not True
        or prepared_snapshot.recovery_evidence_sha256
        != manifest["qualification"]["review"]["sha256"]
        or (prepared_snapshot.version, prepared_snapshot.build)
        != (expected_start["version"], expected_start["build"])
    ):
        raise owner.ContractError("prepared starting snapshot changed")
    approved = owner._object(
        records["10-approved.json"]["payload"], {"approvalSha256"}, "approval record"
    )
    approval_sha = owner._sha(approved["approvalSha256"], "approval digest")
    expected_approval = owner.approval_token(
        manifest_sha, prepared_snapshot, manifest["runId"]
    )
    if approval_sha != owner.sha256_bytes(expected_approval.encode("ascii")):
        raise owner.ContractError("approval record binding changed")
    if records["20-candidate-intent.json"]["payload"] != {"sha256": manifest["candidate"]["sha256"]}:
        raise owner.ContractError("candidate intent binding changed")
    candidate_launch = owner._object(
        records["21-candidate-launched.json"]["payload"],
        {"attempt"},
        "candidate launch",
    )
    if type(candidate_launch["attempt"]) is not int or candidate_launch["attempt"] != 1:
        raise owner.ContractError("candidate launch binding changed")
    candidate_result = owner._object(
        records["22-candidate-result.json"]["payload"],
        {"returncode", "completed", "quiescent", "receiptSha256", "outcome"},
        "candidate result",
    )
    candidate_effect = owner.EffectResult(
        candidate_result["returncode"], candidate_result["completed"],
        candidate_result["quiescent"], candidate_result["receiptSha256"],
        candidate_result["outcome"],
    )
    candidate_effect.validate()
    if candidate_effect.quiescent is not True:
        raise owner.ContractError("candidate helper is not quiescent")
    if evidence_path and (
        candidate_effect.completed is not True
        or candidate_effect.returncode != 0
        or candidate_effect.outcome
        != "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
    ):
        raise owner.ContractError("evidence rollback requires confirmed candidate effect")
    if evidence_path:
        evidence = owner.validate_failed_boot_evidence_payload(
            records["27-failed-boot-evidence-result.json"]["payload"]
        )
        if evidence.quiescent is not True:
            raise owner.ContractError("evidence rollback result is not quiescent")
    if records["30-rollback-intent.json"]["payload"] != {"sha256": manifest["rollback"]["sha256"]}:
        raise owner.ContractError("rollback intent binding changed")
    rollback_launch = owner._object(
        records["31-rollback-launched.json"]["payload"],
        {"attempt"},
        "rollback launch",
    )
    if type(rollback_launch["attempt"]) is not int or rollback_launch["attempt"] != 1:
        raise owner.ContractError("rollback launch binding changed")
    result = owner._object(
        records["32-rollback-result.json"]["payload"],
        {"returncode", "completed", "quiescent", "receiptSha256", "outcome"},
        "rollback result",
    )
    effect = owner.EffectResult(
        result["returncode"], result["completed"], result["quiescent"],
        result["receiptSha256"], result["outcome"],
    )
    effect.validate()
    if effect.quiescent is not True:
        raise owner.ContractError("rollback helper is not quiescent")
    terminal = owner._object(
        records["40-terminal.json"]["payload"],
        {"schema", "terminal", "reason", "snapshot", "candidateReplay", "qualification"},
        "rollback terminal",
    )
    qualification = owner._object(
        terminal["qualification"],
        {"recoveryEvidenceSha256", "hazardId", "hazardAccepted"},
        "rollback terminal qualification",
    )
    if (
        terminal["schema"] != owner.RESULT_SCHEMA
        or terminal["terminal"] != "RECOVERY_REQUIRED"
        or terminal["reason"] != "ROLLBACK_HEALTH_UNPROVED"
        or terminal["candidateReplay"] is not False
        or qualification["recoveryEvidenceSha256"] != manifest["qualification"]["review"]["sha256"]
        or qualification["hazardId"] != manifest["qualification"]["hazard"]["id"]
        or qualification["hazardAccepted"] is not True
    ):
        raise owner.ContractError("rollback terminal is not recovery-required")


def reconcile(manifest_path: Path, backend: RecoveryBackend | None = None) -> dict[str, Any]:
    raw, manifest = owner.load_manifest(manifest_path)
    current_review_sha, review_closure = _review_lease()
    manifest_sha = owner.sha256_bytes(raw)
    qualification_review_sha = manifest["qualification"]["review"]["sha256"]
    historical_review = owner._verify_input(
        manifest["qualification"]["review"], "historical qualification review"
    )
    if owner.sha256_bytes(historical_review) != qualification_review_sha:
        raise owner.ContractError("historical qualification review binding changed")
    owner.ensure_run_root()
    run = owner.RUN_ROOT / manifest["runId"]
    owner._require_run_path(run, manifest["runId"])
    records = owner.read_records(run)
    _require_prefix(records, manifest, manifest_sha)
    if RECORD_NAME in records:
        payload = _validate_payload(
            records[RECORD_NAME]["payload"], manifest,
            qualification_review_sha, current_review_sha,
        )
        owner._require_candidate_guard(manifest)
        active_path, _ = owner._active_guard(manifest)
        if _directory_entry_present(active_path):
            if _review_lease() != (current_review_sha, review_closure):
                raise owner.ContractError("postrollback recovery review lease changed")
            owner._require_active_guard(manifest)
            owner._release_active_guard(manifest)
            owner._require_candidate_guard(manifest)
        return payload
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    if backend is None:
        backend = owner._live_backend(manifest, "postrollback-recovery")
    try:
        if _review_lease() != (current_review_sha, review_closure):
            raise owner.ContractError("postrollback recovery review lease changed")
        owner._require_active_guard(manifest)
        owner._require_candidate_guard(manifest)
        snapshot = backend.observe(
            manifest["rollback"], manifest["qualification"]["freshState"],
            require_fresh_state=False, timeout_sec=manifest["timeouts"]["healthSec"],
        )
        if _review_lease() != (current_review_sha, review_closure):
            raise owner.ContractError("postrollback recovery review lease changed")
        snapshot = _recovered_snapshot(
            snapshot.payload(), manifest, qualification_review_sha
        )
    except Exception as exc:
        raise owner.ContractError("postrollback recovery observation was not proved") from exc
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    payload = _validate_payload(
        _payload(snapshot, current_review_sha), manifest,
        qualification_review_sha, current_review_sha,
    )
    record = owner._record("POSTROLLBACK_RECOVERY_RECONCILED", manifest_sha, payload)
    record_raw = owner.canonical_json(record)
    owner.publish_record(run, RECORD_NAME, record)
    owner._readback_published_record(run, RECORD_NAME, record_raw, manifest_sha)
    if _review_lease() != (current_review_sha, review_closure):
        raise owner.ContractError("postrollback recovery review lease changed")
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(reconcile(args.manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except owner.ContractError as exc:
        print(f"A90_F1_POSTROLLBACK_RECOVERY_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
