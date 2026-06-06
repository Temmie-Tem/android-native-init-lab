#!/usr/bin/env python3
"""V2000 native downstream cascade handoff."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_any_readwrite_handoff_v1998 as prev1998


CYCLE = "V2000"
OUT_DIR = prev1998.prev1992.prev.repo_path("tmp/wifi/v2000-downstream-cascade-handoff")
HANDOFF_DIR = OUT_DIR / "v1999-handoff"
HANDOFF_REPORT = OUT_DIR / "v1999-handoff-report.md"
REPORT_PATH = prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2000_DOWNSTREAM_CASCADE_HANDOFF_2026-06-04.md"
)
V1999_OUT = prev1998.prev1992.prev.repo_path("tmp/wifi/v1999-downstream-cascade-test-boot")
V1999_INIT = V1999_OUT / "init_v1999_downstream_cascade"
V1999_BOOT = V1999_OUT / "boot_linux_v1999_downstream_cascade.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1999/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.182 (v1999-downstream-cascade)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1999.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1999.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1999-helper.result"

ORIGINAL_PATCH_PREV_MODULE = prev1998.patch_prev_module
ORIGINAL_COLLECT_DETAILS = prev1998.collect_details

EVIDENCE_FILES = (
    "test-v1393-helper-result.stdout.txt",
    "test-v1393-helper-result.stderr.txt",
    "test-v1393-log.stdout.txt",
    "test-v1393-log-hide-on-busy.stdout.txt",
    "test-v1393-summary.stdout.txt",
    "test-v1393-dmesg.stdout.txt",
    "test-wlan0.stdout.txt",
)

CASCADE_PATTERNS = {
    "wlan_pd_up": r"root_service_service_ind_cb.*msm/modem/wlan_pd.*0x1fffffff|wlan_pd.*0x1fffffff",
    "icnss_qmi_connected": r"icnss_qmi:\s+QMI Server Connected",
    "wlfw69": r"service\s*69|service=69|svc_id=0x45|svc_id=69|wlfw.*69|WLFW.*69",
    "cap_req": r"cap(?:ability)?[_ -]?req|send.*cap|capability.*request",
    "bdf": r"\bBDF\b|bdwlan|regdb|board data",
    "fw_ready": r"fw[_ -]?ready|firmware ready|FW ready",
    "wlan0": r"\bwlan0\b",
    "wlanmdsp_tftp": r"(tftp_server|tftp-server|tqftp).*wlanmdsp\.mbn|wlanmdsp\.mbn.*(tftp_server|tftp-server|tqftp)",
    "pd_load": r"(subsys-pil|q6v5|remoteproc).*wlan|wlanmdsp.*(load|loading|loaded|firmware|reset|Brought)|firmware.*wlanmdsp",
    "server_check": r"server_check\.txt|readwrite/server_check",
    "wlanmdsp_error": r"wlanmdsp\.mbn.*(fail|error|timeout|no such|not found|denied)",
    "external_degraded": r"esoc0_boot_failed|pcie_initialized|mhi_enable|MHI.*(state|enabled|init)|LTSSM",
}


def rel(path: Path) -> str:
    return prev1998.prev1992.prev.rel(path)


def evidence_paths() -> list[Path]:
    return [HANDOFF_DIR / name for name in EVIDENCE_FILES]


def read_path(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_evidence_text() -> str:
    return "\n".join(read_path(path) for path in evidence_paths())


def grep_count(pattern: str, paths: list[Path] | None = None) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    total = 0
    for path in paths or evidence_paths():
        if not path.exists():
            continue
        total += sum(1 for line in read_path(path).splitlines() if regex.search(line))
    return total


def grep_lines(pattern: str, limit: int = 8, paths: list[Path] | None = None) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    for path in paths or evidence_paths():
        if not path.exists():
            continue
        for line in read_path(path).splitlines():
            if regex.search(line):
                lines.append(f"{rel(path)}: {line[:500]}")
                if len(lines) >= limit:
                    return lines
    return lines


def parse_dmesg_timestamp(line: str) -> float | None:
    match = re.match(r"\[\s*([0-9]+(?:\.[0-9]+)?)\]", line)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def first_timestamp(pattern: str) -> float | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in read_path(HANDOFF_DIR / "test-v1393-dmesg.stdout.txt").splitlines():
        if regex.search(line):
            ts = parse_dmesg_timestamp(line)
            if ts is not None:
                return ts
    return None


def last_dmesg_timestamp() -> float | None:
    last: float | None = None
    for line in read_path(HANDOFF_DIR / "test-v1393-dmesg.stdout.txt").splitlines():
        ts = parse_dmesg_timestamp(line)
        if ts is not None:
            last = ts
    return last


def any_field_positive(fields: dict[str, str], suffix: str, prefixes: tuple[str, ...]) -> bool:
    return any(
        prev1998.prev1992.prev.intish(fields.get(f"{prefix}.{suffix}")) > 0
        for prefix in prefixes
    )


def helper_timeout_sec(fields: dict[str, str]) -> str:
    if fields.get("timeout_sec"):
        return fields["timeout_sec"]
    match = re.search(r"\bmode=[^\n]*\btimeout_sec=(\d+)", read_evidence_text())
    return match.group(1) if match else ""


def collect_cascade(fields: dict[str, str], details: dict[str, Any]) -> dict[str, Any]:
    dmesg_paths = [HANDOFF_DIR / "test-v1393-dmesg.stdout.txt"]
    up_ts = first_timestamp(CASCADE_PATTERNS["wlan_pd_up"])
    last_ts = last_dmesg_timestamp()
    post_up_hold_sec = None if up_ts is None or last_ts is None else max(0.0, last_ts - up_ts)
    prefixes = (
        "wlan_pd_cnss_nonlog_control_flow",
        "wlan_pd_service_window_trigger",
        "wlan_pd_pm_service_window_trigger",
        "wlan_pd_service_object_visible_trigger",
    )
    cnss_running = any_field_positive(fields, "cnss_daemon_running", prefixes) or any_field_positive(
        fields,
        "cnss_daemon_started",
        prefixes,
    )
    tftp_fields = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    requested_wlanmdsp_field = prev1998.prev1992.prev.intish(tftp_fields.get("requested_wlanmdsp"))
    requested_server_check_field = prev1998.prev1992.prev.intish(tftp_fields.get("requested_server_check"))
    requested_any_field = prev1998.prev1992.prev.intish(tftp_fields.get("requested_any"))
    tokenized_wlanmdsp_lines = grep_count(CASCADE_PATTERNS["wlanmdsp_tftp"])
    requested_wlanmdsp = bool(
        (details.get("wlanmdsp_trace") or {}).get("requested")
        or requested_wlanmdsp_field > 0
        or tokenized_wlanmdsp_lines > 0
    )
    cascade = {
        "helper_timeout_sec": helper_timeout_sec(fields),
        "start_order": fields.get("wifi_companion_start.order", ""),
        "child_started": fields.get("wifi_companion_start.child_started", ""),
        "cnss_daemon_running": cnss_running,
        "wlan_pd_up": grep_count(CASCADE_PATTERNS["wlan_pd_up"], dmesg_paths),
        "icnss_qmi_connected": grep_count(CASCADE_PATTERNS["icnss_qmi_connected"], dmesg_paths),
        "wlfw69": grep_count(CASCADE_PATTERNS["wlfw69"], dmesg_paths),
        "cap_req": grep_count(CASCADE_PATTERNS["cap_req"], dmesg_paths),
        "bdf": grep_count(CASCADE_PATTERNS["bdf"], dmesg_paths),
        "fw_ready": grep_count(CASCADE_PATTERNS["fw_ready"], dmesg_paths),
        "wlan0": grep_count(CASCADE_PATTERNS["wlan0"], dmesg_paths),
        "wlanmdsp_tftp": tokenized_wlanmdsp_lines,
        "pd_load": grep_count(CASCADE_PATTERNS["pd_load"], dmesg_paths),
        "server_check_request": requested_server_check_field,
        "requested_any": requested_any_field,
        "wlanmdsp_error": grep_count(CASCADE_PATTERNS["wlanmdsp_error"]),
        "external_degraded": grep_count(CASCADE_PATTERNS["external_degraded"], dmesg_paths),
        "requested_wlanmdsp": requested_wlanmdsp,
        "wlan_pd_up_ts": up_ts,
        "last_dmesg_ts": last_ts,
        "post_up_hold_sec": post_up_hold_sec,
        "post_up_hold_ge_30": post_up_hold_sec is not None and post_up_hold_sec >= 30.0,
        "first_wlan_pd_up_lines": grep_lines(CASCADE_PATTERNS["wlan_pd_up"], limit=4, paths=dmesg_paths),
        "first_icnss_qmi_lines": grep_lines(CASCADE_PATTERNS["icnss_qmi_connected"], limit=4, paths=dmesg_paths),
        "first_wlanmdsp_tftp_lines": grep_lines(CASCADE_PATTERNS["wlanmdsp_tftp"], limit=6),
        "first_pd_load_lines": grep_lines(CASCADE_PATTERNS["pd_load"], limit=6, paths=dmesg_paths),
        "first_wlfw69_lines": grep_lines(CASCADE_PATTERNS["wlfw69"], limit=6, paths=dmesg_paths),
        "first_bdf_lines": grep_lines(CASCADE_PATTERNS["bdf"], limit=6, paths=dmesg_paths),
        "first_fw_ready_lines": grep_lines(CASCADE_PATTERNS["fw_ready"], limit=6, paths=dmesg_paths),
        "first_wlan0_lines": grep_lines(CASCADE_PATTERNS["wlan0"], limit=6, paths=dmesg_paths),
        "first_errors": grep_lines(CASCADE_PATTERNS["wlanmdsp_error"], limit=6),
    }
    return cascade


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v1999",
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
        "a90_android_execns_probe v369",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.order=%s",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
        "libqmi_get_service_list_lookup_call",
        "wlfw_client_init_instance_call",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1999_INIT, init_required), (V1999_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V1999_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == "a90_android_execns_probe v369"
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
    details["cascade"] = collect_cascade(fields, details)
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
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(base.get("combined"))
        and bool(bridge.get("ok"))
        and bool(helper.get("ok"))
        and bool(readwrite.get("ok"))
    )
    if not route_ok:
        label = "native-downstream-cascade-route-regression"
        return {
            **base,
            "label": label,
            "decision": f"v2000-{label}-rollback-blocked",
            "pass": False,
            "reason": "V1999 route did not preserve clean-DSP/PM/CNSS/RFS bridge prerequisites or rollback verification",
            "helper_completion_ok": bool(helper.get("ok")),
            "readwrite_bridge_ok": bool(readwrite.get("ok")),
            "rfs_bridge_ok": bool(bridge.get("ok")),
        }
    if int(cascade.get("wlan0", 0)) > 0:
        label = "native-downstream-cascade-wlan0-progress"
        reason = "V1999 reached wlan0 under the rootfs-only RFS bridges; stop before scan/connect until explicitly gated"
    elif int(cascade.get("fw_ready", 0)) > 0 or int(cascade.get("bdf", 0)) > 0:
        label = "native-downstream-cascade-bdf-fw-progress"
        reason = "V1999 crossed WLFW downstream into BDF/FW-ready progress but did not prove wlan0"
    elif int(cascade.get("wlfw69", 0)) > 0:
        label = "native-downstream-cascade-wlfw69-progress"
        reason = "V1999 reached WLFW service69 publication; downstream path is alive and should be chased to BDF/FW-ready/wlan0"
    elif int(cascade.get("wlan_pd_up", 0)) == 0:
        label = "native-downstream-cascade-wlan-pd-up-regression"
        reason = "V1999 preserved bridges but failed to reproduce WLAN-PD UP"
    elif not bool(cascade.get("cnss_daemon_running")):
        label = "native-downstream-cascade-cnss-daemon-not-running"
        reason = "WLAN-PD reached UP, but stock cnss-daemon was not confirmed running in the cascade window"
    elif not bool(cascade.get("post_up_hold_ge_30")):
        label = "native-downstream-cascade-window-insufficient"
        reason = "WLAN-PD reached UP, but the captured dmesg window did not prove at least 30s of post-UP hold"
    elif bool(cascade.get("requested_wlanmdsp")) and int(cascade.get("wlanmdsp_error", 0)) == 0:
        label = "native-downstream-cascade-wlanmdsp-served-no-wlfw69"
        reason = "WLAN-PD reached UP and wlanmdsp tftp evidence appeared, but WLFW service69/BDF/FW-ready/wlan0 did not follow"
    else:
        label = "native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69"
        reason = "WLAN-PD reached UP with cnss-daemon running and a long post-UP hold, but no tokenized wlanmdsp tftp or WLFW69 cascade appeared"
    return {
        **base,
        "label": label,
        "decision": f"v2000-{label}-rollback-pass",
        "pass": True,
        "reason": reason,
        "helper_completion_ok": True,
        "readwrite_bridge_ok": True,
        "rfs_bridge_ok": True,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    readwrite = details["readwrite_bridge"]
    light = trace["light_observer"]
    rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper_completion", classification.get("helper_completion_ok"), f"version={details['helper_completion']['result_file_version']} probe_rc={details['helper_completion']['probe_run_rc']} child_exit={details['helper_completion']['child_exit_code']} timed_out={details['helper_completion']['timed_out']}"],
        ["readonly_bridge", classification.get("rfs_bridge_ok"), f"exact_exists={bridge['exact_exists']} nonzero={bridge['exact_nonzero']} open_rc={bridge['exact_open_rc']} sda29_write={bridge['sda29_write']}"],
        ["readwrite_bridge", classification.get("readwrite_bridge_ok"), f"exists={readwrite['readwrite_exists']} mode={readwrite['readwrite_mode']} uid={readwrite['readwrite_uid']} gid={readwrite['readwrite_gid']} tmpfs={readwrite['readwrite_tmpfs_requested']} server_check_exists={readwrite['server_check_exists']}"],
        ["consumer_chain", cascade["cnss_daemon_running"], f"order={cascade['start_order']} child_started={cascade['child_started']}"],
        ["post_up_window", cascade["post_up_hold_ge_30"], f"up_ts={cascade['wlan_pd_up_ts']} last_ts={cascade['last_dmesg_ts']} post_up_sec={cascade['post_up_hold_sec']}"],
        ["cascade_counts", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} cap={cascade['cap_req']} bdf={cascade['bdf']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["tftp_request_evidence", cascade["requested_wlanmdsp"], f"wlanmdsp_tftp={cascade['wlanmdsp_tftp']} server_check_request={cascade['server_check_request']} requested_any={cascade['requested_any']} errors={cascade['wlanmdsp_error']} field={trace['requested_field']}"],
        ["pd_load_markers", cascade["pd_load"], "wlanmdsp/PIL WLAN load markers in dmesg"],
        ["light_observer", classification["light_ok"], f"servloc={light['servloc_domain_list_probe']} servnotif={light['service_notifier_listener_probe']} qrtr_send={light['qrtr_readback_send_attempted']} result={light['qrtr_readback_result']}"],
        ["combined_prereq", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["external_degraded_watch", cascade["external_degraded"], "pcie_initialized/mhi_enable/esoc0_boot_failed/LTSSM only"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2000 Downstream Cascade Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2000`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        prev1998.prev1992.prev.markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "",
        "## First WLAN-PD UP Lines",
        "",
        *(f"- `{line}`" for line in cascade["first_wlan_pd_up_lines"]),
        *([] if cascade["first_wlan_pd_up_lines"] else ["- `none`"]),
        "",
        "## First ICNSS QMI Lines",
        "",
        *(f"- `{line}`" for line in cascade["first_icnss_qmi_lines"]),
        *([] if cascade["first_icnss_qmi_lines"] else ["- `none`"]),
        "",
        "## First Wlanmdsp TFTP Lines",
        "",
        *(f"- `{line}`" for line in cascade["first_wlanmdsp_tftp_lines"]),
        *([] if cascade["first_wlanmdsp_tftp_lines"] else ["- `none`"]),
        "",
        "## First PD Load Lines",
        "",
        *(f"- `{line}`" for line in cascade["first_pd_load_lines"]),
        *([] if cascade["first_pd_load_lines"] else ["- `none`"]),
        "",
        "## First WLFW69 Lines",
        "",
        *(f"- `{line}`" for line in cascade["first_wlfw69_lines"]),
        *([] if cascade["first_wlfw69_lines"] else ["- `none`"]),
        "",
        "## First BDF/FW/Wlan0 Lines",
        "",
        *(f"- `{line}`" for line in cascade["first_bdf_lines"]),
        *(f"- `{line}`" for line in cascade["first_fw_ready_lines"]),
        *(f"- `{line}`" for line in cascade["first_wlan0_lines"]),
        *([] if (cascade["first_bdf_lines"] or cascade["first_fw_ready_lines"] or cascade["first_wlan0_lines"]) else ["- `none`"]),
        "",
        "## Branch",
        "",
        "- `native-downstream-cascade-wlfw69-progress`: downstream WLFW published; chase BDF/FW-ready/wlan0 next.",
        "- `native-downstream-cascade-bdf-fw-progress`: BDF/FW progressed; chase `wlan0` only, still no scan/connect.",
        "- `native-downstream-cascade-wlan0-progress`: stop before credentials/scan/connect until a dedicated gated unit.",
        "- `native-downstream-cascade-wlanmdsp-served-no-wlfw69`: WLAN image path progressed but QMI publication did not; inspect PD load/integrity.",
        "- `native-downstream-cascade-wlan-pd-up-no-wlanmdsp-token-no-wlfw69`: WLAN-PD UP is real, but no tokenized wlanmdsp request or WLFW cascade was observed in the long window.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or tftp_server ptrace was run.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1999 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev1998.CYCLE = CYCLE
    prev1998.OUT_DIR = OUT_DIR
    prev1998.HANDOFF_DIR = HANDOFF_DIR
    prev1998.HANDOFF_REPORT = HANDOFF_REPORT
    prev1998.REPORT_PATH = REPORT_PATH
    prev1998.V1997_OUT = V1999_OUT
    prev1998.V1997_INIT = V1999_INIT
    prev1998.V1997_BOOT = V1999_BOOT
    prev1998.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1998.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1998.TEST_LOG_PATH = TEST_LOG_PATH
    prev1998.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1998.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1998.artifact_hook_check = artifact_hook_check
    prev1998.collect_details = collect_details
    prev1998.classify = classify
    prev1998.render_report = render_report
    ORIGINAL_PATCH_PREV_MODULE()


def main(argv: list[str] | None = None) -> int:
    prev1998.patch_prev_module = patch_prev_module
    return prev1998.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
