#!/usr/bin/env python3
"""V2550 host-only live-wrapper plan for native ACDB topology replay.

This unit does not touch the device. It composes the V2549 execute-enabled ACDB
helper with the already-proven V2377/V2379 speaker route/app-type/PCM probe path
so the next live unit has one reviewable sequence: replay topology calibration,
hold the calibration fds open, run the bounded PCM probe, reset route, deallocate,
and rollback to V2321.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_replay_execute_helper_gate_v2549 as v2549
import native_audio_speaker_pilot_live_handoff_v2379 as speaker
import native_audio_snd_nodes_preflight_handoff_v2335 as snd

RUN_ID = "V2550"
BUILD_TAG = "v2550-audio-acdb-topology-replay-live-wrapper-plan"
DEFAULT_MANIFEST = snd.ROOT / "workspace/private/builds/audio" / BUILD_TAG / "manifest.json"
DEFAULT_HELPER = snd.ROOT / "workspace/private/builds/audio/v2549-audio-acdb-replay-execute-helper-gate/bin/a90_acdb_replay_execute_v2549"
DEFAULT_HELPER_SHA256 = "acbd11dfef7fcce187f55f966e357952b5a986fddb79b2ff0b4f3ed727c62792"
REMOTE_DIR = "/cache/a90-runtime/bin/v2550-acdb-topology-replay"
REMOTE_HELPER = f"{REMOTE_DIR}/a90_acdb_replay_execute_v2549"
REMOTE_PAYLOAD = f"{REMOTE_DIR}/core_custom_topologies_v2547.bin"
REMOTE_PCM_PROBE = f"{REMOTE_DIR}/a90_pcm_write_probe_v2386"
REMOTE_TINYMIX = f"{REMOTE_DIR}/tinymix"
REMOTE_PCM = f"{REMOTE_DIR}/pilot_48k_s16le_stereo_0p02_1s.wav"
REMOTE_HELPER_STDOUT = f"{REMOTE_DIR}/acdb-helper.stdout"
REMOTE_HELPER_STDERR = f"{REMOTE_DIR}/acdb-helper.stderr"
FUTURE_APPROVAL_PHRASE = (
    "AUD-5N-native-acdb-topology-replay go: one-shot V2550 topology replay wrapper "
    "with pinned V2547 payload, V2407 app-type, V2377 route, bounded PCM probe, "
    "explicit deallocate, rollback to V2321"
)
FORBIDDEN_PLAN_TOKENS = (
    "fastboot",
    " dd ",
    "/efs",
    "/sec_efs",
    "/dev/block",
    "magisk",
    "su -c",
    "app_process",
    "am start",
    "settings put",
    "AUDIO_GET_CALIBRATION",
    "AUDIO_POST_CALIBRATION",
    "AUDIO_SET_RTAC",
    "AUDIO_GET_RTAC",
)
REQUIRED_PLAN_MARKERS = (
    "AUDIO_SET_CALIBRATION ok",
    "AUDIO_DEALLOCATE_CALIBRATION",
    "route reset",
    "rollback to V2321",
)


def rel(path: Path) -> str:
    return snd.rel(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def helper_state(path: Path = DEFAULT_HELPER) -> dict[str, Any]:
    exists = path.exists()
    state: dict[str, Any] = {
        "path": rel(path),
        "exists": exists,
        "expected_sha256": DEFAULT_HELPER_SHA256,
        "private_only": True,
        "committable": False,
    }
    if not exists:
        state.update({"ready": False, "reason": "missing-private-v2549-helper"})
        return state
    digest = v2549.sha256_file(path)
    file_text = v2549.tool_file(path)
    strings_probe = v2549.run(["strings", str(path)], timeout=10.0)
    strings_text = strings_probe["stdout"] if strings_probe["ok"] else ""
    state.update(
        {
            "sha256": digest,
            "size": path.stat().st_size,
            "mode": oct(path.stat().st_mode & 0o777),
            "file": file_text,
            "sha256_ok": digest == DEFAULT_HELPER_SHA256,
            "file_ok": "ARM aarch64" in file_text and "statically linked" in file_text,
            "execute_marker_ok": "execute_compiled_in" in strings_text and "AUDIO_SET_CALIBRATION" in strings_text,
            "default_block_message_absent": "execute mode is blocked in this host-only scaffold build" not in strings_text,
        }
    )
    state["ready"] = bool(
        state["sha256_ok"]
        and state["file_ok"]
        and state["execute_marker_ok"]
        and state["default_block_message_absent"]
    )
    if not state["ready"]:
        state["reason"] = "helper-sha-file-or-static-probe-failed"
    return state


def payload_state(path: Path = v2549.STABLE_PAYLOAD) -> dict[str, Any]:
    return v2549.payload_state(path)


def speaker_wrapper_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        dry_run=True,
        run_live=False,
        approval="",
        manifest=args.tinyalsa_manifest,
        pcm_probe_manifest=args.pcm_probe_manifest,
        playback_tool="pcm-probe",
        evidence_dir=args.evidence_dir,
        bridge_host=args.bridge_host,
        bridge_port=args.bridge_port,
        device_ip=args.device_ip,
        host_ip=args.host_ip,
        host_prefix=args.host_prefix,
        tcp_port=args.tcp_port,
        command_timeout=args.command_timeout,
        tcp_timeout=args.tcp_timeout,
        device_toolbox=args.device_toolbox,
        device_busybox=args.device_busybox,
        flash_timeout=args.flash_timeout,
        card_timeout=args.card_timeout,
        poll_interval=args.poll_interval,
        menu_settle_sec=args.menu_settle_sec,
        transfer_port=args.transfer_port,
        transfer_delay=args.transfer_delay,
        transfer_timeout=args.transfer_timeout,
        repair_host_ncm=args.repair_host_ncm,
        ncm_setup_timeout=args.ncm_setup_timeout,
        ncm_interface_timeout=args.ncm_interface_timeout,
        ncm_setup_sudo=args.ncm_setup_sudo,
        inventory_transport=args.inventory_transport,
        card=args.card,
        route_transport=args.route_transport,
        mixer_timeout=args.mixer_timeout,
        playback_timeout=args.playback_timeout,
        duration_ms=args.duration_ms,
        amplitude=args.amplitude,
        set_observed_app_type=True,
    )


def remote_replay_script(hold_sec: int) -> str:
    return "\n".join(
        [
            "set -eu",
            f"mkdir -p {REMOTE_DIR}",
            f"chmod 0700 {REMOTE_DIR}",
            f"echo '{v2549.EXPECTED_PAYLOAD_SHA256}  {REMOTE_PAYLOAD}' | sha256sum -c -",
            "minor=$(awk '$2==\"msm_audio_cal\"{print $1; exit}' /proc/misc 2>/dev/null || true)",
            "if [ -z \"$minor\" ]; then echo A90_ACDB_REPLAY_NO_MSM_AUDIO_CAL_MISC; exit 30; fi",
            "if [ ! -e /dev/msm_audio_cal ]; then mknod /dev/msm_audio_cal c 10 \"$minor\"; chmod 0600 /dev/msm_audio_cal || true; fi",
            f"{REMOTE_HELPER} --execute --payload {REMOTE_PAYLOAD} --hold-sec {hold_sec} >{REMOTE_HELPER_STDOUT} 2>{REMOTE_HELPER_STDERR} &",
            "helper_pid=$!",
            "deadline=$((SECONDS+20))",
            "while [ $SECONDS -lt $deadline ]; do",
            f"  if grep -q 'AUDIO_SET_CALIBRATION ok' {REMOTE_HELPER_STDERR} 2>/dev/null; then echo A90_ACDB_REPLAY_SET_OK pid=$helper_pid; exit 0; fi",
            "  if ! kill -0 $helper_pid 2>/dev/null; then echo A90_ACDB_REPLAY_HELPER_EXITED_BEFORE_SET; cat " + REMOTE_HELPER_STDERR + " 2>/dev/null || true; exit 31; fi",
            "  sleep 1",
            "done",
            "echo A90_ACDB_REPLAY_SET_TIMEOUT; cat " + REMOTE_HELPER_STDERR + " 2>/dev/null || true; exit 32",
        ]
    )


def remote_wait_cleanup_script() -> str:
    return "\n".join(
        [
            "set -u",
            "echo A90_ACDB_REPLAY_HELPER_STDERR_BEGIN",
            f"cat {REMOTE_HELPER_STDERR} 2>/dev/null || true",
            f"if grep -q 'AUDIO_DEALLOCATE_CALIBRATION' {REMOTE_HELPER_STDERR} 2>/dev/null; then echo A90_ACDB_REPLAY_DEALLOCATE_SEEN; else echo A90_ACDB_REPLAY_DEALLOCATE_MISSING; exit 33; fi",
            "echo A90_ACDB_REPLAY_HELPER_STDERR_END",
            "echo A90_ACDB_REPLAY_HELPER_STDOUT_BEGIN",
            f"cat {REMOTE_HELPER_STDOUT} 2>/dev/null || true",
            "echo A90_ACDB_REPLAY_HELPER_STDOUT_END",
            "if pgrep -f a90_acdb_replay_execute_v2549 >/dev/null 2>&1; then echo A90_ACDB_REPLAY_HELPER_STILL_RUNNING; fi",
        ]
    )


def plan(args: argparse.Namespace) -> dict[str, Any]:
    speaker_args = speaker_wrapper_args(args)
    speaker_state = speaker.preflight_state(speaker_args)
    speaker_plan = speaker.speaker_plan(speaker_args)
    helper = helper_state(args.helper)
    payload = payload_state(args.payload)
    route_apply = speaker_plan.get("route_apply_commands", [])
    route_reset = speaker_plan.get("route_reset_commands", [])
    app_type = speaker_plan.get("app_type_command")
    playback = speaker_plan.get("playback", {})
    playback_remote = [REMOTE_PCM_PROBE if part == speaker.REMOTE_PCM_PROBE else REMOTE_PCM if part == speaker.REMOTE_PCM else part for part in playback.get("argv", [])]
    plan_payload: dict[str, Any] = {
        "decision": "v2550-acdb-topology-replay-live-wrapper-plan-host-only",
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "playback_run": False,
        "future_live_approval_phrase": FUTURE_APPROVAL_PHRASE,
        "inputs": {
            "helper": helper,
            "payload": payload,
            "speaker_preflight_ok": speaker_state.get("ok"),
            "speaker_app_type_enabled": bool(app_type),
            "route_apply_count": len(route_apply),
            "route_reset_count": len(route_reset),
        },
        "remote_artifacts": {
            "dir": REMOTE_DIR,
            "helper": REMOTE_HELPER,
            "payload": REMOTE_PAYLOAD,
            "tinymix": REMOTE_TINYMIX,
            "pcm_probe": REMOTE_PCM_PROBE,
            "pcm_wav": REMOTE_PCM,
            "helper_stdout": REMOTE_HELPER_STDOUT,
            "helper_stderr": REMOTE_HELPER_STDERR,
        },
        "future_live_sequence": [
            "verify resident V2321 and selftest fail=0",
            "flash V2334 snd-node candidate through checked helper and verify health",
            "run ADSP boot-one-shot only if card is not already up",
            "run /dev/snd materialize-once and require control+pcm nodes",
            "stage V2549 helper, V2547 payload, tinymix, PCM probe, and low-amplitude WAV into runtime temp dir",
            "verify payload SHA-256 on device",
            "take tinymix --all-values baseline",
            "set V2407 Audio Stream 0 App Type Cfg tuple",
            "apply only V2377-observed speaker route controls",
            "start V2549 helper and wait for AUDIO_SET_CALIBRATION ok",
            "run bounded PCM probe during helper hold window",
            "capture helper stdout/stderr including AUDIO_DEALLOCATE_CALIBRATION result",
            "reverse route reset and verify reset snapshot",
            "remove staged runtime files",
            "rollback to V2321 and require selftest fail=0",
        ],
        "app_type_command": app_type,
        "route_apply_commands": route_apply,
        "route_reset_commands": route_reset,
        "replay_wait_script": remote_replay_script(args.hold_sec),
        "playback_command": {
            "name": "bounded-pcm-probe-during-acdb-hold",
            "argv": playback_remote,
            "source": "V2379 pcm-probe playback command with V2550 remote paths",
            "amplitude": args.amplitude,
            "duration_ms": args.duration_ms,
        },
        "helper_cleanup_capture_script": remote_wait_cleanup_script(),
        "abort_conditions": [
            "helper or payload private artifact missing or SHA mismatch",
            "V2334/V2321 preflight fails",
            "ADSP/card or /dev/snd materialization fails",
            "runtime /dev/msm_audio_cal materialization fails",
            "route/app-type apply fails",
            "AUDIO_SET_CALIBRATION ok marker not observed before PCM probe",
            "PCM probe exits with open/prepare/write error",
            "route reset verification fails",
            "AUDIO_DEALLOCATE_CALIBRATION is missing or reports failure",
            "rollback V2321 health is not clean",
        ],
    }
    plan_payload["safety"] = safety(plan_payload)
    plan_payload["ok"] = bool(helper.get("ready") and payload.get("ready") and speaker_state.get("ok") and plan_payload["safety"].get("ok"))
    return plan_payload


def safety(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    findings = []
    for token in FORBIDDEN_PLAN_TOKENS:
        if token in text:
            findings.append({"token": token})
    marker_text = "\n".join(str(item) for item in payload.get("future_live_sequence", [])) + "\n" + str(payload.get("helper_cleanup_capture_script", ""))
    missing = [marker for marker in REQUIRED_PLAN_MARKERS if marker not in marker_text]
    return {
        "ok": not findings and not missing,
        "findings": findings,
        "missing_required_markers": missing,
        "host_only_v2550": True,
        "live_ioctls_blocked_in_this_unit": True,
        "live_replay_requires_future_unit": True,
        "raw_payload_private_only": True,
        "helper_binary_private_only": True,
        "allowed_future_audio_writes": [
            "V2407 observed App Type Cfg",
            "V2377 observed speaker route controls",
            "V2549 topology AUDIO_ALLOCATE/SET/DEALLOCATE sequence",
            "bounded low-amplitude PCM probe",
        ],
    }


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def live_refusal(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    ok_gate = args.approval == FUTURE_APPROVAL_PHRASE
    return {
        "decision": "v2550-live-refused-source-only-wrapper-plan",
        "ok": False,
        "approval_phrase_matched": ok_gate,
        "reason": "V2550 intentionally emits the reviewed wrapper plan only; live topology replay belongs in the next bounded V-iteration after this source is committed.",
        "host_only": True,
        "native_calibration_ioctls_run": False,
        "plan_ok": payload.get("ok"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run-live", action="store_true", help="source-only refusal in V2550; future live uses this exact plan")
    parser.add_argument("--approval", default="")
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--helper", type=Path, default=DEFAULT_HELPER)
    parser.add_argument("--payload", type=Path, default=v2549.STABLE_PAYLOAD)
    parser.add_argument("--hold-sec", type=int, default=10)
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
    parser.add_argument("--transfer-port", type=int, default=18220)
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
    parser.add_argument("--playback-timeout", type=float, default=20.0)
    parser.add_argument("--duration-ms", type=int, default=speaker.DEFAULT_DURATION_MS)
    parser.add_argument("--amplitude", type=float, default=speaker.DEFAULT_AMPLITUDE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = plan(args)
    write_manifest(args.manifest_path, payload)
    if args.run_live:
        refusal = live_refusal(args, payload)
        print(json.dumps(refusal, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
