#!/usr/bin/env python3
"""V1763 host-only reconciliation for the WLAN-PD firmware-request gate.

The active user directive is to stop route-minimization/tracefs-plumbing and use
the Android-good firmware-request gate that V1739 was intended to run.  This
classifier verifies that the equivalent gate is already closed by V1753:

* Android-good captured tftp_server/rmt_storage requests for wlanmdsp.mbn.
* The native V1736 service-manager route reached the WLFW worker with tftp_server
  running, but never requested wlanmdsp.mbn.
* The fixed redirect label is therefore firmware-not-requested.

No device contact or live mutation is performed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_CONTRACT = REPO_ROOT / "docs" / "reports" / "WLAN_PD_REDIRECT_AND_FIRMWARE_SERVE_GATE_2026-06-02.md"
DEFAULT_ANDROID = REPO_ROOT / "tmp" / "wifi" / "v1753-android-good-wlan-pd-firmware-request" / "manifest.json"
DEFAULT_DIFF = REPO_ROOT / "tmp" / "wifi" / "v1753-wlan-pd-firmware-request-diff" / "manifest.json"
DEFAULT_NATIVE = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_V1761 = REPO_ROOT / "tmp" / "wifi" / "v1761-wlan-pd-autoload-trigger-contract-classifier" / "manifest.json"
DEFAULT_V1762 = REPO_ROOT / "tmp" / "wifi" / "v1762-wlan-pd-helper-contract-gap-classifier" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1763-wlan-pd-firmware-request-gate-reconciliation"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1763_WLAN_PD_FIRMWARE_REQUEST_GATE_RECONCILIATION_2026-06-03.md"
)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    payload = load_json(path)
    return {
        "present": True,
        "path": display_path(path),
        "decision": payload.get("decision"),
        "pass": bool(payload.get("pass")),
        "label": payload.get("label"),
        "reason": payload.get("reason"),
    }


def contract_summary(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return {
        "path": display_path(path),
        "present": True,
        "redirect_to_internal_modem": "INTERNAL modem" in text and "wlan0" in text,
        "one_run_label_rule": "ONE run sets the label" in text,
        "forbids_esoc_rc1": "/dev/subsys_esoc0" in text and "forced RC1" in text,
        "fixed_labels_present": all(
            label in text
            for label in (
                "firmware-not-requested",
                "firmware-requested-but-absent-at-served-path",
                "firmware-served-pd-still-uninit",
                "tqftpserv-not-running",
            )
        ),
    }


def android_summary(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    analysis = ((manifest.get("context") or {}).get("analysis") or {})
    return {
        "path": display_path(path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "requested_wlanmdsp": str(analysis.get("requested_wlanmdsp", "0")),
        "requested_pd_image": str(analysis.get("requested_pd_image", "0")),
        "request_summary": analysis.get("request_summary") or {},
        "trace_lines": analysis.get("trace_lines") or {},
        "served_path_candidates": analysis.get("served_path_candidates") or [],
        "rollback_base_decision": manifest.get("base_decision"),
        "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
        "credential_use_executed": bool(manifest.get("credential_use_executed")),
        "dhcp_route_executed": bool(manifest.get("dhcp_route_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
        "pmic_gpio_gdsc_write_executed": bool(manifest.get("pmic_gpio_gdsc_write_executed")),
        "global_pci_rescan_executed": bool(manifest.get("global_pci_rescan_executed")),
        "platform_bind_unbind_executed": bool(manifest.get("platform_bind_unbind_executed")),
    }


def diff_summary(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    android = manifest.get("android") or {}
    native = manifest.get("native") or {}
    return {
        "path": display_path(path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "label": manifest.get("label"),
        "reason": manifest.get("reason"),
        "android_requested_wlanmdsp": android.get("requested_wlanmdsp"),
        "android_wlanmdsp_line_count": android.get("wlanmdsp_line_count"),
        "android_wlanmdsp_paths": android.get("wlanmdsp_paths") or [],
        "native_decision": native.get("decision"),
        "native_pass": bool(native.get("pass")),
        "native_tftp_running": native.get("tftp_running"),
        "native_service_manager": native.get("service_manager"),
        "native_wlfw_start_hit_count": native.get("wlfw_start_hit_count"),
        "native_wlfw_service_request_hit_count": native.get("wlfw_service_request_hit_count"),
        "native_wlfw_worker_create_success_hit_count": native.get("wlfw_worker_create_success_hit_count"),
        "native_wlfw_service69_seen": native.get("wlfw_service69_seen"),
        "native_requested_wlanmdsp": native.get("requested_wlanmdsp"),
        "native_firmware_label": native.get("old_firmware_serve_label"),
        "fresh_native_attempt": manifest.get("fresh_native_attempt") or {},
    }


def native_summary(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    gate = manifest.get("gate") or {}
    return {
        "path": display_path(path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "service_window_label": gate.get("service_window_label"),
        "old_firmware_serve_label": gate.get("old_firmware_serve_label"),
        "service_manager": gate.get("service_manager"),
        "tftp_running": gate.get("tftp_running"),
        "wlfw_start_hit_count": gate.get("wlfw_start_hit_count"),
        "wlfw_service_request_hit_count": gate.get("wlfw_service_request_hit_count"),
        "wlfw_worker_create_success_hit_count": gate.get("wlfw_worker_create_success_hit_count"),
        "wlfw_service69_seen": gate.get("wlfw_service69_seen"),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp"),
        "no_esoc0": gate.get("no_esoc0"),
        "no_forced_rc1": gate.get("no_forced_rc1"),
        "no_fake_online": gate.get("no_fake_online"),
        "no_scan_connect": gate.get("no_scan_connect"),
        "no_credentials": gate.get("no_credentials"),
        "no_dhcp_routes": gate.get("no_dhcp_routes"),
        "no_external_ping": gate.get("no_external_ping"),
    }


def classify(contract: dict[str, Any], android: dict[str, Any], native: dict[str, Any], diff: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not all(contract.get(key) for key in ("redirect_to_internal_modem", "one_run_label_rule", "forbids_esoc_rc1", "fixed_labels_present")):
        return (
            "v1763-redirect-contract-missing",
            False,
            "WLAN-PD redirect contract is missing required stop/gate clauses",
            "contract-missing",
        )
    if not android.get("pass") or intish(android.get("requested_wlanmdsp")) <= 0:
        return (
            "v1763-android-good-request-evidence-missing",
            False,
            "Android-good evidence does not prove a wlanmdsp request",
            "android-good-request-missing",
        )
    if not native.get("pass") or intish(native.get("wlfw_start_hit_count")) <= 0 or intish(native.get("wlfw_service_request_hit_count")) <= 0:
        return (
            "v1763-native-sm-route-baseline-missing",
            False,
            "native V1736 service-manager route does not prove WLFW worker reachability",
            "native-baseline-missing",
        )
    if not diff.get("pass") or diff.get("label") != "firmware-not-requested":
        return (
            "v1763-existing-diff-label-mismatch",
            False,
            f"existing V1753 diff label is {diff.get('label')!r}",
            "diff-label-mismatch",
        )
    if intish(native.get("requested_wlanmdsp")) != 0 or intish(native.get("wlfw_service69_seen")) != 0:
        return (
            "v1763-native-progress-invalidates-fixed-label",
            False,
            "native baseline has progressed beyond no-request/no-service69",
            "native-label-invalidated",
        )
    return (
        "v1763-v1739-equivalent-firmware-request-gate-closed-host-pass",
        True,
        "V1753 already ran the V1739-equivalent Android-good/native firmware-request gate; the fixed label is firmware-not-requested",
        "firmware-not-requested",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["native_v1736"]
    diff = result["v1753_diff"]
    superseded = result["superseded_followups"]
    return "\n".join(
        [
            "# Native Init V1763 WLAN-PD Firmware-request Gate Reconciliation",
            "",
            "## Summary",
            "",
            "- Cycle: `V1763`",
            "- Type: host-only reconciliation of the active WLAN-PD firmware-request directive",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Gate Status",
            "",
            "- The current directive asks for the Android-good firmware-request capture and the native V1736 SM-route comparison.",
            "- That exact discriminator is already present as V1753 and must not be rerun without a new reason, because the contract says one run sets one label.",
            "- Fixed label: `firmware-not-requested`.",
            "",
            "## Android-good Evidence",
            "",
            f"- Manifest: `{android['path']}`",
            f"- Decision/pass: `{android['decision']}` / `{android['pass']}`",
            f"- requested `wlanmdsp`: `{android['requested_wlanmdsp']}`",
            f"- requested PD image: `{android['requested_pd_image']}`",
            f"- trace lines: `{json.dumps(android['trace_lines'], ensure_ascii=False)}`",
            f"- served/request paths: `{json.dumps(diff['android_wlanmdsp_paths'], ensure_ascii=False)}`",
            "",
            "## Native V1736 SM-route Evidence",
            "",
            f"- Manifest: `{native['path']}`",
            f"- Decision/pass: `{native['decision']}` / `{native['pass']}`",
            f"- service-manager / tftp running: `{native['service_manager']}` / `{native['tftp_running']}`",
            f"- WLFW start/request/worker hits: `{native['wlfw_start_hit_count']}` / `{native['wlfw_service_request_hit_count']}` / `{native['wlfw_worker_create_success_hit_count']}`",
            f"- WLFW service 69 / requested `wlanmdsp`: `{native['wlfw_service69_seen']}` / `{native['requested_wlanmdsp']}`",
            f"- old firmware-serve label: `{native['old_firmware_serve_label']}`",
            "",
            "## Existing Diff",
            "",
            f"- Manifest: `{diff['path']}`",
            f"- Decision/pass: `{diff['decision']}` / `{diff['pass']}`",
            f"- Label: `{diff['label']}`",
            f"- Reason: {diff['reason']}",
            f"- Fresh native attempt: `{json.dumps(diff['fresh_native_attempt'], ensure_ascii=False)}`",
            "",
            "## Superseded Follow-up Drift",
            "",
            f"- V1761: `{json.dumps(superseded['v1761'], ensure_ascii=False)}`",
            f"- V1762: `{json.dumps(superseded['v1762'], ensure_ascii=False)}`",
            "- Treat the V1761/V1762 PM/service-object follow-up as superseded for now by the user's latest stop directive.",
            "- Do not implement the V1762 narrow PM service-object helper mode in this unit.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, partition write, tracefs write, or new actor start.",
            "",
            "## Next",
            "",
            "- Stop after the `firmware-not-requested` label.",
            "- The next legitimate work is a separately scoped modem-side WLAN-PD autoload/request-trigger analysis, but only after explicitly reconciling it with this latest stop directive.",
            "- Do not return to route minimization, tracefs plumbing, PM actor expansion, QCACLD, eSoC/RC1, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping from this unit.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE)
    parser.add_argument("--diff-manifest", type=Path, default=DEFAULT_DIFF)
    parser.add_argument("--v1761-manifest", type=Path, default=DEFAULT_V1761)
    parser.add_argument("--v1762-manifest", type=Path, default=DEFAULT_V1762)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    contract = contract_summary(args.contract)
    android = android_summary(args.android_manifest)
    native = native_summary(args.native_manifest)
    diff = diff_summary(args.diff_manifest)
    superseded = {
        "v1761": read_optional_json(args.v1761_manifest),
        "v1762": read_optional_json(args.v1762_manifest),
    }
    decision, pass_ok, reason, label = classify(contract, android, native, diff)
    result = {
        "cycle": "V1763",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "contract": contract,
        "android": android,
        "native_v1736": native,
        "v1753_diff": diff,
        "superseded_followups": superseded,
        "out_dir": display_path(args.out_dir),
        "device_command_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "tracefs_write_executed": False,
        "wifi_hal_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "esoc_notify_executed": False,
        "pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "firmware_write_executed": False,
        "partition_write_executed": False,
    }
    report = render_report(result)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({"decision": decision, "pass": pass_ok, "label": label, "out_dir": result["out_dir"]}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
