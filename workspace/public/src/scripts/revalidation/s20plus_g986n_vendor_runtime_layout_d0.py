#!/usr/bin/env python3
"""Measure the stock-direct vendor Image's full destination on the restored S20+."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat
import types
from uuid import uuid4

import s20plus_g986n_twrp_observe_source_view_v1 as files

SCRIPT = Path(__file__).resolve()
BRACKET = SCRIPT.with_name("s20plus_g986n_stock_direct_readback_d0.py")
support = types.ModuleType("_s20_fixed_read")
support.__file__ = str(BRACKET)
code = files.read_file(BRACKET)
if files.file_receipt(code)["sha256"] != "cf0c1b7e38c01fae1c1ae57cc4389c0ea3709ad5193135a0046cda8f14a79cd0":
    raise ValueError("changed first-return binding helper")
exec(compile(code, str(BRACKET), "exec"), support.__dict__)
io = support.io
health = io.health
ROOT = files.ROOT
PARENT = support.RUNS / "s20plus-g986n-vendor-runtime-layout-d0"
LAYOUT = support.BUILD / "candidate3/handoff/layout.h"
LAYOUT_SHA = "7e07091813ed59fba1d09a276c1b27a714bf01270dccff243674dbebe06da4e1"
SECTION = "## S20+ original Magisk vendor runtime FDT geometry D0\n"
TEST = ROOT / "tests/test_s20plus_g986n_vendor_runtime_layout_d0.py"
ORIGINAL = support.RUN / "final-health.json"
FIRST = support.TICKET / "first-observed-return.json"


def fixed_query():
    header = support.checked(LAYOUT, LAYOUT_SHA).decode("ascii")
    def define(name):
        values = re.findall(r"^#define " + name + r" (0x[0-9a-f]+)$", header, re.M)
        if len(values) != 1:
            raise ValueError("invalid vendor layout constant")
        return int(values[0], 16)
    start = define("OUT_KERNEL")
    runtime = define("KERNEL_RUNTIME")
    template = io.root_template()
    # The old script binds one destination and one independent source sweep.
    # Substitute only the former to retain its reducer and transport checks.
    template, n = re.subn(r"(?<=awk )-v dst=[0-9]+ -v de=[0-9]+(?= -v src=[0-9]+ -v se=[0-9]+ )",
                          f"-v dst={start} -v de={start + runtime}", template)
    if n != 1 or template.count(io.ZERO_BOOT) != 1:
        raise ValueError("unexpected shape of reviewed FDT observer")
    return start, runtime, template


def source_health():
    final = json.loads(support.checked(ORIGINAL, support.PINS[ORIGINAL]))
    first = json.loads(support.checked(FIRST, support.PINS[FIRST]))
    expected = final["health"]
    if not (final["resident_boot_healthy"] and final["rollback_transfer_completed"]
            and expected["boot_id_sha256"] == first["boot_sha256"]):
        raise ValueError("incomplete first restored boot")
    return expected


def subject():
    start, runtime, shell = fixed_query()
    scope = files.read_file(io.TARGET_CONTRACT).decode()
    if scope.count(SECTION) != 1:
        raise ValueError("missing geometry scope")
    section = SECTION + scope.split(SECTION)[1].split("\n## ", 1)[0]
    return dict(profile="s20plus_vendor_runtime_fdt_d0", start=start, runtime=runtime,
                layout=LAYOUT_SHA, owner=io.sha(files.read_file(SCRIPT)), section=io.sha(section.encode()),
                transport=io.identity(shell), bracket=io.sha(files.read_file(BRACKET)),
                file_reader=io.sha(files.read_file(files.SCRIPT)), tests=io.sha(files.read_file(TEST)),
                restored=source_health()["boot_id_sha256"])


def admit(identity):
    if (ROOT != io.CANONICAL or PARENT.resolve(strict=True) != PARENT or not PARENT.is_dir()
            or PARENT.stat().st_uid != os.geteuid() or stat.S_IMODE(PARENT.stat().st_mode) != 0o700):
        raise ValueError("invalid private observation root")
    expected = health._json_bytes(dict(identity=identity, review=files.REVIEW_PASS))
    if files.read_file(PARENT / "activation.json", mode=0o400) != expected or subject() != identity:
        raise ValueError("current review required")
    support.registry.require_no_f1_owner(ROOT)
    if any(os.path.lexists(p) for p in (files.CAMPAIGN_GUARD, files.RUN_ROOT / "active-action.json",
                                        ROOT / support.registry.RESEARCH_PENDING)):
        raise ValueError("pending device owner")


def collect(identity, owner):
    admit(identity)
    expected = source_health()
    adb = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    before = support.bracket(adb["path"], expected)
    boot = before[2]["boot_id"]
    if (not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot)
            or io.sha(boot.encode()) != expected["boot_id_sha256"]):
        raise ValueError("changed restored boot")
    start, runtime, fixed = fixed_query()
    if io.sha(fixed.encode()) != identity["transport"]["root_template"]:
        raise ValueError("changed captured query")
    admit(identity)
    if health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) != adb:
        raise ValueError("changed adb")
    script = shlex.quote(fixed.replace(io.ZERO_BOOT, boot))
    reason, rc, out, err = io.root_capture([adb["path"], "-s", before[0], "shell", "su", "-c", script], 45, 2048)
    io.save_root_receipt(owner, reason, rc, out, err)
    if reason != "completed" or rc != 0 or err:
        raise ValueError("incomplete FDT capture")
    facts = io.parse_layout(out)
    if support.bracket(adb["path"], expected) != before:
        raise ValueError("changed geometry observation boot or endpoint")
    admit(identity)
    return dict(profile=identity["profile"], subject=identity, facts=facts, start=start, end_exclusive=start + runtime,
                runtime_bytes=runtime, root=expected["root_health"],
                binding={k: expected[k] for k in ("boot_id_sha256", "serial_sha256", "topology_sha256")})


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--review-input", action="store_true")
    group.add_argument("--connected", action="store_true")
    args = parser.parse_args()
    identity = subject()
    if args.review_input:
        print(json.dumps(identity, sort_keys=True))
        return
    with support.registry.target_session_lease(ROOT, research_read_only=True):
        admit(identity)
        run = PARENT / ("d0-" + uuid4().hex)
        run.mkdir(mode=0o700)
        health._fsync_directory(PARENT)
        fd = os.open(run, os.O_DIRECTORY | os.O_NOFOLLOW)
        with health.EvidenceOwner(run, fd, health._directory_identity(os.fstat(fd))) as owner:
            try:
                result = collect(identity, owner)
                owner.publish_json("result.json", result)
            except Exception as exc:
                owner.publish_json("failure.json", dict(error=type(exc).__name__, reason_sha256=io.sha(str(exc).encode())))
                raise
        print(json.dumps(dict(facts=result["facts"], path=str(run)), sort_keys=True))


if __name__ == "__main__":
    main()
