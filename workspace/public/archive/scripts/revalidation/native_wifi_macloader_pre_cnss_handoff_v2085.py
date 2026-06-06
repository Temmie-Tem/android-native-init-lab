#!/usr/bin/env python3
"""V2085 rollbackable native handoff for the macloader-pre-CNSS gate."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_qcacld_post_bdf_handoff_v2083 as prev2083


CYCLE = "V2085"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2085-macloader-pre-cnss-handoff"
HANDOFF_DIR = OUT_DIR / "v2084-handoff"
HANDOFF_REPORT = OUT_DIR / "v2084-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2085_MACLOADER_PRE_CNSS_HANDOFF_2026-06-05.md"
)
V2084_OUT = REPO_ROOT / "tmp" / "wifi" / "v2084-macloader-pre-cnss-test-boot"
V2084_INIT = V2084_OUT / "init_v2084_macloader_pre_cnss"
V2084_BOOT = V2084_OUT / "boot_linux_v2084_macloader_pre_cnss.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2084/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.220 (v2084-macloader-pre-cnss)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2084.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2084.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2084-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v405"

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
        "A90v2084",
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
        "wlfw_late_msg21_focused.begin=1",
        "per_mgr_vote_focused.begin=1",
        "%s.begin=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2084_INIT, init_required), (V2084_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2084_INIT else boot_forbidden
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
    return details


def logdw_summary(details: dict[str, Any]) -> dict[str, Any]:
    return prev2083.logdw_summary(details)


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    mac = details.get("macloader_pre_cnss") if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    mac_enabled = intish(mac.get("enabled")) == 1 and intish(mac.get("active_driver_start")) == 1
    mac_ready = intish(mac.get("ready")) == 1 or intish(mac.get("child_observable")) == 1
    mac_route_ok = hook_ok and mac_enabled and mac_ready
    mac_assigned = intish(mac.get("mac_assigned")) == 1
    step_ok = {
        str(step.get("name")): bool(step.get("ok"))
        for step in steps
        if isinstance(step, dict)
    }
    v2085_rollback_ok = step_ok.get("post-selftest", False) and step_ok.get("post-status", False)
    wlanmdsp_seen = (
        intish(summary.get("wlanmdsp")) > 0
        or intish(summary.get("fallback_wlanmdsp")) > 0
        or intish(summary.get("firmware_mnt_wlanmdsp")) > 0
    )
    server_check_seen = intish(summary.get("server_check")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0 or bool(base.get("wlan0"))

    if not hook_ok:
        label = "macloader-pre-cnss-artifact-hook-regression"
        passed = False
        reason = "V2084 artifact does not contain the macloader-pre-CNSS route contract"
    elif not mac_enabled:
        label = "macloader-pre-cnss-route-disabled"
        passed = False
        reason = "helper summary did not enable the macloader-pre-CNSS active driver-start gate"
    elif not mac_ready:
        label = "macloader-pre-cnss-missing-or-exec-failed"
        passed = True
        reason = "macloader was planned but was not observable in the helper window"
    elif wlan0:
        label = "macloader-pre-cnss-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "macloader-pre-cnss-fw-ready-progress"
        passed = True
        reason = "macloader route reached FW-ready; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "macloader-pre-cnss-wlanmdsp-requested-no-fw-ready"
        passed = True
        reason = "macloader route caused a wlanmdsp tftp request, but FW-ready/wlan0 did not follow"
    elif server_check_seen:
        label = "macloader-pre-cnss-server-check-no-wlanmdsp"
        passed = True
        reason = "macloader route reached the Android bootstrap server_check branch, but not wlanmdsp"
    elif mac_assigned:
        label = "macloader-pre-cnss-mac-assigned-no-tftp-bootstrap"
        passed = True
        reason = "macloader assigned the MAC, but modem still did not enter server_check/wlanmdsp tftp bootstrap"
    else:
        label = "macloader-pre-cnss-no-mac-no-tftp-bootstrap"
        passed = True
        reason = "macloader was observable, but no MAC assignment or tftp bootstrap followed"

    return {
        **base,
        "decision": f"v2085-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "mac_enabled": mac_enabled,
        "mac_ready": mac_ready,
        "mac_route_ok": mac_route_ok,
        "mac_assigned": mac_assigned,
        "wlanmdsp_seen": wlanmdsp_seen,
        "server_check_seen": server_check_seen,
        "v2085_rollback_ok": v2085_rollback_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    mac = details.get("macloader_pre_cnss", {}) if isinstance(details.get("macloader_pre_cnss"), dict) else {}
    surface = details.get("icnss_qcacld_post_bdf", {}) if isinstance(details.get("icnss_qcacld_post_bdf"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2085 Macloader Pre-CNSS Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2085`",
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
                ["macloader", classification.get("mac_ready"), f"mac_assigned={classification.get('mac_assigned')} loading_driver={mac.get('loading_driver')} boot_wlan_log={mac.get('boot_wlan_log')}"],
                ["tftp", classification.get("wlanmdsp_seen"), f"server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')} fallback={summary.get('fallback_wlanmdsp')}"],
                ["kernel_surface", surface.get("wlan_module_loaded"), f"dev_wlan={surface.get('dev_wlan_exists')} qcwlanstate={surface.get('qcwlanstate_exists')} wlan0={surface.get('wlan0_exists')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
                ["rollback", classification.get("v2085_rollback_ok"), "post-selftest and post-status succeeded after rollback"],
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
        "- V2085 is the first native lower-window route that intentionally runs Android's `macloader` before `cnss-daemon` while retaining the RFS bridges, PerMgr/WLFW route, and light observer.",
        "- If `server_check`/`wlanmdsp` appears, macloader is part of the missing AP-side trigger chain and the next gate is downstream FW-ready/wlan0.",
        "- If MAC assignment appears but TFTP bootstrap remains absent, the remaining blocker is after AP-side macloader and before modem selection of the WLAN-PD firmware branch.",
        "- If macloader is not observable, repair the macloader execution contract before re-classifying the producer gate.",
        "- Observed V2085 result: `macloader` has the Android identity/domain/caps and stays observable, but no `boot_wlan`/driver-load/MAC-assignment log appears; the next discriminator is the `macloader` precondition/stall point, not PerMgr, RIL, TFTP registration, or SDX50M.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2084 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, private tmp-root `/dev/socket/logdw`, tracefs uprobes, Android-parity `macloader` driver-start action, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2083() -> None:
    prev2083.CYCLE = CYCLE
    prev2083.OUT_DIR = OUT_DIR
    prev2083.HANDOFF_DIR = HANDOFF_DIR
    prev2083.HANDOFF_REPORT = HANDOFF_REPORT
    prev2083.REPORT_PATH = REPORT_PATH
    prev2083.V2082_OUT = V2084_OUT
    prev2083.V2082_INIT = V2084_INIT
    prev2083.V2082_BOOT = V2084_BOOT
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
