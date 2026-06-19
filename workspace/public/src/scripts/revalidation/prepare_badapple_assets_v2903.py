#!/usr/bin/env python3
"""Prepare private Bad Apple-style A/V assets for native-init playback.

This script is a host-side orchestration wrapper around ffmpeg and the V2902
frame encoder. It expects the source media to be provided privately by the
operator and writes all generated frames, PCM, and A90VSTR streams under
workspace/private by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import prepare_video_stream_from_frames_v2902 as frame_encoder

ROOT = repo_root()
RUN_ID = "V2903"
DEFAULT_OUT_ROOT = ROOT / "workspace/private/demo-assets/video/v2903-badapple-assets"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2903_BADAPPLE_ASSET_PREP_WRAPPER_2026-06-20.md"


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def ffmpeg_fps(fps_num: int, fps_den: int) -> str:
    return str(fps_num) if fps_den == 1 else f"{fps_num}/{fps_den}"


def video_filter(width: int, height: int, fps_num: int, fps_den: int) -> str:
    fps_expr = ffmpeg_fps(fps_num, fps_den)
    return (
        f"fps={fps_expr},"
        f"scale=w={width}:h={height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
        "format=gray"
    )


def frame_ffmpeg_command(ffmpeg: str,
                         input_video: Path,
                         frame_pattern: Path,
                         *,
                         width: int,
                         height: int,
                         fps_num: int,
                         fps_den: int,
                         max_frames: int | None) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_video),
        "-an",
        "-vf",
        video_filter(width, height, fps_num, fps_den),
    ]
    if max_frames is not None:
        command.extend(["-frames:v", str(max_frames)])
    command.extend(["-f", "image2", str(frame_pattern)])
    return command


def audio_ffmpeg_command(ffmpeg: str,
                         input_video: Path,
                         audio_path: Path,
                         *,
                         sample_rate: int,
                         channels: int,
                         volume: float) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_video),
        "-vn",
        "-af",
        f"volume={volume}",
        "-ac",
        str(channels),
        "-ar",
        str(sample_rate),
        "-f",
        "s16le",
        str(audio_path),
    ]


def run_command(command: list[str], *, cwd: Path, timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "rc": completed.returncode,
        "ok": completed.returncode == 0,
        "stdout": completed.stdout or "",
    }


def frame_count(frame_dir: Path) -> int:
    return len([path for path in frame_dir.glob("frame-*.pgm") if path.is_file()])


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_report(payload: dict[str, Any]) -> str:
    validation = payload.get("validation", {})
    output = payload.get("output", {})
    commands = payload.get("commands", {})
    return "\n".join([
        "# Native Init V2903 Bad Apple Asset Prep Wrapper",
        "",
        "## Summary",
        "",
        f"- Cycle: `{RUN_ID}`",
        "- Track: active Video playback pipeline on the existing KMS display.",
        f"- Decision: `{payload.get('decision')}`",
        f"- Result: `{'PASS' if payload.get('ok') else 'BLOCKED'}`",
        "- Scope: host-only asset preparation wrapper; no device flash or runtime state.",
        "- Media policy: source media, rendered frames, PCM, and A90VSTR output remain private and are not committed.",
        "",
        "## Wrapper",
        "",
        "- Script: `workspace/public/src/scripts/revalidation/prepare_badapple_assets_v2903.py`",
        "- Video path: ffmpeg renders private source media to full-screen grayscale PGM frames; V2902 encodes them to `A90VSTR1` `mono1`.",
        "- Audio path: ffmpeg renders private source audio to bounded-volume 48 kHz stereo signed 16-bit little-endian PCM.",
        f"- ffmpeg available on this host: `{int(bool(payload.get('ffmpeg_available')))}`",
        "",
        "## Commands",
        "",
        f"- Frame command planned: `{int(bool(commands.get('frames')))}`",
        f"- Audio command planned: `{int(bool(commands.get('audio')))}`",
        "",
        "## Validation",
        "",
        f"- `py_compile`: `{int(bool(validation.get('py_compile')))}`",
        f"- focused tests: `{int(bool(validation.get('unit_tests')))}`",
        f"- dry-run: `{int(bool(validation.get('dry_run')))}`",
        f"- live CLI smoke: `{int(bool(validation.get('live_smoke')))}`",
        "",
        "## Output",
        "",
        f"- Output root: `{output.get('out_dir')}`",
        f"- Frame count: `{output.get('frame_count')}`",
        f"- Video stream SHA256: `{output.get('stream_sha256')}`",
        f"- Audio PCM SHA256: `{output.get('audio_sha256')}`",
        "",
        "## Next",
        "",
        "- Install ffmpeg or provide a host with ffmpeg if `ffmpeg_available=0`.",
        "- Run this wrapper against a private/user-provided Bad Apple source file.",
        "- Seed the generated stream through the V2900 chunked SD cache path and use V2901 for repeat cache-hit playback.",
        "",
    ]) + "\n"


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir if args.out_dir else DEFAULT_OUT_ROOT / now_slug()
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    frame_dir = out_dir / "frames-pgm"
    stream_dir = out_dir / "video-stream"
    audio_path = out_dir / "audio" / "audio.s16le"
    frame_pattern = frame_dir / "frame-%06d.pgm"
    ffmpeg = ffmpeg_path()
    input_video = args.input_video
    if input_video is not None and not input_video.is_absolute():
        input_video = ROOT / input_video
    payload: dict[str, Any] = {
        "run_id": RUN_ID,
        "decision": "v2903-badapple-assets-dry-run" if args.dry_run else "v2903-badapple-assets-started",
        "ok": False,
        "ffmpeg_available": bool(ffmpeg),
        "input_video_private": rel(input_video) if input_video and input_video.exists() and input_video.is_relative_to(ROOT) else str(input_video) if input_video else "",
        "output": {
            "out_dir": rel(out_dir),
            "frame_dir": rel(frame_dir),
            "stream_dir": rel(stream_dir),
            "audio_path": rel(audio_path),
        },
        "settings": {
            "width": args.width,
            "height": args.height,
            "fps_num": args.fps_num,
            "fps_den": args.fps_den,
            "max_frames": args.max_frames,
            "audio_sample_rate": args.audio_sample_rate,
            "audio_channels": args.audio_channels,
            "audio_volume": args.audio_volume,
            "skip_audio": bool(args.skip_audio),
        },
        "commands": {},
        "validation": {},
    }
    command_ffmpeg = ffmpeg or "ffmpeg"
    if input_video:
        payload["commands"]["frames"] = frame_ffmpeg_command(
            command_ffmpeg,
            input_video,
            frame_pattern,
            width=args.width,
            height=args.height,
            fps_num=args.fps_num,
            fps_den=args.fps_den,
            max_frames=args.max_frames,
        )
        if not args.skip_audio:
            payload["commands"]["audio"] = audio_ffmpeg_command(
                command_ffmpeg,
                input_video,
                audio_path,
                sample_rate=args.audio_sample_rate,
                channels=args.audio_channels,
                volume=args.audio_volume,
            )
    return payload


def run(args: argparse.Namespace) -> dict[str, Any]:
    payload = build_payload(args)
    if args.dry_run:
        payload["ok"] = bool(payload["commands"].get("frames"))
        payload["validation"]["dry_run"] = payload["ok"]
        payload["decision"] = "v2903-badapple-assets-dry-run"
        return payload
    if not payload["ffmpeg_available"]:
        payload["decision"] = "v2903-badapple-assets-blocked-ffmpeg-missing"
        payload["error"] = "ffmpeg is not installed or not on PATH"
        return payload
    if not args.input_video:
        payload["decision"] = "v2903-badapple-assets-blocked-missing-input"
        payload["error"] = "--input-video is required without --dry-run"
        return payload
    input_video = args.input_video if args.input_video.is_absolute() else ROOT / args.input_video
    if not input_video.exists():
        payload["decision"] = "v2903-badapple-assets-blocked-input-missing"
        payload["error"] = f"input video not found: {input_video}"
        return payload
    out_dir = Path(payload["output"]["out_dir"])
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    frame_dir = out_dir / "frames-pgm"
    audio_path = out_dir / "audio" / "audio.s16le"
    frame_dir.mkdir(parents=True, exist_ok=True)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    frame_step = run_command(payload["commands"]["frames"], cwd=ROOT, timeout=args.ffmpeg_timeout)
    payload["frame_step"] = {key: frame_step[key] for key in ("rc", "ok", "stdout")}
    if not frame_step["ok"]:
        payload["decision"] = "v2903-badapple-assets-blocked-frame-render-failed"
        return payload
    count = frame_count(frame_dir)
    if count <= 0:
        payload["decision"] = "v2903-badapple-assets-blocked-no-frames"
        payload["error"] = "ffmpeg completed but produced zero PGM frames"
        return payload
    payload["output"]["frame_count"] = count
    if not args.skip_audio:
        audio_step = run_command(payload["commands"]["audio"], cwd=ROOT, timeout=args.ffmpeg_timeout)
        payload["audio_step"] = {key: audio_step[key] for key in ("rc", "ok", "stdout")}
        if not audio_step["ok"]:
            payload["decision"] = "v2903-badapple-assets-blocked-audio-render-failed"
            return payload
        payload["output"]["audio_sha256"] = sha256_file(audio_path)
        payload["output"]["audio_bytes"] = audio_path.stat().st_size
    stream = frame_encoder.write_stream_from_frames(
        input_dir=frame_dir,
        out_dir=out_dir / "video-stream",
        glob_pattern="frame-*.pgm",
        width=args.width,
        height=args.height,
        stride=(args.width + 7) // 8,
        fps_num=args.fps_num,
        fps_den=args.fps_den,
        input_format="pgm",
        output_format="mono1",
        threshold=args.threshold,
        max_frames=args.max_frames,
        asset_id=args.asset_id,
    )
    payload["stream"] = stream
    payload["output"]["stream_sha256"] = stream["sha256"]
    payload["output"]["stream_bytes"] = stream["stream_bytes"]
    payload["decision"] = "v2903-badapple-assets-ready"
    payload["ok"] = True
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-video", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=2400)
    parser.add_argument("--fps-num", type=int, default=30)
    parser.add_argument("--fps-den", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--audio-sample-rate", type=int, default=48000)
    parser.add_argument("--audio-channels", type=int, default=2)
    parser.add_argument("--audio-volume", type=float, default=0.15)
    parser.add_argument("--skip-audio", action="store_true")
    parser.add_argument("--asset-id", default="badapple-v2903-private-source")
    parser.add_argument("--ffmpeg-timeout", type=float, default=3600.0)
    parser.add_argument("--result-json", type=Path)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = run(args)
    result_path = args.result_json
    if result_path is None:
        output_dir = Path(payload["output"]["out_dir"])
        result_path = (ROOT / output_dir if not output_dir.is_absolute() else output_dir) / "v2903-result.json"
    write_json(result_path, payload)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(render_report(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
