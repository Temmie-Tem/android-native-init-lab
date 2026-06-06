#!/usr/bin/env python3
"""V2067 rollbackable handoff for query-only WLAN-PD DIAG support."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_permgr_vote_focused_handoff_v2059 as prev2059


CYCLE = "V2067"
OUT_DIR = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2067-diag-pd-query-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2066-handoff"
HANDOFF_REPORT = OUT_DIR / "v2066-handoff-report.md"
REPORT_PATH = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2067_DIAG_PD_QUERY_HANDOFF_2026-06-04.md"
)
V2066_OUT = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2066-diag-pd-query-test-boot"
)
V2066_INIT = V2066_OUT / "init_v2066_diag_pd_query"
V2066_BOOT = V2066_OUT / "boot_linux_v2066_diag_pd_query.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2066/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.212 (v2066-diag-pd-query)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2066.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2066.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2066-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v397"


def rel(path: Path) -> str:
    return prev2059.rel(path)


def intish(value: object) -> int:
    return prev2059.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2059.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "DIAG_IOCTL_SWITCH_LOGGING",
        "diag_dci_canary_mask_probe.begin=1",
        "diag_dci_register_read_probe.mode=private-node-rdwr-nonblock-dci-reg-read",
        "passive_diag_sink.begin=1",
        "diag_pd_query_probe.switch_logging_attempted=1",
        "diag_pd_query_probe.write_attempted=1",
        "diag_pd_query_probe.log_mask_write=1",
        "diag_pd_query_probe.event_mask_write=1",
        "diag_pd_query_probe.stream_config_attempted=1",
        "diag_pd_query_probe.qmi_send=1",
        "diag_pd_query_probe.ptraced=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2066",
        "v2066-diag-pd-query",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "per_mgr_vote_focused.begin=1",
        "per_mgr_vote_focused.mode=cnss-pm-client-register-vote-uprobe-compact",
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "diag_pd_query_probe.begin=1",
        "diag_pd_query_probe.mode=private-node-query-pd-logging-wlan-only-no-switch-logging",
        "diag_pd_query_probe.ioctl=DIAG_IOCTL_QUERY_PD_LOGGING",
        "diag_pd_query_probe.pd_mask_name=DIAG_CON_UPD_WLAN",
        "diag_pd_query_probe.switch_logging_attempted=0",
        "diag_pd_query_probe.write_attempted=0",
        "diag_pd_query_probe.log_mask_write=0",
        "diag_pd_query_probe.event_mask_write=0",
        "diag_pd_query_probe.stream_config_attempted=0",
        "diag_pd_query_probe.qmi_send=0",
        "diag_pd_query_probe.ptraced=0",
        "diag_pd_query_probe.summary.query_supported=%d",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2066_INIT, init_required, init_forbidden),
        (V2066_BOOT, boot_required, boot_forbidden),
    ):
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        present_forbidden = [token for token in forbidden if token.encode() in data]
        checks[rel(path)] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not present_forbidden,
            "missing": missing,
            "forbidden": present_forbidden,
        }
    return checks


def collect_diag_pd_query(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_pd_query_probe"
    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "started": intish(fields.get(f"{prefix}.started")) or intish(fields.get(f"{prefix}.summary.started")),
        "rootfs_namespace_only": intish(fields.get(f"{prefix}.rootfs_namespace_only")) or intish(fields.get(f"{prefix}.summary.rootfs_namespace_only")),
        "sda29_write": intish(fields.get(f"{prefix}.sda29_write")) or intish(fields.get(f"{prefix}.summary.sda29_write")),
        "switch_logging_attempted": intish(fields.get(f"{prefix}.switch_logging_attempted")) or intish(fields.get(f"{prefix}.summary.switch_logging_attempted")),
        "write_attempted": intish(fields.get(f"{prefix}.write_attempted")) or intish(fields.get(f"{prefix}.summary.write_attempted")),
        "log_mask_write": intish(fields.get(f"{prefix}.log_mask_write")) or intish(fields.get(f"{prefix}.summary.log_mask_write")),
        "event_mask_write": intish(fields.get(f"{prefix}.event_mask_write")) or intish(fields.get(f"{prefix}.summary.event_mask_write")),
        "stream_config_attempted": intish(fields.get(f"{prefix}.stream_config_attempted")) or intish(fields.get(f"{prefix}.summary.stream_config_attempted")),
        "qmi_send": intish(fields.get(f"{prefix}.qmi_send")) or intish(fields.get(f"{prefix}.summary.qmi_send")),
        "ptraced": intish(fields.get(f"{prefix}.ptraced")) or intish(fields.get(f"{prefix}.summary.ptraced")),
        "ioctl": fields.get(f"{prefix}.ioctl", ""),
        "pd_mask": fields.get(f"{prefix}.pd_mask", ""),
        "node_created": intish(fields.get(f"{prefix}.summary.node_created")),
        "open_ok": intish(fields.get(f"{prefix}.summary.open_ok")),
        "attempts": intish(fields.get(f"{prefix}.summary.attempts")),
        "successes": intish(fields.get(f"{prefix}.summary.successes")),
        "failures": intish(fields.get(f"{prefix}.summary.failures")),
        "query_supported": intish(fields.get(f"{prefix}.summary.query_supported")),
        "first_success_attempt": intish(fields.get(f"{prefix}.summary.first_success_attempt")),
        "first_success_delta_ms": intish(fields.get(f"{prefix}.summary.first_success_delta_ms")),
        "last_success_delta_ms": intish(fields.get(f"{prefix}.summary.last_success_delta_ms")),
        "last_rc": intish(fields.get(f"{prefix}.summary.last_rc")),
        "last_errno": intish(fields.get(f"{prefix}.summary.last_errno")),
    }
    data["safe"] = (
        data["rootfs_namespace_only"] == 1
        and data["sda29_write"] == 0
        and data["switch_logging_attempted"] == 0
        and data["write_attempted"] == 0
        and data["log_mask_write"] == 0
        and data["event_mask_write"] == 0
        and data["stream_config_attempted"] == 0
        and data["qmi_send"] == 0
        and data["ptraced"] == 0
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2059.collect_details(handoff)
    fields = prev2059.prev2057.parse_fields()
    details["diag_pd_query"] = collect_diag_pd_query(fields)
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary", {}) if isinstance(logdw.get("summary"), dict) else {}
    wlanmdsp_tftp = intish(summary.get("wlanmdsp"))
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    cascade["wlanmdsp_tftp"] = wlanmdsp_tftp
    cascade["requested_wlanmdsp_raw_tftp"] = wlanmdsp_tftp > 0
    details["cascade"] = cascade
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2059.classify(handoff, hook, steps, details)
    pd = details.get("diag_pd_query") if isinstance(details.get("diag_pd_query"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    pd_started = intish(pd.get("begin")) == 1 and intish(pd.get("started")) == 1
    pd_safe = bool(pd.get("safe"))
    pd_open = intish(pd.get("open_ok")) == 1
    pd_supported = intish(pd.get("query_supported")) == 1
    route_ok = bool(base.get("route_ok")) and hook_ok and pd_started and pd_safe
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    wlanmdsp_seen = intish(cascade.get("wlanmdsp_tftp")) > 0
    wlan0_seen = bool(base.get("wlan0_seen"))

    if not hook_ok:
        label = "diag-pd-query-artifact-hook-regression"
        passed = False
        reason = "V2066 artifact does not contain the query-only WLAN-PD DIAG contract tokens"
    elif not pd_safe:
        label = "diag-pd-query-safety-regression"
        passed = False
        reason = "query-only PD DIAG markers were absent or indicated logging-mode, mask, stream, QMI, ptrace, or partition activity"
    elif not pd_started or not pd_open:
        label = "diag-pd-query-open-failed"
        passed = True
        reason = "private /dev/diag WLAN-PD query probe did not open; DIAG PD visibility cannot be classified until node materialization/open is fixed"
    elif pd_supported and wlanmdsp_seen and wlan0_seen:
        label = "diag-pd-query-wlan-supported-wlan0-up"
        passed = True
        reason = "query-only DIAG saw WLAN-PD logging support and the native route reached wlan0"
    elif pd_supported:
        label = "diag-pd-query-wlan-supported-no-wlanmdsp"
        passed = True
        reason = "query-only DIAG saw WLAN-PD logging support, but native still made no wlanmdsp request"
    else:
        label = "diag-pd-query-wlan-unseen-no-wlanmdsp"
        passed = True
        reason = "query-only DIAG never saw WLAN-PD logging support while native still made no wlanmdsp request"

    return {
        **base,
        "decision": f"v2067-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "pd_started": pd_started,
        "pd_safe": pd_safe,
        "pd_open": pd_open,
        "pd_supported": pd_supported,
        "route_ok": route_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    pm = details.get("per_mgr_vote_focused", {})
    pd = details.get("diag_pd_query", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2067 DIAG PD Query Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2067`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: V2059 remains the AP-side PerMgr answer; V2067 only checks whether query-only DIAG can see WLAN user-PD logging support after the native lower route reaches the post-PerMgr window.",
        "- Raw TFTP/logdw counters are authoritative for the image request branch; this run had `wlanmdsp=0`.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} pd_safe={classification.get('pd_safe')}"],
                ["per_mgr", classification.get("per_mgr_server_success"), f"client={classification.get('per_mgr_client_success')} server={classification.get('per_mgr_server_success')} label={pm.get('label', '')}"],
                ["diag_pd_query", classification.get("pd_supported"), f"open={classification.get('pd_open')} attempts={pd.get('attempts')} successes={pd.get('successes')} failures={pd.get('failures')} last_rc={pd.get('last_rc')} last_errno={pd.get('last_errno')}"],
                ["diag_pd_timing", "", f"first_success_attempt={pd.get('first_success_attempt')} first_delta_ms={pd.get('first_success_delta_ms')} last_delta_ms={pd.get('last_success_delta_ms')}"],
                ["tftp_branch", "", f"server_check={logdw.get('summary', {}).get('server_check')} ota={logdw.get('summary', {}).get('ota_firewall')} mcfg={logdw.get('summary', {}).get('mcfg')} wlanmdsp={logdw.get('summary', {}).get('wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## PD Query Detail",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["mode", pd.get("mode", "")],
                ["ioctl", pd.get("ioctl", "")],
                ["pd_mask", pd.get("pd_mask", "")],
                ["safe", pd.get("safe")],
                ["query_supported", pd.get("query_supported")],
                ["attempts", pd.get("attempts")],
                ["successes", pd.get("successes")],
                ["failures", pd.get("failures")],
                ["last_rc", pd.get("last_rc")],
                ["last_errno", pd.get("last_errno")],
            ],
        ),
        "",
        "## Branch",
        "",
        "- If `diag-pd-query-wlan-supported-no-wlanmdsp`, DIAG can resolve the WLAN user-PD; the next DIAG unit can choose a bounded WLAN/modem mask or explicit PD logging-mode escalation with a separate safety decision.",
        "- If `diag-pd-query-wlan-unseen-no-wlanmdsp`, query-only DIAG cannot see the WLAN user-PD despite the native `wlan_pd` state marker; do not expect mask-only DCI to reveal the modem producer without a heavier active logging-mode path.",
        "- If `diag-pd-query-wlan-supported-wlan0-up`, proceed to the normal no-HAL native `wlan0` bring-up and only then run scan/connect/ping.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG use was limited to a private rootfs `/dev/diag` char node and `DIAG_IOCTL_QUERY_PD_LOGGING` with `DIAG_CON_UPD_WLAN`.",
        "- No `DIAG_IOCTL_SWITCH_LOGGING`, DIAG write, broad log/event mask, DCI stream config, passive DIAG replay, QMI send, AP-side strace, boot-time QRTR matrix, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2066 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2059.prev2057.CYCLE = CYCLE
    prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2059.prev2057.V2056_OUT = V2066_OUT
    prev2059.prev2057.V2056_INIT = V2066_INIT
    prev2059.prev2057.V2056_BOOT = V2066_BOOT
    prev2059.prev2057.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2059.prev2057.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2059.prev2057.TEST_LOG_PATH = TEST_LOG_PATH
    prev2059.prev2057.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2059.prev2057.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2059.prev2057.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2059.prev2057.artifact_hook_check = artifact_hook_check
    prev2059.prev2057.collect_details = collect_details
    prev2059.prev2057.classify = classify
    prev2059.prev2057.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2057()
    return prev2059.prev2057.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
