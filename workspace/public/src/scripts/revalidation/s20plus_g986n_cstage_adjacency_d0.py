#!/usr/bin/env python3
"""Count C-stage frame adjacency on the closed y2q trial's first restored boot."""

import shlex
import sys
import types
from pathlib import Path

import s20plus_g986n_twrp_observe_source_view_v1 as files

SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("s20plus_g986n_mainline_adjacency_d0.py")
SOURCE_SHA = "1db1cf6a160029076b5bff1687d2b752228b66692fa2c3bd304ed5124706a2b8"
READER = files.ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/mainline-handoff/return_stage.py"
READER_SHA = "1fc37c9a3bcf1b1cc6410628a766ad8b5b0f15db9104bc4f3327a6a07ef2f8e5"
RUNS = files.PRIVATE / "runs"
PARENT = RUNS / "s20plus-g986n-cstage-adjacency-d0"
OLD = RUNS / "s20plus-g986n-cstage-list-f1"
RUN = OLD / "run-1795717837883139539"
TICKET = OLD / "ticket-1795717837883139539"
BUILD = files.PRIVATE / "analysis/s20plus-y2q-cstage-serial-20261127"
PAIR = BUILD / "packaged/pair.json"
STAGE = BUILD / "candidate/stage.json"
CANDIDATE = "32e40210c5487f37de32c3d541e454df03e86855d74a5a9c5cf420f7811b5b68"
SCHEMA = "s20plus_g986n_cstage_adjacency_d0_v1"
HEADING = "## S20+ first-return C-stage marker adjacency D0\n"
PREDECESSOR = "## S20+ first-return mainline marker adjacency D0\n"
TRIAL = "## S20+ y2q Linux C-stage and ACM PID1 under one attended approval\n"

PINS = {
    RUN / "terminal.json": "4acf0f9f96487a95089455a2ec4192107ec5a21fb30b674d7bc9bc3bf007890c",
    RUN / "prepared.json": "b352638f01e494afb13e84f919b6e4d6e4da1240ff625944868a1c4547f19799",
    RUN / "final-health.json": "f81d0319e1cba22c5a1a11fb1999b1374dba65935503379d0dfba24f92ba92a3",
    RUN / "mainline-baseline-intent.json": "f654ea139ba4ea68d0e63800ad6f14df396ad92209cc9d95424da0ba16fd6d0a",
    RUN / "mainline-baseline-evidence.json": "801289e519b4ac65fce2a8a7b095fddc6a40387ef1416eaedf170a0a8a2a8416",
    RUN / "mainline-return-intent.json": "9c72054abf0f48e08b9f7e8f66e77fa33de08217d3b2841095537cc767de32e4",
    RUN / "mainline-return-evidence.json": "fb11ec59fe8ffc3e82c0ee72103dc77db24764c3979eb93d2e0ac843530fbace",
    RUN / "mainline-return-scan.capture.json": "88585deed83fc0b6c50934f76b9ea78b75554b6fb16a761e4b0b32d85d9fe954",
    RUN / "candidate-result.json": "40e0b0d073663694b41607e946f391c7c7d741bbafb34682e6a705f68197f3b8",
    RUN / "rollback-result.json": "9e61e06c5621c838c859a482a2ca42f7c1d44b706d76d1e5d1cd484487c819bd",
    RUN / "rollback-intent.json": "91ba736992257e3e7645686baac41be69b1ac7c6b9f2e92e3670cf9fd018acb9",
    RUN / "physical-rollback-intent.json": "806f676f8a4009b541f35d625940e11d10df14e1cb4dcdec1db6318ee97ffd2d",
    RUN / "physical-confirmation-intent.json": "c697fa7572917c762d72bcca4c934a4de8b192a903440a7684ef9cf25d61c6f5",
    RUN / "physical-observation-intent.json": "2a56744465e49f4a355181d90864efb75a5ba3ec803e10f5b44a20009cd0b9b4",
    RUN / "physical-rollback-arrival.json": "5901cce7dbdfbbae32cc004528143755d0da7c3e59515facf7eda72f385c8600",
    TICKET / "prepared.json": "35a0d5e32d6c8f3e152c6c06afd7dba68573414c6c7e83a3a2aff6c8f0d293c1",
    TICKET / "accepted.json": "365863a22d2a7db0ecdde214ebcd5077b5e54305ff51e39df1961327ef6c8f2e",
    TICKET / "first-observed-return.json": "7f990bef1c80b97195e6cbc3a9e9add40dde6ee4a50ca6ab7cdb22b4e341cbd9",
    TICKET / "physical-cue.json": "22438997980be7f81b2b274c7fdc4ee7101a06918ff4baf0f34f8d35aee3e799",
    OLD / "consumed-candidates" / (CANDIDATE + ".json"): "79fd67d212f07346ce3a724cacdaab2439914db4b339d65e214ce038c966dcc0",
    PAIR: "6131db908c212b11d8a1718e4f32d5d9bfb6fd518a3aace2f55d302c7f555489",
    STAGE: "b7c4a59689d9cc5f7589a870dbb6809bb0a4cd9e17e2ea2d6fb57a6a6181d0e4",
}


def scan_command(nonce, boot_digest):
    before, after = profile.reducer()
    after = profile.replace_once(after, '"y2q_log_v1=', '"y2q_cstage_adj_v1=')
    script = profile.reader.shell(nonce, boot_digest)
    return profile.replace_once(script, shlex.quote(before), shlex.quote(after))


def load_profile():
    source = files.read_file(SOURCE)
    if files.file_receipt(source)["sha256"] != SOURCE_SHA:
        raise ValueError("reviewed adjacency owner changed")
    # Reuse the exact lease, health bracket and closure in a private instance.
    # These fixed substitutions change only historical identities and framing.
    for old, new, count in (
        (b", reader.EARLY_STAGES", b"", 4),
        (b"NO_PROOF_Y2Q_EARLY_PAIR_RESIDENT_HEALTH_OBSERVED", b"NO_PROOF_Y2Q_CSTAGE_ORIGINAL_MAGISK_RETURNED", 1),
        (b"HOST_ONLY_S20PLUS_Y2Q_EARLY_AP_PAIR", b"HOST_ONLY_S20PLUS_Y2Q_STAGE_AP_PAIR", 1),
        (b"HOST_ONLY_Y2Q_EARLY_PAIR", b"HOST_ONLY_Y2Q_KERNEL_STAGE_WITNESS", 1),
        (b'y2q_early_v2=2097136,4,4,0', b'y2q_log_v1=2097136,4,4,0', 1),
        (b'rb"y2q_early_adj_v1="', b'rb"y2q_cstage_adj_v1="', 1),
        (b"prebranch_count", b"fdt_count", 2),
        (b"primary_entry_count", b"unflatten_count", 2),
        (b"test_s20plus_g986n_mainline_adjacency_d0.py", b"test_s20plus_g986n_cstage_adjacency_d0.py", 1),
        (b"helpers={p.name:", b"helpers={str(p.relative_to(ROOT)):", 1),
    ):
        if source.count(old) != count:
            raise ValueError("reviewed C-stage adaptation differs")
        source = source.replace(old, new)
    name = "_s20_cstage_adjacency_profile"
    module = types.ModuleType(name)
    module.__file__ = str(SCRIPT)
    sys.modules[name] = module
    exec(compile(source, str(SOURCE), "exec"), module.__dict__)
    module.HELPERS.update({SOURCE: SOURCE_SHA, READER: READER_SHA})
    module.reader = module.load(READER)
    module.support.HELPERS[module.reader.FILTER] = module.support.HELPERS[module.support.reader.FILTER]
    module.PARENT, module.OLD, module.RUN, module.TICKET = PARENT, OLD, RUN, TICKET
    module.PAIR, module.STAGE, module.CANDIDATE, module.PINS = PAIR, STAGE, CANDIDATE, PINS
    module.SCHEMA, module.HEADING = SCHEMA, HEADING
    module.BASE_HEADING, module.TRIAL_HEADING = PREDECESSOR, TRIAL
    module.scan_command = scan_command
    return module


profile = load_profile()


if __name__ == "__main__":
    raise SystemExit(profile.main())
