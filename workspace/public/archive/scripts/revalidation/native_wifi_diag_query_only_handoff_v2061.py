#!/usr/bin/env python3
"""V2061 rollbackable handoff for query-only DIAG DCI-support feasibility."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_permgr_vote_focused_handoff_v2059 as prev2059


CYCLE = "V2061"
OUT_DIR = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2061-diag-query-only-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2060-handoff"
HANDOFF_REPORT = OUT_DIR / "v2060-handoff-report.md"
REPORT_PATH = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2061_DIAG_QUERY_ONLY_HANDOFF_2026-06-04.md"
)
V2060_OUT = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2060-diag-query-only-test-boot"
)
V2060_INIT = V2060_OUT / "init_v2060_diag_query_only"
V2060_BOOT = V2060_OUT / "boot_linux_v2060_diag_query_only.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2060/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.209 (v2060-diag-query-only)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2060.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2060.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2060-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v394"


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
        "diag_query_only_probe.switch_logging_attempted=1",
        "diag_query_only_probe.write_attempted=1",
        "diag_query_only_probe.log_mask_write=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2060",
        "v2060-diag-query-only",
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
        "diag_query_only_probe.begin=1",
        "diag_query_only_probe.mode=private-node-rdwr-nonblock-dci-support-query-only",
        "diag_query_only_probe.switch_logging_attempted=0",
        "diag_query_only_probe.write_attempted=0",
        "diag_query_only_probe.log_mask_write=0",
        "diag_query_only_probe.event_mask_write=0",
        "diag_query_only_probe.dci_support.proc_%d.rc=%d",
        "diag_query_only_probe.summary.ioctl_attempts=%u",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2060_INIT, init_required, init_forbidden),
        (V2060_BOOT, boot_required, boot_forbidden),
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


def collect_diag_query(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_query_only_probe"
    procs: list[dict[str, Any]] = []
    derived_query_count = 0
    derived_success_count = 0
    derived_failure_count = 0
    derived_nonzero_count = 0
    derived_first_success_proc = -1
    derived_first_success_mask = ""
    success_rcs = {0, 1001}
    for proc in range(8):
        rc_field = fields.get(f"{prefix}.dci_support.proc_{proc}.rc")
        mask_field = fields.get(f"{prefix}.dci_support.proc_{proc}.support_mask", "")
        rc = intish(rc_field)
        support_mask_int = intish(mask_field)
        successful = rc in success_rcs
        nonzero = successful and support_mask_int != 0
        if rc_field is not None:
            derived_query_count += 1
            if successful:
                derived_success_count += 1
            else:
                derived_failure_count += 1
            if nonzero:
                derived_nonzero_count += 1
                if derived_first_success_proc < 0:
                    derived_first_success_proc = proc
                    derived_first_success_mask = mask_field
        procs.append({
            "proc": proc,
            "rc": rc,
            "errno": intish(fields.get(f"{prefix}.dci_support.proc_{proc}.errno")),
            "support_mask": mask_field,
            "support_nonzero": 1 if nonzero else 0,
        })
    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "sysfs_dev": fields.get(f"{prefix}.sysfs_dev", ""),
        "major": intish(fields.get(f"{prefix}.major")),
        "minor": intish(fields.get(f"{prefix}.minor")),
        "started": intish(fields.get(f"{prefix}.started")),
        "summary_started": intish(fields.get(f"{prefix}.summary.started")),
        "node_created": intish(fields.get(f"{prefix}.summary.node_created")) or intish(fields.get(f"{prefix}.started")),
        "open_ok": intish(fields.get(f"{prefix}.summary.open_ok")) or intish(fields.get(f"{prefix}.started")),
        "ioctl_attempts": intish(fields.get(f"{prefix}.summary.ioctl_attempts")) or derived_query_count,
        "ioctl_successes": intish(fields.get(f"{prefix}.summary.ioctl_successes")) or derived_success_count,
        "ioctl_failures": intish(fields.get(f"{prefix}.summary.ioctl_failures")) or derived_failure_count,
        "query_count": intish(fields.get(f"{prefix}.summary.query_count")) or derived_query_count,
        "support_nonzero_count": intish(fields.get(f"{prefix}.summary.support_nonzero_count")) or derived_nonzero_count,
        "first_success_proc": intish(fields.get(f"{prefix}.summary.first_success_proc")) if fields.get(f"{prefix}.summary.first_success_proc") is not None else derived_first_success_proc,
        "first_success_mask": fields.get(f"{prefix}.summary.first_success_mask", "") or derived_first_success_mask,
        "last_errno": intish(fields.get(f"{prefix}.summary.last_errno")),
        "safe": (
            intish(fields.get(f"{prefix}.rootfs_namespace_only")) == 1
            and intish(fields.get(f"{prefix}.sda29_write")) == 0
            and intish(fields.get(f"{prefix}.switch_logging_attempted")) == 0
            and intish(fields.get(f"{prefix}.write_attempted")) == 0
            and intish(fields.get(f"{prefix}.log_mask_write")) == 0
            and intish(fields.get(f"{prefix}.event_mask_write")) == 0
            and intish(fields.get(f"{prefix}.qmi_send")) == 0
            and intish(fields.get(f"{prefix}.ptraced")) == 0
        ),
    }
    data["procs"] = procs
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2059.collect_details(handoff)
    fields = prev2059.prev2057.parse_fields()
    details["diag_query_only"] = collect_diag_query(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2059.classify(handoff, hook, steps, details)
    diag = details.get("diag_query_only") if isinstance(details.get("diag_query_only"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    diag_started = intish(diag.get("begin")) == 1 and intish(diag.get("started")) == 1
    diag_safe = bool(diag.get("safe"))
    diag_open = intish(diag.get("open_ok")) == 1
    diag_queried = intish(diag.get("query_count")) > 0 and intish(diag.get("ioctl_attempts")) > 0
    dci_supported = intish(diag.get("support_nonzero_count")) > 0
    base_label = str(base.get("label", ""))

    if not hook_ok:
        label = "diag-query-artifact-hook-regression"
        passed = False
        reason = "V2060 artifact does not contain the query-only DIAG contract tokens"
    elif not diag_safe:
        label = "diag-query-safety-marker-regression"
        passed = False
        reason = "query-only DIAG safety markers were absent or indicated forbidden write/logging-mode activity"
    elif not diag_started or not diag_open:
        label = "diag-query-private-node-open-failed"
        passed = True
        reason = "private /dev/diag query-only probe did not open; active DIAG cannot proceed until diag node materialization/open is fixed"
    elif not diag_queried:
        label = "diag-query-not-executed"
        passed = False
        reason = "private /dev/diag opened but DCI-support queries did not execute"
    elif dci_supported and base_label == "cnss-permgr-register-vote-success-no-wlanmdsp":
        label = "diag-dci-support-present-no-wlanmdsp"
        passed = True
        reason = "query-only DIAG reached DCI support successfully while PerMgr still succeeded and native still made no wlanmdsp request"
    elif dci_supported:
        label = "diag-dci-support-present-route-changed"
        passed = True
        reason = "query-only DIAG reached DCI support but the lower Wi-Fi route changed relative to V2059"
    else:
        label = "diag-dci-support-query-no-supported-proc"
        passed = True
        reason = "query-only DIAG opened and queried DCI support, but no queried proc reported a nonzero support mask"

    return {
        **base,
        "decision": f"v2061-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "diag_started": diag_started,
        "diag_safe": diag_safe,
        "diag_open": diag_open,
        "diag_queried": diag_queried,
        "diag_dci_supported": dci_supported,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    pm = details.get("per_mgr_vote_focused", {})
    diag = details.get("diag_query_only", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    procs = diag.get("procs", []) if isinstance(diag.get("procs"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2061 DIAG Query-Only Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2061`",
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
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} diag_safe={classification.get('diag_safe')}"],
                ["cnss_permgr", classification.get("per_mgr_server_success"), f"client={classification.get('per_mgr_client_success')} peripheral={classification.get('per_mgr_peripheral_success')} server={classification.get('per_mgr_server_success')}"] ,
                ["diag_query", classification.get("diag_queried"), f"open={classification.get('diag_open')} attempts={diag.get('ioctl_attempts')} success={diag.get('ioctl_successes')} failures={diag.get('ioctl_failures')}"] ,
                ["diag_dci", classification.get("diag_dci_supported"), f"support_nonzero={diag.get('support_nonzero_count')} first_proc={diag.get('first_success_proc')} first_mask={diag.get('first_success_mask')}"] ,
                ["tftp_branch", "", f"server_check={logdw.get('summary', {}).get('server_check')} ota={logdw.get('summary', {}).get('ota_firewall')} mcfg={logdw.get('summary', {}).get('mcfg')} wlanmdsp={logdw.get('summary', {}).get('wlanmdsp')}"] ,
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## DIAG Query Detail",
        "",
        markdown_table(
            ["proc", "rc", "errno", "support_mask", "nonzero"],
            [[item.get("proc"), item.get("rc"), item.get("errno"), item.get("support_mask"), item.get("support_nonzero")] for item in procs] or [["none", "", "", "", ""]],
        ),
        "",
        "## PerMgr Anchor",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["focused_label", pm.get("label", "")],
                ["cnss_register_ret", pm.get("cnss_register_ret_line", "")],
                ["cnss_connect_ret", pm.get("cnss_connect_ret_line", "")],
                ["pm_service", f"entry={pm.get('pm_server_register_entry_hit_count')} match={pm.get('pm_server_register_match_hit_count')} add_client={pm.get('pm_server_register_add_client_call_hit_count')} success={pm.get('pm_server_register_success_return_hit_count')}"] ,
            ],
        ),
        "",
        "## Branch",
        "",
        "- If `diag-dci-support-present-no-wlanmdsp`, a bounded active DIAG DCI/log/event-mask capture is technically reachable and is the next modem-internal visibility path; query-only evidence still cannot show modem payloads by itself.",
        "- If `diag-dci-support-query-no-supported-proc`, the next live DIAG route likely needs the heavier logging-mode/mask path rather than DCI support.",
        "- Keep the V2059 AP-side conclusion intact when PerMgr remains successful and TFTP `wlanmdsp=0`: cnss PerMgr register/vote is not the missing WLAN image-request trigger.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG use was limited to a private rootfs `/dev/diag` char node plus `DIAG_IOCTL_DCI_SUPPORT` queries. No `DIAG_IOCTL_SWITCH_LOGGING`, DIAG write, log/event mask write, DCI stream config, passive DIAG replay, QMI send, AP-side strace, boot-time QRTR matrix, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2060 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2059.prev2057.CYCLE = CYCLE
    prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2059.prev2057.V2056_OUT = V2060_OUT
    prev2059.prev2057.V2056_INIT = V2060_INIT
    prev2059.prev2057.V2056_BOOT = V2060_BOOT
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
