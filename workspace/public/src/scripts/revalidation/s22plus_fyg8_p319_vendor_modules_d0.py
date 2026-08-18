#!/usr/bin/env python3
"""Read the normal-boot module list from the running unit.

Gate 0 is `vendor_dlkm/lib/modules/modules.load`, the second-stage list that
orders the 333 vendor modules at normal boot.  It has never been recovered from
firmware, and `vendor_boot`'s lists are the first-stage and recovery orders
instead.  The device mounts the same bytes at `/vendor/lib/modules`, which the
boot log confirms:

    modprobe: Loading module /vendor/lib/modules/pdic_max77705.ko

So this reads it directly, and reads the `max77705` lines of `modules.dep` in
the same pass, because the dependency order is the other half of what a
candidate needs in order to load the mux driver itself.

The read is self-verifying: the firmware copy's SHA-256 is separately known, so
a match proves the device and the firmware carry the same list, and a mismatch
is itself the finding.  Two body reads, both of pinned paths, no writes.
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

SCHEMA = "s22plus_fyg8_p319_vendor_modules_v1"
VERSION = "s22plus-fyg8-p319-vendor-modules-v1"
VERDICT = "PASS_S22PLUS_FYG8_P319_VENDOR_MODULES_D0"
STOP_VERDICT = "STOP_S22PLUS_FYG8_P319_VENDOR_MODULES_D0"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s22plus-fyg8-p319-vendor-modules")
MAX_BYTES = 1024 * 1024

MODULES_DIR = "/vendor/lib/modules"
FORBIDDEN_TOKENS = ("fw_update", "opcode", "mxim", "/dev/", "insmod", "rmmod",
                    "modprobe ", "reboot", "i2c", "dmesg", "/sys/")

VENDOR_MODULES_SCRIPT = (
    "target=/vendor/lib/modules\n"
    "printf 'vm\\tbegin\\n'\n"
    "printf 'dir_present\\t%s\\n' \"$([ -d \"$target\" ] && echo yes || echo no)\"\n"
    "printf 'load_present\\t%s\\n' \"$([ -e \"$target/modules.load\" ] && echo yes || echo no)\"\n"
    "printf 'dep_present\\t%s\\n' \"$([ -e \"$target/modules.dep\" ] && echo yes || echo no)\"\n"
    "printf 'ko_count\\t%s\\n' \"$(ls -a1 \"$target\" | grep -c '\\.ko$')\"\n"
    "printf 'load\\tbegin\\n'\n"
    "cat \"$target/modules.load\"\n"
    "printf 'load_rc\\t%s\\n' \"$?\"\n"
    "printf 'load\\tend\\n'\n"
    "printf 'dep\\tbegin\\n'\n"
    "grep -a max77705 \"$target/modules.dep\"\n"
    "printf 'dep_rc\\t%s\\n' \"$?\"\n"
    "printf 'dep\\tend\\n'\n"
    "printf 'vm\\tend\\n'\n"
)


class VendorModulesError(RuntimeError):
    pass


def vendor_modules_safety_contract(script: str = VENDOR_MODULES_SCRIPT) -> dict[str, Any]:
    lines = [line.strip() for line in script.splitlines()]
    body_reads = [
        line for line in lines if line.split(" ")[0] in {"cat", "od", "head", "tail", "dd"}
    ]
    greps = [line for line in lines if line.startswith("grep ")]
    assignments = [line for line in lines if line.startswith("target=")]
    value = {
        "body_read_count": len(body_reads),
        "body_read_line": body_reads[0] if len(body_reads) == 1 else None,
        "grep_count": len(greps),
        "target_assignment": assignments[0] if len(assignments) == 1 else None,
        "redirect_count": len(re.findall(r"(?<![0-9])>", script)),
        "forbidden_token_hits": sorted(
            token for token in FORBIDDEN_TOKENS if token in script
        ),
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "script_size": len(script.encode("utf-8")),
    }
    value["two_pinned_reads_only"] = (
        value["body_read_count"] == 1
        and value["body_read_line"] == 'cat "$target/modules.load"'
        and value["grep_count"] == 1
        and value["target_assignment"] == f"target={MODULES_DIR}"
        and value["redirect_count"] == 0
        and not value["forbidden_token_hits"]
    )
    value["result"] = "pass" if value["two_pinned_reads_only"] else "fail"
    return value


def repo_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise VendorModulesError("repository root not found")


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


def slice_section(payload: bytes, name: str) -> bytes | None:
    """Return the exact bytes a section framed, so the hash is the file's."""
    start = payload.find(f"{name}\tbegin\n".encode())
    if start < 0:
        return None
    start += len(f"{name}\tbegin\n")
    end = payload.find(f"\n{name}\tend\n".encode(), start)
    if end < 0:
        return None
    return payload[start:end]


TAIL_RE = re.compile(rb"\n?" + re.escape(b"load_rc\t") + rb"\d+$")


def parse_vendor_modules(payload: bytes) -> dict[str, Any]:
    text = payload.decode("utf-8", "replace")
    rows = [line.split("\t") for line in text.splitlines()]
    scalars = {
        row[0]: row[1]
        for row in rows
        if len(row) == 2 and row[1] not in {"begin", "end"}
    }
    raw_load = slice_section(payload, "load")
    load_bytes = None
    if raw_load is not None:
        # `cat` emits the file verbatim; the framing printf that follows is
        # stripped here so the digest is of the file and not of the transcript.
        load_bytes = TAIL_RE.sub(b"", raw_load)
        if load_bytes and not load_bytes.endswith(b"\n"):
            load_bytes += b"\n"
    dep_raw = slice_section(payload, "dep")
    dep_lines = []
    if dep_raw is not None:
        dep_lines = [
            line
            for line in dep_raw.decode("utf-8", "replace").splitlines()
            if line and not line.startswith("dep_rc\t")
        ]
    entries = (
        [line for line in load_bytes.decode("utf-8", "replace").splitlines() if line]
        if load_bytes
        else []
    )
    return {
        "dir_present": scalars.get("dir_present"),
        "load_present": scalars.get("load_present"),
        "dep_present": scalars.get("dep_present"),
        "ko_count": scalars.get("ko_count"),
        "load_rc": scalars.get("load_rc"),
        "dep_rc": scalars.get("dep_rc"),
        "load_bytes": len(load_bytes) if load_bytes else 0,
        "load_sha256": hashlib.sha256(load_bytes).hexdigest() if load_bytes else None,
        "load_entries": len(entries),
        "load_first": entries[:5],
        "load_last": entries[-5:],
        "max77705_entries": [
            (index, name)
            for index, name in enumerate(entries)
            if "max77705" in name or "muic" in name or "pdic" in name
            or "typec_manager" in name
        ],
        "dep_lines": dep_lines,
        "reached_end": ("vm", "end") in {tuple(row[:2]) for row in rows},
    }


def collect(root: Path) -> dict[str, Any]:
    contract = vendor_modules_safety_contract()
    if contract["result"] != "pass":
        raise VendorModulesError("safety contract failed before any device contact")
    run_dir = allocate_run_dir(root)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-vendor-modules")
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
        raise VendorModulesError(f"inventory failed: {exc}") from exc
    selection = prior.select_exact_s22(inventory_text)
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "-s", selection.serial, "exec-out", "su", "-c",
             VENDOR_MODULES_SCRIPT],
            capture_dir,
            "0001-vendor-modules",
            timeout=30,
            stdout_maximum=MAX_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
    except raw_capture.RawCaptureError as exc:
        raise VendorModulesError(f"raw acquisition failed: {exc}") from exc
    payload = raw_capture.read_stdout(handle, maximum=MAX_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=d0.MAX_TEXT_OUTPUT)
    observation = parse_vendor_modules(payload)
    complete = (
        observation["reached_end"]
        and observation["load_present"] == "yes"
        and observation["load_rc"] == "0"
        and observation["load_entries"] > 0
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
    contract = vendor_modules_safety_contract()
    if args.validate:
        print(json.dumps({"schema": SCHEMA, "safety": contract,
                          "device_contact": False}, indent=2, sort_keys=True))
        return 0 if contract["result"] == "pass" else 2
    try:
        value = collect(repo_root())
    except (VendorModulesError, prior.SysfsD0Error) as exc:
        print(f"P3.19 vendor modules error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
