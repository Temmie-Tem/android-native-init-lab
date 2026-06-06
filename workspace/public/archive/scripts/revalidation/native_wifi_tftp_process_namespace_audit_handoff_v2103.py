#!/usr/bin/env python3
"""V2103 rollbackable handoff for stock tftp_server process namespace audit."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_persist_rfs_autodir_handoff_v2101 as prev2101


CYCLE = "V2103"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2103-tftp-process-namespace-audit-handoff"
HANDOFF_DIR = OUT_DIR / "v2102-handoff"
HANDOFF_REPORT = OUT_DIR / "v2102-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2103_TFTP_PROCESS_NAMESPACE_AUDIT_HANDOFF_2026-06-05.md"
)
V2102_OUT = REPO_ROOT / "tmp" / "wifi" / "v2102-tftp-process-namespace-audit-test-boot"
V2102_INIT = V2102_OUT / "init_v2102_tftp_process_namespace_audit"
V2102_BOOT = V2102_OUT / "boot_linux_v2102_tftp_process_namespace_audit.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2102/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.228 (v2102-tftp-process-namespace-audit)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2102.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2102.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2102-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v412"


def rel(path: Path) -> str:
    return prev2101.rel(path)


def intish(value: object) -> int:
    return prev2101.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2101.markdown_table(headers, rows)


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
        "wifi_companion_start.macloader_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2102",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "wifi_companion_start.tftp_process_namespace_audit.compiled=%d",
        "tftp_process_namespace_audit",
        "persist_rfs_shared",
        "persist_rfs_msm_mpss",
        "persist_rfs_msm_adsp",
        "no_ptrace=1",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
    )
    final_checks: dict[str, Any] = {}
    for path, required in ((V2102_INIT, init_required), (V2102_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2102_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        final_checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return final_checks


def ns_path(fields: dict[str, str], name: str) -> dict[str, Any]:
    prefix = f"tftp_process_namespace_audit.path.{name}"
    return {
        "absolute": fields.get(f"{prefix}.absolute", ""),
        "proc_root_path": fields.get(f"{prefix}.proc_root_path", ""),
        "exists": intish(fields.get(f"{prefix}.exists")),
        "is_dir": intish(fields.get(f"{prefix}.is_dir")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "uid": intish(fields.get(f"{prefix}.uid")),
        "gid": intish(fields.get(f"{prefix}.gid")),
        "fs_type": fields.get(f"{prefix}.fs_type", ""),
        "errno": intish(fields.get(f"{prefix}.errno")),
        "error": fields.get(f"{prefix}.error", ""),
    }


def collect_namespace(fields: dict[str, str]) -> dict[str, Any]:
    paths = {
        name: ns_path(fields, name)
        for name in (
            "persist_rfs",
            "persist_rfs_shared",
            "persist_rfs_msm",
            "persist_rfs_msm_mpss",
            "persist_rfs_msm_adsp",
            "vendor_rfs_readwrite",
            "data_tombstones_rfs",
        )
    }
    return {
        "compiled": intish(fields.get("wifi_companion_start.tftp_process_namespace_audit.compiled")),
        "begin": intish(fields.get("tftp_process_namespace_audit.begin")),
        "audit_ok": intish(fields.get("tftp_process_namespace_audit.audit_ok")),
        "pid": intish(fields.get("tftp_process_namespace_audit.pid")),
        "root_target": fields.get("tftp_process_namespace_audit.root.target", ""),
        "cwd_target": fields.get("tftp_process_namespace_audit.cwd.target", ""),
        "ns_mnt_target": fields.get("tftp_process_namespace_audit.ns_mnt.target", ""),
        "mountinfo_match_count": intish(fields.get("tftp_process_namespace_audit.mountinfo.match_count")),
        "paths": paths,
        "all_persist_targets_visible": all(
            paths[name]["exists"] == 1 and paths[name]["is_dir"] == 1
            for name in ("persist_rfs_shared", "persist_rfs_msm_mpss", "persist_rfs_msm_adsp")
        ),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2101.collect_details(handoff)
    fields = prev2101.prev2098.prev2096.prev2083.prev2081.prev2059.prev2057.parse_fields()
    details["tftp_process_namespace_audit"] = collect_namespace(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2101.classify(handoff, hook, steps, details)
    ns = details.get("tftp_process_namespace_audit") if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    persist_auto_dir = intish(base.get("persist_auto_dir_error_count"))
    persist_mkdir = intish(base.get("persist_mkdir_failed_count"))
    all_persist_visible = bool(ns.get("all_persist_targets_visible"))
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0

    if not hook_ok:
        label = "tftp-process-namespace-artifact-hook-regression"
        passed = False
        reason = "V2102 artifact does not contain the bounded process namespace audit contract"
    elif intish(ns.get("audit_ok")) != 1:
        label = "tftp-process-namespace-audit-missing"
        passed = False
        reason = "stock tftp_server process namespace audit did not complete"
    elif wlan0:
        label = "tftp-process-namespace-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "tftp-process-namespace-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif not all_persist_visible and (persist_auto_dir > 0 or persist_mkdir > 0):
        label = "tftp-process-root-missing-persist-autodirs"
        passed = True
        reason = "stock tftp_server process root does not see all helper-created persist-RFS auto-dir targets"
    elif all_persist_visible and (persist_auto_dir > 0 or persist_mkdir > 0):
        label = "tftp-process-sees-persist-autodirs-but-eacces"
        passed = True
        reason = "stock tftp_server process root sees the persist-RFS targets, but startup still logs EACCES"
    else:
        label = "tftp-process-namespace-no-effect-post-up-server-check"
        passed = True
        reason = "process namespace audit completed; native still did not enter Android's ota_firewall/wlanmdsp branch"

    return {
        **base,
        "decision": f"v2103-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "namespace_audit_ok": intish(ns.get("audit_ok")),
        "tftp_pid": intish(ns.get("pid")),
        "all_persist_targets_visible": all_persist_visible,
        "mountinfo_match_count": intish(ns.get("mountinfo_match_count")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    ns = details.get("tftp_process_namespace_audit", {}) if isinstance(details.get("tftp_process_namespace_audit"), dict) else {}
    paths = ns.get("paths", {}) if isinstance(ns.get("paths"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2103 TFTP Process Namespace Audit Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2103`",
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
                ["namespace_audit", classification.get("namespace_audit_ok"), f"pid={classification.get('tftp_pid')} ns={ns.get('ns_mnt_target')} root={ns.get('root_target')}"],
                ["persist_targets_visible", classification.get("all_persist_targets_visible"), f"mountinfo_matches={classification.get('mountinfo_match_count')}"],
                ["persist_auto_dir", classification.get("persist_auto_dir_error_count"), f"mkdir_failed={classification.get('persist_mkdir_failed_count')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Process-Root Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "errno"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("errno")]
                for name, item in paths.items()
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- This unit only audits the already-running stock `tftp_server` process root and mountinfo after the V2102 startup wait.",
        "- No `tftp_server` ptrace, AP QMI send, DIAG, QRTR matrix, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- If the process root does not show the persist-RFS auto-dir targets, the next AP-infra fix is namespace/lifetime ordering, not modem QMI.",
        "- If the process root does show them and EACCES persists, the auto-dir failure is likely not the producer trigger; continue at the modem-internal pre-spawn state.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No macloader retry, passive DIAG, active DIAG mask/log-mode, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2102 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors, read-only tftp process-root audit, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2081() -> None:
    prev2101.prev2098.prev2096.prev2083.prev2081.CYCLE = CYCLE
    prev2101.prev2098.prev2096.prev2083.prev2081.OUT_DIR = OUT_DIR
    prev2101.prev2098.prev2096.prev2083.prev2081.HANDOFF_DIR = HANDOFF_DIR
    prev2101.prev2098.prev2096.prev2083.prev2081.HANDOFF_REPORT = HANDOFF_REPORT
    prev2101.prev2098.prev2096.prev2083.prev2081.REPORT_PATH = REPORT_PATH
    prev2101.prev2098.prev2096.prev2083.prev2081.V2080_OUT = V2102_OUT
    prev2101.prev2098.prev2096.prev2083.prev2081.V2080_INIT = V2102_INIT
    prev2101.prev2098.prev2096.prev2083.prev2081.V2080_BOOT = V2102_BOOT
    prev2101.prev2098.prev2096.prev2083.prev2081.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2101.prev2098.prev2096.prev2083.prev2081.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2101.prev2098.prev2096.prev2083.prev2081.TEST_LOG_PATH = TEST_LOG_PATH
    prev2101.prev2098.prev2096.prev2083.prev2081.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2101.prev2098.prev2096.prev2083.prev2081.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2101.prev2098.prev2096.prev2083.prev2081.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2101.prev2098.prev2096.prev2083.prev2081.artifact_hook_check = artifact_hook_check
    prev2101.prev2098.prev2096.prev2083.prev2081.collect_details = collect_details
    prev2101.prev2098.prev2096.prev2083.prev2081.classify = classify
    prev2101.prev2098.prev2096.prev2083.prev2081.render_report = render_report
    prev2101.prev2098.prev2096.prev2083.prev2081.configure_prev2059()


def main(argv: list[str] | None = None) -> int:
    configure_prev2081()
    return prev2101.prev2098.prev2096.prev2083.prev2081.prev2059.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
