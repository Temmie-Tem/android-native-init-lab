#!/usr/bin/env python3
"""V694 service74-gated PeripheralManager vndservice query proof.

This proof replays the service74-positive PeripheralManager provider start-only
path with helper v117. It starts `pm-service`/`pm-proxy` below Wi-Fi bring-up
and runs a bounded `/vendor/bin/vndservice list` query from the same private
Android namespace to classify whether `pm-service` registers a vendor Binder
service before another CNSS retry or any Wi-Fi HAL/scan/connect work.
"""

from __future__ import annotations

from typing import Any

import native_wifi_peripheral_manager_registry_snapshot_v692 as v692


base = v692.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v694-peripheral-vndservice-query")
base.DEFAULT_HELPER_SHA256 = "4739699b794a4129f0bb84b61ecbbaf726e53eeb51ea93ad0a0b0497b60eeb83"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v117"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v694-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v694 bounded vndservice query proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

V694_MODE = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,"
    "per_mgr,vndservice_query,per_proxy,vndservice_query"
)
MAX_CMDV1_COMMAND_ARGS = 30
V694_USAGE_TOKENS = (
    V694_MODE,
    "a90_android_execns_probe v117",
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)
QUERY_PHASES = ("after_per_mgr_probe", "after_per_proxy_probe")

v692.v668.v666.PROPERTY_ROOT = v692.V535_PROPERTY_ROOT

_v666_build_checks = v692._v666_build_checks
_v668_run_live = v692._v668_run_live
_v668_decide = v692._v668_decide
_v668_render_summary = v692._v668_render_summary
_v668_build_manifest = v692._v668_build_manifest


def _keys(live: dict[str, Any]) -> dict[str, str]:
    return v692.v668.v666._merged_helper_keys(live)


def _int_count(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _query_surface(keys: dict[str, str]) -> dict[str, Any]:
    phases: dict[str, dict[str, str]] = {}
    for phase in QUERY_PHASES:
        prefix = f"wifi_vndservice_query.{phase}."
        phases[phase] = {
            "begin": keys.get(prefix + "begin", ""),
            "end": keys.get(prefix + "end", ""),
            "tool": keys.get(prefix + "tool", ""),
            "argv": keys.get(prefix + "argv", ""),
            "exists": keys.get(prefix + "exists", ""),
            "executable": keys.get(prefix + "executable", ""),
            "exec_attempted": keys.get(prefix + "exec_attempted", ""),
            "child_started": keys.get(prefix + "child_started", ""),
            "exit_code": keys.get(prefix + "exit_code", ""),
            "signal": keys.get(prefix + "signal", ""),
            "timed_out": keys.get(prefix + "timed_out", ""),
            "stdout_bytes": keys.get(prefix + "stdout_bytes", ""),
            "stderr_bytes": keys.get(prefix + "stderr_bytes", ""),
            "vendor_qcom_peripheral_manager_seen": keys.get(prefix + "vendor_qcom_peripheral_manager_seen", ""),
            "peripheral_seen": keys.get(prefix + "peripheral_seen", ""),
            "result": keys.get(prefix + "result", ""),
            "reason": keys.get(prefix + "reason", ""),
        }
    return {
        "enabled": keys.get("wifi_companion_start.vndservice_query.enabled", ""),
        "phases": phases,
    }


def _query_ran(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    return any((phases.get(phase) or {}).get("begin") == "1" for phase in QUERY_PHASES)


def _query_exact_match(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    return any((phases.get(phase) or {}).get("vendor_qcom_peripheral_manager_seen") == "1" for phase in QUERY_PHASES)


def _query_peripheral_match(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    return any((phases.get(phase) or {}).get("peripheral_seen") == "1" for phase in QUERY_PHASES)


def _query_timed_out(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    return any((phases.get(phase) or {}).get("timed_out") == "1" for phase in QUERY_PHASES)


def _query_exit_zero(surface: dict[str, Any]) -> bool:
    phases = surface.get("phases") or {}
    return any(
        (phases.get(phase) or {}).get("exit_code") == "0"
        and (phases.get(phase) or {}).get("signal") in {"", "0"}
        for phase in QUERY_PHASES
    )


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
        and all(token in usage for token in V694_USAGE_TOKENS)
    )
    base.add_check(
        checks,
        "helper-v117-peripheral-vndservice-query-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v117 service74-gated PeripheralManager vndservice query mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V694_MODE in line
            or "wifi_vndservice_query" in line
            or "/vendor/bin/vndservice" in line
            or "--property-root" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:18],
        "deploy helper v117 before V694 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = v692.v668.v666.companion_command(args)
    v692._set_option(command, "--mode", V694_MODE)
    v692._set_option(command, "--property-root", v692.V535_PROPERTY_ROOT)
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V694 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v668_run_live(args, store, steps, mount_preflight)
    keys = _keys(live)
    peripheral = v692._peripheral_surface(keys)
    peripheral["initial_cnss_daemon"] = {
        "index": keys.get("wifi_companion_start.initial_cnss_daemon.index", ""),
        "observable": keys.get("wifi_companion_start.initial_cnss_daemon.observable", ""),
        "cleanup_safe": keys.get("wifi_companion_start.initial_cnss_daemon.cleanup_safe", ""),
    }
    live["v694_peripheral_manager_surface"] = peripheral
    live["v694_property_shim_surface"] = v692._property_shim_surface(keys)
    live["v694_vndservice_query_surface"] = _query_surface(keys)
    live["v694_vndservice_query_ran"] = _query_ran(live["v694_vndservice_query_surface"])
    live["v694_vndservice_exact_match"] = _query_exact_match(live["v694_vndservice_query_surface"])
    live["v694_vndservice_peripheral_match"] = _query_peripheral_match(live["v694_vndservice_query_surface"])
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v694-peripheral-vndservice-query-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v117, refresh current-boot prerequisites, then run V694 preflight/live",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v694-peripheral-vndservice-query-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V694", False
    if args.command == "preflight":
        return (
            "v694-peripheral-vndservice-query-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V694 bounded vndservice query proof",
            False,
        )
    if not base.approved(args):
        return "v694-peripheral-vndservice-query-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V694 approval", False

    decision, pass_ok, reason, next_step, live_executed = _v668_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v694-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", live_executed
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v694-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V694", live_executed
    if not live.get("companion_executed"):
        return "v694-companion-skipped", False, "companion was skipped by QRTR gate", "inspect QRTR wait evidence", live_executed

    surface = live.get("v694_peripheral_manager_surface") or {}
    property_surface = live.get("v694_property_shim_surface") or {}
    query_surface = live.get("v694_vndservice_query_surface") or {}
    counts = live.get("v655_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    cnss_retry = surface.get("cnss_retry") or {}
    initial_cnss = surface.get("initial_cnss_daemon") or {}

    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v694-service74-gate-timeout",
            True,
            f"service74_gate={service74_gate}",
            "provider query was correctly withheld; restore lower service74 path before retry",
            live_executed,
        )
    if surface.get("order") != EXPECTED_ORDER or surface.get("peripheral_manager_enabled") != "1":
        return (
            "v694-helper-order-contract-gap",
            False,
            f"surface={surface}",
            "fix helper v117 provider/query order contract before another live attempt",
            live_executed,
        )
    if vnd_ready.get("ready") != "1" or initial_cnss.get("cleanup_safe") != "1":
        return (
            "v694-vnd-or-initial-cnss-cleanup-gap",
            True,
            f"vnd_ready={vnd_ready} initial_cnss={initial_cnss} cnss_retry={cnss_retry}",
            "inspect vndservicemanager readiness and initial cnss cleanup before provider query",
            live_executed,
        )
    if v692._context_repair_regressed(surface):
        return (
            "v694-context-repair-regressed",
            False,
            f"surface={surface}",
            "remove invalid provider SELinux mapping before another live attempt",
            live_executed,
        )
    if v692._property_ack_regressed(property_surface):
        return (
            "v694-peripheral-property-ack-regressed",
            False,
            f"property_surface={property_surface}",
            "fix exact private property shim ack before another provider query",
            live_executed,
        )
    if not _query_ran(query_surface):
        return (
            "v694-vndservice-query-not-executed",
            False,
            f"query_surface={query_surface}",
            "fix helper v117 query placement before interpreting provider registration",
            live_executed,
        )
    if _advanced(counts, markers):
        return (
            "v694-wifi-surface-advanced",
            True,
            f"WLFW/BDF/wlan0 marker moved; counts={counts}; markers={markers}; query_surface={query_surface}",
            "classify wlan0 readiness before scan/connect or external ping",
            live_executed,
        )
    if _query_exact_match(query_surface):
        return (
            "v694-peripheral-vndservice-registration-confirmed",
            True,
            f"vndservice query saw vendor.qcom.PeripheralManager; query_surface={query_surface}",
            "retry the CNSS tail only after confirmed provider registration, still below Wi-Fi HAL/scan/connect",
            live_executed,
        )
    if _query_peripheral_match(query_surface):
        return (
            "v694-peripheral-vndservice-ambiguous-registration-captured",
            True,
            f"vndservice query saw a peripheral-like service but not the exact expected name; query_surface={query_surface}",
            "inspect query stdout and vendor service contexts before CNSS retry",
            live_executed,
        )
    if _query_timed_out(query_surface):
        return (
            "v694-vndservice-query-timeout",
            True,
            f"query_surface={query_surface}",
            "inspect vndservice/vndservicemanager responsiveness before retrying provider registration",
            live_executed,
        )
    if _query_exit_zero(query_surface):
        return (
            "v694-peripheral-vndservice-registration-absent",
            True,
            f"vndservice list exited zero but did not show PeripheralManager; query_surface={query_surface}",
            "repair provider registration/runtime before another CNSS retry or Wi-Fi HAL start",
            live_executed,
        )
    return (
        "v694-vndservice-query-runtime-gap",
        True,
        f"vndservice query ran but did not exit zero; query_surface={query_surface}",
        "inspect vndservice syntax/runtime output before changing Wi-Fi bring-up order",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v668_render_summary(manifest).replace(
        "# V668 cnss2 Focused Capture Proof",
        "# V694 PeripheralManager vndservice Query Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v694_peripheral_manager_surface") or {}
    query_surface = live.get("v694_vndservice_query_surface") or {}
    rows: list[list[str]] = []
    for section, values in sorted(surface.items()):
        if isinstance(values, dict):
            for key, value in sorted(values.items()):
                rows.append([section, key, str(value)])
        else:
            rows.append(["surface", section, str(values)])
    query_rows: list[list[str]] = []
    phases = query_surface.get("phases") or {}
    for phase, values in sorted(phases.items()):
        for key, value in sorted((values or {}).items()):
            query_rows.append([phase, key, str(value)])
    return "\n".join([
        text,
        "",
        "## V694 PeripheralManager vndservice Query Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{v692.V535_PROPERTY_ROOT}`",
        f"- mode: `{V694_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- query_ran: `{live.get('v694_vndservice_query_ran', '')}`",
        f"- exact_match: `{live.get('v694_vndservice_exact_match', '')}`",
        f"- peripheral_match: `{live.get('v694_vndservice_peripheral_match', '')}`",
        "- Wi-Fi HAL, supplicant, scan/connect, DHCP, routing, credentials, and external ping remain blocked.",
        "",
        base.markdown_table(["section", "key", "value"], rows) if rows else "- provider surface not captured",
        "",
        "## V694 vndservice Query",
        "",
        base.markdown_table(["phase", "key", "value"], query_rows) if query_rows else "- query surface not captured",
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
    manifest["cycle"] = "v694"
    manifest["helper_version"] = "v117"
    manifest["property_root"] = v692.V535_PROPERTY_ROOT
    manifest["peripheral_vndservice_query_mode"] = V694_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["peripheral_manager_surface"] = live.get("v694_peripheral_manager_surface") if live else {}
    manifest["property_shim_surface"] = live.get("v694_property_shim_surface") if live else {}
    manifest["vndservice_query_surface"] = live.get("v694_vndservice_query_surface") if live else {}
    manifest["vndservice_query_ran"] = bool(live.get("v694_vndservice_query_ran")) if live else False
    manifest["vndservice_exact_match"] = bool(live.get("v694_vndservice_exact_match")) if live else False
    manifest["vndservice_peripheral_match"] = bool(live.get("v694_vndservice_peripheral_match")) if live else False
    manifest["wifi_hal_start_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_approved"] = [
        "helper v117 service74-gated PeripheralManager vndservice query mode",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "pm-service and pm-proxy start-only inside bounded private namespace",
        "bounded /vendor/bin/vndservice list query inside bounded private namespace",
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
