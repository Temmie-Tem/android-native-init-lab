#!/usr/bin/env python3
"""V2041 rollbackable handoff for persist-RFS mirror + full downstream chain."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_mcfg_readback_handoff_v2039 as prev2039


CYCLE = "V2041"
OUT_DIR = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2041-persist-rfs-mirror-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2040-handoff"
HANDOFF_REPORT = OUT_DIR / "v2040-handoff-report.md"
REPORT_PATH = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2041_PERSIST_RFS_MIRROR_HANDOFF_2026-06-04.md"
)
V2040_OUT = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2040-persist-rfs-mirror-test-boot"
)
V2040_INIT = V2040_OUT / "init_v2040_persist_rfs_mirror"
V2040_BOOT = V2040_OUT / "boot_linux_v2040_persist_rfs_mirror.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2040/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.201 (v2040-persist-rfs-mirror)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2040.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2040.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2040-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v386"

ORIGINAL_PREV2039_PATCH = prev2039.patch_prev_module
ORIGINAL_PREV2039_COLLECT = prev2039.collect_details
ORIGINAL_PREV2039_CLASSIFY = prev2039.classify
ORIGINAL_PREV2039_RENDER = prev2039.render_report


def rel(path: Path) -> str:
    return prev2039.rel(path)


def intish(value: object) -> int:
    return prev2039.intish(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2040",
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
        "tftp_mcfg_readback.begin=1",
        "tftp_mcfg_readback.summary.post_wrq_sampled=%d",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2040_INIT, init_required), (V2040_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2040_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


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


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_PREV2039_COLLECT(handoff)
    fields = prev2039.prev2037.prev1998.parse_fields(prev2039.prev2037.prev1998.read_helper_text())
    details["persist_rfs_bridge"] = collect_persist_rfs(fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_PREV2039_CLASSIFY(handoff, hook, steps, details)
    persist = details.get("persist_rfs_bridge") if isinstance(details.get("persist_rfs_bridge"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    logdw_summary = logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}
    readback = details.get("mcfg_readback") if isinstance(details.get("mcfg_readback"), dict) else {}
    records = logdw.get("records") if isinstance(logdw.get("records"), list) else []
    lchown_failures = sum(1 for record in records if "lchown fail" in str(record.get("payload", "")))
    route_ok = bool(base.get("route_ok")) and persist_ok(persist)
    transfer_complete = bool(base.get("transfer_complete"))
    wlanmdsp_seen = intish(logdw_summary.get("wlanmdsp")) > 0 or intish(logdw_summary.get("total_bytes_4251884")) > 0
    mcfg_seen = intish(logdw_summary.get("mcfg")) > 0 or intish(readback.get("sample_count")) > 0

    if not route_ok:
        label = "persist-rfs-mirror-route-regression"
        reason = "V2040 did not preserve rollback, full chain, dual-RFS/readwrite bridge, passive logdw, mcfg readback, or persist-RFS tmpfs mirrors"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "persist-rfs-mirror-wlan0-progress"
        reason = "persist-RFS mirror route reached wlan0; stop before credentials/scan/connect until the dedicated Wi-Fi gate"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "persist-rfs-mirror-fw-ready-progress"
        reason = "persist-RFS mirror route crossed into FW-ready progress"
        passed = True
    elif transfer_complete or wlanmdsp_seen:
        label = "persist-rfs-mirror-wlanmdsp-progress-no-fw-ready"
        reason = "persist-RFS mirror route produced wlanmdsp TFTP evidence but FW-ready/wlan0 did not follow"
        passed = True
    elif mcfg_seen and lchown_failures == 0:
        label = "persist-rfs-mirror-mcfg-no-lchown-still-no-wlanmdsp"
        reason = "persist-RFS mirrors removed native-only persist setup ENOENT, but the modem still stopped at mcfg.tmp before wlanmdsp"
        passed = True
    elif mcfg_seen:
        label = "persist-rfs-mirror-mcfg-still-no-wlanmdsp"
        reason = "persist-RFS mirrors were present, but native still stopped at mcfg.tmp before wlanmdsp"
        passed = True
    else:
        label = "persist-rfs-mirror-no-tokenized-tftp"
        reason = "persist-RFS mirrors and full chain were present, but no tokenized TFTP edge reached the passive logdw observer"
        passed = True

    return {
        **base,
        "label": label,
        "decision": f"v2041-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "persist_rfs_ok": persist_ok(persist),
        "persist_lchown_failures": lchown_failures,
        "persist_mcfg_seen": mcfg_seen,
        "persist_wlanmdsp_seen": wlanmdsp_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    persist = manifest["details"].get("persist_rfs_bridge", {})
    classification = manifest["classification"]
    persist_section = "\n".join([
        "## Persist RFS Mirror",
        "",
        prev2039.prev2037.prev1998.prev1992.prev.markdown_table(
            ["field", "value"],
            [
                ["ok", classification.get("persist_rfs_ok")],
                ["lchown_failures", classification.get("persist_lchown_failures")],
                ["rfs", f"{persist.get('rfs_path')} exists={persist.get('rfs_exists')} mode={persist.get('rfs_mode')} uid={persist.get('rfs_uid')} gid={persist.get('rfs_gid')}"],
                ["hlos_rfs", f"{persist.get('hlos_path')} exists={persist.get('hlos_exists')} mode={persist.get('hlos_mode')} uid={persist.get('hlos_uid')} gid={persist.get('hlos_gid')}"],
                ["rfs_readwrite", f"{persist.get('rfs_readwrite_path')} exists={persist.get('rfs_readwrite_exists')} is_dir={persist.get('rfs_readwrite_is_dir')}"],
                ["hlos_readwrite", f"{persist.get('hlos_readwrite_path')} exists={persist.get('hlos_readwrite_exists')} is_dir={persist.get('hlos_readwrite_is_dir')}"],
                ["safety", "rootfs_namespace_only=1 sda29_write=0"],
            ],
        ),
        "",
        "",
    ])
    report = ORIGINAL_PREV2039_RENDER(manifest)
    report = report.replace("V2039", "V2041")
    report = report.replace("v2039", "v2041")
    report = report.replace("V2038", "V2040")
    report = report.replace("v2038", "v2040")
    report = report.replace("Dual RFS MCFG Readback Handoff", "Persist RFS Mirror Handoff")
    report = report.replace("dual-rfs-mcfg-readback-handoff", "persist-rfs-mirror-handoff")
    report = report.replace("\n## MCFG Readback\n", f"\n{persist_section}## MCFG Readback\n")
    report = report.replace("\n## Indication Events\n", "\n\n## Indication Events\n", 1)
    report = report.replace(
        "- V2041 keeps the dual-RFS bypass route and replaces heavy TFTP ptrace with a private logdw datagram sink.",
        "- V2041 keeps the dual-RFS/readwrite bridge, adds namespace-only persist-RFS mirrors, and uses only the private logdw datagram sink.",
    )
    report = report.replace(
        "- V2041 closes the dual-RFS image-path bypass as the immediate fix: both WLAN image paths resolve/open, but the modem still stops after the first `readwrite/mcfg.tmp` RRQ/WRQ and never requests `wlanmdsp.mbn`.",
        "- V2041 tests whether native-only `/mnt/vendor/persist/{rfs,hlos_rfs}` setup failures are the AP-infra gap before `wlanmdsp.mbn`.",
    )
    report = report.replace(
        "- Next bounded unit depends on this result: if `mcfg.tmp` persists with payload, characterize the modem-side transition after the mcfg write ACK; if it is missing or empty, fix tmpfs write/visibility semantics.",
        "- Next bounded unit depends on this result: if persist mirrors remove setup failures but no `wlanmdsp.mbn` follows, pivot to the remaining `mcfg.tmp` semantics; if `wlanmdsp.mbn` appears, chase FW-ready/`wlan0` only.",
    )
    report = report.replace(
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2040 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2040 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
    )
    return report


def patch_prev_module() -> None:
    prev2039.CYCLE = CYCLE
    prev2039.OUT_DIR = OUT_DIR
    prev2039.HANDOFF_DIR = HANDOFF_DIR
    prev2039.HANDOFF_REPORT = HANDOFF_REPORT
    prev2039.REPORT_PATH = REPORT_PATH
    prev2039.V2038_OUT = V2040_OUT
    prev2039.V2038_INIT = V2040_INIT
    prev2039.V2038_BOOT = V2040_BOOT
    prev2039.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2039.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2039.TEST_LOG_PATH = TEST_LOG_PATH
    prev2039.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2039.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2039.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2039.artifact_hook_check = artifact_hook_check
    prev2039.collect_details = collect_details
    prev2039.classify = classify
    prev2039.render_report = render_report
    ORIGINAL_PREV2039_PATCH()


def main(argv: list[str] | None = None) -> int:
    prev2039.patch_prev_module = patch_prev_module
    return prev2039.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
