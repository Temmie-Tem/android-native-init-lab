#!/usr/bin/env python3
"""V649 Android full audio/Wi-Fi dmesg recapture.

This collector runs only while Android ADB is available. It captures read-only
audio/ASoC plus lower Wi-Fi readiness evidence from the same Android boot. It
does not enable Wi-Fi, scan/connect, use credentials, run DHCP, change routes,
write sysfs, start daemons, start HALs, reboot, flash, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from native_wifi_android_lower_surface_recapture_v611 import (
    Capture,
    adb_devices,
    capture_shell,
    selected_device_available,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v649-android-full-audio-wifi-recapture")
DEFAULT_TIMEOUT = 45.0
PROP_KEYS = [
    "sys.boot_completed",
    "ro.baseband",
    "ro.boot.baseband",
    "init.svc.vendor.qrtr-ns",
    "init.svc.vendor.rmt_storage",
    "init.svc.vendor.tftp_server",
    "init.svc.vendor.pd_mapper",
    "init.svc.cnss_diag",
    "init.svc.cnss-daemon",
    "init.svc.vendor.audio-hal-2-0",
    "init.svc.vendor.audio-hal",
    "init.svc.audioserver",
    "init.svc.vendor.mdm_helper",
    "ro.boottime.vendor.qrtr-ns",
    "ro.boottime.vendor.rmt_storage",
    "ro.boottime.vendor.tftp_server",
    "ro.boottime.vendor.pd_mapper",
    "ro.boottime.cnss_diag",
    "ro.boottime.cnss-daemon",
    "ro.boottime.vendor.audio-hal-2-0",
    "ro.boottime.vendor.audio-hal",
    "ro.boottime.audioserver",
]
DMESG_PATTERN = (
    "qrtr: Modem QMI Readiness|sysmon-qmi|service-notifier|wlan_pd|"
    "icnss_qmi: QMI Server Connected|BDF file|regdb\\.bin|bdwlan\\.bin|"
    "WLAN FW is ready|wlan0|servloc|service_locator|QIPCRTR|rpmsg|"
    "rmt_storage|tftp|pd-mapper|cnss-daemon|cnss_diag|"
    "msm_asoc|sm8150-asoc|msm-audio-apr|qcom,msm-pcm-voice|"
    "pm_qos_add_request|kernel/power/qos\\.c:616|wsa881|Sound card|"
    "audio codec|apr_audio_svc|adsprpc|fastrpc|ADSPRPC|bolero|swr"
)
MARKERS = {
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
    "sysmon_modem": re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.I),
    "sysmon_slpi": re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.I),
    "sysmon_cdsp": re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.I),
    "sysmon_adsp": re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.I),
    "sysmon_esoc0": re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.I),
    "service_locator": re.compile(r"servloc: service_locator_new_server", re.I),
    "service_notifier_180": re.compile(r"service-notifier: service_notifier_new_server:.*180 service", re.I),
    "service_notifier_74": re.compile(r"service-notifier: service_notifier_new_server:.*74 service", re.I),
    "wlan_pd": re.compile(r"service-notifier:.*wlan_pd|wlan_pd", re.I),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start|\\bwlfw_start\\b", re.I),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.I),
    "bdf_regdb": re.compile(r"regdb\.bin|BDF file.*regdb", re.I),
    "bdf_bdwlan": re.compile(r"bdwlan\.bin|BDF file.*bdwlan", re.I),
    "wlan_fw_ready": re.compile(r"WLAN FW is ready", re.I),
    "wlan0": re.compile(r"\bwlan0\b", re.I),
    "apr_audio_up": re.compile(r"apr_tal_rpmsg.*apr_audio_svc.*state\[Up\]|apr_audio_svc", re.I),
    "adsp_rpmsg": re.compile(r"opened rpmsg channel for adsp|adsp.*rpmsg", re.I),
    "audio_locator_down": re.compile(r"ADSPRPC: Audio PD restart notifier locator down", re.I),
    "asoc_probe": re.compile(r"msm_asoc_machine_probe: Enter", re.I),
    "asoc_pm_noise": re.compile(r"msm_asoc_machine_probe: pm noise", re.I),
    "pcm_voice_missing": re.compile(r"ASoC: platform /soc/qcom,msm-pcm-voice not registered", re.I),
    "wsa_fail": re.compile(r"wsa881x: probe .* failed|bolero node not found", re.I),
    "audio_codec_registered": re.compile(r"audio codec registered", re.I),
    "sound_card_registered": re.compile(r"Sound card .* registered", re.I),
    "pm_qos_duplicate": re.compile(r"pm_qos_add_request\(\) called for already added request", re.I),
    "qos_warning": re.compile(r"WARNING: CPU:.*kernel/power/qos\.c:616", re.I),
}
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--no-su", action="store_true")
    parser.add_argument("--replay-dir", type=Path, default=None)
    parser.add_argument("command", choices=("plan", "preflight", "run", "replay"))
    return parser.parse_args()


def prop_command() -> str:
    props = " ".join(PROP_KEYS)
    return "; ".join([
        "echo A90_V649_PROPS_BEGIN",
        f"for p in {props}; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        "echo A90_V649_PROPS_END",
    ])


def dmesg_command() -> str:
    return f"dmesg 2>&1 | grep -Ei {DMESG_PATTERN!r} | tail -n 2000 || true"


def unfiltered_tail_command() -> str:
    return "dmesg 2>&1 | tail -n 2500 || true"


def collect(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    store.mkdir("android/commands")
    captures: list[Capture] = []
    captures.append(capture_shell(args, store, "same-boot-props", prop_command(), 15.0))
    captures.append(capture_shell(args, store, "dmesg-audio-wifi-tail", dmesg_command(), 35.0))
    captures.append(capture_shell(args, store, "dmesg-unfiltered-tail", unfiltered_tail_command(), 35.0))
    captures.append(capture_shell(args, store, "proc-asound-cards", "cat /proc/asound/cards 2>&1 || true", 10.0))
    captures.append(capture_shell(args, store, "dev-snd", "ls -l /dev/snd 2>&1 || true", 10.0))
    captures.append(capture_shell(
        args,
        store,
        "platform-audio-devices",
        "ls /sys/bus/platform/devices 2>/dev/null | grep -Ei 'audio|sound|apr|wsa|wcd|swr|bolero|lpass|voice' | tail -n 250 || true",
        10.0,
    ))
    return captures


def capture_text(captures: list[Capture], *names: str) -> str:
    wanted = set(names)
    return "\n".join(capture.text for capture in captures if capture.name in wanted)


def line_time(line: str) -> float | None:
    match = TS_RE.match(line.strip())
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "=" not in line or line.startswith("$"):
            continue
        key, value = line.split("=", 1)
        if key in PROP_KEYS:
            values[key] = value
    return values


def parse_markers(text: str) -> dict[str, Any]:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("$ ") and not line.strip().startswith("rc=")
    ]
    counts: dict[str, int] = {}
    first_lines: dict[str, str] = {}
    first_times: dict[str, float | None] = {}
    for name, pattern in MARKERS.items():
        matched = [line for line in lines if pattern.search(line)]
        counts[name] = len(matched)
        first_lines[name] = matched[0] if matched else "missing"
        first_times[name] = line_time(matched[0]) if matched else None
    return {
        "line_count": len(lines),
        "counts": counts,
        "first_lines": first_lines,
        "first_times": first_times,
        "deltas_ms": {
            "service74_to_asoc_probe": delta_ms(first_times["asoc_probe"], first_times["service_notifier_74"]),
            "service74_to_wlfw_start": delta_ms(first_times["wlfw_start"], first_times["service_notifier_74"]),
            "service74_to_wlan_pd": delta_ms(first_times["wlan_pd"], first_times["service_notifier_74"]),
            "service74_to_qmi_server_connected": delta_ms(first_times["qmi_server_connected"], first_times["service_notifier_74"]),
            "asoc_probe_to_pm_qos": delta_ms(first_times["pm_qos_duplicate"], first_times["asoc_probe"]),
            "pm_qos_to_qos_warning": delta_ms(first_times["qos_warning"], first_times["pm_qos_duplicate"]),
            "apr_audio_up_to_service74": delta_ms(first_times["service_notifier_74"], first_times["apr_audio_up"]),
            "sound_card_to_service74": delta_ms(first_times["service_notifier_74"], first_times["sound_card_registered"]),
        },
    }


def delta_ms(later: float | None, earlier: float | None) -> float | None:
    if later is None or earlier is None:
        return None
    return round((later - earlier) * 1000.0, 3)


def marker_rows(summary: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    counts = summary["counts"]
    first_times = summary["first_times"]
    for name in MARKERS:
        rows.append([name, str(counts.get(name, 0)), "" if first_times.get(name) is None else f"{first_times[name]:.6f}"])
    return rows


def load_replay_captures(args: argparse.Namespace, store: EvidenceStore) -> list[Capture]:
    if args.replay_dir is None:
        return []
    base = args.replay_dir if args.replay_dir.is_absolute() else Path.cwd() / args.replay_dir
    command_dir = base / "android" / "commands"
    captures: list[Capture] = []
    for name in (
        "same-boot-props",
        "dmesg-audio-wifi-tail",
        "dmesg-unfiltered-tail",
        "proc-asound-cards",
        "dev-snd",
        "platform-audio-devices",
    ):
        path = command_dir / f"{name}.txt"
        text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        if text:
            store.write_text(f"android/replay/{name}.txt", text)
        captures.append(Capture(
            name=name,
            command=f"replay:{path}",
            ok=path.exists(),
            rc=0 if path.exists() else None,
            status="ok" if path.exists() else "missing",
            duration_sec=0.0,
            file=f"android/replay/{name}.txt",
            text=text,
            error="" if path.exists() else "missing replay input",
        ))
    return captures


def summarize(captures: list[Capture]) -> dict[str, Any]:
    props = parse_key_values(capture_text(captures, "same-boot-props"))
    dmesg_text = capture_text(captures, "dmesg-audio-wifi-tail", "dmesg-unfiltered-tail")
    marker_summary = parse_markers(dmesg_text)
    counts = marker_summary["counts"]
    return {
        "boot_completed": props.get("sys.boot_completed") == "1",
        "all_commands_ok": all(capture.ok for capture in captures),
        "props": {key: props.get(key, "") for key in PROP_KEYS},
        "markers": marker_summary,
        "has_service74": counts.get("service_notifier_74", 0) > 0,
        "has_wlan_pd": counts.get("wlan_pd", 0) > 0,
        "has_wifi_qmi": counts.get("qmi_server_connected", 0) > 0,
        "has_audio_context": any(counts.get(name, 0) > 0 for name in ("apr_audio_up", "adsp_rpmsg", "asoc_probe", "sound_card_registered", "audio_codec_registered")),
        "has_asoc_probe": counts.get("asoc_probe", 0) > 0,
        "warning_dirty": counts.get("pm_qos_duplicate", 0) > 0 or counts.get("qos_warning", 0) > 0,
        "sound_card_registered": counts.get("sound_card_registered", 0) > 0,
        "audio_locator_down": counts.get("audio_locator_down", 0) > 0,
    }


def decide(args: argparse.Namespace, devices: dict[str, Any], captures: list[Capture], summary: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v649-android-full-audio-wifi-recapture-plan-ready",
            True,
            "plan-only; no adb command executed",
            "boot Android or run approved handoff, then execute V649 collector",
        )
    if args.command == "replay":
        if not captures:
            return "v649-replay-input-missing", False, "no replay captures were loaded", "provide --replay-dir"
        if summary.get("warning_dirty") and summary.get("has_audio_context"):
            return (
                "v649-android-audio-pm-qos-warning-reference-captured",
                True,
                "replayed Android evidence contains service/audio context and duplicate pm_qos warning; the warning is not native-only",
                "plan V650 Android/V644 warning timing comparison; do not retry V644 or start HAL/scan/connect",
            )
        if summary.get("has_service74") and summary.get("has_wlan_pd") and summary.get("has_audio_context") and not summary.get("warning_dirty"):
            return (
                "v649-android-audio-wifi-warning-free-reference-captured",
                True,
                "replayed Android evidence reaches service74/WLAN-PD with audio context and no duplicate pm_qos warning",
                "plan V650 native ASoC-guarded clean-DSP service74 retry; keep HAL/scan/connect blocked",
            )
        return (
            "v649-replay-review-required",
            False,
            f"service74={summary.get('has_service74')} wlan_pd={summary.get('has_wlan_pd')} audio={summary.get('has_audio_context')} warning={summary.get('warning_dirty')}",
            "inspect replayed Android evidence manually",
        )
    if devices["device_count"] == 0:
        return "v649-android-adb-unavailable", False, "no Android ADB device is currently visible", "run Android handoff before V649"
    if not selected_device_available(args, devices):
        return "v649-android-adb-selection-needed", False, f"device_count={devices['device_count']}", "rerun with --serial"
    if args.command == "preflight":
        return "v649-android-full-audio-wifi-preflight-ready", True, "one Android ADB device is visible", "run V649 collector"
    if not summary.get("boot_completed"):
        return "v649-android-not-boot-complete", False, "Android ADB is visible but sys.boot_completed=1 was not captured", "wait for Android boot-complete and rerun V649"
    if summary.get("warning_dirty"):
        return (
            "v649-android-audio-pm-qos-warning-reference-captured",
            True,
            "Android capture contains service/audio context and duplicate pm_qos warning; the warning is not native-only",
            "plan V650 Android/V644 warning timing comparison; do not retry V644 or start HAL/scan/connect",
        )
    if not summary.get("has_service74") or not summary.get("has_wlan_pd"):
        return "v649-lower-wifi-evidence-gap", False, "Android capture lacks service74 or WLAN-PD", "recapture with broader dmesg access"
    if not summary.get("has_audio_context"):
        return "v649-android-audio-context-missing", False, "Android lower path captured but audio context is still absent", "recapture earlier or with broader dmesg buffer"
    return (
        "v649-android-audio-wifi-warning-free-reference-captured",
        True,
        "Android reaches service74/WLAN-PD with audio context and no duplicate pm_qos warning",
        "plan V650 native ASoC-guarded clean-DSP service74 retry; keep HAL/scan/connect blocked",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    summary = manifest["android_summary"]
    return "\n".join([
        "# V649 Android Full Audio/Wi-Fi Recapture",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- boot_completed: `{summary.get('boot_completed')}`",
        f"- warning_dirty: `{summary.get('warning_dirty')}`",
        f"- has_audio_context: `{summary.get('has_audio_context')}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Marker Summary",
        "",
        markdown_table(["marker", "count", "first_ts"], marker_rows(summary["markers"])),
        "",
        "## Timing Deltas",
        "",
        markdown_table(["delta", "ms"], [[key, str(value)] for key, value in summary["markers"]["deltas_ms"].items()]),
        "",
        "## Guardrails",
        "",
        "- Read-only Android ADB collection only.",
        "- No Wi-Fi enable, scan/connect, credentials, DHCP, route changes, or external ping.",
        "- No sysfs write, daemon start, HAL start, reboot, flash, or native boot mutation.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    devices = adb_devices(args) if args.command not in {"plan", "replay"} else {"device_count": 0, "devices": []}
    if args.command == "run":
        captures = collect(args, store)
    elif args.command == "replay":
        captures = load_replay_captures(args, store)
    else:
        captures = []
    summary = summarize(captures) if captures else {"boot_completed": False, "markers": parse_markers(""), "warning_dirty": False, "has_audio_context": False}
    decision, pass_ok, reason, next_step = decide(args, devices, captures, summary)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "devices": devices,
        "captures": [asdict(capture) for capture in captures],
        "android_summary": summary,
        "device_commands_executed": args.command in {"preflight", "run"},
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
