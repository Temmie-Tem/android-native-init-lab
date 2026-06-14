#!/usr/bin/env python3
"""V2378 host-only planner for the first native speaker playback recipe.

This script does not touch the device.  It consumes the V2377 Android
route-delta evidence, verifies that the APK AudioTrack stimulus really ran, and
turns the observed mixer deltas into a future exact-gated native playback plan.

The generated plan is intentionally not a live runner: no tinymix set, no PCM
open/write, and no tinyplay are executed by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_ID = "V2378"
BUILD_TAG = "v2378-audio-native-speaker-route-recipe"
DEFAULT_EVIDENCE_DIR = Path("workspace/private/runs/audio/v2377-android-route-delta-modern-apk-20260615-042113")
REMOTE_DIR = "/cache/a90-audio/v2378-speaker-pilot"
REMOTE_TINYMIX = f"{REMOTE_DIR}/tinymix"
REMOTE_TINYPLAY = f"{REMOTE_DIR}/tinyplay"
REMOTE_PCM = f"{REMOTE_DIR}/pilot_48k_s16le_stereo_0p02_1s.wav"
FUTURE_APPROVAL_PHRASE = (
    "AUD-4-native-speaker-pilot go: one-shot V2377 observed route apply, "
    "low-amplitude tinyplay, reverse reset, rollback to V2321"
)
EXPECTED_MARKERS = {
    "A90_AUDIO_STIMULUS_BEGIN": 1,
    "A90_AUDIO_STIMULUS_END": 1,
    "A90_AUDIO_STIMULUS_FINISH": 1,
    "A90_AUDIO_STIMULUS_ERROR": 0,
    "REVIEW_PERMISSIONS": 0,
}
EXPECTED_APK_SHA256 = "fef87886bd1fb5f3dd07b857bbe3c4c00f9046f797ba9c84d48b89dc1d2d13f3"
EXPECTED_TINYPLAY_SHA256 = "03fd8faa9363f97f58a0b094c1504ae4c6f7d8d37f7befd908eaecc6afe81db0"
EXPECTED_TINYMIX_SHA256 = "747b19a5a263a3f2f02223ba2bad2aa0e34f9e8a3948093d612d57e3ada15411"


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "GOAL.md").exists() and (parent / "workspace").exists():
            return parent
    raise RuntimeError("could not locate repository root")


ROOT = repo_root()
TINYMIX = ROOT / "workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/tinymix"
TINYPLAY = ROOT / "workspace/private/builds/audio/v2345-audio-tinyalsa-tools/bin/tinyplay"


@dataclass(frozen=True)
class ControlSpec:
    idx: int
    name: str
    role: str
    apply_order: int | None = None
    reset: bool = True
    notes: str = ""


CONTROL_SPECS: tuple[ControlSpec, ...] = (
    ControlSpec(3345, "Audio Stream 0 App Type Cfg", "stream_cfg", 10, False, "HAL leaves this configured after playback; set before PCM open if future live proceeds."),
    ControlSpec(3344, "Playback Channel Map0", "stream_cfg", 20, True, "Stereo map observed as 1 2 followed by zeros."),
    ControlSpec(453, "SLIMBUS_0_RX Audio Mixer MultiMedia1", "route", 30, True, "Connect MultiMedia1 to SLIMBUS_0_RX."),
    ControlSpec(346, "SLIM RX0 MUX", "route", 40, True, "Select AIF1_PB."),
    ControlSpec(188, "RX INT7_1 MIX1 INP0", "route", 50, True, "Route RX0 into RX INT7."),
    ControlSpec(139, "COMP7 Switch", "route", 60, True, "Enable COMP7 after upstream route is selected."),
    ControlSpec(344, "AIF4_VI Mixer SPKR_VI_1", "speaker_feedback", 70, True, "Observed speaker VI feedback path."),
    ControlSpec(345, "AIF4_VI Mixer SPKR_VI_2", "speaker_feedback", 80, True, "Observed speaker VI feedback path."),
    ControlSpec(3280, "SLIM_4_TX Format", "speaker_feedback", 90, True, "Observed PACKED_16B feedback format."),
    ControlSpec(3277, "SpkrLeft VISENSE Switch", "speaker_endpoint", 100, True, "Observed smart-amp sense path; not a blind gain poke."),
    ControlSpec(3275, "SpkrLeft COMP Switch", "speaker_endpoint", 110, True, "Speaker-facing switch applied near the end."),
    ControlSpec(3276, "SpkrLeft BOOST Switch", "speaker_endpoint", 120, True, "Observed active in Android route; keep low amplitude."),
    ControlSpec(3627, "SpkrLeft SWR DAC_Port Switch", "speaker_endpoint", 130, True, "Final SoundWire DAC port switch."),
    ControlSpec(3348, "ADSP Path Latency 0", "observe_only", None, False, "Readback/latency signal, not a route write."),
)


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


def strip_dsrange(value: str) -> str:
    return value.split("(dsrange", 1)[0].strip()


def selected_enum(value: str) -> str:
    for part in strip_dsrange(value).split():
        if part.startswith(">"):
            return part[1:]
    raise ValueError(f"enum value has no selected token: {value!r}")


BOOL_VALUE_MAP = {
    "Off": "0",
    "On": "1",
    "off": "0",
    "on": "1",
    "0": "0",
    "1": "1",
}


def command_values(control_type: str, value: str) -> list[str]:
    stripped = strip_dsrange(value)
    if control_type == "ENUM":
        return [selected_enum(stripped)]
    if control_type == "BOOL":
        values: list[str] = []
        for part in stripped.split():
            if part not in BOOL_VALUE_MAP:
                raise ValueError(f"unsupported BOOL token: {part!r}")
            values.append(BOOL_VALUE_MAP[part])
        return values
    return [part[1:] if part.startswith(">") else part for part in stripped.split()]


def parse_tinymix(path: Path) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for line in path.read_text(errors="replace").splitlines():
        match = re.match(r"\s*(\d+)\s+(\S+)\s+(\d+)\s+(.+?)\s{2,}(.+?)\s*$", line)
        if not match:
            continue
        idx, control_type, count, name, value = match.groups()
        rows[int(idx)] = {
            "idx": int(idx),
            "type": control_type,
            "count": int(count),
            "name": name.strip(),
            "value": value.strip(),
            "line": line.rstrip(),
        }
    return rows


def evidence_paths(evidence_dir: Path) -> dict[str, Path]:
    return {
        "baseline": evidence_dir / "baseline-tinymix-all-values.stdout.txt",
        "active": evidence_dir / "active-tinymix-all-values.stdout.txt",
        "post": evidence_dir / "post-tinymix-all-values.stdout.txt",
        "logcat": evidence_dir / "stimulus-logcat.stdout.txt",
        "result": evidence_dir / "result.json",
        "playback": evidence_dir / "playback-start-background.stdout.txt",
        "active_dumpsys_audio": evidence_dir / "active-dumpsys-audio.stdout.txt",
    }


def verify_evidence(evidence_dir: Path) -> dict[str, Any]:
    paths = evidence_paths(evidence_dir)
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        return {"ok": False, "evidence_dir": str(evidence_dir), "missing": missing}

    result = json.loads(paths["result"].read_text(encoding="utf-8"))
    logcat = paths["logcat"].read_text(errors="replace")
    active_audio = paths["active_dumpsys_audio"].read_text(errors="replace")
    marker_counts = {marker: logcat.count(marker) for marker in EXPECTED_MARKERS}
    marker_ok = all(
        marker_counts[marker] == expected
        for marker, expected in EXPECTED_MARKERS.items()
    )
    playback_text = paths["playback"].read_text(errors="replace")
    playback_ok = (
        "Status: ok" in playback_text
        and "com.a90.nativeinit.audio/.A90AudioRouteStimulusActivity" in playback_text
    )
    audio_ok = (
        "AudioTrack: stop(22): called with 96000 frames delivered" in logcat
        and "player piid:103 state:device DeviceId:3" in active_audio
        and "type:speaker" in logcat
    )
    return {
        "ok": bool(result.get("ok") and result.get("rolled_back") and marker_ok and playback_ok and audio_ok),
        "evidence_dir": str(evidence_dir),
        "result_ok": bool(result.get("ok")),
        "rolled_back": bool(result.get("rolled_back")),
        "apk_sha256": result.get("plan", {}).get("stimulus_apk", {}).get("sha256", ""),
        "apk_sha256_ok": result.get("plan", {}).get("stimulus_apk", {}).get("sha256", "") == EXPECTED_APK_SHA256,
        "marker_counts": marker_counts,
        "marker_ok": marker_ok,
        "playback_activity_ok": playback_ok,
        "audio_framework_ok": audio_ok,
    }


def route_delta(evidence_dir: Path) -> dict[str, Any]:
    paths = evidence_paths(evidence_dir)
    phases = {phase: parse_tinymix(paths[phase]) for phase in ("baseline", "active", "post")}
    controls: list[dict[str, Any]] = []
    findings: list[str] = []
    for spec in CONTROL_SPECS:
        rows = {phase: phases[phase].get(spec.idx) for phase in phases}
        if any(row is None for row in rows.values()):
            findings.append(f"missing control {spec.idx} {spec.name}")
            continue
        active = rows["active"]
        assert active is not None
        if active["name"] != spec.name:
            findings.append(f"name mismatch at {spec.idx}: expected {spec.name}, got {active['name']}")
        baseline = rows["baseline"]
        post = rows["post"]
        assert baseline is not None and post is not None
        controls.append({
            "idx": spec.idx,
            "name": spec.name,
            "role": spec.role,
            "type": active["type"],
            "count": active["count"],
            "baseline": baseline["value"],
            "active": active["value"],
            "post": post["value"],
            "changed_during_active": active["value"] != baseline["value"],
            "reset_after_playback": post["value"] == baseline["value"],
            "command_values_active": command_values(active["type"], active["value"]),
            "command_values_baseline": command_values(baseline["type"], baseline["value"]),
            "apply_order": spec.apply_order,
            "reset": spec.reset,
            "notes": spec.notes,
        })
    ok = not findings and all(
        item["changed_during_active"] or item["role"] in {"stream_cfg", "observe_only"}
        for item in controls
    )
    return {"ok": ok, "findings": findings, "controls": controls}


def tinymix_set_command(control: dict[str, Any], values: list[str]) -> list[str]:
    return [REMOTE_TINYMIX, "-D", "0", control["name"], *values]


def build_future_plan(delta: dict[str, Any], duration_ms: int, amplitude: float) -> dict[str, Any]:
    writable = [
        item for item in delta["controls"]
        if item["role"] != "observe_only" and item["apply_order"] is not None
    ]
    apply_order = sorted(writable, key=lambda item: item["apply_order"])
    reset_order = [item for item in reversed(apply_order) if item["reset"]]
    apply_commands = [
        {
            "name": f"apply-{item['idx']}-{item['name']}",
            "kind": "tinymix-set-future",
            "argv": tinymix_set_command(item, item["command_values_active"]),
            "role": item["role"],
            "not_executed_by_v2378": True,
        }
        for item in apply_order
    ]
    reset_commands = [
        {
            "name": f"reset-{item['idx']}-{item['name']}",
            "kind": "tinymix-reset-future",
            "argv": tinymix_set_command(item, item["command_values_baseline"]),
            "role": item["role"],
            "not_executed_by_v2378": True,
        }
        for item in reset_order
    ]
    return {
        "approval_phrase_required_for_future_live": FUTURE_APPROVAL_PHRASE,
        "future_live_only": True,
        "route_apply_commands": apply_commands,
        "playback": {
            "name": "tinyplay-low-amplitude-speaker-pilot",
            "kind": "tinyplay-future",
            "argv": [REMOTE_TINYPLAY, REMOTE_PCM, "-D", "0", "-d", "0"],
            "card": 0,
            "device": 0,
            "duration_ms": duration_ms,
            "sample_rate": 48000,
            "channels": 2,
            "format": "S16_LE",
            "amplitude": amplitude,
            "not_executed_by_v2378": True,
        },
        "route_reset_commands": reset_commands,
        "abort_conditions": [
            "rollback image or final fallback missing",
            "candidate boot health/selftest fails before audio step",
            "ADSP/card/dev_snd materialization does not reproduce V2348/V2367 state",
            "tinymix inventory cannot find every V2377 route control by exact name",
            "any route apply command returns non-zero",
            "tinyplay hangs or exceeds bounded timeout",
            "post-reset tinymix differs from pre-apply for route switches",
            "selftest regresses after reset",
        ],
    }


def verify_tool(path: Path, expected_sha256: str) -> dict[str, Any]:
    exists = path.exists()
    actual = sha256_file(path) if exists else ""
    return {
        "path": rel(path),
        "exists": exists,
        "sha256": actual,
        "expected_sha256": expected_sha256,
        "sha256_ok": exists and actual == expected_sha256,
    }


def command_safety(plan: dict[str, Any], amplitude: float, duration_ms: int) -> dict[str, Any]:
    findings: list[str] = []
    if amplitude <= 0 or amplitude > 0.05:
        findings.append(f"amplitude out of bound: {amplitude}")
    if duration_ms <= 0 or duration_ms > 1000:
        findings.append(f"duration out of bound: {duration_ms}")
    flat = json.dumps(plan, sort_keys=True)
    prohibited = ["fastboot", " dd ", "/efs", "/sec_efs", "/dev/block", "mixer_paths", "settings put"]
    for token in prohibited:
        if token in flat:
            findings.append(f"prohibited token in future plan: {token}")
    return {
        "ok": not findings,
        "findings": findings,
        "host_only": True,
        "device_action": "none",
        "future_live_boundaries": [
            "V2378 emits a plan only; it never executes tinymix or tinyplay",
            "future live must use boot-only checked-helper flow and rollback to V2321",
            "future route writes are restricted to V2377-observed controls only",
            "speaker endpoint switches are observed Android route controls, not blind gain/boost pokes",
            "pilot PCM must be generated under workspace/private and never committed",
        ],
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    evidence_dir = (ROOT / args.evidence_dir).resolve() if not args.evidence_dir.is_absolute() else args.evidence_dir
    evidence = verify_evidence(evidence_dir)
    delta = route_delta(evidence_dir) if evidence["ok"] else {"ok": False, "findings": ["evidence failed"], "controls": []}
    plan = build_future_plan(delta, args.duration_ms, args.amplitude) if delta["ok"] else {}
    safety = command_safety(plan, args.amplitude, args.duration_ms) if plan else {"ok": False, "findings": ["no future plan"]}
    tools = {
        "tinymix": verify_tool(TINYMIX, EXPECTED_TINYMIX_SHA256),
        "tinyplay": verify_tool(TINYPLAY, EXPECTED_TINYPLAY_SHA256),
    }
    ok = bool(evidence["ok"] and delta["ok"] and safety["ok"] and all(tool["sha256_ok"] for tool in tools.values()))
    return {
        "decision": "v2378-native-speaker-route-recipe-ready" if ok else "v2378-native-speaker-route-recipe-blocked",
        "ok": ok,
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "evidence": evidence,
        "tools": tools,
        "route_delta": delta,
        "future_plan": plan,
        "command_safety": safety,
        "next_unit": "write an exact-gated native speaker pilot runner only after reviewing this recipe",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="verify V2377 evidence and print future native playback plan")
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--duration-ms", type=int, default=1000)
    parser.add_argument("--amplitude", type=float, default=0.02)
    args = parser.parse_args()
    if not args.dry_run:
        parser.error("V2378 is host-only; pass --dry-run")
    print(json.dumps(dry_run_payload(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
