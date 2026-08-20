#!/usr/bin/env python3
"""Fixed H0-only physical System-return continuation for A90 H28.

The H28 candidate, rollback, and host return requests are consumed.  This
program arms one operator action and performs one read-only Native observation;
it has no device-effect or transfer path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FIXED_PYTHON = "/usr/bin/python3.14"
FIXED_CWD = "/home/temmie/dev/android-native-init-lab"
FIXED_SCRIPT = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py"
FIXED_OWNER = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
FIXED_SCRIPT_DIR = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro"


class _LaunchContractError(RuntimeError):
    pass


def _require_pre_import_launch_contract() -> None:
    if (
        sys.executable != FIXED_PYTHON
        or sys.dont_write_bytecode != 1
        or getattr(sys.flags, "dont_write_bytecode", 0) != 1
        or getattr(sys.flags, "no_user_site", 0) != 1
        or getattr(sys.flags, "ignore_environment", 0) != 1
        or os.getcwd() != FIXED_CWD
        or __file__ != FIXED_SCRIPT
        or not sys.argv
        or sys.argv[0] != FIXED_SCRIPT
        or not sys.path
        or sys.path[0] != FIXED_SCRIPT_DIR
    ):
        raise _LaunchContractError("fixed H28 pre-import launch contract is not exact")

    for path, label in ((FIXED_SCRIPT, "fixed reconciler"), (FIXED_OWNER, "fixed owner")):
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise _LaunchContractError(f"{label} cannot be inspected") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_uid != os.getuid()
            or metadata.st_gid != os.getgid()
            or metadata.st_mode & 0o022
        ):
            raise _LaunchContractError(f"{label} identity is not exact")


if __name__ == "__main__":
    try:
        _require_pre_import_launch_contract()
    except _LaunchContractError as exc:
        print(f"A90_H28_PHYSICAL_SYSTEM_RETURN_RECONCILE_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


import a90_boot_only_f1_minimal_v1 as owner


CAPABILITY = "A90_H28_PHYSICAL_SYSTEM_RETURN_RECOVERY_V1"
SCHEMA = "a90-h28-physical-system-return-reconciliation-v1"
INTENT_SCHEMA = "a90-h28-physical-system-return-intent-v1"
RUN_ID = "a90-h28-f1-20260821-01"
MANIFEST_PATH = owner.REPO_ROOT / "workspace/private/manifests/a90-h28-f1-20260821-01.json"
MANIFEST_SHA256 = "e708e45e9cd925229682c76ad3b6359426f2e636eb26eb111ea54e9843e8d1c2"
TERMINAL_SHA256 = "400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01"
CURRENT_REVIEW_PATH = owner.REPO_ROOT / (
    "docs/reports/A90_H28_PHYSICAL_SYSTEM_RETURN_RECOVERY_INDEPENDENT_REVIEW_2026-08-21.json"
)
SIDE_ROOT = owner.REPO_ROOT / "workspace/private/runs/a90-h28-physical-system-return-v1"
APPROVAL_PREFIX = "A90-H28-PHYSICAL-SYSTEM-RETURN-V1-APPROVE:"
INTENT_NAME = "10-physical-system-return-intent.json"
OBSERVATION_INTENT_NAME = "20-native-observation-intent.json"
RECOVERY_NAME = "41-recovery-closed.json"
INSTRUCTION = "A90 H28: on the attended A90 handset already showing TWRP, press Reboot -> System once."
BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
_H28_SOURCE_RELS = (
    "workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py",
    "docs/plans/A90_H28_PHYSICAL_SYSTEM_RETURN_RECOVERY_DESIGN_2026-08-21.md",
    "docs/operations/targets/A90_TARGET_CONTRACT.md",
    "AGENTS.md",
    "GOAL_A90.md",
    "docs/reports/A90_H28_TWRP_SYSTEM_RETURN_UNCERTAINTY_INCIDENT_2026-08-21.md",
)
EXECUTION_SOURCE_RELS = tuple(sorted(set(owner.EXECUTION_SOURCE_RELS) | set(_H28_SOURCE_RELS)))
INCIDENT_RECORD_SHA256 = {
    "00-prepared.json": "68b97cac14118ee4f3533a4b9760af10011efcc897332bad25fec585a5a0e7f3",
    "10-approved.json": "e5566c196dfeb7951a3d3d2dbd58863c0bb7c552c1da9fe511f53e0a7a9b2b16",
    "20-candidate-intent.json": "1849ef5cdba2cffdb56e3247ac7c95fc4e7f64b374167e7c75390520d346c591",
    "21-candidate-launched.json": "3107de5921c32e0dbd9fa945cd2bca3edd0191769c8fc8291e4eec97a06dc9cb",
    "22-candidate-result.json": "a53ec74e6f57bd6ee3b7104e6128a88b4f4fd04c296ec0885345e441f8fab546",
    "30-rollback-intent.json": "fcc6f246d9ff561728bb10d20dcc0b21890cf3639f0e1778ad548a10e91727f4",
    "31-rollback-launched.json": "3960accbe09872dde4f527235ad538f6b2c8eb50d046dc724fbb7bff828ded30",
    "32-rollback-result.json": "15c9d2bec62669561faa85d30c9496bf83b61ca250f9acec4e980a4c81eeb32d",
    "40-terminal.json": TERMINAL_SHA256,
}
ACTIVE_GUARD_SHA256 = "28aec73bf82ffda7feaff2a280cf89fe94ca7cf25431cf72d45f2b897601961d"
CANDIDATE_GUARD_SHA256 = "f675a04d00adccfe6484391085b603b8c14f7aff980dcf42ecfacb881e124dfe"
REVIEW_SCHEMA = "a90-h28-physical-system-return-independent-review-v1"
REVIEW_KEYS = {"schema", "capability", "verdict", "runId", "manifestSha256", "terminalSha256", "executionClosureSha256", "findings", "contacts", "liveAuthority"}
FINDING_KEYS = {"high", "medium", "low"}
CONTACT_KEYS = {"device", "dev", "usb", "network", "workspacePrivate", "otherTargets", "writes"}
INTENT_KEYS = {"schema", "capability", "runId", "manifestSha256", "terminalSha256", "currentReviewSha256", "executionClosureSha256", "approvalSha256"}
OBSERVATION_SCHEMA = "a90-h28-native-observation-intent-v1"
OBSERVATION_KEYS = {"schema", "capability", "runId", "manifestSha256", "terminalSha256", "physicalSystemReturnIntentSha256", "currentReviewSha256", "executionClosureSha256", "operatorAttended", "physicalSystemReturnConfirmed"}
PAYLOAD_KEYS = {"schema", "decision", "candidateReplay", "rollbackReplay", "originalTwrpReturnOutcome", "physicalSystemReturnConfirmed", "hostRecoveryCommandCount", "bootWriteCount", "physicalSystemReturnIntentSha256", "observationIntentSha256", "currentReviewSha256", "executionClosureSha256", "recoveredSnapshot", "recoveredSnapshotSha256"}
SNAPSHOT_KEYS = {"targetEvidenceSha256", "bootId", "version", "build", "healthy", "recoveryAvailable", "recoveryEvidenceSha256", "freshStateObserved", "freshStateAbsent", "otherTargetsUntouched", "receiptSha256"}
INCIDENT_NAMES = tuple(owner.ROLLBACK_PATH)


class ContractError(RuntimeError):
    """Any missing, changed, ambiguous, or unsafe state."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_sha(value: Any) -> str:
    return _sha(owner.canonical_json(value))


def _read_json(path: Path, label: str) -> tuple[bytes, Any]:
    try:
        raw = owner._read_bounded_regular(path, label, owner.MAX_JSON_BYTES)
        return raw, owner.parse_canonical(raw, label)
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc


def _private_dir(path: Path, label: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ContractError(f"{label} is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o077:
        raise ContractError(f"{label} is not a private direct directory")


def _run_directory() -> Path:
    _private_dir(owner.RUN_ROOT, "fixed A90 run root")
    result = owner.RUN_ROOT / RUN_ID
    _private_dir(result, "fixed H28 run directory")
    return result


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    for relative in EXECUTION_SOURCE_RELS:
        raw = (owner.REPO_ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii")); digest.update(b"\0")
        digest.update(_sha(raw).encode("ascii")); digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest() -> tuple[bytes, dict[str, Any]]:
    raw, value = _read_json(MANIFEST_PATH, "fixed H28 manifest")
    if _sha(raw) != MANIFEST_SHA256:
        raise ContractError("fixed H28 manifest bytes changed")
    try:
        manifest = owner.validate_manifest(value)
        owner._verify_qualification_inputs(manifest)
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    if manifest["runId"] != RUN_ID or manifest["candidate"]["sha256"] != "aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b" or manifest["rollback"]["sha256"] != owner.V2321_ROLLBACK_SHA256:
        raise ContractError("fixed H28 manifest identity changed")
    return raw, manifest


def _load_records(manifest: dict[str, Any]) -> tuple[Path, dict[str, dict[str, Any]]]:
    run_directory = _run_directory()
    try:
        records = owner.read_records(run_directory)
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    allowed = (set(INCIDENT_NAMES), set(INCIDENT_NAMES) | {RECOVERY_NAME})
    if set(records) not in allowed or tuple(name for name in owner.ROLLBACK_PATH if name in records) != owner.ROLLBACK_PATH:
        raise ContractError("H28 journal is not the exact nine-record terminal")
    for name, expected in INCIDENT_RECORD_SHA256.items():
        record = records.get(name)
        if type(record) is not dict or _json_sha(record) != expected or record.get("manifestSha256") != MANIFEST_SHA256:
            raise ContractError(f"fixed H28 incident record changed: {name}")
    terminal = records["40-terminal.json"]["payload"]
    if terminal.get("schema") != owner.RESULT_SCHEMA or terminal.get("terminal") != "RECOVERY_REQUIRED" or terminal.get("reason") != "ROLLBACK_HEALTH_UNPROVED" or terminal.get("snapshot") is not None or terminal.get("candidateReplay") is not False:
        raise ContractError("fixed H28 incident terminal changed")
    if records["20-candidate-intent.json"]["payload"] != {"sha256": manifest["candidate"]["sha256"]} or records["30-rollback-intent.json"]["payload"] != {"sha256": manifest["rollback"]["sha256"]}:
        raise ContractError("fixed H28 transfer intents changed")
    return run_directory, records


def _guard(path: Path, expected_hash: str, label: str) -> None:
    raw, _ = _read_json(path, label)
    if _sha(raw) != expected_hash:
        raise ContractError(f"{label} bytes changed")


def _require_guards(manifest: dict[str, Any], *, active: bool = True) -> None:
    try:
        active_path, active_raw = owner._active_guard(manifest)
        candidate_path, candidate_raw = owner._candidate_guard(manifest)
    except (KeyError, owner.ContractError) as exc:
        raise ContractError("fixed H28 guard identity cannot be derived") from exc
    if active:
        _guard(active_path, ACTIVE_GUARD_SHA256, "H28 active guard")
        if _sha(active_raw) != ACTIVE_GUARD_SHA256:
            raise ContractError("H28 active guard contract changed")
    _guard(candidate_path, CANDIDATE_GUARD_SHA256, "H28 candidate guard")
    if _sha(candidate_raw) != CANDIDATE_GUARD_SHA256:
        raise ContractError("H28 candidate guard contract changed")


def _validate_review(value: Any, manifest_sha256: str, closure_sha256: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != REVIEW_KEYS:
        raise ContractError("physical-return review fields mismatch")
    if value["schema"] != REVIEW_SCHEMA or value["capability"] != CAPABILITY or value["verdict"] != "PASS_GO" or value["runId"] != RUN_ID or value["manifestSha256"] != manifest_sha256 or value["terminalSha256"] != TERMINAL_SHA256 or value["executionClosureSha256"] != closure_sha256 or value["liveAuthority"] is not False:
        raise ContractError("physical-return review identity or verdict is invalid")
    findings, contacts = value["findings"], value["contacts"]
    if type(findings) is not dict or set(findings) != FINDING_KEYS or any(type(findings[k]) is not list or findings[k] for k in FINDING_KEYS):
        raise ContractError("physical-return review findings are invalid")
    if type(contacts) is not dict or set(contacts) != CONTACT_KEYS or any(type(item) is not int or item != 0 for item in contacts.values()):
        raise ContractError("physical-return review contacts are invalid")
    for key in ("manifestSha256", "terminalSha256", "executionClosureSha256"):
        if re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            raise ContractError(f"physical-return review {key} is invalid")
    return value


def _load_current_review() -> tuple[bytes, dict[str, Any], str, str]:
    raw, value = _read_json(CURRENT_REVIEW_PATH, "current physical-return review")
    closure = execution_closure_sha256()
    return raw, _validate_review(value, MANIFEST_SHA256, closure), _sha(raw), closure


class ReviewLease:
    """Hold the current review by one no-follow descriptor."""

    def __init__(self, expected_sha256: str, expected_closure_sha256: str) -> None:
        try:
            before = CURRENT_REVIEW_PATH.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid() or before.st_gid != os.getgid() or before.st_mode & 0o022 or before.st_size > owner.MAX_JSON_BYTES:
                raise ContractError("current review lease identity is invalid")
            self.fd = os.open(CURRENT_REVIEW_PATH, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as exc:
            raise ContractError("current review lease cannot be opened") from exc
        self.before, self.expected_sha256, self.expected_closure_sha256 = before, expected_sha256, expected_closure_sha256
        try:
            self.check()
        except BaseException:
            os.close(self.fd)
            raise

    def check(self) -> None:
        current = os.fstat(self.fd)
        try:
            pathname = CURRENT_REVIEW_PATH.lstat()
        except OSError as exc:
            raise ContractError("current review lease path disappeared") from exc
        identity = (self.before.st_dev, self.before.st_ino, self.before.st_size)
        if not stat.S_ISREG(current.st_mode) or current.st_nlink != 1 or current.st_uid != os.getuid() or current.st_gid != os.getgid() or current.st_mode & 0o022 or (current.st_dev, current.st_ino, current.st_size) != identity or (pathname.st_dev, pathname.st_ino, pathname.st_size) != identity or pathname.st_mode & 0o022 or pathname.st_uid != os.getuid() or pathname.st_gid != os.getgid():
            raise ContractError("current review lease drifted")
        raw = os.pread(self.fd, current.st_size, 0)
        if len(raw) != current.st_size or _sha(raw) != self.expected_sha256:
            raise ContractError("current review lease bytes changed")
        try:
            value = owner.parse_canonical(raw, "current physical-return review")
        except owner.ContractError as exc:
            raise ContractError(str(exc)) from exc
        _validate_review(value, MANIFEST_SHA256, self.expected_closure_sha256)

    def close(self) -> None:
        if getattr(self, "fd", -1) >= 0:
            os.close(self.fd); self.fd = -1


def _require_closure(lease: ReviewLease) -> str:
    lease.check()
    closure = execution_closure_sha256()
    if closure != lease.expected_closure_sha256:
        raise ContractError("H28 execution closure drifted")
    return closure


def _sidecar_state() -> tuple[tuple[bytes, dict[str, Any], str], tuple[bytes, dict[str, Any], str] | None] | None:
    try:
        metadata = SIDE_ROOT.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ContractError("physical-return sidecar cannot be inspected") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o077:
        raise ContractError("physical-return sidecar is not private and direct")
    try:
        names = {entry.name for entry in SIDE_ROOT.iterdir()}
    except OSError as exc:
        raise ContractError("physical-return sidecar cannot be enumerated") from exc
    if names not in ({INTENT_NAME}, {INTENT_NAME, OBSERVATION_INTENT_NAME}):
        raise ContractError("physical-return sidecar has a collision or extra entry")
    raw, value = _read_json(SIDE_ROOT / INTENT_NAME, "physical-return intent")
    if type(value) is not dict or set(value) != INTENT_KEYS or value["schema"] != INTENT_SCHEMA or value["capability"] != CAPABILITY or value["runId"] != RUN_ID or value["manifestSha256"] != MANIFEST_SHA256 or value["terminalSha256"] != TERMINAL_SHA256:
        raise ContractError("physical-return intent identity changed")
    for key in ("currentReviewSha256", "executionClosureSha256", "approvalSha256"):
        if re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            raise ContractError("physical-return intent digest is invalid")
    physical = (raw, value, _sha(raw))
    observation = None
    if OBSERVATION_INTENT_NAME in names:
        raw, value = _read_json(SIDE_ROOT / OBSERVATION_INTENT_NAME, "Native observation intent")
        if type(value) is not dict or set(value) != OBSERVATION_KEYS or value["schema"] != OBSERVATION_SCHEMA or value["capability"] != CAPABILITY or value["runId"] != RUN_ID or value["manifestSha256"] != MANIFEST_SHA256 or value["terminalSha256"] != TERMINAL_SHA256 or value["physicalSystemReturnIntentSha256"] != physical[2] or value["operatorAttended"] is not True or value["physicalSystemReturnConfirmed"] is not True:
            raise ContractError("Native observation intent identity changed")
        for key in ("currentReviewSha256", "executionClosureSha256"):
            if re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
                raise ContractError("Native observation intent digest is invalid")
        observation = (raw, value, _sha(raw))
    return physical, observation


def _publish_intent(value: dict[str, Any]) -> str:
    if _sidecar_state() is not None:
        raise ContractError("physical-return intent was already reserved")
    parent = SIDE_ROOT.parent
    try:
        metadata = parent.lstat()
    except OSError as exc:
        raise ContractError("physical-return sidecar parent is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o077:
        raise ContractError("physical-return sidecar parent is not private")
    try:
        SIDE_ROOT.mkdir(mode=0o700, parents=False)
        owner._fsync_directory(parent)
    except FileExistsError as exc:
        raise ContractError("physical-return intent was already reserved") from exc
    raw, path = owner.canonical_json(value), SIDE_ROOT / INTENT_NAME
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(fd, raw) != len(raw):
                raise ContractError("physical-return intent short write")
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise ContractError("physical-return intent publication failed") from exc
    owner._fsync_directory(SIDE_ROOT)
    return _sha(raw)


def _publish_observation_intent(value: dict[str, Any]) -> str:
    state = _sidecar_state()
    if state is None or state[1] is not None:
        raise ContractError("Native observation intent was already reserved or physical intent is absent")
    raw = owner.canonical_json(value)
    path = SIDE_ROOT / OBSERVATION_INTENT_NAME
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(fd, raw) != len(raw):
                raise ContractError("Native observation intent short write")
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise ContractError("Native observation intent publication failed") from exc
    owner._fsync_directory(SIDE_ROOT)
    return _sha(raw)


def _approval_token(review_sha256: str, closure_sha256: str) -> str:
    binding = {"capability": CAPABILITY, "runId": RUN_ID, "manifestSha256": MANIFEST_SHA256, "terminalSha256": TERMINAL_SHA256, "currentReviewSha256": review_sha256, "executionClosureSha256": closure_sha256}
    return APPROVAL_PREFIX + _json_sha(binding)


def _require_intent_binding(intent, review_sha256: str, closure_sha256: str) -> None:
    if intent is not None:
        value = intent[1]
        if value["currentReviewSha256"] != review_sha256 or value["executionClosureSha256"] != closure_sha256 or value["approvalSha256"] != _sha(_approval_token(review_sha256, closure_sha256).encode("ascii")):
            raise ContractError("physical-return intent does not bind current review")


def _require_observation_binding(observation, physical_sha: str | None, review_sha: str, closure_sha: str) -> None:
    if observation is not None:
        value = observation[1]
        if physical_sha is None or value["physicalSystemReturnIntentSha256"] != physical_sha or value["currentReviewSha256"] != review_sha or value["executionClosureSha256"] != closure_sha:
            raise ContractError("Native observation intent does not bind current state")


@dataclass
class State:
    manifest_raw: bytes
    manifest: dict[str, Any]
    run_directory: Path
    records: dict[str, dict[str, Any]]
    review_sha256: str
    closure_sha256: str
    intent: tuple[bytes, dict[str, Any], str] | None
    observation: tuple[bytes, dict[str, Any], str] | None


def _state(*, require_active: bool, reject_intent: bool = False) -> State:
    manifest_raw, manifest = _load_manifest()
    run_directory, records = _load_records(manifest)
    _require_guards(manifest, active=require_active)
    _, _, review_sha, closure = _load_current_review()
    sidecar = _sidecar_state()
    intent = None if sidecar is None else sidecar[0]
    observation = None if sidecar is None else sidecar[1]
    _require_intent_binding(intent, review_sha, closure)
    _require_observation_binding(observation, None if intent is None else intent[2], review_sha, closure)
    if reject_intent and intent is not None:
        raise ContractError("physical-return intent already exists")
    return State(manifest_raw, manifest, run_directory, records, review_sha, closure, intent, observation)


def _recheck(state: State, lease: ReviewLease, *, active: bool) -> State:
    manifest_raw, manifest = _load_manifest()
    if manifest_raw != state.manifest_raw or manifest != state.manifest:
        raise ContractError("fixed H28 manifest changed")
    run_directory, records = _load_records(manifest)
    if run_directory != state.run_directory or records != state.records:
        raise ContractError("fixed H28 journal changed")
    _require_guards(manifest, active=active)
    _, _, review_sha, closure = _load_current_review()
    if review_sha != state.review_sha256 or closure != state.closure_sha256:
        raise ContractError("current physical-return review or closure changed")
    sidecar = _sidecar_state()
    intent = None if sidecar is None else sidecar[0]
    observation = None if sidecar is None else sidecar[1]
    _require_intent_binding(intent, review_sha, closure)
    _require_observation_binding(observation, None if intent is None else intent[2], review_sha, closure)
    return State(manifest_raw, manifest, run_directory, records, review_sha, closure, intent, observation)


def prepare() -> str:
    state = _state(require_active=True, reject_intent=True)
    if RECOVERY_NAME in state.records:
        raise ContractError("H28 recovery closure already exists")
    return _approval_token(state.review_sha256, state.closure_sha256)


def authorize(approval: str) -> str:
    if type(approval) is not str:
        raise ContractError("approval token is invalid")
    state = _state(require_active=True, reject_intent=True)
    if RECOVERY_NAME in state.records or approval != _approval_token(state.review_sha256, state.closure_sha256):
        raise ContractError("approval token does not bind fixed H28 state")
    lease = ReviewLease(state.review_sha256, state.closure_sha256)
    try:
        _require_closure(lease)
        state = _recheck(state, lease, active=True)
        if state.intent is not None:
            raise ContractError("physical-return intent was already reserved")
        intent = {"schema": INTENT_SCHEMA, "capability": CAPABILITY, "runId": RUN_ID, "manifestSha256": MANIFEST_SHA256, "terminalSha256": TERMINAL_SHA256, "currentReviewSha256": state.review_sha256, "executionClosureSha256": state.closure_sha256, "approvalSha256": _sha(approval.encode("ascii"))}
        intent_sha = _publish_intent(intent)
        _require_closure(lease)
        state = _recheck(state, lease, active=True)
        if state.intent is None or state.intent[2] != intent_sha or state.observation is not None:
            raise ContractError("published physical-return intent is not exact")
        print(INSTRUCTION)
        return INSTRUCTION
    finally:
        lease.close()


def _snapshot(value: Any, manifest: dict[str, Any], review_sha: str) -> owner.Snapshot:
    if not isinstance(value, owner.Snapshot):
        raise ContractError("Native observation returned the wrong snapshot type")
    try:
        value.validate()
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    if BOOT_ID_RE.fullmatch(value.boot_id) is None or value.healthy is not True or value.recovery_available is not True or value.recovery_evidence_sha256 != review_sha or value.fresh_state_observed is not False or value.fresh_state_absent is not False or value.other_targets_untouched is not True or (value.version, value.build) != (manifest["rollback"]["version"], manifest["rollback"]["build"]):
        raise ContractError("fresh V2321 recovery snapshot is not exact")
    return value


def _payload(snapshot: owner.Snapshot, intent_sha: str, observation_sha: str, review_sha: str, closure: str) -> dict[str, Any]:
    recovered = snapshot.payload()
    return {"schema": SCHEMA, "decision": "PHYSICAL_SYSTEM_RETURN_CONFIRMED_V2321_HEALTHY", "candidateReplay": False, "rollbackReplay": False, "originalTwrpReturnOutcome": "UNPROVED", "physicalSystemReturnConfirmed": True, "hostRecoveryCommandCount": 0, "bootWriteCount": 0, "physicalSystemReturnIntentSha256": intent_sha, "observationIntentSha256": observation_sha, "currentReviewSha256": review_sha, "executionClosureSha256": closure, "recoveredSnapshot": recovered, "recoveredSnapshotSha256": _json_sha(recovered)}


def _validate_payload(payload: Any, manifest: dict[str, Any], intent_sha: str, observation_sha: str, review_sha: str, closure: str) -> None:
    if type(payload) is not dict or set(payload) != PAYLOAD_KEYS or payload["schema"] != SCHEMA or payload["decision"] != "PHYSICAL_SYSTEM_RETURN_CONFIRMED_V2321_HEALTHY" or payload["candidateReplay"] is not False or payload["rollbackReplay"] is not False or payload["originalTwrpReturnOutcome"] != "UNPROVED" or payload["physicalSystemReturnConfirmed"] is not True or type(payload["hostRecoveryCommandCount"]) is not int or payload["hostRecoveryCommandCount"] != 0 or type(payload["bootWriteCount"]) is not int or payload["bootWriteCount"] != 0 or payload["physicalSystemReturnIntentSha256"] != intent_sha or payload["observationIntentSha256"] != observation_sha or payload["currentReviewSha256"] != review_sha or payload["executionClosureSha256"] != closure or payload["recoveredSnapshotSha256"] != _json_sha(payload["recoveredSnapshot"]):
        raise ContractError("physical-return recovery payload is invalid")
    item = payload["recoveredSnapshot"]
    if type(item) is not dict or set(item) != SNAPSHOT_KEYS:
        raise ContractError("physical-return snapshot fields mismatch")
    try:
        recovered = owner.Snapshot(target_evidence_sha256=item["targetEvidenceSha256"], boot_id=item["bootId"], version=item["version"], build=item["build"], healthy=item["healthy"], recovery_available=item["recoveryAvailable"], recovery_evidence_sha256=item["recoveryEvidenceSha256"], fresh_state_observed=item["freshStateObserved"], fresh_state_absent=item["freshStateAbsent"], other_targets_untouched=item["otherTargetsUntouched"], receipt_sha256=item["receiptSha256"])
    except KeyError as exc:
        raise ContractError("physical-return snapshot fields mismatch") from exc
    _snapshot(recovered, manifest, review_sha)


def _existing_recovery(state: State, intent_sha: str, lease: ReviewLease) -> dict[str, Any] | None:
    record = state.records.get(RECOVERY_NAME)
    if record is None:
        return None
    if record.get("schema") != owner.RECORD_SCHEMA or record.get("kind") != owner.RECORD_KINDS[RECOVERY_NAME] or record.get("manifestSha256") != MANIFEST_SHA256:
        raise ContractError("existing H28 recovery closure envelope changed")
    if state.observation is None:
        raise ContractError("recovery closure has no observation intent")
    _require_closure(lease)
    _validate_payload(record.get("payload"), state.manifest, intent_sha, state.observation[2], state.review_sha256, state.closure_sha256)
    try:
        owner._active_guard(state.manifest)[0].lstat()
    except FileNotFoundError:
        _require_guards(state.manifest, active=False)
        return record["payload"]
    except OSError as exc:
        raise ContractError("active guard cannot be inspected") from exc
    raise ContractError("recovery closure exists while active guard remains; park")


def _readback_recovery(state: State, payload: dict[str, Any], intent_sha: str, observation_sha: str, lease: ReviewLease) -> None:
    run_directory, records = _load_records(state.manifest)
    expected = owner._record(owner.RECORD_KINDS[RECOVERY_NAME], MANIFEST_SHA256, payload)
    record = records.get(RECOVERY_NAME)
    if run_directory != state.run_directory or record != expected or _json_sha(record) != _json_sha(expected):
        raise ContractError("published H28 recovery record readback changed")
    _require_closure(lease)
    _validate_payload(record["payload"], state.manifest, intent_sha, observation_sha, state.review_sha256, state.closure_sha256)


def finalize(*, operator_attended: bool, physical_system_return_confirmed: bool) -> dict[str, Any]:
    if operator_attended is not True or physical_system_return_confirmed is not True:
        raise ContractError("both physical-return operator flags are required")
    state = _state(require_active=False)
    if state.intent is None:
        raise ContractError("physical-return intent is not present")
    if state.observation is not None and RECOVERY_NAME not in state.records:
        raise ContractError("Native observation intent is consumed; park")
    intent_sha = state.intent[2]
    lease = ReviewLease(state.review_sha256, state.closure_sha256)
    try:
        _require_closure(lease)
        current = _recheck(state, lease, active=False)
        if current.intent is None or current.intent[2] != intent_sha:
            raise ContractError("physical-return intent changed")
        if current.observation is not None and RECOVERY_NAME not in current.records:
            raise ContractError("Native observation intent is consumed; park")
        if RECOVERY_NAME in current.records:
            result = _existing_recovery(current, intent_sha, lease)
            if result is None:
                raise ContractError("existing recovery closure is unavailable")
            return result
        _require_guards(current.manifest, active=True)
        _require_closure(lease)
        observation_value = {"schema": OBSERVATION_SCHEMA, "capability": CAPABILITY, "runId": RUN_ID, "manifestSha256": MANIFEST_SHA256, "terminalSha256": TERMINAL_SHA256, "physicalSystemReturnIntentSha256": intent_sha, "currentReviewSha256": current.review_sha256, "executionClosureSha256": current.closure_sha256, "operatorAttended": True, "physicalSystemReturnConfirmed": True}
        observation_sha = _publish_observation_intent(observation_value)
        _require_closure(lease)
        current = _recheck(current, lease, active=True)
        if current.observation is None or current.observation[2] != observation_sha:
            raise ContractError("published Native observation intent is not exact")
        bound = dict(current.manifest)
        qualification = dict(bound["qualification"])
        qualification["review"] = {"path": str(CURRENT_REVIEW_PATH), "size": lease.before.st_size, "sha256": current.review_sha256}
        bound["qualification"] = qualification
        snapshot = owner._live_backend(bound, "physical-system-return").observe(bound["rollback"], bound["qualification"]["freshState"], require_fresh_state=False, timeout_sec=bound["timeouts"]["healthSec"])
        _require_closure(lease)
        _snapshot(snapshot, current.manifest, current.review_sha256)
        payload = _payload(snapshot, intent_sha, observation_sha, current.review_sha256, current.closure_sha256)
        _validate_payload(payload, current.manifest, intent_sha, observation_sha, current.review_sha256, current.closure_sha256)
        _require_closure(lease); _require_guards(current.manifest, active=True)
        owner.publish_record(current.run_directory, RECOVERY_NAME, owner._record(owner.RECORD_KINDS[RECOVERY_NAME], MANIFEST_SHA256, payload))
        _require_closure(lease); _require_guards(current.manifest, active=True)
        _readback_recovery(current, payload, intent_sha, observation_sha, lease)
        loaded_intent = _sidecar_state()
        if loaded_intent is None or loaded_intent[0][2] != intent_sha or loaded_intent[1] is None or loaded_intent[1][2] != observation_sha:
            raise ContractError("physical-return intent changed after publication")
        _require_closure(lease); _require_guards(current.manifest, active=True)
        owner._release_active_guard(current.manifest)
        _require_closure(lease); _require_guards(current.manifest, active=False)
        return payload
    finally:
        lease.close()


def _require_launch_contract() -> None:
    try:
        _require_pre_import_launch_contract()
    except _LaunchContractError as exc:
        raise ContractError(str(exc)) from exc
    def direct_file(path: str, label: str) -> None:
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise ContractError(f"{label} cannot be inspected") from exc
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o022:
            raise ContractError(f"{label} identity is not exact")
    direct_file(FIXED_SCRIPT, "fixed reconciler")
    direct_file(FIXED_OWNER, "fixed owner")
    canonical_name = "a90_boot_only_f1_minimal_v1"
    if sys.modules.get(canonical_name) is not owner or getattr(owner, "__file__", None) != FIXED_OWNER:
        raise ContractError("fixed owner module identity is not exact")
    for name, module in tuple(sys.modules.items()):
        if name != canonical_name and module is owner:
            raise ContractError("duplicate owner module alias")
        module_file = getattr(module, "__file__", None)
        if name != canonical_name and isinstance(module_file, str):
            try:
                if str(Path(module_file).resolve()) == FIXED_OWNER:
                    raise ContractError("foreign owner module alias")
            except OSError:
                raise ContractError("foreign owner module alias")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="action", required=True)
    subparsers.add_parser("prepare")
    authorize = subparsers.add_parser("authorize"); authorize.add_argument("--approval", required=True)
    finalize = subparsers.add_parser("finalize"); finalize.add_argument("--operator-attended", action="store_true"); finalize.add_argument("--physical-system-return-confirmed", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    _require_launch_contract()
    args = parser().parse_args(argv)
    if args.action == "prepare":
        print(prepare())
    elif args.action == "authorize":
        authorize(args.approval)
    else:
        print(json.dumps(finalize(operator_attended=args.operator_attended, physical_system_return_confirmed=args.physical_system_return_confirmed), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, owner.ContractError) as exc:
        print(f"A90_H28_PHYSICAL_SYSTEM_RETURN_RECONCILE_V1 NO_GO: {exc}", file=os.sys.stderr)
        raise SystemExit(2) from exc
