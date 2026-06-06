#!/usr/bin/env python3
"""V816 host-only idle-vs-trigger subsystem/sysmon delta classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v816-idle-trigger-delta-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v816-idle-trigger-delta-classifier.txt")
DEFAULT_V815_MANIFEST = Path("tmp/wifi/v815-subsystem-sysmon-snapshot/manifest.json")
DEFAULT_V812_MANIFEST = Path("tmp/wifi/v812-mdm3-wlanpd-service69-observer-rerun/manifest.json")

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash, boot image write, or partition write",
    "reboot or bootloader handoff",
    "daemon start, service-manager start, Wi-Fi HAL start, scan/connect/link-up, or credential use",
    "DHCP, route change, or external ping",
    "boot_wlan, qcwlanstate, esoc0, bind/unbind, driver override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v815-manifest", type=Path, default=DEFAULT_V815_MANIFEST)
    parser.add_argument("--v812-manifest", type=Path, default=DEFAULT_V812_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"_file": {"path": str(resolved), "exists": False}}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_file": {"path": str(resolved), "exists": True, "error": str(exc)}}
    if not isinstance(payload, dict):
        payload = {}
    payload["_file"] = {"path": str(resolved), "exists": True}
    return payload


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_analysis(v815: dict[str, Any], v812: dict[str, Any]) -> dict[str, Any]:
    idle = as_dict(v815.get("analysis"))
    trigger = as_dict(as_dict(v812.get("v735_arm")).get("summary"))
    trigger_markers = as_dict(trigger.get("markers"))
    trigger_qrtr = as_dict(trigger.get("qrtr_readback"))
    idle_runtime = as_dict(idle.get("runtime_counts"))
    return {
        "idle": {
            "decision": v815.get("decision", ""),
            "pass": bool(v815.get("pass")),
            "mss_or_modem_state": idle.get("mss_or_modem_state"),
            "mdm3_state": idle.get("mdm3_state"),
            "subsys_count": int_value(idle.get("subsys_count")),
            "esoc_surface_present": bool(idle.get("esoc_surface_present")),
            "icnss_platform_present": bool(idle.get("icnss_platform_present")),
            "runtime_counts": {
                "sysmon_qmi": int_value(idle_runtime.get("sysmon_qmi")),
                "service_notifier_180": int_value(idle_runtime.get("service_notifier_180")),
                "service_notifier_74": int_value(idle_runtime.get("service_notifier_74")),
                "wlan_pd": int_value(idle_runtime.get("wlan_pd")),
                "wlfw": int_value(idle_runtime.get("wlfw")),
                "bdf": int_value(idle_runtime.get("bdf")),
                "wlan0": int_value(idle_runtime.get("wlan0")),
                "service_locator": int_value(idle_runtime.get("service_locator")),
            },
        },
        "trigger": {
            "decision": v812.get("decision", ""),
            "pass": bool(v812.get("pass")),
            "mss": [trigger.get("mss_after_holder"), trigger.get("mss_after_companion")],
            "mdm3": [trigger.get("mdm3_after_holder"), trigger.get("mdm3_after_companion")],
            "markers": {
                "qrtr_rx": int_value(trigger_markers.get("qrtr_rx")),
                "qrtr_tx": int_value(trigger_markers.get("qrtr_tx")),
                "sysmon_qmi": int_value(trigger_markers.get("sysmon_qmi")),
                "service_notifier": int_value(trigger_markers.get("service_notifier")),
                "wlan_pd": int_value(trigger_markers.get("wlan_pd")),
                "wlfw": int_value(trigger_markers.get("wlfw")),
                "bdf": int_value(trigger_markers.get("bdf")),
                "wlan0": int_value(trigger_markers.get("wlan0")),
                "kernel_warning": int_value(trigger_markers.get("kernel_warning")),
            },
            "qrtr_readback": {
                "service_events": int_value(trigger_qrtr.get("service_events")),
                "timeouts": int_value(trigger_qrtr.get("timeouts")),
                "qmi_attempted": int_value(trigger_qrtr.get("qmi_attempted")),
            },
        },
    }


def build_checks(command: str, v815: dict[str, Any], v812: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only idle-vs-trigger delta plan; no device command executed",
            "next_step": "run host-only delta classifier",
        }]
    idle = analysis["idle"]
    trigger = analysis["trigger"]
    idle_counts = idle["runtime_counts"]
    trigger_markers = trigger["markers"]
    trigger_qrtr = trigger["qrtr_readback"]
    inputs_ready = (
        v815.get("pass") is True
        and v815.get("decision") == "v815-idle-registration-snapshot-captured"
        and v812.get("pass") is True
        and v812.get("decision") == "v812-sysmon-without-service69"
    )
    idle_baseline_clear = (
        idle["mss_or_modem_state"] == "OFFLINING"
        and idle["mdm3_state"] == "OFFLINING"
        and idle_counts["sysmon_qmi"] == 0
        and idle_counts["service_notifier_74"] == 0
        and idle_counts["wlan_pd"] == 0
        and idle_counts["wlfw"] == 0
    )
    trigger_advances_mss_sysmon = (
        "ONLINE" in trigger["mss"]
        and trigger_markers["qrtr_tx"] > 0
        and trigger_markers["sysmon_qmi"] > 0
    )
    trigger_still_blocks_service = (
        trigger["mdm3"] == ["OFFLINING", "OFFLINING"]
        and trigger_markers["service_notifier"] == 0
        and trigger_markers["wlan_pd"] == 0
        and trigger_markers["wlfw"] == 0
        and trigger_markers["bdf"] == 0
        and trigger_markers["wlan0"] == 0
        and trigger_qrtr["service_events"] == 0
        and trigger_qrtr["timeouts"] == 0
    )
    return [
        {
            "name": "required-inputs",
            "status": "pass" if inputs_ready else "blocked",
            "detail": {
                "v815": {"decision": v815.get("decision"), "pass": v815.get("pass")},
                "v812": {"decision": v812.get("decision"), "pass": v812.get("pass")},
            },
            "next_step": "restore V815/V812 evidence before comparing deltas",
        },
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no device command, flash, reboot, HAL, scan/connect, credential use, DHCP, route, or ping",
            "next_step": "preserve V816 as classifier only",
        },
        {
            "name": "idle-baseline-clear",
            "status": "pass" if idle_baseline_clear else "blocked",
            "detail": idle,
            "next_step": "refresh idle snapshot if baseline already contains service publication",
        },
        {
            "name": "trigger-advances-mss-sysmon",
            "status": "pass" if trigger_advances_mss_sysmon else "blocked",
            "detail": trigger,
            "next_step": "rerun lower trigger observer if it no longer advances mss/sysmon",
        },
        {
            "name": "trigger-still-blocks-service-publication",
            "status": "pass" if trigger_still_blocks_service else "blocked",
            "detail": trigger,
            "next_step": "if service publication appears, route to WLFW/BDF readiness instead",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v816-idle-trigger-delta-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only idle-vs-trigger delta classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v816-idle-trigger-delta-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore input evidence or rerun the relevant bounded observer",
        )
    return (
        "v816-trigger-advances-mss-sysmon-not-mdm3-service",
        True,
        "idle has modem/mdm3 offlining and no service publication; lower trigger advances mss/QRTR/sysmon but leaves mdm3/service74/WLAN-PD/WLFW absent",
        "V817 should sample subsystem/sysmon/service-locator state inside the bounded lower trigger window at before/after holder/companion points",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v815 = load_json(args.v815_manifest)
    v812 = load_json(args.v812_manifest)
    analysis = build_analysis(v815, v812)
    checks = build_checks(args.command, v815, v812, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v816",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v815_manifest": v815.get("_file", {}),
            "v812_manifest": v812.get("_file", {}),
        },
        "analysis": analysis,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    signal_rows = [
        ["idle", json.dumps(manifest["analysis"]["idle"], sort_keys=True)],
        ["trigger", json.dumps(manifest["analysis"]["trigger"], sort_keys=True)],
    ]
    return "\n".join([
        "# V816 Idle-vs-Trigger Delta Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
