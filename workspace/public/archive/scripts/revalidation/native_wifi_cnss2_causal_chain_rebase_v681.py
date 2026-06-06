#!/usr/bin/env python3
"""V681 host-only cnss2/WLFW causal-chain rebase classifier.

This classifier consumes existing V667/V668/V669/V680 evidence and re-routes
the next Wi-Fi gate after the clarified dependency model:
service-notifier 180/74 visibility is not equivalent to WLFW service 69
publication or QCA6390 firmware readiness.

It does not contact the device, mount filesystems, start services, scan/connect,
use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v681-cnss2-causal-chain-rebase")
DEFAULT_V667_MANIFEST = Path("tmp/wifi/v667-cnss2-pd-notifier-classifier/manifest.json")
DEFAULT_V668_MANIFEST = Path("tmp/wifi/v668-cnss2-focused-capture-live/manifest.json")
DEFAULT_V669_MANIFEST = Path("tmp/wifi/v669-android-cnss2-runtime-delta/manifest.json")
DEFAULT_V680_MANIFEST = Path("tmp/wifi/v680-binder-debugfs-gap/manifest.json")

CNSS2_SOURCE_URLS = {
    "cnss2_kconfig": (
        "https://android.googlesource.com/kernel/msm-modules/wlan-platform/"
        "+/refs/heads/android-msm-eos-android13-wear-kr3-pixel-watch/cnss2/Kconfig"
    ),
    "wlfw_service_locator": "docs/reports/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_2026-05-19.md",
    "v666_hypothesis": "docs/reports/NATIVE_INIT_V666_REPAIRED_PRIVATE_CNSS_RETRY_LIVE_2026-05-24.md",
}

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "sysfs write",
    "DSP boot-node write",
    "esoc0 open",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v667-manifest", type=Path, default=DEFAULT_V667_MANIFEST)
    parser.add_argument("--v668-manifest", type=Path, default=DEFAULT_V668_MANIFEST)
    parser.add_argument("--v669-manifest", type=Path, default=DEFAULT_V669_MANIFEST)
    parser.add_argument("--v680-manifest", type=Path, default=DEFAULT_V680_MANIFEST)
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
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready", "open"}


def key_counts(v667: dict[str, Any], v668: dict[str, Any], v669: dict[str, Any], v680: dict[str, Any]) -> dict[str, Any]:
    v667_counts = nested(v667, ("parsed", "counts"), {}) or {}
    v668_counts = nested(v668, ("live", "markers", "counts"), {}) or {}
    v668_v655_counts = nested(v668, ("live", "v655_counts"), {}) or {}
    native_v668 = nested(v669, ("native_v668", "counts"), {}) or {}
    android = nested(v669, ("android", "counts"), {}) or {}
    focus = nested(v668, ("live", "v668_cnss2_focus_surface"), {}) or {}
    registry = nested(v680, ("registry", "totals"), {}) or {}
    return {
        "v667": {
            "service_notifier_180": intish(v667_counts.get("service_notifier_180")),
            "service_notifier_74": intish(v667_counts.get("service_notifier_74")),
            "cnss2_pd_notifier": intish(v667_counts.get("cnss2_pd_notifier")),
            "cnss2_power_on": intish(v667_counts.get("cnss2_power_on")),
            "wlfw_service_69": intish(v667_counts.get("wlfw_service_69")),
            "bdf_bdwlan": intish(v667_counts.get("bdf_bdwlan")),
            "wlan0": intish(v667_counts.get("wlan0")),
        },
        "v668": {
            "service_notifier": intish(v668_counts.get("service_notifier")),
            "service_notifier_180": intish(v668_v655_counts.get("service_notifier_180")),
            "service_notifier_74": intish(v668_v655_counts.get("service_notifier_74")),
            "wlfw": intish(v668_counts.get("wlfw")),
            "wlan_pd": intish(v668_counts.get("wlan_pd")),
            "bdf": intish(v668_counts.get("bdf")),
            "wlan0": intish(v668_counts.get("wlan0")),
            "qmi_server_connected": intish(v668_counts.get("qmi_server_connected")),
            "focus_window_icnss": intish(nested(focus, ("window", "icnss_device_captured"), 0)),
            "focus_window_qca6390": intish(nested(focus, ("window", "qca6390_device_captured"), 0)),
            "focus_window_wlan0": intish(nested(focus, ("window", "wlan0_captured"), 0)),
        },
        "v669_android": {
            "wlfw_start": intish(android.get("wlfw_start")),
            "wlfw_service_request": intish(android.get("wlfw_service_request")),
            "wlan_pd_indication": intish(android.get("wlan_pd_indication")),
            "qmi_server_connected": intish(android.get("qmi_server_connected")),
            "bdf_bdwlan": intish(android.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(android.get("wlan_fw_ready")),
            "wlan0_event": intish(android.get("wlan0_event")),
        },
        "v669_native": {
            "wlfw_start": intish(native_v668.get("wlfw_start")),
            "wlfw_service_request": intish(native_v668.get("wlfw_service_request")),
            "wlan_pd_indication": intish(native_v668.get("wlan_pd_indication")),
            "qmi_server_connected": intish(native_v668.get("qmi_server_connected")),
            "bdf_bdwlan": intish(native_v668.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(native_v668.get("wlan_fw_ready")),
            "wlan0_event": intish(native_v668.get("wlan0_event")),
            "binder_transaction_failed": intish(native_v668.get("binder_transaction_failed")),
        },
        "v680": {
            "binder_debug_enoent": intish(registry.get("binder_debug_enoent")),
            "debug_path_blocks": intish(registry.get("debug_path_blocks")),
            "debug_nonzero": intish(registry.get("debug_nonzero")),
        },
    }


def build_checks(v667: dict[str, Any],
                 v668: dict[str, Any],
                 v669: dict[str, Any],
                 v680: dict[str, Any],
                 counts: dict[str, Any]) -> list[dict[str, Any]]:
    v667_counts = counts["v667"]
    v668_counts = counts["v668"]
    android_counts = counts["v669_android"]
    native_counts = counts["v669_native"]
    v680_counts = counts["v680"]
    native_zero = (
        native_counts["wlfw_start"] == 0
        and native_counts["qmi_server_connected"] == 0
        and native_counts["bdf_bdwlan"] == 0
        and native_counts["wlan0_event"] == 0
    )
    return [
        {
            "name": "source-evidence-ready",
            "status": "pass" if all(item.get("pass") for item in (v667, v668, v669, v680)) else "blocked",
            "detail": {
                "v667": v667.get("decision"),
                "v668": v668.get("decision"),
                "v669": v669.get("decision"),
                "v680": v680.get("decision"),
            },
            "next_step": "refresh missing input evidence before routing another live unit",
        },
        {
            "name": "service74-positive-but-cnss2-progression-absent",
            "status": "finding" if (
                v667_counts["service_notifier_180"] > 0
                and v667_counts["service_notifier_74"] > 0
                and v667_counts["cnss2_pd_notifier"] == 0
                and v667_counts["cnss2_power_on"] == 0
                and v667_counts["wlfw_service_69"] == 0
            ) else "review",
            "detail": v667_counts,
            "next_step": "treat userspace-visible service-notifier as insufficient proof of cnss2 callback/power progression",
        },
        {
            "name": "icnss-qca6390-sysfs-present-but-no-netdev",
            "status": "finding" if (
                v668_counts["focus_window_icnss"] > 0
                and v668_counts["focus_window_qca6390"] > 0
                and v668_counts["focus_window_wlan0"] == 0
                and v668_counts["wlfw"] == 0
            ) else "review",
            "detail": v668_counts,
            "next_step": "look for missing runtime trigger/state transition rather than platform device existence",
        },
        {
            "name": "android-advances-native-does-not",
            "status": "finding" if (
                android_counts["wlfw_start"] > 0
                and android_counts["qmi_server_connected"] > 0
                and android_counts["wlan0_event"] > 0
                and native_zero
            ) else "review",
            "detail": {"android": android_counts, "native": native_counts},
            "next_step": "compare the Android trigger edge before repeating Wi-Fi HAL/scan/connect",
        },
        {
            "name": "binder-debugfs-secondary-observability-gap",
            "status": "finding" if (
                v680_counts["binder_debug_enoent"] > 0
                and v680_counts["debug_nonzero"] == 0
                and native_zero
            ) else "review",
            "detail": v680_counts,
            "next_step": "keep Binder debugfs as diagnostic only until cnss2/WLFW progression moves",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v681-cnss2-causal-chain-rebase-plan-ready",
            True,
            "plan-only; host-only evidence routing with no device command",
            "run V681 host-only classifier, then plan a bounded cnss2/WLFW progression observer",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v681-cnss2-causal-chain-rebase-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh the missing V667/V668/V669/V680 evidence before live work",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "service74-positive-but-cnss2-progression-absent",
        "icnss-qca6390-sysfs-present-but-no-netdev",
        "android-advances-native-does-not",
        "binder-debugfs-secondary-observability-gap",
    }
    if required <= findings:
        return (
            "v681-cnss2-causal-chain-rebased",
            True,
            "Existing evidence supports a cnss2/WLFW progression gate after service-notifier 180/74; Binder debugfs is useful diagnostics but not the primary Wi-Fi bring-up gate.",
            "plan V682 around bounded cnss2/WLFW progression observation before any scan/connect or external ping",
        )
    return (
        "v681-cnss2-causal-chain-review",
        False,
        "existing evidence did not fully match the expected causal-chain pattern",
        "inspect V667/V668/V669/V680 manifests manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v667 = load_json(args.v667_manifest)
    v668 = load_json(args.v668_manifest)
    v669 = load_json(args.v669_manifest)
    v680 = load_json(args.v680_manifest)
    counts = key_counts(v667, v668, v669, v680)
    checks = build_checks(v667, v668, v669, v680, counts)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v681",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v667_manifest": str(repo_path(args.v667_manifest)),
            "v668_manifest": str(repo_path(args.v668_manifest)),
            "v669_manifest": str(repo_path(args.v669_manifest)),
            "v680_manifest": str(repo_path(args.v680_manifest)),
        },
        "source_references": CNSS2_SOURCE_URLS,
        "counts": counts,
        "checks": checks,
        "causal_chain": [
            "modem ONLINE",
            "service-locator can resolve WLAN-PD location",
            "service-notifier 180/74 become visible",
            "cnss2/icnss kernel progression should power QCA6390",
            "QCA6390 WLFW boot should publish service 69",
            "BDF download, firmware-ready, and wlan0 should follow",
        ],
        "routing": {
            "primary_next": "cnss2/WLFW progression observer",
            "secondary_next": "private Binder debugfs only if Binder transaction attribution is still needed",
            "do_not_repeat": "old V666/V667-style Binder-only retry without a new cnss2 progression signal",
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
    count_rows: list[list[str]] = []
    for group, counts in manifest["counts"].items():
        for key, value in counts.items():
            count_rows.append([group, key, str(value)])
    return "\n".join([
        "# V681 cnss2/WLFW Causal-chain Rebase",
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
        "## Causal Chain",
        "",
        "\n".join(f"{idx}. {item}" for idx, item in enumerate(manifest["causal_chain"], 1)),
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Key Counts",
        "",
        markdown_table(["source", "marker", "count"], count_rows),
        "",
        "## Routing",
        "",
        markdown_table(["item", "value"], [[key, value] for key, value in manifest["routing"].items()]),
        "",
        "## Interpretation",
        "",
        "- V667/V668 already cover the proposed cnss2 `pd_notifier` and modem-state read-only question.",
        "- V669 proves Android advances through WLFW/BDF/`wlan0` while native remains before WLFW despite visible icnss/QCA6390 platform sysfs.",
        "- V680 Binder debugfs absence is a diagnostic visibility gap; it does not by itself explain missing WLFW service `69`.",
        "- The next bounded unit should observe cnss2/WLFW progression, not repeat an old V666-style Binder-only retry.",
        "",
        "## References",
        "",
        "\n".join(f"- {key}: `{value}`" for key, value in manifest["source_references"].items()),
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
