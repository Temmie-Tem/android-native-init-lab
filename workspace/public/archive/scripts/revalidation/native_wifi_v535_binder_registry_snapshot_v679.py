#!/usr/bin/env python3
"""V679 V535 Binder registry snapshot proof.

This proof replays the V676/V677 V535 property-seeded Android userspace-order
path with helper v112, adding bounded Binder registry/debug snapshots around
the failing cnss-daemon retry window. It does not start supplicant, scan,
connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import re
from typing import Any

import native_wifi_v535_property_android_order_v676 as v676


base = v676.base
v671 = v676.v671

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v679-v535-binder-registry-snapshot")
base.DEFAULT_HELPER_SHA256 = "a2c72c4157f6ddf089a40b2a5310288f3f0390ceced1f423519dcb8c1a8cc643"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v112"
base.APPROVAL_PHRASE = (
    "approve v679 V535 Binder registry snapshot Android userspace-order proof only; "
    "no supplicant, no scan/connect/link-up, no DHCP and no external ping"
)

V679_MODE = "wifi-companion-service74-gated-android-userspace-cnss-retry-registry-snapshot-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,cnss_daemon_initial_cleanup,"
    "wifi_hal_legacy,wifi_hal_ext,wificond,cnss_daemon_retry,registry_snapshot"
)
SNAPSHOT_PHASES = (
    "before_initial_cnss_cleanup",
    "after_initial_cnss_cleanup",
    "after_cnss_retry_spawn",
    "window",
)
PATH_END_RE = re.compile(
    r"^A90_EXECNS_PATH_wifi_registry_(?P<phase>[A-Za-z0-9_]+)_(?P<label>[A-Za-z0-9_]+)_END "
    r"bytes=(?P<bytes>\d+) truncated=(?P<truncated>\d+)$"
)
DIR_END_RE = re.compile(
    r"^A90_EXECNS_DIR_wifi_registry_(?P<phase>[A-Za-z0-9_]+)_(?P<label>[A-Za-z0-9_]+)_END "
    r"count=(?P<count>\d+) shown=(?P<shown>\d+) truncated=(?P<truncated>\d+)$"
)

_v676_build_checks = base.build_checks
_v676_companion_command = base.companion_command
_v676_run_live = base.run_live
_v676_decide = base.decide
_v676_render_summary = base.render_summary
_v676_build_manifest = base.build_manifest


def _rewrite(text: str) -> str:
    return (
        text.replace("V676", "V679")
        .replace("v676", "v679")
        .replace("V535 property-seeded Android userspace-order", "V535 Binder registry snapshot Android userspace-order")
        .replace("property-seeded Android userspace-order", "Binder registry snapshot Android userspace-order")
        .replace("helper v111", "helper v112")
        .replace("a90_android_execns_probe v111", "a90_android_execns_probe v112")
    )


def _keys(live: dict[str, Any]) -> dict[str, str]:
    return v671.v668.v666._merged_helper_keys(live)


def _intish(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _path_dir_capture_summary(helper_text: str) -> dict[str, dict[str, dict[str, int]]]:
    phases: dict[str, dict[str, dict[str, int]]] = {
        phase: {"paths": {}, "dirs": {}} for phase in SNAPSHOT_PHASES
    }
    for raw_line in helper_text.replace("\0", "\n").splitlines():
        line = raw_line.strip()
        path_match = PATH_END_RE.match(line)
        if path_match:
            phase = path_match.group("phase")
            if phase in phases:
                phases[phase]["paths"][path_match.group("label")] = {
                    "bytes": int(path_match.group("bytes")),
                    "truncated": int(path_match.group("truncated")),
                }
            continue
        dir_match = DIR_END_RE.match(line)
        if dir_match:
            phase = dir_match.group("phase")
            if phase in phases:
                phases[phase]["dirs"][dir_match.group("label")] = {
                    "count": int(dir_match.group("count")),
                    "shown": int(dir_match.group("shown")),
                    "truncated": int(dir_match.group("truncated")),
                }
    return phases


def _registry_snapshot_surface(live: dict[str, Any]) -> dict[str, Any]:
    keys = _keys(live)
    helper_text = str(live.get("helper_stdout_stderr") or "")
    path_dir = _path_dir_capture_summary(helper_text)
    phases: dict[str, Any] = {}
    for phase in SNAPSHOT_PHASES:
        paths = path_dir[phase]["paths"]
        dirs = path_dir[phase]["dirs"]
        phases[phase] = {
            "begin": keys.get(f"wifi_registry_snapshot.{phase}.begin", ""),
            "end": keys.get(f"wifi_registry_snapshot.{phase}.end", ""),
            "files_captured": _intish(keys.get(f"wifi_registry_snapshot.{phase}.files_captured")),
            "dirs_captured": _intish(keys.get(f"wifi_registry_snapshot.{phase}.dirs_captured")),
            "child_proc_captured": _intish(keys.get(f"wifi_registry_snapshot.{phase}.child_proc_captured")),
            "dev_properties_capture_path": keys.get(f"wifi_registry_snapshot.{phase}.dev_properties_capture_path", ""),
            "dev_socket_capture_path": keys.get(f"wifi_registry_snapshot.{phase}.dev_socket_capture_path", ""),
            "path_labels": sorted(paths),
            "dir_labels": sorted(dirs),
            "failed_transaction_log_bytes": (paths.get("binder_failed_transaction_log") or {}).get("bytes", 0),
            "transaction_log_bytes": (paths.get("binder_transaction_log") or {}).get("bytes", 0),
            "binder_state_bytes": (paths.get("binder_state") or {}).get("bytes", 0),
        }
    return {
        "mode": keys.get("mode", ""),
        "order": keys.get("wifi_companion_start.order", ""),
        "registry_enabled": keys.get("wifi_companion_start.registry_snapshot.enabled", ""),
        "before_initial_cnss_cleanup_flag": keys.get("wifi_companion_start.registry_snapshot.before_initial_cnss_cleanup", ""),
        "phases": phases,
        "after_retry_captured": phases["after_cnss_retry_spawn"]["end"] == "1",
        "window_captured": phases["window"]["end"] == "1",
        "failed_transaction_log_captured": any(
            phases[phase]["failed_transaction_log_bytes"] > 0 for phase in SNAPSHOT_PHASES
        ),
        "child_proc_captured_total": sum(phases[phase]["child_proc_captured"] for phase in SNAPSHOT_PHASES),
    }


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [
        base.Check(
            _rewrite(check.name),
            check.status,
            check.severity,
            _rewrite(check.detail),
            [_rewrite(item) for item in check.evidence],
            _rewrite(check.next_step),
        )
        for check in _v676_build_checks(args, steps, mount_preflight, v490, v525)
    ]
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = (
        args.helper_sha256 in sha_text
        and args.helper_marker in usage
        and V679_MODE in usage
    )
    base.add_check(
        checks,
        "helper-v112-binder-registry-snapshot-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must expose v112 Android userspace-order Binder registry snapshot mode",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_sha256 in line
            or args.helper_marker in line
            or V679_MODE in line
            or "wifi_registry_snapshot" in line
        ][:16],
        "deploy helper v112 before V679 live proof",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v676_companion_command(args)
    for index, item in enumerate(command):
        if item == "--mode" and index + 1 < len(command):
            command[index + 1] = V679_MODE
            break
    else:
        command.extend(["--mode", V679_MODE])
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v676_run_live(args, store, steps, mount_preflight)
    live["v679_binder_registry_surface"] = _registry_snapshot_surface(live)
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v679-v535-binder-registry-snapshot-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v112, refresh current-boot prerequisites, then run V679 preflight/live",
            False,
        )
    decision, pass_ok, reason, next_step, live_executed = _v676_decide(args, checks, live)
    decision = _rewrite(decision)
    reason = _rewrite(reason)
    next_step = _rewrite(next_step)
    if args.command == "preflight" and pass_ok and "preflight-ready" in decision:
        return (
            "v679-v535-binder-registry-snapshot-preflight-ready",
            True,
            reason,
            "run V679 live proof",
            live_executed,
        )
    if args.command != "run" and "blocked" in decision:
        return (
            "v679-binder-registry-snapshot-blocked",
            pass_ok,
            reason,
            next_step,
            live_executed,
        )
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    if not pass_ok:
        return decision, pass_ok, reason, next_step, live_executed

    registry = live.get("v679_binder_registry_surface") or {}
    property_surface = live.get("v676_property_runtime_surface") or {}
    counts = live.get("v655_counts") or {}
    lower_advanced = any(_intish(counts.get(name)) > 0 for name in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    ))
    if lower_advanced:
        return (
            "v679-binder-registry-wifi-surface-advanced",
            True,
            f"V679 advanced lower Wi-Fi markers; counts={counts}; registry={registry}",
            "classify WLFW/BDF/wlan0 state before supplicant or scan/connect",
            live_executed,
        )
    if (
        registry.get("registry_enabled") == "1"
        and registry.get("after_retry_captured")
        and registry.get("window_captured")
        and property_surface.get("property_denial_total") == 0
    ):
        return (
            "v679-binder-registry-snapshot-captured",
            True,
            f"registry={registry}; property_surface={property_surface}; counts={counts}",
            "classify V679 Binder registry/debug snapshot before retrying service-manager/HAL changes or Wi-Fi connect",
            live_executed,
        )
    return (
        "v679-binder-registry-snapshot-incomplete",
        False,
        f"registry={registry}; property_surface={property_surface}; counts={counts}",
        "inspect helper v112 transcript before another live attempt",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite(_v676_render_summary(manifest)).replace(
        "# V679 V535 Property-seeded Android Userspace-order Proof",
        "# V679 V535 Binder Registry Snapshot Proof",
        1,
    )
    live = manifest.get("live") or {}
    registry = live.get("v679_binder_registry_surface") or {}
    phases = registry.get("phases") or {}
    phase_rows = [
        [
            phase,
            str(values.get("end", "")),
            str(values.get("files_captured", "")),
            str(values.get("dirs_captured", "")),
            str(values.get("child_proc_captured", "")),
            str(values.get("failed_transaction_log_bytes", "")),
        ]
        for phase, values in phases.items()
    ]
    return "\n".join([
        text,
        "",
        "## V679 Binder Registry Snapshot Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- mode: `{V679_MODE}`",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{registry.get('order', '')}`",
        f"- registry_enabled: `{registry.get('registry_enabled', '')}`",
        f"- after_retry_captured: `{registry.get('after_retry_captured', '')}`",
        f"- window_captured: `{registry.get('window_captured', '')}`",
        f"- failed_transaction_log_captured: `{registry.get('failed_transaction_log_captured', '')}`",
        "- Supplicant, scan/connect, DHCP, routing, credentials, and external ping remain blocked.",
        "",
        base.markdown_table(
            ["phase", "end", "files", "dirs", "child_proc", "failed_tx_bytes"],
            phase_rows,
        ) if phase_rows else "- no registry snapshot captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v676_build_manifest(args, store)
    live = manifest.get("live") or {}
    registry = live.get("v679_binder_registry_surface") if live else {}
    manifest["cycle"] = "v679"
    manifest["helper_version"] = "v112"
    manifest["android_userspace_mode"] = V679_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    manifest["v679_binder_registry_surface"] = registry
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    manifest["explicitly_approved"] = [
        "helper v112 service74-gated Android userspace-order Binder registry snapshot mode",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "Wi-Fi HAL legacy/ext and wificond start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "V535 private property root bind and property service shim inside helper namespace",
        "read-only Binder debug/registry snapshots inside helper bounded window",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "sysfs writes or subsystem state writes",
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "supplicant or hostapd start",
        "IWifi.start transaction, qcwlanstate, or sysfs driver-state writes",
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
