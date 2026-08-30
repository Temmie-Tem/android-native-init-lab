#!/usr/bin/env python3
"""Close H41 run-01 before candidate intent; never replay Recovery transition."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
ENGINE_PATH = MODULE_DIR / "a90_h37_pre_candidate_recovery_park_close_v1.py"
SPEC = importlib.util.spec_from_file_location("_a90_h41_park_close_engine_v1", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("H41 park-close engine import failed")
engine = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)
if Path(getattr(engine, "__file__", "")).resolve() != ENGINE_PATH:
    raise RuntimeError("H41 park-close engine identity changed")

owner = engine.owner
adapter = engine.adapter
CAPABILITY = "A90_H41_PRE_CANDIDATE_RECOVERY_PARK_CLOSE_V1"
RUN_ID = "a90-h41-f1-20260830-01"
MANIFEST_SHA256 = "9e36c570095f1b383c1c3bc16367eecd6d211173ddc27a8c6142dde3d8569d43"
SELF_REL = "workspace/public/src/scripts/server-distro/a90_h41_pre_candidate_recovery_park_close_v1.py"
ENGINE_REL = "workspace/public/src/scripts/server-distro/a90_h37_pre_candidate_recovery_park_close_v1.py"
TEST_REL = "tests/test_a90_h41_pre_candidate_recovery_park_close_v1.py"
REPORT_REL = "docs/reports/A90_H41_PRE_CANDIDATE_RECOVERY_PARK_2026-08-30.md"
REVIEW_SCHEMA = "a90-h41-pre-candidate-recovery-park-close-review-v1"
RESULT_SCHEMA = "a90-h41-pre-candidate-recovery-park-close-result-v1"
INTENT_SCHEMA = "a90-h41-pre-candidate-recovery-park-close-observation-intent-v1"

JOURNAL_HASHES = {
    "00-prepared.json": "0138113dcbe27e0ace2c34fcdffc2cff49590b53cc8ddb1c24e016584325587e",
    "10-approved.json": "9eb796e28b21a006646e0f04b01d7ef154e9c576cfc628399b6ccfea63173116",
    "11-recovery-transition-intent.json": "f140d802048cca6de3caaebb6d7cdfa3b4750e4e46d23c581b58bb27db5a0066",
    "13-recovery-transition-parked.json": "5abcac5fd14377a4cb57f874bb8bbbe07d489a3a4fc492814dfb73f0ac417a9e",
}
LOG_HASHES = {
    "001-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "001-usb-inventory.stdout": "fa7a9aff2a906a67cb1a9663f6e78740f5ac6dac95450cbacee81394eddb1509",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "b8bdf0e5044a80656af6184e2c04e9d7f8ff11d6c3c163c8c9ce0da916d30bd1",
    "003-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-boot-id-start.stdout": "0cf5735293b3aaf4dff70bcf8fcb92b7cb5b2228a5564dfb24b61c5cd5a54454",
    "004-version.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "004-version.stdout": "0a01d6b63150098716a1c1b6ec323ee8e039c4299201d1417e595fa12af4ca8d",
    "005-selftest.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "005-selftest.stdout": "7adb9d4236fbc16c1f11794329738d7e200953b916b159eb4839f21b44fe4634",
    "006-status.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "006-status.stdout": "be437964a36374ade3dbaf3cbcb66ce1b2b2846ec1d131cfa327d9990181ba7f",
    "007-boot-id-final.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "007-boot-id-final.stdout": "9e015638f20d5d2fd83f89216a020244a3862181835fd866847675434a87bd52",
    "008-fresh-enable-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "008-fresh-enable-path.stdout": "8eea531652a98e3d2889ded63b5d9c399bbe2ce0a8896ad9d136d3dfa5cb1318",
    "009-fresh-latch-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "009-fresh-latch-path.stdout": "cdf4c383f39961ff7d9d6569c2802696e88255dd739258d90b7edafa9dfe6e39",
    "010-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "010-effect-usb-inventory.stdout": "fa7a9aff2a906a67cb1a9663f6e78740f5ac6dac95450cbacee81394eddb1509",
    "011-native-to-recovery.stderr": "7f274be06506a572298531033a73e4f57158ee0ab996244455588b071ea4b715",
    "011-native-to-recovery.stdout": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


def configure() -> None:
    values = {
        "CAPABILITY": CAPABILITY,
        "REVIEW_SCHEMA": REVIEW_SCHEMA,
        "REVIEW_DATE": "2026-08-30",
        "RESULT_SCHEMA": RESULT_SCHEMA,
        "INTENT_SCHEMA": INTENT_SCHEMA,
        "RUN_ID": RUN_ID,
        "MANIFEST": owner.REPO_ROOT / "workspace/private/manifests/a90-h41-f1-20260830-01.json",
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "REVIEW": owner.REPO_ROOT / "docs/reports/A90_H41_PRE_CANDIDATE_RECOVERY_PARK_CLOSE_REVIEW_2026-08-30.json",
        "SIDE_ROOT": owner.REPO_ROOT / "workspace/private/runs/a90-h41-pre-candidate-recovery-park-close-v1",
        "APPROVAL_PREFIX": "A90-H41-PRE-CANDIDATE-PARK-CLOSE-V1-APPROVE:",
        "SELF_REL": SELF_REL,
        "TEST_REL": TEST_REL,
        "EXTRA_CLOSURE_RELS": (ENGINE_REL, REPORT_REL),
        "REQUIRE_INTENT_FOR_RESULT": True,
        "JOURNAL_HASHES": JOURNAL_HASHES,
        "LOG_HASHES": LOG_HASHES,
    }
    values["RESULT"] = values["SIDE_ROOT"] / "result.json"
    for name, value in values.items():
        setattr(engine, name, value)


configure()
closure_sha256 = engine.closure_sha256
token = engine.token
execute = engine.execute


def main(argv: list[str] | None = None) -> int:
    return engine.main(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        engine.CloseError,
        owner.ContractError,
        adapter.ContractError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
