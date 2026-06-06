#!/usr/bin/env python3
"""V1565 host-only service-window gap classifier.

V1564 proved that the V1562 test boot can launch the Android Wi-Fi
service-window start-only route and roll back safely, but it did not produce
WLFW/BDF/FW-ready/wlan0 progress.  This classifier reconciles that result with
the older V998/V1001 service-window evidence and selects the next bounded gate.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1565-service-window-gap-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1565_SERVICE_WINDOW_GAP_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1565-service-window-gap-classifier.txt")

V1562_MANIFEST = Path("tmp/wifi/v1562-android-wifi-service-window-test-boot/manifest.json")
V1564_MANIFEST = Path("tmp/wifi/v1564-android-wifi-service-window-handoff/manifest.json")
V1564_LOG = Path("tmp/wifi/v1564-android-wifi-service-window-handoff/test-v1393-log.stdout.txt")
V1564_SUMMARY = Path("tmp/wifi/v1564-android-wifi-service-window-handoff/test-v1393-summary.stdout.txt")
V1564_DMESG = Path("tmp/wifi/v1564-android-wifi-service-window-handoff/test-v1393-dmesg.stdout.txt")
V998_MANIFEST = Path("tmp/wifi/v998-android-service-window-live-v169-post-selinux/manifest.json")
V1001_MANIFEST = Path("tmp/wifi/v1001-v1000-route-comparator/manifest.json")
BUILD_SCRIPT = Path("scripts/revalidation/build_native_init_wifi_test_boot_v1393.py")
PID1_SOURCE = Path("stage3/linux_init/v724/90_main.inc.c")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


KV_RE = re.compile(r"(?P<key>[A-Za-z0-9_.:-]+)=(?P<value>[^\n\r ]+)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def get_nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def parse_kv_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for match in KV_RE.finditer(text):
        values[match.group("key")] = match.group("value")
    return values


def truthy_text(value: Any) -> bool:
    return value is True or value == 1 or value == "1" or value == "true"


def present_text(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def source_contracts() -> dict[str, Any]:
    build_source = read_text(BUILD_SCRIPT)
    pid1_source = read_text(PID1_SOURCE)
    helper_source = read_text(HELPER_SOURCE)
    return {
        "build_supports_start_only": "android-service-window-start-only" in build_source,
        "build_supports_subsys_trigger_capture": "android-service-window-subsys-trigger-capture" in build_source,
        "pid1_has_subsys_trigger_macro": "A90_WIFI_TEST_BOOT_ANDROID_SERVICE_WINDOW_SUBSYS_TRIGGER_CAPTURE" in pid1_source,
        "pid1_adds_subsys_trigger_allow_flag": "--allow-android-wifi-service-window-subsys-trigger-capture" in pid1_source,
        "helper_supports_start_only_mode": "wifi-companion-android-wifi-service-window-start-only" in helper_source,
        "helper_supports_subsys_trigger_capture_mode": "wifi-companion-android-wifi-service-window-subsys-trigger-capture" in helper_source,
        "helper_supports_subsys_trigger_allow_flag": "--allow-android-wifi-service-window-subsys-trigger-capture" in helper_source,
        "helper_has_subsys_trigger_child": "start_cnss_before_esoc_subsys_trigger_child" in helper_source,
        "helper_records_subsys_trigger_result": "cnss_before_esoc.subsys_trigger.started" in helper_source,
        "helper_keeps_connect_guardrails": (
            "cnss_before_esoc.scan_connect_linkup=0" in helper_source
            and "cnss_before_esoc.credentials=0" in helper_source
            and "cnss_before_esoc.dhcp_routing=0" in helper_source
            and "cnss_before_esoc.external_ping=0" in helper_source
        ),
    }


def v1564_analysis(v1562: dict[str, Any], v1564: dict[str, Any]) -> dict[str, Any]:
    log_text = read_text(V1564_LOG)
    summary_text = read_text(V1564_SUMMARY)
    dmesg_text = read_text(V1564_DMESG)
    log_kv = parse_kv_text(log_text)
    summary_kv = parse_kv_text(summary_text)
    progress = v1564.get("wifi_progress") if isinstance(v1564.get("wifi_progress"), dict) else {}
    wifi_test = v1562.get("wifi_test") if isinstance(v1562.get("wifi_test"), dict) else {}
    return {
        "decision": v1564.get("decision"),
        "pass": v1564.get("pass"),
        "handoff_pass": v1564.get("handoff_pass"),
        "rollback_ok": get_nested(v1564, "rollback", "ok"),
        "artifact_helper_mode": wifi_test.get("helper_mode"),
        "artifact_runtime_mode": wifi_test.get("helper_runtime_mode"),
        "helper_mode_from_log": log_kv.get("mode"),
        "helper_exit_code": progress.get("helper_exit_code", summary_kv.get("helper_exit_code")),
        "helper_timed_out": progress.get("helper_timed_out", summary_kv.get("helper_timed_out")),
        "wlan0_present": progress.get("wlan0_present"),
        "final_decision": progress.get("final_decision"),
        "wlfw_progress": progress.get("wlfw_progress"),
        "provider_trigger": progress.get("provider_trigger"),
        "rc1_progress": progress.get("rc1_progress"),
        "generic_cnss_seen": has_any(dmesg_text, ["cnss-daemon", "cnss_diag"]),
        "wificond_seen": "wificond" in dmesg_text,
        "wifi_hal_seen": "wifi_hal" in dmesg_text,
        "wlfw_request_seen": has_any(dmesg_text, ["wlfw_start", "wlfw_service_request"]),
        "contract_stdout_seen": has_any(log_text + summary_text, ["cnss_before_esoc.", "android_wifi_service_window."]),
        "log_size": summary_kv.get("log_size"),
    }


def v998_analysis(v998: dict[str, Any]) -> dict[str, Any]:
    contract = get_nested(v998, "analysis", "helper", "contract")
    if not isinstance(contract, dict):
        contract = {}
    return {
        "decision": v998.get("decision"),
        "pass": v998.get("pass"),
        "order": contract.get("order"),
        "service_manager_start_executed": contract.get("service_manager_start_executed"),
        "wifi_hal_start_executed": contract.get("wifi_hal_start_executed"),
        "wificond_start_executed": contract.get("wificond_start_executed"),
        "mdm_helper_start_executed": contract.get("mdm_helper_start_executed"),
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_executed"),
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted"),
        "esoc_ioctl_attempted": contract.get("esoc_ioctl_attempted"),
        "all_observable_at_timeout": contract.get("all_observable_at_timeout"),
        "all_postflight_safe": contract.get("all_postflight_safe"),
        "wlfw_precondition_observed": contract.get("wlfw_precondition_observed"),
        "result": contract.get("result"),
        "reason": contract.get("reason"),
        "guardrails": {
            "scan_connect_linkup": contract.get("scan_connect_linkup"),
            "credentials": contract.get("credentials"),
            "dhcp_routing": contract.get("dhcp_routing"),
            "external_ping": contract.get("external_ping"),
        },
    }


def v1001_analysis(v1001: dict[str, Any]) -> dict[str, Any]:
    checks = v1001.get("checks") if isinstance(v1001.get("checks"), dict) else {}
    return {
        "decision": v1001.get("decision"),
        "pass": v1001.get("pass"),
        "v1000_android_reached_lower_wlfw": checks.get("v1000_android_reached_lower_wlfw"),
        "v1000_esoc_before_wlfw": checks.get("v1000_esoc_before_wlfw"),
        "v998_service_window_clean_no_wlfw": checks.get("v998_service_window_clean_no_wlfw"),
        "v998_did_not_try_subsys": checks.get("v998_did_not_try_subsys"),
        "v923_wlfw_gate_too_strict": checks.get("v923_wlfw_gate_too_strict"),
    }


def classify() -> dict[str, Any]:
    v1562 = read_json(V1562_MANIFEST)
    v1564 = read_json(V1564_MANIFEST)
    v998 = read_json(V998_MANIFEST)
    v1001 = read_json(V1001_MANIFEST)

    current = v1564_analysis(v1562, v1564)
    prior_service_window = v998_analysis(v998)
    route_comparator = v1001_analysis(v1001)
    contracts = source_contracts()

    checks = {
        "v1564_handoff_and_rollback_ok": truthy_text(current["handoff_pass"]) and truthy_text(current["rollback_ok"]),
        "v1564_used_start_only_route": (
            current["artifact_helper_mode"] == "android-service-window-start-only"
            and current["artifact_runtime_mode"] == "wifi-companion-android-wifi-service-window-start-only"
        ),
        "v1564_no_downstream_progress": (
            current["final_decision"] == "no-provider-no-downstream"
            and not truthy_text(current["wlfw_progress"])
            and not truthy_text(current["wlan0_present"])
        ),
        "v1564_actor_surface_seen_but_contract_stdout_sparse": (
            truthy_text(current["generic_cnss_seen"])
            and truthy_text(current["wificond_seen"])
            and not truthy_text(current["contract_stdout_seen"])
        ),
        "v998_full_service_window_clean_no_wlfw": (
            truthy_text(prior_service_window["pass"])
            and prior_service_window["result"] == "service-window-no-wlfw"
            and truthy_text(prior_service_window["all_observable_at_timeout"])
            and truthy_text(prior_service_window["all_postflight_safe"])
            and not truthy_text(prior_service_window["wlfw_precondition_observed"])
        ),
        "v998_did_not_attempt_subsys": (
            prior_service_window["subsys_esoc0_open_attempted"] == "0"
            and prior_service_window["esoc_ioctl_attempted"] == "0"
        ),
        "v1001_selects_scoped_subsys_trigger": (
            truthy_text(route_comparator["pass"])
            and route_comparator["decision"] == "v1001-select-service-window-scoped-subsys-trigger-support"
            and truthy_text(route_comparator["v1000_android_reached_lower_wlfw"])
            and truthy_text(route_comparator["v998_service_window_clean_no_wlfw"])
            and truthy_text(route_comparator["v998_did_not_try_subsys"])
        ),
        "source_supports_subsys_trigger_capture": all(
            truthy_text(contracts[key])
            for key in (
                "build_supports_subsys_trigger_capture",
                "pid1_has_subsys_trigger_macro",
                "pid1_adds_subsys_trigger_allow_flag",
                "helper_supports_subsys_trigger_capture_mode",
                "helper_supports_subsys_trigger_allow_flag",
                "helper_has_subsys_trigger_child",
                "helper_records_subsys_trigger_result",
                "helper_keeps_connect_guardrails",
            )
        ),
    }
    pass_result = all(checks.values())
    decision = (
        "v1565-select-service-window-subsys-trigger-capture-build"
        if pass_result
        else "v1565-service-window-gap-incomplete-review"
    )
    reason = (
        "V1564 proves start-only service-window handoff and rollback but no WLFW/downstream progress; V998/V1001 already show the repaired actor window needs a scoped subsys_esoc0 trigger, and current sources support the trigger-capture test-boot route"
        if pass_result
        else "existing evidence does not fully prove that the next gate should switch from start-only to scoped subsys-trigger capture"
    )
    next_gate = {
        "recommended_cycle": "V1566",
        "type": "source/build-only service-window subsys-trigger-capture artifact",
        "focus": "build the Wi-Fi test boot with android-service-window-subsys-trigger-capture instead of start-only",
        "success_markers": [
            "artifact helper_mode is android-service-window-subsys-trigger-capture",
            "PID1 argv contains --allow-android-wifi-service-window and --allow-android-wifi-service-window-subsys-trigger-capture",
            "artifact excludes credentials, scan/connect, DHCP/routes, external ping, blind notify/BOOT_DONE, global PCI rescan, and platform bind/unbind",
            "sanity verifier confirms the live follow-up will collect cnss_before_esoc/subsys trigger fields",
        ],
        "live_follow_up": "rollbackable handoff may run only after source/build sanity; target is WLFW/BDF/FW-ready/wlan0 progress, still no credentials or external ping",
    }
    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "current_v1564": current,
        "prior_v998": prior_service_window,
        "route_v1001": route_comparator,
        "source_contracts": contracts,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    current = analysis["current_v1564"]
    prior = analysis["prior_v998"]
    route = analysis["route_v1001"]
    contracts = analysis["source_contracts"]
    return "\n".join(
        [
            "# Native Init V1565 Service-Window Gap Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1565`",
            "- Type: host-only service-window gap classifier",
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
                    ["v1562_service_window_artifact", rel(V1562_MANIFEST)],
                    ["v1564_live_handoff", rel(V1564_MANIFEST)],
                    ["v1564_log", rel(V1564_LOG)],
                    ["v1564_summary", rel(V1564_SUMMARY)],
                    ["v1564_dmesg", rel(V1564_DMESG)],
                    ["v998_service_window", rel(V998_MANIFEST)],
                    ["v1001_route_comparator", rel(V1001_MANIFEST)],
                    ["build_script", rel(BUILD_SCRIPT)],
                    ["pid1_source", rel(PID1_SOURCE)],
                    ["helper_source", rel(HELPER_SOURCE)],
                ],
            ),
            "",
            "## Derived Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
            "",
            "## V1564 Current Result",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["decision", current["decision"]],
                    ["handoff_pass", current["handoff_pass"]],
                    ["rollback_ok", current["rollback_ok"]],
                    ["artifact_helper_mode", current["artifact_helper_mode"]],
                    ["artifact_runtime_mode", current["artifact_runtime_mode"]],
                    ["helper_exit_code", current["helper_exit_code"]],
                    ["helper_timed_out", current["helper_timed_out"]],
                    ["final_decision", current["final_decision"]],
                    ["generic_cnss_seen", current["generic_cnss_seen"]],
                    ["wificond_seen", current["wificond_seen"]],
                    ["wifi_hal_seen", current["wifi_hal_seen"]],
                    ["wlfw_request_seen", current["wlfw_request_seen"]],
                    ["contract_stdout_seen", current["contract_stdout_seen"]],
                    ["log_size", current["log_size"]],
                ],
            ),
            "",
            "## Prior Service-Window Evidence",
            "",
            markdown_table(
                ["field", "V998", "V1001"],
                [
                    ["decision", prior["decision"], route["decision"]],
                    ["pass", prior["pass"], route["pass"]],
                    ["actor order", prior["order"], "see checks"],
                    ["all observable", prior["all_observable_at_timeout"], "n/a"],
                    ["all postflight safe", prior["all_postflight_safe"], "n/a"],
                    ["wlfw precondition observed", prior["wlfw_precondition_observed"], "n/a"],
                    ["subsys_esoc0 open attempted", prior["subsys_esoc0_open_attempted"], "V1001 says missing trigger"],
                    ["Android lower WLFW reached", "n/a", route["v1000_android_reached_lower_wlfw"]],
                    ["route selected", "n/a", route["decision"]],
                ],
            ),
            "",
            "## Source Support",
            "",
            markdown_table(["contract", "present"], [[key, present_text(value)] for key, value in contracts.items()]),
            "",
            "## Interpretation",
            "",
            "V1564 is a valid rollbackable live proof of the `start-only` service-window "
            "artifact, but it is not a reason to retry the same route: the helper exits "
            "cleanly, generic `cnss-daemon`/`cnss_diag` and `wificond` activity is visible, "
            "and no WLFW/BDF/FW-ready/`wlan0` progress appears.  The detailed helper "
            "contract output is sparse in the PID1 log, so the next live artifact must "
            "also preserve enough `cnss_before_esoc`/subsys-trigger evidence to classify "
            "the actor window.",
            "",
            "The older V998/V1001 chain remains relevant: after service-window SELinux and "
            "actor observability were repaired, V998 still had no WLFW because it did not "
            "attempt `/dev/subsys_esoc0`; V1001 selected a scoped service-window subsystem "
            "trigger rather than another pre-WLFW wait.  Current sources already expose that "
            "trigger-capture route at build time.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{analysis['next_gate']['recommended_cycle']}`",
            f"- Type: {analysis['next_gate']['type']}",
            f"- Focus: {analysis['next_gate']['focus']}",
            "",
            "### Success Markers",
            "",
            *[f"- {item}" for item in analysis["next_gate"]["success_markers"]],
            "",
            "### Live Follow-Up Constraint",
            "",
            f"- {analysis['next_gate']['live_follow_up']}",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, "
            "partition write, daemon start, Wi-Fi HAL start, scan/connect, credential "
            "handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/"
            "BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform "
            "bind/unbind.",
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
        "cycle": "V1565",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "v1562_service_window_artifact": rel(V1562_MANIFEST),
            "v1564_live_handoff": rel(V1564_MANIFEST),
            "v1564_log": rel(V1564_LOG),
            "v1564_summary": rel(V1564_SUMMARY),
            "v1564_dmesg": rel(V1564_DMESG),
            "v998_service_window": rel(V998_MANIFEST),
            "v1001_route_comparator": rel(V1001_MANIFEST),
            "build_script": rel(BUILD_SCRIPT),
            "pid1_source": rel(PID1_SOURCE),
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
