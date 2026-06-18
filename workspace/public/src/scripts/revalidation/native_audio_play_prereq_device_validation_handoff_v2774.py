#!/usr/bin/env python3
"""V2774 live validation for the native-init audio play prerequisite gate.

This validates the V2773 behavior change: `audio play --execute` must report the PCM devnode prerequisite and refuse before ALSA open when `/dev/snd/pcmC0D0p` is absent, then roll back to V2321.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import a90_transport as transport

ROOT = repo_root()
A90CTL = ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
FLASH = ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2773-audio-play-prereq/manifest.json"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2773_audio_play_prereq.img"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
FALLBACK_V2237_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V48_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2774_AUDIO_PLAY_PREREQ_DEVICE_VALIDATION_2026-06-19.md"

CANDIDATE_VERSION = "0.9.295"
CANDIDATE_TAG = "v2773-audio-play-prereq"
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FALLBACK_V2237_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
PROFILE = "internal-speaker-safe"
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")
BOUNDED_PCM_STAGE_NATIVE_RE = re.compile(
    r"audio\.stages\.(?P<index>\d+)\.id=bounded-pcm-playback"
    r"(?s:.*?)"
    r"audio\.stages\.(?P=index)\.native_implemented=1"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_text(path: Path, limit: int = 1_000_000) -> str:
    try:
        return path.read_bytes()[:limit].decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def file_state(path: Path, expected_sha: str | None = None) -> dict[str, Any]:
    exists = path.exists()
    actual_sha = sha256_file(path) if exists else ""
    return {
        "path": rel(path),
        "exists": exists,
        "sha256": actual_sha,
        "expected_sha256": expected_sha,
        "sha256_ok": expected_sha is None or bool(exists and actual_sha == expected_sha),
    }


def preflight_state() -> dict[str, Any]:
    manifest = read_json(BUILD_MANIFEST)
    candidate_expected_sha = str(manifest.get("boot_sha256") or "")
    return {
        "build_manifest": rel(BUILD_MANIFEST),
        "build_manifest_exists": BUILD_MANIFEST.exists(),
        "build_manifest_decision": manifest.get("decision"),
        "candidate": file_state(CANDIDATE_IMAGE, candidate_expected_sha),
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "fallback_v2237": file_state(FALLBACK_V2237_IMAGE, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48_IMAGE),
        "flash_helper": file_state(FLASH),
        "a90ctl": file_state(A90CTL),
        "candidate_expect_version": CANDIDATE_VERSION,
        "rollback_expect_version": ROLLBACK_VERSION,
        "live_scope": [
            "boot partition only",
            "flash candidate through native_init_flash.py",
            "run read-only audio status/profile/stage commands",
            "run audio play dry-run",
            "run one bounded native PCM execute probe; no retry",
            "rollback to v2321",
        ],
    }


def preflight_ok(state: dict[str, Any]) -> bool:
    return bool(
        state["build_manifest_exists"]
        and state["candidate"].get("sha256_ok")
        and state["rollback"].get("sha256_ok")
        and state["fallback_v2237"].get("sha256_ok")
        and state["fallback_v48"].get("exists")
        and state["flash_helper"].get("exists")
        and state["a90ctl"].get("exists")
    )


def flash_command(image: Path, expect_version: str, expect_sha: str, *, from_native: bool) -> list[str]:
    command = [
        "python3",
        rel(FLASH),
        rel(image),
        "--expect-version",
        expect_version,
        "--expect-sha256",
        expect_sha,
        "--verify-protocol",
        "selftest",
        "--bridge-timeout",
        "300",
        "--recovery-timeout",
        "300",
    ]
    if from_native:
        command.append("--from-native")
    return command


def a90ctl_command(native_command: list[str], *, timeout: float, allow_error: bool = False,
                   retry_unsafe: bool = False) -> list[str]:
    command = [
        "python3",
        rel(A90CTL),
        "--timeout",
        str(timeout),
        "--input-mode",
        "slow",
        "--hide-on-busy",
    ]
    if allow_error:
        command.append("--allow-error")
    if retry_unsafe:
        command.append("--retry-unsafe")
    command.extend(native_command)
    return command


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_step(out_dir: Path, steps: list[dict[str, Any]], name: str, command: list[str], *,
             timeout: float, allow_error: bool = False) -> dict[str, Any]:
    text_path = out_dir / f"{len(steps):02d}_{name}.txt"
    started = time.time()
    record: dict[str, Any] = {
        "name": name,
        "command": command,
        "timeout_sec": timeout,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = completed.stdout or ""
        text_path.write_text(output, encoding="utf-8", errors="replace")
        record.update({
            "rc": completed.returncode,
            "ok": completed.returncode == 0 or allow_error,
            "elapsed_sec": round(time.time() - started, 3),
            "stdout_path": rel(text_path),
            "stdout_tail": output[-4000:],
        })
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        text_path.write_text(output, encoding="utf-8", errors="replace")
        record.update({
            "rc": None,
            "ok": False,
            "timeout": True,
            "elapsed_sec": round(time.time() - started, 3),
            "stdout_path": rel(text_path),
            "stdout_tail": output[-4000:],
        })
    steps.append(record)
    write_json(out_dir / f"{len(steps) - 1:02d}_{name}.json", record)
    if not record["ok"] and not allow_error:
        raise RuntimeError(f"step failed: {name}")
    return record


def run_serial_step(out_dir: Path, steps: list[dict[str, Any]], name: str, native_command: list[str], *,
                    timeout: float, allow_error: bool = False, retry_unsafe: bool = False) -> dict[str, Any]:
    text_path = out_dir / f"{len(steps):02d}_{name}.txt"
    result = transport.run_serial_command_recovered(
        native_command,
        timeout=timeout,
        retry_unsafe=retry_unsafe,
        recovery_step_prefix=name,
    )
    recovery_note: dict[str, Any] | None = None
    protocol = result.get("protocol") if isinstance(result.get("protocol"), dict) else {}
    protocol_status = protocol.get("status") if isinstance(protocol, dict) else None
    if retry_unsafe and (result.get("rc") == -16 or protocol_status == "busy"):
        hide = transport.run_serial_command(["hide"], timeout=20.0, retry_unsafe=True)
        retry = transport.run_serial_command_recovered(
            native_command,
            timeout=timeout,
            retry_unsafe=True,
            recovery_step_prefix=f"{name}-after-protocol-busy",
        )
        recovery_note = {
            "reason": "protocol-status-busy",
            "actions": ["hide", "retry-command"],
            "hide_ok": bool(hide.get("ok")),
            "retry_ok": bool(retry.get("ok")),
        }
        result = retry

    output = "\n".join([str(result.get("stdout") or ""), str(result.get("stderr") or "")])
    text_path.write_text(output, encoding="utf-8", errors="replace")
    record: dict[str, Any] = {
        "name": name,
        "command": [str(part) for part in result.get("command", ["cmdv1", *native_command])],
        "timeout_sec": timeout,
        "started_at": result.get("started"),
        "rc": result.get("rc"),
        "ok": bool(result.get("ok")) or allow_error,
        "elapsed_sec": result.get("elapsed_sec"),
        "stdout_path": rel(text_path),
        "stdout_tail": output[-4000:],
        "transport": "a90_transport.serial",
    }
    if "protocol" in result:
        record["protocol"] = result.get("protocol")
    if "serial_recovery" in result:
        record["serial_recovery_contract"] = result.get("serial_recovery_contract")
        record["serial_recovery"] = result.get("serial_recovery")
    if recovery_note is not None:
        record["protocol_busy_recovery"] = recovery_note
    steps.append(record)
    write_json(out_dir / f"{len(steps) - 1:02d}_{name}.json", record)
    if not record["ok"] and not allow_error:
        raise RuntimeError(f"step failed: {name}")
    return record


def stdout_of(step: dict[str, Any]) -> str:
    return read_text(ROOT / str(step.get("stdout_path") or ""))


def selftest_ok(text: str) -> bool:
    return bool(SELFTEST_FAIL0_RE.search(text))


def summarize_step(step: dict[str, Any]) -> dict[str, Any]:
    text = stdout_of(step)
    return {
        "name": step.get("name"),
        "ok": step.get("ok"),
        "rc": step.get("rc"),
        "has_audio_version": "audio." in text,
        "has_old_execute_refusal": "execute-not-implemented-native-pcm" in text,
        "has_execute_supported": "audio.play.execute_supported=1" in text,
        "has_execute_version": "audio.play.execute.version=1" in text,
        "has_alsa_open_attempt": "audio.play.execute.alsa_open_attempted=1" in text,
        "has_execute_open_suppressed": "audio.play.execute.alsa_open_attempted=0" in text,
        "has_alsa_open_rc": "audio.play.execute.open.rc=" in text,
        "has_hw_params": "audio.play.execute.hw_params.rc=" in text,
        "has_sw_params": "audio.play.execute.sw_params.rc=" in text,
        "has_prepare": "audio.play.execute.prepare.rc=" in text,
        "has_write_attempt": "audio.play.execute.pcm_write_attempted=1" in text,
        "has_done": "audio.play.execute.done=" in text,
        "has_pcm_prereq_missing": "audio.play.prereq.pcm_node.state=missing" in text,
        "has_pcm_prereq_ready0": "audio.play.prereq.pcm_node.ready=0" in text,
        "has_missing_pcm_refusal": "audio.play.refused=missing-pcm-node" in text,
        "has_bounded_pcm_stage_native": bool(BOUNDED_PCM_STAGE_NATIVE_RE.search(text)),
        "has_safety_cap_refusal": "audio.play.refused=safety-cap-exceeded" in text,
        "has_play_dry_run_ok": "audio.play.dry_run_ok=1" in text,
        "has_selftest_fail0": selftest_ok(text),
    }


def render_report(result: dict[str, Any]) -> str:
    summaries = result.get("command_summaries", [])
    summary_lines = [
        "- `{name}`: ok={ok} rc={rc} dry_run_ok={dry} old_refusal={old} "
        "execute_supported={supported} prereq_missing={prereq_missing} "
        "missing_pcm_refusal={missing_refusal} open_attempt={open_attempt} "
        "open_suppressed={open_suppressed} bounded_native={bounded_native} "
        "hw_params={hw} prepare={prepare} write_attempt={write} done={done}".format(
            name=item["name"],
            ok=item["ok"],
            rc=item["rc"],
            dry=item["has_play_dry_run_ok"],
            old=item["has_old_execute_refusal"],
            supported=item["has_execute_supported"],
            prereq_missing=item["has_pcm_prereq_missing"],
            missing_refusal=item["has_missing_pcm_refusal"],
            open_attempt=item["has_alsa_open_attempt"],
            open_suppressed=item["has_execute_open_suppressed"],
            bounded_native=item["has_bounded_pcm_stage_native"],
            hw=item["has_hw_params"],
            prepare=item["has_prepare"],
            write=item["has_write_attempt"],
            done=item["has_done"],
        )
        for item in summaries
    ]
    if not summary_lines:
        summary_lines = ["- No command summaries were captured."]
    return "\n".join([
        "# Native Init V2774 Audio Play Prerequisite Device Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2774`",
        "- Track: audio command play prerequisite device validation.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image SHA256: `{result.get('candidate_sha256')}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2773 adds explicit PCM devnode prerequisite reporting before native ALSA open.",
        "- This run records whether `audio play --execute` reports `/dev/snd/pcmC0D0p` missing and refuses before ALSA open on a baseline where `/dev/snd` is not materialized.",
        "- Expected pass: `bounded-pcm-playback.native_implemented=1`, `audio.play.refused=missing-pcm-node`, and `audio.play.execute.alsa_open_attempted=0`.",
        "- This keeps the play primitive API explicit: playback requires the speaker preparation stages (`/dev/snd`, app-type, SET replay, route) first.",
        "",
        "## Command Summary",
        "",
        *summary_lines,
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is written.",
        "- No forbidden partitions are touched.",
        "- No credentials are used.",
        "- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.",
        "",
    ])


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    if not preflight_ok(state):
        raise SystemExit("refusing live run: preflight failed")

    candidate_sha = str(state["candidate"]["sha256"])
    out_dir = ROOT / f"workspace/private/runs/audio/v2774-audio-play-prereq-device-validation-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": "v2774-audio-play-prereq-device-validation-started",
        "out_dir": rel(out_dir),
        "candidate_sha256": candidate_sha,
        "steps": steps,
        "rollback_attempted": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
    }

    candidate_flash_attempted = False
    candidate_flash_ok = False
    try:
        run_step(
            out_dir,
            steps,
            "preflight-current-v2321-verify",
            flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        current_selftest = run_serial_step(
            out_dir,
            steps,
            "preflight-current-selftest",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        if not selftest_ok(stdout_of(current_selftest)):
            raise RuntimeError("resident preflight selftest did not report fail=0")

        candidate_flash_attempted = True
        run_step(
            out_dir,
            steps,
            "flash-v2773-candidate",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = True

        version = run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        if CANDIDATE_VERSION not in stdout_of(version):
            raise RuntimeError("candidate version output did not contain expected version")
        run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        candidate_selftest = run_serial_step(
            out_dir,
            steps,
            "candidate-selftest",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        if not selftest_ok(stdout_of(candidate_selftest)):
            raise RuntimeError("candidate selftest did not report fail=0")

        audio_steps = [
            ("audio-status", ["audio", "status"], False),
            ("audio-profiles", ["audio", "profiles"], False),
            ("audio-profile", ["audio", "profile", PROFILE], False),
            ("audio-stages", ["audio", "stages", PROFILE], False),
            ("audio-play-dry-run", ["audio", "play", PROFILE, "--mode", "probe", "--dry-run"], False),
            ("audio-play-execute-native-pcm", ["audio", "play", PROFILE, "--mode", "probe", "--execute"], True),
        ]
        command_summaries: list[dict[str, Any]] = []
        for name, native_command, allow_error in audio_steps:
            step = run_serial_step(
                out_dir,
                steps,
                name,
                native_command,
                timeout=150.0,
                allow_error=allow_error,
                retry_unsafe=not allow_error,
            )
            command_summaries.append(summarize_step(step))
        result["command_summaries"] = command_summaries
        result["old_execute_refusal_observed"] = any(item.get("has_old_execute_refusal") for item in command_summaries)
        result["execute_supported_observed"] = any(item.get("has_execute_supported") for item in command_summaries)
        result["alsa_open_attempt_observed"] = any(item.get("has_alsa_open_attempt") for item in command_summaries)
        result["execute_open_suppressed_observed"] = any(item.get("has_execute_open_suppressed") for item in command_summaries)
        result["pcm_prereq_missing_observed"] = any(item.get("has_pcm_prereq_missing") for item in command_summaries)
        result["missing_pcm_refusal_observed"] = any(item.get("has_missing_pcm_refusal") for item in command_summaries)
        result["bounded_pcm_stage_native_observed"] = any(item.get("has_bounded_pcm_stage_native") for item in command_summaries)
        result["pcm_done_observed"] = any(item.get("has_done") for item in command_summaries)
        result["dry_run_ok_observed"] = any(item.get("has_play_dry_run_ok") for item in command_summaries)
        if result["old_execute_refusal_observed"]:
            result["decision"] = "v2774-audio-play-prereq-source-refusal-regression"
        elif (
            result["missing_pcm_refusal_observed"]
            and result["pcm_prereq_missing_observed"]
            and result["execute_open_suppressed_observed"]
            and not result["alsa_open_attempt_observed"]
        ):
            result["decision"] = "v2774-audio-play-prereq-device-pass"
        elif result["pcm_done_observed"]:
            result["decision"] = "v2774-audio-play-prereq-unexpected-pcm-device-pass"
        elif result["alsa_open_attempt_observed"]:
            result["decision"] = "v2774-audio-play-prereq-regression-opened-missing-node"
        elif result["execute_supported_observed"]:
            result["decision"] = "v2774-audio-play-prereq-supported-but-no-refusal"
        else:
            result["decision"] = "v2774-audio-play-prereq-device-validation-unexpected-play-execute-result"
    finally:
        if candidate_flash_attempted:
            result["rollback_attempted"] = True
            rollback_from_native = candidate_flash_ok
            rollback = run_step(
                out_dir,
                steps,
                "rollback-v2321",
                flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=rollback_from_native),
                timeout=args.flash_timeout,
                allow_error=True,
            )
            result["rollback_step_ok"] = bool(rollback.get("ok"))
            if rollback.get("ok"):
                rollback_version = run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = selftest_ok(stdout_of(rollback_selftest))
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def dry_run(state: dict[str, Any]) -> dict[str, Any]:
    candidate_sha = str(state["candidate"].get("sha256") or "")
    return {
        "decision": "v2774-audio-play-prereq-device-validation-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            "audio_checks": [
                ["audio", "status"],
                ["audio", "profiles"],
                ["audio", "profile", PROFILE],
                ["audio", "stages", PROFILE],
                ["audio", "play", PROFILE, "--mode", "probe", "--dry-run"],
                ["audio", "play", PROFILE, "--mode", "probe", "--execute"],
            ],
            "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="perform flash + device validation + rollback")
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = preflight_state()
    if not args.live:
        print(json.dumps(dry_run(state), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if preflight_ok(state) else 1
    result = live_run(args, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "out_dir": result.get("out_dir"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("rollback_version_ok") and result.get("rollback_selftest_fail0") else 1


if __name__ == "__main__":
    raise SystemExit(main())
