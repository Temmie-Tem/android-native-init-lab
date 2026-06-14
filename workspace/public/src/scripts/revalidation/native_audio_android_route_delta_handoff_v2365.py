#!/usr/bin/env python3
"""V2365/V2369 planner and exact-gated runner for Android speaker route-delta capture.

The default mode is still host-only dry-run.  Live mode is guarded by the exact
AUD-3D2 approval phrase and uses only Android framework AudioTrack playback
through app_process.  It does not run native tinyalsa playback, tinymix set, or
direct /dev/snd access.

The planner converts the V2362 route-delta design into a checked-helper command
plan and exposes live blockers explicitly:

* the private Android boot image must be sealed into a 0600 run-local copy
  before passing it to native_init_flash.py, because the archived candidates are
  group-writable;
* an Android framework playback stimulus dex is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_tinyalsa_inventory_gate_v2346 as tinyalsa


RUN_ID = "V2365"
BUILD_TAG = "v2365-android-route-delta-runner-plan"
LIVE_RUN_ID = "V2369"
LIVE_BUILD_TAG = "v2369-android-route-delta-live-runner"
ROOT = Path(__file__).resolve().parents[5]
ANDROID_BOOT_SHA256 = "c15ce425abb8da41f0b1696d19d05a625fd7cec949b4ae50651a5f1e7293057b"
ANDROID_BOOT_CANDIDATES = (
    ROOT / "workspace/private/backups/baseline_a_20260423_030309/boot.img",
    ROOT / "workspace/private/backups/baseline_a_20260423_025322/boot.img",
)
ROLLBACK_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img"
ROLLBACK_SHA256 = "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"
FLASH_HELPER = ROOT / "workspace/public/src/scripts/revalidation/native_init_flash.py"
REMOTE_DIR = "/data/local/tmp/a90-audio-route-delta"
REMOTE_TINYMIX = f"{REMOTE_DIR}/tinymix"
REMOTE_STIMULUS = f"{REMOTE_DIR}/A90AudioRouteStimulus.dex"
REMOTE_STIMULUS_LOG = f"{REMOTE_DIR}/stimulus.log"
REMOTE_STIMULUS_RC = f"{REMOTE_DIR}/stimulus.rc"
APPROVAL_PHRASE = (
    "AUD-3D2-android-route-delta go: rollbackable Android AudioTrack speaker route-delta "
    "capture, checked-helper boot handoff only, low-amplitude framework playback, "
    "no native speaker write, rollback to V2321"
)
DEFAULT_DURATION_MS = 2000
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_AMPLITUDE = 0.05
DEFAULT_ACTIVE_DELAY_SEC = 0.75
DEFAULT_POST_DELAY_SEC = 1.0
WATCH_CONTROLS = (
    "SEC_TDM_RX_0",
    "WSA_CDC_DMA_RX_0",
    "RX INT7",
    "COMP7",
    "Spkr",
    "SPKR",
    "SLIMBUS_0_RX",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def now_slug() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def default_live_out_dir() -> Path:
    return ROOT / f"workspace/private/runs/audio/v2369-android-route-delta-{now_slug()}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_state(path: Path, *, expected_sha256: str | None = None, android_magic: bool = False) -> dict[str, Any]:
    state: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
    }
    if not path.exists():
        state["ok"] = False
        return state

    stat_result = path.stat()
    state.update({
        "size": stat_result.st_size,
        "mode": oct(stat_result.st_mode & 0o777),
        "group_or_world_writable": bool(stat_result.st_mode & 0o022),
        "sha256": sha256(path),
    })
    if expected_sha256:
        state["expected_sha256"] = expected_sha256
        state["sha256_ok"] = state["sha256"] == expected_sha256
    if android_magic:
        state["android_magic"] = path.read_bytes()[:8] == b"ANDROID!"
    state["ok"] = bool(
        state.get("sha256_ok", True)
        and state.get("android_magic", True)
        and stat_result.st_size > 0
    )
    return state


def select_android_boot_candidate() -> dict[str, Any]:
    candidates = [
        file_state(path, expected_sha256=ANDROID_BOOT_SHA256, android_magic=True)
        for path in ANDROID_BOOT_CANDIDATES
    ]
    selected = next((item for item in candidates if item.get("ok")), None)
    return {
        "candidates": candidates,
        "selected": selected,
        "sealed_copy_required": bool(selected and selected.get("group_or_world_writable")),
        "sealed_copy_plan": "copy selected boot image into the private run dir with mode 0600 before invoking native_init_flash.py",
        "ok": bool(selected),
    }


def host_tool_state() -> dict[str, Any]:
    tools = {name: shutil.which(name) for name in ("javac", "java", "d8", "dx")}
    android_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    android_jars: list[str] = []
    if android_home:
        android_jars = [str(path) for path in sorted(Path(android_home).glob("platforms/*/android.jar"))]
    return {
        "tools": tools,
        "android_home": android_home,
        "android_jar_candidates": android_jars[:5],
        "can_build_audiotrack_dex": bool(tools.get("javac") and (tools.get("d8") or tools.get("dx")) and android_jars),
    }


def stimulus_state(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "exists": False,
            "ok": False,
            "reason": "no --stimulus-dex supplied; V2365 does not generate the AudioTrack dex",
        }
    state = file_state(path)
    dex_magic = bool(state["exists"] and path.read_bytes()[:4] == b"dex\n")
    state["dex_magic"] = dex_magic
    state["ok"] = bool(
        state["exists"]
        and state["size"] > 0
        and not state["group_or_world_writable"]
        and dex_magic
    )
    if not state["ok"]:
        state["reason"] = "stimulus dex must exist, be non-empty, start with dex magic, and not be group/world writable"
    return state


def tinymix_state() -> dict[str, Any]:
    manifest = tinyalsa.verify_manifest(tinyalsa.MANIFEST)
    tool = manifest.get("tools", {}).get("tinymix", {})
    return {
        "manifest": manifest,
        "path": tool.get("path"),
        "sha256": tool.get("sha256"),
        "expected_sha256": tinyalsa.EXPECTED_TOOL_HASHES["tinymix"],
        "ok": bool(manifest.get("ok") and tool.get("sha256_ok") and tool.get("exists")),
    }


def flash_android_command(args: argparse.Namespace, boot_image_for_helper: str) -> list[str]:
    command = [
        "python3",
        rel(FLASH_HELPER),
        boot_image_for_helper,
        "--expect-sha256",
        ANDROID_BOOT_SHA256,
        "--expect-readback-sha256",
        ANDROID_BOOT_SHA256,
        "--expect-android-magic",
        "--post-flash-target",
        "android-adb",
        "--android-root-check",
        "--android-timeout",
        str(args.android_timeout),
    ]
    if args.from_native:
        command.append("--from-native")
    return command


def rollback_command(args: argparse.Namespace, *, from_native: bool = False) -> list[str]:
    command = [
        "python3",
        rel(FLASH_HELPER),
        rel(ROLLBACK_IMAGE),
        "--expect-sha256",
        ROLLBACK_SHA256,
        "--expect-version",
        "0.9.285",
        "--verify-protocol",
        "selftest",
    ]
    if from_native:
        command.append("--from-native")
    return command


def android_reboot_recovery_command(args: argparse.Namespace) -> list[str]:
    return [
        "adb",
        "reboot",
        "recovery",
    ]


def android_shell(command: str) -> list[str]:
    return ["adb", "shell", "su", "-c", command]


def snapshot_plan(label: str) -> list[dict[str, Any]]:
    return [
        {
            "name": f"{label}-tinymix-all-values",
            "kind": "mixer-read",
            "command": android_shell(f"{REMOTE_TINYMIX} -D 0 --all-values"),
        },
        {
            "name": f"{label}-dumpsys-audio",
            "kind": "framework-read",
            "command": android_shell("dumpsys audio"),
        },
        {
            "name": f"{label}-dumpsys-audioflinger",
            "kind": "framework-read",
            "command": android_shell("dumpsys media.audio_flinger"),
        },
        {
            "name": f"{label}-dumpsys-audiopolicy",
            "kind": "framework-read",
            "command": android_shell("dumpsys media.audio_policy"),
        },
        {
            "name": f"{label}-proc-asound",
            "kind": "kernel-read",
            "command": android_shell("cat /proc/asound/cards /proc/asound/pcm"),
        },
    ]


def playback_command(args: argparse.Namespace) -> list[str]:
    return android_shell(
        "CLASSPATH={stimulus} app_process /system/bin A90AudioRouteStimulus "
        "--speaker --duration-ms {duration} --sample-rate {rate} --amplitude {amplitude}".format(
            stimulus=REMOTE_STIMULUS,
            duration=args.duration_ms,
            rate=args.sample_rate,
            amplitude=args.amplitude,
        )
    )


def playback_start_command(args: argparse.Namespace) -> list[str]:
    command = (
        f"cd {shlex.quote(REMOTE_DIR)} && "
        f"rm -f {shlex.quote(REMOTE_STIMULUS_LOG)} {shlex.quote(REMOTE_STIMULUS_RC)} && "
        "("
        f"CLASSPATH={shlex.quote(REMOTE_STIMULUS)} "
        "app_process /system/bin A90AudioRouteStimulus "
        f"--speaker --duration-ms {int(args.duration_ms)} "
        f"--sample-rate {int(args.sample_rate)} "
        f"--amplitude {float(args.amplitude)} "
        f"> {shlex.quote(REMOTE_STIMULUS_LOG)} 2>&1; "
        f"echo $? > {shlex.quote(REMOTE_STIMULUS_RC)}"
        ") &"
    )
    return android_shell(command)


def stimulus_result_commands() -> list[list[str]]:
    return [
        android_shell(f"cat {shlex.quote(REMOTE_STIMULUS_LOG)} 2>/dev/null || true"),
        android_shell(f"cat {shlex.quote(REMOTE_STIMULUS_RC)} 2>/dev/null || true"),
    ]


def command_safety(plan: dict[str, Any]) -> dict[str, Any]:
    flat = json.dumps(plan.get("commands", plan), sort_keys=True)
    forbidden = {
        "native_tinymix_set": " tinymix set ",
        "tinyplay": "tinyplay",
        "native_dev_snd": "/dev/snd",
        "direct_dd": " dd if=",
        "fastboot": "fastboot",
        "wifi": " wifi ",
    }
    findings = [
        {"name": name, "needle": needle}
        for name, needle in forbidden.items()
        if needle in flat
    ]
    return {
        "ok": not findings,
        "findings": findings,
        "allowed_playback_path": "Android framework AudioTrack via app_process stimulus only",
        "forbidden": sorted(forbidden),
    }


def dry_run_payload(args: argparse.Namespace) -> dict[str, Any]:
    boot = select_android_boot_candidate()
    tiny = tinymix_state()
    stimulus = stimulus_state(args.stimulus_dex)
    tools = host_tool_state()
    selected = boot.get("selected") or {}
    sealed_boot = "<private-run-dir>/android_boot_0600.img"
    plan: dict[str, Any] = {
        "run_id": RUN_ID,
        "build_tag": BUILD_TAG,
        "decision": "v2365-android-route-delta-runner-dry-run",
        "device_action": "none",
        "approval_phrase_required": APPROVAL_PHRASE,
        "android_boot": boot,
        "rollback": file_state(ROLLBACK_IMAGE, expected_sha256=ROLLBACK_SHA256),
        "tinymix": tiny,
        "host_audio_stimulus_toolchain": tools,
        "stimulus_dex": stimulus,
        "live_ready": bool(boot.get("ok") and tiny.get("ok") and stimulus.get("ok")),
        "live_blockers": [],
        "commands": {
            "flash_android": flash_android_command(args, sealed_boot),
            "stage": [
                ["adb", "shell", "su", "-c", f"rm -rf {REMOTE_DIR} && mkdir -p {REMOTE_DIR} && chmod 700 {REMOTE_DIR}"],
                ["adb", "push", tiny.get("path") or "<tinymix>", REMOTE_TINYMIX],
                ["adb", "push", rel(args.stimulus_dex) if args.stimulus_dex else "<stimulus-dex>", REMOTE_STIMULUS],
                ["adb", "shell", "su", "-c", f"chmod 700 {REMOTE_TINYMIX} {REMOTE_STIMULUS}"],
            ],
            "baseline_snapshots": snapshot_plan("baseline"),
            "playback": playback_command(args),
            "playback_start_background": playback_start_command(args),
            "playback_result": stimulus_result_commands(),
            "active_snapshots": snapshot_plan("active"),
            "post_snapshots": snapshot_plan("post"),
            "cleanup": [["adb", "shell", "su", "-c", f"rm -rf {REMOTE_DIR}"]],
            "android_reboot_recovery_for_rollback": android_reboot_recovery_command(args),
            "rollback_v2321": rollback_command(args),
        },
        "watch_controls": WATCH_CONTROLS,
        "hard_boundary": [
            "no native tinymix set",
            "no native /dev/snd open/write",
            "no tinyplay",
            "no Wi-Fi/network/credentials",
            "boot partition only through native_init_flash.py",
            "rollback to V2321 after capture",
        ],
    }
    if not stimulus.get("ok"):
        plan["live_blockers"].append(stimulus.get("reason", "stimulus dex unavailable"))
    safety = command_safety(plan)
    plan["command_safety"] = safety
    plan["ok"] = bool(boot.get("ok") and tiny.get("ok") and safety.get("ok"))
    return plan


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def run_step(name: str,
             command: list[str],
             out_dir: Path,
             *,
             timeout_sec: float,
             check: bool = True) -> dict[str, Any]:
    started = time.monotonic()
    record: dict[str, Any] = {
        "name": name,
        "command": command,
        "started_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "timeout_sec": timeout_sec,
    }
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
            check=False,
        )
        stdout_path.write_text(result.stdout)
        stderr_path.write_text(result.stderr)
        record.update({
            "rc": result.returncode,
            "stdout": rel(stdout_path),
            "stderr": rel(stderr_path),
            "elapsed_sec": round(time.monotonic() - started, 3),
            "ok": result.returncode == 0,
        })
        if check and result.returncode != 0:
            raise RuntimeError(f"{name} failed rc={result.returncode}; see {rel(stdout_path)} {rel(stderr_path)}")
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "")
        stderr_path.write_text(exc.stderr or "")
        record.update({
            "timeout": True,
            "elapsed_sec": round(time.monotonic() - started, 3),
            "ok": False,
            "stdout": rel(stdout_path),
            "stderr": rel(stderr_path),
        })
        raise RuntimeError(f"{name} timed out after {timeout_sec}s") from exc
    finally:
        record.setdefault("finished_at", datetime.now(timezone.utc).astimezone().isoformat())
    return record


def copy_sealed_android_boot(selected: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    source = ROOT / selected["path"]
    destination = out_dir / "android_boot_0600.img"
    shutil.copyfile(source, destination)
    os.chmod(destination, 0o600)
    state = file_state(destination, expected_sha256=ANDROID_BOOT_SHA256, android_magic=True)
    if not state.get("ok") or state.get("group_or_world_writable"):
        raise RuntimeError(f"sealed Android boot copy is invalid: {state}")
    return state


def capture_snapshots(label: str, out_dir: Path, args: argparse.Namespace, steps: list[dict[str, Any]]) -> None:
    for item in snapshot_plan(label):
        steps.append(run_step(
            item["name"],
            item["command"],
            out_dir,
            timeout_sec=args.adb_command_timeout,
            check=False,
        ))


def ensure_live_approval(args: argparse.Namespace) -> None:
    if args.approval != APPROVAL_PHRASE:
        raise RuntimeError("exact AUD-3D2 route-delta approval phrase is required for --run-live")


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    ensure_live_approval(args)
    payload = dry_run_payload(args)
    if not payload.get("live_ready"):
        raise RuntimeError(f"live inputs are not ready: {payload.get('live_blockers')}")
    if not payload.get("command_safety", {}).get("ok"):
        raise RuntimeError(f"command safety failed: {payload['command_safety']}")

    out_dir = args.out_dir or default_live_out_dir()
    out_dir.mkdir(parents=True, exist_ok=False)
    os.chmod(out_dir, 0o700)

    steps: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "run_id": LIVE_RUN_ID,
        "build_tag": LIVE_BUILD_TAG,
        "decision": "v2369-android-route-delta-live-started",
        "out_dir": rel(out_dir),
        "approval_ok": True,
        "plan": payload,
        "steps": steps,
        "rolled_back": False,
        "ok": False,
    }
    write_json(out_dir / "result.json", result)

    android_boot_state = copy_sealed_android_boot(payload["android_boot"]["selected"], out_dir)
    result["sealed_android_boot"] = android_boot_state
    write_json(out_dir / "result.json", result)

    rollback_needed = False
    try:
        rollback_needed = True
        steps.append(run_step(
            "flash_android",
            flash_android_command(args, str(out_dir / "android_boot_0600.img")),
            out_dir,
            timeout_sec=args.flash_timeout,
        ))

        for index, command in enumerate(payload["commands"]["stage"]):
            steps.append(run_step(f"stage-{index}", command, out_dir, timeout_sec=args.adb_command_timeout))

        capture_snapshots("baseline", out_dir, args, steps)
        steps.append(run_step(
            "playback-start-background",
            playback_start_command(args),
            out_dir,
            timeout_sec=args.adb_command_timeout,
        ))
        time.sleep(args.active_delay_sec)
        capture_snapshots("active", out_dir, args, steps)
        remaining = max(0.0, (args.duration_ms / 1000.0) - args.active_delay_sec + args.post_delay_sec)
        time.sleep(remaining)
        for index, command in enumerate(stimulus_result_commands()):
            steps.append(run_step(f"playback-result-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))
        capture_snapshots("post", out_dir, args, steps)
        for index, command in enumerate(payload["commands"]["cleanup"]):
            steps.append(run_step(f"cleanup-{index}", command, out_dir, timeout_sec=args.adb_command_timeout, check=False))
        result["decision"] = "v2369-android-route-delta-live-captured-before-rollback"
        result["ok"] = True
        return result
    finally:
        if rollback_needed:
            try:
                steps.append(run_step(
                    "android-reboot-recovery-for-rollback",
                    android_reboot_recovery_command(args),
                    out_dir,
                    timeout_sec=args.adb_command_timeout,
                    check=False,
                ))
                steps.append(run_step(
                    "rollback-v2321",
                    rollback_command(args, from_native=False),
                    out_dir,
                    timeout_sec=args.flash_timeout,
                ))
                result["rolled_back"] = True
            except Exception as first_rollback_error:
                result["rollback_error"] = str(first_rollback_error)
                try:
                    steps.append(run_step(
                        "rollback-v2321-from-native-fallback",
                        rollback_command(args, from_native=True),
                        out_dir,
                        timeout_sec=args.flash_timeout,
                    ))
                    result["rolled_back"] = True
                    result["rollback_fallback"] = "from-native"
                except Exception as second_rollback_error:
                    result["rollback_fallback_error"] = str(second_rollback_error)
                    raise
            finally:
                write_json(out_dir / "result.json", result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="emit the route-delta plan; no device action")
    mode.add_argument("--run-live", action="store_true", help="run the exact-gated Android route-delta capture")
    parser.add_argument("--stimulus-dex", type=Path, help="private AudioTrack stimulus dex for future live use")
    parser.add_argument("--approval", help="exact AUD-3D2 approval phrase required by --run-live")
    parser.add_argument("--out-dir", type=Path, help="private live output directory")
    parser.add_argument("--android-timeout", type=float, default=420.0)
    parser.add_argument("--adb-command-timeout", type=float, default=120.0)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--active-delay-sec", type=float, default=DEFAULT_ACTIVE_DELAY_SEC)
    parser.add_argument("--post-delay-sec", type=float, default=DEFAULT_POST_DELAY_SEC)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.run_live:
        payload = run_live(args)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("ok") and payload.get("rolled_back") else 1

    payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
