#!/usr/bin/env python3
"""Close the fixed H37 pre-candidate Recovery park after fresh V2321 health."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

import a90_boot_only_f1_adapter_v1 as adapter
import a90_boot_only_f1_minimal_v1 as owner


CAPABILITY = "A90_H37_PRE_CANDIDATE_RECOVERY_PARK_CLOSE_V1"
REVIEW_SCHEMA = "a90-h37-pre-candidate-recovery-park-close-review-v1"
RESULT_SCHEMA = "a90-h37-pre-candidate-recovery-park-close-result-v1"
INTENT_SCHEMA = "a90-h37-pre-candidate-recovery-park-close-observation-intent-v1"
RUN_ID = "a90-h37-f1-20260829-01"
MANIFEST = owner.REPO_ROOT / "workspace/private/manifests/a90-h37-f1-20260829-01.json"
MANIFEST_SHA256 = "c7bee308bdbf6f9088b75b534395193e3b5d0266bf392eff2478d2b15a8a0546"
REVIEW = owner.REPO_ROOT / "docs/reports/A90_H37_PRE_CANDIDATE_RECOVERY_PARK_CLOSE_REVIEW_2026-08-29.json"
SIDE_ROOT = owner.REPO_ROOT / "workspace/private/runs/a90-h37-pre-candidate-recovery-park-close-v1"
RESULT = SIDE_ROOT / "result.json"
LOG_PREFIX = "observe-"
APPROVAL_PREFIX = "A90-H37-PRE-CANDIDATE-PARK-CLOSE-V1-APPROVE:"
SELF_REL = "workspace/public/src/scripts/server-distro/a90_h37_pre_candidate_recovery_park_close_v1.py"
TEST_REL = "tests/test_a90_h37_pre_candidate_recovery_park_close_v1.py"
CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
EXTRA_CLOSURE_RELS: tuple[str, ...] = ()
REQUIRE_INTENT_FOR_RESULT = False
JOURNAL_HASHES = {
    "00-prepared.json": "7a2ff7f71e8058ec5c007be4fde529ce6304ff116bbc07505630552cf5a1d740",
    "10-approved.json": "742ef50ca0c3a5948ec4b1be709630fdbe4f11ed1b26997e5bb6e54c36371002",
    "11-recovery-transition-intent.json": "02ad91306cd2d622611818502ca6c7014f35b76d026aff3e24eb3693c8a14666",
    "13-recovery-transition-parked.json": "87e62f54813303bd602933fb59be9cccadb3ad5653a36286ccd14b3905446288",
}
LOG_HASHES = {
    "001-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "001-usb-inventory.stdout": "5f2f2d57a24bac0f5dc1ec2f387e9ae50183c6af5efdf6514d3cbc41e0ae2527",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "02a36dddd47a943256285fc7f99cfd536ebac74d34cb8be85b47a3a4e03d7806",
    "003-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-boot-id-start.stdout": "516cee887cbcfd8dd62d578c00b70d202aed50ca53ed2ffb99be08bf7f4661af",
    "004-version.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "004-version.stdout": "cd6ce148855742562d499d2eb6160d5f6ee74c9ba7f878e05c6865f655fee248",
    "005-selftest.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "005-selftest.stdout": "bf15a1b18c6a2133e0a613b5f33d11104bbc270a6504ee381fe9fd86c2d7151d",
    "006-status.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "006-status.stdout": "ccc9a7f6190582c68652c2536086ff3ad04ced36c83df9ab7664c47d87adcb39",
    "007-boot-id-final.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "007-boot-id-final.stdout": "d2d979e919d8f3500f13793ad9dd28815f2909cc804b780e13efe517d57e99b8",
    "008-fresh-enable-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "008-fresh-enable-path.stdout": "776461dc23f2defcddfe357534ccbf2d244fb12fed9cc35620b19b8031554880",
    "009-fresh-latch-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "009-fresh-latch-path.stdout": "311192ffd8d0664e687dd7697f7fafd73a9ec691331f6e40c8738372f51f40e0",
    "010-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "010-effect-usb-inventory.stdout": "5f2f2d57a24bac0f5dc1ec2f387e9ae50183c6af5efdf6514d3cbc41e0ae2527",
    "011-native-to-recovery.stderr": "28c12916c7e85c78a906a546f8c1196a047d3dd0bc65fc32439545a771ca27bf",
    "011-native-to-recovery.stdout": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


class CloseError(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixed_file(path: Path, label: str, *, maximum: int = 1 << 20) -> bytes:
    before = path.lstat()
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_uid != os.getuid()
        or before.st_gid != os.getgid()
        or stat.S_IMODE(before.st_mode) != 0o600
        or not 0 <= before.st_size <= maximum
    ):
        raise CloseError(f"{label} identity is not exact")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        current = os.fstat(descriptor)
        raw = os.pread(descriptor, current.st_size, 0)
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_nlink != 1
            or current.st_uid != os.getuid()
            or current.st_gid != os.getgid()
            or stat.S_IMODE(current.st_mode) != 0o600
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
            or len(raw) != current.st_size
            or os.pread(descriptor, 1, current.st_size)
        ):
            raise CloseError(f"{label} changed during read")
        return raw
    finally:
        os.close(descriptor)


def closure_sha256() -> str:
    value = hashlib.sha256()
    value.update(owner.execution_closure_sha256().encode() + b"\0")
    for rel in (SELF_REL, TEST_REL, CONTRACT_REL, *EXTRA_CLOSURE_RELS):
        raw = (owner.REPO_ROOT / rel).read_bytes()
        value.update(rel.encode() + b"\0" + str(len(raw)).encode() + b"\0" + hashlib.sha256(raw).hexdigest().encode() + b"\0")
    return value.hexdigest()


def review_lease() -> tuple[bytes, str]:
    raw = owner._read_bounded_regular(REVIEW, "H37 park-close review", owner.MAX_JSON_BYTES)
    value = owner.parse_canonical(raw, "H37 park-close review")
    keys = {"schema", "capability", "verdict", "executionClosureSha256", "manifestSha256", "journalHashes", "logHashes", "findings", "contacts", "reviewer", "reviewDate", "liveAuthority"}
    if type(value) is not dict or set(value) != keys or value["schema"] != REVIEW_SCHEMA or value["capability"] != CAPABILITY or value["verdict"] != "PASS_GO" or value["executionClosureSha256"] != closure_sha256() or value["manifestSha256"] != MANIFEST_SHA256 or value["journalHashes"] != JOURNAL_HASHES or value["logHashes"] != LOG_HASHES or value["liveAuthority"] is not False:
        raise CloseError("review is not exact PASS_GO")
    findings = value["findings"]
    contacts = value["contacts"]
    if (
        type(findings) is not dict
        or set(findings) != {"high", "medium", "low"}
        or any(type(findings[key]) is not list or findings[key] for key in findings)
        or type(contacts) is not dict
        or set(contacts) != {"device", "dev", "usb", "network", "workspacePrivate", "otherTargets", "writes"}
        or any(type(item) is not int or item != 0 for item in contacts.values())
        or type(value["reviewer"]) is not str
        or not value["reviewer"]
        or value["reviewDate"] != "2026-08-29"
    ):
        raise CloseError("review contains findings or contacts")
    return raw, hashlib.sha256(raw).hexdigest()


def fixed_inputs(*, allow_released: bool = False) -> tuple[bytes, dict]:
    raw, manifest = owner.load_manifest(MANIFEST)
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256 or manifest["runId"] != RUN_ID:
        raise CloseError("fixed manifest changed")
    run = owner.RUN_ROOT / RUN_ID
    if set(path.name for path in run.iterdir()) != set(JOURNAL_HASHES):
        raise CloseError("journal is not exact 11-to-13 park")
    for name, expected in JOURNAL_HASHES.items():
        if hashlib.sha256(fixed_file(run / name, f"journal {name}")).hexdigest() != expected:
            raise CloseError(f"journal changed: {name}")
    logs = owner.RUN_ROOT / f"{RUN_ID}-execute-1-logs"
    names = {path.name for path in logs.iterdir()}
    if names != set(LOG_HASHES) | {".adb-home"}:
        raise CloseError("execute log inventory changed")
    for name, expected in LOG_HASHES.items():
        if hashlib.sha256(fixed_file(logs / name, f"execute log {name}", maximum=adapter.MAX_OUTPUT_BYTES)).hexdigest() != expected:
            raise CloseError(f"execute log changed: {name}")
    active, _ = owner._active_guard(manifest)
    if active.exists():
        owner._require_active_guard(manifest)
    elif not allow_released:
        raise CloseError("active guard is absent before closure")
    owner._require_candidate_guard_absent(manifest)
    return raw, manifest


def token() -> str:
    manifest_raw, _ = fixed_inputs()
    review_raw, _ = review_lease()
    return APPROVAL_PREFIX + hashlib.sha256(manifest_raw).hexdigest() + ":" + hashlib.sha256(review_raw).hexdigest() + ":" + closure_sha256()


def publish(payload: dict) -> None:
    require_side_root()
    raw = owner.canonical_json(payload)
    fd = os.open(RESULT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    directory = os.open(SIDE_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def observation_intent_path() -> Path:
    return SIDE_ROOT / "observation-intent.json"


def observation_intent_value(
    manifest_sha: str, review_sha: str, approval: str
) -> dict:
    return {
        "schema": INTENT_SCHEMA,
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": manifest_sha,
        "currentReviewSha256": review_sha,
        "executionClosureSha256": closure_sha256(),
        "approvalSha256": hashlib.sha256(approval.encode("ascii")).hexdigest(),
        "healthObservationOnly": True,
        "candidateReplay": False,
        "recoveryTransitionReplay": False,
    }


def publish_observation_intent(payload: dict) -> None:
    require_side_root()
    raw = owner.canonical_json(payload)
    path = observation_intent_path()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        if os.write(fd, raw) != len(raw):
            raise CloseError("observation intent short write")
        os.fsync(fd)
    finally:
        os.close(fd)
    owner._fsync_directory(SIDE_ROOT)


def read_observation_intent(
    manifest_sha: str, review_sha: str, approval: str
) -> dict:
    raw = fixed_file(observation_intent_path(), "park-close observation intent")
    value = owner.parse_canonical(raw, "park-close observation intent")
    expected = observation_intent_value(manifest_sha, review_sha, approval)
    if value != expected or raw != owner.canonical_json(expected):
        raise CloseError("observation intent is not exact")
    return value


def observation_intent_sha256(
    manifest_sha: str, review_sha: str, approval: str
) -> str:
    value = read_observation_intent(manifest_sha, review_sha, approval)
    return hashlib.sha256(owner.canonical_json(value)).hexdigest()


def require_side_root() -> None:
    if not SIDE_ROOT.exists():
        SIDE_ROOT.mkdir(mode=0o700, parents=True)
    metadata = SIDE_ROOT.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise CloseError("side root identity is not exact")


def read_result(
    manifest_sha: str, review_sha: str, recovery_evidence_sha: str,
    observation_intent_sha: str | None = None,
) -> dict:
    raw = fixed_file(RESULT, "park-close result")
    value = owner.parse_canonical(raw, "park-close result")
    keys = {"schema", "decision", "runId", "manifestSha256", "currentReviewSha256", "candidateGuardPublished", "candidateIntentPublished", "candidateHelperLaunched", "candidateBytesTransferred", "rollbackBytesTransferred", "candidateReplay", "recoveryTransitionReplay", "snapshot"}
    if REQUIRE_INTENT_FOR_RESULT:
        keys.add("observationIntentSha256")
    snapshot_keys = {"targetEvidenceSha256", "bootId", "version", "build", "healthy", "recoveryAvailable", "recoveryEvidenceSha256", "freshStateObserved", "freshStateAbsent", "otherTargetsUntouched", "receiptSha256"}
    snapshot = value.get("snapshot") if type(value) is dict else None
    if (
        type(value) is not dict
        or set(value) != keys
        or value.get("schema") != RESULT_SCHEMA
        or value.get("decision") != "PRE_CANDIDATE_RECOVERY_PARK_CLOSED_NO_CANDIDATE"
        or value.get("runId") != RUN_ID
        or value.get("manifestSha256") != manifest_sha
        or value.get("currentReviewSha256") != review_sha
        or (
            REQUIRE_INTENT_FOR_RESULT
            and (
                type(observation_intent_sha) is not str
                or owner.SHA256_RE.fullmatch(observation_intent_sha) is None
                or value.get("observationIntentSha256") != observation_intent_sha
            )
        )
        or value.get("candidateGuardPublished") is not False
        or value.get("candidateIntentPublished") is not False
        or value.get("candidateHelperLaunched") is not False
        or type(value.get("candidateBytesTransferred")) is not int
        or value.get("candidateBytesTransferred") != 0
        or type(value.get("rollbackBytesTransferred")) is not int
        or value.get("rollbackBytesTransferred") != 0
        or value.get("candidateReplay") is not False
        or value.get("recoveryTransitionReplay") is not False
        or type(snapshot) is not dict
        or set(snapshot) != snapshot_keys
        or snapshot.get("version") != owner.V2321_ROLLBACK_VERSION
        or snapshot.get("build") != owner.V2321_ROLLBACK_BUILD
        or snapshot.get("healthy") is not True
        or snapshot.get("recoveryAvailable") is not True
        or snapshot.get("freshStateObserved") is not False
        or snapshot.get("freshStateAbsent") is not False
        or snapshot.get("otherTargetsUntouched") is not True
        or type(snapshot.get("bootId")) is not str
        or re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", snapshot.get("bootId", "")) is None
        or snapshot.get("recoveryEvidenceSha256") != recovery_evidence_sha
        or any(type(snapshot.get(key)) is not str or owner.SHA256_RE.fullmatch(snapshot[key]) is None for key in ("targetEvidenceSha256", "recoveryEvidenceSha256", "receiptSha256"))
    ):
        raise CloseError("park-close result is invalid")
    return value


def next_log_dir() -> Path:
    require_side_root()
    for ordinal in range(1, 9):
        path = SIDE_ROOT / f"{LOG_PREFIX}{ordinal}-logs"
        if not path.exists():
            return path
    raise CloseError("read-only observation ordinal budget exhausted")


def execute(approval: str) -> dict:
    require_side_root()
    result_exists = RESULT.exists()
    intent_exists = observation_intent_path().exists()
    manifest_raw, manifest = fixed_inputs(allow_released=result_exists)
    _review_raw, review_sha = review_lease()
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    expected_token = APPROVAL_PREFIX + hashlib.sha256(manifest_raw).hexdigest() + ":" + review_sha + ":" + closure_sha256()
    if approval != expected_token:
        raise CloseError("approval mismatch")
    recovery_evidence_sha = manifest["qualification"]["review"]["sha256"]
    if result_exists:
        if REQUIRE_INTENT_FOR_RESULT and not intent_exists:
            raise CloseError("result exists without required observation intent")
        intent_sha = (
            observation_intent_sha256(manifest_sha, review_sha, approval)
            if intent_exists else None
        )
        payload = read_result(
            manifest_sha, review_sha, recovery_evidence_sha, intent_sha
        )
        fixed_inputs(allow_released=True)
        review_lease()
        if REQUIRE_INTENT_FOR_RESULT:
            observation_intent_sha256(manifest_sha, review_sha, approval)
        active, _ = owner._active_guard(manifest)
        if active.exists():
            owner._release_active_guard(manifest)
        fixed_inputs(allow_released=True)
        review_lease()
        if REQUIRE_INTENT_FOR_RESULT:
            observation_intent_sha256(manifest_sha, review_sha, approval)
        read_result(manifest_sha, review_sha, recovery_evidence_sha, intent_sha)
        owner._require_candidate_guard_absent(manifest)
        return payload
    if intent_exists:
        raise CloseError("observation intent is consumed without a result; park")
    publish_observation_intent(
        observation_intent_value(manifest_sha, review_sha, approval)
    )
    intent_sha = observation_intent_sha256(manifest_sha, review_sha, approval)
    fixed_inputs()
    review_lease()
    log_dir = next_log_dir()
    runner = adapter.HostRunner(log_dir, redactor=adapter.SerialRedactor(hashes=(manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"],)))
    backend = adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])
    snapshot = backend.observe({"version": owner.V2321_ROLLBACK_VERSION, "build": owner.V2321_ROLLBACK_BUILD}, manifest["qualification"]["freshState"], require_fresh_state=False, timeout_sec=90)
    if not snapshot.healthy or not snapshot.recovery_available or not snapshot.other_targets_untouched or snapshot.fresh_state_observed or snapshot.fresh_state_absent:
        raise CloseError("fresh V2321 health did not pass")
    observation_intent_sha256(manifest_sha, review_sha, approval)
    fixed_inputs()
    review_lease()
    payload = {"schema": RESULT_SCHEMA, "decision": "PRE_CANDIDATE_RECOVERY_PARK_CLOSED_NO_CANDIDATE", "runId": RUN_ID, "manifestSha256": manifest_sha, "currentReviewSha256": review_sha, "candidateGuardPublished": False, "candidateIntentPublished": False, "candidateHelperLaunched": False, "candidateBytesTransferred": 0, "rollbackBytesTransferred": 0, "candidateReplay": False, "recoveryTransitionReplay": False, "snapshot": snapshot.payload()}
    if REQUIRE_INTENT_FOR_RESULT:
        payload["observationIntentSha256"] = intent_sha
    publish(payload)
    observation_intent_sha256(manifest_sha, review_sha, approval)
    read_result(manifest_sha, review_sha, recovery_evidence_sha, intent_sha)
    review_lease()
    owner._release_active_guard(manifest)
    fixed_inputs(allow_released=True)
    review_lease()
    owner._require_candidate_guard_absent(manifest)
    observation_intent_sha256(manifest_sha, review_sha, approval)
    read_result(manifest_sha, review_sha, recovery_evidence_sha, intent_sha)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("prepare")
    live = sub.add_parser("execute")
    live.add_argument("--approval", required=True)
    args = parser.parse_args(argv)
    if args.action == "prepare":
        print(json.dumps({"approval": token(), "runId": RUN_ID}, sort_keys=True))
        return 0
    print(json.dumps(execute(args.approval), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CloseError, owner.ContractError, adapter.ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
