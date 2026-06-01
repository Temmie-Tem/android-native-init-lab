#!/usr/bin/env python3
"""V1593 host-only classifier for V1592 late per-proxy / per_mgr lifetime failure.

V1592 proved the rollbackable test-boot handoff works, but strict
reclassification shows no RC1/MHI/WLFW/BDF/FW-ready/wlan0 progress.  This
classifier compares V1592 with the older V1238/V1303 positive late per-proxy
route to determine whether the next blocker is lower hardware or failure to
reproduce the PM-service-owned `/dev/subsys_esoc0` route.

It does not contact the device or mutate artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1593-pm-proxy-per-mgr-lifetime-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1593_PM_PROXY_PER_MGR_LIFETIME_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1593-pm-proxy-per-mgr-lifetime-classifier.txt")

V1592_RECLASSIFY_MANIFEST = Path("tmp/wifi/v1592-late-per-proxy-lower-marker-reclassify/manifest.json")
V1592_HANDOFF_MANIFEST = Path("tmp/wifi/v1592-late-per-proxy-lower-marker-handoff/manifest.json")
V1592_HELPER = Path(
    "tmp/wifi/v1592-late-per-proxy-lower-marker-handoff/test-v1393-helper-result.stdout.txt"
)
V1592_DMESG = Path("tmp/wifi/v1592-late-per-proxy-lower-marker-handoff/test-v1393-dmesg.stdout.txt")
V1238_MANIFEST = Path("tmp/wifi/v1238-late-per-proxy-only-live/manifest.json")
V1238_SUMMARY = Path("tmp/wifi/v1238-late-per-proxy-only-live/summary.md")
V1303_MANIFEST = Path("tmp/wifi/v1303-compact-powerup-marker-live/manifest.json")
V1303_SUMMARY = Path("tmp/wifi/v1303-compact-powerup-marker-live/summary.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path, limit: int = 8 * 1024 * 1024) -> str:
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


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def helper_value(text: str, key: str) -> str | None:
    prefix = key + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def summary_value(text: str, key: str) -> str | None:
    prefix = f"| {key} |"
    for line in text.splitlines():
        if line.startswith(prefix):
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) >= 2:
                return parts[1].strip("` ")
    return None


def count_lines(text: str, *needles: str) -> int:
    return sum(1 for line in text.splitlines() if all(needle in line for needle in needles))


def bool_text(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def analyze_v1592() -> dict[str, Any]:
    reclassify = read_json(V1592_RECLASSIFY_MANIFEST)
    handoff = read_json(V1592_HANDOFF_MANIFEST)
    helper = read_text(V1592_HELPER)
    dmesg = read_text(V1592_DMESG)
    progress = reclassify.get("wifi_progress") if isinstance(reclassify.get("wifi_progress"), dict) else {}
    handoff_progress = handoff.get("wifi_progress") if isinstance(handoff.get("wifi_progress"), dict) else {}

    order = helper_value(helper, "android_wifi_service_window.order") or ""
    pm_proxy_pid = int_value(helper_value(helper, "wifi_hal_composite_start.child.pm_proxy.pid"), -1)
    per_mgr_pid = int_value(helper_value(helper, "wifi_hal_composite_start.child.per_mgr.pid"), -1)

    return {
        "strict_decision": reclassify.get("decision", ""),
        "strict_pass": truthy(reclassify.get("pass")),
        "handoff_pass": truthy(reclassify.get("handoff_pass")) or (
            truthy(handoff.get("pass")) and truthy(handoff.get("handoff_pass"))
        ),
        "rollback_ok": truthy((reclassify.get("rollback") or {}).get("ok"))
        or truthy((handoff.get("rollback") or {}).get("ok")),
        "strict_final_decision": progress.get("final_decision"),
        "source_final_decision_before_hardening": handoff_progress.get("final_decision"),
        "modem_trigger": truthy(progress.get("modem_trigger")),
        "provider_trigger": truthy(progress.get("provider_trigger")),
        "rc1_progress": truthy(progress.get("rc1_progress")),
        "mhi_progress": truthy(progress.get("mhi_progress")),
        "wlfw_progress": truthy(progress.get("wlfw_progress")),
        "icnss_qmi_connected": truthy(progress.get("icnss_qmi_connected")),
        "wlan0_present": truthy(progress.get("wlan0_present")),
        "order": order,
        "order_has_wifi_hal_before_per_mgr": "wifi_hal_legacy,wifi_hal_ext,per_mgr" in order,
        "order_has_late_pm_proxy": "pm_proxy_late" in order,
        "order_has_direct_trigger_disabled": "lower-marker-no-direct-trigger" in order,
        "pm_proxy_exec_attempted": int_value(
            helper_value(helper, "wifi_hal_composite_start.child.pm_proxy.exec_attempted"), -1
        ),
        "pm_proxy_child_started": int_value(
            helper_value(helper, "wifi_hal_composite_start.child.pm_proxy.child_started"), -1
        ),
        "pm_proxy_pid": pm_proxy_pid,
        "pm_proxy_preexec_status": helper_value(helper, "wifi_hal_composite_child.pm_proxy.preexec_status"),
        "pm_proxy_selinux_exec_ok": int_value(
            helper_value(helper, "wifi_hal_composite_child.pm_proxy.selinux_exec.ok"), -1
        ),
        "pm_proxy_selinux_current_ok": int_value(
            helper_value(helper, "wifi_hal_composite_child.pm_proxy.selinux_current.ok"), -1
        ),
        "pm_proxy_target": helper_value(helper, "wifi_hal_composite_start.child.pm_proxy.target"),
        "pm_proxy_observable": int_value(
            helper_value(helper, "android_wifi_service_window.child.pm_proxy.observable"), -1
        ),
        "pm_proxy_exited": int_value(
            helper_value(helper, "android_wifi_service_window.child.pm_proxy.exited"), -1
        ),
        "pm_proxy_exit_code": int_value(
            helper_value(helper, "android_wifi_service_window.child.pm_proxy.exit_code"), -99
        ),
        "per_mgr_exec_attempted": int_value(
            helper_value(helper, "wifi_hal_composite_start.child.per_mgr.exec_attempted"), -1
        ),
        "per_mgr_child_started": int_value(
            helper_value(helper, "wifi_hal_composite_start.child.per_mgr.child_started"), -1
        ),
        "per_mgr_pid": per_mgr_pid,
        "per_mgr_preexec_status": helper_value(helper, "wifi_hal_composite_child.per_mgr.preexec_status"),
        "per_mgr_target": helper_value(helper, "wifi_hal_composite_start.child.per_mgr.target"),
        "per_mgr_initial_fd_match_error": helper_value(
            helper, "android_wifi_service_window.fd_match.per_mgr_subsys_modem_initial.error"
        ),
        "per_mgr_initial_subsys_modem_count": int_value(
            helper_value(helper, "android_wifi_service_window.fd_match.per_mgr_subsys_modem_initial.count"), -99
        ),
        "per_mgr_observable": int_value(
            helper_value(helper, "android_wifi_service_window.child.per_mgr.observable"), -1
        ),
        "per_mgr_exited": int_value(
            helper_value(helper, "android_wifi_service_window.child.per_mgr.exited"), -1
        ),
        "per_mgr_exit_code": int_value(
            helper_value(helper, "android_wifi_service_window.child.per_mgr.exit_code"), -99
        ),
        "pm_proxy_helper_initial_subsys_modem_count": int_value(
            helper_value(helper, "android_wifi_service_window.pm_proxy_helper_subsys_modem_initial_count"), -99
        ),
        "pm_proxy_helper_final_subsys_modem_count": int_value(
            helper_value(helper, "android_wifi_service_window.pm_proxy_helper_subsys_modem_fd_count"), -99
        ),
        "per_mgr_final_subsys_modem_count": int_value(
            helper_value(helper, "android_wifi_service_window.per_mgr_subsys_modem_fd_count"), -99
        ),
        "pm_full_contract_seen": int_value(
            helper_value(helper, "android_wifi_service_window.pm_full_contract_seen"), -99
        ),
        "mdm_helper_esoc0_fd_count": int_value(
            helper_value(helper, "android_wifi_service_window.mdm_helper_esoc0_fd_count"), -99
        ),
        "subsys_esoc0_open_attempted": int_value(
            helper_value(helper, "android_wifi_service_window.subsys_esoc0_open_attempted"), -99
        ),
        "subsys_trigger_started": int_value(
            helper_value(helper, "android_wifi_service_window.subsys_trigger.started"), -99
        ),
        "result": helper_value(helper, "android_wifi_service_window.result"),
        "reason": helper_value(helper, "android_wifi_service_window.reason"),
        "dmesg_modem_get_count": count_lines(dmesg, "__subsystem_get: modem"),
        "dmesg_pm_service_esoc0_get_count": count_lines(dmesg, "pm-service", "__subsystem_get: esoc0"),
        "dmesg_icnss_qmi_shutdown_fail_count": count_lines(dmesg, "icnss_qmi: Fail to send Shutdown req"),
        "dmesg_icnss_qmi_connected_count": count_lines(dmesg, "icnss_qmi: QMI Server Connected"),
    }


def analyze_positive_route() -> dict[str, Any]:
    v1238 = read_json(V1238_MANIFEST)
    v1238_summary = read_text(V1238_SUMMARY)
    v1303 = read_json(V1303_MANIFEST)
    v1303_summary = read_text(V1303_SUMMARY)
    v1238_order = summary_value(v1238_summary, "pm_order") or ""

    return {
        "v1238_decision": v1238.get("decision", ""),
        "v1238_pass": truthy(v1238.get("pass")),
        "v1238_order": v1238_order,
        "v1238_order_has_no_wifi_hal": "wifi_hal" not in v1238_order and "wificond" not in v1238_order,
        "v1238_order_has_per_mgr_before_late_proxy": "pm_proxy_helper,per_mgr" in v1238_order
        and "late_per_proxy" in v1238_order,
        "v1238_order_has_deferred_proxy": "per_proxy_deferred" in v1238_order,
        "v1238_late_started": int_value(summary_value(v1238_summary, "late_started"), -1),
        "v1238_late_gate_positive": int_value(summary_value(v1238_summary, "late_gate_positive"), -1),
        "v1238_pm_service_actor_esoc0_attempt": bool_text(
            summary_value(v1238_summary, "pm_service_actor_esoc0_attempt")
        ),
        "v1238_post_pm_fd_esoc0_count": int_value(
            summary_value(v1238_summary, "post_pm_fd_esoc0_count"), 0
        ),
        "v1238_post_pm_result": summary_value(v1238_summary, "post_pm_result"),
        "v1238_boundary_wlan0_seen": bool_text(summary_value(v1238_summary, "boundary_wlan0_seen")),
        "v1303_decision": v1303.get("decision", ""),
        "v1303_pass": truthy(v1303.get("pass")),
        "v1303_late_per_proxy_started": int_value(
            summary_value(v1303_summary, "late_per_proxy_started"), -1
        ),
        "v1303_powerup_marker_emitted": bool_text(summary_value(v1303_summary, "powerup_marker_emitted")),
        "v1303_max_powerup_thread_count": int_value(
            summary_value(v1303_summary, "max_powerup_thread_count"), 0
        ),
        "v1303_powerup_subsys_esoc0_inferred_seen": bool_text(
            summary_value(v1303_summary, "powerup_subsys_esoc0_inferred_seen")
        ),
        "v1303_powerup_first_path_values": summary_value(v1303_summary, "powerup_first_path_values"),
        "v1303_powerup_first_wchans": summary_value(v1303_summary, "powerup_first_wchans"),
        "v1303_powerup_first_syscall_names": summary_value(
            v1303_summary, "powerup_first_syscall_names"
        ),
        "v1303_wlan0_seen": bool_text(summary_value(v1303_summary, "wlan0_seen")),
    }


def analyze() -> dict[str, Any]:
    current = analyze_v1592()
    positive = analyze_positive_route()

    handoff_clean = current["handoff_pass"] and current["rollback_ok"]
    v1592_before_lower = (
        handoff_clean
        and current["strict_final_decision"] == "modem-trigger-no-downstream"
        and current["modem_trigger"]
        and not current["provider_trigger"]
        and not current["rc1_progress"]
        and not current["mhi_progress"]
        and not current["wlfw_progress"]
        and not current["wlan0_present"]
    )
    pm_proxy_spawned_then_exited = (
        current["pm_proxy_exec_attempted"] == 1
        and current["pm_proxy_child_started"] == 1
        and current["pm_proxy_pid"] > 0
        and current["pm_proxy_preexec_status"] == "pass"
        and current["pm_proxy_selinux_exec_ok"] == 1
        and current["pm_proxy_selinux_current_ok"] == 1
        and current["pm_proxy_exited"] == 1
        and current["pm_proxy_exit_code"] == 1
    )
    per_mgr_gone_before_contract = (
        current["per_mgr_exec_attempted"] == 1
        and current["per_mgr_child_started"] == 1
        and current["per_mgr_pid"] > 0
        and current["per_mgr_initial_fd_match_error"] == "No such file or directory"
        and current["per_mgr_observable"] == 0
        and current["per_mgr_exited"] == 1
        and current["per_mgr_exit_code"] == 0
        and current["pm_full_contract_seen"] == 0
    )
    positive_route_proves_target = (
        positive["v1238_pass"]
        and positive["v1238_late_started"] == 1
        and positive["v1238_pm_service_actor_esoc0_attempt"]
        and positive["v1238_post_pm_fd_esoc0_count"] > 0
        and positive["v1303_pass"]
        and positive["v1303_late_per_proxy_started"] == 1
        and positive["v1303_powerup_marker_emitted"]
        and positive["v1303_max_powerup_thread_count"] > 0
        and positive["v1303_powerup_subsys_esoc0_inferred_seen"]
        and positive["v1303_powerup_first_path_values"] == "/dev/subsys_esoc0"
        and positive["v1303_powerup_first_wchans"] == "mdm_subsys_powerup"
    )
    order_delta_explains_regression = (
        current["order_has_wifi_hal_before_per_mgr"]
        and current["order_has_late_pm_proxy"]
        and positive["v1238_order_has_no_wifi_hal"]
        and positive["v1238_order_has_deferred_proxy"]
    )

    checks = [
        {
            "name": "v1592-handoff-clean",
            "status": "pass" if handoff_clean else "fail",
            "detail": "V1592 test boot evidence exists, rollback verified, and device selftest stayed clean",
        },
        {
            "name": "v1592-before-lower-hardware",
            "status": "pass" if v1592_before_lower else "fail",
            "detail": "strict V1592 has modem trigger only; no provider/RC1/MHI/WLFW/wlan0 marker",
        },
        {
            "name": "v1592-pm-proxy-spawned-then-exited",
            "status": "pass" if pm_proxy_spawned_then_exited else "fail",
            "detail": "pm-proxy child preexec/SELinux setup passes but exits 1",
        },
        {
            "name": "v1592-per-mgr-gone-before-contract",
            "status": "pass" if per_mgr_gone_before_contract else "fail",
            "detail": "pm-service starts but /proc fd match already fails and PM full contract is absent",
        },
        {
            "name": "positive-route-proves-target",
            "status": "pass" if positive_route_proves_target else "fail",
            "detail": "V1238/V1303 prove late pm-proxy can drive PM-service into /dev/subsys_esoc0/mdm_subsys_powerup",
        },
        {
            "name": "ordering-delta-is-actionable",
            "status": "pass" if order_delta_explains_regression else "fail",
            "detail": "V1592 full service-window order differs from stripped positive PM route before late actor",
        },
    ]
    pass_ok = all(item["status"] == "pass" for item in checks)
    decision = (
        "v1593-late-per-proxy-regressed-before-pm-service-owned-powerup"
        if pass_ok
        else "v1593-input-evidence-incomplete-review-required"
    )
    reason = (
        "V1592 never reaches the lower eSoC/RC1 boundary because per_mgr exits before the PM contract and late pm-proxy exits 1; V1238/V1303 show the stripped late-per_proxy route can reach PM-service-owned /dev/subsys_esoc0"
        if pass_ok
        else "one or more V1592/V1238/V1303 evidence predicates are missing or contradictory"
    )
    next_step = (
        "V1594 source/build-only: preserve V1591 firmware mounts but switch the test-boot service-window to a V1238-style PM-first route with no Wi-Fi HAL/wificond before PM-service-owned /dev/subsys_esoc0 observation, and add explicit pm-proxy/per_mgr exit diagnostics"
        if pass_ok
        else "refresh or inspect missing evidence before another live gate"
    )

    return {
        "cycle": "V1593",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1592_reclassify_manifest": rel(V1592_RECLASSIFY_MANIFEST),
            "v1592_handoff_manifest": rel(V1592_HANDOFF_MANIFEST),
            "v1592_helper": rel(V1592_HELPER),
            "v1592_dmesg": rel(V1592_DMESG),
            "v1238_manifest": rel(V1238_MANIFEST),
            "v1238_summary": rel(V1238_SUMMARY),
            "v1303_manifest": rel(V1303_MANIFEST),
            "v1303_summary": rel(V1303_SUMMARY),
        },
        "current_v1592": current,
        "positive_pm_route": positive,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
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
    current = manifest["current_v1592"]
    positive = manifest["positive_pm_route"]
    return "\n".join(
        [
            "# V1593 PM Proxy / per_mgr Lifetime Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(["input", "path"], [[key, value] for key, value in manifest["inputs"].items()]),
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "status", "detail"],
                [[item["name"], item["status"], item["detail"]] for item in manifest["checks"]],
            ),
            "",
            "## Current V1592 Route",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in current.items()]),
            "",
            "## Positive PM-service Route References",
            "",
            markdown_table(["field", "value"], [[key, value] for key, value in positive.items()]),
            "",
            "## Interpretation",
            "",
            "V1592 did not reach the lower SDX50M/eSoC/RC1 boundary.  The live",
            "handoff itself is valid, but the strict evidence shows only the modem",
            "holder path and no provider, RC1, MHI, WLFW, BDF, FW-ready, or `wlan0`",
            "progress.  The late `pm-proxy` child is spawned with successful preexec",
            "setup, then exits `1`.  `pm-service` (`per_mgr`) exits `0` before fd",
            "matching can inspect `/dev/subsys_modem`, so the full PM contract is",
            "never seen.",
            "",
            "V1238/V1303 remain the positive references for this exact boundary:",
            "their stripped PM-first late-`per_proxy` route reaches a PM-service",
            "owned `/dev/subsys_esoc0` open with `mdm_subsys_powerup`.  Therefore",
            "the next test boot should not continue deeper into firmware/MHI or",
            "scan/connect.  It should repair the service-window route so it first",
            "reproduces the V1238/V1303 PM-service-owned powerup path while keeping",
            "V1591 firmware mount parity.",
            "",
            "## Safety",
            "",
            "Host-only classifier. No device command, Wi-Fi HAL, scan/connect,",
            "credentials, DHCP/routes, external ping, flash, boot image write, or",
            "partition write occurred.",
            "",
        ]
    )


def check_forbidden_output(manifest: dict[str, Any]) -> list[str]:
    text = json.dumps(manifest, sort_keys=True) + "\n" + render_summary(manifest)
    forbidden = [b"temmie" + b"5G", b"temmie" + b"0214"]
    encoded = text.encode("utf-8", errors="replace")
    hits: list[str] = []
    for index, value in enumerate(forbidden, 1):
        if value in encoded:
            hits.append(f"forbidden-pattern-{index}")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    args = parser.parse_args()

    manifest = analyze()
    manifest["command"] = args.command
    if args.command == "plan":
        manifest["decision"] = "v1593-pm-proxy-per-mgr-lifetime-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only host classifier; no device command or mutation"
        manifest["next_step"] = "run V1593 host-only classifier"

    leaks = check_forbidden_output(manifest)
    manifest["forbidden_output_hits"] = leaks
    if leaks:
        manifest["decision"] = "v1593-forbidden-output-hit"
        manifest["pass"] = False
        manifest["reason"] = "forbidden output string detected"
        manifest["next_step"] = "remove sensitive output before continuing"

    store = EvidenceStore(repo_path(args.out_dir))
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(args.report), summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(
        json.dumps(
            {
                "decision": manifest["decision"],
                "pass": manifest["pass"],
                "reason": manifest["reason"],
                "next_step": manifest["next_step"],
                "out_dir": str(store.run_dir),
                "report": rel(args.report),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
