#!/usr/bin/env python3
"""V802 provider-first context plus bounded boot_wlan observe.

This wraps the V752 CNSS-then-boot_wlan runner but replaces the lower CNSS
companion with the V800 provider-first service74/PeripheralManager/CNSS retry
context. It still does not start Wi-Fi HAL, supplicant, scan/connect, use
credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_cnss_then_boot_wlan_v752 as v752
from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text


V802_OUT_DIR = Path("tmp/wifi/v802-provider-first-boot-wlan-observe")
V802_LATEST = Path("tmp/wifi/latest-v802-provider-first-boot-wlan-observe.txt")
V801_MANIFEST = Path("tmp/wifi/v801-v800-edge-route-classifier/manifest.json")
V802_MODE = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only"
V802_EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,per_mgr,vndservice_query,per_proxy,"
    "vndservice_query,cnss_daemon_retry"
)
REAL_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
REAL_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"

v752.DEFAULT_OUT_DIR = V802_OUT_DIR
v752.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
v752.DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
v752.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
v752.MODE = V802_MODE
v752.EXPECTED_ORDER = V802_EXPECTED_ORDER
v752.PROOF_PREFIX = "/tmp/a90-v802-"

_v752_preflight_blockers = v752.preflight_blockers
_v752_build_checks = v752.build_checks
_v752_decide = v752.decide
_v752_render_summary = v752.render_summary
_v752_build_manifest = v752.build_manifest


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def helper_command(args: v752.argparse.Namespace) -> list[str]:
    return [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        V802_MODE,
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "copy-real",
        "--android-selinux-context-mode",
        "service-defaults",
        "--timeout-sec",
        str(args.cnss_runtime_sec),
        "--allow-cnss-start-only",
        "--allow-wifi-companion-start-only",
        "--allow-qrtr-ns-readback",
        "--linkerconfig-source",
        REAL_LD_CONFIG,
        "--apex-libraries-source",
        REAL_APEX_LIBRARIES,
        "--allow-service-manager-start-only",
        "--property-root",
        PROPERTY_ROOT,
    ]


def parse_helper_payload(text: str) -> dict[str, Any]:
    keys = v752.lower.parse_keys(text)
    result = v752.lower.helper_surface(text)
    children = {}
    for name in ("servicemanager", "hwservicemanager", "vndservicemanager", "per_mgr", "per_proxy", "cnss_daemon_retry"):
        prefix = f"wifi_companion_start.child.{name}."
        children[name] = {
            "start_order": keys.get(prefix + "start_order", ""),
            "observable": keys.get(prefix + "observable", ""),
            "exited": keys.get(prefix + "exited", ""),
            "exit_code": keys.get(prefix + "exit_code", ""),
            "signal": keys.get(prefix + "signal", ""),
            "postflight_safe": keys.get(prefix + "postflight_safe", ""),
        }
    query_phases = {}
    for phase in ("after_per_mgr_probe", "after_per_proxy_probe"):
        prefix = f"wifi_vndservice_query.{phase}."
        query_phases[phase] = {
            "begin": keys.get(prefix + "begin", ""),
            "end": keys.get(prefix + "end", ""),
            "exit_code": keys.get(prefix + "exit_code", ""),
            "signal": keys.get(prefix + "signal", ""),
            "timed_out": keys.get(prefix + "timed_out", ""),
            "vendor_qcom_peripheral_manager_seen": keys.get(prefix + "vendor_qcom_peripheral_manager_seen", ""),
            "peripheral_seen": keys.get(prefix + "peripheral_seen", ""),
            "result": keys.get(prefix + "result", ""),
            "reason": keys.get(prefix + "reason", ""),
        }
    service74_gate = {
        "seen": keys.get("wifi_companion_start.service74_gate.seen", ""),
        "open": keys.get("wifi_companion_start.service74_gate.open", ""),
        "status": keys.get("wifi_companion_start.service74_gate.status", ""),
        "wait_ms": keys.get("wifi_companion_start.service74_gate.wait_ms", ""),
    }
    provider_query_exact = any(
        phase.get("vendor_qcom_peripheral_manager_seen") == "1"
        for phase in query_phases.values()
    )
    cnss_retry_child = children["cnss_daemon_retry"]
    cnss_retry = {
        "enabled": keys.get("wifi_companion_start.cnss_retry.enabled", ""),
        "initial_cleanup_safe": keys.get("wifi_companion_start.cnss_retry.initial_cleanup_safe", ""),
        "retry_start_order": (
            keys.get("wifi_companion_start.cnss_retry.retry_start_order", "")
            or cnss_retry_child.get("start_order", "")
        ),
        "retry_observable": (
            keys.get("wifi_companion_start.cnss_retry.retry_observable", "")
            or cnss_retry_child.get("observable", "")
        ),
        "retry_postflight_safe": (
            keys.get("wifi_companion_start.cnss_retry.retry_postflight_safe", "")
            or cnss_retry_child.get("postflight_safe", "")
        ),
    }
    result.update({
        "keys": keys,
        "children": children,
        "service74_gate": service74_gate,
        "vndservice_query": {"phases": query_phases},
        "provider_query_exact": provider_query_exact,
        "initial_cnss_suppressed": keys.get("wifi_companion_start.initial_cnss_daemon.suppressed", "") == "1",
        "cnss_retry": cnss_retry,
        "cnss_retry_started": bool(cnss_retry["retry_start_order"]),
        "cnss_retry_signal": cnss_retry_child.get("signal", ""),
        "service_manager": max(
            result.get("service_manager", 0),
            v752.int_key(keys, "wifi_companion_start.child.servicemanager.observable"),
            v752.int_key(keys, "wifi_companion_start.child.hwservicemanager.observable"),
            v752.int_key(keys, "wifi_companion_start.child.vndservicemanager.observable"),
        ),
        "cnss_daemon": max(result.get("cnss_daemon", 0), v752.int_key(keys, "wifi_companion_start.child.cnss_daemon_retry.observable")),
    })
    return result


def v801_ready() -> bool:
    manifest = load_json_if_exists(V801_MANIFEST)
    return (
        manifest.get("decision") == "v801-provider-first-boot-wlan-observe-selected"
        and bool(manifest.get("pass"))
    )


def preflight_blockers(args: v752.argparse.Namespace,
                       steps: list[dict[str, Any]],
                       preflight: dict[str, Any],
                       v731: dict[str, Any],
                       v732: dict[str, Any],
                       v490: dict[str, Any],
                       v751: dict[str, Any]) -> list[str]:
    blockers = _v752_preflight_blockers(args, steps, preflight, v731, v732, v490, v751)
    if not v801_ready():
        blockers.append("v801-route-reference-missing")
    return sorted(set(blockers))


def _provider_context_ok(helper: dict[str, Any]) -> bool:
    forbidden = (
        int(helper.get("wifi_hal") or 0),
        int(helper.get("wificond") or 0),
        int(helper.get("scan_connect_linkup") or 0),
        int(helper.get("external_ping") or 0),
        int(helper.get("qmi_attempted") or 0),
    )
    return (
        helper.get("order") == V802_EXPECTED_ORDER
        and helper.get("service74_gate", {}).get("open") == "1"
        and helper.get("provider_query_exact")
        and helper.get("initial_cnss_suppressed")
        and helper.get("cnss_retry_started")
        and helper.get("all_postflight_safe") == 1
        and all(value == 0 for value in forbidden)
    )


def _known_asoc_warning(first_line: str) -> bool:
    return "pm_qos_add_request() called for already added request" in first_line


def build_checks(args: v752.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 v731: dict[str, Any],
                 v732: dict[str, Any],
                 v490: dict[str, Any],
                 v751: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    checks = _v752_build_checks(args, steps, preflight, v731, v732, v490, v751, live, blockers)
    for check in checks:
        check["name"] = str(check["name"]).replace("v751-reference", "v751-boot-wlan-reference")
        check["next_step"] = str(check["next_step"]).replace("V752", "V802")
    if args.command != "plan":
        checks.append({
            "name": "v801-route-reference",
            "status": "pass" if v801_ready() else "blocked",
            "detail": {"path": str(repo_path(V801_MANIFEST)), "ready": v801_ready()},
            "next_step": "complete V801 route classifier before V802",
        })
    if not live:
        return checks
    helper = live.get("helper_result") or {}
    for check in checks:
        if check["name"] == "cnss-companion-contract":
            check["name"] = "provider-first-context-contract"
            check["status"] = "pass" if _provider_context_ok(helper) else "blocked"
            check["detail"] = {
                "mode": helper.get("mode"),
                "order": helper.get("order"),
                "service74_gate": helper.get("service74_gate"),
                "provider_query_exact": helper.get("provider_query_exact"),
                "initial_cnss_suppressed": helper.get("initial_cnss_suppressed"),
                "cnss_retry": helper.get("cnss_retry"),
                "children": helper.get("children"),
                "result": helper.get("result"),
            }
            check["next_step"] = "inspect provider-first transcript before interpreting boot_wlan result"
        elif check["name"] == "forbidden-helper-actions":
            forbidden = {
                key: helper.get(key)
                for key in ("wifi_hal", "wificond", "scan_connect_linkup", "external_ping", "qmi_attempted")
            }
            check["status"] = "pass" if all(int(value or 0) == 0 for value in forbidden.values()) else "blocked"
            check["detail"] = forbidden
            check["next_step"] = "stop if helper crossed into HAL/connect or QMI payload"
        elif check["name"] == "kernel-warning-review":
            detail = check.get("detail") if isinstance(check.get("detail"), dict) else {}
            first_line = str(detail.get("first", ""))
            if check.get("status") == "blocked" and _known_asoc_warning(first_line):
                detail["known_asoc_pm_qos_warning"] = True
                detail["classified_by"] = "V792 known ASoC warning guard"
                check["status"] = "finding"
                check["detail"] = detail
                check["next_step"] = "continue only with bounded observability; do not widen to HAL/connect from this warning alone"
    return checks


def decide(args: v752.argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v802-provider-first-boot-wlan-observe-plan-ready",
            True,
            "plan-only; no device command executed",
            "run preflight, then gated V802 live proof",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return "v802-provider-first-boot-wlan-observe-blocked", False, "blocked by " + ", ".join(blocked), "clear blocker before retry"
    if not live:
        return (
            "v802-provider-first-boot-wlan-observe-preflight-ready",
            True,
            "preflight ready; live proof remains below Wi-Fi HAL/connect",
            "run with --allow-cnss-then-boot-wlan --assume-yes",
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    services = live.get("qrtr_services_after_boot") or {}
    if live.get("wlan0_after") or live.get("wiphy_after"):
        return (
            "v802-provider-first-boot-wlan-netdev-appeared",
            True,
            "provider-first plus boot_wlan produced wlan0/wiphy without HAL or scan/connect",
            "plan link-readiness and scan-only gate before credential use",
        )
    if counts.get("wlan_driver_loaded", 0) or counts.get("icnss_qmi_connected", 0) or counts.get("fw_ready", 0) or counts.get("wlfw", 0) or counts.get("bdf", 0) or services.get("69", 0):
        return (
            "v802-provider-first-boot-wlan-driver-advanced",
            True,
            "provider-first plus boot_wlan advanced WLAN driver/WLFW markers but no netdev appeared",
            "classify driver-ready-to-netdev gap before HAL/connect",
        )
    if counts.get("wlan_loading", 0) or counts.get("hdd_state_major", 0) or counts.get("qcwlanstate", 0):
        return (
            "v802-provider-first-boot-wlan-hdd-init-still-stalls",
            True,
            "provider-first context plus boot_wlan still reaches only HDD init/qcwlanstate; driver-loaded/QMI/FW-ready/netdev remain absent",
            "next gate should instrument HDD/PLD init prerequisites inside provider-first boot_wlan window",
        )
    return (
        "v802-provider-first-boot-wlan-no-trigger-progress",
        True,
        "provider-first context plus boot_wlan executed but produced no WLAN trigger markers",
        "inspect helper and boot transcript before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v752_render_summary(manifest)
    text = text.replace("# V752 CNSS then Boot WLAN Proof", "# V802 Provider-first Boot WLAN Observe Proof")
    text = text.replace("V752", "V802").replace("CNSS then boot_wlan", "Provider-first plus boot_wlan")
    live = manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    rows = [
        ["mode", helper.get("mode", "")],
        ["order", helper.get("order", "")],
        ["service74_gate", json.dumps(helper.get("service74_gate", {}), sort_keys=True)],
        ["provider_query_exact", str(helper.get("provider_query_exact", ""))],
        ["initial_cnss_suppressed", str(helper.get("initial_cnss_suppressed", ""))],
        ["cnss_retry", json.dumps(helper.get("cnss_retry", {}), sort_keys=True)],
        ["cnss_retry_signal", str(helper.get("cnss_retry_signal", ""))],
    ]
    return "\n".join([
        text,
        "",
        "## V802 Provider-first Context",
        "",
        v752.markdown_table(["key", "value"], rows),
        "",
    ])


def build_manifest(args: v752.argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    manifest = _v752_build_manifest(args, store)
    live = manifest.get("live") or {}
    helper = live.get("helper_result") if isinstance(live, dict) else {}
    manifest["cycle"] = "v802"
    manifest["v801"] = {
        "path": str(repo_path(V801_MANIFEST)),
        "ready": v801_ready(),
    }
    manifest["decision"] = str(manifest.get("decision", "")).replace("v752", "v802")
    manifest["reason"] = str(manifest.get("reason", "")).replace("CNSS then boot_wlan", "provider-first context plus boot_wlan")
    manifest["next_step"] = str(manifest.get("next_step", "")).replace("V752", "V802")
    manifest["provider_first_context_executed"] = bool(helper and helper.get("provider_query_exact"))
    manifest["service_manager_start_executed"] = bool(helper and int(helper.get("service_manager") or 0))
    manifest["daemon_or_hal_start_executed"] = bool(helper and (int(helper.get("cnss_daemon") or 0) or int(helper.get("service_manager") or 0)))
    manifest["wifi_hal_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["credential_use_executed"] = False
    manifest["dhcp_route_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = v752.parse_args()
    if args.companion_runtime_sec is None:
        args.companion_runtime_sec = args.cnss_runtime_sec
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    write_private_text(repo_path(V802_LATEST), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"provider_first_context_executed: {manifest['provider_first_context_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"dhcp_route_executed: {manifest['dhcp_route_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"boot_wlan_write_executed: {manifest['boot_wlan_write_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


v752.helper_command = helper_command
v752.parse_helper_payload = parse_helper_payload
v752.preflight_blockers = preflight_blockers
v752.build_checks = build_checks
v752.decide = decide
v752.render_summary = render_summary
v752.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(main())
