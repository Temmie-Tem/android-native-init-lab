#!/usr/bin/env python3
"""V1129 host-only classifier for post-policy global firmware mount-only replay."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1129-post-policy-global-firmware-mount-only-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1129-post-policy-global-firmware-mount-only-classifier.txt")
DEFAULT_SELINUXFS = Path("tmp/wifi/v1129-v401-selinuxfs-mount/manifest.json")
DEFAULT_POLICY_LOAD = Path("tmp/wifi/v1129-v490-policy-load-v212/manifest.json")
DEFAULT_LIVE = Path("tmp/wifi/v1129-post-policy-global-firmware-mount-only-cnss-pm-live/manifest.json")
DEFAULT_POST_REBOOT_PS = Path("tmp/wifi/v1129-post-reboot-ps.txt")

EXPECTED_SELINUXFS_DECISION = "toybox-selinuxfs-mount-live-executor-run-pass"
EXPECTED_POLICY_LOAD_DECISION = "v490-selinux-policy-load-proof-pass"
EXPECTED_LIVE_DECISION = "v1121-firmware-mount-only-provider-cnss-connect-ok"
ACTOR_RE = re.compile(
    r"\b(pm-service|pm_proxy_helper|per_proxy|servicemanager|hwservicemanager|"
    r"vndservicemanager|cnss-daemon|cnss_diag|android\.hardware\.wifi|wificond|wpa_supplicant)\b"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def tracefs(data: dict[str, Any]) -> dict[str, Any]:
    value = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    return value if isinstance(value, dict) else {}


def firmware_summary(data: dict[str, Any]) -> dict[str, Any]:
    value = nested_get(data, ("analysis", "firmware_mount_only"), {})
    return value if isinstance(value, dict) else {}


def contract(data: dict[str, Any]) -> dict[str, str]:
    value = tracefs(data).get("pm_contract") or {}
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def return_values(data: dict[str, Any], comm_substring: str, label: str) -> list[str]:
    values: list[str] = []
    by_comm = tracefs(data).get("return_values_by_comm") or {}
    if not isinstance(by_comm, dict):
        return values
    for comm, labels in by_comm.items():
        if comm_substring not in str(comm):
            continue
        if isinstance(labels, dict):
            values.extend(str(item) for item in labels.get(label, []))
    return values


def subsys_modem_pending(data: dict[str, Any]) -> bool:
    c = contract(data)
    for key, value in c.items():
        if key.endswith(".path.value") and value == "/dev/subsys_modem":
            prefix = key.rsplit(".path.value", 1)[0]
            return c.get(prefix + ".wchan") == "__subsystem_get"
    return False


def post_reboot_clean(path: Path) -> dict[str, Any]:
    text = read_text(path)
    matches = ACTOR_RE.findall(text)
    busy = "status=busy" in text or "[busy]" in text
    return {
        "path": str(repo_path(path)),
        "exists": bool(text),
        "busy": busy,
        "matches": matches,
        "clean": bool(text) and not busy and not matches,
    }


def summarize_live(data: dict[str, Any]) -> dict[str, Any]:
    c = contract(data)
    fw = firmware_summary(data)
    marker_counts = (fw.get("markers") or {}).get("counts") or {}
    services = fw.get("qrtr_services_after_observer") or {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "mounted_hits": fw.get("mounted_hits") or {},
        "firmware_class_path": fw.get("firmware_class_path", ""),
        "mss_before": fw.get("mss_before", ""),
        "mss_after_observer": fw.get("mss_after_observer", ""),
        "mdm3_before": fw.get("mdm3_before", ""),
        "mdm3_after_observer": fw.get("mdm3_after_observer", ""),
        "qrtr_services_after_observer": services,
        "marker_counts": marker_counts,
        "vndservicemanager_ready": c.get("vndservicemanager_readiness.ready", ""),
        "vndservice_provider_seen": c.get("vndservice_provider_seen", ""),
        "cnss_daemon_start_executed": c.get("cnss_daemon_start_executed", ""),
        "cnss_register_ret": return_values(data, "cnss", "pm_client_register_ret"),
        "cnss_connect_ret": return_values(data, "cnss", "pm_client_connect_ret"),
        "subsys_modem_pending": subsys_modem_pending(data),
        "wifi_hal_start_executed": c.get("wifi_hal_start_executed", ""),
        "scan_connect_linkup": c.get("scan_connect_linkup", ""),
        "external_ping": c.get("external_ping", ""),
        "subsys_esoc0_open_attempted": c.get("subsys_esoc0_open_attempted", ""),
        "global_modem_holder_opened": bool(data.get("global_modem_holder_opened")),
        "firmware_mounts_executed": bool(data.get("firmware_mounts_executed")),
        "reboot_executed": bool(data.get("reboot_executed")),
    }


def classify(
    selinuxfs: dict[str, Any],
    policy_load: dict[str, Any],
    live: dict[str, Any],
    post_reboot_ps: Path,
) -> dict[str, Any]:
    live_summary = summarize_live(live)
    policy_result = nested_get(policy_load, ("load", "result"), "")
    policy_executed = bool(policy_load.get("policy_load_executed")) or bool(
        nested_get(policy_load, ("load", "policy_load_executed"), 0)
    )
    comparison = {
        "selinuxfs": {
            "decision": selinuxfs.get("decision", ""),
            "pass": bool(selinuxfs.get("pass")),
        },
        "policy_load": {
            "decision": policy_load.get("decision", ""),
            "pass": bool(policy_load.get("pass")),
            "result": policy_result,
            "policy_load_executed": policy_executed,
        },
        "live": live_summary,
        "post_reboot_ps": post_reboot_clean(post_reboot_ps),
    }
    marker_counts = comparison["live"]["marker_counts"]
    services = comparison["live"]["qrtr_services_after_observer"]
    flags = {
        "selinuxfs_ready": comparison["selinuxfs"]["decision"] == EXPECTED_SELINUXFS_DECISION
        and comparison["selinuxfs"]["pass"],
        "policy_load_ready": comparison["policy_load"]["decision"] == EXPECTED_POLICY_LOAD_DECISION
        and comparison["policy_load"]["pass"]
        and comparison["policy_load"]["result"] == "policy-load-pass"
        and comparison["policy_load"]["policy_load_executed"],
        "live_expected": comparison["live"]["decision"] == EXPECTED_LIVE_DECISION
        and comparison["live"]["pass"],
        "global_firmware_mounts_visible": all((comparison["live"]["mounted_hits"] or {}).values()),
        "provider_seen": comparison["live"]["vndservice_provider_seen"] == "1",
        "vndservicemanager_ready": comparison["live"]["vndservicemanager_ready"] == "1",
        "cnss_daemon_started": comparison["live"]["cnss_daemon_start_executed"] == "1",
        "cnss_pm_register_ok": "0x0" in comparison["live"]["cnss_register_ret"],
        "cnss_pm_connect_ok": "0x0" in comparison["live"]["cnss_connect_ret"],
        "subsys_modem_blocker_still_seen": comparison["live"]["subsys_modem_pending"],
        "mss_still_offlining": comparison["live"]["mss_after_observer"] == "OFFLINING",
        "mdm3_still_offlining": comparison["live"]["mdm3_after_observer"] == "OFFLINING",
        "no_wlfw_or_wlan0_advance": not any(
            int(marker_counts.get(key) or 0) > 0
            for key in ("wlfw", "wlan0", "bdf", "mhi", "qca6390", "sysmon_qmi")
        )
        and int(services.get("69") or 0) == 0,
        "no_global_holder": not comparison["live"]["global_modem_holder_opened"],
        "no_wifi_hal_scan_external_ping": all(
            comparison["live"][key] == "0"
            for key in ("wifi_hal_start_executed", "scan_connect_linkup", "external_ping", "subsys_esoc0_open_attempted")
        ),
        "post_reboot_clean": comparison["post_reboot_ps"]["clean"],
    }
    return {
        "comparison": comparison,
        "flags": flags,
        "interpretation": {
            "closed": [
                "V490 plus global firmware mount-only preserves provider visibility",
                "CNSS daemon PM client register/connect still returns 0",
                "global firmware mount-only does not advance mss, mdm3, WLFW, service 69, or wlan0",
                "the /dev/subsys_modem __subsystem_get blocker remains without a global modem holder",
            ],
            "active_delta": (
                "global firmware visibility alone is insufficient; the next gate needs a bounded "
                "modem holder or equivalent PM/eSoC first-opener contract without losing CNSS PM connect"
            ),
            "next_gate": (
                "V1130 should combine the V1128/V1129 post-policy provider-positive CNSS order with a "
                "bounded /dev/subsys_modem first-opener contract, while still forbidding /dev/subsys_esoc0, "
                "Wi-Fi HAL, scan/connect, credentials, and external ping"
            ),
        },
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    flags = analysis["flags"]
    required = (
        "selinuxfs_ready",
        "policy_load_ready",
        "live_expected",
        "global_firmware_mounts_visible",
        "provider_seen",
        "vndservicemanager_ready",
        "cnss_daemon_started",
        "cnss_pm_register_ok",
        "cnss_pm_connect_ok",
        "subsys_modem_blocker_still_seen",
        "mss_still_offlining",
        "mdm3_still_offlining",
        "no_wlfw_or_wlan0_advance",
        "no_global_holder",
        "no_wifi_hal_scan_external_ping",
        "post_reboot_clean",
    )
    missing = [key for key in required if not flags[key]]
    if not missing:
        return (
            "v1129-global-firmware-mount-only-insufficient-subsys-modem-blocker-remains",
            True,
            "global firmware mount-only preserves provider/CNSS PM connect but does not advance mss/mdm3/WLFW; /dev/subsys_modem still blocks",
            "add a bounded /dev/subsys_modem first-opener contract to the post-policy provider-positive CNSS order",
        )
    return (
        "v1129-global-firmware-mount-only-classifier-incomplete",
        False,
        f"missing={missing}",
        "refresh V1129 evidence or inspect the global firmware replay manually",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    flag_rows = [[key, value] for key, value in analysis["flags"].items()]
    comparison_rows = [
        ["selinuxfs", json.dumps(analysis["comparison"]["selinuxfs"], sort_keys=True)],
        ["policy_load", json.dumps(analysis["comparison"]["policy_load"], sort_keys=True)],
        ["live", json.dumps(analysis["comparison"]["live"], sort_keys=True)],
        ["post_reboot_ps", json.dumps(analysis["comparison"]["post_reboot_ps"], sort_keys=True)],
    ]
    return "\n".join(
        [
            "# V1129 Post-Policy Global Firmware Mount-only Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            "",
            "## Flags",
            "",
            markdown_table(["flag", "value"], flag_rows),
            "",
            "## Comparison",
            "",
            markdown_table(["gate", "value"], comparison_rows),
            "",
            "## Interpretation",
            "",
            "- closed:",
            *[f"  - {item}" for item in analysis["interpretation"]["closed"]],
            f"- active_delta: {analysis['interpretation']['active_delta']}",
            f"- next_gate: {analysis['interpretation']['next_gate']}",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--selinuxfs-manifest", type=Path, default=DEFAULT_SELINUXFS)
    parser.add_argument("--policy-load-manifest", type=Path, default=DEFAULT_POLICY_LOAD)
    parser.add_argument("--live-manifest", type=Path, default=DEFAULT_LIVE)
    parser.add_argument("--post-reboot-ps", type=Path, default=DEFAULT_POST_REBOOT_PS)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        analysis: dict[str, Any] = {
            "comparison": {},
            "flags": {},
            "interpretation": {
                "closed": [],
                "active_delta": "plan-only",
                "next_gate": "run V1129 host-only classifier",
            },
        }
        decision, passed, reason, next_step = (
            "v1129-global-firmware-mount-only-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1129 host-only classifier after V401/V490/V1121 live evidence exists",
        )
    else:
        analysis = classify(
            load_json(args.selinuxfs_manifest),
            load_json(args.policy_load_manifest),
            load_json(args.live_manifest),
            args.post_reboot_ps,
        )
        decision, passed, reason, next_step = decide(analysis)

    manifest = {
        "cycle": "v1129",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "selinuxfs_manifest": str(repo_path(args.selinuxfs_manifest)),
            "policy_load_manifest": str(repo_path(args.policy_load_manifest)),
            "live_manifest": str(repo_path(args.live_manifest)),
            "post_reboot_ps": str(repo_path(args.post_reboot_ps)),
        },
        "analysis": analysis,
        "device_commands_executed": False,
        "firmware_mounts_executed": False,
        "global_modem_holder_opened": False,
        "tracefs_write_executed": False,
        "policy_load_executed": False,
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
        "reboot_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
