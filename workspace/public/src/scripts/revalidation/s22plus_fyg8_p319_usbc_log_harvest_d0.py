#!/usr/bin/env python3
"""Harvest what the MAX77705 driver already logged.  No writes, no opcodes.

The Stage B read gave port state but not the mux.  Reaching CONTROL1 by opcode
needs a write, which is F1-class.  This runner takes the read-only route
instead, because the driver already publishes the answer:

  max77705-muic.c:331   max77705_switch_path() pr_info's the CONTROL1 value it
                        is about to write, then issues COMMAND_CONTROL1_WRITE.
  max77705_usbc.c:1897  every opcode write is print_hex_dump'd at KERN_INFO
  max77705_usbc.c:1959  every opcode read response likewise

Both dumps sit on the `#else` side of an `#if 0`, so they are unconditionally
compiled -- there is no CONFIG gate to check.

That settles half of this campaign's open question without touching the device's
state: whether the driver ever *commanded* the mux.  It does not give the mux's
actual bits, and this runner does not claim to.  A `switch_path` line absent from
a ring buffer that covers the attach is evidence the command was never issued.

Two more read-only surfaces are collected in the same pass: /proc/usblog, which
is 0444 and backed by single_open/single_release so reading it is a snapshot and
not a drain (usblog_proc_notify.c:1737, :1260-1266), and the standard Type-C
class port registered at max77705_usbc.c:3775.

The one destructive thing a log reader can do is clear the ring it is reading.
`dmesg -c`, `-C`, `--clear` and `--read-clear` are therefore refused by the
safety contract, not merely avoided by convention.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import device_action_d0_v2 as d0  # noqa: E402
import device_action_raw_capture_v1 as raw_capture  # noqa: E402
import s22plus_fyg8_max77705_sysfs_d0 as prior  # noqa: E402

SCHEMA = "s22plus_fyg8_p319_usbc_log_harvest_v1"
VERSION = "s22plus-fyg8-p319-usbc-log-harvest-v1"
VERDICT = "PASS_S22PLUS_FYG8_P319_USBC_LOG_HARVEST_D0"
STOP_VERDICT = "STOP_S22PLUS_FYG8_P319_USBC_LOG_HARVEST_D0"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s22plus-fyg8-p319-usbc-log-harvest")
MAX_HARVEST_BYTES = 2 * 1024 * 1024

# Reading a log must never clear it.  Named so the contract can prove absence.
RING_CLEARING_TOKENS = ("--clear", "--read-clear")
# A token list alone is weak: `dmesg  -c` with two spaces would slip past it, and
# a bare "-c " token nearly false-matches `wc -c`.  Require instead that every
# dmesg occurrence is immediately followed by a pipe or a closing paren, so no
# flag of any kind can be attached to it.
DMESG_WITH_FLAG_RE = re.compile(r"dmesg(?!\s*[|)])")
# Write primitives that exist nearby and must not appear at all.
FORBIDDEN_TOKENS = ("fw_update", "opcode", "mxim", "/dev/", "insmod", "rmmod",
                    "modprobe", "reboot", "i2c", "/sys/kernel/debug")

# Pinned rather than globbed: "exactly what we read" is the property that makes
# a body read reviewable.  These are the standard Type-C class attributes.
TYPEC_ATTRIBUTES = (
    "data_role",
    "orientation",
    "port_type",
    "power_operation_mode",
    "power_role",
    "preferred_role",
    "supported_accessory_modes",
    "usb_power_delivery_revision",
    "usb_typec_revision",
    "vconn_source",
)

DRIVER_LOG_PATTERN = "max77705|muic|switch_path|com_to_|CCIC|PDIC|typec"

HARVEST_SCRIPT = (
    "printf 'harvest\\tbegin\\n'\n"
    "printf 'kmsg_lines\\t%s\\n' \"$(dmesg | wc -l)\"\n"
    "printf 'kmsg_bytes\\t%s\\n' \"$(dmesg | wc -c)\"\n"
    # Without the ring's time span, an absent log line cannot be told apart
    # from a log line that rotated out.  That distinction is the whole result.
    "printf 'kmsg_first\\t%s\\n' \"$(dmesg | head -n 1 | cut -c1-22)\"\n"
    "printf 'kmsg_last\\t%s\\n' \"$(dmesg | tail -n 1 | cut -c1-22)\"\n"
    "printf 'usblog_present\\t%s\\n' \"$([ -e /proc/usblog ] && echo yes || echo no)\"\n"
    "printf 'typec_port_present\\t%s\\n' \"$([ -d /sys/class/typec/port0 ] && echo yes || echo no)\"\n"
    "printf 'driver_log\\tbegin\\n'\n"
    f"dmesg | grep -aE '{DRIVER_LOG_PATTERN}'\n"
    "printf 'driver_log_rc\\t%s\\n' \"$?\"\n"
    "printf 'driver_log\\tend\\n'\n"
    "printf 'usblog\\tbegin\\n'\n"
    "if [ -e /proc/usblog ]; then\n"
    "    cat /proc/usblog\n"
    "    printf 'usblog_rc\\t%s\\n' \"$?\"\n"
    "fi\n"
    "printf 'usblog\\tend\\n'\n"
    "printf 'typec\\tbegin\\n'\n"
    + "".join(
        f"[ -f /sys/class/typec/port0/{name} ] && "
        f"printf '{name}\\t%s\\n' \"$(cat /sys/class/typec/port0/{name})\"\n"
        for name in TYPEC_ATTRIBUTES
    )
    + "printf 'typec\\tend\\n'\n"
    "printf 'harvest\\tend\\n'\n"
)


class HarvestError(RuntimeError):
    pass


def harvest_safety_contract(script: str = HARVEST_SCRIPT) -> dict[str, Any]:
    """Prove the reader cannot clear what it reads, and writes nothing."""
    value = {
        "ring_clearing_hits": sorted(
            token for token in RING_CLEARING_TOKENS if token in script
        ),
        "flagged_dmesg_count": len(DMESG_WITH_FLAG_RE.findall(script)),
        "forbidden_token_hits": sorted(
            token for token in FORBIDDEN_TOKENS if token in script
        ),
        "redirect_count": len(re.findall(r"(?<![0-9])>", script)),
        "dmesg_invocations": script.count("dmesg"),
        "typec_attribute_count": sum(
            script.count(f"/sys/class/typec/port0/{name}") for name in TYPEC_ATTRIBUTES
        ),
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "script_size": len(script.encode("utf-8")),
    }
    value["read_only_and_non_clearing"] = (
        not value["ring_clearing_hits"]
        and value["flagged_dmesg_count"] == 0
        and not value["forbidden_token_hits"]
        and value["redirect_count"] == 0
    )
    value["result"] = "pass" if value["read_only_and_non_clearing"] else "fail"
    return value


REDACTIONS = (
    ("mac", re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("uuid", re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")),
    ("kernel_pointer", re.compile(r"\b(?:0x)?[0-9a-f]{16}\b")),
    ("long_digits", re.compile(r"\b\d{14,}\b")),
)


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Redact before anything leaves workspace/private.

    The raw capture keeps the unredacted bytes under the gitignored run root;
    this is what may be summarised, quoted or published.
    """
    counts: dict[str, int] = {}
    for name, pattern in REDACTIONS:
        text, hits = pattern.subn(f"<{name.upper()}>", text)
        if hits:
            counts[name] = hits
    return text, counts


def repo_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise HarvestError("repository root not found")


def allocate_run_dir(root: Path) -> Path:
    base = (root / DEFAULT_RUN_ROOT).absolute()
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base / f"d0-{stamp}-{os.urandom(6).hex()}"
    run_dir.mkdir(mode=0o700)
    return run_dir


def persist(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, stat.S_IRUSR)


SWITCH_PATH_RE = re.compile(r"max77705_switch_path value\(0x([0-9a-fA-F]+)\)")
KMSG_TS_RE = re.compile(r"\[\s*(\d+\.\d+)\]")
# An attach inside the captured window is what makes an absent switch_path
# meaningful.  Without one, the negative says nothing.
ATTACH_MARKER_RE = re.compile(
    r"attach_usb_path|muic_attach_dev|PDIC_NOTIFY_ATTACH|plug_attach_done"
    r"|max77705_pdic_attach|ccstat_irq"
)
COM_TO_RE = re.compile(r"\b(com_to_(?:open|usb_ap|usb_cp|uart_ap|uart_cp))\b")
OPCODE_WRITE_RE = re.compile(r"max77705: opcode_write:\s*([0-9a-f ]+)")
OPCODE_MSG_RE = re.compile(r"opcode 0x([0-9a-fA-F]+), (write|read)_length (\d+)")


USBLOG_SECTION_RE = re.compile(r"^usblog (.+?): count=(\d+) maxline=(\d+)$")
USBLOG_VERSION_RE = re.compile(r"^(hw|sw|bin) version =\s*(.+)$")
USBLOG_ENTRY_RE = re.compile(r"^\[\s*(\d+\.\d+)\]\s*(.*)$")
USBLOG_TIMESYNC_RE = re.compile(r"^time sync: \[([^\]]+)\]\[\s*(\d+\.\d+)\]")
# Gadget enumeration reaching SET_CON means the host set a configuration.
ENUMERATION_MARKERS = ("CONNDONE", "GET_DES", "SET_CON", "RESET : SUPER")


def parse_usblog(lines: list[str]) -> dict[str, Any]:
    """Parse /proc/usblog into its named count-bounded rings.

    These rings are bounded by entry count, not by time, and the counts are
    small enough that they reach back to boot.  That is what makes usblog a
    better surface than the kernel ring for anything that happened at attach:
    dmesg here spans tens of seconds, usblog spans the whole uptime.
    """
    sections: dict[str, dict[str, Any]] = {}
    versions: dict[str, str] = {}
    time_sync: dict[str, Any] | None = None
    current: str | None = None
    for line in lines:
        stripped = line.strip()
        match = USBLOG_TIMESYNC_RE.match(stripped)
        if match:
            time_sync = {
                "wall": match.group(1),
                "monotonic": float(match.group(2)),
            }
            continue
        match = USBLOG_SECTION_RE.match(stripped)
        if match:
            current = match.group(1)
            sections[current] = {
                "count": int(match.group(2)),
                "maxline": int(match.group(3)),
                "entries": [],
            }
            continue
        match = USBLOG_VERSION_RE.match(stripped)
        if match:
            versions[match.group(1)] = " ".join(match.group(2).split())
            continue
        match = USBLOG_ENTRY_RE.match(stripped)
        if match and current is not None:
            sections[current]["entries"].append(
                {"t": float(match.group(1)), "text": match.group(2).strip()}
            )
    stamps = [
        entry["t"] for value in sections.values() for entry in value["entries"]
    ]
    everything = [
        entry["text"] for value in sections.values() for entry in value["entries"]
    ]
    ccic = sections.get("CCIC EVENT", {}).get("entries", [])
    return {
        "time_sync": time_sync,
        "versions": versions,
        "sections": {
            name: {
                "count": value["count"],
                "maxline": value["maxline"],
                "parsed": len(value["entries"]),
                # A ring is only trustworthy as history if it is not yet full.
                "wrapped": value["count"] >= value["maxline"],
            }
            for name, value in sections.items()
        },
        "earliest": min(stamps) if stamps else None,
        "latest": max(stamps) if stamps else None,
        # The property that matters: does this reach back to boot?
        "spans_boot": bool(stamps) and min(stamps) < 60.0,
        "attach_events": sum(1 for entry in ccic if "ATTACHED" in entry["text"]),
        "detach_events": sum(1 for entry in ccic if "DETACHED" in entry["text"]),
        "hardreset_sent": [
            entry["t"]
            for value in sections.values()
            for entry in value["entries"]
            if "HARDRESET_SENT" in entry["text"]
        ],
        "enumeration": {
            marker: sum(1 for text in everything if marker in text)
            for marker in ENUMERATION_MARKERS
        },
    }


def parse_harvest(text: str) -> dict[str, Any]:
    rows = [line.split("\t") for line in text.splitlines()]
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for row in rows:
        if len(row) == 2 and row[1] == "begin":
            current = row[0]
            sections.setdefault(current, [])
            continue
        if len(row) == 2 and row[1] == "end":
            current = None
            continue
        if current is not None:
            sections[current].append("\t".join(row))
    scalars = {
        row[0]: row[1]
        for row in rows
        if len(row) == 2 and row[1] not in {"begin", "end"}
    }
    driver_log = sections.get("driver_log", [])
    joined = "\n".join(driver_log)
    switch_values = [f"0x{value.lower()}" for value in SWITCH_PATH_RE.findall(joined)]
    attach_markers = len(ATTACH_MARKER_RE.findall(joined))
    first = KMSG_TS_RE.match(scalars.get("kmsg_first") or "")
    last = KMSG_TS_RE.match(scalars.get("kmsg_last") or "")
    span = (
        round(float(last.group(1)) - float(first.group(1)), 3)
        if first and last
        else None
    )
    return {
        "reached_end": ("harvest", "end") in {tuple(row[:2]) for row in rows},
        "kmsg_first": scalars.get("kmsg_first"),
        "kmsg_last": scalars.get("kmsg_last"),
        "ring_span_seconds": span,
        "attach_markers_in_window": attach_markers,
        # The decisive honesty gate: switch_path_count == 0 only means the
        # driver never commanded the mux if an attach is inside the window.
        "mux_evidence_conclusive": bool(switch_values) or attach_markers > 0,
        "kmsg_lines": scalars.get("kmsg_lines"),
        "kmsg_bytes": scalars.get("kmsg_bytes"),
        "usblog_present": scalars.get("usblog_present"),
        "typec_port_present": scalars.get("typec_port_present"),
        "driver_log_rc": scalars.get("driver_log_rc"),
        "driver_log_lines": len(driver_log),
        "usblog_lines": len(sections.get("usblog", [])),
        "usblog": parse_usblog(sections.get("usblog", [])),
        "typec": {
            name: scalars[name] for name in TYPEC_ATTRIBUTES if name in scalars
        },
        # The decisive question: did the driver ever command the mux?
        "switch_path_count": len(switch_values),
        "switch_path_values": switch_values,
        "com_to_calls": sorted(set(COM_TO_RE.findall(joined))),
        "opcode_write_dumps": len(OPCODE_WRITE_RE.findall(joined)),
        "opcode_messages": len(OPCODE_MSG_RE.findall(joined)),
        # A grep that matched nothing exits 1.  That is a result, not an error.
        "driver_log_matched": bool(driver_log),
    }


def collect(root: Path) -> dict[str, Any]:
    contract = harvest_safety_contract()
    if contract["result"] != "pass":
        raise HarvestError("harvest safety contract failed before any device contact")
    run_dir = allocate_run_dir(root)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-harvest")
    adb = prior.DEFAULT_ADB
    try:
        inventory = raw_capture.acquire_command(
            [str(adb), "devices", "-l"],
            capture_dir,
            "0000-adb-inventory",
            timeout=10,
            stdout_maximum=d0.MAX_TEXT_OUTPUT,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
        inventory_text = raw_capture.decode_success_stdout(
            inventory, maximum=d0.MAX_TEXT_OUTPUT, strip=False
        )
    except raw_capture.RawCaptureError as exc:
        raise HarvestError(f"harvest inventory failed: {exc}") from exc
    selection = prior.select_exact_s22(inventory_text)
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "-s", selection.serial, "exec-out", "su", "-c", HARVEST_SCRIPT],
            capture_dir,
            "0001-usbc-log-harvest",
            timeout=60,
            stdout_maximum=MAX_HARVEST_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
    except raw_capture.RawCaptureError as exc:
        raise HarvestError(f"harvest raw acquisition failed: {exc}") from exc
    payload = raw_capture.read_stdout(handle, maximum=MAX_HARVEST_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=d0.MAX_TEXT_OUTPUT)
    text, redactions = redact(payload.decode("utf-8", "replace"))
    observation = parse_harvest(text)
    complete = (
        observation["reached_end"]
        and observation["kmsg_lines"] is not None
        and int(observation["kmsg_lines"] or 0) > 0
        and not handle.output_exceeded
        and not handle.timed_out
        and handle.producer_error_type is None
    )
    value = {
        "schema": SCHEMA,
        "version": VERSION,
        "verdict": VERDICT if complete else STOP_VERDICT,
        "complete": complete,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "safety": contract,
        "redactions_applied": redactions,
        "device_writes": False,
        "ring_buffer_cleared": False,
        "reboot_requested": False,
        "partition_transfer": False,
        "candidate_used": False,
        "f1_authorized": False,
        "live_authorized": False,
        "observation": observation,
        "raw": {
            "returncode": handle.returncode,
            "timed_out": handle.timed_out,
            "output_exceeded": handle.output_exceeded,
            "producer_error_type": handle.producer_error_type,
            "stdout_bytes": len(payload),
            "stderr_bytes": len(stderr),
            "receipt": str(handle.receipt_path),
        },
    }
    persist(run_dir / "result.json", value)
    redacted_path = run_dir / "driver-log.redacted.txt"
    descriptor = os.open(redacted_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(redacted_path, stat.S_IRUSR)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--collect", action="store_true")
    args = parser.parse_args(argv)
    contract = harvest_safety_contract()
    if args.validate:
        value = {
            "schema": SCHEMA,
            "version": VERSION,
            "verdict": "PASS_S22PLUS_FYG8_P319_USBC_LOG_HARVEST_H0_READY",
            "safety": contract,
            "typec_attributes": list(TYPEC_ATTRIBUTES),
            "device_contact": False,
            "live_authorized": False,
        }
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if contract["result"] == "pass" else 2
    try:
        value = collect(repo_root())
    except (HarvestError, prior.SysfsD0Error) as exc:
        print(f"P3.19 log harvest error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
