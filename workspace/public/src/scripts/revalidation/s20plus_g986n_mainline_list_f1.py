#!/usr/bin/env python3
"""One attended mainline early-pair trial, with a physical first-return observer."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import s20plus_g986n_early_pair_f1 as base

ACTIVE = True
SCRIPT = Path(__file__).resolve()
ROOT, PRIVATE = base.ROOT, base.view.PRIVATE
owner, stage = base.OWNER, base.stage
require = base.require
PROFILE = "s20plus-g986n-mainline-list-f1"
HEADING = "## S20+ mainline compatible-list early pair under one attended approval\n"
PREFIX = "S20PLUS-G986N-MAINLINE-LIST-F1-APPROVE:"
ORIGINAL = base.ORIGINAL
EXP = PRIVATE / "analysis/s20plus-y2q-mainline-list-20261127"
PAIR = EXP / "packaged/pair.json"
PAIR_SHA = "3dc0b14204b28fbd1c87a49ee81bfff7141f7a1736353366ca6bfce3097b910d"
STAGE = EXP / "candidate/stage.json"
STAGE_SHA = "1a4eb13794a5f2ee16835bba2f39664445ae75fc3923ab4258a37be821035ccb"
CANDIDATE = "424ace70dcf22e5b2ed2b5b34636537f42acda19c914454c773455880ed44cdf"
RAW = "1a1ff679b68e5ed0b3f5649b1729d3a105bb9b3435716ac336475c0008f55ef9"
BUILD = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/build_mainline_list.py"
BUILD_SHA = "7429c414eea75229d21b575bc6d08ababcb8d104cb03607f9a6b03edb0c5a463"
TEST = ROOT / "tests/test_s20plus_g986n_mainline_list_f1.py"
LAST = PRIVATE / "runs/s20plus-g986n-stock-list-f1/run-1795713333849192239"
OLD_HEADING = base.HEADING
old_bind, configure_pair, recover_pending = base.bind, base._configure_runtime, base.restore
QUAL = EXP / "qualification.json"
QUAL_SHA = "6412e2c93a6984807f73669f63fba77875c8e482a51861d22007a1f91b016167"


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    frames = base.reader.frames(nonce, base.reader.EARLY_STAGES)
    require(meta["kind"] == "HOST_ONLY_Y2Q_EARLY_PAIR" and meta["nonce"] == nonce
            and meta["stages"] == {k: hashlib.sha256(v).hexdigest() for k, v in frames.items()}
            and data["raw"] == meta["raw"] == RAW and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
            and data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_EARLY_AP_PAIR"
            and data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
            and data["return_template"] == hashlib.sha256(
                base.reader.shell(nonce, "0"*64, base.reader.EARLY_STAGES).encode()).hexdigest(),
            "not the qualified mainline early-marker pair")
    original = PRIVATE / "outputs/s20plus_g986n/boot_recovery_canary_b0_v1/rollback/AP.tar.md5"
    for role, pin, path in (("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
                            ("rollback", ORIGINAL, original)):
        a = data["archives"][role]
        require(Path(a["ap"]["path"]) == path and a["ap"]["sha256"] == pin
                and a["only_member"]["name"] == "boot.img.lz4" and a["decoded_boot"]["size"] == 67108864,
                "wrong archive identity")
    return dict(**data["archives"], nonce=nonce)


def calibrated_identity():
    pins = {
        "terminal": "9a0354400077f81dff308c60ec60bb027b9f1db583d31828d48b34cb9bfc63a4",
        "final-health": "f2d261b3064c007165a0fce19f011c54ad2d9c6c07caf1327e0681bd197dd8e1",
        "mainline-return-evidence": "50427e45c013a073bc387f3f3f6c2b0bc8d054b1ef25df38fe228421d14aef2f",
        "rollback-result": "f4ac60a91fbf7758bf894b74c941e781a2f6bdc5cfc7513604633490b64e7d2f",
    }
    d = {k: json.loads(base.pinned(LAST / (k+".json"), v)) for k, v in pins.items()}
    t, f, a, ret = d["terminal"], d["final-health"], d["rollback-result"], d["mainline-return-evidence"]
    require(t["experiment_pass"] is True and t["verdict"] == "PROVED_STOCK_DIRECT_MARKER_ON_TAGGED_MAGISK_ORIGINAL_RESTORED"
            and all(x["binding_sha256"] == t["binding_sha256"] for x in d.values())
            and f["resident_boot_healthy"] and f["rollback_outcome_proved"] and f["rollback_transfer_completed"]
            and a["classification"] == "odin_transfer_completed" and a["receipt"]["ap"] == pair()["rollback"]["ap"]
            and ret["tag"]["state"] == "ABSENT" and ret["health_sha256"] == pins["final-health"]
            and ret["original_transfer_sha256"] == pins["rollback-result"] and f["health"]["target"] == owner.TARGET,
            "latest original Magisk return unproved")
    return base.source_fields(f["health"])


def review():
    pins = {
        Path(base.__file__): "65921607a5ec5442d9542c3f616642dd6931fb58bba5efb876be4297e86f3676",
        Path(stage.__file__): base.REVIEWED_STAGE, base.CAL_SOURCE: base.CAL_SHA,
        base.READER: base.READER_SHA,
        base.reader.FILTER: "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
        BUILD: BUILD_SHA, PAIR: PAIR_SHA, STAGE: STAGE_SHA, QUAL: QUAL_SHA,
        EXP / "independent/result.json": "ad55133cc0af32b426b582e61576be290222be1b54d97db3b8a9eb8f3ac0c818",
    }
    for path, pin in pins.items():
        base.pinned(path, pin)
    qual = json.loads(base.pinned(QUAL, QUAL_SHA))
    require((qual["candidate"], qual["rollback"], qual["raw"], qual["pair"], qual["stage"]) ==
            (CANDIDATE, ORIGINAL, RAW, PAIR_SHA, STAGE_SHA), "qualification pair changed")
    for name, pin in qual["evidence"].items():
        base.pinned(EXP / name, pin)
    policy = base.view.read_file(owner.CONTRACT).decode()
    headings = (OLD_HEADING, "## S20+ y2q mainline retained kernel stages attended F1\n",
                "## S20+ stock-kernel compatible-list control under one attended approval\n")
    inherited = {}
    for heading in headings:
        require(policy.count(heading) == 1, "missing inherited S20+ scope")
        inherited[heading.strip()] = hashlib.sha256(policy.split(heading)[1].split("\n## ", 1)[0].encode()).hexdigest()
    result = base.old_stage_review()
    result.update(schema="s20plus_mainline_list_owner_v1", inherited_target_sections=inherited,
                  frozen={str(path): pin for path, pin in pins.items()})
    return result


def archived_claim(run, key):
    e, runtime = owner.engine, owner.runtime
    local = owner.strict_private(run / "candidate-claim-intent.json", compact=True)
    claim = local["claim"]
    require(local["run_dir"] == claim["run_dir"] == str(run)
            and local["version"] == claim["version"] == PROFILE
            and local["binding_sha256"] == claim["binding_sha256"] == key
            and local["schema"] == "s20plus_g986n_b0_global_candidate_claim_intent_v1"
            and claim["schema"] == "s20plus_g986n_b0_global_candidate_consumed_v1"
            and claim["candidate_ap_sha256"] == CANDIDATE and claim["candidate_replay_permitted"] is False
            and claim["state"] == "uncertain-consumed-before-backend"
            and local["claim_sha256"] == e.digest(claim) and local["no_replay"] is True,
            "closed candidate claim differs")
    identity = runtime._registry_identity(run.name, key)
    intent = owner.strict_private(run / runtime.P0_REGISTRY_INTENT_NAME, compact=True)
    require(intent["candidate_identity"] == identity and intent["version"] == PROFILE
            and intent["schema"] == runtime.P0_REGISTRY_INTENT_SCHEMA and intent["binding_sha256"] == key
            and intent["candidate_replay_permitted"] is False, "closed registry intent differs")
    uncertain = run / runtime.P0_REGISTRY_UNCERTAIN_NAME
    if os.path.lexists(uncertain):
        require(not os.path.lexists(run / runtime.P0_REGISTRY_RECEIPT_NAME), "two registry dispositions")
        value = owner.strict_private(uncertain, compact=True)
        require(value == dict(schema=runtime.P0_REGISTRY_UNCERTAIN_SCHEMA, version=PROFILE, binding_sha256=key,
                              candidate_identity=identity, claim_intent_sha256=e.digest(intent),
                              registry_state="unavailable-after-claim-intent", consumed_uncertain=True,
                              candidate_replay_permitted=False, at=value["at"]), "closed registry cut differs")
    else:
        runtime._validate_local_registry_receipt(run, key, identity)


def archived_terminal(run):
    """Re-derive a completed post-candidate physical return from the saved journals."""
    v, _ = base.accepted(run)
    e = owner.engine

    def record(name):
        return owner.strict_private(run / (name + ".json"), compact=True)

    terminal = record("terminal")
    require(terminal["binding_sha256"] is not None, "pre-candidate abort belongs to --abort-pre-candidate")
    prep, final = record("prepared"), record("final-health")
    key, binding = prep["binding_sha256"], prep["binding"]
    require(e.digest(binding) == key and binding["run_dir"] == str(run)
            and binding["version"] == PROFILE and binding["target"] == owner.TARGET
            and base.source_fields(binding["preflight"]) == base.source_fields(v["health"])
            and terminal["binding_sha256"] == key, "closed run binding differs")
    archived_claim(run, key)
    base.initial_proof(run, v)
    baseline = stage.derive(run, "baseline", binding["preflight"])
    require(baseline["state"] == "no_record" and baseline == record("mainline-baseline-evidence"),
            "closed source marker baseline differs")

    arm = record("physical-rollback-intent")
    cue = base.get(base.ticket_dir(run), "physical-cue")
    arrival = record("physical-rollback-arrival")
    resumed_arrival = os.path.lexists(run / "physical-resume-observation-intent.json")
    expected_branch = "reporting-cut-current-arrival" if resumed_arrival else "attended-entry"
    if resumed_arrival:
        require(not os.path.lexists(run / stage.paths("return")[0]), "resumed arrival claimed a fresh scan")
    require(arm["branch"] == "attended-entry-required" and arm["baseline"]["endpoint_count"] == 0
            and cue == dict(run=str(run), arm_sha256=e.digest(arm), expires=arm["expires_unix"])
            and arrival["branch"] == expected_branch
            and e.same_download_session(arrival["endpoint"], record("rollback-intent")["endpoint"])
            and arrival["endpoint"]["topology_sha256"] == binding["endpoint"]["topology_sha256"]
            and e.same_download_session(record("candidate-intent")["endpoint"], binding["endpoint"]),
            "closed physical cue, arrival or transfer endpoint differs")
    # These retained B0 validators only read the named records. The namespace
    # validator also owns live claim publication and cannot run after release.
    required = {
        "prepared", "approval", "candidate-intent", "candidate-observation-intent", "candidate-observation",
        "physical-rollback-intent", "physical-confirmation-intent", "physical-observation-intent",
        "physical-rollback-arrival", "rollback-intent", "rollback-cage-quiescent", "rollback-result",
        "final-health", "terminal",
    }
    optional = {"candidate-transfer-cut", "candidate-result", "candidate-cage-quiescent",
                "physical-resume-observation-intent"}
    present = {name for name in optional if os.path.lexists(run / (name + ".json"))}
    require(len(present & {"candidate-result", "candidate-transfer-cut"}) == 1
            and not os.path.lexists(run / "physical-observation-miss.json")
            and not any(path.name.startswith(("rollback-download-", "rollback-reboot.")) for path in run.iterdir()),
            "ambiguous closed disposition")
    if "candidate-transfer-cut" in present:
        cut = record("candidate-transfer-cut")
        require(cut["possible_partition_effect"] is (record("candidate-intent").get("global_claim_cut") is not True)
                and cut["reason"] == "intent-consumed-result-absent", "closed candidate cut differs from its intent")
    stage.restored_original(run, prep, final)
    with stage.bound_run(run):
        e.validate_critical_records(run, {name + ".json" for name in required | present})
    return terminal


def finish_step(run, returned):
    """Keep an inner operation's completed result. Never finalize it again."""
    if returned.get("schema") != "s20plus_g986n_b0_terminal_v1":
        require(not os.path.lexists(run / "terminal.json"), "inner result conflicts with a saved terminal")
        return None
    saved = archived_terminal(run)
    require(returned == saved, "inner result differs from the saved terminal")
    return saved


def restore(run):
    base.accepted(run)
    if os.path.lexists(run / "terminal.json"):
        result = archived_terminal(run)
        if not os.path.lexists(owner.GUARD):
            return result
        guard = owner.strict_private(owner.GUARD, compact=True)
        require(guard == owner.engine.guard_value(run), "another owner holds the guard")
        return owner.engine.finalize_resident(run)
    if (not os.path.lexists(run / "rollback-intent.json")
            and not os.path.lexists(run / "candidate-observation.json")
            and (os.path.lexists(run / "candidate-claim-intent.json") or os.path.lexists(run / "candidate-intent.json"))):
        resumed = owner.engine.resume_run(run)
        result = finish_step(run, resumed)
        if result is not None:
            return result
        require(os.path.lexists(run / "candidate-observation.json") or os.path.lexists(run / "rollback-intent.json"),
                "resume did not establish an observation or rollback")
    return recover_pending(run)


def execute(run, approval):
    # Accept and bind the one grant exactly as in the early-pair transaction.
    v, key = base.subject(run)
    now = int(time.time())
    require(approval == PREFIX + key and v["issued"] <= now < v["expires"], "fresh attended approval required")
    require(not os.path.lexists(run), "run is not fresh")
    base.put(base.ticket_dir(run), "accepted",
             dict(grant_sha256=key, approved_at=now, approval_sha256=hashlib.sha256(approval.encode()).hexdigest()))
    e = owner.engine
    e.prepare(run)
    prep = owner.runtime._read_prepared_for_output(run)
    base.accepted(run, fresh=True)
    require(prep["binding"]["expires_unix"] <= v["expires"]
            and base.source_fields(prep["binding"]["preflight"]) == base.source_fields(v["health"]),
            "post-Download binding exceeds grant")
    print(json.dumps({"status":"CANDIDATE_ADMISSION_BOUND"}), flush=True)
    result = finish_step(run, e.execute(run, prep["approval_token"]))
    if result is not None:
        return result
    return restore(run)


def _configure_runtime(module):
    configure_pair(module)


def bind():
    base.ACTIVE, base.SCRIPT, base.PROFILE = ACTIVE, SCRIPT, PROFILE
    base.RUN_ROOT, base.EXP, base.HEADING, base.PREFIX = PRIVATE / "runs" / PROFILE, EXP, HEADING, PREFIX
    base.PAIR, base.PAIR_SHA, base.CANDIDATE = PAIR, PAIR_SHA, CANDIDATE
    base.CHECK, base.PACKAGER, base.PACKAGER_SHA = TEST, BUILD, BUILD_SHA
    base.pair, base.review, base.calibrated_identity = pair, review, calibrated_identity
    base.execute, base.restore = execute, restore
    old_bind()
    stage.APPROVAL = "S20PLUS-G986N-MAINLINE-LIST-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-MAINLINE-LIST-ARRIVAL:"
    stage._configure_runtime = _configure_runtime


if __name__ == "__main__":
    base.bind = bind
    try:
        base.main(sys.argv[1:])
    except Exception as exc:
        print(json.dumps({"status":"STOP_MAINLINE_LIST","failure":type(exc).__name__,
                          "reason":str(exc)[:210] if isinstance(exc,(owner.Stop,ValueError)) else ""}))
        raise SystemExit(2)
