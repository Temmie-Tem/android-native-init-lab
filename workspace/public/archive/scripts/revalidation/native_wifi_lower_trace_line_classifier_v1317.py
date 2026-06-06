#!/usr/bin/env python3
"""V1317 host-only lower trace-line classifier.

V1316 proved selected tracefs lower events fire while the bounded late
``per_proxy`` PM-service path blocks in ``mdm_subsys_powerup``.  V1317 does not
contact the device.  It classifies the captured trace lines by event, payload
name, actor, target relevance, and noise category so the next live gate can
drop broad background events and focus on SDX50M-relevant first-power-on
signals.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1317-lower-trace-line-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1317-lower-trace-line-classifier.txt")
DEFAULT_V1316_MANIFEST = Path("tmp/wifi/v1316-tracefs-lower-event-collector-live/manifest.json")
DEFAULT_V1316_OBSERVER = Path(
    "tmp/wifi/v1316-tracefs-lower-event-collector-live/host/pm-server-wchan-tracefs-observer.txt"
)
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1317_LOWER_TRACE_LINE_CLASSIFIER_2026-05-31.md")

TARGET_KEYWORDS = (
    "sdx",
    "mdm",
    "esoc",
    "mhi",
    "pcie",
    "wlan",
    "qca",
    "cnss",
    "icnss",
    "gcc_pcie",
    "pcie_0",
    "pcie_1",
)
CRITICAL_EVENTS = {
    "regulator_enable",
    "regulator_enable_complete",
    "regulator_set_voltage",
    "regulator_set_voltage_complete",
    "gpio_direction",
    "gpio_value",
    "power_domain_target",
    "device_pm_callback_start",
    "device_pm_callback_end",
    "pil_event",
    "pil_notif",
    "pil_func",
}
BACKGROUND_EVENTS = {
    "irq_handler_entry",
    "irq_handler_exit",
    "clk_enable",
    "clk_enable_complete",
    "clk_prepare",
    "clk_prepare_complete",
}
TARGET_GPIOS = {135: "ap2mdm-status", 142: "mdm2ap-status", 1270: "pmic-soft-reset"}
LINE_RE = re.compile(r"^\s*(?P<comm>.+?)-(?P<pid>\d+)\s+\[[^\]]+\]\s+\S+\s+(?P<ts>\d+\.\d+): (?P<event>[A-Za-z0-9_]+): (?P<payload>.*)$")
NAME_RE = re.compile(r"\bname=([^\s,]+)")
GPIO_RE = re.compile(r": gpio_(?:value|direction): (?P<gpio>\d+)\b")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1316-manifest", type=Path, default=DEFAULT_V1316_MANIFEST)
    parser.add_argument("--v1316-observer", type=Path, default=DEFAULT_V1316_OBSERVER)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def extract_lower_trace_block(observer_text: str) -> list[str]:
    marker_begin = "lower_trace_lines_begin"
    marker_end = "lower_trace_lines_end"
    start = observer_text.find(marker_begin)
    if start < 0:
        return []
    start += len(marker_begin)
    end = observer_text.find(marker_end, start)
    if end < 0:
        return []
    return [line.rstrip() for line in observer_text[start:end].splitlines() if line.strip()]


def tracefs_analysis(v1316: dict[str, Any]) -> dict[str, Any]:
    return ((v1316.get("analysis") or {}).get("tracefs_uprobe") or {})


def lower_static(v1316: dict[str, Any]) -> dict[str, Any]:
    return tracefs_analysis(v1316).get("lower_static_events") or {}


def category_for(text: str, event: str) -> str:
    lower = text.lower()
    if any(keyword in lower for keyword in TARGET_KEYWORDS):
        return "target_keyword"
    if "ufs" in lower or "ufshc" in lower:
        return "background_storage_ufs"
    if "dwc3" in lower:
        return "background_usb_dwc3"
    if "arch_timer" in lower:
        return "background_timer"
    if "sdcc" in lower or "mmc" in lower:
        return "background_sdcard"
    if "msm_drm" in lower:
        return "background_display"
    if "apps_rsc" in lower:
        return "background_apps_rsc"
    if "pm8150" in lower:
        return "generic_pmic_regulator"
    if event in BACKGROUND_EVENTS:
        return "background_unclassified"
    return "critical_unclassified"


def parse_line(line: str) -> dict[str, Any]:
    match = LINE_RE.match(line)
    event = ""
    comm = ""
    pid = ""
    timestamp = None
    payload = ""
    if match:
        event = match.group("event")
        comm = match.group("comm").strip()
        pid = match.group("pid")
        timestamp = float(match.group("ts"))
        payload = match.group("payload")
    else:
        event_match = re.search(r": ([A-Za-z0-9_]+):", line)
        event = event_match.group(1) if event_match else ""
        payload = line
    name_match = NAME_RE.search(line)
    gpio_match = GPIO_RE.search(line)
    gpio = int(gpio_match.group("gpio")) if gpio_match else None
    category = category_for(line, event)
    return {
        "line": line,
        "event": event,
        "comm": comm,
        "pid": pid,
        "timestamp": timestamp,
        "payload": payload,
        "name": name_match.group(1) if name_match else "",
        "gpio": gpio,
        "target_gpio": TARGET_GPIOS.get(gpio, ""),
        "critical": event in CRITICAL_EVENTS,
        "category": category,
        "target_keyword": category == "target_keyword",
    }


def counter_rows(counter: collections.Counter[str], limit: int = 24) -> list[list[Any]]:
    return [[key, value] for key, value in counter.most_common(limit)]


def classify_lines(lines: list[str]) -> dict[str, Any]:
    parsed = [parse_line(line) for line in lines]
    event_counts = collections.Counter(item["event"] for item in parsed if item["event"])
    name_counts = collections.Counter(item["name"] for item in parsed if item["name"])
    category_counts = collections.Counter(item["category"] for item in parsed)
    gpio_counts = collections.Counter(str(item["gpio"]) for item in parsed if item["gpio"] is not None)
    critical_lines = [item for item in parsed if item["critical"]]
    target_lines = [item for item in parsed if item["target_keyword"]]
    target_gpio_lines = [item for item in parsed if item["target_gpio"]]
    timestamps = [item["timestamp"] for item in parsed if item["timestamp"] is not None]
    return {
        "line_count": len(lines),
        "parsed_count": len(parsed),
        "event_counts": dict(event_counts),
        "name_counts": dict(name_counts),
        "category_counts": dict(category_counts),
        "gpio_counts": dict(gpio_counts),
        "critical_line_count": len(critical_lines),
        "target_keyword_line_count": len(target_lines),
        "target_gpio_line_count": len(target_gpio_lines),
        "first_timestamp": min(timestamps) if timestamps else None,
        "last_timestamp": max(timestamps) if timestamps else None,
        "sample_span_sec": (max(timestamps) - min(timestamps)) if timestamps else None,
        "critical_samples": critical_lines[:40],
        "target_keyword_samples": target_lines[:20],
        "target_gpio_samples": target_gpio_lines[:20],
        "parsed_samples": parsed[:20],
    }


def summarize_v1316(v1316: dict[str, Any]) -> dict[str, Any]:
    lower = lower_static(v1316)
    tracefs = tracefs_analysis(v1316)
    return {
        "decision": v1316.get("decision", ""),
        "pass": bool_value(v1316.get("pass")),
        "tracefs_result": tracefs.get("result", ""),
        "pm_service_esoc0_reach_basis": v1316.get("pm_service_esoc0_reach_basis", ""),
        "lower_enabled_count": int_value(lower.get("enabled_count")),
        "lower_total_count": int_value(lower.get("total_count")),
        "lower_critical_count": int_value(lower.get("critical_count")),
        "lower_noise_count": int_value(lower.get("noise_count")),
        "lower_group_counts": lower.get("group_counts") or {},
        "lower_manifest_line_count": int_value(lower.get("line_count")),
    }


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest["command"] == "plan":
        return (
            "v1317-lower-trace-line-classifier-plan-ready",
            True,
            "plan-only; no device command, tracefs control write, or live action executed",
            "run host-only V1317 classifier against existing V1316 evidence",
        )
    v1316 = manifest["v1316"]
    classified = manifest["classification"]
    if not v1316["pass"] or v1316["decision"] != "v1316-critical-first-power-on-events-captured":
        return (
            "v1317-missing-v1316-pass-evidence",
            False,
            f"V1316 evidence is not the expected PASS: decision={v1316['decision']} pass={v1316['pass']}",
            "refresh or reclassify V1316 before line classification",
        )
    if classified["line_count"] == 0:
        return (
            "v1317-no-lower-trace-lines",
            False,
            "V1316 manifest/observer did not contain lower trace lines",
            "rerun a bounded collector with lower trace line capture enabled",
        )
    if classified["target_keyword_line_count"] > 0 or classified["target_gpio_line_count"] > 0:
        return (
            "v1317-sdx50m-relevant-lower-lines-present",
            True,
            (
                "captured lower trace sample contains SDX50M target keywords or target GPIOs; "
                f"target_keyword_lines={classified['target_keyword_line_count']} "
                f"target_gpio_lines={classified['target_gpio_line_count']}"
            ),
            "build the next gate around the identified target trace lines before any lower mutation",
        )
    return (
        "v1317-sample-background-noise-classified-next-critical-only-dump",
        True,
        (
            "V1316 captured critical event counts, but stored trace-line sample contains no SDX50M/PCIe/MHI/WLAN "
            f"keywords and no target GPIO 135/142/1270 lines; critical_sample_lines={classified['critical_line_count']}"
        ),
        "run a narrower V1318 critical-only trace collector that drops IRQ/clock noise and preserves more regulator/gpio/PIL lines",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1316_raw = read_json(args.v1316_manifest)
    observer_text = read_text(args.v1316_observer)
    lower_lines = extract_lower_trace_block(observer_text)
    if not lower_lines:
        lower_lines = list((lower_static(v1316_raw).get("lines") or []))
    classification = classify_lines(lower_lines)
    return {
        "cycle": "v1317",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1316_manifest": str(repo_path(args.v1316_manifest)),
            "v1316_observer": str(repo_path(args.v1316_observer)),
            "observer_exists": repo_path(args.v1316_observer).exists(),
            "observer_lower_block_lines": len(extract_lower_trace_block(observer_text)),
        },
        "v1316": summarize_v1316(v1316_raw),
        "classification": classification,
        "device_command_executed": False,
        "tracefs_write_executed": False,
        "pm_service_trigger_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    v1316 = manifest["v1316"]
    safety_rows = [[key, manifest.get(key)] for key in (
        "device_command_executed",
        "tracefs_write_executed",
        "pm_service_trigger_executed",
        "pmic_write_executed",
        "gpio_line_request_executed",
        "direct_esoc_ioctl_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]
    critical_rows = [
        [
            item["event"],
            item["category"],
            item.get("name", ""),
            item.get("gpio", ""),
            item["line"],
        ]
        for item in classification["critical_samples"][:16]
    ]
    return "\n".join([
        "# V1317 Lower Trace-Line Classifier",
        "",
        f"- generated: `{manifest.get('generated_at', '')}`",
        f"- command: `{manifest.get('command', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        "## V1316 Input",
        "",
        markdown_table(["field", "value"], [
            ["decision", v1316["decision"]],
            ["pass", v1316["pass"]],
            ["tracefs result", v1316["tracefs_result"]],
            ["PM-service eSoC reach basis", v1316["pm_service_esoc0_reach_basis"]],
            ["lower total / critical / noise", f"{v1316['lower_total_count']} / {v1316['lower_critical_count']} / {v1316['lower_noise_count']}"],
            ["lower group counts", json.dumps(v1316["lower_group_counts"], sort_keys=True)],
        ]),
        "",
        "## Trace-Line Classification",
        "",
        markdown_table(["field", "value"], [
            ["line count", classification["line_count"]],
            ["sample span sec", classification["sample_span_sec"]],
            ["critical sample lines", classification["critical_line_count"]],
            ["target keyword lines", classification["target_keyword_line_count"]],
            ["target GPIO lines", classification["target_gpio_line_count"]],
            ["event counts", json.dumps(classification["event_counts"], sort_keys=True)],
            ["category counts", json.dumps(classification["category_counts"], sort_keys=True)],
            ["GPIO counts", json.dumps(classification["gpio_counts"], sort_keys=True)],
        ]),
        "",
        "## Top Names",
        "",
        markdown_table(["name", "count"], counter_rows(collections.Counter(classification["name_counts"]))),
        "",
        "## Critical Samples",
        "",
        markdown_table(["event", "category", "name", "gpio", "line"], critical_rows),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    v1316 = manifest["v1316"]
    return "\n".join([
        "# Native Init V1317 Lower Trace-Line Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1317`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1317-lower-trace-line-classifier/manifest.json`",
        "  - `tmp/wifi/v1317-lower-trace-line-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_lower_trace_line_classifier_v1317.py`",
        "",
        "V1317 classifies the V1316 lower trace-line sample without contacting the device.",
        "It confirms that V1316 captured lower-event counts while `pm-service` reached",
        "`/dev/subsys_esoc0` / `mdm_subsys_powerup`, but the stored line sample is not yet",
        "specific enough to identify SDX50M first-power-on rails or target GPIOs.",
        "",
        "## Result",
        "",
        markdown_table(["field", "value"], [
            ["V1316 decision", v1316["decision"]],
            ["V1316 lower total / critical / noise", f"{v1316['lower_total_count']} / {v1316['lower_critical_count']} / {v1316['lower_noise_count']}"],
            ["classified line count", classification["line_count"]],
            ["critical sample lines", classification["critical_line_count"]],
            ["target keyword lines", classification["target_keyword_line_count"]],
            ["target GPIO lines", classification["target_gpio_line_count"]],
            ["event counts", json.dumps(classification["event_counts"], sort_keys=True)],
            ["category counts", json.dumps(classification["category_counts"], sort_keys=True)],
            ["GPIO counts", json.dumps(classification["gpio_counts"], sort_keys=True)],
        ]),
        "",
        "The stored sample contains critical lines for `ufs_phy_gdsc`, `pm8150l_l3`,",
        "and GPIO `96`, but no lines containing SDX50M/PCIe/MHI/WLAN/CNSS target",
        "keywords and no target GPIO `135`, `142`, or `1270`. The broad IRQ/clock",
        "capture also consumed most of the saved trace-line budget.",
        "",
        "## Decision",
        "",
        "V1318 should be a narrower bounded live collector, not a lower mutation.",
        "It should drop broad IRQ/clock events and preserve more critical-only",
        "`regulator`, `gpio`, `power`, and `msm_pil_event` lines around the same",
        "late `per_proxy` PM-service path.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, tracefs write, PM-service trigger,",
        "PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, direct GDSC",
        "write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external",
        "ping, flash, boot image write, or partition write occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    classification = manifest["classification"]
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"line_count:             {classification['line_count']}")
    print(f"critical_sample_lines:  {classification['critical_line_count']}")
    print(f"target_keyword_lines:   {classification['target_keyword_line_count']}")
    print(f"target_gpio_lines:      {classification['target_gpio_line_count']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    decision, passed, reason, next_step = decide(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
