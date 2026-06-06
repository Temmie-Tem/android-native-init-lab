#!/usr/bin/env python3
"""V2043 rollbackable handoff for ota_firewall ruleset bridge + full downstream chain."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_dual_rfs_mcfg_readback_handoff_v2039 as prev2039


CYCLE = "V2043"
OUT_DIR = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2043-ota-firewall-ruleset-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2042-handoff"
HANDOFF_REPORT = OUT_DIR / "v2042-handoff-report.md"
REPORT_PATH = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2043_OTA_FIREWALL_RULESET_HANDOFF_2026-06-04.md"
)
V2042_OUT = prev2039.prev2037.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2042-ota-firewall-ruleset-test-boot"
)
V2042_INIT = V2042_OUT / "init_v2042_ota_firewall_ruleset"
V2042_BOOT = V2042_OUT / "boot_linux_v2042_ota_firewall_ruleset.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2042/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.202 (v2042-ota-firewall-ruleset)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2042.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2042.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2042-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v387"

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
        "A90v2042",
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
        "ota_firewall.absolute=/vendor/rfs/msm/mpss/readwrite/ota_firewall/ruleset",
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
        "tftp_logdw_sink.summary.ota_firewall=%u",
        "tftp_mcfg_readback.begin=1",
        "tftp_mcfg_readback.summary.post_wrq_sampled=%d",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2042_INIT, init_required), (V2042_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2042_INIT else boot_forbidden
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


def collect_ota_firewall(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_firmware_serve_gate.rfs_bridge.ota_firewall"
    return {
        "absolute": "/vendor/rfs/msm/mpss/readwrite/ota_firewall/ruleset",
        "path": fields.get(f"{prefix}.host_path", ""),
        "exists": intish(fields.get(f"{prefix}.exists")),
        "is_reg": intish(fields.get(f"{prefix}.is_reg")),
        "size": intish(fields.get(f"{prefix}.size")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "uid": fields.get(f"{prefix}.uid", ""),
        "gid": fields.get(f"{prefix}.gid", ""),
        "errno": intish(fields.get(f"{prefix}.stat_errno")),
        "error": fields.get(f"{prefix}.stat_error", ""),
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


def ota_ok(ota: dict[str, Any]) -> bool:
    return bool(
        ota.get("exists") == 1
        and ota.get("is_reg") == 1
        and ota.get("errno") == 0
    )


def patch_logdw_ota(logdw: dict[str, Any], fields: dict[str, str]) -> None:
    summary = logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}
    summary["ota_firewall"] = intish(fields.get("tftp_logdw_sink.summary.ota_firewall"))
    records = logdw.get("records") if isinstance(logdw.get("records"), list) else []
    for record in records:
        index = intish(record.get("index"))
        prefix = f"tftp_logdw_sink.record_{index:03d}"
        payload = str(record.get("payload", "")).lower()
        record["ota_firewall"] = max(
            intish(fields.get(f"{prefix}.token.ota_firewall")),
            1 if "ota_firewall" in payload or "ruleset" in payload else 0,
        )
        if record["ota_firewall"] and not summary["ota_firewall"]:
            summary["ota_firewall"] = 1


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_PREV2039_COLLECT(handoff)
    fields = prev2039.prev2037.prev1998.parse_fields(prev2039.prev2037.prev1998.read_helper_text())
    details["persist_rfs_bridge"] = collect_persist_rfs(fields)
    details["ota_firewall_bridge"] = collect_ota_firewall(fields)
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    if logdw:
        patch_logdw_ota(logdw, fields)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_PREV2039_CLASSIFY(handoff, hook, steps, details)
    persist = details.get("persist_rfs_bridge") if isinstance(details.get("persist_rfs_bridge"), dict) else {}
    ota = details.get("ota_firewall_bridge") if isinstance(details.get("ota_firewall_bridge"), dict) else {}
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
    ota_seen = intish(logdw_summary.get("ota_firewall")) > 0

    if not route_ok:
        label = "ota-firewall-ruleset-route-regression"
        reason = "V2042 did not preserve rollback, full chain, dual-RFS/readwrite bridge, passive logdw, mcfg readback, or persist-RFS mirrors"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "ota-firewall-ruleset-wlan0-progress"
        reason = "ota_firewall mirror route reached wlan0; stop before credentials/scan/connect until the dedicated Wi-Fi gate"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "ota-firewall-ruleset-fw-ready-progress"
        reason = "ota_firewall mirror route crossed into FW-ready progress"
        passed = True
    elif transfer_complete or wlanmdsp_seen:
        label = "ota-firewall-ruleset-wlanmdsp-progress-no-fw-ready"
        reason = "ota_firewall mirror route produced wlanmdsp TFTP evidence but FW-ready/wlan0 did not follow"
        passed = True
    elif ota_seen and mcfg_seen and lchown_failures == 0:
        label = "ota-firewall-ruleset-ota-then-mcfg-still-no-wlanmdsp"
        reason = "the modem requested ota_firewall/ruleset with the bridge present, then still stopped at mcfg.tmp before wlanmdsp"
        passed = True
    elif ota_seen:
        label = "ota-firewall-ruleset-ota-no-wlanmdsp"
        reason = "the modem requested ota_firewall/ruleset with the bridge present, but no wlanmdsp request followed"
        passed = True
    elif not ota_ok(ota) and mcfg_seen:
        label = "ota-firewall-ruleset-not-preserved-mcfg-still-no-wlanmdsp"
        reason = "the pre-start ota_firewall/ruleset file was absent by the post-run snapshot, and native still stopped at mcfg.tmp before wlanmdsp"
        passed = True
    elif not ota_ok(ota):
        label = "ota-firewall-ruleset-not-preserved-no-tokenized-ota"
        reason = "the pre-start ota_firewall/ruleset file was absent by the post-run snapshot, and no ota_firewall request was observed"
        passed = True
    elif mcfg_seen and lchown_failures == 0:
        label = "ota-firewall-ruleset-mcfg-no-ota-still-no-wlanmdsp"
        reason = "the ota_firewall ruleset file was present, but the modem still skipped visible ota_firewall traffic and stopped at mcfg.tmp before wlanmdsp"
        passed = True
    elif mcfg_seen:
        label = "ota-firewall-ruleset-mcfg-still-no-wlanmdsp"
        reason = "the ota_firewall ruleset bridge was present, but native still stopped at mcfg.tmp before wlanmdsp"
        passed = True
    else:
        label = "ota-firewall-ruleset-no-tokenized-tftp"
        reason = "ota_firewall ruleset bridge and full chain were present, but no tokenized TFTP edge reached the passive logdw observer"
        passed = True

    return {
        **base,
        "label": label,
        "decision": f"v2043-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "persist_rfs_ok": persist_ok(persist),
        "ota_firewall_ok": ota_ok(ota),
        "ota_firewall_seen": ota_seen,
        "persist_lchown_failures": lchown_failures,
        "persist_mcfg_seen": mcfg_seen,
        "persist_wlanmdsp_seen": wlanmdsp_seen,
    }


def render_report(manifest: dict[str, Any]) -> str:
    persist = manifest["details"].get("persist_rfs_bridge", {})
    ota = manifest["details"].get("ota_firewall_bridge", {})
    classification = manifest["classification"]
    persist_section = "\n".join([
        "## OTA Firewall Ruleset",
        "",
        prev2039.prev2037.prev1998.prev1992.prev.markdown_table(
            ["field", "value"],
            [
                ["ok", classification.get("ota_firewall_ok")],
                ["requested", classification.get("ota_firewall_seen")],
                ["ruleset", f"{ota.get('path')} exists={ota.get('exists')} is_reg={ota.get('is_reg')} size={ota.get('size')} mode={ota.get('mode')} uid={ota.get('uid')} gid={ota.get('gid')}"],
                ["ruleset_errno", f"{ota.get('errno')} {ota.get('error')}"],
                ["persist_mirrors_ok", classification.get("persist_rfs_ok")],
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
    report = report.replace("V2039", "V2043")
    report = report.replace("v2039", "v2043")
    report = report.replace("V2038", "V2042")
    report = report.replace("v2038", "v2042")
    report = report.replace("Dual RFS MCFG Readback Handoff", "OTA Firewall Ruleset Handoff")
    report = report.replace("dual-rfs-mcfg-readback-handoff", "ota-firewall-ruleset-handoff")
    report = report.replace("\n## MCFG Readback\n", f"\n{persist_section}## MCFG Readback\n")
    report = report.replace("\n## Indication Events\n", "\n\n## Indication Events\n", 1)
    report = report.replace(
        "- V2043 keeps the dual-RFS bypass route and replaces heavy TFTP ptrace with a private logdw datagram sink.",
        "- V2043 keeps the dual-RFS/readwrite bridge, adds namespace-only ota_firewall ruleset bridge, and uses only the private logdw datagram sink.",
    )
    report = report.replace(
        "- V2043 closes the dual-RFS image-path bypass as the immediate fix: both WLAN image paths resolve/open, but the modem still stops after the first `readwrite/mcfg.tmp` RRQ/WRQ and never requests `wlanmdsp.mbn`.",
        "- V2043 tests whether adding Android's pre-`wlanmdsp.mbn` `readwrite/ota_firewall/ruleset` surface moves native past the early readwrite branch.",
    )
    report = report.replace(
        "- Next bounded unit depends on this result: if `mcfg.tmp` persists with payload, characterize the modem-side transition after the mcfg write ACK; if it is missing or empty, fix tmpfs write/visibility semantics.",
        "- Next bounded unit depends on this result: if `ota_firewall/ruleset` is requested but no `wlanmdsp.mbn` follows, the gate remains modem-internal after the Android-style readwrite branch; if it is not requested and `mcfg.tmp` remains first visible traffic, stay on `mcfg.tmp` visibility semantics.",
    )
    report = report.replace(
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2042 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2042 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, namespace-local ota_firewall tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
    )
    return report


def patch_prev_module() -> None:
    prev2039.CYCLE = CYCLE
    prev2039.OUT_DIR = OUT_DIR
    prev2039.HANDOFF_DIR = HANDOFF_DIR
    prev2039.HANDOFF_REPORT = HANDOFF_REPORT
    prev2039.REPORT_PATH = REPORT_PATH
    prev2039.V2038_OUT = V2042_OUT
    prev2039.V2038_INIT = V2042_INIT
    prev2039.V2038_BOOT = V2042_BOOT
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
