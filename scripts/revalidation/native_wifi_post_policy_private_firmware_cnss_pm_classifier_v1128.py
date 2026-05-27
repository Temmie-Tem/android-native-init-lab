#!/usr/bin/env python3
"""V1128 host-only classifier for post-policy private-firmware CNSS PM replay."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1128-post-policy-private-firmware-cnss-pm-classifier.txt")
DEFAULT_SELINUXFS = Path("tmp/wifi/v1128-v401-selinuxfs-mount/manifest.json")
DEFAULT_POLICY_LOAD = Path("tmp/wifi/v1128-v490-policy-load-v212/manifest.json")
DEFAULT_LIVE = Path("tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-observer-live/manifest.json")
DEFAULT_POST_PASS_PS = Path("tmp/wifi/v1128-post-policy-post-pass-ps.txt")
DEFAULT_POST_REBOOT_PS = Path("tmp/wifi/v1128-post-reboot-ps-r2.txt")

EXPECTED_SELINUXFS_DECISION = "toybox-selinuxfs-mount-live-executor-run-pass"
EXPECTED_POLICY_LOAD_DECISION = "v490-selinux-policy-load-proof-pass"
EXPECTED_LIVE_DECISION = "v1124-private-firmware-provider-preserved-cnss-connect-reached"
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


def label_count(data: dict[str, Any], comm_substring: str, label: str) -> int:
    total = 0
    by_label = tracefs(data).get("by_label_comm") or {}
    labels = by_label.get(label) if isinstance(by_label, dict) else {}
    if not isinstance(labels, dict):
        return 0
    for comm, count in labels.items():
        if comm_substring not in str(comm):
            continue
        try:
            total += int(count)
        except (TypeError, ValueError):
            continue
    return total


def bool_false(value: Any) -> bool:
    return value in (False, 0, "0", "false", "False", None)


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


def post_pass_surface(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return {
        "path": str(repo_path(path)),
        "exists": bool(text),
        "pm_proxy_helper_dstate": bool(re.search(r"\bpm_proxy_helper\b", text) and re.search(r"\bDs\b", text)),
        "pm_service_zombie": bool(re.search(r"\bpm-service\b", text) and re.search(r"\bZs\b", text)),
    }


def subsys_modem_pending(data: dict[str, Any]) -> bool:
    c = contract(data)
    for key, value in c.items():
        if key.endswith(".path.value") and value == "/dev/subsys_modem":
            prefix = key.rsplit(".path.value", 1)[0]
            return c.get(prefix + ".wchan") == "__subsystem_get"
    return False


def summarize_live(data: dict[str, Any]) -> dict[str, Any]:
    c = contract(data)
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "private_firmware_mounts_requested": c.get("private_firmware_mounts_requested", ""),
        "private_firmware_mnt_mounted": c.get("private_firmware_mnt_mounted", ""),
        "private_firmware_modem_mounted": c.get("private_firmware_modem_mounted", ""),
        "vndservicemanager_ready": c.get("vndservicemanager_readiness.ready", ""),
        "vndservice_provider_seen": c.get("vndservice_provider_seen", ""),
        "cnss_daemon_start_executed": c.get("cnss_daemon_start_executed", ""),
        "cnss_register_entry_count": label_count(data, "cnss", "pm_client_register_entry"),
        "cnss_register_ret": return_values(data, "cnss", "pm_client_register_ret"),
        "cnss_connect_entry_count": label_count(data, "cnss", "pm_client_connect_entry"),
        "cnss_connect_ret": return_values(data, "cnss", "pm_client_connect_ret"),
        "pm_server_register_ret": return_values(data, "Binder:", "pm_server_register_ret"),
        "pm_server_connect_ret": return_values(data, "Binder:", "pm_server_connect_ret"),
        "mdm3_state": c.get("post_provider_surface.after_cnss_daemon.mdm3_state", ""),
        "wlan0_exists": c.get("post_provider_surface.after_cnss_daemon.wlan0_exists", ""),
        "qcwlanstate_exists": c.get("post_provider_surface.after_cnss_daemon.qcwlanstate_exists", ""),
        "subsys_modem_pending": subsys_modem_pending(data),
        "observer_result": c.get("result", ""),
        "observer_reason": c.get("reason", ""),
        "wifi_hal_start_executed": c.get("wifi_hal_start_executed", ""),
        "scan_connect_linkup": c.get("scan_connect_linkup", ""),
        "external_ping": c.get("external_ping", ""),
        "subsys_esoc0_open_attempted": c.get("subsys_esoc0_open_attempted", ""),
        "forbidden_true": tracefs(data).get("forbidden_true") or [],
    }


def classify(
    selinuxfs: dict[str, Any],
    policy_load: dict[str, Any],
    live: dict[str, Any],
    post_pass_ps: Path,
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
        "post_pass_ps": post_pass_surface(post_pass_ps),
        "post_reboot_ps": post_reboot_clean(post_reboot_ps),
    }
    flags = {
        "selinuxfs_ready": comparison["selinuxfs"]["decision"] == EXPECTED_SELINUXFS_DECISION
        and comparison["selinuxfs"]["pass"],
        "policy_load_ready": comparison["policy_load"]["decision"] == EXPECTED_POLICY_LOAD_DECISION
        and comparison["policy_load"]["pass"]
        and comparison["policy_load"]["result"] == "policy-load-pass"
        and comparison["policy_load"]["policy_load_executed"],
        "live_expected": comparison["live"]["decision"] == EXPECTED_LIVE_DECISION
        and comparison["live"]["pass"],
        "provider_seen": comparison["live"]["vndservice_provider_seen"] == "1",
        "private_firmware_mounts": all(
            comparison["live"][key] == "1"
            for key in (
                "private_firmware_mounts_requested",
                "private_firmware_mnt_mounted",
                "private_firmware_modem_mounted",
            )
        ),
        "vndservicemanager_ready": comparison["live"]["vndservicemanager_ready"] == "1",
        "cnss_daemon_started": comparison["live"]["cnss_daemon_start_executed"] == "1",
        "cnss_pm_register_ok": "0x0" in comparison["live"]["cnss_register_ret"],
        "cnss_pm_connect_ok": "0x0" in comparison["live"]["cnss_connect_ret"],
        "pm_server_register_ok": "0x0" in comparison["live"]["pm_server_register_ret"],
        "pm_server_connect_ok": "0x0" in comparison["live"]["pm_server_connect_ret"],
        "lower_subsys_modem_blocker_seen": comparison["live"]["subsys_modem_pending"],
        "mdm3_still_offlining": comparison["live"]["mdm3_state"] == "OFFLINING",
        "wlan0_absent": comparison["live"]["wlan0_exists"] == "0",
        "no_wifi_hal_scan_external_ping": all(
            comparison["live"][key] == "0"
            for key in ("wifi_hal_start_executed", "scan_connect_linkup", "external_ping", "subsys_esoc0_open_attempted")
        ),
        "tracefs_forbidden_clear": not comparison["live"]["forbidden_true"],
        "post_pass_cleanup_needed_captured": comparison["post_pass_ps"]["pm_proxy_helper_dstate"],
        "post_reboot_clean": comparison["post_reboot_ps"]["clean"],
    }
    return {
        "comparison": comparison,
        "flags": flags,
        "interpretation": {
            "closed": [
                "V490 policy load is sufficient to preserve vendor.qcom.PeripheralManager visibility",
                "CNSS daemon reaches PM client register and connect with return 0",
                "PM server Binder side reaches register and connect with return 0",
                "the remaining live block is lower /dev/subsys_modem in __subsystem_get with mdm3 OFFLINING",
            ],
            "active_delta": (
                "service-manager policy and PM register/connect are no longer the active blocker; "
                "native Wi-Fi bring-up is now gated by the lower modem/eSoC path"
            ),
            "next_gate": (
                "V1129 should classify the /dev/subsys_modem __subsystem_get path and mdm3/eSoC "
                "state transition needed before any Wi-Fi HAL start or scan/connect"
            ),
        },
    }


def decide(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    flags = analysis["flags"]
    required = (
        "selinuxfs_ready",
        "policy_load_ready",
        "live_expected",
        "provider_seen",
        "private_firmware_mounts",
        "vndservicemanager_ready",
        "cnss_daemon_started",
        "cnss_pm_register_ok",
        "cnss_pm_connect_ok",
        "pm_server_register_ok",
        "pm_server_connect_ok",
        "lower_subsys_modem_blocker_seen",
        "mdm3_still_offlining",
        "wlan0_absent",
        "no_wifi_hal_scan_external_ping",
        "tracefs_forbidden_clear",
        "post_pass_cleanup_needed_captured",
        "post_reboot_clean",
    )
    missing = [key for key in required if not flags[key]]
    if not missing:
        return (
            "v1128-post-policy-cnss-pm-connect-reaches-subsys-modem-blocker",
            True,
            "post-policy private-firmware replay reaches CNSS PM register/connect OK, then blocks at /dev/subsys_modem with mdm3 OFFLINING",
            "classify lower /dev/subsys_modem and mdm3/eSoC transition before any Wi-Fi HAL or scan/connect gate",
        )
    return (
        "v1128-post-policy-cnss-pm-classifier-incomplete",
        False,
        f"missing={missing}",
        "refresh V1128 live evidence or inspect the post-policy replay manually",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    flag_rows = [[key, value] for key, value in analysis["flags"].items()]
    comparison_rows = [
        ["selinuxfs", json.dumps(analysis["comparison"]["selinuxfs"], sort_keys=True)],
        ["policy_load", json.dumps(analysis["comparison"]["policy_load"], sort_keys=True)],
        ["live", json.dumps(analysis["comparison"]["live"], sort_keys=True)],
        ["post_pass_ps", json.dumps(analysis["comparison"]["post_pass_ps"], sort_keys=True)],
        ["post_reboot_ps", json.dumps(analysis["comparison"]["post_reboot_ps"], sort_keys=True)],
    ]
    return "\n".join(
        [
            "# V1128 Post-Policy Private Firmware CNSS PM Classifier",
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
    parser.add_argument("--post-pass-ps", type=Path, default=DEFAULT_POST_PASS_PS)
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
                "next_gate": "run V1128 host-only classifier",
            },
        }
        decision, passed, reason, next_step = (
            "v1128-post-policy-cnss-pm-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1128 host-only classifier after V401/V490/V1124 live evidence exists",
        )
    else:
        analysis = classify(
            load_json(args.selinuxfs_manifest),
            load_json(args.policy_load_manifest),
            load_json(args.live_manifest),
            args.post_pass_ps,
            args.post_reboot_ps,
        )
        decision, passed, reason, next_step = decide(analysis)

    manifest = {
        "cycle": "v1128",
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
            "post_pass_ps": str(repo_path(args.post_pass_ps)),
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
