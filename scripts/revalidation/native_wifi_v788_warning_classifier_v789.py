#!/usr/bin/env python3
"""V789 host-only classifier for the V788 pm_qos warning boundary."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v789-v788-warning-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v789-v788-warning-classifier.txt")
DEFAULT_V788_MANIFEST = Path("tmp/wifi/v788-clean-dsp-lower-readback/manifest.json")
DEFAULT_V788_DMESG_DELTA = Path("tmp/wifi/v788-clean-dsp-lower-readback/native/dmesg-delta.txt")
DEFAULT_V733_MANIFEST = Path("tmp/wifi/v733-holder-lower-companion/manifest.json")
DEFAULT_V735_MANIFEST = Path("tmp/wifi/v735-current-cnss-only-observer/manifest.json")
DEFAULT_V787_MANIFEST = Path("tmp/wifi/v787-clean-dsp-arm-only/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
WARNING_RE = re.compile(r"pm_qos_add_request|WARNING: CPU|msm_asoc_machine_probe|deferred_probe_work_func", re.IGNORECASE)


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
    parser.add_argument("--v788-manifest", type=Path, default=DEFAULT_V788_MANIFEST)
    parser.add_argument("--v788-dmesg-delta", type=Path, default=DEFAULT_V788_DMESG_DELTA)
    parser.add_argument("--v733-manifest", type=Path, default=DEFAULT_V733_MANIFEST)
    parser.add_argument("--v735-manifest", type=Path, default=DEFAULT_V735_MANIFEST)
    parser.add_argument("--v787-manifest", type=Path, default=DEFAULT_V787_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    if manifest.get("cycle") == "v788":
        lower = manifest.get("lower_readback") or {}
        live = lower.get("live") or {}
        markers = live.get("markers") or {}
        return {key: int(value or 0) for key, value in markers.items() if isinstance(value, int)}
    live = manifest.get("live") or {}
    markers = live.get("markers") or {}
    if "counts" in markers and isinstance(markers["counts"], dict):
        return {key: int(value or 0) for key, value in markers["counts"].items() if isinstance(value, int)}
    return {key: int(value or 0) for key, value in markers.items() if isinstance(value, int)}


def warning_context(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved), "lines": [], "first_index": -1}
    lines = [ANSI_RE.sub("", line.rstrip("\n")) for line in resolved.read_text(encoding="utf-8", errors="replace").splitlines()]
    first = next((idx for idx, line in enumerate(lines) if "pm_qos_add_request() called for already added request" in line), -1)
    if first < 0:
        first = next((idx for idx, line in enumerate(lines) if WARNING_RE.search(line)), -1)
    start = max(0, first - 12) if first >= 0 else 0
    end = min(len(lines), first + 58) if first >= 0 else min(len(lines), 40)
    selected = lines[start:end]
    return {
        "exists": True,
        "path": str(resolved),
        "first_index": first,
        "lines": selected,
        "has_pm_qos_duplicate": any("pm_qos_add_request() called for already added request" in line for line in lines),
        "has_asoc_probe": any("msm_asoc_machine_probe" in line for line in lines),
        "has_deferred_probe": any("deferred_probe_work_func" in line for line in lines),
        "has_cnss_calltrace": any("cnss" in line.lower() and "Call trace" in line for line in selected),
    }


def reference_row(name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    counts = marker_counts(manifest)
    return {
        "name": name,
        "path": manifest.get("path", ""),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "kernel_warning": counts.get("kernel_warning", counts.get("pm_qos_warning", 0)),
        "service_notifier": counts.get("service_notifier", 0),
        "sysmon_qmi": counts.get("sysmon_qmi", 0),
        "wlfw": counts.get("wlfw", 0),
        "wlan0": counts.get("wlan0", 0),
    }


def build_checks(args: argparse.Namespace, rows: list[dict[str, Any]], context: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    row_by_name = {row["name"]: row for row in rows}
    v788 = row_by_name.get("v788", {})
    historical_warning_free = all((row_by_name.get(name, {}).get("kernel_warning") or 0) == 0 for name in ("v733", "v735"))
    checks.append(Check(
        "v788-input",
        "pass" if v788.get("decision") == "v788-clean-dsp-lower-readback-blocked" else "blocked",
        "blocker",
        f"decision={v788.get('decision')} pass={v788.get('pass')}",
        [str(repo_path(args.v788_manifest))],
        "complete V788 before warning classification",
    ))
    checks.append(Check(
        "warning-context",
        "pass" if context.get("has_pm_qos_duplicate") and context.get("has_asoc_probe") and context.get("has_deferred_probe") else "blocked",
        "blocker",
        f"pm_qos={context.get('has_pm_qos_duplicate')} asoc={context.get('has_asoc_probe')} deferred={context.get('has_deferred_probe')}",
        [str(repo_path(args.v788_dmesg_delta))],
        "recapture V788 dmesg delta if warning context is missing",
    ))
    checks.append(Check(
        "historical-boundary",
        "pass" if historical_warning_free else "review",
        "warn",
        f"v733={row_by_name.get('v733', {}).get('kernel_warning')} v735={row_by_name.get('v735', {}).get('kernel_warning')}",
        [str(repo_path(args.v733_manifest)), str(repo_path(args.v735_manifest))],
        "treat V788 warning as new unless older matching warnings are found",
    ))
    checks.append(Check(
        "wlff-interface-absent",
        "pass" if not v788.get("wlfw") and not v788.get("wlan0") else "review",
        "warn",
        f"wlfw={v788.get('wlfw')} wlan0={v788.get('wlan0')}",
        [str(repo_path(args.v788_manifest))],
        "if WLFW or wlan0 exists, route to interface capture instead of warning isolation",
    ))
    return checks


def decide(args: argparse.Namespace, checks: list[Check], rows: list[dict[str, Any]], context: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v789-v788-warning-classifier-plan-ready", True, "plan-only; no device command executed", "run host-only V789 classifier"
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "v789-v788-warning-classifier-blocked", False, "blocked by " + ", ".join(blockers), "repair evidence inputs before selecting next gate"
    v788 = next(row for row in rows if row["name"] == "v788")
    if v788.get("service_notifier", 0) and context.get("has_asoc_probe"):
        return (
            "v789-pm-qos-audio-deferred-probe-boundary-classified",
            True,
            "V788 warning is a new pm_qos duplicate-request boundary in msm_asoc_machine_probe after service-notifier/audio deferred probe activity",
            "next live gate should be narrower than CNSS-only: clean-DSP lower-only readback first, with warning stop and no HAL/scan/connect",
        )
    return (
        "v789-pm-qos-warning-classified",
        True,
        "V788 warning boundary is confirmed but source attribution remains coarse",
        "use a narrower lower-only replay before repeating CNSS-only or widening toward HAL/connect",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [row["name"], row["decision"], row["pass"], row["kernel_warning"], row["service_notifier"], row["sysmon_qmi"], row["wlfw"], row["wlan0"]]
        for row in manifest["references"]
    ]
    return "\n".join([
        "# V789 V788 Warning Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## References",
        "",
        markdown_table(["name", "decision", "pass", "kernel_warning", "service_notifier", "sysmon_qmi", "wlfw", "wlan0"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Warning Context",
        "",
        "```text",
        "\n".join(manifest["warning_context"].get("lines", [])),
        "```",
        "",
        "## Safety",
        "",
        "- Host-only classifier.",
        "- No device command, reboot, mount, daemon start, Wi-Fi action, credential use, network change, flash, or partition write.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    manifests = {
        "v788": load_json(args.v788_manifest),
        "v733": load_json(args.v733_manifest),
        "v735": load_json(args.v735_manifest),
        "v787": load_json(args.v787_manifest),
    }
    rows = [reference_row(name, manifest) for name, manifest in manifests.items()]
    context = warning_context(args.v788_dmesg_delta)
    if context.get("lines"):
        store.write_text("warning-context.txt", "\n".join(context["lines"]) + "\n")
    checks = build_checks(args, rows, context)
    decision, passed, reason, next_step = decide(args, checks, rows, context)
    manifest = {
        "cycle": "v789",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "references": rows,
        "warning_context": context,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
