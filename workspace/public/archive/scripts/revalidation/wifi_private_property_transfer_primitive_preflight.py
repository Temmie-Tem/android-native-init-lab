#!/usr/bin/env python3
"""Read-only preflight for v317 ACM transfer primitives."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v318-private-property-transfer-primitive-preflight")
TOYBOX = "/cache/bin/toybox"
SHA256_RE = re.compile(r"\b([0-9a-fA-F]{64})\b")


@dataclass
class CommandCapture:
    name: str
    argv: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class PrimitiveCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def capture_command(args: argparse.Namespace,
                    store: EvidenceStore,
                    name: str,
                    argv: list[str]) -> CommandCapture:
    started = time.monotonic()
    try:
        result: ProtocolResult = run_cmdv1_command(args.host, args.port, args.timeout, argv, retry_unsafe=False)
        duration = time.monotonic() - started
        path = store.write_text(f"commands/{name}.txt", result.text)
        return CommandCapture(name, argv, result.rc == 0 and result.status == "ok", result.rc, result.status, duration, str(path.relative_to(store.run_dir)), "")
    except Exception as exc:  # noqa: BLE001 - preserve preflight failure evidence
        duration = time.monotonic() - started
        path = store.write_text(f"commands/{name}.txt", str(exc) + "\n")
        return CommandCapture(name, argv, False, None, "missing", duration, str(path.relative_to(store.run_dir)), str(exc))


def capture_text(store: EvidenceStore, capture: CommandCapture) -> str:
    return (store.run_dir / capture.file).read_text(encoding="utf-8", errors="replace")


def command_ok(captures: dict[str, CommandCapture], name: str) -> bool:
    capture = captures.get(name)
    return bool(capture and capture.ok)


def sha_from_text(text: str) -> str:
    match = SHA256_RE.search(text)
    return match.group(1).lower() if match else ""


def build_checks(store: EvidenceStore, captures: dict[str, CommandCapture]) -> list[PrimitiveCheck]:
    toybox_text = capture_text(store, captures["toybox-help"]) if "toybox-help" in captures else ""
    base64_text = capture_text(store, captures["base64-help"]) if "base64-help" in captures else ""
    uudecode_text = capture_text(store, captures["uudecode-help"]) if "uudecode-help" in captures else ""
    touch_text = capture_text(store, captures["touch-help"]) if "touch-help" in captures else ""
    writefile_text = capture_text(store, captures["writefile-usage"]) if "writefile-usage" in captures else ""
    shell_text = capture_text(store, captures["sh-probe"]) if "sh-probe" in captures else ""
    return [
        PrimitiveCheck(
            "toybox-present",
            "pass" if command_ok(captures, "toybox-help") else "blocked",
            "blocker",
            "toybox command must execute",
            ["run /cache/bin/toybox"],
        ),
        PrimitiveCheck(
            "toybox-uudecode-output",
            "pass" if command_ok(captures, "uudecode-help") and "-o" in uudecode_text and "OUTFILE" in uudecode_text else "blocked",
            "blocker",
            "toybox uudecode must support input-file to output-file decoding",
            ["run /cache/bin/toybox uudecode --help"],
        ),
        PrimitiveCheck(
            "toybox-base64-file-input",
            "pass" if command_ok(captures, "base64-help") and "-d" in base64_text and "[FILE...]" in base64_text else "blocked",
            "blocker",
            "toybox base64 must support decode and file input for readback/diagnostics",
            ["run /cache/bin/toybox base64 --help"],
        ),
        PrimitiveCheck(
            "toybox-touch",
            "pass" if command_ok(captures, "touch-help") and "usage: touch" in touch_text else "blocked",
            "blocker",
            "toybox touch must exist so the approved live proof can create ASCII staging files before writefile",
            ["run /cache/bin/toybox touch --help"],
        ),
        PrimitiveCheck(
            "writefile-command",
            "pass" if "usage: writefile <path> <value...>" in writefile_text else "blocked",
            "blocker",
            "native writefile command must exist for approved ASCII uuencoded staging",
            ["writefile"],
        ),
        PrimitiveCheck(
            "sha256sum-proc",
            "pass" if command_ok(captures, "sha256-proc-version") and bool(sha_from_text(capture_text(store, captures["sha256-proc-version"]))) else "blocked",
            "blocker",
            "toybox sha256sum must hash a read-only proc file",
            ["run /cache/bin/toybox sha256sum /proc/version"],
        ),
        PrimitiveCheck(
            "toybox-sh-unavailable",
            "warn" if "Unknown command sh" in shell_text else "pass",
            "info",
            "toybox sh is not required; v317 transfer must avoid shell pipelines/redirection",
            ["run /cache/bin/toybox sh -c 'printf A90_SH_OK'"],
        ),
        PrimitiveCheck(
            "no-write-scope",
            "pass",
            "info",
            "preflight uses only read-only commands and no file creation/removal",
            [],
        ),
    ]


def decide(checks: list[PrimitiveCheck]) -> tuple[str, bool, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "private-property-transfer-primitive-preflight-blocked", False, "blocked checks: " + ", ".join(blockers)
    return "private-property-transfer-primitive-preflight-ready", True, "read-only transfer primitive checks passed"


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# v318 Private Property Transfer Primitive Preflight",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Checks",
        "",
        "| name | status | severity | detail |",
        "| --- | --- | --- | --- |",
    ]
    for check in manifest["checks"]:
        lines.append(f"| `{check['name']}` | `{check['status']}` | `{check['severity']}` | {check['detail']} |")
    lines.extend(["", "## Commands", "", "| name | ok | rc | status | file |", "| --- | --- | --- | --- | --- |"])
    for capture in manifest["captures"]:
        lines.append(f"| `{capture['name']}` | `{capture['ok']}` | `{capture['rc']}` | `{capture['status']}` | `{capture['file']}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    captures = {
        "hide-menu": capture_command(args, store, "hide-menu", ["hide"]),
        "toybox-help": capture_command(args, store, "toybox-help", ["run", TOYBOX]),
        "base64-help": capture_command(args, store, "base64-help", ["run", TOYBOX, "base64", "--help"]),
        "uudecode-help": capture_command(args, store, "uudecode-help", ["run", TOYBOX, "uudecode", "--help"]),
        "touch-help": capture_command(args, store, "touch-help", ["run", TOYBOX, "touch", "--help"]),
        "writefile-usage": capture_command(args, store, "writefile-usage", ["writefile"]),
        "sh-probe": capture_command(args, store, "sh-probe", ["run", TOYBOX, "sh", "-c", "printf A90_SH_OK"]),
        "sha256-proc-version": capture_command(args, store, "sha256-proc-version", ["run", TOYBOX, "sha256sum", "/proc/version"]),
    }
    checks = build_checks(store, captures)
    decision, pass_ok, reason = decide(checks)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "checks": [asdict(check) for check in checks],
        "captures": [asdict(capture) for capture in captures.values()],
        "device_mutations": False,
        "blocked_actions": [
            "file write/redirection",
            "mkdir/rm/mv",
            "NCM/tcpctl start",
            "daemon start",
            "Wi-Fi bring-up",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
