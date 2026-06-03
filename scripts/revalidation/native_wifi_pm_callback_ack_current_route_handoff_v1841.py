#!/usr/bin/env python3
"""V1841 one-run current-route PM callback/ack hit-count handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_lower_continuation_sampler_handoff_v1838 as prev1838


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1841"
V1840_OUT = REPO_ROOT / "tmp" / "wifi" / "v1840-pm-callback-ack-current-route-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1840/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1841-pm-callback-ack-current-route-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1841_PM_CALLBACK_ACK_CURRENT_ROUTE_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.163 (v1840-pm-callback-ack-current-route)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1840.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1840.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1840-helper.result"
DMESG_PATTERN = (
    "A90v1840|pm_service_trigger_observer|wlan_pd_after_holder_start|"
    "wlan_pd_after_post_listener_window|periph_pm_callback|periph_pm_client_ack|"
    "periph_pm_server_ack|periph_pm_server_ontransact|pcie_1_gdsc|"
    "pcie_0_gdsc|GPIO135|GPIO142|mdm_status|"
    "wlan_pd_qipcrtr_bound_recv_poll_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|"
    "pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|"
    "wlan_pd|qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3|ext-SDX50M|MHI"
)

CALLBACK_KEYS = (
    "periph_pm_callback_stub_entry",
    "periph_pm_callback_write_state",
    "periph_pm_callback_remote_binder",
    "periph_pm_callback_transact_call",
    "periph_pm_callback_transact_return",
    "periph_pm_client_ack_entry",
    "periph_pm_client_ack_match",
    "periph_pm_client_ack_virtual_call",
    "periph_pm_server_ontransact_entry",
    "periph_pm_server_ack_read_state",
    "periph_pm_server_ack_impl_call",
    "periph_pm_server_ack_write_ret",
)


def runner() -> Any:
    return prev1838.runner()


def prev1796() -> Any:
    return prev1838.prev1796()


def intish(value: object) -> int:
    return prev1838.intish(value)


def configure_runner() -> None:
    prev1838.CYCLE = CYCLE
    prev1838.V1837_OUT = V1840_OUT
    prev1838.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1838.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1838.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1838.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1838.TEST_LOG_PATH = TEST_LOG_PATH
    prev1838.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1838.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1838.DMESG_PATTERN = DMESG_PATTERN
    prev1838.configure_runner()
    runner().DEFAULT_TEST_IMAGE = V1840_OUT / "boot_linux_v1840_pm_callback_ack_current_route.img"


def callback_sample(fields: dict[str, str], key: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.{key}."
    return {
        "key": key,
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "register_rc": fields.get(prefix + "register_rc", ""),
        "enable_rc": fields.get(prefix + "enable_rc", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
    }


def collect_callback_details(fields: dict[str, str]) -> dict[str, Any]:
    samples = [callback_sample(fields, key) for key in CALLBACK_KEYS]
    hit_keys = [sample["key"] for sample in samples if intish(sample.get("hit_count")) > 0]
    registered_ok = all(sample.get("registered") == "1" for sample in samples)
    enabled_ok = all(sample.get("enabled") == "1" for sample in samples)
    return {
        "callback_ack_samples": samples,
        "callback_ack_registered_ok": registered_ok,
        "callback_ack_enabled_ok": enabled_ok,
        "callback_ack_hit_keys": hit_keys,
        "callback_ack_hit_count_total": sum(intish(sample.get("hit_count")) for sample in samples),
        "callback_ack_contract_ok": registered_ok and enabled_ok,
    }


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    base_decision, base_pass, base_reason, details = prev1838.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = runner().fwbase.parse_helper_fields(evidence_dir)
    details.update(collect_callback_details(helper_fields))
    if not base_pass:
        return base_decision, base_pass, base_reason, details
    if not details.get("callback_ack_contract_ok"):
        details["callback_ack_label"] = "callback-ack-contract-missing"
        return (
            f"{args.cycle.lower()}-callback-ack-contract-missing",
            False,
            "current-route callback/ack uprobe labels did not all register and enable",
            details,
        )
    if prev1838.prev1834.actual_publication_progress(details) or bool(details.get("pm_focus_mhi_wlan0_progress")):
        label = "powerup-or-wlfw-progress"
        reason = "powerup, service publication, MHI/WLFW, or wlan0 progressed below the current callback/ack observer"
    elif intish(details.get("callback_ack_hit_count_total")) > 0:
        label = "callback-ack-present-no-powerup"
        reason = "current-route callback/transact/ack hit counts appeared, but lower PMIC/GDSC and MHI/WLFW/wlan0 state stayed static"
    else:
        label = "callback-ack-absent-current-route"
        reason = "PM list/register/connect still succeeded, but current-route callback/ack hit counts stayed zero and lower state stayed static"
    details["callback_ack_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_callback_samples(samples: list[dict[str, str]]) -> list[str]:
    return [
        f"- `{sample.get('key')}` registered/enabled/hits: `{sample.get('registered')}` / `{sample.get('enabled')}` / `{sample.get('hit_count')}` first=`{sample.get('first_hit_line')}`"
        for sample in samples
    ]


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    post = result.get("post_rollback_verification", {})
    lines = [
        "# Native Init V1841 PM Callback/Ack Current-route Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1841`",
        "- Type: one-run rollbackable current-route PM callback/ack hit-count discriminator",
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
        f"- callback/ack label: `{gate.get('callback_ack_label')}`",
        f"- callback/ack registered/enabled: `{gate.get('callback_ack_registered_ok')}` / `{gate.get('callback_ack_enabled_ok')}`",
        f"- callback/ack hit total: `{gate.get('callback_ack_hit_count_total')}`",
        f"- callback/ack hit keys: `{gate.get('callback_ack_hit_keys')}`",
        f"- lower-continuation label: `{gate.get('lower_continuation_label')}`",
        f"- PM focus change fields / mdm-status delta: `{gate.get('pm_focus_change_fields')}` / `{gate.get('pm_focus_mdm_status_delta')}`",
        f"- PM focus MHI/wlan0 progress: `{gate.get('pm_focus_mhi_wlan0_progress')}`",
        f"- service-notifier / QIPCRTR labels: `{gate.get('servnotif_label')}` / `{gate.get('qipcrtr_bound_recv_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Callback/Ack Hits",
        "",
        *render_callback_samples(gate.get("callback_ack_samples", [])),
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
        "- The new V1841 surface only adds read-only uprobe hit counts on existing `libperipheral_client.so` offsets in the V1838 current route.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct `/dev/subsys_esoc0` open, fake ONLINE, PMIC/GPIO/GDSC write, eSoC notify, BOOT_DONE spoof, forced RC1, `boot_wlan`, restart-PD request, PCI rescan, or platform bind/unbind was used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- If callback/ack is absent, classify why current PM connect/register returns without the legacy callback/ack sequence before any new live mutation.",
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
