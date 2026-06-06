#!/usr/bin/env python3
"""V637 host-only service-74 post-CDSP classifier.

V636 proved that CDSP-online plus the V598 modem-holder/readback path still
reaches only service-notifier 180. This classifier compares Android V622,
V631, V635, and V636 to decide whether the next gate should keep targeting the
lower service-74 publisher path instead of Wi-Fi HAL, credentials, or external
connectivity.

It does not contact the device, write sysfs, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect/link-up, use credentials, run
DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v637-service74-post-cdsp-classifier")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V631_REPORT = Path("docs/reports/NATIVE_INIT_V631_PER_NODE_SIBLING_SSCTL_PROOF_LIVE_2026-05-23.md")
DEFAULT_V635_MANIFEST = Path("tmp/wifi/v635-cdsp-proof-20260523-052940/manifest.json")
DEFAULT_V636_MANIFEST = Path("tmp/wifi/v636-cdsp-v598-live-20260523-054728/manifest.json")

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("--v631-report", type=Path, default=DEFAULT_V631_REPORT)
    parser.add_argument("--v635-manifest", type=Path, default=DEFAULT_V635_MANIFEST)
    parser.add_argument("--v636-manifest", type=Path, default=DEFAULT_V636_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    text = read_text(path)
    if not text:
        return {"exists": False, "path": str(resolved)}
    data = json.loads(text)
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(resolved))
        return data
    return {"exists": True, "path": str(resolved), "value": data}


def int_count(mapping: dict[str, Any], key: str) -> int:
    try:
        return int(mapping.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def parse_v631(report: str) -> dict[str, Any]:
    return {
        "decision": "v631-cdsp-timeout-adsp-slpi-ok" if "v631-cdsp-timeout-adsp-slpi-ok" in report else "missing",
        "adsp_ok": "node adsp parent rc=0" in report or "| ADSP | `status=0x0` |" in report,
        "cdsp_timeout": "node cdsp parent rc=-110" in report or "| CDSP | `rc=-110`, reaped |" in report,
        "slpi_ok": "node slpi parent rc=0" in report or "| SLPI | `status=0x0` |" in report,
        "wifi_bringup_blocked": "No Wi-Fi HAL" in report and "external ping was executed" in report,
    }


def android_case(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    counts = summary.get("counts") or {}
    deltas = summary.get("deltas_ms") or {}
    sibling = all(int_count(counts, key) > 0 for key in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp"))
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "counts": counts,
        "deltas_ms": deltas,
        "has_all_sibling_sysmon": sibling,
        "has_service74": int_count(counts, "service_notifier_74") > 0,
        "has_wlan_path": any(int_count(counts, key) > 0 for key in ("wlan_pd", "qmi_server_connected", "wlan_fw_ready", "wlan0")),
    }


def v635_case(manifest: dict[str, Any]) -> dict[str, Any]:
    proof = manifest.get("proof") or {}
    delta = proof.get("marker_delta") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "cdsp_returned": bool(proof.get("cdsp_returned")),
        "cdsp_online": "ONLINE" in str(proof.get("cdsp_state_after") or ""),
        "cdsp_power_ready": int_count(delta, "cdsp_power_clock") > 0,
        "sysmon_cdsp": int_count(delta, "sysmon_cdsp"),
        "service74": int_count(delta, "service_notifier_74"),
        "wlan_pd": int_count(delta, "wlan_pd"),
        "pm_qos_warning": int_count(delta, "pm_qos_warning"),
        "direct_firmware_fail": int_count(delta, "direct_firmware_fail"),
    }


def v636_case(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    cdsp_proof = live.get("cdsp_proof") or {}
    cdsp_delta = cdsp_proof.get("marker_delta") or {}
    post = live.get("post_cdsp_markers") or {}
    v598_live = live.get("v598_live") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "cdsp_returned": bool(cdsp_proof.get("cdsp_returned")),
        "cdsp_power_ready": int_count(cdsp_delta, "cdsp_power_clock") > 0,
        "sysmon_cdsp": int_count(cdsp_delta, "sysmon_cdsp"),
        "service180": int_count(post, "service_notifier_180"),
        "service74": int_count(post, "service_notifier_74"),
        "wlan_pd": int_count(post, "wlan_pd"),
        "qmi_server_connected": int_count(post, "qmi_server_connected"),
        "wlan0": int_count(post, "wlan0"),
        "kernel_warning": int_count(post, "kernel_warning"),
        "mdm3_after_companion": v598_live.get("mdm3_after_companion"),
        "mss_after_companion": v598_live.get("mss_after_companion"),
        "wifi_bringup_executed": manifest.get("wifi_bringup_executed"),
        "external_ping_executed": manifest.get("external_ping_executed"),
    }


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    android = manifest["android_v622"]
    v631 = manifest["v631"]
    v635 = manifest["v635"]
    v636 = manifest["v636"]
    return [
        [
            "Android V622",
            "service 74 follows sibling sysmon",
            (
                f"sibling_sysmon={bool_text(android['has_all_sibling_sysmon'])}; "
                f"service74={android['counts'].get('service_notifier_74', 0)}; "
                f"180->74={android['deltas_ms'].get('service_notifier_180_to_service_notifier_74')}ms"
            ),
            "service 74 remains the lower publisher target before HAL/connect",
        ],
        [
            "V631 per-node sibling proof",
            "ADSP/SLPI returned; CDSP needed firmware surface",
            f"adsp_ok={v631['adsp_ok']} cdsp_timeout={v631['cdsp_timeout']} slpi_ok={v631['slpi_ok']}",
            "CDSP timeout was an active blocker before V634/V635 firmware mount parity",
        ],
        [
            "V635 firmware CDSP-only proof",
            "CDSP loader fixed, no QMI sysmon",
            (
                f"returned={v635['cdsp_returned']} online={v635['cdsp_online']} "
                f"power_ready={v635['cdsp_power_ready']} sysmon_cdsp={v635['sysmon_cdsp']} "
                f"service74={v635['service74']} warnings={v635['pm_qos_warning']}"
            ),
            "CDSP power/ONLINE is not equivalent to Android CDSP SSCTL sysmon publication",
        ],
        [
            "V636 CDSP + V598 composite",
            "service 180 only",
            (
                f"service180={v636['service180']} service74={v636['service74']} "
                f"wlan_pd={v636['wlan_pd']} wlan0={v636['wlan0']} warnings={v636['kernel_warning']}"
            ),
            "adding CDSP-online does not unblock service 74/WLAN-PD",
        ],
        [
            "HAL/connect/credentials",
            "still blocked",
            (
                f"wifi_bringup={v636['wifi_bringup_executed']} "
                f"external_ping={v636['external_ping_executed']} "
                f"android_wlan_path={bool_text(android['has_wlan_path'])}"
            ),
            "do not use credentials or external ping until service 74/WLAN-PD/WLFW advances",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    android = manifest["android_v622"]
    v631 = manifest["v631"]
    v635 = manifest["v635"]
    v636 = manifest["v636"]
    android_ready = android["has_all_sibling_sysmon"] and android["has_service74"] and android["has_wlan_path"]
    cdsp_loader_fixed = (
        v631["cdsp_timeout"]
        and v635["cdsp_returned"]
        and v635["cdsp_online"]
        and v635["pm_qos_warning"] == 0
        and v635["direct_firmware_fail"] == 0
    )
    cdsp_not_qmi_ready = v635["sysmon_cdsp"] == 0 and v636["sysmon_cdsp"] == 0
    service180_only_clean = (
        v636["service180"] > 0
        and v636["service74"] == 0
        and v636["wlan_pd"] == 0
        and v636["kernel_warning"] == 0
    )
    if android_ready and cdsp_loader_fixed and cdsp_not_qmi_ready and service180_only_clean:
        return (
            "v637-service74-needs-sibling-sysmon-not-cdsp-power",
            True,
            (
                "Android service 74 appears with sibling SSCTL sysmon, while V635/V636 prove "
                "CDSP power/ONLINE plus the V598 service-180 path still does not create CDSP sysmon, "
                "service 74, WLAN-PD, WLFW, or wlan0."
            ),
            "V638 should plan a firmware-backed per-node sibling SSCTL composite observer before any HAL/connect attempt",
        )
    return (
        "v637-service74-post-cdsp-evidence-gap",
        False,
        (
            f"android_ready={android_ready} cdsp_loader_fixed={cdsp_loader_fixed} "
            f"cdsp_not_qmi_ready={cdsp_not_qmi_ready} service180_only_clean={service180_only_clean}"
        ),
        "refresh V622/V631/V635/V636 evidence before another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "android_v622_manifest": str(repo_path(args.android_v622_manifest)),
            "v631_report": str(repo_path(args.v631_report)),
            "v635_manifest": str(repo_path(args.v635_manifest)),
            "v636_manifest": str(repo_path(args.v636_manifest)),
        },
        "android_v622": android_case(load_json(args.android_v622_manifest)),
        "v631": parse_v631(read_text(args.v631_report)),
        "v635": v635_case(load_json(args.v635_manifest)),
        "v636": v636_case(load_json(args.v636_manifest)),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
    }
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v637-service74-post-cdsp-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V637 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "evidence_rows": evidence_rows(manifest),
    })
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android_v622"]
    return "\n".join([
        "# V637 Service-74 Post-CDSP Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Android Timing",
        "",
        markdown_table(
            ["delta", "ms"],
            [
                ["sysmon_modem_to_sysmon_slpi", str(android["deltas_ms"].get("sysmon_modem_to_sysmon_slpi"))],
                ["sysmon_modem_to_sysmon_cdsp", str(android["deltas_ms"].get("sysmon_modem_to_sysmon_cdsp"))],
                ["sysmon_modem_to_sysmon_adsp", str(android["deltas_ms"].get("sysmon_modem_to_sysmon_adsp"))],
                ["sysmon_modem_to_service_notifier_180", str(android["deltas_ms"].get("sysmon_modem_to_service_notifier_180"))],
                ["service_notifier_180_to_service_notifier_74", str(android["deltas_ms"].get("service_notifier_180_to_service_notifier_74"))],
                ["service_notifier_180_to_wlan_pd", str(android["deltas_ms"].get("service_notifier_180_to_wlan_pd"))],
                ["service_notifier_180_to_wlfw_start", str(android["deltas_ms"].get("service_notifier_180_to_wlfw_start"))],
            ],
        ),
        "",
        "## Inputs",
        "",
        markdown_table(["name", "path"], [[key, value] for key, value in manifest["inputs"].items()]),
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
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
