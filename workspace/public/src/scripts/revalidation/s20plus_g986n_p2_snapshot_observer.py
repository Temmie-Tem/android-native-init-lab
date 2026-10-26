#!/usr/bin/env python3
"""Fixed P2 observation leaf. The owning TWRP runtime supplies its leased engine.

No standalone CLI or default transport exists. Every command is captured before
parsing; the identical collector can replay saved receipts without a command.
"""
from __future__ import annotations

import hashlib
import re
import shlex
import time
from pathlib import Path
from typing import Any

import s20plus_g986n_p2_ram_snapshot as codec

MAX_ATTEMPTS = 60
OBSERVATION_SECONDS = 180
READER_LOCATIONS = ("/debug_ramdisk", "/sbin")
KINDS = ("inventory", "devpath", "public", "root")


class ObservationError(ValueError):
    pass


def capture_names() -> frozenset[str]:
    prefixes = [f"p2-ready-{i:02d}" for i in range(MAX_ATTEMPTS)] + ["p2-post", "p2-rollback"]
    return frozenset({"p2-snapshot", *(f"{p}-{k}" for p in prefixes for k in KINDS)})


def node_names() -> frozenset[str]:
    return frozenset(f"{n}{suffix}" for n in capture_names()
                     for suffix in (".stdout", ".stderr", ".capture.json"))


def root_script(engine, *, rollback: bool = False) -> str:
    # Keep the existing fixed root identity check; only Android UI readiness is
    # separate. The extra paths are the two documented Magisk RAM locations.
    if rollback:
        return engine.ROOT_READ_SCRIPT
    return engine.ROOT_READ_SCRIPT + r'''
location=$(/data/adb/magisk/magisk --path)
case "$location" in /debug_ramdisk|/sbin) ;; *) exit 65 ;; esac
reader="$location/''' + codec.READER_NAME + r'''"
printf 'reader_location=%s\n' "$location"
if [ -L "$location" ] || [ -L "$reader" ]; then exit 66; fi
if [ ! -f "$reader" ]; then
    printf 'reader_state=absent\nreader_sha256=unavailable\nreader_fs=unavailable\nreader_size=unavailable\n'
else
    size=$(/system/bin/stat -c '%s' "$reader")
    [ "$size" -gt 0 ] && [ "$size" -le 32768 ] || exit 67
    filesystem=$(/system/bin/stat -f -c '%t' "$reader")
    case "$filesystem" in 1021994|858458f6) ;; *) exit 68 ;; esac
    value=$(/system/bin/sha256sum "$reader")
    value=${value%% *}
    printf 'reader_state=present\nreader_sha256=%s\nreader_fs=%s\nreader_size=%s\n' "$value" "$filesystem" "$size"
fi
'''


def command(engine, serial: str | None, name: str, location: str = "/debug_ramdisk") -> list[str]:
    if name not in capture_names():
        raise ObservationError("capture name outside P2 declaration")
    if name.endswith("-inventory"):
        return [str(engine.ADB), "devices", "-l"]
    if not isinstance(serial, str) or not serial:
        raise ObservationError("target serial absent")
    base = [str(engine.ADB), "-s", serial]
    if name.endswith("-devpath"):
        return [*base, "get-devpath"]
    if name.endswith("-public"):
        return [*base, "exec-out", "sh", "-c", engine.PUBLIC_SNAPSHOT_SCRIPT]
    if name.endswith("-root"):
        return [*base, "shell", "su", "-c", shlex.quote(root_script(engine, rollback=name == "p2-rollback-root"))]
    if location not in READER_LOCATIONS:
        raise ObservationError("reader location outside fixed RAM paths")
    return [*base, "exec-out", "su", "-c", shlex.quote("exec " + location + "/" + codec.READER_NAME)]


def bounds(name: str) -> dict[str, Any]:
    if name not in capture_names():
        raise ObservationError("capture name outside P2 declaration")
    timeout = 15 if name == "p2-snapshot" else 10
    maximum = codec.MAX_STREAM_BYTES if name == "p2-snapshot" else 4096
    return {"timeout": timeout, "stdout_maximum": maximum, "stderr_maximum": 4096,
            "stdout_name": name + ".stdout", "stderr_name": name + ".stderr"}


def allowed(engine, argv, name: str, kwargs: dict[str, Any]) -> bool:
    if name not in capture_names() or kwargs != bounds(name):
        return False
    serial = argv[2] if len(argv) >= 4 and argv[:2] == [str(engine.ADB), "-s"] else None
    try:
        return any(argv == command(engine, serial, name, location) for location in READER_LOCATIONS)
    except ObservationError:
        return False


class Collector:
    def __init__(self, engine, run_dir: Path, expected: dict[str, Any], reader_sha256: str,
                 *, replay: list[dict[str, Any]] | None = None):
        self.engine, self.run_dir, self.expected = engine, run_dir, expected
        self.reader_sha256 = reader_sha256
        self.reads: list[dict[str, Any]] = []
        self.replay = replay
        self.deadline = time.monotonic() + OBSERVATION_SECONDS

    def capture(self, name: str, serial: str | None = None, *, location="/debug_ramdisk"):
        e = self.engine
        argv, limits = command(e, serial, name, location), bounds(name)
        descriptor = {"name": name, "command_sha256": e.digest(argv), "bounds": limits}
        if self.replay is not None:
            i = len(self.reads)
            if i >= len(self.replay) or any(self.replay[i].get(k) != v for k, v in descriptor.items()):
                raise ObservationError("saved capture command/order differs")
            handle = e.raw_capture.load_handle(self.run_dir / (name + ".capture.json"))
        else:
            if time.monotonic() >= self.deadline:
                raise ObservationError("observation-deadline")
            handle = e.raw_capture.acquire_command(argv, self.run_dir, name, **limits)
        if (handle.name != name or handle.receipt_path != self.run_dir / (name + ".capture.json")
                or handle.stdout_path != self.run_dir / (name + ".stdout")
                or handle.stderr_path != self.run_dir / (name + ".stderr")):
            raise ObservationError("raw-handle-stream-binding")
        # Both exact raw streams and their receipt exist before any parser runs.
        descriptor["receipt_sha256"] = hashlib.sha256(handle.receipt_path.read_bytes()).hexdigest()
        self.reads.append(descriptor)
        if self.replay is not None and descriptor != self.replay[len(self.reads) - 1]:
            raise ObservationError("saved raw receipt differs")
        stdout = e.raw_capture.read_stdout(handle, maximum=limits["stdout_maximum"])
        stderr = e.raw_capture.read_stderr(handle, maximum=limits["stderr_maximum"])
        if handle.timed_out or handle.output_exceeded or handle.producer_error_type is not None or stderr:
            raise ObservationError("raw-acquisition-failed")
        if type(handle.returncode) is not int or handle.returncode not in ((0, 2) if name == "p2-snapshot" else (0,)):
            raise ObservationError("unexpected-command-result")
        return handle, stdout

    def identity_once(self, prefix: str, *, require_reader: bool = True):
        e = self.engine
        if require_reader != (prefix != "p2-rollback"):
            raise ObservationError("reader requirement differs from fixed phase")
        _, raw = self.capture(prefix + "-inventory")
        rows = e.base.parse_inventory(raw.decode("ascii"))
        matching = [r for r in rows if codec.sha256(r["serial"].encode()) == self.expected["serial_sha256"]
                    or e.EXPECTED_ADB_MODEL in r["metadata"]]
        if not matching:
            return None, None
        if len(matching) != 1:
            raise ObservationError("ambiguous-target")
        row = matching[0]
        serial = row["serial"]
        if codec.sha256(serial.encode()) != self.expected["serial_sha256"]:
            raise ObservationError("target-serial-changed")
        if row["state"] == "offline":
            return None, None
        if row["state"] != "device":
            raise ObservationError("unexpected-target-state")
        e.exact_adb_row(rows, self.expected["serial_sha256"], "device")
        if self.replay is None:
            e.bind_android_inventory(rows)
        _, raw_path = self.capture(prefix + "-devpath", serial)
        if not raw_path.endswith(b"\n") or raw_path.count(b"\n") != 1:
            raise ObservationError("topology-framing")
        if codec.sha256(raw_path[:-1]) != self.expected["topology_sha256"]:
            raise ObservationError("target-topology-changed")
        handle, raw = self.capture(prefix + "-public", serial)
        public = e._ordered_output((handle.returncode, raw, b""), e.PUBLIC_SNAPSHOT_KEYS, "P2 public identity")
        stable = {"model": e.TARGET["model"], "device": e.TARGET["device"],
                  "product_name": e.TARGET["product"], "incremental": e.TARGET["incremental"]}
        if any(public[k] != v for k, v in stable.items()):
            raise ObservationError("target-build-changed")
        if public["selinux"] != "Enforcing":
            raise ObservationError("unexpected-selinux-state")
        if (public["boot_completed"] not in ("", "0", "1")
                or public["bootanim"] not in ("", "stopped", "running", "restarting", "stopping")):
            raise ObservationError("unexpected-public-state")
        if codec.UUID.fullmatch(public["boot_id"]) is None:
            raise ObservationError("malformed-boot-id")
        boot_sha = codec.sha256(public["boot_id"].encode())
        if boot_sha == self.expected["boot_id_sha256"]:
            raise ObservationError("candidate-boot-not-fresh")
        handle, raw = self.capture(prefix + "-root", serial)
        keys = (*e.ROOT_OUTPUT_KEYS, *(("reader_location", "reader_state", "reader_sha256", "reader_fs", "reader_size")
                                     if require_reader else ()))
        root = e._ordered_output((handle.returncode, raw, b""), keys, "P2 root identity")
        if any(root[k] != v for k, v in e.EXPECTED_ROOT_OUTPUT.items()):
            raise ObservationError("unexpected-root-identity")
        if root["boot_id"] != public["boot_id"]:
            raise ObservationError("boot-changed-during-identity")
        if require_reader and root["reader_location"] not in READER_LOCATIONS:
            raise ObservationError("reader-location")
        if not require_reader:
            pass
        elif (root["reader_state"] == "absent" and all(root[k] == "unavailable"
                for k in ("reader_sha256", "reader_fs", "reader_size"))):
            return None, None
        elif (root["reader_state"] != "present" or root["reader_sha256"] != self.reader_sha256
              or root["reader_fs"] not in ("1021994", "858458f6")
              or re.fullmatch(r"[1-9][0-9]{0,4}", root["reader_size"]) is None
              or int(root["reader_size"]) > 32768):
            raise ObservationError("reader-artifact-changed")
        return {"target": e.TARGET, "serial_sha256": self.expected["serial_sha256"],
            "topology_sha256": self.expected["topology_sha256"], "boot_id_sha256": boot_sha,
            "public": {k: v for k, v in public.items() if k != "boot_id"},
            "root": {k: v for k, v in root.items() if k != "boot_id"},
            "android_health_verified": False}, serial

    def collect(self):
        before = serial = None
        for attempt in range(MAX_ATTEMPTS):
            before, serial = self.identity_once(f"p2-ready-{attempt:02d}")
            if before is not None:
                break
            if self.replay is None:
                if time.monotonic() >= self.deadline:
                    break
                time.sleep(2)
        if before is None:
            raise ObservationError("bounded-readiness-timeout")
        handle, raw = self.capture("p2-snapshot", serial, location=before["root"]["reader_location"])
        after, after_serial = self.identity_once("p2-post")
        if (after is None or after_serial != serial
                or any(before[k] != after[k] for k in ("target", "serial_sha256", "topology_sha256", "boot_id_sha256"))):
            raise ObservationError("boot-or-identity-changed-after-capture")
        analysis = codec.analyze(raw, expected_boot_id_sha256=before["boot_id_sha256"], returncode=handle.returncode)
        if analysis.get("location") not in (None, before["root"]["reader_location"]):
            raise ObservationError("reader-executable-location-changed")
        if self.replay is not None and len(self.reads) != len(self.replay):
            raise ObservationError("unconsumed-saved-captures")
        return {"before": before, "after": after, "analysis": analysis,
                "reads": self.reads, "selected_attempt": attempt}, serial
