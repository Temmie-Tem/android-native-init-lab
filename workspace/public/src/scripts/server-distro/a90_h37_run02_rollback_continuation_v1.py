#!/usr/bin/env python3
"""Fixed rollback-only recovery for A90 H37 run-02.

The original rollback helper stopped before any boot write.  This capability
binds that exact incident and permits one newly journaled V2321 rollback from
an already-present, bound TWRP endpoint.  It has no candidate path.
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
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[5]
OWNER_PATH = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
ADAPTER_PATH = ROOT / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_adapter_v1.py"
H28_MENU_PATH = ROOT / "workspace/public/src/scripts/server-distro/a90_h28_menu_hide_health_reconcile_v1.py"
SELF_PATH = Path(__file__).resolve()
CONTRACT_PATH = ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md"
MANIFEST_PATH = ROOT / "workspace/private/manifests/a90-h37-f1-20260829-02.json"
RUN_ID = "a90-h37-f1-20260829-02"
MANIFEST_SHA256 = "2fedf1751898b8146de8c15b2ab3d5cb026085099ad1d37cb6a13be9a84d76ab"
RUN_ROOT = ROOT / "workspace/private/runs/a90-boot-only-f1-minimal-v1"
RUN_DIR = RUN_ROOT / RUN_ID
OLD_LOG_DIR = RUN_ROOT / f"{RUN_ID}-execute-1-logs"
CONT_DIR = RUN_ROOT / "a90-h37-run02-rollback-continuation-v1"
LIVE_LOG_DIR = RUN_ROOT / "a90-h37-run02-rollback-continuation-v1-logs"
INTENT_PATH = CONT_DIR / "00-intent.json"
RESULT_PATH = CONT_DIR / "10-rollback-result.json"
FINAL_PATH = CONT_DIR / "20-final.json"
FINALIZE_INTENT_PATH = CONT_DIR / "15-physical-return-finalize-intent.json"
FINALIZE_LOG_DIR = RUN_ROOT / "a90-h37-run02-rollback-continuation-v1-finalize-logs"
MENU_FINALIZE_INTENT_PATH = CONT_DIR / "16-menu-hide-finalize-intent.json"
MENU_FINALIZE_RECEIPT_PATH = CONT_DIR / "17-menu-hide-finalize-receipt.json"
MENU_FINALIZE_LOG_DIR = RUN_ROOT / "a90-h37-run02-rollback-continuation-v1-menu-hide-finalize-logs"
POST_HIDE_INTENT_PATH = CONT_DIR / "18-post-hide-health-intent.json"
POST_HIDE_LOG_DIR = RUN_ROOT / "a90-h37-run02-rollback-continuation-v1-post-hide-health-logs"
REVIEW_PATH = ROOT / "docs/reports/A90_H37_RUN02_ROLLBACK_CONTINUATION_V1_REVIEW.json"

CAPABILITY = "A90_H37_RUN02_ROLLBACK_CONTINUATION_V1"
REVIEW_SCHEMA = "a90-h37-run02-rollback-continuation-review-v1"
CONT_INTENT_SCHEMA = "a90-h37-run02-rollback-continuation-intent-v1"
CONT_RESULT_SCHEMA = "a90-h37-run02-rollback-continuation-result-v1"
CONT_FINAL_SCHEMA = "a90-h37-run02-rollback-continuation-final-v1"
CONT_FINAL_DECISION = "V2321_HEALTHY_H37_RUN02_RECOVERED"
APPROVAL_PREFIX = "A90-H37-RUN02-ROLLBACK-CONTINUE-V1-APPROVE:"
FINALIZE_APPROVAL_PREFIX = "A90-H37-RUN02-PHYSICAL-RETURN-FINALIZE-V1-APPROVE:"
MENU_FINALIZE_APPROVAL_PREFIX = "A90-H37-RUN02-MENU-HIDE-FINALIZE-V1-APPROVE:"
POST_HIDE_APPROVAL_PREFIX = "A90-H37-RUN02-POST-HIDE-HEALTH-V1-APPROVE:"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
RECORD_HASHES = {
    "00-prepared.json": "b2b6e87342acd9a27777a310ea46f4c5491c62b2d86be722d9c5dfb61c425a9d",
    "10-approved.json": "a41eb1fe081f82785d619884615c350d7447d53ac9c50c8a35688a379327363b",
    "11-recovery-transition-intent.json": "ca9c913ff4e52739160a442c0dcd72b834349d40bad5dd8c9ec20649f16a5f91",
    "12-recovery-ready.json": "9ce7cef0d2549d4a47f1d2736df101bed44055955ba99d2e16e6a22c8b2a17e0",
    "20-candidate-intent.json": "0d1396e0df56236195637bb72b42e0fda188185cba6c67cb7cb2baaa059613a9",
    "21-candidate-launched.json": "dabe7c04b54aa00e8e1ca87d45e651c6d216189cd5f8bf8fafc557b7926f6c8f",
    "22-candidate-result.json": "8864006ff139d530fc0e3b8aad387f7dd11766f58618124bfc334232525eca06",
    "26-failed-boot-evidence-intent.json": "3a8b7d001f21d54a83e6c9317aed1e6f9a34f69fd05d4446e2dbbe6c969a9565",
    "27-failed-boot-evidence-result.json": "805021a6070c77aad25f2ed7d00ae6cd4ad82d1d4558aa9fce99ab73439cc5d8",
    "30-rollback-intent.json": "d24efe7198d2207b76243fef446b403d63778b03dd236ac5966c4d595ae5092d",
    "31-rollback-launched.json": "2c2a71544f99d87221f6e9a21daf9194a6d58b7dfc2877075cdfb887e552c636",
    "32-rollback-result.json": "b263fc92aff3aa7dade75e3a8d5304962d04840511f6e443ea3c224eb4319bc3",
    "40-terminal.json": "199c5d61f5ec518d02ea01e81c4fd619f0512aad86fee0942b20def1926c91d9",
}
OLD_ROLLBACK_STDOUT_SHA256 = "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24"
OLD_ROLLBACK_STDERR_SHA256 = "6a328d4b047ddb73ff57dd68103f56b7b5f39f2f835bb8e8f3dd430cc4149e84"
FIXED_CANDIDATE_OUTCOME = "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
FIXED_ROLLBACK_RESULT = {
    "completed": False, "outcome": "PRE_WRITE_FAILURE", "quiescent": True,
    "receiptSha256": "a8a72b1af241914232d0e4d285f2707fdab12bc60826f0c4bed54de5c4f4912c",
    "returncode": 1,
}
OLD_ROLLBACK_REQUIRED_STDERR = b"native recovery command failed; minimal one-shot mode does not resend"
CONT_INTENT_SHA256 = "66665121effa178def07640760084bb02a5cb0083da3cd419f8d4a5c2d7ad191"
CONT_RESULT_SHA256 = "4b4dd3b8054b71c9fb9f7f1d609538a5c5c8394f2bbb2f13d86b698576888453"
CONT_FLASH_STDOUT_SHA256 = "2e26bf251052f5971314959a43c4f34d23d9f6e6dd8c00d8beadb3b37e6e0ee7"
CONT_FLASH_STDERR_SHA256 = "e9ec162f4b64c60cc93bd69a4ec1333a8835c3d62106474856f6ced84eaab1c5"
FINALIZE_INTENT_SHA256 = "64bae77418a5b25014ec2ec9b8df8153d61690ff088e3ee22d8a22ea99926b57"
FINALIZE_BUSY_LOG_HASHES = {
    "001-usb-inventory.stdout": "862a640ff98d422db8aa65d0b76ac1df447b492dcbc7d8b827342adbabb2efda",
    "001-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "98128fc109d245716b8230186b3543ce7a711611117c4ee2d29897cff447ff1d",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-boot-id-start.stdout": "481752d50ece0bd385422b7ae39716f336dca904e7d140dddb9cc351bb9132d3",
    "003-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
MENU_HIDE_WIRE_SHA256 = hashlib.sha256(b"hide\n").hexdigest()
MENU_FINALIZE_INTENT_SHA256 = "9a9215cf72cc2e7ae77e134e44da22ab1e64f2b4dc3233e0f7ea5dcc25ff6730"
MENU_HIDE_LOG_HASHES = {
    "001-usb-inventory-before.stdout": "862a640ff98d422db8aa65d0b76ac1df447b492dcbc7d8b827342adbabb2efda",
    "001-usb-inventory-before.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "2fd34d09502d3879339647f669fe239db529a6ff8ced147ec5a436b552e27952",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-menu-hide.stdout": "11b2317df962df98b76f4546d8465d14a38b782c962fb476dad3a8a70d8e8f76",
    "003-menu-hide.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
CLOSURE_PATHS = (
    SELF_PATH,
    CONTRACT_PATH,
    OWNER_PATH,
    ADAPTER_PATH,
    H28_MENU_PATH,
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
    pass


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RecoveryError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


owner = _load("a90_boot_only_f1_minimal_v1", OWNER_PATH)
adapter = _load("a90_boot_only_f1_adapter_v1", ADAPTER_PATH)
h28_menu = _load("_a90_h37_h28_menu_hide_engine_v1", H28_MENU_PATH)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(path: Path, maximum: int = 1 << 20) -> bytes:
    raw = owner._read_bounded_regular(path, path.name, maximum)
    return raw


def execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    for path in CLOSURE_PATHS:
        raw = path.read_bytes()
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(str(len(raw)).encode())
        digest.update(b"\0")
        digest.update(_sha(raw).encode())
        digest.update(b"\0")
    digest.update(b"A90-H37-H28-MENU-HIDE-TRANSITIVE-CLOSURE-V1\0")
    digest.update(h28_menu.execution_closure_sha256().encode("ascii"))
    digest.update(b"\0")
    return digest.hexdigest()


def _verify_historical_qualification(manifest: dict[str, Any]) -> None:
    descriptor = manifest["qualification"]["review"]
    raw = owner._verify_input(descriptor, "fixed H37 qualification review")
    review = owner.parse_canonical(raw, "fixed H37 qualification review")
    if (
        type(review) is not dict
        or review.get("verdict") != "PASS_GO"
        or review.get("candidateSha256") != manifest["candidate"]["sha256"]
        or review.get("rollbackSha256") != manifest["rollback"]["sha256"]
        or review.get("targetProfile") != manifest["targetProfile"]
        or review.get("recovery") != manifest["qualification"]["recovery"]
        or review.get("hazard") != manifest["qualification"]["hazard"]
        or review.get("freshState") != manifest["qualification"]["freshState"]
        or review.get("liveAuthority") is not False
    ):
        raise RecoveryError("fixed historical qualification review changed")


def _require_guards(manifest: dict[str, Any]) -> None:
    owner._require_active_guard(manifest)
    owner._require_candidate_guard(manifest)


def _review() -> tuple[str, str]:
    raw = _read(REVIEW_PATH)
    value = owner.parse_canonical(raw, "H37 run02 recovery review")
    expected = {
        "schema", "capability", "verdict", "executionClosureSha256",
        "findings", "contacts", "reviewer", "reviewDate", "liveAuthority",
    }
    if type(value) is not dict or set(value) != expected:
        raise RecoveryError("recovery review schema mismatch")
    findings = value["findings"]
    contacts = value["contacts"]
    if (
        value["schema"] != REVIEW_SCHEMA
        or value["capability"] != CAPABILITY
        or value["verdict"] != "PASS_GO"
        or value["executionClosureSha256"] != execution_closure_sha256()
        or type(findings) is not dict
        or set(findings) != {"high", "medium", "low"}
        or any(type(v) is not list or v for v in findings.values())
        or type(contacts) is not dict
        or set(contacts) != {"device", "dev", "usb", "network", "workspacePrivate", "otherTargets", "writes"}
        or any(type(v) is not int or v != 0 for v in contacts.values())
        or value["liveAuthority"] is not False
    ):
        raise RecoveryError("recovery review is not current PASS_GO")
    return _sha(raw), value["executionClosureSha256"]


def _fixed_context() -> tuple[dict[str, Any], str, str, str]:
    raw, manifest = owner.load_manifest(MANIFEST_PATH)
    if _sha(raw) != MANIFEST_SHA256 or manifest["runId"] != RUN_ID:
        raise RecoveryError("fixed manifest changed")
    records = owner.read_records(RUN_DIR)
    if tuple(records) != tuple(RECORD_HASHES):
        raise RecoveryError("fixed journal path changed")
    for name, expected in RECORD_HASHES.items():
        if _sha(_read(RUN_DIR / name)) != expected:
            raise RecoveryError(f"fixed record changed: {name}")
    candidate = records["22-candidate-result.json"]["payload"]
    rollback = records["32-rollback-result.json"]["payload"]
    terminal = records["40-terminal.json"]["payload"]
    if (
        candidate.get("completed") is not True
        or candidate.get("outcome") != FIXED_CANDIDATE_OUTCOME
        or rollback != FIXED_ROLLBACK_RESULT
        or terminal.get("terminal") != "RECOVERY_REQUIRED"
        or terminal.get("reason") != "ROLLBACK_HEALTH_UNPROVED"
        or terminal.get("candidateReplay") is not False
    ):
        raise RecoveryError("fixed incident classification changed")
    if _sha(_read(OLD_LOG_DIR / "047-flash-rollback.stdout")) != OLD_ROLLBACK_STDOUT_SHA256:
        raise RecoveryError("old rollback stdout changed")
    stderr = _read(OLD_LOG_DIR / "047-flash-rollback.stderr")
    if (
        _sha(stderr) != OLD_ROLLBACK_STDERR_SHA256
        or OLD_ROLLBACK_REQUIRED_STDERR not in stderr
        or b"phase.native_init_flash.adb_push." in stderr
        or b"phase.native_init_flash.boot_dd_write." in stderr
        or b"phase.native_init_flash.boot_readback_sha256." in stderr
    ):
        raise RecoveryError("old rollback log is not exact pre-write failure")
    _verify_historical_qualification(manifest)
    _require_guards(manifest)
    bound = owner.BoundArtifact.open(manifest["rollback"], "rollback")
    os.close(bound.fd)
    review_sha, closure = _review()
    token_payload = {
        "capability": CAPABILITY, "manifestSha256": MANIFEST_SHA256,
        "rollbackSha256": ROLLBACK_SHA256, "reviewSha256": review_sha,
        "executionClosureSha256": closure,
    }
    return manifest, review_sha, closure, APPROVAL_PREFIX + _sha(owner.canonical_json(token_payload))


def _publish(path: Path, value: dict[str, Any]) -> None:
    raw = owner.canonical_json(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        if os.write(fd, raw) != len(raw):
            raise RecoveryError("sidecar short write")
        os.fsync(fd)
    finally:
        os.close(fd)
    owner._fsync_directory(path.parent)


def prepare() -> str:
    if CONT_DIR.exists() or LIVE_LOG_DIR.exists():
        raise RecoveryError("rollback continuation is already consumed")
    _manifest, _review_sha, _closure, token = _fixed_context()
    return token


def _consumed_uncertain_effect() -> dict[str, Any]:
    if (
        _sha(_read(INTENT_PATH)) != CONT_INTENT_SHA256
        or _sha(_read(RESULT_PATH)) != CONT_RESULT_SHA256
        or _sha(_read(LIVE_LOG_DIR / "003-flash-rollback.stdout"))
        != CONT_FLASH_STDOUT_SHA256
        or _sha(_read(LIVE_LOG_DIR / "003-flash-rollback.stderr"))
        != CONT_FLASH_STDERR_SHA256
    ):
        raise RecoveryError("consumed rollback continuation evidence changed")
    result_record = owner.parse_canonical(_read(RESULT_PATH), "continuation result")
    result = result_record.get("result") if type(result_record) is dict else None
    expected = {
        "completed": False,
        "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        "quiescent": True,
        "receiptSha256": "b62cc061b14e769397972ceae628b2c1411dac0781b94943d3fb41c261c00d02",
        "returncode": 1,
    }
    receipt = owner.parse_canonical(
        _read(LIVE_LOG_DIR / "003-flash-rollback.stdout"), "continuation helper receipt"
    )
    if (
        result_record.get("schema") != CONT_RESULT_SCHEMA
        or result != expected
        or receipt.get("outcome") != expected["outcome"]
        or receipt.get("writeStarted") is not True
        or receipt.get("bootWrittenReadbackExact") is not True
        or receipt.get("systemReturnAttempted") is not True
        or receipt.get("systemReturnCommandOk") is not True
        or receipt.get("systemReturnConfirmed") is not False
    ):
        raise RecoveryError("consumed rollback is not exact uncertain System return")
    return result


def prepare_finalize() -> str:
    manifest, review_sha, closure, _token = _fixed_context()
    _consumed_uncertain_effect()
    if FINALIZE_INTENT_PATH.exists() or FINAL_PATH.exists() or FINALIZE_LOG_DIR.exists():
        raise RecoveryError("physical-return finalizer is already consumed")
    payload = {
        "capability": CAPABILITY,
        "phase": "physical-system-return-health-only",
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
    }
    return FINALIZE_APPROVAL_PREFIX + _sha(owner.canonical_json(payload))


def _revalidate_finalize_inputs(
    manifest: dict[str, Any], review_sha: str, closure: str
) -> None:
    current_review_sha, current_closure = _review()
    if current_review_sha != review_sha or current_closure != closure:
        raise RecoveryError("physical-return finalizer review lease changed")
    _verify_historical_qualification(manifest)
    _consumed_uncertain_effect()
    _require_guards(manifest)


def finalize_physical_return(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure, _token = _fixed_context()
    rollback_result = _consumed_uncertain_effect()
    expected = prepare_finalize()
    if approval != expected:
        raise RecoveryError("physical-return finalizer approval mismatch")
    _require_guards(manifest)
    _publish(FINALIZE_INTENT_PATH, {
        "schema": "a90-h37-run02-physical-return-finalize-intent-v1",
        "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "rollbackReplay": False,
        "healthObservationOnly": True,
    })
    _revalidate_finalize_inputs(manifest, review_sha, closure)
    runner = adapter.HostRunner(FINALIZE_LOG_DIR)
    fixed = adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])
    snapshot = fixed.observe(
        manifest["rollback"], manifest["qualification"]["freshState"],
        require_fresh_state=False, timeout_sec=manifest["timeouts"]["healthSec"],
    )
    snapshot.validate()
    if (
        not snapshot.healthy or not snapshot.recovery_available
        or not snapshot.other_targets_untouched
        or (snapshot.version, snapshot.build)
        != (manifest["rollback"]["version"], manifest["rollback"]["build"])
    ):
        raise RecoveryError("physical System return did not establish exact V2321 health")
    final = {
        "schema": "a90-h37-run02-rollback-continuation-final-v1",
        "decision": "V2321_HEALTHY_AFTER_OPERATOR_REPORTED_PHYSICAL_SYSTEM_RETURN",
        "candidateReplay": False,
        "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "helperOutcome": rollback_result["outcome"],
        "helperOutcomePromoted": False,
        "operatorReportedPhysicalSystemReturn": True,
        "physicalButtonActionHostProved": False,
        "snapshot": snapshot.payload(),
    }
    _revalidate_finalize_inputs(manifest, review_sha, closure)
    expected_raw = owner.canonical_json(final)
    _publish(FINAL_PATH, final)
    if _read(FINAL_PATH) != expected_raw:
        raise RecoveryError("physical-return final sidecar readback mismatch")
    _revalidate_finalize_inputs(manifest, review_sha, closure)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def _consumed_finalize_busy() -> None:
    if _sha(_read(FINALIZE_INTENT_PATH)) != FINALIZE_INTENT_SHA256:
        raise RecoveryError("consumed physical-return finalizer intent changed")
    intent = owner.parse_canonical(_read(FINALIZE_INTENT_PATH), "physical-return finalizer intent")
    if (
        type(intent) is not dict
        or intent.get("schema") != "a90-h37-run02-physical-return-finalize-intent-v1"
        or intent.get("capability") != CAPABILITY
        or intent.get("manifestSha256") != MANIFEST_SHA256
        or intent.get("rollbackResultSha256") != CONT_RESULT_SHA256
        or intent.get("rollbackReplay") is not False
        or intent.get("healthObservationOnly") is not True
    ):
        raise RecoveryError("consumed physical-return finalizer intent is not exact")
    try:
        names = {path.name for path in FINALIZE_LOG_DIR.iterdir()}
    except OSError as exc:
        raise RecoveryError("consumed finalizer logs unavailable") from exc
    if names != set(FINALIZE_BUSY_LOG_HASHES) | {".adb-home"}:
        raise RecoveryError("consumed finalizer log inventory changed")
    adb_home = FINALIZE_LOG_DIR / ".adb-home"
    try:
        if {path.name for path in adb_home.iterdir()} != {".android"}:
            raise RecoveryError("consumed finalizer inert ADB home changed")
        if any((adb_home / ".android").iterdir()):
            raise RecoveryError("consumed finalizer inert ADB config is not empty")
    except OSError as exc:
        raise RecoveryError("consumed finalizer inert ADB home unavailable") from exc
    for name, expected in FINALIZE_BUSY_LOG_HASHES.items():
        path = FINALIZE_LOG_DIR / name
        try:
            before = path.lstat()
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_uid != os.getuid()
                or before.st_gid != os.getgid()
                or before.st_mode & 0o022
                or before.st_size > (1 << 20)
            ):
                raise RecoveryError(f"consumed finalizer log identity changed: {name}")
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                current = os.fstat(fd)
                raw = os.pread(fd, current.st_size, 0)
                if (
                    (current.st_dev, current.st_ino, current.st_size)
                    != (before.st_dev, before.st_ino, before.st_size)
                    or len(raw) != current.st_size
                    or os.pread(fd, 1, current.st_size)
                ):
                    raise RecoveryError(f"consumed finalizer log changed while reading: {name}")
            finally:
                os.close(fd)
        except OSError as exc:
            raise RecoveryError(f"consumed finalizer log unavailable: {name}") from exc
        if _sha(raw) != expected:
            raise RecoveryError(f"consumed finalizer log changed: {name}")
    try:
        response = h28_menu.adapter._json(
            _read(FINALIZE_LOG_DIR / "003-boot-id-start.stdout"),
            "H37 run02 busy boot-id receipt",
        )
    except Exception as exc:
        raise RecoveryError("consumed busy boot-id receipt is invalid") from exc
    if (
        type(response) is not dict
        or set(response) != {"begin", "end", "rc", "status", "trust", "text"}
        or response["begin"] != {"seq": "1", "cmd": "cat", "argc": "2", "flags": "0x0"}
        or response["rc"] != -16
        or response["status"] != "busy"
        or response["trust"] != "A90P1_V1_STRUCTURAL_ONLY"
        or type(response["text"]) is not str
        or "[busy] auto menu active; send hide/q before command" not in response["text"]
    ):
        raise RecoveryError("consumed boot-id response is not exact menu EBUSY")
    end = response["end"]
    if (
        type(end) is not dict
        or set(end) != {"seq", "cmd", "rc", "errno", "duration_ms", "flags", "status"}
        or end["seq"] != "1"
        or end["cmd"] != "cat"
        or end["rc"] != "-16"
        or end["errno"] != "16"
        or not str(end["duration_ms"]).isdigit()
        or end["flags"] != "0x0"
        or end["status"] != "busy"
    ):
        raise RecoveryError("consumed boot-id EBUSY end frame changed")


def prepare_menu_finalize() -> str:
    manifest, review_sha, closure, _token = _fixed_context()
    _consumed_uncertain_effect()
    _consumed_finalize_busy()
    if (
        FINAL_PATH.exists()
        or MENU_FINALIZE_INTENT_PATH.exists()
        or MENU_FINALIZE_RECEIPT_PATH.exists()
        or MENU_FINALIZE_LOG_DIR.exists()
    ):
        raise RecoveryError("menu-hide finalizer is already consumed")
    payload = {
        "capability": CAPABILITY,
        "phase": "menu-hide-physical-return-health-only",
        "manifestSha256": MANIFEST_SHA256,
        "physicalReturnFinalizeIntentSha256": FINALIZE_INTENT_SHA256,
        "busyLogSetSha256": _sha(owner.canonical_json(FINALIZE_BUSY_LOG_HASHES)),
        "menuHideWireSha256": MENU_HIDE_WIRE_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
    }
    return MENU_FINALIZE_APPROVAL_PREFIX + _sha(owner.canonical_json(payload))


def _menu_intent_value(approval: str, review_sha: str, closure: str) -> dict[str, Any]:
    return {
        "schema": "a90-h37-run02-menu-hide-finalize-intent-v1",
        "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "physicalReturnFinalizeIntentSha256": FINALIZE_INTENT_SHA256,
        "busyLogSetSha256": _sha(owner.canonical_json(FINALIZE_BUSY_LOG_HASHES)),
        "command": "hide",
        "wireSha256": MENU_HIDE_WIRE_SHA256,
        "sendCount": 1,
        "candidateReplay": False,
        "rollbackReplay": False,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "approvalSha256": _sha(approval.encode("ascii")),
    }


def _require_menu_intent(approval: str, review_sha: str, closure: str) -> str:
    expected = owner.canonical_json(_menu_intent_value(approval, review_sha, closure))
    if _read(MENU_FINALIZE_INTENT_PATH) != expected:
        raise RecoveryError("menu-hide finalizer intent changed")
    return _sha(expected)


def _revalidate_menu_inputs(
    manifest: dict[str, Any], approval: str, review_sha: str, closure: str
) -> str:
    current_review_sha, current_closure = _review()
    if (current_review_sha, current_closure) != (review_sha, closure):
        raise RecoveryError("menu-hide finalizer review lease changed")
    _verify_historical_qualification(manifest)
    _consumed_uncertain_effect()
    _consumed_finalize_busy()
    _require_guards(manifest)
    return _require_menu_intent(approval, review_sha, closure)


def menu_hide_finalize(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure, _token = _fixed_context()
    rollback_result = _consumed_uncertain_effect()
    _consumed_finalize_busy()
    expected = prepare_menu_finalize()
    if approval != expected:
        raise RecoveryError("menu-hide finalizer approval mismatch")
    _publish(MENU_FINALIZE_INTENT_PATH, _menu_intent_value(approval, review_sha, closure))
    intent_sha = _revalidate_menu_inputs(manifest, approval, review_sha, closure)
    serial_sha = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    if type(serial_sha) is not str or owner.SHA256_RE.fullmatch(serial_sha) is None:
        raise RecoveryError("fixed recovery serial hash is invalid")
    redactor = h28_menu.adapter.SerialRedactor(hashes=(serial_sha,))
    runner = h28_menu.adapter.HostRunner(MENU_FINALIZE_LOG_DIR, redactor=redactor)
    qualification = dict(manifest["qualification"])
    review_raw = _read(REVIEW_PATH)
    qualification["review"] = {
        "path": str(REVIEW_PATH), "size": len(review_raw), "sha256": review_sha,
    }
    observer = h28_menu.MenuHideObserver(runner, qualification=qualification)
    try:
        observation = observer.observe(
            manifest["rollback"], timeout_sec=manifest["timeouts"]["healthSec"]
        )
        h28_menu._validate_observation(observation, manifest["rollback"], review_sha)
    except Exception as exc:
        raise RecoveryError("one-shot menu-hide V2321 observation failed") from exc
    receipt = {
        "schema": "a90-h37-run02-menu-hide-finalize-receipt-v1",
        "capability": CAPABILITY,
        "intentSha256": intent_sha,
        "menuHideReceiptSha256": observation.hide_receipt_sha256,
        "wireSha256": MENU_HIDE_WIRE_SHA256,
        "sendCount": 1,
        "candidateReplay": False,
        "rollbackReplay": False,
    }
    _publish(MENU_FINALIZE_RECEIPT_PATH, receipt)
    if _read(MENU_FINALIZE_RECEIPT_PATH) != owner.canonical_json(receipt):
        raise RecoveryError("menu-hide receipt readback mismatch")
    _revalidate_menu_inputs(manifest, approval, review_sha, closure)
    final = {
        "schema": "a90-h37-run02-rollback-continuation-final-v1",
        "decision": "V2321_HEALTHY_AFTER_OPERATOR_REPORTED_PHYSICAL_RETURN_AND_MENU_HIDE",
        "candidateReplay": False,
        "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "helperOutcome": rollback_result["outcome"],
        "helperOutcomePromoted": False,
        "operatorReportedPhysicalSystemReturn": True,
        "physicalButtonActionHostProved": False,
        "priorHealthObservationOutcome": "MENU_BUSY_NO_HEALTH_PROOF",
        "menuHideSendCount": 1,
        "menuHideIntentSha256": intent_sha,
        "menuHideReceiptSha256": observation.hide_receipt_sha256,
        "sameBoot": observation.same_boot,
        "finalBootId": observation.final_boot_id,
        "snapshot": observation.snapshot.payload(),
    }
    expected_raw = owner.canonical_json(final)
    _publish(FINAL_PATH, final)
    if _read(FINAL_PATH) != expected_raw:
        raise RecoveryError("menu-hide final sidecar readback mismatch")
    _revalidate_menu_inputs(manifest, approval, review_sha, closure)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def _read_exact_log_set(directory: Path, hashes: dict[str, str], label: str) -> dict[str, bytes]:
    try:
        names = {path.name for path in directory.iterdir()}
    except OSError as exc:
        raise RecoveryError(f"{label} log directory unavailable") from exc
    if names != set(hashes) | {".adb-home"}:
        raise RecoveryError(f"{label} log inventory changed")
    try:
        adb_home = directory / ".adb-home"
        if {path.name for path in adb_home.iterdir()} != {".android"}:
            raise RecoveryError(f"{label} inert ADB home changed")
        if any((adb_home / ".android").iterdir()):
            raise RecoveryError(f"{label} inert ADB config is not empty")
    except OSError as exc:
        raise RecoveryError(f"{label} inert ADB home unavailable") from exc
    result: dict[str, bytes] = {}
    for name, expected in hashes.items():
        path = directory / name
        try:
            before = path.lstat()
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_uid != os.getuid()
                or before.st_gid != os.getgid()
                or before.st_mode & 0o022
                or before.st_size > (1 << 20)
            ):
                raise RecoveryError(f"{label} log identity changed: {name}")
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                current = os.fstat(fd)
                raw = os.pread(fd, current.st_size, 0)
                if (
                    (current.st_dev, current.st_ino, current.st_size)
                    != (before.st_dev, before.st_ino, before.st_size)
                    or len(raw) != current.st_size
                    or os.pread(fd, 1, current.st_size)
                ):
                    raise RecoveryError(f"{label} log changed while reading: {name}")
            finally:
                os.close(fd)
        except OSError as exc:
            raise RecoveryError(f"{label} log unavailable: {name}") from exc
        if _sha(raw) != expected:
            raise RecoveryError(f"{label} log changed: {name}")
        result[name] = raw
    return result


def _consumed_menu_hide_request(*, allow_final: bool = False) -> None:
    if _sha(_read(MENU_FINALIZE_INTENT_PATH)) != MENU_FINALIZE_INTENT_SHA256:
        raise RecoveryError("consumed menu-hide intent changed")
    intent = owner.parse_canonical(_read(MENU_FINALIZE_INTENT_PATH), "menu-hide intent")
    if (
        type(intent) is not dict
        or intent.get("schema") != "a90-h37-run02-menu-hide-finalize-intent-v1"
        or intent.get("capability") != CAPABILITY
        or intent.get("manifestSha256") != MANIFEST_SHA256
        or intent.get("physicalReturnFinalizeIntentSha256") != FINALIZE_INTENT_SHA256
        or intent.get("command") != "hide"
        or intent.get("wireSha256") != MENU_HIDE_WIRE_SHA256
        or intent.get("sendCount") != 1
        or intent.get("candidateReplay") is not False
        or intent.get("rollbackReplay") is not False
    ):
        raise RecoveryError("consumed menu-hide intent is not exact")
    logs = _read_exact_log_set(MENU_FINALIZE_LOG_DIR, MENU_HIDE_LOG_HASHES, "menu-hide")
    if logs["003-menu-hide.stdout"] != b"hide\r\n[busy] auto menu active; hide requested\r\n":
        raise RecoveryError("menu-hide response is not the fixed accepted request")
    if logs["003-menu-hide.stderr"]:
        raise RecoveryError("menu-hide response has unexpected stderr")
    if MENU_FINALIZE_RECEIPT_PATH.exists() or (FINAL_PATH.exists() and not allow_final):
        raise RecoveryError("failed menu-hide session unexpectedly published success")


class PostHideObserver(h28_menu.MenuHideObserver):
    """Read exact V2321 health after the already-consumed accepted hide request."""

    def observe_post_hide(self, expected: dict[str, Any], *, timeout_sec: int) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_sec
        usb_before = h28_menu.adapter._validate_usb_inventory(
            self.runner.run(
                "usb-inventory-before", (str(h28_menu.adapter.LSUSB),),
                self._remaining(deadline, cap=10),
            )
        )
        bridge = h28_menu.adapter._validate_bridge(
            self._json_command(
                "bridge-preflight",
                (
                    str(h28_menu.adapter.PYTHON), str(h28_menu.adapter.BRIDGE),
                    "preflight", "--device", h28_menu.adapter.FIXED_SERIAL,
                    "--device-glob", h28_menu.adapter.FIXED_SERIAL,
                    "--pin-selected-realpath", "--json",
                ),
                self._remaining(deadline, cap=10),
            )
        )
        receipts: dict[str, Any] = {}
        receipts["bootId"] = self._a90ctl(
            "boot-id", ["cat", "/proc/sys/kernel/random/boot_id"],
            self._remaining(deadline, cap=15),
        )
        receipts["version"] = self._a90ctl(
            "version", ["version"], self._remaining(deadline, cap=15)
        )
        receipts["selftest"] = self._a90ctl(
            "selftest", ["selftest"], self._remaining(deadline, cap=15)
        )
        receipts["status"] = self._a90ctl(
            "status", ["status"], self._remaining(deadline, cap=15)
        )
        receipts["bootIdFinal"] = self._a90ctl(
            "boot-id-final", ["cat", "/proc/sys/kernel/random/boot_id"],
            self._remaining(deadline, cap=15),
        )
        usb_after = h28_menu.adapter._validate_usb_inventory(
            self.runner.run(
                "usb-inventory-after", (str(h28_menu.adapter.LSUSB),),
                self._remaining(deadline, cap=10),
            )
        )
        if usb_before != usb_after:
            raise RecoveryError("post-hide USB target or foreign inventory changed")
        boot_text = h28_menu.adapter._validate_command(
            receipts["bootId"], ["cat", "/proc/sys/kernel/random/boot_id"], "boot ID"
        )
        version_text = h28_menu.adapter._validate_command(
            receipts["version"], ["version"], "version"
        )
        selftest_text = h28_menu.adapter._validate_command(
            receipts["selftest"], ["selftest"], "selftest"
        )
        h28_menu.adapter._validate_command(receipts["status"], ["status"], "status")
        final_text = h28_menu.adapter._validate_command(
            receipts["bootIdFinal"], ["cat", "/proc/sys/kernel/random/boot_id"],
            "final boot ID",
        )
        boot_id = h28_menu.adapter._one_line(
            boot_text, h28_menu.adapter.BOOT_ID_RE, "first boot ID"
        ).group(0)
        final_boot_id = h28_menu.adapter._one_line(
            final_text, h28_menu.adapter.BOOT_ID_RE, "final boot ID"
        ).group(0)
        version = h28_menu.adapter._one_line(
            version_text, h28_menu.adapter.VERSION_RE, "resident version"
        )
        h28_menu.adapter._one_line(
            selftest_text, h28_menu.adapter.SELFTEST_RE, "resident selftest"
        )
        same_boot = boot_id == final_boot_id
        healthy = (
            (version.group("version"), version.group("build"))
            == (expected["version"], expected["build"])
            and same_boot
        )
        stable = {
            "usbBefore": usb_before, "usbAfter": usb_after, "bridge": bridge,
            "bootId": boot_id, "finalBootId": final_boot_id,
            "version": version.group("version"), "build": version.group("build"),
            "recoveryEvidenceSha256": self.recovery_evidence_sha256,
        }
        evidence = {
            "stableIdentity": stable,
            "commandOrder": ["boot-id", "version", "selftest", "status", "boot-id-final"],
            "commands": {key: h28_menu._json_sha(receipts[key]) for key in sorted(receipts)},
        }
        snapshot = owner.Snapshot(
            target_evidence_sha256=_sha(owner.canonical_json(stable)),
            boot_id=boot_id, version=version.group("version"), build=version.group("build"),
            healthy=healthy, recovery_available=True,
            recovery_evidence_sha256=self.recovery_evidence_sha256,
            fresh_state_observed=False, fresh_state_absent=False,
            other_targets_untouched=(
                usb_before == usb_after and usb_before["a90EndpointCount"] == 1
            ),
            receipt_sha256=_sha(owner.canonical_json({"evidence": evidence, "healthy": healthy})),
        )
        return {
            "snapshot": snapshot, "finalBootId": final_boot_id, "sameBoot": same_boot,
            "commandOrder": ("boot-id", "version", "selftest", "status", "boot-id-final"),
        }


def _validate_post_hide_observation(
    observation: Any, expected: dict[str, Any], review_sha: str
) -> owner.Snapshot:
    if (
        type(observation) is not dict
        or set(observation) != {"snapshot", "finalBootId", "sameBoot", "commandOrder"}
        or observation["commandOrder"]
        != ("boot-id", "version", "selftest", "status", "boot-id-final")
        or observation["sameBoot"] is not True
    ):
        raise RecoveryError("post-hide observation order or boot continuity is invalid")
    snapshot = observation["snapshot"]
    snapshot.validate()
    if (
        observation["finalBootId"] != snapshot.boot_id
        or snapshot.healthy is not True
        or snapshot.recovery_available is not True
        or snapshot.recovery_evidence_sha256 != review_sha
        or snapshot.fresh_state_observed is not False
        or snapshot.fresh_state_absent is not False
        or snapshot.other_targets_untouched is not True
        or (snapshot.version, snapshot.build) != (expected["version"], expected["build"])
    ):
        raise RecoveryError("post-hide health is not exact V2321")
    return snapshot


def prepare_post_hide() -> str:
    _manifest, review_sha, closure, _token = _fixed_context()
    _consumed_uncertain_effect(); _consumed_finalize_busy(); _consumed_menu_hide_request()
    if POST_HIDE_INTENT_PATH.exists() or POST_HIDE_LOG_DIR.exists() or FINAL_PATH.exists():
        raise RecoveryError("post-hide health continuation is already consumed")
    payload = {
        "capability": CAPABILITY, "phase": "post-accepted-hide-health-only",
        "manifestSha256": MANIFEST_SHA256,
        "menuHideIntentSha256": MENU_FINALIZE_INTENT_SHA256,
        "menuHideLogSetSha256": _sha(owner.canonical_json(MENU_HIDE_LOG_HASHES)),
        "reviewSha256": review_sha, "executionClosureSha256": closure,
    }
    return POST_HIDE_APPROVAL_PREFIX + _sha(owner.canonical_json(payload))


def _post_hide_intent_value(approval: str, review_sha: str, closure: str) -> dict[str, Any]:
    return {
        "schema": "a90-h37-run02-post-hide-health-intent-v1", "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "menuHideIntentSha256": MENU_FINALIZE_INTENT_SHA256,
        "menuHideLogSetSha256": _sha(owner.canonical_json(MENU_HIDE_LOG_HASHES)),
        "hideSendAllowed": False, "healthObservationOnly": True,
        "candidateReplay": False, "rollbackReplay": False,
        "reviewSha256": review_sha, "executionClosureSha256": closure,
        "approvalSha256": _sha(approval.encode("ascii")),
    }


def _revalidate_post_hide_inputs(
    manifest: dict[str, Any], approval: str, review_sha: str, closure: str,
    *, allow_final: bool = False,
) -> str:
    current_review_sha, current_closure = _review()
    if (current_review_sha, current_closure) != (review_sha, closure):
        raise RecoveryError("post-hide review lease changed")
    _verify_historical_qualification(manifest)
    _consumed_uncertain_effect(); _consumed_finalize_busy()
    _consumed_menu_hide_request(allow_final=allow_final)
    _require_guards(manifest)
    raw = owner.canonical_json(_post_hide_intent_value(approval, review_sha, closure))
    if _read(POST_HIDE_INTENT_PATH) != raw:
        raise RecoveryError("post-hide intent changed")
    return _sha(raw)


def post_hide_finalize(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure, _token = _fixed_context()
    rollback_result = _consumed_uncertain_effect()
    _consumed_finalize_busy(); _consumed_menu_hide_request()
    if approval != prepare_post_hide():
        raise RecoveryError("post-hide approval mismatch")
    _publish(POST_HIDE_INTENT_PATH, _post_hide_intent_value(approval, review_sha, closure))
    intent_sha = _revalidate_post_hide_inputs(manifest, approval, review_sha, closure)
    serial_sha = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    redactor = h28_menu.adapter.SerialRedactor(hashes=(serial_sha,))
    runner = h28_menu.adapter.HostRunner(POST_HIDE_LOG_DIR, redactor=redactor)
    qualification = dict(manifest["qualification"])
    review_raw = _read(REVIEW_PATH)
    qualification["review"] = {
        "path": str(REVIEW_PATH), "size": len(review_raw), "sha256": review_sha,
    }
    observer = PostHideObserver(runner, qualification=qualification)
    try:
        observation = observer.observe_post_hide(
            manifest["rollback"], timeout_sec=manifest["timeouts"]["healthSec"]
        )
        snapshot = _validate_post_hide_observation(
            observation, manifest["rollback"], review_sha
        )
    except Exception as exc:
        raise RecoveryError("one-shot post-hide V2321 observation failed") from exc
    _revalidate_post_hide_inputs(manifest, approval, review_sha, closure)
    final = {
        "schema": "a90-h37-run02-rollback-continuation-final-v1",
        "decision": "V2321_HEALTHY_AFTER_ACCEPTED_HIDE_REQUEST",
        "candidateReplay": False, "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "helperOutcome": rollback_result["outcome"], "helperOutcomePromoted": False,
        "operatorReportedPhysicalSystemReturn": True,
        "physicalButtonActionHostProved": False,
        "priorHealthObservationOutcome": "MENU_BUSY_NO_HEALTH_PROOF",
        "menuHideRequestOutcome": "ACCEPTED_BY_FIXED_NATIVE_RESPONSE",
        "menuHideSendCount": 1, "postHideAdditionalSendCount": 0,
        "menuHideIntentSha256": MENU_FINALIZE_INTENT_SHA256,
        "postHideIntentSha256": intent_sha,
        "sameBoot": observation["sameBoot"],
        "finalBootId": observation["finalBootId"], "snapshot": snapshot.payload(),
    }
    expected_raw = owner.canonical_json(final)
    _publish(FINAL_PATH, final)
    if _read(FINAL_PATH) != expected_raw:
        raise RecoveryError("post-hide final sidecar readback mismatch")
    _revalidate_post_hide_inputs(
        manifest, approval, review_sha, closure, allow_final=True
    )
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def _finalize(manifest: dict[str, Any], runner: Any, effect: Any) -> dict[str, Any]:
    _require_guards(manifest)
    fixed = adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])
    snapshot = fixed.observe(
        manifest["rollback"], manifest["qualification"]["freshState"],
        require_fresh_state=False, timeout_sec=manifest["timeouts"]["healthSec"],
    )
    snapshot.validate()
    if (
        not effect.completed or effect.returncode != 0 or not effect.quiescent
        or effect.outcome != "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
        or not snapshot.healthy or not snapshot.recovery_available
        or not snapshot.other_targets_untouched
        or (snapshot.version, snapshot.build)
        != (manifest["rollback"]["version"], manifest["rollback"]["build"])
    ):
        raise RecoveryError("V2321 rollback or final health is not exact")
    final = {
        "schema": CONT_FINAL_SCHEMA,
        "decision": CONT_FINAL_DECISION,
        "candidateReplay": False, "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "rollbackResult": effect.payload(), "snapshot": snapshot.payload(),
    }
    _require_guards(manifest)
    expected_final = owner.canonical_json(final)
    _publish(FINAL_PATH, final)
    if _read(FINAL_PATH) != expected_final:
        raise RecoveryError("final sidecar readback mismatch")
    _require_guards(manifest)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def execute(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure, expected = _fixed_context()
    if approval != expected or CONT_DIR.exists() or LIVE_LOG_DIR.exists():
        raise RecoveryError("approval mismatch or continuation already consumed")
    runner = adapter.HostRunner(LIVE_LOG_DIR)
    fixed = adapter.FixedA90Adapter(runner, qualification=manifest["qualification"])
    role, usb_digest, adb_digest = fixed._effect_inventory(rollback=True)
    if role != adapter.ADB_ROLE_RECOVERY or adb_digest is None:
        raise RecoveryError("already-present bound TWRP Recovery is required")
    _verify_historical_qualification(manifest)
    _require_guards(manifest)
    CONT_DIR.mkdir(mode=0o700)
    owner._fsync_directory(CONT_DIR.parent)
    _publish(INTENT_PATH, {
        "schema": CONT_INTENT_SCHEMA,
        "capability": CAPABILITY, "manifestSha256": MANIFEST_SHA256,
        "rollbackSha256": ROLLBACK_SHA256, "reviewSha256": review_sha,
        "executionClosureSha256": closure, "candidateReplay": False,
        "originalRollbackReplay": False, "incidentContinuationWriteAllowed": True,
    })
    _verify_historical_qualification(manifest)
    _require_guards(manifest)
    effect = fixed.flash(
        manifest["rollback"], rollback=True,
        timeout_sec=manifest["timeouts"]["flashSec"],
        owner_usb_inventory_sha256=usb_digest,
        owner_adb_inventory_sha256=adb_digest,
        owner_adb_role=role,
    )
    effect.validate()
    _publish(RESULT_PATH, {
        "schema": CONT_RESULT_SCHEMA,
        "result": effect.payload(),
    })
    return _finalize(manifest, runner, effect)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "prepare", "execute", "prepare-finalize", "finalize",
            "prepare-menu-finalize", "menu-finalize",
            "prepare-post-hide", "post-hide-finalize",
        ),
    )
    parser.add_argument("--approval")
    args = parser.parse_args()
    if args.mode == "prepare":
        if args.approval is not None:
            raise RecoveryError("prepare accepts no approval")
        print(prepare())
    elif args.mode == "execute":
        if args.approval is None:
            raise RecoveryError("execute requires approval")
        print(json.dumps(execute(args.approval), sort_keys=True))
    elif args.mode == "prepare-finalize":
        if args.approval is not None:
            raise RecoveryError("prepare-finalize accepts no approval")
        print(prepare_finalize())
    elif args.mode == "finalize":
        if args.approval is None:
            raise RecoveryError("finalize requires approval")
        print(json.dumps(finalize_physical_return(args.approval), sort_keys=True))
    elif args.mode == "prepare-menu-finalize":
        if args.approval is not None:
            raise RecoveryError("prepare-menu-finalize accepts no approval")
        print(prepare_menu_finalize())
    elif args.mode == "menu-finalize":
        if args.approval is None:
            raise RecoveryError("menu-finalize requires approval")
        print(json.dumps(menu_hide_finalize(args.approval), sort_keys=True))
    elif args.mode == "prepare-post-hide":
        if args.approval is not None:
            raise RecoveryError("prepare-post-hide accepts no approval")
        print(prepare_post_hide())
    else:
        if args.approval is None:
            raise RecoveryError("post-hide-finalize requires approval")
        print(json.dumps(post_hide_finalize(args.approval), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RecoveryError, owner.ContractError, adapter.ContractError) as exc:
        print(f"A90_H37_RUN02_ROLLBACK_CONTINUATION_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
