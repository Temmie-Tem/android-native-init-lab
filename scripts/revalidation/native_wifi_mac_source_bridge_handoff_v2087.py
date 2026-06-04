#!/usr/bin/env python3
"""V2087 rollbackable native handoff for the macloader MAC-source bridge gate."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_qcacld_post_bdf_handoff_v2083 as prev2083


CYCLE = "V2087"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2087-mac-source-bridge-handoff"
HANDOFF_DIR = OUT_DIR / "v2086-handoff"
HANDOFF_REPORT = OUT_DIR / "v2086-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2087_MAC_SOURCE_BRIDGE_HANDOFF_2026-06-05.md"
)
V2086_OUT = REPO_ROOT / "tmp" / "wifi" / "v2086-mac-source-bridge-test-boot"
V2086_INIT = V2086_OUT / "init_v2086_mac_source_bridge"
V2086_BOOT = V2086_OUT / "boot_linux_v2086_mac_source_bridge.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2086/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.222 (v2086-mac-source-bridge)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2086.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2086.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2086-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v406"

BASE_COLLECT_DETAILS = prev2083.collect_details
BASE_CLASSIFY = prev2083.classify


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    return prev2083.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2083.markdown_table(headers, rows)


def read_text_best_effort(path: Path, limit: int = 1_000_000) -> str:
    try:
        data = path.read_bytes()[:limit]
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def collect_macloader(fields: dict[str, str], handoff: dict[str, Any]) -> dict[str, Any]:
    handoff_manifest = Path(str(handoff.get("manifest", "")))
    if not handoff_manifest.is_absolute():
        handoff_manifest = REPO_ROOT / handoff_manifest
    handoff_dir = handoff_manifest.parent
    dmesg_text = read_text_best_effort(handoff_dir / "test-v1393-dmesg.stdout.txt")
    log_text = read_text_best_effort(handoff_dir / "test-v1393-log.stdout.txt")
    helper_text = read_text_best_effort(handoff_dir / "test-v1393-helper-result.stdout.txt")
    combined = "\n".join([dmesg_text, log_text, helper_text])
    prefix = "wifi_companion_start.macloader_pre_cnss"
    child_prefix = "wifi_companion_start.child.macloader"
    return {
        "enabled": intish(fields.get(f"{prefix}.enabled")),
        "active_driver_start": intish(fields.get(f"{prefix}.active_driver_start")),
        "boot_wlan_write_expected": intish(fields.get(f"{prefix}.boot_wlan_write_expected")),
        "qcwlanstate_write": intish(fields.get(f"{prefix}.qcwlanstate_write")),
        "observable": intish(fields.get(f"{prefix}.observable")),
        "ready": intish(fields.get(f"{prefix}.ready")),
        "fd_summary_captured": intish(fields.get(f"{prefix}.fd_summary_captured")),
        "child_observable": intish(fields.get(f"{child_prefix}.observable")),
        "child_exited": intish(fields.get(f"{child_prefix}.exited")),
        "child_exit_code": intish(fields.get(f"{child_prefix}.exit_code")),
        "child_signal": intish(fields.get(f"{child_prefix}.signal")),
        "child_postflight_safe": intish(fields.get(f"{child_prefix}.postflight_safe")),
        "mac_assigned": 1 if "Assigning MAC from Macloader" in combined else 0,
        "loading_driver": 1 if "wlan: Loading driver" in combined else 0,
        "boot_wlan_log": 1 if "Start to set boot_wlan" in combined or "Complete to set the boot_wlan" in combined else 0,
        "qcwlan_retry_log": 1 if "PATH_QCWLANSATE_SYSFS read retry" in combined else 0,
    }


def collect_mac_source_bridge(fields: dict[str, str]) -> dict[str, Any]:
    def get(phase: str, name: str, field: str) -> int:
        return intish(fields.get(f"wifi_companion_start.macloader_mac_source_bridge.{phase}.{name}.{field}"))

    return {
        "enabled": intish(fields.get("wifi_companion_start.macloader_mac_source_bridge.enabled")),
        "pre_enabled": intish(fields.get("wifi_companion_start.macloader_mac_source_bridge.pre.enabled")),
        "post_enabled": intish(fields.get("wifi_companion_start.macloader_mac_source_bridge.post.enabled")),
        "mac_info_exists": get("pre", "mac_info", "exists"),
        "mac_info_readable": get("pre", "mac_info", "readable"),
        "mac_info_hash_available": get("pre", "mac_info", "hash_available"),
        "mac_info_bytes": get("pre", "mac_info", "bytes"),
        "sys_wifi_exists": get("pre", "sys_wifi", "exists"),
        "sys_wifi_mac_addr_exists": get("pre", "sys_wifi_mac_addr", "exists"),
        "sys_wifi_mac_addr_writable": get("pre", "sys_wifi_mac_addr", "writable"),
        "sys_wifi_qcwlanstate_exists": get("pre", "sys_wifi_qcwlanstate", "exists"),
        "sys_kernel_boot_wlan_exists": get("pre", "sys_kernel_boot_wlan", "exists"),
        "sys_kernel_boot_wlan_writable": get("pre", "sys_kernel_boot_wlan", "writable"),
        "persist_nv_exists": get("pre", "persist_nv", "exists"),
        "persist_nv_readable": get("pre", "persist_nv", "readable"),
        "post_mac_info_exists": get("post", "mac_info", "exists"),
        "post_sys_wifi_mac_addr_exists": get("post", "sys_wifi_mac_addr", "exists"),
        "post_sys_wifi_mac_addr_writable": get("post", "sys_wifi_mac_addr", "writable"),
        "post_sys_kernel_boot_wlan_exists": get("post", "sys_kernel_boot_wlan", "exists"),
        "post_sys_kernel_boot_wlan_writable": get("post", "sys_kernel_boot_wlan", "writable"),
    }


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
        "A90v2086",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "/vendor/bin/hw/macloader",
        "u:r:macloader:s0",
        "wifi_companion_start.macloader_pre_cnss.enabled=%d",
        "wifi_companion_start.macloader_pre_cnss.active_driver_start=1",
        "wifi_companion_start.macloader_pre_cnss.boot_wlan_write_expected=%d",
        "wifi_companion_start.macloader_pre_cnss.qcwlanstate_write=0",
        "wifi_companion_start.macloader_mac_source_bridge.enabled=%d",
        "/mnt/vendor/efs/wifi/.mac.info",
        "/sys/wifi/mac_addr",
        "/sys/kernel/boot_wlan",
        "/persist/WCNSS_qcom_wlan_nv.bin",
        "wlfw_late_msg21_focused.begin=1",
        "per_mgr_vote_focused.begin=1",
        "%s.begin=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2086_INIT, init_required), (V2086_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2086_INIT else boot_forbidden
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


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2083.prev2081.prev2059.prev2057.parse_fields()
    details["macloader_pre_cnss"] = collect_macloader(fields, handoff)
    details["mac_source_bridge"] = collect_mac_source_bridge(fields)
    return details


def logdw_summary(details: dict[str, Any]) -> dict[str, Any]:
    return prev2083.logdw_summary(details)


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    mac = details.get("macloader_pre_cnss") if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    mac_source = details.get("mac_source_bridge") if isinstance(details.get("mac_source_bridge"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    mac_enabled = intish(mac.get("enabled")) == 1 and intish(mac.get("active_driver_start")) == 1
    mac_ready = intish(mac.get("ready")) == 1 or intish(mac.get("child_observable")) == 1
    mac_route_ok = hook_ok and mac_enabled and mac_ready
    mac_source_ok = bool(
        intish(mac_source.get("enabled")) == 1
        and intish(mac_source.get("mac_info_exists")) == 1
        and intish(mac_source.get("mac_info_readable")) == 1
        and intish(mac_source.get("sys_wifi_mac_addr_exists")) == 1
        and intish(mac_source.get("sys_wifi_mac_addr_writable")) == 1
        and intish(mac_source.get("sys_kernel_boot_wlan_exists")) == 1
        and intish(mac_source.get("sys_kernel_boot_wlan_writable")) == 1
    )
    mac_assigned = intish(mac.get("mac_assigned")) == 1
    step_ok = {
        str(step.get("name")): bool(step.get("ok"))
        for step in steps
        if isinstance(step, dict)
    }
    v2087_rollback_ok = step_ok.get("post-selftest", False) and step_ok.get("post-status", False)
    wlanmdsp_seen = (
        intish(summary.get("wlanmdsp")) > 0
        or intish(summary.get("fallback_wlanmdsp")) > 0
        or intish(summary.get("firmware_mnt_wlanmdsp")) > 0
    )
    server_check_seen = intish(summary.get("server_check")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0 or bool(base.get("wlan0"))

    if not hook_ok:
        label = "mac-source-bridge-artifact-hook-regression"
        passed = False
        reason = "V2086 artifact does not contain the macloader MAC-source bridge route contract"
    elif not mac_enabled:
        label = "mac-source-bridge-route-disabled"
        passed = False
        reason = "helper summary did not enable the macloader MAC-source bridge active driver-start gate"
    elif not mac_ready:
        label = "mac-source-bridge-missing-or-exec-failed"
        passed = True
        reason = "macloader was planned but was not observable in the helper window"
    elif not mac_source_ok:
        label = "mac-source-bridge-source-unavailable"
        passed = True
        reason = "MAC-source bridge ran, but .mac.info or ICNSS sysfs write targets were not available in the macloader namespace"
    elif wlan0:
        label = "mac-source-bridge-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "mac-source-bridge-fw-ready-progress"
        passed = True
        reason = "macloader route reached FW-ready; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "mac-source-bridge-wlanmdsp-requested-no-fw-ready"
        passed = True
        reason = "macloader route caused a wlanmdsp tftp request, but FW-ready/wlan0 did not follow"
    elif server_check_seen:
        label = "mac-source-bridge-server-check-no-wlanmdsp"
        passed = True
        reason = "macloader route reached the Android bootstrap server_check branch, but not wlanmdsp"
    elif mac_assigned:
        label = "mac-source-bridge-mac-assigned-no-tftp-bootstrap"
        passed = True
        reason = "macloader assigned the MAC, but modem still did not enter server_check/wlanmdsp tftp bootstrap"
    else:
        label = "mac-source-bridge-no-mac-no-tftp-bootstrap"
        passed = True
        reason = "macloader was observable, but no MAC assignment or tftp bootstrap followed"

    return {
        **base,
        "decision": f"v2087-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "mac_enabled": mac_enabled,
        "mac_ready": mac_ready,
        "mac_route_ok": mac_route_ok,
        "mac_source_ok": mac_source_ok,
        "mac_assigned": mac_assigned,
        "wlanmdsp_seen": wlanmdsp_seen,
        "server_check_seen": server_check_seen,
        "v2087_rollback_ok": v2087_rollback_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    mac = details.get("macloader_pre_cnss", {}) if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    mac_source = details.get("mac_source_bridge", {}) if isinstance(details.get("mac_source_bridge"), dict) else {}
    surface = details.get("icnss_qcacld_post_bdf", {}) if isinstance(details.get("icnss_qcacld_post_bdf"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2087 Macloader MAC-Source Bridge Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2087`",
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
                ["macloader_route", classification.get("mac_route_ok"), f"hook={classification.get('hook_ok')} mac_enabled={classification.get('mac_enabled')} mac_ready={classification.get('mac_ready')}"],
                ["mac_source", classification.get("mac_source_ok"), f"mac_info={mac_source.get('mac_info_exists')}/{mac_source.get('mac_info_readable')} mac_addr_w={mac_source.get('sys_wifi_mac_addr_writable')} boot_wlan_w={mac_source.get('sys_kernel_boot_wlan_writable')}"],
                ["macloader", classification.get("mac_ready"), f"mac_assigned={classification.get('mac_assigned')} loading_driver={mac.get('loading_driver')} boot_wlan_log={mac.get('boot_wlan_log')}"],
                ["tftp", classification.get("wlanmdsp_seen"), f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')} fallback={summary.get('fallback_wlanmdsp')}"],
                ["kernel_surface", surface.get("wlan_module_loaded"), f"dev_wlan={surface.get('dev_wlan_exists')} qcwlanstate={surface.get('qcwlanstate_exists')} wlan0={surface.get('wlan0_exists')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
                ["rollback", classification.get("v2087_rollback_ok"), "post-selftest and post-status succeeded after rollback"],
            ],
        ),
        "",
        "## MAC Source Bridge",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["enabled", mac_source.get("enabled", "")],
                ["pre_enabled", mac_source.get("pre_enabled", "")],
                ["mac_info_exists", mac_source.get("mac_info_exists", "")],
                ["mac_info_readable", mac_source.get("mac_info_readable", "")],
                ["mac_info_hash_available", mac_source.get("mac_info_hash_available", "")],
                ["mac_info_bytes", mac_source.get("mac_info_bytes", "")],
                ["sys_wifi_exists", mac_source.get("sys_wifi_exists", "")],
                ["sys_wifi_mac_addr_exists", mac_source.get("sys_wifi_mac_addr_exists", "")],
                ["sys_wifi_mac_addr_writable", mac_source.get("sys_wifi_mac_addr_writable", "")],
                ["sys_wifi_qcwlanstate_exists", mac_source.get("sys_wifi_qcwlanstate_exists", "")],
                ["sys_kernel_boot_wlan_exists", mac_source.get("sys_kernel_boot_wlan_exists", "")],
                ["sys_kernel_boot_wlan_writable", mac_source.get("sys_kernel_boot_wlan_writable", "")],
                ["persist_nv_exists", mac_source.get("persist_nv_exists", "")],
                ["post_sys_wifi_mac_addr_exists", mac_source.get("post_sys_wifi_mac_addr_exists", "")],
                ["post_sys_kernel_boot_wlan_exists", mac_source.get("post_sys_kernel_boot_wlan_exists", "")],
            ],
        ),
        "",
        "## Macloader Gate",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["enabled", mac.get("enabled", "")],
                ["active_driver_start", mac.get("active_driver_start", "")],
                ["boot_wlan_write_expected", mac.get("boot_wlan_write_expected", "")],
                ["qcwlanstate_write", mac.get("qcwlanstate_write", "")],
                ["observable", mac.get("observable", "")],
                ["ready", mac.get("ready", "")],
                ["child_exit_code", mac.get("child_exit_code", "")],
                ["child_signal", mac.get("child_signal", "")],
                ["mac_assigned", mac.get("mac_assigned", "")],
                ["loading_driver", mac.get("loading_driver", "")],
                ["qcwlan_retry_log", mac.get("qcwlan_retry_log", "")],
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- V2087 wires Android's MAC inputs into the native `macloader` namespace: read-only EFS `.mac.info`, read-only persist NV path, `/sys/wifi`, and `/sys/kernel/boot_wlan`.",
        "- Required success signal: kernel dmesg contains `icnss: Assigning MAC from Macloader` before evaluating whether `wlanmdsp` follows.",
        "- Falsifier: if MAC assignment appears but `server_check`/`wlanmdsp` remains absent, MAC assignment is not the producer trigger.",
        "- If MAC assignment is still absent with source targets available, inspect the `macloader` write path or remaining Android init property/sysfs preconditions.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2086 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, read-only EFS/persist mounts for `macloader`, `/sys/wifi` and `/sys/kernel/boot_wlan` exposure, private tmp-root `/dev/socket/logdw`, tracefs uprobes, Android-parity `macloader` driver-start action, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2083() -> None:
    prev2083.CYCLE = CYCLE
    prev2083.OUT_DIR = OUT_DIR
    prev2083.HANDOFF_DIR = HANDOFF_DIR
    prev2083.HANDOFF_REPORT = HANDOFF_REPORT
    prev2083.REPORT_PATH = REPORT_PATH
    prev2083.V2082_OUT = V2086_OUT
    prev2083.V2082_INIT = V2086_INIT
    prev2083.V2082_BOOT = V2086_BOOT
    prev2083.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2083.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2083.TEST_LOG_PATH = TEST_LOG_PATH
    prev2083.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2083.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2083.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2083.artifact_hook_check = artifact_hook_check
    prev2083.collect_details = collect_details
    prev2083.classify = classify
    prev2083.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2083()
    return prev2083.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
