#!/usr/bin/env python3
"""V2096 rollbackable handoff for TFTP tombstone-RFS parity."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_icnss_qcacld_post_bdf_handoff_v2083 as prev2083


CYCLE = "V2096"
REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2096-tftp-tombstone-rfs-parity-handoff"
HANDOFF_DIR = OUT_DIR / "v2095-handoff"
HANDOFF_REPORT = OUT_DIR / "v2095-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2096_TFTP_TOMBSTONE_RFS_PARITY_HANDOFF_2026-06-05.md"
)
V2095_OUT = REPO_ROOT / "tmp" / "wifi" / "v2095-tftp-tombstone-rfs-parity-test-boot"
V2095_INIT = V2095_OUT / "init_v2095_tftp_tombstone_rfs_parity"
V2095_BOOT = V2095_OUT / "boot_linux_v2095_tftp_tombstone_rfs_parity.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2095/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.225 (v2095-tftp-tombstone-rfs-parity)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2095.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2095.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2095-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v409"

BASE_COLLECT_DETAILS = prev2083.collect_details
BASE_CLASSIFY = prev2083.classify


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    return prev2083.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2083.markdown_table(headers, rows)


def count_lines(text: str, needle: str, path_fragment: str) -> int:
    return sum(1 for line in text.splitlines() if needle in line and path_fragment in line)


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
        "A90v2095",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled=%d",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.rootfs_namespace_only=1",
        "wifi_companion_start.tftp_tombstone_rfs_tmpfs.ota_ruleset_created=0",
        "%s.begin=1",
        "/data/vendor/tombstones/rfs/modem",
        "/data/vendor/tombstones/rfs/lpass",
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_logdw_sink.order_timestamps=1",
        "per_mgr_vote_focused.begin=1",
        "wlfw_late_msg21_focused.begin=1",
        "icnss_qcacld_post_bdf_focused",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2095_INIT, init_required), (V2095_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2095_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def get_path_snapshot(fields: dict[str, str], name: str) -> dict[str, Any]:
    prefix = f"wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.{name}"
    return {
        "absolute": fields.get(f"{prefix}.absolute", ""),
        "exists": intish(fields.get(f"{prefix}.exists")),
        "is_dir": intish(fields.get(f"{prefix}.is_dir")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "uid": intish(fields.get(f"{prefix}.uid")),
        "gid": intish(fields.get(f"{prefix}.gid")),
        "statfs_ok": intish(fields.get(f"{prefix}.statfs_ok")),
        "fs_type": fields.get(f"{prefix}.fs_type", ""),
        "errno": intish(fields.get(f"{prefix}.errno")),
    }


def first_sample(fields: dict[str, str], item: str, predicate: Any) -> dict[str, Any]:
    for index in range(96):
        prefix = f"tftp_readwrite_transition.sample_{index:03d}"
        if f"{prefix}.{item}.exists" not in fields:
            continue
        if not predicate(prefix):
            continue
        return {
            "index": index,
            "phase": fields.get(f"{prefix}.phase", ""),
            "monotonic_ms": intish(fields.get(f"{prefix}.monotonic_ms")),
            "delta_ms": intish(fields.get(f"{prefix}.delta_ms")),
            "exists": intish(fields.get(f"{prefix}.{item}.exists")),
            "size": intish(fields.get(f"{prefix}.{item}.size")),
            "payload": fields.get(f"{prefix}.{item}.payload", ""),
        }
    return {"index": -1, "phase": "", "monotonic_ms": 0, "delta_ms": 0, "exists": 0, "size": 0, "payload": ""}


def collect_tombstone(fields: dict[str, str], text: str) -> dict[str, Any]:
    paths = {name: get_path_snapshot(fields, name) for name in ("tombstones", "rfs", "modem", "lpass")}
    tombstone_auto_dir = count_lines(text, "Failed to auto_dir", "/data/vendor/tombstones")
    tombstone_mkdir = count_lines(text, "mkdir failed", "/data/vendor/tombstones")
    persist_auto_dir = count_lines(text, "Failed to auto_dir", "/mnt/vendor/persist/rfs")
    persist_mkdir = count_lines(text, "mkdir failed", "/mnt/vendor/persist/rfs")
    safe = (
        intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.enabled")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.rootfs_namespace_only")) == 1
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.sda29_write")) == 0
        and intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.ota_ruleset_created")) == 0
        and all(path["exists"] == 1 and path["is_dir"] == 1 for path in paths.values())
    )
    return {
        "enabled": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.enabled")),
        "pre_enabled": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.enabled")),
        "rootfs_namespace_only": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.rootfs_namespace_only")),
        "sda29_write": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.sda29_write")),
        "ota_ruleset_created": intish(fields.get("wifi_companion_start.tftp_tombstone_rfs_tmpfs.pre.ota_ruleset_created")),
        "paths": paths,
        "safe": safe,
        "auto_dir_error_count": tombstone_auto_dir,
        "mkdir_failed_count": tombstone_mkdir,
        "total_auto_dir_error_count": text.count("Failed to auto_dir"),
        "total_mkdir_failed_count": text.count("mkdir failed"),
        "persist_auto_dir_error_count": persist_auto_dir,
        "persist_mkdir_failed_count": persist_mkdir,
        "tombstone_token_count": text.count("/data/vendor/tombstones"),
    }


def collect_tftp_branch(fields: dict[str, str], details: dict[str, Any]) -> dict[str, Any]:
    summary = prev2083.logdw_summary(details)
    server_check = first_sample(fields, "server_check", lambda prefix: fields.get(f"{prefix}.server_check.payload") == "hello")
    ota = first_sample(fields, "ota_ruleset", lambda prefix: fields.get(f"{prefix}.ota_ruleset.exists") == "1")
    mcfg = first_sample(fields, "mcfg", lambda prefix: fields.get(f"{prefix}.mcfg.exists") == "1")
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    wlan_pd_up_ts = None
    try:
        wlan_pd_up_ts = float(str(cascade.get("wlan_pd_up_ts")))
    except (TypeError, ValueError):
        pass
    server_s = server_check["monotonic_ms"] / 1000.0 if server_check["monotonic_ms"] else None
    server_after_wlan_pd_ms = (
        int(round((server_s - wlan_pd_up_ts) * 1000.0))
        if server_s is not None and wlan_pd_up_ts is not None
        else None
    )
    return {
        "server_check": server_check,
        "ota": ota,
        "mcfg": mcfg,
        "server_after_wlan_pd_ms": server_after_wlan_pd_ms,
        "logdw_server_check": intish(summary.get("server_check")),
        "logdw_ota_firewall": intish(summary.get("ota_firewall")),
        "logdw_mcfg": intish(summary.get("mcfg")),
        "logdw_wlanmdsp": intish(summary.get("wlanmdsp")) + intish(summary.get("fallback_wlanmdsp")) + intish(summary.get("firmware_mnt_wlanmdsp")),
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = BASE_COLLECT_DETAILS(handoff)
    fields = prev2083.prev2081.prev2059.prev2057.parse_fields()
    text = prev2083.prev2081.prev2059.prev2057.helper_text()
    details["tftp_tombstone_rfs_tmpfs"] = collect_tombstone(fields, text)
    details["tftp_tombstone_branch"] = collect_tftp_branch(fields, details)
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = BASE_CLASSIFY(handoff, hook, steps, details)
    tombstone = details.get("tftp_tombstone_rfs_tmpfs") if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch") if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    tombstone_safe = bool(tombstone.get("safe"))
    auto_dir_cleared = intish(tombstone.get("auto_dir_error_count")) == 0 and intish(tombstone.get("mkdir_failed_count")) == 0
    wlanmdsp_seen = intish(branch.get("logdw_wlanmdsp")) > 0
    ota_seen = intish(branch.get("logdw_ota_firewall")) > 0 or intish(branch.get("ota", {}).get("index")) >= 0
    server_payload = str(branch.get("server_check", {}).get("payload", ""))
    post_up_server = branch.get("server_after_wlan_pd_ms")
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0

    if not hook_ok:
        label = "tombstone-parity-artifact-hook-regression"
        passed = False
        reason = "V2095 artifact does not contain the bounded tombstone-RFS parity contract"
    elif not tombstone_safe:
        label = "tombstone-parity-setup-regression"
        passed = False
        reason = "namespace-local tombstone-RFS directories were not proven present/safe"
    elif wlan0:
        label = "tombstone-parity-wlan0-progress"
        passed = True
        reason = "native reached wlan0; stop before scan/connect and run the dedicated connectivity gate"
    elif fw_ready:
        label = "tombstone-parity-fw-ready-progress"
        passed = True
        reason = "native reached FW_READY; chase wlan0 next"
    elif wlanmdsp_seen:
        label = "tombstone-parity-wlanmdsp-progress"
        passed = True
        reason = "removing tombstone auto-dir failure allowed a wlanmdsp tftp request"
    elif not auto_dir_cleared:
        label = "tombstone-parity-auto-dir-still-fails"
        passed = True
        reason = "tombstone bridge was present but tftp_server still logged tombstone auto-dir/mkdir failures"
    elif ota_seen:
        label = "tombstone-parity-early-branch-progress-no-wlanmdsp"
        passed = True
        reason = "tombstone parity cleared startup errors and reached ota_firewall, but not wlanmdsp"
    elif server_payload == "hello" and isinstance(post_up_server, int) and post_up_server > 0:
        label = "tombstone-parity-no-effect-post-up-server-check"
        passed = True
        reason = "tombstone parity cleared startup errors, but native still only shows post-UP server_check and no ota/wlanmdsp"
    else:
        label = "tombstone-parity-no-early-tftp-branch"
        passed = True
        reason = "tombstone parity cleared startup errors, but no Android-order early TFTP branch appeared"

    return {
        **base,
        "decision": f"v2096-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "tombstone_safe": tombstone_safe,
        "auto_dir_cleared": auto_dir_cleared,
        "wlanmdsp_seen": wlanmdsp_seen,
        "ota_seen": ota_seen,
        "server_check_payload": server_payload,
        "server_after_wlan_pd_ms": post_up_server,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    tombstone = details.get("tftp_tombstone_rfs_tmpfs", {}) if isinstance(details.get("tftp_tombstone_rfs_tmpfs"), dict) else {}
    branch = details.get("tftp_tombstone_branch", {}) if isinstance(details.get("tftp_tombstone_branch"), dict) else {}
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    summary = prev2083.logdw_summary(details)
    paths = tombstone.get("paths", {}) if isinstance(tombstone.get("paths"), dict) else {}
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2096 TFTP Tombstone-RFS Parity Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2096`",
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
                ["tombstone_bridge", classification.get("tombstone_safe"), f"auto_dir_cleared={classification.get('auto_dir_cleared')} tombstone_tokens={tombstone.get('tombstone_token_count')}"],
                ["tombstone_auto_dir", tombstone.get("auto_dir_error_count"), f"mkdir_failed={tombstone.get('mkdir_failed_count')} total_auto_dir={tombstone.get('total_auto_dir_error_count')}"],
                ["persist_auto_dir", tombstone.get("persist_auto_dir_error_count"), f"mkdir_failed={tombstone.get('persist_mkdir_failed_count')}"],
                ["server_check", classification.get("server_check_payload"), f"after_wlan_pd_ms={classification.get('server_after_wlan_pd_ms')} logdw={branch.get('logdw_server_check')}"],
                ["ota_firewall", classification.get("ota_seen"), f"logdw={branch.get('logdw_ota_firewall')} file={branch.get('ota', {}).get('index')}"],
                ["wlanmdsp", classification.get("wlanmdsp_seen"), f"logdw={branch.get('logdw_wlanmdsp')} summary={summary.get('wlanmdsp')}/{summary.get('fallback_wlanmdsp')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Tombstone Paths",
        "",
        markdown_table(
            ["path", "exists", "dir", "mode", "uid", "gid", "fs"],
            [
                [name, item.get("exists"), item.get("is_dir"), item.get("mode"), item.get("uid"), item.get("gid"), item.get("fs_type")]
                for name, item in paths.items()
                if isinstance(item, dict)
            ],
        ),
        "",
        "## Interpretation",
        "",
        "- This is the bounded AP-infra parity discriminator: private-root tombstone RFS dirs only, no `ota_firewall/ruleset` fabrication and no `tftp_server` ptrace.",
        "- If this run remains `no-effect-post-up-server-check`, the startup auto-dir errors are not the WLAN-PD firmware-fetch trigger.",
        "- Then the remaining primary gate is still the modem-internal state before Android's pre-spawn `server_check -> ota_firewall -> wlanmdsp` branch.",
        "- MAC/macloader remains closed as a quick falsifier; no further MAC cycles are justified unless a real kernel `icnss: Assigning MAC from Macloader` appears incidentally.",
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
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2095 test-boot flash-handoff, namespace-local RFS bridges/tmpfs mirrors including `/data/vendor/tombstones/rfs/{modem,lpass}`, private tmp-root `/dev/socket/logdw`, tracefs uprobes, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2081() -> None:
    prev2083.prev2081.CYCLE = CYCLE
    prev2083.prev2081.OUT_DIR = OUT_DIR
    prev2083.prev2081.HANDOFF_DIR = HANDOFF_DIR
    prev2083.prev2081.HANDOFF_REPORT = HANDOFF_REPORT
    prev2083.prev2081.REPORT_PATH = REPORT_PATH
    prev2083.prev2081.V2080_OUT = V2095_OUT
    prev2083.prev2081.V2080_INIT = V2095_INIT
    prev2083.prev2081.V2080_BOOT = V2095_BOOT
    prev2083.prev2081.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2083.prev2081.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2083.prev2081.TEST_LOG_PATH = TEST_LOG_PATH
    prev2083.prev2081.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2083.prev2081.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2083.prev2081.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2083.prev2081.artifact_hook_check = artifact_hook_check
    prev2083.prev2081.collect_details = collect_details
    prev2083.prev2081.classify = classify
    prev2083.prev2081.render_report = render_report
    prev2083.prev2081.configure_prev2059()


def main(argv: list[str] | None = None) -> int:
    configure_prev2081()
    return prev2083.prev2081.prev2059.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
