#!/usr/bin/env python3
"""Read the retained S20+ control marker on its exact first observed return boot."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat
import types

import s20plus_g986n_twrp_observe_source_view_v1 as files

SCRIPT = Path(__file__).resolve()
ROOT = files.ROOT
RUNS = files.PRIVATE / "runs"
PARENT = RUNS / "s20plus-g986n-stock-direct-readback-d0"
OLD = RUNS / "s20plus-g986n-stock-direct-f1"
RUN = OLD / "run-1795697759773921837"
TICKET = OLD / "ticket-1795697759773921837"
BUILD = files.PRIVATE / "analysis/s20plus-y2q-stock-direct-20261126"
SOURCE = BUILD / "candidate3/control-src"
PAIR = BUILD / "packaged3/pair.json"
STAGE = BUILD / "candidate3/stage.json"
SECTION = "## S20+ first-return stock-direct marker readback D0\n"
PINS = {
    RUN / "terminal.json": "e0118d4fcc77d6aa17b5656b771db30a5bb7261476dfdee71e0bd702eb42dde7",
    RUN / "prepared.json": "4e9ebbd6cbf8fc31e2a6c87c6224ad43528f10824230c879af3eb13e7da1d8d0",
    RUN / "final-health.json": "ff046fe9155d87808efbc1021828b268733890ef0804dce8ec8a50c7e43e2f4d",
    TICKET / "prepared.json": "973184f0f2aa7b0e71ab62a215e1950f0e568358e2f141da89e4b640acc739e6",
    TICKET / "first-observed-return.json": "74ae8720a27364c1966808b6657e536472b60938698273c32f884bffe9032b27",
    PAIR: "0029519deca70ba480df681661be3bc86f4394bbafb2cb2d67a6ed9c1505393b",
    STAGE: "d794a8cd1d5eedf049f386b7bf9e48a801e3793016f1f00fc9cfb49522a88a55",
    RUN / "mainline-baseline-intent.json": "1d520d7607d46fc76fd263b74f41bd31fda07312713f8a6d4a1a23781ff7c763",
    RUN / "mainline-baseline-evidence.json": "da711c9e6bfc3789e9d95682df05c66f4c829893fae693787ce1434c25365ff9",
    RUN / "mainline-return-evidence.json": "128e65c36662293cd075bcff415200c0b5460ccbe3559f3128f4860a99b6e4dc",
    RUN / "rollback-result.json": "09e5b74e7f42cc1850c00f8078bedf55f857a13299fe20d994e74389a6b32648",
    RUN / "candidate-result.json": "bbf1a635cbfc8c1366311a84ff0536299eba5605d7f33017d5b8da293cd70a3f",
    TICKET / "accepted.json": "e8d03f3d7f9bdba1a39ee7c410d7d3a5a665763c22ad0a148e5e4b5c859adce1",
}
READER = SOURCE / "return_stage.py"
FILTER = SOURCE / "return-stage.awk"
IO = SCRIPT.with_name("s20plus_g986n_fdt_layout_d0.py")
REGISTRY = SCRIPT.with_name("consumed_candidate_registry_v1.py")
HELPERS = {
    READER: "f91b8b437fae3b7a6d97aae3d72dad17bf8ae81254f5bdccb69bd9ea20b600f6",
    FILTER: "58c44217e5d523d74c2aa2ec15b1ff3673ec7892daf2c4e14d19e4f7affcdfc8",
    IO: "be426410befdab709d8edc84c48914dc9b6d2bd1834a9cf135debc2ac3cc55c5",
    REGISTRY: "e67d75137469f0435c3b9e8780c1b81d8bd5fda2d8142e03499d09784443cead",
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def checked(path, expected):
    raw = files.read_file(path)
    require(files.file_receipt(raw)["sha256"] == expected, "changed input " + path.name)
    return raw


def load(path):
    module = types.ModuleType(path.stem)
    module.__file__ = str(path)
    exec(compile(checked(path, HELPERS[path]), str(path), "exec"), module.__dict__)
    return module


io = load(IO)
health = io.health
registry = load(REGISTRY)
reader = load(READER)


def closure():
    d = {p: json.loads(checked(p, pin)) for p, pin in PINS.items()}
    outer = PINS[TICKET / "prepared.json"]
    prepared = d[TICKET / "prepared.json"]
    first = d[TICKET / "first-observed-return.json"]
    final = d[RUN / "final-health.json"]
    inner = d[RUN / "prepared.json"]["binding_sha256"]
    restored = final["health"]
    baseline = d[RUN / "mainline-baseline-evidence.json"]
    intent = d[RUN / "mainline-baseline-intent.json"]
    returned = d[RUN / "mainline-return-evidence.json"]
    require(prepared["run"] == str(RUN) and first["binding_sha256"] == outer
            and d[TICKET / "accepted.json"]["grant_sha256"] == intent["grant_sha256"] == outer
            and intent["pair_sha256"] == PINS[PAIR] and baseline["intent_sha256"] == PINS[RUN / "mainline-baseline-intent.json"]
            and baseline["state"] == "no_record" and baseline["size"] == reader.CAPACITY
            and baseline["boot_id_sha256"] == prepared["health"]["boot_id_sha256"]
            and baseline["boot_id_sha256"] != first["boot_sha256"] == restored["boot_id_sha256"]
            and restored["serial_sha256"] == prepared["health"]["serial_sha256"]
            and restored["topology_sha256"] == prepared["health"]["topology_sha256"], "first-return chain")
    require(inner == final["binding_sha256"] == returned["binding_sha256"] == d[RUN / "terminal.json"]["binding_sha256"]
            and final["resident_boot_healthy"] and final["rollback_transfer_completed"]
            and returned["health_sha256"] == PINS[RUN / "final-health.json"] and returned["tag"]["state"] == "ABSENT"
            and returned["original_transfer_sha256"] == PINS[RUN / "rollback-result.json"], "original return")
    pair, stage = d[PAIR], d[STAGE]
    for key, field in (("candidate", "candidate"), ("rollback", "original")):
        result = d[RUN / (key + "-result.json")]
        require(result["binding_sha256"] == inner and result["classification"] == "odin_transfer_completed"
                and result["receipt"]["ap"] == pair["archives"][key]["ap"]
                and result["receipt"]["ap"]["sha256"] == prepared[field], "transfer chain")
    nonce = pair["nonce"]
    frames = reader.frames(nonce, reader.EARLY_STAGES)
    require(pair["raw"] == stage["raw"] and nonce == stage["nonce"] and stage["single_producer"] == "prebranch"
            and {k: io.sha(v) for k, v in frames.items()} == stage["stages"], "frame identity")
    checked(FILTER, HELPERS[FILTER])
    shell = reader.shell(nonce, restored["boot_id_sha256"], reader.EARLY_STAGES)
    return restored, shell


def subject(shell):
    target = files.read_file(io.TARGET_CONTRACT).decode()
    require(target.count(SECTION) == 1, "selected policy section")
    section = SECTION + target.split(SECTION)[1].split("\n## ", 1)[0]
    rules = files.read_file(ROOT / "AGENTS.md")
    details = io.sha(files.read_file(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"))
    require(re.findall(rb"The incorporated details have SHA-256:\s*`([a-f0-9]{64})`", rules) == [details.encode()],
            "common detail pin")
    return dict(owner=io.sha(files.read_file(SCRIPT)), root=io.sha(rules), details=details, section=io.sha(section.encode()),
                tiers=io.sha(files.read_file(ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md")),
                files=io.sha(files.read_file(files.SCRIPT)), health=io.sha(files.read_file(io.health_path)),
                inventory=io.sha(checked(SCRIPT.with_name(health.INVENTORY_HELPER_NAME), health.INVENTORY_HELPER_SHA256)),
                helpers={p.name: io.sha(checked(p, v)) for p, v in HELPERS.items()}, shell=io.sha(shell.encode()),
                tests=io.sha(files.read_file(ROOT / "tests/test_s20plus_g986n_stock_direct_readback_d0.py")))


def admit(identity):
    require(ROOT == io.CANONICAL and PARENT.resolve(strict=True) == PARENT
            and PARENT.stat().st_uid == os.geteuid() and stat.S_IMODE(PARENT.stat().st_mode) == 0o700, "evidence root")
    actual = files.read_file(PARENT / "activation.json", mode=0o400)
    require(actual == health._json_bytes(dict(identity=identity, review=files.REVIEW_PASS)), "independent review")
    registry.require_no_f1_owner(ROOT)
    require(not any(os.path.lexists(p) for p in (files.RUN_ROOT / "active-action.json", files.CAMPAIGN_GUARD,
                                                ROOT / registry.RESEARCH_PENDING)), "pending operation")


def bracket(adb, expected):
    def call(args, timeout, maximum):
        return health.base.bounded_command([adb, *args], timeout, maximum)
    rows = health.parse_inventory(health._decode_inventory(call(["devices", "-l"], 10, 32768), "inventory"))
    selected = health.select_exact_target(rows)
    serial = selected["serial"]
    require(io.sha(serial.encode()) == expected["serial_sha256"], "target changed")
    port = health._parse_devpath(call(["-s", serial, "get-devpath"], 10, 32768))
    health._validate_devpath_binding(selected, port)
    require(io.sha(port.encode()) == expected["topology_sha256"], "port changed")
    def snapshot():
        args = ["-s", serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT]
        result = health.parse_public_snapshot(call(args, 20, 8192))
        health._validate_snapshot_binding(result, selected)
        return result

    snap = snapshot()
    require(io.sha(snap["boot_id"].encode()) == expected["boot_id_sha256"], "first-return boot changed")
    root = health.parse_root_result(call(["-s", serial, "shell", "su", "-c", health.ROOT_SHELL_ARGUMENT], 25, 4096))
    require(root == expected["root_health"], "root health changed")
    require(snapshot() == snap, "boot changed during root health")
    return serial, port, snap


def classify(rc, out, err):
    facts = reader.parse(rc, out, err, reader.EARLY_STAGES)
    if "size" in facts:
        if facts["size"] == 0:
            facts["state"] = "empty_snapshot"
        elif facts["primary_entry_count"] or facts["prebranch_count"] > 1:
            facts["state"] = "ambiguous"
    return facts


def observe(identity, expected, script):
    admit(identity)
    parent = PARENT / "observation"
    parent.mkdir(mode=0o700)
    health._fsync_directory(PARENT)
    fd = os.open(parent, os.O_DIRECTORY | os.O_NOFOLLOW)
    with health.EvidenceOwner(parent, fd, health._directory_identity(os.fstat(fd))) as owner:
        try:
            adb = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
            before = bracket(adb["path"], expected)
            require(closure() == (expected, script) and subject(script) == identity, "inputs changed")
            admit(identity)
            require(health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) == adb, "ADB changed")
            owner.publish_json("intent.json", dict(identity=identity, boot_id_sha256=expected["boot_id_sha256"]))
            command = [adb["path"], "-s", before[0], "shell", "-T", "su", "-c", shlex.quote(script)]
            reason, rc, out, err = io.root_capture(command, 120, 96)
            io.save_root_receipt(owner, reason, rc, out, err)
            after = bracket(adb["path"], expected)
            require(before == after and reason == "completed", "incomplete first-return bracket")
            facts = classify(rc, out, err)
            admit(identity)
            owner.publish_json("result.json", dict(facts=facts, binding={k: expected[k] for k in
                               ("serial_sha256", "topology_sha256", "boot_id_sha256")}, root=expected["root_health"],
                               shell_sha256=identity["shell"], terminal_sha256=PINS[RUN / "terminal.json"]))
            print(json.dumps(facts, sort_keys=True))
        except Exception as exc:
            owner.publish_json("failure.json", dict(reason_sha256=io.sha(str(exc).encode()), error=type(exc).__name__))
            raise


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review-input", action="store_true")
    mode.add_argument("--connected", action="store_true")
    args = parser.parse_args()
    original, script = closure()
    identity = subject(script)
    if args.review_input:
        print(json.dumps(identity, sort_keys=True))
        return
    health._ALLOWED_EVIDENCE_NAMES |= {"intent.json"}
    health._EVIDENCE_MAXIMUMS["intent.json"] = 16384
    with registry.target_session_lease(ROOT, research_read_only=True):
        observe(identity, original, script)


if __name__ == "__main__":
    main()
