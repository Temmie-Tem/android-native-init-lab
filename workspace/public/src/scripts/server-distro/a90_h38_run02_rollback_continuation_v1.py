#!/usr/bin/env python3
"""Fixed rollback-only continuation for the consumed A90 H38 run-02."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
ENGINE_PATH = MODULE_DIR / "a90_h37_run02_rollback_continuation_v1.py"
SPEC = importlib.util.spec_from_file_location("_a90_h38_run02_rollback_engine_v1", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("H38 rollback engine import failed")
engine = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)
if Path(getattr(engine, "__file__", "")).resolve() != ENGINE_PATH:
    raise RuntimeError("H38 rollback engine identity changed")

owner = engine.owner
adapter = engine.adapter
ROOT = owner.REPO_ROOT
CAPABILITY = "A90_H38_RUN02_ROLLBACK_CONTINUATION_V1"
RUN_ID = "a90-h38-f1-20260830-02"
MANIFEST_SHA256 = "efad371cb1d8b1c617738391bcc8f6981275eb3996d8c4879e11ca974d687a13"
SELF_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests/test_a90_h38_run02_rollback_continuation_v1.py"
FINALIZE_INTENT = owner.RUN_ROOT / "a90-h38-run02-rollback-continuation-v1" / "15-physical-return-menu-health-intent.json"
FINALIZE_LOG_DIR = owner.RUN_ROOT / "a90-h38-run02-rollback-continuation-v1-menu-health-logs"
FINALIZE_APPROVAL_PREFIX = "A90-H38-RUN02-PHYSICAL-RETURN-MENU-HEALTH-V1-APPROVE:"
CONT_INTENT_SHA256 = "337a19d0f5823c84797221466e133c44ea95404a22b50633a099dd9fb3edb0a2"
CONT_RESULT_SHA256 = "7206b1c138f6e64f0bbb744d5a5322bcc6339c8c088243dfdd92f43eaf623934"
CONT_FLASH_STDOUT_SHA256 = "2e26bf251052f5971314959a43c4f34d23d9f6e6dd8c00d8beadb3b37e6e0ee7"
CONT_FLASH_STDERR_SHA256 = "77900d310e0079909d5236f0b5fa07800fa82ebf37e8d413e37a6c8e6a5143ed"
RECORD_HASHES = {
    "00-prepared.json": "f2bdd8ccab4caefda1c202e25c1f4c09348bc4aa6016c66d6df174652569077d",
    "10-approved.json": "0f189846d8c4bcba65af4095661baf9352d440b2de83bc6eca042dfc1a3488a6",
    "11-recovery-transition-intent.json": "713c60688b784ef0c089b3b080c1e1708c148fe74af1e4edb6484f205b28b56e",
    "12-recovery-ready.json": "da5a714e57c12cf900ed0cb0537d7c488ea092622e443ed472eff01b7b572a44",
    "20-candidate-intent.json": "c16460ddc05a6e360bc75350ebaee4202b72452b16db7b6e61b45c430fad6e8d",
    "21-candidate-launched.json": "0d07222776b0082d4834936fa4331916b1529eed135ad2f343839007194d9087",
    "22-candidate-result.json": "33f7a7ad22696bdb3c7eca4797470017f4cdbb0bb0d3eaffa9a58c06297676f4",
    "26-failed-boot-evidence-intent.json": "56791459cb8d6af7fc9280062e5839a23c7338e35a381bb933c3dc05421345ba",
    "27-failed-boot-evidence-result.json": "c34b7ec8dac29b0f4a42f6df779d663046d4d0d2b4fd5be00222d13b571c3e91",
    "30-rollback-intent.json": "5f29aecb57615be47ad82310e85424a3333297c91d416210e2b54db67fcd98e5",
    "31-rollback-launched.json": "3570cbb228f98d74c86bd49d0ad9a2f2182ccc909b3d7f1b79d0b9121f62e03b",
    "32-rollback-result.json": "f9d0fda95948dd4392fa0d2c99172dc407b08d6aca7a528d721829b41f72df93",
    "40-terminal.json": "f79df8db0cdadebdc5bc6a0263c80a2c93452816472a8ca0b8a20de369ae58b6",
}


def configure() -> None:
    run_root = owner.RUN_ROOT
    cont_dir = run_root / "a90-h38-run02-rollback-continuation-v1"
    values = {
        "CAPABILITY": CAPABILITY,
        "REVIEW_SCHEMA": "a90-h38-run02-rollback-continuation-review-v1",
        "CONT_INTENT_SCHEMA": "a90-h38-run02-rollback-continuation-intent-v1",
        "CONT_RESULT_SCHEMA": "a90-h38-run02-rollback-continuation-result-v1",
        "CONT_FINAL_SCHEMA": "a90-h38-run02-rollback-continuation-final-v1",
        "CONT_FINAL_DECISION": "V2321_HEALTHY_H38_RUN02_RECOVERED",
        "APPROVAL_PREFIX": "A90-H38-RUN02-ROLLBACK-CONTINUE-V1-APPROVE:",
        "RUN_ID": RUN_ID,
        "MANIFEST_PATH": ROOT / "workspace/private/manifests/a90-h38-f1-20260830-02.json",
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "RUN_DIR": run_root / RUN_ID,
        "OLD_LOG_DIR": run_root / f"{RUN_ID}-execute-1-logs",
        "CONT_DIR": cont_dir,
        "LIVE_LOG_DIR": run_root / "a90-h38-run02-rollback-continuation-v1-logs",
        "INTENT_PATH": cont_dir / "00-intent.json",
        "RESULT_PATH": cont_dir / "10-rollback-result.json",
        "FINAL_PATH": cont_dir / "20-final.json",
        "REVIEW_PATH": ROOT / "docs/reports/A90_H38_RUN02_ROLLBACK_CONTINUATION_V1_REVIEW.json",
        "RECORD_HASHES": RECORD_HASHES,
        "OLD_ROLLBACK_STDOUT_SHA256": "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24",
        "OLD_ROLLBACK_STDERR_SHA256": "e9979d21b3ad900f80318e3fdc59a53d12492bfdb7ce59628e0769ffc0771eb6",
        "FIXED_ROLLBACK_RESULT": {
            "completed": False, "outcome": "PRE_WRITE_FAILURE", "quiescent": True,
            "receiptSha256": "fba214861b929752af435bceb40666318ba5facdb1a33a5c3981319ae9b9cdd9",
            "returncode": 1,
        },
        "OLD_ROLLBACK_REQUIRED_STDERR": b"bridge command outcome uncertain after one send for 'recovery': None",
        "CLOSURE_PATHS": (SELF_PATH, TEST_PATH, *engine.CLOSURE_PATHS),
    }
    for name, value in values.items():
        setattr(engine, name, value)


configure()
execution_closure_sha256 = engine.execution_closure_sha256
prepare = engine.prepare
execute = engine.execute


def consumed_rollback() -> dict[str, Any]:
    paths = {
        engine.INTENT_PATH: CONT_INTENT_SHA256,
        engine.RESULT_PATH: CONT_RESULT_SHA256,
        engine.LIVE_LOG_DIR / "003-flash-rollback.stdout": CONT_FLASH_STDOUT_SHA256,
        engine.LIVE_LOG_DIR / "003-flash-rollback.stderr": CONT_FLASH_STDERR_SHA256,
    }
    for path, expected in paths.items():
        if hashlib.sha256(engine._read(path)).hexdigest() != expected:
            raise engine.RecoveryError(f"consumed H38 rollback evidence changed: {path.name}")
    record = owner.parse_canonical(engine._read(engine.RESULT_PATH), "H38 continuation result")
    result = record.get("result") if type(record) is dict else None
    expected_result = {
        "completed": False,
        "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        "quiescent": True,
        "receiptSha256": "88eaf8410363c15fdf5569d20452440e7558c5f05064f8c5ff6912ef05d0cf4e",
        "returncode": 1,
    }
    receipt = owner.parse_canonical(
        engine._read(engine.LIVE_LOG_DIR / "003-flash-rollback.stdout"),
        "H38 continuation helper receipt",
    )
    if (
        record.get("schema") != engine.CONT_RESULT_SCHEMA
        or result != expected_result
        or receipt.get("outcome") != expected_result["outcome"]
        or receipt.get("writeStarted") is not True
        or receipt.get("bootWrittenReadbackExact") is not True
        or receipt.get("systemReturnAttempted") is not True
        or receipt.get("systemReturnCommandOk") is not True
        or receipt.get("systemReturnConfirmed") is not False
    ):
        raise engine.RecoveryError("consumed H38 rollback is not exact uncertain System return")
    return result


def prepare_finalize() -> str:
    _manifest, review_sha, closure, _token = engine._fixed_context()
    consumed_rollback()
    if FINALIZE_INTENT.exists() or engine.FINAL_PATH.exists() or FINALIZE_LOG_DIR.exists():
        raise engine.RecoveryError("H38 physical-return finalizer is already consumed")
    binding = {
        "capability": CAPABILITY,
        "phase": "operator-reported-physical-return-menu-hide-health-only",
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
    }
    return FINALIZE_APPROVAL_PREFIX + hashlib.sha256(owner.canonical_json(binding)).hexdigest()


def revalidate_finalize(
    manifest: dict[str, Any], approval: str, review_sha: str, closure: str
) -> str:
    current_review, current_closure = engine._review()
    if (current_review, current_closure) != (review_sha, closure):
        raise engine.RecoveryError("H38 finalizer review lease changed")
    engine._verify_historical_qualification(manifest)
    consumed_rollback()
    engine._require_guards(manifest)
    expected = {
        "schema": "a90-h38-run02-physical-return-menu-health-intent-v1",
        "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "approvalSha256": hashlib.sha256(approval.encode("ascii")).hexdigest(),
        "rollbackReplay": False,
        "healthObservationOnly": True,
        "menuHideSendCount": 1,
    }
    raw = owner.canonical_json(expected)
    if engine._read(FINALIZE_INTENT) != raw:
        raise engine.RecoveryError("H38 finalizer intent changed")
    return hashlib.sha256(raw).hexdigest()


def finalize_physical_return(approval: str) -> dict[str, Any]:
    manifest, review_sha, closure, _token = engine._fixed_context()
    rollback_result = consumed_rollback()
    if approval != prepare_finalize():
        raise engine.RecoveryError("H38 physical-return finalizer approval mismatch")
    intent = {
        "schema": "a90-h38-run02-physical-return-menu-health-intent-v1",
        "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "approvalSha256": hashlib.sha256(approval.encode("ascii")).hexdigest(),
        "rollbackReplay": False,
        "healthObservationOnly": True,
        "menuHideSendCount": 1,
    }
    engine._publish(FINALIZE_INTENT, intent)
    intent_sha = revalidate_finalize(manifest, approval, review_sha, closure)
    serial_sha = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    runner = engine.h28_menu.adapter.HostRunner(
        FINALIZE_LOG_DIR,
        redactor=engine.h28_menu.adapter.SerialRedactor(hashes=(serial_sha,)),
    )
    qualification = dict(manifest["qualification"])
    review_raw = engine._read(engine.REVIEW_PATH)
    qualification["review"] = {
        "path": str(engine.REVIEW_PATH), "size": len(review_raw), "sha256": review_sha,
    }
    observer = engine.h28_menu.MenuHideObserver(runner, qualification=qualification)
    try:
        observation = observer.observe(
            manifest["rollback"], timeout_sec=manifest["timeouts"]["healthSec"]
        )
        engine.h28_menu._validate_observation(observation, manifest["rollback"], review_sha)
    except Exception as exc:
        raise engine.RecoveryError("one-shot H38 rollback menu-health observation failed") from exc
    revalidate_finalize(manifest, approval, review_sha, closure)
    final = {
        "schema": engine.CONT_FINAL_SCHEMA,
        "decision": "V2321_HEALTHY_H38_RUN02_AFTER_OPERATOR_REPORTED_PHYSICAL_RETURN",
        "candidateReplay": False,
        "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "helperOutcome": rollback_result["outcome"],
        "helperOutcomePromoted": False,
        "operatorReportedPhysicalSystemReturn": True,
        "physicalButtonActionHostProved": False,
        "menuHideSendCount": 1,
        "menuHideIntentSha256": intent_sha,
        "menuHideReceiptSha256": observation.hide_receipt_sha256,
        "sameBoot": observation.same_boot,
        "finalBootId": observation.final_boot_id,
        "snapshot": observation.snapshot.payload(),
    }
    raw = owner.canonical_json(final)
    engine._publish(engine.FINAL_PATH, final)
    if engine._read(engine.FINAL_PATH) != raw:
        raise engine.RecoveryError("H38 final sidecar readback mismatch")
    revalidate_finalize(manifest, approval, review_sha, closure)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "execute", "prepare-finalize", "finalize"))
    parser.add_argument("--approval")
    args = parser.parse_args(argv)
    if args.mode == "prepare":
        if args.approval is not None:
            raise engine.RecoveryError("prepare accepts no approval")
        print(prepare())
        return 0
    if args.mode == "prepare-finalize":
        if args.approval is not None:
            raise engine.RecoveryError("prepare-finalize accepts no approval")
        print(prepare_finalize())
        return 0
    if args.approval is None:
        raise engine.RecoveryError("execute requires approval")
    result = execute(args.approval) if args.mode == "execute" else finalize_physical_return(args.approval)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (engine.RecoveryError, owner.ContractError, adapter.ContractError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
