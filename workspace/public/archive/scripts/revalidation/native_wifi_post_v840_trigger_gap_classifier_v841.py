#!/usr/bin/env python3
"""V841 host-only classifier after V840 provider-first prearm still saw UNINIT.

V840 closed the combined provider-first CNSS retry plus prearmed
service-notifier listener timing window.  This classifier compares that result
with the Android lower-stack positive evidence and already-closed side branches
to select the next non-repeating pre-WLFW gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v841-post-v840-trigger-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v841-post-v840-trigger-gap-classifier.txt")

DEFAULT_V840_MANIFEST = Path("tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json")
DEFAULT_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V618_MANIFEST = Path("tmp/wifi/v618-rfs-alias-order-classifier/manifest.json")
DEFAULT_V746_MANIFEST = Path("tmp/wifi/v746-mdm-helper-sysmon-live-current/manifest.json")
DEFAULT_V764_MANIFEST = Path("tmp/wifi/v764-mdm-helper-service180-retry/manifest.json")


EXPECTED = {
    "v840": "v840-provider-first-prearmed-no-indication",
    "v622": "v622-mdm-helper-post-notifier-not-root-trigger",
    "v618": "v618-rfs-alias-pd-mapper-order-gap-classified",
    "v746": "v746-mdm-helper-started-no-lower-progress",
    "v764": "v764-mdm-helper-started-no-lower-progress",
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v840-manifest", type=Path, default=DEFAULT_V840_MANIFEST)
    parser.add_argument("--v622-manifest", type=Path, default=DEFAULT_V622_MANIFEST)
    parser.add_argument("--v618-manifest", type=Path, default=DEFAULT_V618_MANIFEST)
    parser.add_argument("--v746-manifest", type=Path, default=DEFAULT_V746_MANIFEST)
    parser.add_argument("--v764-manifest", type=Path, default=DEFAULT_V764_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def float_value(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def input_item(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": data.get("path"),
        "exists": data.get("exists", False),
        "decision": data.get("decision", ""),
        "pass": bool_value(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
    }


def android_v622_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") if isinstance(manifest.get("android_summary"), dict) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    timing = summary.get("timing") if isinstance(summary.get("timing"), dict) else {}
    deltas = summary.get("deltas_ms") if isinstance(summary.get("deltas_ms"), dict) else {}
    props = summary.get("props") if isinstance(summary.get("props"), dict) else {}
    service180_to_wlfw = float_value(deltas.get("service_notifier_180_to_wlfw_start"))
    service180_to_wlanpd = float_value(deltas.get("service_notifier_180_to_wlan_pd"))
    service180_to_esoc0 = float_value(timing.get("service_notifier_180_to_sysmon_esoc0_ms"))
    return {
        "counts": {
            key: int_value(counts.get(key))
            for key in (
                "service_notifier_180",
                "service_notifier_74",
                "wlfw_start",
                "wlfw_thread",
                "wlan_pd",
                "wlan_pd_ack_180",
                "qmi_server_connected",
                "bdf_regdb",
                "bdf_bdwlan",
                "wlan_fw_ready",
                "wlan0",
                "sysmon_modem",
                "sysmon_esoc0",
                "rmt_storage_ready",
                "rmt_storage_open",
                "cnss_daemon_netlink",
                "cnss_diag_netlink",
            )
        },
        "deltas_ms": {
            "service180_to_wlfw_start": service180_to_wlfw,
            "service180_to_wlan_pd": service180_to_wlanpd,
            "service180_to_qmi_server_connected": float_value(deltas.get("service_notifier_180_to_qmi_server_connected")),
            "wlan_pd_to_qmi_server_connected": float_value(deltas.get("wlan_pd_to_qmi_server_connected")),
            "sysmon_modem_to_service_notifier_180": float_value(deltas.get("sysmon_modem_to_service_notifier_180")),
            "sysmon_modem_to_rmt_storage_ready": float_value(deltas.get("sysmon_modem_to_rmt_storage_ready")),
            "service180_to_sysmon_esoc0": service180_to_esoc0,
        },
        "ordering": {
            "wlfw_start_before_wlan_pd": (
                service180_to_wlfw is not None
                and service180_to_wlanpd is not None
                and service180_to_wlfw < service180_to_wlanpd
            ),
            "sysmon_esoc0_after_wlan_pd": (
                service180_to_esoc0 is not None
                and service180_to_wlanpd is not None
                and service180_to_esoc0 > service180_to_wlanpd
            ),
        },
        "props": {
            key: props.get(key, "")
            for key in (
                "ro.baseband",
                "ro.boot.baseband",
                "init.svc.vendor.qrtr-ns",
                "init.svc.vendor.rmt_storage",
                "init.svc.vendor.tftp_server",
                "init.svc.vendor.pd_mapper",
                "init.svc.vendor.mdm_helper",
                "init.svc.cnss_diag",
                "init.svc.cnss-daemon",
            )
        },
    }


def native_v840_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    provider = nested(manifest, "provider_first_prearmed", "provider_manifest") or {}
    live = provider.get("live") if isinstance(provider.get("live"), dict) else {}
    counts = live.get("v655_counts") if isinstance(live.get("v655_counts"), dict) else {}
    markers = nested(live, "markers", "counts") or {}
    surface = live.get("v655_surface") if isinstance(live.get("v655_surface"), dict) else {}
    listener = nested(manifest, "provider_first_prearmed", "service_notifier") or {}
    timing = nested(manifest, "provider_first_prearmed", "timing") or {}
    safety = manifest.get("safety") if isinstance(manifest.get("safety"), dict) else {}
    return {
        "provider_decision": nested(manifest, "provider_first_prearmed", "decision"),
        "provider_reason": nested(manifest, "provider_first_prearmed", "reason"),
        "listener": {
            "response_success": int_value(listener.get("response_success")),
            "response_state": listener.get("response_curr_state_name", ""),
            "response_raw": listener.get("response_curr_state", ""),
            "indication_seen": int_value(listener.get("indication_seen")),
            "listener_open_at_service74": timing.get("listener_open_at_service74"),
            "held_5s_after_service74": timing.get("held_5s_after_service74"),
            "send_before_to_service74_ms": timing.get("send_before_to_service74_ms"),
            "close_after_service74_ms": timing.get("close_after_service74_ms"),
        },
        "counts": {
            key: int_value(counts.get(key))
            for key in (
                "service_notifier_180",
                "service_notifier_74",
                "cnss_daemon_netlink",
                "cnss_daemon_cld80211",
                "cnss_binder_transaction_failed",
                "binder_transaction_failed",
                "wlfw_start",
                "wlfw_service_request",
                "wlan_pd",
                "qmi_server_connected",
                "bdf_regdb",
                "bdf_bdwlan",
                "wlan_fw_ready",
                "wlan0",
                "kernel_warning",
            )
        },
        "markers": {
            key: int_value(markers.get(key))
            for key in (
                "qrtr_rx",
                "qrtr_tx",
                "sysmon_qmi",
                "service_notifier",
                "wlan_pd",
                "qmi_server_connected",
                "wlfw",
                "bdf",
                "wlan_fw_ready",
                "wlan0",
            )
        },
        "surface": {
            "order": surface.get("order", ""),
            "helper_result": live.get("helper_result", ""),
            "mss_after_companion": live.get("mss_after_companion", ""),
            "mdm3_after_companion": live.get("mdm3_after_companion", ""),
            "service74_gate": surface.get("service74_gate", {}),
            "cnss_retry": surface.get("cnss_retry", {}),
        },
        "safety": {
            key: bool_value(safety.get(key))
            for key in (
                "device_commands_executed",
                "service_manager_start_executed",
                "peripheral_manager_start_executed",
                "cnss_daemon_retry_executed",
                "service_notifier_listener_executed",
                "wifi_hal_start_executed",
                "scan_connect_executed",
                "credential_use_executed",
                "dhcp_route_executed",
                "external_ping_executed",
                "esoc0_open_executed",
                "subsystem_write_executed",
                "module_load_unload_executed",
                "boot_image_write_executed",
                "partition_write_executed",
                "custom_kernel_flash_executed",
            )
        },
    }


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": name,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v840 = load_json(args.v840_manifest)
    v622 = load_json(args.v622_manifest)
    v618 = load_json(args.v618_manifest)
    v746 = load_json(args.v746_manifest)
    v764 = load_json(args.v764_manifest)

    android = android_v622_summary(v622)
    native = native_v840_summary(v840)

    android_reaches_full_lower_path = (
        android["counts"]["service_notifier_180"] > 0
        and android["counts"]["service_notifier_74"] > 0
        and android["counts"]["wlfw_start"] > 0
        and android["counts"]["wlan_pd"] > 0
        and android["counts"]["qmi_server_connected"] > 0
        and android["counts"]["bdf_regdb"] > 0
        and android["counts"]["wlan0"] > 0
    )
    native_provider_prearm_closed = (
        v840.get("decision") == EXPECTED["v840"]
        and native["listener"]["response_state"] == "uninit"
        and native["listener"]["indication_seen"] == 0
        and native["listener"]["listener_open_at_service74"] is True
        and native["listener"]["held_5s_after_service74"] is True
        and native["counts"]["service_notifier_180"] > 0
        and native["counts"]["service_notifier_74"] > 0
        and native["counts"]["cnss_daemon_netlink"] > 0
        and native["counts"]["cnss_daemon_cld80211"] > 0
        and native["counts"]["wlfw_start"] == 0
        and native["counts"]["wlan_pd"] == 0
        and native["counts"]["wlan0"] == 0
    )
    rfs_closed = v618.get("decision") == EXPECTED["v618"] and bool_value(v618.get("pass"))
    mdm_helper_closed = (
        v746.get("decision") == EXPECTED["v746"]
        and bool_value(v746.get("pass"))
        and v764.get("decision") == EXPECTED["v764"]
        and bool_value(v764.get("pass"))
    )
    sysmon_esoc0_not_prereq = bool(android["ordering"]["sysmon_esoc0_after_wlan_pd"])
    android_wlfw_before_wlanpd = bool(android["ordering"]["wlfw_start_before_wlan_pd"])

    return {
        "inputs": {
            "v840": input_item(v840),
            "v622": input_item(v622),
            "v618": input_item(v618),
            "v746": input_item(v746),
            "v764": input_item(v764),
        },
        "signals": {
            "android_v622": android,
            "native_v840": native,
        },
        "derived": {
            "android_reaches_full_lower_path": android_reaches_full_lower_path,
            "native_provider_prearm_closed": native_provider_prearm_closed,
            "android_wlfw_start_before_wlan_pd": android_wlfw_before_wlanpd,
            "sysmon_esoc0_after_wlan_pd_on_android": sysmon_esoc0_not_prereq,
            "rfs_access_standalone_closed_by_v618": rfs_closed,
            "mdm_helper_retry_closed_by_v746_v764": mdm_helper_closed,
            "selected_next_gate": "v842-cnss-daemon-wlfw-start-precondition-classifier",
        },
        "candidate_matrix": [
            candidate(
                "repeat service-notifier listener hold",
                "reject",
                "V838 and V840 registered before service74, held through service74+5s, and still saw UNINIT",
                "do not rerun listener-only timing without a new lower trigger",
            ),
            candidate(
                "repeat provider-first CNSS retry",
                "reject",
                "V840 added provider-first service-manager/PeripheralManager plus CNSS retry and still got no wlfw_start, WLAN-PD, BDF, or wlan0",
                "move below CNSS daemon start into its missing pre-WLFW condition",
            ),
            candidate(
                "sysmon_esoc0 as prerequisite",
                "deprioritize",
                "Android V622 shows sysmon_esoc0 after WLAN-PD UP, so it is not proven as the pre-WLAN-PD trigger",
                "do not chase esoc0 before explaining why native cnss-daemon never reaches wlfw_start",
            ),
            candidate(
                "rfs_access standalone daemon",
                "reject",
                "V618 classified rfs_access as an alias/domain surface already covered by tftp_server/vendor_rfs_access",
                "keep tftp_server in the lower stack but do not add a duplicate rfs daemon",
            ),
            candidate(
                "mdm_helper retry",
                "reject",
                "V746 and V764 started mdm_helper under lower gates without mdm3/WLAN-PD/WLFW progress",
                "do not repeat blind mdm_helper starts",
            ),
            candidate(
                "Wi-Fi HAL / scan / connect / DHCP / external ping",
                "blocked",
                "native still lacks WLAN-PD UP, WLFW, BDF, wiphy, and wlan0",
                "keep final bring-up blocked until lower state advances",
            ),
            candidate(
                "cnss-daemon pre-WLFW start differential",
                "select-next",
                "Android emits cnss-daemon wlfw_start before WLAN-PD UP, while native cnss-daemon reaches netlink/cld80211 but never emits wlfw_start",
                "V842 should classify Android vs native cnss-daemon launch contract, properties, fds, SELinux domain, and exit reason before any HAL/connect action",
            ),
        ],
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    inputs = analysis["inputs"]
    for name, expected in EXPECTED.items():
        item = inputs[name]
        add_check(
            checks,
            f"{name}-input",
            "pass" if item.get("exists") and item.get("pass") and item.get("decision") == expected else "blocked",
            "blocker",
            f"decision={item.get('decision')} pass={item.get('pass')} expected={expected}",
            f"refresh {name} evidence before using V841",
        )
    derived = analysis["derived"]
    add_check(
        checks,
        "android-lower-positive",
        "pass" if derived["android_reaches_full_lower_path"] else "blocked",
        "blocker",
        str(analysis["signals"]["android_v622"]["counts"]),
        "refresh Android lower-stack evidence before selecting a native pre-WLFW gate",
    )
    add_check(
        checks,
        "native-v840-closed",
        "pass" if derived["native_provider_prearm_closed"] else "blocked",
        "blocker",
        str(analysis["signals"]["native_v840"]["counts"]),
        "complete V840 provider-first prearmed listener before selecting V842",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "V841 reads local evidence only",
        "keep V841 non-mutating",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v841-post-v840-trigger-gap-plan-ready",
            True,
            "plan-only; no device command, daemon start, Wi-Fi action, credential, route, ping, or flash executed",
            "run V841 host-only classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v841-post-v840-trigger-gap-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh prerequisite evidence before selecting a V842 gate",
        )
    return (
        "v841-cnss-wlfw-start-gap-selected",
        True,
        "V840 closes provider-first prearmed listener timing; Android reaches wlfw_start before WLAN-PD UP, while native cnss-daemon reaches netlink/cld80211 but never emits wlfw_start",
        "V842 should classify the cnss-daemon pre-WLFW launch/runtime contract before any Wi-Fi HAL, scan/connect, DHCP, or external ping",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V841 Post-V840 Trigger Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Derived",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["derived"].items()]),
        "",
        "## Android V622 Counts",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["signals"]["android_v622"]["counts"].items()]),
        "",
        "## Android V622 Timing",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["signals"]["android_v622"]["deltas_ms"].items()]),
        "",
        "## Native V840 Counts",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["signals"]["native_v840"]["counts"].items()]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason", "next"], [
            [row["candidate"], row["classification"], row["reason"], row["next_step"]]
            for row in analysis["candidate_matrix"]
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify(args)
    checks = build_checks(analysis)
    decision, passed, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v841",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
