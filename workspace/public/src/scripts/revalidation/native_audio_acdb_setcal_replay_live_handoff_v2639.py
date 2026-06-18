#!/usr/bin/env python3
"""V2639 checked live handoff for ACDB SET-cal native replay.

Live mode is implemented and must pass the V2637/V2638 deployment-integrity
gate before any device action. Per the 2026-06-18 GOAL policy update, native
SET-cal replay is self-authorized inside the recoverable envelope; legacy
approval and Gate-2 flags are accepted as no-op compatibility options.
"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_setcal_replay_live_gate_v2637 as v2637
import native_audio_acdb_setcal_replay_live_runner_plan_v2638 as planmod
import native_audio_acdb_topology_replay_live_handoff_v2552 as topology_live
import native_audio_speaker_pilot_live_handoff_v2379 as speaker
import native_audio_snd_nodes_preflight_handoff_v2335 as snd

RUN_ID = "V2639"
BUILD_TAG = "v2639-audio-acdb-setcal-replay-live-handoff"
DEFAULT_MANIFEST = snd.ROOT / "workspace/private/builds/audio" / BUILD_TAG / "manifest.json"
DEFAULT_OUT_BASE = snd.ROOT / "workspace/private/runs/audio"
APPROVAL_PHRASE = v2637.APPROVAL_PHRASE
DMESG_TAIL_LINE_COUNT = 260


def rel(path: Path | str) -> str:
    return snd.rel(Path(path)) if not isinstance(path, str) or path.startswith("/") is False else path


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def write_json(path: Path, payload: Any) -> None:
    snd.write_json(path, payload)


def write_private_json(path: Path, payload: Any) -> None:
    write_json(path, payload)
    path.chmod(0o600)


def stdout_of(step: dict[str, Any]) -> str:
    return snd.stdout_of(step)


def load_deploy_manifest(path: Path) -> dict[str, Any]:
    return planmod.load_v2636(path)


def verify_live_gate(args: argparse.Namespace, deploy_manifest: dict[str, Any]) -> None:
    v2637.verify_live_gate(
        args.approval,
        operator_gate2_accepted=args.operator_gate2_accepted,
        deploy_manifest=deploy_manifest,
    )


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    plan = planmod.build_runner_plan(args)
    payload = copy.deepcopy(plan)
    payload.update(
        {
            "run_id": RUN_ID,
            "build_tag": BUILD_TAG,
            "source_plan_run_id": planmod.RUN_ID,
            "decision": "v2639-setcal-replay-live-handoff-dry-run",
            "live_runner_implemented": True,
            "live_runner_default": "dry-run",
            "live_gate_passed_now": False,
            "manifest_path": rel(args.manifest_path),
        }
    )
    return payload


def run_selftest_fail0(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return topology_live.run_selftest_fail0_observation(args, out_dir, steps, name)


def local_private_path(entry: dict[str, Any]) -> Path:
    local = entry.get("local") or {}
    value = local.get("local_path_private")
    if not value:
        raise RuntimeError(f"deployment entry lacks local_path_private for {entry.get('remote_path')}")
    path = Path(str(value))
    return path if path.is_absolute() else snd.ROOT / path


def install_artifact(args: argparse.Namespace,
                     out_dir: Path,
                     steps: list[dict[str, Any]],
                     name: str,
                     local_path: Path,
                     remote_path: str,
                     port: int,
                     control_channel: str) -> dict[str, Any]:
    step = speaker.run_host_step(
        out_dir,
        steps,
        f"install-{name}",
        speaker.tiny_live.install_command(args, local_path, remote_path, port, control_channel=control_channel),
        timeout=args.transfer_timeout + 60.0,
        allow_error=True,
    )
    if not step.get("ok") or int(step.get("rc") or 0) != 0:
        raise RuntimeError(f"install failed for {name}: {step.get('stdout_tail') or step.get('stderr_tail')}")
    return {"ok": True, "remote": remote_path, "stdout_path": step.get("stdout_path")}


def raw_tool_path(name: str, args: argparse.Namespace) -> Path:
    return topology_live.raw_tool_path(name, args)


def pcm_probe_path(args: argparse.Namespace) -> Path:
    return topology_live.pcm_probe_path(args)


def install_runtime_artifacts(args: argparse.Namespace,
                              out_dir: Path,
                              steps: list[dict[str, Any]],
                              deploy_manifest: dict[str, Any],
                              pcm_path: Path,
                              route_plan: dict[str, Any],
                              state: dict[str, Any]) -> dict[str, Any]:
    readiness = speaker.tiny_live.probe_transfer_readiness(args, out_dir, steps)
    selected = readiness["selected_transport"]
    control_channel = "tcpctl" if selected == "tcpctl" else "bridge"
    result: dict[str, Any] = {
        "transfer_readiness": readiness,
        "selected_transport": selected,
        "control_channel": control_channel,
        "artifacts": {},
        "scripts": {},
    }
    port = int(args.transfer_port)
    for index, entry in enumerate(deploy_manifest.get("files") or []):
        name = f"acdb-{index:02d}-{entry.get('kind')}"
        result["artifacts"][name] = install_artifact(
            args,
            out_dir,
            steps,
            name,
            local_private_path(entry),
            str(entry.get("remote_path")),
            port + index,
            control_channel,
        )
    extra = [
        ("tinymix", raw_tool_path("tinymix", args), route_plan["remote_tinymix"], port + 40),
        ("pcm_probe", pcm_probe_path(args), route_plan["remote_pcm_probe"], port + 41),
        ("pilot_wav", pcm_path, route_plan["remote_pcm"], port + 42),
    ]
    for name, local_path, remote_path, transfer_port in extra:
        result["artifacts"][name] = install_artifact(args, out_dir, steps, name, local_path, remote_path, transfer_port, control_channel)
    for offset, (script_key, remote_path, local_path) in enumerate(runtime_script_files(out_dir, state, deploy_manifest)):
        artifact_name = f"script-{script_key}"
        result["scripts"][script_key] = install_artifact(
            args,
            out_dir,
            steps,
            artifact_name,
            local_path,
            remote_path,
            port + 60 + offset,
            control_channel,
        )
        result["scripts"][script_key]["remote_path"] = remote_path
    return result


def runtime_script_files(out_dir: Path,
                         state: dict[str, Any],
                         deploy_manifest: dict[str, Any]) -> list[tuple[str, str, Path]]:
    script_dir = out_dir / "runtime-scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    paths = state.get("remote_script_paths") or planmod.remote_script_paths(deploy_manifest)
    files: list[tuple[str, str, Path]] = []
    for script_key in ("start_and_wait_all_set", "deallocate_check", "runtime_cleanup"):
        body = str((state.get("remote_scripts") or {}).get(script_key) or "")
        if not body.strip():
            raise RuntimeError(f"missing remote script body: {script_key}")
        local_path = script_dir / Path(str(paths[script_key])).name
        local_path.write_text(body + "\n", encoding="utf-8")
        local_path.chmod(0o600)
        files.append((script_key, str(paths[script_key]), local_path))
    return files


def run_remote_shell(args: argparse.Namespace,
                     out_dir: Path,
                     steps: list[dict[str, Any]],
                     name: str,
                     script: str,
                     *,
                     timeout: float,
                     allow_error: bool = False) -> dict[str, Any]:
    return speaker.run_tool_command(
        args,
        out_dir,
        steps,
        name,
        [args.device_busybox, "sh", "-c", script],
        use_tcpctl=False,
        timeout=timeout,
        allow_error=allow_error,
    )


def run_remote_script(args: argparse.Namespace,
                      out_dir: Path,
                      steps: list[dict[str, Any]],
                      name: str,
                      remote_script: str,
                      *,
                      timeout: float,
                      allow_error: bool = False) -> dict[str, Any]:
    return speaker.run_tool_command(
        args,
        out_dir,
        steps,
        name,
        [args.device_busybox, "sh", remote_script],
        use_tcpctl=False,
        timeout=timeout,
        allow_error=allow_error,
    )


def remote_step_clean(step: dict[str, Any]) -> bool:
    if not step.get("ok"):
        return False
    recovery = step.get("serial_recovery") or {}
    if recovery.get("reason") == "protocol-noise" or recovery.get("unsafe_retry"):
        return False
    text = speaker.step_text(step)
    return "[err] unknown command" not in text and "unknown command:" not in text


def route_plan(args: argparse.Namespace) -> dict[str, Any]:
    base = planmod.speaker_args(args)
    plan = speaker.speaker_plan(base)
    return {
        "raw": plan,
        "remote_tinymix": speaker.REMOTE_TINYMIX,
        "remote_pcm_probe": speaker.REMOTE_PCM_PROBE,
        "remote_pcm": speaker.REMOTE_PCM,
    }


def run_setcal_replay_and_pcm(args: argparse.Namespace,
                              out_dir: Path,
                              steps: list[dict[str, Any]],
                              state: dict[str, Any],
                              deploy_manifest: dict[str, Any]) -> dict[str, Any]:
    plan = route_plan(args)
    route = plan["raw"]
    pcm_path = out_dir / "pilot_48k_s16le_stereo_0p02_1s.wav"
    pcm = speaker.generate_pilot_wav(pcm_path, duration_ms=args.duration_ms, amplitude=args.amplitude)
    result: dict[str, Any] = {
        "pilot_wav": pcm,
        "install": {},
        "route_apply": [],
        "route_reset": [],
        "playback_attempted": False,
        "helper_started": False,
    }
    install = install_runtime_artifacts(args, out_dir, steps, deploy_manifest, pcm_path, plan, state)
    result["install"] = install
    use_tcpctl = install["selected_transport"] == "tcpctl"
    route_use_tcpctl = args.route_transport == "tcpctl"
    baseline_step: dict[str, Any] | None = None
    post_reset_step: dict[str, Any] | None = None
    helper_started = False
    deferred_error: Exception | None = None
    try:
        try:
            baseline_step = speaker.run_tool_command(
                args,
                out_dir,
                steps,
                "tinymix-all-values-before-setcal-replay",
                [plan["remote_tinymix"], "-D", str(args.card), "--all-values"],
                use_tcpctl=use_tcpctl,
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["baseline_snapshot"] = {"ok": bool(baseline_step.get("ok")), "stdout_path": baseline_step.get("stdout_path")}
            if not baseline_step.get("ok"):
                raise RuntimeError(f"baseline tinymix snapshot failed: {baseline_step.get('remote_tool_result')}")
            app_type = route.get("app_type_command")
            if app_type:
                step = speaker.run_tool_command(
                    args,
                    out_dir,
                    steps,
                    app_type["name"],
                    [str(part) for part in app_type["argv"]],
                    use_tcpctl=route_use_tcpctl,
                    timeout=args.mixer_timeout,
                    allow_error=True,
                    failure_markers=("Invalid mixer control",),
                )
                result["app_type_gate"] = {"ok": bool(step.get("ok")), "stdout_path": step.get("stdout_path"), "remote_tool_result": step.get("remote_tool_result")}
                if not step.get("ok"):
                    raise RuntimeError(f"App Type gate failed: {step.get('remote_tool_result')}")
            for command in route.get("route_apply_commands") or []:
                step = speaker.run_tool_command(
                    args,
                    out_dir,
                    steps,
                    command["name"],
                    [str(part) for part in command["argv"]],
                    use_tcpctl=route_use_tcpctl,
                    timeout=args.mixer_timeout,
                    allow_error=True,
                    failure_markers=("Invalid mixer control",),
                )
                result["route_apply"].append({"name": command["name"], "ok": bool(step.get("ok")), "stdout_path": step.get("stdout_path"), "remote_tool_result": step.get("remote_tool_result")})
                if not step.get("ok"):
                    raise RuntimeError(f"route apply failed: {command['name']}: {step.get('remote_tool_result')}")
            replay_script = install["scripts"]["start_and_wait_all_set"]["remote_path"]
            replay_step = run_remote_script(
                args,
                out_dir,
                steps,
                "acdb-setcal-replay-start-wait-all-set",
                replay_script,
                timeout=args.replay_start_timeout,
                allow_error=True,
            )
            replay_clean = remote_step_clean(replay_step)
            result["replay_start"] = {
                "ok": replay_clean,
                "stdout_path": replay_step.get("stdout_path"),
                "remote_tool_result": replay_step.get("remote_tool_result"),
                "remote_script": replay_script,
            }
            if not replay_clean:
                raise RuntimeError(f"ACDB SET-cal replay did not reach final SET marker: {replay_step.get('remote_tool_result')}")
            post_set_dmesg_step = run_remote_shell(
                args,
                out_dir,
                steps,
                "dmesg-after-setcal-replay-before-pcm",
                f"dmesg | tail -n {DMESG_TAIL_LINE_COUNT}",
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["post_set_dmesg"] = {
                "ok": bool(post_set_dmesg_step.get("ok")),
                "stdout_path": post_set_dmesg_step.get("stdout_path"),
            }
            helper_started = True
            result["helper_started"] = True
            result["playback_attempted"] = True
            playback = route.get("playback") or {}
            playback_step = speaker.run_tool_command(
                args,
                out_dir,
                steps,
                playback.get("name", "pcm-probe-after-setcal-replay"),
                [str(part) for part in playback.get("argv") or []],
                use_tcpctl=use_tcpctl,
                timeout=args.playback_timeout,
                allow_error=True,
                failure_markers=("Error playing sample", "A90_PCM_PROBE_WRITE_ERROR", "A90_PCM_PROBE_PCM_OPEN_ERROR"),
            )
            result["playback"] = {"ok": bool(playback_step.get("ok")), "stdout_path": playback_step.get("stdout_path"), "remote_tool_result": playback_step.get("remote_tool_result")}
            if not playback_step.get("ok"):
                raise RuntimeError(f"PCM probe failed: {playback_step.get('remote_tool_result')}")
        except Exception as exc:  # noqa: BLE001
            deferred_error = exc
            if result.get("playback_attempted"):
                dmesg_step = run_remote_shell(args, out_dir, steps, "dmesg-after-setcal-playback-failure-before-reset", f"dmesg | tail -n {DMESG_TAIL_LINE_COUNT}", timeout=args.mixer_timeout, allow_error=True)
                result["playback_failure_dmesg"] = {"ok": bool(dmesg_step.get("ok")), "stdout_path": dmesg_step.get("stdout_path")}
    finally:
        if helper_started:
            cleanup_script = install["scripts"]["deallocate_check"]["remote_path"]
            cleanup = run_remote_script(
                args,
                out_dir,
                steps,
                "acdb-setcal-helper-deallocate-check",
                cleanup_script,
                timeout=args.hold_sec + 45,
                allow_error=True,
            )
            cleanup_clean = remote_step_clean(cleanup)
            result["helper_cleanup"] = {
                "ok": cleanup_clean,
                "stdout_path": cleanup.get("stdout_path"),
                "remote_tool_result": cleanup.get("remote_tool_result"),
                "remote_script": cleanup_script,
            }
            if not cleanup_clean and deferred_error is None:
                deferred_error = RuntimeError(f"ACDB SET-cal helper cleanup/deallocate failed: {cleanup.get('remote_tool_result')}")
        for command in route.get("route_reset_commands") or []:
            step = speaker.run_tool_command(
                args,
                out_dir,
                steps,
                command["name"],
                [str(part) for part in command["argv"]],
                use_tcpctl=route_use_tcpctl,
                timeout=args.mixer_timeout,
                allow_error=True,
                failure_markers=("Invalid mixer control",),
            )
            result["route_reset"].append({"name": command["name"], "ok": bool(step.get("ok")), "stdout_path": step.get("stdout_path"), "remote_tool_result": step.get("remote_tool_result")})
        post_reset_step = speaker.run_tool_command(
            args,
            out_dir,
            steps,
            "tinymix-all-values-after-setcal-reset",
            [plan["remote_tinymix"], "-D", str(args.card), "--all-values"],
            use_tcpctl=use_tcpctl,
            timeout=args.mixer_timeout,
            allow_error=True,
        )
        result["post_reset_snapshot"] = {"ok": bool(post_reset_step.get("ok")), "stdout_path": post_reset_step.get("stdout_path")}
        runtime_cleanup_script = install["scripts"]["runtime_cleanup"]["remote_path"]
        runtime_cleanup = run_remote_script(args, out_dir, steps, "runtime-dir-cleanup-after-setcal-reset", runtime_cleanup_script, timeout=args.mixer_timeout, allow_error=True)
        result["runtime_cleanup"] = {
            "ok": remote_step_clean(runtime_cleanup),
            "stdout_path": runtime_cleanup.get("stdout_path"),
            "remote_tool_result": runtime_cleanup.get("remote_tool_result"),
            "remote_script": runtime_cleanup_script,
        }
    if baseline_step and baseline_step.get("ok") and post_reset_step and post_reset_step.get("ok"):
        result["route_reset_verification"] = speaker.route_reset_verification(
            speaker.step_text(baseline_step), speaker.step_text(post_reset_step), route.get("route_reset_commands") or []
        )
        if not result["route_reset_verification"].get("ok") and deferred_error is None:
            deferred_error = RuntimeError("route reset verification failed")
    if not all(item.get("ok") for item in result["route_reset"]) and deferred_error is None:
        deferred_error = RuntimeError("one or more route reset commands failed")
    if deferred_error is not None:
        result["blocked_error_type"] = type(deferred_error).__name__
        result["blocked_error"] = str(deferred_error)
        raise speaker.SpeakerPilotBlocked(str(deferred_error), result) from deferred_error
    return result


def live_run(args: argparse.Namespace, state: dict[str, Any], deploy_manifest: dict[str, Any]) -> dict[str, Any]:
    verify_live_gate(args, deploy_manifest)
    if not state.get("execution_contract_ok"):
        raise SystemExit("refusing live run: V2639 execution contract is not verified")
    out_dir = DEFAULT_OUT_BASE / f"v2639-acdb-setcal-replay-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": "v2639-acdb-setcal-replay-live-started",
        "out_dir": rel(out_dir),
        "preflight": state,
        "steps": steps,
        "rolled_back": False,
    }
    write_json(out_dir / "preflight.json", state)
    candidate_flashed = False
    try:
        speaker.run_host_step(out_dir, steps, "preflight-current-v2321-verify", snd.flash_command(snd.ROLLBACK_IMAGE, snd.ROLLBACK_VERSION, snd.ROLLBACK_SHA256, from_native=False) + ["--verify-only"], timeout=args.flash_timeout)
        run_selftest_fail0(args, out_dir, steps, "preflight-current-selftest")
        speaker.run_host_step(out_dir, steps, "flash-v2334-candidate", snd.flash_command(snd.CANDIDATE_IMAGE, snd.CANDIDATE_VERSION, snd.CANDIDATE_SHA256, from_native=True), timeout=args.flash_timeout)
        candidate_flashed = True
        version = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-version", ["version"], timeout=90.0)
        if snd.CANDIDATE_VERSION not in stdout_of(version):
            raise RuntimeError("candidate version output did not contain expected version")
        snd.run_a90ctl_observation(args, out_dir, steps, "candidate-status", ["status"], timeout=90.0)
        run_selftest_fail0(args, out_dir, steps, "candidate-selftest")
        pre_adsp = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-audio-adsp-status-before", ["audio", "adsp-status"], timeout=90.0)
        pre_snd = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-audio-snd-status-before", ["audio", "snd-status"], timeout=90.0)
        result["initial_audio"] = snd.classify_audio_status(stdout_of(pre_adsp) + "\n" + stdout_of(pre_snd))
        if not (result["initial_audio"]["has_audio_card"] and result["initial_audio"]["has_sound_class_control"]):
            snd.run_menu_settle_step(out_dir, steps, "settle-before-adsp-boot-once", args)
            adsp_boot_step = snd.run_serial_transport_step(out_dir, steps, "candidate-adsp-boot-once", args, ["audio", "adsp-boot-once", snd.ADSP_TOKEN], timeout=90.0, retry_observation=False, allow_error=True)
            result["adsp_boot_once"] = speaker.classify_adsp_boot_once_step(adsp_boot_step)
            if not result["adsp_boot_once"].get("accepted"):
                raise RuntimeError(f"candidate ADSP boot-once did not show accepted marker: {result['adsp_boot_once']}")
        result["card_wait"] = snd.wait_for_audio_card(args, out_dir, steps)
        snd.run_menu_settle_step(out_dir, steps, "settle-before-snd-materialize-once", args)
        materialize = snd.run_serial_transport_step(out_dir, steps, "snd-materialize-once", args, ["audio", "snd-materialize-once", snd.SND_TOKEN], timeout=90.0, retry_observation=False)
        result["materialize_tail"] = stdout_of(materialize)[-4000:]
        after_materialize = snd.run_a90ctl_observation(args, out_dir, steps, "snd-status-after-materialize", ["audio", "snd-status"], timeout=90.0)
        after = snd.classify_audio_status(stdout_of(after_materialize))
        result["after_materialize"] = after
        if not (after["has_dev_snd_control"] and after["has_dev_snd_pcm"]):
            raise RuntimeError("materialization did not produce control+pcm /dev/snd nodes")
        try:
            result["acdb_setcal_replay"] = run_setcal_replay_and_pcm(args, out_dir, steps, state, deploy_manifest)
        except speaker.SpeakerPilotBlocked as exc:
            result["acdb_setcal_replay"] = exc.partial_result
            raise
        run_selftest_fail0(args, out_dir, steps, "candidate-selftest-after-setcal-replay")
        result["decision"] = "v2639-acdb-setcal-replay-live-pass-before-rollback"
    except Exception as exc:  # noqa: BLE001
        result["decision"] = "v2639-acdb-setcal-replay-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        raise
    finally:
        if candidate_flashed:
            rollback_record = speaker.run_host_step(out_dir, steps, "rollback-v2321", snd.flash_command(snd.ROLLBACK_IMAGE, snd.ROLLBACK_VERSION, snd.ROLLBACK_SHA256, from_native=True), timeout=args.flash_timeout, allow_error=True)
            result["rolled_back"] = bool(rollback_record.get("ok"))
            try:
                rollback_version = snd.run_a90ctl_observation(args, out_dir, steps, "rollback-version", ["version"], timeout=90.0)
                rollback_selftest = run_selftest_fail0(args, out_dir, steps, "rollback-selftest")
                result["rollback_version_ok"] = snd.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = snd.selftest_ok(stdout_of(rollback_selftest))
            except Exception as exc:  # noqa: BLE001
                result["rollback_health_error"] = str(exc)
        write_json(out_dir / "result.json", result)
    return result


def write_report(path: Path, state: dict[str, Any]) -> None:
    lines = [
        "# NATIVE_INIT V2639 — ACDB SET-cal replay live handoff",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Checked live handoff for native replay of the V2636 SET-cal manifest.",
        "Default validation is host-only. Live mode is self-authorized under the",
        "recoverable envelope and is gated by deployment integrity plus the",
        "operational invariants: one-shot exact SET args, bounded PCM probe,",
        "reverse-deallocate cleanup, dmesg instrumentation, and rollback to V2321.",
        "",
        "## Result",
        "",
        f"- decision: `{state.get('decision')}`",
        f"- execution_contract_ok: `{state.get('execution_contract_ok')}`",
        f"- safe_to_run_native_replay: `{state.get('safe_to_run_native_replay')}`",
        f"- live_runner_implemented: `{state.get('live_runner_implemented')}`",
        f"- manifest_path: `{state.get('manifest_path')}`",
        "",
        "## Gate Blockers",
        "",
    ]
    for blocker in state.get("replay_gate_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py tests/test_native_audio_acdb_setcal_replay_live_handoff_v2639.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_handoff_v2639 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --dry-run --write-report`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_handoff_v2639.py --run-live` deployment-integrity gate check",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run-live", action="store_true")
    parser.add_argument("--approval", default="")
    parser.add_argument("--operator-gate2-accepted", action="store_true")
    parser.add_argument("--v2636-manifest", type=Path, default=planmod.DEFAULT_V2636_MANIFEST)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=snd.ROOT / "docs/reports/NATIVE_INIT_V2639_AUDIO_ACDB_SETCAL_REPLAY_LIVE_HANDOFF_2026-06-18.md")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--hold-sec", type=int, default=10)
    parser.add_argument("--replay-start-timeout", type=float, default=60.0)
    parser.add_argument("--tinyalsa-manifest", type=Path, default=speaker.inv.MANIFEST)
    parser.add_argument("--pcm-probe-manifest", type=Path, default=speaker.pcm_probe.DEFAULT_MANIFEST)
    parser.add_argument("--evidence-dir", type=Path, default=speaker.recipe.DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--host-ip", default="192.168.7.1")
    parser.add_argument("--host-prefix", type=int, default=24)
    parser.add_argument("--tcp-port", type=int, default=2325)
    parser.add_argument("--command-timeout", type=float, default=60.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--device-toolbox", default=speaker.DEFAULT_DEVICE_TOOLBOX)
    parser.add_argument("--device-busybox", default=speaker.DEFAULT_DEVICE_BUSYBOX)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--card-timeout", type=float, default=70.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--menu-settle-sec", type=float, default=1.0)
    parser.add_argument("--transfer-port", type=int, default=18280)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--repair-host-ncm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ncm-setup-timeout", type=float, default=120.0)
    parser.add_argument("--ncm-interface-timeout", type=float, default=20.0)
    parser.add_argument("--ncm-setup-sudo", default="sudo -n")
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--card", type=int, default=0)
    parser.add_argument("--route-transport", choices=("serial", "tcpctl"), default="serial")
    parser.add_argument("--mixer-timeout", type=float, default=45.0)
    parser.add_argument("--playback-timeout", type=float, default=25.0)
    parser.add_argument("--duration-ms", type=int, default=speaker.DEFAULT_DURATION_MS)
    parser.add_argument("--amplitude", type=float, default=speaker.DEFAULT_AMPLITUDE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    deploy_manifest = load_deploy_manifest(args.v2636_manifest)
    state = dry_run_payload(args)
    write_private_json(args.manifest_path, state)
    if args.write_report:
        write_report(args.report, state)
    if args.dry_run:
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if state.get("execution_contract_ok") else 2
    result = live_run(args, copy.deepcopy(state), deploy_manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("decision") == "v2639-acdb-setcal-replay-live-pass-before-rollback" else 1


if __name__ == "__main__":
    raise SystemExit(main())
