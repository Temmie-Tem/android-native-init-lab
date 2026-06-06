#!/usr/bin/env python3
"""V462 native Wi-Fi connect/ping gate.

The gate is intentionally fail-closed.  It verifies whether native init has a
real WLAN/wiphy surface before any credential handling or active Wi-Fi action.
If native Wi-Fi is already connected, it can run a bounded external ping proof.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v462-native-wifi-connect-ping")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
WIFI_IFACE_RE = re.compile(r"^(?:wlan\d+|swlan\d+|p2p\d+|wifi-aware\d+)$")
IPV4_RE = re.compile(r"\binet\s+(\d+\.\d+\.\d+\.\d+)/")
DEFAULT_ROUTE_RE = re.compile(r"\bdefault\b.*\bdev\s+(\S+)")
MUTATING_RE = re.compile(
    r"\b(?:rfkill\s+(?:un)?block|ip\s+link\s+set|iw\s+.*(?:scan|connect|set)|"
    r"wpa_supplicant|wpa_cli|hostapd|dhcp|udhcpc|setprop|svc\s+wifi)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CaptureSpec:
    name: str
    command: list[str]
    timeout: float
    required: bool = False


READ_ONLY_CAPTURES: tuple[CaptureSpec, ...] = (
    CaptureSpec("version", ["version"], 15.0, True),
    CaptureSpec("status", ["status"], 25.0, True),
    CaptureSpec("mountsystem-ro", ["mountsystem", "ro"], 45.0, False),
    CaptureSpec("wifiinv-full", ["wifiinv", "full"], 45.0, True),
    CaptureSpec("wififeas-full", ["wififeas", "full"], 45.0, False),
    CaptureSpec("sys-class-net", ["run", "/cache/bin/toybox", "ls", "/sys/class/net"], 20.0, True),
    CaptureSpec("proc-net-dev", ["run", "/cache/bin/toybox", "cat", "/proc/net/dev"], 20.0, True),
    CaptureSpec("proc-net-wireless", ["run", "/cache/bin/toybox", "cat", "/proc/net/wireless"], 20.0, False),
    CaptureSpec("sys-class-ieee80211", ["run", "/cache/bin/toybox", "ls", "/sys/class/ieee80211"], 20.0, False),
    CaptureSpec("sys-class-rfkill", ["run", "/cache/bin/toybox", "ls", "/sys/class/rfkill"], 20.0, False),
    CaptureSpec("firmware-class-path", ["run", "/cache/bin/toybox", "cat", "/sys/module/firmware_class/parameters/path"], 20.0, False),
    CaptureSpec("sys-module-wlan", ["stat", "/sys/module/wlan"], 20.0, False),
    CaptureSpec("sys-module-wlan-fwpath", ["cat", "/sys/module/wlan/parameters/fwpath"], 20.0, False),
    CaptureSpec("system-ping-stat", ["stat", "/mnt/system/system/bin/ping"], 20.0, False),
    CaptureSpec("system-ip-stat", ["stat", "/mnt/system/system/bin/ip"], 20.0, False),
)


PING_TARGETS = ("1.1.1.1", "8.8.8.8")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def default_out_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifi" / f"v462-native-wifi-connect-ping-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--iface", default="wlan0")
    parser.add_argument("--ping-target", action="append", default=[])
    parser.add_argument("--ping-count", type=int, default=1)
    parser.add_argument("--ping-timeout", type=int, default=3)
    parser.add_argument("--allow-external-ping", action="store_true")
    parser.add_argument("--i-understand-native-wifi-packet-probe", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def validate_capture_specs() -> None:
    text = "\n".join(" ".join(spec.command) for spec in READ_ONLY_CAPTURES)
    if MUTATING_RE.search(text):
        raise RuntimeError("read-only capture list contains active Wi-Fi command")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def run_captures(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    validate_capture_specs()
    rows: list[dict[str, Any]] = []
    store.mkdir("native/commands")
    for spec in READ_ONLY_CAPTURES:
        capture = run_capture(args, spec.name, spec.command, timeout=spec.timeout)
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        rel = write_capture(store, spec.name, text)
        item = capture_to_manifest(capture)
        item["required"] = spec.required
        item["file"] = rel
        item["payload"] = text[:2048]
        rows.append(item)
    return rows


def capture_text(captures: list[dict[str, Any]], name: str) -> str:
    for capture in captures:
        if capture.get("name") == name:
            return str(capture.get("payload") or "")
    return ""


def parse_wifiinv_summary(text: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for key in ("wlan_like", "rfkill_wifi", "module_matches", "file_matches"):
        match = re.search(rf"\b{re.escape(key)}=(\d+)\b", text)
        values[key] = int(match.group(1)) if match else 0
    return values


def parse_ifaces(text: str) -> list[str]:
    names: list[str] = []
    for token in re.split(r"\s+", text.strip()):
        cleaned = token.strip(":")
        if cleaned and re.match(r"^[A-Za-z0-9_.:-]+$", cleaned):
            names.append(cleaned)
    return sorted(set(names))


def classify_surface(captures: list[dict[str, Any]], iface: str) -> dict[str, Any]:
    sys_net_text = capture_text(captures, "sys-class-net")
    proc_net_text = capture_text(captures, "proc-net-dev")
    proc_wireless_text = capture_text(captures, "proc-net-wireless")
    ieee80211_text = capture_text(captures, "sys-class-ieee80211")
    wifiinv = parse_wifiinv_summary(capture_text(captures, "wifiinv-full"))
    sys_ifaces = parse_ifaces(sys_net_text)
    proc_ifaces = [
        line.split(":", 1)[0].strip()
        for line in proc_net_text.splitlines()
        if ":" in line and not line.lstrip().startswith("Inter-")
    ]
    wlan_ifaces = sorted({name for name in sys_ifaces + proc_ifaces if WIFI_IFACE_RE.match(name)})
    wireless_ifaces = [
        line.split(":", 1)[0].strip()
        for line in proc_wireless_text.splitlines()
        if ":" in line and not line.lstrip().startswith(("Inter-", "face"))
    ]
    wiphy_names = [name for name in parse_ifaces(ieee80211_text) if name.startswith("phy")]
    iface_present = iface in wlan_ifaces or iface in wireless_ifaces
    wlan_surface = bool(wlan_ifaces or wireless_ifaces or wifiinv.get("wlan_like", 0) > 0)
    wiphy_surface = bool(wiphy_names)
    return {
        "requested_iface": iface,
        "sys_ifaces": sys_ifaces,
        "proc_ifaces": sorted(set(proc_ifaces)),
        "wlan_ifaces": wlan_ifaces,
        "wireless_ifaces": sorted(set(wireless_ifaces)),
        "wiphy_names": sorted(set(wiphy_names)),
        "wifiinv": wifiinv,
        "iface_present": iface_present,
        "wlan_surface": wlan_surface,
        "wiphy_surface": wiphy_surface,
    }


def ping_allowed(args: argparse.Namespace) -> bool:
    return bool(args.allow_external_ping and args.i_understand_native_wifi_packet_probe)


def ping_missing_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.allow_external_ping:
        missing.append("--allow-external-ping")
    if not args.i_understand_native_wifi_packet_probe:
        missing.append("--i-understand-native-wifi-packet-probe")
    return missing


def run_existing_connectivity_probe(
    args: argparse.Namespace,
    store: EvidenceStore,
    surface: dict[str, Any],
) -> list[dict[str, Any]]:
    if not ping_allowed(args) or not surface["iface_present"]:
        return []
    targets = args.ping_target or list(PING_TARGETS)
    records: list[dict[str, Any]] = []
    for target in targets:
        name = f"ping-{target.replace('.', '-')}"
        command = [
            "run",
            "/mnt/system/system/bin/ping",
            "-I",
            args.iface,
            "-c",
            str(args.ping_count),
            "-W",
            str(args.ping_timeout),
            target,
        ]
        capture = run_capture(args, name, command, timeout=max(10.0, args.ping_count * (args.ping_timeout + 2.0)))
        text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
        rel = write_capture(store, name, text)
        item = capture_to_manifest(capture)
        item["file"] = rel
        item["target"] = target
        item["external_packet_probe"] = True
        records.append(item)
    return records


def decide(
    args: argparse.Namespace,
    captures: list[dict[str, Any]],
    surface: dict[str, Any],
    ping_records: list[dict[str, Any]],
) -> tuple[str, bool, str, str]:
    required_failures = [item["name"] for item in captures if item.get("required") and not item.get("ok")]
    if required_failures:
        return (
            "v462-native-wifi-ping-evidence-incomplete",
            False,
            "required native evidence capture failed: " + ", ".join(required_failures),
            "restore bridge/native command path before Wi-Fi connect work",
        )
    if not surface["wlan_surface"] and not surface["wiphy_surface"]:
        return (
            "v462-native-wifi-ping-blocked-no-wlan-surface",
            False,
            "native init currently exposes no wlan interface and no wiphy surface",
            "recreate Android wlan driver/firmware readiness in native before credentials or ping",
        )
    if not surface["iface_present"]:
        return (
            "v462-native-wifi-ping-blocked-requested-iface-missing",
            False,
            f"requested interface {args.iface} is not visible in native Wi-Fi surfaces",
            "select a visible WLAN interface or repair native interface creation",
        )
    if args.command != "run":
        return (
            "v462-native-wifi-ping-preflight-ready-needs-run",
            True,
            "native WLAN surface is visible; external ping proof was not requested in this mode",
            "rerun run with explicit external-ping approval",
        )
    if not ping_allowed(args):
        return (
            "v462-native-wifi-ping-approval-required",
            False,
            "external packet probe requires explicit approval flags",
            "rerun with --allow-external-ping and --i-understand-native-wifi-packet-probe",
        )
    if not ping_records:
        return (
            "v462-native-wifi-ping-no-probe-records",
            False,
            "no external ping records were produced",
            "review native interface and ping tool availability",
        )
    if any(item.get("ok") for item in ping_records):
        return (
            "v462-native-wifi-external-ping-pass",
            True,
            "native WLAN-bound external ping succeeded",
            "document native Wi-Fi connection proof and plan bounded stability",
        )
    return (
        "v462-native-wifi-external-ping-failed",
        False,
        "native WLAN surface existed but all external ping probes failed",
        "inspect IP, route, gateway, DNS, and AP reachability before retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest["surface"]
    capture_rows = [
        [item["name"], "PASS" if item.get("ok") else "FAIL", str(item.get("rc")), item.get("status", "-")]
        for item in manifest["captures"]
    ]
    ping_rows = [
        [item["target"], "PASS" if item.get("ok") else "FAIL", str(item.get("rc")), item.get("status", "-")]
        for item in manifest.get("ping_records", [])
    ]
    lines = [
        "# V462 Native Wi-Fi Connect/Ping Gate",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_gate']}",
        f"- requested iface: `{surface['requested_iface']}`",
        f"- WLAN surface: `{surface['wlan_surface']}`",
        f"- wiphy surface: `{surface['wiphy_surface']}`",
        f"- visible WLAN ifaces: `{', '.join(surface['wlan_ifaces']) or '-'}`",
        f"- visible wiphy names: `{', '.join(surface['wiphy_names']) or '-'}`",
        "",
        "## Native Captures",
        "",
        markdown_table(["Capture", "Result", "RC", "Status"], capture_rows),
        "",
    ]
    if ping_rows:
        lines.extend(["## External Ping Probes", "", markdown_table(["Target", "Result", "RC", "Status"], ping_rows), ""])
    lines.extend(
        [
            "## Guardrails",
            "",
            "- No credential env or policy file is read before a WLAN/wiphy surface exists.",
            "- No scan/connect/link-up command is issued by this V462 gate.",
            "- External ping runs only with explicit packet-probe flags and binds to the requested WLAN interface.",
            "- Evidence is written with private output helpers.",
            "",
        ]
    )
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures = run_captures(args, store)
    surface = classify_surface(captures, args.iface)
    ping_records = run_existing_connectivity_probe(args, store, surface) if args.command == "run" else []
    decision, passed, reason, next_gate = decide(args, captures, surface, ping_records)
    return {
        "schema": "a90.native_wifi_connect_ping.v462",
        "created_at": now_iso(),
        "mode": args.command,
        "host": collect_host_metadata(),
        "expect_version": args.expect_version,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_gate": next_gate,
        "device_commands_executed": bool(args.command in {"preflight", "run"}),
        "device_mutations": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "scan_connect_executed": False,
        "external_ping_executed": bool(ping_records),
        "surface": surface,
        "missing_ping_flags": ping_missing_flags(args),
        "captures": captures,
        "ping_records": ping_records,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    if args.command == "plan":
        manifest = {
            "schema": "a90.native_wifi_connect_ping.v462",
            "created_at": now_iso(),
            "mode": "plan",
            "host": collect_host_metadata(),
            "decision": "v462-native-wifi-ping-plan-ready",
            "pass": True,
            "reason": "plan-only; no device command executed",
            "next_gate": "run preflight on native init, then only ping if WLAN surface exists",
            "device_commands_executed": False,
            "device_mutations": False,
            "wifi_bringup_executed": False,
            "credentials_read": False,
            "scan_connect_executed": False,
            "external_ping_executed": False,
            "surface": {
                "requested_iface": args.iface,
                "wlan_surface": False,
                "wiphy_surface": False,
                "wlan_ifaces": [],
                "wiphy_names": [],
            },
            "captures": [],
            "ping_records": [],
            "guardrails": [
                "no credential read before native WLAN surface",
                "no scan/connect/link-up in V462",
                "external ping requires explicit flags and interface binding",
            ],
        }
    else:
        manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_gate: {manifest['next_gate']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
