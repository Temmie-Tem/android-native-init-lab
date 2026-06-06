#!/usr/bin/env python3
"""V2136 rollbackable handoff for firmware_class fallback-request sampling."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_fwclass_vendor_path_handoff_v2134 as prev2134


CYCLE = "V2136"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2136-firmware-class-fallback-handoff"
HANDOFF_DIR = OUT_DIR / "v2135-handoff"
HANDOFF_REPORT = OUT_DIR / "v2135-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2136_FIRMWARE_CLASS_FALLBACK_HANDOFF_2026-06-05.md"
)
V2135_OUT = REPO_ROOT / "tmp" / "wifi" / "v2135-firmware-class-fallback-test-boot"
V2135_INIT = V2135_OUT / "init_v2135_firmware_class_fallback"
V2135_BOOT = V2135_OUT / "boot_linux_v2135_firmware_class_fallback.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2135/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.242 (v2135-firmware-class-fallback)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2135.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2135.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2135-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v425"
SAMPLER_PHASES = prev2134.prev2132.STACK_PHASES

ORIGINAL_CLASSIFY = prev2134.classify
ORIGINAL_COLLECT_DETAILS = prev2134.collect_details


def intish(value: object) -> int:
    return prev2134.intish(value)


def rel(path: Path) -> str:
    return prev2134.rel(path)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2134.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2135",
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
        "firmware_class_fallback_sampler",
        "read-only-sysfs-firmware-fallback-sampler",
        "no_sysfs_write=1",
        "no_firmware_write=1",
        "no_partition_write=1",
        "skipped-data-node",
        "/sys/class/firmware",
        "/sys/devices/virtual/firmware",
        "/sys/module/firmware_class/parameters/path",
        "fwclass_path.value",
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
    for path, required in ((V2135_INIT, init_required), (V2135_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2135_INIT else boot_forbidden
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


def collect_firmware_class_fallback(fields: dict[str, str]) -> dict[str, Any]:
    phases: dict[str, Any] = {}
    total_entries = 0
    total_interesting = 0
    total_emitted = 0
    safe_phases = 0
    interesting_rows: list[dict[str, Any]] = []
    for phase in SAMPLER_PHASES:
        prefix = f"firmware_class_fallback_sampler.{phase}."
        phase_data: dict[str, Any] = {
            "begin": intish(fields.get(prefix + "begin")),
            "mode": fields.get(prefix + "mode", ""),
            "no_sysfs_write": intish(fields.get(prefix + "no_sysfs_write")),
            "no_firmware_write": intish(fields.get(prefix + "no_firmware_write")),
            "no_partition_write": intish(fields.get(prefix + "no_partition_write")),
            "no_tracefs_write": intish(fields.get(prefix + "no_tracefs_write")),
            "no_wifi_hal": intish(fields.get(prefix + "no_wifi_hal")),
            "scan_connect": intish(fields.get(prefix + "scan_connect")),
            "credentials": intish(fields.get(prefix + "credentials")),
            "dhcp_routing": intish(fields.get(prefix + "dhcp_routing")),
            "external_ping": intish(fields.get(prefix + "external_ping")),
            "fwclass_path_rc": intish(fields.get(prefix + "fwclass_path.rc")),
            "fwclass_path_errno": intish(fields.get(prefix + "fwclass_path.errno")),
            "fwclass_path_value": fields.get(prefix + "fwclass_path.value", ""),
            "timeout_rc": intish(fields.get(prefix + "timeout.rc")),
            "timeout_errno": intish(fields.get(prefix + "timeout.errno")),
            "timeout_value": fields.get(prefix + "timeout.value", ""),
            "entries": intish(fields.get(prefix + "entries")),
            "emitted": intish(fields.get(prefix + "emitted")),
            "interesting": intish(fields.get(prefix + "interesting")),
            "roots": {},
        }
        phase_data["safe"] = (
            phase_data["begin"] == 1
            and phase_data["mode"] == "read-only-sysfs-firmware-fallback-sampler"
            and phase_data["no_sysfs_write"] == 1
            and phase_data["no_firmware_write"] == 1
            and phase_data["no_partition_write"] == 1
            and phase_data["no_tracefs_write"] == 1
            and phase_data["no_wifi_hal"] == 1
            and phase_data["scan_connect"] == 0
            and phase_data["credentials"] == 0
            and phase_data["dhcp_routing"] == 0
            and phase_data["external_ping"] == 0
        )
        if phase_data["safe"]:
            safe_phases += 1
        for root_index in range(2):
            root_prefix = f"{prefix}root_{root_index}."
            root_data: dict[str, Any] = {
                "path": fields.get(root_prefix + "path", ""),
                "entries": intish(fields.get(root_prefix + "entries")),
                "emitted": intish(fields.get(root_prefix + "emitted")),
                "interesting": intish(fields.get(root_prefix + "interesting")),
                "truncated": intish(fields.get(root_prefix + "truncated")),
                "rows": [],
            }
            rows: list[dict[str, Any]] = []
            for entry_index in range(80):
                entry_prefix = f"{root_prefix}entry_{entry_index:02d}."
                if entry_prefix + "path" not in fields:
                    continue
                row = {
                    "phase": phase,
                    "root": root_index,
                    "index": entry_index,
                    "path": fields.get(entry_prefix + "path", ""),
                    "basename": fields.get(entry_prefix + "basename", ""),
                    "depth": intish(fields.get(entry_prefix + "depth")),
                    "type": fields.get(entry_prefix + "type", ""),
                    "mode": fields.get(entry_prefix + "mode", ""),
                    "interesting": intish(fields.get(entry_prefix + "interesting")),
                    "read_rc": intish(fields.get(entry_prefix + "read.rc")),
                    "read_errno": intish(fields.get(entry_prefix + "read.errno")),
                    "preview": fields.get(entry_prefix + "preview", ""),
                    "readlink": fields.get(entry_prefix + "readlink", ""),
                }
                rows.append(row)
                if intish(row["interesting"]) > 0:
                    interesting_rows.append(row)
            root_data["rows"] = rows
            phase_data["roots"][root_index] = root_data
        phases[phase] = phase_data
        total_entries += intish(phase_data["entries"])
        total_emitted += intish(phase_data["emitted"])
        total_interesting += intish(phase_data["interesting"])
    return {
        "phases": phases,
        "entries": total_entries,
        "emitted": total_emitted,
        "interesting": total_interesting,
        "safe_phases": safe_phases,
        "all_safe": safe_phases == len(SAMPLER_PHASES),
        "interesting_rows": interesting_rows,
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    text = prev2134.prev2132.prev2130.prev2128.read_helper_text()
    fields = prev2134.prev2132.prev2130.prev2128.parse_fields(text)
    details["firmware_class_fallback_sampler"] = collect_firmware_class_fallback(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    sampler = details.get("firmware_class_fallback_sampler") if isinstance(details.get("firmware_class_fallback_sampler"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    sampler_safe = bool(sampler.get("all_safe"))
    interesting_count = intish(sampler.get("interesting"))
    wlan0 = intish(cascade.get("wlan0")) > 0
    stack_request_firmware = bool(base.get("stack_request_firmware"))
    stack_qdf_ini_parse = bool(base.get("stack_qdf_ini_parse"))

    label = str(base.get("label", "firmware-class-fallback-unknown"))
    passed = bool(base.get("pass"))
    reason = str(base.get("reason", "classification unavailable"))

    if not base.get("hook_ok"):
        label = "firmware-class-fallback-artifact-regression"
        passed = False
        reason = "V2135 artifact did not contain the v425 firmware-class fallback sampler contract"
    elif not base.get("fwclass_apply_ok"):
        label = "firmware-class-fallback-fwclass-apply-failed"
        passed = False
        reason = "PID1 did not apply/read back the V2133 firmware_class vendor path bridge"
    elif not base.get("fwclass_restore_ok"):
        label = "firmware-class-fallback-fwclass-restore-failed"
        passed = False
        reason = "PID1 did not restore firmware_class.path and cleanup /mnt/vendor"
    elif not sampler_safe:
        label = "firmware-class-fallback-sampler-missing-or-unsafe"
        passed = False
        reason = "firmware_class fallback sampler did not prove the read-only safety contract in both windows"
    elif wlan0:
        label = "firmware-class-fallback-wlan0-progress"
        passed = True
        reason = "post-FW_READY driver-start path reached wlan0; stop before credentials and run the dedicated connectivity gate"
    elif stack_request_firmware and stack_qdf_ini_parse and interesting_count > 0:
        label = "firmware-class-request-entry-captured-still-qdf-ini"
        passed = True
        reason = "QCACLD remained in request_firmware -> qdf_ini_parse and firmware_class sysfs exposed a matching fallback request entry"
    elif stack_request_firmware and stack_qdf_ini_parse:
        label = "firmware-class-no-fallback-entry-still-qdf-ini"
        passed = True
        reason = "QCACLD remained in request_firmware -> qdf_ini_parse but no firmware_class fallback request entry was visible; next gate is the qdf_file_read argument"
    elif base.get("probe_returned_without_driver"):
        label = "firmware-class-fallback-probe-returned-no-wlan0"
        passed = True
        reason = "register-driver probe returned without wlan0 and without a visible firmware_class fallback request entry at sample time"

    return {
        **base,
        "decision": f"v2136-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "firmware_class_sampler_safe": sampler_safe,
        "firmware_class_interesting": interesting_count,
        "firmware_class_entries": intish(sampler.get("entries")),
        "firmware_class_safe_phases": intish(sampler.get("safe_phases")),
    }


def firmware_class_rows(sampler: dict[str, Any]) -> list[list[object]]:
    phases = sampler.get("phases", {}) if isinstance(sampler.get("phases"), dict) else {}
    rows: list[list[object]] = []
    for phase in SAMPLER_PHASES:
        data = phases.get(phase, {}) if isinstance(phases.get(phase), dict) else {}
        rows.append([
            phase,
            f"safe={data.get('safe')} entries={data.get('entries')} interesting={data.get('interesting')}",
            f"path={data.get('fwclass_path_value')} timeout={data.get('timeout_value')} emitted={data.get('emitted')}",
        ])
    return rows


def firmware_class_entry_lines(sampler: dict[str, Any]) -> list[str]:
    rows = sampler.get("interesting_rows", []) if isinstance(sampler.get("interesting_rows"), list) else []
    lines: list[str] = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        preview = str(row.get("preview") or row.get("readlink") or "")
        if len(preview) > 240:
            preview = preview[:237] + "..."
        lines.append(
            f"- `{row.get('phase')}` root `{row.get('root')}` entry `{row.get('index')}` "
            f"type `{row.get('type')}` path `{row.get('path')}` preview `{preview or 'empty'}` "
            f"read `{row.get('read_rc')}/{row.get('read_errno')}`"
        )
    return lines or ["- `none`"]


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    trigger = details.get("post_fw_ready_boot_wlan_trigger", {}) if isinstance(details.get("post_fw_ready_boot_wlan_trigger"), dict) else {}
    stats = details.get("icnss_stats_numeric", {}) if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    stack = details.get("icnss_register_probe_stack_sampler", {}) if isinstance(details.get("icnss_register_probe_stack_sampler"), dict) else {}
    focused = details.get("wlfw_late_msg21_focused", {}) if isinstance(details.get("wlfw_late_msg21_focused"), dict) else {}
    fwclass = details.get("fwclass_vendor_path", {}) if isinstance(details.get("fwclass_vendor_path"), dict) else {}
    sampler = details.get("firmware_class_fallback_sampler", {}) if isinstance(details.get("firmware_class_fallback_sampler"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2136 Firmware Class Fallback Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2136`",
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
                ["fwclass_path", classification.get("fwclass_apply_ok"), f"restore={classification.get('fwclass_restore_ok')} current={fwclass.get('summary_current')} original={fwclass.get('summary_original')}"],
                ["fallback", classification.get("firmware_class_sampler_safe"), f"entries={classification.get('firmware_class_entries')} interesting={classification.get('firmware_class_interesting')} safe_phases={classification.get('firmware_class_safe_phases')}"],
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
        "## Firmware Class",
        "",
        markdown_table(["phase", "value", "detail"], firmware_class_rows(sampler)),
        "",
        "## Firmware Class Entries",
        "",
        *firmware_class_entry_lines(sampler),
        "",
        "## ICNSS Stats",
        "",
        markdown_table(["area", "value", "detail"], prev2134.prev2132.prev2130.prev2128.stats_rows(stats)),
        "",
        "## Stack Sampler",
        "",
        markdown_table(["phase", "value", "detail"], prev2134.prev2132.stack_rows(stack)),
        "",
        "## Stack Samples",
        "",
        *prev2134.prev2132.stack_sample_lines(stack),
        "",
        "## Target Stack Evidence",
        "",
        *prev2134.target_stack_lines(stack),
        "",
        "## Focused Indication",
        "",
        markdown_table(["edge", "hits", "detail"], prev2134.prev2132.prev2130.prev2128.focused_rows(focused)),
        "",
        "## Interpretation",
        "",
        "- V2136 keeps the V2133 global `firmware_class.path=/mnt/vendor/firmware` bridge and the V2131 QCACLD stack sampler unchanged.",
        "- The only added observer is a bounded read-only enumeration of `/sys/class/firmware` and `/sys/devices/virtual/firmware` in the stuck firmware request window.",
        "- If no fallback entry appears while QCACLD is still in `request_firmware -> qdf_ini_parse`, the exact missing input is not exposed by firmware_class fallback sysfs; capture the `qdf_file_read()` argument next.",
        "- If an entry appears, its path/basename/read status names the next bounded file-path fix target.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No firmware fallback `loading`/`data` writes, tracefs write, sysrq, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, module load/unload, or driver bind/unbind was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: V2135 rollbackable test-boot flash-handoff, read-only `sda29` mount at `/mnt/vendor`, one temporary `firmware_class.path` sysfs write with restore proof, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, read-only `/proc`/sysfs/debugfs snapshots, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure() -> None:
    prev2134.CYCLE = CYCLE
    prev2134.OUT_DIR = OUT_DIR
    prev2134.HANDOFF_DIR = HANDOFF_DIR
    prev2134.HANDOFF_REPORT = HANDOFF_REPORT
    prev2134.REPORT_PATH = REPORT_PATH
    prev2134.V2133_OUT = V2135_OUT
    prev2134.V2133_INIT = V2135_INIT
    prev2134.V2133_BOOT = V2135_BOOT
    prev2134.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2134.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2134.TEST_LOG_PATH = TEST_LOG_PATH
    prev2134.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2134.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2134.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2134.artifact_hook_check = artifact_hook_check
    prev2134.collect_details = collect_details
    prev2134.classify = classify
    prev2134.render_report = render_report
    prev2134.configure()


def main(argv: list[str] | None = None) -> int:
    configure()
    return prev2134.prev2132.prev2130.prev2128.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
