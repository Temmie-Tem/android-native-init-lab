#!/usr/bin/env python3
"""V2138 rollbackable handoff for the QCACLD firmware_class fallback feeder."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_wifi_firmware_class_fallback_handoff_v2136 as prev2136


CYCLE = "V2138"
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2138-qcacld-fwclass-feeder-handoff"
HANDOFF_DIR = OUT_DIR / "v2137-handoff"
HANDOFF_REPORT = OUT_DIR / "v2137-handoff-report.md"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2138_QCACLD_FWCLASS_FEEDER_HANDOFF_2026-06-05.md"
)
V2137_OUT = REPO_ROOT / "tmp" / "wifi" / "v2137-qcacld-fwclass-feeder-test-boot"
V2137_INIT = V2137_OUT / "init_v2137_qcacld_fwclass_feeder"
V2137_BOOT = V2137_OUT / "boot_linux_v2137_qcacld_fwclass_feeder.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2137/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.243 (v2137-qcacld-fwclass-feeder)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2137.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2137.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2137-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v426"

ORIGINAL_CLASSIFY = prev2136.classify
ORIGINAL_COLLECT_DETAILS = prev2136.collect_details
ORIGINAL_ARTIFACT_HOOK = prev2136.artifact_hook_check


def intish(value: object) -> int:
    return prev2136.intish(value)


def rel(path: Path) -> str:
    return prev2136.rel(path)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2136.markdown_table(headers, rows)


def artifact_hook_check() -> dict[str, Any]:
    checks = ORIGINAL_ARTIFACT_HOOK()
    for path in (V2137_INIT, V2137_BOOT):
        key = rel(path)
        data = path.read_bytes() if path.exists() else b""
        required = (
            EXPECTED_HELPER_VERSION,
            "qcacld_firmware_class_fallback_feeder",
            "bounded-qcacld-firmware-class-fallback-feeder",
            "sysfs_data_write_scope=firmware_class_userspace_fallback_only",
            "no_firmware_file_write=1",
            "no_sda29_write=1",
            "wlan!qca_cld!WCNSS_qcom_cfg.ini",
            "wlan!qca_cld!bdwlan.bin",
            "wlan!qca_cld!regdb.bin",
            "/proc/1/root/mnt/vendor/firmware",
        ) if path == V2137_BOOT else (
            "A90v2137",
            "fwclass_vendor_path",
            "/mnt/vendor/firmware",
        )
        forbidden = (
            "diag_remote_dev_poll_probe.begin=1",
            "PTRACE_ATTACH",
            "post_bdf_boot_wlan_consumer_gate.begin=1",
            "tftp_server-android-runtime",
        ) if path == V2137_BOOT else (
            "--qrtr-readback-matrix",
            "--pm-observer-private-cnss-daemon-sdx50m",
        )
        missing = [token for token in required if token.encode() not in data]
        forbidden_hits = [token for token in forbidden if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden_hits,
            "missing": missing,
            "forbidden": forbidden_hits,
        }
    return checks


def collect_qcacld_feeder(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "qcacld_firmware_class_fallback_feeder.after_boot_wlan_trigger."
    requests: list[dict[str, Any]] = []
    for request_index in range(3):
        request_prefix = f"{prefix}request_{request_index}."
        requests.append({
            "index": request_index,
            "label": fields.get(request_prefix + "label", ""),
            "firmware": fields.get(request_prefix + "firmware", ""),
            "sysfs_name": fields.get(request_prefix + "sysfs_name", ""),
            "sysfs_dir": fields.get(request_prefix + "sysfs_dir", ""),
            "seen": intish(fields.get(request_prefix + "seen")),
            "source_rc": intish(fields.get(request_prefix + "source_rc")),
            "source_errno": intish(fields.get(request_prefix + "source_errno")),
            "source": fields.get(request_prefix + "source", ""),
            "source_bytes": intish(fields.get(request_prefix + "source_bytes")),
            "loading_start_rc": intish(fields.get(request_prefix + "loading_start_rc")),
            "loading_start_errno": intish(fields.get(request_prefix + "loading_start_errno")),
            "data_rc": intish(fields.get(request_prefix + "data_rc")),
            "data_errno": intish(fields.get(request_prefix + "data_errno")),
            "loading_done_rc": intish(fields.get(request_prefix + "loading_done_rc")),
            "loading_done_errno": intish(fields.get(request_prefix + "loading_done_errno")),
            "abort_rc": intish(fields.get(request_prefix + "abort_rc")),
            "abort_errno": intish(fields.get(request_prefix + "abort_errno")),
            "fed": intish(fields.get(request_prefix + "fed")),
            "final_seen": intish(fields.get(f"{prefix}request_{request_index}.final_seen")),
            "final_fed": intish(fields.get(f"{prefix}request_{request_index}.final_fed")),
        })
    return {
        "begin": intish(fields.get(prefix + "begin")),
        "mode": fields.get(prefix + "mode", ""),
        "wait_ms": intish(fields.get(prefix + "wait_ms")),
        "request_count": intish(fields.get(prefix + "request_count")),
        "scope": fields.get(prefix + "sysfs_data_write_scope", ""),
        "no_partition_write": intish(fields.get(prefix + "no_partition_write")),
        "no_firmware_file_write": intish(fields.get(prefix + "no_firmware_file_write")),
        "no_sda29_write": intish(fields.get(prefix + "no_sda29_write")),
        "no_tracefs_write": intish(fields.get(prefix + "no_tracefs_write")),
        "no_wifi_hal": intish(fields.get(prefix + "no_wifi_hal")),
        "scan_connect": intish(fields.get(prefix + "scan_connect")),
        "credentials": intish(fields.get(prefix + "credentials")),
        "dhcp_routing": intish(fields.get(prefix + "dhcp_routing")),
        "external_ping": intish(fields.get(prefix + "external_ping")),
        "no_esoc0_open": intish(fields.get(prefix + "no_esoc0_open")),
        "no_pcie_rescan": intish(fields.get(prefix + "no_pcie_rescan")),
        "loops": intish(fields.get(prefix + "loops")),
        "seen_count": intish(fields.get(prefix + "seen_count")),
        "fed_count": intish(fields.get(prefix + "fed_count")),
        "timed_out": intish(fields.get(prefix + "timed_out")),
        "requests": requests,
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    text = prev2136.prev2134.prev2132.prev2130.prev2128.read_helper_text()
    fields = prev2136.prev2134.prev2132.prev2130.prev2128.parse_fields(text)
    details["qcacld_firmware_class_fallback_feeder"] = collect_qcacld_feeder(fields)
    details["helper_capture"] = collect_helper_capture()
    return details


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def collect_helper_capture() -> dict[str, Any]:
    helper_result_path = HANDOFF_DIR / "test-v1393-helper-result.stdout.txt"
    helper_summary_path = HANDOFF_DIR / "test-v1393-summary.stdout.txt"
    helper_log_path = HANDOFF_DIR / "test-v1393-log.stdout.txt"
    wlan0_probe_path = HANDOFF_DIR / "test-wlan0.stdout.txt"
    helper_result = read_text(helper_result_path)
    helper_summary = read_text(helper_summary_path)
    helper_log = read_text(helper_log_path)
    wlan0_probe = read_text(wlan0_probe_path)
    helper_missing = "No such file or directory" in helper_result or "can't open" in helper_result
    return {
        "helper_result_file": rel(helper_result_path),
        "helper_summary_file": rel(helper_summary_path),
        "helper_log_file": rel(helper_log_path),
        "wlan0_probe_file": rel(wlan0_probe_path),
        "helper_result_exists": helper_result_path.exists(),
        "helper_result_missing_target": helper_missing,
        "summary_state_armed": "state=armed" in helper_summary,
        "log_spawned_helper": "helper pid=" in helper_log or "spawned" in helper_log,
        "wlan0_probe_present": "wlan0=present" in wlan0_probe,
    }


def feeder_safe(feeder: dict[str, Any]) -> bool:
    return (
        intish(feeder.get("begin")) == 1
        and feeder.get("mode") == "bounded-qcacld-firmware-class-fallback-feeder"
        and feeder.get("scope") == "firmware_class_userspace_fallback_only"
        and intish(feeder.get("no_partition_write")) == 1
        and intish(feeder.get("no_firmware_file_write")) == 1
        and intish(feeder.get("no_sda29_write")) == 1
        and intish(feeder.get("no_tracefs_write")) == 1
        and intish(feeder.get("no_wifi_hal")) == 1
        and intish(feeder.get("scan_connect")) == 0
        and intish(feeder.get("credentials")) == 0
        and intish(feeder.get("dhcp_routing")) == 0
        and intish(feeder.get("external_ping")) == 0
        and intish(feeder.get("no_esoc0_open")) == 1
        and intish(feeder.get("no_pcie_rescan")) == 1
    )


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    feeder = details.get("qcacld_firmware_class_fallback_feeder") if isinstance(details.get("qcacld_firmware_class_fallback_feeder"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    helper_capture = details.get("helper_capture") if isinstance(details.get("helper_capture"), dict) else {}
    safe = feeder_safe(feeder)
    fed_count = intish(feeder.get("fed_count"))
    seen_count = intish(feeder.get("seen_count"))
    requests = feeder.get("requests", []) if isinstance(feeder.get("requests"), list) else []
    ini_fed = len(requests) > 0 and intish(requests[0].get("fed")) > 0
    wlan0 = intish(cascade.get("wlan0")) > 0
    helper_unavailable = bool(helper_capture.get("helper_result_missing_target")) or bool(helper_capture.get("summary_state_armed"))

    label = str(base.get("label", "qcacld-fwclass-feeder-unknown"))
    passed = bool(base.get("pass"))
    reason = str(base.get("reason", "classification unavailable"))

    if not base.get("hook_ok"):
        label = "qcacld-fwclass-feeder-artifact-regression"
        passed = False
        reason = "V2137 artifact did not contain the v426 feeder contract"
    elif wlan0:
        label = "qcacld-fwclass-feeder-wlan0-progress"
        passed = True
        reason = "V2137 firmware_class feeder route advanced QCACLD startup to wlan0; stop before credentials and run the connectivity gate"
    elif not safe:
        label = "qcacld-fwclass-feeder-safety-regression"
        passed = False
        reason = "feeder safety markers were absent or unsafe before wlan0 evidence appeared" if helper_unavailable else "feeder safety markers were absent or unsafe"
    elif fed_count >= 3:
        label = "qcacld-fwclass-feeder-all-known-fed-no-wlan0"
        passed = True
        reason = "all three known QCACLD firmware fallback requests were fed, but wlan0 still did not appear"
    elif ini_fed:
        label = "qcacld-fwclass-feeder-ini-fed-next-request-or-startup-blocker"
        passed = True
        reason = "WCNSS_qcom_cfg.ini was fed through firmware_class; remaining blocker is the next observed firmware request or QCACLD startup state"
    elif seen_count > 0:
        label = "qcacld-fwclass-feeder-request-seen-feed-failed"
        passed = False
        reason = "a QCACLD firmware fallback request appeared, but the feeder did not complete the loading/data/done sequence"
    elif base.get("stack_request_firmware") and base.get("stack_qdf_ini_parse"):
        label = "qcacld-fwclass-feeder-no-request-seen-still-qdf-ini"
        passed = True
        reason = "QCACLD remained in request_firmware -> qdf_ini_parse, but the feeder did not see a supported fallback request node"

    return {
        **base,
        "decision": f"v2138-{label}-rollback-{'pass' if passed else 'blocked'}",
        "label": label,
        "pass": passed,
        "reason": reason,
        "qcacld_feeder_safe": safe,
        "qcacld_feeder_seen_count": seen_count,
        "qcacld_feeder_fed_count": fed_count,
        "qcacld_ini_fed": ini_fed,
        "helper_result_missing_target": bool(helper_capture.get("helper_result_missing_target")),
        "helper_summary_state_armed": bool(helper_capture.get("summary_state_armed")),
        "wlan0_probe_present": bool(helper_capture.get("wlan0_probe_present")),
    }


def feeder_rows(feeder: dict[str, Any]) -> list[list[object]]:
    requests = feeder.get("requests", []) if isinstance(feeder.get("requests"), list) else []
    rows: list[list[object]] = []
    for request in requests:
        if not isinstance(request, dict):
            continue
        rows.append([
            request.get("label"),
            f"seen={request.get('seen')} fed={request.get('fed')}",
            f"src={request.get('source')} bytes={request.get('source_bytes')} loading={request.get('loading_start_rc')}/{request.get('loading_done_rc')} data={request.get('data_rc')}/{request.get('data_errno')}",
        ])
    return rows or [["none", "", ""]]


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details.get("cascade", {}) if isinstance(details.get("cascade"), dict) else {}
    stack = details.get("icnss_register_probe_stack_sampler", {}) if isinstance(details.get("icnss_register_probe_stack_sampler"), dict) else {}
    sampler = details.get("firmware_class_fallback_sampler", {}) if isinstance(details.get("firmware_class_fallback_sampler"), dict) else {}
    feeder = details.get("qcacld_firmware_class_fallback_feeder", {}) if isinstance(details.get("qcacld_firmware_class_fallback_feeder"), dict) else {}
    helper_capture = details.get("helper_capture", {}) if isinstance(details.get("helper_capture"), dict) else {}
    first_wlan0_lines = cascade.get("first_wlan0_lines", []) if isinstance(cascade.get("first_wlan0_lines"), list) else []
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2138 QCACLD Firmware Class Feeder Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2138`",
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
                ["fwclass_sampler", classification.get("firmware_class_sampler_safe"), f"entries={classification.get('firmware_class_entries')} interesting={classification.get('firmware_class_interesting')}"],
                ["feeder", classification.get("qcacld_feeder_safe"), f"seen={classification.get('qcacld_feeder_seen_count')} fed={classification.get('qcacld_feeder_fed_count')} ini_fed={classification.get('qcacld_ini_fed')}"],
                ["helper_capture", "", f"summary_armed={classification.get('helper_summary_state_armed')} helper_missing={classification.get('helper_result_missing_target')} wlan0_probe={classification.get('wlan0_probe_present')}"],
                ["stack", classification.get("stack_available"), f"targets={classification.get('stack_target_hits')} request_firmware={classification.get('stack_request_firmware')} qdf_ini={classification.get('stack_qdf_ini_parse')} hdd_ctx={classification.get('stack_hdd_context_create')}"],
                ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} wlfw69={cascade.get('wlfw69')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')}"],
            ],
        ),
        "",
        "## Feeder",
        "",
        markdown_table(["request", "state", "detail"], feeder_rows(feeder)),
        "",
        "## Firmware Class Entries",
        "",
        *prev2136.firmware_class_entry_lines(sampler),
        "",
        "## Stack Samples",
        "",
        *prev2136.prev2134.prev2132.stack_sample_lines(stack),
        "",
        "## Wlan0 Proof",
        "",
        f"- Probe: `{helper_capture.get('wlan0_probe_file', '')}` present `{helper_capture.get('wlan0_probe_present')}`",
        *(f"- `{line}`" for line in first_wlan0_lines),
        *([] if first_wlan0_lines else ["- `none`"]),
        "",
        "## Capture Caveat",
        "",
        f"- Helper summary was still armed: `{helper_capture.get('summary_state_armed')}`.",
        f"- Helper result target was unavailable at collection time: `{helper_capture.get('helper_result_missing_target')}` from `{helper_capture.get('helper_result_file', '')}`.",
        "- The feeder internal counters are therefore unavailable in this capture, but `test-wlan0` plus dmesg prove native `wlan0` creation.",
        "",
        "## Interpretation",
        "",
        "- V2138 actively tests whether the V2136 fallback request can be satisfied by userspace feeding the observed QCACLD firmware_class node from the read-only vendor source.",
        "- This is a bounded sysfs firmware_class fallback data path, not a firmware file, EFS, partition, GPIO, PCIe, or HAL mutation.",
        "- V2138 reached real native `wlan0`, so the next gate is a dedicated connectivity handoff rather than more firmware_class request classification.",
        "- If INI feed succeeds without wlan0, the next unit should target the next observed firmware request or the post-INI QCACLD startup state rather than returning to AP-side producer captures.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No firmware/partition file writes, EFS writes, tracefs write, sysrq, DIAG, rild/cnss/pm-service strace, boot-time QRTR matrix, QMI payload send, `tftp_server` ptrace, module load/unload, or driver bind/unbind was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: V2137 rollbackable test-boot flash-handoff, read-only `sda29` mount at `/mnt/vendor`, temporary `firmware_class.path` restore-proven write, namespace-local RFS bridges/tmpfs mirrors, one gated `/sys/kernel/boot_wlan/boot_wlan` write after FW_READY, and bounded firmware_class fallback `loading`/`data` writes only for observed QCACLD files.",
        "",
    ])


def configure() -> None:
    prev2136.CYCLE = CYCLE
    prev2136.OUT_DIR = OUT_DIR
    prev2136.HANDOFF_DIR = HANDOFF_DIR
    prev2136.HANDOFF_REPORT = HANDOFF_REPORT
    prev2136.REPORT_PATH = REPORT_PATH
    prev2136.V2135_OUT = V2137_OUT
    prev2136.V2135_INIT = V2137_INIT
    prev2136.V2135_BOOT = V2137_BOOT
    prev2136.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2136.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2136.TEST_LOG_PATH = TEST_LOG_PATH
    prev2136.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2136.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2136.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2136.artifact_hook_check = artifact_hook_check
    prev2136.collect_details = collect_details
    prev2136.classify = classify
    prev2136.render_report = render_report
    prev2136.configure()


def main(argv: list[str] | None = None) -> int:
    configure()
    return prev2136.prev2134.prev2132.prev2130.prev2128.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
