#!/usr/bin/env python3
"""One attended S20+ stock-kernel run with a fresh compatible-list marker."""
import hashlib
import json
from pathlib import Path
import sys

import s20plus_g986n_early_pair_f1 as base

ACTIVE = True
SCRIPT = Path(__file__).resolve()
ROOT = base.ROOT
PRIVATE = base.view.PRIVATE
PROFILE = "s20plus-g986n-stock-list-f1"
HEADING = "## S20+ stock-kernel compatible-list control under one attended approval\n"
PREFIX = "S20PLUS-G986N-STOCK-LIST-F1-APPROVE:"
PROP = "/sys/firmware/devicetree/base/chosen/codex,y2q-stock-list-v1"
EXP = PRIVATE / "analysis/s20plus-y2q-stock-list-20261127"
PAIR = EXP / "packaged/pair.json"
PAIR_SHA = "a01dd24a635ee852ba6b8758624ef2bae7de8ced9ef3e1c027104072ab70b540"
CANDIDATE = "6d2ba177d6447fc166580d07e9bc34a4d771f4c97aabc272f9e7756a26463f25"
RAW = "5eee38a80f1ca2341b5d82e295600c81494619f2cceb6511cd90827519586ecc"
STOCK = SCRIPT.with_name("s20plus_g986n_stock_direct_f1.py")
STOCK_SHA = "b35a819f82ef06254b92eaf265b018fe2d6e3fd067fa095fedbb61f01c5f8b2c"
direct = base.stage.load(STOCK, "_s20_stock_list_transaction", STOCK_SHA)
DIRECT_HEADING = direct.HEADING
BUILD = direct.SRC / "build_list_control.py"
BUILD_SHA = "28103eab6c4b951b1e3b0ff76df712b08a32a77b3aa0ae384de7dc722abeba50"
GUARD_SHA = "131483342a5ec40a6378d16c6b1241f0cb3d319b281c78e43e373c8516ffe0fc"
LAST = PRIVATE / "runs/s20plus-g986n-stock-direct-f1/run-1795697759773921837"
TEST = ROOT / "tests/test_s20plus_g986n_stock_list_f1.py"
STAGE = EXP / "candidate/stage.json"
STAGE_SHA = "b4802551f80a5b338a665adf8a4dd373ef09a835c67b029647c1d2edbec3470c"
QUAL = EXP / "qualification.json"
QUAL_SHA = "125d68324a6bdcb7192e9b26c0726032c45b8bf19c4abe628eea6e6900327d84"
HISTORY = {
    "terminal": "e0118d4fcc77d6aa17b5656b771db30a5bb7261476dfdee71e0bd702eb42dde7",
    "final-health": "ff046fe9155d87808efbc1021828b268733890ef0804dce8ec8a50c7e43e2f4d",
    "mainline-return-evidence": "128e65c36662293cd075bcff415200c0b5460ccbe3559f3128f4860a99b6e4dc",
    "physical-rollback-arrival": "800f0d7e4049a5538dabed694ff648f3543903b2a2b9c089c165597ee17373b9",
    "rollback-result": "09e5b74e7f42cc1850c00f8078bedf55f857a13299fe20d994e74389a6b32648",
}


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    stage = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    frames = base.reader.frames(nonce, base.reader.EARLY_STAGES)
    base.require(data["kind"] == "HOST_ONLY_S20PLUS_STOCK_DIRECT_AP_PAIR"
                 and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
                 and data["raw"] == stage["raw"] == RAW and stage["nonce"] == nonce
                 and stage["guard"] == GUARD_SHA and stage["property"] == PROP.split("/")[-1]
                 and stage["single_producer"] == "prebranch"
                 and stage["stages"] == {k: hashlib.sha256(v).hexdigest() for k, v in frames.items()}
                 and data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
                 and data["return_template"] == hashlib.sha256(
                     base.reader.shell(nonce, "0"*64, base.reader.EARLY_STAGES).encode()).hexdigest(),
                 "stock compatible-list marker or package mismatch")
    original = PRIVATE / "outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback/AP.tar.md5"
    for role, digest, path in (("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
                               ("rollback", base.ORIGINAL, original)):
        item = data["archives"][role]
        base.require(Path(item["ap"]["path"]) == path and item["ap"]["sha256"] == digest
                     and item["decoded_boot"]["size"] == 67108864 and item["only_member"]["name"] == "boot.img.lz4",
                     "wrong boot archive role")
    return dict(**data["archives"], nonce=nonce)


def calibrated_identity():
    records = {name: json.loads(base.pinned(LAST / (name + ".json"), pin)) for name, pin in HISTORY.items()}
    final, terminal = records["final-health"], records["terminal"]
    returned, rollback = records["mainline-return-evidence"], records["rollback-result"]
    key = terminal["binding_sha256"]
    base.require(all(x["binding_sha256"] == key for x in records.values())
                 and terminal["verdict"] == "NO_PROOF_STOCK_DIRECT_MARKER_ORIGINAL_MAGISK_RESTORED"
                 and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
                 and final["rollback_outcome_proved"] and final["resident_boot_healthy"]
                 and final["health"]["target"] == base.OWNER.TARGET
                 and returned["tag"]["state"] == "ABSENT" and returned["health_sha256"] == HISTORY["final-health"]
                 and returned["original_transfer_sha256"] == HISTORY["rollback-result"]
                 and rollback["classification"] == "odin_transfer_completed"
                 and rollback["receipt"]["ap"] == pair()["rollback"]["ap"], "unproved last original return")
    return base.source_fields(final["health"])


def review():
    checked = {
        STOCK: STOCK_SHA, Path(base.__file__): direct.PARENT_SHA, Path(base.stage.__file__): base.REVIEWED_STAGE,
        base.CAL_SOURCE: base.CAL_SHA, BUILD: BUILD_SHA, PAIR: PAIR_SHA, STAGE: STAGE_SHA, QUAL: QUAL_SHA,
        base.READER: base.READER_SHA,
        base.reader.FILTER: "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
        direct.SRC / "build_control.py": "2ad5cc9ebfd5fdeecb74e0699c3c69f3096c18347c42a86486b4ee0371b462b5",
        direct.SRC / "handoff.patch": "9bf218bda9ceb5c29c94b66033dbb23cf1954837dfc56410aa0dd4bae93eeaa3",
        direct.SRC / "stock-control-fdt.h": "a198510941265062d691980315ac03fb7a650a4a423f695685a124167e74b62b",
        EXP / "candidate/control-src/guard.c": GUARD_SHA,
        EXP / "candidate/control-src/stock-control-fdt.h": "3adde71700c72aff2c66ecb4066625e74fb8d8185587a01f56ca7420a7dcee4d",
    }
    checked[EXP / "independent/result.json"] = "99cdd7204b8ab5dc0d94bcc3d7f963b7fbb85b535ba9eb5179ed7df7e05cb81e"
    qual = json.loads(base.pinned(QUAL, QUAL_SHA))
    base.require(qual["candidate"] == CANDIDATE and qual["raw"] == RAW and qual["rollback"] == base.ORIGINAL
                 and qual["stage"] == STAGE_SHA and qual["pair"] == PAIR_SHA,
                 "qualification belongs to a different pair")
    for path, pin in checked.items():
        base.pinned(path, pin)
    for name, pin in qual["evidence"].items():
        base.pinned(EXP / name, pin)
    policy = base.view.read_file(base.OWNER.CONTRACT).decode()
    inherited = {}
    for heading in (DIRECT_HEADING, "## S20+ y2q early handoff pair under one attended approval\n",
                    "## S20+ y2q mainline retained kernel stages attended F1\n"):
        base.require(policy.count(heading) == 1, "missing inherited stock transaction")
        inherited[heading.strip()] = hashlib.sha256(policy.split(heading)[1].split("\n## ", 1)[0].encode()).hexdigest()
    result = base.old_stage_review()
    result.update(schema="s20plus_stock_list_owner_v1", inherited_target_sections=inherited,
                  frozen={str(k): v for k, v in checked.items()})
    return result


def _configure_runtime(module):
    direct._configure_runtime(module)


def bind():
    # Configure the prior stock transaction inside this process only. Its original
    # entrypoint and all consumed tickets retain their original identities.
    direct.ACTIVE, direct.SCRIPT, direct.VERSION = ACTIVE, SCRIPT, PROFILE
    direct.HEADING, direct.PREFIX, direct.PROP = HEADING, PREFIX, PROP
    direct.EXP, direct.PAIR, direct.PAIR_SHA, direct.CANDIDATE = EXP, PAIR, PAIR_SHA, CANDIDATE
    direct.BUILD, direct.BUILD_SHA = BUILD, BUILD_SHA
    direct.pair, direct.review, direct.calibrated_identity = pair, review, calibrated_identity
    direct.bind()
    base.stage._configure_runtime = _configure_runtime
    base.CHECK = base.OWNER.TEST_SOURCE = TEST
    base.stage.APPROVAL = "S20PLUS-G986N-STOCK-LIST-BOUND:"
    base.stage.CONFIRM = "S20PLUS-G986N-STOCK-LIST-ARRIVAL:"


if __name__ == "__main__":
    base.bind = bind
    try:
        base.main(sys.argv[1:])
    except Exception as error:
        print(json.dumps({"status":"STOP_STOCK_LIST", "failure":type(error).__name__,
                          "reason":str(error)[:210] if isinstance(error, (base.OWNER.Stop, ValueError)) else ""}))
        raise SystemExit(2)
