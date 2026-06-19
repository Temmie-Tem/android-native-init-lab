#!/usr/bin/env python3
"""V2805 card-first discriminator for native audio play.

This flashes the already-built V2804 candidate, reproduces the V2802-style
direct ADSP boot/card-publication path before staging runtime ACDB artifacts,
then runs the integrated native `audio play --execute` path only if the ASoC
card/control appear first.

No new boot image is built here. The unit discriminates whether V2804 failed
because runtime artifact staging happened before ADSP/ASoC publication, or
because the V2804 image/path cannot publish the sound card at all.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import native_audio_adsp_kick_no_wait_live_handoff_v2804 as base

ROOT = repo_root()
CYCLE = "V2805"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2805_AUDIO_CARD_FIRST_PLAY_LIVE_2026-06-19.md"
ADSP_TOKEN = "AUD2_ONE_SHOT_ADSP_BOOT"


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
    state = base.preflight_state()
    state["cycle"] = CYCLE
    state["report_path"] = rel(REPORT_PATH)
    state["discriminator"] = "direct-adsp-card-first-before-runtime-acdb-deploy"
    state["live_scope"] = [
        "boot partition only via native_init_flash.py",
        "flash V2804 candidate only; no new boot artifact",
        "run direct audio adsp-boot-once before runtime ACDB staging",
        "poll read-only audio status until sound card/control publication",
        "stage ACDB artifacts only after card publication",
        "run native audio play internal-speaker-safe --mode listen --execute once",
        "low-amplitude profile cap is enforced by native-init source",
        "rollback to v2321 and verify selftest fail=0",
    ]
    return state


def preflight_ok(state: dict[str, Any]) -> bool:
    return base.preflight_ok(state)


def parse_audio_status(text: str) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "has_adsp_rpmsg": ("adsp_like=" in text and "adsp_like=0" not in text),
        "has_sound_card": "card_like=1" in text or "sm8150-tavil-snd-card" in text,
        "has_sound_control": "control_like=1" in text,
        "no_soundcards": "--- no soundcards ---" in text,
    }
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("audio.rpmsg.count="):
            summary["rpmsg_line"] = stripped
        elif stripped.startswith("audio.sound_class.count="):
            summary["sound_class_line"] = stripped
        elif stripped.startswith("audio.dev_snd.count="):
            summary["dev_snd_line"] = stripped
        elif stripped.startswith("audio.proc_asound_cards="):
            summary["proc_asound_cards_line"] = stripped
    return summary


def status_ready(summary: dict[str, Any]) -> bool:
    return bool(summary.get("has_sound_card") or summary.get("has_sound_control"))


def capture_audio_status(out_dir: Path, steps: list[dict[str, Any]], label: str) -> dict[str, Any]:
    adsp = base.run_serial_step(
        out_dir,
        steps,
        f"candidate-audio-adsp-status-{label}",
        ["audio", "adsp-status"],
        timeout=120.0,
        retry_unsafe=True,
        allow_error=True,
    )
    snd = base.run_serial_step(
        out_dir,
        steps,
        f"candidate-audio-snd-status-{label}",
        ["audio", "snd-status"],
        timeout=120.0,
        retry_unsafe=True,
        allow_error=True,
    )
    adsp_text = stdout_of(adsp)
    snd_text = stdout_of(snd)
    summary = parse_audio_status("\n".join([adsp_text, snd_text]))
    return {
        "adsp_stdout_path": adsp.get("stdout_path"),
        "snd_stdout_path": snd.get("stdout_path"),
        "summary": summary,
    }


def wait_for_sound_card(out_dir: Path,
                        steps: list[dict[str, Any]],
                        *,
                        count: int,
                        interval: float) -> dict[str, Any]:
    polls: list[dict[str, Any]] = []
    for index in range(count):
        if index:
            time.sleep(interval)
        status = capture_audio_status(out_dir, steps, f"card-poll-{index + 1:02d}")
        poll = {
            "index": index + 1,
            "adsp_stdout_path": status.get("adsp_stdout_path"),
            "snd_stdout_path": status.get("snd_stdout_path"),
            "summary": status.get("summary") or {},
        }
        polls.append(poll)
        if status_ready(poll["summary"]):
            return {"ready": True, "attempts": index + 1, "polls": polls, "last": poll}
    return {"ready": False, "attempts": len(polls), "polls": polls, "last": polls[-1] if polls else None}


def hide_auto_menu(out_dir: Path, steps: list[dict[str, Any]], label: str) -> dict[str, Any]:
    return base.run_serial_step(
        out_dir,
        steps,
        f"candidate-hide-{label}",
        ["hide"],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )


def run_play_sequence(args: argparse.Namespace,
                      out_dir: Path,
                      steps: list[dict[str, Any]],
                      deploy_plan: dict[str, Any],
                      native_manifest_path: Path) -> dict[str, Any]:
    play_command = [
        "audio",
        "play",
        base.PROFILE,
        "--mode",
        args.play_mode,
        "--duration-ms",
        str(args.duration_ms),
        "--amplitude-milli",
        str(args.amplitude_milli),
        "--manifest",
        base.REMOTE_NATIVE_MANIFEST,
        "--execute",
    ]
    result: dict[str, Any] = {
        "play_command": " ".join(play_command),
        "runtime_artifacts": base.install_runtime_artifacts(args, out_dir, steps, deploy_plan, native_manifest_path),
    }
    result["status_after_deploy"] = capture_audio_status(out_dir, steps, "after-deploy-before-play")
    if not status_ready((result["status_after_deploy"] or {}).get("summary") or {}):
        result["deploy_lost_card"] = True
        return result

    prereq = base.run_serial_step(out_dir, steps, "candidate-audio-prereq", ["audio", "prereq", base.PROFILE], timeout=150.0, retry_unsafe=True)
    result["prereq_stdout_path"] = prereq.get("stdout_path")
    hide_auto_menu(out_dir, steps, "before-play")
    play = base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-play-execute-listen",
        play_command,
        timeout=90.0,
        retry_unsafe=False,
        allow_error=True,
    )
    play_text = stdout_of(play)
    result["play_rc"] = play.get("rc")
    result["play_stdout_path"] = play.get("stdout_path")
    if play.get("rc") != 0 or "audio.play.worker.started=1" not in play_text:
        result["play_summary"] = base.classify_play_output(play_text)
        result["play_output_pass"] = False
        result["play_start_failed"] = True
        return result

    worker = base.wait_for_worker_done(out_dir, steps, args.play_timeout)
    result["worker_status_done"] = bool(worker.get("done"))
    result["worker_status_attempts"] = worker.get("attempts")
    result["worker_status_stdout_path"] = worker.get("stdout_path")
    log_step = base.run_serial_step(
        out_dir,
        steps,
        "candidate-audio-card-first-play-log",
        ["run", "/bin/busybox", "cat", base.REMOTE_PLAY_LOG],
        timeout=45.0,
        retry_unsafe=True,
        allow_error=True,
    )
    log_text = stdout_of(log_step)
    result["worker_log_stdout_path"] = log_step.get("stdout_path")
    combined_text = "\n".join([play_text, str(worker.get("text") or ""), log_text])
    result["play_summary"] = base.classify_play_output(combined_text)
    result["play_output_pass"] = base.play_output_pass(result["play_summary"])
    result["status_after_play"] = capture_audio_status(out_dir, steps, "after-play")
    dmesg_tail = base.run_serial_step(
        out_dir,
        steps,
        "candidate-dmesg-audio-tail",
        ["run", "/bin/busybox", "sh", "-c", "dmesg | tail -n 260"],
        timeout=90.0,
        retry_unsafe=True,
        allow_error=True,
    )
    result["dmesg_audio_tail_stdout_path"] = dmesg_tail.get("stdout_path")
    return result


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    if not preflight_ok(state):
        raise SystemExit("refusing live run: preflight failed")
    deploy_plan = read_json(base.DEPLOY_PLAN)
    candidate_sha = str(state["candidate"]["sha256"])
    out_dir = ROOT / f"workspace/private/runs/audio/v2805-audio-card-first-play-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    native_manifest_path = base.materialize_native_manifest(out_dir, deploy_plan)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "cycle": CYCLE,
        "decision": "v2805-audio-card-first-play-live-started",
        "out_dir": rel(out_dir),
        "candidate_sha256": candidate_sha,
        "candidate_tag": base.CANDIDATE_TAG,
        "candidate_version": base.CANDIDATE_VERSION,
        "native_manifest_path": rel(native_manifest_path),
        "native_manifest_sha256": base.sha256_file(native_manifest_path),
        "direct_adsp_command": f"audio adsp-boot-once {ADSP_TOKEN}",
        "steps": steps,
        "rollback_attempted": False,
        "rollback_recovery_fallback_used": False,
        "rollback_version_ok": False,
        "rollback_selftest_fail0": False,
        "operator_audible_confirmation": "pending-human-listen-confirmation",
    }
    candidate_flash_attempted = False
    candidate_flash_ok = False
    try:
        base.run_step(
            out_dir,
            steps,
            "preflight-current-v2321-verify",
            base.flash_command(base.ROLLBACK_IMAGE, base.ROLLBACK_VERSION, base.ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        current_selftest = base.run_serial_step(
            out_dir,
            steps,
            "preflight-current-selftest",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["preflight_current_selftest_fail0"] = base.selftest_step_ok(current_selftest)
        if not result["preflight_current_selftest_fail0"]:
            raise RuntimeError("resident preflight selftest did not report fail=0")

        candidate_flash_attempted = True
        base.run_step(
            out_dir,
            steps,
            "flash-v2804-candidate",
            base.flash_command(base.CANDIDATE_IMAGE, base.CANDIDATE_VERSION, candidate_sha, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = True

        version = base.run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        result["candidate_version_ok"] = base.CANDIDATE_VERSION in stdout_of(version)
        if not result["candidate_version_ok"]:
            raise RuntimeError("candidate version output did not contain expected version")
        base.run_serial_step(out_dir, steps, "candidate-status", ["status"], timeout=90.0, retry_unsafe=True)
        candidate_selftest = base.run_serial_step(
            out_dir,
            steps,
            "candidate-selftest",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["candidate_selftest_fail0"] = base.selftest_step_ok(candidate_selftest)
        if not result["candidate_selftest_fail0"]:
            raise RuntimeError("candidate selftest did not report fail=0")

        result["status_before_direct_adsp"] = capture_audio_status(out_dir, steps, "before-direct-adsp")
        hide_auto_menu(out_dir, steps, "before-direct-adsp")
        direct = base.run_serial_step(
            out_dir,
            steps,
            "candidate-audio-direct-adsp-boot-once",
            ["audio", "adsp-boot-once", ADSP_TOKEN],
            timeout=120.0,
            retry_unsafe=False,
            allow_error=True,
        )
        direct_text = stdout_of(direct)
        result["direct_adsp_stdout_path"] = direct.get("stdout_path")
        result["direct_adsp_rc"] = direct.get("rc")
        result["direct_adsp_accepted"] = (
            "audio.adsp_boot_once.write=accepted" in direct_text
            or "audio.adsp_boot_once.refused=already-up-or-sound-present" in direct_text
        )
        if not result["direct_adsp_accepted"]:
            result["decision"] = "v2805-card-first-direct-adsp-refused-before-rollback"
            raise RuntimeError("direct ADSP boot command did not report accepted/already-up")

        card_wait = wait_for_sound_card(out_dir, steps, count=args.card_poll_count, interval=args.card_poll_interval)
        result["card_wait"] = card_wait
        result["card_ready_before_deploy"] = bool(card_wait.get("ready"))
        if not result["card_ready_before_deploy"]:
            result["decision"] = "v2805-card-first-direct-adsp-no-card-before-rollback"
            raise RuntimeError("direct ADSP boot did not publish sound card/control before deploy")

        play_result = run_play_sequence(args, out_dir, steps, deploy_plan, native_manifest_path)
        result.update(play_result)
        if play_result.get("deploy_lost_card"):
            result["decision"] = "v2805-card-first-deploy-lost-card-before-rollback"
            raise RuntimeError("runtime artifact deploy lost sound card/control before play")
        if play_result.get("play_start_failed"):
            result["decision"] = "v2805-card-first-play-start-failed-before-rollback"
            raise RuntimeError("native audio play did not start worker")
        if not result.get("play_output_pass"):
            result["decision"] = "v2805-card-first-play-failed-before-rollback"
            raise RuntimeError("native audio play did not emit all required pass markers")

        candidate_selftest_after = base.run_serial_step(
            out_dir,
            steps,
            "candidate-selftest-after-play",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["candidate_selftest_after_play_fail0"] = base.selftest_step_ok(candidate_selftest_after)
        if not result["candidate_selftest_after_play_fail0"]:
            raise RuntimeError("candidate post-play selftest did not report fail=0")
        result["decision"] = "v2805-card-first-play-pass-before-rollback"
    except Exception as exc:
        if result["decision"] == "v2805-audio-card-first-play-live-started":
            result["decision"] = "v2805-card-first-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        raise
    finally:
        if candidate_flash_attempted:
            result["rollback_attempted"] = True
            rollback = base.rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
            result["rollback_step_ok"] = bool(rollback.get("success"))
            result["rollback_attempts"] = rollback.get("attempts", [])
            result["rollback_recovery_fallback_used"] = bool(rollback.get("used_recovery_fallback"))
            if rollback.get("success"):
                rollback_version = base.run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = base.run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = base.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = base.selftest_step_ok(rollback_selftest)
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def render_report(result: dict[str, Any]) -> str:
    play_summary = result.get("play_summary") or {}
    card_wait = result.get("card_wait") or {}
    status_after_deploy = (result.get("status_after_deploy") or {}).get("summary") or {}
    installed = result.get("runtime_artifacts", {}).get("installed", []) if isinstance(result.get("runtime_artifacts"), dict) else []
    installed_lines = [f"- `{item.get('kind')}` `{item.get('remote')}`" for item in installed] or ["- No runtime artifact installs recorded."]
    return "\n".join([
        "# Native Init V2805 Audio Card-First Play Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio core closure gate discriminator.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate tag/version: `{base.CANDIDATE_TAG}` / `{base.CANDIDATE_VERSION}`",
        f"- Candidate image SHA256: `{result.get('candidate_sha256')}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        f"- Operator audible confirmation: `{result.get('operator_audible_confirmation', 'not-recorded-in-runner')}`",
        "",
        "## Discriminator Evidence",
        "",
        f"- Direct ADSP command: `{result.get('direct_adsp_command')}`",
        f"- Direct ADSP rc/accepted: `{result.get('direct_adsp_rc')}` / `{int(bool(result.get('direct_adsp_accepted')))}`",
        f"- Direct ADSP stdout: `{result.get('direct_adsp_stdout_path')}`",
        f"- Card ready before deploy: `{int(bool(result.get('card_ready_before_deploy')))}` after `{card_wait.get('attempts')}` polls",
        f"- Card poll last summary: `{json.dumps((card_wait.get('last') or {}).get('summary') or {}, ensure_ascii=False, sort_keys=True)}`",
        f"- Card/control after deploy before play: `{int(bool(status_after_deploy.get('has_sound_card')))} / {int(bool(status_after_deploy.get('has_sound_control')))}`",
        "",
        "## Playback Evidence",
        "",
        f"- Native command: `{result.get('play_command')}`",
        f"- Play start rc: `{result.get('play_rc')}`",
        f"- Worker status done/attempts: `{int(bool(result.get('worker_status_done')))}` / `{result.get('worker_status_attempts')}`",
        f"- Worker status stdout: `{result.get('worker_status_stdout_path')}`",
        f"- Worker log stdout: `{result.get('worker_log_stdout_path')}`",
        f"- Worker started/done: `{int(bool(play_summary.get('worker_started')))}` / `{int(bool(play_summary.get('worker_done')))}`",
        f"- Integrated done: `{int(bool(play_summary.get('integrated_done')))}`",
        f"- Sound-control ready/timeout: `{int(bool(play_summary.get('sound_control_wait_ready')))}` / `{int(bool(play_summary.get('sound_control_wait_timeout')))}`",
        f"- SET-cal hold/all-set/dealloc: `{int(bool(play_summary.get('setcal_hold_active')))} / {int(bool(play_summary.get('setcal_all_set')))} / {int(bool(play_summary.get('setcal_deallocated')))}`",
        f"- Route apply/reset OK: `{int(bool(play_summary.get('route_apply_ok')))} / {int(bool(play_summary.get('route_reset_ok')))}`",
        f"- PCM write/done: `{int(bool(play_summary.get('pcm_write_attempted')))} / {int(bool(play_summary.get('pcm_done')))}`",
        f"- Safety amplitude/duration cap: `{int(bool(play_summary.get('safety_amplitude')))} / {int(bool(play_summary.get('safety_duration')))}`",
        "",
        "## Runtime Artifacts",
        "",
        f"- Deploy plan: `{rel(base.DEPLOY_PLAN)}`",
        f"- Native manifest remote path: `{base.REMOTE_NATIVE_MANIFEST}`",
        f"- Native manifest SHA256: `{result.get('native_manifest_sha256')}`",
        *installed_lines,
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed; runtime ACDB files are staged under `/cache` after sound-card publication.",
        "- No forbidden partitions are touched.",
        "- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).",
        "- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.",
        "",
    ])


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": "v2805-card-first-play-live-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "commands": {
            "verify_current": base.flash_command(base.ROLLBACK_IMAGE, base.ROLLBACK_VERSION, base.ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": base.flash_command(base.CANDIDATE_IMAGE, base.CANDIDATE_VERSION, str(state["candidate"].get("sha256") or ""), from_native=True),
            "direct_adsp_boot": ["audio", "adsp-boot-once", ADSP_TOKEN],
            "card_poll": ["audio", "adsp-status"],
            "install_count": state.get("deploy_artifact_count", 0) + 1,
            "play": [
                "audio",
                "play",
                base.PROFILE,
                "--mode",
                args.play_mode,
                "--duration-ms",
                str(args.duration_ms),
                "--amplitude-milli",
                str(args.amplitude_milli),
                "--manifest",
                base.REMOTE_NATIVE_MANIFEST,
                "--execute",
            ],
            "rollback": base.flash_command(base.ROLLBACK_IMAGE, base.ROLLBACK_VERSION, base.ROLLBACK_SHA256, from_native=True),
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run-live", action="store_true")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--host-ip", default="192.168.7.1")
    parser.add_argument("--host-prefix", type=int, default=24)
    parser.add_argument("--tcp-port", type=int, default=2325)
    parser.add_argument("--command-timeout", type=float, default=60.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--device-toolbox", default=base.tiny_live.DEFAULT_DEVICE_TOOLBOX)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-port", type=int, default=18321)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--repair-host-ncm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ncm-setup-timeout", type=float, default=120.0)
    parser.add_argument("--ncm-interface-timeout", type=float, default=20.0)
    parser.add_argument("--ncm-setup-sudo", default="sudo -n")
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--play-mode", choices=("probe", "listen"), default="listen")
    parser.add_argument("--duration-ms", type=int, default=8000)
    parser.add_argument("--amplitude-milli", type=int, default=150)
    parser.add_argument("--play-timeout", type=float, default=240.0)
    parser.add_argument("--card-poll-count", type=int, default=35)
    parser.add_argument("--card-poll-interval", type=float, default=2.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state = preflight_state()
    if args.dry_run:
        print(json.dumps(dry_run_payload(args, state), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if preflight_ok(state) else 2
    result = live_run(args, state)
    print(json.dumps({
        "decision": result.get("decision"),
        "out_dir": result.get("out_dir"),
        "card_ready_before_deploy": result.get("card_ready_before_deploy"),
        "play_output_pass": result.get("play_output_pass"),
        "rollback_version_ok": result.get("rollback_version_ok"),
        "rollback_selftest_fail0": result.get("rollback_selftest_fail0"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if (
        result.get("play_output_pass")
        and result.get("rollback_version_ok")
        and result.get("rollback_selftest_fail0")
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
