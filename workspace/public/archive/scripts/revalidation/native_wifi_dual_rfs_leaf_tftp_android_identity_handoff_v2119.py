#!/usr/bin/env python3
"""V2119 rollbackable handoff for dual-RFS leaf route plus tftp_server Android identity only."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_leaf_precreate_handoff_v2113 as prev2113


CYCLE = "V2119"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2119-dual-rfs-leaf-tftp-android-identity-handoff"
HANDOFF_DIR = OUT_DIR / "v2118-handoff"
HANDOFF_REPORT = OUT_DIR / "v2118-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2119_DUAL_RFS_LEAF_TFTP_ANDROID_IDENTITY_HANDOFF_2026-06-05.md"
)
V2118_OUT = REPO_ROOT / "tmp" / "wifi" / "v2118-dual-rfs-leaf-tftp-android-identity-test-boot"
V2118_INIT = V2118_OUT / "init_v2118_dual_rfs_leaf_tftp_android_identity"
V2118_BOOT = V2118_OUT / "boot_linux_v2118_dual_rfs_leaf_tftp_android_identity.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2118/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.234 (v2118-dual-rfs-leaf-tftp-android-identity)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2118.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2118.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2118-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v418"

BASE_COLLECT_DETAILS = prev2113.collect_details
BASE_CLASSIFY = prev2113.classify


def rel(path: Path) -> str:
    return prev2113.rel(path)


def intish(value: object) -> int:
    return prev2113.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2113.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2118",
        "v2118-dual-rfs-leaf-tftp-android-identity",
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
        "android_parity=firmware_mnt_probe_present_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.enabled=%d",
        "wifi_companion_start.tftp_persist_rfs_leaf_precreate.paths=/mnt/vendor/persist/rfs/mdm/mpss,/mnt/vendor/persist/rfs/apq/gnss",
        "wifi_companion_start.tftp_process_namespace_audit.compiled=%d",
        "persist_rfs_mdm_mpss",
        "persist_rfs_apq_gnss",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
        "rmt_storage-init-root",
        "tftp_server-android-runtime",
        "%s.expected.cap_count=%zu",
        "%s.expected.ambient=%d",
    )
    boot_forbidden = (
        "diag_remote_dev_poll_probe.begin=1",
        "diag_wlan_pd_memory_device_probe.begin=1",
        "diag_wlan_pd_memory_regular_mask_probe.begin=1",
        "diag_dci_register_read_probe.begin=1",
        "diag_dci_wlan_target_mask_probe.begin=1",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
        "post_bdf_boot_wlan_consumer_gate.begin=1",
        "ota_firewall/ruleset:",
    )
    checks: dict[str, Any] = {}
    for path, required, forbidden in (
        (V2118_INIT, init_required, init_forbidden),
        (V2118_BOOT, boot_required, boot_forbidden),
    ):
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        present_forbidden = [token for token in forbidden if token.encode() in data]
        checks[rel(path)] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not present_forbidden,
            "missing": missing,
            "forbidden": present_forbidden,
        }
    return checks


def parse_fields() -> dict[str, str]:
    return prev2113.prev2109.prev2103.prev2101.prev2098.prev2096.prev2083.prev2081.prev2059.prev2057.parse_fields()


def identity_summary(fields: dict[str, str], child: str) -> dict[str, Any]:
    prefix = f"wifi_hal_composite_child.{child}"
    return {
        "expected_contract": fields.get(f"{prefix}.expected.contract", ""),
        "expected_uid": intish(fields.get(f"{prefix}.expected.uid")),
        "expected_gid": intish(fields.get(f"{prefix}.expected.gid")),
        "expected_groups": fields.get(f"{prefix}.expected.groups", ""),
        "expected_cap_count": intish(fields.get(f"{prefix}.expected.cap_count")),
        "expected_ambient": intish(fields.get(f"{prefix}.expected.ambient")),
        "setgroups_ok": intish(fields.get(f"{prefix}.setgroups.ok")),
        "keepcaps_ok": intish(fields.get(f"{prefix}.pr_set_keepcaps.ok")),
        "pre_drop_inheritable_ok": intish(fields.get(f"{prefix}.pre_drop_inheritable.ok")),
        "setresgid_ok": intish(fields.get(f"{prefix}.setresgid.ok")),
        "setresuid_ok": intish(fields.get(f"{prefix}.setresuid.ok")),
        "capset_ok": intish(fields.get(f"{prefix}.capset.ok")),
        "ambient_cap10_ok": intish(fields.get(f"{prefix}.ambient_raise.cap10.ok")),
        "ambient_cap36_ok": intish(fields.get(f"{prefix}.ambient_raise.cap36.ok")),
        "preexec_status": fields.get(f"{prefix}.preexec_status", ""),
    }


def identity_ok(summary: dict[str, Any],
                contract: str,
                uid: int,
                gid: int,
                groups: str) -> bool:
    return (
        summary.get("expected_contract") == contract
        and intish(summary.get("expected_uid")) == uid
        and intish(summary.get("expected_gid")) == gid
        and summary.get("expected_groups") == groups
        and intish(summary.get("expected_cap_count")) == 2
        and intish(summary.get("expected_ambient")) == 1
        and intish(summary.get("setgroups_ok")) == 1
        and intish(summary.get("keepcaps_ok")) == 1
        and intish(summary.get("pre_drop_inheritable_ok")) == 1
        and intish(summary.get("setresgid_ok")) == 1
        and intish(summary.get("setresuid_ok")) == 1
        and intish(summary.get("capset_ok")) == 1
        and intish(summary.get("ambient_cap10_ok")) == 1
        and intish(summary.get("ambient_cap36_ok")) == 1
        and summary.get("preexec_status") == "pass"
    )


def root_identity_ok(summary: dict[str, Any], contract: str) -> bool:
    return (
        summary.get("expected_contract") == contract
        and intish(summary.get("expected_uid")) == 0
        and intish(summary.get("expected_gid")) == 0
        and summary.get("expected_groups") == ""
        and intish(summary.get("setgroups_ok")) == 1
        and intish(summary.get("setresgid_ok")) == 1
        and intish(summary.get("setresuid_ok")) == 1
        and summary.get("preexec_status") == "pass"
    )


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = parse_fields()
    rmt_storage = identity_summary(fields, "rmt_storage")
    tftp_server = identity_summary(fields, "tftp_server")
    details["tftp_android_identity"] = {
        "rmt_storage": rmt_storage,
        "tftp_server": tftp_server,
        "rmt_storage_ok": root_identity_ok(rmt_storage, "rmt_storage-init-root"),
        "tftp_server_ok": identity_ok(
            tftp_server,
            "tftp_server-android-runtime",
            2903,
            2903,
            "1000,2903,2904,3010",
        ),
    }
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    identity = details.get("tftp_android_identity") if isinstance(details.get("tftp_android_identity"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    tftp_logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    bridge_ok = prev2113.dual_rfs_ok(details)
    identity_applied = bool(identity.get("rmt_storage_ok")) and bool(identity.get("tftp_server_ok"))
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0
    wlan_pd_up = intish(cascade.get("wlan_pd_up")) > 0
    wlanmdsp_seen = bool(base.get("wlanmdsp_seen"))
    ota_seen = bool(base.get("ota_seen"))
    server_seen = (
        bool(base.get("server_check_seen"))
        or intish(tftp_logdw.get("server_check")) > 0
        or intish(branch.get("server_check", {}).get("exists")) == 1
    )
    server_payload = str(branch.get("server_check", {}).get("payload", ""))
    server_after_wlan_pd_ms = branch.get("server_after_wlan_pd_ms")
    mcfg_seen = (
        bool(base.get("mcfg_seen"))
        or intish(tftp_logdw.get("mcfg")) > 0
        or intish(branch.get("mcfg", {}).get("exists")) == 1
    )

    if not hook_ok:
        label = "tftp-android-identity-artifact-hook-regression"
        passed = False
        reason = "V2118 artifact does not contain the bounded dual-RFS plus tftp-only Android identity contract"
    elif not bridge_ok:
        label = "tftp-android-identity-bridge-missing"
        passed = False
        reason = "exact Android firmware_mnt WLAN image path or fallback path did not resolve in the private RFS bridge"
    elif not identity_applied:
        label = "tftp-android-identity-runtime-contract-not-applied"
        passed = False
        reason = "rmt_storage did not stay on init-root or tftp_server did not emit the Android-observed uid/gid/group/capability contract at preexec"
    elif wlan0:
        label = "tftp-android-identity-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "tftp-android-identity-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "tftp-android-identity-wlanmdsp-progress"
        passed = True
        reason = "tftp-only Android identity produced a visible wlanmdsp TFTP request"
    elif ota_seen:
        label = "tftp-android-identity-ota-no-wlanmdsp"
        passed = True
        reason = "tftp-only Android identity reached ota_firewall but not wlanmdsp"
    elif not wlan_pd_up:
        label = "tftp-android-identity-no-wlan-pd-up-no-tftp"
        passed = True
        reason = "tftp-only Android identity applied and the bridge held, but the route regressed before wlan_pd UP/ICNSS QMI and no Android-order TFTP branch appeared"
    elif server_seen:
        phase = "post-up" if isinstance(server_after_wlan_pd_ms, int) and server_after_wlan_pd_ms >= 0 else "unknown-order"
        label = f"tftp-android-identity-{phase}-server-check-no-wlanmdsp"
        passed = True
        reason = "tftp-only Android identity applied, but native still reached only server_check and not ota_firewall/wlanmdsp"
    elif mcfg_seen:
        label = "tftp-android-identity-mcfg-only-no-android-branch"
        passed = True
        reason = "tftp-only Android identity applied, but native still showed only the late mcfg branch"
    else:
        label = "tftp-android-identity-no-tftp-trigger"
        passed = True
        reason = "tftp-only Android identity applied, but no Android-order TFTP bootstrap appeared"

    return {
        **base,
        "decision": f"v2119-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "dual_rfs_bridge_ok": bridge_ok,
        "tftp_android_identity_applied": identity_applied,
        "rmt_storage_identity_ok": bool(identity.get("rmt_storage_ok")),
        "tftp_server_identity_ok": bool(identity.get("tftp_server_ok")),
        "wlan_pd_up": wlan_pd_up,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    identity = details.get("tftp_android_identity", {}) if isinstance(details.get("tftp_android_identity"), dict) else {}
    bridge = details.get("dual_rfs_bridge", {}) if isinstance(details.get("dual_rfs_bridge"), dict) else {}
    ns = details.get("tftp_process_namespace_audit", {}) if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    tftp_logdw = details.get("tftp_logdw", {}) if isinstance(details.get("tftp_logdw"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    identity_rows = []
    for child in ("rmt_storage", "tftp_server"):
        item = identity.get(child, {}) if isinstance(identity.get(child), dict) else {}
        identity_rows.append([
            child,
            item.get("expected_contract"),
            f"{item.get('expected_uid')}:{item.get('expected_gid')}",
            item.get("expected_groups"),
            f"cap_count={item.get('expected_cap_count')} ambient={item.get('expected_ambient')}",
            f"cap10={item.get('ambient_cap10_ok')} cap36={item.get('ambient_cap36_ok')} status={item.get('preexec_status')}",
        ])
    return "\n".join([
        "# Native Init V2119 Dual-RFS Leaf TFTP Android Identity Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2119`",
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
                ["identity", classification.get("tftp_android_identity_applied"), f"rmt={classification.get('rmt_storage_identity_ok')} tftp={classification.get('tftp_server_identity_ok')}"],
                ["dual_rfs", classification.get("dual_rfs_bridge_ok"), f"bridge={bridge}"],
                ["namespace_audit", classification.get("namespace_audit_ok"), f"pid={classification.get('tftp_pid')} root={ns.get('root_target')}"],
                ["tftp_logdw", tftp_logdw.get("record_count"), f"server_check={classification.get('server_check_seen')} ota={classification.get('ota_seen')} wlanmdsp={classification.get('wlanmdsp_seen')} mcfg={classification.get('mcfg_seen')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')} branch={branch}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Identity Contract",
        "",
        markdown_table(
            ["child", "contract", "uid:gid", "groups", "caps", "runtime"],
            identity_rows,
        ),
        "",
        "## Interpretation",
        "",
        "- V2119 isolates `tftp_server` Android identity while preserving the V2113 root `rmt_storage` contract that kept modem EFS reads and `wlan_pd UP` alive.",
        "- A `wlanmdsp`/FW-ready/`wlan0` label means the tftp_server identity mismatch was on the producer path; chase the normal downstream cascade before any scan/connect.",
        "- A no-`wlan_pd UP` label means tftp-only Android identity did not unlock the trigger and removed the prior bridge-induced `wlan_pd UP` edge; treat this as a `tftp_server` identity regression signal, not downstream progress.",
        "- A server-check/mcfg-only/no-trigger label falsifies tftp_server identity as the missing Android-order WLAN-PD firmware-fetch trigger in the current bridge route.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2118 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, namespace-local persist-RFS leaf precreate in the private rootfs, root `rmt_storage`, Android-runtime `tftp_server` uid/gid/group/cap drop inside the child namespace, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2113() -> None:
    prev2113.CYCLE = CYCLE
    prev2113.OUT_DIR = OUT_DIR
    prev2113.HANDOFF_DIR = HANDOFF_DIR
    prev2113.HANDOFF_REPORT = HANDOFF_REPORT
    prev2113.REPORT_PATH = REPORT_PATH
    prev2113.V2112_OUT = V2118_OUT
    prev2113.V2112_INIT = V2118_INIT
    prev2113.V2112_BOOT = V2118_BOOT
    prev2113.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2113.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2113.TEST_LOG_PATH = TEST_LOG_PATH
    prev2113.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2113.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2113.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2113.prev2109.BRIDGE_CAPTURE = OUT_DIR / "host" / "v2119-autostart-bridge.log"
    prev2113.prev2109.BRIDGE_STDOUT = OUT_DIR / "host" / "v2119-autostart-bridge.stdout.txt"
    prev2113.prev2109.BRIDGE_STDERR = OUT_DIR / "host" / "v2119-autostart-bridge.stderr.txt"
    prev2113.prev2109.BRIDGE_PID = OUT_DIR / "host" / "v2119-autostart-bridge.pid"
    prev2113.artifact_hook_check = artifact_hook_check
    prev2113.collect_details = collect_details
    prev2113.classify = classify
    prev2113.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2113()
    return prev2113.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
