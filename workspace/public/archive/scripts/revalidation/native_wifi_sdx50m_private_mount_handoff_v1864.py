#!/usr/bin/env python3
"""V1864 rollbackable handoff for V1863 private SDX50M cnss-daemon mount."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_pm_service_open_context_handoff_v1847 as prev1847


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1864"
V1863_OUT = REPO_ROOT / "tmp" / "wifi" / "v1863-sdx50m-private-mount-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1863/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1864-sdx50m-private-mount-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1864_SDX50M_PRIVATE_MOUNT_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.166 (v1863-sdx50m-private-mount)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1863.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1863.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1863-helper.result"
TEST_IMAGE = V1863_OUT / "boot_linux_v1863_sdx50m_private_mount.img"
PRIVATE_CNSS_PATH = "/cache/bin/cnss-daemon.sdx50m"
DMESG_PATTERN = (
    "A90v1863|private_cnss_daemon|pm_service_trigger_observer|"
    "wlan_pd_after_holder_start|wlan_pd_after_post_listener_window|"
    "periph_pm_callback|periph_pm_client_ack|periph_pm_server_ack|"
    "periph_pm_server_ontransact|pm_service_ack_impl|pm_service_post_ack|"
    "pcie_1_gdsc|pcie_0_gdsc|GPIO135|GPIO142|mdm_status|"
    "wlan_pd_qipcrtr_bound_recv_poll_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|"
    "pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|"
    "wlan_pd|qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|ext-SDX50M|SDX50M|MHI"
)


def runner() -> Any:
    return prev1847.runner()


def prev1796() -> Any:
    return prev1847.prev1796()


def intish(value: object) -> int:
    return prev1847.intish(value)


def configure_runner() -> None:
    prev1847.CYCLE = CYCLE
    prev1847.V1846_OUT = V1863_OUT
    prev1847.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1847.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1847.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1847.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1847.TEST_LOG_PATH = TEST_LOG_PATH
    prev1847.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1847.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1847.DMESG_PATTERN = DMESG_PATTERN
    prev1847.configure_runner()
    base = runner()
    base.DEFAULT_SOURCE_MANIFEST = V1863_OUT / "manifest.json"
    base.DEFAULT_TEST_IMAGE = TEST_IMAGE
    base.LOCAL_PROPERTY_ROOT = V1863_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT


def private_mount_details(fields: dict[str, str]) -> dict[str, Any]:
    source = fields.get("private_cnss_daemon.source", "")
    target = fields.get("private_cnss_daemon.target", "")
    source_size = fields.get("private_cnss_daemon.source_size", "")
    target_size_before = fields.get("private_cnss_daemon.target_size_before", "")
    target_size_after = fields.get("private_cnss_daemon.target_size_after", "")
    bind_rc = fields.get("private_cnss_daemon.bind_rc", "")
    expected_c_string = fields.get("private_cnss_daemon.expected_c_string", "")
    source_ok = source == PRIVATE_CNSS_PATH
    target_ok = target.endswith("/vendor/bin/cnss-daemon")
    bind_ok = bind_rc == "0"
    size_ok = intish(source_size) > 0 and (intish(target_size_before) > 0 or intish(target_size_after) > 0)
    expected_string_ok = expected_c_string == "SDX50M"
    return {
        "private_cnss_source": source,
        "private_cnss_target": target,
        "private_cnss_source_size": source_size,
        "private_cnss_target_size_before": target_size_before,
        "private_cnss_target_size_after": target_size_after,
        "private_cnss_bind_rc": bind_rc,
        "private_cnss_expected_c_string": expected_c_string,
        "private_cnss_source_ok": source_ok,
        "private_cnss_target_ok": target_ok,
        "private_cnss_bind_ok": bind_ok,
        "private_cnss_size_ok": size_ok,
        "private_cnss_expected_string_ok": expected_string_ok,
        "private_cnss_contract_ok": source_ok and target_ok and bind_ok and size_ok and expected_string_ok,
    }


def sdx50m_selection_seen(details: dict[str, Any]) -> bool:
    observed = ",".join(
        str(details.get(key) or "")
        for key in (
            "pm_server_register_entry_peripheral",
            "pm_server_register_strcmp_candidate",
            "pm_server_register_strcmp_requested",
            "pm_server_register_no_peripheral_name",
            "pm_service_first_add_names",
            "pm_service_second_add_names",
            "pm_service_entry_names",
            "pm_service_known_names",
            "pm_service_init_fail_names",
        )
    )
    return (
        details.get("open_context_path") == "/dev/subsys_esoc0"
        or "SDX50M" in observed.split(",")
        or "SDX50M" in observed
    )


def lower_publication_progress(details: dict[str, Any]) -> bool:
    return (
        prev1847.prev1844.prev1841.prev1838.prev1834.actual_publication_progress(details)
        or bool(details.get("pm_focus_mhi_wlan0_progress"))
    )


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    base_decision, base_pass, base_reason, details = prev1847.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = runner().fwbase.parse_helper_fields(evidence_dir)
    details.update(private_mount_details(helper_fields))
    if (
        bool(test_flash.get("ok"))
        and bool(details.get("version_ok"))
        and bool(details.get("rollback_ok"))
        and not details.get("private_cnss_contract_ok")
    ):
        details["private_mount_label"] = "private-mount-bind-failed"
        return (
            f"{args.cycle.lower()}-private-mount-bind-failed",
            False,
            "private SDX50M cnss-daemon bind-mount contract was not observed; stop before interpreting PM/lower-state deltas",
            details,
        )
    if not base_pass:
        return base_decision, base_pass, base_reason, details
    if lower_publication_progress(details):
        label = "private-mount-lower-publication-progress"
        reason = "private SDX50M daemon mount was active and lower publication, MHI/WLFW, or wlan0 progressed; stop before Wi-Fi HAL/scan/connect"
    elif sdx50m_selection_seen(details):
        label = "private-mount-sdx50m-selected"
        reason = "private SDX50M daemon mount was active and PM-service selection evidence moved toward SDX50M/eSoC; inspect lower publication before connect"
    else:
        label = "private-mount-pre-wifi-gap"
        reason = "private SDX50M daemon mount was active, but WLFW service 69 and wlan0 stayed absent in the bounded lower observer"
    details["private_mount_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_private_mount(gate: dict[str, Any]) -> list[str]:
    return [
        f"- contract/source/target/bind: `{gate.get('private_cnss_contract_ok')}` / `{gate.get('private_cnss_source_ok')}` / `{gate.get('private_cnss_target_ok')}` / `{gate.get('private_cnss_bind_ok')}`",
        f"- source path: `{gate.get('private_cnss_source')}`",
        f"- target path: `{gate.get('private_cnss_target')}`",
        f"- source/target-before/target-after sizes: `{gate.get('private_cnss_source_size')}` / `{gate.get('private_cnss_target_size_before')}` / `{gate.get('private_cnss_target_size_after')}`",
        f"- expected C string: `{gate.get('private_cnss_expected_c_string')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    post = result.get("post_rollback_verification", {})
    lines = [
        f"# Native Init {CYCLE} SDX50M Private Mount Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Type: one-run rollbackable `{TEST_EXPECT_VERSION}` private SDX50M cnss-daemon mount discriminator",
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
        f"- private mount label: `{gate.get('private_mount_label')}`",
        f"- open-context label/path/fd: `{gate.get('open_context_label')}` / `{gate.get('open_context_path')}` / `{gate.get('open_context_fd')}`",
        f"- post-ack label/total: `{gate.get('post_ack_label')}` / `{gate.get('post_ack_hit_count_total')}`",
        f"- callback/ack label/total: `{gate.get('callback_ack_label')}` / `{gate.get('callback_ack_hit_count_total')}`",
        f"- PM register candidate/requested/no-peripheral: `{gate.get('pm_server_register_strcmp_candidate')}` / `{gate.get('pm_server_register_strcmp_requested')}` / `{gate.get('pm_server_register_no_peripheral_name')}`",
        f"- PM-service first add names/devnodes: `{gate.get('pm_service_first_add_names')}` / `{gate.get('pm_service_first_add_devnodes')}`",
        f"- lower-continuation label: `{gate.get('lower_continuation_label')}`",
        f"- PM focus change fields / mdm-status delta: `{gate.get('pm_focus_change_fields')}` / `{gate.get('pm_focus_mdm_status_delta')}`",
        f"- PM focus MHI/wlan0 progress: `{gate.get('pm_focus_mhi_wlan0_progress')}`",
        f"- service-notifier / QIPCRTR labels: `{gate.get('servnotif_label')}` / `{gate.get('qipcrtr_bound_recv_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Private Mount",
        "",
        *render_private_mount(gate),
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
        "- The only new live delta is namespace-local bind mounting the pre-staged private SDX50M `cnss-daemon` over the helper namespace `/vendor/bin/cnss-daemon`.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- If the label is `private-mount-lower-publication-progress`, run a direct read-only prerequisite check before any connect attempt.",
        "- If the label is `private-mount-pre-wifi-gap`, keep classifying the remaining mdm3/ext-SDX50M lower-response gap before another live mutation.",
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
