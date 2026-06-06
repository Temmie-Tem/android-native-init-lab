#!/usr/bin/env python3
"""Read-only rescue-state classifier for Android capture handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v305-android-capture-rescue-doctor")
DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 54321
DEFAULT_NATIVE_IMAGE = Path("stage3/boot_linux_v261.img")
EXPECTED_NATIVE_VERSION = "A90 Linux init 0.9.60 (v261)"
LIVE_GUARD_MANIFEST = Path("tmp/wifi/v304-android-capture-live-guard-final/manifest.json")
FALLBACK_LIVE_COMMAND = (
    "python3 scripts/revalidation/android_capture_handoff_execute.py "
    "--out-dir tmp/wifi/v300-android-capture-executor-live "
    "--allow-android-boot-flash --assume-yes --i-understand-native-rollback run"
)


@dataclass
class Probe:
    name: str
    ok: bool
    detail: str
    text: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=float, default=5.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def run_process(command: list[str], timeout: float) -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - rescue evidence preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def parse_adb_devices(text: str) -> list[dict[str, str]]:
    devices: list[dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"serial": parts[0], "state": parts[1], "line": line})
    return devices


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def bridge_probe(args: argparse.Namespace) -> Probe:
    payload = b"\ncmdv1 version\n"
    data = bytearray()
    try:
        with socket.create_connection((args.bridge_host, args.bridge_port), timeout=min(args.timeout, 3.0)) as sock:
            sock.settimeout(0.5)
            sock.sendall(payload)
            deadline = time.monotonic() + args.timeout
            while time.monotonic() < deadline:
                try:
                    chunk = sock.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    break
                data.extend(chunk)
                if b"A90P1 END" in data or b"[err]" in data:
                    break
    except OSError as exc:
        return Probe("bridge-version", False, str(exc), "")
    text = data.decode("utf-8", errors="replace")
    ok = EXPECTED_NATIVE_VERSION in text and "A90P1 END" in text and "status=ok" in text
    return Probe("bridge-version", ok, "native version matched" if ok else "native version not confirmed", text)


def adb_probe(args: argparse.Namespace) -> tuple[Probe, list[dict[str, str]]]:
    command = [args.adb, "devices", "-l"]
    rc, text, error, _ = run_process(command, args.timeout)
    devices = parse_adb_devices(text)
    detail = f"rc={rc} devices={len(devices)}"
    if error:
        detail += f" error={error}"
    return Probe("adb-devices", rc == 0, detail, text if text else error), devices


def load_live_command() -> str:
    manifest_path = repo_path(LIVE_GUARD_MANIFEST)
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        command = str(payload.get("live_command") or "")
        if command:
            return command
    return FALLBACK_LIVE_COMMAND


def build_commands(args: argparse.Namespace, decision: str, devices: list[dict[str, str]]) -> dict[str, str]:
    serial_arg = f" --serial {shlex.quote(args.serial)}" if args.serial else ""
    commands: dict[str, str] = {}
    commands["live-handoff"] = load_live_command()
    commands["native-rollback"] = (
        "python3 scripts/revalidation/native_init_flash.py "
        f"{shlex.quote(str(DEFAULT_NATIVE_IMAGE))}"
        f"{serial_arg} "
        f"--expect-version {shlex.quote(EXPECTED_NATIVE_VERSION)} "
        "--verify-protocol auto"
    )
    commands["android-capture"] = (
        "python3 scripts/revalidation/wifi_android_property_capture.py "
        "--out-dir tmp/wifi/v297-android-property-capture-android"
        f"{serial_arg} run && "
        "python3 scripts/revalidation/wifi_property_baseline_compare.py "
        "--out-dir tmp/wifi/v298-property-baseline-compare-android run && "
        "python3 scripts/revalidation/android_capture_postprocess.py "
        "--out-dir tmp/wifi/v303-android-capture-postprocess-after-live run"
    )
    if decision == "ambiguous-multiple-adb":
        commands["select-serial"] = "adb devices -l # choose one serial, then rerun doctor with --serial <serial>"
        for index, device in enumerate(devices, start=1):
            commands[f"candidate-{index}"] = f"python3 scripts/revalidation/android_capture_rescue_doctor.py --serial {shlex.quote(device['serial'])} run"
    return commands


def decide(bridge: Probe, devices: list[dict[str, str]], serial: str) -> tuple[str, bool, str]:
    if bridge.ok:
        return "native-ready", True, "native bridge is reachable and reports expected v261"
    if len(devices) > 1 and not serial:
        return "ambiguous-multiple-adb", True, "multiple ADB devices are present; choose --serial before any action"
    if not devices:
        return "disconnected", True, "no native bridge and no ADB devices detected"
    states = {device["state"] for device in devices}
    if "recovery" in states:
        return "recovery-ready-to-restore", True, "TWRP/recovery ADB is present; native rollback command is appropriate"
    if "device" in states:
        return "android-ready-for-capture", True, "Android ADB is present; capture/compare/postprocess path is appropriate"
    return "unknown", True, "ADB devices are present but not in recovery/device state: " + ", ".join(sorted(states))


def render_summary(manifest: dict[str, Any]) -> str:
    device_rows = [[item["serial"], item["state"], item["line"]] for item in manifest["adb_devices"]]
    probe_rows = [[item["name"], "ok" if item["ok"] else "fail", item["detail"]] for item in manifest["probes"]]
    command_rows = [[name, command] for name, command in manifest["commands"].items()]
    return "\n".join([
        "# v305 Android Capture Rescue Doctor",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        "",
        "## Probes",
        "",
        markdown_table(["probe", "status", "detail"], probe_rows),
        "",
        "## ADB Devices",
        "",
        markdown_table(["serial", "state", "line"], device_rows if device_rows else [["none", "-", "-"]]),
        "",
        "## Recommended Commands",
        "",
        markdown_table(["name", "command"], command_rows),
        "",
        "## Safety Boundary",
        "",
        "- This tool does not execute any recommended command.",
        "- Commands that write boot or reboot still require explicit operator approval.",
        "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    bridge = bridge_probe(args)
    adb, devices = adb_probe(args)
    decision, pass_ok, reason = decide(bridge, devices, args.serial)
    commands = build_commands(args, decision, devices)
    for name, command in commands.items():
        store.write_text(f"commands/{name}.txt", command + "\n")
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "probes": [asdict(bridge), asdict(adb)],
        "adb_devices": devices,
        "commands": commands,
        "blocked_actions": [
            "execute recommended commands automatically",
            "reboot/recovery/flash",
            "boot partition write",
            "property mutation",
            "service-manager/HAL/Wi-Fi daemon execution",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
