#!/usr/bin/env python3
"""V2044 rollbackable handoff for full downstream consumer chain with RFS bridges."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_mcfg_readback_handoff_v2039 as prev2039


CYCLE = "V2044"
OUT_DIR = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2044-full-downstream-chain-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2038-handoff"
HANDOFF_REPORT = OUT_DIR / "v2038-handoff-report.md"
REPORT_PATH = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2044_FULL_DOWNSTREAM_CHAIN_HANDOFF_2026-06-04.md"
)

ORIGINAL_CLASSIFY = prev2039.classify


def intish(value: object) -> int:
    return prev2039.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2039.prev2037.prev1998.prev1992.prev.markdown_table(
        headers,
        [[str(cell) for cell in row] for row in rows],
    )


def logdw_summary(details: dict[str, Any]) -> dict[str, Any]:
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    summary = logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}
    return summary


def wlanmdsp_transfer_complete(summary: dict[str, Any]) -> bool:
    return bool(
        intish(summary.get("wlanmdsp")) > 0
        and (
            intish(summary.get("end_transfer")) > 0
            or intish(summary.get("success")) > 0
            or intish(summary.get("total_bytes_4251884")) > 0
        )
    )


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    summary = logdw_summary(details)

    route_ok = bool(base.get("route_ok"))
    wlan_pd_up = intish(cascade.get("wlan_pd_up")) > 0
    cnss_running = bool(cascade.get("cnss_daemon_running"))
    post_up_long = bool(cascade.get("post_up_hold_ge_30"))
    wlanmdsp_seen = intish(summary.get("wlanmdsp")) > 0
    transfer_complete = wlanmdsp_transfer_complete(summary)
    readback = details.get("mcfg_readback") if isinstance(details.get("mcfg_readback"), dict) else {}
    samples = readback.get("samples") if isinstance(readback.get("samples"), list) else []
    mcfg_readable = any(
        intish(sample.get("exists")) > 0
        and intish(sample.get("size")) > 0
        and intish(sample.get("read_len")) > 0
        for sample in samples
        if isinstance(sample, dict)
    )
    initial_tftp_seen = (
        intish(summary.get("server_check")) > 0
        or intish(summary.get("mcfg")) > 0
        or intish(summary.get("datagrams")) > 0
    )

    if not route_ok:
        label = "full-downstream-chain-route-regression"
        reason = "the bridge plus downstream consumer route did not preserve rollback, cnss-daemon, RFS bridges, or light logdw prerequisites"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "full-downstream-chain-wlan0-progress"
        reason = "readonly/readwrite RFS bridges plus stock cnss-daemon reached wlan0; stop before scan/connect until the dedicated Wi-Fi gate"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "full-downstream-chain-fw-ready-progress"
        reason = "readonly/readwrite RFS bridges plus stock cnss-daemon reached firmware-ready progress"
        passed = True
    elif intish(cascade.get("bdf")) > 0:
        label = "full-downstream-chain-bdf-progress"
        reason = "WLFW downstream progressed to BDF/regdb, but firmware-ready/wlan0 did not follow"
        passed = True
    elif intish(cascade.get("wlfw69")) > 0:
        label = "full-downstream-chain-wlfw69-progress"
        reason = "WLFW service 69 appeared after WLAN-PD UP; downstream path is alive and should be chased to BDF/FW-ready/wlan0"
        passed = True
    elif not wlan_pd_up:
        label = "full-downstream-chain-wlan-pd-up-regression"
        reason = "the bridge route did not reproduce WLAN-PD UP"
        passed = False
    elif not cnss_running:
        label = "full-downstream-chain-cnss-daemon-not-running"
        reason = "WLAN-PD reached UP, but stock cnss-daemon was not confirmed in the same window"
        passed = False
    elif not post_up_long:
        label = "full-downstream-chain-window-insufficient"
        reason = "WLAN-PD reached UP with cnss-daemon, but the capture did not prove at least 30s after UP"
        passed = False
    elif transfer_complete:
        label = "full-downstream-chain-wlanmdsp-transfer-complete-no-wlfw69"
        reason = "the modem requested and completed wlanmdsp transfer, but WLFW69/BDF/FW-ready/wlan0 did not follow"
        passed = True
    elif wlanmdsp_seen:
        label = "full-downstream-chain-wlanmdsp-request-no-complete-no-wlfw69"
        reason = "the modem requested wlanmdsp, but no transfer-complete marker or WLFW69 cascade followed"
        passed = True
    elif mcfg_readable:
        label = "full-downstream-chain-mcfg-readable-no-wlanmdsp-no-wlfw69"
        reason = "WLAN-PD reached UP with stock cnss-daemon and long hold; mcfg.tmp became readable from the native TFTP transaction, but no wlanmdsp request or WLFW69 cascade followed"
        passed = True
    elif initial_tftp_seen:
        label = "full-downstream-chain-initial-tftp-no-wlanmdsp-no-wlfw69"
        reason = "WLAN-PD reached UP with stock cnss-daemon and long hold; tftp_server saw initial native traffic, but no wlanmdsp request or WLFW69 cascade followed"
        passed = True
    else:
        label = "full-downstream-chain-wlan-pd-up-zero-tftp-no-wlfw69"
        reason = "WLAN-PD reached UP with stock cnss-daemon and long hold, but no TFTP request or WLFW69 cascade was observed"
        passed = True

    return {
        **base,
        "label": label,
        "decision": f"v2044-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "wlan_pd_up_ok": wlan_pd_up,
        "cnss_daemon_ok": cnss_running,
        "post_up_hold_ok": post_up_long,
        "wlanmdsp_seen": wlanmdsp_seen,
        "wlanmdsp_transfer_complete": transfer_complete,
        "mcfg_readable": mcfg_readable,
        "initial_tftp_seen": initial_tftp_seen,
    }


def logdw_rows(details: dict[str, Any]) -> list[list[object]]:
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    records = logdw.get("records") if isinstance(logdw.get("records"), list) else []
    rows: list[list[object]] = []
    for record in records:
        rows.append([
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
        ])
    return rows


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    readwrite = details["readwrite_bridge"]
    post = details["post_cal_indication"]
    summary = logdw_summary(details)
    readback = details["mcfg_readback"]
    record_rows = logdw_rows(details)
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']} cnss={classification.get('cnss_daemon_ok')} lower={classification.get('lower_route_observed')}"],
        ["readonly_bridge", classification.get("rfs_bridge_ok"), f"path={bridge.get('probe_path')} open_rc={bridge.get('probe_open_rc')} fallback_size={bridge.get('fallback_size')} sda29_write={bridge.get('sda29_write')}"],
        ["readwrite_bridge", classification.get("readwrite_bridge_ok"), f"server_check={readwrite.get('server_check_exists')} tmpfs={readwrite.get('readwrite_tmpfs_requested')} path={readwrite.get('readwrite_path')}"],
        ["consumer_chain", classification.get("cnss_daemon_ok"), f"order={cascade.get('start_order')} child_started={cascade.get('child_started')}"],
        ["post_up_window", classification.get("post_up_hold_ok"), f"up_ts={cascade.get('wlan_pd_up_ts')} last_ts={cascade.get('last_dmesg_ts')} post_up_sec={cascade.get('post_up_hold_sec')}"],
        ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} cap={cascade.get('cap_req')} bdf={cascade.get('bdf')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
        ["wlanmdsp_tftp", classification.get("wlanmdsp_seen"), f"wlanmdsp={summary.get('wlanmdsp')} transfer_complete={classification.get('wlanmdsp_transfer_complete')} total_bytes={summary.get('total_bytes')} 4251884={summary.get('total_bytes_4251884')} end={summary.get('end_transfer')} success={summary.get('success')}"],
        ["initial_tftp", classification.get("initial_tftp_seen"), f"server_check={summary.get('server_check')} mcfg={summary.get('mcfg')} datagrams={summary.get('datagrams')} enoent={summary.get('enoent')}"],
        ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
        ["mcfg_readback", classification.get("mcfg_readback_ok"), f"path={readback.get('path')} samples={readback.get('sample_count')} post_wrq={readback.get('post_wrq_sampled')} readable={classification.get('mcfg_readable')}"],
    ]
    return "\n".join([
        "# Native Init V2044 Full Downstream Chain Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2044`",
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
            record_rows or [["none", 0, 0, 0, 0, 0, 0, 0, 0, ""]],
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
        "- If WLFW69 follows WLAN-PD UP, downstream is alive; chase BDF/FW-ready/wlan0 next.",
        "- If wlanmdsp transfer completes but WLFW69 stays absent, inspect WLAN PD load/integrity and modem-side publication.",
        "- If `mcfg.tmp` becomes readable but no wlanmdsp request follows, the next blocker is after the native mcfg ACK/read branch and before the WLAN image request stage.",
        "- If WLAN-PD UP holds with cnss-daemon but no wlanmdsp request appears, the blocker is before the WLAN image request stage.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2038 test-boot flash-handoff, namespace-local readonly/readwrite RFS bridges, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2039() -> None:
    prev2039.CYCLE = CYCLE
    prev2039.OUT_DIR = OUT_DIR
    prev2039.HANDOFF_DIR = HANDOFF_DIR
    prev2039.HANDOFF_REPORT = HANDOFF_REPORT
    prev2039.REPORT_PATH = REPORT_PATH
    prev2039.classify = classify
    prev2039.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2039()
    return prev2039.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
