#!/usr/bin/env python3
"""V1844 one-run PM-service post-ack branch hit-count handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_pm_callback_ack_current_route_handoff_v1841 as prev1841


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1844"
V1843_OUT = REPO_ROOT / "tmp" / "wifi" / "v1843-pm-service-post-ack-branch-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1843/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1844-pm-service-post-ack-branch-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1844_PM_SERVICE_POST_ACK_BRANCH_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.164 (v1843-pm-service-post-ack-branch)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1843.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1843.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1843-helper.result"
DMESG_PATTERN = (
    "A90v1843|pm_service_trigger_observer|wlan_pd_after_holder_start|"
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

POST_ACK_KEYS = (
    "pm_service_ack_impl_entry",
    "pm_service_ack_impl_match_dispatch",
    "pm_service_post_ack_action_entry",
    "pm_service_post_ack_client_state_store",
    "pm_service_post_ack_vote_scan_done",
    "pm_service_post_ack_action_branch",
    "pm_service_post_ack_timer_settime_call",
    "pm_service_post_ack_power_state_load",
    "pm_service_post_ack_qmi_restart_ind_call",
    "pm_service_post_ack_power_on_open_call",
    "pm_service_post_ack_power_on_open_ret",
    "pm_service_post_ack_unlock_return",
)


def runner() -> Any:
    return prev1841.runner()


def prev1796() -> Any:
    return prev1841.prev1796()


def intish(value: object) -> int:
    return prev1841.intish(value)


def configure_runner() -> None:
    prev1841.CYCLE = CYCLE
    prev1841.V1840_OUT = V1843_OUT
    prev1841.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1841.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1841.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1841.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1841.TEST_LOG_PATH = TEST_LOG_PATH
    prev1841.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1841.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1841.DMESG_PATTERN = DMESG_PATTERN
    prev1841.configure_runner()
    runner().DEFAULT_TEST_IMAGE = V1843_OUT / "boot_linux_v1843_pm_service_post_ack_branch.img"


def post_ack_sample(fields: dict[str, str], key: str) -> dict[str, str]:
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


def collect_post_ack_details(fields: dict[str, str]) -> dict[str, Any]:
    samples = [post_ack_sample(fields, key) for key in POST_ACK_KEYS]
    hit_keys = [sample["key"] for sample in samples if intish(sample.get("hit_count")) > 0]
    registered_ok = all(sample.get("registered") == "1" for sample in samples)
    enabled_ok = all(sample.get("enabled") == "1" for sample in samples)
    hit_counts = {sample["key"]: intish(sample.get("hit_count")) for sample in samples}
    return {
        "post_ack_samples": samples,
        "post_ack_registered_ok": registered_ok,
        "post_ack_enabled_ok": enabled_ok,
        "post_ack_contract_ok": registered_ok and enabled_ok,
        "post_ack_hit_keys": hit_keys,
        "post_ack_hit_count_total": sum(hit_counts.values()),
        "post_ack_hit_counts": hit_counts,
        "post_ack_ack_impl_hits": hit_counts["pm_service_ack_impl_entry"],
        "post_ack_match_dispatch_hits": hit_counts["pm_service_ack_impl_match_dispatch"],
        "post_ack_action_entry_hits": hit_counts["pm_service_post_ack_action_entry"],
        "post_ack_open_call_hits": hit_counts["pm_service_post_ack_power_on_open_call"],
        "post_ack_open_ret_hits": hit_counts["pm_service_post_ack_power_on_open_ret"],
    }


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    base_decision, base_pass, base_reason, details = prev1841.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = runner().fwbase.parse_helper_fields(evidence_dir)
    details.update(collect_post_ack_details(helper_fields))
    if not base_pass:
        return base_decision, base_pass, base_reason, details
    if not details.get("post_ack_contract_ok"):
        details["post_ack_label"] = "post-ack-contract-missing"
        return (
            f"{args.cycle.lower()}-post-ack-contract-missing",
            False,
            "PM-service post-ack uprobe labels did not all register and enable",
            details,
        )
    if prev1841.prev1838.prev1834.actual_publication_progress(details) or bool(details.get("pm_focus_mhi_wlan0_progress")):
        label = "powerup-or-wlfw-progress"
        reason = "powerup, service publication, MHI/WLFW, or wlan0 progressed below the PM-service post-ack observer"
    elif intish(details.get("post_ack_open_call_hits")) > 0 or intish(details.get("post_ack_open_ret_hits")) > 0:
        label = "post-ack-open-branch-reached"
        reason = "PM-service post-ack path reached the devnode open branch; lower-state evidence stayed bounded for rollback inspection"
    elif intish(details.get("post_ack_action_entry_hits")) > 0:
        label = "post-ack-action-no-open"
        reason = "PM-service ack implementation reached the post-ack action path, but the devnode open branch stayed at zero hits and lower state stayed static"
    elif intish(details.get("post_ack_ack_impl_hits")) > 0 or intish(details.get("post_ack_match_dispatch_hits")) > 0:
        label = "post-ack-impl-no-action"
        reason = "PM-service ack implementation was reached, but post-ack action entry did not fire"
    else:
        label = "post-ack-impl-absent-current-route"
        reason = "current-route callback/ack fired, but PM-service ack implementation labels stayed at zero hits"
    details["post_ack_label"] = label
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
        "# Native Init V1844 PM-Service Post-Ack Branch Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1844`",
        "- Type: one-run rollbackable PM-service post-ack branch hit-count discriminator",
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
        f"- post-ack label: `{gate.get('post_ack_label')}`",
        f"- post-ack registered/enabled: `{gate.get('post_ack_registered_ok')}` / `{gate.get('post_ack_enabled_ok')}`",
        f"- post-ack hit total: `{gate.get('post_ack_hit_count_total')}`",
        f"- post-ack hit keys: `{gate.get('post_ack_hit_keys')}`",
        f"- callback/ack label/total: `{gate.get('callback_ack_label')}` / `{gate.get('callback_ack_hit_count_total')}`",
        f"- lower-continuation label: `{gate.get('lower_continuation_label')}`",
        f"- PM focus change fields / mdm-status delta: `{gate.get('pm_focus_change_fields')}` / `{gate.get('pm_focus_mdm_status_delta')}`",
        f"- PM focus MHI/wlan0 progress: `{gate.get('pm_focus_mhi_wlan0_progress')}`",
        f"- service-notifier / QIPCRTR labels: `{gate.get('servnotif_label')}` / `{gate.get('qipcrtr_bound_recv_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## PM-Service Post-Ack Hits",
        "",
        *render_samples(gate.get("post_ack_samples", [])),
        "",
        "## Callback/Ack Hits",
        "",
        *prev1841.render_callback_samples(gate.get("callback_ack_samples", [])),
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
        "- The new V1844 surface only adds read-only `pm-service` uprobe hit counts on the V1843 test boot image.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- If post-ack open targets `/dev/subsys_modem` while lower state stays static, classify PM-service peripheral selection/state flags around `0x88a0`/`0x88c8` before any new mutation.",
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
