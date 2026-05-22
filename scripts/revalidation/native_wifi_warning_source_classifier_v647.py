#!/usr/bin/env python3
"""V647 host-only warning-source classifier for the service74 window.

This classifier does not contact the device, write sysfs, start daemons, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, reboot,
flash, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v647-warning-source-classifier")
DEFAULT_V619_DMESG = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/native/dmesg-delta.txt")
DEFAULT_V638_DMESG = Path("tmp/wifi/v638-firmware-sibling-live-20260523-060104/native/dmesg-after-sibling.txt")
DEFAULT_V644_MANIFEST = Path("tmp/wifi/v644-live-20260523-071610/manifest.json")
DEFAULT_V628_MANIFEST = Path("tmp/wifi/v628-service74-publisher-classifier/manifest.json")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
PATTERNS = {
    "service_notifier_180": re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I),
    "service_notifier_74": re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I),
    "wlan_pd": re.compile(r"service-notifier:.*msm/modem/wlan_pd|wlan_pd", re.I),
    "asoc_probe": re.compile(r"msm_asoc_machine_probe: Enter", re.I),
    "asoc_pm_noise": re.compile(r"msm_asoc_machine_probe: pm noise", re.I),
    "audio_platform_missing": re.compile(r"ASoC: platform .* not registered", re.I),
    "audio_apr": re.compile(r"sm8150-asoc-snd|msm-audio-apr|sound-tavil|wcd-spi|wsa881", re.I),
    "pm_qos_duplicate": re.compile(r"pm_qos_add_request\(\) called for already added request", re.I),
    "qos_warning": re.compile(r"WARNING: CPU:.*kernel/power/qos\.c:616", re.I),
    "calltrace_asoc_probe": re.compile(r"\s+msm_asoc_machine_probe\+0x", re.I),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v619-dmesg", type=Path, default=DEFAULT_V619_DMESG)
    parser.add_argument("--v638-dmesg", type=Path, default=DEFAULT_V638_DMESG)
    parser.add_argument("--v644-manifest", type=Path, default=DEFAULT_V644_MANIFEST)
    parser.add_argument("--v628-manifest", type=Path, default=DEFAULT_V628_MANIFEST)
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


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


def line_time(raw_line: str) -> float | None:
    match = TS_RE.match(clean_line(raw_line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000.0, 3)


def first_line(lines: list[str], pattern: re.Pattern[str]) -> str:
    for line in lines:
        if pattern.search(line):
            return line
    return "missing"


def first_time(lines: list[str], pattern: re.Pattern[str]) -> float | None:
    for line in lines:
        if pattern.search(line):
            return line_time(line)
    return None


def count_lines(lines: list[str], pattern: re.Pattern[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def context_digest(lines: list[str], pattern: re.Pattern[str], *, before: int = 5, after: int = 10) -> list[str]:
    for index, line in enumerate(lines):
        if pattern.search(line):
            start = max(0, index - before)
            stop = min(len(lines), index + after + 1)
            digest: list[str] = []
            for context_line in lines[start:stop]:
                if any(marker.search(context_line) for marker in (
                    PATTERNS["service_notifier_74"],
                    PATTERNS["asoc_probe"],
                    PATTERNS["asoc_pm_noise"],
                    PATTERNS["audio_platform_missing"],
                    PATTERNS["audio_apr"],
                    PATTERNS["pm_qos_duplicate"],
                    PATTERNS["qos_warning"],
                    PATTERNS["calltrace_asoc_probe"],
                )):
                    digest.append(context_line)
            return digest[:12]
    return []


def analyze_dmesg_text(label: str, text: str) -> dict[str, Any]:
    lines = [clean_line(line) for line in text.splitlines() if clean_line(line)]
    counts = {name: count_lines(lines, pattern) for name, pattern in PATTERNS.items()}
    times = {name: first_time(lines, pattern) for name, pattern in PATTERNS.items()}
    first_lines = {name: first_line(lines, pattern) for name, pattern in PATTERNS.items()}
    return {
        "label": label,
        "line_count": len(lines),
        "counts": counts,
        "times": times,
        "first_lines": first_lines,
        "deltas_ms": {
            "service74_to_asoc_probe": delta_ms(times["asoc_probe"], times["service_notifier_74"]),
            "service74_to_pm_qos": delta_ms(times["pm_qos_duplicate"], times["service_notifier_74"]),
            "asoc_probe_to_pm_qos": delta_ms(times["pm_qos_duplicate"], times["asoc_probe"]),
            "pm_qos_to_warning": delta_ms(times["qos_warning"], times["pm_qos_duplicate"]),
        },
        "warning_context": context_digest(lines, PATTERNS["pm_qos_duplicate"]),
        "audio_warning_signature": (
            counts["asoc_probe"] > 0
            and counts["pm_qos_duplicate"] > 0
            and counts["qos_warning"] > 0
            and counts["calltrace_asoc_probe"] > 0
        ),
    }


def build_case_rows(manifest: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for key in ("v619", "v638", "v644"):
        case = manifest[key]
        counts = case["counts"]
        rows.append([
            case["label"],
            str(counts["service_notifier_74"]),
            str(counts["asoc_probe"]),
            str(counts["pm_qos_duplicate"]),
            str(counts["qos_warning"]),
            str(case["audio_warning_signature"]),
            str(case["deltas_ms"].get("service74_to_pm_qos")),
        ])
    android = manifest["android_v622"]
    rows.append([
        "Android V622 post-74 reference",
        str(android["counts"].get("service_notifier_74")),
        "not-classified",
        "not-classified",
        str(android["counts"].get("kernel_warning")),
        str(android["counts"].get("kernel_warning") == 0),
        "not-applicable",
    ])
    return rows


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v619_text = read_text(args.v619_dmesg)
    v638_text = read_text(args.v638_dmesg)
    v644_manifest = load_json(args.v644_manifest)
    v628_manifest = load_json(args.v628_manifest)
    v644_text = str((v644_manifest.get("live") or {}).get("dmesg_delta") or "")
    android_v622 = (v628_manifest.get("android_v622") or {})

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v647-warning-source-classifier-plan-ready",
            True,
            "plan-only; no warning source classification executed",
            "run V647 host-only classifier",
        )
    else:
        v619_exists = bool(v619_text)
        v638_exists = bool(v638_text)
        v644_exists = bool(v644_text)
        android_counts = android_v622.get("counts") or {}
        if not (v619_exists and v638_exists and v644_exists and android_counts):
            decision, pass_ok, reason, next_step = (
                "v647-evidence-missing",
                False,
                f"v619={v619_exists} v638={v638_exists} v644={v644_exists} android={bool(android_counts)}",
                "restore V619/V638/V644/V628 evidence before live work",
            )
        else:
            v619 = analyze_dmesg_text("V619 direct all-sibling Android-order replay", v619_text)
            v638 = analyze_dmesg_text("V638 firmware all-sibling composite", v638_text)
            v644 = analyze_dmesg_text("V644 clean-DSP CNSS service74 run", v644_text)
            non_service74_warning = (
                v619["audio_warning_signature"]
                and v619["counts"]["service_notifier_74"] == 0
            ) or (
                v638["audio_warning_signature"]
                and v638["counts"]["service_notifier_74"] == 0
            )
            android_clean_post74 = (
                int(android_counts.get("service_notifier_74") or 0) > 0
                and int(android_counts.get("kernel_warning") or 0) == 0
            )
            if v644["audio_warning_signature"] and non_service74_warning and android_clean_post74:
                decision, pass_ok, reason, next_step = (
                    "v647-audio-asoc-pm-qos-warning-source-classified",
                    True,
                    "V644 warning call trace is msm_asoc_machine_probe/pm_qos; V619/V638 reproduce the same warning without service74, while Android has service74 without kernel_warning",
                    "plan V648 audio/ASoC parity guard before any V644-style live retry or Wi-Fi HAL/qcwlanstate",
                )
            else:
                decision, pass_ok, reason, next_step = (
                    "v647-warning-source-review-required",
                    False,
                    f"v644_audio={v644['audio_warning_signature']} non_service74_warning={non_service74_warning} android_clean_post74={android_clean_post74}",
                    "inspect warning context manually before any live retry",
                )

    v619 = analyze_dmesg_text("V619 direct all-sibling Android-order replay", v619_text)
    v638 = analyze_dmesg_text("V638 firmware all-sibling composite", v638_text)
    v644 = analyze_dmesg_text("V644 clean-DSP CNSS service74 run", v644_text)
    android_counts = (android_v622.get("counts") or {})
    android_deltas = (android_v622.get("deltas_ms") or {})
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v619_dmesg": str(repo_path(args.v619_dmesg)),
            "v638_dmesg": str(repo_path(args.v638_dmesg)),
            "v644_manifest": str(repo_path(args.v644_manifest)),
            "v628_manifest": str(repo_path(args.v628_manifest)),
        },
        "v619": v619,
        "v638": v638,
        "v644": v644,
        "android_v622": {
            "counts": android_counts,
            "deltas_ms": android_deltas,
            "service74_to_wlan_pd_ms": None if android_deltas.get("service_notifier_180_to_wlan_pd") is None else round(
                float(android_deltas["service_notifier_180_to_wlan_pd"])
                - float(android_deltas["service_notifier_180_to_service_notifier_74"]),
                3,
            ),
            "first_lines": android_v622.get("first_lines") or {},
        },
        "case_rows": [],
        "checks": {},
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    manifest["case_rows"] = build_case_rows(manifest)
    manifest["checks"] = {
        "v644_warning_is_audio_asoc_pm_qos": v644["audio_warning_signature"],
        "warning_exists_without_service74": (
            (v619["audio_warning_signature"] and v619["counts"]["service_notifier_74"] == 0)
            or (v638["audio_warning_signature"] and v638["counts"]["service_notifier_74"] == 0)
        ),
        "android_service74_is_warning_free": (
            int(android_counts.get("service_notifier_74") or 0) > 0
            and int(android_counts.get("kernel_warning") or 0) == 0
        ),
        "service74_is_temporal_neighbor_not_unique_cause": decision == "v647-audio-asoc-pm-qos-warning-source-classified",
        "live_retry_still_blocked": True,
        "wifi_goal_still_incomplete": True,
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V647 Warning Source Classifier",
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
        "## Case Matrix",
        "",
        markdown_table(
            ["case", "svc74", "asoc_probe", "pm_qos_dup", "qos_warning", "audio_signature", "svc74_to_pm_qos_ms"],
            manifest["case_rows"],
        ),
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## V644 Warning Context",
        "",
        *[f"- `{line}`" for line in manifest["v644"]["warning_context"]],
        "",
        "## Interpretation",
        "",
        "- The V644 warning is in `msm_asoc_machine_probe` and `pm_qos_add_request`, not in the Wi-Fi HAL or `qcwlanstate` path.",
        "- V619 and V638 show the same ASoC/pm_qos warning class without service `74`, so service `74` is not a unique root cause.",
        "- Android V622 has service `74` with no kernel warning, so the missing piece is an Android-like audio/ASoC state or ordering guard.",
        "- Keep V644 live retry, HAL start, `qcwlanstate`, scan/connect, DHCP, route changes, and external ping blocked until the ASoC guard is defined.",
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
