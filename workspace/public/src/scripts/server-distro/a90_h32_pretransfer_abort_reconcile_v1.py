#!/usr/bin/env python3
"""Fixed H32 no-write reconciliation for the consumed F1 attempt.

This is a H32-specific binding of the reviewed reconciliation engine.  The
immutable journal prefix ends at ``31-rollback-launched.json``; the exact
candidate receipt says PRE_WRITE_FAILURE and the rollback helper has no
dispatch log.  The module can publish only one 41 record after a future fresh
V2321 ACM/Native health observation.  It never invokes ADB, a flash helper,
reboot, recovery transition, or any image/partition primitive itself.
"""

from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
_ENGINE_NAME = "_a90_h32_h31_engine_v1"
_ENGINE_PATH = MODULE_DIR / "a90_h31_pretransfer_abort_reconcile_v1.py"
_engine = sys.modules.get(_ENGINE_NAME)
if _engine is None:
    specification = importlib.util.spec_from_file_location(_ENGINE_NAME, _ENGINE_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError("H31 reconciliation engine import failed")
    _engine = importlib.util.module_from_spec(specification)
    sys.modules[_ENGINE_NAME] = _engine
    specification.loader.exec_module(_engine)
if Path(getattr(_engine, "__file__", "")).resolve() != _ENGINE_PATH:
    raise RuntimeError("H31 reconciliation engine identity is not exact")

_owner = _engine.owner
_adapter = _engine.adapter
_H28_NAME = "_a90_h32_h28_menu_hide_engine_v1"
_H28_PATH = MODULE_DIR / "a90_h28_menu_hide_health_reconcile_v1.py"
_h28 = sys.modules.get(_H28_NAME)
if _h28 is None:
    specification = importlib.util.spec_from_file_location(_H28_NAME, _H28_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError("H28 menu-hide engine import failed")
    _h28 = importlib.util.module_from_spec(specification)
    sys.modules[_H28_NAME] = _h28
    specification.loader.exec_module(_h28)
if Path(getattr(_h28, "__file__", "")).resolve() != _H28_PATH:
    raise RuntimeError("H28 menu-hide engine identity is not exact")

SCHEMA = "a90-h32-pretransfer-abort-reconciliation-v1"
DECISION = "PRETRANSFER_ABORTED_NO_BOOT_WRITE"
RUN_ID = "a90-h32-f1-20260822-01"
MANIFEST_PATH = _owner.REPO_ROOT / "workspace/private/manifests" / f"{RUN_ID}.json"
MANIFEST_SHA256 = "d503ca705a2b2de1bbe23cf8d77564cf1cacf96d1902c43f0320aa3bb29957a8"
REVIEW_PATH = _owner.REPO_ROOT / "docs/reports/A90_H32_PRETRANSFER_ABORT_CURRENT_REVIEW.json"
REVIEW_SCHEMA = "a90-h32-pretransfer-abort-independent-review-v1"
CAPABILITY = "A90_H32_PRETRANSFER_ABORT_RECONCILE_V1"
SELF_REL = "workspace/public/src/scripts/server-distro/a90_h32_pretransfer_abort_reconcile_v1.py"
TARGET_CONTRACT_REL = "docs/operations/targets/A90_TARGET_CONTRACT.md"
UNSET_SHA256 = "UNSET"

CANDIDATE = {
    "version": "0.11.199",
    "build": "phase3-minimal-h32-stock-rebuild-1007-cfp",
    "size": 58_372_096,
    "sha256": "e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d",
}
ROLLBACK = {
    "version": _owner.V2321_ROLLBACK_VERSION,
    "build": _owner.V2321_ROLLBACK_BUILD,
    "size": _owner.V2321_ROLLBACK_SIZE,
    "sha256": _owner.V2321_ROLLBACK_SHA256,
}
CANDIDATE_RECEIPT_SHA256 = "29fd5aba57bdf62216679f55d31de0fd59f62a4e22cd25c8e347a0ea10d0e4af"
RECORD_HASHES = {
    "00-prepared.json": "39fee43d5d43250c0a434aabfbdbdc41080bfb02d84b3a4f8bff6ddfd366bb0e",
    "10-approved.json": "e92665955c0568a08167df2cd517cea9d8ea86d0894166f54f60f7ba6760e058",
    "20-candidate-intent.json": "34be163cf24da398b43085982f6e7142d02ed2d304c4957f3ebc03c1601640f9",
    "21-candidate-launched.json": "4490fc6eda7973670fa8cb4a60e4def8620008b0acac7506bd306b2ff331f64b",
    "22-candidate-result.json": "418248e1a14605cab1efbda0430e057c9178656abab175e05d09d566a0f45bd2",
    "30-rollback-intent.json": "c9d6729f1ab3cde6df376e735345b47008303651651f05eabd409b75f64566aa",
    "31-rollback-launched.json": "03523f0cc27bae8d44d83f8f71c57adea6f9929b26ffc6e27a7b128e77cfdae3",
}
LOG_DIRECTORY = _owner.RUN_ROOT / f"{RUN_ID}-execute-2-logs"
EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
NATIVE_USB_SHA256 = "d54f5489453027f2fc2f659cfd6e1580aa2d4654b2941c355ca7cf453bb6609f"
ZERO_SAMSUNG_USB_SHA256 = "61c43915e41c839b44df23b47eff399a3ff4f1048a65db5f0995271f1d5f05a3"
LOG_HASHES = {
    "001-usb-inventory.stdout": NATIVE_USB_SHA256,
    "001-usb-inventory.stderr": EMPTY_SHA256,
    "002-bridge-preflight.stdout": "7dbe33cfc8efe84241f2cbb252e4a5dafff356851565e921f6e87e29d5cf336d",
    "002-bridge-preflight.stderr": EMPTY_SHA256,
    "003-boot-id-start.stdout": "288f129f833deda94807543d3ff0acef2206030d9e73dc851facc7204ab8ad50",
    "003-boot-id-start.stderr": EMPTY_SHA256,
    "004-version.stdout": "dc58bff4dd342675eceeadf7471ba16c00bebedbcebe50821de7aa9281b1e329",
    "004-version.stderr": EMPTY_SHA256,
    "005-selftest.stdout": "4b20e52199a8fddf0640befdd8a2ee59d6a4cfd0886f8ff71a7e1a3b4089e17b",
    "005-selftest.stderr": EMPTY_SHA256,
    "006-status.stdout": "d37b6a1819c00bae59ef00969f3841c76f6aa34220da5ba388e84f39abdcf9e4",
    "006-status.stderr": EMPTY_SHA256,
    "007-boot-id-final.stdout": "5cc9432fa6b3703a88a29ad4b9497653fc1d8ff023d916fc7100645b5a4f32ce",
    "007-boot-id-final.stderr": EMPTY_SHA256,
    "008-fresh-enable-path.stdout": "b5d9d71483c3ab89ce40ab956c87d55afacd35df02f2c551bc91cd53b9027b0e",
    "008-fresh-enable-path.stderr": EMPTY_SHA256,
    "009-fresh-latch-path.stdout": "ee93c32a204bef980b9e6d042922d768151532baf8da575f74b039679c856f40",
    "009-fresh-latch-path.stderr": EMPTY_SHA256,
    "010-effect-usb-inventory.stdout": NATIVE_USB_SHA256,
    "010-effect-usb-inventory.stderr": EMPTY_SHA256,
    "011-flash-candidate.stdout": "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24",
    "011-flash-candidate.stderr": "74c25b212265b62995f0159d4088ad85cde5f58452cbef47d76e5e991ebfdad1",
    "012-usb-inventory.stdout": ZERO_SAMSUNG_USB_SHA256,
    "012-usb-inventory.stderr": EMPTY_SHA256,
}
for ordinal in range(13, 33):
    LOG_HASHES[f"{ordinal:03d}-effect-usb-inventory.stdout" if ordinal == 13 else f"{ordinal:03d}-rollback-effect-usb-inventory.stdout"] = ZERO_SAMSUNG_USB_SHA256
    LOG_HASHES[f"{ordinal:03d}-effect-usb-inventory.stderr" if ordinal == 13 else f"{ordinal:03d}-rollback-effect-usb-inventory.stderr"] = EMPTY_SHA256

BUSY_OBSERVATION_LOG_DIRECTORY = _owner.RUN_ROOT / f"{RUN_ID}-reconcile-h31-pretransfer-abort-1-logs"
BUSY_OBSERVATION_LOG_HASHES = {
    "001-usb-inventory.stdout": "63a69b17f850700c4af709e4e3c7c7a40b1159517d489d8825572066d09496ce",
    "001-usb-inventory.stderr": EMPTY_SHA256,
    "002-bridge-preflight.stdout": "984daa475a488aaa2f06c33b308259767a7109496a43a92f0d224b9c65ee30bc",
    "002-bridge-preflight.stderr": EMPTY_SHA256,
    "003-boot-id-start.stdout": "481752d50ece0bd385422b7ae39716f336dca904e7d140dddb9cc351bb9132d3",
    "003-boot-id-start.stderr": EMPTY_SHA256,
}
BUSY_OBSERVATION_LOG_SET_SHA256 = hashlib.sha256(
    _owner.canonical_json(BUSY_OBSERVATION_LOG_HASHES)
).hexdigest()
MENU_HIDE_SIDE_ROOT = _owner.REPO_ROOT / "workspace/private/runs/a90-h32-menu-hide-pretransfer-v1"
MENU_HIDE_INTENT_NAME = "10-menu-hide-intent.json"
MENU_HIDE_RECEIPT_NAME = "11-menu-hide-receipt.json"
MENU_HIDE_LOG_DIRECTORY = _owner.RUN_ROOT / f"{RUN_ID}-menu-hide-1-logs"
MENU_HIDE_INTENT_SCHEMA = "a90-h32-menu-hide-pretransfer-intent-v1"
MENU_HIDE_RECEIPT_SCHEMA = "a90-h32-menu-hide-pretransfer-receipt-v1"
MENU_HIDE_WIRE_SHA256 = hashlib.sha256(b"hide\n").hexdigest()


def _configure_engine() -> None:
    for name, value in {
        "SCHEMA": SCHEMA,
        "DECISION": DECISION,
        "RUN_ID": RUN_ID,
        "MANIFEST_PATH": MANIFEST_PATH,
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "REVIEW_PATH": REVIEW_PATH,
        "REVIEW_SCHEMA": REVIEW_SCHEMA,
        "CAPABILITY": CAPABILITY,
        "SELF_REL": SELF_REL,
        "TARGET_CONTRACT_REL": TARGET_CONTRACT_REL,
        "UNSET_SHA256": UNSET_SHA256,
        "CANDIDATE": CANDIDATE,
        "ROLLBACK": ROLLBACK,
        "CANDIDATE_RECEIPT_SHA256": CANDIDATE_RECEIPT_SHA256,
        "RECORD_HASHES": RECORD_HASHES,
        "LOG_DIRECTORY": LOG_DIRECTORY,
        "LOG_HASHES": LOG_HASHES,
        "CANDIDATE_STDOUT": LOG_DIRECTORY / "011-flash-candidate.stdout",
        "CANDIDATE_STDERR": LOG_DIRECTORY / "011-flash-candidate.stderr",
        "H31_JOURNAL_PATH": _owner.H31_PRETRANSFER_ABORT_PATH,
        "MAX_DURATION_MS": 900_000,
    }.items():
        setattr(_engine, name, value)


def _h32_execution_closure_sha256() -> str:
    digest = hashlib.sha256()
    digest.update(_owner.execution_closure_sha256().encode("ascii"))
    digest.update(b"A90-H32-H28-TRANSITIVE-CLOSURE-V1\0")
    digest.update(_h28.execution_closure_sha256().encode("ascii"))
    digest.update(b"\0")
    for relative in (
        _ENGINE_PATH.relative_to(_owner.REPO_ROOT),
        SELF_REL,
        TARGET_CONTRACT_REL,
    ):
        raw = (_owner.REPO_ROOT / relative).read_bytes()
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _validate_busy_boot_receipt(raw: bytes) -> None:
    try:
        value = _h28.adapter._json(raw, "H32 busy boot-id receipt")
    except Exception as exc:
        raise ContractError("H32 busy boot-id receipt is not canonical") from exc
    response = value
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
        raise ContractError("H32 busy boot-id response is not the fixed EBUSY receipt")
    end = response["end"]
    if (
        type(end) is not dict
        or set(end) != {"seq", "cmd", "rc", "errno", "duration_ms", "flags", "status"}
        or end["seq"] != "1"
        or end["cmd"] != "cat"
        or end["rc"] != "-16"
        or end["errno"] != "16"
        or re.fullmatch(r"[0-9]+", end["duration_ms"]) is None
        or end["flags"] != "0x0"
        or end["status"] != "busy"
    ):
        raise ContractError("H32 busy boot-id end frame is not exact")


def _require_busy_observation_logs() -> bytes:
    try:
        metadata = BUSY_OBSERVATION_LOG_DIRECTORY.lstat()
    except OSError as exc:
        raise ContractError("fixed H32 busy observation logs cannot be inspected") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_gid != os.getgid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ContractError("fixed H32 busy observation log directory is not exact")
    expected_names = set(BUSY_OBSERVATION_LOG_HASHES) | {".adb-home"}
    try:
        names = {entry.name for entry in BUSY_OBSERVATION_LOG_DIRECTORY.iterdir()}
    except OSError as exc:
        raise ContractError("fixed H32 busy observation log inventory cannot be read") from exc
    if names != expected_names:
        raise ContractError("fixed H32 busy observation log inventory changed")
    adb_home = BUSY_OBSERVATION_LOG_DIRECTORY / ".adb-home"
    adb_android = adb_home / ".android"
    for path, label in ((adb_home, "H32 busy ADB home"), (adb_android, "H32 busy ADB android")):
        try:
            item = path.lstat()
        except OSError as exc:
            raise ContractError(f"{label} cannot be inspected") from exc
        if (
            not stat.S_ISDIR(item.st_mode)
            or item.st_uid != os.getuid()
            or item.st_gid != os.getgid()
            or stat.S_IMODE(item.st_mode) != 0o700
        ):
            raise ContractError(f"{label} identity is not exact")
    if set(adb_home.iterdir()) != {adb_android} or set(adb_android.iterdir()):
        raise ContractError("H32 busy ADB home contains unexpected state")
    values: dict[str, bytes] = {}
    for name, expected in BUSY_OBSERVATION_LOG_HASHES.items():
        raw = _engine._read_log(BUSY_OBSERVATION_LOG_DIRECTORY / name, name)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ContractError(f"fixed H32 busy observation log changed: {name}")
        values[name] = raw
    raw = values["003-boot-id-start.stdout"]
    _validate_busy_boot_receipt(raw)
    return raw


def _write_sidecar(path: Path, value: dict[str, object], label: str) -> str:
    raw = _owner.canonical_json(value)
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW,
            0o600,
        )
        try:
            if os.write(descriptor, raw) != len(raw):
                raise ContractError(f"{label} short write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise ContractError(f"{label} publication failed") from exc
    _owner._fsync_directory(path.parent)
    return hashlib.sha256(raw).hexdigest()


def _publish_menu_hide_intent() -> str:
    try:
        _h28._private_dir(MENU_HIDE_SIDE_ROOT.parent, "H32 menu-hide sidecar parent")
    except Exception as exc:
        raise ContractError("H32 menu-hide sidecar parent identity is not exact") from exc
    try:
        metadata = MENU_HIDE_SIDE_ROOT.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as exc:
        raise ContractError("H32 menu-hide sidecar cannot be inspected") from exc
    if metadata is not None:
        raise ContractError("H32 menu-hide intent is consumed; hide must not replay")
    try:
        MENU_HIDE_SIDE_ROOT.mkdir(mode=0o700, parents=False)
    except OSError as exc:
        raise ContractError("H32 menu-hide sidecar creation failed") from exc
    _owner._fsync_directory(MENU_HIDE_SIDE_ROOT.parent)
    intent = {
        "schema": MENU_HIDE_INTENT_SCHEMA,
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "manifestSha256": MANIFEST_SHA256,
        "busyObservationLogSetSha256": BUSY_OBSERVATION_LOG_SET_SHA256,
        "command": "hide",
        "wireSha256": MENU_HIDE_WIRE_SHA256,
        "sendCount": 1,
        "candidateReplay": False,
        "rollbackReplay": False,
        "executionClosureSha256": execution_closure_sha256(),
    }
    return _write_sidecar(MENU_HIDE_SIDE_ROOT / MENU_HIDE_INTENT_NAME, intent, "H32 menu-hide intent")


def _publish_menu_hide_receipt(intent_sha256: str, receipt_sha256: str) -> None:
    receipt = {
        "schema": MENU_HIDE_RECEIPT_SCHEMA,
        "capability": CAPABILITY,
        "runId": RUN_ID,
        "intentSha256": intent_sha256,
        "menuHideReceiptSha256": receipt_sha256,
        "wireSha256": MENU_HIDE_WIRE_SHA256,
        "sendCount": 1,
        "candidateReplay": False,
        "rollbackReplay": False,
    }
    _write_sidecar(MENU_HIDE_SIDE_ROOT / MENU_HIDE_RECEIPT_NAME, receipt, "H32 menu-hide receipt")


def _h32_fresh_v2321_observation(manifest: dict[str, object]):
    _require_busy_observation_logs()
    intent_sha256 = _publish_menu_hide_intent()
    serial_sha256 = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    if type(serial_sha256) is not str or _owner.SHA256_RE.fullmatch(serial_sha256) is None:
        raise ContractError("H32 recovery serial binding is not exact")
    redactor = _h28.adapter.SerialRedactor(hashes=(serial_sha256,))
    runner = _h28.adapter.HostRunner(MENU_HIDE_LOG_DIRECTORY, redactor=redactor)
    observer = _h28.MenuHideObserver(runner, qualification=manifest["qualification"])
    try:
        observation = observer.observe(
            manifest["rollback"],
            timeout_sec=manifest["timeouts"]["healthSec"],
        )
        _h28._validate_observation(
            observation,
            manifest["rollback"],
            manifest["qualification"]["review"]["sha256"],
        )
    except Exception as exc:
        raise ContractError("H32 menu-hide V2321 observation failed") from exc
    _publish_menu_hide_receipt(intent_sha256, observation.hide_receipt_sha256)
    return observation.snapshot


_configure_engine()
_engine.execution_closure_sha256 = _h32_execution_closure_sha256
_engine._fresh_v2321_observation = _h32_fresh_v2321_observation


ContractError = _engine.ContractError


def execution_closure_sha256() -> str:
    return _h32_execution_closure_sha256()


def reconcile():
    return _engine.reconcile()


def main() -> int:
    print(json.dumps(reconcile(), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (_engine.ContractError, _owner.ContractError, _adapter.ContractError) as exc:
        print(f"A90_H32_PRETRANSFER_ABORT_RECONCILE_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
