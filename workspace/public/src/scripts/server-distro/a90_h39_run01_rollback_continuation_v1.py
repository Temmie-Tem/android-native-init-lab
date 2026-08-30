#!/usr/bin/env python3
"""Fixed rollback-only continuation for the consumed A90 H39 run-01."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
ENGINE_PATH = MODULE_DIR / "a90_h37_run02_rollback_continuation_v1.py"
SPEC = importlib.util.spec_from_file_location("_a90_h39_run01_rollback_engine_v1", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("H39 rollback engine import failed")
engine = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)
if Path(getattr(engine, "__file__", "")).resolve() != ENGINE_PATH:
    raise RuntimeError("H39 rollback engine identity changed")

owner = engine.owner
adapter = engine.adapter
ROOT = owner.REPO_ROOT
CAPABILITY = "A90_H39_RUN01_ROLLBACK_CONTINUATION_V1"
RUN_ID = "a90-h39-f1-20260830-01"
MANIFEST_SHA256 = "fec1d042c6415933bbfc922d46c06bf35246d5e254a95a68806becdc83bd73ea"
SELF_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests/test_a90_h39_run01_rollback_continuation_v1.py"
CONT_INTENT_SHA256 = "2274d8840890180fe0c711a96d1cf0051d9153b4aaef47cf09f6575089bdfac6"
CONT_RESULT_SHA256 = "e36cd22dc1bb262846150acf5e6516f3a034cc8ce142c13279dd122c8c63fc7b"
CONT_LOG_HASHES = {
    "001-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "001-effect-usb-inventory.stdout": "3cd0e56abaf342a43f5c71d91e8a6292bad682666fcd39d97238910002455cd0",
    "002-adb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-adb-inventory.stdout": "0236dcb957f762d06f26fda8bd6a2412d5d9db34a52a0818cc201cc2bad1d971",
    "003-flash-rollback.stderr": "48da0128123595af87a42173083e66c35ed0466db6cf74f80ccc1855fdccdedc",
    "003-flash-rollback.stdout": "75ba0ce0b9bc231e56662fd2e49fb177dd9a4949ffba882ee20b6264195a4232",
    "004-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "004-usb-inventory.stdout": "a010cd346ce5869ad2660776e613a685b4bf8dae14c86f390954c03dce52d866",
    "005-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "005-bridge-preflight.stdout": "73988319b7f853d4115bed290b23ba1c9af687812d15a78bbcda71d60dc094dd",
    "006-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "006-boot-id-start.stdout": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
FINALIZE_INTENT = owner.RUN_ROOT / "a90-h39-run01-rollback-continuation-v1" / "15-menu-health-intent.json"
FINALIZE_LOG_DIR = owner.RUN_ROOT / "a90-h39-run01-rollback-continuation-v1-menu-health-logs"
FINALIZE_APPROVAL_PREFIX = "A90-H39-RUN01-MENU-HEALTH-FINALIZE-V1-APPROVE:"
FINALIZE_INTENT_SHA256 = "a1a910487f7d745e289c958458bc943670e3510fbba6ce03f45118941e740de0"
FINALIZE_LOG_HASHES = {
    "001-usb-inventory-before.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "001-usb-inventory-before.stdout": "a010cd346ce5869ad2660776e613a685b4bf8dae14c86f390954c03dce52d866",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "64f727848369b9da394e588d46c2dbee041781e490f9d57ba67b87dcd20df249",
    "003-menu-hide.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-menu-hide.stdout": "11b2317df962df98b76f4546d8465d14a38b782c962fb476dad3a8a70d8e8f76",
}
POST_HIDE_INTENT = owner.RUN_ROOT / "a90-h39-run01-rollback-continuation-v1" / "18-post-hide-health-intent.json"
POST_HIDE_LOG_DIR = owner.RUN_ROOT / "a90-h39-run01-rollback-continuation-v1-post-hide-health-logs"
POST_HIDE_APPROVAL_PREFIX = "A90-H39-RUN01-POST-HIDE-HEALTH-V1-APPROVE:"
RECORD_HASHES = {
    "00-prepared.json": "8315c80b5ed8ceac4a029cdc50833bd34866c5c3a394599f3c9644a629edd6b4",
    "10-approved.json": "4faa4550ef495e490672a0d810446cffa29208793a7c6d7bb7d91478a7255fe8",
    "11-recovery-transition-intent.json": "8976b7bbf008c744fd783bde2d9d6bce42e2978030393b7f4066f5361326bf7e",
    "12-recovery-ready.json": "cb665f8e253b797b48db847b345f812e1369c8f5cddd040761bda6630965407b",
    "20-candidate-intent.json": "f2ca793379891d4d710fd4c0739dec97665dfdf1ea8380624fdf5da452c21ed1",
    "21-candidate-launched.json": "6d3b037ce1f6772ca580c68c52ead108a045d72f8ba4952b548ce58b9f851bf2",
    "22-candidate-result.json": "764d179568c6aa193a2664cb1bc00fcca4c9922007538867a69e7deca540b1a8",
    "26-failed-boot-evidence-intent.json": "d457482ba5f1fb116360e8034615154ab405cd847b5a98b7f2a0e2d42e1e997b",
    "27-failed-boot-evidence-result.json": "98a5539f99f7c66a9a27fc22e7575f6dbd408c006bb1afd286180ee72fcb5941",
    "30-rollback-intent.json": "9ca8fff9575653529fd3423b1ffdadb39afc4064afd8fe6753de938ec6abc32a",
    "31-rollback-launched.json": "0763711633df583c50c8ba9db1f4945b4cfd59c5106ccac160d80d06f6acbf81",
    "32-rollback-result.json": "539e2d2311197c991ddb1ae702fa949b7e18c5b6f57be6f1269e81576e3ac0fd",
    "40-terminal.json": "c0c54b86ab5bd2a4e0b16afb5376da2e2d993bf3f3ca2aa163335ffd78e57493",
}


def configure() -> None:
    run_root = owner.RUN_ROOT
    cont_dir = run_root / "a90-h39-run01-rollback-continuation-v1"
    values = {
        "CAPABILITY": CAPABILITY,
        "REVIEW_SCHEMA": "a90-h39-run01-rollback-continuation-review-v1",
        "CONT_INTENT_SCHEMA": "a90-h39-run01-rollback-continuation-intent-v1",
        "CONT_RESULT_SCHEMA": "a90-h39-run01-rollback-continuation-result-v1",
        "CONT_FINAL_SCHEMA": "a90-h39-run01-rollback-continuation-final-v1",
        "CONT_FINAL_DECISION": "V2321_HEALTHY_H39_RUN01_RECOVERED",
        "APPROVAL_PREFIX": "A90-H39-RUN01-ROLLBACK-CONTINUE-V1-APPROVE:",
        "RUN_ID": RUN_ID,
        "MANIFEST_PATH": ROOT / "workspace/private/manifests/a90-h39-f1-20260830-01.json",
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "RUN_DIR": run_root / RUN_ID,
        "OLD_LOG_DIR": run_root / f"{RUN_ID}-execute-1-logs",
        "CONT_DIR": cont_dir,
        "LIVE_LOG_DIR": run_root / "a90-h39-run01-rollback-continuation-v1-logs",
        "INTENT_PATH": cont_dir / "00-intent.json",
        "RESULT_PATH": cont_dir / "10-rollback-result.json",
        "FINAL_PATH": cont_dir / "20-final.json",
        "REVIEW_PATH": ROOT / "docs/reports/A90_H39_RUN01_ROLLBACK_CONTINUATION_V1_REVIEW.json",
        "RECORD_HASHES": RECORD_HASHES,
        "OLD_ROLLBACK_STDOUT_SHA256": "73f57be33e1a5bf1fc3c33082831a671813f71839273e3f61a1097b114229b24",
        "OLD_ROLLBACK_STDERR_SHA256": "3d37bdfc9479b990b7eb1f2d87c586d54f35151b0cecc28c9efb3f2c2c2d775a",
        "FIXED_ROLLBACK_RESULT": {
            "completed": False,
            "outcome": "PRE_WRITE_FAILURE",
            "quiescent": True,
            "receiptSha256": "e0ffba878f093ade6c6d634837e38f0aa172a0ceb696040a5d1507bb2de50d75",
            "returncode": 1,
        },
        "OLD_ROLLBACK_REQUIRED_STDERR": b"native recovery command failed; minimal one-shot mode does not resend",
        "CLOSURE_PATHS": (SELF_PATH, TEST_PATH, *engine.CLOSURE_PATHS),
    }
    for name, value in values.items():
        setattr(engine, name, value)


configure()
execution_closure_sha256 = engine.execution_closure_sha256
prepare = engine.prepare
execute = engine.execute


def consumed_rollback() -> dict[str, object]:
    if hashlib.sha256(engine._read(engine.INTENT_PATH)).hexdigest() != CONT_INTENT_SHA256:
        raise engine.RecoveryError("consumed H39 rollback intent changed")
    if hashlib.sha256(engine._read(engine.RESULT_PATH)).hexdigest() != CONT_RESULT_SHA256:
        raise engine.RecoveryError("consumed H39 rollback result changed")
    logs = engine._read_exact_log_set(engine.LIVE_LOG_DIR, CONT_LOG_HASHES, "H39 continuation")
    record = owner.parse_canonical(engine._read(engine.RESULT_PATH), "H39 continuation result")
    result = record.get("result") if type(record) is dict else None
    expected = {
        "completed": True,
        "outcome": "BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
        "quiescent": True,
        "receiptSha256": "92ac0922b55a884e8e487afcbe8be6fcc116fad2343ab1bfb2534687fbe12ef1",
        "returncode": 0,
    }
    receipt = owner.parse_canonical(logs["003-flash-rollback.stdout"], "H39 helper receipt")
    if (
        record.get("schema") != engine.CONT_RESULT_SCHEMA
        or result != expected
        or receipt.get("outcome") != expected["outcome"]
        or receipt.get("writeStarted") is not True
        or receipt.get("bootWrittenReadbackExact") is not True
        or receipt.get("systemReturnAttempted") is not True
        or receipt.get("systemReturnCommandOk") is not True
        or receipt.get("systemReturnConfirmed") is not True
        or logs["006-boot-id-start.stdout"]
        or logs["006-boot-id-start.stderr"]
    ):
        raise engine.RecoveryError("consumed H39 rollback/observer incident is not exact")
    return expected


def _finalize_intent_value(approval: str, review_sha: str, closure: str) -> dict[str, object]:
    return {
        "schema": "a90-h39-run01-menu-health-finalize-intent-v1",
        "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "approvalSha256": hashlib.sha256(approval.encode("ascii")).hexdigest(),
        "candidateReplay": False,
        "rollbackReplay": False,
        "healthObservationOnly": True,
        "menuHideSendCount": 1,
    }


def prepare_finalize() -> str:
    _manifest, review_sha, closure, _token = engine._fixed_context()
    consumed_rollback()
    if FINALIZE_INTENT.exists() or FINALIZE_LOG_DIR.exists() or engine.FINAL_PATH.exists():
        raise engine.RecoveryError("H39 menu-health finalizer is already consumed")
    binding = {
        "capability": CAPABILITY,
        "phase": "confirmed-rollback-menu-hide-health-only",
        "manifestSha256": MANIFEST_SHA256,
        "rollbackResultSha256": CONT_RESULT_SHA256,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
    }
    return FINALIZE_APPROVAL_PREFIX + hashlib.sha256(owner.canonical_json(binding)).hexdigest()


def revalidate_finalize(
    manifest: dict[str, object], approval: str, review_sha: str, closure: str
) -> str:
    current_review, current_closure = engine._review()
    if (current_review, current_closure) != (review_sha, closure):
        raise engine.RecoveryError("H39 finalizer review lease changed")
    engine._verify_historical_qualification(manifest)
    consumed_rollback()
    engine._require_guards(manifest)
    raw = owner.canonical_json(_finalize_intent_value(approval, review_sha, closure))
    if engine._read(FINALIZE_INTENT) != raw:
        raise engine.RecoveryError("H39 finalizer intent changed")
    return hashlib.sha256(raw).hexdigest()


def finalize_menu_health(approval: str) -> dict[str, object]:
    manifest, review_sha, closure, _token = engine._fixed_context()
    rollback_result = consumed_rollback()
    if approval != prepare_finalize():
        raise engine.RecoveryError("H39 menu-health finalizer approval mismatch")
    engine._publish(FINALIZE_INTENT, _finalize_intent_value(approval, review_sha, closure))
    intent_sha = revalidate_finalize(manifest, approval, review_sha, closure)
    serial_sha = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    runner = engine.h28_menu.adapter.HostRunner(
        FINALIZE_LOG_DIR,
        redactor=engine.h28_menu.adapter.SerialRedactor(hashes=(serial_sha,)),
    )
    qualification = dict(manifest["qualification"])
    review_raw = engine._read(engine.REVIEW_PATH)
    qualification["review"] = {
        "path": str(engine.REVIEW_PATH),
        "size": len(review_raw),
        "sha256": review_sha,
    }
    observer = engine.h28_menu.MenuHideObserver(runner, qualification=qualification)
    try:
        observation = observer.observe(
            manifest["rollback"], timeout_sec=manifest["timeouts"]["healthSec"]
        )
        engine.h28_menu._validate_observation(observation, manifest["rollback"], review_sha)
    except Exception as exc:
        raise engine.RecoveryError("one-shot H39 menu-health observation failed") from exc
    revalidate_finalize(manifest, approval, review_sha, closure)
    final = {
        "schema": engine.CONT_FINAL_SCHEMA,
        "decision": "V2321_HEALTHY_H39_RUN01_AFTER_CONFIRMED_ROLLBACK",
        "candidateReplay": False,
        "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "rollbackResult": rollback_result,
        "rollbackResultPromoted": False,
        "healthObservationOnly": True,
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
        raise engine.RecoveryError("H39 final sidecar readback mismatch")
    revalidate_finalize(manifest, approval, review_sha, closure)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def consumed_menu_hide(*, allow_final: bool = False) -> None:
    if hashlib.sha256(engine._read(FINALIZE_INTENT)).hexdigest() != FINALIZE_INTENT_SHA256:
        raise engine.RecoveryError("consumed H39 menu-health intent changed")
    intent = owner.parse_canonical(engine._read(FINALIZE_INTENT), "H39 menu-health intent")
    if (
        intent.get("schema") != "a90-h39-run01-menu-health-finalize-intent-v1"
        or intent.get("capability") != CAPABILITY
        or intent.get("manifestSha256") != MANIFEST_SHA256
        or intent.get("rollbackResultSha256") != CONT_RESULT_SHA256
        or intent.get("candidateReplay") is not False
        or intent.get("rollbackReplay") is not False
        or intent.get("healthObservationOnly") is not True
        or intent.get("menuHideSendCount") != 1
    ):
        raise engine.RecoveryError("consumed H39 menu-health intent is not exact")
    logs = engine._read_exact_log_set(FINALIZE_LOG_DIR, FINALIZE_LOG_HASHES, "H39 menu-health")
    if logs["003-menu-hide.stdout"] != b"hide\r\n[busy] auto menu active; hide requested\r\n":
        raise engine.RecoveryError("H39 hide response is not the fixed accepted request")
    if logs["003-menu-hide.stderr"]:
        raise engine.RecoveryError("H39 hide response has unexpected stderr")
    if engine.FINAL_PATH.exists() and not allow_final:
        raise engine.RecoveryError("failed H39 menu-health session published unexpected final")


def _post_hide_intent_value(approval: str, review_sha: str, closure: str) -> dict[str, object]:
    return {
        "schema": "a90-h39-run01-post-hide-health-intent-v1",
        "capability": CAPABILITY,
        "manifestSha256": MANIFEST_SHA256,
        "menuHideIntentSha256": FINALIZE_INTENT_SHA256,
        "menuHideLogSetSha256": hashlib.sha256(
            owner.canonical_json(FINALIZE_LOG_HASHES)
        ).hexdigest(),
        "hideSendAllowed": False,
        "healthObservationOnly": True,
        "candidateReplay": False,
        "rollbackReplay": False,
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
        "approvalSha256": hashlib.sha256(approval.encode("ascii")).hexdigest(),
    }


def prepare_post_hide() -> str:
    _manifest, review_sha, closure, _token = engine._fixed_context()
    consumed_rollback()
    consumed_menu_hide()
    if POST_HIDE_INTENT.exists() or POST_HIDE_LOG_DIR.exists() or engine.FINAL_PATH.exists():
        raise engine.RecoveryError("H39 post-hide health continuation is already consumed")
    binding = {
        "capability": CAPABILITY,
        "phase": "post-accepted-hide-health-only",
        "manifestSha256": MANIFEST_SHA256,
        "menuHideIntentSha256": FINALIZE_INTENT_SHA256,
        "menuHideLogSetSha256": hashlib.sha256(
            owner.canonical_json(FINALIZE_LOG_HASHES)
        ).hexdigest(),
        "reviewSha256": review_sha,
        "executionClosureSha256": closure,
    }
    return POST_HIDE_APPROVAL_PREFIX + hashlib.sha256(owner.canonical_json(binding)).hexdigest()


def revalidate_post_hide(
    manifest: dict[str, object], approval: str, review_sha: str, closure: str,
    *, allow_final: bool = False,
) -> str:
    current_review, current_closure = engine._review()
    if (current_review, current_closure) != (review_sha, closure):
        raise engine.RecoveryError("H39 post-hide review lease changed")
    engine._verify_historical_qualification(manifest)
    consumed_rollback()
    consumed_menu_hide(allow_final=allow_final)
    engine._require_guards(manifest)
    raw = owner.canonical_json(_post_hide_intent_value(approval, review_sha, closure))
    if engine._read(POST_HIDE_INTENT) != raw:
        raise engine.RecoveryError("H39 post-hide intent changed")
    return hashlib.sha256(raw).hexdigest()


def post_hide_finalize(approval: str) -> dict[str, object]:
    manifest, review_sha, closure, _token = engine._fixed_context()
    rollback_result = consumed_rollback()
    consumed_menu_hide()
    if approval != prepare_post_hide():
        raise engine.RecoveryError("H39 post-hide approval mismatch")
    engine._publish(POST_HIDE_INTENT, _post_hide_intent_value(approval, review_sha, closure))
    intent_sha = revalidate_post_hide(manifest, approval, review_sha, closure)
    serial_sha = manifest["qualification"]["recoveryIdentity"]["adbSerialSha256"]
    runner = engine.h28_menu.adapter.HostRunner(
        POST_HIDE_LOG_DIR,
        redactor=engine.h28_menu.adapter.SerialRedactor(hashes=(serial_sha,)),
    )
    qualification = dict(manifest["qualification"])
    review_raw = engine._read(engine.REVIEW_PATH)
    qualification["review"] = {
        "path": str(engine.REVIEW_PATH),
        "size": len(review_raw),
        "sha256": review_sha,
    }
    observer = engine.PostHideObserver(runner, qualification=qualification)
    try:
        observation = observer.observe_post_hide(
            manifest["rollback"], timeout_sec=manifest["timeouts"]["healthSec"]
        )
        snapshot = engine._validate_post_hide_observation(
            observation, manifest["rollback"], review_sha
        )
    except Exception as exc:
        raise engine.RecoveryError("one-shot H39 post-hide V2321 observation failed") from exc
    revalidate_post_hide(manifest, approval, review_sha, closure)
    final = {
        "schema": engine.CONT_FINAL_SCHEMA,
        "decision": "V2321_HEALTHY_H39_RUN01_AFTER_ACCEPTED_HIDE",
        "candidateReplay": False,
        "originalRollbackReplay": False,
        "incidentContinuationWriteCount": 1,
        "rollbackResult": rollback_result,
        "rollbackResultPromoted": False,
        "priorHealthObservationOutcome": "MENU_BUSY_NO_HEALTH_PROOF",
        "menuHideRequestOutcome": "ACCEPTED_BY_FIXED_NATIVE_RESPONSE",
        "menuHideSendCount": 1,
        "postHideAdditionalSendCount": 0,
        "menuHideIntentSha256": FINALIZE_INTENT_SHA256,
        "postHideIntentSha256": intent_sha,
        "sameBoot": observation["sameBoot"],
        "finalBootId": observation["finalBootId"],
        "snapshot": snapshot.payload(),
    }
    raw = owner.canonical_json(final)
    engine._publish(engine.FINAL_PATH, final)
    if engine._read(engine.FINAL_PATH) != raw:
        raise engine.RecoveryError("H39 post-hide final sidecar readback mismatch")
    revalidate_post_hide(manifest, approval, review_sha, closure, allow_final=True)
    owner._release_active_guard(manifest)
    owner._require_candidate_guard(manifest)
    return final


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "mode",
        choices=(
            "prepare", "execute", "prepare-finalize", "finalize",
            "prepare-post-hide", "post-hide-finalize",
        ),
    )
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
    if args.mode == "prepare-post-hide":
        if args.approval is not None:
            raise engine.RecoveryError("prepare-post-hide accepts no approval")
        print(prepare_post_hide())
        return 0
    if args.approval is None:
        raise engine.RecoveryError("execute requires approval")
    if args.mode == "execute":
        result = execute(args.approval)
    elif args.mode == "finalize":
        result = finalize_menu_health(args.approval)
    else:
        result = post_hide_finalize(args.approval)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (engine.RecoveryError, owner.ContractError, adapter.ContractError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
