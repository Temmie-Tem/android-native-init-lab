#!/usr/bin/env python3
"""Compare the original Magisk FDT with the consumed stock-direct loader's input assumptions."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat
from uuid import uuid4

import s20plus_g986n_vendor_runtime_layout_d0 as vendor

SCRIPT = Path(__file__).resolve()
files, io, health, support = vendor.files, vendor.io, vendor.health, vendor.support
PARENT = support.RUNS / "s20plus-g986n-fdt-input-d0"
SECTION = "## S20+ restored Magisk FDT input comparisons D0\n"
HOOK = io.AWK.with_name("fdt_input_checks.awk")
TEST = files.ROOT / "tests/test_s20plus_g986n_fdt_input_d0.py"
VENDOR_SHA = "b68efc5e37b1f50103c920158fa42e88c2fc15f396ceb26c61424ffecc9738cb"
BASE_SHA = "3daa9a0adfbcf7472da2e5640dd674b1b5589cd06659f8ddc98046a05a08b8b7"
GUARD = support.SOURCE / "guard.c"
GUARD_SHA = "769f07a969849b3c86c9679113dd650333c0cf493759f0bcdd43cc25d42d880d"
FLAGS = ("chosen_status_ok", "reserved_reg_sizes_nonzero", "input_tree_fits_before_expected_initrd",
         "assumed_input_tree_one_bank", "expected_initrd_one_bank", "assumed_input_tree_fixed_overlap",
         "expected_initrd_fixed_overlap")


def query():
    header = support.checked(vendor.LAYOUT, vendor.LAYOUT_SHA).decode("ascii")
    def constant(name):
        value, = re.findall(r"^#define " + name + r" (0x[0-9a-f]+)$", header, re.M)
        return int(value, 16)
    start, end = constant("IN_RD"), constant("IN_RD_END")
    fdt = constant("IN_FDT")
    if end - start != constant("RD_SIZE") or not 0 < fdt < start < end:
        raise ValueError("invalid retained layout")
    base = support.checked(io.AWK, BASE_SHA).decode("ascii")
    hooks = files.read_file(HOOK).decode("ascii")
    parser, final = base.split("\nEND {")
    point = "take_property(names[off],pos,n);"
    complete_pair = "if ((rs || re) && (!rs || re <= rs)) invalid()"
    if not final or parser.count(point) != 1 or parser.count(complete_pair) != 1:
        raise ValueError("changed FDT parser")
    # Preserve a present endpoint even when the other one is absent.
    parser = parser.replace(complete_pair, "if (rs && re && re <= rs) invalid()")
    parser = parser.replace(point, "input_property(names[off],pos,n); " + point)
    awk = parser + "\n" + hooks
    original = io.root_template()
    prefix, tail = original.rsplit(' | "$bb" awk ', 1)
    if not tail.endswith(shlex.quote(base) + "\n") or prefix.count(io.ZERO_BOOT) != 1:
        raise ValueError("changed FDT transport")
    args = ["-v", f"dst={fdt}", "-v", f"de={fdt+1}", "-v", f"src={start}", "-v", f"se={end}"]
    return prefix + ' | "$bb" awk ' + shlex.join([*args, awk]) + "\n"


def subject():
    support.checked(vendor.SCRIPT, VENDOR_SHA)
    support.checked(GUARD, GUARD_SHA)
    target = files.read_file(io.TARGET_CONTRACT).decode()
    if target.count(SECTION) != 1:
        raise ValueError("missing input comparison scope")
    section = SECTION + target.split(SECTION)[1].split("\n## ", 1)[0]
    return dict(profile="s20plus_fdt_input_d0", section=io.sha(section.encode()),
                owner=io.sha(files.read_file(SCRIPT)), vendor_transport=VENDOR_SHA, guard=GUARD_SHA,
                tests=io.sha(files.read_file(TEST)), hook=io.sha(files.read_file(HOOK)),
                file_reader=io.sha(files.read_file(files.SCRIPT)), transport=io.identity(query()),
                boot_id_sha256=vendor.source_health()["boot_id_sha256"])


def admit(identity):
    if (files.ROOT != io.CANONICAL or PARENT.resolve(strict=True) != PARENT or not PARENT.is_dir()
            or PARENT.stat().st_uid != os.geteuid() or stat.S_IMODE(PARENT.stat().st_mode) != 0o700):
        raise ValueError("invalid private observation directory")
    expected = health._json_bytes(dict(identity=identity, review=files.REVIEW_PASS))
    if files.read_file(PARENT / "activation.json", mode=0o400) != expected or subject() != identity:
        raise ValueError("input comparison has no matching review")
    support.registry.require_no_f1_owner(files.ROOT)
    if any(os.path.lexists(p) for p in (files.CAMPAIGN_GUARD, files.RUN_ROOT / "active-action.json",
                                        files.ROOT / support.registry.RESEARCH_PENDING)):
        raise ValueError("pending owner")


def parse(out):
    if out.startswith(b"layout_unavailable="):
        return io.parse_layout(out)
    endpoint = rb"(lower|higher|missing|match)"
    form = (rb"input_v1=([1-9][0-9]{1,6})," + (endpoint + b",")*3 + rb"(match|different|missing),"
            + b",".join([rb"([01])"] * len(FLAGS)) + rb"\n")
    m = re.fullmatch(form, out)
    if not m or not 40 <= int(m[1]) <= 2097152:
        raise ValueError("invalid FDT comparison")
    start, end, size, root = (value.decode("ascii") for value in m.groups()[1:5])
    if ("missing" in (start, end)) != (size == "missing"):
        raise ValueError("inconsistent initrd presence")
    if size != "missing":
        sign = {"lower": -1, "match": 0, "higher": 1}
        # The size delta is the end delta minus the start delta.
        if start != end or start == "match":
            direction = sign[end] - sign[start]
            if sign[size] != (direction > 0) - (direction < 0):
                raise ValueError("inconsistent initrd comparisons")
    return dict(observation="input_comparison", fdt_bytes=int(m[1]), initrd_start=start, initrd_end=end,
                initrd_size=size, root_compatible=root, **dict(zip(FLAGS, (v==b"1" for v in m.groups()[5:]))))


def collect(identity, owner):
    admit(identity)
    expected = vendor.source_health()
    adb = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    before = support.bracket(adb["path"], expected)
    boot = before[2]["boot_id"]
    if (not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot)
            or io.sha(boot.encode()) != expected["boot_id_sha256"]):
        raise ValueError("unexpected restored boot")
    fixed = query()
    if io.sha(fixed.encode()) != identity["transport"]["root_template"]:
        raise ValueError("changed comparison input")
    admit(identity)
    if health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) != adb:
        raise ValueError("adb changed")
    cmd = [adb["path"], "-s", before[0], "shell", "su", "-c", shlex.quote(fixed.replace(io.ZERO_BOOT, boot))]
    reason, rc, out, err = io.root_capture(cmd, 45, 2048)
    io.save_root_receipt(owner, reason, rc, out, err)
    if reason != "completed" or rc or err:
        raise ValueError("incomplete fixed comparison")
    facts = parse(out)
    if support.bracket(adb["path"], expected) != before:
        raise ValueError("changed target or boot")
    admit(identity)
    return dict(subject=identity, facts=facts, root=expected["root_health"],
                binding={k:expected[k] for k in ("boot_id_sha256", "serial_sha256", "topology_sha256")})


def main():
    cli = argparse.ArgumentParser(allow_abbrev=False)
    modes = cli.add_mutually_exclusive_group(required=True)
    modes.add_argument("--review-input", action="store_true")
    modes.add_argument("--connected", action="store_true")
    args = cli.parse_args()
    identity = subject()
    if args.review_input:
        print(json.dumps(identity, sort_keys=True))
        return
    with support.registry.target_session_lease(files.ROOT, research_read_only=True):
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
