#!/usr/bin/env python3
"""V2046 rollbackable handoff for fallback-RFS + persist-RFS + mcfg route."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_rfs_fallback_logdw_transfer_handoff_v2035 as prev2035


CYCLE = "V2046"
OUT_DIR = prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2046-fallback-persist-rfs-mcfg-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2045-handoff"
HANDOFF_REPORT = OUT_DIR / "v2045-handoff-report.md"
REPORT_PATH = prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2046_FALLBACK_PERSIST_RFS_MCFG_HANDOFF_2026-06-04.md"
)
V2045_OUT = prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2045-fallback-persist-rfs-mcfg-test-boot"
)
V2045_INIT = V2045_OUT / "init_v2045_fallback_persist_rfs_mcfg"
V2045_BOOT = V2045_OUT / "boot_linux_v2045_fallback_persist_rfs_mcfg.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2045/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.203 (v2045-fallback-persist-rfs-mcfg)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2045.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2045.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2045-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v388"

ORIGINAL_V2035_COLLECT = prev2035.collect_details
ORIGINAL_V2035_CLASSIFY = prev2035.classify


def rel(path: Path) -> str:
    return prev2035.rel(path)


def intish(value: object) -> int:
    return prev2035.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2035.prev1998.prev1992.prev.markdown_table(
        headers,
        [[str(cell) for cell in row] for row in rows],
    )


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2045",
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
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "android_parity=firmware_mnt_probe_absent_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "persist_rfs.tmpfs_requested=1",
        "persist_rfs.path=/mnt/vendor/persist/rfs",
        "persist_hlos_rfs.path=/mnt/vendor/persist/hlos_rfs",
        "persist_rfs.readwrite.host_path=",
        "persist_hlos_rfs.readwrite.host_path=",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
        "wlfw_cal_report_return",
        "wlfw_worker_cal_only_call",
        "wlfw_worker_done_signal",
        "wlfw_qmi_ind_cb_entry",
        "wlfw_handle_ind_entry",
        "tftp_logdw_sink.begin=1",
        "tftp_logdw_sink.socket=/dev/socket/logdw",
        "tftp_logdw_sink.ptraced=0",
        "tftp_logdw_sink.qmi_send=0",
        "tftp_logdw_sink.qrtr_send=0",
        "tftp_logdw_sink.summary.fallback_wlanmdsp=%u",
        "tftp_mcfg_readback.begin=1",
        "tftp_mcfg_readback.mode=read-only-post-wrq-stat-open-read",
        "tftp_mcfg_readback.summary.post_wrq_sampled=%d",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2045_INIT, init_required), (V2045_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2045_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_mcfg_readback(fields: dict[str, str]) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    for index in range(12):
        prefix = f"tftp_mcfg_readback.sample_{index:03d}"
        phase = fields.get(f"{prefix}.phase")
        if phase is None:
            continue
        samples.append({
            "index": index,
            "phase": phase,
            "path": fields.get(f"{prefix}.path", ""),
            "exists": intish(fields.get(f"{prefix}.exists")),
            "is_reg": intish(fields.get(f"{prefix}.is_reg")),
            "size": intish(fields.get(f"{prefix}.size")),
            "mode": fields.get(f"{prefix}.mode", ""),
            "stat_errno": intish(fields.get(f"{prefix}.stat_errno")),
            "open_rc": intish(fields.get(f"{prefix}.open_rc")),
            "open_errno": intish(fields.get(f"{prefix}.open_errno")),
            "read_len": intish(fields.get(f"{prefix}.read_len")),
            "read_errno": intish(fields.get(f"{prefix}.read_errno")),
            "payload": fields.get(f"{prefix}.payload", "")[:120],
        })
    post_wrq = next((sample for sample in samples if sample["phase"] == "post-wrq-stats"), {})
    final = next((sample for sample in reversed(samples) if sample["phase"] == "final-stop"), {})
    post_wrq_sampled = max(
        intish(fields.get("tftp_mcfg_readback.summary.post_wrq_sampled")),
        1 if post_wrq else 0,
    )
    return {
        "begin": intish(fields.get("tftp_mcfg_readback.begin")),
        "end": intish(fields.get("tftp_mcfg_readback.end")),
        "mode": fields.get("tftp_mcfg_readback.mode", ""),
        "path": fields.get("tftp_mcfg_readback.path", ""),
        "sample_count": len(samples),
        "summary_samples": intish(fields.get("tftp_mcfg_readback.summary.samples")),
        "post_wrq_sampled": post_wrq_sampled,
        "post_wrq": post_wrq,
        "final": final,
        "samples": samples,
    }


def collect_persist_rfs(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_firmware_serve_gate.rfs_bridge"
    return {
        "tmpfs_requested": intish(fields.get(f"{prefix}.persist_rfs.tmpfs_requested")),
        "rfs_path": fields.get(f"{prefix}.persist_rfs.host_path", ""),
        "rfs_exists": intish(fields.get(f"{prefix}.persist_rfs.exists")),
        "rfs_is_dir": intish(fields.get(f"{prefix}.persist_rfs.is_dir")),
        "rfs_mode": fields.get(f"{prefix}.persist_rfs.mode", ""),
        "rfs_uid": fields.get(f"{prefix}.persist_rfs.uid", ""),
        "rfs_gid": fields.get(f"{prefix}.persist_rfs.gid", ""),
        "rfs_errno": intish(fields.get(f"{prefix}.persist_rfs.errno")),
        "hlos_path": fields.get(f"{prefix}.persist_hlos_rfs.host_path", ""),
        "hlos_exists": intish(fields.get(f"{prefix}.persist_hlos_rfs.exists")),
        "hlos_is_dir": intish(fields.get(f"{prefix}.persist_hlos_rfs.is_dir")),
        "hlos_mode": fields.get(f"{prefix}.persist_hlos_rfs.mode", ""),
        "hlos_uid": fields.get(f"{prefix}.persist_hlos_rfs.uid", ""),
        "hlos_gid": fields.get(f"{prefix}.persist_hlos_rfs.gid", ""),
        "hlos_errno": intish(fields.get(f"{prefix}.persist_hlos_rfs.errno")),
        "rfs_readwrite_path": fields.get(f"{prefix}.persist_rfs.readwrite.host_path", ""),
        "rfs_readwrite_exists": intish(fields.get(f"{prefix}.persist_rfs.readwrite.exists")),
        "rfs_readwrite_is_dir": intish(fields.get(f"{prefix}.persist_rfs.readwrite.is_dir")),
        "rfs_readwrite_errno": intish(fields.get(f"{prefix}.persist_rfs.readwrite.errno")),
        "hlos_readwrite_path": fields.get(f"{prefix}.persist_hlos_rfs.readwrite.host_path", ""),
        "hlos_readwrite_exists": intish(fields.get(f"{prefix}.persist_hlos_rfs.readwrite.exists")),
        "hlos_readwrite_is_dir": intish(fields.get(f"{prefix}.persist_hlos_rfs.readwrite.is_dir")),
        "hlos_readwrite_errno": intish(fields.get(f"{prefix}.persist_hlos_rfs.readwrite.errno")),
    }


def persist_ok(persist: dict[str, Any]) -> bool:
    return bool(
        persist.get("tmpfs_requested") == 1
        and persist.get("rfs_exists") == 1
        and persist.get("rfs_is_dir") == 1
        and persist.get("hlos_exists") == 1
        and persist.get("hlos_is_dir") == 1
        and persist.get("rfs_readwrite_exists") == 1
        and persist.get("rfs_readwrite_is_dir") == 1
        and persist.get("hlos_readwrite_exists") == 1
        and persist.get("hlos_readwrite_is_dir") == 1
    )


def collect_icnss_ipc(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_icnss_ipc_snapshot.after_post_listener_window.debugfs_ipc_logging"
    return {
        "wlfw_server_arrive": fields.get(f"{prefix}.wlfw_server_arrive", ""),
        "wlfw_server_arrive_seen": intish(fields.get(f"{prefix}.wlfw_server_arrive")) > 0,
        "service69_text": fields.get(f"{prefix}.service69_text", ""),
        "first_focus_line": fields.get(f"{prefix}.first_focus_line", ""),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_V2035_COLLECT(handoff)
    fields = prev2035.prev1998.parse_fields(prev2035.prev1998.read_helper_text())
    details["mcfg_readback"] = collect_mcfg_readback(fields)
    details["persist_rfs_bridge"] = collect_persist_rfs(fields)
    details["icnss_ipc"] = collect_icnss_ipc(fields)
    return details


def logdw_summary(details: dict[str, Any]) -> dict[str, Any]:
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    return logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}


def wlanmdsp_transfer_complete(summary: dict[str, Any]) -> bool:
    return bool(
        intish(summary.get("fallback_wlanmdsp")) > 0
        and (
            intish(summary.get("end_transfer")) > 0
            or intish(summary.get("success")) > 0
            or intish(summary.get("total_bytes_4251884")) > 0
        )
    )


def mcfg_readable(readback: dict[str, Any]) -> bool:
    samples = readback.get("samples") if isinstance(readback.get("samples"), list) else []
    return any(
        intish(sample.get("exists")) > 0
        and intish(sample.get("size")) > 0
        and intish(sample.get("read_len")) > 0
        for sample in samples
        if isinstance(sample, dict)
    )


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_V2035_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    post = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    persist = details.get("persist_rfs_bridge") if isinstance(details.get("persist_rfs_bridge"), dict) else {}
    readback = details.get("mcfg_readback") if isinstance(details.get("mcfg_readback"), dict) else {}
    summary = logdw_summary(details)
    records = (details.get("tftp_logdw") or {}).get("records") if isinstance(details.get("tftp_logdw"), dict) else []
    lchown_failures = sum(1 for record in records if "lchown fail" in str(record.get("payload", "")))
    transfer_complete = wlanmdsp_transfer_complete(summary)
    wlanmdsp_seen = intish(summary.get("fallback_wlanmdsp")) > 0 or intish(summary.get("wlanmdsp")) > 0
    mcfg_seen = intish(summary.get("mcfg")) > 0 or intish(readback.get("sample_count")) > 0
    mcfg_wrq_success = intish(summary.get("mcfg")) > 0 and intish(summary.get("total_bytes")) > 0
    readable = mcfg_readable(readback)
    initial_tftp_seen = (
        intish(summary.get("server_check")) > 0
        or intish(summary.get("mcfg")) > 0
        or intish(summary.get("datagrams")) > 0
    )
    mcfg_observer_ok = intish(readback.get("begin")) == 1
    post_up_long = bool(cascade.get("post_up_hold_ge_30"))
    route_ok = (
        bool(base.get("route_ok"))
        and persist_ok(persist)
        and mcfg_observer_ok
        and post_up_long
    )

    if not route_ok:
        label = "fallback-persist-rfs-route-regression"
        reason = "V2045 did not preserve rollback, fallback readonly path, readwrite tmpfs, persist-RFS mirrors, mcfg observer, passive logdw, cnss-daemon, or the long post-UP window"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "fallback-persist-rfs-wlan0-progress"
        reason = "fallback-only RFS plus persist mirrors and stock cnss-daemon reached wlan0; stop before scan/connect until the dedicated Wi-Fi gate"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "fallback-persist-rfs-fw-ready-progress"
        reason = "fallback-only RFS plus persist mirrors crossed into firmware-ready progress"
        passed = True
    elif transfer_complete:
        label = "fallback-persist-rfs-fallback-wlanmdsp-transfer-complete-no-fw-ready"
        reason = "the Android-parity fallback `wlanmdsp.mbn` transfer completed, but FW-ready/wlan0 did not follow in the long lower window"
        passed = True
    elif wlanmdsp_seen:
        label = "fallback-persist-rfs-fallback-wlanmdsp-request-no-complete"
        reason = "the modem requested fallback `wlanmdsp.mbn`, but no transfer-complete marker or FW-ready/wlan0 followed"
        passed = True
    elif readable:
        label = "fallback-persist-rfs-mcfg-readable-no-wlanmdsp"
        reason = "fallback-only RFS, persist mirrors, stock cnss-daemon, and long hold were present; `mcfg.tmp` became readable but the modem still did not request `wlanmdsp.mbn`"
        passed = True
    elif mcfg_wrq_success and lchown_failures == 0:
        label = "fallback-persist-rfs-mcfg-wrq-success-absent-no-wlanmdsp"
        reason = "native accepted the modem's `mcfg.tmp` WRQ with persist mirrors and no setup failures, but post-WRQ readback found no file and the modem did not request `wlanmdsp.mbn`"
        passed = True
    elif mcfg_seen and lchown_failures == 0:
        label = "fallback-persist-rfs-mcfg-no-wlanmdsp"
        reason = "persist mirrors removed native-only setup failures and mcfg traffic occurred, but the modem still did not request `wlanmdsp.mbn`"
        passed = True
    elif initial_tftp_seen:
        label = "fallback-persist-rfs-initial-tftp-no-wlanmdsp"
        reason = "the modem reached initial TFTP traffic under the fallback-persist route, but no `wlanmdsp.mbn` request followed"
        passed = True
    else:
        label = "fallback-persist-rfs-zero-tokenized-tftp"
        reason = "the fallback-persist route reached the long lower window, but passive logdw saw no tokenized TFTP traffic"
        passed = True

    return {
        **base,
        "label": label,
        "decision": f"v2046-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "persist_rfs_ok": persist_ok(persist),
        "mcfg_observer_ok": mcfg_observer_ok,
        "mcfg_readable": readable,
        "initial_tftp_seen": initial_tftp_seen,
        "wlanmdsp_seen": wlanmdsp_seen,
        "wlanmdsp_transfer_complete": transfer_complete,
        "mcfg_wrq_success": mcfg_wrq_success,
        "post_up_hold_ok": post_up_long,
        "persist_lchown_failures": lchown_failures,
        "worker_cal_rc": post.get("worker_cal_rc", ""),
    }


def logdw_rows(details: dict[str, Any]) -> list[list[object]]:
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    records = logdw.get("records") if isinstance(logdw.get("records"), list) else []
    return [
        [
            f"{intish(record.get('index')):03d}",
            record.get("server_check", 0),
            record.get("mcfg", 0),
            record.get("wlanmdsp", 0),
            record.get("fallback_wlanmdsp", 0),
            record.get("end_transfer", 0),
            record.get("success", 0),
            record.get("total_bytes_4251884", 0),
            record.get("enoent", 0),
            record.get("payload", ""),
        ]
        for record in records
    ]


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    readwrite = details["readwrite_bridge"]
    persist = details["persist_rfs_bridge"]
    readback = details["mcfg_readback"]
    ipc = details["icnss_ipc"]
    post = details["post_cal_indication"]
    summary = logdw_summary(details)
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']} cnss={cascade.get('cnss_daemon_running')}"],
        ["readonly_probe_absent", bridge.get("probe_exists") == 0, f"path={bridge.get('probe_path')} open_rc={bridge.get('probe_open_rc')} errno={bridge.get('probe_open_errno')}"],
        ["readonly_fallback_present", classification.get("rfs_bridge_ok"), f"path={bridge.get('fallback_path')} exists={bridge.get('fallback_exists')} size={bridge.get('fallback_size')} open_rc={bridge.get('fallback_open_rc')}"],
        ["readwrite", classification.get("readwrite_bridge_ok"), f"server_check={readwrite.get('server_check_exists')} tmpfs={readwrite.get('readwrite_tmpfs_requested')} path={readwrite.get('readwrite_path')}"],
        ["persist", classification.get("persist_rfs_ok"), f"rfs={persist.get('rfs_path')} hlos={persist.get('hlos_path')} lchown_failures={classification.get('persist_lchown_failures')}"],
        ["post_up_window", classification.get("post_up_hold_ok"), f"up_ts={cascade.get('wlan_pd_up_ts')} last_ts={cascade.get('last_dmesg_ts')} post_up_sec={cascade.get('post_up_hold_sec')}"],
        ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69_dmesg={cascade.get('wlfw69')} cap={cascade.get('cap_req')} bdf={cascade.get('bdf')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
        ["icnss_ipc", ipc.get("wlfw_server_arrive_seen"), f"service69_text={ipc.get('service69_text')} first={ipc.get('first_focus_line')}"],
        ["wlanmdsp_tftp", classification.get("wlanmdsp_seen"), f"fallback={summary.get('fallback_wlanmdsp')} wlanmdsp={summary.get('wlanmdsp')} complete={classification.get('wlanmdsp_transfer_complete')} total_bytes={summary.get('total_bytes')} 4251884={summary.get('total_bytes_4251884')} end={summary.get('end_transfer')} success={summary.get('success')}"],
        ["initial_tftp", classification.get("initial_tftp_seen"), f"server_check={summary.get('server_check')} mcfg={summary.get('mcfg')} datagrams={summary.get('datagrams')} enoent={summary.get('enoent')}"],
        ["mcfg_readback", classification.get("mcfg_observer_ok"), f"path={readback.get('path')} samples={readback.get('sample_count')} post_wrq={readback.get('post_wrq_sampled')} readable={classification.get('mcfg_readable')} wrq_success={classification.get('mcfg_wrq_success')}"],
        ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
        ["indication", "", f"cb_hits={post['ind_events']['wlfw_qmi_ind_cb_entry']['hit_count']} first_msg={post['first_ind_msg_id']} len={post['first_ind_payload_len']} handle_type={post['first_handle_type']} fw_status={post['first_handle_0x28_status']}"],
    ]
    return "\n".join([
        "# Native Init V2046 Fallback Persist RFS MCFG Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2046`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], matrix_rows),
        "",
        "## Logdw TFTP Records",
        "",
        markdown_table(
            ["idx", "server_check", "mcfg", "wlanmdsp", "fallback", "end", "success", "4251884", "enoent", "payload"],
            logdw_rows(details) or [["none", 0, 0, 0, 0, 0, 0, 0, 0, ""]],
        ),
        "",
        "## MCFG Readback",
        "",
        markdown_table(
            ["idx", "phase", "exists", "size", "open_rc", "read_len", "payload"],
            [
                [
                    sample["index"],
                    sample["phase"],
                    sample["exists"],
                    sample["size"],
                    sample["open_rc"],
                    sample["read_len"],
                    sample["payload"],
                ]
                for sample in readback["samples"]
            ] or [["none", "none", 0, 0, -1, -1, ""]],
        ),
        "",
        "## Branch",
        "",
        "- If fallback `wlanmdsp.mbn` transfer completes and FW-ready/wlan0 follows, the first gate is solved and downstream should be chased only to the Wi-Fi interface gate.",
        "- If fallback `wlanmdsp.mbn` transfer completes but FW-ready/wlan0 does not follow, the next blocker is post-load/post-cal firmware-ready publication.",
        "- If `mcfg.tmp` is readable but no fallback `wlanmdsp.mbn` request follows, the modem stops after mcfg semantics and before WLAN image request.",
        "- If wlan0 appears, stop before scan/connect/credentials until the dedicated Wi-Fi gate.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2045 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2035() -> None:
    prev2035.CYCLE = CYCLE
    prev2035.OUT_DIR = OUT_DIR
    prev2035.HANDOFF_DIR = HANDOFF_DIR
    prev2035.HANDOFF_REPORT = HANDOFF_REPORT
    prev2035.REPORT_PATH = REPORT_PATH
    prev2035.V2034_OUT = V2045_OUT
    prev2035.V2034_INIT = V2045_INIT
    prev2035.V2034_BOOT = V2045_BOOT
    prev2035.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2035.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2035.TEST_LOG_PATH = TEST_LOG_PATH
    prev2035.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2035.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2035.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2035.artifact_hook_check = artifact_hook_check
    prev2035.collect_details = collect_details
    prev2035.classify = classify
    prev2035.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2035()
    return prev2035.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
