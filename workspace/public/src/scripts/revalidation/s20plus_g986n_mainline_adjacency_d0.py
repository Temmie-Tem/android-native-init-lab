#!/usr/bin/env python3
"""Count exact mainline marker adjacency in one already recorded original boot."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import types

import s20plus_g986n_twrp_observe_source_view_v1 as files

SCRIPT = Path(__file__).resolve()
ROOT = files.ROOT
RUNS = files.PRIVATE / "runs"
PARENT = RUNS / "s20plus-g986n-mainline-adjacency-d0"
OLD = RUNS / "s20plus-g986n-mainline-list-f1"
RUN = OLD / "run-1795715419450778655"
TICKET = OLD / "ticket-1795715419450778655"
BUILD = files.PRIVATE / "analysis/s20plus-y2q-mainline-list-20261127"
PAIR = BUILD / "packaged/pair.json"
STAGE = BUILD / "candidate/stage.json"
CANDIDATE = "424ace70dcf22e5b2ed2b5b34636537f42acda19c914454c773455880ed44cdf"
ORIGINAL = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
CAPACITY = 2097136
OLDER_COUNTS = (CAPACITY, 4, 4)
SCHEMA = "s20plus_g986n_mainline_adjacency_d0_v1"
HEADING = "## S20+ first-return mainline marker adjacency D0\n"
BASE_HEADING = "## S20+ first-return stock-direct marker readback D0\n"
TRIAL_HEADING = "## S20+ mainline compatible-list early pair under one attended approval\n"

SUPPORT = SCRIPT.with_name("s20plus_g986n_stock_direct_readback_d0.py")
RAW_CAPTURE = SCRIPT.with_name("device_action_raw_capture_v1.py")
HELPERS = {
    SUPPORT: "cf0c1b7e38c01fae1c1ae57cc4389c0ea3709ad5193135a0046cda8f14a79cd0",
    RAW_CAPTURE: "5a177d6bbe08cdd2c66f867c67a2a4093589b303d4b5b07f1e33d484f17498dc",
}
PINS = {
    RUN / "terminal.json": "2a73e13a634dcf194aef08fbee27891c4f87a546c8142c0b57a068a8885f3a71",
    RUN / "prepared.json": "8604f02108e613b365c37243b0fd4246716e77a195eca7e19e2f4d932721de34",
    RUN / "final-health.json": "ce47f5c81be38f9833752077b74341706c4b14dd189401b83c5cb0447f971747",
    RUN / "mainline-baseline-intent.json": "75b6d3d2392d9ebccda6372a9071de5d6e37cedddf0cec60897bf09fcdfeb5c5",
    RUN / "mainline-baseline-evidence.json": "0c4ec04a388ae080696862f15f3eec582eea38a765de55bcba0ad7ee71de21df",
    RUN / "mainline-return-intent.json": "2d38c20e5e939ae2a19490b3593699eaaf4af1279c325799b63a2125b5547733",
    RUN / "mainline-return-evidence.json": "164e097d071535074dec7b0af1e6190d963769b6e1e8f72a53dc3ec03b14e46c",
    RUN / "mainline-return-scan.capture.json": "4df05f29a3188fec8601d8c8a2b5e0530352fa8f267fc1dd39cdd791e08bc54f",
    RUN / "candidate-result.json": "c36089719720cbc9b4c44674d38d9ead51713b3bccbdf7c98bc8fdefe4162b13",
    RUN / "rollback-result.json": "a257d869b0369534e16e2151857a473f3b487f60c977aa3bcea15f6f741d61fe",
    RUN / "rollback-intent.json": "220439bdd2e44485fc09667ebb9e73eb5d11e9dfd2b9d3bccfedbdb289791269",
    RUN / "physical-rollback-intent.json": "3a98efee49f238dc9e984b528f61e81f27b49700d62aae182f3d26aa6e521c63",
    RUN / "physical-confirmation-intent.json": "57b39953c38f463d6821be07ba564cc467be047c1d297f33197f8df14856f6bc",
    RUN / "physical-observation-intent.json": "b76e05e75ae8828996f827674704097c0d45056561372a49a5107080ff21cca7",
    RUN / "physical-rollback-arrival.json": "c2823b1fcdb7603fb938d608f1211b4041fabbdd9fe516953cb7e49f404c3f65",
    TICKET / "prepared.json": "e4ea5e9aceadf7ad0964a5ccedb0f267f9f600003827c53285c30d2903620e3e",
    TICKET / "accepted.json": "304089b762780d303456a70b58be0817dfe7acfc7763fc500844813b05d836ba",
    TICKET / "first-observed-return.json": "c5c0bdd94a5246be9ea53362058ac95d537ac08c81d72231eed6661313ecdd3d",
    TICKET / "physical-cue.json": "28050992170e7bf1fa8b2b135f01d2720f9e03c7da864182ad4e174e88b508cf",
    OLD / "consumed-candidates" / (CANDIDATE + ".json"): "52b61358511ff8b7941e2fa6112457bab1f77ca2adb636d73a1a241205f55bbc",
    PAIR: "3dc0b14204b28fbd1c87a49ee81bfff7141f7a1736353366ca6bfce3097b910d",
    STAGE: "1a4eb13794a5f2ee16835bba2f39664445ae75fc3923ab4258a37be821035ccb",
}


def sha(raw):
    return files.file_receipt(raw)["sha256"]


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def checked(path, expected, *, mode=None):
    raw = files.read_file(path, mode=mode)
    require(sha(raw) == expected, "changed input " + path.name)
    return raw


def load(path):
    name = "_s20_adjacency_" + path.stem
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(checked(path, HELPERS[path]), str(path), "exec"), module.__dict__)
    return module


support = load(SUPPORT)
capture = load(RAW_CAPTURE)
io, health, registry, reader = support.io, support.health, support.registry, support.reader


def replace_once(source, old, new):
    require(source.count(old) == 1, "reviewed reducer template changed")
    return source.replace(old, new, 1)


def reducer():
    """Keep the existing two exact scans and add an on-device bounded join."""
    before = checked(reader.FILTER, support.HELPERS[reader.FILTER]).decode("ascii")
    after = replace_once(before, "which,    pos,step)", "which,    pos,step,at)")
    after = replace_once(
        after,
        "            start[which] = previous - length(tail)/2 + (pos-1)/2",
        """            at = previous - length(tail)/2 + (pos-1)/2
            # A second-frame hit can use only the first-frame start 128 bytes
            # earlier. Store an exact offset plus one in each bounded slot.
            if (which == 1) first_slot[at % 256] = at + 1
            else if (at >= 128 && first_slot[(at-128) % 256] == at-127) adjacent++""",
    )
    after = replace_once(after, "    paired = hits[1] == 1 && hits[2] == 1 && start[2]-start[1] == 128\n", "")
    after = replace_once(after, "total,hits[1],hits[2],paired", "total,hits[1],hits[2],adjacent")
    return before, after


def scan_command(nonce, boot_digest):
    before, after = reducer()
    script = reader.shell(nonce, boot_digest, reader.EARLY_STAGES)
    script = replace_once(script, shlex.quote(before), shlex.quote(after))
    return replace_once(script, 'result="y2q_early_v2=', 'result="y2q_early_adj_v1=')


def previous_scan(saved):
    path = RUN / "mainline-return-scan.capture.json"
    handle = capture.load_handle(path)
    require(handle.returncode == 0 and not handle.timed_out and not handle.output_exceeded
            and handle.producer_error_type is None and handle.name == "mainline-return-scan"
            and handle.stdout_path == RUN / "mainline-return-scan.stdout"
            and handle.stderr_path == RUN / "mainline-return-scan.stderr"
            and saved["raw_receipt"] == files.file_receipt(checked(path, PINS[path], mode=0o400)),
            "retained capture not bound")
    output = capture.read_stdout(handle, maximum=96)
    errors = capture.read_stderr(handle, maximum=1024)
    require(output == b"y2q_early_v2=2097136,4,4,0\n" and not errors, "retained aggregate differs")
    parsed = reader.parse(0, output, errors, reader.EARLY_STAGES)
    require(all(saved[key] == value for key, value in parsed.items()), "retained interpretation differs")


def same_session(left, right):
    return (all(left[key] == right[key] for key in ("device", "endpoint_sha256", "topology_sha256", "usb"))
            and left["endpoint_identity"][:3] == right["endpoint_identity"][:3])


def closure():
    # These paths are fixed and never written by this profile.
    records = {p: json.loads(checked(p, pin, mode=0o400 if p.is_relative_to(OLD) else None))
               for p, pin in PINS.items()}

    def record(name):
        return records[RUN / (name + ".json")]

    final, terminal = record("final-health"), record("terminal")
    prepared, binding = record("prepared"), record("prepared")["binding"]
    first = records[TICKET / "first-observed-return.json"]
    grant, accepted = records[TICKET / "prepared.json"], records[TICKET / "accepted.json"]
    outer, inner = PINS[TICKET / "prepared.json"], prepared["binding_sha256"]
    restored, source = final["health"], binding["preflight"]
    require(outer == first["binding_sha256"] == accepted["grant_sha256"] and outer != inner
            and grant["run"] == binding["run_dir"] == str(RUN)
            and grant["candidate"] == CANDIDATE and grant["original"] == ORIGINAL
            and first["boot_sha256"] == restored["boot_id_sha256"] != source["boot_id_sha256"]
            and all(restored[k] == source[k] == grant["health"][k]
                    for k in ("target", "serial_sha256", "topology_sha256"))
            and source["boot_id_sha256"] == grant["health"]["boot_id_sha256"],
            "retained source/return identity differs")
    require(inner == terminal["binding_sha256"] == final["binding_sha256"]
            and terminal["verdict"] == "NO_PROOF_Y2Q_EARLY_PAIR_RESIDENT_HEALTH_OBSERVED"
            and terminal["experiment_pass"] is False
            and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
            and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
            and terminal["rollback_transfer_completed"] is final["rollback_transfer_completed"] is True
            and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is True,
            "retained outcome differs")
    claim = records[OLD / "consumed-candidates" / (CANDIDATE + ".json")]
    require(claim["binding_sha256"] == inner and claim["run_dir"] == str(RUN)
            and claim["candidate_ap_sha256"] == CANDIDATE and claim["candidate_replay_permitted"] is False,
            "retained consumption differs")
    arm, confirmation, observation, arrival, rollback = (
        record(name) for name in ("physical-rollback-intent", "physical-confirmation-intent",
                                  "physical-observation-intent", "physical-rollback-arrival", "rollback-intent")
    )
    require(all(item["binding_sha256"] == inner for item in (arm, confirmation, observation, arrival, rollback))
            and arm["branch"] == "attended-entry-required" and arm["baseline"]["endpoint_count"] == 0
            and records[TICKET / "physical-cue.json"] == {"run": str(RUN), "expires": arm["expires_unix"],
                                                        "arm_sha256": PINS[RUN / "physical-rollback-intent.json"]}
            and confirmation["arm_sha256"] == PINS[RUN / "physical-rollback-intent.json"]
            and arm["baseline_sha256"] == observation["baseline_sha256"] == arrival["baseline_sha256"]
            and arrival["branch"] == "attended-entry"
            and rollback["ap_sha256"] == ORIGINAL and rollback["no_replay"] is True
            and same_session(arrival["endpoint"], rollback["endpoint"])
            and arrival["endpoint"]["topology_sha256"] == source["topology_sha256"],
            "retained physical recovery differs")
    pair, stage = records[PAIR], records[STAGE]
    for role, pin in (("candidate", CANDIDATE), ("rollback", ORIGINAL)):
        result = record(role + "-result")
        ap = pair["archives"][role]["ap"]
        require(result["binding_sha256"] == inner and result["classification"] == "odin_transfer_completed"
                and result["receipt"]["ap"] == ap and ap["sha256"] == pin, "retained transfer differs")

    baseline, baseline_intent = record("mainline-baseline-evidence"), record("mainline-baseline-intent")
    saved, intent = record("mainline-return-evidence"), record("mainline-return-intent")
    require(baseline["intent_sha256"] == PINS[RUN / "mainline-baseline-intent.json"]
            and baseline["state"] == "no_record" and baseline["size"] == CAPACITY
            and baseline["boot_id_sha256"] == source["boot_id_sha256"]
            and baseline_intent["grant_sha256"] == intent["grant_sha256"] == outer
            and baseline_intent["pair_sha256"] == intent["pair_sha256"] == PINS[PAIR]
            and saved["intent_sha256"] == PINS[RUN / "mainline-return-intent.json"]
            and saved["boot_id_sha256"] == restored["boot_id_sha256"]
            and intent["binding_sha256"] == inner and intent["first_observed_return"] == first
            and intent["health"] == restored and intent["final_health_sha256"] == PINS[RUN / "final-health.json"]
            and intent["physical_confirmation"] == "physical-confirmation-intent.json"
            and intent["physical_confirmation_sha256"] == PINS[RUN / "physical-confirmation-intent.json"]
            and intent["candidate_sha256"] == PINS[RUN / "candidate-result.json"]
            and intent["rollback_sha256"] == PINS[RUN / "rollback-result.json"], "retained scan binding differs")
    nonce = pair["nonce"]
    frames = reader.frames(nonce, reader.EARLY_STAGES)
    require(pair["kind"] == "HOST_ONLY_S20PLUS_Y2Q_EARLY_AP_PAIR" and pair["device_commands"] == 0
            and pair["target"] == "SM-G986N/y2q/G986NKSS8IYC2" and pair["raw"] == stage["raw"]
            and stage["kind"] == "HOST_ONLY_Y2Q_EARLY_PAIR" and stage["nonce"] == nonce
            and {name: sha(frame) for name, frame in frames.items()} == stage["stages"]
            and intent["script_sha256"] == sha(reader.shell(nonce, restored["boot_id_sha256"], reader.EARLY_STAGES).encode()),
            "retained witness identity differs")
    previous_scan(saved)
    return restored, scan_command(nonce, restored["boot_id_sha256"])


def subject(script):
    policy = files.read_file(io.TARGET_CONTRACT).decode()

    def section(heading):
        require(policy.count(heading) == 1, "missing selected target scope")
        return sha((heading + policy.split(heading, 1)[1].split("\n## ", 1)[0]).encode())

    rules = files.read_file(ROOT / "AGENTS.md")
    details = sha(files.read_file(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"))
    require(re.findall(rb"The incorporated details have SHA-256:\s*`([a-f0-9]{64})`", rules) == [details.encode()],
            "common details pin differs")
    return dict(schema=SCHEMA, owner=sha(files.read_file(SCRIPT)), target=section(HEADING),
                inherited=[section(BASE_HEADING), section(TRIAL_HEADING)], common=sha(rules), details=details,
                tiers=sha(files.read_file(ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md")),
                tests=sha(files.read_file(ROOT / "tests/test_s20plus_g986n_mainline_adjacency_d0.py")),
                helpers={p.name: sha(checked(p, pin)) for p, pin in (HELPERS | support.HELPERS).items()},
                files=sha(files.read_file(files.SCRIPT)), health=sha(files.read_file(io.health_path)),
                inventory=sha(checked(SCRIPT.with_name(health.INVENTORY_HELPER_NAME), health.INVENTORY_HELPER_SHA256)),
                retained={str(p.relative_to(ROOT)): pin for p, pin in PINS.items()}, script=sha(script.encode()))


def admit(identity):
    require(ROOT == io.CANONICAL and PARENT.resolve(strict=True) == PARENT and PARENT.is_dir(), "evidence root differs")
    parent = PARENT.stat()
    activation = PARENT / "activation.json"
    require(parent.st_uid == os.geteuid() and stat.S_IMODE(parent.st_mode) == 0o700
            and activation.stat().st_uid == os.geteuid(), "private owner differs")
    require(files.read_file(activation, mode=0o400) == health._json_bytes({"identity": identity, "review": files.REVIEW_PASS}),
            "independent activation differs")
    registry.require_no_f1_owner(ROOT)
    require(not any(os.path.lexists(path) for path in (files.RUN_ROOT / "active-action.json", files.CAMPAIGN_GUARD,
                                                      ROOT / registry.RESEARCH_PENDING)), "pending owner")


def parse(rc, out, err):
    require(rc == 0 and not err and len(out) <= 96, "incomplete adjacency output")
    if out in (b"y2q_log_missing\n", b"y2q_log_unreadable\n"):
        return {"state": out.decode().strip().removeprefix("y2q_log_")}
    number = rb"(0|[1-9][0-9]{0,6})"
    match = re.fullmatch(rb"y2q_early_adj_v1=" + b",".join([number] * 4) + rb"\n", out)
    require(match is not None, "invalid adjacency framing")
    size, prebranch, primary, pairs = map(int, match.groups())
    require(size <= CAPACITY and 128 * (prebranch + primary) <= size and pairs <= min(prebranch, primary),
            "inconsistent adjacency counts")
    return dict(state="complete", size=size, prebranch_count=prebranch, primary_entry_count=primary,
                adjacent_pair_count=pairs)


def observe(identity, expected, script, evidence):
    tool = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    before = support.bracket(tool["path"], expected)
    require(closure() == (expected, script) and subject(script) == identity, "observation inputs changed")
    admit(identity)
    require(health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) == tool, "ADB changed")
    evidence.publish_json("intent.json", {"identity": identity, "boot_id_sha256": expected["boot_id_sha256"]})
    argv = [tool["path"], "-s", before[0], "shell", "-T", "su", "-c", shlex.quote(script)]
    reason, rc, out, err = io.root_capture(argv, 120, 96)
    io.save_root_receipt(evidence, reason, rc, out, err)
    after = support.bracket(tool["path"], expected)
    require(before == after and reason == "completed", "incomplete same-boot bracket")
    facts = parse(rc, out, err)
    if facts["state"] == "complete":
        require(tuple(facts[key] for key in ("size", "prebranch_count", "primary_entry_count")) == OLDER_COUNTS,
                "snapshot length or stage totals changed")
    admit(identity)
    evidence.publish_json("result.json", dict(schema=SCHEMA, facts=facts, identity=identity,
                          binding={k: expected[k] for k in ("serial_sha256", "topology_sha256", "boot_id_sha256")}))
    return facts


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review-input", action="store_true")
    modes.add_argument("--connected", action="store_true")
    args = parser.parse_args()
    expected, script = closure()
    identity = subject(script)
    if args.review_input:
        print(json.dumps(identity, sort_keys=True))
        return 0
    health._ALLOWED_EVIDENCE_NAMES |= {"intent.json"}
    health._EVIDENCE_MAXIMUMS["intent.json"] = 16384
    with registry.target_session_lease(ROOT, research_read_only=True):
        admit(identity)
        path = PARENT / "observation"
        path.mkdir(mode=0o700)
        health._fsync_directory(PARENT)
        fd = os.open(path, os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with health.EvidenceOwner(path, fd, health._directory_identity(os.fstat(fd))) as evidence:
            try:
                facts = observe(identity, expected, script, evidence)
            except Exception as error:
                evidence.publish_json("failure.json", dict(schema=SCHEMA, error=type(error).__name__,
                                                           reason_sha256=sha(str(error).encode())))
                print("OBSERVATION_CLOSED", path)
                return 2
        print(json.dumps(dict(facts=facts, evidence=str(path)), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
