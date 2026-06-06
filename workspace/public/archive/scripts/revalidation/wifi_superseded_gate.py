#!/usr/bin/env python3
"""Fail-closed evidence helper for superseded Wi-Fi gates."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_PARENT = Path("tmp/wifi")


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def arg_value(argv: list[str], name: str) -> str | None:
    prefix = name + "="
    for index, value in enumerate(argv):
        if value == name and index + 1 < len(argv):
            return argv[index + 1]
        if value.startswith(prefix):
            return value[len(prefix):]
    return None


def approval_phrase(argv: list[str]) -> str:
    return arg_value(argv, "--approval-phrase") or ""


def ensure_private_dir(path: Path) -> None:
    try:
        os.mkdir(path, 0o700)
    except FileExistsError:
        st = os.lstat(path)
        if not os.path.isdir(path) or os.path.islink(path):
            raise RuntimeError(f"refusing unsafe output path: {path}")
        os.chmod(path, 0o700)
        if (st.st_mode & 0o077) != 0:
            os.chmod(path, 0o700)


def safe_write_text(path: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def make_manifest(*, gate: str, argv: list[str], next_phrase: str, replacement_script: str,
                  reason: str) -> dict[str, Any]:
    phrase = approval_phrase(argv)
    return {
        "generated_at": now_iso(),
        "gate": gate,
        "decision": "v409-superseded-by-v410",
        "pass": True,
        "reason": reason,
        "next_step": "use the V410 gate instead",
        "argv": argv,
        "approval_phrase_provided": phrase,
        "superseded_by": "v410",
        "replacement_script": replacement_script,
        "required_next_approval_phrase": next_phrase,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
    }


def render_readme(manifest: dict[str, Any]) -> str:
    return "\n".join([
        f"# {manifest['gate']} Superseded Gate",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- replacement_script: `{manifest['replacement_script']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Required Next Approval Phrase",
        "",
        f"`{manifest['required_next_approval_phrase']}`",
        "",
    ]) + "\n"


def run_superseded_gate(*, gate: str, default_slug: str, next_phrase: str,
                        replacement_script: str, reason: str) -> int:
    argv = sys.argv[1:]
    out_dir_value = arg_value(argv, "--out-dir")
    out_dir = Path(out_dir_value) if out_dir_value else DEFAULT_PARENT / f"{default_slug}-{now_stamp()}"
    ensure_private_dir(out_dir)

    manifest = make_manifest(
        gate=gate,
        argv=argv,
        next_phrase=next_phrase,
        replacement_script=replacement_script,
        reason=reason,
    )
    safe_write_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    safe_write_text(out_dir / "README.md", render_readme(manifest))

    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {out_dir.resolve()}")
    return 0
