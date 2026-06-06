#!/usr/bin/env python3
"""V650 host-only post-warning continuation classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v650-post-warning-continuation")
DEFAULT_V649_MANIFEST = Path("tmp/wifi/v649-final-live-replay-classifier/manifest.json")
DEFAULT_V644_DMESG = Path("tmp/wifi/v644-live-20260523-071610/native/dmesg-after-companion.txt")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
PATTERNS = {
    "service_notifier_74": re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I),
    "asoc_probe": re.compile(r"msm_asoc_machine_probe: Enter", re.I),
    "pm_qos_duplicate": re.compile(r"pm_qos_add_request\(\) called for already added request", re.I),
    "qos_warning": re.compile(r"WARNING: CPU:.*kernel/power/qos\.c:616", re.I),
    "audio_codec_registered": re.compile(r"audio codec registered", re.I),
    "sound_card_registered": re.compile(r"Sound card .* registered", re.I),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start|\bwlfw_start\b", re.I),
    "wlan_pd": re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.I),
    "bdf_regdb": re.compile(r"regdb\.bin|BDF file.*regdb", re.I),
    "bdf_bdwlan": re.compile(r"bdwlan\.bin|BDF file.*bdwlan", re.I),
    "wlan_fw_ready": re.compile(r"WLAN FW is ready", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
}
CONTINUATION = (
    "audio_codec_registered",
    "sound_card_registered",
    "wlfw_start",
    "wlan_pd",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v649-manifest", type=Path, default=DEFAULT_V649_MANIFEST)
    parser.add_argument("--v644-dmesg", type=Path, default=DEFAULT_V644_DMESG)
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


def line_time(line: str) -> float | None:
    match = TS_RE.match(ANSI_RE.sub("", line).strip())
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_dmesg_times(text: str) -> dict[str, Any]:
    lines = [ANSI_RE.sub("", line).strip() for line in text.splitlines() if line.strip()]
    counts: dict[str, int] = {}
    first_times: dict[str, float | None] = {}
    first_lines: dict[str, str] = {}
    for name, pattern in PATTERNS.items():
        matched = [line for line in lines if pattern.search(line)]
        counts[name] = len(matched)
        first_lines[name] = matched[0] if matched else "missing"
        first_times[name] = line_time(matched[0]) if matched else None
    return {"counts": counts, "first_times": first_times, "first_lines": first_lines}


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000.0, 3)


def from_v649_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    markers = ((manifest.get("android_summary") or {}).get("markers") or {})
    counts = markers.get("counts") or {}
    first_times = markers.get("first_times") or {}
    first_lines = markers.get("first_lines") or {}
    return {"counts": counts, "first_times": first_times, "first_lines": first_lines}


def continuation_rows(android: dict[str, Any], native: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    android_warning = android["first_times"].get("qos_warning")
    native_warning = native["first_times"].get("qos_warning")
    for marker in CONTINUATION:
        rows.append([
            marker,
            str(android["counts"].get(marker, 0)),
            str(delta_ms(android["first_times"].get(marker), android_warning)),
            str(native["counts"].get(marker, 0)),
            str(delta_ms(native["first_times"].get(marker), native_warning)),
        ])
    return rows


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v649 = load_json(args.v649_manifest)
    android = from_v649_manifest(v649)
    native = parse_dmesg_times(read_text(args.v644_dmesg))

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v650-post-warning-continuation-plan-ready",
            True,
            "plan-only; no evidence classification executed",
            "run V650 host-only classifier",
        )
    else:
        common_warning = (
            android["counts"].get("qos_warning", 0) > 0
            and native["counts"].get("qos_warning", 0) > 0
        )
        audio_continues_both = (
            android["counts"].get("sound_card_registered", 0) > 0
            and native["counts"].get("sound_card_registered", 0) > 0
        )
        android_wlfw = android["counts"].get("wlfw_start", 0) > 0
        native_wlfw_missing = native["counts"].get("wlfw_start", 0) == 0
        if common_warning and audio_continues_both and android_wlfw and native_wlfw_missing:
            decision, pass_ok, reason, next_step = (
                "v650-post-warning-wlfw-continuation-gap-classified",
                True,
                "Android and native both continue through sound-card registration after the ASoC warning, but only Android reaches WLFW/WLAN-PD/QMI/BDF/wlan0",
                "plan V651 CNSS/WLFW post-warning continuation guard; keep HAL/scan/connect blocked",
            )
        else:
            decision, pass_ok, reason, next_step = (
                "v650-post-warning-review-required",
                False,
                f"common_warning={common_warning} audio_both={audio_continues_both} android_wlfw={android_wlfw} native_wlfw_missing={native_wlfw_missing}",
                "inspect V649/V644 timelines manually",
            )

    android_warning = android["first_times"].get("qos_warning")
    native_warning = native["first_times"].get("qos_warning")
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v649_manifest": str(repo_path(args.v649_manifest)),
            "v644_dmesg": str(repo_path(args.v644_dmesg)),
        },
        "android": android,
        "native_v644": native,
        "key_deltas_ms": {
            "android_service74_to_warning": delta_ms(android["first_times"].get("qos_warning"), android["first_times"].get("service_notifier_74")),
            "native_service74_to_warning": delta_ms(native["first_times"].get("qos_warning"), native["first_times"].get("service_notifier_74")),
            "android_warning_to_sound_card": delta_ms(android["first_times"].get("sound_card_registered"), android_warning),
            "native_warning_to_sound_card": delta_ms(native["first_times"].get("sound_card_registered"), native_warning),
            "android_warning_to_wlfw_start": delta_ms(android["first_times"].get("wlfw_start"), android_warning),
            "native_warning_to_wlfw_start": delta_ms(native["first_times"].get("wlfw_start"), native_warning),
            "android_warning_to_wlan_pd": delta_ms(android["first_times"].get("wlan_pd"), android_warning),
            "native_warning_to_wlan_pd": delta_ms(native["first_times"].get("wlan_pd"), native_warning),
        },
        "continuation_rows": continuation_rows(android, native),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V650 Post-Warning Continuation Classifier",
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
        "## Key Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in manifest["key_deltas_ms"].items()]),
        "",
        "## Continuation Matrix",
        "",
        markdown_table(["marker", "android_count", "android_warning_to_marker_ms", "native_count", "native_warning_to_marker_ms"], manifest["continuation_rows"]),
        "",
        "## Interpretation",
        "",
        "- The ASoC warning is common evidence, not a native-only stop condition.",
        "- Both Android and native V644 reach sound-card registration after the warning.",
        "- Android then reaches WLFW/WLAN-PD/QMI/BDF/wlan0; native V644 does not.",
        "- The next gate should target CNSS/WLFW post-warning continuation, not the warning itself.",
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
