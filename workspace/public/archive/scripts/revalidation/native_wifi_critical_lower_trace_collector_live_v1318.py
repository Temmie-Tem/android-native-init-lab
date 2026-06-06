#!/usr/bin/env python3
"""V1318 bounded critical-only lower tracefs collector.

V1317 showed the V1316 saved trace lines were dominated by IRQ/clock noise.
V1318 reuses the same bounded late ``per_proxy`` PM-service path but enables
only critical lower tracefs events: regulator, GPIO, power, and msm_pil_event.
It preserves a larger critical-only line sample and still avoids Wi-Fi HAL,
scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes,
direct eSoC ioctls, flash, boot image writes, and partition writes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import native_wifi_lower_trace_line_classifier_v1317 as v1317
import native_wifi_tracefs_lower_event_collector_live_v1316 as v1316

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1318-critical-lower-trace-collector-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1318-critical-lower-trace-collector-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1318-critical-lower-trace-collector-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1318-critical-lower-trace-collector-plan.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1318_CRITICAL_LOWER_TRACE_COLLECTOR_2026-05-31.md")
CYCLE_LABEL = "v1318"
CYCLE_NAME = "V1318"
SUMMARY_HEADING = "V1318 Critical Lower Trace Collector"
EVIDENCE_FILE_PREFIX = "v1318"
LINE_LIMIT = 2000

CRITICAL_LOWER_TRACE_EVENTS = (
    ("regulator", "regulator_enable", "critical"),
    ("regulator", "regulator_enable_complete", "critical"),
    ("regulator", "regulator_set_voltage", "critical"),
    ("regulator", "regulator_set_voltage_complete", "critical"),
    ("gpio", "gpio_direction", "critical"),
    ("gpio", "gpio_value", "critical"),
    ("power", "power_domain_target", "critical"),
    ("power", "device_pm_callback_start", "critical"),
    ("power", "device_pm_callback_end", "critical"),
    ("msm_pil_event", "pil_event", "critical"),
    ("msm_pil_event", "pil_notif", "critical"),
    ("msm_pil_event", "pil_func", "critical"),
)


def classify_manifest_lines(manifest: dict[str, Any]) -> dict[str, Any]:
    lower = v1316.lower_static(manifest)
    classification = v1317.classify_lines(list(lower.get("lines") or []))
    target_gpio_samples = classification.get("target_gpio_samples") or []
    gpio135_high = [
        item for item in target_gpio_samples
        if item.get("gpio") == 135 and "set 1" in str(item.get("line", ""))
    ]
    first_gpio135_high = gpio135_high[0].get("timestamp") if gpio135_high else None
    last_timestamp = classification.get("last_timestamp")
    post_gpio135_span = None
    if first_gpio135_high is not None and last_timestamp is not None:
        post_gpio135_span = float(last_timestamp) - float(first_gpio135_high)
    gpio_counts = classification.get("gpio_counts") or {}
    classification.update({
        "gpio1270_line_count": int(gpio_counts.get("1270", 0)),
        "gpio135_line_count": int(gpio_counts.get("135", 0)),
        "gpio142_line_count": int(gpio_counts.get("142", 0)),
        "gpio135_high_count": len(gpio135_high),
        "first_gpio135_high_timestamp": first_gpio135_high,
        "post_gpio135_sample_span_sec": post_gpio135_span,
        "esoc_pil_notif_count": sum(
            1 for item in classification.get("target_keyword_samples") or []
            if item.get("event") == "pil_notif" and "fw=esoc0" in str(item.get("line", ""))
        ),
    })
    return classification


def decide_v1318(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1318-critical-lower-trace-collector-plan-ready",
            True,
            "plan-only; no device command or tracefs control write executed",
            "run V1318 bounded critical-only lower trace collector around the late per_proxy PM-service path",
        )

    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    lower = v1316.lower_static(manifest)
    pm_esoc0_attempt, pm_esoc0_basis = v1316.pm_service_esoc0_reach(manifest)
    manifest["pm_service_esoc0_reach_basis"] = pm_esoc0_basis
    classification = classify_manifest_lines(manifest)
    manifest["critical_line_classification"] = classification

    result = tracefs.get("result", "")
    enable_failures = lower.get("enable_failures") or {}
    disable_failures = lower.get("disable_failures") or {}
    critical_count = int(lower.get("critical_count") or 0)
    line_count = int(classification.get("line_count") or 0)
    target_keywords = int(classification.get("target_keyword_line_count") or 0)
    target_gpios = int(classification.get("target_gpio_line_count") or 0)

    if result != "tracefs-uprobe-pass":
        return (
            "v1318-critical-tracefs-collector-failed",
            False,
            f"tracefs collector result={result}",
            "inspect V1318 collector transcript and cleanup before retry",
        )
    if enable_failures or disable_failures:
        return (
            "v1318-critical-tracefs-cleanup-review",
            False,
            f"enable_failures={enable_failures} disable_failures={disable_failures}",
            "cleanup tracefs event state before another live gate",
        )
    if not pm_esoc0_attempt:
        return (
            "v1318-pm-service-esoc0-not-reached",
            False,
            "late per_proxy path did not reach PM-service /dev/subsys_esoc0",
            "repair PM-service path before interpreting critical lower trace events",
        )
    if critical_count <= 0:
        return (
            "v1318-no-critical-events-before-block",
            True,
            "PM-service reached mdm_subsys_powerup but critical-only tracefs events stayed silent",
            "classify provider wait site or add narrower driver-specific read-only observation before any lower mutation",
        )
    if line_count <= 10:
        return (
            "v1318-critical-line-preservation-insufficient",
            False,
            f"critical_count={critical_count} but preserved_line_count={line_count}, not better than V1317's 10-line critical sample",
            "increase critical-only line capture before selecting the next lower gate",
        )
    if target_keywords or target_gpios:
        return (
            "v1318-target-critical-lines-captured",
            True,
            (
                f"critical-only sample includes target evidence: target_keyword_lines={target_keywords} "
                f"target_gpio_lines={target_gpios}; gpio142_lines={classification.get('gpio142_line_count')}"
            ),
            "build the next gate around GPIO135 assertion with GPIO142/PCIe response absence as the explicit blocker",
        )
    return (
        "v1318-critical-only-lines-captured-no-target",
        True,
        (
            f"critical-only collector preserved {line_count} lines from critical_count={critical_count}, "
            "but still found no SDX50M/PCIe/MHI/WLAN/CNSS target keywords or target GPIO 135/142/1270"
        ),
        "classify full critical-only names/GPIOs, then decide whether to add driver-specific tracepoints or lower timing probes",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lower = v1316.lower_static(manifest)
    classification = manifest.get("critical_line_classification") or classify_manifest_lines(manifest)
    safety_rows = [[key, manifest.get(key)] for key in (
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
            item.get("event", ""),
            item.get("category", ""),
            item.get("name", ""),
            item.get("gpio", ""),
            item.get("line", ""),
        ]
        for item in (classification.get("critical_samples") or [])[:24]
    ]
    target_rows = [
        [
            item.get("event", ""),
            item.get("category", ""),
            item.get("name", ""),
            item.get("gpio", ""),
            item.get("line", ""),
        ]
        for item in (
            list(classification.get("target_keyword_samples") or [])
            + list(classification.get("target_gpio_samples") or [])
        )[:24]
    ]
    return "\n".join([
        f"# {SUMMARY_HEADING}",
        "",
        f"- generated: `{manifest.get('generated_at', '')}`",
        f"- command: `{manifest.get('command', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        f"- next_step: {manifest.get('next_step', '')}",
        "",
        "## Critical Static Events",
        "",
        markdown_table(["field", "value"], [
            ["enabled count", lower.get("enabled_count", 0)],
            ["total count", lower.get("total_count", 0)],
            ["critical count", lower.get("critical_count", 0)],
            ["group counts", json.dumps(lower.get("group_counts") or {}, sort_keys=True)],
            ["lower trace line count", lower.get("line_count", 0)],
            ["enable failures", json.dumps(lower.get("enable_failures") or {}, sort_keys=True)],
            ["disable failures", json.dumps(lower.get("disable_failures") or {}, sort_keys=True)],
            ["PM-service eSoC reach basis", manifest.get("pm_service_esoc0_reach_basis", "")],
        ]),
        "",
        "## Line Classification",
        "",
        markdown_table(["field", "value"], [
            ["line count", classification.get("line_count", 0)],
            ["critical sample lines", classification.get("critical_line_count", 0)],
            ["target keyword lines", classification.get("target_keyword_line_count", 0)],
            ["target GPIO lines", classification.get("target_gpio_line_count", 0)],
            ["GPIO1270 / GPIO135 / GPIO142 lines", f"{classification.get('gpio1270_line_count', 0)} / {classification.get('gpio135_line_count', 0)} / {classification.get('gpio142_line_count', 0)}"],
            ["GPIO135 high count", classification.get("gpio135_high_count", 0)],
            ["post GPIO135 sample span sec", classification.get("post_gpio135_sample_span_sec")],
            ["eSoC PIL notif count", classification.get("esoc_pil_notif_count", 0)],
            ["event counts", json.dumps(classification.get("event_counts") or {}, sort_keys=True)],
            ["category counts", json.dumps(classification.get("category_counts") or {}, sort_keys=True)],
            ["GPIO counts", json.dumps(classification.get("gpio_counts") or {}, sort_keys=True)],
            ["name counts", json.dumps(classification.get("name_counts") or {}, sort_keys=True)],
        ]),
        "",
        "## Critical Samples",
        "",
        markdown_table(["event", "category", "name", "gpio", "line"], critical_rows),
        "",
        "## Target Samples",
        "",
        markdown_table(["event", "category", "name", "gpio", "line"], target_rows),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    lower = v1316.lower_static(manifest)
    classification = manifest.get("critical_line_classification") or classify_manifest_lines(manifest)
    target_rows = [
        [
            item.get("event", ""),
            item.get("category", ""),
            item.get("name", ""),
            item.get("gpio", ""),
            item.get("line", ""),
        ]
        for item in (
            list(classification.get("target_keyword_samples") or [])
            + list(classification.get("target_gpio_samples") or [])
        )[:24]
    ]
    return "\n".join([
        "# Native Init V1318 Critical Lower Trace Collector",
        "",
        "## Summary",
        "",
        "- Cycle: `V1318`",
        "- Type: bounded live collector",
        f"- Decision: `{manifest.get('decision', '')}`",
        f"- Result: {'PASS' if manifest.get('pass') else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json`",
        "  - `tmp/wifi/v1318-critical-lower-trace-collector-live/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_critical_lower_trace_collector_live_v1318.py`",
        "",
        "V1318 reruns the bounded late `per_proxy` PM-service path with only critical",
        "lower tracefs events enabled. This removes broad IRQ/clock noise from V1316",
        "and preserves a larger sample of regulator/GPIO/power/PIL lines.",
        "",
        "## Result",
        "",
        markdown_table(["field", "value"], [
            ["decision", manifest.get("decision", "")],
            ["critical total count", lower.get("critical_count", 0)],
            ["line count", classification.get("line_count", 0)],
            ["target keyword lines", classification.get("target_keyword_line_count", 0)],
            ["target GPIO lines", classification.get("target_gpio_line_count", 0)],
            ["GPIO1270 / GPIO135 / GPIO142 lines", f"{classification.get('gpio1270_line_count', 0)} / {classification.get('gpio135_line_count', 0)} / {classification.get('gpio142_line_count', 0)}"],
            ["GPIO135 high count", classification.get("gpio135_high_count", 0)],
            ["post GPIO135 sample span sec", classification.get("post_gpio135_sample_span_sec")],
            ["eSoC PIL notif count", classification.get("esoc_pil_notif_count", 0)],
            ["group counts", json.dumps(lower.get("group_counts") or {}, sort_keys=True)],
            ["event counts", json.dumps(classification.get("event_counts") or {}, sort_keys=True)],
            ["category counts", json.dumps(classification.get("category_counts") or {}, sort_keys=True)],
            ["GPIO counts", json.dumps(classification.get("gpio_counts") or {}, sort_keys=True)],
        ]),
        "",
        "## Target Samples",
        "",
        markdown_table(["event", "category", "name", "gpio", "line"], target_rows),
        "",
        "## Next",
        "",
        str(manifest.get("next_step", "")),
        "",
        "## Safety",
        "",
        "No Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping,",
        "PMIC write, userspace GPIO line request/hold, direct eSoC ioctl, direct GDSC",
        "write, flash, boot image write, or partition write occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    lower = v1316.lower_static(manifest)
    classification = manifest.get("critical_line_classification") or classify_manifest_lines(manifest)
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"critical_count:        {lower.get('critical_count', 0)}")
    print(f"line_count:            {classification.get('line_count', 0)}")
    print(f"target_keyword_lines:  {classification.get('target_keyword_line_count', 0)}")
    print(f"target_gpio_lines:     {classification.get('target_gpio_line_count', 0)}")
    print(f"wifi_bringup_executed: {manifest.get('wifi_bringup_executed')}")
    print(f"evidence: {manifest.get('_run_dir')}")


def configure_v1316() -> None:
    v1316.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1316.LATEST_POINTER = LATEST_POINTER
    v1316.PLAN_OUT_DIR = PLAN_OUT_DIR
    v1316.PLAN_LATEST_POINTER = PLAN_LATEST_POINTER
    v1316.CYCLE_LABEL = CYCLE_LABEL
    v1316.CYCLE_NAME = CYCLE_NAME
    v1316.SUMMARY_HEADING = SUMMARY_HEADING
    v1316.EVIDENCE_FILE_PREFIX = EVIDENCE_FILE_PREFIX
    v1316.LOWER_TRACE_EVENTS = CRITICAL_LOWER_TRACE_EVENTS
    v1316.LOWER_TRACE_LINE_LIMIT = LINE_LIMIT
    v1316.decide_v1316 = decide_v1318
    v1316.render_summary = render_summary
    v1316.print_result = print_result


def maybe_write_report() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] not in {"run", "reclassify"}:
        return
    manifest_path = repo_path(DEFAULT_OUT_DIR / "manifest.json")
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))


def main() -> int:
    configure_v1316()
    rc = v1316.main()
    maybe_write_report()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
