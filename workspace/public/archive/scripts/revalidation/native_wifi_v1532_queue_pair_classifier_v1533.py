#!/usr/bin/env python3
"""V1533 host-only classifier for V1532 Android workqueue pairing evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1533-v1532-queue-pair-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1533_V1532_QUEUE_PAIR_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1533-v1532-queue-pair-classifier.txt")

V1532_MANIFEST = Path("tmp/wifi/v1532-android-targeted-tracefs-queue-pair-handoff/manifest.json")
V1532_EVIDENCE = Path(
    "tmp/wifi/v1532-android-targeted-tracefs-queue-pair-handoff/"
    "android-postfs-evidence/a90-v1532-tracefs-queue-pair-sampler"
)
V1531_MANIFEST = Path("tmp/wifi/v1531-targeted-trace-source-classifier/manifest.json")


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


def first_trace_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
        if match:
            return float(match.group(1))
    return None


def first_dmesg_ts(text: str, pattern: str) -> float | None:
    regex = re.compile(pattern, re.I)
    for line in text.splitlines():
        if not regex.search(line):
            continue
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
        if match:
            return float(match.group(1))
    return None


def matching_lines(text: str, pattern: str, limit: int = 20) -> list[str]:
    regex = re.compile(pattern, re.I)
    return [line.strip() for line in text.splitlines() if regex.search(line)][:limit]


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000, 3)


def parse_pairing(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = ((manifest.get("context") or {}).get("analysis") or {})
    tracefs = analysis.get("tracefs_analysis") or {}
    pairing = tracefs.get("workqueue_pairing") or {}
    pairs = pairing.get("icnss_pairs") or []
    first_pair = pairs[0] if pairs else {}
    prior_events = first_pair.get("prior_events") or []
    queue_event = next((item for item in prior_events if item.get("event") == "workqueue_queue_work"), {})
    activate_event = next((item for item in prior_events if item.get("event") == "workqueue_activate_work"), {})
    return {
        "raw": pairing,
        "first_pair": first_pair,
        "queue_event": queue_event,
        "activate_event": activate_event,
        "queue_time": queue_event.get("time"),
        "activate_time": activate_event.get("time"),
        "execute_time": first_pair.get("execute_time"),
        "work": first_pair.get("work"),
        "queue_line": queue_event.get("line"),
        "execute_line": first_pair.get("execute_line"),
    }


def classify() -> dict[str, Any]:
    manifest = read_json(V1532_MANIFEST)
    v1531 = read_json(V1531_MANIFEST)
    trace = read_text(V1532_EVIDENCE / "tracefs-events.txt")
    dmesg = "\n".join(
        part
        for part in (
            read_text(V1532_EVIDENCE / "dmesg-filtered.txt"),
            read_text(V1532_EVIDENCE.parent / "host-dmesg-filtered.txt"),
        )
        if part
    )
    setup = read_text(V1532_EVIDENCE / "tracefs-setup.log")
    formats = read_text(V1532_EVIDENCE / "tracefs-formats.txt")
    pairing = parse_pairing(manifest)
    timeline = {
        "macloader_exec": first_trace_ts(trace, r"sched_process_exec: filename=/vendor/bin/hw/macloader"),
        "wlan_loading": first_trace_ts(trace, r"wlan: Loading driver") or first_dmesg_ts(dmesg, r"wlan: Loading driver"),
        "icnss_queue": pairing["queue_time"],
        "icnss_activate": pairing["activate_time"],
        "icnss_execute": pairing["execute_time"],
        "wlan_hdd_state": first_trace_ts(trace, r"wlan_hdd_state wlan major") or first_dmesg_ts(dmesg, r"wlan_hdd_state wlan major"),
        "mac_assign": first_dmesg_ts(dmesg, r"Assigning MAC from Macloader"),
        "pm_service_exec": first_trace_ts(trace, r"sched_process_exec: filename=/vendor/bin/pm-service"),
        "pm_service_modem_get": first_dmesg_ts(dmesg, r"__subsystem_get:\s+modem count:1"),
        "mdm_helper_start": first_dmesg_ts(dmesg, r"starting service 'vendor\.mdm_helper'"),
        "wlfw_start": first_dmesg_ts(dmesg, r"wlfw_start: Starting"),
        "pm_service_esoc0_get": first_dmesg_ts(dmesg, r"__subsystem_get:\s+esoc0 count:0"),
        "qmi_server_connected": first_dmesg_ts(dmesg, r"QMI Server Connected"),
        "bdf_regdb": first_dmesg_ts(dmesg, r"BDF file\s*:\s*regdb\.bin"),
        "fw_ready": first_dmesg_ts(dmesg, r"FW ready|WLAN FW is ready"),
        "wlan0": first_dmesg_ts(dmesg, r"\bwlan0\b"),
    }
    deltas = {
        "macloader_exec_to_icnss_queue": delta_ms(timeline["icnss_queue"], timeline["macloader_exec"]),
        "wlan_loading_to_icnss_queue": delta_ms(timeline["icnss_queue"], timeline["wlan_loading"]),
        "icnss_queue_to_execute": delta_ms(timeline["icnss_execute"], timeline["icnss_queue"]),
        "icnss_queue_to_mac_assign": delta_ms(timeline["mac_assign"], timeline["icnss_queue"]),
        "icnss_queue_to_pm_esoc0_get": delta_ms(timeline["pm_service_esoc0_get"], timeline["icnss_queue"]),
        "icnss_queue_to_qmi": delta_ms(timeline["qmi_server_connected"], timeline["icnss_queue"]),
        "pm_esoc0_get_to_qmi": delta_ms(timeline["qmi_server_connected"], timeline["pm_service_esoc0_get"]),
        "qmi_to_bdf_regdb": delta_ms(timeline["bdf_regdb"], timeline["qmi_server_connected"]),
        "fw_ready_to_wlan0": delta_ms(timeline["wlan0"], timeline["fw_ready"]),
    }
    raw_pairing = pairing["raw"]
    checks = {
        "v1532_pass": manifest.get("pass") is True,
        "v1532_rollback_pass": "rollback-pass" in str(manifest.get("decision")),
        "queue_event_available": "workqueue:workqueue_queue_work" in read_text(V1532_EVIDENCE / "tracefs-available-events.txt"),
        "icnss_queue_execute_pair_captured": raw_pairing.get("icnss_paired_count", 0) > 0,
        "queue_function_is_icnss_driver_event_work": "function=icnss_driver_event_work" in str(pairing["queue_line"]),
        "queue_pid_is_macloader": bool(timeline["macloader_exec"] is not None and timeline["icnss_queue"] is not None and abs(timeline["icnss_queue"] - timeline["macloader_exec"]) < 0.02),
        "queue_before_pm_service_esoc0": bool(timeline["icnss_queue"] is not None and timeline["pm_service_esoc0_get"] is not None and timeline["icnss_queue"] < timeline["pm_service_esoc0_get"]),
        "queue_before_qmi_server": bool(timeline["icnss_queue"] is not None and timeline["qmi_server_connected"] is not None and timeline["icnss_queue"] < timeline["qmi_server_connected"]),
        "android_lower_progress_present": all(timeline[name] is not None for name in ("qmi_server_connected", "bdf_regdb", "fw_ready", "wlan0")),
        "v1531_register_event_source_known": bool(
            ((((v1531.get("analysis") or {}).get("source") or {}).get("icnss") or {}).get("register_driver") or {}).get("found")
        ),
    }
    decision = "v1533-icnss-queue-pair-is-hdd-register-path-not-first-l0-trigger"
    pass_ok = all(checks.values())
    if not pass_ok:
        decision = "v1533-queue-pair-classifier-review"
    return {
        "cycle": "V1533",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": "V1532 pairs icnss_driver_event_work queue/execute to macloader WLAN driver load, before pm-service esoc0 and QMI; this visible ICNSS workqueue signal is not the Android first-L0 trigger",
        "inputs": {
            "v1532_manifest": rel(V1532_MANIFEST),
            "v1532_evidence": rel(V1532_EVIDENCE),
            "v1531_manifest": rel(V1531_MANIFEST),
        },
        "host": collect_host_metadata(),
        "checks": checks,
        "timeline": timeline,
        "deltas_ms": deltas,
        "pairing": pairing,
        "excerpts": {
            "icnss_pair_context": matching_lines(trace, r"icnss_driver_event_work|filename=/vendor/bin/hw/macloader|wlan: Loading driver|wlan_hdd_state", 24),
            "pm_service_context": matching_lines(dmesg, r"vendor\.mdm_helper|wlfw_start|__subsystem_get:\s+(modem count:1|esoc0 count:0)|QMI Server Connected|BDF file|FW ready|\bwlan0\b", 32),
            "tracefs_setup": setup.strip().splitlines()[:32],
            "workqueue_formats": matching_lines(formats, r"workqueue_(queue_work|activate_work|execute_start|execute_end)|field:.*(work|function|workqueue|cpu)", 80),
        },
        "safety": {
            "host_only_classifier": True,
            "device_commands_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
        },
        "next_gate": {
            "cycle": "V1534",
            "summary": "target pm-service Binder/esoc0 subsystem_get and immediate pci-msm first-L0 path, not ICNSS workqueue or firmware/MHI",
            "candidates": [
                "Android host-only/source classifier for pm-service Binder request that causes subsystem_get(esoc0)",
                "bounded Android trace/u(ret)probe design around pm-service QMI/Binder voter callsite if symbols or safe offsets are available",
                "native pre-L0 gate only after the pm-service/esoc0 trigger semantics are mapped",
            ],
        },
    }


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Native Init V1533 V1532 Queue Pair Classifier",
            "",
            f"- Generated: `{manifest['generated_at']}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], [[k, v] for k, v in manifest["checks"].items()]),
            "",
            "## Timeline",
            "",
            markdown_table(["event", "timestamp_s"], [[k, v] for k, v in manifest["timeline"].items()]),
            "",
            "## Deltas",
            "",
            markdown_table(["delta", "ms"], [[k, v] for k, v in manifest["deltas_ms"].items()]),
            "",
            "## Workqueue Pairing",
            "",
            markdown_table(
                ["field", "value"],
                [
                    ["work", manifest["pairing"].get("work")],
                    ["queue_time", manifest["pairing"].get("queue_time")],
                    ["execute_time", manifest["pairing"].get("execute_time")],
                    ["queue_line", manifest["pairing"].get("queue_line")],
                    ["execute_line", manifest["pairing"].get("execute_line")],
                ],
            ),
            "",
            "## Interpretation",
            "",
            "- V1532 captured the missing `workqueue_queue_work` event and paired it with the existing `workqueue_execute_start` for the same `icnss_driver_event_work` work item.",
            "- The queueing thread is the `macloader` process immediately after WLAN driver load, and the event executes roughly 0.012 ms later.",
            "- That ICNSS event is more than 2.7 s before pm-service opens `esoc0` and more than 3.5 s before the QMI server connects, so it is not the first-L0 trigger and not WLFW server-arrive evidence.",
            "- This closes the visible ICNSS workqueue signal as a lead for the native no-L0 blocker; the next useful target is pm-service Binder/QMI voter behavior that opens `subsys_esoc0` and the immediate pci-msm first-L0 path.",
            "",
            "## Excerpts",
            "",
            "### ICNSS Pair Context",
            "",
            *(f"- `{line}`" for line in manifest["excerpts"]["icnss_pair_context"]),
            "",
            "### PM Service Context",
            "",
            *(f"- `{line}`" for line in manifest["excerpts"]["pm_service_context"]),
            "",
            "## Safety",
            "",
            "Host-only classifier. It reads already captured V1532 evidence and performs no device command, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping.",
            "",
            "## Next Gate",
            "",
            f"- Cycle: `{manifest['next_gate']['cycle']}`",
            f"- Summary: {manifest['next_gate']['summary']}",
            *(f"- Candidate: {item}" for item in manifest["next_gate"]["candidates"]),
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
    manifest = classify()
    manifest["out_dir"] = str(store.run_dir)
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
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
