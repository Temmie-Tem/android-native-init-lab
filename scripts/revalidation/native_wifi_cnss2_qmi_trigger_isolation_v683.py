#!/usr/bin/env python3
"""V683 host-only cnss2/QMI trigger isolation classifier.

This classifier consumes V682, V651, V654, and V669 evidence to decide whether
the missing pre-WLFW trigger is still a lower cnss2/QCA6390 power problem or a
native-only cnss-daemon vendor Binder continuation problem. It does not contact
the device, start daemons, mount filesystems, scan/connect, use credentials, run
DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v683-cnss2-qmi-trigger-isolation")
DEFAULT_V682_MANIFEST = Path("tmp/wifi/v682-cnss2-wlfw-progression-observer-live/manifest.json")
DEFAULT_V651_MANIFEST = Path("tmp/wifi/v651-cnss-wlfw-continuation/manifest.json")
DEFAULT_V654_MANIFEST = Path("tmp/wifi/v654-binder-runtime-mismatch-classifier/manifest.json")
DEFAULT_V669_MANIFEST = Path("tmp/wifi/v669-android-cnss2-runtime-delta/manifest.json")

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v682-manifest", type=Path, default=DEFAULT_V682_MANIFEST)
    parser.add_argument("--v651-manifest", type=Path, default=DEFAULT_V651_MANIFEST)
    parser.add_argument("--v654-manifest", type=Path, default=DEFAULT_V654_MANIFEST)
    parser.add_argument("--v669-manifest", type=Path, default=DEFAULT_V669_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def build_surface(v682: dict[str, Any], v651: dict[str, Any], v654: dict[str, Any], v669: dict[str, Any]) -> dict[str, Any]:
    v682_counts = nested(v682, ("arm_v682", "counts"), {}) or {}
    v682_markers = nested(v682, ("arm_v682", "markers"), {}) or {}
    v651_android = nested(v651, ("android", "counts"), {}) or {}
    v651_native = nested(v651, ("native_v644", "counts"), {}) or nested(v651, ("native", "counts"), {}) or {}
    v651_deltas_android = nested(v651, ("android", "deltas_ms"), {}) or {}
    v651_deltas_native = nested(v651, ("native_v644", "deltas_ms"), {}) or nested(v651, ("native", "deltas_ms"), {}) or {}
    v654_checks = v654.get("checks") if isinstance(v654.get("checks"), dict) else {}
    v669_android = nested(v669, ("android", "counts"), {}) or {}
    v669_native = nested(v669, ("native_v668", "counts"), {}) or {}
    return {
        "v682": {
            "decision": v682.get("decision", ""),
            "pass": boolish(v682.get("pass")),
            "service74": intish(v682_counts.get("service_notifier_74")),
            "cnss_netlink": intish(v682_counts.get("cnss_daemon_netlink")),
            "cnss_cld80211": intish(v682_counts.get("cnss_daemon_cld80211")),
            "cnss_binder_tx": intish(v682_counts.get("cnss_binder_transaction_failed")),
            "qmi_server_connected": intish(v682_counts.get("qmi_server_connected")),
            "wlfw_start": intish(v682_counts.get("wlfw_start")),
            "wlfw_request": intish(v682_counts.get("wlfw_service_request")),
            "wlan_pd": intish(v682_counts.get("wlan_pd")),
            "bdf": intish(v682_counts.get("bdf_bdwlan")),
            "wlan0": intish(v682_counts.get("wlan0")),
            "qrtr_tx": intish(v682_markers.get("qrtr_tx")),
            "sysmon_qmi": intish(v682_markers.get("sysmon_qmi")),
            "focus_ready": boolish(nested(v682, ("arm_v682", "focus_ready"), False)),
        },
        "v651": {
            "decision": v651.get("decision", ""),
            "pass": boolish(v651.get("pass")),
            "android_wlfw": intish(v651_android.get("wlfw_start")),
            "android_wlan_pd": intish(v651_android.get("wlan_pd")),
            "android_qmi_server": intish(v651_android.get("qmi_server_connected")),
            "android_bdf": intish(v651_android.get("bdf_bdwlan")),
            "android_wlan0": intish(v651_android.get("wlan0")),
            "android_binder_tx": intish(v651_android.get("binder_transaction_failed")),
            "native_wlfw": intish(v651_native.get("wlfw_start")),
            "native_binder_tx": intish(v651_native.get("binder_transaction_failed")),
            "android_netlink_to_wlfw_ms": v651_deltas_android.get("cnss_daemon_netlink_to_wlfw_start"),
            "native_netlink_to_binder_tx_ms": v651_deltas_native.get("cnss_daemon_netlink_to_binder_transaction"),
        },
        "v654": {
            "decision": v654.get("decision", ""),
            "pass": boolish(v654.get("pass")),
            "native_cnss_binder_transaction_blocks_wlfw": boolish(v654_checks.get("native_cnss_binder_transaction_blocks_wlfw")),
            "android_cnss_binder_transaction_absent": boolish(v654_checks.get("android_cnss_binder_transaction_absent")),
            "vndservicemanager_readiness_unproven": boolish(v654_checks.get("vndservicemanager_readiness_unproven")),
            "v653_service_manager_trio_observable": boolish(v654_checks.get("v653_service_manager_trio_observable")),
        },
        "v669": {
            "decision": v669.get("decision", ""),
            "pass": boolish(v669.get("pass")),
            "android_wlfw": intish(v669_android.get("wlfw_start")),
            "android_qmi_server": intish(v669_android.get("qmi_server_connected")),
            "android_bdf": intish(v669_android.get("bdf_bdwlan")),
            "android_wlan0": intish(v669_android.get("wlan0_event")),
            "native_wlfw": intish(v669_native.get("wlfw_start")),
            "native_qmi_server": intish(v669_native.get("qmi_server_connected")),
            "native_wlan0": intish(v669_native.get("wlan0_event")),
            "native_binder_tx": intish(v669_native.get("binder_transaction_failed")),
        },
    }


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    v682 = surface["v682"]
    v651 = surface["v651"]
    v654 = surface["v654"]
    v669 = surface["v669"]
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if all(item["pass"] for item in (v682, v651, v654, v669)) else "blocked",
            "detail": {
                "v682": v682["decision"],
                "v651": v651["decision"],
                "v654": v654["decision"],
                "v669": v669["decision"],
            },
            "next_step": "refresh missing manifests before V683 routing",
        },
        {
            "name": "native-lower-path-reaches-cnss-before-wlfw",
            "status": "finding" if (
                v682["service74"] > 0
                and v682["cnss_netlink"] > 0
                and v682["focus_ready"]
                and v682["wlfw_start"] == 0
                and v682["qmi_server_connected"] == 0
            ) else "review",
            "detail": v682,
            "next_step": "do not start scan/connect until native reaches WLFW or wlan0",
        },
        {
            "name": "android-cnss-continuation-proven",
            "status": "finding" if (
                v651["android_wlfw"] > 0
                and v651["android_qmi_server"] > 0
                and v651["android_bdf"] > 0
                and v651["android_wlan0"] > 0
                and v651["android_binder_tx"] == 0
            ) else "review",
            "detail": v651,
            "next_step": "refresh Android continuation evidence if missing",
        },
        {
            "name": "native-cnss-binder-precedes-missing-wlfw",
            "status": "finding" if (
                v682["cnss_binder_tx"] > 0
                and v651["native_binder_tx"] > 0
                and v651["native_wlfw"] == 0
                and v654["native_cnss_binder_transaction_blocks_wlfw"]
            ) else "review",
            "detail": {"v682": v682, "v651": v651, "v654": v654},
            "next_step": "capture or repair the cnss-daemon vndbinder transaction target",
        },
        {
            "name": "direct-qca-power-retry-not-yet-justified",
            "status": "finding" if (
                v669["android_wlfw"] > 0
                and v669["native_wlfw"] == 0
                and v682["focus_ready"]
                and v682["wlfw_start"] == 0
            ) else "review",
            "detail": v669,
            "next_step": "avoid direct QCA/sysfs writes until cnss-daemon continuation is explained",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v683-cnss2-qmi-trigger-isolation-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V683 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v683-cnss2-qmi-trigger-isolation-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh input evidence before next live unit",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "native-lower-path-reaches-cnss-before-wlfw",
        "android-cnss-continuation-proven",
        "native-cnss-binder-precedes-missing-wlfw",
        "direct-qca-power-retry-not-yet-justified",
    }
    if required <= findings:
        return (
            "v683-cnss-daemon-vndbinder-pre-wlfw-trigger-classified",
            True,
            "V682 confirms service74/CNSS/focused sysfs without WLFW, while Android continues from CNSS to WLFW without a CNSS binder transaction; the next trigger to isolate is the native cnss-daemon vndbinder transaction before WLFW.",
            "plan V684 as a narrow cnss-daemon vndbinder transaction target capture/repair gate; keep direct QCA writes and scan/connect blocked",
        )
    return (
        "v683-cnss2-qmi-trigger-isolation-review",
        False,
        "evidence did not isolate a single pre-WLFW trigger",
        "inspect V682/V651/V654/V669 manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v682 = load_json(args.v682_manifest)
    v651 = load_json(args.v651_manifest)
    v654 = load_json(args.v654_manifest)
    v669 = load_json(args.v669_manifest)
    surface = build_surface(v682, v651, v654, v669)
    checks = build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v683",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v682_manifest": str(repo_path(args.v682_manifest)),
            "v651_manifest": str(repo_path(args.v651_manifest)),
            "v654_manifest": str(repo_path(args.v654_manifest)),
            "v669_manifest": str(repo_path(args.v669_manifest)),
        },
        "surface": surface,
        "checks": checks,
        "routing": {
            "primary_next": "cnss-daemon vndbinder transaction target capture or repair",
            "secondary_observation": "private Binder debugfs only if needed to identify the transaction target",
            "avoid_next": "direct QCA/sysfs power writes, supplicant, scan/connect, DHCP, external ping",
        },
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "mount_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    surface_rows: list[list[str]] = []
    for group, values in manifest["surface"].items():
        for key, value in values.items():
            surface_rows.append([group, key, str(value)])
    return "\n".join([
        "# V683 cnss2/QMI Trigger Isolation",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Surface",
        "",
        markdown_table(["source", "key", "value"], surface_rows),
        "",
        "## Routing",
        "",
        markdown_table(["item", "value"], [[key, value] for key, value in manifest["routing"].items()]),
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
