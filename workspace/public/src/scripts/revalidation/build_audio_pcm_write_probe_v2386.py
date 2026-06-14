#!/usr/bin/env python3
"""Build the V2386 private AArch64 PCM write diagnostic probe.

This is host-only. It compiles a public diagnostic wrapper against the pinned
V2345 tinyalsa source tree and writes only private build outputs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_audio_tinyalsa_tools_v2345 as tiny

RUN_ID = "V2386"
BUILD_TAG = "v2386-audio-pcm-write-probe"
TOOL_NAME = "a90_pcm_write_probe_v2386"
SOURCE_REL = "workspace/public/src/native-init/helpers/a90_pcm_write_probe_v2386.c"
DEFAULT_BUILD_ROOT = tiny.ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Wno-unused-parameter",
    "-Iinclude",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(command: list[str], *, cwd: Path, timeout: float = 180.0) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return {
        "command": command,
        "cwd": tiny.rel(cwd),
        "rc": completed.returncode,
        "ok": completed.returncode == 0,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def tool_file(path: Path) -> str:
    result = run(["file", str(path)], cwd=tiny.ROOT, timeout=10.0)
    if not result["ok"]:
        raise RuntimeError(result["stderr"] or result["stdout"] or "file failed")
    return str(result["stdout"]).strip()


def build_probe(source_root: Path, build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
    tiny.ensure_source(source_root, force_download=False)
    src_dir = source_root / "src"
    public_source = tiny.ROOT / SOURCE_REL
    if not public_source.exists():
        raise RuntimeError(f"missing probe source: {tiny.rel(public_source)}")
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    output = bin_dir / TOOL_NAME
    command = [cc, *CFLAGS, "-o", str(output), str(public_source), *tiny.LIB_SOURCES, *tiny.LDFLAGS]
    build = run(command, cwd=src_dir, timeout=180.0)
    (log_dir / f"{TOOL_NAME}.build.stdout.txt").write_text(build["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{TOOL_NAME}.build.stderr.txt").write_text(build["stderr"], encoding="utf-8", errors="replace")
    if not build["ok"]:
        raise RuntimeError(f"build failed for {TOOL_NAME}; see {tiny.rel(log_dir / f'{TOOL_NAME}.build.stderr.txt')}")
    stripped = False
    strip_command: list[str] | None = None
    if strip:
        strip_command = [strip, str(output)]
        strip_result = run(strip_command, cwd=tiny.ROOT, timeout=30.0)
        (log_dir / f"{TOOL_NAME}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{TOOL_NAME}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
        if not strip_result["ok"]:
            raise RuntimeError(f"strip failed for {TOOL_NAME}")
        stripped = True
    output.chmod(output.stat().st_mode | 0o111)
    build_record = {key: value for key, value in build.items() if key not in {"stdout", "stderr"}}
    build_record["stdout_log"] = tiny.rel(log_dir / f"{TOOL_NAME}.build.stdout.txt")
    build_record["stderr_log"] = tiny.rel(log_dir / f"{TOOL_NAME}.build.stderr.txt")
    tool_record: dict[str, Any] = {
        "path": tiny.rel(output),
        "sha256": tiny.sha256_file(output),
        "size": output.stat().st_size,
        "file": tool_file(output),
        "stripped": stripped,
    }
    if strip_command is not None:
        tool_record["strip_command"] = strip_command
    return {
        "bin_dir": tiny.rel(bin_dir),
        "logs": tiny.rel(log_dir),
        "build_records": [{"tool": TOOL_NAME, **build_record}],
        "tools": {TOOL_NAME: tool_record},
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "decision": "v2386-audio-pcm-write-probe-staged",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "source": {
            "probe_source": SOURCE_REL,
            "tinyalsa_project": "AOSP platform/external/tinyalsa",
            "tinyalsa_commit": tiny.TINYALSA_COMMIT,
            "tinyalsa_tree_url": tiny.TINYALSA_TREE_URL,
            "license_kind": "probe source plus BSD tinyalsa link dependency",
        },
        "toolchain": {
            "cc": args.cc,
            "strip": None if args.no_strip else args.strip,
            "cflags": list(CFLAGS),
            "ldflags": list(tiny.LDFLAGS),
            "linkage": "static",
        },
        "source_root": tiny.rel(args.source_root),
        "build_root": tiny.rel(args.build_root),
        "diagnostic_contract": {
            "write_error_marker": "A90_PCM_PROBE_WRITE_ERROR",
            "open_error_marker": "A90_PCM_PROBE_PCM_OPEN_ERROR",
            "success_marker": "A90_PCM_PROBE_DONE",
            "reports_pcm_get_error": True,
            "reports_errno": True,
        },
    }
    manifest["build"] = build_probe(args.source_root, args.build_root, cc=args.cc, strip=None if args.no_strip else args.strip)
    manifest_path = args.build_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest["manifest_path"] = tiny.rel(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=tiny.DEFAULT_SOURCE_ROOT)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_manifest(args), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
