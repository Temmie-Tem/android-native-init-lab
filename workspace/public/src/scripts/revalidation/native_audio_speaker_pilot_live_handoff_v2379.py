#!/usr/bin/env python3
"""V2379 exact-gated native speaker pilot runner.

Default mode is host-only dry-run.  The live mode is intentionally guarded by the
exact AUD-4 phrase from V2378.  When live, it reuses the proven V2334 ADSP +
/dev/snd materialization path, stages pinned V2345 tinymix/tinyplay plus a
run-local low-amplitude WAV, applies only the V2377-observed speaker route,
runs one bounded tinyplay, reverses the route switches, verifies selftest, and
rolls back to V2321.

This script must not use Magisk, Android framework playback, audio HAL, adsprpc,
raw partition writes, or unbounded speaker output.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import struct
import subprocess
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_snd_nodes_preflight_handoff_v2335 as snd
import native_audio_speaker_route_recipe_v2378 as recipe
import native_audio_tinyalsa_inventory_gate_v2346 as inv
import native_audio_tinyalsa_inventory_live_handoff_v2349 as tiny_live

RUN_ID = "V2379"
BUILD_TAG = "v2379-audio-native-speaker-pilot-runner"
APPROVAL_PHRASE = recipe.FUTURE_APPROVAL_PHRASE
REMOTE_DIR = "/cache/a90-runtime/bin/v2379-speaker-pilot"
REMOTE_TINYMIX = f"{REMOTE_DIR}/tinymix"
REMOTE_TINYPLAY = f"{REMOTE_DIR}/tinyplay"
REMOTE_PCM = f"{REMOTE_DIR}/pilot_48k_s16le_stereo_0p02_1s.wav"
DEFAULT_DEVICE_TOOLBOX = tiny_live.DEFAULT_DEVICE_TOOLBOX
SAMPLE_RATE = 48_000
CHANNELS = 2
SAMPLE_WIDTH_BYTES = 2
MAX_AMPLITUDE = 0.05
MAX_DURATION_MS = 1000
DEFAULT_AMPLITUDE = 0.02
DEFAULT_DURATION_MS = 1000
FORBIDDEN_TOKENS = (
    "fastboot",
    " dd ",
    "/efs",
    "/sec_efs",
    "/dev/block",
    "mixer_paths",
    "settings put",
    "am start",
    "app_process",
    "magisk",
    "su -c",
    "adsprpc",
)


def rel(path: Path) -> str:
    return snd.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def write_json(path: Path, payload: Any) -> None:
    snd.write_json(path, payload)


def stdout_of(step: dict[str, Any]) -> str:
    return snd.stdout_of(step)


def rewrite_remote_argv(argv: list[str]) -> list[str]:
    mapping = {
        recipe.REMOTE_TINYMIX: REMOTE_TINYMIX,
        recipe.REMOTE_TINYPLAY: REMOTE_TINYPLAY,
        recipe.REMOTE_PCM: REMOTE_PCM,
    }
    return [mapping.get(part, part) for part in argv]


def recipe_state(args: argparse.Namespace) -> dict[str, Any]:
    return recipe.dry_run_payload(
        argparse.Namespace(
            dry_run=True,
            evidence_dir=args.evidence_dir,
            duration_ms=args.duration_ms,
            amplitude=args.amplitude,
        )
    )


def speaker_plan(args: argparse.Namespace) -> dict[str, Any]:
    payload = recipe_state(args)
    future = payload.get("future_plan", {})
    apply_commands = copy.deepcopy(future.get("route_apply_commands", []))
    reset_commands = copy.deepcopy(future.get("route_reset_commands", []))
    playback = copy.deepcopy(future.get("playback", {}))
    for command in apply_commands + reset_commands:
        command["argv"] = rewrite_remote_argv([str(part) for part in command.get("argv", [])])
        command["not_executed_by_v2379_dry_run"] = True
    if playback:
        playback["argv"] = rewrite_remote_argv([str(part) for part in playback.get("argv", [])])
        playback["not_executed_by_v2379_dry_run"] = True
    return {
        "recipe": payload,
        "route_apply_commands": apply_commands,
        "route_reset_commands": reset_commands,
        "playback": playback,
    }


def load_raw_tinyalsa_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path), "build": {"tools": {}}}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["exists"] = True
    manifest["path"] = rel(path)
    return manifest


def raw_tool_record(raw_manifest: dict[str, Any], tool: str) -> dict[str, Any]:
    try:
        return raw_manifest["build"]["tools"][tool]
    except KeyError as exc:
        raise RuntimeError(f"missing tinyalsa tool record: {tool}") from exc


def raw_tool_path(raw_manifest: dict[str, Any], tool: str) -> Path:
    return snd.ROOT / str(raw_tool_record(raw_manifest, tool).get("path", ""))


def verify_tool(raw_manifest: dict[str, Any], tool: str, expected_sha256: str) -> dict[str, Any]:
    try:
        record = raw_tool_record(raw_manifest, tool)
    except RuntimeError as exc:
        return {"tool": tool, "ok": False, "reason": str(exc)}
    path = snd.ROOT / str(record.get("path", ""))
    exists = path.exists()
    actual = recipe.sha256_file(path) if exists else ""
    return {
        "tool": tool,
        "path": rel(path),
        "exists": exists,
        "sha256": actual,
        "expected_sha256": expected_sha256,
        "sha256_ok": exists and actual == expected_sha256 == record.get("sha256"),
        "file": record.get("file", ""),
        "file_ok": "ARM aarch64" in str(record.get("file", "")) and "statically linked" in str(record.get("file", "")),
    }


def command_safety(plan: dict[str, Any], *, amplitude: float, duration_ms: int) -> dict[str, Any]:
    findings: list[str] = []
    apply_commands = plan.get("route_apply_commands", [])
    reset_commands = plan.get("route_reset_commands", [])
    playback = plan.get("playback", {})
    if len(apply_commands) != 13:
        findings.append(f"expected 13 route apply commands, got {len(apply_commands)}")
    if len(reset_commands) != 12:
        findings.append(f"expected 12 route reset commands, got {len(reset_commands)}")
    if amplitude <= 0 or amplitude > MAX_AMPLITUDE:
        findings.append(f"amplitude out of bound: {amplitude}")
    if duration_ms <= 0 or duration_ms > MAX_DURATION_MS:
        findings.append(f"duration out of bound: {duration_ms}")
    flat = json.dumps(plan, sort_keys=True)
    for token in FORBIDDEN_TOKENS:
        if token in flat:
            findings.append(f"forbidden token in plan: {token}")
    for command in apply_commands + reset_commands:
        argv = [str(part) for part in command.get("argv", [])]
        if len(argv) < 5 or argv[0] != REMOTE_TINYMIX or argv[1:3] != ["-D", "0"]:
            findings.append(f"invalid tinymix command argv: {argv}")
        if command.get("role") == "observe_only":
            findings.append(f"observe-only control appears in write plan: {command.get('name')}")
    playback_argv = [str(part) for part in playback.get("argv", [])]
    if playback_argv != [REMOTE_TINYPLAY, REMOTE_PCM, "-D", "0", "-d", "0"]:
        findings.append(f"unexpected tinyplay argv: {playback_argv}")
    return {
        "ok": not findings,
        "findings": findings,
        "boundaries": [
            "dry-run performs no device action",
            "live requires the exact AUD-4 phrase",
            "only V2377-observed route controls may be written",
            "one low-amplitude one-second WAV only",
            "reverse reset is mandatory after attempted route application",
            "rollback to V2321 is mandatory after candidate flash",
            "Magisk remains Android-measurement fallback only, not native runtime dependency",
        ],
    }


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    snd_state = snd.preflight_state()
    manifest = inv.verify_manifest(args.manifest)
    raw_manifest = load_raw_tinyalsa_manifest(args.manifest)
    tools = {
        "tinymix": verify_tool(raw_manifest, "tinymix", recipe.EXPECTED_TINYMIX_SHA256),
        "tinyplay": verify_tool(raw_manifest, "tinyplay", recipe.EXPECTED_TINYPLAY_SHA256),
    }
    plan = speaker_plan(args)
    safety = command_safety(plan, amplitude=args.amplitude, duration_ms=args.duration_ms)
    ok = bool(
        snd.preflight_ok(snd_state)
        and manifest.get("ok")
        and plan["recipe"].get("ok")
        and all(item.get("sha256_ok") and item.get("file_ok") for item in tools.values())
        and safety.get("ok")
        and tiny_live.TCPCTL_HOST.exists()
        and tiny_live.NCM_HOST_SETUP.exists()
    )
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "approval_phrase_required": APPROVAL_PHRASE,
        "created_at": now_iso(),
        "snd_materialization_preflight": snd_state,
        "tinyalsa_manifest": manifest,
        "tinyalsa_raw_manifest": {
            "exists": raw_manifest.get("exists", False),
            "path": raw_manifest.get("path", rel(args.manifest)),
            "source_commit": raw_manifest.get("source", {}).get("commit", ""),
            "tool_names": sorted(raw_manifest.get("build", {}).get("tools", {}).keys()),
        },
        "tools": tools,
        "speaker_plan": plan,
        "command_safety": safety,
        "remote_dir": REMOTE_DIR,
        "remote_tools": {"tinymix": REMOTE_TINYMIX, "tinyplay": REMOTE_TINYPLAY},
        "remote_pcm": REMOTE_PCM,
        "ok": ok,
    }


def dry_run_install_plan(args: argparse.Namespace, state: dict[str, Any]) -> list[dict[str, Any]]:
    install_steps: list[dict[str, Any]] = []
    if state.get("tinyalsa_manifest", {}).get("ok"):
        for index, tool in enumerate(("tinymix", "tinyplay"), start=0):
            raw_manifest = load_raw_tinyalsa_manifest(args.manifest)
            local_path = raw_tool_path(raw_manifest, tool)
            target_path = REMOTE_TINYMIX if tool == "tinymix" else REMOTE_TINYPLAY
            install_steps.append({
                "artifact": tool,
                "auto_select": {
                    "tcpctl": tiny_live.install_command(args, local_path, target_path, args.transfer_port + index, control_channel="tcpctl"),
                    "serial": tiny_live.install_command(args, local_path, target_path, args.transfer_port + index, control_channel="bridge"),
                },
            })
    install_steps.append({
        "artifact": "pilot_wav_generated_runtime",
        "local_path": "workspace/private/runs/audio/<run>/pilot_48k_s16le_stereo_0p02_1s.wav",
        "remote_path": REMOTE_PCM,
        "auto_select": {
            "tcpctl": [*tiny_live.tcpctl_common(args, target_binary=REMOTE_PCM), "install", "--install-control-channel", "tcpctl", "--local-binary", "<generated-pcm>", "--transfer-port", str(args.transfer_port + 2)],
            "serial": [*tiny_live.tcpctl_common(args, target_binary=REMOTE_PCM), "install", "--install-control-channel", "bridge", "--local-binary", "<generated-pcm>", "--transfer-port", str(args.transfer_port + 2)],
        },
    })
    return install_steps


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    state = preflight_state(args)
    materialize_plan = snd.dry_run_plan(state["snd_materialization_preflight"])
    plan = state["speaker_plan"]
    return {
        "decision": "v2379-native-speaker-pilot-runner-dry-run" if state["ok"] else "v2379-native-speaker-pilot-runner-blocked",
        "ok": bool(state["ok"]),
        "device_action": "none",
        "approval_phrase_required": APPROVAL_PHRASE,
        "preflight": state,
        "materialization_plan": materialize_plan,
        "transfer_readiness_plan": {
            "host_ncm_ping": tiny_live.host_ping_command(args),
            "tcpctl_ping": tiny_live.tcpctl_ping_command(args),
            "host_ncm_repair": tiny_live.ncm_host_setup_command(args),
            "selection": "auto: tcpctl when ready; otherwise serial fallback when host NCM ping works",
        },
        "tool_install_plan": dry_run_install_plan(args, state),
        "runtime_plan": {
            "snapshot_before_apply": [REMOTE_TINYMIX, "-D", str(args.card), "--all-values"],
            "route_apply_commands": plan["route_apply_commands"],
            "playback": plan["playback"],
            "route_reset_commands": plan["route_reset_commands"],
            "snapshot_after_reset": [REMOTE_TINYMIX, "-D", str(args.card), "--all-values"],
        },
    }


def generate_pilot_wav(path: Path, *, duration_ms: int, amplitude: float) -> dict[str, Any]:
    if amplitude <= 0 or amplitude > MAX_AMPLITUDE:
        raise ValueError(f"amplitude out of bound: {amplitude}")
    if duration_ms <= 0 or duration_ms > MAX_DURATION_MS:
        raise ValueError(f"duration out of bound: {duration_ms}")
    frame_count = SAMPLE_RATE * duration_ms // 1000
    max_i16 = 32767
    frequency = 440.0
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(CHANNELS)
        wav.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav.setframerate(SAMPLE_RATE)
        for frame in range(frame_count):
            value = int(max_i16 * amplitude * math.sin(2.0 * math.pi * frequency * frame / SAMPLE_RATE))
            packed = struct.pack("<h", value)
            wav.writeframesraw(packed * CHANNELS)
    return {
        "path": rel(path),
        "duration_ms": duration_ms,
        "amplitude": amplitude,
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "sample_width_bytes": SAMPLE_WIDTH_BYTES,
        "frames": frame_count,
        "sha256": recipe.sha256_file(path),
    }


def run_host_step(out_dir: Path, steps: list[dict[str, Any]], name: str, command: list[str], *, timeout: float, allow_error: bool = False) -> dict[str, Any]:
    return snd.run_step(out_dir, steps, name, command, timeout=timeout, allow_error=allow_error)


def step_text(step: dict[str, Any]) -> str:
    return tiny_live.step_text(step)


def run_tool_command(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]], name: str, argv: list[str], *, use_tcpctl: bool, timeout: float, allow_error: bool = False) -> dict[str, Any]:
    if use_tcpctl:
        return run_host_step(out_dir, steps, name, tiny_live.tcpctl_run_command(args, argv), timeout=timeout, allow_error=allow_error)
    return snd.run_serial_transport_step(out_dir, steps, name, args, ["run", *argv], timeout=timeout, retry_observation=False, allow_error=allow_error)


def parse_tinymix_text(text: str) -> dict[int, dict[str, Any]]:
    tmp = snd.ROOT / "workspace/private/tmp/v2379-parse-tinymix.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text, encoding="utf-8", errors="replace")
    try:
        return recipe.parse_tinymix(tmp)
    finally:
        tmp.unlink(missing_ok=True)


def route_reset_verification(pre_text: str, post_text: str, reset_commands: list[dict[str, Any]]) -> dict[str, Any]:
    pre = parse_tinymix_text(pre_text)
    post = parse_tinymix_text(post_text)
    mismatches: list[dict[str, Any]] = []
    for command in reset_commands:
        idx_text = str(command.get("name", "")).split("-", 2)[1:2]
        if not idx_text:
            mismatches.append({"command": command.get("name"), "reason": "could not parse idx"})
            continue
        idx = int(idx_text[0])
        if pre.get(idx, {}).get("value") != post.get(idx, {}).get("value"):
            mismatches.append({
                "idx": idx,
                "name": command.get("name"),
                "before": pre.get(idx, {}).get("value"),
                "after": post.get(idx, {}).get("value"),
            })
    return {"ok": not mismatches, "mismatches": mismatches}


def install_runtime_artifacts(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]], state: dict[str, Any], pcm_path: Path) -> dict[str, Any]:
    readiness = tiny_live.probe_transfer_readiness(args, out_dir, steps)
    use_tcpctl = readiness["selected_transport"] == "tcpctl"
    control_channel = "tcpctl" if use_tcpctl else "bridge"
    installed: dict[str, Any] = {"transfer_readiness": readiness, "artifacts": {}, "selected_transport": readiness["selected_transport"]}
    artifacts = [
        ("tinymix", raw_tool_path(load_raw_tinyalsa_manifest(args.manifest), "tinymix"), REMOTE_TINYMIX, args.transfer_port),
        ("tinyplay", raw_tool_path(load_raw_tinyalsa_manifest(args.manifest), "tinyplay"), REMOTE_TINYPLAY, args.transfer_port + 1),
        ("pilot_wav", pcm_path, REMOTE_PCM, args.transfer_port + 2),
    ]
    for name, local_path, target_path, port in artifacts:
        step = run_host_step(
            out_dir,
            steps,
            f"install-{name}",
            tiny_live.install_command(args, local_path, target_path, port, control_channel=control_channel),
            timeout=args.transfer_timeout + 45.0,
        )
        installed["artifacts"][name] = {"ok": bool(step.get("ok")), "remote": target_path, "stdout_path": step.get("stdout_path")}
    return installed


def run_speaker_pilot(args: argparse.Namespace, out_dir: Path, steps: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    pcm_path = out_dir / "pilot_48k_s16le_stereo_0p02_1s.wav"
    pcm = generate_pilot_wav(pcm_path, duration_ms=args.duration_ms, amplitude=args.amplitude)
    result: dict[str, Any] = {"pilot_wav": pcm, "route_apply": [], "route_reset": [], "playback_attempted": False}
    install = install_runtime_artifacts(args, out_dir, steps, state, pcm_path)
    result["install"] = install
    use_tcpctl = install["selected_transport"] == "tcpctl"
    plan = state["speaker_plan"]
    baseline_step: dict[str, Any] | None = None
    post_reset_step: dict[str, Any] | None = None
    try:
        baseline_step = run_tool_command(
            args,
            out_dir,
            steps,
            "tinymix-all-values-before-apply",
            [REMOTE_TINYMIX, "-D", str(args.card), "--all-values"],
            use_tcpctl=use_tcpctl,
            timeout=args.mixer_timeout,
        )
        for command in plan["route_apply_commands"]:
            step = run_tool_command(
                args,
                out_dir,
                steps,
                command["name"],
                [str(part) for part in command["argv"]],
                use_tcpctl=use_tcpctl,
                timeout=args.mixer_timeout,
            )
            result["route_apply"].append({"name": command["name"], "ok": bool(step.get("ok")), "stdout_path": step.get("stdout_path")})
        result["playback_attempted"] = True
        playback_step = run_tool_command(
            args,
            out_dir,
            steps,
            "tinyplay-low-amplitude-speaker-pilot",
            [str(part) for part in plan["playback"]["argv"]],
            use_tcpctl=use_tcpctl,
            timeout=args.playback_timeout,
        )
        result["playback"] = {"ok": bool(playback_step.get("ok")), "stdout_path": playback_step.get("stdout_path")}
    finally:
        for command in plan["route_reset_commands"]:
            step = run_tool_command(
                args,
                out_dir,
                steps,
                command["name"],
                [str(part) for part in command["argv"]],
                use_tcpctl=use_tcpctl,
                timeout=args.mixer_timeout,
                allow_error=True,
            )
            result["route_reset"].append({"name": command["name"], "ok": bool(step.get("ok")), "stdout_path": step.get("stdout_path")})
        post_reset_step = run_tool_command(
            args,
            out_dir,
            steps,
            "tinymix-all-values-after-reset",
            [REMOTE_TINYMIX, "-D", str(args.card), "--all-values"],
            use_tcpctl=use_tcpctl,
            timeout=args.mixer_timeout,
            allow_error=True,
        )
    if baseline_step and post_reset_step and post_reset_step.get("ok"):
        result["route_reset_verification"] = route_reset_verification(
            step_text(baseline_step),
            step_text(post_reset_step),
            plan["route_reset_commands"],
        )
        if not result["route_reset_verification"].get("ok"):
            raise RuntimeError("route reset verification failed")
    if not all(item.get("ok") for item in result["route_reset"]):
        raise RuntimeError("one or more route reset commands failed")
    return result


def verify_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise SystemExit("refusing live run: exact --approval phrase required:\n" + APPROVAL_PHRASE)


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    verify_live_approval(args)
    if not state.get("ok"):
        raise SystemExit("refusing live run: V2379 preflight failed")
    out_dir = snd.ROOT / f"workspace/private/runs/audio/v2379-native-speaker-pilot-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": "v2379-native-speaker-pilot-live-started",
        "out_dir": rel(out_dir),
        "preflight": state,
        "steps": steps,
        "rolled_back": False,
    }
    write_json(out_dir / "preflight.json", state)
    candidate_flashed = False
    try:
        run_host_step(
            out_dir,
            steps,
            "preflight-current-v2321-verify",
            snd.flash_command(snd.ROLLBACK_IMAGE, snd.ROLLBACK_VERSION, snd.ROLLBACK_SHA256, from_native=False) + ["--verify-only"],
            timeout=args.flash_timeout,
        )
        current_selftest = snd.run_a90ctl_observation(args, out_dir, steps, "preflight-current-selftest", ["selftest", "verbose"], timeout=120.0)
        if not snd.selftest_ok(stdout_of(current_selftest)):
            raise RuntimeError("resident preflight selftest did not report fail=0")

        run_host_step(out_dir, steps, "flash-v2334-candidate", snd.flash_command(snd.CANDIDATE_IMAGE, snd.CANDIDATE_VERSION, snd.CANDIDATE_SHA256, from_native=True), timeout=args.flash_timeout)
        candidate_flashed = True
        version = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-version", ["version"], timeout=90.0)
        if snd.CANDIDATE_VERSION not in stdout_of(version):
            raise RuntimeError("candidate version output did not contain expected version")
        snd.run_a90ctl_observation(args, out_dir, steps, "candidate-status", ["status"], timeout=90.0)
        candidate_selftest = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0)
        if not snd.selftest_ok(stdout_of(candidate_selftest)):
            raise RuntimeError("candidate selftest did not report fail=0")

        pre_adsp = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-audio-adsp-status-before", ["audio", "adsp-status"], timeout=90.0)
        pre_snd = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-audio-snd-status-before", ["audio", "snd-status"], timeout=90.0)
        result["initial_audio"] = snd.classify_audio_status(stdout_of(pre_adsp) + "\n" + stdout_of(pre_snd))
        if not (result["initial_audio"]["has_audio_card"] and result["initial_audio"]["has_sound_class_control"]):
            snd.run_menu_settle_step(out_dir, steps, "settle-before-adsp-boot-once", args)
            snd.run_serial_transport_step(out_dir, steps, "candidate-adsp-boot-once", args, ["audio", "adsp-boot-once", snd.ADSP_TOKEN], timeout=90.0, retry_observation=False)
        result["card_wait"] = snd.wait_for_audio_card(args, out_dir, steps)
        before_materialize = snd.run_a90ctl_observation(args, out_dir, steps, "snd-status-before-materialize", ["audio", "snd-status"], timeout=90.0)
        result["before_materialize"] = snd.classify_audio_status(stdout_of(before_materialize))
        snd.run_menu_settle_step(out_dir, steps, "settle-before-snd-materialize-once", args)
        materialize = snd.run_serial_transport_step(out_dir, steps, "snd-materialize-once", args, ["audio", "snd-materialize-once", snd.SND_TOKEN], timeout=90.0, retry_observation=False)
        result["materialize_tail"] = stdout_of(materialize)[-4000:]
        after_materialize = snd.run_a90ctl_observation(args, out_dir, steps, "snd-status-after-materialize", ["audio", "snd-status"], timeout=90.0)
        after = snd.classify_audio_status(stdout_of(after_materialize))
        result["after_materialize"] = after
        if not (after["has_dev_snd_control"] and after["has_dev_snd_pcm"]):
            raise RuntimeError("materialization did not produce control+pcm /dev/snd nodes")

        result["speaker_pilot"] = run_speaker_pilot(args, out_dir, steps, state)
        final_candidate_selftest = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-selftest-after-speaker-pilot", ["selftest", "verbose"], timeout=120.0)
        if not snd.selftest_ok(stdout_of(final_candidate_selftest)):
            raise RuntimeError("candidate final selftest did not report fail=0")
        result["decision"] = "v2379-native-speaker-pilot-live-pass-before-rollback"
    except Exception as exc:
        result["decision"] = "v2379-native-speaker-pilot-live-blocked"
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        raise
    finally:
        if candidate_flashed:
            rollback_record = run_host_step(out_dir, steps, "rollback-v2321", snd.flash_command(snd.ROLLBACK_IMAGE, snd.ROLLBACK_VERSION, snd.ROLLBACK_SHA256, from_native=True), timeout=args.flash_timeout, allow_error=True)
            result["rolled_back"] = bool(rollback_record.get("ok"))
            try:
                rollback_version = snd.run_a90ctl_observation(args, out_dir, steps, "rollback-version", ["version"], timeout=90.0)
                rollback_selftest = snd.run_a90ctl_observation(args, out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0)
                result["rollback_version_ok"] = snd.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = snd.selftest_ok(stdout_of(rollback_selftest))
            except Exception as exc:  # noqa: BLE001
                result["rollback_health_error"] = str(exc)
        write_json(out_dir / "result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="verify local artifacts and print the exact-gated live plan; no bridge/flash")
    mode.add_argument("--run-live", action="store_true", help="perform the exact-gated native speaker pilot")
    parser.add_argument("--approval", default="", help="exact AUD-4 phrase required with --run-live")
    parser.add_argument("--manifest", type=Path, default=inv.MANIFEST)
    parser.add_argument("--evidence-dir", type=Path, default=recipe.DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--host-ip", default="192.168.7.1")
    parser.add_argument("--host-prefix", type=int, default=24)
    parser.add_argument("--tcp-port", type=int, default=2325)
    parser.add_argument("--command-timeout", type=float, default=60.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--device-toolbox", default=DEFAULT_DEVICE_TOOLBOX)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--card-timeout", type=float, default=70.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--menu-settle-sec", type=float, default=1.0)
    parser.add_argument("--transfer-port", type=int, default=18179)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--repair-host-ncm", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--ncm-setup-timeout", type=float, default=120.0)
    parser.add_argument("--ncm-interface-timeout", type=float, default=20.0)
    parser.add_argument("--ncm-setup-sudo", default="sudo -n")
    parser.add_argument("--inventory-transport", choices=("auto", "tcpctl", "serial"), default="auto")
    parser.add_argument("--card", type=int, default=0)
    parser.add_argument("--mixer-timeout", type=float, default=45.0)
    parser.add_argument("--playback-timeout", type=float, default=20.0)
    parser.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = preflight_state(args)
    if args.dry_run:
        print(json.dumps(dry_run_payload(args), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if state.get("ok") else 2
    result = live_run(args, copy.deepcopy(state))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("decision") == "v2379-native-speaker-pilot-live-pass-before-rollback" else 1


if __name__ == "__main__":
    raise SystemExit(main())
