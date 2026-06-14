#!/usr/bin/env python3
"""Build private AArch64 tinyalsa tools for the native-init audio track.

The script is host-only.  It fetches a pinned AOSP tinyalsa archive into
workspace/private, cross-builds static AArch64 tinymix/tinypcminfo/tinyplay
binaries, and writes a private manifest.  It never deploys or runs the tools on
the device.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_ID = "V2345"
BUILD_TAG = "v2345-audio-tinyalsa-tools"
TINYALSA_COMMIT = "e14bf1479ebaaabf60bc4472ce8d304f72f03c32"
TINYALSA_TREE_URL = f"https://android.googlesource.com/platform/external/tinyalsa/+/{TINYALSA_COMMIT}/"
TINYALSA_ARCHIVE_URL = f"https://android.googlesource.com/platform/external/tinyalsa/+archive/{TINYALSA_COMMIT}.tar.gz"
TOOLS = ("tinymix", "tinypcminfo", "tinyplay")
LIB_SOURCES = (
    "mixer.c",
    "mixer_hw.c",
    "mixer_plugin.c",
    "pcm.c",
    "pcm_hw.c",
    "pcm_plugin.c",
    "snd_utils.c",
)
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Wno-unused-parameter",
    "-Iinclude",
)
LDFLAGS = ("-ldl", "-lpthread")


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "GOAL.md").exists() and (parent / "workspace").exists():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
DEFAULT_SOURCE_ROOT = ROOT / "workspace/private/inputs/external_tools/audio/tinyalsa" / TINYALSA_COMMIT
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def safe_extract_tar_gz(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f"refusing link tar member: {member.name}")
            target = (destination / member.name).resolve()
            if root != target and root not in target.parents:
                raise RuntimeError(f"refusing unsafe tar member: {member.name}")
        tar.extractall(destination)


def run(command: list[str], *, cwd: Path, timeout: float = 120.0) -> dict[str, Any]:
    started_monotonic = time.monotonic()
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
        "cwd": rel(cwd),
        "rc": completed.returncode,
        "ok": completed.returncode == 0,
        "elapsed_sec": round(time.monotonic() - started_monotonic, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def tool_file(path: Path) -> str:
    result = run(["file", str(path)], cwd=ROOT, timeout=10.0)
    if not result["ok"]:
        raise RuntimeError(result["stderr"] or result["stdout"] or "file failed")
    return str(result["stdout"]).strip()


def ensure_source(source_root: Path, *, force_download: bool) -> dict[str, Any]:
    archive = source_root / "tinyalsa.tar.gz"
    src_dir = source_root / "src"
    source_root.mkdir(parents=True, exist_ok=True)
    if force_download or not archive.exists():
        download(TINYALSA_ARCHIVE_URL, archive)
    if force_download and src_dir.exists():
        shutil.rmtree(src_dir)
    if not src_dir.exists() or not (src_dir / "Android.bp").exists():
        if src_dir.exists():
            shutil.rmtree(src_dir)
        safe_extract_tar_gz(archive, src_dir)
    required = ["Android.bp", "NOTICE", *LIB_SOURCES, *(f"{tool}.c" for tool in TOOLS)]
    missing = [item for item in required if not (src_dir / item).exists()]
    if missing:
        raise RuntimeError(f"tinyalsa source missing required files: {missing}")
    return {
        "archive": rel(archive),
        "archive_sha256": sha256_file(archive),
        "src_dir": rel(src_dir),
        "required_files_present": True,
    }


def build_tools(source_root: Path, build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
    src_dir = source_root / "src"
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    build_records: list[dict[str, Any]] = []
    tool_records: dict[str, dict[str, Any]] = {}
    for tool in TOOLS:
        output = bin_dir / tool
        command = [cc, *CFLAGS, "-o", str(output), f"{tool}.c", *LIB_SOURCES, *LDFLAGS]
        result = run(command, cwd=src_dir, timeout=180.0)
        (log_dir / f"{tool}.build.stdout.txt").write_text(result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{tool}.build.stderr.txt").write_text(result["stderr"], encoding="utf-8", errors="replace")
        result_for_manifest = {k: v for k, v in result.items() if k not in {"stdout", "stderr"}}
        result_for_manifest["stdout_log"] = rel(log_dir / f"{tool}.build.stdout.txt")
        result_for_manifest["stderr_log"] = rel(log_dir / f"{tool}.build.stderr.txt")
        build_records.append({"tool": tool, **result_for_manifest})
        if not result["ok"]:
            raise RuntimeError(f"build failed for {tool}; see {result_for_manifest['stderr_log']}")
        stripped = False
        strip_result: dict[str, Any] | None = None
        if strip:
            strip_result = run([strip, str(output)], cwd=ROOT, timeout=30.0)
            stripped = bool(strip_result["ok"])
            (log_dir / f"{tool}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
            (log_dir / f"{tool}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
            if not stripped:
                raise RuntimeError(f"strip failed for {tool}")
        mode = output.stat().st_mode
        output.chmod(mode | 0o111)
        tool_records[tool] = {
            "path": rel(output),
            "sha256": sha256_file(output),
            "size": output.stat().st_size,
            "file": tool_file(output),
            "stripped": stripped,
        }
        if strip_result is not None:
            tool_records[tool]["strip_command"] = strip_result["command"]
    return {
        "bin_dir": rel(bin_dir),
        "logs": rel(log_dir),
        "build_records": build_records,
        "tools": tool_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    strip_tool = None if args.no_strip else args.strip
    manifest: dict[str, Any] = {
        "decision": "v2345-audio-tinyalsa-tools-staged",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "source": {
            "project": "AOSP platform/external/tinyalsa",
            "commit": TINYALSA_COMMIT,
            "tree_url": TINYALSA_TREE_URL,
            "archive_url": TINYALSA_ARCHIVE_URL,
            "license_kind": "BSD per Android.bp external_tinyalsa_license",
        },
        "toolchain": {
            "cc": args.cc,
            "strip": strip_tool or "disabled",
            "cflags": list(CFLAGS),
            "ldflags": list(LDFLAGS),
            "linkage": "static",
        },
        "source_root": rel(args.source_root),
        "build_root": rel(args.build_root),
    }
    manifest["source_artifacts"] = ensure_source(args.source_root, force_download=args.force_download)
    manifest["build"] = build_tools(args.source_root, args.build_root, cc=args.cc, strip=strip_tool)
    manifest_path = args.build_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest["manifest_path"] = rel(manifest_path)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
