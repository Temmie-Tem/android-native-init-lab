#!/usr/bin/env python3
"""V413 read-only VINTF Wi-Fi declaration collector.

This collector inventories Wi-Fi-looking HIDL/VINTF declarations from the
mounted Android system/vendor trees.  It is intentionally narrower than Wi-Fi
bring-up: it may run read-only cmdv1 commands and ``mountsystem ro`` for
visibility, but it must not deploy helpers, start service managers, start Wi-Fi
HALs, scan/connect/link-up, write credentials, run DHCP, or mutate firmware.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v413-vintf-wifi-declared-services")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-system-vintf", ["stat", "/mnt/system/system/etc/vintf"], 10.0),
    ("stat-system-vendor-vintf", ["stat", "/mnt/system/system/vendor/etc/vintf"], 10.0),
    ("stat-system-system-ext-vintf", ["stat", "/mnt/system/system/system_ext/etc/vintf"], 10.0),
    ("stat-vendor-vintf", ["stat", "/mnt/system/vendor/etc/vintf"], 10.0),
    ("stat-odm-vintf", ["stat", "/mnt/system/odm/etc/vintf"], 10.0),
    ("find-vintf-manifests", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "8", "-type", "f", "-name", "*manifest*.xml"], 25.0),
    ("find-vintf-xml", ["run", DEFAULT_TOYBOX, "find", "/mnt/system", "-maxdepth", "8", "-type", "f", "-name", "*.xml"], 25.0),
    ("grep-wifi-vintf", ["run", DEFAULT_TOYBOX, "grep", "-RHiE", "wifi|supplicant|hostapd", "/mnt/system/system/etc/vintf", "/mnt/system/system/vendor/etc/vintf", "/mnt/system/system/system_ext/etc/vintf", "/mnt/system/vendor/etc/vintf", "/mnt/system/odm/etc/vintf"], 25.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 10.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
)

MAX_XML_CAPTURE_PATHS = 24

SERVICE_TOKEN_RE = re.compile(
    r"((?:android|vendor|com)\.[A-Za-z0-9_.-]*(?:wifi|supplicant|hostapd)[A-Za-z0-9_.@:/-]*)",
    re.IGNORECASE,
)
WIFI_NETDEV_RE = re.compile(r"(^|\\s|:)(wlan\\S*|swlan\\S*|p2p\\S*|wiphy\\S*|phy\\d+)(\\s|:|$)", re.IGNORECASE)
MANAGER_OR_WIFI_PROCESS_RE = re.compile(
    r"\\b(servicemanager|hwservicemanager|vndservicemanager|wificond|supplicant|hostapd|cnss-daemon|cnss_diag)\\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CaptureSummary:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def capture_text(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            if not capture.file:
                return ""
            path = store.path(capture.file)
            if path.exists():
                return path.read_text(encoding="utf-8", errors="replace")
    return ""


def capture_ok(captures: list[CaptureSummary], name: str) -> bool:
    return any(capture.name == name and capture.ok for capture in captures)


def append_capture(args: argparse.Namespace,
                   store: EvidenceStore,
                   captures: list[CaptureSummary],
                   name: str,
                   command: list[str],
                   timeout: float) -> CaptureSummary:
    record = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    summary = CaptureSummary(
        name=name,
        command=record.command,
        ok=record.ok,
        rc=record.rc,
        status=record.status,
        duration_sec=record.duration_sec,
        file=rel,
        error=record.error,
    )
    captures.append(summary)
    return summary


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    store.mkdir("native")
    for name, command, timeout in READ_ONLY_COMMANDS:
        append_capture(args, store, captures, name, command, timeout)
    _, grep_source_paths = parse_declared_candidates(capture_text(store, captures, "grep-wifi-vintf"))
    find_source_paths = parse_find_vintf_xml(capture_text(store, captures, "find-vintf-xml"))
    source_paths = merge_paths(grep_source_paths, find_source_paths)
    for idx, source_path in enumerate(source_paths[:MAX_XML_CAPTURE_PATHS]):
        append_capture(
            args,
            store,
            captures,
            f"cat-vintf-{idx:02d}",
            ["cat", source_path],
            20.0,
        )
    return captures


def parse_declared_candidates(text: str) -> tuple[list[str], list[str]]:
    candidates: list[str] = []
    source_paths: list[str] = []
    seen_candidates: set[str] = set()
    seen_paths: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            possible_path = line.split(":", 1)[0]
            if possible_path.startswith("/mnt/system") and possible_path not in seen_paths:
                source_paths.append(possible_path)
                seen_paths.add(possible_path)
        for match in SERVICE_TOKEN_RE.finditer(line):
            value = match.group(1).rstrip(",;")
            if value not in seen_candidates:
                candidates.append(value)
                seen_candidates.add(value)
    return candidates, source_paths


def parse_find_vintf_xml(text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("/mnt/system") or "/vintf/" not in line or not line.endswith(".xml"):
            continue
        if line not in seen:
            paths.append(line)
            seen.add(line)
    return paths


def merge_paths(*path_lists: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for path_list in path_lists:
        for path in path_list:
            if path not in seen:
                merged.append(path)
                seen.add(path)
    return merged


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(parent: ET.Element, name: str) -> str:
    for child in list(parent):
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if local_name(child.tag) == name]


def looks_wifi(value: str) -> bool:
    return bool(re.search(r"wifi|supplicant|hostapd", value, re.IGNORECASE))


def add_unique(values: list[str], seen: set[str], value: str) -> None:
    value = value.strip()
    if value and value not in seen:
        values.append(value)
        seen.add(value)


def parse_xml_declarations(xml_text: str) -> list[str]:
    declarations: list[str] = []
    seen: set[str] = set()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return declarations
    for hal in root.iter():
        if local_name(hal.tag) != "hal":
            continue
        package = child_text(hal, "name")
        versions = [item.text.strip() for item in children(hal, "version") if item.text and item.text.strip()]
        fqnames = [item.text.strip() for item in children(hal, "fqname") if item.text and item.text.strip()]
        for fqname in fqnames:
            if looks_wifi(f"{package}{fqname}"):
                if fqname.startswith("@") and package:
                    add_unique(declarations, seen, f"{package}{fqname}")
                else:
                    add_unique(declarations, seen, fqname)
        for interface in children(hal, "interface"):
            iface = child_text(interface, "name")
            instances = [
                item.text.strip()
                for item in children(interface, "instance") + children(interface, "regex-instance")
                if item.text and item.text.strip()
            ]
            if not instances:
                instances = [""]
            if not versions:
                versions = [""]
            for version in versions:
                for instance in instances:
                    if package and iface and instance:
                        value = f"{package}@{version}::{iface}/{instance}" if version else f"{package}::{iface}/{instance}"
                    elif package and iface:
                        value = f"{package}@{version}::{iface}" if version else f"{package}::{iface}"
                    else:
                        value = package
                    if looks_wifi(value):
                        add_unique(declarations, seen, value)
        if package and looks_wifi(package):
            add_unique(declarations, seen, package)
    return declarations


def parse_structured_declarations(store: EvidenceStore, captures: list[CaptureSummary]) -> list[str]:
    declarations: list[str] = []
    seen: set[str] = set()
    for capture in captures:
        if not capture.name.startswith("cat-vintf-") or not capture.ok:
            continue
        for value in parse_xml_declarations(capture_text(store, captures, capture.name)):
            add_unique(declarations, seen, value)
    return declarations


def active_surface(store: EvidenceStore, captures: list[CaptureSummary]) -> tuple[list[str], list[str]]:
    net_text = capture_text(store, captures, "proc-net-dev") + "\n" + capture_text(store, captures, "sys-class-net")
    ps_text = capture_text(store, captures, "ps")
    net_lines = [line.strip() for line in net_text.splitlines() if WIFI_NETDEV_RE.search(line)]
    proc_lines = [line.strip() for line in ps_text.splitlines() if MANAGER_OR_WIFI_PROCESS_RE.search(line)]
    return net_lines, proc_lines


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str], next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, evidence, next_step))


def planned_captures() -> list[CaptureSummary]:
    return [
        CaptureSummary(name, " ".join(command), True, 0, "planned", 0.0, "", "")
        for name, command, _ in READ_ONLY_COMMANDS
    ]


def build_checks(args: argparse.Namespace,
                 store: EvidenceStore,
                 captures: list[CaptureSummary],
                 candidates: list[str],
                 structured_candidates: list[str],
                 source_paths: list[str],
                 net_lines: list[str],
                 proc_lines: list[str]) -> list[Check]:
    checks: list[Check] = []
    version_text = capture_text(store, captures, "version")
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run read-only collector when bridge is available")
        return checks
    add_check(
        checks,
        "native-version",
        "pass" if args.expect_version in version_text else "warn",
        "warning",
        f"expect_version={args.expect_version}",
        [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
        "refresh defaults if boot image intentionally changed",
    )
    add_check(
        checks,
        "mountsystem-ro",
        "pass" if capture_ok(captures, "mountsystem-ro") else "blocked",
        "blocker",
        "read-only Android partition visibility is required",
        [capture_text(store, captures, "mountsystem-ro").strip()[:300]],
        "restore read-only system mount before VINTF declaration inventory",
    )
    add_check(
        checks,
        "vintf-source-visible",
        "pass" if (
            capture_ok(captures, "stat-system-vintf")
            or capture_ok(captures, "stat-system-vendor-vintf")
            or capture_ok(captures, "stat-system-system-ext-vintf")
            or capture_ok(captures, "stat-vendor-vintf")
            or capture_ok(captures, "stat-odm-vintf")
        ) else "blocked",
        "blocker",
        "at least one VINTF directory should be visible",
        source_paths[:16],
        "inspect Android partition mount/export state",
    )
    add_check(
        checks,
        "wifi-declarations",
        "pass" if candidates else "review",
        "info" if candidates else "warning",
        f"candidate_count={len(candidates)}",
        candidates[:16],
        "use declarations to constrain V411/V412 follow-up service names",
    )
    add_check(
        checks,
        "structured-wifi-declarations",
        "pass" if structured_candidates else "review",
        "info" if structured_candidates else "warning",
        f"structured_candidate_count={len(structured_candidates)}",
        structured_candidates[:16],
        "prefer structured VINTF package/interface/instance candidates when available",
    )
    add_check(
        checks,
        "wifi-link-surface-clean",
        "pass" if not net_lines else "warn",
        "warning",
        f"wifi_like_netdev_count={len(net_lines)}",
        net_lines[:8],
        "do not run declaration inventory during active Wi-Fi link work",
    )
    add_check(
        checks,
        "manager-wifi-process-surface-clean",
        "pass" if not proc_lines else "blocked",
        "blocker",
        f"manager_wifi_process_count={len(proc_lines)}",
        proc_lines[:10],
        "do not run next live gate over residual manager/Wi-Fi processes",
    )
    return checks


def decide(args: argparse.Namespace, checks: list[Check], candidates: list[str]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v413-vintf-wifi-declarations-plan-ready",
            True,
            "plan-only; no device command executed",
            "run read-only VINTF Wi-Fi declaration collector",
        )
    blockers = [check.name for check in checks if check.status == "blocked" and check.severity == "blocker"]
    if blockers:
        return (
            "v413-vintf-wifi-declarations-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "resolve read-only visibility or clean process-surface blockers",
        )
    if candidates:
        return (
            "v413-vintf-wifi-declarations-ready",
            True,
            f"parsed {len(candidates)} Wi-Fi-looking VINTF declaration candidates",
            "compare declared candidates against V411 binderized lshal output after helper v27 deploy",
        )
    return (
        "v413-vintf-wifi-declarations-review",
        True,
        "VINTF sources visible but no Wi-Fi-looking declaration was parsed",
        "inspect captured VINTF files and Android-side lshal output before widening scope",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V413 VINTF Wi-Fi Declarations",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
    ]
    for check in manifest["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`: {check['detail']}")
    if manifest["declared_wifi_candidates"]:
        lines.extend(["", "## Declared Wi-Fi Candidates", ""])
        for candidate in manifest["declared_wifi_candidates"]:
            lines.append(f"- `{candidate}`")
    if manifest["source_paths"]:
        lines.extend(["", "## Source Paths", ""])
        for source_path in manifest["source_paths"]:
            lines.append(f"- `{source_path}`")
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures = planned_captures() if args.command == "plan" else collect_live(args, store)
    grep_text = capture_text(store, captures, "grep-wifi-vintf")
    candidates, grep_source_paths = parse_declared_candidates(grep_text)
    find_source_paths = parse_find_vintf_xml(capture_text(store, captures, "find-vintf-xml"))
    source_paths = merge_paths(grep_source_paths, find_source_paths)
    structured_candidates = parse_structured_declarations(store, captures)
    merged_candidates = list(dict.fromkeys(structured_candidates + candidates))
    net_lines, proc_lines = active_surface(store, captures)
    checks = build_checks(args, store, captures, merged_candidates, structured_candidates, source_paths, net_lines, proc_lines)
    decision, pass_ok, reason, next_step = decide(args, checks, merged_candidates)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "captures": [asdict(capture) for capture in captures],
        "checks": [asdict(check) for check in checks],
        "declared_wifi_candidates": merged_candidates,
        "structured_wifi_candidates": structured_candidates,
        "source_paths": source_paths,
        "wifi_like_netdev_lines": net_lines,
        "manager_wifi_process_lines": proc_lines,
        "device_commands_executed": args.command != "plan",
        "read_only_mount_attempted": args.command != "plan",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "helper deploy",
            "servicemanager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"declared_wifi_candidates: {len(manifest['declared_wifi_candidates'])}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
