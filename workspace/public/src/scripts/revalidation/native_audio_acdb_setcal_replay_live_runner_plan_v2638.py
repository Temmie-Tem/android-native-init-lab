#!/usr/bin/env python3
"""V2638 host-only checked runner plan for exact SET-cal native replay.

This unit converts the V2636 deployment manifest into a concrete future live
execution contract: stage the exact replay files, run the V2635 helper in the
background, wait for all SET records, run the already-proven route + bounded PCM
probe during the helper hold window, then verify deallocation and cleanup.

It does not touch the device. Per the 2026-06-18 GOAL policy update, live replay
is self-authorized inside the recoverable envelope; legacy approval and Gate-2
flags are recorded but do not block the plan.
"""

from __future__ import annotations

import argparse
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_acdb_setcal_replay_live_gate_v2637 as v2637
import native_audio_speaker_pilot_live_handoff_v2379 as speaker
import native_audio_snd_nodes_preflight_handoff_v2335 as snd

ROOT = Path(__file__).resolve().parents[5]
RUN_ID = "V2638"
BUILD_TAG = "v2638-audio-acdb-setcal-replay-live-runner-plan"
DEFAULT_V2636_MANIFEST = v2637.DEFAULT_V2636_MANIFEST
DEFAULT_PRIVATE_MANIFEST = ROOT / "workspace/private/builds/audio" / BUILD_TAG / "runner-plan.json"
DEFAULT_REPORT = ROOT / "docs/reports/NATIVE_INIT_V2638_AUDIO_ACDB_SETCAL_REPLAY_LIVE_RUNNER_PLAN_2026-06-18.md"
APPROVAL_PHRASE = v2637.APPROVAL_PHRASE
REMOTE_STDOUT = "setcal-replay.stdout"
REMOTE_STDERR = "setcal-replay.stderr"
REMOTE_SCRIPT_DIR = "/cache/a90-runtime/bin/v2639-setcal-replay-scripts"
REMOTE_START_SCRIPT = "setcal-start-and-wait-all-set.sh"
REMOTE_DEALLOCATE_SCRIPT = "setcal-deallocate-check.sh"
REMOTE_RUNTIME_CLEANUP_SCRIPT = "setcal-runtime-cleanup.sh"
SET_WAIT_TIMEOUT_SEC = 30


def rel(path: Path | str) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def speaker_args(args: argparse.Namespace) -> argparse.Namespace:
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


def load_v2636(path: Path) -> dict[str, Any]:
    return v2637.load_deploy_manifest(path)["raw"]


def deploy_files(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return list(manifest.get("files") or [])


def remote_paths(manifest: dict[str, Any]) -> list[str]:
    return [str(item.get("remote_path")) for item in deploy_files(manifest) if item.get("remote_path")]


def set_entry_count(manifest: dict[str, Any]) -> int:
    argv = [str(part) for part in manifest.get("remote_argv") or []]
    return int(argv.count("--basic-payload") + argv.count("--exact-set"))


def final_set_index(manifest: dict[str, Any]) -> int:
    return set_entry_count(manifest) - 1


def payload_entry_indices(manifest: dict[str, Any]) -> list[int]:
    argv = [str(part) for part in manifest.get("remote_argv") or []]
    indices: list[int] = []
    entry_index = 0
    offset = 0
    while offset < len(argv):
        token = argv[offset]
        if token == "--basic-payload":
            indices.append(entry_index)
            entry_index += 1
            offset += 2
            continue
        if token == "--exact-set":
            spec = argv[offset + 1] if offset + 1 < len(argv) else ""
            if ":" in spec:
                indices.append(entry_index)
            entry_index += 1
            offset += 2
            continue
        offset += 1
    return indices


def remote_sha_check_lines(manifest: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for item in deploy_files(manifest):
        local = item.get("local") or {}
        digest = local.get("sha256")
        remote = item.get("remote_path")
        if digest and remote:
            lines.append(f"echo {shlex.quote(str(digest) + '  ' + str(remote))} | sha256sum -c -")
    return lines


def devnode_setup_lines() -> list[str]:
    return [
        "cal_minor=$(awk '$2==\"msm_audio_cal\"{print $1; exit}' /proc/misc 2>/dev/null || true)",
        "if [ -z \"$cal_minor\" ]; then echo A90_SETCAL_REPLAY_NO_MSM_AUDIO_CAL_MISC; exit 30; fi",
        "if [ ! -e /dev/msm_audio_cal ]; then mknod /dev/msm_audio_cal c 10 \"$cal_minor\"; chmod 0600 /dev/msm_audio_cal || true; fi",
        "ion_minor=$(awk '$2==\"ion\"{print $1; exit}' /proc/misc 2>/dev/null || true)",
        "if [ -z \"$ion_minor\" ]; then echo A90_SETCAL_REPLAY_NO_ION_MISC; exit 31; fi",
        "if [ ! -e /dev/ion ]; then mknod /dev/ion c 10 \"$ion_minor\"; chmod 0600 /dev/ion || true; fi",
    ]


def remote_start_script(manifest: dict[str, Any], *, wait_timeout_sec: int = SET_WAIT_TIMEOUT_SEC) -> str:
    remote_dir = str(manifest.get("remote_dir"))
    stdout_path = f"{remote_dir}/{REMOTE_STDOUT}"
    stderr_path = f"{remote_dir}/{REMOTE_STDERR}"
    argv = [str(part) for part in manifest.get("remote_argv") or []]
    final_index = final_set_index(manifest)
    lines = [
        "set -eu",
        f"mkdir -p {shlex.quote(remote_dir)}",
        f"chmod 0700 {shlex.quote(remote_dir)}",
        *remote_sha_check_lines(manifest),
        *devnode_setup_lines(),
        " ".join(shlex.quote(part) for part in argv) + f" >{shlex.quote(stdout_path)} 2>{shlex.quote(stderr_path)} &",
        "helper_pid=$!",
        "i=0",
        f"while [ $i -lt {int(wait_timeout_sec)} ]; do",
        f"  if grep -q 'A90_ACDB_SETCAL_SET_OK index={final_index}' {shlex.quote(stderr_path)} 2>/dev/null; then echo A90_SETCAL_REPLAY_ALL_SET_OK pid=$helper_pid final_index={final_index}; exit 0; fi",
        f"  if ! kill -0 $helper_pid 2>/dev/null; then echo A90_SETCAL_REPLAY_HELPER_EXITED_BEFORE_ALL_SET; cat {shlex.quote(stderr_path)} 2>/dev/null || true; exit 32; fi",
        "  i=$((i+1))",
        "  sleep 1",
        "done",
        f"echo A90_SETCAL_REPLAY_SET_TIMEOUT final_index={final_index}; cat {shlex.quote(stderr_path)} 2>/dev/null || true; exit 33",
    ]
    return "\n".join(lines)


def remote_deallocate_check_script(manifest: dict[str, Any]) -> str:
    remote_dir = str(manifest.get("remote_dir"))
    stderr_path = f"{remote_dir}/{REMOTE_STDERR}"
    final_index = final_set_index(manifest)
    lines = [
        "set -u",
        "echo A90_SETCAL_REPLAY_STDERR_BEGIN",
        f"cat {shlex.quote(stderr_path)} 2>/dev/null || true",
        f"if grep -q 'A90_ACDB_SETCAL_REPLAY_DONE rc=0' {shlex.quote(stderr_path)} 2>/dev/null; then echo A90_SETCAL_REPLAY_DONE_OK; else echo A90_SETCAL_REPLAY_DONE_MISSING; exit 34; fi",
    ]
    for index in payload_entry_indices(manifest):
        lines.append(
            f"if grep -q 'A90_ACDB_SETCAL_DEALLOCATE_OK index={index}' {shlex.quote(stderr_path)} 2>/dev/null; "
            f"then echo A90_SETCAL_REPLAY_DEALLOCATE_SEEN index={index}; "
            f"else echo A90_SETCAL_REPLAY_DEALLOCATE_MISSING index={index}; exit 35; fi"
        )
    lines.extend(
        [
            f"if grep -q 'A90_ACDB_SETCAL_SET_OK index={final_index}' {shlex.quote(stderr_path)} 2>/dev/null; then echo A90_SETCAL_REPLAY_FINAL_SET_SEEN; else echo A90_SETCAL_REPLAY_FINAL_SET_MISSING; exit 36; fi",
            "echo A90_SETCAL_REPLAY_STDERR_END",
        ]
    )
    return "\n".join(lines)


def remote_runtime_cleanup_script(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "set -u",
            f"rm -rf {shlex.quote(str(manifest.get('remote_dir')))}",
            f"rm -rf {shlex.quote(REMOTE_SCRIPT_DIR)}",
            "echo A90_SETCAL_REPLAY_RUNTIME_CLEANUP_DONE",
        ]
    )


def remote_script_paths(manifest: dict[str, Any]) -> dict[str, str]:
    _ = manifest
    return {
        "start_and_wait_all_set": f"{REMOTE_SCRIPT_DIR}/{REMOTE_START_SCRIPT}",
        "deallocate_check": f"{REMOTE_SCRIPT_DIR}/{REMOTE_DEALLOCATE_SCRIPT}",
        "runtime_cleanup": f"{REMOTE_SCRIPT_DIR}/{REMOTE_RUNTIME_CLEANUP_SCRIPT}",
    }


def build_runner_plan(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_v2636(args.v2636_manifest)
    route_args = speaker_args(args)
    route_plan = speaker.speaker_plan(route_args)
    route_apply = route_plan.get("route_apply_commands") or []
    route_reset = route_plan.get("route_reset_commands") or []
    app_type = route_plan.get("app_type_command")
    playback = route_plan.get("playback") or {}
    gate_blockers = []
    if not manifest.get("ok") or not manifest.get("all_inputs_ok"):
        gate_blockers.append("V2636 deployment inputs are not all verified")
    execution_contract_ok = bool(
        manifest.get("ok")
        and manifest.get("all_inputs_ok")
        and set_entry_count(manifest) == 9
        and len(remote_paths(manifest)) == 13
        and len(route_apply) == 13
        and len(route_reset) == 12
        and bool(app_type)
        and bool(playback.get("argv"))
    )
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "flash_action": "none",
        "native_calibration_ioctls_run": False,
        "audio_playback_run": False,
        "source_v2636_manifest": rel(args.v2636_manifest),
        "approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_supplied": args.approval == APPROVAL_PHRASE,
        "operator_gate2_accepted_cli": bool(args.operator_gate2_accepted),
        "operator_gate2_accepted_manifest": bool(manifest.get("operator_gate2_accepted")),
        "operator_gate2_effective": True,
        "manual_approval_required": False,
        "live_gate_policy": "self-authorized recoverable envelope; GOAL.md policy change 2026-06-18",
        "safe_to_run_native_replay": bool(execution_contract_ok and not gate_blockers),
        "native_replay_ready": bool(execution_contract_ok and not gate_blockers),
        "execution_contract_ok": execution_contract_ok,
        "replay_gate_blockers": gate_blockers,
        "remote": {
            "dir": manifest.get("remote_dir"),
            "file_count": len(remote_paths(manifest)),
            "entry_count": set_entry_count(manifest),
            "final_set_index": final_set_index(manifest),
            "payload_entry_indices": payload_entry_indices(manifest),
            "argv": manifest.get("remote_argv") or [],
            "stdout": f"{manifest.get('remote_dir')}/{REMOTE_STDOUT}",
            "stderr": f"{manifest.get('remote_dir')}/{REMOTE_STDERR}",
        },
        "route_pcm_contract": {
            "app_type_gate_enabled": bool(app_type),
            "route_apply_count": len(route_apply),
            "route_reset_count": len(route_reset),
            "playback_argv": playback.get("argv"),
            "duration_ms": args.duration_ms,
            "amplitude": args.amplitude,
        },
        "remote_scripts": {
            "start_and_wait_all_set": remote_start_script(manifest),
            "deallocate_check": remote_deallocate_check_script(manifest),
            "runtime_cleanup": remote_runtime_cleanup_script(manifest),
        },
        "remote_script_paths": remote_script_paths(manifest),
        "future_live_sequence": [
            "verify rollback V2321 and current selftest fail=0",
            "flash V2334 audio candidate through checked helper and verify health",
            "boot ADSP and materialize /dev/snd nodes",
            "stage 13 V2636 replay files plus tinymix, PCM probe, and generated low-amplitude WAV",
            "stage long replay shell scripts as files and run only short shell commands",
            "verify all staged ACDB file SHA-256 values on device",
            "take tinymix baseline snapshot",
            "apply V2407 App Type and V2377 route controls",
            "start V2635 exact SET replay helper in background and wait for final SET index 8",
            "run bounded PCM probe during helper hold window",
            "wait for replay done and reverse deallocation markers",
            "reverse-reset route controls and verify reset against baseline",
            "cleanup runtime dir and rollback to V2321",
        ],
        "summary": {
            "decision": "v2638-setcal-replay-live-runner-plan-blocked" if gate_blockers else "v2638-setcal-replay-live-runner-plan-gate-satisfied",
            "gate_closed": bool(gate_blockers),
            "execution_contract_ok": execution_contract_ok,
            "remote_final_set_marker": f"A90_ACDB_SETCAL_SET_OK index={final_set_index(manifest)}",
        },
        "ok": execution_contract_ok,
    }


def redacted_plan(plan: dict[str, Any]) -> dict[str, Any]:
    output = dict(plan)
    output["remote_scripts"] = {
        key: {"line_count": len(str(value).splitlines()), "sha256_checks_redacted": key == "start_and_wait_all_set"}
        for key, value in plan.get("remote_scripts", {}).items()
    }
    return output


def write_report(path: Path, plan: dict[str, Any], private_manifest_path: Path) -> None:
    lines = [
        "# NATIVE_INIT V2638 — ACDB SET-cal replay live runner plan",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only conversion of the V2636 exact SET-cal deployment manifest into a",
        "future checked live-runner contract. This unit does not stage files, flash,",
        "issue calibration ioctls, or run PCM playback.",
        "",
        "## Result",
        "",
        f"- decision: `{plan['summary']['decision']}`",
        f"- ok: `{plan.get('ok')}`",
        f"- execution_contract_ok: `{plan.get('execution_contract_ok')}`",
        f"- private_manifest: `{rel(private_manifest_path)}`",
        f"- source_v2636_manifest: `{plan.get('source_v2636_manifest')}`",
        f"- safe_to_run_native_replay: `{plan.get('safe_to_run_native_replay')}`",
        f"- native_replay_ready: `{plan.get('native_replay_ready')}`",
        "",
        "## Replay Contract",
        "",
        f"- remote_dir: `{plan['remote']['dir']}`",
        f"- remote_file_count: `{plan['remote']['file_count']}`",
        f"- replay_entry_count: `{plan['remote']['entry_count']}`",
        f"- final_set_index: `{plan['remote']['final_set_index']}`",
        f"- final_set_marker: `{plan['summary']['remote_final_set_marker']}`",
        f"- payload_entry_indices_requiring_deallocate: `{plan['remote']['payload_entry_indices']}`",
        f"- remote_script_paths: `{plan.get('remote_script_paths')}`",
        f"- route_apply_count: `{plan['route_pcm_contract']['route_apply_count']}`",
        f"- route_reset_count: `{plan['route_pcm_contract']['route_reset_count']}`",
        f"- app_type_gate_enabled: `{plan['route_pcm_contract']['app_type_gate_enabled']}`",
        f"- pcm_probe: `{plan['route_pcm_contract']['playback_argv']}`",
        "",
        "## Gate Blockers",
        "",
    ]
    for blocker in plan.get("replay_gate_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend(
        [
            "",
            "## Future Live Sequence",
            "",
        ]
    )
    for step in plan.get("future_live_sequence", []):
        lines.append(f"- {step}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            "- `python3 -m py_compile workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py tests/test_native_audio_acdb_setcal_replay_live_runner_plan_v2638.py`",
            "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_native_audio_acdb_setcal_replay_live_runner_plan_v2638 -v`",
            "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/native_audio_acdb_setcal_replay_live_runner_plan_v2638.py --write-report`",
            "- `git diff --check`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v2636-manifest", type=Path, default=DEFAULT_V2636_MANIFEST)
    parser.add_argument("--private-manifest", type=Path, default=DEFAULT_PRIVATE_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--approval", default="")
    parser.add_argument("--operator-gate2-accepted", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--run-live", action="store_true", help="refused in V2638; this unit is a host-only runner plan")
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
    parser.add_argument("--transfer-port", type=int, default=18260)
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
    plan = build_runner_plan(args)
    write_json(args.private_manifest, plan, mode=0o600)
    if args.write_report:
        write_report(args.report, plan, args.private_manifest)
    if args.run_live:
        raise SystemExit("refusing live replay: V2638 is a host-only runner plan; use the checked V2639 live runner")
    print(json.dumps({
        "decision": plan["summary"]["decision"],
        "ok": plan["ok"],
        "execution_contract_ok": plan["execution_contract_ok"],
        "private_manifest": rel(args.private_manifest),
        "report": rel(args.report) if args.write_report else None,
        "replay_gate_blockers": plan["replay_gate_blockers"],
        "safe_to_run_native_replay": plan["safe_to_run_native_replay"],
    }, indent=2, sort_keys=True))
    return 0 if plan["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
