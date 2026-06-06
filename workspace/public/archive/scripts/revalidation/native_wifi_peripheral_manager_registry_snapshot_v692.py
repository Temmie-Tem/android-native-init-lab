#!/usr/bin/env python3
"""V692 service74-gated PeripheralManager provider registry snapshot proof.

This proof replays the current service74-positive CNSS retry path with helper
v116. It inserts the Android PeripheralManager provider pair (`pm-service` and
`pm-proxy`) before the fresh `cnss-daemon` retry and captures bounded
vndservicemanager/binder registry snapshots around the provider start. It does
not start Wi-Fi HAL, supplicant, hostapd, scan/connect, DHCP, routing,
credentials, or external ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_cnss2_focused_capture_v668 as v668


base = v668.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v692-peripheral-manager-registry-snapshot")
base.DEFAULT_HELPER_SHA256 = "cce86ee252a045c7b8127b5e566abcb3ef24cdd89ac16d4592636838b9eb3e2b"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v116"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v692-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v692 PeripheralManager provider registry snapshot proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

V535_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
V692_MODE = "wifi-companion-service74-gated-peripheral-manager-cnss-retry-registry-snapshot-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,"
    "per_mgr,per_proxy,cnss_daemon_retry,registry_snapshot"
)
MAX_CMDV1_COMMAND_ARGS = 30
V692_USAGE_TOKENS = (
    V692_MODE,
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)
EXPECTED_PRIVATE_ACKS = {
    ("vendor.peripheral.SDX50M.state", "OFFLINE"),
    ("vendor.peripheral.modem.state", "OFFLINE"),
}
REGISTRY_PHASES = (
    "before_initial_cnss_cleanup",
    "after_initial_cnss_cleanup",
    "after_per_mgr_probe",
    "after_per_proxy_probe",
    "window",
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
        "selinux_context_mode": keys.get(f"wifi_hal_composite_child.{name}.selinux_context_mode", ""),
        "selinux_exec_target_context": keys.get(f"wifi_hal_composite_child.{name}.selinux_exec.target_context", ""),
        "selinux_exec_skipped": keys.get(f"wifi_hal_composite_child.{name}.selinux_exec.skipped", ""),
        "selinux_exec_reason": keys.get(f"wifi_hal_composite_child.{name}.selinux_exec.reason", ""),
        "selinux_exec_ok": keys.get(f"wifi_hal_composite_child.{name}.selinux_exec.ok", ""),
        "selinux_exec_errno": keys.get(f"wifi_hal_composite_child.{name}.selinux_exec.errno", ""),
        "selinux_exec_error": keys.get(f"wifi_hal_composite_child.{name}.selinux_exec.error", ""),
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


def _property_shim_surface(keys: dict[str, str]) -> dict[str, Any]:
    prefix = "wifi_hal_composite_start.property_service_shim."
    try:
        request_count = int(keys.get(prefix + "request_count") or "0")
    except ValueError:
        request_count = 0
    requests: list[dict[str, str]] = []
    for index in range(1, request_count + 1):
        requests.append({
            "index": str(index),
            "name": keys.get(f"{prefix}request.{index}.name", ""),
            "value": keys.get(f"{prefix}request.{index}.value", ""),
            "allowed": keys.get(f"{prefix}request.{index}.allowed", ""),
            "result": keys.get(f"{prefix}request.{index}.result", ""),
        })
    return {
        "started": keys.get(prefix + "started", ""),
        "allowlist": keys.get(prefix + "allowlist", ""),
        "request_count": str(request_count),
        "requests": requests,
    }


def _registry_snapshot_surface(keys: dict[str, str]) -> dict[str, Any]:
    phases: dict[str, dict[str, str]] = {}
    for phase in REGISTRY_PHASES:
        phases[phase] = {
            "begin": keys.get(f"wifi_registry_snapshot.{phase}.begin", ""),
            "end": keys.get(f"wifi_registry_snapshot.{phase}.end", ""),
            "child_count": keys.get(f"wifi_registry_snapshot.{phase}.child_count", ""),
            "files_captured": keys.get(f"wifi_registry_snapshot.{phase}.files_captured", ""),
            "dirs_captured": keys.get(f"wifi_registry_snapshot.{phase}.dirs_captured", ""),
            "child_proc_captured": keys.get(f"wifi_registry_snapshot.{phase}.child_proc_captured", ""),
            "dev_properties_capture_path": keys.get(f"wifi_registry_snapshot.{phase}.dev_properties_capture_path", ""),
            "dev_socket_capture_path": keys.get(f"wifi_registry_snapshot.{phase}.dev_socket_capture_path", ""),
        }
    return {
        "enabled": keys.get("wifi_companion_start.registry_snapshot.enabled", ""),
        "before_initial_cnss_cleanup_flag": keys.get("wifi_companion_start.registry_snapshot.before_initial_cnss_cleanup", ""),
        "phases": phases,
    }


def _registry_snapshot_complete(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    for phase in REGISTRY_PHASES:
        phase_surface = phases.get(phase) or {}
        if phase_surface.get("begin") != "1" or phase_surface.get("end") != "1":
            return False
    return surface.get("enabled") == "1"


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


def _context_repair_regressed(surface: dict[str, Any]) -> bool:
    children = surface.get("children") or {}
    for name in ("per_mgr", "per_proxy"):
        child = children.get(name) or {}
        if child.get("selinux_exec_target_context") == "u:r:per_mgr:s0":
            return True
        if child.get("selinux_exec_errno") == "22":
            return True
    return False


def _property_ack_regressed(property_surface: dict[str, Any]) -> bool:
    requests = property_surface.get("requests") or []
    seen_expected: set[tuple[str, str]] = set()
    for request in requests:
        name = str(request.get("name") or "")
        value = str(request.get("value") or "")
        allowed = str(request.get("allowed") or "")
        result = str(request.get("result") or "")
        pair = (name, value)
        if pair in EXPECTED_PRIVATE_ACKS:
            if allowed != "1" or result.lower() != "0x00000000":
                return True
            seen_expected.add(pair)
        elif name.startswith("vendor.peripheral.") and allowed == "1":
            return True
    return not EXPECTED_PRIVATE_ACKS.issubset(seen_expected)


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
        and all(token in usage for token in V692_USAGE_TOKENS)
    )
    base.add_check(
        checks,
        "helper-v116-peripheral-manager-registry-snapshot-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v116 service74-gated PeripheralManager registry snapshot mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V692_MODE in line
            or "peripheral" in line
            or "--property-root" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:14],
        "deploy helper v116 before V692 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = v668.v666.companion_command(args)
    _set_option(command, "--mode", V692_MODE)
    _set_option(command, "--property-root", V535_PROPERTY_ROOT)
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V692 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v668_run_live(args, store, steps, mount_preflight)
    keys = _keys(live)
    surface = _peripheral_surface(keys)
    live["v692_peripheral_manager_surface"] = surface
    live["v692_peripheral_manager_ready"] = _provider_ready(surface)
    live["v692_property_shim_surface"] = _property_shim_surface(keys)
    live["v692_registry_snapshot_surface"] = _registry_snapshot_surface(keys)
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v692-peripheral-manager-registry-snapshot-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v116, refresh current-boot prerequisites, then run V692 preflight/live",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v692-peripheral-manager-registry-snapshot-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V692", False
    if args.command == "preflight":
        return (
            "v692-peripheral-manager-registry-snapshot-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V692 live proof",
            False,
        )
    if not base.approved(args):
        return "v692-peripheral-manager-registry-snapshot-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V692 approval", False

    decision, pass_ok, reason, next_step, live_executed = _v668_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v692-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", live_executed
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v692-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V692", live_executed
    if not live.get("companion_executed"):
        return "v692-companion-skipped", False, "companion was skipped by QRTR gate", "inspect QRTR wait evidence", live_executed

    surface = live.get("v692_peripheral_manager_surface") or {}
    counts = live.get("v655_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    cnss_retry = surface.get("cnss_retry") or {}
    property_surface = live.get("v692_property_shim_surface") or {}
    registry_surface = live.get("v692_registry_snapshot_surface") or {}

    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v692-service74-gate-timeout",
            True,
            f"service74_gate={service74_gate}",
            "provider/CNSS retry was correctly withheld; restore lower service74 path before retry",
            live_executed,
        )
    if surface.get("order") != EXPECTED_ORDER or surface.get("peripheral_manager_enabled") != "1":
        return (
            "v692-helper-order-contract-gap",
            False,
            f"surface={surface}",
            "fix helper v116 provider order contract before another live attempt",
            live_executed,
        )
    if vnd_ready.get("ready") != "1" or cnss_retry.get("initial_cleanup_safe") != "1":
        return (
            "v692-vnd-or-initial-cnss-cleanup-gap",
            True,
            f"vnd_ready={vnd_ready} cnss_retry={cnss_retry}",
            "inspect vndservicemanager readiness and initial cnss cleanup before provider retry",
            live_executed,
        )
    if _context_repair_regressed(surface):
        return (
            "v692-context-repair-regressed",
            False,
            f"surface={surface}",
            "remove invalid per_mgr SELinux context mapping before another live attempt",
            live_executed,
        )
    if _property_ack_regressed(property_surface):
        return (
            "v692-peripheral-property-ack-regressed",
            False,
            f"property_surface={property_surface}",
            "fix exact private property shim ack before another provider/CNSS retry",
            live_executed,
        )
    if not _registry_snapshot_complete(registry_surface):
        return (
            "v692-provider-registry-snapshot-incomplete",
            False,
            f"registry_surface={registry_surface}",
            "fix helper v116 registry snapshot phases before interpreting provider registration",
            live_executed,
        )
    if not _provider_ready(surface):
        return (
            "v692-provider-registration-snapshot-captured",
            True,
            f"surface={surface}; registry_surface={registry_surface}",
            "inspect vndservicemanager/binder snapshots for provider registration before Wi-Fi HAL start",
            live_executed,
        )
    if not cnss_retry.get("retry_start_order"):
        return (
            "v692-provider-ready-cnss-retry-withheld",
            True,
            f"surface={surface}",
            "inspect helper provider readiness gate before repeating live proof",
            live_executed,
        )
    if _advanced(counts, markers):
        return (
            "v692-peripheral-manager-wifi-surface-advanced",
            True,
            f"provider ready and lower Wi-Fi markers advanced; counts={counts}; markers={markers}; surface={surface}",
            "classify WLFW/BDF/wlan0 state before scan/connect or external ping",
            live_executed,
        )
    return (
        "v692-peripheral-manager-cnss-retry-gap-persists",
        True,
        f"provider ready and CNSS retry executed, but WLFW/BDF/wlan0 remain absent; counts={counts}; markers={markers}; surface={surface}",
        "classify the remaining pre-WLFW trigger before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v668_render_summary(manifest).replace(
        "# V668 cnss2 Focused Capture Proof",
        "# V692 PeripheralManager Provider Registry Snapshot Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v692_peripheral_manager_surface") or {}
    property_surface = live.get("v692_property_shim_surface") or {}
    registry_surface = live.get("v692_registry_snapshot_surface") or {}
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
        "## V692 PeripheralManager Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{V535_PROPERTY_ROOT}`",
        f"- mode: `{V692_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- peripheral_manager_ready: `{live.get('v692_peripheral_manager_ready', '')}`",
        f"- property_ack_regressed: `{_property_ack_regressed(property_surface) if property_surface else ''}`",
        f"- registry_snapshot_complete: `{_registry_snapshot_complete(registry_surface) if registry_surface else ''}`",
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
    manifest["cycle"] = "v692"
    manifest["helper_version"] = "v116"
    manifest["property_root"] = V535_PROPERTY_ROOT
    manifest["peripheral_manager_mode"] = V692_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["peripheral_manager_surface"] = live.get("v692_peripheral_manager_surface") if live else {}
    manifest["peripheral_manager_ready"] = bool(live.get("v692_peripheral_manager_ready")) if live else False
    manifest["context_repair_regressed"] = _context_repair_regressed(live.get("v692_peripheral_manager_surface") or {}) if live else False
    manifest["property_shim_surface"] = live.get("v692_property_shim_surface") if live else {}
    manifest["property_ack_regressed"] = _property_ack_regressed(live.get("v692_property_shim_surface") or {}) if live else False
    manifest["registry_snapshot_surface"] = live.get("v692_registry_snapshot_surface") if live else {}
    manifest["registry_snapshot_complete"] = _registry_snapshot_complete(live.get("v692_registry_snapshot_surface") or {}) if live else False
    manifest["wifi_hal_start_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_approved"] = [
        "helper v116 service74-gated PeripheralManager provider start-only mode",
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
