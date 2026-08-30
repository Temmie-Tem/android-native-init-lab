#!/usr/bin/env python3
"""One-shot V2321 rollback continuation for consumed A90 H41 run-02.

The original H41 rollback journal reached launch, but its adapter rejected a
two-Samsung pre-effect USB inventory before dispatching the flash helper.  This
continuation binds that exact no-helper/no-write incident.  It has no candidate
path and permits one newly journaled V2321 rollback followed by one separately
journaled read-only health observation after the operator closes the V2321
menu.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
OWNER_PATH = MODULE_DIR / "a90_boot_only_f1_minimal_v1.py"
ADAPTER_PATH = MODULE_DIR / "a90_boot_only_f1_adapter_v1.py"
SELF_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests/test_a90_h41_run02_rollback_continuation_v1.py"
CONTRACT_PATH = ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
GOAL_PATH = ROOT / "GOAL_A90.md"
INCIDENT_PATH = ROOT / "docs/reports/A90_H41_BADAPPLE_TIMEOUT_ROLLBACK_PREFLIGHT_INCIDENT_2026-08-31.md"
REVIEW_PATH = ROOT / "docs/reports/A90_H41_RUN02_ROLLBACK_CONTINUATION_REVIEW_2026-08-31.json"
MANIFEST_PATH = ROOT / "workspace/private/manifests/a90-h41-f1-20260830-02.json"
RUN_ROOT = ROOT / "workspace/private/runs/a90-boot-only-f1-minimal-v1"
ORIGINAL_SIDE_ROOT = RUN_ROOT / "a90-h41-run02-late-recovery-demo-v1"
ORIGINAL_ROLLBACK_LOG_DIR = ORIGINAL_SIDE_ROOT / "rollback-1-logs"
CONT_DIR = RUN_ROOT / "a90-h41-run02-rollback-continuation-v1"
ROLLBACK_LOG_DIR = RUN_ROOT / "a90-h41-run02-rollback-continuation-v1-rollback-logs"
HEALTH_LOG_DIR = RUN_ROOT / "a90-h41-run02-rollback-continuation-v1-health-logs"

CAPABILITY = "A90_H41_RUN02_ROLLBACK_CONTINUATION_V1"
RUN_ID = "a90-h41-f1-20260830-02"
MANIFEST_SHA256 = "eacd2090683e842314dcdfe9e4a1ae16bdb5eb35af5ede0a4b917653e0c6fe40"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
ORIGINAL_REVIEW_SHA256 = "a9a27fe37954390708684169a60fa6decccd32bb99559518c5f9d2c140182d7b"
ORIGINAL_EXECUTION_CLOSURE_SHA256 = "c3c0fcfb03c6a100728a96a63cc8a9b365eb11db91bd294bfc86ac6e1552b982"
ORIGINAL_ROLLBACK_INTENT_SHA256 = "852f2ad6eb9cdaf6f7c9fc7e1396d5286276bd18a3d47106bc1b2ee57b953953"
ORIGINAL_REVIEW_PATH = ROOT / "docs/reports/A90_H41_RUN02_LATE_RECOVERY_MANUAL_DEMO_REVIEW_2026-08-30.json"
REVIEW_SCHEMA = "a90-h41-run02-rollback-continuation-review-v1"
RECORD_SCHEMA = "a90-h41-run02-rollback-continuation-record-v1"
APPROVAL_PREFIX = "A90-H41-RUN02-ROLLBACK-CONTINUE-V1-APPROVE:"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()

ORIGINAL_RECORD_HASHES = {
    "00-transaction-intent.json": "341a3b626c034bbc128a321b4aa33ff183d660397f218b4a554e055b0096ac46",
    "10-late-recovery-ready.json": "e40c687c4df7ac71bb1f911ae072dacd6ca104df858f72f4eefc668e0f9075e8",
    "20-candidate-intent.json": "6292880b9e5e8cb13f6aef3ad48f393d94500bcb1dd1c9f841240cc3fc47881b",
    "21-candidate-launched.json": "bf6d4438babddc23da0c8f9c1982dc3c57273d8717b129cd8a1aba49c07ad62c",
    "22-candidate-result.json": "3158fcfb9cb0418887b347cc18ac197d84f27698d2fa4b0aa626de691487c019",
    "23-demo-window.json": "d383ac3fca49c7fedea73d5ab9e18f5b4a44801d704f333848e29e54a201ac4c",
    "30-rollback-intent.json": ORIGINAL_ROLLBACK_INTENT_SHA256,
    "31-rollback-launched.json": "bf6d4438babddc23da0c8f9c1982dc3c57273d8717b129cd8a1aba49c07ad62c",
}
ORIGINAL_PREFLIGHT_LOG_HASHES = {
    "001-effect-usb-inventory.stderr": EMPTY_SHA256,
    "001-effect-usb-inventory.stdout": "51b28c5879532e609ce020fd3807151ac80c261cd054d679b3c2fe259ad5e5fb",
    "002-adb-inventory.stderr": EMPTY_SHA256,
    "002-adb-inventory.stdout": "40423a67d3e567e0015a62a96266440d3b6deda673cf8aaa7d37839e8538e6bd",
}
ORIGINAL_INSTALL_LOG_HASHES = {
    **ORIGINAL_PREFLIGHT_LOG_HASHES,
    "003-flash-candidate.stderr": "71dd8f23db82c81d286d790b1a1d18266e132a1e2fffc2f7e90a3b9cd4cd72d5",
    "003-flash-candidate.stdout": "75ba0ce0b9bc231e56662fd2e49fb177dd9a4949ffba882ee20b6264195a4232",
}
ORIGINAL_ROLLBACK_LOG_HASHES = {
    "001-effect-usb-inventory.stderr": EMPTY_SHA256,
    "001-effect-usb-inventory.stdout": "e53ba7e9dd0a9f579a83957dac447dbfcbb517c295bc2efcac7c34619d32e83b",
}
ORIGINAL_ROLLBACK_LOG_SET_SHA256 = hashlib.sha256(
    b"".join(
        name.encode("utf-8") + b"\0" + value.encode("ascii") + b"\0"
        for name, value in sorted(ORIGINAL_ROLLBACK_LOG_HASHES.items())
    )
).hexdigest()

CLOSURE_PATHS = (
    ROOT / "AGENTS.md",
    SELF_PATH,
    TEST_PATH,
    CONTRACT_PATH,
    GOAL_PATH,
    INCIDENT_PATH,
    OWNER_PATH,
    ADAPTER_PATH,
    ROOT / "workspace/public/src/native-init/a90_controller.c",
    ROOT / "workspace/public/src/native-init/v319/40_menu_apps.inc.c",
    ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c",
    ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py",
    ROOT / "workspace/public/src/scripts/revalidation/a90_bridge.py",
    ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py",
    ROOT / "workspace/public/src/scripts/revalidation/a90_observation_pipeline.py",
    ROOT / "workspace/public/src/scripts/revalidation/a90_serial_lock.py",
    ROOT / "workspace/public/src/scripts/revalidation/a90_transition_contract_v2.py",
    ROOT / "workspace/public/src/scripts/revalidation/serial_tcp_bridge.py",
    ROOT / "workspace/public/src/scripts/server-distro/a90_serial_redaction_v1.py",
    ROOT / "workspace/public/src/scripts/revalidation/_workspace_bootstrap.py",
)


class RecoveryError(RuntimeError):
    """Any drift, ambiguity, replay, or non-exact H41 recovery state."""


def _load(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RecoveryError(f"cannot load {name}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    if Path(getattr(module, "__file__", "")).resolve() != path:
        raise RecoveryError(f"{name} identity changed")
    return module


owner = _load("_a90_h41_rollback_owner_v1", OWNER_PATH)
adapter = _load("_a90_h41_rollback_adapter_v1", ADAPTER_PATH)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, maximum: int = 1 << 20) -> bytes:
    return owner._read_bounded_regular(path, path.name, maximum)


def _read_log(path: Path, maximum: int = 1 << 20) -> bytes:
    """Read one owned regular log while permitting an exact empty stderr."""
    try:
        before = path.lstat()
        descriptor = os.open(
            path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
        )
    except OSError as exc:
        raise RecoveryError(f"log is unavailable: {path.name}") from exc
    try:
        current = os.fstat(descriptor)
        raw = os.pread(descriptor, current.st_size, 0)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or before.st_nlink != 1
            or current.st_nlink != 1
            or before.st_uid != os.getuid()
            or before.st_gid != os.getgid()
            or current.st_uid != os.getuid()
            or current.st_gid != os.getgid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or stat.S_IMODE(current.st_mode) != 0o600
            or (before.st_dev, before.st_ino, before.st_size)
            != (current.st_dev, current.st_ino, current.st_size)
            or not 0 <= current.st_size <= maximum
            or len(raw) != current.st_size
            or os.pread(descriptor, 1, current.st_size)
        ):
            raise RecoveryError(f"log identity changed: {path.name}")
        return raw
    finally:
        os.close(descriptor)


def _private_dir(path: Path, label: str) -> None:
    try:
        item = path.lstat()
    except OSError as exc:
        raise RecoveryError(f"{label} is unavailable") from exc
    if (
        not stat.S_ISDIR(item.st_mode)
        or item.st_uid != os.getuid()
        or item.st_gid != os.getgid()
        or stat.S_IMODE(item.st_mode) != 0o700
    ):
        raise RecoveryError(f"{label} identity changed")


def _exact_log_set(directory: Path, hashes: dict[str, str], label: str) -> dict[str, bytes]:
    _private_dir(directory, label)
    adb_home = directory / ".adb-home"
    adb_android = adb_home / ".android"
    _private_dir(adb_home, f"{label} ADB home")
    _private_dir(adb_android, f"{label} ADB config")
    if set(path.name for path in directory.iterdir()) != set(hashes) | {".adb-home"}:
        raise RecoveryError(f"{label} inventory changed")
    if set(path.name for path in adb_home.iterdir()) != {".android"} or any(adb_android.iterdir()):
        raise RecoveryError(f"{label} ADB home contains state")
    values = {}
    for name, expected in hashes.items():
        raw = _read_log(directory / name)
        if _sha(raw) != expected:
            raise RecoveryError(f"{label} changed: {name}")
        values[name] = raw
    return values


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    for path in CLOSURE_PATHS:
        raw = path.read_bytes()
        digest.update(str(path.relative_to(ROOT)).encode("utf-8") + b"\0")
        digest.update(str(len(raw)).encode("ascii") + b"\0")
        digest.update(_sha(raw).encode("ascii") + b"\0")
    return digest.hexdigest()


def _review() -> tuple[str, str]:
    raw = _read(REVIEW_PATH)
    value = owner.parse_canonical(raw, "H41 rollback continuation review")
    expected = {
        "schema", "capability", "verdict", "runId", "manifestSha256",
        "originalDemoReviewSha256", "originalRollbackIntentSha256",
        "originalRollbackLogSetSha256", "executionClosureSha256",
        "findings", "contacts", "reviewer", "reviewDate", "liveAuthority",
    }
    closure = execution_closure_sha256()
    if type(value) is not dict or set(value) != expected:
        raise RecoveryError("H41 rollback review schema changed")
    findings = value["findings"]
    contacts = value["contacts"]
    if (
        value["schema"] != REVIEW_SCHEMA
        or value["capability"] != CAPABILITY
        or value["verdict"] != "PASS_GO"
        or value["runId"] != RUN_ID
        or value["manifestSha256"] != MANIFEST_SHA256
        or value["originalDemoReviewSha256"] != ORIGINAL_REVIEW_SHA256
        or value["originalRollbackIntentSha256"] != ORIGINAL_ROLLBACK_INTENT_SHA256
        or value["originalRollbackLogSetSha256"] != ORIGINAL_ROLLBACK_LOG_SET_SHA256
        or value["executionClosureSha256"] != closure
        or value["reviewDate"] != "2026-08-31"
        or value["liveAuthority"] is not False
        or type(findings) is not dict
        or set(findings) != {"high", "medium", "low"}
        or any(type(items) is not list or items for items in findings.values())
        or type(contacts) is not dict
        or set(contacts) != {
            "device", "dev", "usb", "network", "workspacePrivate",
            "otherTargets", "writes",
        }
        or any(type(count) is not int or count != 0 for count in contacts.values())
        or type(value["reviewer"]) is not str
        or not value["reviewer"]
    ):
        raise RecoveryError("H41 rollback review is not exact PASS_GO")
    return _sha(raw), closure


def _record(name: str) -> dict[str, Any]:
    raw = _read(ORIGINAL_SIDE_ROOT / name)
    if _sha(raw) != ORIGINAL_RECORD_HASHES[name]:
        raise RecoveryError(f"original H41 record changed: {name}")
    value = owner.parse_canonical(raw, f"original H41 {name}")
    if (
        type(value) is not dict
        or set(value) != {"schema", "capability", "runId", "manifestSha256", "payload"}
        or value["schema"] != "a90-h41-run02-late-recovery-manual-demo-record-v1"
        or value["capability"] != "A90_H41_RUN02_LATE_RECOVERY_MANUAL_DEMO_V1"
        or value["runId"] != RUN_ID
        or value["manifestSha256"] != MANIFEST_SHA256
        or type(value["payload"]) is not dict
    ):
        raise RecoveryError(f"original H41 record schema changed: {name}")
    return value["payload"]


def _verify_historical_qualification(manifest: dict[str, Any]) -> None:
    descriptor = manifest["qualification"]["review"]
    raw = owner._verify_input(descriptor, "fixed H41 qualification review")
    value = owner.parse_canonical(raw, "fixed H41 qualification review")
    if (
        type(value) is not dict
        or value.get("verdict") != "PASS_GO"
        or value.get("candidateSha256") != manifest["candidate"]["sha256"]
        or value.get("rollbackSha256") != manifest["rollback"]["sha256"]
        or value.get("targetProfile") != manifest["targetProfile"]
        or value.get("recovery") != manifest["qualification"]["recovery"]
        or value.get("hazard") != manifest["qualification"]["hazard"]
        or value.get("freshState") != manifest["qualification"]["freshState"]
        or value.get("liveAuthority") is not False
    ):
        raise RecoveryError("fixed H41 qualification review changed")


def _fixed_incident_evidence(*, allow_active_absent: bool = False) -> dict[str, Any]:
    raw, manifest = owner.load_manifest(MANIFEST_PATH)
    if _sha(raw) != MANIFEST_SHA256 or manifest["runId"] != RUN_ID:
        raise RecoveryError("fixed H41 manifest changed")
    _private_dir(ORIGINAL_SIDE_ROOT, "original H41 side journal")
    expected_side = set(ORIGINAL_RECORD_HASHES) | {
        "preflight-1-logs", "install-1-logs", "rollback-1-logs",
    }
    if set(path.name for path in ORIGINAL_SIDE_ROOT.iterdir()) != expected_side:
        raise RecoveryError("original H41 side journal inventory changed")
    records = {name: _record(name) for name in ORIGINAL_RECORD_HASHES}
    if records["20-candidate-intent.json"] != {
        "attempt": 1, "sha256": manifest["candidate"]["sha256"],
    } or records["21-candidate-launched.json"] != {"attempt": 1}:
        raise RecoveryError("original H41 candidate intent changed")
    candidate = records["22-candidate-result.json"]
    if candidate != {
        "completed": True,
        "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
        "quiescent": True,
        "receiptSha256": "b6cd64a19c5f3473c0d5095762e258e01eb80fadaec4add5bdd5f884b0f7578a",
        "returncode": 0,
    }:
        raise RecoveryError("original H41 candidate result changed")
    if records["23-demo-window.json"] != {
        "candidateReplay": False,
        "operatorMustCloseMenuBeforeRollback": True,
        "rollbackReplay": False,
        "runtimeProved": False,
        "state": "H41_MANUAL_DEMO_WINDOW_UNPROVED",
    }:
        raise RecoveryError("original H41 demo window changed")
    rollback_intent = records["30-rollback-intent.json"]
    if (
        rollback_intent.get("attempt") != 1
        or rollback_intent.get("sha256") != ROLLBACK_SHA256
        or rollback_intent.get("operatorAttended") is not True
        or rollback_intent.get("menuClosedConfirmed") is not True
        or rollback_intent.get("automaticAfterCandidateNonSuccess") is not False
        or rollback_intent.get("candidateReplay") is not False
        or rollback_intent.get("rollbackReplay") is not False
        or rollback_intent.get("currentReviewSha256") != ORIGINAL_REVIEW_SHA256
        or rollback_intent.get("executionClosureSha256") != ORIGINAL_EXECUTION_CLOSURE_SHA256
        or records["31-rollback-launched.json"] != {"attempt": 1}
    ):
        raise RecoveryError("original H41 rollback intent/launch changed")
    preflight = _exact_log_set(
        ORIGINAL_SIDE_ROOT / "preflight-1-logs", ORIGINAL_PREFLIGHT_LOG_HASHES,
        "original H41 preflight logs",
    )
    install = _exact_log_set(
        ORIGINAL_SIDE_ROOT / "install-1-logs", ORIGINAL_INSTALL_LOG_HASHES,
        "original H41 install logs",
    )
    rollback_logs = _exact_log_set(
        ORIGINAL_ROLLBACK_LOG_DIR, ORIGINAL_ROLLBACK_LOG_HASHES,
        "original H41 rollback logs",
    )
    if preflight["001-effect-usb-inventory.stdout"] != install["001-effect-usb-inventory.stdout"]:
        raise RecoveryError("original H41 Recovery inventories differ")
    receipt = owner.parse_canonical(install["003-flash-candidate.stdout"], "H41 candidate receipt")
    if (
        receipt.get("outcome") != "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
        or receipt.get("writeStarted") is not True
        or receipt.get("bootWrittenReadbackExact") is not True
        or receipt.get("systemReturnConfirmed") is not True
    ):
        raise RecoveryError("original H41 candidate helper receipt changed")
    if b"04e8:6861" not in rollback_logs["001-effect-usb-inventory.stdout"] or b"04e8:6860" not in rollback_logs["001-effect-usb-inventory.stdout"]:
        raise RecoveryError("original H41 rollback rejection is not two-Samsung")
    original_review = _read(ORIGINAL_REVIEW_PATH)
    if _sha(original_review) != ORIGINAL_REVIEW_SHA256:
        raise RecoveryError("original H41 demo review changed")
    original_review_value = owner.parse_canonical(original_review, "original H41 demo review")
    if (
        original_review_value.get("verdict") != "PASS_GO"
        or original_review_value.get("executionClosureSha256") != ORIGINAL_EXECUTION_CLOSURE_SHA256
        or original_review_value.get("liveAuthority") is not False
    ):
        raise RecoveryError("original H41 demo review classification changed")
    _verify_historical_qualification(manifest)
    owner._require_candidate_guard(manifest)
    active_path, _active_raw = owner._active_guard(manifest)
    try:
        active_path.lstat()
    except FileNotFoundError:
        if not allow_active_absent:
            raise RecoveryError("H41 active guard is absent before recovery")
    except OSError as exc:
        raise RecoveryError("H41 active guard cannot be inspected") from exc
    else:
        owner._require_active_guard(manifest)
    bound = owner.BoundArtifact.open(manifest["rollback"], "rollback")
    try:
        bound.checkpoint()
    finally:
        bound.close()
    return manifest


def _original_context(*, allow_active_absent: bool = False) -> tuple[dict[str, Any], str, str]:
    manifest = _fixed_incident_evidence(allow_active_absent=allow_active_absent)
    review_sha, closure = _review()
    return manifest, review_sha, closure


def _approval(review_sha: str, closure: str) -> str:
    payload = {
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "rollbackSha256": ROLLBACK_SHA256,
        "originalRollbackIntentSha256": ORIGINAL_ROLLBACK_INTENT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "phases": ["one-v2321-rollback", "one-post-menu-close-health"],
    }
    return APPROVAL_PREFIX + _sha(owner.canonical_json(payload))


def _publish(name: str, payload: dict[str, Any]) -> str:
    value = {
        "schema": RECORD_SCHEMA,
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "payload": payload,
    }
    raw = owner.canonical_json(value)
    path = CONT_DIR / name
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        try:
            if os.write(descriptor, raw) != len(raw):
                raise RecoveryError(f"short sidecar write: {name}")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise RecoveryError(f"sidecar publication failed: {name}") from exc
    owner._fsync_directory(CONT_DIR)
    if _read(path) != raw:
        raise RecoveryError(f"sidecar readback changed: {name}")
    return _sha(raw)


def _continuation_record(name: str) -> dict[str, Any]:
    value = owner.parse_canonical(_read(CONT_DIR / name), f"H41 continuation {name}")
    if (
        type(value) is not dict
        or set(value) != {"schema", "capability", "runId", "manifestSha256", "payload"}
        or value["schema"] != RECORD_SCHEMA
        or value["capability"] != CAPABILITY
        or value["runId"] != RUN_ID
        or value["manifestSha256"] != MANIFEST_SHA256
        or type(value["payload"]) is not dict
    ):
        raise RecoveryError(f"continuation record changed: {name}")
    return value["payload"]


def _effect_result() -> Any:
    payload = _continuation_record("10-rollback-result.json")
    if set(payload) != {"returncode", "completed", "quiescent", "receiptSha256", "outcome"}:
        raise RecoveryError("H41 continuation effect result shape changed")
    result = owner.EffectResult(
        payload["returncode"], payload["completed"], payload["quiescent"],
        payload["receiptSha256"], payload["outcome"],
    )
    result.validate()
    return result


def _current_log_hashes(directory: Path, label: str) -> dict[str, str]:
    _private_dir(directory, label)
    adb_home = directory / ".adb-home"
    adb_android = adb_home / ".android"
    _private_dir(adb_home, f"{label} ADB home")
    _private_dir(adb_android, f"{label} ADB config")
    if set(path.name for path in adb_home.iterdir()) != {".android"} or any(adb_android.iterdir()):
        raise RecoveryError(f"{label} ADB home contains state")
    names = {path.name for path in directory.iterdir()} - {".adb-home"}
    if (
        not names
        or any(
            not name[:3].isdigit()
            or name[3:4] != "-"
            or not name.endswith((".stdout", ".stderr"))
            for name in names
        )
    ):
        raise RecoveryError(f"{label} log inventory is invalid")
    return {name: _sha(_read_log(directory / name)) for name in sorted(names)}


def _snapshot_from_payload(payload: dict[str, Any]) -> Any:
    expected = {
        "targetEvidenceSha256", "bootId", "version", "build", "healthy",
        "recoveryAvailable", "recoveryEvidenceSha256", "freshStateObserved",
        "freshStateAbsent", "otherTargetsUntouched", "receiptSha256",
    }
    if type(payload) is not dict or set(payload) != expected:
        raise RecoveryError("H41 recovery snapshot shape changed")
    snapshot = owner.Snapshot(
        target_evidence_sha256=payload["targetEvidenceSha256"],
        boot_id=payload["bootId"],
        version=payload["version"],
        build=payload["build"],
        healthy=payload["healthy"],
        recovery_available=payload["recoveryAvailable"],
        recovery_evidence_sha256=payload["recoveryEvidenceSha256"],
        fresh_state_observed=payload["freshStateObserved"],
        fresh_state_absent=payload["freshStateAbsent"],
        other_targets_untouched=payload["otherTargetsUntouched"],
        receipt_sha256=payload["receiptSha256"],
    )
    snapshot.validate()
    return snapshot


def _healthy_snapshot(snapshot: Any, manifest: dict[str, Any]) -> bool:
    return (
        snapshot.healthy is True
        and snapshot.recovery_available is True
        and snapshot.other_targets_untouched is True
        and snapshot.fresh_state_observed is False
        and snapshot.fresh_state_absent is False
        and snapshot.recovery_evidence_sha256 == manifest["qualification"]["review"]["sha256"]
        and (snapshot.version, snapshot.build)
        == (manifest["rollback"]["version"], manifest["rollback"]["build"])
    )


def _validate_final_prefix(
    manifest: dict[str, Any], approval: str, review_sha: str, closure: str
) -> dict[str, Any]:
    _private_dir(CONT_DIR, "H41 rollback continuation journal")
    if set(path.name for path in CONT_DIR.iterdir()) != {
        "00-continuation-intent.json", "10-rollback-result.json",
        "15-health-intent.json", "20-final.json",
    }:
        raise RecoveryError("H41 final continuation inventory changed")
    intent = _continuation_record("00-continuation-intent.json")
    health_intent = _continuation_record("15-health-intent.json")
    effect = _effect_result()
    final = _continuation_record("20-final.json")
    intent_keys = {
        "approvalSha256", "reviewSha256", "executionClosureSha256",
        "originalRollbackIntentSha256", "rollbackSha256",
        "ownerUsbInventorySha256", "ownerAdbRole", "continuationWriteCount",
        "candidateReplay", "originalRollbackReplay",
    }
    health_intent_keys = {
        "approvalSha256", "reviewSha256", "executionClosureSha256",
        "rollbackReceiptSha256", "healthObservationCount",
        "operatorAttended", "menuClosedConfirmed", "candidateReplay",
        "rollbackReplay",
    }
    if (
        set(intent) != intent_keys
        or intent.get("approvalSha256") != _sha(approval.encode("ascii"))
        or intent.get("reviewSha256") != review_sha
        or intent.get("executionClosureSha256") != closure
        or intent.get("originalRollbackIntentSha256") != ORIGINAL_ROLLBACK_INTENT_SHA256
        or intent.get("rollbackSha256") != ROLLBACK_SHA256
        or type(intent.get("ownerUsbInventorySha256")) is not str
        or owner.SHA256_RE.fullmatch(intent["ownerUsbInventorySha256"]) is None
        or intent.get("ownerAdbRole") != adapter.ADB_ROLE_NATIVE
        or type(intent.get("continuationWriteCount")) is not int
        or intent["continuationWriteCount"] != 1
        or intent.get("candidateReplay") is not False
        or intent.get("originalRollbackReplay") is not False
        or set(health_intent) != health_intent_keys
        or health_intent != {
            "approvalSha256": _sha(approval.encode("ascii")),
            "reviewSha256": review_sha,
            "executionClosureSha256": closure,
            "rollbackReceiptSha256": effect.receipt_sha256,
            "healthObservationCount": 1,
            "operatorAttended": True,
            "menuClosedConfirmed": True,
            "candidateReplay": False,
            "rollbackReplay": False,
        }
        or type(health_intent.get("healthObservationCount")) is not int
        or health_intent["healthObservationCount"] != 1
        or health_intent.get("operatorAttended") is not True
        or health_intent.get("menuClosedConfirmed") is not True
        or health_intent.get("candidateReplay") is not False
        or health_intent.get("rollbackReplay") is not False
    ):
        raise RecoveryError("H41 final continuation binding changed")
    expected_final = {
        "decision", "candidateReplay", "originalRollbackReplay",
        "continuationRollbackReplay", "incidentContinuationWriteCount",
        "rollbackResult", "snapshot", "rollbackLogHashes", "healthLogHashes",
    }
    if (
        set(final) != expected_final
        or final["decision"] != "V2321_HEALTHY_H41_RUN02_RECOVERED"
        or final["candidateReplay"] is not False
        or final["originalRollbackReplay"] is not False
        or final["continuationRollbackReplay"] is not False
        or type(final["incidentContinuationWriteCount"]) is not int
        or final["incidentContinuationWriteCount"] != 1
        or final["rollbackResult"] != effect.payload()
        or final["rollbackLogHashes"] != _current_log_hashes(
            ROLLBACK_LOG_DIR, "H41 continuation rollback logs"
        )
        or final["healthLogHashes"] != _current_log_hashes(
            HEALTH_LOG_DIR, "H41 continuation health logs"
        )
    ):
        raise RecoveryError("H41 final continuation evidence changed")
    snapshot = _snapshot_from_payload(final["snapshot"])
    if not _healthy_snapshot(snapshot, manifest):
        raise RecoveryError("H41 final snapshot is not exact healthy V2321")
    return final


def _resume_final(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure = _original_context(allow_active_absent=True)
    if approval != _approval(review_sha, closure):
        raise RecoveryError("H41 final resume approval mismatch")
    final = _validate_final_prefix(manifest, approval, review_sha, closure)
    _current_manifest, current_review_sha, current_closure = _original_context(
        allow_active_absent=True
    )
    if (current_review_sha, current_closure) != (review_sha, closure):
        raise RecoveryError("H41 final resume review lease changed before guard release")
    owner._require_candidate_guard(manifest)
    active_path, _active_raw = owner._active_guard(manifest)
    try:
        active_path.lstat()
    except FileNotFoundError:
        return final
    except OSError as exc:
        raise RecoveryError("H41 active guard cannot be inspected at final resume") from exc
    owner._require_active_guard(manifest)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def prepare() -> str:
    if CONT_DIR.exists() or ROLLBACK_LOG_DIR.exists() or HEALTH_LOG_DIR.exists():
        raise RecoveryError("H41 rollback continuation is already consumed")
    _manifest, review_sha, closure = _original_context()
    return _approval(review_sha, closure)


def execute(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure = _original_context()
    if approval != _approval(review_sha, closure):
        raise RecoveryError("H41 rollback continuation approval mismatch")
    if CONT_DIR.exists() or ROLLBACK_LOG_DIR.exists() or HEALTH_LOG_DIR.exists():
        raise RecoveryError("H41 rollback continuation is already consumed")
    rollback_artifact = owner.BoundArtifact.open(manifest["rollback"], "rollback")
    try:
        runner = adapter.HostRunner(
            ROLLBACK_LOG_DIR,
            redactor=adapter.SerialRedactor(
                hashes=(manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"],)
            ),
        )
        fixed = adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])
        role, usb_digest, adb_digest = fixed._effect_inventory(rollback=True)
        if role != adapter.ADB_ROLE_NATIVE or adb_digest is not None:
            raise RecoveryError("exact sole H41 Native endpoint is required")
        rollback_artifact.checkpoint()
        CONT_DIR.mkdir(mode=0o700)
        owner._fsync_directory(CONT_DIR.parent)
        intent = {
            "approvalSha256": _sha(approval.encode("ascii")),
            "reviewSha256": review_sha,
            "executionClosureSha256": closure,
            "originalRollbackIntentSha256": ORIGINAL_ROLLBACK_INTENT_SHA256,
            "rollbackSha256": ROLLBACK_SHA256,
            "ownerUsbInventorySha256": usb_digest,
            "ownerAdbRole": role,
            "continuationWriteCount": 1,
            "candidateReplay": False,
            "originalRollbackReplay": False,
        }
        _publish("00-continuation-intent.json", intent)
        if _continuation_record("00-continuation-intent.json") != intent:
            raise RecoveryError("H41 continuation intent changed before effect")
        _original_context()
        rollback_artifact.checkpoint()
        effect = fixed.flash(
            manifest["rollback"], rollback=True,
            timeout_sec=manifest["timeouts"]["flashSec"],
            owner_usb_inventory_sha256=usb_digest,
            owner_adb_inventory_sha256=None,
            owner_adb_role=role,
        )
        effect.validate()
        rollback_artifact.checkpoint()
        _publish("10-rollback-result.json", effect.payload())
        _original_context()
        return {
            "state": (
                "V2321_SYSTEM_RETURN_CONFIRMED_CLOSE_MENU_THEN_FINALIZE"
                if effect.completed is True
                and effect.returncode == 0
                and effect.quiescent is True
                and effect.outcome == "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
                else "RECOVERY_REQUIRED"
            ),
            "candidateReplay": False,
            "originalRollbackReplay": False,
            "continuationRollbackReplay": False,
            "rollbackResult": effect.payload(),
        }
    finally:
        rollback_artifact.close()


def finalize(
    approval: str, *, operator_attended: bool = False,
    menu_closed_confirmed: bool = False,
) -> dict[str, Any]:
    if operator_attended is not True or menu_closed_confirmed is not True:
        raise RecoveryError("H41 health finalization requires attended closed-menu confirmation")
    if CONT_DIR.is_dir() and (CONT_DIR / "20-final.json").is_file():
        return _resume_final(approval)
    manifest, review_sha, closure = _original_context()
    if approval != _approval(review_sha, closure):
        raise RecoveryError("H41 rollback health approval mismatch")
    _private_dir(CONT_DIR, "H41 rollback continuation journal")
    if set(path.name for path in CONT_DIR.iterdir()) != {
        "00-continuation-intent.json", "10-rollback-result.json",
    } or HEALTH_LOG_DIR.exists():
        raise RecoveryError("H41 rollback health prefix is not exact")
    intent = _continuation_record("00-continuation-intent.json")
    if (
        intent.get("approvalSha256") != _sha(approval.encode("ascii"))
        or intent.get("reviewSha256") != review_sha
        or intent.get("executionClosureSha256") != closure
        or intent.get("originalRollbackIntentSha256") != ORIGINAL_ROLLBACK_INTENT_SHA256
        or intent.get("rollbackSha256") != ROLLBACK_SHA256
        or intent.get("ownerAdbRole") != adapter.ADB_ROLE_NATIVE
        or intent.get("continuationWriteCount") != 1
        or intent.get("candidateReplay") is not False
        or intent.get("originalRollbackReplay") is not False
    ):
        raise RecoveryError("H41 continuation intent binding changed")
    effect = _effect_result()
    if (
        effect.completed is not True
        or effect.returncode != 0
        or effect.quiescent is not True
        or effect.outcome != "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
    ):
        raise RecoveryError("confirmed V2321 System return is required for health finalization")
    health_intent = {
        "approvalSha256": _sha(approval.encode("ascii")),
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "rollbackReceiptSha256": effect.receipt_sha256,
        "healthObservationCount": 1,
        "operatorAttended": True,
        "menuClosedConfirmed": True,
        "candidateReplay": False,
        "rollbackReplay": False,
    }
    _publish("15-health-intent.json", health_intent)
    _original_context()
    runner = adapter.HostRunner(
        HEALTH_LOG_DIR,
        redactor=adapter.SerialRedactor(
            hashes=(manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"],)
        ),
    )
    fixed = adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])
    snapshot = fixed.observe(
        manifest["rollback"], manifest["qualification"]["freshState"],
        require_fresh_state=False, timeout_sec=manifest["timeouts"]["healthSec"],
    )
    snapshot.validate()
    healthy = _healthy_snapshot(snapshot, manifest)
    if not healthy:
        raise RecoveryError("post-rollback health is not exact V2321")
    final = {
        "decision": "V2321_HEALTHY_H41_RUN02_RECOVERED",
        "candidateReplay": False,
        "originalRollbackReplay": False,
        "continuationRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "rollbackResult": effect.payload(),
        "snapshot": snapshot.payload(),
        "rollbackLogHashes": _current_log_hashes(
            ROLLBACK_LOG_DIR, "H41 continuation rollback logs"
        ),
        "healthLogHashes": _current_log_hashes(
            HEALTH_LOG_DIR, "H41 continuation health logs"
        ),
    }
    raw = owner.canonical_json({
        "schema": RECORD_SCHEMA,
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "payload": final,
    })
    _publish("20-final.json", final)
    if _read(CONT_DIR / "20-final.json") != raw:
        raise RecoveryError("H41 recovery final readback changed")
    _validate_final_prefix(manifest, approval, review_sha, closure)
    _original_context()
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "execute", "finalize"))
    parser.add_argument("--approval")
    parser.add_argument("--operator-attended", action="store_true")
    parser.add_argument("--menu-closed-confirmed", action="store_true")
    args = parser.parse_args(argv)
    if args.mode == "prepare":
        if args.approval is not None:
            raise RecoveryError("prepare accepts no approval")
        print(prepare())
        return 0
    if args.approval is None:
        raise RecoveryError(f"{args.mode} requires approval")
    result = (
        execute(args.approval)
        if args.mode == "execute"
        else finalize(
            args.approval,
            operator_attended=args.operator_attended,
            menu_closed_confirmed=args.menu_closed_confirmed,
        )
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RecoveryError, owner.ContractError, adapter.ContractError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
