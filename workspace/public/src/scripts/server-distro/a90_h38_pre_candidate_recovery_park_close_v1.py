#!/usr/bin/env python3
"""Close the fixed H38 run-01 pre-candidate Recovery park read-only."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))
ENGINE_PATH = MODULE_DIR / "a90_h37_pre_candidate_recovery_park_close_v1.py"
SPEC = importlib.util.spec_from_file_location("_a90_h38_park_close_engine_v1", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("H38 park-close engine import failed")
engine = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = engine
SPEC.loader.exec_module(engine)
if Path(getattr(engine, "__file__", "")).resolve() != ENGINE_PATH:
    raise RuntimeError("H38 park-close engine identity changed")

owner = engine.owner
adapter = engine.adapter
CAPABILITY = "A90_H38_PRE_CANDIDATE_RECOVERY_PARK_CLOSE_V1"
RUN_ID = "a90-h38-f1-20260829-01"
MANIFEST_SHA256 = "f4c6175d92b71ff52089ff4bbdc507643cccd751fac2c00ec93d9dcb5eff4255"
SELF_REL = "workspace/public/src/scripts/server-distro/a90_h38_pre_candidate_recovery_park_close_v1.py"
ENGINE_REL = "workspace/public/src/scripts/server-distro/a90_h37_pre_candidate_recovery_park_close_v1.py"
TEST_REL = "tests/test_a90_h38_pre_candidate_recovery_park_close_v1.py"
REVIEW_SCHEMA = "a90-h38-pre-candidate-recovery-park-close-review-v1"
RESULT_SCHEMA = "a90-h38-pre-candidate-recovery-park-close-result-v1"
INTENT_SCHEMA = "a90-h38-pre-candidate-recovery-park-close-observation-intent-v1"

JOURNAL_HASHES = {
    "00-prepared.json": "d2ab3ff13e1762d58ce77c94166841746ed568e9d37774f59ddb1ca842a6ddb6",
    "10-approved.json": "fe9e5a98a4d4e4c0cd906165014a9e54144d66aa43df0e2dab7fb4be59f0d422",
    "11-recovery-transition-intent.json": "a0cd497885df3a8da4c5029e93022c4325fbf9d20b16c5ccc0b07ad3b1a764c6",
    "13-recovery-transition-parked.json": "98a3132df55fdd75cf967ca384194f645d8ed55e908ee26c3f7f1d936a47b691",
}
LOG_HASHES = {
    "001-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "001-usb-inventory.stdout": "862a640ff98d422db8aa65d0b76ac1df447b492dcbc7d8b827342adbabb2efda",
    "002-bridge-preflight.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "002-bridge-preflight.stdout": "98128fc109d245716b8230186b3543ce7a711611117c4ee2d29897cff447ff1d",
    "003-boot-id-start.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "003-boot-id-start.stdout": "c33eb2d7fe5d39390125303fd061d4019435275f41caf5f1ab985a16f4232136",
    "004-version.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "004-version.stdout": "8ddd95edf8117ce534bc0d88b098f868c9718d2237cdb732f1b85d50c9b6b1e7",
    "005-selftest.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "005-selftest.stdout": "66a7deb45f27fab9d99431b84092eb99e2c6515abeaa544a83c915f6a3bbf3bb",
    "006-status.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "006-status.stdout": "7842ddf43dc960f60a10ca43b8f00b19daaceedb92d30ff4f300bf4d80b67031",
    "007-boot-id-final.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "007-boot-id-final.stdout": "815ce473b687b33fbaf8de230c8250667d1d52c8d8a816d12d249e20db821f4b",
    "008-fresh-enable-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "008-fresh-enable-path.stdout": "61b5b3ec60a2f6e344f278d1c213958621deda5dfb3cc0483dcf9392dc211aaf",
    "009-fresh-latch-path.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "009-fresh-latch-path.stdout": "9bfd8a26f509ea9b488b8dfe67782afeb5600aae4e1e9759b3f6d62cd6898f4e",
    "010-effect-usb-inventory.stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "010-effect-usb-inventory.stdout": "862a640ff98d422db8aa65d0b76ac1df447b492dcbc7d8b827342adbabb2efda",
    "011-native-to-recovery.stderr": "695ca06a83b8e0fd63610d40a5d3ec7b2cc739c9f7e44359c34e8ea7510c303b",
    "011-native-to-recovery.stdout": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


def configure() -> None:
    values = {
        "CAPABILITY": CAPABILITY,
        "REVIEW_SCHEMA": REVIEW_SCHEMA,
        "RESULT_SCHEMA": RESULT_SCHEMA,
        "INTENT_SCHEMA": INTENT_SCHEMA,
        "RUN_ID": RUN_ID,
        "MANIFEST": owner.REPO_ROOT / "workspace/private/manifests/a90-h38-f1-20260829-01.json",
        "MANIFEST_SHA256": MANIFEST_SHA256,
        "REVIEW": owner.REPO_ROOT / "docs/reports/A90_H38_PRE_CANDIDATE_RECOVERY_PARK_CLOSE_REVIEW_2026-08-29.json",
        "SIDE_ROOT": owner.REPO_ROOT / "workspace/private/runs/a90-h38-pre-candidate-recovery-park-close-v1",
        "APPROVAL_PREFIX": "A90-H38-PRE-CANDIDATE-PARK-CLOSE-V1-APPROVE:",
        "SELF_REL": SELF_REL,
        "TEST_REL": TEST_REL,
        "EXTRA_CLOSURE_RELS": (ENGINE_REL,),
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
    except (engine.CloseError, owner.ContractError, adapter.ContractError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"{CAPABILITY} NO_GO: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
