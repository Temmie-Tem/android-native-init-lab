#!/usr/bin/env python3
"""V1756 host-only PM register trace classifier from V1736 uprobe evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1755 = REPO_ROOT / "tmp" / "wifi" / "v1755-wlan-pd-pm-vote-contract-classifier" / "manifest.json"
DEFAULT_V1736 = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1756-wlan-pd-pm-register-trace-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1756_WLAN_PD_PM_REGISTER_TRACE_CLASSIFIER_2026-06-03.md"
)


CNSS_EVENTS = (
    "pm_init_pm_client_register_call",
    "pm_init_pm_client_register_retcheck",
    "pm_init_handle_load",
    "pm_init_pm_client_connect_call",
    "pm_init_pm_client_connect_retcheck",
    "pm_init_return_path",
    "wlfw_service_request",
    "wlfw_worker_pthread_create_success",
)

PERIPHERAL_EVENTS = (
    "periph_pm_client_register_entry",
    "periph_pm_register_connect_entry",
    "periph_vndbinder_init_call",
    "periph_default_service_manager_call",
    "periph_manager_name_string16_call",
    "periph_service_manager_get_call",
    "periph_binder_object_present_check",
    "periph_as_interface_call",
    "periph_manager_register_tx_call",
    "periph_manager_register_tx_retcheck",
    "periph_success_path",
    "periph_pm_register_connect_return",
    "periph_pm_client_register_common_return",
)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, limit: int = 6_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def str_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value or str(default)), 0)
    except ValueError:
        return default


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def hit(keys: dict[str, str], prefix: str, event: str) -> int:
    return str_int(keys.get(f"{prefix}.{event}.hit_count"))


def first_line(keys: dict[str, str], prefix: str, event: str) -> str:
    return keys.get(f"{prefix}.{event}.first_hit_line", "none")


def collect_v1736(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    base = Path(manifest["out_dir"])
    helper = read_text(base / "test-v1393-helper-result.stdout.txt")
    keys = parse_key_values(helper)
    cnss_prefix = "wlan_pd_cnss_nonlog_control_flow.uprobe"
    periph_prefix = "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe"
    cnss_hits = {event: hit(keys, cnss_prefix, event) for event in CNSS_EVENTS}
    periph_hits = {event: hit(keys, periph_prefix, event) for event in PERIPHERAL_EVENTS}
    cnss_first = {event: first_line(keys, cnss_prefix, event) for event in CNSS_EVENTS}
    periph_first = {event: first_line(keys, periph_prefix, event) for event in PERIPHERAL_EVENTS}
    gate = manifest.get("gate") or {}
    return {
        "manifest": display_path(path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "gate": gate,
        "cnss_hits": cnss_hits,
        "peripheral_hits": periph_hits,
        "cnss_first_hit_line": cnss_first,
        "peripheral_first_hit_line": periph_first,
        "nonlog_label": keys.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "tracefs_available": keys.get("wlan_pd_cnss_nonlog_control_flow.uprobe.tracefs.available", ""),
        "peripheral_tracefs_available": keys.get("wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.tracefs.available", ""),
    }


def classify(v1755: dict[str, Any], v1736: dict[str, Any]) -> tuple[str, bool, str, str]:
    if v1755.get("label") != "pm-vote-contract-split-gate-needed":
        return (
            "v1756-prerequisite-v1755-label-mismatch",
            False,
            "V1755 did not classify the PM vote contract split gate",
            "prerequisite-mismatch",
        )
    gate = v1736["gate"]
    cnss = v1736["cnss_hits"]
    periph = v1736["peripheral_hits"]
    register_reached = cnss["pm_init_pm_client_register_call"] > 0 and cnss["pm_init_pm_client_register_retcheck"] > 0
    service_object_reached = (
        periph["periph_pm_client_register_entry"] > 0
        and periph["periph_pm_register_connect_entry"] > 0
        and periph["periph_vndbinder_init_call"] > 0
        and periph["periph_default_service_manager_call"] > 0
        and periph["periph_service_manager_get_call"] > 0
        and periph["periph_binder_object_present_check"] > 0
    )
    no_interface_or_tx = (
        periph["periph_as_interface_call"] == 0
        and periph["periph_manager_register_tx_call"] == 0
        and periph["periph_success_path"] == 0
    )
    no_handle_or_connect = (
        cnss["pm_init_handle_load"] == 0
        and cnss["pm_init_pm_client_connect_call"] == 0
    )
    downstream_block = str_int(gate.get("requested_wlanmdsp")) == 0 and str_int(gate.get("wlfw_service_request_hit_count")) > 0
    if register_reached and service_object_reached and no_interface_or_tx and no_handle_or_connect and downstream_block:
        return (
            "v1756-pm-register-stops-after-binder-object-check-host-pass",
            True,
            "V1736 reaches cnss PM register and libperipheral vndbinder/service-manager/binder-object checks, but does not reach asInterface, manager register transaction, success path, handle load, pm_client_connect, or wlanmdsp request",
            "peripheral-manager-interface-conversion-gap",
        )
    return (
        "v1756-pm-register-trace-classification-incomplete",
        False,
        "V1736 PM register trace did not match the supported interface-conversion gap",
        "incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    v1736 = result["v1736"]
    cnss = v1736["cnss_hits"]
    periph = v1736["peripheral_hits"]
    return "\n".join([
        "# Native Init V1756 WLAN-PD PM Register Trace Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1756`",
        "- Type: host-only PM register uprobe trace classifier",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## V1736 CNSS PM Init Hits",
        "",
        "| Event | Hit Count | First Hit |",
        "| --- | ---: | --- |",
        *[
            f"| `{event}` | `{cnss[event]}` | `{v1736['cnss_first_hit_line'][event]}` |"
            for event in CNSS_EVENTS
        ],
        "",
        "## V1736 libperipheral Client Hits",
        "",
        "| Event | Hit Count | First Hit |",
        "| --- | ---: | --- |",
        *[
            f"| `{event}` | `{periph[event]}` | `{v1736['peripheral_first_hit_line'][event]}` |"
            for event in PERIPHERAL_EVENTS
        ],
        "",
        "## Key State",
        "",
        f"- V1736 manifest: `{v1736['manifest']}`",
        f"- V1736 decision/pass: `{v1736['decision']}` / `{v1736['pass']}`",
        f"- nonlog label: `{v1736['nonlog_label']}`",
        f"- tracefs available: `{v1736['tracefs_available']}` / peripheral `{v1736['peripheral_tracefs_available']}`",
        f"- `wlfw_service_request` hits: `{v1736['gate'].get('wlfw_service_request_hit_count')}`",
        f"- requested `wlanmdsp`: `{v1736['gate'].get('requested_wlanmdsp')}`",
        f"- firmware label: `{v1736['gate'].get('old_firmware_serve_label')}`",
        "",
        "## Interpretation",
        "",
        "- The missing PM vote is not because `cnss-daemon` skips PM registration. V1736 reaches `pm_client_register`.",
        "- The path enters `libperipheral_client.so`, initializes vndbinder, asks the default service manager for `vendor.qcom.PeripheralManager`, and reaches the binder-object-present check.",
        "- The path does not reach `asInterface`, the manager register transaction, libperipheral success, CNSS PM handle load, or `pm_client_connect`.",
        "- Therefore the next blocker is a binder interface conversion / service object compatibility gap, not actor ordering, firmware serving, eSoC/RC1, or Wi-Fi HAL.",
        "",
        "## Next Candidate",
        "",
        "- V1757 should be host/source-only: disassemble/classify `libperipheral_client.so` between `periph_binder_object_present_check` and `periph_as_interface_call` to identify the exact branch condition.",
        "- A later live gate should target only that interface conversion gap and keep eSoC/RC1, `/dev/subsys_esoc0`, `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until `wlanmdsp.mbn` request or WLFW service 69 appears.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only and reads retained V1736/V1755 evidence. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1755-manifest", type=Path, default=DEFAULT_V1755)
    parser.add_argument("--v1736-manifest", type=Path, default=DEFAULT_V1736)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    v1755 = load_json(args.v1755_manifest)
    v1736 = collect_v1736(args.v1736_manifest)
    decision, pass_ok, reason, label = classify(v1755, v1736)
    result = {
        "cycle": "V1756",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "v1755": {
            "manifest": display_path(args.v1755_manifest),
            "decision": v1755.get("decision"),
            "label": v1755.get("label"),
            "pass": bool(v1755.get("pass")),
        },
        "v1736": v1736,
        "out_dir": display_path(args.out_dir),
        "report_path": display_path(args.report_path),
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes": False,
            "external_ping": False,
        },
    }
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(store.path("summary.md"), report)
    write_private_text(args.report_path, report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
