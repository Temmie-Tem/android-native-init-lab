#!/usr/bin/env python3
"""V2803 live handoff for native-init audio foreground ADSP prime.

This is the audio core closure gate: flash the V2803 native-init image, stage the
known-good ACDB SET replay artifacts plus native manifest, execute
`audio play internal-speaker-safe --mode listen --execute`, then roll back to
V2321 and verify selftest fail=0.

V2803 flashes the foreground-ADSP-prime candidate, stages the known-good ACDB SET replay artifacts, executes the integrated native audio play command, and rolls back to V2321.
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
import native_audio_tinyalsa_inventory_live_handoff_v2349 as tiny_live

ROOT = repo_root()
A90CTL = ROOT / "workspace/public/src/scripts/revalidation/a90ctl.py"
FLASH = ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
BUILD_MANIFEST = ROOT / "workspace/private/builds/native-init/v2803-audio-foreground-adsp-prime/manifest.json"
CANDIDATE_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2803_audio_foreground_adsp_prime.img"
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
FALLBACK_V2237_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img"
FALLBACK_V48_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v48.img"
DEPLOY_PLAN = ROOT / "workspace/private/builds/audio/v2725-audio-acdb-corrected-core39-ioctl-result-deploy-plan/deploy-plan.json"
REPORT_PATH = ROOT / "docs/reports/NATIVE_INIT_V2803_AUDIO_FOREGROUND_ADSP_PRIME_LIVE_2026-06-19.md"

CYCLE = "V2803"
PROFILE = "internal-speaker-safe"
CANDIDATE_VERSION = "0.9.313"
CANDIDATE_TAG = "v2803-audio-foreground-adsp-prime"
ROLLBACK_VERSION = "0.9.285"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FALLBACK_V2237_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
REMOTE_NATIVE_MANIFEST = "/cache/a90-acdb-setcal-replay-v2725/audio-setcal-internal-speaker-safe.manifest"
REMOTE_PLAY_STATUS = "/cache/a90-audio-play/status.txt"
REMOTE_PLAY_LOG = "/cache/a90-audio-play/worker.log"
EXPECTED_SET_ORDER = [39, 20, 20, 13, 9, 11, 12, 15, 23, 16, 21]
SELFTEST_FAIL0_RE = re.compile(r"\bfail=0\b")
ZERO_SHA256 = hashlib.sha256(b"").hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_text(path: Path, limit: int = 1_000_000) -> str:
    try:
        return path.read_bytes()[:limit].decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def local_private_path(entry: dict[str, Any]) -> Path:
    value = ((entry.get("local") or {}).get("local_path_private") or "")
    path = Path(str(value))
    return path if path.is_absolute() else ROOT / path


def deploy_file_by_remote(deploy_plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for entry in deploy_plan.get("files") or []:
        remote = str(entry.get("remote_path") or "")
        if remote:
            output[remote] = entry
    return output


def deploy_artifacts_for_native_manifest(deploy_plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry for entry in deploy_plan.get("files") or [] if entry.get("kind") != "helper"]


def validate_deploy_plan(deploy_plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not deploy_plan.get("ok"):
        errors.append("deploy plan ok=false")
    if not deploy_plan.get("safe_to_run_native_replay"):
        errors.append("deploy plan safe_to_run_native_replay=false")
    replay_entries = deploy_plan.get("replay_entries") or []
    observed_order = [int(entry.get("cal_type")) for entry in replay_entries]
    if observed_order != EXPECTED_SET_ORDER:
        errors.append(f"unexpected SET order: {observed_order}")
    remote_map = deploy_file_by_remote(deploy_plan)
    for entry in replay_entries:
        arg_remote = str(entry.get("arg_remote") or "")
        if arg_remote not in remote_map:
            errors.append(f"missing arg remote file: {arg_remote}")
        payload_remote = entry.get("payload_remote")
        if entry.get("dmabuf_expected") and not payload_remote:
            errors.append(f"missing payload for dmabuf entry seq={entry.get('sequence')}")
        if payload_remote and str(payload_remote) not in remote_map:
            errors.append(f"missing payload remote file: {payload_remote}")
    for entry in deploy_artifacts_for_native_manifest(deploy_plan):
        local = local_private_path(entry)
        local_state = entry.get("local") or {}
        expected_sha = str(local_state.get("sha256") or "")
        expected_size = int(local_state.get("size") or 0)
        if not local.exists():
            errors.append(f"missing local artifact: {rel(local)}")
            continue
        if expected_sha and sha256_file(local) != expected_sha:
            errors.append(f"sha mismatch: {rel(local)}")
        if expected_size and local.stat().st_size != expected_size:
            errors.append(f"size mismatch: {rel(local)}")
        if local.stat().st_size <= 0:
            errors.append(f"zero-size artifact: {rel(local)}")
    return errors


def render_native_manifest(deploy_plan: dict[str, Any]) -> str:
    remote_map = deploy_file_by_remote(deploy_plan)
    lines = [
        "version 1",
        f"profile {PROFILE}",
        f"entry_count {len(deploy_plan.get('replay_entries') or [])}",
    ]
    for entry in deploy_plan.get("replay_entries") or []:
        sequence = int(entry.get("sequence"))
        cal_type = int(entry.get("cal_type"))
        role = str(entry.get("role") or "-")
        dmabuf_expected = 1 if entry.get("dmabuf_expected") else 0
        arg_remote = str(entry.get("arg_remote") or "")
        arg_file = remote_map[arg_remote]
        arg_local = arg_file.get("local") or {}
        arg_size = int(arg_local.get("size") or entry.get("capture", {}).get("data_size") or 0)
        arg_sha = str(arg_local.get("sha256") or entry.get("capture", {}).get("arg_sha256") or "")
        payload_remote_value = entry.get("payload_remote")
        if payload_remote_value:
            payload_remote = str(payload_remote_value)
            payload_file = remote_map[payload_remote]
            payload_local = payload_file.get("local") or {}
            payload_size = int(payload_local.get("size") or entry.get("capture", {}).get("cal_size") or 0)
            payload_sha = str(payload_local.get("sha256") or entry.get("capture", {}).get("payload_sha256") or "")
        else:
            payload_remote = "-"
            payload_size = 0
            payload_sha = "-"
        lines.append(
            f"entry {sequence} {cal_type} {role} {dmabuf_expected} "
            f"{arg_remote} {arg_size} {arg_sha} {payload_remote} {payload_size} {payload_sha}"
        )
    return "\n".join(lines) + "\n"


def materialize_native_manifest(out_dir: Path, deploy_plan: dict[str, Any]) -> Path:
    manifest_path = out_dir / "runtime" / "audio-setcal-internal-speaker-safe.manifest"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(render_native_manifest(deploy_plan), encoding="utf-8")
    manifest_path.chmod(0o600)
    return manifest_path


def preflight_state() -> dict[str, Any]:
    build_manifest = read_json(BUILD_MANIFEST)
    deploy_plan = read_json(DEPLOY_PLAN)
    candidate_expected_sha = str(build_manifest.get("boot_sha256") or "")
    deploy_errors = validate_deploy_plan(deploy_plan) if deploy_plan else ["missing deploy plan"]
    return {
        "cycle": CYCLE,
        "build_manifest": rel(BUILD_MANIFEST),
        "build_manifest_exists": BUILD_MANIFEST.exists(),
        "build_manifest_decision": build_manifest.get("decision"),
        "candidate": file_state(CANDIDATE_IMAGE, candidate_expected_sha),
        "candidate_expect_version": CANDIDATE_VERSION,
        "candidate_expect_tag": CANDIDATE_TAG,
        "rollback": file_state(ROLLBACK_IMAGE, ROLLBACK_SHA256),
        "rollback_expect_version": ROLLBACK_VERSION,
        "fallback_v2237": file_state(FALLBACK_V2237_IMAGE, FALLBACK_V2237_SHA256),
        "fallback_v48": file_state(FALLBACK_V48_IMAGE),
        "flash_helper": file_state(FLASH),
        "a90ctl": file_state(A90CTL),
        "deploy_plan": rel(DEPLOY_PLAN),
        "deploy_plan_exists": DEPLOY_PLAN.exists(),
        "deploy_plan_ok": bool(deploy_plan and not deploy_errors),
        "deploy_errors": deploy_errors,
        "deploy_artifact_count": len(deploy_artifacts_for_native_manifest(deploy_plan)) if deploy_plan else 0,
        "replay_entry_count": len(deploy_plan.get("replay_entries") or []) if deploy_plan else 0,
        "remote_native_manifest": REMOTE_NATIVE_MANIFEST,
        "live_scope": [
            "boot partition only via native_init_flash.py",
            "stage private ACDB SET arg/payload files under /cache runtime paths",
            "run native audio play internal-speaker-safe --mode listen --execute once",
            "low-amplitude profile cap is enforced by native-init source",
            "rollback to v2321 and verify selftest fail=0",
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
        and state["deploy_plan_ok"]
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
    steps.append(record)
    write_json(out_dir / f"{len(steps) - 1:02d}_{name}.json", record)
    if not record["ok"] and not allow_error:
        raise RuntimeError(f"step failed: {name}")
    return record


def stdout_of(step: dict[str, Any]) -> str:
    return read_text(ROOT / str(step.get("stdout_path") or ""))


def selftest_ok(text: str) -> bool:
    return bool(SELFTEST_FAIL0_RE.search(text))


def protocol_selftest_ok(step: dict[str, Any]) -> bool:
    protocol = step.get("protocol") if isinstance(step.get("protocol"), dict) else {}
    end = protocol.get("end") if isinstance(protocol.get("end"), dict) else {}
    return bool(
        step.get("rc") == 0
        and protocol.get("status") == "ok"
        and end.get("cmd") == "selftest"
        and end.get("rc") == "0"
        and end.get("errno") == "0"
        and end.get("status") == "ok"
    )


def selftest_step_ok(step: dict[str, Any]) -> bool:
    return selftest_ok(stdout_of(step)) or protocol_selftest_ok(step)


def adb_recovery_present() -> bool:
    try:
        completed = subprocess.run(
            ["adb", "devices"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(line.strip().endswith("\trecovery") for line in completed.stdout.splitlines())


def rollback_v2321(out_dir: Path, steps: list[dict[str, Any]], *, from_native: bool,
                   timeout: float) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    first = run_step(
        out_dir,
        steps,
        "rollback-v2321",
        flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=from_native),
        timeout=timeout,
        allow_error=True,
    )
    attempts.append({
        "name": first.get("name"),
        "from_native": from_native,
        "rc": first.get("rc"),
        "success": first.get("rc") == 0,
    })
    if first.get("rc") == 0:
        return {"success": True, "attempts": attempts, "used_recovery_fallback": False}
    recovery_seen = adb_recovery_present()
    attempts[-1]["adb_recovery_present_after_failure"] = recovery_seen
    if not from_native or not recovery_seen:
        return {"success": False, "attempts": attempts, "used_recovery_fallback": False}
    second = run_step(
        out_dir,
        steps,
        "rollback-v2321-recovery-fallback",
        flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False),
        timeout=timeout,
        allow_error=True,
    )
    attempts.append({
        "name": second.get("name"),
        "from_native": False,
        "rc": second.get("rc"),
        "success": second.get("rc") == 0,
    })
    return {"success": second.get("rc") == 0, "attempts": attempts, "used_recovery_fallback": True}


def install_runtime_artifacts(args: argparse.Namespace,
                              out_dir: Path,
                              steps: list[dict[str, Any]],
                              deploy_plan: dict[str, Any],
                              native_manifest_path: Path) -> dict[str, Any]:
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = str(readiness["selected_transport"])
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    result: dict[str, Any] = {
        "transfer_readiness": readiness,
        "selected_transport": selected,
        "control_channel": control_channel,
        "installed": [],
    }
    artifacts = deploy_artifacts_for_native_manifest(deploy_plan)
    port = int(args.transfer_port)
    for index, entry in enumerate(artifacts):
        name = f"acdb-{index:02d}-{entry.get('kind')}"
        step = run_step(
            out_dir,
            steps,
            f"install-{name}",
            tiny_live.install_command(
                args,
                local_private_path(entry),
                str(entry.get("remote_path")),
                port + index,
                control_channel=control_channel,
            ),
            timeout=args.transfer_timeout + 60.0,
        )
        result["installed"].append({
            "name": name,
            "kind": entry.get("kind"),
            "remote": entry.get("remote_path"),
            "stdout_path": step.get("stdout_path"),
        })
    manifest_step = run_step(
        out_dir,
        steps,
        "install-native-setcal-manifest",
        tiny_live.install_command(
            args,
            native_manifest_path,
            REMOTE_NATIVE_MANIFEST,
            port + len(artifacts),
            control_channel=control_channel,
        ),
        timeout=args.transfer_timeout + 60.0,
    )
    result["installed"].append({
        "name": "native-setcal-manifest",
        "kind": "native_manifest",
        "remote": REMOTE_NATIVE_MANIFEST,
        "sha256": sha256_file(native_manifest_path),
        "stdout_path": manifest_step.get("stdout_path"),
    })
    return result


def classify_play_output(text: str) -> dict[str, Any]:
    return {
        "worker_started": "audio.play.worker.started=1" in text,
        "worker_done": "audio.play.worker.done=1 rc=0" in text,
        "worker_log_available": "audio.play_status.log_path=/cache/a90-audio-play/worker.log" in text
        or "[a90-console-child-log path=/cache/a90-audio-play/worker.log]" in text,
        "listen_begin": "A90_LISTEN_WINDOW_BEGIN" in text,
        "listen_end": "A90_LISTEN_WINDOW_END" in text,
        "foreground_prime_seen": "audio.play.execute.foreground_prime_adsp=1" in text,
        "foreground_prime_ok": "audio.play.execute.foreground_prime_adsp.rc=0" in text,
        "foreground_prime_failed": "audio.play.execute.foreground_prime_adsp.failed=1" in text,
        "integrated_done": "audio.play.integrated.done=1 rc=0" in text,
        "sound_control_wait_timeout": "audio.play.integrated.wait.sound_control.ready=0" in text,
        "sound_control_wait_ready": "audio.play.integrated.wait.sound_control.ready=1" in text,
        "ion_materialize_seen": "audio.ion_materialize.version=1" in text,
        "ion_materialize_ok": "audio.ion_materialize.created=1" in text
        or "audio.ion_materialize.already_ok=1" in text,
        "ion_alloc_ok": "audio.setcal.execute.ion.alloc_ok=1" in text,
        "msm_audio_cal_materialize_seen": "audio.msm_audio_cal_materialize.version=1" in text,
        "msm_audio_cal_materialize_ok": "audio.msm_audio_cal_materialize.created=1" in text
        or "audio.msm_audio_cal_materialize.already_ok=1" in text,
        "msm_audio_cal_open_ok": "audio.setcal.execute.open.msm_audio_cal.open_ok=1" in text,
        "dmabuf_msync_nonfatal": "audio.setcal.execute.entry.0.msync_nonfatal=1" in text,
        "setcal_prepared_all": "audio.setcal.execute.prepared_count=11" in text,
        "msm_audio_cal_missing": "audio.setcal.execute.open.msm_audio_cal.open_ok=0 errno=2" in text,
        "setcal_allocate_request_native": "audio.setcal.execute.ioctl.0.request=0xc00861c8" in text,
        "setcal_set_request_native": "audio.setcal.execute.ioctl.1.request=0xc00861cb" in text
        or "audio.setcal.execute.ioctl.2.request=0xc00861cb" in text,
        "setcal_allocate_efault": "audio.setcal.execute.allocate_failed.index=0 errno=14" in text,
        "setcal_first_ioctl_efault": "audio.setcal.execute.ioctl.0.rc=-1 errno=14" in text,
        "setcal_hold_active": "audio.setcal.execute.hold_active=1" in text,
        "setcal_all_set": "audio.setcal.execute.set_count=11" in text,
        "setcal_deallocated": "audio.setcal.execute.deallocated_count=4" in text,
        "route_apply_ok": "audio.play.integrated.route_apply.rc=0" in text,
        "route_reset_ok": "audio.play.integrated.route_reset.rc=0" in text,
        "pcm_write_attempted": "audio.play.execute.pcm_write_attempted=1" in text,
        "pcm_done": "audio.play.execute.done=1" in text,
        "safety_amplitude": "audio.play.safety.amplitude_within_cap=1" in text,
        "safety_duration": "audio.play.safety.duration_within_cap=1" in text,
    }


def play_output_pass(summary: dict[str, Any]) -> bool:
    required = [
        "worker_started",
        "worker_done",
        "listen_begin",
        "listen_end",
        "foreground_prime_seen",
        "foreground_prime_ok",
        "integrated_done",
        "ion_materialize_seen",
        "ion_materialize_ok",
        "ion_alloc_ok",
        "msm_audio_cal_materialize_seen",
        "msm_audio_cal_materialize_ok",
        "msm_audio_cal_open_ok",
        "setcal_hold_active",
        "setcal_all_set",
        "setcal_deallocated",
        "route_apply_ok",
        "route_reset_ok",
        "pcm_write_attempted",
        "pcm_done",
        "safety_amplitude",
        "safety_duration",
    ]
    return all(bool(summary.get(key)) for key in required)


def wait_for_worker_done(out_dir: Path,
                         steps: list[dict[str, Any]],
                         timeout_sec: float,
                         interval_sec: float = 2.0) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    attempts = 0
    last_step: dict[str, Any] | None = None
    while time.time() < deadline:
        attempts += 1
        step = run_serial_step(
            out_dir,
            steps,
            f"candidate-audio-play-status-{attempts:02d}",
            ["audio", "play-status"],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        last_step = step
        text = stdout_of(step)
        if "audio.play.worker.done=1" in text:
            step["worker_poll_done"] = True
            return {
                "done": True,
                "attempts": attempts,
                "stdout_path": step.get("stdout_path"),
                "text": text,
            }
        time.sleep(interval_sec)
    return {
        "done": False,
        "attempts": attempts,
        "stdout_path": last_step.get("stdout_path") if last_step else None,
        "text": stdout_of(last_step) if last_step else "",
    }


def render_report(result: dict[str, Any]) -> str:
    play_summary = result.get("play_summary") or {}
    installed = result.get("runtime_artifacts", {}).get("installed", []) if isinstance(result.get("runtime_artifacts"), dict) else []
    installed_lines = [f"- `{item.get('kind')}` `{item.get('remote')}`" for item in installed]
    if not installed_lines:
        installed_lines = ["- No runtime artifact installs recorded."]
    return "\n".join([
        "# Native Init V2803 Audio Foreground ADSP Prime Live Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: audio core closure gate.",
        f"- Decision: `{result.get('decision')}`",
        f"- Result directory: `{result.get('out_dir')}`",
        f"- Candidate tag: `{CANDIDATE_TAG}`",
        f"- Candidate image SHA256: `{result.get('candidate_sha256')}`",
        f"- Rollback attempted: `{int(bool(result.get('rollback_attempted')))}`",
        f"- Rollback recovery fallback used: `{int(bool(result.get('rollback_recovery_fallback_used')))}`",
        f"- Rollback health: version_ok=`{int(bool(result.get('rollback_version_ok')))}` selftest_fail0=`{int(bool(result.get('rollback_selftest_fail0')))}`",
        f"- Operator audible confirmation: `{result.get('operator_audible_confirmation', 'not-recorded-in-runner')}`",
        "",
        "## Playback Evidence",
        "",
        f"- Native command: `{result.get('play_command')}`",
        f"- Play start rc: `{result.get('play_rc')}`",
        f"- Worker status done/attempts: `{int(bool(result.get('worker_status_done')))}` / `{result.get('worker_status_attempts')}`",
        f"- Worker status stdout: `{result.get('worker_status_stdout_path')}`",
        f"- Worker log stdout: `{result.get('worker_log_stdout_path')}`",
        f"- Worker started/done: `{int(bool(play_summary.get('worker_started')))}` / `{int(bool(play_summary.get('worker_done')))}`",
        f"- Listen window begin/end: `{int(bool(play_summary.get('listen_begin')))} / {int(bool(play_summary.get('listen_end')))}`",
        f"- Foreground ADSP prime seen/ok/failed: `{int(bool(play_summary.get('foreground_prime_seen')))} / {int(bool(play_summary.get('foreground_prime_ok')))} / {int(bool(play_summary.get('foreground_prime_failed')))}`",
        f"- Integrated done: `{int(bool(play_summary.get('integrated_done')))}`",
        f"- Sound-control ready/timeout: `{int(bool(play_summary.get('sound_control_wait_ready')))}` / `{int(bool(play_summary.get('sound_control_wait_timeout')))}`",
        f"- ION materialize seen/ok/alloc: `{int(bool(play_summary.get('ion_materialize_seen')))} / {int(bool(play_summary.get('ion_materialize_ok')))} / {int(bool(play_summary.get('ion_alloc_ok')))}`",
        f"- MSM audio cal materialize seen/ok/open/missing: `{int(bool(play_summary.get('msm_audio_cal_materialize_seen')))} / {int(bool(play_summary.get('msm_audio_cal_materialize_ok')))} / {int(bool(play_summary.get('msm_audio_cal_open_ok')))} / {int(bool(play_summary.get('msm_audio_cal_missing')))}`",
        f"- DMABUF msync nonfatal / SET entries prepared: `{int(bool(play_summary.get('dmabuf_msync_nonfatal')))} / {int(bool(play_summary.get('setcal_prepared_all')))}`",
        f"- SET-cal native allocate/set request seen: `{int(bool(play_summary.get('setcal_allocate_request_native')))} / {int(bool(play_summary.get('setcal_set_request_native')))}`",
        f"- SET-cal first ioctl EFAULT / allocate EFAULT: `{int(bool(play_summary.get('setcal_first_ioctl_efault')))} / {int(bool(play_summary.get('setcal_allocate_efault')))}`",
        f"- SET-cal hold/all-set/dealloc: `{int(bool(play_summary.get('setcal_hold_active')))} / {int(bool(play_summary.get('setcal_all_set')))} / {int(bool(play_summary.get('setcal_deallocated')))}`",
        f"- Route apply/reset OK: `{int(bool(play_summary.get('route_apply_ok')))} / {int(bool(play_summary.get('route_reset_ok')))}`",
        f"- PCM write/done: `{int(bool(play_summary.get('pcm_write_attempted')))} / {int(bool(play_summary.get('pcm_done')))}`",
        f"- Safety amplitude/duration cap: `{int(bool(play_summary.get('safety_amplitude')))} / {int(bool(play_summary.get('safety_duration')))}`",
        "",
        "## Diagnostic Captures",
        "",
        f"- ADSP status before play: `{result.get('adsp_status_before_play_stdout_path')}`",
        f"- SND status before play: `{result.get('snd_status_before_play_stdout_path')}`",
        f"- ADSP status after play: `{result.get('adsp_status_after_play_stdout_path')}`",
        f"- SND status after play: `{result.get('snd_status_after_play_stdout_path')}`",
        f"- Dmesg audio tail: `{result.get('dmesg_audio_tail_stdout_path')}`",
        "",
        "## Runtime Artifacts",
        "",
        f"- Deploy plan: `{rel(DEPLOY_PLAN)}`",
        f"- Native manifest remote path: `{REMOTE_NATIVE_MANIFEST}`",
        f"- Native manifest SHA256: `{result.get('native_manifest_sha256')}`",
        *installed_lines,
        "",
        "## Safety",
        "",
        "- Flash path: `workspace/public/src/scripts/revalidation/native_init_flash.py`.",
        "- Only the boot partition is flashed; runtime ACDB files are staged under `/cache`.",
        "- No forbidden partitions are touched.",
        "- `audio play` uses the source-enforced `internal-speaker-safe` profile caps (`listen` amplitude 0.15, cap 0.2).",
        "- Public report is metadata-only; private ACDB payloads and raw command transcripts stay under `workspace/private/`.",
        "",
    ])


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    if not preflight_ok(state):
        raise SystemExit("refusing live run: preflight failed")
    deploy_plan = read_json(DEPLOY_PLAN)
    candidate_sha = str(state["candidate"]["sha256"])
    out_dir = ROOT / f"workspace/private/runs/audio/v2803-audio-foreground-adsp-prime-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    native_manifest_path = materialize_native_manifest(out_dir, deploy_plan)
    write_json(out_dir / "preflight.json", state)
    steps: list[dict[str, Any]] = []
    play_command = [
        "audio",
        "play",
        PROFILE,
        "--mode",
        args.play_mode,
        "--duration-ms",
        str(args.duration_ms),
        "--amplitude-milli",
        str(args.amplitude_milli),
        "--manifest",
        REMOTE_NATIVE_MANIFEST,
        "--execute",
    ]
    result: dict[str, Any] = {
        "decision": "v2803-audio-foreground-adsp-prime-live-started",
        "out_dir": rel(out_dir),
        "candidate_sha256": candidate_sha,
        "native_manifest_path": rel(native_manifest_path),
        "native_manifest_sha256": sha256_file(native_manifest_path),
        "play_command": " ".join(play_command),
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
        result["preflight_current_selftest_fail0"] = selftest_step_ok(current_selftest)
        if not result["preflight_current_selftest_fail0"]:
            raise RuntimeError("resident preflight selftest did not report fail=0")

        candidate_flash_attempted = True
        run_step(
            out_dir,
            steps,
            "flash-v2803-candidate",
            flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, candidate_sha, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flash_ok = True

        version = run_serial_step(out_dir, steps, "candidate-version", ["version"], timeout=90.0, retry_unsafe=True)
        result["candidate_version_ok"] = CANDIDATE_VERSION in stdout_of(version)
        if not result["candidate_version_ok"]:
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
        result["candidate_selftest_fail0"] = selftest_step_ok(candidate_selftest)
        if not result["candidate_selftest_fail0"]:
            raise RuntimeError("candidate selftest did not report fail=0")
        adsp_before = run_serial_step(
            out_dir,
            steps,
            "candidate-audio-adsp-status-before-play",
            ["audio", "adsp-status"],
            timeout=120.0,
            retry_unsafe=True,
            allow_error=True,
        )
        snd_before = run_serial_step(
            out_dir,
            steps,
            "candidate-audio-snd-status-before-play",
            ["audio", "snd-status"],
            timeout=120.0,
            retry_unsafe=True,
            allow_error=True,
        )
        result["adsp_status_before_play_stdout_path"] = adsp_before.get("stdout_path")
        result["snd_status_before_play_stdout_path"] = snd_before.get("stdout_path")

        result["runtime_artifacts"] = install_runtime_artifacts(args, out_dir, steps, deploy_plan, native_manifest_path)
        prereq = run_serial_step(out_dir, steps, "candidate-audio-prereq", ["audio", "prereq", PROFILE], timeout=150.0, retry_unsafe=True)
        result["prereq_stdout_path"] = prereq.get("stdout_path")
        play = run_serial_step(
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
            result["decision"] = "v2803-audio-foreground-adsp-prime-start-failed-before-rollback"
            result["play_summary"] = classify_play_output(play_text)
            raise RuntimeError("native audio foreground ADSP-prime command did not start")

        worker = wait_for_worker_done(out_dir, steps, args.play_timeout)
        result["worker_status_done"] = bool(worker.get("done"))
        result["worker_status_attempts"] = worker.get("attempts")
        result["worker_status_stdout_path"] = worker.get("stdout_path")
        log_step = run_serial_step(
            out_dir,
            steps,
            "candidate-audio-foreground-adsp-prime-log",
            ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG],
            timeout=45.0,
            retry_unsafe=True,
            allow_error=True,
        )
        log_text = stdout_of(log_step)
        result["worker_log_stdout_path"] = log_step.get("stdout_path")
        combined_text = "\n".join([play_text, str(worker.get("text") or ""), log_text])
        result["play_summary"] = classify_play_output(combined_text)
        result["play_output_pass"] = play_output_pass(result["play_summary"])
        adsp_after = run_serial_step(
            out_dir,
            steps,
            "candidate-audio-adsp-status-after-play",
            ["audio", "adsp-status"],
            timeout=120.0,
            retry_unsafe=True,
            allow_error=True,
        )
        snd_after = run_serial_step(
            out_dir,
            steps,
            "candidate-audio-snd-status-after-play",
            ["audio", "snd-status"],
            timeout=120.0,
            retry_unsafe=True,
            allow_error=True,
        )
        dmesg_tail = run_serial_step(
            out_dir,
            steps,
            "candidate-dmesg-audio-tail",
            ["run", "/bin/busybox", "sh", "-c", "dmesg | tail -n 240"],
            timeout=90.0,
            retry_unsafe=True,
            allow_error=True,
        )
        result["adsp_status_after_play_stdout_path"] = adsp_after.get("stdout_path")
        result["snd_status_after_play_stdout_path"] = snd_after.get("stdout_path")
        result["dmesg_audio_tail_stdout_path"] = dmesg_tail.get("stdout_path")
        if not result["play_output_pass"]:
            result["decision"] = "v2803-audio-foreground-adsp-prime-worker-failed-before-rollback"
            raise RuntimeError("native audio foreground ADSP-prime command did not emit all required pass markers")

        candidate_selftest_after = run_serial_step(
            out_dir,
            steps,
            "candidate-selftest-after-play",
            ["selftest", "verbose"],
            timeout=120.0,
            retry_unsafe=True,
        )
        result["candidate_selftest_after_play_fail0"] = selftest_step_ok(candidate_selftest_after)
        if not result["candidate_selftest_after_play_fail0"]:
            raise RuntimeError("candidate post-play selftest did not report fail=0")
        result["decision"] = "v2803-audio-foreground-adsp-prime-native-command-pass-before-rollback"
    except Exception as exc:
        result.setdefault("decision", "v2803-audio-foreground-adsp-prime-live-blocked")
        if result["decision"] == "v2803-audio-foreground-adsp-prime-live-started":
            result["decision"] = "v2803-audio-foreground-adsp-prime-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        raise
    finally:
        if candidate_flash_attempted:
            result["rollback_attempted"] = True
            rollback = rollback_v2321(out_dir, steps, from_native=candidate_flash_ok, timeout=args.flash_timeout)
            result["rollback_step_ok"] = bool(rollback.get("success"))
            result["rollback_attempts"] = rollback.get("attempts", [])
            result["rollback_recovery_fallback_used"] = bool(rollback.get("used_recovery_fallback"))
            if rollback.get("success"):
                rollback_version = run_serial_step(out_dir, steps, "rollback-version", ["version"], timeout=90.0, retry_unsafe=True, allow_error=True)
                rollback_selftest = run_serial_step(out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0, retry_unsafe=True, allow_error=True)
                result["rollback_version_ok"] = ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = selftest_step_ok(rollback_selftest)
        write_json(out_dir / "result.json", result)
        REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    return result


def dry_run_payload(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    deploy_plan = read_json(DEPLOY_PLAN)
    return {
        "decision": "v2803-audio-foreground-adsp-prime-live-dry-run",
        "preflight_ok": preflight_ok(state),
        "preflight": state,
        "native_manifest_preview_sha256": hashlib.sha256(render_native_manifest(deploy_plan).encode("utf-8")).hexdigest() if deploy_plan else "",
        "commands": {
            "verify_current": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            "flash_candidate": flash_command(CANDIDATE_IMAGE, CANDIDATE_VERSION, str(state["candidate"].get("sha256") or ""), from_native=True),
            "install_count": state.get("deploy_artifact_count", 0) + 1,
            "play": [
                "audio",
                "play",
                PROFILE,
                "--mode",
                args.play_mode,
                "--duration-ms",
                str(args.duration_ms),
                "--amplitude-milli",
                str(args.amplitude_milli),
                "--manifest",
                REMOTE_NATIVE_MANIFEST,
                "--execute",
            ],
            "play_status": ["audio", "play-status"],
            "play_worker_log": ["run", "/bin/busybox", "cat", REMOTE_PLAY_LOG],
            "rollback": flash_command(ROLLBACK_IMAGE, ROLLBACK_VERSION, ROLLBACK_SHA256, from_native=True),
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
    parser.add_argument("--device-toolbox", default=tiny_live.DEFAULT_DEVICE_TOOLBOX)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--transfer-port", type=int, default=18291)
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
