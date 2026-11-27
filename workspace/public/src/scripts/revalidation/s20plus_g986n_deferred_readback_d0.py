#!/usr/bin/env python3
"""One digest-only deferred-worker read on the current restored S20+ boot."""

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
PARENT = RUNS / "s20plus-g986n-deferred-worker-readback-d0"
F1_PROFILE = "s20plus-g986n-deferred-worker-f1"
RUN = RUNS / F1_PROFILE / "run-1795780019923307510"
TICKET = RUN.parent / "ticket-1795780019923307510"
EXP = PRIVATE / "analysis/s20plus-y2q-deferred-worker-f1"
PAIR, STAGE = EXP / "packaged/pair.json", EXP / "candidate/stage.json"
SECTION = "## S20+ current restored boot deferred-worker marker readback D0\n"
F1_SECTION = "## S20+ y2q deferred worker and first flush under one attended approval\n"
SOURCE = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0"
READER = SOURCE / "deferred_reader.py"
FILTER = SOURCE / "deferred-filter.awk"
BASE_READER = SOURCE / "mainline-handoff/return_stage.py"
BASE_FILTER = SOURCE / "mainline-handoff/return-stage.awk"
TEST = ROOT / "tests/test_s20plus_g986n_deferred_readback_d0.py"
STOCK = SCRIPT.with_name("s20plus_g986n_stock_direct_readback_d0.py")
F1 = SCRIPT.with_name("s20plus_g986n_deferred_worker_f1.py")
SCHEMA = "s20plus_g986n_deferred_worker_readback_d0_v1"
SCOPE = "CURRENT_RESTORED_BOOT_ONLY"
IDENTITY = ("serial_sha256", "topology_sha256", "boot_id_sha256")
QUAL = EXP / "qualification.json"
PINS = {
    RUN / "terminal.json": "5028689ab1c4201e2e9ebee8dafb5dff68e2d5340c788f681f1d84f76bd4468b",
    RUN / "prepared.json": "4bbff07ace23be2ded3f235a85bc017b0407c7f11a0b4fe6409fac2ffc94ddb3",
    RUN / "final-health.json": "8251c1b3c2bb9159a0a5f75fadbb8cfaecfbb9716456afc06a4f6b9ac4fba6f1",
    RUN / "mainline-return-evidence.json": "e7c0e87b17ca97378fffeb0c881b09c412fd3e5db3e52f2a69042c745dd66105",
    RUN / "mainline-baseline-intent.json": "f7bd236a68bf0b8b498c25642bc0992e0d237342cd7d5974cb189b234b7d2bb1",
    RUN / "mainline-baseline-evidence.json": "5ab4e87ef3d3aadeb407392b7b40f55430c4d8f8d075522824e573bcee6095c8",
    RUN / "candidate-result.json": "86b5b76d81ed1f44140d709154d912d6b30a2d54bbdeeb82f4e23dd4472eafe7",
    RUN / "rollback-result.json": "5e771347c869cf617aaae7d8bc298e3f1a5e65baba09987a13d9dd736d8eb508",
    TICKET / "prepared.json": "46937d3fe89eeb0631fbba417dc0e9a5b39f6ad9d3c7a1991efa6f31a8c968f2",
    TICKET / "accepted.json": "a9855a4929bd674f81344e5d483e278eaff56b5f302990865b83fdd65eb5cb6d",
    PAIR: "4e4943e84437655aa4a9ffcdd640297fe46f3ec9bb6e6d54c340642b6cff476f",
    STAGE: "77e755e4ecafdd6bb582b576b3b890aba8a9c9e6c5e4bc647e8eb6e114ba1205",
    QUAL: "d5bed095f1634d5970f0f30a5e57032117a1871e8a140c2417e3807706743566",
}
HELPERS = {
    STOCK: "cf0c1b7e38c01fae1c1ae57cc4389c0ea3709ad5193135a0046cda8f14a79cd0",
    F1: "29745e2a4821ecf9c0c64e91ef684f118db7db7d300371ed4ef0027dca67362b",
    READER: "3ae47fda36ff1c32545d697b8c370563c63bf1d5fbc3e19e23c74016a0fb3153",
    FILTER: "3f8640ede2a88f9f4d61ffac331b5f94cd4369cf5a4757d0875974ab88ba9826",
    BASE_READER: "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5",
    SOURCE / "consolidated_reader.py": "b0e4947cfd173663ec284ebb90230ac8eb13569bff5feaa01b5a94865b3427d9",
    SOURCE / "consolidated-filter.awk": "bff0e09869a5d815fce5e3ec4994ac16431897ae685bea934e955f880e445122",
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
for dependency, digest in HELPERS.items():
    checked(dependency, digest)
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
        and baseline["state"] == "no_record" and baseline["epochs"] == baseline["run_windows"] == baseline["flags"] == 0
        and baseline["intent_sha256"] == PINS[RUN / "mainline-baseline-intent.json"]
        and intent["pair_sha256"] == PINS[PAIR],
        "closed deferred-worker source binding differs",
    )
    require(
        final["binding_sha256"] == terminal["binding_sha256"] == key
        and final["resident_boot_healthy"] is final["rollback_outcome_proved"] is final["rollback_transfer_completed"] is True
        and terminal["verdict"] == "NO_PROOF_Y2Q_DEFERRED_WORKER_OR_FLUSH_RETURN_ORIGINAL_RETURNED"
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
            and tuple(frames) == ("run_anchor",) and all(len(frame) == 80 for frame in frames.values())
            and meta["stages"] == {k: sha(v) for k, v in frames.items()}
            and pair["return_template"] == sha(reader.shell(nonce, "0" * 64).encode())
            and intent["script_sha256"] == sha(reader.shell(nonce, before["boot_id_sha256"]).encode()),
            "exact deferred-worker reducer differs")
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
            if facts.get("worker_sample"):
                names = json.loads(checked(QUAL, PINS[QUAL]))["direct_soc_names"]
                facts["worker_name_candidates"] = names.get(facts["worker_sample"]["device_id"], [])
            stock.admit(identity)
            result = dict(schema=SCHEMA, scope=SCOPE, facts=facts, binding=binding,
                          shell_sha256=identity["shell"], terminal_sha256=PINS[RUN / "terminal.json"],
                          first_return_attributed=False, last_candidate_attempt="unknown")
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
