#!/usr/bin/env python3
"""One attended y2q later kernel-stage trial with independent ACM PID 1 evidence."""

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
PROFILE = "s20plus-g986n-pid1-stage-f1"
HEADING = "## S20+ y2q PID1 stage trial under one attended approval\n"
PREFIX = "S20PLUS-G986N-PID1-STAGE-F1-APPROVE:"
RUN_ROOT = PRIVATE / "runs" / PROFILE
EXP = PRIVATE / "analysis/s20plus-y2q-pid1-next-20261127"
PAIR = EXP / "packaged/pair.json"
STAGE = EXP / "candidate/stage.json"
QUAL = EXP / "qualification.json"
SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
BUILD = SOURCE / "build_pid1_stage.py"
READER = SOURCE / "pid1_stage_reader.py"
FILTER = SOURCE / "pid1-stage-filter.awk"
WRITER = SOURCE / "pid1-stage-witness.c"
TEST = ROOT / "tests/test_s20plus_g986n_pid1_stage_f1.py"
READER_TEST = ROOT / "tests/test_s20plus_y2q_pid1_stage_reader.py"
READER_TEST_SHA = "1bd69fd6d19f09eef3d7f60a78fed6d0a134a63ca7c175b86a2713796bcb8d9c"
CSTAGE_SOURCE = Path(cstage.__file__)
CSTAGE_SHA = "32d34edbd7b1fd2ce21e8a2880db02d2e7c3587a57344e473b189ef5be04b56a"
CSTAGE_PROFILE, CSTAGE_HEADING = cstage.PROFILE, cstage.HEADING
LAST = PRIVATE / "runs" / CSTAGE_PROFILE / "run-1795717837883139539"
ADJACENCY = PRIVATE / "runs/s20plus-g986n-cstage-adjacency-d0/observation/result.json"
SOURCE_PINS = {
    LAST / "terminal.json": "4acf0f9f96487a95089455a2ec4192107ec5a21fb30b674d7bc9bc3bf007890c",
    LAST / "final-health.json": "f81d0319e1cba22c5a1a11fb1999b1374dba65935503379d0dfba24f92ba92a3",
    LAST / "mainline-return-evidence.json": "fb11ec59fe8ffc3e82c0ee72103dc77db24764c3979eb93d2e0ac843530fbace",
    LAST / "rollback-result.json": "9e61e06c5621c838c859a482a2ca42f7c1d44b706d76d1e5d1cd484487c819bd",
    ADJACENCY: "38431613bdc66841b0f08ff0ab19a1044a763e066c690601d68649f62aac1b68",
}
ORIGINAL = cstage.ORIGINAL
ORIGINAL_AP = PRIVATE / "outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback/AP.tar.md5"
RETAINED_BIND, RETAINED_CONFIGURE = cstage.bind, cstage._configure_runtime
RETAINED_C_READER, RETAINED_FILTER = cstage.READER, cstage.FILTER
STAGES = ("exec_attempt", "el0_getpid")
INIT_ELF_SHA = "f9b07dbca775cc81eba24a30fcfa31c05fee35efbe92da3a541bc7a03d324f61"

PAIR_SHA = "08b5627ac5dd1cb11f3ea958b4bc69e5ee6a593bea5095ab6adf7d0e6dee890b"
STAGE_SHA = "c18120c692470579f0afc0720d259cd683c765a468f51316be4c17eb210b6e2a"
BUILD_SHA = "8f6eb5482b69f559b2555acf121c3f24e3c661b9aeb9d7893eb97e321d58a9c9"
READER_SHA = "d753824fb41a6773a6333389a09f64aaa3ea30ece3f71f17ba5e021441f4093a"
FILTER_SHA = "21c89c24345fe45a2e852729e1b1a8171c64f9b2f002ec7f616550642d2fda42"
WRITER_SHA = "e786458a417a39b878a2143d8e3603f4eecfd7f865197af8fee83d99a4c44b34"
CANDIDATE = "bd55d714cebf1a4931c31cf4592f559a460283f947ff5dd9e5603bfa709391d7"
RAW = "c1ea8d0641eee4e306760579ca83ed01d0cb75aaf242fdf861f759b08b47da5f"
QUAL_SHA = "6e6ab43530fb9bfaf21418462a8cdca0da05f0efec6e534b709e152df29d1829"


@cache
def reader():
    base.pinned(FILTER, FILTER_SHA)
    module = stage.load(READER, "_s20_pid1_stage_return", READER_SHA)
    require(module.FILTER == FILTER and module.STAGES == STAGES, "PID1-stage reader profile differs")
    return module


@cache
def observer():
    stage.load(cstage.TTY_READER, cstage.TTY_READER.stem, cstage.TTY_READER_SHA)
    module = owner.load_exact(cstage.OBSERVER, "_s20_pid1_stage_acm", acm_source())
    module.PROFILE, module.RUN_ROOT, module.CANDIDATE = PROFILE, RUN_ROOT, CANDIDATE
    return module


def acm_source():
    raw = base.pinned(cstage.OBSERVER, cstage.OBSERVER_SHA)
    original = b"base.SCRIPT.name == 's20plus_g986n_cstage_list_f1.py'"
    require(raw.count(original) == 1, "retained ACM owner gate differs")
    return raw.replace(original, f"base.SCRIPT.name == '{SCRIPT.name}'".encode(), 1)


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    probe = reader()
    frames = probe.frames(nonce)
    require(
        data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR"
        and data["profile"] == PROFILE
        and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["device_commands"] == 0
        and data["clear_frames_absent_from_both_boots"] is True
        and meta["kind"] == "HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS"
        and meta["profile"] == PROFILE
        and meta["init_elf"] == INIT_ELF_SHA
        and meta["nonce"] == nonce
        and tuple(frames) == probe.STAGES == STAGES
        and all(len(frame) == 128 for frame in frames.values())
        and meta["stages"] == {label: hashlib.sha256(frame).hexdigest() for label, frame in frames.items()}
        and data["raw"] == meta["raw"] == RAW
        and data["return_template"] == hashlib.sha256(probe.shell(nonce, "0" * 64).encode()).hexdigest(),
        "candidate PID1-stage package or return reader differs",
    )
    for role, digest, path in (
        ("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
        ("rollback", ORIGINAL, ORIGINAL_AP),
    ):
        archive = data["archives"][role]
        require(archive["ap"]["path"] == str(path) and archive["ap"]["sha256"] == digest
                and archive["only_member"]["name"] == "boot.img.lz4"
                and archive["decoded_boot"]["size"] == 67108864,
                "unexpected PID1-stage or original boot archive")
    return dict(**data["archives"], nonce=nonce)


def calibrated_identity():
    saved = {path: json.loads(base.pinned(path, pin)) for path, pin in SOURCE_PINS.items()}
    terminal, final, scan, rollback = (saved[LAST / name] for name in
        ("terminal.json", "final-health.json", "mainline-return-evidence.json", "rollback-result.json"))
    compared = saved[ADJACENCY]
    source = base.source_fields(final["health"])
    ap = rollback["receipt"]["ap"]
    require(
        terminal["verdict"] == "NO_PROOF_Y2Q_CSTAGE_ORIGINAL_MAGISK_RETURNED"
        and terminal["experiment_pass"] is False
        and terminal["version"] == final["version"] == rollback["version"] == CSTAGE_PROFILE
        and terminal["binding_sha256"] == final["binding_sha256"] == rollback["binding_sha256"]
        and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
        and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
        and terminal["rollback_transfer_completed"] is True
        and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
        and final["health"]["target"] == owner.TARGET
        and rollback["classification"] == "odin_transfer_completed"
        and ap["sha256"] == ORIGINAL and ap["path"] == str(ORIGINAL_AP)
        and scan["phase"] == "return" and scan["state"] == "ambiguous"
        and scan["fdt_count"] == scan["unflatten_count"] == 4
        and scan["boot_id_sha256"] == source["boot_id_sha256"]
        and compared["schema"] == "s20plus_g986n_cstage_adjacency_d0_v1"
        and compared["binding"] == source
        and compared["facts"] == dict(state="complete", size=scan["size"], fdt_count=4,
                                      unflatten_count=4, adjacent_pair_count=4),
        "original C-stage return or its same-boot comparison differs",
    )
    return source


def review():
    pins = {
        CSTAGE_SOURCE: CSTAGE_SHA,
        Path(cstage.previous.__file__): "1b4ff7c5175367e12088682afab7e4e49ee497f53ce840e2605c6edcc5c3fe1b",
        Path(base.__file__): "65921607a5ec5442d9542c3f616642dd6931fb58bba5efb876be4297e86f3676",
        Path(stage.__file__): base.REVIEWED_STAGE,
        base.CAL_SOURCE: base.CAL_SHA,
        base.READER: base.READER_SHA,
        RETAINED_C_READER: "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5",
        RETAINED_FILTER: "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
        cstage.OBSERVER: cstage.OBSERVER_SHA,
        cstage.TTY_READER: cstage.TTY_READER_SHA,
        cstage.OBSERVER_TEST: cstage.OBSERVER_TEST_SHA,
        BUILD: BUILD_SHA,
        READER: READER_SHA,
        FILTER: FILTER_SHA,
        WRITER: WRITER_SHA,
        READER_TEST: READER_TEST_SHA,
        PAIR: PAIR_SHA,
        STAGE: STAGE_SHA,
    }
    for path, digest in pins.items():
        base.pinned(path, digest)
    qual_raw = base.pinned(QUAL, QUAL_SHA)
    qual = json.loads(qual_raw)
    require((qual["candidate"], qual["rollback"], qual["raw"], qual["pair"], qual["stage"])
            == (CANDIDATE, ORIGINAL, RAW, PAIR_SHA, STAGE_SHA)
            and qual["device_commands"] == 0
            and isinstance(qual["evidence"], dict) and bool(qual["evidence"]),
            "qualification pair or evidence differs")
    for name, digest in qual["evidence"].items():
        rel = Path(name)
        require(rel.parts and not rel.is_absolute() and ".." not in rel.parts, "invalid qualification evidence path")
        base.pinned(EXP / rel, digest)

    policy = base.view.read_file(owner.CONTRACT).decode()
    inherited = {}
    for heading in (CSTAGE_HEADING, cstage.PREVIOUS_HEADING, cstage.previous.OLD_HEADING,
                    "## S20+ y2q mainline retained kernel stages attended F1\n"):
        require(policy.count(heading) == 1, "missing inherited S20+ scope")
        section = policy.split(heading, 1)[1].split("\n## ", 1)[0]
        inherited[heading.strip()] = hashlib.sha256(section.encode()).hexdigest()
    result = base.old_stage_review()
    result.update(schema="s20plus_pid1_stage_owner_v1", inherited_target_sections=inherited,
                  frozen={str(path): digest for path, digest in pins.items()},
                  source_close={str(path): digest for path, digest in SOURCE_PINS.items()},
                  acm_runtime=base.view.file_receipt(acm_source()),
                  qualification=base.view.file_receipt(qual_raw))
    return result


def witness_result(run, prepared, final, *, transfer_proved):
    log = stage.first_return(run, prepared, final)
    require(log == owner.engine.read_json(run / stage.paths("return")[2], "PID1-stage evidence"),
            "first-return PID1-stage receipt differs")
    attempt, entry, pairs = (log.get(key) for key in ("exec_attempt_count", "el0_getpid_count", "adjacent_pair_count"))
    complete = transfer_proved and log["state"] == "complete"
    return dict(
        usb_pid1=cstage.observe_acm_result(run, prepared, transfer_proved=transfer_proved),
        first_return=log["state"],
        exec_attempt_count=attempt,
        el0_getpid_count=entry,
        adjacent_pair_count=pairs,
        exec_attempt_observed=complete and attempt > 0,
        el0_getpid_entry_proved=complete and pairs > 0,
    )


def verdict(classification, claim, rollback):
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "final original health")
    require(claim == "NO_PROOF" and rollback is True, "unexpected transport claim or unproved original return")
    proof = witness_result(run, prepared, final, transfer_proved=classification == "odin_transfer_completed")
    stages = []
    if proof["el0_getpid_entry_proved"]:
        stages.append("EL0_PID1_GETPID")
    if proof["usb_pid1"] == "pid1_exact":
        stages.append("ACM_PID1")
    if stages:
        return "PROVED_Y2Q_" + "_AND_".join(stages) + "_ORIGINAL_MAGISK_RETURNED", True
    if proof["exec_attempt_observed"]:
        return "NO_PROOF_Y2Q_PID1_EXEC_ATTEMPT_OBSERVED_ORIGINAL_MAGISK_RETURNED", False
    return "NO_PROOF_Y2Q_PID1_STAGE_ORIGINAL_MAGISK_RETURNED", False


def render(result, run):
    if result.get("schema") == "s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prepared = owner.engine.read_json(run / "prepared.json", "prepared")
        final = owner.engine.read_json(run / "final-health.json", "final original health")
        proof = witness_result(run, prepared, final, transfer_proved=cstage.candidate_transfer_proved(run, prepared))
        print(json.dumps({"status": "PID1_STAGE_WITNESSES", **proof}), flush=True)
    return result


def _configure_runtime(module):
    RETAINED_CONFIGURE(module)


def bind():
    probe = reader()
    cstage.ACTIVE, cstage.SCRIPT, cstage.PROFILE = ACTIVE, SCRIPT, PROFILE
    cstage.EXP, cstage.HEADING, cstage.PREFIX = EXP, HEADING, PREFIX
    cstage.PAIR, cstage.PAIR_SHA, cstage.CANDIDATE = PAIR, PAIR_SHA, CANDIDATE
    cstage.BUILD, cstage.BUILD_SHA, cstage.TEST = BUILD, BUILD_SHA, TEST
    cstage.READER, cstage.FILTER, cstage.reader = READER, probe.FILTER, probe
    cstage.pair, cstage.review, cstage.calibrated_identity = pair, review, calibrated_identity
    cstage.render, cstage.verdict, cstage.observer = render, verdict, observer
    RETAINED_BIND()
    stage.APPROVAL = "S20PLUS-G986N-PID1-STAGE-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-PID1-STAGE-ARRIVAL:"
    stage._configure_runtime = _configure_runtime


def main(argv):
    base.bind = bind
    if argv[:1] != ["--in-source-view"]:
        args = base.parser().parse_args(argv)
        if args.execute:
            require(ACTIVE is True, "STOP_PID1_STAGE_F1_NOT_ACTIVE")
            require(args.run_dir is not None and isinstance(args.approval, str), "missing attended grant or run")
            bind()
            namespace = owner.namespace(
                ["--execute", "--run-dir", str(args.run_dir), "--approval", args.approval], connected=True
            )
            raise SystemExit(observer().launch(namespace, base.view.clean_environment(), args.run_dir, args.approval))
    base.main(argv)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(json.dumps({"status": "STOP_PID1_STAGE", "failure": type(exc).__name__,
                          "reason": str(exc)[:210] if isinstance(exc, (owner.Stop, ValueError)) else ""}))
        raise SystemExit(2)
