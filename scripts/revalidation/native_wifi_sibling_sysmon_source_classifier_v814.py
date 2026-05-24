#!/usr/bin/env python3
"""V814 host-only sibling sysmon/service publication source classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v814-sibling-sysmon-source-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v814-sibling-sysmon-source-classifier.txt")
DEFAULT_V813_MANIFEST = Path("tmp/wifi/v813-post-sysmon-publication-classifier/manifest.json")
DEFAULT_SOURCE_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")

SOURCE_TARGETS = {
    "service_notifier": Path("drivers/soc/qcom/service-notifier.c"),
    "service_notifier_header": Path("include/soc/qcom/service-notifier.h"),
    "sysmon_qmi": Path("drivers/soc/qcom/sysmon-qmi.c"),
    "sysmon_legacy": Path("drivers/soc/qcom/sysmon.c"),
    "subsystem_restart": Path("drivers/soc/qcom/subsystem_restart.c"),
    "sysmon_header": Path("include/soc/qcom/sysmon.h"),
    "esoc_client_header": Path("include/linux/esoc_client.h"),
}

ANCHORS = {
    "service_notifier": (
        "service_notifier_new_server",
        "send_notif_listener_msg_req",
        "root_service_service_ind_cb",
        "service_notif_register_notifier",
        "qmi_add_lookup",
        "subsys_notif_register_notifier",
    ),
    "service_notifier_header": (
        "SERVREG_NOTIF_SERVICE_STATE_UP_V01",
        "service_notif_register_notifier",
    ),
    "sysmon_qmi": (
        "sysmon_notifier_register",
        "qmi_add_lookup",
        "SSCTL_SERVICE_ID",
        "sysmon_send_event",
        "ssctl_new_server",
    ),
    "sysmon_legacy": (
        "sysmon_send_event_no_qmi",
        "sysmon_probe",
        "subsys_initcall",
    ),
    "subsystem_restart": (
        "send_sysmon_notif",
        "sysmon_send_event",
        "qcom,sysmon-id",
        "sysmon_notifier_register",
        "sysmon_glink_register",
    ),
    "sysmon_header": (
        "sysmon_send_event",
        "sysmon_notifier_register",
        "sysmon_glink_register",
    ),
    "esoc_client_header": (
        "esoc_register_client_notifier",
        "esoc_register_client_hook",
    ),
}

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash, boot image write, or partition write",
    "reboot or bootloader handoff",
    "Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "boot_wlan, qcwlanstate, esoc0, bind/unbind, driver override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v813-manifest", type=Path, default=DEFAULT_V813_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return {"file": info, "data": {}}
    info.update({"is_file": True, "size": resolved.stat().st_size})
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": payload if isinstance(payload, dict) else {}}


def scan_anchors(source_root: Path) -> dict[str, Any]:
    root = resolve(source_root)
    result: dict[str, Any] = {
        "source_root": str(root),
        "source_root_exists": root.exists(),
        "targets": {},
    }
    for label, relative in SOURCE_TARGETS.items():
        path = root / relative
        target: dict[str, Any] = {
            "path": str(path),
            "exists": path.exists(),
            "anchors": {},
        }
        if path.exists() and path.is_file():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            for anchor in ANCHORS[label]:
                hits = [
                    {"line": index + 1, "text": line.strip()[:180]}
                    for index, line in enumerate(lines)
                    if anchor in line
                ][:12]
                target["anchors"][anchor] = hits
        result["targets"][label] = target
    return result


def anchors_present(scan: dict[str, Any], label: str, anchors: tuple[str, ...]) -> bool:
    target = scan.get("targets", {}).get(label, {})
    if not target.get("exists"):
        return False
    target_anchors = target.get("anchors", {})
    return all(bool(target_anchors.get(anchor)) for anchor in anchors)


def build_checks(command: str, v813: dict[str, Any], scan: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only source classifier plan; no device command executed",
            "next_step": "run source classifier",
        }]
    targets = scan.get("targets", {})
    all_targets_exist = scan.get("source_root_exists") and all(
        target.get("exists") for target in targets.values()
    )
    v813_ready = (
        v813.get("pass") is True
        and v813.get("decision") == "v813-sibling-sysmon-service-publication-precondition-selected"
    )
    service_notifier_path = anchors_present(
        scan,
        "service_notifier",
        ("service_notifier_new_server", "send_notif_listener_msg_req", "root_service_service_ind_cb", "qmi_add_lookup"),
    )
    service_notifier_state = anchors_present(
        scan,
        "service_notifier_header",
        ("SERVREG_NOTIF_SERVICE_STATE_UP_V01", "service_notif_register_notifier"),
    )
    sysmon_qmi_path = anchors_present(
        scan,
        "sysmon_qmi",
        ("sysmon_notifier_register", "qmi_add_lookup", "SSCTL_SERVICE_ID", "sysmon_send_event"),
    )
    subsystem_registers_sysmon = anchors_present(
        scan,
        "subsystem_restart",
        ("send_sysmon_notif", "sysmon_send_event", "qcom,sysmon-id", "sysmon_notifier_register"),
    )
    esoc_hooks_exist = anchors_present(
        scan,
        "esoc_client_header",
        ("esoc_register_client_notifier", "esoc_register_client_hook"),
    )
    return [
        {
            "name": "v813-route-ready",
            "status": "pass" if v813_ready else "blocked",
            "detail": {"decision": v813.get("decision"), "pass": v813.get("pass")},
            "next_step": "complete V813 before source routing",
        },
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no device command, flash, reboot, HAL, scan/connect, credential use, DHCP, route, or ping",
            "next_step": "preserve V814 as source classifier only",
        },
        {
            "name": "source-targets-present",
            "status": "pass" if all_targets_exist else "blocked",
            "detail": {name: target.get("exists") for name, target in targets.items()},
            "next_step": "stage Samsung OSRC source before classifying source route",
        },
        {
            "name": "servreg-service-notifier-path",
            "status": "pass" if service_notifier_path and service_notifier_state else "blocked",
            "detail": {
                "service_notifier_path": service_notifier_path,
                "service_state_header": service_notifier_state,
            },
            "next_step": "if absent, do not infer service74/WLAN-PD from service-notifier source",
        },
        {
            "name": "sysmon-qmi-registration-path",
            "status": "pass" if sysmon_qmi_path else "blocked",
            "detail": {"sysmon_qmi_path": sysmon_qmi_path},
            "next_step": "if absent, inspect legacy sysmon/glink route before live work",
        },
        {
            "name": "subsystem-sysmon-registration-path",
            "status": "pass" if subsystem_registers_sysmon else "blocked",
            "detail": {"subsystem_registers_sysmon": subsystem_registers_sysmon},
            "next_step": "if absent, inspect subsystem_restart registration before live work",
        },
        {
            "name": "esoc-client-surface-exists",
            "status": "pass" if esoc_hooks_exist else "warn",
            "detail": {"esoc_hooks_exist": esoc_hooks_exist},
            "next_step": "treat esoc as read-only surface unless a separate safe contract is proven",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v814-sibling-sysmon-source-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only source classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v814-sibling-sysmon-source-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore source/evidence before selecting live gate",
        )
    return (
        "v814-source-routes-to-subsystem-sysmon-registration-snapshot",
        True,
        "OSRC source maps service-notifier to SERVREG QMI listener registration and sysmon to subsystem registration/QMI lookup; V813 gap should be isolated at subsystem sysmon/service-publication state, not userspace HAL/connect",
        "V815 should collect a read-only subsystem/sysmon/service-locator registration snapshot on stock v724 before any new trigger",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v813_entry = load_json(args.v813_manifest)
    v813 = v813_entry["data"]
    scan = scan_anchors(args.source_root)
    checks = build_checks(args.command, v813, scan)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v814",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v813_manifest": {
                "path": v813_entry["file"]["path"],
                "exists": v813_entry["file"]["exists"],
                "decision": v813.get("decision", ""),
                "pass": bool(v813.get("pass")),
            },
            "source_root": scan["source_root"],
        },
        "source_scan": scan,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
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
    source_rows = []
    for label, target in manifest["source_scan"]["targets"].items():
        anchors = target.get("anchors", {})
        present = [name for name, hits in anchors.items() if hits]
        source_rows.append([label, str(target.get("exists")), ", ".join(present), target.get("path", "")])
    return "\n".join([
        "# V814 Sibling Sysmon Source Classifier",
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
        "## Source Targets",
        "",
        markdown_table(["target", "exists", "anchors", "path"], source_rows),
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
