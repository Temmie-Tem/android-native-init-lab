#!/usr/bin/env python3
"""Read-only probe that separates Stage A early-exit from output loss.

Stage A stops with "entry_count row cardinality is not one".  Its output is
deterministic across runs, ends cleanly after the `subsystem` entry, and carries
returncode 0 with empty stderr, so the three trailing rows and the universally
present `uevent` entry are both absent.  That leaves two candidates that the
Stage A evidence cannot separate: the remote script terminated early, or its
later output was lost.

This probe answers both in one read.  It drops `set -e` so no single failing
test can end the script, brackets the run with explicit sentinels, records the
remote exit status as data, and lists the client directory with `ls -a` rather
than a shell glob loop.  If `probe end` arrives, the script ran to completion and
Stage A's stop is specific to Stage A's own loop; if it does not, the loss is in
the transport.  Either way the `ls` rows settle whether `uevent` and `regmap`
exist, which Stage A's truncated listing cannot.

Stage A itself is not modified: its pinned script digest must stay e60e7104.
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

SCHEMA = "s22plus_fyg8_p319_stage_a_truncation_probe_v1"
VERSION = "s22plus-fyg8-p319-stage-a-truncation-probe-v1"
VERDICT = "PASS_S22PLUS_FYG8_P319_STAGE_A_TRUNCATION_PROBE_D0"
STOP_VERDICT = "STOP_S22PLUS_FYG8_P319_STAGE_A_TRUNCATION_PROBE_D0"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s22plus-fyg8-p319-stage-a-probe")
MAX_PROBE_BYTES = 32 * 1024

# No `set -e`: the whole point is to reach the end sentinel even when a step
# fails, so that a missing sentinel means transport loss and nothing else.
PROBE_SCRIPT = r"""platform=/sys/bus/platform/devices/994000.i2c
printf 'probe\tbegin\n'
printf 'platform_dir\t%s\n' "$([ -d "$platform" ] && echo present || echo absent)"
adapter=
for candidate in "$platform"/i2c-*; do
    [ -d "$candidate" ] || continue
    adapter=$candidate
    printf 'adapter\t%s\n' "${candidate##*/}"
done
client=
if [ -n "$adapter" ]; then
    for candidate in "$adapter"/*-0066; do
        [ -d "$candidate" ] || continue
        client=$candidate
        printf 'client\t%s\n' "${candidate##*/}"
    done
fi
if [ -n "$client" ]; then
    printf 'lsa\tbegin\n'
    ls -a "$client"
    printf 'lsa_rc\t%s\n' "$?"
    printf 'lsa\tend\n'
    printf 'uevent_present\t%s\n' "$([ -e "$client/uevent" ] && echo yes || echo no)"
    printf 'regmap_present\t%s\n' "$([ -e "$client/regmap" ] && echo yes || echo no)"
else
    printf 'client\tabsent\n'
fi
printf 'mxim_dev\t%s\n' "$([ -e /dev/mxim_dev ] && echo present || echo absent)"
printf 'mxim_class\t%s\n' "$([ -d /sys/class/mxim ] && echo present || echo absent)"
if [ -d /sys/class/mxim ]; then
    printf 'mxim_nodes\tbegin\n'
    ls -a /sys/class/mxim
    printf 'mxim_nodes\tend\n'
fi
if [ -d /sys/class/mxim/debug0 ]; then
    printf 'mxim_debug0\tbegin\n'
    ls -a /sys/class/mxim/debug0
    printf 'mxim_debug0\tend\n'
fi
printf 'probe\tend\n'
"""

FORBIDDEN_TOKENS = (
    ("sysfs_write", re.compile(r">\s*/sys|tee\s|echo[^|]*>\s*/sys")),
    ("attribute_body_read", re.compile(r"\bcat\b|\bod\b|\bhead\b|\btail\b|\bdd\b")),
    ("debugfs_access", re.compile(r"/sys/kernel/debug")),
    ("i2c_device_access", re.compile(r"/dev/i2c|i2cget|i2cset|i2cdump")),
    ("module_action", re.compile(r"\binsmod\b|\brmmod\b|\bmodprobe\b")),
    ("reboot", re.compile(r"\breboot\b|\bsvc\s+power\b")),
)


class ProbeError(RuntimeError):
    pass


def probe_safety_contract(script: str = PROBE_SCRIPT) -> dict[str, Any]:
    counts = {
        name: len(pattern.findall(script)) for name, pattern in FORBIDDEN_TOKENS
    }
    payload = script.encode("utf-8")
    value = {
        **{f"{name}_count": count for name, count in counts.items()},
        "listing_and_inode_test_only": all(
            count == 0 for count in counts.values()
        ),
        "script_sha256": hashlib.sha256(payload).hexdigest(),
        "script_size": len(payload),
    }
    value["result"] = "pass" if value["listing_and_inode_test_only"] else "fail"
    return value


def repo_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise ProbeError("repository root not found")


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


def parse_probe(text: str) -> dict[str, Any]:
    rows: list[tuple[str, ...]] = [
        tuple(line.split("\t")) for line in text.splitlines()
    ]
    tagged = {row[0] for row in rows if row}
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
        if current is not None and len(row) == 1:
            sections[current].append(row[0])
    listing = sections.get("lsa", [])
    return {
        "reached_begin": ("probe", "begin") in {tuple(r[:2]) for r in rows},
        # The single decisive bit: a missing end sentinel is transport loss.
        "reached_end": ("probe", "end") in {tuple(r[:2]) for r in rows},
        "row_tags": sorted(tagged),
        "listing": listing,
        "listing_count": len(listing),
        "uevent_in_listing": "uevent" in listing,
        "regmap_in_listing": "regmap" in listing,
        "mxim_class_nodes": sections.get("mxim_nodes", []),
        "mxim_debug0_entries": sections.get("mxim_debug0", []),
        "scalar_rows": {
            row[0]: row[1] for row in rows if len(row) == 2 and row[0] != "probe"
        },
    }


def collect(root: Path) -> dict[str, Any]:
    run_dir = allocate_run_dir(root)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-probe")
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
        raise ProbeError(f"probe inventory failed: {exc}") from exc
    selection = prior.select_exact_s22(inventory_text)
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "-s", selection.serial, "exec-out", "su", "-c", PROBE_SCRIPT],
            capture_dir,
            "0001-stage-a-truncation-probe",
            timeout=20,
            stdout_maximum=MAX_PROBE_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
    except raw_capture.RawCaptureError as exc:
        raise ProbeError(f"probe raw acquisition failed: {exc}") from exc
    # Deliberately not require_success: a nonzero remote status is the datum.
    payload = raw_capture.read_stdout(handle, maximum=MAX_PROBE_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=d0.MAX_TEXT_OUTPUT)
    observation = parse_probe(payload.decode("utf-8", "replace"))
    # A probe that cannot fail is not evidence.  Reaching the end sentinel proves
    # the remote script completed; the three handle flags prove the capture layer
    # did not silently truncate or time out.  Without this gate a timed-out run
    # renders as PASS with an empty listing, which is exactly the false negative
    # this probe exists to prevent.
    complete = (
        observation["reached_end"]
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
        "safety": probe_safety_contract(),
        "device_writes": False,
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
            "stderr_text": stderr.decode("utf-8", "replace")[:400],
            "receipt": str(handle.receipt_path),
        },
    }
    persist(run_dir / "result.json", value)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--collect", action="store_true")
    args = parser.parse_args(argv)
    if args.validate:
        value = {
            "schema": SCHEMA,
            "version": VERSION,
            "verdict": "PASS_S22PLUS_FYG8_P319_STAGE_A_TRUNCATION_PROBE_H0_READY",
            "safety": probe_safety_contract(),
            "device_contact": False,
            "live_authorized": False,
        }
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if value["safety"]["result"] == "pass" else 2
    try:
        value = collect(repo_root())
    except (ProbeError, prior.SysfsD0Error) as exc:
        print(f"P3.19 Stage A probe error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
