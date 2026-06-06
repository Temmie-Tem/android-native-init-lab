#!/usr/bin/env python3
"""V661 host-only binder registration/context classifier.

This classifier consumes existing V660, V659, V654, and Android reference
evidence. It does not contact the device, write sysfs, start daemons, start
service-manager, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_binder_runtime_mismatch_classifier_v654 as v654
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v661-binder-registration-context-classifier")
DEFAULT_V654_MANIFEST = Path("tmp/wifi/v654-binder-runtime-mismatch-classifier/manifest.json")
DEFAULT_V659_MANIFEST = Path("tmp/wifi/v659-vndservicemanager-readiness-only-live/manifest.json")
DEFAULT_V660_MANIFEST = Path("tmp/wifi/v660-ready-cnss-retry-live/manifest.json")
DEFAULT_V660_DMESG = Path("tmp/wifi/v660-ready-cnss-retry-live/native/dmesg-delta.txt")
DEFAULT_V660_HELPER = Path("tmp/wifi/v660-ready-cnss-retry-live/native/companion-start-only-with-holder.txt")
DEFAULT_ANDROID_AUDIO_DMESG = Path("tmp/wifi/v649-final-live-replay-classifier/android/replay/dmesg-audio-wifi-tail.txt")
DEFAULT_ANDROID_UNFILTERED_DMESG = Path("tmp/wifi/v649-final-live-replay-classifier/android/replay/dmesg-unfiltered-tail.txt")

FORBIDDEN_ACTIONS = (
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "partition/boot-image write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
)

SERVICE_MANAGER_CHILDREN = ("servicemanager", "hwservicemanager", "vndservicemanager")
CONTEXT_FILES = (
    "plat_service_contexts",
    "system_ext_service_contexts",
    "vendor_service_contexts",
    "plat_hwservice_contexts",
    "system_ext_hwservice_contexts",
    "vendor_hwservice_contexts",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v654-manifest", type=Path, default=DEFAULT_V654_MANIFEST)
    parser.add_argument("--v659-manifest", type=Path, default=DEFAULT_V659_MANIFEST)
    parser.add_argument("--v660-manifest", type=Path, default=DEFAULT_V660_MANIFEST)
    parser.add_argument("--v660-dmesg", type=Path, default=DEFAULT_V660_DMESG)
    parser.add_argument("--v660-helper", type=Path, default=DEFAULT_V660_HELPER)
    parser.add_argument("--android-audio-dmesg", type=Path, default=DEFAULT_ANDROID_AUDIO_DMESG)
    parser.add_argument("--android-unfiltered-dmesg", type=Path, default=DEFAULT_ANDROID_UNFILTERED_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    text = v654.read_text(path)
    return json.loads(text) if text else {}


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def boolish(value: Any) -> bool:
    return value in (True, 1, "1", "true", "True", "yes", "pass", "ok")


def intish(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def source_summary(text: str, label: str) -> dict[str, Any]:
    return v654.source_summary(v654.parse_events(text, label))


def helper_keys(path: Path) -> dict[str, str]:
    return v654.parse_key_values(v654.read_text(path))


def key_bool(keys: dict[str, str], key: str) -> bool:
    return boolish(keys.get(key))


def count_value(counts: dict[str, Any], *names: str) -> int:
    for name in names:
        value = intish(counts.get(name))
        if value is not None:
            return value
    return 0


def service_child_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for child in SERVICE_MANAGER_CHILDREN:
        rows.append([
            child,
            keys.get(f"wifi_companion_start.child.{child}.start_order", ""),
            keys.get(f"wifi_companion_start.child.{child}.observable", ""),
            keys.get(f"wifi_companion_start.child.{child}.postflight_safe", ""),
            keys.get(f"wifi_hal_composite_child.{child}.selinux.exec", ""),
            keys.get(f"capture.wifi_hal_composite_{child}.fd_links.entry_03.target", ""),
        ])
    return rows


def context_file_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for context_file in CONTEXT_FILES:
        rows.append([
            context_file,
            keys.get(f"context.{context_file}.exists", ""),
            keys.get(f"context.{context_file}.access_r", ""),
            keys.get(f"context.{context_file}.bytes", ""),
            keys.get(f"context.{context_file}.path", ""),
        ])
    return rows


def binder_device_rows(keys: dict[str, str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for device in ("binder", "hwbinder", "vndbinder"):
        rows.append([
            f"/dev/{device}",
            keys.get(f"context.dev_{device}.exists", ""),
            keys.get(f"context.dev_{device}.access_r", ""),
            keys.get(f"context.dev_{device}.mode", ""),
            keys.get(f"context.dev_{device}.rdev", ""),
        ])
    return rows


def find_registration_keys(keys: dict[str, str]) -> dict[str, bool]:
    lowered = {key.lower(): value.lower() for key, value in keys.items()}
    key_names = tuple(lowered)
    return {
        "service_list_snapshot_seen": any(
            token in key_name
            for key_name in key_names
            for token in ("servicemanager_list", "service_list", "registered_services")
        ),
        "vndservice_list_snapshot_seen": any(
            token in key_name
            for key_name in key_names
            for token in ("vndservicemanager_list", "vndservice_list", "vendor_service_list")
        ),
        "context_manager_probe_seen": any(
            "context_manager" in key_name or "context-manager" in key_name for key_name in key_names
        ),
        "property_area_present": key_bool(keys, "context.dev_properties.exists"),
        "property_service_shim_started": key_bool(keys, "wifi_hal_composite_start.property_service_shim.started"),
    }


def build_surface(v660_manifest: dict[str, Any], keys: dict[str, str]) -> dict[str, Any]:
    live_counts = nested(v660_manifest, ("live", "v655_counts"), {}) or {}
    live_surface = nested(v660_manifest, ("live", "v655_surface"), {}) or {}
    cnss_retry = live_surface.get("cnss_retry") or {}
    readiness = live_surface.get("vndservicemanager_readiness") or {}
    service74_gate = live_surface.get("service74_gate") or {}
    cnss_retry_order = intish(cnss_retry.get("retry_start_order"))
    vnd_ready_child_index = intish(readiness.get("child_index") or keys.get("wifi_companion_start.vndservicemanager_readiness.child_index"))
    vnd_start_order = intish(keys.get("wifi_companion_start.child.vndservicemanager.start_order"))
    return {
        "decision": v660_manifest.get("decision"),
        "pass": v660_manifest.get("pass"),
        "service74_seen": boolish(service74_gate.get("seen")),
        "service74_open": boolish(service74_gate.get("open")) or service74_gate.get("status") == "open",
        "service74_wait_ms": service74_gate.get("wait_ms"),
        "service_manager_started": boolish(live_surface.get("service_manager_started")),
        "vndservicemanager_ready": boolish(readiness.get("ready")),
        "vndservicemanager_observable": boolish(readiness.get("observable")),
        "vndservicemanager_ready_child_index": vnd_ready_child_index,
        "vndservicemanager_start_order": vnd_start_order,
        "cnss_retry_enabled": boolish(cnss_retry.get("enabled")),
        "cnss_retry_initial_cleanup_safe": boolish(cnss_retry.get("initial_cleanup_safe")),
        "cnss_retry_observable": boolish(cnss_retry.get("retry_observable")),
        "cnss_retry_postflight_safe": boolish(cnss_retry.get("retry_postflight_safe")),
        "cnss_retry_start_order": cnss_retry_order,
        "retry_after_vnd_ready": (
            cnss_retry_order is not None
            and vnd_ready_child_index is not None
            and cnss_retry_order > vnd_ready_child_index
        ),
        "retry_after_vnd_start": (
            cnss_retry_order is not None
            and vnd_start_order is not None
            and cnss_retry_order > vnd_start_order
        ),
        "cnss_retry_vndbinder_fd": "/dev/vndbinder" in keys.get(
            "capture.wifi_hal_composite_cnss_daemon_retry.fd_links.entry_15.target", ""
        ),
        "vndservicemanager_vndbinder_fd": "/dev/vndbinder" in keys.get(
            "capture.wifi_hal_composite_vndservicemanager.fd_links.entry_03.target", ""
        ),
        "counts": {
            "service_notifier_180": count_value(live_counts, "service_notifier_180"),
            "service_notifier_74": count_value(live_counts, "service_notifier_74"),
            "cnss_daemon_netlink": count_value(live_counts, "cnss_daemon_netlink"),
            "cnss_daemon_cld80211": count_value(live_counts, "cnss_daemon_cld80211"),
            "cnss_binder_transaction_failed": count_value(live_counts, "cnss_binder_transaction_failed"),
            "binder_transaction_failed": count_value(live_counts, "binder_transaction_failed"),
            "binder_ioctl_unsupported": count_value(live_counts, "binder_ioctl_unsupported"),
            "wlfw_start": count_value(live_counts, "wlfw_start"),
            "wlfw_service_request": count_value(live_counts, "wlfw_service_request"),
            "wlan_pd": count_value(live_counts, "wlan_pd"),
            "qmi_server_connected": count_value(live_counts, "qmi_server_connected"),
            "bdf_regdb": count_value(live_counts, "bdf_regdb"),
            "bdf_bdwlan": count_value(live_counts, "bdf_bdwlan"),
            "wlan_fw_ready": count_value(live_counts, "wlan_fw_ready"),
            "wlan0": count_value(live_counts, "wlan0"),
            "kernel_warning": count_value(live_counts, "kernel_warning"),
        },
    }


def build_checks(manifest: dict[str, Any]) -> dict[str, bool]:
    surface = manifest["v660_surface"]
    android_counts = manifest["android_reference"]["counts"]
    registration = manifest["registration_context"]
    return {
        "v660_binder_loop_persists": surface["decision"] == "v660-cnss-retry-binder-loop-persists",
        "service74_gate_preserved": surface["service74_seen"] and surface["service74_open"],
        "service_manager_trio_started": surface["service_manager_started"] and all(
            row[2] == "1" and row[3] == "1" for row in manifest["service_manager_rows"]
        ),
        "vndservicemanager_ready_before_retry": (
            surface["vndservicemanager_ready"]
            and surface["retry_after_vnd_ready"]
            and surface["retry_after_vnd_start"]
        ),
        "cnss_retry_observable_and_safe": (
            surface["cnss_retry_enabled"]
            and surface["cnss_retry_initial_cleanup_safe"]
            and surface["cnss_retry_observable"]
            and surface["cnss_retry_postflight_safe"]
        ),
        "cnss_retry_reaches_vndbinder": surface["cnss_retry_vndbinder_fd"],
        "vndservicemanager_reaches_vndbinder": surface["vndservicemanager_vndbinder_fd"],
        "binder_devnodes_present": all(row[1] == "1" and row[2] == "1" for row in manifest["binder_device_rows"]),
        "selinux_context_files_present": all(row[1] == "1" and row[2] == "1" for row in manifest["context_file_rows"]),
        "native_cnss_binder_tx_blocks_wlfw": (
            surface["counts"]["cnss_binder_transaction_failed"] > 0
            and surface["counts"]["wlfw_start"] == 0
            and surface["counts"]["wlan_pd"] == 0
            and surface["counts"]["qmi_server_connected"] == 0
        ),
        "android_wlfw_continues_without_cnss_binder_tx": (
            android_counts.get("cnss_wlfw_start", 0) > 0
            and android_counts.get("wlan_pd", 0) > 0
            and android_counts.get("qmi_server_connected", 0) > 0
            and android_counts.get("cnss_binder_transaction_failed", 0) == 0
        ),
        "dynamic_registration_snapshot_missing": not (
            registration["service_list_snapshot_seen"]
            or registration["vndservice_list_snapshot_seen"]
            or registration["context_manager_probe_seen"]
        ),
        "property_namespace_not_mounted": not registration["property_area_present"],
        "property_service_shim_disabled": not registration["property_service_shim_started"],
    }


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    checks = manifest["checks"]
    surface = manifest["v660_surface"]
    registration = manifest["registration_context"]
    android_counts = manifest["android_reference"]["counts"]
    native_counts = surface["counts"]
    return [
        [
            "readiness/order",
            "ruled out as primary blocker",
            (
                f"vnd_ready={surface['vndservicemanager_ready']} "
                f"retry_order={surface['cnss_retry_start_order']} "
                f"ready_index={surface['vndservicemanager_ready_child_index']}"
            ),
            "do not repeat readiness-only or unchanged CNSS retry",
        ],
        [
            "binder devnodes and SELinux context files",
            "present",
            (
                f"devnodes={checks['binder_devnodes_present']} "
                f"context_files={checks['selinux_context_files_present']}"
            ),
            "next gate should inspect dynamic registration rather than remounting devnodes",
        ],
        [
            "native retry stop condition",
            "active blocker",
            (
                f"cnss_tx={native_counts['cnss_binder_transaction_failed']} "
                f"wlfw={native_counts['wlfw_start']} wlan_pd={native_counts['wlan_pd']} "
                f"qmi={native_counts['qmi_server_connected']}"
            ),
            "capture vendor binder registration/context before another retry changes behavior",
        ],
        [
            "Android continuation",
            "reference positive",
            (
                f"wlfw={android_counts.get('cnss_wlfw_start', 0)} "
                f"wlan_pd={android_counts.get('wlan_pd', 0)} "
                f"qmi={android_counts.get('qmi_server_connected', 0)} "
                f"cnss_tx={android_counts.get('cnss_binder_transaction_failed', 0)}"
            ),
            "generic binder ioctl noise is not enough to explain native stop",
        ],
        [
            "dynamic service registration",
            "not captured yet",
            (
                f"service_list={registration['service_list_snapshot_seen']} "
                f"vndservice_list={registration['vndservice_list_snapshot_seen']} "
                f"context_manager={registration['context_manager_probe_seen']}"
            ),
            "add bounded service registry/context snapshot gate",
        ],
        [
            "property namespace",
            "candidate gap",
            (
                f"dev_properties={registration['property_area_present']} "
                f"property_shim={registration['property_service_shim_started']}"
            ),
            "snapshot property area and service-context dependencies before HAL",
        ],
    ]


def marker_rows(manifest: dict[str, Any]) -> list[list[str]]:
    native_counts = manifest["v660_surface"]["counts"]
    android_counts = manifest["android_reference"]["counts"]
    rows: list[list[str]] = []
    for native_name, android_name in (
        ("service_notifier_74", "service_notifier_74"),
        ("cnss_daemon_netlink", "cnss_daemon_netlink"),
        ("cnss_binder_transaction_failed", "cnss_binder_transaction_failed"),
        ("binder_ioctl_unsupported", "generic_binder_ioctl_unsupported"),
        ("wlfw_start", "cnss_wlfw_start"),
        ("wlan_pd", "wlan_pd"),
        ("qmi_server_connected", "qmi_server_connected"),
        ("bdf_regdb", "bdf_regdb"),
        ("bdf_bdwlan", "bdf_bdwlan"),
        ("wlan_fw_ready", "wlan_fw_ready"),
        ("wlan0", "wlan0"),
    ):
        rows.append([
            native_name,
            str(native_counts.get(native_name, 0)),
            str(android_counts.get(android_name, 0)),
        ])
    return rows


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    required = (
        "v660_binder_loop_persists",
        "service74_gate_preserved",
        "service_manager_trio_started",
        "vndservicemanager_ready_before_retry",
        "cnss_retry_observable_and_safe",
        "cnss_retry_reaches_vndbinder",
        "vndservicemanager_reaches_vndbinder",
        "binder_devnodes_present",
        "selinux_context_files_present",
        "native_cnss_binder_tx_blocks_wlfw",
        "android_wlfw_continues_without_cnss_binder_tx",
    )
    if all(checks[name] for name in required):
        return (
            "v661-binder-registration-context-gap-classified",
            True,
            (
                "V660 proves service 74, service-manager trio startup, "
                "vndservicemanager readiness, and fresh cnss retry are not enough; "
                "the remaining native-only gap is dynamic vendor binder registration, "
                "context-manager state, or property namespace visibility before WLFW."
            ),
            (
                "plan V662 as a bounded service-registry/property-context snapshot "
                "gate before any Wi-Fi HAL, scan/connect, credentials, DHCP, routes, "
                "or external ping"
            ),
        )

    if not checks["android_wlfw_continues_without_cnss_binder_tx"]:
        return (
            "v661-android-reference-gap-needs-recapture",
            False,
            "Android reference does not prove WLFW continuation strongly enough for this comparison",
            "recapture Android binder/service context read-only before another native live retry",
        )

    return (
        "v661-v660-evidence-incomplete",
        False,
        "V660 evidence does not prove all readiness, retry, and binder-surface prerequisites",
        "inspect V660 helper and dmesg before choosing another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v654_manifest = load_json(args.v654_manifest)
    v659_manifest = load_json(args.v659_manifest)
    v660_manifest = load_json(args.v660_manifest)
    keys = helper_keys(args.v660_helper)
    android_text = v654.read_text(args.android_audio_dmesg) + "\n" + v654.read_text(args.android_unfiltered_dmesg)
    native_text = v654.read_text(args.v660_dmesg)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v654_manifest": str(repo_path(args.v654_manifest)),
            "v659_manifest": str(repo_path(args.v659_manifest)),
            "v660_manifest": str(repo_path(args.v660_manifest)),
            "v660_dmesg": str(repo_path(args.v660_dmesg)),
            "v660_helper": str(repo_path(args.v660_helper)),
            "android_audio_dmesg": str(repo_path(args.android_audio_dmesg)),
            "android_unfiltered_dmesg": str(repo_path(args.android_unfiltered_dmesg)),
        },
        "prior": {
            "v654": {"decision": v654_manifest.get("decision"), "pass": v654_manifest.get("pass")},
            "v659": {"decision": v659_manifest.get("decision"), "pass": v659_manifest.get("pass")},
            "v660": {"decision": v660_manifest.get("decision"), "pass": v660_manifest.get("pass")},
        },
        "v660_surface": build_surface(v660_manifest, keys),
        "native_v660": source_summary(native_text, "native-v660"),
        "android_reference": source_summary(android_text, "android-v649"),
        "registration_context": find_registration_keys(keys),
        "service_manager_rows": service_child_rows(keys),
        "binder_device_rows": binder_device_rows(keys),
        "context_file_rows": context_file_rows(keys),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    manifest["checks"] = build_checks(manifest)
    manifest["evidence_rows"] = evidence_rows(manifest)
    manifest["marker_rows"] = marker_rows(manifest)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v661-binder-registration-context-classifier-plan-ready",
            True,
            "plan-only; no device contact, no daemon start, no Wi-Fi bring-up",
            "run V661 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V661 Binder Registration Context Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Marker Matrix",
        "",
        markdown_table(["marker", "native_v660_count", "android_reference_count"], manifest["marker_rows"]),
        "",
        "## Service Managers",
        "",
        markdown_table(
            ["child", "start_order", "observable", "postflight_safe", "selinux_exec", "binder_fd"],
            manifest["service_manager_rows"],
        ),
        "",
        "## Binder Devices",
        "",
        markdown_table(["device", "exists", "access_r", "mode", "rdev"], manifest["binder_device_rows"]),
        "",
        "## Service Context Files",
        "",
        markdown_table(["file", "exists", "access_r", "bytes", "path"], manifest["context_file_rows"]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
