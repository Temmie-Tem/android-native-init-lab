#!/usr/bin/env python3
"""V1928 clean-DSP plus V1927 libqmi CCI wait observer handoff."""

from __future__ import annotations

import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_wlfw_client_wait_integration_v1925 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1928"
OUT_DIR = repo_path("tmp/wifi/v1928-libqmi-cci-wait-integration")
HANDOFF_DIR = OUT_DIR / "v1927-handoff"
HANDOFF_REPORT = OUT_DIR / "v1927-handoff-report.md"
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1928_LIBQMI_CCI_WAIT_INTEGRATION_2026-06-04.md")
V1927_OUT = repo_path("tmp/wifi/v1927-libqmi-cci-uprobe-observer-test-boot")
V1927_INIT = V1927_OUT / "init_v1927_libqmi_cci_uprobe_observer"
V1927_BOOT = V1927_OUT / "boot_linux_v1927_libqmi_cci_uprobe_observer.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1927/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.174 (v1927-libqmi-cci-uprobe-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1927.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1927.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1927-helper.result"

WLFW_CLIENT_EVENTS = base.WLFW_CLIENT_EVENTS
LIBQMI_EVENTS = (
    "libqmi_client_init_instance_entry",
    "libqmi_initial_get_service_instance_ret",
    "libqmi_initial_client_init_ret",
    "libqmi_notifier_init_call",
    "libqmi_notifier_init_ret",
    "libqmi_wait_call",
    "libqmi_wait_return",
    "libqmi_loop_get_service_instance_ret",
    "libqmi_loop_client_init_ret",
    "libqmi_init_timeout_path",
    "libqmi_init_return",
    "libqmi_signal_wait_entry",
    "libqmi_signal_wait_timedwait",
    "libqmi_signal_wait_timeout_store",
    "libqmi_xport_new_server_entry",
    "libqmi_xport_new_server_signal",
)

ORIGINAL_COLLECT_DETAILS = base.collect_details


def libqmi_event(fields: dict[str, str], name: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.libqmi_uprobe.{name}."
    return {
        "name": name,
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "sample_count": fields.get(prefix + "sample_count", ""),
        "sample_line_0": fields.get(prefix + "sample_line_0", ""),
        "sample_line_1": fields.get(prefix + "sample_line_1", ""),
        "sample_line_2": fields.get(prefix + "sample_line_2", ""),
        "sample_line_3": fields.get(prefix + "sample_line_3", ""),
    }


def configure_handoff_globals() -> None:
    base.v1847.V1846_OUT = V1927_OUT
    base.v1847.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.v1847.DEFAULT_OUT_DIR = HANDOFF_DIR
    base.v1847.DEFAULT_REPORT_PATH = HANDOFF_REPORT
    base.v1847.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.v1847.TEST_LOG_PATH = TEST_LOG_PATH
    base.v1847.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.v1847.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.v1847.DMESG_PATTERN = (
        "A90v1927|A90v641|sibling fwssctl|wifi-v641-fwssctl|"
        "libqmi_|qmi-client-init|wlfw_client_init_instance|"
        "wlfw_get_service_instance|wlfw_get_instance_id|"
        "wlfw_send_ind_register_entry|wlfw_fw_mem_cond_wait|"
        + base.v1847.DMESG_PATTERN
    )


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
    )
    boot_required = (
        *init_required,
        "a90_android_execns_probe v361",
        "libqmi_client_init_instance_entry",
        "libqmi_wait_call",
        "libqmi_signal_wait_timedwait",
        "libqmi_xport_new_server_entry",
        "wlfw_client_init_instance_call",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1927_INIT, init_required), (V1927_BOOT, boot_required)):
        if not path.exists():
            checks[base.rel(path)] = {"exists": False, "ok": False, "missing": list(required)}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        checks[base.rel(path)] = {"exists": True, "ok": not missing, "missing": missing}
    return checks


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = base.v1847.runner().fwbase.parse_helper_fields(HANDOFF_DIR)
    libqmi_events = {name: libqmi_event(fields, name) for name in LIBQMI_EVENTS}
    wlfw_line = details["events"].get("wlfw_client_init_instance_call", {}).get("first_hit_line", "")
    wlfw_thread = event_thread(wlfw_line)
    wait_thread_hit = thread_event_hit(libqmi_events, "libqmi_wait_call", wlfw_thread)
    wait_return_thread_hit = thread_event_hit(libqmi_events, "libqmi_wait_return", wlfw_thread)
    init_return_thread_hit = thread_event_hit(libqmi_events, "libqmi_init_return", wlfw_thread)
    details["libqmi_label"] = fields.get("wlan_pd_cnss_nonlog_control_flow.libqmi_uprobe.label", "")
    details["libqmi_target"] = fields.get("wlan_pd_cnss_nonlog_control_flow.libqmi_uprobe.target.selected_path", "")
    details["libqmi_hit_count"] = fields.get("wlan_pd_cnss_nonlog_control_flow.libqmi_uprobe.hit_count", "")
    details["libqmi_events"] = libqmi_events
    details["libqmi_wlfw_thread"] = wlfw_thread
    details["libqmi_wlfw_wait_call_seen"] = wait_thread_hit
    details["libqmi_wlfw_wait_return_seen"] = wait_return_thread_hit
    details["libqmi_wlfw_init_return_seen"] = init_return_thread_hit
    details["libqmi_wlfw_wait_outstanding"] = wait_thread_hit and not wait_return_thread_hit and not init_return_thread_hit
    details["libqmi_other_init_return_seen"] = libqmi_hit(details, "libqmi_init_return") > 0 and not init_return_thread_hit
    return details


def libqmi_hit(details: dict[str, Any], name: str) -> int:
    return base.intish(details["libqmi_events"].get(name, {}).get("hit_count"))


def event_thread(line: str) -> str:
    match = re.search(r"\bcnss-daemon-(\d+)\b", line or "")
    return match.group(1) if match else ""


def event_sample_lines(data: dict[str, str]) -> list[str]:
    lines = [str(data.get("first_hit_line") or "")]
    for index in range(4):
        line = str(data.get(f"sample_line_{index}") or "")
        if line and line != "none" and line not in lines:
            lines.append(line)
    return [line for line in lines if line and line != "none"]


def thread_event_hit(events: dict[str, dict[str, str]], name: str, thread: str) -> bool:
    if not thread:
        return False
    return any(event_thread(line) == thread for line in event_sample_lines(events.get(name, {})))


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    rollback = handoff.get("post_rollback_verification") or {}
    hook_ok = all(item.get("ok") for item in hook.values())
    prearm_ok = any(step["name"] == "arm-clean-dsp-flag" and step["ok"] for step in steps)
    handoff_ok = bool(handoff.get("pass"))
    rollback_ok = bool(rollback.get("version_ok")) and bool(rollback.get("selftest_fail_zero"))
    combined = (
        details["service74"]
        and details["pm_open_subsys_modem"]
        and details["holder_opened"]
        and base.hit_from_details(details, "wlfw_service_request") > 0
    )
    publication_progress = details["wlfw69"] or details["wlan_pd"] or details["wlanmdsp"] or details["wlan0"]
    libqmi_label = str(details.get("libqmi_label") or "")
    if not hook_ok or not prearm_ok or not handoff_ok or not rollback_ok:
        label = "libqmi-wait-handoff-failed"
        reason = "artifact hook, clean-DSP prearm, V1927 handoff, or rollback verification failed"
        passed = False
    elif publication_progress or base.hit_from_details(details, "wlfw_ind_register_qmi") > 0 or base.hit_from_details(details, "wlfw_cap_qmi") > 0:
        label = "libqmi-wait-progress-stop"
        reason = "WLFW/QMI or lower WLAN-PD publication progressed; stop before HAL/scan/connect"
        passed = True
    elif not combined:
        label = "libqmi-wait-prereq-regression"
        reason = "combined service74 + PM-open + holder + WLFW worker prerequisites did not reproduce"
        passed = False
    elif details.get("libqmi_wlfw_wait_outstanding"):
        if libqmi_hit(details, "libqmi_xport_new_server_entry") > 0 and details.get("libqmi_other_init_return_seen"):
            label = "qmi-client-init-instance-wlfw-waiting-after-other-service-new-server"
            reason = "WLFW thread entered libqmi wait and stayed there; a new-server edge woke a different qmi_client_init_instance call, not WLFW"
        elif libqmi_hit(details, "libqmi_xport_new_server_entry") > 0:
            label = "qmi-client-init-instance-wlfw-waiting-after-new-server"
            reason = "WLFW thread stayed in libqmi wait despite a transport new-server edge"
        else:
            label = "qmi-client-init-instance-wlfw-waiting-no-new-server"
            reason = "WLFW thread stayed in libqmi wait and no libqmi new-server edge arrived"
        passed = True
    elif libqmi_label.startswith("qmi-client-init-instance-"):
        label = libqmi_label
        if label == "qmi-client-init-instance-waiting-no-new-server":
            reason = "WLFW worker is in libqmi service wait and libqmi saw no new-server wake edge while WLFW69/WLAN-PD stayed absent"
        elif label == "qmi-client-init-instance-new-server-no-wake":
            reason = "libqmi saw a new-server edge, but the qmi_client_init_instance wait loop did not wake/progress"
        elif label == "qmi-client-init-instance-timeout":
            reason = "libqmi qmi_client_init_instance reached its timeout return path"
        else:
            reason = f"libqmi observer refined the qmi_client_init_instance state: {label}"
        passed = True
    elif base.hit_from_details(details, "wlfw_client_init_instance_call") > 0 and base.hit_from_details(details, "wlfw_client_init_instance_retcheck") == 0:
        label = "wlfw-worker-blocked-in-qmi-client-init-instance-libqmi-incomplete"
        reason = "WLFW worker entered qmi_client_init_instance, but libqmi uprobes did not refine the wait state"
        passed = False
    else:
        label = "libqmi-wait-incomplete"
        reason = "new libqmi discriminator was incomplete"
        passed = False
    return {
        "label": label,
        "decision": f"v1928-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "prearm_ok": prearm_ok,
        "handoff_ok": handoff_ok,
        "rollback_ok": rollback_ok,
        "combined": combined,
        "publication_progress": publication_progress,
    }


def render_libqmi_rows(details: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in LIBQMI_EVENTS:
        data = details["libqmi_events"].get(name, {})
        rows.append([
            name,
            f"{data.get('registered')}/{data.get('enabled')}/{data.get('hit_count')}",
            data.get("first_hit_line", ""),
        ])
    return rows


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["combined", classification["combined"], f"service74={details['service74']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["publication", classification["publication_progress"], f"wlfw69={details['wlfw69']} wlan_pd={details['wlan_pd']} wlanmdsp={details['wlanmdsp']} wlan0={details['wlan0']}"],
        ["libqmi", details["libqmi_label"], f"target={details['libqmi_target']} hits={details['libqmi_hit_count']} wlfw_thread={details['libqmi_wlfw_thread']} wait_outstanding={details['libqmi_wlfw_wait_outstanding']}"],
        ["servnotif", details["servnotif_late_state"], f"indication={details['servnotif_late_indication']} qrtr69={details['qrtr69_case0_events']},{details['qrtr69_case1_events']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1928 Libqmi CCI Wait Integration",
        "",
        "## Summary",
        "",
        "- Cycle: `V1928`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## Libqmi Events",
        "",
        markdown_table(["event", "registered/enabled/hits", "first hit"], render_libqmi_rows(details)),
        "",
        "## WLFW Client Events",
        "",
        markdown_table(["event", "registered/enabled/hits", "first hit"], base.render_event_rows(details)),
        "",
        "## Route State",
        "",
        f"- PM open: `{details['open_context_path']}` fd `{details['open_context_fd']}`",
        f"- Holder fd: `{details['holder_fd']}`",
        f"- Labels: `{details['nonlog_label']}` / `{details['libqmi_label']}` / `{details['service_window_label']}` / `{details['service_object_label']}`",
        f"- Servloc: `{details['servloc_result']}` domain `{details['servloc_domain']}` instance `{details['servloc_instance']}`",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1927 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def write_result(store: EvidenceStore,
                 handoff: dict[str, Any],
                 hook: dict[str, Any],
                 steps: list[dict[str, Any]],
                 handoff_rc: int,
                 created: str | None = None) -> dict[str, Any]:
    details = collect_details(handoff)
    classification = classify(handoff, hook, steps, details)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": created or dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": base.rel(OUT_DIR),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "handoff_rc": handoff_rc,
        "handoff_manifest": base.rel(HANDOFF_DIR / "manifest.json"),
        "artifact_hook": hook,
        "classification": classification,
        "details": details,
        "steps": steps,
        "host_metadata": host_metadata,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    return manifest


def patch_base() -> None:
    base.CYCLE = CYCLE
    base.OUT_DIR = OUT_DIR
    base.HANDOFF_DIR = HANDOFF_DIR
    base.HANDOFF_REPORT = HANDOFF_REPORT
    base.REPORT_PATH = REPORT_PATH
    base.V1924_OUT = V1927_OUT
    base.V1924_INIT = V1927_INIT
    base.V1924_BOOT = V1927_BOOT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.artifact_hook_check = artifact_hook_check
    base.configure_handoff_globals = configure_handoff_globals
    base.collect_details = collect_details
    base.classify = classify
    base.render_report = render_report
    base.write_result = write_result


def main(argv: list[str] | None = None) -> int:
    patch_base()
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
