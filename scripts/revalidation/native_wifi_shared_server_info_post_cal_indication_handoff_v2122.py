#!/usr/bin/env python3
"""V2122 rollbackable handoff for the shared-server-info post-cal indication edge."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_shared_server_info_handoff_v2121 as prev2121


CYCLE = "V2122"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2122-shared-server-info-post-cal-indication-handoff"
HANDOFF_DIR = OUT_DIR / "v2120-handoff"
HANDOFF_REPORT = OUT_DIR / "v2120-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2122_SHARED_SERVER_INFO_POST_CAL_INDICATION_HANDOFF_2026-06-05.md"
)
V2120_OUT = prev2121.V2120_OUT
V2120_INIT = prev2121.V2120_INIT
V2120_BOOT = prev2121.V2120_BOOT
REMOTE_PROPERTY_ROOT = prev2121.REMOTE_PROPERTY_ROOT
TEST_EXPECT_VERSION = prev2121.TEST_EXPECT_VERSION
TEST_LOG_PATH = prev2121.TEST_LOG_PATH
TEST_SUMMARY_PATH = prev2121.TEST_SUMMARY_PATH
TEST_HELPER_RESULT_PATH = prev2121.TEST_HELPER_RESULT_PATH
EXPECTED_HELPER_VERSION = prev2121.EXPECTED_HELPER_VERSION

prev2113 = prev2121.prev2113


def rel(path: Path) -> str:
    return prev2121.rel(path)


def intish(value: object) -> int:
    return prev2121.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2121.markdown_table(headers, rows)


def read_helper_text() -> str:
    parts: list[str] = []
    for path in (
        HANDOFF_DIR / "test-v1393-helper-result.stdout.txt",
        HANDOFF_DIR / "test-v1393-helper-result.stderr.txt",
        HANDOFF_DIR / "test-v1393-log.stdout.txt",
        HANDOFF_DIR / "test-v1393-summary.stdout.txt",
    ):
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line or line.startswith("A90_EXECNS_PATH_"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def focused_int(fields: dict[str, str], suffix: str) -> int:
    return intish(fields.get(f"wlfw_late_msg21_focused.{suffix}", ""))


def collect_focused_indication(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlfw_late_msg21_focused."
    samples = [
        fields.get(prefix + "qmi_cb.sample_0", ""),
        fields.get(prefix + "qmi_cb.sample_1", ""),
        fields.get(prefix + "qmi_cb.sample_2", ""),
        fields.get(prefix + "qmi_cb.sample_3", ""),
    ]
    return {
        "begin": focused_int(fields, "begin"),
        "mode": fields.get(prefix + "mode", ""),
        "qmi_cb_hit_count": focused_int(fields, "qmi_cb.hit_count"),
        "qmi_cb_sample_count": focused_int(fields, "qmi_cb.sample_count"),
        "saw_msg21": focused_int(fields, "qmi_cb.saw_msg21"),
        "saw_msg2b": focused_int(fields, "qmi_cb.saw_msg2b"),
        "first": fields.get(prefix + "qmi_cb.first", ""),
        "samples": samples,
        "queue_link_hit_count": focused_int(fields, "queue_link.hit_count"),
        "cond_signal_hit_count": focused_int(fields, "cond_signal.hit_count"),
        "fw_mem_flag_hit_count": focused_int(fields, "fw_mem_flag.hit_count"),
        "msa_flag_hit_count": focused_int(fields, "msa_flag.hit_count"),
        "handle_ind_hit_count": focused_int(fields, "handle_ind.hit_count"),
        "wlan_status_hit_count": focused_int(fields, "wlan_status.hit_count"),
        "wlan_version_hit_count": focused_int(fields, "wlan_version.hit_count"),
        "cal_return_hit_count": focused_int(fields, "cal_return.hit_count"),
    }


def post_cal_value(details: dict[str, Any], key: str) -> str:
    return prev2121.post_cal_value(details, key)


def post_cal_hit(details: dict[str, Any], group: str, event: str) -> int:
    return prev2121.post_cal_hit(details, group, event)


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, item in events.items():
        hit_count = str(item.get("hit_count", ""))
        fetch_args = str(item.get("fetch_args", ""))
        first_hit = str(item.get("first_hit_line", ""))
        if not hit_count and not fetch_args and not first_hit:
            continue
        rows.append([
            name,
            hit_count,
            fetch_args,
            first_hit[:180],
        ])
    return rows


def focused_rows(focused: dict[str, Any]) -> list[list[object]]:
    return [
        ["qmi_cb", focused.get("qmi_cb_hit_count"), focused.get("first", "")],
        ["samples", focused.get("qmi_cb_sample_count"), " | ".join(str(item) for item in focused.get("samples", []) if item and item != "none")],
        ["msg21", focused.get("saw_msg21"), "late QMI callback observed"],
        ["msg2b", focused.get("saw_msg2b"), "FW-mem QMI callback observed"],
        ["fw_mem_flag", focused.get("fw_mem_flag_hit_count"), "sets FW-memory wait edge"],
        ["msa_flag", focused.get("msa_flag_hit_count"), "expected before FW-ready/status cascade"],
        ["queue_link", focused.get("queue_link_hit_count"), "decoded indication queue edge"],
        ["cond_signal", focused.get("cond_signal_hit_count"), "callback condition signal"],
        ["handle_ind", focused.get("handle_ind_hit_count"), "worker indication handler"],
        ["wlan_status", focused.get("wlan_status_hit_count"), "WLAN status send path"],
        ["wlan_version", focused.get("wlan_version_hit_count"), "WLAN version send path"],
    ]


def cap_bdf_cal_success(details: dict[str, Any]) -> bool:
    return (
        post_cal_hit(details, "cap_events", "wlfw_cap_success_branch") > 0
        and post_cal_value(details, "cap_return_rc") == "0x0"
        and post_cal_hit(details, "bdf_events", "wlfw_bdf_return") > 0
        and post_cal_value(details, "bdf_return_rc") == "0x0"
        and post_cal_value(details, "bdf_qmi_result") == "0x0"
        and post_cal_hit(details, "tail_events", "wlfw_cal_report_return") > 0
        and post_cal_value(details, "cal_return_rc") == "0x0"
    )


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2121.collect_details(handoff)
    fields = parse_fields(read_helper_text())
    details["wlfw_late_msg21_focused"] = collect_focused_indication(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2121.classify(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused") if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    wlan0 = intish(cascade.get("wlan0")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    status_hits = intish(focused.get("wlan_status_hit_count"))
    version_hits = intish(focused.get("wlan_version_hit_count"))
    qmi_hits = intish(focused.get("qmi_cb_hit_count"))
    fw_mem_hits = intish(focused.get("fw_mem_flag_hit_count"))
    msa_hits = intish(focused.get("msa_flag_hit_count"))
    queue_hits = intish(focused.get("queue_link_hit_count"))
    handle_hits = intish(focused.get("handle_ind_hit_count"))
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("shared_server_info_bridge_ok"))
        and intish(base.get("server_info_startup_error_count")) == 0
        and intish(cascade.get("wlan_pd_up")) > 0
        and intish(cascade.get("icnss_qmi_connected")) > 0
        and cap_bdf_cal_success(details)
        and all(bool(step.get("ok")) for step in steps)
    )

    if not route_ok:
        label = "shared-post-cal-indication-route-regression"
        passed = False
        reason = "V2122 did not preserve shared-server-info, wlan_pd UP, ICNSS QMI, cap/BDF/cal, or rollback prerequisites"
    elif wlan0:
        label = "shared-post-cal-indication-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "shared-post-cal-indication-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif status_hits > 0 or version_hits > 0:
        label = "shared-post-cal-indication-status-version-no-fw-ready"
        passed = True
        reason = "post-cal status/version path ran but did not produce FW_READY/wlan0"
    elif qmi_hits == 0:
        label = "shared-post-cal-indication-none-from-wlfw"
        passed = True
        reason = "cap/BDF/cal succeeded, but cnss-daemon received no WLFW QMI indication from the WLAN PD"
    elif fw_mem_hits > 0 and msa_hits == 0 and queue_hits == 0 and handle_hits == 0:
        label = "shared-post-cal-fw-mem-only-callback-not-queued"
        passed = True
        reason = "WLFW callback delivered the FW-memory edge, but no MSA/FW-ready indication was decoded, queued, handled, or sent as WLAN status/version"
    elif queue_hits == 0:
        label = "shared-post-cal-indication-callback-not-queued"
        passed = True
        reason = "WLFW QMI callback ran, but no decoded indication was queued for the worker"
    elif handle_hits == 0:
        label = "shared-post-cal-indication-queued-not-drained"
        passed = True
        reason = "WLFW indication was queued, but the worker did not drain it"
    else:
        label = "shared-post-cal-indication-handled-no-fw-ready"
        passed = True
        reason = "WLFW indication was delivered and handled, but FW_READY/wlan0 still did not appear"

    return {
        **base,
        "decision": f"v2122-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "cap_bdf_cal_success": cap_bdf_cal_success(details),
        "focused_qmi_hits": qmi_hits,
        "focused_fw_mem_hits": fw_mem_hits,
        "focused_msa_hits": msa_hits,
        "focused_queue_hits": queue_hits,
        "focused_handle_hits": handle_hits,
        "focused_status_hits": status_hits,
        "focused_version_hits": version_hits,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    shared = details.get("shared_server_info_bridge", {}) if isinstance(details.get("shared_server_info_bridge"), dict) else {}
    post = details.get("post_cal_indication", {}) if isinstance(details.get("post_cal_indication"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused", {}) if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    tail = post.get("tail_events", {}) if isinstance(post.get("tail_events"), dict) else {}
    ind = post.get("ind_events", {}) if isinstance(post.get("ind_events"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2122 Shared Server Info Post-Cal Indication Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2122`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["artifact", classification.get("hook_ok"), f"helper={EXPECTED_HELPER_VERSION}"],
                ["shared_server_info", classification.get("shared_server_info_bridge_ok"), f"mode={shared.get('mode')} uid_gid={shared.get('uid')}:{shared.get('gid')} errno={shared.get('stat_errno')}"],
                ["tftp_branch", "", f"server_check={branch.get('server_check')} ota={classification.get('ota_seen')} wlanmdsp={classification.get('wlanmdsp_seen')}"],
                ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post.get('cap_return_rc')} bdf={post.get('bdf_return_rc')} bdf_qmi={post.get('bdf_qmi_result')} cal={post.get('cal_return_rc')}"],
                ["focused_ind", "", f"qmi={classification.get('focused_qmi_hits')} fw_mem={classification.get('focused_fw_mem_hits')} msa={classification.get('focused_msa_hits')} queue={classification.get('focused_queue_hits')} handle={classification.get('focused_handle_hits')}"],
                ["status_version", "", f"status={classification.get('focused_status_hits')} version={classification.get('focused_version_hits')} dms_addr_qmi={post.get('dms_addr_qmi_result')} dms_addr_rc={post.get('dms_addr_return_rc')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Focused Indication",
        "",
        markdown_table(["edge", "hits", "detail"], focused_rows(focused)),
        "",
        "## Tail Events",
        "",
        markdown_table(["event", "hits", "fetch", "first"], event_rows(tail)),
        "",
        "## Indication Events",
        "",
        markdown_table(["event", "hits", "fetch", "first"], event_rows(ind)),
        "",
        "## Interpretation",
        "",
        "- V2122 keeps the V2120 dual-RFS read-only/read-write/shared bridges and only re-runs the light post-cal observer.",
        "- The discriminator is after `wlfw_cal_report_return rc=0x0`: WLFW QMI callback, decode/queue, worker handle, status/version, FW_READY, and `wlan0`.",
        "- A FW-memory-only callback with no MSA/FW-ready queue/handler keeps the blocker at the WLAN-PD-to-cnss FW-ready indication edge, not at RFS `server_info`, BDF, or cal-report.",
        "- The focused indication table is authoritative for this edge; full per-uprobe rows can be omitted when helper stdout reaches its capture cap.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2120 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local shared `server_info.txt` tmpfs, namespace-local persist-RFS leaf precreate in the private rootfs, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2113() -> None:
    prev2113.CYCLE = CYCLE
    prev2113.OUT_DIR = OUT_DIR
    prev2113.HANDOFF_DIR = HANDOFF_DIR
    prev2113.HANDOFF_REPORT = HANDOFF_REPORT
    prev2113.REPORT_PATH = REPORT_PATH
    prev2113.V2112_OUT = V2120_OUT
    prev2113.V2112_INIT = V2120_INIT
    prev2113.V2112_BOOT = V2120_BOOT
    prev2113.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2113.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2113.TEST_LOG_PATH = TEST_LOG_PATH
    prev2113.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2113.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2113.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2113.BRIDGE_CAPTURE = OUT_DIR / "host" / "v2122-autostart-bridge.log"
    prev2113.BRIDGE_STDOUT = OUT_DIR / "host" / "v2122-autostart-bridge.stdout.txt"
    prev2113.BRIDGE_STDERR = OUT_DIR / "host" / "v2122-autostart-bridge.stderr.txt"
    prev2113.BRIDGE_PID = OUT_DIR / "host" / "v2122-autostart-bridge.pid"
    prev2113.artifact_hook_check = prev2121.artifact_hook_check
    prev2113.collect_details = collect_details
    prev2113.classify = classify
    prev2113.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2113()
    return prev2113.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
