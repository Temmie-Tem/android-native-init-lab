#!/usr/bin/env python3
"""Capture read-only Android-boot property baseline evidence over ADB."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v297-android-property-capture")
REQUIRED_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)
FILTER_TERMS = (
    "wifi",
    "wlan",
    "cnss",
    "qcom",
    "qca",
    "vndk",
    "vendor",
    "product",
    "hardware",
)
SHELL_CAPTURES: tuple[tuple[str, str, int], ...] = (
    ("all-getprop", "getprop", 30),
    (
        "required-props",
        "for p in ro.build.version.sdk ro.product.name ro.hardware ro.vendor.build.version.sdk; "
        "do echo \"$p=$(getprop \"$p\" 2>/dev/null)\"; done",
        15,
    ),
    (
        "wifi-property-filter",
        "getprop | grep -Ei 'wifi|wlan|cnss|qcom|qca|vndk|vendor|product|hardware' || true",
        25,
    ),
    (
        "property-runtime-paths",
        "ls -ld /dev/__properties__ /dev/socket /dev/socket/property_service 2>&1 || true",
        15,
    ),
    (
        "property-area-list",
        "find /dev/__properties__ -maxdepth 2 -type f 2>/dev/null | sort | head -n 200 || true",
        20,
    ),
    (
        "service-manager-processes",
        "ps -A 2>/dev/null | grep -Ei 'servicemanager|hwservicemanager|vndservicemanager|wificond|supplicant|hostapd|cnss|wlan|wifi' || true",
        20,
    ),
    (
        "proc1-cmdline",
        "tr '\\0' ' ' < /proc/1/cmdline 2>/dev/null; echo",
        10,
    ),
)


@dataclass
class CaptureRecord:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--su", action="store_true", help="run adb shell commands through su -c")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell_command(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.su:
        return [*adb_base(args), "shell", "su", "-c", shell_command]
    return [*adb_base(args), "shell", shell_command]


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?im)^([A-Za-z0-9_.:-]+)(\s+(?:device|recovery|sideload|offline|unauthorized)\b)", r"<adb-serial>\2", text)
    text = re.sub(r"(?i)(\b(?:psk|password|passphrase|ssid|bssid)\b)[:=]\s*([^\s\]]+)", r"\1=<redacted>", text)
    text = re.sub(
        r"(?i)(\b(?:androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)\b)[:=]\s*([^\s\]]+)",
        r"\1=<redacted>",
        text,
    )
    text = re.sub(
        r"(?i)(\[(?:ro\.serialno|ro\.boot\.serialno)\]:\s*\[)([^\]]+)(\])",
        r"\1<redacted>\3",
        text,
    )
    return text


def display_command(command: list[str]) -> str:
    redacted = ["<adb-serial>" if index > 0 and command[index - 1] == "-s" else arg for index, arg in enumerate(command)]
    return " ".join(shlex.quote(part) for part in redacted)


def truncate_text(text: str, limit: int = 8192) -> str:
    redacted = redact_text(text)
    if len(redacted) > limit:
        return redacted[:limit] + "\n[truncated in manifest]\n"
    return redacted


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
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
    except FileNotFoundError as exc:
        return None, "", str(exc), time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure details
        return None, "", str(exc), time.monotonic() - started


def write_capture(store: EvidenceStore, name: str, command: list[str], text: str, error: str, rc: int | None) -> str:
    body = "\n".join(
        [
            f"$ {display_command(command)}",
            redact_text(text if text else error).rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"commands/{safe_name(name)}.txt", body)
    return str(path.relative_to(store.run_dir))


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: int) -> CaptureRecord:
    rc, text, error, duration = run_process(command, timeout)
    relative = write_capture(store, name, command, text, error, rc)
    return CaptureRecord(
        name=name,
        command=display_command(command),
        ok=rc == 0,
        rc=rc,
        duration_sec=duration,
        file=relative,
        text=truncate_text(text),
        error=error,
    )


def parse_getprop(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    bracket_re = re.compile(r"^\[([^\]]+)\]: \[(.*)\]$")
    plain_re = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = bracket_re.match(line)
        if match:
            props[match.group(1)] = match.group(2)
            continue
        match = plain_re.match(line)
        if match:
            props[match.group(1)] = match.group(2)
    return props


def read_capture_text(captures: list[CaptureRecord], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return capture.text
    return ""


def adb_state(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures = [
        capture_command(store, "adb-devices", [*adb_base(args), "devices", "-l"], args.timeout),
        capture_command(store, "adb-get-state", [*adb_base(args), "get-state"], args.timeout),
    ]
    state_text = read_capture_text(captures, "adb-get-state").strip()
    state = state_text.splitlines()[-1].strip() if state_text else ""
    if captures[1].rc is None and "No such file" in captures[1].error:
        state = "adb-missing"
    return captures, state


def run_plan(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    commands = {
        "host": [
            display_command([*adb_base(args), "devices", "-l"]),
            display_command([*adb_base(args), "get-state"]),
        ],
        "shell": [command for _, command, _ in SHELL_CAPTURES],
    }
    return {
        "generated_at": now_iso(),
        "decision": "android-property-capture-plan-ready",
        "pass": True,
        "reason": "read-only Android ADB property capture plan generated",
        "host": collect_host_metadata(),
        "guardrails": [
            "no setprop or property mutation",
            "no property runtime creation",
            "no service-manager or Wi-Fi daemon execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no partition write, backup, mount mutation, or reboot",
        ],
        "required_keys": list(REQUIRED_KEYS),
        "filter_terms": list(FILTER_TERMS),
        "commands": commands,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    if state == "device":
        decision = "android-property-capture-adb-online"
        pass_ok = True
        reason = "Android ADB is online; run mode can capture property baseline"
    elif state == "adb-missing":
        decision = "android-property-capture-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    else:
        decision = "android-property-capture-waiting-for-android"
        pass_ok = True
        reason = f"Android ADB is not online yet (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
    }


def collect_android(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures, state = adb_state(args, store)
    if state != "device":
        return captures, state
    for name, shell_command, timeout in SHELL_CAPTURES:
        captures.append(capture_command(store, name, adb_shell_command(args, shell_command), max(timeout, args.timeout)))
    return captures, state


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = collect_android(args, store)
    all_props = parse_getprop(read_capture_text(captures, "all-getprop"))
    required_from_loop = parse_getprop(read_capture_text(captures, "required-props"))
    required: dict[str, str] = {}
    for key in REQUIRED_KEYS:
        required[key] = all_props.get(key, required_from_loop.get(key, ""))
    missing = [key for key, value in required.items() if not value]

    if state != "device":
        decision = "android-property-capture-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
    elif missing:
        decision = "android-property-capture-incomplete"
        pass_ok = False
        reason = "selected Android property keys are missing: " + ", ".join(missing)
    else:
        decision = "android-property-capture-pass"
        pass_ok = True
        reason = "selected Android property baseline captured"

    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "adb_state": state,
        "required": required,
        "required_missing": missing,
        "property_count": len(all_props),
        "wifi_related_property_count": sum(
            1 for key in all_props if any(term in key.lower() or term in all_props[key].lower() for term in FILTER_TERMS)
        ),
        "captures": [asdict(capture) for capture in captures],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    capture_rows = [
        [
            item["name"],
            "ok" if item["ok"] else "fail",
            str(item["rc"]),
            f"{item['duration_sec']:.3f}s",
            item["file"],
        ]
        for item in manifest.get("captures", [])
    ]
    required = manifest.get("required", {})
    required_rows = [[key, "<set>" if value else "missing"] for key, value in required.items()]
    return "\n".join(
        [
            "# v297 Android Property Capture",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- pass: `{manifest['pass']}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: {manifest['reason']}",
            f"- adb_state: `{manifest.get('adb_state', '-')}`",
            f"- property_count: `{manifest.get('property_count', '-')}`",
            f"- wifi_related_property_count: `{manifest.get('wifi_related_property_count', '-')}`",
            "",
            "## Required Properties",
            "",
            markdown_table(["property", "state"], required_rows if required_rows else [["-", "-"]]),
            "",
            "## Captures",
            "",
            markdown_table(["name", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Safety",
            "",
            "- Read-only ADB commands only.",
            "- No Wi-Fi scan/connect/link-up/credential/DHCP/routing.",
            "- No property mutation or property runtime creation.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = run_plan(args, store)
    elif args.command == "preflight":
        manifest = run_preflight(args, store)
    else:
        manifest = run_capture_mode(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
