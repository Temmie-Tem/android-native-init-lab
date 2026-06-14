#!/usr/bin/env python3
"""V2349 exact-gated live runner for read-only tinyalsa inventory.

This is not playback.  The live path first reproduces the proven V2335/V2348
ADSP + /dev/snd materialization window, then installs the pinned V2345 tinyalsa
query tools into a runtime cache directory and runs read-only inventory commands
only.  It must not run tinyplay, write PCM, set mixer controls, invoke the audio
HAL, or touch adsprpc.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_snd_nodes_preflight_handoff_v2335 as snd
import native_audio_tinyalsa_inventory_gate_v2346 as inv

RUN_ID = "V2349"
BUILD_TAG = "v2349-audio-tinyalsa-inventory-live"
APPROVAL_PHRASE = inv.REQUIRED_APPROVAL_PHRASE
REMOTE_DIR = "/cache/a90-audio/v2349-tinyalsa-inventory"
REMOTE_TOOLS = {
    "tinymix": f"{REMOTE_DIR}/tinymix",
    "tinypcminfo": f"{REMOTE_DIR}/tinypcminfo",
}
TCPCTL_HOST = snd.ROOT / "workspace/public/src/scripts/revalidation/tcpctl_host.py"


def rel(path: Path) -> str:
    return snd.rel(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def write_json(path: Path, payload: Any) -> None:
    snd.write_json(path, payload)


def stdout_of(step: dict[str, Any]) -> str:
    return snd.stdout_of(step)


def verify_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise SystemExit(
            "refusing live run: exact --approval phrase required:\n"
            f"{APPROVAL_PHRASE}"
        )


def tool_local_path(manifest_state: dict[str, Any], tool: str) -> Path:
    path_text = manifest_state["tools"][tool]["path"]
    path = snd.ROOT / path_text
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def tcpctl_common(args: argparse.Namespace, *, target_binary: str | None = None) -> list[str]:
    command = [
        "python3",
        rel(TCPCTL_HOST),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--device-ip",
        args.device_ip,
        "--tcp-port",
        str(args.tcp_port),
        "--bridge-timeout",
        str(args.command_timeout),
        "--tcp-timeout",
        str(args.tcp_timeout),
    ]
    if target_binary:
        command.extend(["--device-binary", target_binary])
    return command


def install_command(args: argparse.Namespace, local_path: Path, target_path: str, transfer_port: int) -> list[str]:
    return [
        *tcpctl_common(args, target_binary=target_path),
        "install",
        "--install-control-channel",
        "tcpctl",
        "--local-binary",
        rel(local_path),
        "--transfer-port",
        str(transfer_port),
        "--transfer-timeout",
        str(args.transfer_timeout),
        "--transfer-delay",
        str(args.transfer_delay),
    ]


def tcpctl_run_command(args: argparse.Namespace, argv: list[str]) -> list[str]:
    return [*tcpctl_common(args), "run", "--", *argv]


def planned_inventory_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
    commands = [
        {
            "name": "tinymix-list-card0",
            "kind": "mixer-list",
            "allow_error": False,
            "argv": [REMOTE_TOOLS["tinymix"], "-D", str(args.card)],
        },
        {
            "name": "tinymix-list-card0-all-values",
            "kind": "mixer-list-detail",
            "allow_error": False,
            "argv": [REMOTE_TOOLS["tinymix"], "-D", str(args.card), "--all-values"],
        },
    ]
    for device in args.pcm_device:
        commands.append({
            "name": f"tinypcminfo-card{args.card}-device{device}",
            "kind": "pcm-params-query",
            "allow_error": bool(args.allow_pcm_query_error),
            "argv": [REMOTE_TOOLS["tinypcminfo"], "-D", str(args.card), "-d", str(device)],
        })
    return commands


def command_safety(commands: list[dict[str, Any]]) -> dict[str, Any]:
    as_v2346 = []
    for item in commands:
        as_v2346.append({
            "name": item["name"],
            "argv": item["argv"],
            "mutates_audio_state": False,
            "opens_alsa": True,
        })
    return inv.command_safety(as_v2346)


def preflight_state(args: argparse.Namespace) -> dict[str, Any]:
    snd_state = snd.preflight_state()
    manifest = inv.verify_manifest(args.manifest)
    commands = planned_inventory_commands(args)
    safety = command_safety(commands)
    return {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "approval_phrase_required": APPROVAL_PHRASE,
        "snd_materialization_preflight": snd_state,
        "tinyalsa_manifest": manifest,
        "inventory_commands": commands,
        "command_safety": safety,
        "remote_dir": REMOTE_DIR,
        "remote_tools": REMOTE_TOOLS,
        "ok": bool(snd.preflight_ok(snd_state) and manifest.get("ok") and safety.get("ok") and TCPCTL_HOST.exists()),
        "hard_boundary": [
            "no tinyplay",
            "no PCM playback/write",
            "no tinymix control/value operands",
            "no audio HAL",
            "no adsprpc invoke/ioctl",
            "rollback to V2321 after inventory",
        ],
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    state = preflight_state(args)
    materialize_plan = snd.dry_run_plan(state["snd_materialization_preflight"])
    install_steps = []
    if state["tinyalsa_manifest"].get("ok"):
        for index, tool in enumerate(("tinymix", "tinypcminfo"), start=0):
            local_path = tool_local_path(state["tinyalsa_manifest"], tool)
            install_steps.append({
                "tool": tool,
                "command": install_command(args, local_path, REMOTE_TOOLS[tool], args.transfer_port + index),
            })
    inventory_steps = [
        {"name": item["name"], "command": tcpctl_run_command(args, item["argv"]), "allow_error": item["allow_error"]}
        for item in state["inventory_commands"]
    ]
    return {
        "decision": "v2349-audio-tinyalsa-inventory-live-dry-run" if state["ok"] else "v2349-audio-tinyalsa-inventory-live-blocked",
        "ok": bool(state["ok"]),
        "device_action": "none",
        "approval_phrase_required": APPROVAL_PHRASE,
        "preflight": state,
        "materialization_plan": materialize_plan,
        "tool_install_plan": install_steps,
        "inventory_plan": inventory_steps,
    }


def run_host_step(out_dir: Path,
                  steps: list[dict[str, Any]],
                  name: str,
                  command: list[str],
                  *,
                  timeout: float,
                  allow_error: bool = False) -> dict[str, Any]:
    return snd.run_step(out_dir, steps, name, command, timeout=timeout, allow_error=allow_error)


def run_inventory(args: argparse.Namespace,
                  out_dir: Path,
                  steps: list[dict[str, Any]],
                  manifest_state: dict[str, Any]) -> dict[str, Any]:
    inventory_result: dict[str, Any] = {
        "installed_tools": {},
        "commands": [],
        "tinyplay_used": False,
        "mixer_set_attempted": False,
        "playback_attempted": False,
    }
    for index, tool in enumerate(("tinymix", "tinypcminfo"), start=0):
        local_path = tool_local_path(manifest_state, tool)
        step = run_host_step(
            out_dir,
            steps,
            f"install-{tool}",
            install_command(args, local_path, REMOTE_TOOLS[tool], args.transfer_port + index),
            timeout=args.transfer_timeout + 45.0,
        )
        inventory_result["installed_tools"][tool] = {
            "remote": REMOTE_TOOLS[tool],
            "ok": bool(step.get("ok")),
            "stdout_path": step.get("stdout_path"),
        }

    for item in planned_inventory_commands(args):
        step = run_host_step(
            out_dir,
            steps,
            item["name"],
            tcpctl_run_command(args, item["argv"]),
            timeout=args.inventory_timeout,
            allow_error=bool(item.get("allow_error")),
        )
        inventory_result["commands"].append({
            "name": item["name"],
            "kind": item["kind"],
            "argv": item["argv"],
            "ok": bool(step.get("ok")),
            "rc": step.get("rc"),
            "allow_error": bool(item.get("allow_error")),
            "stdout_path": step.get("stdout_path"),
        })
    return inventory_result


def live_run(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    verify_live_approval(args)
    if not state.get("ok"):
        raise SystemExit("refusing live run: tinyalsa/materialization preflight failed")

    out_dir = snd.ROOT / f"workspace/private/runs/audio/v2349-tinyalsa-inventory-{now_slug()}"
    out_dir.mkdir(parents=True, exist_ok=False)
    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "decision": "v2349-audio-tinyalsa-inventory-live-started",
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
        current_selftest = snd.run_a90ctl_observation(
            args, out_dir, steps, "preflight-current-selftest", ["selftest", "verbose"], timeout=120.0
        )
        if not snd.selftest_ok(stdout_of(current_selftest)):
            raise RuntimeError("resident preflight selftest did not report fail=0")

        run_host_step(
            out_dir,
            steps,
            "flash-v2334-candidate",
            snd.flash_command(snd.CANDIDATE_IMAGE, snd.CANDIDATE_VERSION, snd.CANDIDATE_SHA256, from_native=True),
            timeout=args.flash_timeout,
        )
        candidate_flashed = True

        version = snd.run_a90ctl_observation(args, out_dir, steps, "candidate-version", ["version"], timeout=90.0)
        if snd.CANDIDATE_VERSION not in stdout_of(version):
            raise RuntimeError("candidate version output did not contain expected version")
        snd.run_a90ctl_observation(args, out_dir, steps, "candidate-status", ["status"], timeout=90.0)
        candidate_selftest = snd.run_a90ctl_observation(
            args, out_dir, steps, "candidate-selftest", ["selftest", "verbose"], timeout=120.0
        )
        if not snd.selftest_ok(stdout_of(candidate_selftest)):
            raise RuntimeError("candidate selftest did not report fail=0")

        pre_adsp = snd.run_a90ctl_observation(
            args, out_dir, steps, "candidate-audio-adsp-status-before", ["audio", "adsp-status"], timeout=90.0
        )
        pre_snd = snd.run_a90ctl_observation(
            args, out_dir, steps, "candidate-audio-snd-status-before", ["audio", "snd-status"], timeout=90.0
        )
        result["initial_audio"] = snd.classify_audio_status(stdout_of(pre_adsp) + "\n" + stdout_of(pre_snd))

        if not (result["initial_audio"]["has_audio_card"] and result["initial_audio"]["has_sound_class_control"]):
            snd.run_menu_settle_step(out_dir, steps, "settle-before-adsp-boot-once", args)
            snd.run_serial_transport_step(
                out_dir,
                steps,
                "candidate-adsp-boot-once",
                args,
                ["audio", "adsp-boot-once", snd.ADSP_TOKEN],
                timeout=90.0,
                retry_observation=False,
            )

        result["card_wait"] = snd.wait_for_audio_card(args, out_dir, steps)
        before_materialize = snd.run_a90ctl_observation(
            args, out_dir, steps, "snd-status-before-materialize", ["audio", "snd-status"], timeout=90.0
        )
        result["before_materialize"] = snd.classify_audio_status(stdout_of(before_materialize))
        snd.run_menu_settle_step(out_dir, steps, "settle-before-snd-materialize-once", args)
        materialize = snd.run_serial_transport_step(
            out_dir,
            steps,
            "snd-materialize-once",
            args,
            ["audio", "snd-materialize-once", snd.SND_TOKEN],
            timeout=90.0,
            retry_observation=False,
        )
        result["materialize_tail"] = stdout_of(materialize)[-4000:]
        after_materialize = snd.run_a90ctl_observation(
            args, out_dir, steps, "snd-status-after-materialize", ["audio", "snd-status"], timeout=90.0
        )
        after = snd.classify_audio_status(stdout_of(after_materialize))
        result["after_materialize"] = after
        if not (after["has_dev_snd_control"] and after["has_dev_snd_pcm"]):
            raise RuntimeError("materialization did not produce control+pcm /dev/snd nodes")

        result["tinyalsa_inventory"] = run_inventory(args, out_dir, steps, state["tinyalsa_manifest"])

        final_candidate_selftest = snd.run_a90ctl_observation(
            args, out_dir, steps, "candidate-selftest-after-inventory", ["selftest", "verbose"], timeout=120.0
        )
        if not snd.selftest_ok(stdout_of(final_candidate_selftest)):
            raise RuntimeError("candidate final selftest did not report fail=0")
        result["decision"] = "v2349-tinyalsa-inventory-live-pass-before-rollback"
    finally:
        if candidate_flashed:
            rollback_record = run_host_step(
                out_dir,
                steps,
                "rollback-v2321",
                snd.flash_command(snd.ROLLBACK_IMAGE, snd.ROLLBACK_VERSION, snd.ROLLBACK_SHA256, from_native=True),
                timeout=args.flash_timeout,
                allow_error=True,
            )
            result["rolled_back"] = bool(rollback_record.get("ok"))
            try:
                rollback_version = snd.run_a90ctl_observation(args, out_dir, steps, "rollback-version", ["version"], timeout=90.0)
                rollback_selftest = snd.run_a90ctl_observation(
                    args, out_dir, steps, "rollback-selftest", ["selftest", "verbose"], timeout=120.0
                )
                result["rollback_version_ok"] = snd.ROLLBACK_VERSION in stdout_of(rollback_version)
                result["rollback_selftest_fail0"] = snd.selftest_ok(stdout_of(rollback_selftest))
            except Exception as exc:  # noqa: BLE001
                result["rollback_health_error"] = str(exc)
        write_json(out_dir / "result.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="verify local artifacts and print the live plan; no bridge/flash")
    mode.add_argument("--run-live", action="store_true", help="perform the exact-gated read-only tinyalsa inventory run")
    parser.add_argument("--approval", default="", help="exact operator phrase required with --run-live")
    parser.add_argument("--manifest", type=Path, default=inv.MANIFEST)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--tcp-port", type=int, default=2325)
    parser.add_argument("--command-timeout", type=float, default=60.0)
    parser.add_argument("--tcp-timeout", type=float, default=30.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--card-timeout", type=float, default=70.0)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    parser.add_argument("--menu-settle-sec", type=float, default=1.0)
    parser.add_argument("--transfer-port", type=int, default=18149)
    parser.add_argument("--transfer-delay", type=float, default=1.0)
    parser.add_argument("--transfer-timeout", type=float, default=120.0)
    parser.add_argument("--inventory-timeout", type=float, default=60.0)
    parser.add_argument("--card", type=int, default=0)
    parser.add_argument("--pcm-device", type=int, action="append", default=[0])
    parser.add_argument("--allow-pcm-query-error", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = preflight_state(args)
    if args.dry_run:
        print(json.dumps(dry_run_payload(args), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if state.get("ok") else 2
    result = live_run(args, copy.deepcopy(state))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("decision") == "v2349-tinyalsa-inventory-live-pass-before-rollback" else 1


if __name__ == "__main__":
    raise SystemExit(main())
