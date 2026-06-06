#!/usr/bin/env python3
"""Bundle native long-soak host/device evidence into one handoff directory."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import ProtocolResult, run_cmdv1_command  # noqa: E402

DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.53 (v153)"
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


@dataclass
class CommandCapture:
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


def nofollow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def cloexec_flag() -> int:
    return getattr(os, "O_CLOEXEC", 0)


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PRIVATE_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory bundle path: {path}")
    path.chmod(PRIVATE_DIR_MODE)


def write_private_bytes(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | cloexec_flag() | nofollow_flag()
    fd = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as file:
            fd = -1
            file.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def write_private_text(path: Path, text: str) -> None:
    write_private_bytes(path, text.encode("utf-8"))


def copy_private_regular_file(source: Path, dest: Path) -> None:
    info = source.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"refusing non-regular evidence source: {source}")
    write_private_bytes(dest, source.read_bytes())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="serial bridge host")
    parser.add_argument("--port", type=int, default=54321, help="serial bridge TCP port")
    parser.add_argument("--timeout", type=float, default=15.0, help="per-command timeout")
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--bundle-dir", default="tmp/soak/native-long-soak-v153-bundle")
    parser.add_argument("--host-jsonl", default="tmp/soak/native-long-soak-v153-host.jsonl")
    parser.add_argument("--device-jsonl", default="tmp/soak/native-long-soak-v153-device.jsonl")
    parser.add_argument("--summary-json", default="tmp/soak/native-long-soak-v153-summary.json")
    parser.add_argument("--correlation-md", default="tmp/soak/native-long-soak-v153-report.md")
    parser.add_argument("--correlation-json", default="tmp/soak/native-long-soak-v153-report.json")
    parser.add_argument("--disconnect-md", default="tmp/soak/native-disconnect-v153.md")
    parser.add_argument("--disconnect-json", default="tmp/soak/native-disconnect-v153.json")
    return parser.parse_args()


def copy_if_exists(source: Path, dest_dir: Path, manifest: list[dict[str, Any]]) -> None:
    try:
        source.lstat()
    except FileNotFoundError:
        manifest.append({"source": str(source), "copied": False, "dest": None, "error": "missing"})
        return
    dest = dest_dir / source.name
    try:
        copy_private_regular_file(source, dest)
    except OSError as exc:
        manifest.append({"source": str(source), "copied": False, "dest": str(dest), "error": str(exc)})
        return
    except RuntimeError as exc:
        manifest.append({"source": str(source), "copied": False, "dest": str(dest), "error": str(exc)})
        return
    manifest.append({"source": str(source), "copied": True, "dest": str(dest), "error": ""})


def run_capture(args: argparse.Namespace, out_dir: Path, command: list[str]) -> CommandCapture:
    started = time.monotonic()
    name = "-".join(command).replace("/", "_")
    out_file = out_dir / f"cmd-{name}.txt"
    try:
        result: ProtocolResult = run_cmdv1_command(
            args.host,
            args.port,
            args.timeout,
            command,
            retry_unsafe=False,
        )
        duration = time.monotonic() - started
        ok = result.rc == 0 and result.status == "ok"
        text = result.text
        capture = CommandCapture(" ".join(command), ok, result.rc, result.status, duration, str(out_file), "")
    except Exception as exc:  # noqa: BLE001 - bundle keeps failure evidence
        duration = time.monotonic() - started
        text = str(exc) + "\n"
        capture = CommandCapture(" ".join(command), False, None, "missing", duration, str(out_file), str(exc))
    write_private_text(out_file, text)
    return capture


def main() -> int:
    args = parse_args()
    bundle_dir = Path(args.bundle_dir)
    ensure_private_dir(bundle_dir)
    copied: list[dict[str, Any]] = []
    captures: list[CommandCapture] = []

    for source in (
        Path(args.host_jsonl),
        Path(args.device_jsonl),
        Path(args.summary_json),
        Path(args.correlation_md),
        Path(args.correlation_json),
        Path(args.disconnect_md),
        Path(args.disconnect_json),
    ):
        copy_if_exists(source, bundle_dir, copied)

    for command in (
        ["version"],
        ["status"],
        ["bootstatus"],
        ["timeline"],
        ["logpath"],
        ["longsoak", "status", "verbose"],
        ["netservice", "status"],
        ["selftest", "verbose"],
    ):
        captures.append(run_capture(args, bundle_dir, command))

    version_capture = next((item for item in captures if item.command == "version"), None)
    version_text = Path(version_capture.file).read_text(encoding="utf-8") if version_capture else ""
    version_matches = args.expect_version in version_text
    missing_files = [item for item in copied if not item["copied"]]
    failed_commands = [item for item in captures if not item.ok]
    pass_ok = version_matches and not failed_commands and len(missing_files) == 0

    manifest = {
        "bundle_dir": str(bundle_dir),
        "created_host_ts": time.time(),
        "expect_version": args.expect_version,
        "version_matches": version_matches,
        "pass": pass_ok,
        "copied_files": copied,
        "commands": [asdict(item) for item in captures],
        "missing_file_count": len(missing_files),
        "failed_command_count": len(failed_commands),
    }
    write_private_text(
        bundle_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    lines = [
        "# Native Long Soak Evidence Bundle\n\n",
        f"- result: {'PASS' if pass_ok else 'FAIL'}\n",
        f"- expect_version: `{args.expect_version}`\n",
        f"- version_matches: `{version_matches}`\n",
        f"- missing files: `{len(missing_files)}`\n",
        f"- failed commands: `{len(failed_commands)}`\n\n",
        "## Copied Files\n\n",
    ]
    for item in copied:
        lines.append(f"- {'OK' if item['copied'] else 'MISS'} `{item['source']}`\n")
    lines.append("\n## Command Captures\n\n")
    for item in captures:
        lines.append(
            f"- {'OK' if item.ok else 'FAIL'} `{item.command}` rc={item.rc} "
            f"status={item.status} duration={item.duration_sec:.3f}s file=`{item.file}`\n"
        )
    write_private_text(bundle_dir / "README.md", "".join(lines))

    print(f"{'PASS' if pass_ok else 'FAIL'} bundle={bundle_dir} missing={len(missing_files)} failed_commands={len(failed_commands)}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
