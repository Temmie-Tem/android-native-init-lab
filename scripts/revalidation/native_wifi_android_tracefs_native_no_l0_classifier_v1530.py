#!/usr/bin/env python3
"""V1530 host-only classifier for Android tracefs evidence vs native no-L0."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1530-android-tracefs-native-no-l0-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1530_ANDROID_TRACEFS_NATIVE_NO_L0_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1530-android-tracefs-native-no-l0-classifier.txt")

V1529_MANIFEST = Path("tmp/wifi/v1529-android-tracefs-rc1-event-handoff/manifest.json")
V1529_EVIDENCE = Path(
    "tmp/wifi/v1529-android-tracefs-rc1-event-handoff/"
    "android-postfs-evidence/a90-v1529-tracefs-rc1-sampler"
)
V1496_MANIFEST = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/manifest.json")
V1517_MANIFEST = Path("tmp/wifi/v1517-wifi-critical-source-pre-l0-handoff/manifest.json")
V1523_MANIFEST = Path("tmp/wifi/v1523-msm-pcie-test11-vs-normal-path-classifier/manifest.json")
V1525_MANIFEST = Path("tmp/wifi/v1525-mhi-pm-resume-position-classifier/manifest.json")
V1528_MANIFEST = Path("tmp/wifi/v1528-v1527-tracefs-escalation-classifier/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_dmesg_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def first_trace_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
        if match:
            return float(match.group(1))
    return None


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.I)
    return sum(1 for line in text.splitlines() if regex.search(line))


def matching_lines(text: str, pattern: str, limit: int = 16) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000, 3)


def parse_v1529() -> dict[str, Any]:
    manifest = read_json(V1529_MANIFEST)
    analysis = (((manifest.get("context") or {}).get("analysis")) or {})
    trace = read_text(V1529_EVIDENCE / "tracefs-events.txt")
    dmesg = "\n".join(
        part
        for part in (
            read_text(V1529_EVIDENCE / "dmesg-filtered.txt"),
            read_text(V1529_EVIDENCE.parent / "host-dmesg-filtered.txt"),
        )
        if part
    )
    status_log = read_text(V1529_EVIDENCE / "tracefs-status.log")
    setup_log = read_text(V1529_EVIDENCE / "tracefs-setup.log")
    timeline = {
        "modem_get": first_dmesg_ts(dmesg, r"__subsystem_get:\s+modem count:0"),
        "modem_loading": first_dmesg_ts(dmesg, r"modem:\s+loading"),
        "modem_reset_release": first_dmesg_ts(dmesg, r"modem:\s+Brought out of reset"),
        "icnss_event_work": first_trace_ts(trace, r"workqueue_execute_start:.*function icnss_driver_event_work"),
        "macloader": first_dmesg_ts(dmesg, r"Assigning MAC from Macloader"),
        "pm_service_exec": first_trace_ts(trace, r"sched_process_exec: filename=/vendor/bin/pm-service"),
        "pm_service_modem_get": first_dmesg_ts(dmesg, r"__subsystem_get:\s+modem count:1"),
        "mdm_helper_start": first_dmesg_ts(dmesg, r"starting service 'vendor\.mdm_helper'"),
        "wlfw_start": first_dmesg_ts(dmesg, r"wlfw_start: Starting"),
        "wlfw_service_request": first_dmesg_ts(dmesg, r"wlfw_service_request"),
        "esoc0_get": first_dmesg_ts(dmesg, r"__subsystem_get:\s+esoc0 count:0"),
        "qmi_server_connected": first_dmesg_ts(dmesg, r"QMI Server Connected"),
        "bdf_regdb": first_dmesg_ts(dmesg, r"BDF file\s*:\s*regdb\.bin"),
        "bdf_bdwlan": first_dmesg_ts(dmesg, r"BDF file\s*:\s*bdwlan\.bin"),
        "fw_ready": first_dmesg_ts(dmesg, r"FW ready|WLAN FW is ready"),
        "wlan0": first_dmesg_ts(dmesg, r"\bwlan0\b"),
    }
    trace_counts = {
        "total": len([line for line in trace.splitlines() if line.strip()]),
        "pil_notif": count_lines(trace, r"\bpil_notif:"),
        "pil_esoc_or_sdx": count_lines(trace, r"\bpil_notif:.*fw=(?:esoc0|SDX|sdx)"),
        "pil_modem": count_lines(trace, r"\bpil_notif:.*fw=modem"),
        "workqueue": count_lines(trace, r"workqueue_execute_(?:start|end)"),
        "icnss_driver_event_work": count_lines(trace, r"function icnss_driver_event_work"),
        "sched_exec": count_lines(trace, r"sched_process_exec"),
        "pm_service_exec": count_lines(trace, r"sched_process_exec: filename=/vendor/bin/pm-service"),
        "console": count_lines(trace, r"\bconsole:"),
        "rc1_or_ltssm_text": count_lines(dmesg, r"RC1|LTSSM|PCIe RC1"),
    }
    return {
        "manifest_path": rel(V1529_MANIFEST),
        "evidence_dir": rel(V1529_EVIDENCE),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason"),
        "android_lower_ok": bool(analysis.get("android_lower_ok")),
        "files_present": analysis.get("files_present") or {},
        "sample_count": analysis.get("sample_count"),
        "sample_first_uptime": analysis.get("sample_first_uptime"),
        "sample_last_uptime": analysis.get("sample_last_uptime"),
        "trace_counts": trace_counts,
        "timeline": timeline,
        "deltas_ms": {
            "modem_get_to_icnss_event_work": delta_ms(timeline["icnss_event_work"], timeline["modem_get"]),
            "pm_service_exec_to_modem_get_count1": delta_ms(timeline["pm_service_modem_get"], timeline["pm_service_exec"]),
            "pm_service_exec_to_esoc0_get": delta_ms(timeline["esoc0_get"], timeline["pm_service_exec"]),
            "wlfw_start_to_esoc0_get": delta_ms(timeline["esoc0_get"], timeline["wlfw_start"]),
            "esoc0_get_to_qmi_server": delta_ms(timeline["qmi_server_connected"], timeline["esoc0_get"]),
            "qmi_server_to_bdf_regdb": delta_ms(timeline["bdf_regdb"], timeline["qmi_server_connected"]),
            "bdf_regdb_to_fw_ready": delta_ms(timeline["fw_ready"], timeline["bdf_regdb"]),
            "fw_ready_to_wlan0": delta_ms(timeline["wlan0"], timeline["fw_ready"]),
        },
        "classification": {
            "tracefs_usable": trace_counts["pil_notif"] > 0 and trace_counts["workqueue"] > 0,
            "irq_noise_removed": count_lines(setup_log, r"irq/irq_handler") == 0,
            "no_esoc_pil_notif": trace_counts["pil_esoc_or_sdx"] == 0,
            "icnss_event_work_seen": trace_counts["icnss_driver_event_work"] > 0,
            "pm_service_exec_seen": trace_counts["pm_service_exec"] > 0,
            "wlfw_before_esoc0": timeline["wlfw_start"] is not None
            and timeline["esoc0_get"] is not None
            and timeline["wlfw_start"] < timeline["esoc0_get"],
            "rc1_text_still_absent": trace_counts["rc1_or_ltssm_text"] == 0,
            "partial_but_rollback_pass": manifest.get("decision") == "v1529-tracefs-event-partial-rollback-pass",
        },
        "excerpts": {
            "pil_notif": matching_lines(trace, r"\bpil_notif:", 12),
            "icnss_event_work": matching_lines(trace, r"icnss_driver_event_work", 8),
            "pm_service": matching_lines(trace, r"pm-service|Binder:.*subsys.*(?:modem|esoc0)", 12),
            "dmesg_lower": matching_lines(
                dmesg,
                r"__subsystem_get|wlfw_start|QMI Server Connected|BDF file|WLAN FW is ready|\bwlan0\b",
                16,
            ),
        },
    }


def native_progress(manifest_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    progress = manifest.get("wifi_progress") or {}
    return {
        "path": rel(manifest_path),
        "cycle": manifest.get("cycle"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "final_decision": progress.get("final_decision"),
        "provider_trigger": progress.get("provider_trigger"),
        "rc1_progress": progress.get("rc1_progress"),
        "rc1_l0": progress.get("rc1_l0"),
        "rc1_link_failed": progress.get("rc1_link_failed"),
        "mhi_progress": progress.get("mhi_progress"),
        "wlfw_progress": progress.get("wlfw_progress"),
        "bdf_progress": progress.get("bdf_progress"),
        "fw_ready_progress": progress.get("fw_ready_progress"),
        "wlan0_present": progress.get("wlan0_present"),
        "rollback_ok": (manifest.get("rollback") or {}).get("ok"),
    }


def prior_classifier(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    return {
        "path": rel(path),
        "cycle": manifest.get("cycle"),
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason"),
        "classification": manifest.get("classification") or {},
        "next_gate": manifest.get("next_gate") or {},
    }


def build_analysis() -> dict[str, Any]:
    v1529 = parse_v1529()
    native = {
        "v1496": native_progress(V1496_MANIFEST),
        "v1517": native_progress(V1517_MANIFEST),
    }
    prior = {
        "v1523": prior_classifier(V1523_MANIFEST),
        "v1525": prior_classifier(V1525_MANIFEST),
        "v1528": prior_classifier(V1528_MANIFEST),
    }
    checks = {
        "android_good_lower_path_reached": bool(v1529["android_lower_ok"]),
        "tracefs_has_usable_pil_workqueue_events": v1529["classification"]["tracefs_usable"],
        "tracefs_irq_noise_removed": v1529["classification"]["irq_noise_removed"],
        "android_no_esoc_pil_notif": v1529["classification"]["no_esoc_pil_notif"],
        "android_icnss_event_work_seen": v1529["classification"]["icnss_event_work_seen"],
        "android_pm_service_exec_seen": v1529["classification"]["pm_service_exec_seen"],
        "android_wlfw_before_esoc0": v1529["classification"]["wlfw_before_esoc0"],
        "android_rc1_text_still_absent": v1529["classification"]["rc1_text_still_absent"],
        "native_v1496_fixed_no_l0": native["v1496"]["final_decision"] == "rc1-ltssm-link-failed-no-l0",
        "native_v1517_fixed_no_l0": native["v1517"]["final_decision"] == "rc1-ltssm-link-failed-no-l0",
        "native_mhi_wlfw_wlan0_absent": not any(
            native[item].get(key)
            for item in ("v1496", "v1517")
            for key in ("mhi_progress", "wlfw_progress", "bdf_progress", "fw_ready_progress", "wlan0_present")
        ),
        "test11_not_missing_core_enable": prior["v1523"]["decision"]
        == "v1523-test11-shares-enable-normal-trigger-readiness-gap",
        "mhi_pm_resume_downstream": prior["v1525"]["decision"]
        == "v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger",
    }
    pass_ok = all(checks.values())
    decision = (
        "v1530-android-tracefs-confirms-opaque-initial-rc1-trigger"
        if pass_ok
        else "v1530-android-tracefs-native-no-l0-incomplete"
    )
    reason = (
        "V1529 captured Android-good PIL/workqueue/pm-service evidence and lower Wi-Fi progress, "
        "but still exposes no direct eSoC PIL or RC1/LTSSM caller; native V1496/V1517 remain fixed at no-L0"
        if pass_ok
        else "Required Android tracefs/native no-L0/source classifier inputs are incomplete"
    )
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
        "v1529": v1529,
        "native": native,
        "prior": prior,
        "classification": {
            "current_blocker": "Android-only initial RC1 trigger/readiness remains opaque before native L0",
            "not_blocker_now": [
                "Wi-Fi HAL",
                "scan/connect/credentials",
                "DHCP/routes/external ping",
                "firmware transfer",
                "MHI PM-resume",
                "WLFW/BDF after L0",
            ],
            "why": [
                "Android reaches WLFW/BDF/FW-ready/wlan0 in V1529.",
                "V1529 tracefs sees modem PIL notifications, pm-service exec, and icnss_driver_event_work.",
                "V1529 still lacks RC1/LTSSM text and eSoC/SDX50M PIL notifications.",
                "Native V1496/V1517 still reach RC1 PHY/LTSSM but fail before L0.",
                "V1523/V1525 already rule out missing TEST:11 AP-enable semantics and MHI PM-resume as first-L0 triggers.",
            ],
        },
        "next_gate": {
            "primary": "V1531 targeted Android/source classifier for icnss_driver_event_work and pm-service initial trigger",
            "rationale": (
                "Tracefs proves Android-good lower progress and identifies useful kernel-adjacent signals, "
                "but broad workqueue/console capture is still too generic. The next host/source gate should map "
                "icnss_driver_event_work, pm-service Binder subsystem_get, and pci-msm initial enumerate callsites "
                "before any new native mutation."
            ),
            "allowed": [
                "host/source analysis",
                "read-only Android reference capture if needed",
                "tracefs event design with bounded event list",
            ],
            "forbidden": [
                "Wi-Fi HAL start",
                "scan/connect/credentials",
                "DHCP/routes/external ping",
                "PMIC/GPIO/GDSC direct writes",
                "blind eSoC notify or BOOT_DONE spoof",
                "global PCI rescan",
                "platform bind/unbind",
            ],
        },
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    v1529 = analysis["v1529"]
    native = analysis["native"]
    prior = analysis["prior"]
    return "\n".join(
        [
            "# Native Init V1530 Android Tracefs vs Native No-L0 Classifier",
            "",
            f"- Generated: `{manifest['generated_at']}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Checks",
            "",
            markdown_table(
                ["check", "value"],
                [[key, value] for key, value in analysis["checks"].items()],
            ),
            "",
            "## Android V1529 Timeline",
            "",
            markdown_table(
                ["event", "timestamp_s"],
                [[key, value] for key, value in v1529["timeline"].items()],
            ),
            "",
            "## Android V1529 Deltas",
            "",
            markdown_table(
                ["delta", "ms"],
                [[key, value] for key, value in v1529["deltas_ms"].items()],
            ),
            "",
            "## Tracefs Summary",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["decision", v1529["decision"]],
                    ["sample_count", v1529["sample_count"]],
                    ["sample_window", f"{v1529['sample_first_uptime']}..{v1529['sample_last_uptime']}"],
                    ["files", json.dumps(v1529["files_present"], sort_keys=True)],
                    ["trace_counts", json.dumps(v1529["trace_counts"], sort_keys=True)],
                    ["classification", json.dumps(v1529["classification"], sort_keys=True)],
                ],
            ),
            "",
            "## Native No-L0 References",
            "",
            markdown_table(
                [
                    "cycle",
                    "decision",
                    "final_decision",
                    "provider",
                    "rc1",
                    "l0",
                    "link_failed",
                    "mhi/wlfw/bdf/fw/wlan0",
                ],
                [
                    [
                        item["cycle"],
                        item["decision"],
                        item["final_decision"],
                        item["provider_trigger"],
                        item["rc1_progress"],
                        item["rc1_l0"],
                        item["rc1_link_failed"],
                        f"{item['mhi_progress']}/{item['wlfw_progress']}/{item['bdf_progress']}/{item['fw_ready_progress']}/{item['wlan0_present']}",
                    ]
                    for item in (native["v1496"], native["v1517"])
                ],
            ),
            "",
            "## Prior Source Classifiers",
            "",
            markdown_table(
                ["cycle", "decision", "reason"],
                [[item["cycle"], item["decision"], item["reason"]] for item in prior.values()],
            ),
            "",
            "## Interpretation",
            "",
            "\n".join(f"- {line}" for line in analysis["classification"]["why"]),
            "",
            f"Current blocker: `{analysis['classification']['current_blocker']}`.",
            "",
            "Do not move firmware/MHI/WLFW/scan/connect forward until native RC1 reaches L0 and PCI enumeration exists.",
            "",
            "## Excerpts",
            "",
            "### PIL",
            "",
            "\n".join(f"- `{line}`" for line in v1529["excerpts"]["pil_notif"][:8]),
            "",
            "### ICNSS Workqueue",
            "",
            "\n".join(f"- `{line}`" for line in v1529["excerpts"]["icnss_event_work"][:6]),
            "",
            "### PM Service",
            "",
            "\n".join(f"- `{line}`" for line in v1529["excerpts"]["pm_service"][:8]),
            "",
            "## Next Gate",
            "",
            f"- Primary: {analysis['next_gate']['primary']}",
            f"- Rationale: {analysis['next_gate']['rationale']}",
            "- Allowed: " + ", ".join(f"`{item}`" for item in analysis["next_gate"]["allowed"]),
            "- Forbidden: " + ", ".join(f"`{item}`" for item in analysis["next_gate"]["forbidden"]),
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = build_analysis()
    manifest = {
        "cycle": "V1530",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v1529_manifest": rel(V1529_MANIFEST),
            "v1529_evidence": rel(V1529_EVIDENCE),
            "v1496_manifest": rel(V1496_MANIFEST),
            "v1517_manifest": rel(V1517_MANIFEST),
            "v1523_manifest": rel(V1523_MANIFEST),
            "v1525_manifest": rel(V1525_MANIFEST),
            "v1528_manifest": rel(V1528_MANIFEST),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), report)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
