#!/usr/bin/env python3
"""V648 read-only audio/ASoC parity guard.

This collector reads current native audio/ASoC surface and compares it with
V644 warning evidence plus Android V622 lower-surface evidence. It does not
write sysfs, start daemons, start Wi-Fi HAL, run qcwlanstate, scan/connect,
use credentials, run DHCP, change routes, reboot, flash, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v648-audio-asoc-parity-guard")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 30.0
DEFAULT_ANDROID_DMESG = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/android/commands/dmesg-lower-surface-tail.txt"
)
DEFAULT_V644_DMESG = Path("tmp/wifi/v644-live-20260523-071610/native/dmesg-after-companion.txt")
BUSYBOX = "/cache/bin/busybox"
TOYBOX = "/cache/bin/toybox"
SAFE_AUDIO_GREP = (
    "msm_asoc|sm8150-asoc|msm-audio-apr|qcom,msm-pcm-voice|"
    "pm_qos_add_request|wsa881|Sound card|audio codec|apr_audio_svc|"
    "adsprpc|fastrpc|ADSPRPC|service-notifier|wlan_pd"
)
PATTERNS = {
    "apr_audio_up": re.compile(r"apr_tal_rpmsg.*apr_audio_svc.*state\[Up\]|apr_audio_svc", re.I),
    "adsp_rpmsg": re.compile(r"opened rpmsg channel for adsp|adsp.*rpmsg", re.I),
    "audio_locator_down": re.compile(r"ADSPRPC: Audio PD restart notifier locator down", re.I),
    "audio_ion": re.compile(r"msm-audio-ion", re.I),
    "asoc_probe": re.compile(r"msm_asoc_machine_probe: Enter", re.I),
    "pcm_voice_missing": re.compile(r"ASoC: platform /soc/qcom,msm-pcm-voice not registered", re.I),
    "wsa_fail": re.compile(r"wsa881x: probe .* failed|bolero node not found", re.I),
    "audio_codec_registered": re.compile(r"audio codec registered", re.I),
    "sound_card_registered": re.compile(r"Sound card .* registered", re.I),
    "pm_qos_duplicate": re.compile(r"pm_qos_add_request\(\) called for already added request", re.I),
    "qos_warning": re.compile(r"WARNING: CPU:.*kernel/power/qos\.c:616", re.I),
    "service_notifier_74": re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I),
    "wlan_pd": re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I),
}
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--v644-dmesg", type=Path, default=DEFAULT_V644_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r", "")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel_path = f"native/{safe_name(name)}.txt"
    store.write_text(rel_path, text.rstrip() + "\n")
    return rel_path


def run_step(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, payload)
    item["payload"] = payload
    return item


def line_time(line: str) -> float | None:
    match = TS_RE.match(line.strip())
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def count_lines(lines: list[str], pattern: re.Pattern[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def first_time(lines: list[str], pattern: re.Pattern[str]) -> float | None:
    for line in lines:
        if pattern.search(line):
            return line_time(line)
    return None


def first_line(lines: list[str], pattern: re.Pattern[str]) -> str:
    for line in lines:
        if pattern.search(line):
            return line
    return "missing"


def analyze_audio_text(label: str, text: str) -> dict[str, Any]:
    lines = [line.strip() for line in clean_text(text).splitlines() if line.strip()]
    counts = {name: count_lines(lines, pattern) for name, pattern in PATTERNS.items()}
    times = {name: first_time(lines, pattern) for name, pattern in PATTERNS.items()}
    return {
        "label": label,
        "line_count": len(lines),
        "counts": counts,
        "times": times,
        "first_lines": {name: first_line(lines, pattern) for name, pattern in PATTERNS.items()},
        "warning_dirty": counts["pm_qos_duplicate"] > 0 or counts["qos_warning"] > 0,
        "asoc_probe_started": counts["asoc_probe"] > 0,
        "audio_ready_markers": {
            "apr_audio_up": counts["apr_audio_up"] > 0,
            "audio_codec_registered": counts["audio_codec_registered"] > 0,
            "sound_card_registered": counts["sound_card_registered"] > 0,
        },
    }


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    plan_only = args.command == "plan"
    if not plan_only:
        steps.append(run_step(args, store, "bootstatus", ["bootstatus"], 10.0))
        steps.append(run_step(
            args,
            store,
            "native-audio-dmesg-tail",
            [
                "run",
                BUSYBOX,
                "sh",
                "-c",
                f"{TOYBOX} dmesg 2>&1 | {TOYBOX} grep -Ei '{SAFE_AUDIO_GREP}' | {TOYBOX} tail -n 300",
            ],
            20.0,
        ))
        steps.append(run_step(
            args,
            store,
            "native-asound-cards",
            ["run", BUSYBOX, "sh", "-c", "if [ -r /proc/asound/cards ]; then cat /proc/asound/cards; else echo missing:/proc/asound/cards; fi"],
            10.0,
        ))
        steps.append(run_step(
            args,
            store,
            "native-dev-snd",
            ["run", BUSYBOX, "sh", "-c", "if [ -d /dev/snd ]; then ls -l /dev/snd; else echo missing:/dev/snd; fi"],
            10.0,
        ))
        steps.append(run_step(
            args,
            store,
            "native-platform-audio-devices",
            [
                "run",
                BUSYBOX,
                "sh",
                "-c",
                "ls /sys/bus/platform/devices 2>/dev/null | "
                f"{TOYBOX} grep -Ei 'audio|sound|apr|wsa|wcd|swr|bolero|lpass|voice' | {TOYBOX} tail -n 250",
            ],
            10.0,
        ))

    native_text = "\n".join(step.get("payload", "") for step in steps if step.get("file") == "native/native-audio-dmesg-tail.txt")
    android_text = read_text(args.android_dmesg)
    v644_text = read_text(args.v644_dmesg)
    native = analyze_audio_text("current native v641 read-only", native_text)
    android = analyze_audio_text("Android V622 lower-surface reference", android_text)
    v644 = analyze_audio_text("V644 clean-DSP service74 warning run", v644_text)

    if plan_only:
        decision, pass_ok, reason, next_step = (
            "v648-audio-asoc-parity-guard-plan-ready",
            True,
            "plan-only; no live read-only audio surface collected",
            "run V648 read-only collector on native",
        )
    else:
        current_clean = not native["warning_dirty"] and not native["asoc_probe_started"]
        v644_dirty_asoc = v644["warning_dirty"] and v644["asoc_probe_started"]
        android_lower_clean = android["counts"]["service_notifier_74"] > 0 and not android["warning_dirty"]
        if current_clean and v644_dirty_asoc and android_lower_clean:
            decision, pass_ok, reason, next_step = (
                "v648-current-clean-v644-asoc-gap-classified",
                True,
                "current native v641 is warning-free and has not started ASoC probe; V644 warning appears only when ASoC probe starts during the service74 path; Android lower evidence is warning-free but lacks full early audio context",
                "plan V649 Android full audio/Wi-Fi dmesg recapture before any V644-style retry",
            )
        else:
            decision, pass_ok, reason, next_step = (
                "v648-audio-parity-review-required",
                False,
                f"current_clean={current_clean} v644_dirty_asoc={v644_dirty_asoc} android_lower_clean={android_lower_clean}",
                "inspect current native and Android audio evidence manually",
            )

    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "android_dmesg": str(repo_path(args.android_dmesg)),
            "v644_dmesg": str(repo_path(args.v644_dmesg)),
        },
        "steps": steps,
        "native": native,
        "android": android,
        "v644": v644,
        "case_rows": [
            ["current native v641", str(native["counts"]["service_notifier_74"]), str(native["counts"]["asoc_probe"]), str(native["counts"]["pm_qos_duplicate"]), str(native["counts"]["audio_locator_down"]), str(native["warning_dirty"])],
            ["V644 service74 path", str(v644["counts"]["service_notifier_74"]), str(v644["counts"]["asoc_probe"]), str(v644["counts"]["pm_qos_duplicate"]), str(v644["counts"]["audio_locator_down"]), str(v644["warning_dirty"])],
            ["Android V622 lower", str(android["counts"]["service_notifier_74"]), str(android["counts"]["asoc_probe"]), str(android["counts"]["pm_qos_duplicate"]), str(android["counts"]["audio_locator_down"]), str(android["warning_dirty"])],
        ],
        "device_commands_executed": not plan_only,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V648 Audio/ASoC Parity Guard",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Case Matrix",
        "",
        markdown_table(["case", "svc74", "asoc_probe", "pm_qos_dup", "audio_locator_down", "warning_dirty"], manifest["case_rows"]),
        "",
        "## Current Native First Lines",
        "",
        markdown_table(
            ["marker", "line"],
            [[key, value] for key, value in manifest["native"]["first_lines"].items() if value != "missing"],
        ),
        "",
        "## Interpretation",
        "",
        "- Current native v641 is clean at idle: no ASoC probe and no duplicate `pm_qos` warning in the collected audio tail.",
        "- V644 starts ASoC probe in the service `74` path and immediately hits duplicate `pm_qos`.",
        "- Android lower-surface evidence reaches service `74` without a kernel warning, but the captured Android tail is not a full early audio boot trace.",
        "- The next gate should recapture Android full audio/Wi-Fi dmesg before designing another V644-style live retry.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
