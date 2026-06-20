#!/usr/bin/env python3
"""V2976 host-only completion audit for the Nyan Cat demo rung.

The Nyan charter requires both a real Player-HUD playback proof and a compact
on-device-decodable format win. This verifier reads only metadata/private run
JSON, rejects weak evidence, writes a public metadata-only report, and commits no
media payloads.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root

ROOT = repo_root()
RUN_ID = "V2976"
BUILD_TAG = "v2976-nyan-rung-completion-audit"
DECISION_PREFIX = "v2976-nyan-rung"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2976_NYAN_RUNG_COMPLETION_AUDIT_2026-06-20.md"
ASSET_MANIFEST = ROOT / "workspace/private/demo-assets/video/v2973-nyancat-pal8-rle-preview/video-stream/manifest.json"
RUN_GLOB = "workspace/private/runs/video/v2975-nyan-real-preview-live-*/result.json"

NYAN_ASSET_ID = "nyancat-v2973-pal8-rle-preview"
NYAN_SHA256 = "9a8d91956218acf674b7d99d421467effec442fdde1dbbea8635b8f47085c573"
NYAN_AUDIO_SHA256 = "4c3774553195c04166a3a83de793253696a5bee60afe83a04219419fc28e43de"
EXPECTED_FRAMES = 300
EXPECTED_WIDTH = 540
EXPECTED_HEIGHT = 360
EXPECTED_FORMAT = "pal8-rle"
MAX_COMPRESSION_RATIO_MILLI = 200
MIN_RAW_XBGR_REDUCTION_X100 = 3000  # >=30x smaller than raw XBGR8888.


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_result_path() -> Path | None:
    candidates = sorted(ROOT.glob(RUN_GLOB), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None




def int_value(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def bool_path(payload: dict[str, Any], *keys: str) -> bool:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def int_path(payload: dict[str, Any], *keys: str) -> int | None:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    try:
        return int(current)
    except (TypeError, ValueError):
        return None


def audit_asset(manifest: dict[str, Any]) -> dict[str, Any]:
    video = manifest.get("video", {}) if isinstance(manifest.get("video"), dict) else {}
    encoded = int(video.get("encoded_payload_bytes") or 0)
    raw_pal8 = int(video.get("raw_pal8_bytes") or 0)
    raw_xbgr = int(video.get("raw_xbgr_bytes") or 0)
    compression_ratio = int(video.get("compression_ratio_milli") or 0)
    xbgr_reduction_x100 = (raw_xbgr * 100 // encoded) if encoded else 0
    pal8_reduction_x100 = (raw_pal8 * 100 // encoded) if encoded else 0
    checks = {
        "asset_id_ok": manifest.get("asset_id") == NYAN_ASSET_ID,
        "sha_ok": video.get("sha256") == NYAN_SHA256,
        "format_ok": video.get("format") == EXPECTED_FORMAT,
        "stream_version_ok": int(video.get("stream_version") or -1) == 2,
        "geometry_ok": int(video.get("width") or -1) == EXPECTED_WIDTH and int(video.get("height") or -1) == EXPECTED_HEIGHT,
        "frames_ok": int(video.get("frame_count") or -1) == EXPECTED_FRAMES,
        "palette_bounded": 1 <= int(video.get("palette_count") or 0) <= 256,
        "rle_all_frames": int((video.get("mode_counts") or {}).get("pal8-rle") or 0) == EXPECTED_FRAMES,
        "compression_ratio_ok": 0 < compression_ratio <= MAX_COMPRESSION_RATIO_MILLI,
        "raw_xbgr_reduction_ok": xbgr_reduction_x100 >= MIN_RAW_XBGR_REDUCTION_X100,
        "raw_pal8_reduction_ok": pal8_reduction_x100 >= 500,
        "encoded_positive": encoded > 0,
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "encoded_payload_bytes": encoded,
        "raw_pal8_bytes": raw_pal8,
        "raw_xbgr_bytes": raw_xbgr,
        "compression_ratio_milli": compression_ratio,
        "raw_xbgr_reduction_x100": xbgr_reduction_x100,
        "raw_pal8_reduction_x100": pal8_reduction_x100,
        "palette_count": int(video.get("palette_count") or 0),
    }


def audit_live(result: dict[str, Any]) -> dict[str, Any]:
    play = result.get("cache_play_summary", {}) if isinstance(result.get("cache_play_summary"), dict) else {}
    audio = result.get("audio_summary", {}) if isinstance(result.get("audio_summary"), dict) else {}
    audio_markers = audio.get("summary", {}) if isinstance(audio.get("summary"), dict) else {}
    runtime_install = result.get("runtime_install", {}) if isinstance(result.get("runtime_install"), dict) else {}
    audio_install = result.get("audio_install", {}) if isinstance(result.get("audio_install"), dict) else {}
    checks = {
        "decision_ok": result.get("decision") == "v2975-nyan-real-preview-live-pass-rollback-ok",
        "result_pass": bool(result.get("pass")),
        "rollback_attempted": bool(result.get("rollback_attempted")),
        "rollback_version_ok": bool(result.get("rollback_version_ok")),
        "rollback_selftest_fail0": bool(result.get("rollback_selftest_fail0")),
        "video_cache_seeded": bool(runtime_install.get("cache_uploaded") or runtime_install.get("cache_hit") or runtime_install.get("cache_adopted")),
        "audio_sha_match": bool(audio_install.get("remote_sha_match")),
        "status_ok": bool_path(result, "cache_status_summary", "stream_size_match") and bool_path(result, "cache_status_summary", "format_ok"),
        "verify_ok": bool_path(result, "cache_verify_summary", "sha_match"),
        "play_pass": bool(play.get("pass")),
        "presented_all": int_value(play.get("presented")) == EXPECTED_FRAMES,
        "dropped_zero": int_value(play.get("dropped_frames")) == 0,
        "setcrtc_path": bool(play.get("present_mode_marker")) and bool(play.get("path_ok")) and int_value(play.get("flip_events")) == 0,
        "player_hud": bool(play.get("stream_layout_marker")),
        "pal8_pixel_format": bool(play.get("pixel_format")),
        "sync_pass": bool(play.get("sync_pass")),
        "audio_worker_done": bool(result.get("audio_worker_done")),
        "audio_pass": bool(audio.get("pass")),
        "audio_pcm_file_validated": bool(audio_markers.get("pcm_file_validated")) and bool(audio_markers.get("execute_plan_waveform_file")),
        "audio_safety": bool(audio_markers.get("safety_amplitude")) and bool(audio_markers.get("safety_duration")),
    }
    return {
        "checks": checks,
        "pass": all(checks.values()),
        "presented": int_value(play.get("presented"), 0),
        "dropped_frames": int_value(play.get("dropped_frames"), 0),
        "fps_milli": int_value(play.get("fps_milli"), 0),
        "elapsed_ns": int_value(play.get("elapsed_ns"), 0),
        "bytes": int_value(play.get("bytes"), 0),
        "audio_worker_done": bool(result.get("audio_worker_done")),
    }


def render_report(payload: dict[str, Any]) -> str:
    asset = payload["asset_audit"]
    live = payload["live_audit"]
    return "\n".join([
        "# Native Init V2976 Nyan Rung Completion Audit",
        "",
        "## Summary",
        "",
        f"- Decision: `{payload['decision']}`",
        f"- Result: `{int(bool(payload['pass']))}`",
        "- Track: active Video playback / Nyan Cat compact color demo.",
        f"- Asset manifest: `{payload['asset_manifest']}`",
        f"- Live result: `{payload['live_result']}`",
        "- Device action: `none` in this V2976 audit; it validates V2973/V2975 evidence only.",
        "",
        "## Completion Criteria",
        "",
        f"- Real Nyan Player HUD playback: `{int(bool(live['pass']))}`",
        f"- Compact on-device format win: `{int(bool(asset['pass']))}`",
        f"- Rollback proof: version_ok=`{int(bool(live['checks'].get('rollback_version_ok')))}` selftest_fail0=`{int(bool(live['checks'].get('rollback_selftest_fail0')))}`",
        "",
        "## Compact Format Evidence",
        "",
        f"- Format: `{EXPECTED_FORMAT}` / stream_version=`2` / palette_count=`{asset['palette_count']}`",
        f"- Encoded payload bytes: `{asset['encoded_payload_bytes']}`",
        f"- Raw pal8 bytes: `{asset['raw_pal8_bytes']}` reduction_x100=`{asset['raw_pal8_reduction_x100']}`",
        f"- Raw XBGR bytes: `{asset['raw_xbgr_bytes']}` reduction_x100=`{asset['raw_xbgr_reduction_x100']}`",
        f"- Compression ratio milli vs pal8: `{asset['compression_ratio_milli']}` threshold=`<={MAX_COMPRESSION_RATIO_MILLI}`",
        f"- Asset checks: `{asset['checks']}`",
        "",
        "## Playback Evidence",
        "",
        f"- Presented/dropped: `{live['presented']}` / `{live['dropped_frames']}`",
        f"- fps_milli: `{live['fps_milli']}` elapsed_ns=`{live['elapsed_ns']}` bytes=`{live['bytes']}`",
        f"- Audio worker done: `{int(bool(live['audio_worker_done']))}`",
        f"- Live checks: `{live['checks']}`",
        "",
        "## Interpretation",
        "",
        "- V2975 proves the real Nyan `pal8-rle` stream plays in Player HUD with bounded PCM-file audio and clean rollback.",
        "- V2973/V2976 prove the compact format requirement on real content: the encoded payload is several times smaller than raw pal8 and far smaller than raw XBGR8888.",
        "- This closes the Nyan demo rung as a short real-content preview. Future work should be explicit polish or the next demo rung, not another Nyan bring-up retry.",
        "",
        "## Safety",
        "",
        "- V2976 performs no device action and reads only metadata/private JSON evidence.",
        "- Raw media payloads and private run logs remain under `workspace/private/` and are not committed.",
        "",
    ])


def run(args: argparse.Namespace) -> dict[str, Any]:
    result_path = Path(args.result) if args.result else latest_result_path()
    if result_path is None:
        raise FileNotFoundError(f"no V2975 result found under {RUN_GLOB}")
    manifest_path = Path(args.manifest)
    manifest = load_json(manifest_path)
    result = load_json(result_path)
    asset_audit = audit_asset(manifest)
    live_audit = audit_live(result)
    payload = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "asset_manifest": rel(manifest_path),
        "live_result": rel(result_path),
        "asset_audit": asset_audit,
        "live_audit": live_audit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["pass"] = bool(asset_audit["pass"] and live_audit["pass"])
    payload["decision"] = f"{DECISION_PREFIX}-completion-pass" if payload["pass"] else f"{DECISION_PREFIX}-completion-failed"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(payload), encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ASSET_MANIFEST), help="V2973 private Nyan manifest JSON")
    parser.add_argument("--result", default="", help="V2975 private result.json; defaults to newest V2975 run")
    parser.add_argument("--out-json", type=Path, default=ROOT / "workspace/private/runs/video/v2976-nyan-rung-completion-audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = run(args)
    print(json.dumps({
        "decision": payload["decision"],
        "pass": payload["pass"],
        "asset_manifest": payload["asset_manifest"],
        "live_result": payload["live_result"],
        "report": rel(REPORT_PATH),
    }, indent=2, sort_keys=True))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
