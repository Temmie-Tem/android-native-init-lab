#!/usr/bin/env python3
"""One attended post-wake GPIO trial and same-boot original Magisk readback."""
import hashlib
import json
import os
from pathlib import Path
import sys

import s20plus_g986n_mainline_stage_f1 as stage

SCRIPT = Path(__file__).resolve()
ACTIVE = True
PREVIOUS = SCRIPT.with_name("s20plus_g986n_tlmm_flush_f1.py")
PREVIOUS_SHA = "c64edf72cc4808308a8c4a4842c80585d0ee3e672ecb4e2910e9d53dd70ef36c"
prior = stage.load(PREVIOUS, "_s20_gpio_previous", PREVIOUS_SHA)
base, owner, parent, require = prior.base, prior.owner, prior.parent, prior.require
OLD_REVIEW, OLD_BIND, OLD_HEADING = prior.review, prior.bind, prior.HEADING
OLD_CAPTURE = stage.capture_options
PROFILE = "s20plus-g986n-tlmm-gpio-f1"
HEADING = "## S20+ post-wake GPIO registration attended trial\n"
PREFIX = "S20PLUS-G986N-TLMM-GPIO-F1-APPROVE:"
RUN_ROOT = prior.RUN_ROOT.with_name(PROFILE)
LAST = prior.RUN_ROOT / "run-1795854092652329526"
EXP = prior.EXP.with_name("s20plus-y2q-tlmm-gpio-h0-20261128")
SOURCE = parent.SOURCE
PAIR, STAGE = EXP / "packaged/pair.json", EXP / "candidate/stage.json"
QUAL = EXP / "physical-preparation/qualification.json"
BUILD, READER = SOURCE / "build_tlmm_gpio_h0.py", SOURCE / "gpio_return_reader.py"
FILTER, WRITER = SOURCE / "gpio-return-filter.awk", SOURCE / "tlmm-gpio-hooks.patch"
TEST = READER_TEST = parent.ROOT / "tests/test_s20plus_g986n_tlmm_gpio_f1.py"
HEADER, INIT_ELF = EXP / "candidate/build-id.h", EXP / "candidate/ramfs/init"
BOARD, INITRD = EXP / "candidate/handoff/bound-board.dtb", EXP / "candidate/handoff/bound-initrd.gz"
CANDIDATE = "70f61e5b5701b86bb3635ac31583708b1d70092c8824a0f0765f905134e5ef83"
RAW = "64a3db8af98aae6722f3f154f6cfc9396befd81e9e8073e45ea2bbcdf65f98f4"
# PINS
PAIR_SHA = "54d3a345aeb7dd51b6f41493b340bb01e9c9bb4ca6ce47ad0a4d56a4b2aed165"
STAGE_SHA = "9cd8acd0745e8e75950a4484a79ba6e9cdc1d8109737c2f7dd98b363db671402"
BUILD_SHA = "6874533e09fcf574770f737cd65d87e0683079ad94617a5e8d286df54ef1983d"
READER_SHA = "52b3807da86a64b578a545e3b993396318d281ec56e99a918e40354ff12b93ad"
FILTER_SHA = "ccab3129c9e90f407205e140f7c11e05abca13f696727975d5e05e81229923c0"
WRITER_SHA = "2188d5ae9856babcfd4a1fc2bef8dc4c89fd045ee191cfa38c00e3d8273a3d2c"
READER_TEST_SHA = "56b87a562e03f5dfc465f58ec076dd92911b229d6bcc72b5ad97ffeb595fcfe6"
HEADER_SHA = "0499d3a9b945f753515504affd856479f11c9d9e8213f61e67fef5fac72bf3e0"
INIT_ELF_SHA = "12f2447b44991361e09e521a2d65faa0cf06b061374080646a6a311a69d47fdd"
INITRD_SHA = "dfd2d4704272541766d53fc778853fe4db950a69cb486901eb8617864e663ddb"
BOARD_SHA = "541e220217f8bf0b65d4c18743a4ae6f8e7c35d6e5d9bc4497cda99655b433b8"
QUAL_SHA = "36f4d10cee8e53e81a3024a4f0d2a11d06e4e69df27d58d788c5383efaa068fc"
SOURCE_PINS = {
    LAST / "terminal.json": "4c4822ac265ab341b0ddf7e11b935d621652d66f055bc100255ad4052de1bedb",
    LAST / "final-health.json": "58c90e22a69b0d24dccdb25947bddc7c6c5e3f5975890364ee8c2174257ba7ef",
    LAST / "rollback-result.json": "cb900d394ea2b639ac9a2de6b34f22b24facec6fb1c5c2b26edf0cc6fff52bf6",
}


def calibrated_identity():
    records = {p.stem: json.loads(base.pinned(p, pin)) for p, pin in SOURCE_PINS.items()}
    final, terminal, rollback = (records[name] for name in ("final-health", "terminal", "rollback-result"))
    require(final["binding_sha256"] == terminal["binding_sha256"] == rollback["binding_sha256"]
            and final["version"] == terminal["version"] == rollback["version"] == "s20plus-g986n-tlmm-flush-f1"
            and terminal["verdict"] == "OBSERVED_TLMM_INITIAL_PDC_DEFER_ORIGINAL_RETURNED"
            and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
            and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
            and rollback["classification"] == "odin_transfer_completed" and rollback["replay_permitted"] is False
            and rollback["receipt"]["ap"]["sha256"] == parent.ORIGINAL
            and rollback["receipt"]["ap"]["path"] == str(parent.ORIGINAL_AP)
            and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
            and final["health"]["target"] == owner.TARGET, "previous original Magisk closure differs")
    return base.source_fields(final["health"])


def pair():
    data = json.loads(base.pinned(PAIR, PAIR_SHA))
    meta = json.loads(base.pinned(STAGE, STAGE_SHA))
    nonce = data["nonce"]
    probe = parent.inherited().profile.reader()
    require(data["device_commands"] == 0 and data["clear_frames_absent_from_both_boots"] is True
            and data["target"] == "SM-G986N/y2q/G986NKSS8IYC2" and meta["profile"] == "tlmm-gpio-h0"
            and meta["nonce"] == nonce and data["raw"] == meta["raw"] == RAW
            and data["offline_reader_sha256"] == prior.sha_file(SOURCE / "tlmm_gpio_h0.py")
            and meta["stages"] == {k: hashlib.sha256(v).hexdigest() for k,v in probe.frames(nonce).items()}
            and base.pinned(HEADER, HEADER_SHA) == f'#define Y2Q_BUILD_ID "{nonce}"\n'.encode()
            and meta["init_elf"] == INIT_ELF_SHA and meta["initrd"] == INITRD_SHA and meta["board"] == BOARD_SHA,
            "qualified GPIO build differs")
    for role, path, pin in (("candidate", PAIR.with_name("AP.tar.md5"), CANDIDATE),
                            ("rollback", parent.ORIGINAL_AP, parent.ORIGINAL)):
        part = data["archives"][role]
        require(part["ap"]["path"] == str(path) and part["ap"]["sha256"] == pin
                and part["only_member"]["name"] == "boot.img.lz4" and part["decoded_boot"]["size"] == 67108864,
                "boot AP identity differs")
    return {**data["archives"], "nonce": nonce}


def review():
    record = OLD_REVIEW()
    policy = base.view.read_file(owner.CONTRACT).decode()
    require(policy.count(OLD_HEADING) == 1, "prior TLMM scope missing")
    section = policy.split(OLD_HEADING)[1].split("\n## ", 1)[0]
    record["inherited_target_sections"][OLD_HEADING.strip()] = hashlib.sha256(section.encode()).hexdigest()
    record["frozen"][str(PREVIOUS)] = PREVIOUS_SHA
    for name in ("tlmm_gpio_h0.py", "tlmm_return_reader.py", "tlmm-return-filter.awk"):
        record["frozen"][str(SOURCE / name)] = prior.sha_file(SOURCE / name)
    record["schema"] = "s20plus_tlmm_gpio_attended_v1"
    return record


def capture_options(name):
    return {**OLD_CAPTURE(name), "stdout_maximum": stage.reader.MAX_STDOUT}


def derive(run, phase, health):
    # Preserve the original receipt and live-intent checks at the GPIO output bound.
    intent, raw, _ = stage.paths(phase)
    engine = owner.engine
    stored = engine.read_json(run / intent, "GPIO scan intent")
    require(stored == stage.make_intent(run, phase, health), "GPIO scan inputs changed")
    info = dict(phase=phase, intent_sha256=engine.digest(stored), boot_id_sha256=health["boot_id_sha256"])
    receipt = run / (raw + ".capture.json")
    if not os.path.lexists(receipt):
        return dict(**info, state="capture_cut")
    cap = engine.raw_capture
    handle = cap.load_handle(receipt)
    require(handle.name == raw and handle.stdout_path == run / (raw + ".stdout")
            and handle.stderr_path == run / (raw + ".stderr"), "GPIO scan stream identity differs")
    stdout = cap.read_stdout(handle, maximum=stage.reader.MAX_STDOUT)
    stderr = cap.read_stderr(handle, maximum=capture_options(raw)["stderr_maximum"])
    info["raw_receipt"] = owner.receipt(receipt)
    if type(handle.returncode) is not int or handle.timed_out or handle.output_exceeded or handle.producer_error_type:
        return dict(**info, state="read_failed")
    try:
        return dict(**info, **stage.reader.parse(handle.returncode, stdout, stderr))
    except ValueError:
        return dict(**info, state="read_failed")


def proof(run, transfer_proved):
    engine = owner.engine
    prep = engine.read_json(run / "prepared.json", "GPIO binding")
    final = engine.read_json(run / "final-health.json", "original health")
    log = stage.first_return(run, prep, final)
    require(log == engine.read_json(run / stage.paths("return")[2], "return evidence"), "GPIO receipt differs")
    complete = transfer_proved and log["state"] == "complete"
    data = {name: log[name] if complete else [] for name in
            ("initial", "worker", "flush", "initial_callback_rc", "worker_callback_rc")}
    data.update({name: complete and log[name] for name in
                 ("wait_completed", "flush_returned_true", "flush_returned_false")})
    usb = prior.prior.cstage.observe_acm_result(run, prep, transfer_proved=transfer_proved)
    return dict(state=log["state"], last_candidate_attempt="unknown", usb_pid1=usb, **data)


def verdict(classification, claim, rollback):
    require(claim == "NO_PROOF" and rollback is True, "unexpected transport claim or unproved recovery")
    run = stage.CURRENT_RUN.get() or Path(owner.runtime._require_live_transaction()["run_dir"])
    result = proof(run, classification == "odin_transfer_completed")
    labels = []
    events = set(result["initial"]) | set(result["worker"])
    if events.intersection(stage.reader.offline.EVENTS[16:]):
        labels.append("GPIO_REGISTRATION")
    elif events:
        labels.append("TLMM")
    if result["initial_callback_rc"] or result["worker_callback_rc"]:
        labels.append("CALLBACK_RETURN")
    if result["wait_completed"]:
        labels.append("WAIT_DONE")
    if result["flush_returned_true"]:
        labels.append("FLUSH_TRUE")
    if result["flush_returned_false"]:
        labels.append("FLUSH_FALSE")
    if result["flush"] and not labels:
        labels.append("KERNEL_PROGRESS")
    if result["usb_pid1"] == "pid1_exact":
        labels.append("ACM_PID1")
    if labels:
        return "OBSERVED_" + "_".join(labels) + "_ORIGINAL_RETURNED", True
    return "NO_PROOF_GPIO_ORIGINAL_RETURNED", False


def render(result, run):
    if result.get("schema") == "s20plus_g986n_b0_terminal_v1" and result["binding_sha256"] is not None:
        prep = owner.engine.read_json(run / "prepared.json", "binding")
        proved = prior.prior.cstage.candidate_transfer_proved(run, prep)
        print(json.dumps(dict(status="TLMM_GPIO_WITNESSES", **proof(run, proved))), flush=True)
    return result


def _configure_runtime(module):
    parent._configure_runtime(module)


def bind():
    for name in ("ACTIVE", "SCRIPT", "PROFILE", "PREFIX", "HEADING", "RUN_ROOT", "EXP", "PAIR", "STAGE", "QUAL",
                 "BUILD", "READER", "FILTER", "WRITER", "TEST", "READER_TEST", "HEADER", "INIT_ELF", "BOARD", "INITRD",
                 "PAIR_SHA", "STAGE_SHA", "BUILD_SHA", "READER_SHA", "FILTER_SHA", "WRITER_SHA", "READER_TEST_SHA",
                 "HEADER_SHA", "INIT_ELF_SHA", "BOARD_SHA", "INITRD_SHA", "CANDIDATE", "RAW", "QUAL_SHA", "SOURCE_PINS",
                 "pair", "calibrated_identity", "review", "verdict", "render"):
        setattr(prior, name, globals()[name])
    OLD_BIND()
    stage.capture_options, stage.derive = capture_options, derive
    stage._configure_runtime = _configure_runtime
    stage.APPROVAL = "S20PLUS-G986N-TLMM-GPIO-BOUND:"
    stage.CONFIRM = "S20PLUS-G986N-TLMM-GPIO-ARRIVAL:"


def main(argv):
    prior.prior.ACTIVE, prior.prior.bind = ACTIVE, bind
    prior.prior.main(argv)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(json.dumps(dict(status="STOP_TLMM_GPIO", error=type(exc).__name__,
                              reason=str(exc)[:180] if isinstance(exc, (owner.Stop, ValueError)) else "")))
        raise SystemExit(2)
