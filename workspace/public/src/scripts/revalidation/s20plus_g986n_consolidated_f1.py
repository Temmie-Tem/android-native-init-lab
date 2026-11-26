#!/usr/bin/env python3
"""One attended y2q initcall and USB trial with the retained original-only return."""

from functools import cache
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import s20plus_g986n_cstage_list_f1 as cstage

ACTIVE = True
SCRIPT = Path(__file__).resolve()
base, owner, stage = cstage.base, cstage.owner, cstage.stage
ROOT, PRIVATE, require = cstage.ROOT, cstage.PRIVATE, cstage.require
PROFILE = "s20plus-g986n-consolidated-f1"
HEADING = "## S20+ y2q consolidated initcall and USB trial under one attended approval\n"
PREFIX = "S20PLUS-G986N-CONSOLIDATED-F1-APPROVE:"
RUN_ROOT = PRIVATE / "runs" / PROFILE
EXP = PRIVATE / "analysis/s20plus-y2q-consolidated-20261127"
PAIR = EXP / "packaged/pair.json"
STAGE = EXP / "candidate/stage.json"
QUAL = EXP / "qualification.json"
SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
BUILD = SOURCE / "build_consolidated.py"
READER = SOURCE / "consolidated_reader.py"
FILTER = SOURCE / "consolidated-filter.awk"
WRITER = SOURCE / "consolidated-witness.c"
TEST = ROOT / "tests/test_s20plus_g986n_consolidated_f1.py"
READER_TEST = ROOT / "tests/test_s20plus_consolidated_reader.py"

PREDECESSOR = SCRIPT.with_name("s20plus_g986n_basic_setup_f1.py")
PREDECESSOR_SHA = "153435d8424664c3a66d3e4dd6dbff1aa9e27bfa0d1192846daeba821cc50583"
PREDECESSOR_PROFILE = "s20plus-g986n-basic-setup-f1"
PREDECESSOR_HEADING = "## S20+ y2q basic setup trial under one attended approval\n"
READBACK_HEADING = "## S20+ current restored boot basic-setup marker readback D0\n"
READBACK_OWNER = SCRIPT.with_name("s20plus_g986n_basic_setup_readback_d0.py")
READBACK_OWNER_SHA = "f33135e71f485f3cabb2fb7fd487ef4d0acd1cf7bbe9b110b88b87ffc669c106"
LAST = PRIVATE / "runs" / PREDECESSOR_PROFILE / "run-1795726991377518240"
READBACK = PRIVATE / "runs/s20plus-g986n-basic-setup-readback-d0/observation/result.json"
SOURCE_PINS = {
    LAST / "terminal.json": "9e9518abbd6f3d06e3c5e15a5103adff832c5546c22ab7a88df21a3c211cd90e",
    LAST / "final-health.json": "b16dd3ec3105905362aca215d5f788b8d28fff018f7e2ebd8506c66ef007bab7",
    LAST / "mainline-baseline-evidence.json": "383dea678fd1bee5222abba21022d68460a96d9cf93805ab27aca1a0b26da3ed",
    LAST / "mainline-return-evidence.json": "5535e5abe1904924cf8022e4effc747731c51c0adfb854ce9a0d2b13bba3c14a",
    LAST / "rollback-result.json": "394c94afe21dd4631e8d1733242329c2437af0eff0708362931a02b2a017ffc9",
    READBACK: "1d9dfef4bf8a5383ebe165970b5459a3208787f9393f04942258e4820abde550",
}
ORIGINAL = cstage.ORIGINAL
ORIGINAL_AP = PRIVATE / "outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback/AP.tar.md5"
FRAME_BYTES = 80
DIAGNOSTIC_BYTES = 240
STAGES = ("basic_enter",)
MILESTONES = ("basic_enter", "driver_ready", "flush1_enter", "flush1_return", "flush2_enter",
              "flush2_return", "basic_return", "initramfs_ready", "exec_attempt", "el0_getpid")
FIELDS = ("size", "anchor_count", "record_count")
PAIR_SHA = "58254c04feb670e1767c2426236852eb433e426e2124ab07cffbbced61029b61"
STAGE_SHA = "f5fce621f54cd84dec6a0738830ef15f8b5c791e1cd50c9172588d61e9d8d6da"
BUILD_SHA = "447e2c4bcbe55e50d01cc347db671a1aaccbdb31083b16619923bafd1b352671"
READER_SHA = "b0e4947cfd173663ec284ebb90230ac8eb13569bff5feaa01b5a94865b3427d9"
FILTER_SHA = "bff0e09869a5d815fce5e3ec4994ac16431897ae685bea934e955f880e445122"
WRITER_SHA = "c36d7d7b3f26bcc02f286acd0f9aa4b7e79518eb356a72d90f6e31c2f4b242d1"
READER_TEST_SHA = "5dc9ab68767fa996d9ce6d4ed675d80ff0e00d9e68713f278ae2b7633b9ab0df"
CANDIDATE = "7629240202f5fbe24efaa2a781b054755a733528e6d27b21caf646ba77e6ebe6"
RAW = "6c4b4a2f4e94852b155b25405f870104d77f21f270c46e1251f28457014d51a9"
QUAL_SHA = "9de4bafdb158e3705dd529664dbe023a7023028b9723e61a1f959afbd34d56d3"
HEADER = EXP / "candidate/build-id.h"
INIT_ELF = EXP / "candidate/ramfs/init"
INITRD = EXP / "candidate/handoff/bound-initrd.gz"
BOARD = EXP / "candidate/handoff/bound-board.dtb"
HEADER_SHA = "fe02f8ba07e3b71efd66d6a4f847815ea0f424585427198f67d79ed8c8a13a5f"
INIT_ELF_SHA = "182ab85bdf8abc7a6fce7e58a64ab77c2e99aca3d13980fb1a5c7bd316c843e4"
INITRD_SHA = "e9279dabdf923ff1dc39da59fa4bb392a28fa443418dbf6639a81ab0355d2b14"
BOARD_SHA = "541e220217f8bf0b65d4c18743a4ae6f8e7c35d6e5d9bc4497cda99655b433b8"


@cache
def inherited():
    basic = stage.load(PREDECESSOR, "_s20_consolidated_inherited_basic", PREDECESSOR_SHA)
    profile, _, _ = basic.inherited()
    return SimpleNamespace(basic=basic, bind=basic.bind, review=basic.review, scope=basic.scope,
                           configure=basic._configure_runtime, profile=profile, observer=profile.observer)


def calibrated_identity():
    saved = {path: json.loads(base.pinned(path, pin)) for path, pin in SOURCE_PINS.items()}
    terminal, final, rollback = (saved[LAST / name] for name in ("terminal.json", "final-health.json", "rollback-result.json"))
    baseline = saved[LAST / "mainline-baseline-evidence.json"]
    readback = saved[READBACK]
    source = base.source_fields(final["health"])
    ap = rollback["receipt"]["ap"]
    require(
        terminal["verdict"] == "NO_PROOF_Y2Q_BASIC_SETUP_ORIGINAL_MAGISK_RETURNED"
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
        and baseline["state"] == "no_record" and baseline["phase"] == "baseline"
        and baseline["boot_id_sha256"] != source["boot_id_sha256"]
        and all(baseline[k] == 0 for k in inherited().basic.COUNTS)
        and saved[LAST / "mainline-return-evidence.json"] == dict(
            phase="return", state="observation_gap", binding_sha256=terminal["binding_sha256"],
            final_health_sha256=SOURCE_PINS[LAST / "final-health.json"])
        and readback["schema"] == "s20plus_g986n_basic_setup_readback_d0_v1"
        and readback["scope"] == "CURRENT_RESTORED_BOOT_ONLY" and readback["first_return_attributed"] is False
        and readback["operator_reported_intervening_twrp"] is True and readback["binding"] == source
        and readback["terminal_sha256"] == SOURCE_PINS[LAST / "terminal.json"]
        and readback["facts"] == dict(state="complete", size=baseline["size"], dt_ready_count=4, basic_enter_count=4,
            basic_return_count=0, dt_enter_pair_count=4, enter_return_pair_count=0, triple_count=0),
        "proved basic-setup original return or separate current-boot readback differs",
    )
    return source


@cache
def observer():
    nonce = pair()["nonce"]
    module = inherited().observer()
    require(module.HEADER_SHA != HEADER_SHA and module.HEADER != HEADER,
            "candidate RAM init reused the historical ACM build identity")
    module.HEADER, module.HEADER_SHA = HEADER, HEADER_SHA
    serial, banner = module.witness()
    require(serial == "y2q-" + nonce
            and banner == f"\nS20PLUS_Y2Q_MAINLINE_V1 id={nonce} pid=1 stage=ACM_READY\n".encode(),
            "fresh ACM witness differs from the exact candidate")
    return module


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    probe = inherited().profile.reader()
    frames = probe.frames(nonce)
    require(
        data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR"
        and data["profile"] == meta["profile"] == PROFILE
        and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
        and meta["kind"] == "HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS" and meta["nonce"] == nonce
        and meta["init_elf"] == INIT_ELF_SHA and meta["initrd"] == INITRD_SHA and meta["board"] == BOARD_SHA
        and meta["build_id"] == HEADER_SHA and probe.MILESTONES == MILESTONES
        and base.pinned(HEADER, HEADER_SHA) == f'#define Y2Q_BUILD_ID "{nonce}"\n'.encode()
        and tuple(frames) == probe.STAGES == STAGES and len(frames["basic_enter"]) == FRAME_BYTES
        and meta["stages"] == {"basic_enter": hashlib.sha256(frames["basic_enter"]).hexdigest()}
        and data["raw"] == meta["raw"] == RAW
        and data["return_template"] == hashlib.sha256(probe.shell(nonce, "0" * 64).encode()).hexdigest(),
        "consolidated candidate package, fresh init or return reader differs",
    )
    for role, digest, path in (("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
                               ("rollback", ORIGINAL, ORIGINAL_AP)):
        archive = data["archives"][role]
        require(archive["ap"]["path"] == str(path) and archive["ap"]["sha256"] == digest
                and archive["only_member"]["name"] == "boot.img.lz4"
                and archive["decoded_boot"]["size"] == 67108864, "unexpected consolidated or original boot archive")
    return dict(**data["archives"], nonce=nonce)


def scope():
    return {**inherited().scope(), "diagnostic_bytes_per_kernel_entry": DIAGNOSTIC_BYTES,
            "regular_initcalls": 153, "trace_milestones": list(MILESTONES), "ram_init_udc_wait_seconds": 90}


def review():
    result = inherited().review()
    policy = base.view.read_file(owner.CONTRACT).decode()
    for heading in (PREDECESSOR_HEADING, READBACK_HEADING):
        require(policy.count(heading) == 1, "missing inherited basic-setup scope")
        section = policy.split(heading, 1)[1].split("\n## ", 1)[0]
        result["inherited_target_sections"][heading.strip()] = hashlib.sha256(section.encode()).hexdigest()
    frozen = {PREDECESSOR: PREDECESSOR_SHA, READBACK_OWNER: READBACK_OWNER_SHA,
              HEADER: HEADER_SHA, INIT_ELF: INIT_ELF_SHA, INITRD: INITRD_SHA, BOARD: BOARD_SHA}
    for path, digest in frozen.items():
        base.pinned(path, digest)
    result["frozen"].update({str(path): digest for path, digest in frozen.items()})
    result["schema"] = "s20plus_consolidated_owner_v1"
    return result


def witness_result(run, prepared, final, *, transfer_proved):
    log = stage.first_return(run, prepared, final)
    require(log == owner.engine.read_json(run / stage.paths("return")[2], "consolidated evidence"),
            "first-return consolidated receipt differs")
    complete = transfer_proved and log["state"] == "complete"
    progress_seen = complete and log["record_count"] > 0
    progress = inherited().profile.reader().describe(log["bitmap"]) if progress_seen else None
    return dict(
        usb_pid1=cstage.observe_acm_result(run, prepared, transfer_proved=transfer_proved),
        first_return=log["state"], **{key: log.get(key) for key in FIELDS}, progress=progress,
        basic_setup_call_site_observed=complete and (log["anchor_count"] > 0
            or progress_seen and "basic_enter" in progress["milestones"]),
        cumulative_trace_observed=progress_seen,
        el0_getpid_entry_proved=progress_seen and "el0_getpid" in progress["milestones"],
    )


def verdict(classification, claim, rollback):
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "final original health")
    require(claim == "NO_PROOF" and rollback is True, "unexpected transport claim or unproved original return")
    proof = witness_result(run, prepared, final, transfer_proved=classification == "odin_transfer_completed")
    labels = []
    if proof["el0_getpid_entry_proved"]:
        labels.append("EL0_PID1_GETPID")
    elif proof["cumulative_trace_observed"]:
        labels.append("KERNEL_PROGRESS")
    elif proof["basic_setup_call_site_observed"]:
        labels.append("BASIC_SETUP_CALL_SITE")
    if proof["usb_pid1"] == "pid1_exact":
        labels.append("ACM_PID1")
    if labels:
        return "PROVED_Y2Q_CONSOLIDATED_" + "_AND_".join(labels) + "_ORIGINAL_MAGISK_RETURNED", True
    return "NO_PROOF_Y2Q_CONSOLIDATED_ORIGINAL_MAGISK_RETURNED", False


def render(result, run):
    if result.get("schema") == "s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prepared = owner.engine.read_json(run / "prepared.json", "prepared")
        final = owner.engine.read_json(run / "final-health.json", "final original health")
        proof = witness_result(run, prepared, final, transfer_proved=cstage.candidate_transfer_proved(run, prepared))
        print(json.dumps({"status": "CONSOLIDATED_WITNESSES", **proof}), flush=True)
    return result


def _configure_runtime(module):
    inherited().configure(module)


def bind():
    retained = inherited()
    settings = dict(ACTIVE=ACTIVE, SCRIPT=SCRIPT, PROFILE=PROFILE, HEADING=HEADING, PREFIX=PREFIX,
                    RUN_ROOT=RUN_ROOT, EXP=EXP, PAIR=PAIR, STAGE=STAGE, QUAL=QUAL, BUILD=BUILD,
                    READER=READER, FILTER=FILTER, WRITER=WRITER, TEST=TEST, READER_TEST=READER_TEST,
                    SOURCE_PINS=SOURCE_PINS, STAGES=STAGES, FRAME_BYTES=FRAME_BYTES, PAIR_SHA=PAIR_SHA,
                    STAGE_SHA=STAGE_SHA, BUILD_SHA=BUILD_SHA, READER_SHA=READER_SHA, FILTER_SHA=FILTER_SHA,
                    WRITER_SHA=WRITER_SHA, READER_TEST_SHA=READER_TEST_SHA, CANDIDATE=CANDIDATE, RAW=RAW,
                    QUAL_SHA=QUAL_SHA, pair=pair, calibrated_identity=calibrated_identity, review=review,
                    render=render, verdict=verdict)
    for key, value in settings.items():
        setattr(retained.basic, key, value)
    retained.profile.INIT_ELF_SHA = INIT_ELF_SHA
    retained.profile.observer = observer
    retained.bind()
    stage.APPROVAL = "S20PLUS-G986N-CONSOLIDATED-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-CONSOLIDATED-ARRIVAL:"
    stage._configure_runtime = _configure_runtime
    owner.effect_profile = scope


def main(argv):
    retained = inherited()
    retained.basic.ACTIVE = ACTIVE
    retained.basic.bind = bind
    retained.basic.main(argv)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(json.dumps({"status": "STOP_CONSOLIDATED", "failure": type(exc).__name__,
                          "reason": str(exc)[:210] if isinstance(exc, (owner.Stop, ValueError)) else ""}))
        raise SystemExit(2)
