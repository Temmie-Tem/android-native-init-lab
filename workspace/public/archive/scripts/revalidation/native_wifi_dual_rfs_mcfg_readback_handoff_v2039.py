#!/usr/bin/env python3
"""V2039 rollbackable handoff for dual-RFS mcfg.tmp readback."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_logdw_transfer_handoff_v2037 as prev2037


CYCLE = "V2039"
OUT_DIR = prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2039-dual-rfs-mcfg-readback-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2038-handoff"
HANDOFF_REPORT = OUT_DIR / "v2038-handoff-report.md"
REPORT_PATH = prev2037.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2039_DUAL_RFS_MCFG_READBACK_HANDOFF_2026-06-04.md"
)
V2038_OUT = prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2038-dual-rfs-mcfg-readback-test-boot"
)
V2038_INIT = V2038_OUT / "init_v2038_dual_rfs_mcfg_readback"
V2038_BOOT = V2038_OUT / "boot_linux_v2038_dual_rfs_mcfg_readback.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2038/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.200 (v2038-dual-rfs-mcfg-readback)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2038.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2038.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2038-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v385"

ORIGINAL_PATCH_PREV_MODULE = prev2037.patch_prev_module
ORIGINAL_ARTIFACT_HOOK_CHECK = prev2037.artifact_hook_check
ORIGINAL_COLLECT_DETAILS = prev2037.collect_details
ORIGINAL_CLASSIFY = prev2037.classify
ORIGINAL_RENDER_REPORT = prev2037.render_report


def rel(path: Path) -> str:
    return prev2037.rel(path)


def intish(value: object) -> int:
    return prev2037.intish(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2038",
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
        "android_parity=firmware_mnt_probe_present_firmware_fallback_present",
        "probe.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        "fallback.absolute=/vendor/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
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
        "tftp_mcfg_readback.begin=1",
        "tftp_mcfg_readback.mode=read-only-post-wrq-stat-open-read",
        "tftp_mcfg_readback.sample_%03u.phase=%s",
        "tftp_mcfg_readback.summary.post_wrq_sampled=%d",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2038_INIT, init_required), (V2038_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2038_INIT else boot_forbidden
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
        sample = {
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
        }
        samples.append(sample)
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


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev2037.prev1998.parse_fields(prev2037.prev1998.read_helper_text())
    details["mcfg_readback"] = collect_mcfg_readback(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    readback = details.get("mcfg_readback") if isinstance(details.get("mcfg_readback"), dict) else {}
    post_wrq = readback.get("post_wrq") if isinstance(readback.get("post_wrq"), dict) else {}
    final = readback.get("final") if isinstance(readback.get("final"), dict) else {}
    best = post_wrq or final
    route_ok = bool(base.get("route_ok"))
    transfer_complete = bool(base.get("transfer_complete"))

    if not route_ok:
        label = "dual-rfs-mcfg-readback-route-regression"
        reason = "V2038 did not preserve rollback, dual-RFS, cnss-daemon, passive logdw, or mcfg readback prerequisites"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "dual-rfs-mcfg-readback-wlan0-progress"
        reason = "dual-RFS mcfg readback route reached wlan0; stop before credentials/scan/connect until a dedicated gate"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "dual-rfs-mcfg-readback-fw-ready-progress"
        reason = "dual-RFS mcfg readback route crossed into FW-ready progress"
        passed = True
    elif transfer_complete:
        label = "dual-rfs-mcfg-readback-wlanmdsp-transfer-progress"
        reason = "wlanmdsp transfer progressed under the mcfg readback route"
        passed = True
    elif not best:
        label = "dual-rfs-mcfg-readback-no-post-wrq-sample"
        reason = "mcfg readback observer ran, but no post-WRQ or final mcfg sample was captured"
        passed = True
    elif intish(best.get("exists")) and intish(best.get("size")) > 0 and intish(best.get("read_len")) > 0:
        label = "dual-rfs-mcfg-post-wrq-present-no-wlanmdsp"
        reason = "mcfg.tmp persists with readable payload after native WRQ, but the modem still never requests wlanmdsp"
        passed = True
    else:
        label = "dual-rfs-mcfg-post-wrq-missing-or-empty-no-wlanmdsp"
        reason = "mcfg.tmp is missing, empty, or unreadable after native WRQ, before any wlanmdsp request"
        passed = True

    return {
        **base,
        "label": label,
        "decision": f"v2039-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "mcfg_best_sample": best,
        "mcfg_readback_ok": bool(readback.get("begin")) and bool(readback.get("sample_count")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    readback = manifest["details"]["mcfg_readback"]
    sample_rows = [
        [
            str(sample["index"]),
            str(sample["phase"]),
            str(sample["exists"]),
            str(sample["size"]),
            str(sample["open_rc"]),
            str(sample["read_len"]),
            str(sample["payload"]),
        ]
        for sample in readback["samples"]
    ]
    section = "\n".join([
        "## MCFG Readback",
        "",
        prev2037.prev1998.prev1992.prev.markdown_table(
            ["idx", "phase", "exists", "size", "open_rc", "read_len", "payload"],
            sample_rows or [["none", "none", "0", "0", "-1", "-1", ""]],
        ),
        "",
        f"- Path: `{readback.get('path')}`",
        f"- Samples: `{readback.get('sample_count')}` post_wrq=`{readback.get('post_wrq_sampled')}`",
        "",
    ])
    report = ORIGINAL_RENDER_REPORT(manifest)
    report = report.replace("V2037", "V2039")
    report = report.replace("v2037", "v2039")
    report = report.replace("V2036", "V2038")
    report = report.replace("v2036", "v2038")
    report = report.replace("Dual RFS Logdw Transfer Handoff", "Dual RFS MCFG Readback Handoff")
    report = report.replace("dual-rfs-logdw-transfer-handoff", "dual-rfs-mcfg-readback-handoff")
    report = report.replace("dual-rfs-logdw", "dual-rfs-mcfg-readback")
    report = report.replace("\n## Indication Events\n", f"\n{section}## Indication Events\n")
    report = report.replace(
        "- Next bounded unit: instrument the `readwrite/mcfg.tmp` transaction itself with a light post-WRQ stat/readback inside the native namespace, then compare to Android's immediate RRQ/read/unlink/MCFG-read continuation.",
        "- Next bounded unit depends on this result: if `mcfg.tmp` persists with payload, characterize the modem-side transition after the mcfg write ACK; if it is missing or empty, fix tmpfs write/visibility semantics.",
    )
    return report


def patch_prev_module() -> None:
    prev2037.CYCLE = CYCLE
    prev2037.OUT_DIR = OUT_DIR
    prev2037.HANDOFF_DIR = HANDOFF_DIR
    prev2037.HANDOFF_REPORT = HANDOFF_REPORT
    prev2037.REPORT_PATH = REPORT_PATH
    prev2037.V2036_OUT = V2038_OUT
    prev2037.V2036_INIT = V2038_INIT
    prev2037.V2036_BOOT = V2038_BOOT
    prev2037.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2037.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2037.TEST_LOG_PATH = TEST_LOG_PATH
    prev2037.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2037.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2037.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2037.artifact_hook_check = artifact_hook_check
    prev2037.collect_details = collect_details
    prev2037.classify = classify
    prev2037.render_report = render_report
    ORIGINAL_PATCH_PREV_MODULE()


def main(argv: list[str] | None = None) -> int:
    prev2037.patch_prev_module = patch_prev_module
    return prev2037.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
