#!/usr/bin/env python3
"""V687 service74-gated PeripheralManager provider + CNSS retry proof.

This proof replays the current service74-positive CNSS retry path with helper
v113. It inserts the Android PeripheralManager provider pair (`pm-service` and
`pm-proxy`) before the fresh `cnss-daemon` retry. It does not start Wi-Fi HAL,
supplicant, hostapd, scan/connect, DHCP, routing, credentials, or external
ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_cnss2_focused_capture_v668 as v668


base = v668.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v687-peripheral-manager-cnss-retry")
base.DEFAULT_HELPER_SHA256 = "60ed7a14d3b33b2f700fb644fd1ccd7a037ac8d9c50db082fa0dea7646965ce9"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v113"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v687-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v687 PeripheralManager provider CNSS retry proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

V535_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
V687_MODE = "wifi-companion-service74-gated-peripheral-manager-cnss-retry-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,"
    "per_mgr,per_proxy,cnss_daemon_retry"
)
MAX_CMDV1_COMMAND_ARGS = 30
V687_USAGE_TOKENS = (
    V687_MODE,
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)

v668.v666.PROPERTY_ROOT = V535_PROPERTY_ROOT

_v666_build_checks = v668._v666_build_checks
_v668_run_live = v668.run_live
_v668_decide = v668.decide
_v668_render_summary = v668.render_summary
_v668_build_manifest = v668.build_manifest


def _set_option(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError:
        command.extend([option, value])
    else:
        command[index + 1] = value


def _keys(live: dict[str, Any]) -> dict[str, str]:
    return v668.v666._merged_helper_keys(live)


def _int_count(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _child_surface(keys: dict[str, str], name: str) -> dict[str, str]:
    return {
        "start_order": keys.get(f"wifi_companion_start.child.{name}.start_order", ""),
        "observable": keys.get(f"wifi_companion_start.child.{name}.observable", ""),
        "exited": keys.get(f"wifi_companion_start.child.{name}.exited", ""),
        "exit_code": keys.get(f"wifi_companion_start.child.{name}.exit_code", ""),
        "signal": keys.get(f"wifi_companion_start.child.{name}.signal", ""),
        "postflight_safe": keys.get(f"wifi_companion_start.child.{name}.postflight_safe", ""),
    }


def _peripheral_surface(keys: dict[str, str]) -> dict[str, Any]:
    children = ("per_mgr", "per_proxy", "cnss_daemon_retry")
    return {
        "order": keys.get("wifi_companion_start.order", ""),
        "peripheral_manager_enabled": keys.get("wifi_companion_start.peripheral_manager.enabled", ""),
        "service74_gate": {
            "seen": keys.get("wifi_companion_start.service74_gate.seen", ""),
            "open": keys.get("wifi_companion_start.service74_gate.open", ""),
            "status": keys.get("wifi_companion_start.service74_gate.status", ""),
            "wait_ms": keys.get("wifi_companion_start.service74_gate.wait_ms", ""),
        },
        "vndservicemanager_readiness": {
            "ready": keys.get("wifi_companion_start.vndservicemanager_readiness.ready", ""),
            "observable": keys.get("wifi_companion_start.vndservicemanager_readiness.observable", ""),
            "fd_summary_captured": keys.get("wifi_companion_start.vndservicemanager_readiness.fd_summary_captured", ""),
        },
        "cnss_retry": {
            "enabled": keys.get("wifi_companion_start.cnss_retry.enabled", ""),
            "initial_cleanup_safe": keys.get("wifi_companion_start.cnss_retry.initial_cleanup_safe", ""),
            "retry_start_order": keys.get("wifi_companion_start.child.cnss_daemon_retry.start_order", ""),
            "retry_observable": keys.get("wifi_companion_start.child.cnss_daemon_retry.observable", ""),
            "retry_postflight_safe": keys.get("wifi_companion_start.child.cnss_daemon_retry.postflight_safe", ""),
        },
        "per_mgr": {
            "observable": keys.get("wifi_companion_start.peripheral_manager.per_mgr.observable", ""),
            "fd_summary_captured": keys.get("wifi_companion_start.peripheral_manager.per_mgr.fd_summary_captured", ""),
            "ready": keys.get("wifi_companion_start.peripheral_manager.per_mgr.ready", ""),
        },
        "per_proxy": {
            "observable": keys.get("wifi_companion_start.peripheral_manager.per_proxy.observable", ""),
            "fd_summary_captured": keys.get("wifi_companion_start.peripheral_manager.per_proxy.fd_summary_captured", ""),
            "ready": keys.get("wifi_companion_start.peripheral_manager.per_proxy.ready", ""),
        },
        "children": {name: _child_surface(keys, name) for name in children},
        "result": keys.get("wifi_companion_start.result", ""),
        "reason": keys.get("wifi_companion_start.reason", ""),
        "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe", ""),
        "all_observable": keys.get("wifi_companion_start.all_observable", ""),
    }


def _advanced(counts: dict[str, Any], markers: dict[str, Any] | None = None) -> bool:
    return any(_int_count(counts.get(name)) > 0 for name in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )) or any(_int_count((markers or {}).get(name)) > 0 for name in ("wlfw", "bdf", "wlan0"))


def _provider_ready(surface: dict[str, Any]) -> bool:
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


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v666_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
        and all(token in usage for token in V687_USAGE_TOKENS)
    )
    base.add_check(
        checks,
        "helper-v113-peripheral-manager-cnss-retry-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v113 service74-gated PeripheralManager/CNSS retry mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V687_MODE in line
            or "peripheral" in line
            or "--property-root" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:14],
        "deploy helper v113 before V687 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = v668.v666.companion_command(args)
    _set_option(command, "--mode", V687_MODE)
    _set_option(command, "--property-root", V535_PROPERTY_ROOT)
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V687 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v668_run_live(args, store, steps, mount_preflight)
    surface = _peripheral_surface(_keys(live))
    live["v687_peripheral_manager_surface"] = surface
    live["v687_peripheral_manager_ready"] = _provider_ready(surface)
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v687-peripheral-manager-cnss-retry-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v113, refresh current-boot prerequisites, then run V687 preflight/live",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v687-peripheral-manager-cnss-retry-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V687", False
    if args.command == "preflight":
        return (
            "v687-peripheral-manager-cnss-retry-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V687 live proof",
            False,
        )
    if not base.approved(args):
        return "v687-peripheral-manager-cnss-retry-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V687 approval", False

    decision, pass_ok, reason, next_step, live_executed = _v668_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v687-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", live_executed
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v687-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V687", live_executed
    if not live.get("companion_executed"):
        return "v687-companion-skipped", False, "companion was skipped by QRTR gate", "inspect QRTR wait evidence", live_executed

    surface = live.get("v687_peripheral_manager_surface") or {}
    counts = live.get("v655_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    cnss_retry = surface.get("cnss_retry") or {}

    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v687-service74-gate-timeout",
            True,
            f"service74_gate={service74_gate}",
            "provider/CNSS retry was correctly withheld; restore lower service74 path before retry",
            live_executed,
        )
    if surface.get("order") != EXPECTED_ORDER or surface.get("peripheral_manager_enabled") != "1":
        return (
            "v687-helper-order-contract-gap",
            False,
            f"surface={surface}",
            "fix helper v113 provider order contract before another live attempt",
            live_executed,
        )
    if vnd_ready.get("ready") != "1" or cnss_retry.get("initial_cleanup_safe") != "1":
        return (
            "v687-vnd-or-initial-cnss-cleanup-gap",
            True,
            f"vnd_ready={vnd_ready} cnss_retry={cnss_retry}",
            "inspect vndservicemanager readiness and initial cnss cleanup before provider retry",
            live_executed,
        )
    if not _provider_ready(surface):
        return (
            "v687-peripheral-manager-provider-start-gap",
            True,
            f"surface={surface}",
            "inspect pm-service/pm-proxy child output before another CNSS retry or Wi-Fi HAL start",
            live_executed,
        )
    if not cnss_retry.get("retry_start_order"):
        return (
            "v687-provider-ready-cnss-retry-withheld",
            True,
            f"surface={surface}",
            "inspect helper provider readiness gate before repeating live proof",
            live_executed,
        )
    if _advanced(counts, markers):
        return (
            "v687-peripheral-manager-wifi-surface-advanced",
            True,
            f"provider ready and lower Wi-Fi markers advanced; counts={counts}; markers={markers}; surface={surface}",
            "classify WLFW/BDF/wlan0 state before scan/connect or external ping",
            live_executed,
        )
    return (
        "v687-peripheral-manager-cnss-retry-gap-persists",
        True,
        f"provider ready and CNSS retry executed, but WLFW/BDF/wlan0 remain absent; counts={counts}; markers={markers}; surface={surface}",
        "classify the remaining pre-WLFW trigger before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v668_render_summary(manifest).replace(
        "# V668 cnss2 Focused Capture Proof",
        "# V687 PeripheralManager Provider CNSS Retry Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v687_peripheral_manager_surface") or {}
    rows: list[list[str]] = []
    for section, values in sorted(surface.items()):
        if isinstance(values, dict):
            for key, value in sorted(values.items()):
                rows.append([section, key, str(value)])
        else:
            rows.append(["surface", section, str(values)])
    return "\n".join([
        text,
        "",
        "## V687 PeripheralManager Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{V535_PROPERTY_ROOT}`",
        f"- mode: `{V687_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- peripheral_manager_ready: `{live.get('v687_peripheral_manager_ready', '')}`",
        "- Wi-Fi HAL, supplicant, scan/connect, DHCP, routing, credentials, and external ping remain blocked.",
        "",
        base.markdown_table(["section", "key", "value"], rows) if rows else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v668_build_manifest(args, store)
    live = manifest.get("live") or {}
    decision, pass_ok, reason, next_step, live_executed = decide(
        args,
        [base.Check(**check) for check in manifest.get("checks", [])],
        live if isinstance(live, dict) else None,
    )
    manifest["decision"] = decision
    manifest["pass"] = pass_ok
    manifest["reason"] = reason
    manifest["next_step"] = next_step
    manifest["device_mutations"] = live_executed
    manifest["cycle"] = "v687"
    manifest["helper_version"] = "v113"
    manifest["property_root"] = V535_PROPERTY_ROOT
    manifest["peripheral_manager_mode"] = V687_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["peripheral_manager_surface"] = live.get("v687_peripheral_manager_surface") if live else {}
    manifest["peripheral_manager_ready"] = bool(live.get("v687_peripheral_manager_ready")) if live else False
    manifest["wifi_hal_start_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_approved"] = [
        "helper v113 service74-gated PeripheralManager provider start-only mode",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "pm-service and pm-proxy start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "V535 private property root bind and property service shim inside helper namespace",
        "read-only cnss2/icnss/QCA6390 focused captures",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "sysfs writes or subsystem state writes",
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "Wi-Fi HAL, wificond, supplicant, or hostapd start",
        "qcwlanstate or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
