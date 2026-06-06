#!/usr/bin/env python3
"""Collect read-only Wi-Fi baseline evidence for the A90 native-init stack."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
)
from a90harness.evidence import EvidenceStore
from kernel_capability_summary import DEFAULT_INPUTS as KERNEL_SUMMARY_DEFAULT_INPUTS


FORBIDDEN_ACTIVE_PATTERNS = (
    "rfkill unblock",
    "ip link set wlan0 up",
    "insmod",
    "rmmod",
    "modprobe",
    "svc wifi",
    "cmd wifi set-wifi-enabled",
    "wpa_supplicant",
    "hostapd",
)

ADB_READ_ONLY_COMMANDS = (
    "getprop | grep -Ei 'wifi|wlan|qca|cnss|wcn|firmware' || true",
    "ip link",
    "ls -l /sys/class/net /sys/class/rfkill 2>/dev/null || true",
    "cat /proc/modules 2>/dev/null | grep -Ei 'wlan|wifi|qca|qcacld|cnss|wcn|ath' || true",
    "dmesg 2>/dev/null | grep -Ei 'wlan|wifi|qca|qcacld|cnss|wcn|firmware' | tail -n 120 || true",
    "find /vendor /odm /product /system -maxdepth 5 "
    "\\( -iname '*wifi*' -o -iname '*wlan*' -o -iname '*qca*' "
    "-o -iname '*cnss*' -o -iname '*wcn*' -o -iname '*bdwlan*' "
    "-o -iname '*qwlan*' \\) 2>/dev/null || true",
)

DEVICE_COMMANDS_PRE_MOUNT: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 20.0),
    ("wififeas-gate", ["wififeas", "gate"], 20.0),
    ("wifiinv-full", ["wifiinv", "full"], 60.0),
    ("wifiinv-refresh", ["wifiinv", "refresh"], 45.0),
    ("wififeas-refresh", ["wififeas", "refresh"], 45.0),
    ("wifiinv-paths", ["wifiinv", "paths"], 30.0),
    ("wififeas-paths", ["wififeas", "paths"], 30.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 20.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 20.0),
    ("proc-modules", ["cat", "/proc/modules"], 30.0),
)

DEVICE_COMMANDS_POST_MOUNT: tuple[tuple[str, list[str], float], ...] = (
    ("mounted-wifiinv-full", ["wifiinv", "full"], 60.0),
    ("mounted-wifiinv-refresh", ["wifiinv", "refresh"], 45.0),
    ("mounted-wififeas-full", ["wififeas", "full"], 60.0),
    ("mounted-wififeas-refresh", ["wififeas", "refresh"], 45.0),
)


def default_out_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifi" / f"v203-baseline-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--mount-system-ro", dest="no_mount_system_ro", action="store_false", help="run read-only mountsystem phase")
    parser.add_argument("--no-mount-system-ro", dest="no_mount_system_ro", action="store_true", help="skip read-only mountsystem phase")
    parser.set_defaults(no_mount_system_ro=False)
    parser.add_argument("--skip-kernel-summary", action="store_true", help="skip kernel_capability_summary.py preflight")
    parser.add_argument("--kernel-summary-refresh", action="store_true", help="rerun v197-v200 source collectors")
    parser.add_argument("--android-adb", action="store_true", help="append Android read-only adb baseline")
    parser.add_argument("--twrp-adb", action="store_true", help="append TWRP read-only adb baseline")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--adb-timeout", type=int, default=30)
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def validate_no_active_wifi_commands() -> None:
    device_text = "\n".join(" ".join(command) for _, command, _ in DEVICE_COMMANDS_PRE_MOUNT + DEVICE_COMMANDS_POST_MOUNT)
    adb_text = "\n".join(ADB_READ_ONLY_COMMANDS)
    for token in FORBIDDEN_ACTIVE_PATTERNS:
        if token in device_text:
            raise RuntimeError(f"active Wi-Fi token in device command list: {token}")
    active_adb_tokens = (
        "rfkill unblock",
        "ip link set wlan0 up",
        "insmod",
        "rmmod",
        "modprobe",
        "svc wifi enable",
        "cmd wifi set-wifi-enabled",
    )
    for token in active_adb_tokens:
        if token in adb_text:
            raise RuntimeError(f"active Wi-Fi token in adb command list: {token}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, name, body)
    data = capture_to_manifest(capture)
    data["file"] = relative
    return data


def run_host_command(command: list[str], timeout: float) -> tuple[int, str, float]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout, time.monotonic() - started


def capture_host(store: EvidenceStore,
                 name: str,
                 command: list[str],
                 timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    try:
        rc, text, duration = run_host_command(command, timeout)
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collector records failures
        rc = None
        text = ""
        error = str(exc)
        duration = time.monotonic() - started
    relative = write_capture(store, name, text if text else error)
    return {
        "name": name,
        "command": " ".join(command),
        "ok": rc == 0,
        "rc": rc,
        "status": "ok" if rc == 0 else "error",
        "duration_sec": duration,
        "file": relative,
        "error": error,
    }


def capture_adb_baseline(store: EvidenceStore,
                         args: argparse.Namespace,
                         label: str) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    for index, shell_command in enumerate(ADB_READ_ONLY_COMMANDS, start=1):
        name = f"{label}-adb-{index:02d}"
        command = [args.adb, "shell", shell_command]
        captures.append(capture_host(store, name, command, timeout=args.adb_timeout))
    return captures


def kernel_summary_needs_refresh(args: argparse.Namespace) -> bool:
    if args.kernel_summary_refresh:
        return True
    return any(not repo_path(path).exists() for path in KERNEL_SUMMARY_DEFAULT_INPUTS.values())


def run_kernel_summary(store: EvidenceStore, args: argparse.Namespace) -> dict[str, Any]:
    summary_md = store.path("kernel-capability", "summary.md")
    summary_json = store.path("kernel-capability", "summary.json")
    command = [
        sys.executable,
        "scripts/revalidation/kernel_capability_summary.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--expect-version",
        args.expect_version,
        "--out",
        str(summary_md),
        "--json-out",
        str(summary_json),
    ]
    refresh_sources = kernel_summary_needs_refresh(args)
    if refresh_sources:
        source_dir = store.mkdir("kernel-capability", "sources")
        command.extend([
            "--refresh",
            "--config-json",
            str(source_dir / "kernel-config.json"),
            "--netfilter-json",
            str(source_dir / "netfilter.json"),
            "--cgroup-json",
            str(source_dir / "cgroup-psi.json"),
            "--debug-json",
            str(source_dir / "debug-observability.json"),
        ])
    capture = capture_host(store, "kernel-capability-summary", command, timeout=max(args.timeout * 5, 120.0))
    payload: dict[str, Any] = {}
    if summary_json.exists():
        payload = json.loads(summary_json.read_text(encoding="utf-8"))
    return {
        "capture": capture,
        "manifest": str(summary_json.relative_to(store.run_dir)) if summary_json.exists() else None,
        "report": str(summary_md.relative_to(store.run_dir)) if summary_md.exists() else None,
        "pass": bool(payload.get("pass")),
        "refreshed_sources": refresh_sources,
        "wifi_gate_ok": bool(payload.get("wifi_gate_ok")),
        "wifi_gate_status": payload.get("wifi_gate_status", "missing"),
        "wifi_decision": payload.get("wifi_decision", "unknown"),
    }


def parse_wififeas_decision(text: str) -> str:
    for line in text.splitlines():
        if "wififeas: decision=" in line:
            return line.split("wififeas: decision=", 1)[1].strip().split()[0]
        if line.startswith("decision="):
            return line.split("=", 1)[1].strip().split()[0]
    return "unknown"


def command_text(captures: list[dict[str, Any]], name: str) -> str:
    for capture in captures:
        if capture.get("name") == name:
            return str(capture.get("text", ""))
    return ""


def count_pattern(text: str, pattern: str) -> int | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1), 0)
    except ValueError:
        return None


def derive_missing_gates(captures: list[dict[str, Any]]) -> list[str]:
    joined = "\n".join(str(capture.get("text", "")) for capture in captures)
    missing: list[str] = []
    wlan_count = count_pattern(joined, r"wlan(?:_like)?[= ]+(\d+)")
    rfkill_count = count_pattern(joined, r"(?:rfkill_wifi|wifi_like)[= ]+(\d+)")
    module_count = count_pattern(joined, r"(?:modules matches|module_matches)[= ]+(\d+)")
    if wlan_count == 0:
        missing.append("native-wlan-interface")
    if rfkill_count == 0:
        missing.append("wifi-rfkill")
    if module_count == 0:
        missing.append("wlan-cnss-qca-module-evidence")
    if not missing:
        missing.append("manual-review-required")
    return missing


def derive_candidates(captures: list[dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    path_pattern = re.compile(r"(/(?:mnt/system|system|vendor|odm|product)[^\s\r\n]+)", re.IGNORECASE)
    for capture in captures:
        for line in str(capture.get("text", "")).splitlines():
            if "match kind=" in line and " path=" in line:
                path_text = line.split(" path=", 1)[1]
            elif "exists=yes path=" in line:
                path_text = line.split("exists=yes path=", 1)[1]
            elif "exists=no path=" in line:
                continue
            else:
                continue
            match = path_pattern.search(path_text)
            if not match:
                continue
            path = match.group(1).rstrip("`'\",")
            lowered = path.lower()
            if any(token in lowered for token in ("wifi", "wlan", "qca", "cnss", "wcn", "bdwlan", "qwlan", "wificond", "supplicant", "hostapd")):
                if path not in seen:
                    seen.add(path)
                    candidates.append(path)
            if len(candidates) >= 80:
                return candidates
    return candidates


def final_decision(device_captures: list[dict[str, Any]], kernel_summary: dict[str, Any] | None) -> tuple[str, str]:
    gate_text = command_text(device_captures, "wififeas-gate")
    mounted_text = command_text(device_captures, "mounted-wififeas-full")
    gate_decision = parse_wififeas_decision(gate_text)
    mounted_decision = parse_wififeas_decision(mounted_text)
    gate_ok = any(capture.get("name") == "wififeas-gate" and capture.get("ok") for capture in device_captures)

    if kernel_summary is not None and not kernel_summary.get("wifi_gate_ok"):
        return "baseline-required", "kernel capability Wi-Fi gate did not verify cleanly"
    if not gate_ok:
        return "baseline-required", "live wififeas gate command failed"
    if mounted_decision == "no-go":
        return "no-go", "mounted Android-side candidates exist but kernel-facing gates remain absent"
    if gate_decision == "go":
        return "go-read-only-probe", "native gate reports go; next step is a separate read-only nl80211/iw probe plan"
    if gate_decision == "no-go":
        return "no-go", "native feasibility gate reports no-go"
    return "baseline-required", "native feasibility gate still requires baseline evidence"


def build_report(args: argparse.Namespace,
                 host_metadata: dict[str, Any],
                 device_captures: list[dict[str, Any]],
                 host_captures: list[dict[str, Any]],
                 kernel_summary: dict[str, Any] | None,
                 manual_captures: list[dict[str, Any]],
                 decision: str,
                 reason: str,
                 missing_gates: list[str],
                 candidates: list[str],
                 pass_ok: bool) -> str:
    rows = [
        ["version", "PASS" if any(c.get("name") == "version" and c.get("ok") for c in device_captures) else "FAIL", args.expect_version],
        ["wififeas gate", parse_wififeas_decision(command_text(device_captures, "wififeas-gate")), "live command required"],
        ["kernel summary", "skipped" if kernel_summary is None else str(kernel_summary.get("wifi_decision")), "wifi_gate_ok=" + ("n/a" if kernel_summary is None else str(kernel_summary.get("wifi_gate_ok")))],
        ["mounted system", "skipped" if args.no_mount_system_ro else "captured", "read-only mountsystem phase"],
        ["final decision", decision, reason],
    ]
    lines = [
        "# A90 Wi-Fi Baseline Refresh",
        "",
        f"- generated: `{dt.datetime.now(dt.timezone.utc).isoformat()}`",
        f"- result: `{'PASS' if pass_ok else 'FAIL'}`",
        f"- decision: `{decision}`",
        f"- reason: `{reason}`",
        f"- expected version: `{args.expect_version}`",
        "",
        "## Summary Matrix",
        "",
        markdown_table(["area", "status", "detail"], rows),
        "",
        "## Missing Gates",
        "",
    ]
    lines.extend(f"- `{item}`" for item in missing_gates)
    lines.extend(["", "## Candidate Android/Vendor Paths", ""])
    if candidates:
        lines.extend(f"- `{item}`" for item in candidates[:80])
    else:
        lines.append("- none captured")
    lines.extend([
        "",
        "## Captures",
        "",
        f"- device captures: `{len(device_captures)}`",
        f"- host captures: `{len(host_captures)}`",
        f"- manual ADB captures: `{len(manual_captures)}`",
        "",
        "## Guardrails",
        "",
        "- no Wi-Fi enablement",
        "- no rfkill write",
        "- no wlan link-up",
        "- no module load/unload",
        "- no firmware mutation",
        "- no Android Wi-Fi service start",
        "- no network exposure expansion",
        "",
        "## Host Metadata",
        "",
        "```json",
        json.dumps(host_metadata, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_wifi_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    host_metadata = collect_host_metadata()
    device_captures: list[dict[str, Any]] = []
    host_captures: list[dict[str, Any]] = []
    manual_captures: list[dict[str, Any]] = []
    kernel_summary: dict[str, Any] | None = None

    for name, command, timeout in DEVICE_COMMANDS_PRE_MOUNT:
        device_captures.append(capture_device(store, args, name, command, timeout))

    if not args.skip_kernel_summary:
        kernel_summary = run_kernel_summary(store, args)
        host_captures.append(kernel_summary["capture"])

    if not args.no_mount_system_ro:
        device_captures.append(capture_device(store, args, "mountsystem-ro", ["mountsystem", "ro"], 45.0))
        for name, command, timeout in DEVICE_COMMANDS_POST_MOUNT:
            device_captures.append(capture_device(store, args, name, command, timeout))

    if args.android_adb:
        manual_captures.extend(capture_adb_baseline(store, args, "android"))
    if args.twrp_adb:
        manual_captures.extend(capture_adb_baseline(store, args, "twrp"))

    decision, reason = final_decision(device_captures, kernel_summary)
    missing_gates = derive_missing_gates(device_captures)
    candidates = derive_candidates(device_captures)
    version_ok = args.expect_version in command_text(device_captures, "version")
    gate_ok = any(capture.get("name") == "wififeas-gate" and capture.get("ok") for capture in device_captures)
    kernel_ok = True if args.skip_kernel_summary else bool(kernel_summary and kernel_summary.get("pass") and kernel_summary.get("wifi_gate_ok"))
    pass_ok = version_ok and gate_ok and kernel_ok and decision in {"baseline-required", "no-go", "go-read-only-probe"}

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "expect_version": args.expect_version,
        "version_matches": version_ok,
        "gate_ok": gate_ok,
        "kernel_summary": kernel_summary,
        "missing_gates": missing_gates,
        "candidate_paths": candidates,
        "host_metadata": host_metadata,
        "device_captures": device_captures,
        "host_captures": host_captures,
        "manual_captures": manual_captures,
        "guardrails": {
            "wifi_enablement": "forbidden",
            "rfkill_write": "forbidden",
            "wlan_link_up": "forbidden",
            "module_mutation": "forbidden",
            "firmware_mutation": "forbidden",
            "android_wifi_service_start": "forbidden",
            "network_exposure_expansion": "forbidden",
        },
    }
    report = build_report(
        args,
        host_metadata,
        device_captures,
        host_captures,
        kernel_summary,
        manual_captures,
        decision,
        reason,
        missing_gates,
        candidates,
        pass_ok,
    )
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report.rstrip() + "\n")
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
