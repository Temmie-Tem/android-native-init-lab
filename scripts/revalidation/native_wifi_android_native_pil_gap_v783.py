#!/usr/bin/env python3
"""V783 host-only Android/native PIL and WLAN-PD gap classifier.

This classifier consumes already captured V782 native evidence and Android
reference logs.  It does not talk to the device.  The goal is to decide where
the next safe live/read-only gate should focus after V782 proved PIL
notifications are countable but still did not produce service-notifier,
WLAN-PD, WLFW, BDF, wiphy, or wlan0.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v783-android-native-pil-gap")
LATEST_POINTER = Path("tmp/wifi/latest-v783-android-native-pil-gap.txt")
DEFAULT_ANDROID_DMESG_V519 = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/inputs/android-dmesg-wifi-cnss-tail.txt")
DEFAULT_ANDROID_DMESG_V649 = Path(
    "tmp/wifi/v649-android-full-audio-wifi-handoff-live-20260523-074556/"
    "v649-android-full-audio-wifi-recapture-run/android/commands/dmesg-audio-wifi-tail.txt"
)
DEFAULT_ANDROID_LOWER_STATE = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/android-lower-surface-state.txt"
)
DEFAULT_NATIVE_V782_MANIFEST = Path("tmp/wifi/v782-bpf-counter-boot-wlan/manifest.json")
DEFAULT_NATIVE_V782_DMESG = Path("tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt")
DEFAULT_NATIVE_V782_BPF = Path("tmp/wifi/v782-bpf-counter-boot-wlan/native/bpf-counter-collect.txt")
READ_LIMIT_BYTES = 8 * 1024 * 1024

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TIMESTAMP_RE = re.compile(r"^\s*\[\s*(?P<time>\d+(?:\.\d+)?)\]")

MARKERS: dict[str, re.Pattern[str]] = {
    "wlan_loading": re.compile(r"\bwlan: Loading driver", re.IGNORECASE),
    "wlan_hdd_state": re.compile(r"\bwlan_hdd_state\b", re.IGNORECASE),
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE),
    "sysmon_modem": re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.IGNORECASE),
    "sysmon_slpi": re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.IGNORECASE),
    "sysmon_cdsp": re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.IGNORECASE),
    "sysmon_adsp": re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.IGNORECASE),
    "sysmon_esoc0": re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.IGNORECASE),
    "servloc": re.compile(r"\bservloc:.*Service locator", re.IGNORECASE),
    "service_notifier_74": re.compile(r"service-notifier:.*\b74 service", re.IGNORECASE),
    "service_notifier_180": re.compile(r"service-notifier:.*\b180 service", re.IGNORECASE),
    "wlan_pd_ind": re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.IGNORECASE),
    "icnss_qmi": re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE),
    "wlan0": re.compile(r"\bdev\s*:\s*wlan0\b|ADDRCONF\(NETDEV_UP\): wlan0", re.IGNORECASE),
    "memshare_request": re.compile(r"memshare_.*memory alloc request", re.IGNORECASE),
    "memshare_fail": re.compile(r"memshare_.*unable to allocate|cma: cma_alloc: alloc failed", re.IGNORECASE),
    "icnss_modules_not_init": re.compile(r"icnss: Modules not initialized", re.IGNORECASE),
}

ORDERED_CHAIN = (
    "wlan_loading",
    "wlan_hdd_state",
    "qrtr_rx",
    "qrtr_tx",
    "sysmon_modem",
    "servloc",
    "service_notifier_74",
    "service_notifier_180",
    "wlan_pd_ind",
    "icnss_qmi",
    "bdf_regdb",
    "bdf_bdwlan",
    "sysmon_esoc0",
    "wlan_fw_ready",
    "wlan0",
)


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
    parser.add_argument("--android-dmesg-v519", type=Path, default=DEFAULT_ANDROID_DMESG_V519)
    parser.add_argument("--android-dmesg-v649", type=Path, default=DEFAULT_ANDROID_DMESG_V649)
    parser.add_argument("--android-lower-state", type=Path, default=DEFAULT_ANDROID_LOWER_STATE)
    parser.add_argument("--native-v782-manifest", type=Path, default=DEFAULT_NATIVE_V782_MANIFEST)
    parser.add_argument("--native-v782-dmesg", type=Path, default=DEFAULT_NATIVE_V782_DMESG)
    parser.add_argument("--native-v782-bpf", type=Path, default=DEFAULT_NATIVE_V782_BPF)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    size = resolved.stat().st_size if resolved.is_file() else None
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "size": size,
        "read_limited": bool(size is not None and size > READ_LIMIT_BYTES),
    }


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info = file_info(path)
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info["bytes_read"] = len(data)
    info["truncated"] = bool(resolved.stat().st_size > len(data))
    return data.decode("utf-8", errors="replace"), info


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r\n", "\n")


def timestamp(line: str) -> float | None:
    match = TIMESTAMP_RE.match(line)
    return float(match.group("time")) if match else None


def analyze_text(path: Path, label: str) -> dict[str, Any]:
    raw, info = safe_read(path)
    text = strip_ansi(raw)
    lines = text.splitlines()
    markers: dict[str, dict[str, Any]] = {}
    for name, pattern in MARKERS.items():
        hits: list[dict[str, Any]] = []
        for line_no, line in enumerate(lines, start=1):
            if line.startswith("$ "):
                continue
            if pattern.search(line):
                hits.append({"line_no": line_no, "time": timestamp(line), "line": line[:240]})
        first = hits[0] if hits else None
        markers[name] = {
            "count": len(hits),
            "first_time": first.get("time") if first else None,
            "first_line": first.get("line") if first else "",
            "first_line_no": first.get("line_no") if first else None,
        }
    command_line = lines[0] if lines and lines[0].startswith("$ ") else ""
    return {
        "label": label,
        "file": info,
        "line_count": len(lines),
        "command_line": command_line[:500],
        "grep_filter_mentions_memshare": "memshare" in command_line.lower() or "cma_alloc" in command_line.lower(),
        "markers": markers,
        "chain": build_chain(markers),
        "deltas": build_deltas(markers),
    }


def build_chain(markers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "marker": marker,
            "count": markers[marker]["count"],
            "first_time": markers[marker]["first_time"],
        }
        for marker in ORDERED_CHAIN
    ]


def build_deltas(markers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sysmon_time = markers["sysmon_modem"]["first_time"]
    qrtr_rx_time = markers["qrtr_rx"]["first_time"]

    def delta(marker: str, base: float | None) -> float | None:
        first = markers[marker]["first_time"]
        if first is None or base is None:
            return None
        return round(first - base, 6)

    return {
        "sysmon_minus_qrtr_rx_sec": delta("sysmon_modem", qrtr_rx_time),
        "service74_after_sysmon_sec": delta("service_notifier_74", sysmon_time),
        "service180_after_sysmon_sec": delta("service_notifier_180", sysmon_time),
        "wlan_pd_after_sysmon_sec": delta("wlan_pd_ind", sysmon_time),
        "icnss_qmi_after_sysmon_sec": delta("icnss_qmi", sysmon_time),
        "bdf_regdb_after_sysmon_sec": delta("bdf_regdb", sysmon_time),
        "wlan_fw_ready_after_sysmon_sec": delta("wlan_fw_ready", sysmon_time),
        "wlan0_after_sysmon_sec": delta("wlan0", sysmon_time),
        "memshare_fail_after_sysmon_sec": delta("memshare_fail", sysmon_time),
    }


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    if not info.get("exists"):
        return {"file": info, "data": {}}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": data if isinstance(data, dict) else {}}


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in strip_ansi(text).splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Za-z0-9_.-]+", key):
            values[key] = value.strip()
    return values


def analyze_bpf(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    values = parse_key_values(text)
    return {
        "file": info,
        "target": values.get("target", ""),
        "tracepoint_id": values.get("tracepoint_id", ""),
        "event_count": int(values.get("event_count", "0")) if values.get("event_count", "0").isdigit() else None,
        "result": values.get("result", ""),
        "attach_attempted": values.get("attach_attempted", ""),
        "payload_fields_captured": False,
    }


def parse_state_file(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    values = parse_key_values(text)
    return {"file": info, "values": values}


def analyze_manifest(path: Path) -> dict[str, Any]:
    loaded = load_json(path)
    data = loaded.get("data", {})
    live = data.get("live", {}) if isinstance(data.get("live"), dict) else {}
    markers = live.get("markers", {}) if isinstance(live.get("markers"), dict) else {}
    marker_counts = markers.get("counts", {}) if isinstance(markers.get("counts"), dict) else {}
    return {
        "file": loaded.get("file", {}),
        "decision": data.get("decision", ""),
        "pass": data.get("pass"),
        "bpf_event_count": live.get("bpf_event_count"),
        "mss_before": live.get("mss_before"),
        "mss_after_holder": live.get("mss_after_holder"),
        "mss_after_boot": live.get("mss_after_boot"),
        "mdm3_before": live.get("mdm3_before"),
        "mdm3_after_holder": live.get("mdm3_after_holder"),
        "mdm3_after_boot": live.get("mdm3_after_boot"),
        "qrtr_services_after_boot": live.get("qrtr_services_after_boot", {}),
        "marker_counts": marker_counts,
        "boot_wlan_write_executed": data.get("boot_wlan_write_executed"),
        "wifi_bringup_executed": data.get("wifi_bringup_executed"),
        "scan_connect_executed": data.get("scan_connect_executed"),
        "external_ping_executed": data.get("external_ping_executed"),
    }


def first_present_gap(native_markers: dict[str, dict[str, Any]], android_markers: dict[str, dict[str, Any]]) -> str:
    for marker in ORDERED_CHAIN:
        if android_markers[marker]["count"] > 0 and native_markers[marker]["count"] == 0:
            return marker
    return ""


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    android_v519 = analyze_text(args.android_dmesg_v519, "android-v519")
    android_v649 = analyze_text(args.android_dmesg_v649, "android-v649")
    native_v782 = analyze_text(args.native_v782_dmesg, "native-v782")
    android_reference = android_v649 if android_v649["file"].get("exists") else android_v519
    native_manifest = analyze_manifest(args.native_v782_manifest)
    bpf = analyze_bpf(args.native_v782_bpf)
    android_lower = parse_state_file(args.android_lower_state)
    memshare_android_filter_weak = not (
        android_v519["grep_filter_mentions_memshare"] or android_v649["grep_filter_mentions_memshare"]
    )
    return {
        "inputs": {
            "android_dmesg_v519": android_v519["file"],
            "android_dmesg_v649": android_v649["file"],
            "android_lower_state": android_lower["file"],
            "native_v782_manifest": native_manifest["file"],
            "native_v782_dmesg": native_v782["file"],
            "native_v782_bpf": bpf["file"],
        },
        "android": {
            "v519": android_v519,
            "v649": android_v649,
            "selected_reference": android_reference["label"],
            "lower_state": android_lower["values"],
        },
        "native": {
            "v782": native_v782,
            "v782_manifest": native_manifest,
            "v782_bpf": bpf,
        },
        "comparison": {
            "selected_reference": android_reference["label"],
            "first_android_native_gap": first_present_gap(native_v782["markers"], android_reference["markers"]),
            "android_has_service_notifier": (
                android_reference["markers"]["service_notifier_74"]["count"] > 0
                and android_reference["markers"]["service_notifier_180"]["count"] > 0
            ),
            "native_has_service_notifier": (
                native_v782["markers"]["service_notifier_74"]["count"] > 0
                or native_v782["markers"]["service_notifier_180"]["count"] > 0
            ),
            "native_memshare_fail_count": native_v782["markers"]["memshare_fail"]["count"],
            "native_memshare_request_count": native_v782["markers"]["memshare_request"]["count"],
            "android_memshare_fail_count_in_filtered_refs": (
                android_v519["markers"]["memshare_fail"]["count"] + android_v649["markers"]["memshare_fail"]["count"]
            ),
            "android_memshare_filter_weak": memshare_android_filter_weak,
            "bpf_payload_fields_captured": bpf["payload_fields_captured"],
            "mdm3_native_after_boot": native_manifest.get("mdm3_after_boot"),
            "mss_native_after_boot": native_manifest.get("mss_after_boot"),
            "android_mdm3_state": android_lower["values"].get("mdm3_state", ""),
            "android_mss_state": android_lower["values"].get("mss_state", ""),
        },
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    inputs = analysis["inputs"]
    comparison = analysis["comparison"]
    native = analysis["native"]["v782"]
    android = analysis["android"][analysis["android"]["selected_reference"].split("-", 1)[1]]
    checks: list[Check] = []
    add_check(
        checks,
        "required-inputs",
        "pass" if all(info.get("exists") for info in inputs.values()) else "blocked",
        "blocker",
        " ".join(f"{name}={info.get('exists')}" for name, info in inputs.items()),
        "restore exact V782 and Android reference evidence before classifying",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "device_commands=false flash=false reboot=false",
        "preserve host-only analysis for this cycle",
    )
    add_check(
        checks,
        "v782-bpf-observer",
        "pass" if analysis["native"]["v782_bpf"].get("event_count", 0) > 0 else "review",
        "warn",
        f"event_count={analysis['native']['v782_bpf'].get('event_count')} payload_fields=false",
        "if payload names/codes are needed, create a separate payload-capture gate",
    )
    add_check(
        checks,
        "android-reference-chain",
        "pass" if comparison["android_has_service_notifier"] and android["markers"]["wlan0"]["count"] > 0 else "review",
        "warn",
        f"selected={comparison['selected_reference']} first_gap={comparison['first_android_native_gap']}",
        "use Android chain only as reference, not as a live action plan",
    )
    add_check(
        checks,
        "native-post-sysmon-gap",
        "pass"
        if native["markers"]["sysmon_modem"]["count"] > 0 and not comparison["native_has_service_notifier"]
        else "review",
        "warn",
        (
            f"native_sysmon={native['markers']['sysmon_modem']['count']} "
            f"native_service74={native['markers']['service_notifier_74']['count']} "
            f"native_service180={native['markers']['service_notifier_180']['count']}"
        ),
        "do not repeat boot_wlan; classify why service-notifier 74/180 do not publish in native",
    )
    add_check(
        checks,
        "memshare-cma-lead",
        "pass" if comparison["native_memshare_fail_count"] > 0 else "review",
        "warn",
        (
            f"native_fail={comparison['native_memshare_fail_count']} "
            f"native_request={comparison['native_memshare_request_count']} "
            f"android_filtered_fail={comparison['android_memshare_fail_count_in_filtered_refs']} "
            f"android_filter_weak={comparison['android_memshare_filter_weak']}"
        ),
        "run targeted read-only memshare/CMA surface and Android/native recapture before another WLAN trigger",
    )
    if command == "plan":
        add_check(
            checks,
            "plan-only",
            "pass",
            "info",
            "no evidence mutation beyond private host output",
            "run V783 host-only classifier",
        )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v783-android-native-pil-gap-plan-ready",
            True,
            "plan-only host classifier; no device command or Wi-Fi action",
            "run V783 against existing V782 and Android evidence",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v783-android-native-pil-gap-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "restore required evidence files and rerun host-only classifier",
        )
    comparison = analysis["comparison"]
    native_fail = comparison["native_memshare_fail_count"]
    reason = (
        "native V782 reaches mss ONLINE, QRTR RX/TX, sysmon, service-locator, and boot_wlan, "
        "but lacks service-notifier 74/180, WLAN-PD indication, ICNSS-QMI, BDF, FW-ready, wiphy, and wlan0"
    )
    if native_fail:
        reason += "; native dmesg also shows memshare/CMA allocation failure at the sysmon window"
    return (
        "v783-mdm3-wlan-pd-gap-memshare-lead-classified",
        True,
        reason,
        (
            "V784 should be read-only: collect memshare/CMA/reserved-memory and exact Android/native memshare dmesg "
            "surface before any further boot_wlan, qcwlanstate, daemon, HAL, scan/connect, or flash attempt"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    comparison = analysis["comparison"]
    android_ref = analysis["android"][analysis["android"]["selected_reference"].split("-", 1)[1]]
    native = analysis["native"]["v782"]
    bpf = analysis["native"]["v782_bpf"]
    checks = manifest["checks"]
    chain_rows = []
    for marker in ORDERED_CHAIN:
        chain_rows.append([
            marker,
            android_ref["markers"][marker]["count"],
            android_ref["markers"][marker]["first_time"],
            native["markers"][marker]["count"],
            native["markers"][marker]["first_time"],
        ])
    delta_rows = [
        [key, value, native["deltas"].get(key)]
        for key, value in android_ref["deltas"].items()
    ]
    return "\n".join([
        "# V783 Android/Native PIL Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- flash_executed: `{manifest['flash_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]),
        "",
        "## Chain Comparison",
        "",
        markdown_table(["marker", "android_count", "android_first", "native_count", "native_first"], chain_rows),
        "",
        "## Delta From sysmon_modem",
        "",
        markdown_table(["delta", "android_sec", "native_sec"], delta_rows),
        "",
        "## BPF Counter",
        "",
        markdown_table(["signal", "value"], [
            ["target", bpf.get("target")],
            ["tracepoint_id", bpf.get("tracepoint_id")],
            ["event_count", bpf.get("event_count")],
            ["result", bpf.get("result")],
            ["payload_fields_captured", bpf.get("payload_fields_captured")],
        ]),
        "",
        "## Interpretation",
        "",
        "- V782 proves the lower-window path emits real PIL notifications, but the helper counted only events and did not capture `event_name`, `code`, or `fw_name` payload fields.",
        "- Android reaches service-notifier `74/180`, WLAN-PD indication, ICNSS-QMI, BDF download, firmware-ready, and `wlan0`; native V782 stops after sysmon/service-locator and HDD control-surface creation.",
        "- Native V782 has memshare/CMA allocation failures at the sysmon window. The Android reference logs are filtered and do not include `memshare`, so absence in Android references is not proof; it is a targeted recapture requirement.",
        "- Next work should not repeat blind `boot_wlan`, `qcwlanstate`, daemon ordering, HAL start, scan/connect, or custom-kernel flashing.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v783",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
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
    print(f"flash_executed: {manifest['flash_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
