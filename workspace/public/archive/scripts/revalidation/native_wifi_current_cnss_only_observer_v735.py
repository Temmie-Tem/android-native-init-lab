#!/usr/bin/env python3
"""V735 current-build CNSS-only observer.

This runner replays the current safe lower path:

    firmware mounts -> subsys_modem holder -> lower companions
      -> cnss_diag + cnss-daemon only -> observe CNSS2/MHI/WLFW

It is intentionally below service-manager, Wi-Fi HAL, wificond, supplicant,
scan/connect, credential use, DHCP, route changes, external ping, esoc0, module
load/unload, and subsystem state writes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_holder_lower_companion_v733 as base


DEFAULT_OUT_DIR = Path("tmp/wifi/v735-current-cnss-only-observer")
DEFAULT_V734_MANIFEST = Path("tmp/wifi/v734-current-post-sysmon-route/manifest.json")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v735-v490-current-run/manifest.json")
DEFAULT_COMPANION_RUNTIME_SEC = 30
PROOF_PREFIX = "/tmp/a90-v735-"
MODE = "wifi-companion-start-only"
EXPECTED_ORDER = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon"
LATEST_POINTER = Path("tmp/wifi/latest-v735-current-cnss-only-observer.txt")


_orig_capture_preflight = base.capture_preflight


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=base.DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=base.DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=DEFAULT_V734_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def configure_base() -> None:
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_COMPANION_RUNTIME_SEC = DEFAULT_COMPANION_RUNTIME_SEC
    base.DEFAULT_V490_MANIFEST = DEFAULT_V490_MANIFEST
    base.PROOF_PREFIX = PROOF_PREFIX
    base.MODE = MODE
    base.EXPECTED_ORDER = EXPECTED_ORDER
    base.helper_command = helper_command
    base.capture_preflight = capture_preflight
    base.active_process_hits = active_process_hits


def helper_command(args: argparse.Namespace) -> list[str]:
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
        MODE,
        "--null-device-mode",
        "dev-null",
        "--vndk-apex-alias-mode",
        "v30-to-system-ext-v30",
        "--linkerconfig-mode",
        "minimal-vendor",
        "--android-selinux-context-mode",
        "service-defaults",
        "--timeout-sec",
        str(args.companion_runtime_sec),
        "--allow-cnss-start-only",
        "--allow-wifi-companion-start-only",
        "--allow-qrtr-ns-readback",
    ]


def active_process_hits(ps_text: str) -> list[str]:
    patterns = (
        "a90-v596-subsys-modem",
        "a90-v729-",
        "a90-v731-",
        "a90-v732-",
        "a90-v733-",
        "a90-v735-",
        "qrtr-ns",
        "rmt_storage",
        "tftp_server",
        "pd-mapper",
        "cnss_diag",
        "cnss-daemon",
        "servicemanager",
        "hwservicemanager",
        "vndservicemanager",
        "wificond",
        "wpa_supplicant",
        "android.hardware.wifi",
    )
    return [line.strip() for line in ps_text.splitlines() if any(pattern in line for pattern in patterns)]


def capture_preflight(args: argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = _orig_capture_preflight(args, store, steps)
    base.run_step(args, store, steps, "proc-modules-before", ["cat", "/proc/modules"], 20.0)
    base.run_step(args, store, steps, "wlan-module-ls-before", ["run", args.toybox, "ls", "-l", "/sys/module/wlan"], 10.0)
    base.run_step(args, store, steps, "wlan-parameters-ls-before", ["run", args.toybox, "ls", "-l", "/sys/module/wlan/parameters"], 10.0)
    base.run_step(args, store, steps, "cnss2-driver-ls-before", ["run", args.toybox, "ls", "-l", "/sys/bus/platform/drivers/cnss2"], 10.0)
    base.run_step(args, store, steps, "icnss-device-ls-before", ["run", args.toybox, "ls", "-l", "/sys/devices/platform/soc/18800000.qcom,icnss"], 10.0)
    return preflight


def readback_summary(keys: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    service_events = 0
    end_of_list = 0
    timeouts = 0
    qmi_attempted = 0
    for index in (0, 1):
        prefix = f"wifi_companion_qrtr_readback.case_{index}"
        row = {
            "case": index,
            "service": keys.get(f"{prefix}.service", ""),
            "instance": keys.get(f"{prefix}.instance", ""),
            "socket_rc": keys.get(f"{prefix}.socket.rc", ""),
            "new_lookup_rc": keys.get(f"{prefix}.new_lookup_send.rc", ""),
            "del_lookup_rc": keys.get(f"{prefix}.del_lookup_send.rc", ""),
            "events": _int(keys.get(f"{prefix}.readback.events")),
            "service_events": _int(keys.get(f"{prefix}.readback.service_events")),
            "end_of_list": _int(keys.get(f"{prefix}.readback.end_of_list")),
            "timeout": _int(keys.get(f"{prefix}.readback.timeout")),
            "qmi_attempted": _int(keys.get(f"{prefix}.qmi_attempted")),
            "status": keys.get(f"{prefix}.status", ""),
        }
        rows.append(row)
        service_events += int(row["service_events"])
        end_of_list += int(row["end_of_list"])
        timeouts += int(row["timeout"])
        qmi_attempted += int(row["qmi_attempted"])
    fallback_events = _int(keys.get("qrtr_readback.service_events"))
    fallback_timeouts = _int(keys.get("qrtr_readback.timeouts"))
    fallback_qmi = _int(keys.get("qrtr_readback.qmi_attempted"))
    return {
        "allowed": keys.get("wifi_companion_qrtr_readback.allowed", ""),
        "send_attempted": keys.get("wifi_companion_qrtr_readback.send_attempted", ""),
        "result": keys.get("wifi_companion_qrtr_readback.result", ""),
        "service_events": service_events or fallback_events,
        "end_of_list": end_of_list,
        "timeouts": timeouts or fallback_timeouts,
        "qmi_attempted": qmi_attempted or fallback_qmi,
        "rows": rows,
    }


def normalize_helper(helper: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(helper)
    keys = normalized.get("keys") or {}
    if not isinstance(keys, dict):
        keys = {}
    cnss_diag_started = (
        _int(keys.get("wifi_hal_composite_start.child.cnss_diag.child_started"))
        or _int(keys.get("wifi_companion_start.child.cnss_diag.observable"))
    )
    cnss_daemon_started = (
        _int(keys.get("wifi_hal_composite_start.child.cnss_daemon.child_started"))
        or _int(keys.get("wifi_companion_start.child.cnss_daemon.observable"))
    )
    normalized["cnss_diag"] = max(_int(str(normalized.get("cnss_diag"))), cnss_diag_started)
    normalized["cnss_daemon"] = max(_int(str(normalized.get("cnss_daemon"))), cnss_daemon_started)
    normalized["cnss_diag_pid"] = keys.get("wifi_hal_composite_start.child.cnss_diag.pid", "")
    normalized["cnss_daemon_pid"] = keys.get("wifi_hal_composite_start.child.cnss_daemon.pid", "")
    return normalized


def _int(value: str | None) -> int:
    try:
        return int(value or "0", 0)
    except ValueError:
        return 0


def wlan_surface(steps: list[dict[str, Any]], live: dict[str, Any] | None) -> dict[str, Any]:
    proc_modules = base.step_payload(steps, "proc-modules-before")
    wlan_ls = base.step_payload(steps, "wlan-module-ls-before")
    params_ls = base.step_payload(steps, "wlan-parameters-ls-before")
    cnss2_ls = base.step_payload(steps, "cnss2-driver-ls-before")
    icnss_ls = base.step_payload(steps, "icnss-device-ls-before")
    return {
        "proc_modules_has_wlan": any(line.split()[:1] == ["wlan"] for line in proc_modules.splitlines()),
        "sys_module_wlan_exists": "No such file" not in wlan_ls and bool(wlan_ls.strip()),
        "sys_module_wlan_parameters_visible": "No such file" not in params_ls and bool(params_ls.strip()),
        "cnss2_driver_visible": "No such file" not in cnss2_ls and bool(cnss2_ls.strip()),
        "icnss_device_visible": "No such file" not in icnss_ls and bool(icnss_ls.strip()),
        "wlan_firmware_visible": {
            path: value
            for path, value in ((live or {}).get("wlan_firmware_visible") or {}).items()
            if value
        },
    }


def preflight_blockers(args: argparse.Namespace,
                       steps: list[dict[str, Any]],
                       preflight: dict[str, Any],
                       v731: dict[str, Any],
                       v732: dict[str, Any],
                       v734: dict[str, Any],
                       v490: dict[str, Any]) -> list[str]:
    blockers = base.preflight_blockers(args, steps, preflight, v731, v732, v490)
    if v734.get("decision") != "v734-route-current-build-cnss-only-replay":
        blockers.append("v734-route-reference-missing")
    if not (10 <= args.companion_runtime_sec <= 30):
        blockers.append("companion-runtime-out-of-range")
    return blockers


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 preflight: dict[str, Any],
                 v731: dict[str, Any],
                 v732: dict[str, Any],
                 v734: dict[str, Any],
                 v490: dict[str, Any],
                 live: dict[str, Any] | None,
                 blockers: list[str]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "refresh V401/V490 current boot, then run V735 CNSS-only observer",
        }]
    checks: list[dict[str, Any]] = [
        {
            "name": "preflight-blockers",
            "status": "pass" if not blockers else "blocked",
            "detail": {"blockers": blockers},
            "next_step": "clear blockers before V735 live",
        },
        {
            "name": "references",
            "status": "pass" if v731.get("decision") == "v731-firmware-mounted-modem-holder-qrtr-rx-pass"
            and v732.get("decision") == "v732-cnss2-mhi-holder-window-cnss2-gap-classified"
            and v734.get("decision") == "v734-route-current-build-cnss-only-replay"
            and v490.get("decision") == "v490-selinux-policy-load-proof-pass" else "review",
            "detail": {
                "v731": v731.get("decision"),
                "v732": v732.get("decision"),
                "v734": v734.get("decision"),
                "v490": v490.get("decision"),
            },
            "next_step": "refresh stale prerequisite evidence before interpreting V735",
        },
    ]
    if not live:
        return checks
    counts = ((live.get("markers") or {}).get("counts") or {})
    helper = live.get("helper_result") or {}
    reboot = live.get("reboot_cleanup") or {}
    readback = live.get("qrtr_readback") or {}
    forbidden_helper_values = {
        key: helper.get(key)
        for key in ("service_manager", "wifi_hal", "wificond", "scan_connect_linkup", "external_ping")
    }
    checks.extend([
        {
            "name": "firmware-mounted",
            "status": "pass" if all((live.get("mounted_hits") or {}).values()) and any((live.get("modem_blob_visible") or {}).values()) else "blocked",
            "detail": {"mounted_hits": live.get("mounted_hits"), "modem_blob_visible": live.get("modem_blob_visible")},
            "next_step": "fix firmware mount parity before retry",
        },
        {
            "name": "modem-holder-window",
            "status": "pass" if live.get("holder_opened") and "ONLINE" in {live.get("mss_after_holder"), live.get("mss_after_companion")} and (live.get("qrtr_rx_wait") or {}).get("seen") else "finding",
            "detail": {"holder_opened": live.get("holder_opened"), "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_companion")], "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_companion")], "qrtr_rx": (live.get("qrtr_rx_wait") or {}).get("seen")},
            "next_step": "if missing, compare V731/V732 current deltas before companion retry",
        },
        {
            "name": "wlan-static-surface",
            "status": "pass" if live.get("wlan_surface", {}).get("sys_module_wlan_exists") and not live.get("wlan_surface", {}).get("proc_modules_has_wlan") else "review",
            "detail": live.get("wlan_surface"),
            "next_step": "treat wlan as static/built-in unless Android reference proves a loadable wlan.ko",
        },
        {
            "name": "cnss-only-contract",
            "status": "pass" if helper.get("order") == EXPECTED_ORDER and helper.get("child_started") == 6 and helper.get("all_observable") == 1 and helper.get("all_postflight_safe") == 1 and helper.get("cnss_diag") == 1 and helper.get("cnss_daemon") == 1 else "blocked",
            "detail": {"mode": helper.get("mode"), "order": helper.get("order"), "child_started": helper.get("child_started"), "all_observable": helper.get("all_observable"), "all_postflight_safe": helper.get("all_postflight_safe"), "cnss_diag": helper.get("cnss_diag"), "cnss_diag_pid": helper.get("cnss_diag_pid"), "cnss_daemon": helper.get("cnss_daemon"), "cnss_daemon_pid": helper.get("cnss_daemon_pid"), "result": helper.get("result")},
            "next_step": "inspect helper transcript before interpreting kernel markers",
        },
        {
            "name": "forbidden-helper-actions",
            "status": "pass" if all(_int(str(value)) == 0 for value in forbidden_helper_values.values()) else "blocked",
            "detail": forbidden_helper_values,
            "next_step": "stop if helper crossed into service-manager/HAL/connect",
        },
        {
            "name": "qrtr-readback-guard",
            "status": "pass" if _int(str(readback.get("qmi_attempted"))) == 0 else "blocked",
            "detail": readback,
            "next_step": "stop if QRTR readback sent QMI payloads",
        },
        {
            "name": "cnss2-mhi-wlfw-progression",
            "status": "pass" if counts.get("mhi", 0) or counts.get("qca6390", 0) or counts.get("wlfw", 0) or counts.get("wlan0", 0) or readback.get("service_events", 0) else "finding",
            "detail": {"markers": {key: counts.get(key, 0) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0")}, "qrtr_services": live.get("qrtr_services_after_companion"), "readback_service_events": readback.get("service_events")},
            "next_step": "if absent, the remaining gap is below HAL/connect and likely modem/WLAN-PD/MHI publication",
        },
        {
            "name": "kernel-warning-review",
            "status": "blocked" if counts.get("kernel_warning", 0) else "pass",
            "detail": {"kernel_warning": counts.get("kernel_warning", 0), "first": ((live.get("markers") or {}).get("first_lines") or {}).get("kernel_warning", "")},
            "next_step": "do not repeat or widen if warning appears",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if reboot.get("version_seen") and reboot.get("status_healthy") else "blocked",
            "detail": reboot,
            "next_step": "manually verify native if cleanup did not prove health",
        },
    ])
    return checks


def decide(args: argparse.Namespace, checks: list[dict[str, Any]], live: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v735-current-cnss-only-observer-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current V401/V490 and run bounded V735 live observer",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v735-current-cnss-only-observer-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear blocker before retry",
        )
    if not live:
        return (
            "v735-current-cnss-only-observer-preflight-ready",
            True,
            "preflight ready",
            "run live V735 observer",
        )
    counts = ((live.get("markers") or {}).get("counts") or {})
    services = live.get("qrtr_services_after_companion") or {}
    readback = live.get("qrtr_readback") or {}
    if counts.get("wlan0", 0) or counts.get("wlfw", 0) or services.get("69", 0) or readback.get("service_events", 0):
        return (
            "v735-current-cnss-only-wlfw-advance",
            True,
            "CNSS-only window produced WLFW/service69 or wlan0 evidence without HAL/connect",
            "capture BDF/fw-ready/interface state before Wi-Fi HAL or connect",
        )
    if counts.get("mhi", 0) or counts.get("qca6390", 0):
        return (
            "v735-current-cnss-only-mhi-advance",
            True,
            "CNSS-only window produced MHI/QCA6390 evidence but no WLFW/service69",
            "classify MHI-to-WLFW firmware/runtime gap before HAL/connect",
        )
    if counts.get("service_notifier", 0) or counts.get("wlan_pd", 0) or services.get("180", 0) or services.get("74", 0):
        return (
            "v735-current-cnss-only-service-publication-advance",
            True,
            "CNSS-only window produced service publication evidence but no MHI/WLFW",
            "classify WLAN-PD-to-MHI gap before HAL/connect",
        )
    if counts.get("qrtr_tx", 0) or counts.get("sysmon_qmi", 0):
        return (
            "v735-current-cnss-only-sysmon-gap-classified",
            True,
            "CNSS-only window restored QRTR TX/sysmon but no service publication, MHI, WLFW, or wlan0",
            "focus next on modem/WLAN-PD publication or CNSS2 MHI trigger; still below HAL/connect",
        )
    return (
        "v735-current-cnss-only-no-post-rx-advance",
        True,
        "modem QRTR RX returned but CNSS-only replay did not progress to sysmon/service/MHI/WLFW",
        "compare helper output and current modem lower prerequisites before widening live work",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    readback = live.get("qrtr_readback") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["mounted_hits", json.dumps(live.get("mounted_hits", {}), sort_keys=True)],
        ["wlan_surface", json.dumps(live.get("wlan_surface", {}), sort_keys=True)],
        ["holder_opened", live.get("holder_opened", "")],
        ["mss", f"{live.get('mss_before', '')}->{live.get('mss_after_holder', '')}->{live.get('mss_after_companion', '')}"],
        ["mdm3", f"{live.get('mdm3_before', '')}->{live.get('mdm3_after_holder', '')}->{live.get('mdm3_after_companion', '')}"],
        ["helper", json.dumps({key: helper.get(key) for key in ("mode", "order", "child_started", "all_observable", "all_postflight_safe", "cnss_diag", "cnss_diag_pid", "cnss_daemon", "cnss_daemon_pid", "service_manager", "wifi_hal", "result")}, sort_keys=True)],
        ["qrtr_services", json.dumps(live.get("qrtr_services_after_companion", {}), sort_keys=True)],
        ["qrtr_readback", json.dumps({key: readback.get(key) for key in ("allowed", "send_attempted", "result", "service_events", "end_of_list", "timeouts", "qmi_attempted")}, sort_keys=True)],
        ["reboot_cleanup", json.dumps(live.get("reboot_cleanup", {}), sort_keys=True)],
    ]
    marker_rows = [[name, str(counts.get(name, 0))] for name in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "rpmsg", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "kernel_warning")]
    readback_rows = [
        [
            str(row.get("case", "")),
            str(row.get("service", "")),
            str(row.get("instance", "")),
            str(row.get("service_events", "")),
            str(row.get("end_of_list", "")),
            str(row.get("timeout", "")),
            str(row.get("qmi_attempted", "")),
            str(row.get("status", "")),
        ]
        for row in readback.get("rows", [])
    ]
    return "\n".join([
        "# V735 Current CNSS-only Observer",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- firmware_mounts_executed: `{manifest['firmware_mounts_executed']}`",
        f"- subsys_modem_opened: `{manifest['subsys_modem_opened']}`",
        f"- lower_companion_start_executed: `{manifest['lower_companion_start_executed']}`",
        f"- cnss_diag_start_executed: `{manifest['cnss_diag_start_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        base.markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## State Summary",
        "",
        base.markdown_table(["key", "value"], state_rows),
        "",
        "## Dmesg Marker Counts",
        "",
        base.markdown_table(["marker", "count"], marker_rows),
        "",
        "## QRTR Readback",
        "",
        base.markdown_table(["case", "service", "instance", "service_events", "end_of_list", "timeout", "qmi_attempted", "status"], readback_rows) if readback_rows else "- none",
    ])


def build_manifest(args: argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    v731 = base.load_json_if_exists(args.v731_manifest)
    v732 = base.load_json_if_exists(args.v732_manifest)
    v734 = base.load_json_if_exists(args.v734_manifest)
    v490 = base.load_json_if_exists(args.v490_manifest)
    preflight: dict[str, Any] = {}
    live: dict[str, Any] | None = None
    blockers: list[str] = []
    if args.command == "run":
        preflight = capture_preflight(args, store, steps)
        blockers = preflight_blockers(args, steps, preflight, v731, v732, v734, v490)
        if not blockers:
            live = base.run_live(args, store, steps, preflight)
            live["helper_result"] = normalize_helper(live.get("helper_result") or {})
            helper_keys = (live.get("helper_result") or {}).get("keys") or {}
            live["qrtr_readback"] = readback_summary(helper_keys)
            live["wlan_surface"] = wlan_surface(steps, live)
    checks = build_checks(args, steps, preflight, v731, v732, v734, v490, live, blockers)
    decision, pass_ok, reason, next_step = decide(args, checks, live)
    helper = (live or {}).get("helper_result") or {}
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v735",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": base.collect_host_metadata(),
        "v731": {"decision": v731.get("decision"), "pass": v731.get("pass"), "path": v731.get("path", str(base.repo_path(args.v731_manifest)))},
        "v732": {"decision": v732.get("decision"), "pass": v732.get("pass"), "path": v732.get("path", str(base.repo_path(args.v732_manifest)))},
        "v734": {"decision": v734.get("decision"), "pass": v734.get("pass"), "path": v734.get("path", str(base.repo_path(args.v734_manifest)))},
        "v490": {"decision": v490.get("decision"), "pass": v490.get("pass"), "path": v490.get("path", str(base.repo_path(args.v490_manifest)))},
        "preflight": preflight,
        "steps": steps,
        "checks": checks,
        "live": live or {},
        "device_commands_executed": args.command == "run",
        "firmware_mounts_executed": bool(live),
        "subsys_modem_open_attempted": bool(live),
        "subsys_modem_opened": bool((live or {}).get("holder_opened")),
        "esoc0_node_created": False,
        "esoc0_open_executed": False,
        "subsystem_writes_executed": False,
        "module_load_unload_executed": False,
        "lower_companion_start_executed": bool((live or {}).get("companion_executed")),
        "cnss_diag_start_executed": bool(_int(str(helper.get("cnss_diag")))),
        "cnss_daemon_start_executed": bool(_int(str(helper.get("cnss_daemon")))),
        "daemon_or_hal_start_executed": bool(_int(str(helper.get("cnss_daemon")))),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "reboot_cleanup_executed": bool(live),
    }


def main() -> int:
    configure_base()
    args = parse_args()
    store = base.EvidenceStore(base.repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    base.write_private_text(base.repo_path(LATEST_POINTER), str(store.run_dir.relative_to(base.repo_path("."))) + "\n")
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
