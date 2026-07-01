#!/usr/bin/env python3
"""Host side of the read-only boot-target auditor (§7.1).

Parses the device `boot-audit` command's `A90BOOTAUDIT key=value` output into the boot-target
guard's BlockIdentity, evaluates it (discovery/auditor mode — unconfirmed pin allowed), and emits a
proposed auditor-confirmed BootTargetPin (rdev + canonical + diskseq) for the operator to adopt into
the eventual write path. Read-only: this never triggers a write; it only reads and decides.

Trust-boundary hardening (Codex review 3, P4): the parser accepts ONLY records inside a single valid
`begin ... end rc=0` block, rejects duplicate/injected keys, and a write-authorizing pin is proposed
ONLY when the device reported authoritative=1 (the default boot target), read=ok, end rc=0, and the
identity passes the guard. A forged/replayed line cannot corrupt the identity or promote a pin.

Pure-function core (parse_audit_output / audit_to_identity / assess) is offline-testable; --run
sends the command over the serial bridge and assesses the live output.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import asdict

from a90_boot_target_guard import (
    BlockIdentity,
    BootTargetPin,
    evaluate_boot_target,
)

AUDIT_PREFIX = "A90BOOTAUDIT"
_END_RC_RE = re.compile(r"rc=(-?\d+)")


def parse_audit_output(text: str) -> dict:
    """Extract A90BOOTAUDIT key=value pairs from ONE valid begin/end block.

    Fail-closed structural parse (Codex review 3): raises ValueError on any of
      - a record before `begin` or after `end` (trailing/injected line),
      - a second `begin` (nested/replayed block),
      - a duplicate data key (injected/overwriting line),
      - a missing/malformed `begin` or `end` marker.
    The parsed dict carries `_end_rc` (int) so callers can require `end rc=0`.
    """
    out: dict[str, str] = {}
    seen_begin = False
    seen_end = False
    end_rc: int | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(AUDIT_PREFIX):
            continue
        rest = line[len(AUDIT_PREFIX):].strip()
        if rest == "begin":
            if seen_begin:
                raise ValueError("multiple A90BOOTAUDIT begin markers (nested/replayed block)")
            seen_begin = True
            continue
        if not seen_begin:
            raise ValueError("A90BOOTAUDIT record before begin marker (injected)")
        if seen_end:
            raise ValueError("A90BOOTAUDIT record after end marker (trailing/injected)")
        if rest.startswith("end"):
            m = _END_RC_RE.search(rest)
            if m is None:
                raise ValueError(f"malformed A90BOOTAUDIT end marker: {rest!r}")
            end_rc = int(m.group(1))
            seen_end = True
            continue
        if "=" not in rest:
            raise ValueError(f"unexpected bare marker inside block: {rest!r}")
        key, _, val = rest.partition("=")
        key = key.strip()
        val = val.strip()
        if key in out:
            raise ValueError(f"duplicate A90BOOTAUDIT key {key!r} (injected/replayed record)")
        out[key] = val
    if not seen_begin:
        raise ValueError("no A90BOOTAUDIT begin marker")
    if not seen_end:
        raise ValueError("no A90BOOTAUDIT end marker (truncated output)")
    out["_end_rc"] = end_rc  # type: ignore[assignment]
    return out


def audit_to_identity(parsed: dict) -> BlockIdentity:
    """Build the guard's BlockIdentity from parsed audit fields. Raises on missing essentials or on
    a canonical/sysfs that does not consistently describe the same fd-derived rdev."""
    if parsed.get("open") != "ok":
        raise ValueError(f"boot-audit did not open the target (open={parsed.get('open')!r})")
    rdev = parsed.get("rdev", "")
    if ":" not in rdev:
        raise ValueError(f"missing/invalid rdev: {rdev!r}")
    major_s, _, minor_s = rdev.partition(":")
    if not (major_s.isdigit() and minor_s.isdigit()):
        raise ValueError(f"non-numeric rdev: {rdev!r}")
    major, minor = int(major_s), int(minor_s)
    size_field = parsed.get("size_bytes", "")
    if not size_field.isdigit():
        raise ValueError(f"missing/invalid size_bytes: {size_field!r}")
    # canonical must be an absolute /dev/block/... path — never "unresolved ..." or relative.
    canonical = parsed.get("canonical", "")
    if not canonical.startswith("/dev/block/"):
        raise ValueError(f"canonical is not an absolute /dev/block path: {canonical!r}")
    # sysfs, when present, must describe the SAME rdev (cross-check fd-derived identity consistency).
    sysfs = parsed.get("sysfs")
    if sysfs is not None and sysfs != f"/sys/dev/block/{major}:{minor}":
        raise ValueError(f"sysfs {sysfs!r} does not match rdev {major}:{minor}")
    diskseq = parsed.get("diskseq")
    diskseq_val = int(diskseq) if (diskseq and diskseq.isdigit()) else None
    return BlockIdentity(
        canonical_path=canonical,
        rdev_major=major,
        rdev_minor=minor,
        partname=parsed.get("partname", ""),
        size_bytes=int(size_field),
        is_block=parsed.get("is_block") == "1",
        diskseq=diskseq_val,
    )


def proposed_pin(identity: BlockIdentity) -> BootTargetPin:
    """The auditor-confirmed pin an operator would adopt for the write path (§2). Callers must only
    adopt this when pin_allowed() is satisfied (authoritative + read=ok + end rc=0 + guard-ok)."""
    return BootTargetPin(
        canonical_path=identity.canonical_path,
        rdev_major=identity.rdev_major,
        rdev_minor=identity.rdev_minor,
        diskseq=identity.diskseq,
    )


def pin_allowed(parsed: dict, evaluate_ok: bool) -> tuple[bool, str]:
    """Decide whether a write-authorizing pin may be proposed from this audit. Fail-closed."""
    if parsed.get("authoritative") != "1":
        return False, "non-authoritative target (only the default boot device may propose a pin)"
    if parsed.get("_end_rc") != 0:
        return False, f"audit end rc != 0 (rc={parsed.get('_end_rc')})"
    if not str(parsed.get("read", "")).startswith("ok"):
        return False, f"read did not succeed (read={parsed.get('read')!r})"
    if not evaluate_ok:
        return False, "identity failed the boot-target guard"
    return True, "authoritative read-verified boot target"


def assess(text: str) -> dict:
    """Full offline assessment of raw device output. Returns a report dict."""
    report: dict = {}
    try:
        parsed = parse_audit_output(text)
    except ValueError as exc:
        report["ok"] = False
        report["error"] = f"parse: {exc}"
        return report
    report["parsed"] = parsed
    try:
        identity = audit_to_identity(parsed)
    except ValueError as exc:
        report["ok"] = False
        report["error"] = str(exc)
        return report
    result = evaluate_boot_target(identity)  # discovery mode (unconfirmed pin allowed)
    report["identity"] = asdict(identity)
    report["evaluate_ok"] = result.ok
    report["evaluate_reason"] = result.reason
    allowed, pin_reason = pin_allowed(parsed, result.ok)
    report["pin_reason"] = pin_reason
    report["proposed_pin"] = asdict(proposed_pin(identity)) if allowed else None
    report["ok"] = result.ok and allowed
    return report


def _run_live(args) -> str:
    """Send `boot-audit` over the serial bridge and return raw output."""
    from a90ctl import run_cmdv1_command  # local import; live-only. Defined in a90ctl, not a90_transport.
    result = run_cmdv1_command(args.bridge_host, args.bridge_port, args.bridge_timeout,
                               ["boot-audit"] + ([args.target] if args.target else []))
    return result.text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="send boot-audit over the bridge (live)")
    ap.add_argument("--target", default=None, help="optional target path to audit read-only")
    ap.add_argument("--from-file", type=str, help="assess captured output from a file instead")
    ap.add_argument("--bridge-host", default="127.0.0.1")
    ap.add_argument("--bridge-port", type=int, default=54321)
    ap.add_argument("--bridge-timeout", type=float, default=20.0)
    args = ap.parse_args()

    if args.from_file:
        text = open(args.from_file).read()
    elif args.run:
        text = _run_live(args)
    else:
        text = sys.stdin.read()

    import json
    report = assess(text)
    print(json.dumps(report, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
