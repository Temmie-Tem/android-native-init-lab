#!/usr/bin/env python3
"""V1937 clean-DSP/libqmi plus ICNSS IPC service69 observer handoff."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

import native_wifi_libqmi_service_id_integration_v1930 as parent
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1937"
OUT_DIR = repo_path("tmp/wifi/v1937-icnss-ipc-service69-integration")
HANDOFF_DIR = OUT_DIR / "v1936-handoff"
HANDOFF_REPORT = OUT_DIR / "v1936-handoff-report.md"
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1937_ICNSS_IPC_SERVICE69_INTEGRATION_2026-06-04.md")
V1936_OUT = repo_path("tmp/wifi/v1936-icnss-ipc-service69-observer-test-boot")
V1936_INIT = V1936_OUT / "init_v1936_icnss_ipc_service69_observer"
V1936_BOOT = V1936_OUT / "boot_linux_v1936_icnss_ipc_service69_observer.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1936/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.176 (v1936-icnss-ipc-service69-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1936.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1936.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1936-helper.result"

IPC_PHASES = (
    "after_holder_start",
    "after_early_listener",
    "after_post_listener_window",
)
IPC_ROOTS = (
    "debugfs_ipc_logging",
    "proc_ipc_logging",
)

ORIGINAL_COLLECT_DETAILS = parent.collect_details
ORIGINAL_CLASSIFY = parent.classify


def field_prefix(phase: str, root: str) -> str:
    return f"wlan_pd_icnss_ipc_snapshot.{phase}.{root}."


def intish(value: object) -> int:
    return parent.base.intish(value)


def bool_field(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "present"}


def a90ctl_hide_on_busy(command: list[str]) -> list[str]:
    return [
        sys.executable,
        "scripts/revalidation/a90ctl.py",
        "--timeout",
        "45",
        "--hide-on-busy",
        *command,
    ]


def shell_a90_hide_on_busy(script: str) -> list[str]:
    return a90ctl_hide_on_busy(["run", "/cache/bin/busybox", "sh", "-c", script])


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
    )
    boot_required = (
        *init_required,
        "a90_android_execns_probe v363",
        "wlan_pd_icnss_ipc_snapshot",
        "libqmi_get_service_list_lookup_call",
        "libqmi_client_init_instance_entry",
        "libqmi_wait_call",
        "libqmi_signal_wait_timedwait",
        "libqmi_xport_new_server_entry",
        "libqmi_xport_new_server_service",
        "libqmi_xport_new_server_callback_call",
        "wlfw_client_init_instance_call",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1936_INIT, init_required), (V1936_BOOT, boot_required)):
        if not path.exists():
            checks[parent.base.rel(path)] = {"exists": False, "ok": False, "missing": list(required)}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        checks[parent.base.rel(path)] = {"exists": True, "ok": not missing, "missing": missing}
    return checks


def configure_handoff_globals() -> None:
    parent.base.v1847.V1846_OUT = V1936_OUT
    parent.base.v1847.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    parent.base.v1847.DEFAULT_OUT_DIR = HANDOFF_DIR
    parent.base.v1847.DEFAULT_REPORT_PATH = HANDOFF_REPORT
    parent.base.v1847.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    parent.base.v1847.TEST_LOG_PATH = TEST_LOG_PATH
    parent.base.v1847.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    parent.base.v1847.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    parent.base.v1847.DMESG_PATTERN = (
        "A90v1936|A90v641|sibling fwssctl|wifi-v641-fwssctl|"
        "wlan_pd_icnss_ipc_snapshot|icnss|WLFW server arrive|"
        "PD notification registration|Get service notify|Get service location|"
        "libqmi_|qmi-client-init|wlfw_client_init_instance|"
        "wlfw_get_service_instance|wlfw_get_instance_id|"
        "wlfw_send_ind_register_entry|wlfw_fw_mem_cond_wait|"
        + parent.base.v1847.DMESG_PATTERN
    )


def parse_ipc_snapshots(fields: dict[str, str]) -> dict[str, Any]:
    roots: list[dict[str, Any]] = []
    stats: list[dict[str, Any]] = []
    for phase in IPC_PHASES:
        stats_prefix = f"wlan_pd_icnss_ipc_snapshot.{phase}.icnss_stats."
        stats.append({
            "phase": phase,
            "open": bool_field(fields.get(stats_prefix + "open")),
            "lines": intish(fields.get(stats_prefix + "lines")),
            "ind_register_text": bool_field(fields.get(stats_prefix + "ind_register_text")),
            "cap_text": bool_field(fields.get(stats_prefix + "cap_text")),
            "msa_ready_text": bool_field(fields.get(stats_prefix + "msa_ready_text")),
            "mode_text": bool_field(fields.get(stats_prefix + "mode_text")),
            "error": fields.get(stats_prefix + "error", ""),
        })
        for root in IPC_ROOTS:
            prefix = field_prefix(phase, root)
            roots.append({
                "phase": phase,
                "root": root,
                "root_exists": bool_field(fields.get(prefix + "root_exists")),
                "contexts": intish(fields.get(prefix + "contexts")),
                "readable_logs": intish(fields.get(prefix + "readable_logs")),
                "open_errors": intish(fields.get(prefix + "open_errors")),
                "lines": intish(fields.get(prefix + "lines")),
                "focus_lines": intish(fields.get(prefix + "focus_lines")),
                "get_service_location": bool_field(fields.get(prefix + "get_service_location")),
                "get_service_notify": bool_field(fields.get(prefix + "get_service_notify")),
                "wlan_pd_domain": bool_field(fields.get(prefix + "wlan_pd_domain")),
                "pd_notification_registration": bool_field(fields.get(prefix + "pd_notification_registration")),
                "wlfw_server_arrive": bool_field(fields.get(prefix + "wlfw_server_arrive")),
                "service69_text": bool_field(fields.get(prefix + "service69_text")),
                "first_source": fields.get(prefix + "first_source", ""),
                "first_focus_line": fields.get(prefix + "first_focus_line", ""),
            })
    return {
        "roots": roots,
        "stats": stats,
        "any_root_exists": any(item["root_exists"] for item in roots),
        "any_readable_log": any(item["readable_logs"] > 0 for item in roots),
        "any_focus_line": any(item["focus_lines"] > 0 for item in roots),
        "get_service_location_seen": any(item["get_service_location"] for item in roots),
        "get_service_notify_seen": any(item["get_service_notify"] for item in roots),
        "wlan_pd_domain_seen": any(item["wlan_pd_domain"] for item in roots),
        "pd_notification_registration_seen": any(item["pd_notification_registration"] for item in roots),
        "wlfw_server_arrive_seen": any(item["wlfw_server_arrive"] for item in roots),
        "service69_text_seen": any(item["service69_text"] for item in roots),
        "stats_open_seen": any(item["open"] for item in stats),
        "stats_lines_total": sum(int(item["lines"]) for item in stats),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = parent.base.v1847.runner().fwbase.parse_helper_fields(HANDOFF_DIR)
    details["icnss_ipc"] = parse_ipc_snapshots(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base_classification = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    if not base_classification.get("hook_ok") or not base_classification.get("prearm_ok"):
        return base_classification
    if not base_classification.get("handoff_ok") or not base_classification.get("rollback_ok"):
        return base_classification
    if base_classification.get("publication_progress"):
        return base_classification
    if not base_classification.get("combined"):
        return base_classification
    if not details.get("libqmi_wlfw_wait_outstanding"):
        return base_classification

    ipc = details.get("icnss_ipc") if isinstance(details.get("icnss_ipc"), dict) else {}
    if ipc.get("wlfw_server_arrive_seen"):
        label = "native-icnss-ipc-wlfw-arrive-no-libqmi-wake"
        reason = "native ICNSS IPC records WLFW server arrive, but the WLFW libqmi service69 wait still does not return"
    elif ipc.get("pd_notification_registration_seen") or ipc.get("wlan_pd_domain_seen"):
        label = "native-icnss-ipc-pd-registration-no-wlfw-arrive"
        reason = "native ICNSS IPC records wlan_pd domain/PD notification progress, but no WLFW server-arrive edge reaches libqmi service69"
    elif not ipc.get("any_readable_log") and not ipc.get("stats_open_seen"):
        label = "native-icnss-ipc-unreadable"
        reason = "rollbackable native test boot reproduced the libqmi service69 wait, but ICNSS IPC/debugfs surfaces were unreadable"
    else:
        label = "native-icnss-ipc-wlfw-server-arrive-gap"
        reason = "native reproduces service74/180, PM open, holder, WLFW lookup69, and libqmi wait, while ICNSS IPC/debugfs records no WLFW server-arrive edge"
    return {
        **base_classification,
        "label": label,
        "decision": f"v1937-{label}-rollback-pass",
        "pass": True,
        "reason": reason,
        "base_label": base_classification.get("label", ""),
    }


def render_ipc_rows(details: dict[str, Any]) -> list[list[str]]:
    ipc = details.get("icnss_ipc") if isinstance(details.get("icnss_ipc"), dict) else {}
    rows: list[list[str]] = []
    for item in ipc.get("roots", []):
        rows.append([
            f"{item['phase']}/{item['root']}",
            f"exists={item['root_exists']} readable={item['readable_logs']} lines={item['lines']} focus={item['focus_lines']}",
            f"notify={item['get_service_notify']} pd={item['wlan_pd_domain']} reg={item['pd_notification_registration']} arrive={item['wlfw_server_arrive']} svc69={item['service69_text']}",
            str(item.get("first_focus_line") or ""),
        ])
    for item in ipc.get("stats", []):
        rows.append([
            f"{item['phase']}/icnss_stats",
            f"open={item['open']} lines={item['lines']} error={item['error']}",
            f"ind={item['ind_register_text']} cap={item['cap_text']} msa_ready={item['msa_ready_text']} mode={item['mode_text']}",
            "",
        ])
    return rows


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    ipc = details["icnss_ipc"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["base_label", classification.get("base_label", details.get("libqmi_label", "")), f"libqmi={details['libqmi_label']}"],
        ["combined", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["publication", classification["publication_progress"], f"wlfw69={details['wlfw69']} wlan_pd={details['wlan_pd']} wlanmdsp={details['wlanmdsp']} wlan0={details['wlan0']}"],
        ["service69", details["libqmi_lookup_service69_seen"], f"wait_outstanding={details['libqmi_wlfw_wait_outstanding']} wait_return={details['libqmi_wlfw_wait_return_seen']} new_server69={details['libqmi_new_server_service69_seen']}"],
        ["icnss_ipc", ipc["any_readable_log"], f"notify={ipc['get_service_notify_seen']} pd={ipc['wlan_pd_domain_seen']} reg={ipc['pd_notification_registration_seen']} arrive={ipc['wlfw_server_arrive_seen']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1937 ICNSS IPC Service69 Integration",
        "",
        "## Summary",
        "",
        "- Cycle: `V1937`",
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
        "## ICNSS IPC / Debugfs",
        "",
        markdown_table(["source", "readability", "markers", "first focus"], render_ipc_rows(details)),
        "",
        "## Libqmi Events",
        "",
        markdown_table(["event", "registered/enabled/hits", "first hit"], parent.render_libqmi_rows(details)),
        "",
        "## WLFW Client Events",
        "",
        markdown_table(["event", "registered/enabled/hits", "first hit"], parent.base.render_event_rows(details)),
        "",
        "## Interpretation",
        "",
        "- Android-good V1917 records ICNSS IPC `PD notification registration happened` followed by `WLFW server arrive`; Android-good V1934 then returns the WLFW service69 wait.",
        "- This run keeps the internal-modem A1 route and classifies whether native reaches that ICNSS IPC edge before the known libqmi wait-return gap.",
        "- Stop remains before Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping unless WLFW service69 and `wlan0` are proven.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1936 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
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
        "out_dir": parent.base.rel(OUT_DIR),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "handoff_rc": handoff_rc,
        "handoff_manifest": parent.base.rel(HANDOFF_DIR / "manifest.json"),
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


def patch_parent() -> None:
    parent.CYCLE = CYCLE
    parent.OUT_DIR = OUT_DIR
    parent.HANDOFF_DIR = HANDOFF_DIR
    parent.HANDOFF_REPORT = HANDOFF_REPORT
    parent.REPORT_PATH = REPORT_PATH
    parent.V1929_OUT = V1936_OUT
    parent.V1929_INIT = V1936_INIT
    parent.V1929_BOOT = V1936_BOOT
    parent.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    parent.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    parent.TEST_LOG_PATH = TEST_LOG_PATH
    parent.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    parent.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    parent.artifact_hook_check = artifact_hook_check
    parent.configure_handoff_globals = configure_handoff_globals
    parent.collect_details = collect_details
    parent.classify = classify
    parent.render_report = render_report
    parent.write_result = write_result
    parent.base.a90ctl = a90ctl_hide_on_busy
    parent.base.shell_a90 = shell_a90_hide_on_busy


def main(argv: list[str] | None = None) -> int:
    patch_parent()
    return parent.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
