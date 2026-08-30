#!/usr/bin/env python3
"""Resume exact H41 run-02 from late TWRP for one manual demo and rollback."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import a90_boot_only_f1_minimal_v1 as owner
import a90_boot_only_f1_adapter_v1 as adapter


CAPABILITY = "A90_H41_RUN02_LATE_RECOVERY_MANUAL_DEMO_V1"
RUN_ID = "a90-h41-f1-20260830-02"
MANIFEST = ROOT / "workspace/private/manifests/a90-h41-f1-20260830-02.json"
MANIFEST_SHA256 = "eacd2090683e842314dcdfe9e4a1ae16bdb5eb35af5ede0a4b917653e0c6fe40"
CANDIDATE_SHA256 = "5aa3ca852e1cd9d89a23cfd0223a64fe98e5e0e356d71dc6543da6afe6389574"
ACTIVE_GUARD_SHA256 = "bfe721f317c35e1e7aff8e2d45c9053efc004e51350b2e3efb45168d7f646f50"
SIDE_ROOT = owner.RUN_ROOT / "a90-h41-run02-late-recovery-demo-v1"
REVIEW = ROOT / "docs/reports/A90_H41_RUN02_LATE_RECOVERY_MANUAL_DEMO_REVIEW_2026-08-30.json"
APPROVAL_PREFIX = "A90-H41-RUN02-LATE-RECOVERY-DEMO-V1-APPROVE:"
SELF_REL = "workspace/public/src/scripts/server-distro/a90_h41_run02_late_recovery_demo_v1.py"
TEST_REL = "tests/test_a90_h41_run02_late_recovery_demo_v1.py"
CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
GOAL_REL = "GOAL_A90.md"
INCIDENT_REL = "docs/reports/A90_H41_PRE_CANDIDATE_RECOVERY_PARK_2026-08-30.md"
REVIEW_SCHEMA = "a90-h41-run02-late-recovery-manual-demo-review-v1"
RECORD_SCHEMA = "a90-h41-run02-late-recovery-manual-demo-record-v1"
SHA_RE = re.compile(r"[0-9a-f]{64}")
ORIGINAL_RECORD_HASHES = {
    "00-prepared.json": "c86fc6d120f971d1131b45986817e01884db49e7707e4ffc4b45d96f21452e9c",
    "10-approved.json": "1f7fbd2131a24b6aab4966ed26ef4f3031db1f70f8cca8c05d05e81d66c2500a",
    "11-recovery-transition-intent.json": "76389cbef3aa52621c4dc73889771a363f4b283caee1b22729a12c321980bf19",
    "13-recovery-transition-parked.json": "d3a1b6e9bf9c7cfa1fae98a1bf9c0f7342f2349eb20982921c17c875c5f921c6",
}
ORIGINAL_LOG_HASHES = {
    "001-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "001-usb-inventory.stdout": "663764009e28b57b78cded9955dd826b4479d16b2b0e2135b97d94526761fb72",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "7687c7b41b9e219a9189cf69e56b06925a79bfd00724866565d99112be1399b8",
    "003-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-boot-id-start.stdout": "5a76d56175a61a025a0421987dc066c167e37bec9deb156b87f9c173e70c77df",
    "004-version.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "004-version.stdout": "0a01d6b63150098716a1c1b6ec323ee8e039c4299201d1417e595fa12af4ca8d",
    "005-selftest.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "005-selftest.stdout": "3373c3d32c002a16109302c5879bbf65fefa6f278a443488bb8d913840458d67",
    "006-status.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "006-status.stdout": "5014adbd17644b02eb6eb51fe717c4191705c0f1c7c19e4e74500a3b5f10d554",
    "007-boot-id-final.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "007-boot-id-final.stdout": "ddafe18020dd399bbc608014521c76247c8792d0267bbcee0f6d17ff361cdcc4",
    "008-fresh-enable-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "008-fresh-enable-path.stdout": "8eea531652a98e3d2889ded63b5d9c399bbe2ce0a8896ad9d136d3dfa5cb1318",
    "009-fresh-latch-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "009-fresh-latch-path.stdout": "cdf4c383f39961ff7d9d6569c2802696e88255dd739258d90b7edafa9dfe6e39",
    "010-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "010-effect-usb-inventory.stdout": "663764009e28b57b78cded9955dd826b4479d16b2b0e2135b97d94526761fb72",
    "011-native-to-recovery.stderr": "d59f2098b0203d698724e700116f437c7669387b048de21cc205e7b2c3a66bf2",
    "011-native-to-recovery.stdout": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
INSTALL_PATH = (
    "00-transaction-intent.json", "10-late-recovery-ready.json",
    "20-candidate-intent.json", "21-candidate-launched.json",
    "22-candidate-result.json", "23-demo-window.json",
)
ROLLBACK_PATH = INSTALL_PATH + (
    "30-rollback-intent.json", "31-rollback-launched.json",
    "32-rollback-result.json", "40-final.json",
)


class DemoError(RuntimeError):
    """Any changed, ambiguous, or consumed H41 demo state."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fixed_file(path: Path, label: str, maximum: int = owner.MAX_JSON_BYTES) -> bytes:
    try:
        before = path.lstat()
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise DemoError(f"{label} is unavailable") from exc
    try:
        current = os.fstat(fd)
        raw = os.pread(fd, current.st_size, 0)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or before.st_nlink != 1
            or current.st_nlink != 1
            or before.st_uid != os.getuid()
            or before.st_gid != os.getgid()
            or current.st_uid != os.getuid()
            or current.st_gid != os.getgid()
            or stat.S_IMODE(before.st_mode) not in {0o600, 0o644}
            or stat.S_IMODE(current.st_mode) != stat.S_IMODE(before.st_mode)
            or (before.st_dev, before.st_ino, before.st_size)
            != (current.st_dev, current.st_ino, current.st_size)
            or not 0 <= len(raw) <= maximum
            or len(raw) != current.st_size
            or os.pread(fd, 1, current.st_size)
        ):
            raise DemoError(f"{label} identity changed")
        return raw
    finally:
        os.close(fd)


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    digest.update(owner.execution_closure_sha256().encode("ascii") + b"\0")
    for relative in (SELF_REL, TEST_REL, CONTRACT_REL, GOAL_REL, INCIDENT_REL):
        raw = (ROOT / relative).read_bytes()
        digest.update(relative.encode() + b"\0")
        digest.update(str(len(raw)).encode() + b"\0")
        digest.update(_sha(raw).encode() + b"\0")
    return digest.hexdigest()


def _review_lease() -> tuple[str, str]:
    raw = owner._read_bounded_regular(REVIEW, "H41 late-Recovery demo review", owner.MAX_JSON_BYTES)
    value = owner.parse_canonical(raw, "H41 late-Recovery demo review")
    keys = {
        "schema", "capability", "verdict", "runId", "manifestSha256",
        "executionClosureSha256", "originalRecordHashes", "originalLogHashes",
        "findings", "contacts", "reviewer", "reviewDate", "liveAuthority",
    }
    closure = execution_closure_sha256()
    if (
        type(value) is not dict
        or set(value) != keys
        or value["schema"] != REVIEW_SCHEMA
        or value["capability"] != CAPABILITY
        or value["verdict"] != "PASS_GO"
        or value["runId"] != RUN_ID
        or value["manifestSha256"] != MANIFEST_SHA256
        or value["executionClosureSha256"] != closure
        or value["originalRecordHashes"] != ORIGINAL_RECORD_HASHES
        or value["originalLogHashes"] != ORIGINAL_LOG_HASHES
        or value["reviewDate"] != "2026-08-30"
        or value["liveAuthority"] is not False
    ):
        raise DemoError("H41 late-Recovery demo review is not exact PASS_GO")
    findings, contacts = value["findings"], value["contacts"]
    if (
        type(findings) is not dict
        or set(findings) != {"high", "medium", "low"}
        or any(type(findings[key]) is not list or findings[key] for key in findings)
        or type(contacts) is not dict
        or set(contacts) != {
            "device", "dev", "usb", "network", "workspacePrivate",
            "otherTargets", "writes",
        }
        or any(type(item) is not int or item != 0 for item in contacts.values())
        or type(value["reviewer"]) is not str
        or not value["reviewer"]
    ):
        raise DemoError("H41 late-Recovery demo review has findings or contacts")
    return _sha(raw), closure


def _original_context(
    *, candidate_present: bool, allow_active_absent: bool = False
) -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    raw, manifest = owner.load_manifest(MANIFEST)
    if (
        _sha(raw) != MANIFEST_SHA256
        or manifest["runId"] != RUN_ID
        or manifest["candidate"]["sha256"] != CANDIDATE_SHA256
    ):
        raise DemoError("fixed H41 run-02 manifest changed")
    owner._verify_qualification_inputs(manifest)
    run = owner.RUN_ROOT / RUN_ID
    records = owner.read_records(run)
    if tuple(records) != tuple(ORIGINAL_RECORD_HASHES):
        raise DemoError("H41 run-02 is not the exact four-record park")
    for name, expected in ORIGINAL_RECORD_HASHES.items():
        if _sha(_fixed_file(run / name, f"original record {name}")) != expected:
            raise DemoError(f"original H41 record changed: {name}")
    parked = records["13-recovery-transition-parked.json"]["payload"]
    if parked != {
        "schema": owner.RECOVERY_TRANSITION_PARK_SCHEMA,
        "terminal": "RECOVERY_REQUIRED",
        "reason": "RECOVERY_NOT_PROVED",
        "candidateReplay": False,
        "candidateGuardPublished": False,
        "candidateIntentPublished": False,
        "candidateHelperLaunched": False,
    }:
        raise DemoError("H41 run-02 park payload changed")
    logs = owner.RUN_ROOT / f"{RUN_ID}-execute-1-logs"
    if {path.name for path in logs.iterdir()} != set(ORIGINAL_LOG_HASHES) | {".adb-home"}:
        raise DemoError("H41 run-02 execute log set changed")
    for name, expected in ORIGINAL_LOG_HASHES.items():
        if _sha(_fixed_file(logs / name, f"original log {name}", adapter.MAX_OUTPUT_BYTES)) != expected:
            raise DemoError(f"original H41 log changed: {name}")
    active_path, active_raw = owner._active_guard(manifest)
    try:
        active_present = active_path.exists() or active_path.is_symlink()
    except OSError as exc:
        raise DemoError("H41 active guard presence is uncertain") from exc
    if active_present:
        if _sha(_fixed_file(active_path, "H41 active guard")) != ACTIVE_GUARD_SHA256 or _sha(active_raw) != ACTIVE_GUARD_SHA256:
            raise DemoError("H41 active guard changed")
    elif not allow_active_absent:
        raise DemoError("H41 active guard is absent before final closure")
    if candidate_present:
        owner._require_candidate_guard(manifest)
    else:
        owner._require_candidate_guard_absent(manifest)
    prepared = owner._load_prepared(records, MANIFEST_SHA256, RUN_ID)
    return raw, manifest, prepared


def _ensure_side_root() -> None:
    if not SIDE_ROOT.exists():
        SIDE_ROOT.mkdir(mode=0o700, parents=False)
        owner._fsync_directory(SIDE_ROOT.parent)
    metadata = SIDE_ROOT.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise DemoError("H41 demo side root is not exact private directory")


def _files() -> tuple[str, ...]:
    if not SIDE_ROOT.exists():
        return ()
    names = tuple(sorted(path.name for path in SIDE_ROOT.iterdir() if path.is_file()))
    allowed = {(), *[tuple(sorted(INSTALL_PATH[:index])) for index in range(1, len(INSTALL_PATH) + 1)], *[tuple(sorted(ROLLBACK_PATH[:index])) for index in range(len(INSTALL_PATH) + 1, len(ROLLBACK_PATH) + 1)]}
    if names not in allowed:
        raise DemoError("H41 demo sidecar prefix is not exact")
    return names


def _publish(name: str, payload: dict[str, Any]) -> str:
    _ensure_side_root()
    path = SIDE_ROOT / name
    raw = owner.canonical_json({
        "schema": RECORD_SCHEMA,
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "payload": payload,
    })
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            offset = 0
            while offset < len(raw):
                written = os.write(fd, raw[offset:])
                if written <= 0:
                    raise DemoError("H41 demo record short write")
                offset += written
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise DemoError(f"H41 demo record publication failed: {name}") from exc
    owner._fsync_directory(SIDE_ROOT)
    if _fixed_file(path, f"H41 demo record {name}") != raw:
        raise DemoError(f"H41 demo record readback changed: {name}")
    return _sha(raw)


def _record(name: str) -> dict[str, Any]:
    raw = _fixed_file(SIDE_ROOT / name, f"H41 demo record {name}")
    value = owner.parse_canonical(raw, f"H41 demo record {name}")
    if (
        type(value) is not dict
        or set(value) != {"schema", "capability", "runId", "manifestSha256", "payload"}
        or value["schema"] != RECORD_SCHEMA
        or value["capability"] != CAPABILITY
        or value["runId"] != RUN_ID
        or value["manifestSha256"] != MANIFEST_SHA256
        or type(value["payload"]) is not dict
    ):
        raise DemoError(f"H41 demo record envelope changed: {name}")
    return value["payload"]


def _token(review_sha: str, closure: str) -> str:
    binding = {
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "candidateSha256": CANDIDATE_SHA256,
        "currentReviewSha256": review_sha,
        "executionClosureSha256": closure,
        "phases": ["late-recovery-candidate-install", "manual-demo-window", "v2321-rollback"],
    }
    return APPROVAL_PREFIX + _sha(owner.canonical_json(binding))


def prepare() -> str:
    _original_context(candidate_present=False)
    review_sha, closure = _review_lease()
    if _files():
        raise DemoError("H41 late-Recovery demo transaction is already consumed")
    return _token(review_sha, closure)


def _adapter(log_name: str, manifest: dict[str, Any]) -> adapter.FixedA90Adapter:
    _ensure_side_root()
    runner = adapter.HostRunner(
        SIDE_ROOT / log_name,
        redactor=adapter.SerialRedactor(
            hashes=(manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"],)
        ),
    )
    return adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])


def install(approval: str) -> dict[str, Any]:
    _raw, manifest, prepared = _original_context(candidate_present=False)
    review_sha, closure = _review_lease()
    if approval != _token(review_sha, closure) or _files():
        raise DemoError("H41 late-Recovery install approval/state mismatch")
    candidate = owner.BoundArtifact.open(manifest["candidate"], "candidate")
    try:
        if candidate.checkpoint() != prepared["candidate"]:
            raise DemoError("H41 candidate differs from prepared bytes")
        probe = _adapter("preflight-1-logs", manifest)
        role, usb_sha, adb_sha = probe._effect_inventory(rollback=False)
        if role != adapter.ADB_ROLE_RECOVERY or adb_sha is None:
            raise DemoError("late endpoint is not exact bound A90 Recovery")
        intent = {
            "approvalSha256": _sha(approval.encode("ascii")),
            "currentReviewSha256": review_sha,
            "executionClosureSha256": closure,
            "candidateReplay": False,
            "recoveryTransitionReplay": False,
            "candidateWriteLimit": 1,
            "rollbackWriteLimit": 1,
            "lateRecoveryUsbSha256": usb_sha,
            "lateRecoveryAdbSha256": adb_sha,
        }
        _publish("00-transaction-intent.json", intent)
        _original_context(candidate_present=False)
        if _review_lease() != (review_sha, closure):
            raise DemoError("H41 demo review lease changed")
        live = _adapter("install-1-logs", manifest)
        role2, usb_sha2, adb_sha2 = live._effect_inventory(rollback=False)
        if (role2, usb_sha2, adb_sha2) != (role, usb_sha, adb_sha):
            raise DemoError("late Recovery inventory changed after intent")
        binding = owner.RecoveryBinding(
            usb_inventory_sha256=usb_sha2,
            adb_inventory_sha256=adb_sha2,
            adb_serial_sha256=manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"],
            request_outcome="UNCERTAIN_RESPONSE",
        )
        binding.validate(manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"])
        _publish("10-late-recovery-ready.json", binding.payload())
        _original_context(candidate_present=False)
        owner._publish_candidate_guard(manifest)
        _original_context(candidate_present=True)
        _publish("20-candidate-intent.json", {"sha256": CANDIDATE_SHA256, "attempt": 1})
        candidate.checkpoint()
        _publish("21-candidate-launched.json", {"attempt": 1})
        _original_context(candidate_present=True)
        if _review_lease() != (review_sha, closure):
            raise DemoError("H41 demo review lease changed before candidate")
        result = live.flash(
            manifest["candidate"],
            rollback=False,
            timeout_sec=manifest["timeouts"]["flashSec"],
            recovery_binding=binding,
        )
        result.validate()
        candidate.checkpoint()
        _publish("22-candidate-result.json", result.payload())
        if _review_lease() != (review_sha, closure):
            raise DemoError("H41 demo review lease changed after candidate")
        if (
            result.completed is True
            and result.returncode == 0
            and result.quiescent is True
            and result.outcome == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
        ):
            payload = {
                "state": "H41_MANUAL_DEMO_WINDOW_UNPROVED",
                "candidateReplay": False,
                "rollbackReplay": False,
                "runtimeProved": False,
                "operatorMustCloseMenuBeforeRollback": True,
            }
            _publish("23-demo-window.json", payload)
            return payload
        if result.quiescent is not True:
            raise DemoError("H41 candidate helper is not quiescent; rollback cannot overlap")
        _publish("23-demo-window.json", {
            "state": "H41_CANDIDATE_NON_SUCCESS_ROLLBACK_REQUIRED",
            "candidateReplay": False,
            "rollbackReplay": False,
            "runtimeProved": False,
            "operatorMustCloseMenuBeforeRollback": False,
        })
        return rollback(approval, automatic=True)
    finally:
        candidate.close()


def _effect_result(name: str) -> owner.EffectResult:
    payload = _record(name)
    if set(payload) != {"returncode", "completed", "quiescent", "receiptSha256", "outcome"}:
        raise DemoError(f"H41 effect result shape changed: {name}")
    result = owner.EffectResult(
        payload["returncode"], payload["completed"], payload["quiescent"],
        payload["receiptSha256"], payload["outcome"],
    )
    result.validate()
    return result


def _validate_install_prefix(
    approval: str,
    manifest: dict[str, Any],
    review_sha: str,
    closure: str,
    *, automatic: bool,
) -> owner.EffectResult:
    intent = _record("00-transaction-intent.json")
    if (
        set(intent) != {
            "approvalSha256", "currentReviewSha256", "executionClosureSha256",
            "candidateReplay", "recoveryTransitionReplay", "candidateWriteLimit",
            "rollbackWriteLimit", "lateRecoveryUsbSha256", "lateRecoveryAdbSha256",
        }
        or intent["approvalSha256"] != _sha(approval.encode("ascii"))
        or intent["currentReviewSha256"] != review_sha
        or intent["executionClosureSha256"] != closure
        or intent["candidateReplay"] is not False
        or intent["recoveryTransitionReplay"] is not False
        or type(intent["candidateWriteLimit"]) is not int
        or intent["candidateWriteLimit"] != 1
        or type(intent["rollbackWriteLimit"]) is not int
        or intent["rollbackWriteLimit"] != 1
        or type(intent["lateRecoveryUsbSha256"]) is not str
        or SHA_RE.fullmatch(intent["lateRecoveryUsbSha256"]) is None
        or type(intent["lateRecoveryAdbSha256"]) is not str
        or SHA_RE.fullmatch(intent["lateRecoveryAdbSha256"]) is None
    ):
        raise DemoError("H41 transaction intent changed")
    binding = owner._recovery_binding(
        _record("10-late-recovery-ready.json"),
        manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"],
    )
    if (
        binding.usb_inventory_sha256 != intent["lateRecoveryUsbSha256"]
        or binding.adb_inventory_sha256 != intent["lateRecoveryAdbSha256"]
        or binding.request_outcome != "UNCERTAIN_RESPONSE"
    ):
        raise DemoError("H41 late Recovery binding changed")
    if _record("20-candidate-intent.json") != {
        "sha256": CANDIDATE_SHA256, "attempt": 1,
    } or _record("21-candidate-launched.json") != {"attempt": 1}:
        raise DemoError("H41 candidate intent/launch changed")
    result = _effect_result("22-candidate-result.json")
    expected_demo = {
        "state": (
            "H41_CANDIDATE_NON_SUCCESS_ROLLBACK_REQUIRED"
            if automatic else "H41_MANUAL_DEMO_WINDOW_UNPROVED"
        ),
        "candidateReplay": False,
        "rollbackReplay": False,
        "runtimeProved": False,
        "operatorMustCloseMenuBeforeRollback": not automatic,
    }
    if _record("23-demo-window.json") != expected_demo:
        raise DemoError("H41 manual demo window record changed")
    return result


def _validate_final(final: dict[str, Any], manifest: dict[str, Any]) -> bool:
    if set(final) != {
        "terminal", "reason", "candidateReplay", "rollbackReplay",
        "h41RuntimeProved", "candidateResult", "rollbackResult", "snapshot",
    }:
        raise DemoError("H41 final fields changed")
    candidate_result = _effect_result("22-candidate-result.json")
    rollback_result = _effect_result("32-rollback-result.json")
    if (
        final["candidateReplay"] is not False
        or final["rollbackReplay"] is not False
        or final["h41RuntimeProved"] is not False
        or final["candidateResult"] != candidate_result.payload()
        or final["rollbackResult"] != rollback_result.payload()
    ):
        raise DemoError("H41 final effect binding changed")
    snapshot_payload = final["snapshot"]
    snapshot = None
    if snapshot_payload is not None:
        if type(snapshot_payload) is not dict or set(snapshot_payload) != {
            "targetEvidenceSha256", "bootId", "version", "build", "healthy",
            "recoveryAvailable", "recoveryEvidenceSha256", "freshStateObserved",
            "freshStateAbsent", "otherTargetsUntouched", "receiptSha256",
        }:
            raise DemoError("H41 final snapshot fields changed")
        snapshot = owner.Snapshot(
            target_evidence_sha256=snapshot_payload["targetEvidenceSha256"],
            boot_id=snapshot_payload["bootId"],
            version=snapshot_payload["version"],
            build=snapshot_payload["build"],
            healthy=snapshot_payload["healthy"],
            recovery_available=snapshot_payload["recoveryAvailable"],
            recovery_evidence_sha256=snapshot_payload["recoveryEvidenceSha256"],
            fresh_state_observed=snapshot_payload["freshStateObserved"],
            fresh_state_absent=snapshot_payload["freshStateAbsent"],
            other_targets_untouched=snapshot_payload["otherTargetsUntouched"],
            receipt_sha256=snapshot_payload["receiptSha256"],
        )
        snapshot.validate()
    healthy = (
        rollback_result.completed is True
        and rollback_result.returncode == 0
        and rollback_result.quiescent is True
        and rollback_result.outcome
        == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
        and snapshot is not None
        and snapshot.healthy is True
        and snapshot.recovery_available is True
        and snapshot.other_targets_untouched is True
        and snapshot.fresh_state_observed is False
        and snapshot.fresh_state_absent is False
        and snapshot.recovery_evidence_sha256
        == manifest["qualification"]["review"]["sha256"]
        and (snapshot.version, snapshot.build)
        == (manifest["rollback"]["version"], manifest["rollback"]["build"])
    )
    if healthy:
        if final["terminal"] != "NO_PROOF_ROLLED_BACK" or final["reason"] != "ROLLBACK_HEALTHY":
            raise DemoError("healthy H41 rollback final changed")
        return True
    if final["terminal"] != "RECOVERY_REQUIRED" or final["reason"] != "ROLLBACK_HEALTH_UNPROVED":
        raise DemoError("unproved H41 rollback final changed")
    return False


def _validate_rollback_prefix(
    approval: str, review_sha: str, closure: str
) -> bool:
    intent = _record("30-rollback-intent.json")
    if set(intent) != {
        "sha256", "attempt", "automaticAfterCandidateNonSuccess",
        "operatorAttended", "menuClosedConfirmed", "approvalSha256",
        "currentReviewSha256", "executionClosureSha256",
        "candidateReplay", "rollbackReplay",
    }:
        raise DemoError("H41 rollback intent fields changed")
    automatic = intent["automaticAfterCandidateNonSuccess"]
    if (
        type(automatic) is not bool
        or intent["sha256"] != owner.V2321_ROLLBACK_SHA256
        or type(intent["attempt"]) is not int
        or intent["attempt"] != 1
        or intent["approvalSha256"] != _sha(approval.encode("ascii"))
        or intent["currentReviewSha256"] != review_sha
        or intent["executionClosureSha256"] != closure
        or intent["candidateReplay"] is not False
        or intent["rollbackReplay"] is not False
        or type(intent["operatorAttended"]) is not bool
        or type(intent["menuClosedConfirmed"]) is not bool
        or (
            not automatic
            and (
                intent["operatorAttended"] is not True
                or intent["menuClosedConfirmed"] is not True
            )
        )
        or (
            automatic
            and (
                intent["operatorAttended"] is not False
                or intent["menuClosedConfirmed"] is not False
            )
        )
        or _record("31-rollback-launched.json") != {"attempt": 1}
    ):
        raise DemoError("H41 rollback intent/launch binding changed")
    _effect_result("32-rollback-result.json")
    return automatic


def rollback(
    approval: str,
    *,
    automatic: bool = False,
    operator_attended: bool = False,
    menu_closed_confirmed: bool = False,
) -> dict[str, Any]:
    if (
        type(automatic) is not bool
        or type(operator_attended) is not bool
        or type(menu_closed_confirmed) is not bool
        or (
            not automatic
            and (operator_attended is not True or menu_closed_confirmed is not True)
        )
        or (
            automatic
            and (operator_attended is not False or menu_closed_confirmed is not False)
        )
    ):
        raise DemoError("manual rollback requires attended exact menu-close confirmation")
    _raw, manifest, prepared = _original_context(
        candidate_present=True, allow_active_absent=True
    )
    review_sha, closure = _review_lease()
    if approval != _token(review_sha, closure):
        raise DemoError("H41 rollback approval mismatch")
    names = _files()
    active_path, _active_raw = owner._active_guard(manifest)
    active_present = active_path.exists() or active_path.is_symlink()
    if names == tuple(sorted(ROLLBACK_PATH)):
        _validate_rollback_prefix(approval, review_sha, closure)
        final = _record("40-final.json")
        final_healthy = _validate_final(final, manifest)
        if final_healthy:
            if active_present:
                owner._require_active_guard(manifest)
                owner._release_active_guard(manifest)
            owner._require_candidate_guard(manifest)
            return final
        if active_present:
            owner._require_active_guard(manifest)
            return final
        raise DemoError("H41 final/active state is not resumable")
    if not active_present:
        raise DemoError("H41 active guard disappeared before rollback closure")
    if "30-rollback-intent.json" in names:
        raise DemoError("H41 rollback is already consumed and never replays")
    if tuple(sorted(INSTALL_PATH)) != names:
        raise DemoError("H41 rollback requires exact completed install prefix")
    candidate_result = _validate_install_prefix(
        approval, manifest, review_sha, closure, automatic=automatic
    )
    if candidate_result.quiescent is not True:
        raise DemoError("H41 candidate helper is not quiescent")
    rollback_artifact = owner.BoundArtifact.open(manifest["rollback"], "rollback")
    try:
        if rollback_artifact.checkpoint() != prepared["rollback"]:
            raise DemoError("V2321 rollback differs from prepared bytes")
        rollback_intent_value = {
            "sha256": manifest["rollback"]["sha256"],
            "attempt": 1,
            "automaticAfterCandidateNonSuccess": automatic,
            "operatorAttended": operator_attended,
            "menuClosedConfirmed": menu_closed_confirmed,
            "approvalSha256": _sha(approval.encode("ascii")),
            "currentReviewSha256": review_sha,
            "executionClosureSha256": closure,
            "candidateReplay": False,
            "rollbackReplay": False,
        }
        _publish("30-rollback-intent.json", rollback_intent_value)
        _publish("31-rollback-launched.json", {"attempt": 1})
        rollback_intent = _record("30-rollback-intent.json")
        if (
            rollback_intent != rollback_intent_value
            or _record("31-rollback-launched.json") != {"attempt": 1}
        ):
            raise DemoError("H41 rollback confirmation binding changed before effect")
        _original_context(candidate_present=True)
        if _review_lease() != (review_sha, closure):
            raise DemoError("H41 demo review lease changed before rollback")
        live = _adapter("rollback-1-logs", manifest)
        result = live.flash(
            manifest["rollback"], rollback=True,
            timeout_sec=manifest["timeouts"]["flashSec"],
        )
        result.validate()
        rollback_artifact.checkpoint()
        _publish("32-rollback-result.json", result.payload())
        if _review_lease() != (review_sha, closure):
            raise DemoError("H41 demo review lease changed after rollback")
        snapshot = None
        if result.quiescent is True:
            try:
                snapshot = live.observe(
                    manifest["rollback"], manifest["qualification"]["freshState"],
                    require_fresh_state=False,
                    timeout_sec=manifest["timeouts"]["healthSec"],
                )
                snapshot.validate()
            except Exception:
                snapshot = None
        healthy = (
            snapshot is not None
            and result.completed is True
            and result.returncode == 0
            and result.quiescent is True
            and result.outcome == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
            and snapshot.healthy is True
            and snapshot.recovery_available is True
            and snapshot.other_targets_untouched is True
            and (snapshot.version, snapshot.build)
            == (manifest["rollback"]["version"], manifest["rollback"]["build"])
        )
        final = {
            "terminal": "NO_PROOF_ROLLED_BACK" if healthy else "RECOVERY_REQUIRED",
            "reason": "ROLLBACK_HEALTHY" if healthy else "ROLLBACK_HEALTH_UNPROVED",
            "candidateReplay": False,
            "rollbackReplay": False,
            "h41RuntimeProved": False,
            "candidateResult": candidate_result.payload(),
            "rollbackResult": result.payload(),
            "snapshot": None if snapshot is None else snapshot.payload(),
        }
        _publish("40-final.json", final)
        if _validate_final(_record("40-final.json"), manifest) != healthy:
            raise DemoError("H41 final readback health changed")
        if _review_lease() != (review_sha, closure):
            raise DemoError("H41 demo review lease changed before release")
        if healthy:
            _original_context(candidate_present=True)
            owner._release_active_guard(manifest)
            owner._require_candidate_guard(manifest)
        return final
    finally:
        rollback_artifact.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("prepare")
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--approval", required=True)
    rollback_parser = sub.add_parser("rollback")
    rollback_parser.add_argument("--approval", required=True)
    rollback_parser.add_argument("--operator-attended", action="store_true")
    rollback_parser.add_argument("--menu-closed-confirmed", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "prepare":
        print(json.dumps({"approval": prepare(), "runId": RUN_ID}, sort_keys=True))
    elif args.action == "install":
        print(json.dumps(install(args.approval), sort_keys=True))
    else:
        print(json.dumps(rollback(
            args.approval,
            operator_attended=args.operator_attended,
            menu_closed_confirmed=args.menu_closed_confirmed,
        ), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DemoError, owner.ContractError, adapter.ContractError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
