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
import math
import shlex
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_setcal_replay_live_gate_v2637 as v2637
import native_audio_acdb_setcal_replay_live_runner_plan_v2638 as planmod
import native_audio_acdb_topology_replay_live_handoff_v2552 as topology_live
import native_audio_speaker_pilot_live_handoff_v2379 as speaker
import native_audio_speaker_profiles_v2749 as audio_profiles
import native_audio_snd_nodes_preflight_handoff_v2335 as snd
import build_audio_app_type_config_writer_v2733 as appcfg_writer

RUN_ID = "V2639"
BUILD_TAG = "v2639-audio-acdb-setcal-replay-live-handoff"
DEFAULT_MANIFEST = snd.ROOT / "workspace/private/builds/audio" / BUILD_TAG / "manifest.json"
DEFAULT_OUT_BASE = snd.ROOT / "workspace/private/runs/audio"
APPROVAL_PHRASE = v2637.APPROVAL_PHRASE
DEFAULT_AUDIO_PROFILE_ID = audio_profiles.INTERNAL_SPEAKER_SAFE.profile_id
DEFAULT_AUDIO_PROFILE = audio_profiles.get_profile(DEFAULT_AUDIO_PROFILE_ID)
DMESG_TAIL_LINE_COUNT = 260
GLOBAL_APP_TYPE_CONTROL_NAME = "App Type Config"
GLOBAL_APP_TYPE_SPEAKER_TUPLE = DEFAULT_AUDIO_PROFILE.global_app_type_values()
GLOBAL_APP_TYPE_WRITER_ENTRY = DEFAULT_AUDIO_PROFILE.global_app_type_entry()
REMOTE_APP_TYPE_WRITER = f"{speaker.REMOTE_DIR}/a90_alsa_app_type_config_writer_v2733"
REMOTE_OUTPUT_OBSERVER_SCRIPT = f"{speaker.REMOTE_DIR}/a90_pcm_output_observer_v2741.sh"
REMOTE_LISTEN_WINDOW_SCRIPT = f"{speaker.REMOTE_DIR}/a90_pcm_listen_window_v2743.sh"
DMESG_FOCUS_PATTERN = DEFAULT_AUDIO_PROFILE.dmesg_focus_pattern()
MIXER_OUTPUT_FOCUS_PATTERN = DEFAULT_AUDIO_PROFILE.mixer_focus_pattern()
OUTPUT_OBSERVER_THERMAL_PATTERN = "wsa|spkr|speaker|audio|wcd|tavil|pa"
LISTEN_TEST_DEFAULT_AMPLITUDE = DEFAULT_AUDIO_PROFILE.listen_limits.default_amplitude
LISTEN_TEST_MAX_AMPLITUDE = DEFAULT_AUDIO_PROFILE.listen_limits.max_amplitude
LISTEN_TEST_DEFAULT_DURATION_MS = DEFAULT_AUDIO_PROFILE.listen_limits.default_duration_ms
LISTEN_TEST_MAX_DURATION_MS = DEFAULT_AUDIO_PROFILE.listen_limits.max_duration_ms
LISTEN_TEST_DEFAULT_COUNTDOWN_SEC = 5
LISTEN_TEST_MAX_COUNTDOWN_SEC = 10
OUTPUT_OBSERVER_DIRECT_CONTROLS = DEFAULT_AUDIO_PROFILE.output_observer_controls


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


def selected_audio_profile(args: argparse.Namespace) -> audio_profiles.AudioSpeakerProfile:
    return audio_profiles.get_profile(getattr(args, "audio_profile", DEFAULT_AUDIO_PROFILE_ID))


def verify_live_gate(args: argparse.Namespace, deploy_manifest: dict[str, Any]) -> None:
    v2637.verify_live_gate(
        args.approval,
        operator_gate2_accepted=args.operator_gate2_accepted,
        deploy_manifest=deploy_manifest,
    )


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    plan = planmod.build_runner_plan(args)
    profile = selected_audio_profile(args)
    payload = copy.deepcopy(plan)
    future_sequence = list(payload.get("future_live_sequence") or [])
    future_sequence = [
        (
            "write global App Type Config atomically as 1 69941 48000 16, then apply V2407 stream App Type and V2377 route controls"
            if step == "apply V2407 App Type and V2377 route controls"
            else step
        )
        for step in future_sequence
    ]
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
            "future_live_sequence": future_sequence,
            "v2730_global_app_type_config": global_app_type_plan(args),
            "v2733_atomic_app_type_writer": {
                "enabled": bool(getattr(args, "use_atomic_app_type_writer", True)),
                "manifest": rel(getattr(args, "app_type_writer_manifest", appcfg_writer.DEFAULT_MANIFEST)),
                "remote_path": REMOTE_APP_TYPE_WRITER,
                "reason": "avoid tinymix per-index integer writes on write-only multi-value App Type Config",
            },
            "v2730_dmesg_focus_pattern": DMESG_FOCUS_PATTERN,
            "v2737_mixer_output_focus_pattern": MIXER_OUTPUT_FOCUS_PATTERN,
            "v2739_output_observer": output_observer_plan(args),
            "v2741_output_observer": output_observer_plan(args),
            "v2743_listening_test": listening_test_plan(args),
            "v2749_audio_speaker_profile": profile.manifest(),
        }
    )
    paths = dict(payload.get("remote_script_paths") or {})
    scripts = dict(payload.get("remote_scripts") or {})
    paths["pcm_output_observer"] = REMOTE_OUTPUT_OBSERVER_SCRIPT
    scripts["pcm_output_observer"] = output_observer_script(args)
    paths["listen_window"] = REMOTE_LISTEN_WINDOW_SCRIPT
    scripts["listen_window"] = listen_window_script(args)
    payload["remote_script_paths"] = paths
    payload["remote_scripts"] = scripts
    return payload


def run_a90ctl_hard_observation(args: argparse.Namespace,
                                out_dir: Path,
                                steps: list[dict[str, Any]],
                                name: str,
                                native_command: list[str],
                                *,
                                timeout: float = 120.0,
                                allow_error: bool = False) -> dict[str, Any]:
    """Run observation commands through a subprocess-level timeout.

    V2746 exposed a live-runner hang where the in-process serial observation
    path held the serial transaction lock after the candidate-version step.
    Observation commands are read-only, so use the a90ctl subprocess wrapper and
    let subprocess.run enforce a hard timeout that releases the child process.
    """

    command = [
        "python3",
        snd.rel(snd.A90CTL),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(timeout),
        "--hide-on-busy",
        *native_command,
    ]
    step = speaker.run_host_step(
        out_dir,
        steps,
        name,
        command,
        timeout=timeout + 10.0,
        allow_error=allow_error,
    )
    if not bool(step.get("ok")) and not allow_error:
        raise RuntimeError(f"observation command failed: {name}: {step.get('stdout_tail')}")
    return step


def run_selftest_fail0(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    last_step: dict[str, Any] | None = None
    for attempt in range(1, 4):
        step = run_a90ctl_hard_observation(
            args,
            out_dir,
            steps,
            f"{name}-content-attempt-{attempt}",
            ["selftest", "verbose"],
            timeout=120.0,
            allow_error=True,
        )
        last_step = step
        if snd.selftest_ok(stdout_of(step)):
            step["ok"] = True
            return step
        time.sleep(1.0)
    raise RuntimeError(f"{name} did not report fail=0 after content retries: {last_step.get('stdout_path') if last_step else 'no-step'}")


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


def app_type_writer_path(args: argparse.Namespace) -> Path:
    manifest_path = Path(getattr(args, "app_type_writer_manifest", appcfg_writer.DEFAULT_MANIFEST))
    if not manifest_path.is_absolute():
        manifest_path = snd.ROOT / manifest_path
    if not manifest_path.exists():
        raise RuntimeError(f"missing V2733 App Type Config writer manifest: {rel(manifest_path)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tool = (manifest.get("build") or {}).get("tools", {}).get(appcfg_writer.TOOL_NAME, {})
    path_value = tool.get("path")
    if not path_value:
        raise RuntimeError(f"V2733 writer manifest lacks tool path: {rel(manifest_path)}")
    path = Path(str(path_value))
    return path if path.is_absolute() else snd.ROOT / path


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
    if bool(getattr(args, "set_global_app_type_config", True)) and bool(getattr(args, "use_atomic_app_type_writer", True)):
        extra.append(("app_type_writer", app_type_writer_path(args), REMOTE_APP_TYPE_WRITER, port + 43))
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
    script_keys = ["start_and_wait_all_set"]
    if "listen_window" in paths:
        script_keys.append("listen_window")
    script_keys.extend(["pcm_output_observer", "deallocate_check", "runtime_cleanup"])
    for script_key in script_keys:
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


def global_app_type_plan(args: argparse.Namespace) -> dict[str, Any]:
    enabled = bool(getattr(args, "set_global_app_type_config", True))
    use_atomic = bool(getattr(args, "use_atomic_app_type_writer", True))
    profile = selected_audio_profile(args)
    values = profile.global_app_type_values()
    tool = REMOTE_APP_TYPE_WRITER if use_atomic else speaker.REMOTE_TINYMIX
    argv = (
        [
            tool,
            "--card",
            str(args.card),
            "--control",
            GLOBAL_APP_TYPE_CONTROL_NAME,
            "--entry",
            profile.global_app_type_entry(),
        ]
        if use_atomic
        else [
            tool,
            "-D",
            str(args.card),
            GLOBAL_APP_TYPE_CONTROL_NAME,
            *values,
        ]
    )
    return {
        "enabled": enabled,
        "name": "v2733-atomic-app-type-config" if use_atomic else "v2730-global-app-type-config",
        "profile_id": profile.profile_id,
        "role": "global_app_type_cfg_gate",
        "source": "V2732 write-semantics recon",
        "control": GLOBAL_APP_TYPE_CONTROL_NAME,
        "values": list(values),
        "entry": profile.global_app_type_entry(),
        "writer": "atomic-alsa-elem-write" if use_atomic else "tinymix-per-index-compat",
        "argv": argv,
        "expected_effect": "adm_open bit_width 0->16 and no app-type fallback for app_type 0x11135",
        "transport": "serial-cmdv1x",
    }


def focused_dmesg_script() -> str:
    return f"dmesg | grep -iE {shlex.quote(DMESG_FOCUS_PATTERN)} || true"


def focused_tinymix_script(remote_tinymix: str, card: int) -> str:
    return (
        f"{shlex.quote(remote_tinymix)} -D {int(card)} --all-values "
        f"| grep -iE {shlex.quote(MIXER_OUTPUT_FOCUS_PATTERN)} || true"
    )


def effective_audio_params(args: argparse.Namespace) -> dict[str, Any]:
    profile = selected_audio_profile(args)
    listen_test = bool(getattr(args, "listen_test", False))
    mode: audio_profiles.AudioMode = "listen" if listen_test else "probe"
    limits = profile.limits_for_mode(mode)
    amplitude = float(getattr(args, "amplitude", speaker.DEFAULT_AMPLITUDE))
    duration_ms = int(getattr(args, "duration_ms", speaker.DEFAULT_DURATION_MS))
    if listen_test and amplitude == speaker.DEFAULT_AMPLITUDE:
        amplitude = limits.default_amplitude
    if listen_test and duration_ms == speaker.DEFAULT_DURATION_MS:
        duration_ms = limits.default_duration_ms
    profile.validate_playback(mode=mode, amplitude=amplitude, duration_ms=duration_ms)
    return {
        "profile_id": profile.profile_id,
        "listen_test": listen_test,
        "amplitude": amplitude,
        "duration_ms": duration_ms,
        "max_amplitude": limits.max_amplitude,
        "max_duration_ms": limits.max_duration_ms,
    }


def generate_acdb_pilot_wav(path: Path, *, duration_ms: int, amplitude: float) -> dict[str, Any]:
    frame_count = speaker.SAMPLE_RATE * duration_ms // 1000
    frequency = 440.0
    max_i16 = 32767
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(speaker.SAMPLE_RATE)
        for frame in range(frame_count):
            value = int(max_i16 * amplitude * math.sin(2.0 * math.pi * frequency * frame / speaker.SAMPLE_RATE))
            sample = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(sample + sample)
    return {
        "path": rel(path),
        "duration_ms": duration_ms,
        "amplitude": amplitude,
        "sample_rate": speaker.SAMPLE_RATE,
        "channels": 2,
        "sample_width_bytes": 2,
        "frames": frame_count,
        "sha256": speaker.recipe.sha256_file(path),
    }


def listening_test_plan(args: argparse.Namespace) -> dict[str, Any]:
    params = effective_audio_params(args)
    countdown_sec = effective_listen_countdown_sec(args)
    profile = selected_audio_profile(args)
    return {
        "enabled": bool(getattr(args, "listen_test", False)),
        "name": "v2743-human-audible-listen-window",
        "profile_id": profile.profile_id,
        "endpoint": profile.endpoint,
        "remote_script": REMOTE_LISTEN_WINDOW_SCRIPT,
        "amplitude": params["amplitude"],
        "duration_ms": params["duration_ms"],
        "max_amplitude": params["max_amplitude"],
        "max_duration_ms": params["max_duration_ms"],
        "host_countdown_sec": countdown_sec,
        "markers": ["A90_LISTEN_WINDOW_BEGIN", "A90_LISTEN_WINDOW_END"],
        "safety": list(profile.safety_notes),
    }


def effective_listen_countdown_sec(args: argparse.Namespace) -> int:
    countdown_sec = int(getattr(args, "listen_countdown_sec", LISTEN_TEST_DEFAULT_COUNTDOWN_SEC))
    if countdown_sec < 0 or countdown_sec > LISTEN_TEST_MAX_COUNTDOWN_SEC:
        raise ValueError(f"listen_countdown_sec out of bound: {countdown_sec}")
    return countdown_sec


def run_listen_countdown(args: argparse.Namespace, *, out_dir: Path) -> None:
    if not bool(getattr(args, "listen_test", False)):
        return
    countdown_sec = effective_listen_countdown_sec(args)
    marker = {
        "event": "A90_HOST_LISTEN_WINDOW_COUNTDOWN",
        "countdown_sec": countdown_sec,
        "run_dir": rel(out_dir),
    }
    print(json.dumps(marker, sort_keys=True), flush=True)
    if countdown_sec:
        time.sleep(countdown_sec)
    print(json.dumps({"event": "A90_HOST_LISTEN_WINDOW_STARTING_NOW", "run_dir": rel(out_dir)}, sort_keys=True), flush=True)


def listen_window_script(args: argparse.Namespace) -> str:
    params = effective_audio_params(args)
    card = int(getattr(args, "card", 0))
    device = int(getattr(args, "pcm_device", 0))
    lines = [
        "set -u",
        f"pcm_probe={shlex.quote(speaker.REMOTE_PCM_PROBE)}",
        f"pcm_file={shlex.quote(speaker.REMOTE_PCM)}",
        f"card={card}",
        f"device={device}",
        f"amplitude={params['amplitude']}",
        f"duration_ms={params['duration_ms']}",
        "echo A90_LISTEN_WINDOW_READY amplitude=$amplitude duration_ms=$duration_ms card=$card device=$device",
        "echo A90_LISTEN_WINDOW_BEGIN amplitude=$amplitude duration_ms=$duration_ms",
        '"$pcm_probe" "$pcm_file" -D "$card" -d "$device"',
        "pcm_rc=$?",
        "echo A90_LISTEN_WINDOW_END rc=$pcm_rc",
        "exit $pcm_rc",
    ]
    return "\n".join(lines)


def output_observer_plan(args: argparse.Namespace) -> dict[str, Any]:
    profile = selected_audio_profile(args)
    return {
        "enabled": bool(getattr(args, "output_observer", True)),
        "name": "v2741-direct-output-observer",
        "profile_id": profile.profile_id,
        "endpoint": profile.endpoint,
        "role": "read-only dynamic output-side sampler during bounded PCM probe",
        "remote_script": REMOTE_OUTPUT_OBSERVER_SCRIPT,
        "sample_count": int(getattr(args, "output_observer_samples", 12)),
        "sample_sleep_sec": str(getattr(args, "output_observer_sleep", "0.10")),
        "sampling_mode": "direct-control-allowlist",
        "direct_controls": list(profile.output_observer_controls),
        "thermal_pattern": OUTPUT_OBSERVER_THERMAL_PATTERN,
        "non_goal": "does not change WSA gain/boost/protection controls",
    }


def output_observer_script(args: argparse.Namespace) -> str:
    sample_count = max(1, int(getattr(args, "output_observer_samples", 12)))
    sample_sleep = str(getattr(args, "output_observer_sleep", "0.10"))
    card = int(getattr(args, "card", 0))
    device = int(getattr(args, "pcm_device", 0))
    runtime_dir = f"{speaker.REMOTE_DIR}/v2741-output-observer"
    lines = [
        "set -u",
        f"tinymix={shlex.quote(speaker.REMOTE_TINYMIX)}",
        f"pcm_probe={shlex.quote(speaker.REMOTE_PCM_PROBE)}",
        f"pcm_file={shlex.quote(speaker.REMOTE_PCM)}",
        f"card={card}",
        f"device={device}",
        f"sample_count={sample_count}",
        f"sample_sleep={shlex.quote(sample_sleep)}",
        f"runtime_dir={shlex.quote(runtime_dir)}",
        "rm -rf \"$runtime_dir\"",
        "mkdir -p \"$runtime_dir\"",
        "samples=\"$runtime_dir/samples.txt\"",
        "stop=\"$runtime_dir/stop\"",
        "read_ctl() {",
        "  idx=\"$1\"",
        "  label=\"$2\"",
        "  name=\"$3\"",
        "  out=\"$runtime_dir/ctl-${idx}-${label}.txt\"",
        "  \"$tinymix\" -D \"$card\" \"$name\" >\"$out\" 2>&1",
        "  rc=$?",
        "  echo A90_OUTPUT_OBSERVER_CTL_BEGIN index=$idx label=$label rc=$rc name=$name",
        "  while IFS= read -r line; do",
        "    echo A90_OUTPUT_OBSERVER_CTL index=$idx label=$label line=$line",
        "  done <\"$out\"",
        "  echo A90_OUTPUT_OBSERVER_CTL_END index=$idx label=$label rc=$rc",
        "}",
        "sample_once() {",
        "  idx=\"$1\"",
        "  ts=$(date +%s 2>/dev/null || echo 0)",
        "  echo A90_OUTPUT_OBSERVER_SAMPLE_BEGIN index=$idx ts=$ts",
    ]
    for index, control in enumerate(OUTPUT_OBSERVER_DIRECT_CONTROLS):
        label = f"c{index:02d}"
        lines.append(f"  read_ctl \"$idx\" {shlex.quote(label)} {shlex.quote(control)}")
    lines.extend([
        "  for zone in /sys/class/thermal/thermal_zone*; do",
        "    [ -r \"$zone/type\" ] || continue",
        "    ztype=$(cat \"$zone/type\" 2>/dev/null || true)",
        "    case \"$ztype\" in",
        "      *[Ww][Ss][Aa]*|*[Ss][Pp][Kk][Rr]*|*[Ss][Pp][Ee][Aa][Kk][Ee][Rr]*|*[Aa][Uu][Dd][Ii][Oo]*|*[Ww][Cc][Dd]*|*[Tt][Aa][Vv][Ii][Ll]*|*[Pp][Aa]*)",
        "        ztemp=$(cat \"$zone/temp\" 2>/dev/null || true)",
        "        echo A90_OUTPUT_OBSERVER_THERMAL index=$idx zone=${zone##*/} type=$ztype temp=$ztemp",
        "        ;;",
        "    esac",
        "  done",
        "  echo A90_OUTPUT_OBSERVER_SAMPLE_END index=$idx",
        "}",
        "(",
        "  i=0",
        "  while [ $i -lt $sample_count ]; do",
        "    [ -e \"$stop\" ] && break",
        "    sample_once \"$i\"",
        "    i=$((i+1))",
        "    sleep \"$sample_sleep\" 2>/dev/null || sleep 1",
        "  done",
        ") >\"$samples\" 2>&1 &",
        "sampler_pid=$!",
        "echo A90_OUTPUT_OBSERVER_BEGIN mode=direct-controls samples=$sample_count sleep=$sample_sleep controls=%d" % len(OUTPUT_OBSERVER_DIRECT_CONTROLS),
        "echo A90_OUTPUT_OBSERVER_PCM_BEGIN",
        "\"$pcm_probe\" \"$pcm_file\" -D \"$card\" -d \"$device\"",
        "pcm_rc=$?",
        "echo A90_OUTPUT_OBSERVER_PCM_END rc=$pcm_rc",
        "touch \"$stop\"",
        "wait $sampler_pid 2>/dev/null || true",
        "echo A90_OUTPUT_OBSERVER_SAMPLES_BEGIN",
        "cat \"$samples\" 2>/dev/null || true",
        "echo A90_OUTPUT_OBSERVER_SAMPLES_END",
        "echo A90_OUTPUT_OBSERVER_DONE rc=$pcm_rc",
        "exit $pcm_rc",
    ])
    return "\n".join(lines)


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
    profile = selected_audio_profile(args)
    return {
        "raw": plan,
        "profile": profile.manifest(),
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
    audio_params = effective_audio_params(args)
    suffix = "listen_48k_s16le_stereo_0p15_8s.wav" if audio_params["listen_test"] else "pilot_48k_s16le_stereo_0p02_1s.wav"
    pcm_path = out_dir / suffix
    pcm = generate_acdb_pilot_wav(
        pcm_path,
        duration_ms=int(audio_params["duration_ms"]),
        amplitude=float(audio_params["amplitude"]),
    )
    result: dict[str, Any] = {
        "pilot_wav": pcm,
        "install": {},
        "global_app_type_config": {"enabled": bool(getattr(args, "set_global_app_type_config", True))},
        "route_apply": [],
        "route_reset": [],
        "playback_attempted": False,
        "helper_started": False,
        "listen_test": listening_test_plan(args),
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
            global_app_type = global_app_type_plan(args)
            if global_app_type["enabled"]:
                step = speaker.run_tool_command(
                    args,
                    out_dir,
                    steps,
                    global_app_type["name"],
                    [str(part) for part in global_app_type["argv"]],
                    use_tcpctl=False,
                    timeout=args.mixer_timeout,
                    allow_error=True,
                    failure_markers=("Invalid mixer control",),
                )
                result["global_app_type_config"] = {
                    "enabled": True,
                    "ok": bool(step.get("ok")),
                    "stdout_path": step.get("stdout_path"),
                    "remote_tool_result": step.get("remote_tool_result"),
                    "control": global_app_type["control"],
                    "values": global_app_type["values"],
                    "writer": global_app_type["writer"],
                }
                if not step.get("ok"):
                    raise RuntimeError(f"global App Type Config gate failed: {step.get('remote_tool_result')}")
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
            post_set_focus_step = run_remote_shell(
                args,
                out_dir,
                steps,
                "dmesg-focus-after-setcal-replay-before-pcm",
                focused_dmesg_script(),
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["post_set_dmesg"] = {
                "ok": bool(post_set_dmesg_step.get("ok")),
                "stdout_path": post_set_dmesg_step.get("stdout_path"),
            }
            result["post_set_dmesg_focus"] = {
                "ok": bool(post_set_focus_step.get("ok")),
                "stdout_path": post_set_focus_step.get("stdout_path"),
                "pattern": DMESG_FOCUS_PATTERN,
            }
            active_snapshot_step = speaker.run_tool_command(
                args,
                out_dir,
                steps,
                "tinymix-all-values-active-before-pcm",
                [plan["remote_tinymix"], "-D", str(args.card), "--all-values"],
                use_tcpctl=use_tcpctl,
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            active_focus_step = run_remote_shell(
                args,
                out_dir,
                steps,
                "tinymix-focus-active-before-pcm",
                focused_tinymix_script(plan["remote_tinymix"], args.card),
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["active_snapshot_before_pcm"] = {
                "ok": bool(active_snapshot_step.get("ok")),
                "stdout_path": active_snapshot_step.get("stdout_path"),
            }
            result["active_focus_before_pcm"] = {
                "ok": bool(active_focus_step.get("ok")),
                "stdout_path": active_focus_step.get("stdout_path"),
                "pattern": MIXER_OUTPUT_FOCUS_PATTERN,
            }
            helper_started = True
            result["helper_started"] = True
            result["playback_attempted"] = True
            playback = route.get("playback") or {}
            if bool(getattr(args, "listen_test", False)):
                run_listen_countdown(args, out_dir=out_dir)
                playback_script = install["scripts"]["listen_window"]["remote_path"]
                playback_step = speaker.run_tool_command(
                    args,
                    out_dir,
                    steps,
                    "listen-window-audible-playback",
                    [args.device_busybox, "sh", playback_script],
                    use_tcpctl=False,
                    timeout=args.playback_timeout,
                    allow_error=True,
                    failure_markers=("Error playing sample", "A90_PCM_PROBE_WRITE_ERROR", "A90_PCM_PROBE_PCM_OPEN_ERROR"),
                )
                result["output_observer"] = {"enabled": False, "reason": "listen-test uses marker-only playback wrapper"}
                result["listen_test"] = {**listening_test_plan(args), "stdout_path": playback_step.get("stdout_path")}
            elif bool(getattr(args, "output_observer", True)):
                playback_script = install["scripts"]["pcm_output_observer"]["remote_path"]
                playback_step = speaker.run_tool_command(
                    args,
                    out_dir,
                    steps,
                    "pcm-output-observer-during-playback",
                    [args.device_busybox, "sh", playback_script],
                    use_tcpctl=False,
                    timeout=args.playback_timeout,
                    allow_error=True,
                    failure_markers=("Error playing sample", "A90_PCM_PROBE_WRITE_ERROR", "A90_PCM_PROBE_PCM_OPEN_ERROR"),
                )
                result["output_observer"] = {
                    "enabled": True,
                    "stdout_path": playback_step.get("stdout_path"),
                    "remote_script": playback_script,
                    "sample_count": int(getattr(args, "output_observer_samples", 12)),
                    "sample_sleep_sec": str(getattr(args, "output_observer_sleep", "0.10")),
                }
            else:
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
                result["output_observer"] = {"enabled": False}
            result["playback"] = {"ok": bool(playback_step.get("ok")), "stdout_path": playback_step.get("stdout_path"), "remote_tool_result": playback_step.get("remote_tool_result")}
            playback_dmesg_step = run_remote_shell(
                args,
                out_dir,
                steps,
                "dmesg-after-setcal-playback-before-reset",
                f"dmesg | tail -n {DMESG_TAIL_LINE_COUNT}",
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            playback_dmesg_focus_step = run_remote_shell(
                args,
                out_dir,
                steps,
                "dmesg-focus-after-setcal-playback-before-reset",
                focused_dmesg_script(),
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["playback_dmesg"] = {
                "ok": bool(playback_dmesg_step.get("ok")),
                "stdout_path": playback_dmesg_step.get("stdout_path"),
            }
            result["playback_dmesg_focus"] = {
                "ok": bool(playback_dmesg_focus_step.get("ok")),
                "stdout_path": playback_dmesg_focus_step.get("stdout_path"),
                "pattern": DMESG_FOCUS_PATTERN,
            }
            post_playback_snapshot_step = speaker.run_tool_command(
                args,
                out_dir,
                steps,
                "tinymix-all-values-active-after-pcm-before-reset",
                [plan["remote_tinymix"], "-D", str(args.card), "--all-values"],
                use_tcpctl=use_tcpctl,
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            post_playback_focus_step = run_remote_shell(
                args,
                out_dir,
                steps,
                "tinymix-focus-active-after-pcm-before-reset",
                focused_tinymix_script(plan["remote_tinymix"], args.card),
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["active_snapshot_after_pcm_before_reset"] = {
                "ok": bool(post_playback_snapshot_step.get("ok")),
                "stdout_path": post_playback_snapshot_step.get("stdout_path"),
            }
            result["active_focus_after_pcm_before_reset"] = {
                "ok": bool(post_playback_focus_step.get("ok")),
                "stdout_path": post_playback_focus_step.get("stdout_path"),
                "pattern": MIXER_OUTPUT_FOCUS_PATTERN,
            }
            if not playback_step.get("ok"):
                result["playback_failure_dmesg"] = result["playback_dmesg"]
                result["playback_failure_dmesg_focus"] = result["playback_dmesg_focus"]
                raise RuntimeError(f"PCM probe failed: {playback_step.get('remote_tool_result')}")
        except Exception as exc:  # noqa: BLE001
            deferred_error = exc
            if result.get("playback_attempted") and "playback_dmesg" not in result:
                dmesg_step = run_remote_shell(args, out_dir, steps, "dmesg-after-setcal-playback-failure-before-reset", f"dmesg | tail -n {DMESG_TAIL_LINE_COUNT}", timeout=args.mixer_timeout, allow_error=True)
                dmesg_focus_step = run_remote_shell(args, out_dir, steps, "dmesg-focus-after-setcal-playback-failure-before-reset", focused_dmesg_script(), timeout=args.mixer_timeout, allow_error=True)
                result["playback_failure_dmesg"] = {"ok": bool(dmesg_step.get("ok")), "stdout_path": dmesg_step.get("stdout_path")}
                result["playback_failure_dmesg_focus"] = {
                    "ok": bool(dmesg_focus_step.get("ok")),
                    "stdout_path": dmesg_focus_step.get("stdout_path"),
                    "pattern": DMESG_FOCUS_PATTERN,
                }
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
        version = run_a90ctl_hard_observation(args, out_dir, steps, "candidate-version", ["version"], timeout=90.0)
        if snd.CANDIDATE_VERSION not in stdout_of(version):
            raise RuntimeError("candidate version output did not contain expected version")
        run_a90ctl_hard_observation(args, out_dir, steps, "candidate-status", ["status"], timeout=90.0)
        run_selftest_fail0(args, out_dir, steps, "candidate-selftest")
        pre_adsp = run_a90ctl_hard_observation(args, out_dir, steps, "candidate-audio-adsp-status-before", ["audio", "adsp-status"], timeout=90.0)
        pre_snd = run_a90ctl_hard_observation(args, out_dir, steps, "candidate-audio-snd-status-before", ["audio", "snd-status"], timeout=90.0)
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
        after_materialize = run_a90ctl_hard_observation(args, out_dir, steps, "snd-status-after-materialize", ["audio", "snd-status"], timeout=90.0)
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
                rollback_version = run_a90ctl_hard_observation(args, out_dir, steps, "rollback-version", ["version"], timeout=90.0)
                rollback_selftest = run_selftest_fail0(args, out_dir, steps, "rollback-selftest")
                result["rollback_version_ok"] = snd.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = snd.selftest_ok(stdout_of(rollback_selftest))
            except Exception as exc:  # noqa: BLE001
                result["rollback_health_error"] = str(exc)
        write_json(out_dir / "result.json", result)
    return result


def write_report(path: Path, state: dict[str, Any]) -> None:
    lines = [
        "# NATIVE_INIT V2639/V2730 — ACDB SET-cal replay live handoff",
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
        f"- global_app_type_config: `{state.get('v2730_global_app_type_config')}`",
        f"- dmesg_focus_pattern: `{state.get('v2730_dmesg_focus_pattern')}`",
        "",
        "## V2730 Update",
        "",
        "V2730 updates the existing V2639 runner for the current GOAL frontier:",
        "",
        "- writes the global `App Type Config` mixer control via serial before the",
        "  older per-stream `Audio Stream 0 App Type Cfg` and route controls;",
        "- uses the speaker tuple `1 69941 48000 16`, targeting the kernel",
        "  `app_type_cfg[]` table rather than `fe_dai_app_type_cfg[]`;",
        "- V2733 replaces the old `tinymix` write with an atomic ALSA elem writer",
        "  because V2732 showed `tinymix` performs per-index integer writes;",
        "- captures focused dmesg greps for `q6core`, topology-registration,",
        "  `adm_open`, app-type fallback, and `bit_width` before and after the PCM probe;",
        "- keeps the replay manifest, exact SET bytes, bounded PCM probe, reverse",
        "  deallocate cleanup, route reset, and V2321 rollback contract unchanged.",
        "",
        "## Gate Blockers",
        "",
    ]
    for blocker in state.get("replay_gate_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Future Live Sequence",
            "",
        ]
    )
    for step in state.get("future_live_sequence", []):
        lines.append(f"- {step}")
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
    parser.add_argument("--pcm-device", type=int, default=0)
    parser.add_argument("--audio-profile", choices=audio_profiles.list_profiles(), default=DEFAULT_AUDIO_PROFILE_ID)
    parser.add_argument("--duration-ms", type=int, default=speaker.DEFAULT_DURATION_MS)
    parser.add_argument("--amplitude", type=float, default=speaker.DEFAULT_AMPLITUDE)
    parser.add_argument("--listen-test", action="store_true")
    parser.add_argument("--listen-countdown-sec", type=int, default=LISTEN_TEST_DEFAULT_COUNTDOWN_SEC)
    parser.add_argument("--output-observer", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output-observer-samples", type=int, default=12)
    parser.add_argument("--output-observer-sleep", default="0.10")
    parser.add_argument("--set-global-app-type-config", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--use-atomic-app-type-writer", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--app-type-writer-manifest", type=Path, default=appcfg_writer.DEFAULT_MANIFEST)
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
