#!/usr/bin/env python3
"""V692 current-boot orchestrator for PeripheralManager registry snapshot proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_same_helper_replay_v673 as v673
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v692-peripheral-manager-registry-snapshot-orchestrated")
V692_SCRIPT = "scripts/revalidation/native_wifi_peripheral_manager_registry_snapshot_v692.py"
V692_APPROVAL = (
    "approve v692 PeripheralManager provider registry snapshot proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)
HELPER_SHA256 = "cce86ee252a045c7b8127b5e566abcb3ef24cdd89ac16d4592636838b9eb3e2b"
HELPER_MARKER = "a90_android_execns_probe v116"

ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded helper v116 PeripheralManager provider registry snapshot proof",
    "read-only cnss2/icnss/QCA6390 focused captures",
    "WLFW QRTR nameservice readback without QMI payload",
    "runner-owned reboot cleanup",
)
FORBIDDEN_ACTIONS = (
    "Wi-Fi HAL or wificond start",
    "supplicant or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "sysfs subsystem state write",
    "esoc0 open or hold",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v673.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v673.DEFAULT_PORT)
    parser.add_argument("--expect-version", default=v673.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=v673.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=HELPER_SHA256)
    parser.add_argument("--helper-marker", default=HELPER_MARKER)
    parser.add_argument("--wait-sec", type=float, default=75.0)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def counts_for(arm: dict[str, Any] | None) -> dict[str, int]:
    live = (arm or {}).get("live") or {}
    counts = live.get("v655_counts") or {}
    keys = (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "kernel_warning",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )
    return {key: int_value(counts.get(key)) for key in keys}


def markers_for(arm: dict[str, Any] | None) -> dict[str, int]:
    live = (arm or {}).get("live") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    return {
        key: int_value(counts.get(key))
        for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "kernel_warning", "wlfw", "bdf", "wlan0")
    }


def peripheral_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v692_peripheral_manager_surface")
    return surface if isinstance(surface, dict) else {}


def property_shim_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v692_property_shim_surface")
    return surface if isinstance(surface, dict) else {}


def registry_snapshot_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v692_registry_snapshot_surface")
    return surface if isinstance(surface, dict) else {}


def focus_for(arm: dict[str, Any] | None) -> dict[str, Any]:
    live = (arm or {}).get("live") or {}
    surface = live.get("v668_cnss2_focus_surface")
    return surface if isinstance(surface, dict) else {}


def wifi_advanced(counts: dict[str, int], markers: dict[str, int]) -> bool:
    return any(counts.get(key, 0) > 0 for key in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )) or any(markers.get(key, 0) > 0 for key in ("wlfw", "bdf", "wlan0"))


def provider_ready(surface: dict[str, Any]) -> bool:
    children = surface.get("children") or {}

    def child_stable(name: str) -> bool:
        child = children.get(name) or {}
        natural_exit = (
            child.get("exited") == "1"
            and child.get("signal") in {"", "0"}
            and child.get("exit_code") not in {"", "-1"}
        )
        return not natural_exit

    return (
        surface.get("peripheral_manager_enabled") == "1"
        and (surface.get("per_mgr") or {}).get("ready") == "1"
        and (surface.get("per_proxy") or {}).get("ready") == "1"
        and child_stable("per_mgr")
        and child_stable("per_proxy")
    )


def context_repair_regressed(surface: dict[str, Any]) -> bool:
    children = surface.get("children") or {}
    for name in ("per_mgr", "per_proxy"):
        child = children.get(name) or {}
        if child.get("selinux_exec_target_context") == "u:r:per_mgr:s0":
            return True
        if child.get("selinux_exec_errno") == "22":
            return True
    return False


EXPECTED_PRIVATE_ACKS = {
    ("vendor.peripheral.SDX50M.state", "OFFLINE"),
    ("vendor.peripheral.modem.state", "OFFLINE"),
}


def property_ack_regressed(surface: dict[str, Any]) -> bool:
    requests = surface.get("requests") or []
    seen_expected: set[tuple[str, str]] = set()
    for request in requests:
        name = str(request.get("name") or "")
        value = str(request.get("value") or "")
        allowed = str(request.get("allowed") or "")
        result = str(request.get("result") or "")
        pair = (name, value)
        if pair in EXPECTED_PRIVATE_ACKS:
            if allowed != "1" or result.lower() != "0x00000000":
                return True
            seen_expected.add(pair)
        elif name.startswith("vendor.peripheral.") and allowed == "1":
            return True
    return not EXPECTED_PRIVATE_ACKS.issubset(seen_expected)


def registry_snapshot_complete(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    for phase in (
        "before_initial_cnss_cleanup",
        "after_initial_cnss_cleanup",
        "after_per_mgr_probe",
        "after_per_proxy_probe",
        "window",
    ):
        phase_surface = phases.get(phase) or {}
        if phase_surface.get("begin") != "1" or phase_surface.get("end") != "1":
            return False
    return surface.get("enabled") == "1"


def summarize_arm(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not arm:
        return {}
    reboot = ((arm.get("live") or {}).get("reboot_cleanup") or {})
    return {
        "decision": arm.get("decision", ""),
        "pass": arm.get("pass"),
        "reason": arm.get("reason", ""),
        "next_step": arm.get("next_step", ""),
        "manifest": arm.get("manifest", ""),
        "rc": arm.get("rc"),
        "ok": arm.get("ok"),
        "counts": counts_for(arm),
        "markers": markers_for(arm),
        "peripheral": peripheral_for(arm),
        "property_shim": property_shim_for(arm),
        "registry_snapshot": registry_snapshot_for(arm),
        "focus": focus_for(arm),
        "provider_ready": provider_ready(peripheral_for(arm)),
        "property_ack_regressed": property_ack_regressed(property_shim_for(arm)),
        "registry_snapshot_complete": registry_snapshot_complete(registry_snapshot_for(arm)),
        "reboot_cleanup": {
            "version_seen": reboot.get("version_seen"),
            "status_healthy": reboot.get("status_healthy"),
            "wait_sec": reboot.get("wait_sec"),
        },
    }


def checks_for(prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> list[dict[str, Any]]:
    counts = counts_for(arm)
    markers = markers_for(arm)
    surface = peripheral_for(arm)
    property_surface = property_shim_for(arm)
    registry_surface = registry_snapshot_for(arm)
    registry_surface = registry_snapshot_for(arm)
    return [
        {
            "name": "current-boot-prep-ready",
            "status": "pass" if prep and prep.get("ready") else "blocked",
            "detail": {"ready": bool(prep and prep.get("ready"))},
            "next_step": "restore V641/V401/V490 current-boot prerequisites",
        },
        {
            "name": "service74-gate-positive",
            "status": "pass" if counts["service_notifier_180"] > 0 and counts["service_notifier_74"] > 0 else "blocked",
            "detail": {key: counts[key] for key in ("service_notifier_180", "service_notifier_74")},
            "next_step": "do not evaluate provider retry until service74 is positive",
        },
        {
            "name": "peripheral-provider-ready",
            "status": "pass" if provider_ready(surface) else "finding",
            "detail": {
                "per_mgr": surface.get("per_mgr"),
                "per_proxy": surface.get("per_proxy"),
                "enabled": surface.get("peripheral_manager_enabled"),
            },
            "next_step": "if not ready, inspect pm-service/pm-proxy child output and identity/runtime gap",
        },
        {
            "name": "peripheral-selinux-context-repair",
            "status": "pass" if not context_repair_regressed(surface) else "blocked",
            "detail": {
                "per_mgr": (surface.get("children") or {}).get("per_mgr"),
                "per_proxy": (surface.get("children") or {}).get("per_proxy"),
            },
            "next_step": "remove invalid per_mgr context mapping before runtime/linker classification",
        },
        {
            "name": "peripheral-property-exact-ack",
            "status": "pass" if not property_ack_regressed(property_surface) else "blocked",
            "detail": property_surface,
            "next_step": "fix exact private property ack before provider runtime classification",
        },
        {
            "name": "provider-registry-snapshot-complete",
            "status": "pass" if registry_snapshot_complete(registry_surface) else "blocked",
            "detail": registry_surface,
            "next_step": "fix registry snapshot phases before interpreting provider registration state",
        },
        {
            "name": "cnss-retry-observed",
            "status": "pass" if counts["cnss_daemon_netlink"] > 0 and counts["cnss_daemon_cld80211"] > 0 else "blocked",
            "detail": {key: counts[key] for key in ("cnss_daemon_netlink", "cnss_daemon_cld80211")},
            "next_step": "repair CNSS retry observation before WLFW routing",
        },
        {
            "name": "wlfw-bdf-wlan0-progression",
            "status": "pass" if wifi_advanced(counts, markers) else "finding",
            "detail": {"counts": counts, "markers": markers},
            "next_step": "if still absent, classify remaining pre-WLFW trigger before scan/connect",
        },
    ]


def decide(command: str, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v692-peripheral-manager-orchestrator-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v116, then run V692 orchestrated registry snapshot proof",
        )
    if not prep or not prep.get("ready"):
        return "v692-current-boot-prep-blocked", False, f"prep={prep}", "restore current-boot prerequisites before V692"
    if not arm or not arm.get("decision"):
        return "v692-arm-missing", False, "V692 arm did not produce a manifest", "inspect arm evidence"
    if "blocked" in str(arm.get("decision")):
        return "v692-arm-blocked", False, f"arm={summarize_arm(arm)}", "resolve V692 arm blocker before retry"
    counts = counts_for(arm)
    markers = markers_for(arm)
    surface = peripheral_for(arm)
    property_surface = property_shim_for(arm)
    registry_surface = registry_snapshot_for(arm)
    if context_repair_regressed(surface):
        return (
            "v692-context-repair-regressed",
            False,
            f"helper still forced invalid provider SELinux context; surface={surface}",
            "remove invalid per_mgr context mapping before another live attempt",
        )
    if property_ack_regressed(property_surface):
        return (
            "v692-peripheral-property-ack-regressed",
            False,
            f"property ack did not match exact private contract; property_surface={property_surface}",
            "fix exact private property shim ack before another provider/CNSS retry",
        )
    if not registry_snapshot_complete(registry_surface):
        return (
            "v692-provider-registry-snapshot-incomplete",
            False,
            f"registry_surface={registry_surface}",
            "fix helper registry capture before interpreting provider registration state",
        )
    if wifi_advanced(counts, markers):
        return (
            "v692-peripheral-manager-wifi-surface-advanced",
            True,
            f"WLFW/BDF/wlan0 progression marker moved; counts={counts} markers={markers} peripheral={surface}",
            "classify wlan0 readiness before any scan/connect or external ping",
        )
    if provider_ready(surface):
        return (
            "v692-provider-ready-no-wlfw-advance",
            True,
            f"provider ready and CNSS retry ran, but WLFW/BDF/wlan0 remain absent; counts={counts} peripheral={surface}",
            "classify remaining pre-WLFW trigger before Wi-Fi HAL or scan/connect",
        )
    return (
        "v692-provider-registration-snapshot-captured",
        True,
        f"PeripheralManager provider did not become fully ready; surface={surface}; registry_surface={registry_surface}",
        "inspect captured vndservicemanager/binder registry around provider start",
    )


def build_manifest(args: argparse.Namespace, prep: dict[str, Any] | None, arm: dict[str, Any] | None) -> dict[str, Any]:
    decision, pass_ok, reason, next_step = decide(args.command, prep, arm)
    checks = [] if args.command == "plan" else checks_for(prep, arm)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v692",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "prep_v692": prep or {},
        "arm_v692": summarize_arm(arm),
        "checks": checks,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "daemon_start_executed": args.command == "run",
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    arm = manifest["arm_v692"]
    rows: list[list[str]] = []
    for surface_name in ("counts", "markers", "peripheral", "property_shim", "registry_snapshot", "reboot_cleanup"):
        for key, value in (arm.get(surface_name) or {}).items():
            rows.append([surface_name, key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V692 PeripheralManager Registry Snapshot Orchestrator",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Runtime Surface",
        "",
        markdown_table(["surface", "key", "value"], rows) if rows else "- no runtime surface captured",
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    prep: dict[str, Any] | None = None
    arm: dict[str, Any] | None = None
    if args.command == "run":
        root = store.run_dir
        arm_root = root / "arm-v692-v116-peripheral-manager"
        prep = v673.prep_current_boot(args, store, "v692", arm_root)
        if prep.get("ready"):
            arm = v673.run_arm(
                args,
                store,
                "v692",
                V692_SCRIPT,
                V692_APPROVAL,
                arm_root / "live",
                Path(str(prep["v490"]["manifest"])),
            )
    manifest = build_manifest(args, prep, arm)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
