#!/usr/bin/env python3
"""V2780 live validation for the native-init audio stage module split.

This validates the V2779 behavior change: stage contract data moved into a90_audio_stage.{h,c} while the read-only audio command contract still works on device, then rolls back to V2321.
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
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2779-audio-stage-module/manifest.json"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2779_audio_stage_module.img"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
FALLBACK_V2237_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V48_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2780_AUDIO_STAGE_MODULE_DEVICE_VALIDATION_2026-06-19.md"

CANDIDATE_VERSION = "0.9.298"
CANDIDATE_TAG = "v2779-audio-stage-module"
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
            "run read-only audio status/profile/stage/prereq commands",
            "run audio play dry-run only",
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
        "has_audio_output": "audio." in text,
        "has_prereq_version": "audio.prereq.version=1" in text,
        "has_prereq_profile": f"audio.prereq.profile={PROFILE}" in text,
        "has_prereq_read_only": "audio.prereq.read_only=1" in text,
        "has_prereq_write_attempted0": "audio.prereq.write_attempted=0" in text,
        "has_prereq_playback_attempted0": "audio.prereq.playback_attempted=0" in text,
        "has_prereq_stage_order": "audio.prereq.stage_order=boot,adsp,snd,app_type,setcal,route,pcm,cleanup,rollback" in text,
        "has_prereq_adsp_command": "audio.prereq.adsp.command=audio adsp-boot-once" in text,
        "has_prereq_snd_command": "audio.prereq.snd.snd_materialize_command=audio snd-materialize-once" in text,
        "has_prereq_app_type_command": "audio.prereq.app_type.command=audio app-type" in text,
        "has_prereq_setcal_command": "audio.prereq.setcal.command=audio setcal" in text,
        "has_prereq_route_command": "audio.prereq.route.command=audio route" in text,
        "has_prereq_play_command": "audio.prereq.play.command=audio play" in text,
        "has_prereq_snd_ready": "audio.prereq.snd.pcm_node.ready=" in text,
        "has_prereq_runtime_unverified": "audio.prereq.ready.runtime_state_verified=0" in text,
        "has_prereq_ready_play0": "audio.prereq.ready.play=0" in text,
        "has_prereq_error": "audio.prereq.error=" in text,
        "has_bounded_pcm_stage_native": bool(BOUNDED_PCM_STAGE_NATIVE_RE.search(text)),
        "has_play_dry_run_ok": "audio.play.dry_run_ok=1" in text,
        "has_selftest_fail0": selftest_ok(text),
    }

def render_report(result: dict[str, Any]) -> str:
    summaries = result.get("command_summaries", [])
    summary_lines = [
        "- `{name}`: ok={ok} rc={rc} audio={audio} prereq_version={prereq_version} "
        "read_only={read_only} stage_order={stage_order} commands={commands} "
        "snd_ready={snd_ready} dry_run_ok={dry_run_ok} prereq_error={prereq_error}".format(
            name=item["name"],
            ok=item["ok"],
            rc=item["rc"],
            audio=item["has_audio_output"],
            prereq_version=item["has_prereq_version"],
            read_only=item["has_prereq_read_only"],
            stage_order=item["has_prereq_stage_order"],
            commands=int(bool(
                item["has_prereq_adsp_command"]
                and item["has_prereq_snd_command"]
                and item["has_prereq_app_type_command"]
                and item["has_prereq_setcal_command"]
                and item["has_prereq_route_command"]
                and item["has_prereq_play_command"]
            )),
            snd_ready=item["has_prereq_snd_ready"],
            dry_run_ok=item["has_play_dry_run_ok"],
            prereq_error=item["has_prereq_error"],
        )
        for item in summaries
    ]
    if not summary_lines:
        summary_lines = ["- No command summaries were captured."]
    return "\n".join([
        "# Native Init V2780 Audio Stage Module Device Validation",
        "",
        "## Summary",
        "",
        "- Cycle: `V2780`",
        "- Track: audio stage module device validation.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate image SHA256: `{result.get('candidate_sha256')}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        "",
        "## Finding",
        "",
        "- V2779 splits the explicit stage contract into `a90_audio_stage.{h,c}` while preserving the read-only native-init API surface.",
        "- This run flashes the V2779 test image, checks the stage-module-backed read-only audio commands on device, confirms prereq does not claim runtime state is verified, then rolls back to V2321.",
        "- Expected pass: `audio.prereq.read_only=1`, `write_attempted=0`, `playback_attempted=0`, all stage commands present, no `audio.prereq.error`, and final rollback `selftest fail=0`.",
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
        "- No audio route apply, ACDB SET, PCM open, mixer write, or playback execute is performed by this validation.",
        "- Public report contains metadata only; full command transcripts stay under `workspace/private/runs/audio/`.",
        "",
    ])

def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    if not preflight_ok(state):
        raise SystemExit("refusing live run: preflight failed")

    candidate_sha = str(state["candidate"]["sha256"])
    out_dir = ROOT / f"workspace/private/runs/audio/v2780-audio-stage-module-device-validation-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": "v2780-audio-stage-module-device-validation-started",
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
            "flash-v2779-candidate",
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
            ("audio-prereq", ["audio", "prereq", PROFILE], False),
            ("audio-play-dry-run", ["audio", "play", PROFILE, "--mode", "probe", "--dry-run"], False),
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
        prereq_summary = next((item for item in command_summaries if item.get("name") == "audio-prereq"), {})
        result["prereq_version_observed"] = bool(prereq_summary.get("has_prereq_version"))
        result["prereq_read_only_observed"] = bool(prereq_summary.get("has_prereq_read_only"))
        result["prereq_write_suppressed_observed"] = bool(prereq_summary.get("has_prereq_write_attempted0"))
        result["prereq_playback_suppressed_observed"] = bool(prereq_summary.get("has_prereq_playback_attempted0"))
        result["prereq_stage_order_observed"] = bool(prereq_summary.get("has_prereq_stage_order"))
        result["prereq_commands_observed"] = bool(
            prereq_summary.get("has_prereq_adsp_command")
            and prereq_summary.get("has_prereq_snd_command")
            and prereq_summary.get("has_prereq_app_type_command")
            and prereq_summary.get("has_prereq_setcal_command")
            and prereq_summary.get("has_prereq_route_command")
            and prereq_summary.get("has_prereq_play_command")
        )
        result["prereq_runtime_unverified_observed"] = bool(prereq_summary.get("has_prereq_runtime_unverified"))
        result["prereq_error_observed"] = bool(prereq_summary.get("has_prereq_error"))
        result["play_dry_run_ok_observed"] = any(item.get("has_play_dry_run_ok") for item in command_summaries)
        result["bounded_pcm_stage_native_observed"] = any(item.get("has_bounded_pcm_stage_native") for item in command_summaries)
        if (
            result["prereq_version_observed"]
            and result["prereq_read_only_observed"]
            and result["prereq_write_suppressed_observed"]
            and result["prereq_playback_suppressed_observed"]
            and result["prereq_stage_order_observed"]
            and result["prereq_commands_observed"]
            and result["prereq_runtime_unverified_observed"]
            and result["play_dry_run_ok_observed"]
            and result["bounded_pcm_stage_native_observed"]
            and not result["prereq_error_observed"]
        ):
            result["decision"] = "v2780-audio-stage-module-device-pass"
        elif result["prereq_error_observed"]:
            result["decision"] = "v2780-audio-stage-module-profile-error"
        elif not result["prereq_version_observed"]:
            result["decision"] = "v2780-audio-stage-module-missing-command"
        else:
            result["decision"] = "v2780-audio-stage-module-device-validation-incomplete"
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
        "decision": "v2780-audio-stage-module-device-validation-dry-run",
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
                ["audio", "prereq", PROFILE],
                ["audio", "play", PROFILE, "--mode", "probe", "--dry-run"],
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
