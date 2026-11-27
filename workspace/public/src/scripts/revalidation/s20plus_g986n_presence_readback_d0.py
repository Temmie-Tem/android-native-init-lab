#!/usr/bin/env python3
"""One current-boot, unordered deferred-probe presence scan on the restored S20+."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex

import s20plus_g986n_deferred_readback_d0 as prior

SCRIPT = Path(__file__).resolve()
FILTER = prior.SOURCE / "deferred-presence-filter.awk"
TEST = prior.ROOT / "tests/test_s20plus_presence_readback_d0.py"
PREVIOUS = prior.PARENT / "observation/result.json"
PARENT = prior.RUNS / "s20plus-g986n-presence-readback-d0"
SECTION = "## S20+ current boot unordered deferred probe presence D0\n"
LIMIT = 4656
RESULT_LIMIT = 32768
stock, health, io = prior.stock, prior.health, prior.io
require = prior.require


def inputs():
    prior.checked(prior.SCRIPT, "99479aaf55d9c841d226eeaaecb5d08febadb88cafdaea048d35818612396fc3")
    previous = json.loads(prior.checked(PREVIOUS, "abce42118bb6b43e1fc01a2c28e929f3ab34d50157e34b3bccb2c6eb92ab78b3"))
    expected, original = prior.closure()
    binding = {k: expected[k] for k in prior.IDENTITY}
    require(previous["binding"] == binding and previous["facts"]["state"] == "multiple_windows",
            "prior snapshot binding differs")
    original_filter = shlex.quote(prior.checked(prior.FILTER, prior.HELPERS[prior.FILTER]).decode("ascii"))
    require(original.count(original_filter) == 1, "expected one R4 filter")
    script = original.replace(original_filter, shlex.quote(prior.files.read_file(FILTER).decode("ascii")))
    policy = prior.files.read_file(io.TARGET_CONTRACT).decode()
    require(policy.count(SECTION) == 1, "missing target adoption")
    section = SECTION + policy.split(SECTION)[1].split("\n## ", 1)[0]
    identity = dict(prior=prior.subject(original), schema="s20plus_unordered_presence_d0_v1",
                    section=prior.sha(section.encode()), shell=prior.sha(script.encode()),
                    owner=prior.sha(prior.files.read_file(SCRIPT)), test=prior.sha(prior.files.read_file(TEST)))
    return expected, script, identity


def classify(rc, out, err):
    require(rc == 0 and not err and len(out) <= LIMIT, "incomplete presence scan")
    statuses = {b"P1,invalid\n": "invalid_snapshot", b"y2q_log_missing\n": "missing",
                b"y2q_log_unreadable\n": "unreadable"}
    if out in statuses:
        return {"state": statuses[out]}
    m = re.fullmatch(rb"P1,(\d{1,7}),(\d{1,3}),(\d{1,4}),([01]),([0-9a-f]*),([0-9a-f]*)\n", out)
    require(m is not None, "unknown presence response")
    size, windows, ignored, flush = map(int, m.groups()[:4])
    require(windows <= 256 and windows * 240 <= size <= 2097136 and ignored <= windows * 4
            and (windows or not flush), "inconsistent window summary")
    sets = []
    for raw in m.groups()[4:]:
        ids = re.findall(r"[0-9a-f]{8}", raw.decode("ascii"))
        require(len(ids)*8 == len(raw) and len(ids) == len(set(ids)), "invalid device IDs")
        sets.append(sorted(ids))
    devices = sum(map(len, sets))
    require(devices <= 2 * windows and devices + ignored + flush <= 4 * windows, "excess slot claims")
    names = json.loads(prior.checked(prior.QUAL, prior.PINS[prior.QUAL]))["direct_soc_names"]
    return dict(state="complete", size=size, valid_windows=windows, unauthenticated_slots=ignored,
                first_flush_return="observed" if flush else "unproved", before_call_device_ids=sets[0],
                return_device_ids=sets[1], device_name_candidates={k:names.get(k, []) for k in sorted(set().union(*sets))})


def observe(expected, script, identity):
    stock.admit(identity)
    dest = PARENT / "observation"
    require(not os.path.lexists(dest), "presence read consumed")
    adb = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    before = stock.bracket(adb["path"], expected)
    require(inputs() == (expected, script, identity), "presence closure changed")
    stock.admit(identity)
    require(health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) == adb, "ADB changed")
    dest.mkdir(mode=0o700)
    health._fsync_directory(PARENT)
    fd = os.open(dest, os.O_DIRECTORY | os.O_NOFOLLOW)
    with health.EvidenceOwner(dest, fd, health._directory_identity(os.fstat(fd))) as evidence:
        try:
            binding = {k: expected[k] for k in prior.IDENTITY}
            evidence.publish_json("intent.json", dict(identity=identity, binding=binding))
            cmd = [adb["path"], "-s", before[0], "shell", "-T", "su", "-c", shlex.quote(script)]
            reason, rc, out, err = io.root_capture(cmd, 120, LIMIT)
            io.save_root_receipt(evidence, reason, rc, out, err)
            require(stock.bracket(adb["path"], expected) == before and reason == "completed", "lost boot bracket")
            facts = classify(rc, out, err)
            stock.admit(identity)
            evidence.publish_json("result.json", dict(facts=facts, binding=binding, scope="current_boot_run_wide",
                                                       shell_sha256=identity["shell"], first_return_attributed=False))
            print(json.dumps(facts, sort_keys=True))
        except Exception as exc:
            evidence.publish_json("failure.json", dict(error=type(exc).__name__, reason_sha256=prior.sha(str(exc).encode())))
            raise


def main():
    p = argparse.ArgumentParser(allow_abbrev=False)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review-input", action="store_true")
    mode.add_argument("--connected", action="store_true")
    a = p.parse_args()
    expected, script, identity = inputs()
    if a.review_input:
        print(json.dumps(identity, sort_keys=True))
        return
    stock.PARENT = PARENT
    health._ALLOWED_EVIDENCE_NAMES |= {"intent.json"}
    health._EVIDENCE_MAXIMUMS["intent.json"] = 16384
    health._EVIDENCE_MAXIMUMS["result.json"] = RESULT_LIMIT
    with prior.registry.target_session_lease(prior.ROOT, research_read_only=True):
        observe(expected, script, identity)


if __name__ == "__main__":
    main()
