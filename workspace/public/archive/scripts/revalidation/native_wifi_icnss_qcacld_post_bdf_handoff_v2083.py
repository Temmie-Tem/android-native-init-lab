#!/usr/bin/env python3
"""V2083 rollbackable native handoff for the post-BDF ICNSS/QCACLD edge."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_wlfw_late_msg21_handoff_v2081 as prev2081


CYCLE = "V2083"
OUT_DIR = prev2081.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2083-icnss-qcacld-post-bdf-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2082-handoff"
HANDOFF_REPORT = OUT_DIR / "v2082-handoff-report.md"
REPORT_PATH = prev2081.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2083_ICNSS_QCACLD_POST_BDF_HANDOFF_2026-06-05.md"
)
V2082_OUT = prev2081.prev2059.prev2057.prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2082-icnss-qcacld-post-bdf-test-boot"
)
V2082_INIT = V2082_OUT / "init_v2082_icnss_qcacld_post_bdf"
V2082_BOOT = V2082_OUT / "boot_linux_v2082_icnss_qcacld_post_bdf.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2082/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.219 (v2082-icnss-qcacld-post-bdf)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2082.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2082.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2082-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v404"

BASE_COLLECT_DETAILS = prev2081.collect_details
BASE_CLASSIFY = prev2081.classify


def rel(path: Path) -> str:
    return prev2081.rel(path)


def intish(value: object) -> int:
    return prev2081.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2081.markdown_table(headers, rows)


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
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2082",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "wlfw_late_msg21_focused.begin=1",
        "per_mgr_vote_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
        "%s.begin=1",
        "%s.mode=read-only-post-bdf-icnss-qcacld-surface",
        "%s.no_boot_wlan_write=1",
        "%s.no_qcwlanstate_write=1",
        "%s.no_module_load_unload=1",
        "%s.no_driver_bind_unbind=1",
        "%s.wlan_module_loaded=%d",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2082_INIT, init_required), (V2082_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2082_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def collect_icnss_qcacld(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "icnss_qcacld_post_bdf_focused"
    int_fields = (
        "begin",
        "no_boot_wlan_write",
        "no_qcwlanstate_write",
        "no_module_load_unload",
        "no_driver_bind_unbind",
        "no_diag",
        "no_strace",
        "no_qrtr_matrix",
        "no_wifi_hal",
        "scan_connect",
        "credentials",
        "external_ping",
        "wlan_module_loaded",
        "wlan0_exists",
        "dev_wlan_exists",
        "qcwlanstate_exists",
        "boot_wlan_exists",
        "macloader_process_count",
        "ks_process_count",
        "cnss_daemon_process_count",
        "cnss_diag_process_count",
        "wlan_count",
        "phy_count",
        "proc_wireless_count",
        "wifi_rfkill_count",
        "path.wlan_module.exists",
        "path.dev_qcwlanstate.exists",
        "path.dev_wlan.exists",
        "path.sys_class_net_wlan0.exists",
        "path.sys_class_ieee80211.exists",
        "path.boot_wlan.exists",
        "read.icnss_uevent.ok",
        "read.firmware_class_path.ok",
        "read.wlan0_operstate.ok",
    )
    data: dict[str, Any] = {
        "mode": fields.get(f"{prefix}.mode", ""),
        "icnss_uevent": fields.get(f"{prefix}.read.icnss_uevent.value", ""),
        "firmware_class_path": fields.get(f"{prefix}.read.firmware_class_path.value", ""),
        "wlan0_operstate": fields.get(f"{prefix}.read.wlan0_operstate.value", ""),
        "wlan_names": fields.get(f"{prefix}.wlan_names", ""),
        "phy_names": fields.get(f"{prefix}.phy_names", ""),
        "wifi_rfkill_names": fields.get(f"{prefix}.wifi_rfkill_names", ""),
    }
    for key in int_fields:
        data[key.replace(".", "_")] = intish(fields.get(f"{prefix}.{key}"))
    data["safe"] = (
        data["begin"] == 1
        and data["no_boot_wlan_write"] == 1
        and data["no_qcwlanstate_write"] == 1
        and data["no_module_load_unload"] == 1
        and data["no_driver_bind_unbind"] == 1
        and data["no_diag"] == 1
        and data["no_strace"] == 1
        and data["no_qrtr_matrix"] == 1
        and data["no_wifi_hal"] == 1
        and data["scan_connect"] == 0
        and data["credentials"] == 0
        and data["external_ping"] == 0
    )
    return data


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2081.prev2059.prev2057.parse_fields()
    details["icnss_qcacld_post_bdf"] = collect_icnss_qcacld(fields)
    return details


def logdw_summary(details: dict[str, Any]) -> dict[str, Any]:
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    return logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    surface = details.get("icnss_qcacld_post_bdf") if isinstance(details.get("icnss_qcacld_post_bdf"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    surface_safe = bool(surface.get("safe"))
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0 or intish(surface.get("wlan0_exists")) > 0
    wlanmdsp_seen = (
        intish(summary.get("wlanmdsp")) > 0
        or intish(summary.get("fallback_wlanmdsp")) > 0
        or intish(summary.get("firmware_mnt_wlanmdsp")) > 0
    )
    server_check_seen = intish(summary.get("server_check")) > 0
    mcfg_seen = intish(summary.get("mcfg")) > 0
    module_loaded = intish(surface.get("wlan_module_loaded")) > 0
    dev_wlan = intish(surface.get("dev_wlan_exists")) > 0

    if not hook_ok:
        label = "icnss-qcacld-post-bdf-artifact-hook-regression"
        passed = False
        reason = "V2082 artifact does not contain the compact ICNSS/QCACLD observer contract"
    elif not surface_safe:
        label = "icnss-qcacld-post-bdf-safety-regression"
        passed = False
        reason = "compact ICNSS/QCACLD safety markers were absent or unsafe"
    elif wlan0:
        label = "icnss-qcacld-post-bdf-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "icnss-qcacld-post-bdf-fw-ready-progress"
        passed = True
        reason = "native reached kernel FW-ready; chase wlan0 next"
    elif not wlanmdsp_seen and module_loaded and dev_wlan:
        label = "icnss-qcacld-module-present-no-wlanmdsp-request"
        passed = True
        reason = "native has the kernel WLAN module/dev surface, but modem tftp never requests wlanmdsp"
    elif not wlanmdsp_seen:
        label = "icnss-qcacld-no-wlanmdsp-request"
        passed = True
        reason = "native completes PerMgr/WLFW cap/BDF/cal but modem tftp never requests wlanmdsp"
    elif not module_loaded:
        label = "icnss-qcacld-wlanmdsp-seen-module-missing"
        passed = True
        reason = "wlanmdsp tftp evidence appeared, but the kernel WLAN module surface was absent"
    else:
        label = "icnss-qcacld-wlanmdsp-seen-no-fw-ready"
        passed = True
        reason = "wlanmdsp tftp evidence and kernel module surface were present, but FW-ready/wlan0 did not follow"

    return {
        **base,
        "decision": f"v2083-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "surface_safe": surface_safe,
        "wlanmdsp_seen": wlanmdsp_seen,
        "server_check_seen": server_check_seen,
        "mcfg_seen": mcfg_seen,
        "module_loaded": module_loaded,
        "dev_wlan": dev_wlan,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    surface = details.get("icnss_qcacld_post_bdf", {}) if isinstance(details.get("icnss_qcacld_post_bdf"), dict) else {}
    late = details.get("wlfw_late_msg21", {}) if isinstance(details.get("wlfw_late_msg21"), dict) else {}
    pm = details.get("per_mgr_vote_focused", {}) if isinstance(details.get("per_mgr_vote_focused"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2083 ICNSS QCACLD Post-BDF Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2083`",
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
                ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} surface_safe={classification.get('surface_safe')}"],
                ["per_mgr", classification.get("per_mgr_server_success"), f"cnss={classification.get('per_mgr_client_success')} peripheral={classification.get('per_mgr_peripheral_success')} vote_ack={pm.get('pm_vote_ack_seen')}"],
                ["wlfw", classification.get("saw_msg21"), f"qmi_hit={late.get('qmi_hit_count')} ids={late.get('sample_msg_ids')} cal={late.get('cal_return')}"],
                ["tftp", classification.get("wlanmdsp_seen"), f"server_check={summary.get('server_check')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')} fallback={summary.get('fallback_wlanmdsp')}"],
                ["kernel_surface", classification.get("module_loaded"), f"dev_wlan={classification.get('dev_wlan')} qcwlanstate={surface.get('qcwlanstate_exists')} wlan0={surface.get('wlan0_exists')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## ICNSS QCACLD Surface",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["mode", surface.get("mode", "")],
                ["wlan_module_loaded", surface.get("wlan_module_loaded", "")],
                ["dev_wlan_exists", surface.get("dev_wlan_exists", "")],
                ["qcwlanstate_exists", surface.get("qcwlanstate_exists", "")],
                ["boot_wlan_exists", surface.get("boot_wlan_exists", "")],
                ["wlan0_exists", surface.get("wlan0_exists", "")],
                ["wlan_count", surface.get("wlan_count", "")],
                ["phy_count", surface.get("phy_count", "")],
                ["macloader_process_count", surface.get("macloader_process_count", "")],
                ["ks_process_count", surface.get("ks_process_count", "")],
                ["firmware_class_path", surface.get("firmware_class_path", "")],
                ["icnss_uevent", surface.get("icnss_uevent", "")],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- V2083 keeps the V2081 internal-modem route: cnss-daemon PerMgr register/connect succeeds, WLFW cap/BDF/cal completes, and late `msg_id=0x21` is observed.",
        "- The new discriminator checks whether the post-BDF failure is lack of modem `wlanmdsp` tftp request versus a missing kernel WLAN module consumer surface.",
        "- If `wlanmdsp=0`, the next gate stays on why the modem never fetches the WLAN PD image; do not pivot to Wi-Fi HAL/scan/connect.",
        "- If `wlanmdsp>0` with module surface present, the next gate is kernel FW-ready/ICNSS driver event handling.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2082 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, tracefs uprobes, compact read-only summaries, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2081() -> None:
    prev2081.CYCLE = CYCLE
    prev2081.OUT_DIR = OUT_DIR
    prev2081.HANDOFF_DIR = HANDOFF_DIR
    prev2081.HANDOFF_REPORT = HANDOFF_REPORT
    prev2081.REPORT_PATH = REPORT_PATH
    prev2081.V2080_OUT = V2082_OUT
    prev2081.V2080_INIT = V2082_INIT
    prev2081.V2080_BOOT = V2082_BOOT
    prev2081.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2081.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2081.TEST_LOG_PATH = TEST_LOG_PATH
    prev2081.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2081.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2081.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2081.artifact_hook_check = artifact_hook_check
    prev2081.collect_details = collect_details
    prev2081.classify = classify
    prev2081.render_report = render_report
    prev2081.configure_prev2059()


def main(argv: list[str] | None = None) -> int:
    configure_prev2081()
    return prev2081.prev2059.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
