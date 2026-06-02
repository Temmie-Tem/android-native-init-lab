#!/usr/bin/env python3
"""V1603 host-only classifier for the V1602 pm-service early-exit blocker.

V1602 proved that the pm_proxy_helper modem-fd gate is no longer the blocker:
the helper sees /dev/subsys_modem before per_mgr starts.  The remaining failure
is that /vendor/bin/pm-service exits cleanly before it owns /dev/subsys_modem,
pm-proxy exits 1, and the service window never reaches PM-service-owned
/dev/subsys_esoc0 or mdm_subsys_powerup.

This script only reads existing host evidence and writes a private classifier
manifest/report.  It does not contact the device or mutate any boot artifact.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1603-pm-service-exit-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1603_PM_SERVICE_EXIT_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1603-pm-service-exit-classifier.txt")

V1602_DIR = Path("tmp/wifi/v1602-pm-first-late-per-proxy-pph-gate-lower-marker-handoff")
V1602_MANIFEST = V1602_DIR / "manifest.json"
V1602_SUMMARY = V1602_DIR / "summary.md"
V1602_HELPER_RESULT = V1602_DIR / "test-v1393-helper-result.stdout.txt"
V1602_DMESG = V1602_DIR / "test-v1393-dmesg.stdout.txt"
V1599_REPORT = Path(
    "docs/reports/NATIVE_INIT_V1599_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md"
)
V1602_REPORT = Path(
    "docs/reports/NATIVE_INIT_V1602_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_HANDOFF_2026-06-02.md"
)
PLAN_PATH = Path("docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md")
CLAUDE_PATH = Path("CLAUDE.md")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 16 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = KV_RE.match(line.strip())
        if match:
            values[match.group("key")] = match.group("value").strip()
    return values


def int_value(value: Any, default: int = -1) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on", "pass"}


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def extract_block(text: str, begin: str, end: str) -> str:
    start = text.find(begin)
    if start < 0:
        return ""
    start += len(begin)
    finish = text.find(end, start)
    if finish < 0:
        return text[start:].strip()
    return text[start:finish].strip()


def source_contracts() -> dict[str, Any]:
    helper = read_text(HELPER_SOURCE)
    return {
        "helper_source_present": bool(helper),
        "helper_has_pph_gate_flag": "--allow-android-wifi-service-window-pph-modem-fd-gate" in helper,
        "helper_has_pm_first_late_route": "pm-first-late-per-proxy-pph-gate" in helper,
        "helper_records_pph_gate_seen": "pph_modem_fd_gate_seen" in helper,
        "helper_records_child_exit_code_template": "android_wifi_service_window.child.%s.exit_code" in helper,
        "helper_mentions_per_mgr": "per_mgr" in helper,
        "helper_mentions_pm_proxy": "pm_proxy" in helper,
        "helper_records_stdout_stderr_blocks": "A90_EXECNS_STDERR_BEGIN" in helper,
        "helper_has_fd_match_utility": "/proc/%d/fd" in helper or "/proc" in helper and "fd" in helper,
    }


def analyze_v1602() -> dict[str, Any]:
    manifest = read_json(V1602_MANIFEST)
    summary = read_text(V1602_SUMMARY)
    helper_text = read_text(V1602_HELPER_RESULT)
    dmesg = read_text(V1602_DMESG)
    helper = parse_kv(helper_text)
    stderr = extract_block(helper_text, "A90_EXECNS_STDERR_BEGIN", "A90_EXECNS_STDERR_END")

    return {
        "manifest_cycle": manifest.get("cycle", ""),
        "manifest_decision": manifest.get("decision", ""),
        "manifest_handoff_pass": truthy(manifest.get("handoff_pass")),
        "summary_present": bool(summary),
        "helper_present": bool(helper_text),
        "helper_bytes": len(helper_text.encode("utf-8")),
        "dmesg_present": bool(dmesg),
        "dmesg_bytes": len(dmesg.encode("utf-8")),
        "helper_result": helper.get("android_wifi_service_window.result", ""),
        "helper_reason": helper.get("android_wifi_service_window.reason", ""),
        "helper_timed_out": int_value(helper.get("android_wifi_service_window.timed_out"), 0),
        "pph_gate_enabled": int_value(helper.get("android_wifi_service_window.pph_modem_fd_gate"), 0),
        "pph_gate_seen": int_value(helper.get("android_wifi_service_window.pph_modem_fd_gate_seen"), 0),
        "pph_gate_samples": int_value(helper.get("android_wifi_service_window.pph_modem_fd_gate_samples"), 0),
        "pph_gate_first_seen_ms": int_value(
            helper.get("android_wifi_service_window.pph_modem_fd_gate_first_seen_ms"), -1
        ),
        "pph_gate_final_count": int_value(
            helper.get("android_wifi_service_window.pph_modem_fd_gate_final_count"), -1
        ),
        "pm_proxy_helper_subsys_modem_fd_count": int_value(
            helper.get("android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count"), -1
        ),
        "per_mgr_observable": int_value(helper.get("android_wifi_service_window.child.per_mgr.observable"), -1),
        "per_mgr_exited": int_value(helper.get("android_wifi_service_window.child.per_mgr.exited"), -1),
        "per_mgr_exit_code": int_value(helper.get("android_wifi_service_window.child.per_mgr.exit_code"), -99),
        "per_mgr_signal": int_value(helper.get("android_wifi_service_window.child.per_mgr.signal"), -99),
        "per_mgr_postflight_safe": int_value(
            helper.get("android_wifi_service_window.child.per_mgr.postflight_safe"), -1
        ),
        "per_mgr_subsys_modem_fd_count": int_value(
            helper.get("android_wifi_service_window.per_mgr_subsys_modem_fd_count"), -1
        ),
        "pm_proxy_observable": int_value(helper.get("android_wifi_service_window.child.pm_proxy.observable"), -1),
        "pm_proxy_exited": int_value(helper.get("android_wifi_service_window.child.pm_proxy.exited"), -1),
        "pm_proxy_exit_code": int_value(helper.get("android_wifi_service_window.child.pm_proxy.exit_code"), -99),
        "pm_proxy_signal": int_value(helper.get("android_wifi_service_window.child.pm_proxy.signal"), -99),
        "pm_full_contract_seen": int_value(helper.get("android_wifi_service_window.pm_full_contract_seen"), -1),
        "mdm_helper_esoc0_fd_count": int_value(
            helper.get("android_wifi_service_window.mdm_helper_esoc0_fd_count"), -1
        ),
        "subsys_esoc0_open_attempted": int_value(
            helper.get("android_wifi_service_window.subsys_esoc0_open_attempted"), -1
        ),
        "esoc_ioctl_attempted": int_value(helper.get("android_wifi_service_window.esoc_ioctl_attempted"), -1),
        "subsys_trigger_started": int_value(helper.get("android_wifi_service_window.subsys_trigger.started"), -1),
        "scan_connect_linkup": int_value(helper.get("android_wifi_service_window.scan_connect_linkup"), -1),
        "credentials": int_value(helper.get("android_wifi_service_window.credentials"), -1),
        "dhcp_routing": int_value(helper.get("android_wifi_service_window.dhcp_routing"), -1),
        "external_ping": int_value(helper.get("android_wifi_service_window.external_ping"), -1),
        "stderr_bytes": len(stderr.encode("utf-8")),
        "stderr_has_property_protocol_warning": "old property service protocol" in stderr,
        "stderr_has_kmsg_permission_denied": "can't create /dev/kmsg" in stderr,
        "stderr_has_shell_quote_error": "no closing quote" in stderr,
        "stderr_has_pm_service_specific_text": any(
            token in stderr for token in ("pm-service", "per_mgr", "Peripheral", "PM service")
        ),
        "dmesg_modem_trigger_count": count_lines(dmesg, "__subsystem_get: modem"),
        "dmesg_pm_service_esoc0_count": count_lines(dmesg, "pm-service", "__subsystem_get: esoc0"),
        "dmesg_mdm_subsys_powerup_count": count_lines(dmesg, "mdm_subsys_powerup"),
        "dmesg_rc1_count": count_lines(dmesg, "PCIe RC1") + count_lines(dmesg, "pcie", "RC1"),
        "dmesg_wlfw_count": count_lines(dmesg, "wlfw") + count_lines(dmesg, "WLFW"),
        "dmesg_wlan0_count": count_lines(dmesg, "wlan0"),
    }


def classify() -> dict[str, Any]:
    current = analyze_v1602()
    contracts = source_contracts()
    checks = {
        "v1602_handoff_evidence_present": current["manifest_handoff_pass"]
        and current["summary_present"]
        and current["helper_present"],
        "pph_gate_passed": current["pph_gate_enabled"] == 1
        and current["pph_gate_seen"] == 1
        and current["pm_proxy_helper_subsys_modem_fd_count"] >= 1,
        "per_mgr_exited_clean_before_observable": current["per_mgr_exited"] == 1
        and current["per_mgr_exit_code"] == 0
        and current["per_mgr_observable"] == 0,
        "per_mgr_never_held_subsys_modem": current["per_mgr_subsys_modem_fd_count"] < 0,
        "pm_proxy_failed_after_per_mgr": current["pm_proxy_exited"] == 1 and current["pm_proxy_exit_code"] == 1,
        "pm_service_owned_esoc0_missing": current["pm_full_contract_seen"] == 0
        and current["subsys_esoc0_open_attempted"] == 0
        and current["subsys_trigger_started"] == 0,
        "downstream_markers_absent": current["dmesg_pm_service_esoc0_count"] == 0
        and current["dmesg_rc1_count"] == 0
        and current["dmesg_wlfw_count"] == 0
        and current["dmesg_wlan0_count"] == 0,
        "guardrails_preserved": current["scan_connect_linkup"] == 0
        and current["credentials"] == 0
        and current["dhcp_routing"] == 0
        and current["external_ping"] == 0,
        "source_records_required_fields": contracts["helper_has_pph_gate_flag"]
        and contracts["helper_records_pph_gate_seen"]
        and contracts["helper_records_child_exit_code_template"]
        and contracts["helper_mentions_per_mgr"]
        and contracts["helper_mentions_pm_proxy"],
    }
    pass_result = all(checks.values())
    decision = (
        "v1603-pph-gate-passed-per-mgr-exit-before-contract"
        if pass_result
        else "v1603-pm-service-exit-classification-incomplete"
    )
    reason = (
        "V1602 closes the pm_proxy_helper fd race: /dev/subsys_modem is present before per_mgr, but pm-service exits 0 before observation and before owning /dev/subsys_modem or /dev/subsys_esoc0; the next gate must instrument pm-service startup/lifetime, not RC1/MHI/WLFW"
        if pass_result
        else "existing evidence does not fully prove that the next blocker is pm-service clean early exit after a proven PPH modem fd"
    )
    next_gate = {
        "recommended_cycle": "V1604",
        "type": "source/build-only focused pm-service startup diagnostic",
        "focus": "extend a90_android_execns_probe with a tight per_mgr startup sampler after the proven PPH modem-fd gate",
        "success_markers": [
            "sample per_mgr at 10-20ms cadence from spawn until exit or one second",
            "record first observable time, exit time, exit code, signal, cwd, cmdline, wchan, and fd links if alive",
            "record whether per_mgr ever opens /dev/subsys_modem, /dev/vndbinder, /dev/hwbinder, binder sockets, or service-manager sockets",
            "capture per_mgr stdout/stderr byte counts and last diagnostic lines",
            "preserve the existing PPH fd gate and all scan/connect/credential/DHCP/external-ping guardrails",
        ],
        "live_follow_up": "V1605 artifact sanity, then V1606 rollbackable live handoff only if the diagnostic image excludes Wi-Fi HAL, scan/connect, DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes, blind eSoC notify/BOOT_DONE, global PCI rescan, and platform bind/unbind.",
    }
    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "v1602": current,
        "source_contracts": contracts,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    current = analysis["v1602"]
    next_gate = analysis["next_gate"]
    return "\n".join(
        [
            "# Native Init V1603 PM-Service Exit Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1603`",
            "- Type: host-only PM-service startup/lifetime classifier",
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
                    ["v1602_manifest", rel(V1602_MANIFEST)],
                    ["v1602_summary", rel(V1602_SUMMARY)],
                    ["v1602_helper_result", rel(V1602_HELPER_RESULT)],
                    ["v1602_dmesg", rel(V1602_DMESG)],
                    ["v1599_report", rel(V1599_REPORT)],
                    ["v1602_report", rel(V1602_REPORT)],
                    ["helper_source", rel(HELPER_SOURCE)],
                ],
            ),
            "",
            "## Derived Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
            "",
            "## V1602 Boundary",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["manifest_decision", current["manifest_decision"]],
                    ["helper_result", current["helper_result"]],
                    ["helper_reason", current["helper_reason"]],
                    ["pph_gate_enabled", current["pph_gate_enabled"]],
                    ["pph_gate_seen", current["pph_gate_seen"]],
                    ["pph_gate_first_seen_ms", current["pph_gate_first_seen_ms"]],
                    ["pph_gate_final_count", current["pph_gate_final_count"]],
                    ["pm_proxy_helper_subsys_modem_fd_count", current["pm_proxy_helper_subsys_modem_fd_count"]],
                    ["per_mgr_observable", current["per_mgr_observable"]],
                    ["per_mgr_exited", current["per_mgr_exited"]],
                    ["per_mgr_exit_code", current["per_mgr_exit_code"]],
                    ["per_mgr_subsys_modem_fd_count", current["per_mgr_subsys_modem_fd_count"]],
                    ["pm_proxy_observable", current["pm_proxy_observable"]],
                    ["pm_proxy_exit_code", current["pm_proxy_exit_code"]],
                    ["pm_full_contract_seen", current["pm_full_contract_seen"]],
                    ["subsys_esoc0_open_attempted", current["subsys_esoc0_open_attempted"]],
                    ["subsys_trigger_started", current["subsys_trigger_started"]],
                    ["mdm_helper_esoc0_fd_count", current["mdm_helper_esoc0_fd_count"]],
                ],
            ),
            "",
            "## Downstream Marker State",
            "",
            markdown_table(
                ["marker", "count/value"],
                [
                    ["dmesg __subsystem_get modem", current["dmesg_modem_trigger_count"]],
                    ["dmesg pm-service __subsystem_get esoc0", current["dmesg_pm_service_esoc0_count"]],
                    ["dmesg mdm_subsys_powerup", current["dmesg_mdm_subsys_powerup_count"]],
                    ["dmesg RC1", current["dmesg_rc1_count"]],
                    ["dmesg WLFW", current["dmesg_wlfw_count"]],
                    ["dmesg wlan0", current["dmesg_wlan0_count"]],
                    ["scan/connect guard", current["scan_connect_linkup"]],
                    ["credentials guard", current["credentials"]],
                    ["DHCP/routes guard", current["dhcp_routing"]],
                    ["external ping guard", current["external_ping"]],
                ],
            ),
            "",
            "## Stderr Triage",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["stderr_bytes", current["stderr_bytes"]],
                    ["old_property_service_warning", current["stderr_has_property_protocol_warning"]],
                    ["kmsg_permission_denied", current["stderr_has_kmsg_permission_denied"]],
                    ["shell_quote_error", current["stderr_has_shell_quote_error"]],
                    ["pm_service_specific_text", current["stderr_has_pm_service_specific_text"]],
                ],
            ),
            "",
            "## Interpretation",
            "",
            "V1602 proves the PPH fd race is closed: the route waits until "
            "`pm_proxy_helper` holds `/dev/subsys_modem` before starting "
            "`per_mgr`.  The failure still occurs above the SDX50M/eSoC/RC1 "
            "layer: `/vendor/bin/pm-service` exits with code `0` before it is "
            "observable in the sampling window and before it owns "
            "`/dev/subsys_modem`.  Consequently `pm-proxy` exits `1`, "
            "`pm_full_contract_seen` remains `0`, and no PM-service-owned "
            "`/dev/subsys_esoc0` or `mdm_subsys_powerup` marker exists.",
            "",
            "The current next step is therefore not another RC1/PERST/refclk "
            "or firmware/MHI/WLFW deep dive.  Those paths remain downstream "
            "until the Android-style PM-service contract survives long enough "
            "to trigger `/dev/subsys_esoc0`.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{next_gate['recommended_cycle']}`",
            f"- Type: {next_gate['type']}",
            f"- Focus: {next_gate['focus']}",
            "",
            "### Success Markers",
            "",
            *[f"- {item}" for item in next_gate["success_markers"]],
            "",
            "### Live Follow-Up Constraint",
            "",
            f"- {next_gate['live_follow_up']}",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, "
            "reboot, partition write, daemon start, Wi-Fi HAL start, scan/connect, "
            "credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC "
            "write, blind eSoC notify/`BOOT_DONE` spoof, pci-msm debugfs write, "
            "global PCI rescan, or platform bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = classify()
    manifest = {
        "cycle": "V1603",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "v1602_manifest": rel(V1602_MANIFEST),
            "v1602_summary": rel(V1602_SUMMARY),
            "v1602_helper_result": rel(V1602_HELPER_RESULT),
            "v1602_dmesg": rel(V1602_DMESG),
            "v1599_report": rel(V1599_REPORT),
            "v1602_report": rel(V1602_REPORT),
            "helper_source": rel(HELPER_SOURCE),
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
