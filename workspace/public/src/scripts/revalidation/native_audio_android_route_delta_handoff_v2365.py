#!/usr/bin/env python3
"""V2365 host-only planner for Android speaker route-delta capture.

This does not boot Android and does not play audio.  It converts the V2362
route-delta design into a checked-helper command plan and exposes the remaining
live blockers explicitly:

* the private Android boot image must be sealed into a 0600 run-local copy
  before passing it to native_init_flash.py, because the archived candidates are
  group-writable;
* an Android framework playback stimulus dex/jar is still required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import native_audio_tinyalsa_inventory_gate_v2346 as tinyalsa


RUN_ID = "V2365"
BUILD_TAG = "v2365-android-route-delta-runner-plan"
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
APPROVAL_PHRASE = (
    "AUD-3D2-android-route-delta go: rollbackable Android AudioTrack speaker route-delta "
    "capture, checked-helper boot handoff only, low-amplitude framework playback, "
    "no native speaker write, rollback to V2321"
)
DEFAULT_DURATION_MS = 2000
DEFAULT_SAMPLE_RATE = 48000
DEFAULT_AMPLITUDE = 0.05
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


def rollback_command(args: argparse.Namespace) -> list[str]:
    return [
        "python3",
        rel(FLASH_HELPER),
        rel(ROLLBACK_IMAGE),
        "--expect-sha256",
        ROLLBACK_SHA256,
        "--expect-version",
        "0.9.285",
        "--verify-protocol",
        "selftest",
        "--from-native",
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
            "active_snapshots": snapshot_plan("active"),
            "post_snapshots": snapshot_plan("post"),
            "cleanup": [["adb", "shell", "su", "-c", f"rm -rf {REMOTE_DIR}"]],
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", default=True, help="emit the route-delta plan; no device action")
    parser.add_argument("--stimulus-dex", type=Path, help="private AudioTrack stimulus dex for future live use")
    parser.add_argument("--android-timeout", type=float, default=420.0)
    parser.add_argument("--duration-ms", type=int, default=DEFAULT_DURATION_MS)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--amplitude", type=float, default=DEFAULT_AMPLITUDE)
    parser.add_argument("--from-native", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = dry_run_payload(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
