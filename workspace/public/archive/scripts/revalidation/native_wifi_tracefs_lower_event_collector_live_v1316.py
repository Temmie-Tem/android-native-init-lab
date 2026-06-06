#!/usr/bin/env python3
"""V1316 bounded tracefs lower-event collector.

V1315 proved the selected lower tracefs events exist and have readable formats.
V1316 enables those events only for the existing bounded late per_proxy
PM-service path, collects event counts/lines, disables them, and cleans up.

It does not start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes,
external ping, write PMIC/GPIO/GDSC controls, issue direct eSoC ioctls, flash,
or write partitions.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1316-tracefs-lower-event-collector-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1316-tracefs-lower-event-collector-live.txt")
PLAN_OUT_DIR = Path("tmp/wifi/v1316-tracefs-lower-event-collector-plan")
PLAN_LATEST_POINTER = Path("tmp/wifi/latest-v1316-tracefs-lower-event-collector-plan.txt")
HELPER_MARKER = "a90_android_execns_probe v275"
HELPER_SHA256 = "66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677"
CYCLE_LABEL = "v1316"
CYCLE_NAME = "V1316"
SUMMARY_HEADING = "V1316 Tracefs Lower-Event Collector"
EVIDENCE_FILE_PREFIX = "v1316"

LOWER_TRACE_EVENTS = (
    ("regulator", "regulator_enable", "critical"),
    ("regulator", "regulator_enable_complete", "critical"),
    ("regulator", "regulator_set_voltage", "critical"),
    ("regulator", "regulator_set_voltage_complete", "critical"),
    ("gpio", "gpio_direction", "critical"),
    ("gpio", "gpio_value", "critical"),
    ("irq", "irq_handler_entry", "noise"),
    ("irq", "irq_handler_exit", "noise"),
    ("clk", "clk_enable", "noise"),
    ("clk", "clk_enable_complete", "noise"),
    ("clk", "clk_prepare", "noise"),
    ("clk", "clk_prepare_complete", "noise"),
    ("power", "power_domain_target", "critical"),
    ("power", "device_pm_callback_start", "critical"),
    ("power", "device_pm_callback_end", "critical"),
    ("msm_pil_event", "pil_event", "critical"),
    ("msm_pil_event", "pil_notif", "critical"),
    ("msm_pil_event", "pil_func", "critical"),
)
LOWER_TRACE_LINE_LIMIT = 260

STATIC_COUNT_RE = re.compile(r"^static_event\.([A-Za-z0-9_.-]+)\.count=(\d+)$", re.MULTILINE)
STATIC_STATUS_RE = re.compile(r"^static_event\.([A-Za-z0-9_.-]+)\.([A-Za-z0-9_-]+)=([A-Za-z0-9_.-]+)$", re.MULTILINE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def static_label(group: str, event: str) -> str:
    return f"{group}.{event}"


def static_path(group: str, event: str) -> str:
    return f"{group}/{event}"


def shell_quote_single(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def lower_event_names_pattern() -> str:
    names = [event for _group, event, _kind in LOWER_TRACE_EVENTS]
    return "|".join(re.escape(name) for name in names)


def static_enable_script() -> str:
    lines = ["echo lower_static_events_begin=1"]
    for group, event, kind in LOWER_TRACE_EVENTS:
        label = static_label(group, event)
        path = static_path(group, event)
        lines.extend([
            f"if $BB test -e \"$TRACE/events/{path}/enable\"; then",
            f"  echo 0 > \"$TRACE/events/{path}/enable\" 2>/dev/null || true",
            f"  if echo 1 > \"$TRACE/events/{path}/enable\" 2>/dev/null; then",
            f"    echo static_event.{label}.kind={kind}",
            f"    echo static_event.{label}.enable=ok",
            "  else",
            f"    echo static_event.{label}.enable=failed",
            "  fi",
            "else",
            f"  echo static_event.{label}.enable=missing",
            "fi",
        ])
    lines.append("echo lower_static_events_end=1")
    return "\n".join(lines)


def static_cleanup_script() -> str:
    lines = []
    for group, event, _kind in LOWER_TRACE_EVENTS:
        label = static_label(group, event)
        path = static_path(group, event)
        lines.extend([
            f"  if $BB test -e \"$TRACE/events/{path}/enable\"; then",
            f"    if echo 0 > \"$TRACE/events/{path}/enable\" 2>/dev/null; then",
            f"      echo static_event.{label}.disable=ok",
            "    else",
            f"      echo static_event.{label}.disable=failed",
            "    fi",
            "  fi",
        ])
    return "\n".join(lines)


def static_count_script() -> str:
    lines = []
    for group, event, kind in LOWER_TRACE_EVENTS:
        label = static_label(group, event)
        lines.extend([
            f"count=$($BB grep -c {shell_quote_single(event)} \"$TRACE/trace\" 2>/dev/null || true)",
            f"echo static_event.{label}.kind={kind}",
            f"echo static_event.{label}.count=$count",
        ])
    return "\n".join(lines)


def static_line_dump_script() -> str:
    pattern = lower_event_names_pattern()
    return "\n".join([
        "echo lower_trace_lines_begin",
        f"$BB grep -E {shell_quote_single(pattern)} \"$TRACE/trace\" 2>/dev/null | $BB head -n {LOWER_TRACE_LINE_LIMIT} || true",
        "echo lower_trace_lines_end",
    ])


def collect_lower_trace_lines(text: str) -> list[str]:
    lines: list[str] = []
    in_block = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.strip() == "lower_trace_lines_begin":
            in_block = True
            continue
        if line.strip() == "lower_trace_lines_end":
            in_block = False
            continue
        if in_block:
            lines.append(line)
    return lines


def parse_lower_static_events(text: str) -> dict[str, Any]:
    counts = {label: int(value) for label, value in STATIC_COUNT_RE.findall(text)}
    status: dict[str, dict[str, str]] = {}
    for label, key, value in STATIC_STATUS_RE.findall(text):
        status.setdefault(label, {})
        status[label][key] = value

    event_meta = {
        static_label(group, event): {"group": group, "event": event, "kind": kind}
        for group, event, kind in LOWER_TRACE_EVENTS
    }
    group_counts: dict[str, int] = {}
    critical_count = 0
    noise_count = 0
    for label, count in counts.items():
        meta = event_meta.get(label, {})
        group = str(meta.get("group", label.split(".", 1)[0]))
        kind = str(meta.get("kind", ""))
        group_counts[group] = group_counts.get(group, 0) + count
        if kind == "critical":
            critical_count += count
        else:
            noise_count += count

    enable_failures = {
        label: values.get("enable")
        for label, values in status.items()
        if values.get("enable") not in {None, "ok"}
    }
    disable_failures = {
        label: values.get("disable")
        for label, values in status.items()
        if values.get("disable") not in {None, "ok"}
    }
    lower_trace_lines = collect_lower_trace_lines(text)
    return {
        "event_meta": event_meta,
        "status": status,
        "counts": counts,
        "group_counts": group_counts,
        "total_count": sum(counts.values()),
        "critical_count": critical_count,
        "noise_count": noise_count,
        "enable_failures": enable_failures,
        "disable_failures": disable_failures,
        "enabled_count": sum(1 for values in status.values() if values.get("enable") == "ok"),
        "line_count": len(lower_trace_lines),
        "lines": lower_trace_lines[:LOWER_TRACE_LINE_LIMIT],
    }


def patch_tracefs_collector(v1106: Any) -> None:
    original_collector = v1106.tracefs_collector_script
    original_parser = v1106.parse_tracefs_output

    def collector(args: Any) -> str:
        script = original_collector(args)
        script = script.replace("cleanup() {\n", "cleanup() {\n" + static_cleanup_script() + "\n", 1)
        script = script.replace("echo observe_begin=1", static_enable_script() + "\necho observe_begin=1", 1)
        script = script.replace("echo trace_lines_begin\n", static_line_dump_script() + "\necho trace_lines_begin\n", 1)
        script = script.replace("echo result=tracefs-uprobe-pass", static_count_script() + "\necho result=tracefs-uprobe-pass", 1)
        return script

    def parser(text: str) -> dict[str, Any]:
        parsed = original_parser(text)
        parsed["lower_static_events"] = parse_lower_static_events(text)
        return parsed

    v1106.tracefs_collector_script = collector
    v1106.parse_tracefs_output = parser
    base.v1238.v1237.v1106_mod.tracefs_collector_script = collector
    base.v1238.v1237.v1106_mod.parse_tracefs_output = parser


def lower_static(manifest: dict[str, Any]) -> dict[str, Any]:
    return (((manifest.get("analysis") or {}).get("tracefs_uprobe") or {}).get("lower_static_events") or {})


def pm_service_esoc0_reach(manifest: dict[str, Any]) -> tuple[bool, str]:
    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    pm_contract = tracefs.get("pm_contract") or {}
    top_observer = manifest.get("pm_service_trigger_observer") or {}
    thread_samples = tracefs.get("thread_samples") or []

    if str(top_observer.get("pm_service_actor_esoc0_attempt", "")).lower() in {"1", "true", "yes"}:
        return True, "top-observer-pm-service-actor-esoc0-attempt"
    if str(pm_contract.get("pm_service_actor_esoc0_attempt", "")).lower() in {"1", "true", "yes"}:
        return True, "pm-contract-pm-service-actor-esoc0-attempt"
    if str(pm_contract.get("late_per_proxy_started", "")).lower() in {"1", "true", "yes"}:
        for value in pm_contract.values():
            text = str(value)
            if "/dev/subsys_esoc0" in text:
                return True, "pm-contract-subsys-esoc0-path"
            if "mdm_subsys_powerup" in text:
                return True, "pm-contract-mdm-subsys-powerup"
    for sample in thread_samples:
        if isinstance(sample, dict) and sample.get("wchan") == "mdm_subsys_powerup":
            return True, "tracefs-thread-sample-mdm-subsys-powerup"
    return False, "not-reached"


def decide_v1316(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1316-tracefs-lower-event-collector-plan-ready",
            True,
            "plan-only; no device command or tracefs control write executed",
            "run V1316 bounded tracefs lower-event collector around late per_proxy PM-service path",
        )

    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    lower = lower_static(manifest)
    pm_esoc0_attempt, pm_esoc0_basis = pm_service_esoc0_reach(manifest)
    manifest["pm_service_esoc0_reach_basis"] = pm_esoc0_basis
    result = tracefs.get("result", "")
    enable_failures = lower.get("enable_failures") or {}
    disable_failures = lower.get("disable_failures") or {}
    critical_count = int(lower.get("critical_count") or 0)
    total_count = int(lower.get("total_count") or 0)

    if result != "tracefs-uprobe-pass":
        return (
            "v1316-tracefs-collector-failed",
            False,
            f"tracefs collector result={result}",
            "inspect V1316 collector transcript and cleanup before retry",
        )
    if enable_failures or disable_failures:
        return (
            "v1316-tracefs-lower-event-cleanup-review",
            False,
            f"enable_failures={enable_failures} disable_failures={disable_failures}",
            "cleanup tracefs event state before another live gate",
        )
    if not pm_esoc0_attempt:
        return (
            "v1316-pm-service-esoc0-not-reached",
            False,
            "late per_proxy path did not reach PM-service /dev/subsys_esoc0",
            "repair PM-service path before interpreting lower trace events",
        )
    if critical_count > 0:
        return (
            "v1316-critical-first-power-on-events-captured",
            True,
            f"critical lower tracefs events appeared during mdm_subsys_powerup window; critical_count={critical_count} total_count={total_count}",
            "classify event lines to locate whether regulator/gpio/power/PIL progressed before deciding the next lower gate",
        )
    return (
        "v1316-no-critical-first-power-on-events-before-block",
        True,
        f"PM-service reached mdm_subsys_powerup but no critical regulator/gpio/power/PIL trace events were captured; total_count={total_count}",
        "classify whether provider blocks before first-power-on event emission or needs narrower driver-specific tracepoints before any lower mutation",
    )


def render_static_rows(lower: dict[str, Any]) -> list[list[Any]]:
    counts = lower.get("counts") or {}
    status = lower.get("status") or {}
    meta = lower.get("event_meta") or {}
    rows: list[list[Any]] = []
    for label in sorted(meta):
        rows.append([
            label,
            meta[label].get("kind", ""),
            status.get(label, {}).get("enable", ""),
            status.get(label, {}).get("disable", ""),
            counts.get(label, 0),
        ])
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    lower = lower_static(manifest)
    pm = tracefs.get("pm_contract") or {}
    top_pm = manifest.get("pm_service_trigger_observer") or {}
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
        "## PM-Service Path",
        "",
        markdown_table(["field", "value"], [
            ["tracefs result", tracefs.get("result", "")],
            ["PM-service esoc0 attempt", top_pm.get("pm_service_actor_esoc0_attempt", pm.get("pm_service_actor_esoc0_attempt", ""))],
            ["PM-service esoc0 reach basis", manifest.get("pm_service_esoc0_reach_basis", "")],
            ["late per_proxy started", pm.get("late_per_proxy_started", "")],
            ["all postflight safe", pm.get("all_postflight_safe", "")],
            ["trace lines", tracefs.get("trace_line_count", "")],
        ]),
        "",
        "## Lower Static Events",
        "",
        markdown_table(["field", "value"], [
            ["enabled count", lower.get("enabled_count", 0)],
            ["total count", lower.get("total_count", 0)],
            ["critical count", lower.get("critical_count", 0)],
            ["noise count", lower.get("noise_count", 0)],
            ["group counts", json.dumps(lower.get("group_counts") or {}, sort_keys=True)],
            ["lower trace line count", lower.get("line_count", 0)],
            ["enable failures", json.dumps(lower.get("enable_failures") or {}, sort_keys=True)],
            ["disable failures", json.dumps(lower.get("disable_failures") or {}, sort_keys=True)],
        ]),
        "",
        markdown_table(["event", "kind", "enable", "disable", "count"], render_static_rows(lower)),
        "",
        "## Lower Trace Lines Sample",
        "",
        "```text",
        "\n".join((lower.get("lines") or [])[:80]),
        "```",
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    lower = lower_static(manifest)
    tracefs = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {})
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"tracefs_result:         {tracefs.get('result', '')}")
    print(f"pm_esoc0_reach_basis:   {manifest.get('pm_service_esoc0_reach_basis', '')}")
    print(f"lower_enabled_count:    {lower.get('enabled_count', 0)}")
    print(f"lower_total_count:      {lower.get('total_count', 0)}")
    print(f"lower_critical_count:   {lower.get('critical_count', 0)}")
    print(f"wifi_bringup_executed:  {manifest.get('wifi_bringup_executed')}")
    print(f"evidence: {manifest.get('_run_dir')}")


def reclassify_existing() -> int:
    manifest_path = repo_path(DEFAULT_OUT_DIR / "manifest.json")
    if not manifest_path.exists():
        print(f"error: missing existing {CYCLE_NAME} manifest: {manifest_path}", file=sys.stderr)
        return 2
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        print(f"error: manifest is not an object: {manifest_path}", file=sys.stderr)
        return 2
    manifest["command"] = "run"
    manifest = base._reanalyze_manifest(manifest)
    manifest["cycle"] = CYCLE_LABEL
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["lower_trace_events"] = [static_label(group, event) for group, event, _kind in LOWER_TRACE_EVENTS]
    manifest["reclassified_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1316(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (repo_path(DEFAULT_OUT_DIR) / "summary.md").write_text(render_summary(manifest), encoding="utf-8")
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(DEFAULT_OUT_DIR)) + "\n")
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "reclassify":
        return reclassify_existing()

    out_dir = DEFAULT_OUT_DIR
    latest_pointer = LATEST_POINTER
    if len(sys.argv) >= 2 and sys.argv[1] == "plan":
        out_dir = PLAN_OUT_DIR
        latest_pointer = PLAN_LATEST_POINTER

    base.DEFAULT_OUT_DIR = out_dir
    base.LATEST_POINTER = latest_pointer
    base.HELPER_MARKER = HELPER_MARKER
    base.HELPER_SHA256 = HELPER_SHA256
    base.CYCLE_LABEL = CYCLE_LABEL
    base.CYCLE_NAME = CYCLE_NAME
    base.SUMMARY_HEADING = SUMMARY_HEADING
    base.EVIDENCE_FILE_PREFIX = EVIDENCE_FILE_PREFIX

    v1165, v1106 = base.patch_defaults()
    patch_tracefs_collector(v1106)
    args = v1106.parse_args()
    if args.command == "run":
        args.allow_tracefs_mount = True
        args.allow_tracefs_write = True
        args.allow_vendor_mount = True
        args.allow_selinuxfs_mount = True
        args.allow_pm_service_trigger_observer = True
        args.allow_cnss_daemon_start = True
        args.assume_yes = True
    if args.helper_timeout_sec == 4:
        args.helper_timeout_sec = 30
    if args.toybox_timeout_sec == 18:
        args.toybox_timeout_sec = 90
    if args.tracefs_duration_sec == 18:
        args.tracefs_duration_sec = 95
    if args.thread_sample_count == 80:
        args.thread_sample_count = 260
    v1165.v1143.v1139.v1113.set_global_defaults(args)

    store = EvidenceStore(repo_path(out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["command"] = args.command
    manifest["cycle"] = CYCLE_LABEL
    manifest["generated_at"] = now_iso()
    manifest["_run_dir"] = str(store.run_dir)
    manifest = base._reanalyze_manifest(manifest)
    manifest["cycle"] = CYCLE_LABEL
    manifest["helper_version"] = HELPER_MARKER
    manifest["helper_sha256"] = HELPER_SHA256
    manifest["lower_trace_events"] = [static_label(group, event) for group, event, _kind in LOWER_TRACE_EVENTS]
    decision, passed, reason, next_step = decide_v1316(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(latest_pointer), str(store.run_dir) + "\n")
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
