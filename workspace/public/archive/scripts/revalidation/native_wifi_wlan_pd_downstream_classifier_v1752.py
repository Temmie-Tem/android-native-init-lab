#!/usr/bin/env python3
"""V1752 host-only classifier for the WLAN-PD downstream blocker after V1751."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1751 = REPO_ROOT / "tmp" / "wifi" / "v1751-wlan-pd-tracefs-mount-restore-handoff" / "manifest.json"
DEFAULT_V1719 = REPO_ROOT / "tmp" / "wifi" / "v1719-cnss-peripheral-client-uprobe-handoff" / "manifest.json"
DEFAULT_V1727 = REPO_ROOT / "tmp" / "wifi" / "v1727-wlan-pd-service-manager-bootstrap-handoff" / "manifest.json"
DEFAULT_V1736 = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_CNSS = REPO_ROOT / "tmp" / "wifi" / "v226-vendor-root-live-export" / "vendor-source" / "bin" / "cnss-daemon"
DEFAULT_PERIPHERAL = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v226-vendor-root-live-export"
    / "vendor-source"
    / "lib64"
    / "libperipheral_client.so"
)
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1752-wlan-pd-downstream-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1752_WLAN_PD_DOWNSTREAM_CLASSIFIER_2026-06-03.md"
)

CNSS_OFFSETS = {
    "wlfw_start": "0xec00",
    "wlfw_service_request": "0xd9fc",
    "wlfw_optional_pm_init1_call": "0xec34",
    "wlfw_optional_pm_init1_return": "0xec38",
    "pm_init_entry": "0xc39c",
    "pm_init_pm_client_register_call": "0xc624",
    "pm_init_pm_client_register_retcheck": "0xc628",
}
PERIPHERAL_OFFSETS = {
    "pm_client_register_entry": "0x6ec8",
    "pm_register_connect_entry": "0x612c",
    "vndbinder_init_call": "0x6168",
    "default_service_manager_call": "0x6190",
    "manager_name_string16_call": "0x61a8",
    "service_manager_get_call": "0x61c4",
    "manager_register_tx_call": "0x6274",
    "pm_register_connect_return": "0x66dc",
    "pm_client_register_common_return": "0x7184",
}


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def gate(path: Path) -> dict[str, Any]:
    return load_json(path).get("gate", {})


def str_int(value: object) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def yes(value: object) -> bool:
    return str(value) in {"1", "true", "True"}


def objdump_snippet(path: Path, start: str, stop: str) -> str:
    completed = subprocess.run(
        ["aarch64-linux-gnu-objdump", "-d", f"--start-address={start}", f"--stop-address={stop}", str(path)],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def static_evidence(args: argparse.Namespace) -> dict[str, Any]:
    cnss_wlfw = objdump_snippet(args.cnss_daemon, "0xec00", "0xed20")
    cnss_service_request = objdump_snippet(args.cnss_daemon, "0xd9fc", "0xda60")
    peripheral_connect = objdump_snippet(args.peripheral_client, "0x612c", "0x62a0")
    return {
        "cnss_daemon": display_path(args.cnss_daemon),
        "libperipheral_client": display_path(args.peripheral_client),
        "cnss_offsets": CNSS_OFFSETS,
        "peripheral_offsets": PERIPHERAL_OFFSETS,
        "wlfw_start_calls_pm_init_before_qmi_setup": all(
            token in cnss_wlfw
            for token in ("ec34", "bl", "c39c", "ecd4", "eb14")
        ),
        "wlfw_service_request_is_separate_function": "d9fc" in cnss_service_request and "a21c" in cnss_service_request,
        "default_service_manager_precedes_service_name": all(
            token in peripheral_connect
            for token in ("6190", "defaultServiceManager", "61a8", "String16")
        ),
        "service_manager_get_after_service_name": all(token in peripheral_connect for token in ("61c4", "blr")),
        "wlfw_start_excerpt": cnss_wlfw,
        "wlfw_service_request_excerpt": cnss_service_request,
        "peripheral_connect_excerpt": peripheral_connect,
    }


def observed_evidence(
    v1751_gate: dict[str, Any],
    v1719_gate: dict[str, Any],
    v1727_gate: dict[str, Any],
    v1736_gate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "v1751_label": v1751_gate.get("v1751_label"),
        "v1751_tracefs_available": v1751_gate.get("v1744_tracefs_available"),
        "v1751_uprobe_hit_count": v1751_gate.get("v1744_uprobe_hit_count"),
        "v1751_nonlog_label": v1751_gate.get("v1744_nonlog_label"),
        "v1751_output_label": v1751_gate.get("v1744_output_label"),
        "v1751_legacy_firmware_label": v1751_gate.get("old_firmware_serve_label"),
        "v1751_route_safety_ok": bool(v1751_gate.get("v1744_route_safety_ok")),
        "v1719_wlfw_start_hit_count": v1719_gate.get("nonlog_wlfw_start_hit_count"),
        "v1719_wlfw_service_request_hit_count": v1719_gate.get("nonlog_wlfw_service_request_hit_count"),
        "v1719_optional_pm_init1_call_hit_count": v1719_gate.get("nonlog_wlfw_optional_pm_init1_call_hit_count"),
        "v1719_optional_pm_init1_return_hit_count": v1719_gate.get("nonlog_wlfw_optional_pm_init1_return_hit_count"),
        "v1719_pm_client_register_call_hit_count": v1719_gate.get("nonlog_pm_init_pm_client_register_call_hit_count"),
        "v1719_pm_client_register_retcheck_hit_count": v1719_gate.get("nonlog_pm_init_pm_client_register_retcheck_hit_count"),
        "v1719_periph_default_service_manager_hit_count": v1719_gate.get(
            "peripheral_periph_default_service_manager_call_hit_count"
        ),
        "v1719_periph_manager_name_hit_count": v1719_gate.get(
            "peripheral_periph_manager_name_string16_call_hit_count"
        ),
        "v1719_periph_service_manager_get_hit_count": v1719_gate.get(
            "peripheral_periph_service_manager_get_call_hit_count"
        ),
        "v1727_service_manager": v1727_gate.get("service_manager"),
        "v1727_wlfw_start_hit_count": v1727_gate.get("wlfw_start_hit_count"),
        "v1727_wlfw_service_request_hit_count": v1727_gate.get("wlfw_service_request_hit_count"),
        "v1727_worker_create_success_hit_count": v1727_gate.get("wlfw_worker_create_success_hit_count"),
        "v1727_firmware_label": v1727_gate.get("old_firmware_serve_label"),
        "v1736_service_manager": v1736_gate.get("service_manager"),
        "v1736_wlfw_start_hit_count": v1736_gate.get("wlfw_start_hit_count"),
        "v1736_wlfw_service_request_hit_count": v1736_gate.get("wlfw_service_request_hit_count"),
        "v1736_worker_create_success_hit_count": v1736_gate.get("wlfw_worker_create_success_hit_count"),
        "v1736_wlfw_service69_seen": v1736_gate.get("wlfw_service69_seen"),
        "v1736_wlfw_ind_register_qmi_hit_count": v1736_gate.get("wlfw_ind_register_qmi_hit_count"),
        "v1736_wlfw_cap_qmi_hit_count": v1736_gate.get("wlfw_cap_qmi_hit_count"),
        "v1736_requested_wlanmdsp": v1736_gate.get("requested_wlanmdsp"),
        "v1736_firmware_label": v1736_gate.get("old_firmware_serve_label"),
    }


def classify(observed: dict[str, Any], static: dict[str, Any]) -> tuple[str, bool, str, dict[str, bool]]:
    checks = {
        "v1751_reached_wlfw": observed["v1751_label"] == "wlfw-start-reached-downstream-block",
        "tracefs_worked": yes(observed["v1751_tracefs_available"]) and str_int(observed["v1751_uprobe_hit_count"]) > 0,
        "route_safe": bool(observed["v1751_route_safety_ok"]),
        "pure_route_firmware_not_requested": observed["v1751_legacy_firmware_label"] == "firmware-not-requested",
        "pure_route_wlfw_start_hit": str_int(observed["v1719_wlfw_start_hit_count"]) > 0,
        "pure_route_wlfw_service_request_not_hit": str_int(observed["v1719_wlfw_service_request_hit_count"]) == 0,
        "pure_route_optional_pm_call_no_return": (
            str_int(observed["v1719_optional_pm_init1_call_hit_count"]) > 0
            and str_int(observed["v1719_optional_pm_init1_return_hit_count"]) == 0
        ),
        "pure_route_pm_client_register_call_no_return": (
            str_int(observed["v1719_pm_client_register_call_hit_count"]) > 0
            and str_int(observed["v1719_pm_client_register_retcheck_hit_count"]) == 0
        ),
        "pure_route_peripheral_default_sm_call_no_name": (
            str_int(observed["v1719_periph_default_service_manager_hit_count"]) > 0
            and str_int(observed["v1719_periph_manager_name_hit_count"]) == 0
            and str_int(observed["v1719_periph_service_manager_get_hit_count"]) == 0
        ),
        "service_route_v1727_reaches_request": (
            yes(observed["v1727_service_manager"])
            and str_int(observed["v1727_wlfw_start_hit_count"]) > 0
            and str_int(observed["v1727_wlfw_service_request_hit_count"]) > 0
        ),
        "service_route_v1727_firmware_not_requested": observed["v1727_firmware_label"] == "firmware-not-requested",
        "service_route_v1736_reaches_worker": (
            yes(observed["v1736_service_manager"])
            and str_int(observed["v1736_wlfw_start_hit_count"]) > 0
            and str_int(observed["v1736_wlfw_service_request_hit_count"]) > 0
            and str_int(observed["v1736_worker_create_success_hit_count"]) > 0
        ),
        "service_route_v1736_no_wlfw69_or_qmi": (
            str_int(observed["v1736_wlfw_service69_seen"]) == 0
            and str_int(observed["v1736_wlfw_ind_register_qmi_hit_count"]) == 0
            and str_int(observed["v1736_wlfw_cap_qmi_hit_count"]) == 0
        ),
        "service_route_v1736_no_wlanmdsp": (
            str_int(observed["v1736_requested_wlanmdsp"]) == 0
            and observed["v1736_firmware_label"] == "firmware-not-requested"
        ),
        "static_wlfw_pm_before_request": bool(static["wlfw_start_calls_pm_init_before_qmi_setup"]),
        "static_peripheral_default_sm_before_name": bool(static["default_service_manager_precedes_service_name"]),
    }
    if all(checks.values()):
        return (
            "v1752-pure-route-default-sm-blocker-reconciled-service-route-downstream-pass",
            True,
            "pure internal-modem route blocks at vendor Binder defaultServiceManager before wlfw_service_request, while the already-proven service-manager route reaches wlfw_service_request/worker and still blocks at modem-side WLAN-PD autoload",
            checks,
        )
    return (
        "v1752-cnss-downstream-classifier-incomplete",
        False,
        "existing evidence does not fully reconcile the pure-route defaultServiceManager blocker with the service-manager downstream blocker",
        checks,
    )


def render_report(result: dict[str, Any]) -> str:
    obs = result["observed"]
    static = result["static"]
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1752 WLAN-PD Downstream Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1752`",
        "- Type: host-only downstream route reconciliation classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Observed Evidence",
        "",
        f"- V1751 label: `{obs['v1751_label']}`",
        f"- V1751 tracefs/uprobe hits: `{obs['v1751_tracefs_available']}` / `{obs['v1751_uprobe_hit_count']}`",
        f"- V1751 non-log/output labels: `{obs['v1751_nonlog_label']}` / `{obs['v1751_output_label']}`",
        f"- V1751 firmware label: `{obs['v1751_legacy_firmware_label']}`",
        f"- V1719 pure-route `wlfw_start` / `wlfw_service_request` hits: `{obs['v1719_wlfw_start_hit_count']}` / `{obs['v1719_wlfw_service_request_hit_count']}`",
        f"- V1719 optional PM call/return hits: `{obs['v1719_optional_pm_init1_call_hit_count']}` / `{obs['v1719_optional_pm_init1_return_hit_count']}`",
        f"- V1719 `pm_client_register` call/retcheck hits: `{obs['v1719_pm_client_register_call_hit_count']}` / `{obs['v1719_pm_client_register_retcheck_hit_count']}`",
        f"- V1719 peripheral defaultServiceManager/name/get hits: `{obs['v1719_periph_default_service_manager_hit_count']}` / `{obs['v1719_periph_manager_name_hit_count']}` / `{obs['v1719_periph_service_manager_get_hit_count']}`",
        f"- V1727 service-manager `wlfw_start` / `wlfw_service_request` hits: `{obs['v1727_wlfw_start_hit_count']}` / `{obs['v1727_wlfw_service_request_hit_count']}`",
        f"- V1727 firmware label: `{obs['v1727_firmware_label']}`",
        f"- V1736 service-manager `wlfw_start` / `wlfw_service_request` / worker hits: `{obs['v1736_wlfw_start_hit_count']}` / `{obs['v1736_wlfw_service_request_hit_count']}` / `{obs['v1736_worker_create_success_hit_count']}`",
        f"- V1736 WLFW service 69 / indication QMI / capability QMI hits: `{obs['v1736_wlfw_service69_seen']}` / `{obs['v1736_wlfw_ind_register_qmi_hit_count']}` / `{obs['v1736_wlfw_cap_qmi_hit_count']}`",
        f"- V1736 requested `wlanmdsp` / firmware label: `{obs['v1736_requested_wlanmdsp']}` / `{obs['v1736_firmware_label']}`",
        "",
        "## Static Evidence",
        "",
        f"- cnss-daemon: `{static['cnss_daemon']}`",
        f"- libperipheral_client: `{static['libperipheral_client']}`",
        f"- `wlfw_start` calls PM init before QMI setup: `{static['wlfw_start_calls_pm_init_before_qmi_setup']}`",
        f"- `wlfw_service_request` is a separate observed function: `{static['wlfw_service_request_is_separate_function']}`",
        f"- `defaultServiceManager()` precedes service-name construction: `{static['default_service_manager_precedes_service_name']}`",
        f"- service-manager `getService` call is after service-name construction: `{static['service_manager_get_after_service_name']}`",
        "",
        "## Checks",
        "",
        *[f"- `{key}`: `{value}`" for key, value in checks.items()],
        "",
        "## Interpretation",
        "",
        "- V1751/V1719 prove the pure no-service-manager route reaches `wlfw_start` but blocks in `libperipheral_client.so` before `wlfw_service_request`.",
        "- V1727/V1736 prove the service-manager bootstrap route gets past that client-side blocker and reaches `wlfw_service_request` plus WLFW worker creation.",
        "- Therefore service-manager is a CNSS entry/request enabler, not proof of WLAN-PD or WLFW publication.",
        "- The active downstream blocker remains modem-side WLAN-PD autoload: no WLFW service 69, no WLFW indication/capability QMI, no `wlanmdsp` request, and no `wlan0`.",
        "- Do not debug `pm-service -22`, add PM trio actors, add `boot_wlan`, or return to eSoC/RC1 for the WLAN-PD goal.",
        "",
        "## Next",
        "",
        "- V1753 should be host-only/source-only: compare Android-good firmware request/serve evidence for `wlanmdsp.mbn` around WLAN-PD UP against the V1736 native service-manager baseline.",
        "- The discriminator is whether Android-good `tftp_server` or `rmt_storage` observes a WLAN-PD image request before WLAN-PD UP and which served path satisfies it.",
        "- Do not rebuild or rerun the service-manager bootstrap unless a concrete stale-evidence gap appears in V1736/V1727 artifacts.",
        "- Keep blocked: PM trio, `vendor.qcom.PeripheralManager` actor, `pm-service -22` debugging, `boot_wlan`, eSoC/RC1, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Safety Scope",
        "",
        "This classifier performed host-only analysis only. It did not contact the device, flash, reboot, start service-manager or PM actors, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1751-manifest", type=Path, default=DEFAULT_V1751)
    parser.add_argument("--v1719-manifest", type=Path, default=DEFAULT_V1719)
    parser.add_argument("--v1727-manifest", type=Path, default=DEFAULT_V1727)
    parser.add_argument("--v1736-manifest", type=Path, default=DEFAULT_V1736)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS)
    parser.add_argument("--peripheral-client", type=Path, default=DEFAULT_PERIPHERAL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    v1751_gate = gate(args.v1751_manifest)
    v1719_gate = gate(args.v1719_manifest)
    v1727_gate = gate(args.v1727_manifest)
    v1736_gate = gate(args.v1736_manifest)
    observed = observed_evidence(v1751_gate, v1719_gate, v1727_gate, v1736_gate)
    static = static_evidence(args)
    decision, pass_ok, reason, checks = classify(observed, static)
    result = {
        "cycle": "V1752",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "inputs": {
            "v1751_manifest": display_path(args.v1751_manifest),
            "v1719_manifest": display_path(args.v1719_manifest),
            "v1727_manifest": display_path(args.v1727_manifest),
            "v1736_manifest": display_path(args.v1736_manifest),
            "cnss_daemon": display_path(args.cnss_daemon),
            "peripheral_client": display_path(args.peripheral_client),
        },
        "observed": observed,
        "static": static,
        "checks": checks,
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    store.write_text("cnss-wlfw-start.objdump.txt", static["wlfw_start_excerpt"])
    store.write_text("cnss-wlfw-service-request.objdump.txt", static["wlfw_service_request_excerpt"])
    store.write_text("libperipheral-register-connect.objdump.txt", static["peripheral_connect_excerpt"])
    write_private_text(args.report_path, render_report(result))
    print(json.dumps({"decision": decision, "pass": pass_ok, "out_dir": display_path(args.out_dir)}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
