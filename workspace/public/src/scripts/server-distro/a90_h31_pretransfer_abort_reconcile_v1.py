#!/usr/bin/env python3
"""One-shot, host-owned reconciliation for the fixed A90 H31 park.

The H31 candidate returned the structured ``PRE_WRITE_FAILURE`` receipt after
the rollback intent/launch records were durable, but before the rollback
helper was dispatched.  This module accepts only that immutable prefix and
the fixed public log hashes.  It performs one existing ACM-scoped V2321
observation, publishes the already allowlisted ``41`` record, and releases
only the active-run guard.  It has no candidate/rollback helper, ADB,
reboot, recovery, partition, or caller-selected input surface.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

import a90_boot_only_f1_adapter_v1 as adapter
import a90_boot_only_f1_minimal_v1 as owner


SCHEMA = "a90-h31-pretransfer-abort-reconciliation-v1"
DECISION = "PRETRANSFER_ABORTED_NO_BOOT_WRITE"
RUN_ID = "a90-h31-f1-20260822-01"
MANIFEST_PATH = (
    owner.REPO_ROOT / "workspace/private/manifests" / f"{RUN_ID}.json"
)
MANIFEST_SHA256 = (
    "43d64441984d17f65e1c9b1a4f512ffec30eb83ea2871acbd8693ceee5427253"
)

# A named placeholder is kept as a fail-closed guard for any future evidence
# pin.  No placeholder is accepted by the reconciler.
UNSET_SHA256 = "UNSET"
REVIEW_PATH = (
    owner.REPO_ROOT
    / "docs/reports/A90_H31_PRETRANSFER_ABORT_CURRENT_REVIEW.json"
)
REVIEW_SCHEMA = "a90-h31-pretransfer-abort-independent-review-v1"
CAPABILITY = "A90_H31_PRETRANSFER_ABORT_RECONCILE_V1"
SELF_REL = (
    "workspace/public/src/scripts/server-distro/"
    "a90_h31_pretransfer_abort_reconcile_v1.py"
)
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"

CANDIDATE = {
    "version": "0.11.198",
    "build": "phase3-minimal-h31-stock-rebuild-1007-cfp",
    "size": 58_372_096,
    "sha256": "5ad0fe043e39482163d10b1870f79c85780c12642bc04d9ee65d3eee8dd323f9",
}
ROLLBACK = {
    "version": owner.V2321_ROLLBACK_VERSION,
    "build": owner.V2321_ROLLBACK_BUILD,
    "size": owner.V2321_ROLLBACK_SIZE,
    "sha256": owner.V2321_ROLLBACK_SHA256,
}
CANDIDATE_RECEIPT_SHA256 = (
    "7aee3a03496abfeca3404c58a25f21a9e41817f8940f44facdace911ef68a69d"
)
RECORD_HASHES = {
    "00-prepared.json": "1de52e96760378f826e6aac212ca1ea09e7506d09264d8950ada347136dde1e0",
    "10-approved.json": "b9c021940ab10df4a9a61e29f48f67c04b329b409f842b4ae51ae733b6a2e462",
    "20-candidate-intent.json": "eb2582a941d39c43f31bdd3ce308c899caad2870979808b93fa6f1ec4a36898d",
    "21-candidate-launched.json": "3d8a699a4242c06e3f713804f79389170eb3e3ce6114d593fc6da228da65ab52",
    "22-candidate-result.json": "414cf6ab3083d7e86853840caae3df952ab1a1c5813d93b6ffd0b54ff1669604",
    "30-rollback-intent.json": "3a454fa9904a0b801449a3e6ecf33cc79700f1db3a091116dfef22ecda0d2656",
    "31-rollback-launched.json": "42a2bf6f0e732bcf11e67df7b59b34047f92c119eb8d5b2fa2c3d8f6078caba7",
}

# These are the only logs from the consumed execute attempt.  The two final
# zero-Samsung inventories are evidence of re-enumeration, not authority.
# In particular, no ``flash-rollback`` log is allowlisted.
LOG_HASHES = {
    "001-usb-inventory.stdout": "587fc4641b0f73fea5fd0302bce34aff26b64ab3e43df633839f978f6842aa8d",
    "001-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "fc481bedc17242e7f2f8a1a5766b822046bf17a99ad1971a329209505208fb2d",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-boot-id-start.stdout": "3520040d5eef520614d08bee4bd4479e7df572b523a0588116306c73365ac234",
    "003-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "004-version.stdout": "0a01d6b63150098716a1c1b6ec323ee8e039c4299201d1417e595fa12af4ca8d",
    "004-version.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "005-selftest.stdout": "cf248dafbab744b7207dde0e92aa53742112c50313223a868750de35ecbc7d01",
    "005-selftest.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "006-status.stdout": "d495f31d2634ef8af930d48e3162a7a76f9292cf05c870400935ab2155b0a5ab",
    "006-status.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "007-boot-id-final.stdout": "c85caad633089691f07a0e7eb619169a12b9ff25635a451e6e38af7695b4784c",
    "007-boot-id-final.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "008-fresh-enable-path.stdout": "6754b802ad2252fc0f307e8973b5a3d0e101f4ab7553352694f4a9ee95b55c65",
    "008-fresh-enable-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "009-fresh-latch-path.stdout": "785676beaebd99906aa5396d13141f603380c12147a037e53e9656cf232e054b",
    "009-fresh-latch-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "010-effect-usb-inventory.stdout": "587fc4641b0f73fea5fd0302bce34aff26b64ab3e43df633839f978f6842aa8d",
    "010-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "011-flash-candidate.stdout": "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24",
    "011-flash-candidate.stderr": "636fe8aa08efc1beb278a950901f7fc2f1a57537c214fc809967aabb614197ab",
    "012-usb-inventory.stdout": "61c43915e41c839b44df23b47eff399a3ff4f1048a65db5f0995271f1d5f05a3",
    "012-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "013-effect-usb-inventory.stdout": "61c43915e41c839b44df23b47eff399a3ff4f1048a65db5f0995271f1d5f05a3",
    "013-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
LOG_DIRECTORY = owner.RUN_ROOT / f"{RUN_ID}-execute-1-logs"
CANDIDATE_STDOUT = LOG_DIRECTORY / "011-flash-candidate.stdout"
CANDIDATE_STDERR = LOG_DIRECTORY / "011-flash-candidate.stderr"
MAX_DURATION_MS = 900_000
H31_JOURNAL_PATH = owner.H31_PRETRANSFER_ABORT_PATH


class ContractError(RuntimeError):
    """Raised when the fixed H31 incident cannot be proved."""


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    digest.update(owner.execution_closure_sha256().encode("ascii"))
    digest.update(b"\0")
    for relative in (SELF_REL, TARGET_CONTRACT_REL):
        raw = (owner.REPO_ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _review_lease() -> tuple[str, str]:
    raw = owner._read_bounded_regular(
        REVIEW_PATH, "H31 pretransfer-abort review", owner.MAX_JSON_BYTES
    )
    value = owner.parse_canonical(raw, "H31 pretransfer-abort review")
    if type(value) is not dict or set(value) != {
        "schema", "capability", "verdict", "executionClosureSha256",
        "findings", "contacts", "reviewer", "reviewDate", "liveAuthority",
    }:
        raise ContractError("H31 reconciliation review fields are not exact")
    findings = value["findings"]
    contacts = value["contacts"]
    closure = execution_closure_sha256()
    if (
        value["schema"] != REVIEW_SCHEMA
        or value["capability"] != CAPABILITY
        or value["verdict"] != "PASS_GO"
        or value["executionClosureSha256"] != closure
        or value["liveAuthority"] is not False
        or type(value["reviewer"]) is not str
        or not value["reviewer"]
        or type(value["reviewDate"]) is not str
        or type(findings) is not dict
        or set(findings) != {"high", "medium", "low"}
        or any(type(findings[key]) is not list or findings[key] for key in findings)
        or type(contacts) is not dict
        or set(contacts) != {
            "device", "dev", "usb", "network", "workspacePrivate",
            "otherTargets", "writes",
        }
        or any(type(item) is not int or item != 0 for item in contacts.values())
    ):
        raise ContractError("H31 reconciliation review is not current PASS_GO")
    return owner.sha256_bytes(raw), closure


def _require_sha(value: Any, label: str) -> str:
    if value == UNSET_SHA256:
        raise ContractError(f"{label} pin is still UNSET")
    if type(value) is not str or owner.SHA256_RE.fullmatch(value) is None:
        raise ContractError(f"{label} is not a SHA-256")
    return value


def _read_log(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} cannot be inspected") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != os.getuid()
        or before.st_gid != os.getgid()
        or before.st_mode & 0o022
        or before.st_size > adapter.MAX_OUTPUT_BYTES
    ):
        raise ContractError(f"{label} identity is not exact")
    descriptor = os.open(
        path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    )
    try:
        current = os.fstat(descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
            or current.st_size != before.st_size
        ):
            raise ContractError(f"{label} changed before read")
        raw = os.pread(descriptor, current.st_size, 0)
        if len(raw) != current.st_size or os.pread(descriptor, 1, current.st_size):
            raise ContractError(f"{label} changed during read")
        return raw
    finally:
        os.close(descriptor)


def _require_private_log_directory() -> None:
    try:
        metadata = LOG_DIRECTORY.lstat()
    except OSError as exc:
        raise ContractError("fixed H31 execute log directory cannot be inspected") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or metadata.st_mode & 0o077
    ):
        raise ContractError("fixed H31 execute log directory is not direct and private")


def _load_manifest() -> tuple[bytes, dict[str, Any]]:
    _require_sha(MANIFEST_SHA256, "fixed H31 manifest")
    raw = owner._read_bounded_regular(
        MANIFEST_PATH, "fixed H31 manifest", owner.MAX_JSON_BYTES
    )
    if owner.sha256_bytes(raw) != MANIFEST_SHA256:
        raise ContractError("fixed H31 manifest bytes changed")
    try:
        manifest = owner.validate_manifest(owner.parse_canonical(raw, "fixed H31 manifest"))
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    if manifest["runId"] != RUN_ID:
        raise ContractError("fixed H31 manifest run ID changed")
    if manifest["candidate"] != {
        "path": manifest["candidate"]["path"],
        **CANDIDATE,
    }:
        raise ContractError("fixed H31 candidate changed")
    if manifest["rollback"] != {
        "path": owner.V2321_ROLLBACK_PATH,
        **ROLLBACK,
    }:
        raise ContractError("fixed H31 rollback changed")
    historical = owner._verify_input(
        manifest["qualification"]["review"], "historical H31 qualification review"
    )
    owner.parse_canonical(historical, "historical H31 qualification review")
    return raw, manifest


def _require_records(
    records: dict[str, dict[str, Any]], manifest_sha256: str, *, closed: bool
) -> None:
    expected_path = H31_JOURNAL_PATH if closed else H31_JOURNAL_PATH[:-1]
    if tuple(records) != expected_path:
        raise ContractError("H31 journal is not the fixed 31 or 31+41 prefix")
    for name, expected in RECORD_HASHES.items():
        _require_sha(expected, f"{name} record")
        record = records.get(name)
        if (
            type(record) is not dict
            or record.get("manifestSha256") != manifest_sha256
            or owner.sha256_bytes(owner.canonical_json(record)) != expected
        ):
            raise ContractError(f"fixed H31 record changed: {name}")
    if records["20-candidate-intent.json"]["payload"] != {
        "sha256": CANDIDATE["sha256"]
    }:
        raise ContractError("H31 candidate intent changed")
    if records["30-rollback-intent.json"]["payload"] != {
        "sha256": ROLLBACK["sha256"]
    }:
        raise ContractError("H31 rollback intent changed")
    if records["21-candidate-launched.json"]["payload"] != {"attempt": 1}:
        raise ContractError("H31 candidate launch changed")
    if records["31-rollback-launched.json"]["payload"] != {"attempt": 1}:
        raise ContractError("H31 rollback launch changed")
    result = records["22-candidate-result.json"]["payload"]
    if result != {
        "returncode": 1,
        "completed": False,
        "quiescent": True,
        "receiptSha256": CANDIDATE_RECEIPT_SHA256,
        "outcome": "PRE_WRITE_FAILURE",
    }:
        raise ContractError("H31 candidate result is not PRE_WRITE_FAILURE")


def _require_logs() -> tuple[bytes, bytes]:
    _require_private_log_directory()
    names = {entry.name for entry in LOG_DIRECTORY.iterdir()}
    if names != set(LOG_HASHES):
        raise ContractError("H31 execute log inventory is not exact")
    values: dict[str, bytes] = {}
    for name, expected in LOG_HASHES.items():
        _require_sha(expected, f"{name} log")
        raw = _read_log(LOG_DIRECTORY / name, name)
        if owner.sha256_bytes(raw) != expected:
            raise ContractError(f"fixed H31 log changed: {name}")
        values[name] = raw
    candidate_stdout = values["011-flash-candidate.stdout"]
    candidate_stderr = values["011-flash-candidate.stderr"]
    try:
        value = adapter._json(candidate_stdout, "H31 candidate receipt")
    except adapter.ContractError as exc:
        raise ContractError(str(exc)) from exc
    if (
        adapter.canonical_json(value) != candidate_stdout
        or adapter._parse_owner_effect_receipt(candidate_stdout) != "PRE_WRITE_FAILURE"
    ):
        raise ContractError("H31 candidate stdout is not the fixed PRE_WRITE_FAILURE receipt")
    return candidate_stdout, candidate_stderr


def bind_effect_receipt(
    *,
    expected_sha256: str,
    argv: tuple[str, ...],
    stdout: bytes,
    stderr: bytes,
    maximum_duration_ms: int,
) -> int:
    """Recover exactly one duration from the immutable owner receipt hash."""
    _require_sha(expected_sha256, "candidate effect receipt")
    if type(maximum_duration_ms) is not int or maximum_duration_ms < 0:
        raise ContractError("effect duration bound is invalid")
    fixed = {
        "argv": list(argv),
        "returncode": 1,
        "quiescent": True,
        "stdoutSha256": owner.sha256_bytes(stdout),
        "stderrSha256": owner.sha256_bytes(stderr),
    }
    match: int | None = None
    for duration_ms in range(maximum_duration_ms + 1):
        receipt = dict(fixed)
        receipt["durationMs"] = duration_ms
        if owner.sha256_bytes(owner.canonical_json(receipt)) == expected_sha256:
            if match is not None:
                raise ContractError("candidate receipt duration is not unique")
            match = duration_ms
    if match is None:
        raise ContractError("candidate logs do not bind the fixed receipt")
    return match


def _validate_candidate_receipt(
    manifest: dict[str, Any], stdout: bytes, stderr: bytes
) -> int:
    serial_sha256 = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    try:
        argv = adapter.fixed_flash_argv(
            manifest["candidate"],
            recovery_serial_sha256=serial_sha256,
            timeout_sec=manifest["timeouts"]["flashSec"],
            rollback=False,
            owner_usb_inventory_sha256=LOG_HASHES["010-effect-usb-inventory.stdout"],
            owner_adb_role=adapter.ADB_ROLE_NATIVE,
        )
    except (KeyError, owner.ContractError, adapter.ContractError) as exc:
        raise ContractError("H31 candidate helper binding is not exact") from exc
    return bind_effect_receipt(
        expected_sha256=CANDIDATE_RECEIPT_SHA256,
        argv=argv,
        stdout=stdout,
        stderr=stderr,
        maximum_duration_ms=MAX_DURATION_MS,
    )


def _validate_snapshot(snapshot: owner.Snapshot, manifest: dict[str, Any]) -> None:
    snapshot.validate()
    expected = manifest["rollback"]
    if (
        snapshot.healthy is not True
        or snapshot.recovery_available is not True
        or snapshot.other_targets_untouched is not True
        or snapshot.fresh_state_observed is not False
        or snapshot.fresh_state_absent is not False
        or (snapshot.version, snapshot.build)
        != (expected["version"], expected["build"])
        or snapshot.recovery_evidence_sha256
        != manifest["qualification"]["review"]["sha256"]
    ):
        raise ContractError("fresh ACM V2321 observation is not exact and healthy")


def _fresh_v2321_observation(manifest: dict[str, Any]) -> owner.Snapshot:
    backend = owner._live_backend(manifest, "reconcile-h31-pretransfer-abort")
    try:
        snapshot = backend.observe(
            manifest["rollback"],
            manifest["qualification"]["freshState"],
            require_fresh_state=False,
            timeout_sec=manifest["timeouts"]["healthSec"],
        )
    except Exception as exc:
        raise ContractError("fresh ACM V2321 observation failed") from exc
    _validate_snapshot(snapshot, manifest)
    return snapshot


def _validate_payload(
    payload: dict[str, Any], manifest: dict[str, Any], current_review_sha256: str
) -> None:
    required = {
        "schema",
        "decision",
        "candidateReplay",
        "rollbackReplay",
        "candidateRetryPermitted",
        "currentReviewSha256",
        "candidate",
        "rollback",
        "recoveredSnapshot",
    }
    if type(payload) is not dict or set(payload) != required:
        raise ContractError("H31 reconciliation payload fields mismatch")
    if (
        payload["schema"] != SCHEMA
        or payload["decision"] != DECISION
        or payload["candidateReplay"] is not False
        or payload["rollbackReplay"] is not False
        or payload["candidateRetryPermitted"] is not False
        or _require_sha(payload["currentReviewSha256"], "current review")
        != current_review_sha256
    ):
        raise ContractError("H31 reconciliation decision is invalid")
    if payload["candidate"] != {
        "receiptSha256": CANDIDATE_RECEIPT_SHA256,
        "outcome": "PRE_WRITE_FAILURE",
        "transferStarted": False,
        "bootWriteStarted": False,
    }:
        raise ContractError("H31 candidate reconciliation is invalid")
    if payload["rollback"] != {
        "intentRecorded": True,
        "launchedRecorded": True,
        "helperDispatched": False,
        "helperLogPresent": False,
        "transferStarted": False,
        "bootWriteStarted": False,
    }:
        raise ContractError("H31 rollback reconciliation is invalid")
    snapshot = payload["recoveredSnapshot"]
    if type(snapshot) is not dict or set(snapshot) != {
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
    }:
        raise ContractError("H31 recovered snapshot is not an object")
    try:
        bound = owner.Snapshot(
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
        _validate_snapshot(bound, manifest)
    except (KeyError, TypeError, owner.ContractError) as exc:
        raise ContractError("H31 recovered snapshot is not exact") from exc


def _release_active_if_present(manifest: dict[str, Any]) -> None:
    owner._require_candidate_guard(manifest)
    path, expected = owner._active_guard(manifest)
    try:
        path.lstat()
    except FileNotFoundError:
        return
    actual = owner._verify_input(
        {"path": str(path), "size": len(expected), "sha256": owner.sha256_bytes(expected)},
        "active run guard",
    )
    if actual != expected:
        raise ContractError("active run guard identity mismatch")
    os.unlink(path)
    owner._fsync_directory(owner.RUN_ROOT)


def reconcile() -> dict[str, Any]:
    raw, manifest = _load_manifest()
    manifest_sha256 = owner.sha256_bytes(raw)
    current_review_sha256, review_closure = _review_lease()
    run_directory = owner.RUN_ROOT / RUN_ID
    owner._require_run_path(run_directory, RUN_ID)
    records = owner.read_records(run_directory)
    if "41-pretransfer-abort.json" in records:
        _require_records(records, manifest_sha256, closed=True)
        _validate_payload(
            records["41-pretransfer-abort.json"]["payload"],
            manifest,
            current_review_sha256,
        )
        if _review_lease() != (current_review_sha256, review_closure):
            raise ContractError("H31 reconciliation review lease changed")
        _release_active_if_present(manifest)
        if _review_lease() != (current_review_sha256, review_closure):
            raise ContractError("H31 reconciliation review lease changed after cleanup")
        owner._require_candidate_guard(manifest)
        return records["41-pretransfer-abort.json"]["payload"]
    _require_records(records, manifest_sha256, closed=False)
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    stdout, stderr = _require_logs()
    _validate_candidate_receipt(manifest, stdout, stderr)
    if _review_lease() != (current_review_sha256, review_closure):
        raise ContractError("H31 reconciliation review lease changed")
    snapshot = _fresh_v2321_observation(manifest)
    if _review_lease() != (current_review_sha256, review_closure):
        raise ContractError("H31 reconciliation review lease changed")
    payload = {
        "schema": SCHEMA,
        "decision": DECISION,
        "candidateReplay": False,
        "rollbackReplay": False,
        "candidateRetryPermitted": False,
        "currentReviewSha256": current_review_sha256,
        "candidate": {
            "receiptSha256": CANDIDATE_RECEIPT_SHA256,
            "outcome": "PRE_WRITE_FAILURE",
            "transferStarted": False,
            "bootWriteStarted": False,
        },
        "rollback": {
            "intentRecorded": True,
            "launchedRecorded": True,
            "helperDispatched": False,
            "helperLogPresent": False,
            "transferStarted": False,
            "bootWriteStarted": False,
        },
        "recoveredSnapshot": snapshot.payload(),
    }
    _validate_payload(payload, manifest, current_review_sha256)
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    record = owner._record("PRETRANSFER_ABORT_RECONCILED", manifest_sha256, payload)
    expected_raw = owner.canonical_json(record)
    owner.publish_record(run_directory, "41-pretransfer-abort.json", record)
    owner._readback_published_record(
        run_directory, "41-pretransfer-abort.json", expected_raw, manifest_sha256
    )
    if _review_lease() != (current_review_sha256, review_closure):
        raise ContractError("H31 reconciliation review lease changed")
    _release_active_if_present(manifest)
    if _review_lease() != (current_review_sha256, review_closure):
        raise ContractError("H31 reconciliation review lease changed after cleanup")
    owner._require_candidate_guard(manifest)
    return payload


def main() -> int:
    print(json.dumps(reconcile(), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, owner.ContractError, adapter.ContractError) as exc:
        print(
            f"A90_H31_PRETRANSFER_ABORT_RECONCILE_V1 NO_GO: {exc}",
            file=os.sys.stderr,
        )
        raise SystemExit(2) from exc
