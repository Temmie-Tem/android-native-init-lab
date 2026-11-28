#!/usr/bin/env python3
"""One attended S20+ TLMM/flush witness and original Magisk return."""
import hashlib
import json
from pathlib import Path
import sys

import s20plus_g986n_mainline_stage_f1 as stage

SCRIPT = Path(__file__).resolve()
PREVIOUS = SCRIPT.with_name("s20plus_g986n_deferred_worker_f1.py")
PREVIOUS_SHA = "29745e2a4821ecf9c0c64e91ef684f118db7db7d300371ed4ef0027dca67362b"
prior = stage.load(PREVIOUS, "_s20_tlmm_previous", PREVIOUS_SHA)
base, owner, parent, require = prior.base, prior.owner, prior.parent, prior.require
ACTIVE = True
PROFILE = "s20plus-g986n-tlmm-flush-f1"
PREFIX = "S20PLUS-G986N-TLMM-FLUSH-F1-APPROVE:"
HEADING = "## S20+ TLMM and first deferred flush attended trial\n"
RUN_ROOT = parent.PRIVATE/"runs"/PROFILE
EXP = parent.PRIVATE/"analysis/s20plus-y2q-tlmm-flush-h0-20261128"
SOURCE = parent.SOURCE
PAIR, STAGE = EXP/"packaged/pair.json", EXP/"candidate/stage.json"
QUAL = EXP/"physical-preparation/qualification.json"
BUILD, READER = SOURCE/"build_tlmm_flush_h0.py", SOURCE/"tlmm_return_reader.py"
WRITER, FILTER = SOURCE/"tlmm-flush-hooks.patch", SOURCE/"tlmm-return-filter.awk"
TEST = parent.ROOT/"tests/test_s20plus_g986n_tlmm_flush_f1.py"
READER_TEST = TEST
HEADER, INIT_ELF = EXP/"candidate/build-id.h", EXP/"candidate/ramfs/init"
BOARD, INITRD = EXP/"candidate/handoff/bound-board.dtb", EXP/"candidate/handoff/bound-initrd.gz"
LAST = prior.RUN_ROOT/"run-1795780019923307510"
PREVIOUS_HEADING = prior.HEADING
PREVIOUS_REVIEW = prior.review
PREVIOUS_SCOPE = prior.scope
PREVIOUS_BIND = prior.bind
STAGES = ("fixed_anchor",)
FRAME_BYTES = 80
CANDIDATE = "c5ebf1301144415a1b67b5607d891de27f82cac092adab37b01513570f2b7aa8"
RAW = "1b5abad22b8c6264a19efe092e71e4be1e5bc60a6ebca38aba1932b26fd5917b"
# PINS
PAIR_SHA = "d913c4695896f1ff9182f7ad52cff38f6a400b03036613af77a04cd15c957815"
STAGE_SHA = "270ac272b1210ce5dbde08c5b588057ce8cdbf7bb63d255fb9a41202505f745f"
BUILD_SHA = "51246556e40fa5cd1b9cc1c2ce2ec148be3b669ece8a93f2448d08d958b431d4"
READER_SHA = "62c24c00c5e09bb2baecfb3ad58267b9c5f1feba0a9e09dc970c751229c5296d"
FILTER_SHA = "9c7c65e8aef2604e802f82927535e96a5291df7b5e0991761251869515628410"
WRITER_SHA = "dff808857241b0588e42b0da38da31fcf4b109c97749f1429e029fc8e4c0f927"
READER_TEST_SHA = "e107a339cd49506d5a284ea8d33a039edf7e43e4519594fda9914d8ebcb12677"
HEADER_SHA = "0133bb0dac312d5dcaf2098e4dbbdfe8e8f5f61884c88048ead6d7568d0c2722"
INIT_ELF_SHA = "3a9fb612deb653f42fc08f052e4834dfa8992dde7e967abbf16021d2655e1822"
INITRD_SHA = "e1a808bf6d7e5febb4e7f7aaf164b4f5e2a2e68ef70e5325fbfd46cc1645ea58"
BOARD_SHA = "541e220217f8bf0b65d4c18743a4ae6f8e7c35d6e5d9bc4497cda99655b433b8"
QUAL_SHA = "618af30e2ea4fb200b618b6c28d5bd3a82c0d80e426feb807e46fc86c8280b32"
SOURCE_PINS = {
    LAST/"terminal.json": "5028689ab1c4201e2e9ebee8dafb5dff68e2d5340c788f681f1d84f76bd4468b",
    LAST/"final-health.json": "8251c1b3c2bb9159a0a5f75fadbb8cfaecfbb9716456afc06a4f6b9ac4fba6f1",
    LAST/"rollback-result.json": "5e771347c869cf617aaae7d8bc298e3f1a5e65baba09987a13d9dd736d8eb508",
}


def calibrated_identity():
    saved = {p.name:json.loads(base.pinned(p,pin)) for p,pin in SOURCE_PINS.items()}
    final, terminal, rollback = (saved[n] for n in ("final-health.json","terminal.json","rollback-result.json"))
    require(final["binding_sha256"] == terminal["binding_sha256"] == rollback["binding_sha256"]
            and terminal["version"] == "s20plus-g986n-deferred-worker-f1"
            and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
            and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
            and rollback["classification"] == "odin_transfer_completed" and rollback["replay_permitted"] is False
            and rollback["receipt"]["ap"]["sha256"] == parent.ORIGINAL
            and rollback["receipt"]["ap"]["path"] == str(parent.ORIGINAL_AP)
            and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
            and final["health"]["target"] == owner.TARGET, "prior original closure differs")
    return base.source_fields(final["health"])


def pair():
    data = json.loads(base.pinned(PAIR,PAIR_SHA))
    meta = json.loads(base.pinned(STAGE,STAGE_SHA))
    probe = parent.inherited().profile.reader()
    nonce = meta["nonce"]
    require(data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
            and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2" and meta["profile"] == "tlmm-flush-h0"
            and meta["nonce"] == data["nonce"] and data["raw"] == meta["raw"] == RAW
            and data["offline_reader_sha256"] == sha_file(SOURCE/"tlmm_flush_h0.py")
            and meta["stages"] == {k:hashlib.sha256(v).hexdigest() for k,v in probe.frames(nonce).items()}
            and base.pinned(HEADER,HEADER_SHA) == f'#define Y2Q_BUILD_ID "{nonce}"\n'.encode()
            and meta["init_elf"] == INIT_ELF_SHA and meta["initrd"] == INITRD_SHA and meta["board"] == BOARD_SHA,
            "qualified TLMM build differs")
    for role,path,pin in (("candidate",PAIR.with_name("AP.tar.md5"),CANDIDATE),
                          ("rollback",parent.ORIGINAL_AP,parent.ORIGINAL)):
        archive=data["archives"][role]
        require(archive["ap"]["path"] == str(path) and archive["ap"]["sha256"] == pin
                and archive["only_member"]["name"] == "boot.img.lz4" and archive["decoded_boot"]["size"] == 67108864,
                "boot archive differs")
    return {**data["archives"],"nonce":nonce}


def sha_file(path):
    return hashlib.sha256(base.view.read_file(path)).hexdigest()


def review():
    record = PREVIOUS_REVIEW()
    policy = base.view.read_file(owner.CONTRACT).decode()
    require(policy.count(PREVIOUS_HEADING)==1,"prior scope missing")
    section = policy.split(PREVIOUS_HEADING,1)[1].split("\n## ",1)[0]
    record["inherited_target_sections"][PREVIOUS_HEADING.strip()] = hashlib.sha256(section.encode()).hexdigest()
    record["frozen"][str(PREVIOUS)] = PREVIOUS_SHA
    record["frozen"][str(SOURCE/"tlmm_flush_h0.py")] = sha_file(SOURCE/"tlmm_flush_h0.py")
    record["schema"] = "s20plus_tlmm_flush_attended_v1"
    return record


def scope():
    return {**PREVIOUS_SCOPE(), "pid_publications_max":32, "worker_publications_max":32,
            "byte_stores_max":3160, "trace_milestones":list(stage.reader.offline.FLUSH)}


def proof(run, transfer_proved):
    prep = owner.engine.read_json(run/"prepared.json","candidate binding")
    final = owner.engine.read_json(run/"final-health.json","original health")
    log = stage.first_return(run,prep,final)
    require(log==owner.engine.read_json(run/stage.paths("return")[2],"return scan"),"return receipt differs")
    usb = prior.cstage.observe_acm_result(run,prep,transfer_proved=transfer_proved)
    accepted = transfer_proved and log["state"]=="complete"
    return dict(state=log["state"], initial=log.get("initial",[]) if accepted else [],
                worker=log.get("worker",[]) if accepted else [], flush=log.get("flush",[]) if accepted else [],
                completed_barrier_wait=accepted and log["completed_barrier_wait"],
                initial_rc_classes=log.get("initial_rc_classes",[]) if accepted else [],
                worker_rc_classes=log.get("worker_rc_classes",[]) if accepted else [],
                usb_pid1=usb, last_candidate_attempt="unknown")


def verdict(classification,claim,rollback):
    require(claim=="NO_PROOF" and rollback is True,"unexpected transport claim or unproved recovery")
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    result = proof(run,classification=="odin_transfer_completed")
    labels = []
    if "supplier_pdc" in result["initial"]:
        labels.append("INITIAL_PDC_DEFER")
    if "wake_missing" in result["initial"] or "wake_missing" in result["worker"]:
        labels.append("WAKE_DOMAIN_MISSING")
    if result["completed_barrier_wait"]:
        labels.append("FIRST_BARRIER_WAIT_RETURNED")
    if "no_barrier" in result["flush"]:
        labels.append("NO_BARRIER")
    if result["usb_pid1"]=="pid1_exact":
        labels.append("ACM_PID1")
    if labels:
        return "OBSERVED_TLMM_"+"_".join(labels)+"_ORIGINAL_RETURNED", True
    return "NO_PROOF_TLMM_CAUSE_OR_FLUSH_OUTCOME_ORIGINAL_RETURNED", False


def render(result,run):
    if result.get("schema")=="s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prep=owner.engine.read_json(run/"prepared.json","binding")
        print(json.dumps(dict(status="TLMM_FLUSH_WITNESSES",**proof(run,prior.cstage.candidate_transfer_proved(run,prep)))),flush=True)
    return result


def _configure_runtime(module):
    parent._configure_runtime(module)


def bind():
    for name in ("ACTIVE","SCRIPT","PROFILE","PREFIX","HEADING","RUN_ROOT","EXP","PAIR","STAGE","QUAL","BUILD","READER",
                 "FILTER","WRITER","TEST","READER_TEST","HEADER","INIT_ELF","BOARD","INITRD","STAGES","FRAME_BYTES",
                 "PAIR_SHA","STAGE_SHA","BUILD_SHA","READER_SHA","FILTER_SHA","WRITER_SHA","READER_TEST_SHA",
                 "CANDIDATE","RAW","QUAL_SHA","HEADER_SHA","INIT_ELF_SHA","INITRD_SHA","BOARD_SHA","SOURCE_PINS",
                 "pair","calibrated_identity","scope","review","verdict","render"):
        setattr(prior,name,globals()[name])
    PREVIOUS_BIND()
    stage._configure_runtime = _configure_runtime
    stage.APPROVAL = "S20PLUS-G986N-TLMM-FLUSH-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-TLMM-FLUSH-ARRIVAL:"


def main(argv):
    prior.ACTIVE=ACTIVE
    prior.bind=bind
    prior.main(argv)


if __name__=="__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(json.dumps({"status":"STOP_TLMM_FLUSH","error":type(exc).__name__,
                          "reason":str(exc)[:180] if isinstance(exc,(owner.Stop,ValueError)) else ""}))
        raise SystemExit(2)
