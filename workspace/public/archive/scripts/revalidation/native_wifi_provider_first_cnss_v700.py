#!/usr/bin/env python3
"""V700 provider-first initial-suppressed CNSS retry proof.

This proof runs the same bounded private-namespace companion stack used by
V695, but removes the initial pre-provider `cnss-daemon` start. It confirms
`vendor.qcom.PeripheralManager` first, then starts exactly one fresh
`cnss-daemon` retry tail below Wi-Fi HAL and link bring-up.
"""

from __future__ import annotations

from typing import Any

import native_wifi_provider_confirmed_cnss_retry_v695 as v695


base = v695.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v700-provider-first-cnss")
base.DEFAULT_HELPER_SHA256 = "53c7d74d9a7d4ec2cbbaf7dc98e37af9bb165a9ccaabc45616dc3c12949d794c"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v119"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v700-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v700 provider-first initial-suppressed CNSS proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

V700_MODE = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-provider-first-cnss-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,per_mgr,vndservice_query,per_proxy,"
    "vndservice_query,cnss_daemon_retry"
)
MAX_CMDV1_COMMAND_ARGS = 30
V700_USAGE_TOKENS = (
    V700_MODE,
    "a90_android_execns_probe v119",
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)

v695.v694.v692.v668.v666.PROPERTY_ROOT = v695.v694.v692.V535_PROPERTY_ROOT


def _keys(live: dict[str, Any]) -> dict[str, str]:
    return v695._keys(live)


def _surface(keys: dict[str, str]) -> dict[str, Any]:
    surface = v695._surface(keys)
    initial = surface.setdefault("initial_cnss_daemon", {})
    if isinstance(initial, dict):
        initial["suppressed"] = keys.get("wifi_companion_start.initial_cnss_daemon.suppressed", "")
    return surface


def _initial_suppressed(surface: dict[str, Any]) -> bool:
    initial = surface.get("initial_cnss_daemon") or {}
    return initial.get("suppressed") == "1"


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = v695.v694._v666_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
        and all(token in usage for token in V700_USAGE_TOKENS)
    )
    base.add_check(
        checks,
        "helper-v119-provider-first-cnss-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v119 provider-first initial-suppressed CNSS mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V700_MODE in line
            or "initial_cnss_daemon.suppressed" in line
            or "wifi_vndservice_query" in line
            or "/vendor/bin/vndservice" in line
            or "cnss_daemon_retry" in line
            or "--property-root" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:24],
        "deploy helper v119 before V700 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = v695.v694.v692.v668.v666.companion_command(args)
    v695.v694.v692._set_option(command, "--mode", V700_MODE)
    v695.v694.v692._set_option(command, "--property-root", v695.v694.v692.V535_PROPERTY_ROOT)
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V700 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = v695.v694._v668_run_live(args, store, steps, mount_preflight)
    keys = _keys(live)
    surface = _surface(keys)
    query_surface = v695.v694._query_surface(keys)
    live["v700_peripheral_manager_surface"] = surface
    live["v700_property_shim_surface"] = v695.v694.v692._property_shim_surface(keys)
    live["v700_vndservice_query_surface"] = query_surface
    live["v700_vndservice_query_ran"] = v695.v694._query_ran(query_surface)
    live["v700_vndservice_exact_match"] = v695.v694._query_exact_match(query_surface)
    live["v700_vndservice_peripheral_match"] = v695.v694._query_peripheral_match(query_surface)
    live["v700_initial_cnss_suppressed"] = _initial_suppressed(surface)
    live["v700_cnss_retry_started"] = v695._cnss_retry_started(surface)
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v700-provider-first-cnss-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v119, refresh current-boot prerequisites, then run V700 preflight/live",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v700-provider-first-cnss-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V700", False
    if args.command == "preflight":
        return (
            "v700-provider-first-cnss-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V700 bounded provider-first CNSS proof",
            False,
        )
    if not base.approved(args):
        return "v700-provider-first-cnss-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V700 approval", False

    decision, pass_ok, reason, next_step, live_executed = v695.v694._v668_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v700-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", live_executed
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v700-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V700", live_executed
    if not live.get("companion_executed"):
        return "v700-companion-skipped", False, "companion was skipped by QRTR gate", "inspect QRTR wait evidence", live_executed

    surface = live.get("v700_peripheral_manager_surface") or {}
    query_surface = live.get("v700_vndservice_query_surface") or {}
    property_surface = live.get("v700_property_shim_surface") or {}
    counts = live.get("v655_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}

    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v700-service74-gate-timeout",
            True,
            f"service74_gate={service74_gate}",
            "provider-first CNSS retry was correctly withheld; restore lower service74 path before retry",
            live_executed,
        )
    if surface.get("order") != EXPECTED_ORDER or surface.get("peripheral_manager_enabled") != "1" or not _initial_suppressed(surface):
        return (
            "v700-helper-order-contract-gap",
            False,
            f"surface={surface}",
            "fix helper v119 provider-first order/suppression contract before another live attempt",
            live_executed,
        )
    if vnd_ready.get("ready") != "1":
        return (
            "v700-vnd-readiness-gap",
            True,
            f"vnd_ready={vnd_ready}",
            "inspect vndservicemanager readiness before provider-first CNSS retry",
            live_executed,
        )
    if v695.v694.v692._context_repair_regressed(surface):
        return (
            "v700-context-repair-regressed",
            False,
            f"surface={surface}",
            "remove invalid provider SELinux mapping before another live attempt",
            live_executed,
        )
    if v695.v694.v692._property_ack_regressed(property_surface):
        return (
            "v700-peripheral-property-ack-regressed",
            False,
            f"property_surface={property_surface}",
            "fix exact private property shim ack before another provider-first retry",
            live_executed,
        )
    if not v695.v694._query_ran(query_surface):
        return (
            "v700-vndservice-query-not-executed",
            False,
            f"query_surface={query_surface}",
            "fix helper v119 query placement before interpreting CNSS retry",
            live_executed,
        )
    if not v695.v694._query_exact_match(query_surface):
        if v695.v694._query_peripheral_match(query_surface):
            return (
                "v700-peripheral-vndservice-ambiguous-registration-captured",
                True,
                f"query_surface={query_surface}",
                "inspect query stdout before provider-first CNSS retry",
                live_executed,
            )
        if v695.v694._query_timed_out(query_surface):
            return (
                "v700-vndservice-query-timeout",
                True,
                f"query_surface={query_surface}",
                "inspect vndservice/vndservicemanager responsiveness before retrying",
                live_executed,
            )
        if v695.v694._query_exit_zero(query_surface):
            return (
                "v700-peripheral-vndservice-registration-absent",
                True,
                f"query_surface={query_surface}",
                "repair provider registration/runtime before another CNSS retry",
                live_executed,
            )
        return (
            "v700-vndservice-query-runtime-gap",
            True,
            f"query_surface={query_surface}",
            "inspect vndservice syntax/runtime output before CNSS retry",
            live_executed,
        )
    if not v695._cnss_retry_started(surface):
        return (
            "v700-provider-first-cnss-retry-withheld",
            True,
            f"surface={surface} query_surface={query_surface}",
            "fix helper retry placement after confirmed provider registration",
            live_executed,
        )
    if v695.v694._advanced(counts, markers):
        return (
            "v700-provider-first-cnss-wifi-surface-advanced",
            True,
            f"provider registered and lower Wi-Fi markers advanced; counts={counts}; markers={markers}; surface={surface}; query_surface={query_surface}",
            "classify WLFW/BDF/wlan0 state before scan/connect or external ping",
            live_executed,
        )
    return (
        "v700-provider-first-cnss-gap-persists",
        True,
        f"provider registered and provider-first CNSS retry executed, but WLFW/BDF/wlan0 remain absent; counts={counts}; markers={markers}; surface={surface}; query_surface={query_surface}",
        "classify the remaining pre-WLFW trigger before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = v695.v694._v668_render_summary(manifest).replace(
        "# V668 cnss2 Focused Capture Proof",
        "# V700 Provider-first Initial-suppressed CNSS Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v700_peripheral_manager_surface") or {}
    query_surface = live.get("v700_vndservice_query_surface") or {}
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
        "## V700 Provider-first CNSS Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{v695.v694.v692.V535_PROPERTY_ROOT}`",
        f"- mode: `{V700_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- initial_cnss_suppressed: `{live.get('v700_initial_cnss_suppressed', '')}`",
        f"- query_ran: `{live.get('v700_vndservice_query_ran', '')}`",
        f"- exact_match: `{live.get('v700_vndservice_exact_match', '')}`",
        f"- cnss_retry_started: `{live.get('v700_cnss_retry_started', '')}`",
        "- Wi-Fi HAL, supplicant, scan/connect, DHCP, routing, credentials, and external ping remain blocked.",
        "",
        base.markdown_table(["section", "key", "value"], rows) if rows else "- provider surface not captured",
        "",
        "## V700 vndservice Query",
        "",
        base.markdown_table(["phase", "key", "value"], query_rows) if query_rows else "- query surface not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = v695.v694._v668_build_manifest(args, store)
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
    manifest["cycle"] = "v700"
    manifest["helper_version"] = "v119"
    manifest["property_root"] = v695.v694.v692.V535_PROPERTY_ROOT
    manifest["provider_first_cnss_mode"] = V700_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["peripheral_manager_surface"] = live.get("v700_peripheral_manager_surface") if live else {}
    manifest["property_shim_surface"] = live.get("v700_property_shim_surface") if live else {}
    manifest["vndservice_query_surface"] = live.get("v700_vndservice_query_surface") if live else {}
    manifest["initial_cnss_suppressed"] = bool(live.get("v700_initial_cnss_suppressed")) if live else False
    manifest["vndservice_query_ran"] = bool(live.get("v700_vndservice_query_ran")) if live else False
    manifest["vndservice_exact_match"] = bool(live.get("v700_vndservice_exact_match")) if live else False
    manifest["cnss_retry_started"] = bool(live.get("v700_cnss_retry_started")) if live else False
    manifest["wifi_hal_start_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_approved"] = [
        "helper v119 service74-gated provider-first initial-suppressed CNSS mode",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "pm-service and pm-proxy start-only inside bounded private namespace",
        "bounded /vendor/bin/vndservice list query inside bounded private namespace",
        "one fresh cnss-daemon retry tail after confirmed provider registration",
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
