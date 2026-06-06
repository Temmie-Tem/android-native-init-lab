#!/usr/bin/env python3
"""Shared helpers for read-only A90 kernel evidence collectors."""

from __future__ import annotations

import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402
from a90harness.evidence import (  # noqa: E402
    PRIVATE_DIR_MODE,
    PRIVATE_FILE_MODE,
    ensure_private_dir,
    write_private_bytes,
    write_private_json as _write_private_json,
    write_private_text,
)


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
CONFIG_RE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
CONFIG_NOT_SET_RE = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")


@dataclass
class CommandCapture:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    text: str
    error: str


def write_private_json(path: Path, data: Any) -> None:
    _write_private_json(path, data)


def repo_path(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else REPO_ROOT / value


def run_host_command(command: list[str], timeout: int = 10) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def collect_host_metadata() -> dict[str, Any]:
    rc, head = run_host_command(["git", "rev-parse", "--short", "HEAD"], timeout=5)
    status_rc, status = run_host_command(["git", "status", "--short"], timeout=5)
    return {
        "repo": str(REPO_ROOT),
        "git_head": head.strip() if rc == 0 else "unknown",
        "git_dirty": bool(status.strip()) if status_rc == 0 else None,
        "git_status_short": status.splitlines() if status_rc == 0 and status.strip() else [],
    }


def run_capture(args: Any, name: str, command: list[str], timeout: float | None = None) -> CommandCapture:
    started = time.monotonic()
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            timeout if timeout is not None else args.timeout,
            command,
            retry_unsafe=False,
        )
        duration = time.monotonic() - started
        ok = result.rc == 0 and result.status == "ok"
        return CommandCapture(name, " ".join(command), ok, result.rc, result.status, duration, result.text, "")
    except Exception as exc:  # noqa: BLE001 - collectors preserve failure evidence
        duration = time.monotonic() - started
        return CommandCapture(name, " ".join(command), False, None, "missing", duration, "", str(exc))


def capture_to_manifest(capture: CommandCapture) -> dict[str, Any]:
    data = asdict(capture)
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    return data


def strip_cmdv1_text(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("a90:/#"):
            continue
        if line.startswith("A90P1 BEGIN ") or line.startswith("A90P1 END "):
            continue
        if line.startswith("[done] ") or line.startswith("[exit "):
            continue
        if line.startswith("run: pid="):
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def parse_kernel_config(text: str) -> dict[str, str]:
    config: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = CONFIG_RE.match(line)
        if match:
            config[match.group(1)] = match.group(2).strip('"')
            continue
        match = CONFIG_NOT_SET_RE.match(line)
        if match:
            config[match.group(1)] = "n"
    return config


def config_state(config: dict[str, str], name: str) -> str:
    return config.get(name, "unset")


def config_enabled(config: dict[str, str], name: str) -> bool:
    return config_state(config, name) in {"y", "m"}


def summarize_options(config: dict[str, str], options: list[str]) -> dict[str, int]:
    summary = {"y": 0, "m": 0, "n": 0, "unset": 0, "value": 0}
    for option in options:
        value = config_state(config, option)
        if value in summary:
            summary[value] += 1
        else:
            summary["value"] += 1
    return summary


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    escaped_headers = [header.replace("|", "\\|") for header in headers]
    lines = [
        "| " + " | ".join(escaped_headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        escaped = [str(cell).replace("|", "\\|").replace("\n", "<br>") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def fetch_kernel_config(args: Any) -> tuple[CommandCapture, str, dict[str, str]]:
    capture = run_capture(args, "config-zcat", ["run", "/cache/bin/toybox", "zcat", "/proc/config.gz"], timeout=args.timeout)
    config_text = strip_cmdv1_text(capture.text) if capture.text else ""
    return capture, config_text, parse_kernel_config(config_text)
