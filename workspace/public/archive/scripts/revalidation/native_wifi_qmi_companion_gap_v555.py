#!/usr/bin/env python3
"""V555 native QMI companion gap classifier.

This read-only live probe checks the currently mounted native system/vendor
surfaces for extra QMI companion candidates after V554 observed an empty WLFW
QRTR nameservice readback. It does not start daemons, send QRTR/QMI payloads,
start Wi-Fi HAL, scan/connect/link-up, change routes, ping externally, reboot,
or write Android partitions.
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
    collect_host_metadata,
    capture_to_manifest,
    markdown_table,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v555-qmi-companion-gap")
PROOF_SLUG = "v555-qmi-companion-gap"
PROOF_VERSION = "V555"

REQUIRED_COMPANIONS = (
    "qrtr-ns",
    "rmt_storage",
    "tftp_server",
    "pd-mapper",
    "cnss_diag",
    "cnss-daemon",
)

EXTRA_COMPANIONS = (
    "qmiproxy",
    "ssgqmigd",
    "sysmon-qmi",
    "service-notifier",
    "tqftpserv",
    "rmtfs",
)

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    (
        "mounts",
        ["run", "/cache/bin/toybox", "cat", "/proc/mounts"],
        10.0,
    ),
    (
        "mount-path-stats",
        [
            "run",
            "/cache/bin/toybox",
            "ls",
            "-ld",
            "/mnt/system",
            "/mnt/system/system",
            "/mnt/system/system/vendor",
            "/mnt/vendor_ro",
            "/vendor",
            "/system/vendor",
        ],
        10.0,
    ),
    (
        "system-vendor-readlink",
        ["run", "/cache/bin/toybox", "readlink", "/mnt/system/system/vendor"],
        10.0,
    ),
    (
        "known-path-stats",
        [
            "run",
            "/cache/bin/toybox",
            "ls",
            "-lZ",
            "/mnt/vendor_ro/bin/qrtr-ns",
            "/mnt/vendor_ro/bin/rmt_storage",
            "/mnt/vendor_ro/bin/tftp_server",
            "/mnt/vendor_ro/bin/pd-mapper",
            "/mnt/vendor_ro/bin/cnss_diag",
            "/mnt/vendor_ro/bin/cnss-daemon",
            "/mnt/system/system/bin/qmiproxy",
            "/mnt/vendor_ro/bin/ssgqmigd",
            "/mnt/vendor_ro/bin/sysmon-qmi",
            "/mnt/vendor_ro/bin/service-notifier",
            "/mnt/vendor_ro/bin/tqftpserv",
            "/mnt/vendor_ro/bin/rmtfs",
        ],
        10.0,
    ),
    (
        "qmi-name-find",
        ["run", "/cache/bin/toybox", "find", "/mnt/system", "/mnt/vendor_ro", "-maxdepth", "6", "-name", "*qmi*"],
        20.0,
    ),
    (
        "notifier-name-find",
        ["run", "/cache/bin/toybox", "find", "/mnt/system", "/mnt/vendor_ro", "-maxdepth", "6", "-name", "*notifier*"],
        20.0,
    ),
    (
        "initrc-qmi",
        [
            "run",
            "/cache/bin/toybox",
            "grep",
            "-RHiE",
            "service[[:space:]].*(qrtr|qmi|ssgqmigd|sysmon|service-notifier|rmt|tftp|pd-mapper|cnss|wifi)|"
            "on property:.*(qrtr|qmi|sysmon|rmt|tftp|pd|cnss|wifi)|socket[[:space:]]+ssgqmig",
            "/mnt/system/system/etc/init",
            "/mnt/vendor_ro/etc/init",
            "/mnt/vendor_ro/etc/init/hw",
        ],
        20.0,
    ),
    (
        "process-snapshot",
        ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,ppid,stat,comm,args"],
        10.0,
    ),
    (
        "dmesg-qmi-tail",
        ["run", "/cache/bin/toybox", "dmesg"],
        15.0,
    ),
)

READ_ONLY_GUARDS = (
    "daemon_start_executed=0",
    "wifi_hal_start_executed=0",
    "qrtr_payload_executed=0",
    "qmi_payload_executed=0",
    "scan_connect_linkup=0",
    "external_ping=0",
    "boot_partition_write=0",
)


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
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("command", choices=("plan", "preflight", "run"))
    return parser.parse_args()


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def run_read_only_commands(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures: dict[str, Any] = {}
    texts: dict[str, str] = {}

    version = run_capture(args, "version", ["version"], timeout=10.0)
    captures["version"] = capture_to_manifest(version)
    store.write_text("native/version.txt", version.text or version.error)

    for name, command, timeout in READ_ONLY_COMMANDS:
        capture = run_capture(
            args,
            name,
            command,
            timeout=timeout,
        )
        clean_text = strip_cmdv1_text(capture.text) if capture.text else capture.error
        captures[name] = capture_to_manifest(capture)
        texts[name] = clean_text
        store.write_text(f"native/{name}.txt", clean_text)

    return {"captures": captures, "texts": texts}


def _name_pattern(name: str) -> re.Pattern[str]:
    return re.compile(rf"(^|/|\b){re.escape(name)}($|[\\s:/.-])", re.IGNORECASE)


def _path_present(text: str, name: str) -> bool:
    pattern = _name_pattern(name)
    return any(pattern.search(line) and not line.startswith("ls: ") for line in text.splitlines())


def _init_declared(text: str, name: str) -> bool:
    if name == "pd-mapper":
        return bool(re.search(r"service\s+\S*pd_mapper\b|service\s+\S*pd-mapper\b", text, re.IGNORECASE))
    return bool(re.search(rf"service\s+\S*{re.escape(name)}\b", text, re.IGNORECASE))


def _focus_lines(text: str, names: tuple[str, ...], limit: int = 80) -> list[str]:
    pattern = re.compile("|".join(re.escape(name) for name in names), re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in seen or not pattern.search(line):
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def summarize_surface(texts: dict[str, str]) -> dict[str, Any]:
    candidate_text = "\n".join([
        texts.get("known-path-stats", ""),
        texts.get("qmi-name-find", ""),
        texts.get("notifier-name-find", ""),
    ])
    init_text = texts.get("initrc-qmi", "")
    process_text = texts.get("process-snapshot", "")
    dmesg_text = texts.get("dmesg-qmi-tail", "")

    required = {
        name: {
            "binary_present": _path_present(candidate_text, name),
            "init_declared": _init_declared(init_text, name),
        }
        for name in REQUIRED_COMPANIONS
    }
    extras = {
        name: {
            "binary_present": _path_present(candidate_text, name),
            "init_declared": _init_declared(init_text, name),
            "process_present": _path_present(process_text, name),
        }
        for name in EXTRA_COMPANIONS
    }
    markers = {
        "qmi_server_connected": bool(re.search(r"QMI Server Connected|qmi_server_connected", dmesg_text, re.IGNORECASE)),
        "wlfw": bool(re.search(r"\bWLFW\b|wlfw", dmesg_text, re.IGNORECASE)),
        "bdf": bool(re.search(r"\bBDF\b|bdwlan|regdb", dmesg_text, re.IGNORECASE)),
        "wlan0": bool(re.search(r"\bwlan0\b", dmesg_text, re.IGNORECASE)),
        "modem_qmi_readiness": bool(re.search(r"Modem QMI Readiness", dmesg_text, re.IGNORECASE)),
    }
    return {
        "required": required,
        "extras": extras,
        "markers": markers,
        "candidate_lines": _focus_lines(candidate_text, REQUIRED_COMPANIONS + EXTRA_COMPANIONS, 120),
        "init_lines": _focus_lines(init_text, REQUIRED_COMPANIONS + EXTRA_COMPANIONS + ("wifi", "wlan"), 120),
        "process_lines": _focus_lines(process_text, REQUIRED_COMPANIONS + EXTRA_COMPANIONS + ("wifi", "wlan"), 80),
        "dmesg_lines": _focus_lines(dmesg_text, EXTRA_COMPANIONS + ("qmi", "wlfw", "bdf", "wlan0", "cnss"), 80),
    }


def build_checks(command: str, surface: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "read-only V555 plan; no device command executed")
        return checks
    if command == "preflight":
        add_check(checks, "preflight-scope", "pass", "info", "; ".join(READ_ONLY_GUARDS))
        add_check(checks, "device-command-policy", "pass", "info", "only version and toybox sh read-only commands are used")
        return checks
    if surface is None:
        add_check(checks, "surface-collected", "blocked", "blocker", "missing live surface")
        return checks

    required_missing = [
        name for name, item in surface["required"].items()
        if not item["binary_present"]
    ]
    extra_binaries = [
        name for name, item in surface["extras"].items()
        if item["binary_present"]
    ]
    extra_declared_missing = [
        name for name, item in surface["extras"].items()
        if item["init_declared"] and not item["binary_present"]
    ]
    readiness_markers = [
        name for name, present in surface["markers"].items()
        if present
    ]

    add_check(
        checks,
        "required-companion-binaries",
        "pass" if not required_missing else "blocked",
        "blocker",
        "missing=" + ",".join(required_missing),
        surface["candidate_lines"][:20],
        "restore/mount vendor system surfaces before companion replay",
    )
    add_check(
        checks,
        "extra-qmi-binary-candidates",
        "review" if extra_binaries else "pass",
        "warning",
        "present=" + ",".join(extra_binaries),
        surface["candidate_lines"][:40],
        "if present, plan a separate bounded start-only proof for the exact binary",
    )
    add_check(
        checks,
        "declared-but-missing-extras",
        "pass" if extra_declared_missing else "review",
        "info",
        "declared_missing=" + ",".join(extra_declared_missing),
        surface["init_lines"][:40],
        "do not replay declared services when the binary is absent from mounted images",
    )
    add_check(
        checks,
        "readiness-markers-absent",
        "pass" if not readiness_markers else "review",
        "warning",
        "present=" + ",".join(readiness_markers),
        surface["dmesg_lines"][:20],
        "if WLFW/QMI/BDF is already present, advance to HAL/scan gate",
    )
    add_check(
        checks,
        "no-wifi-bringup-side-effect",
        "pass" if not surface["markers"].get("wlan0") else "review",
        "blocker",
        f"wlan0={surface['markers'].get('wlan0')}",
        surface["dmesg_lines"][:20],
        "stop if read-only probe unexpectedly observes link-up side effects",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status not in {"pass"}]


def decide(command: str, checks: list[Check], surface: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v555-qmi-companion-gap-plan-ready",
            True,
            "read-only QMI companion gap plan is ready",
            "run preflight then live read-only classifier",
        )
    if command == "preflight":
        return (
            "v555-qmi-companion-gap-preflight-ready",
            True,
            "read-only guardrails are satisfied",
            "run V555 live classifier",
        )
    blockers = blocking_checks(checks)
    if blockers:
        return (
            "v555-qmi-companion-gap-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blocker before live Wi-Fi service work",
        )
    assert surface is not None
    extra_binaries = [
        name for name, item in surface["extras"].items()
        if item["binary_present"]
    ]
    extra_declared_missing = [
        name for name, item in surface["extras"].items()
        if item["init_declared"] and not item["binary_present"]
    ]
    if extra_binaries:
        return (
            "v555-extra-qmi-companion-candidate-found",
            True,
            "extra startable QMI companion candidates found: " + ", ".join(extra_binaries),
            "plan a separate bounded start-only proof for those candidates before HAL retry",
        )
    if extra_declared_missing:
        return (
            "v555-extra-qmi-companion-declared-but-absent",
            True,
            "init declares extra QMI companion services but mounted images have no startable binaries: "
            + ", ".join(extra_declared_missing),
            "skip absent-service replay and plan a combined companion plus HAL order proof",
        )
    return (
        "v555-no-extra-qmi-companion-candidate",
        True,
        "no startable extra QMI companion candidate was found beyond the six required companions",
        "plan a combined companion plus HAL order proof instead of qmiproxy/sysmon/service-notifier replay",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks", [])
    surface = manifest.get("surface") or {}
    required = surface.get("required") or {}
    extras = surface.get("extras") or {}
    markers = surface.get("markers") or {}
    required_rows = [
        [name, item.get("binary_present"), item.get("init_declared")]
        for name, item in sorted(required.items())
    ]
    extra_rows = [
        [name, item.get("binary_present"), item.get("init_declared"), item.get("process_present")]
        for name, item in sorted(extras.items())
    ]
    marker_rows = [[name, value] for name, value in sorted(markers.items())]
    check_rows = [
        [item["name"], item["status"], item["severity"], item["detail"], item["next_step"]]
        for item in checks
    ]
    lines = [
        f"# {PROOF_VERSION} Native QMI Companion Gap",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows) if check_rows else "- none",
        "",
        "## Required Companion Binaries",
        "",
        markdown_table(["name", "binary_present", "init_declared"], required_rows) if required_rows else "- not collected",
        "",
        "## Extra QMI Companion Candidates",
        "",
        markdown_table(["name", "binary_present", "init_declared", "process_present"], extra_rows) if extra_rows else "- not collected",
        "",
        "## Readiness Markers",
        "",
        markdown_table(["marker", "present"], marker_rows) if marker_rows else "- not collected",
        "",
        "## Guardrails",
        "",
    ]
    lines.extend(f"- `{guard}`" for guard in READ_ONLY_GUARDS)
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    live: dict[str, Any] | None = None
    surface: dict[str, Any] | None = None

    if args.command == "run":
        live = run_read_only_commands(args, store)
        surface = summarize_surface(live["texts"])

    checks = build_checks(args.command, surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks, surface)
    manifest: dict[str, Any] = {
        "schema": PROOF_SLUG,
        "version": PROOF_VERSION,
        "generated_at": now_iso(),
        "command": args.command,
        "host_metadata": collect_host_metadata(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_linkup": False,
        "external_ping_executed": False,
        "boot_partition_write_executed": False,
        "guardrails": list(READ_ONLY_GUARDS),
        "checks": [asdict(check) for check in checks],
        "surface": surface or {},
    }
    if live is not None:
        manifest["captures"] = live["captures"]
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(json.dumps({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
