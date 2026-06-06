#!/usr/bin/env python3
"""V2063 rollbackable handoff for DIAG DCI register-read visibility."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_permgr_vote_focused_handoff_v2059 as prev2059


CYCLE = "V2063"
OUT_DIR = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2063-dci-register-read-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2062-handoff"
HANDOFF_REPORT = OUT_DIR / "v2062-handoff-report.md"
REPORT_PATH = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2063_DCI_REGISTER_READ_HANDOFF_2026-06-04.md"
)
V2062_OUT = prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2062-dci-register-read-test-boot"
)
V2062_INIT = V2062_OUT / "init_v2062_dci_register_read"
V2062_BOOT = V2062_OUT / "boot_linux_v2062_dci_register_read.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2062/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.210 (v2062-dci-register-read)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2062.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2062.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2062-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v395"


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
        "diag_dci_register_read_probe.switch_logging_attempted=1",
        "diag_dci_register_read_probe.write_attempted=1",
        "diag_dci_register_read_probe.stream_config_attempted=1",
        "diag_dci_register_read_probe.log_mask_write=1",
        "diag_dci_register_read_probe.event_mask_write=1",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2062",
        "v2062-dci-register-read",
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
        "diag_dci_register_read_probe.begin=1",
        "diag_dci_register_read_probe.mode=private-node-rdwr-nonblock-dci-reg-read-no-stream-no-mask-no-write",
        "diag_dci_register_read_probe.switch_logging_attempted=0",
        "diag_dci_register_read_probe.write_attempted=0",
        "diag_dci_register_read_probe.stream_config_attempted=0",
        "diag_dci_register_read_probe.log_mask_write=0",
        "diag_dci_register_read_probe.event_mask_write=0",
        "diag_dci_register_read_probe.dci_support.proc_%d.rc=%d",
        "diag_dci_register_read_probe.register_rc=%d",
        "diag_dci_register_read_probe.summary.read_records=%u",
        "diag_dci_register_read_probe.summary.deinit_attempted=%d",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2062_INIT, init_required, init_forbidden),
        (V2062_BOOT, boot_required, boot_forbidden),
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


def collect_diag_dci_register_read(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "diag_dci_register_read_probe"
    procs: list[dict[str, Any]] = []
    derived_query_count = 0
    derived_nonzero_count = 0
    derived_first_proc = -1
    derived_first_mask = ""
    success_rcs = {0, 1001}
    for proc in range(8):
        rc_field = fields.get(f"{prefix}.dci_support.proc_{proc}.rc")
        mask_field = fields.get(f"{prefix}.dci_support.proc_{proc}.support_mask", "")
        rc = intish(rc_field)
        support_mask = intish(mask_field)
        nonzero = rc in success_rcs and support_mask != 0
        if rc_field is not None:
            derived_query_count += 1
            if nonzero:
                derived_nonzero_count += 1
                if derived_first_proc < 0:
                    derived_first_proc = proc
                    derived_first_mask = mask_field
        procs.append({
            "proc": proc,
            "rc": rc,
            "errno": intish(fields.get(f"{prefix}.dci_support.proc_{proc}.errno")),
            "support_mask": mask_field,
            "support_nonzero": 1 if nonzero else 0,
        })
    read_records = intish(fields.get(f"{prefix}.summary.read_records"))
    dci_data = intish(fields.get(f"{prefix}.summary.dci_data_records"))
    dci_pkt = intish(fields.get(f"{prefix}.summary.dci_pkt_records"))
    user_space = intish(fields.get(f"{prefix}.summary.user_space_records"))
    other = intish(fields.get(f"{prefix}.summary.other_records"))
    samples = []
    for sample_index in range(16):
        key = f"{prefix}.sample_{sample_index:02d}.bytes"
        if key not in fields:
            continue
        samples.append({
            "index": sample_index,
            "bytes": intish(fields.get(key)),
            "data_type": fields.get(f"{prefix}.sample_{sample_index:02d}.data_type", ""),
            "data_type_name": fields.get(f"{prefix}.sample_{sample_index:02d}.data_type_name", ""),
            "prefix_hex": fields.get(f"{prefix}.sample_{sample_index:02d}.prefix_hex", ""),
        })
    data: dict[str, Any] = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "sysfs_dev": fields.get(f"{prefix}.sysfs_dev", ""),
        "major": intish(fields.get(f"{prefix}.major")),
        "minor": intish(fields.get(f"{prefix}.minor")),
        "started": intish(fields.get(f"{prefix}.started")),
        "open_ok": intish(fields.get(f"{prefix}.summary.open_ok")) or intish(fields.get(f"{prefix}.started")),
        "query_count": intish(fields.get(f"{prefix}.summary.query_count")) or derived_query_count,
        "support_nonzero_count": intish(fields.get(f"{prefix}.summary.support_nonzero_count")) or derived_nonzero_count,
        "selected_proc": intish(fields.get(f"{prefix}.summary.selected_proc")) if fields.get(f"{prefix}.summary.selected_proc") is not None else derived_first_proc,
        "selected_mask": fields.get(f"{prefix}.summary.selected_mask", "") or derived_first_mask,
        "register_attempted": intish(fields.get(f"{prefix}.summary.register_attempted")) or intish(fields.get(f"{prefix}.register_attempted")),
        "registered": intish(fields.get(f"{prefix}.summary.registered")) or intish(fields.get(f"{prefix}.registered")),
        "register_rc": intish(fields.get(f"{prefix}.summary.register_rc")) if fields.get(f"{prefix}.summary.register_rc") is not None else intish(fields.get(f"{prefix}.register_rc")),
        "register_errno": intish(fields.get(f"{prefix}.summary.register_errno")) if fields.get(f"{prefix}.summary.register_errno") is not None else intish(fields.get(f"{prefix}.register_errno")),
        "client_id": intish(fields.get(f"{prefix}.summary.client_id")) if fields.get(f"{prefix}.summary.client_id") is not None else intish(fields.get(f"{prefix}.client_id")),
        "read_calls": intish(fields.get(f"{prefix}.summary.read_calls")),
        "read_records": read_records,
        "read_bytes": intish(fields.get(f"{prefix}.summary.read_bytes")),
        "read_eagain": intish(fields.get(f"{prefix}.summary.read_eagain")),
        "read_eintr": intish(fields.get(f"{prefix}.summary.read_eintr")),
        "read_errors": intish(fields.get(f"{prefix}.summary.read_errors")),
        "read_terminal_error": intish(fields.get(f"{prefix}.summary.read_terminal_error")) or intish(fields.get(f"{prefix}.read_terminal_error")),
        "mask_bootstrap_records": intish(fields.get(f"{prefix}.summary.mask_bootstrap_records")),
        "dci_data_records": dci_data,
        "dci_pkt_records": dci_pkt,
        "user_space_records": user_space,
        "other_records": other,
        "payload_records": dci_data + dci_pkt + user_space,
        "non_mask_records": dci_data + dci_pkt + user_space + other,
        "samples": samples,
        "deinit_attempted": intish(fields.get(f"{prefix}.summary.deinit_attempted")),
        "deinit_rc": intish(fields.get(f"{prefix}.summary.deinit_rc")),
        "deinit_errno": intish(fields.get(f"{prefix}.summary.deinit_errno")),
        "safe": (
            intish(fields.get(f"{prefix}.rootfs_namespace_only")) == 1
            and intish(fields.get(f"{prefix}.sda29_write")) == 0
            and intish(fields.get(f"{prefix}.switch_logging_attempted")) == 0
            and intish(fields.get(f"{prefix}.write_attempted")) == 0
            and intish(fields.get(f"{prefix}.stream_config_attempted")) == 0
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
    details["diag_dci_register_read"] = collect_diag_dci_register_read(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2059.classify(handoff, hook, steps, details)
    diag = details.get("diag_dci_register_read") if isinstance(details.get("diag_dci_register_read"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    diag_started = intish(diag.get("begin")) == 1 and intish(diag.get("started")) == 1
    diag_safe = bool(diag.get("safe"))
    diag_open = intish(diag.get("open_ok")) == 1
    diag_queried = intish(diag.get("query_count")) > 0
    dci_supported = intish(diag.get("support_nonzero_count")) > 0
    diag_registered = intish(diag.get("registered")) == 1
    diag_payload = intish(diag.get("payload_records")) > 0
    base_label = str(base.get("label", ""))
    wlan0 = bool(details.get("wlan0"))
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))

    if not hook_ok:
        label = "diag-dci-register-read-artifact-hook-regression"
        passed = False
        reason = "V2062 artifact does not contain the DCI register-read contract tokens"
    elif not diag_safe:
        label = "diag-dci-register-read-safety-marker-regression"
        passed = False
        reason = "DCI register-read safety markers were absent or indicated forbidden write/logging-mode activity"
    elif not diag_started or not diag_open:
        label = "diag-dci-register-read-open-failed"
        passed = True
        reason = "private /dev/diag DCI register-read probe did not open; active DIAG cannot proceed until diag node materialization/open is fixed"
    elif not diag_queried or not dci_supported:
        label = "diag-dci-register-read-no-supported-proc"
        passed = True
        reason = "private /dev/diag opened but no queried DCI proc reported nonzero support"
    elif not diag_registered:
        label = "diag-dci-register-failed"
        passed = True
        reason = "DCI support exists, but DIAG_IOCTL_DCI_REG did not return a usable client"
    elif diag_payload and not wlan0:
        label = "diag-dci-register-read-payload-present-no-wlan0"
        passed = True
        reason = "DCI registration produced payload records while the native Wi-Fi cascade still stopped before wlan0"
    elif diag_registered and base_label == "cnss-permgr-register-vote-success-no-wlanmdsp" and not wlanmdsp_seen:
        label = "diag-dci-register-read-no-payload-no-wlanmdsp"
        passed = True
        reason = "DCI registration/deinit succeeded, but register-only reads yielded no DCI/user payload and native still made no wlanmdsp request"
    elif diag_registered:
        label = "diag-dci-register-read-no-payload-route-changed"
        passed = True
        reason = "DCI registration succeeded without payload, but the lower Wi-Fi route changed relative to V2059"
    else:
        label = "diag-dci-register-read-inconclusive"
        passed = False
        reason = "DCI register-read probe did not produce a classifiable result"

    return {
        **base,
        "decision": f"v2063-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "diag_started": diag_started,
        "diag_safe": diag_safe,
        "diag_open": diag_open,
        "diag_queried": diag_queried,
        "diag_dci_supported": dci_supported,
        "diag_registered": diag_registered,
        "diag_payload_records": intish(diag.get("payload_records")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    pm = details.get("per_mgr_vote_focused", {})
    diag = details.get("diag_dci_register_read", {})
    logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    procs = diag.get("procs", []) if isinstance(diag.get("procs"), list) else []
    samples = diag.get("samples", []) if isinstance(diag.get("samples"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    sample_rows = [
        [sample.get("index"), sample.get("bytes"), sample.get("data_type"), sample.get("data_type_name"), sample.get("prefix_hex")]
        for sample in samples
    ]
    return "\n".join([
        "# Native Init V2063 DIAG DCI Register-Read Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2063`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "- Comparator: `docs/reports/NATIVE_INIT_V2059_PERMGR_VOTE_FOCUSED_HANDOFF_2026-06-04.md` remains the PerMgr discriminator; V2059 showed cnss-daemon register/connect plus pm-service server acceptance succeeded with no `wlanmdsp` request.",
        "- Route note: a `diag-dci-register-read-no-payload-route-changed` label means the DCI run is not a PerMgr-negative result; `cnss-daemon` exited before PerMgr registration, so this run only proves the register-only DCI path itself produced no payload.",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} diag_safe={classification.get('diag_safe')}"],
                ["cnss_permgr", classification.get("per_mgr_server_success"), f"client={classification.get('per_mgr_client_success')} peripheral={classification.get('per_mgr_peripheral_success')} server={classification.get('per_mgr_server_success')}"] ,
                ["diag_register", classification.get("diag_registered"), f"open={classification.get('diag_open')} supported={classification.get('diag_dci_supported')} proc={diag.get('selected_proc')} mask={diag.get('selected_mask')} rc={diag.get('register_rc')} client={diag.get('client_id')}"] ,
                ["diag_reads", classification.get("diag_payload_records"), f"records={diag.get('read_records')} bytes={diag.get('read_bytes')} payload={diag.get('payload_records')} bootstrap={diag.get('mask_bootstrap_records')} other={diag.get('other_records')} eagain={diag.get('read_eagain')} errors={diag.get('read_errors')} terminal_error={diag.get('read_terminal_error')}"] ,
                ["diag_cleanup", diag.get("deinit_attempted"), f"deinit_rc={diag.get('deinit_rc')} errno={diag.get('deinit_errno')}"] ,
                ["tftp_branch", "", f"server_check={logdw.get('summary', {}).get('server_check')} ota={logdw.get('summary', {}).get('ota_firewall')} mcfg={logdw.get('summary', {}).get('mcfg')} wlanmdsp={logdw.get('summary', {}).get('wlanmdsp')}"] ,
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## DIAG Support Detail",
        "",
        markdown_table(
            ["proc", "rc", "errno", "support_mask", "nonzero"],
            [[item.get("proc"), item.get("rc"), item.get("errno"), item.get("support_mask"), item.get("support_nonzero")] for item in procs] or [["none", "", "", "", ""]],
        ),
        "",
        "## DIAG Read Samples",
        "",
        markdown_table(
            ["idx", "bytes", "type", "name", "prefix_hex"],
            sample_rows or [["none", "", "", "", ""]],
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
        "- If `diag-dci-register-read-payload-present-no-wlan0`, decode the captured DCI/user payload offline before adding any log/event masks.",
        "- If `diag-dci-register-read-no-payload-no-wlanmdsp`, register-only DCI is insufficient; the next modem-internal visibility path is a bounded active DCI log/event stream-mask capture.",
        "- If `diag-dci-register-read-no-payload-route-changed`, keep V2059 as the AP-side PerMgr answer and treat this run as a DCI visibility-only result, because the lower route did not match the focused PerMgr baseline.",
        "- If `diag-dci-register-failed`, repair the DCI registration contract before any heavier logging-mode path.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- DIAG use was limited to a private rootfs `/dev/diag` char node plus `DIAG_IOCTL_DCI_SUPPORT`, `DIAG_IOCTL_DCI_REG`, nonblocking reads, and `DIAG_IOCTL_DCI_DEINIT`. No `DIAG_IOCTL_SWITCH_LOGGING`, DIAG write, log/event mask write, DCI stream config, passive DIAG replay, QMI send, AP-side strace, boot-time QRTR matrix, or ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2062 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, private tmp-root `/dev/diag`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2057() -> None:
    prev2059.prev2057.CYCLE = CYCLE
    prev2059.prev2057.OUT_DIR = OUT_DIR
    prev2059.prev2057.HANDOFF_DIR = HANDOFF_DIR
    prev2059.prev2057.HANDOFF_REPORT = HANDOFF_REPORT
    prev2059.prev2057.REPORT_PATH = REPORT_PATH
    prev2059.prev2057.V2056_OUT = V2062_OUT
    prev2059.prev2057.V2056_INIT = V2062_INIT
    prev2059.prev2057.V2056_BOOT = V2062_BOOT
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
