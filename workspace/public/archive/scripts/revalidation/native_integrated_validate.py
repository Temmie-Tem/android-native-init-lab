#!/usr/bin/env python3
"""Run one integrated non-destructive native-init validation gate."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
A90CTL = REPO_ROOT / "scripts" / "revalidation" / "a90ctl.py"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.53 (v153)"

DEFAULT_COMMANDS = [
    "version",
    "status",
    "bootstatus",
    "selftest verbose",
    "pid1guard verbose",
    "exposure guard",
    "exposure verbose",
    "policycheck run",
    "policycheck verbose",
    "service list",
    "service status autohud",
    "service status tcpctl",
    "service status rshell",
    "netservice status",
    "rshell audit",
    "hide",
    "runtime",
    "helpers status",
    "userland status",
    "storage",
    "mountsd status",
    "wififeas gate",
    "diag summary",
    "screenmenu",
    "hide",
]


@dataclass
class ValidationResult:
    index: int
    command: str
    rc: int
    protocol_rc: int | None
    protocol_status: str
    duration_sec: float
    errors: list[str]
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=45.0, help="per-command timeout seconds")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out", default="tmp/validation/native-integrated-v153.txt")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--command", action="append", dest="commands", help="override default command list; may be repeated")
    return parser.parse_args()


def a90ctl_command(args: argparse.Namespace, command: str) -> list[str]:
    return [
        sys.executable,
        str(A90CTL),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(int(args.timeout)),
        "--json",
        *shlex.split(command),
    ]


def run_command(args: argparse.Namespace, index: int, command: str) -> tuple[ValidationResult, dict[str, object] | None]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            a90ctl_command(args, command),
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=args.timeout + 5,
            check=False,
        )
        duration = time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = (exc.stdout or "") + (exc.stderr or "")
        return ValidationResult(index, command, 124, None, "timeout", args.timeout + 5, ["host timeout"], text), None

    payload: dict[str, object] | None = None
    errors: list[str] = []
    protocol_rc: int | None = None
    protocol_status = "missing"
    text = proc.stdout
    try:
        payload = json.loads(proc.stdout)
        end = payload.get("end", {})
        if isinstance(end, dict):
            protocol_status = str(end.get("status", "missing"))
            protocol_rc = int(str(end.get("rc", "1")), 0)
        text = str(payload.get("text", proc.stdout))
    except (ValueError, TypeError) as exc:
        errors.append(f"invalid a90ctl json: {exc}")

    if proc.returncode != 0:
        errors.append(f"a90ctl rc={proc.returncode}")
    if "A90P1 END" not in text:
        errors.append("missing A90P1 END frame")
    if protocol_status != "ok":
        errors.append(f"protocol status={protocol_status}")
    if protocol_rc != 0:
        errors.append(f"protocol rc={protocol_rc}")

    result = ValidationResult(index, command, proc.returncode, protocol_rc, protocol_status, duration, errors, text)
    return result, payload


def contains(text: str, needle: str, errors: list[str], message: str) -> None:
    if needle not in text:
        errors.append(message)


def validate_semantics(args: argparse.Namespace, result: ValidationResult) -> None:
    command = result.command
    text = result.text
    errors = result.errors

    if command == "version":
        contains(text, args.expect_version, errors, f"missing expected version {args.expect_version!r}")
    elif command == "status":
        for needle in ("selftest: pass=", "pid1guard:", "exposure: guard="):
            contains(text, needle, errors, f"status missing {needle}")
    elif command == "bootstatus":
        for needle in ("selftest:", "pid1guard:", "exposure:"):
            contains(text, needle, errors, f"bootstatus missing {needle}")
    elif command.startswith("selftest"):
        contains(text, "fail=0", errors, "selftest fail count is not zero")
    elif command.startswith("pid1guard"):
        contains(text, "fail=0", errors, "pid1guard fail count is not zero")
    elif command == "exposure guard":
        contains(text, "guard=ok", errors, "exposure guard is not ok")
        contains(text, "fail=0", errors, "exposure fail count is not zero")
    elif command == "exposure verbose":
        contains(text, "accepted_boundary=F021/F030", errors, "exposure missing accepted boundary note")
        contains(text, "no_token_values=yes", errors, "exposure did not confirm token redaction")
    elif command.startswith("policycheck"):
        contains(text, "fail=0", errors, "policycheck fail count is not zero")
    elif command == "service list":
        for needle in ("autohud", "tcpctl", "rshell"):
            contains(text, needle, errors, f"service list missing {needle}")
    elif command.startswith("service status"):
        contains(text, "service:", errors, "service status output missing service prefix")
    elif command == "netservice status":
        contains(text, "netservice:", errors, "netservice status output missing prefix")
    elif command == "rshell audit":
        contains(text, "rshell-audit:", errors, "rshell audit output missing prefix")
        if "token_value=" in text:
            errors.append("rshell audit may expose token value")
    elif command == "runtime":
        contains(text, "runtime:", errors, "runtime output missing prefix")
    elif command == "helpers status":
        contains(text, "helpers:", errors, "helpers output missing prefix")
    elif command == "userland status":
        contains(text, "userland:", errors, "userland output missing prefix")
    elif command == "storage":
        contains(text, "storage:", errors, "storage output missing prefix")
    elif command == "mountsd status":
        contains(text, "mountsd:", errors, "mountsd status output missing prefix")
    elif command == "wififeas gate":
        contains(text, "wififeas:", errors, "wififeas gate output missing prefix")
    elif command == "diag summary":
        contains(text, "[A90 DIAG]", errors, "diag summary missing diag section")
    elif command == "screenmenu":
        contains(text, "show requested", errors, "screenmenu did not report show request")
    elif command == "hide":
        contains(text, "hide requested", errors, "hide did not report hide request")


def append_transcript(lines: list[str], result: ValidationResult) -> None:
    verdict = "PASS" if not result.errors else "FAIL"
    lines.append(
        f"== {result.index:02d} {verdict} :: {result.command} :: "
        f"host_rc={result.rc} proto_rc={result.protocol_rc} "
        f"status={result.protocol_status} duration={result.duration_sec:.3f}s ==\n"
    )
    lines.append(result.text.rstrip() + "\n")
    if result.errors:
        lines.append("ERRORS:\n")
        for error in result.errors:
            lines.append(f"- {error}\n")
    lines.append("\n")


def main() -> int:
    args = parse_args()
    commands = args.commands or DEFAULT_COMMANDS
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    transcript: list[str] = []
    transcript.append("# Native Init Integrated Validation\n")
    transcript.append(f"expect_version={args.expect_version}\n")
    transcript.append(f"timeout={args.timeout}\n")
    transcript.append("commands=" + ", ".join(commands) + "\n\n")

    results: list[ValidationResult] = []
    for index, command in enumerate(commands, start=1):
        result, _payload = run_command(args, index, command)
        validate_semantics(args, result)
        results.append(result)
        append_transcript(transcript, result)
        out_path.write_text("".join(transcript))
        if result.errors:
            print(f"FAIL command={command}: {'; '.join(result.errors)}")
            print(out_path)
            if args.json_out:
                Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
                Path(args.json_out).write_text(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
            return 1

    out_path.write_text("".join(transcript))
    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))
    print(f"PASS commands={len(results)}")
    print(out_path)
    if args.json_out:
        print(args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
