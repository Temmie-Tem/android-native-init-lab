#!/usr/bin/env python3
"""Host-only classifier for V1131 modem-holder live evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_post_policy_global_firmware_modem_holder_live_v1131 as live
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1131-post-policy-global-firmware-modem-holder-classifier.txt")
DEFAULT_LIVE = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-cnss-pm-live/manifest.json")
DEFAULT_SELINUXFS = Path("tmp/wifi/v1131-v401-selinuxfs-mount/manifest.json")
DEFAULT_POLICY_LOAD = Path("tmp/wifi/v1131-v490-policy-load-v213/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return live.contract(manifest)


def cget(values: dict[str, str], key: str) -> str:
    return live.contract_value(values, key)


def subsys_modem_blocked(values: dict[str, str]) -> bool:
    for key, value in values.items():
        if key.endswith(".path.value") and value == "/dev/subsys_modem":
            prefix = key.rsplit(".path.value", 1)[0]
            if values.get(prefix + ".wchan") == "__subsystem_get":
                return True
    return False


def summarize(live_manifest: dict[str, Any]) -> dict[str, Any]:
    values = contract(live_manifest)
    firmware = live.firmware_summary(live_manifest)
    fixed_args = argparse.Namespace(command="run")
    fixed_decision, fixed_pass, fixed_reason, fixed_next = live.decide_v1131(fixed_args, live_manifest)
    marker_counts = ((firmware.get("markers") or {}).get("counts") or {})
    services = firmware.get("qrtr_services_after_observer") or {}
    return {
        "input_decision": live_manifest.get("decision", ""),
        "input_pass": bool(live_manifest.get("pass")),
        "fixed_decision": fixed_decision,
        "fixed_pass": fixed_pass,
        "fixed_reason": fixed_reason,
        "fixed_next": fixed_next,
        "runner_false_negative": live_manifest.get("decision") == "v1131-modem-holder-not-requested"
        and fixed_decision == "v1131-modem-holder-not-confirmed",
        "holder": live.modem_holder_fields(values),
        "holder_requested": cget(values, "modem_pre_holder_requested") == "1",
        "holder_allowed": cget(values, "modem_pre_holder_allowed") == "1",
        "holder_start_attempted": cget(values, "modem_pre_holder_start_attempted") == "1",
        "holder_child_chroot": cget(values, "modem_pre_holder_child_chroot") == "1",
        "holder_plain_retry": cget(values, "modem_pre_holder_plain_retry"),
        "holder_open_reported": cget(values, "modem_pre_holder_open_reported") == "1",
        "holder_result_reported": cget(values, "modem_pre_holder_result_reported") == "1",
        "holder_confirmed": live.holder_confirmed(values),
        "holder_cleanup_kill_sent": cget(values, "modem_pre_holder_cleanup_kill_sent") == "1",
        "holder_cleanup_reaped": cget(values, "modem_pre_holder_cleanup_reaped") == "1",
        "provider_seen": values.get("vndservice_provider_seen") == "1",
        "vndservicemanager_ready": values.get("vndservicemanager_readiness.ready") == "1",
        "cnss_daemon_started": values.get("cnss_daemon_start_executed") == "1",
        "cnss_register_ret": live.cnss_return_values(live_manifest, "pm_client_register_ret"),
        "cnss_connect_ret": live.cnss_return_values(live_manifest, "pm_client_connect_ret"),
        "subsys_modem_binder_open_blocked": subsys_modem_blocked(values),
        "per_mgr_subsys_modem_seen": values.get("per_mgr_subsys_modem_seen", ""),
        "pm_proxy_helper_subsys_modem_seen": values.get("pm_proxy_helper_subsys_modem_seen", ""),
        "mss_after": firmware.get("mss_after_observer", ""),
        "mdm3_after": firmware.get("mdm3_after_observer", ""),
        "qrtr_services_after": services,
        "marker_counts": marker_counts,
        "no_wlfw_wlan0": not any(
            int(marker_counts.get(key) or 0) > 0
            for key in ("wlfw", "wlan0", "bdf", "mhi", "qca6390", "sysmon_qmi")
        )
        and int(services.get("69") or 0) == 0,
        "wifi_hal_start_executed": values.get("wifi_hal_start_executed", "") == "1",
        "scan_connect_linkup": values.get("scan_connect_linkup", "") == "1",
        "external_ping": values.get("external_ping", "") == "1",
        "subsys_esoc0_open_attempted": values.get("subsys_esoc0_open_attempted", "") == "1",
        "cleanup": firmware.get("reboot_cleanup") or {},
    }


def classify(selinuxfs: dict[str, Any], policy_load: dict[str, Any], live_manifest: dict[str, Any]) -> dict[str, Any]:
    summary = summarize(live_manifest)
    cleanup = summary["cleanup"]
    flags = {
        "selinuxfs_ready": selinuxfs.get("decision") == "toybox-selinuxfs-mount-live-executor-run-pass"
        and bool(selinuxfs.get("pass")),
        "policy_load_ready": policy_load.get("decision") == "v490-selinux-policy-load-proof-pass"
        and bool(policy_load.get("pass"))
        and ((policy_load.get("load") or {}).get("result") == "policy-load-pass"),
        "holder_attempted_but_open_pending": summary["holder_requested"]
        and summary["holder_allowed"]
        and summary["holder_start_attempted"]
        and summary["holder_child_chroot"]
        and summary["holder_plain_retry"] == "0"
        and not summary["holder_open_reported"]
        and not summary["holder_result_reported"]
        and not summary["holder_confirmed"],
        "provider_and_cnss_pm_ok": summary["provider_seen"]
        and summary["vndservicemanager_ready"]
        and summary["cnss_daemon_started"]
        and "0x0" in summary["cnss_register_ret"]
        and "0x0" in summary["cnss_connect_ret"],
        "subsys_modem_blocker_reproduced": summary["subsys_modem_binder_open_blocked"],
        "lower_state_still_blocked": summary["mss_after"] == "OFFLINING"
        and summary["mdm3_after"] == "OFFLINING"
        and summary["no_wlfw_wlan0"],
        "no_forbidden_wifi_or_esoc": not any(
            summary[key]
            for key in (
                "wifi_hal_start_executed",
                "scan_connect_linkup",
                "external_ping",
                "subsys_esoc0_open_attempted",
            )
        ),
        "cleanup_reboot_healthy": bool(cleanup.get("version_seen")) and bool(cleanup.get("status_healthy")),
        "runner_false_negative": summary["runner_false_negative"],
    }
    required = (
        "selinuxfs_ready",
        "policy_load_ready",
        "holder_attempted_but_open_pending",
        "provider_and_cnss_pm_ok",
        "subsys_modem_blocker_reproduced",
        "lower_state_still_blocked",
        "no_forbidden_wifi_or_esoc",
        "cleanup_reboot_healthy",
    )
    missing = [key for key in required if not flags[key]]
    if not missing:
        decision = "v1131-modem-pre-holder-open-pending-subsys-modem-blocker-confirmed"
        passed = True
        reason = (
            "v213 modem pre-holder was requested/allowed/started, but O_NONBLOCK open produced no result and "
            "PM Binder worker still blocked in __subsystem_get; mss/mdm3/WLFW/wlan0 did not advance"
        )
        next_step = "classify why /dev/subsys_modem O_NONBLOCK open still hangs, likely subsystem_get path ignores nonblock"
    else:
        decision = "v1131-modem-holder-classifier-incomplete"
        passed = False
        reason = "missing=" + ",".join(missing)
        next_step = "inspect V1131 live evidence before retry"
    return {
        "summary": summary,
        "flags": flags,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    summary = analysis["summary"]
    rows = [
        ["input_decision", summary["input_decision"]],
        ["fixed_decision", summary["fixed_decision"]],
        ["runner_false_negative", str(summary["runner_false_negative"])],
        ["holder_requested", str(summary["holder_requested"])],
        ["holder_allowed", str(summary["holder_allowed"])],
        ["holder_start_attempted", str(summary["holder_start_attempted"])],
        ["holder_confirmed", str(summary["holder_confirmed"])],
        ["holder_cleanup_reaped", str(summary["holder_cleanup_reaped"])],
        ["provider_seen", str(summary["provider_seen"])],
        ["cnss_register_ret", json.dumps(summary["cnss_register_ret"])],
        ["cnss_connect_ret", json.dumps(summary["cnss_connect_ret"])],
        ["subsys_modem_binder_open_blocked", str(summary["subsys_modem_binder_open_blocked"])],
        ["mss_after", summary["mss_after"]],
        ["mdm3_after", summary["mdm3_after"]],
        ["qrtr_services_after", json.dumps(summary["qrtr_services_after"], sort_keys=True)],
        ["marker_counts", json.dumps(summary["marker_counts"], sort_keys=True)],
    ]
    flag_rows = [[key, str(value)] for key, value in sorted(analysis["flags"].items())]
    return "\n".join([
        "# V1131 Post-policy Global Firmware Modem-holder Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Summary",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## Flags",
        "",
        markdown_table(["flag", "value"], flag_rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--live-manifest", type=Path, default=DEFAULT_LIVE)
    parser.add_argument("--selinuxfs-manifest", type=Path, default=DEFAULT_SELINUXFS)
    parser.add_argument("--policy-load-manifest", type=Path, default=DEFAULT_POLICY_LOAD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    selinuxfs = load_json(args.selinuxfs_manifest)
    policy_load = load_json(args.policy_load_manifest)
    live_manifest = load_json(args.live_manifest)
    analysis = classify(selinuxfs, policy_load, live_manifest)
    manifest = {
        "cycle": "v1131",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "selinuxfs_manifest": str(repo_path(args.selinuxfs_manifest)),
            "policy_load_manifest": str(repo_path(args.policy_load_manifest)),
            "live_manifest": str(repo_path(args.live_manifest)),
        },
        "analysis": {"summary": analysis["summary"], "flags": analysis["flags"]},
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "next_step": analysis["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
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
