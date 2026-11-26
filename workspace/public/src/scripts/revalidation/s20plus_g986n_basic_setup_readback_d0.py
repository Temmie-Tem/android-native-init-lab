#!/usr/bin/env python3
"""One digest-only basic-setup read on the current restored S20+ boot."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import types

import s20plus_g986n_twrp_observe_source_view_v1 as files

SCRIPT = Path(__file__).resolve()
ROOT, PRIVATE = files.ROOT, files.PRIVATE
RUNS = PRIVATE / "runs"
PARENT = RUNS / "s20plus-g986n-basic-setup-readback-d0"
F1_PROFILE = "s20plus-g986n-basic-setup-f1"
RUN = RUNS / F1_PROFILE / "run-1795726991377518240"
TICKET = RUN.parent / "ticket-1795726991377518240"
EXP = PRIVATE / "analysis/s20plus-y2q-basic-setup-20261127"
PAIR, STAGE = EXP / "packaged/pair.json", EXP / "candidate/stage.json"
SECTION = "## S20+ current restored boot basic-setup marker readback D0\n"
F1_SECTION = "## S20+ y2q basic setup trial under one attended approval\n"
SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
READER = SOURCE / "basic_setup_stage_reader.py"
FILTER = SOURCE / "basic-setup-stage-filter.awk"
BASE_READER = SOURCE / "mainline-handoff/return_stage.py"
BASE_FILTER = SOURCE / "mainline-handoff/return-stage.awk"
TEST = ROOT / "tests/test_s20plus_g986n_basic_setup_readback_d0.py"
STOCK = SCRIPT.with_name("s20plus_g986n_stock_direct_readback_d0.py")
F1 = SCRIPT.with_name("s20plus_g986n_basic_setup_f1.py")
SCHEMA = "s20plus_g986n_basic_setup_readback_d0_v1"
SCOPE = "CURRENT_RESTORED_BOOT_ONLY"
STAGES = ("dt_ready", "basic_enter", "basic_return")
COUNTS = (*(k + "_count" for k in STAGES), "dt_enter_pair_count", "enter_return_pair_count", "triple_count")
IDENTITY = ("serial_sha256", "topology_sha256", "boot_id_sha256")
PINS = {
    RUN / "terminal.json": "9e9518abbd6f3d06e3c5e15a5103adff832c5546c22ab7a88df21a3c211cd90e",
    RUN / "prepared.json": "e344136c2c8bed9c02c5d9b082f4e7b8eeb7625093293a025a0d5453399f8b0b",
    RUN / "final-health.json": "b16dd3ec3105905362aca215d5f788b8d28fff018f7e2ebd8506c66ef007bab7",
    RUN / "mainline-return-evidence.json": "5535e5abe1904924cf8022e4effc747731c51c0adfb854ce9a0d2b13bba3c14a",
    RUN / "mainline-baseline-intent.json": "0286908a378e8922f5af284c138ea3403b183cb4336866951c5d512f704408ee",
    RUN / "mainline-baseline-evidence.json": "383dea678fd1bee5222abba21022d68460a96d9cf93805ab27aca1a0b26da3ed",
    RUN / "candidate-result.json": "6e37bbd1fdc37d3fda51435a40d13539680a244474ea3843cfd1056ee4e1bdda",
    RUN / "rollback-result.json": "394c94afe21dd4631e8d1733242329c2437af0eff0708362931a02b2a017ffc9",
    TICKET / "prepared.json": "a3ebfc6d34c510a41afda1f997ee16d1fe9ee2bf8ec6d9af3111786c71020418",
    TICKET / "accepted.json": "95c01848f369e0149afc067e5a909cbef1d7a72de36178e18f516b8e4542f835",
    PAIR: "2bdc73a5455c85b4df139bf343361307cf1932615ec7f3285846eb10741413d4",
    STAGE: "37d83a435c590ac9e01e29a6a070d649fab7900b1be56ff40c08f30b9a16d67d",
}
HELPERS = {
    STOCK: "cf0c1b7e38c01fae1c1ae57cc4389c0ea3709ad5193135a0046cda8f14a79cd0",
    F1: "153435d8424664c3a66d3e4dd6dbff1aa9e27bfa0d1192846daeba821cc50583",
    READER: "16e39156837f91bc9c316a23c96601c5471873edded440945830a2f554aa383f",
    FILTER: "9bfa644a2cd04105a39d7c5b3053acf529eb1fd0c4a3fec11d948f1558e2f9fd",
    BASE_READER: "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5",
    BASE_FILTER: "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def checked(path, digest):
    raw = files.read_file(path)
    require(sha(raw) == digest, "changed input " + path.name)
    return raw


def load(path):
    module = types.ModuleType("_basic_setup_d0_" + path.stem)
    module.__file__ = str(path)
    exec(compile(checked(path, HELPERS[path]), str(path), "exec"), module.__dict__)
    return module


stock = load(STOCK)
stock.PARENT = PARENT
io, health, registry = stock.io, stock.health, stock.registry
reader = load(READER)


def closure():
    saved = {p: json.loads(checked(p, pin)) for p, pin in PINS.items()}
    prepared, final, terminal = (saved[RUN / name] for name in ("prepared.json", "final-health.json", "terminal.json"))
    restored = final["health"]
    before = prepared["binding"]["preflight"]
    key = prepared["binding_sha256"]
    grant = PINS[TICKET / "prepared.json"]
    outer, accepted = saved[TICKET / "prepared.json"], saved[TICKET / "accepted.json"]
    baseline, intent = (saved[RUN / name] for name in ("mainline-baseline-evidence.json", "mainline-baseline-intent.json"))
    require(
        outer["profile"] == prepared["version"] == final["version"] == terminal["version"] == F1_PROFILE
        and outer["run"] == prepared["binding"]["run_dir"] == str(RUN)
        and accepted["grant_sha256"] == intent["grant_sha256"] == grant
        and all(outer["health"][k] == before[k] for k in IDENTITY)
        and all(restored[k] == before[k] for k in IDENTITY[:2])
        and restored["target"] == before["target"] == dict(model=health.EXPECTED_MODEL, device=health.EXPECTED_DEVICE,
            product=health.EXPECTED_PRODUCT, incremental=health.EXPECTED_INCREMENTAL)
        and restored["boot_id_sha256"] != before["boot_id_sha256"] == baseline["boot_id_sha256"]
        and baseline["phase"] == intent["phase"] == "baseline"
        and baseline["state"] == "no_record" and all(baseline[k] == 0 for k in COUNTS)
        and baseline["intent_sha256"] == PINS[RUN / "mainline-baseline-intent.json"]
        and intent["pair_sha256"] == PINS[PAIR],
        "closed basic-setup source binding differs",
    )
    require(
        final["binding_sha256"] == terminal["binding_sha256"] == key
        and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
        and terminal["verdict"] == "NO_PROOF_Y2Q_BASIC_SETUP_ORIGINAL_MAGISK_RETURNED"
        and terminal["experiment_pass"] is False and terminal["rollback_transfer_completed"] is True
        and terminal["candidate_attempts"] == terminal["rollback_attempts"] == 1
        and terminal["candidate_replay_permitted"] is terminal["rollback_replay_permitted"] is False
        and saved[RUN / "mainline-return-evidence.json"] == dict(
            phase="return", state="observation_gap", binding_sha256=key,
            final_health_sha256=PINS[RUN / "final-health.json"])
        and not any(os.path.lexists(path) for path in (TICKET / "first-observed-return.json",
                RUN / "mainline-return-intent.json", RUN / "mainline-return-scan.capture.json")),
        "proved original restoration or first-return gap differs",
    )
    pair, meta = saved[PAIR], saved[STAGE]
    for role, field in (("candidate", "candidate"), ("rollback", "original")):
        transfer = saved[RUN / (role + "-result.json")]
        archive = pair["archives"][role]
        require(transfer["version"] == F1_PROFILE and transfer["binding_sha256"] == key
                and transfer["kind"] == role and transfer["classification"] == "odin_transfer_completed"
                and transfer["replay_permitted"] is False and transfer["host_process_quiescence_proved"] is True
                and transfer["receipt"]["ap"] == archive["ap"]
                and archive["ap"]["sha256"] == outer[field]
                and archive["only_member"]["name"] == "boot.img.lz4", "closed AP chain differs")
    for path in (FILTER, BASE_READER, BASE_FILTER):
        checked(path, HELPERS[path])
    nonce = pair["nonce"]
    frames = reader.frames(nonce)
    require(pair["profile"] == meta["profile"] == F1_PROFILE and pair["device_commands"] == 0
            and pair["raw"] == meta["raw"] and nonce == meta["nonce"]
            and tuple(frames) == STAGES and all(len(frame) == 80 for frame in frames.values())
            and meta["stages"] == {k: sha(v) for k, v in frames.items()}
            and pair["return_template"] == sha(reader.shell(nonce, "0" * 64).encode())
            and intent["script_sha256"] == sha(reader.shell(nonce, before["boot_id_sha256"]).encode()),
            "exact three-marker reducer binding differs")
    return restored, reader.shell(nonce, restored["boot_id_sha256"])


def subject(script):
    rules = files.read_file(ROOT / "AGENTS.md")
    details = sha(files.read_file(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"))
    require(re.findall(rb"The incorporated details have SHA-256:\s*`([a-f0-9]{64})`", rules) == [details.encode()],
            "common detail pin differs")
    policy = files.read_file(io.TARGET_CONTRACT).decode()
    authority = {}
    for heading in (SECTION, F1_SECTION, stock.SECTION):
        require(policy.count(heading) == 1, "selected target scope differs")
        section = heading + policy.split(heading, 1)[1].split("\n## ", 1)[0]
        authority[heading.strip()] = sha(section.encode())
    sources = {**stock.HELPERS, **HELPERS}
    return dict(schema=SCHEMA, scope=SCOPE, owner=sha(files.read_file(SCRIPT)), root=sha(rules), details=details,
                authority=authority, tiers=sha(files.read_file(ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md")),
                files=sha(files.read_file(files.SCRIPT)), health=sha(files.read_file(io.health_path)),
                inventory=sha(checked(SCRIPT.with_name(health.INVENTORY_HELPER_NAME), health.INVENTORY_HELPER_SHA256)),
                helpers={str(p.relative_to(ROOT)): sha(checked(p, pin)) for p, pin in sources.items()},
                retained={str(p.relative_to(ROOT)): pin for p, pin in PINS.items()},
                tests=sha(files.read_file(TEST)), shell=sha(script.encode()))


def observe(identity, expected, script):
    stock.admit(identity)
    parent = PARENT / "observation"
    if os.path.lexists(parent):
        raise FileExistsError("current restored boot observation already reserved")
    adb = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    before = stock.bracket(adb["path"], expected)
    require(closure() == (expected, script) and subject(script) == identity, "inputs changed")
    stock.admit(identity)
    require(health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) == adb, "ADB changed")
    # The synced exclusive reservation consumes this one attempt even if
    # the process stops before it can publish the complete dispatch intent.
    parent.mkdir(mode=0o700)
    health._fsync_directory(PARENT)
    fd = os.open(parent, os.O_DIRECTORY | os.O_NOFOLLOW)
    with health.EvidenceOwner(parent, fd, health._directory_identity(os.fstat(fd))) as evidence:
        try:
            binding = {key: expected[key] for key in IDENTITY}
            evidence.publish_json("intent.json", dict(identity=identity, binding=binding))
            command = [adb["path"], "-s", before[0], "shell", "-T", "su", "-c", shlex.quote(script)]
            reason, rc, out, err = io.root_capture(command, 120, 96)
            io.save_root_receipt(evidence, reason, rc, out, err)
            after = stock.bracket(adb["path"], expected)
            require(before == after and reason == "completed", "incomplete current restored boot bracket")
            facts = reader.parse(rc, out, err)
            stock.admit(identity)
            result = dict(schema=SCHEMA, scope=SCOPE, facts=facts, binding=binding,
                          shell_sha256=identity["shell"], terminal_sha256=PINS[RUN / "terminal.json"],
                          first_return_attributed=False, operator_reported_intervening_twrp=True)
            evidence.publish_json("result.json", result)
            print(json.dumps({"scope": SCOPE, "facts": facts}, sort_keys=True))
        except Exception as exc:
            evidence.publish_json("failure.json", dict(reason_sha256=sha(str(exc).encode()), error=type(exc).__name__))
            raise


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review-input", action="store_true")
    mode.add_argument("--connected", action="store_true")
    args = parser.parse_args()
    expected, script = closure()
    identity = subject(script)
    if args.review_input:
        print(json.dumps(identity, sort_keys=True))
        return
    health._ALLOWED_EVIDENCE_NAMES |= {"intent.json"}
    health._EVIDENCE_MAXIMUMS["intent.json"] = 16384
    with registry.target_session_lease(ROOT, research_read_only=True):
        observe(identity, expected, script)


if __name__ == "__main__":
    main()
