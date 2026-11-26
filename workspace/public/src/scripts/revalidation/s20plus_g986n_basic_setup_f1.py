#!/usr/bin/env python3
"""One attended y2q basic-setup trial with separate kernel and ACM evidence."""

from functools import cache
import hashlib
import json
from pathlib import Path
import sys

import s20plus_g986n_cstage_list_f1 as cstage

ACTIVE = True
SCRIPT = Path(__file__).resolve()
base, owner, stage = cstage.base, cstage.owner, cstage.stage
ROOT, PRIVATE, require = cstage.ROOT, cstage.PRIVATE, cstage.require
PROFILE = "s20plus-g986n-basic-setup-f1"
HEADING = "## S20+ y2q basic setup trial under one attended approval\n"
PREFIX = "S20PLUS-G986N-BASIC-SETUP-F1-APPROVE:"
RUN_ROOT = PRIVATE / "runs" / PROFILE
EXP = PRIVATE / "analysis/s20plus-y2q-basic-setup-20261127"
PAIR = EXP / "packaged/pair.json"
STAGE = EXP / "candidate/stage.json"
QUAL = EXP / "qualification.json"
SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
BUILD = SOURCE / "build_basic_setup_stage.py"
READER = SOURCE / "basic_setup_stage_reader.py"
FILTER = SOURCE / "basic-setup-stage-filter.awk"
WRITER = SOURCE / "basic-setup-stage-witness.c"
TEST = ROOT / "tests/test_s20plus_g986n_basic_setup_f1.py"
READER_TEST = ROOT / "tests/test_basic_setup_stage_reader.py"

PREDECESSOR = SCRIPT.with_name("s20plus_g986n_pid1_stage_f1.py")
PREDECESSOR_SHA = "b298bccbd2b152d7a908ce52ff22b4bef9129db3c031ca50c9d026ce51c43988"
PREDECESSOR_PROFILE = "s20plus-g986n-pid1-stage-f1"
PREDECESSOR_HEADING = "## S20+ y2q PID1 stage trial under one attended approval\n"
LAST = PRIVATE / "runs" / PREDECESSOR_PROFILE / "run-1795720157503161651"
SOURCE_PINS = {
    LAST / "terminal.json": "24526761a793e1a7f05b6da2d8e36966307ef3be4b5018142c09a7cc2b444803",
    LAST / "final-health.json": "b5843beacbbb918410f3a5bee5b89150859b5112d77d8a103e5546326a41e1cc",
    LAST / "mainline-baseline-evidence.json": "bb810a90b593958fade7daca3c99b213020e9b1b5f3fc89f34b594d704ca2927",
    LAST / "mainline-return-evidence.json": "b3c7168fbeb984a1604204a78148885dfc03936b0da30c440130241cbbf70ebd",
    LAST / "rollback-result.json": "0237a2f52b5bac6d7762426cbf1f8f6075b26ead79cc6ef278d4ba23af710fe8",
}
ORIGINAL = cstage.ORIGINAL
ORIGINAL_AP = PRIVATE / "outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback/AP.tar.md5"
RETAINED_SCOPE = cstage.scope

STAGES = ("dt_ready", "basic_enter", "basic_return")
FRAME_BYTES = 80
COUNTS = (*(label + "_count" for label in STAGES), "dt_enter_pair_count", "enter_return_pair_count", "triple_count")
KERNEL_PROOFS = ("DT_READY", "BASIC_SETUP_CALL_SITE", "BASIC_SETUP_RETURN")
PAIR_SHA = "2bdc73a5455c85b4df139bf343361307cf1932615ec7f3285846eb10741413d4"
STAGE_SHA = "37d83a435c590ac9e01e29a6a070d649fab7900b1be56ff40c08f30b9a16d67d"
BUILD_SHA = "d0225ff2433822977e318c78b5f5dc7bdea3a2d2f5872d2da8fc34c6d7d2f66d"
READER_SHA = "16e39156837f91bc9c316a23c96601c5471873edded440945830a2f554aa383f"
FILTER_SHA = "9bfa644a2cd04105a39d7c5b3053acf529eb1fd0c4a3fec11d948f1558e2f9fd"
WRITER_SHA = "04880e372b1d59be42cbdf4012146fa0549c719f51ae0b537cc98f4ccfe93a00"
READER_TEST_SHA = "a18b1f3bdce714e45c5275763512a69d882d62fb17df4965d53ac82ca8c40c26"
CANDIDATE = "095fa59a69c6bfe44dfec7abdfdf275d5ae02942247c8191d578bfdc57054499"
RAW = "a1ef2acb829e3a1f8c80336f2aa9052d1938ae6b4256a39e1f14d9ed0692fbc0"
QUAL_SHA = "652b39ad5c3fbad2582e3e2dbe21fe9e0f7d09720494b7ef4fd466b9fea19b02"


@cache
def inherited():
    profile = stage.load(PREDECESSOR, "_s20_basic_setup_inherited_pid1", PREDECESSOR_SHA)
    return profile, profile.bind, profile.review


def calibrated_identity():
    saved = {path.name: json.loads(base.pinned(path, pin)) for path, pin in SOURCE_PINS.items()}
    terminal, final, rollback = (saved[name] for name in ("terminal.json", "final-health.json", "rollback-result.json"))
    before, after = (saved[name] for name in ("mainline-baseline-evidence.json", "mainline-return-evidence.json"))
    source = base.source_fields(final["health"])
    ap = rollback["receipt"]["ap"]
    require(
        terminal["verdict"] == "NO_PROOF_Y2Q_PID1_STAGE_ORIGINAL_MAGISK_RETURNED"
        and terminal["experiment_pass"] is False
        and terminal["version"] == final["version"] == rollback["version"] == PREDECESSOR_PROFILE
        and terminal["binding_sha256"] == final["binding_sha256"] == rollback["binding_sha256"]
        and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
        and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
        and terminal["rollback_transfer_completed"] is True
        and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
        and final["health"]["target"] == owner.TARGET
        and rollback["classification"] == "odin_transfer_completed" and rollback["replay_permitted"] is False
        and ap["sha256"] == ORIGINAL and ap["path"] == str(ORIGINAL_AP)
        and before["state"] == after["state"] == "no_record"
        and before["phase"] == "baseline" and after["phase"] == "return"
        and before["boot_id_sha256"] != after["boot_id_sha256"] == source["boot_id_sha256"]
        and all(scan[key] == 0 for scan in (before, after)
                for key in ("exec_attempt_count", "el0_getpid_count", "adjacent_pair_count")),
        "original PID1-stage return or its zero-count boot brackets differ",
    )
    return source


def pair():
    profile, _, _ = inherited()
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    probe = profile.reader()
    frames = probe.frames(nonce)
    require(
        data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR"
        and data["profile"] == meta["profile"] == PROFILE
        and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
        and meta["kind"] == "HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS"
        and meta["init_elf"] == profile.INIT_ELF_SHA and meta["nonce"] == nonce
        and tuple(frames) == probe.STAGES == STAGES
        and all(len(frame) == FRAME_BYTES for frame in frames.values())
        and meta["stages"] == {label: hashlib.sha256(frame).hexdigest() for label, frame in frames.items()}
        and data["raw"] == meta["raw"] == RAW
        and data["return_template"] == hashlib.sha256(probe.shell(nonce, "0" * 64).encode()).hexdigest(),
        "candidate basic-setup package or return reader differs",
    )
    for role, digest, path in (("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
                               ("rollback", ORIGINAL, ORIGINAL_AP)):
        archive = data["archives"][role]
        require(archive["ap"]["path"] == str(path) and archive["ap"]["sha256"] == digest
                and archive["only_member"]["name"] == "boot.img.lz4"
                and archive["decoded_boot"]["size"] == 67108864,
                "unexpected basic-setup or original boot archive")
    return dict(**data["archives"], nonce=nonce)


def scope():
    return {**RETAINED_SCOPE(), "diagnostic_bytes_per_kernel_entry": FRAME_BYTES * len(STAGES)}


def review():
    _, _, retained_review = inherited()
    result = retained_review()
    policy = base.view.read_file(owner.CONTRACT).decode()
    require(policy.count(PREDECESSOR_HEADING) == 1, "missing inherited PID1-stage scope")
    section = policy.split(PREDECESSOR_HEADING, 1)[1].split("\n## ", 1)[0]
    result["inherited_target_sections"][PREDECESSOR_HEADING.strip()] = hashlib.sha256(section.encode()).hexdigest()
    base.pinned(PREDECESSOR, PREDECESSOR_SHA)
    result["frozen"][str(PREDECESSOR)] = PREDECESSOR_SHA
    result["schema"] = "s20plus_basic_setup_owner_v1"
    return result


def witness_result(run, prepared, final, *, transfer_proved):
    log = stage.first_return(run, prepared, final)
    require(log == owner.engine.read_json(run / stage.paths("return")[2], "basic-setup evidence"),
            "first-return basic-setup receipt differs")
    complete = transfer_proved and log["state"] == "complete"
    return dict(usb_pid1=cstage.observe_acm_result(run, prepared, transfer_proved=transfer_proved),
                first_return=log["state"], **{key: log.get(key) for key in COUNTS},
                **{label + "_observed": complete and log[label + "_count"] > 0 for label in STAGES})


def verdict(classification, claim, rollback):
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "final original health")
    require(claim == "NO_PROOF" and rollback is True, "unexpected transport claim or unproved original return")
    proof = witness_result(run, prepared, final, transfer_proved=classification == "odin_transfer_completed")
    labels = [verdict for label, verdict in zip(STAGES, KERNEL_PROOFS, strict=True) if proof[label + "_observed"]]
    if proof["usb_pid1"] == "pid1_exact":
        labels.append("ACM_PID1")
    if labels:
        return "PROVED_Y2Q_" + "_AND_".join(labels) + "_ORIGINAL_MAGISK_RETURNED", True
    return "NO_PROOF_Y2Q_BASIC_SETUP_ORIGINAL_MAGISK_RETURNED", False


def render(result, run):
    if result.get("schema") == "s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prepared = owner.engine.read_json(run / "prepared.json", "prepared")
        final = owner.engine.read_json(run / "final-health.json", "final original health")
        proof = witness_result(run, prepared, final, transfer_proved=cstage.candidate_transfer_proved(run, prepared))
        print(json.dumps({"status": "BASIC_SETUP_WITNESSES", **proof}), flush=True)
    return result


def _configure_runtime(module):
    inherited()[0]._configure_runtime(module)


def bind():
    profile, retained_bind, _ = inherited()
    settings = dict(ACTIVE=ACTIVE, SCRIPT=SCRIPT, PROFILE=PROFILE, HEADING=HEADING, PREFIX=PREFIX,
                    RUN_ROOT=RUN_ROOT, EXP=EXP, PAIR=PAIR, STAGE=STAGE, QUAL=QUAL, BUILD=BUILD,
                    READER=READER, FILTER=FILTER, WRITER=WRITER, TEST=TEST, READER_TEST=READER_TEST,
                    SOURCE_PINS=SOURCE_PINS, STAGES=STAGES, PAIR_SHA=PAIR_SHA, STAGE_SHA=STAGE_SHA,
                    BUILD_SHA=BUILD_SHA, READER_SHA=READER_SHA, FILTER_SHA=FILTER_SHA, WRITER_SHA=WRITER_SHA,
                    READER_TEST_SHA=READER_TEST_SHA, CANDIDATE=CANDIDATE, RAW=RAW, QUAL_SHA=QUAL_SHA,
                    pair=pair, calibrated_identity=calibrated_identity, review=review, render=render, verdict=verdict)
    for key, value in settings.items():
        setattr(profile, key, value)
    retained_bind()
    stage.APPROVAL = "S20PLUS-G986N-BASIC-SETUP-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-BASIC-SETUP-ARRIVAL:"
    stage._configure_runtime = _configure_runtime
    owner.effect_profile = scope


def main(argv):
    profile, _, _ = inherited()
    profile.ACTIVE = ACTIVE
    profile.bind = bind
    profile.main(argv)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(json.dumps({"status": "STOP_BASIC_SETUP", "failure": type(exc).__name__,
                          "reason": str(exc)[:210] if isinstance(exc, (owner.Stop, ValueError)) else ""}))
        raise SystemExit(2)
