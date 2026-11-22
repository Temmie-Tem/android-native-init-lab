#!/usr/bin/env python3
"""Classify the two fixed S20+ sec_log argument sources on the restored Android boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import types

SCRIPT = Path(__file__).resolve()
LIB = SCRIPT.with_name("s20plus_g986n_fdt_layout_d0.py")
LIB_SHA = "be426410befdab709d8edc84c48914dc9b6d2bd1834a9cf135debc2ac3cc55c5"
lib = types.ModuleType("_s20_io")
lib.__file__ = str(LIB)
source = LIB.read_bytes()
if LIB.resolve(strict=True) != LIB or hashlib.sha256(source).hexdigest() != LIB_SHA:
    raise ValueError("changed read-only session dependency")
exec(compile(source, str(LIB), "exec"), lib.__dict__)
health = lib.health
ROOT = lib.ROOT
SECTION = "## S20+ foreground Samsung log argument D0"
SCHEMA = "s20plus_sec_log_argument_v1"
RUNS = lib.RUNS
PARENT = RUNS / "s20plus-g986n-sec-log-argument-d0"
FILTER = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/sec_log_argument.awk"
FOREIGN_OWNERS = (
    "s20plus-g986n-routine-actions/active-action.json",
    "s20plus-g986n-autonomous-research/active-campaign.json",
    "s22plus-goal-research-v1/f1-owner.json",
    "s22plus-goal-research-v1/pending-d1.json",
)


def template():
    expected_health = shlex.quote(health.EXPECTED_ROOT_STDOUT.decode().rstrip("\n"))
    reducer = shlex.quote(lib.checked(FILTER).decode("ascii"))
    return f"""set -eu
set -o pipefail
export LC_ALL=C
test "$(/system/bin/getprop ro.product.model)" = SM-G986N
test "$(/system/bin/getprop ro.product.device)" = y2q
test "$(/system/bin/getprop ro.product.name)" = y2qksx
test "$(/system/bin/getprop ro.build.version.incremental)" = G986NKSS8IYC2
test "$(/system/bin/getprop sys.boot_completed)" = 1
test "$(/system/bin/cat /proc/sys/kernel/random/boot_id)" = {lib.ZERO_BOOT}
actual=$(
{health.ROOT_READ_SCRIPT})
test "$actual" = {expected_health}
bb=/data/adb/magisk/busybox
test -x "$bb" && test -f "$bb" && test ! -L "$bb" || exit 4
test "$(/system/bin/readlink -f "$bb")" = "$bb" || exit 4
test "$(/system/bin/stat -c %s "$bb")" = 1710600 || exit 4
actual_hash=$(/system/bin/sha256sum "$bb")
test "${{actual_hash%% *}}" = 4d60ab3f5a59ebb2ca863f2f514e6924401b581e9b64f602665c008177626651 || exit 4
reduce() {{
    if [ ! -e "$1" ]; then echo missing; return; fi
    test ! -L "$1" && test -f "$1" || exit 3
    test "$(/system/bin/readlink -f "$1")" = "$1" || exit 3
    test "$(/system/bin/stat -f -c %t "$1")" = "$2" || exit 3
    if [ ! -r "$1" ]; then echo unreadable; return; fi
    /system/bin/od -An -v -tx1 -N 8193 "$1" | "$bb" awk -v terminator="$3" {reducer}
}}
reduce /proc/cmdline 9fa0 10
reduce /sys/firmware/devicetree/base/chosen/bootargs 62656572 0
"""


def subject():
    contract = lib.checked(lib.TARGET_CONTRACT).decode()
    marker = SECTION + "\n"
    if contract.count(marker) != 1:
        raise ValueError("missing unique selected authority")
    section = marker + contract.split(marker)[1].split("\n## ", 1)[0]
    parent = lib.HEADING + "\n"
    if contract.count(parent) != 1:
        raise ValueError("missing unique transport authority")
    transport_section = parent + contract.split(parent)[1].split("\n## ", 1)[0]
    rules = lib.checked(ROOT / "AGENTS.md")
    details = lib.sha(lib.checked(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"))
    if re.findall(rb"The incorporated details have SHA-256:\n`([0-9a-f]{64})`", rules) != [details.encode()]:
        raise ValueError("common details pin mismatch")
    return dict(schema=SCHEMA, owner=lib.sha(lib.checked(SCRIPT)), io=lib.sha(lib.checked(LIB, LIB_SHA)),
                filter=lib.sha(lib.checked(FILTER)), template=lib.sha(template().encode()),
                common=lib.sha(rules), details=details, target_section=lib.sha(section.encode()),
                transport_section=lib.sha(transport_section.encode()),
                tiers=lib.sha(lib.checked(ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md")),
                health=lib.sha(lib.checked(lib.health_path)), inventory=lib.sha(lib.checked(
                    SCRIPT.with_name(health.INVENTORY_HELPER_NAME), health.INVENTORY_HELPER_SHA256)))


def admit(identity):
    if ROOT != lib.CANONICAL or identity != subject() or PARENT.resolve(strict=True) != PARENT:
        raise ValueError("changed target or observation identity")
    info = PARENT.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700 or not PARENT.is_dir():
        raise ValueError("invalid evidence root")
    receipt = PARENT / "activation.json"
    expected = dict(identity=identity, review=dict(verdict="PASS_GO", high=0, medium=0, low=0))
    if (receipt.stat().st_uid != os.geteuid() or stat.S_IMODE(receipt.stat().st_mode) != 0o400
            or lib.checked(receipt) != health._json_bytes(expected)):
        raise ValueError("review does not bind current subject")
    if any(os.path.lexists(RUNS / path) for path in FOREIGN_OWNERS):
        raise ValueError("session already owned")


def classify(data):
    word = rb"(match|absent|different|unsupported|ambiguous|missing|unreadable)"
    m = re.fullmatch(word + rb"\n" + word + rb"\n", data)
    if not m:
        raise ValueError("unexpected filter output")
    return dict(effective=m[1].decode(), chosen=m[2].decode())


def collect(identity, owner, counts):
    tool = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    adb = tool["path"]

    def run(kind, args, timeout, maximum):
        admit(identity)
        if health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)) != tool:
            raise ValueError("ADB identity changed")
        counts.append(kind)
        if kind == "root":
            reason, rc, out, err = lib.root_capture([adb, *args], timeout, maximum)
            lib.save_root_receipt(owner, reason, rc, out, err)
            if reason != "completed":
                raise ValueError("root capture " + reason)
        else:
            rc, out, err = health.base.bounded_command([adb, *args], timeout, maximum)
        return health._successful_stdout((rc, out, err), label=kind, maximum=maximum)

    def inventory():
        data = run("inventory", ["devices", "-l"], 10, 32768)
        return health.parse_inventory(health._decode_inventory((0, data, b""), "inventory"))

    initial = inventory()
    selected = health.select_exact_target(initial)
    serial = selected["serial"]
    data = run("devpath", ["-s", serial, "get-devpath"], 10, 32768)
    port = health._parse_devpath((0, data, b""))
    health._validate_devpath_binding(selected, port)

    def snapshot():
        raw = run("snapshot", ["-s", serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT], 20, 8192)
        return health.parse_public_snapshot((0, raw, b""))

    pre = snapshot()
    health._validate_snapshot_binding(pre, selected)
    boot = pre["boot_id"]
    script = template()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot) or script.count(lib.ZERO_BOOT) != 1:
        raise ValueError("invalid boot binding")
    remote = shlex.quote(script.replace(lib.ZERO_BOOT, boot))
    facts = classify(run("root", ["-s", serial, "shell", "su", "-c", remote], 25, 2048))
    if snapshot() != pre:
        raise ValueError("boot or health changed")
    final = inventory()
    last = health.select_exact_target(final)
    health._validate_devpath_binding(last, port)
    if last["serial"] != serial or health.base.sanitized_inventory(initial) != health.base.sanitized_inventory(final):
        raise ValueError("inventory changed")
    admit(identity)
    return dict(schema=SCHEMA, subject=identity, facts=facts, commands=counts, **lib.command_counts(counts),
                target={k:v for k,v in pre.items() if k != "boot_id"},
                binding=dict(serial_sha256=lib.sha(serial.encode()), topology_sha256=lib.sha(port.encode()),
                             boot_id_sha256=lib.sha(boot.encode())))


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review-input", action="store_true")
    mode.add_argument("--connected", action="store_true")
    args = parser.parse_args()
    identity = subject()
    if args.review_input:
        print(json.dumps(identity, sort_keys=True))
        return 0
    admit(identity)
    path = PARENT / ("d0-" + secrets.token_hex(12))
    path.mkdir(mode=0o700)
    desc = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    health._fsync_directory(PARENT)
    with health.EvidenceOwner(path, desc, health._directory_identity(os.fstat(desc))) as owner:
        counts = []
        try:
            result = collect(identity, owner, counts)
            owner.publish_json("result.json", result)
        except Exception as error:
            owner.publish_json("failure.json", dict(schema=SCHEMA, commands=counts, **lib.command_counts(counts),
                                                     failure_type=type(error).__name__, reason_sha256=lib.sha(str(error).encode())))
            print("READ_CLOSED", path)
            return 1
        print(result["facts"], path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
