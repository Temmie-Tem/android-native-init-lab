#!/usr/bin/env python3
"""Stage B: read exactly one attribute body, /sys/class/mxim/debug0/reg.

The P3.19 probe established that /sys/class/mxim/debug0 exists on the running
unit and holds `reg` and `opcode`.  This runner reads `reg` and nothing else.

What that costs was derived from the driver table rather than from the attribute
name.  `mxim_debug_reg_show` walks a fixed seventeen-entry table and skips every
entry marked `.ignore`, so a read is fourteen single-byte I2C reads over
0x00-0x10.  Neither the charger firmware-major register nor any charger detail
register is in that table, so the hazard behind the full-dump prohibition is not
on this path.

One entry in that table is mislabelled in a way that matters.  The debug driver
calls 0x05 `MXIM_REG_RSVD1` and leaves it un-ignored, but `max77705.h:65` defines
0x05 as `REG_VDM_INT`, and `max77705_usbc.c:170-172` clears the interrupt block
by bulk-reading 0x02-0x05 under the comment "clear all interrpts".  Reading `reg`
therefore clears any latched VDM (alternate-mode) interrupt before the driver's
handler can see it.  That is a real side effect on a read path, so it is gated
behind an explicit flag rather than assumed away.

This runner never reads or writes `opcode`, never writes `reg`, and never touches
`fw_update` or /dev/mxim_dev.  All three are unvalidated write primitives into the
USBC controller and require F1-class authority.
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

SCHEMA = "s22plus_fyg8_p319_max77705_reg_stage_b_v1"
VERSION = "s22plus-fyg8-p319-max77705-reg-stage-b-v1"
VERDICT = "PASS_S22PLUS_FYG8_P319_MAX77705_REG_STAGE_B_D0"
STOP_VERDICT = "STOP_S22PLUS_FYG8_P319_MAX77705_REG_STAGE_B_D0"
DEFAULT_RUN_ROOT = Path("workspace/private/runs/s22plus-fyg8-p319-stage-b-reg")
MAX_BODY_BYTES = 8 * 1024

REG_PATH = "/sys/class/mxim/debug0/reg"
# Named here so the safety contract can prove they never appear in the script.
FORBIDDEN_PATHS = (
    "/sys/class/mxim/debug0/opcode",
    "fw_update",
    "/dev/mxim_dev",
)

STAGE_B_SCRIPT = r"""target=/sys/class/mxim/debug0/reg
printf 'stage_b\tbegin\n'
printf 'target_present\t%s\n' "$([ -e "$target" ] && echo yes || echo no)"
if [ -e "$target" ]; then
    printf 'body\tbegin\n'
    cat "$target"
    printf 'body_rc\t%s\n' "$?"
    printf 'body\tend\n'
fi
printf 'stage_b\tend\n'
"""


class StageBError(RuntimeError):
    pass


# Address -> (name from max77705.h, field decoder spec).  The debug driver's own
# header mislabels several of these; the addresses and the names below follow
# max77705.h and the driver's actual reads, not max77705_debug.h.
VBADC = {
    0x0: "3.8V under", 0x1: "3.8-4.5V", 0x2: "4.5-5.5V", 0x3: "5.5-6.5V",
    0x4: "6.5-7.5V", 0x5: "7.5-8.5V", 0x6: "8.5-9.5V", 0x7: "9.5-10.5V",
    0x8: "10.5-11.5V", 0x9: "11.5-12.5V", 0xA: "12.5V over",
}
CCSTAT = {
    0: "cc_No_Connection", 1: "cc_SINK", 2: "cc_SOURCE",
    3: "cc_Audio_Accessory", 4: "cc_Debug_Accessory", 5: "cc_Error",
    6: "cc_Disabled", 7: "cc_RFU",
}
# CCPinStat is BITS(7,6); only the first four enum members can be represented.
CCPINSTAT = {0: "NO_DETERMINATION", 1: "CC1_ACTIVE", 2: "CC2_ACTIVE", 3: "AUDIO_ACCESSORY"}
PRCHGTYP = {
    0x0: "PRCHGTYP_UNKNOWN", 0x1: "PRCHGTYP_SAMSUNG_2A",
    0x2: "PRCHGTYP_APPLE_500MA", 0x3: "PRCHGTYP_APPLE_1A",
    0x4: "PRCHGTYP_APPLE_2A", 0x5: "PRCHGTYP_APPLE_12W",
    0x6: "PRCHGTYP_3A_DCP", 0x7: "PRCHGTYP_RFU",
}

REGISTERS: dict[int, tuple[str, tuple[tuple[str, int, int, dict[int, str] | None], ...]]] = {
    0x00: ("REG_UIC_HW_REV", ()),
    0x01: ("REG_UIC_FW_REV", ()),
    0x05: ("REG_VDM_INT", ()),
    0x06: ("REG_USBC_STATUS1", (
        ("VBADC", 7, 4, VBADC),
        ("UIDADC", 2, 0, None),
    )),
    0x07: ("REG_USBC_STATUS2", (("SYSMsg", 7, 0, None),)),
    0x08: ("REG_BC_STATUS", (
        ("VBUSDet", 7, 7, None),
        ("PrChgTyp", 5, 3, PRCHGTYP),
        ("DCDTmo", 2, 2, None),
        ("ChgTyp", 1, 0, None),
    )),
    0x09: ("REG_UIC_FW_MINOR", ()),
    0x0A: ("REG_CC_STATUS0", (
        ("CCPinStat", 7, 6, CCPINSTAT),
        ("CCIStat", 5, 4, None),
        ("CCVcnStat", 3, 3, None),
        ("CCStat", 2, 0, CCSTAT),
    )),
    0x0B: ("REG_CC_STATUS1", (
        ("CCSBUSHORT", 7, 6, None),
        ("VCONNOCP", 5, 5, None),
        ("VCONNSC", 4, 4, None),
        ("VSAFE0V", 3, 3, None),
        ("AttachSrcErr", 2, 2, None),
        ("ConnStat", 1, 1, None),
        ("Altmode", 0, 0, None),
    )),
    0x0C: ("REG_PD_STATUS0", (("PDMsg", 7, 0, None),)),
    0x0D: ("REG_PD_STATUS1", (
        ("PD_DataRole", 7, 7, None),
        ("PD_ENTER_MODE", 5, 5, None),
        ("PD_PSRDY", 4, 4, None),
        ("FCT_ID", 3, 0, None),
    )),
    0x0E: ("REG_UIC_INT_M", ()),
    0x0F: ("REG_CC_INT_M", ()),
    0x10: ("REG_PD_INT_M", ()),
}
EXPECTED_ADDRESSES = tuple(sorted(REGISTERS))
# 0x05 is read but is REG_VDM_INT, and reading the interrupt block clears it.
READ_TO_CLEAR_ADDRESSES = (0x05,)


def stage_b_safety_contract(script: str = STAGE_B_SCRIPT) -> dict[str, Any]:
    """Structural, not a token lint: prove the one body read and its target.

    The probe's token contract was reviewed and found to pass nine of ten
    dangerous scripts, so this one asserts the shape of the script instead of
    scanning it for bad words.
    """
    lines = [line.strip() for line in script.splitlines()]
    body_reads = [line for line in lines if line.split(" ")[0] in {"cat", "od", "head", "tail", "dd"}]
    assignments = [line for line in lines if line.startswith("target=")]
    value = {
        "body_read_count": len(body_reads),
        "body_read_line": body_reads[0] if len(body_reads) == 1 else None,
        "target_assignment_count": len(assignments),
        "target_assignment": assignments[0] if len(assignments) == 1 else None,
        "redirect_count": len(re.findall(r"(?<!2)>", script)),
        "forbidden_path_hits": sorted(
            path for path in FORBIDDEN_PATHS if path in script
        ),
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "script_size": len(script.encode("utf-8")),
    }
    value["single_body_read_of_pinned_target"] = (
        value["body_read_count"] == 1
        and value["body_read_line"] == 'cat "$target"'
        and value["target_assignment_count"] == 1
        and value["target_assignment"] == f"target={REG_PATH}"
        and value["redirect_count"] == 0
        and not value["forbidden_path_hits"]
    )
    value["result"] = "pass" if value["single_body_read_of_pinned_target"] else "fail"
    return value


def repo_root() -> Path:
    for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise StageBError("repository root not found")


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


def decode(address: int, value: int) -> dict[str, Any]:
    name, fields = REGISTERS[address]
    decoded: dict[str, Any] = {}
    for field, high, low, table in fields:
        raw = (value >> low) & ((1 << (high - low + 1)) - 1)
        decoded[field] = raw if table is None else {
            "value": raw,
            "name": table.get(raw, "reserved"),
        }
    return {
        "register": name,
        "address": f"0x{address:02x}",
        "value": f"0x{value:02x}",
        "fields": decoded,
        "read_to_clear": address in READ_TO_CLEAR_ADDRESSES,
    }


ROW_RE = re.compile(r"^0x([0-9a-fA-F]{2})\s+0x([0-9a-fA-F]{2})$")


def parse_stage_b(text: str) -> dict[str, Any]:
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
        if current is not None and len(row) == 1:
            sections[current].append(row[0])
    body = sections.get("body", [])
    scalars = {row[0]: row[1] for row in rows if len(row) == 2 and row[0] not in {"stage_b", "body"}}
    pairs: list[tuple[int, int]] = []
    header_seen = False
    unparsed: list[str] = []
    for line in body:
        if line.split() == ["reg", "val"]:
            header_seen = True
            continue
        match = ROW_RE.match(line.strip())
        if match is None:
            unparsed.append(line)
            continue
        pairs.append((int(match.group(1), 16), int(match.group(2), 16)))
    addresses = tuple(address for address, _ in pairs)
    known = [pair for pair in pairs if pair[0] in REGISTERS]
    return {
        "reached_end": ("stage_b", "end") in {tuple(row[:2]) for row in rows},
        "target_present": scalars.get("target_present"),
        "body_rc": scalars.get("body_rc"),
        "header_seen": header_seen,
        "row_count": len(pairs),
        "unparsed_rows": unparsed,
        "addresses": [f"0x{address:02x}" for address in addresses],
        "addresses_match_expected": addresses == EXPECTED_ADDRESSES,
        "registers": [decode(address, value) for address, value in known],
        # A failed i2c read is assigned through an int-to-uchar truncation in
        # mxim_debug_i2c_read, so an all-zero dump is the signature to refuse.
        "all_zero": bool(pairs) and all(value == 0 for _, value in pairs),
        "identity_nonzero": any(
            value != 0 for address, value in pairs if address in (0x00, 0x01)
        ),
    }


def collect(root: Path) -> dict[str, Any]:
    contract = stage_b_safety_contract()
    if contract["result"] != "pass":
        raise StageBError("stage B safety contract failed before any device contact")
    run_dir = allocate_run_dir(root)
    capture_dir = raw_capture.prepare_capture_dir(run_dir, "raw-stage-b")
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
        raise StageBError(f"stage B inventory failed: {exc}") from exc
    selection = prior.select_exact_s22(inventory_text)
    try:
        handle = raw_capture.acquire_command(
            [str(adb), "-s", selection.serial, "exec-out", "su", "-c", STAGE_B_SCRIPT],
            capture_dir,
            "0001-max77705-reg",
            timeout=20,
            stdout_maximum=MAX_BODY_BYTES,
            stderr_maximum=d0.MAX_TEXT_OUTPUT,
        )
    except raw_capture.RawCaptureError as exc:
        raise StageBError(f"stage B raw acquisition failed: {exc}") from exc
    payload = raw_capture.read_stdout(handle, maximum=MAX_BODY_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=d0.MAX_TEXT_OUTPUT)
    observation = parse_stage_b(payload.decode("utf-8", "replace"))
    complete = (
        observation["reached_end"]
        and observation["target_present"] == "yes"
        and observation["body_rc"] == "0"
        and observation["header_seen"]
        and observation["addresses_match_expected"]
        and not observation["unparsed_rows"]
        and not observation["all_zero"]
        and observation["identity_nonzero"]
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
        "vdm_int_cleared_by_this_read": True,
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
    parser.add_argument(
        "--accept-vdm-int-clear",
        action="store_true",
        help=(
            "acknowledge that reading reg also reads 0x05 REG_VDM_INT, which the "
            "controller clears on read, so a latched alternate-mode interrupt is "
            "consumed before the driver sees it"
        ),
    )
    args = parser.parse_args(argv)
    contract = stage_b_safety_contract()
    if args.validate:
        value = {
            "schema": SCHEMA,
            "version": VERSION,
            "verdict": "PASS_S22PLUS_FYG8_P319_MAX77705_REG_STAGE_B_H0_READY",
            "safety": contract,
            "expected_addresses": [f"0x{address:02x}" for address in EXPECTED_ADDRESSES],
            "read_to_clear_addresses": [f"0x{a:02x}" for a in READ_TO_CLEAR_ADDRESSES],
            "device_contact": False,
            "live_authorized": False,
        }
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0 if contract["result"] == "pass" else 2
    if not args.accept_vdm_int_clear:
        print(
            "P3.19 Stage B refused: reading reg also reads 0x05 REG_VDM_INT, which "
            "the controller clears on read. Re-run with --accept-vdm-int-clear "
            "once the unit is not mid-negotiation.",
            file=sys.stderr,
        )
        return 3
    try:
        value = collect(repo_root())
    except (StageBError, prior.SysfsD0Error) as exc:
        print(f"P3.19 Stage B error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0 if value["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
