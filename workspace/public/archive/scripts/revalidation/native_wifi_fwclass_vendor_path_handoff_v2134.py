#!/usr/bin/env python3
"""V2134 rollbackable handoff for V2133 firmware_class vendor-path bridge."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_register_probe_stack_handoff_v2132 as prev2132


CYCLE = "V2134"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2134-fwclass-vendor-path-handoff"
HANDOFF_DIR = OUT_DIR / "v2133-handoff"
HANDOFF_REPORT = OUT_DIR / "v2133-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2134_FWCLASS_VENDOR_PATH_HANDOFF_2026-06-05.md"
)
V2133_OUT = REPO_ROOT / "tmp" / "wifi" / "v2133-fwclass-vendor-path-test-boot"
V2133_INIT = V2133_OUT / "init_v2133_fwclass_vendor_path"
V2133_BOOT = V2133_OUT / "boot_linux_v2133_fwclass_vendor_path.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2133/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.241 (v2133-fwclass-vendor-path)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2133.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2133.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2133-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v424"

ORIGINAL_CLASSIFY = prev2132.classify
ORIGINAL_COLLECT_DETAILS = prev2132.collect_details


def intish(value: object) -> int:
    return prev2132.intish(value)


def rel(path: Path) -> str:
    return prev2132.rel(path)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2132.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2133",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
        "fwclass_vendor_path",
        "/mnt/vendor/firmware",
        "/sys/module/firmware_class/parameters/path",
        "safety_sda29_ro_noload=1",
        "no_sda29_write=1",
        "no_icnss_bind_unbind=1",
        "WCNSS_qcom_cfg.ini",
        "bdwlan.bin",
        "regdb.bin",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "post_fw_ready_boot_wlan_trigger",
        "icnss_register_probe_stack_sampler",
        "read-only-proc-stack-workqueue-sampler",
        "no_tracefs_write=1",
        "no_sysrq=1",
        "after_boot_wlan_trigger",
        "after_boot_wlan_long_window",
        "/proc/%ld/stack",
        "workqueue_stats",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.event.register_driver.posted=%d",
        "wlan_pd_icnss_ipc_snapshot.%s.icnss_stats.state.line=%s",
        "wlfw_late_msg21_focused.begin=1",
        "per_mgr_vote_focused.begin=1",
    )
    boot_forbidden = (
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "post_bdf_boot_wlan_consumer_gate.begin=1",
        "ota_firewall/ruleset:",
        "tftp_server-android-runtime",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2133_INIT, init_required), (V2133_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2133_INIT else boot_forbidden
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


def collect_fwclass_vendor_path(fields: dict[str, str], text: str) -> dict[str, Any]:
    lines = text.splitlines()
    apply_match = (
        "fwclass_vendor_path apply write_rc=0 read_rc=0 "
        "readback=/mnt/vendor/firmware match=1"
    ) in text
    restore_seen = "fwclass_vendor_path restore phase=supervisor-complete" in text
    restore_match = any(
        "fwclass_vendor_path restore phase=supervisor-complete write_rc=0 read_rc=0" in line
        and " match=1" in line
        for line in lines
    )
    asset_ok = all(any(
        f"fwclass_vendor_path asset label={name} " in line and " present=1" in line
        for line in lines
    ) for name in ("WCNSS_qcom_cfg.ini", "bdwlan.bin", "regdb.bin"))
    return {
        "requested": intish(fields.get("fwclass_vendor_path_requested")),
        "summary_current": fields.get("fwclass_vendor_path_current", ""),
        "summary_original": fields.get("fwclass_vendor_path_original", ""),
        "summary_read_rc": intish(fields.get("fwclass_vendor_path_current_read_rc")),
        "applied_by_pid1_after_restore": intish(fields.get("fwclass_vendor_path_applied_by_pid1")),
        "vendor_mounted_by_pid1_after_restore": intish(fields.get("fwclass_vendor_path_vendor_mounted_by_pid1")),
        "apply_match": apply_match,
        "restore_seen": restore_seen,
        "restore_match": restore_match,
        "asset_ok": asset_ok,
        "prepare_ok": "fwclass_vendor_path end=1 applied=1" in text,
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    text = prev2132.prev2130.prev2128.read_helper_text()
    fields = prev2132.prev2130.prev2128.parse_fields(text)
    details["fwclass_vendor_path"] = collect_fwclass_vendor_path(fields, text)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    fwclass = details.get("fwclass_vendor_path") if isinstance(details.get("fwclass_vendor_path"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    wlan0 = intish(cascade.get("wlan0")) > 0
    apply_ok = (
        intish(fwclass.get("requested")) == 1
        and bool(fwclass.get("prepare_ok"))
        and bool(fwclass.get("apply_match"))
        and bool(fwclass.get("asset_ok"))
    )
    restore_ok = (
        bool(fwclass.get("restore_seen"))
        and bool(fwclass.get("restore_match"))
        and intish(fwclass.get("summary_read_rc")) == 0
        and str(fwclass.get("summary_current") or "") == str(fwclass.get("summary_original") or "")
        and intish(fwclass.get("applied_by_pid1_after_restore")) == 0
        and intish(fwclass.get("vendor_mounted_by_pid1_after_restore")) == 0
    )

    label = str(base.get("label", "fwclass-vendor-path-unknown"))
    passed = bool(base.get("pass"))
    reason = str(base.get("reason", "classification unavailable"))

    if not base.get("hook_ok"):
        label = "fwclass-vendor-path-artifact-regression"
        passed = False
        reason = "V2133 artifact did not contain the firmware_class vendor-path bridge contract"
    elif not apply_ok:
        label = "fwclass-vendor-path-apply-failed"
        passed = False
        reason = "PID1 did not prove read-only sda29 vendor assets plus firmware_class.path=/mnt/vendor/firmware apply/readback"
    elif not restore_ok:
        label = "fwclass-vendor-path-restore-failed"
        passed = False
        reason = "PID1 did not prove firmware_class.path restore and /mnt/vendor cleanup after the supervised helper"
    elif wlan0:
        label = "fwclass-vendor-path-wlan0-progress"
        passed = True
        reason = "V2133 bridge allowed the post-FW_READY driver-start path to reach wlan0; stop before credentials and run the dedicated connectivity gate"
    elif base.get("stack_request_firmware") and base.get("stack_qdf_ini_parse"):
        label = "fwclass-vendor-path-still-qdf-ini-no-wlan0"
        passed = True
        reason = "kernel QCACLD probe still blocked in request_firmware -> qdf_ini_parse despite global firmware_class.path=/mnt/vendor/firmware"
    elif base.get("probe_returned_without_driver"):
        label = "fwclass-vendor-path-advanced-past-ini-no-wlan0"
        passed = True
        reason = "the INI request stack disappeared, but REGISTER_DRIVER still returned without DRIVER_PROBED or wlan0"
    else:
        label = "fwclass-vendor-path-no-new-register-progress"
        passed = bool(base.get("pass"))
        reason = "firmware_class bridge was applied and restored, but the existing post-FW_READY register/probe state did not advance"

    return {
        **base,
        "decision": f"v2134-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "fwclass_apply_ok": apply_ok,
        "fwclass_restore_ok": restore_ok,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    trigger = details.get("post_fw_ready_boot_wlan_trigger", {}) if isinstance(details.get("post_fw_ready_boot_wlan_trigger"), dict) else {}
    stats = details.get("icnss_stats_numeric", {}) if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    stack = details.get("icnss_register_probe_stack_sampler", {}) if isinstance(details.get("icnss_register_probe_stack_sampler"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused", {}) if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    fwclass = details.get("fwclass_vendor_path", {}) if isinstance(details.get("fwclass_vendor_path"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2134 Firmware Class Vendor Path Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2134`",
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
                ["fwclass", classification.get("fwclass_apply_ok"), f"restore={classification.get('fwclass_restore_ok')} current={fwclass.get('summary_current')} original={fwclass.get('summary_original')} assets={fwclass.get('asset_ok')}"],
                ["route", classification.get("route_ok"), f"trigger_safe={classification.get('trigger_safe')} early_probe={classification.get('early_probe_state')} returned_no_driver={classification.get('probe_returned_without_driver')}"],
                ["trigger", classification.get("trigger_write_ok"), f"gate={classification.get('trigger_gate_ready')} executed={classification.get('trigger_executed')} reason={classification.get('trigger_reason')} duration_ms={classification.get('trigger_duration_ms')}"],
                ["trigger_pre", "", f"fw_ready_processed={trigger.get('pre_fw_ready_processed')} register_driver={trigger.get('pre_register_driver_posted')}/{trigger.get('pre_register_driver_processed')}"],
                ["early_icnss", "", f"register_driver={classification.get('early_register_driver_posted')}/{classification.get('early_register_driver_processed')} state={classification.get('early_state_line')}"],
                ["long_icnss", "", f"register_driver={classification.get('long_register_driver_posted')}/{classification.get('long_register_driver_processed')} state={classification.get('long_state_line')}"],
                ["stack", classification.get("stack_available"), f"targets={classification.get('stack_target_hits')} request_firmware={classification.get('stack_request_firmware')} qdf_ini={classification.get('stack_qdf_ini_parse')} hdd_ctx={classification.get('stack_hdd_context_create')}"],
                ["focused_msg", "", f"qmi={classification.get('focused_qmi_hits')} msg21={classification.get('focused_saw_msg21')} msg2b={classification.get('focused_saw_msg2b')} msg37={classification.get('focused_saw_msg37')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## ICNSS Stats",
        "",
        markdown_table(["area", "value", "detail"], prev2132.prev2130.prev2128.stats_rows(stats)),
        "",
        "## Stack Sampler",
        "",
        markdown_table(["phase", "value", "detail"], prev2132.stack_rows(stack)),
        "",
        "## Stack Samples",
        "",
        *prev2132.stack_sample_lines(stack),
        "",
        "## Target Stack Evidence",
        "",
        *target_stack_lines(stack),
        "",
        "## Focused Indication",
        "",
        markdown_table(["edge", "hits", "detail"], prev2132.prev2130.prev2128.focused_rows(focused)),
        "",
        "## Interpretation",
        "",
        "- V2134 tests the concrete V2132 source gap: kernel-worker `request_firmware()` used the global `firmware_class.path`, while V2132 only exposed `sda29` vendor firmware inside the helper namespace.",
        "- The V2133 PID1 bridge mounts `sda29` read-only at `/mnt/vendor`, switches `firmware_class.path` to `/mnt/vendor/firmware`, proves the Wi-Fi INI/BDF/regdb assets, then restores the original path after the supervised helper.",
        "- If `request_firmware -> qdf_ini_parse` remains in the stack, the next unit must inspect the exact kernel firmware request name/error rather than reworking AP-side producer captures.",
        "- If `wlan0` appears, this handoff intentionally stops before scan/connect/credentials; connectivity belongs in a separate gate.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, tracefs write, sysrq, module load/unload, or driver bind/unbind was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: V2133 rollbackable test-boot flash-handoff, read-only `sda29` mount at `/mnt/vendor`, one temporary `firmware_class.path` sysfs write with restore proof, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, read-only `/proc`/debugfs snapshots, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def target_stack_lines(stack: dict[str, Any]) -> list[str]:
    phases = stack.get("phases", {}) if isinstance(stack.get("phases"), dict) else {}
    lines: list[str] = []
    for phase in prev2132.STACK_PHASES:
        phase_data = phases.get(phase, {}) if isinstance(phases.get(phase), dict) else {}
        for row in phase_data.get("sample_rows", []):
            if not isinstance(row, dict) or intish(row.get("target")) <= 0:
                continue
            stack_preview = " | ".join(row.get("stack_lines", [])[:8])
            if len(stack_preview) > 640:
                stack_preview = stack_preview[:637] + "..."
            lines.append(
                f"- `{phase}` pid `{row.get('pid')}` comm `{row.get('comm')}` "
                f"wchan `{row.get('wchan')}` stack `{stack_preview or 'missing'}`"
            )
    return lines or ["- `none`"]


def configure() -> None:
    prev2132.CYCLE = CYCLE
    prev2132.OUT_DIR = OUT_DIR
    prev2132.HANDOFF_DIR = HANDOFF_DIR
    prev2132.HANDOFF_REPORT = HANDOFF_REPORT
    prev2132.REPORT_PATH = REPORT_PATH
    prev2132.V2131_OUT = V2133_OUT
    prev2132.V2131_INIT = V2133_INIT
    prev2132.V2131_BOOT = V2133_BOOT
    prev2132.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2132.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2132.TEST_LOG_PATH = TEST_LOG_PATH
    prev2132.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2132.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2132.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2132.artifact_hook_check = artifact_hook_check
    prev2132.collect_details = collect_details
    prev2132.classify = classify
    prev2132.render_report = render_report
    prev2132.configure()


def main(argv: list[str] | None = None) -> int:
    configure()
    return prev2132.prev2130.prev2128.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
