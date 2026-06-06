#!/usr/bin/env python3
"""V2025 rollbackable handoff for Android-parity RFS fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_post_bdf_tail_handoff_v2007 as prev2007


CYCLE = "V2025"
OUT_DIR = prev2007.prev2005.prev2000.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2025-rfs-android-fallback-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2024-handoff"
HANDOFF_REPORT = OUT_DIR / "v2024-handoff-report.md"
REPORT_PATH = prev2007.prev2005.prev2000.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2025_RFS_ANDROID_FALLBACK_HANDOFF_2026-06-04.md"
)
V2024_OUT = prev2007.prev2005.prev2000.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2024-rfs-android-fallback-test-boot"
)
V2024_INIT = V2024_OUT / "init_v2024_rfs_android_fallback"
V2024_BOOT = V2024_OUT / "boot_linux_v2024_rfs_android_fallback.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2024/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.194 (v2024-rfs-android-fallback)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2024.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2024.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2024-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v381"


prev2000 = prev2007.prev2000
prev1998 = prev2007.prev1998


def rel(path: Path) -> str:
    return prev2007.rel(path)


def intish(value: object) -> int:
    return prev1998.prev1992.prev.intish(value)


def hit(events: dict[str, dict[str, str]], name: str) -> int:
    return prev2007.hit(events, name)


def is_zero(value: str) -> bool:
    return prev2007.is_zero(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2024",
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
        *init_required,
        EXPECTED_HELPER_VERSION,
        "wlfw_bdf_return",
        "wlfw_cal_report_entry",
        "wlfw_cal_report_return",
        "dms_get_wlan_address_entry",
        "dms_service_request_send_ret",
        "wlan_send_status_entry",
        "wlan_send_version_entry",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "android_parity=firmware_mnt_probe_absent_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2024_INIT, init_required), (V2024_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2024_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {
                "exists": False,
                "ok": False,
                "missing": list(required),
                "forbidden": [],
            }
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {
            "exists": True,
            "ok": not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def patch_bridge_from_fields(details: dict[str, Any], fields: dict[str, str]) -> None:
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    bridge.update({
        "android_parity": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.android_parity", ""),
        "probe_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.host_path", ""),
        "probe_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.exists")),
        "probe_nonzero": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.nonzero")),
        "probe_open_rc": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.open_rc", ""),
        "probe_open_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.probe.open_errno", ""),
        "fallback_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.host_path", ""),
        "fallback_exists": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.exists")),
        "fallback_nonzero": intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.nonzero")),
        "fallback_size": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.size", ""),
        "fallback_open_rc": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.open_rc", ""),
        "fallback_open_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.fallback.open_errno", ""),
    })
    bridge["ok"] = (
        bridge.get("android_parity") == "firmware_mnt_probe_absent_firmware_fallback_present"
        and bridge.get("probe_exists") == 0
        and str(bridge.get("probe_open_rc")) == "-1"
        and str(bridge.get("probe_open_errno")) == "2"
        and bridge.get("fallback_exists") == 1
        and bridge.get("fallback_nonzero") == 1
        and str(bridge.get("fallback_open_rc")) == "0"
        and intish(bridge.get("rootfs_namespace_only")) == 1
        and intish(bridge.get("sda29_write")) == 0
    )
    if bridge["ok"]:
        trace["served"] = True
        trace["served_nonzero"] = True
    trace["rfs_bridge"] = bridge
    details["wlanmdsp_trace"] = trace


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = prev2007.ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == EXPECTED_HELPER_VERSION
        helper["ok"] = bool(
            helper.get("text_present")
            and helper.get("version_ok")
            and helper.get("probe_run_rc_ok")
            and helper.get("child_exit_code_ok")
            and helper.get("child_signal_ok")
            and helper.get("test_flash_ok")
            and helper.get("rollback_version_ok")
            and helper.get("rollback_selftest_fail_zero")
        )
    patch_bridge_from_fields(details, fields)
    details["cascade"] = prev2000.collect_cascade(fields, details)
    details["post_bdf_tail"] = prev2007.collect_post_bdf_tail(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev1998.ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    readwrite = details.get("readwrite_bridge") if isinstance(details.get("readwrite_bridge"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    post = details.get("post_bdf_tail") if isinstance(details.get("post_bdf_tail"), dict) else {}
    cap = post.get("cap_events") if isinstance(post.get("cap_events"), dict) else {}
    bdf = post.get("bdf_events") if isinstance(post.get("bdf_events"), dict) else {}
    tail = post.get("tail_events") if isinstance(post.get("tail_events"), dict) else {}
    cap_bdf_cal_success = (
        hit(cap, "wlfw_cap_success_branch") > 0
        and hit(bdf, "wlfw_bdf_return") > 0
        and is_zero(str(post.get("bdf_return_rc", "")))
        and hit(tail, "wlfw_cal_report_return") > 0
        and is_zero(str(post.get("cal_return_rc", "")))
    )
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(bridge.get("ok"))
        and bool(helper.get("ok"))
        and bool(readwrite.get("ok"))
    )
    if not route_ok:
        label = "rfs-android-fallback-route-regression"
        reason = "V2024 did not preserve rollback, light observer, Android-parity RFS fallback, readwrite bridge, or helper prerequisites"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "rfs-android-fallback-wlan0-progress"
        reason = "Android-parity RFS fallback reached real wlan0; stop before credentials/scan/connect until the next gated unit"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "rfs-android-fallback-fw-ready-progress"
        reason = "Android-parity RFS fallback reached firmware-ready progress but not wlan0"
        passed = True
    elif intish(cascade.get("bdf")) > 0 or cap_bdf_cal_success:
        label = "rfs-android-fallback-post-cal-no-fw-ready"
        reason = "Android-parity RFS fallback preserved cap/BDF/cal success, but no FW-ready or wlan0 cascade followed"
        passed = True
    elif intish(cascade.get("wlfw69")) > 0:
        label = "rfs-android-fallback-wlfw69-no-bdf"
        reason = "WLFW service appeared after Android-parity RFS fallback, but BDF/FW-ready/wlan0 did not follow"
        passed = True
    else:
        label = "rfs-android-fallback-no-wlfw69"
        reason = "Android-parity RFS fallback was installed, wlan_pd/ICNSS came up, but WLFW69/FW-ready/wlan0 did not follow"
        passed = True
    return {
        **base,
        "label": label,
        "decision": f"v2025-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "helper_completion_ok": bool(helper.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "route_ok": route_ok,
        "cap_bdf_cal_success": cap_bdf_cal_success,
    }


def rows_to_md(rows: list[list[object]]) -> str:
    return prev1998.prev1992.prev.markdown_table(
        ["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]
    )


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    cascade = details["cascade"]
    post = details["post_bdf_tail"]
    if classification["label"] == "rfs-android-fallback-wlan0-progress":
        interpretation_lines = [
            "- The Android-parity RFS fallback crossed to real `wlan0`; the next unit may gate HAL/scan/connect.",
        ]
    elif classification["label"] == "rfs-android-fallback-fw-ready-progress":
        interpretation_lines = [
            "- The Android-parity RFS fallback crossed firmware-ready but not interface creation.",
            "- Next bounded unit should stay downstream-only and inspect the kernel/CNSS `wlan0` creation tail.",
        ]
    elif classification["label"] == "rfs-android-fallback-post-cal-no-fw-ready":
        interpretation_lines = [
            "- The bridge now matches Android's served path semantics: first `firmware_mnt/image` probe absent, fallback `vendor/firmware` path present.",
            "- Cap/BDF/cal still return success, but FW-ready/`wlan0` do not appear; the blocker remains after successful WLFW downstream sends.",
        ]
    else:
        interpretation_lines = [
            "- The bridge now matches Android's served path semantics, but no visible WLFW/FW-ready/`wlan0` cascade followed.",
            "- Next bounded unit should measure the non-ptrace TFTP completion edge or modem-side firmware acceptance without returning to AP-side RIL/QMI captures.",
        ]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']}"],
        ["rfs_probe", bridge.get("probe_exists") == 0, f"path={bridge.get('probe_path')} open_rc={bridge.get('probe_open_rc')} errno={bridge.get('probe_open_errno')}"],
        ["rfs_fallback", classification.get("rfs_bridge_ok"), f"path={bridge.get('fallback_path')} exists={bridge.get('fallback_exists')} size={bridge.get('fallback_size')} open_rc={bridge.get('fallback_open_rc')} sda29={bridge.get('sda29_write')}"],
        ["readwrite", classification.get("readwrite_bridge_ok"), f"server_check={details['readwrite_bridge']['server_check_exists']} tmpfs={details['readwrite_bridge']['readwrite_tmpfs_requested']}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} bdf={cascade.get('bdf')} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["firmware", "", f"requested_any={cascade['requested_any']} wlanmdsp_tftp={cascade['wlanmdsp_tftp']} pd_load={cascade['pd_load']} requested={cascade['requested_wlanmdsp']}"],
        ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']}"],
        ["status_version", "", f"status={post['status_return_rc']} version={post['version_return_rc']} dms_req={post['dms_req_send_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2025 RFS Android Fallback Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2025`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        rows_to_md(matrix_rows),
        "",
        "## Interpretation",
        "",
        *interpretation_lines,
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No tftp_server ptrace, rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2024 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2007() -> None:
    prev2007.CYCLE = CYCLE
    prev2007.OUT_DIR = OUT_DIR
    prev2007.HANDOFF_DIR = HANDOFF_DIR
    prev2007.HANDOFF_REPORT = HANDOFF_REPORT
    prev2007.REPORT_PATH = REPORT_PATH
    prev2007.V2006_OUT = V2024_OUT
    prev2007.V2006_INIT = V2024_INIT
    prev2007.V2006_BOOT = V2024_BOOT
    prev2007.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2007.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2007.TEST_LOG_PATH = TEST_LOG_PATH
    prev2007.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2007.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2007.artifact_hook_check = artifact_hook_check
    prev2007.collect_details = collect_details
    prev2007.classify = classify
    prev2007.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2007()
    return prev2007.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
