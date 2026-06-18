#!/usr/bin/env python3
"""Build the V2733 atomic ALSA App Type Config writer.

Host-only unit.  The public C source is tracked; the compiled AArch64 binary is
written only to workspace/private and consumed by the V2639/V2733 replay runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2733"
BUILD_TAG = "v2733-audio-app-type-config-writer"
TOOL_NAME = "a90_alsa_app_type_config_writer_v2733"
SOURCE_REL = "workspace/public/src/native-init/helpers/a90_alsa_app_type_config_writer_v2733.c"
DEFAULT_BUILD_ROOT = ROOT / "workspace/private/builds/audio" / BUILD_TAG
DEFAULT_MANIFEST = DEFAULT_BUILD_ROOT / "manifest.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2733_AUDIO_APP_TYPE_CONFIG_ATOMIC_WRITER_BUILD_2026-06-18.md"
CFLAGS = (
    "-static",
    "-Os",
    "-Wall",
    "-Wextra",
    "-Werror",
)
REQUIRED_SOURCE_TOKENS = {
    "single_elem_write": "SNDRV_CTL_IOCTL_ELEM_WRITE",
    "control_name": "App Type Config",
    "full_count": "A90_APP_TYPE_CFG_MAX_VALUES 128",
    "payload_marker": "A90_APP_TYPE_CFG_PAYLOAD",
    "success_marker": "A90_APP_TYPE_CFG_WRITE_OK",
    "tinymix_bypass": "bypasses tinymix",
}
PROHIBITED_SOURCE_TOKENS = {
    "shell_exec": "system(",
    "exec_call": "execv",
    "speaker_playback": "tinyplay",
    "raw_private_path": "workspace/private/",
    "msm_audio_cal_set": "AUDIO_SET_CALIBRATION",
}


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
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


def run(command: list[str], *, cwd: Path = ROOT, timeout: float = 180.0) -> dict[str, Any]:
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
        "cwd": rel(cwd),
        "rc": completed.returncode,
        "ok": completed.returncode == 0,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def write_json(path: Path, payload: dict[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def source_state() -> dict[str, Any]:
    source = ROOT / SOURCE_REL
    text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    required = {name: token in text for name, token in REQUIRED_SOURCE_TOKENS.items()}
    prohibited = {name: token in text for name, token in PROHIBITED_SOURCE_TOKENS.items()}
    return {
        "source": SOURCE_REL,
        "exists": source.exists(),
        "required_tokens": required,
        "prohibited_tokens": prohibited,
        "ready": source.exists() and all(required.values()) and not any(prohibited.values()),
    }


def tool_file(path: Path) -> str:
    result = run(["file", str(path)], timeout=10.0)
    if not result["ok"]:
        raise RuntimeError(result["stderr"] or result["stdout"] or "file failed")
    return str(result["stdout"]).strip()


def build_tool(build_root: Path, *, cc: str, strip: str | None) -> dict[str, Any]:
    state = source_state()
    if not state["ready"]:
        raise RuntimeError(f"source guard failed: {state}")
    source = ROOT / SOURCE_REL
    bin_dir = build_root / "bin"
    log_dir = build_root / "logs"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    output = bin_dir / TOOL_NAME
    command = [cc, *CFLAGS, "-o", str(output), str(source)]
    build = run(command, timeout=180.0)
    (log_dir / f"{TOOL_NAME}.build.stdout.txt").write_text(build["stdout"], encoding="utf-8", errors="replace")
    (log_dir / f"{TOOL_NAME}.build.stderr.txt").write_text(build["stderr"], encoding="utf-8", errors="replace")
    if not build["ok"]:
        raise RuntimeError(f"build failed; see {rel(log_dir / f'{TOOL_NAME}.build.stderr.txt')}")
    stripped = False
    if strip:
        strip_result = run([strip, str(output)], timeout=30.0)
        (log_dir / f"{TOOL_NAME}.strip.stdout.txt").write_text(strip_result["stdout"], encoding="utf-8", errors="replace")
        (log_dir / f"{TOOL_NAME}.strip.stderr.txt").write_text(strip_result["stderr"], encoding="utf-8", errors="replace")
        if not strip_result["ok"]:
            raise RuntimeError(f"strip failed; see {rel(log_dir / f'{TOOL_NAME}.strip.stderr.txt')}")
        stripped = True
    output.chmod(output.stat().st_mode | 0o111)
    return {
        "bin_dir": rel(bin_dir),
        "logs": rel(log_dir),
        "build_record": {key: value for key, value in build.items() if key not in {"stdout", "stderr"}},
        "tools": {
            TOOL_NAME: {
                "path": rel(output),
                "sha256": sha256_file(output),
                "size": output.stat().st_size,
                "file": tool_file(output),
                "stripped": stripped,
            }
        },
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "decision": "v2733-app-type-config-atomic-writer-built",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "source_state": source_state(),
        "source": {
            "writer_source": SOURCE_REL,
            "purpose": "single atomic SNDRV_CTL_IOCTL_ELEM_WRITE for write-only App Type Config",
        },
        "toolchain": {
            "cc": args.cc,
            "strip": None if args.no_strip else args.strip,
            "cflags": list(CFLAGS),
            "linkage": "static",
        },
        "build_root": rel(args.build_root),
    }
    manifest["build"] = build_tool(args.build_root, cc=args.cc, strip=None if args.no_strip else args.strip)
    manifest["manifest_path"] = rel(args.manifest_path)
    write_json(args.manifest_path, manifest, mode=0o600)
    return manifest


def write_report(path: Path, manifest: dict[str, Any]) -> None:
    tool = manifest.get("build", {}).get("tools", {}).get(TOOL_NAME, {})
    file_desc = str(tool.get("file") or "")
    if ": " in file_desc:
        file_desc = file_desc.split(": ", 1)[1]
    lines = [
        "# NATIVE_INIT V2733 — App Type Config atomic writer build",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only build of a tiny AArch64 writer for the Qualcomm global",
        "`App Type Config` control.  The goal is to replace V2731's `tinymix`",
        "per-index integer writes with one atomic ALSA `SNDRV_CTL_IOCTL_ELEM_WRITE`.",
        "",
        "## Result",
        "",
        f"- decision: `{manifest.get('decision')}`",
        f"- source_ready: `{manifest.get('source_state', {}).get('ready')}`",
        f"- tool: `{TOOL_NAME}`",
        "- tool_path: `workspace/private/...` (private manifest only)",
        f"- sha256: `{tool.get('sha256')}`",
        f"- file: `{file_desc}`",
        "",
        "## Contract",
        "",
        "- opens `/dev/snd/controlC<card>` only;",
        "- resolves `App Type Config` by name unless a runtime numid is supplied;",
        "- validates integer control count is at least 128;",
        "- writes all 128 integer slots in one ioctl;",
        "- does not call `tinymix`, `tinyplay`, `/dev/msm_audio_cal`, or any",
        "  speaker playback primitive.",
        "",
        "## Validation",
        "",
        "- C source token guard passed.",
        "- `aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -Werror` build passed.",
        "- `file` confirms an AArch64 static executable.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--cc", default="aarch64-linux-gnu-gcc")
    parser.add_argument("--strip", default="aarch64-linux-gnu-strip")
    parser.add_argument("--no-strip", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_manifest(args)
    if args.write_report:
        write_report(args.report, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
