#!/usr/bin/env python3
"""V2802 live handoff for ADSP-up -> ALSA/ASoC publication diagnostics.

This flashes the V2799 audio candidate only to use its native `audio` command
surface, runs a single token-gated ADSP boot, captures full dmesg and platform
sound/ASoC state before and after, then rolls back to V2321. It does not stage
ACDB payloads, issue SET-cal ioctls, route audio, open PCM, or play sound.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_sound_control_diagnostic_live_handoff_v2800 as base

ROOT = repo_root()
CYCLE = "V2802"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2799_audio_native_ioctl_width.img"
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2799-audio-native-ioctl-width/manifest.json"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2802_AUDIO_ASOC_PROBE_SNAPSHOT_LIVE_2026-06-19.md"
CANDIDATE_VERSION = "0.9.312"
CANDIDATE_TAG = "v2799-audio-native-ioctl-width"
ADSP_TOKEN = "AUD2_ONE_SHOT_ADSP_BOOT"
ROLLBACK_SHA256 = base.ROLLBACK_SHA256
FALLBACK_V2237_SHA256 = base.FALLBACK_V2237_SHA256


def rel(path: Path | str | None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stdout_of(step: dict[str, Any] | None) -> str:
    return base.stdout_of(step) if step is not None else ""


def preflight_state() -> dict[str, Any]:
    build = read_json(BUILD_MANIFEST)
    candidate_sha = str(build.get("boot_sha256") or "")
    return {
        "cycle": CYCLE,
        "build_manifest": rel(BUILD_MANIFEST),
        "build_manifest_exists": BUILD_MANIFEST.exists(),
        "build_manifest_decision": build.get("decision"),
        "candidate": base.file_state(CANDIDATE_IMAGE, candidate_sha),
        "candidate_expect_version": CANDIDATE_VERSION,
        "candidate_expect_tag": CANDIDATE_TAG,
        "rollback": base.file_state(base.ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "rollback_expect_version": base.ROLLBACK_VERSION,
        "fallback_v2237": base.file_state(base.FALLBACK_V2237_IMAGE, FALLBACK_V2237_SHA256),
        "fallback_v48": base.file_state(base.FALLBACK_V48_IMAGE),
        "flash_helper": base.file_state(base.FLASH),
        "a90ctl": base.file_state(base.A90CTL),
        "live_scope": [
            "boot partition only via native_init_flash.py",
            "flash V2799 only to access native audio command surface",
            "run exactly one audio adsp-boot-once token command",
            "capture read-only dmesg/sysfs/proc snapshots",
            "no ACDB SET-cal, no route, no PCM, no playback",
            "rollback to v2321 and verify selftest fail=0",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return all([
        state.get("build_manifest_exists"),
        (state.get("candidate") or {}).get("sha256_ok"),
        (state.get("rollback") or {}).get("sha256_ok"),
        (state.get("fallback_v2237") or {}).get("sha256_ok"),
        (state.get("fallback_v48") or {}).get("exists"),
        (state.get("flash_helper") or {}).get("exists"),
        (state.get("a90ctl") or {}).get("exists"),
    ])


def parse_audio_status(text: str) -> dict[str, Any]:
    keys = [
        "audio.rpmsg.count=", "audio.rpmsg_class.count=", "audio.fastrpc_class.count=",
        "audio.sound_class.count=", "audio.dev_snd.count=", "audio.proc_asound_cards=",
    ]
    summary: dict[str, Any] = {
        "has_adsp_rpmsg": "adsp_like=7" in text or "adsp_like=" in text and "adsp_like=0" not in text,
        "has_sound_card": "card_like=1" in text or "sm8150-tavil-snd-card" in text,
        "has_sound_control": "control_like=1" in text,
        "no_soundcards": "--- no soundcards ---" in text,
    }
    for line in text.splitlines():
        for key in keys:
            if key in line:
                summary[key.rstrip("=").replace(".", "_")] = line.strip()
    return summary


def capture_snapshot(out_dir: Path, steps: list[dict[str, Any]], label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    commands = {
        "adsp_status": ["audio", "adsp-status"],
        "snd_status": ["audio", "snd-status"],
        "dmesg_full": ["run", "/bin/busybox", "dmesg"],
        "sound_class": ["run", "/bin/busybox", "sh", "-c", "find /sys/class/sound -maxdepth 2 -type l -o -type f 2>/dev/null | sort"],
        "platform_audio": ["run", "/bin/busybox", "sh", "-c", "find /sys/bus/platform/devices /sys/bus/platform/drivers -maxdepth 2 2>/dev/null | grep -Ei 'sound|audio|asoc|tavil|wcd|wsa|slim|apr|lpass|q6|afe|asm|adm' | sort | head -n 300"],
        "debug_asoc": ["run", "/bin/busybox", "sh", "-c", "if [ -d /sys/kernel/debug/asoc ]; then find /sys/kernel/debug/asoc -maxdepth 3 2>/dev/null | sort | head -n 300; else echo debug_asoc_missing; fi"],
    }
    for key, command in commands.items():
        step = base.run_serial_step(
            out_dir,
            steps,
            f"candidate-{label}-{key}",
            command,
            timeout=150.0,
            retry_unsafe=True,
            allow_error=True,
        )
        result[f"{key}_stdout_path"] = step.get("stdout_path")
        if key == "adsp_status":
            result["audio_status_summary"] = parse_audio_status(stdout_of(step))
    return result


def flash_command(image: Path, version: str, sha: str, *, from_native: bool) -> list[str]:
    return base.flash_command(image, version, sha, from_native=from_native)


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    if not preflight_ok(state):
        raise RuntimeError("preflight failed")
    build = read_json(BUILD_MANIFEST)
    candidate_sha = str(build.get("boot_sha256") or base.sha256_file(CANDIDATE_IMAGE))
    out_dir = ROOT / f"workspace/private/runs/audio/v2802-audio-asoc-probe-snapshot-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    candidate_flash_ok = False
    candidate_flash_attempted = False
    result: dict[str, Any] = {
        "cycle": CYCLE,
        "decision": "v2802-audio-asoc-probe-snapshot-live-started",
        "out_dir": rel(out_dir),
        "candidate_image": rel(CANDIDATE_IMAGE),
        "candidate_sha256": candidate_sha,
        "candidate_tag": CANDIDATE_TAG,
        "rollback_attempted": False,
        "rollback_recovery_fallback_used": False,
        "adsp_boot_command": f"audio adsp-boot-once {ADSP_TOKEN}",
    }
    try:
        base.run_step(
            out_dir,
            steps,
            "preflight-current-v2321-verify",
            flash_command(base.ROLLBACK_IMAGE, base.ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        current_selftest = base.run_serial_step(out_dir, steps, "preflight-current-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        if not base.selftest_step_ok(current_selftest):
            raise RuntimeError("resident preflight selftest did not report fail=0")

        candidate_flash_attempted = True
        base.run_step(out_dir, steps, "flash-v2799-candidate", flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True), timeout=args.flash_timeout)
        candidate_flash_ok = True
        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        result["candidate_version_ok"] = CANDIDATE_VERSION in stdout_of(version)
        if not result["candidate_version_ok"]:
            raise RuntimeError("candidate version output did not contain expected version")
        base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        candidate_selftest = base.run_serial_step(out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True)
        result["candidate_selftest_fail0"] = base.selftest_step_ok(candidate_selftest)
        if not result["candidate_selftest_fail0"]:
            raise RuntimeError("candidate selftest did not report fail=0")

        result["snapshot_before"] = capture_snapshot(out_dir, steps, "before-adsp")
        base.run_serial_step(out_dir, steps, "settle-before-adsp-boot", ["run", "/bin/busybox", "true"], timeout=45.0, retry_unsafe=True, allow_error=True)
        adsp_boot = base.run_serial_step(out_dir, steps, "candidate-audio-adsp-boot-once", ["audio", "adsp-boot-once", ADSP_TOKEN], timeout=120.0, retry_unsafe=False, allow_error=True)
        adsp_text = stdout_of(adsp_boot)
        result["adsp_boot_stdout_path"] = adsp_boot.get("stdout_path")
        result["adsp_boot_rc"] = adsp_boot.get("rc")
        result["adsp_boot_accepted"] = "audio.adsp_boot_once.write=accepted" in adsp_text or "audio.adsp_boot_once.refused=already-up-or-sound-present" in adsp_text

        polls: list[dict[str, Any]] = []
        sound_ready = False
        for index in range(args.poll_count):
            time.sleep(args.poll_interval)
            step = base.run_serial_step(out_dir, steps, f"candidate-audio-adsp-status-poll-{index + 1:02d}", ["audio", "adsp-status"], timeout=120.0, retry_unsafe=True, allow_error=True)
            summary = parse_audio_status(stdout_of(step))
            polls.append({"index": index + 1, "stdout_path": step.get("stdout_path"), "summary": summary})
            if summary.get("has_sound_control") or summary.get("has_sound_card"):
                sound_ready = True
                break
        result["polls"] = polls
        result["sound_ready_after_adsp"] = sound_ready
        result["snapshot_after"] = capture_snapshot(out_dir, steps, "after-adsp")
        result["decision"] = "v2802-audio-asoc-probe-snapshot-card-present-before-rollback" if sound_ready else "v2802-audio-asoc-probe-snapshot-no-card-before-rollback"
    except Exception as exc:
        result.setdefault("decision", "v2802-audio-asoc-probe-snapshot-live-blocked")
        if result["decision"] == "v2802-audio-asoc-probe-snapshot-live-started":
            result["decision"] = "v2802-audio-asoc-probe-snapshot-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        raise
    finally:
        if candidate_flash_attempted:
            result["rollback_attempted"] = True
            try:
                rollback = base.rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
                result.update(rollback)
                rollback_version = base.run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = base.run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = base.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = base.selftest_step_ok(rollback_selftest)
            except Exception as rollback_exc:
                result["rollback_error"] = str(rollback_exc)
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def render_report(result: dict[str, Any]) -> str:
    before = ((result.get("snapshot_before") or {}).get("audio_status_summary") or {})
    after = ((result.get("snapshot_after") or {}).get("audio_status_summary") or {})
    poll_lines = []
    for poll in result.get("polls") or []:
        summary = poll.get("summary") or {}
        poll_lines.append(
            f"- Poll {poll.get('index')}: sound_card=`{int(bool(summary.get('has_sound_card')))}` "
            f"sound_control=`{int(bool(summary.get('has_sound_control')))}` path=`{poll.get('stdout_path')}`"
        )
    if not poll_lines:
        poll_lines = ["- No polls recorded."]
    return "\n".join([
        "# Native Init V2802 Audio ASoC Probe Snapshot Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio ADSP/APR-up to ALSA/ASoC publication frontier.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate tag: `{CANDIDATE_TAG}`",
        f"- Candidate image SHA256: `{result.get('candidate_sha256')}`",
        f"- ADSP boot rc: `{result.get('adsp_boot_rc')}` accepted=`{int(bool(result.get('adsp_boot_accepted')))}`",
        f"- Sound ready after ADSP: `{int(bool(result.get('sound_ready_after_adsp')))}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Status Summary",
        "",
        f"- Before ADSP: rpmsg=`{before.get('audio_rpmsg_count')}` sound=`{before.get('audio_sound_class_count')}` cards=`{before.get('audio_proc_asound_cards')}`",
        f"- After ADSP: rpmsg=`{after.get('audio_rpmsg_count')}` sound=`{after.get('audio_sound_class_count')}` cards=`{after.get('audio_proc_asound_cards')}`",
        *poll_lines,
        "",
        "## Snapshot Paths",
        "",
        f"- Before ADSP full dmesg: `{(result.get('snapshot_before') or {}).get('dmesg_full_stdout_path')}`",
        f"- After ADSP full dmesg: `{(result.get('snapshot_after') or {}).get('dmesg_full_stdout_path')}`",
        f"- Before ADSP platform audio snapshot: `{(result.get('snapshot_before') or {}).get('platform_audio_stdout_path')}`",
        f"- After ADSP platform audio snapshot: `{(result.get('snapshot_after') or {}).get('platform_audio_stdout_path')}`",
        f"- Before ADSP debug ASoC snapshot: `{(result.get('snapshot_before') or {}).get('debug_asoc_stdout_path')}`",
        f"- After ADSP debug ASoC snapshot: `{(result.get('snapshot_after') or {}).get('debug_asoc_stdout_path')}`",
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed; no ACDB SET-cal, route, PCM, mixer, or playback command is issued.",
        "- The single live mutation inside the candidate boot is the already-token-gated ADSP boot write, followed by read-only snapshots.",
        "- Rollback target is `v2321`; public report is metadata-only.",
        "",
    ])


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    build = read_json(BUILD_MANIFEST)
    candidate_sha = str(build.get("boot_sha256") or "")
    return {
        "decision": "v2802-audio-asoc-probe-snapshot-live-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            "adsp_boot": ["audio", "adsp-boot-once", ADSP_TOKEN],
            "rollback": flash_command(base.ROLLBACK_IMAGE, base.ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
        "poll_count": args.poll_count,
        "poll_interval": args.poll_interval,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--flash-timeout", type=float, default=300.0)
    parser.add_argument("--poll-count", type=int, default=8)
    parser.add_argument("--poll-interval", type=float, default=10.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state = preflight_state()
    if args.dry_run or not args.run_live:
        print(json.dumps(dry_run_payload(args, state), indent=2, sort_keys=True))
        return 0 if preflight_ok(state) else 1
    result = live_run(args, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "out_dir": result.get("out_dir"),
        "sound_ready_after_adsp": result.get("sound_ready_after_adsp"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, indent=2, sort_keys=True))
    return 0 if result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
