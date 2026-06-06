#!/usr/bin/env python3
"""V1561 host-only WLFW contract rebase classifier.

V1560 showed that the current native V1496/V1557 route reaches generic
`cnss-daemon` netlink traffic plus forced RC1 enumeration, but never reaches
`cnss-daemon wlfw_start`.  V966 already attributed Android's successful lower
Wi-Fi sequence to an Android init Wi-Fi service-window where `wlfw_start`
precedes `/dev/subsys_esoc0`.

This classifier reconciles those two evidence sets and checks whether the
current helper/init artifacts already contain a bounded service-window route
that can be used as the next source/build-only gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1561-wlfw-contract-rebase-classifier")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1561_WLFW_CONTRACT_REBASE_CLASSIFIER_2026-06-02.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1561-wlfw-contract-rebase-classifier.txt")

V966_MANIFEST = Path("tmp/wifi/v966-android-wlfw-start-attribution/manifest.json")
V1560_MANIFEST = Path("tmp/wifi/v1560-android-order-vs-native-route-classifier/manifest.json")
NATIVE_V1496_LOG = Path("tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff/test-v1393-log.stdout.txt")
NATIVE_V1557_LOG = Path("tmp/wifi/v1557-native-endpoint-long-hold-handoff/test-log.stdout.txt")
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
PID1_WIFI_BOOT_SOURCE = Path("stage3/linux_init/v724/90_main.inc.c")

MODE_RE = re.compile(r"\bmode=(?P<mode>[A-Za-z0-9_.@:+/-]+)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    resolved = repo_path(path)
    try:
        return str(resolved.relative_to(repo_path(".")))
    except ValueError:
        return str(resolved)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def get_nested(mapping: dict[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def event_time(manifest: dict[str, Any], name: str) -> float | None:
    value = get_nested(manifest, "timeline", name, "time")
    return float(value) if isinstance(value, int | float) else None


def extract_modes(text: str) -> list[str]:
    modes: list[str] = []
    for match in MODE_RE.finditer(text):
        mode = match.group("mode")
        if mode not in modes:
            modes.append(mode)
    return modes


def helper_capabilities(source: str) -> dict[str, bool]:
    return {
        "service_window_start_only_mode": "wifi-companion-android-wifi-service-window-start-only" in source,
        "service_window_subsys_capture_mode": "wifi-companion-android-wifi-service-window-subsys-trigger-capture" in source,
        "service_window_allow_flag": "--allow-android-wifi-service-window" in source,
        "service_window_capture_allow_flag": "--allow-android-wifi-service-window-subsys-trigger-capture" in source,
        "service_window_rejects_scan_connect": "allow_scan_only" in source and "allow_connect_dhcp_ping" in source,
        "service_window_rejects_other_actor_flags": "Android Wi-Fi service-window modes accept only their service-window allow flags" in source,
        "wificond_target_profile": "target-profile cnss-daemon|system-toybox|system-sh|linker64-self|apex-linker64-self|system-getprop|system-servicemanager|system-hwservicemanager|system-wificond" in source,
        "wifi_hal_legacy_profile": "vendor-wifi-hal-legacy" in source,
        "wifi_hal_ext_profile": "vendor-wifi-hal-ext" in source,
        "wificond_property_key": "init.svc.wificond" in source,
        "cnss_daemon_property_key": "init.svc.cnss-daemon" in source,
        "wlfw_kmsg_summary": "cnss_wlfw_pre.wlfw_start_seen" in source,
    }


def pid1_wifi_test_contract(source: str) -> dict[str, Any]:
    mode_match = re.search(r'#define\s+A90_V1393_WIFI_TEST_MODE\s+"(?P<mode>[^"]+)"', source)
    helper_match = re.search(r'#define\s+A90_V1393_WIFI_TEST_HELPER\s+"(?P<helper>[^"]+)"', source)
    argv_flags = [
        "--allow-pm-service-trigger-observer",
        "--allow-post-pm-mdm-helper-esoc-observer",
        "--allow-post-pm-mdm-helper-lower-trace",
        "--pm-observer-start-mdm-helper-after-cnss",
        "--pm-observer-start-mdm-helper-before-cnss",
        "--pm-observer-mknod-esoc-dev-node-before-cnss",
        "--pm-observer-private-firmware-mounts",
        "--allow-android-wifi-service-window",
    ]
    return {
        "helper": helper_match.group("helper") if helper_match else None,
        "mode": mode_match.group("mode") if mode_match else None,
        "hardcoded_post_pm_observer": bool(mode_match and mode_match.group("mode") == "wifi-companion-post-pm-mdm-helper-esoc-observer"),
        "hardcoded_service_window": bool(mode_match and "android-wifi-service-window" in mode_match.group("mode")),
        "argv_flags_present": {flag: flag in source for flag in argv_flags},
    }


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def value_text(value: Any) -> str:
    return "missing" if value is None else str(value)


def timeline_rows(v966: dict[str, Any], v1560: dict[str, Any]) -> list[list[str]]:
    android_current = get_nested(v1560, "analysis", "android") or {}
    native_v1496 = get_nested(v1560, "analysis", "native_v1496") or {}
    native_v1557 = get_nested(v1560, "analysis", "native_v1557") or {}
    return [
        [
            "Android prior attribution",
            value_text(event_time(v966, "wlfw_start")),
            value_text(event_time(v966, "esoc0_subsystem_get")),
            value_text(event_time(v966, "bdf_regdb")),
            value_text(event_time(v966, "fw_ready")),
            value_text(event_time(v966, "wlan0_event")),
        ],
        [
            "Android current reference",
            value_text(android_current.get("wlfw_start")),
            value_text(android_current.get("esoc0_get")),
            value_text(android_current.get("bdf_regdb")),
            value_text(android_current.get("fw_ready")),
            value_text(android_current.get("wlan0")),
        ],
        [
            "Native V1496 current route",
            value_text(native_v1496.get("wlfw_start")),
            value_text(native_v1496.get("esoc0_get")),
            value_text(native_v1496.get("bdf")),
            value_text(native_v1496.get("fw_ready")),
            value_text(native_v1496.get("wlan0")),
        ],
        [
            "Native V1557 current route",
            value_text(native_v1557.get("wlfw_start")),
            value_text(native_v1557.get("esoc0_get")),
            value_text(native_v1557.get("bdf")),
            value_text(native_v1557.get("fw_ready")),
            value_text(native_v1557.get("wlan0")),
        ],
    ]


def classify() -> dict[str, Any]:
    v966 = read_json(V966_MANIFEST)
    v1560 = read_json(V1560_MANIFEST)
    v1496_log = read_text(NATIVE_V1496_LOG)
    v1557_log = read_text(NATIVE_V1557_LOG)
    helper_source = read_text(HELPER_SOURCE)
    pid1_source = read_text(PID1_WIFI_BOOT_SOURCE)

    v966_checks = v966.get("checks") if isinstance(v966.get("checks"), dict) else {}
    v1560_derived = get_nested(v1560, "analysis", "derived") or {}
    modes = {
        "native_v1496": extract_modes(v1496_log),
        "native_v1557": extract_modes(v1557_log),
    }
    capabilities = helper_capabilities(helper_source)
    pid1_contract = pid1_wifi_test_contract(pid1_source)

    current_route_is_post_pm_observer = all(
        "wifi-companion-post-pm-mdm-helper-esoc-observer" in modes[key]
        for key in ("native_v1496", "native_v1557")
    )
    current_route_not_service_window = all(
        not any("android-wifi-service-window" in mode for mode in modes[key])
        for key in ("native_v1496", "native_v1557")
    )
    service_window_ready_in_helper = all(
        capabilities[key]
        for key in (
            "service_window_start_only_mode",
            "service_window_subsys_capture_mode",
            "service_window_allow_flag",
            "service_window_capture_allow_flag",
            "service_window_rejects_other_actor_flags",
            "wificond_target_profile",
            "wifi_hal_legacy_profile",
            "wifi_hal_ext_profile",
            "wlfw_kmsg_summary",
        )
    )
    android_contract_proven = (
        v966.get("pass") is True
        and v966_checks.get("android_wlfw_start_present") is True
        and v966_checks.get("android_wlfw_before_esoc0_subsystem_get") is True
        and v966_checks.get("v963_native_cnss_netlink_without_wlfw") is True
        and v1560.get("pass") is True
        and v1560_derived.get("android_order_ok") is True
        and v1560_derived.get("native_route_lacks_wlfw") is True
    )
    route_gap_proven = (
        current_route_is_post_pm_observer
        and current_route_not_service_window
        and pid1_contract["hardcoded_post_pm_observer"]
        and not pid1_contract["hardcoded_service_window"]
    )
    pass_result = android_contract_proven and route_gap_proven and service_window_ready_in_helper
    decision = (
        "v1561-current-wlfw-contract-rebases-v966-service-window-next"
        if pass_result
        else "v1561-wlfw-contract-rebase-incomplete-review"
    )
    reason = (
        "V966 and V1560 agree that Android reaches cnss-daemon wlfw_start before esoc0/BDF while the current native test route never reaches wlfw_start; current v1393 test boot is hardcoded to the post-PM observer route, but the helper already contains bounded Android Wi-Fi service-window modes"
        if pass_result
        else "existing evidence or helper capabilities do not fully prove the Android service-window contract gap"
    )
    next_gate = {
        "recommended_cycle": "V1562",
        "type": "source/build-only route selector before live",
        "focus": "make the native Wi-Fi test boot select the existing Android Wi-Fi service-window start-only mode, or build an equivalent bounded helper runner",
        "success_markers": [
            "boot/test artifact uses wifi-companion-android-wifi-service-window-start-only or the subsys-trigger-capture variant",
            "artifact contains --allow-android-wifi-service-window and no scan/connect/DHCP/external-ping flags",
            "live follow-up observes cnss-daemon wlfw_start/wlfw_service_request before treating RC1/L0 as primary",
        ],
        "guardrails": [
            "no credentialed connect attempt",
            "no Wi-Fi scan/connect",
            "no DHCP/routes or external ping",
            "no direct PMIC/GPIO/GDSC writes",
            "no blind eSoC notify or BOOT_DONE spoof",
            "no global PCI rescan or platform bind/unbind",
        ],
    }
    rows = timeline_rows(v966, v1560)
    checks = {
        "v966_pass": v966.get("pass") is True,
        "v966_wlfw_before_esoc0": v966_checks.get("android_wlfw_before_esoc0_subsystem_get") is True,
        "v966_native_cnss_netlink_without_wlfw": v966_checks.get("v963_native_cnss_netlink_without_wlfw") is True,
        "v1560_pass": v1560.get("pass") is True,
        "v1560_android_order_ok": v1560_derived.get("android_order_ok") is True,
        "v1560_native_route_lacks_wlfw": v1560_derived.get("native_route_lacks_wlfw") is True,
        "native_v1496_mode_post_pm_observer": "wifi-companion-post-pm-mdm-helper-esoc-observer" in modes["native_v1496"],
        "native_v1557_mode_post_pm_observer": "wifi-companion-post-pm-mdm-helper-esoc-observer" in modes["native_v1557"],
        "current_route_not_service_window": current_route_not_service_window,
        "pid1_test_boot_hardcoded_post_pm_observer": pid1_contract["hardcoded_post_pm_observer"],
        "helper_service_window_ready": service_window_ready_in_helper,
    }
    return {
        "decision": decision,
        "pass": pass_result,
        "reason": reason,
        "checks": checks,
        "timeline_rows": rows,
        "modes": modes,
        "helper_capabilities": capabilities,
        "pid1_wifi_test_contract": pid1_contract,
        "next_gate": next_gate,
    }


def render_report(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    helper_rows = [[key, bool_text(value)] for key, value in analysis["helper_capabilities"].items()]
    pid1_flags = analysis["pid1_wifi_test_contract"]["argv_flags_present"]
    return "\n".join(
        [
            "# Native Init V1561 WLFW Contract Rebase Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1561`",
            "- Type: host-only WLFW contract rebase classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path"],
                [
                    ["v966_wlfw_attribution", rel(V966_MANIFEST)],
                    ["v1560_current_order", rel(V1560_MANIFEST)],
                    ["native_v1496_log", rel(NATIVE_V1496_LOG)],
                    ["native_v1557_log", rel(NATIVE_V1557_LOG)],
                    ["helper_source", rel(HELPER_SOURCE)],
                    ["pid1_wifi_test_source", rel(PID1_WIFI_BOOT_SOURCE)],
                ],
            ),
            "",
            "## Contract Comparison",
            "",
            markdown_table(
                ["source", "wlfw_start", "esoc0", "BDF", "FW-ready", "wlan0"],
                analysis["timeline_rows"],
            ),
            "",
            "## Derived Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in analysis["checks"].items()]),
            "",
            "## Current Native Route",
            "",
            markdown_table(
                ["artifact", "modes"],
                [[key, ", ".join(value) if value else "missing"] for key, value in analysis["modes"].items()],
            ),
            "",
            "The current v1393 Wi-Fi test boot is still wired to "
            f"`{analysis['pid1_wifi_test_contract']['mode']}` via "
            f"`{analysis['pid1_wifi_test_contract']['helper']}`. That route is useful for PM/eSoC "
            "observer diagnostics, but it does not reproduce Android's pre-`esoc0` "
            "`cnss-daemon wlfw_start` contract.",
            "",
            "## Helper Service-Window Surface",
            "",
            markdown_table(["capability", "present"], helper_rows),
            "",
            "## PID1 Test-Boot Flags",
            "",
            markdown_table(["flag", "present"], [[key, bool_text(value)] for key, value in pid1_flags.items()]),
            "",
            "## Interpretation",
            "",
            "V966 and V1560 now agree on the important ordering: Android reaches "
            "`cnss-daemon wlfw_start`/`wlfw_service_request` before `/dev/subsys_esoc0`, BDF, "
            "FW-ready, and `wlan0`. Native V1496/V1557 reaches generic `cnss-daemon` netlink "
            "and the PM/eSoC observer route, then forced RC1 diagnostics fail before L0, but "
            "the route never emits `wlfw_start`.",
            "",
            "Therefore the next live-relevant unit should not be another credentialed connect "
            "attempt and should not treat forced RC1 enumerate as the primary trigger. First "
            "rebuild or select a bounded Android Wi-Fi service-window route and verify whether "
            "native can produce `wlfw_start`/`wlfw_service_request` at all.",
            "",
            "## Next Gate",
            "",
            f"- Recommended cycle: `{analysis['next_gate']['recommended_cycle']}`",
            f"- Type: {analysis['next_gate']['type']}",
            f"- Focus: {analysis['next_gate']['focus']}",
            "",
            "### Success Markers",
            "",
            *[f"- {item}" for item in analysis["next_gate"]["success_markers"]],
            "",
            "### Guardrails",
            "",
            *[f"- {item}" for item in analysis["next_gate"]["guardrails"]],
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, "
            "partition write, daemon start, Wi-Fi HAL start, scan/connect, credential "
            "handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/"
            "BOOT_DONE spoof, pci-msm debugfs write, global PCI rescan, or platform "
            "bind/unbind.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = classify()
    manifest = {
        "cycle": "V1561",
        "generated_at": now_iso(),
        "decision": analysis["decision"],
        "pass": analysis["pass"],
        "reason": analysis["reason"],
        "host": collect_host_metadata(),
        "input_paths": {
            "v966_wlfw_attribution": rel(V966_MANIFEST),
            "v1560_current_order": rel(V1560_MANIFEST),
            "native_v1496_log": rel(NATIVE_V1496_LOG),
            "native_v1557_log": rel(NATIVE_V1557_LOG),
            "helper_source": rel(HELPER_SOURCE),
            "pid1_wifi_test_source": rel(PID1_WIFI_BOOT_SOURCE),
        },
        "analysis": analysis,
        "out_dir": rel(store.run_dir),
        "device_commands_executed": False,
        "device_mutations": False,
    }
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    if args.write_report:
        write_private_text(repo_path(args.report_path), report)
    write_private_text(repo_path(LATEST_POINTER), rel(store.run_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
