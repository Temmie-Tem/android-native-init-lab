#!/usr/bin/env python3
"""Normalize one post-reboot stock HS-PHY dmesg baseline for P3.03."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat

import s22plus_fyg8_p303_telemetry_spec as spec


SCHEMA = "s22plus_fyg8_p303_stock_log_baseline_v1"
PARSER_ID = "s22plus-fyg8-p303-stock-hsphy-log-baseline-v1"
VERDICT = "PASS_P303_STOCK_HSPHY_LOG_BASELINE_D0"
NORMAL_PATH = b"msm_hsphy_enable_clocks():"
RESET_ASSERT = b"phy_reset assert failed"
RESET_DEASSERT = b"phy_reset deassert failed"
READBACK = re.compile(
    rb"msm_usb_write_readback:\s+write:\s+[0-9a-fA-F]+\s+"
    rb"to\s+QSCRATCH:\s+([0-9a-fA-F]+)\s+FAILED"
)


class BaselineError(ValueError):
    pass


def _read_regular(path: Path, maximum: int = 16 * 1024 * 1024) -> bytes:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise BaselineError("P3.03 stock dmesg is indirect or not regular")
    if metadata.st_size <= 0 or metadata.st_size > maximum:
        raise BaselineError("P3.03 stock dmesg size is invalid")
    payload = path.read_bytes()
    after = path.stat()
    if (
        len(payload) != metadata.st_size
        or after.st_dev != metadata.st_dev
        or after.st_ino != metadata.st_ino
        or after.st_size != metadata.st_size
        or after.st_mtime_ns != metadata.st_mtime_ns
    ):
        raise BaselineError("P3.03 stock dmesg changed while reading")
    return payload


def parse(payload: bytes) -> dict:
    offsets = [int(match.group(1), 16) for match in READBACK.finditer(payload)]
    if any(offset > 0x1F8 or offset & 3 for offset in offsets):
        raise BaselineError("P3.03 stock readback offset is outside the candidate domain")
    normal_path_count = payload.count(NORMAL_PATH)
    if normal_path_count == 0:
        raise BaselineError("P3.03 stock HS-PHY normal path marker is absent")
    reset_mask = (1 if RESET_ASSERT in payload else 0) | (
        2 if RESET_DEASSERT in payload else 0
    )
    first_offset = offsets[0] if offsets else 0
    detail = spec.encode_log(
        readback_count=len(offsets),
        first_offset=first_offset,
        reset_mask=reset_mask,
    )
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "parser_id": PARSER_ID,
        "normal_path_seen": True,
        "normal_path_count": normal_path_count,
        "readback_failure_count": len(offsets),
        "readback_count_bucket": spec.readback_count_bucket(len(offsets)),
        "first_readback_failure_offset": first_offset,
        "reset_failure_mask": reset_mask,
        "candidate_domain_detail": detail,
        "failure_signature_present": bool(offsets or reset_mask),
        "valid": True,
    }


def inspect(path: Path) -> dict:
    payload = _read_regular(path)
    result = parse(payload)
    result["input"] = {
        "path": path.as_posix(),
        "size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = inspect(args.log)
    except (BaselineError, OSError) as exc:
        print(json.dumps({"schema": SCHEMA, "verdict": "FAIL_CLOSED", "error": str(exc)}))
        return 1
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="ascii")
    print(json.dumps({"schema": SCHEMA, "verdict": VERDICT}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
