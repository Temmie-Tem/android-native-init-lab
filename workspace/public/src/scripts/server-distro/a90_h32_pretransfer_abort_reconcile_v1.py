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
import os
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
    for relative in (_ENGINE_PATH.relative_to(_owner.REPO_ROOT), SELF_REL, TARGET_CONTRACT_REL):
        raw = (_owner.REPO_ROOT / relative).read_bytes()
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(raw)).encode("ascii"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


_configure_engine()
_engine.execution_closure_sha256 = _h32_execution_closure_sha256


ContractError = _engine.ContractError


def execution_closure_sha256() -> str:
    return _h32_execution_closure_sha256()


def reconcile():
    return _engine.reconcile()


def main() -> int:
    print(__import__("json").dumps(reconcile(), sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (_engine.ContractError, _owner.ContractError, _adapter.ContractError) as exc:
        print(f"A90_H32_PRETRANSFER_ABORT_RECONCILE_V1 NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
