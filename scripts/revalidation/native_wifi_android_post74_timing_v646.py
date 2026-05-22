#!/usr/bin/env python3
"""V646 host-only Android post-service74 timing comparison."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v646-android-post74-timing")
DEFAULT_V628_MANIFEST = Path("tmp/wifi/v628-service74-publisher-classifier/manifest.json")
DEFAULT_V644_MANIFEST = Path("tmp/wifi/v644-live-20260523-071610/manifest.json")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
MARKERS = (
    ("service_notifier_180", re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I)),
    ("service_notifier_74", re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I)),
    ("wlan_pd", re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I)),
    ("qmi_server_connected", re.compile(r"icnss_qmi: QMI Server Connected", re.I)),
    ("wlfw_start", re.compile(r"\bWLFW\b|wlfw", re.I)),
    ("kernel_warning", re.compile(r"WARNING: CPU|pm_qos_add_request|kernel/power/qos\.c:616", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v628-manifest", type=Path, default=DEFAULT_V628_MANIFEST)
    parser.add_argument("--v644-manifest", type=Path, default=DEFAULT_V644_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def line_ts(line: str) -> float | None:
    clean = ANSI_RE.sub("", line).strip()
    match = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", clean)
    return float(match.group(1)) if match else None


def first_times(text: str) -> dict[str, float | None]:
    found = {name: None for name, _ in MARKERS}
    for line in text.splitlines():
        for name, pattern in MARKERS:
            if found[name] is None and pattern.search(line):
                found[name] = line_ts(line)
    return found


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000, 3)


def subtract_ms(left: object, right: object) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 3)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v628 = load_json(args.v628_manifest)
    v644 = load_json(args.v644_manifest)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v646-android-post74-timing-plan-ready",
            True,
            "plan-only; no evidence classification executed",
            "run V646 host-only classifier",
        )
    else:
        if not v628.get("exists") or not v644.get("exists"):
            decision, pass_ok, reason, next_step = (
                "v646-evidence-missing",
                False,
                f"v628_exists={v628.get('exists')} v644_exists={v644.get('exists')}",
                "restore V628/V644 evidence before next gate",
            )
        else:
            android_deltas = ((v628.get("android_v622") or {}).get("deltas_ms") or {})
            v644_live = v644.get("live") or {}
            v644_times = first_times(str(v644_live.get("dmesg_delta") or ""))
            android_180_to_74 = android_deltas.get("service_notifier_180_to_service_notifier_74")
            android_74_to_wlfw = subtract_ms(android_deltas.get("service_notifier_180_to_wlfw_start"), android_180_to_74)
            android_74_to_wlan_pd = subtract_ms(android_deltas.get("service_notifier_180_to_wlan_pd"), android_180_to_74)
            android_74_to_qmi = subtract_ms(android_deltas.get("service_notifier_180_to_qmi_server_connected"), android_180_to_74)
            v644_74_to_warning = delta_ms(v644_times.get("kernel_warning"), v644_times.get("service_notifier_74"))
            if v644_74_to_warning is not None and android_74_to_wlan_pd is not None and v644_74_to_warning < 100 < android_74_to_wlan_pd:
                decision, pass_ok, reason, next_step = (
                    "v646-native-warning-preempts-android-post74-window",
                    True,
                    f"Android waits {android_74_to_wlan_pd}ms from service74 to WLAN-PD, but V644 warns after {v644_74_to_warning}ms",
                    "plan V647 warning-source classifier; do not repeat V644 or start HAL/qcwlanstate",
                )
            else:
                decision, pass_ok, reason, next_step = (
                    "v646-review-required",
                    False,
                    f"android_74_to_wlan_pd={android_74_to_wlan_pd} v644_74_to_warning={v644_74_to_warning}",
                    "inspect Android/V644 timing manually",
                )
    android_deltas = ((v628.get("android_v622") or {}).get("deltas_ms") or {})
    v644_times = first_times(str(((v644.get("live") or {}).get("dmesg_delta")) or ""))
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {"v628": v628.get("path"), "v644": v644.get("path")},
        "android": {
            "service180_to_74_ms": android_deltas.get("service_notifier_180_to_service_notifier_74"),
            "service74_to_wlfw_start_ms": subtract_ms(android_deltas.get("service_notifier_180_to_wlfw_start"), android_deltas.get("service_notifier_180_to_service_notifier_74")),
            "service74_to_wlan_pd_ms": subtract_ms(android_deltas.get("service_notifier_180_to_wlan_pd"), android_deltas.get("service_notifier_180_to_service_notifier_74")),
            "service74_to_qmi_server_connected_ms": subtract_ms(android_deltas.get("service_notifier_180_to_qmi_server_connected"), android_deltas.get("service_notifier_180_to_service_notifier_74")),
        },
        "v644": {
            "service74_to_warning_ms": delta_ms(v644_times.get("kernel_warning"), v644_times.get("service_notifier_74")),
            "service74_to_wlan_pd_ms": delta_ms(v644_times.get("wlan_pd"), v644_times.get("service_notifier_74")),
            "service74_to_qmi_server_connected_ms": delta_ms(v644_times.get("qmi_server_connected"), v644_times.get("service_notifier_74")),
            "first_times": v644_times,
            "counts": ((v644.get("live") or {}).get("v644_counts") or {}),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        ["Android service180->74", str(manifest["android"]["service180_to_74_ms"])],
        ["Android service74->wlfw_start", str(manifest["android"]["service74_to_wlfw_start_ms"])],
        ["Android service74->wlan_pd", str(manifest["android"]["service74_to_wlan_pd_ms"])],
        ["Android service74->qmi", str(manifest["android"]["service74_to_qmi_server_connected_ms"])],
        ["V644 service74->warning", str(manifest["v644"]["service74_to_warning_ms"])],
        ["V644 service74->wlan_pd", str(manifest["v644"]["service74_to_wlan_pd_ms"])],
        ["V644 service74->qmi", str(manifest["v644"]["service74_to_qmi_server_connected_ms"])],
    ]
    return "\n".join([
        "# V646 Android Post-Service74 Timing",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Timing",
        "",
        markdown_table(["item", "ms"], rows),
        "",
        "## Interpretation",
        "",
        "- Android has a long post-service74 window before WLAN-PD/WLFW/QMI.",
        "- V644 hits the warning almost immediately after service74 and never reaches WLAN-PD/WLFW/QMI.",
        "- The next gate must classify or avoid the warning source before any HAL/qcwlanstate/connect attempt.",
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
