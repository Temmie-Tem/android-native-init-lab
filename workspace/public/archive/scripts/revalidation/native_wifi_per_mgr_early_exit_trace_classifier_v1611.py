#!/usr/bin/env python3
"""V1611 host-only classifier for the V1610 per_mgr early-exit trace handoff."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1611-per-mgr-early-exit-trace-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1611_PER_MGR_EARLY_EXIT_TRACE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1611-per-mgr-early-exit-trace-classifier.txt")

V1610_DIR = Path("tmp/wifi/v1610-per-mgr-early-exit-trace-handoff")
V1610_MANIFEST = V1610_DIR / "manifest.json"
V1610_HELPER = V1610_DIR / "test-v1393-helper-result.stdout.txt"
V1610_DMESG = V1610_DIR / "test-v1393-dmesg.stdout.txt"
V1610_REPORT = Path("docs/reports/NATIVE_INIT_V1610_PER_MGR_EARLY_EXIT_TRACE_HANDOFF_2026-06-02.md")

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")
RECORD_RE = re.compile(
    r"^pm_service_trigger_observer\.syscall\.per_mgr\.record_(?P<idx>[0-9]+)\.(?P<field>[^=]+)=(?P<value>.*)$"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 32 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return (
        resolved.read_bytes()[:limit]
        .replace(b"\0", b"\\0")
        .decode("utf-8", errors="replace")
    )


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = KV_RE.match(raw_line.strip())
        if match:
            values[match.group("key")] = match.group("value").strip()
    return values


def int_value(value: Any, default: int = -1) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def parse_syscall_records(text: str) -> list[dict[str, str]]:
    records: dict[int, dict[str, str]] = {}
    for raw_line in text.splitlines():
        match = RECORD_RE.match(raw_line.strip())
        if not match:
            continue
        idx = int(match.group("idx"), 10)
        records.setdefault(idx, {})[match.group("field")] = match.group("value").strip()
    return [records[idx] for idx in sorted(records)]


def analyze() -> dict[str, Any]:
    manifest = read_json(V1610_MANIFEST)
    progress = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    helper_text = read_text(V1610_HELPER)
    helper = parse_kv(helper_text)
    records = parse_syscall_records(helper_text)
    dmesg = read_text(V1610_DMESG)

    first_record = records[0] if records else {}
    current = {
        "v1610_decision": manifest.get("decision", ""),
        "v1610_pass": bool_value(manifest.get("pass")),
        "handoff_pass": bool_value(manifest.get("handoff_pass")),
        "rollback_ok": bool_value((manifest.get("rollback") or {}).get("ok")),
        "progress_decision": progress.get("final_decision", ""),
        "modem_trigger": bool_value(progress.get("modem_trigger")),
        "provider_trigger": bool_value(progress.get("provider_trigger")),
        "rc1_progress": bool_value(progress.get("rc1_progress")),
        "mhi_progress": bool_value(progress.get("mhi_progress")),
        "wlfw_progress": bool_value(progress.get("wlfw_progress")),
        "wlan0_present": bool_value(progress.get("wlan0_present")),
        "mode": helper.get("android_wifi_service_window.mode", ""),
        "early_exit_trace": int_value(helper.get("android_wifi_service_window.per_mgr_early_exit_trace")),
        "startup_sample_count": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.sample_count")
        ),
        "startup_alive_seen": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.alive_seen")
        ),
        "startup_last_alive_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.last_alive_ms")
        ),
        "startup_first_gone_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_gone_ms")
        ),
        "startup_first_child_done_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_child_done_ms")
        ),
        "startup_exit_code": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")
        ),
        "startup_signal": int_value(helper.get("android_wifi_service_window.per_mgr_startup_trace.signal")),
        "startup_max_subsys_modem_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")
        ),
        "startup_max_subsys_esoc0_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")
        ),
        "child_exit_code": int_value(helper.get("android_wifi_service_window.child.per_mgr.exit_code")),
        "child_signal": int_value(helper.get("android_wifi_service_window.child.per_mgr.signal")),
        "child_traced": int_value(helper.get("android_wifi_service_window.child.per_mgr.traced")),
        "trace_exec_captured": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.trace_exec_captured")
        ),
        "trace_exit_captured": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.trace_exit_captured")
        ),
        "syscall_trace_started": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.syscall_trace_started")
        ),
        "syscall_record_count": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.syscall_record_count")
        ),
        "syscall_error_count": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.syscall_error_count")
        ),
        "syscall_stop_count": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.syscall_stop_count")
        ),
        "syscall_trace_truncated": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.syscall_trace_truncated")
        ),
        "syscall_trace_stop_limited": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.syscall_trace_stop_limited")
        ),
        "trace_disable_reason": helper.get(
            "pm_service_trigger_observer.syscall.per_mgr.trace_disable_reason", ""
        ),
        "first_record_name": first_record.get("name", ""),
        "first_record_path": first_record.get("path.text", ""),
        "first_record_ret": int_value(first_record.get("ret")),
        "helper_timed_out": int_value(helper.get("android_wifi_service_window.timed_out")),
        "helper_result": helper.get("android_wifi_service_window.result", ""),
        "helper_reason": helper.get("android_wifi_service_window.reason", ""),
        "pm_proxy_helper_subsys_modem_fd_count": int_value(
            helper.get("android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count")
        ),
        "per_mgr_subsys_modem_fd_count": int_value(
            helper.get("android_wifi_service_window.per_mgr_subsys_modem_fd_count")
        ),
        "pm_full_contract_seen": int_value(helper.get("android_wifi_service_window.pm_full_contract_seen")),
        "subsys_esoc0_open_attempted": int_value(
            helper.get("android_wifi_service_window.subsys_esoc0_open_attempted")
        ),
        "dmesg_has_rc1": "PCIe RC1" in dmesg or "LTSSM" in dmesg,
        "dmesg_has_wlan0": "wlan0" in dmesg,
    }
    checks = {
        "handoff_and_rollback_ok": current["handoff_pass"] and current["rollback_ok"],
        "early_exit_trace_enabled": current["early_exit_trace"] == 1 and current["child_traced"] == 1,
        "ptrace_stopped_process": current["startup_last_alive_ms"] >= 1000
        and current["startup_first_gone_ms"] == -1
        and current["startup_first_child_done_ms"] == -1,
        "only_one_selected_syscall_record": current["syscall_record_count"] == 1
        and current["first_record_name"] == "faccessat"
        and current["first_record_path"] == "/dev/urandom",
        "trace_hit_stop_limit": current["syscall_stop_count"] >= 128
        and current["syscall_trace_stop_limited"] == 1
        and current["trace_disable_reason"] == "stop-limit",
        "no_pm_contract_fd_seen": current["startup_max_subsys_modem_fd"] == 0
        and current["startup_max_subsys_esoc0_fd"] == 0
        and current["per_mgr_subsys_modem_fd_count"] == 0
        and current["pm_full_contract_seen"] == 0
        and current["subsys_esoc0_open_attempted"] == 0,
        "downstream_wifi_absent": not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"],
    }
    pass_result = all(checks.values())
    decision = (
        "v1611-ptrace-lite-intrusive-stop-limit-no-exit-cause"
        if pass_result
        else "v1611-per-mgr-early-exit-trace-incomplete-review"
    )
    reason = (
        "V1610 collected rollback-safe evidence but ptrace-lite changed the target behavior: pm-service stayed stopped for the full sampler window, recorded only faccessat('/dev/urandom'), hit the syscall stop limit, and never reached a PM contract fd"
        if pass_result
        else "V1610 evidence does not fully prove the ptrace-lite perturbation boundary"
    )
    next_gate = {
        "recommended_cycle": "V1612",
        "type": "source/build-only non-stopping pm-service startup classifier",
        "focus": (
            "replace ptrace-lite syscall tracing with non-stopping evidence: stderr/stdout tails, "
            "service-manager/property/socket namespace snapshots, vendor init/env comparison, "
            "and host-only pm-service dependency/string analysis"
        ),
        "avoid": [
            "ptrace syscall tracing of pm-service",
            "ptrace of mdm_helper",
            "direct scoped /dev/subsys_esoc0 open",
            "Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping",
            "PMIC/GPIO/GDSC direct writes, blind eSoC notify/BOOT_DONE",
        ],
    }
    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "v1610": current,
        "records": records[:8],
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    current = analysis["v1610"]
    next_gate = analysis["next_gate"]
    return "\n".join([
        "# Native Init V1611 per_mgr Early-exit Trace Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1611`",
        "- Type: host-only classifier over V1610 live evidence",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Inputs",
        "",
        markdown_table(
            ["input", "path"],
            [
                ["v1610_manifest", rel(V1610_MANIFEST)],
                ["v1610_helper_result", rel(V1610_HELPER)],
                ["v1610_dmesg", rel(V1610_DMESG)],
                ["v1610_report", rel(V1610_REPORT)],
            ],
        ),
        "",
        "## Derived Checks",
        "",
        markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
        "",
        "## Trace Summary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["handoff_pass", current["handoff_pass"]],
                ["rollback_ok", current["rollback_ok"]],
                ["progress_decision", current["progress_decision"]],
                ["startup_sample_count", current["startup_sample_count"]],
                ["startup_last_alive_ms", current["startup_last_alive_ms"]],
                ["startup_first_gone_ms", current["startup_first_gone_ms"]],
                ["startup_first_child_done_ms", current["startup_first_child_done_ms"]],
                ["startup_exit_code", current["startup_exit_code"]],
                ["child_exit_code", current["child_exit_code"]],
                ["child_traced", current["child_traced"]],
                ["trace_exec_captured", current["trace_exec_captured"]],
                ["trace_exit_captured", current["trace_exit_captured"]],
                ["syscall_record_count", current["syscall_record_count"]],
                ["syscall_stop_count", current["syscall_stop_count"]],
                ["syscall_trace_stop_limited", current["syscall_trace_stop_limited"]],
                ["trace_disable_reason", current["trace_disable_reason"]],
                ["first_record", f"{current['first_record_name']} {current['first_record_path']} ret={current['first_record_ret']}"],
                ["max_subsys_modem_fd", current["startup_max_subsys_modem_fd"]],
                ["max_subsys_esoc0_fd", current["startup_max_subsys_esoc0_fd"]],
                ["pm_full_contract_seen", current["pm_full_contract_seen"]],
                ["subsys_esoc0_open_attempted", current["subsys_esoc0_open_attempted"]],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "V1610 did not reveal the clean V1607 `pm-service` exit cause.  It changed the process behavior.  With ptrace-lite enabled, the startup sampler sees `pm-service` in `ptrace_stop` for the entire 1s window, `first_gone_ms=-1`, and `first_child_done_ms=-1`.  Only one selected syscall record is produced: `faccessat('/dev/urandom')`, after which the tracer hits the syscall stop limit.",
        "",
        "The postflight child exit still reports `exit_code=0`, but this is no longer equivalent to the natural V1607 early exit.  Treat V1608/V1610 ptrace-lite as intrusive for this target and do not base the next branch on lower eSoC/RC1 absence from this run.",
        "",
        "## Next Gate",
        "",
        f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
        f"- Type: {next_gate['type']}",
        f"- Focus: {next_gate['focus']}",
        "",
        "### Avoid",
        "",
        *[f"- {item}" for item in next_gate["avoid"]],
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, global PCI rescan, or platform bind/unbind.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze()
    manifest = {
        "cycle": "V1611",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "v1610_manifest": rel(V1610_MANIFEST),
            "v1610_helper_result": rel(V1610_HELPER),
            "v1610_dmesg": rel(V1610_DMESG),
            "v1610_report": rel(V1610_REPORT),
        },
        "analysis": analysis,
        "out_dir": rel(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    write_private_text(repo_path(LATEST_POINTER), rel(store.run_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
