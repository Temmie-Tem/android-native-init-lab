#!/usr/bin/env python3
"""Fixed S20+ pstore/PMSG metadata D0. No log reads or device writes."""
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

ACTIVE = True
VERSION = "s20plus-g986n-pstore-readiness-d0-v1"
PRIVATE_ROOT = Path("workspace/private/runs/s20plus-g986n-pstore-readiness-d0")
CONTRACT_SECTION = "## S20+ Pstore/PMSG Readiness D0"
HEALTH_NAME = "s20plus_g986n_attended_root_health_d0.py"
HEALTH_SHA256 = "24f69cc5aa43c70558e3594534ee684db0a038e972d1b0db2f1b8d8446af2d44"
ROOT_MAXIMUM = 8192
ROOT_TIMEOUT = 30.0


class ReadinessError(RuntimeError):
    pass


class CaptureClosed(ReadinessError):
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
        raise ReadinessError("indirect health dependency")
    data = path.read_bytes()
    if len(data) != 39819 or digest(data) != HEALTH_SHA256:
        raise ReadinessError("health dependency drift")
    spec = importlib.util.spec_from_file_location("_s20_pstore_health_utilities", path)
    if spec is None or spec.loader is None:
        raise ReadinessError("health dependency unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if path.read_bytes() != data:
        raise ReadinessError("health dependency changed during load")
    return module


health = load_health()

# One declaration generates the fixed shell and the ordered parser surface.
# These are kernel-owned metadata, not user files or log contents.
DT_ROOT = "/sys/firmware/devicetree/base"
RAM_NODE = DT_ROOT + "/reserved-memory/ramoops@9FA00000"
HEX_READS = {
    "dt_compatible": RAM_NODE + "/compatible",
    "dt_reg": RAM_NODE + "/reg",
    "dt_record_size": RAM_NODE + "/record-size",
    "dt_console_size": RAM_NODE + "/console-size",
    "dt_ftrace_size": RAM_NODE + "/ftrace-size",
    "dt_pmsg_size": RAM_NODE + "/pmsg-size",
    "dt_status": RAM_NODE + "/status",
    "dt_parent_status": DT_ROOT + "/reserved-memory/status",
    "dt_root_status": DT_ROOT + "/status",
    "backend": "/sys/module/pstore/parameters/backend",
    "ram_mem_size": "/sys/module/ramoops/parameters/mem_size",
    "ram_record_size": "/sys/module/ramoops/parameters/record_size",
    "ram_console_size": "/sys/module/ramoops/parameters/console_size",
    "ram_ftrace_size": "/sys/module/ramoops/parameters/ftrace_size",
    "ram_pmsg_size": "/sys/module/ramoops/parameters/pmsg_size",
    "pmsg_class_dev": "/sys/devices/virtual/pmsg/pmsg0/dev",
    "watchdog_pet_time": "/sys/bus/platform/devices/17c10000.qcom,wdt/pet_time",
    "watchdog_user_pet_enabled": "/sys/bus/platform/devices/17c10000.qcom,wdt/user_pet_enabled",
}
LINK_READS = {
    "ram_driver": "/sys/bus/platform/devices/9fa00000.ramoops/driver",
}
META_READS = {
    "console_record": "/sys/fs/pstore/console-ramoops-0",
    "pmsg_record": "/sys/fs/pstore/pmsg-ramoops-0",
    "dmesg_record": "/sys/fs/pstore/dmesg-ramoops-0",
    "last_kmsg": "/proc/last_kmsg",
}

SHELL_HELPERS = r"""
export LC_ALL=C
[ "$uid" = 0 ] && [ "$gid" = 0 ] && [ "$context" = u:r:magisk:s0 ] || exit 64
[ "$magisk_version" = 30.7:MAGISK:R ] && [ "$magisk_version_code" = 30700 ] || exit 64
[ "$selinux" = Enforcing ] && [ "$pid1_exe" = /system/bin/init ] && [ "$pid1_context" = u:r:init:s0 ] || exit 64
emit() { printf '%s=%s\n' "$1" "$2"; }
hex_read() {
    key=$1; node=$2
    if [ -L "$node" ]; then emit "$key" indirect; return; fi
    if [ ! -e "$node" ]; then
        parent=${node%/*}
        if [ -d "$parent" ] && [ -r "$parent" ] && [ -x "$parent" ]; then emit "$key" absent
        else emit "$key" unavailable; fi
        return
    fi
    if [ ! -f "$node" ]; then emit "$key" unexpected; return; fi
    if [ ! -r "$node" ]; then emit "$key" unreadable; return; fi
    before=$(/system/bin/stat -c '%d:%i:%f:%h' "$node") || exit 65
    if ! value=$(/system/bin/od -An -v -tx1 -N 65 "$node"); then emit "$key" unreadable; return; fi
    value=$(printf '%s' "$value" | /system/bin/tr -d ' \n')
    after=$(/system/bin/stat -c '%d:%i:%f:%h' "$node") || exit 65
    [ "$before" = "$after" ] || { emit "$key" changed; return; }
    [ "${#value}" -le 128 ] || { emit "$key" oversized; return; }
    emit "$key" "hex:$value"
}
link_read() {
    key=$1; node=$2
    if [ ! -L "$node" ]; then emit "$key" unavailable; return; fi
    value=$(/system/bin/readlink -f "$node") || { emit "$key" unreadable; return; }
    if [ "$value" = /sys/bus/platform/drivers/ramoops ]; then emit "$key" ramoops
    else emit "$key" mismatch; fi
}
meta_read() {
    key=$1; node=$2
    if [ -L "$node" ]; then emit "$key" indirect; return; fi
    if [ ! -e "$node" ]; then emit "$key" unavailable; return; fi
    if [ ! -f "$node" ]; then emit "$key" unexpected; return; fi
    if [ ! -r "$node" ]; then emit "$key" unreadable; return; fi
    value=$(/system/bin/stat -c '%s:%h' "$node") || exit 65
    emit "$key" "regular:$value"
}
pmsg_node() {
    node=/dev/pmsg0
    if [ -L "$node" ]; then emit pmsg_node indirect; return; fi
    if [ ! -e "$node" ]; then emit pmsg_node unavailable; return; fi
    if [ ! -c "$node" ]; then emit pmsg_node unexpected; return; fi
    value=$(/system/bin/stat -c '%t:%T:%h' "$node") || exit 65
    emit pmsg_node "char:$value"
}
pstore_mount() {
    if ! value=$(/system/bin/head -c 65537 /proc/self/mounts && printf .); then emit pstore_mount unreadable; return; fi
    value=${value%.}
    [ "${#value}" -le 65536 ] || { emit pstore_mount oversized; return; }
    printf '%s' "$value" | (
        count=0; valid=0
        while IFS=' ' read -r source target kind remainder; do
            if [ "$target" = /sys/fs/pstore ]; then
                count=$((count + 1))
                if [ "$kind" = pstore ]; then valid=$((valid + 1)); fi
            fi
        done
        if [ "$count" = 0 ]; then emit pstore_mount unmounted
        elif [ "$count" = 1 ] && [ "$valid" = 1 ]; then emit pstore_mount mounted
        else emit pstore_mount conflict; fi
    )
}
"""
ROOT_SCRIPT = health.ROOT_READ_SCRIPT + SHELL_HELPERS + "".join(
    f"{function} {shlex.quote(key)} {shlex.quote(path)}\n"
    for function, fields in (("hex_read", HEX_READS), ("link_read", LINK_READS), ("meta_read", META_READS))
    for key, path in fields.items()
) + "pmsg_node\npstore_mount\n"
ROOT_ARGUMENT = shlex.quote(ROOT_SCRIPT)
OUTPUT_KEYS = (*health.ROOT_OUTPUT_KEYS, *HEX_READS, *LINK_READS, *META_READS, "pmsg_node", "pstore_mount")


def source_receipt() -> dict[str, Any]:
    data, receipt = health._read_direct_regular_source(Path(__file__))
    normalized, count = re.subn(rb"^ACTIVE = (?:True|False)$", b"ACTIVE = <BOOLEAN>", data, flags=re.M)
    if count != 1:
        raise ReadinessError("ambiguous activation atom")
    return {**receipt, "normalized_sha256": digest(normalized)}


def require_active() -> None:
    if not ACTIVE:
        raise ReadinessError("pstore readiness D0 is dormant")
    contract = repo_root() / "docs/operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md"
    data, _ = health._read_direct_regular_source(contract)
    text = data.decode()
    if text.count(CONTRACT_SECTION + "\n") != 1:
        raise ReadinessError("missing unique pstore contract")
    section = text.split(CONTRACT_SECTION + "\n", 1)[1].split("\n## ", 1)[0]
    for line in (
        "Status: **BINDING - PSTORE READINESS D0 ACTIVE**",
        "Runner-Normalized-SHA256: `" + source_receipt()["normalized_sha256"] + "`",
        "Root-Script-SHA256: `" + digest(ROOT_SCRIPT.encode()) + "`",
    ):
        if section.splitlines().count(line) != 1:
            raise ReadinessError("pstore contract/source activation mismatch")
    health._direct_regular_receipt(Path(__file__).with_name(HEALTH_NAME), expected_size=39819, expected_sha256=HEALTH_SHA256)
    health._direct_regular_receipt(Path(__file__).with_name(health.INVENTORY_HELPER_NAME), expected_size=health.INVENTORY_HELPER_SIZE, expected_sha256=health.INVENTORY_HELPER_SHA256)


def parse_root(result: tuple[int, bytes, bytes]) -> dict[str, Any]:
    stdout = health._successful_stdout(result, label="pstore metadata", maximum=ROOT_MAXIMUM)
    values = health._parse_ordered_lines(stdout, keys=OUTPUT_KEYS, label="pstore metadata")
    if any(values[k] != v for k, v in health.EXPECTED_ROOT_OUTPUT.items()):
        raise ReadinessError("root health mismatch")
    facts: dict[str, Any] = {}
    for key in HEX_READS:
        value = values[key]
        if value in ("absent", "unavailable", "unreadable"):
            facts[key] = {"state": value}
            continue
        if not re.fullmatch(r"hex:(?:[0-9a-f]{2}){0,64}", value):
            raise ReadinessError("invalid or unsafe metadata field: " + key)
        data = bytes.fromhex(value[4:])
        if key.startswith("dt_"):
            expected = {
                "dt_compatible": b"ramoops\0",
                "dt_reg": bytes.fromhex("000000009fa000000000000000100000"),
            }.get(key, bytes.fromhex("00040000"))
            match = data in (b"ok\0", b"okay\0") if key.endswith("status") else data == expected
            facts[key] = {"state": "observed", "matches_expected": match, "sha256": digest(data)}
        elif key == "backend":
            facts[key] = {"state": "observed", "matches_expected": data == b"ramoops\n"}
        elif key == "pmsg_class_dev":
            if not re.fullmatch(rb"(?:0|[1-9][0-9]{0,3}):(?:0|[1-9][0-9]{0,6})\n", data):
                raise ReadinessError("malformed PMSG class device")
            major, minor = map(int, data.strip().split(b":"))
            if major > 4095 or minor > 1048575:
                raise ReadinessError("PMSG device range")
            facts[key] = {"state": "observed", "major": major, "minor": minor}
        else:
            if not re.fullmatch(rb"(?:0|[1-9][0-9]{0,8})\n", data):
                raise ReadinessError("malformed numeric metadata: " + key)
            number = int(data)
            if key == "watchdog_user_pet_enabled" and number not in (0, 1):
                raise ReadinessError("invalid watchdog boolean")
            facts[key] = {"state": "observed", "value": number}
    if values["ram_driver"] not in ("ramoops", "mismatch", "unavailable", "unreadable"):
        raise ReadinessError("invalid driver state")
    facts["ram_driver"] = values["ram_driver"]
    for key in META_READS:
        value = values[key]
        if value in ("unavailable", "unreadable"):
            facts[key] = {"state": value}
        else:
            match = re.fullmatch(r"regular:(0|[1-9][0-9]{0,8}):1", value)
            if match is None or int(match[1]) > 64 * 1024 * 1024:
                raise ReadinessError("invalid record metadata: " + key)
            facts[key] = {"state": "regular-access-check-only", "size": int(match[1]), "content_read": False}
    value = values["pmsg_node"]
    node = re.fullmatch(r"char:([0-9a-f]{1,3}):([0-9a-f]{1,5}):1", value)
    if node:
        facts["pmsg_node"] = {"state": "observed", "major": int(node[1], 16), "minor": int(node[2], 16)}
    elif value in ("unavailable", "unreadable"):
        facts["pmsg_node"] = {"state": value}
    else:
        raise ReadinessError("invalid PMSG character metadata")
    if values["pstore_mount"] not in ("mounted", "unmounted", "unreadable", "conflict"):
        raise ReadinessError("invalid or oversized mount observation")
    facts["pstore_mount"] = values["pstore_mount"]
    geometry = all(facts[k].get("matches_expected", False) for k in HEX_READS if k.startswith("dt_") and not k.endswith("status"))
    statuses = all(facts[k].get("matches_expected", False) or facts[k]["state"] == "absent" for k in ("dt_status", "dt_parent_status", "dt_root_status"))
    parameters = all(facts[k].get("value") == (1048576 if k == "ram_mem_size" else 262144) for k in HEX_READS if k.startswith("ram_"))
    pmsg_matches = facts["pmsg_node"]["state"] == "observed" and facts["pmsg_node"] == facts["pmsg_class_dev"]
    facts["metadata_ready"] = bool(geometry and statuses and parameters and pmsg_matches and facts["backend"].get("matches_expected", False) and facts["ram_driver"] == "ramoops" and facts["pstore_mount"] == "mounted")
    return facts


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
            raise ReadinessError("command outside fixed sequence")
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
    if not argv or not 0.1 <= timeout <= 60 or not 1 <= maximum <= 32768:
        raise ReadinessError("invalid capture bounds")
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
                if time.monotonic() >= deadline:
                    reason = "timeout"
                    break
                for key, _ in selector.select(min(0.05, max(0, deadline - time.monotonic()))):
                    remaining = maximum - sum(map(len, buffers))
                    chunk = os.read(key.fd, min(8192, remaining + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffers[key.data].extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        reason = "output_limit"
                        truncated = True
                        break
                if reason:
                    break
            if reason is None:
                try:
                    process.wait(timeout=max(0.01, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    reason = "timeout"
            if reason is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            if reason is not None:
                capture = {
                    "returncode": process.returncode,
                    "stdout_size": len(buffers[0]), "stdout_sha256": digest(bytes(buffers[0])),
                    "stderr_size": len(buffers[1]), "stderr_sha256": digest(bytes(buffers[1])),
                    "raw_published": False, "stop_reason": reason,
                    "prefix_only": True, "truncated": truncated,
                    "maximum_combined_bytes": maximum,
                }
                raise CaptureClosed(capture)
            return process.returncode, bytes(buffers[0]), bytes(buffers[1])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        process.stdout.close()
        process.stderr.close()


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
    rc, stdout, stderr = health._command_envelope(root_result, label="pstore metadata", maximum=ROOT_MAXIMUM)
    recorder.observe_root_transcript(rc, stdout, stderr)
    health._assert_private_tokens_absent(stdout, stderr, health._privacy_tokens(rows, devpath, before["boot_id"]))
    facts = parse_root(root_result)
    after = health.parse_public_snapshot(recorder.run("snapshot", public_argv, 20.0, 8192))
    if after != before:
        raise ReadinessError("target or current boot changed across metadata read")
    final = health.parse_inventory(health._decode_inventory(recorder.run("inventory", [adb, "devices", "-l"], 10.0, 32768), "final inventory"))
    final_selected = health.select_exact_target(final)
    health._validate_devpath_binding(final_selected, devpath)
    if final_selected["serial"] != serial or health.base.sanitized_inventory(final) != health.base.sanitized_inventory(rows):
        raise ReadinessError("global inventory changed")
    if tool != health._validate_adb_receipt(recorder.backend.tool_receipt()) or source_receipt() != before_source:
        raise ReadinessError("host source or tool changed")
    return {
        "schema": VERSION, "verdict": "PASS_S20PLUS_G986N_PSTORE_READINESS_D0_OBSERVED",
        "readiness": "METADATA_READY_RETENTION_UNPROVED" if facts["metadata_ready"] else "NOT_READY_OR_UNOBSERVABLE",
        "target": {k: v for k, v in before.items() if k != "boot_id"},
        "binding": {"serial_sha256": digest(serial.encode()), "topology_sha256": digest(devpath.encode()), "boot_id_sha256": digest(before["boot_id"].encode())},
        "facts": facts, "root_transcript_digest": recorder.root_transcript_digest,
        "source": before_source, "health_dependency_sha256": HEALTH_SHA256,
        "inventory_dependency": health.INVENTORY_HELPER_RECEIPT,
        "root_script_sha256": digest(ROOT_SCRIPT.encode()), "host_tool": tool,
        **recorder.evidence(), "device_effect_count": 0, "device_writes": False,
        "reboot_requested": False, "partition_access": False, "log_contents_read": False,
        "retention_proved": False, "native_pid1_proved": False,
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
            raise ReadinessError("indirect or foreign evidence directory")
        current = child
    if stat.S_IMODE(current.stat().st_mode) != 0o700:
        raise ReadinessError("private evidence root must be 0700")
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
        "root_output_maximum_bytes": ROOT_MAXIMUM, "hex_input_maximum_bytes": 65,
        "mount_input_maximum_bytes": 65537, "record_content_reads": 0,
        "metadata_paths": {**HEX_READS, **LINK_READS, **META_READS, "pmsg_node": "/dev/pmsg0", "pstore_mount": "/proc/self/mounts"},
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
                result.update(schema=VERSION, verdict="FAIL_S20PLUS_G986N_PSTORE_READINESS_D0_CLOSED")
                if isinstance(exc, CaptureClosed):
                    result["last_command_capture"] = exc.capture
                receipt = evidence.publish_json("failure.json", result)
                print(json.dumps({"verdict": result["verdict"], "result_sha256": receipt["sha256"], "run": str(evidence.path), **recorder.evidence()}))
                return 1
            print(json.dumps({"verdict": result["verdict"], "readiness": result["readiness"], "result_sha256": receipt["sha256"], "run": str(evidence.path), **recorder.evidence()}))
            return 0
    except Exception as exc:
        print(json.dumps({"verdict": "STOP_S20PLUS_G986N_PSTORE_READINESS_D0", "error_class": type(exc).__name__, "error_sha256": digest(str(exc).encode())}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
