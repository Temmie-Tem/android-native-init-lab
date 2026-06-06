#!/usr/bin/env python3
"""V2132 rollbackable handoff for ICNSS register-probe stack sampling."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_post_fw_ready_boot_wlan_handoff_v2130 as prev2130


CYCLE = "V2132"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2132-icnss-register-probe-stack-handoff"
HANDOFF_DIR = OUT_DIR / "v2131-handoff"
HANDOFF_REPORT = OUT_DIR / "v2131-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2132_ICNSS_REGISTER_PROBE_STACK_HANDOFF_2026-06-05.md"
)
V2131_OUT = REPO_ROOT / "tmp" / "wifi" / "v2131-icnss-register-probe-stack-test-boot"
V2131_INIT = V2131_OUT / "init_v2131_icnss_register_probe_stack"
V2131_BOOT = V2131_OUT / "boot_linux_v2131_icnss_register_probe_stack.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2131/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.240 (v2131-icnss-register-probe-stack)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2131.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2131.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2131-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v424"
STACK_PHASES = ("after_boot_wlan_trigger", "after_boot_wlan_long_window")

BASE_COLLECT_DETAILS = prev2130.collect_details
BASE_CLASSIFY = prev2130.classify


def intish(value: object) -> int:
    return prev2130.intish(value)


def rel(path: Path) -> str:
    return prev2130.rel(path)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2130.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2131",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
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
    for path, required in ((V2131_INIT, init_required), (V2131_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2131_INIT else boot_forbidden
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


def collect_stack_sampler(fields: dict[str, str]) -> dict[str, Any]:
    phases: dict[str, Any] = {}
    total_targets = 0
    total_samples = 0
    total_stack_ok = 0
    total_stack_fail = 0
    for phase in STACK_PHASES:
        prefix = f"icnss_register_probe_stack_sampler.{phase}."
        phase_data: dict[str, Any] = {
            "begin": intish(fields.get(prefix + "begin")),
            "proc_open_rc": intish(fields.get(prefix + "proc_open.rc")),
            "scanned": intish(fields.get(prefix + "scanned")),
            "candidates": intish(fields.get(prefix + "candidates")),
            "stack_open_ok": intish(fields.get(prefix + "stack_open_ok")),
            "stack_open_fail": intish(fields.get(prefix + "stack_open_fail")),
            "target_hits": intish(fields.get(prefix + "target_hits")),
            "fallback_samples": intish(fields.get(prefix + "fallback_samples")),
            "samples": intish(fields.get(prefix + "samples")),
            "workqueue_rc": intish(fields.get(prefix + "workqueue_stats.rc")),
            "workqueue_errno": intish(fields.get(prefix + "workqueue_stats.errno")),
            "workqueue_has_icnss": intish(fields.get(prefix + "workqueue_stats.has_icnss")),
            "workqueue_preview": fields.get(prefix + "workqueue_stats.preview", ""),
            "sample_rows": [],
        }
        rows: list[dict[str, Any]] = []
        for index in range(14):
            sample_prefix = f"{prefix}sample_{index:02d}."
            if sample_prefix + "pid" not in fields:
                continue
            stack_lines = [
                fields.get(sample_prefix + f"stack_{line_index:02d}", "")
                for line_index in range(8)
                if fields.get(sample_prefix + f"stack_{line_index:02d}", "")
            ]
            rows.append({
                "pid": fields.get(sample_prefix + "pid", ""),
                "comm": fields.get(sample_prefix + "comm", ""),
                "candidate": intish(fields.get(sample_prefix + "candidate")),
                "target": intish(fields.get(sample_prefix + "target")),
                "wchan": fields.get(sample_prefix + "wchan", ""),
                "stack_open": intish(fields.get(sample_prefix + "stack_open")),
                "stack_errno": intish(fields.get(sample_prefix + "stack_errno")),
                "stack_line_count": intish(fields.get(sample_prefix + "stack_line_count")),
                "stack_lines": stack_lines,
            })
        phase_data["sample_rows"] = rows
        phases[phase] = phase_data
        total_targets += intish(phase_data["target_hits"])
        total_samples += intish(phase_data["samples"])
        total_stack_ok += intish(phase_data["stack_open_ok"])
        total_stack_fail += intish(phase_data["stack_open_fail"])
    return {
        "phases": phases,
        "target_hits": total_targets,
        "samples": total_samples,
        "stack_open_ok": total_stack_ok,
        "stack_open_fail": total_stack_fail,
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2130.prev2128.parse_fields(prev2130.prev2128.read_helper_text())
    details["icnss_register_probe_stack_sampler"] = collect_stack_sampler(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    stats = details.get("icnss_stats_numeric") if isinstance(details.get("icnss_stats_numeric"), dict) else {}
    stack = details.get("icnss_register_probe_stack_sampler") if isinstance(details.get("icnss_register_probe_stack_sampler"), dict) else {}
    max_values = stats.get("max", {}) if isinstance(stats.get("max"), dict) else {}
    phases = stats.get("phases", {}) if isinstance(stats.get("phases"), dict) else {}
    early_phase = phases.get("after_boot_wlan_trigger", {}) if isinstance(phases.get("after_boot_wlan_trigger"), dict) else {}
    long_phase = phases.get("after_boot_wlan_long_window", {}) if isinstance(phases.get("after_boot_wlan_long_window"), dict) else {}
    early_state_line = str(early_phase.get("state_line") or "")
    long_state_line = str(long_phase.get("state_line") or stats.get("state_line") or base.get("icnss_state_line") or "")
    register_driver_posted = intish(max_values.get("event.register_driver.posted"))
    register_driver_processed = intish(max_values.get("event.register_driver.processed"))
    early_register_driver_posted = intish(early_phase.get("event.register_driver.posted"))
    early_register_driver_processed = intish(early_phase.get("event.register_driver.processed"))
    long_register_driver_posted = intish(long_phase.get("event.register_driver.posted"))
    long_register_driver_processed = intish(long_phase.get("event.register_driver.processed"))
    early_probe_state = (
        early_register_driver_posted > 0
        and early_register_driver_processed <= 0
        and "POWER ON" in early_state_line
        and "BLOCK SHUTDOWN" in early_state_line
        and "DRIVER PROBED" not in early_state_line
    )
    driver_probed_late = "DRIVER PROBED" in long_state_line
    wlan0 = intish(cascade.get("wlan0")) > 0
    stack_target_hits = intish(stack.get("target_hits"))
    stack_available = intish(stack.get("stack_open_ok")) > 0
    stack_symbols: set[str] = set()
    stack_phases = stack.get("phases", {}) if isinstance(stack.get("phases"), dict) else {}
    for phase_data in stack_phases.values():
        if not isinstance(phase_data, dict):
            continue
        for row in phase_data.get("sample_rows", []):
            if not isinstance(row, dict):
                continue
            for line in row.get("stack_lines", []):
                if isinstance(line, str):
                    stack_symbols.add(line)
    stack_request_firmware = any("request_firmware" in line or "_request_firmware" in line for line in stack_symbols)
    stack_qdf_ini_parse = any("qdf_ini_parse" in line for line in stack_symbols)
    stack_hdd_context_create = any("hdd_context_create" in line for line in stack_symbols)
    stack_wlan_hdd_pld_probe = any("wlan_hdd_pld_probe" in line for line in stack_symbols)
    probe_returned_without_driver = (
        register_driver_processed > 0
        and not driver_probed_late
        and not wlan0
    )

    label = str(base.get("label", "icnss-register-probe-stack-unknown"))
    passed = bool(base.get("pass"))
    reason = str(base.get("reason", "classification unavailable"))
    if not base.get("hook_ok"):
        label = "icnss-register-probe-stack-artifact-regression"
        passed = False
        reason = "V2131 artifact did not contain the v424 stack sampler contract"
    elif not base.get("route_ok"):
        label = "icnss-register-probe-stack-route-regression"
        passed = False
        reason = "V2132 did not preserve the V2130 route prerequisites"
    elif not bool(base.get("trigger_write_ok")):
        label = "icnss-register-probe-stack-trigger-not-written"
        passed = bool(base.get("pass"))
        reason = "post-FW_READY boot_wlan trigger did not complete, so probe-stack classification is not applicable"
    elif register_driver_processed > 0 and wlan0:
        label = "icnss-register-probe-stack-wlan0-progress"
        passed = True
        reason = "REGISTER_DRIVER processed and wlan0 appeared; stop before credentials and run connectivity gate"
    elif probe_returned_without_driver and stack_request_firmware and stack_qdf_ini_parse:
        label = "icnss-register-probe-qdf-ini-firmware-request-no-wlan0"
        passed = True
        reason = "REGISTER_DRIVER processed after the early stack caught QCACLD probe in request_firmware -> qdf_ini_parse, then returned without DRIVER_PROBED or wlan0"
    elif probe_returned_without_driver and stack_target_hits > 0:
        label = "icnss-register-probe-stack-target-returned-no-wlan0"
        passed = True
        reason = "REGISTER_DRIVER processed after the early stack caught QCACLD probe symbols, then returned without DRIVER_PROBED or wlan0"
    elif register_driver_processed > 0:
        label = "icnss-register-probe-stack-register-processed-no-wlan0"
        passed = True
        reason = "REGISTER_DRIVER processed during the long window, but wlan0 did not appear"
    elif early_probe_state and stack_target_hits > 0:
        label = "icnss-register-probe-handler-stuck-stack-target"
        passed = True
        reason = "early state is POWER ON | BLOCK SHUTDOWN with REGISTER_DRIVER 1/0, and stack sampler found target probe symbols"
    elif early_probe_state and stack_available:
        label = "icnss-register-probe-handler-stuck-no-target-stack"
        passed = True
        reason = "early state is POWER ON | BLOCK SHUTDOWN with REGISTER_DRIVER 1/0; stacks were readable but no target symbol was captured"
    elif early_probe_state:
        label = "icnss-register-probe-handler-stuck-stack-unavailable"
        passed = True
        reason = "early state is POWER ON | BLOCK SHUTDOWN with REGISTER_DRIVER 1/0; /proc stack symbols were unavailable"

    return {
        **base,
        "decision": f"v2132-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "source_probe_state": early_probe_state,
        "early_probe_state": early_probe_state,
        "probe_returned_without_driver": probe_returned_without_driver,
        "driver_probed_late": driver_probed_late,
        "stack_target_hits": stack_target_hits,
        "stack_available": stack_available,
        "stack_request_firmware": stack_request_firmware,
        "stack_qdf_ini_parse": stack_qdf_ini_parse,
        "stack_hdd_context_create": stack_hdd_context_create,
        "stack_wlan_hdd_pld_probe": stack_wlan_hdd_pld_probe,
        "early_register_driver_posted": early_register_driver_posted,
        "early_register_driver_processed": early_register_driver_processed,
        "early_state_line": early_state_line,
        "long_register_driver_posted": long_register_driver_posted,
        "long_register_driver_processed": long_register_driver_processed,
        "long_state_line": long_state_line,
    }


def stack_rows(stack: dict[str, Any]) -> list[list[object]]:
    phases = stack.get("phases", {}) if isinstance(stack.get("phases"), dict) else {}
    rows: list[list[object]] = []
    for phase in STACK_PHASES:
        data = phases.get(phase, {}) if isinstance(phases.get(phase), dict) else {}
        rows.append([
            phase,
            f"targets={data.get('target_hits')} samples={data.get('samples')}",
            f"scanned={data.get('scanned')} candidates={data.get('candidates')} stack={data.get('stack_open_ok')}/{data.get('stack_open_fail')} wq_icnss={data.get('workqueue_has_icnss')} errno={data.get('workqueue_errno')}",
        ])
    return rows


def stack_sample_lines(stack: dict[str, Any]) -> list[str]:
    phases = stack.get("phases", {}) if isinstance(stack.get("phases"), dict) else {}
    lines: list[str] = []
    for phase in STACK_PHASES:
        data = phases.get(phase, {}) if isinstance(phases.get(phase), dict) else {}
        for row in data.get("sample_rows", [])[:6]:
            stack_preview = " | ".join(row.get("stack_lines", [])[:8])
            if len(stack_preview) > 520:
                stack_preview = stack_preview[:517] + "..."
            lines.append(
                f"- `{phase}` pid `{row.get('pid')}` comm `{row.get('comm')}` "
                f"target `{row.get('target')}` wchan `{row.get('wchan')}` stack `{stack_preview or 'missing'}`"
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
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2132 ICNSS Register-Probe Stack Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2132`",
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
        markdown_table(["area", "value", "detail"], prev2130.prev2128.stats_rows(stats)),
        "",
        "## Stack Sampler",
        "",
        markdown_table(["phase", "value", "detail"], stack_rows(stack)),
        "",
        "## Stack Samples",
        "",
        *stack_sample_lines(stack),
        "",
        "## Focused Indication",
        "",
        markdown_table(["edge", "hits", "detail"], prev2130.prev2128.focused_rows(focused)),
        "",
        "## Interpretation",
        "",
        "- Source finding: ICNSS increments `REGISTER_DRIVER.processed` only after `icnss_driver_event_register_driver()` returns.",
        "- V2132 keeps the V2130 post-FW_READY `boot_wlan` trigger and adds only read-only stack/workqueue/late ICNSS stats snapshots.",
        "- Early `POWER ON | BLOCK SHUTDOWN` with `REGISTER_DRIVER=1/0` means the event worker entered the register/probe handler.",
        "- The captured target stack localizes that handler to QCACLD startup: `request_firmware -> qdf_file_read -> qdf_ini_parse -> cfg_parse -> hdd_context_create -> wlan_hdd_pld_probe`.",
        "- Source cross-check: `WLAN_INI_FILE` resolves to `wlan/qca_cld/WCNSS_qcom_cfg.ini` on `MSM_PLATFORM`, and `hdd_context_create()` fails out if `cfg_parse(WLAN_INI_FILE)` returns an error.",
        "- The long-window ICNSS snapshot shows `REGISTER_DRIVER=1/1` but no `DRIVER PROBED` state and no `wlan0`, so the probe returned without successful driver registration.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2131 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, read-only `/proc`/debugfs snapshots, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure() -> None:
    prev2130.CYCLE = CYCLE
    prev2130.OUT_DIR = OUT_DIR
    prev2130.HANDOFF_DIR = HANDOFF_DIR
    prev2130.HANDOFF_REPORT = HANDOFF_REPORT
    prev2130.REPORT_PATH = REPORT_PATH
    prev2130.V2129_OUT = V2131_OUT
    prev2130.V2129_INIT = V2131_INIT
    prev2130.V2129_BOOT = V2131_BOOT
    prev2130.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2130.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2130.TEST_LOG_PATH = TEST_LOG_PATH
    prev2130.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2130.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2130.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2130.configure()
    prev2130.prev2128.ICNSS_STATS_PHASES = (
        "after_boot_wlan_long_window",
        "after_boot_wlan_trigger",
        "after_post_listener_window",
        "after_early_listener",
        "after_holder_start",
    )
    prev2130.prev2128.artifact_hook_check = artifact_hook_check
    prev2130.prev2128.collect_details = collect_details
    prev2130.prev2128.classify = classify
    prev2130.prev2128.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure()
    return prev2130.prev2128.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
