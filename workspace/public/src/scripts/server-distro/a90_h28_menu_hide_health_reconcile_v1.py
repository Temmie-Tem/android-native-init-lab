#!/usr/bin/env python3
"""One-shot terminal-only A90 H28 health reconciliation with menu quiescence.

This is a new namespace after the consumed slow-input observer.  It has one
fixed read-only session: durable intent, exact USB/bridge binding, one raw
``hide`` line, then boot-id-first slow-input health reads.  It never transfers
an image or requests a reboot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FIXED_PYTHON = "/usr/bin/python3.14"
FIXED_CWD = "/home/temmie/dev/android-native-init-lab"
FIXED_SCRIPT = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro/a90_h28_menu_hide_health_reconcile_v1.py"
FIXED_OWNER = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
FIXED_ADAPTER = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro/a90_boot_only_f1_adapter_v1.py"
FIXED_PRIOR = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro/a90_h28_physical_system_return_reconcile_v1.py"
FIXED_SCRIPT_DIR = f"{FIXED_CWD}/workspace/public/src/scripts/server-distro"


class _LaunchContractError(RuntimeError):
    pass


def _pre_import_launch_contract() -> None:
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
        raise _LaunchContractError("fixed menu-hide pre-import launch contract is not exact")
    for path, label in (
        (FIXED_SCRIPT, "fixed menu-hide reconciler"),
        (FIXED_OWNER, "fixed owner"),
        (FIXED_ADAPTER, "fixed adapter"),
        (FIXED_PRIOR, "fixed physical reconciler"),
    ):
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
        _pre_import_launch_contract()
    except _LaunchContractError as exc:
        print(f"A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


import a90_boot_only_f1_adapter_v1 as adapter
import a90_boot_only_f1_minimal_v1 as owner
import a90_h28_physical_system_return_reconcile_v1 as prior


CAPABILITY = "A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1"
SCHEMA = "a90-h28-menu-hide-health-reconciliation-v1"
INTENT_SCHEMA = "a90-h28-menu-hide-health-observation-intent-v1"
RUN_ID = "a90-h28-f1-20260821-01"
MANIFEST_PATH = owner.REPO_ROOT / "workspace/private/manifests/a90-h28-f1-20260821-01.json"
MANIFEST_SHA256 = "e708e45e9cd925229682c76ad3b6359426f2e636eb26eb111ea54e9843e8d1c2"
TERMINAL_SHA256 = "400a6fe75ea54a738777092f828dede4d7b801bd3fbd8db29baddf26878c4f01"
PRIOR_PHYSICAL_INTENT_SHA256 = "19377bc18714c7b2b698665a8c9ff96573d3c1fdfb028efba5b86f6b2def9f66"
PRIOR_OBSERVATION_INTENT_SHA256 = "8f401590bca71575258a2e3d45e1bee6c55fd4e8eeff4c22012fc25f559d05be"
PRIOR_SLOW_HEALTH_INTENT_SHA256 = "63c26238f332a7bc1bad37a3950d5dc05f383c50a4a09ecfe57e2a119a390ac4"
CURRENT_REVIEW_PATH = owner.REPO_ROOT / "docs/reports/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_INDEPENDENT_REVIEW_2026-08-21.json"
SIDE_ROOT = owner.REPO_ROOT / "workspace/private/runs/a90-h28-menu-hide-health-v1"
PRIOR_SIDE_ROOT = owner.REPO_ROOT / "workspace/private/runs/a90-h28-physical-system-return-v1"
PRIOR_SLOW_SIDE_ROOT = owner.REPO_ROOT / "workspace/private/runs/a90-h28-slow-health-reconcile-v1"
PRIOR_SLOW_LOG_DIRECTORY = owner.RUN_ROOT / "a90-h28-f1-20260821-01-slow-health-1-logs"
INTENT_NAME = "10-menu-hide-health-observation-intent.json"
RECOVERY_NAME = "41-recovery-closed.json"
PRIOR_SLOW_INTENT_NAME = "10-slow-health-observation-intent.json"
HEALTH_TIMEOUT_SEC = 300
MENU_SETTLE_SEC = 3.0
APPROVAL_PREFIX = "A90-H28-MENU-HIDE-HEALTH-V1-APPROVE:"
BOOT_ID_RE = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
VERSION = owner.V2321_ROLLBACK_VERSION
BUILD = owner.V2321_ROLLBACK_BUILD
BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 54321

PRIOR_SLOW_LOG_HASHES = {
    "001-usb-inventory.stderr": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "001-usb-inventory.stdout": (1264, "c3d1970d8cc59051a00f8ff9f7a595878e1120c77c602818947b84bab5933aab"),
    "002-bridge-preflight.stderr": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "002-bridge-preflight.stdout": (2845, "9454cb13d936dd16ababf5347ece41699cb84e3d6fb267f2b7dd8452775af6d5"),
    "003-version.stderr": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "003-version.stdout": (755, "102e72e05f94d7dd693ed817457ae366dbc1526526f8cabb7d5567126898a6f7"),
    "004-selftest.stderr": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "004-selftest.stdout": (569, "0c6c4aa5ffd5c8c0925ab2c172ae8e3ac585799c233943e4ba812157924edfea"),
    "005-status.stderr": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "005-status.stdout": (3123, "f096438cc1d92b2032d0e316f92741562eff9e6b013690dd108933b7789202c5"),
    "006-boot-id.stderr": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    "006-boot-id.stdout": (560, "864e0886dd5d9923a2e8bb9bf3e026b5c1e610b90ea26a09f869a5388679ea06"),
}
PRIOR_SLOW_LOG_SET_SHA256 = hashlib.sha256(
    owner.canonical_json(PRIOR_SLOW_LOG_HASHES)
).hexdigest()

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
REVIEW_SCHEMA = "a90-h28-menu-hide-health-reconciliation-independent-review-v1"
REVIEW_KEYS = {
    "schema", "capability", "runId", "manifestSha256", "terminalSha256",
    "priorPhysicalIntentSha256", "priorObservationIntentSha256",
    "priorSlowHealthIntentSha256", "priorSlowLogSetSha256", "executionClosureSha256",
    "verdict", "findings", "contacts", "liveAuthority",
}
FINDING_KEYS = {"high", "medium", "low"}
CONTACT_KEYS = {"device", "dev", "usb", "network", "workspacePrivate", "otherTargets", "writes"}
INTENT_KEYS = {
    "schema", "capability", "runId", "manifestSha256", "terminalSha256",
    "priorPhysicalIntentSha256", "priorObservationIntentSha256",
    "priorSlowHealthIntentSha256", "priorSlowLogSetSha256", "currentReviewSha256",
    "executionClosureSha256", "approvalSha256",
}
PAYLOAD_KEYS = {
    "schema", "decision", "priorPhysicalIntentSha256", "priorObservationIntentSha256",
    "priorSlowHealthIntentSha256", "priorSlowLogSetSha256", "menuHideIntentSha256",
    "menuHideReceiptSha256", "priorObserverOutcome", "candidateReplay", "rollbackReplay",
    "hostRecoveryCommandCount", "deviceEffectCount", "bootWriteCount", "rebootCount",
    "physicalActionCount", "sameBoot", "finalBootId", "currentReviewSha256", "executionClosureSha256",
    "recoveredSnapshot", "recoveredSnapshotSha256",
}
SNAPSHOT_KEYS = {
    "targetEvidenceSha256", "bootId", "version", "build", "healthy", "recoveryAvailable",
    "recoveryEvidenceSha256", "freshStateObserved", "freshStateAbsent", "otherTargetsUntouched",
    "receiptSha256",
}
INCIDENT_NAMES = tuple(owner.ROLLBACK_PATH)


class ContractError(RuntimeError):
    """Any fixed-input, parser, launch, transport, or crash-boundary failure."""


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
        raise ContractError(f"{label} unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o077:
        raise ContractError(f"{label} identity is not exact")


def execution_closure_sha256() -> str:
    source_rels = tuple(sorted(set(owner.EXECUTION_SOURCE_RELS) | set(prior.EXECUTION_SOURCE_RELS) | {
        "workspace/public/src/scripts/server-distro/a90_h28_menu_hide_health_reconcile_v1.py",
        "docs/plans/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_DESIGN_2026-08-21.md",
        "docs/plans/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_REVIEW_HANDOFF_2026-08-21.md",
        "docs/reports/A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_H0_2026-08-21.md",
        "docs/reports/A90_H28_SLOW_HEALTH_BOOT_ID_BUSY_NO_PROOF_2026-08-21.md",
        "docs/reports/A90_H28_PHYSICAL_RETURN_SELFTEST_TRANSPORT_NO_PROOF_2026-08-21.md",
        "AGENTS.md", "docs/operations/targets/A90_TARGET_CONTRACT.md", "GOAL_A90.md",
    }))
    digest = hashlib.sha256()
    for relative in source_rels:
        raw = (owner.REPO_ROOT / relative).read_bytes()
        digest.update(relative.encode("utf-8")); digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii")); digest.update(b"\0")
        digest.update(_sha(raw).encode("ascii")); digest.update(b"\0")
    return digest.hexdigest()


def _load_manifest() -> tuple[bytes, dict[str, Any]]:
    raw, value = _read_json(MANIFEST_PATH, "fixed H28 manifest")
    if _sha(raw) != MANIFEST_SHA256:
        raise ContractError("fixed H28 manifest changed")
    try:
        manifest = owner.validate_manifest(value)
        prior._verify_historical_qualification_binding(manifest)
    except (owner.ContractError, prior.ContractError) as exc:
        raise ContractError(str(exc)) from exc
    if manifest["runId"] != RUN_ID or manifest["rollback"]["sha256"] != owner.V2321_ROLLBACK_SHA256:
        raise ContractError("fixed H28 manifest identity changed")
    return raw, manifest


def _load_records(manifest: dict[str, Any]) -> tuple[Path, dict[str, dict[str, Any]]]:
    _private_dir(owner.RUN_ROOT, "fixed A90 run root")
    run_directory = owner.RUN_ROOT / RUN_ID
    _private_dir(run_directory, "fixed H28 run directory")
    try:
        records = owner.read_records(run_directory)
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    allowed = (set(INCIDENT_NAMES), set(INCIDENT_NAMES) | {RECOVERY_NAME})
    if set(records) not in allowed:
        raise ContractError("H28 journal has an unexpected record")
    for name, expected in INCIDENT_RECORD_SHA256.items():
        record = records.get(name)
        if type(record) is not dict or _json_sha(record) != expected or record.get("manifestSha256") != MANIFEST_SHA256:
            raise ContractError(f"fixed H28 record changed: {name}")
    terminal = records["40-terminal.json"]["payload"]
    if terminal.get("schema") != owner.RESULT_SCHEMA or terminal.get("terminal") != "RECOVERY_REQUIRED" or terminal.get("reason") != "ROLLBACK_HEALTH_UNPROVED" or terminal.get("snapshot") is not None or terminal.get("candidateReplay") is not False:
        raise ContractError("fixed H28 terminal changed")
    if records["20-candidate-intent.json"]["payload"] != {"sha256": manifest["candidate"]["sha256"]} or records["30-rollback-intent.json"]["payload"] != {"sha256": manifest["rollback"]["sha256"]}:
        raise ContractError("fixed transfer intent changed")
    if (
        MANIFEST_SHA256 == prior.HISTORICAL_H28_MANIFEST_SHA256
        and manifest["candidate"]["sha256"] == prior.HISTORICAL_H28_CANDIDATE_SHA256
        and RECOVERY_NAME in records
    ):
        prior._historical_recovery_payload(records[RECOVERY_NAME])
    return run_directory, records


def _require_guards(manifest: dict[str, Any], *, active: bool = True) -> None:
    active_path, active_raw = owner._active_guard(manifest)
    candidate_path, candidate_raw = owner._candidate_guard(manifest)
    if active:
        try:
            current = owner._verify_input({"path": str(active_path), "size": len(active_raw), "sha256": _sha(active_raw)}, "active guard")
        except owner.ContractError as exc:
            raise ContractError(str(exc)) from exc
        if current != active_raw or _sha(current) != ACTIVE_GUARD_SHA256:
            raise ContractError("active guard identity changed")
    try:
        current = owner._verify_input({"path": str(candidate_path), "size": len(candidate_raw), "sha256": _sha(candidate_raw)}, "candidate guard")
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    if current != candidate_raw or _sha(current) != CANDIDATE_GUARD_SHA256:
        raise ContractError("candidate guard identity changed")


def _verify_physical_sidecar() -> None:
    _private_dir(PRIOR_SIDE_ROOT, "prior H28 physical sidecar")
    try:
        names = {entry.name for entry in PRIOR_SIDE_ROOT.iterdir()}
    except OSError as exc:
        raise ContractError("prior physical sidecar cannot be enumerated") from exc
    if names != {prior.INTENT_NAME, prior.OBSERVATION_INTENT_NAME}:
        raise ContractError("prior physical sidecar is not exact")
    expected = {prior.INTENT_NAME: PRIOR_PHYSICAL_INTENT_SHA256, prior.OBSERVATION_INTENT_NAME: PRIOR_OBSERVATION_INTENT_SHA256}
    values: dict[str, Any] = {}
    for name, digest in expected.items():
        raw, value = _read_json(PRIOR_SIDE_ROOT / name, f"prior {name}")
        if _sha(raw) != digest or type(value) is not dict:
            raise ContractError(f"prior {name} changed")
        values[name] = value
    physical = values[prior.INTENT_NAME]
    if set(physical) != prior.INTENT_KEYS or physical["schema"] != prior.INTENT_SCHEMA or physical["capability"] != prior.CAPABILITY or physical["runId"] != RUN_ID or physical["manifestSha256"] != MANIFEST_SHA256 or physical["terminalSha256"] != TERMINAL_SHA256:
        raise ContractError("prior physical intent fields changed")
    observation = values[prior.OBSERVATION_INTENT_NAME]
    if set(observation) != prior.OBSERVATION_KEYS or observation["physicalSystemReturnIntentSha256"] != PRIOR_PHYSICAL_INTENT_SHA256 or observation["operatorAttended"] is not True or observation["physicalSystemReturnConfirmed"] is not True:
        raise ContractError("prior physical observation fields changed")


def _verify_prior_slow_intent() -> None:
    _private_dir(PRIOR_SLOW_SIDE_ROOT, "prior slow-health sidecar")
    try:
        names = {entry.name for entry in PRIOR_SLOW_SIDE_ROOT.iterdir()}
    except OSError as exc:
        raise ContractError("prior slow-health sidecar cannot be enumerated") from exc
    if names != {PRIOR_SLOW_INTENT_NAME}:
        raise ContractError("prior slow-health sidecar is not exact")
    raw, value = _read_json(PRIOR_SLOW_SIDE_ROOT / PRIOR_SLOW_INTENT_NAME, "prior slow-health intent")
    if _sha(raw) != PRIOR_SLOW_HEALTH_INTENT_SHA256 or type(value) is not dict:
        raise ContractError("prior slow-health intent changed")
    required = {"schema", "capability", "runId", "manifestSha256", "terminalSha256", "priorPhysicalIntentSha256", "priorObservationIntentSha256", "currentReviewSha256", "executionClosureSha256", "approvalSha256"}
    if set(value) != required or value["schema"] != "a90-h28-slow-health-observation-intent-v1" or value["capability"] != "A90_H28_SLOW_HEALTH_RECONCILIATION_V1" or value["runId"] != RUN_ID or value["manifestSha256"] != MANIFEST_SHA256 or value["terminalSha256"] != TERMINAL_SHA256 or value["priorPhysicalIntentSha256"] != PRIOR_PHYSICAL_INTENT_SHA256 or value["priorObservationIntentSha256"] != PRIOR_OBSERVATION_INTENT_SHA256 or any(type(value[key]) is not str or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None for key in ("currentReviewSha256", "executionClosureSha256", "approvalSha256")):
        raise ContractError("prior slow-health intent fields changed")


def _verify_prior_slow_logs() -> None:
    _private_dir(PRIOR_SLOW_LOG_DIRECTORY, "prior slow-health log directory")
    try:
        names = {entry.name for entry in PRIOR_SLOW_LOG_DIRECTORY.iterdir()}
    except OSError as exc:
        raise ContractError("prior slow-health logs cannot be enumerated") from exc
    if names != set(PRIOR_SLOW_LOG_HASHES):
        raise ContractError("prior slow-health log inventory changed")
    for name, (size, digest) in PRIOR_SLOW_LOG_HASHES.items():
        path = PRIOR_SLOW_LOG_DIRECTORY / name
        try:
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o022 or metadata.st_size != size:
                raise ContractError(f"prior slow-health log {name} identity changed")
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                current = os.fstat(fd)
                raw = os.pread(fd, size, 0)
                if (current.st_dev, current.st_ino, current.st_size) != (metadata.st_dev, metadata.st_ino, size) or len(raw) != size or os.pread(fd, 1, size) or _sha(raw) != digest:
                    raise ContractError(f"prior slow-health log {name} changed")
            finally:
                os.close(fd)
        except OSError as exc:
            raise ContractError(f"prior slow-health log {name} cannot be read") from exc


def _validate_review(value: Any, closure: str) -> None:
    if type(value) is not dict or set(value) != REVIEW_KEYS:
        raise ContractError("menu-hide review fields mismatch")
    if value["schema"] != REVIEW_SCHEMA or value["capability"] != CAPABILITY or value["runId"] != RUN_ID or value["manifestSha256"] != MANIFEST_SHA256 or value["terminalSha256"] != TERMINAL_SHA256 or value["priorPhysicalIntentSha256"] != PRIOR_PHYSICAL_INTENT_SHA256 or value["priorObservationIntentSha256"] != PRIOR_OBSERVATION_INTENT_SHA256 or value["priorSlowHealthIntentSha256"] != PRIOR_SLOW_HEALTH_INTENT_SHA256 or value["priorSlowLogSetSha256"] != PRIOR_SLOW_LOG_SET_SHA256 or value["executionClosureSha256"] != closure or value["verdict"] != "PASS_GO" or value["liveAuthority"] is not False:
        raise ContractError("menu-hide review identity or verdict is invalid")
    findings, contacts = value["findings"], value["contacts"]
    if type(findings) is not dict or set(findings) != FINDING_KEYS or any(type(findings[k]) is not list or findings[k] for k in FINDING_KEYS):
        raise ContractError("menu-hide review findings are invalid")
    if type(contacts) is not dict or set(contacts) != CONTACT_KEYS or any(type(v) is not int or v != 0 for v in contacts.values()):
        raise ContractError("menu-hide review contacts are invalid")


def _current_review() -> tuple[bytes, str, str]:
    raw, value = _read_json(CURRENT_REVIEW_PATH, "current menu-hide review")
    closure = execution_closure_sha256()
    _validate_review(value, closure)
    return raw, _sha(raw), closure


class ReviewLease:
    def __init__(self, digest: str, closure: str) -> None:
        try:
            before = CURRENT_REVIEW_PATH.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != os.getuid() or before.st_gid != os.getgid() or before.st_mode & 0o022:
                raise ContractError("current menu-hide review identity is invalid")
            self.fd = os.open(CURRENT_REVIEW_PATH, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as exc:
            raise ContractError("current menu-hide review cannot be opened") from exc
        self.before, self.digest, self.closure = before, digest, closure
        self.check()

    def check(self) -> None:
        current, pathname = os.fstat(self.fd), CURRENT_REVIEW_PATH.lstat()
        identity = (self.before.st_dev, self.before.st_ino, self.before.st_size)
        if (current.st_dev, current.st_ino, current.st_size) != identity or (pathname.st_dev, pathname.st_ino, pathname.st_size) != identity or current.st_nlink != 1 or pathname.st_nlink != 1 or current.st_mode & 0o022 or pathname.st_mode & 0o022:
            raise ContractError("current menu-hide review lease drifted")
        raw = os.pread(self.fd, current.st_size, 0)
        if len(raw) != current.st_size or _sha(raw) != self.digest:
            raise ContractError("current menu-hide review bytes changed")
        _validate_review(owner.parse_canonical(raw, "current menu-hide review"), self.closure)

    def close(self) -> None:
        if getattr(self, "fd", -1) >= 0:
            os.close(self.fd); self.fd = -1


def _require_closure(lease: ReviewLease) -> None:
    lease.check()
    if execution_closure_sha256() != lease.closure:
        raise ContractError("menu-hide execution closure drifted")


def _sidecar() -> tuple[bytes, dict[str, Any], str] | None:
    try:
        metadata = SIDE_ROOT.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ContractError("menu-hide sidecar unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_gid != os.getgid() or metadata.st_mode & 0o077:
        raise ContractError("menu-hide sidecar identity is not exact")
    try:
        names = {entry.name for entry in SIDE_ROOT.iterdir()}
    except OSError as exc:
        raise ContractError("menu-hide sidecar cannot be enumerated") from exc
    if names != {INTENT_NAME}:
        raise ContractError("menu-hide sidecar has an unexpected entry")
    raw, value = _read_json(SIDE_ROOT / INTENT_NAME, "menu-hide intent")
    if type(value) is not dict or set(value) != INTENT_KEYS or value["schema"] != INTENT_SCHEMA or value["capability"] != CAPABILITY or value["runId"] != RUN_ID or value["manifestSha256"] != MANIFEST_SHA256 or value["terminalSha256"] != TERMINAL_SHA256 or value["priorPhysicalIntentSha256"] != PRIOR_PHYSICAL_INTENT_SHA256 or value["priorObservationIntentSha256"] != PRIOR_OBSERVATION_INTENT_SHA256 or value["priorSlowHealthIntentSha256"] != PRIOR_SLOW_HEALTH_INTENT_SHA256 or value["priorSlowLogSetSha256"] != PRIOR_SLOW_LOG_SET_SHA256:
        raise ContractError("menu-hide intent identity changed")
    return raw, value, _sha(raw)


def _publish_intent(value: dict[str, Any]) -> str:
    if _sidecar() is not None:
        raise ContractError("menu-hide intent already exists")
    _private_dir(SIDE_ROOT.parent, "menu-hide sidecar parent")
    try:
        SIDE_ROOT.mkdir(mode=0o700, parents=False)
        owner._fsync_directory(SIDE_ROOT.parent)
    except FileExistsError as exc:
        raise ContractError("menu-hide sidecar collision") from exc
    raw = owner.canonical_json(value)
    try:
        fd = os.open(SIDE_ROOT / INTENT_NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(fd, raw) != len(raw):
                raise ContractError("menu-hide intent short write")
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise ContractError("menu-hide intent publication failed") from exc
    owner._fsync_directory(SIDE_ROOT)
    return _sha(raw)


def _approval_token(review_sha: str, closure: str) -> str:
    binding = {
        "capability": CAPABILITY, "runId": RUN_ID, "manifestSha256": MANIFEST_SHA256,
        "terminalSha256": TERMINAL_SHA256, "priorPhysicalIntentSha256": PRIOR_PHYSICAL_INTENT_SHA256,
        "priorObservationIntentSha256": PRIOR_OBSERVATION_INTENT_SHA256,
        "priorSlowHealthIntentSha256": PRIOR_SLOW_HEALTH_INTENT_SHA256,
        "priorSlowLogSetSha256": PRIOR_SLOW_LOG_SET_SHA256,
        "currentReviewSha256": review_sha, "executionClosureSha256": closure,
    }
    return APPROVAL_PREFIX + _json_sha(binding)


@dataclass
class State:
    manifest_raw: bytes
    manifest: dict[str, Any]
    run_directory: Path
    records: dict[str, dict[str, Any]]
    review_sha: str
    closure: str
    intent: tuple[bytes, dict[str, Any], str] | None


def _state(*, active: bool) -> State:
    manifest_raw, manifest = _load_manifest()
    run_directory, records = _load_records(manifest)
    _require_guards(manifest, active=active)
    _verify_physical_sidecar(); _verify_prior_slow_intent(); _verify_prior_slow_logs()
    intent = _sidecar()
    if (
        MANIFEST_SHA256 == prior.HISTORICAL_H28_MANIFEST_SHA256
        and manifest["candidate"]["sha256"] == prior.HISTORICAL_H28_CANDIDATE_SHA256
        and RECOVERY_NAME in records
    ):
        prior._historical_recovery_payload(records[RECOVERY_NAME])
        return State(
            manifest_raw,
            manifest,
            run_directory,
            records,
            prior.HISTORICAL_MENU_REVIEW_SHA256,
            prior.HISTORICAL_MENU_CLOSURE_SHA256,
            intent,
        )
    _, review_sha, closure = _current_review()
    if intent is not None and (intent[1]["currentReviewSha256"] != review_sha or intent[1]["executionClosureSha256"] != closure or intent[1]["approvalSha256"] != _sha(_approval_token(review_sha, closure).encode("ascii"))):
        raise ContractError("menu-hide intent is not bound to current review and closure")
    return State(manifest_raw, manifest, run_directory, records, review_sha, closure, intent)


def _recheck(state: State, lease: ReviewLease, *, active: bool) -> State:
    manifest_raw, manifest = _load_manifest()
    if (manifest_raw, manifest) != (state.manifest_raw, state.manifest):
        raise ContractError("fixed H28 manifest changed")
    run_directory, records = _load_records(manifest)
    if (run_directory, records) != (state.run_directory, state.records):
        raise ContractError("fixed H28 journal changed")
    _require_guards(manifest, active=active)
    _verify_physical_sidecar(); _verify_prior_slow_intent(); _verify_prior_slow_logs()
    _, review_sha, closure = _current_review()
    if (review_sha, closure) != (state.review_sha, state.closure):
        raise ContractError("current menu-hide review or closure changed")
    intent = _sidecar()
    if intent is not None and (intent[1]["currentReviewSha256"] != review_sha or intent[1]["executionClosureSha256"] != closure or intent[1]["approvalSha256"] != _sha(_approval_token(review_sha, closure).encode("ascii"))):
        raise ContractError("menu-hide intent binding changed")
    return State(manifest_raw, manifest, run_directory, records, review_sha, closure, intent)


def prepare() -> str:
    state = _state(active=True)
    if state.intent is not None or RECOVERY_NAME in state.records:
        raise ContractError("menu-hide capability is already consumed")
    return _approval_token(state.review_sha, state.closure)


def _write_log_pair(directory: Path, sequence: int, label: str, stdout: bytes, stderr: bytes) -> None:
    for suffix, raw in (("stdout", stdout), ("stderr", stderr)):
        path = directory / f"{sequence:03d}-{label}.{suffix}"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
        try:
            if os.write(fd, raw) != len(raw):
                raise ContractError("menu-hide receipt short write")
            os.fsync(fd)
        finally:
            os.close(fd)
    descriptor = os.open(directory, os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _raw_hide(runner: adapter.HostRunner, timeout_sec: int = 8) -> str:
    """Send exactly one unframed ``hide\n`` line through the fixed bridge."""
    runner.sequence += 1
    started = time.monotonic()
    stdout = bytearray()
    stderr = b""
    sent = False
    try:
        with socket.create_connection((BRIDGE_HOST, BRIDGE_PORT), timeout=timeout_sec) as sock:
            sock.settimeout(0.25)
            sock.sendall(b"hide\n")
            sent = True
            deadline = time.monotonic() + timeout_sec
            while time.monotonic() < deadline and len(stdout) <= adapter.MAX_OUTPUT_BYTES:
                try:
                    chunk = sock.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                stdout.extend(chunk)
                if any(marker in stdout for marker in (b"hide requested", b"a90:/#", b"[done]", b"[busy]", b"[err]")):
                    break
    except OSError as exc:
        stderr = str(exc).encode("utf-8", errors="replace")
    _write_log_pair(runner.log_directory, runner.sequence, "menu-hide", bytes(stdout), stderr)
    if not sent:
        raise ContractError("raw menu-hide line was not sent")
    if not stdout or len(stdout) > adapter.MAX_OUTPUT_BYTES or b"[busy]" in stdout or b"[err]" in stdout or b"auto menu active" in stdout or b"hide requested" not in stdout:
        raise ContractError("raw menu-hide receipt is not a successful quiescence receipt")
    receipt = {"line": "hide", "wireSha256": _sha(b"hide\n"), "sendCount": 1, "stdoutSha256": _sha(bytes(stdout)), "stderrSha256": _sha(stderr), "elapsedMs": int((time.monotonic() - started) * 1000)}
    return _json_sha(receipt)


def _settle_after_hide() -> None:
    """Honor the existing 3-second async-menu settle before the first read."""
    try:
        time.sleep(MENU_SETTLE_SEC)
    except BaseException as exc:
        raise ContractError("menu-hide settle was interrupted") from exc


@dataclass(frozen=True)
class Observation:
    snapshot: owner.Snapshot
    hide_receipt_sha256: str
    command_order: tuple[str, ...]
    final_boot_id: str
    same_boot: bool


class MenuHideObserver(adapter.FixedA90Adapter):
    def _a90ctl(self, label: str, command: list[str], timeout_sec: int = 15) -> dict[str, Any]:
        argv = (str(adapter.PYTHON), str(adapter.A90CTL), "--json", "--timeout", str(timeout_sec), "--input-mode", "slow", "--", *command)
        return {"request": list(command), "response": self._json_command(label, argv, timeout_sec)}

    def observe(self, expected: dict[str, Any], *, timeout_sec: int) -> Observation:
        deadline = time.monotonic() + timeout_sec
        usb_before = adapter._validate_usb_inventory(self.runner.run("usb-inventory-before", (str(adapter.LSUSB),), self._remaining(deadline, cap=10)))
        bridge = adapter._validate_bridge(self._json_command("bridge-preflight", (str(adapter.PYTHON), str(adapter.BRIDGE), "preflight", "--device", adapter.FIXED_SERIAL, "--device-glob", adapter.FIXED_SERIAL, "--pin-selected-realpath", "--json"), self._remaining(deadline, cap=10)))
        hide_receipt_sha = _raw_hide(self.runner, self._remaining(deadline, cap=8))
        _settle_after_hide()
        receipts: dict[str, Any] = {}
        order: list[str] = ["hide"]
        receipts["bootId"] = self._a90ctl("boot-id", ["cat", "/proc/sys/kernel/random/boot_id"], self._remaining(deadline, cap=15)); order.append("boot-id")
        receipts["version"] = self._a90ctl("version", ["version"], self._remaining(deadline, cap=15)); order.append("version")
        receipts["selftest"] = self._a90ctl("selftest", ["selftest"], self._remaining(deadline, cap=15)); order.append("selftest")
        receipts["status"] = self._a90ctl("status", ["status"], self._remaining(deadline, cap=15)); order.append("status")
        receipts["bootIdFinal"] = self._a90ctl("boot-id-final", ["cat", "/proc/sys/kernel/random/boot_id"], self._remaining(deadline, cap=15)); order.append("boot-id-final")
        usb_after = adapter._validate_usb_inventory(self.runner.run("usb-inventory-after", (str(adapter.LSUSB),), self._remaining(deadline, cap=10)))
        if usb_before != usb_after:
            raise ContractError("USB target or foreign endpoint inventory changed")
        boot_text = adapter._validate_command(receipts["bootId"], ["cat", "/proc/sys/kernel/random/boot_id"], "boot ID")
        version_text = adapter._validate_command(receipts["version"], ["version"], "version")
        selftest_text = adapter._validate_command(receipts["selftest"], ["selftest"], "selftest")
        status_text = adapter._validate_command(receipts["status"], ["status"], "status")
        boot_final_text = adapter._validate_command(receipts["bootIdFinal"], ["cat", "/proc/sys/kernel/random/boot_id"], "final boot ID")
        boot_id = adapter._one_line(boot_text, adapter.BOOT_ID_RE, "first boot ID").group(0)
        final_boot_id = adapter._one_line(boot_final_text, adapter.BOOT_ID_RE, "final boot ID").group(0)
        version = adapter._one_line(version_text, adapter.VERSION_RE, "resident version")
        adapter._one_line(selftest_text, adapter.SELFTEST_RE, "resident selftest")
        pstore = [line.strip() for line in status_text.replace("\r", "").splitlines() if line.strip().startswith("pstore=")]
        same_boot = boot_id == final_boot_id
        healthy = len(pstore) == 1 and pstore[0].split().count("entries=0") == 1 and not any(token.startswith("entries=") and token != "entries=0" for token in pstore[0].split()) and (version.group("version"), version.group("build")) == (expected["version"], expected["build"]) and same_boot
        stable = {"usbBefore": usb_before, "usbAfter": usb_after, "bridge": bridge, "bootId": boot_id, "finalBootId": final_boot_id, "version": version.group("version"), "build": version.group("build"), "recoveryEvidenceSha256": self.recovery_evidence_sha256}
        evidence = {"stableIdentity": stable, "commandOrder": order, "commands": {key: _json_sha(receipts[key]) for key in sorted(receipts)}, "menuHideReceiptSha256": hide_receipt_sha}
        snapshot = owner.Snapshot(target_evidence_sha256=_sha(owner.canonical_json(stable)), boot_id=boot_id, version=version.group("version"), build=version.group("build"), healthy=healthy, recovery_available=True, recovery_evidence_sha256=self.recovery_evidence_sha256, fresh_state_observed=False, fresh_state_absent=False, other_targets_untouched=usb_before == usb_after and usb_before["a90EndpointCount"] == 1, receipt_sha256=_sha(owner.canonical_json({"evidence": evidence, "healthy": healthy})))
        return Observation(snapshot, hide_receipt_sha, tuple(order), final_boot_id, same_boot)


def _validate_observation(observation: Any, expected: dict[str, Any], review_sha: str) -> Observation:
    if not isinstance(observation, Observation) or observation.command_order != ("hide", "boot-id", "version", "selftest", "status", "boot-id-final") or type(observation.hide_receipt_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", observation.hide_receipt_sha256) is None or type(observation.final_boot_id) is not str or BOOT_ID_RE.fullmatch(observation.final_boot_id) is None or observation.same_boot is not True:
        raise ContractError("menu-hide observation order or receipt is invalid")
    snapshot = observation.snapshot
    if not isinstance(snapshot, owner.Snapshot):
        raise ContractError("menu-hide observer returned the wrong snapshot type")
    try:
        snapshot.validate()
    except owner.ContractError as exc:
        raise ContractError(str(exc)) from exc
    if BOOT_ID_RE.fullmatch(snapshot.boot_id) is None or observation.final_boot_id != snapshot.boot_id or snapshot.healthy is not True or snapshot.recovery_available is not True or snapshot.recovery_evidence_sha256 != review_sha or snapshot.fresh_state_observed is not False or snapshot.fresh_state_absent is not False or snapshot.other_targets_untouched is not True or (snapshot.version, snapshot.build) != (expected["version"], expected["build"]):
        raise ContractError("menu-hide health is not exact V2321")
    return observation


def _payload(observation: Observation, intent_sha: str, review_sha: str, closure: str) -> dict[str, Any]:
    recovered = observation.snapshot.payload()
    same_boot = observation.same_boot and observation.final_boot_id == observation.snapshot.boot_id
    return {"schema": SCHEMA, "decision": "V2321_HEALTHY_AFTER_MENU_HIDE_OBSERVER_REPAIR", "priorPhysicalIntentSha256": PRIOR_PHYSICAL_INTENT_SHA256, "priorObservationIntentSha256": PRIOR_OBSERVATION_INTENT_SHA256, "priorSlowHealthIntentSha256": PRIOR_SLOW_HEALTH_INTENT_SHA256, "priorSlowLogSetSha256": PRIOR_SLOW_LOG_SET_SHA256, "menuHideIntentSha256": intent_sha, "menuHideReceiptSha256": observation.hide_receipt_sha256, "priorObserverOutcome": "NO_PROOF_TRANSPORT_AND_MENU_BUSY", "candidateReplay": False, "rollbackReplay": False, "hostRecoveryCommandCount": 0, "deviceEffectCount": 0, "bootWriteCount": 0, "rebootCount": 0, "physicalActionCount": 0, "sameBoot": same_boot, "finalBootId": observation.final_boot_id, "currentReviewSha256": review_sha, "executionClosureSha256": closure, "recoveredSnapshot": recovered, "recoveredSnapshotSha256": _json_sha(recovered)}


def _validate_payload(payload: Any, manifest: dict[str, Any], intent_sha: str, review_sha: str, closure: str) -> None:
    if type(payload) is not dict or set(payload) != PAYLOAD_KEYS or payload["schema"] != SCHEMA or payload["decision"] != "V2321_HEALTHY_AFTER_MENU_HIDE_OBSERVER_REPAIR" or payload["priorPhysicalIntentSha256"] != PRIOR_PHYSICAL_INTENT_SHA256 or payload["priorObservationIntentSha256"] != PRIOR_OBSERVATION_INTENT_SHA256 or payload["priorSlowHealthIntentSha256"] != PRIOR_SLOW_HEALTH_INTENT_SHA256 or payload["priorSlowLogSetSha256"] != PRIOR_SLOW_LOG_SET_SHA256 or payload["menuHideIntentSha256"] != intent_sha or type(payload["menuHideReceiptSha256"]) is not str or re.fullmatch(r"[0-9a-f]{64}", payload["menuHideReceiptSha256"]) is None or type(payload["finalBootId"]) is not str or BOOT_ID_RE.fullmatch(payload["finalBootId"]) is None or payload["priorObserverOutcome"] != "NO_PROOF_TRANSPORT_AND_MENU_BUSY" or payload["candidateReplay"] is not False or payload["rollbackReplay"] is not False or any(type(payload[key]) is not int or payload[key] != 0 for key in ("hostRecoveryCommandCount", "deviceEffectCount", "bootWriteCount", "rebootCount", "physicalActionCount")) or payload["currentReviewSha256"] != review_sha or payload["executionClosureSha256"] != closure or payload["recoveredSnapshotSha256"] != _json_sha(payload["recoveredSnapshot"]):
        raise ContractError("menu-hide payload is invalid")
    item = payload["recoveredSnapshot"]
    if type(item) is not dict or set(item) != SNAPSHOT_KEYS:
        raise ContractError("menu-hide snapshot fields mismatch")
    snapshot = owner.Snapshot(target_evidence_sha256=item["targetEvidenceSha256"], boot_id=item["bootId"], version=item["version"], build=item["build"], healthy=item["healthy"], recovery_available=item["recoveryAvailable"], recovery_evidence_sha256=item["recoveryEvidenceSha256"], fresh_state_observed=item["freshStateObserved"], fresh_state_absent=item["freshStateAbsent"], other_targets_untouched=item["otherTargetsUntouched"], receipt_sha256=item["receiptSha256"])
    same_boot = payload["finalBootId"] == snapshot.boot_id
    if payload["sameBoot"] is not same_boot or same_boot is not True:
        raise ContractError("menu-hide payload boot IDs do not match")
    _validate_observation(Observation(snapshot, payload["menuHideReceiptSha256"], ("hide", "boot-id", "version", "selftest", "status", "boot-id-final"), payload["finalBootId"], same_boot), manifest["rollback"], review_sha)


def _existing_recovery(state: State, lease: ReviewLease) -> dict[str, Any] | None:
    record = state.records.get(RECOVERY_NAME)
    if record is None:
        return None
    if state.intent is None:
        raise ContractError("menu-hide recovery has no intent")
    if record.get("schema") != owner.RECORD_SCHEMA or record.get("kind") != owner.RECORD_KINDS[RECOVERY_NAME] or record.get("manifestSha256") != MANIFEST_SHA256:
        raise ContractError("menu-hide recovery envelope changed")
    _require_closure(lease)
    _validate_payload(record.get("payload"), state.manifest, state.intent[2], state.review_sha, state.closure)
    try:
        owner._active_guard(state.manifest)[0].lstat()
    except FileNotFoundError:
        _require_guards(state.manifest, active=False)
        return record["payload"]
    except OSError as exc:
        raise ContractError("active guard cannot be inspected") from exc
    raise ContractError("menu-hide recovery exists while active guard remains; park")


def _readback(state: State, payload: dict[str, Any], intent_sha: str, lease: ReviewLease) -> None:
    run_directory, records = _load_records(state.manifest)
    expected = owner._record(owner.RECORD_KINDS[RECOVERY_NAME], MANIFEST_SHA256, payload)
    record = records.get(RECOVERY_NAME)
    if run_directory != state.run_directory or record != expected or _json_sha(record) != _json_sha(expected):
        raise ContractError("menu-hide recovery readback changed")
    _require_closure(lease)
    _validate_payload(record["payload"], state.manifest, intent_sha, state.review_sha, state.closure)


def execute(approval: str) -> dict[str, Any]:
    if type(approval) is not str:
        raise ContractError("approval token is invalid")
    state = _state(active=False)
    if (
        MANIFEST_SHA256 == prior.HISTORICAL_H28_MANIFEST_SHA256
        and state.manifest["candidate"]["sha256"] == prior.HISTORICAL_H28_CANDIDATE_SHA256
        and RECOVERY_NAME in state.records
    ):
        return prior._historical_recovery_payload(state.records[RECOVERY_NAME])
    if RECOVERY_NAME in state.records:
        lease = ReviewLease(state.review_sha, state.closure)
        try:
            result = _existing_recovery(state, lease)
            if result is None:
                raise ContractError("menu-hide recovery is unavailable")
            return result
        finally:
            lease.close()
    if state.intent is not None:
        raise ContractError("menu-hide intent is consumed; park")
    if approval != _approval_token(state.review_sha, state.closure):
        raise ContractError("approval token does not bind fixed menu-hide state")
    lease = ReviewLease(state.review_sha, state.closure)
    try:
        _require_closure(lease)
        state = _recheck(state, lease, active=True)
        if state.intent is not None:
            raise ContractError("menu-hide intent already exists")
        intent = {"schema": INTENT_SCHEMA, "capability": CAPABILITY, "runId": RUN_ID, "manifestSha256": MANIFEST_SHA256, "terminalSha256": TERMINAL_SHA256, "priorPhysicalIntentSha256": PRIOR_PHYSICAL_INTENT_SHA256, "priorObservationIntentSha256": PRIOR_OBSERVATION_INTENT_SHA256, "priorSlowHealthIntentSha256": PRIOR_SLOW_HEALTH_INTENT_SHA256, "priorSlowLogSetSha256": PRIOR_SLOW_LOG_SET_SHA256, "currentReviewSha256": state.review_sha, "executionClosureSha256": state.closure, "approvalSha256": _sha(approval.encode("ascii"))}
        intent_sha = _publish_intent(intent)
        _require_closure(lease)
        state = _recheck(state, lease, active=True)
        if state.intent is None or state.intent[2] != intent_sha:
            raise ContractError("published menu-hide intent is not exact")
        runner = adapter.HostRunner(owner.RUN_ROOT / "a90-h28-f1-20260821-01-menu-hide-health-1-logs")
        qualification = dict(state.manifest["qualification"])
        qualification["review"] = {"path": str(CURRENT_REVIEW_PATH), "size": lease.before.st_size, "sha256": state.review_sha}
        observer = MenuHideObserver(runner, qualification=qualification)
        observation = observer.observe(state.manifest["rollback"], timeout_sec=HEALTH_TIMEOUT_SEC)
        _require_closure(lease)
        _validate_observation(observation, state.manifest["rollback"], state.review_sha)
        payload = _payload(observation, intent_sha, state.review_sha, state.closure)
        _validate_payload(payload, state.manifest, intent_sha, state.review_sha, state.closure)
        _require_closure(lease); _require_guards(state.manifest, active=True)
        owner.publish_record(state.run_directory, RECOVERY_NAME, owner._record(owner.RECORD_KINDS[RECOVERY_NAME], MANIFEST_SHA256, payload))
        _require_closure(lease); _require_guards(state.manifest, active=True)
        _readback(state, payload, intent_sha, lease)
        _require_closure(lease); _require_guards(state.manifest, active=True)
        owner._release_active_guard(state.manifest)
        _require_closure(lease); _require_guards(state.manifest, active=False)
        return payload
    finally:
        lease.close()


def _post_import_launch_contract() -> None:
    try:
        _pre_import_launch_contract()
    except _LaunchContractError as exc:
        raise ContractError(str(exc)) from exc
    modules = (("a90_boot_only_f1_minimal_v1", owner, FIXED_OWNER), ("a90_boot_only_f1_adapter_v1", adapter, FIXED_ADAPTER), ("a90_h28_physical_system_return_reconcile_v1", prior, FIXED_PRIOR))
    for canonical, module, path in modules:
        if sys.modules.get(canonical) is not module or getattr(module, "__file__", None) != path:
            raise ContractError(f"{canonical} module identity is not exact")
    canonical_names = {name for name, _, _ in modules}
    for name, module in tuple(sys.modules.items()):
        if name not in canonical_names:
            module_file = getattr(module, "__file__", None)
            if any(module is item or (isinstance(module_file, str) and str(Path(module_file).resolve()) == path) for _, item, path in modules):
                raise ContractError("local module alias is not allowed")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="action", required=True)
    subparsers.add_parser("prepare")
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--approval", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    _post_import_launch_contract()
    args = parser().parse_args(argv)
    if args.action == "prepare":
        print(prepare())
    else:
        print(json.dumps(execute(args.approval), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, owner.ContractError, adapter.ContractError, prior.ContractError) as exc:
        print(f"A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
