#!/usr/bin/env python3
"""Terminal-only closure for the fixed A90 H27 post-rollback incident.

This program never dispatches a candidate, rollback, reboot, or recovery
transition.  It accepts no caller-selected path, run, target, command, or
outcome.  It binds the immutable H27 incident journal, obtains one fresh
read-only V2321 Native health snapshot through the reviewed adapter, publishes
one append-only recovery-closure record, and removes only the exact retained
capability-wide active-run guard.  The consumed H27 candidate guard remains.
"""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Any

import a90_boot_only_f1_minimal_v1 as owner


SCHEMA = "a90-h27-postrollback-reconciliation-v1"
DECISION = "V2321_HEALTHY_EXTERNAL_ROLLBACK_OUTCOME_UNPROVED"
RUN_ID = "a90-h27-f1-20260821-01"
MANIFEST_PATH = (
    owner.REPO_ROOT / "workspace/private/manifests/a90-h27-f1-20260821-01.json"
)
MANIFEST_SHA256 = "16347ca9e6435b8ac9edba3445f3946e8c5f447d1347cd207dfd2598c01e80d8"
CURRENT_REVIEW_PATH = (
    owner.REPO_ROOT
    / "docs/reports/A90_BOOT_ONLY_F1_MINIMAL_POSTROLLBACK_INDEPENDENT_REVIEW_2026-08-21.json"
)
INCIDENT_RECORD_SHA256 = {
    "00-prepared.json": "bf60a5c7c32a70320a79795c4af9aa0d4990e4ee4e82af428cc3ef0569e91b95",
    "10-approved.json": "e4228602391765a3d92832ed2502d110c7c65688c2f3510508a4b4707ab62cee",
    "20-candidate-intent.json": "787a129b2ad38e1a3dec68d053904103af2d79ba90da792a0653ff87bc415a8e",
    "21-candidate-launched.json": "8b88cc204e530b7662a3e4b703b283480e4f3e61214d24f1309d1b0857742894",
    "22-candidate-result.json": "fb9d9d08e5732c2b740dac6672fd97d136ccec4b51298a74d328e94adb546e18",
    "30-rollback-intent.json": "c19c1067b21508ecadc56476198055ed9dd7112a64144a2a7504dd3c9bf05cc0",
    "31-rollback-launched.json": "25d43b16cb25d084401a23a2c3b9a8a6906bb567653f1f336602d7752d81fe57",
    "32-rollback-result.json": "36f3d9e5b13df9846f0b9e93a33b69e44ffb9062ba188ab23db81dcd16d15960",
    "40-terminal.json": "b8ee9cfa3fca9d2c01efec9a407fe3f2f92d77fa19868d0cf0ba08b9fb72a2a5",
}


def _load_incident_manifest() -> tuple[bytes, dict[str, Any]]:
    raw = owner._read_bounded_regular(
        MANIFEST_PATH, "fixed H27 incident manifest", owner.MAX_JSON_BYTES
    )
    if owner.sha256_bytes(raw) != MANIFEST_SHA256:
        raise owner.ContractError("fixed H27 incident manifest bytes changed")
    manifest = owner.validate_manifest(
        owner.parse_canonical(raw, "fixed H27 incident manifest")
    )
    if manifest["runId"] != RUN_ID:
        raise owner.ContractError("fixed H27 incident run ID changed")
    historical = owner._verify_input(
        manifest["qualification"]["review"], "historical H27 qualification review"
    )
    owner.parse_canonical(historical, "historical H27 qualification review")
    return raw, manifest


def _current_manifest(manifest: dict[str, Any]) -> tuple[dict[str, Any], str]:
    raw = owner._read_bounded_regular(
        CURRENT_REVIEW_PATH, "current postrollback review", owner.MAX_JSON_BYTES
    )
    current_sha256 = owner.sha256_bytes(raw)
    rebound = dict(manifest)
    qualification = dict(manifest["qualification"])
    qualification["review"] = {
        "path": str(CURRENT_REVIEW_PATH),
        "size": len(raw),
        "sha256": current_sha256,
    }
    rebound["qualification"] = qualification
    owner._verify_qualification_inputs(rebound)
    return rebound, current_sha256


def _require_incident_records(
    records: dict[str, dict[str, Any]], manifest: dict[str, Any]
) -> None:
    if tuple(records) not in (
        owner.ROLLBACK_PATH,
        owner.POSTROLLBACK_RECOVERY_PATH,
    ):
        raise owner.ContractError("journal is not the fixed H27 rollback terminal")
    if set(INCIDENT_RECORD_SHA256) != set(owner.ROLLBACK_PATH):
        raise owner.ContractError("fixed H27 incident record inventory is invalid")
    for name, expected_sha256 in INCIDENT_RECORD_SHA256.items():
        record = records.get(name)
        if (
            type(record) is not dict
            or owner.sha256_bytes(owner.canonical_json(record)) != expected_sha256
            or record.get("manifestSha256") != MANIFEST_SHA256
        ):
            raise owner.ContractError(f"fixed H27 incident record changed: {name}")
    terminal = records["40-terminal.json"]["payload"]
    if (
        terminal.get("schema") != owner.RESULT_SCHEMA
        or terminal.get("terminal") != "RECOVERY_REQUIRED"
        or terminal.get("reason") != "ROLLBACK_HEALTH_UNPROVED"
        or terminal.get("snapshot") is not None
        or terminal.get("candidateReplay") is not False
    ):
        raise owner.ContractError("fixed H27 incident terminal changed")
    if records["20-candidate-intent.json"]["payload"] != {
        "sha256": manifest["candidate"]["sha256"]
    } or records["30-rollback-intent.json"]["payload"] != {
        "sha256": manifest["rollback"]["sha256"]
    }:
        raise owner.ContractError("fixed H27 incident intent changed")


def _require_recovered_snapshot(
    snapshot: owner.Snapshot,
    manifest: dict[str, Any],
    current_review_sha256: str,
) -> None:
    snapshot.validate()
    if (
        re.fullmatch(
            r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", snapshot.boot_id
        )
        is None
        or snapshot.healthy is not True
        or snapshot.recovery_available is not True
        or snapshot.recovery_evidence_sha256 != current_review_sha256
        or snapshot.fresh_state_observed is not False
        or snapshot.fresh_state_absent is not False
        or snapshot.other_targets_untouched is not True
        or (snapshot.version, snapshot.build)
        != (manifest["rollback"]["version"], manifest["rollback"]["build"])
    ):
        raise owner.ContractError("fresh V2321 recovery snapshot is not exact")


def _payload(
    snapshot: owner.Snapshot, current_review_sha256: str
) -> dict[str, Any]:
    recovered_snapshot = snapshot.payload()
    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "candidateReplay": False,
        "rollbackReplay": False,
        "rollbackOutcome": "UNPROVED_EXTERNAL_CONTINUATION",
        "currentReviewSha256": current_review_sha256,
        "incidentTerminalSha256": INCIDENT_RECORD_SHA256["40-terminal.json"],
        "recoveredSnapshot": recovered_snapshot,
        "recoveredSnapshotSha256": owner.sha256_bytes(
            owner.canonical_json(recovered_snapshot)
        ),
    }


def _validate_payload(
    payload: dict[str, Any],
    manifest: dict[str, Any],
    current_review_sha256: str,
) -> None:
    if type(payload) is not dict or set(payload) != {
        "schema",
        "decision",
        "candidateReplay",
        "rollbackReplay",
        "rollbackOutcome",
        "currentReviewSha256",
        "incidentTerminalSha256",
        "recoveredSnapshot",
        "recoveredSnapshotSha256",
    }:
        raise owner.ContractError("postrollback reconciliation fields mismatch")
    if (
        payload["schema"] != SCHEMA
        or payload["decision"] != DECISION
        or payload["candidateReplay"] is not False
        or payload["rollbackReplay"] is not False
        or payload["rollbackOutcome"] != "UNPROVED_EXTERNAL_CONTINUATION"
        or payload["currentReviewSha256"] != current_review_sha256
        or payload["incidentTerminalSha256"]
        != INCIDENT_RECORD_SHA256["40-terminal.json"]
    ):
        raise owner.ContractError("postrollback reconciliation decision is invalid")
    snapshot = owner._object(
        payload["recoveredSnapshot"],
        {
            "targetEvidenceSha256",
            "bootId",
            "version",
            "build",
            "healthy",
            "recoveryAvailable",
            "recoveryEvidenceSha256",
            "freshStateObserved",
            "freshStateAbsent",
            "otherTargetsUntouched",
            "receiptSha256",
        },
        "recovered V2321 snapshot",
    )
    if (
        owner._sha(
            payload["recoveredSnapshotSha256"], "recovered V2321 snapshot digest"
        )
        != owner.sha256_bytes(owner.canonical_json(snapshot))
    ):
        raise owner.ContractError("recovered V2321 snapshot digest mismatch")
    recovered = owner.Snapshot(
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
    _require_recovered_snapshot(recovered, manifest, current_review_sha256)


class CurrentReviewLease:
    """Keep the reviewed execution closure stable across active-guard removal."""

    def __init__(self, manifest: dict[str, Any], expected_sha256: str) -> None:
        binding = manifest["qualification"]["review"]
        if binding["path"] != str(CURRENT_REVIEW_PATH):
            raise owner.ContractError("current review lease path is not exact")
        before = CURRENT_REVIEW_PATH.lstat()
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.getuid()
            or before.st_gid != os.getgid()
            or before.st_mode & 0o022
            or before.st_size != binding["size"]
        ):
            raise owner.ContractError("current review lease identity is invalid")
        self.before = before
        self.expected_sha256 = expected_sha256
        self.descriptor = os.open(
            CURRENT_REVIEW_PATH,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK,
        )
        try:
            self.check()
        except BaseException:
            os.close(self.descriptor)
            raise

    def check(self) -> None:
        current = os.fstat(self.descriptor)
        pathname = CURRENT_REVIEW_PATH.lstat()
        if (
            (current.st_dev, current.st_ino, current.st_size)
            != (self.before.st_dev, self.before.st_ino, self.before.st_size)
            or (pathname.st_dev, pathname.st_ino, pathname.st_size)
            != (self.before.st_dev, self.before.st_ino, self.before.st_size)
            or owner.sha256_bytes(os.pread(self.descriptor, current.st_size, 0))
            != self.expected_sha256
        ):
            raise owner.ContractError("current review lease drifted during cleanup")

    def close(self) -> None:
        os.close(self.descriptor)


def _release_active_only(
    manifest: dict[str, Any], lease: CurrentReviewLease
) -> None:
    lease.check()
    owner._require_candidate_guard(manifest)
    owner._require_active_guard(manifest)
    lease.check()
    owner._require_candidate_guard(manifest)
    owner._release_active_guard(manifest)
    lease.check()
    owner._require_candidate_guard(manifest)


def reconcile() -> dict[str, Any]:
    raw, manifest = _load_incident_manifest()
    current_manifest, current_sha256 = _current_manifest(manifest)
    owner.ensure_run_root()
    run_directory = owner.RUN_ROOT / RUN_ID
    owner._require_run_path(run_directory, RUN_ID)
    records = owner.read_records(run_directory)
    _require_incident_records(records, manifest)
    lease = CurrentReviewLease(current_manifest, current_sha256)
    try:
        if "41-recovery-closed.json" not in records:
            lease.check()
            owner._require_active_guard(manifest)
            owner._require_candidate_guard(manifest)
            backend = owner._live_backend(current_manifest, "reconcile-postrollback")
            recovered = backend.observe(
                manifest["rollback"],
                manifest["qualification"]["freshState"],
                require_fresh_state=False,
                timeout_sec=manifest["timeouts"]["healthSec"],
            )
            _require_recovered_snapshot(recovered, manifest, current_sha256)
            payload = _payload(recovered, current_sha256)
            _validate_payload(payload, manifest, current_sha256)
            lease.check()
            owner._require_active_guard(manifest)
            owner._require_candidate_guard(manifest)
            owner.publish_record(
                run_directory,
                "41-recovery-closed.json",
                owner._record(
                    "POSTROLLBACK_RECOVERY_RECONCILED",
                    owner.sha256_bytes(raw),
                    payload,
                ),
            )
            _release_active_only(manifest, lease)
        else:
            payload = records["41-recovery-closed.json"]["payload"]
            _validate_payload(payload, manifest, current_sha256)
            owner._require_candidate_guard(manifest)
            active_path, _expected = owner._active_guard(manifest)
            try:
                active_path.lstat()
            except FileNotFoundError:
                pass
            else:
                raise owner.ContractError(
                    "postpublication active-guard cleanup was interrupted; park"
                )
        return payload
    finally:
        lease.close()


def main() -> int:
    print(json.dumps(reconcile(), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except owner.ContractError as exc:
        print(
            f"A90_H27_POSTROLLBACK_RECONCILE_V1 NO_GO: {exc}",
            file=os.sys.stderr,
        )
        raise SystemExit(2) from exc
