#!/usr/bin/env python3
"""One attended y2q Linux C-stage trial and passive ACM PID 1 observation."""

from functools import cache
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import s20plus_g986n_mainline_list_f1 as previous

ACTIVE = True
SCRIPT = Path(__file__).resolve()
base, owner, stage = previous.base, previous.owner, previous.stage
ROOT, PRIVATE, require = previous.ROOT, previous.PRIVATE, previous.require
retained_prepare = base.prepare
PROFILE = "s20plus-g986n-cstage-list-f1"
HEADING = "## S20+ y2q Linux C-stage and ACM PID1 under one attended approval\n"
PREFIX = "S20PLUS-G986N-CSTAGE-LIST-F1-APPROVE:"
ORIGINAL = previous.ORIGINAL
EXP = PRIVATE / "analysis/s20plus-y2q-cstage-serial-20261127"
PAIR = EXP / "packaged/pair.json"
PAIR_SHA = "6131db908c212b11d8a1718e4f32d5d9bfb6fd518a3aace2f55d302c7f555489"
STAGE = EXP / "candidate/stage.json"
STAGE_SHA = "b7c4a59689d9cc5f7589a870dbb6809bb0a4cd9e17e2ea2d6fb57a6a6181d0e4"
CANDIDATE = "32e40210c5487f37de32c3d541e454df03e86855d74a5a9c5cf420f7811b5b68"
RAW = "2141646adbf6ca6066d8de2f42ab47ffc78bc15661695d2b12388d022aac852a"
QUAL = EXP / "qualification.json"
QUAL_SHA = "5b0b0cbf65f64d08e9734ff7f8c2c283fc18ad2abad7fc9c7387c26c0ee0cdfb"
BUILD = stage.BUILD / "build_stage.py"
BUILD_SHA = "39073ecfc682b5ea2b33809fb15ada5f649864dedab9f1a666ab27fd0a92ff4c"
SERIAL_BUILDER = BUILD.parent.parent / "build_cstage_serial.py"
SERIAL_BUILDER_SHA = "d0999cf4c1175a16c6089d1d1b755ff0f5add9c3f66cf616dee92ca0efffded9"
PACKAGER = stage.PACKAGER
READER = stage.READER
FILTER = stage.FILTER
reader = stage.reader
OBSERVER = SCRIPT.with_name("s20plus_g986n_cstage_acm.py")
OBSERVER_SHA = "bf452cccc6d4f41618fecd338165be1320bf50d4f39d21dde7622cb470bb7335"
TTY_READER = SCRIPT.with_name("s20plus_g986n_p0_pid1_usb_observer.py")
TTY_READER_SHA = "fea73e43a2cc640784046ac91e48dc5a9271855e8304c0458fba6e25909be538"
TEST = ROOT / "tests/test_s20plus_g986n_cstage_list_f1.py"
OBSERVER_TEST = ROOT / "tests/test_s20plus_g986n_cstage_acm.py"
OBSERVER_TEST_SHA = "939dae9755d9f224622783cba090b7c0b14903b6dccbaff8ffe0f1cc6f0e2a75"
LAST = PRIVATE / "runs/s20plus-g986n-mainline-list-f1/run-1795715419450778655"
PREVIOUS_HEADING = previous.HEADING
SOURCE_PINS = {
    "terminal": "2a73e13a634dcf194aef08fbee27891c4f87a546c8142c0b57a068a8885f3a71",
    "final-health": "ce47f5c81be38f9833752077b74341706c4b14dd189401b83c5cb0447f971747",
    "mainline-return-evidence": "164e097d071535074dec7b0af1e6190d963769b6e1e8f72a53dc3ec03b14e46c",
    "rollback-result": "a257d869b0369534e16e2151857a473f3b487f60c977aa3bcea15f6f741d61fe",
}
DWELL_SECONDS = 180
ACM_SUMMARY = "acm-evidence.json"


@cache
def observer():
    stage.load(TTY_READER, TTY_READER.stem, TTY_READER_SHA)
    return stage.load(OBSERVER, OBSERVER.stem, OBSERVER_SHA)


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    frames = reader.frames(nonce)
    require(
        data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR"
        and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
        and data["device_commands"] == 0
        and data["clear_frames_absent_from_both_boots"] is True
        and meta["kind"] == "HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS"
        and meta["nonce"] == nonce
        and tuple(frames) == ("fdt", "unflatten")
        and meta["stages"] == {name: hashlib.sha256(frame).hexdigest() for name, frame in frames.items()}
        and data["raw"] == meta["raw"] == RAW
        and data["return_template"] == hashlib.sha256(reader.shell(nonce, "0" * 64).encode()).hexdigest(),
        "candidate C-stage package or return reader differs",
    )
    original = PRIVATE / "outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback/AP.tar.md5"
    for role, digest, path in (
        ("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
        ("rollback", ORIGINAL, original),
    ):
        archive = data["archives"][role]
        require(
            archive["ap"]["path"] == str(path)
            and archive["ap"]["sha256"] == digest
            and archive["only_member"]["name"] == "boot.img.lz4"
            and archive["decoded_boot"]["size"] == 67108864,
            "unexpected C-stage or original boot archive",
        )
    return dict(**data["archives"], nonce=nonce)


def calibrated_identity():
    saved = {name: json.loads(base.pinned(LAST / (name + ".json"), digest))
             for name, digest in SOURCE_PINS.items()}
    t, f = saved["terminal"], saved["final-health"]
    a, scan = saved["rollback-result"], saved["mainline-return-evidence"]
    require(
        t["verdict"] == "NO_PROOF_Y2Q_EARLY_PAIR_RESIDENT_HEALTH_OBSERVED"
        and t["experiment_pass"] is False
        and t["version"] == f["version"] == a["version"] == "s20plus-g986n-mainline-list-f1"
        and t["binding_sha256"] == f["binding_sha256"] == a["binding_sha256"]
        and t["candidate_attempts"] == t["rollback_attempts"] == 1
        and t["candidate_replay_permitted"] is t["rollback_replay_permitted"] is False
        and t["rollback_transfer_completed"] is True
        and f["resident_boot_healthy"] is f["rollback_outcome_proved"] is f["rollback_transfer_completed"] is True
        and a["classification"] == "odin_transfer_completed"
        and a["receipt"]["ap"] == pair()["rollback"]["ap"]
        and scan["phase"] == "return" and scan["state"] == "ambiguous"
        and scan["boot_id_sha256"] == f["health"]["boot_id_sha256"]
        and f["health"]["target"] == owner.TARGET,
        "latest mainline-list trial did not establish the original source boot",
    )
    return base.source_fields(f["health"])


def scope():
    return dict(
        **base.old_scope(),
        sites=list(reader.STAGES),
        grant_origin="healthy-original-Android",
        one_attended_grant=True,
        rebind=False,
        calibrated_source=calibrated_identity(),
        candidate_dwell_seconds=DWELL_SECONDS,
        passive_acm="same-port-fixed-PID1-banner-read-only",
        host_serial_policy_checks=["prepare", "initial-reboot", "candidate-transfer"],
    )


def review():
    pins = {
        Path(previous.__file__): "1b4ff7c5175367e12088682afab7e4e49ee497f53ce840e2605c6edcc5c3fe1b",
        Path(base.__file__): "65921607a5ec5442d9542c3f616642dd6931fb58bba5efb876be4297e86f3676",
        Path(stage.__file__): base.REVIEWED_STAGE,
        base.CAL_SOURCE: base.CAL_SHA,
        base.READER: base.READER_SHA,
        READER: "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5",
        FILTER: "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
        PACKAGER: "672ea2268c813ef009ee0c2d1fc00260d494819b5084f5840be0e662c6066f7d",
        BUILD: BUILD_SHA,
        SERIAL_BUILDER: SERIAL_BUILDER_SHA,
        PAIR: PAIR_SHA,
        STAGE: STAGE_SHA,
        OBSERVER: OBSERVER_SHA,
        TTY_READER: TTY_READER_SHA,
        OBSERVER_TEST: OBSERVER_TEST_SHA,
    }
    for path, digest in pins.items():
        base.pinned(path, digest)
    qual_raw = base.pinned(QUAL, QUAL_SHA)
    qual = json.loads(qual_raw)
    require(
        (qual["candidate"], qual["rollback"], qual["raw"], qual["pair"], qual["stage"])
        == (CANDIDATE, ORIGINAL, RAW, PAIR_SHA, STAGE_SHA)
        and qual["device_commands"] == 0
        and isinstance(qual["evidence"], dict) and bool(qual["evidence"]),
        "qualification pair or evidence differs",
    )
    for name, digest in qual["evidence"].items():
        rel = Path(name)
        require(rel.parts and not rel.is_absolute() and ".." not in rel.parts, "invalid qualification evidence path")
        base.pinned(EXP / rel, digest)
    policy = base.view.read_file(owner.CONTRACT).decode()
    inherited = {}
    for heading in (PREVIOUS_HEADING, previous.OLD_HEADING, "## S20+ y2q mainline retained kernel stages attended F1\n"):
        require(policy.count(heading) == 1, "missing inherited S20+ scope")
        section = policy.split(heading, 1)[1].split("\n## ", 1)[0]
        inherited[heading.strip()] = hashlib.sha256(section.encode()).hexdigest()
    result = base.old_stage_review()
    result.update(
        schema="s20plus_cstage_list_owner_v1",
        inherited_target_sections=inherited,
        frozen={str(path): digest for path, digest in pins.items()},
        source_close=SOURCE_PINS,
        qualification=base.view.file_receipt(qual_raw),
    )
    return result


def candidate_transfer_proved(run, prepared):
    result = run / "candidate-result.json"
    if not os.path.lexists(result):
        return False
    if owner.engine.read_json(result, "candidate transfer")["classification"] != "odin_transfer_completed":
        return False
    owner.transfer_receipt(run, "candidate", prepared["binding_sha256"])
    return True


def observe(run, prepared):
    if candidate_transfer_proved(run, prepared):
        stop = time.monotonic() + DWELL_SECONDS
        transaction = owner.runtime._require_live_transaction()
        require(transaction["run_dir"] == str(run), "candidate observer escaped its leased run")
        if transaction["entrypoint"] == "execute":
            observer().observe(run, prepared)
        remaining = stop - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)
    return dict(environment="mainline-physical-return", transport_authorized=False,
                claim_verdict="NO_PROOF", at=owner.engine.utc_now()), None


def observe_acm_result(run, prepared, *, transfer_proved):
    path = base.ticket_dir(run) / ACM_SUMMARY
    if not transfer_proved:
        require(not os.path.lexists(path), "ACM evidence without a proven candidate transfer")
        return "transfer_unproved"
    if not os.path.lexists(path):
        return "observation_gap"
    value = owner.strict_private(path, compact=True)
    require(value["schema"] == "s20plus_cstage_acm_evidence_v1"
            and value["binding_sha256"] == prepared["binding_sha256"]
            and value["state"] in ("pid1_exact", "not_seen", "unproved"), "ACM receipt differs")
    observer().validate(value, run, prepared)
    return value["state"]


def witness_result(run, prepared, final, *, transfer_proved):
    log = stage.first_return(run, prepared, final)
    require(log == owner.engine.read_json(run / stage.paths("return")[2], "C-stage evidence"),
            "first-return C-stage receipt differs")
    acm = observe_acm_result(run, prepared, transfer_proved=transfer_proved)
    return dict(
        usb_pid1=acm,
        first_return=log["state"],
        fdt_count=log.get("fdt_count"),
        unflatten_count=log.get("unflatten_count"),
        fdt_proved=transfer_proved and log["state"] in ("fdt_only", "paired"),
        populated_root_proved=transfer_proved and log["state"] in ("unflatten_only", "paired"),
    )


def verdict(classification, claim, rollback):
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "final original health")
    require(claim == "NO_PROOF", "unexpected candidate transport claim")
    proof = witness_result(run, prepared, final, transfer_proved=classification == "odin_transfer_completed")
    labels = []
    if proof["fdt_proved"]:
        labels.append("FDT")
    if proof["populated_root_proved"]:
        labels.append("POPULATED_ROOT")
    if proof["usb_pid1"] == "pid1_exact":
        labels.append("ACM_PID1")
    if rollback is True and labels:
        return "PROVED_Y2Q_CSTAGE_" + "_AND_".join(labels) + "_ORIGINAL_MAGISK_RETURNED", True
    return "NO_PROOF_Y2Q_CSTAGE_ORIGINAL_MAGISK_RETURNED", False


def render(result, run):
    if result.get("schema") == "s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prepared = owner.engine.read_json(run / "prepared.json", "prepared")
        final = owner.engine.read_json(run / "final-health.json", "final original health")
        proof = witness_result(run, prepared, final, transfer_proved=candidate_transfer_proved(run, prepared))
        print(json.dumps({"status": "CSTAGE_WITNESSES", **proof}), flush=True)
    return result


def execute(run, approval):
    return render(previous.execute(run, approval), run)


def prepare():
    observer().host_serial_policy()
    return retained_prepare()


def restore(run):
    return render(previous.restore(run), run)


def raw_deadline(run):
    grant, _ = base.accepted(run, fresh=True)
    observer().host_serial_policy()
    require(time.time() < grant["expires"], "original candidate approval expired during host serial policy check")


def _configure_runtime(module):
    previous.configure_pair(module)
    module._early_effect_deadline = raw_deadline


def bind():
    previous.PROFILE, previous.PREFIX, previous.CANDIDATE = PROFILE, PREFIX, CANDIDATE
    base.ACTIVE, base.SCRIPT, base.PROFILE = ACTIVE, SCRIPT, PROFILE
    base.RUN_ROOT, base.EXP, base.HEADING, base.PREFIX = PRIVATE / "runs" / PROFILE, EXP, HEADING, PREFIX
    base.PAIR, base.PAIR_SHA, base.CANDIDATE = PAIR, PAIR_SHA, CANDIDATE
    base.CHECK, base.PACKAGER, base.PACKAGER_SHA = TEST, BUILD, BUILD_SHA
    base.pair, base.review, base.calibrated_identity = pair, review, calibrated_identity
    base.prepare, base.execute, base.restore = prepare, execute, restore
    previous.old_bind()
    stage.READER, stage.FILTER, stage.reader = READER, FILTER, reader
    stage.APPROVAL = "S20PLUS-G986N-CSTAGE-LIST-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-CSTAGE-LIST-ARRIVAL:"
    stage._configure_runtime = _configure_runtime
    owner.effect_profile = scope
    owner.observe_candidate = observe
    owner.terminal_verdict = verdict


def main(argv):
    base.bind = bind
    if argv[:1] != ["--in-source-view"]:
        args = base.parser().parse_args(argv)
        if args.execute:
            require(ACTIVE is True, "STOP_CSTAGE_LIST_F1_NOT_ACTIVE")
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
        print(json.dumps({"status": "STOP_CSTAGE_LIST", "failure": type(exc).__name__,
                          "reason": str(exc)[:210] if isinstance(exc, (owner.Stop, ValueError)) else ""}))
        raise SystemExit(2)
