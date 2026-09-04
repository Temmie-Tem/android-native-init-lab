#!/usr/bin/env python3
"""One attended S20+ PMSG marker / ordinary reboot / first-return comparison."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import time

ACTIVE = False
VERSION = "s20plus-g986n-pmsg-warm-reboot-d1-v1"
SECTION = "## S20+ PMSG Warm-Reboot Marker D1"
DELEGATION = "S20PLUS_PMSG_WARM_REBOOT_D1_DELEGATION_V1"
PRIVATE_ROOT = Path("workspace/private/runs/s20plus-g986n-pmsg-warm-reboot-d1")
SHARED_GUARD = Path("workspace/private/runs/s20plus-g986n-routine-actions/active-action.json")
READINESS_NAME = "s20plus_g986n_pstore_readiness_d0.py"
READINESS_SHA256 = "f1e61ec324b7c446ed73e14fe6318cf1a7488733b634861c6ffbbeb79001552b"
WAIT_SECONDS = 180
MAX_POLLS = 60
RECORD_MAXIMUM = 262144
EVENTS = frozenset({"binding", "marker-intent", "marker-result", "reboot-intent", "reboot-result", "arrival", "read-intent", "read-result", "failure", "terminal", "abort", "observation-gap"})


class MarkerError(RuntimeError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise MarkerError("duplicate JSON key")
            result[key] = value
        return result
    result = json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: (_ for _ in ()).throw(MarkerError("nonfinite JSON")))
    if canonical(result) != data:
        raise MarkerError("noncanonical journal bytes")
    return result


def repo_root():
    return Path(__file__).resolve().parents[5]


def load_readiness():
    path = Path(__file__).with_name(READINESS_NAME)
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
        raise MarkerError("indirect readiness dependency")
    data = path.read_bytes()
    if digest(data) != READINESS_SHA256:
        raise MarkerError("readiness dependency drift")
    spec = importlib.util.spec_from_file_location("_s20_pmsg_readiness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if path.read_bytes() != data:
        raise MarkerError("readiness source changed during import")
    return module


ready = load_readiness()
health = ready.health


def normalized_source():
    data, _ = health._read_direct_regular_source(Path(__file__))
    data, count = re.subn(rb"^ACTIVE = (?:True|False)$", b"ACTIVE = <BOOLEAN>", data, flags=re.M)
    if count != 1:
        raise MarkerError("activation normalization")
    return digest(data)


def require_active():
    if not ACTIVE:
        raise MarkerError("PMSG marker capability is dormant")
    root = repo_root()
    for relative in ("AGENTS.md", "docs/operations/DEVICE_ACTION_RISK_TIERS.md"):
        data, _ = health._read_direct_regular_source(root / relative)
        if DELEGATION not in data.decode():
            raise MarkerError("common PMSG delegation missing")
    data, _ = health._read_direct_regular_source(root / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md")
    text = data.decode()
    if text.count(SECTION + "\n") != 1:
        raise MarkerError("missing unique target marker section")
    section = text.split(SECTION + "\n", 1)[1].split("\n## ", 1)[0]
    for line in ("Status: **BINDING - PMSG WARM-REBOOT D1 ACTIVE**", "Runner-Normalized-SHA256: `" + normalized_source() + "`"):
        if section.splitlines().count(line) != 1:
            raise MarkerError("marker activation/source mismatch")
    health._direct_regular_receipt(Path(__file__).with_name(READINESS_NAME), expected_size=24362, expected_sha256=READINESS_SHA256)
    ready.require_active()


def validate_binding(value):
    keys = {"version", "source_sha256", "serial_sha256", "topology_sha256", "source_boot_sha256", "nonce", "major", "minor"}
    if type(value) is not dict or set(value) != keys or value["version"] != VERSION:
        raise MarkerError("binding schema")
    for key in ("source_sha256", "serial_sha256", "topology_sha256", "source_boot_sha256", "nonce"):
        if type(value[key]) is not str or re.fullmatch("[0-9a-f]{64}", value[key]) is None:
            raise MarkerError("binding digest grammar")
    for key, maximum in (("major", 4095), ("minor", 1048575)):
        if type(value[key]) is not int or not 0 <= value[key] <= maximum:
            raise MarkerError("binding device number")
    if value["source_sha256"] != normalized_source():
        raise MarkerError("bound marker source changed")
    return value


def make_binding(observation):
    if observation.get("readiness") != "METADATA_READY_RETENTION_UNPROVED":
        raise MarkerError("PMSG metadata not ready")
    identity = observation["binding"]
    node = observation["facts"]["pmsg_node"]
    value = dict(version=VERSION, source_sha256=normalized_source(), serial_sha256=identity["serial_sha256"], topology_sha256=identity["topology_sha256"], source_boot_sha256=identity["boot_id_sha256"], nonce=secrets.token_hex(32), major=node["major"], minor=node["minor"])
    return validate_binding(value)


def marker_line(binding):
    validate_binding(binding)
    return "S20PMSG1:" + digest(canonical(binding)) + ":" + binding["nonce"] + ":END"


def marker_bytes(binding):
    return ("\n" + marker_line(binding) + "\n").encode("ascii")


def health_guard(boot_sha256):
    if re.fullmatch("[0-9a-f]{64}", boot_sha256) is None:
        raise MarkerError("boot digest grammar")
    return health.ROOT_READ_SCRIPT + r"""
[ "$uid" = 0 ] && [ "$gid" = 0 ] && [ "$context" = u:r:magisk:s0 ] || exit 64
[ "$magisk_version" = 30.7:MAGISK:R ] && [ "$magisk_version_code" = 30700 ] || exit 64
[ "$selinux" = Enforcing ] && [ "$pid1_exe" = /system/bin/init ] && [ "$pid1_context" = u:r:init:s0 ] || exit 64
[ "$(/system/bin/getprop ro.product.model)" = SM-G986N ] || exit 64
[ "$(/system/bin/getprop ro.product.device)" = y2q ] || exit 64
[ "$(/system/bin/getprop ro.product.name)" = y2qksx ] || exit 64
[ "$(/system/bin/getprop ro.build.version.incremental)" = G986NKSS8IYC2 ] || exit 64
[ "$(/system/bin/getprop sys.boot_completed)" = 1 ] || exit 64
boot=$(/system/bin/cat /proc/sys/kernel/random/boot_id)
boot_hash=$(printf '%s' "$boot" | /system/bin/sha256sum)
boot_hash=${boot_hash%% *}
""" + f'[ "$boot_hash" = {boot_sha256} ] || exit 64\n'


def write_script(binding):
    validate_binding(binding)
    dev = f'{binding["major"]}:{binding["minor"]}'
    rdev = f'{binding["major"]:x}:{binding["minor"]:x}:1'
    return health_guard(binding["source_boot_sha256"]) + f"""
[ "$(/system/bin/cat /sys/devices/virtual/pmsg/pmsg0/dev)" = '{dev}' ] || exit 65
[ "$(/system/bin/cat /sys/module/ramoops/parameters/pmsg_size)" = 262144 ] || exit 65
[ ! -L /dev/pmsg0 ] && [ -c /dev/pmsg0 ] || exit 65
# Pin a read-only descriptor and verify its character identity before opening
# that descriptor for writing. Never use a create/truncate open on the pathname.
exec 3< /dev/pmsg0
[ -c /proc/self/fd/3 ] || exit 65
[ "$(/system/bin/stat -Lc '%t:%T:%h' /proc/self/fd/3)" = '{rdev}' ] || exit 65
exec 4> /proc/self/fd/3
[ -c /proc/self/fd/4 ] || exit 65
[ "$(/system/bin/stat -Lc '%t:%T:%h' /proc/self/fd/4)" = '{rdev}' ] || exit 65
printf '\\n%s\\n' '{marker_line(binding)}' >&4
exec 4>&- 3<&-
printf 'S20PMSG_WRITE_V1;returned=1;marker_sha256={digest(marker_bytes(binding))}\\n'
"""


def read_script(binding, boot_sha256):
    validate_binding(binding)
    if boot_sha256 == binding["source_boot_sha256"]:
        raise MarkerError("reader cannot reuse source boot")
    return health_guard(boot_sha256) + f"""
node=/sys/fs/pstore/pmsg-ramoops-0
finish() {{ printf 'S20PMSG_READ_V1;state=%s;matches=%s;size=%s\\n' "$1" "$2" "$3"; }}
[ ! -L "$node" ] || {{ finish indirect 0 0; exit 0; }}
[ -e "$node" ] || {{ finish unavailable 0 0; exit 0; }}
[ -f "$node" ] && [ -r "$node" ] || {{ finish unreadable 0 0; exit 0; }}
before=$(/system/bin/stat -c '%d:%i:%f:%s:%h' "$node")
size=$(/system/bin/stat -c '%s' "$node")
[ "$size" -le {RECORD_MAXIMUM} ] || {{ finish oversized 0 0; exit 0; }}
[ "$(/system/bin/stat -c '%h' "$node")" = 1 ] || {{ finish indirect 0 0; exit 0; }}
exec 3< "$node"
[ -f /proc/self/fd/3 ] || exit 65
[ "$(/system/bin/stat -Lc '%d:%i:%f:%s:%h' /proc/self/fd/3)" = "$before" ] || exit 65
matches=$(/system/bin/head -c {RECORD_MAXIMUM + 1} <&3 | /system/bin/grep -aFx '{marker_line(binding)}' | /system/bin/wc -l)
after=$(/system/bin/stat -Lc '%d:%i:%f:%s:%h' /proc/self/fd/3)
exec 3<&-
[ "$after" = "$before" ] && [ "$(/system/bin/stat -c '%d:%i:%f:%s:%h' "$node")" = "$before" ] || {{ finish changed 0 0; exit 0; }}
finish scanned "$matches" "$size"
"""


def parse_write(result, binding):
    expected = health.EXPECTED_ROOT_STDOUT + f'S20PMSG_WRITE_V1;returned=1;marker_sha256={digest(marker_bytes(binding))}\n'.encode()
    output = health._successful_stdout(result, label="fixed PMSG write", maximum=8192)
    if output != expected:
        raise MarkerError("writer receipt mismatch")
    return {"returned": True, "stdout_sha256": digest(output), "marker_sha256": digest(marker_bytes(binding))}


def parse_read(result):
    output = health._successful_stdout(result, label="fixed PMSG comparison", maximum=8192)
    if not output.startswith(health.EXPECTED_ROOT_STDOUT):
        raise MarkerError("reader root health mismatch")
    match = re.fullmatch(rb"S20PMSG_READ_V1;state=(scanned|unavailable|unreadable|indirect|oversized|changed);matches=(0|[1-9][0-9]{0,3});size=(0|[1-9][0-9]{0,5})\n", output[len(health.EXPECTED_ROOT_STDOUT):])
    if match is None:
        raise MarkerError("reader receipt framing")
    state, count, size = match[1].decode(), int(match[2]), int(match[3])
    if size > RECORD_MAXIMUM or count > RECORD_MAXIMUM // 143 or (state == "scanned" and count * 143 > size):
        raise MarkerError("reader receipt bounds")
    if state != "scanned" and (count or size):
        raise MarkerError("contradictory missing-record receipt")
    return {"state": state, "matches": count, "size": size, "stdout_sha256": digest(output)}


def ensure_private_dirs(root, relative):
    current = root.resolve(strict=True)
    for part in relative.parts:
        child = current / part
        try:
            child.mkdir(mode=0o700)
            health._fsync_directory(current)
        except FileExistsError:
            pass
        info = child.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise MarkerError("indirect or foreign private directory")
        current = child
    return current


def publish(path, value):
    data = canonical(value)
    if len(data) > 32768:
        raise MarkerError("journal node too large")
    temporary = path.with_name(".tmp-" + secrets.token_hex(12))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        offset = 0
        while offset < len(data):
            count = os.write(fd, data[offset:])
            if count <= 0:
                raise MarkerError("short journal publication")
            offset += count
        os.fsync(fd)
        os.link(temporary, path, follow_symlinks=False)
        temporary.unlink()
        health._fsync_directory(path.parent)
    finally:
        os.close(fd)
        if temporary.exists():
            temporary.unlink()


def read_node(path):
    data, _ = health._read_direct_regular_source(path, maximum=32768)
    if stat.S_IMODE(path.stat().st_mode) != 0o400 or path.stat().st_uid != os.geteuid():
        raise MarkerError("journal mode/owner")
    return strict_json(data)


class Journal:
    def __init__(self, path):
        self.path = path

    def has(self, name):
        return os.path.lexists(self.path / (name + ".json"))

    def put(self, name, value):
        if name not in EVENTS:
            raise MarkerError("unknown event")
        publish(self.path / (name + ".json"), {"version": VERSION, "event": name, "data": value})

    def get(self, name):
        node = read_node(self.path / (name + ".json"))
        if type(node) is not dict or set(node) != {"version", "event", "data"} or node["version"] != VERSION or node["event"] != name:
            raise MarkerError("event schema")
        return node["data"]

    def validate_guard(self):
        guard = repo_root() / SHARED_GUARD
        if not exact_data(read_node(guard), guard_data()):
            raise MarkerError("foreign shared guard")

    def validate_names(self):
        if any(p.name not in {x + ".json" for x in EVENTS} for p in self.path.iterdir()):
            raise MarkerError("unknown or partial journal entry")


def check_identity(observation, binding, *, changed_boot=False, expected_boot=None):
    current = observation["binding"]
    if any(current[k] != binding[k] for k in ("serial_sha256", "topology_sha256")):
        raise MarkerError("prepared target/topology changed")
    boot = current["boot_id_sha256"]
    if expected_boot is not None and boot != expected_boot:
        raise MarkerError("bound boot changed")
    if changed_boot and boot == binding["source_boot_sha256"]:
        raise MarkerError("source boot was reused")
    return boot


class Device:
    def __init__(self):
        require_active()
        self.serial = None
        self.last_capture = None
        self.counts = dict(host_command_count=0, selected_target_command_count=0, inventory_command_count=0, root_command_count=0, s22plus_command_count=0, a90_command_count=0, other_target_command_count=0)

    def preflight(self, binding=None, journal=None):
        require_active()
        class BoundReadiness(ready.FixedBackend):
            def run(inner, argv, timeout, maximum):
                require_active()
                adb = health.EXPECTED_ADB_PATH
                shapes = [
                    ([adb, "devices", "-l"], 10.0, 32768),
                    ([adb, "-s", inner.serial, "get-devpath"], 10.0, 32768),
                    ([adb, "-s", inner.serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT], 20.0, 8192),
                    ([adb, "-s", inner.serial, "shell", "su", "-c", ready.ROOT_ARGUMENT], ready.ROOT_TIMEOUT, ready.ROOT_MAXIMUM),
                    ([adb, "-s", inner.serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT], 20.0, 8192),
                    ([adb, "devices", "-l"], 10.0, 32768),
                ]
                if inner.ordinal >= len(shapes) or (argv, timeout, maximum) != shapes[inner.ordinal]:
                    raise MarkerError("command outside fixed readiness sequence")
                inner.ordinal += 1
                inner.started_kinds.append(("inventory", "devpath", "snapshot", "root", "snapshot", "inventory")[inner.ordinal - 1])
                result = self.capture(argv, timeout, maximum)
                if inner.ordinal == 1:
                    rows = health.parse_inventory(health._decode_inventory(result, "initial inventory"))
                    inner.serial = health.select_exact_target(rows)["serial"]
                if binding is not None:
                    if inner.ordinal == 1 and digest(inner.serial.encode()) != binding["serial_sha256"]:
                        raise MarkerError("prepared serial changed before target read")
                    if inner.ordinal == 2 and digest(health._parse_devpath(result).encode()) != binding["topology_sha256"]:
                        raise MarkerError("prepared topology changed before root read")
                    if inner.ordinal == 3 and journal is not None and journal.has("reboot-intent"):
                        snapshot = health.parse_public_snapshot(result)
                        observe_return(journal, binding, digest(snapshot["boot_id"].encode()))
                return result
        backend = BoundReadiness()
        recorder = ready.Recorder(backend)
        try:
            result = ready.collect(recorder)
            self.serial = backend.serial
            return result
        finally:
            counts = recorder.evidence()
            for key in self.counts:
                self.counts[key] += counts[key]

    def capture(self, argv, timeout, maximum):
        self.last_capture = None
        try:
            result = ready.bounded_capture(argv, timeout, maximum)
        except ready.CaptureClosed as exc:
            self.last_capture = exc.capture
            raise
        code, stdout, stderr = result
        self.last_capture = {"returncode": code, "stdout_size": len(stdout), "stdout_sha256": digest(stdout), "stderr_size": len(stderr), "stderr_sha256": digest(stderr), "raw_published": False}
        return result

    def run(self, tail, timeout=20, maximum=8192):
        require_active()
        health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
        if self.serial is None:
            raise MarkerError("no selected target")
        self.counts["host_command_count"] += 1
        self.counts["selected_target_command_count"] += 1
        if "su" in tail:
            self.counts["root_command_count"] += 1
        return self.capture([health.EXPECTED_ADB_PATH, "-s", self.serial, *tail], timeout, maximum)

    def write(self, binding):
        return parse_write(self.run(["shell", "su", "-c", shlex.quote(write_script(binding))], 30), binding)

    def source_check(self, binding, expected_boot):
        snapshot = health.parse_public_snapshot(self.run(["exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT]))
        if digest(snapshot["boot_id"].encode()) != expected_boot:
            raise MarkerError("source boot changed immediately before action")
        return {"boot_id_sha256": expected_boot}

    def reboot(self):
        result = self.run(["reboot"])
        output = health._successful_stdout(result, label="ordinary reboot", maximum=8192)
        if output:
            raise MarkerError("unexpected reboot output")
        return {"returned": True, "stdout_sha256": digest(b""), "stderr_sha256": digest(b"")}

    def wait_return(self, binding, journal):
        deadline = time.monotonic() + WAIT_SECONDS
        for _ in range(MAX_POLLS):
            if time.monotonic() >= deadline:
                break
            require_active()
            health._validate_adb_receipt(health.base.tool_receipt(health.base.DEFAULT_ADB))
            self.counts["host_command_count"] += 1
            self.counts["inventory_command_count"] += 1
            result = self.capture([health.EXPECTED_ADB_PATH, "devices", "-l"], 5, 32768)
            rows = health.parse_inventory(health._decode_inventory(result, "return inventory"))
            bound_rows = [row for row in rows if digest(row["serial"].encode()) == binding["serial_sha256"]]
            if bound_rows and bound_rows[0]["state"] not in ("device", "offline"):
                raise MarkerError("unauthorized or unexpected bound return endpoint")
            if bound_rows and bound_rows[0]["state"] == "device":
                health.select_exact_target(rows)
            candidates = [row for row in rows if {"model:SM_G986N", "device:y2q", "product:y2qksx"} & row["metadata"]]
            if len(candidates) > 1:
                raise MarkerError("ambiguous return target")
            if candidates:
                row = candidates[0]
                if digest(row["serial"].encode()) != binding["serial_sha256"]:
                    raise MarkerError("return serial changed")
                if row["state"] == "device":
                    health.select_exact_target(rows)
                    topologies = [x for x in row["metadata"] if x.startswith("usb:")]
                    if len(topologies) != 1 or digest(topologies[0].encode()) != binding["topology_sha256"]:
                        raise MarkerError("return topology changed before selected read")
                    result = self.run(["exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT], 5)
                    output = health._successful_stdout(result, label="return public snapshot", maximum=8192)
                    snapshot = health._parse_ordered_lines(output, keys=health.PUBLIC_SNAPSHOT_KEYS, label="return public snapshot")
                    for key, value in (("model", "SM-G986N"), ("device", "y2q"), ("product_name", "y2qksx"), ("incremental", "G986NKSS8IYC2")):
                        if snapshot[key] != value:
                            raise MarkerError("return identity mismatch")
                    if snapshot["boot_completed"] == "1" and snapshot["bootanim"] == "stopped":
                        health.parse_public_snapshot(result)
                        boot = digest(snapshot["boot_id"].encode())
                        if boot != binding["source_boot_sha256"]:
                            observe_return(journal, binding, boot)
                            observation = self.preflight(binding, journal)
                            check_identity(observation, binding, changed_boot=True, expected_boot=boot)
                            return observation
            time.sleep(2)
        raise MarkerError("bounded Android return not observed")

    def read_marker(self, binding, boot):
        return parse_read(self.run(["shell", "su", "-c", shlex.quote(read_script(binding, boot))], 30))


def exact_data(actual, expected):
    return canonical(actual) == canonical(expected)


def validate_trial(journal):
    journal.validate_names()
    if journal.has("abort"):
        raise MarkerError("aborted trial cannot continue")
    binding = validate_binding(journal.get("binding"))
    bound = digest(canonical(binding))
    prerequisites = {
        "marker-result": "marker-intent", "reboot-intent": "marker-result",
        "reboot-result": "reboot-intent", "arrival": "reboot-intent",
        "read-intent": "arrival", "read-result": "read-intent", "observation-gap": "reboot-intent",
    }
    for event, prior in prerequisites.items():
        if journal.has(event) and not journal.has(prior):
            raise MarkerError("journal predecessor missing")
    expected = {
        "marker-intent": {"binding_sha256": bound, "script_sha256": digest(write_script(binding).encode())},
        "marker-result": {"returned": True, "stdout_sha256": digest(health.EXPECTED_ROOT_STDOUT + f'S20PMSG_WRITE_V1;returned=1;marker_sha256={digest(marker_bytes(binding))}\n'.encode()), "marker_sha256": digest(marker_bytes(binding))},
        "reboot-intent": {"binding_sha256": bound, "source_boot_sha256": binding["source_boot_sha256"]},
        "reboot-result": {"returned": True, "stdout_sha256": digest(b""), "stderr_sha256": digest(b"")},
    }
    for name, value in expected.items():
        if journal.has(name) and not exact_data(journal.get(name), value):
            raise MarkerError("journal effect binding mismatch")
    if journal.has("observation-gap") and not exact_data(journal.get("observation-gap"), {"binding_sha256": bound, "reason": "resume-without-durable-arrival"}):
        raise MarkerError("invalid observation gap")
    if journal.has("arrival"):
        arrival = journal.get("arrival")
        if type(arrival) is not dict or set(arrival) != {"boot_id_sha256"} or type(arrival["boot_id_sha256"]) is not str or re.fullmatch("[0-9a-f]{64}", arrival["boot_id_sha256"]) is None or arrival["boot_id_sha256"] == binding["source_boot_sha256"]:
            raise MarkerError("invalid first return boot")
        if journal.has("read-intent") and not exact_data(journal.get("read-intent"), {"binding_sha256": bound, **arrival}):
            raise MarkerError("reader boot/binding mismatch")
    if journal.has("read-result"):
        read = journal.get("read-result")
        if type(read) is not dict or set(read) != {"state", "matches", "size", "stdout_sha256"} or type(read["matches"]) is not int or type(read["size"]) is not int:
            raise MarkerError("reader result schema/type")
        raw = health.EXPECTED_ROOT_STDOUT + f'S20PMSG_READ_V1;state={read["state"]};matches={read["matches"]};size={read["size"]}\n'.encode()
        if not exact_data(read, parse_read((0, raw, b""))):
            raise MarkerError("reader result digest mismatch")
    return binding


def validate_terminal(journal):
    binding = validate_trial(journal)
    value = journal.get("terminal")
    keys = {"verdict", "binding_sha256", "return_boot_sha256", "marker_intent_consumed", "reboot_intent_consumed", "marker_match", "ordinary_reboot_attributed", "first_return_continuity", "native_pid1_proved", "download_recovery_retention_proved", "healthy", "replay_permitted", "command_counts_scope", "host_command_count", "selected_target_command_count", "inventory_command_count", "root_command_count", "s22plus_command_count", "a90_command_count", "other_target_command_count"}
    if type(value) is not dict or set(value) != keys:
        raise MarkerError("terminal schema")
    for key in ("marker_intent_consumed", "reboot_intent_consumed", "marker_match", "ordinary_reboot_attributed", "first_return_continuity", "native_pid1_proved", "download_recovery_retention_proved", "healthy", "replay_permitted"):
        if type(value[key]) is not bool:
            raise MarkerError("terminal bool type")
    for key in ("host_command_count", "selected_target_command_count", "inventory_command_count", "root_command_count", "s22plus_command_count", "a90_command_count", "other_target_command_count"):
        if type(value[key]) is not int or not 0 <= value[key] <= 256:
            raise MarkerError("terminal command count")
    proof = journal.has("read-result") and journal.get("read-result")["state"] == "scanned" and journal.get("read-result")["matches"] == 1
    attributed = journal.has("marker-result") and journal.has("reboot-result")
    if value["first_return_continuity"] != (not journal.has("observation-gap")):
        raise MarkerError("terminal observation-gap claim mismatch")
    if value["binding_sha256"] != digest(canonical(binding)) or value["marker_match"] != proof or value["ordinary_reboot_attributed"] != attributed or value["marker_intent_consumed"] != journal.has("marker-intent") or value["reboot_intent_consumed"] != journal.has("reboot-intent"):
        raise MarkerError("terminal claim mismatch")
    expected_verdict = "PROVED_PMSG_ORDINARY_REBOOT_RETENTION_HEALTHY" if proof and attributed and not journal.has("observation-gap") else "NO_PROOF_PMSG_TRIAL_HEALTHY"
    if value["verdict"] != expected_verdict or not value["healthy"] or value["native_pid1_proved"] or value["download_recovery_retention_proved"] or value["replay_permitted"] or value["command_counts_scope"] != "this_invocation" or any(value[k] for k in ("s22plus_command_count", "a90_command_count", "other_target_command_count")):
        raise MarkerError("terminal limits/claims")
    if type(value["return_boot_sha256"]) is not str or re.fullmatch("[0-9a-f]{64}", value["return_boot_sha256"]) is None:
        raise MarkerError("terminal boot digest grammar")
    if journal.has("arrival") and value["return_boot_sha256"] != journal.get("arrival")["boot_id_sha256"]:
        raise MarkerError("terminal return boot mismatch")
    if value["host_command_count"] != value["selected_target_command_count"] + value["inventory_command_count"] or value["root_command_count"] > value["selected_target_command_count"]:
        raise MarkerError("terminal count consistency")
    return value


def observe_return(journal, binding, boot):
    if type(boot) is not str or re.fullmatch("[0-9a-f]{64}", boot) is None or boot == binding["source_boot_sha256"]:
        raise MarkerError("invalid observed return boot")
    value = {"boot_id_sha256": boot}
    if journal.has("arrival"):
        if not exact_data(journal.get("arrival"), value):
            raise MarkerError("first observed return boot changed")
    else:
        journal.put("arrival", value)


def finish(journal, device, observation):
    binding = validate_trial(journal)
    rebooted = journal.has("reboot-intent")
    current_boot = check_identity(observation, binding, changed_boot=rebooted)
    proof = False
    if rebooted:
        if journal.has("arrival"):
            if journal.get("arrival") != {"boot_id_sha256": current_boot}:
                raise MarkerError("first observed return boot changed")
        else:
            journal.put("arrival", {"boot_id_sha256": current_boot})
        if not journal.has("read-intent"):
            journal.put("read-intent", {"binding_sha256": digest(canonical(binding)), "boot_id_sha256": current_boot})
            result = device.read_marker(binding, current_boot)
            journal.put("read-result", result)
        if journal.has("read-result"):
            result = journal.get("read-result")
            proof = result.get("state") == "scanned" and type(result.get("matches")) is int and result["matches"] == 1
    device.source_check(binding, current_boot)
    attributed = journal.has("marker-result") and journal.has("reboot-result")
    terminal = {
        "verdict": "PROVED_PMSG_ORDINARY_REBOOT_RETENTION_HEALTHY" if proof and attributed and not journal.has("observation-gap") else "NO_PROOF_PMSG_TRIAL_HEALTHY",
        "binding_sha256": digest(canonical(binding)), "return_boot_sha256": current_boot,
        "marker_intent_consumed": journal.has("marker-intent"), "reboot_intent_consumed": rebooted,
        "marker_match": proof, "ordinary_reboot_attributed": bool(attributed),
        "first_return_continuity": not journal.has("observation-gap"),
        "native_pid1_proved": False, "download_recovery_retention_proved": False,
        "healthy": True, "replay_permitted": False,
        "command_counts_scope": "this_invocation", **device.counts,
    }
    journal.put("terminal", terminal)
    return validate_terminal(journal)


def execute(journal, device):
    if any(journal.path.iterdir()):
        raise MarkerError("existing trial cannot execute again")
    observation = device.preflight()
    binding = make_binding(observation)
    journal.put("binding", binding)
    journal.put("marker-intent", {"binding_sha256": digest(canonical(binding)), "script_sha256": digest(write_script(binding).encode())})
    journal.validate_guard()
    validate_trial(journal)
    journal.put("marker-result", device.write(binding))
    device.source_check(binding, binding["source_boot_sha256"])
    journal.put("reboot-intent", {"binding_sha256": digest(canonical(binding)), "source_boot_sha256": binding["source_boot_sha256"]})
    journal.validate_guard()
    validate_trial(journal)
    journal.put("reboot-result", device.reboot())
    return finish(journal, device, device.wait_return(binding, journal))


def resume(journal, device):
    journal.validate_names()
    if journal.has("abort") or not journal.has("binding"):
        return abort_unbound(journal)
    if journal.has("terminal"):
        return validate_terminal(journal)
    binding = validate_trial(journal)
    if journal.has("reboot-intent") and not journal.has("arrival") and not journal.has("observation-gap"):
        journal.put("observation-gap", {"binding_sha256": digest(canonical(binding)), "reason": "resume-without-durable-arrival"})
    # Recovery is a single current health observation, with no wait, write or reboot.
    observation = device.preflight(binding, journal)
    return finish(journal, device, observation)


def guard_data():
    return {"schema": VERSION, "trial": str(PRIVATE_ROOT / "trial"), "unresolved": True}


def abort_unbound(journal):
    journal.validate_names()
    allowed = {"failure.json", "abort.json"}
    if any(p.name not in allowed for p in journal.path.iterdir()):
        raise MarkerError("bound or partial trial cannot use zero-effect abort")
    value = {"verdict": "STOP_PMSG_BEFORE_BINDING", "device_effects": 0, "health_claim": False, "replay_permitted": False}
    if journal.has("abort"):
        if not exact_data(journal.get("abort"), value):
            raise MarkerError("abort receipt mismatch")
    else:
        journal.put("abort", value)
    return value


@contextlib.contextmanager
def owned_trial(resuming):
    root = repo_root()
    parent = ensure_private_dirs(root, PRIVATE_ROOT)
    lock = os.open(parent / "owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(lock).st_mode) or os.fstat(lock).st_nlink != 1 or os.fstat(lock).st_uid != os.geteuid() or stat.S_IMODE(os.fstat(lock).st_mode) != 0o600:
            raise MarkerError("invalid owner lock")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = parent / "trial"
        if not resuming:
            path.mkdir(mode=0o700)
            health._fsync_directory(parent)
        if path.is_symlink() or not path.is_dir() or path.stat().st_uid != os.geteuid() or stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise MarkerError("indirect trial directory")
        journal = Journal(path)
        guard = root / SHARED_GUARD
        expected = guard_data()
        ensure_private_dirs(root, SHARED_GUARD.parent)
        if not resuming:
            try:
                publish(guard, expected)
            except Exception:
                # Only this invocation's still-empty trial may be removed.
                path.rmdir()
                health._fsync_directory(parent)
                raise
        elif os.path.lexists(guard):
            if not exact_data(read_node(guard), expected):
                raise MarkerError("foreign shared guard")
        elif not journal.has("terminal") and not journal.has("abort"):
            raise MarkerError("missing shared guard")
        yield journal
        if (journal.has("terminal") or journal.has("abort")) and os.path.lexists(guard):
            if not exact_data(read_node(guard), expected):
                raise MarkerError("guard changed")
            guard.unlink()
            health._fsync_directory(guard.parent)
    finally:
        os.close(lock)


def render_plan():
    return {"version": VERSION, "active": ACTIVE, "normalized_sha256": normalized_source(), "planned_marker_dispatches": 1, "planned_reboot_dispatches": 1, "wait_seconds": WAIT_SECONDS, "max_polls": MAX_POLLS, "record_maximum": RECORD_MAXIMUM, "device_commands": [], "root_writes": [], "mode": "H0", "resume_effects": [], "scope": "ordinary warm reboot only"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument("--render-plan", action="store_true")
    choices.add_argument("--connected", action="store_true")
    choices.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), indent=2))
        return 0
    try:
        require_active()
        with owned_trial(args.resume) as journal:
            device = Device()
            try:
                result = resume(journal, device) if args.resume else execute(journal, device)
            except Exception as exc:
                failure = {"error_class": type(exc).__name__, "error_sha256": digest(str(exc).encode()), "marker_intent_consumed": journal.has("marker-intent"), "reboot_intent_consumed": journal.has("reboot-intent"), "command_counts_scope": "this_invocation", **device.counts, "replay_permitted": False}
                if getattr(device, "last_capture", None) is not None:
                    failure["capture"] = device.last_capture
                if isinstance(exc, ready.CaptureClosed):
                    failure["capture"] = exc.capture
                if not journal.has("failure"):
                    journal.put("failure", failure)
                if not journal.has("binding"):
                    print(json.dumps(abort_unbound(journal)))
                    return 1
                print(json.dumps({"verdict": "PMSG_TRIAL_HEALTH_PENDING_NO_REPLAY", **failure}))
                return 1
            print(json.dumps(result))
            return 0
    except Exception as exc:
        print(json.dumps({"verdict": "STOP_PMSG_WARM_REBOOT_D1", "error_class": type(exc).__name__, "error_sha256": digest(str(exc).encode())}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
