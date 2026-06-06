#!/usr/bin/env python3
"""V833 Android service-notifier positive-control collector.

This runner is intended to execute only while Android ADB is available. It
pushes a small static helper, sends one bounded service-notifier
REGISTER_LISTENER request for `msm/modem/wlan_pd`, captures the response, and
removes the helper. It does not enable Wi-Fi, scan, connect, use credentials,
request DHCP, alter routes, ping externally, or start/stop Android services.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v833-android-servnotif-positive-control")
LATEST_POINTER = Path("tmp/wifi/latest-v833-android-servnotif-positive-control.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v833-servnotif-helper-build/a90_servnotif_listener_probe")
DEFAULT_HELPER_SHA256 = "0d0cc09d4b23b53b0797d9daac1d134b3fc02aa0c38b891ac0d9af8432078981"
DEFAULT_REMOTE_HELPER = "/data/local/tmp/a90_servnotif_listener_probe_v1"
HELPER_MARKER = "a90_servnotif_listener_probe v1"

SENSITIVE_REPLACEMENTS = (
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<mac>"),
    (re.compile(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)"), r"\1=<redacted>"),
    (re.compile(r"(?i)(ssid|bssid|p" r"sk|pass" r"word|passphrase)=([^\s]+)"), r"\1=<redacted>"),
)


@dataclass(frozen=True)
class Capture:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--readback-ms", type=int, default=10000)
    parser.add_argument("--response-ms", type=int, default=15000)
    parser.add_argument("--no-su", action="store_true")
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def redact(text: str) -> str:
    redacted = text
    for pattern, replacement in SENSITIVE_REPLACEMENTS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def display_command(command: list[str]) -> str:
    redacted = ["<adb-serial>" if index > 0 and command[index - 1] == "-s" else part for index, part in enumerate(command)]
    return shlex.join(redacted)


def adb_shell(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.no_su:
        return [*adb_base(args), "shell", shell_command]
    return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell_command)]


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
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence preserves failure details
        return None, "", str(exc), time.monotonic() - started


def write_capture(store: EvidenceStore, name: str, command: list[str], rc: int | None, text: str, error: str, duration: float) -> Capture:
    body = f"$ {display_command(command)}\n{redact(text if text else error).rstrip()}\nrc={rc}\n"
    path = store.write_text(f"android/commands/{name}.txt", body)
    return Capture(name, display_command(command), rc == 0, rc, duration, str(path.relative_to(store.run_dir)), error)


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: float) -> tuple[Capture, str]:
    rc, text, error, duration = run_process(command, timeout)
    capture = write_capture(store, name, command, rc, text, error, duration)
    return capture, redact(text if text else error)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    helper_path = repo_path(args.local_helper)
    info: dict[str, Any] = {
        "path": str(helper_path),
        "exists": helper_path.exists(),
        "size": helper_path.stat().st_size if helper_path.exists() else 0,
        "sha256": "",
        "sha256_match": False,
        "marker": False,
    }
    if not helper_path.exists():
        return info
    info["sha256"] = sha256_file(helper_path)
    info["sha256_match"] = info["sha256"] == args.helper_sha256
    try:
        result = subprocess.run(
            ["strings", str(helper_path)],
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        info["marker"] = HELPER_MARKER in result.stdout
    except Exception:
        info["marker"] = False
    return info


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.startswith("servnotif."):
            values[key] = value
    return values


def canonical_state_name(output: dict[str, str], key_prefix: str) -> str:
    name = output.get(f"{key_prefix}_name", "")
    raw_value = output.get(key_prefix, "")
    if name not in {"", "unknown", "other"}:
        return name
    return {
        "0x0fffffff": "down",
        "0x1fffffff": "up",
        "0x2fffffff": "early-down",
        "0x7fffffff": "uninit",
    }.get(raw_value.lower(), name or "unknown")


def adb_devices(args: argparse.Namespace, store: EvidenceStore) -> tuple[Capture, dict[str, Any]]:
    capture, text = capture_command(store, "adb-devices", [*adb_base(args), "devices", "-l"], args.timeout)
    devices: list[str] = []
    for raw_line in text.splitlines()[1:]:
        parts = raw_line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return capture, {
        "devices": devices,
        "device_count": len(devices),
        "selected_available": args.serial in devices if args.serial else len(devices) == 1,
    }


def build_plan(args: argparse.Namespace) -> list[list[str]]:
    helper = str(repo_path(args.local_helper))
    run_helper = (
        f"{shlex.quote(args.remote_helper)} "
        f"--allow-service-notifier-listener-probe "
        f"--readback-ms {int(args.readback_ms)} "
        f"--response-ms {int(args.response_ms)}"
    )
    return [
        [*adb_base(args), "devices", "-l"],
        [*adb_base(args), "shell", "getprop sys.boot_completed"],
        [*adb_base(args), "push", helper, args.remote_helper],
        [*adb_base(args), "shell", f"chmod 700 {shlex.quote(args.remote_helper)}"],
        adb_shell(args, run_helper),
        adb_shell(args, f"rm -f {shlex.quote(args.remote_helper)}"),
    ]


def run_android_probe(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[Capture], dict[str, Any]]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    device_capture, devices = adb_devices(args, store)
    captures.append(device_capture)
    plan = build_plan(args)
    details: dict[str, Any] = {"devices": devices, "helper_output": {}, "boot_completed": False}

    boot_capture, boot_text = capture_command(store, "boot-completed", [*adb_base(args), "shell", "getprop", "sys.boot_completed"], args.timeout)
    captures.append(boot_capture)
    details["boot_completed"] = boot_text.strip() == "1"
    if not devices["selected_available"] or not details["boot_completed"]:
        return captures, details

    push_capture, _ = capture_command(store, "push-helper", plan[2], max(args.timeout, 120.0))
    captures.append(push_capture)
    chmod_capture, _ = capture_command(store, "chmod-helper", plan[3], args.timeout)
    captures.append(chmod_capture)
    helper_capture, helper_text = capture_command(store, "servnotif-helper", plan[4], max(args.timeout, (args.readback_ms + args.response_ms) / 1000.0 + 20.0))
    captures.append(helper_capture)
    details["helper_output"] = parse_key_values(helper_text)
    cleanup_capture, _ = capture_command(store, "cleanup-helper", plan[5], args.timeout)
    captures.append(cleanup_capture)
    dmesg_command = adb_shell(
        args,
        "dmesg 2>/dev/null | grep -Ei 'service-notifier|wlan_pd|WLFW|BDF|wlan0|icnss_qmi' | tail -n 160 || true",
    )
    dmesg_capture, _ = capture_command(store, "readiness-dmesg-tail", dmesg_command, max(args.timeout, 60.0))
    captures.append(dmesg_capture)
    return captures, details


def decide(args: argparse.Namespace, helper: dict[str, Any], details: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v833-android-servnotif-positive-control-plan-ready",
            True,
            "plan-only; no ADB mutation or QMI payload executed",
            "run preflight while Android is available or execute the V833 handoff wrapper",
        )
    if not helper["exists"] or not helper["sha256_match"] or not helper["marker"]:
        return (
            "v833-android-servnotif-positive-control-helper-blocked",
            False,
            "local helper is missing, has unexpected hash, or lacks the expected marker",
            "build the V833 helper before Android collection",
        )
    if args.command == "preflight":
        if not details or not details["devices"]["selected_available"]:
            return (
                "v833-android-servnotif-positive-control-adb-blocked",
                False,
                "Android ADB device is not uniquely available",
                "boot Android or run the handoff wrapper",
            )
        if not details["boot_completed"]:
            return (
                "v833-android-servnotif-positive-control-boot-blocked",
                False,
                "Android sys.boot_completed is not 1",
                "wait for Android boot completion before run",
            )
        return (
            "v833-android-servnotif-positive-control-preflight-ready",
            True,
            "Android ADB and helper are ready; run remains bounded to one listener request",
            "run V833 Android positive-control collector",
        )
    if not details or not details["devices"]["selected_available"]:
        return (
            "v833-android-servnotif-positive-control-adb-blocked",
            False,
            "Android ADB device is not uniquely available",
            "boot Android or inspect ADB",
        )
    if not details["boot_completed"]:
        return (
            "v833-android-servnotif-positive-control-boot-blocked",
            False,
            "Android boot-complete was not observed",
            "wait or rerun through the handoff wrapper",
        )
    output = details.get("helper_output") or {}
    response_name = canonical_state_name(output, "servnotif.response_curr_state")
    indication_name = canonical_state_name(output, "servnotif.indication_curr_state")
    endpoint_found = output.get("servnotif.endpoint.found") == "1"
    response_seen = output.get("servnotif.response_seen") == "1"
    response_success = output.get("servnotif.response_success") == "1"
    if response_name == "up" or indication_name == "up":
        return (
            "v833-android-servnotif-positive-control-state-up",
            True,
            "Android positive control returned or indicated wlan_pd UP",
            "classify native-only lower-state gap before more native retries",
        )
    if response_seen and response_success and response_name:
        return (
            f"v833-android-servnotif-positive-control-state-{response_name}",
            True,
            f"Android positive control completed but state is {response_name}",
            "fix listener payload/model before using native uninit as lower-state proof",
        )
    if endpoint_found and not response_seen:
        return (
            "v833-android-servnotif-positive-control-no-response",
            False,
            "service-notifier endpoint was visible but listener response was not received",
            "inspect helper transcript and Android service-notifier availability",
        )
    return (
        "v833-android-servnotif-positive-control-no-endpoint",
        False,
        "service-notifier endpoint was not visible on Android",
        "inspect Android QRTR/service-notifier state before native comparison",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    capture_rows = [
        [capture["name"], "ok" if capture["ok"] else "fail", str(capture["rc"]), f"{capture['duration_sec']:.3f}s", capture["file"]]
        for capture in manifest["captures"]
    ]
    output = manifest["android"].get("helper_output") or {}
    canonical = manifest["android"].get("canonical_state") or {}
    selected_keys = [
        "servnotif.endpoint.found",
        "servnotif.endpoint.node",
        "servnotif.endpoint.port",
        "servnotif.response_seen",
        "servnotif.response_success",
        "servnotif.response_curr_state_name",
        "servnotif.indication_seen",
        "servnotif.indication_curr_state_name",
        "servnotif.ack_sent",
        "servnotif.ack_success",
    ]
    return "\n".join([
        "# V833 Android Service-notifier Positive-control",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Helper",
        "",
        markdown_table(["path", "exists", "sha256 match", "marker"], [[
            manifest["helper"]["path"],
            manifest["helper"]["exists"],
            manifest["helper"]["sha256_match"],
            manifest["helper"]["marker"],
        ]]),
        "",
        "## Captures",
        "",
        markdown_table(["name", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["none", "-", "-", "-", "-"]]),
        "",
        "## Service-notifier Result",
        "",
        markdown_table(["key", "value"], [[key, output.get(key, "-")] for key in selected_keys]),
        "",
        "## Canonical State",
        "",
        markdown_table(["key", "value"], [[key, value] for key, value in canonical.items()]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    helper = local_helper_info(args)
    captures: list[Capture] = []
    details: dict[str, Any] = {"devices": {}, "boot_completed": False, "helper_output": {}}
    if args.command in {"preflight", "run"}:
        if args.command == "preflight":
            store.mkdir("android/commands")
            device_capture, devices = adb_devices(args, store)
            captures.append(device_capture)
            boot_capture, boot_text = capture_command(store, "boot-completed", [*adb_base(args), "shell", "getprop", "sys.boot_completed"], args.timeout)
            captures.append(boot_capture)
            details = {"devices": devices, "boot_completed": boot_text.strip() == "1", "helper_output": {}}
        else:
            captures, details = run_android_probe(args, store)
    decision, ok, reason, next_step = decide(args, helper, details)
    output = details.get("helper_output") or {}
    details["canonical_state"] = {
        "response": canonical_state_name(output, "servnotif.response_curr_state"),
        "indication": canonical_state_name(output, "servnotif.indication_curr_state"),
    }
    manifest: dict[str, Any] = {
        "cycle": "v833",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "helper": helper,
        "android": details,
        "captures": [asdict(capture) if isinstance(capture, Capture) else capture for capture in captures],
        "device_commands_executed": args.command in {"preflight", "run"},
        "device_mutations": args.command == "run",
        "qmi_payload_executed": args.command == "run" and bool((details.get("helper_output") or {}).get("servnotif.probe.qmi_payload") == "1"),
        "wifi_bringup_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "service_manager_start_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
