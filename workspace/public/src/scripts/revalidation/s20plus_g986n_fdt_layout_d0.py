#!/usr/bin/env python3
"""Fixed foreground S20+ FDT geometry measurement, activated by exact independent review."""
import argparse
import hashlib
import json
import os
import re
import selectors
import subprocess
import time
import secrets
import shlex
import stat
import types
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[5]
CANONICAL = Path("/home/temmie/dev/android-native-init-lab")
PRIVATE = ROOT / "workspace/private"
RUNS = PRIVATE / "runs"
EVIDENCE = RUNS / "s20plus-g986n-fdt-layout-d0"
HEADING = "## S20+ foreground FDT layout D0"
TARGET_CONTRACT = ROOT / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
AWK = ROOT / "workspace/public/src/mainline/s20plus_y2q_h0/fdt_layout_observer.awk"
MODEL = PRIVATE / "analysis/s20plus-y2q-boot-map-20261123"
SCHEMA = "s20plus_y2q_fdt_layout_d0_v1"
ZERO_BOOT = "00000000-0000-0000-0000-000000000000"
FIELDS = ("fdt_bytes", "ram_banks", "fixed_ranges", "dynamic_pools", "initrd_present",
          "destination_one_bank", "source_one_bank", "destination_fixed_overlap",
          "source_fixed_overlap", "destination_initrd_overlap", "source_initrd_overlap",
          "old_loader_size_ok", "initrd_one_bank")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected=None):
    if path.resolve(strict=True) != path:
        raise ValueError("indirect source")
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > 512 * 1024:
        raise ValueError("invalid source")
    data = path.read_bytes()
    if expected is not None and sha(data) != expected:
        raise ValueError("source drift")
    return data


health_path = SCRIPT.with_name("s20plus_g986n_attended_root_health_d0.py")
health = types.ModuleType("_fixed_s20_layout_health")
health.__file__ = str(health_path)
health_source = checked(health_path, "24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44")
exec(compile(health_source, str(health_path), "exec"), health.__dict__)
# This owner has a private module instance. Use its atomic evidence writer
# with the three record names belonging to this profile.
health._ALLOWED_EVIDENCE_NAMES = frozenset(("root-receipt.json", "result.json", "failure.json"))
health._EVIDENCE_MAXIMUMS = {name: 16384 for name in health._ALLOWED_EVIDENCE_NAMES}



def root_template():
    model = json.loads(checked(MODEL / "fixture-inputs.json", "7866183bf68ba52b9268a8e88e24be5a3db04625f40208d9f9d3aa48326a309c"))
    runtime = json.loads(checked(MODEL / "comparison.json", "652e793cee6b72d8eb979b3d89176a178034d8826aad99c34a849d384fdf9305"))["mainline_runtime"]
    dst = model["destination"]
    src, se = model["source_sweep"]
    awk = checked(AWK).decode("ascii")
    expected = shlex.quote(health.EXPECTED_ROOT_STDOUT.decode().rstrip("\n"))
    return f"""set -eu
set -o pipefail
export LC_ALL=C
test "$(/system/bin/getprop ro.product.model)" = SM-G986N
test "$(/system/bin/getprop ro.product.device)" = y2q
test "$(/system/bin/getprop ro.product.name)" = y2qksx
test "$(/system/bin/getprop ro.build.version.incremental)" = G986NKSS8IYC2
test "$(/system/bin/getprop sys.boot_completed)" = 1
test "$(/system/bin/cat /proc/sys/kernel/random/boot_id)" = {ZERO_BOOT}
actual=$(
{health.ROOT_READ_SCRIPT})
test "$actual" = {expected}
node=/sys/firmware/fdt
if [ ! -e "$node" ]; then echo layout_unavailable=missing; exit 0; fi
test ! -L "$node" && test -f "$node" || exit 3
test "$(/system/bin/readlink -f "$node")" = "$node" || exit 3
test "$(/system/bin/stat -f -c %t "$node")" = 62656572 || exit 3
if [ ! -r "$node" ]; then echo layout_unavailable=unreadable; exit 0; fi
bb=/data/adb/magisk/busybox
if [ ! -x "$bb" ]; then echo layout_unavailable=awk_missing; exit 0; fi
test ! -L "$bb" && test -f "$bb" || exit 4
test "$(/system/bin/readlink -f "$bb")" = "$bb" || exit 4
test "$(/system/bin/stat -c %s "$bb")" = 1710600 || exit 4
actual_hash=$(/system/bin/sha256sum "$bb")
test "${{actual_hash%% *}}" = 4d60ab3f5a59ebb2ca863f2f514e6924401b581e9b64f602665c008177626651 || exit 4
/system/bin/od -An -v -tx1 -N 2097153 "$node" | "$bb" awk -v dst={dst} -v de={dst+runtime} -v src={src} -v se={se} {shlex.quote(awk)}
"""


def identity(template):
    target = checked(TARGET_CONTRACT).decode()
    marker = HEADING + "\n"
    if target.count(marker) != 1:
        raise ValueError("missing unique layout authority")
    section = target.split(marker, 1)[1].split("\n## ", 1)[0]
    rules = checked(ROOT / "AGENTS.md")
    details = sha(checked(ROOT / "docs/operations/DEVICE_ACTION_CONTRACT_DETAILS.md"))
    declared = re.findall(rb"The incorporated details have SHA-256:\n`([0-9a-f]{64})`", rules)
    if declared != [details.encode()]:
        raise ValueError("common authority pin mismatch")
    return {"common_root": sha(rules), "risk_tiers": sha(checked(ROOT / "docs/operations/DEVICE_ACTION_RISK_TIERS.md")),
            "version": SCHEMA, "owner": sha(checked(SCRIPT)), "section": sha((marker+section).encode()),
            "awk": sha(checked(AWK)), "root_template": sha(template.encode()),
            "health": sha(checked(health_path)), "inventory": sha(checked(SCRIPT.with_name(health.INVENTORY_HELPER_NAME), health.INVENTORY_HELPER_SHA256)),
            "common_details": details}


def admission(subject):
    if ROOT != CANONICAL or subject != identity(root_template()):
        raise ValueError("canonical source identity required")
    receipt = EVIDENCE / "activation.json"
    if stat.S_IMODE(receipt.stat().st_mode) != 0o400 or receipt.stat().st_uid != os.geteuid():
        raise ValueError("invalid activation receipt")
    expected = {"identity": subject, "review": {"verdict": "PASS_GO", "high": 0, "medium": 0, "low": 0}}
    if checked(receipt) != health._json_bytes(expected):
        raise ValueError("independent review does not match current inputs")
    for name in ("s20plus-g986n-routine-actions/active-action.json", "s20plus-g986n-autonomous-research/active-campaign.json",
                 "s22plus-goal-research-v1/f1-owner.json", "s22plus-goal-research-v1/pending-d1.json"):
        if os.path.lexists(RUNS / name):
            raise ValueError("another session owns a pending action")


def parse_layout(data):
    if data in (b"layout_unavailable=missing\n", b"layout_unavailable=unreadable\n", b"layout_unavailable=awk_missing\n"):
        return {"observation": data.decode().strip().split("=")[1]}
    match = re.fullmatch(rb"layout_v1=([0-9,]{25,128})\n", data)
    if not match:
        raise ValueError("invalid layout output")
    values = match[1].split(b",")
    if len(values) != len(FIELDS) or any(not re.fullmatch(b"0|[1-9][0-9]{0,6}", x) for x in values):
        raise ValueError("invalid layout fields")
    n, banks, fixed, dynamic, *flags = map(int, values)
    if not (40 <= n <= 2097152 and banks <= 1024 and fixed + dynamic <= n//4 and all(f in (0,1) for f in flags)):
        raise ValueError("out of bounds layout")
    fields = dict(zip(FIELDS, (n, banks, fixed, dynamic, *map(bool,flags))))
    if (not banks and (fields["destination_one_bank"] or fields["source_one_bank"] or fields["initrd_one_bank"]) or
        not fields["initrd_present"] and any(fields[k] for k in ("initrd_one_bank", "source_initrd_overlap", "destination_initrd_overlap")) or
        fields["old_loader_size_ok"] != (n <= 0x140000-256) or
        not fixed and (fields["destination_fixed_overlap"] or fields["source_fixed_overlap"])):
        raise ValueError("inconsistent layout")
    return {"observation": "geometry", **fields}


def allocate():
    if EVIDENCE.resolve(strict=True) != EVIDENCE or EVIDENCE.stat().st_uid != os.geteuid() or stat.S_IMODE(EVIDENCE.stat().st_mode) != 0o700:
        raise ValueError("invalid private run root")
    run = EVIDENCE / ("d0-" + secrets.token_hex(12))
    run.mkdir(mode=0o700)
    fd = os.open(run, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    health._fsync_directory(EVIDENCE)
    return health.EvidenceOwner(run, fd, health._directory_identity(os.fstat(fd)))


def save_root_receipt(owner, reason, rc, out, err):
    return owner.publish_json("root-receipt.json", {
        "capture": reason, "rc": rc, "stdout_bytes": len(out), "stdout_sha256": sha(out),
        "stderr_bytes": len(err), "stderr_sha256": sha(err),
    })


def root_capture(argv, timeout, maximum):
    """Return a bounded prefix even on timeout or overflow, for digest-only evidence."""
    buffers = [bytearray(), bytearray()]
    remaining = maximum
    reason = "completed"
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, close_fds=True) as proc:
        deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as poll:
                for i, stream in enumerate((proc.stdout, proc.stderr)):
                    poll.register(stream, selectors.EVENT_READ, i)
                while poll.get_map() and reason == "completed":
                    left = deadline - time.monotonic()
                    if left <= 0:
                        reason = "timeout"
                        break
                    for key, _ in poll.select(left):
                        data = os.read(key.fd, min(65536, remaining + 1))
                        if not data:
                            poll.unregister(key.fileobj)
                            continue
                        buffers[key.data].extend(data[:remaining])
                        if len(data) > remaining:
                            reason = "overflow"
                            break
                        remaining -= len(data)
            if reason == "completed":
                try:
                    proc.wait(timeout=max(0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    reason = "timeout"
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
    return reason, proc.returncode, bytes(buffers[0]), bytes(buffers[1])


def command_counts(kinds):
    return {"host_commands": len(kinds), "selected_s20plus_commands": len(kinds) - kinds.count("inventory"),
            "s22plus_commands": 0, "a90_commands": 0, "other_target_commands": 0}


def collect(subject, evidence, counts):
    template = root_template()
    admission(subject)
    def dispatch(kind, argv, timeout, limit):
        admission(subject)
        if tool != health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB)):
            raise ValueError("ADB identity changed")
        counts.append(kind)
        if kind == "root":
            reason, rc, out, err = root_capture(argv, timeout, limit)
            save_root_receipt(evidence, reason, rc, out, err)
            if reason != "completed":
                raise ValueError("root capture " + reason)
        else:
            rc, out, err = health.base.bounded_command(argv, timeout, limit)
        return health._successful_stdout((rc,out,err), label=kind, maximum=limit)
    tool = health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
    adb = tool["path"]
    def inventory():
        out = dispatch("inventory", [adb, "devices","-l"], 10, 32768)
        return health.parse_inventory(health._decode_inventory((0,out,b""), "inventory"))
    rows = inventory()
    selected = health.select_exact_target(rows)
    serial = selected["serial"]
    dev = dispatch("devpath", [adb,"-s",serial,"get-devpath"], 10, 32768)
    path = health._parse_devpath((0,dev,b""))
    health._validate_devpath_binding(selected, path)
    def snapshot():
        out = dispatch("snapshot", [adb,"-s",serial,"exec-out","sh","-c",health.PUBLIC_SHELL_ARGUMENT], 20, 8192)
        return health.parse_public_snapshot((0,out,b""))
    pre = snapshot()
    health._validate_snapshot_binding(pre, selected)
    boot = pre["boot_id"]
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot) or template.count(ZERO_BOOT)!=1:
        raise ValueError("invalid boot binding")
    root = shlex.quote(template.replace(ZERO_BOOT, boot))
    data = dispatch("root", [adb,"-s",serial,"shell","su","-c",root], 45, 2048)
    facts = parse_layout(data)
    if snapshot() != pre:
        raise ValueError("boot or Android health changed")
    end = inventory()
    final = health.select_exact_target(end)
    health._validate_devpath_binding(final,path)
    if final["serial"]!=serial or health.base.sanitized_inventory(end)!=health.base.sanitized_inventory(rows):
        raise ValueError("inventory changed")
    admission(subject)
    return {"schema":SCHEMA,"facts":facts,"subject":subject,"commands":counts, **command_counts(counts),
            "binding":{"serial_sha256":sha(serial.encode()),"topology_sha256":sha(path.encode()),"boot_id_sha256":sha(boot.encode())},
            "target":{k:v for k,v in pre.items() if k!="boot_id"},"actual_entry_observed":False}


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--review-input", action="store_true")
    mode.add_argument("--connected", action="store_true")
    args = parser.parse_args()
    template = root_template()
    subject = identity(template)
    if args.review_input:
        print(json.dumps(subject,sort_keys=True))
        return 0
    admission(subject)
    with allocate() as owner:
        counts = []
        try:
            result = collect(subject,owner,counts)
            owner.publish_json("result.json",result)
        except Exception as error:
            owner.publish_json("failure.json",{"schema":SCHEMA,"started_commands":counts, **command_counts(counts),
                               "failure_type":type(error).__name__,"reason_sha256":sha(str(error).encode())})
            print(f"READ_CLOSED {owner.path}")
            return 1
        print(f"{result['facts']['observation']} {owner.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
