#!/usr/bin/env python3
"""Host-only analysis of retained /proc/last_kmsg captures.

The 2026-07-08 M18 live result found no expected marker in the retained log,
observed that it "looks more like ABL/download-mode retention than the M18
native-init printk stream", and left one instruction: analyse the private 2 MiB
last_kmsg.  That was never done.  This does it.

Nothing here touches a device.  It reads capture files already on disk.

What a capture contains, established by structure rather than by assumption:

  - a kernel-log portion, lines of the form `[   12.345678] [cpu: comm: pid] ...`
  - a bootloader portion, lines carrying `[ XBL ]` with their own `{ n }` counter

A native-init candidate replaces PID 1, so a capture of a candidate boot cannot
contain `init:`, `apexd` and `zygote` traffic.  Counting those separates a
candidate boot from a stock Android boot without trusting the file's name.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "s22plus_fyg8_p319_last_kmsg_retention_analysis_v1"
VERSION = "s22plus-fyg8-p319-last-kmsg-retention-analysis-v1"

KERNEL_LINE_RE = re.compile(rb"^\[\s*(\d+\.\d+)\]")
# `[    6.379114] [7:          apexd: 1166] apexd: Marking APEXd as starting`
# Counting a marker across the whole line also counts the comm column, which
# inflates every process name.  Markers are scoped to the message instead, and
# PID 1's comm is read out separately as the cleanest discriminator there is.
KERNEL_MESSAGE_RE = re.compile(
    rb"^\[\s*(\d+\.\d+)\]\s*\[\s*\d+:\s*(.*?):\s*(\d+)\]\s?(.*)$"
)
BANNER_RE = re.compile(rb"Linux version \S+")
XBL_RE = re.compile(rb"\[ XBL \]")
# Userspace echoing the previous reset reason is not a retained panic record.
APEXD_PANIC_ECHO_RE = re.compile(rb"apexd:\s*panic_message\s*:")

# PID 1 traffic.  A native-init candidate cannot produce these.
STOCK_USERSPACE_MARKERS = (b"init: ", b"apexd", b"zygote", b"binder")


class AnalysisError(RuntimeError):
    pass


def analyse(data: bytes) -> dict[str, Any]:
    lines = data.split(b"\n")
    stamps: list[float] = []
    messages: list[bytes] = []
    pid1_comms: set[bytes] = set()
    for line in lines:
        match = KERNEL_LINE_RE.match(line)
        if match:
            stamps.append(float(match.group(1)))
        detail = KERNEL_MESSAGE_RE.match(line)
        if detail:
            messages.append(detail.group(4))
            if detail.group(3) == b"1":
                pid1_comms.add(detail.group(2).strip())
    xbl_indices = [index for index, line in enumerate(lines) if XBL_RE.search(line)]
    userspace = {
        marker.decode().strip(): sum(1 for message in messages if marker in message)
        for marker in STOCK_USERSPACE_MARKERS
    }
    panic_lines = [message for message in messages if b"PANIC" in message]
    panic_echo_only = bool(panic_lines) and all(
        APEXD_PANIC_ECHO_RE.search(line) for line in panic_lines
    )
    # Timestamps run forward with no wrap-back, so a missing banner means the
    # head was overwritten rather than the buffer being out of order.
    backward_steps = sum(
        1
        for index in range(1, len(stamps))
        if stamps[index] < stamps[index - 1] - 1.0
    )
    value: dict[str, Any] = {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "lines": len(lines),
        "kernel_lines": len(stamps),
        "earliest": min(stamps) if stamps else None,
        "latest": max(stamps) if stamps else None,
        "span_seconds": round(max(stamps) - min(stamps), 3) if stamps else None,
        "backward_timestamp_steps": backward_steps,
        "banner_present": BANNER_RE.search(data) is not None,
        "xbl_lines": len(xbl_indices),
        "first_xbl_line": xbl_indices[0] if xbl_indices else None,
        "stock_userspace_markers": userspace,
        "pid1_comms": sorted(
            comm.decode("utf-8", "replace") for comm in pid1_comms
        ),
        "panic_lines": len(panic_lines),
        "panic_is_userspace_echo_only": panic_echo_only,
    }
    # The head is lost when the ring wrapped: forward-only stamps, no banner.
    value["head_overwritten"] = (
        bool(stamps) and not value["banner_present"] and backward_steps == 0
    )
    value["boot_kind"] = classify(value)
    return value


def classify(value: dict[str, Any]) -> str:
    """Name whose boot this is, from PID 1 traffic rather than the filename."""
    markers = value["stock_userspace_markers"]
    if not value["kernel_lines"]:
        return "no_kernel_log"
    # PID 1 running as `init` settles it: a native-init candidate is PID 1.
    if "init" in value["pid1_comms"]:
        return "stock_android_boot"
    if markers.get("init:", 0) > 100 and markers.get("apexd", 0) > 10:
        return "stock_android_boot"
    if sum(markers.values()) == 0:
        return "no_stock_userspace"
    return "indeterminate"


def find_markers(data: bytes, markers: list[str]) -> dict[str, int]:
    return {
        marker: data.count(marker.encode("utf-8", "surrogateescape"))
        for marker in markers
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument(
        "--marker",
        action="append",
        default=[],
        help="string to search for, e.g. a run id; repeatable",
    )
    args = parser.parse_args(argv)
    results = []
    for path in args.captures:
        if not path.is_file():
            raise AnalysisError(f"capture is not a file: {path}")
        data = path.read_bytes()
        value = analyse(data)
        value["name"] = path.name
        if args.marker:
            value["markers"] = find_markers(data, args.marker)
        results.append(value)
    print(
        json.dumps(
            {"schema": SCHEMA, "version": VERSION, "captures": results},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
