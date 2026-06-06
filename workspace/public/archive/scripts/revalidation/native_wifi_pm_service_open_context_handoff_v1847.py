#!/usr/bin/env python3
"""V1847 one-run PM-service open-context hit-count handoff."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_service_post_ack_branch_handoff_v1844 as prev1844


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1847"
V1846_OUT = REPO_ROOT / "tmp" / "wifi" / "v1846-pm-service-open-context-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1846/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1847-pm-service-open-context-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1847_PM_SERVICE_OPEN_CONTEXT_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.165 (v1846-pm-service-open-context)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1846.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1846.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1846-helper.result"
DMESG_PATTERN = (
    "A90v1846|pm_service_trigger_observer|wlan_pd_after_holder_start|"
    "wlan_pd_after_post_listener_window|periph_pm_callback|periph_pm_client_ack|"
    "periph_pm_server_ack|periph_pm_server_ontransact|pm_service_ack_impl|"
    "pm_service_post_ack|pcie_1_gdsc|pcie_0_gdsc|GPIO135|GPIO142|"
    "mdm_status|wlan_pd_qipcrtr_bound_recv_poll_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|"
    "pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|"
    "wlan_pd|qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|ext-SDX50M|MHI"
)

OPEN_CONTEXT_KEYS = (
    "pm_service_post_ack_power_state_loaded",
    "pm_service_post_ack_open_context",
    "pm_service_post_ack_open_path_loaded",
    "pm_service_post_ack_open_fd_store",
    "pm_service_post_ack_open_fd_compare",
    "pm_service_post_ack_open_success_counter",
)


def runner() -> Any:
    return prev1844.runner()


def prev1796() -> Any:
    return prev1844.prev1796()


def intish(value: object) -> int:
    return prev1844.intish(value)


def configure_runner() -> None:
    prev1844.CYCLE = CYCLE
    prev1844.V1843_OUT = V1846_OUT
    prev1844.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1844.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1844.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1844.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1844.TEST_LOG_PATH = TEST_LOG_PATH
    prev1844.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1844.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1844.DMESG_PATTERN = DMESG_PATTERN
    prev1844.configure_runner()
    runner().DEFAULT_TEST_IMAGE = V1846_OUT / "boot_linux_v1846_pm_service_open_context.img"


def context_sample(fields: dict[str, str], key: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.pm_server_uprobe.{key}."
    return {
        "key": key,
        "fetch_args": fields.get(prefix + "fetch_args", ""),
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "register_rc": fields.get(prefix + "register_rc", ""),
        "enable_rc": fields.get(prefix + "enable_rc", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "sample_count": fields.get(prefix + "sample_count", ""),
        "sample_line_0": fields.get(prefix + "sample_line_0", ""),
        "sample_line_1": fields.get(prefix + "sample_line_1", ""),
    }


def extract_path(line: str) -> str:
    match = re.search(r'path="([^"]+)"', line)
    return match.group(1) if match else ""


def extract_hex_field(line: str, field: str) -> str:
    match = re.search(rf"{re.escape(field)}=(0x[0-9a-fA-F]+|-?[0-9]+)", line)
    return match.group(1) if match else ""


def collect_context_details(fields: dict[str, str]) -> dict[str, Any]:
    samples = [context_sample(fields, key) for key in OPEN_CONTEXT_KEYS]
    by_key = {sample["key"]: sample for sample in samples}
    hit_keys = [sample["key"] for sample in samples if intish(sample.get("hit_count")) > 0]
    registered_ok = all(sample.get("registered") == "1" for sample in samples)
    enabled_ok = all(sample.get("enabled") == "1" for sample in samples)
    path_line = by_key["pm_service_post_ack_open_path_loaded"].get("sample_line_0", "")
    context_line = by_key["pm_service_post_ack_open_context"].get("sample_line_0", "")
    state_line = by_key["pm_service_post_ack_power_state_loaded"].get("sample_line_0", "")
    fd_line = by_key["pm_service_post_ack_open_fd_store"].get("sample_line_0", "")
    return {
        "open_context_samples": samples,
        "open_context_registered_ok": registered_ok,
        "open_context_enabled_ok": enabled_ok,
        "open_context_contract_ok": registered_ok and enabled_ok,
        "open_context_hit_keys": hit_keys,
        "open_context_hit_count_total": sum(intish(sample.get("hit_count")) for sample in samples),
        "open_context_path": extract_path(path_line),
        "open_context_power_state": extract_hex_field(state_line, "power_state"),
        "open_context_fd": extract_hex_field(fd_line, "open_rc"),
        "open_context_line": context_line,
        "open_context_path_line": path_line,
        "open_context_state_line": state_line,
        "open_context_fd_line": fd_line,
    }


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    base_decision, base_pass, base_reason, details = prev1844.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = runner().fwbase.parse_helper_fields(evidence_dir)
    details.update(collect_context_details(helper_fields))
    if not base_pass:
        return base_decision, base_pass, base_reason, details
    if not details.get("open_context_contract_ok"):
        details["open_context_label"] = "open-context-contract-missing"
        return (
            f"{args.cycle.lower()}-open-context-contract-missing",
            False,
            "PM-service open-context uprobe labels did not all register and enable",
            details,
        )
    if prev1844.prev1841.prev1838.prev1834.actual_publication_progress(details) or bool(details.get("pm_focus_mhi_wlan0_progress")):
        label = "open-context-esoc0-or-powerup-progress"
        reason = "lower publication, MHI/WLFW, or wlan0 progressed under the PM-service open-context observer"
    elif details.get("open_context_path") == "/dev/subsys_esoc0":
        label = "open-context-esoc0-or-powerup-progress"
        reason = "PM-service open context selected /dev/subsys_esoc0; stop before Wi-Fi HAL/scan/connect"
    elif details.get("open_context_path") == "/dev/subsys_modem" and intish(details.get("open_context_fd")) >= 0:
        label = "open-context-modem-success-static"
        reason = "PM-service open context confirmed /dev/subsys_modem success while lower SDX50M/eSoC state stayed static"
    elif intish(details.get("open_context_hit_count_total")) > 0:
        label = "open-context-other-static"
        reason = "PM-service open context labels fired, but the open path/fd combination did not match the fixed modem-success classifier"
    else:
        label = "open-context-no-hit"
        reason = "PM-service open-context labels registered but did not fire in the current route"
    details["open_context_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_samples(samples: list[dict[str, str]]) -> list[str]:
    return [
        f"- `{sample.get('key')}` registered/enabled/hits: `{sample.get('registered')}` / `{sample.get('enabled')}` / `{sample.get('hit_count')}` first=`{sample.get('first_hit_line')}`"
        for sample in samples
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    post = result.get("post_rollback_verification", {})
    lines = [
        "# Native Init V1847 PM-Service Open-Context Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1847`",
        "- Type: one-run rollbackable PM-service open-context discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
    ]
    if post:
        lines.extend([
            f"- Post-rollback version ok: `{post.get('version_ok')}`",
            f"- Post-rollback selftest fail=0: `{post.get('selftest_fail_zero')}`",
            f"- Post-rollback version evidence: `{post.get('version_stdout_file')}`",
            f"- Post-rollback selftest evidence: `{post.get('selftest_stdout_file')}`",
        ])
    lines.extend([
        "",
        "## Gate Label",
        "",
        f"- open-context label: `{gate.get('open_context_label')}`",
        f"- open-context registered/enabled: `{gate.get('open_context_registered_ok')}` / `{gate.get('open_context_enabled_ok')}`",
        f"- open-context hit total: `{gate.get('open_context_hit_count_total')}`",
        f"- open-context hit keys: `{gate.get('open_context_hit_keys')}`",
        f"- open-context path/state/fd: `{gate.get('open_context_path')}` / `{gate.get('open_context_power_state')}` / `{gate.get('open_context_fd')}`",
        f"- post-ack label/total: `{gate.get('post_ack_label')}` / `{gate.get('post_ack_hit_count_total')}`",
        f"- callback/ack label/total: `{gate.get('callback_ack_label')}` / `{gate.get('callback_ack_hit_count_total')}`",
        f"- lower-continuation label: `{gate.get('lower_continuation_label')}`",
        f"- PM focus change fields / mdm-status delta: `{gate.get('pm_focus_change_fields')}` / `{gate.get('pm_focus_mdm_status_delta')}`",
        f"- PM focus MHI/wlan0 progress: `{gate.get('pm_focus_mhi_wlan0_progress')}`",
        f"- service-notifier / QIPCRTR labels: `{gate.get('servnotif_label')}` / `{gate.get('qipcrtr_bound_recv_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Open-Context Hits",
        "",
        *render_samples(gate.get("open_context_samples", [])),
        "",
        "## Key Lines",
        "",
        f"- state line: `{gate.get('open_context_state_line')}`",
        f"- context line: `{gate.get('open_context_line')}`",
        f"- path line: `{gate.get('open_context_path_line')}`",
        f"- fd line: `{gate.get('open_context_fd_line')}`",
        "",
        "## Lower State",
        "",
        f"- mdm3/MHI/WLFW69/wlan0: `{gate.get('lower_mdm3_states')}` / `{gate.get('lower_mhi_present')}` / `{gate.get('lower_service69_progress')}` / `{gate.get('lower_wlan0_present')}`",
        f"- service180/service74/wlan_pd raw: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- PM-client register/connect/return-path rc: `{gate.get('pm_client_register_rc')}` / `{gate.get('pm_client_connect_rc')}` / `{gate.get('pm_init_return_path_rc')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- Uploaded files/bytes: `{property_deploy.get('file_count')}` / `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- The new V1847 surface only adds read-only `pm-service` open-context uprobe hit counts on the V1846 test boot image.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- If `/dev/subsys_modem` success is confirmed again, the next safe step is host-only/source classification of CNSS PM peripheral selection versus the SDX50M record.",
        "",
    ])
    return "\n".join(lines)


def record_post_rollback_verification() -> dict[str, Any]:
    out_dir = DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    base = runner().fwbase.base
    version_result = base.run_command(
        [
            "bash",
            "-o",
            "pipefail",
            "-lc",
            "python3 scripts/revalidation/a90ctl.py version 2>&1 | sed '/made by /d'",
        ],
        timeout=60.0,
    )
    selftest_result = base.run_command(base.a90ctl_command(["selftest"]), timeout=60.0)
    version_stdout = str(version_result.get("stdout") or "")
    version_stderr = str(version_result.get("stderr") or "")
    selftest_stdout = str(selftest_result.get("stdout") or "")
    selftest_stderr = str(selftest_result.get("stderr") or "")
    (out_dir / "post-rollback-version-filtered.stdout.txt").write_text(version_stdout, encoding="utf-8")
    (out_dir / "post-rollback-version-filtered.stderr.txt").write_text(version_stderr, encoding="utf-8")
    (out_dir / "post-rollback-selftest.stdout.txt").write_text(selftest_stdout, encoding="utf-8")
    (out_dir / "post-rollback-selftest.stderr.txt").write_text(selftest_stderr, encoding="utf-8")
    return {
        "version_ok": "A90 Linux init 0.9.68 (v724)" in (version_stdout + "\n" + version_stderr),
        "selftest_fail_zero": "fail=0" in (selftest_stdout + "\n" + selftest_stderr),
        "version_stdout_file": str((out_dir / "post-rollback-version-filtered.stdout.txt").relative_to(REPO_ROOT)),
        "selftest_stdout_file": str((out_dir / "post-rollback-selftest.stdout.txt").relative_to(REPO_ROOT)),
        "version_rc": version_result.get("rc"),
        "selftest_rc": selftest_result.get("rc"),
    }


def update_manifest_with_post_verification(post: dict[str, Any]) -> int:
    manifest_path = DEFAULT_OUT_DIR / "manifest.json"
    if not manifest_path.exists():
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["post_rollback_verification"] = post
    if not post.get("version_ok") or not post.get("selftest_fail_zero"):
        manifest["pass"] = False
        manifest["decision"] = f"{CYCLE.lower()}-post-rollback-verification-failed"
        manifest["reason"] = "post-rollback filtered version or selftest fail=0 verification failed"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (DEFAULT_OUT_DIR / "summary.md").write_text(render_report(manifest), encoding="utf-8")
    DEFAULT_REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    return 0 if manifest.get("pass") else 1


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    base = runner()
    base.deploy_property_root = prev1796().deploy_property_root_serial
    base.classify_gate = classify_gate
    base.render_report = render_report
    rc = base.main(argv)
    post = record_post_rollback_verification()
    post_rc = update_manifest_with_post_verification(post)
    prev1796().sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc or post_rc


if __name__ == "__main__":
    raise SystemExit(main())
