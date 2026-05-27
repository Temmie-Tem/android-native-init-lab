#!/usr/bin/env python3
"""V1140 host-only classifier for the post-PM mdm_helper lower gap.

This script consumes the V1139 live manifest only.  It does not contact the
device and does not run Wi-Fi HAL, scan/connect, DHCP, routes, credentials, or
external ping.  Its purpose is to close the stale V1071 `pm-service exit 255`
route and select the next lower eSoC/MHI/ks observation gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1140-post-pm-lower-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1140-post-pm-lower-gap-classifier.txt")
DEFAULT_V1139 = Path("tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2/manifest.json")
DEFAULT_V1139_REPORT = Path("docs/reports/NATIVE_INIT_V1139_POST_PM_MDM_HELPER_ESOC_LIVE_2026-05-27.md")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1139", type=Path, default=DEFAULT_V1139)
    parser.add_argument("--v1139-report", type=Path, default=DEFAULT_V1139_REPORT)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data
    for item in path:
        if not isinstance(current, dict):
            return default
        current = current.get(item)
    return default if current is None else current


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "online"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(text, 0)
    except ValueError:
        return 0


def summarize_v1139(data: dict[str, Any]) -> dict[str, Any]:
    global_fw = nested_get(data, ("analysis", "global_firmware"), {})
    trace = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    pm_contract = trace.get("pm_contract", {}) if isinstance(trace, dict) else {}
    post_pm = trace.get("post_pm_mdm_helper", {}) if isinstance(trace, dict) else {}
    queue = trace.get("mdm_helper_queue_timing", {}) if isinstance(trace, dict) else {}
    provider = trace.get("mdm_helper_provider_readiness", {}) if isinstance(trace, dict) else {}
    subsys_hold = trace.get("post_pm_subsys_hold", {}) if isinstance(trace, dict) else {}
    markers = nested_get(global_fw, ("markers", "counts"), {}) if isinstance(global_fw, dict) else {}
    qrtr_services = global_fw.get("qrtr_services_after_observer", {}) if isinstance(global_fw, dict) else {}
    reboot_cleanup = global_fw.get("reboot_cleanup", {}) if isinstance(global_fw, dict) else {}

    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "pm_actor_executed": boolish(data.get("pm_actor_executed")),
        "cnss_daemon_start_executed": boolish(data.get("cnss_daemon_start_executed")),
        "wifi_hal_start_executed": boolish(data.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(data.get("scan_connect_executed")),
        "credential_use_executed": boolish(data.get("credential_use_executed")),
        "dhcp_route_executed": boolish(data.get("dhcp_route_executed")),
        "external_ping_executed": boolish(data.get("external_ping_executed")),
        "wifi_bringup_executed": boolish(data.get("wifi_bringup_executed")),
        "partition_write_executed": boolish(data.get("partition_write_executed")),
        "flash_executed": boolish(data.get("flash_executed")),
        "mss_after_observer": global_fw.get("mss_after_observer", "") if isinstance(global_fw, dict) else "",
        "mdm3_after_observer": global_fw.get("mdm3_after_observer", "") if isinstance(global_fw, dict) else "",
        "qrtr_service69": intish(qrtr_services.get("69") if isinstance(qrtr_services, dict) else 0),
        "qrtr_service74": intish(qrtr_services.get("74") if isinstance(qrtr_services, dict) else 0),
        "qrtr_service180": intish(qrtr_services.get("180") if isinstance(qrtr_services, dict) else 0),
        "wlfw_count": intish(markers.get("wlfw") if isinstance(markers, dict) else 0),
        "bdf_count": intish(markers.get("bdf") if isinstance(markers, dict) else 0),
        "wlan0_count": intish(markers.get("wlan0") if isinstance(markers, dict) else 0),
        "mhi_count": intish(markers.get("mhi") if isinstance(markers, dict) else 0),
        "qca6390_count": intish(markers.get("qca6390") if isinstance(markers, dict) else 0),
        "pm_client_register_ret": nested_get(trace, ("return_values_by_comm", "cnss-daemon", "pm_client_register_ret"), []),
        "pm_client_connect_ret": nested_get(trace, ("return_values_by_comm", "cnss-daemon", "pm_client_connect_ret"), []),
        "pm_contract_result": pm_contract.get("result", "") if isinstance(pm_contract, dict) else "",
        "pm_contract_reason": pm_contract.get("reason", "") if isinstance(pm_contract, dict) else "",
        "per_mgr_exit_code": pm_contract.get("child.per_mgr.exit_code", "") if isinstance(pm_contract, dict) else "",
        "per_mgr_signal": pm_contract.get("child.per_mgr.signal", "") if isinstance(pm_contract, dict) else "",
        "per_mgr_subsys_modem_seen": intish(pm_contract.get("per_mgr_subsys_modem_seen") if isinstance(pm_contract, dict) else 0),
        "pm_proxy_helper_subsys_modem_seen": intish(
            pm_contract.get("pm_proxy_helper_subsys_modem_seen") if isinstance(pm_contract, dict) else 0
        ),
        "vndservice_provider_seen": intish(pm_contract.get("vndservice_provider_seen") if isinstance(pm_contract, dict) else 0),
        "post_pm_result": post_pm.get("result", "") if isinstance(post_pm, dict) else "",
        "post_pm_mdm_helper_observable": intish(post_pm.get("mdm_helper_observable") if isinstance(post_pm, dict) else 0),
        "post_pm_exec_attempted": intish(post_pm.get("exec_attempted") if isinstance(post_pm, dict) else 0),
        "post_pm_window_snapshot_captured": intish(
            post_pm.get("window_snapshot_captured") if isinstance(post_pm, dict) else 0
        ),
        "post_pm_mdm_helper_esoc0_count": intish(
            post_pm.get("fd_esoc0_count.window") if isinstance(post_pm, dict) else 0
        ),
        "post_pm_mdm_helper_subsys_esoc0_count": intish(
            post_pm.get("fd_subsys_esoc0_count.window") if isinstance(post_pm, dict) else 0
        ),
        "post_pm_mdm_helper_mhi_pipe_count": intish(
            post_pm.get("fd_mhi_pipe_count.window") if isinstance(post_pm, dict) else 0
        ),
        "post_pm_ks_count": intish(post_pm.get("ks_count.window") if isinstance(post_pm, dict) else 0),
        "queue_mdm_helper_esoc0_count": intish(
            queue.get("post_pm_window.mdm_helper_esoc0_count") if isinstance(queue, dict) else 0
        ),
        "queue_mdm_helper_subsys_esoc0_count": intish(
            queue.get("post_pm_window.mdm_helper_subsys_esoc0_count") if isinstance(queue, dict) else 0
        ),
        "queue_mdm_helper_mhi_pipe_count": intish(
            queue.get("post_pm_window.mdm_helper_mhi_pipe_count") if isinstance(queue, dict) else 0
        ),
        "queue_ks_count": intish(queue.get("post_pm_window.ks_count") if isinstance(queue, dict) else 0),
        "queue_per_mgr_subsys_modem_count": intish(
            queue.get("post_pm_window.per_mgr_subsys_modem_count") if isinstance(queue, dict) else 0
        ),
        "queue_per_mgr_subsys_esoc0_count": intish(
            queue.get("post_pm_window.per_mgr_subsys_esoc0_count") if isinstance(queue, dict) else 0
        ),
        "provider_per_mgr_vndbinder_count": intish(
            provider.get("post_pm_window.per_mgr_vndbinder_count") if isinstance(provider, dict) else 0
        ),
        "provider_mdm_helper_vndbinder_count": intish(
            provider.get("post_pm_window.mdm_helper_vndbinder_count") if isinstance(provider, dict) else 0
        ),
        "subsys_hold_mdm3": subsys_hold.get("post_pm_mdm_helper_window.mdm3_state", "")
        if isinstance(subsys_hold, dict)
        else "",
        "subsys_hold_mss": subsys_hold.get("post_pm_mdm_helper_window.mss_state", "")
        if isinstance(subsys_hold, dict)
        else "",
        "reboot_cleanup_version_seen": boolish(reboot_cleanup.get("version_seen") if isinstance(reboot_cleanup, dict) else False),
        "reboot_cleanup_status_healthy": boolish(
            reboot_cleanup.get("status_healthy") if isinstance(reboot_cleanup, dict) else False
        ),
    }


def summarize_references(v1139_report: str, esoc_research: str) -> dict[str, Any]:
    return {
        "v1139_report_present": bool(v1139_report),
        "v1139_report_lower_gap_statement": "no MHI pipe, ks, WLFW service 69, BDF, or wlan0" in v1139_report,
        "esoc_research_present": bool(esoc_research),
        "android_mdm_helper_ks_contract_recorded": (
            "Android actor evidence shows `mdm_helper` and `ks` holding `/dev/esoc-0`" in esoc_research
            and "ks` uses `/dev/mhi_0305_01.01.00_pipe_10" in esoc_research
        ),
        "android_pm_service_subsys_esoc0_recorded": (
            "`pm-service` holds `/dev/subsys_esoc0` and `/dev/subsys_modem`" in esoc_research
        ),
    }


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1139 = analysis["v1139"]
    refs = analysis["references"]
    pm_returns_ok = (
        "0x0" in {str(value) for value in v1139["pm_client_register_ret"]}
        and "0x0" in {str(value) for value in v1139["pm_client_connect_ret"]}
    )
    guardrails_clean = not any(
        bool(v1139[key])
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "wifi_bringup_executed",
            "partition_write_executed",
            "flash_executed",
        )
    )
    flags = {
        "v1139_passed": v1139["pass"] and v1139["decision"] == "v1139-post-pm-mdm-helper-lower-artifact-observed",
        "upper_pm_cnss_closed": (
            v1139["pm_actor_executed"]
            and v1139["cnss_daemon_start_executed"]
            and pm_returns_ok
            and v1139["vndservice_provider_seen"] == 1
        ),
        "v1071_exit255_route_obsolete": (
            v1139["per_mgr_exit_code"] == "0"
            and v1139["per_mgr_subsys_modem_seen"] == 1
            and v1139["pm_proxy_helper_subsys_modem_seen"] == 1
        ),
        "mdm_helper_esoc0_positive": (
            v1139["post_pm_exec_attempted"] == 1
            and v1139["post_pm_mdm_helper_observable"] == 1
            and v1139["post_pm_mdm_helper_esoc0_count"] > 0
            and v1139["queue_mdm_helper_esoc0_count"] > 0
        ),
        "subsys_esoc0_missing": (
            v1139["post_pm_mdm_helper_subsys_esoc0_count"] == 0
            and v1139["queue_mdm_helper_subsys_esoc0_count"] == 0
            and v1139["queue_per_mgr_subsys_esoc0_count"] == 0
        ),
        "mhi_ks_missing": (
            v1139["post_pm_mdm_helper_mhi_pipe_count"] == 0
            and v1139["queue_mdm_helper_mhi_pipe_count"] == 0
            and v1139["post_pm_ks_count"] == 0
            and v1139["queue_ks_count"] == 0
        ),
        "wlfw_publication_missing": (
            v1139["qrtr_service69"] == 0
            and v1139["wlfw_count"] == 0
            and v1139["bdf_count"] == 0
            and v1139["wlan0_count"] == 0
        ),
        "mdm3_still_offlining": (
            v1139["mdm3_after_observer"] == "OFFLINING"
            and v1139["subsys_hold_mdm3"] == "OFFLINING"
        ),
        "android_lower_contract_reference_available": (
            refs["android_mdm_helper_ks_contract_recorded"]
            and refs["android_pm_service_subsys_esoc0_recorded"]
        ),
        "guardrails_clean_and_recovered": (
            guardrails_clean
            and v1139["reboot_cleanup_version_seen"]
            and v1139["reboot_cleanup_status_healthy"]
        ),
    }
    missing = [name for name, ok in flags.items() if not ok]
    if not missing:
        return {
            "decision": "v1140-post-pm-esoc0-only-gap-classified",
            "pass": True,
            "reason": (
                "V1139 closes the stale pm-service exit-255 route and proves "
                "post-PM mdm_helper reaches /dev/esoc-0, but it does not progress "
                "to /dev/subsys_esoc0, MHI pipe, ks, WLFW service69, BDF, wlan0, or mdm3 ONLINE"
            ),
            "next_step": (
                "V1141 should add a bounded post-PM mdm_helper lower-trace support path: "
                "capture mdm_helper syscall/ioctl/wchan/status/fd progression and Android ks/MHI "
                "contract deltas without Wi-Fi HAL, scan/connect, credentials, DHCP, routes, external ping, "
                "boot image writes, or blind /dev/subsys_esoc0 trigger"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1140-post-pm-lower-gap-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh the missing V1139 evidence before selecting a new lower gate",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v1139 = manifest["analysis"]["v1139"]
    cls = manifest["analysis"]["classification"]
    rows = [
        ["V1139 pass", str(cls["flags"]["v1139_passed"]), v1139["decision"]],
        ["PM/CNSS closed", str(cls["flags"]["upper_pm_cnss_closed"]), f"register={v1139['pm_client_register_ret']} connect={v1139['pm_client_connect_ret']}"],
        ["V1071 exit255 obsolete", str(cls["flags"]["v1071_exit255_route_obsolete"]), f"per_mgr_exit={v1139['per_mgr_exit_code']} subsys_modem={v1139['per_mgr_subsys_modem_seen']}"],
        ["mdm_helper /dev/esoc-0", str(cls["flags"]["mdm_helper_esoc0_positive"]), str(v1139["post_pm_mdm_helper_esoc0_count"])],
        ["/dev/subsys_esoc0 missing", str(cls["flags"]["subsys_esoc0_missing"]), str(v1139["post_pm_mdm_helper_subsys_esoc0_count"])],
        ["MHI/ks missing", str(cls["flags"]["mhi_ks_missing"]), f"mhi={v1139['post_pm_mdm_helper_mhi_pipe_count']} ks={v1139['post_pm_ks_count']}"],
        ["WLFW missing", str(cls["flags"]["wlfw_publication_missing"]), f"svc69={v1139['qrtr_service69']} wlan0={v1139['wlan0_count']}"],
        ["mdm3 OFFLINING", str(cls["flags"]["mdm3_still_offlining"]), v1139["mdm3_after_observer"]],
        ["Android lower reference", str(cls["flags"]["android_lower_contract_reference_available"]), "mdm_helper+ks+MHI"],
        ["guardrails/recovery", str(cls["flags"]["guardrails_clean_and_recovered"]), "no HAL/scan/credential/DHCP/ping/flash"],
    ]
    facts = [
        ["mss after observer", v1139["mss_after_observer"]],
        ["mdm3 after observer", v1139["mdm3_after_observer"]],
        ["QRTR 69/74/180", f"{v1139['qrtr_service69']}/{v1139['qrtr_service74']}/{v1139['qrtr_service180']}"],
        ["per_mgr vndbinder", str(v1139["provider_per_mgr_vndbinder_count"])],
        ["mdm_helper vndbinder", str(v1139["provider_mdm_helper_vndbinder_count"])],
        ["pm_contract result", v1139["pm_contract_result"]],
        ["post_pm result", v1139["post_pm_result"]],
    ]
    return "\n".join(
        [
            "# V1140 Post-PM Lower Gap Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Classification",
            "",
            markdown_table(["evidence", "ok", "detail"], rows),
            "",
            "## Key Facts",
            "",
            markdown_table(["key", "value"], facts),
            "",
            "## Safety",
            "",
            "- device commands executed: `false`",
            "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`",
            "- boot image/partition writes/flash: `false`",
            "",
            "## Missing",
            "",
            json.dumps(cls["missing"], indent=2, sort_keys=True),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1139": summarize_v1139(load_json(args.v1139)),
        "references": summarize_references(read_text(args.v1139_report), read_text(args.esoc_research)),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1140",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1139": str(repo_path(args.v1139)),
            "v1139_report": str(repo_path(args.v1139_report)),
            "esoc_research": str(repo_path(args.esoc_research)),
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
