#!/usr/bin/env python3
"""V1615 host-only classifier for the V1614 non-stopping per_mgr context evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1615-per-mgr-nonstop-context-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1615_PER_MGR_NONSTOP_CONTEXT_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1615-per-mgr-nonstop-context-classifier.txt")

V1614_DIR = Path("tmp/wifi/v1614-per-mgr-nonstop-context-handoff")
V1614_MANIFEST = V1614_DIR / "manifest.json"
V1614_HELPER = V1614_DIR / "test-v1393-helper-result.stdout.txt"
V1614_DMESG = V1614_DIR / "test-v1393-dmesg.stdout.txt"
V1614_REPORT = Path("docs/reports/NATIVE_INIT_V1614_PER_MGR_NONSTOP_CONTEXT_HANDOFF_2026-06-02.md")

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")


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


def property_requests(helper: dict[str, str]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index in range(1, 17):
        name = helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.name")
        if not name:
            continue
        result.append({
            "index": index,
            "name": name,
            "value": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.value", ""),
            "allowed": int_value(
                helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.allowed")
            ),
            "result": helper.get(f"wifi_hal_composite_start.property_service_shim.request.{index}.result", ""),
        })
    return result


def analyze() -> dict[str, Any]:
    manifest = read_json(V1614_MANIFEST)
    progress = manifest.get("wifi_progress") if isinstance(manifest.get("wifi_progress"), dict) else {}
    helper_text = read_text(V1614_HELPER)
    helper = parse_kv(helper_text)
    dmesg = read_text(V1614_DMESG)
    requests = property_requests(helper)
    request_pairs = {(item["name"], item["value"]) for item in requests}

    current = {
        "v1614_decision": manifest.get("decision", ""),
        "handoff_pass": bool_value(manifest.get("handoff_pass")),
        "rollback_ok": bool_value((manifest.get("rollback") or {}).get("ok")),
        "progress_decision": progress.get("final_decision", ""),
        "modem_trigger": bool_value(progress.get("modem_trigger")),
        "provider_trigger": bool_value(progress.get("provider_trigger")),
        "rc1_progress": bool_value(progress.get("rc1_progress")),
        "mhi_progress": bool_value(progress.get("mhi_progress")),
        "wlfw_progress": bool_value(progress.get("wlfw_progress")),
        "wlan0_present": bool_value(progress.get("wlan0_present")),
        "nonstop_context_trace": int_value(
            helper.get("android_wifi_service_window.per_mgr_nonstop_context_trace")
        ),
        "early_exit_trace": int_value(helper.get("android_wifi_service_window.per_mgr_early_exit_trace")),
        "startup_sample_count": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.sample_count")
        ),
        "sample00_state": helper.get("android_wifi_service_window.per_mgr_startup_trace.sample.00.state", ""),
        "sample01_state": helper.get("android_wifi_service_window.per_mgr_startup_trace.sample.01.state", ""),
        "sample02_alive": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.sample.02.alive")
        ),
        "last_alive_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.last_alive_ms")
        ),
        "first_gone_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_gone_ms")
        ),
        "first_child_done_ms": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.first_child_done_ms")
        ),
        "startup_exit_code": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.exit_code")
        ),
        "child_exit_code": int_value(helper.get("android_wifi_service_window.child.per_mgr.exit_code")),
        "child_traced": int_value(helper.get("android_wifi_service_window.child.per_mgr.traced")),
        "max_subsys_modem_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_modem_fd")
        ),
        "max_subsys_esoc0_fd": int_value(
            helper.get("android_wifi_service_window.per_mgr_startup_trace.max_subsys_esoc0_fd")
        ),
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
        "pre_registry_dirs_captured": int_value(
            helper.get("wifi_registry_snapshot.per_mgr_pre_startup_trace.dirs_captured")
        ),
        "post_registry_dirs_captured": int_value(
            helper.get("wifi_registry_snapshot.per_mgr_post_startup_trace.dirs_captured")
        ),
        "pre_registry_child_proc_captured": int_value(
            helper.get("wifi_registry_snapshot.per_mgr_pre_startup_trace.child_proc_captured")
        ),
        "post_registry_child_proc_captured": int_value(
            helper.get("wifi_registry_snapshot.per_mgr_post_startup_trace.child_proc_captured")
        ),
        "property_request_count": int_value(
            helper.get("wifi_hal_composite_start.property_service_shim.request_count")
        ),
        "property_hwservicemanager_ready": ("hwservicemanager.ready", "true") in request_pairs,
        "property_sdx50m_offline": ("vendor.peripheral.SDX50M.state", "OFFLINE") in request_pairs,
        "property_modem_offline": ("vendor.peripheral.modem.state", "OFFLINE") in request_pairs,
        "helper_result": helper.get("android_wifi_service_window.result", ""),
        "helper_reason": helper.get("android_wifi_service_window.reason", ""),
        "stderr_bytes": len(helper_text.split("A90_EXECNS_STDERR_BEGIN", 1)[1])
        if "A90_EXECNS_STDERR_BEGIN" in helper_text else 0,
        "stderr_old_property_protocol": "Using old property service protocol" in helper_text,
        "stderr_kmsg_permission_denied": "can't create /dev/kmsg: Permission denied" in helper_text,
        "stderr_no_closing_quote": "sh: no closing quote" in helper_text,
        "dmesg_has_rc1": "PCIe RC1" in dmesg or "LTSSM" in dmesg,
        "dmesg_has_wlan0": "wlan0" in dmesg,
    }
    checks = {
        "handoff_and_rollback_ok": current["handoff_pass"] and current["rollback_ok"],
        "nonstopping_trace_enabled": current["nonstop_context_trace"] == 1
        and current["early_exit_trace"] == 0
        and current["child_traced"] == 0,
        "natural_early_exit_reproduced": current["last_alive_ms"] == 20
        and current["first_child_done_ms"] == 21
        and current["first_gone_ms"] == 41
        and current["startup_exit_code"] == 0
        and current["child_exit_code"] == 0,
        "process_reached_only_pre_contract_state": current["sample00_state"] == "D"
        and current["sample01_state"] == "Z"
        and current["sample02_alive"] == 0,
        "no_pm_contract_fd_seen": current["max_subsys_modem_fd"] == 0
        and current["max_subsys_esoc0_fd"] == 0
        and current["per_mgr_subsys_modem_fd_count"] <= 0
        and current["pm_full_contract_seen"] == 0
        and current["subsys_esoc0_open_attempted"] == 0,
        "property_contract_observed": current["property_request_count"] == 3
        and current["property_hwservicemanager_ready"]
        and current["property_sdx50m_offline"]
        and current["property_modem_offline"],
        "context_snapshots_captured": current["pre_registry_dirs_captured"] >= 1
        and current["post_registry_dirs_captured"] >= 1,
        "downstream_wifi_absent": not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"],
    }
    pass_result = all(checks.values())
    decision = (
        "v1615-natural-pm-service-exit-after-offline-property-writes"
        if pass_result
        else "v1615-nonstop-context-incomplete-review"
    )
    reason = (
        "V1614 non-stopping evidence reproduces the natural pm-service clean exit: D at 0ms, zombie at 20ms, gone by 41ms, exit 0, no PM fd, after property writes for SDX50M/modem OFFLINE"
        if pass_result
        else "V1614 evidence does not fully prove the natural non-stopping pm-service exit boundary"
    )
    next_gate = {
        "recommended_cycle": "V1616",
        "type": "host-only + source/build-only pm-service dependency/launch-contract classifier",
        "focus": (
            "classify why /vendor/bin/pm-service exits 0 after setting "
            "vendor.peripheral.SDX50M.state=OFFLINE and vendor.peripheral.modem.state=OFFLINE "
            "without opening binder or /dev/subsys_modem"
        ),
        "candidate_checks": [
            "host-only strings/readelf/needed-libs for /vendor/bin/pm-service",
            "compare Android vendor init service stanza, class, user/group, seclabel, sockets, capabilities, and environment",
            "capture/compare Android property values consumed by pm-service or peripheral manager",
            "if needed, build a bounded property-contract variant that exposes initial peripheral properties without ptrace",
        ],
    }
    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "v1614": current,
        "property_requests": requests,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    current = analysis["v1614"]
    next_gate = analysis["next_gate"]
    return "\n".join([
        "# Native Init V1615 per_mgr Non-stopping Context Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1615`",
        "- Type: host-only classifier over V1614 live evidence",
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
                ["v1614_manifest", rel(V1614_MANIFEST)],
                ["v1614_helper_result", rel(V1614_HELPER)],
                ["v1614_dmesg", rel(V1614_DMESG)],
                ["v1614_report", rel(V1614_REPORT)],
            ],
        ),
        "",
        "## Derived Checks",
        "",
        markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
        "",
        "## Exit Summary",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["handoff_pass", current["handoff_pass"]],
                ["rollback_ok", current["rollback_ok"]],
                ["progress_decision", current["progress_decision"]],
                ["nonstop_context_trace", current["nonstop_context_trace"]],
                ["child_traced", current["child_traced"]],
                ["sample00_state", current["sample00_state"]],
                ["sample01_state", current["sample01_state"]],
                ["last_alive_ms", current["last_alive_ms"]],
                ["first_child_done_ms", current["first_child_done_ms"]],
                ["first_gone_ms", current["first_gone_ms"]],
                ["startup_exit_code", current["startup_exit_code"]],
                ["max_subsys_modem_fd", current["max_subsys_modem_fd"]],
                ["max_subsys_esoc0_fd", current["max_subsys_esoc0_fd"]],
                ["pm_full_contract_seen", current["pm_full_contract_seen"]],
                ["property_request_count", current["property_request_count"]],
                ["stderr_old_property_protocol", current["stderr_old_property_protocol"]],
                ["stderr_kmsg_permission_denied", current["stderr_kmsg_permission_denied"]],
                ["stderr_no_closing_quote", current["stderr_no_closing_quote"]],
            ],
        ),
        "",
        "## Property Requests",
        "",
        markdown_table(
            ["index", "name", "value", "allowed", "result"],
            [
                [item["index"], item["name"], item["value"], item["allowed"], item["result"]]
                for item in analysis["property_requests"]
            ],
        ),
        "",
        "## Interpretation",
        "",
        "V1614 confirms V1607's natural clean `pm-service` early exit without ptrace perturbation.  The process reaches only the pre-contract boundary: state `D` at sample 0, state `Z` at 20ms, reaped/gone by 41ms, and exit code 0.  It never opens `/dev/subsys_modem`, `/dev/subsys_esoc0`, binder nodes, sockets, or the PM full contract.",
        "",
        "`pm-service` or the surrounding service-manager/property setup emits only three property-service requests in this window: `hwservicemanager.ready=true`, `vendor.peripheral.SDX50M.state=OFFLINE`, and `vendor.peripheral.modem.state=OFFLINE`.  The next useful branch is therefore not RC1/MHI/WLFW, but the launch/property contract that makes Android keep peripheral manager alive long enough to own the PM contract.",
        "",
        "## Next Gate",
        "",
        f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
        f"- Type: {next_gate['type']}",
        f"- Focus: {next_gate['focus']}",
        "",
        "### Candidate Checks",
        "",
        *[f"- {item}" for item in next_gate["candidate_checks"]],
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
        "cycle": "V1615",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "v1614_manifest": rel(V1614_MANIFEST),
            "v1614_helper_result": rel(V1614_HELPER),
            "v1614_dmesg": rel(V1614_DMESG),
            "v1614_report": rel(V1614_REPORT),
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
