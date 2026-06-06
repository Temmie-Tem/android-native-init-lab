#!/usr/bin/env python3
"""V738 bounded modem/WLAN/MHI prerequisite observer.

This runner reuses the V735 safe live observer but reclassifies the result with
the V737 SM8250 CNSS2/PCIe routing model. It stays below service-manager,
Wi-Fi HAL, scan/connect, credential use, DHCP, route changes, and external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_current_cnss_only_observer_v735 as observer
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v738-modem-wlan-mhi-observer")
DEFAULT_V737_MANIFEST = Path("tmp/wifi/v737-cnss2-arch-rebase/manifest.json")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v738-v490-current-run/manifest.json")
PROOF_PREFIX = "/tmp/a90-v738-"
LATEST_POINTER = Path("tmp/wifi/latest-v738-modem-wlan-mhi-observer.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=observer.base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=observer.base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=observer.base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=observer.base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=observer.base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=observer.base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=observer.base.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=observer.base.DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=observer.base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=observer.base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=observer.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=observer.base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=observer.base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=observer.base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=observer.base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=observer.DEFAULT_V734_MANIFEST)
    parser.add_argument("--v737-manifest", type=Path, default=DEFAULT_V737_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def configure_observer() -> None:
    observer.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    observer.DEFAULT_V490_MANIFEST = DEFAULT_V490_MANIFEST
    observer.PROOF_PREFIX = PROOF_PREFIX
    observer.configure_base()


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = observer.base.repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(resolved))
        return data
    return {"exists": True, "path": str(resolved), "invalid": "not-object"}


def int_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return 0


def key_int(keys: dict[str, Any], name: str) -> int:
    return int_value(keys.get(name))


def key_bool(keys: dict[str, Any], name: str) -> bool:
    return key_int(keys, name) > 0


def helper_keys(base_manifest: dict[str, Any]) -> dict[str, Any]:
    helper = ((base_manifest.get("live") or {}).get("helper_result") or {})
    keys = helper.get("keys") or {}
    return keys if isinstance(keys, dict) else {}


def check_detail(base_manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in base_manifest.get("checks", []):
        if check.get("name") == name:
            detail = check.get("detail")
            return detail if isinstance(detail, dict) else {}
    return {}


def mhi_surface(base_manifest: dict[str, Any]) -> dict[str, Any]:
    keys = helper_keys(base_manifest)
    live = base_manifest.get("live") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    return {
        "icnss_driver_link": key_bool(keys, "wifi_icnss_edge.window.icnss_driver_link.exists"),
        "qca6390_device_captured": key_bool(keys, "wifi_companion_start.cnss2_focus_window.qca6390_device_captured"),
        "qca6390_driver_link": key_bool(keys, "wifi_icnss_edge.window.qca6390_driver_link.exists"),
        "mhi_devices_count": key_int(keys, "A90_EXECNS_DIR_wifi_icnss_edge_window_mhi_devices_END count"),
        "pci_devices_count": key_int(keys, "A90_EXECNS_DIR_wifi_icnss_edge_window_pci_devices_END count"),
        "wlan0_netdev": key_bool(keys, "wifi_icnss_edge.window.wlan0_netdev.exists"),
        "wlan_params_captured": key_bool(keys, "wifi_companion_start.icnss_edge_window.wlan_params_captured"),
        "qca6390_power_captured": key_bool(keys, "wifi_companion_start.icnss_edge_window.qca6390_power_captured"),
        "rpmsg_devices_captured": key_bool(keys, "wifi_companion_start.icnss_edge_window.rpmsg_devices_captured"),
        "markers": {name: int_value(markers.get(name)) for name in ("mhi", "qca6390", "wlfw", "bdf", "wlan0", "wlan_pd", "kernel_warning")},
    }


def lower_state(base_manifest: dict[str, Any]) -> dict[str, Any]:
    live = base_manifest.get("live") or {}
    return {
        "mss_before": live.get("mss_before", ""),
        "mss_after_holder": live.get("mss_after_holder", ""),
        "mss_after_companion": live.get("mss_after_companion", ""),
        "mdm3_before": live.get("mdm3_before", ""),
        "mdm3_after_holder": live.get("mdm3_after_holder", ""),
        "mdm3_after_companion": live.get("mdm3_after_companion", ""),
        "qrtr_rx_seen": bool((live.get("qrtr_rx_wait") or {}).get("seen")),
        "qrtr_services": live.get("qrtr_services_after_companion") or {},
        "qrtr_readback": live.get("qrtr_readback") or {},
    }


def v735_success(base_manifest: dict[str, Any]) -> bool:
    return bool(base_manifest.get("pass")) and str(base_manifest.get("decision", "")).startswith("v735-")


def build_checks(args: argparse.Namespace,
                 v737: dict[str, Any],
                 base_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "bounded live observer plan; no device command executed",
            "next_step": "refresh V401/V490 on current boot, then run V738",
        }]
    lower = lower_state(base_manifest)
    surface = mhi_surface(base_manifest)
    wlan_surface = check_detail(base_manifest, "wlan-static-surface")
    helper_contract = check_detail(base_manifest, "cnss-only-contract")
    forbidden = check_detail(base_manifest, "forbidden-helper-actions")
    readback = lower.get("qrtr_readback") or {}
    markers = surface.get("markers") or {}
    return [
        {
            "name": "v737-routing-reference",
            "status": "pass" if v737.get("decision") == "v737-route-to-modem-wlan-mhi-prereq-observer" and v737.get("pass") is True else "blocked",
            "detail": {"decision": v737.get("decision"), "pass": v737.get("pass"), "path": v737.get("path")},
            "next_step": "rerun V737 if architecture routing evidence is missing",
        },
        {
            "name": "base-observer-completed",
            "status": "pass" if v735_success(base_manifest) else "blocked",
            "detail": {"decision": base_manifest.get("decision"), "pass": base_manifest.get("pass"), "reason": base_manifest.get("reason")},
            "next_step": "inspect V735-compatible base observer blockers before widening scope",
        },
        {
            "name": "below-hal-connect-contract",
            "status": "pass" if not base_manifest.get("service_manager_start_executed") and not base_manifest.get("wifi_hal_start_executed") and not base_manifest.get("scan_connect_executed") and not base_manifest.get("external_ping_executed") and int_value(readback.get("qmi_attempted")) == 0 else "blocked",
            "detail": {
                "helper_contract": helper_contract,
                "forbidden": forbidden,
                "qmi_attempted": readback.get("qmi_attempted"),
            },
            "next_step": "discard V738 if it crossed HAL/connect or sent a QMI payload",
        },
        {
            "name": "static-wlan-surface-retained",
            "status": "pass" if wlan_surface.get("sys_module_wlan_exists") and not wlan_surface.get("proc_modules_has_wlan") else "review",
            "detail": wlan_surface,
            "next_step": "do not assume a missing loadable wlan.ko without stronger Android evidence",
        },
        {
            "name": "mss-online-mdm3-not-continuing",
            "status": "finding" if "ONLINE" in {lower.get("mss_after_holder"), lower.get("mss_after_companion")} and "ONLINE" not in {lower.get("mdm3_after_holder"), lower.get("mdm3_after_companion")} else "review",
            "detail": lower,
            "next_step": "compare Android lower state trigger for mdm3/WLAN-PD continuation before HAL/connect",
        },
        {
            "name": "mhi-wlfw-surface",
            "status": "finding" if not surface.get("qca6390_driver_link") and int_value(surface.get("mhi_devices_count")) == 0 and int_value(surface.get("pci_devices_count")) == 0 and int_value(markers.get("wlfw")) == 0 and int_value(readback.get("service_events")) == 0 else "pass",
            "detail": surface,
            "next_step": "if still absent, route to lower MDM3/WLAN-PD/MHI trigger analysis; if present, capture WLFW/BDF before HAL/connect",
        },
        {
            "name": "postflight-cleanup",
            "status": "pass" if (base_manifest.get("live") or {}).get("reboot_cleanup", {}).get("status_healthy") else "blocked",
            "detail": (base_manifest.get("live") or {}).get("reboot_cleanup") or {},
            "next_step": "manually verify native health if cleanup did not prove it",
        },
    ]


def decide(args: argparse.Namespace,
           checks: list[dict[str, Any]],
           base_manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v738-modem-wlan-mhi-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh V401/V490 and run bounded V738 live observer",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v738-modem-wlan-mhi-observer-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear blocker before retry",
        )
    lower = lower_state(base_manifest)
    surface = mhi_surface(base_manifest)
    readback = lower.get("qrtr_readback") or {}
    markers = surface.get("markers") or {}
    if int_value(markers.get("wlan0")) or surface.get("wlan0_netdev"):
        return (
            "v738-wlan0-appeared-below-hal",
            True,
            "wlan0 appeared without HAL/connect",
            "capture interface state and only then plan guarded connect",
        )
    if int_value(markers.get("wlfw")) or int_value(readback.get("service_events")):
        return (
            "v738-wlfw-service69-appeared-below-hal",
            True,
            "WLFW/service69 appeared without HAL/connect",
            "capture BDF/fw-ready/interface state before any connect attempt",
        )
    if surface.get("qca6390_driver_link") or int_value(surface.get("mhi_devices_count")) or int_value(surface.get("pci_devices_count")):
        return (
            "v738-mhi-qca-transition-appeared",
            True,
            "QCA/MHI/PCI transition appeared but WLFW/wlan0 did not",
            "classify MHI-to-WLFW firmware/runtime edge before HAL/connect",
        )
    if "ONLINE" in {lower.get("mss_after_holder"), lower.get("mss_after_companion")} and "ONLINE" not in {lower.get("mdm3_after_holder"), lower.get("mdm3_after_companion")}:
        return (
            "v738-mss-online-mdm3-wlan-mhi-gap-classified",
            True,
            "mss reaches ONLINE but mdm3/WLAN-PD/MHI/WLFW do not continue under the safe vendor/CNSS-only window",
            "plan V739 around Android/native mdm3 and WLAN-PD lower trigger delta below HAL/connect",
        )
    return (
        "v738-modem-wlan-mhi-prereq-review",
        True,
        "observer completed but did not match the expected lower-state pattern",
        "inspect V738 manifest before selecting the next live gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    summary_rows = [
        ["v737", json.dumps(manifest.get("v737_reference", {}), sort_keys=True)],
        ["base_observer", json.dumps(manifest.get("base_observer", {}), sort_keys=True)],
        ["lower_state", json.dumps(manifest.get("lower_state", {}), sort_keys=True)],
        ["mhi_surface", json.dumps(manifest.get("mhi_surface", {}), sort_keys=True)],
    ]
    return "\n".join([
        "# V738 Modem/WLAN/MHI Prerequisite Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        observer.base.markdown_table(["name", "status", "detail", "next"], checks),
        "",
        "## Summary",
        "",
        observer.base.markdown_table(["item", "value"], summary_rows),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v737 = load_json_if_exists(args.v737_manifest)
    if args.command == "run":
        base_manifest = observer.build_manifest(args, store)
    else:
        base_manifest = {
            "decision": "v735-compatible-observer-plan-only",
            "pass": True,
            "reason": "plan-only",
            "next_step": "run bounded live observer",
            "checks": [],
            "live": {},
            "device_commands_executed": False,
            "service_manager_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "external_ping_executed": False,
        }
    checks = build_checks(args, v737, base_manifest)
    decision, pass_ok, reason, next_step = decide(args, checks, base_manifest)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v738",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": observer.base.collect_host_metadata(),
        "v737_reference": {"decision": v737.get("decision"), "pass": v737.get("pass"), "path": v737.get("path")},
        "base_observer": {
            "decision": base_manifest.get("decision"),
            "pass": base_manifest.get("pass"),
            "reason": base_manifest.get("reason"),
            "next_step": base_manifest.get("next_step"),
        },
        "lower_state": lower_state(base_manifest),
        "mhi_surface": mhi_surface(base_manifest),
        "checks": checks,
        "base_manifest": base_manifest,
        "device_commands_executed": bool(base_manifest.get("device_commands_executed")),
        "firmware_mounts_executed": bool(base_manifest.get("firmware_mounts_executed")),
        "subsys_modem_open_attempted": bool(base_manifest.get("subsys_modem_open_attempted")),
        "subsys_modem_opened": bool(base_manifest.get("subsys_modem_opened")),
        "esoc0_node_created": False,
        "esoc0_open_executed": False,
        "subsystem_writes_executed": False,
        "module_load_unload_executed": False,
        "lower_companion_start_executed": bool(base_manifest.get("lower_companion_start_executed")),
        "cnss_diag_start_executed": bool(base_manifest.get("cnss_diag_start_executed")),
        "cnss_daemon_start_executed": bool(base_manifest.get("cnss_daemon_start_executed")),
        "daemon_or_hal_start_executed": bool(base_manifest.get("cnss_daemon_start_executed")),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "reboot_cleanup_executed": bool(base_manifest.get("reboot_cleanup_executed")),
    }


def main() -> int:
    configure_observer()
    args = parse_args()
    store = EvidenceStore(observer.base.repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(observer.base.repo_path(LATEST_POINTER), str(store.run_dir.relative_to(observer.base.repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"subsys_modem_opened: {manifest['subsys_modem_opened']}")
    print(f"lower_companion_start_executed: {manifest['lower_companion_start_executed']}")
    print(f"cnss_diag_start_executed: {manifest['cnss_diag_start_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
