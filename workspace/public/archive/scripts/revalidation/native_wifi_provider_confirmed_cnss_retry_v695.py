#!/usr/bin/env python3
"""V695 provider-confirmed PeripheralManager CNSS retry proof.

This proof runs one bounded private-namespace Wi-Fi companion sequence below
Wi-Fi HAL and link bring-up. It first confirms
`vendor.qcom.PeripheralManager` through `/vendor/bin/vndservice list`, then
starts one fresh `cnss-daemon` retry tail in the same helper invocation.
"""

from __future__ import annotations

from typing import Any

import native_wifi_peripheral_vndservice_query_v694 as v694


base = v694.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v695-provider-confirmed-cnss-retry")
base.DEFAULT_HELPER_SHA256 = "7f91a939df2333dde0d92548d236a321d4b0adcce3d02e4d462e9178ac447e36"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v118"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v695-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v695 provider-confirmed CNSS retry proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

V695_MODE = "wifi-companion-service74-gated-peripheral-manager-vndservice-query-cnss-retry-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,"
    "per_mgr,vndservice_query,per_proxy,vndservice_query,cnss_daemon_retry"
)
MAX_CMDV1_COMMAND_ARGS = 30
V695_USAGE_TOKENS = (
    V695_MODE,
    "a90_android_execns_probe v118",
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)

v694.v692.v668.v666.PROPERTY_ROOT = v694.v692.V535_PROPERTY_ROOT


def _keys(live: dict[str, Any]) -> dict[str, str]:
    return v694._keys(live)


def _surface(keys: dict[str, str]) -> dict[str, Any]:
    surface = v694.v692._peripheral_surface(keys)
    surface["initial_cnss_daemon"] = {
        "index": keys.get("wifi_companion_start.initial_cnss_daemon.index", ""),
        "observable": keys.get("wifi_companion_start.initial_cnss_daemon.observable", ""),
        "cleanup_safe": keys.get("wifi_companion_start.initial_cnss_daemon.cleanup_safe", ""),
    }
    return surface


def _cnss_retry_started(surface: dict[str, Any]) -> bool:
    retry = surface.get("cnss_retry") or {}
    return bool(retry.get("retry_start_order"))


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = v694._v666_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
        and all(token in usage for token in V695_USAGE_TOKENS)
    )
    base.add_check(
        checks,
        "helper-v118-provider-confirmed-cnss-retry-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v118 vndservice-query plus CNSS retry mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V695_MODE in line
            or "wifi_vndservice_query" in line
            or "/vendor/bin/vndservice" in line
            or "cnss_daemon_retry" in line
            or "--property-root" in line
            or "--allow-service-manager-start-only" in line
            or "--allow-qrtr-ns-readback" in line
        ][:20],
        "deploy helper v118 before V695 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = v694.v692.v668.v666.companion_command(args)
    v694.v692._set_option(command, "--mode", V695_MODE)
    v694.v692._set_option(command, "--property-root", v694.v692.V535_PROPERTY_ROOT)
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V695 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = v694._v668_run_live(args, store, steps, mount_preflight)
    keys = _keys(live)
    surface = _surface(keys)
    query_surface = v694._query_surface(keys)
    live["v695_peripheral_manager_surface"] = surface
    live["v695_property_shim_surface"] = v694.v692._property_shim_surface(keys)
    live["v695_vndservice_query_surface"] = query_surface
    live["v695_vndservice_query_ran"] = v694._query_ran(query_surface)
    live["v695_vndservice_exact_match"] = v694._query_exact_match(query_surface)
    live["v695_vndservice_peripheral_match"] = v694._query_peripheral_match(query_surface)
    live["v695_cnss_retry_started"] = _cnss_retry_started(surface)
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v695-provider-confirmed-cnss-retry-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v118, refresh current-boot prerequisites, then run V695 preflight/live",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v695-provider-confirmed-cnss-retry-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V695", False
    if args.command == "preflight":
        return (
            "v695-provider-confirmed-cnss-retry-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V695 bounded provider-confirmed CNSS retry proof",
            False,
        )
    if not base.approved(args):
        return "v695-provider-confirmed-cnss-retry-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V695 approval", False

    decision, pass_ok, reason, next_step, live_executed = v694._v668_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v695-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", live_executed
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v695-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V695", live_executed
    if not live.get("companion_executed"):
        return "v695-companion-skipped", False, "companion was skipped by QRTR gate", "inspect QRTR wait evidence", live_executed

    surface = live.get("v695_peripheral_manager_surface") or {}
    query_surface = live.get("v695_vndservice_query_surface") or {}
    property_surface = live.get("v695_property_shim_surface") or {}
    counts = live.get("v655_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    cnss_retry = surface.get("cnss_retry") or {}

    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v695-service74-gate-timeout",
            True,
            f"service74_gate={service74_gate}",
            "provider-confirmed CNSS retry was correctly withheld; restore lower service74 path before retry",
            live_executed,
        )
    if surface.get("order") != EXPECTED_ORDER or surface.get("peripheral_manager_enabled") != "1":
        return (
            "v695-helper-order-contract-gap",
            False,
            f"surface={surface}",
            "fix helper v118 query/retry order contract before another live attempt",
            live_executed,
        )
    if vnd_ready.get("ready") != "1" or cnss_retry.get("initial_cleanup_safe") != "1":
        return (
            "v695-vnd-or-initial-cnss-cleanup-gap",
            True,
            f"vnd_ready={vnd_ready} cnss_retry={cnss_retry}",
            "inspect vndservicemanager readiness and initial cnss cleanup before provider-confirmed retry",
            live_executed,
        )
    if v694.v692._context_repair_regressed(surface):
        return (
            "v695-context-repair-regressed",
            False,
            f"surface={surface}",
            "remove invalid provider SELinux mapping before another live attempt",
            live_executed,
        )
    if v694.v692._property_ack_regressed(property_surface):
        return (
            "v695-peripheral-property-ack-regressed",
            False,
            f"property_surface={property_surface}",
            "fix exact private property shim ack before another provider-confirmed retry",
            live_executed,
        )
    if not v694._query_ran(query_surface):
        return (
            "v695-vndservice-query-not-executed",
            False,
            f"query_surface={query_surface}",
            "fix helper v118 query placement before interpreting CNSS retry",
            live_executed,
        )
    if not v694._query_exact_match(query_surface):
        if v694._query_peripheral_match(query_surface):
            return (
                "v695-peripheral-vndservice-ambiguous-registration-captured",
                True,
                f"query_surface={query_surface}",
                "inspect query stdout before provider-confirmed CNSS retry",
                live_executed,
            )
        if v694._query_timed_out(query_surface):
            return (
                "v695-vndservice-query-timeout",
                True,
                f"query_surface={query_surface}",
                "inspect vndservice/vndservicemanager responsiveness before retrying",
                live_executed,
            )
        if v694._query_exit_zero(query_surface):
            return (
                "v695-peripheral-vndservice-registration-absent",
                True,
                f"query_surface={query_surface}",
                "repair provider registration/runtime before another CNSS retry",
                live_executed,
            )
        return (
            "v695-vndservice-query-runtime-gap",
            True,
            f"query_surface={query_surface}",
            "inspect vndservice syntax/runtime output before CNSS retry",
            live_executed,
        )
    if not _cnss_retry_started(surface):
        return (
            "v695-provider-confirmed-cnss-retry-withheld",
            True,
            f"surface={surface} query_surface={query_surface}",
            "fix helper retry placement after confirmed provider registration",
            live_executed,
        )
    if v694._advanced(counts, markers):
        return (
            "v695-provider-confirmed-cnss-retry-wifi-surface-advanced",
            True,
            f"provider registered and lower Wi-Fi markers advanced; counts={counts}; markers={markers}; surface={surface}; query_surface={query_surface}",
            "classify WLFW/BDF/wlan0 state before scan/connect or external ping",
            live_executed,
        )
    return (
        "v695-provider-confirmed-cnss-retry-gap-persists",
        True,
        f"provider registered and CNSS retry executed, but WLFW/BDF/wlan0 remain absent; counts={counts}; markers={markers}; surface={surface}; query_surface={query_surface}",
        "classify the remaining pre-WLFW trigger before Wi-Fi HAL, scan/connect, DHCP, or external ping",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = v694._v668_render_summary(manifest).replace(
        "# V668 cnss2 Focused Capture Proof",
        "# V695 Provider-confirmed CNSS Retry Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v695_peripheral_manager_surface") or {}
    query_surface = live.get("v695_vndservice_query_surface") or {}
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
        "## V695 Provider-confirmed CNSS Retry Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{v694.v692.V535_PROPERTY_ROOT}`",
        f"- mode: `{V695_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- query_ran: `{live.get('v695_vndservice_query_ran', '')}`",
        f"- exact_match: `{live.get('v695_vndservice_exact_match', '')}`",
        f"- cnss_retry_started: `{live.get('v695_cnss_retry_started', '')}`",
        "- Wi-Fi HAL, supplicant, scan/connect, DHCP, routing, credentials, and external ping remain blocked.",
        "",
        base.markdown_table(["section", "key", "value"], rows) if rows else "- provider surface not captured",
        "",
        "## V695 vndservice Query",
        "",
        base.markdown_table(["phase", "key", "value"], query_rows) if query_rows else "- query surface not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = v694._v668_build_manifest(args, store)
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
    manifest["cycle"] = "v695"
    manifest["helper_version"] = "v118"
    manifest["property_root"] = v694.v692.V535_PROPERTY_ROOT
    manifest["provider_confirmed_cnss_retry_mode"] = V695_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["peripheral_manager_surface"] = live.get("v695_peripheral_manager_surface") if live else {}
    manifest["property_shim_surface"] = live.get("v695_property_shim_surface") if live else {}
    manifest["vndservice_query_surface"] = live.get("v695_vndservice_query_surface") if live else {}
    manifest["vndservice_query_ran"] = bool(live.get("v695_vndservice_query_ran")) if live else False
    manifest["vndservice_exact_match"] = bool(live.get("v695_vndservice_exact_match")) if live else False
    manifest["cnss_retry_started"] = bool(live.get("v695_cnss_retry_started")) if live else False
    manifest["wifi_hal_start_executed"] = False
    manifest["wifi_bringup_executed"] = False
    manifest["external_ping_executed"] = False
    manifest["explicitly_approved"] = [
        "helper v118 service74-gated provider-confirmed CNSS retry mode",
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
