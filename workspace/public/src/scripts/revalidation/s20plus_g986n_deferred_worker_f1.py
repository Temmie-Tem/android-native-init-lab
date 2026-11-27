#!/usr/bin/env python3
"""One attended y2q deferred-probe experiment with the original Magisk return."""
import hashlib
import json
from pathlib import Path
import sys

import s20plus_g986n_mainline_stage_f1 as stage

SCRIPT = Path(__file__).resolve()
ACTIVE = True
PREVIOUS = SCRIPT.with_name("s20plus_g986n_consolidated_f1.py")
PREVIOUS_SHA = "f30c18098da5ee033a4ad96c1119fc30ed4a71d735d3e41e37f0c44e12d6d12c"
parent = stage.load(PREVIOUS, "_y2q_deferred_parent", PREVIOUS_SHA)
base, owner, cstage, require = parent.base, parent.owner, parent.cstage, parent.require
PROFILE = "s20plus-g986n-deferred-worker-f1"
PREFIX = "S20PLUS-G986N-DEFERRED-WORKER-F1-APPROVE:"
HEADING = "## S20+ y2q deferred worker and first flush under one attended approval\n"
RUN_ROOT = parent.PRIVATE / "runs" / PROFILE
EXP = parent.PRIVATE / "analysis/s20plus-y2q-deferred-worker-f1"
PAIR = EXP / "packaged/pair.json"
STAGE = EXP / "candidate/stage.json"
QUAL = EXP / "qualification.json"
SOURCE = parent.SOURCE
BUILD = SOURCE / "build_deferred_worker.py"
READER = SOURCE / "deferred_reader.py"
FILTER = SOURCE / "deferred-filter.awk"
WRITER = SOURCE / "deferred-witness.c"
TEST = parent.ROOT / "tests/test_s20plus_g986n_deferred_worker_f1.py"
READER_TEST = parent.ROOT / "tests/test_s20plus_deferred_reader.py"
HEADER = EXP / "candidate/build-id.h"
INIT_ELF = EXP / "candidate/ramfs/init"
INITRD = EXP / "candidate/handoff/bound-initrd.gz"
BOARD = EXP / "candidate/handoff/bound-board.dtb"
LAST = parent.RUN_ROOT / "run-1795729541663678722"
OLD_HEADING = parent.HEADING
OLD_PROFILE = parent.PROFILE
OLD_READER = parent.READER
OLD_READER_SHA = parent.READER_SHA
OLD_FILTER = parent.FILTER
OLD_FILTER_SHA = parent.FILTER_SHA
OLD_CANDIDATE = parent.CANDIDATE
OLD_PAIR = parent.PAIR
OLD_PAIR_SHA = parent.PAIR_SHA
INHERITED_BIND, INHERITED_REVIEW, INHERITED_SCOPE = parent.bind, parent.review, parent.scope
# QUALIFIED-PINS
STAGES = ("run_anchor",)
FRAME_BYTES = 80
PAIR_SHA = "4e4943e84437655aa4a9ffcdd640297fe46f3ec9bb6e6d54c340642b6cff476f"
STAGE_SHA = "77e755e4ecafdd6bb582b576b3b890aba8a9c9e6c5e4bc647e8eb6e114ba1205"
BUILD_SHA = "fb2fd4703178f61f70da15b114b70471e555f54c75b529948eb78485cc03273c"
READER_SHA = "3ae47fda36ff1c32545d697b8c370563c63bf1d5fbc3e19e23c74016a0fb3153"
FILTER_SHA = "3f8640ede2a88f9f4d61ffac331b5f94cd4369cf5a4757d0875974ab88ba9826"
WRITER_SHA = "7227b2534e9e8d518d0f4cc45107f6caee782138179ffe7241b978f4c624e67d"
READER_TEST_SHA = "48a0eee9fddcf5a9c4ff4a8da0d06bc001238b4a42acbf7a497e1d9b98aeb8d9"
CANDIDATE = "bbedac5d6934a2a924a287c5f027cd1a324fccb14f4ae36a26b7788cfab01d13"
RAW = "5899861eb92f8d6ac796aa4b8173ac5386933e05bef86aa2ba79b5437de8a38d"
HEADER_SHA = "f79ce55174a6471bb035bf8eaddbdaa31998bef260dde9c0159084504a97f628"
INIT_ELF_SHA = "7f55d8d799691b7c7c64d691115655a1bba17530a70f6640870e1246e5701166"
INITRD_SHA = "b8807db378c5916056673cccd08133ea58ccf70da551aab8ba4b39d9e875fe75"
BOARD_SHA = "541e220217f8bf0b65d4c18743a4ae6f8e7c35d6e5d9bc4497cda99655b433b8"
HOOKS_SHA = "d4f7cc47df9707d1885e728660cf830a45e453c1274be1560c0cbe96f993039f"
QUAL_SHA = "d5bed095f1634d5970f0f30a5e57032117a1871e8a140c2417e3807706743566"
SOURCE_PINS = {
    LAST / "terminal.json": "4129da052df972c2486c117e8cada9c441bf8bf443d6f5dec46d0761fcdbf2c4",
    LAST / "final-health.json": "73cefc1e53dc7423b4c682f168ef46192db7a6209205c933a0534a537110cd27",
    LAST / "rollback-result.json": "0db5ed5f1fea1c3033f216f5cc94579917cef481b17e170d78bd3f95f6f102a3",
    LAST / "mainline-baseline-evidence.json": "30abc6348cb5c0b3212435a1c30ad426a2cc371553cd963f7c809f2715f7249f",
    LAST / "mainline-return-evidence.json": "0764bbafd5fc89968175afdb6699f513bc9e87b69e575edfb7988ce78ae5c06d",
}


def calibrated_identity():
    saved = {path.name: json.loads(base.pinned(path, pin)) for path, pin in SOURCE_PINS.items()}
    terminal, final, rollback = (saved[n] for n in ("terminal.json", "final-health.json", "rollback-result.json"))
    before, after = (saved[n] for n in ("mainline-baseline-evidence.json", "mainline-return-evidence.json"))
    source = base.source_fields(final["health"])
    require(terminal["verdict"] == "PROVED_Y2Q_CONSOLIDATED_KERNEL_PROGRESS_ORIGINAL_MAGISK_RETURNED"
            and terminal["experiment_pass"] is True
            and terminal["version"] == final["version"] == rollback["version"] == OLD_PROFILE
            and terminal["binding_sha256"] == final["binding_sha256"] == rollback["binding_sha256"]
            and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
            and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
            and terminal["rollback_transfer_completed"] is final["rollback_transfer_completed"] is True
            and final["rollback_outcome_proved"] is final["resident_boot_healthy"] is True
            and final["health"]["target"] == owner.TARGET
            and rollback["classification"] == "odin_transfer_completed" and rollback["replay_permitted"] is False
            and rollback["receipt"]["ap"]["sha256"] == parent.ORIGINAL
            and rollback["receipt"]["ap"]["path"] == str(parent.ORIGINAL_AP)
            and before["phase"] == "baseline" and before["state"] == "no_record"
            and after["phase"] == "return" and after["state"] == "complete"
            and after["boot_id_sha256"] == source["boot_id_sha256"] != before["boot_id_sha256"],
            "previous candidate, original return or capture changed")
    return source


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    reader = parent.inherited().profile.reader()
    nonce = data["nonce"]
    original_pair = json.loads(base.pinned(OLD_PAIR, OLD_PAIR_SHA))
    require(data["kind"] == "HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR"
            and meta["kind"] == "HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS"
            and data["profile"] == meta["profile"] == PROFILE
            and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2"
            and data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
            and original_pair["nonce"] != nonce == meta["nonce"] and OLD_CANDIDATE != CANDIDATE
            and base.pinned(HEADER, HEADER_SHA) == f'#define Y2Q_BUILD_ID "{nonce}"\n'.encode()
            and meta["build_id"] == HEADER_SHA and meta["init_elf"] == INIT_ELF_SHA
            and meta["board"] == BOARD_SHA and meta["initrd"] == INITRD_SHA
            and data["raw"] == meta["raw"] == RAW
            and meta["stages"] == {k: hashlib.sha256(v).hexdigest() for k, v in reader.frames(nonce).items()}
            and data["return_template"] == hashlib.sha256(reader.shell(nonce, "0" * 64).encode()).hexdigest(),
            "deferred-worker package, init or return reader differs")
    for key, expected, path in (("candidate", CANDIDATE, PAIR.with_name("AP.tar.md5")),
                                ("rollback", parent.ORIGINAL, parent.ORIGINAL_AP)):
        part = data["archives"][key]
        require(part["ap"]["path"] == str(path) and part["ap"]["sha256"] == expected
                and part["only_member"]["name"] == "boot.img.lz4" and part["decoded_boot"]["size"] == 67108864,
                "unexpected boot AP identity")
    return {**data["archives"], "nonce": nonce}


def scope():
    return {**INHERITED_SCOPE(), "regular_initcalls": 159, "deferred_initcall_index": 152,
            "pid_publications_max": 328, "worker_publications_max": 128, "byte_stores_max": 21976,
            "candidate_boot_recency": "unknown"}


def review():
    record = INHERITED_REVIEW()
    policy = base.view.read_file(owner.CONTRACT).decode()
    require(policy.count(OLD_HEADING) == 1, "missing consolidated scope")
    section = policy.split(OLD_HEADING, 1)[1].split("\n## ", 1)[0]
    record["inherited_target_sections"][OLD_HEADING.strip()] = hashlib.sha256(section.encode()).hexdigest()
    for f, pin in {PREVIOUS: PREVIOUS_SHA, OLD_PAIR: OLD_PAIR_SHA, OLD_READER: OLD_READER_SHA,
                   OLD_FILTER: OLD_FILTER_SHA, SOURCE / "deferred-probe-hooks.patch": HOOKS_SHA}.items():
        base.pinned(f, pin)
        record["frozen"][str(f)] = pin
    record["schema"] = "s20plus_deferred_worker_owner_v1"
    return record


def witness_result(run, prepared, final, *, transfer_proved):
    log = stage.first_return(run, prepared, final)
    require(log == owner.engine.read_json(run / stage.paths("return")[2], "deferred return evidence"),
            "stored return evidence differs")
    result = stage.reader.describe(log, transfer_proved)
    result["usb_pid1"] = cstage.observe_acm_result(run, prepared, transfer_proved=transfer_proved)
    if result["worker_sample"]:
        dictionary = json.loads(base.pinned(QUAL, QUAL_SHA))["direct_soc_names"]
        result["worker_name_candidates"] = dictionary.get(result["worker_sample"]["device_id"], [])
    return result


def verdict(classification, claim, rollback):
    require(claim == "NO_PROOF" and rollback is True, "unexpected transfer claim or missing recovery")
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    prepared = owner.engine.read_json(run / "prepared.json", "prepared")
    final = owner.engine.read_json(run / "final-health.json", "restored Android")
    proof = witness_result(run, prepared, final, transfer_proved=classification == "odin_transfer_completed")
    labels = []
    if proof["worker_sample"]:
        labels.append("WORKER_" + proof["worker_sample"]["operation"].upper())
    if proof["first_flush_return_observed"]:
        labels.append("FLUSH1_RETURN")
    if proof["el0_getpid_entry_observed"]:
        labels.append("EL0_PID1")
    if proof["usb_pid1"] == "pid1_exact":
        labels.append("ACM_PID1")
    if labels:
        return "OBSERVED_Y2Q_DEFERRED_RUN_" + "_".join(labels) + "_ORIGINAL_RETURNED", True
    return "NO_PROOF_Y2Q_DEFERRED_WORKER_OR_FLUSH_RETURN_ORIGINAL_RETURNED", False


def render(result, run):
    if result.get("schema") == "s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prepared = owner.engine.read_json(run / "prepared.json", "prepared")
        final = owner.engine.read_json(run / "final-health.json", "original return")
        proof = witness_result(run, prepared, final, transfer_proved=cstage.candidate_transfer_proved(run, prepared))
        print(json.dumps(dict(status="DEFERRED_WORKER_WITNESSES", **proof)), flush=True)
    return result


def _configure_runtime(module):
    parent._configure_runtime(module)


def bind():
    for name in ("ACTIVE", "SCRIPT", "PROFILE", "PREFIX", "HEADING", "RUN_ROOT", "EXP", "PAIR", "STAGE",
                 "QUAL", "BUILD", "READER", "FILTER", "WRITER", "TEST", "READER_TEST", "HEADER", "INIT_ELF",
                 "INITRD", "BOARD", "SOURCE_PINS", "STAGES", "FRAME_BYTES", "PAIR_SHA", "STAGE_SHA", "BUILD_SHA",
                 "READER_SHA", "FILTER_SHA", "WRITER_SHA", "READER_TEST_SHA", "CANDIDATE", "RAW", "QUAL_SHA",
                 "HEADER_SHA", "INIT_ELF_SHA", "INITRD_SHA", "BOARD_SHA", "pair", "calibrated_identity",
                 "review", "scope", "verdict", "render"):
        setattr(parent, name, globals()[name])
    INHERITED_BIND()
    stage._configure_runtime = _configure_runtime
    stage.APPROVAL = "S20PLUS-G986N-DEFERRED-WORKER-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-DEFERRED-WORKER-ARRIVAL:"


def main(argv):
    parent.ACTIVE = ACTIVE
    parent.bind = bind
    parent.main(argv)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as error:
        print(json.dumps({"status": "STOP_DEFERRED_WORKER", "failure": type(error).__name__,
                          "reason": str(error)[:210] if isinstance(error, (owner.Stop, ValueError)) else ""}))
        raise SystemExit(2)
