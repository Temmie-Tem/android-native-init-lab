#!/usr/bin/env python3
"""Fixed S20+ /proc/last_kmsg record-format D0. Shape counts only, no log bytes."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import shlex
import stat
import subprocess
import time
from typing import Any

ACTIVE = False
VERSION = "s20plus-g986n-last-kmsg-record-format-d0-v2"
PRIVATE_ROOT = Path("workspace/private/runs/s20plus-g986n-last-kmsg-observation-d0")
CONTRACT_SECTION = "## S20+ last_kmsg Record-Format D0"
HEALTH_NAME = "s20plus_g986n_attended_root_health_d0.py"
HEALTH_SHA256 = "24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44"
ROOT_MAXIMUM = 8192
ROOT_TIMEOUT = 60.0

# The node is a Samsung sec_log window onto the previous boot's kernel log.
# CONFIG_SEC_LOG_BUF / SEC_LOG_LAST_KMSG / SEC_LOG_STORE_LAST_KMSG are set in the
# stock 4.19.113 kernel and the recorded readiness D0 observed this node as a
# readable regular file of 2,097,136 bytes = 2 MiB - 16.
NODE = "/proc/last_kmsg"
SCAN_MAXIMUM = 4194304
OBSERVED_SIZE = 2097136


class ObservationError(RuntimeError):
    pass


class CaptureClosed(ObservationError):
    def __init__(self, capture):
        super().__init__("bounded command " + capture["stop_reason"])
        self.capture = capture


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def load_health():
    path = Path(__file__).with_name(HEALTH_NAME)
    if path.is_symlink() or path.stat().st_nlink != 1:
        raise ObservationError("indirect health dependency")
    data = path.read_bytes()
    if len(data) != 39819 or digest(data) != HEALTH_SHA256:
        raise ObservationError("health dependency drift")
    spec = importlib.util.spec_from_file_location("_s20_last_kmsg_health_utilities", path)
    if spec is None or spec.loader is None:
        raise ObservationError("health dependency unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if path.read_bytes() != data:
        raise ObservationError("health dependency changed during load")
    return module


health = load_health()

# This capability answers exactly one question: what shape are the records in
# this buffer? It makes no claim about their content and identifies no boot.
#
# It exists because every predicate previously written here was a guess. No byte
# of this node has ever been read on this target, so the record prefix was
# inferred, and an anchor built on an inferred prefix fails in the worse
# direction: too strict, and a real record is silently not counted.
#
# So the patterns below are candidate *shapes*, deliberately overlapping, and
# their counts are the measurement. `seclog_cpu_field` is the one that matters
# most: Samsung sec_log commonly emits a second bracketed cpu/comm/pid field
# after the timestamp, and if it is present here then any anchor that expects
# the message immediately after the timestamp is wrong.
#
# Counts only. No log text is emitted, exactly as before.
SHAPES = {
    "lines_total": r"^",
    "priority_timestamp": r"^<[0-9]+>\[[ 0-9.]+\] ",
    "timestamp_only": r"^\[[ 0-9.]+\] ",
    "priority_only": r"^<[0-9]+>[^[]",
    "seclog_cpu_field": r"^(<[0-9]+>)?\[[ 0-9.]+\] \[[ 0-9]+:",
    "no_record_prefix": r"^[^<[]",
}
PREDICATES = SHAPES

# Every branch emits every key exactly once and in this order, so a short or
# reordered transcript is a parse failure rather than a silent partial read.
# grep exits nonzero on a zero count, which `set -e` would otherwise treat as a
# script failure, hence the explicit `|| key=0` on each assignment.
SHELL_HELPERS = f"""
export LC_ALL=C
[ "$uid" = 0 ] && [ "$gid" = 0 ] && [ "$context" = u:r:magisk:s0 ] || exit 64
[ "$magisk_version" = 30.7:MAGISK:R ] && [ "$magisk_version_code" = 30700 ] || exit 64
[ "$selinux" = Enforcing ] && [ "$pid1_exe" = /system/bin/init ] && [ "$pid1_context" = u:r:init:s0 ] || exit 64
emit() {{ /system/bin/printf '%s=%s\\n' "$1" "$2"; }}
node={shlex.quote(NODE)}
state=unavailable
meta=0:0
bounded=no
window=none
recheck=none
scanned=-1
meta_after=0:0
{chr(10).join(f'{key}=0' for key in PREDICATES)}
if [ -L "$node" ]; then state=indirect
elif [ ! -e "$node" ]; then state=unavailable
elif [ ! -f "$node" ]; then state=unexpected
elif [ ! -r "$node" ]; then state=unreadable
else
    state=regular
    meta=$(/system/bin/stat -c '%s:%h' "$node") || exit 65
    if [ "${{meta%%:*}}" -le {SCAN_MAXIMUM} ]; then
        bounded=yes
        # A pipeline hides an upstream failure: `head` can stop short and
        # `sha256sum` still succeeds over the partial bytes. Count what was
        # actually read and let the host require it to equal the stat size, so a
        # truncated read cannot become a valid digest or a zero predicate count.
        scanned=$(/system/bin/head -c {SCAN_MAXIMUM} "$node" | /system/bin/wc -c) || exit 65
        window=$(/system/bin/head -c {SCAN_MAXIMUM} "$node" | /system/bin/sha256sum) || exit 65
"""
SHELL_HELPERS += "".join(
    f"        {key}=$(/system/bin/head -c {SCAN_MAXIMUM} \"$node\" | /system/bin/grep -aEc {shlex.quote(pattern)}) || {key}=0\n"
    for key, pattern in PREDICATES.items()
)
SHELL_HELPERS += f"""        recheck=$(/system/bin/head -c {SCAN_MAXIMUM} "$node" | /system/bin/sha256sum) || exit 65
        # Re-stat after the passes. A buffer that grew past the cap keeps an
        # identical prefix digest, so the digests alone cannot see it; the size
        # and link count can.
        meta_after=$(/system/bin/stat -c '%s:%h' "$node") || exit 65
    fi
fi
emit state "$state"
emit meta "$meta"
emit bounded "$bounded"
emit scanned "$scanned"
emit window "$window"
emit recheck "$recheck"
emit meta_after "$meta_after"
"""
SHELL_HELPERS += "".join(f'emit {key} "${key}"\n' for key in PREDICATES)

ROOT_SCRIPT = health.ROOT_READ_SCRIPT + SHELL_HELPERS
ROOT_ARGUMENT = shlex.quote(ROOT_SCRIPT)
OUTPUT_KEYS = (
    *health.ROOT_OUTPUT_KEYS,
    "state", "meta", "bounded", "scanned", "window", "recheck", "meta_after",
    *PREDICATES,
)


def source_receipt() -> dict[str, Any]:
    data, receipt = health._read_direct_regular_source(Path(__file__))
    normalized, count = re.subn(rb"^ACTIVE = (?:True|False)$", b"ACTIVE = <BOOLEAN>", data, flags=re.M)
    if count != 1:
        raise ObservationError("ambiguous activation atom")
    return {**receipt, "normalized_sha256": digest(normalized)}


def require_active() -> None:
    if not ACTIVE:
        raise ObservationError("last_kmsg observation D0 is dormant")
    contract = repo_root() / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
    data, _ = health._read_direct_regular_source(contract)
    text = data.decode()
    if text.count(CONTRACT_SECTION + "\n") != 1:
        raise ObservationError("missing unique last_kmsg contract")
    section = text.split(CONTRACT_SECTION + "\n", 1)[1].split("\n## ", 1)[0]
    for line in (
        "Status: **BINDING - LAST_KMSG RECORD-FORMAT D0 ACTIVE**",
        "Runner-Normalized-SHA256: `" + source_receipt()["normalized_sha256"] + "`",
        "Root-Script-SHA256: `" + digest(ROOT_SCRIPT.encode()) + "`",
    ):
        if section.splitlines().count(line) != 1:
            raise ObservationError("last_kmsg contract/source activation mismatch")
    health._direct_regular_receipt(Path(__file__).with_name(HEALTH_NAME), expected_size=39819, expected_sha256=HEALTH_SHA256)
    health._direct_regular_receipt(Path(__file__).with_name(health.INVENTORY_HELPER_NAME), expected_size=health.INVENTORY_HELPER_SIZE, expected_sha256=health.INVENTORY_HELPER_SHA256)


def parse_root(result: tuple[int, bytes, bytes]) -> dict[str, Any]:
    stdout = health._successful_stdout(result, label="last_kmsg observation", maximum=ROOT_MAXIMUM)
    values = health._parse_ordered_lines(stdout, keys=OUTPUT_KEYS, label="last_kmsg observation")
    if any(values[k] != v for k, v in health.EXPECTED_ROOT_OUTPUT.items()):
        raise ObservationError("root health mismatch")
    state = values["state"]
    if state not in ("regular", "indirect", "unavailable", "unexpected", "unreadable"):
        raise ObservationError("invalid node state")
    facts: dict[str, Any] = {"node": NODE, "state": state, "scan_maximum": SCAN_MAXIMUM, "log_contents_emitted": False}
    meta = re.fullmatch(r"(0|[1-9][0-9]{0,9}):([0-9]+)", values["meta"])
    if meta is None:
        raise ObservationError("invalid node metadata")
    facts["size"] = int(meta[1])
    facts["links"] = int(meta[2])
    if values["bounded"] not in ("yes", "no"):
        raise ObservationError("invalid scan bound")
    facts["bounded"] = values["bounded"] == "yes"
    # The shell can only report bounded for a regular node within the cap, so any
    # other combination is a transcript the script cannot have produced.
    if facts["bounded"] != (state == "regular" and facts["size"] <= SCAN_MAXIMUM):
        raise ObservationError("scan bound contradicts the observed node")
    if state == "regular" and facts["links"] != 1:
        raise ObservationError("node is not a direct regular file")
    if facts["bounded"]:
        window = re.fullmatch(r"([0-9a-f]{64}) +-", values["window"])
        if window is None:
            raise ObservationError("invalid scan window digest")
        # The node is read once per predicate. A consuming interface would empty
        # after the first pass and a growing one would drift, so the window is
        # digested again after the last predicate and must be unchanged.
        if values["recheck"] != values["window"]:
            raise ObservationError("scan window changed across the predicate passes")
        # A pipeline can hide a short read: head stops early and sha256sum still
        # succeeds. Requiring the counted bytes to equal the stat size makes a
        # truncated pass a failure rather than a valid digest with zero hits.
        if not re.fullmatch(r"0|[1-9][0-9]{0,9}", values["scanned"]):
            raise ObservationError("invalid scanned byte count")
        facts["scanned"] = int(values["scanned"])
        if facts["scanned"] != facts["size"]:
            raise ObservationError("scan read fewer bytes than the node reports")
        # Identical prefix digests cannot see growth past the cap; the size can.
        if values["meta_after"] != values["meta"]:
            raise ObservationError("node metadata changed across the scan")
        facts["window_sha256"] = window[1]
        facts["window_stable_across_passes"] = True
        facts["scan_complete"] = True
    elif (
        values["window"] != "none"
        or values["recheck"] != "none"
        or values["scanned"] != "-1"
        or values["meta_after"] != "0:0"
    ):
        raise ObservationError("unscanned window reported scan evidence")
    counts: dict[str, int] = {}
    for key in PREDICATES:
        if not re.fullmatch(r"0|[1-9][0-9]{0,8}", values[key]):
            raise ObservationError("invalid predicate count: " + key)
        counts[key] = int(values[key])
    if not facts["bounded"] and any(counts.values()):
        raise ObservationError("unscanned window reported predicate hits")
    facts["shape_counts"] = counts
    # No semantic fact is derived here. This capability reports what the records
    # look like; it does not say what they mean, which boot produced them, or
    # whether anything was retained. Those claims were withdrawn because every
    # one of them rested on a record format that has never been read on this
    # target.
    facts["dominant_shape"] = _dominant_shape(counts)
    facts["seclog_cpu_field_present"] = counts["seclog_cpu_field"] >= 1
    facts["size_matches_recorded_observation"] = facts["size"] == OBSERVED_SIZE
    return facts


def _dominant_shape(counts: dict[str, int]) -> str:
    """Which candidate prefix shape actually describes this buffer.

    Reported rather than asserted: if no shape accounts for most lines, that is
    itself the finding, and designing an anchor on any of them would be the same
    guess this capability exists to replace.
    """
    total = counts["lines_total"]
    if total == 0:
        return "no-records"
    ranked = sorted(
        ((name, counts[name]) for name in SHAPES if name != "lines_total"),
        key=lambda item: item[1],
        reverse=True,
    )
    name, count = ranked[0]
    if count * 2 <= total:
        return "no-dominant-shape"
    return name


def channel_verdict(facts: dict[str, Any]) -> str:
    """Name the measurement, never a conclusion.

    Every verdict here is about the record format. None of them says the buffer
    is retained, says which boot produced it, or says anything ran.
    """
    if facts["state"] != "regular":
        return "NODE_ABSENT_OR_UNREADABLE"
    if not facts["bounded"]:
        return "NODE_TOO_LARGE_TO_SCAN"
    if facts["shape_counts"]["lines_total"] == 0:
        return "SCANNED_NO_RECORDS"
    if facts["seclog_cpu_field_present"]:
        # The finding that would invalidate an anchor expecting the message
        # immediately after the timestamp.
        return "RECORDS_CARRY_A_SECLOG_CPU_FIELD"
    if facts["dominant_shape"] == "no-dominant-shape":
        return "RECORDS_HAVE_NO_DOMINANT_SHAPE"
    return "RECORDS_DOMINANTLY_" + facts["dominant_shape"].upper()


class FixedBackend:
    """One fixed inventory/devpath/pre/root/post/inventory command sequence."""
    def __init__(self):
        require_active()
        self.ordinal = 0
        self.serial: str | None = None
        self.started_kinds: list[str] = []

    def tool_receipt(self):
        require_active()
        return health.base.tool_receipt(health.base.DEFAULT_ADB)

    def run(self, argv, timeout, maximum):
        require_active()
        adb = health.EXPECTED_ADB_PATH
        shapes = [
            ([adb, "devices", "-l"], 10.0, 32768),
            ([adb, "-s", self.serial, "get-devpath"], 10.0, 32768),
            ([adb, "-s", self.serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT], 20.0, 8192),
            ([adb, "-s", self.serial, "shell", "su", "-c", ROOT_ARGUMENT], ROOT_TIMEOUT, ROOT_MAXIMUM),
            ([adb, "-s", self.serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT], 20.0, 8192),
            ([adb, "devices", "-l"], 10.0, 32768),
        ]
        if self.ordinal >= len(shapes) or (argv, timeout, maximum) != shapes[self.ordinal]:
            raise ObservationError("command outside fixed sequence")
        self.ordinal += 1  # no retry even if the command raises
        self.started_kinds.append(("inventory", "devpath", "snapshot", "root", "snapshot", "inventory")[self.ordinal - 1])
        result = bounded_capture(argv, timeout, maximum)
        if self.ordinal == 1:
            rows = health.parse_inventory(health._decode_inventory(result, "initial inventory"))
            self.serial = health.select_exact_target(rows)["serial"]
        return result


def bounded_capture(argv, timeout, maximum):
    """Internal fixed-backend capture; failures retain digests, never raw bytes."""
    require_active()
    if not argv or not 0.1 <= timeout <= 120 or not 1 <= maximum <= 32768:
        raise ObservationError("invalid capture bounds")
    buffers = [bytearray(), bytearray()]
    reason = None
    truncated = False
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, 0)
            selector.register(process.stderr, selectors.EVENT_READ, 1)
            deadline = time.monotonic() + timeout
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    reason = "timed out"
                    break
                for key, _ in selector.select(remaining):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffer = buffers[key.data]
                    if len(buffer) + len(chunk) > maximum:
                        buffer.extend(chunk[: maximum - len(buffer)])
                        truncated = True
                        reason = reason or "exceeded output bound"
                    else:
                        buffer.extend(chunk)
                if truncated:
                    break
    finally:
        if reason is not None:
            process.kill()
        returncode = process.wait()
        process.stdout.close()
        process.stderr.close()
    if reason is not None:
        raise CaptureClosed({
            "schema": "s20plus_g986n_last_kmsg_capture_v1", "stop_reason": reason,
            "returncode": returncode, "stdout_size": len(buffers[0]), "stderr_size": len(buffers[1]),
            "stdout_sha256": digest(bytes(buffers[0])), "stderr_sha256": digest(bytes(buffers[1])),
            "raw_published": False,
        })
    return returncode, bytes(buffers[0]), bytes(buffers[1])


class Recorder(health.CommandRecorder):
    def run(self, kind, argv, timeout, maximum):
        try:
            return super().run(kind, argv, timeout, maximum)
        except CaptureClosed as exc:
            if kind == "root":
                self.root_transcript_digest = exc.capture
            raise

    def evidence(self):
        result = super().evidence()
        kinds = getattr(self.backend, "started_kinds", None)
        if type(kinds) is list:
            result.update(host_command_count=len(kinds), inventory_command_count=kinds.count("inventory"), selected_target_command_count=len(kinds) - kinds.count("inventory"), public_snapshot_command_count=kinds.count("snapshot"), root_command_count=kinds.count("root"))
        return result


def collect(recorder) -> dict[str, Any]:
    require_active()
    before_source = source_receipt()
    tool = health._validate_adb_receipt(recorder.backend.tool_receipt())
    adb = tool["path"]
    rows = health.parse_inventory(health._decode_inventory(recorder.run("inventory", [adb, "devices", "-l"], 10.0, 32768), "initial inventory"))
    selected = health.select_exact_target(rows)
    serial = selected["serial"]
    devpath = health._parse_devpath(recorder.run("devpath", [adb, "-s", serial, "get-devpath"], 10.0, 32768))
    health._validate_devpath_binding(selected, devpath)
    public_argv = [adb, "-s", serial, "exec-out", "sh", "-c", health.PUBLIC_SHELL_ARGUMENT]
    before = health.parse_public_snapshot(recorder.run("snapshot", public_argv, 20.0, 8192))
    health._validate_snapshot_binding(before, selected)
    root_result = recorder.run("root", [adb, "-s", serial, "shell", "su", "-c", ROOT_ARGUMENT], ROOT_TIMEOUT, ROOT_MAXIMUM)
    rc, stdout, stderr = health._command_envelope(root_result, label="last_kmsg observation", maximum=ROOT_MAXIMUM)
    recorder.observe_root_transcript(rc, stdout, stderr)
    health._assert_private_tokens_absent(stdout, stderr, health._privacy_tokens(rows, devpath, before["boot_id"]))
    facts = parse_root(root_result)
    after = health.parse_public_snapshot(recorder.run("snapshot", public_argv, 20.0, 8192))
    if after != before:
        raise ObservationError("target or current boot changed across observation")
    final = health.parse_inventory(health._decode_inventory(recorder.run("inventory", [adb, "devices", "-l"], 10.0, 32768), "final inventory"))
    final_selected = health.select_exact_target(final)
    health._validate_devpath_binding(final_selected, devpath)
    if final_selected["serial"] != serial or health.base.sanitized_inventory(final) != health.base.sanitized_inventory(rows):
        raise ObservationError("global inventory changed")
    if tool != health._validate_adb_receipt(recorder.backend.tool_receipt()) or source_receipt() != before_source:
        raise ObservationError("host source or tool changed")
    return {
        "schema": VERSION, "verdict": "PASS_S20PLUS_G986N_LAST_KMSG_OBSERVATION_D0_OBSERVED",
        "channel": channel_verdict(facts),
        "target": {k: v for k, v in before.items() if k != "boot_id"},
        "binding": {"serial_sha256": digest(serial.encode()), "topology_sha256": digest(devpath.encode()), "boot_id_sha256": digest(before["boot_id"].encode())},
        "facts": facts, "root_transcript_digest": recorder.root_transcript_digest,
        "source": before_source, "health_dependency_sha256": HEALTH_SHA256,
        "inventory_dependency": health.INVENTORY_HELPER_RECEIPT,
        "root_script_sha256": digest(ROOT_SCRIPT.encode()), "host_tool": tool,
        **recorder.evidence(), "device_effect_count": 0, "device_writes": False,
        "reboot_requested": False, "partition_access": False,
        "log_contents_read": False, "log_bytes_retained": 0,
        # This capability measures record format and nothing else. It does not
        # establish retention, does not identify a boot, and proves nothing ran.
        "record_format_measured": True,
        "dominant_shape": facts["dominant_shape"],
        "retention_proved": False, "native_pid1_proved": False,
        "boot_identified": False, "content_interpreted": False,
    }


def allocate_evidence():
    current = repo_root().resolve(strict=True)
    for part in PRIVATE_ROOT.parts:
        child = current / part
        try:
            child.mkdir(mode=0o700)
            health._fsync_directory(current)
        except FileExistsError:
            pass
        info = child.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise ObservationError("indirect or foreign evidence directory")
        current = child
    if stat.S_IMODE(current.stat().st_mode) != 0o700:
        raise ObservationError("private evidence root must be 0700")
    run = current / ("d0-" + secrets.token_hex(16))
    run.mkdir(mode=0o700)
    fd = os.open(run, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    health._fsync_directory(current)
    return health.EvidenceOwner(run, fd, health._directory_identity(os.fstat(fd)))


def render_plan():
    return {
        "schema": VERSION, "active": ACTIVE, "mode": "H0-render-plan",
        "device_commands": [], "device_effects": [], "retention_proved": False,
        "planned_host_commands": 6, "planned_root_commands": 1,
        "root_script_sha256": digest(ROOT_SCRIPT.encode()),
        "root_script_bytes": len(ROOT_SCRIPT.encode()), "root_timeout_seconds": ROOT_TIMEOUT,
        "root_output_maximum_bytes": ROOT_MAXIMUM,
        "observed_node": NODE, "scan_maximum_bytes": SCAN_MAXIMUM,
        "recorded_observed_size": OBSERVED_SIZE,
        "predicates": dict(PREDICATES), "log_contents_read": False,
        "log_bytes_crossing_boundary": 0, "log_bytes_retained": 0,
        "device_writes": False, "reboot_requested": False, "partition_access": False,
        "normalized_sha256": source_receipt()["normalized_sha256"],
        "private_root": str(PRIVATE_ROOT),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render-plan", action="store_true")
    mode.add_argument("--connected", action="store_true")
    args = parser.parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), indent=2))
        return 0
    recorder = None
    try:
        require_active()
        with allocate_evidence() as evidence:
            recorder = Recorder(FixedBackend())
            try:
                result = collect(recorder)
                receipt = evidence.publish_json("result.json", result)
            except Exception as exc:
                result = health.failure_result(recorder, exc, None)
                result.update(schema=VERSION, verdict="FAIL_S20PLUS_G986N_LAST_KMSG_OBSERVATION_D0_CLOSED")
                if isinstance(exc, CaptureClosed):
                    result["last_command_capture"] = exc.capture
                receipt = evidence.publish_json("failure.json", result)
                print(json.dumps({"verdict": result["verdict"], "result_sha256": receipt["sha256"], "run": str(evidence.path), **recorder.evidence()}))
                return 1
            print(json.dumps({"verdict": result["verdict"], "channel": result["channel"], "result_sha256": receipt["sha256"], "run": str(evidence.path), **recorder.evidence()}))
            return 0
    except Exception as exc:
        print(json.dumps({"verdict": "STOP_S20PLUS_G986N_LAST_KMSG_OBSERVATION_D0", "error_class": type(exc).__name__, "error_sha256": digest(str(exc).encode())}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
